# -*- coding: utf-8 -*-
import maya.cmds as cmds
import maya.api.OpenMaya as om2
import time

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

