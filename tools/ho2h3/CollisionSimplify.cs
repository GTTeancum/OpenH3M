// Level collision too detailed for Halo 3's collision BSP format (16-bit counts), even with a rebuilt tree: the collision
// mesh is reduced the way this project's working native Battle Canyon draft did it (tools\stock-h3-audit\NATIVE-DRAFT.md,
// export_360_collision_draft.py; user rule 2026-10-25 "simplify rock and terrain collision ... preserving visible geometry"):
// Blender's standard planar dissolve (Decimate modifier, DISSOLVE, angle limit 30 degrees, material delimit) - faces are
// merged only with near-flat neighbours of the same material and every remaining vertex keeps its exact source position.
// Render geometry is untouched. Blender runs headless (-b, no window) as a thin driver of the official tool.
//   1. surfaces -> OBJ polygons, one material per (material, flags) pair
//   2. Blender: import, dissolve, triangulate, export (axes kept: forward Y, up Z)
//   3. rebuilt as Halo 3 collision geometry: edges/surfaces built here, planes and coplanar merging by TagTool's
//      ImportCollisionGeometryCommand (generate_surface_plane, reduce_collision_geometry), the tree by LargeCollisionBSPBuilder
// If 30 degrees does not fit, larger limits are tried in steps; the smallest that fits is kept and logged. Map-agnostic.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using TagTool.Cache;
using TagTool.Cache.HaloOnline;
using TagTool.Common;
using TagTool.Geometry.BspCollisionGeometry;
using TagTool.Geometry.BspCollisionGeometry.Utils;
using TagTool.Tags;

namespace Ho2H3
{
    public static class CollisionSimplify
    {
        public static string Blender = Environment.GetEnvironmentVariable("HO2H3_BLENDER") ?? @"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe";

