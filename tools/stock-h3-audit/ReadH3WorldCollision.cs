// Read actual H3 collision through the official API; never saves any tag.
using System;
using System.IO;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Web.Script.Serialization;
using Bungie;
using Bungie.Tags;

class ReadH3WorldCollision
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
            var data=field.GetType().GetProperty("Data");
            if(data!=null)result[field.DisplayName]=data.GetValue(field,null);
            var flags=field as TagFieldFlags;
            if(flags!=null)
            {
                var bits=new Dictionary<string,bool>();
                foreach(var name in new[]{"two sided","invisible","climbable","breakable","invalid","conveyor","slip"})
                    bits[name]=flags.TestBit(name);
                result[field.DisplayName]=bits;
            }
            var reference=field as TagFieldReference;
            if(reference!=null)result[field.DisplayName]=reference.Path==null?null:reference.Path.RelativePathWithExtension;
        }
        return result;
    }
    static int Main(string[] args)
    {
        if(args.Length!=3)throw new ArgumentException("Expected kit, report, relative BSP path");
        var kit=Path.GetFullPath(args[0]);
        Directory.SetCurrentDirectory(kit);
        var source=Path.GetFullPath(Path.Combine(kit,"tags",args[2]+".scenario_structure_bsp"));
        if(!source.StartsWith(Path.Combine(kit,"tags")+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))throw new ArgumentException("BSP outside kit");
        var before=Hash(source);
        ManagedBlamSystem.InitializeProject(InitializationType.TagsOnly,kit);
        var geometry=new Dictionary<string,object>();
        var materials=new List<object>();
        using(var tag=new TagFile(TagPath.FromPathAndType(args[2],"sbsp*")))
        {
            foreach(var material in ((TagFieldBlock)tag.SelectField("collision materials")).Elements)materials.Add(Fields(material));
            foreach(var kind in new[]{"collision bsp","large collision bsp"})
            {
                var block=(TagFieldBlock)tag.SelectField("Struct:resource interface/Block:raw_resources/Struct:raw_items/Block:"+kind);
                var rows=new List<object>();
                foreach(var bsp in block.Elements)
                {
                    var row=new Dictionary<string,object>();
                    foreach(var name in new[]{"vertices","edges","surfaces","planes"})
                    {
                        var values=new List<object>();
                        foreach(var element in ((TagFieldBlock)bsp.SelectField(name)).Elements)values.Add(Fields(element));
                        row[name]=values;
                    }
                    rows.Add(row);
                }
                geometry[kind]=rows;
            }
        }
        if(Hash(source)!=before)throw new InvalidOperationException("Source tag changed");
        var json=new JavaScriptSerializer{MaxJsonLength=Int32.MaxValue};
        File.WriteAllText(args[1],json.Serialize(new{source=source,sha256=before,collision=geometry,materials=materials}));
        Console.WriteLine("H3_WORLD_COLLISION_READ_ONLY_COMPLETE");
        return 0;
    }
}
