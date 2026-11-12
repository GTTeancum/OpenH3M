// Inventory official H3 instance collision fields. Never creates/saves tags.
using System;
using System.IO;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Web.Script.Serialization;
using Bungie;
using Bungie.Tags;

class ReadH3InstanceCollision
{
    static string Hash(string path)
    {
        using(var stream=File.OpenRead(path))
        using(var hash=SHA256.Create())
            return BitConverter.ToString(hash.ComputeHash(stream)).Replace("-","").ToLowerInvariant();
    }
    static int Integer(TagField field)
    {
        foreach(var name in new[]{"Data","Value"})
        {
            var property=field.GetType().GetProperty(name);
            if(property!=null)return Convert.ToInt32(property.GetValue(field,null));
        }
        throw new InvalidOperationException("No official numeric property: "+field.GetType().FullName);
    }
    static int Count(TagElement element,string name)
    {
        var block=element.SelectField(name) as TagFieldBlock;
        return block==null?-1:block.Elements.Count;
    }
    static Dictionary<string,bool> Flags(TagField field)
    {
        if(field==null)throw new InvalidOperationException("Missing qualified flags field");
        var flags=(TagFieldFlags)field;
        var result=new Dictionary<string,bool>();
        foreach(var item in flags.Items)result[item.FlagName]=flags.TestBit(item.FlagName);
        return result;
    }
    static int Main(string[] args)
    {
        if(args.Length!=3)throw new ArgumentException("Expected kit, JSON tag list, report");
        var kit=Path.GetFullPath(args[0]);
        Directory.SetCurrentDirectory(kit);
        var json=new JavaScriptSerializer{MaxJsonLength=Int32.MaxValue};
        var paths=json.Deserialize<string[]>(File.ReadAllText(args[1]));
        var reports=new List<object>();
        ManagedBlamSystem.InitializeProject(InitializationType.TagsOnly,kit);
        foreach(var relative in paths)
        {
            var path=Path.GetFullPath(Path.Combine(kit,"tags",relative+".scenario_structure_bsp"));
            if(!path.StartsWith(Path.Combine(kit,"tags")+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))
                throw new ArgumentException("Tag escapes kit");
            var before=Hash(path);
            var instances=new List<object>();
            var definitions=new List<object>();
            var materials=new List<object>();
            int clusterCount=0,portalCount=0;
            using(var tag=new TagFile(TagPath.FromPathAndType(relative,"sbsp*")))
            {
                clusterCount=((TagFieldBlock)tag.SelectField("clusters")).Elements.Count;
                portalCount=((TagFieldBlock)tag.SelectField("cluster portals")).Elements.Count;
                foreach(var material in ((TagFieldBlock)tag.SelectField("materials")).Elements)
                {
                    var references=new Dictionary<string,string>();
                    foreach(var field in material.Fields)
                    {
                        var reference=field as TagFieldReference;
                        if(reference!=null)references[field.DisplayName]=reference.Path==null?null:reference.Path.RelativePathWithExtension;
                    }
                    materials.Add(references);
                }
                var block=(TagFieldBlock)tag.SelectField("Struct:resource interface/Block:raw_resources/Struct:raw_items/Block:instanced geometries definitions");
                foreach(var definition in block.Elements)
                {
                    var surfaces=(TagFieldBlock)definition.SelectField("Struct:collision info/Block:surfaces");
                    if(surfaces==null)throw new InvalidOperationException("No collision-info surfaces: "+relative);
                    var counts=new Dictionary<string,int>();
                    foreach(var surface in surfaces.Elements)
                    {
                        foreach(var pair in Flags(surface.SelectField("flags")))
                            if(pair.Value)counts[pair.Key]=counts.ContainsKey(pair.Key)?counts[pair.Key]+1:1;
                    }
                    definitions.Add(new{surfaces=surfaces.Elements.Count,vertices=Count(definition,"Struct:collision info/Block:vertices"),
                        render_bsp=Count(definition,"render bsp"),mopp_codes=Count(definition,"mopp codes"),surface_flags=counts});
                }
                foreach(var instance in ((TagFieldBlock)tag.SelectField("instanced geometry instances")).Elements)
                {
                    instances.Add(new{name=((TagFieldElementStringID)instance.SelectField("name")).GetStringData(),
                        definition=Integer(instance.SelectField("instance definition")),
                        flags=Flags(instance.SelectField("flags")),physics=Count(instance,"bsp_physics")});
                }
            }
            if(Hash(path)!=before)throw new InvalidOperationException("Source changed: "+path);
            reports.Add(new{source=relative,sha256=before,source_unchanged=true,instances=instances,definitions=definitions,
                materials=materials,clusters=clusterCount,portals=portalCount});
            File.WriteAllText(args[2],json.Serialize(new{status="running",api="Official H3 ManagedBlam",tags=reports}));
            Console.WriteLine("H3_INSTANCE_COLLISION_READ "+relative+" instances="+instances.Count+" definitions="+definitions.Count);
        }
        File.WriteAllText(args[2],json.Serialize(new{status="complete",api="Official H3 ManagedBlam",tags=reports}));
        return 0;
    }
}
