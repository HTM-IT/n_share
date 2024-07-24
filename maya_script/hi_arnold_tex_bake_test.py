# render AO
import os
from tempfile import gettempdir
from maya.mel import eval
import maya.cmds as mc
import maya.api.OpenMaya as om2
import maya.app.renderSetup.views.renderSetupWindow as rs_wind;

debug = True


def get_self_path():
    """ aovsのプリセットのパスを指定
    """
    if debug:
        # デバッグ用のローカルのパス
        path = r'aov_custom_ao.json'
    else:
        path = __file__ + r'\aov_custom_ao.json'

    return path


def load_mtoa_plugin():
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


def set_render_settings():
    """ レンダーセッティングとAOVsの設定
    """
    # Arnoldプラグインがロードされているかのチェックなど
    load_mtoa_plugin()

    # render optionのノード取得、一個しかないんじゃないかな？
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

    # AOVの設定、設定が編に変わっていたりしたらまずいので毎回設定する
    aov_preset_path = get_self_path()
    rs_wind._importAOVsFromPath(aov_preset_path)

    """
    aovs = mc.listConnections('{}.aovList'.format(arnold_op), s=True, d=False, type='aiAOV')
    aov_ao = [aov for aov in aovs if 'custom_AO' in aov]
    """


def guess_crt_prj():
    """ tempdirを使うため、今回は未使用
    """
    current_scene_path = mc.file(q = 1, sceneName = 1)
    current_prj = mc.workspace(q=True, rd=True)[:-1]
    if not current_prj:
        return

    all_maya_files = []
    for folders, _, filenames in os.walk(current_prj):
        if 'scenes' in folders.split('\\')[-1]:
            for file in filenames:
                all_maya_files.append(folders + '\\' + file)
        #all_files.extend(filenames)

    if not all_maya_files: # No scene files exist
        return

    file_path = mc.file(q = 1, sceneName = 1)
    if file_path in all_maya_files:
        # If current_scene_path contains current project path
        index = all_maya_files.index(file_path)
        print(all_maya_files[index])
    else:
        # If current_scene_path doesn't contain...
        target_dir_path = '/'.join(file_path.split('/')[0:-2])
        print(target_dir_path)


def create_working_uv(sel):
    """ ベイクに使用するためのUVの生成
    """
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


def create_ai_mat():
    """ ベイク時にオーバーライドするためのマテリアル生成
        元から設定されているマテリアルのTransparencyからテクスチャを取ってくる
    """
    sel = mc.ls(sl=True, tr=True)

    # マテリアルの取得
    for s in sel:
        shapes = mc.listRelatives(s, shapes=True)
        if not shapes:
            # シェイプがない場合エラーに
            om2.MGlobal.displayError(u'シェイプの存在しないモデルが選択されています')
            return

        SGs = mc.listConnections(shapes, type='shadingEngine')
        if not SGs:
            # マテリアルがない場合エラーに
            om2.MGlobal.displayError(u'マテリアルがアサインされていないモデルが選択されています')
            return
        SGs = list(set(SGs)) # 重複を削除

        materials = [mc.listConnections(SG + '.surfaceShader')[0] for SG in SGs]
        if len(materials) > 1:
            # マテリアルが複数ある場合エラーに
            om2.MGlobal.displayError(u'複数マテリアルには現在対応していません')
            return
        else:
            material = materials[0]

    # 透明度テクスチャを取得
    file = mc.listConnections(material + '.transparency', type='file')[0]
    if not file:
        # fileノードが刺さっていない場合はエラーに
        om2.MGlobal.displayError(u'マテリアルに透明度テクスチャが刺さっていません')
        return

    # 取得した透明度テクスチャを新規作成したaiStandardSurfaceシェーダーに接続
    ai_mat = 'Mt_xxx_ao_bake'
    if not mc.ls(ai_mat, type='aiStandardSurface'):
        mc.createNode('aiStandardSurface', n=ai_mat)

    for ch in ['R', 'G', 'B']:
        mc.connectAttr(file + '.outAlpha', ai_mat + '.opacity' + ch, f=True)

    return ai_mat


def exec_bake():
    """ ベイク処理諸々実行
    """
    sel = mc.ls(sl=True, tr=True)

    # ベイク用のUV作成
    create_working_uv(sel)

    # レンダー設定、重い処理じゃないので毎回設定しちゃう
    set_render_settings()

    # オーバーライド用マテリアル生成
    ai_mat = create_ai_mat()

    shapes = mc.listRelatives(sel, shapes=True, ni=True)
    tex_pathes = [shape + '.custom_AO.exr' for shape in shapes]

    # ベイク実行
    tex_save_path = gettempdir()
    mc.arnoldRenderToTexture(f=tex_save_path, filter='gaussian', aa_samples=3,
                             ee=True, r=2048, aov=True, shader=ai_mat,
                             uvs='xxx_ao_bake')

    mc.select(cl=True)
    for tex_path, s in zip(tex_pathes, sel):
        mc.select(s, r=True)
        tex_baked = tex_save_path + '\\' + tex_path

        # import texture as vertex colorf
        #file = r'C:\Users\hiruk\Desktop\T_alpha_test.tga'
        file = tex_baked

        eval('PaintVertexColorTool; toolPropertyWindow;')
        cmd = 'mc.artAttrPaintVertexCtx("{}", e=True, importfileload=r"{}")'.format(mc.currentCtx(), file)
        mc.evalDeferred(cmd, lp=True)


def create_window():
    """ ウィンドウ作成
    """
    tool_name = 'xxx_bake_ao_vertex_color'
    window_name = tool_name + '_window'

    if mc.window(window_name, exists = True) == True:
        mc.deleteUI(window_name)
    mc.window(window_name, t=tool_name)

    mc.columnLayout(rs=4, cat=('both', 5), cw=300)

    mc.columnLayout(rs = 2)
    mc.text(l=u'■ セットアップ', fn='boldLabelFont')
    mc.button(label=u'ベイク＆頂点カラー設定', c='exec_bake()')
    mc.setParent('..')

    mc.setParent('..')

    mc.showWindow(window_name)



def main():
    # mtoaがロードされているかチェック
    load_mtoa_plugin()

    # create window
    create_window()
    print('executed main function')


if __name__ == '__main__':
    main()

