from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings

from appGUI.GUIElements import FCDoubleSpinner, FCCheckBox, RadioSet, FCLabel, NumericalEvalTupleEntry, \
    NumericalEvalEntry, FCComboBox2
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


class GeometryAdvOptPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "Geometry Advanced Options Preferences", parent=parent)
        super(GeometryAdvOptPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Geometry Adv. Options")))
        self.decimals = decimals

        # ------------------------------
        # ## Advanced Options
        # ------------------------------
        self.geo_label = FCLabel('<b>%s:</b>' % _('Advanced Options'))
        self.geo_label.setToolTip(
            _("A list of advanced parameters.\n"
              "Those parameters are available only for\n"
              "Advanced App. Level.")
        )
        self.layout.addWidget(self.geo_label)

        grid1 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid1)

        # Toolchange X,Y
        toolchange_xy_label = FCLabel('%s:' % _('Toolchange X-Y'))
        toolchange_xy_label.setToolTip(
            _("Toolchange X,Y position.")
        )
        self.toolchangexy_entry = NumericalEvalTupleEntry(border_color='#0069A9')

        grid1.addWidget(toolchange_xy_label, 1, 0)
        grid1.addWidget(self.toolchangexy_entry, 1, 1)

        # Start move Z
        startzlabel = FCLabel('%s:' % _('Start Z'))
        startzlabel.setToolTip(
            _("Height of the tool just after starting the work.\n"
              "Delete the value if you don't need this feature.")
        )
        self.gstartz_entry = NumericalEvalEntry(border_color='#0069A9')

        grid1.addWidget(startzlabel, 2, 0)
        grid1.addWidget(self.gstartz_entry, 2, 1)

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

        grid1.addWidget(fr_rapid_label, 4, 0)
        grid1.addWidget(self.feedrate_rapid_entry, 4, 1)

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
        grid1.addWidget(self.extracut_cb, 5, 0)
        grid1.addWidget(self.e_cut_entry, 5, 1)

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

        grid1.addWidget(self.pdepth_label, 6, 0)
        grid1.addWidget(self.pdepth_entry, 6, 1)

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

        grid1.addWidget(self.feedrate_probe_label, 7, 0)
        grid1.addWidget(self.feedrate_probe_entry, 7, 1)

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
        grid1.addWidget(spindle_dir_label, 8, 0)
        grid1.addWidget(self.spindledir_radio, 8, 1)

        # Fast Move from Z Toolchange
        self.fplunge_cb = FCCheckBox('%s' % _('Fast Plunge'))
        self.fplunge_cb.setToolTip(
            _("By checking this, the vertical move from\n"
              "Z_Toolchange to Z_move is done with G0,\n"
              "meaning the fastest speed available.\n"
              "WARNING: the move is done at Toolchange X,Y coords.")
        )
        grid1.addWidget(self.fplunge_cb, 9, 0, 1, 2)

        # Size of trace segment on X axis
        segx_label = FCLabel('%s:' % _("Segment X size"))
        segx_label.setToolTip(
            _("The size of the trace segment on the X axis.\n"
              "Useful for auto-leveling.\n"
              "A value of 0 means no segmentation on the X axis.")
        )
        self.segx_entry = FCDoubleSpinner()
        self.segx_entry.set_range(0, 99999)
        self.segx_entry.set_precision(self.decimals)
        self.segx_entry.setSingleStep(0.1)
        self.segx_entry.setWrapping(True)

        grid1.addWidget(segx_label, 10, 0)
        grid1.addWidget(self.segx_entry, 10, 1)

        # Size of trace segment on Y axis
        segy_label = FCLabel('%s:' % _("Segment Y size"))
        segy_label.setToolTip(
            _("The size of the trace segment on the Y axis.\n"
              "Useful for auto-leveling.\n"
              "A value of 0 means no segmentation on the Y axis.")
        )
        self.segy_entry = FCDoubleSpinner()
        self.segy_entry.set_range(0, 99999)
        self.segy_entry.set_precision(self.decimals)
        self.segy_entry.setSingleStep(0.1)
        self.segy_entry.setWrapping(True)

        grid1.addWidget(segy_label, 11, 0)
        grid1.addWidget(self.segy_entry, 11, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid1.addWidget(separator_line, 12, 0, 1, 2)

        # -----------------------------
        # --- Area Exclusion ----------
        # -----------------------------
        self.area_exc_label = FCLabel('<b>%s:</b>' % _('Area Exclusion'))
        self.area_exc_label.setToolTip(
            _("Area exclusion parameters.")
        )
        grid1.addWidget(self.area_exc_label, 13, 0, 1, 2)

        # Exclusion Area CB
        self.exclusion_cb = FCCheckBox('%s' % _("Exclusion areas"))
        self.exclusion_cb.setToolTip(
            _(
                "Include exclusion areas.\n"
                "In those areas the travel of the tools\n"
                "is forbidden."
            )
        )
        grid1.addWidget(self.exclusion_cb, 14, 0, 1, 2)

        # Area Selection shape
        self.area_shape_label = FCLabel('%s:' % _("Shape"))
        self.area_shape_label.setToolTip(
            _("The kind of selection shape used for area selection.")
        )

        self.area_shape_radio = RadioSet([{'label': _("Square"), 'value': 'square'},
                                          {'label': _("Polygon"), 'value': 'polygon'}])

        grid1.addWidget(self.area_shape_label, 15, 0)
        grid1.addWidget(self.area_shape_radio, 15, 1)

        # Chose Strategy
        self.strategy_label = FCLabel('%s:' % _("Strategy"))
        self.strategy_label.setToolTip(_("The strategy followed when encountering an exclusion area.\n"
                                         "Can be:\n"
                                         "- Over -> when encountering the area, the tool will go to a set height\n"
                                         "- Around -> will avoid the exclusion area by going around the area"))
        self.strategy_radio = RadioSet([{'label': _('Over'), 'value': 'over'},
                                        {'label': _('Around'), 'value': 'around'}])

        grid1.addWidget(self.strategy_label, 16, 0)
        grid1.addWidget(self.strategy_radio, 16, 1)

        # Over Z
        self.over_z_label = FCLabel('%s:' % _("Over Z"))
        self.over_z_label.setToolTip(_("The height Z to which the tool will rise in order to avoid\n"
                                       "an interdiction area."))
        self.over_z_entry = FCDoubleSpinner()
        self.over_z_entry.set_range(0.000, 10000.0000)
        self.over_z_entry.set_precision(self.decimals)

        grid1.addWidget(self.over_z_label, 18, 0)
        grid1.addWidget(self.over_z_entry, 18, 1)
        
        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid1.addWidget(separator_line, 20, 0, 1, 2)
        
        # -----------------------------
        # --- Area POLISH ----------
        # -----------------------------
        # Add Polish
        self.polish_cb = FCCheckBox(label=_('Add Polish'))
        self.polish_cb.setToolTip(_(
            "Will add a Paint section at the end of the GCode.\n"
            "A metallic brush will clean the material after milling."))
        grid1.addWidget(self.polish_cb, 22, 0, 1, 2)

        # Polish Tool Diameter
        self.polish_dia_lbl = FCLabel('%s:' % _('Tool Dia'))
        self.polish_dia_lbl.setToolTip(
            _("Diameter for the polishing tool.")
        )
        self.polish_dia_entry = FCDoubleSpinner()
        self.polish_dia_entry.set_precision(self.decimals)
        self.polish_dia_entry.set_range(0.000, 10000.0000)

        grid1.addWidget(self.polish_dia_lbl, 24, 0)
        grid1.addWidget(self.polish_dia_entry, 24, 1)

        # Polish Travel Z
        self.polish_travelz_lbl = FCLabel('%s:' % _('Travel Z'))
        self.polish_travelz_lbl.setToolTip(
            _("Height of the tool when\n"
              "moving without cutting.")
        )
        self.polish_travelz_entry = FCDoubleSpinner()
        self.polish_travelz_entry.set_precision(self.decimals)
        self.polish_travelz_entry.set_range(0.00000, 10000.00000)
        self.polish_travelz_entry.setSingleStep(0.1)

        grid1.addWidget(self.polish_travelz_lbl, 26, 0)
        grid1.addWidget(self.polish_travelz_entry, 26, 1)

        # Polish Pressure
        self.polish_pressure_lbl = FCLabel('%s:' % _('Pressure'))
        self.polish_pressure_lbl.setToolTip(
            _("Negative value. The higher the absolute value\n"
              "the stronger the pressure of the brush on the material.")
        )
        self.polish_pressure_entry = FCDoubleSpinner()
        self.polish_pressure_entry.set_precision(self.decimals)
        self.polish_pressure_entry.set_range(-10000.0000, 10000.0000)

        grid1.addWidget(self.polish_pressure_lbl, 28, 0)
        grid1.addWidget(self.polish_pressure_entry, 28, 1)

        # Polish Margin
        self.polish_margin_lbl = FCLabel('%s:' % _('Margin'))
        self.polish_margin_lbl.setToolTip(
            _("Bounding box margin.")
        )
        self.polish_margin_entry = FCDoubleSpinner()
        self.polish_margin_entry.set_precision(self.decimals)
        self.polish_margin_entry.set_range(-10000.0000, 10000.0000)

        grid1.addWidget(self.polish_margin_lbl, 30, 0)
        grid1.addWidget(self.polish_margin_entry, 30, 1)

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

        grid1.addWidget(self.polish_over_lbl, 32, 0)
        grid1.addWidget(self.polish_over_entry, 32, 1)

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

        grid1.addWidget(self.polish_method_lbl, 34, 0)
        grid1.addWidget(self.polish_method_combo, 34, 1)

        self.layout.addStretch()
