from PyQt5 import QtWidgets

from flatcamGUI.preferences.GeneralAppPrefGroupUI import GeneralAppPrefGroupUI
from flatcamGUI.preferences.GeneralAPPSetGroupUI import GeneralAPPSetGroupUI
from flatcamGUI.preferences.GeneralGUIPrefGroupUI import GeneralGUIPrefGroupUI


class GeneralPreferencesUI(QtWidgets.QWidget):
    def __init__(self, decimals, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        self.decimals = decimals

        self.general_app_group = GeneralAppPrefGroupUI(decimals=self.decimals)
        self.general_app_group.setMinimumWidth(250)

        self.general_gui_group = GeneralGUIPrefGroupUI(decimals=self.decimals)
        self.general_gui_group.setMinimumWidth(250)

        self.general_app_set_group = GeneralAPPSetGroupUI(decimals=self.decimals)
        self.general_app_set_group.setMinimumWidth(250)

        self.layout.addWidget(self.general_app_group)
        self.layout.addWidget(self.general_gui_group)
        self.layout.addWidget(self.general_app_set_group)

        self.layout.addStretch()