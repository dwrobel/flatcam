from PyQt6 import QtWidgets

from appGUI.GUIElements import FCSpinner, FCDoubleSpinner, FCComboBox, FCLabel, RadioSet, NumericalEvalTupleEntry, \
    FCGridLayout, FCFrame
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GerberEditorPrefGroupUI(OptionsGroupUI):
    def __init__(self, defaults, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "Gerber Adv. Options Preferences", parent=parent)
        super(GerberEditorPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Editor")))
        self.decimals = decimals
        self.defaults = defaults

        # #############################################################################################################
        # Gerber Editor Parameters Frame
        # #############################################################################################################

        self.param_label = FCLabel('<span style="color:blue;"><b>%s</b></span>' % _('Parameters'))
        self.param_label.setToolTip(
            _("A list of Gerber Editor parameters.")
        )
        self.layout.addWidget(self.param_label)

        par_frame = FCFrame()
        self.layout.addWidget(par_frame)

        param_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        par_frame.setLayout(param_grid)

        # Selection Limit
        self.sel_limit_label = FCLabel('%s:' % _("Selection limit"))
        self.sel_limit_label.setToolTip(
            _("Set the number of selected Gerber geometry\n"
              "items above which the utility geometry\n"
              "becomes just a selection rectangle.\n"
              "Increases the performance when moving a\n"
              "large number of geometric elements.")
        )
        self.sel_limit_entry = FCSpinner()
        self.sel_limit_entry.set_range(0, 10000)

        param_grid.addWidget(self.sel_limit_label, 0, 0)
        param_grid.addWidget(self.sel_limit_entry, 0, 1)

        # New aperture code
        self.addcode_entry_lbl = FCLabel('%s:' % _('New Aperture code'))
        self.addcode_entry_lbl.setToolTip(
            _("Code for the new aperture")
        )

        self.addcode_entry = FCSpinner()
        self.addcode_entry.set_range(10, 99)
        self.addcode_entry.setWrapping(True)

        param_grid.addWidget(self.addcode_entry_lbl, 2, 0)
        param_grid.addWidget(self.addcode_entry, 2, 1)

        # New aperture size
        self.addsize_entry_lbl = FCLabel('%s:' % _('New Aperture size'))
        self.addsize_entry_lbl.setToolTip(
            _("Size for the new aperture")
        )

        self.addsize_entry = FCDoubleSpinner()
        self.addsize_entry.set_range(0, 100)
        self.addsize_entry.set_precision(self.decimals)

        param_grid.addWidget(self.addsize_entry_lbl, 4, 0)
        param_grid.addWidget(self.addsize_entry, 4, 1)

        # New aperture type
        self.addtype_combo_lbl = FCLabel('%s:' % _('New Aperture type'))
        self.addtype_combo_lbl.setToolTip(
            _("Type for the new aperture.\n"
              "Can be 'C', 'R' or 'O'.")
        )

        self.addtype_combo = FCComboBox()
        self.addtype_combo.addItems(['C', 'R', 'O'])

        param_grid.addWidget(self.addtype_combo_lbl, 6, 0)
        param_grid.addWidget(self.addtype_combo, 6, 1)

        # Number of pads in a pad array
        self.grb_array_size_label = FCLabel('%s:' % _('Nr of pads'))
        self.grb_array_size_label.setToolTip(
            _("Specify how many pads to be in the array.")
        )

        self.grb_array_size_entry = FCSpinner()
        self.grb_array_size_entry.set_range(0, 10000)

        param_grid.addWidget(self.grb_array_size_label, 8, 0)
        param_grid.addWidget(self.grb_array_size_entry, 8, 1)

        self.adddim_label = FCLabel('%s:' % _('Aperture Dimensions'))
        self.adddim_label.setToolTip(
            _("Diameters of the tools, separated by comma.\n"
              "The value of the diameter has to use the dot decimals separator.\n"
              "Valid values: 0.3, 1.0")
        )
        self.adddim_entry = NumericalEvalTupleEntry(border_color='#0069A9')

        param_grid.addWidget(self.adddim_label, 10, 0)
        param_grid.addWidget(self.adddim_entry, 10, 1)

        # #############################################################################################################
        # Linear Pad Array Frame
        # #############################################################################################################
        self.grb_array_linear_label = FCLabel('<span style="color:brown;"><b>%s</b></span>' % _('Linear Pad Array'))
        self.layout.addWidget(self.grb_array_linear_label)

        lin_frame = FCFrame()
        self.layout.addWidget(lin_frame)

        # ## Grid Layout
        lin_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        lin_frame.setLayout(lin_grid)

        # Linear Pad Array direction
        self.grb_axis_label = FCLabel('%s:' % _('Linear Direction'))
        self.grb_axis_label.setToolTip(
            _("Direction on which the linear array is oriented:\n"
              "- 'X' - horizontal axis \n"
              "- 'Y' - vertical axis or \n"
              "- 'Angle' - a custom angle for the array inclination")
        )

        self.grb_axis_radio = RadioSet([{'label': _('X'), 'value': 'X'},
                                        {'label': _('Y'), 'value': 'Y'},
                                        {'label': _('Angle'), 'value': 'A'}])

        lin_grid.addWidget(self.grb_axis_label, 0, 0)
        lin_grid.addWidget(self.grb_axis_radio, 0, 1)

        # Linear Pad Array pitch distance
        self.grb_pitch_label = FCLabel('%s:' % _('Pitch'))
        self.grb_pitch_label.setToolTip(
            _("Pitch = Distance between elements of the array.")
        )
        # self.drill_pitch_label.setMinimumWidth(100)
        self.grb_pitch_entry = FCDoubleSpinner()
        self.grb_pitch_entry.set_precision(self.decimals)

        lin_grid.addWidget(self.grb_pitch_label, 2, 0)
        lin_grid.addWidget(self.grb_pitch_entry, 2, 1)

        # Linear Pad Array custom angle
        self.grb_angle_label = FCLabel('%s:' % _('Angle'))
        self.grb_angle_label.setToolTip(
            _("Angle at which each element in circular array is placed.")
        )
        self.grb_angle_entry = FCDoubleSpinner()
        self.grb_angle_entry.set_precision(self.decimals)
        self.grb_angle_entry.set_range(-360, 360)
        self.grb_angle_entry.setSingleStep(5)

        lin_grid.addWidget(self.grb_angle_label, 4, 0)
        lin_grid.addWidget(self.grb_angle_entry, 4, 1)

        # #############################################################################################################
        # Circular Pad Array Frame
        # #############################################################################################################
        self.grb_array_circ_label = FCLabel('<span style="color:green;"><b>%s</b></span>' % _('Circular Pad Array'))
        self.layout.addWidget(self.grb_array_circ_label)

        circ_frame = FCFrame()
        self.layout.addWidget(circ_frame)

        # ## Grid Layout
        circ_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        circ_frame.setLayout(circ_grid)

        # Circular Pad Array direction
        self.grb_circular_direction_label = FCLabel('%s:' % _('Circular Direction'))
        self.grb_circular_direction_label.setToolTip(
            _("Direction for circular array.\n"
              "Can be CW = clockwise or CCW = counter clockwise.")
        )

        self.grb_circular_dir_radio = RadioSet([{'label': _('CW'), 'value': 'CW'},
                                                {'label': _('CCW'), 'value': 'CCW'}])

        circ_grid.addWidget(self.grb_circular_direction_label, 0, 0)
        circ_grid.addWidget(self.grb_circular_dir_radio, 0, 1)

        # Circular Pad Array Angle
        self.grb_circular_angle_label = FCLabel('%s:' % _('Circular Angle'))
        self.grb_circular_angle_label.setToolTip(
            _("Angle at which each element in circular array is placed.")
        )
        self.grb_circular_angle_entry = FCDoubleSpinner()
        self.grb_circular_angle_entry.set_precision(self.decimals)
        self.grb_circular_angle_entry.set_range(-360, 360)

        self.grb_circular_angle_entry.setSingleStep(5)

        circ_grid.addWidget(self.grb_circular_angle_label, 2, 0)
        circ_grid.addWidget(self.grb_circular_angle_entry, 2, 1)

        # #############################################################################################################
        # Buffer Frame
        # #############################################################################################################
        self.grb_array_tools_b_label = FCLabel('<span style="color:darkorange;"><b>%s</b></span>' % _('Buffer Tool'))
        self.layout.addWidget(self.grb_array_tools_b_label)

        buff_frame = FCFrame()
        self.layout.addWidget(buff_frame)

        # ## Grid Layout
        buf_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        buff_frame.setLayout(buf_grid)

        # Buffer Distance
        self.grb_buff_label = FCLabel('%s:' % _('Buffer distance'))
        self.grb_buff_label.setToolTip(
            _("Distance at which to buffer the Gerber element.")
        )
        self.grb_buff_entry = FCDoubleSpinner()
        self.grb_buff_entry.set_precision(self.decimals)
        self.grb_buff_entry.set_range(-10000, 10000)

        buf_grid.addWidget(self.grb_buff_label, 0, 0)
        buf_grid.addWidget(self.grb_buff_entry, 0, 1)

        # #############################################################################################################
        # Scale Frame
        # #############################################################################################################
        self.grb_array_tools_s_label = FCLabel('<span style="color:magenta;"><b>%s</b></span>' % _('Scale Tool'))
        self.layout.addWidget(self.grb_array_tools_s_label)

        scale_frame = FCFrame()
        self.layout.addWidget(scale_frame)

        # ## Grid Layout
        scale_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        scale_frame.setLayout(scale_grid)

        # Scale Factor
        self.grb_scale_label = FCLabel('%s:' % _('Scale factor'))
        self.grb_scale_label.setToolTip(
            _("Factor to scale the Gerber element.")
        )
        self.grb_scale_entry = FCDoubleSpinner()
        self.grb_scale_entry.set_precision(self.decimals)
        self.grb_scale_entry.set_range(0, 10000)

        scale_grid.addWidget(self.grb_scale_label, 0, 0)
        scale_grid.addWidget(self.grb_scale_entry, 0, 1)

        # #############################################################################################################
        # Mark Area Frame
        # #############################################################################################################
        self.grb_array_tools_ma_label = FCLabel('<span style="color:blue;"><b>%s</b></span>' % _('Mark Area Tool'))
        self.layout.addWidget(self.grb_array_tools_ma_label)

        ma_frame = FCFrame()
        self.layout.addWidget(ma_frame)

        # ## Grid Layout
        ma_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        ma_frame.setLayout(ma_grid)

        # Mark area Tool low threshold
        self.grb_ma_low_label = FCLabel('%s:' % _('Threshold low'))
        self.grb_ma_low_label.setToolTip(
            _("Threshold value under which the apertures are not marked.")
        )
        self.grb_ma_low_entry = FCDoubleSpinner()
        self.grb_ma_low_entry.set_precision(self.decimals)
        self.grb_ma_low_entry.set_range(0, 10000)

        ma_grid.addWidget(self.grb_ma_low_label, 0, 0)
        ma_grid.addWidget(self.grb_ma_low_entry, 0, 1)

        # Mark area Tool high threshold
        self.grb_ma_high_label = FCLabel('%s:' % _('Threshold high'))
        self.grb_ma_high_label.setToolTip(
            _("Threshold value over which the apertures are not marked.")
        )
        self.grb_ma_high_entry = FCDoubleSpinner()
        self.grb_ma_high_entry.set_precision(self.decimals)
        self.grb_ma_high_entry.set_range(0, 10000)

        ma_grid.addWidget(self.grb_ma_high_label, 2, 0)
        ma_grid.addWidget(self.grb_ma_high_entry, 2, 1)

        FCGridLayout.set_common_column_size([param_grid, lin_grid, circ_grid, buf_grid, scale_grid, ma_grid], 0)

        self.layout.addStretch()
