// Whole-map collision check: does the converted map still stop a player on every walkable surface of the source?
// collcheck <source pak/map> <source sbsp> <converted .map> <converted sbsp> [list]
// For every upward-facing collision surface of the source (structure and every placed instance, in world space) a short
// vertical segment through its centre is tested against the converted map's collision the way Halo's collision BSP is
// walked: down the 3D BSP, and where the segment crosses a node plane, through the 2D BSP of that plane in the leaves on
// either side to a surface, which stops the segment if it is two-sided or faces the segment. The same test is run on the
// source itself first (a control: it must stop on its own surfaces). Prints misses grouped by source piece.
// Map-agnostic; reads only.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using TagTool.Cache;
using TagTool.Common;
using TagTool.Geometry.BspCollisionGeometry;
using TagTool.Geometry.BspCollisionGeometry.Utils;
using TagTool.Tags.Definitions;

namespace Ho2H3
{
    public static class CollCheck
    {
        // one collision geometry in Halo 3's small layout, with an instance transform (world = s * p * R + T)
        sealed class Piece
        {
            public string Name; public int Index = -1; public ushort Flags; public CollisionGeometry G; public float S = 1; public float[][] R; public float[] T;
            public float[] Lo, Hi;   // world box
            public double[] ToLocal(double[] w) { var p = new double[3]; for (int k = 0; k < 3; k++) p[k] = ((w[0] - T[0]) * R[k][0] + (w[1] - T[1]) * R[k][1] + (w[2] - T[2]) * R[k][2]) / S; return p; }
            public double[] ToWorld(double x, double y, double z) { var w = new double[3]; for (int a = 0; a < 3; a++) w[a] = S * (x * R[0][a] + y * R[1][a] + z * R[2][a]) + T[a]; return w; }
        }

        static float[][] Identity => new[] { new float[] { 1, 0, 0 }, new float[] { 0, 1, 0 }, new float[] { 0, 0, 1 } };

        static List<Piece> Pieces(GameCache c, Stream s, string sbspName, bool shrinkLarge)
        {
            var sb = c.Deserialize<ScenarioStructureBsp>(s, c.TagCache.GetTag(sbspName, "sbsp"));
            var r = c.ResourceCache.GetStructureBspTagResources(sb.CollisionBspResource);
            var list = new List<Piece>();
            var rz = new ResizeCollisionBSP();
            if (r.CollisionBsps != null) foreach (var g in r.CollisionBsps) list.Add(new Piece { Name = "(structure)", G = g, R = Identity, T = new float[3] });
            if (shrinkLarge && r.LargeCollisionBsps != null) foreach (var lb in r.LargeCollisionBsps) list.Add(new Piece { Name = "(structure)", G = Halo3Limits.Shrink(rz, lb), R = Identity, T = new float[3] });
            for (int i = 0; i < sb.InstancedGeometryInstances.Count; i++)
            {
                var x = sb.InstancedGeometryInstances[i]; int d = x.DefinitionIndex;
                if (d < 0 || d >= r.InstancedGeometry.Count || r.InstancedGeometry[d].CollisionInfo?.Surfaces == null || r.InstancedGeometry[d].CollisionInfo.Surfaces.Count == 0) continue;
                var m = x.Matrix;
                list.Add(new Piece { Index = i, Name = c.StringTable.GetString(x.Name) ?? ("instance " + i), Flags = (ushort)x.Flags, G = r.InstancedGeometry[d].CollisionInfo, S = x.Scale == 0 ? 1 : x.Scale,
                    R = new[] { new[] { m.m11, m.m12, m.m13 }, new[] { m.m21, m.m22, m.m23 }, new[] { m.m31, m.m32, m.m33 } }, T = new[] { m.m41, m.m42, m.m43 } });
            }
            foreach (var p in list)
            {
                p.Lo = new[] { float.MaxValue, float.MaxValue, float.MaxValue }; p.Hi = new[] { float.MinValue, float.MinValue, float.MinValue };
                foreach (var v in p.G.Vertices) { var w = p.ToWorld(v.Point.X, v.Point.Y, v.Point.Z); for (int a = 0; a < 3; a++) { p.Lo[a] = Math.Min(p.Lo[a], (float)w[a]); p.Hi[a] = Math.Max(p.Hi[a], (float)w[a]); } }
            }
            return list;
        }

        // refcheck <map> <sbsp> [instance name regex]: walks every collision BSP the way Halo 3 360 does (0x822C7EB8): going
        // down a 3D node it remembers the node plane, as p for the front child and p|0x8000 for the back child; in a leaf it
        // only uses a 2D reference whose plane field equals one of the remembered values. Counts references the game can
        // never use (their surfaces are invisible to every collision query) per collision geometry.
        public static int RefCheck(string[] a)
        {
            var c = Program.OpenPak(a[1]); List<Piece> ps;
            using (var s = Program.OpenStream(c)) ps = Pieces(c, s, a[2], true);
            var rx = a.Length > 3 ? new System.Text.RegularExpressions.Regex(a[3]) : null;
            int geoms = 0, badGeoms = 0; long refs = 0, bad = 0; var seen = new HashSet<CollisionGeometry>();
            foreach (var p in ps)
            {
                if (rx != null && !rx.IsMatch(p.Name)) continue;
                if (!seen.Add(p.G)) continue;
                var g = p.G; var used = new bool[g.Bsp2dReferences.Count]; var reach = new bool[g.Bsp2dReferences.Count]; var stack = new List<int>();
                long gr = 0, gb = 0;
                void Walk(int child, int depth)
                {
                    if (child == 0xFFFFFF || depth > 2000) return;
                    if ((child & 0x800000) != 0)
                    {
                        var lf = g.Leaves[child & 0x7FFFFF];
                        for (int k = 0; k < lf.Bsp2dReferenceCount; k++)
                        {
                            int ri = (int)lf.FirstBsp2dReference + k; reach[ri] = true;
                            if (stack.Contains(g.Bsp2dReferences[ri].PlaneIndex)) used[ri] = true;
                        }
                        return;
                    }
                    var n = g.Bsp3dNodes[child]; int pl = n.Plane & 0x7FFF;
                    stack.Add(pl); Walk(n.FrontChild, depth + 1); stack.RemoveAt(stack.Count - 1);
                    stack.Add((short)(pl | 0x8000)); Walk(n.BackChild, depth + 1); stack.RemoveAt(stack.Count - 1);
                }
                if (g.Bsp3dNodes.Count > 0) Walk(0, 0); else if (g.Leaves.Count > 0) Walk(0x800000, 0);
                for (int i = 0; i < used.Length; i++) { if (!reach[i]) continue; gr++; if (!used[i]) gb++; }
                geoms++; refs += gr; bad += gb; if (gb > 0) badGeoms++;
                if (gb > 0 && (rx != null || badGeoms <= 25)) Console.WriteLine($"  {p.Name}: {gb} of {gr} 2D references unusable (nodes {g.Bsp3dNodes.Count}, leaves {g.Leaves.Count}, surfaces {g.Surfaces.Count})");
            }
            Console.WriteLine($"{geoms} collision geometries, {badGeoms} with unusable 2D references; {bad} of {refs} references unusable");
            return 0;
        }

