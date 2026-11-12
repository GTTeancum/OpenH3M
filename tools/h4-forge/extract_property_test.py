"""Extract original property encoders for isolated bit-encoding tests."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[2]
R=ROOT/'work/h4-forge-research'
parts=['#include "forge_original.h"','#undef DEFINE_REX_FUNC','#define DEFINE_REX_FUNC(name) void name(PPCContext& ctx,uint8_t* base)','namespace property_test {','void sub_822E6870(PPCContext&,uint8_t*);']
records={}
for a,n in {'823B5938':164,'823CACB0':175,'823CAD80':209,'822F0788':63}.items():
 text=(R/f'generated/halo4_recomp.{n}.cpp').read_text();marker=f'DEFINE_REX_FUNC(sub_{a}) {{'
 body=marker+text.split(marker,1)[1].split('DEFINE_REX_FUNC(',1)[0].rstrip()
 parts.append(body);records[a]=hashlib.sha256(body.encode()).hexdigest()
parts.append('}')
(R/'isolated/property_original.cpp').write_text('\n'.join(parts)+'\n')
(R/'isolated/property-original-hashes.json').write_text(json.dumps(records,indent=2)+'\n')
