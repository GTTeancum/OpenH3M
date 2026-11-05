"""Package one fresh map beside existing shared DLC, using established builders."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/warlock-conversion/snapshot/tools'))
from build_dlc_payload import build as payload,ADDITIONAL_MAPS
from build_dlc_previews import build as previews
from build_dlc_live import build as live
from preflight_variant_budget import inspect_quotas
from warlock_handoff import preflight
from cache_reader import Cache
p=argparse.ArgumentParser();p.add_argument('--candidate',type=int,required=True);a=p.parse_args()
source=ROOT/'.local/battle-canyon-fresh'/('candidate'+str(a.candidate))
report=json.loads((source/'build.json').read_text(encoding='utf8'))
assert report['status']=='checkpoint_built',report['status']
native=source/'zanzibar.map'
verified=preflight(native,Path('C:/X360/ISOs/H3M/default.xex'))
c=Cache(native)
try:quotas=inspect_quotas(c)
finally:c.close()
assert quotas['conversion_ready'],quotas
dest=source/'dlc';dest.mkdir()
row=next(r for r in ADDITIONAL_MAPS if r[1]=='battle_canyon')
result=payload(source,Path('C:/X360/ISOs/H3M/maps'),dest/'payload',[row],{'battle_canyon':native})
result['previews']=previews(ROOT,dest/'payload',['battle_canyon'],{'battle_canyon':ROOT/'work/stock-h3-audit/wip/textured-overview.png'})
result['preview_limitation']='Original Reach geometry in Blender studio lighting, not a native game screenshot.'
(dest/'payload.json').write_text(json.dumps(result,indent=2),encoding='utf8')
bundle=live(dest/'payload',dest/'draft.live')
bundle.update(native_validation=verified,quotas=quotas,source_cache=report.get('source_sha256'),
    visual_gameplay_acceptance=False,source='Original Halo Reach MCC Battle Canyon / Certain Affinity; official Reach mod-tool tags imported with unchanged Foundry. No community port or rejected rebuild input.')
(dest/'bundle.json').write_text(json.dumps(bundle,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in bundle.items() if k!='entries'},indent=2))
