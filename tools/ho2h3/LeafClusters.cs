// Structure leaf -> cluster table. Halo 3 finds the camera's cluster by walking the structure collision BSP to a leaf and
// reading that leaf's cluster from the structure BSP's Leaves block, so the block must have one entry per collision BSP
// leaf, in the same order (stock Guardian: 11305 and 11305). Halo Online's Reach ports ship a Leaves block that does not
// match their collision BSP (Sword Base 3308 vs 1109), and rebuilt collision trees (limits, two-sided cleanup) renumber
// leaves (Breakneck 28538 vs 17018); the camera then lands in the wrong cluster or none, and the level draws as hall of
// mirrors with pieces missing (user play test 2026-11-23). When the counts differ, the table is rebuilt: a grid of points
// over the collision geometry's bounds is walked down the shipped collision BSP; each point votes for the smallest
// cluster box that contains it (else the nearest box); each leaf takes its majority cluster; leaves no point reached take the cluster nearest their surfaces (or
// the nearest cluster box). Map-agnostic.
using System;
using System.Collections.Generic;
using System.Linq;
using TagTool.Geometry.BspCollisionGeometry;
using TagTool.Tags.Definitions;

namespace Ho2H3
{
    public static class LeafClusters
    {
        // the source's own tree and leaf table, when they match (all Halo Online maps checked: Sword Base 3308/3308,
        // Breakneck 28538/28538, Battle Canyon 80846/80846): an exact point -> cluster oracle for the rebuilt table
        public static LargeCollisionBspBlock OrigTree; public static byte[] OrigLeafCluster;
        static int OrigCluster(double x, double y, double z)
        {
            var t = OrigTree; if (t?.Bsp3dNodes == null || t.Bsp3dNodes.Count == 0 || OrigLeafCluster == null) return -1;
            int node = 0, guard = 0;
            while (guard++ < 8192)
            {
                var nd = t.Bsp3dNodes[node];
                bool neg = (nd.Plane & 0x80000000) != 0; int pi = nd.Plane & 0x7FFFFFFF; if (pi >= t.Planes.Count) return -1;
                var p = t.Planes[pi].Value; double d = p.I * x + p.J * y + p.K * z - p.D; if (neg) d = -d;
                int child = d >= 0 ? nd.FrontChild : nd.BackChild;
                if (child == -1) return -1;
                if ((child & 0x80000000) != 0) { int lf = child & 0x7FFFFFFF; return lf < OrigLeafCluster.Length && OrigLeafCluster[lf] != 255 ? OrigLeafCluster[lf] : -1; }
                node = child; if (node >= t.Bsp3dNodes.Count) return -1;
            }
            return -1;
        }
        public static void Fix(ScenarioStructureBsp bsp, CollisionGeometry col, string where, List<string> log)
        {
            if (col?.Leaves == null || col.Bsp3dNodes == null || bsp.Clusters == null || bsp.Clusters.Count == 0) return;
            int n = col.Leaves.Count;
            bool rebuild = bsp.Leaves == null || bsp.Leaves.Count != n;
            var checks = new List<(int leaf, byte cluster)>();   // points the source's own tree places: (leaf here, source cluster)
            var cl = bsp.Clusters;
            double Vol(int k) => (cl[k].BoundsX.Upper - cl[k].BoundsX.Lower) * (cl[k].BoundsY.Upper - cl[k].BoundsY.Lower) * (cl[k].BoundsZ.Upper - cl[k].BoundsZ.Lower);
            int BoxCluster(double x, double y, double z)
            {
                int best = -1; double bv = double.MaxValue;
                for (int k = 0; k < cl.Count; k++)
                {
                    var c = cl[k];
                    if (x < c.BoundsX.Lower || x > c.BoundsX.Upper || y < c.BoundsY.Lower || y > c.BoundsY.Upper || z < c.BoundsZ.Lower || z > c.BoundsZ.Upper) continue;
                    double v = Vol(k); if (v < bv) { bv = v; best = k; }
                }
                return best;
            }
            int Nearest(double x, double y, double z)
            {
                int best = 0; double bd = double.MaxValue;
                for (int k = 0; k < cl.Count; k++)
                {
                    var c = cl[k];
                    double dx = Math.Max(0, Math.Max(c.BoundsX.Lower - x, x - c.BoundsX.Upper)), dy = Math.Max(0, Math.Max(c.BoundsY.Lower - y, y - c.BoundsY.Upper)), dz = Math.Max(0, Math.Max(c.BoundsZ.Lower - z, z - c.BoundsZ.Upper));
                    double d = dx * dx + dy * dy + dz * dz; if (d < bd) { bd = d; best = k; }
                }
                return best;
            }
            int Leaf(double x, double y, double z)
            {
                int node = 0, guard = 0;
                while (guard++ < 4096)
                {
                    var nd = col.Bsp3dNodes[node];
                    int pi = nd.Plane & 0x7FFF; bool neg = (nd.Plane & 0x8000) != 0;
                    if (pi >= col.Planes.Count) return -1;
                    var p = col.Planes[pi].Value;
                    double d = p.I * x + p.J * y + p.K * z - p.D; if (neg) d = -d;
                    int child = d >= 0 ? nd.FrontChild : nd.BackChild;
                    if (child == 0xFFFFFF) return -1;
                    if ((child & 0x800000) != 0) return child & 0x7FFFFF;
                    node = child; if (node >= col.Bsp3dNodes.Count) return -1;
                }
                return -1;
            }
            // grid over the clusters' bounds: about 600k points at most
            // grid over the collision geometry's own bounds (cluster boxes can be huge), about 3 million points at most
            var vs = col.Vertices;
            double x0 = vs.Min(v => (double)v.Point.X) - 1, x1 = vs.Max(v => (double)v.Point.X) + 1, y0 = vs.Min(v => (double)v.Point.Y) - 1, y1 = vs.Max(v => (double)v.Point.Y) + 1, z0 = vs.Min(v => (double)v.Point.Z) - 1, z1 = vs.Max(v => (double)v.Point.Z) + 1;
            double vol = Math.Max(1e-3, (x1 - x0) * (y1 - y0) * (z1 - z0)), step = Math.Max(0.1, Math.Cbrt(vol / 3000000.0));
            var votes = new Dictionary<int, int>[n];
            int pts = 0, oracle = 0;
            for (double x = x0 + step / 2; x < x1; x += step)
                for (double y = y0 + step / 2; y < y1; y += step)
                    for (double z = z0 + step / 2; z < z1; z += step)
                    {
                        int lf = Leaf(x, y, z); if (lf < 0 || lf >= n) continue;
                        int c = OrigCluster(x, y, z); if (c >= 0) { oracle++; checks.Add((lf, (byte)c)); } else if (!rebuild) continue; else { c = BoxCluster(x, y, z); if (c < 0) c = Nearest(x, y, z); }
                        pts++; if (!rebuild) continue;
                        var v = votes[lf] ??= new Dictionary<int, int>(); v[c] = v.TryGetValue(c, out var q) ? q + 1 : 1;
                    }
            // points just in front of and behind every collision surface (each triangle of its fan, several offsets): every
            // leaf borders surfaces, so this reaches leaves a uniform grid misses on large maps (Breakneck: grid at 18 units)
            int surfPts = 0;
            if (col.Surfaces != null && col.Edges != null)
                for (int s = 0; s < col.Surfaces.Count; s++)
                {
                    var loop = new List<RealPointLike>(); int e = col.Surfaces[s].FirstEdge, guard = 0;
                    do
                    {
                        if (e < 0 || e >= col.Edges.Count || guard++ > 64) { loop.Clear(); break; }
                        var ed = col.Edges[e];
                        if (ed.RightSurface == s) { var p = col.Vertices[ed.EndVertex].Point; loop.Add(new RealPointLike(p.X, p.Y, p.Z)); e = ed.ReverseEdge; }
                        else { var p = col.Vertices[ed.StartVertex].Point; loop.Add(new RealPointLike(p.X, p.Y, p.Z)); e = ed.ForwardEdge; }
                    } while (e != col.Surfaces[s].FirstEdge);
                    if (loop.Count < 3) continue;
                    int pi = col.Surfaces[s].Plane & 0x7FFF; if (pi >= col.Planes.Count) continue;
                    var pl = col.Planes[pi].Value;
                    for (int t = 1; t + 1 < loop.Count; t++)
                    {
                        double cx0 = (loop[0].X + loop[t].X + loop[t + 1].X) / 3, cy0 = (loop[0].Y + loop[t].Y + loop[t + 1].Y) / 3, cz0 = (loop[0].Z + loop[t].Z + loop[t + 1].Z) / 3;
                        foreach (var off in new[] { 0.03, -0.03, 0.3, -0.3, 1.0, -1.0 })
                        {
                            double x = cx0 + pl.I * off, y = cy0 + pl.J * off, z = cz0 + pl.K * off;
                            int lf = Leaf(x, y, z); if (lf < 0 || lf >= n) continue;
                            int c = OrigCluster(x, y, z); if (c >= 0) { oracle++; checks.Add((lf, (byte)c)); } else if (!rebuild) continue; else { c = BoxCluster(x, y, z); if (c < 0) c = Nearest(x, y, z); }
                            surfPts++; if (!rebuild) continue;
                            var v = votes[lf] ??= new Dictionary<int, int>(); v[c] = v.TryGetValue(c, out var q) ? q + 1 : 1;
                        }
                    }
                }
            pts += surfPts;
            // whole-map check: every point the source's own tree places must land in the same cluster through this tree and table
            int Verify(List<ScenarioStructureBsp.Leaf> table) { int bad = 0; foreach (var (lf, c) in checks) if (lf >= table.Count || table[lf].ClusterNew != c) bad++; return bad; }
            if (!rebuild)
            {
                int bad0 = Verify(bsp.Leaves);
                log.Add($"leaf clusters: {where}: collision tree and leaf table kept as shipped ({n} leaves); check: {checks.Count} points placed by the source's own tree, {bad0} in a different cluster here" + (OrigTree == null ? " (no source tree to check against)" : ""));
                return;
            }
            // leaves without votes: nearest cluster to the centre of their surfaces
            var leafPoint = new double[n][];
            if (col.Bsp2dReferences != null && col.Surfaces != null)
                for (int l = 0; l < n; l++)
                {
                    if (votes[l] != null) continue;
                    var lf = col.Leaves[l]; double sx = 0, sy = 0, sz = 0; int cnt = 0;
                    for (int r = 0; r < lf.Bsp2dReferenceCount; r++)
                    {
                        int ri = (int)lf.FirstBsp2dReference + r; if (ri < 0 || ri >= col.Bsp2dReferences.Count) break;
                        int pl = col.Bsp2dReferences[ri].PlaneIndex & 0x7FFF; if (pl >= col.Planes.Count) continue;
                        // a point on the reference plane near the leaf: averaged surface vertices of surfaces on that plane
                        for (int s = 0; s < col.Surfaces.Count && cnt < 64; s++)
                        {
                            if ((col.Surfaces[s].Plane & 0x7FFF) != pl) continue;
                            int e = col.Surfaces[s].FirstEdge; if (e >= col.Edges.Count) continue;
                            var vp = col.Vertices[col.Edges[e].StartVertex].Point; sx += vp.X; sy += vp.Y; sz += vp.Z; cnt++;
                        }
                    }
                    if (cnt > 0) leafPoint[l] = new[] { sx / cnt, sy / cnt, sz / cnt };
                }
            int voted = 0, near = 0;
            if (bsp.Leaves == null) bsp.Leaves = new List<ScenarioStructureBsp.Leaf>();
            var leaves = new List<ScenarioStructureBsp.Leaf>(n);
            var cx = cl.Select(c => new[] { (c.BoundsX.Lower + c.BoundsX.Upper) / 2.0, (c.BoundsY.Lower + c.BoundsY.Upper) / 2.0, (c.BoundsZ.Lower + c.BoundsZ.Upper) / 2.0 }).ToList();
            for (int l = 0; l < n; l++)
            {
                int c;
                if (votes[l] != null) { c = votes[l].OrderByDescending(kv => kv.Value).First().Key; voted++; }
                else { var p = leafPoint[l] ?? new[] { (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2 }; c = BoxCluster(p[0], p[1], p[2]); if (c < 0) c = Nearest(p[0], p[1], p[2]); near++; }
                leaves.Add(new ScenarioStructureBsp.Leaf { ClusterNew = (byte)c });
            }
            int before = bsp.Leaves.Count;
            bsp.Leaves = leaves;
            int bad = Verify(leaves);
            log.Add($"leaf clusters: {where}: CHECK: {bad} of {checks.Count} points placed by the source's own tree land in a different cluster through the rebuilt tree ({100.0 * bad / Math.Max(1, checks.Count):0.00}%)");
            log.Add($"leaf clusters: {where}: leaf table rebuilt for the shipped collision BSP ({before} entries -> {n}; {voted} leaves by {pts} sample points at {step:0.00} spacing ({oracle} placed by the source's own tree and leaf table), {near} by nearest cluster)");
        }
    }
}
namespace Ho2H3
{
    readonly struct RealPointLike { public readonly double X, Y, Z; public RealPointLike(double x, double y, double z) { X = x; Y = y; Z = z; } }
}
