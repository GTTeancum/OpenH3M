// Xbox 360 (Xenos) texture memory layout: 2D tiling, packed mip tails and GPU byte order.
// Address arithmetic follows the publicly documented Xenos tiling scheme (as described by Xenia's
// texture_address.h and TagTool's XboxBitmapUtils); this is a new implementation for this project.
using System;
using System.Collections.Generic;

namespace Inject360
{
    public static class Xenos
    {
        // Byte address of block (x, y) in a tiled 2D surface whose row pitch is `pitch` blocks (multiple of 32).
        public static uint Address(uint x, uint y, uint pitch, uint bpb)
        {
            uint outer = ((y >> 5) * (pitch >> 5) + (x >> 5)) << 6;
            uint inner = ((y & 14) << 2) + (x & 7);
            uint v = (outer + inner) * bpb;
            uint bank = (y >> 4) & 1, pipe = ((x >> 3) & 3) ^ ((y >> 2) & 2);
            return ((v & 0xFFFFFF00u) << 4) | ((v & 224) << 3) | (bank << 11) | (pipe << 6) | ((v & 16) << 1) | ((y & 1) << 4) | (v & 15);
        }

        public static byte Fill;   // value of bytes no texel lands on (0 in ported maps; texverify varies it to tell padding from texels)
        public static uint Align(uint v, uint a) => (v + a - 1) & ~(a - 1);
        static int Log2Ceil(int v) { int n = 0; while ((1 << n) < v) n++; return n; }

        public class Level { public int W, H, Wb, Hb; public uint Offset, Pitch, Stride; public int X, Y; public bool Tail; }

        // Mip layout for `count` levels starting at a base of width x height.
        // Levels at and after the packed tail share one 4 KiB-aligned subresource.
        public static List<Level> Layout(int width, int height, int count, int blockExtent, uint bpb, out uint total)
        {
            var levels = new List<Level>();
            int logw = Log2Ceil(width), logh = Log2Ceil(height);
            int potw = 1 << logw, poth = 1 << logh;
            int tail = Math.Max(0, Math.Min(logw, logh) - 4);
            uint offset = 0, tailOffset = 0; bool haveTail = false; uint end = 0;
            for (int level = 0; level < count; level++)
            {
                int w = Math.Max(1, width >> level), h = Math.Max(1, height >> level);
                var L = new Level { W = w, H = h, Wb = (w + blockExtent - 1) / blockExtent, Hb = (h + blockExtent - 1) / blockExtent };
                uint blockH;
                if (count > 1 && level >= tail)
                {
                    if (!haveTail) { tailOffset = offset; haveTail = true; }
                    int packed = level - tail;
                    if (packed < 3) { if (logw > logh) L.Y = (16 >> packed) / blockExtent; else L.X = (16 >> packed) / blockExtent; }
                    else if (logw > logh) L.X = ((potw >> tail) >> (packed - 2)) / blockExtent;
                    else L.Y = ((poth >> tail) >> (packed - 2)) / blockExtent;
                    L.Pitch = Align((uint)Math.Max(1, ((potw >> tail) + blockExtent - 1) / blockExtent), 32);
                    blockH = Align((uint)Math.Max(1, ((poth >> tail) + blockExtent - 1) / blockExtent), 32);
                    if (level == 0) L.Pitch = Align((uint)L.Wb, 32);
                    L.Offset = tailOffset; L.Tail = true; L.Stride = Align(L.Pitch * blockH * bpb, 4096);
                    blockH = Math.Max(blockH, (uint)(L.Y + L.Hb));
                }
                else
                {
                    int sw = level == 0 ? width : potw >> level, sh = level == 0 ? height : poth >> level;
                    L.Pitch = Align((uint)((sw + blockExtent - 1) / blockExtent), 32);
                    blockH = Align((uint)((sh + blockExtent - 1) / blockExtent), 32);
                    L.Offset = offset;
                    L.Stride = Align(L.Pitch * blockH * bpb, 4096); offset += L.Stride;
                }
                // end of the last addressed byte of this level
                for (int y = 0; y < L.Hb; y++) for (int x = 0; x < L.Wb; x++)
                    end = Math.Max(end, L.Offset + Address((uint)(L.X + x), (uint)(L.Y + y), L.Pitch, bpb) + bpb);
                levels.Add(L);
            }
            total = end;          // stock 360 controls record the exact end of the last level, not a 4 KiB multiple
            return levels;
        }

