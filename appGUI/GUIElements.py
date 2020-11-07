# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
# ##########################################################

# ##########################################################
# File Modified (major mod): Marius Adrian Stanciu         #
# Date: 3/10/2019                                          #
# ##########################################################

from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal
from PyQt5.QtWidgets import QTextEdit, QCompleter, QAction
from PyQt5.QtGui import QKeySequence, QTextCursor

from copy import copy
import re
import logging
import html
import sys

import gettext
import appTranslation as fcTranslate
import builtins

log = logging.getLogger('base')

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

EDIT_SIZE_HINT = 70


class RadioSet(QtWidgets.QWidget):
    activated_custom = QtCore.pyqtSignal(str)

    def __init__(self, choices, orientation='horizontal', parent=None, stretch=None):
        """
        The choices are specified as a list of dictionaries containing:

        * 'label': Shown in the UI
        * 'value': The value returned is selected

        :param choices: List of choices. See description.
        :param orientation: 'horizontal' (default) of 'vertical'.
        :param parent: Qt parent widget.
        :type choices: list
        """
        super(RadioSet, self).__init__(parent)
        self.choices = copy(choices)
        if orientation == 'horizontal':
            layout = QtWidgets.QHBoxLayout()
        else:
            layout = QtWidgets.QVBoxLayout()

        group = QtWidgets.QButtonGroup(self)

        for choice in self.choices:
            choice['radio'] = QtWidgets.QRadioButton(choice['label'])
            group.addButton(choice['radio'])
            layout.addWidget(choice['radio'], stretch=0)
            choice['radio'].toggled.connect(self.on_toggle)

        layout.setContentsMargins(0, 0, 0, 0)

        if stretch is False:
            pass
        else:
            layout.addStretch()

        self.setLayout(layout)

        self.group_toggle_fn = lambda: None

    def on_toggle(self):
        # log.debug("Radio toggled")
        radio = self.sender()
        if radio.isChecked():
            self.group_toggle_fn()
            ret_val = str(self.get_value())
            self.activated_custom.emit(ret_val)
        return

    def get_value(self):
        for choice in self.choices:
            if choice['radio'].isChecked():
                return choice['value']
        log.error("No button was toggled in RadioSet.")
        return None

    def set_value(self, val):
        for choice in self.choices:
            if choice['value'] == val:
                choice['radio'].setChecked(True)
                return
        log.error("Value given is not part of this RadioSet: %s" % str(val))

    def setOptionsDisabled(self, options: list, val: bool) -> None:
        for option in self.choices:
            if option['label'] in options:
                option['radio'].setDisabled(val)


# class RadioGroupChoice(QtWidgets.QWidget):
#     def __init__(self, label_1, label_2, to_check, hide_list, show_list, parent=None):
#         """
#         The choices are specified as a list of dictionaries containing:
#
#         * 'label': Shown in the UI
#         * 'value': The value returned is selected
#
#         :param choices: List of choices. See description.
#         :param orientation: 'horizontal' (default) of 'vertical'.
#         :param parent: Qt parent widget.
#         :type choices: list
#         """
#         super().__init__(parent)
#
#         group = QtGui.QButtonGroup(self)
#
#         self.lbl1 = label_1
#         self.lbl2 = label_2
#         self.hide_list = hide_list
#         self.show_list = show_list
#
#         self.btn1 = QtGui.QRadioButton(str(label_1))
#         self.btn2 = QtGui.QRadioButton(str(label_2))
#         group.addButton(self.btn1)
#         group.addButton(self.btn2)
#
#         if to_check == 1:
#             self.btn1.setChecked(True)
#         else:
#             self.btn2.setChecked(True)
#
#         self.btn1.toggled.connect(lambda: self.btn_state(self.btn1))
#         self.btn2.toggled.connect(lambda: self.btn_state(self.btn2))
#
#     def btn_state(self, btn):
#         if btn.text() == self.lbl1:
#             if btn.isChecked() is True:
#                 self.show_widgets(self.show_list)
#                 self.hide_widgets(self.hide_list)
#             else:
#                 self.show_widgets(self.hide_list)
#                 self.hide_widgets(self.show_list)
#
#     def hide_widgets(self, lst):
#         for wgt in lst:
#             wgt.hide()
#
#     def show_widgets(self, lst):
#         for wgt in lst:
#             wgt.show()


class FCTree(QtWidgets.QTreeWidget):
    resize_sig = QtCore.pyqtSignal()

    def __init__(self, parent=None, columns=2, header_hidden=True, extended_sel=False, protected_column=None):
        super(FCTree, self).__init__(parent)

        self.setColumnCount(columns)
        self.setHeaderHidden(header_hidden)
        self.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Expanding)

        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Inactive, QtGui.QPalette.Highlight,
                         palette.color(QtGui.QPalette.Active, QtGui.QPalette.Highlight))

        # make inactive rows text some color as active; may be useful in the future
        # palette.setColor(QtGui.QPalette.Inactive, QtGui.QPalette.HighlightedText,
        #                  palette.color(QtGui.QPalette.Active, QtGui.QPalette.HighlightedText))
        self.setPalette(palette)

        if extended_sel:
            self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        self.protected_column = protected_column
        self.itemDoubleClicked.connect(self.on_double_click)
        self.header().sectionDoubleClicked.connect(self.on_header_double_click)
        self.resize_sig.connect(self.on_resize)

    def on_double_click(self, item, column):
        # from here: https://stackoverflow.com/questions/2801959/making-only-one-column-of-a-qtreewidgetitem-editable
        tmp_flags = item.flags()
        if self.is_editable(column):
            item.setFlags(tmp_flags | QtCore.Qt.ItemIsEditable)
        elif tmp_flags & QtCore.Qt.ItemIsEditable:
            item.setFlags(tmp_flags ^ QtCore.Qt.ItemIsEditable)

    def on_header_double_click(self, column):
        header = self.header()
        header.setSectionResizeMode(column, QtWidgets.QHeaderView.ResizeToContents)
        width = header.sectionSize(column)
        header.setSectionResizeMode(column, QtWidgets.QHeaderView.Interactive)
        header.resizeSection(column, width)

    def is_editable(self, tested_col):
        try:
            ret_val = False if tested_col in self.protected_column else True
        except TypeError:
            ret_val = False
        return ret_val

    def addParent(self, parent, title, expanded=False, color=None, font=None):
        item = QtWidgets.QTreeWidgetItem(parent, [title])
        item.setChildIndicatorPolicy(QtWidgets.QTreeWidgetItem.ShowIndicator)
        item.setExpanded(expanded)
        if color is not None:
            # item.setTextColor(0, color) # PyQt4
            item.setForeground(0, QtGui.QBrush(color))
        if font is not None:
            item.setFont(0, font)
        return item

    def addParentEditable(self, parent, title, color=None, font=None, font_items=None, editable=False):
        item = QtWidgets.QTreeWidgetItem(parent)
        item.setChildIndicatorPolicy(QtWidgets.QTreeWidgetItem.DontShowIndicator)
        if editable:
            item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)

        item.setFlags(item.flags() | QtCore.Qt.ItemIsSelectable)

        for t in range(len(title)):
            item.setText(t, title[t])

        if color is not None:
            # item.setTextColor(0, color) # PyQt4
            item.setForeground(0, QtGui.QBrush(color))

        if font and font_items:
            try:
                for fi in font_items:
                    item.setFont(fi, font)
            except TypeError:
                item.setFont(font_items, font)
        elif font:
            item.setFont(0, font)
        return item

    def addChild(self, parent, title, column1=None, font=None, font_items=None, editable=False):
        item = QtWidgets.QTreeWidgetItem(parent)
        if editable:
            item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)

        item.setText(0, str(title[0]))
        if column1 is not None:
            item.setText(1, str(title[1]))
        if font and font_items:
            try:
                for fi in font_items:
                    item.setFont(fi, font)
            except TypeError:
                item.setFont(font_items, font)

    def resizeEvent(self, event):
        """ Resize all sections to content and user interactive """

        super(FCTree, self).resizeEvent(event)
        self.on_resize()

    def on_resize(self):
        header = self.header()
        for column in range(header.count()):
            header.setSectionResizeMode(column, QtWidgets.QHeaderView.ResizeToContents)
            width = header.sectionSize(column)
            header.setSectionResizeMode(column, QtWidgets.QHeaderView.Interactive)
            header.resizeSection(column, width)


class FCLineEdit(QtWidgets.QLineEdit):

    def __init__(self, *args, **kwargs):
        super(FCLineEdit, self).__init__(*args, **kwargs)

        self.menu = None

    def contextMenuEvent(self, event):
        self.menu = QtWidgets.QMenu()

        # UNDO
        undo_action = QAction('%s\t%s' % (_("Undo"), _('Ctrl+Z')), self)
        self.menu.addAction(undo_action)
        undo_action.triggered.connect(self.undo)
        if self.isUndoAvailable() is False:
            undo_action.setDisabled(True)

        # REDO
        redo_action = QAction('%s\t%s' % (_("Redo"), _('Ctrl+Y')), self)
        self.menu.addAction(redo_action)
        redo_action.triggered.connect(self.redo)
        if self.isRedoAvailable() is False:
            redo_action.setDisabled(True)

        self.menu.addSeparator()

        # CUT
        cut_action = QAction('%s\t%s' % (_("Cut"), _('Ctrl+X')), self)
        self.menu.addAction(cut_action)
        cut_action.triggered.connect(self.cut_text)
        if not self.hasSelectedText():
            cut_action.setDisabled(True)

        # COPY
        copy_action = QAction('%s\t%s' % (_("Copy"), _('Ctrl+C')), self)
        self.menu.addAction(copy_action)
        copy_action.triggered.connect(self.copy_text)
        if not self.hasSelectedText():
            copy_action.setDisabled(True)

        # PASTE
        paste_action = QAction('%s\t%s' % (_("Paste"), _('Ctrl+V')), self)
        self.menu.addAction(paste_action)
        paste_action.triggered.connect(self.paste_text)

        # DELETE
        delete_action = QAction('%s\t%s' % (_("Delete"), _('Del')), self)
        self.menu.addAction(delete_action)
        delete_action.triggered.connect(self.del_)

        self.menu.addSeparator()

        # SELECT ALL
        sel_all_action = QAction('%s\t%s' % (_("Select All"), _('Ctrl+A')), self)
        self.menu.addAction(sel_all_action)
        sel_all_action.triggered.connect(self.selectAll)

        self.menu.exec_(event.globalPos())

    def cut_text(self):
        clipboard = QtWidgets.QApplication.clipboard()

        txt = self.selectedText()
        clipboard.clear()
        clipboard.setText(txt)

        self.del_()

    def copy_text(self):
        clipboard = QtWidgets.QApplication.clipboard()

        txt = self.selectedText()
        clipboard.clear()
        clipboard.setText(txt)

    def paste_text(self):
        clipboard = QtWidgets.QApplication.clipboard()

        txt = clipboard.text()
        self.insert(txt)


class LengthEntry(FCLineEdit):
    def __init__(self, output_units='IN', decimals=None, parent=None):
        super(LengthEntry, self).__init__(parent)

        self.output_units = output_units
        self.format_re = re.compile(r"^([^\s]+)(?:\s([a-zA-Z]+))?$")

        # Unit conversion table OUTPUT-INPUT
        self.scales = {
            'IN': {'IN': 1.0,
                   'MM': 1 / 25.4},
            'MM': {'IN': 25.4,
                   'MM': 1.0}
        }
        self.readyToEdit = True
        self.editingFinished.connect(self.on_edit_finished)
        self.decimals = decimals if decimals is not None else 4

    def on_edit_finished(self):
        self.clearFocus()

    def mousePressEvent(self, e, Parent=None):
        super(LengthEntry, self).mousePressEvent(e)  # required to deselect on 2e click
        if self.readyToEdit:
            self.selectAll()
            self.readyToEdit = False

    def focusOutEvent(self, e):
        # don't focus out if the user requests an popup menu
        if e.reason() != QtCore.Qt.PopupFocusReason:
            super(LengthEntry, self).focusOutEvent(e)  # required to remove cursor on focusOut
            self.deselect()
            self.readyToEdit = True

    def returnPressed(self, *args, **kwargs):
        val = self.get_value()
        if val is not None:
            self.set_text(str(val))
        else:
            log.warning("Could not interpret entry: %s" % self.get_text())

    def get_value(self):
        raw = str(self.text()).strip(' ')
        # match = self.format_re.search(raw)

        try:
            units = raw[-2:]
            units = self.scales[self.output_units][units.upper()]
            value = raw[:-2]
            return float(eval(value)) * units
        except IndexError:
            value = raw
            return float(eval(value))
        except KeyError:
            value = raw
            return float(eval(value))
        except Exception:
            log.warning("Could not parse value in entry: %s" % str(raw))
            return None

    def set_value(self, val, decimals=None):
        dec_digits = decimals if decimals is not None else self.decimals
        self.setText(str('%.*f' % (dec_digits, val)))

    def sizeHint(self):
        default_hint_size = super(LengthEntry, self).sizeHint()
        return QtCore.QSize(EDIT_SIZE_HINT, default_hint_size.height())


class FloatEntry(FCLineEdit):
    def __init__(self, decimals=None, parent=None):
        super(FloatEntry, self).__init__(parent)
        self.readyToEdit = True
        self.editingFinished.connect(self.on_edit_finished)
        self.decimals = decimals if decimals is not None else 4

    def on_edit_finished(self):
        self.clearFocus()

    def mousePressEvent(self, e, Parent=None):
        super(FloatEntry, self).mousePressEvent(e)  # required to deselect on 2e click
        if self.readyToEdit is True:
            self.selectAll()
            self.readyToEdit = False

    def focusOutEvent(self, e):
        # don't focus out if the user requests an popup menu
        if e.reason() != QtCore.Qt.PopupFocusReason:
            super(FloatEntry, self).focusOutEvent(e)  # required to remove cursor on focusOut
            self.deselect()
            self.readyToEdit = True

    def returnPressed(self, *args, **kwargs):
        val = self.get_value()
        if val is not None:
            self.set_text(str(val))
        else:
            log.warning("Could not interpret entry: %s" % self.text())

    def get_value(self):
        raw = str(self.text()).strip(' ')

        try:
            evaled = eval(raw)
            return float(evaled)
        except Exception as e:
            if raw != '':
                log.error("Could not evaluate val: %s, error: %s" % (str(raw), str(e)))
            return None

    def set_value(self, val, decimals=None):
        dig_digits = decimals if decimals is not None else self.decimals
        if val is not None:
            self.setText("%.*f" % (dig_digits, float(val)))
        else:
            self.setText("")

    def sizeHint(self):
        default_hint_size = super(FloatEntry, self).sizeHint()
        return QtCore.QSize(EDIT_SIZE_HINT, default_hint_size.height())


class FloatEntry2(FCLineEdit):
    def __init__(self, decimals=None, parent=None):
        super(FloatEntry2, self).__init__(parent)
        self.readyToEdit = True
        self.editingFinished.connect(self.on_edit_finished)
        self.decimals = decimals if decimals is not None else 4

    def on_edit_finished(self):
        self.clearFocus()

    def mousePressEvent(self, e, Parent=None):
        super(FloatEntry2, self).mousePressEvent(e)  # required to deselect on 2e click
        if self.readyToEdit:
            self.selectAll()
            self.readyToEdit = False

    def focusOutEvent(self, e):
        # don't focus out if the user requests an popup menu
        if e.reason() != QtCore.Qt.PopupFocusReason:
            super(FloatEntry2, self).focusOutEvent(e)  # required to remove cursor on focusOut
            self.deselect()
            self.readyToEdit = True

    def get_value(self):
        raw = str(self.text()).strip(' ')

        try:
            evaled = eval(raw)
            return float(evaled)
        except Exception as e:
            if raw != '':
                log.error("Could not evaluate val: %s, error: %s" % (str(raw), str(e)))
            return None

    def set_value(self, val, decimals=None):
        dig_digits = decimals if decimals is not None else self.decimals
        self.setText("%.*f" % (dig_digits, val))

    def sizeHint(self):
        default_hint_size = super(FloatEntry2, self).sizeHint()
        return QtCore.QSize(EDIT_SIZE_HINT, default_hint_size.height())


class IntEntry(FCLineEdit):

    def __init__(self, parent=None, allow_empty=False, empty_val=None):
        super(IntEntry, self).__init__(parent)
        self.allow_empty = allow_empty
        self.empty_val = empty_val
        self.readyToEdit = True
        self.editingFinished.connect(self.on_edit_finished)

    def on_edit_finished(self):
        self.clearFocus()

    def mousePressEvent(self, e, Parent=None):
        super(IntEntry, self).mousePressEvent(e)  # required to deselect on 2e click
        if self.readyToEdit:
            self.selectAll()
            self.readyToEdit = False

    def focusOutEvent(self, e):
        # don't focus out if the user requests an popup menu
        if e.reason() != QtCore.Qt.PopupFocusReason:
            super(IntEntry, self).focusOutEvent(e)  # required to remove cursor on focusOut
            self.deselect()
            self.readyToEdit = True

    def get_value(self):

        if self.allow_empty:
            if str(self.text()) == "":
                return self.empty_val
        # make the text() first a float and then int because if text is a float type,
        # the int() can't convert directly a "text float" into a int type.
        ret_val = float(self.text())
        ret_val = int(ret_val)
        return ret_val

    def set_value(self, val):

        if val == self.empty_val and self.allow_empty:
            self.setText("")
            return

        self.setText(str(val))

    def sizeHint(self):
        default_hint_size = super(IntEntry, self).sizeHint()
        return QtCore.QSize(EDIT_SIZE_HINT, default_hint_size.height())


class FCEntry(FCLineEdit):
    def __init__(self, decimals=None, alignment=None, border_color=None, parent=None):
        super(FCEntry, self).__init__(parent)
        self.readyToEdit = True
        self.editingFinished.connect(self.on_edit_finished)
        self.decimals = decimals if decimals is not None else 4

        if border_color:
            self.setStyleSheet("QLineEdit {border: 1px solid %s;}" % border_color)

        if alignment:
            if alignment == 'center':
                align_val = QtCore.Qt.AlignHCenter
            elif alignment == 'right':
                align_val = QtCore.Qt.AlignRight
            else:
                align_val = QtCore.Qt.AlignLeft
            self.setAlignment(align_val)

    def on_edit_finished(self):
        self.clearFocus()

    def mousePressEvent(self, e, parent=None):
        super(FCEntry, self).mousePressEvent(e)  # required to deselect on 2e click
        if self.readyToEdit:
            self.selectAll()
            self.readyToEdit = False

    def focusOutEvent(self, e):
        if e.reason() != QtCore.Qt.PopupFocusReason:
            super(FCEntry, self).focusOutEvent(e)  # required to remove cursor on focusOut
            self.deselect()
            self.readyToEdit = True

    def get_value(self):
        return str(self.text())

    def set_value(self, val, decimals=None):
        decimal_digits = decimals if decimals is not None else self.decimals
        if type(val) is float:
            self.setText('%.*f' % (decimal_digits, val))
        elif val is None:
            self.setText('')
        else:
            self.setText(str(val))

    def sizeHint(self):
        default_hint_size = super(FCEntry, self).sizeHint()
        return QtCore.QSize(EDIT_SIZE_HINT, default_hint_size.height())


