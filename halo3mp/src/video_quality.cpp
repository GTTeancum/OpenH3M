#include "video_quality.h"
#include <rex/cvar.h>
#include <rex/hook.h>
#include <rex/ui/video_metrics.h>
#include "video_options.h"
#include <bit>
#include <chrono>
#include <cstring>
#include <string_view>
#include <windows.h>
#include <atomic>
#include <unordered_map>

REXCVAR_DEFINE_BOOL(halo3mp_video_sweep, false, "Diagnostics", "One process-local video sweep; requires exclusive input replay").debug_only();
REXCVAR_DEFINE_BOOL(halo3mp_video_visual_sweep, false, "Diagnostics", "Isolated native shadow/LOD/water comparisons; requires exclusive input replay").debug_only();
REXCVAR_DEFINE_BOOL(halo3mp_video_shadow_sweep, false, "Diagnostics", "Shadow quality comparison and explicit no-shadow diagnostic control; requires exclusive replay").debug_only();
REXCVAR_DEFINE_STRING(halo3mp_video_sweep_config, "", "Diagnostics", "Repository-local settings file used by the explicit video sweep").debug_only();
extern "C" void __imp__sub_82160F28(PPCContext&, uint8_t*);
extern "C" void __imp__sub_8221E000(PPCContext&, uint8_t*);
extern "C" void __imp__sub_82315E70(PPCContext&, uint8_t*);
extern "C" void __imp__sub_82462F88(PPCContext&, uint8_t*);
extern "C" void __imp__sub_8218D770(PPCContext&, uint8_t*);
extern "C" void __imp__sub_8218E788(PPCContext&, uint8_t*);

