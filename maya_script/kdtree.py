# -*- coding: utf-8 -*-
import maya.cmds as cmds
import maya.api.OpenMaya as om2


class CustomMPoint(om2.MPoint):
    """ MPointにIndexを追加したクラス """
    def __init__(self, index, *args, **kwargs):
        """
        Args:
            index(int):頂点インデックス、UVインデックスなど
        """
        super(CustomMPoint, self).__init__(*args, **kwargs)
        self.index = index


class KDNode:
    """ KDTreeのノード """
    def __init__(self, point, index, axis, left=None, right=None):
        self.point = point  # 座標（例：[x, y]）
        self.index = index  # 頂点、UVなどのインデックス
        self.axis = axis    # 軸（0:x, 1:y, 2:z）
        self.left = left    # 左
        self.right = right  # 右


def build_kdtree(points, depth=0):
    """　KDTreeのノードの構築
    Args:
        points(list[list[float], int]):座標とそのデックスのリスト
    """
    if not points:
        return None

    k = len(points[0][0])  # 次元数
    axis = depth % k
    points.sort(key=lambda x: x[0][axis])
    median = len(points) // 2

    return KDNode(
        point=points[median][0],
        index=points[median][1],
        axis=axis,
        left=build_kdtree(points[:median], depth + 1),
        right=build_kdtree(points[median + 1:], depth + 1)
    )


def distance_squared(p0, p1):
    """ 距離の2乗を返す
    Args:
        p0(list[float]):座標0
        p1(list[float]):座標1
    """
    return sum((a - b) ** 2 for a, b in zip(p0, p1))


def nearest_neighbor(node, target, result=None):
    """ 最近接点を取得
    Args:
        node(KDNode):KDノード
        target(list[float]):検索の基準となる座標
        result(list[list[float], int]):現在の最近接点の座標とインデックス
    """
    if node is None:
        return result

    dist = distance_squared(target, node.point)
    if result is None or dist < distance_squared(target, result[0]):
        result = [node.point, node.index]

    axis = node.axis
    diff = target[axis] - node.point[axis]

    # 先に探索する側を決める
    # node.pointよりも大きい当りがrightに、小さい値がleftに入っているので以下のようになる
    next_branch = node.left if diff < 0 else node.right
    result = nearest_neighbor(next_branch, target, result)

    # 距離が分割面をまたぐ可能性がある場合
    if diff ** 2 < distance_squared(target, result[0]):
        other_branch = node.right if diff < 0 else node.left
        result = nearest_neighbor(other_branch, target, result)

    return result

import time
# サンプルコード
if __name__ == '__main__':

    sel = om2.MSelectionList()
    sel.add(cmds.ls(sl=True)[0])
    dag, _ = sel.getComponent(0)
    fn_mesh = om2.MFnMesh(dag)
    points = fn_mesh.getPoints()

    grid_vtx_pos_list = [[list(p),i] for i, p in enumerate(points)]

    start = time.time()
    #points = [CustomMPoint(id, pos) for id, pos in enumerate(poslist)]
    kdtree = build_kdtree(grid_vtx_pos_list)
    end = time.time()
    print(end - start, 'sec')

    target = cmds.xform(cmds.ls(sl=True)[1], q=True, ws=True, t=True)
    pos, index = nearest_neighbor(kdtree, target)
    cmds.select(grid + f'.vtx[{index}]')

    # Result: [0.19999998807907104, 0.0, -0.10000002384185791] # 
