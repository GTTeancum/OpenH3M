// Short native authoring names for the official lightmapper; no binary edits.
using System;
using System.IO;
using Bungie;
using Bungie.Tags;
class PrepareHavenBake
{
    static void Main(string[] args)
    {
        string root=Path.GetFullPath(args[0]),kit=Path.Combine(root,@"work\editing-kits\h3ek");
        string backups=Path.Combine(root,@"work\halo4-to-h3\haven\draft-lighting-2026110502");
        string prefix=@"levels\custom\haven_h4\",tags=Path.Combine(kit,"tags");
        string bsp="haven_one_sided_joined_surfaces_opaque_draft_reflections_worldrender";
        string[] inputs={"haven_draft.scenario",bsp+".scenario_structure_bsp","haven_lighting_worldrender.scenario_structure_lighting_info"};
        string[] outputs={"haven_preview.scenario","haven.scenario_structure_bsp","haven.scenario_structure_lighting_info"};
        for(int i=0;i<inputs.Length;i++)
            if(!File.Exists(Path.Combine(backups,inputs[i])) || File.Exists(Path.Combine(tags,prefix+outputs[i])))throw new InvalidOperationException("Missing input or target already exists");
        for(int i=0;i<inputs.Length;i++)File.Copy(Path.Combine(backups,inputs[i]),Path.Combine(tags,prefix+outputs[i]),false);
        Directory.SetCurrentDirectory(kit);ManagedBlamSystem.InitializeProject(InitializationType.TagsOnly,kit);
        using(var scenario=new TagFile(TagPath.FromPathAndExtension(prefix+"haven_preview","scenario")))
        {
            var bsps=(TagFieldBlock)scenario.SelectField("structure bsps");
            if(bsps.Elements.Count!=1)throw new InvalidOperationException("Expected one BSP");
            ((TagFieldReference)bsps.Elements[0].SelectField("structure bsp")).Path=TagPath.FromPathAndExtension(prefix+"haven","scenario_structure_bsp");
            ((TagFieldReference)bsps.Elements[0].SelectField("structure lighting_info")).Path=TagPath.FromPathAndExtension(prefix+"haven","scenario_structure_lighting_info");
            scenario.Save();
        }
        using(var scenario=new TagFile(TagPath.FromPathAndExtension(prefix+"haven_preview","scenario")))
        {
            var savedBsp=((TagFieldBlock)scenario.SelectField("structure bsps")).Elements[0];
            if(((TagFieldReference)savedBsp.SelectField("structure bsp")).Path.RelativePathWithExtension!=prefix+"haven.scenario_structure_bsp" ||
                ((TagFieldReference)savedBsp.SelectField("structure lighting_info")).Path.RelativePathWithExtension!=prefix+"haven.scenario_structure_lighting_info")throw new InvalidOperationException("Saved reference mismatch");
        }
        Console.WriteLine("HAVEN_SHORT_BAKE_TAGS_AUTHORED: scenario haven_preview, BSP haven; source backups preserved");
    }
}
