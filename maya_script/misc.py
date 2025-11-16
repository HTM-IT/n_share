# -*- coding: utf-8 -*-
from maya import cmds
import maya.api.OpenMaya as om2
import time
import math


"""
// custom shader code
float3 tangent_vs = cross(Normal, float3(1, 0, 0));
float3 binormal_vs = cross(tangent_vs, Normal);

float x_ts = dot(Half, tangent_vs);
float y_ts = dot(Half, binormal_vs);
float z_ts = dot(Half, Normal);

float theta = atan2(x_ts, y_ts);
float sqrnorm = pow(abs(sin(2.0 * theta)), n);

float x_edit = (1-sigma *  sqrnorm) * x_ts;
float y_edit = (1-sigma * sqrnorm) * y_ts;

float3 half_edit = float3(x_edit, y_edit, z_ts);
half_edit = normalize(half_edit);

float3 half_view = float3(half_edit.x * tangent_vs + half_edit.y * binormal_vs + half_edit.z * Normal);

return half_view;
"""


def nearest_value(x):
    size_preset = [16, 32, 64, 128, 256, 512, 768,
                   1024, 1280, 1536, 1792, 2048]
    return min(size_preset, key=lambda v: abs(v - x))

def calc_tex_size(ppcm=128):
    sel = om2.MGlobal.getActiveSelectionList()
    dag, comp = sel.getComponent(0)
    fn_mesh = om2.MFnMesh(dag)
    it_poly = om2.MItMeshPolygon(dag)
    
    face_area = 0
    uv_area = 0
    for poly in it_poly:
        face_area += poly.getArea()
        uv_area += poly.getUVArea()
    
    tex_size = ppcm * math.sqrt(face_area / uv_area)
    tex_size_rounded = nearest_value(tex_size) 
    
    print('# Face Area : {}'.format(face_area))
    print('# UV Area : {}'.format(uv_area))
    print('# Texture Size : {}'.format(tex_size))
    print('# Texture Size Rounded : {}'.format(tex_size_rounded))
    
if __name__ == '__main__':
    ppcm = 20 # ppcm:pixel per centimeter
    calc_tex_size(ppcm=ppcm)


def change_edge_display():
    """" エッジの表示モード変更 """
    sel = cmds.ls(sl=True, l=True, tr=True)
    disp_type = []
    for s in sel:
        disp_type.append(cmds.getAttr(s + '.displayEdges'))
        
    if disp_type.count(disp_type[0]) == len(disp_type):
        # リストの最初の要素の出現回数がそのリストの長さと同じなら全要素が同じ
        type = disp_type[0]
        type = (type + 1) % 4
        for s in sel:
            cmds.setAttr(s + '.displayEdges', type)
    else:
        for s in sel:
            cmds.setAttr(s + '.displayEdges', 0)

if __name__ == '__main__':
    change_edge_display()


def smooth_vertex_normals():
    start = time.time()
    sel = om2.MGlobal.getActiveSelectionList()
    
    dag, comp = sel.getComponent(0)
    fn_mesh = om2.MFnMesh(dag)
    it_vtx = om2.MItMeshVertex(dag)
    
    all_normals = [iv.getNormals() for iv in it_vtx]
    vtx_normals = om2.MVectorArray([om2.MVector(0,0,0)] * fn_mesh.numVertices)
    for i, normals in enumerate(all_normals):
        for n in normals:
            vtx_normals[i] += n
    
        vtx_normals[i] = vtx_normals[i].normal()
    
    it_vtx = om2.MItMeshVertex(dag, comp)
    vtx_ids = []
    new_normals = []
    for vtx in it_vtx:
        vtx_id = vtx.index()
        connected_vtxs = vtx.getConnectedVertices()
        normal = vtx_normals[vtx_id]
        for connect_vtx in connected_vtxs:
            normal = normal + vtx_normals[connect_vtx]
            
        vtx_ids.append(vtx_id)
        new_normals.append(normal)
    
    fn_mesh.setVertexNormals(new_normals, vtx_ids)
    end = time.time()
    print(end - start)
    
if __name__ == '__main__':
    smooth_vertex_normals()