class FCEntry2(FCEntry):
    def __init__(self, parent=None):
        super(FCEntry2, self).__init__(parent)

    def set_value(self, val, decimals=4):
        try:
            fval = float(val)
        except ValueError:
            return
        self.setText('%.*f' % (decimals, fval))


class FCEntry3(FCEntry):
    def __init__(self, parent=None):
        super(FCEntry3, self).__init__(parent)

    def set_value(self, val, decimals=4):
        try:
            fval = float(val)
        except ValueError:
            return
        self.setText('%.*f' % (decimals, fval))

    def get_value(self):
        value = str(self.text()).strip(' ')

        try:
            return float(eval(value))
        except Exception as e:
            log.warning("Could not parse value in entry: %s" % str(e))
            return None


class EvalEntry(FCLineEdit):
    def __init__(self, border_color=None, parent=None):
        super(EvalEntry, self).__init__(parent)
        self.readyToEdit = True

        if border_color:
            self.setStyleSheet("QLineEdit {border: 1px solid %s;}" % border_color)

        self.editingFinished.connect(self.on_edit_finished)

    def on_edit_finished(self):
        self.clearFocus()

    def mousePressEvent(self, e, parent=None):
        super(EvalEntry, self).mousePressEvent(e)  # required to deselect on 2e click
        if self.readyToEdit:
            self.selectAll()
            self.readyToEdit = False

    def focusOutEvent(self, e):
        if e.reason() != QtCore.Qt.PopupFocusReason:
            super(EvalEntry, self).focusOutEvent(e)  # required to remove cursor on focusOut
            self.deselect()
            self.readyToEdit = True

    def returnPressed(self, *args, **kwargs):
        val = self.get_value()
        if val is not None:
            self.setText(str(val))
        else:
            log.warning("Could not interpret entry: %s" % self.get_text())

    def get_value(self):
        raw = str(self.text()).strip(' ')
        try:
            evaled = eval(raw)
        except Exception as e:
            if raw != '':
                log.error("Could not evaluate val: %s, error: %s" % (str(raw), str(e)))
            return None
        return evaled

    def set_value(self, val):
        self.setText(str(val))

    def sizeHint(self):
        default_hint_size = super(EvalEntry, self).sizeHint()
        return QtCore.QSize(EDIT_SIZE_HINT, default_hint_size.height())


class EvalEntry2(FCLineEdit):
    def __init__(self, parent=None):
        super(EvalEntry2, self).__init__(parent)
        self.readyToEdit = True
        self.editingFinished.connect(self.on_edit_finished)

    def on_edit_finished(self):
        self.clearFocus()

    def mousePressEvent(self, e, parent=None):
        super(EvalEntry2, self).mousePressEvent(e)  # required to deselect on 2e click
        if self.readyToEdit:
            self.selectAll()
            self.readyToEdit = False

    def focusOutEvent(self, e):
        if e.reason() != QtCore.Qt.PopupFocusReason:
            super(EvalEntry2, self).focusOutEvent(e)  # required to remove cursor on focusOut
            self.deselect()
            self.readyToEdit = True

    def get_value(self):
        raw = str(self.text()).strip(' ')

        try:
            evaled = eval(raw)
        except Exception as e:
            if raw != '':
                log.error("Could not evaluate val: %s, error: %s" % (str(raw), str(e)))
            return None
        return evaled

    def set_value(self, val):
        self.setText(str(val))

    def sizeHint(self):
        default_hint_size = super(EvalEntry2, self).sizeHint()
        return QtCore.QSize(EDIT_SIZE_HINT, default_hint_size.height())


class NumericalEvalEntry(FCEntry):
    """
    Will evaluate the input and return a value. Accepts only float numbers and formulas using the operators: /,*,+,-,%
    """

    def __init__(self, border_color=None):
        super().__init__(border_color=border_color)

        regex = QtCore.QRegExp("[0-9\/\*\+\-\%\.\,\s]*")
        validator = QtGui.QRegExpValidator(regex, self)
        self.setValidator(validator)

    def get_value(self):
        raw = str(self.text()).strip(' ')
        raw = raw.replace(',', '.')
        try:
            evaled = eval(raw)
        except Exception as e:
            if raw != '':
                log.error("Could not evaluate val: %s, error: %s" % (str(raw), str(e)))
            return None
        return evaled


class NumericalEvalTupleEntry(EvalEntry):
    """
    Will return a text value. Accepts only float numbers and formulas using the operators: /,*,+,-,%
    """

    def __init__(self, border_color=None):
        super().__init__(border_color=border_color)

        regex = QtCore.QRegExp("[0-9\/\*\+\-\%\.\s\,\[\]\(\)]*")
        validator = QtGui.QRegExpValidator(regex, self)
        self.setValidator(validator)

    def get_value(self):
        raw = str(self.text()).strip(' ')
        try:
            evaled = eval(raw)
        except Exception as e:
            if raw != '':
                log.error("Could not evaluate val: %s, error: %s" % (str(raw), str(e)))
            return None
        return evaled


class FCColorEntry(QtWidgets.QFrame):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.entry = FCEntry()
        regex = QtCore.QRegExp("[#A-Fa-f0-9]*")
        validator = QtGui.QRegExpValidator(regex, self.entry)
        self.entry.setValidator(validator)

        self.button = QtWidgets.QPushButton()
        self.button.setFixedSize(15, 15)
        self.button.setStyleSheet("border-color: dimgray;")

        self.layout = QtWidgets.QHBoxLayout()
        self.layout.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.entry)
        self.layout.addWidget(self.button)
        self.setLayout(self.layout)

        self.entry.editingFinished.connect(self._sync_button_color)
        self.button.clicked.connect(self._on_button_clicked)

        self.editingFinished = self.entry.editingFinished

    def get_value(self) -> str:
        return self.entry.get_value()

    def set_value(self, value: str):
        self.entry.set_value(value)
        self._sync_button_color()

    def _sync_button_color(self):
        value = self.get_value()
        self.button.setStyleSheet("background-color:%s;" % self._extract_color(value))

    def _on_button_clicked(self):
        value = self.entry.get_value()
        current_color = QtGui.QColor(self._extract_color(value))

        color_dialog = QtWidgets.QColorDialog()
        selected_color = color_dialog.getColor(initial=current_color, options=QtWidgets.QColorDialog.ShowAlphaChannel)

        if selected_color.isValid() is False:
            return

        new_value = str(selected_color.name()) + self._extract_alpha(value)
        self.set_value(new_value)

    def _extract_color(self, value: str) -> str:
        return value[:7]

    def _extract_alpha(self, value: str) -> str:
        return value[7:9]


class FCSliderWithSpinner(QtWidgets.QFrame):

    def __init__(self, min=0, max=100, step=1, **kwargs):
        super().__init__(**kwargs)

        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setMinimum(min)
        self.slider.setMaximum(max)
        self.slider.setSingleStep(step)

        self.spinner = FCSpinner()
        self.spinner.set_range(min, max)
        self.spinner.set_step(step)
        self.spinner.setMinimumWidth(70)

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.spinner.setSizePolicy(sizePolicy)

        self.layout = QtWidgets.QHBoxLayout()
        self.layout.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.slider)
        self.layout.addWidget(self.spinner)
        self.setLayout(self.layout)

        self.slider.valueChanged.connect(self._on_slider)
        self.spinner.valueChanged.connect(self._on_spinner)

        self.valueChanged = self.spinner.valueChanged

    def get_value(self) -> int:
        return self.spinner.get_value()

    def set_value(self, value: int):
        self.spinner.set_value(value)

    def _on_spinner(self):
        spinner_value = self.spinner.value()
        self.slider.setValue(spinner_value)

    def _on_slider(self):
        slider_value = self.slider.value()
        self.spinner.set_value(slider_value)


class FCSpinner(QtWidgets.QSpinBox):
    returnPressed = QtCore.pyqtSignal()
    confirmation_signal = QtCore.pyqtSignal(bool, float, float)

    def __init__(self, suffix=None, alignment=None, parent=None, callback=None, policy=True):
        super(FCSpinner, self).__init__(parent)
        self.readyToEdit = True

        self.editingFinished.connect(self.on_edit_finished)
        if callback:
            self.confirmation_signal.connect(callback)

        self.lineEdit().installEventFilter(self)

        if suffix:
            self.setSuffix(' %s' % str(suffix))

        if alignment:
            if alignment == 'center':
                align_val = QtCore.Qt.AlignHCenter
            elif alignment == 'right':
                align_val = QtCore.Qt.AlignRight
            else:
                align_val = QtCore.Qt.AlignLeft
            self.setAlignment(align_val)

        self.prev_readyToEdit = True
        self.menu = None

        if policy:
            sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
            self.setSizePolicy(sizePolicy)

    def eventFilter(self, object, event):
        if event.type() == QtCore.QEvent.MouseButtonPress and self.prev_readyToEdit is True:
            self.prev_readyToEdit = False
            if self.isEnabled():
                if self.readyToEdit:
                    self.lineEdit().selectAll()
                    self.readyToEdit = False
                else:
                    self.lineEdit().deselect()
                return True
        return False

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Enter:
            self.returnPressed.emit()
            self.clearFocus()
        else:
            super().keyPressEvent(event)

    def wheelEvent(self, *args, **kwargs):
        # should work only there is a focus in the lineedit of the SpinBox
        if self.readyToEdit is False:
            super().wheelEvent(*args, **kwargs)

    def on_edit_finished(self):
        self.clearFocus()
        self.returnPressed.emit()

    # def mousePressEvent(self, e, parent=None):
    #     super(FCSpinner, self).mousePressEvent(e)  # required to deselect on 2e click
    #     if self.readyToEdit:
    #         self.lineEdit().selectAll()
    #         self.readyToEdit = False

    def focusOutEvent(self, e):
        # don't focus out if the user requests an popup menu
        if e.reason() != QtCore.Qt.PopupFocusReason:
            super(FCSpinner, self).focusOutEvent(e)  # required to remove cursor on focusOut
            self.lineEdit().deselect()
            self.readyToEdit = True
            self.prev_readyToEdit = True

    def contextMenuEvent(self, event):
        self.menu = QtWidgets.QMenu()
        line_edit = self.lineEdit()

        # UNDO
        undo_action = QAction('%s\t%s' % (_("Undo"), _('Ctrl+Z')), self)
        self.menu.addAction(undo_action)
        undo_action.triggered.connect(line_edit.undo)
        if line_edit.isUndoAvailable() is False:
            undo_action.setDisabled(True)

        # REDO
        redo_action = QAction('%s\t%s' % (_("Redo"), _('Ctrl+Y')), self)
        self.menu.addAction(redo_action)
        redo_action.triggered.connect(line_edit.redo)
        if line_edit.isRedoAvailable() is False:
            redo_action.setDisabled(True)

        self.menu.addSeparator()

        # CUT
        cut_action = QAction('%s\t%s' % (_("Cut"), _('Ctrl+X')), self)
        self.menu.addAction(cut_action)
        cut_action.triggered.connect(self.cut_text)
        if not line_edit.hasSelectedText():
            cut_action.setDisabled(True)

        # COPY
        copy_action = QAction('%s\t%s' % (_("Copy"), _('Ctrl+C')), self)
        self.menu.addAction(copy_action)
        copy_action.triggered.connect(self.copy_text)
        if not line_edit.hasSelectedText():
            copy_action.setDisabled(True)

        # PASTE
        paste_action = QAction('%s\t%s' % (_("Paste"), _('Ctrl+V')), self)
        self.menu.addAction(paste_action)
        paste_action.triggered.connect(self.paste_text)

        # DELETE
        delete_action = QAction('%s\t%s' % (_("Delete"), _('Del')), self)
        self.menu.addAction(delete_action)
        delete_action.triggered.connect(line_edit.del_)

        self.menu.addSeparator()

        # SELECT ALL
        sel_all_action = QAction('%s\t%s' % (_("Select All"), _('Ctrl+A')), self)
        self.menu.addAction(sel_all_action)
        sel_all_action.triggered.connect(line_edit.selectAll)

        self.menu.addSeparator()

        # STEP UP
        step_up_action = QAction('%s\t%s' % (_("Step Up"), ''), self)
        self.menu.addAction(step_up_action)
        step_up_action.triggered.connect(self.stepUp)

        # STEP DOWN
        step_down_action = QAction('%s\t%s' % (_("Step Down"), ''), self)
        self.menu.addAction(step_down_action)
        step_down_action.triggered.connect(self.stepDown)

        self.menu.exec_(event.globalPos())

    def cut_text(self):
        clipboard = QtWidgets.QApplication.clipboard()
        line_edit = self.lineEdit()

        txt = line_edit.selectedText()
        clipboard.clear()
        clipboard.setText(txt)

        line_edit.del_()

    def copy_text(self):
        clipboard = QtWidgets.QApplication.clipboard()
        line_edit = self.lineEdit()

        txt = line_edit.selectedText()
        clipboard.clear()
        clipboard.setText(txt)

    def paste_text(self):
        clipboard = QtWidgets.QApplication.clipboard()
        line_edit = self.lineEdit()

        txt = clipboard.text()
        line_edit.insert(txt)

    def valueFromText(self, text):
        txt = text.strip('%%')
        try:
            ret_val = int(txt)
        except ValueError:
            ret_val = 0
        return ret_val

    def get_value(self):
        return int(self.value())

    def set_value(self, val):
        try:
            k = int(val)
        except Exception as e:
            log.debug(str(e))
            return
        self.setValue(k)

    def validate(self, p_str, p_int):
        text = p_str

        min_val = self.minimum()
        max_val = self.maximum()
        try:
            if int(text) < min_val or int(text) > max_val:
                self.confirmation_signal.emit(False, min_val, max_val)
                return QtGui.QValidator.Intermediate, text, p_int
        except ValueError:
            pass

        self.confirmation_signal.emit(True, min_val, max_val)
        return QtGui.QValidator.Acceptable, p_str, p_int

    def set_range(self, min_val, max_val):
        self.blockSignals(True)
        self.setRange(min_val, max_val)
        self.blockSignals(False)

    def set_step(self, p_int):
        self.blockSignals(True)
        self.setSingleStep(p_int)
        self.blockSignals(False)

    # def sizeHint(self):
    #     default_hint_size = super(FCSpinner, self).sizeHint()
    #     return QtCore.QSize(EDIT_SIZE_HINT, default_hint_size.height())


class FCDoubleSlider(QtWidgets.QSlider):
    # frome here: https://stackoverflow.com/questions/42820380/use-float-for-qslider

    # create our our signal that we can connect to if necessary
    doubleValueChanged = pyqtSignal(float)

    def __init__(self, decimals=3, orientation='horizontal', *args, **kargs):
        if orientation == 'horizontal':
            super(FCDoubleSlider, self).__init__(QtCore.Qt.Horizontal, *args, **kargs)
        else:
            super(FCDoubleSlider, self).__init__(QtCore.Qt.Vertical, *args, **kargs)

        self._multi = 10 ** decimals

        self.valueChanged.connect(self.emitDoubleValueChanged)

    def emitDoubleValueChanged(self):
        value = float(super(FCDoubleSlider, self).value()) / self._multi
        self.doubleValueChanged.emit(value)

    def value(self):
        return float(super(FCDoubleSlider, self).value()) / self._multi

    def get_value(self):
        return self.value()

    def setMinimum(self, value):
        return super(FCDoubleSlider, self).setMinimum(value * self._multi)

    def setMaximum(self, value):
        return super(FCDoubleSlider, self).setMaximum(value * self._multi)

    def setSingleStep(self, value):
        return super(FCDoubleSlider, self).setSingleStep(value * self._multi)

    def singleStep(self):
        return float(super(FCDoubleSlider, self).singleStep()) / self._multi

    def set_value(self, value):
        super(FCDoubleSlider, self).setValue(int(value * self._multi))

    def set_precision(self, decimals):
        self._multi = 10 ** decimals

    def set_range(self, min, max):
        self.blockSignals(True)
        self.setRange(min * self._multi, max * self._multi)
        self.blockSignals(False)


class FCSliderWithDoubleSpinner(QtWidgets.QFrame):

    def __init__(self, min=0, max=10000.0000, step=1, precision=4, orientation='horizontal', **kwargs):
        super().__init__(**kwargs)

        self.slider = FCDoubleSlider(orientation=orientation)
        self.slider.setMinimum(min)
        self.slider.setMaximum(max)
        self.slider.setSingleStep(step)
        self.slider.set_range(min, max)

        self.spinner = FCDoubleSpinner()
        self.spinner.set_range(min, max)
        self.spinner.set_precision(precision)

        self.spinner.set_step(step)
        self.spinner.setMinimumWidth(70)

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.spinner.setSizePolicy(sizePolicy)

        self.layout = QtWidgets.QHBoxLayout()
        self.layout.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.slider)
        self.layout.addWidget(self.spinner)
        self.setLayout(self.layout)

        self.slider.doubleValueChanged.connect(self._on_slider)
        self.spinner.valueChanged.connect(self._on_spinner)

        self.valueChanged = self.spinner.valueChanged

    def set_precision(self, prec):
        self.spinner.set_precision(prec)

    def setSingleStep(self, step):
        self.spinner.set_step(step)

    def set_range(self, min, max):
        self.spinner.set_range(min, max)
        self.slider.set_range(min, max)

    def set_minimum(self, min):
        self.slider.setMinimum(min)
        self.spinner.setMinimum(min)

    def set_maximum(self, max):
        self.slider.setMaximum(max)
        self.spinner.setMaximum(max)

    def get_value(self) -> float:
        return self.spinner.get_value()

    def set_value(self, value: float):
        self.spinner.set_value(value)

    def _on_spinner(self):
        spinner_value = self.spinner.value()
        self.slider.set_value(spinner_value)

    def _on_slider(self):
        slider_value = self.slider.value()
        self.spinner.set_value(slider_value)


