// pakread list <pak> [name filter]          tags the package itself contains (not base-cache references)
// pakread dump <pak> <tag index hex> [depth] [max elements]   field dump of one package-owned tag (TagTool definitions)
using System; using System.Collections; using System.IO; using System.Linq; using System.Reflection;
using TagTool.Cache; using TagTool.Cache.HaloOnline;

var pak = new FileInfo(args[1]);
var cache = new GameCacheModPackage(null, pak, true);
if (args[0] == "list")
{
    var filter = args.Length > 2 ? args[2] : ""; int n = 0;
    foreach (var t in cache.TagCache.NonNull())
    {
        var name = t.Name ?? "";
        if (!name.Contains(filter, StringComparison.OrdinalIgnoreCase)) continue;
        if (t is CachedTagHaloOnline h && !h.IsEmpty()) { Console.WriteLine($"0x{t.Index:X4} {name}.{t.Group}"); n++; }
    }
    Console.WriteLine($"{n} tags");
    return 0;
}
if (args[0] == "dump")
{
    int idx = Convert.ToInt32(args[2], 16); int depth = args.Length > 3 ? int.Parse(args[3]) : 3; int maxEl = args.Length > 4 ? int.Parse(args[4]) : 3;
    var tag = cache.TagCache.GetTag(idx);
    using var stream = cache.OpenCacheRead(new MemoryStream());
    var def = cache.Deserialize(stream, tag);
    Console.WriteLine($"{tag.Name}.{tag.Group}");
    Dump(def, "", 0);
    void Dump(object o, string path, int d)
    {
        if (o == null) { Console.WriteLine($"{path} = null"); return; }
        var t = o.GetType();
        if (t.IsPrimitive || t.IsEnum || o is string || t.Namespace == "TagTool.Common" && !(o is IList))
        { Console.WriteLine($"{path} = {Fmt(o)}"); return; }
        if (o is CachedTag ct) { Console.WriteLine($"{path} = {ct.Name}.{ct.Group}"); return; }
        if (o is byte[] ba) { Console.WriteLine($"{path} = ({ba.Length}) {BitConverter.ToString(ba, 0, Math.Min(48, ba.Length)).Replace("-", "")}"); return; }
        if (o is IList list)
        {
            Console.WriteLine($"{path} [{list.Count}]");
            if (d >= depth) return;
            for (int i = 0; i < list.Count && i < maxEl; i++) Dump(list[i], $"{path}[{i}]", d + 1);
            return;
        }
        if (d >= depth) { Console.WriteLine($"{path} = <{t.Name}>"); return; }
        foreach (var f in t.GetFields(BindingFlags.Public | BindingFlags.Instance))
        {
            object v; try { v = f.GetValue(o); } catch { continue; }
            Dump(v, path + "/" + f.Name, d + 1);
        }
    }
    string Fmt(object o) => o is float fl ? fl.ToString("G6") : o.ToString();
    return 0;
}
return 1;
