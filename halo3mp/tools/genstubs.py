"""Emit cross-module (guest->guest) import thunk bodies.

ReXGlue v0.10 resolves xboxkrnl/xam imports via the host export resolver but
leaves guest-DLL -> guest-DLL function imports unresolved: codegen declares the
thunks and emits no bodies. This resolves each thunk to the real WavesLibDLL
export address (via the XEX export table) and emits a body that dispatches
there through the SDK's own indirect-call path.

REX_CALL_INDIRECT_FUNC bounds-checks the target against the *calling* module's
code range; a WavesLibDLL address is outside l360/q10, so it falls through to
rex::runtime::ResolveIndirectFunction, which queries the global dispatcher
across every loaded module. That is exactly the behaviour we want.
"""
import re, glob, os, sys
import resolve_imports as ri

PROJ = r"C:\Programming\GitHub\Halo-3-MP\halo3mp"
GEN = os.path.join(PROJ, "generated")
SRC = os.path.join(PROJ, "src")
G = ri.G

MODULES = {
    "l360": os.path.join(G, "waves", "L360.dll"),
    "q10": os.path.join(G, "waves", "Q10.dll"),
}
EXPORTER = os.path.join(G, "WavesLibDLL.dll")


def undefined_for(mod):
    d = os.path.join(GEN, mod)
    declared = set(re.findall(r"DECLARE_REX_FUNC\((sub_[0-9A-Fa-f]+)\)",
                              open(os.path.join(d, "halo3mp_funcs.h")).read()))
    defined = set()
    for f in glob.glob(os.path.join(d, "halo3mp_recomp.*.cpp")):
        defined |= set(re.findall(r"DEFINE_REX_FUNC\((sub_[0-9A-Fa-f]+)\)",
                                  open(f, encoding="utf-8", errors="replace").read()))
    return sorted(declared - defined, key=lambda s: int(s[4:], 16))


HEADER = """// Cross-module (guest->guest) import thunks for %(mod)s.  GENERATED - do not edit.
//
// ReXGlue v0.10 does not resolve guest DLL -> guest DLL function imports, so
// codegen declares these %(n)d WavesLibDLL thunks without emitting bodies.
// Each is resolved here to its real export address via the XEX export table
// (security_info+0x160) and dispatched through the SDK's indirect-call path.
//
// Regenerate with tools/genstubs.py after any codegen run.

#include "halo3mp_funcs.h"

"""

REAL = """// ordinal %(ord)d
DEFINE_REX_FUNC(%(sym)s) {
\tREX_FUNC_PROLOGUE();
\tREX_CALL_INDIRECT_FUNC(0x%(target)08X);
\treturn;
}

"""

FALLBACK = """// UNRESOLVED - no matching WavesLibDLL export; returns 0.
DEFINE_REX_FUNC(%(sym)s) {
\tREX_FUNC_PROLOGUE();
\tctx.r3.u64 = 0;
\treturn;
}

"""

if __name__ == "__main__":
    _, exports, msg = ri.export_map(EXPORTER)
    if not exports:
        print("FATAL: no exports resolved (%s)" % msg)
        sys.exit(1)

    total_real = total_fb = 0
    for mod, path in MODULES.items():
        miss = undefined_for(mod)
        _, pairs = ri.import_pairs(path, "WavesLibDLL.dll")
        out = os.path.join(SRC, "%s_import_stubs.cpp" % mod)
        nreal = nfb = 0
        with open(out, "w", encoding="utf-8") as f:
            f.write(HEADER % {"mod": mod, "n": len(miss)})
            for sym in miss:
                addr = int(sym[4:], 16)
                ordinal = pairs.get(addr)
                target = exports.get(ordinal) if ordinal is not None else None
                if target:
                    f.write(REAL % {"sym": sym, "ord": ordinal, "target": target})
                    nreal += 1
                else:
                    f.write(FALLBACK % {"sym": sym})
                    nfb += 1
        total_real += nreal
        total_fb += nfb
        print("%-5s %3d thunks: %3d resolved, %d fallback -> %s"
              % (mod, len(miss), nreal, nfb, os.path.basename(out)))
    print("total: %d resolved, %d fallback" % (total_real, total_fb))
