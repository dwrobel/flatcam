from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt

from appGUI.GUIElements import FCDoubleSpinner, FCCheckBox, OptionalInputSection, FCSpinner, FCComboBox, \
    NumericalEvalTupleEntry, FCLabel, FCGridLayout
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GeometryOptPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "Geometry Options Preferences", parent=parent)
        super(GeometryOptPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Geometry Options")))
        self.decimals = decimals

        # ------------------------------
        # ## Create CNC Job
        # ------------------------------
        self.cncjob_label = FCLabel('<b>%s:</b>' % _('Create CNCJob'))
        self.cncjob_label.setToolTip(
            _("Create a CNC Job object\n"
              "tracing the contours of this\n"
              "Geometry object.")
        )
        self.layout.addWidget(self.cncjob_label)

        grid1 = FCGridLayout(v_spacing=5, h_spacing=3)
        self.layout.addLayout(grid1)
        grid1.setColumnStretch(0, 0)
        grid1.setColumnStretch(1, 1)

        # Cut Z
        cutzlabel = FCLabel('%s:' % _('Cut Z'))
        cutzlabel.setToolTip(
            _("Cutting depth (negative)\n"
              "below the copper surface.")
        )
        self.cutz_entry = FCDoubleSpinner()
        self.cutz_entry.set_range(-10000.0000, 10000.0000)

        self.cutz_entry.set_precision(self.decimals)
        self.cutz_entry.setSingleStep(0.1)
        self.cutz_entry.setWrapping(True)

        grid1.addWidget(cutzlabel, 0, 0)
        grid1.addWidget(self.cutz_entry, 0, 1)

        self.layout.addStretch()
