"""Restore Forge World architecture materials without altering terrain or gameplay."""
import argparse
from pathlib import Path
from patch_gulch_water import build

NAMES = {r'levels\multi\forge_halo\shaders\forge_halo_forerunner_' + suffix
         for suffix in ('wall_dark', 'trim', 'wall', 'pipe', 'trim_dark', 'base',
                        'hall', 'wall_vert', 'base_dark', 'panel')}
ACCEPTED = {
    'forge_gulch': 'f00aaf7e6304c94c85569fc7b5f0f8e185af744aacd140a0810711717933babb',
    'forge_island': '96d62a150eddd1fd343d39b9c76b2e6c1d792dbbe7669a95d773854edac6e9cf',
}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('basis', 'source', 'disc', 'xex', 'output', 'report'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--map', choices=ACCEPTED, required=True)
    args = vars(parser.parse_args())
    expected = ACCEPTED[args.pop('map')]
    build(**args, names=NAMES, expected_sha256=expected)
