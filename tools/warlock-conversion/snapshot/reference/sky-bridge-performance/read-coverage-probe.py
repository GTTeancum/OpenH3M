"""Join actual GPU occlusion sample counts to byte-attributed model draws.

Counts measure aggregate surviving samples, not a complete coverage mask or
visual acceptance. Guest visibility queries are never nested or modified.
"""
import argparse,array,collections,csv,hashlib,importlib.util,json,struct
from pathlib import Path
REF=Path(__file__).resolve().parent;REPO=REF.parents[4]
spec=importlib.util.spec_from_file_location('model',REF/'trace-model-draws.py');model=importlib.util.module_from_spec(spec);spec.loader.exec_module(model)

def analyze(run):
 run=run.resolve();run.relative_to(REPO/'work/sky-bridge')
 calls={x['sequence']:x for x in json.loads((run/'model-draw-calls.json').read_text())['calls']}
 metadata=json.loads((run/'model-draw-analysis.json').read_text())
 parts={(p['owner'],p['mesh'],p['part']):p for p in metadata['parts']}
 events=collections.Counter();rows={};queries=set()
 with (run/'coverage.csv').open(newline='') as stream:
  for raw in csv.DictReader(stream):
   event=raw.pop('event');events[event]+=1;row={k:int(v) for k,v in raw.items()}
   if event!='sample':continue
   seq=row['sequence'];call=calls[seq]
   assert (row['frame'],row['shader'],row['index_count'])==(call['frame'],call['ps'],call['index_count'])
   assert seq not in rows and row['query'] not in queries;queries.add(row['query']);rows[seq]=row
   assert len(call['candidates'])==1
   part=call['candidates'][0];row.update(part,vs=call['vs'])
 assert not any(events[e] for e in ('pending','initialize_failed','capacity'))
 registers=array.array('I',[0])*0x5003
 for kind,raw in model.packets(run/'draws.bin'):
  if kind==1:seq=struct.unpack('<11Q',raw)[0]
  elif kind==2:
   for i,v in struct.iter_unpack('<II',raw):registers[i]=v
  elif kind==5 and seq in rows:
   row=rows[seq];part=parts[(row['owner'],row['mesh'],row['part'])]
   # Keep exact position, UV decode, camera and referenced skinning constants.
   # Unreferenced palette entries can belong to another object and must not
   # prevent comparison of this part's identical transform inputs.
   data=registers[0x4000:0x4020].tobytes()+registers[0x4030:0x4040].tobytes()
   for i in part['palette_indices']:data+=registers[0x4040+12*i:0x404c+12*i].tobytes()
   row['position_inputs_sha256']=hashlib.sha256(data).hexdigest()
   row['depth_control']=registers[0x2200];row['color_mask']=registers[0x2104]
   row['surface_info']=registers[0x2000];row['raster_control']=registers[0x2205]
 groups={}
 for row in rows.values():
  key=row['owner'],row['mesh'],row['part'],row['vs'],row['shader']
  g=groups.setdefault(key,dict(owner=key[0],mesh=key[1],part=key[2],vs=key[3],ps=key[4],draws=0,zero=0,sample_min=2**64-1,sample_max=0))
  g['draws']+=1;g['zero']+=row['samples']==0;g['sample_min']=min(g['sample_min'],row['samples']);g['sample_max']=max(g['sample_max'],row['samples'])
 report=dict(run=str(run.relative_to(REPO)),events=dict(events),draws=len(calls),recorded=len(rows),missing_sequences=sorted(set(calls)-set(rows)),groups=list(groups.values()),
  inputs_sha256={n:hashlib.sha256((run/n).read_bytes()).hexdigest() for n in ('coverage.csv','draws.bin','model-draw-calls.json')},
  limitations=['Aggregate samples passing rasterization, shader discard and host depth/stencil tests, not an image or pixel identity mask.',
   'Exact position-input keys exclude unreferenced bone constants; pixel material inputs need a separate comparison.',
   'A zero count alone does not distinguish offscreen, occlusion, culling or shader discard.'],
  credit=json.loads((REF/'sky-pixel-probe-build.json').read_text())['credit'])
 (run/'coverage-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
 (run/'coverage-draws.json').write_text(json.dumps(list(rows.values()),indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k not in ('groups','inputs_sha256','credit','limitations','missing_sequences')}))
 print('Missing queries:',len(report['missing_sequences']))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);analyze(p.parse_args().run)
