import sys
import os
import traceback
from datetime import datetime

from PyQt6 import QtWidgets
from PyQt6.QtCore import QSettings, Qt
from app_Main import App
from appGUI import VisPyPatches

from multiprocessing import freeze_support
# import copyreg
# import types

if sys.platform == "win32":
    # cx_freeze 'module win32' workaround
    from win32comext.shell import shell, shellcon

MIN_VERSION_MAJOR = 3
MIN_VERSION_MINOR = 6


def debug_trace():
    """
    Set a tracepoint in the Python debugger that works with Qt
    :return: None
    """
    from PyQt6.QtCore import pyqtRemoveInputHook
    # from pdb import set_trace
    pyqtRemoveInputHook()
    # set_trace()


if __name__ == '__main__':
    # All X11 calling should be thread safe otherwise we have strange issues
    # QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_X11InitThreads)
    # NOTE: Never talk to the GUI from threads! This is why I commented the above.
    freeze_support()

    portable = False
    # Folder for user settings.
    if sys.platform == 'win32':
        # #######################################################################################################
        # ####### CONFIG FILE WITH PARAMETERS REGARDING PORTABILITY #############################################
        # #######################################################################################################
        config_file = os.path.dirname(os.path.dirname(os.path.realpath(__file__))) + '\\config\\configuration.txt'
        try:
            with open(config_file, 'r'):
                pass
        except FileNotFoundError:
            config_file = os.path.dirname(os.path.realpath(__file__)) + '\\config\\configuration.txt'

        with open(config_file, 'r') as f:
            for line in f:
                param = str(line).replace('\n', '').rpartition('=')

                if param[0] == 'portable':
                    try:
                        portable = eval(param[2])
                    except NameError:
                        portable = False

        if portable is False:
            data_path = shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, None, 0) + '\\FlatCAM'
        else:
            data_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__))) + '\\config'
    else:
        data_path = os.path.expanduser('~') + '/.FlatCAM'

    if not os.path.exists(data_path):
        os.makedirs(data_path)

    log_file_path = os.path.join(data_path, "log.txt")

    major_v = sys.version_info.major
    minor_v = sys.version_info.minor

    v_msg = "FlatCAM Evo uses PYTHON 3 or later. The version minimum is %s.%s\n"\
            "Your Python version is: %s.%s" % (MIN_VERSION_MAJOR, MIN_VERSION_MINOR, str(major_v), str(minor_v))

    # Supported Python version is >= 3.6
    if major_v < MIN_VERSION_MAJOR or (major_v >= MIN_VERSION_MAJOR and minor_v < MIN_VERSION_MINOR):
        print(v_msg)
        msg = '%s\n' % str(datetime.today())
        msg += v_msg

        try:
            with open(log_file_path) as f:
                log_file = f.read()
            log_file += '\n' + msg

            with open(log_file_path, 'w') as f:
                f.write(log_file)
        except IOError:
            with open(log_file_path, 'w') as f:
                f.write(msg)

        if minor_v >= 8:
            os._exit(0)
        else:
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

    # if hdpi_support == 2:
    #     QtWidgets.QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    # else:
    #     QtWidgets.QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, False)


    def excepthook(exc_type, exc_value, exc_tb):
        msg = '%s\n' % str(datetime.today())
        msg += "".join(traceback.format_exception(exc_type, exc_value, exc_tb))

        try:
            with open(log_file_path) as f:
                log_file = f.read()
            log_file += '\n' + msg

            with open(log_file_path, 'w') as f:
                f.write(log_file)
        except IOError:
            with open(log_file_path, 'w') as f:
                f.write(msg)
        QtWidgets.QApplication.quit()
        # or QtWidgets.QApplication.exit(0)

    sys.excepthook = excepthook

    app = QtWidgets.QApplication(sys.argv)
    # app.setAttribute(Qt.AA_UseHighDpiPixmaps)

    # apply style
    settings = QSettings("Open Source", "FlatCAM")
    if settings.contains("style"):
        style = settings.value('style', type=str)
        app.setStyle(style)

    fc = App(qapp=app)

    sys.exit(app.exec())
    # app.exec_()
