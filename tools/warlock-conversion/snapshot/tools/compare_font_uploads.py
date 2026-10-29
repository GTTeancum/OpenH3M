"""Compare recorded upload staging bytes with correctly addressed CPU glyphs.

This observes submitted bytes, not GPU conversion output or completed rendering.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path


def compare(run):
    events = [json.loads(line) for line in (run/'loading-trace.jsonl').read_text().splitlines()]
    sample = [e for e in events if e['event'] == 'font_cache'][-1]
    atlas = sample['atlas']
    start = int(atlas['physical_base'], 16)
    size = atlas['pitch_pixels'] * atlas['height'] * 2
    if size > 1048576:
        raise ValueError('Unexpected atlas size')
    pixels, known = bytearray(size), bytearray(size)
    records = 0
    with (run/'font-uploads.bin').open('rb') as source:
        while header := source.read(16):
            if len(header) != 16:
                raise ValueError('Truncated upload header')
            magic, sequence, address, length = struct.unpack('<4I', header)
            if magic != 0x31505546 or sequence != records or not 0 < length <= size:
                raise ValueError('Invalid upload record')
            if not start <= address < address+length <= start+size:
                raise ValueError('Upload outside sampled atlas')
            data = source.read(length)
            if len(data) != length:
                raise ValueError('Truncated upload pixels')
            offset = address-start
            pixels[offset:offset+length] = data
            known[offset:offset+length] = b'\1'*length
            records += 1
    result = []
    for character in sample['characters']:
        if not character.get('hardware_key_matches') or 'atlas_cpu_sha256' not in character:
            continue
        x, y = struct.unpack_from('>HH', bytes.fromhex(character['hardware_record']), 16)
        width, height = character['metrics'][2:4]
        if x+width > atlas['width'] or y+height > atlas['height']:
            raise ValueError('Glyph outside atlas')
        spans = [((y+r)*atlas['pitch_pixels']+x)*2 for r in range(height)]
        covered = all(all(known[o:o+width*2]) for o in spans)
        data = b''.join(pixels[o:o+width*2] for o in spans)
        digest = hashlib.sha256(data).hexdigest() if covered else None
        result.append({'key':character['key'], 'glyph':chr(character['codepoint']),
                       'covered':covered, 'upload_sha256':digest,
                       'cpu_sha256':character['atlas_cpu_sha256'],
                       'matches_cpu':digest == character['atlas_cpu_sha256'] if covered else None})
    return {'run':run.name, 'physical_base':hex(start), 'records':records,
            'covered_atlas_bytes':sum(known), 'atlas_bytes':size,
            'glyphs':result, 'scope':'Final recorded upload staging versus last CPU sample; not GPU readback. Check capture and upload timing separately.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[4]
    run = args.run.resolve()
    run.relative_to(repo)
    report = compare(run)
    (run/'font-upload-comparison.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({k:v for k,v in report.items() if k != 'glyphs'}))
    print('Glyphs',len(report['glyphs']), 'mismatches',sum(g['matches_cpu'] is False for g in report['glyphs']))
