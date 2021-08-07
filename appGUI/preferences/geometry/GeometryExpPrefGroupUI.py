from PyQt6 import QtWidgets, QtCore

from appGUI.GUIElements import FCLabel, FCComboBox, FCGridLayout
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI
import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GeometryExpPrefGroupUI(OptionsGroupUI):

    def __init__(self, decimals=4, parent=None):
        super(GeometryExpPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Geometry Export")))
        self.decimals = decimals

        # Plot options
        self.export_options_label = FCLabel("<b>%s:</b>" % _("Export Options"))
        self.export_options_label.setToolTip(
            _("The parameters set here are used in the file exported\n"
              "when using the File -> Export -> Export DXF menu entry.")
        )
        self.layout.addWidget(self.export_options_label)

        grid0 = FCGridLayout(v_spacing=5, h_spacing=3)
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        self.layout.addLayout(grid0)

        # Excellon non-decimal format
        self.dxf_format_label = FCLabel("%s:" % _("Format"))
        self.dxf_format_label.setToolTip(
            _("Autodesk DXF Format used when exporting Geometry as DXF.")
        )

        self.dxf_format_combo = FCComboBox()
        self.dxf_format_combo.addItems(['R12', 'R2000', 'R2004', 'R2007', 'R2010', 'R2013', 'R2018'])

        grid0.addWidget(self.dxf_format_label, 0, 0)
        grid0.addWidget(self.dxf_format_combo, 0, 1)
