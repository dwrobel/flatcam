import platform

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QSettings

from appGUI.GUIElements import FCCheckBox, FCSpinner, RadioSet, FCSliderWithSpinner, FCColorEntry
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


class ExcellonGenPrefGroupUI(OptionsGroupUI):

    def __init__(self, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "Excellon Options", parent=parent)
        super(ExcellonGenPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Excellon General")))
        self.decimals = decimals

        # Plot options
        self.plot_options_label = QtWidgets.QLabel("<b>%s:</b>" % _("Plot Options"))
        self.layout.addWidget(self.plot_options_label)

        grid1 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid1)

        # Plot CB
        self.plot_cb = FCCheckBox(label=_('Plot'))
        self.plot_cb.setToolTip(
            "Plot (show) this object."
        )
        grid1.addWidget(self.plot_cb, 0, 0)

        # Solid CB
        self.solid_cb = FCCheckBox(label=_('Solid'))
        self.solid_cb.setToolTip(
            "Plot as solid circles."
        )
        grid1.addWidget(self.solid_cb, 0, 1)

        # Multicolored CB
        self.multicolored_cb = FCCheckBox(label='%s' % _('M-Color'))
        self.multicolored_cb.setToolTip(
            _("Draw polygons in different colors.")
        )
        grid1.addWidget(self.multicolored_cb, 0, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid1.addWidget(separator_line, 1, 0, 1, 3)

        grid2 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid2)
        grid2.setColumnStretch(0, 0)
        grid2.setColumnStretch(1, 1)

        # Excellon format
        self.excellon_format_label = QtWidgets.QLabel("<b>%s:</b>" % _("Excellon Format"))
        self.excellon_format_label.setToolTip(
            _("The NC drill files, usually named Excellon files\n"
              "are files that can be found in different formats.\n"
              "Here we set the format used when the provided\n"
              "coordinates are not using period.\n"
              "\n"
              "Possible presets:\n"
              "\n"
              "PROTEUS 3:3 MM LZ\n"
              "DipTrace 5:2 MM TZ\n"
              "DipTrace 4:3 MM LZ\n"
              "\n"
              "EAGLE 3:3 MM TZ\n"
              "EAGLE 4:3 MM TZ\n"
              "EAGLE 2:5 INCH TZ\n"
              "EAGLE 3:5 INCH TZ\n"
              "\n"
              "ALTIUM 2:4 INCH LZ\n"
              "Sprint Layout 2:4 INCH LZ"
              "\n"
              "KiCAD 3:5 INCH TZ")
        )
        grid2.addWidget(self.excellon_format_label, 0, 0, 1, 2)

        self.excellon_format_in_label = QtWidgets.QLabel('%s:' % _("INCH"))
        self.excellon_format_in_label.setToolTip(_("Default values for INCH are 2:4"))

        hlay1 = QtWidgets.QHBoxLayout()
        self.excellon_format_upper_in_entry = FCSpinner()
        self.excellon_format_upper_in_entry.set_range(0, 9)
        self.excellon_format_upper_in_entry.setMinimumWidth(30)
        self.excellon_format_upper_in_entry.setToolTip(
           _("This numbers signify the number of digits in\n"
             "the whole part of Excellon coordinates.")
        )
        hlay1.addWidget(self.excellon_format_upper_in_entry)

        excellon_separator_in_label = QtWidgets.QLabel(':')
        excellon_separator_in_label.setFixedWidth(5)
        hlay1.addWidget(excellon_separator_in_label)

        self.excellon_format_lower_in_entry = FCSpinner()
        self.excellon_format_lower_in_entry.set_range(0, 9)
        self.excellon_format_lower_in_entry.setMinimumWidth(30)
        self.excellon_format_lower_in_entry.setToolTip(
            _("This numbers signify the number of digits in\n"
              "the decimal part of Excellon coordinates.")
        )
        hlay1.addWidget(self.excellon_format_lower_in_entry)

        grid2.addWidget(self.excellon_format_in_label, 1, 0)
        grid2.addLayout(hlay1, 1, 1)

        self.excellon_format_mm_label = QtWidgets.QLabel('%s:' % _("METRIC"))
        self.excellon_format_mm_label.setToolTip(_("Default values for METRIC are 3:3"))

        hlay2 = QtWidgets.QHBoxLayout()
        self.excellon_format_upper_mm_entry = FCSpinner()
        self.excellon_format_upper_mm_entry.set_range(0, 9)
        self.excellon_format_upper_mm_entry.setMinimumWidth(30)
        self.excellon_format_upper_mm_entry.setToolTip(
            _("This numbers signify the number of digits in\n"
              "the whole part of Excellon coordinates.")
        )
        hlay2.addWidget(self.excellon_format_upper_mm_entry)

        excellon_separator_mm_label = QtWidgets.QLabel(':')
        excellon_separator_mm_label.setFixedWidth(5)
        hlay2.addWidget(excellon_separator_mm_label, QtCore.Qt.AlignLeft)

        self.excellon_format_lower_mm_entry = FCSpinner()
        self.excellon_format_lower_mm_entry.set_range(0, 9)
        self.excellon_format_lower_mm_entry.setMinimumWidth(30)
        self.excellon_format_lower_mm_entry.setToolTip(
            _("This numbers signify the number of digits in\n"
              "the decimal part of Excellon coordinates.")
        )
        hlay2.addWidget(self.excellon_format_lower_mm_entry)

        grid2.addWidget(self.excellon_format_mm_label, 2, 0)
        grid2.addLayout(hlay2, 2, 1)

        self.excellon_zeros_label = QtWidgets.QLabel('%s:' % _('Zeros'))
        self.excellon_zeros_label.setAlignment(QtCore.Qt.AlignLeft)
        self.excellon_zeros_label.setToolTip(
            _("This sets the type of Excellon zeros.\n"
              "If LZ then Leading Zeros are kept and\n"
              "Trailing Zeros are removed.\n"
              "If TZ is checked then Trailing Zeros are kept\n"
              "and Leading Zeros are removed.\n\n"
              "This is used when there is no information\n"
              "stored in the Excellon file.")
        )
        grid2.addWidget(self.excellon_zeros_label, 3, 0)

        self.excellon_zeros_radio = RadioSet([{'label': _('LZ'), 'value': 'L'},
                                              {'label': _('TZ'), 'value': 'T'}])

        grid2.addWidget(self.excellon_zeros_radio, 3, 1)

        self.excellon_units_label = QtWidgets.QLabel('%s:' % _('Units'))
        self.excellon_units_label.setAlignment(QtCore.Qt.AlignLeft)
        self.excellon_units_label.setToolTip(
            _("This sets the default units of Excellon files.\n"
              "If it is not detected in the parsed file the value here\n"
              "will be used."
              "Some Excellon files don't have an header\n"
              "therefore this parameter will be used.")
        )

        self.excellon_units_radio = RadioSet([{'label': _('Inch'), 'value': 'INCH'},
                                              {'label': _('mm'), 'value': 'METRIC'}])
        self.excellon_units_radio.setToolTip(
            _("This sets the units of Excellon files.\n"
              "Some Excellon files don't have an header\n"
              "therefore this parameter will be used.")
        )

        grid2.addWidget(self.excellon_units_label, 4, 0)
        grid2.addWidget(self.excellon_units_radio, 4, 1)

        self.update_excellon_cb = FCCheckBox(label=_('Update Export settings'))
        self.update_excellon_cb.setToolTip(
            "If checked, the Excellon Export settings will be updated with the ones above."
        )
        grid2.addWidget(self.update_excellon_cb, 5, 0, 1, 2)

        # Adding the Excellon Format Defaults Button
        self.excellon_defaults_button = QtWidgets.QPushButton()
        self.excellon_defaults_button.setText(str(_("Restore Defaults")))
        self.excellon_defaults_button.setMinimumWidth(80)
        grid2.addWidget(self.excellon_defaults_button, 6, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid2.addWidget(separator_line, 7, 0, 1, 2)

        self.excellon_general_label = QtWidgets.QLabel("<b>%s:</b>" % _("Path Optimization"))
        grid2.addWidget(self.excellon_general_label, 8, 0, 1, 2)

        self.excellon_optimization_label = QtWidgets.QLabel(_('Algorithm:'))
        self.excellon_optimization_label.setToolTip(
            _("This sets the optimization type for the Excellon drill path.\n"
              "If <<MetaHeuristic>> is checked then Google OR-Tools algorithm with\n"
              "MetaHeuristic Guided Local Path is used. Default search time is 3sec.\n"
              "If <<Basic>> is checked then Google OR-Tools Basic algorithm is used.\n"
              "If <<TSA>> is checked then Travelling Salesman algorithm is used for\n"
              "drill path optimization.\n"
              "\n"
              "Some options are disabled when the application works in 32bit mode.")
        )

        self.excellon_optimization_radio = RadioSet([{'label': _('MetaHeuristic'), 'value': 'M'},
                                                     {'label': _('Basic'), 'value': 'B'},
                                                     {'label': _('TSA'), 'value': 'T'}],
                                                    orientation='vertical', stretch=False)

        grid2.addWidget(self.excellon_optimization_label, 9, 0)
        grid2.addWidget(self.excellon_optimization_radio, 9, 1)

        self.optimization_time_label = QtWidgets.QLabel('%s:' % _('Duration'))
        self.optimization_time_label.setAlignment(QtCore.Qt.AlignLeft)
        self.optimization_time_label.setToolTip(
            _("When OR-Tools Metaheuristic (MH) is enabled there is a\n"
              "maximum threshold for how much time is spent doing the\n"
              "path optimization. This max duration is set here.\n"
              "In seconds.")

        )

        self.optimization_time_entry = FCSpinner()
        self.optimization_time_entry.set_range(0, 999)

        grid2.addWidget(self.optimization_time_label, 10, 0)
        grid2.addWidget(self.optimization_time_entry, 10, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid2.addWidget(separator_line, 11, 0, 1, 2)

        # Fuse Tools
        self.join_geo_label = QtWidgets.QLabel('<b>%s</b>:' % _('Join Option'))
        grid2.addWidget(self.join_geo_label, 12, 0, 1, 2)

        self.fuse_tools_cb = FCCheckBox(_("Fuse Tools"))
        self.fuse_tools_cb.setToolTip(
            _("When checked, the tools will be merged\n"
              "but only if they share some of their attributes.")
        )
        grid2.addWidget(self.fuse_tools_cb, 13, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid2.addWidget(separator_line, 14, 0, 1, 2)

        # Excellon Object Color
        self.gerber_color_label = QtWidgets.QLabel('<b>%s</b>' % _('Object Color'))
        grid2.addWidget(self.gerber_color_label, 17, 0, 1, 2)

        # Plot Line Color
        self.line_color_label = QtWidgets.QLabel('%s:' % _('Outline'))
        self.line_color_label.setToolTip(
            _("Set the line color for plotted objects.")
        )
        self.line_color_entry = FCColorEntry()

        grid2.addWidget(self.line_color_label, 19, 0)
        grid2.addWidget(self.line_color_entry, 19, 1)

        # Plot Fill Color
        self.fill_color_label = QtWidgets.QLabel('%s:' % _('Fill'))
        self.fill_color_label.setToolTip(
            _("Set the fill color for plotted objects.\n"
              "First 6 digits are the color and the last 2\n"
              "digits are for alpha (transparency) level.")
        )
        self.fill_color_entry = FCColorEntry()

        grid2.addWidget(self.fill_color_label, 22, 0)
        grid2.addWidget(self.fill_color_entry, 22, 1)

        # Plot Fill Transparency Level
        self.excellon_alpha_label = QtWidgets.QLabel('%s:' % _('Alpha'))
        self.excellon_alpha_label.setToolTip(
            _("Set the fill transparency for plotted objects.")
        )
        self.excellon_alpha_entry = FCSliderWithSpinner(0, 255, 1)

        grid2.addWidget(self.excellon_alpha_label, 24, 0)
        grid2.addWidget(self.excellon_alpha_entry, 24, 1)

        self.layout.addStretch()

        current_platform = platform.architecture()[0]
        if current_platform == '64bit':
            self.excellon_optimization_radio.setOptionsDisabled([_('MetaHeuristic'), _('Basic')], False)
            self.optimization_time_label.setDisabled(False)
            self.optimization_time_entry.setDisabled(False)
        else:
            self.excellon_optimization_radio.setOptionsDisabled([_('MetaHeuristic'), _('Basic')], True)
            self.optimization_time_label.setDisabled(True)
            self.optimization_time_entry.setDisabled(True)

        # Setting plot colors signals
        self.line_color_entry.editingFinished.connect(self.on_line_color_entry)
        self.fill_color_entry.editingFinished.connect(self.on_fill_color_entry)

        self.excellon_alpha_entry.valueChanged.connect(self.on_excellon_alpha_changed)  # alpha

        # Load the defaults values into the Excellon Format and Excellon Zeros fields
        self.excellon_defaults_button.clicked.connect(self.on_excellon_defaults_button)
        # Make sure that when the Excellon loading parameters are changed, the change is reflected in the
        # Export Excellon parameters.
        self.update_excellon_cb.stateChanged.connect(self.on_update_exc_export)

        # call it once to make sure it is updated at startup
        self.on_update_exc_export(state=self.app.defaults["excellon_update"])

        self.excellon_optimization_radio.activated_custom.connect(self.optimization_selection)

    def optimization_selection(self):
        if self.excellon_optimization_radio.get_value() == 'M':
            self.optimization_time_label.setDisabled(False)
            self.optimization_time_entry.setDisabled(False)
        else:
            self.optimization_time_label.setDisabled(True)
            self.optimization_time_entry.setDisabled(True)

    # Setting plot colors handlers
    def on_fill_color_entry(self):
        self.app.defaults['excellon_plot_fill'] = self.fill_color_entry.get_value()[:7] + \
            self.app.defaults['excellon_plot_fill'][7:9]

    def on_line_color_entry(self):
        self.app.defaults['excellon_plot_line'] = self.line_color_entry.get_value()[:7] + \
                                                self.app.defaults['excellon_plot_line'][7:9]

    def on_excellon_alpha_changed(self, spinner_value):
        self.app.defaults['excellon_plot_fill'] = \
            self.app.defaults['excellon_plot_fill'][:7] + \
            (hex(spinner_value)[2:] if int(hex(spinner_value)[2:], 16) > 0 else '00')
        self.app.defaults['excellon_plot_line'] = \
            self.app.defaults['excellon_plot_line'][:7] + \
            (hex(spinner_value)[2:] if int(hex(spinner_value)[2:], 16) > 0 else '00')

    def on_excellon_defaults_button(self):
        self.app.preferencesUiManager.defaults_form_fields["excellon_format_lower_in"].set_value('4')
        self.app.preferencesUiManager.defaults_form_fields["excellon_format_upper_in"].set_value('2')
        self.app.preferencesUiManager.defaults_form_fields["excellon_format_lower_mm"].set_value('3')
        self.app.preferencesUiManager.defaults_form_fields["excellon_format_upper_mm"].set_value('3')
        self.app.preferencesUiManager.defaults_form_fields["excellon_zeros"].set_value('L')
        self.app.preferencesUiManager.defaults_form_fields["excellon_units"].set_value('INCH')

    def on_update_exc_export(self, state):
        """
        This is handling the update of Excellon Export parameters based on the ones in the Excellon General but only
        if the update_excellon_cb checkbox is checked

        :param state: state of the checkbox whose signals is tied to his slot
        :return:
        """
        if state:
            # first try to disconnect
            try:
                self.excellon_format_upper_in_entry.returnPressed.disconnect(self.on_excellon_format_changed)
            except TypeError:
                pass
            try:
                self.excellon_format_lower_in_entry.returnPressed.disconnect(self.on_excellon_format_changed)
            except TypeError:
                pass
            try:
                self.excellon_format_upper_mm_entry.returnPressed.disconnect(self.on_excellon_format_changed)
            except TypeError:
                pass
            try:
                self.excellon_format_lower_mm_entry.returnPressed.disconnect(self.on_excellon_format_changed)
            except TypeError:
                pass

            try:
                self.excellon_zeros_radio.activated_custom.disconnect(self.on_excellon_zeros_changed)
            except TypeError:
                pass
            try:
                self.excellon_units_radio.activated_custom.disconnect(self.on_excellon_zeros_changed)
            except TypeError:
                pass

            # the connect them
            self.excellon_format_upper_in_entry.returnPressed.connect(self.on_excellon_format_changed)
            self.excellon_format_lower_in_entry.returnPressed.connect(self.on_excellon_format_changed)
            self.excellon_format_upper_mm_entry.returnPressed.connect(self.on_excellon_format_changed)
            self.excellon_format_lower_mm_entry.returnPressed.connect(self.on_excellon_format_changed)
            self.excellon_zeros_radio.activated_custom.connect(self.on_excellon_zeros_changed)
            self.excellon_units_radio.activated_custom.connect(self.on_excellon_units_changed)
        else:
            # disconnect the signals
            try:
                self.excellon_format_upper_in_entry.returnPressed.disconnect(self.on_excellon_format_changed)
            except TypeError:
                pass
            try:
                self.excellon_format_lower_in_entry.returnPressed.disconnect(self.on_excellon_format_changed)
            except TypeError:
                pass
            try:
                self.excellon_format_upper_mm_entry.returnPressed.disconnect(self.on_excellon_format_changed)
            except TypeError:
                pass
            try:
                self.excellon_format_lower_mm_entry.returnPressed.disconnect(self.on_excellon_format_changed)
            except TypeError:
                pass

            try:
                self.excellon_zeros_radio.activated_custom.disconnect(self.on_excellon_zeros_changed)
            except TypeError:
                pass
            try:
                self.excellon_units_radio.activated_custom.disconnect(self.on_excellon_zeros_changed)
            except TypeError:
                pass

    def on_excellon_format_changed(self):
        """
        Slot activated when the user changes the Excellon format values in Preferences -> Excellon -> Excellon General
        :return: None
        """
        if self.excellon_units_radio.get_value().upper() == 'METRIC':
            self.app.ui.excellon_defaults_form.excellon_exp_group.format_whole_entry.set_value(
                self.excellon_format_upper_mm_entry.get_value())
            self.app.ui.excellon_defaults_form.excellon_exp_group.format_dec_entry.set_value(
                self.excellon_format_lower_mm_entry.get_value())
        else:
            self.app.ui.excellon_defaults_form.excellon_exp_group.format_whole_entry.set_value(
                self.excellon_format_upper_in_entry.get_value())
            self.app.ui.excellon_defaults_form.excellon_exp_group.format_dec_entry.set_value(
                self.excellon_format_lower_in_entry.get_value())

    def on_excellon_zeros_changed(self, val):
        """
        Slot activated when the user changes the Excellon zeros values in Preferences -> Excellon -> Excellon General
        :return: None
        """
        self.app.ui.excellon_defaults_form.excellon_exp_group.zeros_radio.set_value(val + 'Z')

    def on_excellon_units_changed(self, val):
        """
        Slot activated when the user changes the Excellon unit values in Preferences -> Excellon -> Excellon General
        :return: None
        """
        self.app.ui.excellon_defaults_form.excellon_exp_group.excellon_units_radio.set_value(val)
        self.on_excellon_format_changed()
