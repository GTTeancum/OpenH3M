// surftest <360 map> [sbsp filter]: can each structure collision surface be found the way the engine looks surfaces up?
// For a point just in front of the surface (centroid + 0.02 along its signed normal): 3D BSP -> leaf -> the leaf's 2D
// references on the surface's plane -> 2D BSP with the point projected (TagTool CollisionBSPGen3Builder's projection)
// -> surface. Counted for both 2D child conventions; stock Halo 3 maps are the control.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using TagTool.Cache;
using TagTool.Geometry.BspCollisionGeometry;
using TagTool.Tags.Definitions;

namespace Ho2H3
{
    static class SurfTest
    {
        static readonly int[] Coords = { 2, 1, 1, 2, 0, 2, 2, 0, 1, 0, 0, 1 };
        public static int Run(string[] a)
        {
            var cache = GameCache.Open(new FileInfo(a[1]));
            using (var s = cache.OpenCacheRead())
                foreach (var t in cache.TagCache.NonNull().Where(t => t.IsInGroup("sbsp") && (a.Length < 3 || t.Name.Contains(a[2]))))
                {
                    var bsp = cache.Deserialize<ScenarioStructureBsp>(s, t);
                    var r = cache.ResourceCache.GetStructureBspTagResources(bsp.CollisionBspResource);
                    if (r?.CollisionBsps == null || r.CollisionBsps.Count == 0) continue;
                    var c = r.CollisionBsps[0];
                    int[] found = new int[2], tested = new int[2]; int solid = 0, noRef = 0, sloped = 0; int[] slopedFound = new int[2];
                    for (int si = 0; si < c.Surfaces.Count; si++)
                    {
                        var sf = c.Surfaces[si]; if (((int)sf.Flags & 0x10) != 0) continue;
                        var loop = new List<int>(); int e = sf.FirstEdge, guard = 0;
                        do { if (e < 0 || e >= c.Edges.Count || guard++ > 4096) { loop.Clear(); break; } var ed = c.Edges[e]; if (ed.RightSurface == si) { loop.Add(ed.EndVertex); e = ed.ReverseEdge; } else { loop.Add(ed.StartVertex); e = ed.ForwardEdge; } } while (e != sf.FirstEdge);
                        if (loop.Count < 3) continue;
                        double cx = 0, cy = 0, cz = 0; foreach (var vi in loop) { var p = c.Vertices[vi].Point; cx += p.X; cy += p.Y; cz += p.Z; } cx /= loop.Count; cy /= loop.Count; cz /= loop.Count;
                        int pi = sf.Plane & 0x7FFF; double sg = (sf.Plane & 0x8000) != 0 ? -1 : 1; var pl = c.Planes[pi].Value;
                        double nx = sg * pl.Normal.I, ny = sg * pl.Normal.J, nz = sg * pl.Normal.K;
                        bool isSloped = Math.Abs(nz) > 0.7 && Math.Abs(nz) < 0.99; if (isSloped) sloped++;
                        double px = cx + nx * 0.02, py = cy + ny * 0.02, pz = cz + nz * 0.02;
                        // 3D BSP
                        int node = 0, leaf = -1, depth = 0;
                        while (depth++ < 10000 && node >= 0 && node < c.Bsp3dNodes.Count)
                        {
                            var n = c.Bsp3dNodes[node]; var np = c.Planes[n.Plane].Value;
                            double d = np.Normal.I * px + np.Normal.J * py + np.Normal.K * pz - np.Distance;
                            int child = d >= 0 ? n.FrontChild : n.BackChild;
                            if ((child & 0x800000) != 0) { leaf = Bsp3dNode.GetChildIndex(child); break; }
                            node = child;
                        }
                        if (leaf < 0) { solid++; continue; }
                        var lf = c.Leaves[leaf]; var refs = new List<TagTool.Geometry.BspCollisionGeometry.Bsp2dReference>();
                        for (int k = 0; k < lf.Bsp2dReferenceCount; k++) refs.Add(c.Bsp2dReferences[(int)lf.FirstBsp2dReference + k]);
                        var onPlane = refs.Where(x => (x.PlaneIndex & 0x7FFF) == pi).ToList();
                        if (onPlane.Count == 0) { noRef++; continue; }
                        for (int conv = 0; conv < 2; conv++)
                        {
                            tested[conv]++; bool ok = false;
                            foreach (var rf in onPlane)
                            {
                                var rp = c.Planes[rf.PlaneIndex & 0x7FFF].Value; double rs = (rf.PlaneIndex & 0x8000) != 0 ? -1 : 1;
                                double ri = rs * rp.Normal.I, rj = rs * rp.Normal.J, rk = rs * rp.Normal.K;
                                double ai = Math.Abs(ri), aj = Math.Abs(rj), ak = Math.Abs(rk);
                                int axis = (ak < aj || ak < ai) ? (aj >= ai ? 1 : 0) : 2; bool sign = axis == 0 ? ri > 0 : axis == 1 ? rj > 0 : rk > 0;
                                int v4 = 2 * ((sign ? 1 : 0) + 2 * axis); double[] q = { cx, cy, cz }; double x2 = q[Coords[v4]], y2 = q[Coords[v4 + 1]];
                                int ch = rf.Bsp2dNodeIndex, g2 = 0;
                                while ((ch & 0x8000) == 0 && ch >= 0 && ch < c.Bsp2dNodes.Count && g2++ < 10000)
                                {
                                    var bn = c.Bsp2dNodes[ch]; double dd = bn.Plane.I * x2 + bn.Plane.J * y2 - bn.Plane.Distance;
                                    bool right = conv == 0 ? dd >= 0 : dd < 0;
                                    ch = right ? bn.RightChild : bn.LeftChild;
                                }
                                if ((ch & 0x8000) != 0 && (ch & 0x7FFF) == si) { ok = true; break; }
                                if ((ch & 0x8000) != 0) { var s2 = c.Surfaces[ch & 0x7FFF]; if ((s2.Plane & 0x7FFF) == pi) { ok = true; break; } }   // a coplanar neighbour also covers the point
                            }
                            if (ok) { found[conv]++; if (isSloped) slopedFound[conv]++; }
                        }
                    }
                    Console.WriteLine($"{t.Name}: surfaces {c.Surfaces.Count}: point in solid {solid}, no 2D ref on plane {noRef}, found (convention A) {found[0]}/{tested[0]}, (B) {found[1]}/{tested[1]}; sloped {sloped}: found A {slopedFound[0]} B {slopedFound[1]}");
                }
            return 0;
        }
    }
}
