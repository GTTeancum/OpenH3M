// Read the official H3 model part controls; no tag writes.
using System;
using System.IO;
using Bungie;
using Bungie.Tags;
class InspectH3PropFlags
{
    static void Main(string[] args)
    {
        string kit=Path.Combine(Path.GetFullPath(args[0]),@"work\editing-kits\h3ek");
        Directory.SetCurrentDirectory(kit);ManagedBlamSystem.InitializeProject(InitializationType.TagsOnly,kit);
        using(var tag=new TagFile(TagPath.FromPathAndExtension(@"levels\custom\battle_canyon_fresh\sky\sky","render_model")))
        {
            var meshes=(TagFieldBlock)tag.SelectField("Struct:render geometry/Block:meshes");
            var parts=(TagFieldBlock)meshes.Elements[0].SelectField("parts");
            var flags=(TagFieldFlags)parts.Elements[0].SelectField("part flags");
            foreach(var item in flags.Items)Console.WriteLine(item.FlagName);
        }
    }
}
