"""Plot actual source collision terrain for planning; this is not a game capture."""
import argparse
import os
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    repo = Path(__file__).resolve().parents[4]
    output = args.output.resolve()
    if not output.is_relative_to(repo):
        raise ValueError('Plot must remain inside repository')
    output.parent.mkdir(parents=True, exist_ok=True)
    os.environ['MPLCONFIGDIR'] = str(repo / 'work/forge-world/matplotlib')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    import numpy as np
    from cache_reader import Cache
    from forge_collision_mesh import read_mesh, surface_loops, positions
    c = Cache(args.source, True)
    try:
        tag, arrays = read_mesh(c)
        xyz = positions(arrays)
        loops = surface_loops(arrays)
        # Rotate the top-down view so the canyon lies to the right, as in the
        # user's perspective sketch. Axis labels retain source coordinates.
        materials = c.block(tag['offset'] + 0x28, 24)
        visible = [j for j, surface in enumerate(arrays[5])
                   if c.u(materials[surface[2]] + 12) != 0xffffffff]
        visible.sort(key=lambda j: xyz[loops[j], 2].mean())
        polys = [xyz[loops[j]][:, [1, 0]] * [-1, 1] for j in visible]
        heights = np.array([xyz[loops[j], 2].mean() for j in visible])
        fig, ax = plt.subplots(figsize=(11, 8))
        mesh = PolyCollection(polys, array=heights, cmap='terrain',
                              edgecolors='none', clim=(-5, 70))
        ax.add_collection(mesh)
        from forge_gulch_boundary import BOUNDARY
        boundary = np.asarray(BOUNDARY)
        ax.plot(-boundary[:, 1], boundary[:, 0], color='red', linewidth=2,
                label='Forge Gulch boundary draft (user sketch)')
        ax.legend(loc='upper left')
        ax.autoscale_view()
        ax.set_aspect('equal')
        ax.set_xlabel('Source -Y'); ax.set_ylabel('Source X')
        ax.set_title('Forge World: authored collision terrain (top-down planning view)')
        for text, x, y in [('Gulch', -55, -120), ('Island', 50, 50),
                           ('Sanctuary', 60, 220), ('Beach cave', -23, -15),
                           ('Waterfall', 100, 235), ('Montana', 0, -150)]:
            ax.text(-y, x, text, fontsize=8, ha='center',
                    bbox={'facecolor':'white', 'alpha':0.8, 'edgecolor':'none'})
        fig.colorbar(mesh, ax=ax, label='Source height Z')
        fig.tight_layout(); fig.savefig(output, dpi=120); plt.close(fig)
        print(output)
    finally:
        c.close()


if __name__ == '__main__':
    main()
