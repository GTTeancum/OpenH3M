"""Import missing fixed Reach Forge architecture into an existing H3 map.

Requires the read-only bridge exports. Stock objects and already converted
pieces resolve through the existing importer; no second game installation.
"""
import json
import struct
import xml.etree.ElementTree as ET
from pathlib import Path
from reach_collision import serialize_collision
from reach_physics import serialize_physics
from reach_metadata import link_metadata
from reach_resource import ReachResource, convert_render_resource
from reach_materials import ReachMaterials
from string_ids import StringTable
from reach_forge_lights import serialize_light


class ReachForgeAssets:
    def __init__(self, source, importer, bridge_directory, shared_paths=None):
        self.source, self.importer = source, importer
        self.builder, self.registry = importer.builder, importer.registry
        self.strings = StringTable(source)
        directory = Path(bridge_directory)
        self.models = {r['index']: r for r in json.loads((directory/'converted-render.json').read_text())}
        self.collisions = {r['index']: r for r in json.loads((directory/'converted-collision.json').read_text())}
        self.source_physics = ET.parse(directory/'reference/reach-phmo.xml').getroot()
        self.target_physics = ET.parse(importer.reference/'plugins/phmo.xml').getroot()
        self.materials = ReachMaterials(source, importer, shared_paths)
        self.shared_paths = shared_paths
        self.done, self.report, self.pages = {}, [], {}
        c = self.registry.cache
        matg = next(t['offset'] for t in c.tags.values() if t['group']=='matg')
        self.global_materials = {importer.target_strings.text(c.u(row)): j
                                 for j,row in enumerate(c.block(matg+0x17c,0x170))}
        self.mcc_names = {(t['group'], importer.source.name(i)): t['salt'] << 16 | i
                          for i,t in importer.source.tags.items()}
        self.bind_existing_materials()

    def bind_existing_materials(self):
        # Cache names were stripped from imported shaders. Recover their binding
        # through the unchanged material slots of the already accepted pieces.
        i,c,s = self.importer,self.registry.cache,self.importer.source
        found = {}
        for (group,name),(_,datum) in list(i.resolved.items()):
            if group != 'mode' or not name or not name.startswith('objects\\levels\\forge\\ff_'):
                continue
            source_id = self.mcc_names.get((group,name))
            if source_id is None:
                continue
            source_rows = s.block(s.tags[source_id&65535]['offset']+72,36)
            target_rows = c.block(c.tags[datum&65535]['offset']+72,36)
            if len(source_rows) != len(target_rows):
                raise ValueError('Accepted Forge piece material slots changed')
            for src,dst in zip(source_rows,target_rows):
                source_shader,target_shader = s.u(src+12),c.u(dst+12)
                if source_shader == 0xffffffff:
                    continue
                source_tag,target_tag = s.tags[source_shader&65535],c.tags[target_shader&65535]
                key = source_tag['group'],s.name(source_shader&65535)
                value = target_tag['group'],target_shader
                if key in found and found[key] != value:
                    raise ValueError(f'Conflicting accepted shader bindings: {key}')
                found[key] = value
        i.resolved.update(found)

    def translate_string(self, value):
        return self.strings.translate(value, self.importer.target_strings)

    def material_index(self, value):
        name = self.strings.text(value)
        if name not in self.global_materials:
            raise ValueError(f'Reach physics global material has no H3 match: {name}')
        return self.global_materials[name]

    def import_tag(self, datum):
        s,b,r,i = self.source,self.builder,self.registry,self.importer
        tag = s.tags[datum & 65535]
        if tag['salt'] != datum >> 16:
            raise ValueError('Source Reach tag salt mismatch')
        key = tag['group'], tag['name']
        if key in self.done:
            return self.done[key]
        if key in i.resolved:
            return i.resolved[key]
        if key in self.mcc_names:
            return i.import_tag(self.mcc_names[key])
        group,name = key
        # Reach ships this fixed Forge piece as scenery. In H3 it uses the
        # same editable fixed-crate wrapper as the other Forerunner pieces.
        if group == 'scen' and name == r'objects\levels\forge\ff_dish_antenna\ff_dish_antenna':
            group = 'bloc'
        if group in ('rmsh','rmgl'):
            return self.materials.shader(datum)
        if group in ('ligh','gldf') and name.startswith('objects\\levels\\forge\\ff_'):
            payload = serialize_light(s,tag,b,self.translate_string)
            owner,_ = r.newtag('ligh',payload)
            self.done[key] = ('ligh',owner)
            self.report.append(dict(group='ligh',source=name,datum=hex(owner),
                                    approximation='native spherical falloff' if group=='gldf' else None))
            return self.done[key]
        if group not in ('mode','hlmt','coll','phmo','bloc') or not name.startswith('objects\\levels\\forge\\ff_'):
            raise ValueError(f'Unexpected Reach architecture dependency: {key}')
        size = {'mode':0x1cc,'hlmt':0x188,'coll':68,'phmo':int(self.target_physics.get('baseSize'),0),'bloc':0x10c}[group]
        owner,placeholder = r.newtag(group,bytes(size))
        self.done[key] = (group,owner)
        if group in ('mode','hlmt'):
            record = self.models[datum & 65535]
            address = link_metadata(record,b,self.translate_string,self.import_tag)
            if group == 'mode':
                resource = ReachResource(s,record['resource'],self.shared_paths,self.pages)
                rid = r.add_resource(owner,'render_geometry_api_resource_definition',convert_render_resource(resource))
                b.put(address+0xe0,'II',rid,0)
            else:
                count,pointer = struct.unpack('>II',b.read(address+0x7c,8))
                for j in range(count):
                    row = pointer+j*20
                    sid = struct.unpack('>I',b.read(row+12,4))[0]
                    if not sid:
                        sid = struct.unpack('>I',b.read(row,4))[0]
                    name = i.target_strings.text(sid)
                    if name not in self.global_materials:
                        raise ValueError(f'Unknown model global material {name}')
                    index = self.global_materials[name]
                    # Collision/damager indices address model-local material
                    # lists; only the global table index changes between games.
                    b.put(row+12,'I',sid)
                    b.put(row+16,'h',index)
            struct.pack_into('>I',r.tags,(owner&65535)*8+4,address)
        else:
            if group == 'coll':
                payload = serialize_collision(self.collisions[datum&65535]['definition'],b,self.translate_string)
            elif group == 'phmo':
                payload = serialize_physics(s,tag['offset'],self.source_physics,self.target_physics,b,
                                            self.translate_string,self.material_index)
            else:
                payload = self.crate(tag)
            if len(payload) != size:
                raise ValueError(f'Native {group} root size mismatch: {len(payload)} != {size}')
            b.meta[placeholder-b.base:placeholder-b.base+size] = payload
        self.report.append(dict(group=group,source=tag['name'],datum=hex(owner)))
        return group,owner

    def crate(self, tag):
        s,b,r,i = self.source,self.builder,self.registry,self.importer
        at = tag['offset']
        expected_type = 6 if tag['group']=='scen' else 10
        if s.unpack('HHII',at) != (expected_type,0,0,0) or s.u(at+0xec):
            raise ValueError('Reach Forge crate has unreviewed flags/functions')
        prototype = i.resolved['bloc',r'objects\levels\forge\ff_bank_1x1\ff_bank_1x1'][1]
        address = struct.unpack_from('>I',r.tags,(prototype&65535)*8+4)[0]
        root = bytearray(b.read(address,0x10c))
        struct.pack_into('>4f',root,4,*s.unpack('4f',at+12))
        accelerations = s.unpack('3f',at+28)
        if len(set(accelerations)) != 1:
            raise ValueError('Anisotropic Reach acceleration needs explicit conversion')
        struct.pack_into('>f',root,20,accelerations[0])
        struct.pack_into('>HBB',root,24,*s.unpack('HBB',at+40))
        struct.pack_into('>4f',root,32,*s.unpack('4f',at+44))
        struct.pack_into('>I',root,48,self.translate_string(s.u(at+96)))
        group,model = self.import_tag(s.u(at+112))
        if group != 'hlmt':
            raise ValueError('Forge crate has no model')
        struct.pack_into('>4sIII',root,52,b'hlmt',0,0,model)
        attachments = bytearray()
        for row in s.block(at+0x104,32):
            ref = s.u(row+12)
            if ref == 0xffffffff:
                continue
            color,flags,pad = s.unpack('BBH',row+20)
            if flags or pad or color>4:
                raise ValueError('Unsupported architectural attachment behavior')
            group,ref = self.import_tag(ref)
            attachments.extend(struct.pack('>4sIIIIHHII',group.encode(),0,0,ref,
                self.translate_string(s.u(row+16)),color,0,
                self.translate_string(s.u(row+24)),self.translate_string(s.u(row+28))))
        struct.pack_into('>III',root,0xbc,len(attachments)//32,
                         b.alloc(attachments) if attachments else 0,0)
        return root

    def close(self):
        self.pages.clear()
        self.materials.bitmaps.clear()
