"""Native cache count, hash and PVS conversion regressions (synthetic data)."""
import copy
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock
from types import SimpleNamespace
from cache_integrity import (rebuild_page_reference_counts, page_reference_counts,
                             refresh_cache_page_reference_counts, refresh_cache_hashes,
                             normalized_header, finalize_cache)
from cache_reader import Cache
from map_builder import MapBuilder
from source_schema import load_schema, MCC_2022_BUILD
from tag_metadata import MetadataConverter


def tables(slots, flags=None, page_count=3):
    resources = bytearray(64 * len(slots)); locations = bytearray(16 * len(slots)); pages = bytearray(88 * page_count)
    for i in range(page_count):
        struct.pack_into('>I', pages, i*88+16, 4096)
        struct.pack_into('>H', pages, i*88+84, 999)
    for i, pair in enumerate(slots):
        struct.pack_into('>HB', resources, i*64+16, 0x9100, 1)
        struct.pack_into('>Hh', resources, i*64+32, flags[i] if flags else 3, i)
        struct.pack_into('>hh', locations, i*16, *pair)
    return resources, locations, pages


def native_cache():
    """Small complete cache with a signed section displacement and six partitions.

    The scenario lives in the first digest span and pages in the second, so
    a DLC identity edit plus stale counts exercises both metadata digests.
    """
    start, size = 0x5000, 0x10000
    base = 0xbfc00000 - size
    data = bytearray(start + size + 0x1000)
    data[:4], data[0x2ffc:0x3000] = b'head', b'foot'
    fields = ((4, 11), (8, len(data)), (0x10, base + 0x80), (0x18, size),
              (0x2e8, base), (0x47c, 0x3000), (0x484, 0x3000), (0x488, 0x2000),
              (0x48c, 0x9000), (0x474, 0xffffc000), (0x490, size),
              (0x494, start + size), (0x498, 0x1000))
    for at, value in fields:
        struct.pack_into('>I', data, at, value)
    va = base
    for i, length in enumerate((0x1000, 0x1000, 0x1000, 0x1000, 0x1000, 0xb000)):
        struct.pack_into('>II', data, 0x2f0 + i * 8, va, length)
        va += length
    struct.pack_into('>H', data, 0x13c, 1)
    data[0x142] = 1
    data[0x18c:0x194] = b'zanzibar'
    data[0x36c:0x46c] = bytes(range(256))
    data[0x3000:start] = b'R' * (start - 0x3000)
    data[start + size:] = b'L' * 0x1000
    struct.pack_into('>IIII', data, start + 0x80, 3, base + 0x100, 3, base + 0x140)
    for i, (name, relative) in enumerate(((b'zone', 0x200), (b'play', 0x500),
                                         (b'scnr', 0x600))):
        data[start + 0x100 + i * 16:start + 0x104 + i * 16] = name
        struct.pack_into('>HHI', data, start + 0x140 + i * 8, i, 0x1234, base + relative)
    struct.pack_into('>I', data, start + 0x608, 42)
    resources, locations, pages = tables([(0, 1), (0, 0)], flags=[1, 3])
    locations += struct.pack('>hh12x', 2, 2)  # An orphan row must not count.
    for descriptor, relative, payload, stride in (
            (0x200 + 88, 0x2000, resources, 64),
            (0x500 + 48, 0x2200, locations, 16),
            (0x500 + 24, 0x4000, pages, 88)):
        struct.pack_into('>III', data, start + descriptor, len(payload) // stride,
                         base + relative, 0)
        data[start + relative:start + relative + len(payload)] = payload
    return data, SimpleNamespace(start=start, size=size, base=base,
                                 zone=start + 0x200, play=start + 0x500,
                                 scenario=start + 0x600, pages=start + 0x4000)


