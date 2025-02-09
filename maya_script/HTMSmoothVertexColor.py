# -*- coding: utf-8 -*-
import maya.cmds as mc
import maya.api.OpenMaya as om2
from time import time

def maya_useNewAPI():
    pass

class HTMSmoothVertexColor(om2.MPxCommand):
    kPluginCmdName = 'HTMSmoothVertexColor'

    def __init__(self):
        om2.MPxCommand.__init__(self)
        self.sel = om2.MSelectionList() # Undo用の対象メッシュ情報
        self.self.orig_color = [] # Undo用の頂点カラー情報

    @staticmethod
    def cmdCreator():
        return HTMSmoothVertexColor()

    def doIt(self, args):
        self.redoIt()

    def redoIt(self,):
        """ 基準頂点から、直接エッジでつながっている頂点を取得、それらすべての頂点カラーの
            平均を新しい頂点カラーにする。処理内容はMayaの頂点カラーペイントと同じはず
        """
        self.sel = om2.MGlobal.getActiveSelectionList()
        it_sel = om2.MItSelectionList(self.sel)

        for index, sel in enumerate(it_sel):
            sel_str = sel.getStrings()

            # 全頂点のカラーを取得、MColorに変換
            temp_color = mc.polyColorPerVertex(sel_str[0] + '.vtx[*]',q=True, rgb=True)
            self.orig_color.append([om2.MColor(temp_color[i:i+3]) for i in range(0, len(temp_color), 3)])

            dag = sel.getDagPath()
            it_vtx = om2.MItMeshVertex(dag)
            fn_mesh = om2.MFnMesh(dag)
            num_vtx = it_vtx.count()

            new_col = []
            for vtx in it_vtx:
                connect_vtxs = vtx.getConnectedVertices()
                connect_vtxs.append(vtx.index()) # 自分自身（頂点）も追加
                temp_col = om2.MColor([0.0, 0.0, 0.0])
                for c_vtx in connect_vtxs:
                    temp_col += self.orig_color[index][c_vtx]
                new_col.append(temp_col/len(connect_vtxs))

            vtx_ids = list(range(num_vtx))
            fn_mesh.setVertexColors(new_col, vtx_ids, rep=om2.MColor.kRGB)

    def undoIt(self):
        """ redoItとほぼ同じ処理内容でUndoしてる
        """
        it_sel = om2.MItSelectionList(self.sel)

        for index, sel in enumerate(it_sel):
            dag = sel.getDagPath()
            it_vtx = om2.MItMeshVertex(dag)
            fn_mesh = om2.MFnMesh(dag)
            num_vtx = it_vtx.count()

            vtx_ids = list(range(num_vtx))
            print(self.orig_color[index])
            fn_mesh.setVertexColors(self.orig_color[index], vtx_ids, rep=om2.MColor.kRGB)

    def isUndoable(self):
        return True


def initializePlugin(mobject):
    plugin = om2.MFnPlugin(mobject)
    plugin.registerCommand(HTMSmoothVertexColor.kPluginCmdName, HTMSmoothVertexColor.cmdCreator)

def uninitializePlugin(mobject):
    pluginFn = om2.MFnPlugin(mobject)
    pluginFn.deregisterCommand(HTMSmoothVertexColor.kPluginCmdName)