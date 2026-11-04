"""Approved Reach glass channel rearrangement with Blender's compositor.

Run in background Blender. The original images/tags remain unchanged. This
prepares a working image only; it does not establish native H3 appearance.
"""
import bpy
import hashlib
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'work/stock-h3-audit'
KIT = ROOT / 'work/editing-kits/hrek'
DEST = OUT / 'glass-channel-preparation'
DEST.mkdir(exist_ok=True)
runpy.run_path(str(ROOT / 'tools/stock-h3-audit/check_foundry.py'))
project = bpy.context.preferences.addons['io_scene_foundry'].preferences.projects.add()
project.name = project.project_name = 'Approved Reach glass channel preparation'
project.project_path = str(KIT)
project.tags_directory = str(KIT / 'tags')
project.data_directory = str(KIT / 'data')
project.corinth = False
bpy.context.scene.nwo.scene_project = project.name
from io_scene_foundry.managed_blam.bitmap import BitmapTag
from io_scene_foundry.managed_blam import mb_init
mb_init()
sys.path.insert(0, str(OUT / 'python-packages'))
from PIL import Image, ImageChops

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

sources = {}
hashes = {}
for role, stem in [('base', 'forge_halo_forerunner_glass_diff'),
                   ('opacity', 'forge_halo_forerunner_glass_opacity')]:
    path = Path('levels/multi/forge_halo/bitmaps') / (stem + '.bitmap')
    tag = KIT / 'tags' / path
    image = (KIT / 'data' / path).with_suffix('.tiff')
    hashes[str(tag)] = sha(tag)
    hashes[str(image)] = sha(image)
    with BitmapTag(path=str(path), tag_must_exist=True) as bitmap:
        assert bitmap.block_bitmaps.Elements.Count == 1
        element = bitmap.block_bitmaps.Elements[0]
        curve = int(element.SelectField('CharEnum:curve').Value)
        assert curve == 3, 'Review source color space before repacking'
    with Image.open(image) as pixels:
        assert pixels.size == (512, 512)
        rgba = pixels.convert('RGBA')
        if role == 'base':
            assert rgba.getextrema()[:3] == ((12, 12), (12, 12), (12, 12))
        else:
            r, g, b, a = rgba.split()
            assert ImageChops.difference(r, g).getbbox() is None
            assert ImageChops.difference(r, b).getbbox() is None
    sources[role] = dict(image=str(image), native_curve=curve)

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 1
scene.render.resolution_x = scene.render.resolution_y = 512
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.view_settings.view_transform = 'Raw'
scene.view_settings.look = 'None'
scene.view_settings.exposure = 0
scene.view_settings.gamma = 1
scene.render.image_settings.file_format = 'TIFF'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.image_settings.color_depth = '8'
scene.render.image_settings.tiff_codec = 'DEFLATE'
scene.use_nodes = True
nodes = scene.node_tree.nodes
links = scene.node_tree.links
nodes.clear()
separators = {}
for index, (role, source) in enumerate(sources.items()):
    node = nodes.new('CompositorNodeImage')
    node.label = role + ': original Reach linear channels'
    node.location = (-600, -index * 300)
    node.image = bpy.data.images.load(source['image'], check_existing=False)
    node.image.colorspace_settings.name = 'Non-Color'
    node.image.alpha_mode = 'CHANNEL_PACKED'
    separate = nodes.new('CompositorNodeSeparateColor')
    separate.mode = 'RGB'
    separate.location = (-350, -index * 300)
    links.new(node.outputs['Image'], separate.inputs['Image'])
    separators[role] = separate
combine = nodes.new('CompositorNodeCombineColor')
combine.mode = 'RGB'
combine.label = 'Original RGB + original opacity grayscale as alpha'
combine.location = (-100, 0)
for channel in ['Red', 'Green', 'Blue']:
    links.new(separators['base'].outputs[channel], combine.inputs[channel])
links.new(separators['opacity'].outputs['Red'], combine.inputs['Alpha'])
premultiply = nodes.new('CompositorNodePremulKey')
premultiply.mapping = 'STRAIGHT_TO_PREMUL'
premultiply.location = (150, 0)
links.new(combine.outputs['Image'], premultiply.inputs['Image'])
output = nodes.new('CompositorNodeComposite')
output.location = (350, 0)
links.new(premultiply.outputs['Image'], output.inputs['Image'])
camera = bpy.data.objects.new('Compositor render camera', bpy.data.cameras.new('Compositor render camera'))
scene.collection.objects.link(camera)
scene.camera = camera
destination = DEST / 'bc_glass_color_opacity.tif'
scene.render.filepath = str(destination)
bpy.ops.wm.save_as_mainfile(filepath=str(DEST / 'glass-channel-preparation.blend'))
bpy.ops.render.render(write_still=True)

# Pixel inspection only; all image authoring above uses native Blender nodes.
with Image.open(sources['base']['image']) as image:
    base = image.convert('RGBA')
with Image.open(sources['opacity']['image']) as image:
    opacity = image.convert('RGBA').getchannel('R')
with Image.open(destination) as image:
    result = image.convert('RGBA')
assert result.size == base.size
rgb_error = ImageChops.difference(result.convert('RGB'), base.convert('RGB')).getextrema()
alpha_error = ImageChops.difference(result.getchannel('A'), opacity).getextrema()
assert all(hi <= 1 for lo, hi in rgb_error) and alpha_error[1] <= 1, (rgb_error, alpha_error)
for path, expected in hashes.items():
    assert sha(Path(path)) == expected, path
(DEST / 'report.json').write_text(json.dumps(dict(sources=sources, source_hashes=hashes,
    output=str(destination), output_sha256=sha(destination), size=list(result.size),
    max_rgb_errors=[v[1] for v in rgb_error], max_alpha_error=alpha_error[1],
    node_types=[n.bl_idname for n in nodes], output_ranges=result.getextrema(),
    source_curves='Both native curve 3 (linear): no gamma transform during channel rearrangement.',
    limitation='Approved channel preparation only. H3 import, UV assignment and MCC appearance still require verification.'), indent=2) + '\n')
print('GLASS_CHANNELS_PREPARED', destination, 'RGB_ERROR', rgb_error, 'ALPHA_ERROR', alpha_error, flush=True)