class FCButtonWithDoubleSpinner(QtWidgets.QFrame):

    def __init__(self, min=0, max=100, step=1, decimals=4, button_text='', button_icon=None, callback=None, **kwargs):
        super().__init__(**kwargs)

        self.button = QtWidgets.QToolButton()
        if button_text != '':
            self.button.setText(button_text)
        if button_icon:
            self.button.setIcon(button_icon)

        self.spinner = FCDoubleSpinner()
        self.spinner.set_range(min, max)
        self.spinner.set_step(step)
        self.spinner.set_precision(decimals)
        self.spinner.setMinimumWidth(70)

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)
        self.spinner.setSizePolicy(sizePolicy)

        self.layout = QtWidgets.QHBoxLayout()
        self.layout.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.spinner)
        self.layout.addWidget(self.button)
        self.setLayout(self.layout)

        self.valueChanged = self.spinner.valueChanged

        self._callback = callback
        self.button.clicked.connect(self._callback)

    def get_value(self) -> float:
        return self.spinner.get_value()

    def set_value(self, value: float):
        self.spinner.set_value(value)

    def set_callback(self, callback):
        self._callback = callback

    def set_text(self, txt: str):
        if txt:
            self.button.setText(txt)

    def set_icon(self, icon: QtGui.QIcon):
        self.button.setIcon(icon)


class FCDoubleSpinner(QtWidgets.QDoubleSpinBox):
    returnPressed = QtCore.pyqtSignal()
    confirmation_signal = QtCore.pyqtSignal(bool, float, float)

    def __init__(self, suffix=None, alignment=None, parent=None, callback=None, policy=True):
        """

        :param suffix:      a char added to the end of the value in the LineEdit; like a '%' or '$' etc
        :param alignment:   the value is aligned to left or right
        :param parent:
        :param callback:    called when the entered value is outside limits; the min and max value will be passed to it
        """
        super(FCDoubleSpinner, self).__init__(parent)
        self.readyToEdit = True

        self.editingFinished.connect(self.on_edit_finished)
        if callback:
            self.confirmation_signal.connect(callback)

        self.lineEdit().installEventFilter(self)

        # by default don't allow the minus sign to be entered as the default for QDoubleSpinBox is the positive range
        # between 0.00 and 99.00 (2 decimals)
        self.lineEdit().setValidator(
            QtGui.QRegExpValidator(QtCore.QRegExp("\+?[0-9]*[.,]?[0-9]{%d}" % self.decimals()), self))

        if suffix:
            self.setSuffix(' %s' % str(suffix))

        if alignment:
            if alignment == 'center':
                align_val = QtCore.Qt.AlignHCenter
            elif alignment == 'right':
                align_val = QtCore.Qt.AlignRight
            else:
                align_val = QtCore.Qt.AlignLeft
            self.setAlignment(align_val)

        self.prev_readyToEdit = True
        self.menu = None

        if policy:
            sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
            self.setSizePolicy(sizePolicy)

    def on_edit_finished(self):
        self.clearFocus()
        self.returnPressed.emit()

    def eventFilter(self, object, event):
        if event.type() == QtCore.QEvent.MouseButtonPress and self.prev_readyToEdit is True:
            self.prev_readyToEdit = False
            if self.isEnabled():
                if self.readyToEdit:
                    self.cursor_pos = self.lineEdit().cursorPosition()
                    self.lineEdit().selectAll()
                    self.readyToEdit = False
                else:
                    self.lineEdit().deselect()
                return True
        return False

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Enter:
            self.returnPressed.emit()
            self.clearFocus()
        else:
            super().keyPressEvent(event)

    def wheelEvent(self, *args, **kwargs):
        # should work only there is a focus in the lineedit of the SpinBox
        if self.readyToEdit is False:
            super().wheelEvent(*args, **kwargs)

    def focusOutEvent(self, e):
        # don't focus out if the user requests an popup menu
        if e.reason() != QtCore.Qt.PopupFocusReason:
            super(FCDoubleSpinner, self).focusOutEvent(e)  # required to remove cursor on focusOut
            self.lineEdit().deselect()
            self.readyToEdit = True
            self.prev_readyToEdit = True

    def contextMenuEvent(self, event):
        self.menu = QtWidgets.QMenu()
        line_edit = self.lineEdit()

        # UNDO
        undo_action = QAction('%s\t%s' % (_("Undo"), _('Ctrl+Z')), self)
        self.menu.addAction(undo_action)
        undo_action.triggered.connect(line_edit.undo)
        if line_edit.isUndoAvailable() is False:
            undo_action.setDisabled(True)

        # REDO
        redo_action = QAction('%s\t%s' % (_("Redo"), _('Ctrl+Y')), self)
        self.menu.addAction(redo_action)
        redo_action.triggered.connect(line_edit.redo)
        if line_edit.isRedoAvailable() is False:
            redo_action.setDisabled(True)

        self.menu.addSeparator()

        # CUT
        cut_action = QAction('%s\t%s' % (_("Cut"), _('Ctrl+X')), self)
        self.menu.addAction(cut_action)
        cut_action.triggered.connect(self.cut_text)
        if not line_edit.hasSelectedText():
            cut_action.setDisabled(True)

        # COPY
        copy_action = QAction('%s\t%s' % (_("Copy"), _('Ctrl+C')), self)
        self.menu.addAction(copy_action)
        copy_action.triggered.connect(self.copy_text)
        if not line_edit.hasSelectedText():
            copy_action.setDisabled(True)

        # PASTE
        paste_action = QAction('%s\t%s' % (_("Paste"), _('Ctrl+V')), self)
        self.menu.addAction(paste_action)
        paste_action.triggered.connect(self.paste_text)

        # DELETE
        delete_action = QAction('%s\t%s' % (_("Delete"), _('Del')), self)
        self.menu.addAction(delete_action)
        delete_action.triggered.connect(line_edit.del_)

        self.menu.addSeparator()

        # SELECT ALL
        sel_all_action = QAction('%s\t%s' % (_("Select All"), _('Ctrl+A')), self)
        self.menu.addAction(sel_all_action)
        sel_all_action.triggered.connect(line_edit.selectAll)

        self.menu.addSeparator()

        # STEP UP
        step_up_action = QAction('%s\t%s' % (_("Step Up"), ''), self)
        self.menu.addAction(step_up_action)
        step_up_action.triggered.connect(self.stepUp)

        # STEP DOWN
        step_down_action = QAction('%s\t%s' % (_("Step Down"), ''), self)
        self.menu.addAction(step_down_action)
        step_down_action.triggered.connect(self.stepDown)

        self.menu.exec_(event.globalPos())

    def cut_text(self):
        clipboard = QtWidgets.QApplication.clipboard()
        line_edit = self.lineEdit()

        txt = line_edit.selectedText()
        clipboard.clear()
        clipboard.setText(txt)

        line_edit.del_()

    def copy_text(self):
        clipboard = QtWidgets.QApplication.clipboard()
        line_edit = self.lineEdit()

        txt = line_edit.selectedText()
        clipboard.clear()
        clipboard.setText(txt)

    def paste_text(self):
        clipboard = QtWidgets.QApplication.clipboard()
        line_edit = self.lineEdit()

        txt = clipboard.text()
        line_edit.insert(txt)

    def valueFromText(self, p_str):
        text = p_str.replace(',', '.')
        text = text.strip('%%')
        try:
            ret_val = float(text)
        except ValueError:
            ret_val = 0.0
        return ret_val

    def validate(self, p_str, p_int):
        text = p_str.replace(',', '.')

        min_val = self.minimum()
        max_val = self.maximum()
        try:
            if float(text) < min_val or float(text) > max_val:
                self.confirmation_signal.emit(False, min_val, max_val)
                return QtGui.QValidator.Intermediate, text, p_int
        except ValueError:
            pass

        self.confirmation_signal.emit(True, min_val, max_val)
        return QtGui.QValidator.Acceptable, p_str, p_int

    def get_value(self):
        return float(self.value())

    def set_value(self, val):
        try:
            k = float(val)
        except Exception as e:
            log.debug(str(e))
            return
        self.setValue(k)

    def set_precision(self, val):
        self.setDecimals(val)

        # make sure that the user can't type more decimals than the set precision
        if self.minimum() < 0 or self.maximum() <= 0:
            self.lineEdit().setValidator(
                QtGui.QRegExpValidator(QtCore.QRegExp("-?[0-9]*[.,]?[0-9]{%d}" % self.decimals()), self))
        else:
            self.lineEdit().setValidator(
                QtGui.QRegExpValidator(QtCore.QRegExp("\+?[0-9]*[.,]?[0-9]{%d}" % self.decimals()), self))

    def set_range(self, min_val, max_val):
        if min_val < 0 or max_val <= 0:
            self.lineEdit().setValidator(
                QtGui.QRegExpValidator(QtCore.QRegExp("-?[0-9]*[.,]?[0-9]{%d}" % self.decimals()), self))

        self.setRange(min_val, max_val)

    def set_step(self, p_int):
        self.blockSignals(True)
        self.setSingleStep(p_int)
        self.blockSignals(False)

    # def sizeHint(self):
    #     default_hint_size = super(FCDoubleSpinner, self).sizeHint()
    #     return QtCore.QSize(EDIT_SIZE_HINT, default_hint_size.height())


class FCCheckBox(QtWidgets.QCheckBox):
    def __init__(self, label='', parent=None):
        super(FCCheckBox, self).__init__(str(label), parent)

    def get_value(self):
        return self.isChecked()

    def set_value(self, val):
        self.setChecked(val)

    def toggle(self):
        self.set_value(not self.get_value())


class FCTextArea(QtWidgets.QPlainTextEdit):
    def __init__(self, parent=None):
        super(FCTextArea, self).__init__(parent)

    def set_value(self, val):
        self.setPlainText(val)

    def get_value(self):
        return str(self.toPlainText())

    def sizeHint(self, custom_sizehint=None):
        default_hint_size = super(FCTextArea, self).sizeHint()

        if custom_sizehint is None:
            return QtCore.QSize(EDIT_SIZE_HINT, default_hint_size.height())
        else:
            return QtCore.QSize(custom_sizehint, default_hint_size.height())


class FCTextEdit(QtWidgets.QTextEdit):

    def __init__(self, *args, **kwargs):
        super(FCTextEdit, self).__init__(*args, **kwargs)

        self.menu = None
        self.undo_flag = False
        self.redo_flag = False

        self.undoAvailable.connect(self.on_undo_available)
        self.redoAvailable.connect(self.on_redo_available)

    def on_undo_available(self, val):
        self.undo_flag = val

    def on_redo_available(self, val):
        self.redo_flag = val

    def contextMenuEvent(self, event):
        self.menu = QtWidgets.QMenu()
        tcursor = self.textCursor()
        txt = tcursor.selectedText()

        # UNDO
        undo_action = QAction('%s\t%s' % (_("Undo"), _('Ctrl+Z')), self)
        self.menu.addAction(undo_action)
        undo_action.triggered.connect(self.undo)
        if self.undo_flag is False:
            undo_action.setDisabled(True)

        # REDO
        redo_action = QAction('%s\t%s' % (_("Redo"), _('Ctrl+Y')), self)
        self.menu.addAction(redo_action)
        redo_action.triggered.connect(self.redo)
        if self.redo_flag is False:
            redo_action.setDisabled(True)

        self.menu.addSeparator()

        # CUT
        cut_action = QAction('%s\t%s' % (_("Cut"), _('Ctrl+X')), self)
        self.menu.addAction(cut_action)
        cut_action.triggered.connect(self.cut_text)
        if txt == '':
            cut_action.setDisabled(True)

        # COPY
        copy_action = QAction('%s\t%s' % (_("Copy"), _('Ctrl+C')), self)
        self.menu.addAction(copy_action)
        copy_action.triggered.connect(self.copy_text)
        if txt == '':
            copy_action.setDisabled(True)

        # PASTE
        paste_action = QAction('%s\t%s' % (_("Paste"), _('Ctrl+V')), self)
        self.menu.addAction(paste_action)
        paste_action.triggered.connect(self.paste_text)

        # DELETE
        delete_action = QAction('%s\t%s' % (_("Delete"), _('Del')), self)
        self.menu.addAction(delete_action)
        delete_action.triggered.connect(self.delete_text)

        self.menu.addSeparator()

        # SELECT ALL
        sel_all_action = QAction('%s\t%s' % (_("Select All"), _('Ctrl+A')), self)
        self.menu.addAction(sel_all_action)
        sel_all_action.triggered.connect(self.selectAll)

        self.menu.exec_(event.globalPos())

    def cut_text(self):
        tcursor = self.textCursor()
        clipboard = QtWidgets.QApplication.clipboard()

        txt = tcursor.selectedText()
        clipboard.clear()
        clipboard.setText(txt)

        tcursor.deleteChar()

    def copy_text(self):
        tcursor = self.textCursor()
        clipboard = QtWidgets.QApplication.clipboard()

        txt = tcursor.selectedText()
        clipboard.clear()
        clipboard.setText(txt)

    def paste_text(self):
        tcursor = self.textCursor()
        clipboard = QtWidgets.QApplication.clipboard()

        txt = clipboard.text()
        tcursor.insertText(txt)

    def delete_text(self):
        tcursor = self.textCursor()
        tcursor.deleteChar()


class FCTextAreaRich(FCTextEdit):
    def __init__(self, parent=None):
        super(FCTextAreaRich, self).__init__(parent)

    def set_value(self, val):
        self.setText(val)

    def get_value(self):
        return str(self.toPlainText())

    def sizeHint(self):
        default_hint_size = super(FCTextAreaRich, self).sizeHint()
        return QtCore.QSize(EDIT_SIZE_HINT, default_hint_size.height())


