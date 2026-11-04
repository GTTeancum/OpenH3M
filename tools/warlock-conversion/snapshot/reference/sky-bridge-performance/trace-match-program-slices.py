import argparse,json,struct,collections,hashlib
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument('--trace-dir',type=Path,default=Path('work/sky-bridge/draw-trace-20261103-200444'))
parser.add_argument('--shader-index',type=Path,default=Path('work/sky-bridge/draw-trace-build/candidate32-shader-index.json'))
args=parser.parse_args();root=args.trace_dir
root.resolve().relative_to(Path(__file__).resolve().parents[5])
index=json.loads(args.shader_index.read_text())
data=Path(index['map']).read_bytes(); programs=[]
assert hashlib.sha256(data).hexdigest()==index['map_sha256'], 'Shader index is stale'
for digest,entries in index['programs_by_guest_endian_sha256'].items():
 e=entries[0];raw=data[e['code_file_offset']:e['code_file_offset']+e['code_size']]
 programs.append((entries,raw))
rows=[]
with (root/'draws.bin').open('rb') as f:
 while h:=f.read(8):
  kind,size=struct.unpack('<II',h);d=f.read(size)
  if kind==3: shader,stage=struct.unpack('<QQ',d)
  elif kind==4:
   raw=b''.join(struct.pack('>I',w[0]) for w in struct.iter_unpack('<I',d)); matches=[]
   for entries,blob in programs:
    at=blob.find(raw)
    mode='exact_slice'
    if at<0 and raw[-12:]==bytes(12): at=blob.find(raw[:-12]); mode='zero_final_instruction'
    if at<0 or at%4 or entries[0]['stage']!=('vertex' if stage==0 else 'pixel'): continue
    matches.append({'offset':at,'mode':mode,'runtime_size':len(raw),'cache_size':len(blob),'cache_tail':blob[at+len(raw)-12:at+len(raw)].hex(),'programs':entries})
   rows.append(dict(shader=shader,stage=stage,matches=matches))
(root/'program-slice-matches.json').write_text(json.dumps(rows,indent=2))
print('matched',sum(bool(r['matches']) for r in rows),'of',len(rows))
print('offsets',collections.Counter(m['offset'] for r in rows for m in r['matches']))
print('modes',collections.Counter(m['mode'] for r in rows for m in r['matches']))
print('unmatched',[(r['shader'],r['stage']) for r in rows if not r['matches']])
