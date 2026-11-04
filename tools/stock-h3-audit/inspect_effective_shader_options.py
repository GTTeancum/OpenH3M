"""Use unmodified Foundry readers to inspect active Reach options and defaults.

No Blender nodes, tag writes or H3 shader generation.
"""
import json
import hashlib
from pathlib import Path
import runpy
import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'work/stock-h3-audit'
runpy.run_path(str(ROOT / 'tools/stock-h3-audit/check_foundry.py'))
project = bpy.context.preferences.addons['io_scene_foundry'].preferences.projects.add()
project.name = project.project_name = 'Reach effective shader inspection'
kit = ROOT / 'work/editing-kits/hrek'
project.project_path = str(kit)
project.tags_directory = str(kit / 'tags')
project.data_directory = str(kit / 'data')
project.corinth = False
bpy.context.scene.nwo.scene_project = project.name
bpy.context.scene.nwo_export.show_output = False
from io_scene_foundry.managed_blam.shader import ShaderTag
from io_scene_foundry.managed_blam.render_method_definition import RenderMethodDefinitionTag
from io_scene_foundry.managed_blam.render_method_option import RenderMethodOptionTag
from io_scene_foundry.managed_blam import mb_init
mb_init()
from Bungie.Tags import TagPath

paths = json.loads((OUT / 'reach-source-references.json').read_text())['surface_references']
report = {}
for path in paths:
    categories = []
    source = kit / 'tags' / path
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    # A string passed to ShaderTag enforces .shader even for terrain/glass.
    # An explicit official TagPath preserves the source group. Never create tags.
    tag_path = TagPath.FromPathAndExtension(*path.rsplit('.', 1))
    with ShaderTag(path=tag_path, tag_must_exist=True) as shader:
        if not shader.definition.Path:
            report[path] = dict(error='No render method definition')
            continue
        with RenderMethodDefinitionTag(path=shader.definition.Path, tag_must_exist=True) as definition:
            for index, category in enumerate(definition.block_categories.Elements):
                if index >= shader.block_options.Elements.Count:
                    raise RuntimeError(f'Missing source option index: {path}: {index}')
                option_index = shader._option_value_from_index(index)
                selected = category.Fields[1].Elements[option_index]
                defaults = {}
                option_path = selected.Fields[1].Path
                if option_path:
                    with RenderMethodOptionTag(path=option_path, tag_must_exist=True) as option:
                        for name, parameter in option.get_option_parameters().items():
                            if parameter.type == 0:
                                defaults[name] = str(parameter.default_bitmap.RelativePathWithExtension) if parameter.default_bitmap else None
                categories.append(dict(category=category.Fields[0].GetStringData(), index=option_index,
                                       option=selected.Fields[0].GetStringData(),
                                       tag=str(option_path.RelativePathWithExtension) if option_path else None,
                                       bitmap_defaults=defaults))
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    report[path] = dict(categories=categories, source_sha256=before)
(OUT / 'reach-effective-shader-options.json').write_text(json.dumps(report, indent=2) + '\n')
print('EFFECTIVE_SOURCE_OPTIONS_INSPECTED', len(report), flush=True)
