# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt6 import QtGui, QtCore, QtWidgets

from appTool import AppTool
from appCommon.Common import LoudDict
from appGUI.GUIElements import FCComboBox, FCEntry, FCTable, FCDoubleSpinner, FCSpinner, FCFileSaveDialog, \
    FCInputSpinner, FCButton, VerticalScrollArea

from camlib import distance
from appEditors.AppTextEditor import AppTextEditor

from copy import deepcopy
from datetime import datetime
import re

from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union

import traceback
from io import StringIO

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class SolderPaste(AppTool):
    
    def __init__(self, app):
        AppTool.__init__(self, app)
        self.app = app
        
        # Number of decimals to be used for tools/nozzles in this FlatCAM Tool
        self.decimals = self.app.decimals

        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = SolderUI(layout=self.layout, app=self.app, solder_class=self)
        self.pluginName = self.ui.pluginName
        self.connect_signals_at_init()

        self.tooltable_tools = {}
        self.tooluid = 0

        self.options = LoudDict()
        self.form_fields = {}

        self.units = ''
        self.name = ""

        self.obj = None
        self.text_editor_tab = None

        # this will be used in the combobox context menu, for delete entry
        self.obj_to_be_deleted_name = ''

        # stpre here the flattened geometry
        self.flat_geometry = []

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolSolderPaste()")

        if toggle:
            # if the splitter is hidden, display it
            if self.app.ui.splitter.sizes()[0] == 0:
                self.app.ui.splitter.setSizes([1, 1])

            # if the Tool Tab is hidden display it, else hide it but only if the objectName is the same
            found_idx = None
            for idx in range(self.app.ui.notebook.count()):
                if self.app.ui.notebook.widget(idx).objectName() == "plugin_tab":
                    found_idx = idx
                    break
            # show the Tab
            if not found_idx:
                try:
                    self.app.ui.notebook.addTab(self.app.ui.plugin_tab, _("Plugin"))
                except RuntimeError:
                    self.app.ui.plugin_tab = QtWidgets.QWidget()
                    self.app.ui.plugin_tab.setObjectName("plugin_tab")
                    self.app.ui.plugin_tab_layout = QtWidgets.QVBoxLayout(self.app.ui.plugin_tab)
                    self.app.ui.plugin_tab_layout.setContentsMargins(2, 2, 2, 2)

                    self.app.ui.plugin_scroll_area = VerticalScrollArea()
                    self.app.ui.plugin_tab_layout.addWidget(self.app.ui.plugin_scroll_area)
                    self.app.ui.notebook.addTab(self.app.ui.plugin_tab, _("Plugin"))
                # focus on Tool Tab
                self.app.ui.notebook.setCurrentWidget(self.app.ui.plugin_tab)

            try:
                if self.app.ui.plugin_scroll_area.widget().objectName() == self.pluginName and found_idx:
                    # if the Tool Tab is not focused, focus on it
                    if not self.app.ui.notebook.currentWidget() is self.app.ui.plugin_tab:
                        # focus on Tool Tab
                        self.app.ui.notebook.setCurrentWidget(self.app.ui.plugin_tab)
                    else:
                        # else remove the Tool Tab
                        self.app.ui.notebook.setCurrentWidget(self.app.ui.properties_tab)
                        self.app.ui.notebook.removeTab(2)

                        # if there are no objects loaded in the app then hide the Notebook widget
                        if not self.app.collection.get_list():
                            self.app.ui.splitter.setSizes([0, 1])
            except AttributeError:
                pass
        else:
            if self.app.ui.splitter.sizes()[0] == 0:
                self.app.ui.splitter.setSizes([1, 1])

        AppTool.run(self)
        self.set_tool_ui()
        self.build_ui()

        self.app.ui.notebook.setTabText(2, _("SP Dispenser"))

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Alt+K', **kwargs)

    def clear_context_menu(self):
        self.ui.tools_table.removeContextMenu()

    def init_context_menu(self):
        self.ui.tools_table.setupContextMenu()
        self.ui.tools_table.addContextMenu(
            _("Add"), lambda: self.on_tool_add(dia=None, muted=None),
            icon=QtGui.QIcon(self.app.resource_location + "/plus16.png"))
        self.ui.tools_table.addContextMenu(
            _("Delete"), lambda:
            self.on_tool_delete(rows_to_delete=None, all_tools=None),
            icon=QtGui.QIcon(self.app.resource_location + "/delete32.png")
        )

    def connect_signals_at_init(self):
        self.ui.combo_context_del_action.triggered.connect(self.on_delete_object)

        self.ui.addtool_btn.clicked.connect(self.on_tool_add)
        self.ui.addtool_entry.returnPressed.connect(self.on_tool_add)
        self.ui.deltool_btn.clicked.connect(self.on_tool_delete)
        self.ui.soldergeo_btn.clicked.connect(self.on_create_geo_click)
        self.ui.solder_gcode_btn.clicked.connect(self.on_create_gcode_click)
        self.ui.solder_gcode_view_btn.clicked.connect(self.on_view_gcode)
        self.ui.solder_gcode_save_btn.clicked.connect(self.on_save_gcode)

        self.ui.geo_obj_combo.currentIndexChanged.connect(self.on_geo_select)
        self.ui.cnc_obj_combo.currentIndexChanged.connect(self.on_cncjob_select)

        self.app.object_status_changed.connect(self.update_comboboxes)
        self.ui.reset_button.clicked.connect(self.set_tool_ui)

    def set_tool_ui(self):
        self.clear_ui(self.layout)
        self.ui = SolderUI(layout=self.layout, app=self.app, solder_class=self)
        self.pluginName = self.ui.pluginName
        self.connect_signals_at_init()

        self.form_fields.update({
            "tools_solderpaste_new":            self.ui.addtool_entry,
            "tools_solderpaste_z_start":        self.ui.z_start_entry,
            "tools_solderpaste_z_dispense":     self.ui.z_dispense_entry,
            "tools_solderpaste_z_stop":         self.ui.z_stop_entry,
            "tools_solderpaste_z_travel":       self.ui.z_travel_entry,
            "tools_solderpaste_z_toolchange":   self.ui.z_toolchange_entry,
            "tools_solderpaste_xy_toolchange":  self.ui.xy_toolchange_entry,
            "tools_solderpaste_frxy":           self.ui.frxy_entry,
            "tools_solderpaste_frz":            self.ui.frz_entry,
            "tools_solderpaste_frz_dispense":   self.ui.frz_dispense_entry,
            "tools_solderpaste_speedfwd":       self.ui.speedfwd_entry,
            "tools_solderpaste_dwellfwd":       self.ui.dwellfwd_entry,
            "tools_solderpaste_speedrev":       self.ui.speedrev_entry,
            "tools_solderpaste_dwellrev":       self.ui.dwellrev_entry,
            "tools_solderpaste_pp":             self.ui.pp_combo
        })
        self.set_form_from_defaults()

        for option in self.app.options:
            if option.find('tools_') == 0:
                self.options[option] = deepcopy(self.app.options[option] )
        self.read_form_to_options()

        self.clear_context_menu()
        self.init_context_menu()

        # either originally it was a string or not, xy_end will be made string
        dias_option = self.app.defaults["tools_solderpaste_tools"]
        dias_option = re.sub('[()\[\]]', '', str(dias_option)) if dias_option else None
        try:
            dias = [float(eval(dia)) for dia in dias_option.split(",") if dia != '']
        except Exception as err:
            self.app.log.error("SolderPaste.set_tool_ui() -> nozzle dias -> %s" % str(err))
            self.app.log.error("At least one Nozzle tool diameter needed. "
                               "Verify in Edit -> Preferences -> Plugins -> Solder Paste Tools.")
            return

        self.tooluid = 0

        self.tooltable_tools.clear()
        for tool_dia in dias:
            self.tooluid += 1
            self.tooltable_tools.update({
                int(self.tooluid): {
                    'tooldia': float('%.*f' % (self.decimals, tool_dia)),
                    'data': deepcopy(self.options),
                    'solid_geometry': []
                }
            })

        self.name = ""
        self.obj = None

        self.units = self.app.defaults['units'].upper()

        for name in self.app.preprocessors.keys():
            # populate only with preprocessor files that start with 'Paste_'
            if name.partition('_')[0].lower() != 'paste':
                continue
            self.ui.pp_combo.addItem(name)

        self.reset_fields()

        # SELECT THE CURRENT OBJECT
        obj = self.app.collection.get_active()
        if obj and obj.kind == 'gerber':
            obj_name = obj.options['name']
            self.ui.obj_combo.set_value(obj_name)

    def build_ui(self):
        """
        Will rebuild the UI populating it (tools table)
        :return:
        """
        self.ui_disconnect()

        # updated units
        self.units = self.app.defaults['units'].upper()

        sorted_tools = []
        for k, v in self.tooltable_tools.items():
            sorted_tools.append(float('%.*f' % (self.decimals, float(v['tooldia']))))
        sorted_tools.sort(reverse=True)

        n = len(sorted_tools)
        self.ui.tools_table.setRowCount(n)
        tool_id = 0

        for tool_sorted in sorted_tools:
            for tooluid_key, tooluid_value in self.tooltable_tools.items():
                if float('%.*f' % (self.decimals, tooluid_value['tooldia'])) == tool_sorted:
                    tool_id += 1

                    # Tool name/id
                    id_item = QtWidgets.QTableWidgetItem('%d' % int(tool_id))
                    id_item.setFlags(QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)
                    row_no = tool_id - 1
                    self.ui.tools_table.setItem(row_no, 0, id_item)

                    # Diameter
                    dia = QtWidgets.QTableWidgetItem('%.*f' % (self.decimals, tooluid_value['tooldia']))
                    dia.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
                    self.ui.tools_table.setItem(row_no, 1, dia)

                    # Tool unique ID
                    tool_uid_item = QtWidgets.QTableWidgetItem(str(int(tooluid_key)))
                    self.ui.tools_table.setItem(row_no, 2, tool_uid_item)

        # make the diameter column editable
        for row in range(tool_id):
            self.ui.tools_table.item(row, 1).setFlags(
                QtCore.Qt.ItemFlag.ItemIsEditable | QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)

        # all the tools are selected by default
        self.ui.tools_table.selectColumn(0)
        #
        self.ui.tools_table.resizeColumnsToContents()
        self.ui.tools_table.resizeRowsToContents()

        vertical_header = self.ui.tools_table.verticalHeader()
        vertical_header.hide()
        self.ui.tools_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        horizontal_header = self.ui.tools_table.horizontalHeader()
        horizontal_header.setMinimumSectionSize(10)
        horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Fixed)
        horizontal_header.resizeSection(0, 20)
        horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)

        # self.ui.tools_table.setSortingEnabled(True)
        # sort by tool diameter
        # self.ui.tools_table.sortItems(1)

        self.ui.tools_table.setMinimumHeight(self.ui.tools_table.getHeight())
        self.ui.tools_table.setMaximumHeight(self.ui.tools_table.getHeight())

        self.ui_connect()

    def update_ui(self, row=None):
        """
        Will update the UI form with the data from obj.tools
        :param row: the row (tool) from which to extract information's used to populate the form
        :return:
        """
        self.ui_disconnect()

        if row is None:
            try:
                current_row = self.ui.tools_table.currentRow()
            except Exception:
                current_row = 0
        else:
            current_row = row

        if current_row < 0:
            current_row = 0

        # populate the form with the data from the tool associated with the row parameter
        try:
            tooluid = int(self.ui.tools_table.item(current_row, 2).text())
        except Exception as e:
            self.app.log.error("Tool missing. Add a tool in Tool Table. %s" % str(e))
            return

        # update the form
        try:
            # set the form with data from the newly selected tool
            for tooluid_key, tooluid_value in self.tooltable_tools.items():
                if int(tooluid_key) == tooluid:
                    self.set_form(deepcopy(tooluid_value['data']))
        except Exception as e:
            self.app.log.error("ToolSolderPaste ---> update_ui() " + str(e))

        self.ui_connect()

    def on_add_tool_by_key(self):
        tool_add_popup = FCInputSpinner(title='%s...' % _("New Tool"),
                                        text='%s:' % _('Enter a Tool Diameter'),
                                        min=0.0000, max=100.0000, decimals=self.decimals, step=0.1)
        tool_add_popup.setWindowIcon(QtGui.QIcon(self.app.resource_location + '/letter_t_32.png'))

        val, ok = tool_add_popup.get_value()
        if ok:
            if float(val) == 0:
                self.app.inform.emit('[WARNING_NOTCL] %s' %
                                     _("Please enter a tool diameter with non-zero value, in Float format."))
                return
            self.on_tool_add(dia=float(val))
        else:
            self.app.inform.emit('[WARNING_NOTCL] %s...' % _("Adding Tool cancelled"))

    def on_row_selection_change(self):
        sel_model = self.ui.tools_table.selectionModel()
        sel_indexes = sel_model.selectedIndexes()

        # it will iterate over all indexes which means all items in all columns too but I'm interested only on rows
        sel_rows = set()
        for idx in sel_indexes:
            sel_rows.add(idx.row())

        # update UI only if only one row is selected otherwise having multiple rows selected will deform information
        # for the rows other that the current one (first selected)
        if len(sel_rows) == 1:
            self.update_ui()

    def ui_connect(self):
        # on any change to the widgets that matter it will be called self.gui_form_to_storage which will save the
        # changes in geometry UI
        for i in range(self.ui.param_grid.count()):
            if isinstance(self.ui.param_grid.itemAt(i).widget(), FCComboBox):
                self.ui.param_grid.itemAt(i).widget().currentIndexChanged.connect(self.form_to_storage)
            if isinstance(self.ui.param_grid.itemAt(i).widget(), FCEntry):
                self.ui.param_grid.itemAt(i).widget().editingFinished.connect(self.form_to_storage)

        self.ui.tools_table.itemChanged.connect(self.on_tool_edit)
        self.ui.tools_table.currentItemChanged.connect(self.on_row_selection_change)

    def ui_disconnect(self):
        # if connected, disconnect the signal from the slot on item_changed as it creates issues

        for i in range(self.ui.param_grid.count()):
            if isinstance(self.ui.param_grid.itemAt(i).widget(), FCComboBox):
                try:
                    self.ui.param_grid.itemAt(i).widget().currentIndexChanged.disconnect()
                except (TypeError, AttributeError):
                    pass
            if isinstance(self.ui.param_grid.itemAt(i).widget(), FCEntry):
                try:
                    self.ui.param_grid.itemAt(i).widget().editingFinished.disconnect()
                except (TypeError, AttributeError):
                    pass

        try:
            self.ui.tools_table.itemChanged.disconnect(self.on_tool_edit)
        except (TypeError, AttributeError):
            pass

        try:
            self.ui.tools_table.currentItemChanged.disconnect(self.on_row_selection_change)
        except (TypeError, AttributeError):
            pass

    def update_comboboxes(self, obj, status):
        """
        Modify the current text of the comboboxes to show the last object
        that was created.

        :param obj: object that was changed and called this PyQt slot
        :param status: what kind of change happened: 'append' or 'delete'
        :return:
        """
        try:
            obj_name = obj.options['name']
        except AttributeError:
            # this happen when the 'delete all' is emitted since in that case the obj is set to None and None has no
            # attribute named 'options'
            return

        if status == 'append':
            idx = self.ui.obj_combo.findText(obj_name)
            if idx != -1:
                self.ui.obj_combo.setCurrentIndex(idx)

            idx = self.ui.geo_obj_combo.findText(obj_name)
            if idx != -1:
                self.ui.geo_obj_combo.setCurrentIndex(idx)

            idx = self.ui.cnc_obj_combo.findText(obj_name)
            if idx != -1:
                self.ui.cnc_obj_combo.setCurrentIndex(idx)

    def read_form_to_options(self):
        """
        Will read all the parameters from Solder Paste Tool UI and update the self.options dictionary
        :return:
        """

        for key in self.form_fields:
            self.options[key] = self.form_fields[key].get_value()

    def form_to_storage(self, tooluid=None):
        """
        Will read all the items in the UI form and set the self.tools data accordingly
        :param tooluid: the uid of the tool to be updated in the obj.tools
        :return:
        """
        current_row = self.ui.tools_table.currentRow()
        uid = tooluid if tooluid else int(self.ui.tools_table.item(current_row, 2).text())
        for key in self.form_fields:
            self.tooltable_tools[uid]['data'].update({
                key: self.form_fields[key].get_value()
            })

    def set_form_from_defaults(self):
        """
        Will read all the parameters of Solder Paste Tool from the app self.defaults and update the UI
        :return:
        """
        for key in self.form_fields:
            if key in self.app.defaults:
                self.form_fields[key].set_value(self.app.defaults[key])

    def set_form(self, val):
        """
        Will read all the parameters of Solder Paste Tool from the provided val parameter and update the UI
        :param val: dictionary with values to store in the form
        param_type: dictionary
        :return:
        """

        if not isinstance(val, dict):
            self.app.log.debug("ToolSoderPaste.set_form() --> parameter not a dict")
            return

        for key in self.form_fields:
            if key in val:
                self.form_fields[key].set_value(val[key])

    def on_tool_add(self, dia=None, muted=None):
        """
        Add a Tool in the Tool Table

        :param dia: diameter of the tool to be added
        :param muted: if True will not send status bar messages about adding tools
        :return:
        """
        self.ui_disconnect()

        if dia:
            tool_dia = dia
        else:
            try:
                tool_dia = float(self.ui.addtool_entry.get_value())
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    tool_dia = float(self.ui.addtool_entry.get_value().replace(',', '.'))
                except ValueError:
                    self.app.inform.emit('[ERROR_NOTCL] %s' %
                                         _("Wrong value format entered, use a number."))
                    return
            if tool_dia is None:
                self.build_ui()
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("Please enter a tool diameter to add, in Float format."))
                return

        if tool_dia == 0:
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("Please enter a tool diameter with non-zero value, in Float format."))
            return

        # construct a list of all 'tooluid' in the self.tooltable_tools
        tool_uid_list = []
        for tooluid_key in self.tooltable_tools:
            tool_uid_item = int(tooluid_key)
            tool_uid_list.append(tool_uid_item)

        # find maximum from the temp_uid, add 1 and this is the new 'tooluid'
        if not tool_uid_list:
            max_uid = 0
        else:
            max_uid = max(tool_uid_list)
        self.tooluid = int(max_uid + 1)

        tool_dias = []
        for k, v in self.tooltable_tools.items():
            for tool_v in v.keys():
                if tool_v == 'tooldia':
                    tool_dias.append(float('%.*f' % (self.decimals, v[tool_v])))

        # if float('%.*f' % (self.decimals, tool_dia)) in tool_dias:
        if self.app.dec_format(tool_dia, self.decimals) in tool_dias:
            if muted is None:
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled. Tool already in Tool Table."))
            self.ui.tools_table.itemChanged.connect(self.on_tool_edit)
            return
        else:
            if muted is None:
                self.app.inform.emit('[success] %s' % _("New Nozzle tool added to Tool Table."))
            self.tooltable_tools.update({
                int(self.tooluid): {
                    'tooldia':          float('%.*f' % (self.decimals, tool_dia)),
                    'data':             deepcopy(self.options),
                    'solid_geometry':   []
                }
            })

        self.build_ui()

    def on_tool_edit(self):
        """
        Edit a tool in the Tool Table
        :return:
        """
        self.ui_disconnect()

        tool_dias = []
        for k, v in self.tooltable_tools.items():
            for tool_v in v.keys():
                if tool_v == 'tooldia':
                    tool_dias.append(float('%.*f' % (self.decimals, v[tool_v])))

        for row in range(self.ui.tools_table.rowCount()):

            try:
                new_tool_dia = float(self.ui.tools_table.item(row, 1).text())
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    new_tool_dia = float(self.ui.tools_table.item(row, 1).text().replace(',', '.'))
                except ValueError:
                    self.app.inform.emit('[ERROR_NOTCL] %s' %
                                         _("Wrong value format entered, use a number."))
                    return

            tooluid = int(self.ui.tools_table.item(row, 2).text())

            # identify the tool that was edited and get it's tooluid
            if new_tool_dia not in tool_dias:
                self.tooltable_tools[tooluid]['tooldia'] = new_tool_dia
                self.app.inform.emit('[success] %s' % _("Nozzle tool from Tool Table was edited."))
                self.build_ui()
                return
            else:
                old_tool_dia = ''
                # identify the old tool_dia and restore the text in tool table
                for k, v in self.tooltable_tools.items():
                    if k == tooluid:
                        old_tool_dia = v['tooldia']
                        break
                restore_dia_item = self.ui.tools_table.item(row, 1)
                restore_dia_item.setText(str(old_tool_dia))
                self.app.inform.emit('[WARNING_NOTCL] %s' %
                                     _("Cancelled. New diameter value is already in the Tool Table."))
        self.build_ui()

    def on_tool_delete(self, rows_to_delete=None, all_tools=None):
        """
        Will delete tool(s) in the Tool Table

        :param rows_to_delete:  tell which row (tool) to delete
        :param all_tools:       to delete all tools at once
        :return:
        """
        self.ui_disconnect()

        deleted_tools_list = []
        if all_tools:
            self.tooltable_tools.clear()
            self.build_ui()
            return

        if rows_to_delete:
            try:
                for row in rows_to_delete:
                    tooluid_del = int(self.ui.tools_table.item(row, 2).text())
                    deleted_tools_list.append(tooluid_del)
            except TypeError:
                deleted_tools_list.append(rows_to_delete)

            for t in deleted_tools_list:
                self.tooltable_tools.pop(t, None)
            self.build_ui()
            return

        try:
            if self.ui.tools_table.selectedItems():
                for row_sel in self.ui.tools_table.selectedItems():
                    row = row_sel.row()
                    if row < 0:
                        continue
                    tooluid_del = int(self.ui.tools_table.item(row, 2).text())
                    deleted_tools_list.append(tooluid_del)

                for t in deleted_tools_list:
                    self.tooltable_tools.pop(t, None)

        except AttributeError:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Delete failed. Select a tool to delete."))
            return
        except Exception as e:
            self.app.log.error(str(e))

        self.app.inform.emit('[success] %s' % _("Tools deleted from Tool Table."))
        self.build_ui()

    def on_rmb_combo(self, pos, combo):
        """
        Will create a context menu on the combobox items
        :param pos: mouse click position passed by the signal that called this slot
        :param combo: the actual combo from where the signal was triggered
        :return:
        """
        view = combo.view
        idx = view.indexAt(pos)
        if not idx.isValid():
            return

        self.obj_to_be_deleted_name = combo.model().itemData(idx)[0]

        menu = QtWidgets.QMenu()
        menu.addAction(self.ui.combo_context_del_action)
        menu.exec(view.mapToGlobal(pos))

    def on_delete_object(self):
        """
        Slot for the 'delete' action triggered in the combobox context menu.
        The name of the object to be deleted is collected when the combobox context menu is created.
        :return:
        """
        if self.obj_to_be_deleted_name != '':
            self.app.collection.set_active(self.obj_to_be_deleted_name)
            self.app.collection.delete_active(select_project=False)
            self.obj_to_be_deleted_name = ''

    def on_geo_select(self):
        # if self.geo_obj_combo.currentText().rpartition('_')[2] == 'solderpaste':
        #     self.gcode_frame.setDisabled(False)
        # else:
        #     self.gcode_frame.setDisabled(True)
        pass

    def on_cncjob_select(self):
        # if self.cnc_obj_combo.currentText().rpartition('_')[2] == 'solderpaste':
        #     self.save_gcode_frame.setDisabled(False)
        # else:
        #     self.save_gcode_frame.setDisabled(True)
        pass

    def on_create_geo_click(self):
        """
        Will create a solderpaste dispensing geometry.

        :return:
        """
        name = self.ui.obj_combo.currentText()
        if name == '':
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("No SolderPaste mask Gerber object loaded."))
            return

        obj = self.app.collection.get_by_name(name)
        # update the self.options
        self.read_form_to_options()

        self.on_create_geo(name=name, work_object=obj)

    def on_create_geo(self, name, work_object, use_thread=True):
        """
        The actual work for creating solderpaste dispensing geometry is done here.

        :param name: the outname for the resulting geometry object
        :param work_object: the source Gerber object from which the geometry is created
        :param use_thread: use thread, True or False
        :return: a Geometry type object
        """
        proc = self.app.proc_container.new('%s...' % _("Working"))
        obj = work_object

        # Sort tools in descending order
        sorted_tools = []
        for k, v in self.tooltable_tools.items():
            # make sure that the tools diameter is more than zero and not zero
            if float(v['tooldia']) > 0:
                sorted_tools.append(float('%.*f' % (self.decimals, float(v['tooldia']))))
        sorted_tools.sort(reverse=True)

        if not sorted_tools:
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("No Nozzle tools in the tool table."))
            return 'fail'

        def flatten(geometry=None, reset=True, pathonly=False):
            """
            Creates a list of non-iterable linear geometry objects.
            Polygons are expanded into its exterior pathonly param if specified.

            Results are placed in flat_geometry

            :param geometry: Shapely type or list or list of list of such.
            :param reset: Clears the contents of self.flat_geometry.
            :param pathonly: Expands polygons into linear elements from the exterior attribute.
            """

            if reset:
                self.flat_geometry = []
            # ## If iterable, expand recursively.
            try:
                for geo in geometry:
                    if geo is not None:
                        flatten(geometry=geo,
                                reset=False,
                                pathonly=pathonly)

            # ## Not iterable, do the actual indexing and add.
            except TypeError:
                if pathonly and type(geometry) == Polygon:
                    self.flat_geometry.append(geometry.exterior)
                else:
                    self.flat_geometry.append(geometry)
            return self.flat_geometry

        # TODO when/if the Gerber files will have solid_geometry in the self.tools I will have to take care here

        flatten(geometry=obj.solid_geometry, pathonly=True)

        def geo_init(geo_obj, app_obj):
            geo_obj.options.update(self.options)
            geo_obj.solid_geometry = []

            geo_obj.tools = {}
            geo_obj.multigeo = True
            geo_obj.multitool = True
            geo_obj.special_group = 'solder_paste_tool'

            geo = LineString()
            work_geo = self.flat_geometry
            rest_geo = []
            tooluid = 1

            for tool in sorted_tools:
                offset = tool / 2
                for uid, vl in self.tooltable_tools.items():
                    if float('%.*f' % (self.decimals, float(vl['tooldia']))) == tool:
                        tooluid = int(uid)
                        break

                geo_obj.tools[tooluid] = {}
                geo_obj.tools[tooluid]['tooldia'] = tool
                geo_obj.tools[tooluid]['data'] = deepcopy(self.tooltable_tools[tooluid]['data'])
                geo_obj.tools[tooluid]['solid_geometry'] = []
                geo_obj.tools[tooluid]['type'] = 'SolderPaste'

                geo_obj.tools[tooluid]['data']['tools_mill_offset_type']= 0  # 'Path'
                geo_obj.tools[tooluid]['data']['tools_mill_offset_value'] = 0.0
                geo_obj.tools[tooluid]['data']['tools_mill_job_type'] = 'SP'  #'
                geo_obj.tools[tooluid]['data']['tools_mill_tool_shape'] = 'DN'  # 'DN'

                # self.flat_geometry is a list of LinearRings produced by flatten() from the exteriors of the Polygons
                # We get possible issues if we try to directly use the Polygons, due of possible the interiors,
                # so we do a hack: get first the exterior in a form of LinearRings and then convert back to Polygon
                # because intersection does not work on LinearRings
                for g in work_geo:
                    # for whatever reason intersection on LinearRings does not work so we convert back to Polygons
                    poly = Polygon(g)
                    x_min, y_min, x_max, y_max = poly.bounds

                    diag_1_intersect = LineString([(x_min, y_min), (x_max, y_max)]).intersection(poly)
                    diag_2_intersect = LineString([(x_min, y_max), (x_max, y_min)]).intersection(poly)

                    if self.units == 'MM':
                        round_diag_1 = round(diag_1_intersect.length, 1)
                        round_diag_2 = round(diag_2_intersect.length, 1)
                    else:
                        round_diag_1 = round(diag_1_intersect.length, 2)
                        round_diag_2 = round(diag_2_intersect.length, 2)

                    if round_diag_1 == round_diag_2:
                        length = distance((x_min, y_min), (x_max, y_min))
                        h = distance((x_min, y_min), (x_min, y_max))

                        if offset >= length / 2 or offset >= h / 2:
                            pass
                        else:
                            if length > h:
                                h_half = h / 2
                                start = [x_min, (y_min + h_half)]
                                stop = [(x_min + length), (y_min + h_half)]
                                geo = LineString([start, stop])
                            else:
                                l_half = length / 2
                                start = [(x_min + l_half), y_min]
                                stop = [(x_min + l_half), (y_min + h)]
                                geo = LineString([start, stop])
                    elif round_diag_1 > round_diag_2:
                        geo = diag_1_intersect
                    else:
                        geo = diag_2_intersect

                    offseted_poly = poly.buffer(-offset)
                    geo = geo.intersection(offseted_poly)
                    if not geo.is_empty:
                        try:
                            geo_obj.tools[tooluid]['solid_geometry'].append(geo)
                        except Exception as e:
                            self.app.log.error('ToolSolderPaste.on_create_geo() --> %s' % str(e))
                    else:
                        rest_geo.append(g)

                work_geo = deepcopy(rest_geo)
                rest_geo[:] = []

                if not work_geo:
                    a = 0
                    for tooluid_key in geo_obj.tools:
                        if not geo_obj.tools[tooluid_key]['solid_geometry']:
                            a += 1
                    if a == len(geo_obj.tools):
                        msg = '[ERROR_NOTCL] %s' % '%s ...' % _('Cancelled. Empty file, it has no geometry')
                        self.app.inform.emit(msg)
                        return 'fail'

                    app_obj.inform.emit('[success] %s...' % _("Solder Paste geometry generated successfully"))
                    return

            # if we still have geometry not processed at the end of the tools then we failed
            # some or all the pads are not covered with solder paste
            if work_geo:
                app_obj.inform.emit('[WARNING_NOTCL] %s' %
                                    _("Some or all pads have no solder "
                                      "due of inadequate nozzle diameters..."))
                return 'fail'

        if use_thread:
            def job_thread(app_obj):
                try:
                    app_obj.app_obj.new_object("geometry", name + "_solderpaste", geo_init)
                except Exception as e:
                    self.app.log.error("SolderPaste.on_create_geo() --> %s" % str(e))
                    proc.done()
                    return
                proc.done()

            self.app.inform.emit(_("Generating Solder Paste dispensing geometry..."))
            # Promise object with the new name
            self.app.collection.promise(name)

            # Background
            self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})
        else:
            self.app.app_obj.new_object("geometry", name + "_solderpaste", geo_init)

    def on_create_gcode_click(self):
        """
        Will create a CNCJob object from the solderpaste dispensing geometry.

        :return:
        """
        name = self.ui.geo_obj_combo.currentText()
        obj = self.app.collection.get_by_name(name)

        if name == '':
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Geometry object available."))
            return

        if obj.special_group != 'solder_paste_tool':
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("This Geometry can't be processed. "
                                   "NOT a solder_paste_tool geometry."))
            return

        a = 0
        for tooluid_key in obj.tools:
            if obj.tools[tooluid_key]['solid_geometry'] is None:
                a += 1
        if a == len(obj.tools):
            self.app.inform.emit('[ERROR_NOTCL] %s...' % _('Cancelled. Empty file, it has no geometry'))
            return

        # use the name of the first tool selected in self.geo_tools_table which has the diameter passed as tool_dia
        originar_name = obj.options['name'].partition('_')[0]
        outname = "%s_%s" % (originar_name, 'cnc_solderpaste')

        self.on_create_gcode(name=outname, workobject=obj)

    def on_create_gcode(self, name, workobject, use_thread=True):
        """
        Creates a multi-tool CNCJob. The actual work is done here.

        :param name: outname for the resulting CNCJob object
        :param workobject: the solderpaste dispensing Geometry object that is the source
        :param use_thread: True if threaded execution is desired
        :return:
        """
        obj = workobject

        try:
            xmin = obj.options['xmin']
            ymin = obj.options['ymin']
            xmax = obj.options['xmax']
            ymax = obj.options['ymax']
        except Exception as e:
            self.app.log.error("SolderPaste.on_create_gcode() --> %s\n" % str(e))
            msg = '[ERROR] %s' % _("An internal error has occurred. See shell.\n")
            msg += 'SolderPaste.on_create_gcode() --> %s' % str(e)
            msg += traceback.format_exc()
            self.app.inform.emit(msg)
            return

        # Object initialization function for app.app_obj.new_object()
        # RUNNING ON SEPARATE THREAD!
        def job_init(new_obj, app_obj):
            assert new_obj.kind == 'cncjob', \
                "Initializer expected a CNCJobObject, got %s" % type(new_obj)

            # this turn on the FlatCAMCNCJob plot for multiple tools
            new_obj.multitool = True
            new_obj.multigeo = True
            # new_obj object is a CNCJob object made from an Geometry object
            new_obj.tools.clear()
            new_obj.special_group = 'solder_paste_tool'

            new_obj.options['xmin'] = xmin
            new_obj.options['ymin'] = ymin
            new_obj.options['xmax'] = xmax
            new_obj.options['ymax'] = ymax

            total_gcode = ''
            for tooluid_key, tooluid_value in obj.tools.items():
                # find the tool_dia associated with the tooluid_key
                tool_dia = tooluid_value['tooldia']
                tool_cnc_dict = deepcopy(tooluid_value)

                new_obj.coords_decimals = self.app.defaults["cncjob_coords_decimals"]
                new_obj.fr_decimals = self.app.defaults["cncjob_fr_decimals"]
                new_obj.tool = int(tooluid_key)

                # Propagate options
                new_obj.options["tooldia"] = tool_dia
                new_obj.options['tool_dia'] = tool_dia

                # ## CREATE GCODE # ##
                res = new_obj.generate_gcode_from_solderpaste_geo(**tooluid_value)

                if res == 'fail':
                    app_obj.log.debug("GeometryObject.mtool_gen_cncjob() --> generate_from_geometry2() failed")
                    return 'fail'
                else:
                    tool_cnc_dict['gcode'] = StringIO(res)
                total_gcode += res

                # ## PARSE GCODE # ##
                tool_cnc_dict['gcode_parsed'] = new_obj.gcode_parse(tool_data=tool_cnc_dict['data'])

                # TODO this serve for bounding box creation only; should be optimized
                tool_cnc_dict['solid_geometry'] = unary_union([geo['geom'] for geo in tool_cnc_dict['gcode_parsed']])

                # tell gcode_parse from which point to start drawing the lines depending on what kind of
                # object is the source of gcode
                # new_obj is a CNCJob made from Geometry object
                new_obj.tools.update({
                    tooluid_key: deepcopy(tool_cnc_dict)
                })
                tool_cnc_dict.clear()

            new_obj.source_file = StringIO(total_gcode)

        if use_thread:
            # To be run in separate thread
            def job_thread(app_obj):
                with self.app.proc_container.new('%s...' % _("Working")):
                    if app_obj.app_obj.new_object("cncjob", name, job_init) != 'fail':
                        app_obj.inform.emit('[success] %s: %s' % (_("ToolSolderPaste CNCjob created"), name))
            # Create a promise with the name
            self.app.collection.promise(name)
            # Send to worker
            self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})
        else:
            self.app.app_obj.new_object("cncjob", name, job_init)

    def on_view_gcode(self):
        """
        View GCode in the Editor Tab.

        :return:
        """
        time_str = "{:%A, %d %B %Y at %H:%M}".format(datetime.now())

        self.text_editor_tab = AppTextEditor(app=self.app, plain_text=True)

        # add the tab if it was closed
        self.app.ui.plot_tab_area.addTab(self.text_editor_tab, _("GCode Editor"))
        self.text_editor_tab.setObjectName('solderpaste_gcode_editor_tab')

        # Switch plot_area to CNCJob tab
        self.app.ui.plot_tab_area.setCurrentWidget(self.text_editor_tab)

        name = self.ui.cnc_obj_combo.currentText()
        obj = self.app.collection.get_by_name(name)

        try:
            if obj.special_group != 'solder_paste_tool':
                self.app.inform.emit('[WARNING_NOTCL] %s' %
                                     _("This CNCJob object can't be processed. "
                                       "NOT a solder_paste_tool CNCJob object."))
                return
        except AttributeError:
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("This CNCJob object can't be processed. "
                                   "NOT a solder_paste_tool CNCJob object."))
            return

        gcode = '(G-CODE GENERATED BY FLATCAM v%s - www.flatcam.org - Version Date: %s)\n' % \
                (str(self.app.version), str(self.app.version_date)) + '\n'

        gcode += '(Name: ' + str(name) + ')\n'
        gcode += '(Type: ' + "G-code from " + str(obj.options['type']) + " for Solder Paste dispenser" + ')\n'

        gcode += '(Units: ' + self.units.upper() + ')\n' + "\n"
        gcode += '(Created on ' + time_str + ')\n' + '\n'

        # obj is a CNCJob object made from an Geometry object
        for tool in obj.tools:
            try:
                # it's text
                gcode += obj.tools[tool]['gcode']
            except TypeError:
                # it's StringIO
                gcode += obj.tools[tool]['gcode'].getvalue()

        # then append the text from GCode to the text editor
        # try:
        #     lines = StringIO(gcode)
        # except Exception as e:
        #     self.app.log.error("ToolSolderpaste.on_view_gcode() --> %s" % str(e))
        #     self.app.inform.emit('[ERROR_NOTCL] %s...' % _("No Gcode in the object"))
        #     return

        try:
            # for line in lines:
            #     proc_line = str(line).strip('\n')
            #     self.text_editor_tab.code_editor.append(proc_line)
            self.text_editor_tab.load_text(gcode, move_to_start=True)
        except Exception as e:
            self.app.log.error('ToolSolderPaste.on_view_gcode() -->%s' % str(e))
            self.app.inform.emit('[ERROR] %s --> %s' % ('ToolSolderPaste.on_view_gcode()', str(e)))
            return

    def on_save_gcode(self):
        """
        Save solderpaste dispensing GCode to a file on HDD.

        :return:
        """
        time_str = "{:%A, %d %B %Y at %H:%M}".format(datetime.now())
        name = self.ui.cnc_obj_combo.currentText()
        obj = self.app.collection.get_by_name(name)

        if obj.special_group != 'solder_paste_tool':
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("This CNCJob object can't be processed. "
                                   "NOT a solder_paste_tool CNCJob object."))
            return

        _filter_ = "G-Code Files (*.nc);;G-Code Files (*.txt);;G-Code Files (*.tap);;G-Code Files (*.cnc);;" \
                   "G-Code Files (*.g-code);;All Files (*.*);;G-Code Files (*.gcode);;G-Code Files (*.ngc)"

        try:
            dir_file_to_save = self.app.get_last_save_folder() + '/' + str(name)
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Export GCode ..."),
                directory=dir_file_to_save,
                ext_filter=_filter_
            )
        except TypeError:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Export Code ..."),
                ext_filter=_filter_)

        if filename == '':
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Export cancelled ..."))
            return

        gcode = '(G-CODE GENERATED BY FLATCAM v%s - www.flatcam.org - Version Date: %s)\n' % \
                (str(self.app.version), str(self.app.version_date)) + '\n'

        gcode += '(Name: ' + str(name) + ')\n'
        gcode += '(Type: ' + "G-code from " + str(obj.options['type']) + " for Solder Paste dispenser" + ')\n'

        gcode += '(Units: ' + self.units.upper() + ')\n' + "\n"
        gcode += '(Created on ' + time_str + ')\n' + '\n'

        # for CNCJob objects made from Gerber or Geometry objects
        for tool in obj.tools:
            gcode += obj.tools[tool]['gcode']
        lines = StringIO(gcode)

        # ## Write
        if filename is not None:
            try:
                with open(filename, 'w') as f:
                    for line in lines:
                        f.write(line)
            except FileNotFoundError:
                self.app.inform.emit('[WARNING_NOTCL] %s' %
                                     _("No such file or directory"))
                return
            except PermissionError:
                self.app.inform.emit('[WARNING] %s' %
                                     _("Permission denied, saving not possible.\n"
                                       "Most likely another app is holding the file open and not accessible."))
                return 'fail'

        if self.app.defaults["global_open_style"] is False:
            self.app.file_opened.emit("gcode", filename)
        self.app.file_saved.emit("gcode", filename)
        self.app.inform.emit('[success] %s: %s' % (_("Solder paste dispenser GCode file saved to"), filename))

    def reset_fields(self):
        self.ui.obj_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.ui.geo_obj_combo.setRootModelIndex(self.app.collection.index(2, 0, QtCore.QModelIndex()))
        self.ui.cnc_obj_combo.setRootModelIndex(self.app.collection.index(3, 0, QtCore.QModelIndex()))


