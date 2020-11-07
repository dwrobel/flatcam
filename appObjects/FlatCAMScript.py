# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
# ##########################################################

# ##########################################################
# File modified by: Marius Stanciu                         #
# ##########################################################

from appEditors.AppTextEditor import AppTextEditor
from appObjects.FlatCAMObj import *
from appGUI.ObjectUI import *

import tkinter as tk
import sys

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ScriptObject(FlatCAMObj):
    """
    Represents a TCL script object.
    """
    optionChanged = QtCore.pyqtSignal(str)
    ui_type = ScriptObjectUI

    def __init__(self, name):
        self.decimals = self.app.decimals

        log.debug("Creating a ScriptObject object...")
        FlatCAMObj.__init__(self, name)

        self.kind = "script"

        self.options.update({
            "plot": True,
            "type": 'Script',
            "source_file": '',
        })

        self.units = ''

        self.script_editor_tab = None

        self.ser_attrs = ['options', 'kind', 'source_file']
        self.source_file = ''
        self.script_code = ''

        self.units_found = self.app.defaults['units']

    def set_ui(self, ui):
        """
        Sets the Object UI in Selected Tab for the FlatCAM Script type of object.
        :param ui:
        :return:
        """
        FlatCAMObj.set_ui(self, ui)
        log.debug("ScriptObject.set_ui()")

        assert isinstance(self.ui, ScriptObjectUI), \
            "Expected a ScriptObjectUI, got %s" % type(self.ui)

        self.units = self.app.defaults['units'].upper()
        self.units_found = self.app.defaults['units']

        # Fill form fields only on object create
        self.to_form()

        # Show/Hide Advanced Options
        if self.app.defaults["global_app_level"] == 'b':
            self.ui.level.setText('<span style="color:green;"><b>%s</b></span>' % _("Basic"))
        else:
            self.ui.level.setText('<span style="color:red;"><b>%s</b></span>' % _("Advanced"))

        self.script_editor_tab = AppTextEditor(app=self.app, plain_text=True, parent=self.app.ui)

        # tab_here = False
        # # try to not add too many times a tab that it is already installed
        # for idx in range(self.app.ui.plot_tab_area.count()):
        #     if self.app.ui.plot_tab_area.widget(idx).objectName() == self.options['name']:
        #         tab_here = True
        #         break
        #
        # # add the tab if it is not already added
        # if tab_here is False:
        #     self.app.ui.plot_tab_area.addTab(self.script_editor_tab, '%s' % _("Script Editor"))
        #     self.script_editor_tab.setObjectName(self.options['name'])

        # self.app.ui.plot_tab_area.addTab(self.script_editor_tab, '%s' % _("Script Editor"))
        # self.script_editor_tab.setObjectName(self.options['name'])

        # first clear previous text in text editor (if any)
        # self.script_editor_tab.code_editor.clear()
        # self.script_editor_tab.code_editor.setReadOnly(False)

        self.ui.autocomplete_cb.set_value(self.app.defaults['script_autocompleter'])
        self.on_autocomplete_changed(state=self.app.defaults['script_autocompleter'])

        self.script_editor_tab.buttonRun.show()

        # Switch plot_area to Script Editor tab
        self.app.ui.plot_tab_area.setCurrentWidget(self.script_editor_tab)

        flt = "FlatCAM Scripts (*.FlatScript);;All Files (*.*)"
        self.script_editor_tab.buttonOpen.clicked.disconnect()
        self.script_editor_tab.buttonOpen.clicked.connect(lambda: self.script_editor_tab.handleOpen(filt=flt))
        self.script_editor_tab.buttonSave.clicked.disconnect()
        self.script_editor_tab.buttonSave.clicked.connect(lambda: self.script_editor_tab.handleSaveGCode(filt=flt))

        self.script_editor_tab.buttonRun.clicked.connect(self.handle_run_code)
        self.script_editor_tab.handleTextChanged()

        self.ui.autocomplete_cb.stateChanged.connect(self.on_autocomplete_changed)

        self.ser_attrs = ['options', 'kind', 'source_file']

        # ---------------------------------------------------- #
        # ----------- LOAD THE TEXT SOURCE FILE -------------- #
        # ---------------------------------------------------- #
        self.app.proc_container.view.set_busy('%s...' % _("Loading"))
        self.script_editor_tab.t_frame.hide()

        try:
            # self.script_editor_tab.code_editor.setPlainText(self.source_file)
            self.script_editor_tab.load_text(self.source_file, move_to_end=True)
        except Exception as e:
            log.debug("ScriptObject.set_ui() --> %s" % str(e))

        self.script_editor_tab.t_frame.show()

        self.app.proc_container.view.set_idle()
        self.build_ui()

    def build_ui(self):
        FlatCAMObj.build_ui(self)

        tab_here = False
        # try to not add too many times a tab that it is already installed
        for idx in range(self.app.ui.plot_tab_area.count()):
            if self.app.ui.plot_tab_area.widget(idx).objectName() == self.options['name']:
                tab_here = True
                break

        # add the tab if it is not already added
        if tab_here is False:
            self.app.ui.plot_tab_area.addTab(self.script_editor_tab, '%s' % _("Script Editor"))
            self.script_editor_tab.setObjectName(self.options['name'])
            self.app.ui.plot_tab_area.setCurrentWidget(self.script_editor_tab)

    def parse_file(self, filename):
        """
        Will set an attribute of the object, self.source_file, with the parsed data.

        :param filename:    Tcl Script file to parse
        :return:            None
        """
        with open(filename, "r") as opened_script:
            script_content = opened_script.readlines()
            script_content = ''.join(script_content)

        self.source_file = script_content

    def handle_run_code(self):
        # trying to run a Tcl command without having the Shell open will create some warnings because the Tcl Shell
        # tries to print on a hidden widget, therefore show the dock if hidden
        if self.app.ui.shell_dock.isHidden():
            self.app.ui.shell_dock.show()

        self.app.shell.open_processing()  # Disables input box.

        # make sure that the pixmaps are not updated when running this as they will crash
        # TODO find why the pixmaps load crash when run from this object (perhaps another thread?)
        self.app.ui.fcinfo.lock_pmaps = True

        self.script_code = self.script_editor_tab.code_editor.toPlainText()

        old_line = ''
        for tcl_command_line in self.script_code.splitlines():
            # do not process lines starting with '#' = comment and empty lines
            if not tcl_command_line.startswith('#') and tcl_command_line != '':
                # id FlatCAM is run in Windows then replace all the slashes with
                # the UNIX style slash that TCL understands
                if sys.platform == 'win32':
                    if "open" in tcl_command_line:
                        tcl_command_line = tcl_command_line.replace('\\', '/')

                if old_line != '':
                    new_command = old_line + tcl_command_line + '\n'
                else:
                    new_command = tcl_command_line

                # execute the actual Tcl command
                try:
                    result = self.app.shell.tcl.eval(str(new_command))
                    if result != 'None':
                        self.app.shell.append_output(result + '\n')

                    old_line = ''
                except tk.TclError:
                    old_line = old_line + tcl_command_line + '\n'
                except Exception as e:
                    log.debug("ScriptObject.handleRunCode() --> %s" % str(e))

        if old_line != '':
            # it means that the script finished with an error
            result = self.app.shell.tcl.eval("set errorInfo")
            log.error("Exec command Exception: %s\n" % result)
            self.app.shell.append_error('ERROR: %s\n' % result)

        self.app.ui.fcinfo.lock_pmaps = False
        self.app.shell.close_processing()

    def on_autocomplete_changed(self, state):
        if state:
            self.script_editor_tab.code_editor.completer_enable = True
        else:
            self.script_editor_tab.code_editor.completer_enable = False

    def mirror(self, axis, point):
        pass

    def offset(self, vect):
        pass

    def rotate(self, angle, point):
        pass

    def scale(self, xfactor, yfactor=None, point=None):
        pass

    def skew(self, angle_x, angle_y, point):
        pass

    def buffer(self, distance, join, factor=None):
        pass

    def bounds(self, flatten=False):
        return None, None, None, None

    def to_dict(self):
        """
        Returns a representation of the object as a dictionary.
        Attributes to include are listed in ``self.ser_attrs``.

        :return: A dictionary-encoded copy of the object.
        :rtype: dict
        """
        d = {}
        for attr in self.ser_attrs:
            d[attr] = getattr(self, attr)
        return d

    def from_dict(self, d):
        """
        Sets object's attributes from a dictionary.
        Attributes to include are listed in ``self.ser_attrs``.
        This method will look only for only and all the
        attributes in ``self.ser_attrs``. They must all
        be present. Use only for deserializing saved
        objects.

        :param d: Dictionary of attributes to set in the object.
        :type d: dict
        :return: None
        """
        for attr in self.ser_attrs:
            setattr(self, attr, d[attr])