        public static LargeCollisionBspBlock Run(GameCache cache, LargeCollisionBspBlock lb, string where, List<string> log)
        {
            // 1. polygons by (material, flags) pair
            var pairs = new List<(short mat, byte flags)>(); var pairIx = new Dictionary<(short, byte), int>();
            var polys = new List<(List<int> loop, int pair)>();
            for (int s = 0; s < lb.Surfaces.Count; s++)
            {
                var sf = lb.Surfaces[s]; var loop = new List<int>(); int e = sf.FirstEdge, guard = 0;
                do
                {
                    if (e < 0 || e >= lb.Edges.Count || guard++ > 4096) { loop.Clear(); break; }
                    var ed = lb.Edges[e];
                    if (ed.RightSurface == s) { loop.Add(ed.EndVertex); e = ed.ReverseEdge; } else { loop.Add(ed.StartVertex); e = ed.ForwardEdge; }
                } while (e != sf.FirstEdge);
                if (loop.Count < 3) continue;
                var key = (sf.Material, (byte)((byte)sf.Flags & 0x7F));   // plane negation is recomputed
                if (!pairIx.TryGetValue(key, out int pk)) { pk = pairs.Count; pairs.Add(key); pairIx[key] = pk; }
                polys.Add((loop, pk));
            }
            var dir = Path.Combine(Path.GetTempPath(), "ho2h3_dissolve_" + Guid.NewGuid().ToString("N").Substring(0, 8)); Directory.CreateDirectory(dir);
            var ic = CultureInfo.InvariantCulture;
            var src = Path.Combine(dir, "in.obj");
            using (var w = new StreamWriter(src))
            {
                foreach (var v in lb.Vertices) w.WriteLine(string.Format(ic, "v {0:R} {1:R} {2:R}", v.Point.X, v.Point.Y, v.Point.Z));
                foreach (var grp in polys.GroupBy(p => p.pair))
                {
                    w.WriteLine("g p" + grp.Key);
                    w.WriteLine("usemtl p" + grp.Key);
                    foreach (var p in grp) w.WriteLine("f " + string.Join(" ", p.loop.Select(i => (i + 1).ToString(ic))));
                }
            }
            var rz = new ResizeCollisionBSP();
            try
            {
                foreach (var deg in new[] { 30, 40, 50, 60 })
                {
                    // 2. Blender planar dissolve
                    var outp = Path.Combine(dir, $"out{deg}.obj"); var py = Path.Combine(dir, "dissolve.py");
                    var script = new StringBuilder();
                    script.AppendLine("import bpy, math");
                    script.AppendLine("bpy.ops.wm.read_factory_settings(use_empty=True)");
                    script.AppendLine($"bpy.ops.wm.obj_import(filepath=r'{src}', forward_axis='Y', up_axis='Z')");
                    script.AppendLine("obs = [o for o in bpy.context.scene.objects if o.type == 'MESH']");
                    script.AppendLine("for o in obs: o.select_set(True)");
                    script.AppendLine("bpy.context.view_layer.objects.active = obs[0]");
                    script.AppendLine("if len(obs) > 1: bpy.ops.object.join()");
                    script.AppendLine("ob = bpy.context.view_layer.objects.active");
                    script.AppendLine("m = ob.modifiers.new('dissolve', 'DECIMATE'); m.decimate_type = 'DISSOLVE'");
                    script.AppendLine($"m.angle_limit = math.radians({deg}); m.delimit = {{'MATERIAL'}}");
                    script.AppendLine("bpy.ops.object.modifier_apply(modifier=m.name)");
                    script.AppendLine("t = ob.modifiers.new('tri', 'TRIANGULATE'); bpy.ops.object.modifier_apply(modifier=t.name)");
                    script.AppendLine($"bpy.ops.wm.obj_export(filepath=r'{outp}', forward_axis='Y', up_axis='Z', export_materials=False, export_material_groups=True, export_normals=False, export_uv=False, apply_modifiers=True)");
                    File.WriteAllText(py, script.ToString());
                    var psi = new ProcessStartInfo(Blender, $"-b --factory-startup --python \"{py}\"") { UseShellExecute = false, CreateNoWindow = true, RedirectStandardOutput = true, RedirectStandardError = true, WindowStyle = ProcessWindowStyle.Hidden };
                    string bout;
                    using (var pr = Process.Start(psi)) { bout = pr.StandardOutput.ReadToEnd() + pr.StandardError.ReadToEnd(); pr.WaitForExit(); }
                    if (!File.Exists(outp)) { log.Add($"collision dissolve: {where}: Blender produced no output at {deg} degrees: {bout.Substring(Math.Max(0, bout.Length - 400))}"); return null; }
                    // 3. triangles back (positions are the source values; material groups give the pair)
                    var pos = new List<float>(); var idx = new List<uint>(); var triPair = new List<int>(); int cur = 0;
                    foreach (var line in File.ReadLines(outp))
                    {
                        if (line.StartsWith("v ")) { var f = line.Split(' ', StringSplitOptions.RemoveEmptyEntries); pos.Add(float.Parse(f[1], ic)); pos.Add(float.Parse(f[2], ic)); pos.Add(float.Parse(f[3], ic)); }
                        else if (line.StartsWith("usemtl ") || line.StartsWith("g "))
                        {
                            var nm = line.Substring(line.IndexOf(' ') + 1).Trim(); int u = nm.LastIndexOf('p');
                            if (u >= 0 && int.TryParse(nm.Substring(u + 1), out var q)) cur = q;
                        }
                        else if (line.StartsWith("f "))
                        {
                            var f = line.Split(' ', StringSplitOptions.RemoveEmptyEntries).Skip(1).Select(x => uint.Parse(x.Split('/')[0], ic) - 1).ToList();
                            for (int i = 1; i + 1 < f.Count; i++) { idx.Add(f[0]); idx.Add(f[i]); idx.Add(f[i + 1]); triPair.Add(cur); }
                        }
                    }
                    var g = Build(cache, idx.ToArray(), idx.Count, pos.ToArray(), (t, a, b, c) => triPair[t], pairs, out int dropped, out string why);
                    if (g == null) { log.Add($"collision dissolve: {where}: {deg} degrees ({idx.Count / 3} triangles): {why}"); continue; }
                    var large = rz.GrowCollisionBsp(g);
                    bool ok = GenerateBsp(ref large) && rz.collision_bsp_check_counts(large);
                    log.Add($"collision dissolve: {where}: {polys.Count} source polygons -> {idx.Count / 3} triangles (planar dissolve {deg} degrees, material delimit, vertex positions unchanged), " +
                            $"{dropped} degenerate/non-manifold handled, {g.Surfaces.Count} surfaces after merging, nodes {large.Bsp3dNodes?.Count}, 2D refs {large.Bsp2dReferences?.Count} -> {(ok ? "fits" : "too large")}{(Why != null ? " (" + Why + ")" : "")}");
                    if (ok) return large;
                }
                return null;
            }
            finally { try { Directory.Delete(dir, true); } catch { } }
        }

