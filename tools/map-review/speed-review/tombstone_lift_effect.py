"""Port Halo 2 Tombstone's lift effect (effects\\scenarios\\multi\\cyclotron\\hvac_steam: two rising soft-smoke layers and
one light-streak layer) and its two particle types into Halo 3 tags, and attach it to the ported lift.

Structure comes from stock Halo 3 tags (Guardian's minilift effect, the soft-smoke particle) so every Halo 3 field has
a valid default; Halo 2's values are then written in: particle textures, blend types and facing, emitter shape,
offsets, directions, and each emitter property's inputs and function (Halo 2 and Halo 3 store emitter functions in the
same layout; colour functions get Halo 3's two-colour marker byte). Halo 2's 'fire' motion maps to Halo 3's
fx\\physics_templates\\fire (same template, carried into Halo 3); 'lightweight_particle' has no Halo 3 counterpart and
uses the default template.
Usage: tombstone_lift_effect.py <hvac_steam.json from h2_effect_summary.py> [attach]"""
import json, sys
sys.path.insert(0, r'C:\Programming\GitHub\OpenH3M\.local\tombstone\tagedit')
import te
BS = chr(92)
D = BS.join(['levels', 'test', 'tombstone', 'objects', 'hp_hvac_lift_short', ''])
FX = D + 'fx' + BS
SMOKE, STREAK, EFFECT = FX + 'smoke_soft.particle', FX + 'streaks.particle', FX + 'hvac_steam.effect'
STOCK_P = BS.join(['fx', 'particles', 'atmospheric', 'soft_smoke', 'soft_smoke_large.particle'])
STOCK_FX = BS.join(['levels', 'multi', 'guardian', 'fx', 'minilift', 'minilift.effect'])
PHYS = {'effects\\particle_physics\\fire': BS.join(['fx', 'physics_templates', 'fire.particle_physics']),
        'effects\\particle_physics\\lightweight_particle': BS.join(['fx', 'physics_templates', '_default.particle_physics'])}
PARTICLE = {'effects\\generic\\smoke\\smoke_soft': SMOKE, 'effects\\generic\\sparks\\streaks': STREAK}
H3PROP = {'emission rate': 'particle emission rate', 'lifespan': 'particle lifespan', 'velocity': 'particle initial velocity',
          'angular velocity': 'particle initial rotation rate', 'size': 'particle size', 'tint': 'particle tint',
          'alpha': 'particle alpha', 'emission radius': 'emission radius', 'emission angle': 'emission angle'}
# Halo 2 emitter function inputs -> Halo 3 (no per-emitter randoms in Halo 3: emitter age/random -> system age/random)
INPUT = {0: 0, 2: 2, 3: 4, 4: 1, 5: 3, 6: 8, 7: 11}
src = json.load(open(sys.argv[1]))


def idx(text): return int(text.split(',')[0]) if text else 0


SIMPLE = 'simple' in sys.argv[2:]


def data(p, colour=False):
    b = bytearray.fromhex(p['bytes'])
    if SIMPLE and b[0] != 1:      # Halo 2 curve functions -> two-value function of the same range (test/fallback)
        b = bytearray(b[:12]); b[0] = 1; b[2] = b[3] = 0
    if colour: b[2] = 2
    b += bytes(max(0, 32 - len(b)))
    return b.hex()


ops = [{'op': 'copy', 'from': STOCK_P, 'to': SMOKE, 'overwrite': True}, {'op': 'copy', 'from': STOCK_P, 'to': STREAK, 'overwrite': True},
       {'op': 'copy', 'from': STOCK_FX, 'to': EFFECT, 'overwrite': True}]
S = 'Struct:actual shader?[0]/'
for tag, opts, bm, style, flags in ((SMOKE, [0, 3, 0, 2, 0, 0, 0, 1, 0, 0], D + 'bitmaps' + BS + 'smoke_soft.bitmap', 0, 'random u mirror|random v mirror|random starting rotation'),
                                    (STREAK, [0, 1, 0, 0, 0, 0, 0, 0, 0, 0], D + 'bitmaps' + BS + 'streaks.bitmap', 2, 'random u mirror|random v mirror')):
    ops += [{'op': 'set', 'tag': tag, 'field': 'particle billboard style', 'value': str(style)},
            {'op': 'set', 'tag': tag, 'field': 'appearance flags', 'value': flags},
            {'op': 'clear', 'tag': tag, 'block': S + 'Block:options'}, {'op': 'add', 'tag': tag, 'block': S + 'Block:options', 'count': len(opts)},
            {'op': 'clear', 'tag': tag, 'block': S + 'Block:parameters'}, {'op': 'add', 'tag': tag, 'block': S + 'Block:parameters', 'count': 1},
            {'op': 'set', 'tag': tag, 'field': S + 'Block:parameters[0]/parameter name', 'value': 'base_map'},
            {'op': 'set', 'tag': tag, 'field': S + 'Block:parameters[0]/parameter type', 'value': '0'},
            {'op': 'set', 'tag': tag, 'field': S + 'Block:parameters[0]/bitmap', 'value': bm}]
    ops += [{'op': 'set', 'tag': tag, 'field': S + f'Block:options[{i}]/short', 'value': str(v)} for i, v in enumerate(opts)]
    # Halo 2's particle-level values: colour white, alpha 1 (the stock Halo 3 template's own dim curves replaced).
    # Streaks are drawn parallel to their motion and read as long thin lines in Halo 2; aspect ratio 4 stands in
    # for that stretch (judgement, not a Halo 2 value).
    const = lambda v: '0124' + '0000' + bytes(__import__('struct').pack('<ff', v, v)).hex() + '00' * 20
    white = '01240200ffffff00' + '0000803f' + '00000000' + 'ffffff00' + '00' * 12
    for prop, val in (('color', white), ('alpha', const(1.0)), ('intensity', const(1.0)), ('aspect ratio', const(4.0 if tag == STREAK else 1.0))):
        ops += [{'op': 'set', 'tag': tag, 'field': f'Struct:{prop}[0]/Input Variable', 'value': '0'},
                {'op': 'set', 'tag': tag, 'field': f'Struct:{prop}[0]/Output Modifier', 'value': '0'},
                {'op': 'set', 'tag': tag, 'field': f'Struct:{prop}[0]/Struct:Mapping[0]/data', 'value': val}]
