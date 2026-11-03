Native RGBA16 cloud texture support

Sky Bridge sly_clouds_r_01 is 256x256 A16B16G16R16 with nine authored mip levels (699048 source bytes). Added format28 to the existing native tiled bitmap and mip-chain encoders, preserving 16-bit unsigned-normalized RGBA, identity channel swizzle, 8-in-16 endian order and source curve3. GPU format 0x1a20015a matches the installed Xbox 360 SDK d3d9types.h D3DFMT_A16B16G16R16 definition: format26, endian1, tiled, unsigned fraction, ABGR identity. No conversion to 8-bit channels.

The complete source texture was encoded to704512 bytes, all nine levels recovered exactly with the original SHA256, and no texel addresses overlap. This verifies storage conversion; rendered cloud appearance still belongs to the single native launch test.

Source: Sky Bridge, Halo Online; General Heed / Priception, Halo Online Map Pack For Halo3: https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190. This project supplies Xbox360/OpenH3M adaptation.
