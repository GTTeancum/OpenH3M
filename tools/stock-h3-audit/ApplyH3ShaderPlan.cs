// Automates official H3 ManagedBlam authoring operations; no tag serializer.
using System;
using System.IO;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using Bungie;
using Bungie.Tags;

public class ShaderPlan
{
    public string Kit;
    public string Donor;
    public string Target;
    public List<ParameterPlan> Parameters;
    public List<string> RemoveParameters;
}
public class ParameterPlan
{
    public string Name;
    public int Type;
    public string Bitmap;
    public float? Real;
    public int? Integer;
    public List<AnimationPlan> Animations;
}
public class AnimationPlan
{
    public int Type;
    public string TypeName;
    public string Input;
    public string Range;
    public float Period;
    public string DataBase64;
    public float? Constant;
}
class ApplyH3ShaderPlan
{
    static string Confined(string root, string relative)
    {
        var result=Path.GetFullPath(Path.Combine(root,relative));
        if (!result.StartsWith(Path.GetFullPath(root)+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("Path leaves root: "+relative);
        return result;
    }
    static int Main(string[] args)
    {
        if(args.Length<1 || args.Length>2 || (args.Length==2 && args[1]!="--verify" && args[1]!="--update"))
            throw new ArgumentException("Expected shader authoring plan JSON and optional --verify or --update");
        bool verifyOnly=args.Length==2 && args[1]=="--verify";
        bool updateExisting=args.Length==2 && args[1]=="--update";
        args[0]=Path.GetFullPath(args[0]);
        var plan=new JavaScriptSerializer().Deserialize<ShaderPlan>(File.ReadAllText(args[0]));
        var tags=Path.Combine(plan.Kit,"tags");
        if(!plan.Target.StartsWith(@"levels\custom\battle_canyon_fresh\shaders\",StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("Only fresh Battle Canyon authoring targets are allowed");
        if(!plan.Donor.EndsWith(".shader") || !plan.Target.EndsWith(".shader"))
            throw new InvalidOperationException("This authoring wrapper supports ordinary shader tags only");
        var original=File.ReadAllBytes(Confined(tags,plan.Donor));
        var destination=Confined(tags,plan.Target);
        Directory.CreateDirectory(Path.GetDirectoryName(destination));
        if(!verifyOnly && !updateExisting)File.Copy(Confined(tags,plan.Donor),destination,true);
        Directory.SetCurrentDirectory(plan.Kit);
        ManagedBlamSystem.InitializeProject(InitializationType.TagsOnly,plan.Kit);
        if(!verifyOnly)using(var tag=new TagFile(TagPath.FromPathAndType(Path.ChangeExtension(plan.Target,null),"rmsh*")))
        {
            var parameters=(TagFieldBlock)tag.SelectField("Struct:render_method/Block:parameters");
            if(plan.RemoveParameters!=null)
                for(int i=parameters.Elements.Count-1;i>=0;i--)
                    if(plan.RemoveParameters.Contains(((TagFieldElementStringID)parameters.Elements[i].SelectField("parameter name")).GetStringData()))
                        parameters.RemoveElement(i);
            foreach(var input in plan.Parameters)
            {
                TagElement parameter=null;
                foreach(var element in parameters.Elements)
                    if(((TagFieldElementStringID)element.SelectField("parameter name")).GetStringData()==input.Name)parameter=element;
                if(parameter==null)
                {
                    parameter=parameters.AddElement();
                    ((TagFieldElementStringID)parameter.SelectField("parameter name")).SetStringData(input.Name);
                    ((TagFieldEnum)parameter.SelectField("parameter type")).Value=input.Type;
                }
                if(((TagFieldEnum)parameter.SelectField("parameter type")).Value!=input.Type)
                    throw new InvalidOperationException("Parameter type differs: "+input.Name);
                if(input.Bitmap!=null)
                {
                    if(!File.Exists(Confined(tags,input.Bitmap)))throw new FileNotFoundException(input.Bitmap);
                    ((TagFieldReference)parameter.SelectField("bitmap")).Path=TagPath.FromPathAndType(Path.ChangeExtension(input.Bitmap,null),"bitm*");
                }
                if(input.Real.HasValue)((TagFieldElementSingle)parameter.SelectField("real")).Data=input.Real.Value;
                if(input.Integer.HasValue)
                {
                    // The display name contains '/', which SelectField treats
                    // as a path separator. Select the native field by its name.
                    TagFieldElementInteger integer=null;
                    foreach(var field in parameter.Fields)
                        if(field.DisplayName=="int/bool")integer=field as TagFieldElementInteger;
                    if(integer==null)throw new InvalidOperationException("Missing integer input field");
                    integer.Data=input.Integer.Value;
                }
                var animations=(TagFieldBlock)parameter.SelectField("animated parameters");
                animations.RemoveAllElements();
                foreach(var animation in input.Animations)
                {
                    var element=animations.AddElement();
                    var type=(TagFieldEnum)element.SelectField("type");
                    if(animation.TypeName!=null && type.Items[animation.Type].EnumName!=animation.TypeName)
                        throw new InvalidOperationException("Animation type differs: "+animation.TypeName);
                    type.Value=animation.Type;
                    ((TagFieldElementStringID)element.SelectField("input name")).SetStringData(animation.Input);
                    ((TagFieldElementStringID)element.SelectField("range name")).SetStringData(animation.Range);
                    ((TagFieldElementSingle)element.SelectField("time period")).Data=animation.Period;
                    if(animation.Constant.HasValue)
                    {
                        if(animation.Type!=0 || animation.DataBase64!=null)throw new ArgumentException("Expected scalar default value only");
                        var editor=((TagFieldCustomFunctionEditor)element.SelectField("animation function")).Value;
                        // Same native basic-function operation used by Foundry.
                        // The official editor creates the function data.
                        editor.MasterType=(FunctionEditorMasterType)0;
                        editor.IsRanged=false;
                        editor.ClampRangeMin=animation.Constant.Value;
                    }
                    else ((TagFieldData)element.SelectField("Struct:function/Data:data")).SetData(Convert.FromBase64String(animation.DataBase64));
                }
                Console.WriteLine("AUTHORED_INPUT "+input.Name+" "+input.Animations.Count);
            }
            tag.Save();
        }
        // Reopen through the native API: Tool's XML data export may omit long
        // function blobs. Never treat that omission as successful preservation.
        var verified=new List<object>();
        using(var tag=new TagFile(TagPath.FromPathAndType(Path.ChangeExtension(plan.Target,null),"rmsh*")))
        {
            var parameters=(TagFieldBlock)tag.SelectField("Struct:render_method/Block:parameters");
            if(plan.RemoveParameters!=null)
                foreach(var element in parameters.Elements)
                    if(plan.RemoveParameters.Contains(((TagFieldElementStringID)element.SelectField("parameter name")).GetStringData()))
                        throw new InvalidOperationException("Removed donor override is still present");
            foreach(var input in plan.Parameters)
            {
                TagElement parameter=null;
                foreach(var element in parameters.Elements)
                    if(((TagFieldElementStringID)element.SelectField("parameter name")).GetStringData()==input.Name)parameter=element;
                if(parameter==null)throw new InvalidOperationException("Saved parameter missing: "+input.Name);
                if(((TagFieldEnum)parameter.SelectField("parameter type")).Value!=input.Type)throw new InvalidOperationException("Saved parameter type differs");
                if(input.Real.HasValue && ((TagFieldElementSingle)parameter.SelectField("real")).Data!=input.Real.Value)throw new InvalidOperationException("Saved real differs");
                var animations=(TagFieldBlock)parameter.SelectField("animated parameters");
                if(animations.Elements.Count!=input.Animations.Count)throw new InvalidOperationException("Saved animation count differs: "+input.Name);
                var functions=new List<string>();
                var constants=new List<float?>();
                for(int i=0;i<input.Animations.Count;i++)
                {
                    var element=animations.Elements[i];
                    var expected=input.Animations[i];
                    if(((TagFieldEnum)element.SelectField("type")).Value!=expected.Type ||
                       ((TagFieldElementStringID)element.SelectField("input name")).GetStringData()!=expected.Input ||
                       ((TagFieldElementStringID)element.SelectField("range name")).GetStringData()!=expected.Range ||
                       ((TagFieldElementSingle)element.SelectField("time period")).Data!=expected.Period)
                        throw new InvalidOperationException("Saved animation controls differ: "+input.Name);
                    var actual=Convert.ToBase64String(((TagFieldData)element.SelectField("Struct:function/Data:data")).GetData());
                    if(expected.Constant.HasValue)
                    {
                        var editor=((TagFieldCustomFunctionEditor)element.SelectField("animation function")).Value;
                        if((int)editor.MasterType!=0 || editor.IsRanged || editor.ClampRangeMin!=expected.Constant.Value)
                            throw new InvalidOperationException("Saved native constant differs: "+input.Name);
                        constants.Add(editor.ClampRangeMin);
                    }
                    else
                    {
                        if(actual!=expected.DataBase64)throw new InvalidOperationException("Saved function differs: "+input.Name+" "+i+" bytes "+Convert.FromBase64String(actual).Length);
                        constants.Add(null);
                    }
                    functions.Add(actual);
                }
                verified.Add(new {name=input.Name,functions=functions,constant_values=constants});
            }
        }
        File.WriteAllText(args[0]+".readback.json",new JavaScriptSerializer().Serialize(verified));
        var after=File.ReadAllBytes(Confined(tags,plan.Donor));
        if(original.Length!=after.Length)throw new InvalidOperationException("Stock donor changed");
        for(int i=0;i<original.Length;i++)if(original[i]!=after[i])throw new InvalidOperationException("Stock donor changed");
        Console.WriteLine("H3_SHADER_PLAN_SAVED "+plan.Target);
        return 0;
    }
}
