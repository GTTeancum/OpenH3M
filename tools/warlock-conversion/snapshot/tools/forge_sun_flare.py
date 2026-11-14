"""Retail representation of Forge World's authored multi-texture sun flare.

Retains every reflection and bitmap; modern curves become legacy endpoint ranges
and constant anisotropic scales become equal-area circular scales. These are
explicit POC approximations requiring native visual inspection.
"""
import copy
import hashlib
import math
import struct
import xml.etree.ElementTree as ET
from encode_bitmap import encode_bitmap_base
from tag_functions import convert_function
from tag_metadata import MetadataConverter

NAME = r'levels\multi\s3d_avalanche\sky\shaders\flare_sun_ava_01'
POWERHOUSE = r'levels\multi\s3d_powerhouse\sky_settlement\flare_sun_01'
POWERHOUSE_SECONDARY = r'levels\multi\s3d_powerhouse\sky_settlement\m30_settlement_sun_flare'
EXPECTED_REFLECTIONS = {NAME: 18, POWERHOUSE: 27, POWERHOUSE_SECONDARY: 2}


def encode_authored_image(source, tag, index):
    """Opt-in lossless color/BC flare chain, within audited native dimensions."""
    info = source.info(tag)[index]
    w, h, count, fmt = (info[k] for k in ('width', 'height', 'mips', 'format'))
    if (fmt not in (11, 14, 15, 16) or not 1 <= w <= 1024 or not 1 <= h <= 1024
            or not 1 <= count <= max(w, h).bit_length()
            or (count > 1 and (min(w, h) < 32 or w & (w-1) or h & (h-1)))):
        raise ValueError('Authored flare bitmap outside reviewed lossless format/dimension bounds')
    record, control, raw = encode_bitmap_base(source, tag, index,
        max_dimension=1024, preserve_color_mips=True, preserve_bc_mips=True)
    ow, oh = struct.unpack_from('>HH', record, 4)
    ofmt = struct.unpack_from('>H', record, 12)[0]
    if (ow, oh, record[20]+1, ofmt) != (w, h, count, fmt):
        raise ValueError('Authored flare bitmap dimensions/mips/format changed')
    return record, control, raw


