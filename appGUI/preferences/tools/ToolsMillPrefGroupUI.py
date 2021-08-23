from PyQt6 import QtWidgets, QtCore
from PyQt6.QtCore import Qt

from appGUI.GUIElements import RadioSet, FCDoubleSpinner, FCComboBox, FCCheckBox, FCSpinner, NumericalEvalTupleEntry, \
    OptionalInputSection, NumericalEvalEntry, FCLabel, FCComboBox2, FCEntry, FCGridLayout
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ToolsMillPrefGroupUI(OptionsGroupUI):
    def __init__(self, defaults, decimals=4, parent=None):
        super(ToolsMillPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Milling Plugin")))
        self.decimals = decimals
        self.defaults = defaults

        # ## Clear non-copper regions
        self.mill_label = FCLabel("<b>%s:</b>" % _("Parameters"))
        self.mill_label.setToolTip(
            _("Create CNCJob with toolpaths for milling either Geometry or drill holes.")
        )
        self.layout.addWidget(self.mill_label)

        grid0 = FCGridLayout(v_spacing=5, h_spacing=3)
        self.layout.addLayout(grid0)

        # Tooldia
        tdlabel = FCLabel('<b><font color="green">%s:</font></b>' % _('Tools Dia'))
        tdlabel.setToolTip(
            _("Diameters of the tools, separated by comma.\n"
              "The value of the diameter has to use the dot decimals separator.\n"
              "Valid values: 0.3, 1.0")
        )
        self.cnctooldia_entry = FCEntry()

        grid0.addWidget(tdlabel, 0, 0)
        grid0.addWidget(self.cnctooldia_entry, 0, 1)

        # Tip Dia
        self.tipdialabel = FCLabel('%s:' % _('V-Tip Dia'))
        self.tipdialabel.setToolTip(
            _(
                "The tip diameter for V-Shape Tool"
            )
        )
        self.tipdia_entry = FCDoubleSpinner()
        self.tipdia_entry.set_precision(self.decimals)
        self.tipdia_entry.set_range(0.00001, 10000.0000)
        self.tipdia_entry.setSingleStep(0.1)

        grid0.addWidget(self.tipdialabel, 2, 0)
        grid0.addWidget(self.tipdia_entry, 2, 1)

        # Tip Angle
        self.tipanglelabel = FCLabel('%s:' % _('V-Tip Angle'))
        self.tipanglelabel.setToolTip(
            _(
                "The tip angle for V-Shape Tool.\n"
                "In degree."
            )
        )
        self.tipangle_entry = FCDoubleSpinner()
        self.tipangle_entry.set_precision(self.decimals)
        self.tipangle_entry.set_range(1.0, 180.0)
        self.tipangle_entry.setSingleStep(1)

        grid0.addWidget(self.tipanglelabel, 4, 0)
        grid0.addWidget(self.tipangle_entry, 4, 1)

        # Cut Z
        cutzlabel = FCLabel('%s:' % _('Cut Z'))
        cutzlabel.setToolTip(
            _("Cutting depth (negative)\n"
              "below the copper surface.")
        )
        self.cutz_entry = FCDoubleSpinner()
        self.cutz_entry.set_range(-10000.0000, 10000.0000)

        self.cutz_entry.set_precision(self.decimals)
        self.cutz_entry.setSingleStep(0.1)
        self.cutz_entry.setWrapping(True)

        grid0.addWidget(cutzlabel, 6, 0)
        grid0.addWidget(self.cutz_entry, 6, 1)

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
        grid0.addWidget(self.multidepth_cb, 8, 0)

        # Depth/pass
        self.depthperpass_entry = FCDoubleSpinner()
        self.depthperpass_entry.setToolTip(
            _("Depth of each pass (positive).")
        )
        self.depthperpass_entry.set_range(0, 99999)
        self.depthperpass_entry.set_precision(self.decimals)
        self.depthperpass_entry.setSingleStep(0.1)
        self.depthperpass_entry.setWrapping(True)

        grid0.addWidget(self.depthperpass_entry, 8, 1)

        self.ois_multidepth = OptionalInputSection(self.multidepth_cb, [self.depthperpass_entry])

        # Travel Z
        travelzlabel = FCLabel('%s:' % _('Travel Z'))
        travelzlabel.setToolTip(
            _("Height of the tool when\n"
              "moving without cutting.")
        )
        self.travelz_entry = FCDoubleSpinner()
        self.travelz_entry.set_range(-10000.0000, 10000.0000)

        self.travelz_entry.set_precision(self.decimals)
        self.travelz_entry.setSingleStep(0.1)
        self.travelz_entry.setWrapping(True)

        grid0.addWidget(travelzlabel, 10, 0)
        grid0.addWidget(self.travelz_entry, 10, 1)

        # Tool change:
        self.toolchange_cb = FCCheckBox('%s' % _("Tool change"))
        self.toolchange_cb.setToolTip(
            _(
                "Include tool-change sequence\n"
                "in the Machine Code (Pause for tool change)."
            )
        )
        grid0.addWidget(self.toolchange_cb, 12, 0, 1, 2)

        # Toolchange Z
        toolchangezlabel = FCLabel('%s:' % _('Toolchange Z'))
        toolchangezlabel.setToolTip(
            _(
                "Z-axis position (height) for\n"
                "tool change."
            )
        )
        self.toolchangez_entry = FCDoubleSpinner()
        self.toolchangez_entry.set_range(-10000.0000, 10000.0000)

        self.toolchangez_entry.set_precision(self.decimals)
        self.toolchangez_entry.setSingleStep(0.1)
        self.toolchangez_entry.setWrapping(True)

        grid0.addWidget(toolchangezlabel, 14, 0)
        grid0.addWidget(self.toolchangez_entry, 14, 1)

        # End move Z
        endz_label = FCLabel('%s:' % _('End move Z'))
        endz_label.setToolTip(
            _("Height of the tool after\n"
              "the last move at the end of the job.")
        )
        self.endz_entry = FCDoubleSpinner()
        self.endz_entry.set_range(-10000.0000, 10000.0000)

        self.endz_entry.set_precision(self.decimals)
        self.endz_entry.setSingleStep(0.1)
        self.endz_entry.setWrapping(True)

        grid0.addWidget(endz_label, 16, 0)
        grid0.addWidget(self.endz_entry, 16, 1)

        # End Move X,Y
        endmove_xy_label = FCLabel('%s:' % _('End move X,Y'))
        endmove_xy_label.setToolTip(
            _("End move X,Y position. In format (x,y).\n"
              "If no value is entered then there is no move\n"
              "on X,Y plane at the end of the job.")
        )
        self.endxy_entry = NumericalEvalTupleEntry(border_color='#0069A9')

        grid0.addWidget(endmove_xy_label, 18, 0)
        grid0.addWidget(self.endxy_entry, 18, 1)

        # Feedrate X-Y
        frlabel = FCLabel('%s:' % _('Feedrate X-Y'))
        frlabel.setToolTip(
            _("Cutting speed in the XY\n"
              "plane in units per minute")
        )
        self.cncfeedrate_entry = FCDoubleSpinner()
        self.cncfeedrate_entry.set_range(0, 910000.0000)
        self.cncfeedrate_entry.set_precision(self.decimals)
        self.cncfeedrate_entry.setSingleStep(0.1)
        self.cncfeedrate_entry.setWrapping(True)

        grid0.addWidget(frlabel, 20, 0)
        grid0.addWidget(self.cncfeedrate_entry, 20, 1)

        # Feedrate Z (Plunge)
        frz_label = FCLabel('%s:' % _('Feedrate Z'))
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

        grid0.addWidget(frz_label, 22, 0)
        grid0.addWidget(self.feedrate_z_entry, 22, 1)

        # Spindle Speed
        spdlabel = FCLabel('%s:' % _('Spindle speed'))
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

        grid0.addWidget(spdlabel, 24, 0)
        grid0.addWidget(self.cncspindlespeed_entry, 24, 1)

        # Dwell
        self.dwell_cb = FCCheckBox(label='%s' % _('Enable Dwell'))
        self.dwell_cb.setToolTip(
            _("Pause to allow the spindle to reach its\n"
              "speed before cutting.")
        )

        self.dwelltime_entry = FCDoubleSpinner()
        self.dwelltime_entry.setToolTip(
            _("Number of time units for spindle to dwell.")
        )
        self.dwelltime_entry.set_range(0, 99999)
        self.dwelltime_entry.set_precision(self.decimals)
        self.dwelltime_entry.setSingleStep(0.1)
        self.dwelltime_entry.setWrapping(True)

        grid0.addWidget(self.dwell_cb, 26, 0)
        grid0.addWidget(self.dwelltime_entry, 26, 1)

        self.ois_dwell = OptionalInputSection(self.dwell_cb, [self.dwelltime_entry])

        # preprocessor selection
        pp_label = FCLabel('%s:' % _("Preprocessor"))
        pp_label.setToolTip(
            _("The Preprocessor file that dictates\n"
              "the Machine Code (like GCode, RML, HPGL) output.")
        )
        self.pp_geometry_name_cb = FCComboBox()
        self.pp_geometry_name_cb.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.pp_geometry_name_cb.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                               QtWidgets.QSizePolicy.Policy.Preferred)
        self.pp_geometry_name_cb.addItems(self.defaults["tools_mill_preprocessor_list"])


        for it in range(self.pp_geometry_name_cb.count()):
            self.pp_geometry_name_cb.setItemData(it, self.pp_geometry_name_cb.itemText(it),
                                                 QtCore.Qt.ItemDataRole.ToolTipRole)

        grid0.addWidget(pp_label, 28, 0)
        grid0.addWidget(self.pp_geometry_name_cb, 28, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        grid0.addWidget(separator_line, 30, 0, 1, 2)

        # Toolchange X,Y
        toolchange_xy_label = FCLabel('%s:' % _('Toolchange X-Y'))
        toolchange_xy_label.setToolTip(
            _("Toolchange X,Y position.")
        )
        self.toolchangexy_entry = NumericalEvalTupleEntry(border_color='#0069A9')

        grid0.addWidget(toolchange_xy_label, 32, 0)
        grid0.addWidget(self.toolchangexy_entry, 32, 1)

        # Start move Z
        startzlabel = FCLabel('%s:' % _('Start Z'))
        startzlabel.setToolTip(
            _("Height of the tool just after starting the work.\n"
              "Delete the value if you don't need this feature.")
        )
        self.gstartz_entry = NumericalEvalEntry(border_color='#0069A9')

        grid0.addWidget(startzlabel, 34, 0)
        grid0.addWidget(self.gstartz_entry, 34, 1)

        # Feedrate rapids
        fr_rapid_label = FCLabel('%s:' % _('Feedrate Rapids'))
        fr_rapid_label.setToolTip(
            _("Cutting speed in the XY plane\n"
              "(in units per minute).\n"
              "This is for the rapid move G00.\n"
              "It is useful only for Marlin,\n"
              "ignore for any other cases.")
        )
        self.feedrate_rapid_entry = FCDoubleSpinner()
        self.feedrate_rapid_entry.set_range(0, 910000.0000)
        self.feedrate_rapid_entry.set_precision(self.decimals)
        self.feedrate_rapid_entry.setSingleStep(0.1)
        self.feedrate_rapid_entry.setWrapping(True)

        grid0.addWidget(fr_rapid_label, 36, 0)
        grid0.addWidget(self.feedrate_rapid_entry, 36, 1)

        # End move extra cut
        self.extracut_cb = FCCheckBox('%s' % _('Re-cut'))
        self.extracut_cb.setToolTip(
            _("In order to remove possible\n"
              "copper leftovers where first cut\n"
              "meet with last cut, we generate an\n"
              "extended cut over the first cut section.")
        )

        self.e_cut_entry = FCDoubleSpinner()
        self.e_cut_entry.set_range(0, 99999)
        self.e_cut_entry.set_precision(self.decimals)
        self.e_cut_entry.setSingleStep(0.1)
        self.e_cut_entry.setWrapping(True)
        self.e_cut_entry.setToolTip(
            _("In order to remove possible\n"
              "copper leftovers where first cut\n"
              "meet with last cut, we generate an\n"
              "extended cut over the first cut section.")
        )
        grid0.addWidget(self.extracut_cb, 38, 0)
        grid0.addWidget(self.e_cut_entry, 38, 1)

        # Probe depth
        self.pdepth_label = FCLabel('%s:' % _("Probe Z depth"))
        self.pdepth_label.setToolTip(
            _("The maximum depth that the probe is allowed\n"
              "to probe. Negative value, in current units.")
        )
        self.pdepth_entry = FCDoubleSpinner()
        self.pdepth_entry.set_range(-99999, 0.0000)
        self.pdepth_entry.set_precision(self.decimals)
        self.pdepth_entry.setSingleStep(0.1)
        self.pdepth_entry.setWrapping(True)

        grid0.addWidget(self.pdepth_label, 40, 0)
        grid0.addWidget(self.pdepth_entry, 40, 1)

        # Probe feedrate
        self.feedrate_probe_label = FCLabel('%s:' % _("Feedrate Probe"))
        self.feedrate_probe_label.setToolTip(
            _("The feedrate used while the probe is probing.")
        )
        self.feedrate_probe_entry = FCDoubleSpinner()
        self.feedrate_probe_entry.set_range(0, 910000.0000)
        self.feedrate_probe_entry.set_precision(self.decimals)
        self.feedrate_probe_entry.setSingleStep(0.1)
        self.feedrate_probe_entry.setWrapping(True)

        grid0.addWidget(self.feedrate_probe_label, 42, 0)
        grid0.addWidget(self.feedrate_probe_entry, 42, 1)

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
        grid0.addWidget(spindle_dir_label, 44, 0)
        grid0.addWidget(self.spindledir_radio, 44, 1)

        # Fast Move from Z Toolchange
        self.fplunge_cb = FCCheckBox('%s' % _('Fast Plunge'))
        self.fplunge_cb.setToolTip(
            _("By checking this, the vertical move from\n"
              "Z_Toolchange to Z_move is done with G0,\n"
              "meaning the fastest speed available.\n"
              "WARNING: the move is done at Toolchange X,Y coords.")
        )
        grid0.addWidget(self.fplunge_cb, 46, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        grid0.addWidget(separator_line, 48, 0, 1, 2)

        # -----------------------------
        # --- Area Exclusion ----------
        # -----------------------------
        self.area_exc_label = FCLabel('<b>%s:</b>' % _('Area Exclusion'))
        self.area_exc_label.setToolTip(
            _("Area exclusion parameters.")
        )
        grid0.addWidget(self.area_exc_label, 52, 0, 1, 2)

        # Exclusion Area CB
        self.exclusion_cb = FCCheckBox('%s' % _("Exclusion areas"))
        self.exclusion_cb.setToolTip(
            _(
                "Include exclusion areas.\n"
                "In those areas the travel of the tools\n"
                "is forbidden."
            )
        )
        grid0.addWidget(self.exclusion_cb, 54, 0, 1, 2)

        # Area Selection shape
        self.area_shape_label = FCLabel('%s:' % _("Shape"))
        self.area_shape_label.setToolTip(
            _("The kind of selection shape used for area selection.")
        )

        self.area_shape_radio = RadioSet([{'label': _("Square"), 'value': 'square'},
                                          {'label': _("Polygon"), 'value': 'polygon'}])

        grid0.addWidget(self.area_shape_label, 56, 0)
        grid0.addWidget(self.area_shape_radio, 56, 1)

        # Chose Strategy
        self.strategy_label = FCLabel('%s:' % _("Strategy"))
        self.strategy_label.setToolTip(_("The strategy followed when encountering an exclusion area.\n"
                                         "Can be:\n"
                                         "- Over -> when encountering the area, the tool will go to a set height\n"
                                         "- Around -> will avoid the exclusion area by going around the area"))
        self.strategy_radio = RadioSet([{'label': _('Over'), 'value': 'over'},
                                        {'label': _('Around'), 'value': 'around'}])

        grid0.addWidget(self.strategy_label, 58, 0)
        grid0.addWidget(self.strategy_radio, 58, 1)

        # Over Z
        self.over_z_label = FCLabel('%s:' % _("Over Z"))
        self.over_z_label.setToolTip(_("The height Z to which the tool will rise in order to avoid\n"
                                       "an interdiction area."))
        self.over_z_entry = FCDoubleSpinner()
        self.over_z_entry.set_range(-10000.000, 10000.0000)
        self.over_z_entry.set_precision(self.decimals)

        grid0.addWidget(self.over_z_label, 60, 0)
        grid0.addWidget(self.over_z_entry, 60, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        grid0.addWidget(separator_line, 62, 0, 1, 2)

        # -----------------------------
        # --- Area POLISH ----------
        # -----------------------------

        self.pol_label = FCLabel('<b>%s:</b>' % _('Add Polish'))
        self.pol_label.setToolTip(
            _("Will add a Paint section at the end of the GCode.\n"
              "A metallic brush will clean the material after milling.")
        )
        grid0.addWidget(self.pol_label, 70, 0, 1, 2)

        # Polish Margin
        self.polish_margin_lbl = FCLabel('%s:' % _('Margin'))
        self.polish_margin_lbl.setToolTip(
            _("Bounding box margin.")
        )
        self.polish_margin_entry = FCDoubleSpinner()
        self.polish_margin_entry.set_precision(self.decimals)
        self.polish_margin_entry.set_range(-10000.0000, 10000.0000)

        grid0.addWidget(self.polish_margin_lbl, 72, 0)
        grid0.addWidget(self.polish_margin_entry, 72, 1)

        # Polish Overlap
        self.polish_over_lbl = FCLabel('%s:' % _('Overlap'))
        self.polish_over_lbl.setToolTip(
            _("How much (percentage) of the tool width to overlap each tool pass.")
        )
        self.polish_over_entry = FCDoubleSpinner(suffix='%')
        self.polish_over_entry.set_precision(self.decimals)
        self.polish_over_entry.setWrapping(True)
        self.polish_over_entry.set_range(0.0000, 99.9999)
        self.polish_over_entry.setSingleStep(0.1)

        grid0.addWidget(self.polish_over_lbl, 74, 0)
        grid0.addWidget(self.polish_over_entry, 74, 1)

        # Polish Method
        self.polish_method_lbl = FCLabel('%s:' % _('Method'))
        self.polish_method_lbl.setToolTip(
            _("Algorithm for polishing:\n"
              "- Standard: Fixed step inwards.\n"
              "- Seed-based: Outwards from seed.\n"
              "- Line-based: Parallel lines.")
        )

        self.polish_method_combo = FCComboBox2()
        self.polish_method_combo.addItems(
            [_("Standard"), _("Seed"), _("Lines")]
        )

        grid0.addWidget(self.polish_method_lbl, 76, 0)
        grid0.addWidget(self.polish_method_combo, 76, 1)

        self.layout.addStretch()
