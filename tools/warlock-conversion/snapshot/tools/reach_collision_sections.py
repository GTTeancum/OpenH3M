"""Pack converted Reach collision sections with native resource fixups.

The caller owns native instance headers/bounds and the final resource root.
Keeping this separate prevents publishing zero/default bounds or silently
discarding Reach convex physics while those integrations remain unfinished.
"""
import struct
from reach_bsp_collision_source import ReachBspCollisionSource
from reach_collision_geometry import convert_geometry,convert_surface_mappings,FORMATS
from reach_physics import convert_tag_mopp


class CollisionSections:
    def __init__(self,resource):
        self.source=resource
        self.reader=ReachBspCollisionSource(resource)
        self.control=bytearray(16)
        self.raw=bytearray()
        self.fixups=[]
        self.sections=[]

    def allocate(self,payload,resident=False):
        buffer=self.control if resident else self.raw
        buffer.extend(bytes((-len(buffer))%16))
        at=len(buffer)
        buffer.extend(payload)
        return at

    def block(self,at,count,payload,stride,resident=False):
        if count<0 or len(payload)!=count*stride:
            raise ValueError('Native collision block payload/count mismatch')
        if not 0<=at<=len(self.control)-12:
            raise ValueError('Native collision block header outside control')
        struct.pack_into('>III',self.control,at,count,0,0)
        if count:
            target=self.allocate(payload,resident)
            self.fixups.append((at+4,(0x20000000 if resident else 0x40000000)|target))
            return target

    def geometry(self,source_at,expanded=None,header=None,geometry_override=None):
        payloads,counts=convert_geometry(self.reader.geometry(source_at) if geometry_override is None else geometry_override,expanded)
        if header is None:header=self.allocate(bytes(96),True)
        for index,name in enumerate(FORMATS):
            self.block(header+index*12,counts[name],payloads[name],struct.calcsize('>'+FORMATS[name]))
        self.sections.append(dict(kind='geometry',source=source_at,header=header,counts=counts))
        return header

    def mopps(self,source_at,descriptor=None):
        rows=self.reader.headers(source_at,96)
        if descriptor is None:descriptor=self.allocate(bytes(12),True)
        headers=self.block(descriptor,len(rows),bytes(64*len(rows)),64,True)
        for index,at in enumerate(rows):
            count,code=self.reader.block(at+80,1)
            header,code=convert_tag_mopp(bytes(self.source.data[at:at+96]),code)
            dst=headers+index*64
            self.control[dst:dst+64]=header
            self.block(dst+48,count,code,1)
        self.sections.append(dict(kind='mopps',source=source_at,header=descriptor,count=len(rows)))
        return descriptor

    def mappings(self,ranges_at,triangles_at,header=None,cluster_triangle_remaps=None):
        count,ranges=self.reader.block(ranges_at,8)
        triangle_count,triangles=self.reader.block(triangles_at,4)
        native_ranges,native_triangles=convert_surface_mappings(ranges,triangles,cluster_triangle_remaps)
        if header is None:header=self.allocate(bytes(24),True)
        self.block(header,count,native_ranges,4)
        self.block(header+12,triangle_count,native_triangles,4)
        self.sections.append(dict(kind='mappings',source=ranges_at,header=header,
                                  surfaces=count,triangles=triangle_count))
        return header

    def generated_mopp(self,packed,descriptor,surface_count):
        """Insert native compiler output; never copy Reach's stale cached info."""
        from forge_mopp import terminals
        if len(packed)<48:raise ValueError('Truncated generated MOPP')
        size,capacity=struct.unpack_from('<II',packed,36)
        if not 0<size<=(capacity&0x7fffffff) or not 0<=len(packed)-48-size<=15:
            raise ValueError('Invalid generated MOPP allocation')
        if any(struct.unpack_from('<I',packed,p)[0] for p in (0,8,12,32)):
            raise ValueError('Generated MOPP contains runtime state')
        code=packed[48:48+size]
        if {key for _,_,key in terminals(code)}!=set(range(surface_count)):
            raise ValueError('Generated MOPP keys differ from collision surfaces')
        header=bytearray(64)
        struct.pack_into('>HH',header,4,*struct.unpack_from('<HH',packed,4))
        struct.pack_into('>4I',header,16,*struct.unpack_from('<4I',packed,16))
        struct.pack_into('>II',header,36,size,capacity)
        dst=self.block(descriptor,1,header,64,True)
        self.block(dst+48,size,code,1)
        return dst

    def validate(self):
        seen=set()
        for pointer,target in self.fixups:
            if pointer in seen:raise ValueError('Duplicate native resource fixup')
            seen.add(pointer)
            if not 4<=pointer<=len(self.control)-8:
                raise ValueError('Fixup outside native control data')
            segment,offset=target>>29,target&0x1fffffff
            buffer=self.control if segment==1 else self.raw if segment==2 else None
            if buffer is None or not 0<=offset<len(buffer):
                raise ValueError('Fixup target outside native resource')
            if struct.unpack_from('>I',self.control,pointer)[0]:
                raise ValueError('Serialized runtime pointer must be zero')
        return dict(control_bytes=len(self.control),raw_bytes=len(self.raw),fixups=len(seen))
