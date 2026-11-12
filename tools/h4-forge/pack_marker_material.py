"""Package verified original marker pixel programs/textures for the local host.

The shader wrapper supplies canonical billboard interpolants with the verified
original near/far fade block. Particle lifecycle and world size remain open.
No generated shader or texture payload belongs in Git or a public package.
"""
import hashlib
import json
import struct
import subprocess
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'work/h4-forge-research/isolated'
SHADERS = WORK / 'marker-shaders'
fields = json.loads((WORK / 'marker-effect-fields.json').read_text())
checks = json.loads((SHADERS / 'execution-validation.json').read_text())
fade_checks = json.loads((SHADERS / 'fade-validation.json').read_text())
payload = bytearray()
textures = {}
for index, width, height, wrap in ((7748,256,256,False),(16659,256,1,False),
                                  (419,128,128,True),(341,128,128,True),(16661,512,512,True)):
    pixels = (WORK / 'marker-bitmaps' / f'{index}.rgba').read_bytes()
    if len(pixels) != width*height*4:
        raise ValueError('Invalid decoded texture extent')
    textures[index] = (len(payload), width, height, wrap)
    payload += pixels

source = ['// Private original H4 pixel programs; canonical interpolants pending full particle integration.',
          'ByteAddressBuffer marker_pixels : register(t1);',
          '''float4 MarkerTexel(uint offset,int2 p,int2 extent,bool wrap) {
 p=wrap?((p%extent)+extent)%extent:clamp(p,0,extent-1);
 uint rgba=marker_pixels.Load(offset+4*(p.y*extent.x+p.x));
 return float4(rgba&255,(rgba>>8)&255,(rgba>>16)&255,rgba>>24)/255.0;
}
float4 MarkerSample(uint offset,uint w,uint h,bool wrap,float2 uv) {
 float2 samplePosition=uv*float2(w,h)-.5;int2 p=int2(floor(samplePosition));float2 f=frac(samplePosition);
 int2 extent=int2(w,h);
 return lerp(lerp(MarkerTexel(offset,p,extent,wrap),MarkerTexel(offset,p+int2(1,0),extent,wrap),f.x),
             lerp(MarkerTexel(offset,p+int2(0,1),extent,wrap),MarkerTexel(offset,p+1,extent,wrap),f.x),f.y);
}''']
for material, tag, ids, name in ((331,'16658',(7748,16659,419,341),'Ring'),(16,'16660',(16661,),'Rays')):
    fade = next(row for row in fade_checks if row['material'] == material)
    fade_code = (SHADERS / f'{material}-fade-block.generated.hlsl').read_bytes()
    if hashlib.sha256(fade_code).hexdigest() != fade['extraction']['hlsl_sha256']:
        raise ValueError('Fade block changed since original-microcode verification')
    source.append(fade_code.decode().replace('H4', f'H4Fade{name}'))
    source.append(f'float Marker{name}Fade(float depth) {{ float4 c[256],r[8];uint b[8];')
    source.append('[unroll]for(uint i=0;i<256;++i)c[i]=0;[unroll]for(uint j=0;j<8;++j){r[j]=0;b[j]=0;}')
    source.append(f'c[87].xy=float2({fade["near_range"]:.9g},{fade["near_cutoff"]:.9g});')
    source.append(f'c[88].xy=float2({fade["far_range"]:.9g},{fade["far_cutoff"]:.9g});')
    source.append(f'r[0].{"z" if material==331 else "x"}=depth;float2 fades=H4Fade{name}MarkerPixel(c,b,r).xy;return fades.x*fades.y;}}')
    code = (SHADERS / f'{material}-ps.generated.hlsl').read_bytes()
    checked = next(row for row in checks if row['material'] == material)
    if hashlib.sha256(code).hexdigest() != checked['generated_hlsl_sha256']:
        raise ValueError('Material changed since original-microcode verification')
    source.append(f'float4 H4{name}Fetch(uint slot,float3 uv) {{')
    for slot, index in enumerate(ids):
        offset, width, height, wrap = textures[index]
        source.append(f'if(slot=={slot})return MarkerSample({offset},{width},{height},{str(wrap).lower()},uv.xy);')
    # b228 remains disabled below: the scene renderer supplies actual occlusion.
    source.append('return 0; }')
    source.append(code.decode().replace('H4', f'H4{name}'))
    post = fields[tag]['fields']['Postprocess Definition@0x5C'][0]
    values = {0:(1,1,1,1),1:(0,0,0,0),2:(1,1,1,0),3:(post['Alpha Blend Mode@0x78']['value'],0,0,0)}
    for offset,key in ((160,'Float Constants@0x18'),(184,'Texture Constants@0xC')):
        values.update((offset+i,tuple(row.values())) for i,row in enumerate(post[key]))
    constants = struct.unpack('>16f',(SHADERS/f'{material}-ps-0.constants').read_bytes())
    values[250],values[251]=constants[8:12],constants[12:16]
    source.append(f'float4 Marker{name}(float2 uv,float elapsed,float fade) {{ float4 c[256],r[8];uint b[8];')
    source.append('[unroll]for(uint i=0;i<256;++i)c[i]=0;[unroll]for(uint j=0;j<8;++j){r[j]=0;b[j]=0;}')
    for index, value in values.items():
        source.append(f'c[{index}]=float4('+','.join(format(float(v),'.9g') for v in value)+');')
    source.append(f'b[4]={post["Boolean Constants@0x3C"]};c[1].x=elapsed;r[0]=float4(uv,uv);r[1]=float4(0,0,1,1);r[2].z=.5;')
    if material==331:
        source.append('r[3]=float4(0,0,0,1);r[4]=float4(1,1,1,fade);')
    else:
        # Initial authored particle color from the Gen4 color-function header.
        color=bytes.fromhex(fields[tag]['fields']['Unknown@0xA8'])[4:8]
        source.append('r[3]=float4('+','.join(format(v/255,'.9g') for v in color[1:])+',fade);')
    source.append(f'return H4{name}MarkerPixel(c,b,r); }}')
