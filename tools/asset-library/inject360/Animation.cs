// model_animation_tag_resource: MCC (little-endian) -> original 360 (big-endian), without resampling.
// Control: root {member count, table pointer, 4 unused}; member = 48 bytes {name string id, checksum, frame count u16,
// node count u8, movement type u8, two u8, three u16 (movement bytes, pill bytes, static bytes), uncompressed bytes,
// compressed bytes, data reference (size +28, pointer +40)}. Codec stream layouts per the project's animation notes
// (animation_resource.py, from TagTool's codec readers); new implementation.
using System;
using System.Collections.Generic;
using System.Linq;
using Blamite.Blam;
using Blamite.Blam.Resources;
using Blamite.Injection;

namespace Inject360
{
    public static class AnimationConverter
    {
        static uint Le32(byte[] b, int at) => BitConverter.ToUInt32(b, at);
        static int Le16(byte[] b, int at) => BitConverter.ToUInt16(b, at);
        static void Be32(byte[] b, int at, uint v) { b[at] = (byte)(v >> 24); b[at + 1] = (byte)(v >> 16); b[at + 2] = (byte)(v >> 8); b[at + 3] = (byte)v; }
        static void Be16(byte[] b, int at, int v) { b[at] = (byte)(v >> 8); b[at + 1] = (byte)v; }
        static void Swap(byte[] s, byte[] d, int start, int end, int width)
        {
            if (start < 0 || end > s.Length || start > end || (end - start) % width != 0) throw new Exception("animation stream bounds");
            for (int at = start; at < end; at += width) for (int k = 0; k < width; k++) d[at + k] = s[at + width - 1 - k];
        }

        public static byte[] Codec(byte[] s, int frames)
        {
            if (s.Length < 32) throw new Exception("truncated codec");
            var d = (byte[])s.Clone();
            int codec = s[0], rot = s[1], tr = s[2], sc = s[3];
            if (codec == 1 || codec == 3 || codec == 8)
            {
                Swap(s, d, 4, 32, 4);
                int trOff = (int)Le32(s, 12), scOff = (int)Le32(s, 16), rb = (int)Le32(s, 20), tb = (int)Le32(s, 24), sb = (int)Le32(s, 28), end;
                if (codec == 1) { trOff = 32 + rot * 8; scOff = trOff + tr * 12; end = scOff + sc * 4; }
                else
                {
                    int rw = codec == 8 ? 16 : 8;
                    if (rb != frames * rw || tb != frames * 12 || sb != frames * 4) throw new Exception("unexpected node stride");
                    if (trOff != 32 + rb * rot || scOff != trOff + tb * tr) throw new Exception("node offsets disagree");
                    end = scOff + sb * sc;
                }
                if (end > s.Length) throw new Exception("codec overruns");
                Swap(s, d, 32, trOff, codec == 8 ? 4 : 2);
                Swap(s, d, trOff, end, 4);
                return d;
            }
            if (codec >= 4 && codec <= 7)
            {
                if (s.Length < 48) throw new Exception("truncated keyframe codec");
                int rk = (int)Le32(s, 20), rf = (int)Le32(s, 32), tf = (int)Le32(s, 36);
                Swap(s, d, 4, rk, 4);
                if (codec == 5 || codec == 7) Swap(s, d, rk, rf, 2);
                Swap(s, d, rf, tf, 2);
                Swap(s, d, tf, s.Length - (s.Length - tf) % 4, 4);
                return d;
            }
            throw new Exception("animation codec " + codec + " has no converter yet");
        }

        public class Result { public ExtractedResourceInfo Resource; public List<(int offset, string name)> Names = new List<(int, string)>(); public string Note; }

