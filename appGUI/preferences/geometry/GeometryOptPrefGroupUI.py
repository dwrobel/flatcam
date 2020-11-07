from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QSettings

from appGUI.GUIElements import FCDoubleSpinner, FCCheckBox, OptionalInputSection, FCSpinner, FCComboBox, \
    NumericalEvalTupleEntry
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


class GeometryOptPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "Geometry Options Preferences", parent=parent)
        super(GeometryOptPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Geometry Options")))
        self.decimals = decimals

        # ------------------------------
        # ## Create CNC Job
        # ------------------------------
        self.cncjob_label = QtWidgets.QLabel('<b>%s:</b>' % _('Create CNCJob'))
        self.cncjob_label.setToolTip(
            _("Create a CNC Job object\n"
              "tracing the contours of this\n"
              "Geometry object.")
        )
        self.layout.addWidget(self.cncjob_label)

        grid1 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid1)
        grid1.setColumnStretch(0, 0)
        grid1.setColumnStretch(1, 1)

        # Cut Z
        cutzlabel = QtWidgets.QLabel('%s:' % _('Cut Z'))
        cutzlabel.setToolTip(
            _("Cutting depth (negative)\n"
              "below the copper surface.")
        )
        self.cutz_entry = FCDoubleSpinner()

        if machinist_setting == 0:
            self.cutz_entry.set_range(-10000.0000, 0.0000)
        else:
            self.cutz_entry.set_range(-10000.0000, 10000.0000)

        self.cutz_entry.set_precision(self.decimals)
        self.cutz_entry.setSingleStep(0.1)
        self.cutz_entry.setWrapping(True)

        grid1.addWidget(cutzlabel, 0, 0)
        grid1.addWidget(self.cutz_entry, 0, 1)

        # Multidepth CheckBox
        self.multidepth_cb = FCCheckBox(label=_('Multi-Depth'))
        self.multidepth_cb.setToolTip(
            _(
                "Use multiple passes to limit\n"
                "the cut depth in each pass. Will\n"
                "cut multiple times until Cut Z is\n"
                "reached."
            )
        )
        grid1.addWidget(self.multidepth_cb, 1, 0)

        # Depth/pass
        dplabel = QtWidgets.QLabel('%s:' % _('Depth/Pass'))
        dplabel.setToolTip(
            _("The depth to cut on each pass,\n"
              "when multidepth is enabled.\n"
              "It has positive value although\n"
              "it is a fraction from the depth\n"
              "which has negative value.")
        )

        self.depthperpass_entry = FCDoubleSpinner()
        self.depthperpass_entry.set_range(0, 99999)
        self.depthperpass_entry.set_precision(self.decimals)
        self.depthperpass_entry.setSingleStep(0.1)
        self.depthperpass_entry.setWrapping(True)

        grid1.addWidget(dplabel, 2, 0)
        grid1.addWidget(self.depthperpass_entry, 2, 1)

        self.ois_multidepth = OptionalInputSection(self.multidepth_cb, [self.depthperpass_entry])

        # Travel Z
        travelzlabel = QtWidgets.QLabel('%s:' % _('Travel Z'))
        travelzlabel.setToolTip(
            _("Height of the tool when\n"
              "moving without cutting.")
        )
        self.travelz_entry = FCDoubleSpinner()

        if machinist_setting == 0:
            self.travelz_entry.set_range(0.0001, 10000.0000)
        else:
            self.travelz_entry.set_range(-10000.0000, 10000.0000)

        self.travelz_entry.set_precision(self.decimals)
        self.travelz_entry.setSingleStep(0.1)
        self.travelz_entry.setWrapping(True)

        grid1.addWidget(travelzlabel, 3, 0)
        grid1.addWidget(self.travelz_entry, 3, 1)

        # Tool change:
        self.toolchange_cb = FCCheckBox('%s' % _("Tool change"))
        self.toolchange_cb.setToolTip(
            _(
                "Include tool-change sequence\n"
                "in the Machine Code (Pause for tool change)."
            )
        )
        grid1.addWidget(self.toolchange_cb, 4, 0, 1, 2)

        # Toolchange Z
        toolchangezlabel = QtWidgets.QLabel('%s:' % _('Toolchange Z'))
        toolchangezlabel.setToolTip(
            _(
                "Z-axis position (height) for\n"
                "tool change."
            )
        )
        self.toolchangez_entry = FCDoubleSpinner()

        if machinist_setting == 0:
            self.toolchangez_entry.set_range(0.000, 10000.0000)
        else:
            self.toolchangez_entry.set_range(-10000.0000, 10000.0000)

        self.toolchangez_entry.set_precision(self.decimals)
        self.toolchangez_entry.setSingleStep(0.1)
        self.toolchangez_entry.setWrapping(True)

        grid1.addWidget(toolchangezlabel, 5, 0)
        grid1.addWidget(self.toolchangez_entry, 5, 1)

        # End move Z
        endz_label = QtWidgets.QLabel('%s:' % _('End move Z'))
        endz_label.setToolTip(
            _("Height of the tool after\n"
              "the last move at the end of the job.")
        )
        self.endz_entry = FCDoubleSpinner()

        if machinist_setting == 0:
            self.endz_entry.set_range(0.000, 10000.0000)
        else:
            self.endz_entry.set_range(-10000.0000, 10000.0000)

        self.endz_entry.set_precision(self.decimals)
        self.endz_entry.setSingleStep(0.1)
        self.endz_entry.setWrapping(True)

        grid1.addWidget(endz_label, 6, 0)
        grid1.addWidget(self.endz_entry, 6, 1)

        # End Move X,Y
        endmove_xy_label = QtWidgets.QLabel('%s:' % _('End move X,Y'))
        endmove_xy_label.setToolTip(
            _("End move X,Y position. In format (x,y).\n"
              "If no value is entered then there is no move\n"
              "on X,Y plane at the end of the job.")
        )
        self.endxy_entry = NumericalEvalTupleEntry(border_color='#0069A9')

        grid1.addWidget(endmove_xy_label, 7, 0)
        grid1.addWidget(self.endxy_entry, 7, 1)

        # Feedrate X-Y
        frlabel = QtWidgets.QLabel('%s:' % _('Feedrate X-Y'))
        frlabel.setToolTip(
            _("Cutting speed in the XY\n"
              "plane in units per minute")
        )
        self.cncfeedrate_entry = FCDoubleSpinner()
        self.cncfeedrate_entry.set_range(0, 910000.0000)
        self.cncfeedrate_entry.set_precision(self.decimals)
        self.cncfeedrate_entry.setSingleStep(0.1)
        self.cncfeedrate_entry.setWrapping(True)

        grid1.addWidget(frlabel, 8, 0)
        grid1.addWidget(self.cncfeedrate_entry, 8, 1)

        # Feedrate Z (Plunge)
        frz_label = QtWidgets.QLabel('%s:' % _('Feedrate Z'))
        frz_label.setToolTip(
            _("Cutting speed in the XY\n"
              "plane in units per minute.\n"
              "It is called also Plunge.")
        )
        self.feedrate_z_entry = FCDoubleSpinner()
        self.feedrate_z_entry.set_range(0, 910000.0000)
        self.feedrate_z_entry.set_precision(self.decimals)
        self.feedrate_z_entry.setSingleStep(0.1)
        self.feedrate_z_entry.setWrapping(True)

        grid1.addWidget(frz_label, 9, 0)
        grid1.addWidget(self.feedrate_z_entry, 9, 1)

        # Spindle Speed
        spdlabel = QtWidgets.QLabel('%s:' % _('Spindle speed'))
        spdlabel.setToolTip(
            _(
                "Speed of the spindle in RPM (optional).\n"
                "If LASER preprocessor is used,\n"
                "this value is the power of laser."
            )
        )
        self.cncspindlespeed_entry = FCSpinner()
        self.cncspindlespeed_entry.set_range(0, 1000000)
        self.cncspindlespeed_entry.set_step(100)

        grid1.addWidget(spdlabel, 10, 0)
        grid1.addWidget(self.cncspindlespeed_entry, 10, 1)

        # Dwell
        self.dwell_cb = FCCheckBox(label='%s' % _('Enable Dwell'))
        self.dwell_cb.setToolTip(
            _("Pause to allow the spindle to reach its\n"
              "speed before cutting.")
        )
        dwelltime = QtWidgets.QLabel('%s:' % _('Duration'))
        dwelltime.setToolTip(
            _("Number of time units for spindle to dwell.")
        )
        self.dwelltime_entry = FCDoubleSpinner()
        self.dwelltime_entry.set_range(0, 99999)
        self.dwelltime_entry.set_precision(self.decimals)
        self.dwelltime_entry.setSingleStep(0.1)
        self.dwelltime_entry.setWrapping(True)

        grid1.addWidget(self.dwell_cb, 11, 0)
        grid1.addWidget(dwelltime, 12, 0)
        grid1.addWidget(self.dwelltime_entry, 12, 1)

        self.ois_dwell = OptionalInputSection(self.dwell_cb, [self.dwelltime_entry])

        # preprocessor selection
        pp_label = QtWidgets.QLabel('%s:' % _("Preprocessor"))
        pp_label.setToolTip(
            _("The Preprocessor file that dictates\n"
              "the Machine Code (like GCode, RML, HPGL) output.")
        )
        self.pp_geometry_name_cb = FCComboBox()
        self.pp_geometry_name_cb.setFocusPolicy(Qt.StrongFocus)
        self.pp_geometry_name_cb.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)

        grid1.addWidget(pp_label, 13, 0)
        grid1.addWidget(self.pp_geometry_name_cb, 13, 1)

        self.layout.addStretch()
