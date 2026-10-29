using System.Reflection;
using System.Runtime.Loader;
using TagTool.Common;
using TagTool.Tags;
using TagTool.Geometry.BspCollisionGeometry;
class Program {
 static string toolDir="";
 static int Main(string[] args) {
  toolDir=Path.GetFullPath(args[0]);
  AssemblyLoadContext.Default.Resolving+=(ctx,name)=>{
   foreach(var dir in new[]{toolDir,Path.Combine(toolDir,"Tools")}) {
    var p=Path.Combine(dir,name.Name+".dll");if(File.Exists(p))return ctx.LoadFromAssemblyPath(p);
   }return null;
  };
  return Run(args[1],args[2]);
 }
 static int Run(string input,string output) {
  var b=new CollisionGeometry{Bsp3dNodes=new(),Planes=new(),Leaves=new(),Bsp2dReferences=new(),Bsp2dNodes=new(),Surfaces=new(),Edges=new(),Vertices=new()};
  using(var r=new BinaryReader(File.OpenRead(input))) {
   if(r.ReadUInt32()!=0x31434746)throw new Exception("bad input");
   int n=r.ReadInt32();for(int i=0;i<n;i++)b.Planes.Add(new Plane{Value=new RealPlane3d(r.ReadSingle(),r.ReadSingle(),r.ReadSingle(),r.ReadSingle())});
   n=r.ReadInt32();for(int i=0;i<n;i++)b.Surfaces.Add(new Surface{Plane=r.ReadUInt16(),FirstEdge=r.ReadUInt16(),MaterialIndex=r.ReadInt16(),BreakableSurfaceSet=r.ReadInt16(),BreakableSurfaceIndex=r.ReadInt16(),Flags=(SurfaceFlags)r.ReadByte(),BestPlaneCalculationVertex=r.ReadByte()});
   n=r.ReadInt32();for(int i=0;i<n;i++)b.Edges.Add(new Edge{StartVertex=r.ReadUInt16(),EndVertex=r.ReadUInt16(),ForwardEdge=r.ReadUInt16(),ReverseEdge=r.ReadUInt16(),LeftSurface=r.ReadUInt16(),RightSurface=r.ReadUInt16()});
   n=r.ReadInt32();for(int i=0;i<n;i++)b.Vertices.Add(new Vertex{Point=new RealPoint3d(r.ReadSingle(),r.ReadSingle(),r.ReadSingle()),FirstEdge=r.ReadUInt16(),Sink=r.ReadInt16()});
   if(r.BaseStream.Position!=r.BaseStream.Length)throw new Exception("input trailing bytes");
  }
  Console.WriteLine($"Rebuilding {b.Surfaces.Count} surfaces, {b.Planes.Count} planes");
  var type=Assembly.GetExecutingAssembly().GetType("TagTool.Geometry.BspCollisionGeometry.Utils.CollisionBSPBuilder",true);
  var builder=Activator.CreateInstance(type,true);object[] call={b,false};
  if(!(bool)type.GetMethod("generate_bsp").Invoke(builder,call))throw new Exception("builder rejected geometry");
  b=(CollisionGeometry)call[0];
  Console.WriteLine($"Built nodes={b.Bsp3dNodes.Count}, planes={b.Planes.Count}, leaves={b.Leaves.Count}, surfaces={b.Surfaces.Count}");
  if(b.Planes.Count>32768)throw new Exception("signed retail plane limit exceeded");
  using(var w=new BinaryWriter(File.Create(output))) {
   w.Write(0x31434746u);
   w.Write(b.Bsp3dNodes.Count);foreach(var x in b.Bsp3dNodes)w.Write(x.Value);
   w.Write(b.Planes.Count);foreach(var x in b.Planes){w.Write(x.Value.I);w.Write(x.Value.J);w.Write(x.Value.K);w.Write(x.Value.D);}
   w.Write(b.Leaves.Count);foreach(var x in b.Leaves){w.Write((byte)x.Flags);w.Write((byte)x.Flags2);w.Write(x.Bsp2dReferenceCount);w.Write(x.FirstBsp2dReference);}
   w.Write(b.Bsp2dReferences.Count);foreach(var x in b.Bsp2dReferences){w.Write(x.PlaneIndex);w.Write(x.Bsp2dNodeIndex);}
   w.Write(b.Bsp2dNodes.Count);foreach(var x in b.Bsp2dNodes){w.Write(x.Plane.I);w.Write(x.Plane.J);w.Write(x.Plane.D);w.Write(x.LeftChild);w.Write(x.RightChild);}
   w.Write(b.Surfaces.Count);foreach(var x in b.Surfaces){w.Write(x.Plane);w.Write(x.FirstEdge);w.Write(x.MaterialIndex);w.Write(x.BreakableSurfaceSet);w.Write(x.BreakableSurfaceIndex);w.Write((byte)x.Flags);w.Write(x.BestPlaneCalculationVertex);}
   w.Write(b.Edges.Count);foreach(var x in b.Edges){w.Write(x.StartVertex);w.Write(x.EndVertex);w.Write(x.ForwardEdge);w.Write(x.ReverseEdge);w.Write(x.LeftSurface);w.Write(x.RightSurface);}
   w.Write(b.Vertices.Count);foreach(var x in b.Vertices){w.Write(x.Point.X);w.Write(x.Point.Y);w.Write(x.Point.Z);w.Write(x.FirstEdge);w.Write(x.Sink);}
  }return 0;
 }
}
