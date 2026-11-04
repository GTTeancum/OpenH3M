// Read stock shader option vectors with the official H3 API. Never save tags.
using System;
using System.IO;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Web.Script.Serialization;
using Bungie;
using Bungie.Tags;

public class ShaderInventoryPlan { public string Kit; public List<string> Tags; public List<string> Options; public string Output; public bool IncludeFunctions; }
class ReadH3ShaderConfigurations
{
    static string Group(string path)
    {
        switch(Path.GetExtension(path))
        {
            case ".shader":return "rmsh*";
            case ".shader_terrain":return "rmtr*";
            case ".shader_halogram":return "rmhg*";
            case ".shader_water":return "rmw *";
            default:throw new ArgumentException("Unsupported stock shader group: "+path);
        }
    }
    static string Hash(string path)
    {
        using(var stream=File.OpenRead(path))using(var hash=SHA256.Create())
            return BitConverter.ToString(hash.ComputeHash(stream)).Replace("-","").ToLowerInvariant();
    }
    static int Main(string[] args)
    {
        if(args.Length!=1)throw new ArgumentException("Expected read-only stock inventory JSON");
        var json=new JavaScriptSerializer();json.MaxJsonLength=16*1024*1024;
        var plan=json.Deserialize<ShaderInventoryPlan>(File.ReadAllText(args[0]));
        Directory.SetCurrentDirectory(plan.Kit);
        ManagedBlamSystem.InitializeProject(InitializationType.TagsOnly,plan.Kit);
        var results=new List<object>();
        var tagsRoot=Path.GetFullPath(Path.Combine(plan.Kit,"tags"))+Path.DirectorySeparatorChar;
        if(plan.Options!=null)
        {
            foreach(var path in plan.Options)
            {
                var absolute=Path.GetFullPath(Path.Combine(tagsRoot,path));
                if(!absolute.StartsWith(tagsRoot,StringComparison.OrdinalIgnoreCase)||!path.EndsWith(".render_method_option"))
                    throw new ArgumentException("Expected native option tag: "+path);
                var before=Hash(absolute);
                using(var tag=new TagFile(TagPath.FromPathAndType(Path.ChangeExtension(path,null),"rmop")))
                {
                    var parameters=new List<object>();
                    foreach(var element in ((TagFieldBlock)tag.SelectField("Block:parameters")).Elements)
                    {
                        var fields=new Dictionary<string,object>();
                        foreach(var field in element.Fields)
                        {
                            var property=field.GetType().GetProperty("Data");
                            if(property!=null)fields[field.DisplayName]=property.GetValue(field,null);
                            var enumeration=field as TagFieldEnum;
                            if(enumeration!=null)fields[field.DisplayName]=enumeration.Items[enumeration.Value].EnumName;
                            var reference=field as TagFieldReference;
                            if(reference!=null)fields[field.DisplayName]=reference.Path==null?null:reference.Path.RelativePathWithExtension;
                            var id=field as TagFieldElementStringID;
                            if(id!=null)fields[field.DisplayName]=id.GetStringData();
                        }
                        parameters.Add(fields);
                    }
                    results.Add(new {path=path,sha256=before,parameters=parameters});
                }
                if(before!=Hash(absolute))throw new InvalidOperationException("Stock option tag changed");
            }
            File.WriteAllText(plan.Output,json.Serialize(results));
            Console.WriteLine("STOCK_OPTION_DEFAULTS_READ "+results.Count);
            return 0;
        }
        foreach(var path in plan.Tags)
        {
            var absolute=Path.GetFullPath(Path.Combine(tagsRoot,path));
            if(!absolute.StartsWith(tagsRoot,StringComparison.OrdinalIgnoreCase))
                throw new ArgumentException("Expected stock shader under kit tags: "+path);
            var before=Hash(absolute);
            using(var tag=new TagFile(TagPath.FromPathAndType(Path.ChangeExtension(path,null),Group(path))))
            {
                var options=new List<int>();
                foreach(var element in ((TagFieldBlock)tag.SelectField("Struct:render_method/Block:options")).Elements)
                    options.Add(checked((int)((TagFieldElementInteger)element.Fields[0]).Data));
                var parameters=new List<object>();
                foreach(var element in ((TagFieldBlock)tag.SelectField("Struct:render_method/Block:parameters")).Elements)
                {
                    var bitmap=((TagFieldReference)element.SelectField("bitmap")).Path;
                    var parameter=new Dictionary<string,object>();
                    parameter["name"]=((TagFieldElementStringID)element.SelectField("parameter name")).GetStringData();
                    parameter["type"]=((TagFieldEnum)element.SelectField("parameter type")).Value;
                    parameter["bitmap"]=bitmap==null?null:bitmap.RelativePathWithExtension;
                    if(plan.IncludeFunctions)
                    {
                        var functions=new List<object>();
                        foreach(var animation in ((TagFieldBlock)element.SelectField("animated parameters")).Elements)
                        {
                            var editor=((TagFieldCustomFunctionEditor)animation.SelectField("animation function")).Value;
                            var colors=new List<object>();
                            for(int i=0;i<editor.ColorCount;i++)
                            {
                                var color=editor.GetColor(i);
                                if((int)color.ColorMode==1)color=color.ToRgb();
                                colors.Add(new {red=color.Red,green=color.Green,blue=color.Blue});
                            }
                            functions.Add(new {type=((TagFieldEnum)animation.SelectField("type")).Value,
                                input=((TagFieldElementStringID)animation.SelectField("input name")).GetStringData(),
                                range=((TagFieldElementStringID)animation.SelectField("range name")).GetStringData(),
                                period=((TagFieldElementSingle)animation.SelectField("time period")).Data,
                                master_type=(int)editor.MasterType,color_graph_type=(int)editor.ColorGraphType,
                                is_ranged=editor.IsRanged,clamp_min=editor.ClampRangeMin,clamp_max=editor.ClampRangeMax,
                                colors=colors,data_base64=Convert.ToBase64String(((TagFieldData)animation.SelectField("Struct:function/Data:data")).GetData())});
                        }
                        parameter["functions"]=functions;
                    }
                    parameters.Add(parameter);
                }
                var material=path.EndsWith(".shader") ? ((TagFieldElementStringID)tag.SelectField("StringId:material name")).GetStringData() : null;
                results.Add(new {path=path,sha256=before,options=options,parameters=parameters,material=material});
            }
            if(before!=Hash(absolute))throw new InvalidOperationException("Stock tag changed: "+path);
        }
        File.WriteAllText(plan.Output,json.Serialize(results));
        Console.WriteLine("STOCK_SHADER_CONFIGURATIONS_READ "+results.Count);
        return 0;
    }
}
