# Beaver Creek base lights: Halo 2 lit the bases with its emissive light panels (bc_light_blue / bc_light_red,
# emissive_color, emissive_power 0.1). Halo 3's equivalent is the structure lighting info's per-material emissive
# (stock Guardian: 9 emissive materials, power 2..12, quality 1). Material info follows the ASS material order.
import sys
sys.path.insert(0, r'C:\Programming\GitHub\OpenH3M\.local\tombstone\tagedit')
import te
T = r'levels\test\beavercreek\beavercreek.scenario_structure_lighting_info'
POWER = float(sys.argv[1]) if len(sys.argv) > 1 else 4.0
LIGHTS = {14: '0.737255,0.211765,0.223529', 25: '0.737255,0.211765,0.223529',   # bc_light_red
          21: '0.06,0.61,0.94', 24: '0.06,0.61,0.94'}                            # bc_light_blue
ops = []
for i, col in LIGHTS.items():
    b = 'Block:material info[%d]/' % i
    ops += [{'op': 'set', 'tag': T, 'field': b + 'emissive power', 'value': str(POWER)},
            {'op': 'set', 'tag': T, 'field': b + 'emissive color', 'value': col},
            {'op': 'set', 'tag': T, 'field': b + 'emissive quality', 'value': '1'}]
print(te.edit(ops)[-200:])
