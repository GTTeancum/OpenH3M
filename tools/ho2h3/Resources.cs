// Halo Online resources -> Halo 3 360 resources.
// Converted before a tag is serialized (Prepare, by group) and remembered by reference identity; the serializer hook
// (Pre) then writes each converted reference as a resource fixup, any other as null.
//   bitmaps: Halo Online keeps every level linear and little-endian in the primary data (PC D3D9); Inject360's
//            BitmapConverter tiles it for the 360 (Xenos layout, byte order, DXN bias) and the 64-byte 360 texture
//            control is written as Inject360 does for stock 360 textures.
using System;
using System.Collections.Generic;
using System.Linq;
using Blamite.Injection;
using TagTool.Bitmaps;
using TagTool.Cache;
using TagTool.Common;
using TagTool.Tags;
using TagTool.Tags.Definitions;
using ResourceFixup = Blamite.Blam.Resources.ResourceFixup;
using ResourceDefinitionFixup = Blamite.Blam.Resources.ResourceDefinitionFixup;
using BDatum = Blamite.Blam.DatumIndex;

namespace Ho2H3
{
    public class Resources
    {
        readonly GameCache _cache; readonly TagContainer _container; readonly List<string> _log; readonly Inject360.ResourceSink _sink;
        public int Converted, Dropped; ushort _next;
        readonly Dictionary<TagResourceReference, BDatum> _done = new Dictionary<TagResourceReference, BDatum>(ReferenceEqualityComparer.Instance);
        public Resources(GameCache cache, byte[] salt, TagContainer container, List<string> log) { _cache = cache; _container = container; _log = log; _sink = new Inject360.ResourceSink(container, salt); }

        static void Be32(byte[] b, int at, uint v) { b[at] = (byte)(v >> 24); b[at + 1] = (byte)(v >> 16); b[at + 2] = (byte)(v >> 8); b[at + 3] = (byte)v; }
        static void Be16(byte[] b, int at, int v) { b[at] = (byte)(v >> 8); b[at + 1] = (byte)v; }

