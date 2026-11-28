// Cluster instanced-geometry physics. Halo 3 finds a cluster's instances (for collision, and for drawing through the
// cluster mesh's instance buckets) through the cluster's "instanced geometry physics" MOPP, whose keys are instance
// indices (stock Guardian: 454 of its 479 instances appear in cluster MOPPs). Halo Online leaves these empty for the
// Reach ports, so a player stands on no instanced geometry. Each cluster gets a MOPP built with TagTool's MOPP tool over
// every instance in index order: an instance whose world box (its mesh's compression bounds through the instance
// transform) overlaps the cluster's bounds is one primitive through the box's eight corners; any other instance is a degenerate triangle
// just outside the cluster (the tool keys primitives by input order), so a query inside the cluster never reaches it.
// Same rule as the Reach route (ReachPort ClusterMopps.cs), on TagTool's typed definitions. Map-agnostic.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using TagTool.Cache;
using TagTool.Common;
using TagTool.Havok;
using TagTool.Geometry;
using TagTool.Tags;
using TagTool.Tags.Definitions;
using TagTool.Tags.Resources;

namespace Ho2H3
{
    public static class ClusterMopps
    {
        public static string MoppExe => Path.Combine(AppContext.BaseDirectory, "Tools", "mopp.exe");

        public static void Build(CachedTag self, ScenarioStructureBsp bsp, StructureBspTagResources res, List<string> log)
        {
            var inst = bsp.InstancedGeometryInstances; var comp = bsp.Geometry?.Compression;
            if (inst == null || inst.Count == 0 || bsp.Clusters == null || res?.InstancedGeometry == null) return;
            int ni = inst.Count, noBox = 0;
            var lo = new float[ni][]; var hi = new float[ni][];
            for (int i = 0; i < ni; i++)
            {
                int d = inst[i].DefinitionIndex; if (d < 0 || d >= res.InstancedGeometry.Count) { noBox++; continue; }
                // world box: the render mesh's compression bounds and the collision vertices, through the instance transform
                // (collision-only pieces, e.g. Reflection's invisible stair ramps, have an empty render mesh)
                var def = res.InstancedGeometry[d]; int ci = def.CompressionIndex;
                float s = inst[i].Scale == 0 ? 1 : inst[i].Scale; var m = inst[i].Matrix;
                float[][] rows = { new[] { m.m11, m.m12, m.m13 }, new[] { m.m21, m.m22, m.m23 }, new[] { m.m31, m.m32, m.m33 }, new[] { m.m41, m.m42, m.m43 } };
                var wl = new[] { float.MaxValue, float.MaxValue, float.MaxValue }; var wh = new[] { float.MinValue, float.MinValue, float.MinValue };
                void Add(float px, float py, float pz) { for (int a = 0; a < 3; a++) { float w = s * (px * rows[0][a] + py * rows[1][a] + pz * rows[2][a]) + rows[3][a]; wl[a] = Math.Min(wl[a], w); wh[a] = Math.Max(wh[a], w); } }
                bool any = false;
                if (comp != null && ci >= 0 && ci < comp.Count && def.MeshIndex >= 0 && def.MeshIndex < bsp.Geometry.Meshes.Count && bsp.Geometry.Meshes[def.MeshIndex].Parts.Count > 0)
                {
                    var c = comp[ci]; any = true;
                    for (int k = 0; k < 8; k++) Add((k & 1) != 0 ? c.X.Upper : c.X.Lower, (k & 2) != 0 ? c.Y.Upper : c.Y.Lower, (k & 4) != 0 ? c.Z.Upper : c.Z.Lower);
                }
                if (def.CollisionInfo?.Vertices != null) foreach (var v in def.CollisionInfo.Vertices) { Add(v.Point.X, v.Point.Y, v.Point.Z); any = true; }
                if (!any) { noBox++; continue; }
                lo[i] = wl; hi[i] = wh;
            }
            int built = 0, members = 0, bucketed = 0; var inAny = new HashSet<int>();
            for (int c = 0; c < bsp.Clusters.Count; c++)
            {
                var cl = bsp.Clusters[c]; const float pad = 0.25f;
                float[] b = { cl.BoundsX.Lower, cl.BoundsX.Upper, cl.BoundsY.Lower, cl.BoundsY.Upper, cl.BoundsZ.Lower, cl.BoundsZ.Upper };
                var mem = Enumerable.Range(0, ni).Where(i => lo[i] != null && lo[i][0] <= b[1] + pad && hi[i][0] >= b[0] - pad && lo[i][1] <= b[3] + pad && hi[i][1] >= b[2] - pad && lo[i][2] <= b[5] + pad && hi[i][2] >= b[4] - pad).ToList();
                if (mem.Count == 0) continue;
                // instance buckets on the cluster mesh (what Halo 3 draws with the cluster), when the source has none
                if (cl.MeshIndex >= 0 && cl.MeshIndex < bsp.Geometry.Meshes.Count)
                {
                    var mesh = bsp.Geometry.Meshes[cl.MeshIndex];
                    if (mesh.InstanceBuckets == null || mesh.InstanceBuckets.Count == 0)
                    {
                        mesh.InstanceBuckets = mem.GroupBy(i => inst[i].DefinitionIndex).Where(g => g.Key >= 0 && g.Key < res.InstancedGeometry.Count && res.InstancedGeometry[g.Key].MeshIndex >= 0 && res.InstancedGeometry[g.Key].MeshIndex < bsp.Geometry.Meshes.Count && bsp.Geometry.Meshes[res.InstancedGeometry[g.Key].MeshIndex].Parts.Count > 0).OrderBy(g => g.Key)
                            .Select(g => new Mesh.InstancedBucketBlock { MeshIndex = res.InstancedGeometry[g.Key].MeshIndex, DefinitionIndex = g.Key, Instances = g.OrderBy(x => x).Select(x => new Mesh.InstancedBucketBlock.InstanceIndexBlock { InstanceIndex = (short)x }).ToList() }).ToList();
                        bucketed++;
                    }
                }
                var set = new HashSet<int>(mem); foreach (var i in mem) inAny.Add(i);
                var verts = new List<float[]>(); var polys = new List<int[]>(); var outside = new[] { b[0] - 1f, b[2] - 1f, b[4] - 1f };
                for (int i = 0; i < ni; i++)
                {
                    int v0 = verts.Count;
                    // a member is one primitive through all eight corners of its box: a single triangle across the box
                    // (lo, hi, one more corner) leaves parts of the box outside its extent along the MOPP's diagonal split
                    // directions, so the cluster query never reached the instance there (Sword Base: the player fell
                    // through four stacked walkway pieces at one spot, 2026-11-23)
                    if (set.Contains(i)) { for (int k = 0; k < 8; k++) verts.Add(new[] { (k & 1) != 0 ? hi[i][0] : lo[i][0], (k & 2) != 0 ? hi[i][1] : lo[i][1], (k & 4) != 0 ? hi[i][2] : lo[i][2] }); polys.Add(new[] { v0, v0 + 1, v0 + 3, v0 + 2, v0 + 6, v0 + 7, v0 + 5, v0 + 4 }); }
                    else { verts.Add(outside); verts.Add(outside); verts.Add(outside); polys.Add(new[] { v0, v0 + 1, v0 + 2 }); }
                }
                var g0 = Generate(verts, polys);
                if (g0 == null) { log.Add($"cluster MOPP: {self.Name} cluster {c} generation failed"); continue; }
                var (info, code) = g0.Value;
                var p = cl.InstancedGeometryPhysics ?? new ScenarioStructureBsp.Cluster.InstancedGeometryPhysicsData();
                p.ReferencedObject = new HkpReferencedObject { ReferenceCount = 128 };
                p.Type = 2; p.DisableWelding = false; p.ClusterIndex = c; p.StructureBsp = self;
                if (p.Shape == null) p.Shape = new HkpMoppBvTreeShape();
                p.Shape.ReferencedObject = new HkpReferencedObject { ReferenceCount = 128 }; p.Shape.Type = 0x1B;
                p.MoppCodes = new List<TagHkpMoppCode> { new TagHkpMoppCode
                {
                    ReferencedObject = new HkpReferencedObject { ReferenceCount = 128 },
                    Info = new CodeInfo { Offset = new RealQuaternion(info[0], info[1], info[2], info[3]) },
                    ArrayBase = new HkArrayBase { Size = (uint)code.Length, CapacityAndFlags = (uint)code.Length | 0x80000000u },
                    Data = new TagBlock<byte>(CacheAddressType.Data, code.ToList())
                } };
                cl.InstancedGeometryPhysics = p;
                built++; members += mem.Count;
            }
            log.Add($"cluster MOPP: {self.Name}: built for {built} of {bsp.Clusters.Count} clusters ({members} memberships; {inAny.Count} of {ni} instances in some cluster; {noBox} without bounds); instance buckets added on {bucketed} cluster meshes");
        }

