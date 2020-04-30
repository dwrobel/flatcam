from PyQt5 import QtWidgets

from flatcamGUI.preferences.gerber.GerberEditorPrefGroupUI import GerberEditorPrefGroupUI
from flatcamGUI.preferences.gerber.GerberExpPrefGroupUI import GerberExpPrefGroupUI
from flatcamGUI.preferences.gerber.GerberAdvOptPrefGroupUI import GerberAdvOptPrefGroupUI
from flatcamGUI.preferences.gerber.GerberOptPrefGroupUI import GerberOptPrefGroupUI
from flatcamGUI.preferences.gerber.GerberGenPrefGroupUI import GerberGenPrefGroupUI


class GerberPreferencesUI(QtWidgets.QWidget):

    def __init__(self, decimals, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        self.decimals = decimals

        self.gerber_gen_group = GerberGenPrefGroupUI(decimals=self.decimals)
        self.gerber_gen_group.setMinimumWidth(250)
        self.gerber_opt_group = GerberOptPrefGroupUI(decimals=self.decimals)
        self.gerber_opt_group.setMinimumWidth(250)
        self.gerber_exp_group = GerberExpPrefGroupUI(decimals=self.decimals)
        self.gerber_exp_group.setMinimumWidth(230)
        self.gerber_adv_opt_group = GerberAdvOptPrefGroupUI(decimals=self.decimals)
        self.gerber_adv_opt_group.setMinimumWidth(200)
        self.gerber_editor_group = GerberEditorPrefGroupUI(decimals=self.decimals)
        self.gerber_editor_group.setMinimumWidth(200)

        self.vlay = QtWidgets.QVBoxLayout()
        self.vlay.addWidget(self.gerber_opt_group)
        self.vlay.addWidget(self.gerber_exp_group)

        self.layout.addWidget(self.gerber_gen_group)
        self.layout.addLayout(self.vlay)
        self.layout.addWidget(self.gerber_adv_opt_group)
        self.layout.addWidget(self.gerber_editor_group)

        self.layout.addStretch()