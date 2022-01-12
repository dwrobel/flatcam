# ########################################################
# # customize Title bar
# # dotpy.ir
# # iraj.jelo@gmail.com
# ########################################################
import sys
from PyQt6 import QtWidgets, QtGui
from PyQt6 import QtCore
from PyQt6.QtCore import Qt

from datetime import datetime
import traceback


class TitleBar(QtWidgets.QDialog):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        css = """
        QWidget{
            Background: #0000FF;
            color:white;
            font:12px bold;
            font-weight:bold;
            border-radius: 1px;
            height: 11px;
        }
        QDialog{
            Background-image:url('img/titlebar bg.png');
            font-size:12px;
            color: black;

        }
        QToolButton{
            Background:#AA00AA;
            font-size:11px;
        }
        QToolButton:hover{
            Background: #FF00FF;
            font-size:11px;
        }
        """
        self.setAutoFillBackground(True)
        self.setBackgroundRole(QtGui.QPalette.ColorRole.Highlight)
        self.setStyleSheet(css)
        self.minimize = QtWidgets.QToolButton(self)
        self.minimize.setIcon(QtGui.QIcon('img/min.png'))
        self.maximize = QtWidgets.QToolButton(self)
        self.maximize.setIcon(QtGui.QIcon('img/max.png'))
        close = QtWidgets.QToolButton(self)
        close.setIcon(QtGui.QIcon('img/close.png'))
        self.minimize.setMinimumHeight(10)
        close.setMinimumHeight(10)
        self.maximize.setMinimumHeight(10)
        label = QtWidgets.QLabel(self)
        label.setText("Window Title")
        self.setWindowTitle("Window Title")
        hbox = QtWidgets.QHBoxLayout(self)
        hbox.addWidget(label)
        hbox.addWidget(self.minimize)
        hbox.addWidget(self.maximize)
        hbox.addWidget(close)
        hbox.insertStretch(1, 500)
        hbox.setSpacing(0)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.maxNormal = False
        close.clicked.connect(self.close)
        self.minimize.clicked.connect(self.showSmall)
        self.maximize.clicked.connect(self.showMaxRestore)

    @staticmethod
    def showSmall():
        box.showMinimized()

    def showMaxRestore(self):
        if self.maxNormal:
            box.showNormal()
            self.maxNormal = False
            self.maximize.setIcon(QtGui.QIcon('img/max.png'))
        else:
            box.showMaximized()
            self.maxNormal = True
            self.maximize.setIcon(QtGui.QIcon('img/max2.png'))

    def close(self):
        box.close()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            box.moving = True
            box.offset = event.position()
            if event.type() == QtCore.QEvent.Type.MouseButtonDblClick:
                self.showMaxRestore()

    def mouseMoveEvent(self, event):
        if box.isMaximized():
            self.showMaxRestore()
            box.move(event.globalPosition().toPoint() - box.offset)
        else:
            if box.moving:
                box.move(event.globalPosition().toPoint() - box.offset)


class Frame(QtWidgets.QFrame):
    def __init__(self, parent=None):
        QtWidgets.QFrame.__init__(self, parent)

        self.m_old_pos = None
        self.m_mouse_down = False
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        css = """
        QFrame{
            Background:  #FFFFF0;
            color:white;
            font:13px ;
            font-weight:bold;
            }
        """
        self.setStyleSheet(css)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setMouseTracking(True)
        self.m_titleBar = TitleBar(self)
        self.m_content = QtWidgets.QWidget(self)
        vbox = QtWidgets.QVBoxLayout(self)
        vbox.addWidget(self.m_titleBar)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.m_content)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)
        vbox.addLayout(layout)
        # Allows you to access the content area of the frame
        # where widgets and layouts can be added

    def contentWidget(self):
        return self.m_content

    def titleBar(self):
        return self.m_titleBar

    def mousePressEvent(self, event):
        self.m_old_pos = event.pos()
        self.m_mouse_down = event.button() == Qt.MouseButton.LeftButton

    def mouseMoveEvent(self, event):
        event.position().x()
        event.position().y()

    def mouseReleaseEvent(self, event):
        self.m_mouse_down = False


if __name__ == '__main__':
    def excepthook(exc_type, exc_value, exc_tb):
        msg = '%s\n' % str(datetime.today())
        if exc_type != KeyboardInterrupt:
            msg += "".join(traceback.format_exception(exc_type, exc_value, exc_tb))

            # show the message
            try:
                msgbox = QtWidgets.QMessageBox()
                displayed_msg = "The application encountered a critical error and it will close.\n" \
                                "Please report this error to the developers."

                msgbox.setText(displayed_msg)
                msgbox.setDetailedText(msg)
                msgbox.setWindowTitle("Critical Error")
                # msgbox.setWindowIcon()
                msgbox.setIcon(QtWidgets.QMessageBox.Icon.Critical)

                bt_yes = msgbox.addButton("Quit", QtWidgets.QMessageBox.ButtonRole.YesRole)

                msgbox.setDefaultButton(bt_yes)
                # msgbox.setTextFormat(Qt.TextFormat.RichText)
                msgbox.exec()
            except Exception:
                pass
        QtWidgets.QApplication.quit()
        # or QtWidgets.QApplication.exit(0)


    sys.excepthook = excepthook

    app = QtWidgets.QApplication(sys.argv)
    box = Frame()
    box.move(60, 60)

    le = QtWidgets.QVBoxLayout(box.contentWidget())

    le.setContentsMargins(0, 0, 0, 0)
    edit = QtWidgets.QLabel("""I would've did anything for you to show you how much I adored you
But it's over now, it's too late to save our loveJust promise me you'll think of me
Every time you look up in the sky and see a star 'cuz I'm  your star.""")
    le.addWidget(edit)
    box.show()
    app.exec()
