using System.Collections;
using TagTool.Cache;
using TagTool.Common;
using TagTool.IO;
using TagTool.Serialization;
using TagTool.Tags;
using TagTool.Tags.Definitions;

static class RenderBridge
{
    public static object Convert(RenderModel model)
    {
        model.Version = 0; // Native H3 Forge architecture's model version.
        foreach (var material in model.Materials)
            material.BreakableSurfaceIndex = -1; // Reach has no retail breakable-set entry.
        var geometry = model.Geometry;
        if ((int)geometry.RuntimeFlags != 7 && (int)geometry.RuntimeFlags != 39)
            throw new InvalidDataException("Unreviewed Reach render geometry flags");
        geometry.RuntimeFlags = (TagTool.Geometry.RenderGeometryRuntimeFlags)7;
        foreach (var mesh in geometry.Meshes)
        {
            if ((int)mesh.ReachType != 1 || (int)mesh.FlagsReach != 0)
                throw new InvalidDataException("Expected fixed rigid Reach scenery mesh");
            mesh.Type = Enum.Parse<TagTool.Geometry.VertexType>("Rigid");
            mesh.Flags = 0;
            foreach (var part in mesh.Parts)
            {
                var flags = (int)part.FlagsReach;
                if (flags != 0 && flags != 256 && flags != 384)
                    throw new InvalidDataException("Unreviewed Reach scenery part flags");
                if (flags != 0 && (int)part.TypeNew != 4)
                    throw new InvalidDataException("Reach transparency disagrees with part type");
                // IsTransparent/CannotSinglePassRender are Reach renderer state;
                // H3 uses the preserved transparent part type and its shader.
                part.FlagsNew = 0;
            }
        }
        foreach (var block in geometry.UserData)
        {
            if (block.DataType != 0 || block.DataCount != 1 || block.DataSize != 20 || block.Data.Length != 20)
                throw new InvalidDataException("Unreviewed Reach render user data");
            for (int i = 0; i < 20; i += 4) Array.Reverse(block.Data, i, 4);
        }
        return Serialize(model);
    }

    public static object ConvertModel(Model model)
    {
        if (model.OmahaDamageInfo.MaximumVitality != 0 || model.OmahaDamageInfo.DamageSections.Count != 0 ||
            model.OmahaDamageInfo.DamageConstraints.Count != 0 || model.Nodes.Count < 1 || model.Nodes.Count > 255 ||
            model.Animation != null)
            throw new InvalidDataException("Expected non-destructible rigid Reach architecture model");
        model.InstanceDisappearDistance = model.InstanceDisappearDistanceReach;
        return Serialize(model);
    }

    static object Serialize(object model)
    {
        using var output = new MemoryStream();
        using var writer = new EndianWriter(output, EndianFormat.BigEndian);
        var context = new RelocationContext(writer);
        new TagSerializer(CacheVersion.Halo3Retail, CachePlatform.Original, EndianFormat.BigEndian)
            .Serialize(context, model);
        return new { data = System.Convert.ToBase64String(output.ToArray()),
            root = context.Inner.MainStructOffset, pointers = context.Inner.PointerOffsets,
            strings = context.Strings, tags = context.Tags };
    }
}

// Keep the established serializer's field layouts/alignment while recording
// only the identifiers the retail serializer actually emits. Python resolves
// these against the destination cache before publishing any bytes.
class RelocationContext : ISerializationContext
{
    public readonly DataSerializationContext Inner;
    public readonly List<object> Strings = new();
    public readonly List<object> Tags = new();
    public RelocationContext(EndianWriter writer) { Inner = new DataSerializationContext(writer); }
    public uint AddressToOffset(uint current, uint address) => Inner.AddressToOffset(current, address);
    public EndianReader BeginDeserialize(TagStructureInfo info) => throw new NotSupportedException();
    public void EndDeserialize(TagStructureInfo info, object value) => throw new NotSupportedException();
    public CachedTag GetTagByIndex(int index) => throw new NotSupportedException();
    public CachedTag GetTagByName(TagGroup group, string name) => throw new NotSupportedException();
    public void BeginSerialize(TagStructureInfo info) => Inner.BeginSerialize(info);
    public void EndSerialize(TagStructureInfo info, byte[] data, uint offset) => Inner.EndSerialize(info, data, offset);
    public IDataBlock CreateBlock() => new RelocationBlock(this, Inner.CreateBlock());
    public void AddResourceBlock(int count, CacheAddress address, IList block) => throw new NotSupportedException();

    class RelocationBlock : IDataBlock
    {
        readonly RelocationContext context;
        readonly IDataBlock inner;
        readonly List<(uint offset, uint value)> strings = new();
        readonly List<(uint offset, CachedTag tag, bool shortReference)> tags = new();
        public RelocationBlock(RelocationContext context, IDataBlock inner)
        {
            this.context = context;
            this.inner = inner;
            // TagSerializer sets endianness on the root block only. The generic
            // context otherwise creates LITTLE-endian child blocks, even when
            // the outer serializer is configured for Xbox 360.
            inner.Writer.Format = EndianFormat.BigEndian;
        }
        public MemoryStream Stream => inner.Stream;
        public EndianWriter Writer => inner.Writer;
        public object PreSerialize(TagFieldAttribute info, object value)
        {
            if (value is StringId sid) strings.Add(((uint)Stream.Position, sid.Value));
            return inner.PreSerialize(info, value);
        }
        public void AddTagReference(CachedTag tag, bool isShort)
        {
            if (tag != null) tags.Add(((uint)Stream.Position, tag, isShort));
            inner.AddTagReference(tag, isShort);
        }
        public void WritePointer(uint offset, Type type) => inner.WritePointer(offset, type);
        public void SuggestAlignment(uint align) => inner.SuggestAlignment(align);
        public uint Finalize(Stream stream)
        {
            uint start = inner.Finalize(stream);
            foreach (var entry in strings)
                context.Strings.Add(new { offset = start + entry.offset, value = entry.value });
            foreach (var entry in tags)
                context.Tags.Add(new { offset = start + entry.offset,
                    datum = entry.tag.ID, group = entry.tag.Group.Tag.ToString(),
                    name = entry.tag.Name, shortReference = entry.shortReference });
            return start;
        }
    }
}
