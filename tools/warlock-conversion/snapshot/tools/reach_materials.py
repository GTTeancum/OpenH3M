"""Named Reach scenery parameters, with explicit native shader plans.

No numeric Reach option is assumed to mean the same thing in Halo 3. Category
and option names are read from each cache's render-method definition first.
Unsupported combinations remain explicit, rather than inheriting a random
prototype's lighting. This module prepares plans; it does not publish materials.
"""
from string_ids import StringTable


def categories(cache, strings, root):
    result = {}
    for row in cache.block(root + 16, 24):
        name = strings.text(cache.u(row))
        options = [strings.text(cache.u(x)) for x in cache.block(row + 4, 28)]
        if name in result or len(options) != len(set(options)):
            raise ValueError('Ambiguous render-method category/options')
        result[name] = options
    return result


def discrete_parameters(cache, strings, root, definition, selected):
    """Read selected Reach rmop defaults and explicit rm parameter overrides.

    TagTool RenderMethodOption.ParameterBlock is 0x60 for Reach; integer/bool
    type and default are +8/+36. RenderMethodParameterBlock is 0x3c with
    type/value +4/+28. Only declarations selected by this material participate.
    Compiled constants remain authoritative when a parameter survived compiling.
    """
    datums=[cache.u(definition+12)]
    categories=cache.block(definition+16,24)
    if len(categories)!=len(selected):raise ValueError('Shader category count changed')
    for category,index in zip(categories,selected):
        options=cache.block(category+4,28)
        datums.append(cache.u(options[index]+16))
    defaults={};overrides={}
    for datum in datums:
        if datum==0xffffffff:continue
        tag=cache.tags.get(datum&65535)
        if tag is None or tag['salt']!=datum>>16 or tag['group']!='rmop':
            raise ValueError('Invalid selected Reach shader option')
        for at in cache.block(tag['offset'],96):
            kind=cache.u(at+8)
            if kind not in (3,4):continue
            name=strings.text(cache.u(at));value=cache.u(at+36)
            declaration=dict(type=kind,value=value)
            if name in defaults and defaults[name]!=declaration:
                raise ValueError(f'Conflicting selected shader defaults: {name}')
            defaults[name]=declaration
    for at in cache.block(root+44,60):
        kind=cache.u(at+4)
        if kind not in (3,4):continue
        name=strings.text(cache.u(at))
        if name in overrides:raise ValueError(f'Duplicate shader override: {name}')
        overrides[name]=dict(type=kind,value=cache.u(at+28))
    return defaults,overrides


