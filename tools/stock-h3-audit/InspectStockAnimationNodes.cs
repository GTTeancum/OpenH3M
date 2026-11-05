// Inspect the stock dependencies named by Tool's cache-build errors; no writes.
using System;
using System.IO;
using Bungie;
using Bungie.Tags;
class InspectStockAnimationNodes
{
    static void Main(string[] args)
    {
        string kit=Path.Combine(Path.GetFullPath(args[0]),@"work\editing-kits\h3ek");
        Directory.SetCurrentDirectory(kit);ManagedBlamSystem.InitializeProject(InitializationType.TagsOnly,kit);
        foreach(string path in new[]{@"objects\equipment\gravlift_permanent\gravlift_permanent",@"objects\weapons\melee\gravity_hammer\gravity_hammer",@"objects\multi\powerups\powerup_red\powerup_red"})
        using(var model=new TagFile(TagPath.FromPathAndExtension(path,"model")))
        {
            Console.WriteLine("MODEL "+path);
            foreach(string field in new[]{"render model","animation"})
            {
                var reference=((TagFieldReference)model.SelectField(field)).Path;
                Console.WriteLine("DEPENDENCY "+field+" "+reference.RelativePathWithExtension);
                using(var tag=new TagFile(reference))
                foreach(var item in tag.Fields)
                {
                    var block=item as TagFieldBlock;
                    if(block==null)continue;
                    Console.WriteLine("BLOCK "+block.DisplayName+" "+block.Elements.Count);
                    if(block.DisplayName.IndexOf("node",StringComparison.OrdinalIgnoreCase)<0)continue;
                    foreach(var element in block.Elements)
                    foreach(var value in element.Fields)
                    {
                        var id=value as TagFieldElementStringID;
                        if(id!=null)Console.WriteLine("NODE "+element.ElementIndex+" "+id.DisplayName+" "+id.GetStringData());
                    }
                }
            }
        }
    }
}
