from PyQt6 import QtWidgets

from appGUI.GUIElements import FCDoubleSpinner, FCLabel, GLay, FCFrame
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI
import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ExcellonOptPrefGroupUI(OptionsGroupUI):

    def __init__(self, app, parent=None):
        # OptionsGroupUI.__init__(self, "Excellon Options", parent=parent)
        super(ExcellonOptPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Options")))
        self.decimals = app.decimals
        self.options = app.options

        # #############################################################################################################
        # PARAMETERS Frame
        # #############################################################################################################
        self.cncjob_label = FCLabel('<span style="color:%s;"><b>%s</b></span>' % (self.app.theme_safe_color('blue'), _('Parameters')))
        self.cncjob_label.setToolTip(
            _("Parameters used to create a CNC Job object\n"
              "for this drill object.")
        )
        self.layout.addWidget(self.cncjob_label)

        param_frame = FCFrame()
        self.layout.addWidget(param_frame)

        param_grid = GLay(v_spacing=5, h_spacing=3)
        param_frame.setLayout(param_grid)

        # ### Milling Holes ## ##
        self.mill_hole_label = FCLabel('<b>%s</b>' % _('Mill Holes'))
        self.mill_hole_label.setToolTip(
            _("Create Geometry for milling holes.")
        )
        param_grid.addWidget(self.mill_hole_label, 0, 0, 1, 2)

        tdlabel = FCLabel('%s:' % _('Drill Tool dia'))
        tdlabel.setToolTip(
            _("Diameter of the cutting tool\n"
              "when milling drill holes.")
        )
        self.tooldia_entry = FCDoubleSpinner()
        self.tooldia_entry.set_precision(self.decimals)
        self.tooldia_entry.set_range(0, 999.9999)

        param_grid.addWidget(tdlabel, 2, 0)
        param_grid.addWidget(self.tooldia_entry, 2, 1)

        stdlabel = FCLabel('%s:' % _('Slot Tool dia'))
        stdlabel.setToolTip(
            _("Diameter of the cutting tool\n"
              "when milling slot holes.")
        )
        self.slot_tooldia_entry = FCDoubleSpinner()
        self.slot_tooldia_entry.set_precision(self.decimals)
        self.slot_tooldia_entry.set_range(0, 999.9999)

        param_grid.addWidget(stdlabel, 4, 0)
        param_grid.addWidget(self.slot_tooldia_entry, 4, 1)

        # self.layout.addStretch()