def read_material(cache, datum, expected_group='rmsh'):
    strings = StringTable(cache)
    tag = cache.tags[datum & 65535]
    # ReachMCC render-method subclasses share these base offsets. ShaderWater
    # adds no fields (TagTool ShaderWater.cs, pinned ce2dc6ac). Terrain's
    # additional root fields are not imported by this parameter reader.
    if expected_group not in ('rmsh','rmtr','rmhg','rmw ','rmfl','rmgl','rmcs') or tag['salt'] != datum >> 16 or tag['group'] != expected_group:
        raise ValueError('Expected salted Reach render-method shader')
    root = tag['offset']
    definition = cache.tags[cache.u(root + 12) & 65535]
    options = [cache.unpack('h', x)[0] for x in cache.block(root + 32, 2)]
    names = categories(cache, strings, definition['offset'])
    if len(options) != len(names):
        raise ValueError('Reach shader options differ from definition')
    selected = {}
    for (name, choices), index in zip(names.items(), options):
        if not 0 <= index < len(choices):
            raise ValueError('Reach shader option outside definition')
        selected[name] = choices[index]
    posts = cache.block(root + 56, 180)
    if len(posts) != 1:
        raise ValueError('Expected one Reach shader postprocess')
    post = posts[0]
    template = cache.tags[cache.u(post + 12) & 65535]
    if template['group'] != 'rmt2':
        raise ValueError('Reach shader has no template')
    texture_names = [strings.text(cache.u(x)) for x in cache.block(template['offset'] + 108, 4)]
    constant_names = [strings.text(cache.u(x)) for x in cache.block(template['offset'] + 72, 4)]
    textures = {}
    for name, row in zip(texture_names, cache.block(post + 16, 24), strict=True):
        reference = cache.u(row + 12)
        transform = cache.unpack('b', row + 21)[0]
        overlay = cache.unpack('H', row + 22)[0]
        if not -1 <= transform < len(constant_names):
            raise ValueError('Reach texture transform constant outside table')
        if (overlay & 1023)+(overlay >> 10)>cache.u(post+92):
            raise ValueError('Reach texture animation span outside function table')
        textures[name] = dict(datum=reference,
                              name=cache.name(reference & 65535) if reference != 0xffffffff else None,
                              bitmap_index=cache.unpack('h', row + 16)[0],
                              address_mode=cache.data[row + 18], filter_mode=cache.data[row + 19],
                              external_mode=cache.data[row + 20],
                              transform_constant=constant_names[transform] if transform>=0 else None,
                              transform_overlays=overlay)
    constants = {name: cache.unpack('4f', row) for name, row in
                 zip(constant_names, cache.block(post + 28, 16), strict=True)}
    integer_names = [strings.text(cache.u(x)) for x in cache.block(template['offset'] + 84, 4)]
    boolean_names = [strings.text(cache.u(x)) for x in cache.block(template['offset'] + 96, 4)]
    integers = {name: cache.u(row) for name, row in
                zip(integer_names, cache.block(post + 40, 4), strict=True)}
    bits = cache.u(post + 52)
    if len(boolean_names)>32 or bits >> len(boolean_names):
        raise ValueError('Reach shader has unnamed boolean constants')
    booleans = {name: bool(bits & (1 << j)) for j,name in enumerate(boolean_names)}
    defaults,overrides=discrete_parameters(cache,strings,root,definition['offset'],options)
    return dict(name=tag['name'], options=selected, textures=textures, constants=constants,
                discrete_defaults=defaults,discrete_overrides=overrides,
                integers=integers, booleans=booleans, post=post,
                animated=bool(cache.u(post + 80)), unused_functions=cache.u(post + 92) if not cache.u(post + 80) else 0,
                flags=cache.unpack('H', root + 88)[0],
                sort_layer=cache.data[root + 90], fog=cache.unpack('i', root + 92)[0])


def native_plan(material, native_categories, template_family='shader'):
    """Return exact semantic selections plus requirements still needing work."""
    selected, unresolved = [], []
    options = material['options']
    for name, choices in native_categories.items():
        choice = options.get(name)
        if name == 'misc' and choice == 'default':
            choice = 'first_person_never'
        if choice not in choices:
            unresolved.append(dict(category=name, choice=choice))
            selected.append(None)
        else:
            selected.append(choices.index(choice))
    for name, choice in options.items():
        if name in native_categories:
            continue
        if (name, choice) not in {('wetness', 'default'),
                                  ('alpha_blend_source', 'from_albedo_alpha_without_fresnel')}:
            unresolved.append(dict(category=name, choice=choice))
    if material['animated']:
        unresolved.append(dict(category='animation', choice='requires Reach routing conversion'))
    return dict(name=material['name'], options=selected, unresolved=unresolved,
                template=None if unresolved else 'shaders\\' + template_family + '_templates\\_' + '_'.join(map(str, selected)))


def native_sampler(source):
    """Translate Reach's packed filter byte; never inherit donor sampling.

    TagTool TextureConstant uses PackedSamplerFilterMode for Reach and the
    plain SamplerFilterMode enum for H3 retail. Address nibbles share an enum.
    TagTool ShaderConverter copies FilterModePacked.FilterMode to FilterMode;
    the separate anisotropy nibble has no H3 field and is not an enum value.
    """
    address, packed = source['address_mode'], source['filter_mode']
    if address & 15 > 5 or address >> 4 > 5:
        raise ValueError(f'Unsupported Reach sampler address: {address:#x}')
    if packed & 15 > 6:
        raise ValueError(f'Reach sampler requires explicit filter conversion: {packed:#x}')
    return address, packed & 15


