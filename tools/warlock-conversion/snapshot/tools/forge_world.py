"""Forge World policy: original Sandbox Forge objects and a two-BSP static world."""
import struct
import xml.etree.ElementTree as ET
from assemble_scenario import field, stage

CATEGORIES = ('Vehicle', 'Weapon', 'Equipment', 'Scenery', 'Teleporter', 'Goal', 'Spawner')


def configure(i):
    s = i.source
    root = next(t['offset'] for t in s.tags.values() if t['group'] == 'scnr')
    name = next(s.name(n) for n,t in s.tags.items() if t['group'] == 'scnr')
    if name != r'levels\multi\forge_halo\forge_halo':
        raise ValueError('Sandbox conversion profile requires the identified Forge World source')
    schema = ET.parse(i.reference / 'mcc/scnr.xml').getroot()
    # Source currently has no gameplay-object placements. Fail rather than
    # silently discard newly authored loadouts on a future Workshop update.
    for label in ('Weapons', 'Vehicles', 'Equipment', 'Crates', 'Bipeds', 'Squads', 'Scripts'):
        if s.u(root + int(field(schema,label).get('offset'),0)):
            raise ValueError('Forge World policy requires review of placed ' + label)
    zone = next(t['offset'] for t in s.tags.values() if t['group'] == 'zone')
    zs = ET.parse(i.reference / 'mcc/zone.xml').getroot()
    f = field(zs, 'Zone Set Zone Usage')
    rows = s.block(zone + int(f.get('offset'),0),36)
    if len(rows) != 1 or s.unpack('8I',rows[0]+4) != (0,3,3,0,0,0,0,0xffffffff):
        raise ValueError('Forge World must use one zone with both BSPs always active')
    i.materials.resize_blend_maps = True
    i.materials.preserve_normal_mips = True
    i.materials.forge_world_sky = True
    i.materials.bitmap_size_overrides = {}
    for index, tag in s.tags.items():
        if tag['group'] == 'bitm':
            info = i.materials.bitmaps.info(index)
            if len(info) == 1 and info[0]['mips'] == 1 and max(info[0]['width'], info[0]['height']) <= 1024:
                i.materials.bitmap_size_overrides[s.name(index)] = 1024
    i.stock_forge_palette = True
    i.always_loaded_bsps = True
    i.materials.opaque_prototype = r'objects\vehicles\scorpion\shaders\scorpion_guts'
    return {'forge_palette':'Original Xbox 360 Sandbox, including native prices and limits',
            'custom_forge_objects':'Removed; source palette is not imported',
            'weapons_vehicles':'Stock Halo 3 only; no placed source weapons or vehicles',
            'environment':'Authored two-BSP geometry, lighting, water and effects retained',
            'source_palette_counts': {cat:s.u(root+int(field(schema,'Map Variant '+cat+' Palette').get('offset'),0)) for cat in CATEGORIES}}


def stage_stock_palette(i):
    c,b = i.registry.cache,i.builder
    root = next(t['offset'] for t in c.tags.values() if t['group']=='scnr')
    ds = ET.parse(i.reference/'plugins/scnr.xml').getroot()
    arrays = {}
    for cat in CATEGORIES:
        name = 'Map Variant '+cat+' Palette'
        f = field(ds,name);stride=int(f.get('elementSize'),0)
        rows = c.block(root+int(f.get('offset'),0),stride)
        arrays[name] = len(rows), b''.join(c.data[r:r+stride] for r in rows)
    stage(b,{'arrays':arrays,'unresolved':[]},ds)
    # Preserve actual native Forge budget, rather than the MCC expanded budget.
    for f in ds:
        if 'budget' in f.get('name','').lower() and f.tag.lower()=='float32':
            at=int(f.get('offset'),0)
            b.put(i.registry.address(root+at),'f',c.unpack('f',root+at)[0])
    return {name:count for name,(count,_) in arrays.items()}


def finalize_residency(i):
    """Publish two always-active BSP manifests after resource-ID compaction.

    Both BSPs share the same conservative union of resident resources. Bitsets
    reference the same resources; payloads are not copied or imported twice.
    No streaming-zone transitions are supported by this restricted profile.
    """
    r,b,c = i.registry,i.builder,i.registry.cache
    if len(i.converted_bsps)!=2:
        raise ValueError('Expected both Forge World BSPs')
    schema=ET.parse(i.reference/'plugins/zone.xml').getroot()
    for name in ('Static BSP Zone Manifests','Dynamic BSP Zone Manifests'):
        f=field(schema,name);at=r.address(r.zone+int(f.get('offset'),0))
        count,pointer=struct.unpack('>II',b.read(at,8))
        if count!=1:raise ValueError('Expected one original Sandbox manifest')
        payload=b.read(pointer,120)
        b.put(at,'III',2,b.alloc(payload*2),0)
    f=field(schema,'Zone Set Zone Usage');at=r.address(r.zone+int(f.get('offset'),0))
    count,pointer=struct.unpack('>II',b.read(at,8))
    if count!=1:raise ValueError('Expected one Sandbox zone')
    b.put(pointer+8,'II',3,3)
    return {'bsp_count':2,'active_mask':3,'policy':'Shared conservative residency union; no resource payload duplication'}
