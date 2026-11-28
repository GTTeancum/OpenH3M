// physprobe <pak> <sbsp name>: Halo Online instance definitions: collision surfaces vs Reach-style polyhedra (ExtraData),
// with the names of instances that use each definition
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using TagTool.Common;
using TagTool.Geometry.BspCollisionGeometry;
using TagTool.Cache;
using TagTool.Tags;
using TagTool.Tags.Definitions;

namespace Ho2H3
{
    static class PhysProbe
    {
        public static int Run(string[] a)
        {
            if (a.Length > 3 && a[3] == "flags")
            {
                // collision surface flag counts (structure and instances) of a structure BSP in any cache: physprobe <map|pak> <sbsp> flags
                var hc = a[1].EndsWith(".map", StringComparison.OrdinalIgnoreCase) ? GameCache.Open(new FileInfo(a[1])) : Program.OpenPak(a[1]);
                using (var st = hc is GameCacheModPackage ? Program.OpenStream(hc) : hc.OpenCacheRead())
                {
                    var sb = hc.Deserialize<ScenarioStructureBsp>(st, hc.TagCache.GetTag(a[2], "sbsp"));
                    var r = hc.ResourceCache.GetStructureBspTagResources(sb.CollisionBspResource);
                    var cnt = new System.Collections.Generic.Dictionary<string, int>();
                    void Add(string k) { cnt[k] = cnt.TryGetValue(k, out var n) ? n + 1 : 1; }
                    foreach (var c in r.CollisionBsps ?? new()) foreach (var sf in c.Surfaces) Add("structure " + sf.Flags);
                    foreach (var c in r.LargeCollisionBsps ?? new()) foreach (var sf in c.Surfaces) Add("structure " + sf.Flags);
                    int invInst = 0;
                    foreach (var ig in r.InstancedGeometry ?? new()) { bool inv = false; foreach (var sf in ig.CollisionInfo?.Surfaces ?? new()) { Add("instance " + sf.Flags); if ((sf.Flags & TagTool.Geometry.BspCollisionGeometry.SurfaceFlags.Invisible) != 0) inv = true; } if (inv) invInst++; }
                    foreach (var kv in cnt.OrderByDescending(k => k.Value)) Console.WriteLine($"{kv.Value,7} {kv.Key}");
                    Console.WriteLine($"instance definitions with invisible surfaces: {invInst} of {r.InstancedGeometry?.Count}");
                }
                return 0;
            }
            if (a.Length > 5 && a[3] == "placedump")
            {
                // every field (nested structures expanded one level) of placements a[5..] of scenario block a[4]
                var hc = Program.OpenPak(a[1]);
                using (var st = Program.OpenStream(hc))
                {
                    var sc = hc.Deserialize<Scenario>(st, hc.TagCache.GetTag(a[2], "scnr"));
                    var l = typeof(Scenario).GetField(a[4]).GetValue(sc) as System.Collections.IList;
                    string V(object v) => v is StringId sid ? hc.StringTable.GetString(sid) : v is CachedTag ct ? ct.Name : v is System.Collections.IList il ? $"[{il.Count}]" : v?.ToString();
                    foreach (var idx in a[5].Split(',').Select(int.Parse))
                    {
                        if (idx >= l.Count) continue; var o = l[idx];
                        Console.WriteLine($"== {a[4]}[{idx}]");
                        foreach (var f in o.GetType().GetFields())
                        {
                            var v = f.GetValue(o);
                            if (v != null && !(v is string) && !f.FieldType.IsPrimitive && !f.FieldType.IsEnum && f.FieldType.Namespace?.StartsWith("TagTool.Tags") == true && !(v is System.Collections.IList) && !(v is CachedTag))
                                Console.WriteLine($"  {f.Name}: " + string.Join(" ", v.GetType().GetFields().Select(g => g.Name + "=" + V(g.GetValue(v)))));
                            else Console.WriteLine($"  {f.Name} = {V(v)}");
                        }
                    }
                }
                return 0;
            }
            if (a.Length > 4 && a[3] == "drawn")
            {
                // instances the game draws: every instance index in any mesh's instance buckets -> file a[4] ("B <index>")
                var hc = Program.OpenPak(a[1]);
                using (var st = Program.OpenStream(hc))
                {
                    var sb = hc.Deserialize<ScenarioStructureBsp>(st, hc.TagCache.GetTag(a[2], "sbsp"));
                    var set = new SortedSet<int>();
                    foreach (var m in sb.Geometry.Meshes) foreach (var b in m.InstanceBuckets ?? new()) foreach (var i in b.Instances) set.Add(i.InstanceIndex);
                    System.IO.File.WriteAllLines(a[4], set.Select(i => "B " + i));
                    Console.WriteLine($"{set.Count} of {sb.InstancedGeometryInstances.Count} instances are in draw lists");
                }
                return 0;
            }
            if (a.Length > 3 && a[3] == "decs")
            {
                // decal systems whose name contains a[1]'s filter a[2]: system flags, per decal flags, pass, runtime fields, template
                var hc = Program.OpenPak(a[1]);
                using (var st = Program.OpenStream(hc))
                    foreach (var t in hc.TagCache.NonNull().Where(t => t.IsInGroup("decs") && t.Name.Contains(a[2])).Take(a.Length > 4 ? int.Parse(a[4]) : 12))
                    {
                        var d = hc.Deserialize<TagTool.Tags.Definitions.DecalSystem>(st, t);
                        foreach (var e in d.Decal)
                        {
                            var rm = e.RenderMethod; string tmpl = rm?.ShaderProperties?.Count > 0 ? rm.ShaderProperties[0].Template?.Name : "-";
                            string opts = rm?.Options == null ? "" : string.Join(",", rm.Options.Select(o => o.OptionIndex));
                            Console.WriteLine($"{t.Name}: system {d.Flags} | decal {e.Flags} pass {e.Pass} radius {e.Radius.Lower:0.00}-{e.Radius.Upper:0.00} clamp {e.ClampAngle:0.0} cull {e.CullAngle:0.0} spec {e.RuntimeSpecularMultiplier:0.00} aspect {e.RuntimeBitmapAspect:0.00} | template {System.IO.Path.GetFileName(tmpl ?? "-")} options {opts} sortlayer {rm?.SortLayer} flags {rm?.RenderFlags}");
                        }
                    }
                return 0;
            }
            if (a.Length > 3 && a[3] == "tagsize")
            {
                // tag memory: virtual base, tag section size, tag memory header, highest tag address
                var gc = (TagTool.Cache.GameCacheGen3)Program.OpenPak(a[1]);
                var h = (TagTool.Cache.CacheFileHeaderGen3)gc.BaseMapFile.Header;
                var secs = h.SectionTable.Sections.Select((x, i) => $"{(TagTool.Cache.CacheFileSectionType)i}={x.Size}");
                var tm = h.GetTagMemoryHeader();
                Console.WriteLine($"virtual base 0x{h.VirtualBaseAddress.Value:X}; sections {string.Join(" ", secs)}; tag memory header: " + string.Join(" ", tm.GetType().GetFields().Select(f => f.Name + "=" + f.GetValue(tm))) + $"; tag offsets max 0x{gc.TagCache.NonNull().Max(t => ((TagTool.Cache.Gen3.CachedTagGen3)t).Offset):X}");
                return 0;
            }
            if (a.Length > 3 && a[3] == "nulltags")
            {
                // tags with no data (offset 0) and whether a Forge palette entry or a palette object's own references name them
                var hc = Program.OpenPak(a[1]);
                var nul = hc.TagCache.NonNull().Where(t => t is TagTool.Cache.Gen3.CachedTagGen3 g && g.Offset == 0).ToList();
                Console.WriteLine($"{nul.Count} tags with no data of {hc.TagCache.NonNull().Count()}: " + string.Join(" | ", nul.Take(15).Select(t => t.Group.Tag + ":" + t.Name)));
                Console.WriteLine($"highest tag index {hc.TagCache.NonNull().Max(t => t.Index)}, tag table entries {hc.TagCache.Count}");
                if (hc is TagTool.Cache.GameCacheGen3 g3)
                {
                    var hh = (TagTool.Cache.CacheFileHeaderGen3)g3.BaseMapFile.Header; var tmh = hh.GetTagMemoryHeader();
                    uint lo = (uint)tmh.MemoryBufferOffset, hi = (uint)(tmh.MemoryBufferOffset + tmh.MemoryBufferSize);
                    var outside = hc.TagCache.NonNull().Where(t => { var o = ((TagTool.Cache.Gen3.CachedTagGen3)t).Offset; return o < lo || o >= hi; }).ToList();
                    Console.WriteLine($"tag data window 0x{lo:X}..0x{hi:X}; tags whose data lies outside it: {outside.Count}: " + string.Join(" | ", outside.Take(12).Select(t => $"{t.Index} {t.Group.Tag}:{t.Name} @0x{((TagTool.Cache.Gen3.CachedTagGen3)t).Offset:X}")));
                    var nullIdx = Enumerable.Range(0, hc.TagCache.Count).Where(i => { try { return hc.TagCache.GetTag((uint)i) == null; } catch { return true; } }).ToList();
                    Console.WriteLine($"empty tag table slots: {nullIdx.Count}: {string.Join(",", nullIdx.Take(10))}");
                }
                using (var st = Program.OpenStream(hc))
                {
                    var sc = hc.Deserialize<Scenario>(st, hc.TagCache.GetTag(a[2], "scnr"));
                    var set = new HashSet<int>(nul.Select(t => t.Index));
                    foreach (var f in typeof(Scenario).GetFields().Where(f => f.Name.StartsWith("Sandbox")))
                        foreach (var e in (f.GetValue(sc) as List<Scenario.SandboxObject>) ?? new())
                        {
                            if (e.Object == null) continue;
                            if (set.Contains(e.Object.Index)) Console.WriteLine($"palette {f.Name}: {e.Object.Name} HAS NO DATA");
                            if (a.Length > 4 && e.Object.Index >= int.Parse(a[4])) Console.WriteLine($"palette {f.Name}: {e.Object.Name} index {e.Object.Index}");
                            var h = hc.TagCache.GetTag(e.Object.Index);
                            var go = (TagTool.Tags.Definitions.GameObject)hc.Deserialize(st, e.Object);
                            var gm = go.Model; if (gm != null && (gm.Index < 0 || hc.TagCache.GetTag((uint)gm.Index) == null)) Console.WriteLine($"palette {f.Name}: {e.Object.Name} model index {gm.Index} EMPTY");
                            foreach (var r in new[] { go.Model, go.CollisionDamage, go.CreationEffect, go.MaterialEffects } ) if (r != null && set.Contains(r.Index)) Console.WriteLine($"palette {f.Name}: {e.Object.Name} references {r.Group.Tag}:{r.Name} WITH NO DATA");
                        }
                }
                return 0;
            }
            if (a.Length > 3 && a[3] == "objdump")
            {
                // scalar fields and references of object a[2] (any object group) and of its model
                var hc = Program.OpenPak(a[1]);
                using (var st = Program.OpenStream(hc))
                {
                    var t = hc.TagCache.NonNull().First(x => x.Name == a[2] && (x.IsInGroup("obje")));
                    var o = hc.Deserialize(st, t);
                    string V(object v) => v is StringId sid ? hc.StringTable.GetString(sid) : v is CachedTag ct ? ct.Group.Tag + ":" + ct.Name : v is System.Collections.IList il ? $"[{il.Count}]" : v?.ToString();
                    Console.WriteLine($"{t.Group.Tag}:{t.Name} index {t.Index}");
                    Console.WriteLine(string.Join(" ", o.GetType().GetFields().Select(f => f.Name + "=" + V(f.GetValue(o)))));
                    var go = (TagTool.Tags.Definitions.GameObject)o;
                    if (go.Model != null) { var m = hc.Deserialize(st, go.Model); Console.WriteLine("model: " + string.Join(" ", m.GetType().GetFields().Select(f => f.Name + "=" + V(f.GetValue(m))))); }
                    if (go.Model != null) { var mm = hc.Deserialize<TagTool.Tags.Definitions.Model>(st, go.Model); foreach (var d in mm.ModelObjectData ?? new()) Console.WriteLine("model object data: " + string.Join(" ", d.GetType().GetFields().Select(f => f.Name + "=" + V(f.GetValue(d))))); Console.WriteLine($"object bounding radius {go.BoundingRadius} offset {go.BoundingOffset}"); }
                }
                return 0;
            }
            if (a.Length > 3 && a[3] == "simtable")
            {
                // scenario simulation definition table (object definitions the game may create over the network, Forge
                // included) and which Forge palette objects are missing from it
                var hc = Program.OpenPak(a[1]);
                using (var st = Program.OpenStream(hc))
                {
                    var sc = hc.Deserialize<Scenario>(st, hc.TagCache.GetTag(a[2], "scnr"));
                    var tbl = sc.SimulationDefinitionTable ?? new();
                    var set = new HashSet<int>(tbl.Where(x => x.Tag != null).Select(x => x.Tag.Index));
                    var pal = typeof(Scenario).GetFields().Where(f => f.Name.StartsWith("Sandbox")).SelectMany(f => (f.GetValue(sc) as List<Scenario.SandboxObject>) ?? new()).Where(e => e.Object != null).Select(e => e.Object).ToList();
                    var idx = tbl.Where(x => x.Tag != null).Select(x => x.Tag.Index).ToList(); int desc = 0; for (int q = 1; q < idx.Count; q++) if (idx[q] < idx[q - 1]) desc++;
                    Console.WriteLine($"order: {desc} places where the tag index decreases; first {string.Join(",", idx.Take(8))}");
                    Console.WriteLine($"simulation definition table: {tbl.Count} entries; Forge palette objects {pal.Count}, missing from the table {pal.Count(o => !set.Contains(o.Index))}; groups: {string.Join(",", tbl.Where(x => x.Tag != null).GroupBy(x => x.Tag.Group.Tag.ToString()).Select(g => g.Key + "x" + g.Count()))}");
                }
                return 0;
            }
            if (a.Length > 3 && a[3] == "lightdata")
            {
                // block counts of each lightmap BSP data (Halo 3: scenario lightmap's inline Lightmaps; Halo Online: Lbsp tags)
                var hc = Program.OpenPak(a[1]);
                using (var st = Program.OpenStream(hc))
                {
                    var datas = new List<(string, TagTool.Tags.Definitions.ScenarioLightmapBspData)>();
                    foreach (var t in hc.TagCache.NonNull().Where(t => t.IsInGroup("Lbsp") && t.Name.Contains(a[2]))) datas.Add((t.Name, hc.Deserialize<TagTool.Tags.Definitions.ScenarioLightmapBspData>(st, t)));
                    foreach (var t in hc.TagCache.NonNull().Where(t => t.IsInGroup("sLdT") && t.Name.Contains(a[2])))
                    {
                        var sl = hc.Deserialize<TagTool.Tags.Definitions.ScenarioLightmap>(st, t);
                        foreach (var d in sl.Lightmaps ?? new()) datas.Add((t.Name, d));
                    }
                    foreach (var (n, d) in datas)
                        Console.WriteLine(n + ": " + string.Join(" ", d.GetType().GetFields().Where(f => f.GetValue(d) is System.Collections.IList).Select(f => f.Name + "=" + ((System.Collections.IList)f.GetValue(d)).Count)));
                }
                return 0;
            }
            if (a.Length > 4 && a[3] == "imopp")
            {
                // the Havok MOPP of the first instance definition whose instance name contains a[4]
                var hc = Program.OpenPak(a[1]);
                using (var st = Program.OpenStream(hc))
                {
                    var sb = hc.Deserialize<ScenarioStructureBsp>(st, hc.TagCache.GetTag(a[2], "sbsp"));
                    var r = hc.ResourceCache.GetStructureBspTagResources(sb.CollisionBspResource);
                    var x = sb.InstancedGeometryInstances.First(q => (hc.StringTable.GetString(q.Name) ?? "").Contains(a[4]));
                    var d = r.InstancedGeometry[x.DefinitionIndex];
                    Console.WriteLine($"instance {hc.StringTable.GetString(x.Name)} def {x.DefinitionIndex}: surfaces {d.CollisionInfo?.Surfaces?.Count}, MOPP codes {d.CollisionMoppCodes?.Count}");
                    foreach (var m in d.CollisionMoppCodes ?? new())
                    {
                        System.IO.File.WriteAllBytes(System.IO.Path.Combine(System.IO.Path.GetTempPath(), "imopp_" + a[4] + ".bin"), (m.Data ?? new()).ToArray());
                        try { var regen = TagTool.Havok.CollisionMoppGenerator.Generate(d.CollisionInfo); Console.WriteLine($"  regenerated by TagTool: info {regen.Info?.Offset} size {regen.Data?.Count} first {string.Join("", (regen.Data ?? new()).Take(24).Select(b => b.ToString("x2")))} | identical: {regen.Data != null && m.Data != null && regen.Data.SequenceEqual(m.Data)}"); } catch (Exception ex) { Console.WriteLine("  regen failed " + ex.Message); }
                        Console.WriteLine($"  refobj {m.ReferencedObject?.ReferenceCount} info {m.Info?.Offset} arraybase size {m.ArrayBase?.Size} cap 0x{m.ArrayBase?.CapacityAndFlags:X} data {m.Data?.Count} first {string.Join("", (m.Data ?? new()).Take(24).Select(b => b.ToString("x2")))}");
                        Console.WriteLine("  fields: " + string.Join(" ", m.GetType().GetFields().Select(f => f.Name + "=" + f.GetValue(m))));
                    }
                    Console.WriteLine("  def fields: " + string.Join(" ", d.GetType().GetFields().Where(f => !(f.GetValue(d) is System.Collections.IList)).Select(f => f.Name + "=" + f.GetValue(d))));
                }
                return 0;
            }
            if (a.Length > 4 && a[3] == "bspphys")
            {
                // every field of an instance's BspPhysics entries, two levels deep
                var hc = Program.OpenPak(a[1]);
                using (var st = Program.OpenStream(hc))
                {
                    var sb = hc.Deserialize<ScenarioStructureBsp>(st, hc.TagCache.GetTag(a[2], "sbsp"));
                    var x = sb.InstancedGeometryInstances.First(q => (hc.StringTable.GetString(q.Name) ?? "").Contains(a[4]));
                    void Dump(object o, string ind, int depth)
                    {
                        if (o == null) return;
                        foreach (var f in o.GetType().GetFields())
                        {
                            var v = f.GetValue(o);
                            if (v is System.Collections.IList l) { Console.WriteLine($"{ind}{f.Name}[{l.Count}]"); if (depth < 3) foreach (var e in l.Cast<object>().Take(2)) Dump(e, ind + "  ", depth + 1); }
                            else if (v != null && f.FieldType.Namespace?.StartsWith("TagTool") == true && !f.FieldType.IsEnum && !f.FieldType.IsPrimitive && depth < 3 && !(v is CachedTag)) { Console.WriteLine($"{ind}{f.Name}:"); Dump(v, ind + "  ", depth + 1); }
                            else Console.WriteLine($"{ind}{f.Name} = {v}");
                        }
                    }
                    Console.WriteLine(hc.StringTable.GetString(x.Name));
                    foreach (var bp in x.BspPhysics) Dump(bp, "  ", 0);
                }
                return 0;
            }
            if (a.Length > 3 && a[3] == "bspphysstats")
            {
                // tally of instance BspPhysics shape fields over all instances
                var hc = Program.OpenPak(a[1]);
                using (var st = Program.OpenStream(hc))
                {
                    var sb = hc.Deserialize<ScenarioStructureBsp>(st, hc.TagCache.GetTag(a[2], "sbsp"));
                    var tally = new Dictionary<string, int>(); int keyIsIndex = 0, n = 0;
                    for (int i = 0; i < sb.InstancedGeometryInstances.Count; i++)
                        foreach (var bp in sb.InstancedGeometryInstances[i].BspPhysics ?? new())
                        {
                            var g = bp.GeometryShape; n++;
                            string k = $"shapeType {g.CollisionGeometryShapeType} type {g.Type} weldingOff {g.DisableWelding} mopp type {bp.MoppBvTreeShape?.Type} aabb {(g.AABB_Half_Extents.I == 0 && g.AABB_Half_Extents.J == 0 && g.AABB_Half_Extents.K == 0 ? "ZERO" : "set")}";
                            if (n <= 3) Console.WriteLine($"  instance {i}: aabb centre {g.AABB_Center} half {g.AABB_Half_Extents} scale {g.Scale} model {g.Model?.Name} bsp {g.BspIndex}");
                            tally[k] = tally.TryGetValue(k, out int q) ? q + 1 : 1; if (g.CollisionGeometryShapeKey == i) keyIsIndex++;
                        }
                    Console.WriteLine($"{n} instance physics entries, key = instance index for {keyIsIndex}");
                    foreach (var kv in tally) Console.WriteLine($"  {kv.Value} x {kv.Key}");
                }
                return 0;
            }
            if (a.Length > 3 && a[3] == "sbspblocks")
            {
                // counts of every block in the structure BSP, its Physics struct and the first cluster's physics
                var hc = Program.OpenPak(a[1]);
                using (var st = Program.OpenStream(hc))
                {
                    var sb = hc.Deserialize<ScenarioStructureBsp>(st, hc.TagCache.GetTag(a[2], "sbsp"));
                    Console.WriteLine(string.Join(" ", sb.GetType().GetFields().Where(f => f.GetValue(sb) is System.Collections.IList).Select(f => f.Name + "=" + ((System.Collections.IList)f.GetValue(sb)).Count)));
                    if (sb.Physics != null) Console.WriteLine("Physics: " + string.Join(" ", sb.Physics.GetType().GetFields().Select(f => f.Name + "=" + (f.GetValue(sb.Physics) is System.Collections.IList l ? "[" + l.Count + "]" : f.GetValue(sb.Physics)))));
                    var c0 = sb.Clusters.FirstOrDefault(c => c.InstancedGeometryPhysics != null);
                    if (c0 != null) { var p = c0.InstancedGeometryPhysics; Console.WriteLine("cluster physics: " + string.Join(" ", p.GetType().GetFields().Select(f => f.Name + "=" + (f.GetValue(p) is System.Collections.IList l ? "[" + l.Count + "]" : f.GetValue(p))))); }
                    foreach (var g in sb.ClusterToInstanceGroupSpheres?.Take(2) ?? Enumerable.Empty<ScenarioStructureBsp.StructureInstanceClusterDefinition>()) Console.WriteLine("instance group: " + string.Join(" ", g.GetType().GetFields().Select(f => f.Name + "=" + (f.GetValue(g) is System.Collections.IList l ? "[" + l.Count + "]" : f.GetValue(g)))));
                }
                return 0;
            }
            if (a.Length > 3 && a[3] == "negstats")
            {
                // how plane negation is stored on collision surfaces: plane index bit 15 vs the PlaneNegated flag
                var hc = Program.OpenPak(a[1]);
                using (var st = Program.OpenStream(hc))
                {
                    var sb = hc.Deserialize<ScenarioStructureBsp>(st, hc.TagCache.GetTag(a[2], "sbsp"));
                    var r = hc.ResourceCache.GetStructureBspTagResources(sb.CollisionBspResource);
                    void Count(string what, IEnumerable<CollisionGeometry> gs)
                    {
                        int n = 0, bit = 0, flag = 0, both = 0;
                        foreach (var g in gs) foreach (var sf in g?.Surfaces ?? new()) { n++; bool b = (sf.Plane & 0x8000) != 0, f = (sf.Flags & SurfaceFlags.PlaneNegated) != 0; if (b) bit++; if (f) flag++; if (b && f) both++; }
                        Console.WriteLine($"{what}: {n} surfaces; plane index bit 15 set on {bit}, PlaneNegated flag on {flag}, both {both}");
                    }
                    Count("structure", r.CollisionBsps ?? new());
                    Count("instances", r.InstancedGeometry.Select(i => i.CollisionInfo));
                }
                return 0;
            }
            if (a.Length > 3 && a[3] == "gmat")
            {
                // collision materials' global material indices against the globals' material count; which are used by instances
                var hc = Program.OpenPak(a[1]);
                using (var st = Program.OpenStream(hc))
                {
                    var sb = hc.Deserialize<ScenarioStructureBsp>(st, hc.TagCache.GetTag(a[2], "sbsp"));
                    var g = hc.Deserialize<TagTool.Tags.Definitions.Globals>(st, hc.TagCache.NonNull().First(t => t.IsInGroup("matg")));
                    int count = g.Materials?.Count ?? -1;
                    var r = hc.ResourceCache.GetStructureBspTagResources(sb.CollisionBspResource);
                    var usedInst = new HashSet<int>(r.InstancedGeometry.SelectMany(i => i.CollisionInfo?.Surfaces ?? new()).Select(sf => (int)sf.MaterialIndex));
                    var usedStruct = new HashSet<int>((r.CollisionBsps ?? new()).SelectMany(c => c.Surfaces).Select(sf => (int)sf.MaterialIndex));
                    int bad = 0, badInst = 0, badStruct = 0;
                    for (int m = 0; m < sb.CollisionMaterials.Count; m++)
                    {
                        int gi = sb.CollisionMaterials[m].RuntimeGlobalMaterialIndex;
                        if (gi < 0 || gi >= count) { bad++; if (usedInst.Contains(m)) badInst++; if (usedStruct.Contains(m)) badStruct++; }
                    }
                    foreach (var gi in sb.CollisionMaterials.Select(c => (int)c.RuntimeGlobalMaterialIndex).Distinct().OrderBy(x => x)) if (gi >= 0 && gi < count) { var gm = g.Materials[gi]; Console.WriteLine($"  global material {gi}: {hc.StringTable.GetString(gm.Name)} parent {hc.StringTable.GetString(gm.ParentName)} flags {gm.Flags}"); }
                    Console.WriteLine($"globals materials {count}; collision materials {sb.CollisionMaterials.Count}, out of range {bad} (used by instances {badInst}, by structure {badStruct}); global indices used: {string.Join(",", sb.CollisionMaterials.Select(c => (int)c.RuntimeGlobalMaterialIndex).Distinct().OrderBy(x => x).Take(40))}");
                }
                return 0;
            }
            if (a.Length > 3 && a[3] == "cmats")
            {
                var hc = Program.OpenPak(a[1]);
                using (var st = Program.OpenStream(hc))
                {
                    var sb = hc.Deserialize<ScenarioStructureBsp>(st, hc.TagCache.GetTag(a[2], "sbsp"));
                    var tally = new Dictionary<string, int>();
                    foreach (var c in sb.CollisionMaterials) { var k = $"conveyor {c.ConveyorSurfaceIndex} seam {c.SeamMappingIndex} flags {c.Flags}"; tally[k] = tally.TryGetValue(k, out int q) ? q + 1 : 1; }
                    foreach (var kv in tally) Console.WriteLine($"  {kv.Value} x {kv.Key}");
                    Console.WriteLine($"conveyor surfaces {sb.ConveyorSurfaces?.Count}");
                }
                return 0;
            }
            if (a.Length > 4 && a[3] == "whichbuckets")
            {
                // which clusters' mesh instance buckets list each instance (a[4], comma list); also any non-cluster mesh
                var hc = Program.OpenPak(a[1]);
                using (var st = Program.OpenStream(hc))
                {
                    var sb = hc.Deserialize<ScenarioStructureBsp>(st, hc.TagCache.GetTag(a[2], "sbsp"));
                    var clusterMeshes = sb.Clusters.Select((c, i) => (c.MeshIndex, i)).ToDictionary(x => (int)x.MeshIndex, x => x.i);
                    foreach (var x in a[4].Split(',').Select(int.Parse))
                    {
                        var where = new List<string>();
                        for (int mi = 0; mi < sb.Geometry.Meshes.Count; mi++)
                            if ((sb.Geometry.Meshes[mi].InstanceBuckets ?? new()).Any(b => b.Instances.Any(q => q.InstanceIndex == x)))
                                where.Add(clusterMeshes.TryGetValue(mi, out int ci) ? "cluster " + ci : "mesh " + mi);
                        Console.WriteLine($"instance {x} {hc.StringTable.GetString(sb.InstancedGeometryInstances[x].Name)}: {(where.Count == 0 ? "in NO bucket" : string.Join(", ", where))}");
                    }
                }
                return 0;
            }
            if (a.Length > 5 && a[3] == "inbucket")
            {
                // is each instance (a[5], comma list) in cluster a[4]'s mesh instance buckets (the list Halo 3 builds that
                // cluster's instance collision from)?
                var hc = Program.OpenPak(a[1]);
                using (var st = Program.OpenStream(hc))
                {
                    var sb = hc.Deserialize<ScenarioStructureBsp>(st, hc.TagCache.GetTag(a[2], "sbsp"));
                    var cl = sb.Clusters[int.Parse(a[4])]; var mesh = sb.Geometry.Meshes[cl.MeshIndex];
                    var set = new HashSet<int>((mesh.InstanceBuckets ?? new()).SelectMany(b => b.Instances).Select(i => (int)i.InstanceIndex));
                    Console.WriteLine($"cluster {a[4]} mesh {cl.MeshIndex}: {set.Count} instances in its buckets");
                    foreach (var x in a[5].Split(',').Select(int.Parse)) Console.WriteLine($"  instance {x} {hc.StringTable.GetString(sb.InstancedGeometryInstances[x].Name)}: {(set.Contains(x) ? "IN" : "NOT in")} the cluster's buckets");
                }
                return 0;
            }
            if (a.Length > 2 && a[1] == "layout")
            {
                // field offsets of a TagTool type in the Halo 3 360 layout: physprobe layout <type full name> [recurse]
                var ty = typeof(TagStructure).Assembly.GetType(a[2]) ?? throw new ArgumentException("no type " + a[2]);
                void Print(Type t, uint at, string ind, int depth)
                {
                    var info = TagStructure.GetTagStructureInfo(t, TagTool.Cache.CacheVersion.Halo3Retail, TagTool.Cache.CachePlatform.Original);
                    Console.WriteLine($"{ind}{t.Name} size 0x{info.TotalSize:X}");
                    foreach (var f in TagStructure.GetTagFieldEnumerable(info))
                    {
                        Console.WriteLine($"{ind}  0x{at + f.Offset:X3} {f.Name} : {f.FieldType.Name}");
                        if (depth > 0 && typeof(TagStructure).IsAssignableFrom(f.FieldType) && !f.FieldType.IsGenericType) Print(f.FieldType, at + f.Offset, ind + "    ", depth - 1);
                    }
                }
                Print(ty, 0, "", a.Length > 3 ? int.Parse(a[3]) : 0);
                return 0;
            }
            if (a.Length > 3 && a[3] == "placed")
            {
                // placed objects per scenario block (palette type) and whether that type is in a Forge palette
                var hc = Program.OpenPak(a[1]);
                using (var st = Program.OpenStream(hc))
                {
                    var sc = hc.Deserialize<Scenario>(st, hc.TagCache.GetTag(a[2], "scnr"));
                    var pal = new HashSet<string>(typeof(Scenario).GetFields().Where(f => f.Name.StartsWith("Sandbox")).SelectMany(f => (f.GetValue(sc) as List<Scenario.SandboxObject>) ?? new()).Where(e => e.Object != null).Select(e => e.Object.Name));
                    foreach (var f in typeof(Scenario).GetFields().Where(f => f.Name.EndsWith("Palette") && f.FieldType.IsGenericType))
                    {
                        var palList = f.GetValue(sc) as System.Collections.IList; if (palList == null || palList.Count == 0) continue;
                        var placeField = typeof(Scenario).GetField(f.Name.Substring(0, f.Name.Length - "Palette".Length)) ?? typeof(Scenario).GetField(f.Name.Substring(0, f.Name.Length - "Palette".Length) + "s");
                        var placed = placeField?.GetValue(sc) as System.Collections.IList;
                        var names = new List<string>();
                        foreach (var pe in palList) { var o = pe.GetType().GetField("Object")?.GetValue(pe) as CachedTag; names.Add(o?.Name); }
                        var counts = new Dictionary<int, int>();
                        if (placed != null) foreach (var pl in placed) { var pi = pl.GetType().GetField("PaletteIndex")?.GetValue(pl); int k = pi == null ? -9 : Convert.ToInt32(pi); counts[k] = counts.TryGetValue(k, out int q) ? q + 1 : 1; }
                        Console.WriteLine($"{f.Name}: {palList.Count} types, {placed?.Count} placed ({placeField?.Name})");
                        foreach (var kv in counts.OrderBy(k => k.Key)) Console.WriteLine($"   {kv.Value} x {(kv.Key >= 0 && kv.Key < names.Count ? names[kv.Key] : "palette index " + kv.Key)} {(kv.Key >= 0 && kv.Key < names.Count && names[kv.Key] != null ? (pal.Contains(names[kv.Key]) ? "[in Forge palette]" : "[NOT in Forge palette]") : "")}");
                    }
                }
                return 0;
            }
            if (a.Length > 3 && a[3] == "mpobj")
            {
                // Forge palette objects: group, model/physics presence and the multiplayer object block Forge reads
                var hc = Program.OpenPak(a[1]);
                using (var st = Program.OpenStream(hc))
                {
                    var sc = hc.Deserialize<Scenario>(st, hc.TagCache.GetTag(a[2], "scnr"));
                    var stats = new Dictionary<string, int>(); var odd = new List<string>();
                    foreach (var f in typeof(Scenario).GetFields().Where(f => f.Name.StartsWith("Sandbox")))
                        foreach (var e in (f.GetValue(sc) as List<Scenario.SandboxObject>) ?? new())
                        {
                            if (e.Object == null) { odd.Add(f.Name + ": null object"); continue; }
                            var go = (TagTool.Tags.Definitions.GameObject)hc.Deserialize(st, e.Object);
                            var mp = go.MultiplayerObject;
                            string k = $"{f.Name} {e.Object.Group.Tag} mp={mp?.Count ?? -1} model={(go.Model != null ? 1 : 0)}";
                            stats[k] = stats.TryGetValue(k, out int q) ? q + 1 : 1;
                            if (a.Length > 4) Console.WriteLine($"{f.Name} {e.Object.Name} mp={mp?.Count} {(mp?.Count > 0 ? "type " + mp[0].Type + " flags " + mp[0].Flags + " shape " + mp[0].BoundaryShape + " spawn " + mp[0].SpawnTimerType : "")} model {go.Model?.Name} cost {e.Cost} max {e.MaxAllowed} name {hc.StringTable.GetString(e.Name)}");
                        }
                    foreach (var kv in stats.OrderBy(k => k.Key)) Console.WriteLine($"{kv.Value,5} {kv.Key}");
                    foreach (var o in odd) Console.WriteLine(o);
                }
                return 0;
            }
            if (a.Length > 3 && a[3] == "defspheres")
            {
                // instance definitions' own bounding spheres: how many collidable definitions have none (radius 0)
                var hc = Program.OpenPak(a[1]);
                using (var st = Program.OpenStream(hc))
                {
                    var sb = hc.Deserialize<ScenarioStructureBsp>(st, hc.TagCache.GetTag(a[2], "sbsp"));
                    var r = hc.ResourceCache.GetStructureBspTagResources(sb.CollisionBspResource);
                    int coll = 0, zero = 0, zeroUsed = 0; var ex = new List<string>();
                    for (int d = 0; d < r.InstancedGeometry.Count; d++)
                    {
                        var g = r.InstancedGeometry[d]; if (g.CollisionInfo?.Surfaces == null || g.CollisionInfo.Surfaces.Count == 0) continue; coll++;
                        if (g.BoundingSphereRadius <= 0) { zero++; var u = sb.InstancedGeometryInstances.FirstOrDefault(x => x.DefinitionIndex == d); if (u != null) { zeroUsed++; if (ex.Count < 5) ex.Add(hc.StringTable.GetString(u.Name)); } }
                    }
                    if (a.Length > 4) for (int d = 0; d < r.InstancedGeometry.Count && d < int.Parse(a[4]); d++)
                    {
                        var g = r.InstancedGeometry[d]; var vs = g.CollisionInfo?.Vertices; if (vs == null || vs.Count == 0) continue;
                        float lx = vs.Min(v => v.Point.X), hx = vs.Max(v => v.Point.X), ly = vs.Min(v => v.Point.Y), hy = vs.Max(v => v.Point.Y), lz = vs.Min(v => v.Point.Z), hz = vs.Max(v => v.Point.Z);
                        float cx = (lx + hx) / 2, cy = (ly + hy) / 2, cz = (lz + hz) / 2; var rad = vs.Max(v => Math.Sqrt((v.Point.X - cx) * (v.Point.X - cx) + (v.Point.Y - cy) * (v.Point.Y - cy) + (v.Point.Z - cz) * (v.Point.Z - cz)));
                        var c = sb.Geometry.Compression.Count > g.CompressionIndex && g.CompressionIndex >= 0 ? sb.Geometry.Compression[g.CompressionIndex] : null;
                        Console.WriteLine($"def {d}: offset {g.BoundingSphereOffset} radius {g.BoundingSphereRadius:0.000} | collision box centre ({cx:0.000},{cy:0.000},{cz:0.000}) radius {rad:0.000} | render box {(c == null ? "-" : $"({(c.X.Lower + c.X.Upper) / 2:0.000},{(c.Y.Lower + c.Y.Upper) / 2:0.000},{(c.Z.Lower + c.Z.Upper) / 2:0.000}) half-diag {Math.Sqrt(Math.Pow(c.X.Upper - c.X.Lower, 2) + Math.Pow(c.Y.Upper - c.Y.Lower, 2) + Math.Pow(c.Z.Upper - c.Z.Lower, 2)) / 2:0.000}")}");
                    }
                    Console.WriteLine($"{r.InstancedGeometry.Count} definitions, {coll} with collision, {zero} of those with bounding sphere radius 0 ({zeroUsed} used), e.g. {string.Join(" | ", ex)}");
                }
                return 0;
            }
            if (a.Length > 4 && a[3] == "bspdump")
            {
                // full collision BSP of the first instance whose name contains a[4]
                var hc = Program.OpenPak(a[1]);
                using (var st = Program.OpenStream(hc))
                {
                    var sb = hc.Deserialize<ScenarioStructureBsp>(st, hc.TagCache.GetTag(a[2], "sbsp"));
                    var r = hc.ResourceCache.GetStructureBspTagResources(sb.CollisionBspResource);
                    var x = sb.InstancedGeometryInstances.First(q => (hc.StringTable.GetString(q.Name) ?? "").Contains(a[4]));
                    var g = r.InstancedGeometry[x.DefinitionIndex].CollisionInfo;
                    Console.WriteLine($"transform {x.Matrix} scale {x.Scale}");
                    for (int i = 0; i < g.Planes.Count; i++) Console.WriteLine($"plane {i}: {g.Planes[i].Value}");
                    for (int i = 0; i < g.Bsp3dNodes.Count; i++) Console.WriteLine($"node {i}: plane 0x{g.Bsp3dNodes[i].Plane:X} front 0x{g.Bsp3dNodes[i].FrontChild:X} back 0x{g.Bsp3dNodes[i].BackChild:X}");
                    for (int i = 0; i < g.Leaves.Count; i++) Console.WriteLine($"leaf {i}: flags {g.Leaves[i].Flags} refs {g.Leaves[i].Bsp2dReferenceCount} first {g.Leaves[i].FirstBsp2dReference}");
                    for (int i = 0; i < g.Bsp2dReferences.Count; i++) Console.WriteLine($"ref {i}: plane 0x{g.Bsp2dReferences[i].PlaneIndex:X} node 0x{g.Bsp2dReferences[i].Bsp2dNodeIndex:X}");
                    for (int i = 0; i < g.Bsp2dNodes.Count; i++) Console.WriteLine($"2d {i}: {g.Bsp2dNodes[i].Plane} left 0x{g.Bsp2dNodes[i].LeftChild:X} right 0x{g.Bsp2dNodes[i].RightChild:X}");
                    for (int i = 0; i < g.Surfaces.Count; i++)
                    {
                        var sf = g.Surfaces[i]; var vs = new List<string>(); int e = sf.FirstEdge, gd = 0;
                        do { var ed = g.Edges[e]; var v = g.Vertices[ed.RightSurface == i ? ed.EndVertex : ed.StartVertex].Point; vs.Add($"({v.X:0.00},{v.Y:0.00},{v.Z:0.00})"); e = ed.RightSurface == i ? ed.ReverseEdge : ed.ForwardEdge; } while (e != sf.FirstEdge && gd++ < 32);
                        Console.WriteLine($"surface {i}: plane 0x{sf.Plane:X} flags {sf.Flags} material {sf.MaterialIndex} {string.Join(" ", vs)}");
                    }
                }
                return 0;
            }
            if (a.Length > 4 && a[3] == "instdump")
            {
                // every scalar field of the instances whose name contains a[4], their definition (collision counts, mesh) and
                // flags of their collision surfaces. physprobe <map or pak> <sbsp> instdump <name part>
                var hc = Program.OpenPak(a[1]);
                using (var st = Program.OpenStream(hc))
                {
                    var sb = hc.Deserialize<ScenarioStructureBsp>(st, hc.TagCache.GetTag(a[2], "sbsp"));
                    var r = hc.ResourceCache.GetStructureBspTagResources(sb.CollisionBspResource);
                    string Dump(object o) => o == null ? "null" : string.Join(" ", o.GetType().GetFields().Where(f => !(f.GetValue(o) is System.Collections.IList)).Select(f => { var v = f.GetValue(o); return f.Name + "=" + (v is StringId sid ? hc.StringTable.GetString(sid) : v is CachedTag ct ? ct.Name : v?.ToString()); }));
                    string Lists(object o) => o == null ? "" : string.Join(" ", o.GetType().GetFields().Where(f => f.GetValue(o) is System.Collections.IList).Select(f => f.Name + "[" + ((System.Collections.IList)f.GetValue(o)).Count + "]"));
                    int shown = 0;
                    for (int i = 0; i < sb.InstancedGeometryInstances.Count && shown < 6; i++)
                    {
                        var x = sb.InstancedGeometryInstances[i]; var nm = hc.StringTable.GetString(x.Name) ?? "";
                        if (nm.IndexOf(a[4], StringComparison.OrdinalIgnoreCase) < 0) continue; shown++;
                        Console.WriteLine($"== instance {i} {nm}: {Dump(x)} | {Lists(x)}");
                        var d = r.InstancedGeometry[x.DefinitionIndex];
                        Console.WriteLine($"   def {x.DefinitionIndex}: {Dump(d)} | {Lists(d)}");
                        var ci = d.CollisionInfo;
                        if (ci != null) Console.WriteLine($"   collision: {Lists(ci)}; surface flags {string.Join(",", ci.Surfaces.GroupBy(q => q.Flags).Select(g => g.Key + "x" + g.Count()))}; materials {string.Join(",", ci.Surfaces.Select(q => (int)q.MaterialIndex).Distinct().Select(m => m >= 0 && m < sb.CollisionMaterials.Count ? System.IO.Path.GetFileName(sb.CollisionMaterials[m].RenderMethod?.Name ?? "?") + "/gm" + sb.CollisionMaterials[m].RuntimeGlobalMaterialIndex : "#" + m))}");
                    }
                }
                return 0;
            }
            if (a.Length > 3 && a[3] == "twosided")
            {
                // two-sided collision surfaces per collision geometry (structure + instance definitions): counts, materials,
                // bounds, and the instances that use each definition. physprobe <src> <sbsp> twosided
                var hc = Program.OpenPak(a[1]);
                using (var st = Program.OpenStream(hc))
                {
                    var sb = hc.Deserialize<ScenarioStructureBsp>(st, hc.TagCache.GetTag(a[2], "sbsp"));
                    var r = hc.ResourceCache.GetStructureBspTagResources(sb.CollisionBspResource);
                    string Mat(int m) => m >= 0 && m < sb.CollisionMaterials.Count ? System.IO.Path.GetFileName(sb.CollisionMaterials[m].RenderMethod?.Name ?? "?") : "#" + m;
                    void Report(string what, IEnumerable<(SurfaceFlags f, int m, float[] box)> surfs)
                    {
                        var l = surfs.ToList(); var ts = l.Where(x => (x.f & SurfaceFlags.TwoSided) != 0).ToList(); if (ts.Count == 0) return;
                        var neg = ts.Count(x => (x.f & SurfaceFlags.PlaneNegated) != 0); var inv = ts.Count(x => (x.f & SurfaceFlags.Invisible) != 0);
                        var b = new[] { ts.Min(x => x.box[0]), ts.Max(x => x.box[1]), ts.Min(x => x.box[2]), ts.Max(x => x.box[3]), ts.Min(x => x.box[4]), ts.Max(x => x.box[5]) };
                        Console.WriteLine($"{what}: {l.Count} surfaces, {ts.Count} two-sided ({neg} negated, {inv} invisible), materials {string.Join(",", ts.GroupBy(x => Mat(x.m)).Select(g => g.Key + "x" + g.Count()))}, box x {b[0]:0.0}..{b[1]:0.0} y {b[2]:0.0}..{b[3]:0.0} z {b[4]:0.0}..{b[5]:0.0}");
                    }
                    float[] Box(IEnumerable<RealPoint3d> ps) { var q = ps.ToList(); return q.Count == 0 ? new float[6] : new[] { q.Min(p => p.X), q.Max(p => p.X), q.Min(p => p.Y), q.Max(p => p.Y), q.Min(p => p.Z), q.Max(p => p.Z) }; }
                    IEnumerable<RealPoint3d> LoopL(LargeCollisionBspBlock c, int s) { int e = c.Surfaces[s].FirstEdge, g = 0; do { var ed = c.Edges[e]; if (ed.RightSurface == s) { yield return c.Vertices[ed.EndVertex].Point; e = ed.ReverseEdge; } else { yield return c.Vertices[ed.StartVertex].Point; e = ed.ForwardEdge; } } while (e != c.Surfaces[s].FirstEdge && g++ < 64); }
                    IEnumerable<RealPoint3d> LoopS(CollisionGeometry c, int s) { int e = c.Surfaces[s].FirstEdge, g = 0; do { var ed = c.Edges[e]; if (ed.RightSurface == s) { yield return c.Vertices[ed.EndVertex].Point; e = ed.ReverseEdge; } else { yield return c.Vertices[ed.StartVertex].Point; e = ed.ForwardEdge; } } while (e != c.Surfaces[s].FirstEdge && g++ < 64); }
                    foreach (var lb in r.LargeCollisionBsps ?? new()) Report("structure (large)", Enumerable.Range(0, lb.Surfaces.Count).Select(i => (lb.Surfaces[i].Flags, (int)lb.Surfaces[i].Material, Box(LoopL(lb, i)))));
                    foreach (var cb in r.CollisionBsps ?? new()) Report("structure", Enumerable.Range(0, cb.Surfaces.Count).Select(i => (cb.Surfaces[i].Flags, (int)cb.Surfaces[i].MaterialIndex, Box(LoopS(cb, i)))));
                    for (int d = 0; d < r.InstancedGeometry.Count; d++)
                    {
                        var ci = r.InstancedGeometry[d].CollisionInfo; if (ci?.Surfaces == null) continue;
                        var users = sb.InstancedGeometryInstances.Where(x => x.DefinitionIndex == d).ToList();
                        Report($"def {d} ({users.Count} instances, e.g. {(users.Count > 0 ? hc.StringTable.GetString(users[0].Name) + " flags " + users[0].Flags : "-")})", Enumerable.Range(0, ci.Surfaces.Count).Select(i => (ci.Surfaces[i].Flags, (int)ci.Surfaces[i].MaterialIndex, Box(LoopS(ci, i)))));
                    }
                }
                return 0;
            }
            if (a.Length > 3 && a[3] == "leafcount")
            {
                var hc = Program.OpenPak(a[1]);
                using (var st = Program.OpenStream(hc))
                {
                    var sb = hc.Deserialize<ScenarioStructureBsp>(st, hc.TagCache.GetTag(a[2], "sbsp"));
                    var r = hc.ResourceCache.GetStructureBspTagResources(sb.CollisionBspResource);
                    Console.WriteLine($"leaves with surface references: {sb.Leaves?.Count(l => l.SurfaceReferenceCount > 0)} of {sb.Leaves?.Count}");
                    Console.WriteLine($"sbsp leaves {sb.Leaves?.Count}; large collision leaves {r?.LargeCollisionBsps?.FirstOrDefault()?.Leaves?.Count}; small collision leaves {r?.CollisionBsps?.FirstOrDefault()?.Leaves?.Count}");
                    var cb = r?.CollisionBsps?.FirstOrDefault(); var lb = r?.LargeCollisionBsps?.FirstOrDefault();
                    if (cb != null) Console.WriteLine($"small: 3d nodes {cb.Bsp3dNodes?.Count} 2d nodes {cb.Bsp2dNodes?.Count} 2d refs {cb.Bsp2dReferences?.Count} planes {cb.Planes?.Count} surfaces {cb.Surfaces?.Count} edges {cb.Edges?.Count} vertices {cb.Vertices?.Count}");
                    if (lb != null) Console.WriteLine($"large: 3d nodes {lb.Bsp3dNodes?.Count} 2d nodes {lb.Bsp2dNodes?.Count} 2d refs {lb.Bsp2dReferences?.Count} planes {lb.Planes?.Count} surfaces {lb.Surfaces?.Count} edges {lb.Edges?.Count} vertices {lb.Vertices?.Count}");
                }
                return 0;
            }
            if (a.Length > 3 && a[3] == "mvpal")
            {
                // Reach-style map variant palettes of a scenario (Forge menu with prices): physprobe <src> <scnr> mvpal
                // (src may be a Reach .map: read only)
                var hc = a[1].EndsWith(".map", StringComparison.OrdinalIgnoreCase) ? GameCache.Open(new FileInfo(a[1])) : Program.OpenPak(a[1]);
                using (var st = hc is GameCacheModPackage ? Program.OpenStream(hc) : hc.OpenCacheRead())
                {
                    var sc = hc.Deserialize<Scenario>(st, hc.TagCache.GetTag(a[2], "scnr"));
                    foreach (var pal in sc.MapVariantPalettes ?? new())
                    {
                        Console.WriteLine($"== {hc.StringTable.GetString(pal.Name)} ({pal.Entries?.Count})");
                        foreach (var e in (pal.Entries ?? new()).Take(a.Length > 4 ? 999 : 8))
                            Console.WriteLine($"  {hc.StringTable.GetString(e.Name)}: max {e.MaximumAllowed} price {e.PricePerInstance} variants {string.Join(", ", (e.Variants ?? new()).Select(v => hc.StringTable.GetString(v.DisplayName) + "=" + v.Object?.Name))}");
                    }
                }
                return 0;
            }
            if (a.Length > 3 && a[3] == "iflags")
            {
                // instance flag counts, and flags of instances whose names match a regex: physprobe <src> <sbsp> iflags [regex]
                var hc = Program.OpenPak(a[1]);
                using (var st = Program.OpenStream(hc))
                {
                    var sb = hc.Deserialize<ScenarioStructureBsp>(st, hc.TagCache.GetTag(a[2], "sbsp"));
                    foreach (var g in sb.InstancedGeometryInstances.GroupBy(i => i.Flags.ToString()).OrderByDescending(g => g.Count())) Console.WriteLine($"{g.Count(),6} {g.Key}");
                    if (a.Length > 4)
                    {
                        var re = new System.Text.RegularExpressions.Regex(a[4], System.Text.RegularExpressions.RegexOptions.IgnoreCase);
                        foreach (var gi in sb.InstancedGeometryInstances.Where(i => re.IsMatch(hc.StringTable.GetString(i.Name) ?? "")).Take(20))
                            Console.WriteLine($"  {hc.StringTable.GetString(gi.Name)}: def {gi.DefinitionIndex} flags {gi.Flags} at {gi.Matrix.m41:F2},{gi.Matrix.m42:F2},{gi.Matrix.m43:F2}");
                    }
                }
                return 0;
            }
            if (a.Length > 3 && a[3] == "mirror")
            {
                // instances with a mirrored (negative determinant) transform, and whether their definition has collision
                var hc = Program.OpenPak(a[1]);
                using (var st = Program.OpenStream(hc))
                {
                    var sb = hc.Deserialize<ScenarioStructureBsp>(st, hc.TagCache.GetTag(a[2], "sbsp"));
                    var r = hc.ResourceCache.GetStructureBspTagResources(sb.CollisionBspResource);
                    int mir = 0, mirColl = 0, tot = 0; var ex = new System.Collections.Generic.List<string>();
                    foreach (var gi in sb.InstancedGeometryInstances)
                    {
                        tot++; var m = gi.Matrix;
                        double det = m.m11 * (m.m22 * m.m33 - m.m23 * m.m32) - m.m12 * (m.m21 * m.m33 - m.m23 * m.m31) + m.m13 * (m.m21 * m.m32 - m.m22 * m.m31);
                        bool coll = gi.DefinitionIndex >= 0 && r.InstancedGeometry[gi.DefinitionIndex].CollisionInfo?.Surfaces?.Count > 0;
                        if (det < 0) { mir++; if (coll) { mirColl++; if (ex.Count < 8) ex.Add($"{hc.StringTable.GetString(gi.Name)} at {m.m41:F1},{m.m42:F1},{m.m43:F1}"); } }
                    }
                    Console.WriteLine($"instances {tot}: mirrored {mir}, mirrored with collision {mirColl}");
                    if (a.Length > 4)
                    {
                        var re = new System.Text.RegularExpressions.Regex(a[4], System.Text.RegularExpressions.RegexOptions.IgnoreCase);
                        foreach (var gi in sb.InstancedGeometryInstances)
                        {
                            var nm = hc.StringTable.GetString(gi.Name); if (!re.IsMatch(nm ?? "")) continue;
                            var ci = gi.DefinitionIndex >= 0 ? r.InstancedGeometry[gi.DefinitionIndex].CollisionInfo : null;
                            var mesh = gi.DefinitionIndex >= 0 ? r.InstancedGeometry[gi.DefinitionIndex].MeshIndex : -1;
                            if (ci?.Surfaces != null && nm.Contains("sphere"))
                            {
                                var mats = ci.Surfaces.GroupBy(x => (x.MaterialIndex, x.Flags)).Select(g2 => $"mat {g2.Key.MaterialIndex}={(g2.Key.MaterialIndex >= 0 && g2.Key.MaterialIndex < sb.Materials.Count ? sb.Materials[g2.Key.MaterialIndex].RenderMethod?.Name : "?")} flags {g2.Key.Flags} x{g2.Count()}");
                                Console.WriteLine("    " + string.Join("; ", mats));
                            }
                            Console.WriteLine($"  {nm}: def {gi.DefinitionIndex} scale {gi.Scale} flags {gi.Flags} at {gi.Matrix.m41:F1},{gi.Matrix.m42:F1},{gi.Matrix.m43:F1} coll surfaces {ci?.Surfaces?.Count} polyhedra {r.InstancedGeometry[gi.DefinitionIndex].Polyhedra?.Count} mesh {mesh}");
                        }
                    }
                    foreach (var e in ex) Console.WriteLine("  " + e);
                }
                return 0;
            }
            if (a.Length > 3 && a[3] == "zones")
            {
                // zone set BSP masks and each structure BSP's collision / instance content: physprobe <src> <scnr> zones
                var hc = Program.OpenPak(a[1]);
                using (var st = Program.OpenStream(hc))
                {
                    var sc = hc.Deserialize<Scenario>(st, hc.TagCache.GetTag(a[2], "scnr"));
                    foreach (var z in sc.ZoneSets) Console.WriteLine($"zone set {hc.StringTable.GetString(z.Name)}: bsps 0x{(uint)z.Bsps:X}");
                    for (int i = 0; i < sc.StructureBsps.Count; i++)
                    {
                        var sb = hc.Deserialize<ScenarioStructureBsp>(st, sc.StructureBsps[i].StructureBsp);
                        var r = hc.ResourceCache.GetStructureBspTagResources(sb.CollisionBspResource);
                        var lb = r?.LargeCollisionBsps?.FirstOrDefault(); var cb = r?.CollisionBsps?.FirstOrDefault();
                        var verts = lb != null ? lb.Vertices.Select(v => v.Point).ToList() : cb?.Vertices.Select(v => v.Point).ToList();
                        string bb = verts == null || verts.Count == 0 ? "none" : $"x {verts.Min(v => v.X):F1}..{verts.Max(v => v.X):F1} y {verts.Min(v => v.Y):F1}..{verts.Max(v => v.Y):F1} z {verts.Min(v => v.Z):F1}..{verts.Max(v => v.Z):F1}";
                        Console.WriteLine($"bsp {i} {sc.StructureBsps[i].StructureBsp.Name}: structure surfaces {(lb?.Surfaces.Count ?? cb?.Surfaces.Count ?? 0)} ({bb}), instance defs {r?.InstancedGeometry?.Count}, instances {sb.InstancedGeometryInstances?.Count}, clusters {sb.Clusters?.Count}");
                    }
                }
                return 0;
            }
            if (a.Length > 3 && a[3] == "bounds")
            {
                // render bounds of objects: physprobe <pak> <name regex> bounds <group>
                var hc = Program.OpenPak(a[1]); var re = new System.Text.RegularExpressions.Regex(a[2], System.Text.RegularExpressions.RegexOptions.IgnoreCase);
                using (var st = Program.OpenStream(hc))
                    foreach (var t in hc.TagCache.NonNull().Where(t => t.IsInGroup(a[4]) && re.IsMatch(t.Name)))
                    {
                        try
                        {
                            var o = (GameObject)hc.Deserialize(st, t); var m = hc.Deserialize<Model>(st, o.Model); var rm = hc.Deserialize<RenderModel>(st, m.RenderModel);
                            var c = rm.Geometry.Compression[0];
                            Console.WriteLine($"{t.Name}: x {c.X.Lower:F2}..{c.X.Upper:F2} y {c.Y.Lower:F2}..{c.Y.Upper:F2} z {c.Z.Lower:F2}..{c.Z.Upper:F2}");
                        }
                        catch (Exception ex) { Console.WriteLine($"{t.Name}: {ex.Message}"); }
                    }
                return 0;
            }
            if (a.Length > 3 && a[3] == "sandbox")
            {
                // sandbox (Forge) palettes of one scenario: block sizes and the first few object names
                var hc = Program.OpenPak(a[1]);
                using (var st = Program.OpenStream(hc))
                {
                    var sc = hc.Deserialize<Scenario>(st, hc.TagCache.GetTag(a[2], "scnr"));
                    Console.WriteLine($"scenario sandbox budget {sc.SandboxBudget}");
                    foreach (var f in typeof(Scenario).GetFields().Where(f => f.Name.StartsWith("Sandbox")))
                    {
                        var l = f.GetValue(sc) as System.Collections.Generic.List<Scenario.SandboxObject>;
                        Console.WriteLine($"{f.Name} {l?.Count}: " + string.Join(" | ", (l ?? new()).Take(a.Length > 4 ? 999 : 6).Select(o => (a.Length > 5 ? hc.StringTable.GetString(o.Name) + "=" : "") + (o.Object?.Name ?? "NULL"))));
                    }
                }
                return 0;
            }
            if (a.Length > 3 && a[3] == "phmo")
            {
                var hc = Program.OpenPak(a[1]);
                using (var st = Program.OpenStream(hc))
                {
                    var pm = hc.Deserialize<PhysicsModel>(st, hc.TagCache.GetTag(a[2], "phmo"));
                    Console.WriteLine($"rigid bodies {pm.RigidBodies?.Count}: " + string.Join(" ", pm.RigidBodies.Select(r => $"{r.ShapeType}:{r.ShapeIndex}")));
                    Console.WriteLine($"lists {pm.Lists?.Count} listshapes {pm.ListShapes?.Count} mopps {pm.Mopps?.Count} moppdata {pm.MoppData?.Length} boxes {pm.Boxes?.Count} spheres {pm.Spheres?.Count}");
                }
                return 0;
            }
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
