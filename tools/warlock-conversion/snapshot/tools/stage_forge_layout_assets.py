"""Add only the architectural dependencies used by supplied Reach layouts.

Existing palette indices remain stable. The output is a private candidate,
not an installation; shared map resources are imported once per base map.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from cache_reader import Cache
from cache_registry import CacheRegistry
from map_builder import MapBuilder
from tag_importer import TagImporter
from reach_forge_assets import ReachForgeAssets
from reach_forge_palette import ReachCache
from reach_forge_variant import read_variant
from forge_scenery_labels import stage_labels


UTILITIES = ('ff_light_', 'ff_man_cannon', 'ff_grav_lift', 'ff_teleporter')


def architecture(tag):
    return tag['name'].startswith('objects\\levels\\forge\\ff_') and not tag['name'].split('\\')[-1].startswith(UTILITIES)


def publish_residency(registry):
    """Mirror the new resource/tag union to both already-existing BSPs."""
    r = registry
    b,c = r.builder,r.cache
    manifests = list(c.block(r.manifest_field,120))
    if len(manifests)!=2:
        raise ValueError('Expected the accepted two-BSP Forge base')
    r.finalize()
    for field in (0,0x54,0x60):
        n,p = struct.unpack('>II',b.read(r.address(manifests[0]+field),8))
        union = bytearray(b.read(p,n*4))
        other = r.table(manifests[1]+field,4)
        union.extend(bytes(max(0,len(other)-len(union))))
        for j in range(0,len(other),4):
            struct.pack_into('>I',union,j,struct.unpack_from('>I',union,j)[0] |
                             struct.unpack_from('>I',other,j)[0])
        pointer = b.alloc(union)
        for row in manifests:
            b.put(r.address(row+field),'III',len(union)//4,pointer,0)
    b.put(r.address(manifests[1]+0x30),'I',c.u(manifests[1]+0x30)+r.added_bytes)


def build(args):
    # All generated artifacts are confined even if the CLI is invoked elsewhere.
    repository = Path(__file__).resolve().parents[4]
    for path in (args.output,args.report):
        if not path.resolve().is_relative_to(repository):
            raise ValueError('Output outside repository')
    if args.output.resolve()==args.basis.resolve():
        raise ValueError('Never overwrite the accepted basis')
    import capstone  # Must precede XEX loader's local module search.
    from build_scenario_checkpoint import resource_salt
    salt = resource_salt(args.xex)
    source = ReachCache(args.reach)
    mcc = Cache(args.mcc,True)
    b = MapBuilder(args.basis,0x400000)
    a = None
    try:
        r = CacheRegistry(b,salt)
        bindings = {(x['group'],x['source']):(x['group'],int(x['datum'],16))
                    for x in json.loads(args.bindings.read_text())['tags']}
        i = TagImporter(mcc,r,bindings=bindings,disc_maps=args.disc)
        a = ReachForgeAssets(source,i,args.bridge,{r'maps\shared.map':str(args.shared)})
        palette = source.palette()
        wanted = {}
        for path in args.layout:
            for obj in read_variant(path.read_bytes())['objects']:
                tag = palette[obj['folder']][obj['item']]
                if architecture(tag):
                    wanted[tag['name']] = tag
        c = r.cache
        root = next(t['offset'] for t in c.tags.values() if t['group']=='scnr')
        inverse = {datum:name for (_,name),(_,datum) in i.resolved.items()}
        result,rows_by_kind = [],{}
        for kind in range(1,8):
            rows = list(c.block(root+0x1e8+(kind-1)*12,48))
            rows_by_kind[kind] = bytearray(b''.join(c.data[row:row+48] for row in rows))
            for index,row in enumerate(rows):
                datum = c.u(row+12)
                name = inverse.get(datum) or c.name(datum&65535)
                result.append(dict(kind=kind,index=index,datum=datum,name=name,
                    group=c.tags[datum&65535]['group'],display_sid=c.u(row+16),
                    maximum=c.unpack('i',row+20)[0],price=c.unpack('f',row+24)[0]))
        existing = {p['name'] for p in result}
        labels = {}
        for name,tag in sorted(wanted.items()):
            if name in existing:
                continue
            group,datum = a.import_tag(tag['datum'])
            sid = a.translate_string(tag['display_sid'])
            labels[tag['display_sid']] = sid
            data = rows_by_kind[4]
            index = len(data)//48
            # Match the accepted native Forge pieces' 4-credit/50-instance
            # convention; keep the original 1,500-credit map budget unchanged.
            data.extend(struct.pack('>4sIIIIif',group.encode(),0,0,datum,sid,50,4.)+bytes(20))
            result.append(dict(kind=4,index=index,datum=datum,name=name,group=group,
                               display_sid=sid,maximum=50,price=4.))
        if labels:
            stage_labels(source,r,labels)
        data = rows_by_kind[4]
        b.put(r.address(root+0x20c),'III',len(data)//48,b.alloc(data),0)
        i.target_strings.stage()
        publish_residency(r)
        payload = b.finish(salt)
        report = dict(basis=str(args.basis),basis_sha256=hashlib.sha256(args.basis.read_bytes()).hexdigest(),
            output=str(args.output),sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload),
            metadata_used=b.used,resource_bytes_added=r.added_bytes,compressed_bytes_added=len(b.raw),
            palette=result,tags=a.report+i.added,materials=a.materials.report,
            labels_added=len(labels),layouts=[str(p) for p in args.layout],
            validation='Serialized candidate only; native selection and gameplay not yet verified')
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_bytes(payload)
        args.report.write_text(json.dumps(report,indent=2))
        print(f'Built {args.output}: {len(payload):,} bytes; {len(labels)} new palette entries')
    finally:
        if a:a.close()
        b.close();mcc.close();source.close()


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('basis','bindings','reach','mcc','shared','disc','xex','bridge','output','report'):
        parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--layout',type=Path,action='append',required=True)
    build(parser.parse_args())
