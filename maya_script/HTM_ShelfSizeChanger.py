# -*- coding: utf-8 -*-
import maya.mel as mel
import maya.cmds as mc
from PySide2.QtWidgets import *
from maya.app.general.mayaMixin import MayaQWidgetBaseMixin
from shiboken2 import wrapInstance
from maya import OpenMayaUI as omui

python_version = sys.version_info.major
win_title = 'HTM Shelf Size Changer'

class HTM_ShelfSizeChanger(MayaQWidgetBaseMixin, QWidget):
    # Mayaのシェルフの名前
    shelf_name = 'ShelfLayout'

    def __init__(self, parent=None, *args, **kwargs):
        # すでにあったら閉じる
        self.close_window()

        # 初期化
        super(HTM_ShelfSizeChanger, self).__init__(parent=parent, *args, **kwargs)
        self.init_ui()

    def close_window(self):
        main_window_ptr = omui.MQtUtil.mainWindow()
        if python_version == 3:
            main_window = wrapInstance(int(main_window_ptr), QMainWindow)
        else:
            main_window = wrapInstance(long(main_window_ptr), QMainWindow)

        for child in main_window.children():
            if isinstance(child, QWidget) and child.windowTitle() == win_title:
                child.close()

    def init_ui(self):
        # set window status
        self.setWindowTitle(win_title)
        self.setMinimumSize(200, 100)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        pb_size_up = QPushButton(r'サイズを増やす')
        pb_size_up.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        pb_size_up.clicked.connect(lambda:self.size_change('sizeup'))

        pb_size_down = QPushButton(r'サイズをもとに戻す')
        pb_size_down.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        pb_size_down.clicked.connect(lambda:self.size_change('sizedown'))

        main_layout.addWidget(pb_size_up)
        main_layout.addWidget(pb_size_down)

        self.setLayout(main_layout)
        #self.setCentralWidget(widget)

    def size_change(self, mode='sizeup'):
        default_size = 64
        add_size = 33

        if mode == 'sizeup':
            cur_size = mc.shelfTabLayout(self.shelf_name, q=True, h=True)
            new_size = cur_size + add_size
            mc.shelfTabLayout('ShelfLayout', e=True, h=new_size)
        elif mode == 'sizedown':
            mc.shelfTabLayout('ShelfLayout', e=True, h=default_size)

if __name__ == '__main__':
    htm = HTM_ShelfSizeChanger()
    htm.show()

