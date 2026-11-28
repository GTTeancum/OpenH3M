// Checks of structure render data against Halo 3's visibility code (VISIBILITY-360.md).
// mcvcheck <map> <sbsp>: every cluster's mesh against the per-mesh visibility rules of visibility_collection_structure
// (sapien 0x7765D0 / 0x776380 / 0x6B6050 / 0x6B5F10 / 0x6B5F60): the mesh needs a MeshClusterVisibility entry, its reorder
// table must hold more than 2 * subparts values or the whole cluster mesh is skipped; layout [0, 2S) subpart ranges,
// [2S, 2S+P) sorted position -> real part, [2S+P, 2S+2P) MOPP key -> sorted position; MOPP keys are below P.
using System;
using System.Collections.Generic;
using System.Linq;
using TagTool.Tags.Definitions;

namespace Ho2H3
{
    static class VisRules
    {
        // pvscheck <map> <scenario>: the portal walk (sapien 0x77DE40) only enters the cluster across a portal if that cluster
        // is set in the current cluster's PVS row; a portal neighbour missing from the PVS blocks the area from that side.
        // Checks every zone set's PVS (normal and doors closed) against every portal of every structure BSP.
        public static int PvsCheck(string[] a)
        {
            var c = Program.OpenPak(a[1]);
            using var s = Program.OpenStream(c);
            var sc = c.Deserialize<Scenario>(s, c.TagCache.GetTag(a[2], "scnr"));
            var bsps = sc.StructureBsps.Select(b => b.StructureBsp == null ? null : c.Deserialize<ScenarioStructureBsp>(s, b.StructureBsp)).ToList();
            bool Bit(Scenario.ZoneSetPvsBlock.BspPvsBlock.ClusterPvsBlock row, int pvsBsp, int cluster)
            {
                if (row?.ClusterPvsBitVectors == null || pvsBsp >= row.ClusterPvsBitVectors.Count) return false;
                var bits = row.ClusterPvsBitVectors[pvsBsp].Bits; int w = cluster >> 5;
                return bits != null && w < bits.Count && (((uint)bits[w].Bits >> (cluster & 31)) & 1) != 0;
            }
            for (int z = 0; z < (sc.ZoneSetPvs?.Count ?? 0); z++)
            {
                var zp = sc.ZoneSetPvs[z]; uint mask = (uint)zp.StructureBspMask; var order = Enumerable.Range(0, 32).Where(b => ((mask >> b) & 1) != 0).ToList();
                for (int pi = 0; pi < order.Count && pi < (zp.StructureBspPvs?.Count ?? 0); pi++)
                {
                    int b = order[pi]; var sb = b < bsps.Count ? bsps[b] : null; if (sb == null) continue; var bp = zp.StructureBspPvs[pi];
                    int n = sb.Clusters.Count, rows = bp.ClusterPvs?.Count ?? 0, rowsDc = bp.ClusterPvsDoorsClosed?.Count ?? 0;
                    int portals = 0, missing = 0, missingDc = 0, self = 0; long setBits = 0; var ex = new List<string>();
                    for (int ci = 0; ci < Math.Min(n, rows); ci++) { if (!Bit(bp.ClusterPvs[ci], pi, ci)) self++; for (int cj = 0; cj < n; cj++) if (Bit(bp.ClusterPvs[ci], pi, cj)) setBits++; }
                    foreach (var p in sb.ClusterPortals ?? new())
                    {
                        if (p.BackCluster < 0 || p.FrontCluster < 0 || p.BackCluster >= n || p.FrontCluster >= n) continue; portals++;
                        foreach (var (x, y) in new[] { (p.BackCluster, p.FrontCluster), (p.FrontCluster, p.BackCluster) })
                        {
                            if (x >= rows || !Bit(bp.ClusterPvs[x], pi, y)) { missing++; if (ex.Count < 6) ex.Add($"cluster {x} -> {y}"); }
                            if (x >= rowsDc || !Bit(bp.ClusterPvsDoorsClosed[x], pi, y)) missingDc++;
                        }
                    }
                    // across BSPs: how many of this BSP's clusters have any bit set for each other active BSP's clusters
                    var cross = new List<string>();
                    for (int pj = 0; pj < order.Count; pj++)
                    {
                        if (pj == pi) continue; int bj = order[pj]; var sbj = bj < bsps.Count ? bsps[bj] : null; if (sbj == null) continue;
                        int seeing = 0; for (int ci = 0; ci < rows; ci++) { bool any = false; for (int cj = 0; cj < sbj.Clusters.Count && !any; cj++) any = Bit(bp.ClusterPvs[ci], pj, cj); if (any) seeing++; }
                        cross.Add($"bsp {bj}: {seeing} of {rows} clusters see some of its {sbj.Clusters.Count} clusters");
                    }
                    if (cross.Count > 0) Console.WriteLine($"zone set PVS {z} bsp {b} across BSPs: " + string.Join("; ", cross));
                    Console.WriteLine($"zone set PVS {z} bsp {b} skies: attached [{string.Join(",", (bp.AttachedSkyIndices ?? new()).Select(x => x.SkyIndex))}] visible [{string.Join(",", (bp.VisibleSkyIndices ?? new()).Select(x => x.SkyIndex))}]; scenario skies {sc.SkyReferences?.Count}; clusters flagged sky {sb.Clusters.Count(cl => (cl.Flags & ScenarioStructureBsp.Cluster.ClusterFlags.IsTheSky) != 0)}; cluster sky index [{string.Join(",", sb.Clusters.Select(cl => cl.ScenarioSkyIndex))}]");
                    Console.WriteLine($"zone set PVS {z} bsp {b}: {n} clusters, rows {rows} (doors closed {rowsDc}), bit vectors per row {bp.ClusterPvs?.FirstOrDefault()?.ClusterPvsBitVectors?.Count}; {portals} portals; portal neighbours missing from the PVS {missing} (doors closed {missingDc}); clusters not seeing themselves {self}; visible pairs {setBits} of {(long)n * n}" + (ex.Count > 0 ? "; e.g. " + string.Join(", ", ex) : ""));
                }
            }
            return 0;
        }

