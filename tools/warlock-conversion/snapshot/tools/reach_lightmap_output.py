"""Pack reference-converted Reach lighting into original H3 bitmap resources."""
import hashlib
import json
import math
import struct
from pathlib import Path
from encode_bitmap import encode_lightmap_pixels
from xbox_bitmap import untile_base


def pack_converted_lightmap(directory):
    directory = Path(directory).resolve()
    repo = Path(__file__).resolve().parents[4]
    if not directory.is_relative_to(repo):
        raise ValueError('Lightmap artifacts must remain in the repository')
    meta = json.loads((directory/'conversion.json').read_text(encoding='utf-8-sig'))
    scales = meta['max_l']
    if len(scales) != 5 or any(not math.isfinite(x) or x <= 0 for x in scales):
        raise ValueError('Invalid converted lightmap luminance scales')
    native = []
    for name, depth, key in (('linear-sh',8,'linear_sh'),('dominant-intensity',2,'intensity')):
        linear = (directory/(name+'.bc3')).read_bytes()
        digest = hashlib.sha256(linear).hexdigest()
        if len(linear) != meta[key+'_bytes'] or digest != meta[key+'_sha256'].lower():
            raise ValueError('Converted lightmap payload disagrees with build report')
        record, control, raw = encode_lightmap_pixels(linear,meta['width'],meta['height'],depth)
        stride = len(raw)//depth
        for i in range(depth):
            restored = untile_base(raw[i*stride:(i+1)*stride],meta['width'],meta['height'],16)
            size = len(linear)//depth
            if restored != linear[i*size:(i+1)*size]:
                raise ValueError('Native lightmap tiling changed compressed data')
        for suffix, data in (('record',record),('control',control),('raw',raw)):
            (directory/(name+'.'+suffix)).write_bytes(data)
        native.append(dict(name=name,layers=depth,tiled_bytes=len(raw),
            sha256=hashlib.sha256(raw).hexdigest(),all_layers_roundtrip=True))
    report = dict(width=meta['width'],height=meta['height'],coefficient_scales=scales+[0.0]*4,
                  resources=native,scope='Native texture resources; lighting tag/scenario integration still required')
    (directory/'native-resources.json').write_text(json.dumps(report,indent=2))
    # Only these exact, verified duplicate intermediates are removed.
    for name in ('linear-sh','dominant-intensity'):
        (directory/(name+'.bc3')).unlink()
    return report


def load_native_lightmap(directory):
    """Validate the complete output pair before mutating a cache builder.

    Native H3 coefficients occupy nine 24-byte LuminanceScale records at
    sLdT BSP+8. TagTool initializes only Scale; the other five floats are zero.
    References: ScenarioLightmapBspData and LightmapCache.ImportIntoLbsp.
    """
    directory = Path(directory)
    meta = json.loads((directory/'native-resources.json').read_text())
    scales = meta['coefficient_scales']
    if len(scales) != 9 or any(not math.isfinite(x) or x < 0 for x in scales):
        raise ValueError('Invalid native lightmap scale table')
    if any(x <= 0 for x in scales[:5]) or any(scales[5:]):
        raise ValueError('Expected four SH scales, one intensity scale, four unused scales')
    resources = []
    rows = meta['resources']
    if len(rows) != 2:
        raise ValueError('Expected coefficient and intensity resources')
    for row, name, layers in zip(rows, ('linear-sh','dominant-intensity'), (8,2)):
        if row['name'] != name or row['layers'] != layers:
            raise ValueError('Lightmap resource role/layers mismatch')
        record, control, raw = [(directory/(name+'.'+suffix)).read_bytes()
                                for suffix in ('record','control','raw')]
        if len(record) != 48 or len(control) != 64 or record[:4] != b'bitm':
            raise ValueError('Invalid native lightmap bitmap record/control')
        if len(raw) != row['tiled_bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('Native lightmap payload checksum mismatch')
        expected = (meta['width'],meta['height'],layers,0x0e,3,16,3)
        if struct.unpack_from('>HHBBHHH',record,4) != expected or record[20:22] != bytes(2):
            raise ValueError('Native lightmap image layout mismatch')
        if struct.unpack_from('>HHBBBBI',control,40) != (meta['width'],meta['height'],layers,1,3,0,0x1a200154):
            raise ValueError('Native lightmap GPU layout mismatch')
        if struct.unpack_from('>I',control)[0] != len(raw) or struct.unpack_from('>I',record,28)[0] != len(raw):
            raise ValueError('Native lightmap size mismatch')
        resources.append((record,control,raw))
    return b''.join(struct.pack('>6f',scale,0,0,0,0,0) for scale in scales), resources


def register_native_lightmap(materials, directory):
    """Use the shared bitmap allocator; return scale bytes and native datums.

    Caller must fail the enclosing import if an allocation fails. This does not
    synthesize Reach probe bindings or mark the containing lightmap complete.
    """
    scales, resources = load_native_lightmap(directory)
    return scales, tuple(materials.bitmap_resource(*resource) for resource in resources)


def install_native_lightmap_atlas(root, materials, directory):
    """Install atlas fields in an original H3 0x1B4-byte BSP lighting record.

Geometry, probe tables, per-vertex/cluster bindings and the header belong to
the enclosing importer. Preserve them exactly; this is not a complete Lbsp.
As with bitmap_resource, allocation failures require discarding the build.
"""
    if not isinstance(root, bytearray) or len(root) != 0x1b4:
        raise ValueError('Expected a mutable native BSP lighting record')
    if any(root[8:0x100]):
        raise ValueError('Native atlas fields are already populated')
    scales, datums = register_native_lightmap(materials, directory)
    if len(scales) != 216 or len(datums) != 2:
        raise ValueError('Invalid registered native atlas pair')
    root[8:0xe0] = scales
    for offset, datum in zip((0xe0, 0xf0), datums):
        struct.pack_into('>4sIII', root, offset, b'bitm', 0, 0, datum)
    return datums


def install_lightmap_header(cache, binding, root, native_structure_checksum):
    """Translate active Reach headers; placeholder BSPs require a separate path.

    ScenarioLightmapBspFlags defines bits0..4 for H3, bits6/8 only for Reach's
    pruned mappings/draw optimization. Native topology is rebuilt separately;
    those source build-state flags have no native encoding and are reported.
    """
    if not isinstance(root, bytearray) or len(root) != 0x1b4 or any(root[:8]):
        raise ValueError('Expected an empty native lighting header')
    if binding['lighting_placeholder']:
        raise ValueError('Placeholder lighting needs explicit BSP geometry handling')
    at = binding['lighting']['offset']
    flags, index, checksum = cache.unpack('HHI', at)
    if index != binding['bsp_index'] or checksum != cache.u(binding['bsp']['offset']+0x30):
        raise ValueError('Lighting header disagrees with its source BSP')
    if flags & ~(0x1f | 0x140):
        raise ValueError('Reach lightmap header flags need additional adaptation')
    if not 0 <= native_structure_checksum <= 0xffffffff:
        raise ValueError('Invalid destination structure checksum')
    struct.pack_into('>HHI',root,0,flags & 0x1f,index,native_structure_checksum)
    return dict(source_flags=flags,native_flags=flags & 0x1f,
                source_build_flags_not_encoded=flags & 0x140,
                source_checksum=checksum,native_checksum=native_structure_checksum)
