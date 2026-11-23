// Diagnostic hooks for converted-map collision faults (Reach 360 port work). Developer test build only; built
// into a separate executable by tools\reach360-port\debug\build_probe.sh, never the installed game.
// Logs what the two faulting Halo 3 functions receive, to a file named by COLLISION_PROBE_LOG (flushed per line,
// so the last lines survive a fault):
//   821164D8  surface material lookup: record r4 (+24 bsp index, +28 material, +32 model datum). When the model
//             tag's material block (+0x80) is empty, the record is logged and the stock "no material" value is
//             returned instead of faulting, so the run continues and every such contact is listed.
//   82113C48  Havok shape-key callback: object r3 (+0x30 bsp index, +0x34), shape key r4 (type = key >> 29).
#include <rex/hook.h>
#include <rex/logging.h>
#include <atomic>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <mutex>
#include <unordered_map>

namespace collision_probe {
static uint32_t Be32(uint8_t* base, uint32_t a) { uint32_t v; std::memcpy(&v, base + a, 4); return _byteswap_ulong(v); }
static uint16_t Be16(uint8_t* base, uint32_t a) { uint16_t v; std::memcpy(&v, base + a, 2); return _byteswap_ushort(v); }
static std::mutex lock;
static FILE* out = nullptr;
static void Line(const char* fmt, ...) {
  std::lock_guard<std::mutex> g(lock);
  if (!out) { const char* p = std::getenv("COLLISION_PROBE_LOG"); out = std::fopen(p ? p : "collision_probe.txt", "a"); if (!out) return; }
  va_list ap; va_start(ap, fmt); std::vfprintf(out, fmt, ap); va_end(ap); std::fputc('\n', out); std::fflush(out);
}
static constexpr uint32_t kTagTable = 0x827F0F8C;   // lis -32129, +3980 in 821164D8
static constexpr uint32_t kScenario = 0x827F0F88;   // lis -32129, +3976
static constexpr uint32_t kNoMaterial = 0x82A65194; // lis -32090, +20884: the stock default written first
static std::atomic<int> materialLogs{0}, keyLogs{0};
static uint32_t TagAddress(uint8_t* base, uint32_t datum) { uint32_t t = Be32(base, kTagTable); return t ? Be32(base, t + (datum & 0xFFFF) * 8 + 4) : 0; }
}

extern "C" void __imp__sub_821164D8(PPCContext& __restrict, uint8_t*);
extern "C" void __imp__sub_82113C48(PPCContext& __restrict, uint8_t*);

REX_HOOK_RAW(sub_821164D8) {
  using namespace collision_probe;
  const uint32_t rec = ctx.r4.u32;
  const uint32_t datum = Be32(base, rec + 32);
  if (datum != 0xFFFFFFFF) {
    const uint32_t tag = TagAddress(base, datum);
    const uint32_t mats = tag ? Be32(base, tag + 0x80) : 0;
    if (mats == 0) {
      if (materialLogs++ < 40) {
        const uint32_t t = Be32(base, kTagTable);
        Line("material lr=%08llX rec=%08X type=%u bsp=%d material=%d datum=%08X entry=%08X/%08X tag=%08X matcount=%u | rec words %08X %08X %08X %08X %08X %08X %08X %08X %08X %08X",
             (unsigned long long)ctx.lr, rec, Be32(base, rec + 12), (int16_t)Be16(base, rec + 24), (int16_t)Be16(base, rec + 28), datum,
             Be32(base, t + (datum & 0xFFFF) * 8), Be32(base, t + (datum & 0xFFFF) * 8 + 4), tag, tag ? Be32(base, tag + 0x7C) : 0,
             Be32(base, rec), Be32(base, rec + 4), Be32(base, rec + 8), Be32(base, rec + 12), Be32(base, rec + 16), Be32(base, rec + 20),
             Be32(base, rec + 24), Be32(base, rec + 28), Be32(base, rec + 32), Be32(base, rec + 36));
      }
      const uint16_t none = _byteswap_ushort(Be16(base, kNoMaterial));
      std::memcpy(base + ctx.r3.u32, &none, 2);
      return;
    }
  }
  __imp__sub_821164D8(ctx, base);
}

