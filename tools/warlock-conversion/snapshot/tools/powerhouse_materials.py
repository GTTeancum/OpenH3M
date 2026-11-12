"""Powerhouse exact native shader families, audited against original disc caches.

Source/target parameter sets match; only implicit unit bump strength may differ.
Audit: work/powerhouse/preflight-exact-materials.py. Runtime source variant is checked.
"""

NATIVE_VARIANTS = {
    '040_lamp_small': '_0_0_0_1_0_0_0_0_0_0',  # docks.map
    '040_lamp_small_illum': '_0_1_1_1_2_2_1_0_0_0',  # chill.map
    '040_lamp_small_illum_red': '_0_1_1_1_2_2_1_0_0_0',  # chill.map
    '040_welded_metal': '_0_0_0_0_0_0_0_0_0_0',  # bunkerworld.map
    '30_settlement_sandstone': '_0_2_0_1_0_0_0_0_0_0',  # guardian.map
    'com_antennae_plastic': '_0_1_0_1_2_0_0_0_0_0',  # armory.map
    'concrete_building_holer_02': '_0_1_0_0_0_0_0_0_0_0',  # chill.map
    'concrete_cracked': '_0_1_0_0_0_0_0_0_0_0',  # chill.map
    'dark_metal_pioneer': '_0_0_0_0_0_0_0_0_0_0',  # bunkerworld.map
    'electrical_generator_decals': '_0_0_0_0_0_0_0_3_0_0',  # armory.map
    'grate_ceiling_panel_trim': '_0_2_0_1_2_1_0_0_1_0',  # chill.map
    'kitchen_sink': '_0_1_0_1_2_2_0_0_0_0',  # armory.map
    'm10_light_illum': '_0_0_0_0_0_0_1_0_1_0',  # bunkerworld.map
    'm10_metal_plate_welded': '_0_0_0_0_0_0_0_0_0_0',  # bunkerworld.map
    'm30_concrete_building_holer': '_0_2_0_0_0_0_0_0_0_0',  # bunkerworld.map
    'm30_concrete_pegsquares': '_0_1_0_1_2_0_0_0_0_0',  # armory.map
    'm30_dam_brick': '_0_0_0_1_0_0_0_0_0_0',  # docks.map
    'm30_dam_cards_a': '_0_0_0_0_0_0_0_3_0_0',  # armory.map
    'm30_door_slat': '_0_2_0_1_2_2_0_0_0_0',  # armory.map
    'm30_garage_floor_laquered': '_0_1_0_0_0_0_0_0_0_0',  # chill.map
    'm30_glass_green': '_0_1_0_2_2_1_0_3_0_0',  # armory.map
    'm30_glass_green_v2': '_0_1_0_2_2_1_0_3_0_0',  # armory.map
    'm30_metal': '_0_2_0_1_2_2_0_0_0_0',  # armory.map
    'm30_metal_corrugated_reinforced_outer_wall': '_7_2_0_1_2_2_0_0_0_0',  # armory.map
    'm30_metal_dark_01': '_0_2_0_1_2_1_0_0_0_0',  # armory.map
    'm30_metal_dark_01_v2': '_0_2_0_1_2_1_0_0_0_0',  # armory.map
    'm30_metal_flashing': '_0_1_0_1_2_2_0_0_1_0',  # chill.map
    'm30_metal_flat': '_0_1_0_1_2_0_0_0_0_0',  # armory.map
    'm30_metal_ibeam': '_0_2_0_1_2_2_0_0_0_0',  # armory.map
    'm30_metal_painted_blue': '_0_2_0_1_2_2_0_0_0_0',  # armory.map
    'm30_metal_painted_green': '_0_2_0_1_2_2_0_0_0_0',  # armory.map
    'm30_metal_painted_transformer': '_0_2_0_1_2_2_0_0_0_0',  # armory.map
    'm30_metal_plate_welded': '_7_2_0_1_2_2_0_0_0_0',  # armory.map
    'm30_non_slip_rubber': '_0_2_0_1_2_2_0_0_0_0',  # armory.map
    'm30_panel_vinyl': '_0_2_0_1_2_2_0_0_0_0',  # armory.map
    'm30_panel_vinyl_trim': '_0_1_0_1_2_2_0_0_0_0',  # armory.map
    'm30_sandstone_30_settlement': '_0_2_0_1_0_0_0_0_0_0',  # guardian.map
    'm30_stucco_spackled': '_0_2_0_0_0_0_0_0_0_0',  # bunkerworld.map
    'm30_water': '_0_0_0_0_0_0_0_0_0_0',  # bunkerworld.map
    'm30_wire_bundled': '_0_1_0_2_2_2_0_0_0_0',  # armory.map
    'm30_wood_bleached': '_0_2_0_1_0_0_0_0_0_0',  # guardian.map
    'm30_wood_plank_weathered': '_0_1_0_1_2_0_0_0_0_0',  # armory.map
    'm30_wood_trim_bleached': '_0_2_0_0_0_0_0_0_0_0',  # bunkerworld.map
    'm35_bridge_road_asphalt': '_0_2_0_1_2_0_0_0_0_0',  # armory.map
    'metal_dark_01': '_0_2_0_1_2_0_0_0_0_0',  # armory.map
    'metal_dark_01_v2': '_0_2_0_1_2_0_0_0_0_0',  # armory.map
    'metal_panel_battered_01': '_6_2_0_1_2_2_0_0_0_0',  # salvation.map
    'ropes': '_0_1_0_0_0_0_0_0_0_0',  # chill.map
    'tree_arid_a_leaves': '_0_1_1_0_0_0_0_0_0_0',  # snowbound.map
    'tree_arid_lod_branches': '_0_0_0_0_0_0_0_3_0_0',  # armory.map
    'vet_control_panel_screen': '_7_0_0_0_0_0_4_0_0_0',  # bunkerworld.map
    'water_tank_horizontal_decal': '_0_0_0_0_0_0_0_3_0_0',  # armory.map
    'wood_fine_grain': '_0_1_0_1_2_1_0_0_0_0',  # armory.map
    'wood_floor_weathered': '_0_1_0_1_2_2_0_0_0_0',  # armory.map
    'y_set_round_illum_a': '_0_0_0_0_0_0_1_0_1_0',  # bunkerworld.map
    'y_set_settlement_piperoom_uber': '_0_0_0_0_0_0_1_0_1_0',  # bunkerworld.map
}

