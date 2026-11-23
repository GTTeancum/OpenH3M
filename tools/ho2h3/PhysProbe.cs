// physprobe <pak> <sbsp name>: Halo Online instance definitions: collision surfaces vs Reach-style polyhedra (ExtraData),
// with the names of instances that use each definition
using System;
using System.IO;
using System.Linq;
using TagTool.Cache;
using TagTool.Tags.Definitions;

namespace Ho2H3
{
    static class PhysProbe
    {
        public static int Run(string[] a)
        {
            var ho = (GameCacheModPackage)Program.OpenPak(a[1]);
            using (var s = ho.OpenCacheRead(new MemoryStream()))
            {
                var t = ho.TagCache.GetTag(a[2], "sbsp"); var bsp = ho.Deserialize<ScenarioStructureBsp>(s, t);
                var r = ho.ResourceCache.GetStructureBspTagResources(bsp.CollisionBspResource);
                int both = 0, polyOnly = 0, collOnly = 0, none = 0;
                for (int d = 0; d < r.InstancedGeometry.Count; d++)
                {
                    var ig = r.InstancedGeometry[d]; int surf = ig.CollisionInfo?.Surfaces?.Count ?? 0; int poly = ig.ExtraData?.Sum(e => e.Polyhedra?.Count ?? 0) ?? 0;
                    if (surf > 0 && poly > 0) both++; else if (poly > 0) polyOnly++; else if (surf > 0) collOnly++; else none++;
                    if (surf == 0 && (poly > 0 || a.Length > 3))
                    {
                        var users = bsp.InstancedGeometryInstances.Where(x => x.DefinitionIndex == d).ToList();
                        Console.WriteLine($"def {d}: surfaces {surf} polyhedra {poly} mesh {ig.MeshIndex} instances {users.Count} e.g. {(users.Count > 0 ? ho.StringTable.GetString(users[0].Name) : "-")} flags {(users.Count > 0 ? users[0].Flags.ToString() : "")}");
                    }
                }
                Console.WriteLine($"definitions {r.InstancedGeometry.Count}: collision+polyhedra {both}, polyhedra only {polyOnly}, collision only {collOnly}, neither {none}");
            }
            return 0;
        }
    }
}
