# -*- coding: utf-8 -*-
import maya.cmds as cmds
import maya.api.OpenMaya as om2
from time import time


kShort_flag_base_weight = '-bw'
kLong_flag_base_weight = '-baseWeight'


def maya_useNewAPI():
    pass


class HTM_TransferVertexNormals(om2.MPxCommand):
    kPluginCmdName = 'HTM_TransferVertexNormals'

    def __init__(self):
        om2.MPxCommand.__init__(self)
        self.sel = om2.MSelectionList # Undo用の対象メッシュ情報

    @staticmethod
    def cmdCreator():
        return HTM_TransferVertexNormals()

    def doIt(self, args):
        self.parseArguments(args)
        self.redoIt()

    def redoIt(self):
        # シンメトリを切る、ソフト選択のウェイトが正しく取得できないので
        if cmds.symmetricModelling(q=True, symmetry=True):
            cmds.symmetricModelling(symmetry=False)

        # ソフト選択モードがONかどうか
        soft_sel_state = cmds.softSelect(q=True, sse=True) # 0=NotActive, 1=Active

        # 最初に選択したものをソースにする
        rich_sel = om2.MGlobal.getRichSelection()

        self.sel = rich_sel.getSelection()
        it_sel = om2.MItSelectionList(self.sel)

        self.orig_info = [] # Undo用

        sta = time()
        for i, sel in enumerate(it_sel):
            dag, comp = sel.getComponent()

            # 転送元処理
            if i == 0:
                # ソースに関して、コンポーネント選択したい状況がまず考えられないので
                if sel.hasComponents():
                    om2.MGlobal.displayError(u'ソースオブジェクトはオブジェクトとして選択してください')

                fn_mesh_src = om2.MFnMesh(dag)
                continue

            # 転送先処理
            else:
                fn_mesh_dst = om2.MFnMesh(dag)
                num_vtx = fn_mesh_dst.numVertices

                # ------------------------------------------------------------
                # Undo用情報取得
                normals = fn_mesh_dst.getNormals(om2.MSpace.kWorld)
                lock_state = []
                for i in range(len(normals)):
                    state = fn_mesh_dst.isNormalLocked(i)
                    lock_state.append(state)

                it_face_vtx = om2.MItMeshFaceVertex(dag)
                new_normals = om2.MVectorArray()
                faces_locked = []
                vtxs_locked = []
                for face_vtx in it_face_vtx:
                    nrm_id = face_vtx.normalId()
                    if lock_state[nrm_id] == True:
                        # 法線がロックされている頂点フェースとその法線を取得
                        faces_locked.append(face_vtx.faceId())
                        vtxs_locked.append(face_vtx.vertexId())
                        new_normals.append(normals[nrm_id])

                # ソフトエッジ・ハードエッジの情報
                edge_smoothing = [fn_mesh_dst.isEdgeSmooth(id) for id in range(fn_mesh_dst.numEdges)]
                edge_ids = [id for id in range(fn_mesh_dst.numEdges)]

                self.orig_info.append({'normals':new_normals, 'faces_locked':faces_locked, 'vtxs_locked':vtxs_locked,
                                       'edge_ids':edge_ids, 'edge_smoothing':edge_smoothing})

                # ------------------------------------------------------------
                # 転送処理
                normal_edit = fn_mesh_dst.getVertexNormals(False, om2.MSpace.kWorld) # 編集用法線

                # コンポーネント選択かどうかで処理を分岐させる
                if sel.hasComponents():
                    dst_fn_comp = om2.MFnSingleIndexedComponent(comp)

                    for j, vtx_id in enumerate(dst_fn_comp.getElements()):
                        if soft_sel_state == 1:
                            if self.base_weight == 1.0:
                                # ベースのウェイトが1.0ならself.base_weightをかける処理は省略できる
                                weight = dst_fn_comp.weight(j).influence
                            else:
                                weight = dst_fn_comp.weight(j).influence * self.base_weight
                        else:
                            # ソフト選択がOFFなら各コンポーネントのウェイトを考えなくていい
                            weight = self.base_weight


                        pos = fn_mesh_dst.getPoint(vtx_id, om2.MSpace.kWorld)
                        normal_edit[vtx_id] = normal_edit[vtx_id] * (1.0 - weight) + weight *\
                                              om2.MFloatVector(fn_mesh_src.getClosestNormal(pos, om2.MSpace.kWorld)[0])

                else:
                    # オブジェクト選択の場合
                    points = fn_mesh_dst.getPoints(om2.MSpace.kWorld)

                    if self.base_weight == 1.0:
                        for j, pos in enumerate(points):
                            normal_edit[j] = fn_mesh_src.getClosestNormal(pos, om2.MSpace.kWorld)[0]
                    else:
                        for j, pos in enumerate(points):
                            normal_edit[j] = normal_edit[j] * (1.0 - self.base_weight) + self.base_weight * \
                                             om2.MFloatVector(fn_mesh_src.getClosestNormal(pos, om2.MSpace.kWorld)[0])
                            
            # 法線転送
            fn_mesh_dst.setVertexNormals(normal_edit, range(num_vtx), om2.MSpace.kWorld)

            end = time()
            print(f'# HTM_TransferVertexNormals : {end - sta:.3f} sec')

    def undoIt(self):
        it_sel = om2.MItSelectionList(self.sel)

        for i, sel in enumerate(it_sel):
            # ソースオブジェクトはスルー
            if i == 0: continue

            # ターゲットのUndo処理
            dag = sel.getDagPath()
            fn_mesh = om2.MFnMesh(dag)

            fn_mesh.unlockVertexNormals(range(fn_mesh.numVertices))
            fn_mesh.setFaceVertexNormals(self.orig_info[i-1]['normals'],
                                         self.orig_info[i-1]['faces_locked'],
                                         self.orig_info[i-1]['vtxs_locked'],
                                         om2.MSpace.kWorld)
            
            fn_mesh.setEdgeSmoothings(self.orig_info[i-1]['edge_ids'],
                                      self.orig_info[i-1]['edge_smoothing'])
            
            fn_mesh.updateSurface()

    def parseArguments(self, args):
        arg_data = om2.MArgDatabase(self.syntax(), args)

        if arg_data.isFlagSet(kShort_flag_base_weight):
            self.base_weight = arg_data.flagArgumentFloat(kShort_flag_base_weight, 0)

    def isUndoable(self):
        return True

    @staticmethod
    def syntaxCreator():
        """
        Args:
            baseWeight(bw): float
        """
        syntax = om2.MSyntax()
        syntax.addFlag(kShort_flag_base_weight, kLong_flag_base_weight, om2.MSyntax.kLong) # kLong == int
        return syntax


def initializePlugin(mobject):
    plugin = om2.MFnPlugin(mobject)
    plugin.registerCommand(HTM_TransferVertexNormals.kPluginCmdName,
                           HTM_TransferVertexNormals.cmdCreator,
                           HTM_TransferVertexNormals.syntaxCreator)


def uninitializePlugin(mobject):
    pluginFn = om2.MFnPlugin(mobject)
    pluginFn.deregisterCommand(HTM_TransferVertexNormals.kPluginCmdName)
