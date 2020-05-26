from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings

from AppGUI.GUIElements import FCCheckBox, RadioSet, FCDoubleSpinner, FCSpinner, OptionalInputSection
from AppGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import AppTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

settings = QSettings("Open Source", "FlatCAM")
if settings.contains("machinist"):
    machinist_setting = settings.value('machinist', type=int)
else:
    machinist_setting = 0


class GerberAdvOptPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "Gerber Adv. Options Preferences", parent=parent)
        super(GerberAdvOptPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Gerber Adv. Options")))
        self.decimals = decimals

        # ## Advanced Gerber Parameters
        self.adv_param_label = QtWidgets.QLabel('<b>%s:</b>' % _('Advanced Options'))
        self.adv_param_label.setToolTip(
            _("A list of Gerber advanced parameters.\n"
              "Those parameters are available only for\n"
              "Advanced App. Level.")
        )
        self.layout.addWidget(self.adv_param_label)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        # Follow Attribute
        self.follow_cb = FCCheckBox(label=_('"Follow"'))
        self.follow_cb.setToolTip(
            _("Generate a 'Follow' geometry.\n"
              "This means that it will cut through\n"
              "the middle of the trace.")
        )
        grid0.addWidget(self.follow_cb, 0, 0, 1, 2)

        # Aperture Table Visibility CB
        self.aperture_table_visibility_cb = FCCheckBox(label=_('Table Show/Hide'))
        self.aperture_table_visibility_cb.setToolTip(
            _("Toggle the display of the Gerber Apertures Table.\n"
              "Also, on hide, it will delete all mark shapes\n"
              "that are drawn on canvas.")

        )
        grid0.addWidget(self.aperture_table_visibility_cb, 1, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 2, 0, 1, 2)

        # Buffering Type
        buffering_label = QtWidgets.QLabel('%s:' % _('Buffering'))
        buffering_label.setToolTip(
            _("Buffering type:\n"
              "- None --> best performance, fast file loading but no so good display\n"
              "- Full --> slow file loading but good visuals. This is the default.\n"
              "<<WARNING>>: Don't change this unless you know what you are doing !!!")
        )
        self.buffering_radio = RadioSet([{'label': _('None'), 'value': 'no'},
                                         {'label': _('Full'), 'value': 'full'}])
        grid0.addWidget(buffering_label, 9, 0)
        grid0.addWidget(self.buffering_radio, 9, 1)

        # Simplification
        self.simplify_cb = FCCheckBox(label=_('Simplify'))
        self.simplify_cb.setToolTip(
            _("When checked all the Gerber polygons will be\n"
              "loaded with simplification having a set tolerance.\n"
              "<<WARNING>>: Don't change this unless you know what you are doing !!!")
                                    )
        grid0.addWidget(self.simplify_cb, 10, 0, 1, 2)

        # Simplification tolerance
        self.simplification_tol_label = QtWidgets.QLabel(_('Tolerance'))
        self.simplification_tol_label.setToolTip(_("Tolerance for polygon simplification."))

        self.simplification_tol_spinner = FCDoubleSpinner()
        self.simplification_tol_spinner.set_precision(self.decimals + 1)
        self.simplification_tol_spinner.setWrapping(True)
        self.simplification_tol_spinner.setRange(0.00000, 0.01000)
        self.simplification_tol_spinner.setSingleStep(0.0001)

        grid0.addWidget(self.simplification_tol_label, 11, 0)
        grid0.addWidget(self.simplification_tol_spinner, 11, 1)
        self.ois_simplif = OptionalInputSection(
            self.simplify_cb,
            [
                self.simplification_tol_label, self.simplification_tol_spinner
            ],
            logic=True)

        self.layout.addStretch()
