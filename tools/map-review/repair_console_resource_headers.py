"""Stage a map-only correction for stale optimized resource headers.

Preserves installed content. Writes one reviewable candidate inside the repo.
Console size limits still apply; this is not a way around oversized maps.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from build_scenario_checkpoint import resource_salt
from build_dlc_live import build
from verify_dlc_stfs import verify_payload
from console_cache_limits import require_console_sizes


def normalized_header(header):
    data = bytearray(header)
    for start, size in ((0x320,4),(0x328,8),(0x330,0x13c),(0x1c,0x100),
                        (0x144,8),(0x16c,0x20),(0x49c,0x10)):
        data[start:start+size] = bytes(size)
    return data


def repair(source, output, xex):
    source, output = source.resolve(strict=True), output.resolve()
    if not source.is_relative_to(ROOT) or not output.is_relative_to(ROOT):
        raise ValueError('Source and output must stay in the repository')
    if output.exists():
        raise ValueError('Inspect the existing candidate before replacing it')
    gate = require_console_sizes([source])[0]
    salt = resource_salt(xex)
    original = source.read_bytes()
    if original[0x142] != 1:
        raise ValueError('Expected enabled original optimized-resource header')
    if hashlib.sha1(salt+normalized_header(original[:0x3000])).digest() != original[0x330:0x344]:
        raise ValueError('Source salted header hash is invalid')
    corrected = bytearray(original)
    corrected[0x142] = 0
    corrected[0x330:0x344] = hashlib.sha1(salt+normalized_header(corrected[:0x3000])).digest()
    changed = [i for i, (a,b) in enumerate(zip(original, corrected)) if a != b]
    if any(i != 0x142 and not 0x330 <= i < 0x344 for i in changed):
        raise ValueError('Correction changed bytes outside the enable flag and header hash')
    assert original[0x3000:] == corrected[0x3000:]
    info = (source.with_suffix('.mapinfo')).read_bytes()
    title = info[0x44:0x84].decode('utf-16-be').split('\0')[0]
    preview = info[0xF44:0x1044].split(b'\0')[0].decode('ascii')
    if not preview or any(c in preview for c in '/\\:'):
        raise ValueError('Invalid preview identity')
    names = [source.with_suffix('.mapinfo').name] + [preview+s+'.blf' for s in ('','_sm','_clip','_film','_variant')]
    if any(not (source.parent/n).is_file() for n in names):
        raise ValueError('Incomplete source payload')
    payload = output/'payload'
    payload.mkdir(parents=True)
    (payload/source.name).write_bytes(corrected)
    for name in names:
        os.link(source.parent/name, payload/name)
    result = build(payload, output/'Content/0000000000000000/4D5307E6/00000002/building')
    result['payload_verification'] = verify_payload(Path(result['package']), payload)
    result.update(map=source.stem, title=title, source_map=str(source),
                  original_map_sha256=hashlib.sha256(original).hexdigest(),
                  corrected_map_sha256=hashlib.sha256(corrected).hexdigest(),
                  changed_map_offsets=[hex(i) for i in changed],
                  cache_size_gate=gate, body_unchanged=True,
                  correction='Disable stale optimized resource layout; retain native play/zone tables',
                  xex_changes='None', console_status='Hardware unverified repair candidate')
    (output/'manifest.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--xex', type=Path, required=True)
    options = parser.parse_args()
    result = repair(options.source, options.output, options.xex)
    print(json.dumps({k:result[k] for k in ('package','corrected_map_sha256','body_unchanged','console_status')}))
