"""Import textures and named material parameters through native retail shaders.

Compiled MCC shaders are never copied. Unavailable variants use the existing
proof's retail templates and report every unrepresented parameter explicitly.
"""
import struct
from mcc_bitmap_source import BitmapSource
from encode_bitmap import encode_bitmap_base
from string_ids import StringTable

# Explicit, reported proof-of-concept substitutions for absent disc variants.
PARTICLE_ALIASES = {
    '_0_10_0_0_1_0_1_1_0_0': ('_0_10_0_0_0_0_1_1_0_0', 'render_targets', 'LDR-only becomes LDR and HDR'),
    '_1_10_0_0_0_1_1_1_0_0': ('_1_3_0_0_0_1_1_1_0_0', 'blend_mode', 'Premultiplied alpha becomes alpha blend'),
}
DECAL_ALIASES = {
    '_0_3_0_1_1_3': ('_0_3_0_1_1_1', 'tinting', 'Fully modulated tint becomes unmodulated tint'),
    '_0_3_2_1_1_0': ('_0_3_0_1_1_0', 'render_pass', 'MCC transparent pass becomes retail pre-lighting pass'),
    '_6_3_0_1_1_1': ('_0_3_0_1_1_1', 'albedo', 'Identical untiled alpha mask uses base-map alpha'),
    '_6_3_0_1_1_3': ('_0_3_0_1_1_1', 'albedo', 'Identical untiled alpha mask uses base-map alpha; fully modulated tint becomes unmodulated'),
    '_6_3_2_1_1_3': ('_0_3_0_1_1_1', 'albedo', 'Identical untiled alpha mask uses base-map alpha; tint becomes unmodulated and pass becomes pre-lighting'),
}


