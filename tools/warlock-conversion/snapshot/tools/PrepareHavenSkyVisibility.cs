// Author H3 cluster sky selection through the official tag API.
using System;
using System.IO;
using Bungie;
using Bungie.Tags;
class PrepareHavenSkyVisibility {
 static void Main(string[] args) {
  string root=Path.GetFullPath(args[0]),kit=Path.Combine(root,@"work\editing-kits\h3ek");
  string tags=Path.Combine(kit,"tags"),prefix=@"levels\custom\haven_h4\";
  string sc=prefix+"haven_skyview",bsp=prefix+"haven_sky";
  if(File.Exists(Path.Combine(tags,sc+".scenario")) || File.Exists(Path.Combine(tags,bsp+".scenario_structure_bsp")))throw new InvalidOperationException("Preserve existing checkpoint");
  File.Copy(Path.Combine(tags,prefix+"haven_preview.scenario"),Path.Combine(tags,sc+".scenario"));
  File.Copy(Path.Combine(tags,prefix+"haven.scenario_structure_bsp"),Path.Combine(tags,bsp+".scenario_structure_bsp"));
  Directory.SetCurrentDirectory(kit);ManagedBlamSystem.InitializeProject(InitializationType.TagsOnly,kit);
  using(var scenario=new TagFile(TagPath.FromPathAndExtension(sc,"scenario"))) {
   var skies=(TagFieldBlock)scenario.SelectField("skies");
   if(skies.Elements.Count!=1 || ((TagFieldReference)skies.Elements[0].SelectField("sky")).Path.RelativePathWithExtension!=prefix+@"sky\sky.scenery")throw new InvalidOperationException("Unexpected sky");
   var bsps=(TagFieldBlock)scenario.SelectField("structure bsps");
   if(bsps.Elements.Count!=1)throw new InvalidOperationException("Expected one BSP");
   ((TagFieldReference)bsps.Elements[0].SelectField("structure bsp")).Path=TagPath.FromPathAndExtension(bsp,"scenario_structure_bsp");
   scenario.Save();
  }
  using(var tag=new TagFile(TagPath.FromPathAndExtension(bsp,"scenario_structure_bsp"))) {
   var clusters=(TagFieldBlock)tag.SelectField("clusters");
   if(clusters.Elements.Count!=8)throw new InvalidOperationException("Unexpected cluster count");
   foreach(var e in clusters.Elements) {
    var sky=(TagFieldElementInteger)e.SelectField("scenario sky index");
    if(sky.Data!=-1)throw new InvalidOperationException("Expected unassigned sky");
    sky.Data=0;
   }
   tag.Save();
  }
  using(var tag=new TagFile(TagPath.FromPathAndExtension(bsp,"scenario_structure_bsp")))
   foreach(var e in ((TagFieldBlock)tag.SelectField("clusters")).Elements)
    if(((TagFieldElementInteger)e.SelectField("scenario sky index")).Data!=0)throw new InvalidOperationException("Saved sky mismatch");
  Console.WriteLine("HAVEN_SKY_VISIBILITY_AUTHORED: eight H3 clusters select the scenario's sole sky; original baked inputs preserved");
 }
}
