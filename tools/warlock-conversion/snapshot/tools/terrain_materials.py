"""Bind MCC terrain layers to matching original-disc shader templates."""
import struct
import xml.etree.ElementTree as ET
from pathlib import Path
from cache_reader import Cache
from string_ids import StringTable
from tag_metadata import MetadataConverter
from native_shaders import NativeShaderImporter
from assemble_scenario import field

DONORS = {'_0_1_1_0_0_0': 'sandbox.map', '_0_2_1_1_1_2': 'docks.map',
          '_0_2_1_1_2_0': 'chill.map', '_0_1_1_1_1_2': 'sidewinder.map'}


class TerrainImporter:
    def __init__(self, importer, disc_maps):
        self.importer, self.disc_maps = importer, Path(disc_maps)
        self.resolved, self.done = {}, {}

    def shader(self, datum):
        if datum in self.done:
            return self.done[datum]
        i, s, b = self.importer, self.importer.source, self.importer.builder
        tag = s.tags[datum & 65535]
        if tag['group'] != 'rmtr' or tag['salt'] != datum >> 16:
            raise ValueError('Invalid terrain material datum')
        root = tag['offset']
        posts = s.block(root + 40, 140)
        if len(posts) != 1 or s.u(root + 28):
            raise ValueError('Terrain requires one compiled postprocess and no editor parameters')
        post = posts[0]
        template_name = s.name(s.u(post + 12) & 65535)
        variant = template_name.rsplit('\\', 1)[-1]
        if variant not in DONORS:
            raise ValueError(f'No verified native terrain donor: {template_name}')
        donor = Cache(str(self.disc_maps / DONORS[variant]))
        try:
            native = NativeShaderImporter(donor, i, self.resolved)
            lookup = {(t['group'], donor.name(k)): (t['salt'] << 16) | k
                      for k, t in donor.tags.items()}
            target_template = lookup['rmt2', template_name]
            native_strings = StringTable(donor)
            source_template = s.tags[s.u(post + 12) & 65535]['offset']
            target_root = donor.tags[target_template & 65535]['offset']
            for offset in (72, 84, 96, 108):
                source_names = [i.source_strings.text(s.u(r)) for r in s.block(source_template + offset, 4)]
                target_names = [native_strings.text(donor.u(r)) for r in donor.block(target_root + offset, 4)]
                if source_names != target_names:
                    raise ValueError('Terrain template parameter order differs between platforms')
            options = [s.unpack('h', r)[0] for r in s.block(root + 16, 2)]
            if options != [int(value) for value in variant.split('_')[1:]]:
                raise ValueError('Terrain root options differ from template variant')
            definition = native.import_tag(lookup['rmdf', r'shaders\terrain'])
            _, template = native.import_tag(target_template)
            output = bytearray(132)
            output[:16] = b'rmt2' + bytes(8) + struct.pack('>I', template)
            overlays = s.block(post + 92, 36)
            # The three observed overlays scroll a water-ripple normal over 300s.
            # POC retains its authored static normal; reject any other animation.
            for row in overlays:
                size = s.u(row + 16)
                start = s.pointer(s.u(row + 28))
                expected = bytes.fromhex('0034000000000000000080bf0000000000000000000000000000000000000000')
                if (s.unpack('IIIf', row) != (6, 0, 0, 300.)
                        or bytes(s.data[start:start + size]) != expected):
                    raise ValueError('Terrain animation outside the documented static-ripple approximation')
            textures = bytearray()
            rows = s.block(post + 16, 28)
            if len(rows) != s.u(source_template + 108):
                raise ValueError('Terrain texture count differs from template')
            for row in rows:
                bitmap = s.u(row + 12)
                index, address, filtering, comparison, external, transform, pad, animation, pad2 = s.unpack('h4BbBhH', row + 16)
                if comparison or pad or pad2 or (animation and not overlays):
                    raise ValueError('Unsupported terrain sampler routing')
                if index != 0:
                    raise ValueError('Terrain texture array/sub-image is unsupported')
                bitmap = i.materials.bitmap(bitmap) if bitmap != 0xffffffff else bitmap
                textures.extend((b'bitm' if bitmap != 0xffffffff else b'\xff' * 4) + bytes(8)
                                + struct.pack('>IhBBBbH', bitmap, index, address, filtering, external, transform, 0))
            struct.pack_into('>III', output, 16, len(rows), b.alloc(textures), 0)
            for offset, stride, fmt, parameter_offset in ((28, 16, '4I', 72), (40, 4, 'I', 84)):
                rows = s.block(post + offset, stride)
                if len(rows) != s.u(source_template + parameter_offset):
                    raise ValueError('Terrain constant count differs from template')
                payload = b''.join(struct.pack('>' + fmt, *s.unpack(fmt, row)) for row in rows)
                struct.pack_into('>III', output, offset, len(rows), b.alloc(payload) if rows else 0, 0)
            struct.pack_into('>I', output, 52, s.u(post + 52))
            struct.pack_into('>III8h', output, 104, *s.unpack('III8h', post + 104))
            ss = ET.parse(i.reference / 'mcc/rmtr.xml').getroot()
            ds = ET.parse(i.reference / 'plugins/rmtr.xml').getroot()

            def reference(value):
                if value != s.u(root + 12):
                    raise ValueError('Unexpected terrain root dependency')
                return definition

            converter = MetadataConverter(s, b, i.source_strings, i.target_strings, reference,
                special_block=lambda at, sf, df, path: bytes(output) if sf.get('name') == 'Postprocess' else None)
            payload = bytearray(converter.convert(root, ss, ds, 'rmtr:' + s.name(datum & 65535)))
            c = i.registry.cache
            matg = next(t['offset'] for t in c.tags.values() if t['group'] == 'matg')
            materials = field(ET.parse(i.reference / 'plugins/matg.xml').getroot(), 'Materials')
            target_strings = StringTable(c)
            names = {native_name: index for index, native_name in enumerate(
                target_strings.text(c.u(row)) for row in c.block(matg + int(materials.get('offset'), 0),
                                                               int(materials.get('elementSize'), 0)))}
            for index in range(4):
                material = i.source_strings.text(s.u(root + 64 + index * 4))
                if material not in names:
                    raise ValueError(f'Terrain physics material missing in retail globals: {material}')
                struct.pack_into('>h', payload, 80 + index * 2, names[material])
            owner, _ = i.registry.newtag('rmtr', payload)
            self.done[datum] = ('rmtr', owner)
            i.materials.report.append({'source': s.name(datum & 65535), 'retail_template': template_name,
                'native_donor': DONORS[variant], 'approximation': bool(overlays),
                'difference': '300-second normal-map scrolling frozen at authored initial transform' if overlays else None,
                'textures_imported': len(textures) // 24, 'all_layer_parameters_preserved': True})
            return self.done[datum]
        except Exception:
            i.failed = True
            raise
        finally:
            donor.close()
