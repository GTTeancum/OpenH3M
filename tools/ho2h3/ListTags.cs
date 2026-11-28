// tags <360 map> <group>: tag names of one group (TagTool Gen3)
using System; using System.IO; using System.Linq; using TagTool.Cache;
namespace Ho2H3 { static class ListTags { public static int Run(string[] a) { var c = a[1].EndsWith(".pak", StringComparison.OrdinalIgnoreCase) || a[1].EndsWith(".dat", StringComparison.OrdinalIgnoreCase) ? Program.OpenPak(a[1]) : GameCache.Open(new FileInfo(a[1])); foreach (var t in c.TagCache.NonNull().Where(t => t.IsInGroup(a[2]))) Console.WriteLine(t.Name); return 0; } } }
