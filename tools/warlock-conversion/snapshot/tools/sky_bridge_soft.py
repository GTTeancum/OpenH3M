"""Bind Sky Bridge additive soft-fade programs and depth-carrying native vertices."""
import hashlib,json,re,struct
from pathlib import Path
from lightmap_register_reservations import require_safe_material_routes, require_safe_shared_float_uploads


def bind_soft_template(materials, template, directory):
    directory=Path(directory).resolve()
    if not directory.is_relative_to(Path(__file__).resolve().parents[4]):
        raise ValueError('Soft shader inputs must remain inside repository')
    plan=json.loads((directory/'route-plan.json').read_text())
    compiled={x['entry']:x for x in json.loads((directory/'compilation.json').read_text())['programs'] if x['stage']=='ps'}
    audit=json.loads((directory/'native-interface-audit.json').read_text())
    if plan['unresolved'] or len(audit)!=10 or any(not x['soft_depth_extension_matches'] or any(not r['equal'] for r in x['fixed_register_checks']) for x in audit):
        raise ValueError('Soft shader interfaces differ from native donor')
    require_safe_material_routes(plan)
    require_safe_shared_float_uploads(plan)
    b,registry=materials.builder,materials.registry
    def address(datum):
        return struct.unpack_from('>I', registry.tags, (datum & 65535) * 8 + 4)[0]

    def rows(root, offset, stride):
        count, pointer = struct.unpack_from('>II', root, offset)
        return [bytes(b.read(pointer + j * stride, stride)) for j in range(count)]

    root = bytearray(b.read(address(template), 132))
    pixel = bytearray(b.read(address(struct.unpack_from('>I', root, 28)[0]), 32))
    programs = rows(pixel, 20, 80)
    if len(programs) != len(plan['programs']) or struct.unpack_from('>I', root, 120)[0]:
        raise ValueError('Compiled soft shader donor shape changed')
    textures=[materials.target_strings.text(struct.unpack('>I',x)[0]) for x in rows(root,108,4)]
    constants=[materials.target_strings.text(struct.unpack('>I',x)[0]) for x in rows(root,72,4)]
    added_constants=['overlay_map','overlay_tint','overlay_intensity','soft_fresnel_power','soft_z_range']
    added_textures=['overlay_map']
    added_booleans=['use_soft_fresnel','use_soft_z']
    if textures + added_textures != plan['names']['0'] or constants + added_constants != plan['names']['4']:
        raise ValueError('Compiled soft shader donor parameter names changed')
    for offset,expected in ((108,textures),(72,constants)):
        actual=[materials.target_strings.text(struct.unpack('>I',x)[0]) for x in rows(root,offset,4)]
        if actual != expected:
            raise ValueError('Reused native template parameter order differs from donor')
    pixel_entries=rows(pixel,4,2)
    entries = rows(root, 36, 2)
    passes = [bytearray(x) for x in rows(root, 48, 28)]
    old_routes = rows(root, 60, 4)
    new_usages = {}
    evidence = []
    for program in plan['programs']:
        entry, name, index = program['entry'], program['name'], program['shader']
        if tuple(pixel_entries[entry]) != (index,1):
            raise ValueError('Reused native pixel entry mapping differs from donor')
        raw = (directory / (name + '-ps.bin')).read_bytes()
        if not compiled[entry]['success'] or hashlib.sha256(raw).hexdigest() != compiled[entry]['sha256']:
            raise ValueError('Compiled soft shader bytecode does not match audited manifest')
        magic, debug_size, code_size = struct.unpack_from('>III', raw)
        if magic >> 16 != 0x102a or debug_size < 28 or code_size == 0 or debug_size + code_size != len(raw):
            raise ValueError('Compiled soft shader debug/microcode bounds invalid')
        assembly = (directory / (name + '-ps.asm')).read_text()
        registers = [dict(name=n, set={'b':0,'i':1,'c':2,'s':3}[kind], register=int(reg), count=int(count))
            for n,kind,reg,count in re.findall(r'^//\s+(\w+)\s+([cbis])(\d+)\s+(\d+)\s*$',assembly,re.M)]
        if registers != program['registers']:
            raise ValueError('Compiled soft shader reflection differs from route plan')
        # H3 also binds these shared textures outside material-route updates.
        # Compiler-selected slots can therefore read stale or vertex-fetch data
        # even when every named material route has been remapped correctly.
        fixed_samplers = {'albedo_texture': 10, 'normal_texture': 11,
                          'lightprobe_texture_array': 12,
                          'dominant_light_intensity_map': 13,
                          'scene_ldr_texture': 10, 'depth_buffer': 11}
        for register in registers:
            expected = fixed_samplers.get(register['name'].lower())
            if expected is not None and (register['set'], register['register'], register['count']) != (3, expected, 1):
                raise ValueError('Compiled shader changes an H3 fixed sampler: ' + register['name'])
        info = bytearray(40)
        struct.pack_into('>I', info, 16, b.alloc(raw[debug_size:]))
        info.extend(raw[:debug_size])
        row = bytearray(programs[index])
        row[:40] = bytes(40)
        reflection = b''.join(struct.pack('>IHBB', materials.target_strings.id_for_text(v['name'].lower()),
            v['register'], v['count'], v['set']) for v in registers)
        struct.pack_into('>III', row, 40, len(registers), b.alloc(reflection), 0)
        row[56:68] = bytes(12)
        gprs = int(re.search(r'PsMaxReg=(\d+)', assembly).group(1)) + 1
        struct.pack_into('>II', row, 72, gprs, b.alloc(info))
        programs[index] = bytes(row)
        packed = struct.unpack('>H', entries[entry])[0]
        if packed >> 10 != 1:
            raise ValueError('Compiled soft shader needs one pass per entry')
        new_usages[packed & 1023] = program['usages']
        evidence.append(dict(entry=entry, name=name, sha256=compiled[entry]['sha256'], gprs=gprs))
    struct.pack_into('>III', pixel, 20, len(programs), b.alloc(b''.join(programs)), 0)
    pixel_datum, _ = registry.newtag('pixl', pixel)
    struct.pack_into('>I', root, 28, pixel_datum)
    routes = bytearray()
    for index, p in enumerate(passes):
        for usage in range(12):
            packed = struct.unpack_from('>H', p, usage * 2)[0]
            if index in new_usages:
                payload = b''.join(struct.pack('>HBB', *x) for x in new_usages[index][usage])
            else:
                payload = b''.join(old_routes[packed & 1023:(packed & 1023) + (packed >> 10)])
            start, count = len(routes)//4, len(payload)//4
            if start > 1023 or count > 63:
                raise ValueError('Compiled soft shader routing exceeds H3 limits')
            struct.pack_into('>H', p, usage * 2, start | count << 10)
            routes.extend(payload)
    real_names = b''.join(rows(root,72,4)) + b''.join(
        struct.pack('>I', materials.target_strings.id_for_text(n)) for n in added_constants)
    texture_names = b''.join(rows(root,108,4)) + b''.join(
        struct.pack('>I', materials.target_strings.id_for_text(n)) for n in added_textures)
    boolean_rows = rows(root,96,4)
    boolean_names = [materials.target_strings.text(struct.unpack('>I', x)[0]) for x in boolean_rows]
    if boolean_names + added_booleans != plan['names']['6']:
        raise ValueError('Compiled material donor boolean names changed')
    if added_booleans:
        payload = b''.join(boolean_rows) + b''.join(struct.pack('>I', materials.target_strings.id_for_text(n)) for n in added_booleans)
        struct.pack_into('>III', root, 96, len(boolean_names)+len(added_booleans), b.alloc(payload), 0)
    for offset,count,payload in ((48,len(passes),b''.join(passes)),(60,len(routes)//4,routes),
                                 (72,len(constants)+len(added_constants),real_names),
                                 (108,len(textures)+len(added_textures),texture_names)):
        struct.pack_into('>III',root,offset,count,b.alloc(payload),0)
    template_datum, _ = registry.newtag('rmt2',root)
    print('Sky Bridge soft fade: bound ten native programs',flush=True)
    return template_datum,evidence


def bind_soft_vertices(materials, definition, directory):
    directory=Path(directory)
    plan=json.loads((directory/'vertex-plan.json').read_text())
    compiled={(r['entry'],r['stage']):r for r in json.loads((directory/'compilation.json').read_text())['programs']}
    b,registry=materials.builder,materials.registry
    def address(datum):
        return struct.unpack_from('>I',registry.tags,(datum&65535)*8+4)[0]
    def rows(root,offset,stride):
        count,pointer=struct.unpack_from('>II',root,offset)
        return [bytes(b.read(pointer+j*stride,stride)) for j in range(count)]
    root=bytearray(b.read(address(definition[1]),92))
    vertex=bytearray(b.read(address(struct.unpack_from('>I',root,80)[0]),28))
    programs=rows(vertex,16,80)
    types=rows(vertex,0,12)
    for item in plan:
        if item['differences']:raise ValueError('Soft vertex constant binding changed')
        entry=rows(types[item['type']],0,16)[item['entry']]
        if struct.unpack_from('>I',entry,0)[0] or struct.unpack_from('>I',entry,12)[0]!=item['shader']:
            raise ValueError('Soft vertex donor entry changed')
        name=item['name']+'-vs-'+item['kind']
        raw=(directory/(name+'.bin')).read_bytes()
        expected=compiled[item['entry'],'vs-'+item['kind']]
        if not expected['success'] or hashlib.sha256(raw).hexdigest()!=expected['sha256']:
            raise ValueError('Soft vertex compiled payload changed')
        magic,debug_size,code_size=struct.unpack_from('>III',raw)
        if magic>>16!=0x102a or debug_size+code_size!=len(raw):
            raise ValueError('Invalid soft vertex payload')
        assembly=(directory/(name+'.asm')).read_text()
        registers=[dict(name=n.lower(),set={'b':0,'i':1,'c':2,'s':3}[k],register=int(i),count=int(count)) for n,k,i,count in re.findall(r'^//\s+(\w+)\s+([cbis])(\d+)\s+(\d+)\s*$',assembly,re.M)]
        if registers!=item['registers']:raise ValueError('Soft vertex reflection changed')
        row=bytearray(programs[item['shader']])
        original=[dict(name=materials.target_strings.text(struct.unpack_from('>I',r)[0]),register=struct.unpack_from('>H',r,4)[0],count=r[6],set=r[7]) for r in rows(row,40,8)]
        if any(r not in original for r in registers):raise ValueError('Soft vertex requires an unbound constant')
        info=bytearray(0x368);struct.pack_into('>I',info,16,b.alloc(raw[debug_size:]));info.extend(raw[:debug_size])
        row[:40]=bytes(40)
        reflection=b''.join(struct.pack('>IHBB',materials.target_strings.id_for_text(v['name']),v['register'],v['count'],v['set']) for v in registers)
        struct.pack_into('>III',row,40,len(registers),b.alloc(reflection),0);row[56:68]=bytes(12)
        gprs=int(re.search(r'VsMaxReg=(\d+)',assembly).group(1))+1
        struct.pack_into('>II',row,72,gprs,b.alloc(info));programs[item['shader']]=row
    struct.pack_into('>III',vertex,16,len(programs),b.alloc(b''.join(programs)),0)
    datum,_=registry.newtag('glvs',vertex);struct.pack_into('>I',root,80,datum)
    datum,_=registry.newtag('rmdf',root)
    return ('rmdf',datum)
