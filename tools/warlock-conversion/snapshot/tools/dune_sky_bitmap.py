"""Preserve the audited Dune single-mip sky image, without synthesizing mips."""
import hashlib
from dune_flare import SCENARIO, BUILD

NAME = r'levels\skies\multi\zanzibar\bitmaps\sky_dome'
PIXEL_SHA256 = 'de8f0abd696ed6cf05a557e4a5ebcf1c9cbf918bca73c387f47c03d90191ad53'


def resolution(source, name, bitmaps, tag):
    if name != NAME or [source.name(k) for k, t in source.tags.items()
                       if t['group'] == 'scnr'] != [SCENARIO]:
        return None
    build = bytes(source.data[0xa0:0xc0]).split(b'\0', 1)[0].decode('ascii')
    info = bitmaps.info(tag)
    if (build != BUILD or len(info) != 1 or
            tuple(info[0][k] for k in ('width', 'height', 'format', 'mips')) != (2048, 2048, 11, 1)):
        raise ValueError('Dune authored sky bitmap layout changed')
    pixels = bitmaps.pixels(tag)
    if len(pixels) != 16777216 or hashlib.sha256(pixels).hexdigest() != PIXEL_SHA256:
        raise ValueError('Dune authored sky bitmap pixels changed')
    return 2048
