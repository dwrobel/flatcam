
from appGUI.GUIElements import FCSpinner, FCDoubleSpinner, RadioSet, FCLabel, GLay, FCFrame
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ExcellonEditorPrefGroupUI(OptionsGroupUI):
    def __init__(self, app, parent=None):
        super(ExcellonEditorPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Editor")))
        self.decimals = app.decimals
        self.options = app.options

        # #############################################################################################################
        # PARAMETERS Frame
        # #############################################################################################################
        self.param_label = FCLabel('%s' % _("Parameters"), color='blue', bold=True)
        self.param_label.setToolTip(
            _("A list of Excellon Editor parameters.")
        )
        self.layout.addWidget(self.param_label)

        param_frame = FCFrame()
        self.layout.addWidget(param_frame)

        param_grid = GLay(v_spacing=5, h_spacing=3)
        param_frame.setLayout(param_grid)

        # Selection Limit
        self.sel_limit_label = FCLabel('%s:' % _("Selection limit"))
        self.sel_limit_label.setToolTip(
            _("Set the number of selected Excellon geometry\n"
              "items above which the utility geometry\n"
              "becomes just a selection rectangle.\n"
              "Increases the performance when moving a\n"
              "large number of geometric elements.")
        )
        self.sel_limit_entry = FCSpinner()
        self.sel_limit_entry.set_range(0, 99999)

        param_grid.addWidget(self.sel_limit_label, 0, 0)
        param_grid.addWidget(self.sel_limit_entry, 0, 1)

        # New Diameter
        self.addtool_entry_lbl = FCLabel('%s:' % _('New Dia'))
        self.addtool_entry_lbl.setToolTip(
            _("Diameter for the new tool")
        )

        self.addtool_entry = FCDoubleSpinner()
        self.addtool_entry.set_range(0.000001, 99.9999)
        self.addtool_entry.set_precision(self.decimals)

        param_grid.addWidget(self.addtool_entry_lbl, 2, 0)
        param_grid.addWidget(self.addtool_entry, 2, 1)

        # Number of drill holes in a drill array
        self.drill_array_size_label = FCLabel('%s:' % _('Nr of drills'))
        self.drill_array_size_label.setToolTip(
            _("Specify how many drills to be in the array.")
        )
        # self.drill_array_size_label.setMinimumWidth(100)

        self.drill_array_size_entry = FCSpinner()
        self.drill_array_size_entry.set_range(0, 9999)

        param_grid.addWidget(self.drill_array_size_label, 4, 0)
        param_grid.addWidget(self.drill_array_size_entry, 4, 1)

        # #############################################################################################################
        # Linear Array Frame
        # #############################################################################################################
        self.drill_array_linear_label = FCLabel('%s' % _("Linear Drill Array"), color='brown', bold=True)
        self.layout.addWidget(self.drill_array_linear_label)

        lin_frame = FCFrame()
        self.layout.addWidget(lin_frame)

        lin_grid = GLay(v_spacing=5, h_spacing=3)
        lin_frame.setLayout(lin_grid)

        # Linear Drill Array direction
        self.drill_axis_label = FCLabel('%s:' % _('Linear Direction'))
        self.drill_axis_label.setToolTip(
            _("Direction on which the linear array is oriented:\n"
              "- 'X' - horizontal axis \n"
              "- 'Y' - vertical axis or \n"
              "- 'Angle' - a custom angle for the array inclination")
        )
        # self.drill_axis_label.setMinimumWidth(100)
        self.drill_axis_radio = RadioSet([{'label': _('X'), 'value': 'X'},
                                          {'label': _('Y'), 'value': 'Y'},
                                          {'label': _('Angle'), 'value': 'A'}], compact=True)

        lin_grid.addWidget(self.drill_axis_label, 0, 0)
        lin_grid.addWidget(self.drill_axis_radio, 0, 1)

        # Linear Drill Array pitch distance
        self.drill_pitch_label = FCLabel('%s:' % _('Pitch'))
        self.drill_pitch_label.setToolTip(
            _("Pitch = Distance between elements of the array.")
        )
        # self.drill_pitch_label.setMinimumWidth(100)
        self.drill_pitch_entry = FCDoubleSpinner()
        self.drill_pitch_entry.set_range(0, 910000.0000)
        self.drill_pitch_entry.set_precision(self.decimals)

        lin_grid.addWidget(self.drill_pitch_label, 2, 0)
        lin_grid.addWidget(self.drill_pitch_entry, 2, 1)

        # Linear Drill Array custom angle
        self.drill_angle_label = FCLabel('%s:' % _('Angle'))
        self.drill_angle_label.setToolTip(
            _("Angle at which each element in circular array is placed.")
        )
        self.drill_angle_entry = FCDoubleSpinner()
        self.drill_pitch_entry.set_range(-360, 360)
        self.drill_pitch_entry.set_precision(self.decimals)
        self.drill_angle_entry.setWrapping(True)
        self.drill_angle_entry.setSingleStep(5)

        lin_grid.addWidget(self.drill_angle_label, 4, 0)
        lin_grid.addWidget(self.drill_angle_entry, 4, 1)

        # #############################################################################################################
        # Circular Array Frame
        # #############################################################################################################
        self.drill_array_circ_label = FCLabel('%s' % _("Circular Drill Array"), color='green', bold=True)
        self.layout.addWidget(self.drill_array_circ_label)

        circ_frame = FCFrame()
        self.layout.addWidget(circ_frame)

        circ_grid = GLay(v_spacing=5, h_spacing=3)
        circ_frame.setLayout(circ_grid)

        # Circular Drill Array direction
        self.drill_circular_direction_label = FCLabel('%s:' % _('Circular Direction'))
        self.drill_circular_direction_label.setToolTip(
            _("Direction for circular array.\n"
              "Can be CW = clockwise or CCW = counter clockwise.")
        )

        self.drill_circular_dir_radio = RadioSet([{'label': _('CW'), 'value': 'CW'},
                                                  {'label': _('CCW'), 'value': 'CCW'}], compact=True)

        circ_grid.addWidget(self.drill_circular_direction_label, 0, 0)
        circ_grid.addWidget(self.drill_circular_dir_radio, 0, 1)

        # Circular Drill Array Angle
        self.drill_circular_angle_label = FCLabel('%s:' % _('Circular Angle'))
        self.drill_circular_angle_label.setToolTip(
            _("Angle at which each element in circular array is placed.")
        )
        self.drill_circular_angle_entry = FCDoubleSpinner()
        self.drill_circular_angle_entry.set_range(-360, 360)
        self.drill_circular_angle_entry.set_precision(self.decimals)
        self.drill_circular_angle_entry.setWrapping(True)
        self.drill_circular_angle_entry.setSingleStep(5)

        circ_grid.addWidget(self.drill_circular_angle_label, 2, 0)
        circ_grid.addWidget(self.drill_circular_angle_entry, 2, 1)

        # #############################################################################################################
        # Slots Frame
        # #############################################################################################################
        self.drill_array_circ_label = FCLabel('%s' % _("Slots"), color='darkorange', bold=True)
        self.layout.addWidget(self.drill_array_circ_label)

        slots_frame = FCFrame()
        self.layout.addWidget(slots_frame)

        slots_grid = GLay(v_spacing=5, h_spacing=3)
        slots_frame.setLayout(slots_grid)

        # Slot length
        self.slot_length_label = FCLabel('%s:' % _('Length'))
        self.slot_length_label.setToolTip(
            _("Length. The length of the slot.")
        )
        self.slot_length_label.setMinimumWidth(100)

        self.slot_length_entry = FCDoubleSpinner()
        self.slot_length_entry.set_range(0, 99999)
        self.slot_length_entry.set_precision(self.decimals)
        self.slot_length_entry.setWrapping(True)
        self.slot_length_entry.setSingleStep(1)

        slots_grid.addWidget(self.slot_length_label, 0, 0)
        slots_grid.addWidget(self.slot_length_entry, 0, 1)

        # Slot direction
        self.slot_axis_label = FCLabel('%s:' % _('Direction'))
        self.slot_axis_label.setToolTip(
            _("Direction on which the slot is oriented:\n"
              "- 'X' - horizontal axis \n"
              "- 'Y' - vertical axis or \n"
              "- 'Angle' - a custom angle for the slot inclination")
        )
        self.slot_axis_label.setMinimumWidth(100)

        self.slot_direction_radio = RadioSet([{'label': _('X'), 'value': 'X'},
                                              {'label': _('Y'), 'value': 'Y'},
                                              {'label': _('Angle'), 'value': 'A'}], compact=True)
        slots_grid.addWidget(self.slot_axis_label, 2, 0)
        slots_grid.addWidget(self.slot_direction_radio, 2, 1)

        # Slot custom angle
        self.slot_angle_label = FCLabel('%s:' % _('Angle'))
        self.slot_angle_label.setToolTip(
            _("Angle at which the slot is placed.\n"
              "The precision is of max 2 decimals.\n"
              "Min value is: -360.00 degrees.\n"
              "Max value is: 360.00 degrees.")
        )
        self.slot_angle_label.setMinimumWidth(100)

        self.slot_angle_spinner = FCDoubleSpinner()
        self.slot_angle_spinner.set_precision(self.decimals)
        self.slot_angle_spinner.setWrapping(True)
        self.slot_angle_spinner.setRange(-359.99, 360.00)
        self.slot_angle_spinner.setSingleStep(5)

        slots_grid.addWidget(self.slot_angle_label, 4, 0)
        slots_grid.addWidget(self.slot_angle_spinner, 4, 1)

        # #############################################################################################################
        # Slots Array Frame
        # #############################################################################################################
        self.slot_array_linear_label = FCLabel('%s' % _("Linear Slot Array"), color='magenta', bold=True)
        self.layout.addWidget(self.slot_array_linear_label)

        slot_array_frame = FCFrame()
        self.layout.addWidget(slot_array_frame)

        slot_array_grid = GLay(v_spacing=5, h_spacing=3)
        slot_array_frame.setLayout(slot_array_grid)

        # Number of slot holes in a drill array
        self.slot_array_size_label = FCLabel('%s:' % _('Nr of slots'))
        self.drill_array_size_label.setToolTip(
            _("Specify how many slots to be in the array.")
        )
        # self.array_size_label.setMinimumWidth(100)

        self.slot_array_size_entry = FCSpinner()
        self.slot_array_size_entry.set_range(0, 999999)

        slot_array_grid.addWidget(self.slot_array_size_label, 0, 0)
        slot_array_grid.addWidget(self.slot_array_size_entry, 0, 1)

        # Linear Slot Array direction
        self.slot_array_axis_label = FCLabel('%s:' % _('Linear Direction'))
        self.slot_array_axis_label.setToolTip(
            _("Direction on which the linear array is oriented:\n"
              "- 'X' - horizontal axis \n"
              "- 'Y' - vertical axis or \n"
              "- 'Angle' - a custom angle for the array inclination")
        )
        # self.slot_axis_label.setMinimumWidth(100)
        self.slot_array_axis_radio = RadioSet([{'label': _('X'), 'value': 'X'},
                                               {'label': _('Y'), 'value': 'Y'},
                                               {'label': _('Angle'), 'value': 'A'}], compact=True)

        slot_array_grid.addWidget(self.slot_array_axis_label, 2, 0)
        slot_array_grid.addWidget(self.slot_array_axis_radio, 2, 1)

        # Linear Slot Array pitch distance
        self.slot_array_pitch_label = FCLabel('%s:' % _('Pitch'))
        self.slot_array_pitch_label.setToolTip(
            _("Pitch = Distance between elements of the array.")
        )
        # self.drill_pitch_label.setMinimumWidth(100)
        self.slot_array_pitch_entry = FCDoubleSpinner()
        self.slot_array_pitch_entry.set_precision(self.decimals)
        self.slot_array_pitch_entry.setWrapping(True)
        self.slot_array_pitch_entry.setRange(0, 999999)
        self.slot_array_pitch_entry.setSingleStep(1)

        slot_array_grid.addWidget(self.slot_array_pitch_label, 4, 0)
        slot_array_grid.addWidget(self.slot_array_pitch_entry, 4, 1)

        # Linear Slot Array custom angle
        self.slot_array_angle_label = FCLabel('%s:' % _('Angle'))
        self.slot_array_angle_label.setToolTip(
            _("Angle at which each element in circular array is placed.")
        )
        self.slot_array_angle_entry = FCDoubleSpinner()
        self.slot_array_angle_entry.set_precision(self.decimals)
        self.slot_array_angle_entry.setWrapping(True)
        self.slot_array_angle_entry.setRange(-360, 360)
        self.slot_array_angle_entry.setSingleStep(5)

        slot_array_grid.addWidget(self.slot_array_angle_label, 6, 0)
        slot_array_grid.addWidget(self.slot_array_angle_entry, 6, 1)

        # #############################################################################################################
        # Circular Slot Array Frame
        # #############################################################################################################
        self.slot_array_circ_label = FCLabel('%s' % _("Circular Slot Array"), color='blue', bold=True)
        self.layout.addWidget(self.slot_array_circ_label)

        circ_slot_frame = FCFrame()
        self.layout.addWidget(circ_slot_frame)

        circ_slot_grid = GLay(v_spacing=5, h_spacing=3)
        circ_slot_frame.setLayout(circ_slot_grid)

        # Circular Slot Array direction
        self.slot_array_circular_direction_label = FCLabel('%s:' % _('Circular Direction'))
        self.slot_array_circular_direction_label.setToolTip(
            _("Direction for circular array.\n"
              "Can be CW = clockwise or CCW = counter clockwise.")
        )

        self.slot_array_circular_dir_radio = RadioSet([{'label': _('CW'), 'value': 'CW'},
                                                       {'label': _('CCW'), 'value': 'CCW'}], compact=True)

        circ_slot_grid.addWidget(self.slot_array_circular_direction_label, 0, 0)
        circ_slot_grid.addWidget(self.slot_array_circular_dir_radio, 0, 1)

        # Circular Slot Array Angle
        self.slot_array_circular_angle_label = FCLabel('%s:' % _('Circular Angle'))
        self.slot_array_circular_angle_label.setToolTip(
            _("Angle at which each element in circular array is placed.")
        )
        self.slot_array_circular_angle_entry = FCDoubleSpinner()
        self.slot_array_circular_angle_entry.set_precision(self.decimals)
        self.slot_array_circular_angle_entry.setWrapping(True)
        self.slot_array_circular_angle_entry.setRange(-360, 360)
        self.slot_array_circular_angle_entry.setSingleStep(5)

        circ_slot_grid.addWidget(self.slot_array_circular_angle_label, 2, 0)
        circ_slot_grid.addWidget(self.slot_array_circular_angle_entry, 2, 1)

        GLay.set_common_column_size(
            [param_grid, lin_grid, circ_grid, slots_grid, slot_array_grid, circ_slot_grid], 0)

        self.layout.addStretch()
