"""Read complete marker records from the original H4 cache, without rewriting it."""
import mmap
import struct


class SourceMarkerCache:
    def __init__(self, path):
        self.file = path.open('rb')
        self.data = mmap.mmap(self.file.fileno(), 0, access=mmap.ACCESS_READ)
        self.start = (self.u(0x484) + self.u(0x49c)) & 0xffffffff
        self.base = self.u(0x2f8)
        header = self.offset(self.u(0x10), 16)
        self.group_count, groups, self.tag_count, tags = struct.unpack_from('>4I', self.data, header)
        self.groups = self.offset(groups, self.group_count * 16)
        self.tags = self.offset(tags, self.tag_count * 8)

    def u(self, at):
        return struct.unpack_from('>I', self.data, at)[0]

    def offset(self, pointer, length):
        at = pointer - self.base + self.start
        if at < 0 or length < 0 or at + length > len(self.data):
            raise ValueError('Marker source pointer outside cache')
        return at

    def records(self, tag_index):
        if not 0 <= tag_index < self.tag_count:
            raise ValueError('Marker source tag index outside cache')
        group, _, pointer = struct.unpack_from('>HHI', self.data, self.tags + tag_index * 8)
        if group >= self.group_count or self.data[self.groups+group*16:self.groups+group*16+4] != b'mode':
            raise ValueError('Marker source is not a render model')
        model = self.offset(pointer, 0x48)
        count, pointer = struct.unpack_from('>II', self.data, model + 0x3c)
        groups = self.offset(pointer, count * 16) if count else 0
        result = None
        for index in range(count):
            at = groups + index * 16
            if self.u(at) != 0x193:
                continue
            if result is not None:
                raise ValueError('Duplicate source sandbox_magnet group')
            size, pointer = struct.unpack_from('>II', self.data, at + 4)
            records = self.offset(pointer, size * 48) if size else 0
            result = [bytes(self.data[records+i*48:records+(i+1)*48]) for i in range(size)]
        if result is None:
            raise ValueError('Missing original sandbox_magnet group')
        return result

    def close(self):
        self.data.close()
        self.file.close()