# effect: one looping 0.5 s event (Halo 2 timing) at the direction_up marker, three particle systems, no light volume
ops += [{'op': 'set', 'tag': EFFECT, 'field': 'Block:locations[0]/marker name', 'value': 'direction_up'},
        {'op': 'remove', 'tag': EFFECT, 'block': 'Block:events', 'index': 0},
        {'op': 'set', 'tag': EFFECT, 'field': 'loop start event', 'value': '0'},
        {'op': 'set', 'tag': EFFECT, 'field': 'Block:events[0]/delay bounds', 'value': '0,0'},
        {'op': 'set', 'tag': EFFECT, 'field': 'Block:events[0]/duration bounds', 'value': '0.5,0.5'},
        {'op': 'clear', 'tag': EFFECT, 'block': 'Block:events[0]/Block:parts'},
        {'op': 'remove', 'tag': EFFECT, 'block': 'Block:events[0]/Block:particle systems', 'index': 1}]
for _ in range(len(src) - 1):
    ops.append({'op': 'duplicate', 'tag': EFFECT, 'block': 'Block:events[0]/Block:particle systems', 'index': 0})
for i, s in enumerate(src):
    P = f'Block:events[0]/Block:particle systems[{i}]/'
    f = s['fields']
    ops += [{'op': 'set', 'tag': EFFECT, 'field': P + 'particle', 'value': PARTICLE[s['particle']]},
            {'op': 'set', 'tag': EFFECT, 'field': P + 'coordinate system', 'value': str(idx(f.get('coordinate system')))},
            {'op': 'set', 'tag': EFFECT, 'field': P + 'LOD out distance', 'value': f.get('LOD out distance') if float(f.get('LOD out distance') or 0) > 0 else '50'},   # Halo 2 0 = no distance limit
            {'op': 'set', 'tag': EFFECT, 'field': P + 'LOD feather out delta', 'value': f.get('LOD feather out delta', '20')}]
    e = s['emitters'][0]; E = P + 'Block:emitters[0]/'; ef = e['fields']
    ops += [{'op': 'set', 'tag': EFFECT, 'field': E + 'emission shape', 'value': str(idx(ef['emission shape']))},
            {'op': 'set', 'tag': EFFECT, 'field': E + 'Struct:particle movement[0]/template', 'value': PHYS.get(ef.get('particle physics'), PHYS['effects\\particle_physics\\lightweight_particle'])}]
    zero = '0124' + '00' * 30
    off = ef['translational offset']; rd = ef['relative direction']
    ops += [{'op': 'set', 'tag': EFFECT, 'field': E + 'Struct:translational offset[0]/Starting interpolant', 'value': off},
            {'op': 'set', 'tag': EFFECT, 'field': E + 'Struct:translational offset[0]/Ending interpolant', 'value': off},
            {'op': 'set', 'tag': EFFECT, 'field': E + 'Struct:translational offset[0]/Struct:Mapping[0]/data', 'value': zero},
            {'op': 'set', 'tag': EFFECT, 'field': E + 'Struct:relative direction[0]/Struct:Starting interpolant[0]/Euler angles', 'value': rd},
            {'op': 'set', 'tag': EFFECT, 'field': E + 'Struct:relative direction[0]/Struct:Ending interpolant[0]/Euler angles', 'value': rd},
            {'op': 'set', 'tag': EFFECT, 'field': E + 'Struct:relative direction[0]/Struct:Mapping[0]/data', 'value': zero}]
    for h2, h3 in H3PROP.items():
        p = e['properties'][h2]; Q = E + f'Struct:{h3}[0]/'
        ops += [{'op': 'set', 'tag': EFFECT, 'field': Q + 'Input Variable', 'value': str(INPUT.get(idx(p['input']), 0))},
                {'op': 'set', 'tag': EFFECT, 'field': Q + 'Range Variable', 'value': str(INPUT.get(idx(p.get('Range Variable')), 0))},
                {'op': 'set', 'tag': EFFECT, 'field': Q + 'Output Modifier', 'value': str(idx(p.get('Output Modifier')))},
                {'op': 'set', 'tag': EFFECT, 'field': Q + 'Output Modifier Input', 'value': str(INPUT.get(idx(p.get('Output Modifier Input')), 0))},
                {'op': 'set', 'tag': EFFECT, 'field': Q + 'Struct:Mapping[0]/data', 'value': data(p, colour=(h2 == 'tint'))}]
# attach to the lift as Halo 2 does (no marker on the attachment; the effect's own location is direction_up)
CRATE = D + 'hp_hvac_lift_short.crate'
if 'attach' in sys.argv[2:]: ops += [{'op': 'clear', 'tag': CRATE, 'block': 'Struct:object[0]/Block:attachments'}, {'op': 'add', 'tag': CRATE, 'block': 'Struct:object[0]/Block:attachments', 'count': 1},
        {'op': 'set', 'tag': CRATE, 'field': 'Struct:object[0]/Block:attachments[0]/type', 'value': EFFECT}]
print(te.edit(ops, timeout=900)[-300:])
