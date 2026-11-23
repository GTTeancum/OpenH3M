// MCC (little-endian, MCC plugin layout) -> original Xbox 360 (big-endian, 360 plugin layout) tag data translator.
// Input: the data blocks Blamite's DataBlockBuilder reads from the MCC map (raw bytes + fixups at source offsets).
// Output: new data blocks in the 360 layout and byte order, with every fixup moved to its 360 offset, ready for
// Blamite's TagContainerInjector. New code for this project; it only uses Blamite's public data model.
using System;
using System.Collections.Generic;
using System.Linq;
using Blamite.Blam;
using Blamite.Injection;

namespace Inject360
{
    public class Translator
    {
        readonly Dictionary<uint, DataBlock> _src;            // source blocks by original address
        readonly Dictionary<uint, DataBlock> _done = new Dictionary<uint, DataBlock>();
        public readonly List<DataBlock> Output = new List<DataBlock>();
        public readonly List<string> Log = new List<string>();
        public Func<DatumIndex, bool> KeepTagRef = _ => true;   // false -> the reference is cleared (target has no such tag)
        public Func<DatumIndex, bool> KeepResource = _ => false;
        public Func<DataBlockSoundFixup, DataBlockSoundFixup> SoundFixup = _ => null;   // the converted sound rows for a tag, or null when its sound was not converted  // true -> a converted 360 resource exists for this datum
        public int Dropped, Functions, FunctionFallbacks, Identity;

        public DataBlock Get(uint address) => _done.TryGetValue(address, out var b) ? b : null;
        uint _next = 0xFE000000;
        // A new block not taken from the source map (rules build these); its address is synthetic and unique.
        public DataBlock NewBlock(int count, int align, byte[] data)
        {
            while (_src.ContainsKey(_next) || _done.ContainsKey(_next)) _next += 0x10;
            var b = new DataBlock(_next, count, align, false, data); _done[_next] = b; Output.Add(b); _next += 0x10;
            return b;
        }
        public void Remove(DataBlock b) { Output.Remove(b); }

        public Translator(IEnumerable<DataBlock> sourceBlocks)
        {
            _src = new Dictionary<uint, DataBlock>();
            foreach (var b in sourceBlocks) if (!_src.ContainsKey(b.OriginalAddress)) _src[b.OriginalAddress] = b;
        }

        // Field pairs: same plugin file -> by position; different plugin files -> by type + name (+ occurrence).
        static List<(Node s, Node d)> Match(List<Node> s, List<Node> d)
        {
            var pairs = new List<(Node, Node)>();
            if (s.Count == d.Count && s.Zip(d, (a, b) => a.Key == b.Key && a.Offset == b.Offset).All(x => x))
            { for (int i = 0; i < s.Count; i++) pairs.Add((s[i], d[i])); return pairs; }
            var pool = new Dictionary<string, Queue<Node>>();
            foreach (var n in s) { if (!pool.TryGetValue(n.Key, out var q)) pool[n.Key] = q = new Queue<Node>(); q.Enqueue(n); }
            var left = new List<Node>();
            foreach (var n in d)
                if (pool.TryGetValue(n.Key, out var q) && q.Count > 0) pairs.Add((q.Dequeue(), n)); else left.Add(n);
            // Second pass: same name and size, scalar type spelled differently (u8/i8, u16/i16, ...).
            var rest = pool.Values.SelectMany(q => q).ToList();
            foreach (var n in left)
            {
                var m = rest.FirstOrDefault(x => x.Kind == n.Kind && x.Size == n.Size && (x.Name ?? "").Trim().ToLowerInvariant() == (n.Name ?? "").Trim().ToLowerInvariant());
                if (m != null) { rest.Remove(m); pairs.Add((m, n)); continue; }
                // Havok "User Data" is a 64-bit offset on MCC and 32-bit on 360 (re-scaled when copied)
                if ((n.Name ?? "").Trim() == "User Data")
                {
                    var u = rest.FirstOrDefault(x => (x.Name ?? "").Trim() == "User Data");
                    if (u != null) { rest.Remove(u); pairs.Add((u, n)); }
                }
            }
            return pairs;
        }

