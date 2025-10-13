# -*- coding: utf-8 -*-
from __future__ import with_statement, print_function

from PySide2.QtWidgets import *
from PySide2 import QtCore
from shiboken2 import wrapInstance

from maya.app.general.mayaMixin import MayaQWidgetBaseMixin
import maya.OpenMayaUI as omui


# --------------------------------------------------------
# メインウィンドウ
# --------------------------------------------------------
class HTM_WindowBase(MayaQWidgetBaseMixin, QMainWindow):
    def __init__(self, window_title, parent=None):
        self.window_title = window_title
        self.geom = self.delete_existing_ui()

        super(HTM_WindowBase, self).__init__(parent)
        self.setWindowTitle(self.window_title)
        self.setObjectName(self.window_title)

        self.init_ui()
        self.show()

    def delete_existing_ui(self):
        main_window_ptr = omui.MQtUtil.mainWindow()
        main_window = wrapInstance(int(main_window_ptr), QMainWindow)

        geom = None
        for child in main_window.findChildren(QMainWindow):
            if child.windowTitle() == self.window_title:
                geom = child.geometry()
                child.close()
                
        return geom

    def setWindowSize(self, width=300, height=300):
        if not self.geom is None:
            self.setGeometry(self.geom)
        else:
            self.resize(width, height)
        
    def add_menu(self):
        pass

    def init_ui(self):
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        
        self.main_layout = QVBoxLayout()
        self.main_layout.setMargin(4)
        self.main_layout.setSpacing(4)
        self.main_widget.setLayout(self.main_layout)
        
    def closeEvent(self, event):
        #super(HTM_WindowBase, self).closeEvent(event)
        self.deleteLater() # インスタンスを完全に消す


# --------------------------------------------------------
# レイアウト・ウィジェット
# --------------------------------------------------------
class LayoutBase(object):
    """ レイアウトのコンテキストマネージャーのための基底クラス """
    def __init__(self, parent, layout_cls):
        self.parent = parent
        self.layout = layout_cls()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if isinstance(self.parent, QWidget):
            self.parent.setLayout(self.layout)
        elif isinstance(self.parent, QLayout):
            self.parent.addLayout(self.layout)
        else:
            raise TypeError('parent must be QWidget or QLayout')

    def addWidget(self, widget, *args, **kwargs):
        self.layout.addWidget(widget, *args, **kwargs)

    def addLayout(self, layout, *args, **kwargs):
        self.layout.addLayout(layout, *args, **kwargs)

    def setSpacingAndMargins(self, spacing=4, margin=4):
        self.layout.setSpacing(spacing)
        self.layout.setContentsMargins(margin, margin, margin, margin)
        

class HTM_HBoxLayout(LayoutBase):
    """ HBoxLayoutのコンテキストマネージャー """
    def __init__(self, parent):
        super(HTM_HBoxLayout, self).__init__(parent, QHBoxLayout)


class HTM_VBoxLayout(LayoutBase):
    """ HVoxLayoutのコンテキストマネージャー """
    def __init__(self, parent):
        super(HTM_VBoxLayout, self).__init__(parent, QVBoxLayout)


class HTM_GridLayout(LayoutBase):
    """ GridLayoutのコンテキストマネージャー """
    def __init__(self, parent):
        super(HTM_GridLayout, self).__init__(parent, QGridLayout)


class HTM_GroupBox(QGroupBox, object):
    """ GroupBoxのコンテキストマネージャー """
    def __init__(self, title='', parent=None):
        super(HTM_GroupBox, self).__init__(title)
        self.parent = parent

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if isinstance(self.parent, QLayout):
            self.parent.addWidget(self)
        else:
            raise TypeError('parent must be QLayout')


class HTM_HSeparator(QFrame, object):
    """ 横方向のセパレーター """
    def __init__(self):
        super(HTM_HSeparator, self).__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)


class HTM_VSeparator(QFrame, object):
    """ 縦方向のセパレーター """
    def __init__(self):
        super(HTM_VSeparator, self).__init__()
        self.setFrameShape(QFrame.VLine)
        self.setFrameShadow(QFrame.Sunken)

     
class HTM_PushButton(QPushButton, object):
    """ カスタムボタン
    """
    def __init__(self, title='', parent=None):
        super(HTM_PushButton, self).__init__(title, parent)
        self.right_click_callback = None
        
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(self.minimumSizeHint())
        
        self.setStyleSheet("""
            QPushButton {
                background-color: palette(button);
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1C44E0;
            }
            QPushButton:pressed {
                background-color: #222222;
            }
        """)

    def setLeftClickCallback(self, callback):
        # 左クリックの処理
        self.clicked.connect(callback)
    
    def setRightClickCallback(self, callback):
        # 右クリックの処理、コールバックの登録だけする
        self.right_click_callback = callback

    def mousePressEvent(self, event):
        # クリックの種類によって処理を分ける、とりあえず右クリック対応
        if event.button() == QtCore.Qt.RightButton:
            if self.right_click_callback:
                self.right_click_callback()
            return
        super(HTM_PushButton, self).mousePressEvent(event)


"""
class HTM_GroupBox(QGroupBox):
    def __init__(self, title='', parent=None, layout_cls=QVBoxLayout):
        super(HTM_GroupBox, self).__init__(title, parent)
        self._layout = layout_cls()
        self.setMargins(4)
        self.setLayout(self._layout)

    def addWidget(self, widget, *args, **kwargs):
        self._layout.addWidget(widget, *args, **kwargs)

    def addLayout(self, layout, *args, **kwargs):
        self._layout.addLayout(layout, *args, **kwargs)
        
    def setMargins(self, num):
        self._layout.setContentsMargins(num, num, num, num)
        self._layout.setSpacing(num)
"""


# --------------------------------------------------------
# サンプルコード
# --------------------------------------------------------
class HTM_EditNormalTools(HTM_WindowBase):
    def __init__(self, parent=None):
        super(HTM_EditNormalTools, self).__init__('HTM Tools')
        self.setWindowSize(width=500, height=200)

        with HTM_GroupBox(u'法線のコピペ', parent=self.main_layout) as gb:
            with HTM_HBoxLayout(gb) as l:
                l.setSpacingAndMargins()
                btn1 = HTM_PushButton(u'法線のコピー', self)
                btn1.setLeftClickCallback(lambda:print('Push'))
                btn1.setRightClickCallback(lambda:print('Pull'))
                btn2 = HTM_PushButton(u'法線のペースト', self)
                l.addWidget(btn1)
                l.addWidget(HTM_VSeparator())
                l.addWidget(btn2)

        with HTM_GroupBox(u'法線のスムース', parent=self.main_layout) as gb2:
            with HTM_GridLayout(gb2) as l2:
                l2.setSpacingAndMargins()
                le = QLineEdit()
                btn3 = HTM_PushButton(u'法線のフリーズ', self)
                btn4 = HTM_PushButton(u'法線のスムース', self)
                l2.addWidget(le, 0, 0, 1, 2)
                l2.addWidget(btn3, 1, 0)
                l2.addWidget(btn4, 1, 1)


if __name__ == '__main__':
    HTM_EditNormalTools()


