import maya.cmds as mc
import maya.api.OpenMaya as om2
from re import findall

class ConnectBorder:
    @classmethod
    def get_averaged_normal(cls, src, dst, mode='average'):
        """ Average normal

        Param:
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

    @classmethod
    def get_closest_border_vertex(cls, threshold=0.5):
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
                    new_nrm_s, new_nrm_d = cls.get_averaged_normal(src, dst, mode='average')
                    mc.polyNormalPerVertex(src, xyz=list(new_nrm_s))
                    mc.polyNormalPerVertex(dst, xyz=list(new_nrm_d))

                # Weight
                if weight:
                   pass

        mc.selectType(ocm=True, vertex=True)
        mc.select(cl=True)
        mc.select(vtx_dst, vtx_src, r=True)
        mc.hilite(obj)


ConnectBorder.connect_border(1.0, connect=True)