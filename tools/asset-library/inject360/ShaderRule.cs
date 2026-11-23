// Render-method rule (shader, halogram, terrain, ... any tag with Options + Postprocess):
//  * the MCC shader template is replaced by the original 360 template (360 compiled shaders are kept, PC ones dropped);
//  * the shader's option list is cut to the 360 category count;
//  * postprocess textures, float, integer and boolean constants are re-ordered by parameter name onto the 360
//    template; a value the MCC shader lacks comes from the 360 render-method option default.
using System;
using System.Collections.Generic;
using System.Linq;
using Blamite.Blam;
using Blamite.Injection;
using Blamite.Util;

namespace Inject360
{
    public class ShaderRule
    {
        public readonly Dictionary<uint, string> Template = new Dictionary<uint, string>();  // source rmt2 datum -> 360 rmt2 name
        public readonly List<string> Log = new List<string>();
        readonly Func<string, Elem> _dstTag;          // "grp:name" in the 360 map -> tree (null if absent)
        readonly Func<string, bool> _dstHas;
        readonly Func<uint, Elem> _srcTag;            // source datum -> tree
        readonly Func<uint, string> _srcName;
        readonly Func<uint, string> _dstName;         // 360 datum -> name
        readonly Func<string, string, DatumIndex> _synth;   // (group, 360 name) -> container tag index that resolves to it
        readonly List<string> _dstTemplates;

        public ShaderRule(IEnumerable<string> dstTemplateNames, Func<string, Elem> dstTag, Func<string, bool> dstHas,
            Func<uint, Elem> srcTag, Func<uint, string> srcName, Func<uint, string> dstName, Func<string, string, DatumIndex> synth)
        {
            _dstTemplates = dstTemplateNames.ToList(); _dstTag = dstTag; _dstHas = dstHas; _srcTag = srcTag; _srcName = srcName; _dstName = dstName; _synth = synth;
        }

        static int[] Digits(string name) => name.Substring(name.LastIndexOf('\\') + 1).Split(new[] { '_' }, StringSplitOptions.RemoveEmptyEntries).Select(int.Parse).ToArray();
        static string Dir(string name) => name.Substring(0, name.LastIndexOf('\\') + 1);

        // 360 template for an MCC template name: same directory, 360 option count; exact if present, else nearest.
        public string Choose(string mccName)
        {
            var dir = Dir(mccName); var d = Digits(mccName);
            var pool = _dstTemplates.Where(n => Dir(n).Equals(dir, StringComparison.OrdinalIgnoreCase)).ToList();
            if (pool.Count == 0) { Log.Add("NO 360 TEMPLATES in " + dir); return null; }
            int n = Digits(pool[0]).Length;
            if (d.Skip(n).Any(x => x != 0)) Log.Add($"template {mccName}: MCC-only options {string.Join(",", d.Skip(n))} dropped");
            var want = dir + "_" + string.Join("_", d.Take(n));
            var exact = pool.FirstOrDefault(p => p.Equals(want, StringComparison.OrdinalIgnoreCase));
            if (exact != null) return exact;
            // Cost of each option change, by 360 category name (from the render method definition the template
            // directory belongs to, e.g. shaders\shader_templates\ -> shaders\shader): turning bump mapping on with
            // the 360 default flat normal map is neutral; misc options are minor; alpha test and blend mode are
            // never changed unless nothing else exists; any other change alters the authored look.
            var rmdf = _dstTag("rmdf:" + dir.TrimEnd((char)92).Replace("_templates", ""));
            var cat = rmdf?.Block("Categories").Select(c => c.Str("Category Name")).ToList() ?? new List<string>();
            Func<int, int, int, int> cost = (i, from, to) =>
            {
                if (from == to) return 0;
                var c = i < cat.Count ? cat[i] : "";
                if (c == "bump_mapping" && from == 0 && to == 1) return 1;
                // Material models MCC added after 2007 (shaders\shader options 8-16): each is a variant of an original one,
                // which shares its parameters by name: car_paint and every cook_torrance_* -> cook_torrance (1),
                // two_lobe_phong_tint_map (12) -> two_lobe_phong (2).
                if (c == "material_model" && from >= 8 && from <= 16) return to == (from == 12 ? 2 : 1) ? 2 : 60;
                if (c == "misc") return 3;
                if (c == "alpha_test" || c == "blend_mode") return 1000;
                return 20 + Math.Abs(to - from);
            };
            var best = pool.Select(p => new { p, dd = Digits(p) })
                .Where(x => x.dd.Length == n)
                .OrderBy(x => Enumerable.Range(0, n).Sum(i => cost(i, d[i], x.dd[i])))
                .First().p;
            Log.Add($"template {want} is not on the 360 map: using nearest {best} (missing values from 360 option defaults)");
            return best;
        }

