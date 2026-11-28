// Visibility data check, source against converted map: cluster portals (sides, flags, vertices, and the collision plane
// each one names, compared by value), each cluster's portal list, and the scenario's per-cluster potentially-visible
// sets. viscompare <source> <sbsp> <scnr> <converted .map> <sbsp> <scnr>. Reads only; map-agnostic.
using System;
using System.Collections.Generic;
using System.Linq;
using TagTool.Cache;
using TagTool.Common;
using TagTool.Tags.Definitions;

namespace Ho2H3
{
    public static class VisCheck
    {
        static (ScenarioStructureBsp sb, Scenario sc, List<RealPlane3d> planes) Load(string path, string sbsp, string scnr)
        {
            var c = Program.OpenPak(path);
            using var s = Program.OpenStream(c);
            var sb = c.Deserialize<ScenarioStructureBsp>(s, c.TagCache.GetTag(sbsp, "sbsp"));
            var sc = c.Deserialize<Scenario>(s, c.TagCache.GetTag(scnr, "scnr"));
            var r = c.ResourceCache.GetStructureBspTagResources(sb.CollisionBspResource);
            var planes = r.LargeCollisionBsps?.Count > 0 ? r.LargeCollisionBsps[0].Planes.Select(p => p.Value).ToList() : r.CollisionBsps[0].Planes.Select(p => p.Value).ToList();
            return (sb, sc, planes);
        }
        public static int Run(string[] a)
        {
            var (s1, c1, p1) = Load(a[1], a[2], a[3]); var (s2, c2, p2) = Load(a[4], a[5], a[6]);
            Console.WriteLine($"clusters {s1.Clusters.Count} -> {s2.Clusters.Count}; portals {s1.ClusterPortals.Count} -> {s2.ClusterPortals.Count}; collision planes {p1.Count} -> {p2.Count}");
            int n = Math.Min(s1.ClusterPortals.Count, s2.ClusterPortals.Count), side = 0, flags = 0, verts = 0, plane = 0, badIdx = 0;
            for (int i = 0; i < n; i++)
            {
                var x = s1.ClusterPortals[i]; var y = s2.ClusterPortals[i];
                if (x.BackCluster != y.BackCluster || x.FrontCluster != y.FrontCluster) side++;
                if (x.Flags != y.Flags) flags++;
                if (x.Vertices.Count != y.Vertices.Count || x.Vertices.Zip(y.Vertices).Any(z => Math.Abs(z.First.Position.X - z.Second.Position.X) > 1e-3 || Math.Abs(z.First.Position.Y - z.Second.Position.Y) > 1e-3 || Math.Abs(z.First.Position.Z - z.Second.Position.Z) > 1e-3)) verts++;
                int i1 = x.PlaneIndex & 0x7FFFFFFF, i2 = y.PlaneIndex & 0x7FFFFFFF;
                if (i1 >= p1.Count || i2 >= p2.Count) { badIdx++; continue; }
                var q1 = p1[i1]; var q2 = p2[i2];
                if (Math.Abs(q1.I - q2.I) > 1e-3 || Math.Abs(q1.J - q2.J) > 1e-3 || Math.Abs(q1.K - q2.K) > 1e-3 || Math.Abs(q1.D - q2.D) > 1e-2) plane++;
            }
            Console.WriteLine($"portals differing: sides {side}, flags {flags}, vertices {verts}, named plane (by value) {plane}, plane index out of range {badIdx}");
            int cl = 0; for (int i = 0; i < Math.Min(s1.Clusters.Count, s2.Clusters.Count); i++) if (!s1.Clusters[i].Portals.Select(p => p.PortalIndex).SequenceEqual(s2.Clusters[i].Portals.Select(p => p.PortalIndex))) cl++;
            Console.WriteLine($"clusters whose portal list differs: {cl}");
            string Bits(Scenario sc) => string.Join("|", (sc.ZoneSetPvs ?? new()).Select(z => string.Join(";", z.StructureBspPvs.Select(b => string.Join(",", b.ClusterPvs.Select(cp => string.Join(".", cp.ClusterPvsBitVectors.Select(v => string.Join("", v.Bits.Select(d => ((uint)d.Bits).ToString("X8")))))))))));
            string Sky(Scenario sc) => string.Join("|", (sc.ZoneSetPvs ?? new()).Select(z => string.Join(";", z.StructureBspPvs.Select(b => string.Join(",", b.AttachedSkyIndices.Select(k => k.SkyIndex)) + "/" + string.Join(",", b.VisibleSkyIndices.Select(k => k.SkyIndex))))));
            Console.WriteLine($"zone set PVS: {c1.ZoneSetPvs?.Count} -> {c2.ZoneSetPvs?.Count}; cluster bit vectors {(Bits(c1) == Bits(c2) ? "identical" : "DIFFERENT")}; sky indices {(Sky(c1) == Sky(c2) ? "identical" : "DIFFERENT: " + Sky(c1).Substring(0, Math.Min(80, Sky(c1).Length)) + " -> " + Sky(c2).Substring(0, Math.Min(80, Sky(c2).Length)))}");
            return 0;
        }
    }
}
