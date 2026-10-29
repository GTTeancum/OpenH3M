"""Resolve MCC U13 and retail Halo 3 string IDs through their actual tables.

Namespace rules follow Assembly's format definitions (reference/formats).
No raw MCC ID is copied into a retail tag. Missing retail strings are explicit.
"""
from pathlib import Path
import xml.etree.ElementTree as ET


class StringTable:
    def __init__(self, cache):
        self.cache = cache
        if cache.mcc:
            self.bits = 19
            count, base, size, index, ns_count, ns_offset = cache.unpack('6I', 0x30)
            if not 1 <= ns_count <= 256:
                raise ValueError('Unsupported MCC string namespace table')
            lengths = cache.unpack('I' * ns_count, ns_offset)
            lengths = [x & ((1 << self.bits) - 1) for x in lengths]
            total = lengths[0]
            namespaces = []
            for ns in range(1, ns_count):
                namespaces.append((ns, 0, total))
                total += lengths[ns]
            namespaces.append((0, lengths[0], total))
        else:
            self.bits = 16
            count, size, index, base = cache.unpack('4I', 0x158)
            mask = cache.u(0x46c)
            index, base = (index + mask) & 0xffffffff, (base + mask) & 0xffffffff
            definition = Path(__file__).resolve().parents[1] / 'reference/formats/H3_StringIDs.xml'
            namespaces = [(int(x.get('id'), 0), int(x.get('min', '0'), 0),
                           int(x.get('startIndex'), 0)) for x in ET.parse(definition).getroot()]
        self.namespaces = sorted(namespaces)
        if count > 1000000 or index + count * 4 > len(cache.data) or base + size > len(cache.data):
            raise ValueError('String table outside cache')
        self.strings = []
        for i in range(count):
            offset = cache.u(index + i * 4)
            if offset == 0xffffffff:
                self.strings.append(None)
                continue
            if offset >= size:
                raise ValueError('String offset outside table')
            end = cache.data.find(b'\0', base + offset, base + size)
            if end < 0:
                raise ValueError('Unterminated string')
            # Debug names include legacy non-UTF8 bytes. Latin-1 preserves every
            # byte for exact matching; never replace or normalize identifier data.
            self.strings.append(cache.data[base + offset:end].decode('latin-1'))
        self.by_text = {}
        for i, text in enumerate(self.strings):
            if text is not None:
                self.by_text.setdefault(text, self.id_for_index(i))

    def index_for_id(self, value):
        value &= (1 << (self.bits + 8)) - 1
        namespace = value >> self.bits
        candidates = [x for x in self.namespaces if x[0] <= namespace]
        if candidates and (value & ((1 << self.bits) - 1)) < candidates[-1][1]:
            candidates.pop()
        if not candidates:
            return value
        ns, minimum, start = candidates[-1]
        return value - ((ns << self.bits) | minimum) + start

    def id_for_index(self, index):
        candidates = [x for x in self.namespaces if x[2] <= index]
        if not candidates:
            return index
        ns, minimum, start = max(candidates, key=lambda x: x[2])
        return index - start + (ns << self.bits) + minimum

    def text(self, value):
        if value == 0xffffffff:
            return None
        index = self.index_for_id(value)
        if not 0 <= index < len(self.strings):
            raise ValueError(f'String ID {value:#x} resolves outside table')
        return self.strings[index]

    def translate(self, value, target):
        if value in (0, 0xffffffff):
            return value
        text = self.text(value)
        if text is None:
            raise ValueError(f'Missing retail string: {text!r} ({value:#x})')
        return target.id_for_text(text)

    def id_for_text(self, text):
        if text not in self.by_text:
            raise ValueError(f'Missing retail string: {text!r}')
        return self.by_text[text]


class WritableStringTable(StringTable):
    """Append new identifiers without changing IDs of existing strings."""
    def __init__(self, builder):
        super().__init__(builder.cache)
        self.builder = builder
        self.original_count = len(self.strings)
        self.staged = False

    def id_for_text(self, text):
        if text in self.by_text:
            return self.by_text[text]
        if self.staged:
            raise ValueError('String table already staged')
        value = self.id_for_index(len(self.strings))
        if value > 0xffffff or self.index_for_id(value) != len(self.strings):
            raise ValueError('Retail string namespace exhausted')
        self.by_text[text] = value
        self.strings.append(text)
        return value

    def stage(self):
        import struct
        if self.staged:
            raise ValueError('String table already staged')
        if len(self.strings) != self.original_count:
            indices, data = bytearray(), bytearray()
            for text in self.strings:
                if text is None:
                    indices.extend(struct.pack('>I', 0xffffffff))
                else:
                    indices.extend(struct.pack('>I', len(data)))
                    data.extend(text.encode('latin-1') + b'\0')
            index_pointer = self.builder.append_debug(indices)
            data_pointer = self.builder.append_debug(data)
            self.builder.header_updates.update({0x158: len(self.strings), 0x15c: len(data),
                                                0x160: index_pointer, 0x164: data_pointer})
        self.staged = True
