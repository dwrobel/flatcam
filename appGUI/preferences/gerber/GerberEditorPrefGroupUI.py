from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings

from appGUI.GUIElements import FCSpinner, FCDoubleSpinner, FCComboBox, FCEntry, RadioSet, NumericalEvalTupleEntry
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


class GerberEditorPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "Gerber Adv. Options Preferences", parent=parent)
        super(GerberEditorPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Gerber Editor")))
        self.decimals = decimals

        # Advanced Gerber Parameters
        self.param_label = QtWidgets.QLabel("<b>%s:</b>" % _("Parameters"))
        self.param_label.setToolTip(
            _("A list of Gerber Editor parameters.")
        )
        self.layout.addWidget(self.param_label)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        # Selection Limit
        self.sel_limit_label = QtWidgets.QLabel('%s:' % _("Selection limit"))
        self.sel_limit_label.setToolTip(
            _("Set the number of selected Gerber geometry\n"
              "items above which the utility geometry\n"
              "becomes just a selection rectangle.\n"
              "Increases the performance when moving a\n"
              "large number of geometric elements.")
        )
        self.sel_limit_entry = FCSpinner()
        self.sel_limit_entry.set_range(0, 9999)

        grid0.addWidget(self.sel_limit_label, 0, 0)
        grid0.addWidget(self.sel_limit_entry, 0, 1)

        # New aperture code
        self.addcode_entry_lbl = QtWidgets.QLabel('%s:' % _('New Aperture code'))
        self.addcode_entry_lbl.setToolTip(
            _("Code for the new aperture")
        )

        self.addcode_entry = FCSpinner()
        self.addcode_entry.set_range(10, 99)
        self.addcode_entry.setWrapping(True)

        grid0.addWidget(self.addcode_entry_lbl, 1, 0)
        grid0.addWidget(self.addcode_entry, 1, 1)

        # New aperture size
        self.addsize_entry_lbl = QtWidgets.QLabel('%s:' % _('New Aperture size'))
        self.addsize_entry_lbl.setToolTip(
            _("Size for the new aperture")
        )

        self.addsize_entry = FCDoubleSpinner()
        self.addsize_entry.set_range(0, 100)
        self.addsize_entry.set_precision(self.decimals)

        grid0.addWidget(self.addsize_entry_lbl, 2, 0)
        grid0.addWidget(self.addsize_entry, 2, 1)

        # New aperture type
        self.addtype_combo_lbl = QtWidgets.QLabel('%s:' % _('New Aperture type'))
        self.addtype_combo_lbl.setToolTip(
            _("Type for the new aperture.\n"
              "Can be 'C', 'R' or 'O'.")
        )

        self.addtype_combo = FCComboBox()
        self.addtype_combo.addItems(['C', 'R', 'O'])

        grid0.addWidget(self.addtype_combo_lbl, 3, 0)
        grid0.addWidget(self.addtype_combo, 3, 1)

        # Number of pads in a pad array
        self.grb_array_size_label = QtWidgets.QLabel('%s:' % _('Nr of pads'))
        self.grb_array_size_label.setToolTip(
            _("Specify how many pads to be in the array.")
        )

        self.grb_array_size_entry = FCSpinner()
        self.grb_array_size_entry.set_range(0, 9999)

        grid0.addWidget(self.grb_array_size_label, 4, 0)
        grid0.addWidget(self.grb_array_size_entry, 4, 1)

        self.adddim_label = QtWidgets.QLabel('%s:' % _('Aperture Dimensions'))
        self.adddim_label.setToolTip(
            _("Diameters of the tools, separated by comma.\n"
              "The value of the diameter has to use the dot decimals separator.\n"
              "Valid values: 0.3, 1.0")
        )
        self.adddim_entry = NumericalEvalTupleEntry(border_color='#0069A9')

        grid0.addWidget(self.adddim_label, 5, 0)
        grid0.addWidget(self.adddim_entry, 5, 1)

        self.grb_array_linear_label = QtWidgets.QLabel('<b>%s:</b>' % _('Linear Pad Array'))
        grid0.addWidget(self.grb_array_linear_label, 6, 0, 1, 2)

        # Linear Pad Array direction
        self.grb_axis_label = QtWidgets.QLabel('%s:' % _('Linear Direction'))
        self.grb_axis_label.setToolTip(
            _("Direction on which the linear array is oriented:\n"
              "- 'X' - horizontal axis \n"
              "- 'Y' - vertical axis or \n"
              "- 'Angle' - a custom angle for the array inclination")
        )

        self.grb_axis_radio = RadioSet([{'label': _('X'), 'value': 'X'},
                                        {'label': _('Y'), 'value': 'Y'},
                                        {'label': _('Angle'), 'value': 'A'}])

        grid0.addWidget(self.grb_axis_label, 7, 0)
        grid0.addWidget(self.grb_axis_radio, 7, 1)

        # Linear Pad Array pitch distance
        self.grb_pitch_label = QtWidgets.QLabel('%s:' % _('Pitch'))
        self.grb_pitch_label.setToolTip(
            _("Pitch = Distance between elements of the array.")
        )
        # self.drill_pitch_label.setMinimumWidth(100)
        self.grb_pitch_entry = FCDoubleSpinner()
        self.grb_pitch_entry.set_precision(self.decimals)

        grid0.addWidget(self.grb_pitch_label, 8, 0)
        grid0.addWidget(self.grb_pitch_entry, 8, 1)

        # Linear Pad Array custom angle
        self.grb_angle_label = QtWidgets.QLabel('%s:' % _('Angle'))
        self.grb_angle_label.setToolTip(
            _("Angle at which each element in circular array is placed.")
        )
        self.grb_angle_entry = FCDoubleSpinner()
        self.grb_angle_entry.set_precision(self.decimals)
        self.grb_angle_entry.set_range(-360, 360)
        self.grb_angle_entry.setSingleStep(5)

        grid0.addWidget(self.grb_angle_label, 9, 0)
        grid0.addWidget(self.grb_angle_entry, 9, 1)

        self.grb_array_circ_label = QtWidgets.QLabel('<b>%s:</b>' % _('Circular Pad Array'))
        grid0.addWidget(self.grb_array_circ_label, 10, 0, 1, 2)

        # Circular Pad Array direction
        self.grb_circular_direction_label = QtWidgets.QLabel('%s:' % _('Circular Direction'))
        self.grb_circular_direction_label.setToolTip(
            _("Direction for circular array.\n"
              "Can be CW = clockwise or CCW = counter clockwise.")
        )

        self.grb_circular_dir_radio = RadioSet([{'label': _('CW'), 'value': 'CW'},
                                                {'label': _('CCW'), 'value': 'CCW'}])

        grid0.addWidget(self.grb_circular_direction_label, 11, 0)
        grid0.addWidget(self.grb_circular_dir_radio, 11, 1)

        # Circular Pad Array Angle
        self.grb_circular_angle_label = QtWidgets.QLabel('%s:' % _('Circular Angle'))
        self.grb_circular_angle_label.setToolTip(
            _("Angle at which each element in circular array is placed.")
        )
        self.grb_circular_angle_entry = FCDoubleSpinner()
        self.grb_circular_angle_entry.set_precision(self.decimals)
        self.grb_circular_angle_entry.set_range(-360, 360)

        self.grb_circular_angle_entry.setSingleStep(5)

        grid0.addWidget(self.grb_circular_angle_label, 12, 0)
        grid0.addWidget(self.grb_circular_angle_entry, 12, 1)

        self.grb_array_tools_b_label = QtWidgets.QLabel('<b>%s:</b>' % _('Buffer Tool'))
        grid0.addWidget(self.grb_array_tools_b_label, 13, 0, 1, 2)

        # Buffer Distance
        self.grb_buff_label = QtWidgets.QLabel('%s:' % _('Buffer distance'))
        self.grb_buff_label.setToolTip(
            _("Distance at which to buffer the Gerber element.")
        )
        self.grb_buff_entry = FCDoubleSpinner()
        self.grb_buff_entry.set_precision(self.decimals)
        self.grb_buff_entry.set_range(-9999, 9999)

        grid0.addWidget(self.grb_buff_label, 14, 0)
        grid0.addWidget(self.grb_buff_entry, 14, 1)

        self.grb_array_tools_s_label = QtWidgets.QLabel('<b>%s:</b>' % _('Scale Tool'))
        grid0.addWidget(self.grb_array_tools_s_label, 15, 0, 1, 2)

        # Scale Factor
        self.grb_scale_label = QtWidgets.QLabel('%s:' % _('Scale factor'))
        self.grb_scale_label.setToolTip(
            _("Factor to scale the Gerber element.")
        )
        self.grb_scale_entry = FCDoubleSpinner()
        self.grb_scale_entry.set_precision(self.decimals)
        self.grb_scale_entry.set_range(0, 9999)

        grid0.addWidget(self.grb_scale_label, 16, 0)
        grid0.addWidget(self.grb_scale_entry, 16, 1)

        self.grb_array_tools_ma_label = QtWidgets.QLabel('<b>%s:</b>' % _('Mark Area Tool'))
        grid0.addWidget(self.grb_array_tools_ma_label, 17, 0, 1, 2)

        # Mark area Tool low threshold
        self.grb_ma_low_label = QtWidgets.QLabel('%s:' % _('Threshold low'))
        self.grb_ma_low_label.setToolTip(
            _("Threshold value under which the apertures are not marked.")
        )
        self.grb_ma_low_entry = FCDoubleSpinner()
        self.grb_ma_low_entry.set_precision(self.decimals)
        self.grb_ma_low_entry.set_range(0, 9999)

        grid0.addWidget(self.grb_ma_low_label, 18, 0)
        grid0.addWidget(self.grb_ma_low_entry, 18, 1)

        # Mark area Tool high threshold
        self.grb_ma_high_label = QtWidgets.QLabel('%s:' % _('Threshold high'))
        self.grb_ma_high_label.setToolTip(
            _("Threshold value over which the apertures are not marked.")
        )
        self.grb_ma_high_entry = FCDoubleSpinner()
        self.grb_ma_high_entry.set_precision(self.decimals)
        self.grb_ma_high_entry.set_range(0, 9999)

        grid0.addWidget(self.grb_ma_high_label, 19, 0)
        grid0.addWidget(self.grb_ma_high_entry, 19, 1)

        self.layout.addStretch()
