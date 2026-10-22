import struct
import unittest

from resource_heap_probe import snapshot


class ResourceHeapProbeTests(unittest.TestCase):
    def setUp(self):
        self.memory = bytearray(0x50000)
        self.wrapper, self.heap, self.table, self.nodes = 0x10000, 0x20000, 0x30000, 0x40000
        self.put(self.wrapper + 12, self.heap)
        self.memory[self.heap:self.heap+9] = b'resources'
        self.put(self.heap+0x38, 100, 12)
        self.put(self.heap+0x48, 0x10000)
        self.put(self.heap+0x70, self.table)
        self.put(self.table+0x20, 2, 24)
        self.put(self.table+0x44, self.nodes)
        self.put(self.nodes, 0x10000, 20, 10, 0x10001, 0xffffffff, 0)
        self.put(self.nodes+24, 0x10000, 30, 40, 0xffffffff, 0x10000, 0)

    def put(self, address, *values):
        struct.pack_into('>'+'I'*len(values), self.memory, address, *values)

    def read(self, address, size):
        return bytes(self.memory[address:address+size])

    def test_fragmentation_not_just_free_total(self):
        result = snapshot(self.read, 0, self.wrapper)
        self.assertEqual(result['occupied_bytes'], 50*4096)
        self.assertEqual(result['free_bytes'], 50*4096)
        self.assertEqual(result['largest_free_extent_bytes'], 30*4096)
        self.assertFalse(result['retail_console_budget_verified'])

    def test_overlap_is_rejected(self):
        self.put(self.nodes+24+8, 29)
        with self.assertRaisesRegex(ValueError, 'extents'):
            snapshot(self.read, 0, self.wrapper)

    def test_cycle_is_rejected(self):
        self.put(self.nodes+24+12, 0x10000)
        with self.assertRaisesRegex(ValueError, 'Cyclic'):
            snapshot(self.read, 0, self.wrapper)

    def test_over_capacity_is_rejected(self):
        self.put(self.nodes+24+4, 61)
        with self.assertRaisesRegex(ValueError, 'extents'):
            snapshot(self.read, 0, self.wrapper)

    def test_null_wrapper_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'bounded'):
            snapshot(self.read, 0, 0)


if __name__ == '__main__':
    unittest.main()
