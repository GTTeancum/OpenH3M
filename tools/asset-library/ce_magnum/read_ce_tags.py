"""Read CE pistol tags to JSON with the unchanged General-101 tag interface.

Run inside background Blender (blender_env.run). JSON goes to
work/asset-library/_work/ce_magnum/ce-tags/<name>.json.
"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import blender_env
blender_env.enable('io_scene_halo')
from io_scene_halo.file_tag.tag_interface import tag_interface, tag_common

SRC = blender_env.ROOT / 'work/asset-library/_work/source/hceek/tags'
OUT = blender_env.ROOT / 'work/asset-library/_work/ce_magnum/ce-tags'
OUT.mkdir(parents=True, exist_ok=True)
game_defs, engine_tag, tag_defs, tag_groups, tag_extensions, _, _ = tag_interface.get_version_args('halo1', 0)
import os
merged = game_defs.generate_defs(tag_defs, os.path.join(os.path.dirname(tag_defs), os.path.basename(tag_defs) + '_merged_output'), tag_groups, tag_extensions)
for rel in sys.argv[sys.argv.index('--') + 1:]:
    d = tag_interface.read_file(merged, str(SRC) + os.sep, str(SRC / rel), 0, engine_tag=engine_tag)
    name = Path(rel.replace('\\', '/')).name
    (OUT / (name + '.json')).write_text(json.dumps(d, indent=1, default=str))
    print('READ', rel, flush=True)
