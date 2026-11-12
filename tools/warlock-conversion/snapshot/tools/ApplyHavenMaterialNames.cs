// Assign existing H3 physical-material names through the official native API.
// This changes fresh shader tags only; it does not create global materials.
using System;
using System.IO;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using Bungie;
using Bungie.Tags;

public class MaterialNamesPlan { public string Kit; public string Output; public List<MaterialNamesTag> Tags; }
public class MaterialNamesTag { public string Path; public Dictionary<string,string> Fields; }
class ApplyHavenMaterialNames
{
    static string Group(string path)
    {
        switch(Path.GetExtension(path))
        {
            case ".shader":return "rmsh*";
            case ".shader_terrain":return "rmtr*";
            case ".shader_foliage":return "rmfl*";
            default:throw new ArgumentException("Unsupported shader type: "+path);
        }
    }
    static int Main(string[] args)
    {
        if(args.Length!=1 && !(args.Length==2 && args[1]=="--apply"))throw new ArgumentException("Expected plan and optional --apply");
        bool apply=args.Length==2;
        var json=new JavaScriptSerializer();
        var plan=json.Deserialize<MaterialNamesPlan>(File.ReadAllText(args[0]));
        Directory.SetCurrentDirectory(plan.Kit);
        ManagedBlamSystem.InitializeProject(InitializationType.TagsOnly,plan.Kit);
        var names=new HashSet<string>();
        using(var globals=new TagFile(TagPath.FromPathAndType(@"globals\globals","matg")))
        {
            var materials=(TagFieldBlock)globals.SelectField("Block:materials");
            if(materials==null)throw new InvalidOperationException("Missing native global materials block");
            foreach(var element in materials.Elements)
                names.Add(((TagFieldElementStringID)element.SelectField("name")).GetStringData());
        }
        var results=new List<object>();
        // Preflight every target and value before making any change.
        foreach(var target in plan.Tags)
        {
            if(!target.Path.StartsWith(@"levels\custom\haven_h4\shaders\") || target.Path.Contains(".."))
                throw new ArgumentException("Only fresh shaders may be edited");
            using(var tag=new TagFile(TagPath.FromPathAndType(Path.ChangeExtension(target.Path,null),Group(target.Path))))
                foreach(var field in target.Fields)
                {
                    if(!names.Contains(field.Value))throw new ArgumentException("Not a stock H3 global material: "+field.Value);
                    if(!(tag.SelectField("StringId:"+field.Key) is TagFieldElementStringID))throw new ArgumentException("No material field: "+field.Key);
                }
        }
        foreach(var target in plan.Tags)
        {
            var before=new Dictionary<string,string>();
            var after=new Dictionary<string,string>();
            var path=TagPath.FromPathAndType(Path.ChangeExtension(target.Path,null),Group(target.Path));
            using(var tag=new TagFile(path))
            {
                foreach(var field in target.Fields)
                {
                    var native=(TagFieldElementStringID)tag.SelectField("StringId:"+field.Key);
                    before[field.Key]=native.GetStringData();
                    if(apply)native.SetStringData(field.Value);
                }
                if(apply)tag.Save();
            }
            using(var tag=new TagFile(path))
                foreach(var field in target.Fields)
                {
                    after[field.Key]=((TagFieldElementStringID)tag.SelectField("StringId:"+field.Key)).GetStringData();
                    if(apply && after[field.Key]!=field.Value)throw new InvalidOperationException("Material readback mismatch");
                }
            results.Add(new {path=target.Path,before=before,after=after});
        }
        File.WriteAllText(plan.Output,json.Serialize(new {applied=apply,stock_material_names=names,tags=results}));
        Console.WriteLine("H3_MATERIAL_NAMES "+(apply?"APPLIED ":"INSPECTED ")+results.Count);
        return 0;
    }
}
