// shaderprobe <stock 360 map> <shader name.group>: dump a stock Halo 3 render method's postprocess layout (TagTool Gen3)
using System;
using System.IO;
using System.Linq;
using TagTool.Cache;
using TagTool.Tags.Definitions;

namespace Ho2H3
{
    static class ShaderProbe
    {
        public static int Run(string[] a)
        {
            var cache = GameCache.Open(new FileInfo(a[1]));
            Console.WriteLine($"{cache.GetType().Name} {cache.Version} {cache.Platform}");
            using (var s = cache.OpenCacheRead())
            {
                // "tmpl:<template suffix>": the shaders using that template (up to 3)
                bool byTemplate = a.Length > 2 && a[2].StartsWith("tmpl:");
                var tags = byTemplate
                    ? cache.TagCache.NonNull().Where(t => t.IsInGroup("rmsh")).Where(t => { try { var r = (RenderMethod)cache.Deserialize(s, t); return r.ShaderProperties.Count > 0 && (r.ShaderProperties[0].Template?.Name ?? "").EndsWith("\\" + a[2].Substring(5)); } catch { return false; } }).Take(3).ToList()
                    : cache.TagCache.NonNull().Where(t => a.Length < 3 ? t.IsInGroup("rmsh") : $"{t.Name}.{t.Group}".Equals(a[2], StringComparison.OrdinalIgnoreCase)).Take(a.Length < 3 ? 3 : 1).ToList();
                foreach (var tag in tags)
                {
                    var rm = (RenderMethod)cache.Deserialize(s, tag);
                    var p = rm.ShaderProperties[0];
                    var t2 = cache.Deserialize<RenderMethodTemplate>(s, p.Template);
                    Console.WriteLine($"== {tag.Name}.{tag.Group}  template {p.Template.Name}  rmdf {rm.BaseRenderMethod?.Name} options [{string.Join(",", rm.Options.Select(o => o.OptionIndex))}]");
                    Console.WriteLine($"  textures {p.TextureConstants.Count}/{t2.TextureParameterNames.Count} reals {p.RealConstants.Count}/{t2.RealParameterNames.Count} ints {p.IntegerConstants.Count}/{t2.IntegerParameterNames.Count} bools {t2.BooleanParameterNames.Count} = 0x{p.BooleanConstants:X}");
                    Console.WriteLine($"  entry {p.EntryPoints.Count} (template {t2.EntryPoints.Count}) passes {p.Passes.Count} routing {p.RoutingInfo.Count} functions {p.Functions.Count} blend {p.BlendMode} flags {p.Flags} query [{string.Join(",", p.QueryableProperties ?? new short[0])}]");
                    for (int i = 0; i < p.TextureConstants.Count; i++) { var c = p.TextureConstants[i]; Console.WriteLine($"  tex {cache.StringTable.GetString(t2.TextureParameterNames[i].Name)} = {c.Bitmap?.Name} xf {c.TextureTransformConstantIndex} filt {c.FilterMode} ext {c.ExternTextureMode}"); }
                    for (int i = 0; i < p.RealConstants.Count; i++) { var c = p.RealConstants[i]; Console.WriteLine($"  real {cache.StringTable.GetString(t2.RealParameterNames[i].Name)} = {c.Arg0} {c.Arg1} {c.Arg2} {c.Arg3}"); }
                    for (int i = 0; i < p.EntryPoints.Count; i++) Console.Write($" e{i}:{p.EntryPoints[i].Offset}+{p.EntryPoints[i].Count}"); Console.WriteLine();
                }
            }
            return 0;
        }
    }
}