REX_HOOK_RAW(sub_82113C48) {
  using namespace collision_probe;
  const uint32_t obj = ctx.r3.u32, key = ctx.r4.u32;
  if (keyLogs++ < 400) {
    const int32_t bsp = (int32_t)Be32(base, obj + 0x30);
    uint32_t sbspDatum = 0, sbsp = 0, useItems = 0, resDatum = 0;
    const uint32_t scen = Be32(base, kScenario);
    if (scen && bsp >= 0 && bsp < 16) {
      sbspDatum = Be32(base, Be32(base, scen + 24) + bsp * 108 + 12);
      sbsp = TagAddress(base, sbspDatum);
      if (sbsp) { useItems = Be32(base, sbsp + 0x384); resDatum = Be32(base, sbsp + 0x37C); }
    }
    Line("key lr=%08llX obj=%08X key=%08X type=%u idx=%u hi=%u bsp=%d obj34=%08X sbsp=%08X/%08X useItems=%u res=%08X",
         (unsigned long long)ctx.lr, obj, key, key >> 29, key & 0xFFFF, (key >> 16) & 0x1FFF, bsp, Be32(base, obj + 0x34), sbspDatum, sbsp, useItems, resDatum);
  }
  __imp__sub_82113C48(ctx, base);
}

// 82240D00: faults at spawn on converted Reflection 030 (reads a float-looking pointer). Log its inputs and caller.
extern "C" void __imp__sub_82240D00(PPCContext& __restrict, uint8_t*);
REX_HOOK_RAW(sub_82240D00) {
  using namespace collision_probe;
  static std::atomic<int> n{0};
  static bool once = false;
  if (!once) {
    once = true;
    const uint32_t g = Be32(base, 0x828E6404), tagAddr = g ? Be32(base, g + 4) : 0, table = Be32(base, kTagTable);
    uint32_t datum = 0xFFFFFFFF;
    for (uint32_t i = 0; table && i < 0x4000; i++) if (Be32(base, table + i * 8 + 4) == tagAddr) { datum = i; break; }
    Line("fx global 828E6404=%08X tag address=%08X tag index=%04X | +0x10C count=%u ptr=%08X | +0x120 count=%u ptr=%08X",
         g, tagAddr, datum, tagAddr ? Be32(base, tagAddr + 0x10C) : 0, tagAddr ? Be32(base, tagAddr + 0x110) : 0, tagAddr ? Be32(base, tagAddr + 0x120) : 0, tagAddr ? Be32(base, tagAddr + 0x124) : 0);
  }
  if (n++ < 300) Line("fx82240D00 lr=%08llX r3=%08X r4=%08X r5=%08X r6=%08X r7=%08X", (unsigned long long)ctx.lr, ctx.r3.u32, ctx.r4.u32, ctx.r5.u32, ctx.r6.u32, ctx.r7.u32);
  __imp__sub_82240D00(ctx, base);
}

// 82098C60: resolves a tag resource reference (r3 -> {datum, ...}) to its loaded definition (returned in r3, 0 when
// not loaded). Logs each injected resource (index past the stock map's count, COLLISION_PROBE_FIRST_NEW, default
// 4426) once per state, so it shows whether converted geometry / textures / collision are resident.
extern "C" void __imp__sub_82098C60(PPCContext& __restrict, uint8_t*);
REX_HOOK_RAW(sub_82098C60) {
  using namespace collision_probe;
  static const uint32_t firstNew = [] { const char* v = std::getenv("COLLISION_PROBE_FIRST_NEW"); return v ? (uint32_t)std::strtoul(v, nullptr, 0) : 4426u; }();
  static std::mutex m; static std::unordered_map<uint32_t, uint32_t> seen;
  const uint32_t ref = ctx.r3.u32, datum = Be32(base, ref);
  __imp__sub_82098C60(ctx, base);
  if ((datum & 0xFFFF) >= firstNew) {
    const uint32_t got = ctx.r3.u32, state = got ? 1 : 2;
    bool log = false;
    { std::lock_guard<std::mutex> g(m); auto& s = seen[datum]; if ((s & state) == 0) { s |= state; log = seen.size() < 2000; } }
    if (log) Line("resource datum=%08X index=%u -> %08X lr=%08llX", datum, datum & 0xFFFF, got, (unsigned long long)ctx.lr);
  }
}

