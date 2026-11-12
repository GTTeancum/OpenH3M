"""Conservatively extend authored cluster PVS for one appended split cluster."""
import copy
import struct


def split_zone(zone,bsp_index,parent):
    out=copy.deepcopy(zone)
    counts=[len(b['open']) for b in zone['bsps']]
    if zone['mask']!=(1<<len(counts))-1:
        raise ValueError('Sparse BSP masks require explicit slot mapping')
    if not 0<=bsp_index<len(counts) or not 0<=parent<counts[bsp_index]:
        raise ValueError('Invalid split PVS cluster')
    child=counts[bsp_index]
    def duplicate_bit(words,count):
        if len(words)!=(count+31)//32:raise ValueError('PVS vector width disagrees with cluster count')
        if count%32 and words[-1]>> (count%32):raise ValueError('Unexpected PVS padding bits')
        expanded=list(words)
        if child//32==len(expanded):expanded.append(0)
        if (words[parent//32]>>(parent%32))&1:expanded[child//32]|=1<<(child%32)
        return expanded
    for bi,b in enumerate(out['bsps']):
        for key in ('open','closed'):
            if len(b[key])!=counts[bi]:raise ValueError('PVS row count mismatch')
            for row in b[key]:
                if len(row)!=len(counts):raise ValueError('PVS BSP vector count mismatch')
                for ti,words in enumerate(row):
                    if len(words)!=(counts[ti]+31)//32:raise ValueError('PVS target width mismatch')
                row[bsp_index]=duplicate_bit(row[bsp_index],child)
            if bi==bsp_index:b[key].append(copy.deepcopy(b[key][parent]))
        if bi==bsp_index:
            for key in ('attached_skies','visible_skies'):
                if len(b[key])!=child:raise ValueError('PVS sky row count mismatch')
                b[key].append(b[key][parent])
            b['audio']=duplicate_bit(b['audio'],child)
        for mapping in b['seam_mappings']:
            for refs in mapping:
                if [bsp_index,parent] in refs and [bsp_index,child] not in refs:
                    refs.append([bsp_index,child])
        if bi==bsp_index:
            if len(b['seam_mappings'])!=child:raise ValueError('PVS seam row count mismatch')
            b['seam_mappings'].append(copy.deepcopy(b['seam_mappings'][parent]))
    return out


def serialize_matrix(rows,allocate):
    """Native H3 nested cluster/vector/dword layout, shared with Reach."""
    def block(data,count):return struct.pack('>III',count,allocate(data) if data else 0,0)
    result=bytearray()
    for row in rows:
        vectors=b''.join(block(b''.join(struct.pack('>I',w) for w in words),len(words)) for words in row)
        result.extend(block(vectors,len(row)))
    return bytes(result)
