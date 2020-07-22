# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 07/22/2020                                         #
# MIT Licence                                              #
# ##########################################################

from appEditors.AppTextEditor import AppTextEditor
from appObjects import FlatCAMCNCJob
from appGUI.GUIElements import FCFileSaveDialog, FCEntry, FCTextAreaExtended, FCTextAreaLineNumber, FCButton
from PyQt5 import QtWidgets, QtCore, QtGui

# from io import StringIO

import logging

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class appGCodeEditor(QtCore.QObject):

    def __init__(self, app, parent=None):
        super().__init__(parent=parent)

        self.app = app
        self.plain_text = ''
        self.callback = lambda x: None

        self.ui = appGCodeEditorUI(app=self.app)

        # #################################################################################
        # ################### SIGNALS #####################################################
        # #################################################################################

        self.gcode_obj = None
        self.code_edited = ''

    def set_ui(self):
        pass

    def build_ui(self):
        pass

    def ui_connect(self):
        pass

    def ui_disconnect(self):
        pass

    def handleTextChanged(self):
        # enable = not self.ui.code_editor.document().isEmpty()
        # self.ui.buttonPrint.setEnabled(enable)
        # self.ui.buttonPreview.setEnabled(enable)

        self.buttonSave.setStyleSheet("QPushButton {color: red;}")
        self.buttonSave.setIcon(QtGui.QIcon(self.app.resource_location + '/save_as_red.png'))

    def edit_fcgcode(self, cnc_obj):
        assert isinstance(cnc_obj, FlatCAMCNCJob)
        self.gcode_obj = cnc_obj

        preamble = str(self.ui.prepend_text.get_value())
        postamble = str(self.ui.append_text.get_value())

        gcode_text = self.gcode_obj.source_file

        self.gcode_editor_tab.buttonSave.clicked.connect(self.on_update_source_file)

        self.app.inform.emit('[success] %s...' % _('Loaded Machine Code into Code Editor'))

        self.ui.gcode_editor_tab.load_text(self, gcode_text, move_to_start=True, clear_text=True)

    def update_gcode(self):
        my_gcode = self.ui.gcode_editor_tab.code_editor.toPlainText()
        self.gcode_obj.source_file = my_gcode

        self.ui.gcode_editor_tab.buttonSave.setStyleSheet("")
        self.ui.gcode_editor_tab.setIcon(QtGui.QIcon(self.app.resource_location + '/save_as.png'))

    def handleOpen(self, filt=None):
        self.app.defaults.report_usage("handleOpen()")

        if filt:
            _filter_ = filt
        else:
            _filter_ = "G-Code Files (*.nc);; G-Code Files (*.txt);; G-Code Files (*.tap);; G-Code Files (*.cnc);; " \
                       "All Files (*.*)"

        path, _f = QtWidgets.QFileDialog.getOpenFileName(
            caption=_('Open file'), directory=self.app.get_last_folder(), filter=_filter_)

        if path:
            file = QtCore.QFile(path)
            if file.open(QtCore.QIODevice.ReadOnly):
                stream = QtCore.QTextStream(file)
                self.code_edited = stream.readAll()
                self.ui.gcode_editor_tab.load_text(self, self.code_edited, move_to_start=True, clear_text=True)
                file.close()


class appGCodeEditorUI:
    def __init__(self, app):
        self.app = app

        # Number of decimals used by tools in this class
        self.decimals = self.app.decimals

        # ## Current application units in Upper Case
        self.units = self.app.defaults['units'].upper()

        # self.setSizePolicy(
        #     QtWidgets.QSizePolicy.MinimumExpanding,
        #     QtWidgets.QSizePolicy.MinimumExpanding
        # )

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.editor_frame = QtWidgets.QFrame()
        self.editor_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.editor_frame)

        self.editor_layout = QtWidgets.QGridLayout(self.editor_frame)
        self.editor_layout.setContentsMargins(2, 2, 2, 2)
        self.editor_frame.setLayout(self.editor_layout)

        # #############################################################################################################
        # ############# ADD a new TAB in the PLot Tab Area
        # #############################################################################################################
        self.gcode_editor_tab = AppTextEditor(app=self.app, plain_text=True)

        # add the tab if it was closed
        self.app.ui.plot_tab_area.addTab(self.gcode_editor_tab, '%s' % _("Code Editor"))
        self.gcode_editor_tab.setObjectName('code_editor_tab')

        # delete the absolute and relative position and messages in the infobar
        self.app.ui.position_label.setText("")
        self.app.ui.rel_position_label.setText("")

        self.gcode_editor_tab.code_editor.completer_enable = False
        self.gcode_editor_tab.buttonRun.hide()

        # Switch plot_area to CNCJob tab
        self.app.ui.plot_tab_area.setCurrentWidget(self.gcode_editor_tab)

        self.gcode_editor_tab.t_frame.hide()
        # then append the text from GCode to the text editor
        try:
            self.gcode_editor_tab.load_text(self.app.gcode_edited.getvalue(), move_to_start=True, clear_text=True)
        except Exception as e:
            log.debug('FlatCAMCNNJob.on_edit_code_click() -->%s' % str(e))
            self.app.inform.emit('[ERROR] %s %s' % ('FlatCAMCNNJob.on_edit_code_click() -->', str(e)))
            return

        self.gcode_editor_tab.t_frame.show()
        self.app.proc_container.view.set_idle()

        self.layout.addStretch()

        # Editor
        self.exit_editor_button = QtWidgets.QPushButton(_('Exit Editor'))
        self.exit_editor_button.setIcon(QtGui.QIcon(self.app.resource_location + '/power16.png'))
        self.exit_editor_button.setToolTip(
            _("Exit from Editor.")
        )
        self.exit_editor_button.setStyleSheet("""
                                          QPushButton
                                          {
                                              font-weight: bold;
                                          }
                                          """)
        self.layout.addWidget(self.exit_editor_button)
        # ############################ FINSIHED GUI ###################################
        # #############################################################################

    def confirmation_message(self, accepted, minval, maxval):
        if accepted is False:
            self.app.inform[str, bool].emit('[WARNING_NOTCL] %s: [%.*f, %.*f]' % (_("Edited value is out of range"),
                                                                                  self.decimals,
                                                                                  minval,
                                                                                  self.decimals,
                                                                                  maxval), False)
        else:
            self.app.inform[str, bool].emit('[success] %s' % _("Edited value is within limits."), False)

    def confirmation_message_int(self, accepted, minval, maxval):
        if accepted is False:
            self.app.inform[str, bool].emit('[WARNING_NOTCL] %s: [%d, %d]' %
                                            (_("Edited value is out of range"), minval, maxval), False)
        else:
            self.app.inform[str, bool].emit('[success] %s' % _("Edited value is within limits."), False)
