// Bounding spheres of instanced-geometry definitions and instances. Stock Halo 3 gives every definition a sphere around
// its own geometry (Guardian, all 193 collidable definitions: centre = middle of the render mesh's compression box,
// radius = half that box's diagonal) and every instance that sphere in world space. Halo Online's Reach ports leave the
// definition's sphere at radius 0 (Sword Base: all 439 collidable definitions), and pieces that gain collision here
// (ramps) outgrow theirs. The definition's sphere becomes the box around its render mesh and its collision geometry;
// the instance's world centre and minimum radius follow from its transform. Runs after all collision changes. Map-agnostic.
using System;
using System.Collections.Generic;
using System.Linq;
using TagTool.Common;
using TagTool.Tags.Definitions;
using TagTool.Tags.Resources;

namespace Ho2H3
{
    public static class InstanceSpheres
    {
        public static void Fix(ScenarioStructureBsp bsp, StructureBspTagResources res, string where, List<string> log)
        {
            if (res?.InstancedGeometry == null) return;
            var comp = bsp.Geometry?.Compression; int fixedDefs = 0, grown = 0, inst = 0;
            var center = new RealPoint3d[res.InstancedGeometry.Count]; var radius = new float[res.InstancedGeometry.Count];
            for (int d = 0; d < res.InstancedGeometry.Count; d++)
            {
                var g = res.InstancedGeometry[d];
                float lx = float.MaxValue, ly = float.MaxValue, lz = float.MaxValue, hx = float.MinValue, hy = float.MinValue, hz = float.MinValue; bool any = false;
                if (comp != null && g.CompressionIndex >= 0 && g.CompressionIndex < comp.Count && g.MeshIndex >= 0 && g.MeshIndex < bsp.Geometry.Meshes.Count && bsp.Geometry.Meshes[g.MeshIndex].Parts.Count > 0)
                {
                    var c = comp[g.CompressionIndex]; lx = c.X.Lower; hx = c.X.Upper; ly = c.Y.Lower; hy = c.Y.Upper; lz = c.Z.Lower; hz = c.Z.Upper; any = true;
                }
                if (g.CollisionInfo?.Vertices != null)
                    foreach (var v in g.CollisionInfo.Vertices) { var p = v.Point; lx = Math.Min(lx, p.X); hx = Math.Max(hx, p.X); ly = Math.Min(ly, p.Y); hy = Math.Max(hy, p.Y); lz = Math.Min(lz, p.Z); hz = Math.Max(hz, p.Z); any = true; }
                if (!any) { center[d] = g.BoundingSphereOffset; radius[d] = g.BoundingSphereRadius; continue; }
                var cc = new RealPoint3d((lx + hx) / 2, (ly + hy) / 2, (lz + hz) / 2);
                float r = (float)(Math.Sqrt((hx - lx) * (hx - lx) + (hy - ly) * (hy - ly) + (hz - lz) * (hz - lz)) / 2);
                // keep a valid stock-style sphere that already holds the box
                var o = g.BoundingSphereOffset; double off = Math.Sqrt((o.X - cc.X) * (o.X - cc.X) + (o.Y - cc.Y) * (o.Y - cc.Y) + (o.Z - cc.Z) * (o.Z - cc.Z));
                if (g.BoundingSphereRadius > 0 && off + r <= g.BoundingSphereRadius + 1e-3) { center[d] = o; radius[d] = g.BoundingSphereRadius; continue; }
                if (g.BoundingSphereRadius <= 0) fixedDefs++; else grown++;
                g.BoundingSphereOffset = cc; g.BoundingSphereRadius = r; center[d] = cc; radius[d] = r;
            }
            foreach (var x in bsp.InstancedGeometryInstances)
            {
                int d = x.DefinitionIndex; if (d < 0 || d >= center.Length || radius[d] <= 0) continue;
                float s = x.Scale == 0 ? 1 : x.Scale; var m = x.Matrix; var c = center[d];
                var w = new RealPoint3d(s * (c.X * m.m11 + c.Y * m.m21 + c.Z * m.m31) + m.m41, s * (c.X * m.m12 + c.Y * m.m22 + c.Z * m.m32) + m.m42, s * (c.X * m.m13 + c.Y * m.m23 + c.Z * m.m33) + m.m43);
                float wr = radius[d] * Math.Abs(s);
                var b = x.BoundingSphereRadiusBounds;
                bool change = Math.Abs(w.X - x.WorldBoundingSphereCenter.X) > 1e-3 || Math.Abs(w.Y - x.WorldBoundingSphereCenter.Y) > 1e-3 || Math.Abs(w.Z - x.WorldBoundingSphereCenter.Z) > 1e-3 || b.Lower < wr - 1e-3;
                if (!change) continue;
                x.WorldBoundingSphereCenter = w; x.BoundingSphereRadiusBounds = new Bounds<float>(wr, b.Upper); inst++;   // Upper is the instance "checksum" field in the real layout (offset 0x50): kept
            }
            log.Add($"instance spheres: {where}: {fixedDefs} definitions had no bounding sphere (radius 0) and got one, {grown} grown to hold their collision; {inst} instances' world spheres updated");
        }
    }
}
