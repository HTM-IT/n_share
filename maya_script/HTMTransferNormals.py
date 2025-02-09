# -*- coding: utf-8 -*-
import maya.cmds as mc
import maya.api.OpenMaya as om2
from time import time
from copy import deepcopy

kShort_flag_base_weight = '-bw'
kLong_flag_base_weight = '-baseWeight'


def maya_useNewAPI():
    pass

class HTMTransferNormals(om2.MPxCommand):
    kPluginCmdName = 'HTMTransferNormals'

    def __init__(self):
        om2.MPxCommand.__init__(self)
        self.sel = om2.MSelectionList # Undo用の対象メッシュ情報
        self.normal_orig = []
        self.base_weight = 1.0

    @staticmethod
    def cmdCreator():
        return HTMTransferNormals()

    def doIt(self, args):
        self.parseArguments(args)
        self.redoIt()

    def redoIt(self):
        #self.base_weight = 1.0
        # シンメトリを切る、ソフト選択のウェイトが正しく取得できないので
        if mc.symmetricModelling(q=True, symmetry=True):
            mc.symmetricModelling(symmetry=False)

        # ソフト選択モードがONかどうか
        soft_sel_state = mc.softSelect(q=True, sse=True) # 0=NotActive, 1=Active

        # 最初に選択したものをソースにする
        rich_sel = om2.MGlobal.getRichSelection()

        self.sel = rich_sel.getSelection()
        it_sel = om2.MItSelectionList(self.sel)

        self.orig_info = [] # Undo用

        sta = time()
        for i, sel in enumerate(it_sel):
            # src : 転送元、 dst : 転送先
            dag_path, obj = sel.getComponent()

            # 転送元処理
            if i == 0:
                # ソースに関して、コンポーネント選択したい状況がまず考えられないので
                if sel.hasComponents():
                    om2.MGlobal.displayError(u'ソースオブジェクトはオブジェクトとして選択してください')

                src_fn_mesh = om2.MFnMesh(dag_path)
                continue

            # 転送先処理
            else:
                dst_fn_mesh = om2.MFnMesh(dag_path)
                num_vtx = dst_fn_mesh.numVertices

                # Undo用情報の取得
                # 頂点法線復帰用の情報は「頂点フェース」に関して取って置く必要がある
                # でないとハードエッジ設定されていたものをUndo時に破壊してしまうので
                it_poly = om2.MItMeshPolygon(dag_path)
                normals = om2.MVectorArray()
                connect_vtxs = []
                face_ids = []
                for i, poly in enumerate(it_poly):
                    # 頂点フェースを構成するポイントの取得（頂点ではない）
                    vtx_temp = poly.getVertices()

                    # MfnMesh.setFaceVertexNormalsようにフェースIDを生成
                    face_ids.extend([i] * len(vtx_temp))
                    connect_vtxs.extend(vtx_temp)
                    normals += poly.getNormals(om2.MSpace.kWorld)

                self.orig_info.append({'Normals': normals, 'FaceIDs' : face_ids, 'VertexIds' : connect_vtxs})


                # 編集用法線
                normal_edit = dst_fn_mesh.getVertexNormals(False, om2.MSpace.kWorld)

                # コンポーネント選択かどうかで処理を分岐させる
                if sel.hasComponents():
                    dst_fn_comp = om2.MFnSingleIndexedComponent(obj)

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


                        pos = dst_fn_mesh.getPoint(vtx_id, om2.MSpace.kWorld)
                        normal_edit[vtx_id] = normal_edit[vtx_id] * (1.0 - weight) + weight *\
                                              om2.MFloatVector(src_fn_mesh.getClosestNormal(pos, om2.MSpace.kWorld)[0])

                else:
                    # オブジェクト選択の場合
                    points = dst_fn_mesh.getPoints(om2.MSpace.kWorld)

                    if self.base_weight == 1.0:
                        for j, pos in enumerate(points):
                            normal_edit[j] = src_fn_mesh.getClosestNormal(pos, om2.MSpace.kWorld)[0]
                    else:
                        for j, pos in enumerate(points):
                            normal_edit[j] = normal_edit[j] * (1.0 - self.base_weight) + self.base_weight * \
                                             om2.MFloatVector(src_fn_mesh.getClosestNormal(pos, om2.MSpace.kWorld)[0])

            # 法線転送
            dst_fn_mesh.setVertexNormals(normal_edit, range(num_vtx), om2.MSpace.kWorld)
            end = time()
            print(f'# HTMTransferNormals : {end - sta:.3f} sec')


    def undoIt(self):
        it_sel = om2.MItSelectionList(self.sel)
        for i, sel in enumerate(it_sel):
            if i == 0:
                continue

            dag_path, _ = sel.getComponent()
            fn_mesh = om2.MFnMesh(dag_path)
            fn_mesh.setFaceVertexNormals(self.orig_info[i-1]['Normals'],
                                         self.orig_info[i-1]['FaceIDs'],
                                         self.orig_info[i-1]['VertexIds'],
                                         om2.MSpace.kWorld)


    def parseArguments(self, args):
        arg_data = om2.MArgDatabase(self.syntax(), args)

        if arg_data.isFlagSet(kShort_flag_base_weight):
            self.base_weight = arg_data.flagArgumentFloat(kShort_flag_base_weight, 0)


    def isUndoable(self):
        return True

    @staticmethod
    def syntaxCreator():
        """ Add arguments, keyword arguments.
        Flag:
            Kwargs:
                baseWeight(bw): float
        """
        syntax = om2.MSyntax()
        syntax.addFlag(kShort_flag_base_weight, kLong_flag_base_weight, om2.MSyntax.kLong) # kLong == int
        return syntax


def initializePlugin(mobject):
    plugin = om2.MFnPlugin(mobject)
    plugin.registerCommand(HTMTransferNormals.kPluginCmdName,
                           HTMTransferNormals.cmdCreator,
                           HTMTransferNormals.syntaxCreator)


def uninitializePlugin(mobject):
    pluginFn = om2.MFnPlugin(mobject)
    pluginFn.deregisterCommand(HTMTransferNormals.kPluginCmdName)