        public void Prepare(CachedTag tag, object def, Func<CachedTag, BDatum> tagDatum)
        {
            var self = tagDatum(tag);
            try
            {
                if (def is Bitmap bitm) PrepareBitmap(tag, bitm, self);
                if (def is ScenarioStructureBsp sbsp && sbsp.CollisionBspResource != null && !_done.ContainsKey(sbsp.CollisionBspResource))
                {
                    var rdef = _cache.ResourceCache.GetStructureBspTagResources(sbsp.CollisionBspResource);
                    if (rdef != null)
                    {
                        // Halo Online keeps level collision as large collision BSPs (32-bit indices), which Halo 3 retail
                        // does not have: shrink them back into ordinary collision BSPs (TagTool ResizeCollisionBSP) when
                        // the counts fit Halo 3's 16-bit limits
                        if (rdef.LargeCollisionBsps != null && rdef.LargeCollisionBsps.Count > 0)
                        {
                            var rz = new TagTool.Geometry.BspCollisionGeometry.Utils.ResizeCollisionBSP();
                            if (rdef.CollisionBsps == null) rdef.CollisionBsps = new TagBlock<TagTool.Geometry.BspCollisionGeometry.CollisionGeometry>(CacheAddressType.Definition);
                            foreach (var lb in rdef.LargeCollisionBsps)
                            {
                                if (!rz.collision_bsp_check_counts(lb)) { _log.Add($"collision: large collision BSP of {tag.Name} exceeds Halo 3 limits (nodes {lb.Bsp3dNodes?.Count}, surfaces {lb.Surfaces?.Count}, edges {lb.Edges?.Count}, vertices {lb.Vertices?.Count})"); continue; }
                                rdef.CollisionBsps.Add(rz.ShrinkCollisionBsp(lb));
                            }
                            _log.Add($"collision: {tag.Name}: {rdef.LargeCollisionBsps.Count} large collision BSP(s) -> {rdef.CollisionBsps.Count} Halo 3 collision BSP(s)");
                            rdef.LargeCollisionBsps.Clear();
                        }
                        // instance collision with no Havok MOPP: Reach (and so Halo Online) gives most instance definitions
                        // decomposed polyhedra instead, which Halo 3 does not have; without a MOPP the player falls through.
                        // Generated with TagTool's own MOPP tool (CollisionMoppGenerator, TagTool\Tools\mopp.exe), as the
                        // Reach route did (ReachPort MoppGen).
                        if (rdef.InstancedGeometry != null)
                        {
                            int made = 0, failed = 0;
                            foreach (var ig in rdef.InstancedGeometry)
                            {
                                if (ig.CollisionInfo?.Surfaces == null || ig.CollisionInfo.Surfaces.Count == 0) continue;   // all regenerated: Halo Online's own use post-Halo 3 keys
                                TagTool.Havok.TagHkpMoppCode m = null;
                                try { m = TagTool.Havok.CollisionMoppGenerator.Generate(ig.CollisionInfo); } catch (Exception ex) { _log.Add($"collision: MOPP generation error {tag.Name}: {ex.Message}"); }
                                if (m == null) { failed++; continue; }
                                ig.CollisionMoppCodes = new TagBlock<TagTool.Havok.TagHkpMoppCode>(CacheAddressType.Definition) { m }; made++;
                            }
                            _log.Add($"collision: {tag.Name}: {made} instance MOPPs generated, {failed} failed");
                        }
                        ClusterMopps.Build(tag, sbsp, rdef, _log);
                        ClusterMopps.BuildStructure(tag, sbsp, rdef, _log);
                        // per-mesh cluster visibility, generated for every mesh (Halo Online's are empty or post-Halo 3)
                        var meshComp = new Dictionary<int, int>();
                        if (rdef.InstancedGeometry != null) foreach (var ig in rdef.InstancedGeometry) if (ig.MeshIndex >= 0 && !meshComp.ContainsKey(ig.MeshIndex)) meshComp[ig.MeshIndex] = ig.CompressionIndex;
                        var gdef = GeoDef(sbsp.Geometry, tag.Name);
                        MeshMopps.Build(_cache, sbsp.Geometry, gdef, meshComp, _log, tag.Name);   // cluster instance physics (Halo Online leaves it empty)
                        // surface facing: Halo Online marks a negated plane with a surface flag (0x80); Halo 3 has no such flag
                        // and negates through the plane index's high bit (0x8000). Folded in for the structure and every instance
                        // (Reflection 030: 3774 surfaces; without it ramps and edges face the wrong way and cannot be walked).
                        int negated = 0;
                        void FoldNegation(TagTool.Geometry.BspCollisionGeometry.CollisionGeometry cg)
                        {
                            if (cg?.Surfaces == null) return;
                            foreach (var sf in cg.Surfaces)
                                if (((int)sf.Flags & 0x80) != 0) { sf.Plane = (ushort)(sf.Plane | 0x8000); sf.Flags = (TagTool.Geometry.BspCollisionGeometry.SurfaceFlags)((int)sf.Flags & ~0x80); negated++; }
                        }
                        if (rdef.CollisionBsps != null) foreach (var cg in rdef.CollisionBsps) FoldNegation(cg);
                        if (rdef.InstancedGeometry != null) foreach (var ig in rdef.InstancedGeometry) FoldNegation(ig.CollisionInfo);
                        _log.Add($"collision: {tag.Name}: {negated} surface plane negations folded into plane indices");
                        TagFixups.Fix(rdef);   // MOPP code and other per-game values inside the resource
                        var di = new BDatum(0xC000, _next++);
                        if (PackDefinition(rdef, "structure_bsp_tag_resources", 0x4, di, self, $"{tag.Name}.{tag.Group}/CollisionBspResource")) { _done[sbsp.CollisionBspResource] = di; Converted++; }
                    }
                }
                if (def is ScenarioLightmap sl && sl.Lightmaps != null)
                    foreach (var lm in sl.Lightmaps) ConvertGeometry(tag, lm.Geometry, self, "Lightmaps");
                // render geometry anywhere at the top level of the tag (structure BSP, render model, lightmap BSP, ...)
                foreach (var f in def.GetType().GetFields())
                    if (f.FieldType == typeof(TagTool.Geometry.RenderGeometry) && f.GetValue(def) is TagTool.Geometry.RenderGeometry rg && rg.Resource != null && !_done.ContainsKey(rg.Resource))
                    {
                        var gdef = GeoDef(rg, tag.Name);
                        if (gdef == null) { _log.Add($"geometry {tag.Name}.{tag.Group}/{f.Name}: no resource"); continue; }
                        var di = new BDatum(0xC000, _next++);
                        var er = GeometryConvert.Convert(gdef, _cache.Version, _cache.Platform, di, self, _sink, _log, $"{tag.Name}.{tag.Group}/{f.Name}");
                        if (er != null) { _done[rg.Resource] = di; Converted++; }
                    }
            }
            catch (Exception ex) { _log.Add($"resources of {tag.Name}.{tag.Group}: {ex.Message}"); }
        }

