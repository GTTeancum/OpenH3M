// Two-sided collision surfaces: Reach (so Halo Online) stores each as a pair - the surface and a coincident copy with the
// plane negated, both flagged two-sided. Stock Halo 3 stores one surface with the two-sided flag (Guardian: 592 two-sided
// invisible instance surfaces, no negated copies). The pairs are what Reach's invisible "sphere only" walking surfaces
// over stairs and glass bridges are made of (Sword Base: 437 pairs), and in Halo 3 the player fell through them.
// For every collision geometry holding such pairs, the negated copy whose partner (same vertices, opposite order) exists
// is removed and the geometry rebuilt: edges from the remaining surfaces (a surface that would make an edge serve a third
// time keeps vertices of its own), planes and flags kept, tree by TagTool's LargeCollisionBSPBuilder (empty leaves allowed,
// CollisionSimplify.GenerateBsp). Runs before plane-negation folding, ramps and MOPP generation. Map-agnostic.
using System;
using System.Collections.Generic;
using System.Linq;
using TagTool.Common;
using TagTool.Geometry.BspCollisionGeometry;
using TagTool.Geometry.BspCollisionGeometry.Utils;
using TagTool.Tags;

namespace Ho2H3
{
    public static class TwoSided
    {
        public static int Removed, Rebuilt, Failed, EmptyLeaves;

        static List<int> Loop(CollisionGeometry c, int s)
        {
            var sf = c.Surfaces[s]; var loop = new List<int>(); int e = sf.FirstEdge, guard = 0;
            do
            {
                if (e < 0 || e >= c.Edges.Count || guard++ > 4096) return null;
                var ed = c.Edges[e];
                if (ed.RightSurface == s) { loop.Add(ed.EndVertex); e = ed.ReverseEdge; } else { loop.Add(ed.StartVertex); e = ed.ForwardEdge; }
            } while (e != sf.FirstEdge);
            return loop.Count >= 3 ? loop : null;
        }

