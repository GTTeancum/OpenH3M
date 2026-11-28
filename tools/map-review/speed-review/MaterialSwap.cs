// Official H3EK ManagedBlam automation: set a material tag's render-method options.
// Build: csc /platform:x64 /highentropyva- /reference:ManagedBlam.dll /reference:System.Web.Extensions.dll MaterialSwap.cs
// (ManagedBlam asserts on addresses above 4 GB.) Always run on a hidden desktop.
// Usage:
//   MaterialSwap.exe <kit> dump <tag-relative-path-with-extension> <out.txt>
//   MaterialSwap.exe <kit> apply <plan.json>
//      plan: [{"tag": "levels\\...\\x.shader", "options": [0, 2, ...]}]  (one index per category, kit definition order)
// Writes are refused outside the two map roots below.
using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using Bungie;
using Bungie.Tags;

class MaterialSwap
{
    static readonly string[] Allowed = {
        @"levels\test\beavercreek\",
        @"levels\test\elongation\",
        @"levels\multi\s3d_sky_bridgenew\",
        @"objects\levels\multi\s3d_sky_bridgenew\",
        @"levels\multi\s3d_reactor\",
        @"objects\levels\multi\s3d_reactor\",
        @"levels\multi\s3d_turf\shaders\turf_banners_01.shader_halogram",
        @"levels\multi\s3d_turf\shaders\turf_farplane.shader",
        @"levels\multi\s3d_waterfall\shaders\wtf_metal_01.shader",
        @"levels\multi\s3d_waterfall\shaders\lighting\unsc_lightfixtures_01.shader",
        @"levels\solo\s3d_tutorial\shaders\lighting\tut_device_04_glow.shader_halogram",
        @"fx\particles\flare\light_beam_flat_01.particle",
        @"levels\multi\s3d_powerhouse\fx\particles\fluid_spray_xlarge.particle",
        @"fx\particles\atmospheric\snow\snow_nofade.particle",
        @"levels\multi\s3d_sky_bridgenew\fx\spark_01.particle",
        @"fx\particles\vehicle\charger_sparks.particle",
        @"fx\particles\atmospheric\soft_smoke\soft_smoke_large_n3.particle",
        @"levels\multi\s3d_avalanche\shaders\cyber_glass.shader",
        @"levels\multi\s3d_turf\shaders\a10_cryo_base.shader",
        @"levels\ui\mainmenu\shaders\unsc_panel_21.shader",
        @"levels\ui\mainmenu\shaders\d40_hangar_12.shader",
        @"fx\particles\atmospheric\soft_smoke\soft_steam_fast_02.particle",
        @"fx\particles\atmospheric\soft_smoke\soft_steam_fast_01.particle",
        @"fx\particles\atmospheric\soft_smoke\soft_steam_fast.particle",
        @"fx\particles\atmospheric\soft_smoke\soft_steam_large.particle",
        @"fx\particles\material\water\water_spray.particle",
        @"levels\solo\030_outskirts\fx\shaft_fire\particles\shaft_top_rolling_fire.particle",
    };
    static TagPath TP(string rel)
    {
        var ext = Path.GetExtension(rel).TrimStart('.');
        return TagPath.FromPathAndExtension(rel.Substring(0, rel.Length - ext.Length - 1), ext);
    }
    static void Dump(IEnumerable<TagField> fields, string prefix, StringBuilder sb, int depth)
    {
        if (depth > (Environment.GetEnvironmentVariable("DUMP_DEPTH") == null ? 3 : int.Parse(Environment.GetEnvironmentVariable("DUMP_DEPTH")))) return;
        foreach (var f in fields)
        {
            if (f is TagFieldExplanation || f is TagFieldCustom) continue;
            if (f is TagFieldBlock)
            {
                var b = (TagFieldBlock)f;
                sb.AppendLine(prefix + "Block:" + f.FieldName + "\t" + b.Elements.Count);
                for (int i = 0; i < Math.Min(b.Elements.Count, 16); i++) Dump(b.Elements[i].Fields, prefix + "Block:" + f.FieldName + "[" + i + "]/", sb, depth + 1);
            }
            else if (f is TagFieldStruct)
            {
                var s = (TagFieldStruct)f;
                for (int i = 0; i < s.Elements.Count; i++) Dump(s.Elements[i].Fields, prefix + "Struct:" + f.FieldName + "[" + i + "]/", sb, depth + 1);
            }
            else
            {
                string v = "";
                try
                {
                    if (f is TagFieldReference) { var p = ((TagFieldReference)f).Path; v = p == null ? "" : p.RelativePathWithExtension; }
                    else if (f is TagFieldData) v = BitConverter.ToString(((TagFieldData)f).GetData());
                    else if (f is TagFieldEnum) { var e = (TagFieldEnum)f; v = e.Value + ":" + (e.Value >= 0 && e.Value < e.Items.Length ? e.Items[e.Value].EnumName : "") + "  [" + string.Join("|", e.Items.Select((it, i) => i + "=" + it.EnumName)) + "]"; }
                    else if (f is TagFieldElement) v = ((TagFieldElement)f).GetStringData();
                }
                catch (Exception ex) { v = "<" + ex.GetType().Name + ">"; }
                sb.AppendLine(prefix + f.FieldName + "\t" + f.GetType().Name + "\t" + v);
            }
        }
    }
    static void ExportPixels(string rel, string outPath)
    {
                using (var t = new TagFile(TP(rel)))
                {
                    TagFieldStruct root = null;
                    foreach (var f in t.Fields) if (f is TagFieldStruct) { root = (TagFieldStruct)f; break; }
                    IEnumerable<TagField> fields = root != null ? root.Elements[0].Fields : t.Fields;
                    var all = fields.ToList();
                    if (!all.Any(f => f.FieldName == "processed pixel data")) all = t.Fields.ToList();
                    var data = (TagFieldData)all.First(f => f.FieldName == "processed pixel data");
                    File.WriteAllBytes(outPath, data.GetData());
                    var sb = new StringBuilder("{");
                    foreach (var f in all)
                    {
                        if (f is TagFieldEnum) { var e = (TagFieldEnum)f; sb.Append("\"" + f.FieldName + "\":\"" + e.Value + ":" + (e.Value >= 0 && e.Value < e.Items.Length ? e.Items[e.Value].EnumName : "") + "\","); }
                        else if (f is TagFieldElementInteger) sb.Append("\"" + f.FieldName + "\":" + ((TagFieldElement)f).GetStringData() + ",");
                    }
                    var imgs = (TagFieldBlock)all.First(f => f.FieldName == "bitmaps");
                    sb.Append("\"images\":[");
                    for (int i = 0; i < imgs.Elements.Count; i++)
                    {
                        sb.Append("{");
                        foreach (var f in imgs.Elements[i].Fields)
                        {
                            if (f is TagFieldEnum) { var e = (TagFieldEnum)f; sb.Append("\"" + f.FieldName + "\":\"" + e.Value + ":" + (e.Value >= 0 && e.Value < e.Items.Length ? e.Items[e.Value].EnumName : "") + "\","); }
                            else if (f is TagFieldElementInteger) sb.Append("\"" + f.FieldName + "\":" + ((TagFieldElement)f).GetStringData() + ",");
                            else if (f is TagFieldFlags) { var fl = (TagFieldFlags)f; sb.Append("\"" + f.FieldName + "\":\"" + string.Join("|", fl.Items.Where(x => fl.TestBit(x.FlagName)).Select(x => x.FlagName)) + "\","); }
                        }
                        sb.Append("\"_\":0}" + (i + 1 < imgs.Elements.Count ? "," : ""));
                    }
                    sb.Append("]}");
                    File.WriteAllText(outPath + ".json", sb.ToString());
                    Console.WriteLine("EXPORT_OK " + data.GetData().Length);
                }
                }
    static TagFieldBlock OptionsBlock(TagFile t)
    {
        foreach (var f in t.Fields)
        {
            if (f is TagFieldBlock && f.FieldName.ToLowerInvariant() == "options") return (TagFieldBlock)f;
            if (f is TagFieldStruct && (f.FieldName == "render_method" || f.FieldName.StartsWith("actual shader")))
                foreach (var g in ((TagFieldStruct)f).Elements[0].Fields)
                    if (g is TagFieldBlock && g.FieldName.ToLowerInvariant() == "options") return (TagFieldBlock)g;
        }
        throw new InvalidOperationException("no render_method options block");
    }
    static int Main(string[] args)
    {
        var kit = Path.GetFullPath(args[0]);
        ManagedBlamSystem.InitializeProject(InitializationType.TagsOnly, kit);
        try
        {
            if (args[1] == "dump")
            {
                using (var t = new TagFile(TP(args[2])))
                {
                    var sb = new StringBuilder(); Dump(t.Fields, "", sb, 0); File.WriteAllText(args[3], sb.ToString());
                }
            }
            else if (args[1] == "empty-placements")
            {
                // List (and with "remove", delete) placements whose palette type is unset (-1). The game skips them.
                var rel = args[2]; var low = rel.ToLowerInvariant();
                bool remove = args.Length > 3 && args[3] == "remove";
                if (remove && (low.Contains("..") || !Allowed.Any(a => low.StartsWith(a)))) throw new InvalidOperationException("refused: " + rel);
                using (var t = new TagFile(TP(rel)))
                {
                    int removed = 0;
                    foreach (var f in t.Fields)
                    {
                        var b = f as TagFieldBlock; if (b == null) continue;
                        for (int i = b.Elements.Count - 1; i >= 0; i--)
                        {
                            var type = b.Elements[i].Fields.FirstOrDefault(x => x.FieldName == "type") as TagFieldBlockIndex;
                            if (type == null || type.Value != -1) continue;
                            Console.WriteLine("EMPTY " + f.FieldName + "[" + i + "]");
                            if (remove) { b.RemoveElement(i); removed++; }
                        }
                    }
                    if (remove && removed > 0) t.Save();
                    Console.WriteLine("EMPTY_OK " + removed);
                }
            }
            else if (args[1] == "drop-palette")
            {
                // drop-palette <tag> <palette block> <placement block> <path substring>...
                // Removes placements of the matching palette entries, then the entries themselves.
                // Refuses unless the matching entries are the last ones (no renumbering of others).
                var rel = args[2]; var low = rel.ToLowerInvariant();
                if (low.Contains("..") || !Allowed.Any(a => low.StartsWith(a))) throw new InvalidOperationException("refused: " + rel);
                var subs = args.Skip(5).Select(x => x.ToLowerInvariant()).ToList();
                using (var t = new TagFile(TP(rel)))
                {
                    var pal = t.Fields.OfType<TagFieldBlock>().First(b => b.FieldName == args[3]);
                    var plc = t.Fields.OfType<TagFieldBlock>().FirstOrDefault(b => b.FieldName == args[4]);
                    var drop = new List<int>();
                    for (int i = 0; i < pal.Elements.Count; i++)
                    {
                        var r = pal.Elements[i].Fields.OfType<TagFieldReference>().First();
                        var path = r.Path == null ? "" : r.Path.RelativePathWithExtension.ToLowerInvariant();
                        if (subs.Any(x => path.Contains(x))) drop.Add(i);
                    }
                    if (drop.Count == 0) { Console.WriteLine("DROP_OK 0 0"); return 0; }
                    if (drop.Min() != pal.Elements.Count - drop.Count || drop.Max() != pal.Elements.Count - 1) throw new InvalidOperationException("matching entries are not the last ones; refusing to renumber");
                    int placed = 0;
                    if (plc != null)
                        for (int i = plc.Elements.Count - 1; i >= 0; i--)
                        {
                            var type = (TagFieldBlockIndex)plc.Elements[i].Fields.First(x => x.FieldName == "type");
                            if (drop.Contains((int)type.Value)) { plc.RemoveElement(i); placed++; }
                        }
                    for (int k = drop.Count - 1; k >= 0; k--) pal.RemoveElement(drop[k]);
                    t.Save();
                    Console.WriteLine("DROP_OK " + drop.Count + " " + placed);
                }
            }
            else if (args[1] == "export-pixels-list")
            {
                // export-pixels-list <list.txt> <outdir>: export-pixels for each tag path in the list (one per line).
                foreach (var line in File.ReadAllLines(args[2]).Where(x => x.Trim().Length > 0))
                {
                    var rel = line.Trim();
                    var outp = Path.Combine(args[3], rel.Replace((char)92, (char)126) + ".bin");
                    try { ExportPixels(rel, outp); Console.WriteLine("EXPORTED " + rel); }
                    catch (Exception ex) { Console.WriteLine("FAILED " + rel + " " + ex.GetType().Name + ": " + ex.Message); }
                }
                Console.WriteLine("EXPORT_LIST_OK");
            }
            else if (args[1] == "export-pixels")
            {
                ExportPixels(args[2], args[3]);
            }
            else if (args[1] == "set-enum")
            {
                // set-enum <tag> <top-level field name> <index>   (inside the tag's first struct when present)
                var rel = args[2]; var low = rel.ToLowerInvariant();
                using (var t = new TagFile(TP(rel)))
                {
                    TagFieldStruct root = t.Fields.OfType<TagFieldStruct>().FirstOrDefault();
                    var all = (root != null ? root.Elements[0].Fields : t.Fields).ToList();
                    var e = (TagFieldEnum)all.Concat(t.Fields).First(f => f.FieldName == args[3] && f is TagFieldEnum);
                    var before = e.Value; e.Value = int.Parse(args[4]); t.Save();
                    Console.WriteLine("SET_ENUM " + args[3] + " " + before + " -> " + e.Value);
                }
            }
            else if (args[1] == "set-real-param")
            {
                // set-real-param <material tag> <parameter name> <value>: add (or update) a real-valued material parameter.
                var rel = args[2]; var low = rel.ToLowerInvariant();
                if (low.Contains("..") || !Allowed.Any(a => low.StartsWith(a))) throw new InvalidOperationException("refused: " + rel);
                using (var t = new TagFile(TP(rel)))
                {
                    TagFieldBlock pars = null;
                    foreach (var f in t.Fields)
                        if (f is TagFieldStruct && f.FieldName == "render_method")
                            pars = ((TagFieldStruct)f).Elements[0].Fields.OfType<TagFieldBlock>().First(b => b.FieldName == "parameters");
                    if (pars == null) throw new InvalidOperationException("no parameters block");
                    TagElement el = null;
                    foreach (var e in pars.Elements)
                        if (((TagFieldElement)e.Fields.First(x => x.FieldName == "parameter name")).GetStringData() == args[3]) el = e;
                    if (el == null) { pars.AddElement(); el = pars.Elements[pars.Elements.Count - 1]; ((TagFieldElement)el.Fields.First(x => x.FieldName == "parameter name")).SetStringData(args[3]); }
                    var type = (TagFieldEnum)el.Fields.First(x => x.FieldName == "parameter type");
                    type.Value = Array.FindIndex(type.Items, i => i.EnumName.ToLowerInvariant() == "real");
                    ((TagFieldElement)el.Fields.First(x => x.FieldName == "real")).SetStringData(args[4]);
                    var anim = el.Fields.OfType<TagFieldBlock>().FirstOrDefault(b => b.FieldName == "animated parameters");
                    if (anim != null && anim.Elements.Count > 0)
                    {
                        if (args.Length > 5 && args[5] == "clear-animation") { while (anim.Elements.Count > 0) anim.RemoveElement(0); Console.WriteLine("cleared animated values"); }
                        else Console.WriteLine("note: parameter already has animated values");
                    }
                    t.Save();
                    Console.WriteLine("SET_PARAM " + rel + " " + args[3] + " = " + args[4] + " (type index " + type.Value + ")");
                }
            }
            else if (args[1] == "remove-placements")
            {
                // remove-placements <tag> <placement block> <palette block> <all|outside|list> <x0,y0,z0,x1,y1,z1> <substr...>
                // Removes placements whose palette path contains a substring ("outside": only those outside the box).
                // "list" removes nothing and prints each matching placement with its name index and position.
                var rel = args[2]; var low = rel.ToLowerInvariant(); var mode = args[5];
                if (mode != "list" && (low.Contains("..") || !Allowed.Any(a => low.StartsWith(a)))) throw new InvalidOperationException("refused: " + rel);
                var box = args[6].Split(',').Select(x => double.Parse(x, System.Globalization.CultureInfo.InvariantCulture)).ToArray();
                var subs = args.Skip(7).Select(x => x.ToLowerInvariant()).ToList();
                using (var t = new TagFile(TP(rel)))
                {
                    var pal = t.Fields.OfType<TagFieldBlock>().First(b => b.FieldName == args[4]);
                    var plc = t.Fields.OfType<TagFieldBlock>().First(b => b.FieldName == args[3]);
                    var match = new HashSet<int>();
                    for (int i = 0; i < pal.Elements.Count; i++)
                    {
                        var r = pal.Elements[i].Fields.OfType<TagFieldReference>().First();
                        var path = r.Path == null ? "" : r.Path.RelativePathWithExtension.ToLowerInvariant();
                        if (subs.Any(x => path.Contains(x))) match.Add(i);
                    }
                    int removed = 0;
                    for (int i = plc.Elements.Count - 1; i >= 0; i--)
                    {
                        var el = plc.Elements[i];
                        var type = (TagFieldBlockIndex)el.Fields.First(x => x.FieldName == "type");
                        if (!match.Contains((int)type.Value)) continue;
                        var od = el.Fields.OfType<TagFieldStruct>().First(x => x.FieldName == "object data");
                        var posf = (TagFieldElementArraySingle)od.Elements[0].Fields.First(x => x.FieldName == "position");
                        var p = posf.Data;
                        bool outside = p[0] < box[0] || p[1] < box[1] || p[2] < box[2] || p[0] > box[3] || p[1] > box[4] || p[2] > box[5];
                        var nameIdx = ((TagFieldBlockIndex)el.Fields.First(x => x.FieldName == "name")).Value;
                        Console.WriteLine("MATCH " + args[3] + "[" + i + "] name=" + nameIdx + " pos=" + string.Join(",", p.Select(v => v.ToString("0.0", System.Globalization.CultureInfo.InvariantCulture))) + (outside ? " outside" : " inside"));
                        if (mode == "all" || (mode == "outside" && outside)) { plc.RemoveElement(i); removed++; }
                    }
                    if (removed > 0) t.Save();
                    Console.WriteLine("REMOVED " + removed);
                }
            }
            else if (args[1] == "get-data")
            {
                // get-data <tag> <top-level data field> <out file>
                using (var t = new TagFile(TP(args[2])))
                {
                    var d = (TagFieldData)t.Fields.First(f => f.FieldName == args[3] && f is TagFieldData);
                    File.WriteAllBytes(args[4], d.GetData()); Console.WriteLine("GOT " + d.GetData().Length);
                }
            }
            else if (args[1] == "set-data")
            {
                // set-data <tag> <top-level data field> <in file> [clear-block-name]
                var rel = args[2]; var low = rel.ToLowerInvariant();
                if (low.Contains("..") || !Allowed.Any(a => low.StartsWith(a))) throw new InvalidOperationException("refused: " + rel);
                using (var t = new TagFile(TP(rel)))
                {
                    var d = (TagFieldData)t.Fields.First(f => f.FieldName == args[3] && f is TagFieldData);
                    d.SetData(File.ReadAllBytes(args[4]));
                    if (args.Length > 5) { var b = t.Fields.OfType<TagFieldBlock>().First(x => x.FieldName == args[5]); while (b.Elements.Count > 0) b.RemoveElement(0); }
                    t.Save(); Console.WriteLine("SET_DATA " + d.GetData().Length);
                }
            }
            else if (args[1] == "build-shader")
            {
                // build-shader <plan.json>: create (or overwrite) material tags. Each entry:
                // {tag, definition, options:[...], params:[{name, bitmap?, real?, color?:[r,g,b], scale_x?, scale_y?}]}
                // Values are written as constant functions in the same layout stock Halo 3 tags use
                // (header 01 20, value float at byte 4; colours as B,G,R,0 at bytes 4 and 16).
                var plan = new JavaScriptSerializer { MaxJsonLength = int.MaxValue }.Deserialize<List<Dictionary<string, object>>>(File.ReadAllText(args[2]));
                foreach (var e in plan)
                {
                    var rel = (string)e["tag"]; var low = rel.ToLowerInvariant();
                    if (low.Contains("..") || !low.StartsWith(@"levels\test\tombstone\") && !low.StartsWith(@"levels\test\beavercreek\") && !low.StartsWith(@"levels\test\elongation\")) throw new InvalidOperationException("refused: " + rel);
                    var t = new TagFile();
                    if (File.Exists(Path.Combine(kit, "tags", rel))) t.Load(TP(rel)); else t.New(TP(rel));
                    using (t)
                    {
                        var rm = t.Fields.OfType<TagFieldStruct>().First(f => f.FieldName == "render_method").Elements[0].Fields;
                        ((TagFieldReference)rm.First(f => f.FieldName == "definition")).Path = TP((string)e["definition"]);
                        var opts = (TagFieldBlock)rm.First(f => f is TagFieldBlock && f.FieldName == "options");
                        while (opts.Elements.Count > 0) opts.RemoveElement(0);
                        foreach (var o in ((System.Collections.ArrayList)e["options"]).Cast<object>())
                        { opts.AddElement(); ((TagFieldElement)opts.Elements[opts.Elements.Count - 1].Fields.First(x => x is TagFieldElement)).SetStringData(Convert.ToInt32(o).ToString()); }
                        var pars = (TagFieldBlock)rm.First(f => f is TagFieldBlock && f.FieldName == "parameters");
                        while (pars.Elements.Count > 0) pars.RemoveElement(0);
                        foreach (Dictionary<string, object> p in (System.Collections.ArrayList)e["params"])
                        {
                            pars.AddElement(); var el = pars.Elements[pars.Elements.Count - 1];
                            ((TagFieldElement)el.Fields.First(x => x.FieldName == "parameter name")).SetStringData((string)p["name"]);
                            var type = (TagFieldEnum)el.Fields.First(x => x.FieldName == "parameter type");
                            var anim = el.Fields.OfType<TagFieldBlock>().First(b => b.FieldName == "animated parameters");
                            Action<int, byte[]> addAnim = (kind, data) =>
                            {
                                anim.AddElement(); var a = anim.Elements[anim.Elements.Count - 1];
                                ((TagFieldEnum)a.Fields.First(x => x.FieldName == "type")).Value = kind;
                                var fn = a.Fields.OfType<TagFieldStruct>().First(x => x.FieldName == "function").Elements[0].Fields;
                                ((TagFieldData)fn.First(x => x is TagFieldData)).SetData(data);
                            };
                            Func<double, byte[]> constant = v =>
                            { var d = new byte[32]; d[0] = 1; d[1] = 0x20; BitConverter.GetBytes((float)v).CopyTo(d, 4); BitConverter.GetBytes((float)v).CopyTo(d, 8); return d; };
                            if (p.ContainsKey("bitmap"))
                            {
                                type.Value = 0;
                                ((TagFieldReference)el.Fields.First(x => x.FieldName == "bitmap")).Path = TP((string)p["bitmap"]);
                                // texture sampling as stock materials set it (e.g. base/bump maps: flags 1, filter mode 4)
                                if (p.ContainsKey("bitmap_flags")) ((TagFieldElement)el.Fields.First(x => x.FieldName == "bitmap flags")).SetStringData(Convert.ToInt32(p["bitmap_flags"]).ToString());
                                if (p.ContainsKey("filter_mode")) ((TagFieldElement)el.Fields.First(x => x.FieldName == "bitmap filter mode")).SetStringData(Convert.ToInt32(p["filter_mode"]).ToString());
                                if (p.ContainsKey("scale_x"))
                                {
                                    double sx = Convert.ToDouble(p["scale_x"]), sy = Convert.ToDouble(p.ContainsKey("scale_y") ? p["scale_y"] : p["scale_x"]);
                                    if (sx == sy) addAnim(2, constant(sx)); else { addAnim(3, constant(sx)); addAnim(4, constant(sy)); }
                                }
                                // anim_copy: {from: stock material tag, param, index, type, period}: copy that stock animated
                                // parameter's function bytes exactly, with the given type (5 = translation x) and time period.
                                if (p.ContainsKey("anim_copy"))
                                {
                                    var ac = (Dictionary<string, object>)p["anim_copy"];
                                    byte[] src;
                                    using (var st = new TagFile())
                                    {
                                        st.Load(TP((string)ac["from"]));
                                        var srm = st.Fields.OfType<TagFieldStruct>().First(f => f.FieldName == "render_method").Elements[0].Fields;
                                        var spars = (TagFieldBlock)srm.First(f => f is TagFieldBlock && f.FieldName == "parameters");
                                        var sel = spars.Elements.First(x => ((TagFieldElement)x.Fields.First(y => y.FieldName == "parameter name")).GetStringData() == (string)ac["param"]);
                                        var sanim = sel.Fields.OfType<TagFieldBlock>().First(b => b.FieldName == "animated parameters");
                                        var sa = sanim.Elements[Convert.ToInt32(ac["index"])];
                                        var sfn = sa.Fields.OfType<TagFieldStruct>().First(x => x.FieldName == "function").Elements[0].Fields;
                                        src = ((TagFieldData)sfn.First(x => x is TagFieldData)).GetData();
                                        Console.WriteLine("ANIM_COPY from " + ac["from"] + " " + ac["param"] + " type " + ((TagFieldEnum)sa.Fields.First(x => x.FieldName == "type")).Value
                                            + " period " + ((TagFieldElement)sa.Fields.First(x => x.FieldName == "time period")).GetStringData() + " data " + BitConverter.ToString(src));
                                    }
                                    addAnim(Convert.ToInt32(ac["type"]), src);
                                    var added = anim.Elements[anim.Elements.Count - 1];
                                    ((TagFieldElement)added.Fields.First(x => x.FieldName == "time period")).SetStringData(Convert.ToDouble(ac["period"]).ToString(System.Globalization.CultureInfo.InvariantCulture));
                                }
                            }
                            else if (p.ContainsKey("color"))
                            {
                                type.Value = 1;
                                var c = ((System.Collections.ArrayList)p["color"]).Cast<object>().Select(Convert.ToDouble).ToArray();
                                var d = new byte[32]; d[0] = 1; d[1] = 0x20; d[2] = 2;
                                for (int k = 0; k < 2; k++) { int o = k == 0 ? 4 : 16; d[o] = (byte)Math.Round(255 * c[2]); d[o + 1] = (byte)Math.Round(255 * c[1]); d[o + 2] = (byte)Math.Round(255 * c[0]); }
                                addAnim(1, d);
                            }
                            else
                            {
                                type.Value = 2; var v = Convert.ToDouble(p["real"]);
                                ((TagFieldElement)el.Fields.First(x => x.FieldName == "real")).SetStringData(v.ToString(System.Globalization.CultureInfo.InvariantCulture));
                                addAnim(0, constant(v));
                            }
                        }
                        t.Save();
                        Console.WriteLine("BUILT " + rel + " params " + pars.Elements.Count);
                    }
                }
            }
            else if (args[1] == "apply")
            {
                var plan = new JavaScriptSerializer { MaxJsonLength = int.MaxValue }.Deserialize<List<Dictionary<string, object>>>(File.ReadAllText(args[2]));
                int changed = 0;
                foreach (var e in plan)
                {
                    var rel = (string)e["tag"];
                    var low = rel.ToLowerInvariant();
                    if (low.Contains("..") || !Allowed.Any(a => low.StartsWith(a))) throw new InvalidOperationException("refused: " + rel);
                    var want = ((System.Collections.ArrayList)e["options"]).Cast<object>().Select(Convert.ToInt32).ToList();
                    using (var t = new TagFile(TP(rel)))
                    {
                        var block = OptionsBlock(t);
                        while (block.Elements.Count < want.Count) block.AddElement();
                        var before = new List<string>();
                        for (int i = 0; i < want.Count; i++)
                        {
                            var el = (TagFieldElement)block.Elements[i].Fields.First(x => x is TagFieldElement);
                            before.Add(el.GetStringData());
                            el.SetStringData(want[i].ToString());
                        }
                        t.Save();
                        Console.WriteLine("SET " + rel + " " + string.Join(",", before) + " -> " + string.Join(",", want));
                        changed++;
                    }
                }
                Console.WriteLine("MATERIALSWAP_OK " + changed);
            }
        }
        finally { }
        return 0;
    }
}
