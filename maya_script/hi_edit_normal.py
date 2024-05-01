# -*- coding: utf-8 -*-
import maya.cmds as mc
import maya.mel as mel
import maya.api.OpenMaya as om2


class Decorators:
    @classmethod
    def undo_ctx_wrapper(cls, func):
        """ Anytime close undo chunk.
        """
        def wrapper(*args, **kwargs):
            @contextmanager
            def undo_context():
                mc.undoInfo(openChunk=True)
                print('// undoInfo: Open Chunk')
                yield
                mc.undoInfo(closeChunk=True)
                print('// undoInfo: Close Chunk')

            with undo_context():
                func(*args, **kwargs)

        return wrapper


class BlendNormal:
    # ソフト選択のウェイトがそのままソースオブジェクトの法線の影響度合いに掛け合わされます。
    # ソースオブジェクトの法線の影響度合いは softselectionWeight * weight(0.0~1.0) になります。
    # 最初にターゲットを選択（コンポーネントでもオブジェクトでも）、次にソースをオブジェクト選択して実行する

    @classmethod
    @Decorators.undo_ctx_wrapper
    def transfer_vertex_normals(cls, base_weight = 1.0):
        """ Transfer vertex normal which consider soft selection weight
            and base weight you specified.

        params:
            base_weight(int): weight for blend src and dst normals.
        """

        # Symmetry can affect soft selection weight so disable it.
        if mc.symmetricModelling(q=True, symmetry=True):
            mc.symmetricModelling(symmetry=False)

        rich_sel = om2.MGlobal.getRichSelection()

        if 2 == om2.MGlobal.getActiveSelectionList().length():

            src_dag_path, src_mobj = rich_sel.getSelection().getComponent(0)
            dst_dag_path, dst_mobj = rich_sel.getSelection().getComponent(1)

            if om2.MFn.kTransform == src_dag_path.apiType() and \
               om2.MFn.kTransform == dst_dag_path.apiType():
                # Replace dst_mobj, with vertex component of selected destination object.
                temp_fn_mesh = om2.MFnMesh(dst_dag_path)
                num_vtx = temp_fn_mesh.numVertices
                vtx_comp = om2.MIntArray(range(num_vtx))

                temp_fn_single = om2.MFnSingleIndexedComponent()
                dst_mobj = temp_fn_single.create(om2.MFn.kMeshVertComponent)
                temp_fn_single.addElements(vtx_comp)

            elif not (om2.MFn.kTransform == src_dag_path.apiType() and
                      om2.MFn.kMeshVertComponent == dst_mobj.apiType()):
                # If soft selection used, apiType will return MFnMeshVertComponent
                # even for selected faces or edges.
                om2.MGlobal.displayError('// Source should be "transform", Destination should be "vetices" or "transform".')
                return

        else:
            om2.MGlobal.displayError('// Please, select just two object.')
            return

        dst_name = dst_dag_path.fullPathName()
        dst_fn_comp = om2.MFnSingleIndexedComponent(dst_mobj)
        dst_fn_single = om2.MFnSingleIndexedComponent(dst_mobj)
        dst_fn_mesh = om2.MFnMesh(dst_dag_path)
        src_fn_mesh = om2.MFnMesh(src_dag_path)
        num_dst_vtx = dst_fn_mesh.numVertices # all vertices count

        weights = [0.0] * num_dst_vtx
        src_normals = om2.MVectorArray().setLength(num_dst_vtx) # Almost zero vector array
        dst_normals = om2.MVectorArray(dst_fn_mesh.getNormals()) # Get Normal as MVector

        if dst_fn_comp.hasWeights:
            for i, v_id in enumerate(dst_fn_single.getElements()):
                weights[v_id] = dst_fn_comp.weight(i).influence * base_weight
                dst_pos = dst_fn_mesh.getPoint(v_id, om2.MSpace.kWorld)
                src_normals[v_id] = src_fn_mesh.getClosestNormal(dst_pos, om2.MSpace.kWorld)[0] # Return MVector
        else:
            for i, v_id in enumerate(dst_fn_single.getElements()):
                weights[v_id] = base_weight
                dst_pos = dst_fn_mesh.getPoint(v_id, om2.MSpace.kWorld)
                src_normals[v_id] = src_fn_mesh.getClosestNormal(dst_pos, om2.MSpace.kWorld)[0]

        progress = hi_utility.ProgressBar(len(dst_fn_single.getElements()))
        for i in dst_fn_single.getElements():
            dst_vtx_name = '{}.vtx[{}]'.format(dst_name, i)
            if not weights[i] == 1.0: # Avoid zero vector
                new_normal = (dst_normals[i] * (1.0 - weights[i]) + src_normals[i] * weights[i]).normal()
                #quaternion = om2.MQuaternion(dst_normals[i], src_normals[i], weights[i])
                #new_normal = dst_normals[i].rotateBy(quaternion)
            else:
                new_normal = src_normals[i]

            try:
                mc.polyNormalPerVertex(dst_vtx_name, xyz = new_normal)
                progress.count()
            except Exception as e:
                om2.MGlobal.displayError(e)
                progress.end()

        progress.end()


