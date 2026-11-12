"""Read-only preflight of installed H3 candidates in the requested conversion queue."""
import argparse
import collections
import json
from pathlib import Path
from cache_reader import Cache
from preflight_collision_budget import inspect

ROOT=Path(__file__).resolve().parents[4]


def audit(queue,shared,output):
    if not output.resolve().is_relative_to(ROOT):raise ValueError('Output outside repository')
    result=[]
    for entry in json.loads(queue.read_text()):
        for candidate in entry['sources']:
            for file in candidate['cache_paths']:
                record=dict(map=entry['name'],source=file,workshop_id=candidate['workshop_id'])
                cache=None
                try:
                    cache=Cache(file,True)
                    cache.shared_paths={r'maps\shared.map':shared}
                    cache.decoded_pages={}
                    record['scenarios']=[cache.name(i) for i,t in cache.tags.items() if t['group']=='scnr']
                    record['collision']=inspect(cache)
                    formats=collections.Counter()
                    for tag in cache.tags.values():
                        if tag['group']=='bitm':
                            formats.update(cache.unpack('H',r+12)[0] for r in cache.block(tag['offset']+0x60,56))
                    record['bitmap_formats']=dict(sorted(formats.items()))
                except Exception as exc:
                    record['error']=str(exc)
                finally:
                    if cache is not None:cache.close()
                result.append(record)
                output.write_text(json.dumps(result,indent=2)+'\n')
                print(json.dumps(dict(map=entry['name'],source=file,error=record.get('error'),
                    collision_ready=record.get('collision',{}).get('conversion_ready'))),flush=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('queue','shared','output'):p.add_argument('--'+name,type=Path,required=True)
    audit(**vars(p.parse_args()))
