#pragma once
#include <cstdint>
struct PPCContext;
namespace advanced_forge {
// Returns true when Advanced Forge handled the held object for this player.
using NativeHeldDispatch = bool (*)(PPCContext& ctx, uint8_t* base, uint32_t player, uint32_t datum);
// Halo 3's Forge per-player update with the Advanced Forge hand-off.
void RunNativeForgeTick(PPCContext& ctx, uint8_t* base, NativeHeldDispatch dispatch);
}