        // a tag-style resource definition (structure BSP collision etc.): TagTool writes it in Halo 3 360 layout; structs
        // holding pointers go to the definition ("info", resource address 0x2...), leaf arrays to the page (0x4...)
        bool PackDefinition(object rdef, string type, byte flags, BDatum id, BDatum parent, string where)
        {
            var ser = new TagTool.Serialization.TagSerializer(CacheVersion.Halo3Retail, CachePlatform.Original, TagTool.IO.EndianFormat.BigEndian);
            var ctx = new H3Context(_cache, t => new BDatum(0xFFFFFFFF), Pre);
            ser.Serialize(ctx, rdef);
            if (ctx.MainBlock == null) { _log.Add($"resource {where}: nothing serialized"); return false; }
            var blocks = ctx.Blocks; var byOff = blocks.ToDictionary(b => b.StreamOffset);
            var order = new List<H3Context.Block>(); var seen = new HashSet<long>();
            void Visit(H3Context.Block b) { if (b == null || !seen.Add(b.StreamOffset)) return; order.Add(b); foreach (var (_, target) in b.Pointers) Visit(byOff.TryGetValue(target, out var c) ? c : null); }
            Visit(ctx.MainBlock);
            var info = new List<byte>(); var raw = new List<byte>(); var place = new Dictionary<long, uint>();
            foreach (var b in order)
            {
                bool st = b == ctx.MainBlock || b.Pointers.Count > 0; var list = st ? info : raw;
                int al = (int)Math.Max(4, b.Align); while (list.Count % Math.Max(16, al) != 0) list.Add(0);
                place[b.StreamOffset] = (st ? 0x20000000u : 0x40000000u) | (uint)list.Count; list.AddRange(b.Stream.ToArray());
            }
            var infoArr = info.ToArray(); var fix = new List<ResourceFixup>();
            foreach (var b in order.Where(b => b == ctx.MainBlock || b.Pointers.Count > 0))
            {
                int baseAt = (int)(place[b.StreamOffset] & 0x1FFFFFFF);
                foreach (var (at, target) in b.Pointers)
                {
                    infoArr[baseAt + at] = 0; infoArr[baseAt + at + 1] = 0; infoArr[baseAt + at + 2] = 0; infoArr[baseAt + at + 3] = 0;
                    if (place.TryGetValue(target, out var to)) fix.Add(new ResourceFixup { Offset = baseAt + at, Address = to });
                }
            }
            var er = new ExtractedResourceInfo(id) { Flags = flags, Type = type, Info = infoArr, ResourceBits = raw.Count > 0 ? 1 : 0, BaseDefinitionAddress = (int)place[ctx.MainBlock.StreamOffset], OriginalParentTagIndex = parent, Location = new ExtractedResourcePointer() };
            er.ResourceFixups.AddRange(fix);
            if (raw.Count > 0) { er.Location.OriginalPrimaryPageIndex = _sink.Page(raw.ToArray(), true, true); er.Location.PrimaryOffset = 0; }
            _sink.Add(er);
            _log.Add($"resource {where}: {order.Count} blocks, definition {infoArr.Length} bytes, data {raw.Count} bytes, {fix.Count} pointers");
            return true;
        }

