// Point existing tag references in chosen tags of the target map at other tags (e.g. a palette entry or the
// multiplayer weapon list at a ported weapon). Schema-driven; writes only the 4-byte datum of a matching reference.
using System;
using System.Collections.Generic;
using Blamite.Blam;
using Blamite.IO;

namespace Inject360
{
    public static class Retarget
    {
        public static int Apply(ICacheFile file, IStream s, ITag tag, Schema schema, Dictionary<uint, uint> map, List<string> log, string tagName)
        {
            int n = 0;
            Walk(file, s, tag.MetaLocation.AsOffset(), schema.Fields, map, ref n, log, tagName, "");
            return n;
        }

        static void Walk(ICacheFile file, IStream s, long at, List<Node> fields, Dictionary<uint, uint> map, ref int n, List<string> log, string tagName, string path)
        {
            foreach (var f in fields)
            {
                if (f.Kind == Kind.TagRef)
                {
                    long datumAt = at + f.Offset + (f.WithGroup ? 12 : 0);
                    s.SeekTo(datumAt); uint d = s.ReadUInt32();
                    if (map.TryGetValue(d, out var nd))
                    {
                        s.SeekTo(datumAt); s.WriteUInt32(nd); n++;
                        log.Add($"retarget {tagName}{path}/{f.Name}: 0x{d:X8} -> 0x{nd:X8}");
                    }
                }
                else if (f.Kind == Kind.Block && !(f.Name ?? "").StartsWith("Simulation Definition"))   // network table lists each tag once; leave it
                {
                    s.SeekTo(at + f.Offset); int count = s.ReadInt32(); uint ptr = s.ReadUInt32();
                    if (count <= 0 || ptr == 0) continue;
                    long off = file.MetaArea.PointerToOffset(file.PointerExpander.Expand(ptr));
                    for (int i = 0; i < count; i++) Walk(file, s, off + i * f.ElementSize, f.Kids, map, ref n, log, tagName, path + "/" + f.Name + "[" + i + "]");
                }
            }
        }
    }
}
