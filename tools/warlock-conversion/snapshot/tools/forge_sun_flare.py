"""Retail representation of Forge World's authored multi-texture sun flare.

Retains every reflection and bitmap; modern curves become legacy endpoint ranges
and constant anisotropic scales become equal-area circular scales. These are
explicit POC approximations requiring native visual inspection.
"""
import copy
import math
import struct
import xml.etree.ElementTree as ET
from encode_bitmap import encode_bitmap_base
from tag_functions import convert_function
from tag_metadata import MetadataConverter

NAME = r'levels\multi\s3d_avalanche\sky\shaders\flare_sun_ava_01'


def import_flare(i, datum):
    s, b = i.source, i.builder
    root = s.tags[datum & 65535]['offset']
    rows = s.block(root + 0x44, 156)
    occlusion = s.unpack('i', root + 8)[0]
    if len(rows) != 18 or not 0 <= occlusion < len(rows):
        raise ValueError('Forge sun flare changed; review required')
    bitmap_root = bytearray(164)
    struct.pack_into('>H', bitmap_root, 4, 0x50)
    bitmap_owner, bitmap_address = i.registry.newtag('bitm', bitmap_root)
    images, records, hardware = {}, bytearray(), bytearray()
    approximations = []

    def curve(at):
        size = s.u(at); pointer = s.pointer(s.u(at+12))
        raw = bytes(s.data[pointer:pointer+size])
        convert_function(raw)  # Validate complete declared function layout.
        if len(raw) < 32 or raw[2] or raw[0] not in (1, 3, 8):
            raise ValueError('Unsupported sun-flare curve')
        low, high = struct.unpack_from('<2f', raw, 4)
        if not all(math.isfinite(v) and v >= 0 for v in (low, high)):
            raise ValueError('Invalid sun-flare curve range')
        if raw[0] == 1 and low != high:
            raise ValueError('Nonconstant flare scale')
        return (low, high), raw[0]

    def reflection(row):
        flags, pad, image_index, pad2 = s.unpack('4H', row)
        if pad or pad2 or any(s.unpack('6I', row+32)):
            raise ValueError('Unexpected sun-flare reflection fields')
        bitmap = s.u(row+20)
        if bitmap == 0xffffffff:
            raise ValueError('Sun flare needs explicit bitmap override')
        key = bitmap, image_index
        if key not in images:
            record, control, raw = encode_bitmap_base(i.materials.bitmaps, bitmap & 65535, image_index)
            rid = i.registry.add_resource(bitmap_owner, 'bitmap_texture_interop_resource',
                {'control': control, 'raw': raw, 'root': 52,
                 'fixups': [(12, 0x40000000), (52, 0x20000000)], 'interops': [(0x20000034, 2)]})
            images[key] = len(images)
            records.extend(record); hardware.extend(struct.pack('>II', rid, 0))
        radius, kind = curve(row+56)
        x, xkind = curve(row+76); y, ykind = curve(row+96)
        brightness, bkind = curve(row+116)
        if xkind != 1 or ykind != 1:
            raise ValueError('Animated anisotropic sun scale requires separate conversion')
        scale = math.sqrt(x[0]*y[0])
        approximations.append({'radius_curve': kind, 'brightness_curve': bkind,
                               'source_scale_xy': [x[0], y[0]], 'retail_scale': scale})
        return struct.pack('>HH11f', flags & ~4096, images[key],
                           *s.unpack('2f', row+24), *(v*scale for v in radius),
                           *brightness, s.unpack('f', row+148)[0],
                           *s.unpack('3f', row+136), s.unpack('f', row+152)[0])

    converted = [reflection(row) for row in rows]
    # H3 tests the first reflection. Move the authored occlusion element first;
    # retain every reflection, with the changed feedback order reported below.
    ordered = [converted[occlusion]] + [v for j,v in enumerate(converted) if j != occlusion]
    b.put(bitmap_address+96, 'III', len(images), b.alloc(records), 0)
    b.put(bitmap_address+140, 'III', len(images), b.alloc(hardware), 0)
    ss = copy.deepcopy(ET.parse(i.reference/'mcc/lens.xml').getroot())
    ds = ET.parse(i.reference/'plugins/lens.xml').getroot()
    ss.remove(next(f for f in ss if f.get('name') == 'Occlusion Reflection Index'))

    def special(at, source_schema, target_schema, path):
        if source_schema.get('name') == 'Reflections':
            return ordered[rows.index(at)]

    def data(path, cache, at):
        if not path.endswith('/Function'):
            raise ValueError('Unsupported sun-flare animation data')
        size=cache.u(at); pointer=cache.pointer(cache.u(at+12))
        return convert_function(bytes(cache.data[pointer:pointer+size]))

    converter = MetadataConverter(s, b, i.source_strings, i.target_strings,
                                  i.import_tag, data_reference=data, special_block=special)
    payload = bytearray(converter.convert(root, ss, ds, 'forge-lens:'+NAME))
    payload[32:48] = b'bitm' + bytes(8) + struct.pack('>I', bitmap_owner)
    owner, _ = i.registry.newtag('lens', payload)
    i.resolved['lens', NAME] = 'lens', owner
    i.added.append({'source': NAME, 'group': 'lens', 'datum': hex(owner),
                    'reflection_count': len(rows), 'bitmap_images': len(images),
                    'approximation': True, 'native_visuals_verified': False,
                    'differences': ['Curves reduced to endpoint ranges',
                                    'Anisotropic scales use equal-area circular scale',
                                    'Authored occlusion reflection moved first; feedback order changes'],
                    'reflection_conversion': approximations})
    return 'lens', owner
