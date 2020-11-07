import sys
import os

from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings, Qt
from app_Main import App
from appGUI import VisPyPatches

from multiprocessing import freeze_support
# import copyreg
# import types

if sys.platform == "win32":
    # cx_freeze 'module win32' workaround
    pass

MIN_VERSION_MAJOR = 3
MIN_VERSION_MINOR = 5


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

    major_v = sys.version_info.major
    minor_v = sys.version_info.minor
    # Supported Python version is >= 3.5
    if major_v >= MIN_VERSION_MAJOR:
        if minor_v >= MIN_VERSION_MINOR:
            pass
        else:
            print("FlatCAM BETA uses PYTHON 3 or later. The version minimum is %s.%s\n"
                  "Your Python version is: %s.%s" % (MIN_VERSION_MAJOR, MIN_VERSION_MINOR, str(major_v), str(minor_v)))

            if minor_v >= 8:
                os._exit(0)
            else:
                sys.exit(0)
    else:
        print("FlatCAM BETA uses PYTHON 3 or later. The version minimum is %s.%s\n"
              "Your Python version is: %s.%s" % (MIN_VERSION_MAJOR, MIN_VERSION_MINOR, str(major_v), str(minor_v)))
        sys.exit(0)

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

    # if hdpi_support == 2:
    #     tst_screen = QtWidgets.QApplication(sys.argv)
    #     if tst_screen.screens()[0].geometry().width() > 1930 or tst_screen.screens()[1].geometry().width() > 1930:
    #         QGuiApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    #         del tst_screen
    # else:
    #     QGuiApplication.setAttribute(Qt.AA_EnableHighDpiScaling, False)

    if hdpi_support == 2:
        QtWidgets.QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    else:
        QtWidgets.QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, False)

    app = QtWidgets.QApplication(sys.argv)

    # apply style
    settings = QSettings("Open Source", "FlatCAM")
    if settings.contains("style"):
        style = settings.value('style', type=str)
        app.setStyle(style)

    fc = App(qapp=app)
    sys.exit(app.exec_())
    # app.exec_()