class FCTextAreaExtended(FCTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.completer = MyCompleter()

        self.model = QtCore.QStringListModel()
        self.completer.setModel(self.model)
        self.set_model_data(keyword_list=[])
        self.completer.insertText.connect(self.insertCompletion)
        self.completer.popup().clicked.connect(self.insert_completion_click)

        self.completer_enable = False

    def set_model_data(self, keyword_list):
        self.model.setStringList(keyword_list)

    def insert_completion_click(self):
        self.completer.insertText.emit(self.completer.getSelected())
        self.completer.setCompletionMode(QCompleter.PopupCompletion)

    def insertCompletion(self, completion):
        tc = self.textCursor()
        extra = (len(completion) - len(self.completer.completionPrefix()))

        # don't insert if the word is finished but add a space instead
        if extra == 0:
            tc.insertText(' ')
            self.completer.popup().hide()
            return

        tc.movePosition(QTextCursor.Left)
        tc.movePosition(QTextCursor.EndOfWord)
        tc.insertText(completion[-extra:])
        # add a space after inserting the word
        tc.insertText(' ')
        self.setTextCursor(tc)
        self.completer.popup().hide()

    def focusInEvent(self, event):
        if self.completer:
            self.completer.setWidget(self)
        QTextEdit.focusInEvent(self, event)

    def set_value(self, val):
        self.setText(val)

    def get_value(self):
        self.toPlainText()

    def insertFromMimeData(self, data):
        """
        Reimplemented such that when SHIFT is pressed and doing click Paste in the contextual menu, the '\' symbol
        is replaced with the '/' symbol. That's because of the difference in path separators in Windows and TCL
        :param data:
        :return:
        """
        modifier = QtWidgets.QApplication.keyboardModifiers()
        if modifier == Qt.ShiftModifier:
            text = data.text()
            text = text.replace('\\', '/')
            self.insertPlainText(text)
        else:
            self.insertPlainText(data.text())

    def keyPressEvent(self, event):
        """
        Reimplemented so the CTRL + SHIFT + V shortcut key combo will paste the text but replacing '\' with '/'
        :param event:
        :return:
        """
        key = event.key()
        modifier = QtWidgets.QApplication.keyboardModifiers()

        if modifier & Qt.ControlModifier and modifier & Qt.ShiftModifier:
            if key == QtCore.Qt.Key_V:
                clipboard = QtWidgets.QApplication.clipboard()
                clip_text = clipboard.text()
                clip_text = clip_text.replace('\\', '/')
                self.insertPlainText(clip_text)
        elif modifier & Qt.ControlModifier:
            if key == Qt.Key_Slash:
                self.comment()

        tc = self.textCursor()
        if (key == Qt.Key_Tab or key == Qt.Key_Enter or key == Qt.Key_Return) and self.completer.popup().isVisible():
            self.completer.insertText.emit(self.completer.getSelected())
            self.completer.setCompletionMode(QCompleter.PopupCompletion)
            return
        elif key == Qt.Key_BraceLeft:
            tc.insertText('{}')
            self.moveCursor(QtGui.QTextCursor.Left)
        elif key == Qt.Key_BracketLeft:
            tc.insertText('[]')
            self.moveCursor(QtGui.QTextCursor.Left)
        elif key == Qt.Key_ParenLeft:
            tc.insertText('()')
            self.moveCursor(QtGui.QTextCursor.Left)

        elif key == Qt.Key_BraceRight:
            tc.select(QtGui.QTextCursor.WordUnderCursor)
            if tc.selectedText() == '}':
                tc.movePosition(QTextCursor.Right)
                self.setTextCursor(tc)
            else:
                tc.clearSelection()
                self.textCursor().insertText('}')
        elif key == Qt.Key_BracketRight:
            tc.select(QtGui.QTextCursor.WordUnderCursor)
            if tc.selectedText() == ']':
                tc.movePosition(QTextCursor.Right)
                self.setTextCursor(tc)
            else:
                tc.clearSelection()
                self.textCursor().insertText(']')
        elif key == Qt.Key_ParenRight:
            tc.select(QtGui.QTextCursor.WordUnderCursor)
            if tc.selectedText() == ')':
                tc.movePosition(QTextCursor.Right)
                self.setTextCursor(tc)
            else:
                tc.clearSelection()
                self.textCursor().insertText(')')
        else:
            super(FCTextAreaExtended, self).keyPressEvent(event)

        if self.completer_enable:
            tc.select(QTextCursor.WordUnderCursor)
            cr = self.cursorRect()

            if len(tc.selectedText()) > 0:
                self.completer.setCompletionPrefix(tc.selectedText())
                popup = self.completer.popup()
                popup.setCurrentIndex(self.completer.completionModel().index(0, 0))

                cr.setWidth(self.completer.popup().sizeHintForColumn(0)
                            + self.completer.popup().verticalScrollBar().sizeHint().width())
                self.completer.complete(cr)
            else:
                self.completer.popup().hide()

    def comment(self):
        """
        Got it from here:
        https://stackoverflow.com/questions/49898820/how-to-get-text-next-to-cursor-in-qtextedit-in-pyqt4
        :return:
        """
        pos = self.textCursor().position()
        self.moveCursor(QtGui.QTextCursor.StartOfLine)
        line_text = self.textCursor().block().text()
        if self.textCursor().block().text().startswith(" "):
            # skip the white space
            self.moveCursor(QtGui.QTextCursor.NextWord)
        self.moveCursor(QtGui.QTextCursor.NextCharacter, QtGui.QTextCursor.KeepAnchor)
        character = self.textCursor().selectedText()
        if character == "#":
            # delete #
            self.textCursor().deletePreviousChar()
            # delete white space 
            self.moveCursor(QtGui.QTextCursor.NextWord, QtGui.QTextCursor.KeepAnchor)
            self.textCursor().removeSelectedText()
        else:
            self.moveCursor(QtGui.QTextCursor.PreviousCharacter, QtGui.QTextCursor.KeepAnchor)
            self.textCursor().insertText("# ")
        cursor = QtGui.QTextCursor(self.textCursor())
        cursor.setPosition(pos)
        self.setTextCursor(cursor)


class FCPlainTextAreaExtended(QtWidgets.QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.completer = MyCompleter()

        self.model = QtCore.QStringListModel()
        self.completer.setModel(self.model)
        self.set_model_data(keyword_list=[])
        self.completer.insertText.connect(self.insertCompletion)
        self.completer.popup().clicked.connect(self.insert_completion_click)

        self.completer_enable = False

        self.menu = None
        self.undo_flag = False
        self.redo_flag = False

        self.undoAvailable.connect(self.on_undo_available)
        self.redoAvailable.connect(self.on_redo_available)

    def on_undo_available(self, val):
        self.undo_flag = val

    def on_redo_available(self, val):
        self.redo_flag = val

    def append(self, text):
        """
        Added this to make this subclass compatible with FCTextAreaExtended
        :param text: string
        :return:
        """
        self.appendPlainText(text)

    def set_model_data(self, keyword_list):
        self.model.setStringList(keyword_list)

    def insert_completion_click(self):
        self.completer.insertText.emit(self.completer.getSelected())
        self.completer.setCompletionMode(QCompleter.PopupCompletion)

    def insertCompletion(self, completion):
        tc = self.textCursor()
        extra = (len(completion) - len(self.completer.completionPrefix()))

        # don't insert if the word is finished but add a space instead
        if extra == 0:
            tc.insertText(' ')
            self.completer.popup().hide()
            return

        tc.movePosition(QTextCursor.Left)
        tc.movePosition(QTextCursor.EndOfWord)
        tc.insertText(completion[-extra:])
        # add a space after inserting the word
        tc.insertText(' ')
        self.setTextCursor(tc)
        self.completer.popup().hide()

    def focusInEvent(self, event):
        if self.completer:
            self.completer.setWidget(self)
        QtWidgets.QPlainTextEdit.focusInEvent(self, event)

    def contextMenuEvent(self, event):
        self.menu = QtWidgets.QMenu()
        tcursor = self.textCursor()
        txt = tcursor.selectedText()

        # UNDO
        undo_action = QAction('%s\t%s' % (_("Undo"), _('Ctrl+Z')), self)
        self.menu.addAction(undo_action)
        undo_action.triggered.connect(self.undo)
        if self.undo_flag is False:
            undo_action.setDisabled(True)

        # REDO
        redo_action = QAction('%s\t%s' % (_("Redo"), _('Ctrl+Y')), self)
        self.menu.addAction(redo_action)
        redo_action.triggered.connect(self.redo)
        if self.redo_flag is False:
            redo_action.setDisabled(True)

        self.menu.addSeparator()

        # CUT
        cut_action = QAction('%s\t%s' % (_("Cut"), _('Ctrl+X')), self)
        self.menu.addAction(cut_action)
        cut_action.triggered.connect(self.cut_text)
        if txt == '':
            cut_action.setDisabled(True)

        # COPY
        copy_action = QAction('%s\t%s' % (_("Copy"), _('Ctrl+C')), self)
        self.menu.addAction(copy_action)
        copy_action.triggered.connect(self.copy_text)
        if txt == '':
            copy_action.setDisabled(True)

        # PASTE
        paste_action = QAction('%s\t%s' % (_("Paste"), _('Ctrl+V')), self)
        self.menu.addAction(paste_action)
        paste_action.triggered.connect(self.paste_text)

        # DELETE
        delete_action = QAction('%s\t%s' % (_("Delete"), _('Del')), self)
        self.menu.addAction(delete_action)
        delete_action.triggered.connect(self.delete_text)

        self.menu.addSeparator()

        # SELECT ALL
        sel_all_action = QAction('%s\t%s' % (_("Select All"), _('Ctrl+A')), self)
        self.menu.addAction(sel_all_action)
        sel_all_action.triggered.connect(self.selectAll)

        self.menu.exec_(event.globalPos())

    def cut_text(self):
        tcursor = self.textCursor()
        clipboard = QtWidgets.QApplication.clipboard()

        txt = tcursor.selectedText()
        clipboard.clear()
        clipboard.setText(txt)

        tcursor.deleteChar()

    def copy_text(self):
        tcursor = self.textCursor()
        clipboard = QtWidgets.QApplication.clipboard()

        txt = tcursor.selectedText()
        clipboard.clear()
        clipboard.setText(txt)

    def paste_text(self):
        tcursor = self.textCursor()
        clipboard = QtWidgets.QApplication.clipboard()

        txt = clipboard.text()
        tcursor.insertText(txt)

    def delete_text(self):
        tcursor = self.textCursor()
        tcursor.deleteChar()

    def set_value(self, val):
        self.setPlainText(val)

    def get_value(self):
        self.toPlainText()

    def insertFromMimeData(self, data):
        """
        Reimplemented such that when SHIFT is pressed and doing click Paste in the contextual menu, the '\' symbol
        is replaced with the '/' symbol. That's because of the difference in path separators in Windows and TCL
        :param data:
        :return:
        """
        modifier = QtWidgets.QApplication.keyboardModifiers()
        if modifier == Qt.ShiftModifier:
            text = data.text()
            text = text.replace('\\', '/')
            self.insertPlainText(text)
        else:
            self.insertPlainText(data.text())

    def keyPressEvent(self, event):
        """
        Reimplemented so the CTRL + SHIFT + V shortcut key combo will paste the text but replacing '\' with '/'
        :param event:
        :return:
        """
        key = event.key()
        modifier = QtWidgets.QApplication.keyboardModifiers()

        if modifier & Qt.ControlModifier and modifier & Qt.ShiftModifier:
            if key == QtCore.Qt.Key_V:
                clipboard = QtWidgets.QApplication.clipboard()
                clip_text = clipboard.text()
                clip_text = clip_text.replace('\\', '/')
                self.insertPlainText(clip_text)

        if modifier & Qt.ControlModifier and key == Qt.Key_Slash:
            self.comment()

        tc = self.textCursor()
        if (key == Qt.Key_Tab or key == Qt.Key_Enter or key == Qt.Key_Return) and self.completer.popup().isVisible():
            self.completer.insertText.emit(self.completer.getSelected())
            self.completer.setCompletionMode(QCompleter.PopupCompletion)
            return
        elif key == Qt.Key_BraceLeft:
            tc.insertText('{}')
            self.moveCursor(QtGui.QTextCursor.Left)
        elif key == Qt.Key_BracketLeft:
            tc.insertText('[]')
            self.moveCursor(QtGui.QTextCursor.Left)
        elif key == Qt.Key_ParenLeft:
            tc.insertText('()')
            self.moveCursor(QtGui.QTextCursor.Left)

        elif key == Qt.Key_BraceRight:
            tc.select(QtGui.QTextCursor.WordUnderCursor)
            if tc.selectedText() == '}':
                tc.movePosition(QTextCursor.Right)
                self.setTextCursor(tc)
            else:
                tc.clearSelection()
                self.textCursor().insertText('}')
        elif key == Qt.Key_BracketRight:
            tc.select(QtGui.QTextCursor.WordUnderCursor)
            if tc.selectedText() == ']':
                tc.movePosition(QTextCursor.Right)
                self.setTextCursor(tc)
            else:
                tc.clearSelection()
                self.textCursor().insertText(']')
        elif key == Qt.Key_ParenRight:
            tc.select(QtGui.QTextCursor.WordUnderCursor)
            if tc.selectedText() == ')':
                tc.movePosition(QTextCursor.Right)
                self.setTextCursor(tc)
            else:
                tc.clearSelection()
                self.textCursor().insertText(')')
        else:
            super(FCPlainTextAreaExtended, self).keyPressEvent(event)

        if self.completer_enable:
            tc.select(QTextCursor.WordUnderCursor)
            cr = self.cursorRect()

            if len(tc.selectedText()) > 0:
                self.completer.setCompletionPrefix(tc.selectedText())
                popup = self.completer.popup()
                popup.setCurrentIndex(self.completer.completionModel().index(0, 0))

                cr.setWidth(self.completer.popup().sizeHintForColumn(0)
                            + self.completer.popup().verticalScrollBar().sizeHint().width())
                self.completer.complete(cr)
            else:
                self.completer.popup().hide()

    def comment(self):
        """
        Got it from here:
        https://stackoverflow.com/questions/49898820/how-to-get-text-next-to-cursor-in-qtextedit-in-pyqt4
        :return:
        """
        pos = self.textCursor().position()
        self.moveCursor(QtGui.QTextCursor.StartOfLine)
        self.textCursor().block().text()
        if self.textCursor().block().text().startswith(" "):
            # skip the white space
            self.moveCursor(QtGui.QTextCursor.NextWord)
        self.moveCursor(QtGui.QTextCursor.NextCharacter, QtGui.QTextCursor.KeepAnchor)
        character = self.textCursor().selectedText()
        if character == "#":
            # delete #
            self.textCursor().deletePreviousChar()
            # delete white space
            self.moveCursor(QtGui.QTextCursor.NextWord, QtGui.QTextCursor.KeepAnchor)
            self.textCursor().removeSelectedText()
        else:
            self.moveCursor(QtGui.QTextCursor.PreviousCharacter, QtGui.QTextCursor.KeepAnchor)
            self.textCursor().insertText("# ")
        cursor = QtGui.QTextCursor(self.textCursor())
        cursor.setPosition(pos)
        self.setTextCursor(cursor)


class FCComboBox(QtWidgets.QComboBox):

    def __init__(self, parent=None, callback=None, policy=True):
        super(FCComboBox, self).__init__(parent)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.view = self.view()
        self.view.viewport().installEventFilter(self)
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)

        self._set_last = False
        self._obj_type = None

        if policy is True:
            sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
            self.setSizePolicy(sizePolicy)

        # the callback() will be called on customcontextmenu event and will be be passed 2 parameters:
        # pos = mouse right click click position
        # self = is the combobox object itself
        if callback:
            self.view.customContextMenuRequested.connect(lambda pos: callback(pos, self))

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.MouseButtonRelease:
            if event.button() == Qt.RightButton:
                return True
        return False

    def wheelEvent(self, *args, **kwargs):
        pass

    def get_value(self):
        return str(self.currentText())

    def set_value(self, val):
        idx = self.findText(str(val))
        if idx == -1:
            self.setCurrentIndex(0)
            return
        self.setCurrentIndex(idx)

    @property
    def is_last(self):
        return self._set_last

    @is_last.setter
    def is_last(self, val):
        self._set_last = val
        if self._set_last is True:
            self.model().rowsInserted.connect(self.on_model_changed)
        self.setCurrentIndex(1)

    @property
    def obj_type(self):
        return self._obj_type

    @obj_type.setter
    def obj_type(self, val):
        self._obj_type = val

    def on_model_changed(self, parent, first, last):
        if self.model().data(parent, QtCore.Qt.DisplayRole) == self.obj_type:
            self.setCurrentIndex(first)


class FCComboBox2(FCComboBox):
    def __init__(self, parent=None, callback=None):
        super(FCComboBox2, self).__init__(parent=parent, callback=callback)

    def get_value(self):
        return int(self.currentIndex())

    def set_value(self, val):
        self.setCurrentIndex(val)


class FCInputDialog(QtWidgets.QInputDialog):
    def __init__(self, parent=None, ok=False, val=None, title=None, text=None, min=None, max=None, decimals=None,
                 init_val=None):
        super(FCInputDialog, self).__init__(parent)

        self.allow_empty = ok
        self.empty_val = val

        self.val = 0.0
        self.ok = ''

        self.init_value = init_val if init_val else 0.0

        if title is None:
            self.title = 'title'
        else:
            self.title = title
        if text is None:
            self.text = 'text'
        else:
            self.text = text
        if min is None:
            self.min = 0
        else:
            self.min = min
        if max is None:
            self.max = 0
        else:
            self.max = max
        if decimals is None:
            self.decimals = 6
        else:
            self.decimals = decimals

    def get_value(self):
        self.val, self.ok = self.getDouble(self, self.title, self.text, min=self.min,
                                           max=self.max, decimals=self.decimals, value=self.init_value)
        return [self.val, self.ok]

    # "Transform", "Enter the Angle value:"
    def set_value(self, val):
        pass


class FCInputDoubleSpinner(QtWidgets.QDialog):
    def __init__(self, parent=None, title=None, text=None,
                 min=0.0, max=100.0000, step=1, decimals=4, init_val=None):
        super(FCInputDoubleSpinner, self).__init__(parent)

        self.val = 0.0

        self.init_value = init_val if init_val else 0.0

        self.setWindowTitle(title) if title else self.setWindowTitle('title')
        self.text = text if text else 'text'

        self.min = min
        self.max = max
        self.step = step
        self.decimals = decimals

        self.lbl = FCLabel(self.text)

        if title is None:
            self.title = 'title'
        else:
            self.title = title
        if text is None:
            self.text = 'text'
        else:
            self.text = text

        self.wdg = FCDoubleSpinner()
        self.wdg.set_precision(self.decimals)
        self.wdg.set_range(self.min, self.max)
        self.wdg.set_step(self.step)
        self.wdg.set_value(self.init_value)

        QBtn = QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel

        self.buttonBox = QtWidgets.QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.lbl)
        self.layout.addWidget(self.wdg)
        self.layout.addWidget(self.buttonBox)

        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText(_("Ok"))
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText(_("Cancel"))

        self.setLayout(self.layout)

    def set_title(self, txt):
        self.setWindowTitle(txt)

    def set_text(self, txt):
        self.lbl.set_value(txt)

    def set_icon(self, icon):
        self.setWindowIcon(icon)

    def set_min(self, val):
        self.wdg.setMinimum(val)

    def set_max(self, val):
        self.wdg.setMaximum(val)

    def set_range(self, min, max):
        self.wdg.set_range(min, max)

    def set_step(self, val):
        self.wdg.set_step(val)

    def set_value(self, val):
        self.wdg.set_value(val)

    def get_value(self):
        if self.exec_() == QtWidgets.QDialog.Accepted:
            return self.wdg.get_value(), True
        else:
            return None, False


class FCInputSpinner(QtWidgets.QDialog):
    def __init__(self, parent=None, title=None, text=None, min=None, max=None, decimals=4, step=1, init_val=None):
        super().__init__(parent)

        self.val = 0.0
        self.ok = ''

        self.init_value = init_val if init_val else 0.0

        self.setWindowTitle(title) if title else self.setWindowTitle('title')
        self.text = text if text else 'text'

        self.min = min if min else 0
        self.max = max if max else 255
        self.step = step if step else 1

        self.lbl = FCLabel(self.text)

        self.wdg = FCDoubleSpinner()
        self.wdg.set_value(self.init_value)
        self.wdg.set_range(self.min, self.max)
        self.wdg.set_step(self.step)
        self.wdg.set_precision(decimals)

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.wdg.setSizePolicy(sizePolicy)

        QBtn = QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel

        self.buttonBox = QtWidgets.QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText(_("Ok"))
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText(_("Cancel"))

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.lbl)
        self.layout.addWidget(self.wdg)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

    def set_title(self, txt):
        self.setWindowTitle(txt)

    def set_text(self, txt):
        self.lbl.set_value(txt)

    def set_min(self, val):
        self.wdg.spinner.setMinimum(val)

    def set_max(self, val):
        self.wdg.spinner.setMaximum(val)

    def set_range(self, min, max):
        self.wdg.spinner.set_range(min, max)

    def set_step(self, val):
        self.wdg.spinner.set_step(val)

    def get_value(self):
        if self.exec_() == QtWidgets.QDialog.Accepted:
            return [self.wdg.get_value(), True]
        else:
            return [None, False]


class FCInputDialogSlider(QtWidgets.QDialog):

    def __init__(self, parent=None, title=None, text=None, min=None, max=None, step=1, init_val=None):
        super().__init__(parent)

        self.val = 0.0

        self.init_value = init_val if init_val else 0.0

        self.setWindowTitle(title) if title else self.setWindowTitle('title')
        self.text = text if text else 'text'

        self.min = min if min else 0
        self.max = max if max else 255
        self.step = step if step else 1

        self.lbl = FCLabel(self.text)

        self.wdg = FCSliderWithSpinner(min=self.min, max=self.max, step=self.step)
        self.wdg.set_value(self.init_value)

        QBtn = QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel

        self.buttonBox = QtWidgets.QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText(_("Ok"))
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText(_("Cancel"))

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.lbl)
        self.layout.addWidget(self.wdg)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

    def set_title(self, txt):
        self.setWindowTitle(txt)

    def set_text(self, txt):
        self.lbl.set_value(txt)

    def set_min(self, val):
        self.wdg.spinner.setMinimum(val)

    def set_max(self, val):
        self.wdg.spinner.setMaximum(val)

    def set_range(self, min, max):
        self.wdg.spinner.set_range(min, max)

    def set_step(self, val):
        self.wdg.spinner.set_step(val)

    def get_results(self):
        if self.exec_() == QtWidgets.QDialog.Accepted:
            return self.wdg.get_value(), True
        else:
            return None, False


