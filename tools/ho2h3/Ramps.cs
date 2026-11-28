// Stair ramps. Halo 3 bipeds cannot climb real steps; stock Halo 3 levels lay invisible collision ramps over stairs.
// Reach's character movement climbs steps, so Reach levels (and the Halo Online ports of them) have ramps only in places
// (Reflection: a collision-only "walking surface" instance covers most stairs; the rest are bare steps). This finds every
// step face in the collision that has no ramp and lays a wedge over it:
//   step face: a vertical collision surface 0.08..maxHeight tall and at least 0.3 wide, with a walkable surface right
//   behind its top and floor right in front of its bottom, and nothing already above that floor (no existing ramp);
//   wedge: a closed triangular prism from the step's top edge down to the floor in front at a 35 degree slope.
// The wedges are added to the BSP's existing collision-only instance definition (in its own coordinates), whose collision
// BSP is then rebuilt with TagTool's builder, so instance and lightmap tables keep their sizes. Zones (map cfg) can allow
// taller faces in one place (Reflection's centre pool). Map-agnostic apart from the zones.
using System;
using System.Collections.Generic;
using System.Linq;
using TagTool.Common;
using TagTool.Geometry.BspCollisionGeometry;
using TagTool.Geometry.BspCollisionGeometry.Utils;
using TagTool.Tags;
using TagTool.Tags.Definitions;
using TagTool.Tags.Resources;

namespace Ho2H3
{
    public static class Ramps
    {
        public static List<(double x, double y, double r, double maxH, double zlo, double zhi)> Zones = new List<(double, double, double, double, double, double)>();
        const double MinH = 0.08, MaxH = 0.5, MinWidth = 0.3, Slope = 35;

        class Poly { public List<double[]> P; public short Material; public double[] N; }

        static double[] Newell(List<double[]> p)
        {
            double nx = 0, ny = 0, nz = 0;
            for (int k = 0; k < p.Count; k++) { var a = p[k]; var b = p[(k + 1) % p.Count]; nx += (a[1] - b[1]) * (a[2] + b[2]); ny += (a[2] - b[2]) * (a[0] + b[0]); nz += (a[0] - b[0]) * (a[1] + b[1]); }
            double l = Math.Sqrt(nx * nx + ny * ny + nz * nz); return l < 1e-9 ? null : new[] { nx / l, ny / l, nz / l };
        }

        static List<Poly> Polys(CollisionGeometry c, Func<double[], double[]> xf)
        {
            var list = new List<Poly>(); if (c?.Surfaces == null) return list;
            for (int si = 0; si < c.Surfaces.Count; si++)
            {
                var sf = c.Surfaces[si]; if (((int)sf.Flags & 0x10) != 0) continue;
                var loop = new List<int>(); int e = sf.FirstEdge, guard = 0;
                do { if (e < 0 || e >= c.Edges.Count || guard++ > 4096) { loop.Clear(); break; } var ed = c.Edges[e]; if (ed.RightSurface == si) { loop.Add(ed.EndVertex); e = ed.ReverseEdge; } else { loop.Add(ed.StartVertex); e = ed.ForwardEdge; } } while (e != sf.FirstEdge);
                if (loop.Count < 3) continue;
                var pts = loop.Select(v => xf(new double[] { c.Vertices[v].Point.X, c.Vertices[v].Point.Y, c.Vertices[v].Point.Z })).ToList();
                var n = Newell(pts); if (n == null) continue;
                list.Add(new Poly { P = pts, Material = sf.MaterialIndex, N = n });
            }
            return list;
        }

