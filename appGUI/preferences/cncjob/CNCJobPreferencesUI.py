from PyQt5 import QtWidgets

from appGUI.preferences.cncjob.CNCJobAdvOptPrefGroupUI import CNCJobAdvOptPrefGroupUI
from appGUI.preferences.cncjob.CNCJobOptPrefGroupUI import CNCJobOptPrefGroupUI
from appGUI.preferences.cncjob.CNCJobGenPrefGroupUI import CNCJobGenPrefGroupUI
from appGUI.preferences.cncjob.CNCJobEditorPrefGroupUI import CNCJobEditorPrefGroupUI


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

        self.cncjob_editor_group = CNCJobEditorPrefGroupUI(decimals=self.decimals)
        self.cncjob_editor_group.setMinimumWidth(260)

        vlay = QtWidgets.QVBoxLayout()
        vlay.addWidget(self.cncjob_opt_group)
        vlay.addWidget(self.cncjob_adv_opt_group)

        self.layout.addWidget(self.cncjob_gen_group)
        self.layout.addLayout(vlay)
        self.layout.addWidget(self.cncjob_editor_group)

        self.layout.addStretch()
