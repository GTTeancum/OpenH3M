"""Extract original H3 packet chain and H4 magnet predicate, unchanged."""
from pathlib import Path
import re,hashlib,json
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'work/h4-forge-research'
parts=['#include "forge_original.h"','#undef DEFINE_REX_FUNC','#define DEFINE_REX_FUNC(name) void name(PPCContext& ctx,uint8_t* base)'];records={}
for namespace,folder,prefix,locations in [
 ('h3_input',ROOT/'halo3mp/generated/default','halo3mp_recomp',{'820B8608':51,'821EC0E0':95,'820B8510':64,'__savegprlr_26':87,'__restgprlr_26':61,'__savegprlr_29':67,'__restgprlr_29':56}),
 ('h4_input',R/'generated','halo4_recomp',{'82582178':101,'82361880':56,'82221B08':93,'822562A8':180,'__savegprlr_27':248,'__restgprlr_27':280,'__savegprlr_22':16,'__restgprlr_22':63,'__savefpr_14':279,'__restfpr_14':48,'823619F8':276,'8229D0F8':192,'__savegprlr_23':9,'__restgprlr_23':85,'8244EED8':70,'8244A118':49,'82282728':163,'__savegprlr_28':162,'__restgprlr_28':55,'__savegprlr_29':65,'__restgprlr_29':54})]:
 bodies={}
 for a,n in locations.items():
  name=a if a.startswith('__') else 'sub_'+a
  text=(folder/f'{prefix}.{n}.cpp').read_text();marker=f'DEFINE_REX_FUNC({name}) {{'
  bodies[name]=marker+text.split(marker,1)[1].split('DEFINE_REX_FUNC(',1)[0].rstrip()
  records[namespace+'::'+name]=hashlib.sha256(bodies[name].encode()).hexdigest()
 calls=set()
 for b in bodies.values():calls.update(re.findall(r'\b((?:sub_|__save|__rest)\w+)\(ctx, base\)',b))
 parts.append('namespace '+namespace+' {')
 parts += [f'void {n}(PPCContext&,uint8_t*);' for n in sorted(calls|set(bodies))]
 parts+=list(bodies.values());parts.append('}')
 print(namespace,'external:',sorted(calls-set(bodies)))
(R/'isolated/input_chain_original.cpp').write_text('\n'.join(parts)+'\n')
(R/'isolated/input-chain-hashes.json').write_text(json.dumps(records,indent=2)+'\n')
