"""Restore Reach architecture onto an accepted Gulch cache without rebuilding terrain."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from cache_reader import Cache
from map_builder import MapBuilder
from cache_registry import CacheRegistry
from tag_importer import TagImporter
from native_assets import NativeAssets
from build_scenario_checkpoint import resource_salt
from forge_reach_scenery import stage_scenery

ROOT = Path(__file__).resolve().parents[4]


def build(source, basis, xex, disc, output, report):
    for p in (output, report):
        if not p.resolve().is_relative_to(ROOT) or (p == output and p.exists()):
            raise ValueError('Outputs must be new repository-local files')
    basis_hash = hashlib.sha256(Path(basis).read_bytes()).hexdigest()
    if basis_hash not in {
        '17278eae3fa0a3fc70afeb2568e10486f52796b0d0fb2be21b36edbe840896eb',
        '4656e4e708832f8ba876a7a7d16ae4750c5b09b73d4289379893db740746f339',
    }:
        raise ValueError('Use the accepted pre-scenery Gulch cache; never append twice')
    s = Cache(source, True)
    b = MapBuilder(basis, 0x400000)
    r = CacheRegistry(b, resource_salt(xex))
    i = TagImporter(s, r, disc_maps=disc)
    i.native_assets = NativeAssets(i, disc)
    i.materials.native_assets = i.native_assets
    i.materials.preserve_normal_mips = True
    i.materials.opaque_prototype = r'objects\vehicles\scorpion\shaders\scorpion_guts'
    result = {'basis': str(basis), 'basis_sha256': basis_hash}
    try:
        result['scenery'] = stage_scenery(i)
        manifests = b.cache.block(r.manifest_field, 120)
        if len(manifests) != 2 or b.read(r.address(manifests[0]),120) != b.read(r.address(manifests[1]),120):
            raise ValueError('Expected accepted Gulch shared two-BSP residency union')
        i.finalize()
        first = b.read(r.address(manifests[0]),120)
        second = r.address(manifests[1])
        b.meta[second-b.base:second-b.base+120] = first
        result.update(tags=i.added, materials=i.materials.report, metadata_used=b.used,
                      raw_bytes_added=len(b.raw), resource_bytes_added=r.added_bytes)
        payload = b.finish(r.salt)
        output.write_bytes(payload)
        result.update(bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest(),status='built; native validation required')
    except Exception as e:
        result.update(status='failed', error=str(e),tags=i.added)
        raise
    finally:
        report.write_text(json.dumps(result,indent=2)+'\n')
        b.close();s.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source','basis','xex','disc','output','report'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    build(a.source,a.basis,a.xex,a.disc,a.output,a.report)
