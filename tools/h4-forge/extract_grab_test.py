"""Extract original grab/reset/clamp; world services remain explicit test adapters."""
from pathlib import Path
import re,json,hashlib
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'work/h4-forge-research'
bodies={}
for a,n in {'8244B518':127,'8244A6A8':262,'8228ACE8':175,'82265E28':185,'82265C30':43,'822C1398':53,'8226BFC0':46,'8244A7D0':105,'822C5470':204,'82232AC8':195,'82265430':211,'821DF530':201,'8222AAD0':290,'82449A60':173,'82368CE0':181,'82450E10':43,'82449ED8':101,'82452738':104,'82451500':144,'82451250':11}.items():
 text=(R/f'generated/halo4_recomp.{n}.cpp').read_text();marker=f'DEFINE_REX_FUNC(sub_{a}) {{'
 bodies['sub_'+a]=marker+text.split(marker,1)[1].split('DEFINE_REX_FUNC(',1)[0].rstrip()
for name,number in {'__savegprlr_28':162,'__restgprlr_28':55,'__savegprlr_29':65,'__restgprlr_29':54,'__savegprlr_24':177,'__restgprlr_24':123,'__savegprlr_21':18,'__restgprlr_21':110,'__savegprlr_25':146,'__restgprlr_25':70}.items():
 text=(R/f'generated/halo4_recomp.{number}.cpp').read_text()
 marker=f'DEFINE_REX_FUNC({name}) {{'
 if marker not in text: raise ValueError(name)
 tail=text.split(marker,1)[1];end=tail.find('DEFINE_REX_FUNC(')
 bodies[name]=marker+tail[:end if end>=0 else tail.rfind('\n}')].rstrip()
calls=set()
for b in bodies.values():calls.update(re.findall(r'\b((?:sub_|__save|__rest)\w+)\(ctx, base\)',b))
parts=['#include "forge_original.h"','#undef DEFINE_REX_FUNC','#define DEFINE_REX_FUNC(name) void name(PPCContext& ctx,uint8_t* base)','namespace grab_test {']
parts += [f'void {n}(PPCContext&,uint8_t*);' for n in sorted(calls|set(bodies))]
parts += list(bodies.values());parts.append('}')
(R/'isolated/grab_original.cpp').write_text('\n'.join(parts)+'\n')
(R/'isolated/grab-original-hashes.json').write_text(json.dumps({n:hashlib.sha256(b.encode()).hexdigest() for n,b in bodies.items()},indent=2)+'\n')
print('External adapters:', ','.join(sorted(calls-set(bodies))))
