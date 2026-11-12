"""Verify imported terrain shared programs and entry-point tables against disc donors."""
import argparse,hashlib,json
from pathlib import Path
from cache_reader import Cache

def programs(c,root,kind):
 result=[]
 for row in c.block(root+16,80):
  p=c.u(row+76)
  if not p:result.append(None);continue
  header=c.pointer(p);debug=header+(0x368 if kind=='vertex' else 0x28)
  size=c.u(debug+8);start=c.pointer(c.u(header+16))
  result.append(hashlib.sha256(c.data[start:start+size]).hexdigest())
 return result

def entries(c,root,kind):
 def ep(row):
  return {'default':c.unpack('i',row+12)[0], 'categories':[
   (c.unpack('i',category)[0],[c.unpack('i',opt)[0] for opt in c.block(category+4,4)])
   for category in c.block(row,16)]}
 if kind=='pixel':return [ep(row) for row in c.block(root,16)]
 return [[ep(row) for row in c.block(vtype,16)] for vtype in c.block(root,12)]

def verify(source,candidate,build,disc):
 s,t=Cache(source,True),Cache(candidate);donors={};results=[]
 try:
  materials={m['source']:m for m in json.loads(Path(build).read_text())['materials'] if 'native_donor' in m}
  sb=[v['offset'] for v in s.tags.values() if v['group']=='sbsp'];tb=[v['offset'] for v in t.tags.values() if v['group']=='sbsp']
  if len(sb)!=1 or len(tb)!=1:raise ValueError('Verifier requires one BSP')
  sm,tm=s.block(sb[0]+0xd0,36),t.block(tb[0]+0xc0,36)
  if len(sm)!=len(tm):raise ValueError('Material table count changed')
  checked=set()
  for sa,ta in zip(sm,tm):
   if s.u(sa+12)==0xffffffff:
    if t.u(ta+12)!=0xffffffff:raise ValueError('Null source material acquired a target shader')
    continue
   si,ti=s.u(sa+12)&65535,t.u(ta+12)&65535
   if s.tags[si]['group']!='rmtr' or ti in checked:continue
   checked.add(ti);name=s.name(si);record=materials[name];donor_name=record['native_donor']
   if donor_name not in donors:donors[donor_name]=Cache(Path(disc)/donor_name)
   d=donors[donor_name];dr=next(v['offset'] for i,v in d.tags.items() if v['group']=='rmdf' and d.name(i)==r'shaders\terrain')
   tr=t.tags[t.u(t.tags[ti]['offset']+12)&65535]['offset']
   for offset,kind in [(52,'pixel'),(68,'vertex')]:
    a=d.tags[d.u(dr+offset+12)&65535]['offset'];b=t.tags[t.u(tr+offset+12)&65535]['offset']
    results.append(dict(material=name,donor=donor_name,kind=kind,
     programs_equal=programs(d,a,kind)==programs(t,b,kind),entry_tables_equal=entries(d,a,kind)==entries(t,b,kind)))
  return {'candidate':str(candidate),'materials':len(checked),'passed':all(x['programs_equal'] and x['entry_tables_equal'] for x in results),'checks':results}
 finally:
  s.close();t.close()
  for c in donors.values():c.close()

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('source','candidate','build','disc','report'):p.add_argument('--'+name,required=True,type=Path)
 a=p.parse_args();r=verify(a.source,a.candidate,a.build,a.disc);a.report.write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps({k:v for k,v in r.items() if k!='checks'}));raise SystemExit(0 if r['passed'] else 1)
