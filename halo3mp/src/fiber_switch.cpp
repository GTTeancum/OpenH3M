// Host-fiber backed override for Halo 3's user-mode job-system context switch.
//
// The guest routine at 0x825B8320 (reached via the one-instruction thunk
// sub_825B5FE0 = `b 0x825B8320`) is a fiber switch:
//
//   1. read the current context buffer from TLS: *(r13+256) -> +356
//   2. save r1, r14-r31, cr, lr, f14-f31, VMX into it
//   3. restore the same set from the *incoming* context in r3, including
//      `mtlr r7` where r7 = lwz r7,28(r3)  -- the incoming fiber's saved lr
//   4. install the new context pointer, load the new stack pointer, and
//      tail-call KeSetCurrentStackPointers (xboxkrnl ordinal 0x9B)
//
// On hardware the final return uses the *restored* lr, resuming the incoming
// fiber's call chain. ReXGlue compiles every guest function to a host C
// function and `blr` to `return`, so ctx.lr is inert data: the host would
// return to the original C caller while ctx held the incoming fiber's register
// file. That mismatch produced the null store in sub_822C50B0.
//
// This override gives every guest context its own host fiber so host control
// flow follows the guest. Suspended register state is kept host-side (a whole
// PPCContext copy); the guest buffer is only read when a context is resumed for
// the first time, because the game initialises it when creating a fiber.

#include <rex/cvar.h>
#include <rex/hook.h>
#include <rex/logging.h>
#include <rex/ppc/func.h>

#ifdef _WIN32
#include <windows.h>
#endif

#include <atomic>
#include <cstring>
#include <mutex>
#include <unordered_map>

REXCVAR_DEFINE_BOOL(halo3mp_fiber_trace, false, "Halo3MP/Fiber",
                    "Log every Halo 3 job-system fiber transition");
REXCVAR_DEFINE_UINT32(halo3mp_fiber_summary_interval, 1000, "Halo3MP/Fiber",
                      "Log one Halo 3 fiber summary every N switches; 0 disables summaries");

