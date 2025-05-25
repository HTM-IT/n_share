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
import maya.api.OpenMayaAnim as oma2
import maya.OpenMaya as om
import maya.OpenMayaAnim as oma

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
        # バインドポーズ関連
        gb_bp = QGroupBox(u'バインドポーズ')
        vbl_bp = QVBoxLayout()
        vbl_bp.setContentsMargins(2, 2, 2, 2)
        vbl_bp.setSpacing(4)

        pb_bp = QPushButton(u'ジョイントの再初期化')
        pb_bp.clicked.connect(HTM_ReinitializeSkinnedJoint.reinitialize)
        pb_bp.setFixedHeight(30)
        vbl_bp.addWidget(pb_bp)

        pb_rbp = QPushButton(u'バインドポーズを1つにする\n(現在のジョイントの状態をバインドポーズに)')
        pb_rbp.clicked.connect(HTM_RecreateBindPose.recreate_bind_pose)
        pb_rbp.setFixedHeight(40)
        vbl_bp.addWidget(pb_rbp)

        gb_bp.setLayout(vbl_bp)
        main_layout.addWidget(gb_bp)

        # ----------------------------------------------
        # バインドポーズ関連
        gb_dh = QGroupBox(u'ヒストリ整理')
        vbl_dh = QVBoxLayout()
        vbl_dh.setContentsMargins(2, 2, 2, 2)
        vbl_dh.setSpacing(4)

        pb_rbp = QPushButton(u'ヒストリの削除\n(バインド情報は残す)')
        pb_rbp.clicked.connect(HTM_DeleteHistoryWithoutSC.del_history_without_sc)
        pb_rbp.setFixedHeight(40)
        vbl_dh.addWidget(pb_rbp)

        gb_dh.setLayout(vbl_dh)
        main_layout.addWidget(gb_dh)

        # ----------------------------------------------
        # バインドポーズ関連
        gb_jo = QGroupBox(u'ジョイントの方向づけ')

        # コンボボックスオブジェクトの生成
        self.cb_jo_prim = QComboBox(self)
        self.cb_jo_prim.addItems(['X', 'Y', 'Z'])
        self.cb_jo_sec = QComboBox(self)
        self.cb_jo_sec.addItems(['X', 'Y', 'Z', 'Bend'])
        self.cb_jo_sec.setCurrentIndex(1)
        self.cb_jo_w = QComboBox(self)
        self.cb_jo_w.addItems(['X', 'Y', 'Z'])
        self.cb_jo_w.setCurrentIndex(1)
        self.chb_inverse = QCheckBox(u'反転')
        pb_jo = QPushButton(u'ジョイントの方向づけ')
        pb_jo.clicked.connect(self.joint_orient_clbk)

        gl_jo = QGridLayout()
        gl_jo.setContentsMargins(2, 2, 2, 2)
        gl_jo.setSpacing(4)
        gl_jo.addWidget(QLabel(u'プライマリ軸 :'), 0, 0)
        gl_jo.addWidget(self.cb_jo_prim, 0, 1)
        gl_jo.addWidget(QLabel(u'セカンダリ軸 :'), 1, 0)
        gl_jo.addWidget(self.cb_jo_sec, 1, 1)
        gl_jo.addWidget(QLabel(u'セカンダリ軸のワールド方向 :'), 2, 0, 1, 2)
        gl_jo.addWidget(self.cb_jo_w, 3, 0)
        gl_jo.addWidget(self.chb_inverse, 3, 1)
        gl_jo.addWidget(pb_jo, 4, 0, 1, 2)


        gb_jo.setLayout(gl_jo)
        main_layout.addWidget(gb_jo)

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

    def joint_orient_clbk(self):
        # Get primary axis, secondary axis and bend mode flag
        prm_axis = self.cb_jo_prim.currentText().lower()
        sec_axis = self.cb_jo_sec.currentText().lower()
        if prm_axis == sec_axis:
            om2.MGlobal.displayError(u'プライマリ軸とセカンダリ軸はそれぞれ別々の軸を設定してください')
            return

        bend_direction = False
        if sec_axis == 'bend':
            axis_table = {'x':'z', 'y':'x', 'z':'y'}
            sec_axis = axis_table[prm_axis]
            bend_direction = True

        # セカンダリ軸のワールド方向の取得
        sec_target = self.cb_jo_w.currentText().lower()

        # ワールド方向の反転フラグ取得
        sec_target_inv = self.chb_inverse.isChecked()
        if sec_target_inv:
            sec_target = '-' + sec_target

        HTM_JointOrient.joint_orient(bend_direction, prm_axis=prm_axis,
                                   sec_axis=sec_axis, sec_target=sec_target)
        #self.orient_func.joint_orient(bend_direction, prm_axis=prm_axis,
        #                           sec_axis=sec_axis, sec_target=sec_target)


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
    @classmethod
    def get_all_root_joints(cls):
        # ルートジョイント取得用再帰関数
        def get_root_joint(joint, processed):
            parent_temp = mc.listRelatives(joint, p=True, type='joint', f=True)
            if parent_temp == None:
                return joint

            processed.append(parent_temp[0])
            return get_root_joint(parent_temp[0], processed)

        joints = mc.ls(sl=True, type='joint', l=True)
        if not joints:
            om2.MGlobal.displayError(u'ジョイントの最低1つは選択して実行してください')

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
        roots = cls.get_all_root_joints()

        for root in roots:
            childlen = mc.listRelatives(root, ad=True, type='joint', f=1)
            dagpose = mc.listConnections(root, type='dagPose')
            dagpose = list(set(dagpose))

            # dagPoseノードの削除と作り直し
            mc.delete(dagpose)
            mc.dagPose(root, bp=True, save=True)


