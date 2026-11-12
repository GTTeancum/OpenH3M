"""Read marker particle input selectors and constants from the original cache.

Offsets/types follow the locally archived Gen4 Effect/Particle schemas. This
does not infer particle lifetime, random state or spawn/update semantics.
"""
import contextlib
import hashlib
import io
import json
import re
import struct
with contextlib.redirect_stdout(io.StringIO()):
    import audit_marker_visual as cache

schema = (cache.RESEARCH/'reference/TagTool-Gen4-Particle.cs').read_text()
states = [name.strip() for name in re.search(
    r'public enum GameStateTypeEnum : sbyte\s*\{([^}]+)',schema).group(1).split(',') if name.strip()]
assert states[:3] == ['ParticleAge','SystemAge','ParticleRandom']
def state_name(value):
    # Retail assets include selectors beyond this reference schema's enum.
    # Preserve those raw IDs for original-code tracing; never alias them.
    return states[value] if 0 <= value < len(states) else f'UnresolvedRetailState({value})'

def property_at(base, offset):
    at = base+offset
    selectors = struct.unpack_from('>4b',cache.data,at)
    size = cache.u(at+4)
    assert 32 <= size <= 4096
    data_at = cache.offset(cache.u(at+16))
    function = cache.data[data_at:data_at+size]
    return dict(offset=hex(offset), selectors=selectors,
        input=state_name(selectors[0]), range=state_name(selectors[1]),
        modifier=selectors[2], modifier_input=state_name(selectors[3]),
        runtime_constant=struct.unpack_from('>f',cache.data,at+24)[0],
        runtime_flags=struct.unpack_from('>H',cache.data,at+28)[0],
        function_sha256=hashlib.sha256(function).hexdigest())

report = dict(schema_sha256=hashlib.sha256(schema.encode()).hexdigest(),particles=[],systems=[])
for tag in (16658,16660):
    base=cache.tags[tag]['offset']
    properties={name:property_at(base,offset) for offset,name in (
        (0x84,'aspect'),(0xa4,'color'),(0xc4,'intensity'),(0xe4,'alpha'),
        (0x10c,'frame'),(0x12c,'animation_rate'),(0x14c,'palette'))}
    report['particles'].append(dict(tag=tag,name=cache.tags[tag]['name'],properties=properties,
        appearance_flags=cache.u(base+0x10),billboard_style=struct.unpack_from('>H',cache.data,base+0x14)[0]))
effect=cache.tags[16657]['offset']
assert cache.u(effect+0x34)==1
event=cache.offset(cache.u(effect+0x38))
assert cache.u(event+0x38)==2
systems=cache.offset(cache.u(event+0x3c))
for index in range(2):
    system=systems+index*0x7c
    assert cache.u(system+0x68)==1
    emitter=cache.offset(cache.u(system+0x6c))
    properties={name:property_at(emitter,offset) for offset,name in (
        (0x110,'starting_count'),(0x130,'max_count'),(0x150,'emission_rate'),
        (0x170,'emission_per_distance'),(0x190,'lifespan'),(0x234,'initial_velocity'),
        (0x254,'rotation'),(0x274,'rotation_rate'),(0x294,'size'),(0x2b4,'scale'),
        (0x2d4,'scale_x'),(0x2f4,'scale_y'),(0x314,'tint'),(0x334,'alpha'),
        (0x354,'black_point'),(0x374,'white_point'))}
    report['systems'].append(dict(index=index,size_scale=struct.unpack_from('>f',cache.data,system+0x30)[0],
        properties=properties))
report['limitation']='Authored selectors/constants only; original spawn, random/correlation state, lifetime update and interpolation still require execution/integration.'
output=cache.RESEARCH/'isolated/marker-particle-inputs.json'
output.write_text(json.dumps(report,indent=2)+'\n')
for particle in report['particles']:
    print(particle['tag'],{k:(v['input'],v['range'],v['modifier']) for k,v in particle['properties'].items()})
print(output)
