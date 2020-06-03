from typing import Union, Sequence, List

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QSettings

from appGUI.GUIElements import RadioSet, FCCheckBox, FCButton, FCComboBox, FCEntry, FCSpinner, FCColorEntry, \
    FCSliderWithSpinner, FCDoubleSpinner, FloatEntry, FCTextArea

import gettext
import appTranslation as fcTranslate
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
    def __init__(self, option: str, label_text: str, label_tooltip: Union[str, None] = None,
                 label_bold: bool = False, label_color: Union[str, None] = None):
        super().__init__(option=option)
        self.label_text = label_text
        self.label_tooltip = label_tooltip
        self.label_bold = label_bold
        self.label_color = label_color
        self.label_widget = self.build_label_widget()
        self.entry_widget = self.build_entry_widget()

    def build_label_widget(self) -> QtWidgets.QLabel:
        fmt = "%s:"
        if self.label_bold:
            fmt = "<b>%s</b>" % fmt
        if self.label_color:
            fmt = "<span style=\"color:%s;\">%s</span>" % (self.label_color, fmt)
        label_widget = QtWidgets.QLabel(fmt % _(self.label_text))
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


class LineEntryOptionUI(BasicOptionUI):
    def build_entry_widget(self) -> QtWidgets.QWidget:
        return FCEntry()


# Not sure why this is needed over DoubleSpinnerOptionUI
class FloatEntryOptionUI(BasicOptionUI):
    def build_entry_widget(self) -> QtWidgets.QWidget:
        return FloatEntry()


class RadioSetOptionUI(BasicOptionUI):

    def __init__(self, option: str, label_text: str, choices: list, orientation='horizontal', **kwargs):
        self.choices = choices
        self.orientation = orientation
        super().__init__(option=option, label_text=label_text, **kwargs)

    def build_entry_widget(self) -> QtWidgets.QWidget:
        return RadioSet(choices=self.choices, orientation=self.orientation)


class TextAreaOptionUI(OptionUI):

    def __init__(self, option: str, label_text: str, label_tooltip: str):
        super().__init__(option=option)
        self.label_text = label_text
        self.label_tooltip = label_tooltip
        self.label_widget = self.build_label_widget()
        self.textarea_widget = self.build_textarea_widget()

    def build_label_widget(self):
        label = QtWidgets.QLabel("%s:" % _(self.label_text))
        label.setToolTip(_(self.label_tooltip))
        return label

    def build_textarea_widget(self):
        textarea = FCTextArea()
        textarea.setPlaceholderText(_(self.label_tooltip))

        qsettings = QSettings("Open Source", "FlatCAM")
        if qsettings.contains("textbox_font_size"):
            tb_fsize = qsettings.value('textbox_font_size', type=int)
        else:
            tb_fsize = 10
        font = QtGui.QFont()
        font.setPointSize(tb_fsize)
        textarea.setFont(font)

        return textarea

    def get_field(self):
        return self.textarea_widget

    def add_to_grid(self, grid: QtWidgets.QGridLayout, row: int) -> int:
        grid.addWidget(self.label_widget, row, 0, 1, 3)
        grid.addWidget(self.textarea_widget, row+1, 0, 1, 3)
        return 2


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

    def __init__(self, option: str, label_text: str, choices: Sequence, **kwargs):
        self.choices = choices
        super().__init__(option=option, label_text=label_text, **kwargs)

    def build_entry_widget(self):
        combo = FCComboBox()
        for choice in self.choices:
            # don't translate the QCombo items as they are used in QSettings and identified by name
            combo.addItem(choice)
        return combo


class ColorOptionUI(BasicOptionUI):
    def build_entry_widget(self) -> QtWidgets.QWidget:
        entry = FCColorEntry()
        return entry


class SliderWithSpinnerOptionUI(BasicOptionUI):
    def __init__(self, option: str, label_text: str, min_value=0, max_value=100, step=1, **kwargs):
        self.min_value = min_value
        self.max_value = max_value
        self.step = step
        super().__init__(option=option, label_text=label_text, **kwargs)

    def build_entry_widget(self) -> QtWidgets.QWidget:
        entry = FCSliderWithSpinner(min=self.min_value, max=self.max_value, step=self.step)
        return entry


