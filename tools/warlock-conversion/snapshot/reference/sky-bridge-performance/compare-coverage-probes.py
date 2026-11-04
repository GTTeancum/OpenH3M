"""Compare aggregate coverage for identical position/state inputs in two replays."""
import argparse, collections, hashlib, json
from pathlib import Path

REF=Path(__file__).resolve().parent
REPO=REF.parents[4]
FIELDS=('position_inputs_sha256','depth_control','color_mask','surface_info','raster_control')

def compare(left, right, output):
    for path in (left,right,output):path.resolve().relative_to(REPO/'work/sky-bridge')
    rows=[json.loads((p/'coverage-draws.json').read_text()) for p in (left,right)]
    parts=[{(x['owner'],x['mesh'],x['part']):x for x in json.loads((p/'model-draw-analysis.json').read_text())['parts']} for p in (left,right)]
    for key,part in parts[0].items():
        if key[0] not in (10122,10177):continue
        for field in ('index_count','vertex_stride','vertex_format','palette_indices','vertex_prefix_sha256','index_prefix_sha256'):
            assert part[field]==parts[1][key][field], (key,field)
    grouped=[]
    for values in rows:
        groups=collections.defaultdict(list)
        for row in values:
            if row['owner'] in (10122,10177):groups[(row['owner'],row['mesh'],row['part'],row['vs'])].append(row)
        grouped.append(groups)
    assert grouped[0].keys()==grouped[1].keys()
    results=[]
    for identity in sorted(grouped[0]):
        source=[g[identity] for g in grouped]
        indexed=[]
        for values in source:
            group=collections.defaultdict(list)
            for row in values:group[tuple(row[k] for k in FIELDS)].append(row)
            indexed.append(group)
        shared=sorted(indexed[0].keys() & indexed[1].keys())
        equal=[];different=[]
        for key in shared:
            a,b=(g[key] for g in indexed)
            counts=[sorted({x['samples'] for x in v}) for v in (a,b)]
            record=dict(key=key,samples=counts,frames=[[x['frame'] for x in v] for v in (a,b)])
            (equal if counts[0]==counts[1] else different).append(record)
        results.append(dict(owner=identity[0],mesh=identity[1],part=identity[2],vs=identity[3],
            draws=[len(v) for v in source],ranges=[[min(x['samples'] for x in v),max(x['samples'] for x in v)] for v in source],
            pixel_shaders=[sorted({x['shader'] for x in v}) for v in source],
            matched_keys=len(shared),equal_keys=len(equal),different=different,equal_examples=equal[:3]))
    report=dict(runs=[str(p.relative_to(REPO)) for p in (left,right)],key_fields=FIELDS,groups=results,
        matched_fabric_cutout_keys=sum(x['matched_keys'] for x in results if (x['owner'],x['part'])==(10177,1)),
        different_fabric_cutout_keys=sum(len(x['different']) for x in results if (x['owner'],x['part'])==(10177,1)),
        inputs_sha256={str((p/n).relative_to(REPO)):hashlib.sha256((p/n).read_bytes()).hexdigest() for p in (left,right) for n in ('coverage-draws.json','coverage-analysis.json','model-draw-analysis.json')},
        limitations=['Equal aggregate passing-sample counts do not establish an identical coverage mask.',
            'Keys match referenced position constants and selected raster/depth state, not every pixel-shader input or other scene objects.',
            'Different simulation times are matched by exact input values, not by CPU/GPU frame number.',
            'Zero passing samples alone do not identify occlusion, depth/stencil rejection, culling, or shader discard.'],
        credit=json.loads((REF/'sky-pixel-probe-build.json').read_text())['credit'])
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('matched_fabric_cutout_keys','different_fabric_cutout_keys')}))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('left','right','output'):parser.add_argument(name,type=lambda s:Path(s).resolve())
    args=parser.parse_args();compare(args.left,args.right,args.output)
