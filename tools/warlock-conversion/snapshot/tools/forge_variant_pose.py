"""Translate Reach Forge poses to Halo 3's different packed orientation format.

Both caches use Z-up world coordinates. Reach's cube-face packing and angle
quantizer differ from H3; copying the packed integers rotates buildings.
"""
import math


def normalize(vector):
    length = math.sqrt(sum(x*x for x in vector))
    if not math.isfinite(length) or length < 1e-8:
        raise ValueError('Invalid orientation vector')
    return tuple(x / length for x in vector)


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def seed(up):
    x, y, z = up
    return normalize((z, 0, -x) if abs(y) <= abs(x) else (0, z, -y))


def rotate(up, angle):
    forward = seed(up)
    left = cross(up, forward)
    return normalize(tuple(a*math.cos(angle)+b*math.sin(angle) for a, b in zip(forward, left)))


def reach_axes(obj):
    if obj['global_up']:
        up = (0., 0., 1.)
    else:
        # 20-bit Reach encoding: six faces, two base-417 coordinates per face.
        face_span = sum(1 << bit for bit in range(1, 19, 2))
        count = math.isqrt(face_span)-1
        face, remainder = divmod(obj['up_quantized'], face_span)
        if face > 5:
            raise ValueError('Invalid Reach unit-vector face')
        a, b = divmod(remainder, count)
        a, b = (-1 + 2*(v + .5)/(count - 1) for v in (a, b))
        vector = [a, b]
        vector.insert(face % 3, 1 if face < 3 else -1)
        up = normalize(vector)
    angle = -math.pi + 2*math.pi*(obj['angle_quantized']+.5)/16384
    return rotate(up, angle), up


def h3_up(packed):
    face = packed & 7
    if face > 5:
        raise ValueError('Invalid H3 unit-vector face')
    components = [max(-1., min(1., q/127-1)) for q in ((packed >> 3) & 255, (packed >> 11) & 255)]
    components.insert(face % 3, 1 if face < 3 else -1)
    return normalize(components)


def h3_axes(obj):
    up = (0., 0., 1.) if obj['global_up'] else h3_up(obj['up_q'])
    return rotate(up, -math.pi + 2*math.pi*min(254, obj['angle_q'])/254), up


def encode_pose(position, forward, up, bounds):
    forward, up = normalize(forward), normalize(up)
    if abs(sum(a*b for a, b in zip(forward, up))) > 1e-4:
        raise ValueError('Forward/up axes are not perpendicular')
    result = {}
    for axis, value in zip('xyz', position):
        lower, upper = bounds[axis+'min'], bounds[axis+'max']
        if not math.isfinite(value) or not lower <= value <= upper or upper <= lower:
            raise ValueError('Placement outside destination bounds')
        result[axis+'_q'] = min(65535, math.floor((value-lower)/(upper-lower)*65535+.5))
    result['global_up'] = int(max(abs(a-b) for a,b in zip(up,(0,0,1))) < 1e-4)
    if not result['global_up']:
        # Tie preference is Z, then Y, then X, as in the native H3 writer.
        major = max(range(3), key=lambda k: (abs(up[k]), k))
        components = [up[k]/abs(up[major]) for k in range(3) if k != major]
        a, b = (min(254, max(0, math.floor((v+1)*127+.5))) for v in components)
        result['up_q'] = major + (3 if up[major] < 0 else 0) | a << 3 | b << 11
        up = h3_up(result['up_q'])
    basis = seed(up)
    left = normalize(cross(up, basis))
    angle = math.atan2(sum(a*b for a,b in zip(forward,left)), sum(a*b for a,b in zip(forward,basis)))
    result['angle_q'] = min(254, max(0, math.floor((angle+math.pi)/(2*math.pi)*254+.5)))
    return result