        // TagTool's LargeCollisionBSPBuilder.generate_bsp, accepting empty leaves: its verifier rejects a leaf with no 2D
        // references (FirstBsp2dReference 0xFFFFFFFF fails its range test) although its next test requires exactly that
        // value for empty leaves, so any open spot fails the whole build. When generate_bsp fails, the built tree is taken
        // from the builder, checked here with empty leaves allowed, and finished with the builder's own pruning step.
        public static string Why;
        public static int FallbackUsed;   // rebuilds that needed the empty-leaf fallback
        public static bool GenerateBsp(ref LargeCollisionBspBlock bsp)
        {
            Why = null;
            var b = new LargeCollisionBSPBuilder();
            if (b.generate_bsp(ref bsp, false)) { Why = null; return true; }
            FallbackUsed++;
            const BindingFlags F = BindingFlags.Instance | BindingFlags.NonPublic | BindingFlags.Public;
            var fBsp = typeof(LargeCollisionBSPBuilder).GetField("Bsp", F); var pBsp = typeof(LargeCollisionBSPBuilder).GetProperty("Bsp", F);
            var t = (LargeCollisionBspBlock)(fBsp != null ? fBsp.GetValue(b) : pBsp?.GetValue(b));
            if (t == null || t.Bsp3dNodes == null || t.Bsp3dNodes.Count == 0 || t.Leaves == null || t.Leaves.Count == 0) { Why = $"no tree in the builder (field {fBsp != null}, property {pBsp != null}, nodes {t?.Bsp3dNodes?.Count}, leaves {t?.Leaves?.Count})"; return false; }
            foreach (var n in t.Bsp3dNodes)
                foreach (var c in new[] { n.BackChild, n.FrontChild })
                    if (c != -1 && (c & 0x7FFFFFFF) >= ((c & 0x80000000u) != 0 ? t.Leaves.Count : t.Bsp3dNodes.Count)) { Why = "bad node child"; return false; }
            foreach (var l in t.Leaves)
            {
                if (l.Bsp2dReferenceCount == 0) { if (l.FirstBsp2dReference != uint.MaxValue) { Why = "empty leaf with a reference index"; return false; } continue; }
                if (l.FirstBsp2dReference + l.Bsp2dReferenceCount > t.Bsp2dReferences.Count) { Why = "leaf references out of range"; return false; }
            }
            if (!(bool)typeof(LargeCollisionBSPBuilder).GetMethod("prune_node_tree", F).Invoke(b, null)) { Why = "pruning failed"; return false; }
            bsp = ((LargeCollisionBspBlock)(fBsp != null ? fBsp.GetValue(b) : pBsp.GetValue(b))).DeepClone();
            return true;
        }

