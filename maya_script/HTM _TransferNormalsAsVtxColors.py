import webbrowser
import maya.cmds as mc
import maya.mel as mel
import maya.api.OpenMaya as om2
from PySide2 import QtWidgets, QtCore, QtGui
from maya.app.general.mayaMixin import MayaQWidgetBaseMixin


class ProgressBar:
    def __init__(self, max_count):
        # メインプログレスバーの取得
        self.bar = mel.eval('$tmp = $gMainProgressBar')
        cmds.progressBar(
            self.bar,
            edit=True,
            beginProgress=True,
            isInterruptable=False,
            status=u'処理中...',
            minValue=0,
            maxValue=max_count
        )

    def step(self):
        cmds.progressBar(self.bar, edit=True, step=1)

    def end(self):
        cmds.progressBar(self.bar, edit=True, endProgress=True)
        

class HTM_TransferNormalsAsVtxColors(MayaQWidgetBaseMixin, QtWidgets.QMainWindow):
    WINDOW_NAME = u'HTMTransferNormalsAsVtxColors'

    def __init__(self, parent=None):
        self.delete_existing_window()
        super(HTM_TransferNormalsAsVtxColors, self).__init__(parent)
        self.setObjectName(self.WINDOW_NAME)
        self.setWindowTitle('HTM Transfer Normals As Vtx Colors')
        self.setMinimumSize(250, 100)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.init_ui()
        self.init_menu()

    def delete_existing_window(self):
        for widget in QtWidgets.QApplication.allWidgets():
            if widget.objectName() == self.WINDOW_NAME:
                widget.close()
                widget.deleteLater()

    def init_ui(self):
        # Central Widget & Layout
        central_widget = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(central_widget)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        
        # Checkboxes
        self.check_a = QtWidgets.QCheckBox(u'カラーを0-1に収める')
        self.check_a.setChecked(True)
        self.check_b = QtWidgets.QCheckBox(u'接線空間のベクトルにする')
        self.check_b.setChecked(True)
        self.check_c = QtWidgets.QCheckBox(u'Gチャンネルを反転する')
        self.check_c.setChecked(True)

        # Button
        self.print_button = QtWidgets.QPushButton(u'法線の転送を実行')
        self.print_button.clicked.connect(self.main)

        # Add widgets to layout
        layout.addWidget(self.check_a)
        layout.addWidget(self.check_b)
        layout.addWidget(self.check_c)
        layout.addWidget(self.print_button)

        self.setCentralWidget(central_widget)

    def init_menu(self):
        menubar = self.menuBar()
        help_menu = menubar.addMenu('ヘルプ')

        show_help = QtWidgets.QAction(u'ヘルプ', self)
        url = r'https://www.google.com'
        show_help.triggered.connect(lambda:webbrowser.open(url))

        help_menu.addAction(show_help)


    def main(self):
        range_01 = self.check_a.isChecked()
        tangent_space = self.check_b.isChecked()
        flip_g = self.check_c.isChecked()
        cls = TransferNormasAsColor()
        cls.main(range_01, tangent_space, flip_g)


class TransferNormasAsColor():
    def main(self, range_01, tangent_space, flip_g):
        val = 1.0
        if flip_g:
            val = -1.0
        
        sel = mc.ls(sl=True, tr=True, fl=True)
        
        # 転送元
        src = om2.MGlobal.getSelectionListByName(sel[0])
        dag_src = src.getDagPath(0)
        fn_mesh_src = om2.MFnMesh(dag_src)
        
        
        for s in sel[1:]:
            # カラー
            colors = []
            face_ids = []
            vtx_ids = []
        
            # 転送先
            dst = om2.MGlobal.getSelectionListByName(s)
            dag_dst = dst.getDagPath(0)
            fn_mesh_dst = om2.MFnMesh(dag_dst)
            it_poly_dst = om2.MItMeshPolygon(dag_dst)
            num_faces = fn_mesh_dst.numPolygons
        
            # 近接ノーマル取得
            # この処理が一番重いのでここでプログレスバーを動かす
            progress = ProgressBar(fn_mesh_dst.numVertices)
            closest_normals = []
            for pos in fn_mesh_dst.getPoints(om2.MSpace.kWorld):
                temp = om2.MFloatVector(fn_mesh_src.getClosestNormal(pos, om2.MSpace.kWorld)[0])
                closest_normals.append(temp)
                progress.step()
            progress.end()    
            
        
            # 近接ノーマルのリスト参照用の頂点のリスト
            vertex_id_list = []
            for ip in it_poly_dst:
                temp = ip.getVertices()
                vertex_id_list.append(temp)
        
            # フェースの数だけ処理する
            for i in range(num_faces):
                if tangent_space:
                    # ワールド法線・接線・従法線を取得(接線空間への変換用)
                    normals = fn_mesh_dst.getFaceVertexNormals(i, om2.MSpace.kWorld)
                    tangents = fn_mesh_dst.getFaceVertexTangents(i, om2.MSpace.kWorld)
                    binormals = [n ^ t for n, t in zip(normals, tangents)]
                    
                    # 各頂点フェースに対応する最近接ノーマルのリストを取得
                    src_vecs = [closest_normals[id] for id in vertex_id_list[i]]
                    
                    new_normals_ts = []
                    for vec, t, b, n in zip(src_vecs, tangents, binormals, normals):
                        x = vec * t
                        y = vec * b * val # 反転が有効な場合valは-1.0になっている
                        z = vec * n
            
                        if range_01:
                            x = (x + 1.0) * 0.5
                            y = (y + 1.0) * 0.5
                            z = (z + 1.0) * 0.5
                                
                        new_normals_ts.append(om2.MVector(x, y, z))
                        
                    colors_temp = [om2.MColor((n.x, n.y, n.z)) for n in new_normals_ts]
        
                else:
                    # 各頂点フェースに対応する最近接ノーマルのリストを取得
                    new_normals_ws = [closest_normals[id] for id in vertex_id_list[i]]    
                    colors_temp = [om2.MColor((n.x, n.y, n.z)) for n in new_normals_ws]
                    
                # カラー設定用のリスト
                colors.extend(colors_temp)
                face_ids.extend([i] * len(colors_temp))
                vtx_ids.extend(vertex_id_list[i])
                            
            fn_mesh_dst.setFaceVertexColors(colors, face_ids, vtx_ids)

if __name__ == '__main__':
    # 実行
    window = CheckBoxMainWindow()
    window.show()
