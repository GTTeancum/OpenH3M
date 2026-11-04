// Read stock H3 water geometry through the official API. Never saves a tag.
using System;
using System.IO;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Web.Script.Serialization;
using Bungie;
using Bungie.Tags;

class InspectH3WaterGeometry
{
    static string Hash(string path)
    {
        using(var stream=File.OpenRead(path))
        using(var sha=SHA256.Create())
            return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
    }
    static object Fields(TagElement element)
    {
        var result=new Dictionary<string,object>();
        foreach(var field in element.Fields)
        {
            var property=field.GetType().GetProperty("Data");
            if(property!=null)result[field.DisplayName]=property.GetValue(field,null);
            var enumeration=field as TagFieldEnum;
            if(enumeration!=null)result[field.DisplayName]=enumeration.Value;
            var block=field as TagFieldBlock;
            if(block!=null)result[field.DisplayName]=new {count=block.Elements.Count};
            var reference=field as TagFieldReference;
            if(reference!=null)result[field.DisplayName]=reference.Path==null?null:reference.Path.RelativePathWithExtension;
        }
        return result;
    }
    static int Main(string[] args)
    {
        if(args.Length<2 || args.Length>3)throw new ArgumentException("Expected repository-local kit, report and optional relative BSP path");
        var kit=Path.GetFullPath(args[0]);
        Directory.SetCurrentDirectory(kit);
        var name=args.Length==3?args[2]:@"levels\dlc\docks\docks";
        var source=Path.GetFullPath(Path.Combine(kit,"tags",name+".scenario_structure_bsp"));
        if(!source.StartsWith(Path.Combine(kit,"tags")+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))
            throw new ArgumentException("BSP must stay inside kit tags");
        var before=Hash(source);
        Console.WriteLine("H3_WATER_INITIALIZING");
        ManagedBlamSystem.InitializeProject(InitializationType.TagsOnly,kit);
        Console.WriteLine("H3_WATER_INITIALIZED");
        var rows=new List<object>();
        var materialScales=new List<object>();
        using(var tag=new TagFile(TagPath.FromPathAndType(name,"sbsp*")))
        {
            Console.WriteLine("H3_WATER_TAG_OPENED");
            foreach(var material in ((TagFieldBlock)tag.SelectField("materials")).Elements)
            {
                var properties=new List<object>();
                foreach(var property in ((TagFieldBlock)material.SelectField("properties")).Elements)
                    properties.Add(Fields(property));
                materialScales.Add(new {index=material.ElementIndex,fields=Fields(material),properties=properties});
            }
            var temporary=(TagFieldBlock)tag.SelectField("Struct:render geometry/Block:per mesh temporary");
            foreach(var mesh in temporary.Elements)
            {
                var water=(TagFieldBlock)mesh.SelectField("raw water data");
                if(water.Elements.Count==0)continue;
                var data=water.Elements[0];
                var vertices=(TagFieldBlock)mesh.SelectField("raw vertices");
                var rawVertices=new List<object>();
                foreach(var vertex in vertices.Elements)rawVertices.Add(Fields(vertex));
                var waterBlocks=new Dictionary<string,object>();
                foreach(var field in data.Fields)
                {
                    var block=field as TagFieldBlock;
                    if(block==null)continue;
                    var values=new List<object>();
                    foreach(var element in block.Elements)values.Add(Fields(element));
                    waterBlocks[field.DisplayName]=values;
                }
                rows.Add(new {mesh=mesh.ElementIndex,raw_vertices=rawVertices,water=waterBlocks});
                Console.WriteLine("H3_WATER_MESH "+mesh.ElementIndex+" vertices "+vertices.Elements.Count);
            }
        }
        if(Hash(source)!=before)throw new InvalidOperationException("Stock source changed");
        if(rows.Count==0)throw new InvalidOperationException("No water data found");
        var json=new JavaScriptSerializer {MaxJsonLength=Int32.MaxValue};
        File.WriteAllText(args[1],json.Serialize(new {source=source,sha256=before,meshes=rows,
            material_lightmap_scales=materialScales}));
        Console.WriteLine("H3_WATER_READ_ONLY_COMPLETE "+rows.Count);
        return 0;
    }
}
