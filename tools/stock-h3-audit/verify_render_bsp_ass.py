"""Compare both collision layers and visible triangles to isolated clean inputs."""
from pathlib import Path
import runpy

HERE=Path(__file__).resolve().parent
# Reuse the full ASS read and exact oriented-triangle comparator; also rerun
# the existing ten-boulder checks rather than bypassing their protection.
context=runpy.run_path(str(HERE/'verify_boulder_batch_ass.py'))
read=context['read'];sha=context['sha'];triangles=context['triangles']
asset=context['asset'];instances=context['instances'];export=context['export']
process_file=context['process_file'];OUT=context['OUT'];json=context['json']
authoring=read('h3-render-bsp-authoring.json')
saved=read('render-bsp-bound-verification.json')
assert saved['scene_sha256']==export['source_sha256']
assert saved['exact_visible_geometry_normals_uvs_transforms'] and saved['exact_original_collision_layers']
checked=[]
for case in authoring['cases']:
    name=case['target']
    probe=read('collision-workflow-precise-render-only-original-render-bsp-'+name+'-probe.json')
    assert probe['source_sha256']==case['diagnostic_scene_sha256']
    assert sha(probe['ass'])==probe['ass_sha256']==case['diagnostic_ass_sha256']
    expected=process_file(probe['ass']);row=dict(target=name,diagnostic_ass_sha256=probe['ass_sha256'])
    for role,key in (('render_and_original_render_bsp','render_instance'),('collision_child','collision_child')):
        instance_name=probe[key]
        source=next(i for i in expected.instances if i.name==instance_name)
        original=triangles(expected,source);current=triangles(asset,instances[instance_name])
        assert original==current,(name,role,sum((original-current).values()),sum((current-original).values()))
        row[role+'_triangles']=sum(current.values())
    assert asset.instances[instances[probe['collision_child']].parent_id] is instances[probe['render_instance']]
    checked.append(row)
result=dict(scene_sha256=export['source_sha256'],ass_sha256=export['ass_sha256'],targets=checked,
    exact_diagnosed_triangles_and_material_controls=True,
    limitation='Full ASS exactly matches isolated passing inputs. Combined native import and MCC remain independent gates.')
(OUT/'render-bsp-ass-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print('RENDER_BSP_ASS_VERIFIED',len(checked),'definitions',flush=True)
