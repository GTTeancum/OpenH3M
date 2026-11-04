"""Follow the unchanged shared shadow path for candidate35 material9821.

This verifies asset routing and native discard instructions, not runtime shadow
coverage or equivalence of the old additional hardware alpha test.
"""
import hashlib,json,os,subprocess,sys
from pathlib import Path
REF=Path(__file__).resolve().parent;REPO=REF.parents[4]
sys.path.insert(0,str(REPO/'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from string_ids import StringTable

def inspect(candidate):
    cache=Cache(REPO/f'work/sky-bridge/payload-{candidate}/sky_bridge.map')
    material=cache.tags[9821]['offset'];definition=cache.u(material+12)&65535
    options=[cache.unpack('h',x)[0] for x in cache.block(material+16,2)]
    root=cache.tags[definition]['offset'];shared=cache.u(root+0x34+12)&65535
    strings=StringTable(cache)
    categories=[strings.text(cache.u(x)) for x in cache.block(root+16,24)]
    entry,=[x for x in cache.block(root+0x1c,16) if cache.u(x)==10]
    shadow_pass,=cache.block(entry+4,16);flags=cache.unpack('H',shadow_pass)[0]
    deps=[cache.unpack('h',x)[0] for x in cache.block(shadow_pass+4,2)]
    shared_root=cache.tags[shared]['offset'];shared_entry=cache.block(shared_root,16)[10]
    default=cache.unpack('i',shared_entry+12)[0]
    dependency,=cache.block(shared_entry,16);category=cache.u(dependency)
    indices=[cache.unpack('i',x)[0] for x in cache.block(dependency+4,4)]
    selected=indices[options[category]]
    assert flags&1 and deps==[category] and categories[category]=='alpha_test'
    program=cache.block(shared_root+16,80)[selected]
    info=cache.pointer(cache.u(program+76));debug=info+40
    _,debug_size,code_size=cache.unpack('III',debug);code=cache.pointer(cache.u(info+16))
    blob=bytes(cache.data[debug:debug+debug_size])+bytes(cache.data[code:code+code_size])
    result=dict(definition=definition,shared_pixel=shared,options=dict(zip(categories,options)),
        shadow_entry=10,shared_pass_flags=flags,category_dependencies=deps,default_program=default,
        option_program_indices=indices,selected_program=selected,gprs=cache.u(program+72),
        program_bytes=len(blob),program_sha256=hashlib.sha256(blob).hexdigest())
    cache.close();return result,blob

def main():
    original,a=inspect(32);corrected,b=inspect(35)
    assert original==corrected and a==b
    out=REPO/'work/sky-bridge/fabric-cutout-build';binary=out/'shadow-global.bin';assembly=out/'shadow-global.asm'
    binary.write_bytes(a)
    env=os.environ.copy();env['TEMP']=env['TMP']=str(REPO/'.local/build-temp')
    subprocess.run([str(out/'shader-tool.exe'),'disassemble',str(binary),str(assembly)],check=True,cwd=REPO,env=env)
    text=assembly.read_text(errors='strict').replace('\x00','')
    for instruction in ('def c255, 0.5, 0, 0, 0','tfetch2D r0.1w__, r0.xy, tf0','subsc r0.z, -c255.x, -r0.y','kill_gt r0._, c255.y, r0.z'):
        assert instruction in text,instruction
    report=dict(candidate32=original,candidate35=corrected,identical_program_and_routing=True,
        shader_alpha_discard_threshold=0.5,
        conclusion='The global shadow program already rejects alpha below 0.5 and is unchanged. Clearing the material hardware-alpha flag does not remove this native shader discard.',
        limitations=['This is an asset/program audit, not runtime shadow coverage verification.',
            'The former material hardware threshold was about 0.501960814; its additional effect in the shadow path has not been measured.',
            'This does not establish visually identical shadow edges or acceptance on physical Xbox 360.'],
        credit=json.loads((REF/'sky-pixel-probe-build.json').read_text())['credit'])
    (out/'shadow-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(identical_program_and_routing=True,selected_program=original['selected_program'],threshold=0.5)))

if __name__=='__main__':main()
