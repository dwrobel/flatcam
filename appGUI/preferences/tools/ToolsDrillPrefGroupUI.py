from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings, Qt

from appGUI.GUIElements import RadioSet, FCDoubleSpinner, FCComboBox, FCCheckBox, FCSpinner, NumericalEvalTupleEntry, \
    OptionalInputSection
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
        self.drill_label = QtWidgets.QLabel("<b>%s:</b>" % _("Parameters"))
        self.drill_label.setToolTip(
            _("Create CNCJob with toolpaths for drilling or milling holes.")
        )
        self.layout.addWidget(self.drill_label)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        # Tool order Radio Button
        self.order_label = QtWidgets.QLabel('%s:' % _('Tool order'))
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
        cutzlabel = QtWidgets.QLabel('%s:' % _('Cut Z'))
        cutzlabel.setToolTip(
            _("Drill depth (negative)\n"
              "below the copper surface.")
        )

        self.cutz_entry = FCDoubleSpinner()

        if machinist_setting == 0:
            self.cutz_entry.set_range(-9999.9999, 0.0000)
        else:
            self.cutz_entry.set_range(-9999.9999, 9999.9999)

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
        self.maxdepth_entry.set_range(0, 9999.9999)
        self.maxdepth_entry.setSingleStep(0.1)

        self.maxdepth_entry.setToolTip(_("Depth of each pass (positive)."))

        grid0.addWidget(self.mpass_cb, 4, 0)
        grid0.addWidget(self.maxdepth_entry, 4, 1, 1, 2)

        # Travel Z
        travelzlabel = QtWidgets.QLabel('%s:' % _('Travel Z'))
        travelzlabel.setToolTip(
            _("Tool height when travelling\n"
              "across the XY plane.")
        )

        self.travelz_entry = FCDoubleSpinner()
        self.travelz_entry.set_precision(self.decimals)

        if machinist_setting == 0:
            self.travelz_entry.set_range(0.0001, 9999.9999)
        else:
            self.travelz_entry.set_range(-9999.9999, 9999.9999)

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
        toolchangezlabel = QtWidgets.QLabel('%s:' % _('Toolchange Z'))
        toolchangezlabel.setToolTip(
            _("Z-axis position (height) for\n"
              "tool change.")
        )

        self.toolchangez_entry = FCDoubleSpinner()
        self.toolchangez_entry.set_precision(self.decimals)

        if machinist_setting == 0:
            self.toolchangez_entry.set_range(0.0001, 9999.9999)
        else:
            self.toolchangez_entry.set_range(-9999.9999, 9999.9999)

        grid0.addWidget(toolchangezlabel, 7, 0)
        grid0.addWidget(self.toolchangez_entry, 7, 1, 1, 2)

        # End Move Z
        endz_label = QtWidgets.QLabel('%s:' % _('End move Z'))
        endz_label.setToolTip(
            _("Height of the tool after\n"
              "the last move at the end of the job.")
        )
        self.endz_entry = FCDoubleSpinner()
        self.endz_entry.set_precision(self.decimals)

        if machinist_setting == 0:
            self.endz_entry.set_range(0.0000, 9999.9999)
        else:
            self.endz_entry.set_range(-9999.9999, 9999.9999)

        grid0.addWidget(endz_label, 8, 0)
        grid0.addWidget(self.endz_entry, 8, 1, 1, 2)

        # End Move X,Y
        endmove_xy_label = QtWidgets.QLabel('%s:' % _('End move X,Y'))
        endmove_xy_label.setToolTip(
            _("End move X,Y position. In format (x,y).\n"
              "If no value is entered then there is no move\n"
              "on X,Y plane at the end of the job.")
        )
        self.endxy_entry = NumericalEvalTupleEntry(border_color='#0069A9')

        grid0.addWidget(endmove_xy_label, 9, 0)
        grid0.addWidget(self.endxy_entry, 9, 1, 1, 2)

        # Feedrate Z
        frlabel = QtWidgets.QLabel('%s:' % _('Feedrate Z'))
        frlabel.setToolTip(
            _("Tool speed while drilling\n"
              "(in units per minute).\n"
              "So called 'Plunge' feedrate.\n"
              "This is for linear move G01.")
        )
        self.feedrate_z_entry = FCDoubleSpinner()
        self.feedrate_z_entry.set_precision(self.decimals)
        self.feedrate_z_entry.set_range(0, 99999.9999)

        grid0.addWidget(frlabel, 10, 0)
        grid0.addWidget(self.feedrate_z_entry, 10, 1, 1, 2)

        # Spindle speed
        spdlabel = QtWidgets.QLabel('%s:' % _('Spindle Speed'))
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
        dwelltime = QtWidgets.QLabel('%s:' % _('Duration'))
        dwelltime.setToolTip(_("Number of time units for spindle to dwell."))
        self.dwelltime_entry = FCDoubleSpinner()
        self.dwelltime_entry.set_precision(self.decimals)
        self.dwelltime_entry.set_range(0, 99999.9999)

        grid0.addWidget(dwelltime, 13, 0)
        grid0.addWidget(self.dwelltime_entry, 13, 1, 1, 2)

        self.ois_dwell_exc = OptionalInputSection(self.dwell_cb, [self.dwelltime_entry])

        # preprocessor selection
        pp_excellon_label = QtWidgets.QLabel('%s:' % _("Preprocessor"))
        pp_excellon_label.setToolTip(
            _("The preprocessor JSON file that dictates\n"
              "Gcode output.")
        )

        self.pp_excellon_name_cb = FCComboBox()
        self.pp_excellon_name_cb.setFocusPolicy(Qt.StrongFocus)

        grid0.addWidget(pp_excellon_label, 14, 0)
        grid0.addWidget(self.pp_excellon_name_cb, 14, 1, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 16, 0, 1, 3)

        # DRILL SLOTS LABEL
        self.dslots_label = QtWidgets.QLabel('<b>%s:</b>' % _('Drilling Slots'))
        grid0.addWidget(self.dslots_label, 18, 0, 1, 3)

        # Drill slots
        self.drill_slots_cb = FCCheckBox('%s' % _('Drill slots'))
        self.drill_slots_cb.setToolTip(
            _("If the selected tool has slots then they will be drilled.")
        )
        grid0.addWidget(self.drill_slots_cb, 20, 0, 1, 3)

        # Drill Overlap
        self.drill_overlap_label = QtWidgets.QLabel('%s:' % _('Overlap'))
        self.drill_overlap_label.setToolTip(
            _("How much (percentage) of the tool diameter to overlap previous drill hole.")
        )

        self.drill_overlap_entry = FCDoubleSpinner()
        self.drill_overlap_entry.set_precision(self.decimals)
        self.drill_overlap_entry.set_range(0.0, 9999.9999)
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

        self.layout.addStretch()