        // Structure physics MOPP over the structure collision BSP. Stock Halo 3 keys each structure surface as
        // 0x20050000 | surface index (Guardian; the Reach route matched it); Halo Online's uses another key layout, so the
        // MOPP is rebuilt: one primitive per surface in order (an invalid surface as a zero-area triangle on one of its own
        // vertices, keeping the numbering), then a leading re-offset (opcode 0x0B, 32-bit) adds 0x20050000 to every key.
        public static void BuildStructure(CachedTag self, ScenarioStructureBsp bsp, StructureBspTagResources res, List<string> log)
        {
            if (res?.CollisionBsps == null || res.CollisionBsps.Count == 0 || bsp.Physics == null) return;
            var c = res.CollisionBsps[0];
            var verts = c.Vertices.Select(v => new[] { v.Point.X, v.Point.Y, v.Point.Z }).ToList(); var polys = new List<int[]>(); int invalid = 0;
            for (int si = 0; si < c.Surfaces.Count; si++)
            {
                var sf = c.Surfaces[si]; var loop = new List<int>(); int e = sf.FirstEdge, guard = 0;
                do
                {
                    if (e < 0 || e >= c.Edges.Count || guard++ > 4096) { loop.Clear(); break; }
                    var ed = c.Edges[e];
                    if (ed.RightSurface == si) { loop.Add(ed.EndVertex); e = ed.ReverseEdge; } else { loop.Add(ed.StartVertex); e = ed.ForwardEdge; }
                } while (e != sf.FirstEdge);
                if (loop.Count < 3 || sf.Flags.HasFlag(TagTool.Geometry.BspCollisionGeometry.SurfaceFlags.Invalid)) { int v = loop.Count > 0 ? loop[0] : 0; polys.Add(new[] { v, v, v }); invalid++; }
                else polys.Add(loop.ToArray());
            }
            // placed pieces (Halo 3's tool, sapien 0x6A6240 / 0x6A6520 / 0x6A5EA0; COLLISION-360.md): after the structure
            // surfaces, one primitive per instance whose definition has collision surfaces, keyed 0x40000000 | instance,
            // over its child shape's box: the bsp physics box through the instance transform. Only instances with a bsp
            // physics entry (the 360 contact path 0x82270F48 reads it). The player's contacts with placed pieces come only
            // through these keys.
            int nS = polys.Count; var pieceOf = new List<int>();
            var inst = bsp.InstancedGeometryInstances;
            for (int i = 0; inst != null && i < inst.Count; i++)
            {
                var x = inst[i]; int d = x.DefinitionIndex;
                if (d < 0 || d >= (res.InstancedGeometry?.Count ?? 0) || !(res.InstancedGeometry[d].CollisionInfo?.Surfaces?.Count > 0)) continue;
                var bp = x.BspPhysics?.FirstOrDefault(); if (bp == null) continue;
                var gs = bp.GeometryShape; var ce = gs.AABB_Center; var he = gs.AABB_Half_Extents;
                if (he.I <= 0 && he.J <= 0 && he.K <= 0) continue;
                var m = x.Matrix; float[][] R = { new[] { m.m11, m.m12, m.m13 }, new[] { m.m21, m.m22, m.m23 }, new[] { m.m31, m.m32, m.m33 } }; float[] T = { m.m41, m.m42, m.m43 };
                var lo = new[] { float.MaxValue, float.MaxValue, float.MaxValue }; var hi = new[] { float.MinValue, float.MinValue, float.MinValue };
                for (int k = 0; k < 8; k++)
                {
                    float px = ce.I + ((k & 1) != 0 ? he.I : -he.I), py = ce.J + ((k & 2) != 0 ? he.J : -he.J), pz = ce.K + ((k & 4) != 0 ? he.K : -he.K);
                    for (int a = 0; a < 3; a++) { float w = px * R[0][a] + py * R[1][a] + pz * R[2][a] + T[a]; lo[a] = Math.Min(lo[a], w); hi[a] = Math.Max(hi[a], w); }
                }
                int v0 = verts.Count;
                for (int k = 0; k < 8; k++) verts.Add(new[] { (k & 1) != 0 ? hi[0] : lo[0], (k & 2) != 0 ? hi[1] : lo[1], (k & 4) != 0 ? hi[2] : lo[2] });
                polys.Add(new[] { v0, v0 + 1, v0 + 3, v0 + 2, v0 + 6, v0 + 7, v0 + 5, v0 + 4 }); pieceOf.Add(i);
            }
            var g = Generate(verts, polys);
            if (g == null) { log.Add($"structure MOPP: {self.Name} generation failed; source MOPP kept"); return; }
            var (info, code0) = g.Value;
            byte[] code;
            try { code = MoppRekey.Rekey(code0, k => k < nS ? 0x20050000 + k : 0x40000000 | pieceOf[k - nS]); }
            catch (Exception ex) { log.Add($"structure MOPP: {self.Name}: re-key failed ({ex.Message}); source MOPP kept"); return; }
            var kk = TagTool.Havok.HavokMoppUtil.GetAllKeys(code);
            log.Add($"structure MOPP: {self.Name}: {kk.Count(k => ((uint)k >> 29) == 1)} structure keys, {kk.Count(k => ((uint)k >> 29) == 2)} placed-piece keys ({pieceOf.Count} pieces with collision and a physics entry)");
            bsp.Physics.CollisionMoppCodes = new List<TagHkpMoppCode> { new TagHkpMoppCode
            {
                ReferencedObject = new HkpReferencedObject { ReferenceCount = 128 },
                Info = new CodeInfo { Offset = new RealQuaternion(info[0], info[1], info[2], info[3]) },
                ArrayBase = new HkArrayBase { Size = (uint)code.Length, CapacityAndFlags = (uint)code.Length | 0x80000000u },
                Data = new TagBlock<byte>(CacheAddressType.Data, code.ToList())
            } };
            bsp.Physics.MoppBoundsMin = new RealPoint3d(verts.Min(v => v[0]), verts.Min(v => v[1]), verts.Min(v => v[2]));
            bsp.Physics.MoppBoundsMax = new RealPoint3d(verts.Max(v => v[0]), verts.Max(v => v[1]), verts.Max(v => v[2]));
            log.Add($"structure MOPP: {self.Name}: rebuilt over {nS} surfaces ({invalid} invalid kept as zero-area) and {pieceOf.Count} placed pieces, {code.Length} bytes, keys 0x20050000 + surface, 0x40000000 | instance");
        }

