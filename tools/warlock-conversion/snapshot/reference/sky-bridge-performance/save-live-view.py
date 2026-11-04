"""Save an existing OpenH3M guest view with one restored debugger breakpoint.

No UI, input, process creation, image capture, or persistent memory modification.
All guest reads happen while the process is stopped at the verified frame hook.
"""
import argparse
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
from pathlib import Path
import struct
import time
import pefile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--pid', type=int, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
repo = Path(__file__).resolve().parents[5]
args.output.resolve().relative_to(repo)
args.output.mkdir(parents=True, exist_ok=False)
exe = Path('C:/X360/ISOs/H3M/OpenH3M.exe')
binary = exe.read_bytes()
digest = hashlib.sha256(binary).hexdigest()
if digest != 'a90c7d1d10ec7833e58df4f72ba96a7c65ebab5567cd7ba1032b69f1dd0621ad':
    raise ValueError('Executable differs from the recorded human run')
pe = pefile.PE(data=binary, fast_load=True)
guest_hook = 0x82160F28
at = binary.find(struct.pack('<Q', guest_hook))
if at < 0:
    raise ValueError('Frame function mapping missing')
rva = struct.unpack_from('<Q', binary, at+8)[0] - pe.OPTIONAL_HEADER.ImageBase
if not any(s.VirtualAddress <= rva < s.VirtualAddress+s.Misc_VirtualSize
           and s.Characteristics & 0x20000000 for s in pe.sections):
    raise ValueError('Frame mapping is not executable')

k = C.WinDLL('kernel32', use_last_error=True)
p = C.WinDLL('psapi', use_last_error=True)
def api(lib, name, params, result=W.BOOL):
    f = getattr(lib, name); f.argtypes = params; f.restype = result; return f
op = api(k, 'OpenProcess', [W.DWORD,W.BOOL,W.DWORD], W.HANDLE)
close = api(k, 'CloseHandle', [W.HANDLE])
rpm = api(k, 'ReadProcessMemory', [W.HANDLE,C.c_void_p,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)])
wpm = api(k, 'WriteProcessMemory', [W.HANDLE,C.c_void_p,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)])
flush = api(k, 'FlushInstructionCache', [W.HANDLE,C.c_void_p,C.c_size_t])
enum = api(p, 'EnumProcessModules', [W.HANDLE,C.c_void_p,W.DWORD,C.POINTER(W.DWORD)])
modname = api(p, 'GetModuleFileNameExW', [W.HANDLE,W.HMODULE,W.LPWSTR,W.DWORD], W.DWORD)
attach = api(k, 'DebugActiveProcess', [W.DWORD])
detach = api(k, 'DebugActiveProcessStop', [W.DWORD])
kill = api(k, 'DebugSetProcessKillOnExit', [W.BOOL])
wait = api(k, 'WaitForDebugEvent', [C.c_void_p,W.DWORD])
cont = api(k, 'ContinueDebugEvent', [W.DWORD,W.DWORD,W.DWORD])
ot = api(k, 'OpenThread', [W.DWORD,W.BOOL,W.DWORD], W.HANDLE)
getctx = api(k, 'GetThreadContext', [W.HANDLE,C.c_void_p])
setctx = api(k, 'SetThreadContext', [W.HANDLE,C.c_void_p])
def check(ok):
    if not ok: raise C.WinError(C.get_last_error())
ph = op(0x1f0fff, False, args.pid); check(ph)
def read(addr, size):
    b = C.create_string_buffer(size); n = C.c_size_t()
    check(rpm(ph,addr,b,size,C.byref(n)))
    if n.value != size: raise ValueError('Partial guest read')
    return b.raw
def write(addr, data):
    n = C.c_size_t(); check(wpm(ph,addr,data,len(data),C.byref(n)))
    if n.value != len(data): raise ValueError('Partial breakpoint write')
    check(flush(ph,addr,len(data)))

