from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings, Qt

from appGUI.GUIElements import RadioSet, FCDoubleSpinner, FCComboBox, FCCheckBox, FCSpinner, NumericalEvalTupleEntry, \
    OptionalInputSection, NumericalEvalEntry, FCLabel
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


class ToolsDrillPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):
        super(ToolsDrillPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Drilling Tool Options")))
        self.decimals = decimals

        # ## Clear non-copper regions
        self.drill_label = FCLabel("<b>%s:</b>" % _("Parameters"))
        self.drill_label.setToolTip(
            _("Create CNCJob with toolpaths for drilling or milling holes.")
        )
        self.layout.addWidget(self.drill_label)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        # Tool order Radio Button
        self.order_label = FCLabel('%s:' % _('Tool order'))
        self.order_label.setToolTip(_("This set the way that the tools in the tools table are used.\n"
                                      "'No' --> means that the used order is the one in the tool table\n"
                                      "'Forward' --> means that the tools will be ordered from small to big\n"
                                      "'Reverse' --> means that the tools will ordered from big to small\n\n"
                                      "WARNING: using rest machining will automatically set the order\n"
                                      "in reverse and disable this control."))

        self.order_radio = RadioSet([{'label': _('No'), 'value': 'no'},
                                     {'label': _('Forward'), 'value': 'fwd'},
                                     {'label': _('Reverse'), 'value': 'rev'}])

        grid0.addWidget(self.order_label, 1, 0)
        grid0.addWidget(self.order_radio, 1, 1, 1, 2)

        # Cut Z
        cutzlabel = FCLabel('%s:' % _('Cut Z'))
        cutzlabel.setToolTip(
            _("Drill depth (negative)\n"
              "below the copper surface.")
        )

        self.cutz_entry = FCDoubleSpinner()

        if machinist_setting == 0:
            self.cutz_entry.set_range(-10000.0000, 0.0000)
        else:
            self.cutz_entry.set_range(-10000.0000, 10000.0000)

        self.cutz_entry.setSingleStep(0.1)
        self.cutz_entry.set_precision(self.decimals)

        grid0.addWidget(cutzlabel, 3, 0)
        grid0.addWidget(self.cutz_entry, 3, 1, 1, 2)

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

        grid0.addWidget(self.mpass_cb, 4, 0)
        grid0.addWidget(self.maxdepth_entry, 4, 1, 1, 2)

        # Travel Z
        travelzlabel = FCLabel('%s:' % _('Travel Z'))
        travelzlabel.setToolTip(
            _("Tool height when travelling\n"
              "across the XY plane.")
        )

        self.travelz_entry = FCDoubleSpinner()
        self.travelz_entry.set_precision(self.decimals)

        if machinist_setting == 0:
            self.travelz_entry.set_range(0.0001, 10000.0000)
        else:
            self.travelz_entry.set_range(-10000.0000, 10000.0000)

        grid0.addWidget(travelzlabel, 5, 0)
        grid0.addWidget(self.travelz_entry, 5, 1, 1, 2)

        # Tool change:
        self.toolchange_cb = FCCheckBox('%s' % _("Tool change"))
        self.toolchange_cb.setToolTip(
            _("Include tool-change sequence\n"
              "in G-Code (Pause for tool change).")
        )
        grid0.addWidget(self.toolchange_cb, 6, 0, 1, 3)

        # Tool Change Z
        toolchangezlabel = FCLabel('%s:' % _('Toolchange Z'))
        toolchangezlabel.setToolTip(
            _("Z-axis position (height) for\n"
              "tool change.")
        )

        self.toolchangez_entry = FCDoubleSpinner()
        self.toolchangez_entry.set_precision(self.decimals)

        if machinist_setting == 0:
            self.toolchangez_entry.set_range(0.0001, 10000.0000)
        else:
            self.toolchangez_entry.set_range(-10000.0000, 10000.0000)

        grid0.addWidget(toolchangezlabel, 7, 0)
        grid0.addWidget(self.toolchangez_entry, 7, 1, 1, 2)

        # End Move Z
        endz_label = FCLabel('%s:' % _('End move Z'))
        endz_label.setToolTip(
            _("Height of the tool after\n"
              "the last move at the end of the job.")
        )
        self.endz_entry = FCDoubleSpinner()
        self.endz_entry.set_precision(self.decimals)

        if machinist_setting == 0:
            self.endz_entry.set_range(0.0000, 10000.0000)
        else:
            self.endz_entry.set_range(-10000.0000, 10000.0000)

        grid0.addWidget(endz_label, 8, 0)
        grid0.addWidget(self.endz_entry, 8, 1, 1, 2)

        # End Move X,Y
        endmove_xy_label = FCLabel('%s:' % _('End move X,Y'))
        endmove_xy_label.setToolTip(
            _("End move X,Y position. In format (x,y).\n"
              "If no value is entered then there is no move\n"
              "on X,Y plane at the end of the job.")
        )
        self.endxy_entry = NumericalEvalTupleEntry(border_color='#0069A9')

        grid0.addWidget(endmove_xy_label, 9, 0)
        grid0.addWidget(self.endxy_entry, 9, 1, 1, 2)

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

        grid0.addWidget(frlabel, 10, 0)
        grid0.addWidget(self.feedrate_z_entry, 10, 1, 1, 2)

        # Spindle speed
        spdlabel = FCLabel('%s:' % _('Spindle Speed'))
        spdlabel.setToolTip(
            _("Speed of the spindle\n"
              "in RPM (optional)")
        )

        self.spindlespeed_entry = FCSpinner()
        self.spindlespeed_entry.set_range(0, 1000000)
        self.spindlespeed_entry.set_step(100)

        grid0.addWidget(spdlabel, 11, 0)
        grid0.addWidget(self.spindlespeed_entry, 11, 1, 1, 2)

        # Dwell
        self.dwell_cb = FCCheckBox('%s' % _('Enable Dwell'))
        self.dwell_cb.setToolTip(
            _("Pause to allow the spindle to reach its\n"
              "speed before cutting.")
        )

        grid0.addWidget(self.dwell_cb, 12, 0, 1, 3)

        # Dwell Time
        dwelltime = FCLabel('%s:' % _('Duration'))
        dwelltime.setToolTip(_("Number of time units for spindle to dwell."))
        self.dwelltime_entry = FCDoubleSpinner()
        self.dwelltime_entry.set_precision(self.decimals)
        self.dwelltime_entry.set_range(0, 910000.0000)

        grid0.addWidget(dwelltime, 13, 0)
        grid0.addWidget(self.dwelltime_entry, 13, 1, 1, 2)

        self.ois_dwell_exc = OptionalInputSection(self.dwell_cb, [self.dwelltime_entry])

        # preprocessor selection
        pp_excellon_label = FCLabel('%s:' % _("Preprocessor"))
        pp_excellon_label.setToolTip(
            _("The preprocessor JSON file that dictates\n"
              "Gcode output.")
        )

        self.pp_excellon_name_cb = FCComboBox()
        self.pp_excellon_name_cb.setFocusPolicy(Qt.StrongFocus)
        self.pp_excellon_name_cb.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)

        grid0.addWidget(pp_excellon_label, 14, 0)
        grid0.addWidget(self.pp_excellon_name_cb, 14, 1, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 16, 0, 1, 3)

        # DRILL SLOTS LABEL
        self.dslots_label = FCLabel('<b>%s:</b>' % _('Drilling Slots'))
        grid0.addWidget(self.dslots_label, 18, 0, 1, 3)

        # Drill slots
        self.drill_slots_cb = FCCheckBox('%s' % _('Drill slots'))
        self.drill_slots_cb.setToolTip(
            _("If the selected tool has slots then they will be drilled.")
        )
        grid0.addWidget(self.drill_slots_cb, 20, 0, 1, 3)

        # Drill Overlap
        self.drill_overlap_label = FCLabel('%s:' % _('Overlap'))
        self.drill_overlap_label.setToolTip(
            _("How much (percentage) of the tool diameter to overlap previous drill hole.")
        )

        self.drill_overlap_entry = FCDoubleSpinner()
        self.drill_overlap_entry.set_precision(self.decimals)
        self.drill_overlap_entry.set_range(0.0, 10000.0000)
        self.drill_overlap_entry.setSingleStep(0.1)

        grid0.addWidget(self.drill_overlap_label, 22, 0)
        grid0.addWidget(self.drill_overlap_entry, 22, 1, 1, 2)

        # Last drill in slot
        self.last_drill_cb = FCCheckBox('%s' % _('Last drill'))
        self.last_drill_cb.setToolTip(
            _("If the slot length is not completely covered by drill holes,\n"
              "add a drill hole on the slot end point.")
        )
        grid0.addWidget(self.last_drill_cb, 24, 0, 1, 3)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 26, 0, 1, 3)

        self.exc_label = FCLabel('<b>%s:</b>' % _('Advanced Options'))
        self.exc_label.setToolTip(
            _("A list of advanced parameters.")
        )
        grid0.addWidget(self.exc_label, 28, 0, 1, 3)

        # Offset Z
        offsetlabel = FCLabel('%s:' % _('Offset Z'))
        offsetlabel.setToolTip(
            _("Some drill bits (the larger ones) need to drill deeper\n"
              "to create the desired exit hole diameter due of the tip shape.\n"
              "The value here can compensate the Cut Z parameter."))
        self.offset_entry = FCDoubleSpinner()
        self.offset_entry.set_precision(self.decimals)
        self.offset_entry.set_range(-999.9999, 999.9999)

        grid0.addWidget(offsetlabel, 29, 0)
        grid0.addWidget(self.offset_entry, 29, 1, 1, 2)

        # ToolChange X,Y
        toolchange_xy_label = FCLabel('%s:' % _('Toolchange X,Y'))
        toolchange_xy_label.setToolTip(
            _("Toolchange X,Y position.")
        )
        self.toolchangexy_entry = NumericalEvalTupleEntry(border_color='#0069A9')

        grid0.addWidget(toolchange_xy_label, 31, 0)
        grid0.addWidget(self.toolchangexy_entry, 31, 1, 1, 2)

        # Start Z
        startzlabel = FCLabel('%s:' % _('Start Z'))
        startzlabel.setToolTip(
            _("Height of the tool just after starting the work.\n"
              "Delete the value if you don't need this feature.")
        )
        self.estartz_entry = NumericalEvalEntry(border_color='#0069A9')

        grid0.addWidget(startzlabel, 33, 0)
        grid0.addWidget(self.estartz_entry, 33, 1, 1, 2)

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

        grid0.addWidget(fr_rapid_label, 35, 0)
        grid0.addWidget(self.feedrate_rapid_entry, 35, 1, 1, 2)

        # Probe depth
        self.pdepth_label = FCLabel('%s:' % _("Probe Z depth"))
        self.pdepth_label.setToolTip(
            _("The maximum depth that the probe is allowed\n"
              "to probe. Negative value, in current units.")
        )
        self.pdepth_entry = FCDoubleSpinner()
        self.pdepth_entry.set_precision(self.decimals)
        self.pdepth_entry.set_range(-910000.0000, 0.0000)

        grid0.addWidget(self.pdepth_label, 37, 0)
        grid0.addWidget(self.pdepth_entry, 37, 1, 1, 2)

        # Probe feedrate
        self.feedrate_probe_label = FCLabel('%s:' % _("Feedrate Probe"))
        self.feedrate_probe_label.setToolTip(
           _("The feedrate used while the probe is probing.")
        )
        self.feedrate_probe_entry = FCDoubleSpinner()
        self.feedrate_probe_entry.set_precision(self.decimals)
        self.feedrate_probe_entry.set_range(0, 910000.0000)

        grid0.addWidget(self.feedrate_probe_label, 38, 0)
        grid0.addWidget(self.feedrate_probe_entry, 38, 1, 1, 2)

        # Spindle direction
        spindle_dir_label = FCLabel('%s:' % _('Spindle direction'))
        spindle_dir_label.setToolTip(
            _("This sets the direction that the spindle is rotating.\n"
              "It can be either:\n"
              "- CW = clockwise or\n"
              "- CCW = counter clockwise")
        )

        self.spindledir_radio = RadioSet([{'label': _('CW'), 'value': 'CW'},
                                          {'label': _('CCW'), 'value': 'CCW'}])
        grid0.addWidget(spindle_dir_label, 40, 0)
        grid0.addWidget(self.spindledir_radio, 40, 1, 1, 2)

        self.fplunge_cb = FCCheckBox('%s' % _('Fast Plunge'))
        self.fplunge_cb.setToolTip(
            _("By checking this, the vertical move from\n"
              "Z_Toolchange to Z_move is done with G0,\n"
              "meaning the fastest speed available.\n"
              "WARNING: the move is done at Toolchange X,Y coords.")
        )
        grid0.addWidget(self.fplunge_cb, 42, 0, 1, 3)

        self.fretract_cb = FCCheckBox('%s' % _('Fast Retract'))
        self.fretract_cb.setToolTip(
            _("Exit hole strategy.\n"
              " - When uncheked, while exiting the drilled hole the drill bit\n"
              "will travel slow, with set feedrate (G1), up to zero depth and then\n"
              "travel as fast as possible (G0) to the Z Move (travel height).\n"
              " - When checked the travel from Z cut (cut depth) to Z_move\n"
              "(travel height) is done as fast as possible (G0) in one move.")
        )

        grid0.addWidget(self.fretract_cb, 45, 0, 1, 3)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 46, 0, 1, 3)

        # -----------------------------
        # --- Area Exclusion ----------
        # -----------------------------
        self.area_exc_label = FCLabel('<b>%s:</b>' % _('Area Exclusion'))
        self.area_exc_label.setToolTip(
            _("Area exclusion parameters.")
        )
        grid0.addWidget(self.area_exc_label, 47, 0, 1, 2)

        # Exclusion Area CB
        self.exclusion_cb = FCCheckBox('%s' % _("Exclusion areas"))
        self.exclusion_cb.setToolTip(
            _(
                "Include exclusion areas.\n"
                "In those areas the travel of the tools\n"
                "is forbidden."
            )
        )
        grid0.addWidget(self.exclusion_cb, 49, 0, 1, 2)

        # Area Selection shape
        self.area_shape_label = FCLabel('%s:' % _("Shape"))
        self.area_shape_label.setToolTip(
            _("The kind of selection shape used for area selection.")
        )

        self.area_shape_radio = RadioSet([{'label': _("Square"), 'value': 'square'},
                                          {'label': _("Polygon"), 'value': 'polygon'}])

        grid0.addWidget(self.area_shape_label, 51, 0)
        grid0.addWidget(self.area_shape_radio, 51, 1)

        # Chose Strategy
        self.strategy_label = FCLabel('%s:' % _("Strategy"))
        self.strategy_label.setToolTip(_("The strategy followed when encountering an exclusion area.\n"
                                         "Can be:\n"
                                         "- Over -> when encountering the area, the tool will go to a set height\n"
                                         "- Around -> will avoid the exclusion area by going around the area"))
        self.strategy_radio = RadioSet([{'label': _('Over'), 'value': 'over'},
                                        {'label': _('Around'), 'value': 'around'}])

        grid0.addWidget(self.strategy_label, 53, 0)
        grid0.addWidget(self.strategy_radio, 53, 1)

        # Over Z
        self.over_z_label = FCLabel('%s:' % _("Over Z"))
        self.over_z_label.setToolTip(_("The height Z to which the tool will rise in order to avoid\n"
                                       "an interdiction area."))
        self.over_z_entry = FCDoubleSpinner()
        self.over_z_entry.set_range(0.000, 10000.0000)
        self.over_z_entry.set_precision(self.decimals)

        grid0.addWidget(self.over_z_label, 55, 0)
        grid0.addWidget(self.over_z_entry, 55, 1)

        self.layout.addStretch()
