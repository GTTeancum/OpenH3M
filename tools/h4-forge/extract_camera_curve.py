"""Extract original H4 Forge pitch-to-vertical camera curve; no game execution."""
import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / 'work/h4-forge-research'
SOURCE = RESEARCH / 'disc2-assets/ca_forge_ravine.map'

with SOURCE.open('rb') as source:
    header = source.read(0x500)
    u = lambda offset: struct.unpack_from('>I', header, offset)[0]
    start = (u(0x484) + u(0x49c)) & 0xffffffff
    base = u(0x2f8)
    size = source.seek(0, 2)

    def read(pointer, length):
        offset = pointer - base + start
        if offset < 0 or offset + length > size:
            raise ValueError('Tag pointer outside source cache')
        source.seek(offset)
        data = source.read(length)
        if len(data) != length:
            raise ValueError('Truncated source cache')
        return data

    group_count, groups, tag_count, tags = struct.unpack('>4I', read(u(0x10), 16))
    matches = []
    for index in range(tag_count):
        group, salt, pointer = struct.unpack('>HHI', read(tags + index * 8, 8))
        if group == 0xffff or pointer in (0, 0xffffffff):
            continue
        if group >= group_count:
            raise ValueError('Invalid source tag group')
        if read(groups + group * 16, 4) == b'matg':
            matches.append((index, pointer))
    if len(matches) != 1:
        raise ValueError('Expected one globals tag')
    index, pointer = matches[0]
    # Original8244B758: globals256 -> camera16 -> data-reference12.
    count, camera = struct.unpack('>II', read(pointer + 252, 8))
    if count != 1:
        raise ValueError('Expected one original camera settings record')
    #824BFE90 reads180 bytes starting at camera36. Keep the full216-byte
    # record so the existing pitch-function reference can be relocated too.
    settings = read(camera, 216)
    reference = read(camera + 16, 20)
    length = struct.unpack_from('>I', reference, 0)[0]
    payload = struct.unpack_from('>I', reference, 12)[0]
    if not 20 <= length <= 65536:
        raise ValueError('Unexpected camera curve payload size')
    data = read(payload, length)

out = RESEARCH / 'isolated'
out.mkdir(exist_ok=True)
(out / 'camera-pitch-function.bin').write_bytes(data)
(out / 'camera-settings.bin').write_bytes(settings)
report = dict(source=str(SOURCE.relative_to(ROOT)), tag_index=index,
              globals_pointer=hex(pointer), block_offset='0xfc',
              camera_pointer=hex(camera), reference_hex=reference.hex(),
              source_payload_pointer=hex(payload), byte_count=length,
              sha256=hashlib.sha256(data).hexdigest(),
              consumer='8244B758 via original8226CD10',
              semantic='Camera.PitchToVerticalOffset; scaled by held object definition bounding radius',
              settings_byte_count=len(settings),
              settings_sha256=hashlib.sha256(settings).hexdigest(),
              settings_consumer='824BFE90: camera36 -> runtime8407F2B0,180 bytes',
              obstruction_settings=list(struct.unpack_from('>6f',settings,192)),
              limitation='Source-data extraction only; not runtime validation')
(out / 'camera-pitch-function.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
