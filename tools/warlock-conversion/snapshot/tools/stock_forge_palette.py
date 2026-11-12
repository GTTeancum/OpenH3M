"""Assemble selected original H3 Forge entries using native asset relocation.

Sandbox supplies the preferred duplicate entries; every other original map may
add missing identities. Existing limits/prices/padding are preserved. This is
an explicit option of the existing stock-palette stage, not its new default.
"""
from pathlib import Path
import struct

from assemble_scenario import field
from cache_reader import Cache
from forge_scenery_labels import native_label_text, stage_label_text
from forge_world import CATEGORIES
from source_schema import load_schema
from string_ids import StringTable


def assemble(importer, paths):
    preferred = getattr(importer,'stock_forge_preferred_donor','sandbox')
    excluded = set(getattr(importer,'stock_forge_excluded_categories',()))
    if excluded-set(CATEGORIES):raise ValueError('Unknown excluded Forge category')
    paths = sorted({Path(p).resolve(strict=True) for p in paths},
                   key=lambda p: (p.stem != preferred, p.name))
    if not any(p.stem == preferred for p in paths):
        raise ValueError('Stock Forge palette is missing its preferred native donor: '+preferred)
    arrays = {'Map Variant '+cat+' Palette': bytearray() for cat in CATEGORIES}
    seen, proof, duplicates = set(), [], []
    existing = native_label_text(importer.registry.cache)
    labels, label_proof = {}, []
    for path in paths:
        cache = Cache(path)
        try:
            root = next(t['offset'] for t in cache.tags.values() if t['group']=='scnr')
            schema, strings = load_schema(cache,'scnr'), StringTable(cache)
            english = native_label_text(cache)
            for cat in CATEGORIES:
                if cat in excluded:continue
                name = 'Map Variant '+cat+' Palette'
                f = field(schema,name)
                if int(f.get('elementSize'),0) != 48:
                    raise ValueError('Unexpected native Forge record size')
                for row in cache.block(root+int(f.get('offset'),0),48):
                    datum = cache.u(row+12)
                    tag = cache.tags.get(datum & 65535)
                    if tag is None or tag['salt'] != datum >> 16:
                        raise ValueError('Invalid stock Forge datum in '+path.name)
                    identity = cat,tag['group'],cache.name(datum & 65535)
                    entry = dict(category=cat,group=tag['group'],name=identity[2],donor=path.name,
                                 native_limit=cache.u(row+20),native_cost=cache.unpack('f',row+24)[0])
                    if identity in seen:
                        duplicates.append(entry)
                        continue
                    seen.add(identity)
                    if len(seen)>256:
                        raise ValueError('Stock Forge palette exceeds the original H3 256-quota capacity; select a smaller native palette')
                    result = importer.native_assets.import_named(identity[1:])
                    if result is None or result[0] != tag['group']:
                        raise ValueError('Native Forge dependency absent or changed type: '+identity[2])
                    payload = bytearray(cache.data[row:row+48])
                    payload[:4] = result[0].encode('ascii')
                    payload[4:12] = bytes(8)
                    struct.pack_into('>I',payload,12,result[1])
                    source_label = cache.u(row+16)
                    target_label = strings.translate(source_label,importer.target_strings)
                    struct.pack_into('>I',payload,16,target_label)
                    if target_label not in existing:
                        if source_label not in english:
                            raise ValueError('Missing native Forge label: '+identity[2])
                        text = english[source_label]
                        if target_label in labels and labels[target_label] != text:
                            raise ValueError('Conflicting stock Forge display labels')
                        if target_label not in labels:
                            labels[target_label] = text
                            label_proof.append(dict(donor=path.name,source_id=hex(source_label),
                                                    target_id=hex(target_label),text=text[:-1].decode('utf-8')))
                    arrays[name].extend(payload)
                    proof.append(dict(entry,target_datum=hex(result[1]),label=strings.text(source_label)))
                    print('stock forge:',cat,identity[2],flush=True)
        finally:
            cache.close()
    added_labels = stage_label_text(importer.registry,labels)
    return ({name:(len(payload)//48,bytes(payload)) for name,payload in arrays.items()},
            dict(entries=proof,duplicate_entries=duplicates,added_english_labels=added_labels,
                 label_sources=label_proof,donor_preference=preferred+', then remaining selected original maps by name',
                 excluded_categories=sorted(excluded),
                 validation='Assembly only; runtime menu, resource budgets and gameplay remain unverified'))
