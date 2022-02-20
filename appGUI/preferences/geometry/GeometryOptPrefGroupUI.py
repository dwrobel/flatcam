from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt

from appGUI.GUIElements import FCDoubleSpinner, FCLabel, FCGridLayout, FCFrame
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GeometryOptPrefGroupUI(OptionsGroupUI):
    def __init__(self, app, parent=None):
        # OptionsGroupUI.__init__(self, "Geometry Options Preferences", parent=parent)
        super(GeometryOptPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Options")))
        self.decimals = app.decimals
        self.options = app.options

        # #############################################################################################################
        # PARAMETERS Frame
        # #############################################################################################################
        self.cncjob_label = FCLabel('<span style="color:blue;"><b>%s</b></span>' % _("Parameters"))
        self.layout.addWidget(self.cncjob_label)

        param_frame = FCFrame()
        self.layout.addWidget(param_frame)

        param_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        param_frame.setLayout(param_grid)

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

        param_grid.addWidget(cutzlabel, 0, 0)
        param_grid.addWidget(self.cutz_entry, 0, 1)

        # self.layout.addStretch()
