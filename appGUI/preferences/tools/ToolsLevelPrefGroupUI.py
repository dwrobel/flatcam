from PyQt5 import QtWidgets

from appGUI.GUIElements import FCDoubleSpinner, FCSpinner, RadioSet, FCLabel, FCComboBox
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ToolsLevelPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "Cutout Tool Options", parent=parent)
        super(ToolsLevelPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Levelling Tool Options")))
        self.decimals = decimals

        # ## Board cuttout
        self.levelling_label = FCLabel("<b>%s:</b>" % _("Parameters"))
        self.levelling_label.setToolTip(
            _("Generate CNC Code with auto-levelled paths.")
        )
        self.layout.addWidget(self.levelling_label)

        # Grid Layout
        grid0 = QtWidgets.QGridLayout()
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        self.layout.addLayout(grid0)

        # Probe points mode
        al_mode_lbl = FCLabel('%s:' % _("Mode"))
        al_mode_lbl.setToolTip(_("Choose a mode for height map generation.\n"
                                 "- Manual: will pick a selection of probe points by clicking on canvas\n"
                                 "- Grid: will automatically generate a grid of probe points"))

        self.al_mode_radio = RadioSet(
            [
                {'label': _('Manual'), 'value': 'manual'},
                {'label': _('Grid'), 'value': 'grid'}
            ])
        grid0.addWidget(al_mode_lbl, 8, 0)
        grid0.addWidget(self.al_mode_radio, 8, 1)

        # AUTOLEVELL METHOD
        self.al_method_lbl = FCLabel('%s:' % _("Method"))
        self.al_method_lbl.setToolTip(_("Choose a method for approximation of heights from autolevelling data.\n"
                                        "- Voronoi: will generate a Voronoi diagram\n"
                                        "- Bilinear: will use bilinear interpolation. Usable only for grid mode."))

        self.al_method_radio = RadioSet(
            [
                {'label': _('Voronoi'), 'value': 'v'},
                {'label': _('Bilinear'), 'value': 'b'}
            ])
        grid0.addWidget(self.al_method_lbl, 9, 0)
        grid0.addWidget(self.al_method_radio, 9, 1)

        # ## Columns
        self.al_columns_entry = FCSpinner()

        self.al_columns_label = FCLabel('%s:' % _("Columns"))
        self.al_columns_label.setToolTip(
            _("The number of grid columns.")
        )
        grid0.addWidget(self.al_columns_label, 10, 0)
        grid0.addWidget(self.al_columns_entry, 10, 1)

        # ## Rows
        self.al_rows_entry = FCSpinner()

        self.al_rows_label = FCLabel('%s:' % _("Rows"))
        self.al_rows_label.setToolTip(
            _("The number of grid rows.")
        )
        grid0.addWidget(self.al_rows_label, 12, 0)
        grid0.addWidget(self.al_rows_entry, 12, 1)

        # Travel Z Probe
        self.ptravelz_label = FCLabel('%s:' % _("Probe Z travel"))
        self.ptravelz_label.setToolTip(
            _("The safe Z for probe travelling between probe points.")
        )
        self.ptravelz_entry = FCDoubleSpinner()
        self.ptravelz_entry.set_precision(self.decimals)
        self.ptravelz_entry.set_range(0.0000, 10000.0000)

        grid0.addWidget(self.ptravelz_label, 14, 0)
        grid0.addWidget(self.ptravelz_entry, 14, 1)

        # Probe depth
        self.pdepth_label = FCLabel('%s:' % _("Probe Z depth"))
        self.pdepth_label.setToolTip(
            _("The maximum depth that the probe is allowed\n"
              "to probe. Negative value, in current units.")
        )
        self.pdepth_entry = FCDoubleSpinner()
        self.pdepth_entry.set_precision(self.decimals)
        self.pdepth_entry.set_range(-910000.0000, 0.0000)

        grid0.addWidget(self.pdepth_label, 16, 0)
        grid0.addWidget(self.pdepth_entry, 16, 1)

        # Probe feedrate
        self.feedrate_probe_label = FCLabel('%s:' % _("Probe Feedrate"))
        self.feedrate_probe_label.setToolTip(
            _("The feedrate used while the probe is probing.")
        )
        self.feedrate_probe_entry = FCDoubleSpinner()
        self.feedrate_probe_entry.set_precision(self.decimals)
        self.feedrate_probe_entry.set_range(0, 910000.0000)

        grid0.addWidget(self.feedrate_probe_label, 18, 0)
        grid0.addWidget(self.feedrate_probe_entry, 18, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 20, 0, 1, 2)

        self.al_controller_label = FCLabel('%s:' % _("Controller"))
        self.al_controller_label.setToolTip(
            _("The kind of controller for which to generate\n"
              "height map gcode.")
        )

        self.al_controller_combo = FCComboBox()
        self.al_controller_combo.addItems(["MACH3", "MACH4", "LinuxCNC", "GRBL"])
        grid0.addWidget(self.al_controller_label, 22, 0)
        grid0.addWidget(self.al_controller_combo, 22, 1)

        # JOG Step
        self.jog_step_label = FCLabel('%s:' % _("Step"))
        self.jog_step_label.setToolTip(
            _("Each jog action will move the axes with this value.")
        )

        self.jog_step_entry = FCDoubleSpinner()
        self.jog_step_entry.set_precision(self.decimals)
        self.jog_step_entry.set_range(0, 910000.0000)

        grid0.addWidget(self.jog_step_label, 24, 0)
        grid0.addWidget(self.jog_step_entry, 24, 1)

        # JOG Feedrate
        self.jog_fr_label = FCLabel('%s:' % _("Feedrate"))
        self.jog_fr_label.setToolTip(
            _("Feedrate when jogging.")
        )

        self.jog_fr_entry = FCDoubleSpinner()
        self.jog_fr_entry.set_precision(self.decimals)
        self.jog_fr_entry.set_range(0, 910000.0000)

        grid0.addWidget(self.jog_fr_label, 26, 0)
        grid0.addWidget(self.jog_fr_entry, 26, 1)

        # JOG Travel Z
        self.jog_travelz_label = FCLabel('%s:' % _("Travel Z"))
        self.jog_travelz_label.setToolTip(
            _("Safe height (Z) distance when jogging to origin.")
        )

        self.jog_travelz_entry = FCDoubleSpinner()
        self.jog_travelz_entry.set_precision(self.decimals)
        self.jog_travelz_entry.set_range(0, 910000.0000)

        grid0.addWidget(self.jog_travelz_label, 28, 0)
        grid0.addWidget(self.jog_travelz_entry, 28, 1)

        self.layout.addStretch(1)
