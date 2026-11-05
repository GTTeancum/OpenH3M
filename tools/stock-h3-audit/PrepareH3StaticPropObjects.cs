// Standard Guerilla model/crate authoring through the official H3 API.
using System;
using System.IO;
using System.Xml;
using System.Text.RegularExpressions;
using Bungie;
using Bungie.Tags;
class PrepareH3StaticPropObjects
{
    static string Value(XmlNode parent,string name) {return parent.SelectSingleNode("field[@name='"+name+"']").Attributes["value"].Value;}
    static void String(TagField field,string value) {if(!((TagFieldElement)field).SetStringData(value))throw new InvalidOperationException("Invalid value for "+field.FieldPath);}
    static void Main(string[] args)
    {
        string root=Path.GetFullPath(args[0]),kit=Path.Combine(root,@"work\editing-kits\h3ek"),output=Path.Combine(root,@"work\stock-h3-audit");
        Directory.SetCurrentDirectory(kit);ManagedBlamSystem.InitializeProject(InitializationType.TagsOnly,kit);
        foreach(string name in new[]{"cex_health_cabinet","ff_redbase_rocks02"})
        {
            string relative=@"levels\custom\battle_canyon_fresh\props\"+name+"\\"+name;
            foreach(string extension in new[]{"model","crate"})if(File.Exists(Path.Combine(kit,"tags",relative+"."+extension)))throw new InvalidOperationException("Inspect existing object before rerunning: "+name);
            foreach(string extension in new[]{"render_model","collision_model","physics_model"})if(!File.Exists(Path.Combine(kit,"tags",relative+"."+extension)))throw new FileNotFoundException(relative+"."+extension);
            var source=new XmlDocument();source.LoadXml(File.ReadAllText(Path.Combine(output,"original-prop-"+name+"-model.xml")).Replace("<unavailable>","&lt;unavailable&gt;"));
            var variant=source.SelectSingleNode("/tag/field[@name='variants']/following-sibling::element[1]");
            var region=variant.SelectSingleNode("field[@name='regions']/following-sibling::element[1]");
            var permutation=region.SelectSingleNode("field[@name='permutations']/following-sibling::element[1]");
            var material=source.SelectSingleNode("/tag/field[@name='model materials']/following-sibling::element[1]");
            string global=Value(material,"global material name");
            if(!Regex.IsMatch(File.ReadAllText(Path.Combine(output,"standoff-global-materials.txt")),@"\] Name: StringId = "+Regex.Escape(global)+@"\s*$",RegexOptions.Multiline))throw new InvalidOperationException("Verify stock global material "+global);
            if(Value(variant,"objects")!="0" || Value(permutation,"states")!="0" || Value(permutation,"flags")!="")throw new InvalidOperationException("Unexpected source variant behavior");
            using(var model=new TagFile())
            {
                model.New(TagPath.FromPathAndExtension(relative,"model"));
                foreach(string[] pair in new[]{new[]{"render model","render_model"},new[]{"collision model","collision_model"},new[]{"physics_model","physics_model"}})
                    ((TagFieldReference)model.SelectField(pair[0])).Path=TagPath.FromPathAndExtension(relative,pair[1]);
                var v=((TagFieldBlock)model.SelectField("variants")).AddElement();String(v.SelectField("name"),Value(variant,"name"));
                var r=((TagFieldBlock)v.SelectField("regions")).AddElement();String(r.SelectField("region name"),Value(region,"region name"));
                var p=((TagFieldBlock)r.SelectField("permutations")).AddElement();String(p.SelectField("permutation name"),Value(permutation,"permutation name"));String(p.SelectField("probability"),Value(permutation,"probability"));
                var m=((TagFieldBlock)model.SelectField("materials")).AddElement();String(m.SelectField("material name"),Value(material,"material name"));String(m.SelectField("global material name"),global);
                model.Save();
            }
            using(var crate=new TagFile())
            {
                crate.New(TagPath.FromPathAndExtension(relative,"crate"));
                ((TagFieldReference)crate.SelectField("Struct:object/Reference:model")).Path=TagPath.FromPathAndExtension(relative,"model");
                // Native fixed rigid bodies retain the source's static placement.
                // These objects are not added to the approved stock Forge palette.
                // No Reach-only Forge phasing or healing behavior is imported.
                crate.Save();
            }
            Console.WriteLine("STATIC_PROP_OBJECT_CREATED "+name+" material "+Value(material,"material name")+" -> "+global);
        }
    }
}
