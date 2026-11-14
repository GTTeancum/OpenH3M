"""Control-only render resources must not allocate empty enabled raw pages."""
import struct
from types import SimpleNamespace
import unittest
from unittest import mock
import zlib

from cache_integrity import page_reference_counts
from cache_registry import CacheRegistry
from render_resource import convert_render_resource


class EmptyRenderResource(unittest.TestCase):
    def registry(self):
        r = CacheRegistry.__new__(CacheRegistry)
        r.closed = False
        r.tags = bytearray(struct.pack('>HHI', 0, 0x9000, 0xbe000000))
        r.cache = SimpleNamespace(groups=['sbsp'])
        r.resources, r.pages, r.locations, r.control = (bytearray() for _ in range(4))
        r.types = {'render_geometry_api_resource_definition': 0, 'sound_resource_definition': 1}
        r.salt, r.added_bytes = bytes(range(34)), 0
        r.added_resource_bytes = {}
        r.builder = SimpleNamespace(alloc=mock.Mock(return_value=0xbe100000),
                                    append_raw=mock.Mock(return_value=4096))
        return r

    def test_empty_render_control_matches_native_no_page_shape(self):
        payload = convert_render_resource(SimpleNamespace(buffers=lambda _: []))
        self.assertEqual(payload, dict(control=bytes(48), raw=b'', root=0,
                                      fixups=[], interops=[], vertex_buffers=0, index_buffers=0))
        r = self.registry()
        datum = r.add_resource(0x90000000, 'render_geometry_api_resource_definition', payload)
        self.assertEqual(datum, 0x91000000)
        self.assertEqual(r.added_resource_bytes, {0: 0})
        self.assertEqual(r.control, bytes(48))
        self.assertEqual(r.pages, b'')
        self.assertEqual(struct.unpack('>hhIIhh', r.locations), (-1, -1, 0, 0, -1, -1))
        self.assertEqual(struct.unpack_from('>II', r.resources, 20), (0, 48))
        self.assertEqual(struct.unpack_from('>Hh', r.resources, 32), (0, 0))
        self.assertEqual(page_reference_counts(r.resources, r.locations, r.pages), ([], [], 0))
        r.builder.append_raw.assert_not_called()

    def test_nonempty_resource_still_allocates_enabled_checked_page(self):
        r = self.registry(); raw = b'buffer' * 16
        r.add_resource(0x90000000, 'render_geometry_api_resource_definition',
                       dict(control=bytes(48), raw=raw, root=0, fixups=[], interops=[]))
        self.assertEqual(r.added_resource_bytes, {0: len(raw)})
        compressed = r.builder.append_raw.call_args.args[0]
        self.assertEqual(zlib.decompress(compressed, -15), raw)
        self.assertEqual(struct.unpack_from('>Hh', r.resources, 32), (1, 0))
        self.assertEqual(page_reference_counts(r.resources, r.locations, r.pages), ([1], [1], 1))

    def test_empty_raw_does_not_make_dangling_fixups_valid(self):
        r = self.registry()
        with self.assertRaisesRegex(ValueError, 'Invalid new resource fixup'):
            r.add_resource(0x90000000, 'render_geometry_api_resource_definition',
                           dict(control=bytes(48), raw=b'', root=0,
                                fixups=[(12, 0x40000000)], interops=[]))
        self.assertEqual((r.resources, r.pages, r.locations, r.control), (b'', b'', b'', b''))


if __name__ == '__main__':
    unittest.main()