def expected_integrity(data, salt):
    """Independent scalar XOR and final-byte digest oracle (no finalizer calls)."""
    checksum = 0
    for (word,) in struct.iter_unpack('>I', data[0x3000:]):
        checksum ^= word
    header = bytearray(data[:0x3000])
    for at, length in ((0x320, 4), (0x328, 8), (0x330, 0x13c), (0x1c, 0x100),
                       (0x144, 8), (0x16c, 0x20), (0x49c, 0x10)):
        header[at:at + length] = bytes(length)
    words = lambda at: struct.unpack_from('>I', data, at)[0]
    start = (words(0x48c) + words(0x474)) & 0xffffffff
    sizes = [sum(words(at) for at in (0x2f4, 0x2fc, 0x304)),
             sum(words(at) for at in (0x30c, 0x314, 0x31c))]
    hashes = [hashlib.sha1(salt + header).digest()]
    for length in sizes:
        hashes.append(hashlib.sha1(salt + data[start:start + length]).digest())
        start += length
    return checksum, hashes


class ReferenceCounts(unittest.TestCase):
    def test_every_resource_slot_not_unique_location_or_page(self):
        r,l,p=tables([(0,1),(0,1),(0,0)])
        struct.pack_into('>h',r,64+34,0) # two resources sharing a location still count twice
        report=rebuild_page_reference_counts(r,l,p)
        self.assertEqual([struct.unpack_from('>H',p,i*88+84)[0] for i in range(3)],[4,2,0])
        self.assertEqual(report['nonempty_reserved_slots'],6)
        self.assertFalse(rebuild_page_reference_counts(r,l,p)['changes'])

    def test_orphan_location_not_counted_and_optional_flags_untouched(self):
        r,l,p=tables([(0,1)],[1]); l += struct.pack('>hh12x',2,2)
        original_r,original_l=bytes(r),bytes(l)
        counts,enabled,total=page_reference_counts(r,l,p)
        self.assertEqual((counts,enabled,total),([1,1,0],[1,0,0],2))
        rebuild_page_reference_counts(r,l,p)
        self.assertEqual((bytes(r),bytes(l)),(original_r,original_l))

    def test_disabled_empty_optional_is_reserved_but_not_allocated(self):
        r,l,p=tables([(0,1)],[1]); struct.pack_into('>I',p,88+16,0)
        self.assertEqual(page_reference_counts(r,l,p),([1,1,0],[1,0,0],1))
        struct.pack_into('>H',r,32,3)
        with self.assertRaisesRegex(ValueError,'empty page'):page_reference_counts(r,l,p)

    def test_retired_resource_and_bad_references_reject(self):
        r,l,p=tables([(0,-1)]); struct.pack_into('>H',r,16,0xffff)
        with self.assertRaisesRegex(ValueError,'Retired'):page_reference_counts(r,l,p)
        struct.pack_into('>h',r,34,-1)
        self.assertEqual(page_reference_counts(r,l,p),([0,0,0],[0,0,0],0))
        r,l,p=tables([(4,-1)])
        with self.assertRaisesRegex(ValueError,'outside final'):page_reference_counts(r,l,p)

    def test_uint16_page_and_total_overflow_reject(self):
        r,l,p=tables([(0,-1)],page_count=2)
        r*=65536
        with self.assertRaisesRegex(ValueError,'count exceeds'):page_reference_counts(r,l,p)
        r,l,p=tables([(0,1)],page_count=2);r*=32768
        with self.assertRaisesRegex(ValueError,'Cumulative'):page_reference_counts(r,l,p)


class PVSVersion(unittest.TestCase):
    def fixture(self,mcc,old=False):
        s=Cache.__new__(Cache); s.mcc=mcc;s.endian='<' if mcc else '>';s.data=bytearray(0x400)
        s.base=0;s.start=0
        if mcc:
            build=(MCC_2022_BUILD if old else 'May 30 2023 12:00:00').encode()
            s.data[0xa0:0xa0+len(build)]=build
        dst=SimpleNamespace(mcc=False)
        ss=next(x for x in load_schema(s,'scnr') if x.get('name')=='Zone Set Potentially Visible Sets')
        ds=next(x for x in load_schema(dst,'scnr') if x.get('name')=='Zone Set Potentially Visible Sets')
        converter=MetadataConverter(s,SimpleNamespace(),None,None,None)
        return s,ss,ds,converter

    def test_old_and_current_mcc_full_word(self):
        for old in (False,True):
            s,ss,ds,c=self.fixture(True,old)
            struct.pack_into('<II',s.data,0x200,1,8)
            src_schema=copy.deepcopy(ss);dst_schema=copy.deepcopy(ds)
            result=c.convert(0x200,ss,ds,'scnr:/Zone Set Potentially Visible Sets')
            self.assertEqual(result[:8],bytes.fromhex('0000000100000008'))
            self.assertEqual(result[8:],bytes(36))
            import xml.etree.ElementTree as ET
            self.assertEqual(ET.tostring(ss),ET.tostring(src_schema))
            self.assertEqual(ET.tostring(ds),ET.tostring(dst_schema))

    def test_native_word_roundtrip(self):
        s,ss,ds,c=self.fixture(False)
        struct.pack_into('>II',s.data,0x200,1,8)
        self.assertEqual(c.convert(0x200,ss,ds,'scnr:/Zone Set Potentially Visible Sets'),bytes(s.data[0x200:0x22c]))

    def test_unsupported_full_word_rejects_not_just_low_half(self):
        s,ss,ds,c=self.fixture(True)
        for version in (0,7,9,0x10008,0x80000):
            struct.pack_into('<I',s.data,0x204,version)
            with self.assertRaisesRegex(ValueError,'version word'):c.convert(0x200,ss,ds,'scnr:/Zone Set Potentially Visible Sets')


