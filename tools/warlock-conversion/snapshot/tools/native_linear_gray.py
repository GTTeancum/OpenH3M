"""Recover a stripped stock linear-gray texture from an intact H3 donor.

The same-named tag in a target cache is not proof of resident pixels. Some H3
maps retain its editor bitmap metadata but strip the resource control data.
Keep this recovery scoped to the audited static 1x1 default; render targets
and other engine-created textures must not be classified by this rule.
"""

NAME = r'shaders\default_bitmaps\bitmaps\gray_50_percent_linear'


def recover(materials, key):
    if key != ('bitm', NAME):
        return None
    native = getattr(materials, 'native_assets', None)
    if native is None:
        return None
    existing = native.i.resolved.get(key)
    if existing is None:
        return None
    c = materials.target
    tag = c.tags.get(existing[1] & 65535)
    if tag is None:  # Already imported into this builder.
        return None
    if tag['group'] != 'bitm' or tag['salt'] != existing[1] >> 16:
        raise ValueError('Invalid resolved linear-gray bitmap')
    images = c.block(tag['offset'] + 96, 48)
    if (len(images) != 1 or c.unpack('HH', images[0] + 4) != (1, 1)
            or c.unpack('H', images[0] + 12)[0] != 11
            or c.data[images[0] + 21] != 3):
        raise ValueError('Stock linear-gray bitmap shape/format changed; re-audit')
    zone = next(t['offset'] for t in c.tags.values() if t['group'] == 'zone')
    resources = c.block(zone + 88, 64)
    handles = [c.u(row) for field in (140, 152)
               for row in c.block(tag['offset'] + field, 8)]
    def resident(datum):
        index = datum & 65535
        return (datum != 0xffffffff and index < len(resources)
                and c.unpack('H', resources[index] + 16)[0] == datum >> 16
                and c.u(resources[index] + 24) != 0)
    if handles and all(resident(datum) for datum in handles):
        return None
    restored = native.import_named(key, force=True)
    if restored is None or restored[0] != 'bitm' or restored == existing:
        raise ValueError('No intact stock linear-gray replacement imported')
    materials.done[key] = restored[1]
    materials.report.append(dict(source=NAME, native_resource_recovered=True,
                                 old_datum=hex(existing[1]), new_datum=hex(restored[1]),
                                 reason='Target bitmap retained metadata but stripped its resource'))
    return restored[1]
