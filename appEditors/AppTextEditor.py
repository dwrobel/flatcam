# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 10/10/2019                                         #
# MIT Licence                                              #
# ##########################################################

from appGUI.GUIElements import FCFileSaveDialog, FCEntry, FCTextAreaExtended, FCTextAreaLineNumber, FCButton
from PyQt5 import QtPrintSupport, QtWidgets, QtCore, QtGui

from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch, mm

# from io import StringIO

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class AppTextEditor(QtWidgets.QWidget):

    def __init__(self, app, text=None, plain_text=None, parent=None):
        super().__init__(parent=parent)

        self.app = app
        self.plain_text = plain_text
        self.callback = lambda x: None

        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

        # UI Layout
        self.main_editor_layout = QtWidgets.QVBoxLayout(self)
        self.main_editor_layout.setContentsMargins(0, 0, 0, 0)

        self.t_frame = QtWidgets.QFrame()
        self.t_frame.setContentsMargins(0, 0, 0, 0)
        self.main_editor_layout.addWidget(self.t_frame)

        self.work_editor_layout = QtWidgets.QGridLayout(self.t_frame)
        self.work_editor_layout.setContentsMargins(2, 2, 2, 2)
        self.t_frame.setLayout(self.work_editor_layout)

        # CODE Editor
        if self.plain_text:
            self.editor_class = FCTextAreaLineNumber()
            self.code_editor = self.editor_class.edit

            stylesheet = """
                            QPlainTextEdit { selection-background-color:yellow;
                                             selection-color:black;
                            }
                         """
            self.work_editor_layout.addWidget(self.editor_class, 0, 0, 1, 5)
        else:
            self.code_editor = FCTextAreaExtended()
            stylesheet = """
                            QTextEdit { selection-background-color:yellow;
                                        selection-color:black;
                            }
                         """
            self.work_editor_layout.addWidget(self.code_editor, 0, 0, 1, 5)

        self.code_editor.setStyleSheet(stylesheet)

        if text:
            self.code_editor.setPlainText(text)

        # #############################################################################################################
        # UI SETUP
        # #############################################################################################################
        control_lay = QtWidgets.QHBoxLayout()
        self.work_editor_layout.addLayout(control_lay, 1, 0, 1, 5)

        # FIND
        self.buttonFind = FCButton(_('Find'))
        self.buttonFind.setIcon(QtGui.QIcon(self.app.resource_location + '/find32.png'))
        self.buttonFind.setToolTip(_("Will search and highlight in yellow the string in the Find box."))
        control_lay.addWidget(self.buttonFind)

        # Entry FIND
        self.entryFind = FCEntry()
        self.entryFind.setToolTip(_("Find box. Enter here the strings to be searched in the text."))
        control_lay.addWidget(self.entryFind)

        # REPLACE
        self.buttonReplace = FCButton(_('Replace With'))
        self.buttonReplace.setIcon(QtGui.QIcon(self.app.resource_location + '/replace32.png'))
        self.buttonReplace.setToolTip(_("Will replace the string from the Find box with the one in the Replace box."))
        control_lay.addWidget(self.buttonReplace)

        # Entry REPLACE
        self.entryReplace = FCEntry()
        self.entryReplace.setToolTip(_("String to replace the one in the Find box throughout the text."))
        control_lay.addWidget(self.entryReplace)

        # Select All
        self.sel_all_cb = QtWidgets.QCheckBox(_('All'))
        self.sel_all_cb.setToolTip(_("When checked it will replace all instances in the 'Find' box\n"
                                     "with the text in the 'Replace' box.."))
        control_lay.addWidget(self.sel_all_cb)

        # COPY All
        # self.button_copy_all = FCButton(_('Copy All'))
        # self.button_copy_all.setIcon(QtGui.QIcon(self.app.resource_location + '/copy_file32.png'))
        # self.button_copy_all.setToolTip(_("Will copy all the text in the Code Editor to the clipboard."))
        # control_lay.addWidget(self.button_copy_all)

        # Update
        self.button_update_code = QtWidgets.QToolButton()
        self.button_update_code.setIcon(QtGui.QIcon(self.app.resource_location + '/save_as.png'))
        self.button_update_code.setToolTip(_("Save changes internally."))
        self.button_update_code.hide()
        control_lay.addWidget(self.button_update_code)

        # Print PREVIEW
        self.buttonPreview = QtWidgets.QToolButton()
        self.buttonPreview.setIcon(QtGui.QIcon(self.app.resource_location + '/preview32.png'))
        self.buttonPreview.setToolTip(_("Open a OS standard Preview Print window."))
        control_lay.addWidget(self.buttonPreview)

        # PRINT
        self.buttonPrint = QtWidgets.QToolButton()
        self.buttonPrint.setIcon(QtGui.QIcon(self.app.resource_location + '/printer32.png'))
        self.buttonPrint.setToolTip(_("Open a OS standard Print window."))
        control_lay.addWidget(self.buttonPrint)

        # OPEN
        self.buttonOpen = QtWidgets.QToolButton()
        self.buttonOpen.setIcon(QtGui.QIcon(self.app.resource_location + '/folder32_bis.png'))
        self.buttonOpen.setToolTip(_("Will open a text file in the editor."))
        control_lay.addWidget(self.buttonOpen)

        # SAVE
        self.buttonSave = QtWidgets.QToolButton()
        self.buttonSave.setIcon(QtGui.QIcon(self.app.resource_location + '/save_as.png'))
        self.buttonSave.setToolTip(_("Will save the text in the editor into a file."))
        control_lay.addWidget(self.buttonSave)

        # RUN
        self.buttonRun = FCButton(_('Run'))
        self.buttonRun.setToolTip(_("Will run the TCL commands found in the text file, one by one."))
        self.buttonRun.hide()
        control_lay.addWidget(self.buttonRun)

        # #############################################################################################################
        # ################### SIGNALS #################################################################################
        # #############################################################################################################
        self.code_editor.textChanged.connect(self.handleTextChanged)
        self.buttonOpen.clicked.connect(self.handleOpen)
        self.buttonSave.clicked.connect(self.handleSaveGCode)
        self.buttonPrint.clicked.connect(self.handlePrint)
        self.buttonPreview.clicked.connect(self.handlePreview)
        self.buttonFind.clicked.connect(self.handleFindGCode)
        self.buttonReplace.clicked.connect(self.handleReplaceGCode)
        # self.button_copy_all.clicked.connect(self.handleCopyAll)

        self.code_editor.set_model_data(self.app.myKeywords)

        self.code_edited = ''

    def set_callback(self, callback):
        self.callback = callback

    def handlePrint(self):
        dialog = QtPrintSupport.QPrintDialog()
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            self.code_editor.document().print_(dialog.printer())

    def handlePreview(self):
        dialog = QtPrintSupport.QPrintPreviewDialog()
        dialog.paintRequested.connect(self.code_editor.print)
        dialog.exec()

    def handleTextChanged(self):
        # enable = not self.ui.code_editor.document().isEmpty()
        # self.ui.buttonPrint.setEnabled(enable)
        # self.ui.buttonPreview.setEnabled(enable)

        self.buttonSave.setStyleSheet("QPushButton {color: red;}")
        self.buttonSave.setIcon(QtGui.QIcon(self.app.resource_location + '/save_as_red.png'))

    def load_text(self, text, move_to_start=False, move_to_end=False, clear_text=True, as_html=False):
        self.code_editor.textChanged.disconnect()
        if clear_text:
            # first clear previous text in text editor (if any)
            self.code_editor.clear()

        self.code_editor.setReadOnly(False)
        if as_html is False:
            self.code_editor.setPlainText(text)
        else:
            self.code_editor.setHtml(text)
        if move_to_start:
            self.code_editor.moveCursor(QtGui.QTextCursor.Start)
        elif move_to_end:
            self.code_editor.moveCursor(QtGui.QTextCursor.End)
        self.code_editor.textChanged.connect(self.handleTextChanged)

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
                self.code_editor.setPlainText(self.code_edited)
                file.close()

    def handleSaveGCode(self, name=None, filt=None, callback=None):
        self.app.defaults.report_usage("handleSaveGCode()")

        if filt:
            _filter_ = filt
        else:
            _filter_ = "G-Code Files (*.nc);; G-Code Files (*.txt);; G-Code Files (*.tap);; G-Code Files (*.cnc);; " \
                       "PDF Files (*.pdf);;All Files (*.*)"

        if name:
            obj_name = name
        else:
            try:
                obj_name = self.app.collection.get_active().options['name']
            except AttributeError:
                obj_name = 'file'
                if filt is None:
                    _filter_ = "FlatConfig Files (*.FlatConfig);;PDF Files (*.pdf);;All Files (*.*)"

        try:
            filename = str(FCFileSaveDialog.get_saved_filename(
                caption=_("Export Code ..."),
                directory=self.app.defaults["global_last_folder"] + '/' + str(obj_name),
                ext_filter=_filter_
            )[0])
        except TypeError:
            filename = str(FCFileSaveDialog.get_saved_filename(
                caption=_("Export Code ..."),
                ext_filter=_filter_)[0])

        if filename == "":
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
            return
        else:
            try:
                my_gcode = self.code_editor.toPlainText()
                if filename.rpartition('.')[2].lower() == 'pdf':
                    page_size = (
                        self.app.plotcanvas.pagesize_dict[self.app.defaults['global_workspaceT']][0] * mm,
                        self.app.plotcanvas.pagesize_dict[self.app.defaults['global_workspaceT']][1] * mm
                    )

                    # add new line after each line
                    lined_gcode = my_gcode.replace("\n", "<br />")

                    styles = getSampleStyleSheet()
                    styleN = styles['Normal']
                    # styleH = styles['Heading1']
                    story = []

                    if self.app.defaults['units'].lower() == 'mm':
                        bmargin = self.app.defaults['global_tpdf_bmargin'] * mm
                        tmargin = self.app.defaults['global_tpdf_tmargin'] * mm
                        rmargin = self.app.defaults['global_tpdf_rmargin'] * mm
                        lmargin = self.app.defaults['global_tpdf_lmargin'] * mm
                    else:
                        bmargin = self.app.defaults['global_tpdf_bmargin'] * inch
                        tmargin = self.app.defaults['global_tpdf_tmargin'] * inch
                        rmargin = self.app.defaults['global_tpdf_rmargin'] * inch
                        lmargin = self.app.defaults['global_tpdf_lmargin'] * inch

                    doc = SimpleDocTemplate(
                        filename,
                        pagesize=page_size,
                        bottomMargin=bmargin,
                        topMargin=tmargin,
                        rightMargin=rmargin,
                        leftMargin=lmargin)

                    P = Paragraph(lined_gcode, styleN)
                    story.append(P)

                    doc.build(
                        story,
                    )
                else:
                    with open(filename, 'w') as f:
                        for line in my_gcode:
                            f.write(line)
                self.buttonSave.setStyleSheet("")
                self.buttonSave.setIcon(QtGui.QIcon(self.app.resource_location + '/save_as.png'))
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

        if callback is not None:
            callback()

    def handleFindGCode(self):

        flags = QtGui.QTextDocument.FindCaseSensitively
        text_to_be_found = self.entryFind.get_value()

        r = self.code_editor.find(str(text_to_be_found), flags)
        if r is False:
            self.code_editor.moveCursor(QtGui.QTextCursor.Start)
            self.code_editor.find(str(text_to_be_found), flags)

    def handleReplaceGCode(self):

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
                    self.code_editor.moveCursor(QtGui.QTextCursor.Start)
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

    # def handleCopyAll(self):
    #     text = self.code_editor.toPlainText()
    #     self.app.clipboard.setText(text)
    #     self.app.inform.emit(_("Content copied to clipboard ..."))

    # def closeEvent(self, QCloseEvent):
    #     super().closeEvent(QCloseEvent)
