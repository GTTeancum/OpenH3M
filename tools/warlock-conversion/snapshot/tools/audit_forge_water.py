"""Read-only comparison of Forge water bindings with original-disc examples."""
import json,sys
from pathlib import Path
from cache_reader import Cache
from string_ids import StringTable


def inspect(path, mcc=False):
    c=Cache(path,mcc)
    try:
        strings=StringTable(c)
        records=[]
        for index,tag in c.tags.items():
            if tag['group']!='rmw ': continue
            root=tag['offset']
            for post in c.block(root+40,140 if mcc else 132):
                td=c.u(post+12)&65535; template=c.tags[td]['offset']
                names=lambda offset:[strings.text(c.u(row)) for row in c.block(template+offset,4)]
                real_names,texture_names=names(72),names(108)
                textures=[]
                for n,row in enumerate(c.block(post+16,28 if mcc else 24)):
                    bitmap=c.u(row+12)
                    textures.append({'parameter':texture_names[n], 'bitmap':None if bitmap==0xffffffff else c.name(bitmap&65535),
                        'extern_mode':c.data[row+(21 if mcc else 20)],
                        'transform':c.unpack('b',row+(22 if mcc else 21))[0]})
                query=c.unpack('8h',post+116)
                records.append({'index':index,'name':c.name(index),'template':c.name(td),
                    'options':[c.unpack('h',r)[0] for r in c.block(root+16,2)],
                    'blend_flags_pad':c.unpack('3I',post+104),'queryable':query,
                    'queryable_as_texture':[texture_names[n] if 0<=n<len(texture_names) else None for n in query],
                    'queryable_as_real':[real_names[n] if 0<=n<len(real_names) else None for n in query],
                    'textures':textures,'constants':dict(zip(real_names,[c.unpack('4f',r) for r in c.block(post+28,16)]))})
        return records
    finally:c.close()

if __name__=='__main__':
    root=Path(__file__).resolve().parents[4]
    report={}
    for name in ('zanzibar','riverworld','docks','deadlock'):
        report[name]=inspect(root/'../../maps'/f'{name}.map')
    report['forge_source']=inspect(Path(r'D:\SteamLibrary\steamapps\workshop\content\976730\3597611181\maps\forge_halo.map'),True)
    report['forge_candidate']=inspect(Path(sys.argv[1]) if len(sys.argv)>1
                                      else root/'../custom-maps-play/maps/sandbox.map')
    (root/'work/forge-world/water-reference-audit.json').write_text(json.dumps(report,indent=2))
    for name,records in report.items():
        print(name,len(records),'water materials')
        for r in records:
            print(' ',r['name'],r['template'],r['queryable'],[(t['parameter'],t['extern_mode']) for t in r['textures'] if t['extern_mode']])
