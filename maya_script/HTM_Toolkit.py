# -*- coding: utf-8 -*-
import sys
from tempfile import gettempdir
from math import degrees, radians

from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import QImage, QIcon
from shiboken2 import wrapInstance

import maya.cmds as mc
import maya.api.OpenMaya as om2
from maya.OpenMayaUI import MQtUtil
from maya import OpenMayaUI as omui
from maya.app.general.mayaMixin import MayaQWidgetBaseMixin
from maya.mel import eval
import maya.utils

python_version = sys.version_info.major
win_title = 'HTM Tools'


import time
class Timer:
    def start(self):
        self.sta = time.time()

    def end(self):
        result = time.time() - self.sta
        print('# ---------------------------------------')
        print(f'# Timer Result:{result:.3f} sec.')
        print('# ---------------------------------------')


class QHLine(QFrame):
    def __init__(self):
        super(QHLine, self).__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)


class ColoredQPushButton(QPushButton):
    def __init__(self, text, color='002222', *args, **kwargs):
        super(ColoredQPushButton, self).__init__(text, *args, **kwargs)
        self.setStyleSheet(
            f'QPushButton{{background-color:#{color};\
                           color:black}}'
        )


class HTM_Toolkit(MayaQWidgetBaseMixin, QMainWindow):
    def __init__(self, parent=None, *args, **kwargs):
        # すでにあったら閉じる
        self.close_window()

        # 初期化
        super(HTM_Toolkit, self).__init__(parent=parent, *args, **kwargs)
        self.init_ui()

    def close_window(self):
        main_window_ptr = omui.MQtUtil.mainWindow()
        if python_version == 3:
            main_window = wrapInstance(int(main_window_ptr), QMainWindow)
        else:
            main_window = wrapInstance(long(main_window_ptr), QMainWindow)

        for child in main_window.children():
            if isinstance(child, QMainWindow) and child.windowTitle() == win_title:
                child.close()

    def init_ui(self):
        # set window status
        self.setWindowTitle(win_title)
        #self.setMaximumSize(300, 300)

        # central widget
        widget = QWidget()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        #----------------------------------------------------------
        # ミラー関連
        #----------------------------------------------------------
        # ミラーのメインレイアウト
        gb_mirror = QGroupBox(u'ミラー')
        vbl_mirror = QVBoxLayout()
        vbl_mirror.setContentsMargins(2, 2, 2, 2) # この設定親だけでいいっぽい
        vbl_mirror.setSpacing(4)

        # スペース指定
        hbl_axis = QHBoxLayout()
        radio_group = QButtonGroup()
        self.rb_world = QRadioButton('World')
        self.rb_object = QRadioButton('Object')
        radio_group.addButton(self.rb_world, 1)
        radio_group.addButton(self.rb_object, 2)
        radio_group.button(1).setChecked(True)
        hbl_axis.addWidget(self.rb_world)
        hbl_axis.addWidget(self.rb_object)

        vbl_mirror.addLayout(hbl_axis)

        # ミラーボタン郡
        gl_mirror = QGridLayout()
        pb_xplus = ColoredQPushButton(u'X +', 'D13D3C')
        pb_yplus = ColoredQPushButton(u'Y +', '22bb22')
        pb_zplus = ColoredQPushButton(u'Z +', '3564DF')
        pb_xminus = ColoredQPushButton(u'X -', 'D13D3C')
        pb_yminus = ColoredQPushButton(u'Y -', '22bb22')
        pb_zminus = ColoredQPushButton(u'Z -', '3564DF')

        pb_xplus.clicked.connect(lambda:self.custom_mirror_clbk('px'))
        pb_xminus.clicked.connect(lambda:self.custom_mirror_clbk('mx'))
        pb_yplus.clicked.connect(lambda:self.custom_mirror_clbk('py'))
        pb_yminus.clicked.connect(lambda:self.custom_mirror_clbk('my'))
        pb_zplus.clicked.connect(lambda:self.custom_mirror_clbk('pz'))
        pb_zminus.clicked.connect(lambda:self.custom_mirror_clbk('mz'))

        gl_mirror.addWidget(pb_xplus, 0, 0)
        gl_mirror.addWidget(pb_yplus, 0, 1)
        gl_mirror.addWidget(pb_zplus, 0, 2)
        gl_mirror.addWidget(pb_xminus, 1, 0)
        gl_mirror.addWidget(pb_yminus, 1, 1)
        gl_mirror.addWidget(pb_zminus, 1, 2)

        vbl_mirror.addLayout(gl_mirror)

        # マージしきい値
        hbl_merge = QHBoxLayout()
        l_threshold = QLabel(u'マージしきい値')
        l_threshold.setAlignment(Qt.AlignRight|Qt.AlignVCenter)

        self.sb_threshold = QDoubleSpinBox()
        self.sb_threshold.setDecimals(4)
        self.sb_threshold.setValue(0.005)
        self.sb_threshold.setSingleStep(0.001)
        self.sb_threshold.setRange(0.000, 100.0)

        hbl_merge.addWidget(l_threshold)
        hbl_merge.addWidget(self.sb_threshold)
        vbl_mirror.addLayout(hbl_merge)

        gb_mirror.setLayout(vbl_mirror)

        #----------------------------------------------------------
        # SRTツール、ピボット関連
        #----------------------------------------------------------
        gb_srt = QGroupBox(u'SRTツール / ピボット')
        vbl_srt = QVBoxLayout()
        vbl_srt.setContentsMargins(2, 2, 2, 2) # この設定親だけでいいっぽい
        vbl_srt.setSpacing(4)

        pb_custom_axis = QPushButton(u'カスタム軸をON')
        pb_custom_axis.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        pb_custom_axis.clicked.connect(OtherFunc.srt_tool_custom_axis)

        pb_center_piv = QPushButton(u'ピボットを中心に')
        pb_center_piv.setIcon(QIcon(':/menuIconModify.png'))
        pb_center_piv.setIconSize(QSize(20,20))
        pb_center_piv.clicked.connect(mc.CenterPivot)

        pb_pivot_comp = QPushButton(u'ピボットをコンポーネントに設定')
        pb_pivot_comp.clicked.connect(OtherFunc.set_pivot_to_comp)

        pb_pivot_edges = QPushButton(u'2つのエッジからピボット設定')
        pb_pivot_edges.clicked.connect(OtherFunc.exec_set_pivot_from_two_edges)

        pb_bakepiv_t = QPushButton(u'ピボットベイク (移動)')
        pb_bakepiv_r = QPushButton(u'ピボットベイク (回転)')
        pb_bakepiv_t.clicked.connect(lambda:OtherFunc.hi_bake_pivot(1,0))
        pb_bakepiv_r.clicked.connect(lambda:OtherFunc.hi_bake_pivot(0,1))

        pb_ss_v = QPushButton(u'ソフト ボリューム')
        pb_ss_s = QPushButton(u'ソフト サーフェス')
        pb_ss_v.clicked.connect(lambda:OtherFunc.switch_soft_select_type('volume'))
        pb_ss_s.clicked.connect(lambda:OtherFunc.switch_soft_select_type('surface'))

        pb_open_setting = QPushButton(u'ツール設定を開く')
        pb_open_setting.clicked.connect(OtherFunc.open_tool_settings)

        gl_srt = QGridLayout()
        gl_srt.addWidget(pb_custom_axis, 0, 0)
        gl_srt.addWidget(pb_center_piv, 0, 1)
        gl_srt.addWidget(pb_pivot_comp, 1, 0, 1, 2)
        gl_srt.addWidget(pb_pivot_edges, 2, 0, 1, 2)
        gl_srt.addWidget(pb_bakepiv_t, 3, 0)
        gl_srt.addWidget(pb_bakepiv_r, 3, 1)
        gl_srt.addWidget(QHLine(), 4, 0, 1, 2) # separalater
        gl_srt.addWidget(pb_ss_v, 5, 0)
        gl_srt.addWidget(pb_ss_s, 5, 1)
        gl_srt.addWidget(pb_open_setting, 6, 0)

        vbl_srt.addLayout(gl_srt)
        gb_srt.setLayout(vbl_srt)


        #----------------------------------------------------------
        # 頂点カラー
        #----------------------------------------------------------
        gb_other = QGroupBox(u'頂点カラー編集')
        vbl_other = QVBoxLayout()
        vbl_other.setContentsMargins(2, 2, 2, 2) # この設定親だけでいいっぽい
        vbl_other.setSpacing(4)

        pb_toggle_vc = QPushButton(u'頂点カラー 表示/非表示')
        #pb_toggle_vc.setIcon(QIcon(':/render_swColorPerVertex.png'))
        #pb_toggle_vc.setIconSize(QSize(20,20))
        pb_toggle_vc.clicked.connect(VertexColorFunc.toggle_display_vertex_color)

        #pb_toggle_vc = QPushButton(u'頂点カラー 表示モード切替')
        #pb_toggle_vc.clicked.connect(VertexColorFunc.change_blendmode_vertex_color)

        vbl_other.addWidget(pb_toggle_vc)
        gb_other.setLayout(vbl_other)

        #----------------------------------------------------------
        # メインレイアウト処理
        #----------------------------------------------------------
        main_layout.addWidget(gb_mirror)
        main_layout.addWidget(gb_srt)
        main_layout.addWidget(gb_other)

        widget.setLayout(main_layout)
        self.setCentralWidget(widget)


    def custom_mirror_clbk(self, mode_key):
        threshold = self.sb_threshold.value()
        space = 'world'
        if self.rb_object.isChecked():
            space = 'object'

        mode = {'px':('x', '+'),
                'py':('y', '+'),
                'pz':('z', '+'),
                'mx':('x', '-'),
                'my':('y', '-'),
                'mz':('z', '-')}

        CustomMirror.custom_mirror(*mode[mode_key], space_key=space,
                                    merge_threshold=threshold)


