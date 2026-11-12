"""Measure unresolved anchor-to-render distances without treating fit as proof.

Every point is checked against every triangle of its own piece, not against
other object combinations. Near surfaces can still be the wrong mating faces;
farther points can be intentional construction-plane or clearance markers.
These measurements prioritize review and never modify the runtime data.
"""
import contextlib
import io
import json
from pathlib import Path
import runpy

ROOT=Path(__file__).resolve().parents[2]
with contextlib.redirect_stdout(io.StringIO()):
    audit=runpy.run_path(str(Path(__file__).with_name('verify_scenery_math.py')))
OUT=audit['OUT']
report=[]
for row,proof in zip(audit['inventory']['rows'],audit['proofs']):
    if proof['status']!='unverified':continue
    result={k:row[k] for k in ('map','palette_index','label','bound')}
    source=row['current_source'] or row['candidate_source']
    if not source:
        result.update(status='source_unresolved',reason='No reviewed H4 source model mapping')
    else:
        name=source.split('\\')[-1]
        try:
            _,_,points=audit['source_markers'](name)
            frame=audit['frames'].get(name,dict(yaw_degrees=0,translation=[0,0,0]))
            mapped=[audit['adapt'](p,frame) for p in points]
            triangles=audit['actual_triangles'](row)
            distances=[audit['triangle_distance'](p['position'],triangles) for p in mapped]
            result.update(status='measured_not_verified',source=source,
                points=[dict(index=i,position=p['position'],surface_distance=d)
                        for i,(p,d) in enumerate(zip(mapped,distances))],
                maximum_distance=max(distances),minimum_distance=min(distances))
        except (AssertionError,KeyError,ValueError) as exc:
            result.update(status='transform_or_render_unresolved',reason=str(exc) or type(exc).__name__)
    report.append(result)
(OUT/'unresolved-anchor-residuals.json').write_text(json.dumps(dict(
    method=__doc__,maps=audit['inventory']['maps'],rows=report),indent=2)+'\n')
seen=set()
for r in sorted(report,key=lambda r:-r.get('maximum_distance',-1)):
    if r['label'] in seen:continue
    seen.add(r['label'])
    print(r['label'],r['status'],round(r['maximum_distance'],6) if 'maximum_distance' in r else r['reason'])