        static uint Be32(byte[] b, int at) => (uint)(b[at] << 24 | b[at + 1] << 16 | b[at + 2] << 8 | b[at + 3]);
        static void Put32(byte[] b, int at, uint v) { b[at] = (byte)(v >> 24); b[at + 1] = (byte)(v >> 16); b[at + 2] = (byte)(v >> 8); b[at + 3] = (byte)v; }
        static void PutF(byte[] b, int at, float f) => Put32(b, at, BitConverter.ToUInt32(BitConverter.GetBytes(f), 0));
        static void Put16(byte[] b, int at, int v) { b[at] = (byte)(v >> 8); b[at + 1] = (byte)v; }

        static Node Field(List<Node> fields, string name) => fields.First(f => string.Equals((f.Name ?? "").Trim(), name, StringComparison.OrdinalIgnoreCase));

        DataBlock Child(Translator tr, DataBlock parent, int pointerOffset)
        {
            var fx = parent.AddressFixups.FirstOrDefault(f => f.WriteOffset == pointerOffset);
            return fx == null ? null : tr.Get(fx.OriginalAddress);
        }
        void SetChild(DataBlock parent, int blockFieldOffset, DataBlock child, int count)
        {
            parent.AddressFixups.RemoveAll(f => f.WriteOffset == blockFieldOffset + 4);
            Put32(parent.Data, blockFieldOffset, (uint)count);
            Put32(parent.Data, blockFieldOffset + 4, 0);
            if (child != null && count > 0) parent.AddressFixups.Add(new DataBlockAddressFixup(child.OriginalAddress, blockFieldOffset + 4));
        }

        public bool Applies(Schema s) => s.Fields.Any(f => f.Name == "Options" && f.Kind == Kind.Block) && s.Fields.Any(f => f.Name == "Postprocess" && f.Kind == Kind.Block);

        public void Apply(Translator tr, DataBlock root, Schema s, string tagName) => Apply(tr, root, s.Fields, 0, tagName);

        // Render methods embedded in a block of another tag (decal systems): every element of every block whose
        // fields include Definition + Options + Postprocess. Returns how many were handled.
        public int ApplyNested(Translator tr, DataBlock block, List<Node> fields, uint elementSize, string path)
        {
            int n = 0;
            foreach (var f in fields.Where(f => f.Kind == Kind.Block && f.Kids != null))
            {
                bool isMethod = f.Kids.Any(k => k.Name == "Options" && k.Kind == Kind.Block) && f.Kids.Any(k => k.Name == "Postprocess" && k.Kind == Kind.Block) && f.Kids.Any(k => k.Name == "Definition");
                for (int e = 0; e < block.EntryCount; e++)
                {
                    var child = Child(tr, block, e * (int)elementSize + (int)f.Offset + 4); if (child == null) continue;
                    if (isMethod) for (int c = 0; c < child.EntryCount; c++) { Apply(tr, child, f.Kids, c * (int)f.ElementSize, path + "/" + f.Name + "[" + c + "]"); n++; }
                    else n += ApplyNested(tr, child, f.Kids, f.ElementSize, path + "/" + f.Name);
                }
            }
            return n;
        }

