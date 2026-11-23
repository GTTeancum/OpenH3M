"""Damage states, model variants (incl. turret child objects), collision materials, targets and marker fixes for the
Reach Falcon / Revenant and their turrets (ManagedBlam via TagEdit).

Everything is rebuilt against the vehicles' OWN Reach regions, permutations and markers:
  * model variant 'default': regions/permutations/states translated from the Reach .model default variant
    (HREK falcon.model / revenant.model / turret .model, read with tool export-tag-to-xml), plus the Reach child objects
    (chin gun and side guns / plasma mortar) attached the stock-H3 way (Warthog chaingun, Wraith mortar).
  * model materials = the vehicles' own collision materials, each mapped to its Reach damage section.
  * damage sections / instant responses = Reach's damage sections (thresholds, region transitions, flags), with Reach
    effects replaced by the stock Halo 3 effect of the same name (fx\\scenery_fx\\...) or the closest stock H3
    vehicle effect; Reach-only effects without a stock equivalent are left empty (listed in DAMAGE_NOTES).
  * hornet/ghost-derived targets, attachments and response markers that point at markers these models lack are
    retargeted to the Reach markers or removed.
Usage: python damage_setup.py <falcon|revenant|turrets|all>
"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import kit, xml_flat
from build import wp, BS
from turrets import T, FAL, REV

U = 'Struct:unit[0]/'; O = U + 'Struct:object[0]/'
DI = 'Block:new damage info[0]/'
SX = wp('fx', 'scenery_fx')
def fx(kind, name): return wp(SX, kind, name, name + '.effect')
E = {  # Reach effect name -> stock H3 effect (same-named stock effect, or closest stock H3 vehicle effect)
    'human_explosion_huge': fx('explosions', 'human_explosion_huge'), 'human_explosion_large': fx('explosions', 'human_explosion_large'),
    'human_explosion_medium': fx('explosions', 'human_explosion_medium'), 'covenant_explosion_large': fx('explosions', 'covenant_explosion_large'),
    'covenant_explosion_small': fx('explosions', 'covenant_explosion_small'),
    'covenant_mech_break_small': fx('destruction', 'covenant_mech_break_small'), 'covenant_mech_break_medium': fx('destruction', 'covenant_mech_break_medium'),
    'covenant_mech_break_large': fx('destruction', 'covenant_mech_break_medium'),   # H3 has no "large"; medium is the largest
    'human_mech_break_medium': fx('destruction', 'human_mech_break_medium'),
    'human_engine_damage_minor': fx('destruction', 'human_mech_break_small'),       # Reach-only; closest stock H3 human break effect
    'human_engine_damage_medium': fx('destruction', 'human_mech_break_medium'),
    'tail_major': wp('objects', 'vehicles', 'hornet', 'fx', 'destruction', 'trans_tail_major.effect'),
    'falcon_body_destroyed': wp('objects', 'vehicles', 'hornet', 'fx', 'destruction', 'trans_hull_destroyed.effect'),
    'revenant_body_destroyed': wp('objects', 'vehicles', 'ghost', 'fx', 'destruction', 'trans_hull_destroyed.effect'),
    'trans_damage_large': wp('objects', 'vehicles', 'damage_effects', 'large_trans_damage.damage_effect'),
    'ghost_perm_hull_medium': wp('objects', 'vehicles', 'ghost', 'fx', 'destruction', 'perm_hull_medium.effect'),
    'ghost_perm_hull_major': wp('objects', 'vehicles', 'ghost', 'fx', 'destruction', 'perm_hull_major.effect'),
}
DAMAGE_NOTES = [
    "Reach 'can skip transition effects' response flag, section damage transfers, response looping effects, seat-eject lists, "
    "Reach-only falcon/revenant effects (hull_major, wing_*_major, front/back_*_major, body_destroyed_debris, body_constant_*) "
    "have no Halo 3 field or stock effect; omitted unless noted.",
    "Halo 3 instant responses change at most two regions; Reach's death response (7 regions) is split into several responses "
    "with the same threshold.",
    "Revenant 'med_*_decals' regions (Reach medium-damage decal overlays that are hidden by default) are not exported: Halo 3 "
    "has no hidden-by-default region.",
]


def reach_states(xml, regions):
    """Reach default variant -> [(region, [(state, permutation name)])] for the regions we export."""
    rows = xml_flat.flat(xml); out = {}
    for p, v in rows:
        if p.startswith('variants[0]/regions[') and p.endswith('/region name'): cur = v; out[cur] = []
        elif p.startswith('variants[0]/regions[') and '/permutations[0]/states[' in p:
            if p.endswith('/permutation name'): pn = v
            elif p.endswith('/state'): out[cur].append((v, pn))
    return [(r, out[r]) for r in out if r in regions]


def variant_ops(tag, name, regions, objects, idx=0, looping=None):
    V = 'Block:variants[%d]/' % idx; looping = looping or {}
    ops = [{'op': 'add', 'tag': tag, 'block': 'Block:variants'}, {'op': 'set', 'tag': tag, 'field': V + 'name', 'value': name}]
    for ri, (region, states) in enumerate(regions):
        R = V + 'Block:regions[%d]/' % ri
        ops += [{'op': 'add', 'tag': tag, 'block': V + 'Block:regions'}, {'op': 'set', 'tag': tag, 'field': R + 'region name', 'value': region},
                {'op': 'add', 'tag': tag, 'block': R + 'Block:permutations'},
                {'op': 'set', 'tag': tag, 'field': R + 'Block:permutations[0]/permutation name', 'value': 'default'}]
        for si, (state, perm) in enumerate(states):
            S = R + 'Block:permutations[0]/Block:states[%d]/' % si
            ops += [{'op': 'add', 'tag': tag, 'block': R + 'Block:permutations[0]/Block:states'},
                    {'op': 'set', 'tag': tag, 'field': S + 'state', 'value': state},
                    {'op': 'set', 'tag': tag, 'field': S + 'permutation name', 'value': perm}]
            if (region, state) in looping:
                eff, mk = looping[(region, state)]
                ops += [{'op': 'set', 'tag': tag, 'field': S + 'looping effect', 'value': eff},
                        {'op': 'set', 'tag': tag, 'field': S + 'looping effect marker name', 'value': mk}]
    for oi, (pm, cm, child) in enumerate(objects):
        Ob = V + 'Block:objects[%d]/' % oi
        ops += [{'op': 'add', 'tag': tag, 'block': V + 'Block:objects'}, {'op': 'set', 'tag': tag, 'field': Ob + 'parent marker', 'value': pm},
                {'op': 'set', 'tag': tag, 'field': Ob + 'child marker', 'value': cm}, {'op': 'set', 'tag': tag, 'field': Ob + 'child object', 'value': child}]
    return ops


def damage_ops(tag, vitality, global_mat, materials, sections, indirect=0):
    ops = [{'op': 'set', 'tag': tag, 'field': DI + 'Struct:body[0]/maximum vitality', 'value': str(vitality)},
           {'op': 'set', 'tag': tag, 'field': DI + 'global indirect material name', 'value': global_mat},
           {'op': 'clear', 'tag': tag, 'block': DI + 'Block:damage sections'},
           {'op': 'clear', 'tag': tag, 'block': 'Block:materials'}]
    for si, s in enumerate(sections):
        S = DI + 'Block:damage sections[%d]/' % si
        ops += [{'op': 'add', 'tag': tag, 'block': DI + 'Block:damage sections'}, {'op': 'set', 'tag': tag, 'field': S + 'name', 'value': s['name']},
                {'op': 'set', 'tag': tag, 'field': S + 'vitality percentage', 'value': str(s.get('vitality', 1))},
                {'op': 'set', 'tag': tag, 'field': S + 'flags', 'value': s.get('flags', '')}]
        for k in ('stun time', 'recharge time'):
            if k in s: ops.append({'op': 'set', 'tag': tag, 'field': S + k, 'value': str(s[k])})
        for ri, r in enumerate(s.get('responses', [])):
            Rr = S + 'Block:instant responses[%d]/' % ri
            ops.append({'op': 'add', 'tag': tag, 'block': S + 'Block:instant responses'})
            vals = {'damage threshold': r.get('threshold', 0), 'flags': r.get('flags', ''), 'region': r.get('region', ''),
                    'new state': r.get('state', 'default'), 'region (secondary)': r.get('region2', ''), 'new state (secondary)': r.get('state2', 'default'),
                    'transition effect (generic)': r.get('generic', ''), 'transition effect (specific)': r.get('specific', ''),
                    'Struct:damage effect[0]/transition damage effect': r.get('damage_effect', ''), 'effect marker name': r.get('marker', ''),
                    'response delay': r.get('delay', 0), 'delay effect': r.get('delay_effect', ''), 'delay effect marker name': r.get('delay_marker', '')}
            ops += [{'op': 'set', 'tag': tag, 'field': Rr + k, 'value': str(v)} for k, v in vals.items()]
    for mi, (m, sec) in enumerate(materials):
        M = 'Block:materials[%d]/' % mi
        ops += [{'op': 'add', 'tag': tag, 'block': 'Block:materials'}, {'op': 'set', 'tag': tag, 'field': M + 'material name', 'value': m},
                {'op': 'set', 'tag': tag, 'field': M + 'global material name', 'value': global_mat},
                {'op': 'set', 'tag': tag, 'field': M + 'damage section', 'value': str(sec)}]
    ops.append({'op': 'set', 'tag': tag, 'field': DI + 'indirect damage section', 'value': str(indirect)})
    return ops


def target_ops(tag, targets):
    """Keep the donor's first target as the template (lock-on settings), one element per Reach target marker."""
    dump = kit.dump(tag).read_text().splitlines()
    n = int(next(l for l in dump if l.startswith('Block:targets\t')).split('\t')[2])
    ops = [{'op': 'remove', 'tag': tag, 'block': 'Block:targets', 'index': i} for i in range(n - 1, 0, -1)]
    for i, (mk, size) in enumerate(targets):
        if i: ops.append({'op': 'duplicate', 'tag': tag, 'block': 'Block:targets', 'index': 0})
        ops += [{'op': 'set', 'tag': tag, 'field': 'Block:targets[%d]/marker name' % i, 'value': mk},
                {'op': 'set', 'tag': tag, 'field': 'Block:targets[%d]/size' % i, 'value': str(size)},
                {'op': 'set', 'tag': tag, 'field': 'Block:targets[%d]/damage section' % i, 'value': '0'}]
    return ops


