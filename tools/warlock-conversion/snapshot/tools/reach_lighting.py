"""Decode Reach six-byte static-lighting probes without discarding direction.

Reference: TheGuardians/TagTool ce2dc6ac13072b160752af618ea1dc143e2727ac,
TagTool/Lighting/VmfConversion.cs. Direction vectors retain reference precision.
Target SH/RGBE encoding is a separate step; this is not an H3 buffer writer.
"""
import numpy as np

DIRECTIONS = np.array([(0.0, 0.0, 1.0), (0.36070001, 0.0, 0.93269998), (0.1115, 0.34310001, 0.93269998), (0.67290002, 0.0, 0.73970002), (0.4795, 0.3484, 0.80540001), (0.2079, 0.63990003, 0.73970002), (0.8944, 0.0, 0.4472), (0.78439999, 0.34310001, 0.51679999), (0.56870002, 0.63990003, 0.51679999), (0.2764, 0.85070002, 0.4472), (-0.29179999, 0.212, 0.93269998), (-0.1832, 0.56370002, 0.80540001), (-0.54439998, 0.3955, 0.73970002), (-0.083899997, 0.852, 0.51679999), (-0.43290001, 0.73860002, 0.51679999), (-0.72359997, 0.52569997, 0.4472), (-0.29179999, -0.212, 0.93269998), (-0.5927, -0.0, 0.80540001), (-0.54439998, -0.3955, 0.73970002), (-0.8362, 0.18350001, 0.51679999), (-0.8362, -0.18350001, 0.51679999), (-0.72359997, -0.52569997, 0.4472), (0.1115, -0.34310001, 0.93269998), (-0.1832, -0.56370002, 0.80540001), (0.2079, -0.63990003, 0.73970002), (-0.43290001, -0.73860002, 0.51679999), (-0.083899997, -0.852, 0.51679999), (0.2764, -0.85070002, 0.4472), (0.4795, -0.3484, 0.80540001), (0.56870002, -0.63990003, 0.51679999), (0.78439999, -0.34310001, 0.51679999), (0.96469998, -0.212, 0.1561), (0.96469998, 0.212, 0.1561), (0.90509999, -0.3955, -0.1561), (0.98549998, 0.0, -0.1699), (0.90509999, 0.3955, -0.1561), (0.72359997, -0.52569997, -0.4472), (0.8362, -0.18350001, -0.51679999), (0.8362, 0.18350001, -0.51679999), (0.72359997, 0.52569997, -0.4472), (0.4998, 0.852, 0.1561), (0.096500002, 0.98299998, 0.1561), (0.65579998, 0.73860002, -0.1561), (0.30450001, 0.93720001, -0.1699), (-0.096500002, 0.98299998, -0.1561), (0.43290001, 0.73860002, -0.51679999), (0.083899997, 0.852, -0.51679999), (-0.2764, 0.85070002, -0.4472), (-0.65579998, 0.73860002, 0.1561), (-0.90509999, 0.3955, 0.1561), (-0.4998, 0.852, -0.1561), (-0.79729998, 0.57920003, -0.1699), (-0.96469998, 0.212, -0.1561), (-0.56870002, 0.63990003, -0.51679999), (-0.78439999, 0.34310001, -0.51679999), (-0.8944, -0.0, -0.4472), (-0.90509999, -0.3955, 0.1561), (-0.65579998, -0.73860002, 0.1561), (-0.96469998, -0.212, -0.1561), (-0.79729998, -0.57920003, -0.1699), (-0.4998, -0.852, -0.1561), (-0.78439999, -0.34310001, -0.51679999), (-0.56870002, -0.63990003, -0.51679999), (-0.2764, -0.85070002, -0.4472), (0.096500002, -0.98299998, 0.1561), (0.4998, -0.852, 0.1561), (-0.096500002, -0.98299998, -0.1561), (0.30450001, -0.93720001, -0.1699), (0.65579998, -0.73860002, -0.1561), (0.083899997, -0.852, -0.51679999), (0.43290001, -0.73860002, -0.51679999), (0.79729998, 0.57920003, 0.1699), (-0.30450001, 0.93720001, 0.1699), (-0.98549998, -0.0, 0.1699), (-0.30450001, -0.93720001, 0.1699), (0.79729998, -0.57920003, 0.1699), (0.0, 0.0, -1.0), (-0.1115, 0.34310001, -0.93269998), (0.29179999, 0.212, -0.93269998), (-0.2079, 0.63990003, -0.73970002), (0.1832, 0.56370002, -0.80540001), (0.54439998, 0.3955, -0.73970002), (-0.36070001, -0.0, -0.93269998), (-0.67290002, -0.0, -0.73970002), (-0.4795, 0.3484, -0.80540001), (-0.1115, -0.34310001, -0.93269998), (-0.2079, -0.63990003, -0.73970002), (-0.4795, -0.3484, -0.80540001), (0.29179999, -0.212, -0.93269998), (0.54439998, -0.3955, -0.73970002), (0.1832, -0.56370002, -0.80540001), (0.5927, 0.0, -0.80540001)], dtype=np.float64)