class CacheHashes(unittest.TestCase):
    def fixture(self):
        data=bytearray(0x5000);data[:4]=b'head';data[0x2ffc:0x3000]=b'foot'
        for at,value in ((4,11),(8,len(data)),(0x18,0x2000),(0x48c,0x3000),
                         (0x490,0x2000),(0x2f4,0x1000),(0x30c,0x1000)):
            struct.pack_into('>I',data,at,value)
        struct.pack_into('>H',data,0x13c,1)
        data[0x36c:0x46c]=bytes(range(256))
        data[0x3000:0x4000]=b'A'*4096;data[0x4000:0x5000]=b'B'*4096
        return data,bytes(range(34))

    def test_both_metadata_hashes_refresh_and_signature_is_not_forged(self):
        import hashlib
        data,salt=self.fixture();signature=bytes(data[0x36c:0x46c])
        result=refresh_cache_hashes(data,salt)
        expected=[hashlib.sha1(salt+normalized_header(data[:0x3000])).digest(),
                  hashlib.sha1(salt+b'A'*4096).digest(),hashlib.sha1(salt+b'B'*4096).digest()]
        self.assertEqual(bytes(data[0x330:0x36c]),b''.join(expected))
        self.assertEqual(bytes(data[0x36c:0x46c]),signature)
        before=bytes(data);self.assertEqual(refresh_cache_hashes(data,salt),result);self.assertEqual(bytes(data),before)

    def test_single_bit_changes_each_partition_and_final_digest(self):
        data,salt=self.fixture();baseline=refresh_cache_hashes(data,salt)
        for offset,partition in ((0x3000,1),(0x4000,2)):
            changed=bytearray(data);changed[offset]^=1
            result=refresh_cache_hashes(changed,salt)
            self.assertNotEqual(result['salted_hashes'][partition],baseline['salted_hashes'][partition])
            self.assertNotEqual(result['body_xor'],baseline['body_xor'])
            self.assertNotEqual(result['recomputed_triplet_digest'],baseline['recomputed_triplet_digest'])

    def test_resources_only_uses_signed_zero_placeholders(self):
        data,salt=self.fixture()
        for at in (0x18,0x48c,0x490,0x2f4,0x30c):struct.pack_into('>I',data,at,0)
        struct.pack_into('>H',data,0x13c,3)
        refresh_cache_hashes(data,salt)
        self.assertEqual(data[0x344:0x36c],bytes(40))

    def test_partition_mismatch_rejected(self):
        data,salt=self.fixture();struct.pack_into('>I',data,0x18,4096)
        with self.assertRaisesRegex(ValueError,'partition spans'):refresh_cache_hashes(data,salt)


class FinalizationTestCase(unittest.TestCase):
    salt = bytes(range(34))

    def setUp(self):
        work = Path(__file__).resolve().parents[4] / 'work'
        work.mkdir(exist_ok=True)
        directory = tempfile.TemporaryDirectory(prefix='cache-finalization-', dir=work)
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)

    def assert_integrity(self, data, report):
        checksum, hashes = expected_integrity(data, self.salt)
        self.assertEqual(struct.unpack_from('>I', data, 0x2c4)[0], checksum)
        self.assertEqual(data[0x330:0x36c], b''.join(hashes))
        self.assertEqual(report['body_xor'], f'{checksum:08x}')
        self.assertEqual(report['salted_hashes'], [h.hex() for h in hashes])
        self.assertEqual(report['recomputed_triplet_digest'],
                         hashlib.sha1(self.salt + b''.join(hashes)).hexdigest())
        self.assertEqual(data[0x36c:0x46c], bytes(range(256)))


