# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from appTool import AppTool
from appCommon.Common import LoudDict
from appGUI.GUIElements import FCComboBox, FCEntry, FCTable, FCDoubleSpinner, FCSpinner, FCFileSaveDialog, \
    FCInputSpinner
from app_Main import log
from camlib import distance
from appEditors.AppTextEditor import AppTextEditor

from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import Qt
from copy import deepcopy
from datetime import datetime

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
        self.toolName = self.ui.toolName

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

        # action to be added in the combobox context menu
        self.combo_context_del_action = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/trash16.png'),
                                                          _("Delete Object"))

        # ## Signals
        self.combo_context_del_action.triggered.connect(self.on_delete_object)
        
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

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolSolderPaste()")

        if toggle:
            # if the splitter is hidden, display it, else hide it but only if the current widget is the same
            if self.app.ui.splitter.sizes()[0] == 0:
                self.app.ui.splitter.setSizes([1, 1])
            else:
                try:
                    if self.app.ui.tool_scroll_area.widget().objectName() == self.toolName:
                        # if tab is populated with the tool but it does not have the focus, focus on it
                        if not self.app.ui.notebook.currentWidget() is self.app.ui.tool_tab:
                            # focus on Tool Tab
                            self.app.ui.notebook.setCurrentWidget(self.app.ui.tool_tab)
                        else:
                            self.app.ui.splitter.setSizes([0, 1])
                except AttributeError:
                    pass
        else:
            if self.app.ui.splitter.sizes()[0] == 0:
                self.app.ui.splitter.setSizes([1, 1])

        AppTool.run(self)
        self.set_tool_ui()
        self.build_ui()

        self.app.ui.notebook.setTabText(2, _("SolderPaste Tool"))

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Alt+K', **kwargs)

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

    def set_tool_ui(self):
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
        self.read_form_to_options()

        self.ui.tools_table.setupContextMenu()
        self.ui.tools_table.addContextMenu(
            _("Add"), lambda: self.on_tool_add(dia=None, muted=None),
            icon=QtGui.QIcon(self.app.resource_location + "/plus16.png"))
        self.ui.tools_table.addContextMenu(
            _("Delete"), lambda:
            self.on_tool_delete(rows_to_delete=None, all_tools=None),
            icon=QtGui.QIcon(self.app.resource_location + "/delete32.png")
        )

        try:
            dias = [float(eval(dia)) for dia in self.app.defaults["tools_solderpaste_tools"].split(",") if dia != '']
        except Exception:
            log.error("At least one Nozzle tool diameter needed. "
                      "Verify in Edit -> Preferences -> TOOLS -> Solder Paste Tools.")
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

        for name in list(self.app.preprocessors.keys()):
            # populate only with preprocessor files that start with 'Paste_'
            if name.partition('_')[0] != 'Paste':
                continue
            self.ui.pp_combo.addItem(name)

        self.reset_fields()

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
                    id_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                    row_no = tool_id - 1
                    self.ui.tools_table.setItem(row_no, 0, id_item)

                    # Diameter
                    dia = QtWidgets.QTableWidgetItem('%.*f' % (self.decimals, tooluid_value['tooldia']))
                    dia.setFlags(QtCore.Qt.ItemIsEnabled)
                    self.ui.tools_table.setItem(row_no, 1, dia)

                    # Tool unique ID
                    tool_uid_item = QtWidgets.QTableWidgetItem(str(int(tooluid_key)))
                    self.ui.tools_table.setItem(row_no, 2, tool_uid_item)

        # make the diameter column editable
        for row in range(tool_id):
            self.ui.tools_table.item(row, 1).setFlags(
                QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

        # all the tools are selected by default
        self.ui.tools_table.selectColumn(0)
        #
        self.ui.tools_table.resizeColumnsToContents()
        self.ui.tools_table.resizeRowsToContents()

        vertical_header = self.ui.tools_table.verticalHeader()
        vertical_header.hide()
        self.ui.tools_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        horizontal_header = self.ui.tools_table.horizontalHeader()
        horizontal_header.setMinimumSectionSize(10)
        horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(0, 20)
        horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)

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
            log.debug("Tool missing. Add a tool in Tool Table. %s" % str(e))
            return

        # update the form
        try:
            # set the form with data from the newly selected tool
            for tooluid_key, tooluid_value in self.tooltable_tools.items():
                if int(tooluid_key) == tooluid:
                    self.set_form(deepcopy(tooluid_value['data']))
        except Exception as e:
            log.debug("ToolSolderPaste ---> update_ui() " + str(e))

        self.ui_connect()

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
        for i in range(self.ui.gcode_form_layout.count()):
            if isinstance(self.ui.gcode_form_layout.itemAt(i).widget(), FCComboBox):
                self.ui.gcode_form_layout.itemAt(i).widget().currentIndexChanged.connect(self.read_form_to_tooldata)
            if isinstance(self.ui.gcode_form_layout.itemAt(i).widget(), FCEntry):
                self.ui.gcode_form_layout.itemAt(i).widget().editingFinished.connect(self.read_form_to_tooldata)

        self.ui.tools_table.itemChanged.connect(self.on_tool_edit)
        self.ui.tools_table.currentItemChanged.connect(self.on_row_selection_change)

    def ui_disconnect(self):
        # if connected, disconnect the signal from the slot on item_changed as it creates issues

        for i in range(self.ui.gcode_form_layout.count()):
            if isinstance(self.ui.gcode_form_layout.itemAt(i).widget(), FCComboBox):
                try:
                    self.ui.gcode_form_layout.itemAt(i).widget().currentIndexChanged.disconnect()
                except (TypeError, AttributeError):
                    pass
            if isinstance(self.ui.gcode_form_layout.itemAt(i).widget(), FCEntry):
                try:
                    self.ui.gcode_form_layout.itemAt(i).widget().editingFinished.disconnect()
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

    def read_form_to_tooldata(self, tooluid=None):
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
            log.debug("ToolSoderPaste.set_form() --> parameter not a dict")
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

        if float('%.*f' % (self.decimals, tool_dia)) in tool_dias:
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
            log.debug(str(e))

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
        menu.addAction(self.combo_context_del_action)
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
        proc = self.app.proc_container.new(_("Working ..."))
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

        # TODO when/if the Gerber files will have solid_geometry in the self.apertures I will have to take care here
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
                geo_obj.tools[tooluid]['offset'] = 'Path'
                geo_obj.tools[tooluid]['offset_value'] = 0.0
                geo_obj.tools[tooluid]['type'] = 'SolderPaste'
                geo_obj.tools[tooluid]['tool_type'] = 'DN'

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
                            log.debug('ToolSolderPaste.on_create_geo() --> %s' % str(e))
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
                    log.error("SolderPaste.on_create_geo() --> %s" % str(e))
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
            log.debug("SolderPaste.on_create_gcode() --> %s\n" % str(e))
            msg = '[ERROR] %s' % _("An internal error has occurred. See shell.\n")
            msg += 'SolderPaste.on_create_gcode() --> %s' % str(e)
            msg += traceback.format_exc()
            self.app.inform.emit(msg)
            return

        # Object initialization function for app.app_obj.new_object()
        # RUNNING ON SEPARATE THREAD!
        def job_init(job_obj):
            assert job_obj.kind == 'cncjob', \
                "Initializer expected a CNCJobObject, got %s" % type(job_obj)

            # this turn on the FlatCAMCNCJob plot for multiple tools
            job_obj.multitool = True
            job_obj.multigeo = True
            job_obj.cnc_tools.clear()
            job_obj.special_group = 'solder_paste_tool'

            job_obj.options['xmin'] = xmin
            job_obj.options['ymin'] = ymin
            job_obj.options['xmax'] = xmax
            job_obj.options['ymax'] = ymax

            total_gcode = ''
            for tooluid_key, tooluid_value in obj.tools.items():
                # find the tool_dia associated with the tooluid_key
                tool_dia = tooluid_value['tooldia']
                tool_cnc_dict = deepcopy(tooluid_value)

                job_obj.coords_decimals = self.app.defaults["cncjob_coords_decimals"]
                job_obj.fr_decimals = self.app.defaults["cncjob_fr_decimals"]
                job_obj.tool = int(tooluid_key)

                # Propagate options
                job_obj.options["tooldia"] = tool_dia
                job_obj.options['tool_dia'] = tool_dia

                # ## CREATE GCODE # ##
                res = job_obj.generate_gcode_from_solderpaste_geo(**tooluid_value)

                if res == 'fail':
                    log.debug("GeometryObject.mtool_gen_cncjob() --> generate_from_geometry2() failed")
                    return 'fail'
                else:
                    tool_cnc_dict['gcode'] = res
                total_gcode += res

                # ## PARSE GCODE # ##
                tool_cnc_dict['gcode_parsed'] = job_obj.gcode_parse()

                # TODO this serve for bounding box creation only; should be optimized
                tool_cnc_dict['solid_geometry'] = unary_union([geo['geom'] for geo in tool_cnc_dict['gcode_parsed']])

                # tell gcode_parse from which point to start drawing the lines depending on what kind of
                # object is the source of gcode
                job_obj.toolchange_xy_type = "geometry"
                job_obj.cnc_tools.update({
                    tooluid_key: deepcopy(tool_cnc_dict)
                })
                tool_cnc_dict.clear()

            job_obj.source_file = total_gcode

        if use_thread:
            # To be run in separate thread
            def job_thread(app_obj):
                with self.app.proc_container.new('%s' % _("Working ...")):
                    if app_obj.app_obj.new_object("cncjob", name, job_init) != 'fail':
                        app_obj.inform.emit('[success] [success] %s: %s' %
                                            (_("ToolSolderPaste CNCjob created"), name))
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

        self.text_editor_tab = AppTextEditor(app=self.app)

        # add the tab if it was closed
        self.app.ui.plot_tab_area.addTab(self.text_editor_tab, _("SP GCode Editor"))
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

        # if str(p['options']['type']) == 'Excellon' or str(p['options']['type']) == 'Excellon Geometry':
        #     gcode += '(Tools in use: ' + str(p['options']['Tools_in_use']) + ')\n'

        gcode += '(Units: ' + self.units.upper() + ')\n' + "\n"
        gcode += '(Created on ' + time_str + ')\n' + '\n'

        for tool in obj.cnc_tools:
            gcode += obj.cnc_tools[tool]['gcode']

        # then append the text from GCode to the text editor
        try:
            lines = StringIO(gcode)
        except Exception as e:
            log.debug("ToolSolderpaste.on_view_gcode() --> %s" % str(e))
            self.app.inform.emit('[ERROR_NOTCL] %s...' % _("No Gcode in the object"))
            return

        try:
            # for line in lines:
            #     proc_line = str(line).strip('\n')
            #     self.text_editor_tab.code_editor.append(proc_line)
            self.text_editor_tab.load_text(lines, move_to_start=True)
        except Exception as e:
            log.debug('ToolSolderPaste.on_view_gcode() -->%s' % str(e))
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

        # if str(p['options']['type']) == 'Excellon' or str(p['options']['type']) == 'Excellon Geometry':
        #     gcode += '(Tools in use: ' + str(p['options']['Tools_in_use']) + ')\n'

        gcode += '(Units: ' + self.units.upper() + ')\n' + "\n"
        gcode += '(Created on ' + time_str + ')\n' + '\n'

        for tool in obj.cnc_tools:
            gcode += obj.cnc_tools[tool]['gcode']
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

    toolName = _("Solder Paste Tool")

    def __init__(self, layout, app, solder_class):
        self.app = app
        self.decimals = self.app.decimals
        self.layout = layout

        # ## Title
        title_label = QtWidgets.QLabel("%s" % self.toolName)
        title_label.setStyleSheet("""
                               QLabel
                               {
                                   font-size: 16px;
                                   font-weight: bold;
                               }
                               """)
        self.layout.addWidget(title_label)

        # ## Form Layout
        obj_form_layout = QtWidgets.QFormLayout()
        self.layout.addLayout(obj_form_layout)

        # ## Gerber Object to be used for solderpaste dispensing
        self.obj_combo = FCComboBox(callback=solder_class.on_rmb_combo)
        self.obj_combo.setModel(self.app.collection)
        self.obj_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.obj_combo.is_last = True
        self.obj_combo.obj_type = "Gerber"

        self.object_label = QtWidgets.QLabel('<b>%s</b>:' % _("GERBER"))
        self.object_label.setToolTip(_("Gerber Solderpaste object.")
                                     )
        obj_form_layout.addRow(self.object_label)
        obj_form_layout.addRow(self.obj_combo)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        obj_form_layout.addRow(separator_line)

        # ### Tools ## ##
        self.tools_table_label = QtWidgets.QLabel('<b>%s</b>' % _('Tools Table'))
        self.tools_table_label.setToolTip(
            _("Tools pool from which the algorithm\n"
              "will pick the ones used for dispensing solder paste.")
        )
        self.layout.addWidget(self.tools_table_label)

        self.tools_table = FCTable()
        self.layout.addWidget(self.tools_table)

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
        hlay_tools = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay_tools)

        self.addtool_entry_lbl = QtWidgets.QLabel('<b>%s:</b>' % _('New Nozzle Tool'))
        self.addtool_entry_lbl.setToolTip(
            _("Diameter for the new tool to add in the Tool Table")
        )
        self.addtool_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.addtool_entry.set_range(0.0000001, 10000.0000)
        self.addtool_entry.set_precision(self.decimals)
        self.addtool_entry.setSingleStep(0.1)

        # hlay.addWidget(self.addtool_label)
        # hlay.addStretch()
        hlay_tools.addWidget(self.addtool_entry_lbl)
        hlay_tools.addWidget(self.addtool_entry)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        self.addtool_btn = QtWidgets.QPushButton(_('Add'))
        self.addtool_btn.setToolTip(
            _("Add a new nozzle tool to the Tool Table\n"
              "with the diameter specified above.")
        )

        self.deltool_btn = QtWidgets.QPushButton(_('Delete'))
        self.deltool_btn.setToolTip(
            _("Delete a selection of tools in the Tool Table\n"
              "by first selecting a row in the Tool Table.")
        )

        grid0.addWidget(self.addtool_btn, 0, 0)
        grid0.addWidget(self.deltool_btn, 0, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 1, 0, 1, 3)

        # ## Buttons
        grid0_1 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0_1)

        step1_lbl = QtWidgets.QLabel("<b>%s:</b>" % _('STEP 1'))
        step1_lbl.setToolTip(
            _("First step is to select a number of nozzle tools for usage\n"
              "and then optionally modify the GCode parameters below.")
        )
        step1_description_lbl = QtWidgets.QLabel(_("Select tools.\n"
                                                   "Modify parameters."))

        grid0_1.addWidget(step1_lbl, 0, 0, alignment=Qt.AlignTop)
        grid0_1.addWidget(step1_description_lbl, 0, 2, alignment=Qt.AlignBottom)

        self.gcode_frame = QtWidgets.QFrame()
        self.gcode_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.gcode_frame)
        self.gcode_box = QtWidgets.QVBoxLayout()
        self.gcode_box.setContentsMargins(0, 0, 0, 0)
        self.gcode_frame.setLayout(self.gcode_box)

        # ## Form Layout
        self.gcode_form_layout = QtWidgets.QFormLayout()
        self.gcode_box.addLayout(self.gcode_form_layout)

        # Z dispense start
        self.z_start_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.z_start_entry.set_range(0.0000001, 10000.0000)
        self.z_start_entry.set_precision(self.decimals)
        self.z_start_entry.setSingleStep(0.1)

        self.z_start_label = QtWidgets.QLabel('%s:' % _("Z Dispense Start"))
        self.z_start_label.setToolTip(
            _("The height (Z) when solder paste dispensing starts.")
        )
        self.gcode_form_layout.addRow(self.z_start_label, self.z_start_entry)

        # Z dispense
        self.z_dispense_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.z_dispense_entry.set_range(0.0000001, 10000.0000)
        self.z_dispense_entry.set_precision(self.decimals)
        self.z_dispense_entry.setSingleStep(0.1)

        self.z_dispense_label = QtWidgets.QLabel('%s:' % _("Z Dispense"))
        self.z_dispense_label.setToolTip(
            _("The height (Z) when doing solder paste dispensing.")
        )
        self.gcode_form_layout.addRow(self.z_dispense_label, self.z_dispense_entry)

        # Z dispense stop
        self.z_stop_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.z_stop_entry.set_range(0.0000001, 10000.0000)
        self.z_stop_entry.set_precision(self.decimals)
        self.z_stop_entry.setSingleStep(0.1)

        self.z_stop_label = QtWidgets.QLabel('%s:' % _("Z Dispense Stop"))
        self.z_stop_label.setToolTip(
            _("The height (Z) when solder paste dispensing stops.")
        )
        self.gcode_form_layout.addRow(self.z_stop_label, self.z_stop_entry)

        # Z travel
        self.z_travel_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.z_travel_entry.set_range(0.0000001, 10000.0000)
        self.z_travel_entry.set_precision(self.decimals)
        self.z_travel_entry.setSingleStep(0.1)

        self.z_travel_label = QtWidgets.QLabel('%s:' % _("Z Travel"))
        self.z_travel_label.setToolTip(
            _("The height (Z) for travel between pads\n"
              "(without dispensing solder paste).")
        )
        self.gcode_form_layout.addRow(self.z_travel_label, self.z_travel_entry)

        # Z toolchange location
        self.z_toolchange_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.z_toolchange_entry.set_range(0.0000001, 10000.0000)
        self.z_toolchange_entry.set_precision(self.decimals)
        self.z_toolchange_entry.setSingleStep(0.1)

        self.z_toolchange_label = QtWidgets.QLabel('%s:' % _("Z Toolchange"))
        self.z_toolchange_label.setToolTip(
            _("The height (Z) for tool (nozzle) change.")
        )
        self.gcode_form_layout.addRow(self.z_toolchange_label, self.z_toolchange_entry)

        # X,Y Toolchange location
        self.xy_toolchange_entry = FCEntry()
        self.xy_toolchange_label = QtWidgets.QLabel('%s:' % _("Toolchange X-Y"))
        self.xy_toolchange_label.setToolTip(
            _("The X,Y location for tool (nozzle) change.\n"
              "The format is (x, y) where x and y are real numbers.")
        )
        self.gcode_form_layout.addRow(self.xy_toolchange_label, self.xy_toolchange_entry)

        # Feedrate X-Y
        self.frxy_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.frxy_entry.set_range(0.0000, 910000.0000)
        self.frxy_entry.set_precision(self.decimals)
        self.frxy_entry.setSingleStep(0.1)

        self.frxy_label = QtWidgets.QLabel('%s:' % _("Feedrate X-Y"))
        self.frxy_label.setToolTip(
            _("Feedrate (speed) while moving on the X-Y plane.")
        )
        self.gcode_form_layout.addRow(self.frxy_label, self.frxy_entry)

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
        self.gcode_form_layout.addRow(self.frz_label, self.frz_entry)

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
        self.gcode_form_layout.addRow(self.frz_dispense_label, self.frz_dispense_entry)

        # Spindle Speed Forward
        self.speedfwd_entry = FCSpinner(callback=self.confirmation_message_int)
        self.speedfwd_entry.set_range(0, 999999)
        self.speedfwd_entry.set_step(1000)

        self.speedfwd_label = QtWidgets.QLabel('%s:' % _("Spindle Speed FWD"))
        self.speedfwd_label.setToolTip(
            _("The dispenser speed while pushing solder paste\n"
              "through the dispenser nozzle.")
        )
        self.gcode_form_layout.addRow(self.speedfwd_label, self.speedfwd_entry)

        # Dwell Forward
        self.dwellfwd_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.dwellfwd_entry.set_range(0.0000001, 10000.0000)
        self.dwellfwd_entry.set_precision(self.decimals)
        self.dwellfwd_entry.setSingleStep(0.1)

        self.dwellfwd_label = QtWidgets.QLabel('%s:' % _("Dwell FWD"))
        self.dwellfwd_label.setToolTip(
            _("Pause after solder dispensing.")
        )
        self.gcode_form_layout.addRow(self.dwellfwd_label, self.dwellfwd_entry)

        # Spindle Speed Reverse
        self.speedrev_entry = FCSpinner(callback=self.confirmation_message_int)
        self.speedrev_entry.set_range(0, 999999)
        self.speedrev_entry.set_step(1000)

        self.speedrev_label = QtWidgets.QLabel('%s:' % _("Spindle Speed REV"))
        self.speedrev_label.setToolTip(
            _("The dispenser speed while retracting solder paste\n"
              "through the dispenser nozzle.")
        )
        self.gcode_form_layout.addRow(self.speedrev_label, self.speedrev_entry)

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
        self.gcode_form_layout.addRow(self.dwellrev_label, self.dwellrev_entry)

        # Preprocessors
        pp_label = QtWidgets.QLabel('%s:' % _('Preprocessor'))
        pp_label.setToolTip(
            _("Files that control the GCode generation.")
        )

        self.pp_combo = FCComboBox()
        # self.pp_combo.setStyleSheet('background-color: rgb(255,255,255)')
        self.gcode_form_layout.addRow(pp_label, self.pp_combo)

        # ## Buttons
        # grid1 = QtWidgets.QGridLayout()
        # self.gcode_box.addLayout(grid1)

        self.solder_gcode_btn = QtWidgets.QPushButton(_("Generate GCode"))
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

        self.generation_frame = QtWidgets.QFrame()
        self.generation_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.generation_frame)
        self.generation_box = QtWidgets.QVBoxLayout()
        self.generation_box.setContentsMargins(0, 0, 0, 0)
        self.generation_frame.setLayout(self.generation_box)

        # ## Buttons
        grid2 = QtWidgets.QGridLayout()
        self.generation_box.addLayout(grid2)

        step2_lbl = QtWidgets.QLabel("<b>%s:</b>" % _('STEP 2'))
        step2_lbl.setToolTip(
            _("Second step is to create a solder paste dispensing\n"
              "geometry out of an Solder Paste Mask Gerber file.")
        )

        self.soldergeo_btn = QtWidgets.QPushButton(_("Generate Geo"))
        self.soldergeo_btn.setToolTip(
            _("Generate solder paste dispensing geometry.")
        )
        self.soldergeo_btn.setStyleSheet("""
                                               QPushButton
                                               {
                                                   font-weight: bold;
                                               }
                                               """)

        grid2.addWidget(step2_lbl, 0, 0)
        grid2.addWidget(self.soldergeo_btn, 0, 2)

        # ## Form Layout
        geo_form_layout = QtWidgets.QFormLayout()
        self.generation_box.addLayout(geo_form_layout)

        # ## Geometry Object to be used for solderpaste dispensing
        self.geo_obj_combo = FCComboBox(callback=solder_class.on_rmb_combo)
        self.geo_obj_combo.setModel(self.app.collection)
        self.geo_obj_combo.setRootModelIndex(self.app.collection.index(2, 0, QtCore.QModelIndex()))
        self.geo_obj_combo.is_last = True
        self.geo_obj_combo.obj_type = "Geometry"

        self.geo_object_label = QtWidgets.QLabel('%s:' % _("Geo Result"))
        self.geo_object_label.setToolTip(
            _("Geometry Solder Paste object.\n"
              "The name of the object has to end in:\n"
              "'_solderpaste' as a protection.")
        )
        geo_form_layout.addRow(self.geo_object_label, self.geo_obj_combo)

        grid3 = QtWidgets.QGridLayout()
        self.generation_box.addLayout(grid3)

        step3_lbl = QtWidgets.QLabel("<b>%s:</b>" % _('STEP 3'))
        step3_lbl.setToolTip(
            _("Third step is to select a solder paste dispensing geometry,\n"
              "and then generate a CNCJob object.\n\n"
              "REMEMBER: if you want to create a CNCJob with new parameters,\n"
              "first you need to generate a geometry with those new params,\n"
              "and only after that you can generate an updated CNCJob.")
        )

        grid3.addWidget(step3_lbl, 0, 0)
        grid3.addWidget(self.solder_gcode_btn, 0, 2)

        # ## Form Layout
        cnc_form_layout = QtWidgets.QFormLayout()
        self.generation_box.addLayout(cnc_form_layout)

        # ## Gerber Object to be used for solderpaste dispensing
        self.cnc_obj_combo = FCComboBox(callback=solder_class.on_rmb_combo)
        self.cnc_obj_combo.setModel(self.app.collection)
        self.cnc_obj_combo.setRootModelIndex(self.app.collection.index(3, 0, QtCore.QModelIndex()))
        self.cnc_obj_combo.is_last = True
        self.geo_obj_combo.obj_type = "CNCJob"

        self.cnc_object_label = QtWidgets.QLabel('%s:' % _("CNC Result"))
        self.cnc_object_label.setToolTip(
            _("CNCJob Solder paste object.\n"
              "In order to enable the GCode save section,\n"
              "the name of the object has to end in:\n"
              "'_solderpaste' as a protection.")
        )
        cnc_form_layout.addRow(self.cnc_object_label, self.cnc_obj_combo)

        grid4 = QtWidgets.QGridLayout()
        self.generation_box.addLayout(grid4)

        self.solder_gcode_view_btn = QtWidgets.QPushButton(_("View GCode"))
        self.solder_gcode_view_btn.setToolTip(
            _("View the generated GCode for Solder Paste dispensing\n"
              "on PCB pads.")
        )
        self.solder_gcode_view_btn.setStyleSheet("""
                               QPushButton
                               {
                                   font-weight: bold;
                               }
                               """)

        self.solder_gcode_save_btn = QtWidgets.QPushButton(_("Save GCode"))
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

        step4_lbl = QtWidgets.QLabel("<b>%s:</b>" % _('STEP 4'))
        step4_lbl.setToolTip(
            _("Fourth step (and last) is to select a CNCJob made from \n"
              "a solder paste dispensing geometry, and then view/save it's GCode.")
        )

        grid4.addWidget(step4_lbl, 0, 0)
        grid4.addWidget(self.solder_gcode_view_btn, 0, 2)
        grid4.addWidget(self.solder_gcode_save_btn, 1, 0, 1, 3)

        self.layout.addStretch()

        # ## Reset Tool
        self.reset_button = QtWidgets.QPushButton(_("Reset Tool"))
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
