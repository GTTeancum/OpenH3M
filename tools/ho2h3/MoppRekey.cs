// Havok MOPP code key remapping. TagTool's MOPP tool keys primitives by input order; Halo 3's structure physics MOPP
// mixes key ranges (structure surfaces 0x20050000 | surface, placed pieces 0x40000000 | instance; COLLISION-360.md).
// The code is re-emitted with the same opcodes in the same order: every terminal becomes an absolute key
// (HK_MOPP_TERM_REOFFSET32 key, HK_MOPP_TERM4_0), unconditional jumps are followed, the source's re-offsets are applied
// and dropped, and every branch's children are placed after the branch behind forward HK_MOPP_JUMP24 so no child has to
// fit an 8 or 16-bit branch offset. Opcode layouts as TagTool's HavokMoppUtil decodes them.
using System;
using System.Collections.Generic;
using System.Linq;

namespace Ho2H3
{
    static class MoppRekey
    {
        public static byte[] Rekey(IList<byte> code, Func<int, int> map)
        {
            var o = new List<byte>();
            void J24(out int at) { at = o.Count; o.Add(0x07); o.Add(0); o.Add(0); o.Add(0); }
            void Patch(int at) { int d = o.Count - (at + 4); if (d < 0 || d > 0xFFFFFF) throw new InvalidOperationException("MOPP jump out of range"); o[at + 1] = (byte)(d >> 16); o[at + 2] = (byte)(d >> 8); o[at + 3] = (byte)d; }
            void Copy(int i, int n) { for (int k = 0; k < n; k++) o.Add(code[i + k]); }
            void Path(int i, int offset)
            {
                while (true)
                {
                    int op = code[i];
                    switch (op)
                    {
                        case 0x00: o.Add(0); return;
                        case 0x01: case 0x02: case 0x03: case 0x04: Copy(i, 4); i += 4; break;
                        case 0x05: i += code[i + 1] + 2; break;
                        case 0x06: i += 256 * code[i + 1] + code[i + 2] + 3; break;
                        case 0x07: i += 256 * (code[i + 2] + (code[i + 1] << 8)) + code[i + 3] + 4; break;
                        case 0x09: offset += code[i + 1]; i += 2; break;
                        case 0x0A: offset += code[i + 2] + (code[i + 1] << 8); i += 3; break;
                        case 0x0B: offset = code[i + 4] + ((code[i + 3] + ((code[i + 2] + (code[i + 1] << 8)) << 8)) << 8); i += 5; break;
                        case >= 0x10 and <= 0x1C:
                        {
                            int c1 = i + 4, c2 = i + 4 + code[i + 3];
                            o.Add((byte)op); o.Add(code[i + 1]); o.Add(code[i + 2]); o.Add(4);
                            J24(out int j1); J24(out int j2);
                            Patch(j1); Path(c1, offset); Patch(j2); Path(c2, offset); return;
                        }
                        case 0x20: case 0x21: case 0x22:
                        {
                            int c1 = i + 3, c2 = i + 3 + code[i + 2];
                            o.Add((byte)op); o.Add(code[i + 1]); o.Add(4);
                            J24(out int j1); J24(out int j2);
                            Patch(j1); Path(c1, offset); Patch(j2); Path(c2, offset); return;
                        }
                        case 0x23: case 0x24: case 0x25:
                        {
                            int b = i + 7, ca = b + (code[i + 4] + (code[i + 3] << 8)), cb = b + (code[i + 6] + (code[i + 5] << 8));
                            o.Add((byte)op); o.Add(code[i + 1]); o.Add(code[i + 2]); o.Add(0); o.Add(0); o.Add(0); o.Add(4);
                            J24(out int j1); J24(out int j2);
                            Patch(j1); Path(ca, offset); Patch(j2); Path(cb, offset); return;
                        }
                        case 0x26: case 0x27: case 0x28: Copy(i, 3); i += 3; break;
                        case 0x29: case 0x2A: case 0x2B: Copy(i, 7); i += 7; break;
                        case >= 0x30 and <= 0x53:
                        {
                            int t = op <= 0x4F ? op - 0x30
                                : op == 0x50 ? code[i + 1]
                                : op == 0x51 ? code[i + 2] + (code[i + 1] << 8)
                                : op == 0x52 ? code[i + 3] + ((code[i + 2] + (code[i + 1] << 8)) << 8)
                                : ((code[i + 2] + (code[i + 1] << 8)) << 16) + code[i + 4] + (code[i + 3] << 8);
                            int k = map(offset + t);
                            o.Add(0x0B); o.Add((byte)(k >> 24)); o.Add((byte)(k >> 16)); o.Add((byte)(k >> 8)); o.Add((byte)k); o.Add(0x30);
                            return;
                        }
                        case 0x60: case 0x61: case 0x62: case 0x63: Copy(i, 2); i += 2; break;
                        case 0x64: case 0x65: case 0x66: case 0x67: Copy(i, 3); i += 3; break;
                        case 0x68: case 0x69: case 0x6A: case 0x6B: Copy(i, 5); i += 5; break;
                        default: throw new InvalidOperationException($"MOPP opcode 0x{op:X2} at {i}");
                    }
                }
            }
            Path(0, 0);
            // check: the same keys, remapped, in the same order
            var before = TagTool.Havok.HavokMoppUtil.GetAllKeys(code).Select(map).ToList();
            var after = TagTool.Havok.HavokMoppUtil.GetAllKeys(o);
            if (!before.SequenceEqual(after)) throw new InvalidOperationException("MOPP re-key check failed");
            return o.ToArray();
        }
    }
}
