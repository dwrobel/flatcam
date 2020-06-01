from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QSettings

from flatcamGUI.GUIElements import FCCheckBox, FCSpinner, RadioSet, FCEntry
from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import FlatCAMTranslation as fcTranslate
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

        # Solid CB
        self.solid_cb = FCCheckBox(label='%s' % _('Solid'))
        self.solid_cb.setToolTip(
            _("Solid color polygons.")
        )
        grid0.addWidget(self.solid_cb, 0, 0)

        # Multicolored CB
        self.multicolored_cb = FCCheckBox(label='%s' % _('M-Color'))
        self.multicolored_cb.setToolTip(
            _("Draw polygons in different colors.")
        )
        grid0.addWidget(self.multicolored_cb, 0, 1)

        # Plot CB
        self.plot_cb = FCCheckBox(label='%s' % _('Plot'))
        self.plot_options_label.setToolTip(
            _("Plot (show) this object.")
        )
        grid0.addWidget(self.plot_cb, 0, 2)

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

        self.gerber_units_radio = RadioSet([{'label': _('INCH'), 'value': 'IN'},
                                            {'label': _('MM'), 'value': 'MM'}])
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

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 9, 0, 1, 3)

        # Gerber Object Color
        self.gerber_color_label = QtWidgets.QLabel('<b>%s</b>' % _('Gerber Object Color'))
        grid0.addWidget(self.gerber_color_label, 10, 0, 1, 3)

        # Plot Line Color
        self.pl_color_label = QtWidgets.QLabel('%s:' % _('Outline'))
        self.pl_color_label.setToolTip(
            _("Set the line color for plotted objects.")
        )
        self.pl_color_entry = FCEntry()
        self.pl_color_button = QtWidgets.QPushButton()
        self.pl_color_button.setFixedSize(15, 15)

        self.form_box_child_2 = QtWidgets.QHBoxLayout()
        self.form_box_child_2.addWidget(self.pl_color_entry)
        self.form_box_child_2.addWidget(self.pl_color_button)
        self.form_box_child_2.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        grid0.addWidget(self.pl_color_label, 11, 0)
        grid0.addLayout(self.form_box_child_2, 11, 1, 1, 2)

        # Plot Fill Color
        self.pf_color_label = QtWidgets.QLabel('%s:' % _('Fill'))
        self.pf_color_label.setToolTip(
            _("Set the fill color for plotted objects.\n"
              "First 6 digits are the color and the last 2\n"
              "digits are for alpha (transparency) level.")
        )
        self.pf_color_entry = FCEntry()
        self.pf_color_button = QtWidgets.QPushButton()
        self.pf_color_button.setFixedSize(15, 15)

        self.form_box_child_1 = QtWidgets.QHBoxLayout()
        self.form_box_child_1.addWidget(self.pf_color_entry)
        self.form_box_child_1.addWidget(self.pf_color_button)
        self.form_box_child_1.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        grid0.addWidget(self.pf_color_label, 12, 0)
        grid0.addLayout(self.form_box_child_1, 12, 1, 1, 2)

        # Plot Fill Transparency Level
        self.pf_alpha_label = QtWidgets.QLabel('%s:' % _('Alpha'))
        self.pf_alpha_label.setToolTip(
            _("Set the fill transparency for plotted objects.")
        )
        self.pf_color_alpha_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.pf_color_alpha_slider.setMinimum(0)
        self.pf_color_alpha_slider.setMaximum(255)
        self.pf_color_alpha_slider.setSingleStep(1)

        self.pf_color_alpha_spinner = FCSpinner()
        self.pf_color_alpha_spinner.setMinimumWidth(70)
        self.pf_color_alpha_spinner.set_range(0, 255)

        self.form_box_child_3 = QtWidgets.QHBoxLayout()
        self.form_box_child_3.addWidget(self.pf_color_alpha_slider)
        self.form_box_child_3.addWidget(self.pf_color_alpha_spinner)

        grid0.addWidget(self.pf_alpha_label, 13, 0)
        grid0.addLayout(self.form_box_child_3, 13, 1, 1, 2)

        self.layout.addStretch()

        # Setting plot colors signals
        self.pl_color_entry.editingFinished.connect(self.on_pl_color_entry)
        self.pl_color_button.clicked.connect(self.on_pl_color_button)
        self.pf_color_entry.editingFinished.connect(self.on_pf_color_entry)
        self.pf_color_button.clicked.connect(self.on_pf_color_button)
        self.pf_color_alpha_spinner.valueChanged.connect(self.on_pf_color_spinner)
        self.pf_color_alpha_slider.valueChanged.connect(self.on_pf_color_slider)

    # Setting plot colors handlers
    def on_pf_color_entry(self):
        self.app.defaults['gerber_plot_fill'] = self.pf_color_entry.get_value()[:7] + \
            self.app.defaults['gerber_plot_fill'][7:9]
        self.pf_color_button.setStyleSheet("background-color:%s" % str(self.app.defaults['gerber_plot_fill'])[:7])

    def on_pf_color_button(self):
        current_color = QtGui.QColor(self.app.defaults['gerber_plot_fill'][:7])

        c_dialog = QtWidgets.QColorDialog()
        plot_fill_color = c_dialog.getColor(initial=current_color)

        if plot_fill_color.isValid() is False:
            return

        self.pf_color_button.setStyleSheet("background-color:%s" % str(plot_fill_color.name()))

        new_val = str(plot_fill_color.name()) + str(self.app.defaults['gerber_plot_fill'][7:9])
        self.pf_color_entry.set_value(new_val)
        self.app.defaults['gerber_plot_fill'] = new_val

    def on_pf_color_spinner(self):
        spinner_value = self.pf_color_alpha_spinner.value()
        self.pf_color_alpha_slider.setValue(spinner_value)
        self.app.defaults['gerber_plot_fill'] = \
            self.app.defaults['gerber_plot_fill'][:7] + \
            (hex(spinner_value)[2:] if int(hex(spinner_value)[2:], 16) > 0 else '00')
        self.app.defaults['gerber_plot_line'] = \
            self.app.defaults['gerber_plot_line'][:7] + \
            (hex(spinner_value)[2:] if int(hex(spinner_value)[2:], 16) > 0 else '00')

    def on_pf_color_slider(self):
        slider_value = self.pf_color_alpha_slider.value()
        self.pf_color_alpha_spinner.setValue(slider_value)

    def on_pl_color_entry(self):
        self.app.defaults['gerber_plot_line'] = self.pl_color_entry.get_value()[:7] + \
                                                self.app.defaults['gerber_plot_line'][7:9]
        self.pl_color_button.setStyleSheet("background-color:%s" % str(self.app.defaults['gerber_plot_line'])[:7])

    def on_pl_color_button(self):
        current_color = QtGui.QColor(self.app.defaults['gerber_plot_line'][:7])
        # print(current_color)

        c_dialog = QtWidgets.QColorDialog()
        plot_line_color = c_dialog.getColor(initial=current_color)

        if plot_line_color.isValid() is False:
            return

        self.pl_color_button.setStyleSheet("background-color:%s" % str(plot_line_color.name()))

        new_val_line = str(plot_line_color.name()) + str(self.app.defaults['gerber_plot_line'][7:9])
        self.pl_color_entry.set_value(new_val_line)
        self.app.defaults['gerber_plot_line'] = new_val_line
