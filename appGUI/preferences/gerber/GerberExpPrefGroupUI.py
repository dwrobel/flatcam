from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QSettings

from appGUI.GUIElements import RadioSet, FCSpinner
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


class GerberExpPrefGroupUI(OptionsGroupUI):

    def __init__(self, decimals=4, parent=None):
        super(GerberExpPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Gerber Export")))
        self.decimals = decimals

        # Plot options
        self.export_options_label = QtWidgets.QLabel("<b>%s:</b>" % _("Export Options"))
        self.export_options_label.setToolTip(
            _("The parameters set here are used in the file exported\n"
              "when using the File -> Export -> Export Gerber menu entry.")
        )
        self.layout.addWidget(self.export_options_label)

        form = QtWidgets.QFormLayout()
        self.layout.addLayout(form)

        # Gerber Units
        self.gerber_units_label = QtWidgets.QLabel('%s:' % _('Units'))
        self.gerber_units_label.setToolTip(
            _("The units used in the Gerber file.")
        )

        self.gerber_units_radio = RadioSet([{'label': _('Inch'), 'value': 'IN'},
                                            {'label': _('mm'), 'value': 'MM'}])
        self.gerber_units_radio.setToolTip(
            _("The units used in the Gerber file.")
        )

        form.addRow(self.gerber_units_label, self.gerber_units_radio)

        # Gerber format
        self.digits_label = QtWidgets.QLabel("%s:" % _("Int/Decimals"))
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

        gerber_separator_label = QtWidgets.QLabel(':')
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

        form.addRow(self.digits_label, hlay1)

        # Gerber Zeros
        self.zeros_label = QtWidgets.QLabel('%s:' % _('Zeros'))
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

        form.addRow(self.zeros_label, self.zeros_radio)

        self.layout.addStretch()