def death(regions, generic, specific, marker, delay=0, delay_effect='', delay_marker='', flags='kills variant objects', damage_effect=''):
    """Reach death response -> H3 responses, two regions each (first one carries the effects)."""
    out = []
    for i in range(0, len(regions), 2):
        r = dict(threshold=0, region=regions[i], state='destroyed', flags=flags if i == 0 else '')
        if i + 1 < len(regions): r.update(region2=regions[i + 1], state2='destroyed')
        if i == 0: r.update(generic=generic, specific=specific, marker=marker, delay=delay, delay_effect=delay_effect, delay_marker=delay_marker, damage_effect=damage_effect)
        out.append(r)
    return out


def falcon():
    md = wp(FAL, 'reach_falcon.model'); vh = wp(FAL, 'reach_falcon.vehicle'); X = kit.WORK / 'reach-xml' / 'falcon.model.xml'
    regions = reach_states(X, ['canopy', 'tail', 'hull', 'wing_left', 'wing_right', 'props', 'interior'])
    regions = [(r, [(st, p) for st, p in s if not (r == 'props' and p == 'blur')]) for r, s in regions]  # rotor blur perm not exported
    tur = wp(FAL, 'turrets')
    objects = [('turret', 'vehicle_attach', wp(tur, 'falcon_chin_gun', 'falcon_chin_gun.vehicle')),
               ('falcon_side_gun_left', 'vehicle_attach', wp(tur, 'falcon_side_gun_left', 'falcon_side_gun_left.vehicle')),
               ('falcon_side_gun_right', 'vehicle_attach', wp(tur, 'falcon_side_gun_right', 'falcon_side_gun_right.vehicle'))]
    sections = [
        dict(name='body', flags='takes full dmg when object dies|takes full dmg when obj dstryd', vitality=1, **{'stun time': 5, 'recharge time': 15}, responses=[
            dict(threshold=0.75, generic=E['human_engine_damage_minor'], marker='fx_engine_damage'),
            dict(threshold=0.5, generic=E['human_engine_damage_minor'], marker='fx_engine_damage'),
            dict(threshold=0.25, generic=E['human_engine_damage_medium'], marker='fx_engine_damage', region='hull', state='major damage'),
            *death(['hull', 'canopy', 'wing_left', 'wing_right', 'tail', 'interior', 'props'], E['falcon_body_destroyed'], E['human_explosion_huge'],
                   'fx_explosion', 0.35, E['human_explosion_medium'], 'fx_explosion_start', damage_effect=E['trans_damage_large'])]),
        dict(name='canopy', vitality=0.2, responses=[dict(threshold=0.25, region='canopy', state='major damage')]),
        dict(name='wing_left', vitality=0.3, responses=[dict(threshold=0.25, generic=E['human_mech_break_medium'], marker='fx_wing_left_damage', region='wing_left', state='major damage')]),
        dict(name='wing_right', vitality=0.3, responses=[dict(threshold=0.25, generic=E['human_mech_break_medium'], marker='fx_wing_right_damage', region='wing_right', state='major damage')]),
        dict(name='tail', vitality=0.3, responses=[dict(threshold=0.25, specific=E['tail_major'], region='tail', state='major damage')]),
    ]
    materials = [('hull', 0), ('canopy', 1), ('wing_left', 2), ('wing_right', 3), ('tail', 4)]
    ops = [{'op': 'clear', 'tag': md, 'block': 'Block:variants'}] + variant_ops(md, 'default', regions, objects)
    ops += damage_ops(md, 500, 'hard_metal_thick_hum_hornet', materials, sections)
    # Reach targets (falcon.model 'targets old'), on the markers this render model has
    ops += target_ops(md, [('target_driver', 0.25), ('target_canopy', 0.4), ('target_bay', 0.45), ('target_tail', 0.25),
                           ('target_wing_left', 0.25), ('target_wing_right', 0.25)])
    # stock Hornet attachments on Hornet-only markers -> the Falcon's own engine markers; right-side duplicates removed
    A = O + 'Block:attachments'
    ops += [{'op': 'remove', 'tag': vh, 'block': A, 'index': i} for i in (8, 7)]
    for i, mk in ((0, 'fx_thrust'), (1, 'fx_engine_exhaust'), (2, 'fx_thrust'), (3, 'fx_engine_exhaust'), (5, 'fx_thrust_flare'), (6, 'fx_thrust'), (7, 'thrust')):
        ops.append({'op': 'set', 'tag': vh, 'field': A + '[%d]/marker' % i, 'value': mk})
    # seats (Reach falcon.vehicle): front cabin seats l1/r1 are 'invalid for hero' in Reach (AI only; players use the side guns
    # there) -> H3 'invalid for player'; rear cabin seats l2/r2 use the stock H3 seated troop-bay poses (Pelican bench
    # pelican_p_l05 / pelican_p_r05, present in the Spartan graph and inherited by the Elite graph) instead of the
    # standing Hornet skid pose, because the Falcon cabin seats are seated benches.
    S = U + 'Block:seats[%d]/'
    ops += [{'op': 'set', 'tag': vh, 'field': S % 1 + 'flags', 'value': 'third person camera|allows weapons|invalid for player'},
            {'op': 'set', 'tag': vh, 'field': S % 2 + 'flags', 'value': 'third person camera|allows weapons|invalid for player'},
            {'op': 'set', 'tag': vh, 'field': S % 5 + 'label', 'value': 'pelican_p_l05'},
            {'op': 'set', 'tag': vh, 'field': S % 6 + 'label', 'value': 'pelican_p_r05'}]
    print(kit.edit(ops, 'falcon_damage'))
    return regions


