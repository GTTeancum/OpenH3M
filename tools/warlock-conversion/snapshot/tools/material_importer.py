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
        # The accepted conversion uses this retail bitmap root as its prototype.
        root = bytearray(c.data[c.tags[8796]['offset']:c.tags[8796]['offset'] + 0xa4])
        root[0x54:0x8c] = bytes(0x38)
        owner, address = self.registry.newtag('bitm', root)
        resource = self.registry.add_resource(owner, 'bitmap_texture_interop_resource',
            {'control': control, 'raw': raw, 'root': 52,
             'fixups': [(12, 0x40000000), (52, 0x20000000)],
             'interops': [(0x20000034, 2)]})
        b.put(address + 0x60, 'III', 1, b.alloc(record), 0)
        b.put(address + 0x8c, 'III', 1, b.alloc(struct.pack('>II', resource, 0)), 0)
        b.put(address + 0x98, 'III', 0, 0, 0)
        self.done[key] = owner
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
        template_id = 392 if alpha else 0x21bb
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

    def particle_post(self, source_post):
        """Use an exact native particle template, with source named parameters."""
        s, c, b = self.source, self.target, self.builder
        template_name = s.name(s.u(source_post + 12) & 65535)
        alias = PARTICLE_ALIASES.get(template_name.rsplit('\\', 1)[-1])
        target_template = template_name.rsplit('\\', 1)[0] + '\\' + alias[0] if alias else template_name
        post = None
        for tag in c.tags.values():
            if tag['group'] != 'prt3':
                continue
            for candidate in c.block(tag['offset'] + 100, 132):
                datum = c.u(candidate + 12)
                if datum != 0xffffffff and c.name(datum & 65535) == template_name:
                    post, alias, target_template = candidate, None, template_name
                    break
                if datum != 0xffffffff and c.name(datum & 65535) == target_template:
                    post = candidate
            if post is not None and alias is None:
                break
        if post is None:
            raise ValueError(f'No exact retail particle template: {template_name}')
        source_names = self.parameters(s, self.source_strings, source_post)
        target_names = self.parameters(c, self.target_strings, post)
        if source_names != target_names or s.u(source_post + 92):
            raise ValueError('Particle parameter order differs or has animated overlays')
        textures = s.block(source_post + 16, 28)
        constants = s.block(source_post + 28, 16)
        if len(textures) != len(source_names[0]) or len(constants) != len(source_names[1]):
            raise ValueError('Particle template parameter count mismatch')
        converted = bytearray()
        for row in textures:
            bitmap = s.u(row + 12)
            index, address, filtering, comparison, external, transform, pad, block, pad2 = s.unpack('h4BbBhH', row + 16)
            if comparison or pad or pad2 or block:
                raise ValueError('Unsupported particle sampler comparison/animation routing')
            bitmap = self.bitmap(bitmap) if bitmap != 0xffffffff else bitmap
            converted.extend((b'bitm' if bitmap != 0xffffffff else b'\xff'*4) + bytes(8)
                             + struct.pack('>IhBBBbH', bitmap, index, address, filtering, external, transform, 0))
        output = bytearray(c.data[post:post + 132])
        for offset, stride, rows, payload in (
                (16, 24, textures, converted),
                (28, 16, constants, b''.join(struct.pack('>4I', *s.unpack('4I', row)) for row in constants))):
            struct.pack_into('>III', output, offset, len(rows), b.alloc(payload) if rows else 0, 0)
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
                            'approximation': bool(alias), 'difference': alias[2] if alias else None,
                            'textures_imported': source_names[0], 'constants_imported': source_names[1]})
        self.particle_aliases[source_post] = alias
        return bytes(output)

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
