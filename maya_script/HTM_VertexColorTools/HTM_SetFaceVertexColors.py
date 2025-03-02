# -*- coding: utf-8 -*-
import maya.cmds as mc
import maya.api.OpenMaya as om2

import HTM_Tools.HTM_GlobalVariable as g

def maya_useNewAPI():
    pass


class HTM_SetFaceVertexColors(om2.MPxCommand):
    """ MFnMesh.setFaceVertexColors()のUndo対応をしたいがために作ったプラグイン
    """
    kPluginCmdName = 'HTM_SetFaceVertexColors'

    def __init__(self):
        om2.MPxCommand.__init__(self)
        self.fn_mesh = om2.MFnMesh()
        self.colors_old = om2.MColorArray()
        self.face_ids_g = []
        self.vtx_ids_g = []
        self.obj = ''

    def doIt(self, args):
        self.parseArguments(args)
        self.redoIt()

    def redoIt(self):
        sel = om2.MSelectionList()
        sel.add(self.obj)

        dag, _ = sel.getComponent(0)
        self.fn_mesh = om2.MFnMesh(dag)

        # Undoのための情報取得
        self.colors_old = self.fn_mesh.getFaceVertexColors()
        num_faces = self.fn_mesh.numPolygons

        for i in range(num_faces):
            vtxs = self.fn_mesh.getPolygonVertices(i)
            for v in vtxs:
                self.vtx_ids_g.append(v)
                self.face_ids_g.append(i)

        self.fn_mesh.setFaceVertexColors(g.HTM_SetFaceVertexColors_colors,
                                         g.HTM_SetFaceVertexColors_faces,
                                         g.HTM_SetFaceVertexColors_vertex)

    def undoIt(self):
        self.fn_mesh.setFaceVertexColors(self.colors_old,
                                         self.face_ids_g,
                                         self.vtx_ids_g)

    def isUndoable(self):
        return True

    def parseArguments(self, args):
        """ Memo: This process, especially arguments has multi use flag, is too heavy.
                  It should be ideal to use global variable to pass the values to this command.
        """
        arg_data = om2.MArgDatabase(self.syntax(), args)

        # MSelectionListで取得される、1個しか扱えないので加工、あと文字列に変換
        sel_list = arg_data.getObjectList()
        self.obj = sel_list.getDagPath(0).fullPathName()

    @staticmethod
    def syntaxCreator():
        """ Add arguments, keyword arguments.

        Flag:
            Positional:
                shape name: Str
        """
        syntax = om2.MSyntax()

        # Positional Args
        # setObjectTypeした時点でコマンド引数が設定される。オブジェクトはstringでしか渡せない。
        # syntax.setObjectType(om2.MSyntax.kSelectionList)
        syntax.setObjectType(om2.MSyntax.kSelectionList)
        return syntax

    @staticmethod
    def cmdCreator():
        return HTM_SetFaceVertexColors()


def initializePlugin(mobject):
    plugin = om2.MFnPlugin(mobject)
    plugin.registerCommand(HTM_SetFaceVertexColors.kPluginCmdName,
                           HTM_SetFaceVertexColors.cmdCreator,
                           HTM_SetFaceVertexColors.syntaxCreator)


def uninitializePlugin(mobject):
    pluginFn = om2.MFnPlugin(mobject)
    pluginFn.deregisterCommand(HTM_SetFaceVertexColors.kPluginCmdName)
