// Shaders: Halo Online render methods onto stock Halo 3 templates.
// Halo Online's shader programs are compiled for the PC and its render method definitions have extra options, so no
// shader program is converted. For every render method (shader, terrain, foliage, water, halogram, custom, decal,
// particle ...) the Halo Online options are read by name (HaloShaderGenerator's method/option enums, the same source
// TagTool builds Halo Online's definitions from), matched to the stock Halo 3 definition's categories by name, and the
// closest stock Halo 3 template (any stock map; grafted when the basis lacks it) is chosen. The constants are then laid
// out in the stock template's own parameter order, by name: textures (bitmap, sampler, transform index), reals, ints,
// bools and queryable properties; anything the source lacks takes the stock option default. Animated parameters are
// re-routed onto the stock template (TagTool ShaderFunctionHelper). Modelled on TagTool's ShaderMatcherNew and
// ShaderConverter, run in the opposite direction (Halo Online source, Halo 3 base).
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using TagTool.Cache;
using TagTool.Shaders.ShaderFunctions;
using TagTool.Shaders.ShaderMatching;
using TagTool.Tags.Definitions;
using static TagTool.Tags.Definitions.RenderMethod.RenderMethodPostprocessBlock;

namespace Ho2H3
{
    public class Shaders
    {
        readonly GameCache _ho; readonly Stream _hoStream; readonly Dictionary<string, string> _owner; readonly string _basis; readonly List<string> _log;
        readonly Func<CachedTag, bool> _stockRef;   // registers a stock Halo 3 tag (from a TagTool Gen3 cache) as referenced
        readonly Dictionary<string, (GameCache c, Stream s)> _h3 = new Dictionary<string, (GameCache, Stream)>(StringComparer.OrdinalIgnoreCase);
        readonly Dictionary<string, (RenderMethodDefinition def, CachedTag tag, GameCache c)> _rmdf = new Dictionary<string, (RenderMethodDefinition, CachedTag, GameCache)>();
        readonly Dictionary<string, List<(string name, int[] opts)>> _templates = new Dictionary<string, List<(string, int[])>>();
        public int Converted, Exact, Failed;

        public Shaders(GameCache ho, Stream hoStream, Dictionary<string, string> owner, string basis, Func<CachedTag, bool> stockRef, List<string> log)
        {
            _ho = ho; _hoStream = hoStream; _owner = owner; _basis = basis; _stockRef = stockRef; _log = log;
            foreach (var k in owner.Keys)
            {
                if (!k.StartsWith("rmt2:shaders\\", StringComparison.OrdinalIgnoreCase)) continue;
                var name = k.Substring(5); var parts = name.Split('\\'); if (parts.Length != 3 || !parts[1].EndsWith("_templates") || !parts[2].StartsWith("_")) continue;
                var type = parts[1].Substring(0, parts[1].Length - "_templates".Length);
                int[] o; try { o = parts[2].Substring(1).Split('_').Select(int.Parse).ToArray(); } catch { continue; }
                if (!_templates.TryGetValue(type, out var l)) _templates[type] = l = new List<(string, int[])>();
                l.Add((name, o));
            }
        }

        public (GameCache c, Stream s) H3(string path)
        {
            if (!_h3.TryGetValue(path, out var v)) { var c = GameCache.Open(new FileInfo(path)); _h3[path] = v = (c, c.OpenCacheRead()); }
            return v;
        }
        public CachedTag StockTag(string key) => H3Tag(key).t;
        (GameCache c, Stream s, CachedTag t) H3Tag(string key)
        {
            if (!_owner.TryGetValue(key, out var m)) return (null, null, null);
            var (c, s) = H3(m); int i = key.IndexOf(':');
            return c.TagCache.TryGetTag(key.Substring(i + 1) + "." + key.Substring(0, i), out var t) ? (c, s, t) : (c, s, null);
        }

        static readonly Dictionary<string, int> Weight = new Dictionary<string, int>
        {
            ["blend_mode"] = 100000, ["alpha_test"] = 50000, ["distortion"] = 20000, ["blending"] = 20000, ["albedo"] = 3000,
            ["bump_mapping"] = 2000, ["self_illumination"] = 1500, ["material_model"] = 1000, ["environment_mapping"] = 800,
            ["specular_mask"] = 400, ["parallax"] = 200, ["misc"] = 100, ["lighting"] = 3000, ["render_targets"] = 50000,
        };

