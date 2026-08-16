p = r"C:\Programming\GitHub\Halo-3-MP\halo3mp\src\fiber_switch.cpp"
s = open(p, encoding="utf-8").read()

# 1) add a Store64 helper next to Store32
anchor_store = """inline void Store32(uint8_t* base, uint32_t addr, uint32_t value) {
  const uint32_t v = _byteswap_ulong(value);
  std::memcpy(base + addr, &v, sizeof(v));
}
"""
add_store = anchor_store + """
inline void Store64(uint8_t* base, uint32_t addr, uint64_t value) {
  const uint64_t v = _byteswap_uint64(value);
  std::memcpy(base + addr, &v, sizeof(v));
}
"""
assert anchor_store in s, "Store32 anchor missing"
s = s.replace(anchor_store, add_store, 1)

# 2) add SaveGuestContext mirroring the guest routine's own save, before
#    the ApplyStackPointers comment block
anchor_apply = "// Mirror of the routine's tail: install the incoming context as current and"
save_fn = """// Mirror of the routine's save half. The suspended register file is kept
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

""" + anchor_apply
assert anchor_apply in s, "ApplyStackPointers anchor missing"
s = s.replace(anchor_apply, save_fn, 1)

# 3) call it when suspending
anchor_suspend = "  self->saved = ctx;\n"
new_suspend = "  self->saved = ctx;\n  SaveGuestContext(ctx, base, cur_addr);\n"
assert anchor_suspend in s, "suspend anchor missing"
s = s.replace(anchor_suspend, new_suspend, 1)

open(p, "w", encoding="utf-8").write(s)
print("patched fiber_switch.cpp with guest-visible context save")
