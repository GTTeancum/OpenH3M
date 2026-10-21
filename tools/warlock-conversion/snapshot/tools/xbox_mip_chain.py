"""Packed 2D BC mip layout for original Xbox 360 resources.

Layout references: TagTool XboxBitmapUtils.GetXboxBitmapLevelOffset and
Xenia texture_util.GetPackedMipOffset. All authored BC blocks are retained.
"""
import numpy as np
from xbox_bitmap import addresses


def layout(width, height, count, bytes_per_block=16):
    if min(width, height) < 32 or any(v & (v-1) for v in (width, height)):
        raise ValueError('Mip chain requires power-of-two dimensions >= 32')
    if not 1 < count <= max(width, height).bit_length():
        raise ValueError('Invalid mip count')
    tail = min(width, height).bit_length()-1-4
    offset, rows = 0, []
    tail_offset = None
    for level in range(count):
        w, h = max(1, width >> level), max(1, height >> level)
        wb, hb = (w+3)//4, (h+3)//4
        x, y = 0, 0
        if level >= tail:
            if tail_offset is None:
                tail_offset = offset
            packed = level-tail
            if packed < 3:
                if width > height:
                    y = (16 >> packed)//4
                else:
                    x = (16 >> packed)//4
            elif width > height:
                x = ((width >> tail) >> (packed-2))//4
            else:
                y = ((height >> tail) >> (packed-2))//4
            pitch = (max(1, (width >> tail)+3)//4 + 31) & ~31
            block_height = (max(1, (height >> tail)+3)//4 + 31) & ~31
            pos = addresses(pitch, max(block_height, y+hb), bytes_per_block)[y:y+hb, x:x+wb]
            level_offset = tail_offset
        else:
            pitch, block_height = (wb+31)&~31, (hb+31)&~31
            pos = addresses(pitch, block_height, bytes_per_block)[:hb, :wb]
            level_offset = offset
            offset += pitch*block_height*bytes_per_block
        rows.append((level_offset+pos, wb*hb*bytes_per_block))
    size = max(int(pos.max())+bytes_per_block for pos, _ in rows)
    return rows, (size+4095)&~4095


def tile_chain(payload, width, height, count, fmt):
    if fmt not in (14, 15, 16, 33):
        raise ValueError('Packed mip encoder requires BC1/2/3/5')
    bpb = 8 if fmt == 14 else 16
    rows, size = layout(width, height, count, bpb)
    if len(payload) != sum(n for _, n in rows):
        raise ValueError('Authored mip chain length mismatch')
    out = np.zeros(size, dtype=np.uint8)
    consumed = 0
    for pos, length in rows:
        # Xenos 8-in-16 byte order; compression selectors are not reencoded.
        blocks = np.frombuffer(payload[consumed:consumed+length], dtype=np.uint8)
        blocks = blocks.reshape(-1, 2)[:, ::-1].reshape(-1, bpb)
        out[pos.reshape(-1, 1)+np.arange(bpb)] = blocks
        consumed += length
    return out.tobytes()