def revenant():
    md = wp(REV, 'reach_revenant.model'); vh = wp(REV, 'reach_revenant.vehicle'); X = kit.WORK / 'reach-xml' / 'revenant.model.xml'
    regions = reach_states(X, ['hull', 'front_left', 'front_right', 'back_left', 'back_right', 'interior'])
    objects = [('turret', '', wp(REV, 'turrets', 'revenant_plasma_turret', 'revenant_plasma_turret.vehicle'))]
    looping = {('hull', 'minor damage'): (E['ghost_perm_hull_medium'], 'fx_engine_damage'), ('hull', 'major damage'): (E['ghost_perm_hull_major'], 'fx_engine_damage')}
    sections = [
        dict(name='body', flags='takes full dmg when object dies', vitality=1, **{'stun time': 5, 'recharge time': 15}, responses=[
            dict(threshold=0.75, generic=E['human_engine_damage_medium'], specific=E['covenant_mech_break_medium'], marker='fx_engine_damage', region='hull', state='minor damage'),
            dict(threshold=0.5, generic=E['human_engine_damage_medium'], specific=E['covenant_mech_break_medium'], marker='fx_engine_damage'),
            dict(threshold=0.2, specific=E['covenant_mech_break_large'], marker='fx_engine_damage', region='hull', state='major damage'),
            *death(['hull', 'interior', 'front_left', 'front_right', 'back_left', 'back_right'], E['covenant_explosion_large'], E['revenant_body_destroyed'],
                   'fx_explosion', 0.25, E['covenant_explosion_small'], 'fx_engine_damage', flags='kills object|kills variant objects', damage_effect=E['trans_damage_large'])]),
    ]
    for i, side in enumerate(('front_left', 'front_right', 'back_left', 'back_right')):
        gm = 'garbage_wing_' + side
        r0 = dict(threshold=0.5, generic=E['covenant_mech_break_small'], marker=gm)
        if side.startswith('front'): r0.update(region=side, state='medium damage')  # back sections' medium step only shows hidden decals
        sections.append(dict(name=side, vitality=0.3, responses=[r0, dict(threshold=0.25, generic=E['covenant_mech_break_medium' if side != 'back_right' else 'covenant_mech_break_small'],
                                                                          marker=gm, region=side, state='major damage')]))
    materials = [('hull', 0), ('front_left', 1), ('front_right', 2), ('back_left', 3), ('back_right', 4)]
    ops = [{'op': 'clear', 'tag': md, 'block': 'Block:variants'}] + variant_ops(md, 'default', regions, objects, looping=looping)
    ops += damage_ops(md, 400, 'hard_metal_thick_cov_ghost', materials, sections)
    ops += target_ops(md, [('target_driver', 0.25), ('target_passenger', 0.25), ('target_hull_left', 0.3), ('target_hull_right', 0.3),
                           ('target_wing_left', 0.25), ('target_wing_right', 0.25), ('target_back_left', 0.25), ('target_back_right', 0.25)])
    A = O + 'Block:attachments'
    for i, mk in ((0, 'engine'), (1, 'engine'), (2, 'engine'), (3, 'engine'), (4, 'fx_boost_light')):
        ops.append({'op': 'set', 'tag': vh, 'field': A + '[%d]/marker' % i, 'value': mk})
    ops.append({'op': 'set', 'tag': vh, 'field': O + 'bounding offset', 'value': '0,0,0'})  # radius is computed (0); ghost offset ignored
    print(kit.edit(ops, 'revenant_damage'))
    return regions