        // one geometry definition per resource, read once, with Halo 3's 16-bit part offsets enforced (GeometryConvert.FixPartOffsets)
        readonly Dictionary<TagResourceReference, TagTool.Tags.Resources.RenderGeometryApiResourceDefinition> _geo = new Dictionary<TagResourceReference, TagTool.Tags.Resources.RenderGeometryApiResourceDefinition>();
        TagTool.Tags.Resources.RenderGeometryApiResourceDefinition GeoDef(TagTool.Geometry.RenderGeometry rg, string where)
        {
            if (rg?.Resource == null) return null;
            if (!_geo.TryGetValue(rg.Resource, out var d)) { d = _cache.ResourceCache.GetRenderGeometryApiResourceDefinition(rg.Resource); GeometryConvert.FixPartOffsets(rg, d, _log, where); _geo[rg.Resource] = d; }
            return d;
        }

        void ConvertGeometry(CachedTag tag, TagTool.Geometry.RenderGeometry rg, BDatum self, string field)
        {
            if (rg?.Resource == null || _done.ContainsKey(rg.Resource)) return;
            var gdef = GeoDef(rg, tag.Name);
            if (gdef == null) { _log.Add($"geometry {tag.Name}.{tag.Group}/{field}: no resource"); return; }
            var di = new BDatum(0xC000, _next++);
            if (GeometryConvert.Convert(gdef, _cache.Version, _cache.Platform, di, self, _sink, _log, $"{tag.Name}.{tag.Group}/{field}") != null) { _done[rg.Resource] = di; Converted++; }
        }

