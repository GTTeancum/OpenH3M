// MCC input adapter for TheGuardians/TagTool ReachLightmapConverter.cs,
// revision ce2dc6ac13072b160752af618ea1dc143e2727ac. Conversion and compression
// remain in TagTool; source arrays are linear MCC BC blocks, not Xenos tiles.
using System;
using System.Reflection;
using TagTool.Bitmaps;
using TagTool.Cache;
using TagTool.Common;
using TagTool.Lighting;

public static class ReachMccLightmapBridge
{
    public static unsafe float[] DecodeIntensity(byte[] data, int width, int height)
    {
        if (width <= 0 || height <= 0 || width % 4 != 0 || height % 4 != 0 ||
            data.Length != checked(width * height))
            throw new ArgumentException("Expected one block-aligned BC3 layer");
        var result = new float[checked(width * height * 4)];
        fixed (float* output = result)
        fixed (byte* input = data)
            DxtCompression.DecompressImage(output, width, height, input);
        return result;
    }

    public static ReachLightmapConverter.ConversionResult Convert(
        byte[] directionData, byte[] intensityData, int width, int height, float brightness)
    {
        int count = checked(width * height);
        if (directionData.Length != count || intensityData.Length != checked(count * 3) ||
            !float.IsFinite(brightness) || brightness < 0)
            throw new ArgumentException("Invalid MCC DualVMF pair");
        var directionBytes = BitmapCompression.Decompress(directionData, width, height,
            BitmapFormat.DxnMonoAlpha, CacheVersion.HaloReach, CachePlatform.MCC);
        var intensity = new float[3][];
        for (int layer = 0; layer < 3; layer++)
        {
            var bytes = new byte[count];
            Buffer.BlockCopy(intensityData, layer * count, bytes, 0, count);
            intensity[layer] = DecodeIntensity(bytes, width, height);
        }
        // Bind the reference sample decoder once, avoiding per-pixel reflection
        // and avoiding a second implementation of Reach's lighting equations.
        var method = typeof(ReachLightmapConverter).GetMethod("DecompressVmfLightmapSample",
            BindingFlags.Static | BindingFlags.NonPublic);
        if (method == null) throw new MissingMethodException("Reference VMF sample decoder");
        var decode = (Func<ReachLightmapConverter.Float4, ReachLightmapConverter.Float4,
            ReachLightmapConverter.Float4, ReachLightmapConverter.Float4, float, DualVmfBasis>)
            method.CreateDelegate(typeof(Func<ReachLightmapConverter.Float4, ReachLightmapConverter.Float4,
            ReachLightmapConverter.Float4, ReachLightmapConverter.Float4, float, DualVmfBasis>));
        var colors = new RealRgbColor[5][];
        for (int i = 0; i < 5; i++) colors[i] = new RealRgbColor[count];
        for (int p = 0; p < count; p++)
        {
            int at = p * 4;
            var d = new ReachLightmapConverter.Float4(directionBytes[at] / 255f,
                directionBytes[at+1] / 255f, directionBytes[at+2] / 255f, directionBytes[at+3] / 255f);
            var vmf = decode(d, Sample(intensity[0], at), Sample(intensity[1], at),
                Sample(intensity[2], at), brightness);
            var sh = VmfConversion.ConvertVmfLightprobe(vmf);
            SphericalHarmonics.QudraticToLinearAndIntensity(sh, out var linear, out var dominant);
            for (int i = 0; i < 4; i++)
                colors[i][p] = CheckedColor(sh.R[i], sh.G[i], sh.B[i]);
            colors[4][p] = CheckedColor(dominant.Red, dominant.Green, dominant.Blue);
        }
        var compressor = new LightmapCompressor();
        compressor.MaxDegreeOfParallelism = 2;
        compressor.ProgressUpdateInterval = 10000;
        compressor.ProgressUpdated += value => Console.WriteLine("Lightmap compression {0:F1}%", value * 100);
        for (int i = 0; i < 5; i++)
            compressor.AddTask(new LightmapCompressionTask(i, colors[i], width, height));
        compressor.Run();
        var result = new ReachLightmapConverter.ConversionResult();
        result.Width = width; result.Height = height;
        result.MaxLs = new float[5];
        result.LinearSH = new byte[checked(count * 8)];
        result.Intensity = new byte[checked(count * 2)];
        for (int i = 0; i < 5; i++)
        {
            var task = compressor.Tasks[i];
            if (task.Dxt0.Length != count || task.Dxt1.Length != count)
                throw new InvalidOperationException("Unexpected compressed layer size");
            result.MaxLs[i] = task.MaxL;
            var destination = i == 4 ? result.Intensity : result.LinearSH;
            int offset = i == 4 ? 0 : i * count * 2;
            Buffer.BlockCopy(task.Dxt0, 0, destination, offset, count);
            Buffer.BlockCopy(task.Dxt1, 0, destination, offset + count, count);
        }
        return result;
    }
    private static ReachLightmapConverter.Float4 Sample(float[] data, int at) =>
        new ReachLightmapConverter.Float4(data[at], data[at+1], data[at+2], data[at+3]);
    private static RealRgbColor CheckedColor(float r, float g, float b)
    {
        if (!float.IsFinite(r) || !float.IsFinite(g) || !float.IsFinite(b))
            throw new InvalidOperationException("Nonfinite converted lightmap coefficient");
        return new RealRgbColor(r, g, b);
    }
}
