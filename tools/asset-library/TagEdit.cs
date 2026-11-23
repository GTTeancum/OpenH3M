// Official H3EK ManagedBlam automation for the asset library. No tag serializer.
// Build: csc /platform:x64 /highentropyva- (ManagedBlam asserts on >4 GB addresses).
// Always launch through hidden_run.py (private desktop).
// Usage: TagEdit.exe <kit> <plan.json>
// Plan: {"ops":[{...}]} with op one of:
//   dump  {tag, out}                 recursive field dump (path<TAB>type<TAB>value) to file
//   copy  {from, to}                 file copy of an existing tag to a new allowed path (fails if exists unless overwrite)
//   new   {tag}                      create empty tag of the extension's group
//   set   {tag, field, value}        set a field by ManagedBlam path (Struct:/Block:[i]/name)
//   add   {tag, block, count}        append elements to a block
//   clear {tag, block}               remove all elements from a block
//   remove {tag, block, index}
//   duplicate {tag, block, index}   append a copy of an element (ManagedBlam DuplicateElement)
// Writes are confined to the allowed roots below.
using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using Bungie;
using Bungie.Tags;

class TagEdit
{
    static readonly string[] Allowed = {
        @"objects\weapons\pistol\ce_magnum\",
        @"objects\weapons\rifle\reach_dmr\",
        @"objects\vehicles\reach_falcon\",
        @"objects\vehicles\reach_revenant\",
        @"levels\test\asset_library_test\",
    };
    static string Kit;
    static void Check(string rel)
    {
        var r = rel.ToLowerInvariant();
        if (r.Contains("..") || !Allowed.Any(a => r.StartsWith(a)))
            throw new InvalidOperationException("Write outside asset-library roots refused: " + rel);
    }
    static TagPath TP(string rel)
    {
        var ext = Path.GetExtension(rel).TrimStart('.');
        return TagPath.FromPathAndExtension(rel.Substring(0, rel.Length - ext.Length - 1), ext);
    }
    static string Value(TagField f)
    {
        try
        {
            if (f is TagFieldReference) { var p = ((TagFieldReference)f).Path; return p == null ? "" : p.RelativePathWithExtension; }
            if (f is TagFieldEnum) { var e = (TagFieldEnum)f; return e.Value + ":" + (e.Value >= 0 && e.Value < e.Items.Length ? e.Items[e.Value].EnumName : ""); }
            if (f is TagFieldFlags) { var fl = (TagFieldFlags)f; return string.Join("|", fl.Items.Where(i => fl.TestBit(i.FlagName)).Select(i => i.FlagName)); }
            if (f is TagFieldBlockIndex) return ((TagFieldBlockIndex)f).Value.ToString();
            if (f is TagFieldElementArray) return string.Join(",", ((TagFieldElementArray)f).GetStringData());
            if (f is TagFieldElement) return ((TagFieldElement)f).GetStringData();
        }
        catch (Exception ex) { return "<" + ex.GetType().Name + ">"; }
        return "";
    }
    static void Dump(IEnumerable<TagField> fields, string prefix, StringBuilder sb)
    {
        foreach (var f in fields)
        {
            if (f is TagFieldExplanation || f is TagFieldCustom) continue;
            var name = f.FieldName;
            if (f is TagFieldBlock)
            {
                var b = (TagFieldBlock)f;
                sb.AppendLine(prefix + "Block:" + name + "\tblock\t" + b.Elements.Count);
                for (int i = 0; i < b.Elements.Count; i++) Dump(b.Elements[i].Fields, prefix + "Block:" + name + "[" + i + "]/", sb);
            }
            else if (f is TagFieldStruct)
            {
                var s = (TagFieldStruct)f;
                for (int i = 0; i < s.Elements.Count; i++) Dump(s.Elements[i].Fields, prefix + "Struct:" + name + "[" + i + "]/", sb);
            }
            else if (f is TagFieldArray)
            {
                var a = (TagFieldArray)f;
                for (int i = 0; i < a.Elements.Count; i++) Dump(a.Elements[i].Fields, prefix + "Array:" + name + "[" + i + "]/", sb);
            }
            else sb.AppendLine(prefix + name + "\t" + f.GetType().Name.Replace("TagField", "") + "\t" + Value(f));
        }
    }
    static void Set(TagField f, string v)
    {
        if (f is TagFieldReference)
        {
            ((TagFieldReference)f).Path = string.IsNullOrEmpty(v) ? null : TP(v);
        }
        else if (f is TagFieldEnum)
        {
            var e = (TagFieldEnum)f; int n;
            if (int.TryParse(v, out n)) e.Value = n;
            else { var it = e.Items.FirstOrDefault(i => i.EnumName == v); if (it == null) throw new ArgumentException("enum " + v); e.Value = it.EnumIndex; }
        }
        else if (f is TagFieldFlags)
        {
            var fl = (TagFieldFlags)f; var want = new HashSet<string>(v.Split(new[] { '|' }, StringSplitOptions.RemoveEmptyEntries));
            foreach (var w in want) if (!fl.Items.Any(i => i.FlagName == w)) throw new ArgumentException("flag " + w);
            foreach (var i in fl.Items) fl.SetBit(i.FlagName, want.Contains(i.FlagName));
        }
        else if (f is TagFieldBlockIndex) ((TagFieldBlockIndex)f).Value = int.Parse(v);
        else if (f is TagFieldElementArray) { if (!((TagFieldElementArray)f).SetStringData(v.Split(','))) throw new ArgumentException("array rejected " + v); }
        else if (f is TagFieldElement) { if (!((TagFieldElement)f).SetStringData(v)) throw new ArgumentException("SetStringData rejected " + v); }
        else throw new ArgumentException("unsupported field type " + f.GetType().Name);
    }
    // SelectField returns the first field with a name; explanations can share names with real fields.
    static TagField Resolve(TagFile t, string path)
    {
        var f = t.SelectField(path);
        if (!(f is TagFieldExplanation) && !(f is TagFieldCustom)) return f;
        string name = f.FieldName;
        IEnumerable<TagField> siblings = f.GetParentElement().Fields;
        foreach (var c in siblings)
            if (c.FieldName == name && !(c is TagFieldExplanation) && !(c is TagFieldCustom)) return c;
        throw new ArgumentException("no value field named " + name);
    }
    static int Main(string[] args)
    {
        Kit = Path.GetFullPath(args[0]);
        var plan = new JavaScriptSerializer().Deserialize<Dictionary<string, object>>(File.ReadAllText(args[1]));
        Directory.SetCurrentDirectory(Kit);
        ManagedBlamSystem.InitializeProject(InitializationType.TagsOnly, Kit);
        var tags = Path.Combine(Kit, "tags");
        var open = new Dictionary<string, TagFile>(StringComparer.OrdinalIgnoreCase);
        Func<string, TagFile> get = rel =>
        {
            TagFile t;
            if (!open.TryGetValue(rel, out t)) { t = new TagFile(TP(rel)); open[rel] = t; }
            return t;
        };
        int n = 0;
        foreach (Dictionary<string, object> op in (System.Collections.ArrayList)plan["ops"])
        {
            var kind = (string)op["op"];
            Func<string, string> S = k => op.ContainsKey(k) ? Convert.ToString(op[k], System.Globalization.CultureInfo.InvariantCulture) : null;
            try
            {
                switch (kind)
                {
                    case "dump":
                        {
                            var sb = new StringBuilder(); Dump(get(S("tag")).Fields, "", sb);
                            File.WriteAllText(S("out"), sb.ToString()); break;
                        }
                    case "copy":
                        {
                            Check(S("to"));
                            var dst = Path.Combine(tags, S("to"));
                            if (File.Exists(dst) && S("overwrite") != "True") throw new IOException("exists: " + S("to"));
                            Directory.CreateDirectory(Path.GetDirectoryName(dst));
                            File.Copy(Path.Combine(tags, S("from")), dst, true); break;
                        }
                    case "new":
                        {
                            Check(S("tag"));
                            if (File.Exists(Path.Combine(tags, S("tag")))) throw new IOException("exists: " + S("tag"));
                            var t = new TagFile(); t.New(TP(S("tag"))); open[S("tag")] = t; break;
                        }
                    case "set":
                        Check(S("tag")); Set(Resolve(get(S("tag")), S("field")), S("value")); break;
                    case "add":
                        {
                            Check(S("tag")); var b = (TagFieldBlock)get(S("tag")).SelectField(S("block"));
                            int c = op.ContainsKey("count") ? Convert.ToInt32(op["count"]) : 1;
                            for (int i = 0; i < c; i++) b.AddElement(); break;
                        }
                    case "listflags":
                        {
                            var fl = (TagFieldFlags)Resolve(get(S("tag")), S("field"));
                            File.WriteAllText(S("out"), string.Join(Environment.NewLine, fl.Items.Select(i => i.FlagIndex + " " + i.FlagName + " " + (fl.TestBit(i.FlagName) ? "SET" : "")))); break;
                        }
                    case "duplicate":
                        Check(S("tag")); ((TagFieldBlock)get(S("tag")).SelectField(S("block"))).DuplicateElement(Convert.ToInt32(op["index"])); break;
                    case "clear":
                        Check(S("tag")); ((TagFieldBlock)get(S("tag")).SelectField(S("block"))).RemoveAllElements(); break;
                    case "remove":
                        Check(S("tag")); ((TagFieldBlock)get(S("tag")).SelectField(S("block"))).RemoveElement(Convert.ToInt32(op["index"])); break;
                    default: throw new ArgumentException("op " + kind);
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine("OP_FAILED " + n + " " + kind + " " + S("tag") + " " + S("field") + " : " + ex.Message);
                foreach (var t in open.Values) t.Dispose();
                return 2;
            }
            n++;
        }
        foreach (var kv in open)
        {
            if (Allowed.Any(a => kv.Key.ToLowerInvariant().StartsWith(a))) kv.Value.Save();
            kv.Value.Dispose();
        }
        Console.WriteLine("TAGEDIT_OK " + n + " ops");
        return 0;
    }
}
