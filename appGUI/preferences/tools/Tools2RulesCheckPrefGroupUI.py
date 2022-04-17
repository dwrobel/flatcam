from PyQt6 import QtWidgets

from appGUI.GUIElements import FCCheckBox, FCDoubleSpinner, FCLabel, GLay, FCFrame
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class Tools2RulesCheckPrefGroupUI(OptionsGroupUI):
    def __init__(self, app, parent=None):

        super(Tools2RulesCheckPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Check Rules Plugin")))
        self.setToolTip(
            _("A tool to check if Gerber files are within a set\n"
              "of Manufacturing Rules.")
        )
        self.decimals = app.decimals
        self.options = app.options

        # #############################################################################################################
        # Rules Frame
        # #############################################################################################################
        rules_copper_label = FCLabel('<span style="color:%s;"><b>%s %s</b></span>' % (self.app.theme_safe_color('darkorange'), _("Copper"), _("Rules")))
        self.layout.addWidget(rules_copper_label)

        copper_frame = FCFrame()
        self.layout.addWidget(copper_frame)

        self.copper_grid = GLay(v_spacing=5, h_spacing=3)
        copper_frame.setLayout(self.copper_grid)

        # Trace size
        self.trace_size_cb = FCCheckBox('%s:' % _("Trace Size"))
        self.trace_size_cb.setToolTip(
            _("This checks if the minimum size for traces is met.")
        )
        self.copper_grid.addWidget(self.trace_size_cb, 0, 0, 1, 2)

        # Trace size value
        self.trace_size_lbl = FCLabel('%s:' % _("Value"))
        self.trace_size_lbl.setToolTip(
            _("Minimum acceptable trace size.")
        )

        self.trace_size_entry = FCDoubleSpinner()
        self.trace_size_entry.set_range(0.0000, 10000.0000)
        self.trace_size_entry.set_precision(self.decimals)
        self.trace_size_entry.setSingleStep(0.1)

        self.copper_grid.addWidget(self.trace_size_lbl, 2, 0)
        self.copper_grid.addWidget(self.trace_size_entry, 2, 1)

        # Copper2copper clearance
        self.clearance_copper2copper_cb = FCCheckBox('%s:' % _("Copper to Copper clearance"))
        self.clearance_copper2copper_cb.setToolTip(
            _("This checks if the minimum clearance between copper\n"
              "features is met.")
        )
        self.copper_grid.addWidget(self.clearance_copper2copper_cb, 4, 0, 1, 2)

        # Copper2copper clearance value
        self.clearance_copper2copper_lbl = FCLabel('%s:' % _("Value"))
        self.clearance_copper2copper_lbl.setToolTip(
            _("Minimum acceptable clearance value.")
        )

        self.clearance_copper2copper_entry = FCDoubleSpinner()
        self.clearance_copper2copper_entry.set_range(0.0000, 10000.0000)
        self.clearance_copper2copper_entry.set_precision(self.decimals)
        self.clearance_copper2copper_entry.setSingleStep(0.1)

        self.copper_grid.addWidget(self.clearance_copper2copper_lbl, 6, 0)
        self.copper_grid.addWidget(self.clearance_copper2copper_entry, 6, 1)

        # Copper2outline clearance
        self.clearance_copper2ol_cb = FCCheckBox('%s:' % _("Copper to Outline clearance"))
        self.clearance_copper2ol_cb.setToolTip(
            _("This checks if the minimum clearance between copper\n"
              "features and the outline is met.")
        )
        self.copper_grid.addWidget(self.clearance_copper2ol_cb, 8, 0, 1, 2)

        # Copper2outline clearance value
        self.clearance_copper2ol_lbl = FCLabel('%s:' % _("Value"))
        self.clearance_copper2ol_lbl.setToolTip(
            _("Minimum acceptable clearance value.")
        )

        self.clearance_copper2ol_entry = FCDoubleSpinner()
        self.clearance_copper2ol_entry.set_range(0.0000, 10000.0000)
        self.clearance_copper2ol_entry.set_precision(self.decimals)
        self.clearance_copper2ol_entry.setSingleStep(0.1)

        self.copper_grid.addWidget(self.clearance_copper2ol_lbl, 10, 0)
        self.copper_grid.addWidget(self.clearance_copper2ol_entry, 10, 1)

        # Ring integrity check
        self.ring_integrity_cb = FCCheckBox('%s:' % _("Minimum Annular Ring"))
        self.ring_integrity_cb.setToolTip(
            _("This checks if the minimum copper ring left by drilling\n"
              "a hole into a pad is met.")
        )
        self.copper_grid.addWidget(self.ring_integrity_cb, 12, 0, 1, 2)

        # Ring integrity value
        self.ring_integrity_lbl = FCLabel('%s:' % _("Value"))
        self.ring_integrity_lbl.setToolTip(
            _("Minimum acceptable ring value.")
        )

        self.ring_integrity_entry = FCDoubleSpinner()
        self.ring_integrity_entry.set_range(0.0000, 10000.0000)
        self.ring_integrity_entry.set_precision(self.decimals)
        self.ring_integrity_entry.setSingleStep(0.1)

        self.copper_grid.addWidget(self.ring_integrity_lbl, 14, 0)
        self.copper_grid.addWidget(self.ring_integrity_entry, 14, 1)

        # #############################################################################################################
        # Silk Frame
        # #############################################################################################################
        silk_copper_label = FCLabel('<span style="color:%s;"><b>%s %s</b></span>' % (self.app.theme_safe_color('teal'), _("Silk"), _("Rules")))
        self.layout.addWidget(silk_copper_label)

        silk_frame = FCFrame()
        self.layout.addWidget(silk_frame)

        self.silk_grid = GLay(v_spacing=5, h_spacing=3)
        silk_frame.setLayout(self.silk_grid)

        # Silkscreen2silkscreen clearance
        self.clearance_silk2silk_cb = FCCheckBox('%s:' % _("Silk to Silk Clearance"))
        self.clearance_silk2silk_cb.setToolTip(
            _("This checks if the minimum clearance between silkscreen\n"
              "features and silkscreen features is met.")
        )
        self.silk_grid.addWidget(self.clearance_silk2silk_cb, 0, 0, 1, 2)

        # Copper2silkscreen clearance value
        self.clearance_silk2silk_lbl = FCLabel('%s:' % _("Value"))
        self.clearance_silk2silk_lbl.setToolTip(
            _("Minimum acceptable clearance value.")
        )

        self.clearance_silk2silk_entry = FCDoubleSpinner()
        self.clearance_silk2silk_entry.set_range(0.0000, 10000.0000)
        self.clearance_silk2silk_entry.set_precision(self.decimals)
        self.clearance_silk2silk_entry.setSingleStep(0.1)

        self.silk_grid.addWidget(self.clearance_silk2silk_lbl, 2, 0)
        self.silk_grid.addWidget(self.clearance_silk2silk_entry, 2, 1)

        # Silkscreen2soldermask clearance
        self.clearance_silk2sm_cb = FCCheckBox('%s:' % _("Silk to Solder Mask Clearance"))
        self.clearance_silk2sm_cb.setToolTip(
            _("This checks if the minimum clearance between silkscreen\n"
              "features and soldermask features is met.")
        )
        self.silk_grid.addWidget(self.clearance_silk2sm_cb, 4, 0, 1, 2)

        # Silkscreen2soldermask clearance value
        self.clearance_silk2sm_lbl = FCLabel('%s:' % _("Value"))
        self.clearance_silk2sm_lbl.setToolTip(
            _("Minimum acceptable clearance value.")
        )

        self.clearance_silk2sm_entry = FCDoubleSpinner()
        self.clearance_silk2sm_entry.set_range(0.0000, 10000.0000)
        self.clearance_silk2sm_entry.set_precision(self.decimals)
        self.clearance_silk2sm_entry.setSingleStep(0.1)

        self.silk_grid.addWidget(self.clearance_silk2sm_lbl, 6, 0)
        self.silk_grid.addWidget(self.clearance_silk2sm_entry, 6, 1)

        # Silk2outline clearance
        self.clearance_silk2ol_cb = FCCheckBox('%s:' % _("Silk to Outline Clearance"))
        self.clearance_silk2ol_cb.setToolTip(
            _("This checks if the minimum clearance between silk\n"
              "features and the outline is met.")
        )
        self.silk_grid.addWidget(self.clearance_silk2ol_cb, 8, 0, 1, 2)

        # Silk2outline clearance value
        self.clearance_silk2ol_lbl = FCLabel('%s:' % _("Value"))
        self.clearance_silk2ol_lbl.setToolTip(
            _("Minimum acceptable clearance value.")
        )

        self.clearance_silk2ol_entry = FCDoubleSpinner()
        self.clearance_silk2ol_entry.set_range(0.0000, 10000.0000)
        self.clearance_silk2ol_entry.set_precision(self.decimals)
        self.clearance_silk2ol_entry.setSingleStep(0.1)

        self.silk_grid.addWidget(self.clearance_silk2ol_lbl, 10, 0)
        self.silk_grid.addWidget(self.clearance_silk2ol_entry, 10, 1)

        # #############################################################################################################
        # Soldermask Frame
        # #############################################################################################################
        sm_copper_label = FCLabel('<span style="color:%s;"><b>%s %s</b></span>' % (self.app.theme_safe_color('magenta'), _("Soldermask"), _("Rules")))
        self.layout.addWidget(sm_copper_label)

        solder_frame = FCFrame()
        self.layout.addWidget(solder_frame)

        self.solder_grid = GLay(v_spacing=5, h_spacing=3)
        solder_frame.setLayout(self.solder_grid)

        # Soldermask2soldermask clearance
        self.clearance_sm2sm_cb = FCCheckBox('%s:' % _("Minimum Solder Mask Sliver"))
        self.clearance_sm2sm_cb.setToolTip(
            _("This checks if the minimum clearance between soldermask\n"
              "features and soldermask features is met.")
        )
        self.solder_grid.addWidget(self.clearance_sm2sm_cb, 0, 0, 1, 2)

        # Soldermask2soldermask clearance value

        self.clearance_sm2sm_lbl = FCLabel('%s:' % _("Value"))
        self.clearance_sm2sm_lbl.setToolTip(
            _("Minimum acceptable clearance value.")
        )

        self.clearance_sm2sm_entry = FCDoubleSpinner()
        self.clearance_sm2sm_entry.set_range(0.0000, 10000.0000)
        self.clearance_sm2sm_entry.set_precision(self.decimals)
        self.clearance_sm2sm_entry.setSingleStep(0.1)

        self.solder_grid.addWidget(self.clearance_sm2sm_lbl, 2, 0)
        self.solder_grid.addWidget(self.clearance_sm2sm_entry, 2, 1)

        # #############################################################################################################
        # Holes Frame
        # #############################################################################################################
        holes_copper_label = FCLabel('<span style="color:%s;"><b>%s %s</b></span>' % (self.app.theme_safe_color('brown'), _("Holes"), _("Rules")))
        self.layout.addWidget(holes_copper_label)

        holes_frame = FCFrame()
        self.layout.addWidget(holes_frame)

        self.holes_grid = GLay(v_spacing=5, h_spacing=3)
        holes_frame.setLayout(self.holes_grid)

        # Hole2Hole clearance
        self.clearance_d2d_cb = FCCheckBox('%s:' % _("Hole to Hole Clearance"))
        self.clearance_d2d_cb.setToolTip(
            _("This checks if the minimum clearance between a drill hole\n"
              "and another drill hole is met.")
        )
        self.holes_grid.addWidget(self.clearance_d2d_cb, 0, 0, 1, 2)

        # Hole2Hole clearance value
        self.clearance_d2d_lbl = FCLabel('%s:' % _("Value"))
        self.clearance_d2d_lbl.setToolTip(
            _("Minimum acceptable clearance value.")
        )

        self.clearance_d2d_entry = FCDoubleSpinner()
        self.clearance_d2d_entry.set_range(0.0000, 10000.0000)
        self.clearance_d2d_entry.set_precision(self.decimals)
        self.clearance_d2d_entry.setSingleStep(0.1)

        self.holes_grid.addWidget(self.clearance_d2d_lbl, 2, 0)
        self.holes_grid.addWidget(self.clearance_d2d_entry, 2, 1)

        # Drill holes size check
        self.drill_size_cb = FCCheckBox('%s:' % _("Hole Size"))
        self.drill_size_cb.setToolTip(
            _("This checks if the drill holes\n"
              "sizes are above the threshold.")
        )
        self.holes_grid.addWidget(self.drill_size_cb, 4, 0, 1, 2)

        # Drills holes value
        self.drill_size_lbl = FCLabel('%s:' % _("Value"))
        self.drill_size_lbl.setToolTip(
            _("Minimum acceptable drill size.")
        )

        self.drill_size_entry = FCDoubleSpinner()
        self.drill_size_entry.set_range(0.0000, 10000.0000)
        self.drill_size_entry.set_precision(self.decimals)
        self.drill_size_entry.setSingleStep(0.1)

        self.holes_grid.addWidget(self.drill_size_lbl, 6, 0)
        self.holes_grid.addWidget(self.drill_size_entry, 6, 1)

        self.layout.addStretch(1)
