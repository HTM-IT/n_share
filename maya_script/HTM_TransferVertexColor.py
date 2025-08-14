import math

import maya.api.OpenMaya as om2
import maya.cmds as mc

from PySide2.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QWidget
from maya.app.general.mayaMixin import MayaQWidgetBaseMixin


class CustomUI(MayaQWidgetBaseMixin, QMainWindow):
    def __init__(self, parent=None):
        super(CustomUI, self).__init__(parent)
        self.setWindowTitle('HTM_TransferVertexColor | 頂点カラー転送')

        # セントラルウィジェットとレイアウトの設定
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # ボタン1の作成と接続
        self.button1 = QPushButton('頂点カラーを転送する')
        self.button1.clicked.connect(self.print_button1)
        self.layout.addWidget(self.button1)

        # ボタン2の作成と接続
        self.button2 = QPushButton('カラーセット1の削除')
        self.button2.clicked.connect(self.print_button2)
        self.layout.addWidget(self.button2)

    def print_button1(self):
        transfer_vertex_color()

    def print_button2(self):
        print('Remove Vertex Color Set 1')


def in_triangle(base_point, points):
    u""" 三角形と点の当たり判定、同一平面上に各点がある前提
    param:
        base_point(MPoint):
        points(MPoint):
    """
    vec_10 = points[1] - points[0]
    vec_1p = points[1] - base_point

    vec_21 = points[2] - points[1]
    vec_2p = points[2] - base_point

    vec_02 = points[0] - points[2]
    vec_0p = points[0] - base_point

    cross_1 = vec_10 ^ vec_1p
    cross_2 = vec_21 ^ vec_2p
    cross_3 = vec_02 ^ vec_0p

    dot_12 = cross_1 * cross_2
    dot_13 = cross_1 * cross_3

    if dot_12 >= 0 and dot_13 >= 0:
        return True

    return False


def get_vertex_pos_weight(base_point, points):
    u"""
    param:
        base_point(MPoint):
        points(MPoint):
    """
    dist = 0
    for pos in points:
        dist_temp = (base_point - pos).length()
        dist += dist_temp

    weight = []
    weight_total = 0
    for pos in points:
        dist_temp = (base_point - pos).length()
        if dist_temp == 0:
            dist_temp = 1 / sys.maxsize
        weight.append(dist / dist_temp)
        weight_total += weight[-1]

    weight_new = []
    for w in weight:
        weight_new.append(w / weight_total)

    for i, w in enumerate(weight_new):
        if math.isclose(w, 0, abs_tol=1e-10):
            weight_new[i] = 0

    return weight_new



def transfer_vertex_color():
    u""" 頂点カラー転送
    """
    sel = om2.MGlobal.getActiveSelectionList()

    if sel.length() is not 2:
        om2.MGlobal.displayError(u'転送元・転送先となるオブジェクトを選択して実行してください')
        return

    # ------------------------------------
    # 転送元
    dag_src = sel.getDagPath(0)
    fn_mesh_src = om2.MFnMesh(dag_src)

    tris, vtxs = fn_mesh_src.getTriangles()
    colors_src = fn_mesh_src.getVertexColors()
    points_src = fn_mesh_src.getPoints()

    # 三角フェースとその頂点のリストを整形
    tris_face_vtxs_src = []
    counter = 0
    for num_tris in tris:
        temp = []
        for _ in range(num_tris):
            temp.append([vtxs[counter], vtxs[counter+1], vtxs[counter+2]])
            counter += 3

        tris_face_vtxs_src.append(temp)


    # ------------------------------------
    # 転送先
    dag_dst = sel.getDagPath(1)
    fn_mesh_dst = om2.MFnMesh(dag_dst)
    fn_trans_dst = om2.MFnTransform(dag_dst)
    trans = dag_dst.inclusiveMatrix()

    vtxs_pos_dst = fn_mesh_dst.getPoints()
    vtxs_pos_dst = [pos * trans for pos in vtxs_pos_dst] # ワールド行列をかけておく
    vtxs_nrm_dst = fn_mesh_dst.getNormals(om2.MSpace.kWorld)


    # ------------------------------------
    # 交差判定取って頂点カラーを転送する処理
    index = 0
    new_colors = []
    for pos, nrm in zip(vtxs_pos_dst, vtxs_nrm_dst):
        # 一旦最短距離の点を取ってきて、そこへ向けたベクトルで交差を取る
        closest_pos, face_id = fn_mesh_src.getClosestPoint(pos, om2.MSpace.kWorld)

        vtxs_grp = tris_face_vtxs_src[face_id]
        not_found = True
        for triangle_id, vtxs in enumerate(vtxs_grp):
            points = [points_src[id] for id in vtxs]
            if in_triangle(closest_pos, points):
                weights = get_vertex_pos_weight(closest_pos, points)
                v0, v1, v2 = tris_face_vtxs_src[face_id][triangle_id]
                w0, w1, w2 = weights

                color_temp = colors_src[v0] * w0 + colors_src[v1] * w1 + colors_src[v2] * w2
                new_colors.append(color_temp)
                not_found = False
                break
        else:
            new_colors.append(om2.MColor([0, 0, 0, 1]))

        #return
        """
        ray_dir = om2.MFloatVector(closest_pos - pos)

        distance = ray_dir.length() + 1.0 # 1.0足してるのはベクトルの長さが足りないかもしれないから
        ray_source = om2.MFloatPoint(pos)

        out = fn_mesh_src.closestIntersection(ray_source, ray_dir, om2.MSpace.kWorld, distance, True)
        if out is None:
            new_colors.append(om2.MColor([0, 0, 0]))
            continue

        _, _, face, tris, w0, w1 = out
        w2 = 1 - w0 - w1

        v0, v1, v2 = tris_face_vtxs_src[face][tris]

        color_temp = colors_src[v0] * w0 + colors_src[v1] * w1 + colors_src[v2] * w2
        new_colors.append(color_temp)
        """

    print(len(new_colors), len(vtxs_pos_dst))
    fn_mesh_dst.setVertexColors(new_colors, range(len(vtxs_pos_dst)))


# UI表示
def show_ui():
    global custom_ui
    custom_ui = CustomUI()
    custom_ui.show()

if __name__ == '__main__':
    show_ui()