class SerializedFinalization(FinalizationTestCase):
    def test_complete_graph_signed_displacement_and_both_digest_spans(self):
        data, layout = native_cache()
        before = bytes(data)
        result = finalize_cache(data, self.salt)
        counts = result['reference_counts']
        self.assertEqual([row['after'] for row in counts['changes']], [3, 1, 0])
        self.assertEqual([row['file_offset'] for row in counts['changes']],
                         [layout.pages + i * 88 + 84 for i in range(3)])
        self.assertEqual(counts['serialized_slots'], 4)
        self.assertEqual(counts['native_enabled_slots'], 3)
        self.assert_integrity(data, result['integrity'])
        self.assertEqual(data[0x3000:layout.start], before[0x3000:layout.start])
        self.assertEqual(data[layout.start + layout.size:], before[layout.start + layout.size:])
        final = bytes(data)
        repeated = finalize_cache(data, self.salt)
        self.assertFalse(repeated['reference_counts']['changes'])
        self.assertEqual(repeated['integrity'], result['integrity'])
        self.assertEqual(bytes(data), final)

    def test_malformed_header_or_partition_rejected_before_mutation(self):
        for offset, value in ((0, 0), (4, 13), (8, 0), (0x2ffc, 0),
                              (0x18, 0), (0x490, 0), (0x48c, 0x5000),
                              (0x490, 0x10004), (0x2f4, 0x1004),
                              (0x474, 0x7fffffff)):
            with self.subTest(offset=hex(offset), value=value):
                data, _ = native_cache()
                struct.pack_into('>I', data, offset, value)
                before = bytes(data)
                with self.assertRaises(ValueError):
                    finalize_cache(data, self.salt)
                self.assertEqual(data, before)
        for size in (0, 0x2fff, 0x3000, 0x5001):
            data, _ = native_cache()
            data = data[:size]
            before = bytes(data)
            with self.assertRaises(ValueError):
                refresh_cache_hashes(data, self.salt)
            self.assertEqual(data, before)
        data, _ = native_cache()
        before = bytes(data)
        with self.assertRaisesRegex(ValueError, 'salt'):
            finalize_cache(data, bytes(33))
        self.assertEqual(data, before)

    def test_final_table_pointers_and_duplicate_roots_reject(self):
        data, layout = native_cache()
        cases = ((layout.zone + 92, layout.base - 1),
                 (layout.play + 28, layout.base + layout.size - 80),
                 (layout.start + 0x80, 0xffffffff),
                 (layout.start + 0x148, 0x00001234))  # Change play's group to zone.
        for offset, value in cases:
            with self.subTest(offset=hex(offset)):
                changed = bytearray(data)
                struct.pack_into('>I', changed, offset, value)
                before = bytes(changed)
                with self.assertRaises(ValueError):
                    refresh_cache_page_reference_counts(changed)
                self.assertEqual(changed, before)

    def test_map_builder_follows_relocated_tables_not_stale_source_tables(self):
        data, layout = native_cache()
        source = self.directory / 'basis.map'
        source.write_bytes(data)
        builder = MapBuilder(source, reserve=0x10000)
        self.addCleanup(builder.close)
        resources, locations, pages = tables([(2, 1), (2, 2)], flags=[1, 3])
        locations += struct.pack('>hh12x', 0, 0)
        resource_va = builder.alloc(resources)
        location_va = builder.alloc(locations)
        page_va = builder.alloc(pages)
        builder.put(layout.base + 0x200 + 88, 'III', 2, resource_va, 0)
        builder.put(layout.base + 0x500 + 48, 'III', 3, location_va, 0)
        builder.put(layout.base + 0x500 + 24, 'III', 3, page_va, 0)
        out = builder.finish(self.salt)
        at = layout.start + page_va - builder.base
        self.assertEqual([struct.unpack_from('>H', out, at + i * 88 + 84)[0]
                          for i in range(3)], [0, 1, 3])
        self.assertEqual(struct.unpack_from('>H', out, layout.pages + 0x10000 + 84)[0], 999)
        self.assertEqual(out[0x142], 0)
        self.assert_integrity(out, builder.integrity_report)
        self.assertEqual(builder.reference_count_report['serialized_slots'], 4)
        self.assertFalse(finalize_cache(out, self.salt)['reference_counts']['changes'])
        self.assertEqual(source.read_bytes(), data)


