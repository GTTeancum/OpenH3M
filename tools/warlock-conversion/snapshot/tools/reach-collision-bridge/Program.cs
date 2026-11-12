using System.Collections;
using System.Reflection;
using System.Runtime.Loader;
using System.Text.Json;
using TagTool.Cache;
using TagTool.Cache.Gen3;
using TagTool.Common;
using TagTool.Geometry.BspCollisionGeometry.Utils;
using TagTool.IO;
using TagTool.Serialization;
using TagTool.Tags;
using TagTool.Tags.Definitions;

// Read-only adapter to the installed TagTool collision-tree conversion API.
// Arguments: TagTool.dll, Reach cache, manifest JSON, output JSON.
class Program
{
    static void Main(string[] args)
    {
        if (args.Length != 4) throw new ArgumentException("Expected DLL, cache, manifest, output");
        var dllDirectory = Path.GetDirectoryName(Path.GetFullPath(args[0]));
        AssemblyLoadContext.Default.Resolving += (context, name) =>
        {
            foreach (var directory in new[] { dllDirectory, Path.Combine(dllDirectory, "Tools") })
            {
                var file = Path.Combine(directory, name.Name + ".dll");
                if (File.Exists(file)) return context.LoadFromAssemblyPath(file);
            }
            return null;
        };
        Run(args);
    }

    static object Plain(object value)
    {
        if (value == null) return null;
        var type = value.GetType();
        if (type.IsPrimitive || type.IsEnum || value is string) return value;
        if (value is byte[] bytes) return Convert.ToBase64String(bytes);
        if (value is IEnumerable list) return list.Cast<object>().Select(Plain).ToArray();
        var fields = type.GetFields(BindingFlags.Public | BindingFlags.Instance)
            .ToDictionary(f => f.Name, f => Plain(f.GetValue(value)));
        // Coordinates, packed node indices and StringId expose scalar properties.
        foreach (var property in type.GetProperties(BindingFlags.Public | BindingFlags.Instance))
            if (property.CanRead && property.GetIndexParameters().Length == 0 &&
                (property.PropertyType.IsPrimitive || property.PropertyType.IsEnum) &&
                !fields.ContainsKey(property.Name))
                fields[property.Name] = property.GetValue(value);
        return fields;
    }

    static void Run(string[] args)
    {
        using var manifest = JsonDocument.Parse(File.ReadAllText(args[2]));
        var magic = manifest.RootElement.GetProperty("magic").GetInt64();
        var output = new List<object>();
        var tags = new Dictionary<int, CachedTag>();
        if (manifest.RootElement.TryGetProperty("tags", out var sourceTags))
            foreach (var pair in sourceTags.EnumerateObject())
            {
                int index = int.Parse(pair.Name);
                var tag = pair.Value;
                var group = tag.GetProperty("group").GetString();
                tags[index] = new CachedTagGen3 { Index = index,
                    ID = ((uint)tag.GetProperty("salt").GetInt32() << 16) | (uint)index,
                    Name = tag.GetProperty("name").GetString(),
                    Group = new TagGroup(new Tag(group), group.StartsWith("rm") ? new Tag("rm  ") : Tag.Null) };
            }
        foreach (var entry in manifest.RootElement.GetProperty("collisions").EnumerateArray())
        {
            using var context = new ReadContext(args[1], magic, entry.GetProperty("offset").GetUInt32());
            var model = new TagDeserializer(CacheVersion.HaloReach, CachePlatform.MCC)
                .Deserialize<CollisionModel>(context);
            int expanded = 0;
            foreach (var region in model.Regions)
                foreach (var permutation in region.Permutations)
                    foreach (var bsp in permutation.Bsps)
                        if (bsp.Geometry.Bsp3dSupernodes.Count > 0)
                        {
                            var resize = new ResizeCollisionBSP();
                            var converter = new SupernodeToNodeConverter();
                            bsp.Geometry = resize.ShrinkCollisionBsp(
                                converter.Convert(resize.GrowCollisionBsp(bsp.Geometry)));
                            // The utility retains the obsolete source array for debugging.
                            bsp.Geometry.Bsp3dSupernodes.Clear();
                            expanded++;
                        }
            output.Add(new { name = entry.GetProperty("name").GetString(),
                index = entry.GetProperty("index").GetInt32(), expanded,
                definition = Plain(model) });
        }
        if (manifest.RootElement.TryGetProperty("renderModels", out var renderModels))
            foreach (var entry in renderModels.EnumerateArray())
            {
                using var context = new ReadContext(args[1], magic,
                    entry.GetProperty("offset").GetUInt32(), tags);
                var model = new TagDeserializer(CacheVersion.HaloReach, CachePlatform.MCC)
                    .Deserialize<RenderModel>(context);
                output.Add(new { name = entry.GetProperty("name").GetString(),
                    index = entry.GetProperty("index").GetInt32(), group = "mode",
                    resource = model.Geometry.Resource.Gen3ResourceID.Value,
                    geometry = Plain(model.Geometry),
                    nodes = Plain(model.Nodes),
                    metadata = RenderBridge.Convert(model) });
            }
        if (manifest.RootElement.TryGetProperty("models", out var models))
            foreach (var entry in models.EnumerateArray())
            {
                using var context = new ReadContext(args[1], magic,
                    entry.GetProperty("offset").GetUInt32(), tags);
                var model = new TagDeserializer(CacheVersion.HaloReach, CachePlatform.MCC)
                    .Deserialize<Model>(context);
                output.Add(new { name = entry.GetProperty("name").GetString(),
                    index = entry.GetProperty("index").GetInt32(), group = "hlmt",
                    metadata = RenderBridge.ConvertModel(model) });
            }
        // Publish only after every requested collision model converted.
        File.WriteAllText(args[3], JsonSerializer.Serialize(output));
        Console.WriteLine($"Converted {output.Count} asset metadata records.");
    }
}

class ReadContext : ISerializationContext, IDisposable
{
    readonly EndianReader reader;
    readonly long magic;
    readonly uint start;
    readonly Dictionary<int, CachedTag> tags;
    public ReadContext(string path, long magic, uint start, Dictionary<int, CachedTag> tags = null)
    {
        this.magic = magic;
        this.start = start;
        this.tags = tags;
        reader = new EndianReader(File.OpenRead(path), EndianFormat.LittleEndian);
    }
    public uint AddressToOffset(uint current, uint address) =>
        checked((uint)((long)(int)address * 4 + 0x50000000 - magic));
    public EndianReader BeginDeserialize(TagStructureInfo info)
    { reader.BaseStream.Position = start; return reader; }
    public void EndDeserialize(TagStructureInfo info, object value) { }
    public CachedTag GetTagByIndex(int index)
    {
        if (index == -1) return null;
        if (tags == null || !tags.TryGetValue(index & 65535, out var tag) || tag.ID != (uint)index)
            throw new InvalidDataException("Invalid source tag reference");
        return tag;
    }
    public CachedTag GetTagByName(TagGroup group, string name) => throw new NotSupportedException();
    public void BeginSerialize(TagStructureInfo info) => throw new NotSupportedException();
    public void EndSerialize(TagStructureInfo info, byte[] data, uint offset) => throw new NotSupportedException();
    public IDataBlock CreateBlock() => throw new NotSupportedException();
    public void AddResourceBlock(int count, CacheAddress address, IList block) => throw new NotSupportedException();
    public void Dispose() => reader.Dispose();
}
