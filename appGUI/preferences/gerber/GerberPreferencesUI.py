from PyQt6 import QtWidgets

from appGUI.preferences.gerber.GerberEditorPrefGroupUI import GerberEditorPrefGroupUI
from appGUI.preferences.gerber.GerberExpPrefGroupUI import GerberExpPrefGroupUI
from appGUI.preferences.gerber.GerberAdvOptPrefGroupUI import GerberAdvOptPrefGroupUI
from appGUI.preferences.gerber.GerberOptPrefGroupUI import GerberOptPrefGroupUI
from appGUI.preferences.gerber.GerberGenPrefGroupUI import GerberGenPrefGroupUI

from appGUI.ColumnarFlowLayout import ColumnarFlowLayout

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GerberPreferencesUI(QtWidgets.QWidget):

    def __init__(self, app, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        if app.defaults['global_gui_layout'] == 0:
            self.layout = QtWidgets.QHBoxLayout()
        else:
            self.layout = ColumnarFlowLayout()
        self.setLayout(self.layout)

        self.gerber_gen_group = GerberGenPrefGroupUI(app=app)
        self.gerber_gen_group.setMinimumWidth(250)
        self.gerber_opt_group = GerberOptPrefGroupUI(app=app)
        self.gerber_opt_group.setMinimumWidth(250)
        self.gerber_exp_group = GerberExpPrefGroupUI(app=app)
        self.gerber_exp_group.setMinimumWidth(230)
        self.gerber_adv_opt_group = GerberAdvOptPrefGroupUI(app=app)
        self.gerber_adv_opt_group.setMinimumWidth(220)
        self.gerber_editor_group = GerberEditorPrefGroupUI(app=app)
        self.gerber_editor_group.setMinimumWidth(270)

        self.vlay = QtWidgets.QVBoxLayout()
        self.vlay.addWidget(self.gerber_opt_group)
        self.vlay.addWidget(self.gerber_adv_opt_group)
        self.vlay.addWidget(self.gerber_exp_group)
        self.vlay.addStretch()

        self.layout.addWidget(self.gerber_gen_group)
        self.layout.addLayout(self.vlay)
        self.layout.addWidget(self.gerber_editor_group)

        self.layout.addStretch()
