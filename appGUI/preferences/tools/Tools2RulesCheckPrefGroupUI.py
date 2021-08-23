from PyQt6 import QtWidgets

from appGUI.GUIElements import FCCheckBox, FCDoubleSpinner, FCLabel, FCGridLayout
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class Tools2RulesCheckPrefGroupUI(OptionsGroupUI):
    def __init__(self, defaults, decimals=4, parent=None):

        super(Tools2RulesCheckPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Check Rules Plugin")))
        self.decimals = decimals
        self.defaults = defaults

        self.crlabel = FCLabel("<b>%s:</b>" % _("Parameters"))
        self.crlabel.setToolTip(
            _("A tool to check if Gerber files are within a set\n"
              "of Manufacturing Rules.")
        )
        self.layout.addWidget(self.crlabel)

        # Form Layout
        self.grid0 = FCGridLayout(v_spacing=5, h_spacing=3)
        self.grid0.setColumnStretch(0, 0)
        self.grid0.setColumnStretch(1, 1)
        self.layout.addLayout(self.grid0)

        # Trace size
        self.trace_size_cb = FCCheckBox('%s:' % _("Trace Size"))
        self.trace_size_cb.setToolTip(
            _("This checks if the minimum size for traces is met.")
        )
        self.grid0.addWidget(self.trace_size_cb, 0, 0, 1, 2)

        # Trace size value
        self.trace_size_entry = FCDoubleSpinner()
        self.trace_size_entry.set_range(0.0000, 10000.0000)
        self.trace_size_entry.set_precision(self.decimals)
        self.trace_size_entry.setSingleStep(0.1)

        self.trace_size_lbl = FCLabel('%s:' % _("Min value"))
        self.trace_size_lbl.setToolTip(
            _("Minimum acceptable trace size.")
        )
        self.grid0.addWidget(self.trace_size_lbl, 2, 0)
        self.grid0.addWidget(self.trace_size_entry, 2, 1)

        # Copper2copper clearance
        self.clearance_copper2copper_cb = FCCheckBox('%s:' % _("Copper to Copper clearance"))
        self.clearance_copper2copper_cb.setToolTip(
            _("This checks if the minimum clearance between copper\n"
              "features is met.")
        )
        self.grid0.addWidget(self.clearance_copper2copper_cb, 4, 0, 1, 2)

        # Copper2copper clearance value
        self.clearance_copper2copper_entry = FCDoubleSpinner()
        self.clearance_copper2copper_entry.set_range(0.0000, 10000.0000)
        self.clearance_copper2copper_entry.set_precision(self.decimals)
        self.clearance_copper2copper_entry.setSingleStep(0.1)

        self.clearance_copper2copper_lbl = FCLabel('%s:' % _("Min value"))
        self.clearance_copper2copper_lbl.setToolTip(
            _("Minimum acceptable clearance value.")
        )
        self.grid0.addWidget(self.clearance_copper2copper_lbl, 6, 0)
        self.grid0.addWidget(self.clearance_copper2copper_entry, 6, 1)

        # Copper2outline clearance
        self.clearance_copper2ol_cb = FCCheckBox('%s:' % _("Copper to Outline clearance"))
        self.clearance_copper2ol_cb.setToolTip(
            _("This checks if the minimum clearance between copper\n"
              "features and the outline is met.")
        )
        self.grid0.addWidget(self.clearance_copper2ol_cb, 8, 0, 1, 2)

        # Copper2outline clearance value
        self.clearance_copper2ol_entry = FCDoubleSpinner()
        self.clearance_copper2ol_entry.set_range(0.0000, 10000.0000)
        self.clearance_copper2ol_entry.set_precision(self.decimals)
        self.clearance_copper2ol_entry.setSingleStep(0.1)

        self.clearance_copper2ol_lbl = FCLabel('%s:' % _("Min value"))
        self.clearance_copper2ol_lbl.setToolTip(
            _("Minimum acceptable clearance value.")
        )
        self.grid0.addWidget(self.clearance_copper2ol_lbl, 10, 0)
        self.grid0.addWidget(self.clearance_copper2ol_entry, 10, 1)

        # Silkscreen2silkscreen clearance
        self.clearance_silk2silk_cb = FCCheckBox('%s:' % _("Silk to Silk Clearance"))
        self.clearance_silk2silk_cb.setToolTip(
            _("This checks if the minimum clearance between silkscreen\n"
              "features and silkscreen features is met.")
        )
        self.grid0.addWidget(self.clearance_silk2silk_cb, 12, 0, 1, 2)

        # Copper2silkscreen clearance value
        self.clearance_silk2silk_entry = FCDoubleSpinner()
        self.clearance_silk2silk_entry.set_range(0.0000, 10000.0000)
        self.clearance_silk2silk_entry.set_precision(self.decimals)
        self.clearance_silk2silk_entry.setSingleStep(0.1)

        self.clearance_silk2silk_lbl = FCLabel('%s:' % _("Min value"))
        self.clearance_silk2silk_lbl.setToolTip(
            _("Minimum acceptable clearance value.")
        )
        self.grid0.addWidget(self.clearance_silk2silk_lbl, 14, 0)
        self.grid0.addWidget(self.clearance_silk2silk_entry, 14, 1)

        # Silkscreen2soldermask clearance
        self.clearance_silk2sm_cb = FCCheckBox('%s:' % _("Silk to Solder Mask Clearance"))
        self.clearance_silk2sm_cb.setToolTip(
            _("This checks if the minimum clearance between silkscreen\n"
              "features and soldermask features is met.")
        )
        self.grid0.addWidget(self.clearance_silk2sm_cb, 16, 0, 1, 2)

        # Silkscreen2soldermask clearance value
        self.clearance_silk2sm_entry = FCDoubleSpinner()
        self.clearance_silk2sm_entry.set_range(0.0000, 10000.0000)
        self.clearance_silk2sm_entry.set_precision(self.decimals)
        self.clearance_silk2sm_entry.setSingleStep(0.1)

        self.clearance_silk2sm_lbl = FCLabel('%s:' % _("Min value"))
        self.clearance_silk2sm_lbl.setToolTip(
            _("Minimum acceptable clearance value.")
        )
        self.grid0.addWidget(self.clearance_silk2sm_lbl, 18, 0)
        self.grid0.addWidget(self.clearance_silk2sm_entry, 18, 1)

        # Silk2outline clearance
        self.clearance_silk2ol_cb = FCCheckBox('%s:' % _("Silk to Outline Clearance"))
        self.clearance_silk2ol_cb.setToolTip(
            _("This checks if the minimum clearance between silk\n"
              "features and the outline is met.")
        )
        self.grid0.addWidget(self.clearance_silk2ol_cb, 20, 0, 1, 2)

        # Silk2outline clearance value
        self.clearance_silk2ol_entry = FCDoubleSpinner()
        self.clearance_silk2ol_entry.set_range(0.0000, 10000.0000)
        self.clearance_silk2ol_entry.set_precision(self.decimals)
        self.clearance_silk2ol_entry.setSingleStep(0.1)

        self.clearance_silk2ol_lbl = FCLabel('%s:' % _("Min value"))
        self.clearance_silk2ol_lbl.setToolTip(
            _("Minimum acceptable clearance value.")
        )
        self.grid0.addWidget(self.clearance_silk2ol_lbl, 22, 0)
        self.grid0.addWidget(self.clearance_silk2ol_entry, 22, 1)

        # Soldermask2soldermask clearance
        self.clearance_sm2sm_cb = FCCheckBox('%s:' % _("Minimum Solder Mask Sliver"))
        self.clearance_sm2sm_cb.setToolTip(
            _("This checks if the minimum clearance between soldermask\n"
              "features and soldermask features is met.")
        )
        self.grid0.addWidget(self.clearance_sm2sm_cb, 24, 0, 1, 2)

        # Soldermask2soldermask clearance value
        self.clearance_sm2sm_entry = FCDoubleSpinner()
        self.clearance_sm2sm_entry.set_range(0.0000, 10000.0000)
        self.clearance_sm2sm_entry.set_precision(self.decimals)
        self.clearance_sm2sm_entry.setSingleStep(0.1)

        self.clearance_sm2sm_lbl = FCLabel('%s:' % _("Min value"))
        self.clearance_sm2sm_lbl.setToolTip(
            _("Minimum acceptable clearance value.")
        )
        self.grid0.addWidget(self.clearance_sm2sm_lbl, 26, 0)
        self.grid0.addWidget(self.clearance_sm2sm_entry, 26, 1)

        # Ring integrity check
        self.ring_integrity_cb = FCCheckBox('%s:' % _("Minimum Annular Ring"))
        self.ring_integrity_cb.setToolTip(
            _("This checks if the minimum copper ring left by drilling\n"
              "a hole into a pad is met.")
        )
        self.grid0.addWidget(self.ring_integrity_cb, 28, 0, 1, 2)

        # Ring integrity value
        self.ring_integrity_entry = FCDoubleSpinner()
        self.ring_integrity_entry.set_range(0.0000, 10000.0000)
        self.ring_integrity_entry.set_precision(self.decimals)
        self.ring_integrity_entry.setSingleStep(0.1)

        self.ring_integrity_lbl = FCLabel('%s:' % _("Min value"))
        self.ring_integrity_lbl.setToolTip(
            _("Minimum acceptable ring value.")
        )
        self.grid0.addWidget(self.ring_integrity_lbl, 30, 0)
        self.grid0.addWidget(self.ring_integrity_entry, 30, 1)

        self.grid0.addWidget(FCLabel(''), 32, 0, 1, 2)

        # Hole2Hole clearance
        self.clearance_d2d_cb = FCCheckBox('%s:' % _("Hole to Hole Clearance"))
        self.clearance_d2d_cb.setToolTip(
            _("This checks if the minimum clearance between a drill hole\n"
              "and another drill hole is met.")
        )
        self.grid0.addWidget(self.clearance_d2d_cb, 34, 0, 1, 2)

        # Hole2Hole clearance value
        self.clearance_d2d_entry = FCDoubleSpinner()
        self.clearance_d2d_entry.set_range(0.0000, 10000.0000)
        self.clearance_d2d_entry.set_precision(self.decimals)
        self.clearance_d2d_entry.setSingleStep(0.1)

        self.clearance_d2d_lbl = FCLabel('%s:' % _("Min value"))
        self.clearance_d2d_lbl.setToolTip(
            _("Minimum acceptable drill size.")
        )
        self.grid0.addWidget(self.clearance_d2d_lbl, 36, 0)
        self.grid0.addWidget(self.clearance_d2d_entry, 36, 1)

        # Drill holes size check
        self.drill_size_cb = FCCheckBox('%s:' % _("Hole Size"))
        self.drill_size_cb.setToolTip(
            _("This checks if the drill holes\n"
              "sizes are above the threshold.")
        )
        self.grid0.addWidget(self.drill_size_cb, 38, 0, 1, 2)

        # Drile holes value
        self.drill_size_entry = FCDoubleSpinner()
        self.drill_size_entry.set_range(0.0000, 10000.0000)
        self.drill_size_entry.set_precision(self.decimals)
        self.drill_size_entry.setSingleStep(0.1)

        self.drill_size_lbl = FCLabel('%s:' % _("Min value"))
        self.drill_size_lbl.setToolTip(
            _("Minimum acceptable clearance value.")
        )
        self.grid0.addWidget(self.drill_size_lbl, 40, 0)
        self.grid0.addWidget(self.drill_size_entry, 40, 1)

        self.layout.addStretch(1)
