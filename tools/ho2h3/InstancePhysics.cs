// Instance physics shapes. Every stock Halo 3 instance with collision has one BspPhysics entry whose collision geometry
// shape is type 2 / collision geometry shape type 2 with welding on and its own instance index as key (Guardian 454 of
// 454, Valhalla 248 of 248). Halo Online's Reach ports carry Reach's values (Sword Base: 1168 entries type 0, 184 type 7,
// welding off) and some collidable instances have no entry at all; Halo 3's physics then never collides the player with
// those instances: the player fell through every walkway on Sword Base and stair ramps did nothing on Reflection (user
// play tests 2026-11-23; in-game drop test through a solid ramp, glass rails and an invisible walking surface to the floor
// 4.5 units below). Every collidable instance (collision surfaces, not render-only) gets one entry with the stock values;
// an entry is cloned from the instance's own or another entry when it has none. Map-agnostic.
using System;
using System.Collections.Generic;
using System.Linq;
using TagTool.Geometry.BspCollisionGeometry;
using TagTool.Tags;
using TagTool.Tags.Definitions;
using TagTool.Tags.Resources;

namespace Ho2H3
{
    public static class InstancePhysics
    {
        public static void Fix(ScenarioStructureBsp bsp, StructureBspTagResources res, string where, List<string> log)
        {
            var inst = bsp.InstancedGeometryInstances; if (inst == null || res?.InstancedGeometry == null) return;
            var template = inst.SelectMany(x => x.BspPhysics ?? new List<InstancedGeometryPhysics>()).FirstOrDefault();
            if (template == null) { log.Add($"instance physics: {where}: no entry to copy; unchanged"); return; }
            // the shape's box (local, centre and half extents, w = 0): stock = box around the definition's render mesh
            // (Guardian instance 0: centre (2.537, 0.095, -1.029) = definition sphere offset, half (2.368, 1.497, 2.404));
            // here the render box together with the collision vertices, as for the definition spheres
            var comp = bsp.Geometry?.Compression;
            // Halo 3's tool (sapien 0x6A4A80, the collision geometry shape built by the structure post-process): the box is
            // the bounds of the definition's collision vertices times the instance scale; the 360 game uses it as stored
            // (geometry shape getAabb 0x822712F0) and so does the structure MOPP's placed-piece entry (COLLISION-360.md)
            (TagTool.Common.RealQuaternion c, TagTool.Common.RealQuaternion h)? Box(int d, float scale)
            {
                var g = res.InstancedGeometry[d];
                float lx = float.MaxValue, ly = float.MaxValue, lz = float.MaxValue, hx = float.MinValue, hy = float.MinValue, hz = float.MinValue; bool any = false;
                if (g.CollisionInfo?.Vertices != null) foreach (var v in g.CollisionInfo.Vertices) { var p = v.Point; lx = Math.Min(lx, p.X); hx = Math.Max(hx, p.X); ly = Math.Min(ly, p.Y); hy = Math.Max(hy, p.Y); lz = Math.Min(lz, p.Z); hz = Math.Max(hz, p.Z); any = true; }
                if (!any) return null;
                float s = scale == 0 ? 1 : scale;
                return (new TagTool.Common.RealQuaternion(s * (lx + hx) / 2, s * (ly + hy) / 2, s * (lz + hz) / 2, 0), new TagTool.Common.RealQuaternion(s * (hx - lx) / 2, s * (hy - ly) / 2, s * (hz - lz) / 2, 0));
            }
            int changed = 0, added = 0, collidable = 0, boxes = 0;
            for (int i = 0; i < inst.Count; i++)
            {
                var x = inst[i]; int d = x.DefinitionIndex;
                bool coll = d >= 0 && d < res.InstancedGeometry.Count && res.InstancedGeometry[d].CollisionInfo?.Surfaces?.Count > 0
                            && (x.Flags & InstancedGeometryInstance.InstancedGeometryFlags.RenderOnly) == 0;
                if (!coll) continue; collidable++;
                if (x.BspPhysics == null || x.BspPhysics.Count == 0)
                {
                    x.BspPhysics = new List<InstancedGeometryPhysics> { (InstancedGeometryPhysics)template.DeepClone() }; added++;
                }
                foreach (var bp in x.BspPhysics)
                {
                    var g = bp.GeometryShape;
                    if (g.CollisionGeometryShapeType != 2 || g.Type != 2 || g.DisableWelding || g.CollisionGeometryShapeKey != i) changed++;
                    g.CollisionGeometryShapeType = 2; g.Type = 2; g.DisableWelding = false; g.CollisionGeometryShapeKey = (ushort)i;
                    var bx = Box(d, x.Scale); if (bx != null) { var (bc, bh) = bx.Value; if (Math.Abs(g.AABB_Center.I - bc.I) + Math.Abs(g.AABB_Center.J - bc.J) + Math.Abs(g.AABB_Center.K - bc.K) + Math.Abs(g.AABB_Half_Extents.I - bh.I) + Math.Abs(g.AABB_Half_Extents.J - bh.J) + Math.Abs(g.AABB_Half_Extents.K - bh.K) > 1e-3) boxes++; g.AABB_Center = bc; g.AABB_Half_Extents = bh; }
                    if (bp.MoppBvTreeShape != null) bp.MoppBvTreeShape.Type = 27;
                }
            }
            log.Add($"instance physics: {where}: {collidable} collidable instances; {changed} entries set to the stock shape values, {added} entries added, {boxes} shape boxes set from the definition's geometry (were zero or different)");
        }
    }
}
