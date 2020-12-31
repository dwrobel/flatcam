from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QSettings

from appGUI.GUIElements import RadioSet, FCSpinner, FCLabel
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


class ExcellonExpPrefGroupUI(OptionsGroupUI):

    def __init__(self, decimals=4, parent=None):
        super(ExcellonExpPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Excellon Export")))
        self.decimals = decimals

        # Plot options
        self.export_options_label = FCLabel("<b>%s:</b>" % _("Export Options"))
        self.export_options_label.setToolTip(
            _("The parameters set here are used in the file exported\n"
              "when using the File -> Export -> Export Excellon menu entry.")
        )
        self.layout.addWidget(self.export_options_label)

        grid0 = QtWidgets.QGridLayout()
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        self.layout.addLayout(grid0)

        # Excellon Units
        self.excellon_units_label = FCLabel('%s:' % _('Units'))
        self.excellon_units_label.setToolTip(
            _("The units used in the Excellon file.")
        )

        self.excellon_units_radio = RadioSet([{'label': _('Inch'), 'value': 'INCH'},
                                              {'label': _('mm'), 'value': 'METRIC'}])
        self.excellon_units_radio.setToolTip(
            _("The units used in the Excellon file.")
        )

        grid0.addWidget(self.excellon_units_label, 0, 0)
        grid0.addWidget(self.excellon_units_radio, 0, 1)

        # Excellon non-decimal format
        self.digits_label = FCLabel("%s:" % _("Int/Decimals"))
        self.digits_label.setToolTip(
            _("The NC drill files, usually named Excellon files\n"
              "are files that can be found in different formats.\n"
              "Here we set the format used when the provided\n"
              "coordinates are not using period.")
        )

        hlay1 = QtWidgets.QHBoxLayout()

        self.format_whole_entry = FCSpinner()
        self.format_whole_entry.set_range(0, 9)
        self.format_whole_entry.setMinimumWidth(30)
        self.format_whole_entry.setToolTip(
            _("This numbers signify the number of digits in\n"
              "the whole part of Excellon coordinates.")
        )
        hlay1.addWidget(self.format_whole_entry, QtCore.Qt.AlignLeft)

        excellon_separator_label = FCLabel(':')
        excellon_separator_label.setFixedWidth(5)
        hlay1.addWidget(excellon_separator_label, QtCore.Qt.AlignLeft)

        self.format_dec_entry = FCSpinner()
        self.format_dec_entry.set_range(0, 9)
        self.format_dec_entry.setMinimumWidth(30)
        self.format_dec_entry.setToolTip(
            _("This numbers signify the number of digits in\n"
              "the decimal part of Excellon coordinates.")
        )
        hlay1.addWidget(self.format_dec_entry, QtCore.Qt.AlignLeft)
        hlay1.addStretch()

        grid0.addWidget(self.digits_label, 2, 0)
        grid0.addLayout(hlay1, 2, 1)

        # Select the Excellon Format
        self.format_label = FCLabel("%s:" % _("Format"))
        self.format_label.setToolTip(
            _("Select the kind of coordinates format used.\n"
              "Coordinates can be saved with decimal point or without.\n"
              "When there is no decimal point, it is required to specify\n"
              "the number of digits for integer part and the number of decimals.\n"
              "Also it will have to be specified if LZ = leading zeros are kept\n"
              "or TZ = trailing zeros are kept.")
        )
        self.format_radio = RadioSet([{'label': _('Decimal'), 'value': 'dec'},
                                      {'label': _('No-Decimal'), 'value': 'ndec'}])
        self.format_radio.setToolTip(
            _("Select the kind of coordinates format used.\n"
              "Coordinates can be saved with decimal point or without.\n"
              "When there is no decimal point, it is required to specify\n"
              "the number of digits for integer part and the number of decimals.\n"
              "Also it will have to be specified if LZ = leading zeros are kept\n"
              "or TZ = trailing zeros are kept.")
        )

        grid0.addWidget(self.format_label, 4, 0)
        grid0.addWidget(self.format_radio, 4, 1)

        # Excellon Zeros
        self.zeros_label = FCLabel('%s:' % _('Zeros'))
        self.zeros_label.setAlignment(QtCore.Qt.AlignLeft)
        self.zeros_label.setToolTip(
            _("This sets the type of Excellon zeros.\n"
              "If LZ then Leading Zeros are kept and\n"
              "Trailing Zeros are removed.\n"
              "If TZ is checked then Trailing Zeros are kept\n"
              "and Leading Zeros are removed.")
        )

        self.zeros_radio = RadioSet([{'label': _('LZ'), 'value': 'LZ'},
                                     {'label': _('TZ'), 'value': 'TZ'}])
        self.zeros_radio.setToolTip(
            _("This sets the default type of Excellon zeros.\n"
              "If LZ then Leading Zeros are kept and\n"
              "Trailing Zeros are removed.\n"
              "If TZ is checked then Trailing Zeros are kept\n"
              "and Leading Zeros are removed.")
        )

        grid0.addWidget(self.zeros_label, 6, 0)
        grid0.addWidget(self.zeros_radio, 6, 1)

        # Slot type
        self.slot_type_label = FCLabel('%s:' % _('Slot type'))
        self.slot_type_label.setAlignment(QtCore.Qt.AlignLeft)
        self.slot_type_label.setToolTip(
            _("This sets how the slots will be exported.\n"
              "If ROUTED then the slots will be routed\n"
              "using M15/M16 commands.\n"
              "If DRILLED(G85) the slots will be exported\n"
              "using the Drilled slot command (G85).")
        )

        self.slot_type_radio = RadioSet([{'label': _('Routed'), 'value': 'routing'},
                                         {'label': _('Drilled(G85)'), 'value': 'drilling'}])
        self.slot_type_radio.setToolTip(
            _("This sets how the slots will be exported.\n"
              "If ROUTED then the slots will be routed\n"
              "using M15/M16 commands.\n"
              "If DRILLED(G85) the slots will be exported\n"
              "using the Drilled slot command (G85).")
        )

        grid0.addWidget(self.slot_type_label, 8, 0)
        grid0.addWidget(self.slot_type_radio, 8, 1)

        self.layout.addStretch(1)

        # Signals
        self.format_radio.activated_custom.connect(self.optimization_selection)

    def optimization_selection(self):
        if self.format_radio.get_value() == 'dec':
            self.zeros_label.setDisabled(True)
            self.zeros_radio.setDisabled(True)
        else:
            self.zeros_label.setDisabled(False)
            self.zeros_radio.setDisabled(False)
