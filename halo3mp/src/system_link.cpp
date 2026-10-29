#include "system_link.h"

#include <array>
#include <atomic>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

#if defined(_WIN32)
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
// clang-format off: Windows networking headers require this order.
#include <winsock2.h>
#include <windows.h>
#include <iphlpapi.h>
// clang-format on
#endif

#include <rex/cvar.h>
#include <rex/logging/macros.h>
#include <rex/ppc/context.h>
#include <rex/runtime.h>
#include <rex/system/function_dispatcher.h>

REXCVAR_DEFINE_BOOL(open_h3m_system_link, true, "OpenH3M",
                    "Enable the host System Link compatibility layer");
REXCVAR_DEFINE_BOOL(
    open_h3m_system_link_log, true, "OpenH3M",
    "Log OpenH3M XNet and socket metadata without packet payloads");

extern "C" {
void __imp__NetDll_XNetStartup(PPCContext &ctx, uint8_t *base);
void __imp__NetDll_XNetCleanup(PPCContext &ctx, uint8_t *base);
void __imp__NetDll_XNetXnAddrToInAddr(PPCContext &ctx, uint8_t *base);
void __imp__NetDll_XNetInAddrToXnAddr(PPCContext &ctx, uint8_t *base);
void __imp__NetDll_XNetGetTitleXnAddr(PPCContext &ctx, uint8_t *base);
void __imp__NetDll_XNetGetEthernetLinkStatus(PPCContext &ctx, uint8_t *base);
void __imp__NetDll_socket(PPCContext &ctx, uint8_t *base);
void __imp__NetDll_bind(PPCContext &ctx, uint8_t *base);
void __imp__NetDll_recvfrom(PPCContext &ctx, uint8_t *base);
void __imp__NetDll_sendto(PPCContext &ctx, uint8_t *base);
}

