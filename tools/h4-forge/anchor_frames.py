"""Adapt original H4 anchor data to measured Reach authoring coordinates."""
import math

def profile_point(position, rotation, profile):
    """Map reviewed rectangular marker roles onto a convex X/Z extrusion.

    This is offline model-data adaptation. The original H4 runtime still
    selects and aligns these markers exactly as it does every other marker.
    """
    roles=[]
    for value,levels,tolerance in zip(position,profile['source_levels'],profile['source_tolerance']):
        index=min(range(len(levels)),key=lambda i:abs(levels[i]-value))
        if abs(levels[index]-value)>tolerance:
            raise ValueError('Marker does not match the reviewed extrusion role')
        roles.append(index)
    z=profile['target_z'][roles[2]];polygon=profile['polygon_xz'];intersections=[]
    for a,b in zip(polygon,polygon[1:]+polygon[:1]):
        dx,dz=b[0]-a[0],b[1]-a[1]
        if abs(dz)<1e-10 or not min(a[1],b[1])-1e-8<=z<=max(a[1],b[1])+1e-8:continue
        x=a[0]+(z-a[1])*dx/dz;length=math.hypot(dx,dz)
        intersections.append((x,(dz/length,0,-dx/length)))
    if len(intersections)<2:raise ValueError('Extrusion slice lacks two boundaries')
    boundary=min(intersections) if roles[0]==0 else max(intersections)
    x=profile['center_x'] if roles[0]==1 else boundary[0]
    q=list(rotation)
    forward=(1-2*(q[1]*q[1]+q[2]*q[2]),2*(q[0]*q[1]+q[2]*q[3]),2*(q[0]*q[2]-q[1]*q[3]))
    if roles[0]!=1 and abs(abs(forward[0])-1)<1e-6 and abs(forward[1])+abs(forward[2])<1e-6:
        sign=-1 if roles[0]==0 else 1
        if abs(forward[0]-sign)>1e-6:raise ValueError('Unexpected inward extrusion side marker')
        normal=boundary[1];angle=math.atan2(-normal[2]*sign,normal[0]*sign)
        sy,cy=math.sin(angle/2),math.cos(angle/2);qx,qy,qz,qw=q
        q=[cy*qx+sy*qz,cy*qy+sy*qw,cy*qz-sy*qx,cy*qw-sy*qy]
    return [x,profile['target_y'][roles[1]],z],q