class CustomMirror:
    @classmethod
    def custom_mirror(cls, axis_key, direction_key, space_key, merge=True, merge_threshold=0.001):
        """
        カスタムミラー、不要なコンポーネントができないように調整してある
        args:
            merge_mode: 1 = merge borders, 3 = do not merge borders
        """
        axis = {'x':0, 'y':1, 'z':2}
        axis_direction = {'+':0, '-':1}
        space = {'object':1, 'world':2}
        space_om2 = {'object':om2.MSpace.kObject, 'world':om2.MSpace.kWorld}

        sel = mc.ls(sl=True, tr=True, l=True)
        if not sel:
            om2.MGlobal.displayError('No valid objects are selected.')
            return

        for s in sel:
            mc.polyMirrorFace(s,
                              cutMesh=True,
                              axis=axis[axis_key],
                              axisDirection=axis_direction[direction_key],
                              mirrorAxis=space[space_key],
                              mergeMode=3,
                              mergeThresholdType=1,
                              mergeThreshold=merge_threshold,
                              mirrorPosition=0,
                              smoothingAngle=30,
                              flipUVs=0,
                              ch=1)

            if merge:
                print('// Merge: Exec delete_irregular_comp().')
                cls.delete_irregular_comp(s, axis=axis[axis_key],
                                          space=space_om2[space_key],
                                          tolerance=merge_threshold)
        mc.select(sel, r=True)

    @staticmethod
    def delete_irregular_comp(obj, axis=0, space=om2.MSpace.kWorld, tolerance=0.001):
        """ 不要コンポーネント削除の処理
        args:
            axis(int): x=0, y=1, z=2
            space(om2.MSpace): MSpace.kWorld or Mspace.kObject
        """

        sel = om2.MSelectionList()
        sel.add(obj)
        sel_it = om2.MItSelectionList(sel)
        for sel in sel_it:
            dag, _ = sel.getComponent()

            # 不正なフェースの削除
            # 全頂点がしきい値以下ならほぼ面積0の不正なフェース
            poly_it = om2.MItMeshPolygon(dag)
            del_face_id = []
            for poly in poly_it:
                pos_list = poly.getPoints(space)
                not_center = False
                for pos in pos_list:
                    if abs(pos[axis] - 0.0) > tolerance:
                        break
                else:
                    del_face_id.append(poly.index())

            del_face_list = ['{}.f[{}]'.format(dag.fullPathName(), id) for id in del_face_id]
            if del_face_list:
                mc.delete(del_face_list)

            # 不要な頂点の削除
            # マージ対象のしきい値以下のものをリスト、接続頂点が2つしかない場合不正な頂点とする
            # ただし、その頂点が角にある場合はスルーしないと行けない
            fn_mesh = om2.MFnMesh(dag)
            it_vtx = om2.MItMeshVertex(dag)

            # 平面の定義
            fn_trans = om2.MFnTransform(dag)
            rp_pos = fn_trans.rotatePivot(om2.MSpace.kWorld)
            rp_vec = om2.MVector(rp_pos).normal()
            rot = fn_trans.rotation(om2.MSpace.kWorld, True)

            vec_per_axis = [om2.MVector(1, 0, 0),
                            om2.MVector(0, 1, 0),
                            om2.MVector(0, 0, 1)]

            if space == om2.MSpace.kObject:
                plane_vec = vec_per_axis[axis].rotateBy(rot)
                plane = om2.MPlane().setPlane(plane_vec, 0)
                offset = plane.distanceToPoint(om2.MVector(rp_pos))

                # 向きチェック（平面のオフセットの符号を決める）
                if rp_vec * plane.normal() > 0:
                    offset *= -1

                plane.setPlane(plane_vec, offset)

            else:
                plane = om2.MPlane().setPlane(vec_per_axis[axis], 0)


            pos_list = fn_mesh.getPoints(space)
            vtxs_delete = []
            timer = Timer()
            timer.start()
            for i, pos in enumerate(pos_list):
                diff = plane.distanceToPoint(om2.MVector(pos))
                if diff < tolerance:
                    center_vtxs.append(i)

                it_vtx.setIndex(i)
                con_vtxs = it_vtx.getConnectedVertices()
                if len(con_vtxs) > 2:
                    continue

                # 接続頂点が2つだが、不正ではない頂点をはぶく処理
                # 接続エッジをベクトルとして、足して0になったら同一直線上にあると判断
                vec_a = (fn_mesh.getPoint(con_vtxs[0]) - pos).normal()
                vec_b = (fn_mesh.getPoint(con_vtxs[1]) - pos).normal()
                if om2.MVector(0,0,0).isEquivalent(vec_a + vec_b, 0.000001):
                    vtxs_delete.append(i)

            vtxs_delete = [f'{obj}.vtx[{v}]' for v in vtxs_delete]
            if vtxs_delete:
                mc.delete(vtxs_delete)

            timer.end()

            # 頂点マージ
            mc.polyMergeVertex(dag.fullPathName(), d=tolerance, am =False, ch=True)


