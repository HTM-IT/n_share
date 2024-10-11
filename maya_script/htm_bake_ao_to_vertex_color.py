# -*- coding: utf-8 -*-
import sys
from tempfile import gettempdir

from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import QImage, QIcon
from shiboken2 import wrapInstance

import maya.cmds as mc
import maya.api.OpenMaya as om2
from maya.OpenMayaUI import MQtUtil
from maya.app.general.mayaMixin import MayaQWidgetBaseMixin
from maya.mel import eval
import maya.utils


WIN_TITLE = 'HTM Bake AO To Vertex Color'

class HTMBakeaAOToVertexColor(MayaQWidgetBaseMixin, QMainWindow):
    def __init__(self, parent=None, *args, **kwargs):
        super(HTMBakeaAOToVertexColor, self).__init__(parent=parent, *args, **kwargs)
        self.load_mtoa_plugin()
        self.init_ui()
        #maya.utils.executeDeferred(self.init_aov)
        self.init_aov()
        self.init_render_settings()

    def init_ui(self):
        # set window status
        self.setWindowTitle(WIN_TITLE)
        self.setMaximumSize(300, 300)

        # central widget
        widget = QWidget()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # =========================================
        # ベイク用UV生成
        # =========================================
        vbl_create_uv = QVBoxLayout()
        vbl_create_uv.setContentsMargins(4, 4, 4, 4)
        vbl_create_uv.setSpacing(4)
        gb_sub_2 = QGroupBox(u'ベイク用UV生成')
        pb_create_uv = QPushButton(u'UV生成')
        pb_create_uv.setIcon(QIcon(':/UVEditorCheckered.png'))
        pb_create_uv.setIconSize(QSize(20,20))
        pb_create_uv.clicked.connect(self.create_uv_for_bake)

        vbl_create_uv.addWidget(pb_create_uv)
        gb_sub_2.setLayout(vbl_create_uv)

        # =========================================
        # ベイク設定
        # =========================================
        vbl_settings = QVBoxLayout()
        vbl_settings.setContentsMargins(4, 4, 4, 4)
        vbl_settings.setSpacing(4)
        gb_main = QGroupBox(u'ベイク設定')

        # texture size
        l_tex_size = QLabel(u'テクスチャサイズ :')
        l_tex_size.setStyleSheet(u'font:Meiriyo UI')
        l_tex_size.setFixedWidth(100)
        l_tex_size.setAlignment(Qt.AlignRight|Qt.AlignVCenter)

        hbl_tex_size = QHBoxLayout()
        self.cb_tex_size = QComboBox()
        self.cb_tex_size.addItems(['512 x 512px', '1024 x 1024px', '2048 x 2048px'])
        self.cb_tex_size.setCurrentText('2048 x 2048px')

        hbl_tex_size.addWidget(l_tex_size)
        hbl_tex_size.addWidget(self.cb_tex_size)

        # sample count
        hbl_sample_count = QHBoxLayout()
        l_sample_count = QLabel(u'サンプル数 :')
        l_sample_count.setFixedWidth(100)
        l_sample_count.setAlignment(Qt.AlignRight|Qt.AlignVCenter)

        self.s_sample_count = QSlider()
        self.s_sample_count.setValue(3)
        self.s_sample_count.setRange(3,16)
        self.s_sample_count.setOrientation(Qt.Horizontal)
        self.s_sample_count.valueChanged.connect(self.slider_on_value_changed)

        self.sb_sample_count = QSpinBox()
        self.sb_sample_count.setValue(3)
        self.sb_sample_count.setRange(3,16)
        self.sb_sample_count.valueChanged.connect(self.sb_on_value_changed)
        self.sb_sample_count.setFixedWidth(50)

        hbl_sample_count.addWidget(l_sample_count)
        hbl_sample_count.addWidget(self.s_sample_count)
        hbl_sample_count.addWidget(self.sb_sample_count)

        # exec button
        pb_bake = QPushButton(u'AOベイク && 頂点カラーへ適用', self)
        pb_bake.setIcon(QIcon(':/textureToGeom.png'))
        pb_bake.setIconSize(QSize(20,20))
        pb_bake.clicked.connect(self.exec_bake)

        vbl_settings.addLayout(hbl_tex_size)
        vbl_settings.addLayout(hbl_sample_count)
        vbl_settings.addWidget(pb_bake)
        gb_main.setLayout(vbl_settings)

        # =========================================
        # 頂点カラー編集
        # =========================================
        vbl_vcolor_edit = QVBoxLayout()
        vbl_vcolor_edit.setContentsMargins(4, 4, 4, 4)
        vbl_vcolor_edit.setSpacing(4)
        gb_sub = QGroupBox(u'頂点カラー編集')

        pb_toggle_col = QPushButton(u'頂点カラー 表示/非表示')
        pb_toggle_col.setIcon(QIcon(':/render_swColorPerVertex.png'))
        pb_toggle_col.setIconSize(QSize(20,20))
        pb_toggle_col.clicked.connect(self.toggle_vertex_color)

        pb_blur_col = QPushButton(u'頂点カラーをぼかす')
        pb_blur_col.setIcon(QIcon(':/smoothSkinWeights.png'))
        pb_blur_col.setIconSize(QSize(20,20))
        pb_blur_col.clicked.connect(self.blur_vertex_color)

        vbl_vcolor_edit.addWidget(pb_toggle_col)
        vbl_vcolor_edit.addWidget(pb_blur_col)
        gb_sub.setLayout(vbl_vcolor_edit)

        # =========================================
        # メインレイアウト
        # =========================================
        main_layout.addWidget(gb_sub_2)
        main_layout.addWidget(gb_main)
        main_layout.addWidget(gb_sub)

        widget.setLayout(main_layout)
        self.setCentralWidget(widget)

    def slider_on_value_changed(self):
        value = self.s_sample_count.value()
        self.sb_sample_count.setValue(value)

    def sb_on_value_changed(self):
        value = self.sb_sample_count.value()
        self.s_sample_count.setValue(value)

    def create_uv_for_bake(self):
        """ ベイクに使用するためのUVの生成
        """
        sel = mc.ls(sl=True, type='transform')
        if not sel:
            om2.MGlobal.displayError(u'1つ以上のオブジェクトを選択して実行してください')
        working_uv = 'xxx_ao_bake'

        for s in sel:
            all_uvs = mc.polyUVSet(s, q=True, allUVSets=True)

            if not working_uv in all_uvs:
                mc.polyUVSet(s, create=True, uvSet=working_uv)

            # UVのコピーはあえて毎回やる、内容が変わっていることがあるあるなので
            mc.polyUVSet(s, copy=True, newUVSet=working_uv)
            try:
                # 最初からao_bakeセットが選択されているとエラーが出る
                # ただ、どのUVSetがデフォルトのものかわからないので、対策どうするか考える
                mc.polyUVSet(s, currentUVSet=True, uvSet=working_uv)
            except:
                pass

            # UVのレイアウトし直し
            padding = 1.0 / 2048 * 10 # 2048x2048のテクスチャで10ピクセル間隔をあけて配置する場合
            cmd = 'mc.u3dLayout("{0}.f[*]", res=1024, scl=1, spc={1}, mar={1}, box=[0,1,0,1])'.format(s, padding)
            mc.evalDeferred(cmd, lp=True)

    def exec_bake(self):
        """ ベイク実行
        """
        sel = mc.ls(sl=True, type='transform')
        if not sel:
            om2.MGlobal.displayError(u'オブジェクトを選択して実行してください')

        size_table = {'512 x 512px':512, '1024 x 1024px':1024, '2048 x 2048px':2048}
        tex_size = self.cb_tex_size.currentText()
        sample_count = self.s_sample_count.value()

        # AOのサンプル数変更
        mc.setAttr(self.ao + '.samples', sample_count)

        # ベイクと頂点カラーのインポート
        temp_dir = gettempdir()
        if True:

            # 選択オブジェクトの取得
            sel = mc.ls(sl=True, type='transform')
            if not len(sel) == 1:
                return
            shape = mc.listRelatives(sel, shapes=True, ni=True)

            # ベイク実行
            mc.arnoldRenderToTexture(f=temp_dir, filter='gaussian',
                                     aa_samples=sample_count, ee=True,
                                     r=size_table[tex_size], aov=True)

            # テクスチャを頂点カラーとしてインポート、頂点カラーのペイントツールの機能を使用
            # ベイク処理が終わるまで待ちたいのでevalDeferredで
            baked_tex = temp_dir + '\\' + shape[0] + '.custom_AO.exr'
            eval('PaintVertexColorTool; toolPropertyWindow;')
            cmd = 'mc.artAttrPaintVertexCtx("{}", e=True, importfileload=r"{}")'.format(mc.currentCtx(), baked_tex)
            mc.evalDeferred(cmd, lp=True)

    def toggle_vertex_color(self):
        """ 頂点カラーの表示非表示のトグル
        """
        sel = mc.ls(sl=True, tr=True)
        if sel:
            shapes = mc.listRelatives(sel, shapes=True, ni=True)
        else:
            shapes = mc.ls(mc.listRelatives(mc.ls(tr=True), shapes=True, ni=True), type='mesh')

        for s in shapes:
            if mc.getAttr(s + '.displayColors'):
                for s in shapes:
                    mc.setAttr(s + '.displayColors', False)
                break
            else:
                mc.setAttr(s + '.displayColors', True)

    def blur_vertex_color(self):
        # コマンドプラグインとして実装する
        # ある頂点から接続されている頂点を取得、すべての頂点カラーを足して頂点数で割った数を設定すると
        # Maya標準のブラー処理と一緒になる、要は平均とるだけ。
        print('Blur Vertex Color')

    def load_mtoa_plugin(self):
        """ mtoaロードされてるかチェック
        """
        loaded = mc.pluginInfo('mtoa', q=True, l=True)
        if not loaded:
            try:
                mc.loadPlugin('mtoa', quiet=True)
            except Exception as e:
                # プラグインがロードできない場合はエラー
                # Arnoldが何らかの理由によりインストールされていない場合に備え
                om2.MGlobal.displayError(e)
                return

            mc.pluginInfo('mtoa', e=True, a=True)
        else:
            om2.MGlobal.displayInfo('Arnold Plugin has been loaded.')

    def init_aov(self):
        """ AOVの設定
        """
        render_op = mc.ls("defaultArnoldRenderOptions")
        if not render_op:
            # レンダー設定ノードがなかったら作成
            #eval('unifiedRenderGlobalsRevertToDefault()')
            #eval('initRenderSettingsWindow();')
            pass

        mc.evalDeferred("print('hoge')")
        aov = None

        # AOVがある場合は全接続を切る
        connections = mc.listConnections('defaultArnoldRenderOptions.aovList', p=True, c=True)
        if connections:
            for i in range(0, len(connections), 2):
                aov_node = connections[i+1].split('.')[0]

                if mc.getAttr(aov_node + '.name') == 'custom_AO':
                    aov = aov_node
                    continue
                mc.disconnectAttr(connections[i+1], connections[i])

        if aov:
            # custom_AOのAOVがすでにある場合
            shader = mc.listConnections(aov + '.defaultValue')
            if shader:
                if mc.nodeType(shader) == 'aiAmbientOcclusion':
                    # ShaderがaiAOだった場合は処理を完了
                    self.ao = shader[0]
                    return

                elif mc.nodeType(shader) != 'aiAmbientOcclusion':
                    # ShaderがaiAOじゃない場合は接続を切っておく
                    connections = mc.listConnections(aov + 'defaultValue', c=True)
                    mc.disconnectAttr(connections[1], connections[0])

        else:
            # AOVノード作成
            aov = mc.createNode('aiAOV', n='aiAOV_custom_AO')
            mc.setAttr(aov + '.name', 'custom_AO', type='string')

            # mtoaがロードされていたらdeaultArnoldDriverとかはシーン内に存在するはず
            mc.connectAttr('defaultArnoldDriver.message', aov + '.outputs[0].driver')
            mc.connectAttr('defaultArnoldFilter.message', aov + '.outputs[0].filter')
            mc.connectAttr(aov + '.message', 'defaultArnoldRenderOptions.aovList[0]')

        # AOシェーダーの作成と接続
        self.ao = mc.createNode('aiAmbientOcclusion', n='aiAO')
        mc.connectAttr(self.ao + '.outColor', aov + '.defaultValue')

    def init_render_settings(self):
        """ レンダー設定変更
        """
        # render optionのノード取得、おそらくシーンに一個しかないんじゃないかな？
        arnold_op = mc.ls(type='aiOptions')[0]

        # Smapling設定
        mc.setAttr('{}.AASamples'.format(arnold_op),0);
        mc.setAttr('{}.GIDiffuseSamples'.format(arnold_op),0);
        mc.setAttr('{}.GISpecularSamples'.format(arnold_op),0);
        mc.setAttr('{}.GITransmissionSamples'.format(arnold_op),0);
        mc.setAttr('{}.GISssSamples'.format(arnold_op),0);
        mc.setAttr('{}.GIVolumeSamples'.format(arnold_op),0);

        # RayDepth設定
        mc.setAttr('{}.GIDiffuseDepth'.format(arnold_op), 0)
        mc.setAttr('{}.GISpecularDepth'.format(arnold_op), 0)
        mc.setAttr('{}.GITransmissionDepth'.format(arnold_op), 0)
        mc.setAttr('{}.GIVolumeDepth'.format(arnold_op), 0)
        mc.setAttr('{}.autoTransparencyDepth'.format(arnold_op), 8)
        mc.setAttr('{}.GITotalDepth'.format(arnold_op), 8)


def main():
    win_ptr = MQtUtil.findControl(WIN_TITLE)
    if win_ptr:
        win_inst = wrapInstance(int(win_ptr), QWidget)
        win_inst.close()

    app = QApplication.instance()
    ex = HTMBakeaAOToVertexColor()
    ex.show()
    sys.exit()
    app.exec_()


if '__main__' == __name__:
    main()

eval('unifiedRenderGlobalsRevertToDefault()')