def adapt(point, frame):
    p=list(point['position']);x,y,z,w=point['rotation']
    if 'axis_scale' in frame:
        if 'horizontal_scale' in frame:
            raise ValueError('Use only one anchor scaling convention')
        scale=frame['axis_scale']
        if len(scale)!=3 or any(not math.isfinite(v) or v<=0 for v in scale):
            raise ValueError('Anchor axis scales must be finite and positive')
        axes=[(1-2*(y*y+z*z),2*(x*y+z*w),2*(x*z-y*w)),
              (2*(x*y-z*w),1-2*(x*x+z*z),2*(y*z+x*w)),
              (2*(x*z+y*w),2*(y*z-x*w),1-2*(x*x+y*y))]
        # Scaling positions may retain the authored rotation only when every
        # frame axis keeps its direction (e.g. cardinal box-face markers).
        # Reject tilted frames requiring an explicit orientation adaptation.
        for axis in axes:
            scaled=[a*s for a,s in zip(axis,scale)]
            length=math.sqrt(sum(v*v for v in scaled))
            if math.dist(axis,[v/length for v in scaled])>1e-6:
                raise ValueError('Axis scaling changes this anchor orientation')
        p=[v*s for v,s in zip(p,scale)]
    horizontal_scale=frame.get('horizontal_scale',1.)
    if horizontal_scale != 1.:
        # Reviewed Base, Round markers are upright, with horizontal normals.
        # Equal XY scaling preserves those orientations. Reject tilted markers
        # rather than silently treating a nonuniform scale as a rigid transform.
        if horizontal_scale <= 0 or abs(x)>1e-6 or abs(y)>1e-6:
            raise ValueError('Horizontal anchor scaling requires upright markers')
        p[0]*=horizontal_scale;p[1]*=horizontal_scale
    if frame.get('mirror_y'):
        p[1]=-p[1]
        # Conjugate the rotation by the Y reflection. Forward/up reflect;
        # the recomputed left axis keeps a proper right-handed frame.
        x,z=-x,-z
    angle=math.radians(frame['yaw_degrees']);c,s=math.cos(angle),math.sin(angle)
    p=[c*p[0]-s*p[1],s*p[0]+c*p[1],p[2]]
    qz,qw=math.sin(angle/2),math.cos(angle/2)
    q=[qw*x-qz*y,qw*y+qz*x,qw*z+qz*w,qw*w-qz*z]
    p=[v+t for v,t in zip(p,frame['translation'])]
    if 'position_levels' in frame:
        # Some corresponding features have different target heights despite
        # sharing a source coordinate (e.g. separately authored floor panels).
        # Match a complete reviewed source role, never a nearest-point guess.
        if any(key in frame for key in ('axis_levels','coordinate_planes','extrusion_profile','radial_profile')):
            raise ValueError('Full-position roles cannot mix with other position mappings')
        mapping=frame['position_levels'];limit=mapping['tolerance'];levels=mapping['levels']
        if not math.isfinite(limit) or not 0<limit<=.0001 or not 1<=len(levels)<=32:
            raise ValueError('Invalid reviewed position-role mapping')
        for level in levels:
            if any(len(level[key])!=3 or any(not math.isfinite(v) for v in level[key]) for key in ('source','target')):
                raise ValueError('Invalid reviewed position role')
        matches=[level['target'] for level in levels if math.dist(p,level['source'])<=limit]
        if len(matches)!=1:raise ValueError('Marker does not match one reviewed position role')
        p=list(matches[0])
    if 'upright_yaw_levels' in frame:
        # Explicit offline repair for reviewed source frames whose normals
        # differ from the target faces. Do not infer a new runtime snap rule.
        mapping=frame['upright_yaw_levels'];limit=mapping['tolerance_degrees']
        if abs(q[0])+abs(q[1])>1e-6 or not math.isfinite(limit) or not 0<limit<=.0001:
            raise ValueError('Invalid reviewed upright orientation mapping')
        yaw=math.degrees(math.atan2(2*q[2]*q[3],1-2*q[2]*q[2]))
        delta=lambda a,b:(a-b+180)%360-180
        levels=mapping['levels'];maximum=mapping.get('maximum_correction_degrees',5)
        if not math.isfinite(maximum) or not 0<maximum<=45:
            raise ValueError('Invalid reviewed orientation correction bound')
        if not levels or any(len(pair)!=2 or any(not math.isfinite(v) for v in pair) or abs(delta(*pair))>maximum for pair in levels):
            raise ValueError('Invalid reviewed upright orientation levels')
        matches=[target for source,target in levels if abs(delta(yaw,source))<=limit]
        if len(matches)!=1:raise ValueError('Marker does not match one reviewed orientation')
        angle=math.radians(matches[0])/2;q=[0,0,math.sin(angle),math.cos(angle)]
    if 'axis_levels' in frame:
        # Reviewed source construction levels can differ from target levels.
        # Match an explicit source role; never use an unlimited nearest-plane
        # correction to hide a changed model dimension.
        for mapping in frame['axis_levels']:
            axis=mapping['axis'];limit=mapping['tolerance'];levels=mapping['levels']
            if axis not in (0,1,2) or not math.isfinite(limit) or not 0<limit<=.0001:
                raise ValueError('Invalid construction-level mapping')
            if not levels or any(len(pair)!=2 or any(not math.isfinite(v) for v in pair) for pair in levels):
                raise ValueError('Invalid construction levels')
            matches=[target for source,target in levels if abs(p[axis]-source)<=limit]
            if len(matches)!=1:raise ValueError('Marker does not match one reviewed construction level')
            p[axis]=matches[0]
    if 'coordinate_planes' in frame:
        # Offline authoring-data repair for reviewed construction roles only.
        # Project original, slightly noisy markers onto measured face/center
        # planes. This never participates in the game's object snap algorithm.
        planes=frame['coordinate_planes'];limit=frame['coordinate_tolerance']
        if len(planes)!=3 or not math.isfinite(limit) or not 0<limit<=.01:
            raise ValueError('Invalid reviewed coordinate-plane projection')
        for i,values in enumerate(planes):
            if not values or any(not math.isfinite(v) for v in values):
                raise ValueError('Invalid construction planes')
            nearest=min(values,key=lambda v:abs(v-p[i]))
            if abs(nearest-p[i])>limit:
                raise ValueError('Authored anchor exceeds reviewed plane correction tolerance')
            p[i]=nearest
    if 'extrusion_profile' in frame:
        p,q=profile_point(p,q,frame['extrusion_profile'])
    if 'radial_profile' in frame:
        radius=math.hypot(p[0],p[1]);profile=frame['radial_profile']
        matches=[level for level in profile['levels'] if abs(radius-level['source_radius'])<profile['tolerance'] and abs(p[2]-level['source_z'])<profile['tolerance']]
        if len(matches)!=1 or radius<=0:raise ValueError('Marker does not match reviewed radial level')
        scale=matches[0]['target_radius']/radius
        p=[p[0]*scale,p[1]*scale,p[2]]
    return dict(point,position=p,rotation=q)
