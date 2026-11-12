"""Read-only source opcode/signature audit against original Halo 3 definitions."""
import argparse
from collections import Counter
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from cache_reader import Cache
from assemble_scenario import field


def audit(path, version='U14'):
    reference = Path(__file__).resolve().parents[1] / 'reference'
    source_defs = ET.parse(reference / f'scripting/H3MCC_{version}_Scripting.xml').getroot()
    target_defs = ET.parse(reference / 'scripting/H3_Scripting.xml').getroot()
    source_functions = {int(f.get('opcode'), 0): f for f in source_defs.find('functions')}
    target_functions = {f.get('name'): f for f in target_defs.find('functions')}
    def signature(f):
        return f.get('returnType'), [dict(p.attrib) for p in f]
    source = Cache(path, True)
    try:
        root = next(t['offset'] for t in source.tags.values() if t['group'] == 'scnr')
        schema = ET.parse(reference / 'mcc/scnr.xml').getroot()
        block = field(schema, 'Script Expressions')
        rows = source.block(root + int(block.get('offset'), 0), 24)
        strings_field = field(schema, 'Script Strings')
        strings_at = root + int(strings_field.get('offset'), 0)
        strings_size = source.u(strings_at)
        strings_start = source.pointer(source.u(strings_at + 12)) if strings_size else 0
        strings = bytes(source.data[strings_start:strings_start + strings_size])
        # HsSyntaxNode handles carry both a slot index and its allocation salt.
        # Check these before attempting endian/opcode conversion: an in-range
        # index alone can silently link to a different expression allocation.
        graph_errors, roots, links = [], [], []
        active = {index: source.unpack('4H', row) for index, row in enumerate(rows)
                  if source.unpack('H', row)[0]}
        def check_handle(handle, owner, allow_null=True):
            if handle == 0xffffffff and allow_null:
                return
            index, salt = handle & 65535, handle >> 16
            if index not in active or active[index][0] != salt:
                graph_errors.append(dict(owner=owner, handle=f'{handle:08x}',
                    reason='missing slot or mismatched allocation salt'))
            else:
                links.append((owner, index))
        for block_name, handle_offset in (('Scripts', 36), ('Globals', 36)):
            spec = field(schema, block_name)
            for index, row in enumerate(source.block(root + int(spec.get('offset'), 0),
                                                       int(spec.get('elementSize'), 0))):
                handle = source.u(row + handle_offset)
                name = bytes(source.data[row:row + 32]).split(b'\0')[0].decode('ascii')
                roots.append(dict(block=block_name, index=index, name=name,
                                  handle=f'{handle:08x}'))
                check_handle(handle, f'{block_name}[{index}]')
        for index, (salt, opcode, kind, state) in active.items():
            row = rows[index]
            check_handle(source.u(row + 8), f'expression[{index}].next')
            if state in (8, 10):
                check_handle(source.u(row + 16), f'expression[{index}].child', False)
        name_mismatches = []
        counts, types, flags = Counter(), Counter(), Counter()
        script_name_nodes = {source.u(row + 16) & 65535 for row in rows
                             if source.unpack('H', row)[0] and source.unpack('H', row + 6)[0] == 10}
        for index, row in enumerate(rows):
            salt, opcode, kind, state = source.unpack('4H', row)
            if not salt:
                continue
            types[kind] += 1
            flags[state] += 1
            if state == 8 or (state == 9 and kind == 2 and index not in script_name_nodes):
                counts[opcode] += 1
            if state == 9 and kind == 2 and index not in script_name_nodes:
                offset = source.u(row + 12)
                text = strings[offset:].split(b'\0')[0].decode('ascii', errors='replace')
                sf = source_functions.get(opcode)
                if sf is None or sf.get('name') != text:
                    name_mismatches.append(dict(opcode=opcode, source_text=text,
                        defined_name=sf.get('name') if sf is not None else None))
        functions = []
        for opcode, count in sorted(counts.items()):
            sf = source_functions.get(opcode)
            tf = target_functions.get(sf.get('name')) if sf is not None else None
            functions.append(dict(source_opcode=opcode, count=count,
                name=sf.get('name') if sf is not None else None,
                target_opcode=int(tf.get('opcode'), 0) if tf is not None else None,
                same_signature=sf is not None and tf is not None and signature(sf) == signature(tf)))
        return dict(source=str(path), source_version=version, expressions=len(rows), active=sum(flags.values()),
                    flags=dict(flags), types=dict(types), functions=functions,
                    opcode_name_mismatches=name_mismatches,
                    graph=dict(roots=roots, validated_links=len(links), errors=graph_errors),
                    unsupported=[r for r in functions if not r['same_signature']])
    finally:
        source.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--version', choices=('U13', 'U14'), default='U14')
    args = parser.parse_args()
    args.report.resolve().relative_to(Path(__file__).resolve().parents[4])
    result = audit(args.source, args.version)
    args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(active=result['active'], flags=result['flags'],
        unsupported=result['unsupported'], opcode_name_mismatch_count=len(result['opcode_name_mismatches'])), indent=2))
