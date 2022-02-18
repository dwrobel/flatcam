from PyQt6 import QtGui

from appGUI.GUIElements import FCSpinner, FCColorEntry, FCLabel, FCGridLayout, FCFrame
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI
import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class CNCJobAdvOptPrefGroupUI(OptionsGroupUI):
    def __init__(self, defaults, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "CNC Job Advanced Options Preferences", parent=None)
        super(CNCJobAdvOptPrefGroupUI, self).__init__(self, parent=parent)
        self.decimals = decimals
        self.defaults = defaults

        self.setTitle(str(_("Adv. Options")))

        # #############################################################################################################
        # PARAMETERS Frame
        # #############################################################################################################
        self.export_gcode_label = FCLabel('<span style="color:blue;"><b>%s</b></span>' % _("Parameters"))
        self.export_gcode_label.setToolTip(
            _("Export and save G-Code to\n"
              "make this object to a file.")
        )
        self.layout.addWidget(self.export_gcode_label)

        param_frame = FCFrame()
        self.layout.addWidget(param_frame)

        param_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        param_frame.setLayout(param_grid)

        # Annotation Font Size
        self.annotation_fontsize_label = FCLabel('%s:' % _("Annotation Size"))
        self.annotation_fontsize_label.setToolTip(
            _("The font size of the annotation text. In pixels.")
        )
        self.annotation_fontsize_sp = FCSpinner()
        self.annotation_fontsize_sp.set_range(0, 9999)

        param_grid.addWidget(self.annotation_fontsize_label, 0, 0)
        param_grid.addWidget(self.annotation_fontsize_sp, 0, 1)

        # Annotation Font Color
        self.annotation_color_label = FCLabel('%s:' % _('Annotation Color'))
        self.annotation_color_label.setToolTip(
            _("Set the font color for the annotation texts.")
        )
        self.annotation_fontcolor_entry = FCColorEntry(icon=QtGui.QIcon(
            self.app.resource_location + '/set_colors64.png'))

        param_grid.addWidget(self.annotation_color_label, 2, 0)
        param_grid.addWidget(self.annotation_fontcolor_entry, 2, 1)

        self.layout.addStretch(1)

        self.annotation_fontcolor_entry.editingFinished.connect(self.on_annotation_fontcolor_entry)

    def on_annotation_fontcolor_entry(self):
        self.app.options['cncjob_annotation_fontcolor'] = self.annotation_fontcolor_entry.get_value()
