from PyQt5 import QtWidgets

from flatcamGUI.preferences.ToolsSubPrefGroupUI import ToolsSubPrefGroupUI
from flatcamGUI.preferences.ToolsSolderpastePrefGroupUI import ToolsSolderpastePrefGroupUI
from flatcamGUI.preferences.ToolsTransformPrefGroupUI import ToolsTransformPrefGroupUI
from flatcamGUI.preferences.ToolsCalculatorsPrefGroupUI import ToolsCalculatorsPrefGroupUI
from flatcamGUI.preferences.ToolsPanelizePrefGroupUI import ToolsPanelizePrefGroupUI
from flatcamGUI.preferences.ToolsFilmPrefGroupUI import ToolsFilmPrefGroupUI
from flatcamGUI.preferences.ToolsPaintPrefGroupUI import ToolsPaintPrefGroupUI
from flatcamGUI.preferences.Tools2sidedPrefGroupUI import Tools2sidedPrefGroupUI
from flatcamGUI.preferences.ToolsCutoutPrefGroupUI import ToolsCutoutPrefGroupUI
from flatcamGUI.preferences.ToolsNCCPrefGroupUI import ToolsNCCPrefGroupUI


class ToolsPreferencesUI(QtWidgets.QWidget):

    def __init__(self, decimals, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        self.decimals = decimals

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

        self.tools_sub_group = ToolsSubPrefGroupUI(decimals=self.decimals)
        self.tools_sub_group.setMinimumWidth(200)

        self.vlay = QtWidgets.QVBoxLayout()
        self.vlay.addWidget(self.tools_ncc_group)
        self.vlay.addWidget(self.tools_cutout_group)

        self.vlay1 = QtWidgets.QVBoxLayout()
        self.vlay1.addWidget(self.tools_paint_group)
        self.vlay1.addWidget(self.tools_panelize_group)

        self.vlay2 = QtWidgets.QVBoxLayout()
        self.vlay2.addWidget(self.tools_transform_group)
        self.vlay2.addWidget(self.tools_2sided_group)
        self.vlay2.addWidget(self.tools_sub_group)

        self.vlay3 = QtWidgets.QVBoxLayout()
        self.vlay3.addWidget(self.tools_film_group)
        self.vlay3.addWidget(self.tools_calculators_group)

        self.vlay4 = QtWidgets.QVBoxLayout()
        self.vlay4.addWidget(self.tools_solderpaste_group)

        self.layout.addLayout(self.vlay)
        self.layout.addLayout(self.vlay1)
        self.layout.addLayout(self.vlay2)
        self.layout.addLayout(self.vlay3)
        self.layout.addLayout(self.vlay4)

        self.layout.addStretch()