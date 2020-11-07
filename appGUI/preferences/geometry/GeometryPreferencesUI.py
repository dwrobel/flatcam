from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings

from appGUI.preferences.geometry.GeometryEditorPrefGroupUI import GeometryEditorPrefGroupUI
from appGUI.preferences.geometry.GeometryAdvOptPrefGroupUI import GeometryAdvOptPrefGroupUI
from appGUI.preferences.geometry.GeometryOptPrefGroupUI import GeometryOptPrefGroupUI
from appGUI.preferences.geometry.GeometryGenPrefGroupUI import GeometryGenPrefGroupUI

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


class GeometryPreferencesUI(QtWidgets.QWidget):

    def __init__(self, decimals, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        self.decimals = decimals

        self.geometry_gen_group = GeometryGenPrefGroupUI(decimals=self.decimals)
        self.geometry_gen_group.setMinimumWidth(220)
        self.geometry_opt_group = GeometryOptPrefGroupUI(decimals=self.decimals)
        self.geometry_opt_group.setMinimumWidth(300)
        self.geometry_adv_opt_group = GeometryAdvOptPrefGroupUI(decimals=self.decimals)
        self.geometry_adv_opt_group.setMinimumWidth(270)
        self.geometry_editor_group = GeometryEditorPrefGroupUI(decimals=self.decimals)
        self.geometry_editor_group.setMinimumWidth(250)

        self.layout.addWidget(self.geometry_gen_group)
        self.layout.addWidget(self.geometry_opt_group)
        self.layout.addWidget(self.geometry_adv_opt_group)
        self.layout.addWidget(self.geometry_editor_group)

        self.layout.addStretch()
