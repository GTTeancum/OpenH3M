"""Foundation's diffuse-only cloud mask is not a specular consumer."""
SCENARIO = r'halo_2\levels\foundation\foundation'
MATERIAL = r'halo_2\levels\zanzibar\sky\shaders\clouds_low'
SOURCE_OPTIONS = [0, 0, 0, 1, 0, 0, 0, 5, 0, 0, 0, 0, 0]
TARGET_OPTIONS = [0, 0, 0, 0, 0, 0, 0, 5, 0, 0]
TEXTURES = ['base_map', 'detail_map']
CONSTANTS = ['base_map', 'detail_map', 'albedo_color']


def select_foundation_clouds(source, material, options, textures, constants):
    if (material != MATERIAL or [source.name(k) for k, t in source.tags.items()
                                if t['group'] == 'scnr'] != [SCENARIO]):
        return False
    if options != SOURCE_OPTIONS or textures != TEXTURES or constants != CONSTANTS:
        raise ValueError('Foundation clouds differ from audited diffuse-only material')
    return True