namespace {
constexpr uint32_t kCurrentThrottles = 0x8285843C;
std::atomic<int> visual_phase{-1};
std::atomic<unsigned> water_full{}, water_basic{}, shadow_submissions{};
std::atomic<unsigned> shadow_maps{};
uint32_t ReadWord(uint8_t* base, uint32_t address) {
  uint32_t word; std::memcpy(&word, base + address, 4); return std::byteswap(word);
}
bool Pointer(uint32_t address) { return address >= 0x10000 && address < 0xC0000000; }
void Sweep(PPCContext& ctx, uint8_t* base) {
  if ((!REXCVAR_GET(halo3mp_video_sweep) && !REXCVAR_GET(halo3mp_video_visual_sweep) && !REXCVAR_GET(halo3mp_video_shadow_sweep)) || rex::cvar::GetFlagByName("input_state_replay").empty()) return;
  if (!Pointer(ctx.r13.u32)) return;
  const uint32_t tls = ReadWord(base, ctx.r13.u32);
  if (!Pointer(tls)) return;
  const uint32_t game = ReadWord(base, tls + 0x80);
  if (!Pointer(game) || base[game + 0x14] != 1) return;
  const std::string_view map(reinterpret_cast<const char*>(base + game + 0x34), 260);
  if (map.find("zanzibar") == std::string_view::npos) return;
  using Clock = std::chrono::steady_clock;
  static const auto start = Clock::now();
  const auto seconds = std::chrono::duration<double>(Clock::now() - start).count();
  if (REXCVAR_GET(halo3mp_video_visual_sweep) || REXCVAR_GET(halo3mp_video_shadow_sweep)) {
    const bool shadow_probe = REXCVAR_GET(halo3mp_video_shadow_sweep);
    const int phase = std::min(shadow_probe ? 6 : 12, int(seconds / 10));
    static int previous = -1;
    if (phase != previous) {
      visual_phase = phase;
      water_full = 0; water_basic = 0; shadow_submissions = 0;
      shadow_maps = 0;
      previous = phase;
      spartan::video::Quality quality{};
      if (shadow_probe) {
        if (phase == 1) quality[0] = 2;
        if (phase == 3) quality[0] = 1;
      } else {
        if (phase == 1 || phase == 9 || phase == 11) quality[0] = 2;
        if (phase == 3) quality[2] = 2;
        if (phase == 5) quality[4] = 2;
        if (phase == 7) quality[4] = 1;
      }
      for (size_t i=0; i<5; ++i) rex::cvar::SetFlagByName(spartan::video::kQualityFlags[i], std::to_string(quality[i]));
      REXLOG_INFO("[video-visual] phase={} seconds={:.3f} isolated=shadows,objects,water camera_stationary=true",phase,seconds);
      if (shadow_probe) REXLOG_INFO("[video-shadow-probe] phase={} diagnostic_shadows_disabled={}",phase,phase==5);
    }
    static int observed = -1;
    if (seconds >= phase * 10 + 3 && observed != phase) {
      observed = phase;
      auto observer = ReadWord(base,tls+0x25c);
      if (Pointer(observer)) {
        auto f = [&](uint32_t at) { return std::bit_cast<float>(ReadWord(base,at)); };
        auto camera = observer+0x1cc;
        REXLOG_INFO("[video-visual] observed={} position={:.3f},{:.3f},{:.3f} forward={:.3f},{:.3f},{:.3f} water_flags={},{}",
          phase,f(camera),f(camera+4),f(camera+8),f(camera+0x28),f(camera+0x2c),f(camera+0x30),base[0x8274CD4A],base[0x8274CD4B]);
        REXLOG_INFO("[video-visual-render] phase={} water_full_submissions={} water_basic_submissions={} shadow_submissions={} shadow_maps={}", phase,water_full.load(),water_basic.load(),shadow_submissions.load(),shadow_maps.load());
      }
    }
    return;
  }
  const int phase = std::min(4, int(seconds / 12));
  static int previous = -1;
  if (phase == previous) return;
  previous = phase;
  if (phase < 3) rex::ui::ApplySurfacePreset(2 - phase);
  if (phase == 3) {
    const char* values[] = {"1", "2", "1", "2", "1"};
    for (size_t i = 0; i < 5; ++i) rex::cvar::SetFlagByName(spartan::video::kQualityFlags[i], values[i]);
    const auto path = REXCVAR_GET(halo3mp_video_sweep_config);
    if (!path.empty()) {
      rex::cvar::SaveConfig(path);
      // Match a fresh launch's precedence for these five controls only.
      // Runtime overrides intentionally outrank config-file values.
      for (const char* flag : spartan::video::kQualityFlags) rex::cvar::ResetToDefault(flag);
      rex::cvar::LoadConfig(path);
      bool match = true;
      for (size_t i = 0; i < 5; ++i) match &= rex::cvar::GetFlagByName(spartan::video::kQualityFlags[i]) == values[i];
      REXLOG_INFO("[video-sweep] saved_custom_reload={}", match);
    }
  }
  if (phase == 4) rex::ui::RestoreVideoDefaults();
  const auto metrics = rex::ui::ReadVideoMetrics();
  REXLOG_INFO("[video-sweep] phase={} seconds={:.2f} map=zanzibar cpu_ms={:.3f} gpu_ms={:.3f}",
              phase, seconds, metrics.cpu_ms, metrics.gpu_ms);
}

// Read-only witnesses of actual native render choices for the opt-in visual
// sweep. Preserve every guest argument and result; no forced LOD or draw result.
REX_HOOK_RAW(sub_82315E70) {
  const int phase = visual_phase.load();
  const uint32_t datum = ctx.r3.u32, model = ctx.r5.u32;
  const double distance = ctx.f1.f64;
  const auto lod = Pointer(model) ? ReadWord(base,model+32) : 0xffffffff;
  const float threshold = Pointer(model) ? std::bit_cast<float>(ReadWord(base,model+12)) : 0;
  __imp__sub_82315E70(ctx,base);
  if (phase >= 0 && lod != 0xffffffff && threshold > 0) {
    static thread_local std::unordered_map<uint32_t,int> reported;
    auto it=reported.find(datum);
    if (it==reported.end() || it->second!=phase) {
      reported[datum]=phase;
      REXLOG_INFO("[video-lod-render] phase={} object={:08X} distance={:.3f} threshold={:.3f} native_lod={}",phase,datum,distance,threshold,ctx.r3.s32);
    }
  }
}
REX_HOOK_RAW(sub_82462F88) {
  if (visual_phase.load() >= 0) {
    if (ctx.r3.u32==3) ++water_full;
    if (ctx.r3.u32==4) ++water_basic;
  }
  __imp__sub_82462F88(ctx,base);
}
REX_HOOK_RAW(sub_8218D770) {
  const int phase=visual_phase.load();
  const auto datum=ctx.r31.u32;
  const double lod=ctx.f2.f64;
  const auto before=shadow_maps.load();
  if (phase >= 0) ++shadow_submissions;
  __imp__sub_8218D770(ctx,base);
  if (phase >= 0 && REXCVAR_GET(halo3mp_video_shadow_sweep)) {
    static thread_local std::unordered_map<uint32_t,int> reported;
    auto it=reported.find(datum);
    if (it==reported.end() || it->second!=phase) {
      reported[datum]=phase;
      REXLOG_INFO("[video-shadow-object] phase={} object={:08X} projected_lod={:.5f} map_rendered={}",phase,datum,lod,shadow_maps.load()!=before);
    }
  }
}
REX_HOOK_RAW(sub_8218E788) {
  if (visual_phase.load() >= 0) ++shadow_maps;
  __imp__sub_8218E788(ctx,base);
}
}

