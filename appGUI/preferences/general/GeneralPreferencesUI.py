
from PyQt6 import QtWidgets

from appGUI.preferences.general.GeneralAppPrefGroupUI import GeneralAppPrefGroupUI
from appGUI.preferences.general.GeneralAPPSetGroupUI import GeneralAPPSetGroupUI
from appGUI.preferences.general.GeneralGUIPrefGroupUI import GeneralGUIPrefGroupUI

from appGUI.ColumnarFlowLayout import ColumnarFlowLayout

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GeneralPreferencesUI(QtWidgets.QWidget):
    def __init__(self, app, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        if app.defaults['global_gui_layout'] == 0:
            self.layout = QtWidgets.QHBoxLayout()
        else:
            self.layout = ColumnarFlowLayout()
        self.setLayout(self.layout)

        self.general_app_group = GeneralAppPrefGroupUI(app=app)
        self.general_app_group.setMinimumWidth(250)
        # self.general_app_group.setMaximumWidth(250)

        self.general_gui_group = GeneralGUIPrefGroupUI(app=app)
        self.general_gui_group.setMinimumWidth(250)
        # self.general_gui_group.setMaximumWidth(250)

        self.general_app_set_group = GeneralAPPSetGroupUI(app=app)
        self.general_app_set_group.setMinimumWidth(250)
        # self.general_app_set_group.setMaximumWidth(250)

        self.layout.addWidget(self.general_app_group)
        self.layout.addWidget(self.general_gui_group)
        self.layout.addWidget(self.general_app_set_group)

        self.layout.addStretch()
