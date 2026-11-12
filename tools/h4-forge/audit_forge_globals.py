"""Read and cross-check the complete retail Forge globals; no runtime writes."""
import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / 'work/h4-forge-research'
prior = json.loads((RESEARCH/'isolated/forge-globals.json').read_text())
schema = ROOT/'work/stock-h3-audit/TagTool/TagTool/Tags/Definitions/Gen4/ForgeGlobals.cs'
assert 'Size = 0x58' in schema.read_text()
with (RESEARCH/prior['source']).open('rb') as source:
    header = source.read(0x500)
    u = lambda offset: struct.unpack_from('>I', header, offset)[0]
    start = (u(0x484) + u(0x49c)) & 0xffffffff
    base = u(0x2f8)
    def read_at(offset, size):
        source.seek(offset)
        data = source.read(size)
        assert len(data) == size
        return data
    def at(pointer):
        return pointer-base+start
    group_count, groups, tag_count, tags = struct.unpack('>4I', read_at(at(u(0x10)),16))
    assert prior['tag_index'] < tag_count
    group, salt, pointer = struct.unpack('>HHI', read_at(at(tags)+prior['tag_index']*8,8))
    assert group < group_count
    assert read_at(at(groups)+group*16,4) == b'forg'
    assert at(pointer) == prior['offset']
    data = read_at(at(pointer),0x58)
assert hashlib.sha256(data[:prior.get('byte_count',0x50)]).hexdigest() == prior['sha256']
fields = {
    0x24: 'throttle_sensitivity', 0x28: 'magnet_very_low',
    0x2c: 'magnet_low', 0x30: 'magnet_medium', 0x34: 'magnet_high',
    0x38: 'magnet_very_high', 0x3c: 'magnet_angle_degrees',
    0x40: 'magnet_offset_influence', 0x44: 'object_grab_range',
    0x48: 'default_focal_distance', 0x4c: 'minimum_focal_distance',
    0x50: 'maximum_focal_distance', 0x54: 'focal_distance_multiplier',
}
report = dict(source=prior['source'], tag_index=prior['tag_index'], offset=prior['offset'],
              byte_count=len(data), sha256=hashlib.sha256(data).hexdigest(),
              prior_80_bytes_verified=True,
              schema=str(schema.relative_to(ROOT)),
              schema_sha256=hashlib.sha256(schema.read_bytes()).hexdigest(),
              caveat='Names from local TagTool schema; original consumers must establish semantics. Ravine values only.',
              fields={name:dict(offset=hex(offset), value=struct.unpack_from('>f',data,offset)[0])
                      for offset,name in fields.items()})
(RESEARCH/'isolated/full-re-globals.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
