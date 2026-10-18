import hashlib,json
from pathlib import Path
from cache_reader import Cache
from mcc_bitmap_source import BitmapSource
from xbox_bitmap import tile_base,untile_base,addresses
# Independent XGAddress2DTiledOffset algebra, compared across tile boundaries.
def reference(x,y,pitch,log):
 aligned=(pitch+31)&~31
 macro=((x>>5)+(y>>5)*(aligned>>5))<<(log+7)
 micro=((x&7)+((y&6)<<2))<<log
 offset=macro+((micro&~15)<<1)+(micro&15)+((y&8)<<(3+log))+((y&1)<<4)
 return ((offset&~511)<<3)+((offset&448)<<2)+(offset&63)+((y&16)<<7)+((((y&8)>>2)+(x>>3)&3)<<6)
for bpb in (8,16):
 a=addresses(257,129,bpb)
 for y in range(129):
  for x in range(257):assert int(a[y,x])==reference(x,y,257,bpb.bit_length()-1),(x,y,bpb)
c=Cache('D:/SteamLibrary/steamapps/workshop/content/976730/2977651586/maps/warlock.map',True);s=BitmapSource(c);report=[]
for tag in (0x2a42,0x2a45,0x2a43):
 info=s.info(tag)[0];pixels=s.pixels(tag);tiled=tile_base(pixels,info['width'],info['height'],info['format']);back=untile_base(tiled,info['width'],info['height'],info['format']);assert back==pixels[:len(back)]
 report.append({'name':c.name(tag),'format':info['format'],'tiled_bytes':len(tiled),'tiled_sha256':hashlib.sha256(tiled).hexdigest(),'roundtrip_matches':True})
Path('.local/reports/texture-encoding.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));c.close()
