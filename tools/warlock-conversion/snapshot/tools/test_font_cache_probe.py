import struct
import unittest
from font_cache_probe import snapshot


class FontCacheProbeTests(unittest.TestCase):
    def setUp(self):
        self.memory = bytearray(0x90000)
        self.word(0x10000, 0x20000)
        self.word(0x200f4, 0x30000)
        struct.pack_into('>5I', self.memory, 0x30000, 42, 0, 0x40000, 0x50000, 0x70000)
        self.word(0x5003c, 2)
        self.word(0x50070, 0x60000)
        self.word(0x60044, 0x80000)
        self.word(0x50048, 0xabcd0000)
        struct.pack_into('>6I', self.memory, 0x80000, 0xabcd0000, 8, 0, 0xabce0001, 0xffffffff, 0)
        struct.pack_into('>6I', self.memory, 0x80018, 0xabce0001, 6, 8, 0xffffffff, 0xabcd0000, 0)
        struct.pack_into('>3I6H', self.memory, 0x70000, 0x10041, 42, 0xffffffff, 6, 4, 8, 6, 0, 0)
        self.memory[0x70018:0x7001c] = b'ABCD'
        struct.pack_into('>3I6H', self.memory, 0x70020, 0x1004a, 42, 0xffffffff, 0, 0, 0, 0, 0, 0)

    def word(self, at, value):
        struct.pack_into('>I', self.memory, at, value)

    def read(self, at, size):
        return bytes(self.memory[at:at+size])

    def test_user_virtual_cache_and_empty_glyph(self):
        result = snapshot(self.read, 0, 0x10000)
        self.assertEqual([c['codepoint'] for c in result['characters']], [65, 74])
        self.assertEqual([c['pixel_nonzero_bytes'] for c in result['characters']], [4, 0])

    def test_cycle_rejected(self):
        self.word(0x80024, 0xabcd0000)
        with self.assertRaisesRegex(ValueError, 'Cyclic'):
            snapshot(self.read, 0, 0x10000)

    def test_truncated_allocation_rejected(self):
        self.word(0x80004, 6)
        with self.assertRaisesRegex(ValueError, 'exceed allocation'):
            snapshot(self.read, 0, 0x10000)

    def test_null_pointer_rejected(self):
        self.word(0x200f4, 0)
        with self.assertRaisesRegex(ValueError, 'outside bounded'):
            snapshot(self.read, 0, 0x10000)


if __name__ == '__main__':
    unittest.main()
