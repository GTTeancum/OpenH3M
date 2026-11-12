"""Read Reach U13 2D scenery textures through their actual resource controls.

Image metadata can have PixelDataSize=0 for shared textures; resource sizes
remain authoritative. No compiled Reach shaders or runtime LUTs are imported.
"""
from reach_resource import ReachResource


class ReachBitmapSource:
    def __init__(self, cache, shared_paths=None):
        self.c = cache
        self.shared_paths = shared_paths
        self._resources = {}

    def resource(self, datum):
        if datum not in self._resources:
            self._resources[datum] = ReachResource(self.c, datum, self.shared_paths)
        return self._resources[datum]

    def clear(self):
        # Resource views retain their decompressed page. Release between bitmaps
        # rather than keeping an unbounded copy of every source resource page.
        self._resources.clear()

    def info(self, tag):
        c = self.c
        root = c.tags[tag]
        if root['group'] != 'bitm':
            raise ValueError('Expected Reach bitmap')
        rows = c.block(root['offset'] + 0x7c, 56)
        hardware = c.block(root['offset'] + 0xa8, 8)
        if len(rows) != len(hardware):
            raise ValueError('Interleaved Reach bitmaps require separate conversion')
        result = []
        for row, hw in zip(rows, hardware):
            resource = self.resource(c.u(hw))
            if resource.root != 60 or resource.ptr(60) != 0:
                raise ValueError('Unexpected Reach bitmap control layout')
            low, high = resource.unpack('I', 0)[0], resource.unpack('I', 20)[0]
            width, height = c.unpack('HH', row)
            kind, curve = c.data[row + 6], c.data[row + 17]
            fmt = c.unpack('H', row + 8)[0]
            rw, rh, depth, mips, rk = resource.unpack('HHBBB', 40)
            if (rw, rh, depth, mips, rk) != (width, height, 1, c.data[row + 16] + 1, kind):
                raise ValueError('Bitmap image and resource dimensions disagree')
            dxgi = resource.unpack('I', 52)[0]
            # The native encoder names signed BC5 as H3 MCC format 33. Reach
            # calls it 38; inspect DXGI as well rather than assuming signedness.
            # V8U8 is 22 in both games; DXGI 51 is R8G8_SNORM. Preserve
            # its signed bytes through the existing native V8U8 encoder.
            expected = {11: (87, 91), 14: (71, 72), 15: (74, 75), 16: (77, 78), 22: (51,), 38: (84,)}
            if fmt not in expected or dxgi not in expected[fmt] or kind not in (0,2):
                raise ValueError(f'Unreviewed Reach texture encoding {fmt}/{dxgi}/{kind}')
            if kind==2 and (width!=height or high or fmt in (22,38)):
                raise ValueError('Reach cube requires square, unsplit color face chains')
            if dxgi in (91, 72, 75, 78):
                curve = 5  # Preserve the resource's explicit sRGB sampling.
            if resource.fix.get(12) != 0x40000000 or (high and resource.fix.get(32) != 0x60000000):
                raise ValueError('Unexpected Reach bitmap pixel fixups')
            result.append(dict(width=width, height=height, format=33 if fmt == 38 else fmt,
                               mips=mips, kind=kind, curve=curve, size=low + high,
                               low_size=low, high_size=high, resource=c.u(hw)))
        return result

    def pixels(self, tag, index=0):
        info = self.info(tag)[index]
        resource = self.resource(info['resource'])
        low, high = info['low_size'], info['high_size']
        if len(resource.raw) != 2 or low > len(resource.raw[0]) or high > len(resource.raw[1]):
            raise ValueError('Bitmap pixels outside Reach resource segment')
        result = bytes(resource.raw[1][:high]) + bytes(resource.raw[0][:low])
        from encode_bitmap import mip_size
        width, height = info['width'], info['height']
        size = 0
        for _ in range(info['mips']):
            size += mip_size(width, height, info['format'])
            width, height = max(1, width // 2), max(1, height // 2)
        if info['kind']==2:size*=6
        if len(result) != size:
            raise ValueError('Reach bitmap mip chain size mismatch')
        return result
