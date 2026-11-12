// Supported H3 editor authoring; uses the established placement field setters.
using System;
using System.IO;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Web.Script.Serialization;
using Bungie;
using Bungie.Tags;
public class HavenLightFields { public Dictionary<string,string> Fields; }
public class HavenLightPlan
{
    public string Kit,Scenario,SourceTag,TargetTag,PreviousTag,SourceSha256,Output,Backup;
    public string TargetBsp,PreviousBsp;
    public int ExpectedCount;
    public List<HavenLightFields> Definitions,Instances;
}
class PrepareHavenLighting
{
    static string Hash(string p) { using(var h=SHA256.Create())using(var f=File.OpenRead(p))return BitConverter.ToString(h.ComputeHash(f)).Replace("-","").ToLowerInvariant(); }
    static string TagFilePath(string kit,string tag,string extension)
    {
        string root=Path.GetFullPath(Path.Combine(kit,"tags"))+Path.DirectorySeparatorChar;
        string result=Path.GetFullPath(Path.Combine(root,tag+"."+extension));
        if(!result.StartsWith(root,StringComparison.OrdinalIgnoreCase))throw new InvalidOperationException("Path leaves tag root");
        return result;
    }
    static void Fill(TagFieldBlock block,List<HavenLightFields> rows)
    {
        if(block.Elements.Count!=0)throw new InvalidOperationException("Expected no authored generic lights in source BSP");
        foreach(var row in rows)
        {
            var element=block.AddElement();
            foreach(var pair in row.Fields)PrepareH3BasicPlacements.Set(element.SelectField(pair.Key),pair.Value);
        }
    }
    static void Main(string[] args)
    {
        var plan=new JavaScriptSerializer().Deserialize<HavenLightPlan>(File.ReadAllText(args[0]));
        if((plan.TargetTag!=@"levels\custom\haven_h4\haven_lighting" && plan.TargetTag!=@"levels\custom\haven_h4\haven_lighting_with_sky" && plan.TargetTag!=@"levels\custom\haven_h4\haven_lighting_worldrender") || plan.Scenario!=@"levels\custom\haven_h4\haven_draft")throw new InvalidOperationException("Wrong target namespace");
        if(plan.TargetBsp!=null && (plan.TargetBsp!=@"levels\custom\haven_geometry_probe\haven_one_sided_joined_surfaces_opaque_draft_reflections_worldrender" || !File.Exists(TagFilePath(plan.Kit,plan.TargetBsp,"scenario_structure_bsp"))))throw new InvalidOperationException("Wrong or missing replacement BSP");
        string source=TagFilePath(plan.Kit,plan.SourceTag,"scenario_structure_lighting_info");
        string target=TagFilePath(plan.Kit,plan.TargetTag,"scenario_structure_lighting_info");
        if(Hash(source)!=plan.SourceSha256 || File.Exists(target) || File.Exists(plan.Backup))throw new InvalidOperationException("Source changed or authoring already attempted");
        if((plan.ExpectedCount!=194 && plan.ExpectedCount!=290) || plan.Definitions.Count!=plan.ExpectedCount || plan.Instances.Count!=plan.ExpectedCount)throw new InvalidOperationException("Incomplete source lights");
        Directory.SetCurrentDirectory(plan.Kit);ManagedBlamSystem.InitializeProject(InitializationType.TagsOnly,plan.Kit);
        File.Copy(source,target,false);
        int materials;
        using(var tag=new TagFile(TagPath.FromPathAndExtension(plan.TargetTag,"scenario_structure_lighting_info")))
        {
            materials=((TagFieldBlock)tag.SelectField("material info")).Elements.Count;
            Fill((TagFieldBlock)tag.SelectField("generic light definitions"),plan.Definitions);
            Fill((TagFieldBlock)tag.SelectField("generic light instances"),plan.Instances);
            tag.Save();
        }
        using(var tag=new TagFile(TagPath.FromPathAndExtension(plan.TargetTag,"scenario_structure_lighting_info")))
        {
            if(((TagFieldBlock)tag.SelectField("generic light definitions")).Elements.Count!=plan.ExpectedCount ||
                ((TagFieldBlock)tag.SelectField("generic light instances")).Elements.Count!=plan.ExpectedCount ||
                ((TagFieldBlock)tag.SelectField("material info")).Elements.Count!=materials)throw new InvalidOperationException("Saved lighting count differs");
        }
        using(var scenario=new TagFile(TagPath.FromPathAndExtension(plan.Scenario,"scenario")))
        {
            var bsps=(TagFieldBlock)scenario.SelectField("structure bsps");
            if(bsps.Elements.Count!=1)throw new InvalidOperationException("Wrong BSP count");
            var reference=(TagFieldReference)bsps.Elements[0].SelectField("structure lighting_info");
            if(reference.Path.RelativePathWithExtension!=plan.PreviousTag+".scenario_structure_lighting_info")throw new InvalidOperationException("Scenario lighting reference changed");
            if(plan.TargetBsp!=null)
            {
                var bsp=(TagFieldReference)bsps.Elements[0].SelectField("structure bsp");
                if(bsp.Path.RelativePathWithExtension!=plan.PreviousBsp+".scenario_structure_bsp")throw new InvalidOperationException("Scenario BSP reference changed");
                bsp.Path=TagPath.FromPathAndExtension(plan.TargetBsp,"scenario_structure_bsp");
            }
            File.Copy(TagFilePath(plan.Kit,plan.Scenario,"scenario"),plan.Backup,false);
            reference.Path=TagPath.FromPathAndExtension(plan.TargetTag,"scenario_structure_lighting_info");
            scenario.Save();
        }
        if(Hash(source)!=plan.SourceSha256)throw new InvalidOperationException("Source was modified");
        File.WriteAllText(plan.Output,new JavaScriptSerializer().Serialize(new { definitions=plan.ExpectedCount,instances=plan.ExpectedCount,material_records_retained=materials,source_sha256=Hash(source),target_sha256=Hash(target),rendering_verified=false }));
        Console.WriteLine("H4_LIGHTS_AUTHORED "+plan.ExpectedCount+" definitions and instances; original BSP lighting tag unchanged; draft rendering pending");
    }
}
