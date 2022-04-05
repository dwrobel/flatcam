from PyQt6 import QtWidgets

from appGUI.GUIElements import FCDoubleSpinner, FCLabel, GLay, FCFrame
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI
import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class CNCJobPPGroupUI(OptionsGroupUI):
    def __init__(self, app, parent=None):
        super(CNCJobPPGroupUI, self).__init__(self, parent=parent)
        self.decimals = app.decimals
        self.options = app.options

        self.setTitle(str(_("Pre-Processors")))

        # #############################################################################################################
        # PARAMETERS Frame
        # #############################################################################################################
        self.comp_gcode_label = FCLabel('<span style="color:blue;"><b>%s</b></span>' % _("Compensation"))
        self.comp_gcode_label.setToolTip(
            _("Compensate CNC bed issues.")
        )
        self.layout.addWidget(self.comp_gcode_label)

        comp_frame = FCFrame()
        self.layout.addWidget(comp_frame)

        comp_grid = GLay(v_spacing=5, h_spacing=3)
        comp_frame.setLayout(comp_grid)

        # Bed Size X
        self.bed_max_x_lbl = FCLabel('%s %s:' % (_("Bed Size"), "X"))
        self.bed_max_x_lbl.setToolTip(
            '%s: X' % _("CNC bed size on direction")
        )
        self.bed_max_x_entry = FCDoubleSpinner()
        self.bed_max_x_entry.set_range(-9999.9999, 9999.9999)
        self.bed_max_x_entry.set_precision(self.decimals)

        comp_grid.addWidget(self.bed_max_x_lbl, 0, 0)
        comp_grid.addWidget(self.bed_max_x_entry, 0, 1)

        # Bed Size Y
        self.bed_max_y_lbl = FCLabel('%s %s:' % (_("Bed Size"), "Y"))
        self.bed_max_y_lbl.setToolTip(
            '%s: Y' % _("CNC bed size on direction")
        )
        self.bed_max_y_entry = FCDoubleSpinner()
        self.bed_max_y_entry.set_range(-9999.9999, 9999.9999)
        self.bed_max_y_entry.set_precision(self.decimals)

        comp_grid.addWidget(self.bed_max_y_lbl, 2, 0)
        comp_grid.addWidget(self.bed_max_y_entry, 2, 1)

        # Bed Offset X
        self.bed_offx_lbl = FCLabel('%s %s:' % (_("Bed Offset"), "X"))
        self.bed_offx_lbl.setToolTip(
            '%s: X' % _("CNC bed offset on direction")
        )
        self.bed_offx_entry = FCDoubleSpinner()
        self.bed_offx_entry.set_range(-9999.9999, 9999.9999)
        self.bed_offx_entry.set_precision(self.decimals)

        comp_grid.addWidget(self.bed_offx_lbl, 4, 0)
        comp_grid.addWidget(self.bed_offx_entry, 4, 1)

        # Bed Offset Y
        self.bed_offy_lbl = FCLabel('%s %s:' % (_("Bed Offset"), "Y"))
        self.bed_offy_lbl.setToolTip(
            '%s: Y' % _("CNC bed offset on direction")
        )
        self.bed_offy_entry = FCDoubleSpinner()
        self.bed_offy_entry.set_range(-9999.9999, 9999.9999)
        self.bed_offy_entry.set_precision(self.decimals)

        comp_grid.addWidget(self.bed_offy_lbl, 6, 0)
        comp_grid.addWidget(self.bed_offy_entry, 6, 1)

        # Bed Skew X
        self.bed_skewx_lbl = FCLabel('%s %s:' % (_("Bed Skew"), "X"))
        self.bed_skewx_lbl.setToolTip(
            '%s: X' % _("CNC bed skew on direction")
        )
        self.bed_skewx_entry = FCDoubleSpinner()
        self.bed_skewx_entry.set_range(-9999.9999, 9999.9999)
        self.bed_skewx_entry.set_precision(self.decimals)

        comp_grid.addWidget(self.bed_skewx_lbl, 8, 0)
        comp_grid.addWidget(self.bed_skewx_entry, 8, 1)

        # Bed Skew Y
        self.bed_skewy_lbl = FCLabel('%s %s:' % (_("Bed Skew"), "Y"))
        self.bed_skewy_lbl.setToolTip(
            '%s: Y' % _("CNC bed skew on direction")
        )
        self.bed_skewy_entry = FCDoubleSpinner()
        self.bed_skewy_entry.set_range(-9999.9999, 9999.9999)
        self.bed_skewy_entry.set_precision(self.decimals)

        comp_grid.addWidget(self.bed_skewy_lbl, 10, 0)
        comp_grid.addWidget(self.bed_skewy_entry, 10, 1)

        self.layout.addStretch(1)