source.append('''float3 MarkerMaterial(float2 uv,float elapsed,float viewDepth) {
 float4 ring=MarkerRing(uv,elapsed,MarkerRingFade(viewDepth));
 float4 rays=MarkerRays(uv,elapsed,MarkerRaysFade(viewDepth));
 // Both layers export unpremultiplied color with particle alpha separately.
 // Consume that alpha in this interim additive host compositor.
 return ring.rgb*ring.a+rays.rgb*rays.a;
}''')
shader='\n'.join(source).encode()
shader_path=WORK/'marker-material.generated.hlsl'
shader_path.write_bytes(shader)
compiler=ROOT/'work/rexglue-sdk/out/win-amd64/h4_forge_marker_compile.exe'
prefix=WORK/'marker-material'
subprocess.run([str(compiler),str(shader_path),str(prefix),"3"],cwd=ROOT,check=True,timeout=60,
    env=dict(os.environ,TEMP=str(ROOT/'work/build-temp'),TMP=str(ROOT/'work/build-temp')))
programs=[Path(str(prefix)+f'.{i}.dxbc').read_bytes() for i in range(2)]
assert all(code.startswith(b'DXBC') for code in programs)
out=WORK/'marker-material.bin'
out.write_bytes(struct.pack('<4sIIII',b'H4MP',3,len(programs[0]),len(programs[1]),len(payload))+b''.join(programs)+payload)
(WORK/'marker-material.json').write_text(json.dumps(dict(
    sha256=hashlib.sha256(out.read_bytes()).hexdigest(), shader_bytes=len(shader),texture_bytes=len(payload),
    source_checks=checks, fade_checks=fade_checks, compiled_program_sha256=[hashlib.sha256(p).hexdigest() for p in programs],
    limitations='Canonical billboard interpolants; original fade blocks use camera-axis depth at default near scale/FOV. Particle lifetime, world size and intensity/tint curves remain open.'),indent=2)+'\n')
print(f'{out}: {len(shader)} shader bytes, {len(payload)} private texture bytes')
