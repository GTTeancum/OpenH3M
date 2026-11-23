"""Stage compiled H3 MCC scripts into the retail scenario, preserving indices."""
import copy
import struct
import xml.etree.ElementTree as ET
from assemble_scenario import field
from audit_scenario_scripts import audit
from script_expressions import convert_expressions


def prepare_scripts(i, ss, ds, converter, root):
    s = i.source
    # Keep integration scoped to sources whose runtime tables were audited.
    # Foundation uses U14. Dune's June 2023 build uses U13, not the current
    # opcode table; both exact scenarios have audited tables and graph links.
    # Runtime graph/opcode/parameter checks below still run on every build.
    name = next(s.name(n) for n, t in s.tags.items() if t['group'] == 'scnr')
    version = 'U14'
    if name == r'levels\multi\dune\dune':
        build = bytes(s.data[0xA0:0xC0]).split(b'\0', 1)[0].decode('ascii')
        if build != 'Jun 27 2023 08:39:36':
            raise ValueError(f'Dune script build has not been audited: {build}')
        version = 'U13'
    elif (not name.endswith(('h2_elongation', 's3d_sky_bridgenew'))
            and name != r'halo_2\levels\foundation\foundation'
            # Asset-library throwaway test map: a stock Zanzibar copy with its own scripts removed, so only the
            # kit's global_scripts remain (as in the kit-built Sky Bridge). The audit below still runs.
            and name != r'levels\test\asset_library_test\asset_library_test'):
        raise ValueError(f'Script scenario has not been audited: {name}')
    report = audit(s.file.name, version)
    if report['unsupported'] or report['opcode_name_mismatches'] or report['graph']['errors']:
        raise ValueError('Source script graph or opcode audit failed')
    def rows(label):
        f = field(ss, label)
        return s.block(root + int(f.get('offset'), 0), int(f.get('elementSize'), 0))
    script_rows, global_rows = rows('Scripts'), rows('Globals')
    def names(entries):
        return [bytes(s.data[a:a+32]).split(b'\0')[0].decode('ascii') for a in entries]
    expression_rows = rows('Script Expressions')
    records = [bytes(s.data[a:a+24]) for a in expression_rows]
    nodes = [struct.unpack('<4H3I2h', record) for record in records]
    # Each parameter reference must belong to a script declaring that parameter.
    # Script calls link to an argument list, not to the callee's expression root.
    params_field = field(field(ss, 'Scripts'), 'Parameters')
    for script in script_rows:
        params = s.block(script + int(params_field.get('offset'), 0),
                         int(params_field.get('elementSize'), 0))
        pending, visited = [s.u(script+36)], set()
        while pending:
            handle = pending.pop()
            if handle == 0xffffffff or handle in visited:
                continue
            visited.add(handle)
            node = nodes[handle & 65535]
            if node[3] == 29:
                if node[6] >= len(params):
                    raise ValueError('Script parameter index exceeds its declaration')
                if s.unpack('H', params[node[6]]+32)[0] != node[2]:
                    raise ValueError('Script parameter type differs from declaration')
            pending.append(node[4])
            if node[3] in (8, 10):
                pending.append(node[6])
    string_ref = root + int(field(ss, 'Script Strings').get('offset'), 0)
    count = s.u(string_ref)
    start = s.pointer(s.u(string_ref+12)) if count else 0
    strings = bytes(s.data[start:start+count])
    def tag(datum, group):
        source_tag = s.tags.get(datum & 65535)
        if source_tag is None or source_tag['salt'] != datum >> 16:
            raise ValueError('Script literal references an invalid tag')
        return i.import_tag(datum)[1]
    payload, changes = convert_expressions(records, strings,
        ET.parse(i.reference/f'scripting/H3MCC_{version}_Scripting.xml').getroot(),
        ET.parse(i.reference/'scripting/H3_Scripting.xml').getroot(),
        names(script_rows), names(global_rows), tag,
        lambda value: i.source_strings.translate(value, i.target_strings))
    arrays = {'Script Expressions': (len(records), payload)}
    for label in ('Scripts', 'Globals', 'Script References'):
        entries = rows(label)
        source_schema, target_schema = copy.deepcopy(field(ss, label)), copy.deepcopy(field(ds, label))
        if label in ('Scripts', 'Globals'):
            # These datums address the validated expression array, not resources.
            for schema in (source_schema, target_schema):
                roots = [f for f in schema if f.tag == 'datum' and int(f.get('offset'), 0) == 36]
                if len(roots) != 1:
                    raise ValueError('Unexpected script root handle schema')
                roots[0].tag = 'uint32'
        arrays[label] = (len(entries), b''.join(converter.convert(a, source_schema,
            target_schema, 'scnr:/'+label) for a in entries))
    i.script_conversion = dict(source_opcode_profile=version,
        scripts=len(script_rows), globals=len(global_rows),
        active_expressions=report['active'], opcode_changes=len(changes))
    return arrays, strings