class FCInputDialogSpinnerButton(QtWidgets.QDialog):

    def __init__(self, parent=None, title=None, text=None, min=None, max=None, step=1, decimals=4, init_val=None,
                 button_text='', button_icon=None, callback=None):
        super().__init__(parent)

        self.val = 0.0

        self.init_value = init_val if init_val else 0.0

        self.setWindowTitle(title) if title else self.setWindowTitle('title')
        self.text = text if text else 'text'

        self.min = min if min else 0
        self.max = max if max else 255
        self.step = step if step else 1
        self.decimals = decimals if decimals else 4

        self.lbl = FCLabel(self.text)

        self.wdg = FCButtonWithDoubleSpinner(min=self.min, max=self.max, step=self.step, decimals=decimals,
                                             button_text=button_text, button_icon=button_icon, callback=callback)
        self.wdg.set_value(self.init_value)

        QBtn = QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel

        self.buttonBox = QtWidgets.QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText(_("Ok"))
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText(_("Cancel"))

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.lbl)
        self.layout.addWidget(self.wdg)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

    def set_title(self, txt):
        self.setWindowTitle(txt)

    def set_text(self, txt):
        self.lbl.set_value(txt)

    def set_icon(self, icon):
        self.setWindowIcon(icon)

    def set_min(self, val):
        self.wdg.spinner.setMinimum(val)

    def set_max(self, val):
        self.wdg.spinner.setMaximum(val)

    def set_range(self, min, max):
        self.wdg.spinner.set_range(min, max)

    def set_step(self, val):
        self.wdg.spinner.set_step(val)

    def set_value(self, val):
        self.wdg.spinner.set_value(val)

    def get_results(self):
        if self.exec_() == QtWidgets.QDialog.Accepted:
            return self.wdg.get_value(), True
        else:
            return None, False


class FCButton(QtWidgets.QPushButton):
    def __init__(self, text=None, checkable=None, click_callback=None, parent=None):
        super(FCButton, self).__init__(text, parent)
        if checkable is not None:
            self.setCheckable(checkable)

        if not click_callback is None:
            self.clicked.connect(click_callback)

    def get_value(self):
        return self.isChecked()

    def set_value(self, val):
        self.setText(str(val))


class FCLabel(QtWidgets.QLabel):
    clicked = QtCore.pyqtSignal(bool)
    right_clicked = QtCore.pyqtSignal(bool)
    middle_clicked = QtCore.pyqtSignal(bool)

    def __init__(self, parent=None):
        super(FCLabel, self).__init__(parent)

        # for the usage of this label as a clickable label, to know that current state
        self.clicked_state = False
        self.middle_clicked_state = False
        self.right_clicked_state = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked_state = not self.clicked_state
            self.clicked.emit(self.clicked_state)
        elif event.button() == Qt.RightButton:
            self.right_clicked_state = not self.right_clicked_state
            self.right_clicked.emit(True)
        elif event.button() == Qt.MiddleButton:
            self.middle_clicked_state = not self.middle_clicked_state
            self.middle_clicked.emit(True)

    def get_value(self):
        return self.text()

    def set_value(self, val):
        self.setText(str(val))


class FCMenu(QtWidgets.QMenu):
    def __init__(self):
        super().__init__()
        self.mouse_is_panning = False
        self.popup_active = False

    def popup(self, pos, action=None):
        super().popup(pos)
        self.mouse_is_panning = False
        self.popup_active = True


class FCTab(QtWidgets.QTabWidget):
    def __init__(self, parent=None):
        super(FCTab, self).__init__(parent)
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.closeTab)

    def deleteTab(self, currentIndex):
        widget = self.widget(currentIndex)
        if widget is not None:
            widget.deleteLater()
        self.removeTab(currentIndex)

    def closeTab(self, currentIndex):
        self.removeTab(currentIndex)

    def protectTab(self, currentIndex):
        self.tabBar().setTabButton(currentIndex, QtWidgets.QTabBar.RightSide, None)


# class FCTabBar(QtWidgets.QTabBar):
#     def tabSizeHint(self, index):
#         size =QtWidgets.QTabBar.tabSizeHint(self, index)
#         w = int(self.width()/self.count())
#         return QtCore.QSize(w, size.height())


class FCDetachableTab(QtWidgets.QTabWidget):
    """
    From here:
    https://stackoverflow.com/questions/47267195/in-pyqt4-is-it-possible-to-detach-tabs-from-a-qtabwidget
    """
    tab_detached = QtCore.pyqtSignal(str)
    tab_attached = QtCore.pyqtSignal(str)

    def __init__(self, protect=None, protect_by_name=None, parent=None):
        super().__init__(parent=parent)

        self.tabBar = self.FCTabBar(self)
        self.tabBar.onMoveTabSignal.connect(self.moveTab)
        self.tabBar.onCloseTabSignal.connect(self.on_closetab_middle_button)

        self.tabBar.detachedTabDropSignal.connect(self.detachedTabDrop)
        self.set_detachable(val=True)

        self.setTabBar(self.tabBar)

        # Used to keep a reference to detached tabs since their QMainWindow
        # does not have a parent
        self.detachedTabs = {}

        # a way to make sure that tabs can't be closed after they attach to the parent tab
        self.protect_tab = True if protect is not None and protect is True else False

        self.protect_by_name = protect_by_name if isinstance(protect_by_name, list) else None

        # Close all detached tabs if the application is closed explicitly
        QtWidgets.qApp.aboutToQuit.connect(self.closeDetachedTabs)  # @UndefinedVariable

        # used by the property self.useOldIndex(param)
        self.use_old_index = None
        self.old_index = None

        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.closeTab)

    def set_rmb_callback(self, callback):
        """

        :param callback: Function to call on right mouse click on tab
        :type callback: func
        :return: None
        """

        self.tabBar.right_click.connect(callback)

    def set_detachable(self, val=True):
        try:
            self.tabBar.onDetachTabSignal.disconnect()
        except TypeError:
            pass

        if val is True:
            self.tabBar.onDetachTabSignal.connect(self.detachTab)
            # the tab can be moved around
            self.tabBar.can_be_dragged = True
        else:
            # the detached tab can't be moved
            self.tabBar.can_be_dragged = False

        return val

    def setupContextMenu(self):
        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

    def addContextMenu(self, entry, call_function, icon=None, initial_checked=False):
        action_name = str(entry)
        action = QtWidgets.QAction(self)
        action.setCheckable(True)
        action.setText(action_name)
        if icon:
            assert isinstance(icon, QtGui.QIcon), \
                "Expected the argument to be QtGui.QIcon. Instead it is %s" % type(icon)
            action.setIcon(icon)
        action.setChecked(initial_checked)
        self.addAction(action)
        action.triggered.connect(call_function)

    def useOldIndex(self, param):
        if param:
            self.use_old_index = True
        else:
            self.use_old_index = False

    def deleteTab(self, currentIndex):
        widget = self.widget(currentIndex)
        if widget is not None:
            widget.deleteLater()
        self.removeTab(currentIndex)

    def closeTab(self, currentIndex):
        """
        Slot connected to the tabCloseRequested signal

        :param currentIndex:
        :return:
        """

        self.removeTab(currentIndex)

    def on_closetab_middle_button(self, current_index):
        """

        :param current_index:
        :return:
        """

        # if tab is protected don't delete it
        if self.tabBar.tabButton(current_index, QtWidgets.QTabBar.RightSide) is not None:
            self.removeTab(current_index)

    def protectTab(self, currentIndex):
        # self.FCTabBar().setTabButton(currentIndex, QtWidgets.QTabBar.RightSide, None)
        self.tabBar.setTabButton(currentIndex, QtWidgets.QTabBar.RightSide, None)

    def setMovable(self, movable):
        """
        The default movable functionality of QTabWidget must remain disabled
        so as not to conflict with the added features

        :param movable:
        :return:
        """
        pass

    @pyqtSlot(int, int)
    def moveTab(self, fromIndex, toIndex):
        """
        Move a tab from one position (index) to another

        :param fromIndex:   the original index location of the tab
        :param toIndex:     the new index location of the tab
        :return:
        """

        widget = self.widget(fromIndex)
        icon = self.tabIcon(fromIndex)
        text = self.tabText(fromIndex)

        self.removeTab(fromIndex)
        self.insertTab(toIndex, widget, icon, text)
        self.setCurrentIndex(toIndex)

    # @pyqtSlot(int, QtCore.QPoint)
    def detachTab(self, index, point):
        """
        Detach the tab by removing it's contents and placing them in
        a DetachedTab window

        :param index:   the index location of the tab to be detached
        :param point:   the screen position for creating the new DetachedTab window
        :return:
        """
        self.old_index = index

        # Get the tab content and add name FlatCAM to the tab so we know on which app is this tab linked
        name = "FlatCAM " + self.tabText(index)
        icon = self.tabIcon(index)
        if icon.isNull():
            icon = self.window().windowIcon()
        contentWidget = self.widget(index)

        try:
            contentWidgetRect = contentWidget.frameGeometry()
        except AttributeError:
            return

        # Create a new detached tab window
        detachedTab = self.FCDetachedTab(name, contentWidget)
        detachedTab.setWindowModality(QtCore.Qt.NonModal)
        detachedTab.setWindowIcon(icon)
        detachedTab.setGeometry(contentWidgetRect)
        detachedTab.onCloseSignal.connect(self.attachTab)
        detachedTab.onDropSignal.connect(self.tabBar.detachedTabDrop)
        detachedTab.move(point)
        detachedTab.show()

        # Create a reference to maintain access to the detached tab
        self.detachedTabs[name] = detachedTab

        self.tab_detached.emit(name)

    def attachTab(self, contentWidget, name, icon, insertAt=None):
        """
        Re-attach the tab by removing the content from the DetachedTab window,
        closing it, and placing the content back into the DetachableTabWidget

        :param contentWidget:   the content widget from the DetachedTab window
        :param name:            the name of the detached tab
        :param icon:            the window icon for the detached tab
        :param insertAt:        insert the re-attached tab at the given index
        :return:
        """

        old_name = name

        # Make the content widget a child of this widget
        contentWidget.setParent(self)

        # make sure that we strip the 'FlatCAM' part of the detached name otherwise the tab name will be too long
        name = name.partition(' ')[2]

        # helps in restoring the tab to the same index that it was before was detached
        insert_index = self.old_index if self.use_old_index is True else insertAt

        # Create an image from the given icon (for comparison)
        if not icon.isNull():
            try:
                tabIconPixmap = icon.pixmap(icon.availableSizes()[0])
                tabIconImage = tabIconPixmap.toImage()
            except IndexError:
                tabIconImage = None
        else:
            tabIconImage = None

        # Create an image of the main window icon (for comparison)
        if not icon.isNull():
            try:
                windowIconPixmap = self.window().windowIcon().pixmap(icon.availableSizes()[0])
                windowIconImage = windowIconPixmap.toImage()
            except IndexError:
                windowIconImage = None
        else:
            windowIconImage = None

        # Determine if the given image and the main window icon are the same.
        # If they are, then do not add the icon to the tab
        if tabIconImage == windowIconImage:
            if insert_index is None:
                index = self.addTab(contentWidget, name)
            else:
                index = self.insertTab(insert_index, contentWidget, name)
        else:
            if insert_index is None:
                index = self.addTab(contentWidget, icon, name)
            else:
                index = self.insertTab(insert_index, contentWidget, icon, name)

        obj_name = contentWidget.objectName()
        self.tab_attached.emit(obj_name)

        # on reattaching the tab if protect is true then the closure button is not added
        if self.protect_tab is True:
            self.protectTab(index)

        # on reattaching the tab disable the closure button for the tabs with the name in the self.protect_by_name list
        if self.protect_by_name is not None:
            for tab_name in self.protect_by_name:
                for index in range(self.count()):
                    if str(tab_name) == str(self.tabText(index)):
                        self.protectTab(index)

            # Make this tab the current tab
            if index > -1:
                self.setCurrentIndex(insert_index) if self.use_old_index else self.setCurrentIndex(index)

        # Remove the reference
        # Unix-like OS's crash with segmentation fault after this. FOr whatever reason, they loose reference
        if sys.platform == 'win32':
            try:
                del self.detachedTabs[old_name]
            except KeyError:
                pass

    def removeTabByName(self, name):
        """
        Remove the tab with the given name, even if it is detached

        :param name: the name of the tab to be removed
        :return:
        """

        # Remove the tab if it is attached
        attached = False
        for index in range(self.count()):
            if str(name) == str(self.tabText(index)):
                self.removeTab(index)
                attached = True
                break

        # If the tab is not attached, close it's window and
        # remove the reference to it
        if not attached:
            for key in self.detachedTabs:
                if str(name) == str(key):
                    self.detachedTabs[key].onCloseSignal.disconnect()
                    self.detachedTabs[key].close()
                    del self.detachedTabs[key]
                    break

    @QtCore.pyqtSlot(str, int, QtCore.QPoint)
    def detachedTabDrop(self, name, index, dropPos):
        """
        Handle dropping of a detached tab inside the DetachableTabWidget

        :param name:        the name of the detached tab
        :param index:       the index of an existing tab (if the tab bar
    #                       determined that the drop occurred on an
    #                       existing tab)
        :param dropPos:     the mouse cursor position when the drop occurred
        :return:
        """

        # If the drop occurred on an existing tab, insert the detached
        # tab at the existing tab's location
        if index > -1:

            # Create references to the detached tab's content and icon
            contentWidget = self.detachedTabs[name].contentWidget
            icon = self.detachedTabs[name].windowIcon()

            # Disconnect the detached tab's onCloseSignal so that it
            # does not try to re-attach automatically
            self.detachedTabs[name].onCloseSignal.disconnect()

            # Close the detached
            self.detachedTabs[name].close()

            # Re-attach the tab at the given index
            self.attachTab(contentWidget, name, icon, index)

        # If the drop did not occur on an existing tab, determine if the drop
        # occurred in the tab bar area (the area to the side of the QTabBar)
        else:

            # Find the drop position relative to the DetachableTabWidget
            tabDropPos = self.mapFromGlobal(dropPos)

            # If the drop position is inside the DetachableTabWidget...
            if self.rect().contains(tabDropPos):

                # If the drop position is inside the tab bar area (the
                # area to the side of the QTabBar) or there are not tabs
                # currently attached...
                if tabDropPos.y() < self.tabBar.height() or self.count() == 0:
                    # Close the detached tab and allow it to re-attach
                    # automatically
                    self.detachedTabs[name].close()

    def closeDetachedTabs(self):
        """
        Close all tabs that are currently detached.

        :return:
        """
        listOfDetachedTabs = []

        for key in self.detachedTabs:
            listOfDetachedTabs.append(self.detachedTabs[key])

        for detachedTab in listOfDetachedTabs:
            detachedTab.close()

    class FCDetachedTab(QtWidgets.QMainWindow):
        """
        When a tab is detached, the contents are placed into this QMainWindow.  The tab
        can be re-attached by closing the dialog or by dragging the window into the tab bar
        """

        onCloseSignal = QtCore.pyqtSignal(QtWidgets.QWidget, str, QtGui.QIcon)
        onDropSignal = QtCore.pyqtSignal(str, QtCore.QPoint)

        def __init__(self, name, contentWidget):
            QtWidgets.QMainWindow.__init__(self, None)

            self.setObjectName(name)
            self.setWindowTitle(name)

            self.contentWidget = contentWidget
            self.setCentralWidget(self.contentWidget)
            self.contentWidget.show()

            self.windowDropFilter = self.WindowDropFilter()
            self.installEventFilter(self.windowDropFilter)
            self.windowDropFilter.onDropSignal.connect(self.windowDropSlot)

        @QtCore.pyqtSlot(QtCore.QPoint)
        def windowDropSlot(self, dropPos):
            """
            Handle a window drop event

            :param dropPos:     the mouse cursor position of the drop
            :return:
            """
            self.onDropSignal.emit(self.objectName(), dropPos)

        def closeEvent(self, event):
            """
            If the window is closed, emit the onCloseSignal and give the
            content widget back to the DetachableTabWidget

            :param event:    a close event
            :return:
            """
            self.onCloseSignal.emit(self.contentWidget, self.objectName(), self.windowIcon())

        class WindowDropFilter(QtCore.QObject):
            """
            An event filter class to detect a QMainWindow drop event
            """

            onDropSignal = QtCore.pyqtSignal(QtCore.QPoint)

            def __init__(self):
                QtCore.QObject.__init__(self)
                self.lastEvent = None

            def eventFilter(self, obj, event):
                """
                Detect a QMainWindow drop event by looking for a NonClientAreaMouseMove (173)
                event that immediately follows a Move event

                :param obj:     the object that generated the event
                :param event:   the current event
                :return:
                """

                # If a NonClientAreaMouseMove (173) event immediately follows a Move event...
                if self.lastEvent == QtCore.QEvent.Move and event.type() == 173:

                    # Determine the position of the mouse cursor and emit it with the
                    # onDropSignal
                    mouseCursor = QtGui.QCursor()
                    dropPos = mouseCursor.pos()
                    self.onDropSignal.emit(dropPos)
                    self.lastEvent = event.type()
                    return True

                else:
                    self.lastEvent = event.type()
                    return False

    class FCTabBar(QtWidgets.QTabBar):
        onDetachTabSignal = QtCore.pyqtSignal(int, QtCore.QPoint)
        onMoveTabSignal = QtCore.pyqtSignal(int, int)
        detachedTabDropSignal = QtCore.pyqtSignal(str, int, QtCore.QPoint)
        onCloseTabSignal = QtCore.pyqtSignal(int)
        right_click = QtCore.pyqtSignal(int)

        def __init__(self, parent=None):
            QtWidgets.QTabBar.__init__(self, parent)

            self.setAcceptDrops(True)
            self.setElideMode(QtCore.Qt.ElideRight)
            self.setSelectionBehaviorOnRemove(QtWidgets.QTabBar.SelectLeftTab)

            self.prev_index = -1

            self.dragStartPos = QtCore.QPoint()
            self.dragDropedPos = QtCore.QPoint()
            self.mouseCursor = QtGui.QCursor()
            self.dragInitiated = False

            # set this to False and the tab will no longer be displayed as detached
            self.can_be_dragged = True

        def mouseDoubleClickEvent(self, event):
            """
            Send the onDetachTabSignal when a tab is double clicked

            :param event:   a mouse double click event
            :return:
            """

            event.accept()
            self.onDetachTabSignal.emit(self.tabAt(event.pos()), self.mouseCursor.pos())

        def mousePressEvent(self, event):
            """
            Set the starting position for a drag event when the left mouse button is pressed.
            Start detection of a right mouse click.

            :param event:   a mouse press event
            :return:
            """
            if event.button() == QtCore.Qt.LeftButton:
                self.dragStartPos = event.pos()
            elif event.button() == QtCore.Qt.RightButton:
                self.prev_index = self.tabAt(event.pos())

            self.dragDropedPos.setX(0)
            self.dragDropedPos.setY(0)
            self.dragInitiated = False

            QtWidgets.QTabBar.mousePressEvent(self, event)

        def mouseReleaseEvent(self, event):
            """
            Finish the detection of the right mouse click on the tab


            :param event:   a mouse press event
            :return:
            """
            if event.button() == QtCore.Qt.RightButton and self.prev_index == self.tabAt(event.pos()):
                self.right_click.emit(self.prev_index)

            if event.button() == QtCore.Qt.MiddleButton:
                self.onCloseTabSignal.emit(int(self.tabAt(event.pos())))

            self.prev_index = -1

            QtWidgets.QTabBar.mouseReleaseEvent(self, event)

        def mouseMoveEvent(self, event):
            """
            Determine if the current movement is a drag.  If it is, convert it into a QDrag.  If the
            drag ends inside the tab bar, emit an onMoveTabSignal.  If the drag ends outside the tab
            bar, emit an onDetachTabSignal.

            :param event:   a mouse move event
            :return:
            """
            # Determine if the current movement is detected as a drag
            if not self.dragStartPos.isNull() and \
                    ((event.pos() - self.dragStartPos).manhattanLength() < QtWidgets.QApplication.startDragDistance()):
                self.dragInitiated = True

            # If the current movement is a drag initiated by the left button
            if (event.buttons() & QtCore.Qt.LeftButton) and self.dragInitiated and self.can_be_dragged:

                # Stop the move event
                finishMoveEvent = QtGui.QMouseEvent(
                    QtCore.QEvent.MouseMove, event.pos(), QtCore.Qt.NoButton, QtCore.Qt.NoButton, QtCore.Qt.NoModifier
                )
                QtWidgets.QTabBar.mouseMoveEvent(self, finishMoveEvent)

                # Convert the move event into a drag
                drag = QtGui.QDrag(self)
                mimeData = QtCore.QMimeData()
                # mimeData.setData('action', 'application/tab-detach')
                drag.setMimeData(mimeData)
                # screen = QScreen(self.parentWidget().currentWidget().winId())
                # Create the appearance of dragging the tab content
                try:
                    pixmap = self.parent().widget(self.tabAt(self.dragStartPos)).grab()
                except Exception as e:
                    log.debug("GUIElements.FCDetachable. FCTabBar.mouseMoveEvent() --> %s" % str(e))
                    return

                targetPixmap = QtGui.QPixmap(pixmap.size())
                targetPixmap.fill(QtCore.Qt.transparent)
                painter = QtGui.QPainter(targetPixmap)
                painter.setOpacity(0.85)
                painter.drawPixmap(0, 0, pixmap)
                painter.end()
                drag.setPixmap(targetPixmap)

                # Initiate the drag
                dropAction = drag.exec_(QtCore.Qt.MoveAction | QtCore.Qt.CopyAction)

                # For Linux:  Here, drag.exec_() will not return MoveAction on Linux.  So it
                #             must be set manually
                if self.dragDropedPos.x() != 0 and self.dragDropedPos.y() != 0:
                    dropAction = QtCore.Qt.MoveAction

                # If the drag completed outside of the tab bar, detach the tab and move
                # the content to the current cursor position
                if dropAction == QtCore.Qt.IgnoreAction:
                    event.accept()
                    self.onDetachTabSignal.emit(self.tabAt(self.dragStartPos), self.mouseCursor.pos())

                # Else if the drag completed inside the tab bar, move the selected tab to the new position
                elif dropAction == QtCore.Qt.MoveAction:
                    if not self.dragDropedPos.isNull():
                        event.accept()
                        self.onMoveTabSignal.emit(self.tabAt(self.dragStartPos), self.tabAt(self.dragDropedPos))
            else:
                QtWidgets.QTabBar.mouseMoveEvent(self, event)

        def dragEnterEvent(self, event):
            """
            Determine if the drag has entered a tab position from another tab position

            :param event:   a drag enter event
            :return:
            """
            mimeData = event.mimeData()
            # formats = mcd imeData.formats()

            # if formats.contains('action') and mimeData.data('action') == 'application/tab-detach':
            # event.acceptProposedAction()

            QtWidgets.QTabBar.dragMoveEvent(self, event)

        def dropEvent(self, event):
            """
            Get the position of the end of the drag

            :param event:    a drop event
            :return:
            """
            self.dragDropedPos = event.pos()
            QtWidgets.QTabBar.dropEvent(self, event)

        def detachedTabDrop(self, name, dropPos):
            """
            Determine if the detached tab drop event occurred on an existing tab,
            then send the event to the DetachableTabWidget

            :param name:
            :param dropPos:
            :return:
            """
            tabDropPos = self.mapFromGlobal(dropPos)

            index = self.tabAt(tabDropPos)

            self.detachedTabDropSignal.emit(name, index, dropPos)