def turrets_models():
    out = {}
    for t, xmlname, gmat, regs in (('chin', 'falcon_chin_gun', 'hard_metal_thick_hum_hornet', ['default']),
                                   ('side_l', 'falcon_side_gun_left', 'hard_metal_thick_hum_hornet', ['default']),
                                   ('side_r', 'falcon_side_gun_right', 'hard_metal_thick_hum_hornet', ['default']),
                                   ('mortar', 'revenant_plasma_turret', 'hard_metal_thick_cov_ghost', ['default', 'interior'])):
        c = T[t]; md = wp(c['root'], c['name'] + '.model')
        regions = reach_states(kit.WORK / 'reach-xml' / (xmlname + '.model.xml'), regs)
        # Reach turrets: one 'body' section (vitality 500), no responses; the parent's death response kills them (kills variant objects)
        ops = [{'op': 'clear', 'tag': md, 'block': 'Block:variants'}] + variant_ops(md, 'default', regions, [])
        ops += damage_ops(md, 500, gmat, [(m, 0) for m in sorted(set(c['collision_material'].values()))],
                          [dict(name='body', vitality=1, responses=[dict(threshold=0, region='default', state='destroyed')])])
        vh = wp(c['root'], c['name'] + '.vehicle')
        ops.append({'op': 'set', 'tag': vh, 'field': O + 'bounding offset', 'value': '0,0,0'})  # radius is computed (0); donor offset ignored
        if t.startswith('side'):
            # stock Warthog-gunner damage seat -> this turret's gunner seat label and its own region
            DS = DI + 'Block:damage seats'
            n = int(next(l for l in kit.dump(md).read_text().splitlines() if l.startswith(DS + '\t')).split('\t')[2])
            ops += [{'op': 'remove', 'tag': md, 'block': DS, 'index': i} for i in range(n - 1, 0, -1)]  # keep only the first (gunner) entry
            ops += [
                    {'op': 'set', 'tag': md, 'field': DS + '[0]/seat label', 'value': 'turret_g'},
                    {'op': 'set', 'tag': md, 'field': DS + '[0]/Block:region-specific-damage[0]/damage region name', 'value': 'default'}]
        print(kit.edit(ops, t + '_damage')); out[t] = regions
    return out