        // fadecheck <map> <scenario>: placed-piece fade by projected size (sapien 0x775B6A): a piece's FadePixelsStart/End
        // (+0x6C/+0x6E) when start > 0 and start >= end, otherwise the scenario structure BSP's InstanceFadeStart/EndPixels
        // when start > 0 and start > end; pieces smaller on screen than that fade out.
        public static int FadeCheck(string[] a)
        {
            var c = Program.OpenPak(a[1]);
            using var s = Program.OpenStream(c);
            var sc = c.Deserialize<Scenario>(s, c.TagCache.GetTag(a[2], "scnr"));
            for (int b = 0; b < sc.StructureBsps.Count; b++)
            {
                var r = sc.StructureBsps[b]; if (r.StructureBsp == null) continue;
                var sb = c.Deserialize<ScenarioStructureBsp>(s, r.StructureBsp);
                var tally = sb.InstancedGeometryInstances.GroupBy(i => $"{i.FadePixelsStart}/{i.FadePixelsEnd}").OrderByDescending(g => g.Count()).Take(8).Select(g => $"{g.Key} x{g.Count()}");
                int own = sb.InstancedGeometryInstances.Count(i => i.FadePixelsStart > 0 && i.FadePixelsStart >= i.FadePixelsEnd);
                Console.WriteLine($"bsp {b} {r.StructureBsp.Name}: scenario default fade start/end {r.InstanceFadeStartPixels}/{r.InstanceFadeEndPixels}; instances {sb.InstancedGeometryInstances.Count}, with their own fade {own}; values {string.Join(", ", tally)}");
            }
            return 0;
        }