        void Apply(Translator tr, DataBlock root, List<Node> fields, int baseAt, string tagName)
        {
            var optF = Field(fields, "Options"); var ppF = Field(fields, "Postprocess");
            var defF = Field(fields, "Definition");
            var pp = Child(tr, root, baseAt + (int)ppF.Offset + 4);
            if (pp == null) { Log.Add(tagName + ": no postprocess"); return; }
            var tmplF = Field(ppF.Kids, "Shader Template");
            var texF = Field(ppF.Kids, "Textures"); var fltF = Field(ppF.Kids, "Float Constants");
            var intF = Field(ppF.Kids, "Integer Constants"); var boolF = Field(ppF.Kids, "Boolean Constants");
            var ovF = Field(ppF.Kids, "Overlays");
            int el = (int)ppF.ElementSize;
            // Definition (rmdf) by name in the 360 map
            var defFix = root.TagFixups.FirstOrDefault(f => f.WriteOffset == baseAt + defF.Offset + 12);
            var rmdfName = defFix != null ? _srcName(defFix.OriginalIndex.Value) : null;
            var rmdf = rmdfName != null ? _dstTag("rmdf:" + rmdfName) : null;
            if (rmdf == null) { Log.Add(tagName + ": 360 map lacks render method definition " + rmdfName); return; }

            for (int e = 0; e < pp.EntryCount; e++)
            {
                int b = e * el;
                var tf = pp.TagFixups.FirstOrDefault(f => f.WriteOffset == b + tmplF.Offset + 12);
                if (tf == null) { Log.Add(tagName + ": no template"); continue; }
                var srcTmplName = _srcName(tf.OriginalIndex.Value);
                if (!Template.TryGetValue(tf.OriginalIndex.Value, out var dstTmplName) || dstTmplName == null)
                {
                    // Same name on both sides (decal, particle and other kinds whose option count did not change): the 360 map's own template.
                    if (srcTmplName != null && _dstHas("rmt2:" + srcTmplName)) Template[tf.OriginalIndex.Value] = dstTmplName = srcTmplName;
                    else { Log.Add(tagName + ": template not mapped " + srcTmplName); continue; }
                }
                var sT = _srcTag(tf.OriginalIndex.Value); var dT = _dstTag("rmt2:" + dstTmplName);
                Func<Elem, string, List<string>> names = (t, blk) => t.Block(blk).Select(x => x.Str("Parameter Name")).ToList();
                var sF = names(sT, "Float Constants"); var dF = names(dT, "Float Constants");
                var sI = names(sT, "Integer Constants"); var dI = names(dT, "Integer Constants");
                var sB = names(sT, "Boolean Constants"); var dB = names(dT, "Boolean Constants");
                var sX = names(sT, "Textures"); var dX = names(dT, "Textures");

                // 360 option defaults for this template's options
                var digits = Digits(dstTmplName);
                var defaults = new Dictionary<string, Elem>(StringComparer.OrdinalIgnoreCase);
                Action<uint> addRmop = idx =>
                {
                    if (idx == 0xFFFFFFFF) return; var nm = _dstName(idx); var op = nm == null ? null : _dstTag("rmop:" + nm);
                    if (op != null) foreach (var p in op.Block("Parameters")) defaults[p.Str("Parameter Name")] = p;
                };
                addRmop(rmdf.Datum("Global Options"));
                var cats = rmdf.Block("Categories");
                for (int c = 0; c < cats.Count && c < digits.Length; c++)
                {
                    var opts = cats[c].Block("Options");
                    if (digits[c] < opts.Count) addRmop(opts[digits[c]].Datum("Option"));
                }

                var ppData = pp.Data;
                // Source values (already translated to big-endian)
                var sTex = Child(tr, pp, b + (int)texF.Offset + 4); var sFlt = Child(tr, pp, b + (int)fltF.Offset + 4);
                var sInt = Child(tr, pp, b + (int)intF.Offset + 4);
                uint sBool = Be32(ppData, b + (int)boolF.Offset);
                Func<string, float[]> srcFloat = nm =>
                {
                    int i = sF.IndexOf(nm); if (i < 0 || sFlt == null || (i + 1) * 16 > sFlt.Data.Length) return null;
                    return Enumerable.Range(0, 4).Select(k => BitConverter.ToSingle(BitConverter.GetBytes(Be32(sFlt.Data, i * 16 + k * 4)), 0)).ToArray();
                };
                Func<string, bool?> srcBool = nm => { int i = sB.IndexOf(nm); return i < 0 ? (bool?)null : ((sBool >> i) & 1) != 0; };
                Func<string, int?> srcInt = nm => { int i = sI.IndexOf(nm); return i < 0 || sInt == null ? (int?)null : (int)Be32(sInt.Data, i * 4); };

                // Textures
                var tex = new byte[dX.Count * 0x18]; var texBlock = tr.NewBlock(Math.Max(dX.Count, 1), 4, dX.Count == 0 ? new byte[0x18] : tex);
                for (int i = 0; i < dX.Count; i++)
                {
                    int j = sX.IndexOf(dX[i]), at = i * 0x18;
                    if (j >= 0 && sTex != null && (j + 1) * 0x18 <= sTex.Data.Length)
                    {
                        Buffer.BlockCopy(sTex.Data, j * 0x18, tex, at, 0x18);
                        var fx = sTex.TagFixups.FirstOrDefault(f => f.WriteOffset == j * 0x18 + 12);
                        if (fx != null) texBlock.TagFixups.Add(new DataBlockTagFixup(fx.OriginalIndex, at + 12));
                        int k = (sbyte)sTex.Data[j * 0x18 + 0x15];
                        tex[at + 0x15] = (byte)(k >= 0 && k < sF.Count ? (sbyte)dF.IndexOf(sF[k]) : (sbyte)-1);
                    }
                    else
                    {
                        defaults.TryGetValue(dX[i], out var p);
                        var bm = p != null ? _dstName(p.Datum("Default Bitmap")) : null;
                        Put32(tex, at, (uint)CharConstant.FromString("bitm")); Put32(tex, at + 12, 0xFFFFFFFF);
                        if (bm != null) { var si = _synth("bitm", bm); if (si.IsValid) texBlock.TagFixups.Add(new DataBlockTagFixup(si, at + 12)); }
                        tex[at + 0x12] = (byte)(p != null ? p.Num("Default Address Mode") : 0);
                        tex[at + 0x13] = (byte)(p != null ? p.Num("Default Filter Mode") : 0);
                        tex[at + 0x15] = (byte)(sbyte)dF.IndexOf(dX[i]);
                        Log.Add($"{tagName}: texture {dX[i]} from 360 default {bm ?? "(none)"}");
                    }
                }
                SetChild(pp, b + (int)texF.Offset, texBlock, dX.Count);

                // Float constants
                var flt = new byte[Math.Max(dF.Count, 1) * 16];
                for (int i = 0; i < dF.Count; i++)
                {
                    var v = srcFloat(dF[i]);
                    if (v == null && srcBool(dF[i]) is bool bb) { float x = bb ? 1 : 0; v = new[] { x, x, x, x }; }
                    if (v == null && srcInt(dF[i]) is int ii) v = new float[] { ii, ii, ii, ii };
                    if (v == null)
                    {
                        defaults.TryGetValue(dF[i], out var p);
                        v = DefaultFloat(p);
                        Log.Add($"{tagName}: float {dF[i]} from 360 default ({string.Join(" ", v)})");
                    }
                    for (int k = 0; k < 4; k++) PutF(flt, i * 16 + k * 4, v[k]);
                }
                SetChild(pp, b + (int)fltF.Offset, dF.Count > 0 ? tr.NewBlock(dF.Count, 4, flt) : null, dF.Count);

                // Integer constants
                var ints = new byte[Math.Max(dI.Count, 1) * 4];
                for (int i = 0; i < dI.Count; i++)
                {
                    int v = srcInt(dI[i]) ?? (srcBool(dI[i]) is bool bb ? (bb ? 1 : 0) : (int?)(srcFloat(dI[i])?[0]) ?? (defaults.TryGetValue(dI[i], out var p) ? (int)p.Num("Default Int/Bool Value") : 0));
                    Put32(ints, i * 4, (uint)v);
                }
                SetChild(pp, b + (int)intF.Offset, dI.Count > 0 ? tr.NewBlock(dI.Count, 4, ints) : null, dI.Count);

                // Boolean constants
                uint bits = 0;
                for (int i = 0; i < dB.Count && i < 32; i++)
                {
                    bool v = srcBool(dB[i]) ?? (srcFloat(dB[i]) is float[] f ? f[0] != 0 : srcInt(dB[i]) is int ii ? ii != 0 : (defaults.TryGetValue(dB[i], out var p) && p.Num("Default Int/Bool Value") != 0));
                    if (v) bits |= 1u << i;
                }
                Put32(ppData, b + (int)boolF.Offset, bits);

                // Routing (animated shaders): each entry names a GPU register of the MCC (PC) template. Find the
                // parameter that register belongs to in the MCC template's routing for the same entry point / pass,
                // then use that parameter's register in the 360 template's routing.
                var epF = Field(ppF.Kids, "Entry Points"); var paF = Field(ppF.Kids, "Passes"); var roF = Field(ppF.Kids, "Routing Info");
                var sEp = Child(tr, pp, b + (int)epF.Offset + 4); var sPa = Child(tr, pp, b + (int)paF.Offset + 4); var sRo = Child(tr, pp, b + (int)roF.Offset + 4);
                if (sEp != null && sPa != null && sRo != null)
                {
                    // The MCC build stores identical blocks once; edit a private copy so another shader sharing it is untouched.
                    var roCopy = tr.NewBlock(sRo.EntryCount, sRo.Alignment, (byte[])sRo.Data.Clone());
                    SetChild(pp, b + (int)roF.Offset, roCopy, sRo.EntryCount); sRo = roCopy;
                    int fixedN = 0, missN = 0;
                    var routeCats = new[] { ("Bitmaps", "Bitmaps", sX, dX, 0), ("Vertex Real", "Vertex Real Constants", sF, dF, 2), ("Pixel Real", "Pixel Real Constants", sF, dF, 4) };
                    Func<int, (int count, int start)> range = v => (v >> 10, v & 1023);
                    var sTE = sT.Block("Entry Points"); var dTE = dT.Block("Entry Points");
                    var sTP = sT.Block("Passes"); var dTP = dT.Block("Passes"); var sTR = sT.Block("Routing Info"); var dTR = dT.Block("Routing Info");
                    for (int ep = 0; ep < sEp.EntryCount && ep < sTE.Count && ep < dTE.Count; ep++)
                    {
                        var (pc, ps) = range(sEp.Data[ep * 2] << 8 | sEp.Data[ep * 2 + 1]);
                        var (spc, sps) = range((int)sTE[ep].Num("Block Index Data")); var (dpc, dps) = range((int)dTE[ep].Num("Block Index Data"));
                        for (int k = 0; k < pc && k < spc && k < dpc; k++)
                        {
                            int pa = (ps + k) * 6;
                            foreach (var (shName, tName, sNames, dNames, at) in routeCats)
                            {
                                var (rc, rs) = range(sPa.Data[pa + at] << 8 | sPa.Data[pa + at + 1]);
                                var (src, srs) = range((int)sTP[sps + k].Num(tName)); var (drc, drs) = range((int)dTP[dps + k].Num(tName));
                                for (int r = 0; r < rc; r++)
                                {
                                    int ro = (rs + r) * 4; if (ro + 4 > sRo.Data.Length) continue;
                                    int dest = sRo.Data[ro] << 8 | sRo.Data[ro + 1];
                                    var m = Enumerable.Range(srs, src).Where(i => i < sTR.Count).FirstOrDefault(i => (int)sTR[i].Num("Destination Index") == dest && sTR[i].Num("Source Index") < sNames.Count);
                                    int newDest = -1;
                                    if (src > 0 && m >= srs && (int)sTR[m].Num("Destination Index") == dest)
                                    {
                                        var name = sNames[(int)sTR[m].Num("Source Index")]; int di = dNames.IndexOf(name);
                                        var x = Enumerable.Range(drs, drc).Where(i => i < dTR.Count).FirstOrDefault(i => (int)dTR[i].Num("Source Index") == di);
                                        if (di >= 0 && drc > 0 && x >= drs && (int)dTR[x].Num("Source Index") == di) newDest = (int)dTR[x].Num("Destination Index");
                                    }
                                    if (newDest >= 0) { sRo.Data[ro] = (byte)(newDest >> 8); sRo.Data[ro + 1] = (byte)newDest; fixedN++; }
                                    else missN++;
                                }
                            }
                        }
                    }
                    Log.Add($"{tagName}: routing registers re-mapped to the 360 template: {fixedN}, unresolved {missN}");
                    if (missN > 0)
                    {
                        // An unresolved register would drive the wrong GPU constant: drop the animation, keep the static values.
                        SetChild(pp, b + (int)ovF.Offset, null, 0); SetChild(pp, b + (int)epF.Offset, null, 0);
                        SetChild(pp, b + (int)paF.Offset, null, 0); SetChild(pp, b + (int)roF.Offset, null, 0);
                        Log.Add($"{tagName}: animated overlays removed (registers could not be resolved)");
                    }
                }
                Log.Add($"{tagName}: template {srcTmplName} -> {dstTmplName}; textures {dX.Count}, floats {dF.Count}, ints {dI.Count}, bools {dB.Count}");
            }

            // Options: 360 option digits of the chosen template (first postprocess)
            var tf0 = pp.TagFixups.FirstOrDefault(f => f.WriteOffset == tmplF.Offset + 12);
            if (tf0 != null && Template.TryGetValue(tf0.OriginalIndex.Value, out var t0) && t0 != null)
            {
                var d = Digits(t0); var data = new byte[d.Length * 2];
                for (int i = 0; i < d.Length; i++) Put16(data, i * 2, d[i]);
                SetChild(root, baseAt + (int)optF.Offset, tr.NewBlock(d.Length, 4, data), d.Length);
            }
        }

        static float[] DefaultFloat(Elem p)
        {
            if (p == null) return new float[] { 0, 0, 0, 0 };
            int type = (int)p.Num("Parameter Type");
            switch (type)
            {
                case 0: { float s = (float)p.Num("Default Bitmap Scale"); if (s == 0) s = 1; return new[] { s, s, 0, 0 }; }
                case 1: case 5:
                    {
                        uint c = (uint)p.Num("Default Color");
                        return new[] { ((c >> 16) & 255) / 255f, ((c >> 8) & 255) / 255f, (c & 255) / 255f, type == 5 ? ((c >> 24) & 255) / 255f : 1f };
                    }
                case 2: { float v = (float)p.Num("Default Real Value"); return new[] { v, v, v, v }; }
                default: { float v = (float)p.Num("Default Int/Bool Value"); return new[] { v, v, v, v }; }
            }
        }
    }
}