        // vertical ray caster over triangle-fanned polygons, bucketed on a 1-unit xy grid
        class Caster
        {
            readonly Dictionary<(int, int), List<double[][]>> _g = new Dictionary<(int, int), List<double[][]>>();
            public Caster(IEnumerable<Poly> polys)
            {
                foreach (var p in polys)
                {
                    if (Math.Abs(p.N[2]) < 0.05) continue;   // vertical faces never stop a vertical ray
                    for (int k = 1; k + 1 < p.P.Count; k++)
                    {
                        var t = new[] { p.P[0], p.P[k], p.P[k + 1] };
                        int x0 = (int)Math.Floor(t.Min(v => v[0])), x1 = (int)Math.Floor(t.Max(v => v[0])), y0 = (int)Math.Floor(t.Min(v => v[1])), y1 = (int)Math.Floor(t.Max(v => v[1]));
                        for (int x = x0; x <= x1; x++) for (int y = y0; y <= y1; y++) { if (!_g.TryGetValue((x, y), out var l)) _g[(x, y)] = l = new List<double[][]>(); l.Add(t); }
                    }
                }
            }
            // highest surface at (x, y) at or below z, or NaN
            public double Down(double x, double y, double z)
            {
                double best = double.NaN; if (!_g.TryGetValue(((int)Math.Floor(x), (int)Math.Floor(y)), out var l)) return best;
                foreach (var t in l)
                {
                    double d = (t[1][0] - t[0][0]) * (t[2][1] - t[0][1]) - (t[2][0] - t[0][0]) * (t[1][1] - t[0][1]); if (Math.Abs(d) < 1e-12) continue;
                    double u = ((x - t[0][0]) * (t[2][1] - t[0][1]) - (t[2][0] - t[0][0]) * (y - t[0][1])) / d, w = ((t[1][0] - t[0][0]) * (y - t[0][1]) - (x - t[0][0]) * (t[1][1] - t[0][1])) / d;
                    if (u < -1e-6 || w < -1e-6 || u + w > 1 + 1e-6) continue;
                    double hz = t[0][2] + u * (t[1][2] - t[0][2]) + w * (t[2][2] - t[0][2]);
                    if (hz <= z + 1e-6 && (double.IsNaN(best) || hz > best)) best = hz;
                }
                return best;
            }
        }

