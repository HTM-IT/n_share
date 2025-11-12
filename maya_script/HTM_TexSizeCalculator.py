# -*- coding: utf-8 -*-
import math

import maya.api.OpenMaya as om2
from maya import cmds

from maya.app.general.mayaMixin import MayaQWidgetBaseMixin
from PySide2.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QHeaderView,
                               QPushButton, QLabel, QSpinBox, QTableWidget)


class HTM_TexSizeCalculator(MayaQWidgetBaseMixin, QWidget):
    WIN_TITLE = 'HTM Texture Size Calculator'
    
    def __init__(self, parent=None):
        super(HTM_TexSizeCalculator, self).__init__(parent)
        self.setWindowTitle(self.WIN_TITLE)
        
        main_layout = QVBoxLayout()
        layout = QHBoxLayout()

        # 実行部分        
        label = QLabel('PPM (pixel / meter):')
        self.spinbox = QSpinBox()
        self.spinbox.setMinimum(1)
        self.spinbox.setMaximum(100000)        
        self.spinbox.setValue(128)
        btn = QPushButton('Execute')
        btn.clicked.connect(self.calc_tex_size_clbk)
        
        layout.addWidget(label)
        layout.addWidget(self.spinbox)

        main_layout.addLayout(layout)
        main_layout.addWidget(btn)
        
        # リスト表示
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels([u'オブジェクト', u'マテリアル', 
                                         u'サイズ(プリセット)', u'サイズ'])

        # ヘッダーをウィンドウサイズに合わせて拡縮
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        
        main_layout.addWidget(table)
        self.setLayout(main_layout)

    def calc_tex_size_clbk(self):
        ppm = self.spinbox.value()
        tex_size = calc_tex_size(ppm=ppm)


def nearest_value(x):
    size_preset = [16, 32, 64, 128, 256, 512, 768,
                   1024, 1280, 1536, 1792, 2048]
    return min(size_preset, key=lambda v: abs(v - x))

def calc_tex_size(ppm=128):
    """
    conversion = {'mm':0.001, 'cm':0.01, 'm':1, 'km':1000}
    unit = cmds.currentUnit(q=True, linear=True )

    try:
        # Mayaの単位によって変換する
        ppm = ppm * conversion[unit]
    except:
        return
    """
    sel = om2.MGlobal.getActiveSelectionList()
    dag, comp = sel.getComponent(0)
    fn_mesh = om2.MFnMesh(dag)
    it_poly = om2.MItMeshPolygon(dag)
    
    face_area = 0
    uv_area = 0
    for poly in it_poly:
        face_area += poly.getArea()
        uv_area += poly.getUVArea()
    
    tex_size = ppm * math.sqrt(face_area / uv_area)
    tex_size_rounded = nearest_value(tex_size) 
    
    print('# -----------------------------------------')
    print(math.sqrt(face_area / uv_area))
    print('# Face Area : {}'.format(face_area))
    print('# UV Area : {}'.format(uv_area))
    print('# Texture Size : {:.2f}'.format(tex_size))
    print('# Texture Size Rounded : {}'.format(tex_size_rounded))
    print('# -----------------------------------------')
    
    return tex_size
    
if __name__ == '__main__':
    cls = HTM_TexSizeCalculator()
    cls.show()