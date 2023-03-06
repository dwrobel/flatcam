
from PyQt6 import QtCore

from appGUI.GUIElements import FCDoubleSpinner, FCSpinner, FCComboBox, NumericalEvalTupleEntry, FCLabel, GLay, \
    FCFrame
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ToolsSolderpastePrefGroupUI(OptionsGroupUI):
    def __init__(self, app, parent=None):

        super(ToolsSolderpastePrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("SolderPaste Plugin")))
        self.decimals = app.decimals
        self.options = app.options

        # #############################################################################################################
        # PARAMETERS Frame
        # #############################################################################################################
        self.solderpastelabel = FCLabel('%s' % _("Parameters"), color='blue', bold=True)
        self.solderpastelabel.setToolTip(
            _("A tool to create GCode for dispensing\n"
              "solder paste onto a PCB.")
        )
        self.layout.addWidget(self.solderpastelabel)

        param_frame = FCFrame()
        self.layout.addWidget(param_frame)

        param_grid = GLay(v_spacing=5, h_spacing=3)
        param_frame.setLayout(param_grid)

        # Nozzle Tool Diameters
        nozzletdlabel = FCLabel('%s:' % _('Tools Dia'), color='green', bold=True)
        nozzletdlabel.setToolTip(
            _("Diameters of the tools, separated by comma.\n"
              "The value of the diameter has to use the dot decimals separator.\n"
              "Valid values: 0.3, 1.0")
        )
        self.nozzle_tool_dia_entry = NumericalEvalTupleEntry(border_color='#0069A9')

        param_grid.addWidget(nozzletdlabel, 0, 0)
        param_grid.addWidget(self.nozzle_tool_dia_entry, 0, 1)

        # New Nozzle Tool Dia
        self.addtool_entry_lbl = FCLabel('%s:' % _('New Nozzle Dia'), bold=True)
        self.addtool_entry_lbl.setToolTip(
            _("Diameter for the new tool to add in the Tool Table")
        )
        self.addtool_entry = FCDoubleSpinner()
        self.addtool_entry.set_precision(self.decimals)
        self.addtool_entry.set_range(0.0000001, 10000.0000)
        self.addtool_entry.setSingleStep(0.1)

        param_grid.addWidget(self.addtool_entry_lbl, 2, 0)
        param_grid.addWidget(self.addtool_entry, 2, 1)

        # Margin
        self.margin_label = FCLabel('%s:' % _("Margin"))
        self.margin_label.setToolTip('%s %s' % (
            _("Offset from the boundary."),
            _("Fraction of tool diameter.")
        )
                                     )
        self.margin_entry = FCDoubleSpinner(suffix='%')
        self.margin_entry.set_range(-100.0000, 100.0000)
        self.margin_entry.set_precision(self.decimals)
        self.margin_entry.setSingleStep(0.1)

        param_grid.addWidget(self.margin_label, 4, 0)
        param_grid.addWidget(self.margin_entry, 4, 1)

        # Z dispense start
        self.z_start_entry = FCDoubleSpinner()
        self.z_start_entry.set_precision(self.decimals)
        self.z_start_entry.set_range(0.0000001, 10000.0000)
        self.z_start_entry.setSingleStep(0.1)

        self.z_start_label = FCLabel('%s:' % _("Z Dispense Start"))
        self.z_start_label.setToolTip(
            _("The height (Z) when solder paste dispensing starts.")
        )
        param_grid.addWidget(self.z_start_label, 6, 0)
        param_grid.addWidget(self.z_start_entry, 6, 1)

        # Z dispense
        self.z_dispense_entry = FCDoubleSpinner()
        self.z_dispense_entry.set_precision(self.decimals)
        self.z_dispense_entry.set_range(0.0000001, 10000.0000)
        self.z_dispense_entry.setSingleStep(0.1)

        self.z_dispense_label = FCLabel('%s:' % _("Z Dispense"))
        self.z_dispense_label.setToolTip(
            _("The height (Z) when doing solder paste dispensing.")
        )
        param_grid.addWidget(self.z_dispense_label, 8, 0)
        param_grid.addWidget(self.z_dispense_entry, 8, 1)

        # Z dispense stop
        self.z_stop_entry = FCDoubleSpinner()
        self.z_stop_entry.set_precision(self.decimals)
        self.z_stop_entry.set_range(0.0000001, 10000.0000)
        self.z_stop_entry.setSingleStep(0.1)

        self.z_stop_label = FCLabel('%s:' % _("Z Dispense Stop"))
        self.z_stop_label.setToolTip(
            _("The height (Z) when solder paste dispensing stops.")
        )
        param_grid.addWidget(self.z_stop_label, 10, 0)
        param_grid.addWidget(self.z_stop_entry, 10, 1)

        # Z travel
        self.z_travel_entry = FCDoubleSpinner()
        self.z_travel_entry.set_precision(self.decimals)
        self.z_travel_entry.set_range(0.0000001, 10000.0000)
        self.z_travel_entry.setSingleStep(0.1)

        self.z_travel_label = FCLabel('%s:' % _("Z Travel"))
        self.z_travel_label.setToolTip(
            _("The height (Z) for travel between pads\n"
              "(without dispensing solder paste).")
        )
        param_grid.addWidget(self.z_travel_label, 12, 0)
        param_grid.addWidget(self.z_travel_entry, 12, 1)

        # Z toolchange location
        self.z_toolchange_entry = FCDoubleSpinner()
        self.z_toolchange_entry.set_precision(self.decimals)
        self.z_toolchange_entry.set_range(0.0000001, 10000.0000)
        self.z_toolchange_entry.setSingleStep(0.1)

        self.z_toolchange_label = FCLabel('%s:' % _("Z Toolchange"))
        self.z_toolchange_label.setToolTip(
            _("The height (Z) for tool (nozzle) change.")
        )
        param_grid.addWidget(self.z_toolchange_label, 14, 0)
        param_grid.addWidget(self.z_toolchange_entry, 14, 1)

        # X,Y Toolchange location
        self.xy_toolchange_entry = NumericalEvalTupleEntry(border_color='#0069A9')
        self.xy_toolchange_label = FCLabel('%s:' % _("Toolchange X-Y"))
        self.xy_toolchange_label.setToolTip(
            _("The X,Y location for tool (nozzle) change.\n"
              "The format is (x, y) where x and y are real numbers.")
        )
        param_grid.addWidget(self.xy_toolchange_label, 16, 0)
        param_grid.addWidget(self.xy_toolchange_entry, 16, 1)

        # Feedrate X-Y
        self.frxy_entry = FCDoubleSpinner()
        self.frxy_entry.set_precision(self.decimals)
        self.frxy_entry.set_range(0.0000001, 910000.0000)
        self.frxy_entry.setSingleStep(0.1)

        self.frxy_label = FCLabel('%s:' % _("Feedrate X-Y"))
        self.frxy_label.setToolTip(
            _("Feedrate (speed) while moving on the X-Y plane.")
        )
        param_grid.addWidget(self.frxy_label, 18, 0)
        param_grid.addWidget(self.frxy_entry, 18, 1)

        # Feedrate Rapids
        self.frapids_lbl = FCLabel('%s:' % _("Feedrate Rapids"))
        self.frapids_lbl.setToolTip(
            _("Feedrate while moving as fast as possible.")
        )

        self.fr_rapids_entry = FCDoubleSpinner()
        self.fr_rapids_entry.set_range(0.0000, 10000.0000)
        self.fr_rapids_entry.set_precision(self.decimals)
        self.fr_rapids_entry.setSingleStep(0.1)

        param_grid.addWidget(self.frapids_lbl, 20, 0)
        param_grid.addWidget(self.fr_rapids_entry, 20, 1)

        # Feedrate Z
        self.frz_entry = FCDoubleSpinner()
        self.frz_entry.set_precision(self.decimals)
        self.frz_entry.set_range(0.0000001, 910000.0000)
        self.frz_entry.setSingleStep(0.1)

        self.frz_label = FCLabel('%s:' % _("Feedrate Z"))
        self.frz_label.setToolTip(
            _("Feedrate (speed) while moving vertically\n"
              "(on Z plane).")
        )
        param_grid.addWidget(self.frz_label, 22, 0)
        param_grid.addWidget(self.frz_entry, 22, 1)

        # Feedrate Z Dispense
        self.frz_dispense_entry = FCDoubleSpinner()
        self.frz_dispense_entry.set_precision(self.decimals)
        self.frz_dispense_entry.set_range(0.0000001, 910000.0000)
        self.frz_dispense_entry.setSingleStep(0.1)

        self.frz_dispense_label = FCLabel('%s:' % _("Feedrate Z Dispense"))
        self.frz_dispense_label.setToolTip(
            _("Feedrate (speed) while moving up vertically\n"
              "to Dispense position (on Z plane).")
        )
        param_grid.addWidget(self.frz_dispense_label, 24, 0)
        param_grid.addWidget(self.frz_dispense_entry, 24, 1)

        # Spindle Speed Forward
        self.speedfwd_entry = FCSpinner()
        self.speedfwd_entry.set_range(0, 99999)
        self.speedfwd_entry.set_step(1000)

        self.speedfwd_label = FCLabel('%s:' % _("Spindle Speed FWD"))
        self.speedfwd_label.setToolTip(
            _("The dispenser speed while pushing solder paste\n"
              "through the dispenser nozzle.")
        )
        param_grid.addWidget(self.speedfwd_label, 26, 0)
        param_grid.addWidget(self.speedfwd_entry, 26, 1)

        # Dwell Forward
        self.dwellfwd_entry = FCDoubleSpinner()
        self.dwellfwd_entry.set_precision(self.decimals)
        self.dwellfwd_entry.set_range(0.0000, 10000.0000)
        self.dwellfwd_entry.setSingleStep(0.1)

        self.dwellfwd_label = FCLabel('%s:' % _("Dwell FWD"))
        self.dwellfwd_label.setToolTip(
            _("Pause after solder dispensing.")
        )
        param_grid.addWidget(self.dwellfwd_label, 28, 0)
        param_grid.addWidget(self.dwellfwd_entry, 28, 1)

        # Spindle Speed Reverse
        self.speedrev_entry = FCSpinner()
        self.speedrev_entry.set_range(0, 1000000)
        self.speedrev_entry.set_step(1000)

        self.speedrev_label = FCLabel('%s:' % _("Spindle Speed REV"))
        self.speedrev_label.setToolTip(
            _("The dispenser speed while retracting solder paste\n"
              "through the dispenser nozzle.")
        )
        param_grid.addWidget(self.speedrev_label, 30, 0)
        param_grid.addWidget(self.speedrev_entry, 30, 1)

        # Dwell Reverse
        self.dwellrev_entry = FCDoubleSpinner()
        self.dwellrev_entry.set_precision(self.decimals)
        self.dwellrev_entry.set_range(0.0000, 10000.0000)
        self.dwellrev_entry.setSingleStep(0.1)

        self.dwellrev_label = FCLabel('%s:' % _("Dwell REV"))
        self.dwellrev_label.setToolTip(
            _("Pause after solder paste dispenser retracted,\n"
              "to allow pressure equilibrium.")
        )
        param_grid.addWidget(self.dwellrev_label, 32, 0)
        param_grid.addWidget(self.dwellrev_entry, 32, 1)

        # Preprocessors
        pp_label = FCLabel('%s:' % _('Preprocessor'))
        pp_label.setToolTip(
            _("Files that control the GCode generation.")
        )

        self.pp_combo = FCComboBox()
        self.pp_combo.addItems(self.options["tools_solderpaste_preprocessor_list"])

        # add ToolTips for the Preprocessor ComboBoxes in Preferences
        for it in range(self.pp_combo.count()):
            self.pp_combo.setItemData(it, self.pp_combo.itemText(it), QtCore.Qt.ItemDataRole.ToolTipRole)

        param_grid.addWidget(pp_label, 34, 0)
        param_grid.addWidget(self.pp_combo, 34, 1)

        self.layout.addStretch(1)