        // Linear little-endian levels (concatenated) -> tiled big-endian GPU layout.
        // Destination byte offset of every block, in linear (level, row, column) order.
        // tiled = false: plain rows at a 32-block pitch (stock single-level textures whose fetch word has the
        // tiled bit clear; size = (rows - 1) x pitch + width, checked on four stock textures).
        public static List<uint> BlockOffsets(int width, int height, int count, int blockExtent, int bpb, bool tiled, out uint total)
        {
            var o = new List<uint>();
            if (!tiled)
            {
                if (count != 1) throw new Exception("untiled layout is only known for single-level textures");
                int wb = (width + blockExtent - 1) / blockExtent, hb = (height + blockExtent - 1) / blockExtent;
                uint pitch = Align((uint)wb, 32);
                for (int y = 0; y < hb; y++) for (int x = 0; x < wb; x++) o.Add((uint)((y * pitch + x) * bpb));
                total = (uint)(((hb - 1) * pitch + wb) * bpb);
                return o;
            }
            var levels = Layout(width, height, count, blockExtent, (uint)bpb, out total);
            foreach (var L in levels)
                for (int y = 0; y < L.Hb; y++)
                    for (int x = 0; x < L.Wb; x++)
                        o.Add(L.Offset + Address((uint)(L.X + x), (uint)(L.Y + y), L.Pitch, (uint)bpb));
            return o;
        }

        // Cube maps: the 360 stores them level by level, six face slices per level (each slice 4 KiB aligned),
        // with one packed tail slice per face. Offsets are returned in the order the input holds its blocks:
        // faceMajor = each face's whole chain in turn, otherwise each level's six faces in turn.
        public static List<uint> CubeOffsets(int width, int count, int blockExtent, int bpb, bool faceMajor, out uint total)
        {
            var levels = Layout(width, width, count, blockExtent, (uint)bpb, out _);
            var bases = new uint[levels.Count]; uint at = 0;
            for (int i = 0; i < levels.Count; i++) { bases[i] = at; if (!levels[i].Tail) at += 6 * levels[i].Stride; }
            var o = new List<uint>(); uint end = 0;
            Action<int, int> emit = (face, i) =>
            {
                var L = levels[i];
                for (int y = 0; y < L.Hb; y++) for (int x = 0; x < L.Wb; x++)
                {
                    uint a = bases[i] + (uint)face * L.Stride + Address((uint)(L.X + x), (uint)(L.Y + y), L.Pitch, (uint)bpb);
                    o.Add(a); end = Math.Max(end, a + (uint)bpb);
                }
            };
            if (faceMajor) for (int f = 0; f < 6; f++) for (int i = 0; i < levels.Count; i++) emit(f, i);
            else for (int i = 0; i < levels.Count; i++) for (int f = 0; f < 6; f++) emit(f, i);
            total = end;
            return o;
        }

        public static byte[] Place(byte[] linear, List<uint> offs, uint total, int bpb, int swapUnit)
        {
            var o = new byte[total]; int at = 0;
            if (Fill != 0) for (int z = 0; z < o.Length; z++) o[z] = Fill;
            foreach (var dst in offs)
            {
                if (at + bpb > linear.Length) throw new Exception("linear mip data truncated");
                for (int k = 0; k < bpb; k += swapUnit)
                    for (int j2 = 0; j2 < swapUnit; j2++) o[dst + k + j2] = linear[at + k + swapUnit - 1 - j2];
                at += bpb;
            }
            if (at != linear.Length) throw new Exception("linear data is " + linear.Length + " bytes, layout uses " + at);
            return o;
        }

        // Linear little-endian levels (concatenated) -> 360 GPU layout and byte order.
        public static byte[] Tile(byte[] linear, int linearOffset, int width, int height, int count, int blockExtent, int bpb, int swapUnit, bool tiled = true)
        {
            var offs = BlockOffsets(width, height, count, blockExtent, bpb, tiled, out uint total);
            var o = new byte[total]; int at = linearOffset;
            if (Fill != 0) for (int z = 0; z < o.Length; z++) o[z] = Fill;
            foreach (var dst in offs)
            {
                if (at + bpb > linear.Length) throw new Exception("linear mip data truncated");
                for (int k = 0; k < bpb; k += swapUnit)
                    for (int j2 = 0; j2 < swapUnit; j2++) o[dst + k + j2] = linear[at + k + swapUnit - 1 - j2];
                at += bpb;
            }
            return o;
        }

        public static int LinearSize(int width, int height, int count, int blockExtent, int bpb)
        {
            int n = 0;
            for (int l = 0; l < count; l++) n += ((Math.Max(1, width >> l) + blockExtent - 1) / blockExtent) * ((Math.Max(1, height >> l) + blockExtent - 1) / blockExtent) * bpb;
            return n;
        }
    }
}
