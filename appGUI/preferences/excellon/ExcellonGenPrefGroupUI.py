import platform

from PyQt6 import QtWidgets, QtCore, QtGui

from appGUI.GUIElements import FCCheckBox, FCSpinner, RadioSet, FCSliderWithSpinner, FCColorEntry, FCLabel, \
    FCGridLayout, FCFrame
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI
import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ExcellonGenPrefGroupUI(OptionsGroupUI):

    def __init__(self, defaults, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "Excellon Options", parent=parent)
        super(ExcellonGenPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("General")))
        self.decimals = decimals
        self.defaults = defaults

        # #############################################################################################################
        # Plot Frame
        # #############################################################################################################
        self.plot_options_label = FCLabel('<span style="color:blue;"><b>%s</b></span>' % _("Plot Options"))
        self.layout.addWidget(self.plot_options_label)

        plot_frame = FCFrame()
        self.layout.addWidget(plot_frame)

        plot_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        plot_frame.setLayout(plot_grid)

        # Plot CB
        self.plot_cb = FCCheckBox(label=_('Plot'))
        self.plot_cb.setToolTip(
            "Plot (show) this object."
        )
        plot_grid.addWidget(self.plot_cb, 0, 0)

        # Solid CB
        self.solid_cb = FCCheckBox(label=_('Solid'))
        self.solid_cb.setToolTip(
            "Plot as solid circles."
        )
        plot_grid.addWidget(self.solid_cb, 0, 1)

        # Multicolored CB
        self.multicolored_cb = FCCheckBox(label='%s' % _('M-Color'))
        self.multicolored_cb.setToolTip(
            _("Draw polygons in different colors.")
        )
        plot_grid.addWidget(self.multicolored_cb, 0, 2)

        # Number of circle steps for circular aperture linear approximation
        self.circle_steps_label = FCLabel('%s:' % _("Circle Steps"))
        self.circle_steps_label.setToolTip(
            _("The number of circle steps for \n"
              "linear approximation of circles.")
        )
        self.circle_steps_entry = FCSpinner()
        self.circle_steps_entry.set_range(0, 9999)

        plot_grid.addWidget(self.circle_steps_label, 2, 0)
        plot_grid.addWidget(self.circle_steps_entry, 2, 1, 1, 2)

        # separator_line = QtWidgets.QFrame()
        # separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        # separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        # plot_grid.addWidget(separator_line, 1, 0, 1, 3)

        # #############################################################################################################
        # Excellon Format Frame
        # #############################################################################################################
        self.excellon_format_label = FCLabel('<span style="color:green;"><b>%s</b></span>' % _("Excellon Format"))
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
        self.layout.addWidget(self.excellon_format_label)

        format_frame = FCFrame()
        self.layout.addWidget(format_frame)

        format_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        format_frame.setLayout(format_grid)

        self.excellon_format_in_label = FCLabel('%s:' % _("INCH"))
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

        excellon_separator_in_label = FCLabel(' : ')
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

        format_grid.addWidget(self.excellon_format_in_label, 1, 0)
        format_grid.addLayout(hlay1, 1, 1)

        self.excellon_format_mm_label = FCLabel('%s:' % _("METRIC"))
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

        excellon_separator_mm_label = FCLabel(' : ')
        excellon_separator_mm_label.setFixedWidth(5)
        hlay2.addWidget(excellon_separator_mm_label, QtCore.Qt.AlignmentFlag.AlignLeft)

        self.excellon_format_lower_mm_entry = FCSpinner()
        self.excellon_format_lower_mm_entry.set_range(0, 9)
        self.excellon_format_lower_mm_entry.setMinimumWidth(30)
        self.excellon_format_lower_mm_entry.setToolTip(
            _("This numbers signify the number of digits in\n"
              "the decimal part of Excellon coordinates.")
        )
        hlay2.addWidget(self.excellon_format_lower_mm_entry)

        format_grid.addWidget(self.excellon_format_mm_label, 2, 0)
        format_grid.addLayout(hlay2, 2, 1)

        self.excellon_zeros_label = FCLabel('%s:' % _('Zeros'))
        self.excellon_zeros_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.excellon_zeros_label.setToolTip(
            _("This sets the type of Excellon zeros.\n"
              "If LZ then Leading Zeros are kept and\n"
              "Trailing Zeros are removed.\n"
              "If TZ is checked then Trailing Zeros are kept\n"
              "and Leading Zeros are removed.\n\n"
              "This is used when there is no information\n"
              "stored in the Excellon file.")
        )
        format_grid.addWidget(self.excellon_zeros_label, 3, 0)

        self.excellon_zeros_radio = RadioSet([{'label': _('LZ'), 'value': 'L'},
                                              {'label': _('TZ'), 'value': 'T'}])

        format_grid.addWidget(self.excellon_zeros_radio, 3, 1)

        self.excellon_units_label = FCLabel('%s:' % _('Units'))
        self.excellon_units_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
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

        format_grid.addWidget(self.excellon_units_label, 4, 0)
        format_grid.addWidget(self.excellon_units_radio, 4, 1)

        self.update_excellon_cb = FCCheckBox(label=_('Update Export settings'))
        self.update_excellon_cb.setToolTip(
            "If checked, the Excellon Export settings will be updated with the ones above."
        )
        format_grid.addWidget(self.update_excellon_cb, 5, 0, 1, 2)

        # Adding the Excellon Format Defaults Button
        self.excellon_defaults_button = QtWidgets.QPushButton()
        self.excellon_defaults_button.setText(str(_("Restore Defaults")))
        self.excellon_defaults_button.setMinimumWidth(80)
        format_grid.addWidget(self.excellon_defaults_button, 6, 0, 1, 2)

        # #############################################################################################################
        # Optimization Frame
        # #############################################################################################################
        self.excellon_general_label = FCLabel('<span style="color:teal;"><b>%s</b></span>' % _("Path Optimization"))
        self.layout.addWidget(self.excellon_general_label)

        opt_frame = FCFrame()
        self.layout.addWidget(opt_frame)

        opt_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        opt_frame.setLayout(opt_grid)

        self.excellon_optimization_label = FCLabel(_('Algorithm:'))
        self.excellon_optimization_label.setToolTip(
            _("This sets the path optimization algorithm.\n"
              "- Rtre -> Rtree algorithm\n"
              "- MetaHeuristic -> Google OR-Tools algorithm with\n"
              "MetaHeuristic Guided Local Path is used. Default search time is 3sec.\n"
              "- Basic -> Using Google OR-Tools Basic algorithm\n"
              "- TSA -> Using Travelling Salesman algorithm\n"
              "\n"
              "Some options are disabled when the application works in 32bit mode.")
        )

        self.excellon_optimization_radio = RadioSet(
            [
                {'label': _('Rtree'), 'value': 'R'},
                {'label': _('MetaHeuristic'), 'value': 'M'},
                {'label': _('Basic'), 'value': 'B'},
                {'label': _('TSA'), 'value': 'T'}
            ], orientation='vertical', compact=True)

        opt_grid.addWidget(self.excellon_optimization_label, 0, 0)
        opt_grid.addWidget(self.excellon_optimization_radio, 0, 1)

        self.optimization_time_label = FCLabel('%s:' % _('Duration'))
        self.optimization_time_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.optimization_time_label.setToolTip(
            _("When OR-Tools Metaheuristic (MH) is enabled there is a\n"
              "maximum threshold for how much time is spent doing the\n"
              "path optimization. This max duration is set here.\n"
              "In seconds.")

        )

        self.optimization_time_entry = FCSpinner()
        self.optimization_time_entry.set_range(0, 999)

        opt_grid.addWidget(self.optimization_time_label, 2, 0)
        opt_grid.addWidget(self.optimization_time_entry, 2, 1)

        # #############################################################################################################
        # Fusing Frame
        # #############################################################################################################
        # Fuse Tools
        self.join_geo_label = FCLabel('<span style="color:magenta;"><b>%s</b></span>' % _('Join Option'))
        self.layout.addWidget(self.join_geo_label)

        fuse_frame = FCFrame()
        self.layout.addWidget(fuse_frame)

        fuse_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        fuse_frame.setLayout(fuse_grid)

        self.fuse_tools_cb = FCCheckBox(_("Fuse Tools"))
        self.fuse_tools_cb.setToolTip(
            _("When checked, the tools will be merged\n"
              "but only if they share some of their attributes.")
        )
        fuse_grid.addWidget(self.fuse_tools_cb, 0, 0, 1, 2)

        # #############################################################################################################
        # Object Color Frame
        # #############################################################################################################
        self.gerber_color_label = FCLabel('<span style="color:darkorange;"><b>%s</b></span>' % _('Object Color'))
        self.layout.addWidget(self.gerber_color_label)

        obj_frame = FCFrame()
        self.layout.addWidget(obj_frame)

        obj_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        obj_frame.setLayout(obj_grid)

        # Plot Line Color
        self.line_color_label = FCLabel('%s:' % _('Outline'))
        self.line_color_label.setToolTip(
            _("Set the line color for plotted objects.")
        )
        self.line_color_entry = FCColorEntry(icon=QtGui.QIcon(self.app.resource_location + '/set_colors64.png'))

        obj_grid.addWidget(self.line_color_label, 0, 0)
        obj_grid.addWidget(self.line_color_entry, 0, 1)

        # Plot Fill Color
        self.fill_color_label = FCLabel('%s:' % _('Fill'))
        self.fill_color_label.setToolTip(
            _("Set the fill color for plotted objects.\n"
              "First 6 digits are the color and the last 2\n"
              "digits are for alpha (transparency) level.")
        )
        self.fill_color_entry = FCColorEntry(icon=QtGui.QIcon(self.app.resource_location + '/set_colors64.png'))

        obj_grid.addWidget(self.fill_color_label, 2, 0)
        obj_grid.addWidget(self.fill_color_entry, 2, 1)

        # Plot Fill Transparency Level
        self.excellon_alpha_label = FCLabel('%s:' % _('Alpha'))
        self.excellon_alpha_label.setToolTip(
            _("Set the fill transparency for plotted objects.")
        )
        self.excellon_alpha_entry = FCSliderWithSpinner(0, 255, 1)

        obj_grid.addWidget(self.excellon_alpha_label, 4, 0)
        obj_grid.addWidget(self.excellon_alpha_entry, 4, 1)

        FCGridLayout.set_common_column_size([plot_grid, format_grid, opt_grid, obj_grid, fuse_grid], 0)

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

        try:
            import ortools
        except ModuleNotFoundError:
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

    def optimization_selection(self, val):
        if platform.architecture()[0] != '64bit':
            # set Excellon path optimizations algorithm to TSA if the app is run on a 32bit platform
            # modes 'M' or 'B' are not allowed when the app is running in 32bit platform
            if val in ['M', 'B']:
                self.opt_algorithm_radio.blockSignals(True)
                self.excellon_optimization_radio.set_value('T')
                self.opt_algorithm_radio.blockSignals(False)

        if val == 'M':
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
            self.app.ui.excellon_pref_form.excellon_exp_group.format_whole_entry.set_value(
                self.excellon_format_upper_mm_entry.get_value())
            self.app.ui.excellon_pref_form.excellon_exp_group.format_dec_entry.set_value(
                self.excellon_format_lower_mm_entry.get_value())
        else:
            self.app.ui.excellon_pref_form.excellon_exp_group.format_whole_entry.set_value(
                self.excellon_format_upper_in_entry.get_value())
            self.app.ui.excellon_pref_form.excellon_exp_group.format_dec_entry.set_value(
                self.excellon_format_lower_in_entry.get_value())

    def on_excellon_zeros_changed(self, val):
        """
        Slot activated when the user changes the Excellon zeros values in Preferences -> Excellon -> Excellon General
        :return: None
        """
        self.app.ui.excellon_pref_form.excellon_exp_group.zeros_radio.set_value(val + 'Z')

    def on_excellon_units_changed(self, val):
        """
        Slot activated when the user changes the Excellon unit values in Preferences -> Excellon -> Excellon General
        :return: None
        """
        self.app.ui.excellon_pref_form.excellon_exp_group.excellon_units_radio.set_value(val)
        self.on_excellon_format_changed()