        static CollisionGeometry Build(GameCache cache, uint[] idx, int count, float[] pos, Func<int, int, int, int, int> pairOf, List<(short mat, byte flags)> pairs, out int dropped, out string why)
        {
            dropped = 0; why = null;
            var g = new CollisionGeometry
            {
                Bsp3dNodes = new TagBlock<Bsp3dNode>(), Planes = new TagBlock<Plane>(), Leaves = new TagBlock<Leaf>(), Bsp2dReferences = new TagBlock<Bsp2dReference>(),
                Bsp2dNodes = new TagBlock<Bsp2dNode>(), Surfaces = new TagBlock<Surface>(), Edges = new TagBlock<Edge>(), Vertices = new TagBlock<Vertex>()
            };
            var vmap = new Dictionary<int, int>(); var edgeOf = new Dictionary<(int, int), int>();
            int V(int src)
            {
                if (vmap.TryGetValue(src, out int v)) return v;
                v = g.Vertices.Count; g.Vertices.Add(new Vertex { Point = new RealPoint3d(pos[src * 3], pos[src * 3 + 1], pos[src * 3 + 2]), FirstEdge = 0xFFFF }); vmap[src] = v; return v;
            }
            // TagTool's importer class is internal: created by name
            var T = typeof(LargeCollisionBSPBuilder).Assembly.GetTypes().First(x => x.Name == "ImportCollisionGeometryCommand");
            var cmd = Activator.CreateInstance(T, BindingFlags.Instance | BindingFlags.NonPublic | BindingFlags.Public, null, new object[] { (GameCacheHaloOnlineBase)cache }, null);
            const BindingFlags F = BindingFlags.Instance | BindingFlags.NonPublic | BindingFlags.Public;
            T.GetProperty("Bsp", F).SetValue(cmd, g);
            var genPlane = T.GetMethod("generate_surface_plane", F);
            for (int t = 0; t + 2 < count; t += 3)
            {
                int sa = (int)idx[t], sb = (int)idx[t + 1], sc = (int)idx[t + 2];
                if (sa == sb || sb == sc || sa == sc) { dropped++; continue; }
                // zero-area triangles carry no collision
                {
                    double ax = pos[sa * 3], ay = pos[sa * 3 + 1], az = pos[sa * 3 + 2];
                    double ux = pos[sb * 3] - ax, uy = pos[sb * 3 + 1] - ay, uz = pos[sb * 3 + 2] - az, wx = pos[sc * 3] - ax, wy = pos[sc * 3 + 1] - ay, wz = pos[sc * 3 + 2] - az;
                    double cx = uy * wz - uz * wy, cy = uz * wx - ux * wz, cz = ux * wy - uy * wx, area2 = Math.Sqrt(cx * cx + cy * cy + cz * cz);
                    double l1 = ux * ux + uy * uy + uz * uz, l2 = wx * wx + wy * wy + wz * wz, l3 = (ux - wx) * (ux - wx) + (uy - wy) * (uy - wy) + (uz - wz) * (uz - wz);
                    double longest = Math.Sqrt(Math.Max(l1, Math.Max(l2, l3)));
                    if (area2 < 1e-9) { dropped++; continue; }   // no area at all (long thin triangles from triangulation are kept)
                }
                // an edge may join at most two surfaces, each direction once
                bool bad = false;
                foreach (var (p, q) in new[] { (sa, sb), (sb, sc), (sc, sa) })
                {
                    if (vmap.TryGetValue(p, out int vp) && vmap.TryGetValue(q, out int vq) && (edgeOf.ContainsKey((vp, vq)) || (edgeOf.TryGetValue((vq, vp), out int eo) && g.Edges[eo].RightSurface != 0xFFFF))) bad = true;
                }
                int a, b, c;
                if (bad)
                {
                    // a third surface on an edge: kept as its own piece on vertices of its own (no hole), not joined to neighbours
                    dropped++;
                    int Fresh(int src) { int v = g.Vertices.Count; g.Vertices.Add(new Vertex { Point = new RealPoint3d(pos[src * 3], pos[src * 3 + 1], pos[src * 3 + 2]), FirstEdge = 0xFFFF }); return v; }
                    a = Fresh(sa); b = Fresh(sb); c = Fresh(sc);
                }
                else { a = V(sa); b = V(sb); c = V(sc); }
                if (g.Vertices.Count > 0xFFFE || g.Edges.Count > 0xFFFB || g.Surfaces.Count > 0xFFFE) { why = "over 16-bit counts"; return null; }
                int s = g.Surfaces.Count;
                g.Surfaces.Add(new Surface { Plane = 0xFFFF, MaterialIndex = (short)pairOf(t / 3, sa, sb, sc), BreakableSurfaceIndex = 0xFF });
                var es = new int[3]; var vs = new[] { a, b, c };
                for (int i = 0; i < 3; i++)
                {
                    int p = vs[i], q = vs[(i + 1) % 3];
                    if (edgeOf.TryGetValue((q, p), out int e)) g.Edges[e].RightSurface = (ushort)s;
                    else { e = g.Edges.Count; g.Edges.Add(new Edge { StartVertex = (ushort)p, EndVertex = (ushort)q, LeftSurface = (ushort)s, RightSurface = 0xFFFF, ForwardEdge = 0xFFFF, ReverseEdge = 0xFFFF }); edgeOf[(p, q)] = e; }
                    es[i] = e;
                    if (g.Vertices[p].FirstEdge == 0xFFFF) g.Vertices[p].FirstEdge = (ushort)e;
                }
                for (int i = 0; i < 3; i++) { var ed = g.Edges[es[i]]; int next = es[(i + 1) % 3]; if (ed.LeftSurface == s) ed.ForwardEdge = (ushort)next; else ed.ReverseEdge = (ushort)next; }
                g.Surfaces[s].FirstEdge = (ushort)es.Min();
                if (!(bool)genPlane.Invoke(cmd, new object[] { s })) { why = "plane generation failed"; return null; }
            }
            // coplanar neighbours with the same (material, flags) pair merged into polygons of up to 8 edges (TagTool)
            if (!(bool)T.GetMethod("reduce_collision_geometry", F).Invoke(cmd, null)) { why = "surface merging failed"; return null; }
            g = (CollisionGeometry)T.GetProperty("Bsp", F).GetValue(cmd);
            foreach (var sf in g.Surfaces) { var (mat, flags) = pairs[sf.MaterialIndex]; sf.MaterialIndex = mat; sf.Flags = (SurfaceFlags)(((byte)sf.Flags & 0x80) | flags); }
            return g;
        }
    }
}
