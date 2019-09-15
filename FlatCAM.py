import sys
import os

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QSettings, Qt
from FlatCAMApp import App
from flatcamGUI import VisPyPatches

from multiprocessing import freeze_support

if sys.platform == "win32":
    # cx_freeze 'module win32' workaround
    pass


def debug_trace():
    """
    Set a tracepoint in the Python debugger that works with Qt
    :return: None
    """
    from PyQt5.QtCore import pyqtRemoveInputHook
    # from pdb import set_trace
    pyqtRemoveInputHook()
    # set_trace()


if __name__ == '__main__':
    # All X11 calling should be thread safe otherwise we have strange issues
    # QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_X11InitThreads)
    # NOTE: Never talk to the GUI from threads! This is why I commented the above.
    freeze_support()

    debug_trace()
    VisPyPatches.apply_patches()

    # apply High DPI support
    settings = QSettings("Open Source", "FlatCAM")
    if settings.contains("hdpi"):
        hdpi_support = settings.value('hdpi', type=int)
    else:
        hdpi_support = 0

    if hdpi_support == 2:
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    else:
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"

    app = QtWidgets.QApplication(sys.argv)

    # apply style
    settings = QSettings("Open Source", "FlatCAM")
    if settings.contains("style"):
        style = settings.value('style', type=str)
        app.setStyle(style)

    if hdpi_support == 2:
        app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    else:
        app.setAttribute(Qt.AA_EnableHighDpiScaling, False)

    fc = App()

    if settings.contains("maximized_gui"):
        maximized_ui = settings.value('maximized_gui', type=bool)
        if maximized_ui is True:
            fc.ui.showMaximized()
        else:
            fc.ui.show()

    sys.exit(app.exec_())
