"""Read-only collision compatibility preflight for original Xbox 360 Halo 3."""
import argparse
import json
from pathlib import Path
from cache_reader import Cache
from resource_reader import Resource

FIELDS = ('nodes_3d', 'planes', 'leaves', 'references_2d', 'nodes_2d', 'surfaces', 'edges', 'vertices')


def inspect(cache):
    result = []
    for index, tag in cache.tags.items():
        if tag['group'] != 'sbsp':
            continue
        resource = Resource(cache, cache.u(tag['offset'] + 0x38c))
        small, large, instances, havok = [resource.unpack('I', resource.root + o)[0] for o in (0,12,24,36)]
        entry = {'bsp': cache.name(index), 'small_collision_bsps': small,
                 'large_collision_bsps': large, 'instances': instances, 'havok_blocks': havok,
                 'large_blocks': []}
        if large:
            ptr = resource.fix[resource.root+16]
            if ptr >> 29 != 1:
                raise ValueError('Large collision headers are outside control segment')
            for k in range(large):
                at = (ptr & 0x1fffffff) + k*96
                counts = {name:resource.unpack('I',at+j*12)[0] for j,name in enumerate(FIELDS)}
                def payload(j,stride):
                    count=resource.unpack('I',at+j*12)[0]
                    if not count:return b''
                    pointer=resource.fix[at+j*12+4];segment=pointer>>29
                    data=resource.data if segment==1 else resource.raw[segment-2]
                    off=pointer&0x1fffffff
                    if off+count*stride>len(data):raise ValueError('Collision block exceeds segment')
                    return data[off:off+count*stride]
                planes=payload(1,16)
                unique=len({planes[o:o+16] for o in range(0,len(planes),16)})
                entry['large_blocks'].append({'counts':counts,'byte_unique_planes':unique,
                    'plane_index_width_retail_bits':16,'plane_index_signed':True,'maximum_plane_count':32768,'edge_index_width_retail_bits':16,
                    'direct_narrowing_overflow':counts['planes']>32768 or counts['edges']>65535,
                    'exact_plane_dedup_still_exceeds_signed_limit':unique>32768})
        result.append(entry)
    return {'bsps':result, 'retail_large_collision_supported':False,
            'conversion_ready': all(not e['large_collision_bsps'] and not e['havok_blocks'] for e in result),
            'note':'Index-format preflight only; does not prove RAM, rendering or gameplay budgets.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    repo=Path(__file__).resolve().parents[4]
    report=args.report.resolve()
    if not report.is_relative_to(repo):raise ValueError('Preflight reports must stay in the repository')
    cache=Cache(args.source,True)
    try:result=inspect(cache)
    finally:cache.close()
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