class FCDetachableTab2(FCDetachableTab):
    tab_closed_signal = QtCore.pyqtSignal(object, int)

    def __init__(self, protect=None, protect_by_name=None, parent=None):
        super(FCDetachableTab2, self).__init__(protect=protect, protect_by_name=protect_by_name, parent=parent)

        try:
            self.tabBar.onCloseTabSignal.disconnect()
        except TypeError:
            pass

        self.tabBar.onCloseTabSignal.connect(self.on_closetab_middle_button)

    def on_closetab_middle_button(self, current_index):
        """

        :param current_index:
        :return:
        """

        # if tab is protected don't delete it
        if self.tabBar.tabButton(current_index, QtWidgets.QTabBar.RightSide) is not None:
            self.closeTab(current_index)

    def closeTab(self, currentIndex):
        """
        Slot connected to the tabCloseRequested signal

        :param currentIndex:
        :return:
        """
        # idx = self.currentIndex()
        tab_name = self.widget(currentIndex).objectName()
        self.tab_closed_signal.emit(tab_name, currentIndex)

        self.removeTab(currentIndex)


class VerticalScrollArea(QtWidgets.QScrollArea):
    """
    This widget extends QtGui.QScrollArea to make a vertical-only
    scroll area that also expands horizontally to accommodate
    its contents.
    """

    def __init__(self, parent=None):
        QtWidgets.QScrollArea.__init__(self, parent=parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

    def eventFilter(self, source, event):
        """
        The event filter gets automatically installed when setWidget()
        is called.

        :param source:
        :param event:
        :return:
        """
        if event.type() == QtCore.QEvent.Resize and source == self.widget():
            # log.debug("VerticalScrollArea: Widget resized:")
            # log.debug(" minimumSizeHint().width() = %d" % self.widget().minimumSizeHint().width())
            # log.debug(" verticalScrollBar().width() = %d" % self.verticalScrollBar().width())

            self.setMinimumWidth(self.widget().sizeHint().width() +
                                 self.verticalScrollBar().sizeHint().width())

            # if self.verticalScrollBar().isVisible():
            #     log.debug(" Scroll bar visible")
            #     self.setMinimumWidth(self.widget().minimumSizeHint().width() +
            #                          self.verticalScrollBar().width())
            # else:
            #     log.debug(" Scroll bar hidden")
            #     self.setMinimumWidth(self.widget().minimumSizeHint().width())
        return QtWidgets.QWidget.eventFilter(self, source, event)


class OptionalInputSection:

    def __init__(self, cb, optinputs, logic=True):
        """
        Associates the a checkbox with a set of inputs.

        :param cb: Checkbox that enables the optional inputs.
        :param optinputs: List of widgets that are optional.
        :param logic: When True the logic is normal, when False the logic is in reverse
        It means that for logic=True, when the checkbox is checked the widgets are Enabled, and
        for logic=False, when the checkbox is checked the widgets are Disabled
        :return:
        """
        assert isinstance(cb, FCCheckBox), \
            "Expected an FCCheckBox, got %s" % type(cb)

        self.cb = cb
        self.optinputs = optinputs
        self.logic = logic

        self.on_cb_change()
        self.cb.stateChanged.connect(self.on_cb_change)

    def on_cb_change(self):

        if self.cb.checkState():
            for widget in self.optinputs:
                if self.logic is True:
                    widget.setEnabled(True)
                else:
                    widget.setEnabled(False)
        else:
            for widget in self.optinputs:
                if self.logic is True:
                    widget.setEnabled(False)
                else:
                    widget.setEnabled(True)


class OptionalHideInputSection:

    def __init__(self, cb, optinputs, logic=True):
        """
        Associates the a checkbox with a set of inputs.

        :param cb:          Checkbox that enables the optional inputs.
        :type cb:           QtWidgets.QCheckBox
        :param optinputs:   List of widgets that are optional.
        :type optinputs:    list
        :param logic:       When True the logic is normal, when False the logic is in reverse
                            It means that for logic=True, when the checkbox is checked the widgets are Enabled, and
                            for logic=False, when the checkbox is checked the widgets are Disabled
        :type logic:        bool
        :return:
        """
        assert isinstance(cb, FCCheckBox), \
            "Expected an FCCheckBox, got %s" % type(cb)

        self.cb = cb
        self.optinputs = optinputs
        self.logic = logic

        self.on_cb_change()
        self.cb.stateChanged.connect(self.on_cb_change)

    def on_cb_change(self):

        if self.cb.checkState():
            for widget in self.optinputs:
                if self.logic is True:
                    widget.show()
                else:
                    widget.hide()
        else:
            for widget in self.optinputs:
                if self.logic is True:
                    widget.hide()
                else:
                    widget.show()


class FCTable(QtWidgets.QTableWidget):
    drag_drop_sig = QtCore.pyqtSignal(object, int)
    lost_focus = QtCore.pyqtSignal()

    def __init__(self, drag_drop=False, protected_rows=None, parent=None):
        super(FCTable, self).__init__(parent)

        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Inactive, QtGui.QPalette.Highlight,
                         palette.color(QtGui.QPalette.Active, QtGui.QPalette.Highlight))

        # make inactive rows text some color as active; may be useful in the future
        palette.setColor(QtGui.QPalette.Inactive, QtGui.QPalette.HighlightedText,
                         palette.color(QtGui.QPalette.Active, QtGui.QPalette.HighlightedText))
        self.setPalette(palette)

        if drag_drop:
            self.setDragEnabled(True)
            self.setAcceptDrops(True)
            self.viewport().setAcceptDrops(True)
            self.setDragDropOverwriteMode(False)
            self.setDropIndicatorShown(True)

            self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
            self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)

        self.rows_not_for_drag_and_drop = []
        if protected_rows:
            try:
                for r in protected_rows:
                    self.rows_not_for_drag_and_drop.append(r)
            except TypeError:
                self.rows_not_for_drag_and_drop = [protected_rows]

        self.rows_to_move = []
        self.rows_dragged = None

    def sizeHint(self):
        default_hint_size = super(FCTable, self).sizeHint()
        return QtCore.QSize(EDIT_SIZE_HINT, default_hint_size.height())

    def getHeight(self):
        height = self.horizontalHeader().height()
        for i in range(self.rowCount()):
            height += self.rowHeight(i)
        return height

    def getWidth(self):
        width = self.verticalHeader().width()
        for i in range(self.columnCount()):
            width += self.columnWidth(i)
        return width

    # color is in format QtGui.Qcolor(r, g, b, alpha) with or without alpha
    def setColortoRow(self, rowIndex, color):
        for j in range(self.columnCount()):
            self.item(rowIndex, j).setBackground(color)

    # if user is clicking an blank area inside the QTableWidget it will deselect currently selected rows
    def mousePressEvent(self, event):
        clicked_item = self.itemAt(event.pos())
        if not clicked_item:
            self.clearSelection()
            self.clearFocus()
        else:
            self.rows_dragged = [it.row() for it in self.selectedItems()]
            QtWidgets.QTableWidget.mousePressEvent(self, event)

    def focusOutEvent(self, event):
        self.lost_focus.emit()
        super().focusOutEvent(event)

    def setupContextMenu(self):
        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

    def addContextMenu(self, entry, call_function, icon=None):
        action_name = str(entry)
        action = QtWidgets.QAction(self)
        action.setText(action_name)
        if icon:
            assert isinstance(icon, QtGui.QIcon), \
                "Expected the argument to be QtGui.QIcon. Instead it is %s" % type(icon)
            action.setIcon(icon)
        self.addAction(action)
        action.triggered.connect(call_function)

    # def dropEvent(self, event: QtGui.QDropEvent):
    #     if not event.isAccepted() and event.source() == self:
    #         drop_row = self.drop_on(event)
    #
    #         rows = sorted(set(item.row() for item in self.selectedItems()))
    #         # rows_to_move = [
    #         #     [QtWidgets.QTableWidgetItem(self.item(row_index, column_index))
    #         #      for column_index in range(self.columnCount())] for row_index in rows
    #         # ]
    #         self.rows_to_move[:] = []
    #         for row_index in rows:
    #             row_items = []
    #             for column_index in range(self.columnCount()):
    #                 r_item = self.item(row_index, column_index)
    #                 w_item = self.cellWidget(row_index, column_index)
    #
    #                 if r_item is not None:
    #                     row_items.append(QtWidgets.QTableWidgetItem(r_item))
    #                 elif w_item is not None:
    #                     row_items.append(w_item)
    #
    #             self.rows_to_move.append(row_items)
    #
    #         for row_index in reversed(rows):
    #             self.removeRow(row_index)
    #             if row_index < drop_row:
    #                 drop_row -= 1
    #
    #         for row_index, data in enumerate(self.rows_to_move):
    #             row_index += drop_row
    #             self.insertRow(row_index)
    #
    #             for column_index, column_data in enumerate(data):
    #                 if isinstance(column_data, QtWidgets.QTableWidgetItem):
    #                     self.setItem(row_index, column_index, column_data)
    #                 else:
    #                     self.setCellWidget(row_index, column_index, column_data)
    #
    #         event.accept()
    #         for row_index in range(len(self.rows_to_move)):
    #             self.item(drop_row + row_index, 0).setSelected(True)
    #             self.item(drop_row + row_index, 1).setSelected(True)
    #
    #     super().dropEvent(event)
    #
    # def drop_on(self, event):
    #     ret_val = False
    #     index = self.indexAt(event.pos())
    #     if not index.isValid():
    #         return self.rowCount()
    #
    #     ret_val = index.row() + 1 if self.is_below(event.pos(), index) else index.row()
    #
    #     return ret_val
    #
    # def is_below(self, pos, index):
    #     rect = self.visualRect(index)
    #     margin = 2
    #     if pos.y() - rect.top() < margin:
    #         return False
    #     elif rect.bottom() - pos.y() < margin:
    #         return True
    #     # noinspection PyTypeChecker
    #     return rect.contains(pos, True) and not (
    #                 int(self.model().flags(index)) & Qt.ItemIsDropEnabled) and pos.y() >= rect.center().y()

    def dragEnterEvent(self, e: QtGui.QDragEnterEvent) -> None:
        if e.source() == self:
            self.blockSignals(True)
            e.accept()
        else:
            e.ignore()

    # def dropEvent(self, event):
    #     """
    #     From here: https://stackoverflow.com/questions/26227885/drag-and-drop-rows-within-qtablewidget
    #     :param event:
    #     :return:
    #     """
    #     if event.source() == self:
    #         event.acceptProposedAction()
    #
    #         # create a set of the selected rows that are dragged to another position
    #         rows = set([mi.row() for mi in self.selectedIndexes()])
    #         # if one of the selected rows for drag and drop is within the protected list, return
    #         for r in rows:
    #             if r in self.rows_not_for_drag_and_drop:
    #                 return
    #
    #         drop_index = self.indexAt(event.pos())
    #         # row where we drop the selected rows
    #         targetRow = drop_index.row()
    #
    #         # drop_indicator = self.dropIndicatorPosition()
    #         # if targetRow != -1:
    #         #     if drop_indicator == QtWidgets.QAbstractItemView.AboveItem:
    #         #         print("above")
    #         #     elif drop_indicator == QtWidgets.QAbstractItemView.BelowItem:
    #         #         print("below")
    #         #     elif drop_indicator == QtWidgets.QAbstractItemView.OnItem:
    #         #         print("on")
    #         #     elif drop_indicator == QtWidgets.QAbstractItemView.OnViewport:
    #         #         print("on viewport")
    #
    #         # if we drop on one row from the already dragged rows
    #         rows.discard(targetRow)
    #         rows = sorted(rows)
    #         if not rows:
    #             return
    #         if targetRow == -1:
    #             targetRow = self.rowCount()
    #
    #         # insert empty rows at the index of the targetRow
    #         for _ in range(len(rows)):
    #             self.insertRow(targetRow)
    #
    #         rowMapping = {}  # Src row to target row.
    #         for idx, row in enumerate(rows):
    #             if row < targetRow:
    #                 rowMapping[row] = targetRow + idx
    #             else:
    #                 rowMapping[row + len(rows)] = targetRow + idx
    #
    #         colCount = self.columnCount()
    #         for srcRow, tgtRow in sorted(rowMapping.items()):
    #             for col in range(0, colCount):
    #                 new_item = self.item(srcRow, col)
    #                 if new_item is None:
    #                     new_item = self.cellWidget(srcRow, col)
    #
    #                 if isinstance(new_item, QtWidgets.QTableWidgetItem):
    #                     new_item = self.takeItem(srcRow, col)
    #                     self.setItem(tgtRow, col, new_item)
    #                 else:
    #                     self.setCellWidget(tgtRow, col, new_item)
    #
    #         for row in reversed(sorted(rowMapping.keys())):
    #             self.removeRow(row)
    #
    #         self.blockSignals(False)
    #         self.drag_drop_sig.emit(int(self.row_dragged), int(targetRow))
    #     else:
    #         event.ignore()

    def dropEvent(self, event: QtGui.QDropEvent):
        if not event.isAccepted() and event.source() == self:
            drop_row = self.drop_on(event)

            rows = sorted(set(item.row() for item in self.selectedItems()))

            rows_to_move = []
            for row_index in rows:
                temp_lst = []
                for column_index in range(self.columnCount()):
                    col_data = self.item(row_index, column_index)

                    if isinstance(col_data, QtWidgets.QTableWidgetItem):
                        table_item = QtWidgets.QTableWidgetItem(col_data)
                    else:
                        old_item = self.cellWidget(row_index, column_index)
                        if isinstance(old_item, QtWidgets.QComboBox):
                            table_item = FCComboBox()
                            items = [old_item.itemText(i) for i in range(old_item.count())]
                            table_item.addItems(items)
                            table_item.setCurrentIndex(old_item.currentIndex())
                        elif isinstance(old_item, QtWidgets.QCheckBox):
                            table_item = FCCheckBox()
                            table_item.setChecked(old_item.isChecked())
                            table_item.setText(old_item.text())
                        else:
                            table_item = None

                    temp_lst.append(table_item)
                rows_to_move.append(temp_lst)

            for row_index in reversed(rows):
                self.removeRow(row_index)
                if row_index < drop_row:
                    drop_row -= 1

            for row_index, data in enumerate(rows_to_move):
                row_index += drop_row
                self.insertRow(row_index)
                for column_index, column_data in enumerate(data):
                    if column_data is None:
                        continue

                    if isinstance(column_data, QtWidgets.QTableWidgetItem):
                        self.setItem(row_index, column_index, column_data)
                    else:
                        self.setCellWidget(row_index, column_index, column_data)
            event.accept()
            for row_index in range(len(rows_to_move)):
                self.item(drop_row + row_index, 0).setSelected(True)
                self.item(drop_row + row_index, 1).setSelected(True)

            self.blockSignals(False)
            self.drag_drop_sig.emit(self.rows_dragged, int(drop_row))

        self.blockSignals(False)
        self.resizeRowsToContents()
        super().dropEvent(event)

    def drop_on(self, event):
        index = self.indexAt(event.pos())
        if not index.isValid():
            return self.rowCount()

        return index.row() + 1 if self.is_below(event.pos(), index) else index.row()

    def is_below(self, pos, index):
        rect = self.visualRect(index)
        margin = 2
        if pos.y() - rect.top() < margin:
            return False
        elif rect.bottom() - pos.y() < margin:
            return True
        # noinspection PyTypeChecker
        return rect.contains(pos, True) and not (int(self.model().flags(index)) & Qt.ItemIsDropEnabled) and \
               pos.y() >= rect.center().y()


