"""Apply bounded native Blender Join with an exact corner-attribute audit."""
from collections import Counter
import bpy
from mathutils import Matrix

def join_collision(copies,authoring,plan,mesh_processing):
    lookup={r['source_object']:r for r in authoring['objects']}
    def snapshot(objects):
        faces=Counter()
        for obj in objects:
            mesh=obj.data
            assert not obj.modifiers
            for face in mesh.polygons:
                mat=mesh.materials[face.material_index]
                material=(mesh_processing.append_material_symbols(mat,'halo3',True),
                    mat.nwo.shader_path,str(mat.get('haven_source_global_material','')))
                corners=[]
                for li in face.loop_indices:
                    vertex=mesh.vertices[mesh.loops[li].vertex_index]
                    # Positions/UV/colors exact; normals rounded only at 1e-6.
                    corners.append((tuple(vertex.co),tuple(round(v,6) for v in mesh.corner_normals[li].vector),
                        tuple((layer.name,tuple(layer.data[li].uv)) for layer in mesh.uv_layers),
                        tuple((layer.name,layer.domain,tuple(layer.data[li if layer.domain=='CORNER' else vertex.index].color))
                            for layer in mesh.color_attributes)))
                faces[(material,tuple(corners))]+=1
        return faces
    reports=[]
    for batch in plan['proposed_bounded_batches']:
        keys=[lookup[n]['export_name'] for n in batch['objects']]
        objects=[copies[k] for k in keys]
        matrix=objects[0].matrix_world.copy()
        assert all(o.matrix_world==matrix for o in objects)
        assert len({lookup[n]['source_collision_type'] for n in batch['objects']})==1
        assert len({k.split('hvn_')[0] for k in keys})==1
        expected=snapshot(objects)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:
            obj.data=obj.data.copy()
            obj.matrix_world=Matrix.Identity(4)
            obj.select_set(True)
        active=objects[0]
        bpy.context.view_layer.objects.active=active
        assert bpy.ops.object.join()=={'FINISHED'}
        bpy.context.view_layer.update()
        actual=snapshot([active])
        assert actual==expected,(keys,'Joined corner attributes differ',sum((expected-actual).values()),sum((actual-expected).values()))
        active.matrix_world=matrix
        for key in keys[1:]:del copies[key]
        reports.append(dict(source_objects=batch['objects'],export_name=keys[0],
            category=batch['category'],faces_checked=sum(expected.values()),
            corner_attributes_preserved=True,transform_preserved=active.matrix_world==matrix))
    bpy.context.view_layer.update()
    return reports