        static ulong ReadBe(byte[] b, int at, int size) { ulong v = 0; for (int i = 0; i < size; i++) v = v << 8 | b[at + i]; return v; }
        static void WriteBe(byte[] b, int at, int size, ulong v) { for (int i = size - 1; i >= 0; i--) { b[at + i] = (byte)v; v >>= 8; } }
        static bool Generic(string n) => string.IsNullOrEmpty(n) || System.Text.RegularExpressions.Regex.IsMatch(n, @"^(Bit|Unknown) ?\d*$", System.Text.RegularExpressions.RegexOptions.IgnoreCase);
        readonly HashSet<string> _reported = new HashSet<string>();

        // MCC renumbered some flag bits (e.g. weapon flag 21 is "uses 3rd person camera" on 360 but an unrelated bit on MCC):
        // carry each set bit to the 360 bit of the same name.
        void RemapBits(Node s, Node d, byte[] data, int at, string path)
        {
            ulong v = ReadBe(data, at, d.Size), o = 0;
            for (int i = 0; i < d.Size * 8; i++)
            {
                if ((v >> i & 1) == 0) continue;
                s.Bits.TryGetValue(i, out var name);
                int to = -1;
                if (!Generic(name)) foreach (var kv in d.Bits) if (string.Equals(kv.Value, name, StringComparison.OrdinalIgnoreCase)) { to = kv.Key; break; }
                if (to < 0 && (Generic(name) || (d.Bits.TryGetValue(i, out var dn) && string.Equals(dn, name, StringComparison.OrdinalIgnoreCase)))) to = i;
                if (to < 0) { if (_reported.Add(path + d.Name + name)) Log.Add($"flag '{name}' of {path}/{d.Name} has no 360 bit: dropped"); continue; }
                if (to != i && _reported.Add(path + d.Name + name)) Log.Add($"flag '{name}' of {path}/{d.Name}: MCC bit {i} -> 360 bit {to}");
                o |= 1UL << to;
            }
            WriteBe(data, at, d.Size, o);
        }

        void RemapEnum(Node s, Node d, byte[] data, int at, string path)
        {
            int v = (int)ReadBe(data, at, d.Size);
            if (!s.Options.TryGetValue(v, out var name) || Generic(name)) return;
            if (d.Options.TryGetValue(v, out var same) && string.Equals(same, name, StringComparison.OrdinalIgnoreCase)) return;
            foreach (var kv in d.Options)
                if (string.Equals(kv.Value, name, StringComparison.OrdinalIgnoreCase))
                {
                    WriteBe(data, at, d.Size, (ulong)kv.Key);
                    if (_reported.Add(path + d.Name + name)) Log.Add($"option '{name}' of {path}/{d.Name}: MCC {v} -> 360 {kv.Key}");
                    return;
                }
        }

        static void Swap(byte[] src, int so, byte[] dst, int dof, int size, int unit)
        {
            if (unit <= 1) { Buffer.BlockCopy(src, so, dst, dof, size); return; }
            for (int at = 0; at + unit <= size; at += unit)
                for (int k = 0; k < unit; k++) dst[dof + at + k] = src[so + at + unit - 1 - k];
        }

        static void Put32(byte[] d, int at, uint v) { d[at] = (byte)(v >> 24); d[at + 1] = (byte)(v >> 16); d[at + 2] = (byte)(v >> 8); d[at + 3] = (byte)v; }
        static uint Le32(byte[] s, int at) => BitConverter.ToUInt32(s, at);

        public DataBlock TranslateRoot(uint address, Schema s, Schema d, string tag)
            => Block(address, s.Fields, d.Fields, s.BaseSize, d.BaseSize, tag);

