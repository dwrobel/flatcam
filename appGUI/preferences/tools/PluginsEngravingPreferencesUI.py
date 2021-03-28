from PyQt5 import QtWidgets

from appGUI.preferences.tools.Tools2sidedPrefGroupUI import Tools2sidedPrefGroupUI
from appGUI.preferences.tools.ToolsLevelPrefGroupUI import ToolsLevelPrefGroupUI

from appGUI.preferences.tools.ToolsNCCPrefGroupUI import ToolsNCCPrefGroupUI
from appGUI.preferences.tools.ToolsPaintPrefGroupUI import ToolsPaintPrefGroupUI
from appGUI.preferences.tools.ToolsISOPrefGroupUI import ToolsISOPrefGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class PluginsEngravingPreferencesUI(QtWidgets.QWidget):

    def __init__(self, decimals, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        self.decimals = decimals

        self.tools_iso_group = ToolsISOPrefGroupUI(decimals=self.decimals)
        self.tools_iso_group.setMinimumWidth(220)

        self.tools_ncc_group = ToolsNCCPrefGroupUI(decimals=self.decimals)
        self.tools_ncc_group.setMinimumWidth(220)

        self.tools_paint_group = ToolsPaintPrefGroupUI(decimals=self.decimals)
        self.tools_paint_group.setMinimumWidth(220)

        self.tools_2sided_group = Tools2sidedPrefGroupUI(decimals=self.decimals)
        self.tools_2sided_group.setMinimumWidth(220)

        self.tools_level_group = ToolsLevelPrefGroupUI(decimals=self.decimals)
        self.tools_level_group.setMinimumWidth(220)

        self.vlay = QtWidgets.QVBoxLayout()
        self.vlay.addWidget(self.tools_iso_group)

        self.vlay1 = QtWidgets.QVBoxLayout()
        self.vlay1.addWidget(self.tools_ncc_group)

        self.vlay2 = QtWidgets.QVBoxLayout()
        self.vlay2.addWidget(self.tools_paint_group)

        self.vlay3 = QtWidgets.QVBoxLayout()
        self.vlay3.addWidget(self.tools_2sided_group)
        self.vlay3.addWidget(self.tools_level_group)

        self.layout.addLayout(self.vlay)
        self.layout.addLayout(self.vlay1)
        self.layout.addLayout(self.vlay2)
        self.layout.addLayout(self.vlay3)

        self.layout.addStretch()
