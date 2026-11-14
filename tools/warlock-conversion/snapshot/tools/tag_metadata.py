"""Schema-based MCC-to-retail metadata conversion with explicit dependencies.

Resource datums and opaque data require dedicated handlers; this converter never
copies platform pointers or compiled data blindly. Callers own a scratch builder
and publish it only after the complete dependency graph has converted.
"""
import struct
from scenario_placements import FORMATS, fields, translate_flags, translate_enum


SCALARS = dict(FORMATS, uint8='B', uint16='H', uint32='I', rangef='2f', range16='2h',
               colorf='3f', vector2='2f', vector3='3f', vector4='4f', point2='2f',
               plane3='4f', plane2='3f', degree2='2f', ranged='2f', point16='2h')

# Original-disc UI defaults; ODST variants use their corresponding H3 family.
ITEM_UI = {
    # Powerhouse DMR explicitly uses the native 'br' HUD weapon family.
    # This selects pickup icon/sort only; custom DMR behavior stays authored.
    r'weap:priception\objects\weapons\rifle\dmr\dmr': (4, 0),
    # Generational Combat's mounted rocket turrets have no pickup/swap UI.
    r'weap:custom\vehicles\tgof_hce_new_rwarthog\r_turret\rturret_weapon\rturret_weapon': (0, 0),
    r'weap:custom\vehicles\tgof_warthog_turrets\rocket\weapon\rocket_turret': (0, 0),
    r'weap:objects\levels\dlc\shared\golf_club\golf_club': (0, 0),
    r'weap:objects\equipment\autoturret\autoturret_beam': (0, 0),
    r'eqip:objects\equipment\invincibility_equipment\invincibility_equipment': (0, 0),
    r'eqip:objects\equipment\invisibility_equipment\invisibility_equipment': (0, 0),
    r'eqip:objects\equipment\autoturret_equipment\autoturret_equipment': (0, 0),
    r'weap:objects\weapons\pistol\automag\automag': (6, 2),
    r'weap:objects\weapons\turret\missile_pod\missile_pod': (32, 0),
    r'weap:objects\weapons\rifle\smg_silenced\smg_silenced': (14, 0),
    r'weap:objects\weapons\rifle\plasma_rifle_red\plasma_rifle_red': (22, 0),
    # Resuscitation's vehicle-mounted weapons have no pickup/swap UI or icons.
    r'weap:objects\vehicles\spectre\turrets\plasma\plasma_turret': (0, 0),
    r'weap:objects\vehicles\spectre\turrets\shadow\shadow_turret': (0, 0),
    # Undeployed MCC variants use their retail portable turret family's UI.
    r'weap:objects\weapons\turret\machinegun_turret\machinegun_turret_undeployed': (28, 0),
    r'weap:objects\weapons\turret\plasma_cannon\plasma_cannon_undeployed': (0, 0),
}


