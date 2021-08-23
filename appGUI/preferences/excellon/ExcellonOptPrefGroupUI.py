from PyQt6 import QtWidgets

from appGUI.GUIElements import FCDoubleSpinner, FCLabel, FCGridLayout
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI
import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ExcellonOptPrefGroupUI(OptionsGroupUI):

    def __init__(self, defaults, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "Excellon Options", parent=parent)
        super(ExcellonOptPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Excellon Options")))
        self.decimals = decimals
        self.defaults = defaults

        # ## Create CNC Job
        self.cncjob_label = FCLabel('<b>%s</b>' % _('Parameters'))
        self.cncjob_label.setToolTip(
            _("Parameters used to create a CNC Job object\n"
              "for this drill object.")
        )
        self.layout.addWidget(self.cncjob_label)

        grid2 = FCGridLayout(v_spacing=5, h_spacing=3)
        self.layout.addLayout(grid2)
        grid2.setColumnStretch(0, 0)
        grid2.setColumnStretch(1, 1)

        # ### Milling Holes ## ##
        self.mill_hole_label = FCLabel('<b>%s</b>' % _('Mill Holes'))
        self.mill_hole_label.setToolTip(
            _("Create Geometry for milling holes.")
        )
        grid2.addWidget(self.mill_hole_label, 16, 0, 1, 2)

        tdlabel = FCLabel('%s:' % _('Drill Tool dia'))
        tdlabel.setToolTip(
            _("Diameter of the cutting tool\n"
              "when milling drill holes.")
        )
        self.tooldia_entry = FCDoubleSpinner()
        self.tooldia_entry.set_precision(self.decimals)
        self.tooldia_entry.set_range(0, 999.9999)

        grid2.addWidget(tdlabel, 18, 0)
        grid2.addWidget(self.tooldia_entry, 18, 1)

        stdlabel = FCLabel('%s:' % _('Slot Tool dia'))
        stdlabel.setToolTip(
            _("Diameter of the cutting tool\n"
              "when milling slot holes.")
        )
        self.slot_tooldia_entry = FCDoubleSpinner()
        self.slot_tooldia_entry.set_precision(self.decimals)
        self.slot_tooldia_entry.set_range(0, 999.9999)

        grid2.addWidget(stdlabel, 21, 0)
        grid2.addWidget(self.slot_tooldia_entry, 21, 1)

        self.layout.addStretch()