extern "C" void __imp__KeSetCurrentStackPointers(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void __imp__sub_825B8320(PPCContext& __restrict ctx, uint8_t* base);

namespace {

// --- guest context buffer layout (from the routine's own save/restore) ------
constexpr uint32_t kOffStackAllocBase = 4;
constexpr uint32_t kOffStackBase = 8;
constexpr uint32_t kOffStackLimit = 12;
constexpr uint32_t kOffLr = 28;
constexpr uint32_t kOffR1 = 48;
constexpr uint32_t kOffGpr14 = 152;  // r14..r31, stride 8
constexpr uint32_t kOffCr = 296;
constexpr uint32_t kOffFpr14 = 424;  // f14..f31, stride 8

// KPCR / KTHREAD
constexpr uint32_t kPcrCurrentThread = 256;  // r13 + 256 -> KTHREAD
constexpr uint32_t kThreadContextPtr = 356;  // KTHREAD + 356 -> current context

constexpr uint32_t kGuestAddressLimit = 0xC0000000u;

inline bool PlausibleGuestPtr(uint32_t a) { return a >= 0x1000u && a < kGuestAddressLimit; }

inline uint32_t Load32(uint8_t* base, uint32_t addr) {
  uint32_t v;
  std::memcpy(&v, base + addr, sizeof(v));
  return _byteswap_ulong(v);
}

inline uint64_t Load64(uint8_t* base, uint32_t addr) {
  uint64_t v;
  std::memcpy(&v, base + addr, sizeof(v));
  return _byteswap_uint64(v);
}

inline void Store32(uint8_t* base, uint32_t addr, uint32_t value) {
  const uint32_t v = _byteswap_ulong(value);
  std::memcpy(base + addr, &v, sizeof(v));
}

inline void Store64(uint8_t* base, uint32_t addr, uint64_t value) {
  const uint64_t v = _byteswap_uint64(value);
  std::memcpy(base + addr, &v, sizeof(v));
}

struct GuestFiber {
  void* host_fiber = nullptr;
  uint32_t ctx_addr = 0;
  bool is_root = false;
  PPCContext saved{};
  PPCContext* live = nullptr;
  uint8_t* base = nullptr;
  // lr written into the guest buffer when this context was last suspended. If
  // the guest buffer's lr no longer matches, the scheduler re-dispatched this
  // context to a new job and the parked host fiber is stale.
  uint32_t suspended_lr = 0;
  bool has_suspended_lr = false;
};

std::mutex g_mutex;
std::unordered_map<uint32_t, GuestFiber*> g_fibers;
std::atomic<uint64_t> g_switches{0};
std::atomic<uint64_t> g_restarts{0};
std::atomic<uint64_t> g_created{0};
std::atomic<uint64_t> g_entries{0};
std::atomic<uint64_t> g_fallbacks{0};

thread_local GuestFiber* t_current = nullptr;
thread_local GuestFiber* t_root = nullptr;

bool FiberTraceEnabled() { return REXCVAR_GET(halo3mp_fiber_trace); }

void LogFiberSummaryIfNeeded(uint64_t switches) {
  const uint32_t interval = REXCVAR_GET(halo3mp_fiber_summary_interval);
  if (!interval || (switches % interval) != 0) {
    return;
  }
  REXLOG_INFO("[fiber] summary switches={} entries={} created={} restarts={} fallbacks={}",
              switches, g_entries.load(std::memory_order_relaxed),
              g_created.load(std::memory_order_relaxed),
              g_restarts.load(std::memory_order_relaxed),
              g_fallbacks.load(std::memory_order_relaxed));
}

GuestFiber* FiberFor(uint32_t ctx_addr) {
  std::lock_guard<std::mutex> lock(g_mutex);
  auto it = g_fibers.find(ctx_addr);
  if (it != g_fibers.end()) {
    return it->second;
  }
  auto* f = new GuestFiber();
  f->ctx_addr = ctx_addr;
  g_fibers.emplace(ctx_addr, f);
  return f;
}

// Seed the live register file from a context buffer the game has initialised.
void LoadInitialContext(PPCContext& ctx, uint8_t* base, uint32_t buf) {
  ctx.r1.u64 = Load64(base, buf + kOffR1);
  ctx.lr = Load32(base, buf + kOffLr);

  PPCRegister* gpr[] = {&ctx.r14, &ctx.r15, &ctx.r16, &ctx.r17, &ctx.r18, &ctx.r19,
                        &ctx.r20, &ctx.r21, &ctx.r22, &ctx.r23, &ctx.r24, &ctx.r25,
                        &ctx.r26, &ctx.r27, &ctx.r28, &ctx.r29, &ctx.r30, &ctx.r31};
  for (uint32_t i = 0; i < 18; ++i) {
    gpr[i]->u64 = Load64(base, buf + kOffGpr14 + i * 8);
  }

  PPCRegister* fpr[] = {&ctx.f14, &ctx.f15, &ctx.f16, &ctx.f17, &ctx.f18, &ctx.f19,
                        &ctx.f20, &ctx.f21, &ctx.f22, &ctx.f23, &ctx.f24, &ctx.f25,
                        &ctx.f26, &ctx.f27, &ctx.f28, &ctx.f29, &ctx.f30, &ctx.f31};
  for (uint32_t i = 0; i < 18; ++i) {
    fpr[i]->u64 = Load64(base, buf + kOffFpr14 + i * 8);
  }

  const uint32_t cr = Load32(base, buf + kOffCr);
  PPCCRRegister* crf[] = {&ctx.cr0, &ctx.cr1, &ctx.cr2, &ctx.cr3,
                          &ctx.cr4, &ctx.cr5, &ctx.cr6, &ctx.cr7};
  for (uint32_t i = 0; i < 8; ++i) {
    crf[i]->set_raw((cr >> (28 - i * 4)) & 0xF);
  }
}

// Mirror of the routine's save half. The suspended register file is kept
// host-side, but the guest scheduler can inspect a parked context's saved r1 /
// lr / non-volatiles, so keep the guest-visible buffer coherent too.
void SaveGuestContext(const PPCContext& ctx, uint8_t* base, uint32_t buf) {
  Store64(base, buf + kOffR1, ctx.r1.u64);
  Store32(base, buf + kOffLr, static_cast<uint32_t>(ctx.lr));

  const PPCRegister* gpr[] = {&ctx.r14, &ctx.r15, &ctx.r16, &ctx.r17, &ctx.r18, &ctx.r19,
                              &ctx.r20, &ctx.r21, &ctx.r22, &ctx.r23, &ctx.r24, &ctx.r25,
                              &ctx.r26, &ctx.r27, &ctx.r28, &ctx.r29, &ctx.r30, &ctx.r31};
  for (uint32_t i = 0; i < 18; ++i) {
    Store64(base, buf + kOffGpr14 + i * 8, gpr[i]->u64);
  }

  const PPCRegister* fpr[] = {&ctx.f14, &ctx.f15, &ctx.f16, &ctx.f17, &ctx.f18, &ctx.f19,
                              &ctx.f20, &ctx.f21, &ctx.f22, &ctx.f23, &ctx.f24, &ctx.f25,
                              &ctx.f26, &ctx.f27, &ctx.f28, &ctx.f29, &ctx.f30, &ctx.f31};
  for (uint32_t i = 0; i < 18; ++i) {
    Store64(base, buf + kOffFpr14 + i * 8, fpr[i]->u64);
  }

  const PPCCRRegister* crf[] = {&ctx.cr0, &ctx.cr1, &ctx.cr2, &ctx.cr3,
                                &ctx.cr4, &ctx.cr5, &ctx.cr6, &ctx.cr7};
  uint32_t cr = 0;
  for (uint32_t i = 0; i < 8; ++i) {
    cr |= (crf[i]->raw() & 0xF) << (28 - i * 4);
  }
  Store32(base, buf + kOffCr, cr);
}

// Mirror of the routine's tail: install the incoming context as current and
// hand the kernel its stack bounds. KeSetCurrentStackPointers reads its
// arguments from the context passed to it but writes r1 on the *live* thread
// context, so nothing is copied back here.
void ApplyStackPointers(PPCContext& ctx, uint8_t* base, uint32_t thread_ptr, uint32_t buf) {
  Store32(base, thread_ptr + kThreadContextPtr, buf);

  PPCContext call = ctx;
  call.r3.u64 = Load64(base, buf + kOffR1);
  call.r4.u64 = thread_ptr;
  call.r5.u64 = Load32(base, buf + kOffStackAllocBase);
  call.r6.u64 = Load32(base, buf + kOffStackBase);
  call.r7.u64 = Load32(base, buf + kOffStackLimit);
  __imp__KeSetCurrentStackPointers(call, base);
}

void CALLBACK GuestFiberEntry(void* param) {
  auto* self = static_cast<GuestFiber*>(param);
  PPCContext& ctx = *self->live;
  uint8_t* base = self->base;

  LoadInitialContext(ctx, base, self->ctx_addr);
  const uint32_t entry = static_cast<uint32_t>(ctx.lr);

  ++g_entries;
  if (FiberTraceEnabled()) {
    REXLOG_INFO(
        "[fiber] start ctx {:#010x} pc {:#010x} sp {:#010x} r31={:#010x} r30={:#010x} "
        "r14={:#010x} cr={:#x}",
        self->ctx_addr, entry, ctx.r1.u32, ctx.r31.u32, ctx.r30.u32, ctx.r14.u32,
        ctx.cr0.raw());
  }

  if (auto* fn = rex::runtime::ResolveIndirectFunction(entry)) {
    fn(ctx, base);
    REXLOG_WARN("[fiber] context {:#010x} returned from pc {:#010x}", self->ctx_addr, entry);
  } else {
    REXLOG_ERROR("[fiber] context {:#010x}: unresolved entry pc {:#010x}", self->ctx_addr, entry);
  }

  if (t_root && t_root->host_fiber) {
    t_current = t_root;
    SwitchToFiber(t_root->host_fiber);
  }
}

}  // namespace

REX_HOOK_RAW(sub_825B8320) {
#ifndef _WIN32
  __imp__sub_825B8320(ctx, base);
#else
  const uint32_t r13 = ctx.r13.u32;
  const uint32_t new_addr = ctx.r3.u32;

  if (!PlausibleGuestPtr(r13) || !PlausibleGuestPtr(new_addr)) {
    ++g_fallbacks;
    REXLOG_WARN("[fiber] implausible switch (r13={:#010x} r3={:#010x}); using recompiled path", r13,
                new_addr);
    __imp__sub_825B8320(ctx, base);
    return;
  }

  const uint32_t thread_ptr = Load32(base, r13 + kPcrCurrentThread);
  if (!PlausibleGuestPtr(thread_ptr)) {
    ++g_fallbacks;
    REXLOG_WARN("[fiber] bad KTHREAD {:#010x}; using recompiled path", thread_ptr);
    __imp__sub_825B8320(ctx, base);
    return;
  }

  const uint32_t cur_addr = Load32(base, thread_ptr + kThreadContextPtr);
  const uint64_t switch_count = ++g_switches;
  if (FiberTraceEnabled()) {
    REXLOG_INFO("[fiber] switch {:#010x} -> {:#010x} (thread {:#010x})", cur_addr, new_addr,
                thread_ptr);
  }
  LogFiberSummaryIfNeeded(switch_count);

  if (!PlausibleGuestPtr(cur_addr)) {
    ++g_fallbacks;
    REXLOG_WARN("[fiber] bad current context {:#010x}; using recompiled path", cur_addr);
    __imp__sub_825B8320(ctx, base);
    return;
  }

  if (new_addr == cur_addr) {
    ApplyStackPointers(ctx, base, thread_ptr, new_addr);
    return;
  }

  // Adopt the calling thread's stack as a fiber the first time through.
  if (!t_root) {
    void* root = ConvertThreadToFiber(nullptr);
    if (!root) {
      root = GetCurrentFiber();
    }
    auto* rf = FiberFor(cur_addr);
    rf->host_fiber = root;
    rf->is_root = true;
    rf->live = &ctx;
    rf->base = base;
    t_root = rf;
    t_current = rf;
    if (FiberTraceEnabled()) {
      REXLOG_INFO("[fiber] adopted thread stack as root fiber for context {:#010x}", cur_addr);
    }
  }

  GuestFiber* self = t_current ? t_current : FiberFor(cur_addr);
  self->live = &ctx;
  self->base = base;
  self->saved = ctx;
  SaveGuestContext(ctx, base, cur_addr);
  self->suspended_lr = static_cast<uint32_t>(ctx.lr);
  self->has_suspended_lr = true;

  GuestFiber* target = FiberFor(new_addr);
  target->live = &ctx;
  target->base = base;

  // If the guest re-dispatched this context, the parked host fiber is stale:
  // resuming it would return onto the job's terminal `bl <fatal>`.
  if (target->host_fiber && !target->is_root && target->has_suspended_lr) {
    const uint32_t buf_lr = Load32(base, new_addr + kOffLr);
    if (buf_lr != target->suspended_lr) {
      ++g_restarts;
      if (FiberTraceEnabled()) {
        REXLOG_INFO("[fiber] ctx {:#010x} re-dispatched (lr {:#010x} -> {:#010x}); restarting",
                    new_addr, target->suspended_lr, buf_lr);
      }
      DeleteFiber(target->host_fiber);
      target->host_fiber = nullptr;
      target->has_suspended_lr = false;
    }
  }

  ApplyStackPointers(ctx, base, thread_ptr, new_addr);

  if (!target->host_fiber) {
    target->host_fiber = CreateFiber(0, &GuestFiberEntry, target);
    if (!target->host_fiber) {
      REXLOG_ERROR("[fiber] CreateFiber failed for context {:#010x}", new_addr);
      return;
    }
    ++g_created;
    if (FiberTraceEnabled()) {
      REXLOG_INFO("[fiber] created host fiber for context {:#010x}", new_addr);
    }
  }

  t_current = target;
  SwitchToFiber(target->host_fiber);

  // Resumed: restore our register file.
  t_current = self;
  ctx = self->saved;
#endif
}

// --- diagnostic: guest bug-check path ---------------------------------------
// sub_825A49B0 tail-calls KeBugCheck (xboxkrnl ordinal 0x52). KeBugCheckEx
// flushes stdout but not the file logger, so its "*** STOP" line is lost in the
// buffer when debug::Break() kills the process. Log the arguments here and
// flush before handing over.
extern "C" void __imp__sub_825A49B0(PPCContext& __restrict ctx, uint8_t* base);

REX_HOOK_RAW(sub_825A49B0) {
  REXLOG_CRITICAL(
      "[bugcheck] guest KeBugCheck path: r3={:#x} r4={:#x} r5={:#x} r6={:#x} r7={:#x} lr={:#x}",
      ctx.r3.u32, ctx.r4.u32, ctx.r5.u32, ctx.r6.u32, ctx.r7.u32,
      static_cast<uint32_t>(ctx.lr));
  if (auto l = ::rex::GetLogger()) {
    l->flush();
  }
  // Suppressing this (returning instead of forwarding) was tried and is worse:
  // the title continues with broken invariants and dies in an access violation
  // inside the fiber entry instead of stopping cleanly here. Forward it.
  __imp__sub_825A49B0(ctx, base);
}

// --- diagnostic: GPU vblank interrupt delivery ------------------------------
// The game registers 0x821A4F50 via VdSetGraphicsInterruptCallback. If the
// guest never sees vblank the job system's wait loop times out, which is the
// bug check above. Count deliveries to confirm.
extern "C" void __imp__sub_821A4F50(PPCContext& __restrict ctx, uint8_t* base);

REX_HOOK_RAW(sub_821A4F50) {
  static std::atomic<uint32_t> hits{0};
  const uint32_t n = ++hits;
  if (n <= 3 || (n % 60) == 0) {
    REXLOG_INFO("[vblank] guest interrupt callback #{} (source={:#x} data={:#x})", n, ctx.r3.u32,
                ctx.r4.u32);
  }
  __imp__sub_821A4F50(ctx, base);
}

// --- diagnostic: fiber job argument -----------------------------------------
// sub_825B5FF0 passes the job argument from *(current_context + 0). If that
// slot is not populated the decoder at sub_8232C6F8 reads garbage and asserts.
extern "C" void __imp__sub_8232C6F8(PPCContext& __restrict ctx, uint8_t* base);

REX_HOOK_RAW(sub_8232C6F8) {
  static std::atomic<uint32_t> hits{0};
  const uint32_t n = ++hits;
  if (n <= 4) {
    const uint32_t arg = ctx.r3.u32;
    uint32_t w0 = 0, w8 = 0;
    if (arg >= 0x1000u && arg < 0xC0000000u) {
      std::memcpy(&w0, base + arg, 4);
      std::memcpy(&w8, base + arg + 8, 4);
      w0 = _byteswap_ulong(w0);
      w8 = _byteswap_ulong(w8);
    }
    REXLOG_INFO("[job] decoder #{} arg(r3)={:#010x} [0]={:#010x} [8]={:#010x}", n, arg, w0, w8);
    if (auto l = ::rex::GetLogger()) {
      l->flush();
    }
  }
  __imp__sub_8232C6F8(ctx, base);
}
