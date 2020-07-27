# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 07/22/2020                                         #
# MIT Licence                                              #
# ##########################################################

from appEditors.AppTextEditor import AppTextEditor
from appObjects.FlatCAMCNCJob import CNCJobObject
from appGUI.GUIElements import FCTextArea, FCEntry, FCButton
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


class AppGCodeEditor(QtCore.QObject):

    def __init__(self, app, parent=None):
        super().__init__(parent=parent)

        self.app = app
        self.plain_text = ''
        self.callback = lambda x: None

        self.ui = AppGCodeEditorUI(app=self.app)

        self.gcode_obj = None
        self.code_edited = ''

        # store the status of the editor so the Delete at object level will not work until the edit is finished
        self.editor_active = False
        log.debug("Initialization of the GCode Editor is finished ...")

    def set_ui(self):
        """

        :return:
        :rtype:
        """
        # #############################################################################################################
        # ############# ADD a new TAB in the PLot Tab Area
        # #############################################################################################################
        self.ui.gcode_editor_tab = AppTextEditor(app=self.app, plain_text=True)

        # add the tab if it was closed
        self.app.ui.plot_tab_area.addTab(self.ui.gcode_editor_tab, '%s' % _("Code Editor"))
        self.ui.gcode_editor_tab.setObjectName('code_editor_tab')

        # delete the absolute and relative position and messages in the infobar
        self.app.ui.position_label.setText("")
        self.app.ui.rel_position_label.setText("")

        self.ui.gcode_editor_tab.code_editor.completer_enable = False
        self.ui.gcode_editor_tab.buttonRun.hide()

        # Switch plot_area to CNCJob tab
        self.app.ui.plot_tab_area.setCurrentWidget(self.ui.gcode_editor_tab)

        self.ui.gcode_editor_tab.t_frame.hide()

        self.ui.gcode_editor_tab.t_frame.show()
        self.app.proc_container.view.set_idle()
        # #############################################################################################################
        # #############################################################################################################

        self.ui.append_text.set_value(self.app.defaults["cncjob_append"])
        self.ui.prepend_text.set_value(self.app.defaults["cncjob_prepend"])

        # #################################################################################
        # ################### SIGNALS #####################################################
        # #################################################################################
        self.ui.update_gcode_button.clicked.connect(self.insert_gcode)
        self.ui.exit_editor_button.clicked.connect(self.update_fcgcode)

    def build_ui(self):
        """

        :return:
        :rtype:
        """
        # Remove anything else in the GUI Selected Tab
        self.app.ui.selected_scroll_area.takeWidget()
        # Put ourselves in the GUI Selected Tab
        self.app.ui.selected_scroll_area.setWidget(self.ui.edit_widget)
        # Switch notebook to Selected page
        self.app.ui.notebook.setCurrentWidget(self.app.ui.selected_tab)

    def ui_connect(self):
        """

        :return:
        :rtype:
        """
        pass

    def ui_disconnect(self):
        """

        :return:
        :rtype:
        """
        pass

    def handleTextChanged(self):
        """

        :return:
        :rtype:
        """
        # enable = not self.ui.code_editor.document().isEmpty()
        # self.ui.buttonPrint.setEnabled(enable)
        # self.ui.buttonPreview.setEnabled(enable)

        self.buttonSave.setStyleSheet("QPushButton {color: red;}")
        self.buttonSave.setIcon(QtGui.QIcon(self.app.resource_location + '/save_as_red.png'))

    def insert_gcode(self):
        """

        :return:
        :rtype:
        """
        pass

    def edit_fcgcode(self, cnc_obj):
        """

        :param cnc_obj:
        :type cnc_obj:
        :return:
        :rtype:
        """
        assert isinstance(cnc_obj, CNCJobObject)
        self.gcode_obj = cnc_obj

        gcode_text = self.gcode_obj.source_file

        self.set_ui()
        self.build_ui()

        # then append the text from GCode to the text editor
        self.ui.gcode_editor_tab.load_text(gcode_text, move_to_start=True, clear_text=True)
        self.app.inform.emit('[success] %s...' % _('Loaded Machine Code into Code Editor'))

    def update_fcgcode(self):
        """

        :return:
        :rtype:
        """
        preamble = str(self.ui.prepend_text.get_value())
        postamble = str(self.ui.append_text.get_value())
        my_gcode = self.ui.gcode_editor_tab.code_editor.toPlainText()
        self.gcode_obj.source_file = my_gcode

        self.ui.gcode_editor_tab.buttonSave.setStyleSheet("")
        self.ui.gcode_editor_tab.setIcon(QtGui.QIcon(self.app.resource_location + '/save_as.png'))

    def on_open_gcode(self):
        """

        :return:
        :rtype:
        """
        _filter_ = "G-Code Files (*.nc);; G-Code Files (*.txt);; G-Code Files (*.tap);; G-Code Files (*.cnc);; " \
                   "All Files (*.*)"

        path, _f = QtWidgets.QFileDialog.getOpenFileName(
            caption=_('Open file'), directory=self.app.get_last_folder(), filter=_filter_)

        if path:
            file = QtCore.QFile(path)
            if file.open(QtCore.QIODevice.ReadOnly):
                stream = QtCore.QTextStream(file)
                self.code_edited = stream.readAll()
                self.ui.gcode_editor_tab.load_text(self.code_edited, move_to_start=True, clear_text=True)
                file.close()


