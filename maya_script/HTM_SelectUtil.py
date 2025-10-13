# -*- coding: utf-8 -*-
from collections import defaultdict, OrderedDict
import maya.api.OpenMaya as om2
import maya.cmds as cmds


def filter_obj_component(sel=None):
    """
    シェイプを持つオブジェクト、頂点・フェースなどコンポーネントだけを返す

    Args:
        sel(list[str]): オブジェクト、コンポーネントなどの名前のリスト
    """
    if not sel:
        sel = cmds.ls(sl=True)

    component_type = [om2.MFn.kMeshVertComponent,
                      om2.MFn.kMeshPolygonComponent,
                      om2.MFn.kMeshEdgeComponent,
                      om2.MFn.kMeshFaceVertComponent]

    filtered = []
    for s in sel:
        sel_list = om2.MSelectionList()
        sel_list.add(s)
        dag, comp = sel_list.getComponent(0)

        # シェイプを持つトランスフォームノード
        if dag.apiType() == om2.MFn.kTransform:
            child_count = dag.childCount() # シェイプがあるかどうか
            if child_count > 0:
                for i in range(child_count):
                    child = dag.child(i)
                    if child.apiType() == om2.MFn.kMesh:
                        # シェイプが1つでもあればリストに追加する
                        filtered.append(s)
                        break
        
        # 頂点・フェース・エッジ・頂点フェース
        if comp.apiType() in component_type:
            # 頂点、フェース、エッジのどれかが選択されている
            filtered.append(s)
    
    return filtered


class DefaultOrderedDict(OrderedDict):
    """ 順番を保持するdefaultdict
    """
    def __init__(self, default_factory=None, *args, **kwargs):
        """
        Args:
            default_factory: valueの初期値、listなどを渡す
        """
        self.default_factory = default_factory
        super().__init__(*args, **kwargs)

    def __getitem__(self, key):
        if key not in self:
            # キーがない場合、default_factoryでkeyに対するvalueを生成
            if self.default_factory is None:
                raise KeyError(key)
            self[key] = self.default_factory()
        return super().__getitem__(key)


def get_vtx_component(sel_list):
    """
    オブジェクトか頂点リスト（["pCube1.vtx[0]", "pSphere1.vtx[2]"]）を受け取り、
    オブジェクトごとにdagPathとMObject（頂点コンポーネント）を返す。

    Returns:
        list[list[dagPath, MObject]]: DagPathとMObjectのリストを返す
    """
    # リストにオブジェクト名が混在していても無理やり頂点に
    vtx_list = cmds.ls(cmds.polyListComponentConversion(sel_list, tv=True))
    obj_vtx_map = DefaultOrderedDict(list)
    
    for vtx in vtx_list:
        if ".vtx[" in vtx and vtx.endswith("]"):
            split1 = vtx.split(".vtx[")
            obj_name = split1[0]
            index_str = split1[1][:-1]  # "]" を除去
            
            indices = []
            if ':' in index_str:
                # 頂点が.vtx[0:10]のような形で渡されているときの処理
                num = index_str.split(':')
                start, end = int(num[0]), int(num[1])
                indices = list(range(start, end + 1))            
            else:
                indices = [int(index_str)]
            
            obj_vtx_map[obj_name].extend(indices)

        else:
            raise ValueError(f"Invalid vertex format: {vtx}")

    result = []
    for obj_name, indices in obj_vtx_map.items():
        sel = om2.MSelectionList()
        sel.add(obj_name)
        dag = sel.getDagPath(0)

        comp_fn = om2.MFnSingleIndexedComponent()
        vtx_comp = comp_fn.create(om2.MFn.kMeshVertComponent)
        comp_fn.addElements(indices)

        result.append([dag, vtx_comp])

    return result


def get_soft_sel_weights():
    """ ソフト選択のウェイトの取得、ソフト選択が無効の場合は空のリストを返す
    """
    # ソフト選択がOFFの場合は何もしない
    if not cmds.softSelect(q=True, sse=True):
        return []
    
    # シンメトリ編集をOFFにして見た目上の選択状態と、実際に得られる選択頂点を一致させる
    symmetry_state = cmds.symmetricModelling(query=True, symmetry=True)
    if symmetry_state:
        cmds.symmetricModelling(symmetry=False)
    
    rich_sel = om2.MGlobal.getRichSelection()
    dag, comp = rich_sel.getSelection().getComponent(0)
    
    # 頂点が選択されていない場合エラー
    if not comp.hasFn(om2.MFn.kMeshVertComponent):
        om2.MGlobal.displayError(u'頂点が選択されていません')
        return
    
    fn_mesh = om2.MFnMesh(dag)
    num_vtx = fn_mesh.numVertices
    
    fn_comp = om2.MFnSingleIndexedComponent(comp)
    vtx_ids = fn_comp.getElements()
    
    # 全頂点に対するウェイトのリストを作る
    weights = [0.0] * num_vtx
    for i, vtx_id in enumerate(vtx_ids):
        weights[vtx_id] = fn_comp.weight(i).influence

    # もともとシンメトリ編集がONだった場合はONに
    if symmetry_state:
        cmds.symmetricModelling(symmetry=False)
        
    return weights