        // sphere360 <map> <sbsp> x y z radius [instance index]: Halo 3 360's collision BSP sphere test (0x822C7E08 and the
        // functions it calls, read from the Mythic default.xex) reproduced step for step on each placed piece whose box
        // holds the point: 3D BSP with the plane stack, 2D references matched against the stack, the 2D BSP, then per surface
        // vertex / edge distance and the inside test with the game's projection table. Prints what the game would find.
        static readonly short[] Proj360 = { 2, 1, 0, 1, 2, 0, 0, 2, 1, 2, 0, 1, 1, 0, 2, 0, 1, 2 };
        public static int Sphere360(string[] a)
        {
            var c = Program.OpenPak(a[1]); List<Piece> ps;
            using (var s = Program.OpenStream(c)) ps = Pieces(c, s, a[2], true);
            var w = new[] { double.Parse(a[3]), double.Parse(a[4]), double.Parse(a[5]) }; double R = double.Parse(a[6]);
            int only = a.Length > 7 ? int.Parse(a[7]) : int.MinValue;
            foreach (var p in ps)
            {
                if (only != int.MinValue && p.Index != only) continue;
                bool inBox = true; for (int k = 0; k < 3; k++) if (w[k] < p.Lo[k] - R || w[k] > p.Hi[k] + R) inBox = false;
                if (!inBox) continue;
                var g = p.G; var P = p.ToLocal(w); double r = R / p.S;
                var stack = new List<int>(); var found = new List<string>(); var refused = new List<string>();
                RealPlane3d PlaneOf(int idx) { var q = g.Planes[idx & 0x7FFF].Value; return q; }
                void Surf(int si, int refPlane, int axis, int flag, double pu, double pv)
                {
                    var sf = g.Surfaces[si]; bool hit = false;
                    int e = sf.FirstEdge; int guard = 0;
                    do { var ed = g.Edges[e]; int side = ed.RightSurface == si ? 1 : 0; int vi = side == 1 ? ed.EndVertex : ed.StartVertex;
                         var v = g.Vertices[vi].Point; double dx = P[0] - v.X, dy = P[1] - v.Y, dz = P[2] - v.Z; if (dx * dx + dy * dy + dz * dz <= r * r) hit = true;
                         e = side == 1 ? ed.ReverseEdge : ed.ForwardEdge; } while (e != sf.FirstEdge && ++guard < 10000);
                    bool inside = true; int neg = 0, posc = 0; e = sf.FirstEdge; guard = 0; int t0 = Proj360[(axis * 2 + flag) * 3], t1 = Proj360[(axis * 2 + flag) * 3 + 1];
                    double[] pp = { 0, 0, 0 }; pp[t0] = pu; pp[t1] = pv;
                    do { var ed = g.Edges[e]; int side = ed.RightSurface == si ? 1 : 0;
                         var v1 = g.Vertices[side == 1 ? ed.EndVertex : ed.StartVertex].Point; var v2 = g.Vertices[side == 1 ? ed.StartVertex : ed.EndVertex].Point;
                         double[] A = { v1.X, v1.Y, v1.Z }, B = { v2.X, v2.Y, v2.Z };
                         double cr = (B[t1] - pv) * (A[t0] - pu) - (A[t1] - pv) * (B[t0] - pu); if (cr < 0) { inside = false; neg++; } else if (cr > 0) posc++;
                         e = side == 1 ? ed.ReverseEdge : ed.ForwardEdge; } while (e != sf.FirstEdge && ++guard < 10000);
                    string tag = $"surface {si} plane {sf.Plane & 0x7FFF}{((sf.Plane & 0x8000) != 0 ? "-" : "+")} flags {sf.Flags} via ref plane {refPlane & 0x7FFF}{((refPlane & 0x8000) != 0 ? "-" : "+")} axis {axis} flag {flag}";
                    if (hit || inside) found.Add(tag + (inside ? " INSIDE" : " vertex/edge")); else refused.Add(tag + (posc == 0 && neg > 0 ? " (point IS inside, ring wound the other way)" : $" (outside: {neg} edges against, {posc} for)"));
                }
                void TwoD(int node, int refPlane, int axis, int flag, double pu, double pv)
                {
                    while (true)
                    {
                        if ((node & 0x8000) != 0) { Surf(node & 0x7FFF, refPlane, axis, flag, pu, pv); return; }
                        var n = g.Bsp2dNodes[node]; double d = n.Plane.I * pu + n.Plane.J * pv - n.Plane.D;
                        bool left = d <= r, right = d >= -r;
                        if (left) TwoD(n.LeftChild, refPlane, axis, flag, pu, pv);
                        if (!right) return; node = n.RightChild;
                    }
                }
                void Walk(int child)
                {
                    if ((child & 0x800000) != 0)
                    {
                        if (child == 0xFFFFFF) return;
                        var lf = g.Leaves[child & 0x7FFFFF];
                        for (int k = 0; k < lf.Bsp2dReferenceCount; k++)
                        {
                            var rf = g.Bsp2dReferences[(int)lf.FirstBsp2dReference + k];
                            if (!stack.Contains(rf.PlaneIndex)) continue;
                            var pl = PlaneOf(rf.PlaneIndex); double dd = pl.I * P[0] + pl.J * P[1] + pl.K * P[2] - pl.D;
                            double[] q = { P[0] - pl.I * dd, P[1] - pl.J * dd, P[2] - pl.K * dd }; double[] nn = { pl.I, pl.J, pl.K };
                            double ax = Math.Abs(nn[0]), ay = Math.Abs(nn[1]), az = Math.Abs(nn[2]);
                            int axis = (az >= ay && az >= ax) ? 2 : (ay >= ax ? 1 : 0);
                            int pos = nn[axis] > 0 ? 1 : 0, neg = ((ushort)rf.PlaneIndex) >> 15; int flag = neg == pos ? 0 : 1;
                            int t0 = Proj360[(axis * 2 + flag) * 3], t1 = Proj360[(axis * 2 + flag) * 3 + 1];
                            TwoD((ushort)rf.Bsp2dNodeIndex, rf.PlaneIndex, axis, flag, q[t0], q[t1]);
                        }
                        return;
                    }
                    var n = g.Bsp3dNodes[child]; int pi = n.Plane & 0x7FFF; var np = PlaneOf(pi);
                    double d = np.I * P[0] + np.J * P[1] + np.K * P[2] - np.D;
                    bool back = d < r, front = d > -r;
                    if (front && back) { stack.Add((short)(pi | 0x8000)); Walk(n.BackChild); stack.RemoveAt(stack.Count - 1); stack.Add(pi); Walk(n.FrontChild); stack.RemoveAt(stack.Count - 1); }
                    else Walk(back ? n.BackChild : n.FrontChild);
                }
                if (g.Bsp3dNodes.Count > 0) Walk(0);
                Console.WriteLine($"{p.Name} (instance {p.Index}) local point {P[0]:F3},{P[1]:F3},{P[2]:F3} radius {r:F3}: game finds {found.Count} surfaces, refuses {refused.Count} it reached");
                foreach (var f in found) Console.WriteLine("   found   " + f);
                foreach (var f in refused.Take(12)) Console.WriteLine("   refused " + f);
            }
            return 0;
        }

