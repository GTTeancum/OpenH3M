"""Inventory the unchanged Foundry reader's H4 collision output and source shapes."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import sys
import bpy
import addon_utils

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'work/halo4-to-h3/haven'
KIT = ROOT / 'work/editing-kits/h4ek'
sys.path.insert(0, str(ROOT / 'work/halo4-to-h3/python-packages-313'))
sys.path.insert(0, str(ROOT / 'work/halo4-to-h3/upstream/Foundry-1.9.19'))
addon_utils.enable('io_scene_foundry', default_set=True, persistent=False)
project = bpy.context.preferences.addons['io_scene_foundry'].preferences.projects.add()
project.name = project.project_name = 'Haven collision audit'
project.project_path = str(KIT)
project.tags_directory = str(KIT / 'tags')
project.data_directory = str(KIT / 'data')
project.corinth = True
bpy.context.scene.nwo.scene_project = project.name
bpy.context.scene.nwo.lights_export_on_save = False
bpy.context.scene.nwo.prefabs_export_on_save = False
from io_scene_foundry.managed_blam.scenario_structure_bsp import ScenarioStructureBspTag
from io_scene_foundry.managed_blam.connected_geometry import BSPCollisionMaterial
from io_scene_foundry.managed_blam.havok_tagfile import HavokTagfileReader

def manifest():
    return {str(p.relative_to(KIT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (KIT / 'tags').rglob('*') if p.is_file()}

def shape_inventory(shape):
    """Summarize the existing reader's object tree; never decode bytes here."""
    classes = Counter()
    stack, seen = [shape], set()
    while stack:
        item = stack.pop()
        if isinstance(item, (dict, list, tuple)):
            if id(item) in seen:
                continue
            seen.add(id(item))
            if isinstance(item, dict):
                classes.update(item.get('classes', []))
                stack.extend(item.values())
            else:
                stack.extend(item)
    return dict(classes)

before = manifest()
report = {'reader': 'Unmodified Foundry release 1.9.19', 'collision_outputs': [], 'serialized_sources': []}
source = KIT / 'tags/levels/multi/wraparound/wraparound_000.scenario_structure_bsp'
assert source.is_file()
try:
    with ScenarioStructureBspTag(path=str(source), tag_must_exist=True) as bsp:
        materials = [BSPCollisionMaterial(e) for e in bsp.tag.SelectField('Block:collision materials').Elements]
        for collision in bsp._read_havok_collisions(materials):
            counts = {str(k): len(v) for k,v in collision.source_instance_face_indices().items()}
            report['collision_outputs'].append(dict(name=collision.name,
                vertices=len(collision.vertices), faces=len(collision.faces),
                collision_type=collision.collision_type_name, source_instance_face_counts=counts))
        raw = bsp.tag.SelectField('Struct:resource interface[0]/Block:raw_resources')
        for resource in raw.Elements:
            for havok in resource.SelectField('Struct:raw_items[0]/Block:Havok Data').Elements:
                for collision in havok.SelectField('Block:Serialized Per Collision Type Havok Geometry').Elements:
                    for field_name in ('Serialized Havok Data', 'Serialized Static Havok Data'):
                        data = bsp._data_field_bytes(bsp._select_field_safe(collision, field_name))
                        if not data:
                            continue
                        parsed = HavokTagfileReader(data).parse()
                        records = []
                        for item in parsed.get('fields', {}).get('instances', []):
                            fields = item.get('fields', {})
                            records.append(dict(source_instance_index=fields.get('userData', -1),
                                shape_classes=shape_inventory(fields.get('shape'))))
                        report['serialized_sources'].append(dict(field=field_name, bytes=len(data),
                            root_classes=parsed.get('classes'), instances=records))
finally:
    report['source_tags_unchanged'] = manifest() == before
    (OUT / 'haven-havok-audit.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    assert report['source_tags_unchanged']
print('HAVOK_AUDIT_OK', [(r['name'],r['faces']) for r in report['collision_outputs']], flush=True)
