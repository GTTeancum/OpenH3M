// Halo Online resources -> Halo 3 360 resources.
// Converted before a tag is serialized (Prepare, by group) and remembered by reference identity; the serializer hook
// (Pre) then writes each converted reference as a resource fixup, any other as null.
//   bitmaps: Halo Online keeps every level linear and little-endian in the primary data (PC D3D9); Inject360's
//            BitmapConverter tiles it for the 360 (Xenos layout, byte order, DXN bias) and the 64-byte 360 texture
//            control is written as Inject360 does for stock 360 textures.
using System;
using TagTool.Geometry.BspCollisionGeometry;
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
                        LeafClusters.OrigTree = null; LeafClusters.OrigLeafCluster = null;
                        if (rdef.LargeCollisionBsps?.Count > 0 && sbsp.Leaves != null && rdef.LargeCollisionBsps[0].Leaves?.Count == sbsp.Leaves.Count)
                        { LeafClusters.OrigTree = rdef.LargeCollisionBsps[0]; LeafClusters.OrigLeafCluster = sbsp.Leaves.Select(l => l.ClusterNew).ToArray(); }
                        if (rdef.LargeCollisionBsps != null && rdef.LargeCollisionBsps.Count > 0)
                        {
                            var rz = new TagTool.Geometry.BspCollisionGeometry.Utils.ResizeCollisionBSP();
                            if (rdef.CollisionBsps == null) rdef.CollisionBsps = new TagBlock<TagTool.Geometry.BspCollisionGeometry.CollisionGeometry>(CacheAddressType.Definition);
                            foreach (var lb0 in rdef.LargeCollisionBsps)
                            {
                                var lb = lb0;
                                if (!Halo3Limits.Fits(lb, out string over)) _log.Add($"collision: {tag.Name}: large collision BSP over Halo 3's own limits ({over})");
                                else if (!rz.collision_bsp_check_counts(lb)) _log.Add($"collision: {tag.Name}: large collision BSP kept as shipped (within Halo 3's own limits; nodes {lb.Bsp3dNodes.Count}, leaves {lb.Leaves.Count}); TagTool's lower caps not applied");
                                if (!Halo3Limits.Fits(lb, out _))
                                {
                                    // the tree (not the surfaces) is usually what overflows: Halo Online's comes from TagTool's supernode
                                    // conversion and is larger than one built directly. Rebuild it from the same surfaces with TagTool's
                                    // builder and keep it if it fits.
                                    int n0 = lb.Bsp3dNodes?.Count ?? 0; var rebuilt = lb;
                                    bool ok = false;
                                    try { ok = new TagTool.Geometry.BspCollisionGeometry.Utils.LargeCollisionBSPBuilder().generate_bsp(ref rebuilt, false) && rz.collision_bsp_check_counts(rebuilt); } catch (Exception ex) { _log.Add($"collision: rebuild of {tag.Name} failed: {ex.Message}"); }
                                    _log.Add($"collision: large collision BSP of {tag.Name} exceeds Halo 3 limits (nodes {n0}, surfaces {lb.Surfaces?.Count}, edges {lb.Edges?.Count}, vertices {lb.Vertices?.Count}); rebuilt tree: nodes {rebuilt.Bsp3dNodes?.Count}, leaves {rebuilt.Leaves?.Count}, 2D nodes {rebuilt.Bsp2dNodes?.Count}, 2D refs {rebuilt.Bsp2dReferences?.Count} -> {(ok ? "fits" : "still too large")}");
                                    if (!ok)
                                    {
                                        // still too large: simplify the collision mesh itself (CollisionSimplify.cs)
                                        LargeCollisionBspBlock simp = null;
                                        try { simp = CollisionSimplify.Run(_cache, lb, tag.Name, _log); } catch (Exception ex) { _log.Add($"collision simplify: {tag.Name} failed: {ex}"); }
                                        if (simp == null) continue;
                                        rebuilt = simp;
                                    }
                                    lb = rebuilt;
                                }
                                rdef.CollisionBsps.Add(Halo3Limits.Shrink(rz, lb));
                            }
                            _log.Add($"collision: {tag.Name}: {rdef.LargeCollisionBsps.Count} large collision BSP(s) -> {rdef.CollisionBsps.Count} Halo 3 collision BSP(s)");
                            rdef.LargeCollisionBsps.Clear();
                        }
                        // Reach-style two-sided surface pairs -> one two-sided surface, as stock (TwoSided.cs)
                        {
                            int r0 = TwoSided.Removed, b0 = TwoSided.Rebuilt, f0 = TwoSided.Failed;
                            // not the structure collision BSP: rebuilding its tree breaks the leaf -> cluster table the camera uses (hall of
                            // mirrors in Sword Base and Breakneck, user play test 2026-11-23); the in-place removal (default) keeps the tree
                            if (rdef.CollisionBsps != null && (Environment.GetEnvironmentVariable("HO2H3_TWOSIDED_REBUILD") != "1" || Environment.GetEnvironmentVariable("HO2H3_TWOSIDED_STRUCTURE") == "1")) for (int i = 0; i < rdef.CollisionBsps.Count; i++) rdef.CollisionBsps[i] = TwoSided.Fix(rdef.CollisionBsps[i]);
                            if (rdef.InstancedGeometry != null) foreach (var ig in rdef.InstancedGeometry) if (ig.CollisionInfo != null) ig.CollisionInfo = TwoSided.Fix(ig.CollisionInfo);
                            _log.Add($"two-sided: {tag.Name}: {TwoSided.Removed - r0} negated copies removed, {TwoSided.Rebuilt - b0} collision geometries rebuilt, {TwoSided.Failed - f0} left as they were (rebuild failed)");
                        }
                        if (rdef.InstancedGeometry != null) InstanceTrees.Rebuild(rdef.InstancedGeometry, tag.Name, _log);   // Halo 3 solid-space trees (InstanceTrees.cs)
                        Ramps.Build(sbsp, rdef, tag.Name, _log);   // invisible ramps over bare steps (before MOPPs are generated)
                        if (rdef.CollisionBsps != null && rdef.CollisionBsps.Count > 0) LeafClusters.Fix(sbsp, rdef.CollisionBsps[0], tag.Name, _log);   // leaf -> cluster table for the shipped tree
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
                        InstanceSpheres.Fix(sbsp, rdef, tag.Name, _log);
                        InstancePhysics.Fix(sbsp, rdef, tag.Name, _log);   // stock instance physics shape values (player collision)   // definition / instance bounding spheres (before the cluster MOPPs)
                        ClusterMopps.Build(tag, sbsp, rdef, _log);
                        if (Environment.GetEnvironmentVariable("HO2H3_EMPTY_CLUSTER_MOPP") == "1" && sbsp.Clusters != null)
                        {
                            // as Halo 3's own tools leave it (Beaver Creek via H3EK: every cluster's instanced geometry MOPP empty)
                            foreach (var cl in sbsp.Clusters) if (cl.InstancedGeometryPhysics != null) { cl.InstancedGeometryPhysics.MoppCodes = new List<TagTool.Havok.TagHkpMoppCode>(); cl.InstancedGeometryPhysics.StructureBsp = null; }
                            _log.Add($"cluster MOPP: {tag.Name}: left empty (HO2H3_EMPTY_CLUSTER_MOPP)");
                        }
                        // Halo Online instances flagged "not for render" (collision-only copies, merged duplicates) are skipped
                        // when drawing; Halo 3 has no such flag (the same bit is another setting), so they were drawn on top
                        // of the visible originals: z-fighting everywhere on Icebox (user play test 2026-11-23). They are
                        // taken out of the draw lists (cluster mesh instance buckets) and the bit is cleared; collision stays.
                        {
                            const ushort NotForRender = 0x40;
                            var hidden = new HashSet<int>(Enumerable.Range(0, sbsp.InstancedGeometryInstances?.Count ?? 0).Where(i => ((ushort)sbsp.InstancedGeometryInstances[i].Flags & NotForRender) != 0));
                            // map cfg "nodraw <structure BSP name> <instance index,...>": drawn duplicates (a merged copy and the
                            // separate pieces it repeats, coincident triangles) that fight in Halo 3 because each piece's
                            // vertices are compressed against its own bounds, so the copies land at slightly different depths
                            // (Icebox, measured with tools\map-review coplanar check). Taken out of the draw lists; collision stays.
                            var noDraw = new HashSet<int>();
                            foreach (var spec in (Environment.GetEnvironmentVariable("HO2H3_NODRAW") ?? "").Split(';', StringSplitOptions.RemoveEmptyEntries))
                            {
                                var parts = spec.Trim().Split(' ', 2, StringSplitOptions.RemoveEmptyEntries);
                                if (parts.Length == 2 && string.Equals(parts[0], tag.Name, StringComparison.OrdinalIgnoreCase))
                                    foreach (var x in parts[1].Split(',', StringSplitOptions.RemoveEmptyEntries)) if (int.TryParse(x.Trim(), out int ii) && ii >= 0 && ii < (sbsp.InstancedGeometryInstances?.Count ?? 0)) noDraw.Add(ii);
                            }
                            int nd0 = hidden.Count; hidden.UnionWith(noDraw);
                            int removed = 0;
                            if (hidden.Count > 0 && sbsp.Geometry?.Meshes != null)
                                foreach (var mesh in sbsp.Geometry.Meshes)
                                {
                                    if (mesh.InstanceBuckets == null) continue;
                                    foreach (var bk in mesh.InstanceBuckets) { int n0 = bk.Instances.Count; bk.Instances.RemoveAll(x => hidden.Contains(x.InstanceIndex)); removed += n0 - bk.Instances.Count; }
                                    mesh.InstanceBuckets.RemoveAll(bk => bk.Instances.Count == 0);
                                }
                            foreach (var i in hidden) sbsp.InstancedGeometryInstances[i].Flags = (TagTool.Geometry.BspCollisionGeometry.InstancedGeometryInstance.InstancedGeometryFlags)((ushort)sbsp.InstancedGeometryInstances[i].Flags & ~NotForRender);
                            if (hidden.Count > 0) _log.Add($"not-for-render instances: {tag.Name}: {hidden.Count} instances taken out of the draw lists ({removed} bucket entries), collision kept");
                            if (noDraw.Count > 0) _log.Add($"nodraw: {tag.Name}: {noDraw.Count} drawn duplicates named in the map cfg taken out of the draw lists ({hidden.Count - nd0} not already hidden), collision kept");
                            // drawable instances in no cluster mesh's bucket are never drawn in Halo 3 (Breakneck: a bridge
                            // floor under a spawn; user play test 2026-11-23). Each goes into the bucket list of the cluster
                            // holding its centre (else the nearest cluster), joining a bucket of its definition if there is one.
                            var inst2 = sbsp.InstancedGeometryInstances; var inBucket = new HashSet<int>();
                            foreach (var m in sbsp.Geometry.Meshes) if (m.InstanceBuckets != null) foreach (var bk in m.InstanceBuckets) foreach (var x in bk.Instances) inBucket.Add(x.InstanceIndex);
                            int added = 0;
                            for (int i = 0; i < (inst2?.Count ?? 0); i++)
                            {
                                if (inBucket.Contains(i) || hidden.Contains(i)) continue;
                                int d = inst2[i].DefinitionIndex; if (d < 0 || d >= rdef.InstancedGeometry.Count) continue;
                                int mi = rdef.InstancedGeometry[d].MeshIndex; if (mi < 0 || mi >= sbsp.Geometry.Meshes.Count || sbsp.Geometry.Meshes[mi].Parts.Count == 0) continue;
                                var c = inst2[i].WorldBoundingSphereCenter; int best = -1; double bestD = double.MaxValue;
                                for (int k = 0; k < sbsp.Clusters.Count; k++)
                                {
                                    var cl = sbsp.Clusters[k]; if (cl.MeshIndex < 0 || cl.MeshIndex >= sbsp.Geometry.Meshes.Count) continue;
                                    double dx = Math.Max(0, Math.Max(cl.BoundsX.Lower - c.X, c.X - cl.BoundsX.Upper)), dy = Math.Max(0, Math.Max(cl.BoundsY.Lower - c.Y, c.Y - cl.BoundsY.Upper)), dz = Math.Max(0, Math.Max(cl.BoundsZ.Lower - c.Z, c.Z - cl.BoundsZ.Upper));
                                    double dd = dx * dx + dy * dy + dz * dz; if (dd < bestD) { bestD = dd; best = k; }
                                }
                                if (best < 0) continue;
                                var mesh = sbsp.Geometry.Meshes[sbsp.Clusters[best].MeshIndex];
                                if (mesh.InstanceBuckets == null) mesh.InstanceBuckets = new List<TagTool.Geometry.Mesh.InstancedBucketBlock>();
                                var bucket = mesh.InstanceBuckets.FirstOrDefault(bk => bk.DefinitionIndex == d);
                                if (bucket == null) { bucket = new TagTool.Geometry.Mesh.InstancedBucketBlock { MeshIndex = (short)mi, DefinitionIndex = (short)d, Instances = new List<TagTool.Geometry.Mesh.InstancedBucketBlock.InstanceIndexBlock>() }; mesh.InstanceBuckets.Add(bucket); }
                                bucket.Instances.Add(new TagTool.Geometry.Mesh.InstancedBucketBlock.InstanceIndexBlock { InstanceIndex = (short)i }); added++;
                            }
                            if (added > 0) _log.Add($"draw lists: {tag.Name}: {added} drawable instances in no bucket added to their cluster's buckets");
                        }
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

        public static int PhysicsMoppData;
        // MOPP data = repeated [48-byte hkpMoppCode header][code, padded to 16]. Header: vtable u32 @0, size/flags u16 @4,
        // ref count u16 @6, (pad to 16), code info offset float4 @16, array data u32 @32, size u32 @36, capacity u32 @40, pad.
        // Source is little-endian (Halo Online PC); Halo 3 360 is big-endian. The code bytes are a byte stream (unchanged).
        // (TagTool's ConvertHkpMoppData treats the Halo 3 original-platform target as little-endian too, so it is not used.)
        static bool MoppDataToBigEndian(byte[] d)
        {
            int at = 0;
            while (at + 48 <= d.Length)
            {
                void Sw(int o, int n) { System.Array.Reverse(d, at + o, n); }
                uint size = System.BitConverter.ToUInt32(d, at + 36);
                if (size > d.Length - at - 48) return false;
                Sw(0, 4); Sw(4, 2); Sw(6, 2);
                for (int o = 16; o < 32; o += 4) Sw(o, 4);
                Sw(32, 4); Sw(36, 4); Sw(40, 4);
                at += 48 + (int)((size + 15) & ~15u);
            }
            return at == d.Length;
        }
        public static void Apply(CachedTag tag, object def, List<string> log)
        {
            Walk(def, 0);
            // sky visibility: Reach (so Halo Online) leaves clusters it judges sky-less at visible sky -1; Halo 3 draws no sky
            // from such a cluster and the open sky shows as hall of mirrors (stock maps mark every cluster: Guardian 26/26,
            // High Ground 42/43). With a single sky, every cluster sees it.
            if (def is TagTool.Tags.Definitions.Scenario sc && sc.SkyReferences?.Count == 1 && sc.ZoneSetPvs != null)
            {
                int fixedSky = 0;
                foreach (var zp in sc.ZoneSetPvs) if (zp.StructureBspPvs != null) foreach (var bp in zp.StructureBspPvs) if (bp.VisibleSkyIndices != null)
                    foreach (var si in bp.VisibleSkyIndices) if (si.SkyIndex < 0) { si.SkyIndex = 0; fixedSky++; }
                log.Add($"sky: {fixedSky} cluster(s) without a visible sky given the scenario's sky");
            }
            // scenario decals: Halo Online leaves "editing bound to bsp" at 255 (none); stock Halo 3 binds each decal to its BSP
            // (High Ground: 0). With one structure BSP every unbound decal is bound to it. (User play test 2026-11-23: decals
            // flickering on Icebox objects.)
            if (def is TagTool.Tags.Definitions.Scenario sc4 && sc4.Decals != null && sc4.StructureBsps?.Count == 1)
            {
                int bound = 0;
                foreach (var d in sc4.Decals) if (d.EditingBoundToBsp == 255) { d.EditingBoundToBsp = 0; bound++; }
                log.Add($"decals: {bound} of {sc4.Decals.Count} unbound decals bound to the single structure BSP");
            }
            // decals left out by map choice (cfg "nodecal <scenario> <source decal indices>", env HO2H3_NODECAL
            // "<scenario>=<i,j,...>;..."): overlapping decals listed by ho2h3 decaloverlap (Icebox, user 2026-11-24)
            // The structure BSP's clusters index the scenario decal block (runtime decal start/count, decals sorted by
            // cluster), so their ranges are renumbered to the kept decals: BSPs whose name starts with the scenario's.
            foreach (var spec in (Environment.GetEnvironmentVariable("HO2H3_NODECAL") ?? "").Split(';', StringSplitOptions.RemoveEmptyEntries))
            {
                int eq = spec.LastIndexOf('='); if (eq < 0) continue;
                string scnName = spec.Substring(0, eq).Trim();
                var drop = spec.Substring(eq + 1).Split(',', StringSplitOptions.RemoveEmptyEntries).Select(s => int.Parse(s.Trim())).ToHashSet();
                if (def is TagTool.Tags.Definitions.Scenario sc5 && sc5.Decals != null && string.Equals(scnName, tag.Name, StringComparison.OrdinalIgnoreCase))
                {
                    int before = sc5.Decals.Count;
                    if (drop.Any(i => i < 0 || i >= before)) throw new Exception($"nodecal: index outside {tag.Name}'s {before} decals");
                    sc5.Decals = sc5.Decals.Where((d, i) => !drop.Contains(i)).ToList();
                    log.Add($"decals: {before - sc5.Decals.Count} of {before} left out by map choice (nodecal)");
                }
                if (def is ScenarioStructureBsp sb5 && sb5.Clusters != null && tag.Name.StartsWith(scnName, StringComparison.OrdinalIgnoreCase))
                {
                    int Kept(int upTo) => upTo - drop.Count(i => i < upTo);   // kept decals before source index upTo
                    int changed = 0;
                    foreach (var cl in sb5.Clusters)
                    {
                        if (cl.RuntimeDecalCount <= 0 || cl.RuntimeDecalStartIndex < 0) continue;
                        int s0 = cl.RuntimeDecalStartIndex, e0 = s0 + cl.RuntimeDecalCount;
                        int s1 = Kept(s0), n1 = Kept(e0) - s1;
                        if (s1 != s0 || n1 != cl.RuntimeDecalCount) changed++;
                        cl.RuntimeDecalStartIndex = (short)(n1 > 0 ? s1 : -1); cl.RuntimeDecalCount = (short)n1;
                    }
                    log.Add($"decals: {changed} cluster decal ranges of {tag.Name} renumbered for left-out decals (nodecal)");
                }
            }
            // diagnostic: scale a render model's geometry through its compression bounds (HO2H3_SCALE_MODEL="<name regex>=<factor>")
            if (def is TagTool.Tags.Definitions.RenderModel rmd && Environment.GetEnvironmentVariable("HO2H3_SCALE_MODEL") is string smv && smv.Contains('='))
            {
                var re = new System.Text.RegularExpressions.Regex(smv.Substring(0, smv.LastIndexOf('=')), System.Text.RegularExpressions.RegexOptions.IgnoreCase);
                float f = float.Parse(smv.Substring(smv.LastIndexOf('=') + 1), System.Globalization.CultureInfo.InvariantCulture);
                if (re.IsMatch(tag.Name) && rmd.Geometry?.Compression != null)
                {
                    foreach (var c in rmd.Geometry.Compression) { c.X = new Bounds<float>(c.X.Lower * f, c.X.Upper * f); c.Y = new Bounds<float>(c.Y.Lower * f, c.Y.Upper * f); c.Z = new Bounds<float>(c.Z.Lower * f, c.Z.Upper * f); }
                    log.Add($"diagnostic: {tag.Name} geometry scaled by {f}");
                }
            }
            // diagnostic: every cluster attached to sky 0 (HO2H3_SKY_ALL=1)
            var skyAll = Environment.GetEnvironmentVariable("HO2H3_SKY_ALL") ?? "";
            if (skyAll != "")
            {
                if (skyAll.Contains("c") && def is ScenarioStructureBsp sbx && sbx.Clusters != null) { foreach (var cl in sbx.Clusters) cl.ScenarioSkyIndex = 0; log.Add($"diagnostic: {sbx.Clusters.Count} clusters attached to sky 0"); }
                if ((skyAll.Contains("a") || skyAll.Contains("n")) && def is TagTool.Tags.Definitions.Scenario sc3 && sc3.ZoneSetPvs != null)
                    foreach (var zp in sc3.ZoneSetPvs) if (zp.StructureBspPvs != null) foreach (var bp in zp.StructureBspPvs) if (bp.AttachedSkyIndices != null) foreach (var si in bp.AttachedSkyIndices) si.SkyIndex = (sbyte)(skyAll.Contains("n") ? -1 : 0);
            }
            // diagnostic: every cluster sees every cluster (HO2H3_PVS_ALL=1)
            if (def is TagTool.Tags.Definitions.Scenario sc2 && Environment.GetEnvironmentVariable("HO2H3_PVS_ALL") == "1" && sc2.ZoneSetPvs != null)
            {
                int set = 0;
                foreach (var zp in sc2.ZoneSetPvs) if (zp.StructureBspPvs != null) foreach (var bp in zp.StructureBspPvs)
                    foreach (var list in new[] { bp.ClusterPvs, bp.ClusterPvsDoorsClosed }) if (list != null)
                        foreach (var cp in list) if (cp.ClusterPvsBitVectors != null) foreach (var bv in cp.ClusterPvsBitVectors) if (bv.Bits != null)
                            foreach (var d in bv.Bits) { d.Bits = (TagTool.Tags.Definitions.Scenario.ZoneSetPvsBlock.BitVectorDword.DwordBits)unchecked((int)0xFFFFFFFF); set++; }
                log.Add($"diagnostic: cluster visibility set to all ({set} words)");
            }
            // physics model MOPP data is a raw byte array of Havok MOPP code headers + code in the source byte order;
            // TagTool's converter reads each header in the source order and writes it in Halo 3 360's (big-endian)
            // (symptom when left little-endian: read fault in the physics model loader 0x821D00C8)
            if (def is TagTool.Tags.Definitions.PhysicsModel pm && pm.MoppData != null && pm.MoppData.Length > 0)
            {
                if (MoppDataToBigEndian(pm.MoppData)) PhysicsMoppData++; else log.Add($"physics MOPP data not convertible: {tag.Name}");
            }
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