def effect_copies():
    """Stock running effects whose internal locations name Hornet/Ghost-only markers: unchanged-content copies with the
    location markers renamed to the Falcon's / Revenant's own Reach markers, and the attachments pointed at the copies."""
    HF = wp('objects', 'vehicles', 'hornet', 'fx', 'running'); GF = wp('objects', 'vehicles', 'ghost', 'fx', 'running')
    jobs = [(wp(HF, 'running.effect'), wp(FAL, 'fx', 'running.effect'), {'fx_running_light_red': 'fx_running_lights_left',
             'fx_running_light_amber': 'fx_running_lights_right', 'fx_running_light_white': 'fx_bay_light', 'fx_floodlight': 'fx_headlight',
             'fx_floodlight_light_volume': 'fx_headlight_light', 'fx_landing_light': 'light_landing'}, wp(FAL, 'reach_falcon.vehicle'), [4]),
            (wp(GF, 'antigrav_lift.effect'), wp(REV, 'fx', 'antigrav_lift.effect'), {'fx_antigrav_rear': 'fx_antigrav_back'}, wp(REV, 'reach_revenant.vehicle'), [5]),
            (wp(GF, 'boost.effect'), wp(REV, 'fx', 'boost.effect'), {'fx_antigrav_light': 'fx_boost_light'}, wp(REV, 'reach_revenant.vehicle'), [8])]
    ops = []
    for src, dst, ren, vh, atts in jobs:
        locs = [l.split('\t') for l in kit.dump(src).read_text().splitlines() if l.startswith('Block:locations[') and '/marker name\t' in l]
        ops.append({'op': 'copy', 'from': src, 'to': dst, 'overwrite': True})
        for f, _, v in locs:
            if v in ren: ops.append({'op': 'set', 'tag': dst, 'field': f, 'value': ren[v]})
        ops += [{'op': 'set', 'tag': vh, 'field': O + 'Block:attachments[%d]/type' % i, 'value': dst} for i in atts]
    print(kit.edit(ops, 'effect_copies'))


if __name__ == '__main__':
    what = sys.argv[1]; rep = {}
    if what == 'effects': effect_copies(); sys.exit()
    if what in ('falcon', 'all'): rep['falcon'] = falcon()
    if what in ('revenant', 'all'): rep['revenant'] = revenant()
    if what in ('turrets', 'all'): rep['turrets'] = turrets_models()
    (kit.WORK / 'vehicle-session' / ('damage-%s.json' % what)).write_text(json.dumps(dict(states=rep, notes=DAMAGE_NOTES), indent=1))
