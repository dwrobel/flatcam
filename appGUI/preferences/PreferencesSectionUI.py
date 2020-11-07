from typing import Dict
from PyQt5 import QtWidgets, QtCore

from appGUI.ColumnarFlowLayout import ColumnarFlowLayout
from appGUI.preferences.OptionUI import OptionUI
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI


class PreferencesSectionUI(QtWidgets.QWidget):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = ColumnarFlowLayout()  # QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)

        self.groups = self.build_groups()
        for group in self.groups:
            group.setMinimumWidth(250)
            self.layout.addWidget(group)

    def build_groups(self) -> [OptionsGroupUI]:
        return []

    def option_dict(self) -> Dict[str, OptionUI]:
        result = {}
        for group in self.groups:
            groupoptions = group.option_dict()
            result.update(groupoptions)
        return result

    def build_tab(self):
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidget(self)
        scroll_area.setWidgetResizable(True)
        return scroll_area

    def get_tab_id(self) -> str:
        raise NotImplementedError

    def get_tab_label(self) -> str:
        raise NotImplementedError
