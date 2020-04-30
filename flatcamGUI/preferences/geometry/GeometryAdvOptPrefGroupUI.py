from PyQt5 import QtWidgets

from flatcamGUI.GUIElements import FCEntry, FloatEntry, FCDoubleSpinner, FCCheckBox, RadioSet
from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI


class GeometryAdvOptPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "Geometry Advanced Options Preferences", parent=parent)
        super(GeometryAdvOptPrefGroupUI, self).__init__(self)

        self.setTitle(str(_("Geometry Adv. Options")))
        self.decimals = decimals

        # ------------------------------
        # ## Advanced Options
        # ------------------------------
        self.geo_label = QtWidgets.QLabel('<b>%s:</b>' % _('Advanced Options'))
        self.geo_label.setToolTip(
            _("A list of Geometry advanced parameters.\n"
              "Those parameters are available only for\n"
              "Advanced App. Level.")
        )
        self.layout.addWidget(self.geo_label)

        grid1 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid1)

        # Toolchange X,Y
        toolchange_xy_label = QtWidgets.QLabel('%s:' % _('Toolchange X-Y'))
        toolchange_xy_label.setToolTip(
            _("Toolchange X,Y position.")
        )
        grid1.addWidget(toolchange_xy_label, 1, 0)
        self.toolchangexy_entry = FCEntry()
        grid1.addWidget(self.toolchangexy_entry, 1, 1)

        # Start move Z
        startzlabel = QtWidgets.QLabel('%s:' % _('Start Z'))
        startzlabel.setToolTip(
            _("Height of the tool just after starting the work.\n"
              "Delete the value if you don't need this feature.")
        )
        grid1.addWidget(startzlabel, 2, 0)
        self.gstartz_entry = FloatEntry()
        grid1.addWidget(self.gstartz_entry, 2, 1)

        # Feedrate rapids
        fr_rapid_label = QtWidgets.QLabel('%s:' % _('Feedrate Rapids'))
        fr_rapid_label.setToolTip(
            _("Cutting speed in the XY plane\n"
              "(in units per minute).\n"
              "This is for the rapid move G00.\n"
              "It is useful only for Marlin,\n"
              "ignore for any other cases.")
        )
        self.feedrate_rapid_entry = FCDoubleSpinner()
        self.feedrate_rapid_entry.set_range(0, 99999.9999)
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
        self.pdepth_label = QtWidgets.QLabel('%s:' % _("Probe Z depth"))
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
        self.feedrate_probe_label = QtWidgets.QLabel('%s:' % _("Feedrate Probe"))
        self.feedrate_probe_label.setToolTip(
            _("The feedrate used while the probe is probing.")
        )
        self.feedrate_probe_entry = FCDoubleSpinner()
        self.feedrate_probe_entry.set_range(0, 99999.9999)
        self.feedrate_probe_entry.set_precision(self.decimals)
        self.feedrate_probe_entry.setSingleStep(0.1)
        self.feedrate_probe_entry.setWrapping(True)

        grid1.addWidget(self.feedrate_probe_label, 7, 0)
        grid1.addWidget(self.feedrate_probe_entry, 7, 1)

        # Spindle direction
        spindle_dir_label = QtWidgets.QLabel('%s:' % _('Spindle direction'))
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
        segx_label = QtWidgets.QLabel('%s:' % _("Segment X size"))
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
        segy_label = QtWidgets.QLabel('%s:' % _("Segment Y size"))
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

        self.layout.addStretch()