        // vector360 <map> <sbsp> x y z0 z1 [query flags, default 1] [instance index]: Halo 3 360's collision BSP vector test
        // (0x822C8890 with 0x822C8C80 / 0x820CA728, Mythic default.xex) reproduced on each placed piece the vertical segment
        // passes through. Leaf types as the game sets them: 3 = solid (child -1), 2 = leaf flagged double-sided, 1 = open.
        // A surface is only tested on open->solid (flag 1), solid->open (flag 2) or double-sided->double-sided (unless flag 4).
        public static int Vector360(string[] a)
        {
            var c = Program.OpenPak(a[1]); List<Piece> ps;
            using (var s = Program.OpenStream(c)) ps = Pieces(c, s, a[2], true);
            double x = double.Parse(a[3]), y = double.Parse(a[4]), z0 = double.Parse(a[5]), z1 = double.Parse(a[6]);
            int qf = a.Length > 7 ? int.Parse(a[7]) : 1; int only = a.Length > 8 ? int.Parse(a[8]) : int.MinValue;
            foreach (var p in ps)
            {
                if (only != int.MinValue && p.Index != only) continue;
                if (x < p.Lo[0] || x > p.Hi[0] || y < p.Lo[1] || y > p.Hi[1] || Math.Min(z0, z1) > p.Hi[2] || Math.Max(z0, z1) < p.Lo[2]) continue;
                var g = p.G; var O = p.ToLocal(new[] { x, y, z0 }); var E = p.ToLocal(new[] { x, y, z1 }); var D = new[] { E[0] - O[0], E[1] - O[1], E[2] - O[2] };
                int negNodes = g.Bsp3dNodes.Count(n => (n.Plane & 0x8000) != 0);
                int prevLeaf = -1, prevType = 0, crossPlane = -1; double bestT = 1; string hit = null; var seq = new List<string>();
                int LeafSurface(int leaf, double t, bool twoSidedCase)
                {
                    var lf = g.Leaves[leaf];
                    for (int k = 0; k < lf.Bsp2dReferenceCount; k++)
                    {
                        var rf = g.Bsp2dReferences[(int)lf.FirstBsp2dReference + k];
                        if ((rf.PlaneIndex & 0x7FFF) != crossPlane) continue;
                        var pl = g.Planes[crossPlane].Value; double[] nn = { pl.I, pl.J, pl.K };
                        double ax = Math.Abs(nn[0]), ay = Math.Abs(nn[1]), az = Math.Abs(nn[2]);
                        int axis = (az >= ay && az >= ax) ? 2 : (ay >= ax ? 1 : 0);
                        int pos = nn[axis] > 0 ? 1 : 0, neg = ((ushort)rf.PlaneIndex) >> 15; int flag = neg == pos ? 0 : 1;
                        double[] hp = { O[0] + D[0] * t, O[1] + D[1] * t, O[2] + D[2] * t };
                        double u = hp[Proj360[(axis * 2 + flag) * 3]], v = hp[Proj360[(axis * 2 + flag) * 3 + 1]];
                        int node = (ushort)rf.Bsp2dNodeIndex;
                        while ((node & 0x8000) == 0) { var n2 = g.Bsp2dNodes[node]; double d = n2.Plane.I * u + n2.Plane.J * v - n2.Plane.D; node = d >= 0 ? (ushort)n2.RightChild : (ushort)n2.LeftChild; }
                        if (node == 0xFFFF) continue;
                        return node & 0x7FFF;
                    }
                    return -1;
                }
                bool Walk(int node, double t0, double t1)
                {
                    while ((node & 0x800000) == 0)
                    {
                        var n = g.Bsp3dNodes[node]; var pl = g.Planes[n.Plane & 0x7FFF].Value;
                        double d0 = pl.I * O[0] + pl.J * O[1] + pl.K * O[2] - pl.D, f = pl.I * D[0] + pl.J * D[1] + pl.K * D[2];
                        double a0 = f * t0 + d0, a1 = f * t1 + d0; bool sa = a0 >= 0, sb = a1 >= 0;
                        if (sa == sb) { node = sa ? n.FrontChild : n.BackChild; continue; }
                        double tc = -d0 / f; bool towardFront = f > 0;
                        if (Walk(towardFront ? n.BackChild : n.FrontChild, t0, tc)) return true;
                        if (bestT <= tc) return false;
                        crossPlane = n.Plane & 0x7FFF; node = towardFront ? n.FrontChild : n.BackChild; t0 = tc;
                    }
                    int leaf = node == 0xFFFFFF ? -1 : node & 0x7FFFFF;
                    int type = leaf < 0 ? 3 : ((g.Leaves[leaf].Flags & (LeafFlags)1) != 0 ? 2 : 1);
                    seq.Add($"{type}@{t0:F3}");
                    int test = -1; bool two = false;
                    if ((qf & 1) != 0 && (prevType == 1 || prevType == 2) && type == 3) test = prevLeaf;
                    else if ((qf & 2) != 0 && prevType == 3 && (type == 1 || type == 2)) test = leaf;
                    else if ((qf & 4) == 0 && prevType == 2 && type == 2) { test = (qf & 1) != 0 ? prevLeaf : leaf; two = true; }
                    if (test >= 0)
                    {
                        int sfi = LeafSurface(test, t0, two);
                        if (sfi >= 0) { var sf = g.Surfaces[sfi]; bestT = t0; var w = p.ToWorld(O[0] + D[0] * t0, O[1] + D[1] * t0, O[2] + D[2] * t0);
                            hit = $"HIT surface {sfi} flags {sf.Flags} at z {w[2]:F3} (leaf type {prevType}->{type})"; return true; }
                    }
                    prevLeaf = leaf; prevType = type; return false;
                }
                if (g.Bsp3dNodes.Count > 0) Walk(0, 0, 1);
                Console.WriteLine($"{p.Name} (instance {p.Index}): {hit ?? "no hit"}; leaves crossed {string.Join(" ", seq)}; nodes with flipped plane bit {negNodes} of {g.Bsp3dNodes.Count}; leaves flagged double-sided {g.Leaves.Count(l => (l.Flags & (LeafFlags)1) != 0)} of {g.Leaves.Count}");
            }
            return 0;
        }

        // solidstats <map> <sbsp>: per collision geometry, 3D BSP children that are solid (-1) and leaves flagged
        // double-sided. Halo 3's vector test only finds a surface at open->solid or double-sided->double-sided transitions.
        public static int SolidStats(string[] a)
        {
            var c = Program.OpenPak(a[1]); List<Piece> ps;
            using (var s = Program.OpenStream(c)) ps = Pieces(c, s, a[2], true);
            var seen = new HashSet<CollisionGeometry>(); int n = 0, noSolid = 0, noSolidNoDs = 0, oneSidedSurfNoSolid = 0;
            foreach (var p in ps)
            {
                if (p.Index < 0 || !seen.Add(p.G)) continue; var g = p.G; n++;
                int solid = g.Bsp3dNodes.Sum(q => (q.FrontChild == 0xFFFFFF ? 1 : 0) + (q.BackChild == 0xFFFFFF ? 1 : 0));
                int ds = g.Leaves.Count(l => (l.Flags & (LeafFlags)1) != 0);
                int one = g.Surfaces.Count(sf => (sf.Flags & SurfaceFlags.TwoSided) == 0);
                if (solid == 0) { noSolid++; if (ds == 0) noSolidNoDs++; if (one > 0) oneSidedSurfNoSolid++; }
                if (a.Length > 3 && p.Name.Contains(a[3])) Console.WriteLine($"  {p.Name}: solid children {solid}, nodes {g.Bsp3dNodes.Count}, double-sided leaves {ds}/{g.Leaves.Count}, one-sided surfaces {one}/{g.Surfaces.Count}");
            }
            Console.WriteLine($"{n} piece geometries: {noSolid} with no solid space ({noSolidNoDs} of them with no double-sided leaf either; {oneSidedSurfNoSolid} have one-sided surfaces)");
            return 0;
        }

        // Halo 3 360's collision BSP vector test (0x822C8890 / 0x822C8C80 / 0x820CA728) on one collision geometry, local
        // space, segment O + t*D for t in [0,1]. Returns the surface hit or -1.
        public static int VectorHit360(CollisionGeometry g, double[] O, double[] D, int qf, out double hitT)
        {
            int prevLeaf = -1, prevType = 0, crossPlane = -1; double bestT = 1; int hit = -1;
            int LeafSurface(int leaf, double t)
            {
                var lf = g.Leaves[leaf];
                for (int k = 0; k < lf.Bsp2dReferenceCount; k++)
                {
                    var rf = g.Bsp2dReferences[(int)lf.FirstBsp2dReference + k];
                    if ((rf.PlaneIndex & 0x7FFF) != crossPlane) continue;
                    var pl = g.Planes[crossPlane].Value; double[] nn = { pl.I, pl.J, pl.K };
                    double ax = Math.Abs(nn[0]), ay = Math.Abs(nn[1]), az = Math.Abs(nn[2]);
                    int axis = (az >= ay && az >= ax) ? 2 : (ay >= ax ? 1 : 0);
                    int pos = nn[axis] > 0 ? 1 : 0, neg = ((ushort)rf.PlaneIndex) >> 15; int flag = neg == pos ? 0 : 1;
                    double[] hp = { O[0] + D[0] * t, O[1] + D[1] * t, O[2] + D[2] * t };
                    double u = hp[Proj360[(axis * 2 + flag) * 3]], v = hp[Proj360[(axis * 2 + flag) * 3 + 1]];
                    int node = (ushort)rf.Bsp2dNodeIndex; int guard = 0;
                    while ((node & 0x8000) == 0 && ++guard < 100000) { var n2 = g.Bsp2dNodes[node]; double d = n2.Plane.I * u + n2.Plane.J * v - n2.Plane.D; node = d >= 0 ? (ushort)n2.RightChild : (ushort)n2.LeftChild; }
                    if (node == 0xFFFF) continue;
                    return node & 0x7FFF;
                }
                return -1;
            }
            bool Walk(int node, double t0, double t1)
            {
                while ((node & 0x800000) == 0)
                {
                    var n = g.Bsp3dNodes[node]; var pl = g.Planes[n.Plane & 0x7FFF].Value;
                    double d0 = pl.I * O[0] + pl.J * O[1] + pl.K * O[2] - pl.D, f = pl.I * D[0] + pl.J * D[1] + pl.K * D[2];
                    double a0 = f * t0 + d0, a1 = f * t1 + d0; bool sa = a0 >= 0, sb = a1 >= 0;
                    if (sa == sb) { node = sa ? n.FrontChild : n.BackChild; continue; }
                    double tc = -d0 / f; bool towardFront = f > 0;
                    if (Walk(towardFront ? n.BackChild : n.FrontChild, t0, tc)) return true;
                    if (bestT <= tc) return false;
                    crossPlane = n.Plane & 0x7FFF; node = towardFront ? n.FrontChild : n.BackChild; t0 = tc;
                }
                int leaf = node == 0xFFFFFF ? -1 : node & 0x7FFFFF;
                int type = leaf < 0 ? 3 : ((g.Leaves[leaf].Flags & (LeafFlags)1) != 0 ? 2 : 1);
                int test = -1;
                if ((qf & 1) != 0 && (prevType == 1 || prevType == 2) && type == 3) test = prevLeaf;
                else if ((qf & 2) != 0 && prevType == 3 && (type == 1 || type == 2)) test = leaf;
                else if ((qf & 4) == 0 && prevType == 2 && type == 2) test = (qf & 1) != 0 ? prevLeaf : leaf;
                if (test >= 0) { int sfi = LeafSurface(test, t0); if (sfi >= 0) { bestT = t0; hit = sfi; return true; } }
                prevLeaf = leaf; prevType = type; return false;
            }
            if (g.Bsp3dNodes.Count > 0) Walk(0, 0, 1); else if (g.Leaves.Count > 0) Walk(0x800000, 0, 1);
            hitT = bestT; return hit;
        }

