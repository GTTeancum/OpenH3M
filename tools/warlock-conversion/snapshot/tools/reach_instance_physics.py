"""Stage geometry-only Reach MCC instance physics as retail H3 wrappers.

Pinned TagTool PortingContextGen3.Bsp.cs rebuilds CMoppBvTreeShape (type 27,
MoppScale), retaining the geometry child. Its cached code size/info are not
native serialized fields. This does NOT resolve the associated MOPP resource
or make a complete instance; callers must finish those bindings separately.
Convex children must use the separate fixed-hull conversion, never this path.
"""
import math
import struct
import hashlib
from reach_bsp_collision_source import ReachBspCollisionSource


def geometry_physics(resource, instance, source_bsp_index=0):
    if not isinstance(source_bsp_index,int) or not 0<=source_bsp_index<=127:
        raise ValueError('Source BSP identity exceeds signed-byte storage')
    if instance['physics_count'] != 1:
        raise ValueError('Expected exactly one Reach physics wrapper')
    pointer = instance['physics_pointer']
    if pointer is None or pointer >> 29 != 1:
        raise ValueError('Reach physics wrapper must be resident')
    reader = ReachBspCollisionSource(resource)
    at = pointer & 0x1fffffff
    header = bytes(reader.read(pointer, 128))
    count, child = reader.block(at + 128, 112)
    if count != 1 or resource.unpack('I', at + 140)[0]:
        raise ValueError('Expected a geometry child without a convex child')
    if struct.unpack_from('<I', header, 24)[0] != 10:
        raise ValueError('Unexpected Reach MOPP shape type')
    if struct.unpack_from('<I', child, 24)[0] != 7:
        raise ValueError('Unexpected Reach geometry shape type')
    for offset in (0, 16, 32, 88, 96):
        if struct.unpack_from('<Q', child, offset)[0]:
            raise ValueError('Serialized Reach runtime pointer is nonzero')
    if bytes(child[40:44]) != b'\x00\x03\x00\x00':
        raise ValueError('Unsupported Reach collection flags/type')
    if struct.unpack_from('<I', child, 80)[0] != 0xffffffff:
        raise ValueError('Geometry child unexpectedly owns a model')
    bounds = struct.unpack_from('<8f', child, 48)
    bsp, kind, key = struct.unpack_from('<bBH', child, 104)
    scale = struct.unpack_from('<f', child, 108)[0]
    mopp_scale = struct.unpack_from('<f', header, 112)[0]
    if bsp != source_bsp_index or kind != 2 or key != instance['index']:
        raise ValueError('Geometry child does not identify its source instance')
    if not all(math.isfinite(v) for v in (*bounds, scale, mopp_scale)):
        raise ValueError('Nonfinite physics dimensions')
    if any(v < 0 for v in bounds[4:7]) or scale <= 0 or mopp_scale < 0:
        raise ValueError('Invalid physics dimensions')
    out = bytearray(112)
    struct.pack_into('>HH', out, 4, 0, 128)
    struct.pack_into('>I', out, 12, 2)
    struct.pack_into('>8f', out, 32, *bounds)
    struct.pack_into('>I', out, 64, 0xffffffff)
    struct.pack_into('>bBHf', out, 72, bsp, kind, key, scale)
    struct.pack_into('>HH', out, 84, 0, 128)
    struct.pack_into('>I', out, 92, 27)
    struct.pack_into('>f', out, 108, mopp_scale)
    return bytes(out), dict(source_mopp_header=header.hex(),
        source_code_size=struct.unpack_from('<I', header, 56)[0],
        source_code_info=list(struct.unpack_from('<4f', header, 64)),
        requires_mopp_binding_verification=True)


def bind_geometry_physics(resource, instance, source_collision, native_collision,
                          source_bsp_index=0, rebuilt_mopp=None):
    """Verify the definition MOPP used by a native instance's runtime lookup.

    H3 resolves BSP/instance -> placement definition -> resource MOPP at load.
    Do not write a host pointer into the serialized physics wrapper. Return the
    wrapper and evidence for that lookup; the caller must retain placement order.
    """
    from reach_physics import convert_tag_mopp
    wrapper,evidence=geometry_physics(resource,instance,source_bsp_index)
    reader=ReachBspCollisionSource(source_collision)
    definitions=reader.headers(source_collision.root+24,324)
    definition=instance['definition']
    if not 0<=definition<len(definitions):
        raise ValueError('Physics definition outside source collision resource')
    source_headers=reader.headers(definitions[definition]+236,96)
    if rebuilt_mopp is None:
        if len(source_headers)!=1:
            raise ValueError('Geometry physics needs exactly one definition MOPP')
        at=source_headers[0]
        size=source_collision.unpack('I',at+56)[0]
        info=bytes(source_collision.data[at+32:at+48])
        header=bytes.fromhex(evidence['source_mopp_header'])
        if struct.unpack_from('<I',header,56)[0]!=size or header[64:80]!=info:
            raise ValueError('Source instance cached MOPP disagrees with its definition')
        native_header,expected_code=convert_tag_mopp(bytes(source_collision.data[at:at+96]),reader.block(at+80,1)[1])
        expected_info=native_header[16:32]
    else:
        if source_headers or not source_collision.unpack('I',definitions[definition]+4)[0]&16:
            raise ValueError('Rebuilt physics would replace an existing/unreviewed MOPP')
        size=struct.unpack_from('<I',rebuilt_mopp,36)[0]
        expected_code=rebuilt_mopp[48:48+size]
        expected_info=struct.pack('>4I',*struct.unpack_from('<4I',rebuilt_mopp,16))
    control=native_collision['control'];fix=dict(native_collision['fixups'])
    def resolve(pointer,resident):
        address=fix[pointer]
        if address>>29!=(1 if resident else 2):
            raise ValueError('Unexpected native physics resource segment')
        return address&0x1fffffff
    root=native_collision['root']
    if struct.unpack_from('>I',control,root+12)[0]!=len(definitions):
        raise ValueError('Native collision definition order/count changed')
    at=resolve(root+16,True)+definition*184
    if struct.unpack_from('>I',control,at+128)[0]!=1:
        raise ValueError('Native instance definition lacks exactly one MOPP')
    mopp=resolve(at+132,True)
    code_at=resolve(mopp+52,False)
    code_size=struct.unpack_from('>I',control,mopp+48)[0]
    if code_size!=len(expected_code) or native_collision['raw'][code_at:code_at+code_size]!=expected_code:
        raise ValueError('Native instance resolves to the wrong MOPP code')
    if control[mopp+16:mopp+32]!=expected_info:
        raise ValueError('Native MOPP quantization info differs from its compiled code')
    return wrapper,dict(bsp_index=source_bsp_index,instance=instance['index'],definition=definition,
        code_bytes=code_size,code_sha256=hashlib.sha256(expected_code).hexdigest(),
        rebuilt=rebuilt_mopp is not None,requires_mopp_binding_verification=False,
        requires_placement_order_preservation=True,runtime_verified=False)