gBlendMode = 0

class VertexColorFunc:
    """ 頂点カラー関連
    """
    @classmethod
    def toggle_display_vertex_color(cls):
        shapes = mc.listRelatives(mc.ls(sl=True), shapes=True, ni=True)

        # すべて表示状態の時はすべて非表示に
        vc_state = [mc.getAttr(f'{s}.displayColors') for s in shapes]
        if all(vc_state):
            for s in shapes:
                mc.setAttr(f'{s}.displayColors', 0)
        else:
            for s in shapes:
                mc.setAttr(f'{s}.displayColors', 1)

    @classmethod
    def change_blendmode_vertex_color(cls, mode_id):
        shapes = mc.listRelatives(shapes=True, ni=True)
        mode = {0:'None', 1:'Ambient+Diffuse', 2:'Diffuse'}
        for s in shapes:
            mc.setAttr(f'{s}.displayColorChannel', mode[mode_id],type='string')



class OtherFunc:
    """ その他ツール群
    """
    @classmethod
    def srt_tool_custom_axis(cls):
        """ カスタム軸をアクティブにするだけ
        """
        current_ctx = mc.currentCtx()

        move_context = mel.eval('$tmp = $gMove;')
        rotate_context = mel.eval('$tmp = $gRotate;')
        scale_context = mel.eval('$tmp = $gScale;')

        if move_context == current_ctx:
            mc.manipMoveContext('Move', e=True, mode=6)
        elif rotate_context == current_ctx:
            mc.manipRotateContext('Rotate', e=True, mode=6)
        elif scale_context == current_ctx:
            mc.manipScaleContext('Scale', e=True, mode=6)

    @classmethod
    def set_pivot_to_comp(cls):
        """ ピボットをコンポーネントに設定する組み込み機能の呼び出し
        """
        mc.manipPivot(pin=True)
        mel.eval('manipMoveOrient 4')

    @classmethod
    def exec_set_pivot_from_two_edges(cls):
        """ 2つのエッジからピボットの回転値を設定する
            ピボットベイクと組み合わせて使うと、フリーズした回転を復活させたりもできる
        """
        # ScriptCtx name
        script_ctx_name = 'hi_set_pivot_from_two_edges_ctx'

        # Get path to this class

        if not __name__ == '__main__':
            this_class = __name__ + '.' + cls.__name__
        else:
            this_class = cls.__name__


        # Tool setup
        py_cmd = '{}.set_pivot_rot_from_two_edges();'.format(this_class)
        mel_cmd = 'python("{}")'.format(py_cmd)

        if mc.scriptCtx(script_ctx_name, q=True, exists=True):
            mc.deleteUI(script_ctx_name)

        # Get selection and change sel mode to edges
        hl = mc.ls(hl=True)
        sel = mc.ls(sl=True, tr=True)
        sel.extend(hl)
        if sel:
            mc.hilite(sel)
            mc.selectType(ocm=True, edge=True)
            mc.select(cl=True)
        else:
            om2.MGlobal.displayWarning(u'オブジェクトを選択して実行してください')
            return

        mc.scriptCtx(script_ctx_name, title='Set Pivot', edge=True,
                     snh=u'エッジを2つ選択してください', sat=True, fcs=mel_cmd, tct='edit',
                     totalSelectionSets=1, setSelectionCount=2, setAutoComplete=True)

        # Change current tool to reset tool after executing customCtx.
        tool_context = mel.eval('$tmp = $gMove;')
        mc.setToolTo(tool_context)

        mc.setToolTo(script_ctx_name)

    @classmethod
    def set_pivot_rot_from_two_edges(cls):
        sel = mc.ls(sl=True, fl=True)
        obj = mc.ls(hl=True)
        edges = mc.ls(mc.polyListComponentConversion(sel, te=True), fl=True)
        if not len(edges) == 2:
            om2.MGlobal.displayError(u'2つ以上のエッジが選択されています')
            return

        pos_list = []
        for e in edges:
            vtxs = mc.ls(mc.polyListComponentConversion(e, tv=True), fl=True)
            pos = mc.xform(vtxs, q=True, ws=True, t=True)
            pos_a = om2.MPoint(pos[:3])
            pos_b = om2.MPoint(pos[3:])
            pos_list.append([pos_a, pos_b])

        # Get distance between each points
        dist = []
        for i in range(2):
            for j in range(2):
                dist_temp = pos_list[0][i].distanceTo(pos_list[1][j])
                dist.append([dist_temp, pos_list[0][i], pos_list[0][abs(i-1)],
                                        pos_list[1][j], pos_list[1][abs(j-1)]])

        # Gen vectors
        dist.sort(key=lambda x: x[0])
        vec_z = (dist[0][2] - dist[0][1]).normal()
        vec_x = (dist[0][4] - dist[0][3]).normal()
        vec_y = vec_z ^ vec_x
        vec_x = vec_y ^ vec_z

        # Gen matrix
        matrix = [vec_x[0], vec_x[1], vec_x[2], 0,
                  vec_y[0], vec_y[1], vec_y[2], 0,
                  vec_z[0], vec_z[1], vec_z[2], 0,
                  0, 0, 0, 1]
        matrix = om2.MMatrix(matrix)

        # convert matrix to euler roation and set pivot rotation
        euler_rot = om2.MTransformationMatrix(matrix).rotation()
        deg = [degrees(e) for e in list(euler_rot)]

        # Change selection type to object
        mc.selectPref(affectsActive=False)
        mc.hilite(obj, unHilite=True)
        mc.select(obj, add=True)

        # Get manip move context name and set its pivot axis orientation
        tool_context = mel.eval('$tmp = $gMove;')
        mc.manipPivot(pin=True)
        mc.setToolTo(tool_context)
        mc.manipMoveContext('Move', e=True, oa=list(euler_rot), mode=6)

    @classmethod
    def hi_bake_pivot(cls, pos_op, rot_op):
        ''' ピボットのベイク処理、Maya組み込み機能を使用
        @param pos_op(int): 1 -> bake position, 0 -> not bake pos
        @param rot_op(int): 1 -> bake rotaion, 0 -> not bake rot
        '''

        try:
            # Get selected object name, not component name.
            # Ignore multiple selection.
            sel = mc.ls(sl=True, l=True, type='transform')
            hilite = mc.ls(hl=True, l=True)
        except:
            om2.MGlobal.displayError('Nothing is selected.')
            return

        mc.hilite(hilite, u=True)
        mc.select(sel, hilite, r=True)
        if rot_op:
            cls.srt_tool_custom_axis() # Change pivot axis to custom.

        mel.eval('bakeCustomToolPivot {} {}'.format(pos_op, rot_op))

    @classmethod
    def trans_const_surface_toggle(cls):
        current = mc.xformConstraint(q=True, t=True)
        msg = ''
        if current == 'none':
            mc.xformConstraint(t=u'surface')
            msg = 'Transform constraint : Surface'
        elif current == 'surface':
            mc.xformConstraint(t=u'none')
            msg = 'Transform constraint : OFF'

        mc.inViewMessage(smg = msg, pos = 'topCenter', bkc = 0x000000ff, fade=1, textAlpha = 1.0)

    @classmethod
    def switch_soft_select_type(cls, type='surface'):
        #type_list = {0:'Volume', 1:'Surface', 2:'Global', 3:'Object'}
        type_list = {'volume':0, 'surface':1}

        mc.softSelect(softSelectFalloff=type_list[type])

        msg = 'Soft Select Type : {}'.format(type[0].upper() + type[1:])
        mc.inViewMessage(smg = msg, pos = 'topCenter', bkc = 0x000000ff, fade=1, textAlpha = 1.0)

    @classmethod
    def open_tool_settings(cls):
        mel.eval("toolPropertyWindow;")


def main():
    app = QApplication.instance()
    win_ptr = MQtUtil.findControl(win_title)
    if win_ptr:
        win_inst = wrapInstance(int(win_ptr), QWidget)
        win_inst.close()

    ex = HTM_Toolkit()
    ex.show()
    sys.exit()
    app.exec_()


if '__main__' == __name__:
    main()