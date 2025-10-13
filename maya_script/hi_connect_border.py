import maya.cmds as mc
import maya.api.OpenMaya as om2
from re import findall


class ConnectBorder:
    @staticmethod
    def get_new_normal(src, dst):
        """
        頂点法線は、頂点と接続のあるフェースのノーマル * 頂点角度 * フェース面積
        の総和を正規化したものになる

        Args:
            src:
            dst:
        """

        # ヘルパー関数群
        def get_normal_area(obj, face_id):
            sel = om2.MSelectionList().add(obj)
            dag, _ = sel.getComponent(0)

            fn_mesh = om2.MFnMesh(dag)
            it_poly = om2.MItMeshPolygon(dag)

            normal = fn_mesh.getPolygonNormal(face_id, om2.MSpace.kWorld)
            it_poly.setIndex(face_id)
            area = it_poly.getArea()
            edges = it_poly.getEdges()

            return normal, area, edges


        def get_vtx_edge(obj, vtx_id):
            sel = om2.MSelectionList().add(obj)
            dag, _ = sel.getComponent(0)

            it_vtx = om2.MItMeshVertex(dag)
            it_vtx.setIndex(vtx_id)

            vtx_edge = it_vtx.getConnectedEdges()
            return vtx_edge


        def extract_face_id(face_name):
            # フェースの文字列からフェースIDを抽出
            face_id = face_name.split('f[')[-1][0:-1]
            return int(face_id)


        def extract_vtx_id(face_name):
            # 頂点の文字列から頂点IDを抽出
            vtx_id = face_name.split('vtx[')[-1][0:-1]
            return int(vtx_id)


        # 頂点選択（ペア）で実行
        #sel = mc.ls(sl=True, fl=True)
        sel = [src, dst]

        all_normals = []
        all_area = []
        all_angle_rad = []
        for s in sel:
            # エッジを構成する頂点を取得するようのMFｎMesh
            slist = om2.MSelectionList().add(s)
            dag, _ = slist.getComponent(0)
            fn_mesh = om2.MFnMesh(dag)

            # フェース面積計算用に、頂点と接続のあるフェースを取得
            faces = mc.ls(mc.polyListComponentConversion(s, tf=True), fl=True)

            # 頂点と接続のあるエッジの取得
            vtx_id = extract_vtx_id(s)
            vtx_edges = get_vtx_edge(s, vtx_id)

            for f in faces:
                # フェースノーマル、面積、構成するエッジの取得
                face_id = extract_face_id(f)
                normal_tmp, area_tmp, face_edges = get_normal_area(s, face_id)

                # 頂点と接続のある全エッジから、特定フェースを構成するエッジのみ抽出
                edges = set(face_edges) & set(vtx_edges)

                edge_vec = []
                for e in edges:
                    vtxs = fn_mesh.getEdgeVertices(e)
                    p1 = om2.MVector(fn_mesh.getPoint(vtxs[0]))
                    p2 = om2.MVector(fn_mesh.getPoint(vtxs[1]))

                    # 現在の頂点を基準に方向を取得
                    if vtx_id == vtxs[0]:
                        edge_vec.append((p2 - p1))
                    else:
                        edge_vec.append((p1 - p2))

                all_angle_rad.append(edge_vec[0].angle(edge_vec[1]))
                all_normals.append(normal_tmp)
                all_area.append(area_tmp)

        # 法線計算
        normal_sum = om2.MVector(0, 0, 0)
        for n, a, ar in zip(all_normals, all_area, all_angle_rad):
            normal_sum += n * a * ar

        new_normal = normal_sum.normal()
        #mc.polyNormalPerVertex(sel[0], xyz=list(new_normal))
        #mc.polyNormalPerVertex(sel[1], xyz=list(new_normal))
        return new_normal


    @staticmethod
    def transfer_skin_weights(src_vtx, dst_vtx):
        """
        スキンウェイトをある頂点から別の頂点に転送する

        Args:
            src_vtx(str): source vtx, "xxx.vtx[x]"
            dst_vtx(str): destination vtx, "xxx.vtx[x]"
        """
        # 転送元頂点のスキンクラスターを取得
        src_mesh = src_vtx.split('.')[0]
        src_history = mc.listHistory(src_mesh, pruneDagObjects=True)
        src_skin_cluster = mc.ls(src_history, type='skinCluster')[0]

        # 転送先頂点のスキンクラスターを取得
        dst_mesh = dst_vtx.split('.')[0]
        dst_history = mc.listHistory(dst_mesh, pruneDagObjects=True)
        dst_skin_cluster = mc.ls(dst_history, type='skinCluster')[0]

        if not src_skin_cluster:
            om2.MGlobal.displayError(f'スキンクラスターが見つかりませんでした（転送元: {src_vtx}）')
            return

        if not dst_skin_cluster:
            om2.MGlobal.displayError(f'スキンクラスターが見つかりませんでした（転送先: {dst_vtx}）')
            return

        # 元の頂点のスキンウェイトを取得
        src_joints = mc.skinCluster(src_skin_cluster, query=True, influence=True)
        src_weights = mc.skinPercent(src_skin_cluster, src_vtx, query=True, value=True)

        # 転送先の頂点にスキンウェイトを適用
        for joint, weight in zip(src_joints, src_weights):
            mc.skinPercent(dst_skin_cluster, dst_vtx, transformValue=[(joint, weight)])



    @staticmethod
    def get_averaged_normal(src, dst, mode='average'):
        """
        Average normal

        Args:
            src(str): source vertex, "xxx.vtx[x]"
            dst(str): destination vertex, "xxx.vtx[x]"
        """
        sel = om2.MSelectionList()
        ids = []
        for item in [src, dst]:
            obj, comp = item.split('.')
            ids.append(int(findall('[0-9]+', comp)[-1]))
            sel.add(obj)

        dag_s, dag_d = sel.getDagPath(0), sel.getDagPath(1)

        it_vtx_s = om2.MItMeshVertex(dag_s)
        it_vtx_d = om2.MItMeshVertex(dag_d)

        fn_trans_s = om2.MFnTransform(dag_s)
        fn_trans_d = om2.MFnTransform(dag_d)

        inv_mtx_s = fn_trans_s.rotation(asQuaternion=True, space=om2.MSpace.kWorld).asMatrix().inverse()
        inv_mtx_d = fn_trans_d.rotation(asQuaternion=True, space=om2.MSpace.kWorld).asMatrix().inverse()

        it_vtx_s.setIndex(ids[0])
        it_vtx_d.setIndex(ids[1])

        nrm_s = it_vtx_s.getNormal(space=om2.MSpace.kWorld)
        nrm_d = it_vtx_d.getNormal(space=om2.MSpace.kWorld)

        pos = it_vtx_s.position(space=om2.MSpace.kWorld)
        if mode == 'average':
            new_nrm_s = ((nrm_s + nrm_d) / 2) * inv_mtx_s
            new_nrm_d = ((nrm_s + nrm_d) / 2) * inv_mtx_d
        elif mode == 'use_src':
            new_nrm_s = nrm_s * inv_mtx_s
            new_nrm_d = nrm_s * inv_mtx_d
        elif mode == 'use_dst':
            new_nrm_s = nrm_d * inv_mtx_s
            new_nrm_d = nrm_d * inv_mtx_d

        return new_nrm_s, new_nrm_d


    @staticmethod
    def get_closest_border_vertex(threshold=0.5):
        ''' Get closest border vertex normal, name, position
            1st object selected --> for editing
            2nd object selected --> for src

        Params:
            pos(int): vertex position to move to a closest vertex

        Returns:
        '''

        # 選択順正しいか問題。cmds.ls(os=Ture)を使うべきなのか？
        # ANS : getActiveSelectionList() は順番考慮してる
        sel = om2.MGlobal.getActiveSelectionList()
        if not 2 == sel.length():
            om2.MGlobal.displayError('Please select JUST TWO objects.')
            return

        dag_src = sel.getDagPath(0) # src object
        dag_dst = sel.getDagPath(1) # an object to be edited
        name_src = str(dag_src)
        name_dst = str(dag_dst)

        fn_mesh_src = om2.MFnMesh(dag_src) # to get closest point
        it_poly_src = om2.MItMeshPolygon(dag_src) # to get vertex from face
        it_vtx_dst = om2.MItMeshVertex(dag_dst) # to get position and normal
        it_edge_dst = om2.MItMeshEdge(dag_dst) # to get border edges

        # Get boundary vertex id
        vtx_id_dst = list()
        for e in it_edge_dst:
            if e.onBoundary():
                # Each edge must have two vertices.
                vtx_id_dst.append(it_edge_dst.vertexId(0))
                vtx_id_dst.append(it_edge_dst.vertexId(1))
        vtx_id_dst = list(set(vtx_id_dst)) # Remove multiple id

        # Destination vertices list
        vtx_name_dst = ['{}.vtx[{}]'.format(name_dst, v) for v in vtx_id_dst]

        vtx_id_src = []
        for id in vtx_id_dst:
            # Get closest pos and face id.
            it_vtx_dst.setIndex(id)
            pos = it_vtx_dst.position(om2.MSpace.kWorld)
            closest_pos, f_id = fn_mesh_src.getClosestPoint(pos, om2.MSpace.kWorld)

            # From face id(f_id), get a losest vertex.
            it_poly_src.setIndex(f_id)
            vtx_id_list = it_poly_src.getVertices()
            vtx_pos_list = it_poly_src.getPoints(om2.MSpace.kWorld)

            dist_list = [pos.distanceTo(v_pos) for v_pos in vtx_pos_list]
            if min(dist_list) < threshold:
                min_v_id = dist_list.index(min(dist_list)) # get index of a closest vertex
                vtx_id_src.append(vtx_id_list[min_v_id])

            # If no vertex is found within specified threshold.
            else:
                vtx_id_src.append(None)

        if all(val == -1 for val in vtx_id_src):
            om2.MGlobal.displayError('No closest vertices were fould.')
            return

        # Generate src vtx name by their id.
        vtx_name_src = ['{}.vtx[{}]'.format(name_src, v) if not v == None else None for v in vtx_id_src]

        return vtx_name_dst, vtx_name_src


    @classmethod
    def connect_border(cls, threshold, connect=False, pos=True, normal=True, weight=False):
        """
        """
        # re select transform node, which is temporal
        sel = mc.ls(sl=True)
        obj = []
        for s in sel:
            obj_name = s.split('.')[0]
            if not obj or obj_name not in obj:
                obj.append(obj_name)
        mc.select(obj, r=True)

        # main
        vtx_src, vtx_dst = cls.get_closest_border_vertex(threshold)
        if connect:
            for src, dst in zip(vtx_src, vtx_dst):
                if src == None or dst == None:
                    continue

                # Get values
                if pos:
                    new_pos = mc.xform(src, q=True, ws=True, t=True)
                    mc.xform(dst, ws=True, t=list(new_pos[0:3]))

                # Normal
                if normal:
                    #new_nrm_s, new_nrm_d = cls.get_averaged_normal(src, dst, mode='average')
                    new_normal = cls.get_new_normal(src, dst)
                    mc.polyNormalPerVertex(src, xyz=list(new_normal))
                    mc.polyNormalPerVertex(dst, xyz=list(new_normal))

                # Weight
                if weight:
                    cls.transfer_skin_weights(src, dst)

        mc.selectType(ocm=True, vertex=True)
        mc.select(cl=True)
        mc.select(vtx_dst, vtx_src, r=True)
        mc.hilite(obj)


if '__main__' == __name__:
    ConnectBorder.connect_border(1.0, connect=True, weight=True)

