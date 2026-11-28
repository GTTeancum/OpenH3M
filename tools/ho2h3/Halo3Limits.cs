// Halo 3's own collision BSP limits, from the field widths of its small collision BSP (and confirmed by stock maps:
// Sidewinder 92248 3D nodes / 46686 leaves, Snowbound 82567 / 44216): 3D node children are 24 bits with the leaf flag in
// bit 23; node, surface and 2D reference planes are 16 bits with the negation flag in bit 15; 2D node children are 16 bits
// with the leaf flag in bit 15; edges and vertices are referenced by unsigned 16 bits (0xFFFF = none). TagTool's
// collision_bsp_check_counts caps 3D nodes and leaves at 32767, which made the converter rebuild Breakneck's tree (51314
// nodes) and lose the source's leaf -> cluster table (hall of mirrors, user play test 2026-11-23).
using TagTool.Geometry.BspCollisionGeometry;
using TagTool.Geometry.BspCollisionGeometry.Utils;

namespace Ho2H3
{
    public static class Halo3Limits
    {
        public static bool Fits(LargeCollisionBspBlock b, out string over)
        {
            string o = null;
            void Chk(string what, int n, int max) { if (n > max && o == null) o = $"{what} {n} > {max}"; }
            Chk("3D nodes", b.Bsp3dNodes?.Count ?? 0, 0x7FFFFF);
            Chk("leaves", b.Leaves?.Count ?? 0, 0x7FFFFF);
            Chk("planes", b.Planes?.Count ?? 0, 0x7FFF);
            Chk("2D nodes", b.Bsp2dNodes?.Count ?? 0, 0x7FFF);
            Chk("surfaces", b.Surfaces?.Count ?? 0, 0x7FFF);
            Chk("edges", b.Edges?.Count ?? 0, 0xFFFE);
            Chk("vertices", b.Vertices?.Count ?? 0, 0xFFFE);
            over = o; return o == null;
        }

        // TagTool's shrink, plus the 3D node plane negation (bit 31 in the large node, bit 15 in the small one), which its
        // node conversion drops
        public static CollisionGeometry Shrink(ResizeCollisionBSP rz, LargeCollisionBspBlock lb)
        {
            var g = rz.ShrinkCollisionBsp(lb);
            for (int i = 0; i < lb.Bsp3dNodes.Count && i < g.Bsp3dNodes.Count; i++)
            {
                int p = lb.Bsp3dNodes[i].Plane;
                ulong small = (ulong)((p & 0x7FFF) | ((p & unchecked((int)0x80000000)) != 0 ? 0x8000 : 0));
                g.Bsp3dNodes[i].Value = (g.Bsp3dNodes[i].Value & ~0xFFFFUL) | small;
            }
            return g;
        }
    }
}