        DataBlock Block(uint address, List<Node> sf, List<Node> df, uint sElem, uint dElem, string path)
        {
            if (_done.TryGetValue(address, out var have)) return have;
            if (!_src.TryGetValue(address, out var src)) { Log.Add("missing source block " + path); return null; }
            int count = src.EntryCount;
            if (src.Data.Length != sElem * count) Log.Add($"size mismatch {path}: {src.Data.Length} vs {sElem}x{count}");
            var pairs = Match(sf, df);
            foreach (var n in df.Where(n => !pairs.Any(p => p.d == n))) Log.Add($"no MCC source for 360 field {path}/{n}");
            foreach (var n in sf.Where(n => !pairs.Any(p => p.s == n))) Log.Add($"MCC field not carried {path}/{n}");
            var data = new byte[dElem * count];
            var block = new DataBlock(address, count, src.Alignment, src.Sortable, data);
            _done[address] = block; Output.Add(block);

            // 360-only fields: a tag reference with no MCC source must read "none" (-1), not tag index 0.
            var unmatchedRefs = df.Where(n => n.Kind == Kind.TagRef && !pairs.Any(p => p.d == n)).ToList();
            for (int e = 0; e < count; e++)
                foreach (var n in unmatchedRefs)
                {
                    int dof = (int)(e * dElem + n.Offset);
                    if (n.WithGroup) { Put32(data, dof, 0xFFFFFFFF); Put32(data, dof + 12, 0xFFFFFFFF); } else Put32(data, dof, 0xFFFFFFFF);
                }
            for (int e = 0; e < count; e++)
            {
                int sb = (int)(e * sElem), db = (int)(e * dElem);
                foreach (var (s, d) in pairs)
                {
                    int so = sb + (int)s.Offset, dof = db + (int)d.Offset;
                    if (so + s.Size > src.Data.Length || dof + d.Size > data.Length) continue;
                    switch (d.Kind)
                    {
                        case Kind.Scalar: case Kind.Raw:
                            if ((d.Name ?? "").Trim() == "User Data" && s.Size != d.Size)
                            {
                                // Offset of this shape's Havok header from the block start: index x element size + where the
                                // header (its runtime code pointer) sits inside the element. Stock 360 phmo: 0x20, 0xA0, ...
                                ulong v = s.Size == 8 ? BitConverter.ToUInt64(src.Data, so) : BitConverter.ToUInt32(src.Data, so);
                                uint sHead = sf.Where(x => (x.Name ?? "").Trim() == "Runtime Code Pointer" && x.Offset < s.Offset).Select(x => x.Offset).DefaultIfEmpty(0u).Max();
                                uint dHead = df.Where(x => (x.Name ?? "").Trim() == "Runtime Code Pointer" && x.Offset < d.Offset).Select(x => x.Offset).DefaultIfEmpty(0u).Max();
                                if (v == 0) Put32(data, dof, 0);
                                else
                                {
                                    ulong idx = (v - sHead) / sElem;
                                    if ((v - sHead) % sElem != 0 && _reported.Add(path + "userdata")) Log.Add($"Havok user data {path}: 0x{v:X} is not index x size + header");
                                    Put32(data, dof, (uint)(idx * dElem + dHead));
                                }
                            }
                            else Swap(src.Data, so, data, dof, Math.Min(s.Size, d.Size), d.Unit);
                            if (s.Bits != null && d.Bits != null) RemapBits(s, d, data, dof, path);
                            else if (s.Options != null && d.Options != null) RemapEnum(s, d, data, dof, path);
                            break;
                        case Kind.StringId: Put32(data, dof, 0); break;            // filled by its string fixup
                        case Kind.TagRef:
                            if (d.WithGroup) { Put32(data, dof, Le32(src.Data, so)); Put32(data, dof + 12, 0xFFFFFFFF); }
                            else Put32(data, dof, 0xFFFFFFFF);
                            break;
                        case Kind.Block: Put32(data, dof, Le32(src.Data, so)); break;  // count; pointer by fixup
                        case Kind.DataRef: Put32(data, dof, Le32(src.Data, so)); break; // size; pointer by fixup
                        default: break;                                                // shader / unic: not carried
                    }
                }
            }
            // Collision BSP nodes pack two 24-bit child indices and a 16-bit plane into one 64-bit value.
            if (path.EndsWith("/BSP3D Nodes") && sElem == 8 && dElem == 8)
                for (int e = 0; e < count; e++) for (int k = 0; k < 8; k++) data[e * 8 + k] = src.Data[e * 8 + 7 - k];
            // MOPP bounding-tree code: byte stream with re-encoded shape keys.
            if (path.EndsWith("/MOPP Data") && dElem == 1)
            {
                try { var m = Havok.MoppCode(data); Buffer.BlockCopy(m, 0, data, 0, m.Length); }
                catch (Exception ex) { Log.Add($"MOPP code {path}: {ex.Message}"); }
            }

            // Map a source write offset to the target layout.
            Func<int, (int at, Node s, Node d)> map = off =>
            {
                int e = (int)(off / sElem), rel = (int)(off % sElem);
                foreach (var (s, d) in pairs)
                    if (rel >= s.Offset && rel < s.Offset + s.Size)
                        return ((int)(e * dElem + d.Offset + (rel - s.Offset)), s, d);
                return (-1, null, null);
            };

            foreach (var f in src.AddressFixups)
            {
                var (at, s, d) = map(f.WriteOffset);
                if (at < 0) { Dropped++; Log.Add($"dropped child of unmatched field {path} @0x{f.WriteOffset:X}"); continue; }
                DataBlock child = null;
                if (d.Kind == Kind.Block)
                    child = Block(f.OriginalAddress, s.Kids, d.Kids, s.ElementSize, d.ElementSize, path + "/" + d.Name);
                else if (d.Kind == Kind.DataRef)
                    child = Data(f.OriginalAddress, d, path + "/" + d.Name);
                if (child != null && d.Kind == Kind.DataRef) Put32(data, at - 12, (uint)child.Data.Length);   // a converted function can change length
                if (child == null) { Dropped++; Put32(data, d.Kind == Kind.Block ? at - 4 : d.Kind == Kind.DataRef ? at - 12 : at, 0); continue; }
                block.AddressFixups.Add(new DataBlockAddressFixup(f.OriginalAddress, at));
            }
            foreach (var f in src.TagFixups)
            {
                var (at, _, d) = map(f.WriteOffset);
                if (at < 0 || !KeepTagRef(f.OriginalIndex)) { Dropped++; continue; }
                block.TagFixups.Add(new DataBlockTagFixup(f.OriginalIndex, at));
            }
            foreach (var f in src.StringIDFixups)
            {
                var (at, _, _) = map(f.WriteOffset);
                if (at < 0) { Dropped++; continue; }
                block.StringIDFixups.Add(new DataBlockStringIDFixup(f.OriginalString, at));
            }
            foreach (var f in src.ResourceFixups)
            {
                var (at, _, _) = map(f.WriteOffset);
                if (at < 0) { Dropped++; continue; }
                if (!KeepResource(f.OriginalIndex)) { Put32(data, at, 0xFFFFFFFF); Log.Add($"resource cleared {path} @0x{at:X}"); continue; }
                block.ResourceFixups.Add(new DataBlockResourceFixup(f.OriginalIndex, at));
            }
            int lostSound = 0;
            foreach (var f in src.SoundFixups) { var n = SoundFixup(f); if (n != null) block.SoundFixups.Add(n); else lostSound++; }
            int other = src.ShaderFixups.Count + src.UnicListFixups.Count + src.InteropFixups.Count + src.EffectFixups.Count + lostSound;
            if (other > 0) { Dropped += other; Log.Add($"{other} shader/unic/interop/effect/sound fixups not carried in {path}"); }
            return block;
        }

