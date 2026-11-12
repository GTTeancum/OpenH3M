"""Read original selection collision metadata; does not execute game code."""
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / "work/h4-forge-research"
SOURCE = RESEARCH / "disc2-assets/ca_forge_ravine.map"

with SOURCE.open("rb") as source:
    header = source.read(0x500)
    u = lambda offset: struct.unpack_from(">I", header, offset)[0]
    start = (u(0x484) + u(0x49c)) & 0xffffffff
    base = u(0x2f8)
    size = source.seek(0, 2)

    def read(pointer, length):
        offset = pointer - base + start
        if offset < 0 or offset + length > size:
            raise ValueError("Tag pointer outside source cache")
        source.seek(offset)
        data = source.read(length)
        if len(data) != length:
            raise ValueError("Truncated source cache")
        return data

    group_count, groups, tag_count, tags = struct.unpack(">4I", read(u(0x10), 16))
    matches = []
    for index in range(tag_count):
        group, salt, pointer = struct.unpack(">HHI", read(tags + index * 8, 8))
        if group == 0xffff or pointer in (0, 0xffffffff):
            continue
        if group >= group_count:
            raise ValueError("Invalid tag group")
        if read(groups + group * 16, 4) == b"hcfd":
            matches.append((index, pointer))
    if len(matches) != 1:
        raise ValueError("Expected one collision filter tag")
    index, pointer = matches[0]
    data = read(pointer, 0x110)
    lookup = struct.unpack_from(">32I", data, 16 + 52)

#8236D730 patches the cached group-filter ray interface to82000F00.
# Its slot4 calls82286F38 ->82D817C0 ->82D813F8.
with (RESEARCH / "h4-image.bin").open("rb") as image:
    image.seek(0xf00)
    vtable = struct.unpack(">2I", image.read(8))
    if vtable[1] != 0x82286f38:
        raise ValueError("Unexpected original ray filter callback")

layer = 26  #8244C740 request0 ->82417550 ray input36.
mask = lookup[layer]
report = dict(
    source=str(SOURCE.relative_to(ROOT)), tag_index=index,
    tag_pointer=hex(pointer), group_filter_offset=16,
    cached_ray_interface=hex(struct.unpack_from(">I", data, 36)[0]),
    runtime_ray_interface="0x82000f00", callback=hex(vtable[1]),
    callback_chain=["8236D730", "82286F38", "82D817C0", "82D813F8"],
    lookup=[f"0x{x:08x}" for x in lookup], ray_layer=layer,
    ray_layer_mask=f"0x{mask:08x}",
    rejected_layers=[i for i in range(32) if not mask & (1 << i)],
    rule="lookup[ray_filter_info & 31] & (1 << (shape_filter_info & 31))",
    qualification="Ray filter info is26 with zero system-group bits; same nonzero system-group branch does not apply to this ray.",
    limitation="Source extraction only. Subsequent H4 collector gates and native H3 correspondence remain separate integration obligations.",
)
out = RESEARCH / "isolated/selection-filter.json"
out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
