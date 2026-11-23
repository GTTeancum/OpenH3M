"""Turret .model / .vehicle / .weapon / .projectile / .damage_effect tags from stock H3 donors + Reach values (TagEdit).

Donors (stock Halo 3): side guns = Warthog chaingun turret (gunner seat + boarding seat, chaingun weapon, bullet);
chin gun and plasma mortar = Wraith mortar turret (seatless child driven by the parent's gunner seat: unit flags
'controlled by parent gunner|parent's primary weapon', the same flags Reach's chin gun and mortar use).
Effects, sounds, HUD and impact materials stay the donors' stock Halo 3 ones.
Usage: python turret_objects.py <chin|side_l|side_r|mortar|all>
"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import kit, xml_flat
from build import wp, BS
from turrets import T, TW

U = 'Struct:unit[0]/'
STOCK = dict(chaingun=wp('objects', 'vehicles', 'warthog', 'turrets', 'chaingun'), mortar=wp('objects', 'vehicles', 'wraith', 'turrets', 'mortar'))
B = 'Block:barrels[0]/'; F = B + 'Struct:firing[0]/'; AA = 'Struct:weapon aim assist[0]/'
# (H3 field, value, Reach source field) - HREK falcon_machinegun.weapon, falcon_chin_gun.weapon, revenant_plasma_turret.weapon
WEAPON = {
 'side': [('Block:new triggers[0]/behavior', 'spew', 'new triggers[0]/behavior'), (F + 'rounds per second', '12,12', 'barrels[0]/rounds per second'),
          (F + 'acceleration time', 1.25, 'barrels[0]/firing/acceleration time'), (F + 'deceleration time', 2, 'barrels[0]/firing/deceleration time'),
          (F + 'blurred rate of fire', 0.75, 'barrels[0]/blurred rate of fire'), (F + 'fire recovery time', 0.333333, 'barrels[0]/fire recovery time'),
          (B + 'Struct:firing error[0]/deceleration time', 0.75, 'barrels[0]/firing error/deceleration time'), (B + 'error angle', '0.5,1', 'barrels[0]/error angle'),
          (B + 'rounds between tracers', 3, 'barrels[0]/rounds between tracers'), (B + 'heat generated per round', 0.03665, 'barrels[0]/heat generated per round'),
          ('heat recovery threshold', 0.01, 'heat recovery threshold'), ('overheated threshold', 1, 'overheated threshold'),
          ('heat loss per second', 0.3, 'heat loss per second'), ('overheated heat loss per second', 0.3, 'overheated heat loss per second'),
          (AA + 'autoaim angle', 4, 'autoaim angle'), (AA + 'autoaim range', 50, 'autoaim range'), (AA + 'autoaim falloff range', 25, 'autoaim falloff range'),
          (AA + 'magnetism angle', 8, 'magnetism angle'), (AA + 'magnetism range', 50, 'magnetism range'),
          (AA + 'magnetism falloff range', 25, 'magnetism falloff range'), (AA + 'deviation angle', 4, 'deviation angle')],
 'chin': [('Block:new triggers[0]/behavior', 'spew', 'new triggers[0]/behavior'), (F + 'rounds per second', '10,10', 'barrels[0]/rounds per second'),
          (F + 'blurred rate of fire', 0.5, 'barrels[0]/blurred rate of fire'), (F + 'shots per fire', '5,5', 'barrels[0]/shots per fire'),
          (F + 'fire recovery time', 0.25, 'barrels[0]/fire recovery time'),
          (B + 'Struct:firing error[0]/deceleration time', 1, 'barrels[0]/firing error/deceleration time'), (B + 'error angle', '0.5,3', 'barrels[0]/error angle'),
          ('heat recovery threshold', 0.4, 'heat recovery threshold'), ('overheated threshold', 1, 'overheated threshold'),
          ('heat loss per second', 0.3, 'heat loss per second'), ('overheated heat loss per second', 0.3, 'overheated heat loss per second'),
          (AA + 'autoaim angle', 4, 'autoaim angle'), (AA + 'autoaim range', 100, 'autoaim range'), (AA + 'autoaim falloff range', 50, 'autoaim falloff range'),
          (AA + 'magnetism angle', 8, 'magnetism angle'), (AA + 'magnetism range', 100, 'magnetism range'),
          (AA + 'magnetism falloff range', 50, 'magnetism falloff range'), (AA + 'deviation angle', 4, 'deviation angle')],
 'mortar': [('Block:new triggers[0]/behavior', 'latch', 'new triggers[0]/behavior'), (F + 'rounds per second', '1,1', 'barrels[0]/rounds per second'),
            (F + 'shots per fire', '1,1', 'barrels[0]/shots per fire'), (F + 'fire recovery time', 1.5, 'barrels[0]/fire recovery time'),
            ('heat recovery threshold', 0.25, 'heat recovery threshold'), ('overheated threshold', 0.95, 'overheated threshold'),
            ('heat loss per second', 0.4, 'heat loss per second'), ('heat illumination', 1, 'heat illumination'),
            ('overheated heat loss per second', 0.33, 'overheated heat loss per second'),
            (AA + 'autoaim angle', 6, 'autoaim angle'), (AA + 'autoaim range', 36, 'autoaim range'), (AA + 'autoaim falloff range', 18, 'autoaim falloff range'),
            (AA + 'magnetism angle', 12, 'magnetism angle'), (AA + 'magnetism range', 36, 'magnetism range'),
            (AA + 'magnetism falloff range', 18, 'magnetism falloff range')],
}
PROJ = {  # same-named fields of the Reach projectile
 'side': [('initial velocity', 100), ('final velocity', 100), ('maximum range', 80), ('air damage range', '0,80'), ('water damage range', '0,10'), ('water gravity scale', 0.2)],
 'chin': [('initial velocity', 100), ('final velocity', 400), ('maximum range', 500), ('water gravity scale', 0.2)],
 'mortar': [('collision radius', 0.1), ('danger radius', 2), ('maximum range', 200), ('air gravity scale', 0.33), ('water gravity scale', 1),
            ('initial velocity', 16), ('final velocity', 8)],
}
DMG = {  # same-named fields of the Reach damage effect
 'side': [('damage lower bound', 0), ('damage upper bound', '13,14'), ('active camouflage damage', 0.2), ('instantaneous acceleration', 0.12)],
 'chin': [('radius', '0.25,0.75'), ('AOE core radius', 0.2), ('damage lower bound', 0), ('damage upper bound', '20,20'), ('active camouflage damage', 0.1),
          ('instantaneous acceleration', 1), ('rider minimum transfer damage scale', 1.5)],
 'mortar': [('radius', '0.5,1.75'), ('cutoff scale', 0.5), ('AOE core radius', 0.4), ('damage lower bound', 0), ('damage upper bound', '60,60'),
            ('active camouflage damage', 0.5), ('instantaneous acceleration', 2), ('rider minimum transfer damage scale', 2), ('AI stun radius', 3.5),
            ('AI stun bounds', '1,0.75')],
 'mortar_impact': [('radius', '0,0'), ('AOE core radius', 0), ('damage lower bound', 0), ('damage upper bound', '60,60'), ('active camouflage damage', 1),
                   ('instantaneous acceleration', 1), ('rider minimum transfer damage scale', 2)],
}


def reach_unit(name):
    rows = dict(xml_flat.flat(kit.WORK / 'reach-xml' / (name + '.vehicle.xml')))
    return float(rows.get('aiming velocity maximum') or 0), float(rows.get('aiming acceleration maximum') or 0)


def objects(t):
    c = T[t]; r, n = c['root'], c['name']; kind = 'side' if t.startswith('side') else t
    md, vh = wp(r, n + '.model'), wp(r, n + '.vehicle')
    wpn = wp(r, 'weapon', n + '.weapon'); pr = wp(r, 'weapon', n + '.projectile'); de = wp(r, 'weapon', n + '.damage_effect')
    dn = 'mortar' if kind in ('chin', 'mortar') else 'chaingun'; donor = STOCK[dn]
    dw = wp(donor, 'mortar_turret.weapon') if dn == 'mortar' else wp(donor, 'weapon', 'chaingun_turret.weapon')
    dp = wp(STOCK['mortar'], 'mortar_turret_charged.projectile') if kind == 'mortar' else wp(STOCK['chaingun'], 'weapon', 'bullet.projectile')
    dd = wp('objects', 'vehicles', 'wraith', 'damage_effects', 'wraith_mortar.damage_effect') if kind == 'mortar' else \
         wp('objects', 'vehicles', 'warthog', 'damage_effects', 'warthog_chaingun_bullet.damage_effect')
    phys = wp(r, n + '.physics_model') if (kit.TAGS / r / (n + '.physics_model')).exists() else ''
    ops = [{'op': 'copy', 'from': wp(donor, dn + '.model'), 'to': md, 'overwrite': True},
           {'op': 'set', 'tag': md, 'field': 'render model', 'value': wp(r, n + '.render_model')},
           {'op': 'set', 'tag': md, 'field': 'collision model', 'value': wp(r, n + '.collision_model')},
           {'op': 'set', 'tag': md, 'field': 'physics_model', 'value': phys},
           {'op': 'set', 'tag': md, 'field': 'animation', 'value': wp(r, n + '.model_animation_graph')},
           {'op': 'set', 'tag': md, 'field': 'lod_render_model', 'value': ''},
           {'op': 'clear', 'tag': md, 'block': 'Block:targets'},
           {'op': 'copy', 'from': dd, 'to': de, 'overwrite': True}]
    ops += [{'op': 'set', 'tag': de, 'field': k, 'value': str(v)} for k, v in DMG[kind]]
    ops += [{'op': 'copy', 'from': dp, 'to': pr, 'overwrite': True}]
    ops += [{'op': 'set', 'tag': pr, 'field': k, 'value': str(v)} for k, v in PROJ[kind]]
    if kind == 'mortar':
        di = wp(r, 'weapon', n + '_impact.damage_effect')
        ops += [{'op': 'copy', 'from': dd, 'to': di, 'overwrite': True}] + [{'op': 'set', 'tag': di, 'field': k, 'value': str(v)} for k, v in DMG['mortar_impact']]
        ops += [{'op': 'set', 'tag': pr, 'field': 'detonation damage', 'value': de}, {'op': 'set', 'tag': pr, 'field': 'impact damage', 'value': di}]
    else:
        # Reach's chin-gun bullet deals its damage as a small detonation (radius 0.25-0.75 m); the stock H3 bullet applies impact
        # damage on a hit, so the Reach damage effect (radius kept) is used as the impact damage.
        ops.append({'op': 'set', 'tag': pr, 'field': 'impact damage', 'value': de})
    ops += [{'op': 'copy', 'from': dw, 'to': wpn, 'overwrite': True}, {'op': 'set', 'tag': wpn, 'field': B + 'projectile', 'value': pr}]
    ops += [{'op': 'set', 'tag': wpn, 'field': k, 'value': str(v)} for k, v, _ in WEAPON[kind]]
    ops += [{'op': 'copy', 'from': wp(donor, dn + '.vehicle'), 'to': vh, 'overwrite': True},
            {'op': 'set', 'tag': vh, 'field': U + 'Struct:object[0]/model', 'value': md},
            {'op': 'set', 'tag': vh, 'field': U + 'Struct:object[0]/default model variant', 'value': 'default'},
            {'op': 'set', 'tag': vh, 'field': U + 'Struct:object[0]/bounding radius', 'value': '0'},
            {'op': 'set', 'tag': vh, 'field': U + 'Block:weapons[0]/weapon', 'value': wpn}]
    av, aa = reach_unit(c['src'])
    if av: ops += [{'op': 'set', 'tag': vh, 'field': U + 'aiming velocity maximum', 'value': str(av)},
                   {'op': 'set', 'tag': vh, 'field': U + 'aiming acceleration maximum', 'value': str(aa)}]
    S0, S1 = U + 'Block:seats[0]/', U + 'Block:seats[1]/'
    if kind == 'side':
        yaw = (-95, 105) if t == 'side_l' else (-105, 95)  # Reach gunner seat yaw minimum / maximum
        ops += [{'op': 'set', 'tag': vh, 'field': S0 + k, 'value': str(v)} for k, v in (
                    ('label', 'turret_g'),  # stock H3 machine-gun turret gunner pose (Reach seat marker is also 'turret_g')
                    ('marker name', 'turret_g'), ('entry marker(s) name', 'turret_g_enter'), ('Struct:unit camera[0]/camera marker name', 'camera'),
                    ('yaw minimum', yaw[0]), ('yaw maximum', yaw[1]), ('yaw rate bounds', '45,45'), ('pitch rate bounds', '45,45'), ('entry radius', 1),
                    ('entry marker cone angle', 70), ('entry marker facing angle', 60))]
        ops += [{'op': 'set', 'tag': vh, 'field': S1 + k, 'value': str(v)} for k, v in (
                    ('marker name', 'turret_b_g'), ('entry marker(s) name', 'turret_g_enter'), ('Struct:unit camera[0]/camera marker name', 'camera'),
                    ('entry radius', 1.9), ('entry marker cone angle', 70), ('entry marker facing angle', 60))]
        ops.append({'op': 'set', 'tag': vh, 'field': U + 'Struct:object[0]/Block:attachments[0]/marker', 'value': 'weapon'})  # stock traverse sound
        ops.append({'op': 'set', 'tag': vh, 'field': U + 'flags', 'value': 'causes passenger dialogue'})  # no 'circular aiming': Reach seat yaw is limited
    else:
        ops.append({'op': 'clear', 'tag': vh, 'block': U + 'Block:seats'})  # Reach chin gun / mortar have no seats
    print(kit.edit(ops, t + '_objects'))
    for tg in (md, vh, wpn, pr, de): kit.dump(tg, TW / c['src'] / ('final-' + tg.split(BS)[-1] + '.txt'))


if __name__ == '__main__':
    for t in (list(T) if sys.argv[1] == 'all' else [sys.argv[1]]): objects(t)
