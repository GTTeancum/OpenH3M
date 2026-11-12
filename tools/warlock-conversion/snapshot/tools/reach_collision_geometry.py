"""Serialize bounded Reach collision arrays into original H3 byte order.

Accept an expanded tree only with identical original plane prefix. Physics
acceleration and instance headers remain the caller's responsibility.
"""
import struct

FORMATS={'nodes':'Q','planes':'4I','leaves':'BBHI','references':'2H',
         'nodes2d':'3I2H','surfaces':'5H2B','edges':'6H','vertices':'3I2H'}

def convert_surface_mappings(ranges,mappings,cluster_triangle_remaps=None):
    """Reach 20:12 packed triangle/cluster -> H3 ushort pair.

    TagTool TagDeserializer.DeserializePlaneReference documents the version
    split; the per-surface start/count also narrows from int/int to ushort/short.
    """
    if len(ranges)%8 or len(mappings)%4:raise ValueError('Unaligned collision surface mappings')
    mapping_count=len(mappings)//4
    native_ranges=bytearray();native_mappings=bytearray()
    for start,count in struct.iter_unpack('<ii',ranges):
        if count==0 and start==-1:start=65535
        elif start<0 or start+count>mapping_count:raise ValueError('Collision surface mapping span outside table')
        if not 0<=start<=65535 or not 0<=count<=32767:
            raise ValueError('Collision surface span exceeds native widths')
        native_ranges.extend(struct.pack('>Hh',start,count))
    cluster_triangle_remaps=cluster_triangle_remaps or {}
    for (value,) in struct.iter_unpack('<I',mappings):
        triangle,cluster=value>>12,value&4095
        if cluster in cluster_triangle_remaps:
            if triangle not in cluster_triangle_remaps[cluster]:
                raise ValueError('Split cluster lacks a collision triangle destination')
            triangle,cluster=cluster_triangle_remaps[cluster][triangle]
            if not 0<=triangle<=65535 or not 0<=cluster<=65535:
                raise ValueError('Split collision destination exceeds native widths')
        if triangle>65535:raise ValueError('Reach collision triangle reference exceeds H3 width')
        native_mappings.extend(struct.pack('>HH',triangle,cluster))
    return bytes(native_ranges),bytes(native_mappings)

def convert_geometry(geometry,expanded=None):
    arrays={name:bytes(geometry[name][1]) for name in FORMATS}
    if geometry['supernodes'][0] and expanded is None:
        raise ValueError('Reach collision supernodes require verified expansion')
    if expanded is not None:
        nodes,planes=struct.unpack_from('<II',expanded)
        if len(expanded)!=8+nodes*8+planes*16:
            raise ValueError('Truncated expanded tree')
        arrays['nodes']=expanded[8:8+nodes*8]
        arrays['planes']=expanded[8+nodes*8:]
        if not arrays['planes'].startswith(bytes(geometry['planes'][1])):
            raise ValueError('Expanded tree does not retain original plane table')
    counts={name:len(data)//struct.calcsize('<'+FORMATS[name]) for name,data in arrays.items()}
    if counts['planes']>32768 or counts['surfaces']>32768 or counts['nodes2d']>32768:
        raise ValueError('Collision exceeds native signed index widths')
    if counts['vertices']>65535 or counts['edges']>65535:
        raise ValueError('Collision exceeds native unsigned index widths')
    def check(index,name,sentinel=False):
        if sentinel and index==65535:return
        if not 0<=index<counts[name]:raise ValueError(f'Collision {name} reference out of bounds: {index}')
    for (value,) in struct.iter_unpack('<Q',arrays['nodes']):
        check(value&65535,'planes')
        for child in ((value>>16)&0xffffff,(value>>40)&0xffffff):
            if child!=0xffffff:check(child&0x7fffff,'leaves' if child&0x800000 else 'nodes')
    for flags,flags2,count,start in struct.iter_unpack('<BBHI',arrays['leaves']):
        if flags&~1 or flags2 or (start+count>counts['references'] and not (count==0 and start==0xffffffff)):
            raise ValueError(f'Unsupported collision leaf flags/reference span: flags={flags:#x}/{flags2:#x}, '
                             f'range={start}+{count}/{counts["references"]}')
    for plane,node in struct.iter_unpack('<2H',arrays['references']):
        check(plane&32767,'planes')
        if node!=65535:check(node&32767,'surfaces' if node&32768 else 'nodes2d')
    for row in struct.iter_unpack('<3I2H',arrays['nodes2d']):
        for child in row[3:]:
            if child!=65535:check(child&32767,'surfaces' if child&32768 else 'nodes2d')
    surfaces=bytearray()
    for plane,edge,material,bset,bindex,flags,best in struct.iter_unpack('<5H2B',arrays['surfaces']):
        if flags&128:plane|=32768;flags&=127
        if flags&~63:raise ValueError(f'Reach-only collision surface flags: {flags:#x}')
        check(plane&32767,'planes');check(edge,'edges')
        surfaces.extend(struct.pack('>5H2B',plane,edge,material,bset,bindex,flags,best))
    for row in struct.iter_unpack('<6H',arrays['edges']):
        for j,name in enumerate(('vertices','vertices','edges','edges','surfaces','surfaces')):
            check(row[j],name,sentinel=True)
    for row in struct.iter_unpack('<3I2H',arrays['vertices']):check(row[3],'edges',sentinel=True)
    output={name:b''.join(struct.pack('>'+FORMATS[name],*row)
                        for row in struct.iter_unpack('<'+FORMATS[name],data)) for name,data in arrays.items()}
    output['surfaces']=bytes(surfaces)
    return output,counts