        void PrepareBitmap(CachedTag tag, Bitmap bitm, BDatum self)
        {
            if (bitm.HardwareTextures == null) return;
            for (int i = 0; i < bitm.HardwareTextures.Count; i++)
            {
                var r = bitm.HardwareTextures[i]; if (r == null) continue;
                var res = _cache.ResourceCache.GetBitmapTextureInteropResource(r);
                var d = res?.Texture?.Definition; if (d == null) { _log.Add($"bitmap {tag.Name} [{i}]: no texture data"); continue; }
                var b = d.Bitmap; int w = b.Width, h = b.Height, levels = Math.Max(1, (int)b.MipmapCount), type = (int)b.BitmapType, format = (int)b.Format, curve = (int)b.Curve;
                byte[] prim = d.PrimaryResourceData?.Data, sec = d.SecondaryResourceData?.Data;
                if (prim == null || prim.Length == 0) { _log.Add($"bitmap {tag.Name} [{i}]: empty primary data"); continue; }
                // texture arrays (Halo Online keeps the lightmap layer stacks as 3D textures; stock Halo 3 uses arrays,
                // Guardian: 1024x1024x8 DXT5, slices back to back): each slice recoded and tiled as a 2D texture, slices
                // concatenated in order, each padded to 4 KB; written as an array (type 3)
                bool array = (type == 1 || type == 3) && b.Depth > 1;
                if (!array && ((type != 0 && type != 2) || b.Depth > 1)) { _log.Add($"bitmap {tag.Name} [{i}]: type {type} depth {b.Depth} not converted yet"); continue; }
                if (array && (levels != 1 || prim.Length % b.Depth != 0)) { _log.Add($"bitmap {tag.Name} [{i}]: array with {levels} levels / {prim.Length} bytes for {b.Depth} slices not converted yet"); continue; }
                int outFormat; byte[] p360, s360;
                if (array)
                {
                    int slice = prim.Length / b.Depth; var all = new List<byte>(); outFormat = format;
                    for (int z = 0; z < b.Depth; z++)
                    {
                        var sp = new byte[slice]; Buffer.BlockCopy(prim, z * slice, sp, 0, slice); byte[] ss = null;
                        outFormat = Inject360.BitmapConverter.Recode(ref sp, ref ss, false, w, h, 1, format, 0);
                        var (t, _) = Inject360.BitmapConverter.Tile360(sp, null, false, w, h, 1, outFormat, true, 0);
                        all.AddRange(t); while (all.Count % 4096 != 0) all.Add(0);
                    }
                    if (!Inject360.BitmapConverter.Supported(outFormat)) { _log.Add($"bitmap {tag.Name} [{i}]: format {format} not supported yet"); continue; }
                    p360 = all.ToArray(); s360 = null; type = 3; if (curve == 0) curve = 3;
                    _log.Add($"bitmap {tag.Name} [{i}]: array {w}x{h}x{b.Depth} format {outFormat}, {p360.Length} bytes, fetch 0x{Inject360.BitmapConverter.FetchWord(outFormat, curve):X8}");
                }
                else
                {
                    outFormat = Inject360.BitmapConverter.Recode(ref prim, ref sec, false, w, h, levels, format, type);
                    if (!Inject360.BitmapConverter.Supported(outFormat)) { _log.Add($"bitmap {tag.Name} [{i}]: format {format} not supported yet"); continue; }
                    (p360, s360) = Inject360.BitmapConverter.Tile360(prim, null, false, w, h, levels, outFormat, true, type);
                }
                bool split = s360 != null;
                var di = new BDatum(0xC000, _next++);
                var ctl = new byte[64];
                var er = new ExtractedResourceInfo(di) { Flags = 0x2, Type = "bitmap_texture_interop_resource", Info = ctl, BaseDefinitionAddress = 0x20000034, OriginalParentTagIndex = self, Location = new ExtractedResourcePointer() };
                if (p360 != null) { Be32(ctl, 0x00, (uint)p360.Length); er.Location.OriginalPrimaryPageIndex = _sink.Page(p360); er.Location.PrimaryOffset = 0; er.ResourceFixups.Add(new ResourceFixup { Offset = 0x0C, Address = 0x40000000 }); }
                if (s360 != null) { Be32(ctl, 0x14, (uint)s360.Length); er.Location.OriginalSecondaryPageIndex = _sink.Page(s360); er.Location.SecondaryOffset = 0; er.ResourceFixups.Add(new ResourceFixup { Offset = 0x20, Address = 0x60000000 }); }
                Be16(ctl, 0x28, w); Be16(ctl, 0x2A, h); ctl[0x2C] = (byte)Math.Max(1, (int)b.Depth); ctl[0x2D] = (byte)levels; ctl[0x2E] = (byte)type; ctl[0x2F] = (byte)(split ? 1 : 0);
                Be32(ctl, 0x30, Inject360.BitmapConverter.FetchWord(outFormat, curve)); Be32(ctl, 0x3C, 0xB0063001);
                er.ResourceBits = (p360 != null ? 1 : 0) | (s360 != null ? 2 : 0);
                er.ResourceFixups.Add(new ResourceFixup { Offset = 0x34, Address = 0x20000000 });
                er.DefinitionFixups.Add(new ResourceDefinitionFixup { Offset = 0x20000034, Type = 2 });
                _sink.Add(er); _done[r] = di; Converted++;
                // the image entry, as on stock 360 images
                if (i < bitm.Images.Count)
                {
                    var im = bitm.Images[i];
                    im.Signature = new Tag("bitm"); im.PixelDataOffset = 0; im.PixelDataSize = 0; im.HighResPixelsOffsetOffset = 0; im.HighResPixelsSize = split ? s360.Length : 0;
                    im.HardwareFormat = -1; im.Format = (BitmapFormat)outFormat;
                    if (array) { im.Type = BitmapType.Array; im.Curve = (BitmapImageCurve)curve; }
                    im.XboxFlags = BitmapFlagsXbox.Xbox360PitchMemorySpacing | BitmapFlagsXbox.Xbox360ByteOrder | BitmapFlagsXbox.Xbox360TiledTexture | BitmapFlagsXbox.Xbox360CreatedCorrectlyHackForBumps | (split ? BitmapFlagsXbox.Xbox360HighResolutionOffsetIsValid : 0);
                }
            }
            bitm.InterleavedHardwareTextures?.Clear();
        }

