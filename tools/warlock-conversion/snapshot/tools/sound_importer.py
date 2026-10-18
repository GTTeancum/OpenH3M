"""Append decoded MCC sounds to retail ugh! tables and sound resources."""
import struct
import xml.etree.ElementTree as ET
from tag_metadata import MetadataConverter


class SoundImporter:
    def __init__(self, importer, bank):
        self.importer, self.bank = importer, bank
        self.source, self.registry = importer.source, importer.registry
        self.builder, self.target = importer.builder, importer.registry.cache
        self.ss = ET.parse(importer.reference / 'mcc/ugh!.xml').getroot()
        self.ds = ET.parse(importer.reference / 'plugins/ugh!.xml').getroot()
        self.source_root = next(t['offset'] for t in self.source.tags.values() if t['group'] == 'ugh!')
        self.target_root = next(t['offset'] for t in self.target.tags.values() if t['group'] == 'ugh!')
        self.tables, self.changed, self.report = {}, set(), []
        for field in self.ds:
            if field.tag.lower() == 'tagblock':
                size = int(field.get('elementSize'), 0)
                rows = self.target.block(self.target_root + int(field.get('offset'), 0), size)
                self.tables[field.get('name')] = [bytes(self.target.data[x:x + size]) for x in rows]

    def field(self, schema, name):
        return next(x for x in schema if x.get('name') == name)

    def row(self, name, index):
        field = self.field(self.ss, name)
        rows = self.source.block(self.source_root + int(field.get('offset'), 0), int(field.get('elementSize'), 0))
        if not 0 <= index < len(rows):
            raise ValueError(f'{name}: invalid source sound-table index {index}')
        return rows[index]

    def append(self, name, payload):
        table = self.tables[name]
        index = len(table)
        table.append(payload)
        self.changed.add(name)
        return index

    def copy(self, name, index):
        if index == -1:
            return -1
        conv = MetadataConverter(self.source, self.builder, self.importer.source_strings,
                                 self.importer.target_strings, self.importer.import_tag)
        data = conv.convert(self.row(name, index), self.field(self.ss, name),
                            self.field(self.ds, name), 'ugh!/' + name)
        # Reuse existing equal scalar rows; there are no nested fields in these
        # copied tables, so equality does not compare relocated pointers.
        try:
            return self.tables[name].index(data)
        except ValueError:
            return self.append(name, data)

    def import_sound(self, datum):
        s = self.source
        at = s.tags[datum & 65535]['offset']
        flags, category, count = s.unpack('HBB', at)
        codec, first, language, priority, playback, scale = s.unpack('6h', at + 4)
        promotion, custom, extra = s.unpack('bbh', at + 16)
        if language != -1 or promotion != -1 or custom != -1 or s.u(at + 32):
            raise ValueError('Localized/promoted/custom-bank sound requires another importer')
        if extra != -1 and s.u(self.row('Extra Info', extra)):
            raise ValueError('Encoded sound permutation sections are not implemented')
        if not 0 < count <= 63:
            raise ValueError('Invalid sound pitch-range count')
        owner, address = self.registry.newtag('snd!', bytes(32))
        first_target = len(self.tables['Pitch Ranges'])
        raw, total_frames, format_key = bytearray(), [], None
        for pitch_index in range(first, first + count):
            row = self.row('Pitch Ranges', pitch_index)
            name, parameters, encoded, runtime, packed = s.unpack('4hI', row)
            first_perm, perm_count = packed & 0xfffff, (packed >> 20) & 63
            fixed_permutation = encoded == 0 and runtime == -1 and perm_count == 1
            if (encoded != -1 and not fixed_permutation) or not perm_count:
                raise ValueError(f'{s.name(datum & 65535)}: pitch range {pitch_index} '
                                 f'has encoded index {encoded}, permutation count {perm_count}')
            target_perm = len(self.tables['Permutations'])
            if target_perm + perm_count > 65535:
                raise ValueError('Retail sound permutation index exhausted')
            runtime_bit = -1 if fixed_permutation else len(self.tables['Runtime Permutation Flags']) * 8
            if runtime_bit > 32767:
                raise ValueError('Retail runtime sound flag index exhausted')
            for _ in range(0 if fixed_permutation else (perm_count + 7) // 8):
                self.append('Runtime Permutation Flags', b'\0')
            for perm_index in range(first_perm, first_perm + perm_count):
                p = self.row('Permutations', perm_index)
                import_name, skip, samples, chunk, chunks, gain, info, sound_hash = s.unpack('hhIIhbbI', p)
                decoded = self.bank.decode(sound_hash)
                key = decoded['rate'], decoded['channels']
                if format_key is not None and key != format_key:
                    raise ValueError('Mixed audio formats in one sound tag')
                format_key = key
                pcm, frames = decoded['pcm'], decoded['frames']
                if len(pcm) > 0xffffff:
                    raise ValueError('PCM permutation exceeds retail chunk size')
                target_chunk = self.append('Chunks', struct.pack('>IIiII', len(raw),
                    0x70000000 | len(pcm), -1, 0, frames))
                raw.extend(pcm)
                self.append('Permutations', struct.pack('>hhIIhbb', self.copy('Import Names', import_name),
                    skip, frames, target_chunk, 1, gain, info))
                total_frames.append(frames)
            self.append('Pitch Ranges', struct.pack('>4h2H', self.copy('Import Names', name),
                self.copy('Pitch Range Parameters', parameters), encoded, runtime_bit,
                (packed >> 16) & 0xfff0, target_perm))
        rate, channels = format_key
        codec_data = bytes(({22050: 0, 44100: 1, 32000: 2, 48000: 3}[rate],
                            {1: 0, 2: 1, 4: 2, 6: 3}[channels], 0))
        try:
            target_codec = self.tables['Codecs'].index(codec_data)
        except ValueError:
            target_codec = self.append('Codecs', codec_data)
        resource = self.registry.add_resource(owner, 'sound_resource_definition',
            {'control': b'', 'raw': bytes(raw), 'root': 0, 'fixups': [(12, 0x40000000)], 'interops': []})
        payload = struct.pack('>HBB6hbbhIII', flags, category, count, target_codec, first_target,
            -1, priority, self.copy('Playbacks', playback), self.copy('Scales', scale),
            -1, -1, -1, (max(total_frames) * 1000 + rate - 1) // rate, resource, 0)
        offset = address - self.builder.base
        self.builder.meta[offset:offset + 32] = payload
        self.report.append({'source': s.name(datum & 65535), 'datum': hex(owner),
                            'permutations': len(total_frames), 'frames': total_frames,
                            'rate': rate, 'channels': channels, 'encoding': 'PCM16 big endian'})
        return 'snd!', owner

    def stage(self):
        address = self.target_root - self.target.start + self.target.base
        for name in sorted(self.changed):
            rows = self.tables[name]
            field = self.field(self.ds, name)
            payload = b''.join(rows)
            self.builder.put(address + int(field.get('offset'), 0), 'III', len(rows),
                             self.builder.alloc(payload) if payload else 0, 0)
