// buckets <360 map> <sbsp>: render instances (definition with a drawable mesh) missing from every cluster mesh's
// instance buckets (Halo 3 draws placed level pieces only through those lists)
using System;
using System.IO;
using System.Linq;
using TagTool.Cache;
using TagTool.Tags.Definitions;

namespace Ho2H3
{
    static class BucketProbe
    {
        public static int Run(string[] a)
        {
            var c = GameCache.Open(new FileInfo(a[1]));
            using (var s = c.OpenCacheRead())
            {
                var sb = c.Deserialize<ScenarioStructureBsp>(s, c.TagCache.GetTag(a[2], "sbsp"));
                var res = c.ResourceCache.GetStructureBspTagResources(sb.CollisionBspResource);
                Console.WriteLine($"structure leaves (leaf -> cluster table) {sb.Leaves?.Count}; structure collision BSP leaves {res.CollisionBsps?.FirstOrDefault()?.Leaves?.Count}");
                var inBucket = new System.Collections.Generic.HashSet<int>();
                int meshesWithBuckets = 0;
                foreach (var m in sb.Geometry.Meshes) if (m.InstanceBuckets != null && m.InstanceBuckets.Count > 0) { meshesWithBuckets++; foreach (var b in m.InstanceBuckets) foreach (var i in b.Instances) inBucket.Add(i.InstanceIndex); }
                int drawable = 0, missing = 0; var ex = new System.Collections.Generic.List<string>();
                for (int i = 0; i < sb.InstancedGeometryInstances.Count; i++)
                {
                    var gi = sb.InstancedGeometryInstances[i]; var d = gi.DefinitionIndex;
                    if (d < 0 || d >= res.InstancedGeometry.Count) continue;
                    int mi = res.InstancedGeometry[d].MeshIndex;
                    if (mi < 0 || mi >= sb.Geometry.Meshes.Count || sb.Geometry.Meshes[mi].Parts.Count == 0) continue;
                    drawable++;
                    if (!inBucket.Contains(i)) { missing++; if (ex.Count < 10) ex.Add($"{i} {c.StringTable.GetString(gi.Name)}"); }
                }
                Console.WriteLine($"clusters {sb.Clusters.Count}, cluster meshes with buckets {meshesWithBuckets}; drawable instances {drawable}, in no bucket {missing}");
                // bucket placement: is each bucketed instance's centre inside (or within 2 units of) the cluster that lists it?
                int inside = 0, outside = 0; var oex = new System.Collections.Generic.List<string>();
                var bucketsOf = new System.Collections.Generic.Dictionary<int, int>();
                for (int k = 0; k < sb.Clusters.Count; k++)
                {
                    var cl = sb.Clusters[k]; if (cl.MeshIndex < 0 || cl.MeshIndex >= sb.Geometry.Meshes.Count) continue;
                    var m = sb.Geometry.Meshes[cl.MeshIndex]; if (m.InstanceBuckets == null) continue;
                    foreach (var b in m.InstanceBuckets) foreach (var x in b.Instances)
                    {
                        var c2 = sb.InstancedGeometryInstances[x.InstanceIndex].WorldBoundingSphereCenter; const float pad = 2;
                        bool inn = c2.X >= cl.BoundsX.Lower - pad && c2.X <= cl.BoundsX.Upper + pad && c2.Y >= cl.BoundsY.Lower - pad && c2.Y <= cl.BoundsY.Upper + pad && c2.Z >= cl.BoundsZ.Lower - pad && c2.Z <= cl.BoundsZ.Upper + pad;
                        if (inn) inside++; else { outside++; if (oex.Count < 6) oex.Add($"instance {x.InstanceIndex} {c.StringTable.GetString(sb.InstancedGeometryInstances[x.InstanceIndex].Name)} listed by cluster {k}"); }
                        bucketsOf[x.InstanceIndex] = bucketsOf.TryGetValue(x.InstanceIndex, out var n) ? n + 1 : 1;
                    }
                }
                Console.WriteLine($"bucket entries inside their cluster: {inside}, outside: {outside}; instances listed by more than one cluster: {bucketsOf.Count(kv => kv.Value > 1)}");
                foreach (var e in oex) Console.WriteLine("  " + e);
                foreach (var e in ex) Console.WriteLine("  " + e);
            }
            return 0;
        }
    }
}