        // serializer hook: resource references become resource fixups (converted) or null
        public object Pre(object obj, TagFieldAttribute info, H3Context.Block block)
        {
            if (obj is TagResourceReference r)
            {
                if (_done.TryGetValue(r, out var d)) { block.Resources.Add(((int)block.Stream.Position, d)); return new TagResourceReference { Gen3ResourceID = DatumHandle.None }; }
                Dropped++;
                return new TagResourceReference { Gen3ResourceID = DatumHandle.None };
            }
            return obj;
        }

        public bool Fixup(object res, int at, DataBlock db)
        {
            if (res is BDatum d) { db.ResourceFixups.Add(new DataBlockResourceFixup(d, at)); return true; }
            return false;
        }
    }

    // Fixes applied to every Halo Online definition before it is written in Halo 3 form.
    public static class TagFixups
    {
        public static CacheVersion SourceVersion; public static CachePlatform SourcePlatform; public static StringTable SourceStrings;
        public static readonly Dictionary<string, int> Counts = new Dictionary<string, int>();
        static readonly Dictionary<Type, System.Reflection.FieldInfo[]> _fields = new Dictionary<Type, System.Reflection.FieldInfo[]>();

        public static void Apply(CachedTag tag, object def, List<string> log)
        {
            Walk(def, 0);
            // per-mesh cluster visibility: Halo Online leaves most entries empty and the rest hold Havok MOPP code in the
            // post-Halo 3 encoding (TagTool converts only Halo 3 -> later, not back). Left out until generated for Halo 3;
            // the engine skips meshes beyond the table (the earlier Reach route booted without it).
            foreach (var f in def.GetType().GetFields())
                if (!(def is ScenarioStructureBsp) && f.GetValue(def) is TagTool.Geometry.RenderGeometry rg && rg.MeshClusterVisibility != null && rg.MeshClusterVisibility.Count > 0)
                { log.Add($"mesh cluster visibility left out: {tag.Name} {f.Name} {rg.MeshClusterVisibility.Count} entries, {rg.MeshClusterVisibility.Count(m => m.MoppCode?.Length > 0)} with data"); rg.MeshClusterVisibility.Clear(); }
            // Halo Online scripts use Halo Online's script function and type numbering, which is not Halo 3's: a converted
            // script can call a function slot Halo 3 does not have. Multiplayer scripts are left out until scripts are
            // converted by name.
            if (def is TagTool.Tags.Definitions.Scenario scn)
            {
                log.Add($"scenario scripts left out: {scn.Scripts?.Count ?? 0} scripts, {scn.Globals?.Count ?? 0} globals, {scn.ScriptExpressions?.Count ?? 0} expressions");
                scn.Scripts?.Clear(); scn.Globals?.Clear(); scn.ScriptExpressions?.Clear(); scn.ScriptingData?.Clear();
                scn.ScriptSourceFileReferences?.Clear(); scn.ScriptExternalFileReferences?.Clear();
                // Reach's soft kill volumes (warning, then kill if you stay) came through as ordinary kill triggers; Halo 3
                // kills on contact, so they are left out. Halo Online no longer carries Reach's flag; Reach names them
                // "kill_soft" (Reflection: 9 of 24, matching the Reach flag).
                if (scn.ScenarioKillTriggers != null && scn.TriggerVolumes != null)
                {
                    int before = scn.ScenarioKillTriggers.Count;
                    scn.ScenarioKillTriggers.RemoveAll(k => k.TriggerVolume >= 0 && k.TriggerVolume < scn.TriggerVolumes.Count && (SourceStrings?.GetString(scn.TriggerVolumes[k.TriggerVolume].Name) ?? "").Contains("soft"));
                    log.Add($"kill triggers: {scn.ScenarioKillTriggers.Count} kept, {before - scn.ScenarioKillTriggers.Count} soft left out (Halo 3 has no soft kill)");
                }
                scn.ScenarioSafeTriggers?.Clear();
                if (Environment.GetEnvironmentVariable("HO2H3_NO_KILL") != null) { scn.ScenarioKillTriggers?.Clear(); log.Add("kill triggers: all left out (HO2H3_NO_KILL diagnostic)"); }
            }
        }