        // returns the fixed geometry, or the input when it has no pairs or the rebuild fails
        public static CollisionGeometry Fix(CollisionGeometry c)
        {
            if (c?.Surfaces == null || c.Surfaces.Count == 0 || Environment.GetEnvironmentVariable("HO2H3_NO_TWOSIDED") == "1") return c;
            const SurfaceFlags TS = SurfaceFlags.TwoSided, NEG = SurfaceFlags.PlaneNegated;
            if (!c.Surfaces.Any(s => (s.Flags & TS) != 0 && (s.Flags & NEG) != 0)) return c;
            var loops = new List<int>[c.Surfaces.Count];
            for (int s = 0; s < c.Surfaces.Count; s++) loops[s] = Loop(c, s);
            string Key(List<int> l) => string.Join(",", l.OrderBy(v => v));
            var plain = new Dictionary<string, int>();
            for (int s = 0; s < c.Surfaces.Count; s++)
                if (loops[s] != null && (c.Surfaces[s].Flags & TS) != 0 && (c.Surfaces[s].Flags & NEG) == 0) plain[Key(loops[s])] = s;
            var drop = new bool[c.Surfaces.Count]; int n = 0;
            for (int s = 0; s < c.Surfaces.Count; s++)
                if (loops[s] != null && (c.Surfaces[s].Flags & TS) != 0 && (c.Surfaces[s].Flags & NEG) != 0 && plain.ContainsKey(Key(loops[s]))) { drop[s] = true; n++; }
            if (n == 0) return c;

            var g = new CollisionGeometry
            {
                Bsp3dNodes = new TagBlock<Bsp3dNode>(), Planes = new TagBlock<Plane>(), Leaves = new TagBlock<Leaf>(), Bsp2dReferences = new TagBlock<Bsp2dReference>(),
                Bsp2dNodes = new TagBlock<Bsp2dNode>(), Surfaces = new TagBlock<Surface>(), Edges = new TagBlock<Edge>(), Vertices = new TagBlock<Vertex>()
            };
            foreach (var p in c.Planes) g.Planes.Add(new Plane { Value = p.Value });
            foreach (var v in c.Vertices) g.Vertices.Add(new Vertex { Point = v.Point, FirstEdge = 0xFFFF });
            var edgeOf = new Dictionary<(int, int), int>();
            for (int s0 = 0; s0 < c.Surfaces.Count; s0++)
            {
                if (drop[s0] || loops[s0] == null) continue;
                var src = c.Surfaces[s0]; var lp = loops[s0];
                bool clash = false;
                for (int i = 0; i < lp.Count && !clash; i++)
                {
                    int a = lp[i], b = lp[(i + 1) % lp.Count];
                    if (edgeOf.ContainsKey((a, b)) || (edgeOf.TryGetValue((b, a), out int eo) && g.Edges[eo].RightSurface != 0xFFFF)) clash = true;
                }
                if (clash)
                {
                    // own vertices: not joined to neighbours
                    lp = lp.Select(v => { g.Vertices.Add(new Vertex { Point = c.Vertices[v].Point, FirstEdge = 0xFFFF }); return g.Vertices.Count - 1; }).ToList();
                }
                if (g.Vertices.Count > 0xFFFE || g.Edges.Count + lp.Count > 0xFFFE || g.Surfaces.Count > 0xFFFE) { Failed++; return c; }
                int s = g.Surfaces.Count;
                g.Surfaces.Add(new Surface { Plane = src.Plane, MaterialIndex = src.MaterialIndex, Flags = src.Flags, BreakableSurfaceIndex = src.BreakableSurfaceIndex, BestPlaneCalculationVertex = src.BestPlaneCalculationVertex });
                var es = new List<int>();
                for (int i = 0; i < lp.Count; i++)
                {
                    int a = lp[i], b = lp[(i + 1) % lp.Count];
                    if (edgeOf.TryGetValue((b, a), out int e) && g.Edges[e].RightSurface == 0xFFFF) g.Edges[e].RightSurface = (ushort)s;
                    else { e = g.Edges.Count; g.Edges.Add(new Edge { StartVertex = (ushort)a, EndVertex = (ushort)b, LeftSurface = (ushort)s, RightSurface = 0xFFFF, ForwardEdge = 0xFFFF, ReverseEdge = 0xFFFF }); edgeOf[(a, b)] = e; }
                    es.Add(e);
                    if (g.Vertices[a].FirstEdge == 0xFFFF) g.Vertices[a].FirstEdge = (ushort)e;
                }
                for (int i = 0; i < es.Count; i++) { var ed = g.Edges[es[i]]; int next = es[(i + 1) % es.Count]; if (ed.LeftSurface == s) ed.ForwardEdge = (ushort)next; else ed.ReverseEdge = (ushort)next; }
                g.Surfaces[s].FirstEdge = (ushort)es[0];
            }
            // in place (default): the source's own tree is kept; its 2D BSP leaves that named a removed copy name its partner,
            // and surface indices are renumbered for the shortened surface list. Nothing is rebuilt, so nothing can fail,
            // and the structure BSP's leaf -> cluster table stays valid (HO2H3_TWOSIDED_REBUILD=1: the old rebuild).
            if (Environment.GetEnvironmentVariable("HO2H3_TWOSIDED_REBUILD") != "1")
            {
                var newIndex = new int[c.Surfaces.Count]; int k = 0;
                for (int s0 = 0; s0 < c.Surfaces.Count; s0++) newIndex[s0] = drop[s0] || loops[s0] == null ? -1 : k++;
                for (int s0 = 0; s0 < c.Surfaces.Count; s0++) if (drop[s0]) newIndex[s0] = newIndex[plain[Key(loops[s0])]];
                bool bad = false;
                short Remap(short child)
                {
                    if ((child & 0x8000) == 0 || (ushort)child == 0xFFFF) return child;
                    int old = child & 0x7FFF; int ni = old < newIndex.Length ? newIndex[old] : -1;
                    if (ni < 0) { bad = true; return child; }
                    return (short)(ni | 0x8000);
                }
                foreach (var nd in c.Bsp3dNodes) g.Bsp3dNodes.Add(new Bsp3dNode { Value = nd.Value });
                foreach (var lf in c.Leaves) g.Leaves.Add(new Leaf { Flags = lf.Flags, Bsp2dReferenceCount = lf.Bsp2dReferenceCount, FirstBsp2dReference = lf.FirstBsp2dReference });
                foreach (var rf in c.Bsp2dReferences) g.Bsp2dReferences.Add(new Bsp2dReference { PlaneIndex = rf.PlaneIndex, Bsp2dNodeIndex = Remap(rf.Bsp2dNodeIndex) });
                foreach (var n2 in c.Bsp2dNodes) g.Bsp2dNodes.Add(new Bsp2dNode { Plane = n2.Plane, LeftChild = Remap(n2.LeftChild), RightChild = Remap(n2.RightChild) });
                if (c.Bsp3dSupernodes != null) g.Bsp3dSupernodes = c.Bsp3dSupernodes;
                if (bad || g.Surfaces.Count != k) { Failed++; return c; }
                Removed += n; Rebuilt++;
                return g;
            }
            var rz = new ResizeCollisionBSP(); var large = rz.GrowCollisionBsp(g);
            // only a tree TagTool's builder verifies itself: trees that needed the empty-leaf fallback made Breakneck's map
            // fail to load ("players failed to load content", 2026-11-23); such pieces keep their original pairs
            int fb0 = CollisionSimplify.FallbackUsed;
            if (!CollisionSimplify.GenerateBsp(ref large) || !rz.collision_bsp_check_counts(large) || CollisionSimplify.FallbackUsed > fb0) { Failed++; return c; }
            EmptyLeaves += large.Leaves.Count(l => l.Bsp2dReferenceCount == 0);
            Removed += n; Rebuilt++;
            return rz.ShrinkCollisionBsp(large);
        }
    }
}
