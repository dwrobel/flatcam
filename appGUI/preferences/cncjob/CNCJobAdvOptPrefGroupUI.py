from PyQt6 import QtWidgets

from appGUI.GUIElements import FCComboBox, FCSpinner, FCColorEntry, FCLabel, FCGridLayout
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI
import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class CNCJobAdvOptPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "CNC Job Advanced Options Preferences", parent=None)
        super(CNCJobAdvOptPrefGroupUI, self).__init__(self, parent=parent)
        self.decimals = decimals

        self.setTitle(str(_("CNC Job Adv. Options")))

        grid0 = FCGridLayout(v_spacing=3)
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        self.layout.addLayout(grid0)

        # ## Export G-Code
        self.export_gcode_label = FCLabel("<b>%s:</b>" % _("Parameters"))
        self.export_gcode_label.setToolTip(
            _("Export and save G-Code to\n"
              "make this object to a file.")
        )
        grid0.addWidget(self.export_gcode_label, 0, 0, 1, 2)

        # Annotation Font Size
        self.annotation_fontsize_label = FCLabel('%s:' % _("Annotation Size"))
        self.annotation_fontsize_label.setToolTip(
            _("The font size of the annotation text. In pixels.")
        )
        self.annotation_fontsize_sp = FCSpinner()
        self.annotation_fontsize_sp.set_range(0, 9999)

        grid0.addWidget(self.annotation_fontsize_label, 2, 0)
        grid0.addWidget(self.annotation_fontsize_sp, 2, 1)

        # Annotation Font Color
        self.annotation_color_label = FCLabel('%s:' % _('Annotation Color'))
        self.annotation_color_label.setToolTip(
            _("Set the font color for the annotation texts.")
        )
        self.annotation_fontcolor_entry = FCColorEntry()

        grid0.addWidget(self.annotation_color_label, 4, 0)
        grid0.addWidget(self.annotation_fontcolor_entry, 4, 1)

        self.layout.addStretch(1)

        self.annotation_fontcolor_entry.editingFinished.connect(self.on_annotation_fontcolor_entry)

    def on_annotation_fontcolor_entry(self):
        self.app.defaults['cncjob_annotation_fontcolor'] = self.annotation_fontcolor_entry.get_value()
