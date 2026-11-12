"""Reach instance basis -> H3 scenario Euler angles, with float32 readback.

Axis convention follows retained TagTool MapVariantGenerator's
Vectors3dFromEulerAngles, not generic graphics-library Euler defaults.
"""
import math
import struct
import numpy as np


def axes_from_angles(yaw,pitch,roll):
    sy,sp,sr=map(math.sin,(yaw,pitch,roll));cy,cp,cr=map(math.cos,(yaw,pitch,roll))
    forward=(cy*cp,sy*cr-sp*sr*cy,sp*cr*cy+sy*sr)
    up=(-sp,-cp*sr,cp*cr)
    left=tuple(np.cross(up,forward))
    return (*forward,*left,*up)


def placement_angles(matrix,scale):
    if len(matrix)!=12 or not all(math.isfinite(x) for x in (*matrix,scale)) or scale<=0:
        raise ValueError('Invalid instance pose')
    axes=np.asarray(matrix[:9],dtype=float).reshape(3,3)
    if not np.allclose(axes@axes.T,np.eye(3),rtol=0,atol=2e-5) or np.linalg.det(axes)<=0:
        raise ValueError('Instance pose has shear or reflection')
    # Independently rounded source axes are slightly nonorthogonal. Near a
    # gimbal pole that error destabilizes separate yaw/roll extraction. Project
    # onto the closest proper rotation before inversion; the final comparison
    # remains against the original source basis, not the projected one.
    u,_,vt=np.linalg.svd(axes)
    f,left,up=u@vt
    pitch=math.atan2(-up[0],math.hypot(up[1],up[2]))
    if math.hypot(up[1],up[2])>1e-6:
        yaw=math.atan2(-left[0],f[0]);roll=math.atan2(-up[1],up[2])
    else:
        roll=0.;yaw=math.atan2(f[1],math.sin(pitch)*f[2])
    angles=struct.unpack('>3f',struct.pack('>3f',yaw,pitch,roll))
    if max(abs(a-b) for a,b in zip(axes_from_angles(*angles),matrix[:9]))>2e-5:
        raise ValueError('Native Euler pose does not reproduce Reach basis')
    return angles
