// Preserve original shared motion settings through official H3 editor fields.
using System;
using System.IO;
using System.Xml;
using Bungie;
using Bungie.Tags;
class PrepareH3PropPhysics
{
    static void Main(string[] args)
    {
        string root=Path.GetFullPath(args[0]),kit=Path.Combine(root,@"work\editing-kits\h3ek"),output=Path.Combine(root,@"work\stock-h3-audit");
        Directory.SetCurrentDirectory(kit);ManagedBlamSystem.InitializeProject(InitializationType.TagsOnly,kit);
        foreach(string name in new[]{"frunner_wheel","cex_health_cabinet","ff_redbase_rocks02"})
        {
            var source=new XmlDocument();source.LoadXml(File.ReadAllText(Path.Combine(output,"original-prop-"+name+"-physics.xml")).Replace("<unavailable>","&lt;unavailable&gt;"));
            var body=source.SelectSingleNode("/tag/field[@name='rigid bodies']/following-sibling::element[1]");
            string motion=body.SelectSingleNode("field[@name='motion type']").Attributes["value"].Value;
            string relative=@"levels\custom\battle_canyon_fresh\props\"+name+"\\"+name;
            using(var tag=new TagFile(TagPath.FromPathAndExtension(relative,"physics_model")))
            {
                var bodies=(TagFieldBlock)tag.SelectField("rigid bodies");
                if(bodies.Elements.Count!=1)throw new InvalidOperationException("Expected one body");
                var field=(TagFieldEnum)bodies.Elements[0].SelectField("motion type");
                int target=-1;foreach(var item in field.Items)if(item.EnumName==motion)target=item.EnumIndex;
                if(target<0)throw new InvalidOperationException("Unsupported original motion type "+motion);
                if(field.Value!=target)
                {
                    string backup=Path.Combine(output,"h3-prop-"+name+"-before-motion.physics_model");
                    if(File.Exists(backup))throw new InvalidOperationException("Inspect previous motion edit before repeating");
                    File.Copy(Path.Combine(kit,"tags",relative+".physics_model"),backup);
                    field.Value=target;tag.Save();
                }
                Console.WriteLine("PROP_MOTION "+name+" "+motion);
            }
        }
    }
}
