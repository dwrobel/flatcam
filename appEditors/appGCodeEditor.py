# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 07/22/2020                                         #
# MIT Licence                                              #
# ##########################################################

from appEditors.AppTextEditor import AppTextEditor
from appObjects.FlatCAMCNCJob import CNCJobObject
from appGUI.GUIElements import FCTextArea, FCEntry, FCButton, FCTable
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
        self.decimals = self.app.decimals
        self.plain_text = ''
        self.callback = lambda x: None

        self.ui = AppGCodeEditorUI(app=self.app)

        self.edited_obj_name = ""
        self.edit_area = None

        self.gcode_obj = None
        self.code_edited = ''

        # #################################################################################
        # ################### SIGNALS #####################################################
        # #################################################################################
        self.ui.name_entry.returnPressed.connect(self.on_name_activate)
        self.ui.update_gcode_button.clicked.connect(self.insert_gcode)
        self.ui.exit_editor_button.clicked.connect(lambda: self.app.editor2object())

        log.debug("Initialization of the GCode Editor is finished ...")

    def set_ui(self):
        """

        :return:
        :rtype:
        """

        self.decimals = self.app.decimals

        # #############################################################################################################
        # ############# ADD a new TAB in the PLot Tab Area
        # #############################################################################################################
        self.ui.gcode_editor_tab = AppTextEditor(app=self.app, plain_text=True)
        self.edit_area = self.ui.gcode_editor_tab.code_editor

        # add the tab if it was closed
        self.app.ui.plot_tab_area.addTab(self.ui.gcode_editor_tab, '%s' % _("Code Editor"))
        self.ui.gcode_editor_tab.setObjectName('gcode_editor_tab')
        # protect the tab that was just added
        for idx in range(self.app.ui.plot_tab_area.count()):
            if self.app.ui.plot_tab_area.widget(idx).objectName() == self.ui.gcode_editor_tab.objectName():
                self.app.ui.plot_tab_area.protectTab(idx)

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

        # Remove anything else in the GUI Properties Tab
        self.app.ui.properties_scroll_area.takeWidget()
        # Put ourselves in the GUI Properties Tab
        self.app.ui.properties_scroll_area.setWidget(self.ui.edit_widget)
        # Switch notebook to Properties page
        self.app.ui.notebook.setCurrentWidget(self.app.ui.properties_tab)

        # make a new name for the new Excellon object (the one with edited content)
        self.edited_obj_name = self.gcode_obj.options['name']
        self.ui.name_entry.set_value(self.edited_obj_name)

        self.activate()

    def build_ui(self):
        """

        :return:
        :rtype:
        """

        self.ui_disconnect()

        # if the FlatCAM object is Excellon don't build the CNC Tools Table but hide it
        self.ui.cnc_tools_table.hide()
        if self.gcode_obj.cnc_tools:
            self.ui.cnc_tools_table.show()
            self.build_cnc_tools_table()

        self.ui.exc_cnc_tools_table.hide()
        if self.gcode_obj.exc_cnc_tools:
            self.ui.exc_cnc_tools_table.show()
            self.build_excellon_cnc_tools()

        self.ui_connect()

    def build_cnc_tools_table(self):
        tool_idx = 0
        row_no = 0

        n = len(self.gcode_obj.cnc_tools) + 3
        self.ui.cnc_tools_table.setRowCount(n)

        # add the All Gcode selection
        allgcode_item = QtWidgets.QTableWidgetItem('%s' % _("All GCode"))
        allgcode_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        self.ui.cnc_tools_table.setItem(row_no, 1, allgcode_item)
        row_no += 1

        # add the Header Gcode selection
        header_item = QtWidgets.QTableWidgetItem('%s' % _("Header GCode"))
        header_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        self.ui.cnc_tools_table.setItem(row_no, 1, header_item)
        row_no += 1

        # add the Start Gcode selection
        start_item = QtWidgets.QTableWidgetItem('%s' % _("Start GCode"))
        start_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        self.ui.cnc_tools_table.setItem(row_no, 1, start_item)

        for dia_key, dia_value in self.gcode_obj.cnc_tools.items():

            tool_idx += 1
            row_no += 1

            t_id = QtWidgets.QTableWidgetItem('%d' % int(tool_idx))
            # id.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.ui.cnc_tools_table.setItem(row_no, 0, t_id)  # Tool name/id

            dia_item = QtWidgets.QTableWidgetItem('%.*f' % (self.decimals, float(dia_value['tooldia'])))

            offset_txt = list(str(dia_value['offset']))
            offset_txt[0] = offset_txt[0].upper()
            offset_item = QtWidgets.QTableWidgetItem(''.join(offset_txt))
            type_item = QtWidgets.QTableWidgetItem(str(dia_value['type']))
            tool_type_item = QtWidgets.QTableWidgetItem(str(dia_value['tool_type']))

            t_id.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            dia_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            offset_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            type_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            tool_type_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

            self.ui.cnc_tools_table.setItem(row_no, 1, dia_item)  # Diameter
            self.ui.cnc_tools_table.setItem(row_no, 2, offset_item)  # Offset
            self.ui.cnc_tools_table.setItem(row_no, 3, type_item)  # Toolpath Type
            self.ui.cnc_tools_table.setItem(row_no, 4, tool_type_item)  # Tool Type

            tool_uid_item = QtWidgets.QTableWidgetItem(str(dia_key))
            # ## REMEMBER: THIS COLUMN IS HIDDEN IN OBJECTUI.PY # ##
            self.ui.cnc_tools_table.setItem(row_no, 5, tool_uid_item)  # Tool unique ID)

        self.ui.cnc_tools_table.resizeColumnsToContents()
        self.ui.cnc_tools_table.resizeRowsToContents()

        vertical_header = self.ui.cnc_tools_table.verticalHeader()
        # vertical_header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        vertical_header.hide()
        self.ui.cnc_tools_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        horizontal_header = self.ui.cnc_tools_table.horizontalHeader()
        horizontal_header.setMinimumSectionSize(10)
        horizontal_header.setDefaultSectionSize(70)
        horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(0, 20)
        horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        horizontal_header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(4, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(4, 40)

        # horizontal_header.setStretchLastSection(True)
        self.ui.cnc_tools_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.ui.cnc_tools_table.setColumnWidth(0, 20)
        self.ui.cnc_tools_table.setColumnWidth(4, 40)
        self.ui.cnc_tools_table.setColumnWidth(6, 17)

        # self.ui.geo_tools_table.setSortingEnabled(True)

        self.ui.cnc_tools_table.setMinimumHeight(self.ui.cnc_tools_table.getHeight())
        self.ui.cnc_tools_table.setMaximumHeight(self.ui.cnc_tools_table.getHeight())

    def build_excellon_cnc_tools(self):
        """

        :return:
        :rtype:
        """

        tool_idx = 0
        row_no = 0

        n = len(self.gcode_obj.exc_cnc_tools) + 3
        self.ui.exc_cnc_tools_table.setRowCount(n)

        # add the All Gcode selection
        allgcode_item = QtWidgets.QTableWidgetItem('%s' % _("All GCode"))
        allgcode_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        self.ui.exc_cnc_tools_table.setItem(row_no, 1, allgcode_item)
        row_no += 1

        # add the Header Gcode selection
        header_item = QtWidgets.QTableWidgetItem('%s' % _("Header GCode"))
        header_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        self.ui.exc_cnc_tools_table.setItem(row_no, 1, header_item)
        row_no += 1

        # add the Start Gcode selection
        start_item = QtWidgets.QTableWidgetItem('%s' % _("Start GCode"))
        start_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        self.ui.exc_cnc_tools_table.setItem(row_no, 1, start_item)

        for tooldia_key, dia_value in self.gcode_obj.exc_cnc_tools.items():

            tool_idx += 1
            row_no += 1

            t_id = QtWidgets.QTableWidgetItem('%d' % int(tool_idx))
            dia_item = QtWidgets.QTableWidgetItem('%.*f' % (self.decimals, float(tooldia_key)))
            nr_drills_item = QtWidgets.QTableWidgetItem('%d' % int(dia_value['nr_drills']))
            nr_slots_item = QtWidgets.QTableWidgetItem('%d' % int(dia_value['nr_slots']))
            cutz_item = QtWidgets.QTableWidgetItem('%.*f' % (
                self.decimals, float(dia_value['offset']) + float(dia_value['data']['tools_drill_cutz'])))

            t_id.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            dia_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            nr_drills_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            nr_slots_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            cutz_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

            self.ui.exc_cnc_tools_table.setItem(row_no, 0, t_id)  # Tool name/id
            self.ui.exc_cnc_tools_table.setItem(row_no, 1, dia_item)  # Diameter
            self.ui.exc_cnc_tools_table.setItem(row_no, 2, nr_drills_item)  # Nr of drills
            self.ui.exc_cnc_tools_table.setItem(row_no, 3, nr_slots_item)  # Nr of slots

            tool_uid_item = QtWidgets.QTableWidgetItem(str(dia_value['tool']))
            # ## REMEMBER: THIS COLUMN IS HIDDEN IN OBJECTUI.PY # ##
            self.ui.exc_cnc_tools_table.setItem(row_no, 4, tool_uid_item)  # Tool unique ID)
            self.ui.exc_cnc_tools_table.setItem(row_no, 5, cutz_item)

        self.ui.exc_cnc_tools_table.resizeColumnsToContents()
        self.ui.exc_cnc_tools_table.resizeRowsToContents()

        vertical_header = self.ui.exc_cnc_tools_table.verticalHeader()
        vertical_header.hide()
        self.ui.exc_cnc_tools_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        horizontal_header = self.ui.exc_cnc_tools_table.horizontalHeader()
        horizontal_header.setMinimumSectionSize(10)
        horizontal_header.setDefaultSectionSize(70)
        horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(0, 20)
        horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        horizontal_header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeToContents)

        # horizontal_header.setStretchLastSection(True)
        self.ui.exc_cnc_tools_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.ui.exc_cnc_tools_table.setColumnWidth(0, 20)
        self.ui.exc_cnc_tools_table.setColumnWidth(6, 17)

        self.ui.exc_cnc_tools_table.setMinimumHeight(self.ui.exc_cnc_tools_table.getHeight())
        self.ui.exc_cnc_tools_table.setMaximumHeight(self.ui.exc_cnc_tools_table.getHeight())

    def ui_connect(self):
        """

        :return:
        :rtype:
        """
        # rows selected
        if self.gcode_obj.cnc_tools:
            self.ui.cnc_tools_table.clicked.connect(self.on_row_selection_change)
            self.ui.cnc_tools_table.horizontalHeader().sectionClicked.connect(self.on_toggle_all_rows)
        if self.gcode_obj.exc_cnc_tools:
            self.ui.exc_cnc_tools_table.clicked.connect(self.on_row_selection_change)
            self.ui.exc_cnc_tools_table.horizontalHeader().sectionClicked.connect(self.on_toggle_all_rows)

    def ui_disconnect(self):
        """

        :return:
        :rtype:
        """
        # rows selected
        if self.gcode_obj.cnc_tools:
            try:
                self.ui.cnc_tools_table.clicked.disconnect(self.on_row_selection_change)
            except (TypeError, AttributeError):
                pass
            try:
                self.ui.cnc_tools_table.horizontalHeader().sectionClicked.disconnect(self.on_toggle_all_rows)
            except (TypeError, AttributeError):
                pass

        if self.gcode_obj.exc_cnc_tools:
            try:
                self.ui.exc_cnc_tools_table.clicked.disconnect(self.on_row_selection_change)
            except (TypeError, AttributeError):
                pass
            try:
                self.ui.exc_cnc_tools_table.horizontalHeader().sectionClicked.disconnect(self.on_toggle_all_rows)
            except (TypeError, AttributeError):
                pass

    def on_row_selection_change(self):
        """

        :return:
        :rtype:
        """
        flags = QtGui.QTextDocument.FindCaseSensitively
        self.edit_area.moveCursor(QtGui.QTextCursor.Start)

        if self.gcode_obj.cnc_tools:
            t_table = self.ui.cnc_tools_table
        elif self.gcode_obj.exc_cnc_tools:
            t_table = self.ui.exc_cnc_tools_table
        else:
            return

        sel_model = t_table.selectionModel()
        sel_indexes = sel_model.selectedIndexes()

        # it will iterate over all indexes which means all items in all columns too but I'm interested only on rows
        sel_rows = set()
        for idx in sel_indexes:
            sel_rows.add(idx.row())

        if 0 in sel_rows:
            self.edit_area.selectAll()
            return

        if 1 in sel_rows:
            text_to_be_found = self.gcode_obj.gc_header
            text_list = [x for x in text_to_be_found.split("\n") if x != '']

            self.edit_area.find(str(text_list[0]), flags)
            my_text_cursor = self.edit_area.textCursor()
            start_sel = my_text_cursor.selectionStart()

            end_sel = 0
            while True:
                f = self.edit_area.find(str(text_list[-1]), flags)
                if f is False:
                    break
                my_text_cursor = self.edit_area.textCursor()
                end_sel = my_text_cursor.selectionEnd()

            my_text_cursor.setPosition(start_sel)
            my_text_cursor.setPosition(end_sel, QtGui.QTextCursor.KeepAnchor)
            self.edit_area.setTextCursor(my_text_cursor)

        if 2 in sel_rows:
            text_to_be_found = self.gcode_obj.gc_start
            text_list = [x for x in text_to_be_found.split("\n") if x != '']

            self.edit_area.find(str(text_list[0]), flags)
            my_text_cursor = self.edit_area.textCursor()
            start_sel = my_text_cursor.selectionStart()

            end_sel = 0
            while True:
                f = self.edit_area.find(str(text_list[-1]), flags)
                if f is False:
                    break
                my_text_cursor = self.edit_area.textCursor()
                end_sel = my_text_cursor.selectionEnd()

            my_text_cursor.setPosition(start_sel)
            my_text_cursor.setPosition(end_sel, QtGui.QTextCursor.KeepAnchor)
            self.edit_area.setTextCursor(my_text_cursor)

        sel_list = []
        for row in sel_rows:
            # those are special rows treated before so we except them
            if row not in [0, 1, 2]:
                tool_no = int(t_table.item(row, 0).text())

                text_to_be_found = None
                if self.gcode_obj.cnc_tools:
                    text_to_be_found = self.gcode_obj.cnc_tools[tool_no]['gcode']
                elif self.gcode_obj.exc_cnc_tools:
                    tool_dia = self.app.dec_format(float(t_table.item(row, 1).text()), dec=self.decimals)
                    for tool_d in self.gcode_obj.exc_cnc_tools:
                        if self.app.dec_format(tool_d, dec=self.decimals) == tool_dia:
                            text_to_be_found = self.gcode_obj.exc_cnc_tools[tool_d]['gcode']
                    if text_to_be_found is None:
                        continue
                else:
                    continue

                text_list = [x for x in text_to_be_found.split("\n") if x != '']

                # self.edit_area.find(str(text_list[0]), flags)
                # my_text_cursor = self.edit_area.textCursor()
                # start_sel = my_text_cursor.selectionStart()

                # first I search for the tool
                found_tool = self.edit_area.find('T%d' % tool_no, flags)
                if found_tool is False:
                    continue

                # once the tool found then I set the text Cursor position to the tool Tx position
                my_text_cursor = self.edit_area.textCursor()
                tool_pos = my_text_cursor.selectionStart()
                my_text_cursor.setPosition(tool_pos)

                # I search for the first finding of the first line in the Tool GCode
                f = self.edit_area.find(str(text_list[0]), flags)
                if f is False:
                    continue

                # once found I set the text Cursor position here
                my_text_cursor = self.edit_area.textCursor()
                start_sel = my_text_cursor.selectionStart()

                # I search for the next find of M6 (which belong to the next tool
                m6 = self.edit_area.find('M6', flags)
                if m6 is False:
                    # this mean that we are in the last tool, we take all to the end
                    self.edit_area.moveCursor(QtGui.QTextCursor.End)
                    my_text_cursor = self.edit_area.textCursor()
                    end_sel = my_text_cursor.selectionEnd()
                else:
                    pos_list = []

                    my_text_cursor = self.edit_area.textCursor()
                    m6_pos = my_text_cursor.selectionEnd()

                    # move cursor back to the start of the tool gcode so the find method will work on the tool gcode
                    t_curs = self.edit_area.textCursor()
                    t_curs.setPosition(start_sel)
                    self.edit_area.setTextCursor(t_curs)

                    # search for all findings of the last line in the tool gcode
                    # yet, we may find in multiple locations or in the gcode that belong to other tools
                    while True:
                        f = self.edit_area.find(str(text_list[-1]), flags)
                        if f is False:
                            break
                        my_text_cursor = self.edit_area.textCursor()
                        pos_list.append(my_text_cursor.selectionEnd())

                    # now we find a position that is less than the m6_pos but also the closest (maximum)
                    belong_to_tool_list = []
                    for last_line_pos in pos_list:
                        if last_line_pos < m6_pos:
                            belong_to_tool_list.append(last_line_pos)
                    if belong_to_tool_list:
                        end_sel = max(belong_to_tool_list)
                    else:
                        # this mean that we are in the last tool, we take all to the end
                        self.edit_area.moveCursor(QtGui.QTextCursor.End)
                        my_text_cursor = self.edit_area.textCursor()
                        end_sel = my_text_cursor.selectionEnd()

                my_text_cursor.setPosition(start_sel)
                my_text_cursor.setPosition(end_sel, QtGui.QTextCursor.KeepAnchor)
                self.edit_area.setTextCursor(my_text_cursor)

                tool_selection = QtWidgets.QTextEdit.ExtraSelection()
                tool_selection.cursor = self.edit_area.textCursor()
                tool_selection.format.setFontUnderline(True)
                sel_list.append(tool_selection)

        self.edit_area.setExtraSelections(sel_list)

    def on_toggle_all_rows(self):
        """

        :return:
        :rtype:
        """
        if self.gcode_obj.cnc_tools:
            t_table = self.ui.cnc_tools_table
        elif self.gcode_obj.exc_cnc_tools:
            t_table = self.ui.exc_cnc_tools_table
        else:
            return

        sel_model = t_table.selectionModel()
        sel_indexes = sel_model.selectedIndexes()

        # it will iterate over all indexes which means all items in all columns too but I'm interested only on rows
        sel_rows = set()
        for idx in sel_indexes:
            sel_rows.add(idx.row())

        if len(sel_rows) == t_table.rowCount():
            t_table.clearSelection()
            my_text_cursor = self.edit_area.textCursor()
            my_text_cursor.clearSelection()
        else:
            t_table.selectAll()

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

    def update_fcgcode(self, edited_obj):
        """

        :return:
        :rtype:
        """
        my_gcode = self.ui.gcode_editor_tab.code_editor.toPlainText()
        self.gcode_obj.source_file = my_gcode
        self.deactivate()

        self.ui.gcode_editor_tab.buttonSave.setStyleSheet("")
        self.ui.gcode_editor_tab.buttonSave.setIcon(QtGui.QIcon(self.app.resource_location + '/save_as.png'))

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

    def activate(self):
        self.app.call_source = 'gcode_editor'

    def deactivate(self):
        self.app.call_source = 'app'

    def on_name_activate(self):
        self.edited_obj_name = self.ui.name_entry.get_value()


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

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.edit_box.addWidget(separator_line)

        # CNC Tools Table when made out of Geometry
        self.cnc_tools_table = FCTable()
        self.cnc_tools_table.setSortingEnabled(False)
        self.cnc_tools_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.edit_box.addWidget(self.cnc_tools_table)

        self.cnc_tools_table.setColumnCount(6)
        self.cnc_tools_table.setColumnWidth(0, 20)
        self.cnc_tools_table.setHorizontalHeaderLabels(['#', _('Dia'), _('Offset'), _('Type'), _('TT'), ''])
        self.cnc_tools_table.setColumnHidden(5, True)

        # CNC Tools Table when made out of Excellon
        self.exc_cnc_tools_table = FCTable()
        self.exc_cnc_tools_table.setSortingEnabled(False)
        self.exc_cnc_tools_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.edit_box.addWidget(self.exc_cnc_tools_table)

        self.exc_cnc_tools_table.setColumnCount(6)
        self.exc_cnc_tools_table.setColumnWidth(0, 20)
        self.exc_cnc_tools_table.setHorizontalHeaderLabels(['#', _('Dia'), _('Drills'), _('Slots'), '', _("Cut Z")])
        self.exc_cnc_tools_table.setColumnHidden(4, True)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.edit_box.addWidget(separator_line)

        # Prepend text to GCode
        prependlabel = QtWidgets.QLabel('%s 1:' % _('CNC Code Snippet'))
        prependlabel.setToolTip(
            _("Code snippet defined in Preferences.")
        )
        self.edit_box.addWidget(prependlabel)

        self.prepend_text = FCTextArea()
        self.prepend_text.setPlaceholderText(
            _("Type here any G-Code commands you would\n"
              "like to insert at the cursor location.")
        )
        self.edit_box.addWidget(self.prepend_text)

        # Insert Button
        self.update_gcode_button = FCButton(_('Insert Code'))
        # self.update_gcode_button.setIcon(QtGui.QIcon(self.app.resource_location + '/save_as.png'))
        self.update_gcode_button.setToolTip(
            _("Insert the code above at the cursor location.")
        )
        self.edit_box.addWidget(self.update_gcode_button)

        # Append text to GCode
        appendlabel = QtWidgets.QLabel('%s 2:' % _('CNC Code Snippet'))
        appendlabel.setToolTip(
            _("Code snippet defined in Preferences.")
        )
        self.edit_box.addWidget(appendlabel)

        self.append_text = FCTextArea()
        self.append_text.setPlaceholderText(
            _("Type here any G-Code commands you would\n"
              "like to insert at the cursor location.")
        )
        self.edit_box.addWidget(self.append_text)

        # Insert Button
        self.update_gcode_sec_button = FCButton(_('Insert Code'))
        # self.update_gcode_button.setIcon(QtGui.QIcon(self.app.resource_location + '/save_as.png'))
        self.update_gcode_sec_button.setToolTip(
            _("Insert the code above at the cursor location.")
        )
        self.edit_box.addWidget(self.update_gcode_sec_button)

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
