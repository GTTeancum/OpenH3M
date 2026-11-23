// TagTool serialization into Blamite data blocks.
// TagTool's TagSerializer writes a tag definition for a chosen game version, platform and byte order (here Halo 3
// retail, Xbox 360, big-endian), converting versioned enums itself. This context receives its output: every tag
// block TagTool creates becomes a Blamite DataBlock; pointers become address fixups, tag references tag fixups,
// string ids string fixups (by string), so Blamite's TagContainerInjector can place them in a 360 map.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Blamite.Injection;
using TagTool.Cache;
using TagTool.Common;
using TagTool.IO;
using TagTool.Serialization;
using TagTool.Tags;
using BDatum = Blamite.Blam.DatumIndex;

namespace Ho2H3
{
    public class H3Context : ISerializationContext
    {
        public readonly GameCache Source;                 // the Halo Online cache (strings, tags)
        public readonly Func<CachedTag, BDatum> TagDatum; // source tag -> datum used in the container
        public readonly Func<object, TagFieldAttribute, Block, object> Pre;   // value hook (resources etc.); may replace the value
        public readonly List<Block> Blocks = new List<Block>();
        public Block MainBlock; public uint NextAddress = 0x10000000;
        public readonly MemoryStream Stream = new MemoryStream();   // TagTool's tag stream (layout only; data lives in the blocks)

        public H3Context(GameCache source, Func<CachedTag, BDatum> tagDatum, Func<object, TagFieldAttribute, Block, object> pre = null) { Source = source; TagDatum = tagDatum; Pre = pre; }

        public void BeginSerialize(TagStructureInfo info) { }
        public void EndSerialize(TagStructureInfo info, byte[] data, uint mainStructOffset)
        {
            // the main struct is the last finalized block whose stream offset is mainStructOffset
            MainBlock = Blocks.LastOrDefault(b => b.StreamOffset == mainStructOffset) ?? Blocks.LastOrDefault();
            // data references (byte[] / TagData) are written by TagTool straight into its tag stream, not as blocks: each
            // becomes a block of its own here. The reference is size, 0, 0, pointer, 0, so the size is 12 bytes before the pointer.
            var known = new HashSet<long>(Blocks.Select(b => b.StreamOffset));
            foreach (var b in Blocks.ToList())
            {
                var bd = b.Stream.ToArray();
                foreach (var (at, target) in b.Pointers)
                {
                    if (known.Contains(target) || at < 12) continue;
                    int size = bd[at - 12] << 24 | bd[at - 11] << 16 | bd[at - 10] << 8 | bd[at - 9];
                    if (size <= 0 || target + size > data.Length) continue;
                    var nb = new Block(this) { StreamOffset = target, Address = (uint)target, Align = 16, IsData = true };
                    nb.Stream.Write(data, (int)target, size);
                    Blocks.Add(nb); known.Add(target); DataBlocks++;
                }
            }
        }
        public int DataBlocks;
        public EndianReader BeginDeserialize(TagStructureInfo info) => throw new NotSupportedException();
        public void EndDeserialize(TagStructureInfo info, object obj) => throw new NotSupportedException();
        public uint AddressToOffset(uint currentOffset, uint address) => address;
        public CachedTag GetTagByIndex(int index) => Source.TagCache.GetTag(index);
        public CachedTag GetTagByName(TagGroup group, string name) => Source.TagCache.GetTag(name, group.Tag.ToString());
        public IDataBlock CreateBlock() => new Block(this);
        public void AddResourceBlock(int count, CacheAddress address, System.Collections.IList block) { }

