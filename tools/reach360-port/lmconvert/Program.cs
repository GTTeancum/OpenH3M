// lmconvert <reach map> <out dir> [lightmap BSP name suffix ...]
// For each Reach lightmap BSP (Lbsp) tag (or the named ones): TagTool's ReachLightmapConverter turns its dual-VMF
// lightmap into Halo 3's form. Writes <out>\<lbsp leaf>.sh.bin (8 DXT5 slices: 4 SH coefficients x 2), .intensity.bin
// (2 DXT5 slices), and .json (width, height, the 5 coefficient-map scales). Pixel data is linear (untiled) DXT5.
// Also, following TagTool's documented Reach lightmap port (PortingContextGen3.Lighting.cs / VmfConversion.cs):
//   <leaf>.spv.bin     static per-vertex lighting: each Reach 6-byte VMF record -> TagTool's SH conversion -> Halo 3
//                      static per-vertex data (5 colours, EncodePixel32 for Halo 3 Xbox, written big-endian as TagTool's
//                      Xbox vertex stream reads them), cluster buffers padded by Per Vertex Offset x 0x14 bytes of 0xCD.
//                      Layout (little-endian): int count; per buffer: int reach vertex buffer index, int vertex count,
//                      int byte length, bytes.
//   <leaf>.probes.bin  instanced-geometry light probes: VmfConversion.ConvertHalfLightprobe -> Halo 3 0x48-byte probe
//                      (dominant direction, dominant intensity, 27 SH halves; big-endian). int count, then records.
using System;
using System.IO;
using System.Linq;
using TagTool.Cache;
using TagTool.Tags.Definitions;
using TagTool.Lighting;

