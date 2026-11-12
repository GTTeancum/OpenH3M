"""Translate reviewed Reach stitched environment keys to retail instance keys.

Preserve the authored spatial branches. Stitched geometry terminals become
instance candidates; the rebuilt definition MOPP performs the second query.
Explicitly replaced convex instances leave this tree because their independent
native objects enter Havok's broadphase. Never remove unaccounted instances.
"""
from collections import Counter, defaultdict
from forge_mopp import terminals, relocate_keys


def convert_environment(code, surface_counts, main_surface_count,
                        geometry_instances, convex_replacements,invalid_main_surfaces=()):
    geometry_instances=set(geometry_instances)
    convex_replacements=set(convex_replacements)
    if geometry_instances & convex_replacements:
        raise ValueError('Geometry and replacement physics overlap')
    invalid_main_surfaces=set(invalid_main_surfaces)
    if not invalid_main_surfaces<=set(range(main_surface_count)):
        raise ValueError('Invalid-surface exclusion outside main table')
    reached=terminals(code);stitched=defaultdict(set);direct=set();main=defaultdict(set)
    def target(key):
        if 8<=key>>26<=13:
            surface=key&0x3ffffff
            if surface>=main_surface_count:raise ValueError('Main surface key out of range')
            main[key>>26].add(surface)
            return key
        if key>>26==16:
            index=key&0x3ffffff
            direct.add(index)
            if index in convex_replacements:return None
            if index not in geometry_instances:raise ValueError('Direct instance lacks native geometry physics')
            return key
        if key>>29==3:
            index=key&65535;surface=(key>>16)&8191
            if index>=len(surface_counts):raise ValueError('Stitched instance key out of range')
            stitched[index].add(surface)
            if index in convex_replacements:return None
            if index not in geometry_instances or surface>=surface_counts[index]:
                raise ValueError('Stitched geometry key lacks matching surface/physics')
            return (16<<26)|index
        raise ValueError(f'Unreviewed Reach environment key {key:#x}')
    expected=Counter()
    for _,_,key in reached:
        value=target(key)
        if value is not None:expected[value]+=1
    if any(main[k]!=main[8] for k in range(9,13)) or main[8]&main[13]:
        raise ValueError('Main surface shape classes do not form the reviewed partition')
    if main[8]|main[13]!=set(range(main_surface_count))-invalid_main_surfaces:
        raise ValueError('Environment MOPP does not cover the main surface table')
    if set(stitched)&direct:raise ValueError('Mixed direct and stitched instance paths')
    if not convex_replacements<=set(stitched)|direct:
        raise ValueError('Replacement lacks authored stitched broadphase entry')
    for index,surfaces in stitched.items():
        if index not in convex_replacements and surfaces!=set(range(surface_counts[index])):
            raise ValueError('Stitched instance surface coverage incomplete')
    # Retail compacts surface-key class bits while retaining instance indices.
    def retail_key(k):return (k&0x60000000)|(((k>>26)&7)<<16)|(k&65535)
    def native_target(k):
        mapped=target(k)
        return None if mapped is None else retail_key(mapped)
    native=relocate_keys(code,native_target,clear_source_bases=True)
    wanted=Counter()
    for k,v in expected.items():wanted[retail_key(k)]+=v
    if Counter(k for _,_,k in terminals(native))!=wanted:
        raise ValueError('Native environment keys differ after compaction')
    return native,dict(main_surfaces=len(main[8]|main[13]),excluded_invalid_main_surfaces=sorted(invalid_main_surfaces),direct_instances=len(direct),
        stitched_geometry_instances=len(set(stitched)-convex_replacements),
        replaced_convex_instances=sorted(convex_replacements),
        geometry_instances_absent_from_source=sorted(geometry_instances-direct-set(stitched)),
        source_terminals=len(reached),native_terminals=sum(wanted.values()),
        source_bytes=len(code),native_bytes=len(native),
        runtime_verified=False)