        static System.Reflection.FieldInfo[] Fields(Type t)
        {
            if (!_fields.TryGetValue(t, out var f)) _fields[t] = f = t.GetFields(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance);
            return f;
        }

        // TagTool keeps some values as one field per game (GameObjectType16: Halo3Retail, Halo3ODST, HaloOnline ...).
        // Reading Halo Online fills only the Halo Online field; the Halo 3 field is filled here by enum member name.
        static void Walk(object o, int depth)
        {
            if (o == null || depth > 24) return;
            var t = o.GetType();
            if (o is System.Collections.IList list)
            {
                var et = t.IsArray ? t.GetElementType() : (t.IsGenericType ? t.GetGenericArguments()[0] : null);
                if (et == null || !typeof(TagStructure).IsAssignableFrom(et)) return;
                foreach (var e in list) Walk(e, depth + 1);
                return;
            }
            if (o is TagFunction tf) { tf.Data = FunctionToBigEndian(tf.Data); return; }
            if (o is TagTool.Havok.TagHkpMoppCode mc && mc.Data != null && mc.Data.Count > 0) MoppToHalo3(mc.Data);
            if (!(o is TagStructure)) return;
            var fs = Fields(t);
            var h3 = fs.FirstOrDefault(f => f.Name == "Halo3Retail" && f.FieldType.IsEnum);
            if (h3 != null)
            {
                var src = fs.FirstOrDefault(f => f != h3 && f.FieldType.IsEnum && f.GetCustomAttributes(typeof(TagFieldAttribute), false).FirstOrDefault() is TagFieldAttribute a && CacheVersionDetection.TestAttribute(a, SourceVersion, SourcePlatform));
                if (src != null)
                {
                    var v = (Enum)src.GetValue(o); var key = t.Name;
                    if (Map(v, h3.FieldType, out var nv)) { h3.SetValue(o, nv); key += " converted"; } else key += $" no Halo 3 value for {v}";
                    Counts[key] = Counts.TryGetValue(key, out var n) ? n + 1 : 1;
                }
            }
            foreach (var f in fs)
            {
                var ft = f.FieldType;
                if (ft.IsPrimitive || ft.IsEnum || ft == typeof(string) || ft == typeof(byte[])) continue;
                if (typeof(TagStructure).IsAssignableFrom(ft) || typeof(System.Collections.IList).IsAssignableFrom(ft)) Walk(f.GetValue(o), depth + 1);
            }
        }