        public static void Build(ScenarioStructureBsp bsp, StructureBspTagResources res, string where, List<string> log)
        {
            if (res?.CollisionBsps == null || res.CollisionBsps.Count == 0 || res.InstancedGeometry == null || Environment.GetEnvironmentVariable("HO2H3_NO_RAMPS") == "1") return;
            var inst = bsp.InstancedGeometryInstances ?? new List<TagTool.Geometry.BspCollisionGeometry.InstancedGeometryInstance>();
            Func<double[], double[]> World(TagTool.Geometry.BspCollisionGeometry.InstancedGeometryInstance i)
            {
                float s = i.Scale == 0 ? 1 : i.Scale; var m = i.Matrix;
                return p => new[] { m.m41 + s * (p[0] * m.m11 + p[1] * m.m21 + p[2] * m.m31), m.m42 + s * (p[0] * m.m12 + p[1] * m.m22 + p[2] * m.m32), m.m43 + s * (p[0] * m.m13 + p[1] * m.m23 + p[2] * m.m33) };
            }
            // host: the instance whose collision gets the wedges (in its own coordinates). Preferred: a collision-only
            // definition used by exactly one instance; otherwise any collidable definition used by exactly one instance
            // (its look is unchanged; only its collision grows). Never the structure BSP: it also classifies inside /
            // outside the level, and closed wedges inside it crash the point classifier (0x820ABE50; tested 2026-11-23).
            // Reflection 000 and 001 have no collision-only instance, which left them without ramps.
            int host = -1, hostInst = -1; bool hostRenders = false;
            for (int pass = 0; pass < 2 && host < 0; pass++)
                for (int d = 0; d < res.InstancedGeometry.Count && host < 0; d++)
                {
                    var def = res.InstancedGeometry[d]; if (def.CollisionInfo?.Surfaces == null || def.CollisionInfo.Surfaces.Count == 0) continue;
                    bool noRender = def.MeshIndex < 0 || def.MeshIndex >= bsp.Geometry.Meshes.Count || bsp.Geometry.Meshes[def.MeshIndex].Parts.Count == 0;
                    if (pass == 0 && !noRender) continue;
                    var users = Enumerable.Range(0, inst.Count).Where(k => inst[k].DefinitionIndex == d).ToList();
                    if (users.Count != 1) continue;
                    var fl = inst[users[0]].Flags;
                    if ((fl & TagTool.Geometry.BspCollisionGeometry.InstancedGeometryInstance.InstancedGeometryFlags.RenderOnly) != 0) continue;
                    if (Math.Abs((inst[users[0]].Scale == 0 ? 1 : inst[users[0]].Scale) - 1) > 1e-3) continue;   // unscaled host keeps wedges exact
                    host = d; hostInst = users[0]; hostRenders = !noRender;
                }
            if (host < 0) { log.Add($"ramps: {where}: no single-use collidable instance to hold ramps; none added"); return; }
            // all collision in world space
            var all = Polys(res.CollisionBsps[0], p => p);
            for (int k = 0; k < inst.Count; k++) { int d = inst[k].DefinitionIndex; if (d >= 0 && d < res.InstancedGeometry.Count) all.AddRange(Polys(res.InstancedGeometry[d].CollisionInfo, World(inst[k]))); }
            var cast = new Caster(all);
            double run = 1 / Math.Tan(Slope * Math.PI / 180);
            var wedges = new List<(double[][] pts, short mat)>(); int faces = 0, skippedRamp = 0, skippedNoFloor = 0, skippedNoTread = 0, tall = 0;
            foreach (var p in all)
            {
                if (Math.Abs(p.N[2]) > 0.15) continue;
                double zmin = p.P.Min(v => v[2]), zmax = p.P.Max(v => v[2]), h = zmax - zmin;
                double hx = p.N[0], hy = p.N[1], hl = Math.Sqrt(hx * hx + hy * hy); if (hl < 1e-6) continue; hx /= hl; hy /= hl;
                double ux = -hy, uy = hx;   // along the face
                double smin = p.P.Min(v => v[0] * ux + v[1] * uy), smax = p.P.Max(v => v[0] * ux + v[1] * uy);
                if (smax - smin < MinWidth || h < MinH) continue;
                var cx = p.P.Average(v => v[0]); var cy = p.P.Average(v => v[1]);
                double maxH = MaxH; foreach (var zn in Zones) if ((cx - zn.x) * (cx - zn.x) + (cy - zn.y) * (cy - zn.y) <= zn.r * zn.r && zmin >= zn.zlo && zmin <= zn.zhi) maxH = Math.Max(maxH, zn.maxH);
                if (h > maxH) { if (h < 1.0) { tall++; if (Environment.GetEnvironmentVariable("HO2H3_RAMP_PROBE") is string pr) { var q = pr.Split(',').Select(double.Parse).ToArray(); if ((cx - q[0]) * (cx - q[0]) + (cy - q[1]) * (cy - q[1]) < q[2] * q[2]) log.Add($"ramps probe: tall face at {cx:0.00},{cy:0.00} z {zmin:0.00}..{zmax:0.00} h {h:0.00} width {smax - smin:0.00}"); } } continue; }
                faces++;
                // origin on the face's own plane at its centre column
                double oc = (smin + smax) / 2, d0 = cx * hx + cy * hy;   // signed offset of the face along its normal
                double mx = ux * oc + hx * d0, my = uy * oc + hy * d0;
                bool probe = false; if (Environment.GetEnvironmentVariable("HO2H3_RAMP_PROBE") is string pr2) { var q = pr2.Split(',').Select(double.Parse).ToArray(); probe = (cx - q[0]) * (cx - q[0]) + (cy - q[1]) * (cy - q[1]) < q[2] * q[2] && zmin < 241.5; }
                if (probe) log.Add($"ramps probe: face {cx:0.00},{cy:0.00} z {zmin:0.00}..{zmax:0.00} n {hx:0.00},{hy:0.00}: floor in front {cast.Down(mx + hx * 0.15, my + hy * 0.15, zmin + 0.06):0.00} tread behind {cast.Down(mx - hx * 0.05, my - hy * 0.05, zmax + 0.06):0.00} above front {cast.Down(mx + hx * 0.1, my + hy * 0.1, zmax + 0.3):0.00} behind within 1.2 {cast.Down(mx - hx * 0.05, my - hy * 0.05, zmax + 1.2):0.00} behind 0.3 {cast.Down(mx - hx * 0.3, my - hy * 0.3, zmax + 1.2):0.00}");
                // floor in front: at the face's foot or up to 0.3 lower (a face split in two, a stepped floor); the wedge runs
                // down to it, within the height limit
                double floorZ = cast.Down(mx + hx * 0.15, my + hy * 0.15, zmin + 0.06);
                if (double.IsNaN(floorZ) || floorZ > zmin + 0.06 || floorZ < zmin - 0.3 || zmax - floorZ > maxH) { skippedNoFloor++; continue; }
                zmin = Math.Min(zmin, floorZ); h = zmax - zmin;
                double treadZ = cast.Down(mx - hx * 0.05, my - hy * 0.05, zmax + 0.06);
                if (double.IsNaN(treadZ) || Math.Abs(treadZ - zmax) > 0.06) { skippedNoTread++; continue; }
                double above = cast.Down(mx + hx * 0.1, my + hy * 0.1, zmax + 0.3);
                if (!double.IsNaN(above) && above > zmin + 0.04) { skippedRamp++; continue; }
                double len = h * run;
                double[] P(double s, double off, double z) => new[] { ux * s + hx * (d0 + off), uy * s + hy * (d0 + off), z };
                // prism: a/b = the two ends along the face; t = top edge, o = bottom edge at the face, f = far bottom
                var at = P(smin, 0, zmax); var bt = P(smax, 0, zmax); var ao = P(smin, 0, zmin); var bo = P(smax, 0, zmin); var af = P(smin, len, zmin); var bf = P(smax, len, zmin);
                wedges.Add((new[] { at, bt, bo, ao, af, bf }, p.Material));
                // test points for an in-game check (HO2H3_RAMP_POINTS=file): a quarter of the way down the slope, where the
                // ramp is three quarters of the step high and the bare floor is at the step's foot
                if (Environment.GetEnvironmentVariable("HO2H3_RAMP_POINTS") is string rp) { var q = P(oc, len * 0.25, zmin + 0.75 * h); System.IO.File.AppendAllText(rp, $"{q[0]:0.000} {q[1]:0.000} {q[2]:0.000} 0 # ramp {zmin + 0.75 * h:0.000} floor {zmin:0.000} {where}" + Environment.NewLine); }
            }
            if (wedges.Count == 0 && Environment.GetEnvironmentVariable("HO2H3_RAMPS_REBUILD_ONLY") != "1") { log.Add($"ramps: {where}: {faces} step faces, none need a ramp ({skippedRamp} already ramped, {skippedNoFloor} no floor, {skippedNoTread} no tread, {tall} taller than allowed)"); return; }
            // into the host's own coordinates (inverse of its orthonormal transform)
            var hi0 = inst[hostInst]; float hs = hi0.Scale == 0 ? 1 : hi0.Scale; var hm = hi0.Matrix;
            double[] Local(double[] w) { double dx = w[0] - hm.m41, dy = w[1] - hm.m42, dz = w[2] - hm.m43; return new[] { (dx * hm.m11 + dy * hm.m12 + dz * hm.m13) / hs, (dx * hm.m21 + dy * hm.m22 + dz * hm.m23) / hs, (dx * hm.m31 + dy * hm.m32 + dz * hm.m33) / hs }; }
            var geo = res.InstancedGeometry[host].CollisionInfo;
            int addedSurfaces = 0;
            if (Environment.GetEnvironmentVariable("HO2H3_RAMPS_REBUILD_ONLY") == "1") wedges.Clear();   // diagnostic: rebuild, add nothing
            foreach (var (w, mat) in wedges)
            {
                var v = w.Select(Local).ToArray();   // 0 at, 1 bt, 2 bo, 3 ao, 4 af, 5 bf
                // faces with outward winding (checked against the wedge centre below)
                var faceLoops = new List<int[]> { new[] { 0, 3, 4 }, new[] { 1, 5, 2 }, new[] { 0, 4, 5, 1 }, new[] { 3, 2, 5, 4 }, new[] { 0, 1, 2, 3 } };
                var cen = new[] { v.Average(q => q[0]), v.Average(q => q[1]), v.Average(q => q[2]) };
                for (int f = 0; f < faceLoops.Count; f++)
                {
                    var n = Newell(faceLoops[f].Select(i => v[i]).ToList()); if (n == null) continue;
                    var c0 = v[faceLoops[f][0]]; if ((c0[0] - cen[0]) * n[0] + (c0[1] - cen[1]) * n[1] + (c0[2] - cen[2]) * n[2] < 0) faceLoops[f] = System.Linq.Enumerable.Reverse(faceLoops[f]).ToArray();
                }
                AddClosed(geo, v, faceLoops, mat); addedSurfaces += faceLoops.Count;
            }
            // rebuild the host's collision BSP with TagTool's builder
            var rz = new ResizeCollisionBSP(); var large = rz.GrowCollisionBsp(geo);
            var builder = new LargeCollisionBSPBuilder();
            int fb0 = CollisionSimplify.FallbackUsed;
            if (!CollisionSimplify.GenerateBsp(ref large) || !rz.collision_bsp_check_counts(large)) { log.Add($"ramps: {where}: collision BSP rebuild failed; ramps not added"); return; }
            res.InstancedGeometry[host].CollisionInfo = rz.ShrinkCollisionBsp(large);
            log.Add($"ramps: {where}: {wedges.Count} ramps added to instance {hostInst} ({(hostRenders ? "a visible piece; look unchanged" : "collision-only")}, {addedSurfaces} surfaces, {(CollisionSimplify.FallbackUsed > fb0 ? "empty-leaf fallback" : "builder verified")}) over {faces} step faces ({skippedRamp} already ramped, {skippedNoFloor} no floor, {skippedNoTread} no tread, {tall} taller than allowed)");
        }

