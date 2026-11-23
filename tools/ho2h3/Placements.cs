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
        public static void Add(GameCache ho, Scenario scn, string scenarioName, Dictionary<string, string> subst, Dictionary<string, string> owner, Func<string, CachedTag> stockTag, Func<CachedTag, bool> stockRef, List<string> log, List<string> unresolved)
        {
            var pak = ho as GameCacheModPackage; if (pak == null) return;
            MapVariant v = null;
            for (int i = 0; i < pak.BaseModPackage.MapFileStreams.Count && v == null; i++)
            {
                try { var mf = VariantProbe.Read(pak, i); if (string.Equals(mf.Header?.GetScenarioPath(), scenarioName, StringComparison.OrdinalIgnoreCase)) v = mf.MapFileBlf?.MapVariant?.MapVariant; } catch { }
            }
            if (v == null) { log.Add("object layout: no map variant for " + scenarioName); return; }
            int added = 0, skipped = 0; var counts = new Dictionary<string, int>(); ushort uid = 0x4000;
            short Palette(List<ScenarioPaletteEntry> pal, CachedTag t)
            {
                int k = pal.FindIndex(p => ReferenceEquals(p.Object, t)); if (k >= 0) return (short)k;
                pal.Add(new ScenarioPaletteEntry { Object = t, Padding = new byte[32] }); return (short)(pal.Count - 1);
            }
            foreach (var o in v.Objects)
            {
                if (o == null || o.QuotaIndex < 0 || o.QuotaIndex >= v.Quotas.Length) continue;
                int ti = v.Quotas[o.QuotaIndex].ObjectDefinitionIndex;
                var hoTag = ti >= 0 && ti < ho.TagCache.Count ? ho.TagCache.GetTag(ti) : null;
                string g = hoTag?.Group.Tag.ToString();
                if (hoTag == null || !(g == "scen" || g == "bloc" || g == "weap" || g == "eqip" || g == "vehi")) { skipped++; unresolved.Add($"object layout: entry for tag {ti} ({(hoTag == null ? "not in the package" : g + ":" + hoTag.Name)}) left out"); continue; }
                string key = g + ":" + hoTag.Name;
                if (subst.TryGetValue(key, out var s)) key = s.Contains(":") ? s : g + ":" + s;
                var t = owner.ContainsKey(key) ? stockTag(key) : null;
                if (t == null || !stockRef(t)) { skipped++; unresolved.Add($"object layout: no stock Halo 3 {key}"); continue; }
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
                    si.NodeOrientations = new List<ObjectNodeOrientation>(); si.UniqueHandle = new DatumHandle(uid, uid); uid++;
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
                    case "vehi": { var si = new VehicleInstance { Multiplayer = mp }; Common(si, Palette(scn.VehiclePalette, t), "Vehicle"); scn.Vehicles.Add(si); break; }
                }
                added++; counts[key] = counts.TryGetValue(key, out var n) ? n + 1 : 1;
            }
            log.Add($"object layout: {added} of {v.VariantObjectCount} map variant objects placed as stock Halo 3 objects, {skipped} left out");
            foreach (var kv in counts.OrderByDescending(x => x.Value)) log.Add($"  placed {kv.Value} x {kv.Key}");
        }
    }
}