def decode_static_lighting(payload, hdr_scale):
    if not np.isfinite(hdr_scale) or hdr_scale < 0:
        raise ValueError('Invalid Reach lighting HDR scale')
    count = len(payload) // 6
    if any(value != 0xcd for value in payload[count * 6:]):
        raise ValueError('Unexpected Reach lighting padding')
    values = np.frombuffer(payload[:count * 6], dtype=np.uint8).reshape(count, 6)
    indices = values[:, 0] & 127
    if np.any(indices >= len(DIRECTIONS)):
        raise ValueError('Reach lighting direction outside table')
    mask = ((values[:, 0] >> 7) | ((values[:, 1] & 1) << 1)).astype(float) / 3
    indirect = np.stack(((values[:, 1] >> 1) & 31,
                         ((values[:, 1] >> 6) & 3) | ((values[:, 2] & 7) << 2),
                         (values[:, 2] >> 3) & 31), axis=1).astype(float)
    indirect = (indirect / 31) ** 2 * hdr_scale
    direct = (values[:, 3:6].astype(float) / 255) ** 2 * hdr_scale
    return {'direction': DIRECTIONS[indices], 'analytical_mask': mask,
            'direct_color': direct, 'indirect_color': indirect}


def lighting_coefficients(decoded):
    """Convert decoded static VMF probes to intensity plus four linear SH terms.

    Follows TagTool VmfConversion and QudraticToLinearAndIntensity. Preserve
    signed coefficients; target RGBE quantization is deliberately separate.
    """
    def basis(direction):
        x,y,z=direction.T
        return np.stack((np.full(len(x),.28209479177387814),
            -.4886025119029199*y,.4886025119029199*z,-.4886025119029199*x,
            1.0925484305920792*x*y,-1.0925484305920792*y*z,
            -.31539156525252005*(x*x+y*y-2*z*z),
            -1.0925484305920792*x*z,.5462742152960396*(x*x-y*y)),axis=1)
    k=(56.976875-56)**(-.93375814)*55.384312-.81427675
    coth=1/np.tanh(k)
    bands=np.array([1,(coth*k-1)/k,(3+k*k-3*k*coth)/(k*k)])
    sh=basis(decoded['direction'])[:,:,None]*bands[[0,1,1,1,2,2,2,2,2]][None,:,None]*decoded['direct_color'][:,None,:]
    sh[:,0,:]+=.28209479177387814*decoded['indirect_color']
    weighted=sh@np.array([.212656,.715158,.0721856])
    dominant=np.stack((-weighted[:,3],-weighted[:,1],weighted[:,2]),axis=1)
    length=np.linalg.norm(dominant,axis=1)
    dominant=np.divide(dominant,length[:,None],out=np.zeros_like(dominant),where=length[:,None]>0)
    direction_basis=basis(dominant)
    intensity=np.einsum('ni,nic->nc',direction_basis,sh)
    denominator=np.sum(direction_basis**2,axis=1)
    intensity=np.divide(intensity,denominator[:,None],out=intensity,where=denominator[:,None]>=.0001)
    result=np.concatenate((intensity[:,None,:],sh[:,:4,:]),axis=1)
    if not np.all(np.isfinite(result)):
        raise ValueError('Nonfinite converted Reach lighting')
    return result


