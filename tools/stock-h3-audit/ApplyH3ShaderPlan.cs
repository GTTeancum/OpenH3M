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
        if(args.Length!=1)throw new ArgumentException("Expected shader authoring plan JSON");
        var plan=new JavaScriptSerializer().Deserialize<ShaderPlan>(File.ReadAllText(args[0]));
        var tags=Path.Combine(plan.Kit,"tags");
        if(!plan.Target.StartsWith(@"levels\custom\battle_canyon_fresh\shaders\",StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("Only fresh Battle Canyon authoring targets are allowed");
        if(!plan.Donor.EndsWith(".shader") || !plan.Target.EndsWith(".shader"))
            throw new InvalidOperationException("This authoring wrapper supports ordinary shader tags only");
        var original=File.ReadAllBytes(Confined(tags,plan.Donor));
        var destination=Confined(tags,plan.Target);
        Directory.CreateDirectory(Path.GetDirectoryName(destination));
        File.Copy(Confined(tags,plan.Donor),destination,true);
        Directory.SetCurrentDirectory(plan.Kit);
        ManagedBlamSystem.InitializeProject(InitializationType.TagsOnly,plan.Kit);
        using(var tag=new TagFile(TagPath.FromPathAndType(Path.ChangeExtension(plan.Target,null),"rmsh*")))
        {
            var parameters=(TagFieldBlock)tag.SelectField("Struct:render_method/Block:parameters");
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
                if(input.Integer.HasValue)((TagFieldElementInteger)parameter.SelectField("int/bool")).Data=input.Integer.Value;
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
                    ((TagFieldData)element.SelectField("Struct:function/Data:data")).SetData(Convert.FromBase64String(animation.DataBase64));
                }
                Console.WriteLine("AUTHORED_INPUT "+input.Name+" "+input.Animations.Count);
            }
            tag.Save();
        }
        var after=File.ReadAllBytes(Confined(tags,plan.Donor));
        if(original.Length!=after.Length)throw new InvalidOperationException("Stock donor changed");
        for(int i=0;i<original.Length;i++)if(original[i]!=after[i])throw new InvalidOperationException("Stock donor changed");
        Console.WriteLine("H3_SHADER_PLAN_SAVED "+plan.Target);
        return 0;
    }
}
