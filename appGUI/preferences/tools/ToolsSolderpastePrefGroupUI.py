from PyQt6 import QtCore

from appGUI.GUIElements import FCDoubleSpinner, FCSpinner, FCComboBox, NumericalEvalTupleEntry, FCLabel, FCGridLayout, \
    FCFrame
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ToolsSolderpastePrefGroupUI(OptionsGroupUI):
    def __init__(self, defaults, decimals=4, parent=None):

        super(ToolsSolderpastePrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("SolderPaste Plugin")))
        self.decimals = decimals
        self.defaults = defaults

        # #############################################################################################################
        # PARAMETERS Frame
        # #############################################################################################################
        self.solderpastelabel = FCLabel('<span style="color:blue;"><b>%s</b></span>' % _("Parameters"))
        self.solderpastelabel.setToolTip(
            _("A tool to create GCode for dispensing\n"
              "solder paste onto a PCB.")
        )
        self.layout.addWidget(self.solderpastelabel)

        param_frame = FCFrame()
        self.layout.addWidget(param_frame)

        param_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        param_frame.setLayout(param_grid)

        # Nozzle Tool Diameters
        nozzletdlabel = FCLabel('<b><font color="green">%s:</font></b>' % _('Tools Dia'))
        nozzletdlabel.setToolTip(
            _("Diameters of the tools, separated by comma.\n"
              "The value of the diameter has to use the dot decimals separator.\n"
              "Valid values: 0.3, 1.0")
        )
        self.nozzle_tool_dia_entry = NumericalEvalTupleEntry(border_color='#0069A9')

        param_grid.addWidget(nozzletdlabel, 0, 0)
        param_grid.addWidget(self.nozzle_tool_dia_entry, 0, 1)

        # New Nozzle Tool Dia
        self.addtool_entry_lbl = FCLabel('<b>%s:</b>' % _('New Nozzle Dia'))
        self.addtool_entry_lbl.setToolTip(
            _("Diameter for the new tool to add in the Tool Table")
        )
        self.addtool_entry = FCDoubleSpinner()
        self.addtool_entry.set_precision(self.decimals)
        self.addtool_entry.set_range(0.0000001, 10000.0000)
        self.addtool_entry.setSingleStep(0.1)

        param_grid.addWidget(self.addtool_entry_lbl, 1, 0)
        param_grid.addWidget(self.addtool_entry, 1, 1)

        # Z dispense start
        self.z_start_entry = FCDoubleSpinner()
        self.z_start_entry.set_precision(self.decimals)
        self.z_start_entry.set_range(0.0000001, 10000.0000)
        self.z_start_entry.setSingleStep(0.1)

        self.z_start_label = FCLabel('%s:' % _("Z Dispense Start"))
        self.z_start_label.setToolTip(
            _("The height (Z) when solder paste dispensing starts.")
        )
        param_grid.addWidget(self.z_start_label, 2, 0)
        param_grid.addWidget(self.z_start_entry, 2, 1)

        # Z dispense
        self.z_dispense_entry = FCDoubleSpinner()
        self.z_dispense_entry.set_precision(self.decimals)
        self.z_dispense_entry.set_range(0.0000001, 10000.0000)
        self.z_dispense_entry.setSingleStep(0.1)

        self.z_dispense_label = FCLabel('%s:' % _("Z Dispense"))
        self.z_dispense_label.setToolTip(
            _("The height (Z) when doing solder paste dispensing.")
        )
        param_grid.addWidget(self.z_dispense_label, 3, 0)
        param_grid.addWidget(self.z_dispense_entry, 3, 1)

        # Z dispense stop
        self.z_stop_entry = FCDoubleSpinner()
        self.z_stop_entry.set_precision(self.decimals)
        self.z_stop_entry.set_range(0.0000001, 10000.0000)
        self.z_stop_entry.setSingleStep(0.1)

        self.z_stop_label = FCLabel('%s:' % _("Z Dispense Stop"))
        self.z_stop_label.setToolTip(
            _("The height (Z) when solder paste dispensing stops.")
        )
        param_grid.addWidget(self.z_stop_label, 4, 0)
        param_grid.addWidget(self.z_stop_entry, 4, 1)

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
        param_grid.addWidget(self.z_travel_label, 5, 0)
        param_grid.addWidget(self.z_travel_entry, 5, 1)

        # Z toolchange location
        self.z_toolchange_entry = FCDoubleSpinner()
        self.z_toolchange_entry.set_precision(self.decimals)
        self.z_toolchange_entry.set_range(0.0000001, 10000.0000)
        self.z_toolchange_entry.setSingleStep(0.1)

        self.z_toolchange_label = FCLabel('%s:' % _("Z Toolchange"))
        self.z_toolchange_label.setToolTip(
            _("The height (Z) for tool (nozzle) change.")
        )
        param_grid.addWidget(self.z_toolchange_label, 6, 0)
        param_grid.addWidget(self.z_toolchange_entry, 6, 1)

        # X,Y Toolchange location
        self.xy_toolchange_entry = NumericalEvalTupleEntry(border_color='#0069A9')
        self.xy_toolchange_label = FCLabel('%s:' % _("Toolchange X-Y"))
        self.xy_toolchange_label.setToolTip(
            _("The X,Y location for tool (nozzle) change.\n"
              "The format is (x, y) where x and y are real numbers.")
        )
        param_grid.addWidget(self.xy_toolchange_label, 7, 0)
        param_grid.addWidget(self.xy_toolchange_entry, 7, 1)

        # Feedrate X-Y
        self.frxy_entry = FCDoubleSpinner()
        self.frxy_entry.set_precision(self.decimals)
        self.frxy_entry.set_range(0.0000001, 910000.0000)
        self.frxy_entry.setSingleStep(0.1)

        self.frxy_label = FCLabel('%s:' % _("Feedrate X-Y"))
        self.frxy_label.setToolTip(
            _("Feedrate (speed) while moving on the X-Y plane.")
        )
        param_grid.addWidget(self.frxy_label, 8, 0)
        param_grid.addWidget(self.frxy_entry, 8, 1)

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
        param_grid.addWidget(self.frz_label, 9, 0)
        param_grid.addWidget(self.frz_entry, 9, 1)

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
        param_grid.addWidget(self.frz_dispense_label, 10, 0)
        param_grid.addWidget(self.frz_dispense_entry, 10, 1)

        # Spindle Speed Forward
        self.speedfwd_entry = FCSpinner()
        self.speedfwd_entry.set_range(0, 99999)
        self.speedfwd_entry.set_step(1000)

        self.speedfwd_label = FCLabel('%s:' % _("Spindle Speed FWD"))
        self.speedfwd_label.setToolTip(
            _("The dispenser speed while pushing solder paste\n"
              "through the dispenser nozzle.")
        )
        param_grid.addWidget(self.speedfwd_label, 11, 0)
        param_grid.addWidget(self.speedfwd_entry, 11, 1)

        # Dwell Forward
        self.dwellfwd_entry = FCDoubleSpinner()
        self.dwellfwd_entry.set_precision(self.decimals)
        self.dwellfwd_entry.set_range(0.0000001, 10000.0000)
        self.dwellfwd_entry.setSingleStep(0.1)

        self.dwellfwd_label = FCLabel('%s:' % _("Dwell FWD"))
        self.dwellfwd_label.setToolTip(
            _("Pause after solder dispensing.")
        )
        param_grid.addWidget(self.dwellfwd_label, 12, 0)
        param_grid.addWidget(self.dwellfwd_entry, 12, 1)

        # Spindle Speed Reverse
        self.speedrev_entry = FCSpinner()
        self.speedrev_entry.set_range(0, 999999)
        self.speedrev_entry.set_step(1000)

        self.speedrev_label = FCLabel('%s:' % _("Spindle Speed REV"))
        self.speedrev_label.setToolTip(
            _("The dispenser speed while retracting solder paste\n"
              "through the dispenser nozzle.")
        )
        param_grid.addWidget(self.speedrev_label, 13, 0)
        param_grid.addWidget(self.speedrev_entry, 13, 1)

        # Dwell Reverse
        self.dwellrev_entry = FCDoubleSpinner()
        self.dwellrev_entry.set_precision(self.decimals)
        self.dwellrev_entry.set_range(0.0000001, 10000.0000)
        self.dwellrev_entry.setSingleStep(0.1)

        self.dwellrev_label = FCLabel('%s:' % _("Dwell REV"))
        self.dwellrev_label.setToolTip(
            _("Pause after solder paste dispenser retracted,\n"
              "to allow pressure equilibrium.")
        )
        param_grid.addWidget(self.dwellrev_label, 14, 0)
        param_grid.addWidget(self.dwellrev_entry, 14, 1)

        # Preprocessors
        pp_label = FCLabel('%s:' % _('Preprocessor'))
        pp_label.setToolTip(
            _("Files that control the GCode generation.")
        )

        self.pp_combo = FCComboBox()
        self.pp_combo.addItems(self.defaults["tools_solderpaste_preprocessor_list"])

        # add ToolTips for the Preprocessor ComboBoxes in Preferences
        for it in range(self.pp_combo.count()):
            self.pp_combo.setItemData(it, self.pp_combo.itemText(it), QtCore.Qt.ItemDataRole.ToolTipRole)

        param_grid.addWidget(pp_label, 15, 0)
        param_grid.addWidget(self.pp_combo, 15, 1)

        self.layout.addStretch()
