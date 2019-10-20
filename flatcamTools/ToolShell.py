# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
# ##########################################################


from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QVBoxLayout, QWidget
from flatcamGUI.GUIElements import _BrowserTextEdit, _ExpandableTextEdit
import html
import sys

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class TermWidget(QWidget):
    """
    Widget which represents terminal. It only displays text and allows to enter text.
    All high level logic should be implemented by client classes

    User pressed Enter. Client class should decide, if command must be executed or user may continue edit it
    """

    def __init__(self, version, *args):
        QWidget.__init__(self, *args)

        self._browser = _BrowserTextEdit(version=version)
        self._browser.setStyleSheet("font: 9pt \"Courier\";")
        self._browser.setReadOnly(True)
        self._browser.document().setDefaultStyleSheet(
            self._browser.document().defaultStyleSheet() +
            "span {white-space:pre;}")

        self._edit = _ExpandableTextEdit(self, self)
        self._edit.historyNext.connect(self._on_history_next)
        self._edit.historyPrev.connect(self._on_history_prev)
        self._edit.setFocus()
        self.setFocusProxy(self._edit)

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._browser)
        layout.addWidget(self._edit)

        self._history = ['']  # current empty line
        self._historyIndex = 0

    def open_proccessing(self, detail=None):
        """
        Open processing and disable using shell commands again until all commands are finished

        :param detail: text detail about what is currently called from TCL to python
        :return: None
        """

        self._edit.setTextColor(Qt.white)
        self._edit.setTextBackgroundColor(Qt.darkGreen)
        if detail is None:
            self._edit.setPlainText(_("...proccessing..."))
        else:
            self._edit.setPlainText('%s [%s]' % (_("...proccessing..."),  detail))

        self._edit.setDisabled(True)
        self._edit.setFocus()

    def close_proccessing(self):
        """
        Close processing and enable using shell commands  again
        :return:
        """

        self._edit.setTextColor(Qt.black)
        self._edit.setTextBackgroundColor(Qt.white)
        self._edit.setPlainText('')
        self._edit.setDisabled(False)
        self._edit.setFocus()

    def _append_to_browser(self, style, text):
        """
        Convert text to HTML for inserting it to browser
        """
        assert style in ('in', 'out', 'err', 'warning', 'success', 'selected')

        text = html.escape(text)
        text = text.replace('\n', '<br/>')

        if style == 'in':
            text = '<span style="font-weight: bold;">%s</span>' % text
        elif style == 'err':
            text = '<span style="font-weight: bold; color: red;">%s</span>' % text
        elif style == 'warning':
            text = '<span style="font-weight: bold; color: #f4b642;">%s</span>' % text
        elif style == 'success':
            text = '<span style="font-weight: bold; color: #084400;">%s</span>' % text
        elif style == 'selected':
            text = ''
        else:
            text = '<span>%s</span>' % text  # without span <br/> is ignored!!!

        scrollbar = self._browser.verticalScrollBar()
        old_value = scrollbar.value()
        scrollattheend = old_value == scrollbar.maximum()

        self._browser.moveCursor(QTextCursor.End)
        self._browser.insertHtml(text)

        """TODO When user enters second line to the input, and input is resized, scrollbar changes its position
        and stops moving. As quick fix of this problem, now we always scroll down when add new text.
        To fix it correctly, scroll to the bottom, if before input has been resized,
        scrollbar was in the bottom, and remove next line
        """
        scrollattheend = True

        if scrollattheend:
            scrollbar.setValue(scrollbar.maximum())
        else:
            scrollbar.setValue(old_value)

    def exec_current_command(self):
        """
        Save current command in the history. Append it to the log. Clear edit line
        Re-implement in the child classes to actually execute command
        """
        text = str(self._edit.toPlainText())

        # in Windows replace all backslash symbols '\' with '\\' slash because Windows paths are made with backslash
        # and in Python single slash is the escape symbol
        if sys.platform == 'win32':
            text = text.replace('\\', '\\\\')

        self._append_to_browser('in', '> ' + text + '\n')

        if len(self._history) < 2 or self._history[-2] != text:  # don't insert duplicating items
            try:
                if text[-1] == '\n':
                    self._history.insert(-1, text[:-1])
                else:
                    self._history.insert(-1, text)
            except IndexError:
                return

        self._historyIndex = len(self._history) - 1

        self._history[-1] = ''
        self._edit.clear()

        if not text[-1] == '\n':
            text += '\n'

        self.child_exec_command(text)

    def child_exec_command(self, text):
        """
        Re-implement in the child classes
        """
        pass

    def add_line_break_to_input(self):
        self._edit.textCursor().insertText('\n')

    def append_output(self, text):
        """
        Append text to output widget
        """
        self._append_to_browser('out', text)

    def append_success(self, text):
        """Appent text to output widget
        """
        self._append_to_browser('success', text)

    def append_selected(self, text):
        """Appent text to output widget
        """
        self._append_to_browser('selected', text)

    def append_warning(self, text):
        """Appent text to output widget
        """
        self._append_to_browser('warning', text)

    def append_error(self, text):
        """Appent error text to output widget. Text is drawn with red background
        """
        self._append_to_browser('err', text)

    def is_command_complete(self, text):
        """
        Executed by _ExpandableTextEdit. Reimplement this function in the child classes.
        """
        return True

    def browser(self):
        return self._browser

    def _on_history_next(self):
        """
        Down pressed, show next item from the history
        """
        if (self._historyIndex + 1) < len(self._history):
            self._historyIndex += 1
            self._edit.setPlainText(self._history[self._historyIndex])
            self._edit.moveCursor(QTextCursor.End)

    def _on_history_prev(self):
        """
        Up pressed, show previous item from the history
        """
        if self._historyIndex > 0:
            if self._historyIndex == (len(self._history) - 1):
                self._history[-1] = self._edit.toPlainText()
            self._historyIndex -= 1
            self._edit.setPlainText(self._history[self._historyIndex])
            self._edit.moveCursor(QTextCursor.End)


class FCShell(TermWidget):
    def __init__(self, sysShell, version, *args):
        TermWidget.__init__(self, version, *args)
        self._sysShell = sysShell

    def is_command_complete(self, text):
        def skipQuotes(text):
            quote = text[0]
            text = text[1:]
            endIndex = str(text).index(quote)
            return text[endIndex:]
        while text:
            if text[0] in ('"', "'"):
                try:
                    text = skipQuotes(text)
                except ValueError:
                    return False
            text = text[1:]
        return True

    def child_exec_command(self, text):
        self._sysShell.exec_command(text)