        DataBlock Data(uint address, Node d, string path)
        {
            if (_done.TryGetValue(address, out var have)) return have;
            if (!_src.TryGetValue(address, out var src)) return null;
            byte[] data;
            var name = (d.Name ?? "").ToLowerInvariant();
            if (name.Contains("function")) data = Function(src.Data, path);
            else if (name == "mopp codes")
            {
                try { data = Havok.PackedMopp(src.Data); }
                catch (Exception ex) { Log.Add($"packed MOPP {path}: {ex.Message} (copied unchanged)"); data = (byte[])src.Data.Clone(); }
            }
            else
            {
                data = (byte[])src.Data.Clone();
                if (!name.Contains("script")) Log.Add($"data reference copied unchanged {path} ({data.Length} bytes)");
            }
            var block = new DataBlock(address, 1, src.Alignment, false, data);
            _done[address] = block; Output.Add(block);
            return block;
        }

        // Tag function: 4 header bytes, 7 header words (word 7 = payload length), then opcode-specific payload.
        // Layout knowledge from the project's earlier function notes and observed tags; this is a new implementation.
        byte[] Function(byte[] s, string path)
        {
            var d = (byte[])s.Clone();
            try
            {
                if (s.Length < 32) throw new Exception("short");
                int at = 4;
                Action<int> words = n => { if (at + 4 * n > s.Length) throw new Exception("truncated"); for (int i = 0; i < n; i++, at += 4) Swap(s, at, d, at, 4, 4); };
                words(7);
                int payload = (int)Le32(s, 28);
                if (payload != s.Length - 32) throw new Exception("payload length");
                int passes = (s[1] & 1) != 0 ? 2 : 1;
                for (int p = 0; p < passes; p++)
                {
                    switch (s[0])
                    {
                        case 0: case 1: break;
                        case 2: at += 4; words(2); break;
                        case 3: at += 4; words(4); break;
                        case 4: words(2); break;
                        case 5: words(20); break;
                        case 7: words(4); break;
                        case 9: words(3); break;
                        case 10: words(7); break;
                        case 8:
                            int sections = (int)Le32(s, at); words(1);
                            for (int i = 0; i < sections; i++) { int kind = s[at]; at += 4; words(kind == 4 ? 3 : kind == 7 ? 5 : 8); }
                            break;
                        default: throw new Exception("opcode " + s[0]);
                    }
                }
                if (at != s.Length) throw new Exception($"consumed {at} of {s.Length}");
                Functions++;
                // MCC stores an identity function as type 0 with no payload (32 bytes). The 2007 engine has no such type:
                // the same stock functions on the 360 are type 8 with one linear segment (52 bytes; seen on every stock
                // tag compared - Hornet functions, battle rifle firing effect, battle rifle damage effect).
                if (s[0] == 0 && s.Length == 32 && (s[1] & 1) == 0)
                {
                    var e = new byte[52]; Buffer.BlockCopy(d, 0, e, 0, 32);
                    e[0] = 8; e[31] = 0x14;
                    var tail = new byte[] { 0, 0, 0, 1, 4, 0, 0, 0xCD, 0x7F, 0x7F, 0xFF, 0xFF, 0x3F, 0x80, 0, 0, 0, 0, 0, 0 };
                    Buffer.BlockCopy(tail, 0, e, 32, 20);
                    Identity++;
                    return e;
                }
                return d;
            }
            catch (Exception ex)
            {
                // Fallback: keep header bytes, swap every following 32-bit word (all payloads are floats/ints).
                FunctionFallbacks++;
                Log.Add($"function fallback {path}: {ex.Message} (opcode {(s.Length > 0 ? s[0] : -1)}, {s.Length} bytes)");
                var f = (byte[])s.Clone();
                for (int at = 4; at + 4 <= s.Length; at += 4) Swap(s, at, f, at, 4, 4);
                return f;
            }
        }
    }
}
