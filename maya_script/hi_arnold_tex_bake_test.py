# -*- coding: utf-8 -*-
# render AO
import maya.cmds as mc
import os


def guess_crt_prj():
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
guess_crt_prj()


def create_working_uv(sel):
    working_uv = 'ao_bake'

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
        cmd = 'mc.u3dLayout("{}.f[*]", res=1024, scl=1, spc=padding, mar=padding, box=[0,1,0,1])'.format(s)
        mc.evalDeferred(cmd, lp=True)

sel = mc.ls(sl=True)
create_working_uv(sel)


# AOV設定
def set_render_settings():
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

    # AOV
    aovs = mc.listConnections('{}.aovList'.format(arnold_op), s=True, d=False, type='aiAOV')
    aovs = [aov for aov in aovs if 'custon_AO' in aov]


# Arnoldのテクスチャにベイクするコマンド
mc.arnoldRenderToTexture(f='C:/Users/hiruk/Desktop', filter='gaussian', aa_samples=3,
                         ee=True, r=1024, aov=True, shader='aiStandardSurface1',
                         uvs='ao_bake')
