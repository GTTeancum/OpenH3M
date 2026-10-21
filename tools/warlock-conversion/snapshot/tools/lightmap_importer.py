"""Collapse MCC Lbsp lighting into retail sLdT and share rebuilt BSP geometry."""
import copy
import struct
from collections import Counter
import xml.etree.ElementTree as ET
from tag_metadata import MetadataConverter
from collision_physics import convert_packed_mopp
from encode_bitmap import encode_lightmap_array


def import_lightmap(importer, geometry_resource):
    if importer.failed:
        raise ValueError('Cannot import lighting into a failed graph')
    try:
        return _import(importer, geometry_resource)
    except Exception:
        importer.failed = True
        raise


def _import(i, geometry_resource):
    s, b = i.source, i.builder
    scenario = next(t['offset'] for t in s.tags.values() if t['group'] == 'scnr')
    schema = ET.parse(i.reference / 'mcc/scnr.xml').getroot()
    f = next(f for f in schema if f.get('name') == 'Lightmaps')
    datum = s.u(scenario + int(f.get('offset'), 0) + 12)

    def resolve(value, group):
        tag = s.tags.get(value & 65535)
        if tag is None or tag['salt'] != value >> 16 or tag['group'] != group:
            raise ValueError('Invalid lightmap tag binding')
        return tag['offset']

    root = resolve(datum, 'sLdT')
    resources = [geometry_resource] if isinstance(geometry_resource, int) else geometry_resource
    rows = s.block(root + 4, 16)
    if len(rows) != len(resources) or s.u(root + 16) or any(s.u(root + o) for o in (0, 64, 68, 72)):
        raise ValueError('Expected matching per-pixel BSP lightmaps and no extra root data')
    converted_bsps = []
    for bsp_index, (source_row, geometry_resource) in enumerate(zip(rows, resources)):
        lighting = resolve(s.u(source_row + 12), 'Lbsp')
        if s.unpack('h', lighting + 2)[0] != bsp_index:
            raise ValueError('Lightmap BSP index differs from scenario order')
        rid = geometry_resource & 65535
        if rid >= len(i.registry.resources) // 64 or struct.unpack_from('>H', i.registry.resources, rid * 64 + 16)[0] != geometry_resource >> 16:
            raise ValueError('Invalid rebuilt lightmap geometry resource')
        ss = ET.parse(i.reference / 'mcc/sLdT.xml').getroot()
        ls = ET.parse(i.reference / 'mcc/Lbsp.xml').getroot()
        ds = ET.parse(i.reference / 'plugins/sLdT.xml').getroot()
        target_bsp = next(f for f in ds if f.get('name') == "Lightmap BSP's")
        # Per-BSP probe tables are cached subsets of root tables. Validate before
        # omitting them; the MCC per-BSP airprobe mask is the all-BSP sentinel.
        for so, lo, stride in ((28, 436, 92), (40, 448, 80), (52, 460, 44)):
            def records(offset):
                result = []
                for row in s.block(offset, stride):
                    value = bytearray(s.data[row:row + stride])
                    if stride == 92:
                        mask = struct.unpack_from('<H', value, 16)[0]
                        if mask not in (0, 65535):
                            raise ValueError('Nondefault cached airprobe BSP mask')
                        value[16:18] = bytes(2)
                    result.append(bytes(value))
                return Counter(result)
            if records(lighting + lo) - records(root + so):
                raise ValueError('Per-BSP probes contain lighting absent from root probes')
        if any(s.u(lighting + o) for o in (472, 476, 480)):
            raise ValueError('Nonempty lightmap error data')
        converted_schema = copy.deepcopy(ls)
        for node in list(converted_schema):
            if node.get('offset') and int(node.get('offset'), 0) >= 436:
                converted_schema.remove(node)
        textures = {}
        for offset in (0xe0, 0xf0):
            value = s.u(lighting + offset + 12)
            resolve(value, 'bitm')
            record, control, raw = encode_lightmap_array(i.materials.bitmaps, value & 65535)
            textures[value] = ('bitm', i.materials.bitmap_resource(record, control, raw))

        def reference(value):
            if value not in textures:
                raise ValueError('Unexpected lightmap dependency')
            return textures[value]

        def data(path, cache, at):
            if '/User Data[' in path and path.endswith('/User Data'):
                kind, count, stride = cache.unpack('BBH', at - 4)
                size = cache.u(at)
                if (kind, count, stride, size) == (0, 1, 20, 20):
                    pointer = cache.pointer(cache.u(at + 12))
                    if pointer + size > len(cache.data):
                        raise ValueError('Lightmap PRT descriptor outside cache')
                    # Same five-word PRT descriptor used by render models.
                    return struct.pack('>5I', *cache.unpack('5I', pointer))
            if '/Per Mesh MOPP[' not in path or not path.endswith('/MOPP Code'):
                raise ValueError(f'{path}: unsupported opaque lightmap data')
            size = cache.u(at)
            pointer = cache.pointer(cache.u(at + 12))
            if pointer + size > len(cache.data):
                raise ValueError('Lightmap MOPP outside cache')
            return convert_packed_mopp(bytes(cache.data[pointer:pointer + size]))

        def resource(path, value):
            if path in ('sLdT:/Scenery Probes/Unique ID', 'sLdT:/Device Machine Probes/Unique ID'):
                # Scenario placement unique IDs are preserved by the placement
                # converter. These are object identifiers, not zone resources.
                return value
            if not path.endswith('/[zone] Asset Datum') or value != s.u(lighting + 0x1ac):
                raise ValueError('Unexpected lightmap resource')
            return geometry_resource

        converter = MetadataConverter(s, b, i.source_strings, i.target_strings,
                                      reference, data_reference=data, resource_reference=resource)
        bsp = converter.convert(lighting, converted_schema, target_bsp, 'Lbsp:source')
        converted_bsps.append(bsp)
    result = bytearray(88)
    struct.pack_into('>III', result, 4, len(converted_bsps), b.alloc(b''.join(converted_bsps)), 0)
    counts = {}
    for name in ('Airprobes', 'Scenery Probes', 'Device Machine Probes'):
        sf = copy.deepcopy(next(f for f in ss if f.get('name') == name))
        df = next(f for f in ds if f.get('name') == name)
        for node in sf:
            label = node.get('name', '').replace('Lightprobe Term Coefficient', 'Lightprobe Coefficient')
            for color, short in (('Red', 'R'), ('Green', 'G'), ('Blue', 'B')):
                label = label.replace('Dominant Light Intensity ' + color, 'Dominant Light Intensity ' + short)
            node.set('name', label)
        entries = s.block(root + int(sf.get('offset'), 0), int(sf.get('elementSize'), 0))
        payload = b''.join(converter.convert(row, sf, df, 'sLdT:/' + name) for row in entries)
        struct.pack_into('>III', result, int(df.get('offset'), 0), len(entries), b.alloc(payload) if payload else 0, 0)
        counts[name] = len(entries)
    owner, address = i.registry.newtag('sLdT', result)
    i.resolved['sLdT', s.name(datum & 65535)] = ('sLdT', owner)
    report = {'group': 'sLdT', 'datum': hex(owner), 'source': s.name(datum & 65535),
              'bsp_count': len(converted_bsps), 'probe_counts': counts, 'source_lightmap_arrays': True}
    i.added.append(report)
    return ('sLdT', owner), address, report
