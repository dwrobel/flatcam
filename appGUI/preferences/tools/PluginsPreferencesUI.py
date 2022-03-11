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

from appGUI.ColumnarFlowLayout import ColumnarFlowLayout

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class PluginsPreferencesUI(QtWidgets.QWidget):

    def __init__(self, app, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        if app.defaults['global_gui_layout'] == 0:
            self.layout = QtWidgets.QHBoxLayout()
        else:
            self.layout = ColumnarFlowLayout()
        self.setLayout(self.layout)

        self.tools_drill_group = ToolsDrillPrefGroupUI(app=app)
        self.tools_drill_group.setMinimumWidth(250)

        self.tools_mill_group = ToolsMillPrefGroupUI(app=app)
        self.tools_mill_group.setMinimumWidth(250)

        self.tools_cutout_group = ToolsCutoutPrefGroupUI(app=app)
        self.tools_cutout_group.setMinimumWidth(250)

        self.tools_film_group = ToolsFilmPrefGroupUI(app=app)
        self.tools_film_group.setMinimumWidth(250)

        self.tools_panelize_group = ToolsPanelizePrefGroupUI(app=app)
        self.tools_panelize_group.setMinimumWidth(250)

        self.tools_calculators_group = ToolsCalculatorsPrefGroupUI(app=app)
        self.tools_calculators_group.setMinimumWidth(250)

        self.tools_transform_group = ToolsTransformPrefGroupUI(app=app)
        self.tools_transform_group.setMinimumWidth(250)

        self.tools_solderpaste_group = ToolsSolderpastePrefGroupUI(app=app)
        self.tools_solderpaste_group.setMinimumWidth(250)

        self.tools_markers_group = ToolsMarkersPrefGroupUI(app=app)
        self.tools_markers_group.setMinimumWidth(250)

        self.tools_sub_group = ToolsSubPrefGroupUI(app=app)
        self.tools_sub_group.setMinimumWidth(250)

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
