"""Match imported single-level textures to exact authored source mip chains."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from cache_reader import Cache
from resource_reader import Resource
from mcc_bitmap_source import BitmapSource
from encode_bitmap import mip_size
from xbox_bitmap import untile_base


def audit(source_path, target_path):
    s,c = Cache(source_path,True),Cache(target_path)
    targets,dimensions = {},set()
    try:
        for n,t in c.tags.items():
            if t['group'] != 'bitm' or c.name(n) is not None:
                continue
            rows=c.block(t['offset']+96,48);hw=c.block(t['offset']+140,8)
            if len(rows)!=1 or len(hw)!=1:continue
            row=rows[0];w,h=c.unpack('HH',row+4);fmt=c.unpack('H',row+12)[0]
            if c.unpack('H',row+10)[0]!=0 or c.data[row+20] or min(w,h)<32 or fmt not in (14,15,16,33):continue
            r=Resource(c,c.u(hw[0]),shared_paths={'maps\\shared.map': Path('C:/X360/ISOs/H3M/maps/shared.map')});raw=untile_base(r.raw[0],w,h,fmt)
            key=(w,h,fmt,hashlib.sha256(raw).hexdigest())
            targets.setdefault(key,[]).append(n);dimensions.add((w,h,fmt))
        matches={};skipped=[];bitmaps=BitmapSource(s)
        for n,t in s.tags.items():
            if t['group']!='bitm':continue
            infos=bitmaps.info(n)
            if len(infos)!=1:continue
            info=infos[0];w,h,fmt=info['width'],info['height'],info['format']
            if fmt not in (14,15,16,33) or info['mips']<2:continue
            dims=[(max(1,w>>k),max(1,h>>k),fmt) for k in range(info['mips']-1)]
            if not any(d in dimensions for d in dims):continue
            try:
                pixels=bitmaps.pixels(n)
            except (ValueError,AssertionError) as error:
                skipped.append(dict(name=s.name(n),reason=str(error)))
                continue
            offset=0
            for level in range(info['mips']-1):
                length=mip_size(w,h,fmt)
                if (w,h,fmt) in dimensions:
                    raw=pixels[offset:offset+length]
                    if fmt==33:
                        block=np.frombuffer(raw,dtype=np.uint8).reshape(-1,16).copy()
                        for column in (0,1,8,9):block[:,column]=(block[:,column].astype(np.uint16)+128)%256
                        raw=block.tobytes()
                    for target in targets.get((w,h,fmt,hashlib.sha256(raw).hexdigest()),[]):
                        record=dict(target=target,source=n,name=s.name(n),level=level,remaining_mips=info['mips']-level,width=w,height=h,format=fmt)
                        previous=matches.get(target)
                        if previous and (previous.get('ambiguous') or previous['name']!=record['name']):
                            # Same base alone cannot choose between differing chains.
                            record['ambiguous']=True
                        matches[target]=record
                offset+=length;w,h=max(1,w//2),max(1,h//2)
        return dict(source=str(source_path),target=str(target_path),eligible=sum(map(len,targets.values())),matches=list(matches.values()),unreadable_source_textures=skipped)
    finally:s.close();c.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','target','report'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();root=Path(__file__).resolve().parents[4]
    if not a.report.resolve().is_relative_to(root):raise ValueError('Report outside repository')
    r=audit(a.source,a.target);a.report.write_text(json.dumps(r,indent=2)+'\n')
    print(f"Matched {len(r['matches'])}/{r['eligible']} imported single-level textures to authored source chains")
