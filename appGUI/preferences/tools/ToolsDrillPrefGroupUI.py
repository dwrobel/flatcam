from PyQt6 import QtWidgets, QtCore
from PyQt6.QtCore import Qt

from appGUI.GUIElements import RadioSet, FCDoubleSpinner, FCComboBox, FCCheckBox, FCSpinner, NumericalEvalTupleEntry, \
    OptionalInputSection, NumericalEvalEntry, FCLabel, FCGridLayout, FCComboBox2, FCFrame
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ToolsDrillPrefGroupUI(OptionsGroupUI):
    def __init__(self, defaults, decimals=4, parent=None):
        super(ToolsDrillPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Drilling Plugin")))
        self.decimals = decimals
        self.defaults = defaults

        # #############################################################################################################
        # PARAMETERS Frame
        # #############################################################################################################
        self.drill_label = FCLabel('<span style="color:blue;"><b>%s</b></span>' % _("Parameters"))
        self.drill_label.setToolTip(
            _("Create CNCJob with toolpaths for drilling or milling holes.")
        )
        self.layout.addWidget(self.drill_label)

        param_frame = FCFrame()
        self.layout.addWidget(param_frame)

        param_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        param_frame.setLayout(param_grid)

        # Tool order Radio Button
        self.order_label = FCLabel('%s:' % _('Tool order'))
        self.order_label.setToolTip(_("This set the way that the tools in the tools table are used.\n"
                                      "'Default' --> the order from the file\n"
                                      "'Forward' --> tools will be ordered from small to big\n"
                                      "'Reverse' --> tools will ordered from big to small."))

        self.order_combo = FCComboBox2()
        self.order_combo.addItems([_('Default'), _('Forward'), _('Reverse')])

        param_grid.addWidget(self.order_label, 0, 0)
        param_grid.addWidget(self.order_combo, 0, 1, 1, 2)

        # Cut Z
        cutzlabel = FCLabel('%s:' % _('Cut Z'))
        cutzlabel.setToolTip(
            _("Drill depth (negative)\n"
              "below the copper surface.")
        )

        self.cutz_entry = FCDoubleSpinner()
        self.cutz_entry.set_range(-10000.0000, 10000.0000)

        self.cutz_entry.setSingleStep(0.1)
        self.cutz_entry.set_precision(self.decimals)

        param_grid.addWidget(cutzlabel, 2, 0)
        param_grid.addWidget(self.cutz_entry, 2, 1, 1, 2)

        # Multi-Depth
        self.mpass_cb = FCCheckBox('%s:' % _("Multi-Depth"))
        self.mpass_cb.setToolTip(
            _(
                "Use multiple passes to limit\n"
                "the cut depth in each pass. Will\n"
                "cut multiple times until Cut Z is\n"
                "reached."
            )
        )

        self.maxdepth_entry = FCDoubleSpinner()
        self.maxdepth_entry.set_precision(self.decimals)
        self.maxdepth_entry.set_range(0, 10000.0000)
        self.maxdepth_entry.setSingleStep(0.1)

        self.maxdepth_entry.setToolTip(_("Depth of each pass (positive)."))

        param_grid.addWidget(self.mpass_cb, 4, 0)
        param_grid.addWidget(self.maxdepth_entry, 4, 1, 1, 2)

        self.ois_md = OptionalInputSection(self.mpass_cb, [self.maxdepth_entry])

        # Travel Z
        travelzlabel = FCLabel('%s:' % _('Travel Z'))
        travelzlabel.setToolTip(
            _("Tool height when travelling\n"
              "across the XY plane.")
        )

        self.travelz_entry = FCDoubleSpinner()
        self.travelz_entry.set_precision(self.decimals)
        self.travelz_entry.set_range(-10000.0000, 10000.0000)

        param_grid.addWidget(travelzlabel, 6, 0)
        param_grid.addWidget(self.travelz_entry, 6, 1, 1, 2)

        # Tool change:
        self.toolchange_cb = FCCheckBox('%s' % _("Tool change"))
        self.toolchange_cb.setToolTip(
            _("Include tool-change sequence\n"
              "in G-Code (Pause for tool change).")
        )
        param_grid.addWidget(self.toolchange_cb, 8, 0, 1, 3)

        # Tool Change Z
        toolchangezlabel = FCLabel('%s:' % _('Toolchange Z'))
        toolchangezlabel.setToolTip(
            _("Z-axis position (height) for\n"
              "tool change.")
        )

        self.toolchangez_entry = FCDoubleSpinner()
        self.toolchangez_entry.set_precision(self.decimals)
        self.toolchangez_entry.set_range(-10000.0000, 10000.0000)

        param_grid.addWidget(toolchangezlabel, 10, 0)
        param_grid.addWidget(self.toolchangez_entry, 10, 1, 1, 2)

        # End Move Z
        endz_label = FCLabel('%s:' % _('End move Z'))
        endz_label.setToolTip(
            _("Height of the tool after\n"
              "the last move at the end of the job.")
        )
        self.endz_entry = FCDoubleSpinner()
        self.endz_entry.set_precision(self.decimals)
        self.endz_entry.set_range(-10000.0000, 10000.0000)

        param_grid.addWidget(endz_label, 12, 0)
        param_grid.addWidget(self.endz_entry, 12, 1, 1, 2)

        # End Move X,Y
        endmove_xy_label = FCLabel('%s:' % _('End move X,Y'))
        endmove_xy_label.setToolTip(
            _("End move X,Y position. In format (x,y).\n"
              "If no value is entered then there is no move\n"
              "on X,Y plane at the end of the job.")
        )
        self.endxy_entry = NumericalEvalTupleEntry(border_color='#0069A9')

        param_grid.addWidget(endmove_xy_label, 14, 0)
        param_grid.addWidget(self.endxy_entry, 14, 1, 1, 2)

        # Feedrate Z
        frlabel = FCLabel('%s:' % _('Feedrate Z'))
        frlabel.setToolTip(
            _("Tool speed while drilling\n"
              "(in units per minute).\n"
              "So called 'Plunge' feedrate.\n"
              "This is for linear move G01.")
        )
        self.feedrate_z_entry = FCDoubleSpinner()
        self.feedrate_z_entry.set_precision(self.decimals)
        self.feedrate_z_entry.set_range(0, 910000.0000)

        param_grid.addWidget(frlabel, 16, 0)
        param_grid.addWidget(self.feedrate_z_entry, 16, 1, 1, 2)

        # Spindle speed
        spdlabel = FCLabel('%s:' % _('Spindle Speed'))
        spdlabel.setToolTip(
            _("Speed of the spindle\n"
              "in RPM (optional)")
        )

        self.spindlespeed_entry = FCSpinner()
        self.spindlespeed_entry.set_range(0, 1000000)
        self.spindlespeed_entry.set_step(100)

        param_grid.addWidget(spdlabel, 18, 0)
        param_grid.addWidget(self.spindlespeed_entry, 18, 1, 1, 2)

        # Dwell
        self.dwell_cb = FCCheckBox('%s' % _('Enable Dwell'))
        self.dwell_cb.setToolTip(
            _("Pause to allow the spindle to reach its\n"
              "speed before cutting.")
        )

        param_grid.addWidget(self.dwell_cb, 20, 0)

        # Dwell Time
        self.dwelltime_entry = FCDoubleSpinner()
        self.dwelltime_entry.setToolTip(_("Number of time units for spindle to dwell."))
        self.dwelltime_entry.set_precision(self.decimals)
        self.dwelltime_entry.set_range(0, 910000.0000)

        param_grid.addWidget(self.dwelltime_entry, 20, 1, 1, 2)

        self.ois_dwell_exc = OptionalInputSection(self.dwell_cb, [self.dwelltime_entry])

        # preprocessor selection
        pp_excellon_label = FCLabel('%s:' % _("Preprocessor"))
        pp_excellon_label.setToolTip(
            _("The preprocessor JSON file that dictates\n"
              "Gcode output.")
        )

        self.pp_excellon_name_cb = FCComboBox()
        self.pp_excellon_name_cb.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.pp_excellon_name_cb.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                               QtWidgets.QSizePolicy.Policy.Preferred)
        self.pp_excellon_name_cb.addItems(self.defaults["tools_drill_preprocessor_list"])

        for it in range(self.pp_excellon_name_cb.count()):
            self.pp_excellon_name_cb.setItemData(it, self.pp_excellon_name_cb.itemText(it),
                                                 QtCore.Qt.ItemDataRole.ToolTipRole)

        param_grid.addWidget(pp_excellon_label, 24, 0)
        param_grid.addWidget(self.pp_excellon_name_cb, 24, 1, 1, 2)

        # separator_line = QtWidgets.QFrame()
        # separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        # separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        # param_grid.addWidget(separator_line, 29, 0, 1, 3)

        # #############################################################################################################
        # Drill Slots Frame
        # #############################################################################################################
        self.dslots_label = FCLabel('<span style="color:brown;"><b>%s</b></span>' % _('Drilling Slots'))
        self.layout.addWidget(self.dslots_label)

        ds_frame = FCFrame()
        self.layout.addWidget(ds_frame)

        ds_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        ds_frame.setLayout(ds_grid)

        # Drill slots
        self.drill_slots_cb = FCCheckBox('%s' % _('Drill slots'))
        self.drill_slots_cb.setToolTip(
            _("If the selected tool has slots then they will be drilled.")
        )
        ds_grid.addWidget(self.drill_slots_cb, 0, 0)

        # Last drill in slot
        self.last_drill_cb = FCCheckBox('%s' % _('Last drill'))
        self.last_drill_cb.setToolTip(
            _("If the slot length is not completely covered by drill holes,\n"
              "add a drill hole on the slot end point.")
        )
        ds_grid.addWidget(self.last_drill_cb, 0, 1, 1, 2)

        # Drill Overlap
        self.drill_overlap_label = FCLabel('%s:' % _('Overlap'))
        self.drill_overlap_label.setToolTip(
            _("How much (percentage) of the tool diameter to overlap previous drill hole.")
        )

        self.drill_overlap_entry = FCDoubleSpinner()
        self.drill_overlap_entry.set_precision(self.decimals)
        self.drill_overlap_entry.set_range(0.0, 10000.0000)
        self.drill_overlap_entry.setSingleStep(0.1)

        ds_grid.addWidget(self.drill_overlap_label, 2, 0)
        ds_grid.addWidget(self.drill_overlap_entry, 2, 1, 1, 2)

        # separator_line = QtWidgets.QFrame()
        # separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        # separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        # ds_grid.addWidget(separator_line, 6, 0, 1, 3)

        # #############################################################################################################
        # Advanced Options Frame
        # #############################################################################################################
        self.exc_label = FCLabel('<span style="color:teal;"><b>%s</b></span>' % _('Advanced Options'))
        self.exc_label.setToolTip(
            _("A list of advanced parameters.")
        )
        self.layout.addWidget(self.exc_label)

        adv_frame = FCFrame()
        self.layout.addWidget(adv_frame)

        adv_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        adv_frame.setLayout(adv_grid)

        # Offset Z
        offsetlabel = FCLabel('%s:' % _('Offset Z'))
        offsetlabel.setToolTip(
            _("Some drill bits (the larger ones) need to drill deeper\n"
              "to create the desired exit hole diameter due of the tip shape.\n"
              "The value here can compensate the Cut Z parameter."))
        self.offset_entry = FCDoubleSpinner()
        self.offset_entry.set_precision(self.decimals)
        self.offset_entry.set_range(-999.9999, 999.9999)

        adv_grid.addWidget(offsetlabel, 0, 0)
        adv_grid.addWidget(self.offset_entry, 0, 1, 1, 2)

        # ToolChange X,Y
        toolchange_xy_label = FCLabel('%s:' % _('Toolchange X,Y'))
        toolchange_xy_label.setToolTip(
            _("Toolchange X,Y position.")
        )
        self.toolchangexy_entry = NumericalEvalTupleEntry(border_color='#0069A9')

        adv_grid.addWidget(toolchange_xy_label, 2, 0)
        adv_grid.addWidget(self.toolchangexy_entry, 2, 1, 1, 2)

        # Start Z
        startzlabel = FCLabel('%s:' % _('Start Z'))
        startzlabel.setToolTip(
            _("Height of the tool just after starting the work.\n"
              "Delete the value if you don't need this feature.")
        )
        self.estartz_entry = NumericalEvalEntry(border_color='#0069A9')

        adv_grid.addWidget(startzlabel, 4, 0)
        adv_grid.addWidget(self.estartz_entry, 4, 1, 1, 2)

        # Feedrate Rapids
        fr_rapid_label = FCLabel('%s:' % _('Feedrate Rapids'))
        fr_rapid_label.setToolTip(
            _("Tool speed while drilling\n"
              "(in units per minute).\n"
              "This is for the rapid move G00.\n"
              "It is useful only for Marlin,\n"
              "ignore for any other cases.")
        )
        self.feedrate_rapid_entry = FCDoubleSpinner()
        self.feedrate_rapid_entry.set_precision(self.decimals)
        self.feedrate_rapid_entry.set_range(0, 910000.0000)

        adv_grid.addWidget(fr_rapid_label, 6, 0)
        adv_grid.addWidget(self.feedrate_rapid_entry, 6, 1, 1, 2)

        # Probe depth
        self.pdepth_label = FCLabel('%s:' % _("Probe Z depth"))
        self.pdepth_label.setToolTip(
            _("The maximum depth that the probe is allowed\n"
              "to probe. Negative value, in current units.")
        )
        self.pdepth_entry = FCDoubleSpinner()
        self.pdepth_entry.set_precision(self.decimals)
        self.pdepth_entry.set_range(-910000.0000, 0.0000)

        adv_grid.addWidget(self.pdepth_label, 8, 0)
        adv_grid.addWidget(self.pdepth_entry, 8, 1, 1, 2)

        # Probe feedrate
        self.feedrate_probe_label = FCLabel('%s:' % _("Feedrate Probe"))
        self.feedrate_probe_label.setToolTip(
           _("The feedrate used while the probe is probing.")
        )
        self.feedrate_probe_entry = FCDoubleSpinner()
        self.feedrate_probe_entry.set_precision(self.decimals)
        self.feedrate_probe_entry.set_range(0, 910000.0000)

        adv_grid.addWidget(self.feedrate_probe_label, 10, 0)
        adv_grid.addWidget(self.feedrate_probe_entry, 10, 1, 1, 2)

        # Spindle direction
        spindle_dir_label = FCLabel('%s:' % _('Spindle direction'))
        spindle_dir_label.setToolTip(
            _("This sets the direction that the spindle is rotating.\n"
              "It can be either:\n"
              "- CW = clockwise or\n"
              "- CCW = counter clockwise")
        )

        self.spindledir_radio = RadioSet([{'label': _('CW'), 'value': 'CW'},
                                          {'label': _('CCW'), 'value': 'CCW'}], compact=True)
        adv_grid.addWidget(spindle_dir_label, 12, 0)
        adv_grid.addWidget(self.spindledir_radio, 12, 1, 1, 2)

        self.fplunge_cb = FCCheckBox('%s' % _('Fast Plunge'))
        self.fplunge_cb.setToolTip(
            _("By checking this, the vertical move from\n"
              "Z_Toolchange to Z_move is done with G0,\n"
              "meaning the fastest speed available.\n"
              "WARNING: the move is done at Toolchange X,Y coords.")
        )
        adv_grid.addWidget(self.fplunge_cb, 14, 0)

        self.fretract_cb = FCCheckBox('%s' % _('Fast Retract'))
        self.fretract_cb.setToolTip(
            _("Exit hole strategy.\n"
              " - When uncheked, while exiting the drilled hole the drill bit\n"
              "will travel slow, with set feedrate (G1), up to zero depth and then\n"
              "travel as fast as possible (G0) to the Z Move (travel height).\n"
              " - When checked the travel from Z cut (cut depth) to Z_move\n"
              "(travel height) is done as fast as possible (G0) in one move.")
        )

        adv_grid.addWidget(self.fretract_cb, 14, 1, 1, 2)

        # separator_line = QtWidgets.QFrame()
        # separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        # separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        # adv_grid.addWidget(separator_line, 18, 0, 1, 3)

        # #############################################################################################################
        # Area Exclusion Frame
        # #############################################################################################################
        self.area_exc_label = FCLabel('<span style="color:magenta;"><b>%s</b></span>' % _('Area Exclusion'))
        self.area_exc_label.setToolTip(
            _("Area exclusion parameters.")
        )
        self.layout.addWidget(self.area_exc_label)

        area_frame = FCFrame()
        self.layout.addWidget(area_frame)

        area_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        area_frame.setLayout(area_grid)

        # Exclusion Area CB
        self.exclusion_cb = FCCheckBox('%s' % _("Exclusion areas"))
        self.exclusion_cb.setToolTip(
            _(
                "Include exclusion areas.\n"
                "In those areas the travel of the tools\n"
                "is forbidden."
            )
        )
        area_grid.addWidget(self.exclusion_cb, 0, 0, 1, 3)

        # Area Selection shape
        self.area_shape_label = FCLabel('%s:' % _("Shape"))
        self.area_shape_label.setToolTip(
            _("The kind of selection shape used for area selection.")
        )

        self.area_shape_radio = RadioSet([{'label': _("Square"), 'value': 'square'},
                                          {'label': _("Polygon"), 'value': 'polygon'}])

        area_grid.addWidget(self.area_shape_label, 2, 0)
        area_grid.addWidget(self.area_shape_radio, 2, 1, 1, 2)

        # Chose Strategy
        self.strategy_label = FCLabel('%s:' % _("Strategy"))
        self.strategy_label.setToolTip(_("The strategy followed when encountering an exclusion area.\n"
                                         "Can be:\n"
                                         "- Over -> when encountering the area, the tool will go to a set height\n"
                                         "- Around -> will avoid the exclusion area by going around the area"))
        self.strategy_radio = RadioSet([{'label': _('Over'), 'value': 'over'},
                                        {'label': _('Around'), 'value': 'around'}])

        area_grid.addWidget(self.strategy_label, 4, 0)
        area_grid.addWidget(self.strategy_radio, 4, 1, 1, 2)

        # Over Z
        self.over_z_label = FCLabel('%s:' % _("Over Z"))
        self.over_z_label.setToolTip(_("The height Z to which the tool will rise in order to avoid\n"
                                       "an interdiction area."))
        self.over_z_entry = FCDoubleSpinner()
        self.over_z_entry.set_range(-10000.000, 10000.0000)
        self.over_z_entry.set_precision(self.decimals)

        area_grid.addWidget(self.over_z_label, 6, 0)
        area_grid.addWidget(self.over_z_entry, 6, 1, 1, 2)

        FCGridLayout.set_common_column_size([param_grid, ds_grid, adv_grid, area_grid], 0)

        self.layout.addStretch()
