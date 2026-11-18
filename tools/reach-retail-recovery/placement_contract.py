"""Strict, separately reconstructed format policy for a placement that has already been recreated.

It intentionally does not create a gameplay object, choose a team/mode, decide a BSP geometrically,
compile visibility or claim that changing a record fixes a black screen. It touches only the two
attachment mask words after validating one source placement and an explicit source/target BSP map.
"""
import struct

def apply_automatic_ownership(source, native, source_to_native, *, strict_identity=True):
    if len(source)!=0xdc or len(native)!=0xb4:raise ValueError('not matching retail Reach/H3 scenery row sizes')
    def h(row,offset):return struct.unpack_from('>H',row,offset)[0]
    if source[0x33] or h(source,0x34):raise ValueError('manual/zone-set attachment requires separate proof')
    if native[0x40]:raise ValueError('not an automatically attached native object')
    if strict_identity and source[0x3c:0x44]!=native[0x38:0x40]:raise ValueError('full object identifier mismatch')
    flags=h(source,0x54)
    if not flags:raise ValueError('source has no compiled ownership; need independent point proof')
    slots=[i for i in range(16) if (flags>>i)&1]
    if any(i not in source_to_native for i in slots):raise ValueError('source references absent native BSP')
    targets=[source_to_native[i] for i in slots]
    if any(type(i)!=int or not 0<=i<16 for i in targets) or len(set(targets))!=len(slots):raise ValueError('not a valid injective source to native BSP mapping')
    mask=sum(1<<i for i in targets);out=bytearray(native)
    old=(h(out,0x32),h(out,0x50))
    if old not in {(0,0),(0,mask),(mask,0)}:raise ValueError('cannot safely overwrite an independent attachment assignment')
    struct.pack_into('>H',out,0x32,0);struct.pack_into('>H',out,0x50,mask)
    return bytes(out)


def propose_e25(path):
    from native_attach_audit import Native
    import hashlib
    from pathlib import Path
    expected='8813ee366770e01f5e2efa9a18febb43fd7d1782715370227a5a5b3fd4112e4b'
    with Path(path).open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
    if actual!=expected:raise ValueError('exact registered E25 Reflection not supplied; no proposal')
    c=Native(path);edits=[]
    try:
        for idx,row,name,manual,policy,compiled in c.scenery():
            if name not in {r'objects\multi\spawning\respawn_point',r'objects\multi\spawning\respawn_point_invisible'}:continue
            engine=c.u16(row+0x84); team=c.u16(row+0x86)
            if (engine and not(engine&2)) or team!=8:continue
            if (manual,policy,compiled)!=(2,0,0):raise ValueError('this original marker did not have the documented E25 failure')
            edits.extend([{'index':idx,'offset':row+0x32,'old':'0002','desired':'0000'}, {'index':idx,'offset':row+0x50,'old':'0000','desired':'0002'}])
    finally:c.close()
    if len(edits)!=294:raise ValueError('must be exactly 147 existing eligible neutral markers or stop')
    return {'mode':'read-only source-content proposal; does NOT write or launch anything', 'base_sha256':expected,'locked_historical_after_normal_header_digests_sha256':'718a67d9253854d682273ebb29dce16db01665d7e32c83e7cccf7af47eeffb6b','edits':edits}