class HTM_DeleteHistoryWithoutSC:
    @classmethod
    def get_sc(cls, obj_name_str):
        sc = mc.ls(mc.listHistory(obj_name_str, pdo=True), type='skinCluster')[0]
        sel_sc = om2.MGlobal.getSelectionListByName(sc)
        mo_sc= sel_sc.getDependNode(0)
        fn_sc = oma2.MFnSkinCluster(mo_sc)
        return sc, fn_sc

    @classmethod
    @undo_ctx
    def del_history_without_sc(cls):
        sel = om2.MGlobal.getActiveSelectionList()
        it_sel = om2.MItSelectionList(sel)
        selection = mc.ls(sl=True)

        for it_s in it_sel:
            dag, comp = it_s.getComponent()

            # トランスフォームノード以外が選択されていたらスルー
            # シェイプがない場合もスルー
            if not dag.hasFn(om2.MFn.kTransform):
                continue

            fn_trans = om2.MFnTransform(dag)
            has_shape = False
            for i in range(fn_trans.childCount()):
                child = fn_trans.child(i)
                if child.hasFn(om2.MFn.kMesh):
                    has_shape = True
            if not has_shape:
                continue

            # シェイプの取得
            dp_shape = dag.extendToShape()
            obj_name_str = dag.fullPathName()

            # スキンクラスター関連情報取得
            sc, fn_sc = cls.get_sc(obj_name_str)

            infs = mc.skinCluster(sc, q=True, inf=True)
            max_inf = mc.getAttr(sc + '.maxInfluences')
            normalize_weights = mc.getAttr(sc + '.normalizeWeights')
            maintain_max_inf = mc.getAttr(sc + '.maintainMaxInfluences')

            # ウェイト保存
            weights, num_inf = fn_sc.getWeights(dp_shape, comp)

            # ヒストリ削除
            mc.skinCluster(obj_name_str, e=True, ub=True)
            mc.delete(obj_name_str, ch=True)
            mc.skinCluster(obj_name_str, infs, tsb=True, mi=max_inf,
                           omi=maintain_max_inf, nw=normalize_weights)

            # バインド情報復旧
            _, fn_sc_new = cls.get_sc(obj_name_str)
            inf_ids = om2.MIntArray(range(num_inf))
            fn_sc_new.setWeights(dp_shape, comp, inf_ids, weights)

        om2.MGlobal.setActiveSelectionList(sel)


