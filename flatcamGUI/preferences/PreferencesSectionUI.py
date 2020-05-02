from typing import Dict

from PyQt5 import QtWidgets

from flatcamGUI.preferences.OptionUI import OptionUI
from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI


class PreferencesSectionUI(QtWidgets.QWidget):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)

        self.groups = self.build_groups()
        for group in self.groups:
            group.setMinimumWidth(250)
            self.layout.addWidget(group)

        self.layout.addStretch()

    def build_groups(self) -> [OptionsGroupUI]:
        return []

    def option_dict(self) -> Dict[str, OptionUI]:
        result = {}
        for group in self.groups:
            groupoptions = group.option_dict()
            result.update(groupoptions)
        return result