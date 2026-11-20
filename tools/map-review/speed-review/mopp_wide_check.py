"""Check 0x23-0x25 (16-bit split) semantics separately: count validated terminals beneath one, both orientations."""
import sys, re, collections
from pathlib import Path
src = Path(__file__).with_name('mopp_validate.py').read_text()
# variant: only the wide split uses the swapped flag; narrow split fixed to validated orientation
src = src.replace("left_hi, right_lo = (b, a) if split_swapped else (a, b)\n                rlo, rhi = list(lo), list(hi); rlo[ax] = max(rlo[ax], right_lo)\n                stack.append((at + 4 + off", "left_hi, right_lo = (a, b)\n                rlo, rhi = list(lo), list(hi); rlo[ax] = max(rlo[ax], right_lo)\n                stack.append((at + 4 + off")
src = src.replace("stack.append((at + 7 + ro, base, rlo, rhi, resc, exo))", "stack.append((at + 7 + ro, base, rlo, rhi, resc, 'wide'))")
src = src.replace("hi[ax] = min(hi[ax], left_hi); at += 7 + lo_off", "hi[ax] = min(hi[ax], left_hi); exo = 'wide'; at += 7 + lo_off")
src = src.replace("tally[which, swapped, name, 'ok' if ok else 'FAIL'] += 1", "tally[which, swapped, name, 'ok' if ok else 'FAIL', 'under-wide' if exo == 'wide' else 'other'] += 1")
assert src.count("'wide'") >= 3
exec(compile(src, 'variant', 'exec'))
