// geomprobe <pak> <360 map> <sbsp name> [mesh]: the same mesh's first vertices read from the Halo Online source and
// from the converted 360 map, both through TagTool's vertex readers, plus the first indices
using System;
using System.IO;
using System.Linq;
using TagTool.Cache;
using TagTool.Cache.HaloOnline;
using TagTool.Geometry;
using TagTool.Tags.Definitions;

namespace Ho2H3
{
    static class GeomProbe
    {
        static void Dump(string label, GameCache c, Stream s, CachedTag t, int meshIndex)
        {
            RenderGeometry geo;
            if (t.IsInGroup("Lbsp")) geo = c.Deserialize<ScenarioLightmapBspData>(s, t).Geometry; else geo = c.Deserialize<ScenarioStructureBsp>(s, t).Geometry;
            var bsp = new { Geometry = geo };
            var def = c.ResourceCache.GetRenderGeometryApiResourceDefinition(bsp.Geometry.Resource);
            var mesh = bsp.Geometry.Meshes[meshIndex];
            Console.WriteLine($"== {label}: meshes {bsp.Geometry.Meshes.Count} compression {bsp.Geometry.Compression.Count} vb {def?.VertexBuffers?.Count} ib {def?.IndexBuffers?.Count}; mesh {meshIndex} type {mesh.Type} prim {mesh.IndexBufferType} vbIdx [{string.Join(",", mesh.VertexBufferIndices)}] ibIdx [{string.Join(",", mesh.IndexBufferIndices)}] parts {mesh.Parts.Count}");
            if (bsp.Geometry.Compression.Count > 0) { var cp = bsp.Geometry.Compression[0]; Console.WriteLine($"   compression0 X {cp.X} Y {cp.Y} Z {cp.Z} U {cp.U} V {cp.V}"); }
            {
                int vbi0 = mesh.VertexBufferIndices[0], ibi0 = mesh.IndexBufferIndices[0];
                int maxEnd = mesh.Parts.Max(pp => (int)pp.FirstIndex + (int)pp.IndexCount), subMax = mesh.SubParts.Count > 0 ? mesh.SubParts.Max(pp => (int)pp.FirstIndex + (int)pp.IndexCount) : 0;
                Console.WriteLine($"   parts {mesh.Parts.Count} subparts {mesh.SubParts.Count}; largest part end {maxEnd}, subpart end {subMax}; vertices {(vbi0 >= 0 && vbi0 < (def?.VertexBuffers?.Count ?? 0) ? def.VertexBuffers[vbi0].Definition.Count : -1)}; index buffer bytes {(ibi0 >= 0 && ibi0 < (def?.IndexBuffers?.Count ?? 0) ? def.IndexBuffers[ibi0].Definition.Data.Data.Length : -1)}; parts first indices [{string.Join(",", mesh.Parts.Select(pp => (int)pp.FirstIndex))}]");
            }
            if (mesh.Parts.Count > 0) { var p = mesh.Parts[0]; Console.WriteLine($"   part0 material {p.MaterialIndex}"); }
            int vbi = mesh.VertexBufferIndices[0]; if (vbi == ushort.MaxValue || def == null) return;
            var vb = def.VertexBuffers[vbi].Definition;
            Console.WriteLine($"   vb{vbi} format {vb.Format} count {vb.Count} bytes {vb.Data.Data.Length}");
            var r = VertexStreamFactory.Create(c.Version, c.Platform, new MemoryStream(vb.Data.Data));
            for (int k = 0; k < 3; k++)
            {
                if (vb.Format == VertexBufferFormat.Rigid) { var v = r.ReadRigidVertex(); Console.WriteLine($"   v{k} pos {v.Position} uv {v.Texcoord} n {v.Normal}"); }
                else if (vb.Format == VertexBufferFormat.World) { var v = r.ReadWorldVertex(); Console.WriteLine($"   v{k} pos {v.Position} uv {v.Texcoord} n {v.Normal}"); }
                else break;
            }
            int ibi = mesh.IndexBufferIndices[0];
            if (ibi != ushort.MaxValue && ibi < def.IndexBuffers.Count)
            {
                var ib = def.IndexBuffers[ibi].Definition; var d = ib.Data.Data;
                var e = c.Endianness == TagTool.IO.EndianFormat.BigEndian;
                Console.WriteLine($"   ib{ibi} format {ib.Format} bytes {d.Length} first: {string.Join(" ", Enumerable.Range(0, Math.Min(9, d.Length / 2)).Select(i => e ? (d[i * 2] << 8 | d[i * 2 + 1]) : (d[i * 2] | d[i * 2 + 1] << 8)))}");
            }
        }
        public static int Run(string[] a)
        {
            if (a[1] == "stock") { var sc = GameCache.Open(new FileInfo(a[2])); using (var ss = sc.OpenCacheRead()) Dump("stock", sc, ss, sc.TagCache.GetTag(a[3], "sbsp"), int.Parse(a[4])); return 0; }
            int mi = a.Length > 4 ? int.Parse(a[4]) : 0;
            if (a.Length > 5 && a[5] == "cluster") { var hc = GameCache.Open(new FileInfo(a[2])); using (var hs = hc.OpenCacheRead()) mi = hc.Deserialize<ScenarioStructureBsp>(hs, hc.TagCache.GetTag(a[3], "sbsp")).Clusters[mi].MeshIndex; Console.WriteLine("cluster mesh " + mi); }
            var ho = Program.OpenPak(a[1]);
            using (var s = ((GameCacheModPackage)ho).OpenCacheRead(new MemoryStream())) { var lb = ho.TagCache.NonNull().FirstOrDefault(x => x.IsInGroup("Lbsp") && x.Name.StartsWith(a[3], StringComparison.OrdinalIgnoreCase)); Console.WriteLine("lbsp: " + lb?.Name); Dump("Halo Online", ho, s, lb, mi); }
            var h3 = GameCache.Open(new FileInfo(a[2]));
            using (var s = h3.OpenCacheRead()) Dump("converted 360", h3, s, h3.TagCache.GetTag(a[3], "sbsp"), mi);
            return 0;
        }
    }
}
