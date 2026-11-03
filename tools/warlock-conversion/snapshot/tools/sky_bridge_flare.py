"""User-authorized original-H3 flare behavior for the Sky Bridge playtest."""
from forge_sun_flare import import_flare
PREFIX = 'levels\\multi\\s3d_sky_bridgenew\\'
COUNTS = {PREFIX + suffix: count for suffix, count in (
    ('shaders\\lighting\\flare_projector', 8),
    ('shaders\\lighting\\flare_projector_illum', 3),
    ('sky\\shaders\\flare_sun_01', 27),
    ('sky\\shaders\\l_flare_01', 3),
    ('sky\\shaders\\flare_blue_sb_01', 3),
    ('sky\\shaders\\flare_antenna_01', 4),
    ('sky\\shaders\\flare_antenna_02', 4))}

def import_sky_bridge_flare(importer, datum):
    name = importer.source.name(datum & 65535)
    return import_flare(importer, datum, native_placement=True,
                        expected_reflections=COUNTS[name])
