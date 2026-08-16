"""Consolidate: keep the real fixes, revert the hacks that make things worse.

- fiber override, campaign.map, cache partitions, import resolution: KEEP
- guest bug-check suppression: REVERT (turns a clean diagnosable stop into an AV)
- SDK non-fatal kernel breaks: flip default back to fatal, opt-in via env
"""

# 1) restore forwarding in the guest bugcheck hook
p = r"C:\Programming\GitHub\Halo-3-MP\halo3mp\src\fiber_switch.cpp"
s = open(p, encoding="utf-8").read()

old = """  // Executive decision: do NOT forward to the recompiled body, which tail-calls
  // KeBugCheck and kills the process. This is a wait-loop timeout assert (see
  // sub_8232C6F8); swallowing it lets the title continue past a subsystem that
  // never signals. Returning 0 in r3 mimics "handled".
  static bool warned = false;
  if (!warned) {
    warned = true;
    REXLOG_CRITICAL("[bugcheck] suppressed guest bug check; continuing (see BUILD.md)");
    if (auto l2 = ::rex::GetLogger()) {
      l2->flush();
    }
  }
  ctx.r3.u64 = 0;
}"""

new = """  // Suppressing this (returning instead of forwarding) was tried and is worse:
  // the title continues with broken invariants and dies in an access violation
  // inside the fiber entry instead of stopping cleanly here. Forward it.
  __imp__sub_825A49B0(ctx, base);
}"""

assert old in s, "bugcheck suppression anchor missing"
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(s)
print("reverted bug-check suppression")

# 2) SDK: default back to fatal, non-fatal opt-in
q = r"C:\Programming\GitHub\Halo-3-MP\work\rexglue-sdk\src\kernel\xboxkrnl\xboxkrnl_debug.cpp"
t = open(q, encoding="utf-8").read()

old2 = """  static const bool fatal = [] {
    const char* v = std::getenv("REXGLUE_FATAL_BREAK");
    return v && v[0] == '1';
  }();"""
new2 = """  static const bool fatal = [] {
    const char* v = std::getenv("REXGLUE_NONFATAL_BREAK");
    return !(v && v[0] == '1');  // fatal by default; opt in to continuing
  }();"""
assert old2 in t, "sdk break-policy anchor missing"
t = t.replace(old2, new2, 1)
t = t.replace("(set REXGLUE_FATAL_BREAK=1 to trap)", "(set REXGLUE_NONFATAL_BREAK=1 to continue)")
open(q, "w", encoding="utf-8").write(t)
print("SDK kernel breaks default back to fatal (opt-in via REXGLUE_NONFATAL_BREAK=1)")
