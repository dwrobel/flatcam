
from PyQt6 import QtWidgets
import sys

from appGUI.preferences.utilities.AutoCompletePrefGroupUI import AutoCompletePrefGroupUI
from appGUI.preferences.utilities.FAGrbPrefGroupUI import FAGrbPrefGroupUI
from appGUI.preferences.utilities.FAGcoPrefGroupUI import FAGcoPrefGroupUI
from appGUI.preferences.utilities.FAExcPrefGroupUI import FAExcPrefGroupUI

from appGUI.ColumnarFlowLayout import ColumnarFlowLayout


class UtilPreferencesUI(QtWidgets.QWidget):

    def __init__(self, app, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        if app.defaults['global_gui_layout'] == 0:
            self.layout = QtWidgets.QHBoxLayout()
        else:
            self.layout = ColumnarFlowLayout()
        self.setLayout(self.layout)

        self.fa_excellon_group = FAExcPrefGroupUI(app=app)
        self.fa_excellon_group.setMinimumWidth(260)

        self.fa_gcode_group = FAGcoPrefGroupUI(app=app)
        self.fa_gcode_group.setMinimumWidth(260)

        self.fa_gerber_group = FAGrbPrefGroupUI(app=app)
        self.fa_gerber_group.setMinimumWidth(260)

        self.kw_group = AutoCompletePrefGroupUI(app=app)
        self.kw_group.setMinimumWidth(260)

        # this does not make sense in Linux and MacOs so w edo not display it for those OS's
        if sys.platform not in ['linux', 'darwin']:
            self.vlay = QtWidgets.QVBoxLayout()

            self.vlay.addWidget(self.fa_excellon_group)
            self.vlay.addWidget(self.fa_gcode_group)

            self.layout.addLayout(self.vlay)
            self.layout.addWidget(self.fa_gerber_group)

        self.layout.addWidget(self.kw_group)

        self.layout.addStretch(1)
