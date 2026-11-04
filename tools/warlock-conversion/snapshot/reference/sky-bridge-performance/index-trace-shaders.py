"""Index exact native microcode bytes and tag references for draw-trace attribution."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO/'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from string_ids import StringTable


def index_map(path):
    cache = Cache(path)
    strings = StringTable(cache)
    schemas = REPO/'tools/warlock-conversion/snapshot/reference/plugins'
    materials = defaultdict(list)
    templates = defaultdict(list)
    def identity(tag_id):
        return {'id': tag_id, 'group': cache.tags[tag_id]['group'], 'name': cache.name(tag_id)}
    for tag_id, tag in cache.tags.items():
        if tag['group'] == 'rmt2':
            for stage, offset in (('vertex', 12), ('pixel', 28)):
                shader_id = cache.u(tag['offset']+offset) & 65535
                if shader_id in cache.tags:
                    templates[shader_id].append(dict(identity(tag_id), stage=stage))
        schema_path = schemas / (tag['group'] + '.xml')
        if not schema_path.exists():
            continue
        schema = ET.parse(schema_path).getroot()
        for post in schema.findall("tagblock[@name='Postprocess']"):
            template_ref = post.find("tagRef[@name='Shader Template']")
            if template_ref is None:
                continue
            for row in cache.block(tag['offset'] + int(post.get('offset'), 0),
                                   int(post.get('elementSize'), 0)):
                template_id = cache.u(row+int(template_ref.get('offset'), 0)+12) & 65535
                if template_id in cache.tags:
                    assert cache.tags[template_id]['group'] == 'rmt2'
                    materials[template_id].append(identity(tag_id))
    by_hash = defaultdict(list)
    missing = []
    for tag_id, tag in cache.tags.items():
        if tag['group'] not in ('pixl', 'vtsh', 'glps', 'glvs'):
            continue
        schema = ET.parse(schemas/(tag['group']+'.xml')).getroot()
        for block in schema.findall('tagblock'):
            shader = block.find('shader')
            if shader is None:
                continue
            stage = shader.get('type')
            runtime_size = {'pixel': 0x28, 'vertex': 0x368}[stage]
            for ordinal, row in enumerate(cache.block(tag['offset']+int(block.get('offset'), 0),
                                                       int(block.get('elementSize'), 0))):
                entry = dict(identity(tag_id), program_index=ordinal, stage=stage)
                pointer = cache.u(row+int(shader.get('offset'), 0))
                if pointer == 0:
                    missing.append(entry)
                    continue
                runtime = cache.pointer(pointer)
                debug = runtime+runtime_size
                magic, debug_size, code_size = cache.unpack('III', debug)
                assert magic >> 16 == 0x102a and debug_size >= 28
                code = cache.pointer(cache.u(runtime+16))
                assert code_size > 0 and code_size % 4 == 0 and code+code_size <= len(cache.data)
                digest = hashlib.sha256(cache.data[code:code+code_size]).hexdigest()
                entry['code_size'] = code_size
                entry['code_file_offset'] = code
                entry['templates'] = [dict(t, materials=materials[t['id']]) for t in templates[tag_id]]
                entry['reflection'] = [{'name': strings.text(cache.u(r)),
                    'register': cache.unpack('H', r+4)[0], 'count': cache.data[r+6],
                    'register_set': cache.data[r+7]} for r in cache.block(row+40, 8)]
                by_hash[digest].append(entry)
    cache.close()
    return {'map': str(path), 'map_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'program_count': sum(map(len, by_hash.values())), 'unique_microcodes': len(by_hash),
        'programs_by_guest_endian_sha256': dict(by_hash), 'null_runtime_programs': missing,
        'limitation': 'Exact shader byte and tag-reference identities. Shared bytecode may have multiple material users; geometry and bindings are needed to disambiguate. No live draws or pixels have been observed by this tool.',
        'credit': 'Sky Bridge from Halo Online; upstream H3 conversion GeneralHeed / Priception, Halo Online Map Pack For Halo 3, https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190 . Original individual creator unspecified; this project is the Xbox 360/OpenH3M adaptation.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.resolve().relative_to(REPO)
    report = index_map(args.map)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: report[k] for k in ('map_sha256', 'program_count', 'unique_microcodes')}))