// 82183020: shader animated-parameter (overlay) evaluation. r4 = the 0x24-byte overlay element
// (+4 input name, +8 range name, +0xC period, +0x10 function data reference, address at +0x1C).
// Logs elements whose function address is not a valid guest pointer, with the caller, before the fault.
extern "C" void __imp__sub_82183020(PPCContext& __restrict, uint8_t*);
REX_HOOK_RAW(sub_82183020) {
  using namespace collision_probe;
  static std::atomic<int> logs{0};
  const uint32_t e = ctx.r4.u32;
  const uint32_t fn = Be32(base, e + 0x1C);
  if (fn < 0x10000 && logs++ < 40)
    Line("overlay lr=%08llX r3=%08X elem=%08X | %08X %08X %08X %08X %08X %08X %08X %08X %08X | before %08X %08X %08X %08X",
         (unsigned long long)ctx.lr, ctx.r3.u32, e, Be32(base, e), Be32(base, e + 4), Be32(base, e + 8), Be32(base, e + 12),
         Be32(base, e + 16), Be32(base, e + 20), Be32(base, e + 24), Be32(base, e + 28), Be32(base, e + 32),
         Be32(base, e - 16), Be32(base, e - 12), Be32(base, e - 8), Be32(base, e - 4));
  __imp__sub_82183020(ctx, base);
}

// 826360E0: virtual call through r3+24 -> object -> vtable+24 (faulted reading guest 0x40 after the full Reach scenario port).
extern "C" void __imp__sub_826360E0(PPCContext& __restrict, uint8_t*);
REX_HOOK_RAW(sub_826360E0) {
  using namespace collision_probe;
  static std::atomic<int> logs{0};
  const uint32_t o = ctx.r3.u32;
  const uint32_t p = o ? Be32(base, o + 24) : 0;
  const uint32_t q = (p && p > 0x10000) ? Be32(base, p) : 0;
  const uint32_t vt = (q && q > 0x10000) ? Be32(base, q) : 0;
  if ((q < 0x10000 || vt < 0x10000) && logs++ < 20)
    Line("826360E0 lr=%08llX r3=%08X r4=%08X [r3+24]=%08X [[r3+24]]=%08X vt=%08X | r3 words %08X %08X %08X %08X %08X %08X %08X %08X",
         (unsigned long long)ctx.lr, o, ctx.r4.u32, p, q, vt, Be32(base, o), Be32(base, o + 4), Be32(base, o + 8), Be32(base, o + 12),
         Be32(base, o + 16), Be32(base, o + 20), Be32(base, o + 24), Be32(base, o + 28));
  __imp__sub_826360E0(ctx, base);
}

// 8215CF30: r3 = small record (byte type, byte, u32) used to index a type table; faulted reading garbage after the
// full Reach scenario port when the benchmark placed the player.
extern "C" void __imp__sub_8215CF30(PPCContext& __restrict, uint8_t*);
REX_HOOK_RAW(sub_8215CF30) {
  using namespace collision_probe;
  static std::atomic<int> logs{0};
  const uint32_t r = ctx.r3.u32;
  const uint8_t type = r ? base[r] : 0xFF;
  static std::mutex seenLock; static std::unordered_map<uint64_t, int> seen;
  bool fresh; { std::lock_guard<std::mutex> g(seenLock); fresh = seen.emplace(((uint64_t)ctx.lr << 16) | (type << 8) | base[r + 1], 1).second; }
  if (fresh && logs++ < 200)
    Line("8215CF30 lr=%08llX r3=%08X type=%u b1=%u w=%08X | words %08X %08X %08X %08X", (unsigned long long)ctx.lr, r, type, base[r + 1],
         Be32(base, r + 4), Be32(base, r), Be32(base, r + 4), Be32(base, r + 8), Be32(base, r + 12));
  __imp__sub_8215CF30(ctx, base);
}

