
from PyQt6 import QtWidgets

from appGUI.preferences.cncjob.CNCJobAdvOptPrefGroupUI import CNCJobAdvOptPrefGroupUI
from appGUI.preferences.cncjob.CNCJobOptPrefGroupUI import CNCJobOptPrefGroupUI
from appGUI.preferences.cncjob.CNCJobGenPrefGroupUI import CNCJobGenPrefGroupUI
from appGUI.preferences.cncjob.CNCJobEditorPrefGroupUI import CNCJobEditorPrefGroupUI
from appGUI.preferences.cncjob.CNCJobPPGroupUI import CNCJobPPGroupUI

from appGUI.ColumnarFlowLayout import ColumnarFlowLayout


class CNCJobPreferencesUI(QtWidgets.QWidget):

    def __init__(self, app, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        if app.defaults['global_gui_layout'] == 0:
            self.layout = QtWidgets.QHBoxLayout()
        else:
            self.layout = ColumnarFlowLayout()
        self.setLayout(self.layout)

        self.cncjob_gen_group = CNCJobGenPrefGroupUI(app=app)
        self.cncjob_gen_group.setMinimumWidth(260)

        self.cncjob_opt_group = CNCJobOptPrefGroupUI(app=app)
        self.cncjob_opt_group.setMinimumWidth(260)
        self.cncjob_adv_opt_group = CNCJobAdvOptPrefGroupUI(app=app)
        self.cncjob_adv_opt_group.setMinimumWidth(260)

        self.cncjob_editor_group = CNCJobEditorPrefGroupUI(app=app)
        self.cncjob_editor_group.setMinimumWidth(260)

        self.cncjob_pp_group = CNCJobPPGroupUI(app=app)
        self.cncjob_pp_group.setMinimumWidth(260)

        vlay = QtWidgets.QVBoxLayout()
        vlay.addWidget(self.cncjob_opt_group)
        vlay.addWidget(self.cncjob_adv_opt_group)
        vlay.addWidget(self.cncjob_pp_group)
        vlay.addStretch()

        self.layout.addWidget(self.cncjob_gen_group)
        self.layout.addLayout(vlay)
        self.layout.addWidget(self.cncjob_editor_group)

        self.layout.addStretch()
