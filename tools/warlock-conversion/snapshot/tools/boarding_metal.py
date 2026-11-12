"""Scoped MCC PBR control conversion to original H3 Cook–Torrance.

Keep sampled specular/roughness data instead of dropping the control map.
Normalize the environment control channel and fold its constant multiplier
into the native environment tint, avoiding clipping a value of eight to one.
"""
import numpy as np

def prepare(source, tag, tint_tag, blend, environment):
    c = source.c
    info = source.info(tag)
    row = c.block(c.tags[tag]['offset'] + 96, 56)[0]
    curve = c.data[row + 21]
    if len(info) != 1 or info[0]['format'] != 11 or curve not in (1,3,5):
        raise ValueError('Boarding metal requires an ARGB control map with known color curve')
    if not 0 <= blend <= 1 or not np.isfinite(environment) or environment < 0:
        raise ValueError('Invalid Boarding metal control constants')
    tint_info = source.info(tint_tag)
    tr = c.block(c.tags[tint_tag]['offset'] + 96, 56)[0]
    if len(tint_info) != 1 or (tint_info[0]['width'], tint_info[0]['height'], tint_info[0]['format']) != (1, 1, 11) or c.data[tr+21] != 3:
        raise ValueError('Boarding metal specular tint must be constant linear ARGB')
    tint = source.pixels(tint_tag)
    if len(tint) != 4:
        raise ValueError('Unexpected Boarding metal tint data')
    raw = source.pixels(tag)
    pixels = np.frombuffer(raw, np.uint8).reshape(-1, 4)
    sampled = pixels[:,[2,1]].astype(np.float64)/255.
    if curve in (1,5):
        sampled = np.where(sampled<=.04045,sampled/12.92,((sampled+.055)/1.055)**2.4)
    controls = np.rint(sampled*255).astype(np.uint8)
    output = np.empty_like(pixels)
    output[:,0] = 255              # normalized environment contribution
    output[:,1] = round(blend*255) # albedo blend
    output[:,2] = controls[:,0]    # decoded source specular coefficient R
    output[:,3] = controls[:,1]    # decoded source roughness G
    error = float(np.max(np.abs(controls.astype(np.float64)/255-sampled)))
    if error > .5/255 + 1e-12:
        raise ValueError('Control-map quantization exceeded half a linear byte')
    class Baked:
        def info(self, unused):
            return [dict(info[0], kind=0, curve=3)]
        def pixels(self, unused, index=0):
            return output.tobytes()
    Baked.c = c
    return Baked(), dict(environment_scale=environment,
                        specular_tint=[tint[2-j]/255. for j in range(3)],
                        blend_quantization_error=abs(round(blend*255)/255-blend),
                        control_quantization_error=error,source_curve=curve,
                        source_control_bytes=len(raw))
