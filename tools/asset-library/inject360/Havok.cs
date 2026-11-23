// Havok data inside collision / physics tags: MOPP bounding-tree code and its headers, MCC -> original 360.
// Opcode lengths and the shape-key re-encoding follow the project's collision notes (collision_physics.py);
// this is a new implementation.
using System;
using System.Collections.Generic;

namespace Inject360
{
    public static class Havok
    {
        // operand byte count per MOPP opcode
        static readonly Dictionary<int, int> Len = Build();
        static Dictionary<int, int> Build()
        {
            var d = new Dictionary<int, int> { [0] = 0, [5] = 1, [6] = 2, [7] = 3, [8] = 4, [9] = 1, [10] = 2, [11] = 4, [12] = 2, [13] = 5 };
            for (int i = 1; i <= 4; i++) d[i] = 3;
            for (int i = 0x10; i < 0x1D; i++) d[i] = 3;
            for (int i = 0x20; i < 0x23; i++) d[i] = 2;
            for (int i = 0x23; i < 0x26; i++) d[i] = 6;
            for (int i = 0x26; i < 0x29; i++) d[i] = 2;
            for (int i = 0x29; i < 0x2C; i++) d[i] = 6;
            for (int i = 0x30; i < 0x50; i++) d[i] = 0;
            for (int i = 0; i < 4; i++) { d[0x50 + i] = i + 1; d[0x54 + i] = i + 1; }
            for (int i = 0x60; i < 0x64; i++) d[i] = 1;
            for (int i = 0x64; i < 0x68; i++) d[i] = 2;
            for (int i = 0x68; i < 0x6C; i++) d[i] = 4;
            return d;
        }

        // MOPP code is a byte stream (no endian change); 32-bit shape keys (opcodes 0x0B, 0x53) are re-encoded
        // from the MCC key layout to the original layout.
        public static byte[] MoppCode(byte[] code)
        {
            var o = (byte[])code.Clone(); int at = 0;
            while (at < o.Length)
            {
                int op = o[at];
                if (!Len.TryGetValue(op, out int n) || at + n + 1 > o.Length) throw new Exception($"MOPP opcode 0x{op:X2} unsupported or truncated at {at}");
                if (op == 0x0B || op == 0x53)
                {
                    uint key = (uint)(o[at + 1] << 24 | o[at + 2] << 16 | o[at + 3] << 8 | o[at + 4]);
                    if ((key & 0x83FF0000) != 0) throw new Exception($"MOPP key 0x{key:X8} cannot be represented on 360");
                    key = (key & 0x60000000) | (((key >> 26) & 7) << 16) | (key & 0xFFFF);
                    o[at + 1] = (byte)(key >> 24); o[at + 2] = (byte)(key >> 16); o[at + 3] = (byte)(key >> 8); o[at + 4] = (byte)key;
                }
                at += n + 1;
            }
            return o;
        }

        static uint Le32(byte[] b, int at) => BitConverter.ToUInt32(b, at);
        static void Be32(byte[] b, int at, uint v) { b[at] = (byte)(v >> 24); b[at + 1] = (byte)(v >> 16); b[at + 2] = (byte)(v >> 8); b[at + 3] = (byte)v; }

        // Packed MOPP data reference: repeated {48-byte header, code, padding to 16}. MCC headers hold 64-bit
        // runtime pointers at +0 and +32; the 360 header keeps size/count, the offset vector and size/capacity.
        public static byte[] PackedMopp(byte[] p)
        {
            var o = new List<byte>(); int at = 0;
            while (at < p.Length)
            {
                if (at + 48 > p.Length) throw new Exception("truncated packed MOPP header");
                int size = (int)Le32(p, at + 40); uint cap = Le32(p, at + 44);
                int end = at + 48 + size, aligned = (end + 15) & ~15;
                if (end > p.Length || (cap & 0x7FFFFFFF) < size) throw new Exception("packed MOPP code exceeds its allocation");
                var h = new byte[48];
                h[4] = p[at + 9]; h[5] = p[at + 8]; h[6] = p[at + 11]; h[7] = p[at + 10];        // size, count (u16)
                for (int i = 0; i < 4; i++) Be32(h, 16 + i * 4, Le32(p, at + 16 + i * 4));      // offset vector + w
                Be32(h, 36, (uint)size); Be32(h, 40, cap);
                o.AddRange(h);
                var code = new byte[size]; Buffer.BlockCopy(p, at + 48, code, 0, size);
                o.AddRange(MoppCode(code));
                while (o.Count % 16 != 0) o.Add(0);
                at = Math.Min(aligned, p.Length);
            }
            return o.ToArray();
        }
    }
}