class MetadataConverter:
    def __init__(self, source, builder, strings, target_strings, tag_reference,
                 data_reference=None, resource_reference=None, special_block=None, shader_reference=None):
        self.source, self.builder = source, builder
        self.strings, self.target_strings = strings, target_strings
        self.tag_reference = tag_reference
        self.data_reference = data_reference
        self.resource_reference = resource_reference
        self.special_block = special_block
        self.shader_reference = shader_reference
        self.applied_notes = []

    def convert(self, offset, source_schema, target_schema, path='', depth=0):
        if path == 'scnr:/Zone Set Potentially Visible Sets':
            # Old Assembly schemas split the word into Version/Flags shorts.
            # That swaps MCC 08 00 00 00 into 00 08 00 00 instead of native 8.
            # Normalize fresh schema copies only, preserving pinned references.
            import copy
            import xml.etree.ElementTree as ET
            if self.source.u(offset + 4) != 8:
                raise ValueError('Unsupported zone PVS version word; expected 8')
            schemas = []
            for schema in (source_schema, target_schema):
                schema = copy.deepcopy(schema)
                if int(schema.get('elementSize'), 0) != 44:
                    raise ValueError('Unsupported zone PVS record size')
                split = [n for n in schema if n.get('offset') is not None
                         and 4 <= int(n.get('offset'), 0) < 8]
                if [(n.tag.lower(), int(n.get('offset'), 0)) for n in split] != [('int16', 4), ('flags16', 6)]:
                    raise ValueError('Unexpected zone PVS schema version fields')
                for node in split:
                    schema.remove(node)
                ET.SubElement(schema, 'uint32', name='Native Version Word', offset='0x4')
                schemas.append(schema)
            source_schema, target_schema = schemas
        if path == 'scnr:/Cutscene Camera Points':
            # TagTool Scenario.CutsceneCameraPoint: original-only padding at
            # 0x24 separates the fixed name from position/orientation.
            flags,kind=self.source.unpack('HH',offset)
            if (int(source_schema.get('elementSize'),0)!=60
                    or int(target_schema.get('elementSize'),0)!=64
                    or flags & ~1 or kind not in range(4)):
                raise ValueError('Unexpected cutscene camera layout or flags')
            return (struct.pack('>HH',flags,kind)+bytes(self.source.data[offset+4:offset+36])
                    +bytes(4)+struct.pack('>6I',*self.source.unpack('6I',offset+36)))
        if path == 'scnr:/Cutscene Flags':
            # TagTool Scenario.CutsceneFlag: original H3 begins with four
            # padding bytes; MCC instead appends editor-folder/padding shorts.
            if (int(source_schema.get('elementSize'), 0) != 28
                    or int(target_schema.get('elementSize'), 0) != 28
                    or self.source.unpack('h', offset+26)[0]):
                raise ValueError('Unexpected cutscene marker layout/padding')
            name = self.strings.translate(self.source.u(offset), self.target_strings)
            return bytes(4) + struct.pack('>I5I', name, *self.source.unpack('5I', offset+4))
        if (path.startswith('lens:') and source_schema.get('name') == 'Reflections'
                and int(source_schema.get('elementSize'), 0) == 156
                and int(target_schema.get('elementSize'), 0) == 48):
            from lens_reflections import convert_reflection
            return convert_reflection(self.source, offset)
        if (path.startswith('char:') and source_schema.get('name') == 'Pre-Search Properties'
                and int(source_schema.get('elementSize'), 0) == 0x24
                and int(target_schema.get('elementSize'), 0) == 0x28):
            # TagTool CharacterPreSearchProperties identifies the removed
            # retail float at 0x18 as DEPRECATED. It is not MCC's final padding
            # short, despite both being called Unknown in Assembly schemas.
            if self.source.u(offset) & ~1 or self.source.unpack('h', offset + 0x22)[0]:
                raise ValueError(f'{path}: unsupported pre-search flags or padding')
            return (struct.pack('>6I', *self.source.unpack('6I', offset)) + bytes(4)
                    + struct.pack('>2I2h', *self.source.unpack('2I2h', offset + 0x18)))
        if self.special_block is not None:
            result = self.special_block(offset, source_schema, target_schema, path)
            if result is not None:
                return result
        from collision_physics import convert_collision_block
        from bsp_metadata import convert_bsp_block
        specialized = convert_bsp_block(self, offset, source_schema, target_schema, path)
        if specialized is not None:
            return specialized
        specialized = convert_collision_block(self, offset, source_schema, target_schema, path)
        if specialized is not None:
            return specialized
        from model_physics import convert_model_physics
        specialized = convert_model_physics(self, offset, source_schema, target_schema, path)
        if specialized is not None:
            return specialized
        if depth > 32:
            raise ValueError(f'{path}: metadata nesting exceeds limit')
        source_fields, target_fields = fields(source_schema), fields(target_schema)
        item_ui = ITEM_UI
        if (path in (r'weap:h2\objects\vehicles\spectre\plasma_turret\weapon\plasma_turret',
                     r'weap:h2\objects\vehicles\creep\plasma_turret\weapons\creep_turret')
                and [self.source.name(k) for k,t in self.source.tags.items() if t['group']=='scnr'] == [r'levels\multi\dune\dune']):
            # Exact Dune mounted turret has no pickup UI; no weapon behavior changes.
            for field_name in ('Private Use Font Icon', 'Private Use Font Icon (Dual)',
                               'First Person Weapon Offset Override'):
                node = next(n for (name,_),n in source_fields.items() if name==field_name)
                width = 12 if field_name=='First Person Weapon Offset Override' else 4
                at = offset + int(node.get('offset'),0)
                if any(self.source.data[at:at+width]):
                    raise ValueError('Dune mounted turret UI fields changed')
            item_ui = dict(ITEM_UI, **{path:(0,0)})
            self.applied_notes.append('Dune mounted turret: zero MCC pickup icons and centered-crosshair offset omitted; native pickup/sort and legacy scales=0, collision-sound/aged-weapon references null. Custom weapon behavior retained.')
        size = int(target_schema.get('baseSize') or target_schema.get('elementSize'), 0)
        out = bytearray(size)
        covered = set()
        for key, src in source_fields.items():
            if key in target_fields:
                continue
            at = offset + int(src.get('offset'), 0)
            if (path.startswith('lens:') and key[0] == 'Occlusion Reflection Index'
                    and self.source.unpack('i', at)[0] == 0):
                # MCC can choose a reflection for occlusion; retail uses the
                # default first reflection. Nondefault selections still reject.
                continue
            if (path == r'lens:levels\multi\cex_beavercreek\fx\sun_flare_01'
                    and key[0] == 'Occlusion Reflection Index'
                    and self.source.unpack('i', at)[0] == 26
                    and self.source.u(offset + 0x44) == 1
                    and self.source.unpack('H', offset + 0x34)[0] == 0x10):
                # Authored index 26 is outside this one-reflection legacy flare.
                # Retain its sole reflection and simple-box occlusion; retail
                # uses reflection zero. Native visual validation is required.
                continue
            if (path.startswith('scnr:/Player Starting Profile') and key[0] == 'Editor Folder Index'
                    and self.source.unpack('h', at)[0] == -1):
                continue
            if (path.startswith('scnr:/Player Starting Profile') and key[0] == 'Unknown'
                    and self.source.unpack('h', at)[0] == 0):
                continue
            if path in item_ui:
                if key[0] in ('Private Use Font Icon', 'Private Use Font Icon (Dual)'):
                    # MCC Unicode pickup icons have no retail field. Retail
                    # uses the family message index supplied below instead.
                    continue
                if key[0] == 'First Person Weapon Offset Override':
                    # Only used by MCC's optional centered-crosshair mode.
                    # Retail uses the ordinary first-person weapon offset.
                    continue
            if src.tag.lower() == 'tagblock' and self.source.u(at) == 0:
                continue
            if (path.startswith('scnr:/Scenario Resources/Resources[')
                    and key[0] == 'Decals Per-BSP Resources'
                    and src.tag.lower() == 'tagblock'
                    and int(src.get('elementSize'), 0) == 16
                    and all(self.source.u(row + 12) == 0xffffffff
                            for row in self.source.block(at, 16))):
                # MCC retains null per-BSP editor references after compilation.
                # Retail has no such array; active references still reject.
                continue
            if path.startswith('chdt:') and src.tag.lower() == 'undefined' and self.source.u(at) == 0:
                continue
            if (path.startswith('chdt:') and source_schema.get('name') == 'Text Widgets'
                    and key[0] == 'Unknown' and src.tag.lower() == 'int16'
                    and self.source.unpack('h', at)[0] == 0):
                continue
            if key[0] in ('Instance Flags 3', 'Instance Flags 4') and src.tag.lower() == 'flags32' and self.source.u(at) == 0:
                # MCC extends instance masks to 128 bits. Retail's 64-bit mask
                # can represent this block only when both high words are zero.
                continue
            raise ValueError(f'{path}/{key[0]}: source-only field requires explicit handling')
        for key, dst in target_fields.items():
            kind = dst.tag.lower()
            at = int(dst.get('offset'), 0)
            name = path + '/' + key[0]
            src = source_fields.get(key)
            if src is None:
                if (path.startswith('hlmt:') and '/Variants[' in path
                        and source_schema.get('name') == 'Permutations'
                        and int(source_schema.get('elementSize'), 0) == 24 and size == 36
                        and 24 <= at < 36 and (key[0].startswith('Runtime State Permutation Index ')
                                               or key[0] == 'Unknown')):
                    # Original antenna model stores this runtime lookup and
                    # trailing padding as zero; authored States remain intact.
                    width = 4 if kind == 'undefined' else struct.calcsize('>' + SCALARS[kind])
                    covered.update(range(at, at + width))
                    continue
                if (path.startswith(('bloc:', 'weap:', 'vehi:', 'eqip:', 'bipd:', 'crea:')) and source_schema.get('name') == 'AI Properties'
                        and source_schema.get('elementSize') == '0xC' and size == 16
                        and key[0] == 'Unknown' and kind == 'undefined' and at == 8):
                    # Zero in every original-disc AI row in these groups
                    # (183 vehicle, 426 crate, 236 weapon, 78 equipment, 80 biped).
                    # Creature rows also verified in creature-ai-padding.json.
                    covered.update(range(at, at + 4))
                    continue
                if (path.startswith('vehi:') and '/' not in path
                        and key[0] in ('Postures', 'Dialogue Variants') and kind == 'tagblock'):
                    covered.update(range(at, at + 12))
                    continue
                if (path.startswith('vehi:') and '/' not in path
                        and key[0] in ('Camera Stiffness', 'Feign Death Threshold', 'Feign Death Time',
                                       'Stunned Movement Threshold', 'Feign Death Chance', 'Feign Repeat Chance',
                                       'Spawned Actor Count', 'Spawned Velocity', 'Lipsync Attack Weight',
                                       'Lipsync Decay Weight') and kind in ('float32', 'range16')):
                    # All 266 original-disc vehicle tags leave these removed
                    # camera, actor-spawning and dialogue fields zero.
                    covered.update(range(at, at + 4))
                    continue
                if ((path.startswith('vehi:') and '/' not in path and key[0] == 'Integrated Light Toggle'
                     or path.startswith('vehi:') and '/Seats[' in path
                     and key[0] == 'Built-In Gunner') and kind == 'tagref'):
                    # Null in all original-disc vehicles, including all 739 seats.
                    out[at:at + 4] = b'\xff' * 4
                    struct.pack_into('>I', out, at + 12, 0xffffffff)
                    covered.update(range(at, at + 16))
                    continue
                if (path.startswith('hlmt:') and '/New Damage Info[' in path
                        and source_schema.get('name') == 'Nodes'
                        and int(source_schema.get('elementSize'), 0) == 2 and size == 16
                        and key[0] == 'Unknown' and kind in ('int16', 'undefined')):
                    width = 2 if kind == 'int16' else 4
                    covered.update(range(at, at + width))
                    continue
                if (path.startswith('hlmt:') and source_schema.get('name') == 'Damage Sections'
                        and int(source_schema.get('elementSize'), 0) == 0x2c and size == 0x44
                        and key[0] in ('null block here 1', 'null block here 2')
                        and kind == 'uint32' and 0x18 <= at < 0x30):
                    covered.update(range(at, at + 4))
                    continue
                if (path.startswith('hlmt:') and source_schema.get('name') == 'New Damage Info'
                        and int(source_schema.get('elementSize'), 0) == 0xa4 and size == 0x100
                        and key[0] == 'Unknown' and kind in ('undefined', 'int16')):
                    # MCC strips these zero retail fields; confirmed against
                    # original armory missile model damage metadata.
                    width = 4 if kind == 'undefined' else 2
                    covered.update(range(at, at + width))
                    continue
                machine_defaults = {
                    r'mach:objects\gear\human\industrial\krane_01\krane_01': 2,
                    'mach:objects\\levels\\multi\\s3d_sky_bridgenew\\search_light_1\\search_light_1': 2,
                    'mach:objects\\levels\\multi\\s3d_sky_bridgenew\\sbr_envelope_04_anim_01\\sbr_envelope_04_anim_01': 2,
                    'mach:objects\\levels\\multi\\s3d_sky_bridgenew\\sbr_envelope_04_anim_02\\sbr_envelope_04_anim_02': 2,
                    'mach:objects\\levels\\multi\\s3d_sky_bridgenew\\sbr_envelope_06_anim_01\\sbr_envelope_06_anim_01': 2,
                    'mach:objects\\levels\\multi\\s3d_sky_bridgenew\\sbr_envelope_06_anim_02\\sbr_envelope_06_anim_02': 2,
                    'mach:objects\\levels\\multi\\s3d_sky_bridgenew\\sbr_panel_fabric_01_anim_01\\sbr_panel_fabric_01_anim_01': 2,
                    'mach:objects\\levels\\multi\\s3d_sky_bridgenew\\sbr_panel_fabric_01_anim_02\\sbr_panel_fabric_01_anim_02': 2,
                    'mach:objects\\levels\\multi\\s3d_sky_bridgenew\\sbr_panel_fabric_01_anim_03\\sbr_panel_fabric_01_anim_03': 2,
                    'mach:objects\\levels\\multi\\s3d_sky_bridgenew\\sbr_panel_fabric_b_anim_01\\sbr_panel_fabric_b_anim_01': 2,
                    'mach:objects\\levels\\multi\\s3d_sky_bridgenew\\sbr_panel_fabric_b_anim_02\\sbr_panel_fabric_b_anim_02': 2,
                    'mach:objects\\levels\\multi\\s3d_sky_bridgenew\\sbr_lift_cabin_01\\sbr_lift_cabin_01': 1,
                    r'mach:objects\gear\human\residential\y_set_fan_small_a\y_set_fan_small_a': 2,
                    r'mach:objects\gear\human\industrial\elongation_conveyor\elongation_conveyor': 0,
                    r'mach:objects\levels\solo\020_base\security_red_light\security_red_light': 2,
                }
                # Dune's U13 machines omit the same retail response/padding.
                # All supplied native platforms use pause-until-crushed (0).
                # Restrict defaults to the audited map and exact machine roots.
                if any(tag['group'] == 'scnr' and self.source.name(k) == r'levels\multi\dune\dune'
                       for k, tag in self.source.tags.items()):
                    machine_defaults.update({
                        'mach:levels\\objects\\multi\\dune\\base_lights\\base_lights': 1,
                        'mach:levels\\objects\\multi\\dune\\teleporter_switch\\teleporter_switch': 1,
                        'mach:objects\\multi\\2way_teleporter_collapsable\\2way_teleporter_collapsable': 1,
                        'mach:levels\\objects\\covenant\\military\\cov_lookout_tower\\cov_watchtower_base\\cov_watchtower_base': 1,
                        'mach:levels\\objects\\covenant\\military\\cov_lookout_tower\\cov_watchtower_pod\\cov_watchtower_pod': 1,
                        'mach:h2\\scenarios\\objects\\multi\\dune\\dune_gate\\dune_gate': 1,
                        'mach:h2\\scenarios\\objects\\covenant\\military\\cov_lookout_tower\\cov_watchtower_base\\cov_watchtower_base': 1,
                        'mach:h2\\scenarios\\objects\\covenant\\military\\cov_lookout_tower\\cov_watchtower_pod\\cov_watchtower_pod': 1,
                    })
                if (path in machine_defaults
                        and ((key[0] == 'Collision Response' and kind == 'enum16')
                             or (key[0] == 'Unknown' and at == 0x1a6 and kind == 'int16'))):
                    if self.source.unpack('H', offset+0x190)[0] != machine_defaults[path]:
                        raise ValueError('Audited machine type changed')
                    # Original Warehouse fans/doors and High Ground's gate use
                    # pause-until-crushed (0). MCC omits this retail setting.
                    struct.pack_into('>h', out, at, 0)
                    self.applied_notes.append(f'{path}: retail-only {key[0]} defaults to0; Collision Response0 is Pause Until Crushed.')
                    covered.update(range(at, at+2))
                    continue
                if path in item_ui:
                    defaults = {'OLD Message Index': ('h', item_ui[path][0]), 'Sort Order': ('h', item_ui[path][1]),
                                'OLD Multiplayer On-Ground Scale': ('f', 0),
                                'OLD Campaign On-Ground Scale': ('f', 0)}
                    if key[0] in defaults:
                        fmt, value = defaults[key[0]]
                        struct.pack_into('>' + fmt, out, at, value)
                        covered.update(range(at, at + struct.calcsize(fmt)))
                        continue
                    if key[0] in ('Collision Sound', 'Aged Weapon'):
                        out[at:at + 4] = b'\xff' * 4
                        struct.pack_into('>I', out, at + 12, 0xffffffff)
                        covered.update(range(at, at + 16))
                        continue
                if (path.startswith('hlmt:') and source_schema.get('name') == 'Variants'
                        and int(source_schema.get('elementSize'), 0) == 48 and size == 56
                        and kind == 'undefined' and at in (48, 52)):
                    covered.update(range(at, at + 4))
                    continue
                if (path.startswith('hlmt:') and source_schema.get('name') == 'Regions'
                        and int(source_schema.get('elementSize'), 0) == 20 and size == 24
                        and at in (20, 22)):
                    # MCC omits retail's region sorting override and padding.
                    # Neutral order is zero (no camera-relative override).
                    covered.update(range(at, at + 2))
                    continue
                if (path.startswith('hlmt:') and source_schema.get('name') == 'Permutations'
                        and int(source_schema.get('elementSize'), 0) == 24 and size == 36
                        and at >= 24 and self.source.u(offset + 12) == 0):
                    # Retail runtime-state lookup/padding is zero for stateless
                    # permutations, confirmed against native model records.
                    width = 4 if kind == 'undefined' else struct.calcsize('>' + SCALARS[kind])
                    covered.update(range(at, at + width))
                    continue
                if kind == 'tagblock' and key[0] in ('Predicted Resources', 'Predicted Bitmaps'):
                    covered.update(range(at, at + 12))
                    continue
                raise ValueError(f'{name}: retail-only field needs a default')
            compatible_flags = src.tag.lower().startswith('flags') and kind.startswith('flags')
            if src.tag.lower() != kind and not compatible_flags:
                raise ValueError(f'{name}: source/retail field types differ')
            read = offset + int(src.get('offset'), 0)
            if kind == 'ascii':
                width = int(dst.get('size'), 0)
                if src.get('size') != dst.get('size'):
                    raise ValueError(f'{name}: string field size differs')
                out[at:at + width] = self.source.data[read:read + width]
            elif kind == 'hexstring' and '/Seam Identifiers[' in path and key[0] == 'ID':
                # Opaque seam identity, matched byte-for-byte across BSPs.
                width = int(src.get('size'), 0)
                if width != 16 or int(dst.get('size'), 0) != width:
                    raise ValueError('Unexpected seam identifier size')
                out[at:at + width] = self.source.data[read:read + width]
            elif kind == 'tagblock':
                stride = int(src.get('elementSize'), 0)
                rows = self.source.block(read, stride)
                if len(rows) > 1000000:
                    raise ValueError(f'{name}: excessive block count')
                payload = b''.join(self.convert(row, src, dst, name + f'[{i}]', depth + 1)
                                   for i, row in enumerate(rows))
                pointer = self.builder.alloc(payload) if payload else 0
                struct.pack_into('>III', out, at, len(rows), pointer, 0)
                width = 12
            elif kind == 'tagref':
                datum = self.source.u(read + 12)
                if datum == 0xffffffff:
                    out[at:at + 4] = b'\xff' * 4
                    struct.pack_into('>I', out, at + 12, datum)
                else:
                    group, target = self.tag_reference(datum)
                    if len(group) != 4 or target == 0xffffffff:
                        raise ValueError(f'{name}: invalid resolved tag reference')
                    out[at:at + 4] = group.encode('ascii')
                    struct.pack_into('>I', out, at + 12, target)
                width = 16
            elif kind == 'dataref':
                count = self.source.u(read)
                if count:
                    if self.data_reference is None:
                        raise ValueError(f'{name}: opaque data needs a format handler')
                    payload = self.data_reference(name, self.source, read)
                    struct.pack_into('>I', out, at, len(payload))
                    struct.pack_into('>I', out, at + 12, self.builder.alloc(payload))
                width = 20
            elif kind == 'shader':
                if self.shader_reference is None:
                    raise ValueError(f'{name}: native shader needs a dedicated handler')
                pointer = self.shader_reference(self.source.u(read), src.get('type'))
                struct.pack_into('>I', out, at, pointer)
                width = 4
            elif kind == 'undefined':
                if self.source.u(read):
                    raise ValueError(f'{name}: nonzero unknown field')
                width = 4
            else:
                fmt = SCALARS.get(kind)
                if kind == 'colorf' and dst.get('alpha') == 'true':
                    if src.get('alpha') != 'true':
                        raise ValueError(f'{name}: color alpha layout differs')
                    fmt = '4f'
                if fmt is None:
                    raise ValueError(f'{name}: unsupported field type {kind}')
                values = self.source.unpack(SCALARS[src.tag.lower()] if compatible_flags else fmt, read)
                if kind == 'stringid':
                    values = (self.strings.translate(values[0], self.target_strings),)
                elif kind == 'datum' and values[0] != 0xffffffff:
                    if path.startswith('scnr:/Light Volumes[') and key[0] == 'Unique ID':
                        pass  # Authored placement identity, not a resource handle.
                    elif self.resource_reference is None:
                        raise ValueError(f'{name}: resource datum needs conversion')
                    else:
                        values = (self.resource_reference(name, values[0]),)
                elif kind.startswith('flags'):
                    if path.startswith('effe:') and source_schema.get('name') == 'Particle Systems' and key[0] == 'Flags':
                        # MCC enhanced-graphics near-fade override has no retail
                        # graphics mode. Other particle behavior bits still map.
                        values = (values[0] & ~(1 << 14),)
                    if path.startswith('phmo:') and source_schema.get('baseSize') and key[0] == 'Flags':
                        # This describes the serialized pointer width. Nested
                        # shapes must independently pass their layout handlers.
                        values = (values[0] & ~4,)
                    dune_model_flag = (key[0]=='Flags' and kind=='flags8'
                        and path.startswith(r'hlmt:h2\objects\vehicles\creep\creep/Variants[')
                        and source_schema.get('name')=='Permutations'
                        and int(source_schema.get('elementSize'),0)==24 and size==36
                        and [self.source.name(k) for k,t in self.source.tags.items() if t['group']=='scnr']==[r'levels\multi\dune\dune'])
                    retained_flag = values[0]&2 if dune_model_flag else 0
                    if retained_flag:
                        self.applied_notes.append(f'{path}: undocumented permutation flag bit1 preserved unchanged, matching original H3 layout and native Zanzibar elite precedent.')
                    # TagTool Model.Permutation.FlagsValue has Bit1 on both
                    # platforms; original Zanzibar elite has14 matching rows.
                    # Preserve this undocumented bit, do not discard it.
                    try:
                        values = (translate_flags(values[0]&~retained_flag, src, dst)|retained_flag,)
                    except ValueError as error:
                        raise ValueError(f'{name}: {error}') from error
                elif kind.startswith('enum'):
                    statistic_alias = next((pair for token, pair in (
                        ('automag', ('Automag', 'Magnum')),
                        ('smg_silenced', ('Silenced SMG', 'SMG')),
                        ('plasma_rifle_red', ('Brute Plasma Rifle', 'Plasma Rifle')))
                        if token in path), None)
                    if (statistic_alias and key[0] in ('Damage Effect Reporting Type', 'Damage Reporting Type')
                            and any(x.get('name') == statistic_alias[0] and int(x.get('value'), 0) == values[0] for x in src)):
                        # Retail statistics use the corresponding weapon family.
                        values = (int(next(x for x in dst if x.get('name') == statistic_alias[1]).get('value'), 0),)
                    else:
                        values = (translate_enum(values[0], src, dst),)
                struct.pack_into('>' + fmt, out, at, *values)
                width = struct.calcsize('>' + fmt)
            if at + width > size or covered.intersection(range(at, at + width)):
                raise ValueError(f'{name}: overlapping or out-of-bounds schema field')
            covered.update(range(at, at + width))
        if len(covered) != size:
            raise ValueError(f'{path}: schema leaves {size-len(covered)} bytes undescribed')
        return bytes(out)