        // linecheck <map> <sbsp> [list]: for every one-sided surface of every placed piece definition, the game's vector test
        // (flags 1) along the reversed surface normal through a point just inside the surface: counts surfaces it cannot hit.
        public static int LineCheck(string[] a)
        {
            var c = Program.OpenPak(a[1]); List<Piece> ps;
            using (var s = Program.OpenStream(c)) ps = Pieces(c, s, a[2], true);
            var seen = new HashSet<CollisionGeometry>(); long tested = 0, missed = 0; int geoms = 0, badGeoms = 0; bool floorsOnly = a.Contains("floors");
            foreach (var p in ps)
            {
                if (p.Index < 0 || !seen.Add(p.G)) continue; var g = p.G; geoms++;
                var (gt, gm) = LineMisses(g, floorsOnly);
                tested += gt; missed += gm; if (gm > 0) badGeoms++;
                if (a.Contains("list") && gm > 0) Console.WriteLine($"  {p.Name}: {gm} of {gt} sample points not hit");
            }
            Console.WriteLine($"{geoms} piece geometries, {badGeoms} with misses; sample points on one-sided {(floorsOnly ? "floor " : "")}surfaces the game's line test cannot hit from the front: {missed} of {tested} ({(tested == 0 ? 0 : 100.0 * missed / tested):F1}%)");
            return 0;
        }

        // renderbsp <map> <sbsp>: instance definitions with a RenderBsp collision geometry (definition +0x74), which Halo 3
        // 360's per-piece vector test (0x820C0B00) uses instead of CollisionInfo when the query has flag 0x8.
        public static int RenderBsp(string[] a)
        {
            var c = Program.OpenPak(a[1]);
            using var s = Program.OpenStream(c);
            var sb = c.Deserialize<ScenarioStructureBsp>(s, c.TagCache.GetTag(a[2], "sbsp"));
            var r = c.ResourceCache.GetStructureBspTagResources(sb.CollisionBspResource);
            int with = 0, empty = 0, surf = 0; var ex = new List<string>();
            for (int d = 0; d < r.InstancedGeometry.Count; d++)
            {
                var g = r.InstancedGeometry[d]; int n = g.RenderBsp?.Count ?? 0;
                if (n > 0) { with++; int rs = g.RenderBsp.Sum(b => b.Surfaces?.Count ?? 0); surf += rs; if (rs == 0) empty++; if (ex.Count < 6) ex.Add($"def {d}: render bsp x{n}, surfaces {rs}, nodes {g.RenderBsp[0].Bsp3dNodes?.Count}, collision surfaces {g.CollisionInfo?.Surfaces?.Count}"); }
            }
            Console.WriteLine($"{r.InstancedGeometry.Count} definitions, {with} with a render BSP ({empty} of them with no surfaces)");
            foreach (var e in ex) Console.WriteLine("  " + e);
            return 0;
        }

        // the game's vector test (flags 1) along the reversed normal through sample points of every one-sided surface of one
        // collision geometry: (sample points tested, missed). Used by linecheck and InstanceTrees.
        public static (long tested, long missed) LineMisses(CollisionGeometry g, bool floorsOnly)
        {
            long gt = 0, gm = 0;
            for (int si = 0; si < g.Surfaces.Count; si++)
            {
                var sf = g.Surfaces[si]; if ((sf.Flags & SurfaceFlags.TwoSided) != 0 || (sf.Flags & SurfaceFlags.Invalid) != 0) continue;
                var vs = new List<double[]>(); int e = sf.FirstEdge, guard = 0;
                do { var ed = g.Edges[e]; int side = ed.RightSurface == si ? 1 : 0; var v = g.Vertices[side == 1 ? ed.EndVertex : ed.StartVertex].Point; vs.Add(new double[] { v.X, v.Y, v.Z }); e = side == 1 ? ed.ReverseEdge : ed.ForwardEdge; } while (e != sf.FirstEdge && ++guard < 1000);
                if (vs.Count < 3) continue;
                var pl = g.Planes[sf.Plane & 0x7FFF].Value; double sg = (sf.Plane & 0x8000) != 0 ? -1 : 1; double[] n = { pl.I * sg, pl.J * sg, pl.K * sg };
                if (floorsOnly && n[2] < 0.7) continue;
                for (int f = 1; f + 1 < vs.Count; f++)
                {
                    var tri = new[] { vs[0], vs[f], vs[f + 1] }; var cen = new double[3]; for (int k = 0; k < 3; k++) cen[k] = (tri[0][k] + tri[1][k] + tri[2][k]) / 3;
                    var samples = new List<double[]> { cen }; foreach (var tv in tri) samples.Add(new[] { cen[0] + (tv[0] - cen[0]) * 0.8, cen[1] + (tv[1] - cen[1]) * 0.8, cen[2] + (tv[2] - cen[2]) * 0.8 });
                    foreach (var cpt in samples)
                    {
                        var O = new[] { cpt[0] + n[0] * 0.05, cpt[1] + n[1] * 0.05, cpt[2] + n[2] * 0.05 }; var D = new[] { -n[0] * 0.1, -n[1] * 0.1, -n[2] * 0.1 };
                        gt++; if (VectorHit360(g, O, D, 1, out _) < 0) gm++;
                    }
                }
            }
            return (gt, gm);
        }

        // 2D references the game can never use (see refcheck)
        public static long UnusableRefs(CollisionGeometry g)
        {
            var used = new bool[g.Bsp2dReferences.Count]; var reach = new bool[g.Bsp2dReferences.Count]; var stack = new List<int>();
            void Walk(int child, int depth)
            {
                if (child == 0xFFFFFF || depth > 2000) return;
                if ((child & 0x800000) != 0)
                {
                    var lf = g.Leaves[child & 0x7FFFFF];
                    for (int k = 0; k < lf.Bsp2dReferenceCount; k++) { int ri = (int)lf.FirstBsp2dReference + k; reach[ri] = true; if (stack.Contains(g.Bsp2dReferences[ri].PlaneIndex)) used[ri] = true; }
                    return;
                }
                var n = g.Bsp3dNodes[child]; int pl = n.Plane & 0x7FFF;
                stack.Add(pl); Walk(n.FrontChild, depth + 1); stack.RemoveAt(stack.Count - 1);
                stack.Add((short)(pl | 0x8000)); Walk(n.BackChild, depth + 1); stack.RemoveAt(stack.Count - 1);
            }
            if (g.Bsp3dNodes.Count > 0) Walk(0, 0); else if (g.Leaves.Count > 0) Walk(0x800000, 0);
            long bad = 0; for (int i = 0; i < used.Length; i++) if (reach[i] && !used[i]) bad++;
            return bad;
        }

