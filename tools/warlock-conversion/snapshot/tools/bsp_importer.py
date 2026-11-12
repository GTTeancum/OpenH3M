"""Assemble a new retail BSP tag and its resources from MCC source data."""
from source_schema import load_schema
import xml.etree.ElementTree as ET
import struct
from tag_metadata import MetadataConverter
from resource_reader import Resource
from render_resource import convert_render_resource
from bsp_source import convert_bsp_geometry
from bsp_collision_resource import convert_bsp_collision


def import_bsp(importer, terrain, water, bsp_index=0):
    if importer.failed:
        raise ValueError('Cannot import BSP into an incomplete dependency graph')
    try:
        return _import_bsp(importer, terrain, water, bsp_index)
    except Exception:
        importer.failed = True
        raise


def _import_bsp(i, terrain, water, bsp_index):
    s, b = i.source, i.builder
    scenario_schema = load_schema(i.source, 'scnr', i.reference)
    field = next(f for f in scenario_schema if f.get('name') == 'Structure BSPs')
    scenarios = [t['offset'] for t in s.tags.values() if t['group'] == 'scnr']
    if len(scenarios) != 1:
        raise ValueError('Expected one source scenario')
    rows = s.block(scenarios[0] + int(field.get('offset'), 0), int(field.get('elementSize'), 0))
    if not 0 <= bsp_index < len(rows):
        raise ValueError('BSP index outside scenario bindings')
    datum = s.u(rows[bsp_index] + 12)
    source = s.tags.get(datum & 65535)
    if source is None or source['salt'] != datum >> 16 or source['group'] != 'sbsp':
        raise ValueError('Invalid source BSP binding')
    name = s.name(datum & 65535)
    ss = load_schema(i.source, 'sbsp', i.reference)
    ds = ET.parse(i.reference / 'plugins/sbsp.xml').getroot()
    size = int(ds.get('baseSize'), 0)
    owner, address = i.registry.newtag('sbsp', bytes(size))
    # Reserve before recursion; cluster/instance physics refer to their owner.
    i.resolved['sbsp', name] = ('sbsp', owner)
    resources = []

    def reference(value):
        tag = s.tags.get(value & 65535)
        if tag is None or tag['salt'] != value >> 16:
            raise ValueError('Invalid BSP dependency salt')
        group = tag['group']
        if group in ('rmtr', 'rmhg'):
            return terrain.shader(value)
        if group == 'rmw ':
            return water.shader(value)
        return i.import_tag(value)

    def resource(path, value):
        provenance = None
        if path.endswith('/[zone] Asset Datum 1'):
            payload = convert_render_resource(Resource(s, value))
            kind = 'render_geometry_api_resource_definition'
        elif path.endswith('/[zone] Asset Datum 2'):
            payload, provenance = convert_bsp_geometry(s, bsp_index)
            kind = 'render_geometry_api_resource_definition'
        elif path.endswith('/[zone] Tag Resources Asset Datum'):
            partition = (getattr(i, 'reference_rebuild', None) or getattr(i, 'gulch_partition', None)) if bsp_index == 0 else None
            payload = convert_bsp_collision(Resource(s, value), partition[0] if partition else None)
            kind = 'structure_bsp_tag_resources'
        else:
            raise ValueError(f'Unsupported BSP resource field: {path}')
        target = i.registry.add_resource(owner, kind, payload)
        resources.append({'field': path.rsplit('/', 1)[-1], 'datum': hex(target),
                          'raw_bytes': len(payload['raw']), 'source_binding': provenance})
        return target

    collision_materials = []
    rendered = {s.u(row+12) for row in s.block(source['offset']+0xd0, 36)}

    def collision_material(at, source_schema, target_schema, path):
        if source_schema.get('name') != 'Collision Materials':
            return None
        shader = s.u(at+12)
        if shader == 0xffffffff or shader in rendered:
            return None
        # Compiled collision retains its physical response separately from the
        # optional old editor shader. Stock warehouse has an invalid render ref;
        # structure_collision_material explicitly permits INVALID_TAG. Never
        # clear a shader used by this BSP's render geometry.
        fields = list(s.unpack('4h', at+16))
        if fields[1] != -1:
            return None  # Conveyor shaders require their own runtime audit.
        tag = s.tags.get(shader & 65535)
        if tag is None or tag['salt'] != shader >> 16:
            raise ValueError('Invalid collision-only shader datum')
        globals_source = next(t['offset'] for t in s.tags.values() if t['group'] == 'matg')
        globals_target = next(t['offset'] for t in i.registry.cache.tags.values() if t['group'] == 'matg')
        source_material_field = next(f for f in load_schema(s, 'matg', i.reference)
                                     if f.get('name') == 'Materials')
        source_materials = s.block(globals_source + int(source_material_field.get('offset'), 0),
                                   int(source_material_field.get('elementSize'), 0))
        target_materials = i.registry.cache.block(globals_target+0x17c, 0x170)
        if not 0 <= fields[0] < len(source_materials):
            raise ValueError('Collision-only shader has invalid physical material')
        material = i.source_strings.text(s.u(source_materials[fields[0]]))
        matches = [j for j, row in enumerate(target_materials)
                   if i.target_strings.text(i.registry.cache.u(row)) == material]
        if len(matches) != 1 or fields[3] != 0:
            raise ValueError('Collision-only shader lacks an exact native physical material')
        fields[0] = matches[0]
        collision_materials.append({'shader': s.name(shader & 65535),
                                    'physical_material': material, 'native_index': fields[0],
                                    'reason': 'collision-only optional render reference'})
        return struct.pack('>4I4h', 0xffffffff, 0, 0, 0xffffffff, *fields)

    converter = MetadataConverter(s, b, i.source_strings, i.target_strings,
                                  reference, resource_reference=resource,
                                  special_block=collision_material)
    converter.source_bsp = source
    converter.gulch_partition = (getattr(i, 'reference_rebuild', None) or getattr(i, 'gulch_partition', None)) if bsp_index == 0 else None
    payload = converter.convert(source['offset'], ss, ds, 'sbsp:' + name)
    material_bindings = []
    if getattr(i.materials, 'prisoner_materials', False):
        # The CE-authored metal shaders have no physical material assignment.
        # Give their collision surfaces the existing Halo 3 metal response.
        globals_root = next(t['offset'] for t in i.registry.cache.tags.values() if t['group']=='matg')
        materials = i.registry.cache.block(globals_root+0x17c,0x170)
        metal = next(n for n,row in enumerate(materials)
                     if i.target_strings.text(i.registry.cache.u(row))=='hard_metal_thick')
        source_rows = s.block(source['offset']+0x28,24)
        count, pointer = struct.unpack_from('>II',payload,0x24)
        if count != len(source_rows): raise ValueError('Collision material count changed')
        for n,row in enumerate(source_rows):
            shader = s.u(row+12)
            shader_name = s.name(shader & 65535) or ''
            if (shader_name.startswith('custom\\levels\\multiplayer\\prisoner\\shaders\\metal_')
                    and s.unpack('h',row+16)[0]==0
                    and not i.source_strings.text(s.u(s.tags[shader&65535]['offset']+64))):
                b.put(pointer+n*24+16,'h',metal)
                material_bindings.append({'shader':shader_name,'material':'hard_metal_thick','index':metal})
    if len(payload) != size:
        raise ValueError('BSP root size mismatch')
    b.meta[address - b.base:address - b.base + size] = payload
    report = {'source': name, 'group': 'sbsp', 'datum': hex(owner),
              'resources': resources, 'source_geometry': True,
              'native_collision_materials': material_bindings,
              'collision_only_materials': collision_materials}
    i.added.append(report)
    return ('sbsp', owner), address, report
