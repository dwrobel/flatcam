from PyQt5 import QtWidgets

from flatcamGUI.preferences.ExcellonEditorPrefGroupUI import ExcellonEditorPrefGroupUI
from flatcamGUI.preferences.ExcellonExpPrefGroupUI import ExcellonExpPrefGroupUI
from flatcamGUI.preferences.ExcellonAdvOptPrefGroupUI import ExcellonAdvOptPrefGroupUI
from flatcamGUI.preferences.ExcellonOptPrefGroupUI import ExcellonOptPrefGroupUI
from flatcamGUI.preferences.ExcellonGenPrefGroupUI import ExcellonGenPrefGroupUI


class ExcellonPreferencesUI(QtWidgets.QWidget):

    def __init__(self, decimals, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        self.decimals = decimals

        self.excellon_gen_group = ExcellonGenPrefGroupUI(decimals=self.decimals)
        self.excellon_gen_group.setMinimumWidth(220)
        self.excellon_opt_group = ExcellonOptPrefGroupUI(decimals=self.decimals)
        self.excellon_opt_group.setMinimumWidth(290)
        self.excellon_exp_group = ExcellonExpPrefGroupUI(decimals=self.decimals)
        self.excellon_exp_group.setMinimumWidth(250)
        self.excellon_adv_opt_group = ExcellonAdvOptPrefGroupUI(decimals=self.decimals)
        self.excellon_adv_opt_group.setMinimumWidth(250)
        self.excellon_editor_group = ExcellonEditorPrefGroupUI(decimals=self.decimals)
        self.excellon_editor_group.setMinimumWidth(260)

        self.vlay = QtWidgets.QVBoxLayout()
        self.vlay.addWidget(self.excellon_opt_group)
        self.vlay.addWidget(self.excellon_exp_group)

        self.layout.addWidget(self.excellon_gen_group)
        self.layout.addLayout(self.vlay)
        self.layout.addWidget(self.excellon_adv_opt_group)
        self.layout.addWidget(self.excellon_editor_group)

        self.layout.addStretch()