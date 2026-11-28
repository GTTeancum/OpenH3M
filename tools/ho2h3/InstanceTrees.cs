// Placed-piece (instanced geometry) collision trees rebuilt the way Halo 3's tool builds them.
//
// Why (read from the Halo 3 Mythic default.xex, see README "Placed-piece collision"): Halo 3 360's collision BSP vector test
// (0x822C8890, used for every placed piece by 0x820C0B00) only looks for a surface where the segment passes from an open
// leaf into solid space (a 3D node child of -1), from solid into open, or between two leaves flagged double-sided. Two open
// leaves either side of a one-sided surface means the surface is never found: a falling player passes through it (traced in
// the running game: Sword Base walkway piece 824 tested about 70 times during a drop, never hit). Halo 3's builder makes the
// space behind surfaces solid (TagTool CollisionBSPBuilder, the tool's algorithm: a region holding only used back faces is
// solid); Reach's trees, as carried by Halo Online, often leave it open.
//
// What: each definition's tree is rebuilt from its own surfaces with TagTool's CollisionBSPBuilder; the rebuilt tree is kept
// only if it fits Halo 3's limits, every 2D reference is reachable by the game's plane-matching rule, and the game's vector
// test (CollCheck.LineMisses) misses no more sample points on its one-sided surfaces than with the shipped tree.
using System;
using System.Collections.Generic;
using TagTool.Geometry.BspCollisionGeometry;
using TagTool.Geometry.BspCollisionGeometry.Utils;

namespace Ho2H3
{
    static class InstanceTrees
    {
        // TagTool's CollisionBSPBuilder is internal: CollisionBSPBuilder.generate_bsp(ref CollisionGeometry, bool)
        static readonly Type BuilderType = typeof(LargeCollisionBSPBuilder).Assembly.GetType("TagTool.Geometry.BspCollisionGeometry.Utils.CollisionBSPBuilder", true);
        static bool Build(ref CollisionGeometry g)
        {
            var b = Activator.CreateInstance(BuilderType, true);
            var args = new object[] { g, false };
            bool ok = (bool)BuilderType.GetMethod("generate_bsp").Invoke(b, args);
            g = (CollisionGeometry)args[0];
            return ok;
        }

        public static void Rebuild(IList<InstancedGeometryBlock> defs, string name, List<string> log)
        {
            if (Environment.GetEnvironmentVariable("HO2H3_KEEP_INSTANCE_TREES") == "1") { log.Add($"instance trees: {name}: kept as shipped (HO2H3_KEEP_INSTANCE_TREES)"); return; }
            int kept = 0, rebuilt = 0, failed = 0, worse = 0; long before = 0, after = 0, samples = 0;
            for (int d = 0; d < defs.Count; d++)
            {
                var g = defs[d].CollisionInfo; if (g?.Surfaces == null || g.Surfaces.Count == 0) continue;
                var (t0, m0) = CollCheck.LineMisses(g, false);
                samples += t0; before += m0;
                if (m0 == 0) { kept++; continue; }
                CollisionGeometry nb = null; bool ok = false;
                try { nb = g.DeepClone(); ok = Build(ref nb); } catch (Exception ex) { log.Add($"instance trees: {name}: definition {d}: builder failed: {(ex.InnerException ?? ex).Message}"); }
                if (ok) ok = nb.Bsp2dNodes.Count < 0x8000 && nb.Surfaces.Count < 0x8000 && nb.Bsp3dNodes.Count < 0x800000 && nb.Leaves.Count < 0x800000 && nb.Planes.Count < 0x8000;
                if (ok && CollCheck.UnusableRefs(nb) > 0) ok = false;
                if (!ok) { failed++; after += m0; continue; }
                var (_, m1) = CollCheck.LineMisses(nb, false);
                if (m1 > m0) { worse++; after += m0; continue; }
                defs[d].CollisionInfo = nb; rebuilt++; after += m1;
            }
            log.Add($"instance trees: {name}: {rebuilt} rebuilt with Halo 3's builder, {kept} already complete, {failed} not rebuildable, {worse} kept (rebuild no better); line-test misses on one-sided surface samples {before} -> {after} of {samples}");
        }
    }
}
