from PyQt5 import QtWidgets

from flatcamGUI.preferences.cncjob.CNCJobAdvOptPrefGroupUI import CNCJobAdvOptPrefGroupUI
from flatcamGUI.preferences.cncjob.CNCJobOptPrefGroupUI import CNCJobOptPrefGroupUI
from flatcamGUI.preferences.cncjob.CNCJobGenPrefGroupUI import CNCJobGenPrefGroupUI


class CNCJobPreferencesUI(QtWidgets.QWidget):

    def __init__(self, decimals, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        self.decimals = decimals

        self.cncjob_gen_group = CNCJobGenPrefGroupUI(decimals=self.decimals)
        self.cncjob_gen_group.setMinimumWidth(260)
        self.cncjob_opt_group = CNCJobOptPrefGroupUI(decimals=self.decimals)
        self.cncjob_opt_group.setMinimumWidth(260)
        self.cncjob_adv_opt_group = CNCJobAdvOptPrefGroupUI(decimals=self.decimals)
        self.cncjob_adv_opt_group.setMinimumWidth(260)

        self.layout.addWidget(self.cncjob_gen_group)
        self.layout.addWidget(self.cncjob_opt_group)
        self.layout.addWidget(self.cncjob_adv_opt_group)

        self.layout.addStretch()