def pack_lighting_coefficients(coefficients):
    """Encode five signed RGBE vectors as Xbox H3's 20-byte ABGR record.

    Quarter-stop shared exponent and signed mantissas follow TagTool
    ColorConversion.ToRgbe/EncodePixel32 for Halo3Retail Original. Explicitly
    reject exponent overflow rather than silently clipping authored lighting.
    """
    colors=np.asarray(coefficients,dtype=np.float32)
    if colors.ndim!=3 or colors.shape[1:]!=(5,3) or not np.all(np.isfinite(colors)):
        raise ValueError('Expected finite Nx5x3 lighting coefficients')
    absolute=np.abs(colors).reshape(-1,3)
    maximum=np.max(absolute,axis=1)
    active=maximum>np.float32(1e-32)
    exponent=(np.frexp(maximum)[1]*4).astype(np.int32)
    power=np.exp2(exponent.astype(np.float32)/4).astype(np.float32)
    quarter=np.float32(0.5**0.25)
    power*=quarter
    for _ in range(8):
        reduce=active & (power>=maximum)
        if not np.any(reduce):break
        exponent[reduce]-=1
        power[reduce]*=quarter
    else:raise ValueError('RGBE exponent search failed')
    if np.any(active & ((exponent < -127) | (exponent > 128))):
        raise ValueError('Lighting exceeds native RGBE exponent range')
    scale=np.float32(127)/np.exp2(exponent.astype(np.float32)/4).astype(np.float32)
    magnitude=np.clip(absolute*scale[:,None],0,127)
    signed=magnitude*np.sign(colors.reshape(-1,3))
    mantissa=np.floor(signed+np.float32(.5)).astype(np.int16)
    mantissa[~active]=0
    exponent[~active]=-127
    result=np.empty((len(maximum),4),dtype=np.uint8)
    result[:,0]=(exponent&255).astype(np.uint8)
    result[:,1:]=(mantissa[:,::-1]&255).astype(np.uint8)
    return result.tobytes()


def resource_lighting_bindings(cache, lighting_offset):
    """Resolve Lbsp HDR scales and cluster prefixes for each lighting buffer."""
    rows=cache.block(lighting_offset+0x48,4)
    bindings={}
    by_row=[]
    for at in rows:
        index,hdr=cache.unpack('he',at)
        by_row.append(index)
        if index==-1:continue
        if index<0 or not np.isfinite(hdr) or hdr<0:
            raise ValueError('Invalid Reach lighting binding')
        entry={'hdr_scale':hdr,'prefix_vertices':0}
        if index in bindings and bindings[index]!=entry:
            raise ValueError('Conflicting HDR scales for one lighting buffer')
        bindings[index]=entry
    prefixes={}
    for at in cache.block(lighting_offset+0x54,8):
        image,row,prefix=cache.unpack('hhi',at)
        if row==-1:continue
        if not 0<=row<len(by_row) or prefix<0:
            raise ValueError('Invalid Reach cluster lighting binding')
        index=by_row[row]
        if index==-1:
            if prefix:raise ValueError('Lighting prefix without a buffer')
            continue
        if index in prefixes and prefixes[index]!=prefix:
            raise ValueError('Conflicting cluster prefixes for shared lighting buffer')
        prefixes[index]=prefix
        bindings[index]['prefix_vertices']=prefix
    return bindings


