from typing import Union

from PyQt5 import QtWidgets
from flatcamGUI.GUIElements import RadioSet, FCCheckBox, FCButton, FCComboBox, FCEntry, FCSpinner, FCColorEntry

import gettext
import FlatCAMTranslation as fcTranslate
import builtins
fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class OptionUI:

    def __init__(self, option: str):
        self.option = option

    def add_to_grid(self, grid: QtWidgets.QGridLayout, row: int) -> int:
        """
        Adds the necessary widget to the grid, starting at the supplied row.
        Returns the number of rows used (normally 1)
        """
        raise NotImplementedError()

    def get_field(self):
        raise NotImplementedError()


class BasicOptionUI(OptionUI):
    """Abstract OptionUI that has a label on the left then some other widget on the right"""
    def __init__(self, option: str, label_text: str, label_tooltip: str):
        super().__init__(option=option)
        self.label_text = label_text
        self.label_tooltip = label_tooltip
        self.label_widget = self.build_label_widget()
        self.entry_widget = self.build_entry_widget()

    def build_label_widget(self) -> QtWidgets.QLabel:
        label_widget = QtWidgets.QLabel('%s:' % _(self.label_text))
        if self.label_tooltip is not None:
            label_widget.setToolTip(_(self.label_tooltip))
        return label_widget

    def build_entry_widget(self) -> QtWidgets.QWidget:
        raise NotImplementedError()

    def add_to_grid(self, grid: QtWidgets.QGridLayout, row: int) -> int:
        grid.addWidget(self.label_widget, row, 0)
        grid.addWidget(self.entry_widget, row, 1)
        return 1

    def get_field(self):
        return self.entry_widget


class RadioSetOptionUI(BasicOptionUI):

    def __init__(self, option: str, label_text: str, label_tooltip: str, choices: list, orientation='horizontal'):
        self.choices = choices
        self.orientation = orientation
        super().__init__(option=option, label_text=label_text, label_tooltip=label_tooltip)

    def build_entry_widget(self) -> QtWidgets.QWidget:
        return RadioSet(choices=self.choices, orientation=self.orientation)


class CheckboxOptionUI(OptionUI):

    def __init__(self, option: str, label_text: str, label_tooltip: str):
        super().__init__(option=option)
        self.label_text = label_text
        self.label_tooltip = label_tooltip
        self.checkbox_widget = self.build_checkbox_widget()

    def build_checkbox_widget(self):
        checkbox = FCCheckBox('%s' % _(self.label_text))
        checkbox.setToolTip(_(self.label_tooltip))
        return checkbox

    def add_to_grid(self, grid: QtWidgets.QGridLayout, row: int) -> int:
        grid.addWidget(self.checkbox_widget, row, 0, 1, 3)
        return 1

    def get_field(self):
        return self.checkbox_widget


class ComboboxOptionUI(BasicOptionUI):

    def __init__(self, option: str, label_text: str, label_tooltip: str, choices: list):
        self.choices = choices
        super().__init__(option=option, label_text=label_text, label_tooltip=label_tooltip)

    def build_entry_widget(self):
        combo = FCComboBox()
        for choice in self.choices:
            # don't translate the QCombo items as they are used in QSettings and identified by name
            combo.addItem(choice)
        return combo


class ColorOptionUI(BasicOptionUI):
    def build_entry_widget(self) -> QtWidgets.QWidget:
        return FCColorEntry()


class HeadingOptionUI(OptionUI):
    def __init__(self, label_text: str, label_tooltip: Union[str, None]):
        super().__init__(option="__heading")
        self.label_text = label_text
        self.label_tooltip = label_tooltip

    def build_heading_widget(self):
        heading = QtWidgets.QLabel('<b>%s</b>' % _(self.label_text))
        heading.setToolTip(_(self.label_tooltip))
        return heading

    def add_to_grid(self, grid: QtWidgets.QGridLayout, row: int) -> int:
        grid.addWidget(self.build_heading_widget(), row, 0, 1, 2)
        return 1

    def get_field(self):
        return None


class SeparatorOptionUI(OptionUI):

    def __init__(self):
        super().__init__(option="__separator")

    def build_separator_widget(self):
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.HLine)
        separator.setFrameShadow(QtWidgets.QFrame.Sunken)
        return separator

    def add_to_grid(self, grid: QtWidgets.QGridLayout, row: int) -> int:
        grid.addWidget(self.build_separator_widget(), row, 0, 1, 2)
        return 1

    def get_field(self):
        return None


class FullWidthButtonOptionUI(OptionUI):
    def __init__(self, option: str, label_text: str, label_tooltip: str):
        super().__init__(option=option)
        self.label_text = label_text
        self.label_tooltip = label_tooltip
        self.button_widget = self.build_button_widget()

    def build_button_widget(self):
        button = FCButton(_(self.label_text))
        button.setToolTip(_(self.label_tooltip))
        return button

    def add_to_grid(self, grid: QtWidgets.QGridLayout, row: int) -> int:
        grid.addWidget(self.button_widget, row, 0, 1, 3)
        return 1

    def get_field(self):
        return self.button_widget