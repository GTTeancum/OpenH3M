"""Translate fixed architectural lights to Halo 3's native light format.

Reach light fields follow TagTool Light.cs / ConvertLight. Cheap spherical
lights have no H3 tag class, so retain their constant color, intensity and
radius in a native sphere; their falloff curve is an explicit approximation.
"""
import struct
from tag_functions import convert_function


def serialize_light(cache, tag, builder, translate_string):
    at = tag['offset']
    out = bytearray(0x94)
    for p, group in ((0x60,b'bitm'),(0x84,b'lens')):
        struct.pack_into('>4sIII',out,p,group,0,0,0xffffffff)

    def function(source, target):
        inp,ran,modifier,pad,modinp = cache.unpack('IIHHI',at+source)
        if pad or modifier not in (0,1,2):
            raise ValueError('Unreviewed architectural light function')
        struct.pack_into('>IIHHI',out,target,translate_string(inp),
                         translate_string(ran),modifier,0,translate_string(modinp))
        ref = at+source+16
        length = cache.u(ref)
        address = cache.pointer(cache.u(ref+12))
        data = convert_function(bytes(cache.data[address:address+length]))
        struct.pack_into('>I',out,target+16,len(data))
        struct.pack_into('>I',out,target+28,builder.alloc(data))

    if tag['group']=='ligh':
        method,version,flags,kind = cache.unpack('BBHH',at)
        if method!=0 or version!=4 or flags & ~0x3ff or kind not in (0,1):
            raise ValueError('Unsupported Reach architectural light mode')
        if cache.u(at+0x8c)!=0xffffffff or cache.u(at+0xa8)!=0xffffffff:
            raise ValueError('Architectural light needs gel/lens conversion')
        struct.pack_into('>IH',out,0,flags,kind)
        struct.pack_into('>f',out,8,cache.unpack('f',at+8)[0])
        struct.pack_into('>3f',out,12,*cache.unpack('3f',at+0x14))
        function(0x38,0x18)
        function(0x5c,0x3c)
        diffusion = cache.unpack('f',at+0x28)[0] or 10.0
        struct.pack_into('>4f',out,0x70,diffusion,cache.unpack('f',at+0x24)[0],
                         0.0,cache.unpack('f',at+0x94)[0])
        out[0x80:0x82] = cache.data[at+0x98:at+0x9a]
    elif tag['group']=='gldf':
        if any(cache.unpack('4I',at+0x48)):
            raise ValueError('Animated cheap-light radius requires conversion')
        ref = at+0x58
        ptr = cache.pointer(cache.u(ref+12))
        raw = bytes(cache.data[ptr:ptr+cache.u(ref)])
        if len(raw)!=32 or raw[:4]!=bytes.fromhex('01340000'):
            raise ValueError('Nonconstant cheap-light radius')
        radius,upper = struct.unpack_from('<ff',raw,4)
        if radius!=upper or radius<=0:
            raise ValueError('Invalid cheap-light radius')
        struct.pack_into('>f',out,8,radius)
        function(0,0x18)
        function(0x24,0x3c)
        struct.pack_into('>3f',out,0x70,10.0,1.0,1.0)
    else:
        raise ValueError('Expected Reach light')
    return out