class MaterialImporter:
    def __init__(self, source, registry):
        self.source, self.registry = source, registry
        self.target, self.builder = registry.cache, registry.builder
        self.bitmaps = BitmapSource(source)
        self.source_strings, self.target_strings = StringTable(source), StringTable(self.target)
        self.done = {}
        self.report = []
        self.particle_aliases = {}
        self.target_names = {(t['group'], self.target.name(i)): (t['salt'] << 16) | i
                             for i, t in self.target.tags.items()}

    def bitmap(self, datum):
        s, c, b = self.source, self.target, self.builder
        tag = datum & 65535
        key = ('bitm', s.name(tag))
        if key in self.done:
            return self.done[key]
        if key in self.target_names:
            return self.target_names[key]
        record, control, raw = encode_bitmap_base(self.bitmaps, tag)
        owner = self.bitmap_resource(record, control, raw)
        self.done[key] = owner
        return owner

    def bitmap_resource(self, record, control, raw):
        c, b = self.target, self.builder
        # Explicit single-image runtime root: resource-backed and sampleable.
        # All editor data, sequences and runtime pointers start empty. These
        # are the same non-pointer fields as the accepted bitmap prototype.
        root = bytearray(0xa4)
        struct.pack_into('>H', root, 4, 0x50)
        owner, address = self.registry.newtag('bitm', root)
        resource = self.registry.add_resource(owner, 'bitmap_texture_interop_resource',
            {'control': control, 'raw': raw, 'root': 52,
             'fixups': [(12, 0x40000000), (52, 0x20000000)],
             'interops': [(0x20000034, 2)]})
        b.put(address + 0x60, 'III', 1, b.alloc(record), 0)
        b.put(address + 0x8c, 'III', 1, b.alloc(struct.pack('>II', resource, 0)), 0)
        b.put(address + 0x98, 'III', 0, 0, 0)
        return owner

    def parameters(self, cache, strings, post):
        template = cache.tags[cache.u(post + 12) & 65535]
        if template['group'] != 'rmt2':
            raise ValueError('Shader postprocess has no render-method template')
        offset = template['offset']
        return ([strings.text(cache.u(x)) for x in cache.block(offset + 0x6c, 4)],
                [strings.text(cache.u(x)) for x in cache.block(offset + 0x48, 4)])

    def shader(self, datum):
        s, c, b = self.source, self.target, self.builder
        tag = s.tags[datum & 65535]
        if tag['group'] not in ('rmsh', 'rmfl'):
            raise ValueError(f"Material class requires dedicated handling: {tag['group']}")
        key = tag['group'], s.name(datum & 65535)
        if key in self.done:
            return 'rmsh', self.done[key]
        source_post = s.block(tag['offset'] + 40, 140)[0]
        texture_names, constant_names = self.parameters(s, self.source_strings, source_post)
        source_textures = s.block(source_post + 16, 28)
        source_constants = s.block(source_post + 28, 16)
        if len(texture_names) != len(source_textures) or len(constant_names) != len(source_constants):
            raise ValueError('Source material parameter counts differ from its template')
        options = [s.unpack('h', x)[0] for x in s.block(tag['offset'] + 16, 2)]
        alpha = tag['group'] == 'rmfl' or (len(options) > 2 and options[2] == 1)
        template_name = (r'objects\weapons\lod\shaders\lod_plasma_grenade' if alpha
                         else r'levels\dlc\lockout\shaders\metal_wall_white_flat')
        native = self.target_names.get(('rmsh', template_name))
        if native is None:
            raise ValueError(f'Required native material prototype absent: {template_name}')
        template_id = native & 65535
        retail = c.tags[template_id]['offset']
        post = c.block(retail + 40, 132)[0]
        target_texture_names, target_constant_names = self.parameters(c, self.target_strings, post)
        textures = bytearray(b''.join(c.data[x:x + 24] for x in c.block(post + 16, 24)))
        constants = bytearray(b''.join(c.data[x:x + 16] for x in c.block(post + 28, 16)))
        imported = []
        for index, name in enumerate(target_texture_names):
            source_name = 'base_map' if name == 'alpha_test_map' and name not in texture_names else name
            if source_name not in texture_names:
                continue
            row = source_textures[texture_names.index(source_name)]
            bitmap_datum = s.u(row + 12)
            if bitmap_datum == 0xffffffff:
                continue
            struct.pack_into('>I', textures, index * 24 + 12, self.bitmap(bitmap_datum))
            imported.append(source_name)
        for index, name in enumerate(target_constant_names):
            source_name = 'base_map' if name == 'alpha_test_map' and name not in constant_names else name
            if source_name in constant_names:
                values = s.unpack('4f', source_constants[constant_names.index(source_name)])
                struct.pack_into('>4f', constants, index * 16, *values)
        root = bytearray(c.data[retail:retail + 68])
        root[28:40] = bytes(12)
        owner, address = self.registry.newtag('rmsh', root)
        output_post = bytearray(c.data[post:post + 132])
        struct.pack_into('>III', output_post, 16, len(target_texture_names), b.alloc(textures), 0)
        struct.pack_into('>III', output_post, 28, len(target_constant_names), b.alloc(constants), 0)
        b.put(address + 40, 'III', 1, b.alloc(output_post), 0)
        self.done[key] = owner
        self.report.append({'source': key[1], 'retail_template': template_id,
            'approximation': True, 'textures_imported': imported,
            'unrepresented_textures': sorted(set(texture_names) - set(imported)),
            'unrepresented_constants': sorted(set(constant_names) - set(target_constant_names))})
        return 'rmsh', owner

    def particle_post(self, source_post, group='prt3'):
        """Use native particle/decal routing with source named parameters."""
        s, c, b = self.source, self.target, self.builder
        template_name = s.name(s.u(source_post + 12) & 65535)
        aliases = DECAL_ALIASES if group == 'decs' else PARTICLE_ALIASES if group == 'prt3' else {}
        alias = aliases.get(template_name.rsplit('\\', 1)[-1])
        target_template = template_name.rsplit('\\', 1)[0] + '\\' + alias[0] if alias else template_name
        post = None
        for tag in c.tags.values():
            if tag['group'] != group:
                continue
            if group == 'decs':
                containers = [row + 48 for row in c.block(tag['offset'] + 20, 116)]
            elif group == 'cntl':
                containers = [row + 0x158 for row in c.block(tag['offset'], 0x26c)]
            else:
                containers = [tag['offset'] + 100]
            for candidate in (post for container in containers for post in c.block(container, 132)):
                datum = c.u(candidate + 12)
                if datum != 0xffffffff and c.name(datum & 65535) == template_name:
                    post, alias, target_template = candidate, None, template_name
                    break
                if datum != 0xffffffff and c.name(datum & 65535) == target_template:
                    post = candidate
            if post is not None and alias is None:
                break
        if post is None:
            raise ValueError(f'No supported retail {group} template: {template_name}')
        source_names = self.parameters(s, self.source_strings, source_post)
        target_names = self.parameters(c, self.target_strings, post)
        textures = s.block(source_post + 16, 28)
        constants = s.block(source_post + 28, 16)
        if len(textures) != len(source_names[0]) or len(constants) != len(source_names[1]):
            raise ValueError('Particle template parameter count mismatch')
        baked_bitmap = None
        baked_tiles = None
        if group == 'decs' and alias and alias[1] == 'albedo':
            # Mask albedo samples alpha in untiled coordinates. It is equivalent
            # to base alpha only for the same texture, untiled and without sprites.
            base = textures[source_names[0].index('base_map')]
            mask = textures[source_names[0].index('alpha_map')]
            datum = s.u(base + 12)
            tile_values = [s.unpack('4f', constants[source_names[1].index(name)])
                           for name in ('u_tiles', 'v_tiles')]
            mask_datum = s.u(mask + 12)
            if (datum == 0xffffffff or mask_datum == 0xffffffff
                    or s.unpack('h', base + 16)[0] != 0 or s.unpack('h', mask + 16)[0] != 0
                    or s.unpack('h4BbBhH', base + 16)[3:] != (0, 0, -1, 0, 0, 0)
                    or s.unpack('h4BbBhH', mask + 16)[3:] != (0, 0, -1, 0, 0, 0)):
                raise ValueError('Decal mask requires unsupported sampler/transform routing')
            if (datum != mask_datum or any(values != (1., 1., 1., 1.) for values in tile_values)):
                if s.data[base + 18] != 0 or s.data[mask + 18] != 17:
                    raise ValueError('Decal baking requires wrap diffuse and clamp mask addressing')
                from decal_bitmap import bake
                baked_tiles = tuple(values[0] for values in tile_values)
                key = ('decal_bake', datum, mask_datum, baked_tiles)
                if key not in self.done:
                    self.done[key] = self.bitmap_resource(*bake(self.bitmaps, datum & 65535,
                                                               mask_datum & 65535, baked_tiles))
                baked_bitmap = self.done[key]
                alias = (alias[0], alias[1], 'Separate alpha mask baked into tiled diffuse; nearest sampling, 512-pixel limit, one mip; native unmodulated tint/pre-lighting pass')
            elif s.u(s.tags[datum & 65535]['offset'] + 0x54):
                raise ValueError('Decal alpha alias does not support sprites')
            # Both samples address the same pixels. Retain the mask sampler for
            # the combined texture so clamp/filter behavior preserves cutouts;
            # RGB now shares its filtering instead of its old independent sampler.
            textures[source_names[0].index('base_map')] = mask
            alias = (alias[0], alias[1], alias[2] + '; RGB shares alpha-mask sampler filtering/addressing')
            mask_index = source_names[0].index('alpha_map')
            textures = [row for index, row in enumerate(textures) if index != mask_index]
            source_names = ([name for name in source_names[0] if name != 'alpha_map'], source_names[1])
        if source_names != target_names or s.u(source_post + 92):
            raise ValueError('Particle parameter order differs or has animated overlays')
        converted = bytearray()
        for row in textures:
            bitmap = s.u(row + 12)
            index, address, filtering, comparison, external, transform, pad, block, pad2 = s.unpack('h4BbBhH', row + 16)
            if comparison or pad or pad2 or block:
                raise ValueError('Unsupported particle sampler comparison/animation routing')
            bitmap = (baked_bitmap if baked_bitmap is not None and row == mask else
                      self.bitmap(bitmap) if bitmap != 0xffffffff else bitmap)
            converted.extend((b'bitm' if bitmap != 0xffffffff else b'\xff'*4) + bytes(8)
                             + struct.pack('>IhBBBbH', bitmap, index, address, filtering, external, transform, 0))
        output = bytearray(c.data[post:post + 132])
        for offset, stride, rows, payload in (
                (16, 24, textures, converted),
                (28, 16, constants, b''.join(struct.pack('>4I', *s.unpack('4I', row)) for row in constants))):
            struct.pack_into('>III', output, offset, len(rows), b.alloc(payload) if rows else 0, 0)
        if baked_tiles is not None:
            pointer = struct.unpack_from('>I', output, 32)[0]
            for name in ('u_tiles', 'v_tiles'):
                b.put(pointer + source_names[1].index(name) * 16, '4f', 1., 1., 1., 1.)
            # Bump retains the old tiled UVs after diffuse tiling was baked.
            index = source_names[1].index('bump_map')
            x, y, z, w = s.unpack('4f', constants[index])
            b.put(pointer + index * 16, '4f', x * baked_tiles[0], y * baked_tiles[1], z, w)
        integers = s.block(source_post + 40, 4)
        payload = b''.join(struct.pack('>I', s.u(row)) for row in integers)
        struct.pack_into('>III', output, 40, len(integers), b.alloc(payload) if integers else 0, 0)
        struct.pack_into('>I', output, 52, s.u(source_post + 52))
        struct.pack_into('>III8h', output, 104, *s.unpack('III8h', source_post + 104))
        if alias and alias[1] == 'blend_mode':
            struct.pack_into('>I', output, 104, c.u(post + 104))
            index = source_names[1].index('blend_mode')
            native = c.block(post + 28, 16)[index]
            pointer = struct.unpack_from('>I', output, 32)[0]
            b.put(pointer + index * 16, '4I', *c.unpack('4I', native))
        self.report.append({'particle_template': template_name, 'retail_template': target_template,
                            'render_method_group': group,
                            'approximation': bool(alias), 'difference': alias[2] if alias else None,
                            'textures_imported': source_names[0], 'constants_imported': source_names[1]})
        self.particle_aliases[source_post] = alias
        return bytes(output)

    def decal_root(self, source_offset, payload):
        """Apply reported option aliases to each converted decal render method."""
        source_rows = self.source.block(source_offset + 20, 116)
        count, pointer = struct.unpack_from('>II', payload, 20)
        if count != len(source_rows):
            raise ValueError('Decal system count changed during conversion')
        for index, row in enumerate(source_rows):
            posts = self.source.block(row + 48, 140)
            aliases = [self.particle_aliases.get(post) for post in posts]
            if not any(aliases):
                continue
            if len(posts) != 1:
                raise ValueError('Decal alias requires one postprocess record')
            options = [int(value) for value in aliases[0][0].split('_')[1:]]
            at = pointer + index * 116 + 24 - self.builder.base
            option_count, option_pointer = struct.unpack_from('>II', self.builder.meta, at)
            if option_count != len(options):
                raise ValueError('Decal option count differs from template name')
            for option, value in enumerate(options):
                self.builder.put(option_pointer + option * 2, 'h', value)
        return payload

    def particle_root(self, source_offset, payload):
        """Keep root options/runtime flags consistent with a reported alias."""
        posts = self.source.block(source_offset + 100, 140)
        if len(posts) != 1:
            return payload
        alias = self.particle_aliases.get(posts[0])
        if alias is None:
            return payload
        options = [int(x) for x in alias[0].split('_')[1:]]
        out = bytearray(payload)
        count, pointer = struct.unpack_from('>II', out, 76)
        if count != len(options):
            raise ValueError('Particle option count differs from template name')
        for index, value in enumerate(options):
            self.builder.put(pointer + index * 2, 'h', value)
        if alias[1] == 'render_targets':
            flags = struct.unpack_from('>I', out, 16)[0]
            struct.pack_into('>I', out, 16, flags & ~(1 << 14))
        return bytes(out)
