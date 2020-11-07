from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QSettings

from appGUI.GUIElements import FCCheckBox, RadioSet, FCSpinner, FCDoubleSpinner, FCSliderWithSpinner, FCColorEntry
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


class CNCJobGenPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "CNC Job General Preferences", parent=None)
        super(CNCJobGenPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("CNC Job General")))
        self.decimals = decimals

        # ## Plot options
        self.plot_options_label = QtWidgets.QLabel("<b>%s:</b>" % _("Plot Options"))
        self.layout.addWidget(self.plot_options_label)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)

        # Plot CB
        # self.plot_cb = QtWidgets.QCheckBox('Plot')
        self.plot_cb = FCCheckBox(_('Plot Object'))
        self.plot_cb.setToolTip(_("Plot (show) this object."))
        grid0.addWidget(self.plot_cb, 0, 0, 1, 2)

        # ###################################################################
        # Number of circle steps for circular aperture linear approximation #
        # ###################################################################
        self.steps_per_circle_label = QtWidgets.QLabel('%s:' % _("Circle Steps"))
        self.steps_per_circle_label.setToolTip(
            _("The number of circle steps for <b>GCode</b> \n"
              "circle and arc shapes linear approximation.")
        )
        grid0.addWidget(self.steps_per_circle_label, 3, 0)
        self.steps_per_circle_entry = FCSpinner()
        self.steps_per_circle_entry.set_range(0, 99999)
        grid0.addWidget(self.steps_per_circle_entry, 3, 1)

        # Tool dia for plot
        tdlabel = QtWidgets.QLabel('%s:' % _('Travel dia'))
        tdlabel.setToolTip(
            _("The width of the travel lines to be\n"
              "rendered in the plot.")
        )
        self.tooldia_entry = FCDoubleSpinner()
        self.tooldia_entry.set_range(0, 99999)
        self.tooldia_entry.set_precision(self.decimals)
        self.tooldia_entry.setSingleStep(0.1)
        self.tooldia_entry.setWrapping(True)

        grid0.addWidget(tdlabel, 4, 0)
        grid0.addWidget(self.tooldia_entry, 4, 1)

        # add a space
        grid0.addWidget(QtWidgets.QLabel('<b>%s:</b>' % _("G-code Decimals")), 5, 0, 1, 2)

        # Number of decimals to use in GCODE coordinates
        cdeclabel = QtWidgets.QLabel('%s:' % _('Coordinates'))
        cdeclabel.setToolTip(
            _("The number of decimals to be used for \n"
              "the X, Y, Z coordinates in CNC code (GCODE, etc.)")
        )
        self.coords_dec_entry = FCSpinner()
        self.coords_dec_entry.set_range(0, 9)
        self.coords_dec_entry.setWrapping(True)

        grid0.addWidget(cdeclabel, 6, 0)
        grid0.addWidget(self.coords_dec_entry, 6, 1)

        # Number of decimals to use in GCODE feedrate
        frdeclabel = QtWidgets.QLabel('%s:' % _('Feedrate'))
        frdeclabel.setToolTip(
            _("The number of decimals to be used for \n"
              "the Feedrate parameter in CNC code (GCODE, etc.)")
        )
        self.fr_dec_entry = FCSpinner()
        self.fr_dec_entry.set_range(0, 9)
        self.fr_dec_entry.setWrapping(True)

        grid0.addWidget(frdeclabel, 7, 0)
        grid0.addWidget(self.fr_dec_entry, 7, 1)

        # The type of coordinates used in the Gcode: Absolute or Incremental
        coords_type_label = QtWidgets.QLabel('%s:' % _('Coordinates type'))
        coords_type_label.setToolTip(
            _("The type of coordinates to be used in Gcode.\n"
              "Can be:\n"
              "- Absolute G90 -> the reference is the origin x=0, y=0\n"
              "- Incremental G91 -> the reference is the previous position")
        )
        self.coords_type_radio = RadioSet([
            {"label": _("Absolute"), "value": "G90"},
            {"label": _("Incremental"), "value": "G91"}
        ], orientation='vertical', stretch=False)
        grid0.addWidget(coords_type_label, 8, 0)
        grid0.addWidget(self.coords_type_radio, 8, 1)

        # hidden for the time being, until implemented
        coords_type_label.hide()
        self.coords_type_radio.hide()

        # Line Endings
        self.line_ending_cb = FCCheckBox(_("Force Windows style line-ending"))
        self.line_ending_cb.setToolTip(
            _("When checked will force a Windows style line-ending\n"
              "(\\r\\n) on non-Windows OS's.")
        )

        grid0.addWidget(self.line_ending_cb, 9, 0, 1, 3)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 12, 0, 1, 2)

        # Travel Line Color
        self.travel_color_label = QtWidgets.QLabel('<b>%s</b>' % _('Travel Line Color'))
        grid0.addWidget(self.travel_color_label, 13, 0, 1, 2)

        # Plot Line Color
        self.tline_color_label = QtWidgets.QLabel('%s:' % _('Outline'))
        self.tline_color_label.setToolTip(
            _("Set the travel line color for plotted objects.")
        )
        self.tline_color_entry = FCColorEntry()

        grid0.addWidget(self.tline_color_label, 14, 0)
        grid0.addWidget(self.tline_color_entry, 14, 1)

        # Plot Fill Color
        self.tfill_color_label = QtWidgets.QLabel('%s:' % _('Fill'))
        self.tfill_color_label.setToolTip(
            _("Set the fill color for plotted objects.\n"
              "First 6 digits are the color and the last 2\n"
              "digits are for alpha (transparency) level.")
        )
        self.tfill_color_entry = FCColorEntry()

        grid0.addWidget(self.tfill_color_label, 15, 0)
        grid0.addWidget(self.tfill_color_entry, 15, 1)

        # Plot Fill Transparency Level
        self.cncjob_alpha_label = QtWidgets.QLabel('%s:' % _('Alpha'))
        self.cncjob_alpha_label.setToolTip(
            _("Set the fill transparency for plotted objects.")
        )
        self.cncjob_alpha_entry = FCSliderWithSpinner(0, 255, 1)

        grid0.addWidget(self.cncjob_alpha_label, 16, 0)
        grid0.addWidget(self.cncjob_alpha_entry, 16, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 17, 0, 1, 2)

        # CNCJob Object Color
        self.cnc_color_label = QtWidgets.QLabel('<b>%s</b>' % _('Object Color'))
        grid0.addWidget(self.cnc_color_label, 18, 0, 1, 2)

        # Plot Line Color
        self.line_color_label = QtWidgets.QLabel('%s:' % _('Outline'))
        self.line_color_label.setToolTip(
            _("Set the color for plotted objects.")
        )
        self.line_color_entry = FCColorEntry()

        grid0.addWidget(self.line_color_label, 19, 0)
        grid0.addWidget(self.line_color_entry, 19, 1)

        # Plot Fill Color
        self.fill_color_label = QtWidgets.QLabel('%s:' % _('Fill'))
        self.fill_color_label.setToolTip(
            _("Set the fill color for plotted objects.\n"
              "First 6 digits are the color and the last 2\n"
              "digits are for alpha (transparency) level.")
        )
        self.fill_color_entry = FCColorEntry()

        grid0.addWidget(self.fill_color_label, 20, 0)
        grid0.addWidget(self.fill_color_entry, 20, 1)

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
        self.app.defaults['cncjob_travel_fill'] = self.tfill_color_entry.get_value()[:7] + \
                                                  self.app.defaults['cncjob_travel_fill'][7:9]

    def on_tline_color_entry(self):
        self.app.defaults['cncjob_travel_line'] = self.tline_color_entry.get_value()[:7] + \
                                                  self.app.defaults['cncjob_travel_line'][7:9]

    def on_cncjob_alpha_changed(self, spinner_value):
        self.app.defaults['cncjob_travel_fill'] = \
            self.app.defaults['cncjob_travel_fill'][:7] + \
            (hex(spinner_value)[2:] if int(hex(spinner_value)[2:], 16) > 0 else '00')
        self.app.defaults['cncjob_travel_line'] = \
            self.app.defaults['cncjob_travel_line'][:7] + \
            (hex(spinner_value)[2:] if int(hex(spinner_value)[2:], 16) > 0 else '00')

    # ------------------------------------------------------
    # Setting plot colors handlers
    # ------------------------------------------------------
    def on_fill_color_entry(self):
        self.app.defaults['cncjob_plot_fill'] = self.fill_color_entry.get_value()[:7] + \
                                                  self.app.defaults['cncjob_plot_fill'][7:9]

    def on_line_color_entry(self):
        self.app.defaults['cncjob_plot_line'] = self.line_color_entry.get_value()[:7] + \
                                                  self.app.defaults['cncjob_plot_line'][7:9]
