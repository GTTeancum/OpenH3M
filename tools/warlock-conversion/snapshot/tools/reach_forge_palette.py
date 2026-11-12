"""Read-only MCC Reach U13 Forge palette; no whole-cache extraction.

Header and palette layouts checked against Reclaimer's CacheFileU8 and
HaloMapStudio's ScenarioForgePaletteWalker. Counts are 32-bit: the adjacent
padding in retail MCC files is NOT necessarily zero.
"""
import mmap
import struct


class ReachCache:
    mcc = True
    endian = '<'

    def __init__(self, path):
        self.file = open(path, 'rb')
        self.data = mmap.mmap(self.file.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            if self.data[:4] != b'daeh' or self.u(4) != 13:
                raise ValueError('Expected MCC Reach U13 cache')
            build = self.data[160:192].split(b'\0')[0]
            if build != b'Jun 21 2023 15:35:31':
                raise ValueError(f'Unreviewed Reach cache build: {build!r}')
            self.magic = self.q(736) - ((self.u(1260)+self.u(1236)) & 0xffffffff)
            index = self.offset(self.q(744))
            ng, ga, nt, ta = self.u(index), self.q(index+8), self.u(index+16), self.q(index+24)
            if not 0 < ng < 1024 or not 0 < nt < 65536:
                raise ValueError('Invalid tag-index counts')
            ga, ta = self.offset(ga), self.offset(ta)
            groups = [self.data[ga+i*16:ga+i*16+4][::-1].decode('ascii') for i in range(ng)]
            names = (self.u(36)+self.u(1228)) & 0xffffffff
            indices = (self.u(44)+self.u(1228)) & 0xffffffff
            self.tags = {}
            for i in range(nt):
                group, salt, pointer = struct.unpack_from('<HHI', self.data, ta+i*8)
                if group == 65535:
                    continue
                if group >= ng:
                    raise ValueError('Invalid tag group index')
                rel = self.u(indices+i*4)
                if rel >= self.u(40):
                    raise ValueError('Tag name outside string buffer')
                end = self.data.find(b'\0', names+rel, names+self.u(40))
                if end < 0:
                    raise ValueError('Unterminated tag name')
                self.tags[i] = dict(group=groups[group], salt=salt,
                                    name=self.data[names+rel:end].decode('utf-8'),
                                    offset=self.pointer(pointer))
        except Exception:
            self.close()
            raise

    def u(self, offset):
        return struct.unpack_from('<I', self.data, offset)[0]

    def unpack(self, fmt, offset):
        return struct.unpack_from('<' + fmt, self.data, offset)

    def name(self, index):
        return self.tags[index]['name']

    def debug_offset(self, address):
        return (address + self.u(1228)) & 0xffffffff

    def locale_offset(self, address):
        return (address + self.u(1240)) & 0xffffffff

    def q(self, offset):
        return struct.unpack_from('<Q', self.data, offset)[0]

    def offset(self, address):
        offset = address-self.magic
        if not 0 <= offset < len(self.data):
            raise ValueError('Reach address outside cache')
        return offset

    def pointer(self, value):
        signed = value if value < 0x80000000 else value-0x100000000
        return self.offset(signed*4+0x50000000)

    def block(self, at, stride):
        if stride <= 0:
            raise ValueError('Reach block stride must be positive')
        count, pointer = self.u(at), self.u(at+4)
        if not count:
            return []
        offset = self.pointer(pointer)
        # Byte blocks (notably BSP MOPP programs) legitimately exceed 65,536
        # elements. Bound their byte span against the mapped file instead;
        # returning range does not allocate count objects. This is a reader
        # correction, not a change to any output format or engine index limit.
        if count > (len(self.data)-offset)//stride:
            raise ValueError('Reach block outside cache')
        return range(offset, offset+count*stride, stride)

    def palette(self):
        roots = [t['offset'] for t in self.tags.values() if t['group'] == 'scnr']
        if len(roots) != 1:
            raise ValueError('Expected one scenario')
        result = []
        for category in self.block(roots[0]+0x228, 20):
            for entry in self.block(category+8, 28):
                variants = []
                for row in self.block(entry+4, 24):
                    datum = self.u(row+16)
                    if datum == 0xffffffff:
                        variants.append(None)
                        continue
                    tag = self.tags[datum & 65535]
                    if tag['salt'] != datum >> 16:
                        raise ValueError('Palette tag salt mismatch')
                    variants.append(dict(group=tag['group'], name=tag['name'], datum=datum,
                                         variant_sid=self.u(row+20), display_sid=self.u(row)))
                result.append(variants)
        return result

    def close(self):
        self.data.close()
        self.file.close()
