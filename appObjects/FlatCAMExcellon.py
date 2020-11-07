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


from shapely.geometry import LineString

from appParsers.ParseExcellon import Excellon
from appObjects.FlatCAMObj import *

import itertools
import numpy as np

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ExcellonObject(FlatCAMObj, Excellon):
    """
    Represents Excellon/Drill code. An object stored in the FlatCAM objects collection (a dict)
    """

    ui_type = ExcellonObjectUI
    optionChanged = QtCore.pyqtSignal(str)
    multicolored_build_sig = QtCore.pyqtSignal()

    def __init__(self, name):
        self.decimals = self.app.decimals

        self.circle_steps = int(self.app.defaults["geometry_circle_steps"])

        Excellon.__init__(self, geo_steps_per_circle=self.circle_steps)
        FlatCAMObj.__init__(self, name)

        self.kind = "excellon"

        self.options.update({
            "plot": True,
            "solid": False,
            "multicolored": False,
            "merge_fuse_tools": True,

            "tooldia": 0.1,
            "milling_dia": 0.04,
            "slot_tooldia": 0.1,

            "format_upper_in": 2,
            "format_lower_in": 4,
            "format_upper_mm": 3,
            "lower_mm": 3,
            "zeros": "T",
            "units": "INCH",
            "update": True,

            "optimization_type": "B",
            "search_time": 3
        })

        # TODO: Document this.
        self.tool_cbs = {}

        # dict that holds the object names and the option name
        # the key is the object name (defines in ObjectUI) for each UI element that is a parameter
        # particular for a tool and the value is the actual name of the option that the UI element is changing
        self.name2option = {}

        # default set of data to be added to each tool in self.tools as self.tools[tool]['data'] = self.default_data
        self.default_data = {}

        # variable to store the total amount of drills per job
        self.tot_drill_cnt = 0
        self.tool_row = 0

        # variable to store the total amount of slots per job
        self.tot_slot_cnt = 0
        self.tool_row_slots = 0

        # variable to store the distance travelled
        self.travel_distance = 0.0

        # store the source file here
        self.source_file = ""

        self.multigeo = False
        self.units_found = self.app.defaults['units']

        self.fill_color = self.app.defaults['excellon_plot_fill']
        self.outline_color = self.app.defaults['excellon_plot_line']
        self.alpha_level = 'bf'

        # the key is the tool id and the value is a list of shapes keys (indexes)
        self.shape_indexes_dict = {}

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from predecessors.
        self.ser_attrs += ['options', 'kind', 'fill_color', 'outline_color', 'alpha_level']

    def set_ui(self, ui):
        """
        Configures the user interface for this object.
        Connects options to form fields.

        :param ui:  User interface object.
        :type ui:   ExcellonObjectUI
        :return:    None
        """
        FlatCAMObj.set_ui(self, ui)

        log.debug("ExcellonObject.set_ui()")

        self.units = self.app.defaults['units'].upper()

        # fill in self.options values  for the Drilling Tool from self.app.options
        for opt_key, opt_val in self.app.options.items():
            if opt_key.find('tools_drill_') == 0:
                self.options[opt_key] = deepcopy(opt_val)

        # fill in self.default_data values from self.options
        for opt_key, opt_val in self.app.options.items():
            if opt_key.find('excellon_') == 0 or opt_key.find('tools_drill_') == 0:
                self.default_data[opt_key] = deepcopy(opt_val)

        self.form_fields.update({
            "plot":             self.ui.plot_cb,
            "solid":            self.ui.solid_cb,
            "multicolored":     self.ui.multicolored_cb,

            "autoload_db":      self.ui.autoload_db_cb,
            "tooldia":          self.ui.tooldia_entry,
            "slot_tooldia":     self.ui.slot_tooldia_entry,
        })

        self.to_form()

        # Show/Hide Advanced Options
        if self.app.defaults["global_app_level"] == 'b':
            self.ui.level.setText('<span style="color:green;"><b>%s</b></span>' % _('Basic'))

            self.ui.tools_table.setColumnHidden(4, True)
            self.ui.tools_table.setColumnHidden(5, True)
            self.ui.table_visibility_cb.set_value(True)
            self.ui.table_visibility_cb.hide()
            self.ui.autoload_db_cb.set_value(False)
            self.ui.autoload_db_cb.hide()
        else:
            self.ui.level.setText('<span style="color:red;"><b>%s</b></span>' % _('Advanced'))
            self.ui.table_visibility_cb.show()
            self.ui.table_visibility_cb.set_value(self.app.defaults["excellon_tools_table_display"])
            self.on_table_visibility_toggle(state=self.app.defaults["excellon_tools_table_display"])
            self.ui.autoload_db_cb.show()

        assert isinstance(self.ui, ExcellonObjectUI), \
            "Expected a ExcellonObjectUI, got %s" % type(self.ui)

        self.ui.plot_cb.stateChanged.connect(self.on_plot_cb_click)
        self.ui.solid_cb.stateChanged.connect(self.on_solid_cb_click)
        self.ui.multicolored_cb.stateChanged.connect(self.on_multicolored_cb_click)
        self.multicolored_build_sig.connect(self.on_multicolored_build)

        self.ui.autoload_db_cb.stateChanged.connect(self.on_autoload_db_toggled)

        # Editor
        self.ui.editor_button.clicked.connect(lambda: self.app.object2editor())

        # Properties
        self.ui.properties_button.toggled.connect(self.on_properties)
        self.calculations_finished.connect(self.update_area_chull)

        self.ui.drill_button.clicked.connect(lambda: self.app.drilling_tool.run(toggle=True))
        # FIXME will uncomment when Milling Tool is ready
        # self.ui.milling_button.clicked.connect(lambda: self.app.milling_tool.run(toggle=True))

        # UTILITIES
        self.ui.util_button.clicked.connect(lambda st: self.ui.util_frame.show() if st else self.ui.util_frame.hide())
        self.ui.generate_milling_button.clicked.connect(self.on_generate_milling_button_click)
        self.ui.generate_milling_slots_button.clicked.connect(self.on_generate_milling_slots_button_click)

        # Toggle all Table rows
        self.ui.tools_table.horizontalHeader().sectionClicked.connect(self.on_toggle_rows)

        self.ui.table_visibility_cb.stateChanged.connect(self.on_table_visibility_toggle)

        self.units_found = self.app.defaults['units']

    def build_ui(self):
        """
        Will (re)build the Excellon UI updating it (the tool table)

        :return:    None
        :rtype:
        """
        FlatCAMObj.build_ui(self)

        self.units = self.app.defaults['units'].upper()

        for row in range(self.ui.tools_table.rowCount()):
            try:
                # if connected, disconnect the signal from the slot on item_changed as it creates issues
                offset_spin_widget = self.ui.tools_table.cellWidget(row, 4)
                offset_spin_widget.valueChanged.disconnect()
            except (TypeError, AttributeError):
                pass

        n = len(self.tools)
        # we have (n+2) rows because there are 'n' tools, each a row, plus the last 2 rows for totals.
        self.ui.tools_table.setRowCount(n + 2)

        self.tot_drill_cnt = 0
        self.tot_slot_cnt = 0

        self.tool_row = 0

        sort = []
        for k, v in list(self.tools.items()):
            try:
                sort.append((k, v['tooldia']))
            except KeyError:
                # for old projects to be opened
                sort.append((k, v['C']))

        sorted_tools = sorted(sort, key=lambda t1: t1[1])
        tools = [i[0] for i in sorted_tools]

        new_options = {}
        for opt in self.options:
            new_options[opt] = self.options[opt]

        for tool_no in tools:
            try:
                dia_val = self.tools[tool_no]['tooldia']
            except KeyError:
                # for old projects to be opened
                dia_val = self.tools[tool_no]['C']

            # add the data dictionary for each tool with the default values
            self.tools[tool_no]['data'] = deepcopy(new_options)

            drill_cnt = 0  # variable to store the nr of drills per tool
            slot_cnt = 0  # variable to store the nr of slots per tool

            # Find no of drills for the current tool
            try:
                drill_cnt = len(self.tools[tool_no]['drills'])
            except KeyError:
                drill_cnt = 0
            self.tot_drill_cnt += drill_cnt

            # Find no of slots for the current tool
            try:
                slot_cnt = len(self.tools[tool_no]['slots'])
            except KeyError:
                slot_cnt = 0
            self.tot_slot_cnt += slot_cnt

            # Tool ID
            exc_id_item = QtWidgets.QTableWidgetItem('%d' % int(tool_no))
            exc_id_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.ui.tools_table.setItem(self.tool_row, 0, exc_id_item)  # Tool name/id

            # Diameter
            dia_item = QtWidgets.QTableWidgetItem('%.*f' % (self.decimals, dia_val))
            dia_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.ui.tools_table.setItem(self.tool_row, 1, dia_item)  # Diameter

            # Drill count
            drill_count_item = QtWidgets.QTableWidgetItem('%d' % drill_cnt)
            drill_count_item.setFlags(QtCore.Qt.ItemIsEnabled)
            self.ui.tools_table.setItem(self.tool_row, 2, drill_count_item)  # Number of drills per tool

            # Slot Count
            # if the slot number is zero is better to not clutter the GUI with zero's so we print a space
            slot_count_str = '%d' % slot_cnt if slot_cnt > 0 else ''
            slot_count_item = QtWidgets.QTableWidgetItem(slot_count_str)
            slot_count_item.setFlags(QtCore.Qt.ItemIsEnabled)
            self.ui.tools_table.setItem(self.tool_row, 3, slot_count_item)  # Number of drills per tool

            # Empty Plot Item
            empty_plot_item = QtWidgets.QTableWidgetItem('')
            empty_plot_item.setFlags(QtCore.Qt.NoItemFlags)
            self.ui.tools_table.setItem(self.tool_row, 4, empty_plot_item)

            if 'multicolor' in self.tools[tool_no] and self.tools[tool_no]['multicolor'] is not None:
                red = self.tools[tool_no]['multicolor'][0] * 255
                green = self.tools[tool_no]['multicolor'][1] * 255
                blue = self.tools[tool_no]['multicolor'][2] * 255
                alpha = self.tools[tool_no]['multicolor'][3] * 255
                h_color = QtGui.QColor(red, green, blue, alpha)
                self.ui.tools_table.item(self.tool_row, 4).setBackground(h_color)
            else:
                h1 = self.app.defaults["excellon_plot_fill"][1:7]
                h2 = self.app.defaults["excellon_plot_fill"][7:9]
                h_color = QtGui.QColor('#' + h2 + h1)
                self.ui.tools_table.item(self.tool_row, 4).setBackground(h_color)

            # Plot Item
            plot_item = FCCheckBox()
            plot_item.setLayoutDirection(QtCore.Qt.RightToLeft)
            if self.ui.plot_cb.isChecked():
                plot_item.setChecked(True)
            self.ui.tools_table.setCellWidget(self.tool_row, 5, plot_item)

            self.tool_row += 1

        # add a last row with the Total number of drills
        empty_1 = QtWidgets.QTableWidgetItem('')
        empty_1.setFlags(QtCore.Qt.NoItemFlags)
        empty_1_1 = QtWidgets.QTableWidgetItem('')
        empty_1_1.setFlags(QtCore.Qt.NoItemFlags)
        empty_1_2 = QtWidgets.QTableWidgetItem('')
        empty_1_2.setFlags(QtCore.Qt.NoItemFlags)
        empty_1_3 = QtWidgets.QTableWidgetItem('')
        empty_1_3.setFlags(QtCore.Qt.NoItemFlags)
        empty_1_4 = QtWidgets.QTableWidgetItem('')
        empty_1_4.setFlags(QtCore.Qt.NoItemFlags)

        label_tot_drill_count = QtWidgets.QTableWidgetItem(_('Total Drills'))
        tot_drill_count = QtWidgets.QTableWidgetItem('%d' % self.tot_drill_cnt)
        label_tot_drill_count.setFlags(QtCore.Qt.ItemIsEnabled)
        tot_drill_count.setFlags(QtCore.Qt.ItemIsEnabled)

        self.ui.tools_table.setItem(self.tool_row, 0, empty_1)
        self.ui.tools_table.setItem(self.tool_row, 1, label_tot_drill_count)
        self.ui.tools_table.setItem(self.tool_row, 2, tot_drill_count)  # Total number of drills
        self.ui.tools_table.setItem(self.tool_row, 3, empty_1_1)
        self.ui.tools_table.setItem(self.tool_row, 4, empty_1_2)
        self.ui.tools_table.setItem(self.tool_row, 5, empty_1_3)

        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)

        for k in [1, 2]:
            self.ui.tools_table.item(self.tool_row, k).setForeground(QtGui.QColor(127, 0, 255))
            self.ui.tools_table.item(self.tool_row, k).setFont(font)

        self.tool_row += 1

        # add a last row with the Total number of slots
        empty_2 = QtWidgets.QTableWidgetItem('')
        empty_2.setFlags(QtCore.Qt.NoItemFlags)
        empty_2_1 = QtWidgets.QTableWidgetItem('')
        empty_2_1.setFlags(QtCore.Qt.NoItemFlags)
        empty_2_2 = QtWidgets.QTableWidgetItem('')
        empty_2_2.setFlags(QtCore.Qt.NoItemFlags)
        empty_2_3 = QtWidgets.QTableWidgetItem('')
        empty_2_3.setFlags(QtCore.Qt.NoItemFlags)
        empty_2_4 = QtWidgets.QTableWidgetItem('')
        empty_2_4.setFlags(QtCore.Qt.NoItemFlags)

        label_tot_slot_count = QtWidgets.QTableWidgetItem(_('Total Slots'))
        tot_slot_count = QtWidgets.QTableWidgetItem('%d' % self.tot_slot_cnt)
        label_tot_slot_count.setFlags(QtCore.Qt.ItemIsEnabled)
        tot_slot_count.setFlags(QtCore.Qt.ItemIsEnabled)

        self.ui.tools_table.setItem(self.tool_row, 0, empty_2)
        self.ui.tools_table.setItem(self.tool_row, 1, label_tot_slot_count)
        self.ui.tools_table.setItem(self.tool_row, 2, empty_2_1)
        self.ui.tools_table.setItem(self.tool_row, 3, tot_slot_count)  # Total number of slots
        self.ui.tools_table.setItem(self.tool_row, 4, empty_2_3)
        self.ui.tools_table.setItem(self.tool_row, 5, empty_2_4)

        for kl in [1, 2, 3]:
            self.ui.tools_table.item(self.tool_row, kl).setFont(font)
            self.ui.tools_table.item(self.tool_row, kl).setForeground(QtGui.QColor(0, 70, 255))

        # sort the tool diameter column
        # self.ui.tools_table.sortItems(1)

        # all the tools are selected by default
        self.ui.tools_table.selectColumn(0)

        self.ui.tools_table.resizeColumnsToContents()
        self.ui.tools_table.resizeRowsToContents()

        vertical_header = self.ui.tools_table.verticalHeader()
        # vertical_header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        vertical_header.hide()
        self.ui.tools_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        horizontal_header = self.ui.tools_table.horizontalHeader()
        horizontal_header.setMinimumSectionSize(10)
        horizontal_header.setDefaultSectionSize(70)
        horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(0, 20)

        horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)

        horizontal_header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(4, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(4, 17)
        horizontal_header.setSectionResizeMode(5, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(5, 17)
        self.ui.tools_table.setColumnWidth(5, 17)

        # horizontal_header.setStretchLastSection(True)
        # horizontal_header.setColumnWidth(2, QtWidgets.QHeaderView.ResizeToContents)

        # horizontal_header.setStretchLastSection(True)
        self.ui.tools_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.ui.tools_table.setSortingEnabled(False)

        self.ui.tools_table.setMinimumHeight(self.ui.tools_table.getHeight())
        self.ui.tools_table.setMaximumHeight(self.ui.tools_table.getHeight())

        # find if we have drills:
        has_drills = None
        for tt in self.tools:
            if 'drills' in self.tools[tt] and self.tools[tt]['drills']:
                has_drills = True
                break
        if has_drills is None:
            self.ui.tooldia_entry.setDisabled(True)
            self.ui.generate_milling_button.setDisabled(True)
        else:
            self.ui.tooldia_entry.setDisabled(False)
            self.ui.generate_milling_button.setDisabled(False)

        # find if we have slots
        has_slots = None
        for tt in self.tools:
            if 'slots' in self.tools[tt] and self.tools[tt]['slots']:
                has_slots = True
                break
        if has_slots is None:
            self.ui.slot_tooldia_entry.setDisabled(True)
            self.ui.generate_milling_slots_button.setDisabled(True)
        else:
            self.ui.slot_tooldia_entry.setDisabled(False)
            self.ui.generate_milling_slots_button.setDisabled(False)

        # update the milling section
        self.on_row_selection_change()

        self.ui_connect()

    def ui_connect(self):
        """
        Will connect all signals in the Excellon UI that needs to be connected

        :return:    None
        :rtype:
        """

        # selective plotting
        for row in range(self.ui.tools_table.rowCount() - 2):
            self.ui.tools_table.cellWidget(row, 5).clicked.connect(self.on_plot_cb_click_table)
        self.ui.plot_cb.stateChanged.connect(self.on_plot_cb_click)

        # rows selected
        self.ui.tools_table.clicked.connect(self.on_row_selection_change)

    def ui_disconnect(self):
        """
        Will disconnect all signals in the Excellon UI that needs to be disconnected

        :return:    None
        :rtype:
        """
        # selective plotting
        for row in range(self.ui.tools_table.rowCount()):
            try:
                self.ui.tools_table.cellWidget(row, 5).clicked.disconnect()
            except (TypeError, AttributeError):
                pass
        try:
            self.ui.plot_cb.stateChanged.disconnect()
        except (TypeError, AttributeError):
            pass

        # rows selected
        try:
            self.ui.tools_table.clicked.disconnect()
        except (TypeError, AttributeError):
            pass

    def on_row_selection_change(self):
        """
        Called when the user clicks on a row in Tools Table

        :return:    None
        :rtype:
        """
        self.ui_disconnect()

        sel_model = self.ui.tools_table.selectionModel()
        sel_indexes = sel_model.selectedIndexes()

        # it will iterate over all indexes which means all items in all columns too but I'm interested only on rows
        sel_rows = set()
        for idx in sel_indexes:
            sel_rows.add(idx.row())

        if not sel_rows:
            self.ui.tooldia_entry.setDisabled(True)
            self.ui.generate_milling_button.setDisabled(True)
            self.ui.slot_tooldia_entry.setDisabled(True)
            self.ui.generate_milling_slots_button.setDisabled(True)
            self.ui_connect()
            return
        else:
            self.ui.tooldia_entry.setDisabled(False)
            self.ui.generate_milling_button.setDisabled(False)
            self.ui.slot_tooldia_entry.setDisabled(False)
            self.ui.generate_milling_slots_button.setDisabled(False)

            has_drills = True
            has_slots = True
            for row in sel_rows:
                row_dia = self.app.dec_format(float(self.ui.tools_table.item(row, 1).text()), self.decimals)

                for tt in self.tools:
                    tool_dia = self.app.dec_format(float(self.tools[tt]['tooldia']), self.decimals)
                    if tool_dia == row_dia:
                        # find if we have drills:
                        if 'drills' not in self.tools[tt] or not self.tools[tt]['drills']:
                            has_drills = None

                        # find if we have slots
                        if 'slots' not in self.tools[tt] or not self.tools[tt]['slots']:
                            has_slots = None

            if has_drills is None:
                self.ui.tooldia_entry.setDisabled(True)
                self.ui.generate_milling_button.setDisabled(True)
            else:
                self.ui.tooldia_entry.setDisabled(False)
                self.ui.generate_milling_button.setDisabled(False)

            if has_slots is None:
                self.ui.slot_tooldia_entry.setDisabled(True)
                self.ui.generate_milling_slots_button.setDisabled(True)
            else:
                self.ui.slot_tooldia_entry.setDisabled(False)
                self.ui.generate_milling_slots_button.setDisabled(False)

        self.ui_connect()

    def on_toggle_rows(self):
        sel_model = self.ui.tools_table.selectionModel()
        sel_indexes = sel_model.selectedIndexes()

        # it will iterate over all indexes which means all items in all columns too but I'm interested only on rows
        sel_rows = set()
        for idx in sel_indexes:
            sel_rows.add(idx.row())

        # subtract the last 2 rows that show the total and are always displayed but not selected
        if len(sel_rows) == self.ui.tools_table.rowCount() - 2:
            self.ui.tools_table.clearSelection()
        else:
            self.ui.tools_table.selectAll()

        self.on_row_selection_change()

    def get_selected_tools_list(self):
        """
        Returns the keys to the self.tools dictionary corresponding
        to the selections on the tool list in the appGUI.

        :return:    List of tools.
        :rtype:     list
        """
        rows = set()
        for item in self.ui.tools_table.selectedItems():
            rows.add(item.row())

        tool_ids = []
        for row in rows:
            tool_ids.append(int(self.ui.tools_table.item(row, 0).text()))
        return tool_ids
        # return [x.text() for x in self.ui.tools_table.selectedItems()]

    def get_selected_tools_table_items(self):
        """
        Returns a list of lists, each list in the list is made out of row elements

        :return:    List of table_tools items.
        :rtype:     list
        """
        table_tools_items = []
        for x in self.ui.tools_table.selectedItems():
            # from the columnCount we subtract a value of 1 which represent the last column (plot column)
            # which does not have text
            txt = ''
            elem = []

            for column in range(0, self.ui.tools_table.columnCount() - 1):
                try:
                    txt = self.ui.tools_table.item(x.row(), column).text()
                except AttributeError:
                    try:
                        txt = self.ui.tools_table.cellWidget(x.row(), column).currentText()
                    except AttributeError:
                        pass
                elem.append(txt)
            table_tools_items.append(deepcopy(elem))
            # table_tools_items.append([self.ui.tools_table.item(x.row(), column).text()
            #                           for column in range(0, self.ui.tools_table.columnCount() - 1)])
        for item in table_tools_items:
            item[0] = str(item[0])
        return table_tools_items

    def on_table_visibility_toggle(self, state):
        self.ui.tools_table.show() if state else self.ui.tools_table.hide()

    def on_properties(self, state):
        if state:
            self.ui.properties_frame.show()
        else:
            self.ui.properties_frame.hide()
            return

        self.ui.treeWidget.clear()
        self.add_properties_items(obj=self, treeWidget=self.ui.treeWidget)

        # make sure that the FCTree widget columns are resized to content
        self.ui.treeWidget.resize_sig.emit()

    def export_excellon(self, whole, fract, e_zeros=None, form='dec', factor=1, slot_type='routing'):
        """
        Returns two values, first is a boolean , if 1 then the file has slots and second contain the Excellon code

        :param whole:       Integer part digits
        :type whole:        int
        :param fract:       Fractional part digits
        :type fract:        int
        :param e_zeros:     Excellon zeros suppression: LZ or TZ
        :type e_zeros:      str
        :param form:        Excellon format: 'dec',
        :type form:         str
        :param factor:      Conversion factor
        :type factor:       float
        :param slot_type:   How to treat slots: "routing" or "drilling"
        :type slot_type:    str
        :return:            A tuple: (has_slots, Excellon_code) -> (bool, str)
        :rtype:             tuple
        """

        excellon_code = ''

        # store here if the file has slots, return 1 if any slots, 0 if only drills
        slots_in_file = 0

        # find if we have drills:
        has_drills = None
        for tt in self.tools:
            if 'drills' in self.tools[tt] and self.tools[tt]['drills']:
                has_drills = True
                break
        # find if we have slots:
        has_slots = None
        for tt in self.tools:
            if 'slots' in self.tools[tt] and self.tools[tt]['slots']:
                has_slots = True
                slots_in_file = 1
                break

        # drills processing
        try:
            if has_drills:
                length = whole + fract
                for tool in self.tools:
                    excellon_code += 'T0%s\n' % str(tool) if int(tool) < 10 else 'T%s\n' % str(tool)

                    for drill in self.tools[tool]['drills']:
                        if form == 'dec':
                            drill_x = drill.x * factor
                            drill_y = drill.y * factor
                            excellon_code += "X{:.{dec}f}Y{:.{dec}f}\n".format(drill_x, drill_y, dec=fract)
                        elif e_zeros == 'LZ':
                            drill_x = drill.x * factor
                            drill_y = drill.y * factor

                            exc_x_formatted = "{:.{dec}f}".format(drill_x, dec=fract)
                            exc_y_formatted = "{:.{dec}f}".format(drill_y, dec=fract)

                            # extract whole part and decimal part
                            exc_x_formatted = exc_x_formatted.partition('.')
                            exc_y_formatted = exc_y_formatted.partition('.')

                            # left padd the 'whole' part with zeros
                            x_whole = exc_x_formatted[0].rjust(whole, '0')
                            y_whole = exc_y_formatted[0].rjust(whole, '0')

                            # restore the coordinate padded in the left with 0 and added the decimal part
                            # without the decinal dot
                            exc_x_formatted = x_whole + exc_x_formatted[2]
                            exc_y_formatted = y_whole + exc_y_formatted[2]

                            excellon_code += "X{xform}Y{yform}\n".format(xform=exc_x_formatted,
                                                                         yform=exc_y_formatted)
                        else:
                            drill_x = drill.x * factor
                            drill_y = drill.y * factor

                            exc_x_formatted = "{:.{dec}f}".format(drill_x, dec=fract).replace('.', '')
                            exc_y_formatted = "{:.{dec}f}".format(drill_y, dec=fract).replace('.', '')

                            # pad with rear zeros
                            exc_x_formatted.ljust(length, '0')
                            exc_y_formatted.ljust(length, '0')

                            excellon_code += "X{xform}Y{yform}\n".format(xform=exc_x_formatted,
                                                                         yform=exc_y_formatted)
        except Exception as e:
            log.debug(str(e))

        # slots processing
        try:
            if has_slots:
                for tool in self.tools:
                    excellon_code += 'G05\n'

                    if int(tool) < 10:
                        excellon_code += 'T0' + str(tool) + '\n'
                    else:
                        excellon_code += 'T' + str(tool) + '\n'

                    for slot in self.tools[tool]['slots']:
                        if form == 'dec':
                            start_slot_x = slot.x * factor
                            start_slot_y = slot.y * factor
                            stop_slot_x = slot.x * factor
                            stop_slot_y = slot.y * factor
                            if slot_type == 'routing':
                                excellon_code += "G00X{:.{dec}f}Y{:.{dec}f}\nM15\n".format(start_slot_x,
                                                                                           start_slot_y,
                                                                                           dec=fract)
                                excellon_code += "G01X{:.{dec}f}Y{:.{dec}f}\nM16\n".format(stop_slot_x,
                                                                                           stop_slot_y,
                                                                                           dec=fract)
                            elif slot_type == 'drilling':
                                excellon_code += "X{:.{dec}f}Y{:.{dec}f}G85X{:.{dec}f}Y{:.{dec}f}\nG05\n".format(
                                    start_slot_x, start_slot_y, stop_slot_x, stop_slot_y, dec=fract
                                )

                        elif e_zeros == 'LZ':
                            start_slot_x = slot.x * factor
                            start_slot_y = slot.y * factor
                            stop_slot_x = slot.x * factor
                            stop_slot_y = slot.y * factor

                            start_slot_x_formatted = "{:.{dec}f}".format(start_slot_x, dec=fract).replace('.', '')
                            start_slot_y_formatted = "{:.{dec}f}".format(start_slot_y, dec=fract).replace('.', '')
                            stop_slot_x_formatted = "{:.{dec}f}".format(stop_slot_x, dec=fract).replace('.', '')
                            stop_slot_y_formatted = "{:.{dec}f}".format(stop_slot_y, dec=fract).replace('.', '')

                            # extract whole part and decimal part
                            start_slot_x_formatted = start_slot_x_formatted.partition('.')
                            start_slot_y_formatted = start_slot_y_formatted.partition('.')
                            stop_slot_x_formatted = stop_slot_x_formatted.partition('.')
                            stop_slot_y_formatted = stop_slot_y_formatted.partition('.')

                            # left padd the 'whole' part with zeros
                            start_x_whole = start_slot_x_formatted[0].rjust(whole, '0')
                            start_y_whole = start_slot_y_formatted[0].rjust(whole, '0')
                            stop_x_whole = stop_slot_x_formatted[0].rjust(whole, '0')
                            stop_y_whole = stop_slot_y_formatted[0].rjust(whole, '0')

                            # restore the coordinate padded in the left with 0 and added the decimal part
                            # without the decinal dot
                            start_slot_x_formatted = start_x_whole + start_slot_x_formatted[2]
                            start_slot_y_formatted = start_y_whole + start_slot_y_formatted[2]
                            stop_slot_x_formatted = stop_x_whole + stop_slot_x_formatted[2]
                            stop_slot_y_formatted = stop_y_whole + stop_slot_y_formatted[2]

                            if slot_type == 'routing':
                                excellon_code += "G00X{xstart}Y{ystart}\nM15\n".format(xstart=start_slot_x_formatted,
                                                                                       ystart=start_slot_y_formatted)
                                excellon_code += "G01X{xstop}Y{ystop}\nM16\n".format(xstop=stop_slot_x_formatted,
                                                                                     ystop=stop_slot_y_formatted)
                            elif slot_type == 'drilling':
                                excellon_code += "{xstart}Y{ystart}G85X{xstop}Y{ystop}\nG05\n".format(
                                    xstart=start_slot_x_formatted, ystart=start_slot_y_formatted,
                                    xstop=stop_slot_x_formatted, ystop=stop_slot_y_formatted
                                )
                        else:
                            start_slot_x = slot.x * factor
                            start_slot_y = slot.y * factor
                            stop_slot_x = slot.x * factor
                            stop_slot_y = slot.y * factor
                            length = whole + fract

                            start_slot_x_formatted = "{:.{dec}f}".format(start_slot_x, dec=fract).replace('.', '')
                            start_slot_y_formatted = "{:.{dec}f}".format(start_slot_y, dec=fract).replace('.', '')
                            stop_slot_x_formatted = "{:.{dec}f}".format(stop_slot_x, dec=fract).replace('.', '')
                            stop_slot_y_formatted = "{:.{dec}f}".format(stop_slot_y, dec=fract).replace('.', '')

                            # pad with rear zeros
                            start_slot_x_formatted.ljust(length, '0')
                            start_slot_y_formatted.ljust(length, '0')
                            stop_slot_x_formatted.ljust(length, '0')
                            stop_slot_y_formatted.ljust(length, '0')

                            if slot_type == 'routing':
                                excellon_code += "G00X{xstart}Y{ystart}\nM15\n".format(xstart=start_slot_x_formatted,
                                                                                       ystart=start_slot_y_formatted)
                                excellon_code += "G01X{xstop}Y{ystop}\nM16\n".format(xstop=stop_slot_x_formatted,
                                                                                     ystop=stop_slot_y_formatted)
                            elif slot_type == 'drilling':
                                excellon_code += "{xstart}Y{ystart}G85X{xstop}Y{ystop}\nG05\n".format(
                                    xstart=start_slot_x_formatted, ystart=start_slot_y_formatted,
                                    xstop=stop_slot_x_formatted, ystop=stop_slot_y_formatted
                                )
        except Exception as e:
            log.debug(str(e))

        if not has_drills and not has_slots:
            log.debug("FlatCAMObj.ExcellonObject.export_excellon() --> Excellon Object is empty: no drills, no slots.")
            return 'fail'

        return slots_in_file, excellon_code

    def generate_milling_drills(self, tools=None, outname=None, tooldia=None, plot=False, use_thread=False):
        """
        Will generate an Geometry Object allowing to cut a drill hole instead of drilling it.

        Note: This method is a good template for generic operations as
        it takes it's options from parameters or otherwise from the
        object's options and returns a (success, msg) tuple as feedback
        for shell operations.

        :param tools:       A list of tools where the drills are to be milled or a string: "all"
        :type tools:
        :param outname:     the name of the resulting Geometry object
        :type outname:      str
        :param tooldia:     the tool diameter to be used in creation of the milling path (Geometry Object)
        :type tooldia:      float
        :param plot:        if to plot the resulting object
        :type plot:         bool
        :param use_thread:  if to use threading for creation of the Geometry object
        :type use_thread:   bool
        :return:            Success/failure condition tuple (bool, str).
        :rtype:             tuple
        """

        # Get the tools from the list. These are keys
        # to self.tools
        if tools is None:
            tools = self.get_selected_tools_list()

        if outname is None:
            outname = self.options["name"] + "_mill"

        if tooldia is None:
            tooldia = self.ui.tooldia_entry.get_value()

        # Sort tools by diameter. items() -> [('name', diameter), ...]
        # sorted_tools = sorted(list(self.tools.items()), key=lambda tl: tl[1]) # no longer works in Python3

        sort = []
        for k, v in self.tools.items():
            sort.append((k, v['tooldia']))
        sorted_tools = sorted(sort, key=lambda t1: t1[1])

        if tools == "all":
            tools = [i[0] for i in sorted_tools]  # List if ordered tool names.
            log.debug("Tools 'all' and sorted are: %s" % str(tools))

        if len(tools) == 0:
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Please select one or more tools from the list and try again."))
            return False, "Error: No tools."

        for tool in tools:
            if tooldia > self.tools[tool]["tooldia"]:
                mseg = '[ERROR_NOTCL] %s %s: %s' % (_("Milling tool for DRILLS is larger than hole size. Cancelled."),
                                                    _("Tool"),
                                                    str(tool))
                self.app.inform.emit(mseg)
                return False, "Error: Milling tool is larger than hole."

        def geo_init(geo_obj, app_obj):
            """

            :param geo_obj:     New object
            :type geo_obj:      GeometryObject
            :param app_obj:     App
            :type app_obj:      FlatCAMApp.App
            :return:
            :rtype:
            """
            assert geo_obj.kind == 'geometry', "Initializer expected a GeometryObject, got %s" % type(geo_obj)

            # ## Add properties to the object

            # get the tool_table items in a list of row items
            tool_table_items = self.get_selected_tools_table_items()
            # insert an information only element in the front
            tool_table_items.insert(0, [_("Tool_nr"), _("Diameter"), _("Drills_Nr"), _("Slots_Nr")])

            geo_obj.options['Tools_in_use'] = tool_table_items
            geo_obj.options['type'] = 'Excellon Geometry'
            geo_obj.options["cnctooldia"] = str(tooldia)
            geo_obj.options["multidepth"] = self.app.defaults["geometry_multidepth"]
            geo_obj.solid_geometry = []

            # in case that the tool used has the same diameter with the hole, and since the maximum resolution
            # for FlatCAM is 6 decimals,
            # we add a tenth of the minimum value, meaning 0.0000001, which from our point of view is "almost zero"
            for etool in tools:
                for drill in self.tools[etool]['drills']:
                    buffer_value = self.tools[etool]['tooldia'] / 2 - tooldia / 2
                    if buffer_value == 0:
                        geo_obj.solid_geometry.append(drill.buffer(0.0000001).exterior)
                    else:
                        geo_obj.solid_geometry.append(drill.buffer(buffer_value).exterior)

        if use_thread:
            def geo_thread(a_obj):
                a_obj.app_obj.new_object("geometry", outname, geo_init, plot=plot)

            # Create a promise with the new name
            self.app.collection.promise(outname)

            # Send to worker
            self.app.worker_task.emit({'fcn': geo_thread, 'params': [self.app]})
        else:
            self.app.app_obj.new_object("geometry", outname, geo_init, plot=plot)

        return True, ""

    def generate_milling_slots(self, tools=None, outname=None, tooldia=None, plot=False, use_thread=False):
        """
        Will generate an Geometry Object allowing to cut/mill a slot hole.

        Note: This method is a good template for generic operations as
        it takes it's options from parameters or otherwise from the
        object's options and returns a (success, msg) tuple as feedback
        for shell operations.

        :param tools:       A list of tools where the drills are to be milled or a string: "all"
        :type tools:
        :param outname:     the name of the resulting Geometry object
        :type outname:      str
        :param tooldia:     the tool diameter to be used in creation of the milling path (Geometry Object)
        :type tooldia:      float
        :param plot:        if to plot the resulting object
        :type plot:         bool
        :param use_thread:  if to use threading for creation of the Geometry object
        :type use_thread:   bool
        :return:            Success/failure condition tuple (bool, str).
        :rtype:             tuple
        """

        # Get the tools from the list. These are keys
        # to self.tools
        if tools is None:
            tools = self.get_selected_tools_list()

        if outname is None:
            outname = self.options["name"] + "_mill"

        if tooldia is None:
            tooldia = float(self.options["slot_tooldia"])

        # Sort tools by diameter. items() -> [('name', diameter), ...]
        # sorted_tools = sorted(list(self.tools.items()), key=lambda tl: tl[1]) # no longer works in Python3

        sort = []
        for k, v in self.tools.items():
            sort.append((k, v['tooldia']))
        sorted_tools = sorted(sort, key=lambda t1: t1[1])

        if tools == "all":
            tools = [i[0] for i in sorted_tools]  # List if ordered tool names.
            log.debug("Tools 'all' and sorted are: %s" % str(tools))

        if len(tools) == 0:
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Please select one or more tools from the list and try again."))
            return False, "Error: No tools."

        for tool in tools:
            # I add the 0.0001 value to account for the rounding error in converting from IN to MM and reverse
            adj_toolstable_tooldia = float('%.*f' % (self.decimals, float(tooldia)))
            adj_file_tooldia = float('%.*f' % (self.decimals, float(self.tools[tool]["tooldia"])))
            if adj_toolstable_tooldia > adj_file_tooldia + 0.0001:
                self.app.inform.emit('[ERROR_NOTCL] %s' %
                                     _("Milling tool for SLOTS is larger than hole size. Cancelled."))
                return False, "Error: Milling tool is larger than hole."

        def geo_init(geo_obj, app_obj):
            assert geo_obj.kind == 'geometry', "Initializer expected a GeometryObject, got %s" % type(geo_obj)

            # ## Add properties to the object

            # get the tool_table items in a list of row items
            tool_table_items = self.get_selected_tools_table_items()
            # insert an information only element in the front
            tool_table_items.insert(0, [_("Tool_nr"), _("Diameter"), _("Drills_Nr"), _("Slots_Nr")])

            geo_obj.options['Tools_in_use'] = tool_table_items
            geo_obj.options['type'] = 'Excellon Geometry'
            geo_obj.options["cnctooldia"] = str(tooldia)
            geo_obj.options["multidepth"] = self.app.defaults["geometry_multidepth"]
            geo_obj.solid_geometry = []

            # in case that the tool used has the same diameter with the hole, and since the maximum resolution
            # for FlatCAM is 6 decimals,
            # we add a tenth of the minimum value, meaning 0.0000001, which from our point of view is "almost zero"
            for m_tool in tools:
                for slot in self.tools[m_tool]['slots']:
                    toolstable_tool = float('%.*f' % (self.decimals, float(tooldia)))
                    file_tool = float('%.*f' % (self.decimals, float(self.tools[m_tool]["tooldia"])))

                    # I add the 0.0001 value to account for the rounding error in converting from IN to MM and reverse
                    # for the file_tool (tooldia actually)
                    buffer_value = float(file_tool / 2) - float(toolstable_tool / 2) + 0.0001
                    if buffer_value == 0:
                        start = slot[0]
                        stop = slot[1]

                        lines_string = LineString([start, stop])
                        poly = lines_string.buffer(0.0000001, int(self.geo_steps_per_circle)).exterior
                        geo_obj.solid_geometry.append(poly)
                    else:
                        start = slot[0]
                        stop = slot[1]

                        lines_string = LineString([start, stop])
                        poly = lines_string.buffer(buffer_value, int(self.geo_steps_per_circle)).exterior
                        geo_obj.solid_geometry.append(poly)

        if use_thread:
            def geo_thread(a_obj):
                a_obj.app_obj.new_object("geometry", outname + '_slot', geo_init, plot=plot)

            # Create a promise with the new name
            self.app.collection.promise(outname)

            # Send to worker
            self.app.worker_task.emit({'fcn': geo_thread, 'params': [self.app]})
        else:
            self.app.app_obj.new_object("geometry", outname + '_slot', geo_init, plot=plot)

        return True, ""

    def on_generate_milling_button_click(self, *args):
        self.app.defaults.report_usage("excellon_on_create_milling_drills button")
        self.read_form()

        self.generate_milling_drills(use_thread=False, plot=True)

    def on_generate_milling_slots_button_click(self, *args):
        self.app.defaults.report_usage("excellon_on_create_milling_slots_button")
        self.read_form()

        self.generate_milling_slots(use_thread=False, plot=True)

    def convert_units(self, units):
        log.debug("FlatCAMObj.ExcellonObject.convert_units()")

        Excellon.convert_units(self, units)

        # factor = Excellon.convert_units(self, units)
        # self.options['drillz'] = float(self.options['drillz']) * factor
        # self.options['travelz'] = float(self.options['travelz']) * factor
        # self.options['feedrate'] = float(self.options['feedrate']) * factor
        # self.options['feedrate_rapid'] = float(self.options['feedrate_rapid']) * factor
        # self.options['toolchangez'] = float(self.options['toolchangez']) * factor
        #
        # if self.app.defaults["excellon_toolchangexy"] == '':
        #     self.options['toolchangexy'] = "0.0, 0.0"
        # else:
        #     coords_xy = [float(eval(coord)) for coord in self.app.defaults["excellon_toolchangexy"].split(",")]
        #     if len(coords_xy) < 2:
        #         self.app.inform.emit('[ERROR] %s' % _("The Toolchange X,Y field in Edit -> Preferences has to be "
        #                                               "in the format (x, y) \n"
        #                                               "but now there is only one value, not two. "))
        #         return 'fail'
        #     coords_xy[0] *= factor
        #     coords_xy[1] *= factor
        #     self.options['toolchangexy'] = "%f, %f" % (coords_xy[0], coords_xy[1])
        #
        # if self.options['startz'] is not None:
        #     self.options['startz'] = float(self.options['startz']) * factor
        # self.options['endz'] = float(self.options['endz']) * factor

    def on_solid_cb_click(self, *args):
        if self.muted_ui:
            return
        self.read_form_item('solid')
        self.plot()

    def on_multicolored_cb_click(self, val):
        if self.muted_ui:
            return
        self.read_form_item('multicolored')
        self.plot()
        if not val:
            self.build_ui()

    def on_autoload_db_toggled(self, state):
        self.app.defaults["excellon_autoload_db"] = True if state else False

    def on_plot_cb_click(self, val):
        if self.muted_ui:
            return
        # self.plot()
        self.read_form_item('plot')

        self.ui_disconnect()
        cb_flag = self.ui.plot_cb.isChecked()
        for row in range(self.ui.tools_table.rowCount() - 2):
            table_cb = self.ui.tools_table.cellWidget(row, 5)
            if cb_flag:
                table_cb.setChecked(True)
            else:
                table_cb.setChecked(False)
        self.ui_connect()

    def on_plot_cb_click_table(self):
        self.ui_disconnect()
        check_row = 0

        for tool_key in self.tools:
            # find the geo_tool_table row associated with the tool_key
            for row in range(self.ui.tools_table.rowCount()):
                tool_item = int(self.ui.tools_table.item(row, 0).text())
                if tool_item == int(tool_key):
                    check_row = row
                    break
            state = self.ui.tools_table.cellWidget(check_row, 5).isChecked()
            self.shapes.update_visibility(state, indexes=self.shape_indexes_dict[tool_key])
        self.shapes.redraw()
        self.ui_connect()

    def plot(self, visible=None, kind=None):

        multicolored = self.ui.multicolored_cb.get_value()

        # Does all the required setup and returns False
        # if the 'ptint' option is set to False.
        if not FlatCAMObj.plot(self):
            return

        if self.app.is_legacy is False:
            def random_color():
                r_color = np.random.rand(4)
                r_color[3] = 1
                return r_color
        else:
            def random_color():
                while True:
                    r_color = np.random.rand(4)
                    r_color[3] = 1

                    new_color = '#'
                    for idx_c in range(len(r_color)):
                        new_color += '%x' % int(r_color[idx_c] * 255)
                    # do it until a valid color is generated
                    # a valid color has the # symbol, another 6 chars for the color and the last 2 chars for alpha
                    # for a total of 9 chars
                    if len(new_color) == 9:
                        break
                return new_color

        # this stays for compatibility reasons, in case we try to open old projects
        try:
            __ = iter(self.solid_geometry)
        except TypeError:
            self.solid_geometry = [self.solid_geometry]

        visible = visible if visible else self.ui.plot_cb.get_value()

        try:
            # Plot Excellon (All polygons?)
            if self.ui.solid_cb.get_value():
                # plot polygons for each tool separately
                for tool in self.tools:
                    # set the color here so we have one color for each tool
                    geo_color = random_color()
                    if multicolored:
                        self.tools[tool]['multicolor'] = geo_color
                    else:
                        self.tools[tool]['multicolor'] = None

                    # tool is a dict also
                    for geo in self.tools[tool]["solid_geometry"]:
                        idx = self.add_shape(shape=geo,
                                             color=geo_color if multicolored else self.outline_color,
                                             face_color=geo_color if multicolored else self.fill_color,
                                             visible=visible,
                                             layer=2)
                        try:
                            self.shape_indexes_dict[tool].append(idx)
                        except KeyError:
                            self.shape_indexes_dict[tool] = [idx]
            else:
                for tool in self.tools:
                    for geo in self.tools[tool]['solid_geometry']:
                        idx = self.add_shape(shape=geo.exterior, color='red', visible=visible)
                        try:
                            self.shape_indexes_dict[tool].append(idx)
                        except KeyError:
                            self.shape_indexes_dict[tool] = [idx]
                        for ints in geo.interiors:
                            idx = self.add_shape(shape=ints, color='orange', visible=visible)
                            try:
                                self.shape_indexes_dict[tool].append(idx)
                            except KeyError:
                                self.shape_indexes_dict[tool] = [idx]
                # for geo in self.solid_geometry:
                #     self.add_shape(shape=geo.exterior, color='red', visible=visible)
                #     for ints in geo.interiors:
                #         self.add_shape(shape=ints, color='orange', visible=visible)

            self.shapes.redraw()
        except (ObjectDeleted, AttributeError) as e:
            log.debug("ExcellonObject.plot() -> %s" % str(e))
            self.shapes.clear(update=True)

        if multicolored:
            self.multicolored_build_sig.emit()

    def on_multicolored_build(self):
        self.build_ui()

    @staticmethod
    def merge(exc_list, exc_final, decimals=None, fuse_tools=True):
        """
        Merge Excellon objects found in exc_list parameter into exc_final object.
        Options are always copied from source .

        Tools are disregarded, what is taken in consideration is the unique drill diameters found as values in the
        exc_list tools dict's. In the reconstruction section for each unique tool diameter it will be created a
        tool_name to be used in the final Excellon object, exc_final.

        If only one object is in exc_list parameter then this function will copy that object in the exc_final

        :param exc_list:    List or one object of ExcellonObject Objects to join.
        :type exc_list:     list
        :param exc_final:   Destination ExcellonObject object.
        :type exc_final:    class
        :param decimals:    The number of decimals to be used for diameters
        :type decimals:     int
        :param fuse_tools:  If True will try to fuse tools of the same diameter for the Excellon objects
        :type fuse_tools:   bool
        :return:            None
        """

        if exc_final.tools is None:
            exc_final.tools = {}

        if decimals is None:
            decimals = 4
        decimals_exc = decimals

        try:
            flattened_list = list(itertools.chain(*exc_list))
        except TypeError:
            flattened_list = exc_list

        new_tools = {}
        total_geo = []
        toolid = 0
        for exc in flattened_list:
            # copy options of the current excellon obj to the final excellon obj
            # only the last object options will survive
            for option in exc.options:
                if option != 'name':
                    try:
                        exc_final.options[option] = deepcopy(exc.options[option])
                    except Exception:
                        exc.app.log.warning("Failed to copy option.", option)

            for tool in exc.tools:
                toolid += 1
                new_tools[toolid] = deepcopy(exc.tools[tool])

            exc_final.tools = deepcopy(new_tools)
            # add the zeros and units to the exc_final object
            exc_final.zeros = deepcopy(exc.zeros)
            exc_final.units = deepcopy(exc.units)
            total_geo += exc.solid_geometry

        exc_final.solid_geometry = deepcopy(total_geo)

        fused_tools_dict = {}
        if exc_final.tools and fuse_tools:
            toolid = 0
            for tool, tool_dict in exc_final.tools.items():
                current_tooldia = float('%.*f' % (decimals_exc, tool_dict['tooldia']))
                toolid += 1

                # calculate all diameters in fused_tools_dict
                all_dia = []
                if fused_tools_dict:
                    for f_tool in fused_tools_dict:
                        all_dia.append(float('%.*f' % (decimals_exc, fused_tools_dict[f_tool]['tooldia'])))

                if current_tooldia in all_dia:
                    # find tool for current_tooldia in fuse_tools
                    t = None
                    for f_tool in fused_tools_dict:
                        if fused_tools_dict[f_tool]['tooldia'] == current_tooldia:
                            t = f_tool
                            break
                    if t:
                        fused_tools_dict[t]['drills'] += tool_dict['drills']
                        fused_tools_dict[t]['slots'] += tool_dict['slots']
                        fused_tools_dict[t]['solid_geometry'] += tool_dict['solid_geometry']
                else:
                    fused_tools_dict[toolid] = tool_dict
                    fused_tools_dict[toolid]['tooldia'] = current_tooldia

            exc_final.tools = fused_tools_dict

        # create the geometry for the exc_final object
        exc_final.create_geometry()
