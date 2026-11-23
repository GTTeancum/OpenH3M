// --skya <reach map> <scenario name> <out.txt>: TagTool's skya generation for Reach sources (PortingContextGen3.Scenario.cs,
// "Generate skya from fog parameters"), followed by TagTool's SkyAtmParameters.Postprocess(). Writes Halo 3 field values
// as lines "<field path>=<value>" ("#<block>=<count>", references "grp:name" or null, string ids "sid:name") for
// ReachPort's skya rule (ReachScenario.SkyaPost).
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using TagTool.Cache;
using TagTool.Common;
using TagTool.Tags.Definitions;

static class Skya
{
    public static void FromReach(string map, string scnrName, string outPath)
    {
        var cache = GameCache.Open(new FileInfo(map));
        using var stream = cache.OpenCacheRead();
        var scnr = cache.Deserialize<Scenario>(stream, cache.TagCache.GetTag<Scenario>(scnrName));
        var skya = new SkyAtmParameters { AtmosphereSettings = new(), UnderwaterSettings = new() };
        string fogBitmap = null; var names = new List<string>(); var weather = new List<string>(); var uwNames = new List<string>();
        if (scnr.AtmosphereGlobals != null)
        {
            var atgf = cache.Deserialize<AtmosphereGlobals>(stream, scnr.AtmosphereGlobals);
            skya.Flags = SkyAtmParameters.SkyAtmFlags.None;
            fogBitmap = atgf.FogBitmap?.Name;
            skya.TextureRepeatRate = atgf.TextureRepeatRate; skya.DistanceBetweenSheets = atgf.DistanceBetweenSheets; skya.DepthFadeFactor = atgf.DepthFadeFactor;
            skya.ClusterSearchRadius = 25.0f; skya.TransparentSortDistance = atgf.TransparentSortDistance; skya.TransparentSortLayer = atgf.TransparentSortLayer;
            foreach (var u in atgf.UnderwaterSettings)
            { skya.UnderwaterSettings.Add(new SkyAtmParameters.UnderwaterBlock { Name = u.Name, Murkiness = u.Murkiness, FogColor = u.FogColor }); uwNames.Add(cache.StringTable.GetString(u.Name)); }
        }
        foreach (var sd in scnr.StructureDesigns)
        {
            if (sd.StructureDesign == null) continue;
            var sddt = cache.Deserialize<StructureDesign>(stream, sd.StructureDesign);
            foreach (var w in sddt.WaterInstances)
            {
                var wn = cache.StringTable.GetString(sddt.WaterGroups[w.WaterNameIndex].Name);
                if (uwNames.Contains(wn)) continue;
                skya.UnderwaterSettings.Add(new SkyAtmParameters.UnderwaterBlock { Name = sddt.WaterGroups[w.WaterNameIndex].Name, Murkiness = w.FogMurkiness, FogColor = w.FogColor });
                uwNames.Add(wn);
            }
        }
        foreach (var ap in scnr.Atmosphere)
        {
            while (ap.AtmosphereSettingIndex >= skya.AtmosphereSettings.Count) { skya.AtmosphereSettings.Add(new SkyAtmParameters.AtmosphereProperty()); names.Add(""); weather.Add(null); }
            if (ap.AtmosphereFog == null) continue;
            var fogg = cache.Deserialize<AtmosphereFog>(stream, ap.AtmosphereFog);
            var a = skya.AtmosphereSettings[ap.AtmosphereSettingIndex];
            a.Flags |= SkyAtmParameters.AtmosphereProperty.AtmosphereFlags.EnableAtmosphere;
            names[ap.AtmosphereSettingIndex] = cache.StringTable.GetString(ap.Name);
            if (fogg.Flags.HasFlag(AtmosphereFog.AtmosphereFogFlags.PatchyFogEnabled)) a.Flags |= SkyAtmParameters.AtmosphereProperty.AtmosphereFlags.PatchyFog;
            a.SheetDensity = fogg.PatchyFog.SheetDensity; a.FullIntensityHeight = fogg.PatchyFog.FullIntensityHeight;
            a.HalfIntensityHeight = fogg.PatchyFog.HalfIntensityHeight; a.WindDirection = fogg.PatchyFog.WindDirection;
            weather[ap.AtmosphereSettingIndex] = fogg.WeatherEffect?.Name;
            AtmosphereFog.FogSettings fs = null;
            if (fogg.Flags.HasFlag(AtmosphereFog.AtmosphereFogFlags.GroundFogEnabled)) fs = fogg.GroundFog;
            else if (fogg.Flags.HasFlag(AtmosphereFog.AtmosphereFogFlags.SkyFogEnabled)) fs = fogg.SkyFog;
            if (fs != null)
            {
                a.Flags |= SkyAtmParameters.AtmosphereProperty.AtmosphereFlags.OverrideRealSunValues;
                a.Color = fs.FogColor; a.Intensity = 1.0f; a.SunAnglePitch = 0.0f; a.SunAngleYaw = 0.0f;
                if (scnr.SkyReferences.Count > 0 && scnr.SkyReferences[0].SkyObject != null)
                {
                    var obj = (GameObject)cache.Deserialize(stream, scnr.SkyReferences[0].SkyObject);
                    var hlmt = cache.Deserialize<Model>(stream, obj.Model);
                    var mode = cache.Deserialize<RenderModel>(stream, hlmt.RenderModel);
                    if (mode.LightgenLights != null && mode.LightgenLights.Count > 0)
                    {
                        var d = mode.LightgenLights.Last().Direction;
                        a.SunAnglePitch = (float)(Math.Asin(d.K) * (180.0f / Math.PI)); if (a.SunAnglePitch < 0.0f) a.SunAnglePitch = -a.SunAnglePitch;
                        a.SunAngleYaw = (float)(Math.Atan2(d.J, d.I) * (180.0f / Math.PI));
                    }
                }
                a.SeaLevel = fs.BaseHeight; a.RayleignHeightScale = fs.FogHeight; a.MieHeightScale = fs.FogHeight; a.MaxFogThickness = fs.FogThickness * 65536.0f;
            }
            a.RayleighMultiplier = 0.05f; a.MieMultiplier = 0.025f; a.SunPhaseFunction = 0.2f; a.Desaturation = 0.0f; a.DistanceBias = fogg.DistanceBias;
        }
        skya.Postprocess();

        var inv = System.Globalization.CultureInfo.InvariantCulture;
        string F(float v) { var t = v.ToString("R", inv); return t.Contains('.') || t.Contains('E') ? t : t + ".0"; }
        string V(RealVector3d v) => $"{F(v.I)} {F(v.J)} {F(v.K)}";
        var o = new List<string>
        {
            $"Flags={(int)skya.Flags}", $"Fog Bitmap={(fogBitmap == null ? "null" : "bitm:" + fogBitmap)}", $"Texture Repeat Rate={F(skya.TextureRepeatRate)}",
            $"Distance Between Sheets={F(skya.DistanceBetweenSheets)}", $"Depth Fade Factor={F(skya.DepthFadeFactor)}", $"Cluster Search Radius={F(skya.ClusterSearchRadius)}",
            $"Falloff Start Distance={F(skya.FalloffStartDistance)}", $"Distance Falloff Power={F(skya.DistanceFalloffPower)}",
            $"Transparent Sort Distance={F(skya.TransparentSortDistance)}", $"Transparent Sort Layer={(int)skya.TransparentSortLayer}",
            $"#Atmosphere Settings={skya.AtmosphereSettings.Count}", $"#Underwater Settings={skya.UnderwaterSettings.Count}"
        };
        for (int i = 0; i < skya.AtmosphereSettings.Count; i++)
        {
            var a = skya.AtmosphereSettings[i]; string p = $"Atmosphere Settings[{i}]/";
            o.AddRange(new[] {
                $"{p}Flags={(int)a.Flags}", $"{p}Name=sid:{names[i]}", $"{p}Sun Angle Pitch={F(a.SunAnglePitch)}", $"{p}Sun Angle Yaw={F(a.SunAngleYaw)}",
                $"{p}Color={F(a.Color.Red)} {F(a.Color.Green)} {F(a.Color.Blue)}", $"{p}Intensity={F(a.Intensity)}", $"{p}Sea Level={F(a.SeaLevel)}",
                $"{p}Rayleign Height Scale={F(a.RayleignHeightScale)}", $"{p}Mie Height Scale={F(a.MieHeightScale)}", $"{p}Rayleigh Multiplier={F(a.RayleighMultiplier)}",
                $"{p}Mie Multiplier={F(a.MieMultiplier)}", $"{p}Sun Phase Function={F(a.SunPhaseFunction)}", $"{p}Desaturation={F(a.Desaturation)}",
                $"{p}Distance Bias={F(a.DistanceBias)}", $"{p}Max Fog Thickness={F(a.MaxFogThickness)}", $"{p}Beta M={V(a.BetaM)}", $"{p}Beta P={V(a.BetaP)}",
                $"{p}Beta M Theta Prefix={V(a.BetaMThetaPrefix)}", $"{p}Beta P Theta Prefix={V(a.BetaPThetaPrefix)}", $"{p}Sheet Density={F(a.SheetDensity)}",
                $"{p}Full Intensity Height={F(a.FullIntensityHeight)}", $"{p}Half Intensity Height={F(a.HalfIntensityHeight)}", $"{p}Wind Direction={V(a.WindDirection)}",
                $"{p}Weather Effect={(weather[i] == null ? "null" : "effe:" + weather[i])}" });
        }
        for (int i = 0; i < skya.UnderwaterSettings.Count; i++)
        {
            var u = skya.UnderwaterSettings[i]; string p = $"Underwater Settings[{i}]/";
            o.AddRange(new[] { $"{p}Name=sid:{uwNames[i]}", $"{p}Murkiness={F(u.Murkiness)}", $"{p}Fog Color={F(u.FogColor.Red)} {F(u.FogColor.Green)} {F(u.FogColor.Blue)}" });
        }
        File.WriteAllLines(outPath, o);
        Console.WriteLine($"skya: {skya.AtmosphereSettings.Count} atmosphere settings, {skya.UnderwaterSettings.Count} underwater settings -> {outPath}");
    }
}