class AppGCodeEditorUI:
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

        self.gcode_editor_tab = None

        self.edit_widget = QtWidgets.QWidget()
        # ## Box for custom widgets
        # This gets populated in offspring implementations.
        layout = QtWidgets.QVBoxLayout()
        self.edit_widget.setLayout(layout)

        # add a frame and inside add a vertical box layout. Inside this vbox layout I add all the Drills widgets
        # this way I can hide/show the frame
        self.edit_frame = QtWidgets.QFrame()
        self.edit_frame.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.edit_frame)
        self.edit_box = QtWidgets.QVBoxLayout()
        self.edit_box.setContentsMargins(0, 0, 0, 0)
        self.edit_frame.setLayout(self.edit_box)

        # ## Page Title box (spacing between children)
        self.title_box = QtWidgets.QHBoxLayout()
        self.edit_box.addLayout(self.title_box)

        # ## Page Title icon
        pixmap = QtGui.QPixmap(self.app.resource_location + '/flatcam_icon32.png')
        self.icon = QtWidgets.QLabel()
        self.icon.setPixmap(pixmap)
        self.title_box.addWidget(self.icon, stretch=0)

        # ## Title label
        self.title_label = QtWidgets.QLabel("<font size=5><b>%s</b></font>" % _('GCode Editor'))
        self.title_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.title_box.addWidget(self.title_label, stretch=1)

        # ## Object name
        self.name_box = QtWidgets.QHBoxLayout()
        self.edit_box.addLayout(self.name_box)
        name_label = QtWidgets.QLabel(_("Name:"))
        self.name_box.addWidget(name_label)
        self.name_entry = FCEntry()
        self.name_box.addWidget(self.name_entry)

        # Prepend text to GCode
        prependlabel = QtWidgets.QLabel('%s:' % _('Prepend to CNC Code'))
        prependlabel.setToolTip(
            _("Type here any G-Code commands you would\n"
              "like to add at the beginning of the G-Code file.")
        )
        self.edit_box.addWidget(prependlabel)

        self.prepend_text = FCTextArea()
        self.prepend_text.setPlaceholderText(
            _("Type here any G-Code commands you would\n"
              "like to add at the beginning of the G-Code file.")
        )
        self.edit_box.addWidget(self.prepend_text)

        # Append text to GCode
        appendlabel = QtWidgets.QLabel('%s:' % _('Append to CNC Code'))
        appendlabel.setToolTip(
            _("Type here any G-Code commands you would\n"
              "like to append to the generated file.\n"
              "I.e.: M2 (End of program)")
        )
        self.edit_box.addWidget(appendlabel)

        self.append_text = FCTextArea()
        self.append_text.setPlaceholderText(
            _("Type here any G-Code commands you would\n"
              "like to append to the generated file.\n"
              "I.e.: M2 (End of program)")
        )
        self.edit_box.addWidget(self.append_text)

        h_lay = QtWidgets.QHBoxLayout()
        h_lay.setAlignment(QtCore.Qt.AlignVCenter)
        self.edit_box.addLayout(h_lay)

        # GO Button
        self.update_gcode_button = FCButton(_('Update Code'))
        # self.update_gcode_button.setIcon(QtGui.QIcon(self.app.resource_location + '/save_as.png'))
        self.update_gcode_button.setToolTip(
            _("Update the Gcode in the Editor with the values\n"
              "in the 'Prepend' and 'Append' text boxes.")
        )

        h_lay.addWidget(self.update_gcode_button)

        layout.addStretch()

        # Editor
        self.exit_editor_button = FCButton(_('Exit Editor'))
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
        layout.addWidget(self.exit_editor_button)
        # ############################ FINSIHED GUI ##################################################################
        # #############################################################################################################

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