class HTM_JointOrient:
    @staticmethod
    def get_n_vector(joint_0, joint_1, joint_2):
        """
        Param:
            pos_0: float list or MPoint list
            pos_1: float list or MPoint list
            pos_2: float list or MPoint list
        """
        pos_0 = om2.MPoint(mc.xform(joint_0, q=True, ws=True, t=True))
        pos_1 = om2.MPoint(mc.xform(joint_1, q=True, ws=True, t=True))
        pos_2 = om2.MPoint(mc.xform(joint_2, q=True, ws=True, t=True))

        vector_0 = (pos_1 - pos_0).normal()
        vector_1 = (pos_2 - pos_1).normal()

        n_vector = (vector_0 ^ vector_1).normal()

        return n_vector

    @staticmethod
    def get_aim_vector(joint_0, joint_1):
        """
        Param:
            jiont_0(str): fullpath
            jiont_1(str): fullpath
        """
        pos_base = om2.MPoint(mc.xform(joint_0, q=True, ws=True, t=True))
        pos_aim = om2.MPoint(mc.xform(joint_1, q=True, ws=True, t=True))
        vec_aim = (pos_aim - pos_base).normal()
        return vec_aim

    @staticmethod
    def aim_transform(joint, vec_aim, vec_sec,
                      prm_axis='x', sec_axis='z', sec_target='y'):
        """
        """
        vector_table = {'x' : om2.MVector(1, 0, 0),
                        'y' : om2.MVector(0, 1, 0),
                        'z' : om2.MVector(0, 0, 1),
                        '-x': om2.MVector(1, 0, 0),
                        '-y': om2.MVector(0, 1, 0),
                        '-z': om2.MVector(0, 0, 1)}

        pos = mc.xform(joint, q=True, ws=True, t=True)

        # Secondary axis world orientation
        sec_axis_target = vector_table[sec_target]
        vec_temp = (vec_aim ^ sec_axis_target).normal()
        if not vec_sec:
            vec_sec = (vec_temp ^ vec_aim).normal()

        # Init primary/secondary base vecotr to calculate rotation.
        vec_prm_base = vector_table[prm_axis]
        vec_sec_base = vector_table[sec_axis]

        # Get quaternion that can rotate "vec_prm_base" to "vec_aim".
        quaternion_aim = om2.MQuaternion(vec_prm_base, vec_aim)
        vec_sec_base = vec_sec_base.rotateBy(quaternion_aim)

        # Get quaternion about secondary vector
        quaternion_sec = vec_sec_base.rotateTo(vec_sec)

        rot_mtx = om2.MMatrix()
        if '-' in sec_target:
            quaternion_inverse = om2.MQuaternion(math.radians(180), vec_aim)
            rot_mtx = (quaternion_aim * quaternion_sec * quaternion_inverse).asMatrix()
        else:
            rot_mtx = (quaternion_aim * quaternion_sec).asMatrix()

        parent_inv_mtx = om2.MMatrix(mc.getAttr(joint + '.parentInverseMatrix'))
        matrix = rot_mtx * parent_inv_mtx

        mc.xform(joint, ws=False, m=matrix)
        mc.xform(joint, ws=True, t=pos)


    @classmethod
    @undo_ctx
    def joint_orient(cls, bend_direction=False,
                     prm_axis='x', sec_axis='z', sec_target='y'):
        """
        """
        joints = mc.ls(sl=True, type='joint', l=True)
        if not joints:
            om2.MGlobal.displayError('Please select one ore more joints.')
            return

        hierarchy = True
        if hierarchy:
            joints_child = mc.listRelatives(joints, ad=True, type='joint', f=True)
            if joints_child:
                joints_child.extend(joints)
                joints_child.reverse()
                joints = joints_child

        joints_peak = []
        for joint in joints:

            vec_sec = None
            if bend_direction:
                # Bend direction mode
                parent = mc.listRelatives(joint, p=True, f=True) or []
                child  = mc.listRelatives(joint, c=True, f=True) or []

                # if there's multiple child joint
                """
                if len(child) > 1:
                    om2.MGlobal.displayWarning('"{}" skipped because of multiple child joints found.')
                    continue
                """

                # if not child joint exists
                if not len(child):
                    joints_peak.append(joint)
                    continue

                # if not parent joint exists
                elif not len(parent) or parent[0] not in joints:
                    joint_0 = joint
                    joint_1 = child[0]
                    joint_2 = mc.listRelatives(child, c=True, f=True)[0]

                    if not joint_2:
                        # If there's less than two joints in the selection.
                        mc.error('There\'s no enough number of joints.')

                else:
                    joint_0 = parent
                    joint_1 = joint
                    joint_2 = child[0]

                # Get a vector of bend axis
                vec_sec = cls.get_n_vector(joint_0, joint_1, joint_2)

            else:
                child = mc.listRelatives(joint, c=True, f=True)

                # If multiple child joints were found.
                #if len(child) > 1:
                #    om2.MGlobal.displayWarning('"{}" skipped because of multiple child joints found.')
                #    continue

                # If no child joints were found.
                if not child:
                    joints_peak.append(joint)
                    continue

            # Restore child's pos/rot
            child_rot = []
            child_pos = []
            for c in child:
                child_rot.append(mc.xform(c, q=True, ws=True, ro=True))
                child_pos.append(mc.xform(c, q=True, ws=True, t=True))

            # Execute aim_transform
            vec_aim = cls.get_aim_vector(joint, child[0])
            cls.aim_transform(joint, vec_aim, vec_sec, prm_axis, sec_axis, sec_target)

            # Reset child pos/rot
            for c, rot, pos in zip(child, child_rot, child_pos):
                mc.xform(c, ws=True, ro=rot)
                mc.xform(c, ws=True,  t=pos)

        # For peak joints
        for joint in joints_peak:
            mc.setAttr('%s.rotate' % joint, 0, 0, 0)
            mc.setAttr('%s.jointOrient' % joint, 0, 0, 0)


def main():
    win_ptr = MQtUtil.findControl(win_title)
    if win_ptr:
        win_inst = wrapInstance(int(win_ptr), QWidget)
        win_inst.close()

    ex = HTM_SetupTools()
    ex.show()


if '__main__' == __name__:
    main()



