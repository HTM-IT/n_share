# -*- coding: utf-8 -*-
import sys
import time
import random

from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import QImage, QIcon, QCloseEvent
from shiboken2 import wrapInstance

import maya.cmds as mc
import maya.api.OpenMaya as om2
from maya.OpenMayaUI import MQtUtil
from maya import OpenMayaUI as omui
from maya.app.general.mayaMixin import MayaQWidgetBaseMixin

import HTM_Tools.HTM_GlobalVariable as g
from HTM_Tools.HTM_Util import load_plugin

python_version = sys.version_info.major
win_title = 'HTM Vertex Color Tools'


class HTM_VertexColorTools(MayaQWidgetBaseMixin, QMainWindow):
    def __init__(self, parent=None, *args, **kwargs):
        # すでにあったら閉じる
        self.close_window()

        # 初期化
        super(HTM_VertexColorTools, self).__init__(parent=parent, *args, **kwargs)
        self.init_ui()

        self.load_plugin()


    def load_plugin(self):
        load_plugin('HTM_SetFaceVertexColors')


    def close_window(self):
        main_window_ptr = omui.MQtUtil.mainWindow()

        if python_version == 3:
            main_window = wrapInstance(int(main_window_ptr), QMainWindow)
        else:
            main_window = wrapInstance(long(main_window_ptr), QMainWindow)

        for child in main_window.children():
            if isinstance(child, QMainWindow) and child.windowTitle() == win_title:
                if mc.control('gc_htm_vtx_clr_tools', ex=True):
                    mc.deleteUI('gc_htm_vtx_clr_tools')
                child.close()

    def closeEvent(self, QCloseEvent):
        if mc.control('gc_htm_vtx_clr_tools', ex=True):
            mc.deleteUI('gc_htm_vtx_clr_tools')

    def convert_to_qt(self, control_name):
        control_ptr = omui.MQtUtil.findControl(control_name)
        if control_ptr is not None:
            if python_version == 3:
                return wrapInstance(int(control_ptr), QWidget)
            else:
                return wrapInstance(long(control_ptr), QWidget)

    def init_ui(self):
        # set window status
        self.setWindowTitle(win_title)

        # central widget
        widget = QWidget()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        mc.optionVar(stringValue=['falloffCurveOptionVar', '0,1,2'])
        mc.optionVar(stringValueAppend=['falloffCurveOptionVar', '1,0,2'])

        self.grad_ctrl = mc.gradientControlNoAttr('gc_htm_vtx_clr_tools', h=60, optionVar='falloffCurveOptionVar')
        #mc.gradientControlNoAttr('gc_htm_vtx_clr_tools', e=True, optionVar='falloffCurveOptionVar')

        self.qt_obj = self.convert_to_qt(self.grad_ctrl)
        #self.grad_ctrl.setAsString('.1,.25,1, .9,.75,1')

        main_layout.addWidget(self.qt_obj)

        # 色付け
        pb_set_grad = QPushButton('Set Gradation Ch-G')
        pb_set_grad.clicked.connect(self.set_gradient_color_from_uv)

        pb_set_rand = QPushButton('Set Random Ch-B')
        pb_set_rand.clicked.connect(self.set_random_color_from_uv)
        main_layout.addWidget(pb_set_grad)
        main_layout.addWidget(pb_set_rand)

        widget.setLayout(main_layout)
        self.setCentralWidget(widget)


    def set_random_color_from_uv(self):
        sel = mc.ls(sl=True, tr=True)
        if not sel:
            om2.MGlobal.displayWarning('Nothing is selected.')

        for s in sel:
            self.set_gradient_color_from_uv_main(s, mode='random', channel='b')


    def set_gradient_color_from_uv(self):
        sel = mc.ls(sl=True, tr=True)

        if not sel:
            om2.MGlobal.displayWarning('Nothing is selected.')

        for s in sel:
            self.set_gradient_color_from_uv_main(s, mode='gradient', channel='g')


    def set_gradient_color_from_uv_main(self, obj, mode, use_gradient_ctrl=True, channel='r'):
        """ とあるアセット用の専用処理
        """
        sel = om2.MSelectionList()
        sel.add(obj)

        dag, _ = sel.getComponent(0)
        fn_mesh = om2.MFnMesh(dag)

        # UVシェルのID取得等
        num_shells, shell_ids = fn_mesh.getUvShellsIds()

        # 元のカラー
        colors_orig = fn_mesh.getFaceVertexColors()
        print(len(colors_orig))

        # 全UV値取得
        u_vals, v_vals = fn_mesh.getUVs()

        # UVシェル事に所属UVIDを取得
        shell_to_uvs = [[-1] for _ in range(num_shells)]
        for i, shell_id in enumerate(shell_ids):
            if shell_to_uvs[shell_id][0] == -1:
                shell_to_uvs[shell_id][0] = i
            else:
                shell_to_uvs[shell_id].append(i)

        colors = om2.MColorArray().setLength(fn_mesh.numUVs())
        if mode == 'gradient':
            # UVが、所属しているUVのシェルのどの位置にあるかで頂点カラーを決める
            for uvs in shell_to_uvs:
                bb_temp = om2.MBoundingBox()
                # UVシェルごとの処理

                for uv in uvs:
                    # BBに対してMPointを投げ込んで拡張していく
                    point = om2.MPoint(u_vals[uv], v_vals[uv])
                    bb_temp.expand(point)
                max = bb_temp.max
                min = bb_temp.min

                for uv in uvs:
                    # BBの最大値・最小値の中での現在のUV値の割合をそのままカラーに
                    v_pos = v_vals[uv]
                    ratio = (v_pos - min.y) / (max.y - min.y)
                    if use_gradient_ctrl:
                        remapped_ratio = mc.gradientControlNoAttr('gc_htm_vtx_clr_tools', q=True, valueAtPoint=ratio)
                        colors[uv] = (remapped_ratio, remapped_ratio, remapped_ratio, 1)
                    else:
                        colors[uv] = (ratio, ratio, ratio, 1)

        elif mode == 'random':
            # UVシェル事に0.0-1.0のランダムな値を
            for uvs in shell_to_uvs:
                rand_val = random.random()
                for uv in uvs:
                    colors[uv] = (rand_val, rand_val, rand_val, 1)

        it_f = om2.MItMeshPolygon(dag)
        it_v = om2.MItMeshVertex(dag)
        it_fv = om2.MItMeshFaceVertex(dag)

        # フェースIDと、それに対応する頂点ID
        # フェース数 * 頂点数分、配列要素がある
        faces = []
        vertices = []
        uvs_orig = []
        sta = time.time()
        colors_new = om2.MColorArray()
        for i, fv in enumerate(it_fv):
            faces.append(fv.faceId())
            vertices.append(fv.vertexId())
            uvs_orig.append(fv.getUVIndex())
            colors_new.append(colors[uvs_orig[-1]])

        # この処理流石に冗長過ぎて...どうにかしたい
        if channel == 'r':
            for cn, co in zip(colors_new, colors_orig):
                cn.g = co.g
                cn.b = co.b
        if channel == 'g':
            for cn, co in zip(colors_new, colors_orig):
                cn.r = co.r
                cn.b = co.b
        elif channel == 'b':
            for cn, co in zip(colors_new, colors_orig):
                cn.r = co.r
                cn.g = co.g

        end = time.time()
        print(f'// Set Color : {end - sta:3f} Sec')

        g.HTM_SetFaceVertexColors_colors = colors_new
        g.HTM_SetFaceVertexColors_faces = faces
        g.HTM_SetFaceVertexColors_vertex = vertices
        mc.HTM_SetFaceVertexColors(obj)



def main():
    ex = HTM_VertexColorTools()
    ex.show()


if '__main__' == __name__:
    main()