        // spherecheck <map> <sbsp>: the placed-piece view test (sapien 0x775B6A -> 0x6805E0) uses the world sphere stored on
        // the instance (+0x40 centre, +0x4C radius); a sphere that does not hold the piece's render box drops the piece
        // while part of it is still on screen. Measures how far each piece's render box corners reach outside its sphere.
        public static int SphereCheck(string[] a)
        {
            var c = Program.OpenPak(a[1]);
            using var s = Program.OpenStream(c);
            var sb = c.Deserialize<ScenarioStructureBsp>(s, c.TagCache.GetTag(a[2], "sbsp"));
            var res = c.ResourceCache.GetStructureBspTagResources(sb.CollisionBspResource);
            var comp = sb.Geometry.Compression; int n = 0, outside = 0; double worst = 0; var ex = new List<string>();
            for (int i = 0; i < sb.InstancedGeometryInstances.Count; i++)
            {
                var x = sb.InstancedGeometryInstances[i]; int d = x.DefinitionIndex; if (d < 0 || d >= res.InstancedGeometry.Count) continue;
                var g = res.InstancedGeometry[d]; int ci = g.CompressionIndex;
                if (comp == null || ci < 0 || ci >= comp.Count || g.MeshIndex < 0 || g.MeshIndex >= sb.Geometry.Meshes.Count || sb.Geometry.Meshes[g.MeshIndex].Parts.Count == 0) continue;
                var cb = comp[ci]; var m = x.Matrix; float sc = x.Scale == 0 ? 1 : x.Scale; n++;
                double cx = x.WorldBoundingSphereCenter.X, cy = x.WorldBoundingSphereCenter.Y, cz = x.WorldBoundingSphereCenter.Z, r = x.BoundingSphereRadiusBounds.Lower, far = 0;
                for (int k = 0; k < 8; k++)
                {
                    double px = (k & 1) != 0 ? cb.X.Upper : cb.X.Lower, py = (k & 2) != 0 ? cb.Y.Upper : cb.Y.Lower, pz = (k & 4) != 0 ? cb.Z.Upper : cb.Z.Lower;
                    double wx = sc * (px * m.m11 + py * m.m21 + pz * m.m31) + m.m41, wy = sc * (px * m.m12 + py * m.m22 + pz * m.m32) + m.m42, wz = sc * (px * m.m13 + py * m.m23 + pz * m.m33) + m.m43;
                    far = Math.Max(far, Math.Sqrt((wx - cx) * (wx - cx) + (wy - cy) * (wy - cy) + (wz - cz) * (wz - cz)));
                }
                // the compression box is a box, its corners lie beyond the mesh; count only reaches beyond 10% of the box half-diagonal
                double half = 0.5 * sc * Math.Sqrt(Math.Pow(cb.X.Upper - cb.X.Lower, 2) + Math.Pow(cb.Y.Upper - cb.Y.Lower, 2) + Math.Pow(cb.Z.Upper - cb.Z.Lower, 2));
                double over = far - r;
                if (over > 0.1 * half + 0.01) { outside++; if (over > worst) worst = over; if (ex.Count < 8) ex.Add($"{c.StringTable.GetString(x.Name)} (instance {i}): radius {r:F2}, box corner at {far:F2}"); }
            }
            Console.WriteLine($"{n} drawn pieces; render box reaching outside the stored sphere by more than 10% of its half-diagonal: {outside}, worst {worst:F2}");
            foreach (var e in ex) Console.WriteLine("  " + e);
            return 0;
        }

