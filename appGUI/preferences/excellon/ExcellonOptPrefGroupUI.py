from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QSettings

from appGUI.GUIElements import RadioSet, FCDoubleSpinner, FCCheckBox, FCEntry, FCSpinner, OptionalInputSection, \
    FCComboBox, NumericalEvalTupleEntry
from appGUI.preferences import machinist_setting
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


class ExcellonOptPrefGroupUI(OptionsGroupUI):

    def __init__(self, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "Excellon Options", parent=parent)
        super(ExcellonOptPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Excellon Options")))
        self.decimals = decimals

        # ## Create CNC Job
        self.cncjob_label = QtWidgets.QLabel('<b>%s</b>' % _('Create CNC Job'))
        self.cncjob_label.setToolTip(
            _("Parameters used to create a CNC Job object\n"
              "for this drill object.")
        )
        self.layout.addWidget(self.cncjob_label)

        grid2 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid2)
        grid2.setColumnStretch(0, 0)
        grid2.setColumnStretch(1, 1)

        # Operation Type
        self.operation_label = QtWidgets.QLabel('<b>%s:</b>' % _('Operation'))
        self.operation_label.setToolTip(
            _("Operation type:\n"
              "- Drilling -> will drill the drills/slots associated with this tool\n"
              "- Milling -> will mill the drills/slots")
        )
        self.operation_radio = RadioSet(
            [
                {'label': _('Drilling'), 'value': 'drill'},
                {'label': _("Milling"), 'value': 'mill'}
            ]
        )

        grid2.addWidget(self.operation_label, 0, 0)
        grid2.addWidget(self.operation_radio, 0, 1)

        self.mill_type_label = QtWidgets.QLabel('%s:' % _('Milling Type'))
        self.mill_type_label.setToolTip(
            _("Milling type:\n"
              "- Drills -> will mill the drills associated with this tool\n"
              "- Slots -> will mill the slots associated with this tool\n"
              "- Both -> will mill both drills and mills or whatever is available")
        )
        self.milling_type_radio = RadioSet(
            [
                {'label': _('Drills'), 'value': 'drills'},
                {'label': _("Slots"), 'value': 'slots'},
                {'label': _("Both"), 'value': 'both'},
            ]
        )

        grid2.addWidget(self.mill_type_label, 1, 0)
        grid2.addWidget(self.milling_type_radio, 1, 1)

        self.mill_dia_label = QtWidgets.QLabel('%s:' % _('Milling Diameter'))
        self.mill_dia_label.setToolTip(
            _("The diameter of the tool who will do the milling")
        )

        self.mill_dia_entry = FCDoubleSpinner()
        self.mill_dia_entry.set_precision(self.decimals)
        self.mill_dia_entry.set_range(0.0000, 9999.9999)

        grid2.addWidget(self.mill_dia_label, 2, 0)
        grid2.addWidget(self.mill_dia_entry, 2, 1)

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

        grid2.addWidget(cutzlabel, 3, 0)
        grid2.addWidget(self.cutz_entry, 3, 1)

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

        grid2.addWidget(self.mpass_cb, 4, 0)
        grid2.addWidget(self.maxdepth_entry, 4, 1)

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

        grid2.addWidget(travelzlabel, 5, 0)
        grid2.addWidget(self.travelz_entry, 5, 1)

        # Tool change:
        self.toolchange_cb = FCCheckBox('%s' % _("Tool change"))
        self.toolchange_cb.setToolTip(
            _("Include tool-change sequence\n"
              "in G-Code (Pause for tool change).")
        )
        grid2.addWidget(self.toolchange_cb, 6, 0, 1, 2)

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

        grid2.addWidget(toolchangezlabel, 7, 0)
        grid2.addWidget(self.toolchangez_entry, 7, 1)

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

        grid2.addWidget(endz_label, 8, 0)
        grid2.addWidget(self.endz_entry, 8, 1)

        # End Move X,Y
        endmove_xy_label = QtWidgets.QLabel('%s:' % _('End move X,Y'))
        endmove_xy_label.setToolTip(
            _("End move X,Y position. In format (x,y).\n"
              "If no value is entered then there is no move\n"
              "on X,Y plane at the end of the job.")
        )
        self.endxy_entry = NumericalEvalTupleEntry(border_color='#0069A9')

        grid2.addWidget(endmove_xy_label, 9, 0)
        grid2.addWidget(self.endxy_entry, 9, 1)

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

        grid2.addWidget(frlabel, 10, 0)
        grid2.addWidget(self.feedrate_z_entry, 10, 1)

        # Spindle speed
        spdlabel = QtWidgets.QLabel('%s:' % _('Spindle Speed'))
        spdlabel.setToolTip(
            _("Speed of the spindle\n"
              "in RPM (optional)")
        )

        self.spindlespeed_entry = FCSpinner()
        self.spindlespeed_entry.set_range(0, 1000000)
        self.spindlespeed_entry.set_step(100)

        grid2.addWidget(spdlabel, 11, 0)
        grid2.addWidget(self.spindlespeed_entry, 11, 1)

        # Dwell
        self.dwell_cb = FCCheckBox('%s' % _('Enable Dwell'))
        self.dwell_cb .setToolTip(
            _("Pause to allow the spindle to reach its\n"
              "speed before cutting.")
        )

        grid2.addWidget(self.dwell_cb, 12, 0, 1, 2)

        # Dwell Time
        dwelltime = QtWidgets.QLabel('%s:' % _('Duration'))
        dwelltime.setToolTip(_("Number of time units for spindle to dwell."))
        self.dwelltime_entry = FCDoubleSpinner()
        self.dwelltime_entry.set_precision(self.decimals)
        self.dwelltime_entry.set_range(0, 99999.9999)

        grid2.addWidget(dwelltime, 13, 0)
        grid2.addWidget(self.dwelltime_entry, 13, 1)

        self.ois_dwell_exc = OptionalInputSection(self.dwell_cb, [self.dwelltime_entry])

        # preprocessor selection
        pp_excellon_label = QtWidgets.QLabel('%s:' % _("Preprocessor"))
        pp_excellon_label.setToolTip(
            _("The preprocessor JSON file that dictates\n"
              "Gcode output.")
        )

        self.pp_excellon_name_cb = FCComboBox()
        self.pp_excellon_name_cb.setFocusPolicy(Qt.StrongFocus)

        grid2.addWidget(pp_excellon_label, 14, 0)
        grid2.addWidget(self.pp_excellon_name_cb, 14, 1)

        # ### Choose what to use for Gcode creation: Drills, Slots or Both
        excellon_gcode_type_label = QtWidgets.QLabel('<b>%s</b>' % _('Gcode'))
        excellon_gcode_type_label.setToolTip(
            _("Choose what to use for GCode generation:\n"
              "'Drills', 'Slots' or 'Both'.\n"
              "When choosing 'Slots' or 'Both', slots will be\n"
              "converted to drills.")
        )
        self.excellon_gcode_type_radio = RadioSet([{'label': 'Drills', 'value': 'drills'},
                                                   {'label': 'Slots', 'value': 'slots'},
                                                   {'label': 'Both', 'value': 'both'}])
        grid2.addWidget(excellon_gcode_type_label, 15, 0)
        grid2.addWidget(self.excellon_gcode_type_radio, 15, 1)

        # until I decide to implement this feature those remain disabled
        excellon_gcode_type_label.hide()
        self.excellon_gcode_type_radio.setVisible(False)

        # ### Milling Holes ## ##
        self.mill_hole_label = QtWidgets.QLabel('<b>%s</b>' % _('Mill Holes'))
        self.mill_hole_label.setToolTip(
            _("Create Geometry for milling holes.")
        )
        grid2.addWidget(self.mill_hole_label, 16, 0, 1, 2)

        tdlabel = QtWidgets.QLabel('%s:' % _('Drill Tool dia'))
        tdlabel.setToolTip(
            _("Diameter of the cutting tool.")
        )
        self.tooldia_entry = FCDoubleSpinner()
        self.tooldia_entry.set_precision(self.decimals)
        self.tooldia_entry.set_range(0, 999.9999)

        grid2.addWidget(tdlabel, 18, 0)
        grid2.addWidget(self.tooldia_entry, 18, 1)

        stdlabel = QtWidgets.QLabel('%s:' % _('Slot Tool dia'))
        stdlabel.setToolTip(
            _("Diameter of the cutting tool\n"
              "when milling slots.")
        )
        self.slot_tooldia_entry = FCDoubleSpinner()
        self.slot_tooldia_entry.set_precision(self.decimals)
        self.slot_tooldia_entry.set_range(0, 999.9999)

        grid2.addWidget(stdlabel, 21, 0)
        grid2.addWidget(self.slot_tooldia_entry, 21, 1)

        self.layout.addStretch()
