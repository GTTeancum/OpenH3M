// Diagnostic native-editor roundtrip, not a tag serializer or production shader.
using System;
using System.IO;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Web.Script.Serialization;
using Bungie;
using Bungie.Tags;

public class FunctionSample { public float input, range, value; }
public class FunctionProbe
{
    public string data_base64, source_type, target_type, source_input, range, master_type, color_type;
    public float time_period, clamp_min, clamp_max;
    public bool is_ranged, is_color;
    public int graph_count, color_count;
    public List<float[]> colors;
    public List<FunctionSample> native_scalar_samples;
    public List<string> origins;
}
public class FunctionProbePlan
{
    public string Kit, Donor, Target, Output;
    public List<FunctionProbe> Functions;
}
class VerifyH4FunctionsInH3
{
    static string Hash(string p)
    {
        using(var s=File.OpenRead(p))using(var h=SHA256.Create())
            return BitConverter.ToString(h.ComputeHash(s)).Replace("-","").ToLowerInvariant();
    }
    static void Require(bool condition,string message)
    { if(!condition)throw new InvalidOperationException(message); }
    static void Near(float expected,float actual,string field)
    { Require(Math.Abs(expected-actual)<=0.000001f,field+": "+expected+" != "+actual); }
    static string Confined(string root,string relative)
    {
        var p=Path.GetFullPath(Path.Combine(root,relative));
        Require(p.StartsWith(Path.GetFullPath(root)+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase),"Path outside tags");
        return p;
    }
    static int Main(string[] args)
    {
        Require(args.Length==1,"Expected plan JSON");
        var json=new JavaScriptSerializer();json.MaxJsonLength=16*1024*1024;
        var plan=json.Deserialize<FunctionProbePlan>(File.ReadAllText(args[0]));
        Require(plan.Functions.Count<=32,"Use bounded diagnostic batches of at most 32 functions");
        Require(plan.Target.StartsWith(@"levels\custom\haven_function_probe\",StringComparison.OrdinalIgnoreCase),"Diagnostic namespace only");
        var tags=Path.Combine(plan.Kit,"tags");
        var donor=Confined(tags,plan.Donor);var target=Confined(tags,plan.Target);
        var before=Hash(donor);
        Directory.CreateDirectory(Path.GetDirectoryName(target));
        File.Copy(donor,target,true);
        Directory.SetCurrentDirectory(plan.Kit);
        ManagedBlamSystem.InitializeProject(InitializationType.TagsOnly,plan.Kit);
        var path=TagPath.FromPathAndType(Path.ChangeExtension(plan.Target,null),"rmsh*");
        using(var tag=new TagFile(path))
        {
            var parameters=(TagFieldBlock)tag.SelectField("Struct:render_method/Block:parameters");
            parameters.RemoveAllElements();
            for(int i=0;i<plan.Functions.Count;i++)
            {
                var f=plan.Functions[i];
                Console.WriteLine("AUTHOR_FUNCTION "+i+" "+f.source_type+" "+f.master_type);
                var parameter=parameters.AddElement();
                ((TagFieldElementStringID)parameter.SelectField("parameter name")).SetStringData("probe_"+i);
                var parameterType=(TagFieldEnum)parameter.SelectField("parameter type");
                string wantedType=f.is_color?"color":"real";
                int parameterTypeIndex=-1;
                for(int t=0;t<parameterType.Items.Length;t++)
                {
                    if(i==0)Console.WriteLine("H3_PARAMETER_TYPE "+t+" "+parameterType.Items[t].EnumName);
                    if(parameterType.Items[t].EnumName==wantedType)parameterTypeIndex=t;
                }
                Require(parameterTypeIndex>=0,"No H3 parameter type: "+wantedType);
                parameterType.Value=parameterTypeIndex;
                var element=((TagFieldBlock)parameter.SelectField("animated parameters")).AddElement();
                var type=(TagFieldEnum)element.SelectField("type");
                if(i==0)for(int t=0;t<type.Items.Length;t++)Console.WriteLine("H3_ANIMATION_TYPE "+t+" "+type.Items[t].EnumName);
                int found=-1;
                for(int t=0;t<type.Items.Length;t++)if(type.Items[t].EnumName==f.target_type)found=t;
                Require(found>=0,"No native H3 animation type: "+f.target_type);type.Value=found;
                ((TagFieldElementStringID)element.SelectField("input name")).SetStringData(f.source_input);
                ((TagFieldElementStringID)element.SelectField("range name")).SetStringData(f.range);
                ((TagFieldElementSingle)element.SelectField("time period")).Data=f.time_period;
                ((TagFieldData)element.SelectField("Struct:function/Data:data")).SetData(Convert.FromBase64String(f.data_base64));
            }
            Console.WriteLine("SAVE_FUNCTION_PROBE "+plan.Functions.Count);
            tag.Save();
            Console.WriteLine("SAVED_FUNCTION_PROBE");
        }
        var results=new List<object>();
        using(var tag=new TagFile(path))
        {
            var parameters=(TagFieldBlock)tag.SelectField("Struct:render_method/Block:parameters");
            Require(parameters.Elements.Count==plan.Functions.Count,"Function count changed");
            for(int i=0;i<plan.Functions.Count;i++)
            {
                var f=plan.Functions[i];
                Console.WriteLine("READ_FUNCTION "+i+" "+f.source_type+" "+f.master_type);
                var parameterType=(TagFieldEnum)parameters.Elements[i].SelectField("parameter type");
                Require(parameterType.Items[parameterType.Value].EnumName==(f.is_color?"color":"real"),"Parameter type changed");
                var element=((TagFieldBlock)parameters.Elements[i].SelectField("animated parameters")).Elements[0];
                var type=(TagFieldEnum)element.SelectField("type");
                Require(type.Items[type.Value].EnumName==f.target_type,"Animation type changed");
                Require(((TagFieldElementStringID)element.SelectField("input name")).GetStringData()==f.source_input,"Input changed");
                Require(((TagFieldElementStringID)element.SelectField("range name")).GetStringData()==f.range,"Range changed");
                Near(f.time_period,((TagFieldElementSingle)element.SelectField("time period")).Data,"Period");
                Require(Convert.ToBase64String(((TagFieldData)element.SelectField("Struct:function/Data:data")).GetData())==f.data_base64,"Function bytes changed");
                var editor=((TagFieldCustomFunctionEditor)element.SelectField("animation function")).Value;
                Require(editor.MasterType.ToString()==f.master_type,"Master type changed");
                Require(editor.ColorGraphType.ToString()==f.color_type,"Color graph changed");
                Require(editor.IsRanged==f.is_ranged && editor.GraphCount==f.graph_count && editor.ColorCount==f.color_count,"Graph counts changed");
                if(f.is_color)
                    for(int c=0;c<f.color_count;c++)
                    {
                        var color=editor.GetColor(c);if((int)color.ColorMode==1)color=color.ToRgb();
                        Near(f.colors[c][0],color.Red,"Red");Near(f.colors[c][1],color.Green,"Green");Near(f.colors[c][2],color.Blue,"Blue");
                        // H3 GameColor exposes RGB. This boundary accepts only
                        // H4 color functions whose alpha is the identity value.
                        Near(1.0f,f.colors[c][3],"Source color alpha must be identity");
                    }
                else { Near(f.clamp_min,editor.ClampRangeMin,"Minimum");Near(f.clamp_max,editor.ClampRangeMax,"Maximum"); }
                float error=0;
                if(f.native_scalar_samples!=null)
                    foreach(var sample in f.native_scalar_samples)
                    {
                        float value=editor.Evaluate(sample.input,sample.range);
                        Near(sample.value,value,"Evaluated scalar");error=Math.Max(error,Math.Abs(sample.value-value));
                    }
                results.Add(new {index=i,origins=f.origins,master=f.master_type,source_type=f.source_type,target_type=f.target_type,
                    period=f.time_period,samples=f.native_scalar_samples==null?0:f.native_scalar_samples.Count,max_sample_error=error});
            }
        }
        Require(before==Hash(donor),"Stock donor changed");
        File.WriteAllText(plan.Output,json.Serialize(new {status="verified",functions=results,
            donor=plan.Donor,donor_sha256=before,donor_unchanged=true,target=plan.Target,target_sha256=Hash(target),
            limitation="Official editor compatibility only. Probe input names are diagnostic, not a production shader or runtime appearance acceptance."}));
        Console.WriteLine("H4_FUNCTION_H3_ROUNDTRIP_VERIFIED "+results.Count);
        return 0;
    }
}