        // moppkeys <map> <sbsp>: keys of the cluster instance MOPPs and of the instance definition MOPPs (Halo 3 360's
        // contact path 0x82270F48 only takes cluster keys whose top three bits are 0x40000000)
        public static int MoppKeys(string[] a)
        {
            var c = Program.OpenPak(a[1]);
            using var s = Program.OpenStream(c);
            var sb = c.Deserialize<ScenarioStructureBsp>(s, c.TagCache.GetTag(a[2], "sbsp"));
            var r = c.ResourceCache.GetStructureBspTagResources(sb.CollisionBspResource);
            var pm = sb.Physics?.CollisionMoppCodes;
            if (pm != null && pm.Count > 0 && pm[0].Data != null)
            {
                var sk = TagTool.Havok.HavokMoppUtil.GetAllKeys(pm[0].Data);
                Console.WriteLine($"structure physics MOPP: {pm[0].Data.Count} bytes, {sk.Count} keys; by top 16 bits: {string.Join(", ", sk.GroupBy(k => ((uint)k >> 16)).OrderBy(g => g.Key).Select(g => "0x" + g.Key.ToString("X4") + " x" + g.Count()))}; surfaces {r.CollisionBsps?.FirstOrDefault()?.Surfaces?.Count}, instances {sb.InstancedGeometryInstances?.Count}");
            }
            int shown = 0;
            for (int i = 0; i < sb.Clusters.Count && shown < 3; i++)
            {
                var m = sb.Clusters[i].InstancedGeometryPhysics?.MoppCodes; if (m == null || m.Count == 0 || m[0].Data == null) continue;
                var keys = TagTool.Havok.HavokMoppUtil.GetAllKeys(m[0].Data); shown++;
                Console.WriteLine($"cluster {i}: {m[0].Data.Count} bytes, first {string.Join(" ", m[0].Data.Take(12).Select(b => b.ToString("x2")))}, {keys.Count} keys, sample [{string.Join(",", keys.Take(6).Select(k => "0x" + k.ToString("X")))}], top bits {string.Join(",", keys.Select(k => "0x" + ((uint)k & 0xE0000000u).ToString("X")).Distinct())}");
            }
            shown = 0;
            for (int d = 0; d < r.InstancedGeometry.Count && shown < 3; d++)
            {
                var m = r.InstancedGeometry[d].CollisionMoppCodes; if (m == null || m.Count == 0 || m[0].Data == null) continue;
                var keys = TagTool.Havok.HavokMoppUtil.GetAllKeys(m[0].Data); shown++;
                Console.WriteLine($"definition {d}: {m[0].Data.Count} bytes, first {string.Join(" ", m[0].Data.Take(12).Select(b => b.ToString("x2")))}, {keys.Count} keys, sample [{string.Join(",", keys.Take(6).Select(k => "0x" + k.ToString("X")))}], surfaces {r.InstancedGeometry[d].CollisionInfo?.Surfaces?.Count}, offset {m[0].Info?.Offset}");
            }
            return 0;
        }

        static RealPlane3d Pl(CollisionGeometry g, int idx, out bool ok) { int i = idx & 0x7FFF; ok = i < g.Planes.Count; if (!ok) return new RealPlane3d(); var p = g.Planes[i].Value; return (idx & 0x8000) != 0 ? new RealPlane3d(-p.I, -p.J, -p.K, -p.D) : p; }
        static double Dist(RealPlane3d p, double[] x) => p.I * x[0] + p.J * x[1] + p.K * x[2] - p.D;

        static int LeafAt(CollisionGeometry g, double[] x)
        {
            if (g.Bsp3dNodes == null || g.Bsp3dNodes.Count == 0) return g.Leaves?.Count > 0 ? 0 : -1;
            int node = 0, guard = 0;
            while (guard++ < 100000)
            {
                var nd = g.Bsp3dNodes[node]; var p = Pl(g, nd.Plane, out bool ok); if (!ok) return -1;
                int child = Dist(p, x) >= 0 ? nd.FrontChild : nd.BackChild;
                if (child == 0xFFFFFF) return -1;
                if ((child & 0x800000) != 0) return child & 0x7FFFFF;
                node = child; if (node >= g.Bsp3dNodes.Count) return -1;
            }
            return -1;
        }

        static double[] Proj(double[] v, int axis, int mirror)
        {
            int[] cl = { 2, 1, 1, 2, 0, 2, 2, 0, 1, 0, 0, 1 }; int k = 2 * (mirror + 2 * axis);
            return new[] { v[cl[k]], v[cl[k + 1]] };
        }

        // surface of the leaf's 2D BSP on plane 'planeIdx' at point x, or -1
        static int Surface2d(CollisionGeometry g, int leaf, int planeIdx, double[] x)
        {
            if (leaf < 0 || leaf >= g.Leaves.Count) return -1;
            var lf = g.Leaves[leaf];
            for (int r = 0; r < lf.Bsp2dReferenceCount; r++)
            {
                long ri = (long)lf.FirstBsp2dReference + r; if (ri < 0 || ri >= g.Bsp2dReferences.Count) return -1;
                var rf = g.Bsp2dReferences[(int)ri];
                if ((rf.PlaneIndex & 0x7FFF) != (planeIdx & 0x7FFF)) continue;
                var bp = g.Planes[rf.PlaneIndex & 0x7FFF].Value;
                float ai = Math.Abs(bp.I), aj = Math.Abs(bp.J), ak = Math.Abs(bp.K);
                int axis = (ak < aj || ak < ai) ? (aj >= ai ? 1 : 0) : 2;
                bool pos = axis == 0 ? bp.I > 0 : axis == 1 ? bp.J > 0 : bp.K > 0;
                int mirror = pos != ((rf.PlaneIndex & 0x8000) != 0) ? 1 : 0;
                var uv = Proj(x, axis, mirror);
                int n = rf.Bsp2dNodeIndex, guard = 0;
                while ((n & 0x8000) == 0 && guard++ < 100000)
                {
                    if (n < 0 || n >= g.Bsp2dNodes.Count) return -1;
                    var nd = g.Bsp2dNodes[n];
                    n = nd.Plane.I * uv[0] + nd.Plane.J * uv[1] - nd.Plane.D >= 0 ? nd.RightChild : nd.LeftChild;
                }
                return n & 0x7FFF;
            }
            return -1;
        }

        static List<double[]> Loop(CollisionGeometry g, int s)
        {
            var l = new List<double[]>(); int e = g.Surfaces[s].FirstEdge, guard = 0;
            do
            {
                if (e >= g.Edges.Count || guard++ > 256) return null;
                var ed = g.Edges[e];
                if (ed.RightSurface == s) { var p = g.Vertices[ed.EndVertex].Point; l.Add(new double[] { p.X, p.Y, p.Z }); e = ed.ReverseEdge; }
                else { var p = g.Vertices[ed.StartVertex].Point; l.Add(new double[] { p.X, p.Y, p.Z }); e = ed.ForwardEdge; }
            } while (e != g.Surfaces[s].FirstEdge);
            return l;
        }

        // does segment a->b (local coordinates) hit a surface of g? Walks the 3D BSP; at every node-plane crossing tests the
        // leaves on both sides for a surface on that plane at the crossing point.
        static bool Hit(CollisionGeometry g, double[] a, double[] b, out bool anyCross)
        {
            anyCross = false;
            if (g.Bsp3dNodes == null || g.Bsp3dNodes.Count == 0) return false;
            var stack = new Stack<(int node, double[] p0, double[] p1)>(); stack.Push((0, a, b));
            bool cross = false; int guard = 0;
            while (stack.Count > 0 && guard++ < 200000)
            {
                var (node, p0, p1) = stack.Pop();
                if ((node & 0x800000) != 0 || node == 0xFFFFFF || node >= g.Bsp3dNodes.Count) continue;
                var nd = g.Bsp3dNodes[node]; var pl = Pl(g, nd.Plane, out bool ok); if (!ok) continue;
                double d0 = Dist(pl, p0), d1 = Dist(pl, p1);
                if (d0 >= 0 && d1 >= 0) { stack.Push((nd.FrontChild, p0, p1)); continue; }
                if (d0 < 0 && d1 < 0) { stack.Push((nd.BackChild, p0, p1)); continue; }
                double t = d0 / (d0 - d1); var x = new[] { p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t, p0[2] + (p1[2] - p0[2]) * t };
                cross = true;
                var dir = new[] { b[0] - a[0], b[1] - a[1], b[2] - a[2] }; double len = Math.Sqrt(dir[0] * dir[0] + dir[1] * dir[1] + dir[2] * dir[2]);
                foreach (var side in new[] { -1e-3, 1e-3 })
                {
                    var q = new[] { x[0] + dir[0] / len * side, x[1] + dir[1] / len * side, x[2] + dir[2] / len * side };
                    int s = Surface2d(g, LeafAt(g, q), nd.Plane, x);
                    if (s < 0 || s >= g.Surfaces.Count) continue;
                    var sf = g.Surfaces[s]; var sp = Pl(g, sf.Plane, out bool ok2); if (!ok2) continue;
                    bool faces = Dist(sp, a) > Dist(sp, b);
                    if ((sf.Flags & SurfaceFlags.TwoSided) != 0 || faces) { anyCross = true; return true; }
                }
                int near = d0 >= 0 ? nd.FrontChild : nd.BackChild, far = d0 >= 0 ? nd.BackChild : nd.FrontChild;
                stack.Push((far, x, p1)); stack.Push((near, p0, x));
            }
            anyCross = cross; return false;
        }

