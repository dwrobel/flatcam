
# https://stackoverflow.com/questions/57569044/pyqt-how-to-create-custom-combined-titlebar-and-menubar


import sys
from PyQt6.QtCore import pyqtSlot, QPoint, Qt, QRect
from PyQt6.QtWidgets import (QMainWindow, QApplication, QPushButton, QHBoxLayout,
                             QVBoxLayout, QTabWidget, QWidget, QSizeGrip,
                             QLabel, QSizeGrip, QMenuBar)
from PyQt6.QtGui import QAction
from PyQt6.QtGui import QIcon


class TitleBar(QWidget):
    height = 35

    def __init__(self, parent):
        super(TitleBar, self).__init__()
        self.movement = None
        self.end = None
        self.parent = parent
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.menu_bar = QMenuBar()
        self.menu_bar.setStyleSheet("""
            color: #fff;
            background-color: #23272A;
            font-size: 14px;
            padding: 4px; 
        """)
        self.menu_file = self.menu_bar.addMenu('file')
        self.menu_file_open = self.menu_file.addAction('open')
        self.menu_file_save = self.menu_file.addAction('save')
        self.menu_file_saveas = self.menu_file.addAction('save as...')
        self.menu_file_quit = self.menu_file.addAction('exit')
        self.menu_file_quit.triggered.connect(QApplication.quit)

        self.menu_work = self.menu_bar.addMenu('work')
        self.menu_analysis = self.menu_bar.addMenu('analysis')
        self.menu_edit = self.menu_bar.addMenu('edit')
        self.menu_window = self.menu_bar.addMenu('window')
        self.menu_help = self.menu_bar.addMenu('help')

        self.layout.addWidget(self.menu_bar)

        self.title = QLabel("Hello World!")
        self.title.setFixedHeight(self.height)
        self.layout.addWidget(self.title)
        self.title.setStyleSheet("""
            background-color: #23272a;  /* 23272a   #f00*/
            font-weight: bold;
            font-size: 16px;
            color: blue;
            padding-left: 170px;
        """)

        self.closeButton = QPushButton(' ')
        self.closeButton.clicked.connect(self.on_click_close)
        self.closeButton.setStyleSheet("""
            background-color: #DC143C;
            border-radius: 10px;
            height: {};
            width: {};
            margin-right: 3px;
            font-weight: bold;
            color: #000;
            font-family: "Webdings";
            qproperty-text: "r";
        """.format(self.height / 1.7, self.height / 1.7))

        self.maxButton = QPushButton(' ')
        self.maxButton.clicked.connect(self.on_click_maximize)
        self.maxButton.setStyleSheet("""
            background-color: #32CD32;
            border-radius: 10px;
            height: {};
            width: {};
            margin-right: 3px;
            font-weight: bold;
            color: #000;
            font-family: "Webdings";
            qproperty-text: "1";
        """.format(self.height / 1.7, self.height / 1.7))

        self.hideButton = QPushButton(' ')
        self.hideButton.clicked.connect(self.on_click_hide)
        self.hideButton.setStyleSheet("""
            background-color: #FFFF00;
            border-radius: 10px;
            height: {};
            width: {};
            margin-right: 3px;
            font-weight: bold;
            color: #000;
            font-family: "Webdings";
            qproperty-text: "0";
        """.format(self.height / 1.7, self.height / 1.7))

        self.layout.addWidget(self.hideButton)
        self.layout.addWidget(self.maxButton)
        self.layout.addWidget(self.closeButton)
        self.setLayout(self.layout)

        self.start = QPoint(0, 0)
        self.pressing = False
        self.maximaze = False

    def resizeEvent(self, QResizeEvent):
        super(TitleBar, self).resizeEvent(QResizeEvent)
        self.title.setFixedWidth(self.parent.width())

    def mousePressEvent(self, event):
        self.start = self.mapToGlobal(event.pos())
        self.pressing = True

    def mouseDoubleClickEvent(self, a0):
        self.on_click_maximize()
        super().mouseDoubleClickEvent(a0)

    def mouseMoveEvent(self, event):
        if self.pressing:
            self.end = self.mapToGlobal(event.pos())
            self.movement = self.end - self.start
            self.parent.move(self.mapToGlobal(self.movement))
            self.start = self.end

    def mouseReleaseEvent(self, QMouseEvent):
        self.pressing = False

    @staticmethod
    def on_click_close():
        sys.exit()

    def on_click_maximize(self):
        self.maximaze = not self.maximaze
        if self.maximaze:
            self.parent.setWindowState(Qt.WindowState.WindowNoState)
        if not self.maximaze:
            self.parent.setWindowState(Qt.WindowState.WindowMaximized)

    def on_click_hide(self):
        self.parent.showMinimized()


class StatusBar(QWidget):
    def __init__(self, parent):
        super(StatusBar, self).__init__(parent)
        self.grip = None
        self.layout = None
        self.label = None
        self.parent = parent
        self.initUI()
        self.showMessage("showMessage: Hello world!")

    def initUI(self):
        self.label = QLabel("Status bar...")
        self.label.setFixedHeight(24)
        self.label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.label.setStyleSheet("""
            background-color: #23272a;
            font-size: 12px;
            padding-left: 5px;
            color: white;
        """)
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.label)
        self.layout.addStretch(1)
        self.grip = QSizeGrip(self.parent)
        self.layout.addWidget(self.grip)
        self.setLayout(self.layout)

    def showMessage(self, text):
        self.label.setText(text)


class MainWindow(QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setMinimumSize(800, 400)

        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet("background-color: #2c2f33;")
        self.setWindowTitle('Code Maker')

        self.title_bar = TitleBar(self)
        self.status_bar = StatusBar(self)

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.title_bar)
        self.layout.addStretch(1)
        self.layout.addWidget(self.status_bar)
        self.layout.setSpacing(0)
        self.setLayout(self.layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec())
