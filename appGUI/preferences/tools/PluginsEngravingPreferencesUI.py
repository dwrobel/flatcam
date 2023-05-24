
from PyQt6 import QtWidgets

from appGUI.preferences.tools.Tools2sidedPrefGroupUI import Tools2sidedPrefGroupUI
from appGUI.preferences.tools.ToolsLevelPrefGroupUI import ToolsLevelPrefGroupUI

from appGUI.preferences.tools.ToolsNCCPrefGroupUI import ToolsNCCPrefGroupUI
from appGUI.preferences.tools.ToolsPaintPrefGroupUI import ToolsPaintPrefGroupUI
from appGUI.preferences.tools.ToolsISOPrefGroupUI import ToolsISOPrefGroupUI

from appGUI.ColumnarFlowLayout import ColumnarFlowLayout

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class PluginsEngravingPreferencesUI(QtWidgets.QWidget):

    def __init__(self, app, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        if app.defaults['global_gui_layout'] == 0:
            self.layout = QtWidgets.QHBoxLayout()
        else:
            self.layout = ColumnarFlowLayout()
        self.setLayout(self.layout)

        self.tools_iso_group = ToolsISOPrefGroupUI(app=app)
        self.tools_iso_group.setMinimumWidth(270)

        self.tools_ncc_group = ToolsNCCPrefGroupUI(app=app)
        self.tools_ncc_group.setMinimumWidth(270)

        self.tools_paint_group = ToolsPaintPrefGroupUI(app=app)
        self.tools_paint_group.setMinimumWidth(250)

        self.tools_2sided_group = Tools2sidedPrefGroupUI(app=app)
        self.tools_2sided_group.setMinimumWidth(250)

        self.tools_level_group = ToolsLevelPrefGroupUI(app=app)
        self.tools_level_group.setMinimumWidth(250)

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
