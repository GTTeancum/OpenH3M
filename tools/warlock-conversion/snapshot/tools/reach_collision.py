"""Write retail collision metadata from explicitly expanded Reach geometry.

Input is the read-only bridge's CollisionModel export. Reach supernodes must
already have been expanded by TagTool's SupernodeToNodeConverter. No Reach
physics acceleration structures are copied into the Halo 3 collision tag.
"""
import struct


def serialize_collision(model, builder, translate_string):
    def sid(value):
        return translate_string(value['Value'])

    def block(out, at, rows, encode):
        payload = b''.join(encode(row) for row in rows)
        struct.pack_into('>III', out, at, len(rows), builder.alloc(payload) if rows else 0, 0)

    def short(value):
        if not -32768 <= value <= 65535:
            raise ValueError('Collision index exceeds retail width')
        return value & 65535

    def point(value):
        return value['X'], value['Y'], value['Z']

    def geometry(bsp):
        g = bsp['Geometry']
        if g['Bsp3dSupernodes']:
            raise ValueError('Reach collision supernodes were not expanded')
        out = bytearray(100)
        struct.pack_into('>h', out, 0, bsp['NodeIndex'])
        nodes, planes, leaves = g['Bsp3dNodes'], g['Planes'], g['Leaves']
        if len(planes) > 32768 or len(g['Surfaces']) > 32768:
            raise ValueError('Collision planes/surfaces exceed retail signed-index limits')
        for n in nodes:
            if n['Plane'] >= len(planes):
                raise ValueError('Collision node plane outside table')
            for child in (n['BackChild'], n['FrontChild']):
                if child == 0xffffff:
                    continue
                index = child & 0x7fffff
                if index >= (len(leaves) if child & 0x800000 else len(nodes)):
                    raise ValueError('Collision node child outside table')
        block(out, 4, nodes, lambda n: struct.pack('>Q', n['Value']))
        block(out, 16, planes, lambda p: struct.pack('>4f', *(p['Value'][a] for a in ('I', 'J', 'K', 'D'))))

        def leaf(row):
            if row['Flags2'] or row['Flags'] & ~1:
                raise ValueError('Unsupported Reach collision leaf flags')
            return struct.pack('>BBHI', row['Flags'], 0,
                               row['Bsp2dReferenceCount'], row['FirstBsp2dReference'])

        block(out, 28, leaves, leaf)
        block(out, 40, g['Bsp2dReferences'], lambda r: struct.pack('>HH',
              short(r['PlaneIndex']), short(r['Bsp2dNodeIndex'])))
        block(out, 52, g['Bsp2dNodes'], lambda r: struct.pack('>3fHH',
              *(r['Plane'][a] for a in ('I', 'J', 'D')),
              short(r['LeftChild']), short(r['RightChild'])))

        def surface(row):
            plane = short(row['Plane'])
            flags = row['Flags']
            if flags & 128:
                plane |= 32768
                flags &= ~128
            if (plane & 32767) >= len(planes) or flags & ~63:
                raise ValueError('Unsupported collision surface plane/flags')
            return struct.pack('>5HBB', plane, short(row['FirstEdge']),
                               short(row['MaterialIndex']), short(row['BreakableSurfaceSet']),
                               short(row['BreakableSurfaceIndex']), flags,
                               row['BestPlaneCalculationVertex'])

        block(out, 64, g['Surfaces'], surface)
        block(out, 76, g['Edges'], lambda r: struct.pack('>6H', *(short(r[k]) for k in
              ('StartVertex', 'EndVertex', 'ForwardEdge', 'ReverseEdge', 'LeftSurface', 'RightSurface'))))
        block(out, 88, g['Vertices'], lambda r: struct.pack('>3fHh',
              *point(r['Point']), short(r['FirstEdge']), r['Sink']))
        return bytes(out)

    def permutation(row):
        if row['BspPhysics'] or row['BspMoppCodes']:
            raise ValueError('Reach collision BSP physics requires separate conversion')
        out = bytearray(40)
        struct.pack_into('>I', out, 0, sid(row['Name']))
        block(out, 4, row['Bsps'], geometry)
        return bytes(out)

    def region(row):
        out = bytearray(16)
        struct.pack_into('>I', out, 0, sid(row['Name']))
        block(out, 4, row['Permutations'], permutation)
        return bytes(out)

    if model['CookieCutters'] or model['Flags'] & ~3:
        raise ValueError('Unsupported Reach collision root extensions')
    out = bytearray(68)
    # Reach PhysicsBuilt is compiler state. Existing H3 Forge pieces retain
    # only ContainsOpenEdges; their separate phmo tags supply rigid physics.
    struct.pack_into('>I', out, 0, model['CollisionModelChecksum'])
    struct.pack_into('>I', out, 16, model['Flags'] & 1)
    block(out, 20, model['Materials'], lambda r: struct.pack('>I', sid(r['Name'])))
    block(out, 32, model['Regions'], region)
    block(out, 44, model['PathfindingSpheres'], lambda r: struct.pack('>hH4f',
          r['Node'], r['Flags'], *point(r['Center']), r['Radius']))
    block(out, 56, model['Nodes'], lambda r: struct.pack('>IHhhh', sid(r['Name']),
          r['Flags'], r['ParentNode'], r['NextSiblingNode'], r['FirstChildNode']))
    return bytes(out)