def lock_unlock_normals(mode):
    if mode == 'lock_selected':
        sel = mc.polyListComponentConversion(tv = True)
        mc.polyNormalPerVertex(sel, fn = True)
    elif mode == 'unlock_selected':
        sel = mc.polyListComponentConversion(tv = True)
        mc.polyNormalPerVertex(sel, ufn = True)
    else:
        return


def get_connected_faces(vtx, selected_faces):
    # 今から処理する頂点を含むフェースが選択中フェースのリストに含まれているかチェック
    # 含まれているもののフェース法線ベクトルの平均を取ったベクトルを返す
    avg_vector = om2.MVector(0, 0, 0)

    connected_faces = mc.ls(mc.polyListComponentConversion(vtx, tf = True), fl = True)

    src_set = set(selected_faces)
    tgt_set = set(connected_faces)
    matched_faces = list(src_set & tgt_set)
    face_count = len(matched_faces)

    #get all related face normal
    for face in matched_faces:
        face_normal = mc.polyInfo(face, fn = True)[0].split(' ')[-3:]
        face_normal = [float(norm) for norm in face_normal]
        avg_vector += om2.MVector(face_normal[0], face_normal[1], face_normal[2])

    normal = avg_vector / face_count
    return([normal[0], normal[1], normal[2]], face_count)


def set_weighted_normal(ignore_end = False):
    sel = mc.ls(sl = True, fl = True)
    faces = [s for s in sel if '.f[' in s] or False
    if not faces:
        mc.error('Please select faces')

    faces = mc.ls(mc.polyListComponentConversion(tf = True), fl = True)
    vtxs = mc.ls(mc.polyListComponentConversion(tv = True), fl = True)

    for vtx in vtxs:
        normal, face_count = get_connected_faces(vtx, faces)
        if face_count == 1 and ignore_end == True:
            continue
        mc.polyNormalPerVertex(vtx, normalXYZ = normal)


def get_set_normal(mode):
    # 法線の取得と設定を行う
    if mode == 'get':
        sel = mc.ls(sl = True, fl = True)
        normal = [0.0, 0.0, 0.0]
        if len(sel) > 1:
            mc.error('Please select only one component')

        if '.vtx[' in sel[0]:
            normal = mc.polyNormalPerVertex(sel[0], q = True, xyz = True)
        elif '.f[' in sel[0]:
            normal = mc.polyInfo(sel[0], fn = True)[0].split(' ')[-3:]
            normal = [float(n) for n in normal]

        mc.floatFieldGrp('hi_edit_normal_FFG', edit = True,
                          value1 = normal[0], value2 = normal[1], value3 = normal[2])
    elif mode == 'set':
        sel = mc.polyListComponentConversion(tv = True)
        normal = mc.floatFieldGrp('hi_edit_normal_FFG', q = True, v = True)
        for vtx in sel:
            mc.polyNormalPerVertex(vtx, normalXYZ = normal)


def normal_visibility(mode):
    sel = mc.ls(sl = True)
    sel = [s.split('.')[0] for s in sel]

    frag = True if mode == 'show' else False
    print(frag)
    for s in sel:
        mc.setAttr(s + '.normalType', 2)
        mc.setAttr(s + '.displayNormal', frag)


def normal_length(mode):
    sel = mc.ls(sl = True)
    sel = [s.split('.')[0] for s in sel]

    multiplier = 2.0 if mode == 'extend' else 0.5
    for s in sel:
        length = mc.getAttr(s + '.normalSize')
        mc.setAttr(s + '.normalSize', (length * multiplier))


def soft_hard_edge(mode):
    sel = mc.ls(sl=True)
    for s in sel:
        if mode == 'soft':
            mc.polySoftEdge(s, a = 180, ch = True)
        elif mode == 'hard':
            mc.polySoftEdge(s, a = 0, ch = True)

    sel = mc.polyListComponentConversion(sel, te=True)
    mc.select(sel, r=True)


def toggle_soft_edge_display():
    if mc.polyOptions(q = True, ae = True)[0]:
        mc.polyOptions(se = True)
    else:
        mc.polyOptions(ae = True)


def harden_uv_border():
    sel = mc.ls(sl=True, o=True)
    processed = []
    for s in sel:
        mc.select(s, r=True)
        mc.polyNormalPerVertex(unFreezeNormal=True)
        mc.select(s+'.map[*]', r=True)

        mel.eval('polySelectBorderShell 1')

        uv_border = mc.polyListComponentConversion(te=True)
        uv_border = mc.ls(uv_border, fl=True)

        border = []
        for u_b in uv_border:
            edge_uvs = mc.polyListComponentConversion(u_b, tuv=True)
            edge_uvs = mc.ls(edge_uvs, fl=True)

            if len(edge_uvs) > 2:
               border.append(u_b)

        if border:
            mc.polySoftEdge(border, a=False, ch=True)
            processed.extend(border)

    if processed:
        mc.select(processed, r=True)


