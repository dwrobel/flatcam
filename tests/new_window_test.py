import sys
from PyQt5.Qt import *
from PyQt5 import QtGui, QtWidgets

class MyPopup(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        lay = QtWidgets.QVBoxLayout()
        self.setLayout(lay)
        lay.setContentsMargins(0, 0, 0, 0)
        le = QtWidgets.QLineEdit()
        le.setText("Abracadabra")
        le.setReadOnly(True)
        # le.setStyleSheet("QLineEdit { qproperty-frame: false }")
        le.setFrame(False)
        le.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        # lay.addStretch()
        but = QtWidgets.QPushButton("OK")
        hlay = QtWidgets.QHBoxLayout()
        hlay.setContentsMargins(0, 5, 5, 5)

        hlay.addStretch()
        hlay.addWidget(but)

        lay.addWidget(le)
        lay.addLayout(hlay)
    # def paintEvent(self, e):
    #     dc = QtGui.QPainter(self)
    #     dc.drawLine(0, 0, 100, 100)
    #     dc.drawLine(100, 0, 0, 100)

class MainWindow(QMainWindow):
    def __init__(self, *args):
        QtWidgets.QMainWindow.__init__(self, *args)
        self.cw = QtWidgets.QWidget(self)
        self.setCentralWidget(self.cw)
        self.btn1 = QtWidgets.QPushButton("Click me", self.cw)
        self.btn1.setGeometry(QRect(0, 0, 100, 30))
        self.btn1.clicked.connect(self.doit)
        self.w = None

    def doit(self):
        print("Opening a new popup window...")
        self.w = MyPopup()
        self.w.setGeometry(QRect(100, 100, 400, 200))
        self.w.show()

class App(QApplication):
    def __init__(self, *args):
        QtWidgets.QApplication.__init__(self, *args)
        self.main = MainWindow()
        # self.lastWindowClosed.connect(self.byebye)
        self.main.show()

    def byebye(self):
        self.exit(0)

def main(args):
    global app
    app = App(args)
    app.exec_()

if __name__ == "__main__":
    main(sys.argv)