def native_switches(material, names):
    """Bind discrete shader parameters by name, including Reach float layers."""
    def declared(name,kind):
        entry=material.get('discrete_overrides',{}).get(name)
        if entry is None:entry=material.get('discrete_defaults',{}).get(name)
        if entry is None and kind==4 and name=='order3_area_specular':
            # Reach VMF has no authored SH-order switch. Use H3's documented
            # default (order 2), matching the converted linear SH lightmaps.
            # This selects an approximation; it is not an equivalence claim.
            # 343Industries/forge-docs, 678af9cb, H3/Shaders/MaterialModel.md.
            return 0
        if entry is None or entry['type']!=kind:
            raise ValueError(f'No authored declaration for native shader parameter {name}')
        if kind==4 and entry['value'] not in (0,1):
            raise ValueError(f'Non-boolean shader declaration: {name}')
        return entry['value']
    integers = []
    for name in names['integer']:
        if name in material['integers']:
            value = material['integers'][name]
        elif name == 'layers_of_4' and name in material['constants']:
            values = material['constants'][name]
            value = values[0]
            if not 1 <= value <= 255 or value != int(value) or any(x != value for x in values):
                raise ValueError('Reach hologram layer count cannot be represented by H3 integer')
            value = int(value)
        else:
            value=declared(name,3)
        integers.append(value)
    if len(names['boolean'])>32:
        raise ValueError('Native shader boolean count exceeds bit field')
    bits = 0
    for j,name in enumerate(names['boolean']):
        value=material['booleans'][name] if name in material['booleans'] else declared(name,4)
        bits |= int(value) << j
    return integers, bits