        // bucketcheck <map> <sbsp>: placed pieces are drawn only through the instance buckets of visible clusters' meshes
        // (sapien 0x775B6A). For each piece: clusters whose bounds its world sphere overlaps, and how many of those list it.
        public static int BucketCheck(string[] a)
        {
            var c = Program.OpenPak(a[1]);
            using var s = Program.OpenStream(c);
            var sb = c.Deserialize<ScenarioStructureBsp>(s, c.TagCache.GetTag(a[2], "sbsp"));
            var listed = new Dictionary<int, HashSet<int>>();
            for (int ci = 0; ci < sb.Clusters.Count; ci++)
            {
                int mi = sb.Clusters[ci].MeshIndex; if (mi < 0 || mi >= sb.Geometry.Meshes.Count) continue;
                foreach (var bk in sb.Geometry.Meshes[mi].InstanceBuckets ?? new()) foreach (var ii in bk.Instances) { if (!listed.TryGetValue(ii.InstanceIndex, out var h)) listed[ii.InstanceIndex] = h = new HashSet<int>(); h.Add(ci); }
            }
            int pieces = 0, none = 0, noneDrawable = 0; long pairs = 0, missing = 0, extra = 0; var ex = new List<string>(); var exNone = new List<string>();
            for (int i = 0; i < sb.InstancedGeometryInstances.Count; i++)
            {
                var x = sb.InstancedGeometryInstances[i]; var cc = x.WorldBoundingSphereCenter; double r = x.BoundingSphereRadiusBounds.Lower;
                var ov = new List<int>();
                for (int ci = 0; ci < sb.Clusters.Count; ci++)
                {
                    var cl = sb.Clusters[ci];
                    double dx = Math.Max(0, Math.Max(cl.BoundsX.Lower - cc.X, cc.X - cl.BoundsX.Upper)), dy = Math.Max(0, Math.Max(cl.BoundsY.Lower - cc.Y, cc.Y - cl.BoundsY.Upper)), dz = Math.Max(0, Math.Max(cl.BoundsZ.Lower - cc.Z, cc.Z - cl.BoundsZ.Upper));
                    if (dx * dx + dy * dy + dz * dz <= r * r) ov.Add(ci);
                }
                listed.TryGetValue(i, out var l); l ??= new HashSet<int>();
                if (l.Count == 0)
                {
                    none++;
                    var rr = c.ResourceCache.GetStructureBspTagResources(sb.CollisionBspResource); int dd = x.DefinitionIndex;
                    bool drawable = dd >= 0 && dd < rr.InstancedGeometry.Count && rr.InstancedGeometry[dd].MeshIndex >= 0 && rr.InstancedGeometry[dd].MeshIndex < sb.Geometry.Meshes.Count && sb.Geometry.Meshes[rr.InstancedGeometry[dd].MeshIndex].Parts.Count > 0;
                    if (drawable) { noneDrawable++; if (exNone.Count < 6) exNone.Add($"{c.StringTable.GetString(x.Name)} (instance {i}, flags {x.Flags})"); }
                    continue;
                }
                pieces++; pairs += ov.Count; missing += ov.Count(o => !l.Contains(o)); extra += l.Count(o => !ov.Contains(o));
                if (ov.Any(o => !l.Contains(o)) && ex.Count < 5) ex.Add($"{c.StringTable.GetString(x.Name)} (instance {i}): overlaps clusters [{string.Join(",", ov)}], listed in [{string.Join(",", l)}]");
            }
            int twins = 0;
            for (int i = 0; i < sb.InstancedGeometryInstances.Count; i++)
            {
                if (listed.ContainsKey(i)) continue; var x = sb.InstancedGeometryInstances[i];
                for (int j = 0; j < sb.InstancedGeometryInstances.Count; j++)
                {
                    if (!listed.ContainsKey(j)) continue; var y = sb.InstancedGeometryInstances[j];
                    if (y.DefinitionIndex == x.DefinitionIndex && Math.Abs(y.Matrix.m41 - x.Matrix.m41) + Math.Abs(y.Matrix.m42 - x.Matrix.m42) + Math.Abs(y.Matrix.m43 - x.Matrix.m43) < 0.01) { twins++; break; }
                }
            }
            Console.WriteLine($"pieces in no bucket with a listed twin (same definition and position): {twins}");
            Console.WriteLine($"pieces in no bucket: {none}, of them with render geometry (never drawn): {noneDrawable}" + (exNone.Count > 0 ? "; e.g. " + string.Join(", ", exNone) : ""));
            Console.WriteLine($"{pieces} listed pieces ({none} in no bucket): overlapped clusters {pairs}, of which not listing the piece {missing} ({(pairs == 0 ? 0 : 100.0 * missing / pairs):F1}%); listed in clusters they do not overlap {extra}");
            foreach (var e in ex) Console.WriteLine("  " + e);
            return 0;
        }