# Full paths avoid collisions with similarly named BSP and other-map materials.
# Source/native parameter sets and boolean bits match; see
# work/powerhouse/remaining-material-preflight-28.json.
NATIVE_OBJECT_VARIANTS = {
    'levels\\shared\\shaders\\multi\\checker': '_0_0_0_0_0_0_0_0_0_0',  # bunkerworld.map
    'objects\\gear\\human\\residential\\shaders\\control_panel_screen': '_0_0_0_0_0_0_4_1_0_0',  # chill.map
    'objects\\gear\\human\\residential\\shaders\\glass_broken': '_0_1_0_2_5_2_0_0_0_0',  # zanzibar.map
    'objects\\gear\\human\\residential\\shaders\\holo_projector': '_0_0_0_0_0_0_3_1_0_0',  # armory.map
    'objects\\gear\\human\\residential\\shaders\\logo_optican': '_0_0_0_0_0_0_0_3_0_0',  # armory.map
    'objects\\gear\\human\\residential\\shaders\\m30_light_illum': '_0_0_0_0_0_0_1_0_0_0',  # armory.map
    'objects\\gear\\human\\residential\\shaders\\m30_metal': '_0_2_0_1_2_2_0_0_0_0',  # armory.map
    'objects\\gear\\human\\residential\\shaders\\m30_metal_dark_01': '_0_2_0_1_2_1_0_0_0_0',  # armory.map
    'objects\\gear\\human\\residential\\shaders\\oni_illum_green_off': '_0_0_0_0_0_0_1_0_0_0',  # armory.map
    'objects\\gear\\human\\residential\\shaders\\vet_computer_wires': '_0_0_0_1_2_0_0_0_0_0',  # cyberdyne.map
    'priception\\objects\\weapons\\rifle\\dmr\\shaders\\reflections_other': '_0_0_0_0_0_0_0_0_0_0',  # bunkerworld.map
    'priception\\objects\\weapons\\rifle\\dmr\\shaders\\storm_dmr_default_eaglecrest': '_0_0_1_0_0_0_0_0_0_0',  # armory.map
}