        // a closed polyhedron appended as its own manifold component (edges shared only within it)
        static void AddClosed(CollisionGeometry g, double[][] v, List<int[]> loops, short mat)
        {
            int vb = g.Vertices.Count;
            foreach (var p in v) g.Vertices.Add(new Vertex { Point = new RealPoint3d((float)p[0], (float)p[1], (float)p[2]), FirstEdge = 0xFFFF });
            var edgeOf = new Dictionary<(int, int), int>(); var surfEdges = new List<List<int>>();
            int sb = g.Surfaces.Count;
            for (int f = 0; f < loops.Count; f++)
            {
                int s = sb + f; var lp = loops[f]; var es = new List<int>();
                for (int i = 0; i < lp.Length; i++)
                {
                    int a = vb + lp[i], b = vb + lp[(i + 1) % lp.Length];
                    if (edgeOf.TryGetValue((b, a), out int e) && g.Edges[e].RightSurface == 0xFFFF) { g.Edges[e].RightSurface = (ushort)s; }
                    else { e = g.Edges.Count; g.Edges.Add(new Edge { StartVertex = (ushort)a, EndVertex = (ushort)b, LeftSurface = (ushort)s, RightSurface = 0xFFFF, ForwardEdge = 0xFFFF, ReverseEdge = 0xFFFF }); edgeOf[(a, b)] = e; }
                    es.Add(e);
                    if (g.Vertices[a].FirstEdge == 0xFFFF) g.Vertices[a].FirstEdge = (ushort)e;
                }
                surfEdges.Add(es);
                // plane from the outward winding
                var n = Newell(lp.Select(i => v[i]).ToList()); var p0 = v[lp[0]];
                g.Planes.Add(new TagTool.Geometry.BspCollisionGeometry.Plane { Value = new RealPlane3d((float)n[0], (float)n[1], (float)n[2], (float)(n[0] * p0[0] + n[1] * p0[1] + n[2] * p0[2])) });
                g.Surfaces.Add(new Surface { Plane = (ushort)(g.Planes.Count - 1), FirstEdge = (ushort)es[0], MaterialIndex = mat, BreakableSurfaceIndex = 0xFF, BestPlaneCalculationVertex = 0 });
            }
            for (int f = 0; f < loops.Count; f++)
            {
                int s = sb + f; var es = surfEdges[f];
                for (int i = 0; i < es.Count; i++) { var ed = g.Edges[es[i]]; int next = es[(i + 1) % es.Count]; if (ed.LeftSurface == s) ed.ForwardEdge = (ushort)next; else ed.ReverseEdge = (ushort)next; }
            }
        }
    }
}
