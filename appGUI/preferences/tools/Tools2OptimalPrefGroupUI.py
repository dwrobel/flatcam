from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings

from appGUI.GUIElements import FCSpinner
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

settings = QSettings("Open Source", "FlatCAM")
if settings.contains("machinist"):
    machinist_setting = settings.value('machinist', type=int)
else:
    machinist_setting = 0


class Tools2OptimalPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):

        super(Tools2OptimalPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Optimal Tool Options")))
        self.decimals = decimals

        # ## Parameters
        self.optlabel = QtWidgets.QLabel("<b>%s:</b>" % _("Parameters"))
        self.optlabel.setToolTip(
            _("A tool to find the minimum distance between\n"
              "every two Gerber geometric elements")
        )
        self.layout.addWidget(self.optlabel)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)

        self.precision_sp = FCSpinner()
        self.precision_sp.set_range(2, 10)
        self.precision_sp.set_step(1)
        self.precision_sp.setWrapping(True)

        self.precision_lbl = QtWidgets.QLabel('%s:' % _("Precision"))
        self.precision_lbl.setToolTip(
            _("Number of decimals for the distances and coordinates in this tool.")
        )

        grid0.addWidget(self.precision_lbl, 0, 0)
        grid0.addWidget(self.precision_sp, 0, 1)

        self.layout.addStretch()
