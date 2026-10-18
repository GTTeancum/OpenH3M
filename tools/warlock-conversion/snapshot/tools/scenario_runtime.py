"""Replace map-specific visibility, audio and inactive stock script state."""
import copy
import xml.etree.ElementTree as ET
from assemble_scenario import field, stage
from tag_metadata import MetadataConverter


EMPTY_BLOCKS = ('Scripts', 'Globals', 'Script References', 'Machines', 'Machine Palette',
                'Soft Ceilings', 'Trigger Volumes', 'Scenario Kill Triggers',
                'Scenario Safe Zone Triggers')


def stage_runtime(importer):
    try:
        return _stage(importer)
    except Exception:
        importer.failed = True
        raise


def _stage(i):
    s, c, b = i.source, i.registry.cache, i.builder
    ss = ET.parse(i.reference / 'mcc/scnr.xml').getroot()
    ds = ET.parse(i.reference / 'plugins/scnr.xml').getroot()
    root = next(t['offset'] for t in s.tags.values() if t['group'] == 'scnr')
    target = next(t['offset'] for t in c.tags.values() if t['group'] == 'scnr')
    converter = MetadataConverter(s, b, i.source_strings, i.target_strings, i.import_tag)
    arrays = {}
    for name in EMPTY_BLOCKS:
        sf = field(ss, name)
        if s.u(root + int(sf.get('offset'), 0)):
            raise ValueError(f'Active source {name} requires a dedicated conversion')
        arrays[name] = (0, b'')
    expressions = field(ss, 'Script Expressions')
    stride = int(expressions.get('elementSize'), 0)
    rows = s.block(root + int(expressions.get('offset'), 0), stride)
    # Unallocated expression slots have a zero salt followed by MCC heap fill.
    # They are capacity, not executable script nodes; no live roots exist above.
    if any(bytes(s.data[r:r + stride]) != bytes(2) + b'\xba' * (stride - 2) for r in rows):
        raise ValueError('Source contains populated script expression slots')
    arrays['Script Expressions'] = (0, b'')
    for name in ('Zone Set Potentially Visible Sets', 'Zone Set Audibility', 'Zone Sets', 'Scripting Data', 'AI User Hint Data'):
        sf, df = copy.deepcopy(field(ss, name)), field(ds, name)
        rows = s.block(root + int(sf.get('offset'), 0), int(sf.get('elementSize'), 0))
        if name == 'Zone Sets':
            if any(s.unpack('HH', r + 36) != (65535, 0) for r in rows):
                raise ValueError('Active MCC zone lighting override requires conversion')
            for node in list(sf):
                if node.get('offset') and int(node.get('offset'), 0) >= 36:
                    sf.remove(node)
        payload = b''.join(converter.convert(r, sf, df, 'scnr:/' + name) for r in rows)
        arrays[name] = len(rows), payload
    stage(b, {'arrays': arrays, 'unresolved': []}, ds)
    # With no scripts/globals/live expressions, the source string allocation is
    # unused. Remove stock strings and editor data without copying heap slack.
    for name in ('Script Strings', 'Editor Scenario Data'):
        if name == 'Editor Scenario Data' and s.u(root + int(field(ss, name).get('offset'), 0)):
            raise ValueError('Nonempty scenario editor data is unsupported')
        address = target - c.start + c.base + int(field(ds, name).get('offset'), 0)
        b.meta[address - b.base:address - b.base + 20] = bytes(20)
    return {name: count for name, (count, _) in arrays.items()}
