"""Packed 2D BC mip layout for original Xbox 360 resources.

Layout references: TagTool XboxBitmapUtils.GetXboxBitmapLevelOffset and
Xenia texture_util.GetPackedMipOffset. All authored BC blocks are retained.
"""
import numpy as np
from xbox_bitmap import addresses


def layout(width, height, count, bytes_per_block=16, block_extent=4):
    if min(width, height) < 32 or any(v & (v-1) for v in (width, height)):
        raise ValueError('Mip chain requires power-of-two dimensions >= 32')
    if not 1 < count <= max(width, height).bit_length():
        raise ValueError('Invalid mip count')
    tail = min(width, height).bit_length()-1-4
    offset, rows = 0, []
    tail_offset = None
    for level in range(count):
        w, h = max(1, width >> level), max(1, height >> level)
        wb, hb = (w+block_extent-1)//block_extent, (h+block_extent-1)//block_extent
        x, y = 0, 0
        if level >= tail:
            if tail_offset is None:
                tail_offset = offset
            packed = level-tail
            if packed < 3:
                if width > height:
                    y = (16 >> packed)//block_extent
                else:
                    x = (16 >> packed)//block_extent
            elif width > height:
                x = ((width >> tail) >> (packed-2))//block_extent
            else:
                y = ((height >> tail) >> (packed-2))//block_extent
            pitch = (max(1, (width >> tail)+block_extent-1)//block_extent + 31) & ~31
            block_height = (max(1, (height >> tail)+block_extent-1)//block_extent + 31) & ~31
            pos = addresses(pitch, max(block_height, y+hb), bytes_per_block)[y:y+hb, x:x+wb]
            level_offset = tail_offset
        else:
            pitch, block_height = (wb+31)&~31, (hb+31)&~31
            pos = addresses(pitch, block_height, bytes_per_block)[:hb, :wb]
            level_offset = offset
            # Xenos subresources start on 4 KiB boundaries (TagTool
            # GetXboxBitmapLevelOffset / Xenia array_slice_stride_bytes).
            # The 32-square V8U8 level occupies 2 KiB logically but addresses
            # both banks; the packed tail must not start inside that page.
            offset += (pitch*block_height*bytes_per_block+4095) & ~4095
        rows.append((level_offset+pos, wb*hb*bytes_per_block))
    size = max(int(pos.max())+bytes_per_block for pos, _ in rows)
    return rows, (size+4095)&~4095


def tile_chain(payload, width, height, count, fmt):
    if fmt not in (11, 14, 15, 16, 22, 26, 28, 33):
        raise ValueError('Packed mip encoder requires BC1/2/3/5')
    bpb = 2 if fmt == 22 else 4 if fmt in (11,26) else 8 if fmt in (14,28) else 16
    rows, size = layout(width, height, count, bpb, 1 if fmt in (11,22,26,28) else 4)
    if len(payload) != sum(n for _, n in rows):
        raise ValueError('Authored mip chain length mismatch')
    out = np.zeros(size, dtype=np.uint8)
    consumed = 0
    for pos, length in rows:
        # Xenos 8-in-16 byte order; compression selectors are not reencoded.
        blocks = np.frombuffer(payload[consumed:consumed+length], dtype=np.uint8)
        blocks = blocks.reshape(-1, 4 if fmt in (11,26) else 2)[:, ::-1].reshape(-1, bpb)
        out[pos.reshape(-1, 1)+np.arange(bpb)] = blocks
        consumed += length
    return out.tobytes()


def cube_layout(width, count, fmt):
    """Mip-major cube slices, with one packed mip tail per face.

    GetXboxBitmapLevelOffset advances over all six faces at each mip; six
    concatenated complete 2D mip chains would address the wrong face/level.
    """
    if fmt not in (11,14,15,16):
        raise ValueError('Unsupported cube mip format')
    bpb,extent=(4,1) if fmt==11 else (8 if fmt==14 else 16,4)
    rows,_=layout(width,width,count,bpb,extent)
    tail=width.bit_length()-1-4
    base=0;levels=[]
    for level,(pos,length) in enumerate(rows):
        effective=min(level,tail)
        blocks=(max(1,width>>effective)+extent-1)//extent
        aligned=(blocks+31)&~31
        stride=(aligned*aligned*bpb+4095)&~4095
        levels.append((base,stride,pos-base,length))
        if level<tail:base+=stride
    result=[]
    for face in range(6):
        result.append([(6*base+face*stride+local,length) for base,stride,local,length in levels])
    size=6*(levels[-1][0]+levels[-1][1])
    return result,size


def tile_cube_chain(payload,width,count,fmt):
    faces,size=cube_layout(width,count,fmt)
    if len(payload)!=sum(n for face in faces for _,n in face):
        raise ValueError('Cubemap authored face/mip size mismatch')
    bpb=4 if fmt==11 else 8 if fmt==14 else 16
    out=np.zeros(size,dtype=np.uint8)
    consumed=0
    for face in faces:
        for pos,length in face:
            blocks=np.frombuffer(payload[consumed:consumed+length],dtype=np.uint8)
            blocks=blocks.reshape(-1,4 if fmt==11 else 2)[:,::-1].reshape(-1,bpb)
            out[pos.reshape(-1,1)+np.arange(bpb)]=blocks
            consumed+=length
    return out.tobytes()
