from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings

from appGUI.GUIElements import FCSpinner, FCDoubleSpinner, RadioSet
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


class ExcellonEditorPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):
        super(ExcellonEditorPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Excellon Editor")))
        self.decimals = decimals

        # Excellon Editor Parameters
        self.param_label = QtWidgets.QLabel("<b>%s:</b>" % _("Parameters"))
        self.param_label.setToolTip(
            _("A list of Excellon Editor parameters.")
        )
        self.layout.addWidget(self.param_label)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        # Selection Limit
        self.sel_limit_label = QtWidgets.QLabel('%s:' % _("Selection limit"))
        self.sel_limit_label.setToolTip(
            _("Set the number of selected Excellon geometry\n"
              "items above which the utility geometry\n"
              "becomes just a selection rectangle.\n"
              "Increases the performance when moving a\n"
              "large number of geometric elements.")
        )
        self.sel_limit_entry = FCSpinner()
        self.sel_limit_entry.set_range(0, 99999)

        grid0.addWidget(self.sel_limit_label, 0, 0)
        grid0.addWidget(self.sel_limit_entry, 0, 1)

        # New Diameter
        self.addtool_entry_lbl = QtWidgets.QLabel('%s:' % _('New Dia'))
        self.addtool_entry_lbl.setToolTip(
            _("Diameter for the new tool")
        )

        self.addtool_entry = FCDoubleSpinner()
        self.addtool_entry.set_range(0.000001, 99.9999)
        self.addtool_entry.set_precision(self.decimals)

        grid0.addWidget(self.addtool_entry_lbl, 1, 0)
        grid0.addWidget(self.addtool_entry, 1, 1)

        # Number of drill holes in a drill array
        self.drill_array_size_label = QtWidgets.QLabel('%s:' % _('Nr of drills'))
        self.drill_array_size_label.setToolTip(
            _("Specify how many drills to be in the array.")
        )
        # self.drill_array_size_label.setMinimumWidth(100)

        self.drill_array_size_entry = FCSpinner()
        self.drill_array_size_entry.set_range(0, 9999)

        grid0.addWidget(self.drill_array_size_label, 2, 0)
        grid0.addWidget(self.drill_array_size_entry, 2, 1)

        self.drill_array_linear_label = QtWidgets.QLabel('<b>%s:</b>' % _('Linear Drill Array'))
        grid0.addWidget(self.drill_array_linear_label, 3, 0, 1, 2)

        # Linear Drill Array direction
        self.drill_axis_label = QtWidgets.QLabel('%s:' % _('Linear Direction'))
        self.drill_axis_label.setToolTip(
            _("Direction on which the linear array is oriented:\n"
              "- 'X' - horizontal axis \n"
              "- 'Y' - vertical axis or \n"
              "- 'Angle' - a custom angle for the array inclination")
        )
        # self.drill_axis_label.setMinimumWidth(100)
        self.drill_axis_radio = RadioSet([{'label': _('X'), 'value': 'X'},
                                          {'label': _('Y'), 'value': 'Y'},
                                          {'label': _('Angle'), 'value': 'A'}])

        grid0.addWidget(self.drill_axis_label, 4, 0)
        grid0.addWidget(self.drill_axis_radio, 4, 1)

        # Linear Drill Array pitch distance
        self.drill_pitch_label = QtWidgets.QLabel('%s:' % _('Pitch'))
        self.drill_pitch_label.setToolTip(
            _("Pitch = Distance between elements of the array.")
        )
        # self.drill_pitch_label.setMinimumWidth(100)
        self.drill_pitch_entry = FCDoubleSpinner()
        self.drill_pitch_entry.set_range(0, 910000.0000)
        self.drill_pitch_entry.set_precision(self.decimals)

        grid0.addWidget(self.drill_pitch_label, 5, 0)
        grid0.addWidget(self.drill_pitch_entry, 5, 1)

        # Linear Drill Array custom angle
        self.drill_angle_label = QtWidgets.QLabel('%s:' % _('Angle'))
        self.drill_angle_label.setToolTip(
            _("Angle at which each element in circular array is placed.")
        )
        self.drill_angle_entry = FCDoubleSpinner()
        self.drill_pitch_entry.set_range(-360, 360)
        self.drill_pitch_entry.set_precision(self.decimals)
        self.drill_angle_entry.setWrapping(True)
        self.drill_angle_entry.setSingleStep(5)

        grid0.addWidget(self.drill_angle_label, 6, 0)
        grid0.addWidget(self.drill_angle_entry, 6, 1)

        self.drill_array_circ_label = QtWidgets.QLabel('<b>%s:</b>' % _('Circular Drill Array'))
        grid0.addWidget(self.drill_array_circ_label, 7, 0, 1, 2)

        # Circular Drill Array direction
        self.drill_circular_direction_label = QtWidgets.QLabel('%s:' % _('Circular Direction'))
        self.drill_circular_direction_label.setToolTip(
            _("Direction for circular array.\n"
              "Can be CW = clockwise or CCW = counter clockwise.")
        )

        self.drill_circular_dir_radio = RadioSet([{'label': _('CW'), 'value': 'CW'},
                                                  {'label': _('CCW'), 'value': 'CCW'}])

        grid0.addWidget(self.drill_circular_direction_label, 8, 0)
        grid0.addWidget(self.drill_circular_dir_radio, 8, 1)

        # Circular Drill Array Angle
        self.drill_circular_angle_label = QtWidgets.QLabel('%s:' % _('Circular Angle'))
        self.drill_circular_angle_label.setToolTip(
            _("Angle at which each element in circular array is placed.")
        )
        self.drill_circular_angle_entry = FCDoubleSpinner()
        self.drill_circular_angle_entry.set_range(-360, 360)
        self.drill_circular_angle_entry.set_precision(self.decimals)
        self.drill_circular_angle_entry.setWrapping(True)
        self.drill_circular_angle_entry.setSingleStep(5)

        grid0.addWidget(self.drill_circular_angle_label, 9, 0)
        grid0.addWidget(self.drill_circular_angle_entry, 9, 1)

        # ##### SLOTS #####
        # #################
        self.drill_array_circ_label = QtWidgets.QLabel('<b>%s:</b>' % _('Slots'))
        grid0.addWidget(self.drill_array_circ_label, 10, 0, 1, 2)

        # Slot length
        self.slot_length_label = QtWidgets.QLabel('%s:' % _('Length'))
        self.slot_length_label.setToolTip(
            _("Length. The length of the slot.")
        )
        self.slot_length_label.setMinimumWidth(100)

        self.slot_length_entry = FCDoubleSpinner()
        self.slot_length_entry.set_range(0, 99999)
        self.slot_length_entry.set_precision(self.decimals)
        self.slot_length_entry.setWrapping(True)
        self.slot_length_entry.setSingleStep(1)

        grid0.addWidget(self.slot_length_label, 11, 0)
        grid0.addWidget(self.slot_length_entry, 11, 1)

        # Slot direction
        self.slot_axis_label = QtWidgets.QLabel('%s:' % _('Direction'))
        self.slot_axis_label.setToolTip(
            _("Direction on which the slot is oriented:\n"
              "- 'X' - horizontal axis \n"
              "- 'Y' - vertical axis or \n"
              "- 'Angle' - a custom angle for the slot inclination")
        )
        self.slot_axis_label.setMinimumWidth(100)

        self.slot_axis_radio = RadioSet([{'label': _('X'), 'value': 'X'},
                                         {'label': _('Y'), 'value': 'Y'},
                                         {'label': _('Angle'), 'value': 'A'}])
        grid0.addWidget(self.slot_axis_label, 12, 0)
        grid0.addWidget(self.slot_axis_radio, 12, 1)

        # Slot custom angle
        self.slot_angle_label = QtWidgets.QLabel('%s:' % _('Angle'))
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

        grid0.addWidget(self.slot_angle_label, 13, 0)
        grid0.addWidget(self.slot_angle_spinner, 13, 1)

        # #### SLOTS ARRAY #######
        # ########################

        self.slot_array_linear_label = QtWidgets.QLabel('<b>%s:</b>' % _('Linear Slot Array'))
        grid0.addWidget(self.slot_array_linear_label, 14, 0, 1, 2)

        # Number of slot holes in a drill array
        self.slot_array_size_label = QtWidgets.QLabel('%s:' % _('Nr of slots'))
        self.drill_array_size_label.setToolTip(
            _("Specify how many slots to be in the array.")
        )
        # self.slot_array_size_label.setMinimumWidth(100)

        self.slot_array_size_entry = FCSpinner()
        self.slot_array_size_entry.set_range(0, 999999)

        grid0.addWidget(self.slot_array_size_label, 15, 0)
        grid0.addWidget(self.slot_array_size_entry, 15, 1)

        # Linear Slot Array direction
        self.slot_array_axis_label = QtWidgets.QLabel('%s:' % _('Linear Direction'))
        self.slot_array_axis_label.setToolTip(
            _("Direction on which the linear array is oriented:\n"
              "- 'X' - horizontal axis \n"
              "- 'Y' - vertical axis or \n"
              "- 'Angle' - a custom angle for the array inclination")
        )
        # self.slot_axis_label.setMinimumWidth(100)
        self.slot_array_axis_radio = RadioSet([{'label': _('X'), 'value': 'X'},
                                               {'label': _('Y'), 'value': 'Y'},
                                               {'label': _('Angle'), 'value': 'A'}])

        grid0.addWidget(self.slot_array_axis_label, 16, 0)
        grid0.addWidget(self.slot_array_axis_radio, 16, 1)

        # Linear Slot Array pitch distance
        self.slot_array_pitch_label = QtWidgets.QLabel('%s:' % _('Pitch'))
        self.slot_array_pitch_label.setToolTip(
            _("Pitch = Distance between elements of the array.")
        )
        # self.drill_pitch_label.setMinimumWidth(100)
        self.slot_array_pitch_entry = FCDoubleSpinner()
        self.slot_array_pitch_entry.set_precision(self.decimals)
        self.slot_array_pitch_entry.setWrapping(True)
        self.slot_array_pitch_entry.setRange(0, 999999)
        self.slot_array_pitch_entry.setSingleStep(1)

        grid0.addWidget(self.slot_array_pitch_label, 17, 0)
        grid0.addWidget(self.slot_array_pitch_entry, 17, 1)

        # Linear Slot Array custom angle
        self.slot_array_angle_label = QtWidgets.QLabel('%s:' % _('Angle'))
        self.slot_array_angle_label.setToolTip(
            _("Angle at which each element in circular array is placed.")
        )
        self.slot_array_angle_entry = FCDoubleSpinner()
        self.slot_array_angle_entry.set_precision(self.decimals)
        self.slot_array_angle_entry.setWrapping(True)
        self.slot_array_angle_entry.setRange(-360, 360)
        self.slot_array_angle_entry.setSingleStep(5)

        grid0.addWidget(self.slot_array_angle_label, 18, 0)
        grid0.addWidget(self.slot_array_angle_entry, 18, 1)

        self.slot_array_circ_label = QtWidgets.QLabel('<b>%s:</b>' % _('Circular Slot Array'))
        grid0.addWidget(self.slot_array_circ_label, 19, 0, 1, 2)

        # Circular Slot Array direction
        self.slot_array_circular_direction_label = QtWidgets.QLabel('%s:' % _('Circular Direction'))
        self.slot_array_circular_direction_label.setToolTip(
            _("Direction for circular array.\n"
              "Can be CW = clockwise or CCW = counter clockwise.")
        )

        self.slot_array_circular_dir_radio = RadioSet([{'label': _('CW'), 'value': 'CW'},
                                                       {'label': _('CCW'), 'value': 'CCW'}])

        grid0.addWidget(self.slot_array_circular_direction_label, 20, 0)
        grid0.addWidget(self.slot_array_circular_dir_radio, 20, 1)

        # Circular Slot Array Angle
        self.slot_array_circular_angle_label = QtWidgets.QLabel('%s:' % _('Circular Angle'))
        self.slot_array_circular_angle_label.setToolTip(
            _("Angle at which each element in circular array is placed.")
        )
        self.slot_array_circular_angle_entry = FCDoubleSpinner()
        self.slot_array_circular_angle_entry.set_precision(self.decimals)
        self.slot_array_circular_angle_entry.setWrapping(True)
        self.slot_array_circular_angle_entry.setRange(-360, 360)
        self.slot_array_circular_angle_entry.setSingleStep(5)

        grid0.addWidget(self.slot_array_circular_angle_label, 21, 0)
        grid0.addWidget(self.slot_array_circular_angle_entry, 21, 1)

        self.layout.addStretch()
