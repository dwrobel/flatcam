from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings

from appGUI.GUIElements import FCSpinner, RadioSet
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

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


class GeometryEditorPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "Gerber Adv. Options Preferences", parent=parent)
        super(GeometryEditorPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Geometry Editor")))
        self.decimals = decimals

        # Editor Parameters
        self.param_label = QtWidgets.QLabel("<b>%s:</b>" % _("Parameters"))
        self.param_label.setToolTip(
            _("A list of Editor parameters.")
        )
        self.layout.addWidget(self.param_label)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        # Selection Limit
        self.sel_limit_label = QtWidgets.QLabel('%s:' % _("Selection limit"))
        self.sel_limit_label.setToolTip(
            _("Set the number of selected geometry\n"
              "items above which the utility geometry\n"
              "becomes just a selection rectangle.\n"
              "Increases the performance when moving a\n"
              "large number of geometric elements.")
        )
        self.sel_limit_entry = FCSpinner()
        self.sel_limit_entry.set_range(0, 9999)

        grid0.addWidget(self.sel_limit_label, 0, 0)
        grid0.addWidget(self.sel_limit_entry, 0, 1)

        # Milling Type
        milling_type_label = QtWidgets.QLabel('%s:' % _('Milling Type'))
        milling_type_label.setToolTip(
            _("Milling type:\n"
              "- climb / best for precision milling and to reduce tool usage\n"
              "- conventional / useful when there is no backlash compensation")
        )
        self.milling_type_radio = RadioSet([{'label': _('Climb'), 'value': 'cl'},
                                            {'label': _('Conventional'), 'value': 'cv'}])
        grid0.addWidget(milling_type_label, 1, 0)
        grid0.addWidget(self.milling_type_radio, 1, 1)

        self.layout.addStretch()
