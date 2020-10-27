# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
# ##########################################################


from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCursor, QPixmap
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout, QLabel
from appGUI.GUIElements import _BrowserTextEdit, _ExpandableTextEdit, FCLabel
import html
import sys
import traceback

import tkinter as tk
import tclCommands

import gettext
import appTranslation as fcTranslate
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

    def __init__(self, version, app, *args):
        QWidget.__init__(self, *args)

        self.app = app

        self._browser = _BrowserTextEdit(version=version, app=app)
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

        self._delete_line = FCLabel()
        self._delete_line.setPixmap(QPixmap(self.app.resource_location + '/clear_line16.png'))
        self._delete_line.setMargin(3)
        self._delete_line.setToolTip(_("Clear the text."))

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._browser)

        hlay = QHBoxLayout()
        hlay.addWidget(self._delete_line)
        hlay.addWidget(QLabel(" "))
        hlay.addWidget(self._edit)
        layout.addLayout(hlay)

        self._history = ['']  # current empty line
        self._historyIndex = 0

        self._delete_line.clicked.connect(self.on_delete_line_clicked)

    def command_line(self):
        return self._edit

    def on_delete_line_clicked(self):
        self._edit.clear()

    def open_processing(self, detail=None):
        """
        Open processing and disable using shell commands again until all commands are finished

        :param detail: text detail about what is currently called from TCL to python
        :return: None
        """

        self._edit.setTextColor(Qt.white)
        self._edit.setTextBackgroundColor(Qt.darkGreen)
        if detail is None:
            self._edit.setPlainText(_("...processing..."))
        else:
            self._edit.setPlainText('%s [%s]' % (_("...processing..."),  detail))

        self._edit.setDisabled(True)
        self._edit.setFocus()

    def close_processing(self):
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
        assert style in ('in', 'out', 'err', 'warning', 'success', 'selected', 'raw')

        if style != 'raw':
            text = html.escape(text)
            text = text.replace('\n', '<br/>')
        else:
            text = text.replace('\n', '<br>')
            text = text.replace('\t', '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;')

        idx = text.find(']')
        mtype = text[:idx+1].upper()
        mtype = mtype.replace('_NOTCL', '')
        body = text[idx+1:]
        if style.lower() == 'in':
            text = '<span style="font-weight: bold;">%s</span>' % text
        elif style.lower() == 'err':
            text = '<span style="font-weight: bold; color: red;">%s</span>'\
                   '<span style="font-weight: bold;">%s</span>'\
                   % (mtype, body)
        elif style.lower() == 'warning':
            # text = '<span style="font-weight: bold; color: #f4b642;">%s</span>' % text
            text = '<span style="font-weight: bold; color: #f4b642;">%s</span>' \
                   '<span style="font-weight: bold;">%s</span>' \
                   % (mtype, body)
        elif style.lower() == 'success':
            # text = '<span style="font-weight: bold; color: #15b300;">%s</span>' % text
            text = '<span style="font-weight: bold; color: #15b300;">%s</span>' \
                   '<span style="font-weight: bold;">%s</span>' \
                   % (mtype, body)
        elif style.lower() == 'selected':
            text = ''
        elif style.lower() == 'raw':
            text = text
        else:
            # without span <br/> is ignored!!!
            text = '<span>%s</span>' % text

        scrollbar = self._browser.verticalScrollBar()
        old_value = scrollbar.value()
        # scrollattheend = old_value == scrollbar.maximum()

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

    def append_raw(self, text):
        """
        Append text to output widget as it is
        """
        self._append_to_browser('raw', text)

    def append_success(self, text):
        """Append text to output widget
        """
        self._append_to_browser('success', text)

    def append_selected(self, text):
        """Append text to output widget
        """
        self._append_to_browser('selected', text)

    def append_warning(self, text):
        """Append text to output widget
        """
        self._append_to_browser('warning', text)

    def append_error(self, text):
        """Append error text to output widget. Text is drawn with red background
        """
        self._append_to_browser('err', text)

    def is_command_complete(self, text):
        """
        Executed by _ExpandableTextEdit. Re-implement this function in the child classes.
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
    def __init__(self, app, version, *args):
        """
        Initialize the TCL Shell. A dock widget that holds the GUI interface to the FlatCAM command line.

        :param app:    When instantiated the sysShell will be actually the FlatCAMApp.App() class
        :param version:     FlatCAM version string
        :param args:        Parameters passed to the TermWidget parent class
        """
        TermWidget.__init__(self, version, *args, app=app)
        self.app = app

        self.tcl_commands_storage = {}
        self.tcl = None

        self.init_tcl()

        self._edit.set_model_data(self.app.myKeywords)
        self.setWindowIcon(self.app.ui.app_icon)
        self.setWindowTitle(_("FlatCAM Shell"))
        self.resize(*self.app.defaults["global_shell_shape"])
        self._append_to_browser('in', "FlatCAM %s - " % version)
        self.append_output('%s\n\n' % _("Type >help< to get started"))

        self.app.ui.shell_dock.setWidget(self)
        self.app.log.debug("TCL Shell has been initialized.")

    def init_tcl(self):
        if hasattr(self, 'tcl') and self.tcl is not None:
            # self.tcl = None
            # new object cannot be used here as it will not remember values created for next passes,
            # because tcl was executed in old instance of TCL
            pass
        else:
            self.tcl = tk.Tcl()
            self.setup_shell()

    def setup_shell(self):
        """
        Creates shell functions. Runs once at startup.

        :return: None
        """

        '''
            How to implement TCL shell commands:

            All parameters passed to command should be possible to set as None and test it afterwards.
            This is because we need to see error caused in tcl,
            if None value as default parameter is not allowed TCL will return empty error.
            Use:
                def mycommand(name=None,...):

            Test it like this:
            if name is None:

                self.raise_tcl_error('Argument name is missing.')

            When error occurred, always use raise_tcl_error, never return "some text" on error,
            otherwise we will miss it and processing will silently continue.
            Method raise_tcl_error  pass error into TCL interpreter, then raise python exception,
            which is caught in exec_command and displayed in TCL shell console with red background.
            Error in console is displayed  with TCL  trace.

            This behavior works only within main thread,
            errors with promissed tasks can be catched and detected only with log.
            TODO: this problem have to be addressed somehow, maybe rewrite promissing to be blocking somehow for
            TCL shell.

            Kamil's comment: I will rewrite existing TCL commands from time to time to follow this rules.

        '''

        # Import/overwrite tcl commands as objects of TclCommand descendants
        # This modifies the variable 'self.tcl_commands_storage'.
        tclCommands.register_all_commands(self.app, self.tcl_commands_storage)

        # Add commands to the tcl interpreter
        for cmd in self.tcl_commands_storage:
            self.tcl.createcommand(cmd, self.tcl_commands_storage[cmd]['fcn'])

        # Make the tcl puts function return instead of print to stdout
        self.tcl.eval('''
            rename puts original_puts
            proc puts {args} {
                if {[llength $args] == 1} {
                    return "[lindex $args 0]"
                } else {
                    eval original_puts $args
                }
            }
            ''')

    def is_command_complete(self, text):

        # def skipQuotes(txt):
        #     quote = txt[0]
        #     text_val = txt[1:]
        #     endIndex = str(text_val).index(quote)
        #     return text[endIndex:]

        # I'm disabling this because I need to be able to load paths that have spaces by
        # enclosing them in quotes --- Marius Stanciu
        # while text:
        #     if text[0] in ('"', "'"):
        #         try:
        #             text = skipQuotes(text)
        #         except ValueError:
        #             return False
        #     text = text[1:]

        return True

    def child_exec_command(self, text):
        self.exec_command(text)

    def exec_command(self, text, no_echo=False):
        """
        Handles input from the shell. See FlatCAMApp.setup_shell for shell commands.
        Also handles execution in separated threads

        :param text:        FlatCAM TclCommand with parameters
        :param no_echo:     If True it will not try to print to the Shell because most likely the shell is hidden and it
                            will create crashes of the _Expandable_Edit widget
        :return:            output if there was any
        """

        self.app.defaults.report_usage('exec_command')

        return self.exec_command_test(text, False, no_echo=no_echo)

    def exec_command_test(self, text, reraise=True, no_echo=False):
        """
        Same as exec_command(...) with additional control over  exceptions.
        Handles input from the shell. See FlatCAMApp.setup_shell for shell commands.

        :param text: Input command
        :param reraise: Re-raise TclError exceptions in Python (mostly for unittests).
        :param no_echo: If True it will not try to print to the Shell because most likely the shell is hidden and it
        will create crashes of the _Expandable_Edit widget
        :return: Output from the command
        """

        tcl_command_string = str(text)

        try:
            if no_echo is False:
                self.open_processing()  # Disables input box.

            result = self.tcl.eval(str(tcl_command_string))
            if result != 'None' and no_echo is False:
                self.append_output(result + '\n')

        except tk.TclError as e:
            # This will display more precise answer if something in TCL shell fails
            result = self.tcl.eval("set errorInfo")
            self.app.log.error("Exception on Tcl Command execution: %s" % (result + '\n'))
            if no_echo is False:
                self.append_error('ERROR Report: ' + result + '\n')
            # Show error in console and just return or in test raise exception
            if reraise:
                raise e
        finally:
            if no_echo is False:
                self.close_processing()
            pass
        return result

    def raise_tcl_unknown_error(self, unknownException):
        """
        Raise exception if is different type than TclErrorException
        this is here mainly to show unknown errors inside TCL shell console.

        :param unknownException:
        :return:
        """

        if not isinstance(unknownException, self.TclErrorException):
            self.raise_tcl_error("Unknown error: %s" % str(unknownException))
        else:
            raise unknownException

    def display_tcl_error(self, error, error_info=None):
        """
        Escape bracket [ with '\' otherwise there is error
        "ERROR: missing close-bracket" instead of real error

        :param error: it may be text  or exception
        :param error_info: Some informations about the error
        :return: None
        """

        if isinstance(error, Exception):
            exc_type, exc_value, exc_traceback = error_info
            if not isinstance(error, self.TclErrorException):
                show_trace = 1
            else:
                show_trace = int(self.app.defaults['global_verbose_error_level'])

            if show_trace > 0:
                trc = traceback.format_list(traceback.extract_tb(exc_traceback))
                trc_formated = []
                for a in reversed(trc):
                    trc_formated.append(a.replace("    ", " > ").replace("\n", ""))
                text = "%s\nPython traceback: %s\n%s" % (exc_value, exc_type, "\n".join(trc_formated))
            else:
                text = "%s" % error
        else:
            text = error

        text = text.replace('[', '\\[').replace('"', '\\"')
        self.tcl.eval('return -code error "%s"' % text)

    def raise_tcl_error(self, text):
        """
        This method  pass exception from python into TCL as error, so we get stacktrace and reason

        :param text: text of error
        :return: raise exception
        """

        self.display_tcl_error(text)
        raise self.TclErrorException(text)

    class TclErrorException(Exception):
        """
        this exception is defined here, to be able catch it if we successfully handle all errors from shell command
        """
        pass

    # """
    # Code below is unsused. Saved for later.
    # """

    # parts = re.findall(r'([\w\\:\.]+|".*?")+', text)
    # parts = [p.replace('\n', '').replace('"', '') for p in parts]
    # self.log.debug(parts)
    # try:
    #     if parts[0] not in commands:
    #         self.shell.append_error("Unknown command\n")
    #         return
    #
    #     #import inspect
    #     #inspect.getargspec(someMethod)
    #     if (type(commands[parts[0]]["params"]) is not list and len(parts)-1 != commands[parts[0]]["params"]) or \
    #             (type(commands[parts[0]]["params"]) is list and len(parts)-1 not in commands[parts[0]]["params"]):
    #         self.shell.append_error(
    #             "Command %s takes %d arguments. %d given.\n" %
    #             (parts[0], commands[parts[0]]["params"], len(parts)-1)
    #         )
    #         return
    #
    #     cmdfcn = commands[parts[0]]["fcn"]
    #     cmdconv = commands[parts[0]]["converters"]
    #     if len(parts) - 1 > 0:
    #         retval = cmdfcn(*[cmdconv[i](parts[i + 1]) for i in range(len(parts)-1)])
    #     else:
    #         retval = cmdfcn()
    #     retfcn = commands[parts[0]]["retfcn"]
    #     if retval and retfcn(retval):
    #         self.shell.append_output(retfcn(retval) + "\n")
    #
    # except Exception as e:
    #     #self.shell.append_error(''.join(traceback.format_exc()))
    #     #self.shell.append_error("?\n")
    #     self.shell.append_error(str(e) + "\n")
