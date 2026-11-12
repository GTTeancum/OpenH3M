#include "developer_framerate.h"
#include <rex/hook.h>
#include <rex/logging.h>
#include <rex/cvar.h>
#include <chrono>
#include <bit>
#include <cstring>
#include <windows.h>

REXCVAR_DECLARE(bool, halo3mp_dev_unlock_test);

// Read-only game-time observation at the existing native frame boundary.
void ObserveDeveloperSimulation(PPCContext& ctx, uint8_t* base) {
  if (REXCVAR_GET(halo3mp_dev_unlock_test)) {
    const auto now = std::chrono::steady_clock::now();
    static thread_local auto last = now - std::chrono::seconds(2);
    if (now - last >= std::chrono::seconds(1)) {
      last = now;
      auto read = [&](uint32_t at, void* value, size_t size) {
        SIZE_T count = 0;
        return at >= 0x10000 && uint64_t(at) + size < 0xE0000000ull &&
            ReadProcessMemory(GetCurrentProcess(), base + at, value, size, &count) && count == size;
      };
      uint32_t tls = 0, pointer = 0;
      uint8_t state[20]{};
      if (read(ctx.r13.u32, &tls, 4) &&
          read(std::byteswap(tls) + 0xBC, &pointer, 4) &&
          read(std::byteswap(pointer), state, sizeof(state))) {
        uint32_t ticks, speed;
        std::memcpy(&ticks, state + 12, 4);
        std::memcpy(&speed, state + 16, 4);
        REXLOG_INFO("[dev-simulation] unlock={} wall_ms={} initialized={} rate={} ticks={} speed={}",
            open_h3m::developer::uncapped.load(),
            std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch()).count(),
            state[0], (unsigned(state[4]) << 8) | state[5], std::byteswap(ticks),
            std::bit_cast<float>(std::byteswap(speed)));
      }
    }
  }
}

extern "C" void __imp__sub_825BF758(PPCContext& __restrict ctx, uint8_t* base);

// XDK presentation scheduling callback. Bits 8..11 select how many vblanks
// to add to device+0x409c. Zero uses the existing immediate-completion path.
// Keep the fence address (bits 12..31), threshold (bits 0..7), guest timer,
// interrupt delivery and simulation code intact.
REX_HOOK_RAW(sub_825BF758) {
  const bool enabled = open_h3m::developer::uncapped.load(std::memory_order_relaxed);
  static thread_local int previous_mode = -1;
  if (previous_mode != int(enabled)) {
    REXLOG_INFO("[dev-present] unlock={} original_interval={} argument={:#x}",
                enabled, (ctx.r3.u32 >> 8) & 15, ctx.r3.u32);
    previous_mode = int(enabled);
  }
  if (enabled) ctx.r3.u32 &= ~0xF00u;
  __imp__sub_825BF758(ctx, base);
}
