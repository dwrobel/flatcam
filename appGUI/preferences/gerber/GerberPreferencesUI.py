from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings

from appGUI.preferences.gerber.GerberEditorPrefGroupUI import GerberEditorPrefGroupUI
from appGUI.preferences.gerber.GerberExpPrefGroupUI import GerberExpPrefGroupUI
from appGUI.preferences.gerber.GerberAdvOptPrefGroupUI import GerberAdvOptPrefGroupUI
from appGUI.preferences.gerber.GerberOptPrefGroupUI import GerberOptPrefGroupUI
from appGUI.preferences.gerber.GerberGenPrefGroupUI import GerberGenPrefGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

settings = QSettings("Open Source", "FlatCAM")
if settings.contains("machinist"):
    machinist_setting = settings.value('machinist', type=int)
else:
    machinist_setting = 0


class GerberPreferencesUI(QtWidgets.QWidget):

    def __init__(self, decimals, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        self.decimals = decimals

        self.gerber_gen_group = GerberGenPrefGroupUI(decimals=self.decimals)
        self.gerber_gen_group.setMinimumWidth(250)
        self.gerber_opt_group = GerberOptPrefGroupUI(decimals=self.decimals)
        self.gerber_opt_group.setMinimumWidth(250)
        self.gerber_exp_group = GerberExpPrefGroupUI(decimals=self.decimals)
        self.gerber_exp_group.setMinimumWidth(230)
        self.gerber_adv_opt_group = GerberAdvOptPrefGroupUI(decimals=self.decimals)
        self.gerber_adv_opt_group.setMinimumWidth(200)
        self.gerber_editor_group = GerberEditorPrefGroupUI(decimals=self.decimals)
        self.gerber_editor_group.setMinimumWidth(200)

        self.vlay = QtWidgets.QVBoxLayout()
        self.vlay.addWidget(self.gerber_opt_group)
        self.vlay.addWidget(self.gerber_adv_opt_group)
        self.vlay.addWidget(self.gerber_exp_group)
        self.vlay.addStretch()

        self.layout.addWidget(self.gerber_gen_group)
        self.layout.addLayout(self.vlay)
        self.layout.addWidget(self.gerber_editor_group)

        self.layout.addStretch()
