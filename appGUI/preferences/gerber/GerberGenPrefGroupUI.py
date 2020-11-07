from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QSettings

from appGUI.GUIElements import FCCheckBox, FCSpinner, RadioSet, FCButton, FCSliderWithSpinner, FCColorEntry
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


class GerberGenPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "Gerber General Preferences", parent=parent)
        super(GerberGenPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Gerber General")))
        self.decimals = decimals

        # ## Plot options
        self.plot_options_label = QtWidgets.QLabel("<b>%s:</b>" % _("Plot Options"))
        self.layout.addWidget(self.plot_options_label)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        # Plot CB
        self.plot_cb = FCCheckBox(label='%s' % _('Plot'))
        self.plot_options_label.setToolTip(
            _("Plot (show) this object.")
        )
        grid0.addWidget(self.plot_cb, 0, 0)

        # Solid CB
        self.solid_cb = FCCheckBox(label='%s' % _('Solid'))
        self.solid_cb.setToolTip(
            _("Solid color polygons.")
        )
        grid0.addWidget(self.solid_cb, 0, 1)

        # Multicolored CB
        self.multicolored_cb = FCCheckBox(label='%s' % _('M-Color'))
        self.multicolored_cb.setToolTip(
            _("Draw polygons in different colors.")
        )
        grid0.addWidget(self.multicolored_cb, 0, 2)

        # Number of circle steps for circular aperture linear approximation
        self.circle_steps_label = QtWidgets.QLabel('%s:' % _("Circle Steps"))
        self.circle_steps_label.setToolTip(
            _("The number of circle steps for Gerber \n"
              "circular aperture linear approximation.")
        )
        self.circle_steps_entry = FCSpinner()
        self.circle_steps_entry.set_range(0, 9999)

        grid0.addWidget(self.circle_steps_label, 1, 0)
        grid0.addWidget(self.circle_steps_entry, 1, 1, 1, 2)

        grid0.addWidget(QtWidgets.QLabel(''), 2, 0, 1, 3)

        # Default format for Gerber
        self.gerber_default_label = QtWidgets.QLabel('<b>%s:</b>' % _('Default Values'))
        self.gerber_default_label.setToolTip(
            _("Those values will be used as fallback values\n"
              "in case that they are not found in the Gerber file.")
        )

        grid0.addWidget(self.gerber_default_label, 3, 0, 1, 3)

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

        grid0.addWidget(self.gerber_units_label, 4, 0)
        grid0.addWidget(self.gerber_units_radio, 4, 1, 1, 2)

        # Gerber Zeros
        self.gerber_zeros_label = QtWidgets.QLabel('%s:' % _('Zeros'))
        self.gerber_zeros_label.setAlignment(QtCore.Qt.AlignLeft)
        self.gerber_zeros_label.setToolTip(
            _("This sets the type of Gerber zeros.\n"
              "If LZ then Leading Zeros are removed and\n"
              "Trailing Zeros are kept.\n"
              "If TZ is checked then Trailing Zeros are removed\n"
              "and Leading Zeros are kept.")
        )

        self.gerber_zeros_radio = RadioSet([{'label': _('LZ'), 'value': 'L'},
                                            {'label': _('TZ'), 'value': 'T'}])
        self.gerber_zeros_radio.setToolTip(
            _("This sets the type of Gerber zeros.\n"
              "If LZ then Leading Zeros are removed and\n"
              "Trailing Zeros are kept.\n"
              "If TZ is checked then Trailing Zeros are removed\n"
              "and Leading Zeros are kept.")
        )

        grid0.addWidget(self.gerber_zeros_label, 5, 0)
        grid0.addWidget(self.gerber_zeros_radio, 5, 1, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 6, 0, 1, 3)

        # Apertures Cleaning
        self.gerber_clean_cb = FCCheckBox(label='%s' % _('Clean Apertures'))
        self.gerber_clean_cb.setToolTip(
            _("Will remove apertures that do not have geometry\n"
              "thus lowering the number of apertures in the Gerber object.")
        )
        grid0.addWidget(self.gerber_clean_cb, 7, 0, 1, 3)

        # Apply Extra Buffering
        self.gerber_extra_buffering = FCCheckBox(label='%s' % _('Polarity change buffer'))
        self.gerber_extra_buffering.setToolTip(
            _("Will apply extra buffering for the\n"
              "solid geometry when we have polarity changes.\n"
              "May help loading Gerber files that otherwise\n"
              "do not load correctly.")
        )
        grid0.addWidget(self.gerber_extra_buffering, 8, 0, 1, 3)

        # Store colors
        self.store_colors_cb = FCCheckBox(label='%s' % _('Store colors'))
        self.store_colors_cb.setToolTip(
            _("It will store the set colors for Gerber objects.\n"
              "Those will be used each time the application is started.")
        )
        grid0.addWidget(self.store_colors_cb, 11, 0)

        # Clear stored colors
        self.clear_colors_button = FCButton('%s' % _('Clear Colors'))
        self.clear_colors_button.setIcon(QtGui.QIcon(self.app.resource_location + '/trash32.png'))
        self.clear_colors_button.setToolTip(
            _("Reset the colors associated with Gerber objects.")
        )
        grid0.addWidget(self.clear_colors_button, 11, 1, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 13, 0, 1, 3)

        # Gerber Object Color
        self.gerber_color_label = QtWidgets.QLabel('<b>%s</b>' % _('Object Color'))
        grid0.addWidget(self.gerber_color_label, 15, 0, 1, 3)

        # Plot Line Color
        self.line_color_label = QtWidgets.QLabel('%s:' % _('Outline'))
        self.line_color_label.setToolTip(
            _("Set the line color for plotted objects.")
        )
        self.line_color_entry = FCColorEntry()

        grid0.addWidget(self.line_color_label, 17, 0)
        grid0.addWidget(self.line_color_entry, 17, 1, 1, 2)

        # Plot Fill Color
        self.fill_color_label = QtWidgets.QLabel('%s:' % _('Fill'))
        self.fill_color_label.setToolTip(
            _("Set the fill color for plotted objects.\n"
              "First 6 digits are the color and the last 2\n"
              "digits are for alpha (transparency) level.")
        )
        self.fill_color_entry = FCColorEntry()

        grid0.addWidget(self.fill_color_label, 20, 0)
        grid0.addWidget(self.fill_color_entry, 20, 1, 1, 2)

        # Plot Fill Transparency Level
        self.gerber_alpha_label = QtWidgets.QLabel('%s:' % _('Alpha'))
        self.gerber_alpha_label.setToolTip(
            _("Set the fill transparency for plotted objects.")
        )
        self.gerber_alpha_entry = FCSliderWithSpinner(0, 255, 1)

        grid0.addWidget(self.gerber_alpha_label, 22, 0)
        grid0.addWidget(self.gerber_alpha_entry, 22, 1, 1, 2)

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