        // seamcheck <map> <scenario>: the portal walk crosses into another structure BSP only through structure seams
        // (sapien 0x77DE40 -> 0x618670, structure_seams.cpp). Reports each BSP's seam identifiers, the scenario's structure
        // seams tags, and the PVS attached-cluster lists.
        public static int SeamCheck(string[] a)
        {
            var c = Program.OpenPak(a[1]);
            using var s = Program.OpenStream(c);
            var sc = c.Deserialize<Scenario>(s, c.TagCache.GetTag(a[2], "scnr"));
            Console.WriteLine($"scenario structure seams: {sc.StructureSeams?.Name ?? "none"}; local structure seams: {sc.LocalStructureSeams?.Name ?? "none"}");
            for (int b = 0; b < sc.StructureBsps.Count; b++)
            {
                var r = sc.StructureBsps[b]; if (r.StructureBsp == null) continue;
                var sb = c.Deserialize<ScenarioStructureBsp>(s, r.StructureBsp);
                Console.WriteLine($"bsp {b} bounds x {sb.WorldBoundsX.Lower:F0}..{sb.WorldBoundsX.Upper:F0} y {sb.WorldBoundsY.Lower:F0}..{sb.WorldBoundsY.Upper:F0} z {sb.WorldBoundsZ.Lower:F0}..{sb.WorldBoundsZ.Upper:F0}; instances {sb.InstancedGeometryInstances.Count}, cluster mesh parts {sb.Clusters.Sum(cl => cl.MeshIndex >= 0 && cl.MeshIndex < sb.Geometry.Meshes.Count ? sb.Geometry.Meshes[cl.MeshIndex].Parts.Count : 0)}");
                for (int k = 0; k < (sb.SeamIdentifiers?.Count ?? 0); k++)
                {
                    var si = sb.SeamIdentifiers[k];
                    Console.WriteLine($"   seam {k}: ids {string.Join(" ", si.SeamIDs.Select(x => x.ToString("X8")))}; edges {si.EdgeMapping?.Count ?? 0}; clusters [{string.Join(",", (si.ClusterMapping ?? new()).Select(cm => cm.ClusterIndex + "@" + cm.ClusterCenter.X.ToString("F2") + "," + cm.ClusterCenter.Y.ToString("F2") + "," + cm.ClusterCenter.Z.ToString("F2")))}]");
                }
                Console.WriteLine($"   clusters with seam indices: {sb.Clusters.Count(cl => cl.SeamIndices?.Count > 0)}: {string.Join(" ", sb.Clusters.Select((cl, ci) => (cl, ci)).Where(t => t.cl.SeamIndices?.Count > 0).Select(t => t.ci + ":[" + string.Join(",", t.cl.SeamIndices.Select(q => q.SeamIndex)) + "]"))}; seam collision materials {sb.CollisionMaterials.Count(m => (m.Flags & ScenarioStructureBsp.CollisionMaterial.FlagsValue.IsSeam) != 0)}");
                Console.WriteLine($"bsp {b} {r.StructureBsp.Name}: seam identifiers {sb.SeamIdentifiers?.Count ?? 0}, edge-to-seam-edge {sb.EdgeToSeamEdge?.Count ?? 0}, clusters {sb.Clusters.Count}");
            }
            foreach (var zp in sc.ZoneSetPvs ?? new())
                for (int pi = 0; pi < (zp.StructureBspPvs?.Count ?? 0); pi++)
                {
                    var m = zp.StructureBspPvs[pi].ClusterMappings;
                    Console.WriteLine($"PVS entry {pi}: attached-cluster lists {m?.Count ?? 0}, entries {m?.Sum(x => x.Clusters?.Count ?? 0) ?? 0}");
                }
            return 0;
        }

