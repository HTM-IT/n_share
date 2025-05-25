# -*- coding: utf-8 -*-
import sys
from tempfile import gettempdir
import math
from functools import wraps
from contextlib import contextmanager

from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import QImage, QIcon
from shiboken2 import wrapInstance

import maya.cmds as mc
import maya.api.OpenMaya as om2
import maya.OpenMayaAnim as oma
import maya.OpenMaya as om
from maya.OpenMayaUI import MQtUtil
from maya import OpenMayaUI as omui
from maya.app.general.mayaMixin import MayaQWidgetBaseMixin
from maya.mel import eval
import maya.utils

python_version = sys.version_info.major
win_title = 'HTM Setup Tools'


def undo_ctx(func):
    """ エラーが出ても絶対UndoChunk閉じるマン
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        @contextmanager
        def undo_context():
            try:
                print('// Open Undo Chunk //')
                mc.undoInfo(openChunk=True)
                yield

            except Exception as e:
                print(e)

            finally:
                print('// Close Undo Chunk //')
                mc.undoInfo(closeChunk=True)

        with undo_context():
            func(*args, **kwargs)

    return wrapper


class QHLine(QFrame):
    def __init__(self):
        super(QHLine, self).__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)


class HTM_SetupTools(MayaQWidgetBaseMixin, QMainWindow):
    def __init__(self, parent=None, *args, **kwargs):
        # すでにあったら閉じる
        self.close_window()

        # 初期化
        super(HTM_SetupTools, self).__init__(parent=parent, *args, **kwargs)
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
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(4)

        # ----------------------------------------------
        # フリーズジョイント系
        gb_fj = QGroupBox(u'ジョイントのフリーズ')
        vbl_fj = QVBoxLayout()
        vbl_fj.setContentsMargins(2, 2, 2, 2)
        vbl_fj.setSpacing(4)

        # ラジオボタン
        hbl_fj_radio = QHBoxLayout()
        self.radio_group = QButtonGroup()

        rb_rotate = QRadioButton(u'回転')
        rb_orient = QRadioButton(u'ジョイントの方向')
        hbl_fj_radio.addWidget(rb_rotate)
        hbl_fj_radio.addWidget(rb_orient)
        rb_rotate.setChecked(True)

        self.radio_group.addButton(rb_rotate, 1)
        self.radio_group.addButton(rb_orient, 2)

        # ボタン
        pb_freeze_sel = QPushButton(u'選択をフリーズ')
        pb_freeze_sel.clicked.connect(lambda _:self.freeze_joint_clbk(hierarchy=False))
        pb_freeze_sel.setFixedHeight(30)

        pb_freeze_hie = QPushButton(u'階層をフリーズ')
        pb_freeze_hie.clicked.connect(lambda _:self.freeze_joint_clbk(hierarchy=True))
        pb_freeze_hie.setFixedHeight(30)
        pb_unfreezed_search = QPushButton(u'フリーズされてないジョイントを選択')
        pb_unfreezed_search.clicked.connect(self.search_unfreezed_clbk)

        vbl_fj.addLayout(hbl_fj_radio)
        vbl_fj.addWidget(pb_freeze_sel)
        vbl_fj.addWidget(pb_freeze_hie)
        vbl_fj.addWidget(pb_unfreezed_search)

        gb_fj.setLayout(vbl_fj)
        main_layout.addWidget(gb_fj)

        # ----------------------------------------------
        # ジョイントの再初期化
        gb_rj = QGroupBox(u'ジョイントの再初期化')
        vbl_rj = QVBoxLayout()
        vbl_rj.setContentsMargins(2, 2, 2, 2)
        vbl_rj.setSpacing(4)

        pb_rj = QPushButton(u'ジョイントの再初期化')
        pb_rj.clicked.connect(HTM_ReinitializeSkinnedJoint.reinitialize)
        pb_rj.setFixedHeight(30)
        vbl_rj.addWidget(pb_rj)

        gb_rj.setLayout(vbl_rj)
        main_layout.addWidget(gb_rj)

        # ----------------------------------------------
        # バインドポーズの作り直し
        gb_rbp = QGroupBox(u'バインドポーズを一つに')
        vbl_rbp = QVBoxLayout()
        vbl_rbp.setContentsMargins(2, 2, 2, 2)
        vbl_rbp.setSpacing(4)

        pb_rbp = QPushButton(u'現在のジョイントの状態で\nバインドポーズを作り直す')
        pb_rbp.clicked.connect(HTM_RecreateBindPose.recreate_bind_pose)
        pb_rbp.setFixedHeight(40)
        vbl_rbp.addWidget(pb_rbp)

        gb_rbp.setLayout(vbl_rbp)
        main_layout.addWidget(gb_rbp)

        # ----------------------------------------------
        # メインレイアウト処理
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)

    def freeze_joint_clbk(self, hierarchy=True):
        # target id
        # 1 --> フリーズ:回転
        # 2 --> フリーズ:ジョイントの方向
        target_id = self.radio_group.checkedId()
        print(target_id)
        if target_id == 1:
            HTM_FreezeJoint.freeze_joint(freeze_rot=True, hierarchy=hierarchy)
        else:
            HTM_FreezeJoint.freeze_joint(freeze_rot=False, hierarchy=hierarchy)

    def search_unfreezed_clbk(self, hierarchy=True):
        # target id
        # 1 --> フリーズ:回転
        # 2 --> フリーズ:ジョイントの方向
        target_id = self.radio_group.checkedId()
        print(target_id)
        if target_id == 1:
            HTM_FreezeJoint.search_unfreezed_joint(mode='rotation')
        else:
            HTM_FreezeJoint.search_unfreezed_joint(mode='orientation')


class HTM_FreezeJoint:
    """ ジョイントの回転・方向のフリーズ
    """
    @classmethod
    #@Decorators.undo_ctx
    def freeze_joint(cls, freeze_rot=True, hierarchy=True):
        """ ジョイントの方向 or 回転をフリーズする

        Param:
            freeze_rot(bool):回転値をフリーズ(ゼロにする)かどうか
            hierarchy(bool):階層で実行するかどうか
        """
        joints = mc.ls(sl=1, type='joint', l=1)
        if hierarchy:
            joints += mc.listRelatives(mc.ls(sl=1), ad=1, type='joint', f=1)
            joints = set(joints)  # delete redundant nodes

        for joint in joints:
            # 一旦回転値に値を全て逃がす（ジョイントの方向のフリーズ）
            mtx = mc.getAttr('{}.worldMatrix[0]'.format(joint))
            mtx = om2.MMatrix(mtx)
            rot_rad = om2.MTransformationMatrix(mtx).rotation()
            rot_deg = [math.degrees(x) for x in rot_rad]

            mc.setAttr('%s.jointOrient' % joint, 0, 0, 0)
            mc.xform(joint, ws=True, ro=rot_deg)

            # ジョイントの回転のフリーズ(逃がした回転地をジョイントの方向に入れ直すだけ)
            if freeze_rot:
                rot = mc.xform(joint, q=True, ws=False, ro=True)
                mc.xform(joint, ro=(0, 0, 0))
                mc.setAttr('{}.jointOrient'.format(joint), *rot)

    @classmethod
    def search_unfreezed_joint(cls, mode='rotation'):
        """ 回転とジョイントの方向両方に値が入っているジョイントを選択する

        Param:
            mode(str): モード切替

        Return:
            unfreezed(list): フリーズされていないジョイントのリスト
        """
        joints = mc.ls(type='joint', l=True)
        unfreezed = []
        if mode == 'rotation':
            for joint in joints:
                if not [0.0, 0.0, 0.0] == mc.xform(joint, q=True, ws=False, ro=True):
                    unfreezed.append(joint)
        elif mode == 'orientation':
            for joint in joints:
                if not (0.0, 0.0, 0.0) == mc.getAttr(joint + '.jointOrient')[0]:
                    unfreezed.append(joint)
        mc.select(unfreezed, r=True)
        return unfreezed


class HTM_ReinitializeSkinnedJoint:
    """ 現在のジョイント位置をバインドポーズ位置とする機能
        メッシュ形状はオリジナルのバインドポーズの状態を維持する
    """
    @classmethod
    #@Decorators.undo_ctx
    @undo_ctx
    def reinitialize(cls):
        """ Set current joint toransformation as BindPose
        """
        selected = mc.ls(sl=True, type='joint', l=1)
        childlen = mc.listRelatives(ad=True, type='joint', f=1)
        parents = mc.listRelatives(p=True, type='joint', f=1)

        joints = []
        joints += selected
        joints += childlen if childlen else []
        joints += parents if parents else []

        if not selected:
            om2.MGlobal.displayError(u'ジョイントを選択して実行してください')
            return

        for j in joints:
            # get all skin cluster connecting to the joint
            sc_temp_list = mc.listConnections('{}.worldMatrix'.format(j), d=True, p=True, type='skinCluster')
            if not sc_temp_list:
                continue

            # get joint's matrix
            mtx_ws = mc.getAttr('{}.worldMatrix'.format(j))
            mtx_os = mc.xform(j, q=1, os=1, m=1)
            mtx_inv = mc.getAttr('{}.worldInverseMatrix'.format(j))

            # process per joints
            mc.setAttr('{}.bindPose'.format(j), mtx_ws, type='matrix')

            # bind pose info
            plugs = mc.listConnections(j, d=True, p=True, type = 'dagPose')
            dagpose = mc.listConnections(f'{j}.message', type='dagPose')
            if len(dagpose) == 0:
                continue
            elif len(dagpose) > 1:
                om2.MGlobal.displayError(u'複数バインドポーズには対応していません')
                return

            plug_id = int(plugs[0].split('[')[-1][:-1])

            # バインドポーズのリセット
            # dagPoseが一つしかない前提で処理
            mc.setAttr('{}.xformMatrix[{}]'.format(dagpose[0], plug_id), mtx_os, type='matrix')

            for sc_temp in sc_temp_list:
                # skin cluster info
                sc = sc_temp.split('.')[0]
                sc_plug_id = int(sc_temp.split('[')[-1][:-1])

                # reset initial position
                mc.setAttr('{}.bindPreMatrix[{}]'.format(sc, sc_plug_id), mtx_inv, type='matrix')

        mc.select(selected, r=1)

    @classmethod
    def sc_envelope_toggle(cls):
        """
        """
        sc_list = mc.ls(type='skinCluster')
        for sc in sc_list:
            if mc.getAttr(sc + '.envelope') == 0:
                # Set all SC envelope at 1, if even one SC whose envelope is 0 was found.
                for sc2 in sc_list:
                    mc.setAttr(sc2 + '.envelope', 1)
                return
            else:
                mc.setAttr(sc + '.envelope', 0)


class HTM_RecreateBindPose:
    @staticmethod
    def get_all_root_joints():
        # ルートジョイント取得用再帰関数
        def get_root_joint(joint, processed):
            parent_temp = mc.listRelatives(joint, p=True, type='joint', f=True)
            if parent_temp == None:
                return joint

            processed.append(parent_temp[0])
            return get_root_joint(parent_temp[0], processed)

        joints = mc.ls(sl=True, type='joint', l=True)

        processed = []
        root_joints = []
        for j in joints:
            if j in processed:
                continue
            root_joints.append(get_root_joint(j, processed))

        # 一回セットにして重複を取り除いて返す
        return list(set(root_joints))

    @classmethod
    def recreate_bind_pose(cls):
        roots = get_all_root_joints()

        for root in roots:
            childlen = mc.listRelatives(root, ad=True, type='joint', f=1)
            dagpose = mc.listConnections(root, type='dagPose')
            dagpose = list(set(dagpose))

            # dagPoseノードの削除と作り直し
            mc.delete(dagpose)
            mc.dagPose(root, bp=True, save=True)


def main():
    win_ptr = MQtUtil.findControl(win_title)
    if win_ptr:
        win_inst = wrapInstance(int(win_ptr), QWidget)
        win_inst.close()

    ex = HTM_SetupTools()
    ex.show()


if '__main__' == __name__:
    main()