        // the render methods inside a converted definition: the definition itself and one level of fields / blocks
        public void ConvertAll(object def, CachedTag tag)
        {
            if (def is RenderMethod rm0) { Convert(rm0, tag); return; }
            foreach (var f in def.GetType().GetFields())
            {
                var v = f.GetValue(def);
                if (v is RenderMethod rm) Convert(rm, tag);
                else if (v is IList list && !(v is Array)) foreach (var e in list) if (e != null) foreach (var f2 in e.GetType().GetFields()) if (f2.GetValue(e) is RenderMethod rm2) Convert(rm2, tag);
            }
        }

        public void Convert(RenderMethod rm, CachedTag tag)
        {
            if (rm.ShaderProperties == null || rm.ShaderProperties.Count == 0 || rm.ShaderProperties[0].Template == null) return;
            var p = rm.ShaderProperties[0]; var hoTemplate = p.Template; string where = $"{tag.Name}.{tag.Group.Tag}";
            try
            {
                if (!ShaderMatcherNew.Rmt2Descriptor.TryParse(hoTemplate.Name, out var desc) || desc.IsMs30) { _log.Add($"shader: template name not understood {hoTemplate.Name} ({where})"); Failed++; Clear(rm); return; }
                string type = desc.Type;
                // Halo Online option names
                var gen = desc.GetGenerator();
                var hoNames = new Dictionary<string, string>();
                if (gen != null)
                {
                    var methods = gen.GetMethodNames();
                    for (int i = 0; i < methods.Length && i < desc.Options.Length; i++)
                    {
                        var opts = gen.GetMethodOptionNames(i);
                        hoNames[Fix(methods.GetValue(i).ToString().ToLowerInvariant())] = desc.Options[i] < opts.Length ? Fix(opts.GetValue(desc.Options[i]).ToString().ToLowerInvariant()) : null;
                    }
                }
                // stock Halo 3 definition
                if (!_rmdf.TryGetValue(type, out var rd))
                {
                    var (c, s, t) = H3Tag("rmdf:shaders\\" + type);
                    rd = t == null ? (null, null, null) : (c.Deserialize<RenderMethodDefinition>(s, t), t, c);
                    _rmdf[type] = rd;
                }
                if (rd.def == null || !_templates.TryGetValue(type, out var cands)) { _log.Add($"shader: no stock Halo 3 {type} definition/templates ({where})"); Failed++; Clear(rm); return; }
                var cats = rd.def.Categories;
                var want = new int[cats.Count]; var catNames = new string[cats.Count];
                for (int i = 0; i < cats.Count; i++)
                {
                    catNames[i] = rd.c.StringTable.GetString(cats[i].Name);
                    if (!hoNames.TryGetValue(catNames[i], out var on) || on == null) { want[i] = 0; continue; }
                    int k = cats[i].ShaderOptions.FindIndex(o => rd.c.StringTable.GetString(o.Name) == on);
                    if (k < 0) { k = 0; _log.Add($"shader: {type} {catNames[i]}\\{on} has no Halo 3 option; using {rd.c.StringTable.GetString(cats[i].ShaderOptions.Count > 0 ? cats[i].ShaderOptions[0].Name : TagTool.Common.StringId.Invalid)} ({where})"); }
                    want[i] = k;
                }
                // closest stock template: weighted category agreement; then no graft; then simplest
                var best = cands.OrderByDescending(x => Enumerable.Range(0, want.Length).Sum(i => i < x.opts.Length && x.opts[i] == want[i] ? (Weight.TryGetValue(catNames[i], out var w) ? w : 300) : 0))
                    .ThenBy(x => _owner["rmt2:" + x.name] == _basis ? 0 : 1).ThenBy(x => x.opts.Sum()).First();
                bool exact = best.opts.Length == want.Length && best.opts.SequenceEqual(want);
                string diff = exact ? "" : " [" + string.Join(" ", Enumerable.Range(0, want.Length).Where(i => i >= best.opts.Length || best.opts[i] != want[i]).Select(i => $"{catNames[i]}:{Opt(rd, i, want[i])}->{(i < best.opts.Length ? Opt(rd, i, best.opts[i]) : "?")}")) + "]";
                var (hc, hs, ht) = H3Tag("rmt2:" + best.name);
                var h3t = hc.Deserialize<RenderMethodTemplate>(hs, ht);
                if (!ReferenceEquals(hc, rd.c)) { var (c2, s2, t2) = (hc, hs, hc.TagCache.GetTag(rd.tag.Name, "rmdf")); rd = (c2.Deserialize<RenderMethodDefinition>(s2, t2), t2, c2); }
                var parms = TagTool.Shaders.ShaderGenerator.ShaderGeneratorNew.GatherParameters(hc, hs, rd.def, best.opts.Select(x => (byte)x).ToList(), true);
                string HName(TagTool.Common.StringId id) => hc.StringTable.GetString(id);

                // source template parameter names (Halo Online rmt2 in the package)
                RenderMethodTemplate hoT = null;
                if (hoTemplate is TagTool.Cache.HaloOnline.CachedTagHaloOnline ht0 && !ht0.IsEmpty()) hoT = _ho.Deserialize<RenderMethodTemplate>(_hoStream, hoTemplate);
                var hoTex = hoT?.TextureParameterNames.Select(n => _ho.StringTable.GetString(n.Name)).ToList() ?? new List<string>();
                var hoReal = hoT?.RealParameterNames.Select(n => _ho.StringTable.GetString(n.Name)).ToList() ?? new List<string>();
                var hoInt = hoT?.IntegerParameterNames.Select(n => _ho.StringTable.GetString(n.Name)).ToList() ?? new List<string>();
                var hoBool = hoT?.BooleanParameterNames.Select(n => _ho.StringTable.GetString(n.Name)).ToList() ?? new List<string>();
                if (hoT == null) _log.Add($"shader: source template {hoTemplate.Name} not in the package; stock defaults only ({where}); authoring parameters {rm.Parameters?.Count}: {string.Join(",", (rm.Parameters ?? new List<RenderMethod.RenderMethodParameterBlock>()).Select(x => _ho.StringTable.GetString(x.Name)))}; constants tex {p.TextureConstants.Count} real {p.RealConstants.Count}");
                var animated = hoT != null && p.Functions.Count > 0 ? ShaderFunctionHelper.GetAnimatedParameters(_ho, rm, hoT) : new List<ShaderFunctionHelper.AnimatedParameter>();

                // source template not in the package: with an exact option match and the same constant counts, the stock
                // template's order is the source's (Halo Online templates are generated from the same option set)
                if (hoT == null && exact && p.TextureConstants.Count == h3t.TextureParameterNames.Count && p.RealConstants.Count == h3t.RealParameterNames.Count && p.IntegerConstants.Count == h3t.IntegerParameterNames.Count)
                {
                    hoTex = h3t.TextureParameterNames.Select(n => hc.StringTable.GetString(n.Name)).ToList(); hoReal = h3t.RealParameterNames.Select(n => hc.StringTable.GetString(n.Name)).ToList();
                    hoInt = h3t.IntegerParameterNames.Select(n => hc.StringTable.GetString(n.Name)).ToList(); hoBool = h3t.BooleanParameterNames.Select(n => hc.StringTable.GetString(n.Name)).ToList();
                    _log.Add($"shader: {where} constants taken in stock template order (same options and counts)");
                }
                // source template not in the package, counts differ: rebuild its parameter order the way Halo Online's
                // templates are generated (option parameters in category order, global options first: a bitmap adds a
                // texture and its transform real, real/colour a real, int an int, bool a bool), from the stock options
                // with the same names; used per kind only where the count equals the source constants exactly
                if (hoT == null && hoTex.Count == 0)
                {
                    var st = new List<string>(); var sr = new List<string>(); var si = new List<string>(); var sbo = new List<string>();
                    foreach (var prm in parms)
                    {
                        if (prm.RenderMethodExtern != TagTool.Shaders.RenderMethodExtern.none) continue;
                        string n = HName(prm.Name);
                        switch (prm.Type)
                        {
                            case RenderMethodOption.ParameterBlock.OptionDataType.Bitmap: st.Add(n); sr.Add(n); break;
                            case RenderMethodOption.ParameterBlock.OptionDataType.Real: case RenderMethodOption.ParameterBlock.OptionDataType.Color: case RenderMethodOption.ParameterBlock.OptionDataType.ArgbColor: sr.Add(n); break;
                            case RenderMethodOption.ParameterBlock.OptionDataType.Int: si.Add(n); break;
                            case RenderMethodOption.ParameterBlock.OptionDataType.Bool: sbo.Add(n); break;
                        }
                    }
                    // second source: Halo Online's own shader generator for these options (TagTool GenerateRenderMethodTemplate:
                    // pixel then vertex parameters, by kind); third: the stock order filtered to the generator's names
                    List<string> gt = new List<string>(), gr = new List<string>(), gi = new List<string>();
                    try
                    {
                        dynamic px = gen?.GetPixelShaderParameters(), vx = gen?.GetVertexShaderParameters();
                        void AddAll(List<string> to, dynamic list) { if (list != null) foreach (var q in list) { string n = q.ParameterName; if (!to.Contains(n)) to.Add(n); } }
                        if (px != null) { AddAll(gr, px.GetRealPixelParameters()); AddAll(gi, px.GetIntegerPixelParameters()); AddAll(gt, px.GetSamplerPixelParameters()); }
                        if (vx != null) { AddAll(gr, vx.GetRealVertexParameters()); AddAll(gi, vx.GetIntegerVertexParameters()); AddAll(gt, vx.GetSamplerVertexParameters()); }
                    }
                    catch (Exception ex) { _log.Add($"shader: {where} generator parameters unavailable: {ex.GetType().Name}"); }
                    var all = new HashSet<string>(gt.Concat(gr).Concat(gi));
                    List<string> Pick(int count, params List<string>[] cands) => cands.FirstOrDefault(c => c.Count == count && count > 0);
                    var used = new List<string>();
                    var tPick = Pick(p.TextureConstants.Count, st, gt, st.Where(all.Contains).ToList()); if (tPick != null) { hoTex = tPick; used.Add("textures"); }
                    var rPick = Pick(p.RealConstants.Count, sr, gr, sr.Where(all.Contains).ToList()); if (rPick != null) { hoReal = rPick; used.Add("reals"); }
                    var iPick = Pick(p.IntegerConstants.Count, si, gi, si.Where(all.Contains).ToList()); if (iPick != null) { hoInt = iPick; used.Add("ints"); }
                    _log.Add($"shader: {where} generator tex [{string.Join(",", gt)}] real [{string.Join(",", gr)}]");
                    // still unmatched: the material's real option set can differ from its template name by one setting
                    // (Reflection's bamboo leaves: no detail map); try every option set one setting away
                    if (tPick == null || rPick == null)
                    {
                        // a texture's transform real looks like (scale u, scale v, offset u, offset v): both scales non-zero.
                        // Score = texture-named reals that look like that; best fitting option set wins.
                        int Score(List<string> tx, List<string> rl) { int sc = 0; for (int k = 0; k < rl.Count && k < p.RealConstants.Count; k++) { var c = p.RealConstants[k]; bool xf = c.Arg0 != 0 && c.Arg1 != 0 && c.Arg3 != 1; if (tx.Contains(rl[k]) == xf) sc++; } return sc; }
                        (List<string> t, List<string> r, string d, int sc) bestAlt = (null, null, null, -1);
                        for (int ci2 = 0; ci2 < rd.def.Categories.Count; ci2++)
                            for (int oi = 0; oi < rd.def.Categories[ci2].ShaderOptions.Count; oi++)
                            {
                                if (ci2 < best.opts.Length && oi == best.opts[ci2]) continue;
                                var alt = best.opts.Select(x => (byte)x).ToList(); while (alt.Count <= ci2) alt.Add(0); alt[ci2] = (byte)oi;
                                List<RenderMethodOption.ParameterBlock> ap; try { ap = TagTool.Shaders.ShaderGenerator.ShaderGeneratorNew.GatherParameters(hc, hs, rd.def, alt, true); } catch { continue; }
                                var at = new List<string>(); var ar = new List<string>();
                                foreach (var prm in ap)
                                {
                                    if (prm.RenderMethodExtern != TagTool.Shaders.RenderMethodExtern.none) continue; string n = HName(prm.Name);
                                    if (prm.Type == RenderMethodOption.ParameterBlock.OptionDataType.Bitmap) { at.Add(n); ar.Add(n); }
                                    else if (prm.Type == RenderMethodOption.ParameterBlock.OptionDataType.Real || prm.Type == RenderMethodOption.ParameterBlock.OptionDataType.Color || prm.Type == RenderMethodOption.ParameterBlock.OptionDataType.ArgbColor) ar.Add(n);
                                }
                                if (at.Count != p.TextureConstants.Count || ar.Count != p.RealConstants.Count) continue;
                                int sc = Score(at, ar);
                                if (sc > bestAlt.sc) bestAlt = (at, ar, catNames[ci2] + " -> " + Opt(rd, ci2, oi), sc);
                            }
                        if (bestAlt.t != null && bestAlt.sc == p.RealConstants.Count)
                        { hoTex = bestAlt.t; hoReal = bestAlt.r; tPick = bestAlt.t; rPick = bestAlt.r; used.Add($"textures, reals (option set one setting away: {bestAlt.d}; all {bestAlt.sc} reals consistent)"); }
                        else if (bestAlt.t != null) _log.Add($"shader: {where} nearest option set {bestAlt.d} fits counts but only {bestAlt.sc} of {p.RealConstants.Count} reals consistent; not used");
                        // last: the source has fewer entries than the stock order (Halo Online options Halo 3 lacks, e.g. foliage
                        // albedo without detail): drop the surplus textures (with their transform reals) and surplus other reals,
                        // keep the one subsequence where every value is consistent with its slot
                        if (tPick == null && st.Count > p.TextureConstants.Count && st.Count - p.TextureConstants.Count <= 2)
                        {
                            IEnumerable<List<int>> Combos(int n, int k, int from = 0) { if (k == 0) { yield return new List<int>(); yield break; } for (int x = from; x <= n - k; x++) foreach (var rest in Combos(n, k - 1, x + 1)) { rest.Insert(0, x); yield return rest; } }
                            (List<string> t, List<string> r, int sc, string d) bs = (null, null, -1, null);
                            foreach (var dt in Combos(st.Count, st.Count - p.TextureConstants.Count))
                            {
                                var t2 = st.Where((x, k) => !dt.Contains(k)).ToList(); var gone = dt.Select(k => st[k]).ToList();
                                var r1 = sr.Where(x => !gone.Contains(x)).ToList(); int extra = r1.Count - p.RealConstants.Count; if (extra < 0 || extra > 2) continue;
                                var others = Enumerable.Range(0, r1.Count).Where(k => !t2.Contains(r1[k])).ToList();
                                foreach (var dr in Combos(others.Count, extra))
                                {
                                    var drop = new HashSet<int>(dr.Select(k => others[k])); var r2 = r1.Where((x, k) => !drop.Contains(k)).ToList();
                                    int sc = Score(t2, r2); if (sc >= bs.sc) bs = (t2, r2, sc, "dropped " + string.Join(",", gone.Concat(drop.Select(k => r1[k]))));
                                }
                            }
                            if (bs.t != null && bs.sc == p.RealConstants.Count) { hoTex = bs.t; hoReal = bs.r; tPick = bs.t; rPick = bs.r; used.Add($"textures, reals (stock order, {bs.d}; all reals consistent)"); }
                            else if (bs.t != null) _log.Add($"shader: {where} best subsequence ({bs.d}) only {bs.sc} of {p.RealConstants.Count} reals consistent; not used");
                        }
                    }
                    _log.Add($"shader: {where} source textures [{string.Join(", ", p.TextureConstants.Select(x => x.Bitmap?.Name ?? "null"))}] reals [{string.Join(" | ", p.RealConstants.Select(x => $"{x.Arg0:0.###} {x.Arg1:0.###} {x.Arg2:0.###} {x.Arg3:0.###}"))}]; stock order tex [{string.Join(",", st)}] real [{string.Join(",", sr)}]");
                    _log.Add($"shader: {where} source order rebuilt from stock options: {(used.Count > 0 ? string.Join(", ", used) : "no kind matched")} (source tex {p.TextureConstants.Count}/{st.Count} real {p.RealConstants.Count}/{sr.Count})");
                }
                RenderMethodOption.ParameterBlock Default(string n, Func<RenderMethodOption.ParameterBlock, bool> ok) => parms.FirstOrDefault(x => HName(x.Name) == n && ok(x));
                var h3Real = h3t.RealParameterNames.Select(n => HName(n.Name)).ToList();
                var tex = new List<TextureConstant>(); int defaulted = 0;
                foreach (var n in h3t.TextureParameterNames.Select(x => HName(x.Name)))
                {
                    int si = hoTex.IndexOf(n); TextureConstant tc;
                    if (si >= 0 && si < p.TextureConstants.Count) tc = p.TextureConstants[si];
                    else
                    {
                        defaulted++; var d = Default(n, x => x.Type == RenderMethodOption.ParameterBlock.OptionDataType.Bitmap);
                        tc = new TextureConstant { Bitmap = d?.DefaultSamplerBitmap, ExternTextureMode = TextureConstant.RenderMethodExternTextureMode.UseBitmapAsNormal };
                        if (d != null)
                        {
                            tc.SamplerAddressMode = new TextureConstant.PackedSamplerAddressMode { AddressU = (TextureConstant.SamplerAddressModeEnum)d.DefaultAddressMode, AddressV = (TextureConstant.SamplerAddressModeEnum)d.DefaultAddressMode };
                            tc.FilterMode = (TextureConstant.SamplerFilterMode)d.DefaultFilterMode;
                        }
                        if (tc.Bitmap != null) _stockRef(tc.Bitmap);
                    }
                    tc.TextureTransformConstantIndex = (sbyte)h3Real.IndexOf(n);
                    tc.TextureTransformOverlayIndices = new TagTool.Common.TagBlockIndex();
                    tex.Add(tc);
                }
                var real = new List<RealConstant>();
                foreach (var n in h3Real)
                {
                    int si = hoReal.IndexOf(n);
                    if (si >= 0 && si < p.RealConstants.Count) { real.Add(p.RealConstants[si]); continue; }
                    defaulted++; var d = Default(n, x => x.Type != RenderMethodOption.ParameterBlock.OptionDataType.Bool && x.Type != RenderMethodOption.ParameterBlock.OptionDataType.Int);
                    var rc = new RealConstant();
                    if (d == null) { }
                    else if (d.Type == RenderMethodOption.ParameterBlock.OptionDataType.Bitmap) { rc.Arg0 = rc.Arg1 = d.DefaultBitmapScale > 0 ? d.DefaultBitmapScale : 1f; }
                    else if (d.Type == RenderMethodOption.ParameterBlock.OptionDataType.ArgbColor) { rc.Arg0 = d.DefaultColor.Red / 255f; rc.Arg1 = d.DefaultColor.Green / 255f; rc.Arg2 = d.DefaultColor.Blue / 255f; rc.Arg3 = d.DefaultColor.Alpha / 255f; }
                    else rc.Arg0 = rc.Arg1 = rc.Arg2 = rc.Arg3 = d.DefaultFloatArgument;
                    real.Add(rc);
                }
                var ints = new List<uint>();
                foreach (var n in h3t.IntegerParameterNames.Select(x => HName(x.Name)))
                {
                    int si = hoInt.IndexOf(n);
                    if (si >= 0 && si < p.IntegerConstants.Count) ints.Add(p.IntegerConstants[si]);
                    else { defaulted++; ints.Add(Default(n, x => true)?.DefaultIntBoolArgument ?? 0); }
                }
                uint bools = 0; var h3Bool = h3t.BooleanParameterNames.Select(x => HName(x.Name)).ToList();
                for (int i = 0; i < h3Bool.Count; i++)
                {
                    int si = hoBool.IndexOf(h3Bool[i]); bool v;
                    if (si >= 0) v = (p.BooleanConstants >> si & 1) != 0; else { defaulted++; v = (Default(h3Bool[i], x => true)?.DefaultIntBoolArgument ?? 0) != 0; }
                    if (v) bools |= 1u << i;
                }
                // queryable properties: 0-3 and 5 texture indices, 4 a real index (TagTool ShaderConverter)
                var q = new short[8]; var hq = p.QueryableProperties ?? Enumerable.Repeat((short)-1, 8).ToArray();
                var h3Tex = h3t.TextureParameterNames.Select(x => HName(x.Name)).ToList();
                for (int i = 0; i < 8; i++)
                {
                    q[i] = -1; if (hq[i] < 0) continue;
                    if (i == 4) { if (hq[i] < hoReal.Count) q[i] = (short)h3Real.IndexOf(hoReal[hq[i]]); }
                    else if (i <= 5) { if (hq[i] < hoTex.Count) q[i] = (short)h3Tex.IndexOf(hoTex[hq[i]]); }
                }

                // write back in Halo 3 form
                rm.BaseRenderMethod = rd.tag; _stockRef(rd.tag);
                rm.Options = best.opts.Select(o => new RenderMethod.RenderMethodOptionIndex { OptionIndex = (short)o }).ToList();
                rm.Parameters = new List<RenderMethod.RenderMethodParameterBlock>();
                p.Template = ht; _stockRef(ht);
                // alpha-tested templates need the render method's alpha test flag (stock Guardian's tree branches carry it;
                // TagTool clears it when porting to Halo Online, so the source never has it)
                int atc = Array.IndexOf(catNames, "alpha_test");
                if (atc >= 0 && atc < best.opts.Length)
                {
                    var atName = Opt(rd, atc, best.opts[atc]);
                    if (atName != "none" && atName != "off") p.Flags |= RenderMethodPostprocessFlags.EnableAlphaTest; else p.Flags &= ~RenderMethodPostprocessFlags.EnableAlphaTest;
                }
                p.TextureConstants = tex; p.RealConstants = real; p.IntegerConstants = ints; p.BooleanConstants = bools; p.QueryableProperties = q;
                p.EntryPoints = new List<TagTool.Common.TagBlockIndex>(); p.Passes = new List<RenderMethodPostprocessPassBlock>(); p.RoutingInfo = new List<RenderMethodRoutingInfoBlock>();
                if (animated.Count > 0) ShaderFunctionHelper.BuildAnimatedParameters(hc, rm, h3t, animated);
                else p.Functions = new List<RenderMethod.RenderMethodAnimatedParameterBlock>();
                Converted++; if (exact) Exact++;
                _log.Add($"shader: {where} {hoTemplate.Name} -> {best.name}{(exact ? "" : " (closest)" + diff)}{(defaulted > 0 ? $", {defaulted} stock defaults" : "")}{(animated.Count > 0 ? $", {animated.Count} animated" : "")}");
            }
            catch (Exception ex) { Failed++; _log.Add($"shader: failed {where}: {ex.GetType().Name} {ex.Message}"); Clear(rm); }
        }

        static string Opt((RenderMethodDefinition def, CachedTag tag, GameCache c) rd, int cat, int opt) => opt < rd.def.Categories[cat].ShaderOptions.Count ? rd.c.StringTable.GetString(rd.def.Categories[cat].ShaderOptions[opt].Name) : opt.ToString();

        // a render method that could not be matched keeps no Halo Online template (reference cleared, listed)
        static void Clear(RenderMethod rm) { rm.ShaderProperties[0].Template = null; }

        static string Fix(string s) => s switch
        {
            "first_person_never_with_rotating_bitmaps" => @"first_person_never_w/rotating_bitmaps",
            "_3_channel_self_illum" => "3_channel_self_illum",
            "blackness_no_options" => "blackness(no_options)",
            "always_calc_albedo" => "first_person_never",   // Halo Online misc option; Halo 3's default
            _ => s
        };
    }
}
