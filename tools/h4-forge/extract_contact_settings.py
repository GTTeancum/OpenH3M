"""Extract original H4 biped and non-biped soft-ceiling response data; no game execution."""
import hashlib
import json
import math
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
    # Gen4 Globals: SoftCeilings block at0x144, pointer at0x148.
    # Original82235650 reads global8405D340 ->328 ->16/20/24
    # for non-bipeds; its biped coefficients occupy0/4/8/12.
    count, settings_pointer = struct.unpack('>II', read(pointer + 0x144, 8))
    if count != 1:
        raise ValueError('Expected one original soft-ceiling settings record')
    data = read(settings_pointer, 0x1c)
    values = struct.unpack('>7f', data)
    if not all(math.isfinite(value) for value in values):
        raise ValueError('Nonfinite source response setting')

out = RESEARCH / 'isolated'
out.mkdir(exist_ok=True)
(out / 'contact-settings.bin').write_bytes(data)
names = ('biped_spring_constant', 'biped_normal_damping', 'biped_tangent_damping',
         'biped_min_tangent_damp_velocity', 'vehicle_spring_constant',
         'vehicle_normal_damping', 'vehicle_tangent_damping')
report = dict(source=str(SOURCE.relative_to(ROOT)), tag_index=index,
              globals_pointer=hex(pointer), block_offset='0x144',
              settings_pointer=hex(settings_pointer), count=count,
              sha256=hashlib.sha256(data).hexdigest(),
              fields={name:dict(offset=offset*4,value=value)
                      for offset,(name,value) in enumerate(zip(names,values))},
              consumer='82235650 biped branch uses offsets0/4/8/12; non-biped branch uses16/20/24, including scenery/crates',
              schema='work/stock-h3-audit/TagTool/TagTool/Tags/Definitions/Gen4/Globals.cs',
              limitation='Source data extraction only; no runtime test or native integration proof')
(out / 'contact-settings.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
