from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings

from appGUI.preferences.tools.Tools2InvertPrefGroupUI import Tools2InvertPrefGroupUI
from appGUI.preferences.tools.Tools2PunchGerberPrefGroupUI import Tools2PunchGerberPrefGroupUI
from appGUI.preferences.tools.Tools2EDrillsPrefGroupUI import Tools2EDrillsPrefGroupUI
from appGUI.preferences.tools.Tools2CalPrefGroupUI import Tools2CalPrefGroupUI
from appGUI.preferences.tools.Tools2FiducialsPrefGroupUI import Tools2FiducialsPrefGroupUI
from appGUI.preferences.tools.Tools2CThievingPrefGroupUI import Tools2CThievingPrefGroupUI
from appGUI.preferences.tools.Tools2QRCodePrefGroupUI import Tools2QRCodePrefGroupUI
from appGUI.preferences.tools.Tools2OptimalPrefGroupUI import Tools2OptimalPrefGroupUI
from appGUI.preferences.tools.Tools2RulesCheckPrefGroupUI import Tools2RulesCheckPrefGroupUI

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


class Tools2PreferencesUI(QtWidgets.QWidget):

    def __init__(self, decimals, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        self.decimals = decimals

        self.tools2_checkrules_group = Tools2RulesCheckPrefGroupUI(decimals=self.decimals)
        self.tools2_checkrules_group.setMinimumWidth(220)

        self.tools2_optimal_group = Tools2OptimalPrefGroupUI(decimals=self.decimals)
        self.tools2_optimal_group.setMinimumWidth(220)

        self.tools2_qrcode_group = Tools2QRCodePrefGroupUI(decimals=self.decimals)
        self.tools2_qrcode_group.setMinimumWidth(220)

        self.tools2_cfill_group = Tools2CThievingPrefGroupUI(decimals=self.decimals)
        self.tools2_cfill_group.setMinimumWidth(220)

        self.tools2_fiducials_group = Tools2FiducialsPrefGroupUI(decimals=self.decimals)
        self.tools2_fiducials_group.setMinimumWidth(220)

        self.tools2_cal_group = Tools2CalPrefGroupUI(decimals=self.decimals)
        self.tools2_cal_group.setMinimumWidth(220)

        self.tools2_edrills_group = Tools2EDrillsPrefGroupUI(decimals=self.decimals)
        self.tools2_edrills_group.setMinimumWidth(220)

        self.tools2_punch_group = Tools2PunchGerberPrefGroupUI(decimals=self.decimals)
        self.tools2_punch_group.setMinimumWidth(220)

        self.tools2_invert_group = Tools2InvertPrefGroupUI(decimals=self.decimals)
        self.tools2_invert_group.setMinimumWidth(220)

        self.vlay = QtWidgets.QVBoxLayout()
        self.vlay.addWidget(self.tools2_checkrules_group)
        self.vlay.addWidget(self.tools2_optimal_group)

        self.vlay1 = QtWidgets.QVBoxLayout()
        self.vlay1.addWidget(self.tools2_qrcode_group)
        self.vlay1.addWidget(self.tools2_fiducials_group)

        self.vlay2 = QtWidgets.QVBoxLayout()
        self.vlay2.addWidget(self.tools2_cfill_group)

        self.vlay3 = QtWidgets.QVBoxLayout()
        self.vlay3.addWidget(self.tools2_cal_group)
        self.vlay3.addWidget(self.tools2_edrills_group)

        self.vlay4 = QtWidgets.QVBoxLayout()
        self.vlay4.addWidget(self.tools2_punch_group)
        self.vlay4.addWidget(self.tools2_invert_group)

        self.layout.addLayout(self.vlay)
        self.layout.addLayout(self.vlay1)
        self.layout.addLayout(self.vlay2)
        self.layout.addLayout(self.vlay3)
        self.layout.addLayout(self.vlay4)

        self.layout.addStretch()