class DLCPayloadFinalization(FinalizationTestCase):
    def build_payload(self, data):
        from build_dlc_payload import build
        converted = self.directory / 'converted'
        stock = self.directory / 'maps'
        converted.mkdir()
        (stock / 'info').mkdir(parents=True)
        source = converted / 'zanzibar.map'
        source.write_bytes(data)
        info = bytearray(0x4d80 + 273)
        info[0x30:0x34], info[0x4d80:0x4d84] = b'levl', b'_eof'
        struct.pack_into('>I', info, 0x3c, 42)
        (stock / 'info' / 'zanzibar.mapinfo').write_bytes(info)
        output = self.directory / 'payload'
        with mock.patch('build_dlc_payload.resource_salt', return_value=self.salt):
            report = build(converted, stock, output,
                           [('zanzibar', 'desolation', 'Desolation', 1748)])
        self.assertEqual(source.read_bytes(), data)
        return output, report['maps'][0]

    def assert_payload(self, output, report):
        data = bytearray((output / 'desolation.map').read_bytes())
        cache = Cache(output / 'desolation.map')
        try:
            scenario = next(t['offset'] for t in cache.tags.values() if t['group'] == 'scnr')
            self.assertEqual(cache.u(scenario + 8), 1748)
        finally:
            cache.close()
        self.assertEqual(data[0x18c:0x1ac].rstrip(b'\0'), b'desolation')
        self.assertEqual(data[0x1b0:0x2b0].rstrip(b'\0'), b'levels\\dlc\\desolation\\desolation')
        self.assert_integrity(data, report['cache_finalization']['integrity'])
        self.assertEqual(report['sha256'], hashlib.sha256(data).hexdigest())
        self.assertEqual(report['bytes'], len(data))
        final = bytes(data)
        self.assertFalse(finalize_cache(data, self.salt)['reference_counts']['changes'])
        self.assertEqual(data, final)
        info = (output / 'desolation.mapinfo').read_bytes()
        self.assertEqual(struct.unpack_from('>I', info, 0x3c)[0], 1748)
        self.assertEqual(info[0x4d91:], bytes(256))
        return data

    def test_dlc_rehashes_after_changing_builder_scenario_identity(self):
        data, _ = native_cache()
        basis = self.directory / 'basis.map'
        basis.write_bytes(data)
        builder = MapBuilder(basis, reserve=0x10000)
        try:
            data = builder.finish(self.salt)
        finally:
            builder.close()
        output, report = self.build_payload(data)
        final = self.assert_payload(output, report)
        self.assertNotEqual(final[0x330:0x344], data[0x330:0x344])
        self.assertNotEqual(final[0x344:0x358], data[0x344:0x358])
        self.assertEqual(final[0x358:0x36c], data[0x358:0x36c])
        self.assertFalse(report['cache_finalization']['reference_counts']['changes'])

    def test_dlc_repairs_stale_counts_xor_and_both_metadata_hashes(self):
        data, _ = native_cache()
        data[0x330:0x36c] = b'?' * 60
        output, report = self.build_payload(data)
        self.assert_payload(output, report)
        self.assertEqual([row['after'] for row in report['cache_finalization']['reference_counts']['changes']],
                         [3, 1, 0])

    def test_invalid_graph_is_not_written_as_a_payload(self):
        data, layout = native_cache()
        struct.pack_into('>I', data, layout.pages + 16, 0)
        with self.assertRaisesRegex(ValueError, 'empty page'):
            self.build_payload(data)
        self.assertFalse((self.directory / 'payload' / 'desolation.map').exists())
        self.assertEqual((self.directory / 'converted' / 'zanzibar.map').read_bytes(), data)


if __name__=='__main__':unittest.main()