        static bool HitAny(List<Piece> pieces, double[] wa, double[] wb)
        {
            foreach (var p in pieces)
            {
                const float m = 0.5f;
                if (Math.Max(wa[0], wb[0]) < p.Lo[0] - m || Math.Min(wa[0], wb[0]) > p.Hi[0] + m || Math.Max(wa[1], wb[1]) < p.Lo[1] - m || Math.Min(wa[1], wb[1]) > p.Hi[1] + m || Math.Max(wa[2], wb[2]) < p.Lo[2] - m || Math.Min(wa[2], wb[2]) > p.Hi[2] + m) continue;
                if (Hit(p.G, p.ToLocal(wa), p.ToLocal(wb), out _)) return true;
            }
            return false;
        }


        static double PolyDist(List<double[]> poly, double[] n, double[] q)
        {
            // distance from q to a convex planar polygon with unit normal n
            double d = (q[0] - poly[0][0]) * n[0] + (q[1] - poly[0][1]) * n[1] + (q[2] - poly[0][2]) * n[2];
            var pq = new[] { q[0] - d * n[0], q[1] - d * n[1], q[2] - d * n[2] };
            bool inside = true; int sign = 0;
            for (int i = 0; i < poly.Count; i++)
            {
                var a = poly[i]; var b = poly[(i + 1) % poly.Count];
                var e = new[] { b[0] - a[0], b[1] - a[1], b[2] - a[2] }; var w = new[] { pq[0] - a[0], pq[1] - a[1], pq[2] - a[2] };
                var cr = new[] { e[1] * w[2] - e[2] * w[1], e[2] * w[0] - e[0] * w[2], e[0] * w[1] - e[1] * w[0] };
                int sg = Math.Sign(cr[0] * n[0] + cr[1] * n[1] + cr[2] * n[2]); if (sg == 0) continue; if (sign == 0) sign = sg; else if (sg != sign) { inside = false; break; }
            }
            if (inside) return Math.Abs(d);
            double best = double.MaxValue;
            for (int i = 0; i < poly.Count; i++)
            {
                var a = poly[i]; var b = poly[(i + 1) % poly.Count]; var e = new[] { b[0] - a[0], b[1] - a[1], b[2] - a[2] };
                double ee = e[0] * e[0] + e[1] * e[1] + e[2] * e[2]; double t = ee <= 0 ? 0 : Math.Clamp(((q[0] - a[0]) * e[0] + (q[1] - a[1]) * e[1] + (q[2] - a[2]) * e[2]) / ee, 0, 1);
                var c = new[] { a[0] + e[0] * t - q[0], a[1] + e[1] * t - q[1], a[2] + e[2] * t - q[2] }; best = Math.Min(best, Math.Sqrt(c[0] * c[0] + c[1] * c[1] + c[2] * c[2]));
            }
            return best;
        }

        // decaloverlap <source> <scnr> [out]: scenario decals whose footprints lie on the same plane and overlap (they draw at
        // the same depth and fight). Footprint = decal system radius (upper) x placement scale, square along the decal's
        // own axes. Pairs: normals within ~25 degrees, each centre within 2 cm of the other's plane, squares overlapping.
        // Out file: one line per pair "i j paletteI paletteJ overlap" (overlap = shared area / smaller footprint area).
        public static int DecalOverlap(string[] a)
        {
            var sc = Program.OpenPak(a[1]); Scenario scn; var radius = new Dictionary<int, double>(); var names = new Dictionary<int, string>();
            using (var ss = Program.OpenStream(sc))
            {
                scn = sc.Deserialize<Scenario>(ss, sc.TagCache.GetTag(a[2], "scnr"));
                for (int i = 0; i < (scn.DecalPalette?.Count ?? 0); i++)
                {
                    var t = scn.DecalPalette[i].Instance; names[i] = t?.Name ?? "-"; radius[i] = 0;
                    if (t == null) continue;
                    var ds = sc.Deserialize<TagTool.Tags.Definitions.DecalSystem>(ss, t);
                    foreach (var e in ds.Decal) radius[i] = Math.Max(radius[i], e.Radius.Upper);
                }
            }
            var D = new List<(double[] p, double[] x, double[] y, double[] n, double r, int pal)>();
            foreach (var d in scn.Decals ?? new())
            {
                var q = d.Rotation; double x = q.I, y = q.J, z = q.K, w = q.W;
                var fx = new[] { 1 - 2 * (y * y + z * z), 2 * (x * y + w * z), 2 * (x * z - w * y) };
                var fy = new[] { 2 * (x * y - w * z), 1 - 2 * (x * x + z * z), 2 * (y * z + w * x) };
                var fz = new[] { 2 * (x * z + w * y), 2 * (y * z - w * x), 1 - 2 * (x * x + y * y) };
                double s = d.Scale > 0 ? d.Scale : 1;
                D.Add((new double[] { d.Position.X, d.Position.Y, d.Position.Z }, fx, fy, fz, radius.GetValueOrDefault(d.DecalPaletteIndex) * s, d.DecalPaletteIndex));
            }
            double Dot(double[] u, double[] v) => u[0] * v[0] + u[1] * v[1] + u[2] * v[2];
            // decal footprint: the projection axis is the decal's z (decalcheck: 609 of 609 Icebox decals have z along the surface
            // normal); the square spans its x and y axes
            var lines = new List<string>(); var pairsByPal = new Dictionary<string, int>();
            for (int i = 0; i < D.Count; i++)
                for (int j = i + 1; j < D.Count; j++)
                {
                    var A = D[i]; var B = D[j];
                    var dp = new[] { B.p[0] - A.p[0], B.p[1] - A.p[1], B.p[2] - A.p[2] };
                    if (Math.Sqrt(Dot(dp, dp)) > (A.r + B.r) * 1.5) continue;
                    if (Math.Abs(Dot(A.n, B.n)) < 0.9) continue;
                    if (Math.Abs(Dot(dp, A.n)) > 0.02 || Math.Abs(Dot(dp, B.n)) > 0.02) continue;
                    // overlap area of the two squares, sampled on A's plane (grid over A's square, point-in-B test)
                    int N = 24, inside = 0;
                    for (int u = 0; u < N; u++) for (int v = 0; v < N; v++)
                    {
                        double su = (u + 0.5) / N * 2 - 1, sv = (v + 0.5) / N * 2 - 1;
                        var pt = new[] { A.p[0] + A.r * (su * A.x[0] + sv * A.y[0]), A.p[1] + A.r * (su * A.x[1] + sv * A.y[1]), A.p[2] + A.r * (su * A.x[2] + sv * A.y[2]) };
                        var rel = new[] { pt[0] - B.p[0], pt[1] - B.p[1], pt[2] - B.p[2] };
                        if (Math.Abs(Dot(rel, B.x)) <= B.r && Math.Abs(Dot(rel, B.y)) <= B.r) inside++;
                    }
                    double shared = (double)inside / (N * N) * 4 * A.r * A.r, smaller = 4 * Math.Min(A.r, B.r) * Math.Min(A.r, B.r);
                    if (shared <= 0) continue;
                    double ov = Math.Min(1, shared / smaller);
                    lines.Add($"{i} {j} {A.pal} {B.pal} {ov:0.00}");
                    string key = names[A.pal].Split('\\').Last() + " + " + names[B.pal].Split('\\').Last(); pairsByPal[key] = pairsByPal.GetValueOrDefault(key) + 1;
                }
            Console.WriteLine($"decals {D.Count}, overlapping pairs {lines.Count}, decals involved {lines.SelectMany(l => l.Split(' ').Take(2)).Distinct().Count()}");
            foreach (var kv in pairsByPal.OrderByDescending(k => k.Value).Take(25)) Console.WriteLine($"  {kv.Value,4}  {kv.Key}");
            if (a.Length > 3 && a[3] != "-") System.IO.File.WriteAllLines(a[3], lines);
            if (a.Length > 4)
            {   // clusters' runtime decal ranges (index the scenario decal block; removing decals would shift them)
                using var ss = Program.OpenStream(sc);
                var sb = sc.Deserialize<TagTool.Tags.Definitions.ScenarioStructureBsp>(ss, sc.TagCache.GetTag(a[4], "sbsp"));
                int used = sb.Clusters.Count(c => c.RuntimeDecalCount > 0);
                Console.WriteLine($"clusters {sb.Clusters.Count}, with runtime decals {used}, total {sb.Clusters.Sum(c => (int)c.RuntimeDecalCount)}");
            }
            return 0;
        }