class SpinBoxDelegate(QtWidgets.QItemDelegate):

    def __init__(self, units):
        super(SpinBoxDelegate, self).__init__()
        self.units = units
        self.current_value = None

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QDoubleSpinBox(parent)
        editor.setMinimum(-999.9999)
        editor.setMaximum(999.9999)

        if self.units == 'MM':
            editor.setDecimals(2)
        else:
            editor.setDecimals(3)

        return editor

    def setEditorData(self, spinBox, index):
        try:
            value = float(index.model().data(index, Qt.EditRole))
        except ValueError:
            value = self.current_value
            # return

        spinBox.setValue(value)

    def setModelData(self, spinBox, model, index):
        spinBox.interpretText()
        value = spinBox.value()
        self.current_value = value

        model.setData(index, value, Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

    @staticmethod
    def setDecimals(spinbox, digits):
        spinbox.setDecimals(digits)


class Dialog_box(QtWidgets.QWidget):
    def __init__(self, title=None, label=None, icon=None, initial_text=None):
        """

        :param title: string with the window title
        :param label: string with the message inside the dialog box
        """
        super(Dialog_box, self).__init__()
        if initial_text is None:
            self.location = str((0, 0))
        else:
            self.location = initial_text

        self.ok = False

        self.dialog_box = QtWidgets.QInputDialog()
        self.dialog_box.setMinimumWidth(290)
        self.setWindowIcon(icon)

        self.location, self.ok = self.dialog_box.getText(self, title, label,
                                                         text=str(self.location).replace('(', '').replace(')', ''))
        self.readyToEdit = True

    def mousePressEvent(self, e, parent=None):
        super(Dialog_box, self).mousePressEvent(e)  # required to deselect on 2e click
        if self.readyToEdit:
            self.lineEdit().selectAll()
            self.readyToEdit = False

    def focusOutEvent(self, e):
        # don't focus out if the user requests an popup menu
        if e.reason() != QtCore.Qt.PopupFocusReason:
            super(Dialog_box, self).focusOutEvent(e)  # required to remove cursor on focusOut
            self.lineEdit().deselect()
            self.readyToEdit = True


class DialogBoxRadio(QtWidgets.QDialog):
    def __init__(self, title=None, label=None, icon=None, initial_text=None, reference='abs', parent=None):
        """

        :param title: string with the window title
        :param label: string with the message inside the dialog box
        """
        super(DialogBoxRadio, self).__init__(parent=parent)
        if initial_text is None:
            self.location = str((0, 0))
        else:
            self.location = initial_text

        self.ok = False

        self.setWindowIcon(icon)
        self.setWindowTitle(str(title))

        self.form = QtWidgets.QFormLayout(self)

        self.ref_label = QtWidgets.QLabel('%s:' % _("Reference"))
        self.ref_label.setToolTip(
            _("The reference can be:\n"
              "- Absolute -> the reference point is point (0,0)\n"
              "- Relative -> the reference point is the mouse position before Jump")
        )
        self.ref_radio = RadioSet([
            {"label": _("Abs"), "value": "abs"},
            {"label": _("Relative"), "value": "rel"}
        ], orientation='horizontal', stretch=False)
        self.ref_radio.set_value(reference)
        self.form.addRow(self.ref_label, self.ref_radio)

        self.form.addRow(QtWidgets.QLabel(''))

        self.wdg_label = QtWidgets.QLabel('<b>%s</b>' % str(label))
        self.form.addRow(self.wdg_label)

        self.loc_label = QtWidgets.QLabel('%s:' % _("Location"))
        self.loc_label.setToolTip(
            _("The Location value is a tuple (x,y).\n"
              "If the reference is Absolute then the Jump will be at the position (x,y).\n"
              "If the reference is Relative then the Jump will be at the (x,y) distance\n"
              "from the current mouse location point.")
        )
        self.lineEdit = EvalEntry(parent=self)
        self.lineEdit.setText(str(self.location).replace('(', '').replace(')', ''))
        self.lineEdit.selectAll()
        self.lineEdit.setFocus()
        self.form.addRow(self.loc_label, self.lineEdit)

        self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
                                                     orientation=Qt.Horizontal, parent=self)
        self.form.addRow(self.button_box)

        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setText(_("Ok"))
        self.button_box.button(QtWidgets.QDialogButtonBox.Cancel).setText(_("Cancel"))

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.readyToEdit = True

        if self.exec_() == QtWidgets.QDialog.Accepted:
            self.ok = True
            self.location = self.lineEdit.text()
            self.reference = self.ref_radio.get_value()
        else:
            self.ok = False


class _BrowserTextEdit(QTextEdit):

    def __init__(self, version, app=None):
        QTextEdit.__init__(self)
        self.menu = None
        self.version = version
        self.app = app

    def contextMenuEvent(self, event):
        # self.menu = self.createStandardContextMenu(event.pos())
        self.menu = QtWidgets.QMenu()
        tcursor = self.textCursor()
        txt = tcursor.selectedText()

        copy_action = QAction('%s\t%s' % (_("Copy"), _('Ctrl+C')), self)
        self.menu.addAction(copy_action)
        copy_action.triggered.connect(self.copy_text)
        if txt == '':
            copy_action.setDisabled(True)

        self.menu.addSeparator()

        sel_all_action = QAction('%s\t%s' % (_("Select All"), _('Ctrl+A')), self)
        self.menu.addAction(sel_all_action)
        sel_all_action.triggered.connect(self.selectAll)

        if self.app:
            save_action = QAction('%s\t%s' % (_("Save Log"), _('Ctrl+S')), self)
            # save_action.setShortcut(QKeySequence(Qt.Key_S))
            self.menu.addAction(save_action)
            save_action.triggered.connect(lambda: self.save_log(app=self.app))

        clear_action = QAction('%s\t%s' % (_("Clear All"), _('Del')), self)
        # clear_action.setShortcut(QKeySequence(Qt.Key_Delete))
        self.menu.addAction(clear_action)
        clear_action.triggered.connect(self.clear)

        # if self.app:
        #     close_action = QAction(_("Close"), self)
        #     self.menu.addAction(close_action)
        #     close_action.triggered.connect(lambda: self.app.ui.shell_dock.hide())

        self.menu.exec_(event.globalPos())

    def keyPressEvent(self, event) -> None:
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        key = event.key()

        if modifiers == QtCore.Qt.ControlModifier:
            # Select All
            if key == QtCore.Qt.Key_A:
                self.selectAll()
            # Copy Text
            elif key == QtCore.Qt.Key_C:
                self.copy_text()
            # Save Log
            elif key == QtCore.Qt.Key_S:
                if self.app:
                    self.save_log(app=self.app)

        elif modifiers == QtCore.Qt.NoModifier:
            # Clear all
            if key == QtCore.Qt.Key_Delete:
                self.clear()
            # Shell toggle
            if key == QtCore.Qt.Key_S:
                self.app.ui.toggle_shell_ui()

    def copy_text(self):
        tcursor = self.textCursor()
        clipboard = QtWidgets.QApplication.clipboard()

        txt = tcursor.selectedText()
        clipboard.clear()
        clipboard.setText(txt)

    def clear(self):
        QTextEdit.clear(self)

        text = "!FlatCAM %s? - %s" % (self.version, _("Type >help< to get started"))
        text = html.escape(text)
        # hack so I can make text bold because the escape method will replace the '<' and '>' signs with html code
        text = text.replace('!', '<b>')
        text = text.replace('?', '</b>')
        text += '<br><br>'
        self.moveCursor(QTextCursor.End)
        self.insertHtml(text)

    def save_log(self, app):
        html_content = self.toHtml()
        txt_content = self.toPlainText()
        app.save_to_file(content_to_save=html_content, txt_content=txt_content)


class _ExpandableTextEdit(FCTextEdit):
    """
    Class implements edit line, which expands themselves automatically
    """

    historyNext = QtCore.pyqtSignal()
    historyPrev = QtCore.pyqtSignal()

    def __init__(self, termwidget, *args):
        FCTextEdit.__init__(self, *args)
        self.setStyleSheet("font: 9pt \"Courier\";")
        self._fittedHeight = 1
        self.textChanged.connect(self._fit_to_document)
        self._fit_to_document()
        self._termWidget = termwidget

        self.completer = MyCompleter()

        self.model = QtCore.QStringListModel()
        self.completer.setModel(self.model)
        self.set_model_data(keyword_list=[])
        self.completer.insertText.connect(self.insertCompletion)
        self.completer.popup().clicked.connect(self.insert_completion_click)

    def set_model_data(self, keyword_list):
        self.model.setStringList(keyword_list)

    def insert_completion_click(self):
        self.completer.insertText.emit(self.completer.getSelected())
        self.completer.setCompletionMode(QCompleter.PopupCompletion)

    def insertCompletion(self, completion):
        tc = self.textCursor()
        extra = (len(completion) - len(self.completer.completionPrefix()))

        # don't insert if the word is finished but add a space instead
        if extra == 0:
            tc.insertText(' ')
            self.completer.popup().hide()
            return

        tc.movePosition(QTextCursor.Left)
        tc.movePosition(QTextCursor.EndOfWord)
        tc.insertText(completion[-extra:])
        # add a space after inserting the word
        tc.insertText(' ')
        self.setTextCursor(tc)
        self.completer.popup().hide()

    def focusInEvent(self, event):
        if self.completer:
            self.completer.setWidget(self)
        QTextEdit.focusInEvent(self, event)

    def keyPressEvent(self, event):
        """
        Catch keyboard events. Process Enter, Up, Down
        """

        key = event.key()
        if (key == Qt.Key_Tab or key == Qt.Key_Return or key == Qt.Key_Enter) and self.completer.popup().isVisible():
            self.completer.insertText.emit(self.completer.getSelected())
            self.completer.setCompletionMode(QCompleter.PopupCompletion)
            return

        if event.matches(QKeySequence.InsertParagraphSeparator):
            text = self.toPlainText()
            if self._termWidget.is_command_complete(text):
                self._termWidget.exec_current_command()
                return
        elif event.matches(QKeySequence.MoveToNextLine):
            text = self.toPlainText()
            cursor_pos = self.textCursor().position()
            textBeforeEnd = text[cursor_pos:]

            if len(textBeforeEnd.split('\n')) <= 1:
                self.historyNext.emit()
                return
        elif event.matches(QKeySequence.MoveToPreviousLine):
            text = self.toPlainText()
            cursor_pos = self.textCursor().position()
            text_before_start = text[:cursor_pos]
            # lineCount = len(textBeforeStart.splitlines())
            line_count = len(text_before_start.split('\n'))
            if len(text_before_start) > 0 and \
                    (text_before_start[-1] == '\n' or text_before_start[-1] == '\r'):
                line_count += 1
            if line_count <= 1:
                self.historyPrev.emit()
                return
        elif event.matches(QKeySequence.MoveToNextPage) or event.matches(QKeySequence.MoveToPreviousPage):
            return self._termWidget.browser().keyPressEvent(event)

        tc = self.textCursor()

        QTextEdit.keyPressEvent(self, event)
        tc.select(QTextCursor.WordUnderCursor)
        cr = self.cursorRect()

        if len(tc.selectedText()) > 0:
            self.completer.setCompletionPrefix(tc.selectedText())
            popup = self.completer.popup()
            popup.setCurrentIndex(self.completer.completionModel().index(0, 0))

            cr.setWidth(self.completer.popup().sizeHintForColumn(0)
                        + self.completer.popup().verticalScrollBar().sizeHint().width())
            self.completer.complete(cr)
        else:
            self.completer.popup().hide()

    def sizeHint(self):
        """
        QWidget sizeHint impelemtation
        """
        hint = QTextEdit.sizeHint(self)
        hint.setHeight(self._fittedHeight)
        return hint

    def _fit_to_document(self):
        """
        Update widget height to fit all text
        """
        documentsize = self.document().size().toSize()
        self._fittedHeight = documentsize.height() + (self.height() - self.viewport().height())
        self.setMaximumHeight(self._fittedHeight)
        self.updateGeometry()

    def insertFromMimeData(self, mime_data):
        # Paste only plain text.
        self.insertPlainText(mime_data.text())


class MyCompleter(QCompleter):
    insertText = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        QCompleter.__init__(self, parent=parent)
        self.setCompletionMode(QCompleter.PopupCompletion)
        self.highlighted.connect(self.setHighlighted)

        self.lastSelected = ''

        # self.popup().installEventFilter(self)

    # def eventFilter(self, obj, event):
    #     if event.type() == QtCore.QEvent.Wheel and obj is self.popup():
    #         pass
    #     return False

    def setHighlighted(self, text):
        self.lastSelected = text

    def getSelected(self):
        return self.lastSelected


class FCTextAreaLineNumber(QtWidgets.QFrame):
    textChanged = QtCore.pyqtSignal()

    class NumberBar(QtWidgets.QWidget):

        def __init__(self, edit):
            QtWidgets.QWidget.__init__(self, edit)

            self.edit = edit
            self.adjustWidth(1)

        def paintEvent(self, event):
            self.edit.numberbarPaint(self, event)
            QtWidgets.QWidget.paintEvent(self, event)

        def adjustWidth(self, count):
            # three spaces added to the width to make up for the space added in the line number
            width = self.fontMetrics().width(str(count) + '   ')
            if self.width() != width:
                self.setFixedWidth(width)

        def updateContents(self, rect, scroll):
            if scroll:
                self.scroll(0, scroll)
            else:
                # It would be nice to do
                # self.update(0, rect.y(), self.width(), rect.height())
                # But we can't because it will not remove the bold on the
                # current line if word wrap is enabled and a new block is
                # selected.
                self.update()

    class PlainTextEdit(FCPlainTextAreaExtended):
        """
        TextEdit with line numbers and highlight
        From here: https://nachtimwald.com/2009/08/19/better-qplaintextedit-with-line-numbers/
        and from here: https://doc.qt.io/qt-5/qtwidgets-widgets-codeeditor-example.html
        """

        def __init__(self, *args):
            FCPlainTextAreaExtended.__init__(self, *args)

            # self.setFrameStyle(QFrame.NoFrame)
            self.setFrameStyle(QtWidgets.QFrame.NoFrame)
            self.highlight()
            # self.setLineWrapMode(QPlainTextEdit.NoWrap)
            self.cursorPositionChanged.connect(self.highlight)

        def highlight(self):
            hi_selection = QTextEdit.ExtraSelection()

            hi_selection.format.setBackground(self.palette().alternateBase())
            hi_selection.format.setProperty(QtGui.QTextFormat.FullWidthSelection, True)
            hi_selection.cursor = self.textCursor()
            hi_selection.cursor.clearSelection()

            self.setExtraSelections([hi_selection])

        def numberbarPaint(self, number_bar, event):
            font_metrics = self.fontMetrics()
            current_line = self.document().findBlock(self.textCursor().position()).blockNumber() + 1

            painter = QtGui.QPainter(number_bar)
            painter.fillRect(event.rect(), QtCore.Qt.lightGray)

            block = self.firstVisibleBlock()
            line_count = int(block.blockNumber())
            block_top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
            block_bottom = block_top + int(self.blockBoundingRect(block).height())

            # Iterate over all visible text blocks in the document.
            while block.isValid() and block_top <= event.rect().bottom():
                line_count += 1

                # Check if the position of the block is out side of the visible
                # area.
                if block.isVisible() and block_bottom >= event.rect().top():

                    # We want the line number for the selected line to be bold.
                    if line_count == current_line:
                        font = painter.font()
                        font.setBold(True)
                        painter.setPen(QtCore.Qt.blue)
                        painter.setFont(font)
                    else:
                        font = painter.font()
                        font.setBold(False)
                        painter.setPen(self.palette().base().color())
                        painter.setFont(font)

                    # Draw the line number right justified at the position of the line.
                    paint_rect = QtCore.QRect(0, block_top, number_bar.width(), font_metrics.height())
                    # I add some spaces to the line_count to prettify; make sure to remember adjust the width in the
                    # NumberBar() class above
                    painter.drawText(paint_rect, Qt.AlignRight, ' ' + str(line_count) + '  ')

                block = block.next()
                block_top = block_bottom
                block_bottom = block_top + self.blockBoundingRect(block).height()

            painter.end()

    def __init__(self, *args):
        QtWidgets.QFrame.__init__(self, *args)

        self.setFrameStyle(QtWidgets.QFrame.StyledPanel | QtWidgets.QFrame.Sunken)

        self.edit = self.PlainTextEdit()
        self.number_bar = self.NumberBar(self.edit)

        hbox = QtWidgets.QHBoxLayout(self)
        hbox.setSpacing(0)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.addWidget(self.number_bar)
        hbox.addWidget(self.edit)

        self.edit.blockCountChanged.connect(self.number_bar.adjustWidth)
        self.edit.updateRequest.connect(self.number_bar.updateContents)

    def getText(self):
        return str(self.edit.toPlainText())

    def setText(self, text):
        self.edit.setPlainText(text)

    def isModified(self):
        return self.edit.document().isModified()

    def setModified(self, modified):
        self.edit.document().setModified(modified)

    def setLineWrapMode(self, mode):
        self.edit.setLineWrapMode(mode)


