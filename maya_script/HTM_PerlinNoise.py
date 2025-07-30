import random
import math

import maya.cmds as mc
import maya.api.OpenMaya as om2


def grad3(pos):
    def fract(x):
        return x % 1.0

    xyz = [pos * om2.MVector(312.2, 541.6, 234.3),
           pos * om2.MVector(117.1, 131.4, 339.1),
           pos * om2.MVector(511.3, 397.3, 113.2)]

    x = 2.0 * fract(math.sin(xyz[0]) * 62145.2137913) - 1.0
    y = 2.0 * fract(math.sin(xyz[1]) * 62145.2137913) - 1.0
    z = 2.0 * fract(math.sin(xyz[2]) * 62145.2137913) - 1.0

    return om2.MVector([x, y, z])


def floor(pos):
    x = math.floor(pos.x)
    y = math.floor(pos.y)
    z = math.floor(pos.z)

    return om2.MVector([x, y, z])

def fract(pos):
    x = pos.x % 1.0
    y = pos.y % 1.0
    z = pos.z % 1.0

    return om2.MVector([x, y, z])

def lerp(x, y, t):
    return (y - x) * (3 - t * 2) * t * t + x
    #return x * t + (1 - t) * y

def perlin_noise(pos):
    pos_floor = floor(pos)
    pos_fract = fract(pos)

    # front, back, top, bottom, right, left
    p_bbl = pos_floor + om2.MVector([0, 0, 0])
    p_bbr = pos_floor + om2.MVector([1, 0, 0])
    p_btl = pos_floor + om2.MVector([0, 1, 0])
    p_btr = pos_floor + om2.MVector([1, 1, 0])
    p_fbl = pos_floor + om2.MVector([0, 0, 1])
    p_fbr = pos_floor + om2.MVector([1, 0, 1])
    p_ftl = pos_floor + om2.MVector([0, 1, 1])
    p_ftr = pos_floor + om2.MVector([1, 1, 1])

    # gradient
    grad_bbl = grad3(p_bbl)
    grad_bbr = grad3(p_bbr)
    grad_btl = grad3(p_btl)
    grad_btr = grad3(p_btr)
    grad_fbl = grad3(p_fbl)
    grad_fbr = grad3(p_fbr)
    grad_ftl = grad3(p_ftl)
    grad_ftr = grad3(p_ftr)

    # dot value
    val_bbl = grad_bbl * (om2.MPoint(pos) - om2.MPoint(p_bbl))
    val_bbr = grad_bbr * (om2.MPoint(pos) - om2.MPoint(p_bbr))
    val_btl = grad_btl * (om2.MPoint(pos) - om2.MPoint(p_btl))
    val_btr = grad_btr * (om2.MPoint(pos) - om2.MPoint(p_btr))
    val_fbl = grad_fbl * (om2.MPoint(pos) - om2.MPoint(p_fbl))
    val_fbr = grad_fbr * (om2.MPoint(pos) - om2.MPoint(p_fbr))
    val_ftl = grad_ftl * (om2.MPoint(pos) - om2.MPoint(p_ftl))
    val_ftr = grad_ftr * (om2.MPoint(pos) - om2.MPoint(p_ftr))

    # interpolation
    intp_bb = lerp(val_bbl, val_bbr, pos_fract.x)
    intp_bt = lerp(val_btl, val_btr, pos_fract.x)
    intp_fb = lerp(val_fbl, val_fbr, pos_fract.x)
    intp_ft = lerp(val_ftl, val_ftr, pos_fract.x)

    intp_b = lerp(intp_bb, intp_bt, pos_fract.y)
    intp_f = lerp(intp_fb, intp_ft, pos_fract.y)

    intp = lerp(intp_b, intp_f, pos_fract.z)

    #intp = lerp(intp_bb, intp_fb, pos_fract.z)
    #return intp_b

    return intp * (1.0 / math.sqrt(3/4))


scale = 0.03
offset = 0.0

sel = mc.ls(sl=True)
for s in sel:
    vtxs = mc.ls(s + '.vtx[*]', fl=True)
    for v in vtxs:
        pos = mc.xform(v, q=True, ws=True, t=True)
        pos = om2.MVector(pos) * scale + om2.MVector(offset, offset, offset)
        val = perlin_noise(pos)
        val = (val + 1.0) * 0.5
        color = [val, val, val]
        mc.polyColorPerVertex(v, rgb=color)
