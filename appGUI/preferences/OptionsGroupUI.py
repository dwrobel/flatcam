# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File by:  David Robertson (c)                            #
# Date:     5/2020                                         #
# License:  MIT Licence                                    #
# ##########################################################

from typing import Dict

from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings

import gettext
import appTranslation as fcTranslate
import builtins

from appGUI.preferences.OptionUI import OptionUI

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

settings = QSettings("Open Source", "FlatCAM")
if settings.contains("machinist"):
    machinist_setting = settings.value('machinist', type=int)
else:
    machinist_setting = 0


class OptionsGroupUI(QtWidgets.QGroupBox):
    app = None

    def __init__(self, title, parent=None):
        # QtGui.QGroupBox.__init__(self, title, parent=parent)
        super(OptionsGroupUI, self).__init__()
        self.setStyleSheet("""
        QGroupBox
        {
            font-size: 16px;
            font-weight: bold;
        }
        """)

        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

    def option_dict(self) -> Dict[str, OptionUI]:
        # FIXME!
        return {}


class OptionsGroupUI2(OptionsGroupUI):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.grid = QtWidgets.QGridLayout()
        self.layout.addLayout(self.grid)
        self.grid.setColumnStretch(0, 0)
        self.grid.setColumnStretch(1, 1)

        self.options = self.build_options()

        row = 0
        for option in self.options:
            row += option.add_to_grid(grid=self.grid, row=row)

        self.layout.addStretch()

    def build_options(self) -> [OptionUI]:
        return []

    def option_dict(self) -> Dict[str, OptionUI]:
        result = {}
        for optionui in self.options:
            result[optionui.option] = optionui
        return result