class FCFileSaveDialog(QtWidgets.QFileDialog):

    def __init__(self, *args):
        super(FCFileSaveDialog, self).__init__(*args)

    @staticmethod
    def get_saved_filename(parent=None, caption='', directory='', ext_filter='', initialFilter=''):
        filename, _filter = QtWidgets.QFileDialog.getSaveFileName(parent=parent, caption=caption,
                                                                  directory=directory, filter=ext_filter,
                                                                  initialFilter=initialFilter)

        filename = str(filename)
        if filename == '':
            return filename, _filter

        extension = '.' + _filter.strip(')').rpartition('.')[2]

        if filename.endswith(extension) or extension == '.*':
            return filename, _filter
        else:
            filename += extension
            return filename, _filter


class FCDock(QtWidgets.QDockWidget):

    def __init__(self, *args, **kwargs):
        super(FCDock, self).__init__(*args)
        self.close_callback = kwargs["close_callback"] if "close_callback" in kwargs else None

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.close_callback()
        super().closeEvent(event)

    def show(self) -> None:
        if self.isFloating():
            self.setFloating(False)
        super().show()


class FCJog(QtWidgets.QFrame):

    def __init__(self, app, *args, **kwargs):
        super(FCJog, self).__init__(*args, **kwargs)

        self.app = app
        self.setFrameShape(QtWidgets.QFrame.Box)
        self.setLineWidth(1)

        # JOG axes
        grbl_jog_grid = QtWidgets.QGridLayout()
        grbl_jog_grid.setAlignment(QtCore.Qt.AlignCenter)
        grbl_jog_grid.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
        grbl_jog_grid.setContentsMargins(2, 4, 2, 4)

        self.setLayout(grbl_jog_grid)

        # JOG Y Up
        self.jog_up_button = QtWidgets.QToolButton()
        self.jog_up_button.setIcon(QtGui.QIcon(self.app.resource_location + '/up-arrow32.png'))
        self.jog_up_button.setToolTip(
            _("Jog the Y axis.")
        )
        grbl_jog_grid.addWidget(self.jog_up_button, 2, 1)

        # Origin
        self.jog_origin_button = QtWidgets.QToolButton()
        self.jog_origin_button.setIcon(QtGui.QIcon(self.app.resource_location + '/origin2_32.png'))
        self.jog_origin_button.setToolTip(
            '%s' % _("Move to Origin")
        )

        grbl_jog_grid.addWidget(self.jog_origin_button, 3, 1)

        # JOG Y Down
        self.jog_down_button = QtWidgets.QToolButton()
        self.jog_down_button.setIcon(QtGui.QIcon(self.app.resource_location + '/down-arrow32.png'))
        self.jog_down_button.setToolTip(
            _("Jog the Y axis.")
        )
        grbl_jog_grid.addWidget(self.jog_down_button, 4, 1)

        # JOG X Left
        self.jog_left_button = QtWidgets.QToolButton()
        self.jog_left_button.setIcon(QtGui.QIcon(self.app.resource_location + '/left_arrow32.png'))
        self.jog_left_button.setToolTip(
            _("Jog the X axis.")
        )
        grbl_jog_grid.addWidget(self.jog_left_button, 3, 0)

        # JOG X Right
        self.jog_right_button = QtWidgets.QToolButton()
        self.jog_right_button.setIcon(QtGui.QIcon(self.app.resource_location + '/right_arrow32.png'))
        self.jog_right_button.setToolTip(
            _("Jog the X axis.")
        )
        grbl_jog_grid.addWidget(self.jog_right_button, 3, 2)

        # JOG Z Up
        self.jog_z_up_button = QtWidgets.QToolButton()
        self.jog_z_up_button.setIcon(QtGui.QIcon(self.app.resource_location + '/up-arrow32.png'))
        self.jog_z_up_button.setText('Z')
        self.jog_z_up_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.jog_z_up_button.setToolTip(
            _("Jog the Z axis.")
        )
        grbl_jog_grid.addWidget(self.jog_z_up_button, 2, 3)

        # JOG Z Down
        self.jog_z_down_button = QtWidgets.QToolButton()
        self.jog_z_down_button.setIcon(QtGui.QIcon(self.app.resource_location + '/down-arrow32.png'))
        self.jog_z_down_button.setText('Z')
        self.jog_z_down_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.jog_z_down_button.setToolTip(
            _("Jog the Z axis.")
        )
        grbl_jog_grid.addWidget(self.jog_z_down_button, 4, 3)


class FCZeroAxes(QtWidgets.QFrame):

    def __init__(self, app, *args, **kwargs):
        super(FCZeroAxes, self).__init__(*args, **kwargs)
        self.app = app

        self.setFrameShape(QtWidgets.QFrame.Box)
        self.setLineWidth(1)

        # Zero the axes
        grbl_zero_grid = QtWidgets.QGridLayout()
        grbl_zero_grid.setContentsMargins(2, 4, 2, 4)
        grbl_zero_grid.setColumnStretch(0, 0)
        grbl_zero_grid.setColumnStretch(1, 0)
        # grbl_zero_grid.setRowStretch(4, 1)
        self.setLayout(grbl_zero_grid)

        # Zero X axis
        self.grbl_zerox_button = QtWidgets.QToolButton()
        self.grbl_zerox_button.setText(_("X"))
        self.grbl_zerox_button.setToolTip(
            _("Zero the CNC X axes at current position.")
        )
        grbl_zero_grid.addWidget(self.grbl_zerox_button, 1, 0)
        # Zero Y axis
        self.grbl_zeroy_button = QtWidgets.QToolButton()
        self.grbl_zeroy_button.setText(_("Y"))

        self.grbl_zeroy_button.setToolTip(
            _("Zero the CNC Y axes at current position.")
        )
        grbl_zero_grid.addWidget(self.grbl_zeroy_button, 2, 0)
        # Zero Z axis
        self.grbl_zeroz_button = QtWidgets.QToolButton()
        self.grbl_zeroz_button.setText(_("Z"))

        self.grbl_zeroz_button.setToolTip(
            _("Zero the CNC Z axes at current position.")
        )
        grbl_zero_grid.addWidget(self.grbl_zeroz_button, 3, 0)
        self.grbl_homing_button = QtWidgets.QToolButton()
        self.grbl_homing_button.setText(_("Do Home"))
        self.grbl_homing_button.setToolTip(
            _("Perform a homing cycle on all axis."))
        grbl_zero_grid.addWidget(self.grbl_homing_button, 4, 0, 1, 2)
        # Zeroo all axes
        self.grbl_zero_all_button = QtWidgets.QToolButton()
        self.grbl_zero_all_button.setText(_("All"))
        self.grbl_zero_all_button.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)

        self.grbl_zero_all_button.setToolTip(
            _("Zero all CNC axes at current position.")
        )
        grbl_zero_grid.addWidget(self.grbl_zero_all_button, 1, 1, 3, 1)


class RotatedToolButton(QtWidgets.QToolButton):
    def __init__(self, orientation="east", *args, **kwargs):
        super(RotatedToolButton, self).__init__(*args, **kwargs)
        self.orientation = orientation

    def paintEvent(self, event):
        painter = QtWidgets.QStylePainter(self)
        if self.orientation == "east":
            painter.rotate(270)
            painter.translate(-1 * self.height(), 0)
        if self.orientation == "west":
            painter.rotate(90)
            painter.translate(0, -1 * self.width())
        painter.drawControl(QtWidgets.QStyle.CE_PushButton, self.getSyleOptions())

    def minimumSizeHint(self):
        size = super(RotatedToolButton, self).minimumSizeHint()
        size.transpose()
        return size

    def sizeHint(self):
        size = super(RotatedToolButton, self).sizeHint()
        size.transpose()
        return size

    def getSyleOptions(self):
        options = QtWidgets.QStyleOptionButton()
        options.initFrom(self)
        size = options.rect.size()
        size.transpose()
        options.rect.setSize(size)
        options.features = QtWidgets.QStyleOptionButton.None_
        # if self.isFlat():
        #     options.features |= QtWidgets.QStyleOptionButton.Flat
        if self.menu():
            options.features |= QtWidgets.QStyleOptionButton.HasMenu
        # if self.autoDefault() or self.isDefault():
        #     options.features |= QtWidgets.QStyleOptionButton.AutoDefaultButton
        # if self.isDefault():
        #     options.features |= QtWidgets.QStyleOptionButton.DefaultButton
        if self.isDown() or (self.menu() and self.menu().isVisible()):
            options.state |= QtWidgets.QStyle.State_Sunken
        if self.isChecked():
            options.state |= QtWidgets.QStyle.State_On
        # if not self.isFlat() and not self.isDown():
        #     options.state |= QtWidgets.QStyle.State_Raised

        options.text = self.text()
        options.icon = self.icon()
        options.iconSize = self.iconSize()
        return options


class RotatedButton(QtWidgets.QPushButton):
    def __init__(self, orientation="west", *args, **kwargs):
        super(RotatedButton, self).__init__(*args, **kwargs)
        self.orientation = orientation

    def paintEvent(self, event):
        painter = QtWidgets.QStylePainter(self)
        if self.orientation == "east":
            painter.rotate(270)
            painter.translate(-1 * self.height(), 0)
        if self.orientation == "west":
            painter.rotate(90)
            painter.translate(0, -1 * self.width())
        painter.drawControl(QtWidgets.QStyle.CE_PushButton, self.getSyleOptions())

    def minimumSizeHint(self):
        size = super(RotatedButton, self).minimumSizeHint()
        size.transpose()
        return size

    def sizeHint(self):
        size = super(RotatedButton, self).sizeHint()
        size.transpose()
        return size

    def getSyleOptions(self):
        options = QtWidgets.QStyleOptionButton()
        options.initFrom(self)
        size = options.rect.size()
        size.transpose()
        options.rect.setSize(size)
        options.features = QtWidgets.QStyleOptionButton.None_
        if self.isFlat():
            options.features |= QtWidgets.QStyleOptionButton.Flat
        if self.menu():
            options.features |= QtWidgets.QStyleOptionButton.HasMenu
        if self.autoDefault() or self.isDefault():
            options.features |= QtWidgets.QStyleOptionButton.AutoDefaultButton
        if self.isDefault():
            options.features |= QtWidgets.QStyleOptionButton.DefaultButton
        if self.isDown() or (self.menu() and self.menu().isVisible()):
            options.state |= QtWidgets.QStyle.State_Sunken
        if self.isChecked():
            options.state |= QtWidgets.QStyle.State_On
        if not self.isFlat() and not self.isDown():
            options.state |= QtWidgets.QStyle.State_Raised

        options.text = self.text()
        options.icon = self.icon()
        options.iconSize = self.iconSize()
        return options


class FlatCAMActivityView(QtWidgets.QWidget):
    """
    This class create and control the activity icon displayed in the App status bar
    """

    def __init__(self, app, parent=None):
        super().__init__(parent=parent)

        self.app = app

        if self.app.defaults["global_activity_icon"] == "Ball green":
            icon = self.app.resource_location + '/active_2_static.png'
            movie = self.app.resource_location + "/active_2.gif"
        elif self.app.defaults["global_activity_icon"] == "Ball black":
            icon = self.app.resource_location + '/active_static.png'
            movie = self.app.resource_location + "/active.gif"
        elif self.app.defaults["global_activity_icon"] == "Arrow green":
            icon = self.app.resource_location + '/active_3_static.png'
            movie = self.app.resource_location + "/active_3.gif"
        elif self.app.defaults["global_activity_icon"] == "Eclipse green":
            icon = self.app.resource_location + '/active_4_static.png'
            movie = self.app.resource_location + "/active_4.gif"
        else:
            icon = self.app.resource_location + '/active_static.png'
            movie = self.app.resource_location + "/active.gif"

        self.setMinimumWidth(200)
        self.movie_path = movie
        self.icon_path = icon

        self.icon = FCLabel(self)
        self.icon.setGeometry(0, 0, 16, 12)
        self.movie = QtGui.QMovie(self.movie_path)

        self.icon.setMovie(self.movie)
        # self.movie.start()

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setAlignment(QtCore.Qt.AlignLeft)
        self.setLayout(layout)

        layout.addWidget(self.icon)
        self.text = QtWidgets.QLabel(self)
        self.text.setText(_("Idle."))
        self.icon.setPixmap(QtGui.QPixmap(self.icon_path))

        layout.addWidget(self.text)

        self.icon.clicked.connect(self.app.on_toolbar_replot)

    def set_idle(self):
        self.movie.stop()
        self.text.setText(_("Idle."))

    def set_busy(self, msg, no_movie=None):
        if no_movie is not True:
            self.icon.setMovie(self.movie)
            self.movie.start()
        self.text.setText(msg)


class FlatCAMInfoBar(QtWidgets.QWidget):
    """
    This class create a place to display the App messages in the Status Bar
    """

    def __init__(self, parent=None, app=None):
        super(FlatCAMInfoBar, self).__init__(parent=parent)

        self.app = app

        self.icon = QtWidgets.QLabel(self)
        self.icon.setGeometry(0, 0, 12, 12)
        self.pmap = QtGui.QPixmap(self.app.resource_location + '/graylight12.png')
        self.icon.setPixmap(self.pmap)

        self.lock_pmaps = False

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(5, 0, 5, 0)
        self.setLayout(layout)

        layout.addWidget(self.icon)

        self.text = QtWidgets.QLabel(self)
        self.text.setText(_("Application started ..."))
        self.text.setToolTip(_("Hello!"))

        layout.addWidget(self.text)
        layout.addStretch()

    def set_text_(self, text, color=None):
        self.text.setText(text)
        self.text.setToolTip(text)
        if color:
            self.text.setStyleSheet('color: %s' % str(color))

    def set_status(self, text, level="info"):
        level = str(level)

        if self.lock_pmaps is not True:
            self.pmap.fill()
            if level == "ERROR" or level == "ERROR_NOTCL":
                self.pmap = QtGui.QPixmap(self.app.resource_location + '/redlight12.png')
            elif level.lower() == "success":
                self.pmap = QtGui.QPixmap(self.app.resource_location + '/greenlight12.png')
            elif level == "WARNING" or level == "WARNING_NOTCL":
                self.pmap = QtGui.QPixmap(self.app.resource_location + '/yellowlight12.png')
            elif level.lower() == "selected":
                self.pmap = QtGui.QPixmap(self.app.resource_location + '/bluelight12.png')
            else:
                self.pmap = QtGui.QPixmap(self.app.resource_location + '/graylight12.png')

        try:
            self.set_text_(text)
            self.icon.setPixmap(self.pmap)
        except Exception as e:
            log.debug("FlatCAMInfoBar.set_status() --> %s" % str(e))


class FlatCAMSystemTray(QtWidgets.QSystemTrayIcon):
    """
    This class create the Sys Tray icon for the app
    """

    def __init__(self, app, icon, headless=None, parent=None):
        # QtWidgets.QSystemTrayIcon.__init__(self, icon, parent)
        super().__init__(icon, parent=parent)
        self.app = app

        menu = QtWidgets.QMenu(parent)

        menu_runscript = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/script14.png'),
                                           '%s' % _('Run Script ...'), self)
        menu_runscript.setToolTip(
            _("Will run the opened Tcl Script thus\n"
              "enabling the automation of certain\n"
              "functions of FlatCAM.")
        )
        menu.addAction(menu_runscript)

        menu.addSeparator()

        if headless is None:
            self.menu_open = menu.addMenu(QtGui.QIcon(self.app.resource_location + '/folder32_bis.png'), _('Open'))

            # Open Project ...
            menu_openproject = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/folder16.png'),
                                                 '%s ...' % _('Open Project'), self)
            self.menu_open.addAction(menu_openproject)
            self.menu_open.addSeparator()

            # Open Gerber ...
            menu_opengerber = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/flatcam_icon24.png'),
                                                '%s ...\t%s' % (_('Open Gerber'), _('Ctrl+G')), self)
            self.menu_open.addAction(menu_opengerber)

            # Open Excellon ...
            menu_openexcellon = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/open_excellon32.png'),
                                                  '%s ...\t%s' % (_('Open Excellon'), _('Ctrl+E')), self)
            self.menu_open.addAction(menu_openexcellon)

            # Open G-Code ...
            menu_opengcode = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/code.png'),
                                               '%s ...' % _('Open G-Code'), self)
            self.menu_open.addAction(menu_opengcode)

            self.menu_open.addSeparator()

            menu_openproject.triggered.connect(self.app.f_handlers.on_file_openproject)
            menu_opengerber.triggered.connect(self.app.f_handlers.on_fileopengerber)
            menu_openexcellon.triggered.connect(self.app.f_handlers.on_fileopenexcellon)
            menu_opengcode.triggered.connect(self.app.f_handlers.on_fileopengcode)

        exitAction = menu.addAction(_("Exit"))
        exitAction.setIcon(QtGui.QIcon(self.app.resource_location + '/power16.png'))
        self.setContextMenu(menu)

        menu_runscript.triggered.connect(lambda: self.app.on_filerunscript(
            silent=True if self.app.cmd_line_headless == 1 else False))

        exitAction.triggered.connect(self.app.final_save)


def message_dialog(title, message, kind="info", parent=None):
    """
    Builds and show a custom QMessageBox to be used in FlatCAM.

    :param title:       title of the QMessageBox
    :param message:     message to be displayed
    :param kind:        type of QMessageBox; will display a specific icon.
    :param parent:      parent
    :return:            None
    """
    icon = {"info": QtWidgets.QMessageBox.Information,
            "warning": QtWidgets.QMessageBox.Warning,
            "error": QtWidgets.QMessageBox.Critical}[str(kind)]
    dlg = QtWidgets.QMessageBox(icon, title, message, parent=parent)
    dlg.setText(message)
    dlg.exec_()


def rreplace(s, old, new, occurrence):
    """
    Credits go here:
    https://stackoverflow.com/questions/2556108/rreplace-how-to-replace-the-last-occurrence-of-an-expression-in-a-string

    :param s: string to be processed
    :param old: old char to be replaced
    :param new: new char to replace the old one
    :param occurrence: how many places from end to replace the old char
    :return: modified string
    """

    li = s.rsplit(old, occurrence)
    return new.join(li)