        // function curves are typed byte streams: Halo Online's are little-endian, the 360's big-endian. TagTool's own
        // reader (TagFunction.ParseTagFunctionData) walks them field by field; here it writes big-endian.
        static readonly System.Reflection.MethodInfo _parseFn = typeof(TagFunction).GetMethod("ParseTagFunctionData", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
        public static int FunctionsSwapped;
        static byte[] FunctionToBigEndian(byte[] data)
        {
            if (data == null || data.Length == 0) return data;
            var result = new byte[data.Length];
            using (var r = new TagTool.IO.EndianReader(new System.IO.MemoryStream(data), TagTool.IO.EndianFormat.LittleEndian))
            using (var w = new TagTool.IO.EndianWriter(new System.IO.MemoryStream(result), TagTool.IO.EndianFormat.BigEndian))
            {
                var h = new TagFunction.TagFunctionHeader(); h.Read(r); h.Write(w);
                _parseFn.Invoke(null, new object[] { h.Opcode, r, w });
                if (h.Interpolated()) _parseFn.Invoke(null, new object[] { h.Opcode, r, w });
                while (!r.EOF && r.BaseStream.Length - r.BaseStream.Position >= 4) w.Write(r.ReadSingle());
            }
            FunctionsSwapped++;
            return result;
        }

        // Havok MOPP code (physics lookup trees for level and instance collision) is a byte stream, but its 32-bit shape
        // keys (opcodes 0x0B, 0x53) use the post-Halo 3 layout in Halo Online; Halo 3 360 keeps the original layout.
        // Opcode lengths and the key re-encoding as in ReachPort Havok.MoppCode (the project's collision notes);
        // TagTool's HavokConverter.ConvertMoppCodes does the opposite direction.
        static readonly Dictionary<int, int> MoppLen = BuildMoppLen();
        static Dictionary<int, int> BuildMoppLen()
        {
            var d = new Dictionary<int, int> { [0] = 0, [5] = 1, [6] = 2, [7] = 3, [8] = 4, [9] = 1, [10] = 2, [11] = 4, [12] = 2, [13] = 5 };
            for (int i = 1; i <= 4; i++) d[i] = 3;
            for (int i = 0x10; i < 0x1D; i++) d[i] = 3;
            for (int i = 0x20; i < 0x23; i++) d[i] = 2;
            for (int i = 0x23; i < 0x26; i++) d[i] = 6;
            for (int i = 0x26; i < 0x29; i++) d[i] = 2;
            for (int i = 0x29; i < 0x2C; i++) d[i] = 6;
            for (int i = 0x30; i < 0x50; i++) d[i] = 0;
            for (int i = 0; i < 4; i++) { d[0x50 + i] = i + 1; d[0x54 + i] = i + 1; }
            for (int i = 0x60; i < 0x64; i++) d[i] = 1;
            for (int i = 0x64; i < 0x68; i++) d[i] = 2;
            for (int i = 0x68; i < 0x6C; i++) d[i] = 4;
            return d;
        }
        public static int MoppsConverted, MoppsFailed;
        static void MoppToHalo3(IList<byte> o)
        {
            var b = o.ToArray(); int at = 0;
            while (at < b.Length)
            {
                int op = b[at];
                if (!MoppLen.TryGetValue(op, out int n) || at + n + 1 > b.Length) { MoppsFailed++; return; }
                if (op == 0x0B || op == 0x53)
                {
                    uint key = (uint)(b[at + 1] << 24 | b[at + 2] << 16 | b[at + 3] << 8 | b[at + 4]);
                    if ((key & 0x83FF0000) != 0) { MoppsFailed++; return; }
                    key = (key & 0x60000000) | (((key >> 26) & 7) << 16) | (key & 0xFFFF);
                    b[at + 1] = (byte)(key >> 24); b[at + 2] = (byte)(key >> 16); b[at + 3] = (byte)(key >> 8); b[at + 4] = (byte)key;
                }
                at += n + 1;
            }
            for (int i = 0; i < b.Length; i++) o[i] = b[i];
            MoppsConverted++;
        }

        public static void Fix(object o) => Walk(o, 0);

        static bool Map(Enum v, Type target, out object result)
        {
            result = null;
            if (target.GetCustomAttributes(typeof(FlagsAttribute), false).Length > 0)
            {
                ulong bits = 0; ulong src = Convert.ToUInt64(v);
                foreach (Enum m in Enum.GetValues(v.GetType()))
                {
                    ulong mb = Convert.ToUInt64(m); if (mb == 0 || (src & mb) != mb || (mb & (mb - 1)) != 0) continue;
                    if (Enum.TryParse(target, m.ToString(), out var tm)) bits |= Convert.ToUInt64(tm); else return false;
                }
                result = Enum.ToObject(target, bits); return true;
            }
            if (Enum.TryParse(target, v.ToString(), out var r) && Enum.IsDefined(target, r)) { result = r; return true; }
            return false;
        }
    }
}