        // TagTool's MOPP tool, "generate-collision-mopp": vertices then surfaces as vertex loops; writes a Halo Online
        // hkpMoppCode (0x30-byte header: code info at 0x10, array size at 0x24, then the code bytes)
        static (float[] info, byte[] code)? Generate(List<float[]> vertices, List<int[]> surfaces)
        {
            var dir = Path.Combine(AppContext.BaseDirectory, "Temp"); Directory.CreateDirectory(dir);
            string id = Guid.NewGuid().ToString("N").Substring(0, 12), inp = Path.Combine(dir, "cmopp_" + id + ".input"), outp = Path.Combine(dir, "cmopp_" + id + ".output");
            try
            {
                var sb = new StringBuilder();
                sb.Append(";### vertices ###\n").Append(vertices.Count).Append('\n');
                foreach (var v in vertices) sb.Append(string.Format(CultureInfo.InvariantCulture, "{0:0.0000000000}\t{1:0.0000000000}\t{2:0.0000000000}\n", v[0], v[1], v[2]));
                sb.Append('\n').Append(";### surfaces ###\n").Append(surfaces.Count).Append('\n');
                foreach (var s in surfaces) sb.Append(s.Length).Append('\n').Append(string.Join("\t", s)).Append('\n');
                File.WriteAllText(inp, sb.ToString());
                var p = Process.Start(new ProcessStartInfo { FileName = MoppExe, Arguments = $"generate-collision-mopp \"{inp}\" \"{outp}\"", UseShellExecute = false, CreateNoWindow = true, RedirectStandardOutput = true, RedirectStandardError = true, WindowStyle = ProcessWindowStyle.Hidden });
                p.StandardOutput.ReadToEnd(); p.StandardError.ReadToEnd(); p.WaitForExit();
                if (p.ExitCode != 0 || !File.Exists(outp)) return null;
                var bytes = File.ReadAllBytes(outp); if (bytes.Length < 0x30) return null;
                var info = new float[4]; for (int k = 0; k < 4; k++) info[k] = BitConverter.ToSingle(bytes, 0x10 + k * 4);
                int size = BitConverter.ToInt32(bytes, 0x24); if (size <= 0 || 0x30 + size > bytes.Length) return null;
                var code = new byte[size]; Buffer.BlockCopy(bytes, 0x30, code, 0, size);
                return (info, code);
            }
            finally { try { File.Delete(inp); } catch { } try { File.Delete(outp); } catch { } }
        }
    }
}