// 825A4230: memcpy (r3 dst, r4 src, r5 size); faulted reading guest 0 after the Reach scenario port placed the player.
extern "C" void __imp__sub_825A4230(PPCContext& __restrict, uint8_t*);
REX_HOOK_RAW(sub_825A4230) {
  using namespace collision_probe;
  static std::atomic<int> logs{0};
  if (ctx.r4.u32 < 0x10000 && ctx.r5.u32 != 0 && logs++ < 20)
    Line("825A4230 memcpy from null: lr=%08llX dst=%08X src=%08X size=%u", (unsigned long long)ctx.lr, ctx.r3.u32, ctx.r4.u32, ctx.r5.u32);
  __imp__sub_825A4230(ctx, base);
}

// 821AA0D8: BSP activation loop. For each active BSP (mask at [lis -32116]+16164 = 0x828C3F24), the scenario's Structure
// BSPs element (+12 datum) -> tag (tag table +4) -> Use Resource Items (+0x384) / Tag Resources datum (+0x37C) -> loaded
// resource pointer through the resource table at ([0x8276B8D0+8] + 0x2AD00 + 800)+84, indexed by the thread's slot
// (r13 -> +116) then +12 -> [resource index]. Logs each step and the table's header words before the original runs.
extern "C" void __imp__sub_821AA0D8(PPCContext& __restrict, uint8_t*);
REX_HOOK_RAW(sub_821AA0D8) {
  using namespace collision_probe;
  static std::atomic<int> logs{0}; static uint32_t lastScnr = 0, lastMask = 0xFFFFFFFF;
  const uint32_t scnr0 = Be32(base, 0x827F0F88), mask0 = Be32(base, 0x828C3F24);
  const bool fresh = scnr0 != lastScnr || mask0 != lastMask; lastScnr = scnr0; lastMask = mask0;
  if (fresh && logs++ < 12) {
    const uint32_t tags = Be32(base, 0x827F0F8C), scnr = scnr0, mask = mask0;
    const uint32_t g8 = Be32(base, 0x8276B8D0 + 8), rm = g8 ? g8 + 0x2AD00 + 800 : 0, tb84 = rm ? Be32(base, rm + 84) : 0;
    const uint32_t tls = Be32(base, ctx.r13.u32), slot = tls ? Be32(base, tls + 116) : 0, tb = tb84 ? Be32(base, tb84 + slot * 4) : 0;
    const uint32_t arr = tb ? Be32(base, tb + 12) : 0;
    Line("821AA0D8 r3=%08X tags=%08X scnr=%08X mask=%08X g8=%08X tb84=%08X slot=%u tb=%08X arr=%08X | tb words %08X %08X %08X %08X %08X %08X %08X %08X",
         ctx.r3.u32, tags, scnr, mask, g8, tb84, slot, tb, arr, tb ? Be32(base, tb) : 0, tb ? Be32(base, tb + 4) : 0, tb ? Be32(base, tb + 8) : 0,
         tb ? Be32(base, tb + 12) : 0, tb ? Be32(base, tb + 16) : 0, tb ? Be32(base, tb + 20) : 0, tb ? Be32(base, tb + 24) : 0, tb ? Be32(base, tb + 28) : 0);
    const uint32_t n = scnr ? Be32(base, scnr + 20) : 0, el = scnr ? Be32(base, scnr + 24) : 0;
    for (uint32_t i = 0; i < n && i < 16; i++) {
      const uint32_t d = Be32(base, el + i * 108 + 12), tag = tags ? Be32(base, tags + (d & 0xFFFF) * 8 + 4) : 0;
      const uint32_t use = tag ? Be32(base, tag + 0x384) : 0, rd = tag ? Be32(base, tag + 0x37C) : 0, gd = tag ? Be32(base, tag + 0xE0 + 0x0) : 0;
      const uint32_t p = (arr && rd != 0xFFFFFFFF) ? Be32(base, arr + (rd & 0xFFFF) * 4) : 0;
      Line("  bsp %u datum=%08X tag=%08X use=%u tagres=%08X -> %08X", i, d, tag, use, rd, p);
    }
    for (uint32_t k = 4400; arr && mask && k < 4930; k += 10) {
      char buf[256]; int o = 0;
      for (uint32_t j = 0; j < 10; j++) o += std::snprintf(buf + o, sizeof(buf) - o, " %08X", Be32(base, arr + (k + j) * 4));
      Line("  res[%u..]%s", k, buf);
    }
  }
  __imp__sub_821AA0D8(ctx, base);
}
