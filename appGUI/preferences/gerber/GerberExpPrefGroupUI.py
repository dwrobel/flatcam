from PyQt5 import QtWidgets, QtCore

from appGUI.GUIElements import RadioSet, FCSpinner, FCLabel
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GerberExpPrefGroupUI(OptionsGroupUI):

    def __init__(self, decimals=4, parent=None):
        super(GerberExpPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Gerber Export")))
        self.decimals = decimals

        # Plot options
        self.export_options_label = FCLabel("<b>%s:</b>" % _("Export Options"))
        self.export_options_label.setToolTip(
            _("The parameters set here are used in the file exported\n"
              "when using the File -> Export -> Export Gerber menu entry.")
        )
        self.layout.addWidget(self.export_options_label)

        grid0 = QtWidgets.QGridLayout()
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        self.layout.addLayout(grid0)

        # Gerber Units
        self.gerber_units_label = FCLabel('%s:' % _('Units'))
        self.gerber_units_label.setToolTip(
            _("The units used in the Gerber file.")
        )

        self.gerber_units_radio = RadioSet([{'label': _('Inch'), 'value': 'IN'},
                                            {'label': _('mm'), 'value': 'MM'}])
        self.gerber_units_radio.setToolTip(
            _("The units used in the Gerber file.")
        )

        grid0.addWidget(self.gerber_units_label, 0, 0)
        grid0.addWidget(self.gerber_units_radio, 0, 1)

        # Gerber format
        self.digits_label = FCLabel("%s:" % _("Int/Decimals"))
        self.digits_label.setToolTip(
            _("The number of digits in the whole part of the number\n"
              "and in the fractional part of the number.")
        )

        hlay1 = QtWidgets.QHBoxLayout()

        self.format_whole_entry = FCSpinner()
        self.format_whole_entry.set_range(0, 9)
        self.format_whole_entry.set_step(1)
        self.format_whole_entry.setWrapping(True)

        self.format_whole_entry.setMinimumWidth(30)
        self.format_whole_entry.setToolTip(
            _("This numbers signify the number of digits in\n"
              "the whole part of Gerber coordinates.")
        )
        hlay1.addWidget(self.format_whole_entry, QtCore.Qt.AlignLeft)

        gerber_separator_label = FCLabel(':')
        gerber_separator_label.setFixedWidth(5)
        hlay1.addWidget(gerber_separator_label, QtCore.Qt.AlignLeft)

        self.format_dec_entry = FCSpinner()
        self.format_dec_entry.set_range(0, 9)
        self.format_dec_entry.set_step(1)
        self.format_dec_entry.setWrapping(True)

        self.format_dec_entry.setMinimumWidth(30)
        self.format_dec_entry.setToolTip(
            _("This numbers signify the number of digits in\n"
              "the decimal part of Gerber coordinates.")
        )
        hlay1.addWidget(self.format_dec_entry, QtCore.Qt.AlignLeft)
        hlay1.addStretch()

        grid0.addWidget(self.digits_label, 2, 0)
        grid0.addLayout(hlay1, 2, 1)

        # Gerber Zeros
        self.zeros_label = FCLabel('%s:' % _('Zeros'))
        self.zeros_label.setAlignment(QtCore.Qt.AlignLeft)
        self.zeros_label.setToolTip(
            _("This sets the type of Gerber zeros.\n"
              "If LZ then Leading Zeros are removed and\n"
              "Trailing Zeros are kept.\n"
              "If TZ is checked then Trailing Zeros are removed\n"
              "and Leading Zeros are kept.")
        )

        self.zeros_radio = RadioSet([{'label': _('LZ'), 'value': 'L'},
                                     {'label': _('TZ'), 'value': 'T'}])
        self.zeros_radio.setToolTip(
            _("This sets the type of Gerber zeros.\n"
              "If LZ then Leading Zeros are removed and\n"
              "Trailing Zeros are kept.\n"
              "If TZ is checked then Trailing Zeros are removed\n"
              "and Leading Zeros are kept.")
        )

        grid0.addWidget(self.zeros_label, 4, 0)
        grid0.addWidget(self.zeros_radio, 4, 1)

        self.layout.addStretch()