class ColorAlphaSliderOptionUI(SliderWithSpinnerOptionUI):
    def __init__(self, applies_to: List[str], group, label_text: str, **kwargs):
        self.applies_to = applies_to
        self.group = group
        super().__init__(option="__color_alpha_slider", label_text=label_text, min_value=0, max_value=255, step=1,
                         **kwargs)
        self.get_field().valueChanged.connect(self._on_alpha_change)

    def add_to_grid(self, grid: QtWidgets.QGridLayout, row: int) -> int:
        for index, field in enumerate(self._get_target_fields()):
            field.entry.textChanged.connect(lambda value, i=index: self._on_target_change(target_index=i))
        return super().add_to_grid(grid, row)

    def _get_target_fields(self):
        return list(map(lambda n: self.group.option_dict()[n].get_field(), self.applies_to))

    def _on_target_change(self, target_index: int):
        field = self._get_target_fields()[target_index]
        color = field.get_value()
        alpha_part = color[7:]
        if len(alpha_part) != 2:
            return
        alpha = int(alpha_part, 16)
        if alpha < 0 or alpha > 255 or self.get_field().get_value() == alpha:
            return
        self.get_field().set_value(alpha)

    def _on_alpha_change(self):
        alpha = self.get_field().get_value()
        for field in self._get_target_fields():
            old_value = field.get_value()
            new_value = self._modify_color_alpha(old_value, alpha=alpha)
            field.set_value(new_value)

    @staticmethod
    def _modify_color_alpha(color: str, alpha: int):
        color_without_alpha = color[:7]
        if alpha > 255:
            return color_without_alpha + "FF"
        elif alpha < 0:
            return color_without_alpha + "00"
        else:
            hexalpha = hex(alpha)[2:]
            if len(hexalpha) == 1:
                hexalpha = "0" + hexalpha
            return color_without_alpha + hexalpha


class SpinnerOptionUI(BasicOptionUI):
    def __init__(self, option: str, label_text: str, min_value: int, max_value: int, step: int = 1, **kwargs):
        self.min_value = min_value
        self.max_value = max_value
        self.step = step
        super().__init__(option=option, label_text=label_text, **kwargs)

    def build_entry_widget(self) -> QtWidgets.QWidget:
        entry = FCSpinner()
        entry.set_range(self.min_value, self.max_value)
        entry.set_step(self.step)
        entry.setWrapping(True)
        return entry


class DoubleSpinnerOptionUI(BasicOptionUI):
    def __init__(self, option: str, label_text: str, step: float, decimals: int, min_value=None, max_value=None,
                 suffix=None, **kwargs):
        self.min_value = min_value
        self.max_value = max_value
        self.step = step
        self.suffix = suffix
        self.decimals = decimals
        super().__init__(option=option, label_text=label_text, **kwargs)

    def build_entry_widget(self) -> QtWidgets.QWidget:
        entry = FCDoubleSpinner(suffix=self.suffix)
        entry.set_precision(self.decimals)
        entry.setSingleStep(self.step)
        if self.min_value is None:
            self.min_value = entry.minimum()
        else:
            entry.setMinimum(self.min_value)
        if self.max_value is None:
            self.max_value = entry.maximum()
        else:
            entry.setMaximum(self.max_value)
        return entry


class HeadingOptionUI(OptionUI):
    def __init__(self, label_text: str, label_tooltip: Union[str, None] = None):
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

    @staticmethod
    def build_separator_widget():
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
    def __init__(self, option: str, label_text: str, label_tooltip: Union[str, None]):
        super().__init__(option=option)
        self.label_text = label_text
        self.label_tooltip = label_tooltip
        self.button_widget = self.build_button_widget()

    def build_button_widget(self):
        button = FCButton(_(self.label_text))
        if self.label_tooltip is not None:
            button.setToolTip(_(self.label_tooltip))
        return button

    def add_to_grid(self, grid: QtWidgets.QGridLayout, row: int) -> int:
        grid.addWidget(self.button_widget, row, 0, 1, 3)
        return 1

    def get_field(self):
        return self.button_widget
