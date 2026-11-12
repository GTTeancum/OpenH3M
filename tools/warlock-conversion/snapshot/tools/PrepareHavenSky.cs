// Connect the standard Tool-compiled sky through official editor fields.
using System;
using System.IO;
using Bungie;
using Bungie.Tags;

class PrepareHavenSky
{
    const string Scenario=@"levels\custom\haven_h4\haven_draft";
    const string Sky=@"levels\custom\haven_h4\sky\sky";
    static int Main(string[] args)
    {
        if(args.Length!=1)throw new ArgumentException("Expected repository root");
        string root=Path.GetFullPath(args[0]),kit=Path.Combine(root,@"work\editing-kits\h3ek");
        string tags=Path.Combine(kit,"tags"),output=Path.Combine(root,@"work\halo4-to-h3\haven\h3-authoring");
        string backup=Path.Combine(output,"scenario-before-sky-setup.scenario");
        if(File.Exists(backup))throw new InvalidOperationException("Sky setup already attempted; inspect checkpoint before rerunning");
        if(!File.Exists(Path.Combine(tags,Sky+".render_model")))throw new FileNotFoundException("Compile sky render model first");
        foreach(string extension in new[]{"model","scenery"})
            if(File.Exists(Path.Combine(tags,Sky+"."+extension)))throw new InvalidOperationException("Fresh sky tag already exists: "+extension);
        Directory.SetCurrentDirectory(kit);
        ManagedBlamSystem.InitializeProject(InitializationType.TagsOnly,kit);
        // Standoff's model has no variants, child objects, physics or animation.
        File.Copy(Path.Combine(tags,@"levels\dlc\bunkerworld\sky\sky_bunkerworld.model"),Path.Combine(tags,Sky+".model"));
        File.Copy(Path.Combine(tags,@"levels\dlc\bunkerworld\sky\bunkerworld.scenery"),Path.Combine(tags,Sky+".scenery"));
        using(var model=new TagFile(TagPath.FromPathAndExtension(Sky,"model")))
        {
            foreach(string field in new[]{"collision model","animation","physics_model","lod_render_model"})
                if(((TagFieldReference)model.SelectField(field)).Path!=null)throw new InvalidOperationException("Unexpected stock model dependency "+field);
            ((TagFieldReference)model.SelectField("render model")).Path=TagPath.FromPathAndExtension(Sky,"render_model");
            model.Save();
        }
        using(var scenery=new TagFile(TagPath.FromPathAndExtension(Sky,"scenery")))
        {
            ((TagFieldReference)scenery.SelectField("Struct:object/Reference:model")).Path=TagPath.FromPathAndExtension(Sky,"model");
            // This draft supplies imported H4 render geometry only; source sky
            // auxiliary systems remain separately tracked, not inherited from H3.
            // Do not retain the donor's missile sounds/contrail controllers.
            ((TagFieldBlock)scenery.SelectField("Struct:object/Block:attachments")).RemoveAllElements();
            ((TagFieldBlock)scenery.SelectField("Struct:object/Block:functions")).RemoveAllElements();
            ((TagFieldElementSingle)scenery.SelectField("Struct:object/Real:bounding radius")).Data=0;
            scenery.Save();
        }
        using(var scenario=new TagFile(TagPath.FromPathAndExtension(Scenario,"scenario")))
        {
            var skies=(TagFieldBlock)scenario.SelectField("skies");
            if(skies.Elements.Count!=0)throw new InvalidOperationException("Sky block is not empty");
            var sky=skies.AddElement();
            ((TagFieldReference)sky.SelectField("sky")).Path=TagPath.FromPathAndExtension(Sky,"scenery");
            dynamic flags=sky.SelectField("active on bsps");
            foreach(dynamic item in flags.Items)item.IsSet=true;
            var bsps=(TagFieldBlock)scenario.SelectField("structure bsps");
            if(bsps.Elements.Count!=1)throw new InvalidOperationException("Expected one BSP");
            ((dynamic)bsps.Elements[0].SelectField("default sky")).Value=0;
            File.Copy(Path.Combine(tags,Scenario+".scenario"),backup);
            scenario.Save();
        }
        Console.WriteLine("H3_SKY_CONNECTED original H4 render geometry; stock H3 sky container; no donor effects/attachments; BSP 0 sky 0");
        return 0;
    }
}
