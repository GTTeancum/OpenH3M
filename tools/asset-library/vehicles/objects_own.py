"""Falcon / Revenant on their own Reach skeletons: .model and .vehicle tags (ManagedBlam via TagEdit).

Starts from stock H3 donor tags (hornet = VTOL type, ghost = alien scout type, the same physics types the working
Forge World port uses), then points them at the new render/collision/physics/animation tags, uses the Reach seat
markers with H3 rider poses (labels as in the Forge World port), and copies Reach values (official HREK tags
falcon.vehicle / revenant.vehicle / falcon.model / revenant.model) into the H3 fields that have the same meaning.
Usage: python objects_own.py <falcon|revenant>
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import kit
from build import V, wp, BS

PT = 'Struct:physics types[0]/'
U = 'Struct:unit[0]/'
SEAT = U + 'Block:seats[%d]/'
VITALITY = {'falcon': 500, 'revenant': 400}  # Reach model 'new damage info' body maximum vitality


def seat_ops(tag, i, marker=None, entry=None, camera=None, label=None, flags=None, ai=None, boarding=None):
    o = []
    for field, val in (('marker name', marker), ('entry marker(s) name', entry), ('Struct:unit camera[0]/camera marker name', camera),
                       ('label', label), ('flags', flags), ('ai seat type', ai), ('boarding seat', boarding)):
        if val is not None:
            o.append({'op': 'set', 'tag': tag, 'field': SEAT % i + field, 'value': str(val)})
    return o


def main(v):
    c = V[v]; r, n, d, dn = c['root'], c['name'], c['donor'], c['donor_name']
    md, vh = wp(r, n + '.model'), wp(r, n + '.vehicle')
    ops = [{'op': 'copy', 'from': wp(d, dn + '.model'), 'to': md, 'overwrite': True},
           {'op': 'set', 'tag': md, 'field': 'render model', 'value': wp(r, n + '.render_model')},
           {'op': 'set', 'tag': md, 'field': 'collision model', 'value': wp(r, n + '.collision_model')},
           {'op': 'set', 'tag': md, 'field': 'physics_model', 'value': wp(r, n + '.physics_model')},
           {'op': 'set', 'tag': md, 'field': 'animation', 'value': wp(r, n + '.model_animation_graph')},
           {'op': 'set', 'tag': md, 'field': 'lod_render_model', 'value': ''},
           {'op': 'clear', 'tag': md, 'block': 'Block:variants'},
           {'op': 'set', 'tag': md, 'field': 'Block:new damage info[0]/Struct:body[0]/maximum vitality', 'value': str(VITALITY[v])},
           {'op': 'copy', 'from': wp(d, dn + '.vehicle'), 'to': vh, 'overwrite': True},
           {'op': 'set', 'tag': vh, 'field': U + 'Struct:object[0]/model', 'value': md},
           {'op': 'set', 'tag': vh, 'field': U + 'Struct:object[0]/bounding radius', 'value': '0'},  # 0 = computed from the model
           # Donor (hornet missiles / ghost guns) weapons removed: the Reach chin/side guns and plasma mortar are separate work.
           {'op': 'clear', 'tag': vh, 'block': U + 'Block:weapons'}]
    if v == 'falcon':
        ops += seat_ops(vh, 0, 'falcon_d', 'falcon_d_enter')
        ops += seat_ops(vh, 1, 'falcon_p_l1', 'falcon_p_l1_enter', 'falcon_p_l1_camera')
        ops += seat_ops(vh, 2, 'falcon_p_r1', 'falcon_p_r1_enter', 'falcon_p_r1_camera')
        ops += seat_ops(vh, 3, 'falcon_b_d_l', 'falcon_b_d_l_enter')
        ops += seat_ops(vh, 4, 'falcon_b_d_r', 'falcon_b_d_r_enter')
        ops += [{'op': 'remove', 'tag': vh, 'block': U + 'Block:seats', 'index': 6},
                {'op': 'remove', 'tag': vh, 'block': U + 'Block:seats', 'index': 5},
                {'op': 'duplicate', 'tag': vh, 'block': U + 'Block:seats', 'index': 1},
                {'op': 'duplicate', 'tag': vh, 'block': U + 'Block:seats', 'index': 2}]
        ops += seat_ops(vh, 5, 'falcon_p_l2', 'falcon_p_l2_enter', 'falcon_p_l2_camera')
        ops += seat_ops(vh, 6, 'falcon_p_r2', 'falcon_p_r2_enter', 'falcon_p_r2_camera')
        T = PT + 'Block:type-vtol[0]/'
        vals = {'Struct:turning control[0]/maximum left turn': 3, 'Struct:turning control[0]/maximum right turn (negative)': -3,
                'Struct:turning control[0]/turn rate': 60, 'left lift marker': 'phy_thrust_left_front',
                'right lift marker': 'phy_thrust_right_front', 'thrust marker': 'thrust', 'maximum up acceleration': 6,
                'maximum turn acceleration': 5, 'turn acceleration gain': 30,
                # Reach has low- and high-speed parameter sets; H3 has one. The high-speed (cruise) set is used.
                'rotor damping': 5.5, 'maximum left acceleration': 6, 'maximum forward acceleration': 6, 'drag coeficient': 0.03,
                'constant deceleration': 0.5, 'magic angular acc exp': 1.2, 'magic angular acc scale': 10, 'magic angular acc k': 0.7,
                'lift angles acc': 360, 'render lift angles acc': 360, 'prop rotation speed': '2,4'}
        ops += [{'op': 'set', 'tag': vh, 'field': T + k, 'value': str(val)} for k, val in vals.items()]
    else:
        ops += seat_ops(vh, 0, 'revenant_d', 'revenant_d_enter')
        ops += seat_ops(vh, 1, 'revenant_p', 'revenant_p_enter', 'revenant_p_camera', 'warthog_p',
                        'third person camera|allows weapons|ai firing disabled by max acceleration', 'passenger', -1)
        ops += seat_ops(vh, 2, 'revenant_b_d', 'revenant_b_d_enter', None, 'ghost_b_d', 'third person camera|boarding seat|boarding enters seat', None, 0)
        ops += seat_ops(vh, 3, 'revenant_b_p', 'revenant_b_p_enter', None, 'warthog_b_p', 'third person camera|boarding seat', None, 1)
        ops += [{'op': 'remove', 'tag': vh, 'block': U + 'Block:seats', 'index': 4}]
        T = PT + 'Block:type-alien_scout[0]/'
        vals = {'Struct:steering control[0]/overdampen cusp angle': 15, 'Struct:steering control[0]/overdampen exponent': 2,
                'maximum forward speed': 6, 'maximum reverse speed': 3, 'speed acceleration': 6, 'speed deceleration': 8,
                'maximum left slide': 4.8, 'maximum right slide': 4.8, 'slide acceleration': 4, 'slide deceleration': 3,
                'drag coeficient': 0.008, 'torque scale': 1.8,
                'Struct:engine gravity function[0]/min anti gravity engine speed': 0.5,
                'Struct:engine gravity function[0]/max anti gravity engine speed': 2,
                'Struct:engine gravity function[0]/engine speed acceleration': 0.5,
                'Struct:engine gravity function[0]/maximum vehicle speed': 4,
                'Struct:contrail gravity function[0]/min anti gravity engine speed': 0.5,
                'Struct:contrail gravity function[0]/max anti gravity engine speed': 2,
                'Struct:contrail gravity function[0]/engine speed acceleration': 2.5,
                'Struct:contrail gravity function[0]/maximum vehicle speed': 8.5}
        ops += [{'op': 'set', 'tag': vh, 'field': T + k, 'value': str(val)} for k, val in vals.items()]
        AG = 'Struct:havok vehicle physics[0]/Block:anti gravity points'
        points = ['antigrav_front_left_wing', 'antigrav_front_right_wing', 'antigrav_front_left', 'antigrav_front_right',
                  'antigrav_back_left', 'antigrav_back_right']
        ops += [{'op': 'clear', 'tag': vh, 'block': AG}, {'op': 'add', 'tag': vh, 'block': AG, 'count': len(points)}]
        for i, m in enumerate(points):
            # Reach: strength 1, height 0.35, compression damping 0.9 (H3 has one damp factor), k1 0.4, k0 0.2, radius 0.05
            for k, val in (('marker name', m), ('antigrav strength', 1), ('antigrav height', 0.35), ('antigrav damp factor', 0.9),
                           ('antigrav normal k1', 0.4), ('antigrav normal k0', 0.2), ('radius', 0.05)):
                ops.append({'op': 'set', 'tag': vh, 'field': AG + '[%d]/' % i + k, 'value': str(val)})
    print(kit.edit(ops, v + '_objects_own'))
    for t in (md, vh):
        kit.dump(t, c['work'] / ('final-' + t.split(BS)[-1] + '.txt'))


if __name__ == '__main__':
    main(sys.argv[1])