        // decalcheck <source> <sbsp> <scnr>: which collision surface each scenario decal sits on, and whether that surface
        // belongs to an instance flagged not-for-render (0x40) while the nearest drawn surface lies elsewhere
        public static int Decals(string[] a)
        {
            var sc = Program.OpenPak(a[1]); List<Piece> src; Scenario scn;
            using (var ss = Program.OpenStream(sc)) { src = Pieces(sc, ss, a[2], true); scn = sc.Deserialize<Scenario>(ss, sc.TagCache.GetTag(a[3], "scnr")); }
            var polys = new List<(Piece p, List<double[]> poly, double[] n)>();
            foreach (var p in src)
                for (int s = 0; s < p.G.Surfaces.Count; s++)
                {
                    var l = Loop(p.G, s); if (l == null || l.Count < 3) continue;
                    var w = l.Select(v => p.ToWorld(v[0], v[1], v[2])).ToList();
                    var e1 = new[] { w[1][0] - w[0][0], w[1][1] - w[0][1], w[1][2] - w[0][2] }; var e2 = new[] { w[2][0] - w[0][0], w[2][1] - w[0][1], w[2][2] - w[0][2] };
                    var n = new[] { e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0] }; double ln = Math.Sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2]); if (ln < 1e-9) continue;
                    polys.Add((p, w, new[] { n[0] / ln, n[1] / ln, n[2] / ln }));
                }
            if (a.Length > 4)
            {
                // decal positions and normals (rotation applied to +x and +z), and hidden (not-for-render) instance indices
                var lines = new List<string>();
                foreach (var d in scn.Decals ?? new()) { var q = d.Rotation; double x = q.I, y = q.J, z = q.K, w = q.W;
                    var fx = new[] { 1 - 2 * (y * y + z * z), 2 * (x * y + w * z), 2 * (x * z - w * y) }; var uz = new[] { 2 * (x * z + w * y), 2 * (y * z - w * x), 1 - 2 * (x * x + y * y) };
                    lines.Add($"D {d.Position.X} {d.Position.Y} {d.Position.Z} {fx[0]:0.0000} {fx[1]:0.0000} {fx[2]:0.0000} {uz[0]:0.0000} {uz[1]:0.0000} {uz[2]:0.0000} {d.DecalPaletteIndex}"); }
                foreach (var p in src.Where(p => (p.Flags & 0x40) != 0)) lines.Add($"H {p.Index}");
                System.IO.File.WriteAllLines(a[4], lines);
            }
            var axisHits = new int[3];
            int onHidden = 0, onHiddenOffset = 0, onVisible = 0, none = 0; var gaps = new List<double>(); var ex = new List<string>();
            foreach (var d in scn.Decals ?? new())
            {
                var q = new double[] { d.Position.X, d.Position.Y, d.Position.Z };
                double bh = double.MaxValue, bv = double.MaxValue; string hn = null; double[] hnorm = null; ushort hf = 0; double[] vpt = null; double[] vn = null;
                foreach (var (p, poly, n) in polys)
                {
                    if (q[0] < p.Lo[0] - 1 || q[0] > p.Hi[0] + 1 || q[1] < p.Lo[1] - 1 || q[1] > p.Hi[1] + 1 || q[2] < p.Lo[2] - 1 || q[2] > p.Hi[2] + 1) continue;
                    double dist = PolyDist(poly, n, q);
                    if ((p.Flags & 0x40) != 0) { if (dist < bh) { bh = dist; hn = p.Name; hnorm = n; hf = p.Flags; } } else if (dist < bv) { bv = dist; vpt = poly[0]; vn = n; }
                }
                if (Math.Min(bh, bv) > 0.25) { none++; continue; }
                {   // which decal axis is the surface normal (diagnostic for the projection axis)
                    var sn = bh < bv ? hnorm : vn; var r = d.Rotation; double x = r.I, y = r.J, z = r.K, w = r.W;
                    var ax = new[] { new[] { 1 - 2 * (y * y + z * z), 2 * (x * y + w * z), 2 * (x * z - w * y) }, new[] { 2 * (x * y - w * z), 1 - 2 * (x * x + z * z), 2 * (y * z + w * x) }, new[] { 2 * (x * z + w * y), 2 * (y * z - w * x), 1 - 2 * (x * x + y * y) } };
                    if (sn != null) { int best = 0; double bd = 0; for (int k = 0; k < 3; k++) { double dd = Math.Abs(ax[k][0] * sn[0] + ax[k][1] * sn[1] + ax[k][2] * sn[2]); if (dd > bd) { bd = dd; best = k; } } if (bd > 0.9) axisHits[best]++; }
                }
                if (bh < bv) { onHidden++; if (bv - bh > 0.002) { onHiddenOffset++; gaps.Add(bv - bh); if (ex.Count < 8) { double side = vpt == null ? 0 : (q[0] - vpt[0]) * vn[0] + (q[1] - vpt[1]) * vn[1] + (q[2] - vpt[2]) * vn[2]; ex.Add($"{hn} flags 0x{hf:X} hidden {bh:0.0000} drawn {bv:0.0000}; decal on the {(side > 0 ? "front" : "back")} side of the drawn surface ({side:0.0000})"); } } }
                else onVisible++;
            }
            Console.WriteLine($"decals {scn.Decals?.Count}: nearest surface drawn {onVisible}, nearest surface a not-for-render instance {onHidden} ({onHiddenOffset} with the drawn surface further than 2 mm; median gap {(gaps.Count > 0 ? gaps.OrderBy(x => x).ElementAt(gaps.Count / 2) : 0):0.0000}), no surface within 0.25: {none}");
            Console.WriteLine($"decal axis along the surface normal: x {axisHits[0]}, y {axisHits[1]}, z {axisHits[2]}");
            foreach (var e in ex) Console.WriteLine("  " + e);
            return 0;
        }

        // points <map> <sbsp> <piece name regex> <count> [slope]: test points (x y z yaw) on walkable surfaces of matching
        // pieces, at their centre, spaced at least 2 units apart; "slope" picks only sloped surfaces (ramps: 0.5 < up < 0.97)
        public static int Points(string[] a)
        {
            var c = Program.OpenPak(a[1]); List<Piece> ps;
            using (var s = Program.OpenStream(c)) ps = Pieces(c, s, a[2], true);
            var re = new System.Text.RegularExpressions.Regex(a[3], System.Text.RegularExpressions.RegexOptions.IgnoreCase);
            int want = int.Parse(a[4]); bool slope = a.Length > 5 && a[5] == "slope";
            var got = new List<double[]>();
            foreach (var p in ps.Where(p => a[3].StartsWith("#") ? p.Index == int.Parse(a[3].Substring(1)) : re.IsMatch(p.Name)))
                for (int si = 0; si < p.G.Surfaces.Count && got.Count < want; si++)
                {
                    var sf = p.G.Surfaces[si]; var pl = Pl(p.G, sf.Plane, out bool ok); if (!ok) continue;
                    double nz = pl.I * p.R[0][2] + pl.J * p.R[1][2] + pl.K * p.R[2][2];
                    if (slope ? (nz <= 0.5 || nz >= 0.97) : nz < 0.9) continue;
                    var loop = Loop(p.G, si); if (loop == null || loop.Count < 3) continue;
                    var w = loop.Select(v => p.ToWorld(v[0], v[1], v[2])).ToList();
                    double area = 0; for (int i = 1; i + 1 < w.Count; i++) { var e1 = new[] { w[i][0] - w[0][0], w[i][1] - w[0][1], w[i][2] - w[0][2] }; var e2 = new[] { w[i + 1][0] - w[0][0], w[i + 1][1] - w[0][1], w[i + 1][2] - w[0][2] }; var cr = new[] { e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0] }; area += Math.Sqrt(cr[0] * cr[0] + cr[1] * cr[1] + cr[2] * cr[2]) / 2; }
                    if (area < (slope ? 0.05 : 0.6)) continue;
                    var cpt = new[] { w.Average(v => v[0]), w.Average(v => v[1]), w.Average(v => v[2]) };
                    if (got.Any(g => (g[0] - cpt[0]) * (g[0] - cpt[0]) + (g[1] - cpt[1]) * (g[1] - cpt[1]) < 4)) continue;
                    got.Add(cpt); Console.WriteLine($"{cpt[0]:0.000} {cpt[1]:0.000} {cpt[2]:0.000} 0   # {p.Name} surface {si} up {nz:0.00} area {area:0.00}");
                }
            return 0;
        }

        // raycol <map> <sbsp> x y z0 z1: collision pieces a vertical segment crosses, in 0.05 steps (first hit per piece)
        public static int Ray(string[] a)
        {
            var c = Program.OpenPak(a[1]); List<Piece> ps;
            using (var s = Program.OpenStream(c)) ps = Pieces(c, s, a[2], true);
            double x = double.Parse(a[3]), y = double.Parse(a[4]), z0 = double.Parse(a[5]), z1 = double.Parse(a[6]);
            using (var s2 = Program.OpenStream(c))
            {
                var sb = c.Deserialize<ScenarioStructureBsp>(s2, c.TagCache.GetTag(a[2], "sbsp"));
                var st = ps.First(p => p.Index < 0).G;
                int lf = LeafAt(st, new[] { x, y, (z0 + z1) / 2 });
                foreach (var zz in new[] { z0, (z0 + z1) / 2, z1 })
                {
                    int l2 = LeafAt(st, new[] { x, y, zz }); int cl = l2 >= 0 && l2 < sb.Leaves.Count ? sb.Leaves[l2].ClusterNew : -1;
                    var b = cl >= 0 && cl < sb.Clusters.Count ? sb.Clusters[cl] : null;
                    Console.WriteLine($"z {zz:0.00}: leaf {l2} cluster {cl}" + (b == null ? "" : $" bounds x {b.BoundsX.Lower:0.0}..{b.BoundsX.Upper:0.0} y {b.BoundsY.Lower:0.0}..{b.BoundsY.Upper:0.0} z {b.BoundsZ.Lower:0.0}..{b.BoundsZ.Upper:0.0}"));
                }
            }
            var seen = new HashSet<string>();
            for (double z = z0; z > z1; z -= 0.05)
                foreach (var p in ps)
                {
                    var wa = new[] { x, y, z }; var wb = new[] { x, y, z - 0.05 };
                    if (x < p.Lo[0] - 0.5 || x > p.Hi[0] + 0.5 || y < p.Lo[1] - 0.5 || y > p.Hi[1] + 0.5) continue;
                    if (Hit(p.G, p.ToLocal(wa), p.ToLocal(wb), out _)) { string k = p.Name + "#" + p.Index; if (seen.Add(k + z.ToString("0.00"))) Console.WriteLine($"z {z:0.00}..{z - 0.05:0.00}: {p.Name} (instance {p.Index}, flags 0x{p.Flags:X})"); }
                }
            return 0;
        }

        // gapscan <map> <sbsp> [n]: walkable instance surfaces with clear air 2.5 above and nothing within 1.2 below them
        // (good single-drop test points), first n
        public static int GapScan(string[] a)
        {
            var c = Program.OpenPak(a[1]); List<Piece> ps;
            using (var s = Program.OpenStream(c)) ps = Pieces(c, s, a[2], true);
            int want = a.Length > 3 ? int.Parse(a[3]) : 10, got = 0; double minArea = a.Length > 4 ? double.Parse(a[4]) : 0.6, below = a.Length > 5 ? double.Parse(a[5]) : 0.8;
            foreach (var p in ps.Where(p => p.Index >= 0))
                for (int si = 0; si < p.G.Surfaces.Count && got < want; si++)
                {
                    var sf = p.G.Surfaces[si]; var pl = Pl(p.G, sf.Plane, out bool ok); if (!ok) continue;
                    double nz = pl.I * p.R[0][2] + pl.J * p.R[1][2] + pl.K * p.R[2][2]; if (nz < (a.Length > 6 ? double.Parse(a[6]) : 0.95)) continue;
                    var loop = Loop(p.G, si); if (loop == null || loop.Count < 3) continue;
                    var w = loop.Select(v => p.ToWorld(v[0], v[1], v[2])).ToList();
                    double area = 0; for (int i = 1; i + 1 < w.Count; i++) { var e1 = new[] { w[i][0] - w[0][0], w[i][1] - w[0][1], w[i][2] - w[0][2] }; var e2 = new[] { w[i + 1][0] - w[0][0], w[i + 1][1] - w[0][1], w[i + 1][2] - w[0][2] }; var cr = new[] { e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0] }; area += Math.Sqrt(cr[0] * cr[0] + cr[1] * cr[1] + cr[2] * cr[2]) / 2; }
                    if (area < minArea) continue;
                    double x = w.Average(v => v[0]), y = w.Average(v => v[1]), z = w.Average(v => v[2]);
                    if (HitAny(ps, new[] { x, y, z + 2.0 }, new[] { x, y, z + 0.05 })) continue;
                    if (HitAny(ps.Where(q => q != p).ToList(), new[] { x, y, z - 0.02 }, new[] { x, y, z - below })) continue;
                    if (HitAny(new List<Piece> { p }, new[] { x, y, z - 0.05 }, new[] { x, y, z - below })) continue;
                    Console.WriteLine($"{x:0.000} {y:0.000} {z:0.000} 0   # {p.Name} (instance {p.Index}) area {area:0.0}"); got++;
                }
            return 0;
        }
        public static int Run(string[] a)
        {
            var sc = Program.OpenPak(a[1]); var oc = Program.OpenPak(a[3]);
            List<Piece> src, outp;
            using (var ss = Program.OpenStream(sc)) src = Pieces(sc, ss, a[2], true);
            using (var os = Program.OpenStream(oc)) outp = Pieces(oc, os, a[4], false);
            bool list = a.Length > 5;
            // walkable source surfaces (world centre, up normal)
            var tests = new List<(string piece, double[] c, bool invisible, bool twoSided)>();
            foreach (var p in src)
                for (int s = 0; s < p.G.Surfaces.Count; s++)
                {
                    var sf = p.G.Surfaces[s]; var pl = Pl(p.G, sf.Plane, out bool ok); if (!ok) continue;
                    var n = new[] { pl.I * p.R[0][0] + pl.J * p.R[1][0] + pl.K * p.R[2][0], pl.I * p.R[0][1] + pl.J * p.R[1][1] + pl.K * p.R[2][1], pl.I * p.R[0][2] + pl.J * p.R[1][2] + pl.K * p.R[2][2] };
                    if (n[2] < 0.6) continue;
                    var loop = Loop(p.G, s); if (loop == null || loop.Count < 3) continue;
                    double cx = loop.Average(v => v[0]), cy = loop.Average(v => v[1]), cz = loop.Average(v => v[2]);
                    tests.Add((p.Name, p.ToWorld(cx, cy, cz), (sf.Flags & SurfaceFlags.Invisible) != 0, (sf.Flags & SurfaceFlags.TwoSided) != 0));
                }
            Console.WriteLine($"collcheck: {tests.Count} walkable source surfaces; source {src.Count} collision pieces, converted {outp.Count}");
            int srcMiss = 0, outMiss = 0; var missBy = new Dictionary<string, (int miss, int all)>(); var srcMissBy = new Dictionary<string, int>();
            foreach (var t in tests)
            {
                var wa = new[] { t.c[0], t.c[1], t.c[2] + 0.3 }; var wb = new[] { t.c[0], t.c[1], t.c[2] - 0.3 };
                bool hs = HitAny(src, wa, wb), ho = HitAny(outp, wa, wb);
                string key = System.Text.RegularExpressions.Regex.Replace(t.piece, @"_?\d+__\(", "__(") + (t.invisible ? " [invisible]" : "") + (t.twoSided ? " [two-sided]" : "");
                var e = missBy.TryGetValue(key, out var q) ? q : (miss: 0, all: 0); e.all++;
                if (!hs) { srcMiss++; srcMissBy[key] = srcMissBy.TryGetValue(key, out int z) ? z + 1 : 1; }
                if (hs && !ho) { outMiss++; e.miss++; }
                missBy[key] = e;
            }
            Console.WriteLine($"control (source against itself): {tests.Count - srcMiss} of {tests.Count} stop ({srcMiss} do not: tester limits)");
            Console.WriteLine($"converted: {outMiss} of {tests.Count - srcMiss} surfaces that stop a player in the source do not stop one in the converted map");
            foreach (var kv in missBy.Where(k => k.Value.miss > 0).OrderByDescending(k => k.Value.miss).Take(list ? 400 : 40)) Console.WriteLine($"  {kv.Value.miss}/{kv.Value.all} {kv.Key}");
            if (list) foreach (var kv in srcMissBy.OrderByDescending(k => k.Value).Take(30)) Console.WriteLine($"  control miss {kv.Value} {kv.Key}");
            return 0;
        }
    }
}
