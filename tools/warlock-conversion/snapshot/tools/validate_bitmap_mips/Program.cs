using System.Security.Cryptography;
using System.Text.Json;
using TagTool.Bitmaps;
using TagTool.Tags.Resources;

// Independent decoder from the pinned collision-builder dependency. No game
// code executes, and no files are written by this validation program.
var raw = File.ReadAllBytes(args[0]);
var definition = new BitmapTextureInteropDefinition {
    Width=short.Parse(args[1]), Height=short.Parse(args[2]), Depth=args.Length > 5 ? byte.Parse(args[5]) : (byte)1,
    MipmapCount=sbyte.Parse(args[3]), BitmapType=args.Length > 6 ? (BitmapType)int.Parse(args[6]) : BitmapType.Texture2D,
    HighResInSecondaryResource=0, D3DFormat=unchecked((int)Convert.ToUInt32(args[4], 16))
};
var hashes = new List<string>();
for (int level=0; level<definition.MipmapCount; level++) {
    var bytes = XboxBitmapUtils.GetXboxBitmapLevelData(raw, null, definition, level, args.Length > 7 ? int.Parse(args[7]) : 0, false, 0, null);
    hashes.Add(Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant());
}
Console.WriteLine(JsonSerializer.Serialize(hashes));