        public static Result Convert(Resource src, Func<ResourcePage, byte[]> pageBytes, ResourceSink sink, DatumIndex parentTag, Func<uint, string> mccString)
        {
            var c = src.Info; if (c == null) return new Result { Note = "no control data" };
            var fix = src.ResourceFixups.ToDictionary(f => f.Offset, f => f.Address);
            int root = src.BaseDefinitionAddress & 0x1FFFFFFF;
            int count = (int)Le32(c, root);
            int table = count > 0 ? (int)(fix[root + 4] & 0x1FFFFFFF) : 0;
            var ctl = new byte[12 + count * 48]; Be32(ctl, 0, (uint)count);
            var res = new Result();
            var r = new ExtractedResourceInfo(src.Index)
            {
                Flags = src.Flags, Type = src.Type, Info = ctl, ResourceBits = src.ResourceBits, BaseDefinitionAddress = 0x20000000,
                OriginalParentTagIndex = parentTag, Location = new ExtractedResourcePointer(),
            };
            if (count > 0) r.ResourceFixups.Add(new ResourceFixup { Offset = 4, Address = 0x2000000C });
            var raw = new List<byte>(); var codecs = new HashSet<int>();
            for (int i = 0; i < count; i++)
            {
                int at = table + i * 48, dst = 12 + i * 48;
                uint name = Le32(c, at), checksum = Le32(c, at + 4);
                int frames = Le16(c, at + 8), nodes = c[at + 10], movement = c[at + 11], sf = c[at + 12], af = c[at + 13];
                int md = Le16(c, at + 14), pill = Le16(c, at + 16), stat = Le16(c, at + 18);
                uint unpacked = Le32(c, at + 20), compressed = Le32(c, at + 24); int size = (int)Le32(c, at + 28);
                if (movement > 1 || pill != 0 || unpacked != 0) throw new Exception($"animation {i}: movement {movement}, pill {pill}, uncompressed {unpacked} not supported yet");
                uint addr = fix[at + 40];
                var pg = (addr & 0xE0000000) == 0x40000000 ? src.Location.PrimaryPage : src.Location.SecondaryPage;
                int off = (int)(addr & 0x1FFFFFFF) + Math.Max(0, (addr & 0xE0000000) == 0x40000000 ? src.Location.PrimaryOffset : src.Location.SecondaryOffset);
                var data = pageBytes(pg).Skip(off).Take(size).ToArray();
                if (data.Length != size || size != stat + compressed + sf + af + md) throw new Exception($"animation {i}: payload size mismatch");
                var payload = new List<byte>();
                if (stat > 0) { payload.AddRange(Codec(data.Take(stat).ToArray(), frames)); codecs.Add(data[0]); }
                payload.AddRange(Codec(data.Skip(stat).Take((int)compressed).ToArray(), frames)); codecs.Add(data[stat]);
                var tail = data.Skip(stat + (int)compressed).ToArray(); var tailBe = (byte[])tail.Clone(); Swap(tail, tailBe, 0, tail.Length - tail.Length % 4, 4);
                payload.AddRange(tailBe);
                res.Names.Add((dst, mccString(name)));
                Be32(ctl, dst + 4, checksum); Be16(ctl, dst + 8, frames); ctl[dst + 10] = (byte)nodes; ctl[dst + 11] = (byte)movement;
                ctl[dst + 12] = (byte)sf; ctl[dst + 13] = (byte)af; Be16(ctl, dst + 14, md); Be16(ctl, dst + 16, pill); Be16(ctl, dst + 18, stat);
                Be32(ctl, dst + 20, unpacked); Be32(ctl, dst + 24, compressed); Be32(ctl, dst + 28, (uint)size);
                while (raw.Count % 16 != 0) raw.Add(0);
                r.ResourceFixups.Add(new ResourceFixup { Offset = dst + 40, Address = 0x40000000u | (uint)raw.Count });
                raw.AddRange(payload);
            }
            if (raw.Count > 0) { r.Location.OriginalPrimaryPageIndex = sink.Page(raw.ToArray()); r.Location.PrimaryOffset = 0; }
            sink.Add(r);
            res.Resource = r; res.Note = $"{count} animations, codecs {string.Join(",", codecs.OrderBy(x => x))} ({raw.Count} bytes)";
            return res;
        }
    }
}
