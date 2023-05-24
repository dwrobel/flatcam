
from PyQt6 import QtWidgets

from appGUI.GUIElements import FCSpinner, FCLabel, GLay, FCFrame
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class Tools2OptimalPrefGroupUI(OptionsGroupUI):
    def __init__(self, app, parent=None):

        super(Tools2OptimalPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Optimal Plugin")))
        self.decimals = app.decimals
        self.options = app.options

        # #############################################################################################################
        # Parameters Frame
        # #############################################################################################################
        self.optlabel = FCLabel('%s' % _("Parameters"), color='blue', bold=True)
        self.optlabel.setToolTip(
            _("A tool to find the minimum distance between\n"
              "every two Gerber geometric elements")
        )
        self.layout.addWidget(self.optlabel)

        par_frame = FCFrame()
        self.layout.addWidget(par_frame)

        param_grid = GLay(v_spacing=5, h_spacing=3)
        par_frame.setLayout(param_grid)

        self.precision_sp = FCSpinner()
        self.precision_sp.set_range(2, 10)
        self.precision_sp.set_step(1)
        self.precision_sp.setWrapping(True)

        self.precision_lbl = FCLabel('%s:' % _("Precision"))
        self.precision_lbl.setToolTip(
            _("Number of decimals for the distances and coordinates in this tool.")
        )

        param_grid.addWidget(self.precision_lbl, 0, 0)
        param_grid.addWidget(self.precision_sp, 0, 1)

        self.layout.addStretch()
