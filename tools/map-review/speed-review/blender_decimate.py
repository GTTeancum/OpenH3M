"""Blender (background) side of reduce_to_360.py: decimate each mesh with Blender's own Decimate (collapse)
modifier and hand back split vertices (position, corner normal, UV) and triangles with material slots.

Run: blender --background --factory-startup --python blender_decimate.py -- <in.npz> <out.npz>
in.npz holds, per mesh k: p{k} (n,3) positions, u{k} (n,2) UVs, t{k} (m,3) triangles, m{k} (m,) material ids,
r{k} () keep ratio. Seams in the source are separate vertices; they are welded first (UVs stay per corner) so
decimation does not open cracks, then normals are rebuilt by angle (smooth under 40 degrees)."""
import sys, math, numpy as np
import bpy, bmesh

src, dst = sys.argv[sys.argv.index('--') + 1:][:2]
z = np.load(src); out = {}
keys = sorted({int(k[1:]) for k in z.files if k[0] == 'p'})
for k in keys:
    p, u, t, m, r = z[f'p{k}'], z[f'u{k}'], z[f't{k}'], z[f'm{k}'], float(z[f'r{k}'])
    me = bpy.data.meshes.new(f'm{k}')
    me.from_pydata(p.tolist(), [], t.tolist())
    me.polygons.foreach_set('material_index', m.astype(np.int32))
    uvl = me.uv_layers.new(name='uv')
    loops_v = np.empty(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', loops_v)
    uvl.data.foreach_set('uv', u[loops_v].astype(np.float32).ravel())
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.01)          # source units are cm
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(f'o{k}', me); bpy.context.scene.collection.objects.link(ob)
    if r < 0.999:
        mod = ob.modifiers.new('dec', 'DECIMATE'); mod.decimate_type = 'COLLAPSE'; mod.ratio = r
        mod.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = ob
    dg = bpy.context.evaluated_depsgraph_get(); ev = ob.evaluated_get(dg)
    em = bpy.data.meshes.new_from_object(ev)
    bm = bmesh.new(); bm.from_mesh(em)
    bmesh.ops.dissolve_degenerate(bm, dist=0.01, edges=bm.edges)       # strong collapse leaves zero-area faces
    bmesh.ops.triangulate(bm, faces=bm.faces); bm.to_mesh(em); bm.free()
    em.shade_smooth(); em.set_sharp_from_angle(angle=math.radians(40))   # smooth, hard edges above 40 degrees
    nl = len(em.loops)
    lv = np.empty(nl, np.int32); em.loops.foreach_get('vertex_index', lv)
    co = np.empty(len(em.vertices) * 3, np.float32); em.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    cn = np.array([c.vector[:] for c in em.corner_normals], np.float32)
    bad = np.linalg.norm(cn, axis=1) < 1e-4                            # the kit rejects zero normals
    if bad.any(): cn[bad] = (0.0, 0.0, 1.0)
    uv = np.empty(nl * 2, np.float32); em.uv_layers['uv'].data.foreach_get('uv', uv); uv = uv.reshape(-1, 2)
    fm = np.empty(len(em.polygons), np.int32); em.polygons.foreach_get('material_index', fm)
    fs = np.empty(len(em.polygons), np.int32); em.polygons.foreach_get('loop_start', fs)
    # split vertices per (position, normal, uv)
    keyarr = np.c_[co[lv], np.round(cn, 4), np.round(uv, 5)]
    uniq, inv = np.unique(keyarr, axis=0, return_inverse=True)
    tri = inv.reshape(-1)[np.add.outer(fs, np.arange(3))]
    out[f'p{k}'] = uniq[:, :3]; out[f'n{k}'] = uniq[:, 3:6]; out[f'u{k}'] = uniq[:, 6:8]
    out[f't{k}'] = tri.astype(np.int32); out[f'm{k}'] = fm
    bpy.data.objects.remove(ob); bpy.data.meshes.remove(me); bpy.data.meshes.remove(em)
np.savez(dst, **out)
print('decimated', len(keys), 'meshes')
