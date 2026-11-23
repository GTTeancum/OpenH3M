// objexport <360 map> <output folder>: every structure BSP's render geometry read back from the converted 360 map
// through TagTool (the data the game is given), written as Wavefront OBJ for Blender: one object per cluster mesh and
// per instanced geometry instance (placed with its transform), positions and texcoords decompressed with the mesh's
// compression bounds (cluster meshes: compression 0; instances: their definition's), faces from each part grouped by
// the part's material (structure BSP material -> shader name).
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using TagTool.Cache;
using TagTool.Geometry;
using TagTool.Tags.Definitions;

namespace Ho2H3
{
    static class ObjExport
    {
        public static int Run(string[] a)
        {
            var cache = a[1].EndsWith(".pak", StringComparison.OrdinalIgnoreCase) ? Program.OpenPak(a[1]) : GameCache.Open(new FileInfo(a[1])); Directory.CreateDirectory(a[2]);
            var ic = CultureInfo.InvariantCulture;
            using (var s = cache is TagTool.Cache.GameCacheModPackage mp ? mp.OpenCacheRead(new MemoryStream()) : cache.OpenCacheRead())
                foreach (var t in cache.TagCache.NonNull().Where(t => t.IsInGroup("sbsp") && (a.Length < 4 || t.Name.Contains(a[3]))))
                {
                    var bsp = cache.Deserialize<ScenarioStructureBsp>(s, t);
                    var geo = bsp.Geometry;
                    if (cache is TagTool.Cache.GameCacheModPackage)   // Halo Online: render geometry lives in the lightmap BSP data
                    {
                        var lb = cache.TagCache.NonNull().FirstOrDefault(x => x.IsInGroup("Lbsp") && x.Name == t.Name);
                        if (lb != null) geo = cache.Deserialize<ScenarioLightmapBspData>(s, lb).Geometry;
                    }
                    var def = cache.ResourceCache.GetRenderGeometryApiResourceDefinition(geo.Resource);
                    var res = cache.ResourceCache.GetStructureBspTagResources(bsp.CollisionBspResource);
                    if (def == null) { Console.WriteLine($"{t.Name}: no render geometry resource"); continue; }
                    var mats = bsp.Materials.Select(m => m.RenderMethod?.Name ?? "none").ToList();
                    var sb = new StringBuilder(); int vbase = 1, objects = 0, tris = 0, skipped = 0;
                    void Mesh(string name, int mi, int ci, Func<float[], float[]> xf)
                    {
                        if (mi < 0 || mi >= geo.Meshes.Count) { skipped++; return; }
                        var m = geo.Meshes[mi]; int vbi = m.VertexBufferIndices[0], ibi = m.IndexBufferIndices[0];
                        if (vbi == ushort.MaxValue || ibi == ushort.MaxValue || vbi >= def.VertexBuffers.Count || ibi >= def.IndexBuffers.Count) { skipped++; return; }
                        var vb = def.VertexBuffers[vbi].Definition; var ib = def.IndexBuffers[ibi].Definition;
                        var c = ci >= 0 && ci < geo.Compression.Count ? geo.Compression[ci] : null;
                        var r = VertexStreamFactory.Create(cache.Version, cache.Platform, new MemoryStream(vb.Data.Data));
                        var pos = new List<float[]>(); var uv = new List<float[]>();
                        for (int k = 0; k < vb.Count; k++)
                        {
                            float[] p; float[] u;
                            if (vb.Format == VertexBufferFormat.World) { var v = r.ReadWorldVertex(); p = new[] { v.Position.I, v.Position.J, v.Position.K }; u = new[] { v.Texcoord.I, v.Texcoord.J }; }
                            else if (vb.Format == VertexBufferFormat.Rigid) { var v = r.ReadRigidVertex(); p = new[] { v.Position.I, v.Position.J, v.Position.K }; u = new[] { v.Texcoord.I, v.Texcoord.J }; if (c != null) { p = new[] { c.X.Lower + p[0] * (c.X.Upper - c.X.Lower), c.Y.Lower + p[1] * (c.Y.Upper - c.Y.Lower), c.Z.Lower + p[2] * (c.Z.Upper - c.Z.Lower) }; u = new[] { c.U.Lower + u[0] * (c.U.Upper - c.U.Lower), c.V.Lower + u[1] * (c.V.Upper - c.V.Lower) }; } }
                            else { skipped++; return; }
                            pos.Add(xf(p)); uv.Add(u);
                        }
                        sb.Append("o ").Append(name).Append('\n');
                        foreach (var p in pos) sb.Append(string.Format(ic, "v {0:0.#####} {1:0.#####} {2:0.#####}\n", p[0], p[2], -p[1]));   // Halo z-up -> OBJ y-up
                        foreach (var u in uv) sb.Append(string.Format(ic, "vt {0:0.#####} {1:0.#####}\n", u[0], 1 - u[1]));
                        foreach (var part in m.Parts)
                        {
                            var st = new IndexBufferStream(new MemoryStream(ib.Data.Data), cache.Endianness) { Position = (uint)part.FirstIndex };
                            var ix = m.IndexBufferType == PrimitiveType.TriangleStrip ? st.ReadTriangleStrip((uint)part.IndexCount) : st.ReadIndices((uint)part.IndexCount);
                            sb.Append("usemtl ").Append(part.MaterialIndex >= 0 && part.MaterialIndex < mats.Count ? mats[part.MaterialIndex].Replace('\\', '/') : "none").Append('\n');
                            for (int k = 0; k + 2 < ix.Length; k += 3)
                            {
                                int x = ix[k], y = ix[k + 1], z = ix[k + 2]; if (x == y || y == z || x == z || x >= pos.Count || y >= pos.Count || z >= pos.Count) continue;
                                sb.Append($"f {vbase + x}/{vbase + x} {vbase + y}/{vbase + y} {vbase + z}/{vbase + z}\n"); tris++;
                            }
                        }
                        vbase += pos.Count; objects++;
                    }
                    void Safe(string n, int mi, int ci, Func<float[], float[]> xf) { try { Mesh(n, mi, ci, xf); } catch (Exception ex) { skipped++; Console.WriteLine($"  {n}: mesh {mi} not exported ({ex.GetType().Name})"); } }
                    for (int ci = 0; ci < bsp.Clusters.Count; ci++) Safe($"cluster_{ci:000}", bsp.Clusters[ci].MeshIndex, 0, p => p);
                    for (int ii = 0; ii < bsp.InstancedGeometryInstances.Count; ii++)
                    {
                        var ins = bsp.InstancedGeometryInstances[ii]; int d = ins.DefinitionIndex;
                        if (res?.InstancedGeometry == null || d < 0 || d >= res.InstancedGeometry.Count) { skipped++; continue; }
                        var igd = res.InstancedGeometry[d]; float sc = ins.Scale == 0 ? 1 : ins.Scale; var mx = ins.Matrix;
                        Safe($"instance_{ii:0000}_{cache.StringTable.GetString(ins.Name)}", igd.MeshIndex, igd.CompressionIndex, p => new[] {
                            mx.m41 + sc * (p[0] * mx.m11 + p[1] * mx.m21 + p[2] * mx.m31),
                            mx.m42 + sc * (p[0] * mx.m12 + p[1] * mx.m22 + p[2] * mx.m32),
                            mx.m43 + sc * (p[0] * mx.m13 + p[1] * mx.m23 + p[2] * mx.m33) });
                    }
                    // collision: the structure collision BSP and every instance's collision BSP placed, faces as vertex loops
                    if (res?.CollisionBsps != null)
                    {
                        void Coll(string name, TagTool.Geometry.BspCollisionGeometry.CollisionGeometry c, Func<float[], float[]> xf)
                        {
                            if (c?.Surfaces == null || c.Surfaces.Count == 0) return;
                            sb.Append("o ").Append(name).Append('\n');
                            foreach (var v in c.Vertices) { var p = xf(new[] { v.Point.X, v.Point.Y, v.Point.Z }); sb.Append(string.Format(ic, "v {0:0.#####} {1:0.#####} {2:0.#####}\n", p[0], p[2], -p[1])); }
                            sb.Append("usemtl collision\n");
                            for (int si = 0; si < c.Surfaces.Count; si++)
                            {
                                var sf = c.Surfaces[si]; var loop = new List<int>(); int e = sf.FirstEdge, guard = 0;
                                do { if (e < 0 || e >= c.Edges.Count || guard++ > 4096) { loop.Clear(); break; } var ed = c.Edges[e]; if (ed.RightSurface == si) { loop.Add(ed.EndVertex); e = ed.ReverseEdge; } else { loop.Add(ed.StartVertex); e = ed.ForwardEdge; } } while (e != sf.FirstEdge);
                                if (loop.Count >= 3) sb.Append("f ").Append(string.Join(" ", loop.Select(x => (vbase + x).ToString()))).Append('\n');
                            }
                            vbase += c.Vertices.Count; objects++;
                        }
                        if (res.CollisionBsps.Count > 0) Coll("collision_structure", res.CollisionBsps[0], p => p);
                        for (int ii = 0; ii < bsp.InstancedGeometryInstances.Count; ii++)
                        {
                            var ins = bsp.InstancedGeometryInstances[ii]; int d = ins.DefinitionIndex; if (d < 0 || d >= res.InstancedGeometry.Count) continue;
                            float sc = ins.Scale == 0 ? 1 : ins.Scale; var mx = ins.Matrix;
                            Coll($"collision_instance_{ii:0000}", res.InstancedGeometry[d].CollisionInfo, p => new[] {
                                mx.m41 + sc * (p[0] * mx.m11 + p[1] * mx.m21 + p[2] * mx.m31), mx.m42 + sc * (p[0] * mx.m12 + p[1] * mx.m22 + p[2] * mx.m32), mx.m43 + sc * (p[0] * mx.m13 + p[1] * mx.m23 + p[2] * mx.m33) });
                        }
                    }
                    var file = Path.Combine(a[2], Path.GetFileName(t.Name) + ".obj");
                    File.WriteAllText(file, sb.ToString());
                    Console.WriteLine($"{file}: {objects} objects, {tris} triangles, {skipped} skipped");
                }
            return 0;
        }
    }
}