namespace open_h3m::system_link {
namespace {

constexpr uint32_t kGuestAddressLimit = 0xC0000000;
constexpr uint32_t kXnAddrSize = 36;
constexpr uint32_t kXNetAddressStatic = 0x00000004;
constexpr uint32_t kXNetAddressDhcp = 0x00000008;
constexpr uint32_t kXNetAddressGateway = 0x00000020;
constexpr uint32_t kEthernetActive = 0x01;
constexpr uint32_t kEthernet100Mbps = 0x02;
constexpr uint32_t kEthernetFullDuplex = 0x08;

struct HostNetworkIdentity {
  bool available = false;
  std::array<uint8_t, 4> ipv4{};
  std::array<uint8_t, 6> mac{};
  uint32_t interface_type = 0;
  uint32_t address_status = 0;
};

HostNetworkIdentity g_identity;
std::atomic<uint64_t> g_sent_packets{0};
std::atomic<uint64_t> g_sent_bytes{0};
std::atomic<uint64_t> g_received_packets{0};
std::atomic<uint64_t> g_received_bytes{0};
std::atomic<uint64_t> g_send_failures{0};
std::atomic<bool> g_logged_title_address{false};
std::atomic<bool> g_logged_link_status{false};

bool LoggingEnabled() { return REXCVAR_GET(open_h3m_system_link_log); }

uint8_t *GuestPointer(uint8_t *base, uint32_t address, uint32_t size) {
  if (!base || address < 0x1000 || address >= kGuestAddressLimit ||
      size > kGuestAddressLimit - address) {
    return nullptr;
  }
  return base + address;
}

std::string FormatIpv4(const uint8_t *bytes) {
  return std::to_string(bytes[0]) + "." + std::to_string(bytes[1]) + "." +
         std::to_string(bytes[2]) + "." + std::to_string(bytes[3]);
}

std::string FormatEndpoint(uint8_t *base, uint32_t guest_address) {
  const uint8_t *address = GuestPointer(base, guest_address, 16);
  if (!address) {
    return "<none>";
  }
  const uint16_t family = static_cast<uint16_t>((address[0] << 8) | address[1]);
  const uint16_t port = static_cast<uint16_t>((address[2] << 8) | address[3]);
  if (family != 2) {
    return "family=" + std::to_string(family);
  }
  return FormatIpv4(address + 4) + ":" + std::to_string(port);
}

void LogDatagram(bool sent, uint32_t socket_handle, uint32_t byte_count,
                 const std::string &endpoint) {
  auto &packet_counter = sent ? g_sent_packets : g_received_packets;
  auto &byte_counter = sent ? g_sent_bytes : g_received_bytes;
  const uint64_t packets =
      packet_counter.fetch_add(1, std::memory_order_relaxed) + 1;
  const uint64_t bytes =
      byte_counter.fetch_add(byte_count, std::memory_order_relaxed) +
      byte_count;

  // Keep logs useful during long games without turning every datagram into a
  // line.
  if (LoggingEnabled() && (packets <= 8 || packets % 256 == 0)) {
    REXLOG_INFO(
        "[system-link] UDP {} socket={:#x} endpoint={} bytes={} totals={}/{}",
        sent ? "send" : "recv", socket_handle, endpoint, byte_count, packets,
        bytes);
  }
}

HostNetworkIdentity FindHostNetworkIdentity() {
  HostNetworkIdentity identity;
#if defined(_WIN32)
  ULONG size = 16 * 1024;
  std::vector<uint8_t> storage(size);
  auto *addresses = reinterpret_cast<IP_ADAPTER_ADDRESSES *>(storage.data());
  ULONG result =
      GetAdaptersAddresses(AF_INET,
                           GAA_FLAG_SKIP_ANYCAST | GAA_FLAG_SKIP_MULTICAST |
                               GAA_FLAG_SKIP_DNS_SERVER |
                               GAA_FLAG_INCLUDE_GATEWAYS,
                           nullptr, addresses, &size);
  if (result == ERROR_BUFFER_OVERFLOW) {
    storage.resize(size);
    addresses = reinterpret_cast<IP_ADAPTER_ADDRESSES *>(storage.data());
    result =
        GetAdaptersAddresses(AF_INET,
                             GAA_FLAG_SKIP_ANYCAST | GAA_FLAG_SKIP_MULTICAST |
                                 GAA_FLAG_SKIP_DNS_SERVER |
                                 GAA_FLAG_INCLUDE_GATEWAYS,
                             nullptr, addresses, &size);
  }
  if (result != NO_ERROR) {
    REXLOG_WARN("[system-link] GetAdaptersAddresses failed with {}", result);
    return identity;
  }

  for (auto *adapter = addresses; adapter; adapter = adapter->Next) {
    if (adapter->OperStatus != IfOperStatusUp ||
        adapter->IfType == IF_TYPE_SOFTWARE_LOOPBACK ||
        adapter->PhysicalAddressLength < identity.mac.size()) {
      continue;
    }
    for (auto *unicast = adapter->FirstUnicastAddress; unicast;
         unicast = unicast->Next) {
      if (!unicast->Address.lpSockaddr ||
          unicast->Address.lpSockaddr->sa_family != AF_INET) {
        continue;
      }
      const auto *socket_address =
          reinterpret_cast<const sockaddr_in *>(unicast->Address.lpSockaddr);
      const uint8_t *ipv4 =
          reinterpret_cast<const uint8_t *>(&socket_address->sin_addr);
      if ((ipv4[0] == 127) ||
          (ipv4[0] == 0 && ipv4[1] == 0 && ipv4[2] == 0 && ipv4[3] == 0)) {
        continue;
      }

      std::memcpy(identity.ipv4.data(), ipv4, identity.ipv4.size());
      std::memcpy(identity.mac.data(), adapter->PhysicalAddress,
                  identity.mac.size());
      identity.interface_type = adapter->IfType;
      identity.address_status = (adapter->Flags & IP_ADAPTER_DHCP_ENABLED)
                                    ? kXNetAddressDhcp
                                    : kXNetAddressStatic;
      if (adapter->FirstGatewayAddress) {
        identity.address_status |= kXNetAddressGateway;
      }
      identity.available = true;
      return identity;
    }
  }
#endif
  return identity;
}

extern "C" void OpenH3M_XNetStartup(PPCContext &ctx, uint8_t *base) {
  const uint32_t caller = ctx.r3.u32;
  const uint32_t params = ctx.r4.u32;
  __imp__NetDll_XNetStartup(ctx, base);
  if (LoggingEnabled()) {
    REXLOG_INFO("[system-link] XNetStartup caller={} params={:#x} result={:#x}",
                caller, params, ctx.r3.u32);
  }
}

extern "C" void OpenH3M_XNetCleanup(PPCContext &ctx, uint8_t *base) {
  const uint32_t caller = ctx.r3.u32;
  __imp__NetDll_XNetCleanup(ctx, base);
  if (LoggingEnabled()) {
    REXLOG_INFO("[system-link] XNetCleanup caller={} result={:#x}", caller,
                ctx.r3.u32);
  }
}

extern "C" void OpenH3M_XNetGetTitleXnAddr(PPCContext &ctx, uint8_t *base) {
  const uint32_t address_pointer = ctx.r4.u32;
  uint8_t *address = GuestPointer(base, address_pointer, kXnAddrSize);
  if (!g_identity.available || !address) {
    __imp__NetDll_XNetGetTitleXnAddr(ctx, base);
    return;
  }

  std::memset(address, 0, kXnAddrSize);
  std::memcpy(address, g_identity.ipv4.data(), g_identity.ipv4.size());
  std::memcpy(address + 10, g_identity.mac.data(), g_identity.mac.size());
  ctx.r3.u64 = g_identity.address_status;
  if (LoggingEnabled() &&
      !g_logged_title_address.exchange(true, std::memory_order_relaxed)) {
    REXLOG_INFO("[system-link] XNetGetTitleXnAddr status={:#x} local_ipv4={}",
                g_identity.address_status, FormatIpv4(g_identity.ipv4.data()));
  }
}

extern "C" void OpenH3M_XNetGetEthernetLinkStatus(PPCContext &ctx,
                                                  uint8_t *base) {
  (void)base;
  ctx.r3.u64 = g_identity.available
                   ? kEthernetActive | kEthernet100Mbps | kEthernetFullDuplex
                   : 0;
  if (LoggingEnabled() &&
      !g_logged_link_status.exchange(true, std::memory_order_relaxed)) {
    REXLOG_INFO("[system-link] XNetGetEthernetLinkStatus result={:#x}",
                ctx.r3.u32);
  }
}

extern "C" void OpenH3M_XNetXnAddrToInAddr(PPCContext &ctx, uint8_t *base) {
  const uint32_t address_pointer = ctx.r4.u32;
  const uint32_t key_pointer = ctx.r5.u32;
  const uint32_t output_pointer = ctx.r6.u32;
  __imp__NetDll_XNetXnAddrToInAddr(ctx, base);
  if (LoggingEnabled()) {
    REXLOG_INFO("[system-link] XNetXnAddrToInAddr xnaddr={:#x} key={:#x} "
                "out={:#x} result={:#x}",
                address_pointer, key_pointer, output_pointer, ctx.r3.u32);
  }
}

extern "C" void OpenH3M_XNetInAddrToXnAddr(PPCContext &ctx, uint8_t *base) {
  const uint32_t input_pointer = ctx.r4.u32;
  const uint32_t address_pointer = ctx.r5.u32;
  const uint32_t key_pointer = ctx.r6.u32;
  __imp__NetDll_XNetInAddrToXnAddr(ctx, base);
  if (LoggingEnabled()) {
    REXLOG_INFO("[system-link] XNetInAddrToXnAddr in={:#x} xnaddr={:#x} "
                "key={:#x} result={:#x}",
                input_pointer, address_pointer, key_pointer, ctx.r3.u32);
  }
}

extern "C" void OpenH3M_socket(PPCContext &ctx, uint8_t *base) {
  const uint32_t family = ctx.r4.u32;
  const uint32_t type = ctx.r5.u32;
  const uint32_t protocol = ctx.r6.u32;
  __imp__NetDll_socket(ctx, base);
  if (LoggingEnabled()) {
    REXLOG_INFO(
        "[system-link] socket family={} type={} protocol={} handle={:#x}",
        family, type, protocol, ctx.r3.u32);
  }
}

extern "C" void OpenH3M_bind(PPCContext &ctx, uint8_t *base) {
  const uint32_t socket_handle = ctx.r4.u32;
  const uint32_t address_pointer = ctx.r5.u32;
  const std::string endpoint = FormatEndpoint(base, address_pointer);
  __imp__NetDll_bind(ctx, base);
  if (LoggingEnabled()) {
    REXLOG_INFO("[system-link] bind socket={:#x} endpoint={} result={:#x}",
                socket_handle, endpoint, ctx.r3.u32);
  }
}

extern "C" void OpenH3M_sendto(PPCContext &ctx, uint8_t *base) {
  const uint32_t socket_handle = ctx.r4.u32;
  const uint32_t requested_bytes = ctx.r6.u32;
  const std::string endpoint = FormatEndpoint(base, ctx.r8.u32);
  __imp__NetDll_sendto(ctx, base);
  const int32_t result = ctx.r3.s32;
  if (result >= 0) {
    LogDatagram(true, socket_handle, static_cast<uint32_t>(result), endpoint);
  } else if (LoggingEnabled() &&
             g_send_failures.fetch_add(1, std::memory_order_relaxed) < 8) {
    REXLOG_WARN(
        "[system-link] UDP send failed socket={:#x} endpoint={} requested={}",
        socket_handle, endpoint, requested_bytes);
  }
}

extern "C" void OpenH3M_recvfrom(PPCContext &ctx, uint8_t *base) {
  const uint32_t socket_handle = ctx.r4.u32;
  const uint32_t source_pointer = ctx.r8.u32;
  __imp__NetDll_recvfrom(ctx, base);
  const int32_t result = ctx.r3.s32;
  if (result > 0) {
    LogDatagram(false, socket_handle, static_cast<uint32_t>(result),
                FormatEndpoint(base, source_pointer));
  }
}

struct Hook {
  uint32_t guest_address;
  PPCFunc *function;
  const char *name;
};

constexpr std::array<Hook, 10> kHooks{{
    {0x82724294, &OpenH3M_XNetStartup, "XNetStartup"},
    {0x827242A4, &OpenH3M_XNetCleanup, "XNetCleanup"},
    {0x827242F4, &OpenH3M_XNetXnAddrToInAddr, "XNetXnAddrToInAddr"},
    {0x82724314, &OpenH3M_XNetInAddrToXnAddr, "XNetInAddrToXnAddr"},
    {0x827243A4, &OpenH3M_XNetGetTitleXnAddr, "XNetGetTitleXnAddr"},
    {0x827243B4, &OpenH3M_XNetGetEthernetLinkStatus,
     "XNetGetEthernetLinkStatus"},
    {0x827243F4, &OpenH3M_socket, "socket"},
    {0x82724444, &OpenH3M_bind, "bind"},
    {0x827244A4, &OpenH3M_recvfrom, "recvfrom"},
    {0x827244C4, &OpenH3M_sendto, "sendto"},
}};

} // namespace

bool Install(rex::Runtime *runtime) {
  if (!REXCVAR_GET(open_h3m_system_link)) {
    REXLOG_INFO("[system-link] host compatibility layer disabled");
    return true;
  }
  if (!runtime || !runtime->function_dispatcher()) {
    REXLOG_ERROR("[system-link] runtime function dispatcher is unavailable");
    return false;
  }

  g_identity = FindHostNetworkIdentity();
  if (g_identity.available) {
    REXLOG_INFO("[system-link] selected local IPv4 {} (interface type {}); "
                "payload capture is off",
                FormatIpv4(g_identity.ipv4.data()), g_identity.interface_type);
  } else {
    REXLOG_WARN("[system-link] no active non-loopback IPv4 adapter found; "
                "using SDK fallback");
  }

  bool installed = true;
  for (const Hook &hook : kHooks) {
    if (!runtime->function_dispatcher()->SetFunction(hook.guest_address,
                                                     hook.function)) {
      REXLOG_ERROR("[system-link] failed to install {} at {:#010x}", hook.name,
                   hook.guest_address);
      installed = false;
    }
  }
  if (installed) {
    REXLOG_INFO("[system-link] installed {} host-only XNet/socket hooks",
                kHooks.size());
  }
  return installed;
}

} // namespace open_h3m::system_link
