# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 10/10/2019                                         #
# MIT Licence                                              #
# ##########################################################

from flatcamGUI.GUIElements import *
from PyQt5 import QtPrintSupport

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class TextEditor(QtWidgets.QWidget):

    def __init__(self, app, text=None, plain_text=None):
        super().__init__()

        self.app = app
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

        self.main_editor_layout = QtWidgets.QVBoxLayout(self)
        self.main_editor_layout.setContentsMargins(0, 0, 0, 0)

        self.t_frame = QtWidgets.QFrame()
        self.t_frame.setContentsMargins(0, 0, 0, 0)
        self.main_editor_layout.addWidget(self.t_frame)

        self.work_editor_layout = QtWidgets.QGridLayout(self.t_frame)
        self.work_editor_layout.setContentsMargins(2, 2, 2, 2)
        self.t_frame.setLayout(self.work_editor_layout)

        if plain_text:
            self.code_editor = FCPlainTextAreaExtended()
            stylesheet = """
                            QPlainTextEdit { selection-background-color:yellow;
                                             selection-color:black;
                            }
                         """
        else:
            self.code_editor = FCTextAreaExtended()
            stylesheet = """
                            QTextEdit { selection-background-color:yellow;
                                        selection-color:black;
                            }
                         """

        self.code_editor.setStyleSheet(stylesheet)

        if text:
            self.code_editor.setPlainText(text)

        self.buttonPreview = QtWidgets.QPushButton(_('Print Preview'))
        self.buttonPreview.setToolTip(_("Open a OS standard Preview Print window."))
        self.buttonPreview.setMinimumWidth(100)

        self.buttonPrint = QtWidgets.QPushButton(_('Print Code'))
        self.buttonPrint.setToolTip(_("Open a OS standard Print window."))

        self.buttonFind = QtWidgets.QPushButton(_('Find in Code'))
        self.buttonFind.setToolTip(_("Will search and highlight in yellow the string in the Find box."))
        self.buttonFind.setMinimumWidth(100)

        self.entryFind = FCEntry()
        self.entryFind.setToolTip(_("Find box. Enter here the strings to be searched in the text."))

        self.buttonReplace = QtWidgets.QPushButton(_('Replace With'))
        self.buttonReplace.setToolTip(_("Will replace the string from the Find box with the one in the Replace box."))
        self.buttonReplace.setMinimumWidth(100)

        self.entryReplace = FCEntry()
        self.entryReplace.setToolTip(_("String to replace the one in the Find box throughout the text."))

        self.sel_all_cb = QtWidgets.QCheckBox(_('All'))
        self.sel_all_cb.setToolTip(_("When checked it will replace all instances in the 'Find' box\n"
                                     "with the text in the 'Replace' box.."))

        self.button_copy_all = QtWidgets.QPushButton(_('Copy All'))
        self.button_copy_all.setToolTip(_("Will copy all the text in the Code Editor to the clipboard."))
        self.button_copy_all.setMinimumWidth(100)

        self.buttonOpen = QtWidgets.QPushButton(_('Open Code'))
        self.buttonOpen.setToolTip(_("Will open a text file in the editor."))

        self.buttonSave = QtWidgets.QPushButton(_('Save Code'))
        self.buttonSave.setToolTip(_("Will save the text in the editor into a file."))

        self.buttonRun = QtWidgets.QPushButton(_('Run Code'))
        self.buttonRun.setToolTip(_("Will run the TCL commands found in the text file, one by one."))

        self.buttonRun.hide()
        self.work_editor_layout.addWidget(self.code_editor, 0, 0, 1, 5)

        editor_hlay_1 = QtWidgets.QHBoxLayout()
        # cnc_tab_lay_1.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        editor_hlay_1.addWidget(self.buttonFind)
        editor_hlay_1.addWidget(self.entryFind)
        editor_hlay_1.addWidget(self.buttonReplace)
        editor_hlay_1.addWidget(self.entryReplace)
        editor_hlay_1.addWidget(self.sel_all_cb)
        editor_hlay_1.addWidget(self.button_copy_all)
        self.work_editor_layout.addLayout(editor_hlay_1, 1, 0, 1, 5)

        editor_hlay_2 = QtWidgets.QHBoxLayout()
        editor_hlay_2.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        editor_hlay_2.addWidget(self.buttonPreview)
        editor_hlay_2.addWidget(self.buttonPrint)
        self.work_editor_layout.addLayout(editor_hlay_2, 2, 0, 1, 1, QtCore.Qt.AlignLeft)

        cnc_tab_lay_4 = QtWidgets.QHBoxLayout()
        cnc_tab_lay_4.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        cnc_tab_lay_4.addWidget(self.buttonOpen)
        cnc_tab_lay_4.addWidget(self.buttonSave)
        cnc_tab_lay_4.addWidget(self.buttonRun)
        self.work_editor_layout.addLayout(cnc_tab_lay_4, 2, 4, 1, 1)

        # #################################################################################
        # ################### SIGNALS #####################################################
        # #################################################################################

        self.code_editor.textChanged.connect(self.handleTextChanged)
        self.buttonOpen.clicked.connect(self.handleOpen)
        self.buttonSave.clicked.connect(self.handleSaveGCode)
        self.buttonPrint.clicked.connect(self.handlePrint)
        self.buttonPreview.clicked.connect(self.handlePreview)
        self.buttonFind.clicked.connect(self.handleFindGCode)
        self.buttonReplace.clicked.connect(self.handleReplaceGCode)
        self.button_copy_all.clicked.connect(self.handleCopyAll)

        self.code_editor.set_model_data(self.app.myKeywords)

        self.gcode_edited = ''

    def handlePrint(self):
        self.app.report_usage("handlePrint()")

        dialog = QtPrintSupport.QPrintDialog()
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.code_editor.document().print_(dialog.printer())

    def handlePreview(self):
        self.app.report_usage("handlePreview()")

        dialog = QtPrintSupport.QPrintPreviewDialog()
        dialog.paintRequested.connect(self.code_editor.print_)
        dialog.exec_()

    def handleTextChanged(self):
        # enable = not self.ui.code_editor.document().isEmpty()
        # self.ui.buttonPrint.setEnabled(enable)
        # self.ui.buttonPreview.setEnabled(enable)
        pass

    def handleOpen(self, filt=None):
        self.app.report_usage("handleOpen()")

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
                self.gcode_edited = stream.readAll()
                self.code_editor.setPlainText(self.gcode_edited)
                file.close()

    def handleSaveGCode(self, name=None, filt=None):
        self.app.report_usage("handleSaveGCode()")

        if filt:
            _filter_ = filt
        else:
            _filter_ = "G-Code Files (*.nc);; G-Code Files (*.txt);; G-Code Files (*.tap);; G-Code Files (*.cnc);; " \
                       "All Files (*.*)"

        if name:
            obj_name = name
        else:
            try:
                obj_name = self.app.collection.get_active().options['name']
            except AttributeError:
                obj_name = 'file'
                if filt is None:
                    _filter_ = "FlatConfig Files (*.FlatConfig);;All Files (*.*)"

        try:
            filename = str(QtWidgets.QFileDialog.getSaveFileName(
                caption=_("Export Code ..."),
                directory=self.app.defaults["global_last_folder"] + '/' + str(obj_name),
                filter=_filter_
            )[0])
        except TypeError:
            filename = str(QtWidgets.QFileDialog.getSaveFileName(caption=_("Export Code ..."), filter=_filter_)[0])

        if filename == "":
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Export Code cancelled."))
            return
        else:
            try:
                my_gcode = self.code_editor.toPlainText()
                with open(filename, 'w') as f:
                    for line in my_gcode:
                        f.write(line)
            except FileNotFoundError:
                self.app.inform.emit('[WARNING] %s' % _("No such file or directory"))
                return
            except PermissionError:
                self.app.inform.emit('[WARNING] %s' %
                                     _("Permission denied, saving not possible.\n"
                                       "Most likely another app is holding the file open and not accessible."))
                return

        # Just for adding it to the recent files list.
        if self.app.defaults["global_open_style"] is False:
            self.app.file_opened.emit("cncjob", filename)
        self.app.file_saved.emit("cncjob", filename)
        self.app.inform.emit('%s: %s' % (_("Saved to"), str(filename)))

    def handleFindGCode(self):
        self.app.report_usage("handleFindGCode()")

        flags = QtGui.QTextDocument.FindCaseSensitively
        text_to_be_found = self.entryFind.get_value()

        r = self.code_editor.find(str(text_to_be_found), flags)
        if r is False:
            self.code_editor.moveCursor(QtGui.QTextCursor.Start)
            r = self.code_editor.find(str(text_to_be_found), flags)

    def handleReplaceGCode(self):
        self.app.report_usage("handleReplaceGCode()")

        old = self.entryFind.get_value()
        new = self.entryReplace.get_value()

        if self.sel_all_cb.isChecked():
            while True:
                cursor = self.code_editor.textCursor()
                cursor.beginEditBlock()
                flags = QtGui.QTextDocument.FindCaseSensitively
                # self.ui.editor is the QPlainTextEdit
                r = self.code_editor.find(str(old), flags)
                if r:
                    qc = self.code_editor.textCursor()
                    if qc.hasSelection():
                        qc.insertText(new)
                else:
                    self.ui.code_editor.moveCursor(QtGui.QTextCursor.Start)
                    break
            # Mark end of undo block
            cursor.endEditBlock()
        else:
            cursor = self.code_editor.textCursor()
            cursor.beginEditBlock()
            qc = self.code_editor.textCursor()
            if qc.hasSelection():
                qc.insertText(new)
            # Mark end of undo block
            cursor.endEditBlock()

    def handleCopyAll(self):
        text = self.code_editor.toPlainText()
        self.app.clipboard.setText(text)
        self.app.inform.emit(_("Code Editor content copied to clipboard ..."))

    # def closeEvent(self, QCloseEvent):
    #     super().closeEvent(QCloseEvent)