def select_hard_edges():
    mel.eval('ConvertSelectionToEdges')
    mc.polySelectConstraint(m=3, t=0x8000, sm=True)
    mel.eval('resetPolySelectConstraint')


def hi_edit_normal_window():
    if mc.window('hi_edit_normal_window', exists = True) == True:
        mc.deleteUI('hi_edit_normal_window')

    mc.window('hi_edit_normal_window', t = 'Hi Edit Normal')

    #main layout
    mc.columnLayout(rs = 4, cat = ('both', 5), cw = 300)

    mc.columnLayout(rs = 2)
    mc.text(l = '■ Set Face Weighted Normals', fn = 'boldLabelFont')
    mc.text(l = '(only works with faces)')
    mc.rowLayout(nc = 2)
    mc.button(l = 'Set FWN', c = 'set_weighted_normal()')
    mc.button(l = 'Set FWN (Inner Only)', c = 'set_weighted_normal(True)')
    mc.setParent('..')
    mc.setParent('..')

    mc.columnLayout()
    mc.text(l = '■ Lock / Unlock Normals', fn = 'boldLabelFont')
    mc.rowLayout(nc = 2)
    mc.button(l = 'Lock Normals', c = 'lock_unlock_normals("lock_selected")')
    mc.button(l = 'Unlock Normals', c = 'lock_unlock_normals("unlock_selected")')
    mc.setParent('..')
    mc.setParent('..')

    mc.columnLayout()
    mc.text(l = '■ Soft / Hard Edge', fn = 'boldLabelFont')
    mc.rowLayout(nc = 2)
    mc.button(l = 'Soft Edge', c = 'soft_hard_edge("soft")')
    mc.button(l = 'Hard Edge', c = 'soft_hard_edge("hard")')
    mc.setParent('..')
    mc.rowLayout(nc = 1)
    mc.button(l = 'Harden UV Border', c = 'harden_uv_border()')
    mc.setParent('..')
    mc.rowLayout(nc = 2)
    mc.button(l = 'Toggle Disp', c = 'toggle_soft_edge_display()')
    mc.button(l = 'Select Hard Edges', c = 'select_hard_edges()')
    mc.setParent('..')
    mc.setParent('..')

    mc.columnLayout()
    mc.text(l = '■ Get / Set Normal', fn = 'boldLabelFont')
    mc.rowLayout(nc = 2)
    mc.button(l = 'Get Normal', c = 'get_set_normal("get")')
    mc.button(l = 'Set Normal', c = 'get_set_normal("set")')
    mc.setParent('..')
    mc.floatFieldGrp('hi_edit_normal_FFG',
                     nf = 3, l = 'Source Normal (x, y, z)',
                     cw = [(1, 110), (2, 50), (3, 50), (4, 50)],
                     value1 = 0.0, value2 = 0.0, value3 = 1.0,
                     cat = (1, 'left', 0))
    mc.setParent('..')

    mc.columnLayout()
    mc.text(l = '■ Display Normal', fn = 'boldLabelFont')
    mc.rowLayout(nc = 2)
    mc.button(l = 'Show', c = 'normal_visibility("show")')
    mc.button(l = 'Hide', c = 'normal_visibility("hide")')
    mc.setParent('..')
    mc.rowLayout(nc = 2)
    mc.button(l = 'Length x 2', c = 'normal_length("extend")')
    mc.button(l = 'Length x 0.5', c = 'normal_length("shrink")')
    mc.setParent('..')
    mc.setParent('..')

    mc.columnLayout()
    mc.text(l = '■ Transfer And Blend Normal', fn = 'boldLabelFont')
    mc.text(l = 'Select target first, then source and execute.')
    mc.text(l = 'Transfer source object\'s normals to those of target ')
    mc.text(l = 'based on soft selection weight if you use soft selection.')
    mc.rowLayout(nc = 3)
    mc.button(l = 'Transfer Blend Normals', c = lambda *args:
              BlendNormal().transfer_vertex_normals(mc.floatField('hi_edit_normal_FF', q = True, v = True)))
    mc.text(l = ' Blend Weight')
    mc.floatField('hi_edit_normal_FF', value = 1.0)
    mc.setParent('..')
    mc.setParent('..')

    mc.columnLayout()
    log_text = '2023/03/25 Add HardenUVBorder\n'
    log_text += '2022/05/16 Add BlendNormal\n'
    log_text += '2022/05/15 Add first version'
    mc.text(l = '===== Dev Log =====', fn = 'boldLabelFont')
    mc.scrollField(wordWrap = True, h = 50, w = 300, enable = False,
                   text = log_text)
    mc.setParent('..')

    #main layout end
    mc.setParent('..')

    mc.showWindow('hi_edit_normal_window')


def main():
    hi_edit_normal_window()


if __name__ == '__main__':
    main()
