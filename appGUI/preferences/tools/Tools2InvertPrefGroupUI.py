from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings

from appGUI.GUIElements import FCDoubleSpinner, RadioSet
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


class Tools2InvertPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):

        super(Tools2InvertPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Invert Gerber Tool Options")))
        self.decimals = decimals

        # ## Subtractor Tool Parameters
        self.sublabel = QtWidgets.QLabel("<b>%s:</b>" % _("Parameters"))
        self.sublabel.setToolTip(
            _("A tool to invert Gerber geometry from positive to negative\n"
              "and in revers.")
        )
        self.layout.addWidget(self.sublabel)

        # Grid Layout
        grid0 = QtWidgets.QGridLayout()
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        self.layout.addLayout(grid0)

        # Margin
        self.margin_label = QtWidgets.QLabel('%s:' % _('Margin'))
        self.margin_label.setToolTip(
            _("Distance by which to avoid\n"
              "the edges of the Gerber object.")
        )
        self.margin_entry = FCDoubleSpinner()
        self.margin_entry.set_precision(self.decimals)
        self.margin_entry.set_range(0.0000, 10000.0000)
        self.margin_entry.setObjectName(_("Margin"))

        grid0.addWidget(self.margin_label, 2, 0, 1, 2)
        grid0.addWidget(self.margin_entry, 3, 0, 1, 2)

        self.join_label = QtWidgets.QLabel('%s:' % _("Lines Join Style"))
        self.join_label.setToolTip(
            _("The way that the lines in the object outline will be joined.\n"
              "Can be:\n"
              "- rounded -> an arc is added between two joining lines\n"
              "- square -> the lines meet in 90 degrees angle\n"
              "- bevel -> the lines are joined by a third line")
        )
        self.join_radio = RadioSet([
            {'label': _('Rounded'), 'value': 'r'},
            {'label': _('Square'), 'value': 's'},
            {'label': _('Bevel'), 'value': 'b'}
        ], orientation='vertical', stretch=False)

        grid0.addWidget(self.join_label, 5, 0, 1, 2)
        grid0.addWidget(self.join_radio, 7, 0, 1, 2)

        self.layout.addStretch()
