from PyQt6 import QtWidgets

from appGUI.preferences.tools.ToolsSubPrefGroupUI import ToolsSubPrefGroupUI
from appGUI.preferences.tools.ToolsSolderpastePrefGroupUI import ToolsSolderpastePrefGroupUI
from appGUI.preferences.tools.ToolsMarkersPrefGroupUI import ToolsMarkersPrefGroupUI

from appGUI.preferences.tools.ToolsTransformPrefGroupUI import ToolsTransformPrefGroupUI
from appGUI.preferences.tools.ToolsCalculatorsPrefGroupUI import ToolsCalculatorsPrefGroupUI

from appGUI.preferences.tools.ToolsPanelizePrefGroupUI import ToolsPanelizePrefGroupUI
from appGUI.preferences.tools.ToolsFilmPrefGroupUI import ToolsFilmPrefGroupUI

from appGUI.preferences.tools.ToolsCutoutPrefGroupUI import ToolsCutoutPrefGroupUI
from appGUI.preferences.tools.ToolsDrillPrefGroupUI import ToolsDrillPrefGroupUI
from appGUI.preferences.tools.ToolsMillPrefGroupUI import ToolsMillPrefGroupUI
import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class PluginsPreferencesUI(QtWidgets.QWidget):

    def __init__(self, defaults, decimals, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        self.decimals = decimals
        self.defaults = defaults

        self.tools_drill_group = ToolsDrillPrefGroupUI(decimals=self.decimals, defaults=self.defaults)
        self.tools_drill_group.setMinimumWidth(180)

        self.tools_mill_group = ToolsMillPrefGroupUI(decimals=self.decimals, defaults=self.defaults)
        self.tools_mill_group.setMinimumWidth(180)

        self.tools_cutout_group = ToolsCutoutPrefGroupUI(decimals=self.decimals, defaults=self.defaults)
        self.tools_cutout_group.setMinimumWidth(220)

        self.tools_film_group = ToolsFilmPrefGroupUI(decimals=self.decimals, defaults=self.defaults)
        self.tools_film_group.setMinimumWidth(220)

        self.tools_panelize_group = ToolsPanelizePrefGroupUI(decimals=self.decimals, defaults=self.defaults)
        self.tools_panelize_group.setMinimumWidth(220)

        self.tools_calculators_group = ToolsCalculatorsPrefGroupUI(decimals=self.decimals, defaults=self.defaults)
        self.tools_calculators_group.setMinimumWidth(220)

        self.tools_transform_group = ToolsTransformPrefGroupUI(decimals=self.decimals, defaults=self.defaults)
        self.tools_transform_group.setMinimumWidth(200)

        self.tools_solderpaste_group = ToolsSolderpastePrefGroupUI(decimals=self.decimals, defaults=self.defaults)
        self.tools_solderpaste_group.setMinimumWidth(200)

        self.tools_markers_group = ToolsMarkersPrefGroupUI(decimals=self.decimals, defaults=self.defaults)
        self.tools_markers_group.setMinimumWidth(200)

        self.tools_sub_group = ToolsSubPrefGroupUI(decimals=self.decimals, defaults=self.defaults)
        self.tools_sub_group.setMinimumWidth(200)

        self.vlay = QtWidgets.QVBoxLayout()
        self.vlay.addWidget(self.tools_drill_group)

        self.vlay1 = QtWidgets.QVBoxLayout()
        self.vlay1.addWidget(self.tools_mill_group)

        self.vlay2 = QtWidgets.QVBoxLayout()
        self.vlay2.addWidget(self.tools_cutout_group)
        self.vlay2.addWidget(self.tools_panelize_group)

        self.vlay3 = QtWidgets.QVBoxLayout()
        self.vlay3.addWidget(self.tools_film_group)
        self.vlay3.addWidget(self.tools_transform_group)

        self.vlay4 = QtWidgets.QVBoxLayout()
        self.vlay4.addWidget(self.tools_solderpaste_group)
        self.vlay4.addWidget(self.tools_markers_group)
        self.vlay4.addWidget(self.tools_calculators_group)
        self.vlay4.addWidget(self.tools_sub_group)

        self.layout.addLayout(self.vlay)
        self.layout.addLayout(self.vlay1)
        self.layout.addLayout(self.vlay2)
        self.layout.addLayout(self.vlay3)
        self.layout.addLayout(self.vlay4)

        self.layout.addStretch()
