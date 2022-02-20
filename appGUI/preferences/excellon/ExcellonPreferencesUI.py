from PyQt6 import QtWidgets

from appGUI.preferences.excellon.ExcellonEditorPrefGroupUI import ExcellonEditorPrefGroupUI
from appGUI.preferences.excellon.ExcellonExpPrefGroupUI import ExcellonExpPrefGroupUI
from appGUI.preferences.excellon.ExcellonAdvOptPrefGroupUI import ExcellonAdvOptPrefGroupUI
from appGUI.preferences.excellon.ExcellonOptPrefGroupUI import ExcellonOptPrefGroupUI
from appGUI.preferences.excellon.ExcellonGenPrefGroupUI import ExcellonGenPrefGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ExcellonPreferencesUI(QtWidgets.QWidget):

    def __init__(self, app, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)

        self.excellon_gen_group = ExcellonGenPrefGroupUI(app=app)
        self.excellon_gen_group.setMinimumWidth(240)
        self.excellon_opt_group = ExcellonOptPrefGroupUI(app=app)
        self.excellon_opt_group.setMinimumWidth(290)
        self.excellon_exp_group = ExcellonExpPrefGroupUI(app=app)
        self.excellon_exp_group.setMinimumWidth(250)
        self.excellon_adv_opt_group = ExcellonAdvOptPrefGroupUI(app=app)
        self.excellon_adv_opt_group.setMinimumWidth(250)
        self.excellon_editor_group = ExcellonEditorPrefGroupUI(app=app)
        self.excellon_editor_group.setMinimumWidth(260)

        self.vlay = QtWidgets.QVBoxLayout()
        self.vlay.addWidget(self.excellon_opt_group)
        self.vlay.addWidget(self.excellon_adv_opt_group)
        self.vlay.addWidget(self.excellon_exp_group)

        self.layout.addWidget(self.excellon_gen_group)
        self.layout.addLayout(self.vlay)
        self.layout.addWidget(self.excellon_editor_group)

        self.layout.addStretch()