class SolderUI:

    pluginName = _("SP Dispenser")

    def __init__(self, layout, app, solder_class):
        self.app = app
        self.decimals = self.app.decimals
        self.layout = layout

        # ## Title
        title_label = QtWidgets.QLabel("%s" % self.pluginName)
        title_label.setStyleSheet("""
                               QLabel
                               {
                                   font-size: 16px;
                                   font-weight: bold;
                               }
                               """)
        title_label.setToolTip(
            _("A plugin to help dispense solder paste on the PCB pads using a CNC machine.")
        )
        self.layout.addWidget(title_label)

        # ## Form Layout
        obj_form_layout = QtWidgets.QGridLayout()
        obj_form_layout.setColumnStretch(0, 0)
        obj_form_layout.setColumnStretch(1, 1)
        self.layout.addLayout(obj_form_layout)

        # ## Gerber Object to be used for solderpaste dispensing
        self.object_label = QtWidgets.QLabel('<b>%s</b>:' % _("GERBER"))
        self.object_label.setToolTip(_("Gerber Solderpaste object."))

        self.obj_combo = FCComboBox(callback=solder_class.on_rmb_combo)
        self.obj_combo.setModel(self.app.collection)
        self.obj_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.obj_combo.is_last = True
        self.obj_combo.obj_type = "Gerber"

        obj_form_layout.addWidget(self.object_label, 0, 0, 1, 2)
        obj_form_layout.addWidget(self.obj_combo, 2, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        obj_form_layout.addWidget(separator_line, 4, 0, 1, 2)

        # ### Tools ## ##
        self.tools_table_label = QtWidgets.QLabel('<b>%s</b>' % _('Tools Table'))
        self.tools_table_label.setToolTip(
            _("Tools pool from which the algorithm\n"
              "will pick the ones used for dispensing solder paste.")
        )
        obj_form_layout.addWidget(self.tools_table_label, 6, 0, 1, 2)

        self.tools_table = FCTable()
        obj_form_layout.addWidget(self.tools_table, 8, 0, 1, 2)

        self.tools_table.setColumnCount(3)
        self.tools_table.setHorizontalHeaderLabels(['#', _('Diameter'), ''])
        self.tools_table.setColumnHidden(2, True)
        self.tools_table.setSortingEnabled(False)
        # self.tools_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        self.tools_table.horizontalHeaderItem(0).setToolTip(
            _("This is the Tool Number.\n"
              "The solder dispensing will start with the tool with the biggest \n"
              "diameter, continuing until there are no more Nozzle tools.\n"
              "If there are no longer tools but there are still pads not covered\n "
              "with solder paste, the app will issue a warning message box.")
        )
        self.tools_table.horizontalHeaderItem(1).setToolTip(
            _("Tool Diameter. Its value\n"
              "is the width of the solder paste dispensed."))

        # ### Add a new Tool ## ##
        grid0 = QtWidgets.QGridLayout()
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        self.layout.addLayout(grid0)

        self.addtool_entry_lbl = QtWidgets.QLabel('<b>%s:</b>' % _('New Tool'))
        self.addtool_entry_lbl.setToolTip(
            _("Diameter for the new tool to add in the Tool Table")
        )
        self.addtool_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.addtool_entry.set_range(0.0000001, 10000.0000)
        self.addtool_entry.set_precision(self.decimals)
        self.addtool_entry.setSingleStep(0.1)

        self.addtool_btn = QtWidgets.QToolButton()
        self.addtool_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/plus16.png'))
        self.addtool_btn.setToolTip(
            _("Add a new nozzle tool to the Tool Table\n"
              "with the diameter specified above.")
        )

        self.deltool_btn = QtWidgets.QToolButton()
        self.deltool_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/trash16.png'))
        self.deltool_btn.setToolTip(
            _("Delete a selection of tools in the Tool Table\n"
              "by first selecting a row in the Tool Table.")
        )

        grid0.addWidget(self.addtool_entry_lbl, 0, 0)
        grid0.addWidget(self.addtool_entry, 0, 1)
        grid0.addWidget(self.addtool_btn, 0, 2)
        grid0.addWidget(self.deltool_btn, 0, 3)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        grid0.addWidget(separator_line, 2, 0, 1, 4)

        self.gcode_frame = QtWidgets.QFrame()
        self.gcode_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.gcode_frame)

        self.tool_box = QtWidgets.QVBoxLayout()
        self.tool_box.setContentsMargins(0, 0, 0, 0)
        self.gcode_frame.setLayout(self.tool_box)

        # Parameter Layout
        self.param_grid = QtWidgets.QGridLayout()
        self.tool_box.addLayout(self.param_grid)

        step1_lbl = QtWidgets.QLabel("<b>%s:</b>" % _('Parameters'))
        self.param_grid.addWidget(step1_lbl, 0, 0)

        # Z dispense start
        self.z_start_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.z_start_entry.set_range(0.0000001, 10000.0000)
        self.z_start_entry.set_precision(self.decimals)
        self.z_start_entry.setSingleStep(0.1)

        self.z_start_label = QtWidgets.QLabel('%s:' % _("Z Dispense Start"))
        self.z_start_label.setToolTip(
            _("The height (Z) when solder paste dispensing starts.")
        )
        self.param_grid.addWidget(self.z_start_label, 2, 0)
        self.param_grid.addWidget(self.z_start_entry, 2, 1)

        # Z dispense
        self.z_dispense_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.z_dispense_entry.set_range(0.0000001, 10000.0000)
        self.z_dispense_entry.set_precision(self.decimals)
        self.z_dispense_entry.setSingleStep(0.1)

        self.z_dispense_label = QtWidgets.QLabel('%s:' % _("Z Dispense"))
        self.z_dispense_label.setToolTip(
            _("The height (Z) when doing solder paste dispensing.")
        )
        self.param_grid.addWidget(self.z_dispense_label, 4, 0)
        self.param_grid.addWidget(self.z_dispense_entry, 4, 1)

        # Z dispense stop
        self.z_stop_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.z_stop_entry.set_range(0.0000001, 10000.0000)
        self.z_stop_entry.set_precision(self.decimals)
        self.z_stop_entry.setSingleStep(0.1)

        self.z_stop_label = QtWidgets.QLabel('%s:' % _("Z Dispense Stop"))
        self.z_stop_label.setToolTip(
            _("The height (Z) when solder paste dispensing stops.")
        )
        self.param_grid.addWidget(self.z_stop_label, 6, 0)
        self.param_grid.addWidget(self.z_stop_entry, 6, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.param_grid.addWidget(separator_line, 7, 0, 1, 2)

        # Z travel
        self.z_travel_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.z_travel_entry.set_range(0.0000001, 10000.0000)
        self.z_travel_entry.set_precision(self.decimals)
        self.z_travel_entry.setSingleStep(0.1)

        self.z_travel_label = QtWidgets.QLabel('%s:' % _("Travel Z"))
        self.z_travel_label.setToolTip(
            _("The height (Z) for travel between pads\n"
              "(without dispensing solder paste).")
        )
        self.param_grid.addWidget(self.z_travel_label, 8, 0)
        self.param_grid.addWidget(self.z_travel_entry, 8, 1)

        # Z toolchange location
        self.z_toolchange_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.z_toolchange_entry.set_range(0.0000001, 10000.0000)
        self.z_toolchange_entry.set_precision(self.decimals)
        self.z_toolchange_entry.setSingleStep(0.1)

        self.z_toolchange_label = QtWidgets.QLabel('%s:' % _("Tool change Z"))
        self.z_toolchange_label.setToolTip(
            _("The height (Z) for tool (nozzle) change.")
        )
        self.param_grid.addWidget(self.z_toolchange_label, 10, 0)
        self.param_grid.addWidget(self.z_toolchange_entry, 10, 1)

        # X,Y Toolchange location
        self.xy_toolchange_entry = FCEntry()
        self.xy_toolchange_label = QtWidgets.QLabel('%s:' % _("Toolchange X-Y"))
        self.xy_toolchange_label.setToolTip(
            _("The X,Y location for tool (nozzle) change.\n"
              "The format is (x, y) where x and y are real numbers.")
        )
        self.param_grid.addWidget(self.xy_toolchange_label, 12, 0)
        self.param_grid.addWidget(self.xy_toolchange_entry, 12, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.param_grid.addWidget(separator_line, 13, 0, 1, 2)

        # Feedrate X-Y
        self.frxy_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.frxy_entry.set_range(0.0000, 910000.0000)
        self.frxy_entry.set_precision(self.decimals)
        self.frxy_entry.setSingleStep(0.1)

        self.frxy_label = QtWidgets.QLabel('%s:' % _("Feedrate X-Y"))
        self.frxy_label.setToolTip(
            _("Feedrate (speed) while moving on the X-Y plane.")
        )
        self.param_grid.addWidget(self.frxy_label, 14, 0)
        self.param_grid.addWidget(self.frxy_entry, 14, 1)

        # Feedrate Z
        self.frz_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.frz_entry.set_range(0.0000, 910000.0000)
        self.frz_entry.set_precision(self.decimals)
        self.frz_entry.setSingleStep(0.1)

        self.frz_label = QtWidgets.QLabel('%s:' % _("Feedrate Z"))
        self.frz_label.setToolTip(
            _("Feedrate (speed) while moving vertically\n"
              "(on Z plane).")
        )
        self.param_grid.addWidget(self.frz_label, 16, 0)
        self.param_grid.addWidget(self.frz_entry, 16, 1)

        # Feedrate Z Dispense
        self.frz_dispense_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.frz_dispense_entry.set_range(0.0000, 910000.0000)
        self.frz_dispense_entry.set_precision(self.decimals)
        self.frz_dispense_entry.setSingleStep(0.1)

        self.frz_dispense_label = QtWidgets.QLabel('%s:' % _("Feedrate Z Dispense"))
        self.frz_dispense_label.setToolTip(
            _("Feedrate (speed) while moving up vertically\n"
              "to Dispense position (on Z plane).")
        )
        self.param_grid.addWidget(self.frz_dispense_label, 18, 0)
        self.param_grid.addWidget(self.frz_dispense_entry, 18, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.param_grid.addWidget(separator_line, 19, 0, 1, 2)

        # Spindle Speed Forward
        self.speedfwd_entry = FCSpinner(callback=self.confirmation_message_int)
        self.speedfwd_entry.set_range(0, 999999)
        self.speedfwd_entry.set_step(1000)

        self.speedfwd_label = QtWidgets.QLabel('%s:' % _("Spindle Speed FWD"))
        self.speedfwd_label.setToolTip(
            _("The dispenser speed while pushing solder paste\n"
              "through the dispenser nozzle.")
        )
        self.param_grid.addWidget(self.speedfwd_label, 20, 0)
        self.param_grid.addWidget(self.speedfwd_entry, 20, 1)

        # Dwell Forward
        self.dwellfwd_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.dwellfwd_entry.set_range(0.0000001, 10000.0000)
        self.dwellfwd_entry.set_precision(self.decimals)
        self.dwellfwd_entry.setSingleStep(0.1)

        self.dwellfwd_label = QtWidgets.QLabel('%s:' % _("Dwell FWD"))
        self.dwellfwd_label.setToolTip(
            _("Pause after solder dispensing.")
        )
        self.param_grid.addWidget(self.dwellfwd_label, 22, 0)
        self.param_grid.addWidget(self.dwellfwd_entry, 22, 1)

        # Spindle Speed Reverse
        self.speedrev_entry = FCSpinner(callback=self.confirmation_message_int)
        self.speedrev_entry.set_range(0, 999999)
        self.speedrev_entry.set_step(1000)

        self.speedrev_label = QtWidgets.QLabel('%s:' % _("Spindle Speed REV"))
        self.speedrev_label.setToolTip(
            _("The dispenser speed while retracting solder paste\n"
              "through the dispenser nozzle.")
        )
        self.param_grid.addWidget(self.speedrev_label, 24, 0)
        self.param_grid.addWidget(self.speedrev_entry, 24, 1)

        # Dwell Reverse
        self.dwellrev_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.dwellrev_entry.set_range(0.0000001, 10000.0000)
        self.dwellrev_entry.set_precision(self.decimals)
        self.dwellrev_entry.setSingleStep(0.1)

        self.dwellrev_label = QtWidgets.QLabel('%s:' % _("Dwell REV"))
        self.dwellrev_label.setToolTip(
            _("Pause after solder paste dispenser retracted,\n"
              "to allow pressure equilibrium.")
        )
        self.param_grid.addWidget(self.dwellrev_label, 26, 0)
        self.param_grid.addWidget(self.dwellrev_entry, 26, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.param_grid.addWidget(separator_line, 27, 0, 1, 2)

        # Preprocessors
        pp_label = QtWidgets.QLabel('%s:' % _('Preprocessor'))
        pp_label.setToolTip(
            _("Files that control the GCode generation.")
        )

        self.pp_combo = FCComboBox()
        self.param_grid.addWidget(pp_label, 28, 0)
        self.param_grid.addWidget(self.pp_combo, 28, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.param_grid.addWidget(separator_line, 30, 0, 1, 2)

        # Buttons Grid
        self.button_grid = QtWidgets.QGridLayout()
        self.button_grid.setColumnStretch(0, 0)
        self.button_grid.setColumnStretch(1, 1)
        self.tool_box.addLayout(self.button_grid)

        # Generate Geometry
        self.soldergeo_btn = FCButton(_("Generate Geometry"))
        self.soldergeo_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/geometry32.png'))

        self.soldergeo_btn.setToolTip(
            _("Generate solder paste dispensing geometry.")
        )
        self.soldergeo_btn.setStyleSheet("""
                                           QPushButton
                                           {
                                               font-weight: bold;
                                           }
                                           """)
        self.button_grid.addWidget(self.soldergeo_btn, 0, 0, 1, 2)

        # Geometry Object to be used for Solderpaste dispensing
        self.geo_obj_combo = FCComboBox(callback=solder_class.on_rmb_combo)
        self.geo_obj_combo.setModel(self.app.collection)
        self.geo_obj_combo.setRootModelIndex(self.app.collection.index(2, 0, QtCore.QModelIndex()))
        self.geo_obj_combo.is_last = True
        self.geo_obj_combo.obj_type = "Geometry"

        self.geo_object_label = QtWidgets.QLabel('%s:' % _("Geometry"))
        self.geo_object_label.setToolTip(
            _("Geometry Solder Paste object.\n"
              "The name of the object has to end in:\n"
              "'_solderpaste' as a protection.")
        )
        self.button_grid.addWidget(self.geo_object_label, 2, 0)
        self.button_grid.addWidget(self.geo_obj_combo, 2, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.button_grid.addWidget(separator_line, 4, 0, 1, 2)

        # ## Buttons
        self.solder_gcode_btn = FCButton(_("Generate CNCJob object"))
        self.solder_gcode_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/cnc16.png'))
        self.solder_gcode_btn.setToolTip(
            _("Generate GCode for Solder Paste dispensing\n"
              "on PCB pads.")
        )
        self.solder_gcode_btn.setStyleSheet("""
                               QPushButton
                               {
                                   font-weight: bold;
                               }
                               """)
        self.button_grid.addWidget(self.solder_gcode_btn, 6, 0, 1, 2)

        # Gerber Object to be used for solderpaste dispensing
        self.cnc_obj_combo = FCComboBox(callback=solder_class.on_rmb_combo)
        self.cnc_obj_combo.setModel(self.app.collection)
        self.cnc_obj_combo.setRootModelIndex(self.app.collection.index(3, 0, QtCore.QModelIndex()))
        self.cnc_obj_combo.is_last = True
        self.geo_obj_combo.obj_type = "CNCJob"

        self.cnc_object_label = QtWidgets.QLabel('%s:' % _("CNCJob"))
        self.cnc_object_label.setToolTip(
            _("CNCJob Solder paste object.\n"
              "In order to enable the GCode save section,\n"
              "the name of the object has to end in:\n"
              "'_solderpaste' as a protection.")
        )
        self.button_grid.addWidget(self.cnc_object_label, 8, 0)
        self.button_grid.addWidget(self.cnc_obj_combo, 8, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.button_grid.addWidget(separator_line, 10, 0, 1, 2)

        # Save and Review GCode
        buttons_hlay = QtWidgets.QHBoxLayout()
        self.solder_gcode_save_btn = FCButton(_("Save GCode"))
        self.solder_gcode_save_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/save_as.png'))
        self.solder_gcode_save_btn.setToolTip(
            _("Save the generated GCode for Solder Paste dispensing\n"
              "on PCB pads, to a file.")
        )
        self.solder_gcode_save_btn.setStyleSheet("""
                               QPushButton
                               {
                                   font-weight: bold;
                               }
                               """)

        self.solder_gcode_view_btn = QtWidgets.QToolButton()
        self.solder_gcode_view_btn.setToolTip(_("Review CNC Code."))
        self.solder_gcode_view_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/find32.png'))

        buttons_hlay.addWidget(self.solder_gcode_save_btn)
        buttons_hlay.addWidget(self.solder_gcode_view_btn)
        self.button_grid.addLayout(buttons_hlay, 12, 0, 1, 2)

        self.layout.addStretch(1)

        # ## Reset Tool
        self.reset_button = FCButton(_("Reset Tool"))
        self.reset_button.setIcon(QtGui.QIcon(self.app.resource_location + '/reset32.png'))
        self.reset_button.setToolTip(
            _("Will reset the tool parameters.")
        )
        self.reset_button.setStyleSheet("""
                               QPushButton
                               {
                                   font-weight: bold;
                               }
                               """)
        self.layout.addWidget(self.reset_button)

        # action to be added in the combobox context menu
        self.combo_context_del_action = QtGui.QAction(QtGui.QIcon(self.app.resource_location + '/trash16.png'),
                                                          _("Delete Object"))

        # #################################### FINSIHED GUI ###########################
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