attached=False; original=None; pending=None; captured=None
try:
    mods=(W.HMODULE*1024)(); needed=W.DWORD(); check(enum(ph,mods,C.sizeof(mods),C.byref(needed)))
    image_base=None
    for module in mods[:needed.value//C.sizeof(W.HMODULE)]:
        name=C.create_unicode_buffer(32768)
        if modname(ph,module,name,len(name)) and Path(name.value).resolve()==exe.resolve(): image_base=module
    if image_base is None: raise ValueError('PID is not the recorded OpenH3M executable')
    hook=image_base+rva
    expected=pe.get_data(rva,16)
    if read(hook,16)!=expected or expected[:1]==b'\xcc': raise ValueError('Hook bytes differ')
    check(attach(args.pid)); attached=True; check(kill(False))
    original=read(hook,1); write(hook,b'\xcc')
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        event=C.create_string_buffer(176)
        if not wait(event,100): continue
        code,pid,tid=struct.unpack_from('<III',event)
        pending=(pid,tid,0x10002)
        if code in (3,6):
            fh=struct.unpack_from('<Q',event,16)[0]
            if fh: close(fh)
        if code==1:
            exception=struct.unpack_from('<I',event,16)[0]
            address=struct.unpack_from('<Q',event,32)[0]
            if exception==0x80000003 and address==hook:
                th=ot(0x1f03ff,False,tid); check(th)
                try:
                    backing=C.create_string_buffer(1248); ca=(C.addressof(backing)+15)&~15
                    ctx=(C.c_ubyte*1232).from_address(ca)
                    struct.pack_into('<I',ctx,48,0x10001f); check(getctx(th,ca))
                    ppc,memory=struct.unpack_from('<QQ',ctx,128)
                    write(hook,original); original=None
                    struct.pack_into('<Q',ctx,248,hook); check(setctx(th,ca))
                    r13=struct.unpack('<Q',read(ppc+104,8))[0]&0xffffffff
                    def gu(addr): return struct.unpack('>I',read(memory+addr,4))[0]
                    tls=gu(r13)
                    if not 0x10000<=tls<0xe0000000: raise ValueError(f'Unexpected guest TLS: r13={r13:#x}, tls={tls:#x}')
                    captured={'pid':pid,'exe_sha256':digest,'guest_frame_hook':hex(guest_hook),
                        'host_memory_base':hex(memory),'r13':hex(r13),'tls':hex(tls),
                        'captured_unix_time':time.time(),'blobs':{},'tables':[]}
                    def blob(name,addr,size):
                        raw=read(memory+addr,size)
                        captured['blobs'][name]={'guest_address':hex(addr),'bytes':raw.hex()}
                        return raw
                    blob('tls',tls,0x800)
                    # Native allocation and result getter: 82213440 / 82098CD0.
                    # The older +25c/+1cc route reached this through adjacency.
                    captured['observer_tls_offset']=0x2cc
                    captured['observer_result_offset']=0x110
                    observer=gu(tls+0x2cc)
                    blob('observer',observer,0xf28)
                    game=gu(tls+0x80); blob('game_globals',game,0x1000)
                    engine=gu(tls+0x64); blob('game_engine',engine,0x78)
                    if engine: blob('map_variant',engine+0x78,0xe090)
                    for offset in range(0,0x800,4):
                        try:
                            ptr=gu(tls+offset)
                            if not 0x10000<=ptr<0xe0000000: continue
                            # Preserve bounded per-thread control/camera state for
                            # offline field identification; never restore pointers.
                            try: blob('tls_block_'+hex(offset),ptr,0x400)
                            except OSError: pass
                            header=read(memory+ptr,96); label=header[:32].split(b'\0')[0]
                            if label in (b'players',b'object'):
                                count,stride=struct.unpack_from('>II',header,0x20)
                                data=struct.unpack_from('>I',header,0x44)[0]
                                if not 0<count<=4096 or not 0<stride<=0x10000 or count*stride>2*1024*1024: continue
                                item={'name':label.decode(),'tls_offset':hex(offset),'pointer':hex(ptr),
                                      'count':count,'stride':stride,'data_pointer':hex(data),'header':header.hex()}
                                payload=blob(label.decode(),data,count*stride)
                                captured['tables'].append(item)
                                if label==b'object':
                                    for i in range(count):
                                        head=payload[i*stride:(i+1)*stride]
                                        salt=struct.unpack_from('>H',head)[0]; body=struct.unpack_from('>I',head,12)[0]
                                        if salt and 0x80000000<=body<0xe0000000:
                                            try: blob('object_'+hex(salt<<16|i),body,0x400)
                                            except OSError: blob('object_'+hex(salt<<16|i),body,0x100)
                        except OSError: continue
                    player_bytes=bytes.fromhex(captured['blobs']['players']['bytes'])
                    object_headers=bytes.fromhex(captured['blobs']['object']['bytes'])
                    current=struct.unpack_from('>I',player_bytes,0x28)[0]
                    seen=set()
                    while current!=0xffffffff and current not in seen:
                        seen.add(current)
                        head=object_headers[(current&65535)*16:(current&65535)*16+16]
                        salt=struct.unpack_from('>H',head)[0]
                        if salt!=current>>16: raise ValueError('Stale player/parent handle')
                        size=struct.unpack_from('>H',head,6)[0]
                        address=struct.unpack_from('>I',head,12)[0]
                        if not 0x100<=size<=0x10000: raise ValueError('Unbounded object data size')
                        raw=blob('object_'+hex(current),address,size)
                        current=struct.unpack_from('>I',raw,0x10)[0]
                finally: close(th)
            elif exception!=0x80000003: pending=(pid,tid,0x80010001)
        check(cont(*pending)); pending=None
        if captured: break
    if not captured: raise RuntimeError('Frame hook not reached in ten seconds')
finally:
    if original is not None: write(hook,original)
    if pending: check(cont(*pending))
    if attached: check(detach(args.pid))
    close(ph)

captured['breakpoint_restored']=True
captured['guest_state_modified']=False
destination=args.output/'guest-snapshot.json'
destination.write_text(json.dumps(captured,indent=2)+'\n')
print(json.dumps({'saved':str(destination),'tables':captured['tables'],'blobs':len(captured['blobs']),
                  'breakpoint_restored':True}))
