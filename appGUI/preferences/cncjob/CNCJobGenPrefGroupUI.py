
from PyQt6 import QtGui

from appGUI.GUIElements import FCCheckBox, RadioSet, FCSpinner, FCDoubleSpinner, FCSliderWithSpinner, FCColorEntry, \
    FCLabel, GLay, FCFrame
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI
import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class CNCJobGenPrefGroupUI(OptionsGroupUI):
    def __init__(self, app, parent=None):
        # OptionsGroupUI.__init__(self, "CNC Job General Preferences", parent=None)
        super(CNCJobGenPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("General")))
        self.decimals = app.decimals
        self.options = app.options

        # #############################################################################################################
        # Plot Frame
        # #############################################################################################################
        self.plot_options_label = FCLabel('%s' % _("Plot Options"), color='blue', bold=True)
        self.layout.addWidget(self.plot_options_label)

        plot_frame = FCFrame()
        self.layout.addWidget(plot_frame)

        plot_grid = GLay(v_spacing=5, h_spacing=3)
        plot_frame.setLayout(plot_grid)

        # Plot CB
        self.plot_cb = FCCheckBox(_('Plot Object'))
        self.plot_cb.setToolTip(_("Plot (show) this object."))
        plot_grid.addWidget(self.plot_cb, 0, 0, 1, 2)

        # ###################################################################
        # Number of circle steps for circular aperture linear approximation #
        # ###################################################################
        self.steps_per_circle_label = FCLabel('%s:' % _("Circle Steps"))
        self.steps_per_circle_label.setToolTip(
            _("The number of circle steps for \n"
              "linear approximation of circles.")
        )

        self.steps_per_circle_entry = FCSpinner()
        self.steps_per_circle_entry.set_range(0, 99999)

        plot_grid.addWidget(self.steps_per_circle_label, 2, 0)
        plot_grid.addWidget(self.steps_per_circle_entry, 2, 1)

        # Tool dia for plot
        tdlabel = FCLabel('%s:' % _('Travel dia'))
        tdlabel.setToolTip(
            _("The width of the travel lines to be\n"
              "rendered in the plot.")
        )
        self.tooldia_entry = FCDoubleSpinner()
        self.tooldia_entry.set_range(0, 99999)
        self.tooldia_entry.set_precision(self.decimals)
        self.tooldia_entry.setSingleStep(0.1)
        self.tooldia_entry.setWrapping(True)

        plot_grid.addWidget(tdlabel, 4, 0)
        plot_grid.addWidget(self.tooldia_entry, 4, 1)

        # #############################################################################################################
        # Decimals Frame
        # #############################################################################################################
        self.layout.addWidget(FCLabel('%s' % _("G-code Decimals"), color='teal', bold=True))

        dec_frame = FCFrame()
        self.layout.addWidget(dec_frame)

        dec_grid = GLay(v_spacing=5, h_spacing=3)
        dec_frame.setLayout(dec_grid)

        # Number of decimals to use in GCODE coordinates
        cdeclabel = FCLabel('%s:' % _('Coordinates'))
        cdeclabel.setToolTip(
            _("The number of decimals to be used for \n"
              "the X, Y, Z coordinates in CNC code (GCODE, etc.)")
        )
        self.coords_dec_entry = FCSpinner()
        self.coords_dec_entry.set_range(0, 9)
        self.coords_dec_entry.setWrapping(True)

        dec_grid.addWidget(cdeclabel, 0, 0)
        dec_grid.addWidget(self.coords_dec_entry, 0, 1)

        # Number of decimals to use in GCODE feedrate
        frdeclabel = FCLabel('%s:' % _('Feedrate'))
        frdeclabel.setToolTip(
            _("The number of decimals to be used for \n"
              "the Feedrate parameter in CNC code (GCODE, etc.)")
        )
        self.fr_dec_entry = FCSpinner()
        self.fr_dec_entry.set_range(0, 9)
        self.fr_dec_entry.setWrapping(True)

        dec_grid.addWidget(frdeclabel, 2, 0)
        dec_grid.addWidget(self.fr_dec_entry, 2, 1)

        # The type of coordinates used in the Gcode: Absolute or Incremental
        coords_type_label = FCLabel('%s:' % _('Coordinates type'))
        coords_type_label.setToolTip(
            _("The type of coordinates to be used in Gcode.\n"
              "Can be:\n"
              "- Absolute G90 -> the reference is the origin x=0, y=0\n"
              "- Incremental G91 -> the reference is the previous position")
        )
        self.coords_type_radio = RadioSet([
            {"label": _("Absolute"), "value": "G90"},
            {"label": _("Incremental"), "value": "G91"}
        ], orientation='vertical', compact=True)
        dec_grid.addWidget(coords_type_label, 4, 0)
        dec_grid.addWidget(self.coords_type_radio, 4, 1)

        # hidden for the time being, until implemented
        coords_type_label.hide()
        self.coords_type_radio.hide()

        # Line Endings
        self.line_ending_cb = FCCheckBox(_("Force Windows style line-ending"))
        self.line_ending_cb.setToolTip(
            _("When checked will force a Windows style line-ending\n"
              "(\\r\\n) on non-Windows OS's.")
        )

        dec_grid.addWidget(self.line_ending_cb, 6, 0, 1, 3)

        # separator_line = QtWidgets.QFrame()
        # separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        # separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        # plot_grid.addWidget(separator_line, 12, 0, 1, 2)

        # #############################################################################################################
        # Travel Frame
        # #############################################################################################################
        self.travel_color_label = FCLabel('%s' % _("Travel Line Color"), color='green', bold=True)
        self.layout.addWidget(self.travel_color_label)

        travel_frame = FCFrame()
        self.layout.addWidget(travel_frame)

        travel_grid = GLay(v_spacing=5, h_spacing=3)
        travel_frame.setLayout(travel_grid)

        # Plot Line Color
        self.tline_color_label = FCLabel('%s:' % _('Outline'))
        self.tline_color_label.setToolTip(
            _("Set the travel line color for plotted objects.")
        )
        self.tline_color_entry = FCColorEntry(icon=QtGui.QIcon(self.app.resource_location + '/set_colors64.png'))

        travel_grid.addWidget(self.tline_color_label, 0, 0)
        travel_grid.addWidget(self.tline_color_entry, 0, 1)

        # Plot Fill Color
        self.tfill_color_label = FCLabel('%s:' % _('Fill'))
        self.tfill_color_label.setToolTip(
            _("Set the fill color for plotted objects.\n"
              "First 6 digits are the color and the last 2\n"
              "digits are for alpha (transparency) level.")
        )
        self.tfill_color_entry = FCColorEntry(icon=QtGui.QIcon(self.app.resource_location + '/set_colors64.png'))

        travel_grid.addWidget(self.tfill_color_label, 2, 0)
        travel_grid.addWidget(self.tfill_color_entry, 2, 1)

        # Plot Fill Transparency Level
        self.cncjob_alpha_label = FCLabel('%s:' % _('Alpha'))
        self.cncjob_alpha_label.setToolTip(
            _("Set the fill transparency for plotted objects.")
        )
        self.cncjob_alpha_entry = FCSliderWithSpinner(0, 255, 1)

        travel_grid.addWidget(self.cncjob_alpha_label, 4, 0)
        travel_grid.addWidget(self.cncjob_alpha_entry, 4, 1)

        # separator_line = QtWidgets.QFrame()
        # separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        # separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        # plot_grid.addWidget(separator_line, 17, 0, 1, 2)

        # #############################################################################################################
        # Object Color Frame
        # #############################################################################################################
        self.cnc_color_label = FCLabel('%s' % _("Object Color"), color='darkorange', bold=True)
        self.layout.addWidget(self.cnc_color_label)

        obj_frame = FCFrame()
        self.layout.addWidget(obj_frame)

        obj_grid = GLay(v_spacing=5, h_spacing=3)
        obj_frame.setLayout(obj_grid)

        # Plot Line Color
        self.line_color_label = FCLabel('%s:' % _('Outline'))
        self.line_color_label.setToolTip(
            _("Set the color for plotted objects.")
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

        GLay.set_common_column_size([plot_grid, dec_grid, travel_grid, obj_grid], 0)

        self.layout.addStretch()

        # Setting plot colors signals
        self.tline_color_entry.editingFinished.connect(self.on_tline_color_entry)
        self.tfill_color_entry.editingFinished.connect(self.on_tfill_color_entry)

        self.cncjob_alpha_entry.valueChanged.connect(self.on_cncjob_alpha_changed)  # alpha

        self.line_color_entry.editingFinished.connect(self.on_line_color_entry)
        self.fill_color_entry.editingFinished.connect(self.on_fill_color_entry)

    # ------------------------------------------------------
    # Setting travel colors handlers
    # ------------------------------------------------------
    def on_tfill_color_entry(self):
        self.app.options['cncjob_travel_fill'] = self.tfill_color_entry.get_value()[:7] + \
                                                  self.app.options['cncjob_travel_fill'][7:9]

    def on_tline_color_entry(self):
        self.app.options['cncjob_travel_line'] = self.tline_color_entry.get_value()[:7] + \
                                                  self.app.options['cncjob_travel_line'][7:9]

    def on_cncjob_alpha_changed(self, spinner_value):
        self.app.options['cncjob_travel_fill'] = \
            self.app.options['cncjob_travel_fill'][:7] + \
            (hex(spinner_value)[2:] if int(hex(spinner_value)[2:], 16) > 0 else '00')
        self.app.options['cncjob_travel_line'] = \
            self.app.options['cncjob_travel_line'][:7] + \
            (hex(spinner_value)[2:] if int(hex(spinner_value)[2:], 16) > 0 else '00')

    # ------------------------------------------------------
    # Setting plot colors handlers
    # ------------------------------------------------------
    def on_fill_color_entry(self):
        self.app.options['cncjob_plot_fill'] = self.fill_color_entry.get_value()[:7] + \
                                                  self.app.options['cncjob_plot_fill'][7:9]

    def on_line_color_entry(self):
        self.app.options['cncjob_plot_line'] = self.line_color_entry.get_value()[:7] + \
                                                  self.app.options['cncjob_plot_line'][7:9]