class ReachMaterials:
    """Stage exact semantic native matches; reject unsupported material features.

The caller can inspect the plans before creating a map. Missing templates and
Reach-only specular modes deliberately stop staging instead of silently making
every new piece shiny or opaque.
    """
    reach_entry_points = True

    def __init__(self, source, importer, shared_paths=None, group='rmsh'):
        from reach_bitmap_source import ReachBitmapSource
        self.source, self.importer = source, importer
        self.builder, self.registry = importer.builder, importer.registry
        self.source_strings, self.target_strings = StringTable(source), importer.target_strings
        self.bitmaps = ReachBitmapSource(source, shared_paths)
        self.report, self.done = [], {}
        c = self.registry.cache
        self.group = group
        self.family = {'rmsh':'shader','rmtr':'terrain','rmhg':'halogram'}[group]
        self.native_definition = next((t['salt'] << 16 | i, t['offset']) for i,t in c.tags.items()
                                      if t['group'] == 'rmdf' and c.name(i) == 'shaders\\'+self.family)
        self.categories = categories(c, self.target_strings, self.native_definition[1])
        self.mcc_names = {(t['group'], importer.source.name(i)): t['salt'] << 16 | i
                          for i,t in importer.source.tags.items()}

    def parameters(self, cache, strings, post):
        return self.importer.materials.parameters(cache, strings, post)

    def bitmap(self, datum):
        from encode_bitmap import encode_bitmap_base
        name = self.source.name(datum & 65535)
        key = ('bitm', name)
        if key in self.importer.resolved:
            return self.importer.resolved[key][1]
        native_assets=getattr(self.importer,'native_assets',None)
        if native_assets is not None:
            native=native_assets.import_named(key)
            if native is not None:
                self.importer.resolved[key]=native
                return native[1]
        if key in self.mcc_names:
            return self.importer.import_tag(self.mcc_names[key])[1]
        if key not in self.done:
            try:
                info=self.bitmaps.info(datum&65535)[0]
                if info['kind']==2:
                    from encode_bitmap import encode_cubemap_base
                    record,control,raw=encode_cubemap_base(self.bitmaps,datum&65535,max_dimension=info['width'],preserve_mips=True)
                else:
                    record, control, raw = encode_bitmap_base(self.bitmaps, datum & 65535,
                                                             preserve_normal_mips=True, preserve_bc_mips=True)
                self.done[key] = self.importer.materials.bitmap_resource(record, control, raw)
            finally:
                self.bitmaps.clear()
        return self.done[key]

    def shader(self, datum):
        import struct
        from material_animation import convert_material_animation
        s, b, r = self.source, self.builder, self.registry
        tag = s.tags[datum & 65535]
        key = (self.group, tag['name'])
        # Reach glass has a dedicated class, but the already accepted workshop
        # conversion binds that same named Forge glass to a native rmsh.
        if key in self.importer.resolved:
            return self.importer.resolved[key]
        if key in self.mcc_names:
            return self.importer.import_tag(self.mcc_names[key])
        if key in self.done:
            return self.group, self.done[key]
        material = read_material(s, datum, self.group)
        tail = bytearray(28 if self.group=='rmtr' else 4)
        if self.group=='rmtr':
            target=self.registry.cache
            matg=next(t['offset'] for t in target.tags.values() if t['group']=='matg')
            globals_by_name={self.target_strings.text(target.u(p)):j for j,p in enumerate(target.block(matg+0x17c,0x170))}
            for j in range(4):
                name=self.source_strings.text(s.u(tag['offset']+100+j*4))
                if name and name not in globals_by_name:
                    raise ValueError(f'Reach terrain global material needs stock H3 mapping: {name}')
                struct.pack_into('>I',tail,j*4,self.target_strings.id_for_text(name) if name else 0)
                struct.pack_into('>h',tail,16+j*2,globals_by_name[name] if name else -1)
            # ShaderTerrain declares this as the same uint field in Reach/H3,
            # separate from the four GlobalMaterialIndices above.
            struct.pack_into('>I',tail,24,s.u(tag['offset']+124))
        elif self.group=='rmhg':
            name=self.source_strings.text(s.u(tag['offset']+100))
            struct.pack_into('>I',tail,0,self.target_strings.id_for_text(name) if name else 0)
        overrides = {}
        differences = []
        if material['options'].get('specular_mask') == 'specular_mask_mult_diffuse':
            from types import SimpleNamespace
            from reach_specular import bake_mask
            from encode_bitmap import encode_bitmap_base
            mask, transform = bake_mask(material, self.bitmaps)
            memory = SimpleNamespace(c=None, info=lambda _: [mask], pixels=lambda *_: mask['pixels'])
            overrides['specular_mask_texture'] = self.importer.materials.bitmap_resource(
                *encode_bitmap_base(memory, 0, preserve_bc_mips=True))
            material['constants']['specular_mask_texture'] = transform
            material['options']['specular_mask'] = 'specular_mask_from_texture'
            differences.append('Multiplied diffuse/specular alpha baked into a 512-square mipmapped mask')
        # These two source combinations have no exact original-disc program.
        # Preserve surface opacity and the primary normal map. This is the same
        # deliberate detail-normal reduction used by the accepted Forge glass.
        if tag['name'] == r'objects\multi\models\mp_stunt_ramp\shaders\stunt_ramp_panel_light':
            material['options']['bump_mapping'] = 'standard'
            differences.append('Secondary detail normal omitted; primary normal and authored cubemap retained')
        if tag['name'] == r'objects\multi\models\mp_stunt_ramp\shaders\stunt_ramp_glass':
            material['options']['environment_mapping'] = 'none'
            differences.append('Dynamic reflection omitted; glass tint, specular lighting and alpha blend retained')
        plan = native_plan(material, self.categories, self.family)
        unresolved = [p for p in plan['unresolved'] if p['category'] != 'animation']
        if unresolved:
            raise ValueError(f"Reach shader needs explicit conversion: {tag['name']}: {unresolved}")
        template = 'shaders\\' + self.family + '_templates\\_' + '_'.join(map(str, plan['options']))
        post, names, donor = self.importer.materials.native_effect_post(self.group, template, replace_material_textures=True)
        post = bytearray(post)
        switches = self.importer.materials.native_effect_post.parameter_switches[template]
        integer_values, boolean_bits = native_switches(material, switches)
        if 'order3_area_specular' in switches['boolean'] and all(
                'order3_area_specular' not in material.get(field,{}) for field in
                ('booleans','discrete_overrides','discrete_defaults')):
            differences.append('Reach VMF uses native H3 default order-2 area specular; authored specular contribution retained')
        integer_payload = struct.pack('>'+'I'*len(integer_values), *integer_values)
        struct.pack_into('>III', post, 40, len(integer_values), b.alloc(integer_payload) if integer_payload else 0, 0)
        struct.pack_into('>I', post, 52, boolean_bits)
        nt, nc = names
        count, address = struct.unpack_from('>II', post, 16)
        textures = bytearray(b.read(address, count * 24))
        count, address = struct.unpack_from('>II', post, 28)
        constants = bytearray(b.read(address, count * 16))
        for j,name in enumerate(nt):
            if name not in material['textures']:
                raise ValueError(f'Source has no binding for native texture {name}')
            source = material['textures'][name]
            if name in overrides:
                # A baked mask has its own periodic transform. Bind it by name
                # and use authored sampling instead of retaining donor metadata.
                source = dict(source, transform_constant=name, transform_overlays=0)
            if source['external_mode'] or source['bitmap_index']:
                raise ValueError('Reach animated/external texture binding requires review')
            address_mode, filter_mode = native_sampler(source)
            struct.pack_into('>hBBB', textures, j*24+16, 0, address_mode, filter_mode, 0)
            transform_name = source['transform_constant']
            if transform_name is not None and transform_name not in nc:
                raise ValueError(f'Native shader lacks authored texture transform {transform_name}')
            transform_index = nc.index(transform_name) if transform_name is not None else -1
            if transform_index>127:
                raise ValueError('Native texture transform exceeds signed byte index')
            if source['transform_overlays'] and not material['animated']:
                raise ValueError('Reach texture animation has no converted register routes')
            # Animation conversion preserves source function order. Remap the
            # constant by name; preserve its validated function span, not donor's.
            struct.pack_into('>bH', textures, j*24+21, transform_index, source['transform_overlays'])
            if name in overrides:
                struct.pack_into('>I', textures, j*24+12, overrides[name])
            elif source['datum'] != 0xffffffff:
                struct.pack_into('>I', textures, j*24+12, self.bitmap(source['datum']))
        for j,name in enumerate(nc):
            if name in material['constants']:
                struct.pack_into('>4f', constants, j*16, *material['constants'][name])
        post[56:104] = bytes(48)
        self.animation_omissions=[]
        animation_count = convert_material_animation(self, material['post'], post) if material['animated'] else 0
        struct.pack_into('>III', post, 16, len(nt), b.alloc(textures), 0)
        struct.pack_into('>III', post, 28, len(nc), b.alloc(constants), 0)
        root = bytearray(92 if self.group=='rmtr' else 68)
        struct.pack_into('>4sIII', root, 0, b'rmdf', 0, 0, self.native_definition[0])
        struct.pack_into('>III', root, 16, len(plan['options']), b.alloc(struct.pack('>'+'h'*len(plan['options']), *plan['options'])), 0)
        struct.pack_into('>III', root, 40, 1, b.alloc(post), 0)
        struct.pack_into('>HBBii', root, 52, material['flags'], material['sort_layer'], 0, material['fog'], -1)
        root[64:]=tail
        owner,_ = r.newtag(self.group, root)
        self.done[key] = owner
        self.report.append(dict(name=tag['name'], template=template, donor=donor, animations=animation_count,
                                animation_omissions=self.animation_omissions,
                                differences=differences,
                                sampler_names=nt,
                                constant_names=nc,
                                integer_bindings=dict(zip(switches['integer'], integer_values)),
                                boolean_bindings={name:bool(boolean_bits & (1<<j)) for j,name in enumerate(switches['boolean'])},
                                unrepresented_textures=sorted(set(material['textures'])-set(nt)),
                                unrepresented_constants=sorted(set(material['constants'])-set(nc))))
        return self.group, owner
