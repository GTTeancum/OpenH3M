"""Serialize reviewed Reach part ranges to original H3 metadata.

Layout: retained TagTool Mesh.cs and original H3 mode.xml. Flags must be
translated by the caller; Reach bit positions are never copied implicitly.
Subpart lighting and mesh flags remain separate conversion responsibilities.
"""
import struct


def pack_part(source, native_flags, material_index=None):
    if len(source) != 24:
        raise ValueError('Reach part must be 24 bytes')
    material, sorting, first, count, subfirst, subcount, kind, specialized, flags, vertices, tessellation = struct.unpack('<hhIIhHbbHHH', source)
    if material_index is not None:
        material = material_index
    if specialized != 0 and not (specialized == 7 and kind == 5) and not (specialized == 6 and kind == 2 and native_flags&8):
        raise ValueError('Reach specialized render requires a dedicated adapter')
    if tessellation:
        raise ValueError('Reach tessellation requires a dedicated adapter')
    if not 0 <= kind <= 5:
        raise ValueError('Unsupported original H3 part type')
    if first > 65535 or count > 65535:
        raise ValueError('Part requires index-range splitting before serialization')
    if subfirst < 0 or not 0 <= native_flags <= 255:
        raise ValueError('Invalid native subpart start or flags')
    return struct.pack('>hhHHhHbBH', material, sorting, first, count,
                       subfirst, subcount, kind, native_flags, vertices)