REX_HOOK_RAW(sub_82160F28) {
  // The original chooses the current map's authored ptag and split-screen row.
  __imp__sub_82160F28(ctx, base);
  Sweep(ctx, base);
  spartan::video::Throttles original;
  auto* words = reinterpret_cast<uint8_t*>(&original);
  for (unsigned i = 0; i < sizeof(original); i += 4) {
    const auto word = ReadWord(base, kCurrentThrottles + i);
    std::memcpy(words + i, &word, 4);
  }
  const auto quality = spartan::video::ReadQuality();
  auto result = spartan::video::Apply(original, quality);
  // Explicit opt-in control to locate visible shadow coverage. This is never
  // a user quality level and is excluded from normal launches and saved data.
  if (REXCVAR_GET(halo3mp_video_shadow_sweep) && visual_phase.load()==5) result.shadows=0;
  const auto* output = reinterpret_cast<const uint8_t*>(&result);
  for (unsigned i = 0; i < sizeof(result); i += 4) {
    uint32_t word; std::memcpy(&word, output + i, 4); word = std::byteswap(word);
    std::memcpy(base + kCurrentThrottles + i, &word, 4);
  }
  static spartan::video::Quality previous{-1, -1, -1, -1, -1};
  if (quality != previous) {
    previous = quality;
    REXLOG_INFO("[video-quality] levels={},{},{},{},{} shadows={}->{} shadow_lod={:.3f}->{:.3f} decorators={:.3f}->{:.3f} objects={:.3f}->{:.3f} effects={:.3f}->{:.3f} water={:.3f}->{:.3f} original_exact={}",
      quality[0], quality[1], quality[2], quality[3], quality[4], original.shadows, result.shadows,
      original.shadow_lod, result.shadow_lod, original.decorators, result.decorators,
      original.object_lod, result.object_lod, original.effects, result.effects, original.water, result.water,
      std::memcmp(&original, &result, sizeof(result)) == 0);
  }
}

REX_HOOK_RAW(sub_8221E000) {
  __imp__sub_8221E000(ctx, base);
  // Actual process CPU consumption per render frame, including worker threads;
  // excludes sleeping/pacing. It may exceed wall time when threads run together.
  FILETIME created, exited, kernel, user;
  if (GetProcessTimes(GetCurrentProcess(), &created, &exited, &kernel, &user)) {
    auto value = [](FILETIME time) { return (uint64_t(time.dwHighDateTime) << 32) | time.dwLowDateTime; };
    const uint64_t current = value(kernel) + value(user);
    static uint64_t previous = 0;
    if (previous && current >= previous) rex::ui::PublishVideoCpuFrame(double(current - previous) / 10000.0);
    previous = current;
  }
}
