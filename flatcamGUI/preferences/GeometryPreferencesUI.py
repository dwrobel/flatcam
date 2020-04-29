from PyQt5 import QtWidgets

from flatcamGUI.preferences.GeometryEditorPrefGroupUI import GeometryEditorPrefGroupUI
from flatcamGUI.preferences.GeometryAdvOptPrefGroupUI import GeometryAdvOptPrefGroupUI
from flatcamGUI.preferences.GeometryOptPrefGroupUI import GeometryOptPrefGroupUI
from flatcamGUI.preferences.GeometryGenPrefGroupUI import GeometryGenPrefGroupUI


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