# MCC boolean use_material_texture maps to the named native float switch.
# All other inputs match; verified in remaining-material-preflight-28.json.
NATIVE_OBJECT_VARIANTS.update({
    'levels\\multi\\s3d_powerhouse\\shaders\\040_garage_wires': '_0_1_0_1_1_1_0_0_0_0',  # construct.map
    'levels\\multi\\s3d_powerhouse\\shaders\\bolts': '_0_1_0_1_1_0_0_0_0_0',  # armory.map
    'levels\\multi\\s3d_powerhouse\\shaders\\com_antennae': '_0_1_0_1_1_0_0_0_0_0',  # armory.map
    'levels\\multi\\s3d_powerhouse\\shaders\\concrete_building_holer_01': '_0_1_0_1_1_0_0_0_0_0',  # armory.map
    'levels\\multi\\s3d_powerhouse\\shaders\\generic_damaged_metal': '_0_1_0_1_1_2_0_0_0_0',  # armory.map
    'levels\\multi\\s3d_powerhouse\\shaders\\hvac': '_0_2_0_1_1_2_0_0_0_0',  # armory.map
    'levels\\multi\\s3d_powerhouse\\shaders\\industrial_control_panel': '_0_2_0_1_1_0_0_0_0_0',  # chillout.map
    'levels\\multi\\s3d_powerhouse\\shaders\\kitchen_dishwasher': '_0_2_0_1_1_0_0_0_0_0',  # chillout.map
    'levels\\multi\\s3d_powerhouse\\shaders\\kitchen_dishwasher_metal': '_0_1_0_1_1_0_0_0_0_0',  # armory.map
    'levels\\multi\\s3d_powerhouse\\shaders\\m30_concrete_broken': '_0_2_0_1_1_0_0_0_0_1',  # armory.map
    'levels\\multi\\s3d_powerhouse\\shaders\\m30_concrete_foundation_aged': '_0_2_0_1_1_0_0_0_0_0',  # chillout.map
    'levels\\multi\\s3d_powerhouse\\shaders\\m30_concrete_leaky': '_0_2_0_1_1_0_0_0_0_1',  # armory.map
    'levels\\multi\\s3d_powerhouse\\shaders\\m30_concrete_pitted': '_0_1_0_1_1_2_0_0_0_0',  # armory.map
    'levels\\multi\\s3d_powerhouse\\shaders\\m30_dam_glass': '_0_0_0_0_1_2_0_0_0_0',  # docks.map
    'levels\\multi\\s3d_powerhouse\\shaders\\m30_dam_grate_opaque': '_0_1_0_1_1_2_0_0_1_0',  # armory.map
    'levels\\multi\\s3d_powerhouse\\shaders\\m30_dam_metal': '_0_0_0_0_1_0_0_0_0_0',  # warehouse.map
    'levels\\multi\\s3d_powerhouse\\shaders\\m30_garage_wires_railings': '_0_1_0_1_1_1_0_0_0_0',  # construct.map
    'levels\\multi\\s3d_powerhouse\\shaders\\m30_metal_corrugated_reinforced_outer_wall_flat': '_7_2_0_1_1_2_0_0_0_0',  # armory.map
    'levels\\multi\\s3d_powerhouse\\shaders\\m30_metal_corrugated_reinforced_outer_wall_flat_v2': '_7_2_0_1_1_2_0_0_0_0',  # armory.map
    'levels\\multi\\s3d_powerhouse\\shaders\\m30_metal_ext_a': '_0_1_0_1_1_1_0_0_0_0',  # construct.map
    'levels\\multi\\s3d_powerhouse\\shaders\\m30_metal_ext_a_v2': '_0_1_0_1_1_1_0_0_0_0',  # construct.map
    'levels\\multi\\s3d_powerhouse\\shaders\\m30_metal_gate_details': '_0_1_0_1_1_2_0_0_0_0',  # armory.map
    'levels\\multi\\s3d_powerhouse\\shaders\\m30_metal_gate_galvanized_lighter': '_0_0_0_1_1_2_0_0_0_0',  # armory.map
    'levels\\multi\\s3d_powerhouse\\shaders\\m30_metal_gate_rust': '_0_1_0_1_1_2_0_0_0_0',  # armory.map
    'levels\\multi\\s3d_powerhouse\\shaders\\m30_metal_panel_battered': '_6_2_0_1_1_2_0_0_0_0',  # shrine.map
    'levels\\multi\\s3d_powerhouse\\shaders\\m30_metal_pioneer_trim_02': '_7_2_0_1_1_2_0_0_0_0',  # armory.map
    'levels\\multi\\s3d_powerhouse\\shaders\\m30_metal_pioneer_trim_04': '_7_2_0_1_1_2_0_0_0_0',  # armory.map
    'levels\\multi\\s3d_powerhouse\\shaders\\m30_metal_pioneer_trim_04_v2': '_7_2_0_1_1_2_0_0_0_0',  # armory.map
    'levels\\multi\\s3d_powerhouse\\shaders\\m30_metal_pipe_a_smooth': '_0_2_0_1_1_1_0_0_0_0',  # sidewinder.map
    'levels\\multi\\s3d_powerhouse\\shaders\\m30_metal_pipe_b': '_0_2_0_1_1_2_0_0_1_0',  # armory.map
    'levels\\multi\\s3d_powerhouse\\shaders\\m30_metal_pipe_coupling': '_0_1_0_1_1_2_0_0_0_0',  # armory.map
    'levels\\multi\\s3d_powerhouse\\shaders\\m30_metal_pipe_weave': '_0_2_0_1_1_2_0_0_0_0',  # armory.map
    'levels\\multi\\s3d_powerhouse\\shaders\\m30_metal_tech_trim': '_0_2_0_1_1_2_0_0_0_0',  # armory.map
    'levels\\multi\\s3d_powerhouse\\shaders\\m30_metal_tech_trim_v2': '_0_2_0_1_1_2_0_0_0_0',  # armory.map
    'levels\\multi\\s3d_powerhouse\\shaders\\m30_tile_bathroom': '_7_2_0_1_1_2_0_0_0_0',  # armory.map
    'levels\\multi\\s3d_powerhouse\\shaders\\m30_tile_bathroom_floor': '_7_2_0_1_1_2_0_0_0_0',  # armory.map
    'levels\\multi\\s3d_powerhouse\\shaders\\oven': '_0_2_0_1_1_2_0_0_0_0',  # armory.map
    'levels\\multi\\s3d_powerhouse\\shaders\\oven_hardware': '_0_1_0_1_1_2_0_0_0_0',  # armory.map
    'levels\\multi\\s3d_powerhouse\\shaders\\roof_grid': '_0_2_0_1_1_1_0_0_0_0',  # sidewinder.map
    'levels\\multi\\s3d_powerhouse\\shaders\\steel_basic': '_0_1_0_1_1_2_0_0_0_0',  # armory.map
    'levels\\multi\\s3d_powerhouse\\shaders\\water_tank_horizontal': '_0_1_0_1_1_2_0_0_0_0',  # armory.map
    'objects\\gear\\human\\residential\\shaders\\bolts': '_0_1_0_1_1_0_0_0_0_0',  # armory.map
    'objects\\gear\\human\\residential\\shaders\\chrome_pitted': '_0_1_0_1_1_2_0_0_0_0',  # armory.map
    'objects\\gear\\human\\residential\\shaders\\chrome_weathered': '_0_1_0_1_1_2_0_0_0_0',  # armory.map
    'objects\\gear\\human\\residential\\shaders\\glass_broken_tilable': '_0_1_0_2_1_2_0_3_0_0',  # ghosttown.map
    'objects\\gear\\human\\residential\\shaders\\glass_dark_edge': '_0_2_0_2_1_2_0_0_0_0',  # zanzibar.map
    'objects\\gear\\human\\residential\\shaders\\m30_metal_ext_a': '_0_1_0_1_1_1_0_0_0_0',  # construct.map
    'objects\\gear\\human\\residential\\shaders\\m30_metal_pipe_b': '_0_2_0_1_1_2_0_0_1_0',  # armory.map
    'objects\\gear\\human\\residential\\shaders\\pioneer_whiteboard_glass_broken': '_0_1_0_1_1_0_0_3_0_0',  # armory.map
    'objects\\gear\\human\\residential\\shaders\\vet_computer': '_0_1_0_1_1_2_0_0_0_0',  # armory.map
})
