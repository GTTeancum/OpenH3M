"""Summarize native camera telemetry without interpreting it as visual proof."""
import sys,json,math,runpy
from pathlib import Path
root=Path(sys.argv[1]);records=[json.loads(line) for line in (root/'loading-trace.jsonl').read_text().splitlines()]
samples=[{k:r[k] for k in ('seconds','position','forward','location')} for r in records if r['event']=='observer_position' and r['seconds']>=114]
assert len(samples)>20
for row in samples:assert all(math.isfinite(v) for v in row['position']+row['forward'])
angles=[math.atan2(r['forward'][1],r['forward'][0]) for r in samples]
deltas=[(b-a+math.pi)%(2*math.pi)-math.pi for a,b in zip(angles,angles[1:])]
planar_path=sum(math.dist(a['position'][:2],b['position'][:2]) for a,b in zip(samples,samples[1:]))
summary=next(r for r in reversed(records) if r['event']=='hash_summary');assert summary['failed']==0
errors=[r for r in records if r['event'] in ('error','exception','observer_sample_error')]
report=dict(scope='Native observer samples from 114 seconds onward; earlier menu-to-game camera transition excluded.',
 native_hash_summary=summary,diagnostic_errors=errors,observer_samples=samples,
 planar_path_world_units=planar_path,net_displacement_world_units=math.dist(samples[0]['position'],samples[-1]['position']),
 cumulative_absolute_yaw_degrees=sum(abs(x) for x in deltas)*180/math.pi,
 position_bounds={axis:[min(r['position'][i] for r in samples),max(r['position'][i] for r in samples)] for i,axis in enumerate('xyz')},
 limitations=['Short local movement and a slow camera turn; not a full-map walkthrough.','Native camera motion and hash validation do not verify panels, lighting, audio, or visible gameplay.','Debugger instrumentation may affect timing.'])
analyze=runpy.run_path(str(Path(__file__).with_name('analyze-timing.py')))['analyze']
report['timing']=analyze(root,scope='Bounded native-observer movement/turn test; host timing, 110-165 runtime seconds. No visual or console verification.')
(root/'movement-summary.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='observer_samples'},indent=2))
