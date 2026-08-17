// Fast path for Halo 3's local-player signed-in helper.
//
// The generated sub_8209A4C8 repeatedly tail-calls XamUserGetSigninState through
// a guest import thunk. In split-screen gameplay this becomes the dominant XAM
// call site. This hook preserves the helper's observed checks while avoiding
// the XAM round trip in the enabled fast path.

#include <rex/cvar.h>
#include <rex/hook.h>
#include <rex/logging.h>
#include <rex/types.h>

#ifdef _WIN32
#include <cstdlib>
#endif

#include <atomic>
#include <cstdint>
#include <cstring>

REXCVAR_DEFINE_BOOL(halo3mp_fast_local_user_state, true, "Halo3MP",
                     "Fast-path Halo 3's local-player signed-in helper");
REXCVAR_DEFINE_BOOL(halo3mp_fast_local_user_state_compare, false, "Halo3MP",
                    "Compare Halo 3 local-player signed-in helper fast path without using it");

extern "C" void __imp__sub_8209A4C8(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void __imp__sub_8209A438(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void __imp__sub_8209A588(PPCContext& __restrict ctx, uint8_t* base);

namespace rex::kernel::xam {
u32 XamUserGetSigninState_direct(u32 user_index);
}

namespace {

constexpr uint32_t kGuestAddressLimit = 0xC0000000u;
constexpr uint32_t kLocalPlayerArrayBase = 0x8319CB88u;
constexpr uint32_t kLocalPlayerArrayStride = 2776u;
constexpr uint32_t kLocalUserStateBase = 0x82F84CB8u;
constexpr uint32_t kLocalUserStateStride = 392u;

inline bool PlausibleGuestPtr(uint32_t address, uint32_t size = 1) {
  return address >= 0x1000u && address < kGuestAddressLimit && size <= kGuestAddressLimit - address;
}

inline uint16_t Load16(uint8_t* base, uint32_t address) {
  uint16_t value;
  std::memcpy(&value, base + address, sizeof(value));
#ifdef _WIN32
  return _byteswap_ushort(value);
#else
  return __builtin_bswap16(value);
#endif
}

inline uint32_t Load32(uint8_t* base, uint32_t address) {
  uint32_t value;
  std::memcpy(&value, base + address, sizeof(value));
#ifdef _WIN32
  return _byteswap_ulong(value);
#else
  return __builtin_bswap32(value);
#endif
}

inline void Store32(uint8_t* base, uint32_t address, uint32_t value) {
#ifdef _WIN32
  value = _byteswap_ulong(value);
#else
  value = __builtin_bswap32(value);
#endif
  std::memcpy(base + address, &value, sizeof(value));
}

inline bool LocalPlayerIndexFromAddress(uint32_t player, uint32_t& out_index) {
  if (player < kLocalPlayerArrayBase) {
    return false;
  }

  const uint32_t offset = player - kLocalPlayerArrayBase;
  if (offset % kLocalPlayerArrayStride != 0) {
    return false;
  }

  const uint32_t index = offset / kLocalPlayerArrayStride;
  if (index >= 4) {
    return false;
  }

  out_index = index;
  return true;
}

bool SignedInUserForPrivilegeFastPath(uint32_t user_index) {
  if (user_index == 255) {
    for (uint32_t candidate = 0; candidate < 4; ++candidate) {
      if (rex::kernel::xam::XamUserGetSigninState_direct(candidate) == 1) {
        return true;
      }
    }
    return false;
  }

  return rex::kernel::xam::XamUserGetSigninState_direct(user_index) == 1;
}

struct FastLocalUserState {
  uint32_t value = 0;
  int32_t local_state_index = -1;
  uint32_t signin_user_index = 0;
  uint32_t local_state_address = 0;
  bool local_slot_active = false;
  bool player_allows_local_user = false;
  uint32_t signin_state = 0;
};

bool TryComputeFastLocalUserState(uint8_t* base, uint32_t player, FastLocalUserState& out) {
  if (!PlausibleGuestPtr(player, 4)) {
    return false;
  }

  out.local_state_index = static_cast<int16_t>(Load16(base, player + 2));
  if (out.local_state_index < 0 || out.local_state_index >= 4) {
    out.value = 0;
    return true;
  }

  if (!LocalPlayerIndexFromAddress(player, out.signin_user_index)) {
    return false;
  }

  out.local_state_address =
      kLocalUserStateBase + static_cast<uint32_t>(out.local_state_index) * kLocalUserStateStride;
  out.local_slot_active =
      PlausibleGuestPtr(out.local_state_address, 4) && Load32(base, out.local_state_address) == 1;
  out.player_allows_local_user = ((Load16(base, player) >> 2) & 1u) != 0;
  // Halo 3 only needs to distinguish signed-in/offline-live local users from
  // absent users here. The local slot flag has already tracked whether the
  // synthetic player exists, so avoid re-entering XAM for the million-call
  // split-screen path.
  out.signin_state = out.signin_user_index < 4 && out.local_slot_active ? 1 : 0;
  out.value = out.local_slot_active && (out.signin_state == 1 || out.signin_state == 2)
                  ? 1
                  : 0;
  return true;
}

}  // namespace

REX_HOOK_RAW(sub_8209A438) {
  const bool compare = REXCVAR_GET(halo3mp_fast_local_user_state_compare);
  const bool enabled = REXCVAR_GET(halo3mp_fast_local_user_state);
  const uint32_t user_index = ctx.r3.u32;
  const uint32_t out_ptr = ctx.r5.u32;
  const bool can_fast_return =
      PlausibleGuestPtr(out_ptr, 4) && SignedInUserForPrivilegeFastPath(user_index);

  if (!enabled) {
    __imp__sub_8209A438(ctx, base);
    if (compare && can_fast_return &&
        (ctx.r3.u32 != 1245 || Load32(base, out_ptr) != 0)) {
      static std::atomic<uint32_t> mismatch_count{0};
      const uint32_t count = mismatch_count.fetch_add(1, std::memory_order_relaxed);
      if (count < 64) {
        REXLOG_INFO(
            "[halo3mp-fast-privilege-signin] mismatch user={} original={} out={:#x}",
            user_index, ctx.r3.u32, Load32(base, out_ptr));
      }
    }
    return;
  }

  if (!can_fast_return) {
    __imp__sub_8209A438(ctx, base);
    return;
  }

  Store32(base, out_ptr, 0);
  ctx.r3.u64 = 1245;
}

REX_HOOK_RAW(sub_8209A4C8) {
  const bool compare = REXCVAR_GET(halo3mp_fast_local_user_state_compare);
  const bool enabled = REXCVAR_GET(halo3mp_fast_local_user_state);
  const uint32_t player = ctx.r3.u32;

  if (!enabled) {
    FastLocalUserState fast{};
    const bool fast_available =
        compare ? TryComputeFastLocalUserState(base, player, fast) : false;
    __imp__sub_8209A4C8(ctx, base);
    if (compare && fast_available && static_cast<uint32_t>(ctx.r3.u32 != 0) != fast.value) {
      static std::atomic<uint32_t> mismatch_count{0};
      const uint32_t count = mismatch_count.fetch_add(1, std::memory_order_relaxed);
      if (count < 64) {
        REXLOG_INFO(
            "[halo3mp-fast-local-user] mismatch player={:#x} original={} fast={} "
            "local_state_index={} signin_user={} local_state={:#x} slot_active={} "
            "player_allows={} signin_state={}",
            player, static_cast<uint32_t>(ctx.r3.u32 != 0), fast.value, fast.local_state_index,
            fast.signin_user_index, fast.local_state_address, fast.local_slot_active,
            fast.player_allows_local_user, fast.signin_state);
      }
    }
    return;
  }

  FastLocalUserState fast{};
  if (!TryComputeFastLocalUserState(base, player, fast)) {
    __imp__sub_8209A4C8(ctx, base);
    return;
  }

  ctx.r3.u64 = fast.value;
}

REX_HOOK_RAW(sub_8209A588) {
  const bool compare = REXCVAR_GET(halo3mp_fast_local_user_state_compare);
  const bool enabled = REXCVAR_GET(halo3mp_fast_local_user_state);
  const uint32_t user_index = ctx.r3.u32;

  if (!enabled) {
    const uint32_t fast =
        compare ? rex::kernel::xam::XamUserGetSigninState_direct(user_index) : 0;
    __imp__sub_8209A588(ctx, base);
    if (compare && ctx.r3.u32 != fast) {
      static std::atomic<uint32_t> mismatch_count{0};
      const uint32_t count = mismatch_count.fetch_add(1, std::memory_order_relaxed);
      if (count < 64) {
        REXLOG_INFO(
            "[halo3mp-fast-signin-wrapper] mismatch user={} original={} fast={}",
            user_index, ctx.r3.u32, fast);
      }
    }
    return;
  }

  ctx.r3.u64 = rex::kernel::xam::XamUserGetSigninState_direct(user_index);
}