if (args[0] == "--skya") { Skya.FromReach(args[1], args[2], args[3]); return; }
var map = args[0]; var outDir = args[1]; var only = args.Skip(2).ToArray();
Directory.CreateDirectory(outDir);
var cache = GameCache.Open(new FileInfo(map));
using var stream = cache.OpenCacheRead();
foreach (var t in cache.TagCache.TagTable.Where(t => t != null && t.Group != null && t.Group.Tag.ToString() == "Lbsp"))
{
    if (only.Length > 0 && !only.Any(o => t.Name.EndsWith(o, StringComparison.OrdinalIgnoreCase))) continue;
    var lbsp = cache.Deserialize<ScenarioLightmapBspData>(stream, t);
    if (lbsp.LightmapSHCoefficientsBitmap == null || lbsp.LightmapDominantLightDirectionBitmap == null) { Console.WriteLine($"{t.Name}: no lightmap bitmaps"); File.WriteAllText(Path.Combine(outDir, t.Name.Substring(t.Name.LastIndexOf((char)92) + 1) + ".none"), "no lightmap bitmaps"); continue; }
    var conv = new ReachLightmapConverter { MaxDegreeOfParallelism = Environment.ProcessorCount };
    var r = conv.Convert(cache, stream, lbsp);
    if (r == null) { Console.WriteLine($"{t.Name}: conversion failed"); continue; }
    var leaf = t.Name.Substring(t.Name.LastIndexOf((char)92) + 1);
    File.WriteAllBytes(Path.Combine(outDir, leaf + ".sh.bin"), r.LinearSH);
    File.WriteAllBytes(Path.Combine(outDir, leaf + ".intensity.bin"), r.Intensity);
    File.WriteAllText(Path.Combine(outDir, leaf + ".json"),
        $"{{\"name\":\"{t.Name.Replace("\\", "\\\\")}\",\"width\":{r.Width},\"height\":{r.Height},\"scales\":[{string.Join(",", r.MaxLs.Select(x => x.ToString(System.Globalization.CultureInfo.InvariantCulture)))}]}}");
    WritePerVertex(cache, lbsp, Path.Combine(outDir, leaf + ".spv.bin"));
    WriteProbes(lbsp.InstancedGeometryLightProbes.Select(p => p.VmfLightProbe).ToList(), Path.Combine(outDir, leaf + ".probes.bin"));
    Console.WriteLine($"{t.Name}: {r.Width}x{r.Height}, SH {r.LinearSH.Length} bytes, intensity {r.Intensity.Length} bytes, scales {string.Join(" ", r.MaxLs.Select(x => x.ToString("0.###")))}");
}

static void WritePerVertex(GameCache cache, ScenarioLightmapBspData lbsp, string path)
{
    var res = cache.ResourceCache.GetRenderGeometryApiResourceDefinition(lbsp.Geometry.Resource);
    var converted = new System.Collections.Generic.Dictionary<int, (int count, byte[] data)>();
    foreach (var e in lbsp.StaticPerVertexLightingBuffers)
    {
        int vb = e.VertexBufferIndexReach; if (vb < 0 || converted.ContainsKey(vb)) continue;
        var src = res.VertexBuffers[vb].Definition.Data.Data;
        float hdr = (float)BitConverter.UInt16BitsToHalf(e.HDRScalar);
        int n = src.Length / 6; var o = new byte[n * 20];
        for (int i = 0; i < n; i++)
        {
            int at = i * 6; int dir = src[at] & 0x7f;
            float dc = (((src[at] >> 7) & 1) | ((src[at + 1] & 1) << 1)) / 3.0f;
            float r1 = (float)Math.Pow(((src[at + 1] >> 1) & 31) / 31.0f, 2) * hdr;
            float g1 = (float)Math.Pow((((src[at + 1] >> 6) & 3) | ((src[at + 2] & 7) << 2)) / 31.0f, 2) * hdr;
            float b1 = (float)Math.Pow(((src[at + 2] >> 3) & 31) / 31.0f, 2) * hdr;
            float r0 = (float)Math.Pow(src[at + 3] / 255.0f, 2) * hdr;
            float g0 = (float)Math.Pow(src[at + 4] / 255.0f, 2) * hdr;
            float b0 = (float)Math.Pow(src[at + 5] / 255.0f, 2) * hdr;
            var vmf = new TagTool.Lighting.DualVmfBasis();
            vmf.Direct = new TagTool.Lighting.VmfLight { Direction = VmfConversion.GetStaticDirection(dir), AnalyticalMask = dc, Color = new TagTool.Common.RealRgbColor(r0, g0, b0), Bandwidth = 1.0f };
            vmf.Indirect = new TagTool.Lighting.VmfLight { Direction = new TagTool.Common.RealVector3d(0, 0, 1), AnalyticalMask = dc, Color = new TagTool.Common.RealRgbColor(r1, g1, b1), Bandwidth = 0.0f };
            var sh = VmfConversion.ConvertVmfLightprobe(vmf);
            TagTool.Common.SphericalHarmonics.QudraticToLinearAndIntensity(sh, out var linear, out var intensity);
            var spv = VmfConversion.CompressStaticPerVertex(intensity, linear, CacheVersion.Halo3Retail, CachePlatform.Original);
            uint[] c = { spv.Color1, spv.Color2, spv.Color3, spv.Color4, spv.Color5 };
            for (int k = 0; k < 5; k++) { o[i * 20 + k * 4] = (byte)(c[k] >> 24); o[i * 20 + k * 4 + 1] = (byte)(c[k] >> 16); o[i * 20 + k * 4 + 2] = (byte)(c[k] >> 8); o[i * 20 + k * 4 + 3] = (byte)c[k]; }
        }
        converted[vb] = (n, o);
    }
    // TagTool pads a cluster's buffer so it lines up 1:1 with the cluster mesh (parts below the offset are per-pixel)
    foreach (var cl in lbsp.ClusterStaticPerVertexLightingBuffers)
    {
        if (cl.StaticPerVertexLightingIndex < 0 || cl.PerVertexOffset <= 0) continue;
        int vb = lbsp.StaticPerVertexLightingBuffers[cl.StaticPerVertexLightingIndex].VertexBufferIndexReach;
        if (!converted.TryGetValue(vb, out var cv)) continue;
        var pad = Enumerable.Repeat((byte)0xCD, cl.PerVertexOffset * 0x14).ToArray();
        converted[vb] = (cv.count + cl.PerVertexOffset, pad.Concat(cv.data).ToArray());
    }
    using var w = new BinaryWriter(File.Create(path));
    w.Write(converted.Count);
    foreach (var kv in converted.OrderBy(k => k.Key)) { w.Write(kv.Key); w.Write(kv.Value.count); w.Write(kv.Value.data.Length); w.Write(kv.Value.data); }
    Console.WriteLine($"  static per-vertex: {converted.Count} buffers, {converted.Sum(k => k.Value.count)} vertices");
}

static void WriteProbes(System.Collections.Generic.List<TagTool.Tags.Definitions.DualVmfLightProbe> probes, string path)
{
    using var w = new BinaryWriter(File.Create(path));
    w.Write(probes.Count);
    void H(ushort v) { w.Write((byte)(v >> 8)); w.Write((byte)v); }
    foreach (var p in probes)
    {
        var h = VmfConversion.ConvertHalfLightprobe(p);
        for (int i = 0; i < 3; i++) H(h.DominantLightDirection[i]); H(0);
        for (int i = 0; i < 3; i++) H(h.DominantLightIntensity[i]); H(0);
        for (int i = 0; i < 9; i++) H(h.SHRed[i]);
        for (int i = 0; i < 9; i++) H(h.SHGreen[i]);
        for (int i = 0; i < 9; i++) H(h.SHBlue[i]);
        H(0);
    }
    Console.WriteLine($"  light probes: {probes.Count}");
}
