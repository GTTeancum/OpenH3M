// collprobe <360 map>: read every structure BSP's collision resource back through TagTool and print its sizes
using System;
using System.IO;
using System.Linq;
using TagTool.Cache;
using TagTool.Tags.Definitions;

namespace Ho2H3
{
    static class CollProbe
    {
        public static int Run(string[] a)
        {
            var cache = GameCache.Open(new FileInfo(a[1]));
            using (var s = cache.OpenCacheRead())
                foreach (var t in cache.TagCache.NonNull().Where(t => t.IsInGroup("sbsp")))
                {
                    var bsp = cache.Deserialize<ScenarioStructureBsp>(s, t);
                    try
                    {
                        var r = cache.ResourceCache.GetStructureBspTagResources(bsp.CollisionBspResource);
                        Console.WriteLine($"{t.Name}: collision bsps {r?.CollisionBsps?.Count} instanced {r?.InstancedGeometry?.Count}");
                        if (r?.CollisionBsps != null && a.Length > 4) foreach (var c in r.CollisionBsps)
                        {
                            // point classification through the 3D BSP (front when on or in front of the plane)
                            float px = float.Parse(a[2]), py = float.Parse(a[3]), pz = float.Parse(a[4]);
                            int node = 0, depth = 0; string res = "?";
                            while (depth++ < 10000)
                            {
                                if (node < 0 || node >= c.Bsp3dNodes.Count) { res = "bad node " + node; break; }
                                var n = c.Bsp3dNodes[node]; var pl = c.Planes[n.Plane].Value;
                                float d = pl.Normal.I * px + pl.Normal.J * py + pl.Normal.K * pz - pl.Distance;
                                int child = d >= 0 ? n.FrontChild : n.BackChild;
                                if ((child & 0x800000) != 0) { int idx = TagTool.Geometry.BspCollisionGeometry.Bsp3dNode.GetChildIndex(child); res = idx < 0 ? "OUTSIDE (solid)" : $"leaf {idx} flags {c.Leaves[idx].Flags} refs {c.Leaves[idx].Bsp2dReferenceCount}"; break; }
                                node = child;
                            }
                            Console.WriteLine($"  point {px} {py} {pz}: {res} after {depth} nodes");
                        }
                        if (r?.CollisionBsps != null && r.CollisionBsps.Count > 0)
                        {
                            var c0 = r.CollisionBsps[0]; var all = new System.Collections.Generic.Dictionary<string, int>(); var sloped = new System.Collections.Generic.Dictionary<string, int>();
                            for (int si = 0; si < c0.Surfaces.Count; si++)
                            {
                                var sf = c0.Surfaces[si]; string k = $"{sf.Flags} (0x{(int)sf.Flags:X2})"; all[k] = all.TryGetValue(k, out var n1) ? n1 + 1 : 1;
                                int pi = sf.Plane & 0x7FFF; if (pi < c0.Planes.Count) { var nz = Math.Abs(c0.Planes[pi].Value.Normal.K); if (nz > 0.7 && nz < 0.99) sloped[k] = sloped.TryGetValue(k, out var n2) ? n2 + 1 : 1; }
                            }
                            int agree = 0, disagree = 0;
                            for (int si = 0; si < c0.Surfaces.Count; si++)
                            {
                                var sf = c0.Surfaces[si]; var loop = new System.Collections.Generic.List<int>(); int e = sf.FirstEdge, guard = 0;
                                do { if (e < 0 || e >= c0.Edges.Count || guard++ > 4096) { loop.Clear(); break; } var ed = c0.Edges[e]; if (ed.RightSurface == si) { loop.Add(ed.EndVertex); e = ed.ReverseEdge; } else { loop.Add(ed.StartVertex); e = ed.ForwardEdge; } } while (e != sf.FirstEdge);
                                if (loop.Count < 3) continue;
                                double nx = 0, ny = 0, nz = 0;
                                for (int k = 0; k < loop.Count; k++) { var va = c0.Vertices[loop[k]].Point; var vb = c0.Vertices[loop[(k + 1) % loop.Count]].Point; nx += (va.Y - vb.Y) * (va.Z + vb.Z); ny += (va.Z - vb.Z) * (va.X + vb.X); nz += (va.X - vb.X) * (va.Y + vb.Y); }
                                int pi = sf.Plane & 0x7FFF; if (pi >= c0.Planes.Count) continue; var pn = c0.Planes[pi].Value.Normal; double sgn = (sf.Plane & 0x8000) != 0 ? -1 : 1;
                                double d = sgn * (pn.I * nx + pn.J * ny + pn.K * nz); if (d > 0) agree++; else if (d < 0) disagree++;
                            }
                            Console.WriteLine($"  surface winding vs plane: {agree} agree, {disagree} disagree");
                            Console.WriteLine("  surface flags: " + string.Join("; ", all.Select(kv => $"{kv.Key} x{kv.Value}")));
                            Console.WriteLine("  sloped surface flags: " + string.Join("; ", sloped.Select(kv => $"{kv.Key} x{kv.Value}")));
                        }
                        if (r?.CollisionBsps != null) foreach (var c in r.CollisionBsps)
                        {
                            Console.WriteLine($"  nodes {c.Bsp3dNodes?.Count} planes {c.Planes?.Count} leaves {c.Leaves?.Count} 2dref {c.Bsp2dReferences?.Count} 2dnodes {c.Bsp2dNodes?.Count} surfaces {c.Surfaces?.Count} edges {c.Edges?.Count} vertices {c.Vertices?.Count}");
                            if (c.Bsp3dNodes?.Count > 0) { var n = c.Bsp3dNodes[0]; Console.WriteLine($"  node0 {string.Join(" ", n.GetType().GetFields().Select(f => f.Name + "=" + f.GetValue(n)))}"); }
                            if (c.Planes?.Count > 0) { var p = c.Planes[0]; Console.WriteLine($"  plane0 {p.Value}"); }
                            if (c.Vertices?.Count > 0) { var v = c.Vertices[0]; Console.WriteLine($"  vertex0 {v.Point}"); }
                        }
                        if (r?.InstancedGeometry != null) Console.WriteLine($"  instances with surfaces {r.InstancedGeometry.Count(i => i.CollisionInfo?.Surfaces?.Count > 0)}, with MOPP {r.InstancedGeometry.Count(i => i.CollisionMoppCodes?.Count > 0)}, MOPP bytes {r.InstancedGeometry.Sum(i => i.CollisionMoppCodes?.Sum(m => m.Data?.Count ?? 0) ?? 0)}");
                        foreach (var f in bsp.GetType().GetFields()) { var v = f.GetValue(bsp); if (v is System.Collections.IList l && f.FieldType.IsGenericType && f.FieldType.GetGenericArguments()[0].Name.Contains("Mopp")) Console.WriteLine($"  sbsp {f.Name}: {l.Count}"); }
                        var mcv = bsp.Geometry.MeshClusterVisibility; TagTool.Geometry.Mesh m0(int q) => bsp.Geometry.Meshes[q];
                        Console.WriteLine($"  meshes {bsp.Geometry.Meshes.Count} mesh cluster visibility {mcv?.Count}");
                        if (mcv != null) for (int q = 0; q < Math.Min(3, mcv.Count); q++)
                        {
                            var b = mcv[q].MoppCode; if (b == null || b.Length < 0x30) { Console.WriteLine($"   mcv{q}: empty"); continue; }
                            int size = b[0x24] << 24 | b[0x25] << 16 | b[0x26] << 8 | b[0x27];
                            var code = b.Skip(0x30).Take(size).ToList(); var keys = TagTool.Havok.HavokMoppUtil.GetAllKeys(code);
                            var m = bsp.Geometry.Meshes[q];
                            float Fl(int at) => BitConverter.ToSingle(new[] { b[at + 3], b[at + 2], b[at + 1], b[at] }, 0);
                            Console.WriteLine($"   mcv{q} info {Fl(0x10)} {Fl(0x14)} {Fl(0x18)} {Fl(0x1C)} | mesh type {m0(q).Type} rigid? compression count {bsp.Geometry.Compression.Count} c0 X {bsp.Geometry.Compression[0].X} Y {bsp.Geometry.Compression[0].Y} Z {bsp.Geometry.Compression[0].Z}; cluster using mesh: {bsp.Clusters.FindIndex(cl => cl.MeshIndex == q)} bounds {(bsp.Clusters.FindIndex(cl => cl.MeshIndex == q) is int ci && ci >= 0 ? bsp.Clusters[ci].BoundsX + " " + bsp.Clusters[ci].BoundsY + " " + bsp.Clusters[ci].BoundsZ : "-")}");
                            Console.WriteLine($"   mcv{q}: {b.Length} bytes, code {size}, keys [{string.Join(",", keys.Take(12).Select(k => "0x" + k.ToString("X")))}] reorder {mcv[q].MoppReorderTable?.Count} [{string.Join(",", mcv[q].MoppReorderTable.Take(12))}] | mesh parts {m.Parts.Count} subparts {m.SubParts.Count} instance buckets {m.InstanceBuckets?.Count}");
                        }
                        var pm = bsp.Physics.CollisionMoppCodes;
                        if (pm != null && pm.Count > 0 && r?.CollisionBsps?.Count > 0)
                        {
                            var keys = TagTool.Havok.HavokMoppUtil.GetAllKeys(pm[0].Data);
                            Console.WriteLine($"  structure MOPP: {pm[0].Data.Count} bytes, {keys.Count} keys, min 0x{keys.DefaultIfEmpty(0).Min():X} max 0x{keys.DefaultIfEmpty(0).Max():X}, distinct {keys.Distinct().Count()}, surfaces {r.CollisionBsps[0].Surfaces.Count}, high bits {keys.Count(k => (k & ~0xFFFF) != 0)}");
                        }
                        Console.WriteLine($"  sbsp instanced placements {bsp.InstancedGeometryInstances?.Count} clusters {bsp.Clusters?.Count}");
                        if (r?.InstancedGeometry?.Count > 0) { var ig = r.InstancedGeometry[0]; Console.WriteLine($"  instance0 nodes {ig.CollisionInfo?.Bsp3dNodes?.Count} surfaces {ig.CollisionInfo?.Surfaces?.Count} mopps {ig.CollisionMoppCodes?.Count} mesh {ig.MeshIndex}"); }
                    }
                    catch (Exception ex) { Console.WriteLine($"{t.Name}: {ex.GetType().Name} {ex.Message}"); }
                }
            return 0;
        }
    }
}