def import_flare(i, datum, *, native_placement=False, expected_reflections=None,
                 preserve_authored_bitmap_chains=False):
    s, b = i.source, i.builder
    name = s.name(datum & 65535)
    root = s.tags[datum & 65535]['offset']
    rows = s.block(root + 0x44, 156)
    occlusion = s.unpack('i', root + 8)[0]
    expected = EXPECTED_REFLECTIONS.get(name) if expected_reflections is None else expected_reflections
    if len(rows) != expected or (not native_placement and not 0 <= occlusion < len(rows)):
        raise ValueError('Forge sun flare changed; review required')
    bitmap_root = bytearray(164)
    struct.pack_into('>H', bitmap_root, 4, 0x50)
    bitmap_owner, bitmap_address = i.registry.newtag('bitm', bitmap_root)
    images, records, hardware = {}, bytearray(), bytearray()
    approximations = []
    bitmap_preservation = []

    def curve(at):
        size = s.u(at); pointer = s.pointer(s.u(at+12))
        raw = bytes(s.data[pointer:pointer+size])
        convert_function(raw)  # Validate complete declared function layout.
        if len(raw) < 32 or raw[2] or raw[0] not in ((0, 1, 3, 8) if name == POWERHOUSE_SECONDARY else (1, 3, 8)):
            raise ValueError('Unsupported sun-flare curve')
        low, high = struct.unpack_from('<2f', raw, 4)
        if not all(math.isfinite(v) and v >= 0 for v in (low, high)):
            raise ValueError('Invalid sun-flare curve range')
        if raw[0] == 1 and low != high:
            raise ValueError('Nonconstant flare scale')
        return (low, high), raw[0]

    def reflection(row):
        flags, pad, image_index, pad2 = s.unpack('4H', row)
        if pad or pad2 or any(s.unpack('4I' if native_placement else '6I', row+(40 if native_placement else 32))):
            raise ValueError('Unexpected sun-flare reflection fields')
        bitmap = s.u(row+20)
        if bitmap == 0xffffffff and name == POWERHOUSE_SECONDARY:
            bitmap = s.u(root+0x30)
        if bitmap == 0xffffffff:
            raise ValueError('Sun flare needs explicit bitmap or root bitmap')
        key = bitmap, image_index
        if key not in images:
            encoder = encode_authored_image if preserve_authored_bitmap_chains else encode_bitmap_base
            record, control, raw = encoder(i.materials.bitmaps, bitmap & 65535, image_index)
            info = i.materials.bitmaps.info(bitmap & 65535)[image_index]
            bitmap_preservation.append({
                'source': s.name(bitmap & 65535), 'source_image_index': image_index,
                'source_dimensions': [info['width'], info['height']], 'source_mips': info['mips'],
                'source_format': info['format'],
                'source_payload_sha256': hashlib.sha256(i.materials.bitmaps.pixels(bitmap & 65535, image_index)).hexdigest(),
                'output_dimensions': list(struct.unpack_from('>HH', record, 4)),
                'output_mips': record[20]+1, 'output_format': struct.unpack_from('>H', record, 12)[0],
                'output_tiled_payload_sha256': hashlib.sha256(raw).hexdigest(),
                'authored_chain_requested': preserve_authored_bitmap_chains})
            rid = i.registry.add_resource(bitmap_owner, 'bitmap_texture_interop_resource',
                {'control': control, 'raw': raw, 'root': 52,
                 'fixups': [(12, 0x40000000), (52, 0x20000000)], 'interops': [(0x20000034, 2)]})
            images[key] = len(images)
            records.extend(record); hardware.extend(struct.pack('>II', rid, 0))
        radius, kind = curve(row+56)
        x, xkind = curve(row+76); y, ykind = curve(row+96)
        brightness, bkind = curve(row+116)
        animated_scale = name == POWERHOUSE_SECONDARY and xkind == ykind == 0 and x == y == (0.,1.)
        if (xkind != 1 or ykind != 1) and not animated_scale:
            raise ValueError('Animated anisotropic sun scale requires separate conversion')
        scales = [math.sqrt(x[k]*y[k]) for k in range(2)]
        scale = scales[1]
        approximations.append({'radius_curve': kind, 'brightness_curve': bkind,
                               'source_scale_xy': [x[0], y[0]], 'retail_scale': scale, 'scale_endpoints': scales, 'animated_scale_endpoint_approximation': animated_scale, 'source_axis_offset': s.unpack('f', row+28)[0], 'source_offset_bounds': s.unpack('2f', row+32)})
        if not native_placement and s.unpack('f', row+28)[0] != 0.0:
            raise ValueError('MCC sun-flare axis offset has no verified retail representation')
        # Original H3 reads bitmap index at +4 and rotation at +8.
        return struct.pack('>H2xH2x10f', flags & ~4096, images[key],
                           s.unpack('f', row+24)[0], *(v*scale for v,scale in zip(radius,scales)),
                           *brightness, s.unpack('f', row+148)[0],
                           *s.unpack('3f', row+136), s.unpack('f', row+152)[0])

    converted = [reflection(row) for row in rows]
    # H3 tests the first reflection. Native-placement mode retains source order.
    # Existing map conversions move their selected occlusion element first.
    ordered = converted if native_placement else [converted[occlusion]] + [v for j,v in enumerate(converted) if j != occlusion]
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
    payload = bytearray(converter.convert(root, ss, ds, 'forge-lens:'+name))
    payload[32:48] = b'bitm' + bytes(8) + struct.pack('>I', bitmap_owner)
    owner, _ = i.registry.newtag('lens', payload)
    i.resolved['lens', name] = 'lens', owner
    i.added.append({'source': name, 'group': 'lens', 'datum': hex(owner),
                    'reflection_count': len(rows), 'bitmap_images': len(images),
                    'preserve_authored_bitmap_chains': preserve_authored_bitmap_chains,
                    'bitmap_preservation': bitmap_preservation,
                    'approximation': True, 'native_visuals_verified': False,
                    'native_placement': native_placement, 'source_occlusion_index': occlusion,
                    'differences': ['Curves reduced to endpoint ranges',
                                    'Anisotropic scales use equal-area circular scale',
                                    ('Original H3 placement and first-reflection occlusion; source order retained' if native_placement else 'Authored occlusion reflection moved first; feedback order changes')],
                    'reflection_conversion': approximations})
    return 'lens', owner