def convert_lighting_tables(cache, lighting_offset, converted_resource, cluster_sources=None):
    """Build native static/cluster bindings after VMF resource conversion.

    Native layouts follow ScenarioLightmapBspData.cs: empty 12-byte runtime
    block plus int32 buffer index; cluster records contain two int16 indices.
    HDR is already baked into the converted SH stream. Reach cluster prefixes
    are already materialized in that stream by convert_render_resource.
    Instance references are preserved. Reach-only analytical fields are returned
    separately for the caller; they are not silently treated as native fields.
    cluster_sources optionally maps each output cluster to its source cluster.
    Split meshes must retain original vertex indices and lightmap coordinates;
    this remaps bindings only, without copying lighting streams or atlas images.
    """
    import struct
    bindings = resource_lighting_bindings(cache, lighting_offset)
    fixups = dict(converted_resource['fixups'])
    control = converted_resource['control']
    table = fixups[28] & 0x1fffffff
    indices = []
    static = bytearray()
    for at in cache.block(lighting_offset + 0x48, 4):
        index = cache.unpack('h', at)[0]
        if index != -1:
            if index not in bindings or index >= converted_resource['vertex_buffers']:
                raise ValueError('Lighting buffer absent from converted resource')
            descriptor = fixups[table + index * 12] & 0x1fffffff
            count, fmt, stride, size = struct.unpack_from('>IHHI', control, descriptor)
            if fmt != 6 or stride != 20 or size != count * 20:
                raise ValueError('Lighting table requires converted native SH vertices')
            if count < bindings[index]['prefix_vertices']:
                raise ValueError('Converted lighting stream lacks cluster prefix')
        indices.append(index)
        static.extend(bytes(12) + struct.pack('>i', index))
    clusters = bytearray()
    for at in cache.block(lighting_offset + 0x54, 8):
        image, row, prefix = cache.unpack('hhi', at)
        if row != -1:
            if not 0 <= row < len(indices):
                raise ValueError('Cluster references absent lighting row')
            expected_prefix = 0 if indices[row] == -1 else bindings[indices[row]]['prefix_vertices']
            if prefix != expected_prefix:
                raise ValueError('Cluster prefix differs from converted stream')
        elif prefix:
            raise ValueError('Unbound cluster has lighting prefix')
        clusters.extend(struct.pack('>hh', image, row))
    if cluster_sources is not None:
        source_clusters = bytes(clusters)
        source_count = len(source_clusters) // 4
        cluster_sources = list(cluster_sources)
        if any(type(i) is not int or not 0 <= i < source_count for i in cluster_sources):
            raise ValueError('Output cluster references absent source lighting')
        if set(cluster_sources) != set(range(source_count)):
            raise ValueError('Cluster split must retain every source lighting binding')
        clusters = bytearray().join(source_clusters[i*4:i*4+4] for i in cluster_sources)
    probe_count = len(cache.block(lighting_offset + 0x6c, 36))
    instances = bytearray()
    analytical = bytearray()
    for at in cache.block(lighting_offset + 0x60, 12):
        image, row, probe, padding, light = cache.unpack('hhhhI', at)
        if image not in (-1, 0):
            raise ValueError('Instance references an unsupported lightmap image')
        if row != -1 and not 0 <= row < len(indices):
            raise ValueError('Instance references absent static lighting row')
        if probe != -1 and not 0 <= probe < probe_count:
            raise ValueError('Instance references absent light probe')
        if padding:
            raise ValueError('Nonempty Reach instance lighting padding')
        instances.extend(struct.pack('>hhhh', image, row, probe, 0))
        analytical.extend(struct.pack('>I', light))
    return {'static': bytes(static), 'clusters': bytes(clusters),
            'instances': bytes(instances), 'instance_analytical': bytes(analytical),
            'static_count': len(indices), 'cluster_count': len(clusters) // 4,
            'instance_count': len(instances) // 8, 'instance_probe_count': probe_count}


def install_lighting_tables(root, tables, probes, allocate):
    """Link converted tables/probes into an original H3 BSP lighting record.

    Atlas, geometry and header fields are owned by the enclosing importer.
    Return Reach analytical selections explicitly for its separate adaptation.
    Allocation failure invalidates the enclosing build.
    """
    import struct
    if not isinstance(root, bytearray) or len(root) != 0x1b4:
        raise ValueError('Expected native BSP lighting record')
    if any(root[0x100:0x130]):
        raise ValueError('Lighting tables already populated')
    rows = [(0x100, tables['static'], 16, tables['static_count']),
            (0x10c, tables['clusters'], 4, tables['cluster_count']),
            (0x118, tables['instances'], 8, tables['instance_count']),
            (0x124, probes, 72, tables['instance_probe_count'])]
    for _, payload, stride, count in rows:
        if count < 0 or len(payload) != stride * count:
            raise ValueError('Native lighting table length mismatch')
    analytical = tables['instance_analytical']
    if len(analytical) != tables['instance_count'] * 4:
        raise ValueError('Missing instance analytical selections')
    for at in range(0, len(tables['clusters']), 4):
        image, row = struct.unpack_from('>hh', tables['clusters'], at)
        if image not in (-1, 0) or not -1 <= row < tables['static_count']:
            raise ValueError('Invalid native cluster lighting reference')
    for at in range(0, len(tables['instances']), 8):
        image, row, probe, padding = struct.unpack_from('>hhhh', tables['instances'], at)
        if (image not in (-1, 0) or not -1 <= row < tables['static_count']
                or not -1 <= probe < tables['instance_probe_count'] or padding):
            raise ValueError('Invalid native instance lighting reference')
    for at in range(0, len(probes), 72):
        values = struct.unpack_from('>36H', probes, at)
        if any(v & 0x7c00 == 0x7c00 for v in values) or any(values[i] for i in (3, 7, 35)):
            raise ValueError('Invalid native instance probe')
    for offset, payload, stride, count in rows:
        struct.pack_into('>III', root, offset, count, allocate(payload) if count else 0, 0)
    return analytical
