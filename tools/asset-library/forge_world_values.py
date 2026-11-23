"""Apply Forge World (Ryno's MCC "Forge World - Halo 3" port, Steam Workshop 3597611181) tuning values to the
asset-library tags, as the user asked on 2026-11-20 ("use those values").

Input: Inject360 field dumps of the Forge World tags and of our compiled tags (work\\asset-library\\_work\\forge_world_compare),
which name fields the Assembly-plugin way; output: TagEdit 'set' ops on our source tags, which use the editing kit's
names, matched by normalised path. Only tuning values are taken; structure (shapes, regions, markers, strings, tag
references, model-derived bounds) stays ours. Written to work\\asset-library\\_work\\forge_world_compare\\applied.json.

  python forge_world_values.py plan     show what would change
  python forge_world_values.py apply    write the values with TagEdit
"""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit

D = kit.WORK / 'forge_world_compare'
BS = chr(92)
PAIRS = [  # (our compiled dump, forge world dump, our source tag)
    ('our_dmr_weap', 'fw_dmr_weap', 'objects{0}weapons{0}rifle{0}reach_dmr{0}reach_dmr.weapon'),
    ('our_dmr_proj', 'fw_dmr_proj', 'objects{0}weapons{0}rifle{0}reach_dmr{0}reach_dmr_bullet.projectile'),
    ('our_dmr_jpt', 'fw_dmr_jpt', 'objects{0}weapons{0}rifle{0}reach_dmr{0}reach_dmr_bullet.damage_effect'),
    ('our_falcon_vehi', 'fw_falcon_vehi', 'objects{0}vehicles{0}reach_falcon{0}reach_falcon.vehicle'),
    ('our_rev_vehi', 'fw_rev_vehi', 'objects{0}vehicles{0}reach_revenant{0}reach_revenant.vehicle'),
    ('our_rev_phmo', 'fw_rev_phmo', 'objects{0}vehicles{0}reach_revenant{0}reach_revenant.physics_model'),
]
# not tuning: structure, presentation, strings, references, model-derived bounds, runtime/computed data
SKIP = re.compile(r'^/Mass$|Runtime|Unknown|Pointer|Predicted|Function|Index|Marker|Name|Checksum|User Data|Padding|Datum|Message|'
                  r'Font Icon|Bounding|Radius|Size|Shape|Region|Node|Inertia|Center Of Mass|First Person|Material|'
                  r'Campaign|Scale By|Turn Off With|Default Model Variant|Attachments|Seats|Damage Sections|MOPP|'
                  r'Polyhedr|Lists|Phantom|Mass Distributions|Four Vectors|Plane Equations', re.I)


def load(p):
    d = {}
    for line in open(p, encoding='utf-8', errors='replace'):
        if ' = ' in line:
            k, v = line.rstrip('\n').split(' = ', 1)
            d.setdefault(k, v)
    return d


def numbers(v):
    try:
        return [float(x) for x in v.split()]
    except ValueError:
        return None


ALIAS = {'vtoltype': 'typevtol', 'alienscouttype': 'typealienscout', 'magicangularaccelerationexponent': 'magicangularaccexp',
         'magicangularaccelerationscale': 'magicangularaccscale', 'magicangularaccelerationk': 'magicangularacck',
         'propellerrotationspeed': 'proprotationspeed'}


def norm(path):
    out = []
    for seg in path.strip('/').split('/'):
        seg = re.sub(r'^(Struct|Block):', '', seg)
        m = re.match(r'(.*?)(\[\d+\])?$', seg)
        n = re.sub(r'[^a-z0-9]', '', m.group(1).lower())
        out.append(ALIAS.get(n, n) + (m.group(2) or ''))
    return out


def plan():
    ops, report = [], []
    for ours, fw, tag in PAIRS:
        tag = tag.format(BS)
        a, b = load(D / f'{ours}.txt'), load(D / f'{fw}.txt')
        kd = kit.dump(tag).read_text(encoding='utf-8', errors='replace').splitlines()
        kfields = {}
        for line in kd:
            parts = line.split('\t')
            if len(parts) >= 3:
                kfields[parts[0]] = (parts[1], parts[2])
        for k, va in a.items():
            vb = b.get(k)
            if vb is None or va == vb or SKIP.search(k):
                continue
            na, nb = numbers(va), numbers(vb)
            if na is None or nb is None or len(na) != len(nb):
                continue
            if all(abs(x - y) < 1e-4 * max(1, abs(x)) for x, y in zip(na, nb)):
                continue
            want = norm(k)
            # kit paths carry struct levels that the plugin view flattens away: drop them before comparing
            hits = [kk for kk in kfields
                    if [norm(seg)[0] for seg in kk.split('/') if not seg.startswith('Struct:')] == want]
            if len(hits) != 1:
                report.append(f'NO UNIQUE KIT FIELD for {tag} {k} ({len(hits)} candidates)')
                continue
            ktype, kval = kfields[hits[0]]
            # Source tags sometimes store other units than the built map (degrees vs radians, per second vs per
            # tick). Copy only where our source already equals our built value, or the target is zero.
            ks = numbers(kval.split(':')[0].replace(',', ' '))
            factor = None
            if all(x == 0 for x in nb):
                factor = 1.0
            elif ks is not None and len(ks) == len(na):
                ratios = [k / x for k, x in zip(ks, na) if abs(x) > 1e-9]
                if ratios and all(abs(r - ratios[0]) < 1e-3 * max(1, abs(ratios[0])) for r in ratios)                         and all(abs(k) < 1e-9 for k, x in zip(ks, na) if abs(x) <= 1e-9):
                    factor = ratios[0]          # same units (1) or a linear unit change such as degrees/radians
            if factor is None and ks is not None and len(ks) == len(na) and all(abs(k) < 1e-9 and abs(x) < 1e-9 for k, x in zip(ks, na)):
                factor = 57.29577951 if 'angle' in hits[0].lower() else 1.0   # kit stores angles in degrees
            if factor is None:
                report.append(f'UNITS DIFFER, not copied: {tag} {hits[0]} (source {kval}, built {va}, forge world {vb})')
                continue
            nb = [x * factor for x in nb]
            value = ','.join(f'{x:g}' for x in nb) if ',' in kval or len(nb) > 1 else f'{nb[0]:g}'
            if ktype in ('ElementInteger', 'ElementShortInteger', 'ElementCharInteger', 'ElementEnum'):
                value = str(int(nb[0]))
            ops.append({'op': 'set', 'tag': tag, 'field': hits[0], 'value': value})
            report.append(f'{tag} | {hits[0]}: {kval} -> {value}')
    # the physics model's rigid body mass is computed by the kit when left 0; use Forge World's
    rev_phmo = PAIRS[5][2].format(BS)
    fwm = load(D / 'fw_rev_phmo.txt').get('/Rigid Bodies[0]/Mass')
    if fwm:
        ops.append({'op': 'set', 'tag': rev_phmo, 'field': 'Block:rigid bodies[0]/mass', 'value': fwm})
        report.append(f'{rev_phmo} | Block:rigid bodies[0]/mass: (computed) -> {fwm}')
    return ops, report


if __name__ == '__main__':
    ops, report = plan()
    print('\n'.join(report))
    print(len(ops), 'values')
    if sys.argv[1:] == ['apply']:
        print(kit.edit(ops, 'forge_world_values'))
        (D / 'applied.json').write_text(json.dumps({'source': 'Forge World - Halo 3 (Ryno), Steam Workshop 3597611181',
                                                   'ops': ops}, indent=1))
