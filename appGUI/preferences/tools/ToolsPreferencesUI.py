from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings

from appGUI.preferences.tools.ToolsSubPrefGroupUI import ToolsSubPrefGroupUI
from appGUI.preferences.tools.ToolsSolderpastePrefGroupUI import ToolsSolderpastePrefGroupUI
from appGUI.preferences.tools.ToolsCornersPrefGroupUI import ToolsCornersPrefGroupUI
from appGUI.preferences.tools.ToolsTransformPrefGroupUI import ToolsTransformPrefGroupUI
from appGUI.preferences.tools.ToolsCalculatorsPrefGroupUI import ToolsCalculatorsPrefGroupUI
from appGUI.preferences.tools.ToolsPanelizePrefGroupUI import ToolsPanelizePrefGroupUI
from appGUI.preferences.tools.ToolsFilmPrefGroupUI import ToolsFilmPrefGroupUI
from appGUI.preferences.tools.Tools2sidedPrefGroupUI import Tools2sidedPrefGroupUI

from appGUI.preferences.tools.ToolsCutoutPrefGroupUI import ToolsCutoutPrefGroupUI
from appGUI.preferences.tools.ToolsNCCPrefGroupUI import ToolsNCCPrefGroupUI
from appGUI.preferences.tools.ToolsPaintPrefGroupUI import ToolsPaintPrefGroupUI
from appGUI.preferences.tools.ToolsISOPrefGroupUI import ToolsISOPrefGroupUI
from appGUI.preferences.tools.ToolsDrillPrefGroupUI import ToolsDrillPrefGroupUI

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


class ToolsPreferencesUI(QtWidgets.QWidget):

    def __init__(self, decimals, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        self.decimals = decimals

        self.tools_iso_group = ToolsISOPrefGroupUI(decimals=self.decimals)
        self.tools_iso_group.setMinimumWidth(220)

        self.tools_drill_group = ToolsDrillPrefGroupUI(decimals=self.decimals)
        self.tools_drill_group.setMinimumWidth(220)

        self.tools_ncc_group = ToolsNCCPrefGroupUI(decimals=self.decimals)
        self.tools_ncc_group.setMinimumWidth(220)

        self.tools_paint_group = ToolsPaintPrefGroupUI(decimals=self.decimals)
        self.tools_paint_group.setMinimumWidth(220)

        self.tools_cutout_group = ToolsCutoutPrefGroupUI(decimals=self.decimals)
        self.tools_cutout_group.setMinimumWidth(220)

        self.tools_2sided_group = Tools2sidedPrefGroupUI(decimals=self.decimals)
        self.tools_2sided_group.setMinimumWidth(220)

        self.tools_film_group = ToolsFilmPrefGroupUI(decimals=self.decimals)
        self.tools_film_group.setMinimumWidth(220)

        self.tools_panelize_group = ToolsPanelizePrefGroupUI(decimals=self.decimals)
        self.tools_panelize_group.setMinimumWidth(220)

        self.tools_calculators_group = ToolsCalculatorsPrefGroupUI(decimals=self.decimals)
        self.tools_calculators_group.setMinimumWidth(220)

        self.tools_transform_group = ToolsTransformPrefGroupUI(decimals=self.decimals)
        self.tools_transform_group.setMinimumWidth(200)

        self.tools_solderpaste_group = ToolsSolderpastePrefGroupUI(decimals=self.decimals)
        self.tools_solderpaste_group.setMinimumWidth(200)

        self.tools_corners_group = ToolsCornersPrefGroupUI(decimals=self.decimals)
        self.tools_corners_group.setMinimumWidth(200)

        self.tools_sub_group = ToolsSubPrefGroupUI(decimals=self.decimals)
        self.tools_sub_group.setMinimumWidth(200)

        self.vlay = QtWidgets.QVBoxLayout()

        self.vlay.addWidget(self.tools_iso_group)
        self.vlay.addWidget(self.tools_2sided_group)
        self.vlay.addWidget(self.tools_cutout_group)

        self.vlay1 = QtWidgets.QVBoxLayout()
        self.vlay1.addWidget(self.tools_drill_group)
        self.vlay1.addWidget(self.tools_panelize_group)

        self.vlay2 = QtWidgets.QVBoxLayout()
        self.vlay2.addWidget(self.tools_ncc_group)
        self.vlay2.addWidget(self.tools_paint_group)

        self.vlay3 = QtWidgets.QVBoxLayout()
        self.vlay3.addWidget(self.tools_film_group)
        self.vlay3.addWidget(self.tools_transform_group)

        self.vlay4 = QtWidgets.QVBoxLayout()
        self.vlay4.addWidget(self.tools_solderpaste_group)
        self.vlay4.addWidget(self.tools_corners_group)
        self.vlay4.addWidget(self.tools_calculators_group)
        self.vlay4.addWidget(self.tools_sub_group)

        self.layout.addLayout(self.vlay)
        self.layout.addLayout(self.vlay1)
        self.layout.addLayout(self.vlay2)
        self.layout.addLayout(self.vlay3)
        self.layout.addLayout(self.vlay4)

        self.layout.addStretch()
