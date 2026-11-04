"""Compare named animation consumers of all animated BSP materials, not just counts."""
import collections,json,sys
from pathlib import Path
sys.path.insert(0,'tools/warlock-conversion/snapshot/tools')
from cache_reader import Cache
from string_ids import StringTable
from tag_functions import convert_function

def inspect(c,strings,tid,mcc):
    post,=c.block(c.tags[tid]['offset']+40,140 if mcc else 132)
    template=c.tags[c.u(post+12)&65535]['offset']
    functions=[]
    for row in c.block(post+92,36):
        size=c.u(row+16);ptr=c.pointer(c.u(row+28));raw=bytes(c.data[ptr:ptr+size])
        functions.append((c.u(row),strings.text(c.u(row+4)),strings.text(c.u(row+8)),
                          c.unpack('f',row+12)[0],(convert_function(raw) if mcc else raw).hex()))
    routes=c.block(post+80,4);passes=c.block(post+68,6);entries=c.block(post+56,2)
    troutes=c.block(template+60,4);tpasses=c.block(template+48,32 if mcc else 28)
    tentries=c.block(template+36,2);consumers=[];invalid=[]
    def span(packed,rows):
        start,count=packed&1023,packed>>10
        assert start+count<=len(rows)
        return range(start,start+count)
    for entry,(ep,tep) in enumerate(zip(entries,tentries)):
        ps=list(span(c.unpack('H',ep)[0],passes));ts=list(span(c.unpack('H',tep)[0],tpasses))
        if len(ps)!=len(ts) and ps:invalid.append(('pass_count',entry,len(ps),len(ts)))
        for pi,ti in zip(ps,ts):
            for usage,tu in enumerate((0,1,4)):
                names=[strings.text(c.u(x)) for x in c.block(template+(108 if usage==0 else 72),4)]
                for ri in span(c.unpack('H',passes[pi]+usage*2)[0],routes):
                    reg,fn,const=c.unpack('HBB',routes[ri])
                    matches=[c.unpack('HBB',troutes[r]) for r in span(c.unpack('H',tpasses[ti]+tu*2)[0],troutes)
                             if c.unpack('HBB',troutes[r])[:2]==(reg,const)]
                    if fn>=len(functions) or const>=len(names) or len(matches)!=1:
                        invalid.append(('route',entry,usage,reg,fn,const,len(matches)));continue
                    consumers.append((entry,usage,fn,names[const],matches[0][2]))
    return functions,collections.Counter(consumers),invalid

s=Cache('D:/SteamLibrary/steamapps/workshop/content/976730/3003239190/maps/s3d_sky_bridgenew.map',True)
t=Cache('work/sky-bridge/zanzibar-32.map');ss,ts=StringTable(s),StringTable(t)
a=s.block(s.tags[10471]['offset']+208,36)
br,=[v['offset'] for v in t.tags.values() if v['group']=='sbsp' and t.u(v['offset']+192)==len(a)]
b=t.block(br+192,36);seen=set();results=[]
for x,y in zip(a,b):
    si,ti=s.u(x+12)&65535,t.u(y+12)&65535
    if si in seen:continue
    seen.add(si);p,=s.block(s.tags[si]['offset']+40,140)
    if not s.u(p+92):continue
    sf,sc,se=inspect(s,ss,si,True);tf,tc,te=inspect(t,ts,ti,False)
    results.append(dict(source_id=si,target_id=ti,name=s.name(si),functions_equal=sf==tf,
        source_consumers=sum(sc.values()),target_consumers=sum(tc.values()),
        missing=[dict(consumer=k,count=v) for k,v in (sc-tc).items()],
        added=[dict(consumer=k,count=v) for k,v in (tc-sc).items()],source_invalid=se,target_invalid=te))
out=Path('work/sky-bridge/candidate32-all-animation-routes.json');out.write_text(json.dumps(results,indent=2))
print('Audited',len(results),'animated BSP materials')
for r in results:
    if not r['functions_equal'] or r['missing'] or r['added'] or r['source_invalid'] or r['target_invalid']:
        print(r['source_id'],r['name'].rsplit('\\',1)[-1], 'functions',r['functions_equal'],
              'consumers',r['source_consumers'],r['target_consumers'],'invalid',len(r['target_invalid']))
s.close();t.close()