        public class Block : IDataBlock
        {
            readonly H3Context _c;
            public MemoryStream Stream { get; } = new MemoryStream();
            public EndianWriter Writer { get; }
            public uint Align = 4; public long StreamOffset = -1; public uint Address;
            public readonly List<(int at, long target)> Pointers = new List<(int, long)>();
            public readonly List<(int at, BDatum datum)> Tags = new List<(int, BDatum)>();
            public readonly List<(int at, string str)> Strings = new List<(int, string)>();
            public readonly List<(int at, object res)> Resources = new List<(int, object)>();
            public int EntryCount = 1; public bool IsData;
            public Block(H3Context c) { _c = c; Writer = new EndianWriter(Stream, EndianFormat.BigEndian); }
            public void WritePointer(uint targetOffset, Type type) { Pointers.Add(((int)Stream.Position, targetOffset)); Writer.Write(targetOffset); }
            public readonly List<int> NullRefs = new List<int>();   // datum positions of references cleared (group written too for full refs)
            public void AddTagReference(CachedTag referencedTag, bool isShort)
            {
                // called before TagTool writes the reference: full references are group, 0, 0, datum (datum at +12)
                int at = (int)Stream.Position + (isShort ? 0 : 12);
                var d = referencedTag == null ? BDatum.Null : _c.TagDatum(referencedTag);
                if (d.Value == 0xFFFFFFFF) { NullRefs.Add(isShort ? -at - 1 : at); return; }
                Tags.Add((at, d));
            }
            public object PreSerialize(TagFieldAttribute info, object obj)
            {
                if (obj is StringId sid)
                {
                    var s = sid == StringId.Invalid ? null : _c.Source.StringTable.GetString(sid);
                    if (!string.IsNullOrEmpty(s)) Strings.Add(((int)Stream.Position, s));
                    return StringId.Invalid;
                }
                return _c.Pre != null ? _c.Pre(obj, info, this) : obj;
            }
            public void SuggestAlignment(uint align) { Align = Math.Max(Align, align); }
            public uint Finalize(Stream outStream)
            {
                // place in TagTool's stream for offsets; the data itself is kept by this block
                while (outStream.Position % Align != 0) outStream.WriteByte(0);
                StreamOffset = outStream.Position; var data = Stream.ToArray(); outStream.Write(data, 0, data.Length);
                Address = (uint)StreamOffset;
                _c.Blocks.Add(this);
                return (uint)StreamOffset;
            }
        }

        // TagTool's blocks -> Blamite DataBlocks (original addresses are the TagTool stream offsets, made unique per tag)
        public List<DataBlock> ToDataBlocks(uint addressBase, Func<object, int, DataBlock, bool> resource)
        {
            var map = Blocks.ToDictionary(b => b.StreamOffset, b => (uint)(addressBase + b.StreamOffset));
            var outB = new List<DataBlock>();
            // a block's element count is the count written just before the pointer that refers to it
            var counts = new Dictionary<long, int>();
            foreach (var b in Blocks) { var d0 = b.Stream.ToArray(); foreach (var (at, target) in b.Pointers) if (at >= 4) counts[target] = d0[at - 4] << 24 | d0[at - 3] << 16 | d0[at - 2] << 8 | d0[at - 1]; }
            foreach (var b in Blocks) if (counts.TryGetValue(b.StreamOffset, out var n) && n > 0) b.EntryCount = n;
            foreach (var b in Blocks)
            {
                var data = b.Stream.ToArray();
                var db = new DataBlock(map[b.StreamOffset], b.EntryCount, (int)b.Align, false, data);
                foreach (var (at, target) in b.Pointers)
                    if (map.TryGetValue(target, out var to)) db.AddressFixups.Add(new DataBlockAddressFixup(to, at));
                foreach (var (at, datum) in b.Tags)
                {
                    // TagTool writes group (4), name pointer/padding (8), datum (4) for full references; locate the datum
                    db.TagFixups.Add(new DataBlockTagFixup(datum, at));
                }
                foreach (var at0 in b.NullRefs)
                {
                    bool shortRef = at0 < 0; int at = shortRef ? -at0 - 1 : at0;
                    for (int k = 0; k < 4; k++) data[at + k] = 0xFF;
                    if (!shortRef) for (int k = 0; k < 4; k++) data[at - 12 + k] = 0xFF;
                }
                foreach (var (at, s) in b.Strings) db.StringIDFixups.Add(new DataBlockStringIDFixup(s, at));
                foreach (var (at, r) in b.Resources) resource?.Invoke(r, at, db);
                outB.Add(db);
            }
            return outB;
        }
    }
}