        // locate <map> <scenario>: Halo 3's location from a point (sapien 0x3DDFE0): the active structure BSPs in index
        // order, the first whose structure collision BSP has the point in a non-solid leaf wins; cluster = that BSP's leaf
        // table. Without seams the portal walk never leaves that BSP, so only it is drawn. Run on every player start.
        public static int Locate(string[] a)
        {
            var c = Program.OpenPak(a[1]);
            using var s = Program.OpenStream(c);
            var sc = c.Deserialize<Scenario>(s, c.TagCache.GetTag(a[2], "scnr"));
            uint mask = sc.ZoneSetPvs != null && sc.ZoneSetPvs.Count > 0 ? (uint)sc.ZoneSetPvs[0].StructureBspMask : 0xFFFFFFFF;
            var active = new List<(int b, ScenarioStructureBsp sb, TagTool.Geometry.BspCollisionGeometry.CollisionGeometry g)>();
            for (int b = 0; b < sc.StructureBsps.Count; b++)
            {
                if (((mask >> b) & 1) == 0 || sc.StructureBsps[b].StructureBsp == null) continue;
                var sb = c.Deserialize<ScenarioStructureBsp>(s, sc.StructureBsps[b].StructureBsp);
                var r = c.ResourceCache.GetStructureBspTagResources(sb.CollisionBspResource);
                var g = r.CollisionBsps?.FirstOrDefault();
                if (g == null && r.LargeCollisionBsps?.Count > 0) g = Halo3Limits.Shrink(new TagTool.Geometry.BspCollisionGeometry.Utils.ResizeCollisionBSP(), r.LargeCollisionBsps[0]);
                active.Add((b, sb, g));
            }
            int Leaf(TagTool.Geometry.BspCollisionGeometry.CollisionGeometry g, double x, double y, double z)
            {
                if (g == null || g.Bsp3dNodes.Count == 0) return -1; int node = 0, guard = 0;
                while ((node & 0x800000) == 0 && ++guard < 100000)
                {
                    var n = g.Bsp3dNodes[node]; var p = g.Planes[n.Plane & 0x7FFF].Value;
                    node = p.I * x + p.J * y + p.K * z - p.D >= 0 ? n.FrontChild : n.BackChild;
                }
                return node == 0xFFFFFF ? -1 : node & 0x7FFFFF;
            }
            var tally = new Dictionary<string, int>(); int nPts = 0;
            foreach (var st in sc.PlayerStartingLocations ?? new())
            {
                var p = st.Position; nPts++; string who = "nowhere";
                foreach (var (b, sb, g) in active) { int lf = Leaf(g, p.X, p.Y, p.Z + 0.6); if (lf >= 0) { who = $"bsp {b} {sb.Clusters.Count} clusters"; break; } }
                tally[who] = tally.TryGetValue(who, out int q) ? q + 1 : 1;
            }
            Console.WriteLine($"active BSPs {string.Join(",", active.Select(x => x.b))}; {nPts} player starts located in: {string.Join("; ", tally.Select(kv => kv.Key + " x" + kv.Value))}");
            // floors: points 1 unit above upward structure surfaces of each active BSP (and above its placed pieces' tops)
            foreach (var (b0, sb0, g0) in active)
            {
                if (g0 == null) continue; var t2 = new Dictionary<string, int>(); int n2 = 0;
                for (int si = 0; si < g0.Surfaces.Count && n2 < 2000; si += Math.Max(1, g0.Surfaces.Count / 2000))
                {
                    var sf = g0.Surfaces[si]; var pl = g0.Planes[sf.Plane & 0x7FFF].Value; double sg = (sf.Plane & 0x8000) != 0 ? -1 : 1;
                    if (pl.K * sg < 0.8) continue;
                    var vs = new List<double[]>(); int e = sf.FirstEdge, guard = 0;
                    do { var ed = g0.Edges[e]; int side = ed.RightSurface == si ? 1 : 0; var v = g0.Vertices[side == 1 ? ed.EndVertex : ed.StartVertex].Point; vs.Add(new double[] { v.X, v.Y, v.Z }); e = side == 1 ? ed.ReverseEdge : ed.ForwardEdge; } while (e != sf.FirstEdge && ++guard < 1000);
                    if (vs.Count < 3) continue;
                    double x = vs.Average(v => v[0]), y = vs.Average(v => v[1]), z = vs.Average(v => v[2]) + 1.0;
                    if (Leaf(g0, x, y, z) < 0) continue;   // not open space in its own BSP
                    n2++; string who = "nowhere";
                    foreach (var (b, sb, g) in active) { if (Leaf(g, x, y, z) >= 0) { who = b == b0 ? "its own BSP" : $"bsp {b} (its own geometry not drawn)"; break; } }
                    t2[who] = t2.TryGetValue(who, out int q) ? q + 1 : 1;
                }
                Console.WriteLine($"  floor points of bsp {b0} ({sb0.Clusters.Count} clusters): {n2} sampled; located in {string.Join("; ", t2.Select(kv => kv.Key + " x" + kv.Value))}");
            }
            return 0;
        }

