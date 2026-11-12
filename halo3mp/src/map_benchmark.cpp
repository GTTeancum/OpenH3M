// Developer-only, process-local spawn benchmark. Never writes map assets.
#include "developer_framerate.h"
#include <rex/cvar.h>
#include <rex/logging.h>
#include <rex/hook.h>
#include <rex/ui/presenter.h>
#include <array>
#include <algorithm>
#include <bit>
#include <chrono>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>
#include <windows.h>

REXCVAR_DEFINE_STRING(halo3mp_benchmark_map, "", "Halo3MP/Developer", "Expected internal map name for spawn benchmark");
REXCVAR_DEFINE_STRING(halo3mp_benchmark_variant, "", "Halo3MP/Developer", "Expected saved Forge layout name, if selected");
REXCVAR_DEFINE_STRING(halo3mp_benchmark_points, "", "Halo3MP/Developer", "Repository-local authored spawn coordinate list");
REXCVAR_DEFINE_UINT32(halo3mp_benchmark_seconds, 10, "Halo3MP/Developer", "Seconds measured at each spawn").range(5, 60);
extern "C" void __imp__sub_8232E8B8(PPCContext&, uint8_t*);

namespace {
using Clock = std::chrono::steady_clock;
std::atomic<bool> benchmark_input{false};
std::atomic<int16_t> benchmark_right_x{0};
bool Read(uint8_t* base, uint32_t at, void* out, size_t size) {
  SIZE_T n = 0;
  return at >= 0x10000 && uint64_t(at) + size < 0xE0000000ull &&
      ReadProcessMemory(GetCurrentProcess(), base + at, out, size, &n) && n == size;
}
uint32_t Word(uint8_t* base, uint32_t at) {
  uint32_t value = 0;
  Read(base, at, &value, 4);
  return std::byteswap(value);
}
float Float(uint8_t* base, uint32_t at) { return std::bit_cast<float>(Word(base, at)); }
void Put(uint8_t* base, uint32_t at, float value) {
  auto word = std::byteswap(std::bit_cast<uint32_t>(value));
  std::memcpy(base + at, &word, 4);
}
uint32_t Object(uint8_t* base, uint32_t tls, uint32_t handle) {
  if (handle == 0xFFFFFFFFu) return 0;
  auto table = Word(base, tls + 0xA8);
  if ((handle & 65535) >= Word(base, table + 0x20)) return 0;
  auto header = Word(base, table + 0x44) + (handle & 65535) * 16;
  if ((Word(base, header) >> 16) != (handle >> 16)) return 0;
  return Word(base, header + 12);
}
struct Benchmark {
  bool loaded = false, done = false;
  std::string expected;
  std::vector<std::array<float, 4>> points;
  size_t index = 0;
  uint32_t players_offset = 0, handle = 0xFFFFFFFFu;
  int stage = 0;
  Clock::time_point since{}, sample_start{}, observed{};
  uint64_t first_frame = 0;
  bool position_valid = true;
  std::array<float, 3> camera{};
  void Fail(const char* reason) {
    benchmark_input.store(false);
    REXLOG_ERROR("[map-benchmark] FAILED map={} point={} reason={}", expected, index + 1, reason);
    done = true;
  }
  void Frame(PPCContext& ctx, uint8_t* base) {
    if (done) return;
    if (!loaded) {
      expected = REXCVAR_GET(halo3mp_benchmark_map);
      const auto requested = REXCVAR_GET(halo3mp_benchmark_points);
      if (expected.empty() || requested.empty()) return;
      loaded = true;
      const auto path = std::filesystem::weakly_canonical(requested);
      const auto root = std::filesystem::weakly_canonical("C:/X360/ISOs/H3M/.local/OpenH3M-source/.local/map-benchmarks");
      auto rel = path.lexically_relative(root);
      if (rel.empty() || rel.is_absolute()) { Fail("points_outside_repository"); return; }
      for (const auto& part : rel) if (part == "..") { Fail("points_outside_repository"); return; }
      std::ifstream input(path);
      std::array<float, 4> point{};
      while (input >> point[0] >> point[1] >> point[2] >> point[3]) {
        for (auto v : point) if (!std::isfinite(v)) { Fail("nonfinite_spawn"); return; }
        points.push_back(point);
      }
      if (points.empty() || points.size() > 3) { Fail("invalid_spawn_count"); return; }
    }
    auto* presenter = open_h3m::developer::presenter.load();
    if (!presenter) return;
    const auto tls = Word(base, ctx.r13.u32);
    const auto game = Word(base, tls + 0x80);
    char path[261]{};
    if (!Read(base, game + 0x34, path, 260)) return;
    std::string actual(path);
    const auto slash = actual.find_last_of("/\\");
    const auto leaf = actual.substr(slash == std::string::npos ? 0 : slash + 1);
    if (leaf != expected) return;
    const auto expected_variant = REXCVAR_GET(halo3mp_benchmark_variant);
    if (!expected_variant.empty()) {
      const auto variant = Word(base, tls + 0x64) + 0x78;
      std::array<uint8_t, 32> name{};
      if (!Read(base, variant + 8, name.data(), name.size())) return;
      std::string actual_variant;
      for (unsigned i = 0; i < name.size() && (name[i] || name[i+1]); i += 2)
        actual_variant += name[i] ? '?' : char(name[i+1]);
      if (actual_variant != expected_variant) return;
    }
    if (!players_offset) {
      for (uint32_t offset = 0; offset < 0x800; offset += 4) {
        char label[8]{};
        if (Read(base, Word(base, tls + offset), label, sizeof(label)) &&
            std::memcmp(label, "players\0", 8) == 0) { players_offset = offset; break; }
      }
      if (!players_offset) return;
    }
    const auto players = Word(base, tls + players_offset);
    const auto unit = Word(base, Word(base, players + 0x44) + 0x28);
    const auto body = Object(base, tls, unit);
    if (!body) return;
    const auto now = Clock::now();
    if (stage == 0) {
      const auto& point = points[index];
      PPCContext call = ctx;
      call.r1.u32 -= 0x200;
      const auto scratch = call.r1.u32 + 0x100;
      std::array<uint8_t, 36> saved{};
      std::memcpy(saved.data(), base + scratch, saved.size());
      const std::array<float, 9> pose{point[0], point[1], point[2] + .1f,
          std::cos(point[3]), std::sin(point[3]), 0, 0, 0, 1};
      for (unsigned i = 0; i < pose.size(); ++i) Put(base, scratch + i * 4, pose[i]);
      call.r3.u32 = unit; call.r4.u32 = scratch; call.r5.u32 = scratch + 12;
      call.r6.u32 = scratch + 24; call.r7.u32 = 0; call.r8.u32 = 0;
      __imp__sub_8232E8B8(call, base);
      std::memcpy(base + scratch, saved.data(), saved.size());
      handle = unit; since = now; stage = 1; position_valid = true;
      benchmark_input.store(true);
      REXLOG_INFO("[map-benchmark] placed map={} actual={} point={} target={},{},{} handle={:#x}",
          expected, actual, index + 1, point[0], point[1], point[2], unit);
      if (!expected_variant.empty()) REXLOG_INFO("[map-benchmark] verified variant={}", expected_variant);
      return;
    }
    if (now - observed >= std::chrono::seconds(1)) {
      observed = now;
      const auto observer = Word(base, tls + 0x2CC) + 0x110;
      for (unsigned i = 0; i < 3; ++i) camera[i] = Float(base, observer + i * 4);
      const float dx = camera[0] - points[index][0], dy = camera[1] - points[index][1];
      const float dz = camera[2] - points[index][2];
      if (stage >= 3 && (unit != handle || !std::isfinite(dx + dy + dz) ||
          dx*dx + dy*dy > 2.25f || dz < -.5f || dz > 2.5f)) position_valid = false;
      REXLOG_INFO("[map-benchmark] view map={} point={} camera={},{},{} valid={}",
          expected, index + 1, camera[0], camera[1], camera[2], position_valid);
    }
    const auto observer_result = Word(base, tls + 0x2CC) + 0x110;
    const float actual_yaw = std::atan2(Float(base, observer_result + 0x2C), Float(base, observer_result + 0x28));
    const float yaw_error = std::remainder(points[index][3] - actual_yaw, 6.28318530718f);
    if (stage == 1) {
      if (!std::isfinite(yaw_error)) { Fail("invalid_camera_direction"); return; }
      const bool aligned = std::abs(yaw_error) < .04f;
      benchmark_right_x.store(aligned ? 0 : int16_t(-std::copysign(
          std::clamp(std::abs(yaw_error)*.65f, .4f, .7f), yaw_error)*32767));
      if (now - since > std::chrono::seconds(18) && !aligned) { Fail("camera_alignment_timeout"); return; }
      if (!aligned) return;
    }
    if (stage == 1 && now - since >= std::chrono::seconds(3)) {
      benchmark_right_x.store(0);
      REXLOG_INFO("[map-benchmark] aligned point={} target_yaw={} camera_yaw={}", index+1, points[index][3], actual_yaw);
      open_h3m::developer::capture_done.store(0);
      open_h3m::developer::capture_request.store(int(index + 1));
      stage = 2; since = now;
    } else if (stage == 2) {
      const int captured = open_h3m::developer::capture_done.load();
      if (captured < 0) { Fail("native_capture_failed"); return; }
      if (captured == int(index + 1)) { stage = 3; since = now; }
      else if (now - since > std::chrono::seconds(10)) Fail("native_capture_timeout");
    } else if (stage == 3 && now - since >= std::chrono::seconds(2)) {
      first_frame = presenter->guest_output_frame_count(); sample_start = now; stage = 4;
    } else if (stage == 4 && now - sample_start >= std::chrono::seconds(REXCVAR_GET(halo3mp_benchmark_seconds))) {
      const auto frames = presenter->guest_output_frame_count() - first_frame;
      const double seconds = std::chrono::duration<double>(now - sample_start).count();
      REXLOG_INFO("[map-benchmark] RESULT map={} point={} frames={} seconds={:.6f} fps={:.3f} valid={} camera={},{},{}",
          expected, index + 1, frames, seconds, frames / seconds, position_valid,
          camera[0], camera[1], camera[2]);
      if (++index == points.size()) {
        benchmark_input.store(false);
        done = true; REXLOG_INFO("[map-benchmark] COMPLETE map={} points={}", expected, points.size());
      } else stage = 0;
    }
  }
};
}
void ApplyMapBenchmarkInput(PPCContext& ctx, uint8_t* base, uint32_t user, uint32_t destination) {
  if (!benchmark_input.load() || user != 0 || ctx.r3.u32 != 0 || destination < 0x10000 || destination > 0xDFFFFFE0) return;
  static std::atomic<uint32_t> packets{0};
  const auto packet = std::byteswap(++packets);
  std::memcpy(base + destination, &packet, 4);
  std::memset(base + destination + 4, 0, 12);
  const auto right_x = std::byteswap(uint16_t(benchmark_right_x.load()));
  std::memcpy(base + destination + 12, &right_x, 2);
}
void UpdateMapBenchmark(PPCContext& ctx, uint8_t* base) {
  static Benchmark benchmark;
  benchmark.Frame(ctx, base);
}
