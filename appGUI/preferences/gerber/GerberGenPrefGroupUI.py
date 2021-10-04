from PyQt6 import QtWidgets, QtCore, QtGui

from appGUI.GUIElements import FCCheckBox, FCSpinner, RadioSet, FCButton, FCSliderWithSpinner, FCColorEntry, FCLabel, \
    FCGridLayout, FCFrame
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GerberGenPrefGroupUI(OptionsGroupUI):
    def __init__(self, defaults, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "Gerber General Preferences", parent=parent)
        super(GerberGenPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Gerber General")))
        self.decimals = decimals
        self.defaults = defaults

        # ## Plot options
        self.plot_options_label = FCLabel('<span style="color:blue;"><b>%s</b></span>' % _("Plot Options"))
        self.layout.addWidget(self.plot_options_label)

        # #############################################################################################################
        # Plot Frame
        # #############################################################################################################

        plot_frame = FCFrame()
        self.layout.addWidget(plot_frame)

        # ## Grid Layout
        plot_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        plot_frame.setLayout(plot_grid)

        # Plot CB
        self.plot_cb = FCCheckBox(label='%s' % _('Plot'))
        self.plot_options_label.setToolTip(
            _("Plot (show) this object.")
        )
        plot_grid.addWidget(self.plot_cb, 0, 0)

        # Solid CB
        self.solid_cb = FCCheckBox(label='%s' % _('Solid'))
        self.solid_cb.setToolTip(
            _("Solid color polygons.")
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

        # #############################################################################################################
        # Default Values Frame
        # #############################################################################################################

        # Default format for Gerber
        self.gerber_default_label = FCLabel('<span style="color:green;"><b>%s</b></span>' % _('Default Values'))
        self.gerber_default_label.setToolTip(
            _("Those values will be used as fallback values\n"
              "in case that they are not found in the Gerber file.")
        )

        self.layout.addWidget(self.gerber_default_label)

        def_frame = FCFrame()
        self.layout.addWidget(def_frame)

        # ## Grid Layout
        def_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        def_frame.setLayout(def_grid)

        # Gerber Units
        self.gerber_units_label = FCLabel('%s:' % _('Units'))
        self.gerber_units_label.setToolTip(
            _("The units used in the Gerber file.")
        )

        self.gerber_units_radio = RadioSet([{'label': _('Inch'), 'value': 'IN'},
                                            {'label': _('mm'), 'value': 'MM'}], compact=True)
        self.gerber_units_radio.setToolTip(
            _("The units used in the Gerber file.")
        )

        def_grid.addWidget(self.gerber_units_label, 0, 0)
        def_grid.addWidget(self.gerber_units_radio, 0, 1, 1, 2)

        # Gerber Zeros
        self.gerber_zeros_label = FCLabel('%s:' % _('Zeros'))
        self.gerber_zeros_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.gerber_zeros_label.setToolTip(
            _("This sets the type of Gerber zeros.\n"
              "If LZ then Leading Zeros are removed and\n"
              "Trailing Zeros are kept.\n"
              "If TZ is checked then Trailing Zeros are removed\n"
              "and Leading Zeros are kept.")
        )

        self.gerber_zeros_radio = RadioSet([{'label': _('LZ'), 'value': 'L'},
                                            {'label': _('TZ'), 'value': 'T'}], compact=True)
        self.gerber_zeros_radio.setToolTip(
            _("This sets the type of Gerber zeros.\n"
              "If LZ then Leading Zeros are removed and\n"
              "Trailing Zeros are kept.\n"
              "If TZ is checked then Trailing Zeros are removed\n"
              "and Leading Zeros are kept.")
        )

        def_grid.addWidget(self.gerber_zeros_label, 2, 0)
        def_grid.addWidget(self.gerber_zeros_radio, 2, 1, 1, 2)

        # #############################################################################################################
        # Parameters Frame
        # #############################################################################################################
        self.param_label = FCLabel('<span style="color:indigo;"><b>%s</b></span>' % _('Parameters'))
        self.layout.addWidget(self.param_label)

        par_frame = FCFrame()
        self.layout.addWidget(par_frame)

        # ## Grid Layout
        param_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        par_frame.setLayout(param_grid)

        # Apertures Cleaning
        self.gerber_clean_cb = FCCheckBox(label='%s' % _('Clean Apertures'))
        self.gerber_clean_cb.setToolTip(
            _("Will remove apertures that do not have geometry\n"
              "thus lowering the number of apertures in the Gerber object.")
        )
        param_grid.addWidget(self.gerber_clean_cb, 0, 0, 1, 3)

        # Apply Extra Buffering
        self.gerber_extra_buffering = FCCheckBox(label='%s' % _('Polarity change buffer'))
        self.gerber_extra_buffering.setToolTip(
            _("Will apply extra buffering for the\n"
              "solid geometry when we have polarity changes.\n"
              "May help loading Gerber files that otherwise\n"
              "do not load correctly.")
        )
        param_grid.addWidget(self.gerber_extra_buffering, 2, 0, 1, 3)

        # Store colors
        self.store_colors_cb = FCCheckBox(label='%s' % _('Store colors'))
        self.store_colors_cb.setToolTip(
            _("It will store the set colors for Gerber objects.\n"
              "Those will be used each time the application is started.")
        )

        # Clear stored colors
        self.clear_colors_button = FCButton()
        # self.clear_colors_button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.clear_colors_button.setText('%s' % _('Clear Colors'))
        self.clear_colors_button.setIcon(QtGui.QIcon(self.app.resource_location + '/trash32.png'))
        self.clear_colors_button.setToolTip(
            _("Reset the colors associated with Gerber objects.")
        )

        param_grid.addWidget(self.store_colors_cb, 4, 0, 1, 3)
        param_grid.addWidget(self.clear_colors_button, 6, 0, 1, 3)

        # separator_line = QtWidgets.QFrame()
        # separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        # separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        # plot_grid.addWidget(separator_line, 13, 0, 1, 3)

        # #############################################################################################################
        # Object Frame
        # #############################################################################################################
        # Gerber Object Color
        self.gerber_color_label = FCLabel('<span style="color:darkorange;"><b>%s</b></span>' % _('Object Color'))
        self.layout.addWidget(self.gerber_color_label)

        obj_frame = FCFrame()
        self.layout.addWidget(obj_frame)

        # ## Grid Layout
        obj_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        obj_frame.setLayout(obj_grid)

        # Plot Line Color
        self.line_color_label = FCLabel('%s:' % _('Outline'))
        self.line_color_label.setToolTip(
            _("Set the line color for plotted objects.")
        )
        self.line_color_entry = FCColorEntry()

        obj_grid.addWidget(self.line_color_label, 0, 0)
        obj_grid.addWidget(self.line_color_entry, 0, 1, 1, 2)

        # Plot Fill Color
        self.fill_color_label = FCLabel('%s:' % _('Fill'))
        self.fill_color_label.setToolTip(
            _("Set the fill color for plotted objects.\n"
              "First 6 digits are the color and the last 2\n"
              "digits are for alpha (transparency) level.")
        )
        self.fill_color_entry = FCColorEntry()

        obj_grid.addWidget(self.fill_color_label, 2, 0)
        obj_grid.addWidget(self.fill_color_entry, 2, 1, 1, 2)

        # Plot Fill Transparency Level
        self.gerber_alpha_label = FCLabel('%s:' % _('Alpha'))
        self.gerber_alpha_label.setToolTip(
            _("Set the fill transparency for plotted objects.")
        )
        self.gerber_alpha_entry = FCSliderWithSpinner(0, 255, 1)

        obj_grid.addWidget(self.gerber_alpha_label, 4, 0)
        obj_grid.addWidget(self.gerber_alpha_entry, 4, 1, 1, 2)

        FCGridLayout.set_common_column_size([plot_grid, param_grid, def_grid, obj_grid], 0)

        self.layout.addStretch()

        # Setting plot colors signals
        self.line_color_entry.editingFinished.connect(self.on_line_color_changed)
        self.fill_color_entry.editingFinished.connect(self.on_fill_color_changed)

        self.gerber_alpha_entry.valueChanged.connect(self.on_gerber_alpha_changed)     # alpha

        self.clear_colors_button.clicked.connect(self.on_colors_clear_clicked)

    # Setting plot colors handlers
    def on_fill_color_changed(self):
        self.app.defaults['gerber_plot_fill'] = self.fill_color_entry.get_value()[:7] + \
                                                self.app.defaults['gerber_plot_fill'][7:9]

    def on_gerber_alpha_changed(self, spinner_value):
        self.app.defaults['gerber_plot_fill'] = \
            self.app.defaults['gerber_plot_fill'][:7] + \
            (hex(spinner_value)[2:] if int(hex(spinner_value)[2:], 16) > 0 else '00')
        self.app.defaults['gerber_plot_line'] = \
            self.app.defaults['gerber_plot_line'][:7] + \
            (hex(spinner_value)[2:] if int(hex(spinner_value)[2:], 16) > 0 else '00')

    def on_line_color_changed(self):
        self.app.defaults['gerber_plot_line'] = self.line_color_entry.get_value()[:7] + \
                                                self.app.defaults['gerber_plot_line'][7:9]

    def on_colors_clear_clicked(self):
        self.app.defaults['gerber_color_list'].clear()
        self.app.inform.emit('[WARNING_NOTCL] %s' % _("Stored colors for Gerber objects are deleted."))
