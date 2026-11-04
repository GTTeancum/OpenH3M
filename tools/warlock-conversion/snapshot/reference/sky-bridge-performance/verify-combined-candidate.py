"""Verify candidate36 combines only candidate35 fabric and candidate34 bitmap fixes.

Compare the entire retained metadata/raw sections, not just tag roots. New
registry tables must retain all original entries; bitmap content is compared
with the separately runtime-tested candidate34 resources.
"""
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import numpy as np

REF = Path(__file__).resolve().parent
REPO = REF.parents[4]
sys.path.insert(0, str(REPO/'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from resource_reader import Resource


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify():
    paths = {i: REPO/f'work/sky-bridge/payload-{i}/sky_bridge.map' for i in (34, 35, 36)}
    expected = {
        34: '70e5c7aaed939be2c8c718535d8113deb334cd66ed428bd995c7b8573e93aa59',
        35: '9dec756fd9d0b4b3d2af252bb75a7468bccba5e6d3d8034001f8cf0c2f705a8e'}
    for i, digest in expected.items():
        assert sha(paths[i].read_bytes()) == digest
    a, b, screen = (Cache(paths[i]) for i in (35, 36, 34))
    try:
        assert set(a.tags) == set(b.tags)
        assert a.base-b.base == 0x200000
        assert b.u(0x490)-a.u(0x490) == 0x200000

        def same_address(offset):
            return b.pointer(offset-a.start+a.base)

        # Original file offsets relocate; virtual addresses remain unchanged.
        for tid, tag in a.tags.items():
            other = b.tags[tid]
            assert tag['group'] == other['group'] and tag['salt'] == other['salt']
            assert same_address(tag['offset']) == other['offset']

        allowed = []
        def allow(offset, size, reason):
            allowed.append((offset, size, reason))

        zone = next(t['offset'] for t in a.tags.values() if t['group'] == 'zone')
        play = next(t['offset'] for t in a.tags.values() if t['group'] == 'play')
        schema = ET.parse(REPO/'tools/warlock-conversion/snapshot/reference/plugins/zone.xml').getroot()
        field = lambda name: zone+int(next(x for x in schema if x.get('name') == name).get('offset'), 0)
        control = field('Native Resource Control Data')
        manifests = field('Static BSP Zone Manifests')
        manifest, = a.block(manifests, 120)
        index = a.pointer(a.u(16))

        tables = []
        for offset, stride, added in ((zone+0x58, 64, 2), (play+0x18, 88, 2),
                                      (play+0x24, 16, 0), (play+0x30, 16, 2)):
            old = [bytes(a.data[x:x+stride]) for x in a.block(offset, stride)]
            new = [bytes(b.data[x:x+stride]) for x in b.block(same_address(offset), stride)]
            assert len(new) == len(old)+added and new[:len(old)] == old
            allow(offset, 12, 'registry table location/count')
            tables.append(dict(stride=stride, original_rows=len(old), added_rows=added))
        ac = a.pointer(a.u(control+12)); bc = b.pointer(b.u(same_address(control)+12))
        assert a.data[ac:ac+a.u(control)] == b.data[bc:bc+a.u(control)]
        allow(control, 4, 'resource control byte count')
        allow(control+12, 4, 'resource control location')
        assert a.u(index+8) == b.u(same_address(index)+8)
        ai = a.pointer(a.u(index+12)); bi = b.pointer(b.u(same_address(index)+12))
        assert a.data[ai:ai+a.u(index+8)*8] == b.data[bi:bi+a.u(index+8)*8]
        allow(index+8, 8, 'tag table count/location; contents unchanged')
        old_bits = [a.u(x) for x in a.block(manifest, 4)]
        new_bits = [b.u(x) for x in b.block(same_address(manifest), 4)]
        resource_count = a.u(zone+0x58)
        expected_bits = old_bits+[0]*max(0, (resource_count+2+31)//32-len(old_bits))
        for rid in (resource_count, resource_count+1):
            expected_bits[rid//32] |= 1 << (rid%32)
        assert new_bits == expected_bits
        allow(manifest, 12, 'two added bitmap residency bits')
        allow(manifest+0x30, 4, 'added bitmap memory budget')

        textures = []
        added_raw_bytes = added_control_bytes = 0
        for tid, mips in ((9767, 9), (9772, 8)):
            def bitmap(c):
                root = c.tags[tid]['offset']
                row, = c.block(root+96, 48)
                handle, = c.block(root+140, 8)
                return row, handle, Resource(c, c.u(handle))
            old_row, old_handle, _ = bitmap(a)
            row, _, resource = bitmap(b)
            sr, _, reference = bitmap(screen)
            assert b.data[row:row+48] == screen.data[sr:sr+48]
            assert resource.data == reference.data and resource.fix == reference.fix
            assert resource.raw == reference.raw and resource.root == reference.root
            assert b.data[row+20]+1 == mips
            added_raw_bytes += sum(map(len, resource.raw))
            added_control_bytes += len(resource.data)
            allow(old_row, 48, f'bitmap {tid} record')
            allow(old_handle, 4, f'bitmap {tid} resource handle')
            textures.append(dict(tag=tid, mips=mips, raw_sha256=[sha(x) for x in resource.raw],
                                 control_sha256=sha(resource.data), fixups=resource.fix))
        assert b.u(same_address(manifest)+0x30)-a.u(manifest+0x30) == added_raw_bytes
        assert b.u(same_address(control))-a.u(control) == added_control_bytes

        original_meta = np.frombuffer(a.data, dtype=np.uint8, offset=a.start, count=a.u(0x490))
        retained_meta = np.frombuffer(b.data, dtype=np.uint8, offset=same_address(a.start), count=a.u(0x490))
        differences = original_meta != retained_meta
        changed_bytes = int(np.count_nonzero(differences))
        for offset, size, _ in allowed:
            differences[offset-a.start:offset-a.start+size] = False
        assert not np.any(differences), 'Unrelated retained metadata changed'
        del original_meta, retained_meta

        ar = (a.u(0x484)+a.u(0x470)) & 0xffffffff
        br = (b.u(0x484)+b.u(0x470)) & 0xffffffff
        assert a.data[ar:ar+a.u(0x488)] == b.data[br:br+a.u(0x488)]
        assert a.data[a.start+a.u(0x490):] == b.data[b.start+b.u(0x490):]
        report = dict(candidate=36, map_sha256=sha(paths[36].read_bytes()),
            bytes=paths[36].stat().st_size, tags=len(a.tags),
            retained_metadata_bytes=a.u(0x490), changed_retained_metadata_bytes=changed_bytes,
            unrelated_metadata_unchanged=True, original_raw_bytes_unchanged=a.u(0x488),
            trailing_sections_unchanged=True, original_registry_entries_unchanged=True,
            tables=tables, textures=textures,
            fabric_programs_and_material_retained_from_candidate35=True,
            allowed_metadata_fields=[dict(virtual_address=hex(x-a.start+a.base), bytes=n, reason=r)
                                     for x,n,r in allowed],
            limitation='Structural composition only; combined runtime and visual behavior require verification.',
            credit=json.loads((REF/'sky-pixel-probe-build.json').read_text())['credit'])
        output = REPO/'work/sky-bridge/combined-candidate-build/verification.json'
        output.write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps({k:v for k,v in report.items() if k not in ('allowed_metadata_fields','tables','textures')}))
    finally:
        a.close(); b.close(); screen.close()


if __name__ == '__main__':
    verify()
