# -*- coding: utf-8 -*-
import maya.api.OpenMaya as om2


def maya_useNewAPI():
    pass

class HTM_SmoothVertexNormals(om2.MPxCommand):
    """ 頂点法線のスムース処理 """

    kPluginCmdName = 'HTM_SmoothVertexNormals'

    def __init__(self):
        om2.MPxCommand.__init__(self)

    def doIt(self, args):
        self.parseArgument(args)
        self.redoIt()

    def redoIt(self):
        dag, comp = self.sel.getComponent(0)
        self.fn_mesh = om2.MFnMesh(dag)
        it_vtx = om2.MItMeshVertex(dag)

        # ------------------------------------------------------------
        # Undo用情報取得
        normals = self.fn_mesh.getNormals()
        lock_state = []
        for i in range(len(normals)):
            state = self.fn_mesh.isNormalLocked(i)
            lock_state.append(state)

        it_face_vtx = om2.MItMeshFaceVertex(dag)
        self.new_normals = []
        self.lock_faces = []
        self.lock_vtxs = []
        for face_vtx in it_face_vtx:
            nrm_id = face_vtx.normalId()
            if lock_state[nrm_id] == True:
                # 法線がロックされている頂点フェースとその法線を取得
                self.lock_faces.append(face_vtx.faceId())
                self.lock_vtxs.append(face_vtx.vertexId())
                self.new_normals.append(normals[nrm_id])
        self.new_normals = [om2.MVector(n) for n in self.new_normals]

        # ソフトエッジ・ハードエッジの情報
        self.edge_smoothing = [self.fn_mesh.isEdgeSmooth(id) for id in range(self.fn_mesh.numEdges)]
        self.edge_ids = [id for id in range(self.fn_mesh.numEdges)]

        # ------------------------------------------------------------
        # スムース処理、頂点フェース法線ではなく頂点法線で処理する
        all_normals = [iv.getNormals() for iv in it_vtx]
        vtx_normals = om2.MVectorArray([om2.MVector(0,0,0)] * self.fn_mesh.numVertices)
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
        
        self.fn_mesh.setVertexNormals(new_normals, vtx_ids)

    def undoIt(self):
        self.fn_mesh.unlockVertexNormals(range(self.fn_mesh.numVertices))
        self.fn_mesh.setFaceVertexNormals(self.new_normals, self.lock_faces, self.lock_vtxs)
        self.fn_mesh.setEdgeSmoothings(self.edge_ids, self.edge_smoothing)
        self.fn_mesh.updateSurface()

    def isUndoable(self):
        return True

    def parseArgument(self, args):     
        arg_data = om2.MArgDatabase(self.syntax(), args)
        self.sel = arg_data.getObjectList() # MSelectionListとして取得

    @staticmethod
    def cmdCreator():
        return HTM_SmoothVertexNormals()

    @staticmethod
    def syntaxCreator():
        """ コマンドの引数設定、オブジェクトをMSelectionListとして取得するだけ """
        syntax = om2.MSyntax()
        syntax.useSelectionAsDefault(True)
        syntax.setObjectType(om2.MSyntax.kSelectionList)
        return syntax


def initializePlugin(mobject):
    mplugin = om2.MFnPlugin(mobject)
    try:
        mplugin.registerCommand(HTM_SmoothVertexNormals.kPluginCmdName, 
                                HTM_SmoothVertexNormals.cmdCreator,
                                HTM_SmoothVertexNormals.syntaxCreator)
    except:
        om2.MGlobal.displayError('Failed to register command:' + kPluginCmdName)


def uninitializePlugin(mobject):
    mplugin = om2.MFnPlugin(mobject)
    try:
        mplugin.deregisterCommand(HTM_SmoothVertexNormals.kPluginCmdName)
    except:
        om2.MGlobal.displayError('Failed to unregister command:' + kPluginCmdName)