        public static int McvCheck(string[] a)
        {
            var c = Program.OpenPak(a[1]);
            using var s = Program.OpenStream(c);
            var sb = c.Deserialize<ScenarioStructureBsp>(s, c.TagCache.GetTag(a[2], "sbsp"));
            var geo = sb.Geometry; var mcv = geo.MeshClusterVisibility;
            int clusters = sb.Clusters.Count, noEntry = 0, skipped = 0, shortLayout = 0, badKeys = 0, badMap = 0, ok = 0, emptyMesh = 0;
            var notes = new List<string>();
            for (int ci = 0; ci < clusters; ci++)
            {
                int mi = sb.Clusters[ci].MeshIndex;
                if (mi < 0 || mi >= geo.Meshes.Count) { emptyMesh++; notes.Add($"cluster {ci}: mesh index {mi} out of range"); continue; }
                var mesh = geo.Meshes[mi]; int P = mesh.Parts?.Count ?? 0, S = mesh.SubParts?.Count ?? 0;
                if (P == 0) { emptyMesh++; continue; }
                if (mcv == null || mi >= mcv.Count) { noEntry++; notes.Add($"cluster {ci}: mesh {mi} has no visibility entry (entries {mcv?.Count ?? 0})"); continue; }
                var e = mcv[mi]; var r = e.MoppReorderTable?.Select(x => (int)x).ToList() ?? new List<int>(); int R = r.Count;
                if (R <= 2 * S) { skipped++; notes.Add($"cluster {ci}: mesh {mi} reorder table {R} <= 2 x subparts {S}: whole mesh skipped"); continue; }
                if (R < 2 * S + 2 * P) { shortLayout++; notes.Add($"cluster {ci}: mesh {mi} reorder table {R} < 2S+2P = {2 * S + 2 * P} (P {P}, S {S})"); }
                var b = e.MoppCode; var keys = new List<int>(); if (b != null && b.Length >= 0x30) { int size = b[0x24] << 24 | b[0x25] << 16 | b[0x26] << 8 | b[0x27]; if (size > 0 && 0x30 + size <= b.Length) keys = TagTool.Havok.HavokMoppUtil.GetAllKeys(b.Skip(0x30).Take(size).ToList()).ToList(); }
                if (a.Length > 3 && ci < int.Parse(a[3])) Console.WriteLine($"  raw cluster {ci} mesh {mi}: P {P} S {S} R {R} keys {keys.Count} min {(keys.Count > 0 ? keys.Min() : -1)} max {(keys.Count > 0 ? keys.Max() : -1)} distinct {keys.Distinct().Count()} | table head {string.Join(",", r.Take(Math.Min(R, 2 * S + 6)).Skip(Math.Max(0, 2 * S - 4)))}");
                if (keys.Count == 0 || keys.Any(k => k < 0 || k >= S)) { badKeys++; notes.Add($"cluster {ci}: mesh {mi} MOPP keys {keys.Count}, outside subparts: {keys.Count(k => k < 0 || k >= S)} (S {S}, max {(keys.Count > 0 ? keys.Max() : -1)})"); }
                bool mapBad = false;
                for (int k = 0; k < Math.Min(R, 2 * S + 2 * P); k++) if (r[k] < 0 || r[k] >= (k < 2 * S ? S : P)) { mapBad = true; break; }
                if (mapBad) { badMap++; notes.Add($"cluster {ci}: mesh {mi} reorder values outside parts"); }
                if (R >= 2 * S + 2 * P && !mapBad && keys.Count > 0 && keys.All(k => k >= 0 && k < S)) ok++;
            }
            Console.WriteLine($"{clusters} clusters: {ok} meshes pass every rule; no visibility entry {noEntry}; whole mesh skipped (reorder <= 2S) {skipped}; reorder shorter than 2S+2P {shortLayout}; MOPP keys outside subparts {badKeys}; reorder values out of range {badMap}; empty/no mesh {emptyMesh}; visibility entries {mcv?.Count ?? 0}, meshes {geo.Meshes.Count}");
            foreach (var n in notes.Take(30)) Console.WriteLine("  " + n);
            return 0;
        }
    }
}
