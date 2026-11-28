// Object layout. ElDewrito keeps a map's multiplayer objects (respawn points, game-mode markers, weapons, grenades,
// props) in the map file's built-in map variant rather than in the scenario (Reflection: 301 variant objects; its
// scenario has 2 scenery and 3 crates). Halo 3 places multiplayer objects as scenario placements with multiplayer
// properties, field for field the variant's: so each variant object becomes a placement of the matching stock Halo 3
// object (by name; map cfg substitutions apply, e.g. DMR -> battle rifle), with its position, facing, team, spawn time,
// game-mode flags and boundary. Objects with no stock Halo 3 tag (ElDewrito Forge blocks, base-cache content the
// package does not carry) are listed and left out.
using System;
using System.Collections.Generic;
using System.Linq;
using TagTool.BlamFile;
using TagTool.Cache;
using TagTool.Common;
using TagTool.Tags.Definitions;
using TagTool.Tags.Definitions.Common;
using static TagTool.Tags.Definitions.Scenario;

namespace Ho2H3
{
    public static class Placements
    {
        public static List<(string key, double x, double y, double z, double yaw)> Extra = new List<(string, double, double, double, double)>();
        // before the walk: map variant objects with no stock Halo 3 tag of the same name (and no cfg substitute) are map pieces
        // of their own (e.g. Icebox's cart and radio tower); they are walked and converted, then placed as converted objects
        public static IEnumerable<CachedTag> Roots(GameCache ho, string scenarioName, Dictionary<string, string> subst, Dictionary<string, string> owner, List<string> log)
        {
            // opt-in (HO2H3_VARIANT_PIECES=1): placed as is they misbehave - Sword Base's crashed-Pelican gibs hang in mid-air,
            // Reflection's include ElDewrito reforge blocks
            if (Environment.GetEnvironmentVariable("HO2H3_VARIANT_PIECES") != "1") yield break;
            var v = ReadVariant(ho, scenarioName, log); if (v == null) yield break;
            var seen = new HashSet<int>();
            foreach (var q in v.Quotas)
            {
                int ti = q.ObjectDefinitionIndex; if (ti < 0 || ti >= ho.TagCache.Count || !seen.Add(ti)) continue;
                var t = ho.TagCache.GetTag(ti); if (t == null) continue;
                string g = t.Group.Tag.ToString(), key = g + ":" + t.Name;
                if (!(g == "scen" || g == "bloc" || g == "mach" || g == "ctrl")) continue;
                if (subst.ContainsKey(key) || owner.ContainsKey(key)) continue;
                yield return t;
            }
        }
        static MapVariant ReadVariant(GameCache ho, string scenarioName, List<string> log)
        {
            var pak = ho as GameCacheModPackage;
            MapVariant v = null;
            if (pak != null)
                for (int i = 0; i < pak.BaseModPackage.MapFileStreams.Count && v == null; i++)
                {
                    try { var mf = VariantProbe.Read(pak, i); if (string.Equals(mf.Header?.GetScenarioPath(), scenarioName, StringComparison.OrdinalIgnoreCase)) v = mf.MapFileBlf?.MapVariant?.MapVariant; } catch { }
                }
            else if (Environment.GetEnvironmentVariable("HO2H3_BASE_VARIANT") == "1")
            {
                // base game: the map's .map file next to tags.dat holds a default map variant, but its object indices were
                // written against another tags.dat build (Icebox's point at riverworld waterfalls and ElDewrito reforge
                // blocks), so it is off by default; the base maps carry their own objects in the scenario
                var mapFile = System.IO.Path.Combine(System.IO.Path.GetDirectoryName(Program.SourcePath), System.IO.Path.GetFileName(scenarioName) + ".map");
                try { using (var fs = System.IO.File.OpenRead(mapFile)) { var mf = new MapFile(); mf.Read(new TagTool.IO.EndianReader(fs, TagTool.IO.EndianFormat.LittleEndian)); v = mf.MapFileBlf?.MapVariant?.MapVariant; } }
                catch (Exception ex) { log.Add($"object layout: {mapFile}: {ex.Message}"); }
            }
            return v;
        }
        public static Func<int, bool> IsConverted = _ => false;
        public static void Add(GameCache ho, Scenario scn, string scenarioName, Dictionary<string, string> subst, Dictionary<string, string> owner, Func<string, CachedTag> stockTag, Func<CachedTag, bool> stockRef, List<string> log, List<string> unresolved)
        {
            var v = ReadVariant(ho, scenarioName, log);
            if (v == null) { log.Add("object layout: no map variant used for " + scenarioName + " (the scenario's own placements stay)"); v = new MapVariant { Objects = new VariantObjectDatum[0], Quotas = new VariantObjectQuota[0] }; }
            // extra placements from the map cfg ("place <grp:stock name> x y z yaw"), as variant objects of the stock tag
            var extraKeys = new Dictionary<int, string>();
            if (Extra.Count > 0)
            {
                var objs = v.Objects.ToList(); var quotas = v.Quotas.ToList();
                foreach (var e in Extra)
                {
                    int qi = quotas.Count; quotas.Add(new VariantObjectQuota { ObjectDefinitionIndex = -1000 - qi }); extraKeys[-1000 - qi] = e.key;
                    double yr = e.yaw * Math.PI / 180;
                    objs.Add(new VariantObjectDatum { QuotaIndex = qi, Position = new RealPoint3d((float)e.x, (float)e.y, (float)e.z), Forward = new RealVector3d((float)Math.Cos(yr), (float)Math.Sin(yr), 0), Up = new RealVector3d(0, 0, 1), Properties = new VariantMultiplayerProperties { Team = MultiplayerTeamDesignator.Neutral, EngineFlags = (GameEngineSubTypeFlags)0x3FF } });
                }
                v.Objects = objs.ToArray(); v.Quotas = quotas.ToArray();
                log.Add($"object layout: {Extra.Count} placements added from the map cfg");
            }
            int added = 0, skipped = 0, convertedPlaced = 0; var counts = new Dictionary<string, int>();
            // unique ids continue after the scenario's own (stock: small indices, e.g. Sandbox 17..608); the earlier fixed
            // start at 0x4000 (index 16384+) is suspected of breaking Forge's object list (Void: Forge could not create any
            // object, user play test 2026-11-23)
            int maxUid = 0;
            foreach (var f in typeof(Scenario).GetFields())
                if (f.GetValue(scn) is System.Collections.IEnumerable list && !(list is string))
                    foreach (var o in list) if (o is ScenarioInstance si0 && si0.UniqueHandle.Index != 0xFFFF) maxUid = Math.Max(maxUid, si0.UniqueHandle.Index);
            ushort uid = (ushort)(maxUid + 1);
            short Palette(List<ScenarioPaletteEntry> pal, CachedTag t)
            {
                int k = pal.FindIndex(p => ReferenceEquals(p.Object, t)); if (k >= 0) return (short)k;
                pal.Add(new ScenarioPaletteEntry { Object = t, Padding = new byte[32] }); return (short)(pal.Count - 1);
            }
            foreach (var o in v.Objects)
            {
                if (o == null || o.QuotaIndex < 0 || o.QuotaIndex >= v.Quotas.Length) continue;
                int ti = v.Quotas[o.QuotaIndex].ObjectDefinitionIndex;
                string ek = extraKeys.TryGetValue(ti, out var ekv) ? ekv : null;
                var hoTag = ek == null && ti >= 0 && ti < ho.TagCache.Count ? ho.TagCache.GetTag(ti) : null;
                string g = ek != null ? ek.Substring(0, 4) : hoTag?.Group.Tag.ToString();
                if ((hoTag == null && ek == null) || !(g == "scen" || g == "bloc" || g == "mach" || g == "ctrl" || g == "weap" || g == "eqip" || g == "vehi")) { skipped++; unresolved.Add($"object layout: entry for tag {ti} ({(hoTag == null ? "not in the package" : g + ":" + hoTag.Name)}) left out"); continue; }
                string key = ek ?? g + ":" + hoTag.Name;
                if (subst.TryGetValue(key, out var s)) key = s.Contains(":") ? s : g + ":" + s;
                var t = owner.ContainsKey(key) ? stockTag(key) : null;
                bool conv = false;
                if (t == null && ek != null && ho.TagCache.TryGetTag(ek.Substring(5) + "." + g, out var et) && IsConverted(et.Index)) hoTag = et;   // cfg placement of a converted piece
                if (t == null && hoTag != null && key == g + ":" + hoTag.Name && IsConverted(hoTag.Index)) { t = hoTag; conv = true; }   // map piece converted from the source
                else if (t == null || !stockRef(t)) { skipped++; unresolved.Add($"object layout: no stock Halo 3 {key}"); continue; }
                if (conv) convertedPlaced++;
                // facing: yaw/pitch from forward, roll from up
                var f = o.Forward; var u = o.Up;
                double yaw = Math.Atan2(f.J, f.I), pitch = Math.Asin(Math.Max(-1, Math.Min(1, f.K)));
                double[] left0 = { -Math.Sin(yaw), Math.Cos(yaw), 0 }, up0 = { -Math.Cos(yaw) * Math.Sin(pitch), -Math.Sin(yaw) * Math.Sin(pitch), Math.Cos(pitch) };
                double roll = Math.Atan2(-(u.I * left0[0] + u.J * left0[1] + u.K * left0[2]), u.I * up0[0] + u.J * up0[1] + u.K * up0[2]);
                var p = o.Properties ?? new VariantMultiplayerProperties();
                var mp = new MultiplayerObjectProperties
                {
                    // stock stores "all game types" as 0; ElDewrito as every bit set
                    EngineFlags = ((ushort)p.EngineFlags & 0x3FF) == 0x3FF ? 0 : (GameEngineSubTypeFlags)(ushort)p.EngineFlags,
                    Team = g == "weap" || g == "eqip" ? MultiplayerTeamDesignator.Neutral : p.Team, SpawnTime = p.SpawnTime, SpawnOrder = (sbyte)p.SharedStorage,
                    Shape = p.Boundary?.Type ?? MultiplayerObjectBoundaryShape.None, BoundaryWidthRadius = p.Boundary?.WidthRadius ?? 0, BoundaryBoxLength = p.Boundary?.BoxLength ?? 0,
                    BoundaryPositiveHeight = p.Boundary?.PositiveHeight ?? 0, BoundaryNegativeHeight = p.Boundary?.NegativeHeight ?? 0, MapVariantParent = new ScenarioObjectParentStruct(),
                    TeleporterChannel = (sbyte)p.SharedStorage
                };
                void Common(ScenarioInstance si, short pal, string typeName)
                {
                    si.PaletteIndex = pal; si.NameIndex = -1; si.Position = o.Position;
                    si.Rotation = new RealEulerAngles3d(Angle.FromDegrees((float)(yaw * 180 / Math.PI)), Angle.FromDegrees((float)(pitch * 180 / Math.PI)), Angle.FromDegrees((float)(roll * 180 / Math.PI)));
                    si.NodeOrientations = new List<ObjectNodeOrientation>(); si.UniqueHandle = new DatumHandle(0x1004, uid); uid++;   // salt as on stock Sandbox weapons
                    si.OriginBspIndex = -1; si.EditorFolder = -1; si.ParentId = new ScenarioObjectParentStruct();
                    // every per-game variant of the type set by name (the per-game fix step later copies the source game's field)
                    si.ObjectType = new TagTool.Tags.Definitions.GameObjectType8();
                    foreach (var fld in si.ObjectType.GetType().GetFields()) if (fld.FieldType.IsEnum && Enum.IsDefined(fld.FieldType, typeName)) fld.SetValue(si.ObjectType, Enum.Parse(fld.FieldType, typeName));
                    // stock Guardian defaults: scale 0 (= 1), source editor, attachable to the BSP, placement flag 0x100 on items
                    si.Scale = 0; si.Source = ScenarioInstance.SourceValue.Editor; si.CanAttachToBspFlags = 1;
                    si.PlacementFlags = new ObjectPlacementFlags(); if (typeName != "Scenery") si.PlacementFlags.Flags = (ObjectPlacementFlags.ObjectLocationPlacementFlags)0x100;
                }
                switch (g)
                {
                    case "scen": { var si = new SceneryInstance { Multiplayer = mp, PathfindingReferences = new List<PathfindingReference>() }; Common(si, Palette(scn.SceneryPalette, t), "Scenery"); scn.Scenery.Add(si); break; }
                    case "bloc": { var si = new CrateInstance { Multiplayer = mp, PathfindingReferences = new List<PathfindingReference>() }; Common(si, Palette(scn.CratePalette, t), "Crate"); scn.Crates.Add(si); break; }
                    case "weap": { var si = new WeaponInstance { Multiplayer = mp }; Common(si, Palette(scn.WeaponPalette, t), "Weapon"); scn.Weapons.Add(si); break; }
                    case "eqip": { var si = new EquipmentInstance { Multiplayer = mp }; Common(si, Palette(scn.EquipmentPalette, t), "Equipment"); scn.Equipment.Add(si); break; }
                    case "mach": { var si = new MachineInstance { PowerGroup = -1, PositionGroup = -1, Multiplayer = mp, PathfindingReferences = new List<MachineInstance.PathfindingReference>() }; Common(si, Palette(scn.MachinePalette, t), "Machine"); scn.Machines.Add(si); break; }
                    case "ctrl": { var si = new ControlInstance { PowerGroup = -1, PositionGroup = -1, Multiplayer = mp }; Common(si, Palette(scn.ControlPalette, t), "Control"); scn.Controls.Add(si); break; }
                    case "vehi": { var si = new VehicleInstance { Multiplayer = mp }; Common(si, Palette(scn.VehiclePalette, t), "Vehicle"); scn.Vehicles.Add(si); break; }
                }
                added++; counts[key] = counts.TryGetValue(key, out var n) ? n + 1 : 1;
            }
            log.Add($"object layout: {added} of {v.VariantObjectCount} map variant objects placed ({convertedPlaced} of them map pieces converted from the source, the rest stock Halo 3), {skipped} left out");
            foreach (var kv in counts.OrderByDescending(x => x.Value)) log.Add($"  placed {kv.Value} x {kv.Key}");
        }
    }
}
