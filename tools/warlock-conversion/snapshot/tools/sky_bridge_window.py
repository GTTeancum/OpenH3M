"""Scoped twelve-entry native sbr_window_01 template; preserves source animation routes."""
import hashlib,json,re,struct
from pathlib import Path
from lightmap_register_reservations import require_safe_material_routes, require_safe_shared_float_uploads


def bind_window_template(materials, template, directory):
    directory=Path(directory).resolve()
    if not directory.is_relative_to(Path(__file__).resolve().parents[4]):
        raise ValueError('Window shader inputs must remain inside repository')
    plan=json.loads((directory/'route-plan.json').read_text())
    compiled={x['entry']:x for x in json.loads((directory/'compilation.json').read_text())['programs'] if x['stage']=='ps'}
    audit=json.loads((directory/'native-interface-audit.json').read_text())
    if plan['unresolved'] or len(audit)!=12 or any(not x['inputs_match'] or any(not r['equal'] for r in x['fixed_register_checks']) for x in audit):
        raise ValueError('Window shader interfaces differ from native donor')
    require_safe_material_routes(plan)
    require_safe_shared_float_uploads(plan)
    expected={1,3,4,5,6,7,8,9,12,13,14,17}
    if {x['entry'] for x in audit} != expected or {x['entry'] for x in plan['programs']} != expected:
        raise ValueError('Window native entry set changed')
    source=materials.source
    if source.name(12142) != r'levels\multi\s3d_sky_bridgenew\shaders\sbr_window_01':
        raise ValueError('Window source identity changed')
    sp,=source.block(source.tags[12142]['offset']+40,140)
    st=source.tags[source.u(sp+12)&65535]['offset']
    original={str(u):[materials.source_strings.text(source.u(x)) for x in source.block(st+off,4)]
              for u,off in ((0,108),(4,72),(5,84),(6,96))}
    if source.u(sp+92) or source.u(sp+40):
        raise ValueError('Window animation/integer data needs new audit')
    original['4'].append('use_material_texture')
    if original != plan['names']:
        raise ValueError('Window source parameter names changed')
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
        raise ValueError('Compiled window shader donor shape changed')
    profile=json.loads((directory/'profile.json').read_text())
    if plan['names']!=profile['names']:raise ValueError('Window parameter plan changed')
    # Vertex routes are absent for the default-albedo donor; the replacement
    # parameter lists therefore cannot change a vertex material binding.
    if any(p['usages'][u] for p in plan['programs'] for u in (1,2,3)):
        raise ValueError('Window donor has material vertex routes')
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
            raise ValueError('Compiled window shader bytecode does not match audited manifest')
        magic, debug_size, code_size = struct.unpack_from('>III', raw)
        if magic >> 16 != 0x102a or debug_size < 28 or code_size == 0 or debug_size + code_size != len(raw):
            raise ValueError('Compiled window shader debug/microcode bounds invalid')
        assembly = (directory / (name + '-ps.asm')).read_text()
        registers = [dict(name=n, set={'b':0,'i':1,'c':2,'s':3}[kind], register=int(reg), count=int(count))
            for n,kind,reg,count in re.findall(r'^//\s+(\w+)\s+([cbis])(\d+)\s+(\d+)\s*$',assembly,re.M)]
        if registers != program['registers']:
            raise ValueError('Compiled window shader reflection differs from route plan')
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
            raise ValueError('Compiled window shader needs one pass per entry')
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
                raise ValueError('Compiled window shader routing exceeds H3 limits')
            struct.pack_into('>H', p, usage * 2, start | count << 10)
            routes.extend(payload)
    for offset,usage in ((72,'4'),(84,'5'),(96,'6'),(108,'0')):
        names=profile['names'][usage]
        payload=b''.join(struct.pack('>I',materials.target_strings.id_for_text(n)) for n in names)
        struct.pack_into('>III',root,offset,len(names),b.alloc(payload) if payload else 0,0)
    struct.pack_into('>III',root,48,len(passes),b.alloc(b''.join(passes)),0)
    struct.pack_into('>III',root,60,len(routes)//4,b.alloc(routes),0)
    template_datum, _ = registry.newtag('rmt2',root)
    print('Sky Bridge window: bound twelve native programs',flush=True)
    return template_datum,evidence


def bind_window(materials, post, donor_names, directory):
    post=bytearray(post)
    template,evidence=bind_window_template(materials,struct.unpack_from('>I',post,12)[0],directory)
    profile=json.loads((Path(directory)/'profile.json').read_text())
    names=(profile['names']['0'],profile['names']['4'])
    for offset,stride,old,new in ((16,24,donor_names[0],names[0]),(28,16,donor_names[1],names[1])):
        count,pointer=struct.unpack_from('>II',post,offset)
        if count != len(old): raise ValueError('Window donor parameter count changed')
        rows=[bytes(materials.builder.read(pointer+i*stride,stride)) for i in range(count)]
        payload=bytearray()
        for name in new:
            if name in old:
                row=bytearray(rows[old.index(name)])
            elif stride==16:
                row=bytearray(16)  # Source constant loop must replace every value.
            else:
                raise ValueError('Window donor lacks required texture '+name)
            if stride==24:
                struct.pack_into('>b',row,21,names[1].index(name))
            payload.extend(row)
        struct.pack_into('>III',post,offset,len(new),materials.builder.alloc(payload),0)
    struct.pack_into('>I',post,12,template)
    struct.pack_into('>i',post,104,3)  # Native alpha blend.
    if profile['names']['5']: raise ValueError('Window integer parameters unsupported')
    post[40:52]=bytes(12)
    struct.pack_into('>I',post,52,materials.source.u(materials.source.block(materials.source.tags[12142]['offset']+40,140)[0]+52))
    count,pointer=struct.unpack_from('>II',post,28)
    payload=bytearray(materials.builder.read(pointer,count*16))
    enabled=bool(struct.unpack_from('>I',post,52)[0] & (1 << profile['names']['6'].index('use_material_texture')))
    struct.pack_into('>4f',payload,names[1].index('use_material_texture')*16,*([float(enabled)]*4))
    struct.pack_into('>III',post,28,count,materials.builder.alloc(payload),0)
    return post,names,evidence
