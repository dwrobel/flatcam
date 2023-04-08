
import sys
import os
import traceback
from datetime import datetime

from PyQt6 import QtWidgets, QtGui
from PyQt6.QtCore import QSettings, QTimer
from appMain import App
from appGUI import VisPyPatches

from appGUI.GUIElements import FCMessageBox

from multiprocessing import freeze_support
# import copyreg
# import types

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
            # data_path = shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, None, 0) + '\\FlatCAM'
            data_path = os.path.join(os.getenv('appdata'), 'FlatCAM')
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

        # if minor_v >= 8:
        #     os._exit(0)
        # else:
        #     sys.exit(0)
        sys.exit(0)

    debug_trace()
    VisPyPatches.apply_patches()

    def excepthook(exc_type, exc_value, exc_tb):
        msg = '%s\n' % str(datetime.today())
        if exc_type != KeyboardInterrupt:
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

            # show the message
            try:
                msgbox = FCMessageBox()
                displayed_msg = "The application encountered a critical error and it will close.\n"\
                                "Please report this error to the developers."
                title = "Critical Error"
                msgbox.setWindowTitle(title)  # taskbar still shows it
                ic = QtGui.QIcon()
                ic.addPixmap(QtGui.QPixmap("assets/resources/warning.png"), QtGui.QIcon.Mode.Normal)
                msgbox.setWindowIcon(ic)
                msgbox.setText('<b>%s</b>' % displayed_msg)
                msgbox.setDetailedText(msg)
                msgbox.setIcon(QtWidgets.QMessageBox.Icon.Critical)

                bt_yes = msgbox.addButton("Quit", QtWidgets.QMessageBox.ButtonRole.YesRole)
                bt_ret = msgbox.addButton("Return", QtWidgets.QMessageBox.ButtonRole.NoRole)

                msgbox.setDefaultButton(bt_yes)
                # msgbox.setTextFormat(Qt.TextFormat.RichText)
                msgbox.exec()

                response = msgbox.clickedButton()
                if response == bt_ret:
                    pass
            except Exception:
                QtWidgets.QApplication.quit()
        else:
            QtWidgets.QApplication.quit()
        # or QtWidgets.QApplication.exit(0)

    sys.excepthook = excepthook

    app = QtWidgets.QApplication(sys.argv)

    # apply style
    settings = QSettings("Open Source", "FlatCAM_EVO")
    if settings.contains("style"):
        style_index = settings.value('style', type=str)
        try:
            idx = int(style_index)
        except Exception:
            idx = 0
        style = QtWidgets.QStyleFactory.keys()[idx]
        app.setStyle(style)
    else:
        app.setStyle('windowsvista')

    fc = App(qapp=app)

    # interrupt the Qt loop such that Python events have a chance to be responsive
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(100)

    try:
        sys.exit(app.exec())
    except SystemError:
        pass
    # app.exec()
