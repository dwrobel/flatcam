# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Modified by: Marius Adrian Stanciu (c)              #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtCore, QtGui

from appTool import AppTool
from appGUI.GUIElements import FCCheckBox, FCDoubleSpinner, RadioSet, FCTable, FCButton,\
    FCComboBox, OptionalInputSection, FCLabel, FCInputDialogSpinnerButton, FCComboBox2
from appParsers.ParseGerber import Gerber

from camlib import grace

from copy import deepcopy

import numpy as np
from shapely.geometry import base
from shapely.ops import unary_union, nearest_points
from shapely.geometry import MultiPolygon, Polygon, MultiLineString, LineString, LinearRing

from matplotlib.backend_bases import KeyEvent as mpl_key_event

import logging
import traceback
import sys
import gettext
import simplejson as json
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class NonCopperClear(AppTool, Gerber):

    optimal_found_sig = QtCore.pyqtSignal(float)

    def __init__(self, app):
        self.app = app
        self.decimals = self.app.decimals

        AppTool.__init__(self, app)
        Gerber.__init__(self, steps_per_circle=self.app.defaults["gerber_circle_steps"])

        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = NccUI(layout=self.layout, app=self.app)
        self.toolName = self.ui.toolName

        # #############################################################################
        # ###################### Setup CONTEXT MENU ###################################
        # #############################################################################
        self.ui.tools_table.setupContextMenu()
        self.ui.tools_table.addContextMenu(
            _("Add"), self.on_add_tool_by_key, icon=QtGui.QIcon(self.app.resource_location + "/plus16.png")
        )
        self.ui.tools_table.addContextMenu(
            _("Add from DB"), self.on_add_tool_by_key, icon=QtGui.QIcon(self.app.resource_location + "/plus16.png")
        )
        self.ui.tools_table.addContextMenu(
            _("Delete"), lambda:
            self.on_tool_delete(rows_to_delete=None, all_tools=None),
            icon=QtGui.QIcon(self.app.resource_location + "/delete32.png")
        )

        # #############################################################################
        # ########################## VARIABLES ########################################
        # #############################################################################
        self.units = ''
        self.ncc_tools = {}
        self.tooluid = 0

        # store here the default data for Geometry Data
        self.default_data = {}

        self.obj_name = ""
        self.ncc_obj = None

        self.sel_rect = []

        self.bound_obj_name = ""
        self.bound_obj = None

        self.ncc_dia_list = []
        self.iso_dia_list = []
        self.has_offset = None
        self.o_name = None
        self.overlap = None
        self.connect = None
        self.contour = None
        self.rest = None

        # store here the tool diameter that is guaranteed to isolate the object
        self.safe_tooldia = None

        self.first_click = False
        self.cursor_pos = None
        self.mouse_is_dragging = False

        # store here the points for the "Polygon" area selection shape
        self.points = []
        # set this as True when in middle of drawing a "Polygon" area selection shape
        # it is made False by first click to signify that the shape is complete
        self.poly_drawn = False

        self.mm = None
        self.mr = None
        self.kp = None

        # disconnect flags
        self.area_sel_disconnect_flag = False

        # store here solid_geometry when there are tool with isolation job
        self.solid_geometry = []

        self.select_method = None
        self.tool_type_item_options = []

        self.circle_steps = int(self.app.defaults["gerber_circle_steps"])

        self.tooldia = None

        self.form_fields = {
            "tools_ncc_operation":      self.ui.op_radio,
            "tools_ncc_overlap":        self.ui.ncc_overlap_entry,
            "tools_ncc_margin":         self.ui.ncc_margin_entry,
            "tools_ncc_method":         self.ui.ncc_method_combo,
            "tools_ncc_connect":        self.ui.ncc_connect_cb,
            "tools_ncc_contour":        self.ui.ncc_contour_cb,
            "tools_ncc_offset_choice":  self.ui.ncc_choice_offset_cb,
            "tools_ncc_offset_value":   self.ui.ncc_offset_spinner,
            "tools_ncc_milling_type":   self.ui.milling_type_radio,
            "tools_ncc_check_valid":    self.ui.valid_cb
        }

        self.name2option = {
            "n_operation":      "tools_ncc_operation",
            "n_overlap":        "tools_ncc_overlap",
            "n_margin":         "tools_ncc_margin",
            "n_method":         "tools_ncc_method",
            "n_connect":        "tools_ncc_connect",
            "n_contour":        "tools_ncc_contour",
            "n_offset":         "tools_ncc_offset_choice",
            "n_offset_value":   "tools_ncc_offset_value",
            "n_milling_type":   "tools_ncc_milling_type",
            "n_check":          "tools_ncc_check_valid",
        }

        self.old_tool_dia = None

        self.connect_signals_at_init()

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Alt+N', **kwargs)

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolNonCopperClear()")
        log.debug("ToolNCC().run() was launched ...")

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

        # reset those objects on a new run
        self.ncc_obj = None
        self.bound_obj = None
        self.obj_name = ''
        self.bound_obj_name = ''

        self.build_ui()

        # all the tools are selected by default
        # self.ui.tools_table.selectColumn(0)
        self.ui.tools_table.selectAll()

        self.app.ui.notebook.setTabText(2, _("NCC Tool"))

    def connect_signals_at_init(self):
        # #############################################################################
        # ############################ SIGNALS ########################################
        # #############################################################################
        self.ui.find_optimal_button.clicked.connect(self.on_find_optimal_tooldia)
        # Custom Signal
        self.optimal_found_sig.connect(lambda val: self.ui.new_tooldia_entry.set_value(float(val)))

        self.ui.deltool_btn.clicked.connect(self.on_tool_delete)
        self.ui.generate_ncc_button.clicked.connect(self.on_ncc_click)

        self.ui.op_radio.activated_custom.connect(self.on_operation_change)

        self.ui.reference_combo_type.currentIndexChanged.connect(self.on_reference_combo_changed)
        self.ui.select_combo.currentIndexChanged.connect(self.ui.on_toggle_reference)

        self.ui.ncc_rest_cb.stateChanged.connect(self.ui.on_rest_machining_check)
        self.ui.ncc_order_radio.activated_custom[str].connect(self.on_order_changed)

        self.ui.type_obj_radio.activated_custom.connect(self.on_type_obj_index_changed)
        self.ui.apply_param_to_all.clicked.connect(self.on_apply_param_to_all_clicked)

        # add a new tool Signals
        self.ui.add_newtool_button.clicked.connect(lambda: self.on_tool_add())
        self.ui.addtool_from_db_btn.clicked.connect(self.on_ncc_tool_add_from_db_clicked)

        self.ui.reset_button.clicked.connect(self.set_tool_ui)

        # Cleanup on Graceful exit (CTRL+ALT+X combo key)
        self.app.cleanup.connect(self.set_tool_ui)

    def on_type_obj_index_changed(self, val):
        obj_type = 0 if val == 'gerber' else 2
        self.ui.object_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.ui.object_combo.setCurrentIndex(0)
        self.ui.object_combo.obj_type = {
            "gerber": "Gerber", "geometry": "Geometry"
        }[self.ui.type_obj_radio.get_value()]

    def on_operation_change(self, val):
        self.ui.parameters_ui(val=val)

        current_row = self.ui.tools_table.currentRow()
        try:
            current_uid = int(self.ui.tools_table.item(current_row, 3).text())
            self.ncc_tools[current_uid]['data']['tools_ncc_operation'] = val
            # TODO got a crash here, a KeyError exception; need to see it again and find out the why
        except AttributeError:
            return

    def on_toggle_all_rows(self):
        """
        will toggle the selection of all rows in Tools table

        :return:
        """
        sel_model = self.ui.tools_table.selectionModel()
        sel_indexes = sel_model.selectedIndexes()

        # it will iterate over all indexes which means all items in all columns too but I'm interested only on rows
        sel_rows = set()
        for idx in sel_indexes:
            sel_rows.add(idx.row())

        if len(sel_rows) == self.ui.tools_table.rowCount():
            self.ui.tools_table.clearSelection()
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("No Tool Selected"))
            )
        else:
            self.ui.tools_table.selectAll()
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("Multiple Tools"))
            )

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

    def update_ui(self):
        self.blockSignals(True)

        sel_rows = set()
        table_items = self.ui.tools_table.selectedItems()
        if table_items:
            for it in table_items:
                sel_rows.add(it.row())
            # sel_rows = sorted(set(index.row() for index in self.ui.tools_table.selectedIndexes()))

        if not sel_rows or len(sel_rows) == 0:
            self.ui.generate_ncc_button.setDisabled(True)
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("No Tool Selected"))
            )
            self.blockSignals(False)
            return
        else:
            self.ui.generate_ncc_button.setDisabled(False)

        for current_row in sel_rows:
            # populate the form with the data from the tool associated with the row parameter
            try:
                item = self.ui.tools_table.item(current_row, 3)
                if item is not None:
                    tooluid = int(item.text())
                else:
                    return
            except Exception as e:
                log.debug("Tool missing. Add a tool in the Tool Table. %s" % str(e))
                return

            # update the QLabel that shows for which Tool we have the parameters in the UI form
            if len(sel_rows) == 1:
                cr = current_row + 1
                self.ui.tool_data_label.setText(
                    "<b>%s: <font color='#0000FF'>%s %d</font></b>" % (_('Parameters for'), _("Tool"), cr)
                )
                try:
                    # set the form with data from the newly selected tool
                    for tooluid_key, tooluid_value in list(self.ncc_tools.items()):
                        if int(tooluid_key) == tooluid:
                            for key, value in tooluid_value.items():
                                if key == 'data':
                                    self.storage_to_form(tooluid_value['data'])
                except Exception as e:
                    log.debug("NonCopperClear ---> update_ui() " + str(e))
            else:
                self.ui.tool_data_label.setText(
                    "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("Multiple Tools"))
                )

        self.blockSignals(False)

    def storage_to_form(self, dict_storage):
        for form_key in self.form_fields:
            for storage_key in dict_storage:
                if form_key == storage_key:
                    try:
                        self.form_fields[form_key].set_value(dict_storage[form_key])
                    except Exception as e:
                        log.debug("NonCopperClear.storage_to_form() --> %s" % str(e))
                        pass

    def form_to_storage(self):
        if self.ui.tools_table.rowCount() == 0:
            # there is no tool in tool table so we can't save the GUI elements values to storage
            return

        self.blockSignals(True)

        widget_changed = self.sender()
        wdg_objname = widget_changed.objectName()
        option_changed = self.name2option[wdg_objname]

        # row = self.ui.tools_table.currentRow()
        rows = sorted(set(index.row() for index in self.ui.tools_table.selectedIndexes()))
        for row in rows:
            if row < 0:
                row = 0
            tooluid_item = int(self.ui.tools_table.item(row, 3).text())

            for tooluid_key, tooluid_val in self.ncc_tools.items():
                if int(tooluid_key) == tooluid_item:
                    new_option_value = self.form_fields[option_changed].get_value()
                    if option_changed in tooluid_val:
                        tooluid_val[option_changed] = new_option_value
                    if option_changed in tooluid_val['data']:
                        tooluid_val['data'][option_changed] = new_option_value

        self.blockSignals(False)

    def on_apply_param_to_all_clicked(self):
        if self.ui.tools_table.rowCount() == 0:
            # there is no tool in tool table so we can't save the GUI elements values to storage
            log.debug("NonCopperClear.on_apply_param_to_all_clicked() --> no tool in Tools Table, aborting.")
            return

        self.blockSignals(True)

        row = self.ui.tools_table.currentRow()
        if row < 0:
            row = 0

        tooluid_item = int(self.ui.tools_table.item(row, 3).text())
        temp_tool_data = {}

        for tooluid_key, tooluid_val in self.ncc_tools.items():
            if int(tooluid_key) == tooluid_item:
                # this will hold the 'data' key of the self.tools[tool] dictionary that corresponds to
                # the current row in the tool table
                temp_tool_data = tooluid_val['data']
                break

        for tooluid_key, tooluid_val in self.ncc_tools.items():
            tooluid_val['data'] = deepcopy(temp_tool_data)

        # store all the data associated with the row parameter to the self.tools storage
        # tooldia_item = float(self.ui.tools_table.item(row, 1).text())
        # type_item = self.ui.tools_table.cellWidget(row, 2).currentText()
        # operation_type_item = self.ui.tools_table.cellWidget(row, 4).currentText()
        #
        # nccoffset_item = self.ncc_choice_offset_cb.get_value()
        # nccoffset_value_item = float(self.ncc_offset_spinner.get_value())

        # this new dict will hold the actual useful data, another dict that is the value of key 'data'
        # temp_tools = {}
        # temp_dia = {}
        # temp_data = {}
        #
        # for tooluid_key, tooluid_value in self.ncc_tools.items():
        #     for key, value in tooluid_value.items():
        #         if key == 'data':
        #             # update the 'data' section
        #             for data_key in tooluid_value[key].keys():
        #                 for form_key, form_value in self.form_fields.items():
        #                     if form_key == data_key:
        #                         temp_data[data_key] = form_value.get_value()
        #                 # make sure we make a copy of the keys not in the form (we may use 'data' keys that are
        #                 # updated from self.app.defaults
        #                 if data_key not in self.form_fields:
        #                     temp_data[data_key] = value[data_key]
        #             temp_dia[key] = deepcopy(temp_data)
        #             temp_data.clear()
        #
        #         elif key == 'solid_geometry':
        #             temp_dia[key] = deepcopy(self.tools[tooluid_key]['solid_geometry'])
        #         else:
        #             temp_dia[key] = deepcopy(value)
        #
        #         temp_tools[tooluid_key] = deepcopy(temp_dia)
        #
        # self.ncc_tools.clear()
        # self.ncc_tools = deepcopy(temp_tools)
        # temp_tools.clear()

        self.app.inform.emit('[success] %s' % _("Current Tool parameters were applied to all tools."))

        self.blockSignals(False)

    def on_add_tool_by_key(self):
        # tool_add_popup = FCInputDialog(title='%s...' % _("New Tool"),
        #                                text='%s:' % _('Enter a Tool Diameter'),
        #                                min=0.0001, max=10000.0000, decimals=self.decimals)
        btn_icon = QtGui.QIcon(self.app.resource_location + '/open_excellon32.png')

        tool_add_popup = FCInputDialogSpinnerButton(title='%s...' % _("New Tool"),
                                                    text='%s:' % _('Enter a Tool Diameter'),
                                                    min=0.0001, max=10000.0000, decimals=self.decimals,
                                                    button_icon=btn_icon,
                                                    callback=self.on_find_optimal_tooldia,
                                                    parent=self.app.ui)
        tool_add_popup.setWindowIcon(QtGui.QIcon(self.app.resource_location + '/letter_t_32.png'))

        def find_optimal(valor):
            tool_add_popup.set_value(float(valor))

        self.optimal_found_sig.connect(find_optimal)

        val, ok = tool_add_popup.get_results()
        if ok:
            if float(val) == 0:
                self.app.inform.emit('[WARNING_NOTCL] %s' %
                                     _("Please enter a tool diameter with non-zero value, in Float format."))
                self.optimal_found_sig.disconnect(find_optimal)
                return
            self.on_tool_add(custom_dia=float(val))
        else:
            self.app.inform.emit('[WARNING_NOTCL] %s...' % _("Adding Tool cancelled"))
        self.optimal_found_sig.disconnect(find_optimal)

    def set_tool_ui(self):
        self.units = self.app.defaults['units'].upper()
        self.old_tool_dia = self.app.defaults["tools_ncc_newdia"]

        # reset the value to prepare for another isolation
        self.safe_tooldia = None

        self.ui.tools_frame.show()

        # use the current selected object and make it visible in the NCC object combobox
        sel_list = self.app.collection.get_selected()
        if len(sel_list) == 1:
            active = self.app.collection.get_active()
            kind = active.kind
            if kind == 'gerber':
                self.ui.type_obj_radio.set_value('gerber')
            else:
                self.ui.type_obj_radio.set_value('geometry')

            # run those once so the obj_type attribute is updated for the FCComboboxes
            # so the last loaded object is displayed
            self.on_type_obj_index_changed(val=kind)
            self.on_reference_combo_changed()

            self.ui.object_combo.set_value(active.options['name'])
        else:
            kind = 'gerber'
            self.ui.type_obj_radio.set_value('gerber')

            # run those once so the obj_type attribute is updated for the FCComboboxes
            # so the last loaded object is displayed
            self.on_type_obj_index_changed(val=kind)
            self.on_reference_combo_changed()

        self.ui.op_radio.set_value(self.app.defaults["tools_ncc_operation"])
        self.ui.ncc_order_radio.set_value(self.app.defaults["tools_ncc_order"])
        self.ui.ncc_overlap_entry.set_value(self.app.defaults["tools_ncc_overlap"])
        self.ui.ncc_margin_entry.set_value(self.app.defaults["tools_ncc_margin"])
        self.ui.ncc_method_combo.set_value(self.app.defaults["tools_ncc_method"])
        self.ui.ncc_connect_cb.set_value(self.app.defaults["tools_ncc_connect"])
        self.ui.ncc_contour_cb.set_value(self.app.defaults["tools_ncc_contour"])
        self.ui.ncc_choice_offset_cb.set_value(self.app.defaults["tools_ncc_offset_choice"])
        self.ui.ncc_offset_spinner.set_value(self.app.defaults["tools_ncc_offset_value"])

        self.ui.ncc_rest_cb.set_value(self.app.defaults["tools_ncc_rest"])
        self.ui.on_rest_machining_check(state=self.app.defaults["tools_ncc_rest"])

        self.ui.rest_ncc_margin_entry.set_value(self.app.defaults["tools_ncc_margin"])
        self.ui.rest_ncc_connect_cb.set_value(self.app.defaults["tools_ncc_connect"])
        self.ui.rest_ncc_contour_cb.set_value(self.app.defaults["tools_ncc_contour"])
        self.ui.rest_ncc_choice_offset_cb.set_value(self.app.defaults["tools_ncc_offset_choice"])
        self.ui.rest_ncc_offset_spinner.set_value(self.app.defaults["tools_ncc_offset_value"])

        self.ui.select_combo.set_value(self.app.defaults["tools_ncc_ref"])
        self.ui.area_shape_radio.set_value(self.app.defaults["tools_ncc_area_shape"])
        self.ui.valid_cb.set_value(self.app.defaults["tools_ncc_check_valid"])

        self.ui.milling_type_radio.set_value(self.app.defaults["tools_ncc_milling_type"])

        self.ui.new_tooldia_entry.set_value(self.app.defaults["tools_ncc_newdia"])

        # init the working variables
        self.default_data.clear()
        self.default_data = {
            "name":                     '_ncc',
            "plot":                     self.app.defaults["geometry_plot"],
            "cutz":                     float(self.app.defaults["geometry_cutz"]),
            "vtipdia":                  float(self.app.defaults["geometry_vtipdia"]),
            "vtipangle":                float(self.app.defaults["geometry_vtipangle"]),
            "travelz":                  self.app.defaults["geometry_travelz"],
            "feedrate":                 self.app.defaults["geometry_feedrate"],
            "feedrate_z":               self.app.defaults["geometry_feedrate_z"],
            "feedrate_rapid":           self.app.defaults["geometry_feedrate_rapid"],
            "dwell":                    self.app.defaults["geometry_dwell"],
            "dwelltime":                self.app.defaults["geometry_dwelltime"],
            "multidepth":               self.app.defaults["geometry_multidepth"],
            "ppname_g":                 self.app.defaults["geometry_ppname_g"],
            "depthperpass":             self.app.defaults["geometry_depthperpass"],
            "extracut":                 self.app.defaults["geometry_extracut"],
            "extracut_length":          self.app.defaults["geometry_extracut_length"],
            "toolchange":               self.app.defaults["geometry_toolchange"],
            "toolchangez":              self.app.defaults["geometry_toolchangez"],
            "endz":                     self.app.defaults["geometry_endz"],
            "endxy":                    self.app.defaults["geometry_endxy"],

            "spindlespeed":             self.app.defaults["geometry_spindlespeed"],
            "toolchangexy":             self.app.defaults["geometry_toolchangexy"],
            "startz":                   self.app.defaults["geometry_startz"],

            "area_exclusion":           self.app.defaults["geometry_area_exclusion"],
            "area_shape":               self.app.defaults["geometry_area_shape"],
            "area_strategy":            self.app.defaults["geometry_area_strategy"],
            "area_overz":               float(self.app.defaults["geometry_area_overz"]),
            "optimization_type":        self.app.defaults["geometry_optimization_type"],

            "tools_ncc_operation":      self.app.defaults["tools_ncc_operation"],
            "tools_ncc_margin":         self.app.defaults["tools_ncc_margin"],
            "tools_ncc_method":         self.app.defaults["tools_ncc_method"],
            "tools_ncc_connect":        self.app.defaults["tools_ncc_connect"],
            "tools_ncc_contour":        self.app.defaults["tools_ncc_contour"],
            "tools_ncc_overlap":        self.app.defaults["tools_ncc_overlap"],
            "tools_ncc_rest":           self.app.defaults["tools_ncc_rest"],
            "tools_ncc_ref":            self.app.defaults["tools_ncc_ref"],
            "tools_ncc_offset_choice":  self.app.defaults["tools_ncc_offset_choice"],
            "tools_ncc_offset_value":   self.app.defaults["tools_ncc_offset_value"],
            "tools_ncc_milling_type":   self.app.defaults["tools_ncc_milling_type"],
            "tools_ncc_check_valid":    self.app.defaults["tools_ncc_check_valid"],
        }

        try:
            dias = [float(self.app.defaults["tools_ncc_tools"])]
        except (ValueError, TypeError):
            try:
                dias = [float(eval(dia)) for dia in self.app.defaults["tools_ncc_tools"].split(",") if dia != '']
            except AttributeError:
                dias = self.app.defaults["tools_ncc_tools"]
        except Exception:
            dias = []

        self.tooluid = 0

        self.ncc_tools.clear()
        for tool_dia in dias:
            self.on_tool_add(custom_dia=tool_dia)

        self.obj_name = ""
        self.ncc_obj = None
        self.bound_obj_name = ""
        self.bound_obj = None

        self.tool_type_item_options = ["C1", "C2", "C3", "C4", "B", "V"]
        self.units = self.app.defaults['units'].upper()

        self.first_click = False
        self.cursor_pos = None
        self.mouse_is_dragging = False

        prog_plot = True if self.app.defaults["tools_ncc_plotting"] == 'progressive' else False
        if prog_plot:
            self.temp_shapes.clear(update=True)

        self.sel_rect = []

        self.ui.tools_table.drag_drop_sig.connect(self.rebuild_ui)

    def rebuild_ui(self):
        # read the table tools uid
        current_uid_list = []
        for row in range(self.ui.tools_table.rowCount()):
            uid = int(self.ui.tools_table.item(row, 3).text())
            current_uid_list.append(uid)

        new_tools = {}
        new_uid = 1

        for current_uid in current_uid_list:
            new_tools[new_uid] = deepcopy(self.ncc_tools[current_uid])
            new_uid += 1

        self.ncc_tools = new_tools

        # the tools table changed therefore we need to rebuild it
        QtCore.QTimer.singleShot(20, self.build_ui)

    def build_ui(self):
        self.ui_disconnect()

        # updated units
        self.units = self.app.defaults['units'].upper()

        sorted_tools = []
        for k, v in self.ncc_tools.items():
            if self.units == "IN":
                sorted_tools.append(float('%.*f' % (self.decimals, float(v['tooldia']))))
            else:
                sorted_tools.append(float('%.*f' % (self.decimals, float(v['tooldia']))))

        order = self.ui.ncc_order_radio.get_value()
        if order == 'fwd':
            sorted_tools.sort(reverse=False)
        elif order == 'rev':
            sorted_tools.sort(reverse=True)
        else:
            pass

        n = len(sorted_tools)
        self.ui.tools_table.setRowCount(n)
        tool_id = 0

        for tool_sorted in sorted_tools:
            for tooluid_key, tooluid_value in self.ncc_tools.items():
                if float('%.*f' % (self.decimals, tooluid_value['tooldia'])) == tool_sorted:
                    tool_id += 1

                    id_ = QtWidgets.QTableWidgetItem('%d' % int(tool_id))
                    flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
                    id_.setFlags(flags)
                    row_no = tool_id - 1
                    self.ui.tools_table.setItem(row_no, 0, id_)  # Tool name/id

                    # Make sure that the drill diameter when in MM is with no more than self.decimals decimals
                    dia = QtWidgets.QTableWidgetItem('%.*f' % (self.decimals, tooluid_value['tooldia']))
                    dia.setFlags(QtCore.Qt.ItemIsEnabled)
                    self.ui.tools_table.setItem(row_no, 1, dia)  # Diameter

                    tool_type_item = FCComboBox()
                    tool_type_item.addItems(self.tool_type_item_options)
                    idx = tool_type_item.findText(tooluid_value['tool_type'])
                    tool_type_item.setCurrentIndex(idx)
                    self.ui.tools_table.setCellWidget(row_no, 2, tool_type_item)

                    tool_uid_item = QtWidgets.QTableWidgetItem(str(int(tooluid_key)))
                    # ## REMEMBER: THIS COLUMN IS HIDDEN IN OBJECTUI.PY # ##
                    self.ui.tools_table.setItem(row_no, 3, tool_uid_item)  # Tool unique ID

        # make the diameter column editable
        for row in range(tool_id):
            flags = QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
            self.ui.tools_table.item(row, 1).setFlags(flags)

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

        self.ui.tools_table.setMinimumHeight(self.ui.tools_table.getHeight())
        self.ui.tools_table.setMaximumHeight(self.ui.tools_table.getHeight())

        self.ui_connect()

        # set the text on tool_data_label after loading the object
        sel_rows = set()
        sel_items = self.ui.tools_table.selectedItems()
        for it in sel_items:
            sel_rows.add(it.row())
        if len(sel_rows) > 1:
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("Multiple Tools"))
            )

    def ui_connect(self):
        self.ui.tools_table.itemChanged.connect(self.on_tool_edit)

        # rows selected
        self.ui.tools_table.clicked.connect(self.on_row_selection_change)
        self.ui.tools_table.horizontalHeader().sectionClicked.connect(self.on_toggle_all_rows)

        for row in range(self.ui.tools_table.rowCount()):
            try:
                self.ui.tools_table.cellWidget(row, 2).currentIndexChanged.connect(self.on_tooltable_cellwidget_change)
            except AttributeError:
                pass

        for opt in self.form_fields:
            current_widget = self.form_fields[opt]
            if isinstance(current_widget, FCCheckBox):
                current_widget.stateChanged.connect(self.form_to_storage)
            if isinstance(current_widget, RadioSet):
                current_widget.activated_custom.connect(self.form_to_storage)
            elif isinstance(current_widget, FCDoubleSpinner):
                current_widget.returnPressed.connect(self.form_to_storage)
            elif isinstance(current_widget, FCComboBox):
                current_widget.currentIndexChanged.connect(self.form_to_storage)

        self.ui.ncc_rest_cb.stateChanged.connect(self.ui.on_rest_machining_check)
        self.ui.ncc_order_radio.activated_custom[str].connect(self.on_order_changed)

    def ui_disconnect(self):

        try:
            # if connected, disconnect the signal from the slot on item_changed as it creates issues
            self.ui.tools_table.itemChanged.disconnect()
        except (TypeError, AttributeError):
            pass

        for row in range(self.ui.tools_table.rowCount()):

            try:
                self.ui.tools_table.cellWidget(row, 2).currentIndexChanged.disconnect()
            except (TypeError, AttributeError):
                pass

        for opt in self.form_fields:
            current_widget = self.form_fields[opt]
            if isinstance(current_widget, FCCheckBox):
                try:
                    current_widget.stateChanged.disconnect(self.form_to_storage)
                except (TypeError, ValueError):
                    pass
            if isinstance(current_widget, RadioSet):
                try:
                    current_widget.activated_custom.disconnect(self.form_to_storage)
                except (TypeError, ValueError):
                    pass
            elif isinstance(current_widget, FCDoubleSpinner):
                try:
                    current_widget.returnPressed.disconnect(self.form_to_storage)
                except (TypeError, ValueError):
                    pass
            elif isinstance(current_widget, FCComboBox):
                try:
                    current_widget.currentIndexChanged.disconnect(self.form_to_storage)
                except (TypeError, ValueError):
                    pass

        try:
            self.ui.ncc_rest_cb.stateChanged.disconnect(self.ui.on_rest_machining_check)
        except (TypeError, ValueError):
            pass
        try:
            self.ui.ncc_order_radio.activated_custom[str].disconnect(self.on_order_changed)
        except (TypeError, ValueError):
            pass

        # rows selected
        try:
            self.ui.tools_table.clicked.disconnect()
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.tools_table.horizontalHeader().sectionClicked.disconnect()
        except (TypeError, AttributeError):
            pass

    def on_reference_combo_changed(self):
        obj_type = self.ui.reference_combo_type.currentIndex()
        self.ui.reference_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.ui.reference_combo.setCurrentIndex(0)
        self.ui.reference_combo.obj_type = {0: "Gerber", 1: "Excellon", 2: "Geometry"}[obj_type]

    def on_order_changed(self, order):
        if order != 'no':
            self.build_ui()

    def on_tooltable_cellwidget_change(self):
        cw = self.sender()
        assert isinstance(cw, QtWidgets.QComboBox),\
            "Expected a QtWidgets.QComboBox, got %s" % isinstance(cw, QtWidgets.QComboBox)

        cw_index = self.ui.tools_table.indexAt(cw.pos())
        cw_row = cw_index.row()
        cw_col = cw_index.column()

        current_uid = int(self.ui.tools_table.item(cw_row, 3).text())

        # if the sender is in the column with index 2 then we update the tool_type key
        if cw_col == 2:
            tt = cw.currentText()
            typ = 'Iso' if tt == 'V' else 'Rough'

            self.ncc_tools[current_uid].update({
                'type': typ,
                'tool_type': tt,
            })

    def on_find_optimal_tooldia(self):
        self.find_safe_tooldia_worker()

    @staticmethod
    def find_optim_mp(aperture_storage, decimals):
        msg = 'ok'
        total_geo = []

        for ap in list(aperture_storage.keys()):
            if 'geometry' in aperture_storage[ap]:
                for geo_el in aperture_storage[ap]['geometry']:
                    if 'solid' in geo_el and geo_el['solid'] is not None and geo_el['solid'].is_valid:
                        total_geo.append(geo_el['solid'])

        total_geo = MultiPolygon(total_geo)
        total_geo = total_geo.buffer(0)

        try:
            __ = iter(total_geo)
            geo_len = len(total_geo)
        except TypeError:
            msg = ('[ERROR_NOTCL] %s' % _("The Gerber object has one Polygon as geometry.\n"
                                          "There are no distances between geometry elements to be found."))

        min_dict = {}
        idx = 1
        for geo in total_geo:
            for s_geo in total_geo[idx:]:
                # minimize the number of distances by not taking into considerations
                # those that are too small
                dist = geo.distance(s_geo)
                dist = float('%.*f' % (decimals, dist))
                loc_1, loc_2 = nearest_points(geo, s_geo)

                proc_loc = (
                    (float('%.*f' % (decimals, loc_1.x)), float('%.*f' % (decimals, loc_1.y))),
                    (float('%.*f' % (decimals, loc_2.x)), float('%.*f' % (decimals, loc_2.y)))
                )

                if dist in min_dict:
                    min_dict[dist].append(proc_loc)
                else:
                    min_dict[dist] = [proc_loc]

            idx += 1

        min_list = list(min_dict.keys())
        min_dist = min(min_list)

        return msg, min_dist

    # multiprocessing variant
    def find_safe_tooldia_multiprocessing(self):
        self.app.inform.emit(_("Checking tools for validity."))
        self.units = self.app.defaults['units'].upper()

        obj_name = self.ui.object_combo.currentText()

        # Get source object.
        try:
            fcobj = self.app.collection.get_by_name(obj_name)
        except Exception:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), str(obj_name)))
            return

        if fcobj is None:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Object not found"), str(obj_name)))
            return

        def job_thread(app_obj):
            with self.app.proc_container.new(_("Checking ...")):

                ap_storage = fcobj.apertures

                p = app_obj.pool.apply_async(self.find_optim_mp, args=(ap_storage, self.decimals))
                res = p.get()

                if res[0] != 'ok':
                    app_obj.inform.emit(res[0])
                    return 'fail'
                else:
                    min_dist = res[1]

                try:
                    min_dist_truncated = self.app.dec_format(float(min_dist), self.decimals)
                    self.safe_tooldia = min_dist_truncated

                    # find the selected tool ID's
                    sorted_tools = []
                    table_items = self.ui.tools_table.selectedItems()
                    sel_rows = {t.row() for t in table_items}
                    for row in sel_rows:
                        tid = int(self.ui.tools_table.item(row, 3).text())
                        sorted_tools.append(tid)
                    if not sorted_tools:
                        msg = _("There are no tools selected in the Tool Table.")
                        self.app.inform.emit('[ERROR_NOTCL] %s' % msg)
                        return 'fail'

                    # check if the tools diameters are less then the safe tool diameter
                    suitable_tools = []
                    for tool in sorted_tools:
                        tool_dia = float(self.ncc_tools[tool]['tooldia'])
                        if tool_dia <= self.safe_tooldia:
                            suitable_tools.append(tool_dia)

                    if not suitable_tools:
                        msg = _("Incomplete isolation. None of the selected tools could do a complete isolation.")
                        self.app.inform.emit('[WARNING] %s' % msg)
                    else:
                        msg = _("At least one of the selected tools can do a complete isolation.")
                        self.app.inform.emit('[success] %s' % msg)

                    # reset the value to prepare for another isolation
                    self.safe_tooldia = None
                except Exception as ee:
                    log.debug(str(ee))
                    return

        self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})

    def find_safe_tooldia_worker(self):
        self.app.inform.emit(_("Checking tools for validity."))
        self.units = self.app.defaults['units'].upper()

        obj_name = self.ui.object_combo.currentText()

        # Get source object.
        try:
            fcobj = self.app.collection.get_by_name(obj_name)
        except Exception:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), str(obj_name)))
            return

        if fcobj is None:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Object not found"), str(obj_name)))
            return

        def job_thread(app_obj):
            with self.app.proc_container.new(_("Checking ...")):
                try:
                    old_disp_number = 0
                    pol_nr = 0
                    app_obj.proc_container.update_view_text(' %d%%' % 0)
                    total_geo = []

                    for ap in list(fcobj.apertures.keys()):
                        if 'geometry' in fcobj.apertures[ap]:
                            for geo_el in fcobj.apertures[ap]['geometry']:
                                if self.app.abort_flag:
                                    # graceful abort requested by the user
                                    raise grace

                                if 'solid' in geo_el and geo_el['solid'] is not None and geo_el['solid'].is_valid:
                                    total_geo.append(geo_el['solid'])

                    total_geo = MultiPolygon(total_geo)
                    total_geo = total_geo.buffer(0)

                    try:
                        __ = iter(total_geo)
                        geo_len = len(total_geo)
                        geo_len = (geo_len * (geo_len - 1)) / 2
                    except TypeError:
                        app_obj.inform.emit('[ERROR_NOTCL] %s' %
                                            _("The Gerber object has one Polygon as geometry.\n"
                                              "There are no distances between geometry elements to be found."))
                        return 'fail'

                    min_dict = {}
                    idx = 1
                    for geo in total_geo:
                        for s_geo in total_geo[idx:]:
                            if self.app.abort_flag:
                                # graceful abort requested by the user
                                raise grace

                            # minimize the number of distances by not taking into considerations
                            # those that are too small
                            dist = geo.distance(s_geo)
                            dist = float('%.*f' % (self.decimals, dist))
                            loc_1, loc_2 = nearest_points(geo, s_geo)

                            proc_loc = (
                                (float('%.*f' % (self.decimals, loc_1.x)), float('%.*f' % (self.decimals, loc_1.y))),
                                (float('%.*f' % (self.decimals, loc_2.x)), float('%.*f' % (self.decimals, loc_2.y)))
                            )

                            if dist in min_dict:
                                min_dict[dist].append(proc_loc)
                            else:
                                min_dict[dist] = [proc_loc]

                            pol_nr += 1
                            disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 100]))

                            if old_disp_number < disp_number <= 100:
                                app_obj.proc_container.update_view_text(' %d%%' % disp_number)
                                old_disp_number = disp_number
                        idx += 1

                    min_list = list(min_dict.keys())
                    min_dist = min(min_list)

                    min_dist_truncated = self.app.dec_format(float(min_dist), self.decimals)
                    self.safe_tooldia = min_dist_truncated

                    self.optimal_found_sig.emit(min_dist_truncated)

                    app_obj.inform.emit('[success] %s: %s %s' %
                                        (_("Optimal tool diameter found"), str(min_dist_truncated),
                                         self.units.lower()))
                except Exception as ee:
                    log.debug(str(ee))
                    return

        self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})

    def on_tool_add(self, custom_dia=None):
        self.blockSignals(True)

        filename = self.app.tools_database_path()

        new_tools_dict = deepcopy(self.default_data)
        updated_tooldia = None

        # construct a list of all 'tooluid' in the self.iso_tools
        tool_uid_list = [int(tooluid_key) for tooluid_key in self.ncc_tools]

        # find maximum from the temp_uid, add 1 and this is the new 'tooluid'
        max_uid = 0 if not tool_uid_list else max(tool_uid_list)
        tooluid = int(max_uid + 1)

        tool_dias = []
        for k, v in self.ncc_tools.items():
            for tool_v in v.keys():
                if tool_v == 'tooldia':
                    tool_dias.append(self.app.dec_format(v[tool_v], self.decimals))

        # determine the new tool diameter
        if custom_dia is None:
            tool_dia = self.ui.new_tooldia_entry.get_value()
        else:
            tool_dia = custom_dia

        if tool_dia is None or tool_dia == 0:
            self.build_ui()
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Please enter a tool diameter with non-zero value, "
                                                          "in Float format."))
            self.blockSignals(False)
            return

        truncated_tooldia = self.app.dec_format(tool_dia, self.decimals)

        # if new tool diameter already in the Tool List then abort
        if truncated_tooldia in tool_dias:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled. Tool already in Tool Table."))
            self.blockSignals(False)
            return

        # load the database tools from the file
        try:
            with open(filename) as f:
                tools = f.read()
        except IOError:
            self.app.log.error("Could not load tools DB file.")
            self.app.inform.emit('[ERROR] %s' % _("Could not load the file."))
            self.blockSignals(False)
            self.on_tool_default_add(dia=tool_dia)
            return

        try:
            # store here the tools from Tools Database when searching in Tools Database
            tools_db_dict = json.loads(tools)
        except Exception:
            e = sys.exc_info()[0]
            self.app.log.error(str(e))
            self.app.inform.emit('[ERROR] %s' % _("Failed to parse Tools DB file."))
            self.blockSignals(False)
            self.on_tool_default_add(dia=tool_dia)

            return

        tool_found = 0

        offset = 'Path'
        offset_val = 0.0
        typ = 'Rough'
        tool_type = 'V'
        # look in database tools
        for db_tool, db_tool_val in tools_db_dict.items():
            offset = db_tool_val['offset']
            offset_val = db_tool_val['offset_value']
            typ = db_tool_val['type']
            tool_type = db_tool_val['tool_type']

            db_tooldia = db_tool_val['tooldia']
            low_limit = float(db_tool_val['data']['tol_min'])
            high_limit = float(db_tool_val['data']['tol_max'])

            # we need only tool marked for Isolation Tool
            if db_tool_val['data']['tool_target'] != _('NCC'):
                continue

            # if we find a tool with the same diameter in the Tools DB just update it's data
            if truncated_tooldia == db_tooldia:
                tool_found += 1
                for d in db_tool_val['data']:
                    if d.find('tools_iso') == 0:
                        new_tools_dict[d] = db_tool_val['data'][d]
                    elif d.find('tools_') == 0:
                        # don't need data for other App Tools; this tests after 'tools_drill_'
                        continue
                    else:
                        new_tools_dict[d] = db_tool_val['data'][d]
            # search for a tool that has a tolerance that the tool fits in
            elif high_limit >= truncated_tooldia >= low_limit:
                tool_found += 1
                updated_tooldia = db_tooldia
                for d in db_tool_val['data']:
                    if d.find('tools_iso') == 0:
                        new_tools_dict[d] = db_tool_val['data'][d]
                    elif d.find('tools_') == 0:
                        # don't need data for other App Tools; this tests after 'tools_drill_'
                        continue
                    else:
                        new_tools_dict[d] = db_tool_val['data'][d]

        # test we found a suitable tool in Tools Database or if multiple ones
        if tool_found == 0:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Tool not in Tools Database. Adding a default tool."))
            self.on_tool_default_add(dia=tool_dia)
            self.blockSignals(False)
            return

        if tool_found > 1:
            self.app.inform.emit(
                '[WARNING_NOTCL] %s' % _("Cancelled.\n"
                                         "Multiple tools for one tool diameter found in Tools Database."))
            self.blockSignals(False)
            return

        # if new tool diameter found in Tools Database already in the Tool List then abort
        if updated_tooldia is not None and updated_tooldia in tool_dias:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled. Tool already in Tool Table."))
            self.blockSignals(False)
            return

        new_tdia = deepcopy(updated_tooldia) if updated_tooldia is not None else deepcopy(truncated_tooldia)
        self.ncc_tools.update({
            tooluid: {
                'tooldia':          new_tdia,
                'offset':           deepcopy(offset),
                'offset_value':     deepcopy(offset_val),
                'type':             deepcopy(typ),
                'tool_type':        deepcopy(tool_type),
                'data':             deepcopy(new_tools_dict),
                'solid_geometry':   []
            }
        })
        self.blockSignals(False)
        self.build_ui()

        # select the tool just added
        for row in range(self.ui.tools_table.rowCount()):
            if int(self.ui.tools_table.item(row, 3).text()) == tooluid:
                self.ui.tools_table.selectRow(row)
                break

        # update the UI form
        self.update_ui()

        self.app.inform.emit('[success] %s' % _("New tool added to Tool Table from Tools Database."))

    def on_tool_default_add(self, dia=None, muted=None):
        self.blockSignals(True)
        self.units = self.app.defaults['units'].upper()

        if dia:
            tool_dia = dia
        else:
            tool_dia = self.ui.new_tooldia_entry.get_value()

        if tool_dia is None or tool_dia == 0:
            self.build_ui()
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Please enter a tool diameter with non-zero value, "
                                                          "in Float format."))
            self.blockSignals(False)
            return

        # construct a list of all 'tooluid' in the self.tools
        tool_uid_list = [int(tooluid_key) for tooluid_key in self.ncc_tools]

        # find maximum from the temp_uid, add 1 and this is the new 'tooluid'
        max_uid = 0 if not tool_uid_list else max(tool_uid_list)
        self.tooluid = int(max_uid + 1)

        tool_dias = []
        for k, v in self.ncc_tools.items():
            for tool_v in v.keys():
                if tool_v == 'tooldia':
                    tool_dias.append(float('%.*f' % (self.decimals, (v[tool_v]))))

        truncated_tooldia = self.app.dec_format(tool_dia, self.decimals)
        if truncated_tooldia in tool_dias:
            if muted is None:
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled. Tool already in Tool Table."))
            # self.ui.tools_table.itemChanged.connect(self.on_tool_edit)
            self.blockSignals(False)
            return

        self.ncc_tools.update({
            int(self.tooluid): {
                'tooldia':          truncated_tooldia,
                'offset':           'Path',
                'offset_value':     0.0,
                'type':             'Iso',
                'tool_type':        deepcopy(self.app.defaults["tools_ncc_tool_type"]),
                'data':             deepcopy(self.default_data),
                'solid_geometry':   []
            }
        })

        self.blockSignals(False)
        self.build_ui()

        # select the tool just added
        for row in range(self.ui.tools_table.rowCount()):
            if int(self.ui.tools_table.item(row, 3).text()) == self.tooluid:
                self.ui.tools_table.selectRow(row)
                break

        # update the UI form
        self.update_ui()

        if muted is None:
            self.app.inform.emit('[success] %s' % _("Default tool added to Tool Table."))

    def on_tool_edit(self, item):
        self.blockSignals(True)

        edited_row = item.row()
        editeduid = int(self.ui.tools_table.item(edited_row, 3).text())
        tool_dias = []

        try:
            new_tool_dia = float(self.ui.tools_table.item(edited_row, 1).text())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                new_tool_dia = float(self.ui.tools_table.item(edited_row, 1).text().replace(',', '.'))
            except ValueError:
                self.app.inform.emit('[ERROR_NOTCL]  %s' % _("Wrong value format entered, use a number."))
                self.blockSignals(False)
                return

        for v in self.ncc_tools.values():
            tool_dias = [float('%.*f' % (self.decimals, v[tool_v])) for tool_v in v.keys() if tool_v == 'tooldia']

        # identify the tool that was edited and get it's tooluid
        if new_tool_dia not in tool_dias:
            self.ncc_tools[editeduid]['tooldia'] = deepcopy(float('%.*f' % (self.decimals, new_tool_dia)))
            self.app.inform.emit('[success] %s' % _("Tool from Tool Table was edited."))
            self.blockSignals(False)
            self.build_ui()
            return

        # identify the old tool_dia and restore the text in tool table
        for k, v in self.ncc_tools.items():
            if k == editeduid:
                old_tool_dia = v['tooldia']
                restore_dia_item = self.ui.tools_table.item(edited_row, 1)
                restore_dia_item.setText(str(old_tool_dia))
                break

        self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled. New diameter value is already in the Tool Table."))
        self.blockSignals(False)
        self.build_ui()

    def on_tool_delete(self, rows_to_delete=None, all_tools=None):
        """
        Will delete a tool in the tool table

        :param rows_to_delete:  which rows to delete; can be a list
        :param all_tools:       delete all tools in the tool table
        :return:
        """
        self.blockSignals(True)

        deleted_tools_list = []

        if all_tools:
            self.ncc_tools.clear()
            self.blockSignals(False)
            self.build_ui()
            return

        if rows_to_delete:
            try:
                for row in rows_to_delete:
                    tooluid_del = int(self.ui.tools_table.item(row, 3).text())
                    deleted_tools_list.append(tooluid_del)
            except TypeError:
                tooluid_del = int(self.ui.tools_table.item(rows_to_delete, 3).text())
                deleted_tools_list.append(tooluid_del)

            for t in deleted_tools_list:
                self.ncc_tools.pop(t, None)

            self.blockSignals(False)
            self.build_ui()
            return

        try:
            if self.ui.tools_table.selectedItems():
                for row_sel in self.ui.tools_table.selectedItems():
                    row = row_sel.row()
                    if row < 0:
                        continue
                    tooluid_del = int(self.ui.tools_table.item(row, 3).text())
                    deleted_tools_list.append(tooluid_del)

                for t in deleted_tools_list:
                    self.ncc_tools.pop(t, None)

        except AttributeError:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Delete failed. Select a tool to delete."))
            self.blockSignals(False)
            return
        except Exception as e:
            log.debug(str(e))

        self.app.inform.emit('[success] %s' % _("Tool(s) deleted from Tool Table."))
        self.blockSignals(False)
        self.build_ui()

    def on_ncc_click(self):
        """
        Slot for clicking signal
        :return: None
        """

        self.app.defaults.report_usage("on_ncc_click")

        self.first_click = False
        self.cursor_pos = None
        self.mouse_is_dragging = False

        prog_plot = True if self.app.defaults["tools_ncc_plotting"] == 'progressive' else False
        if prog_plot:
            self.temp_shapes.clear(update=True)

        self.sel_rect = []

        obj_type = self.ui.type_obj_radio.get_value
        self.circle_steps = int(self.app.defaults["gerber_circle_steps"]) if obj_type == 'gerber' else \
            int(self.app.defaults["geometry_circle_steps"])
        self.obj_name = self.ui.object_combo.currentText()

        # Get source object.
        try:
            self.ncc_obj = self.app.collection.get_by_name(self.obj_name)
        except Exception as e:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"),  str(self.obj_name)))
            return "Could not retrieve object: %s with error: %s" % (self.obj_name, str(e))

        if self.ncc_obj is None:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Object not found"), str(self.obj_name)))
            return

        if self.ui.valid_cb.get_value() is True:
            # this is done in another Process
            self.find_safe_tooldia_multiprocessing()

        # use the selected tools in the tool table; get diameters for isolation
        self.iso_dia_list = []
        # use the selected tools in the tool table; get diameters for non-copper clear
        self.ncc_dia_list = []

        table_items = self.ui.tools_table.selectedItems()
        sel_rows = {t.row() for t in table_items}
        if len(sel_rows) > 0:
            for row in sel_rows:
                try:
                    self.tooldia = float(self.ui.tools_table.item(row, 1).text())
                except ValueError:
                    # try to convert comma to decimal point. if it's still not working error message and return
                    try:
                        self.tooldia = float(self.ui.tools_table.item(row, 1).text().replace(',', '.'))
                    except ValueError:
                        self.app.inform.emit('[ERROR_NOTCL] %s' % _("Wrong value format entered, use a number."))
                        continue

                # find out which tools is for isolation and which are for copper clearing
                for uid_k, uid_v in self.ncc_tools.items():
                    if round(uid_v['tooldia'], self.decimals) == round(self.tooldia, self.decimals):
                        if uid_v['data']['tools_ncc_operation'] == "iso":
                            self.iso_dia_list.append(self.tooldia)
                        else:
                            self.ncc_dia_list.append(self.tooldia)
        else:
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("There are no tools selected in the Tool Table."))
            return

        self.o_name = '%s_ncc' % self.obj_name

        self.select_method = self.ui.select_combo.get_value()
        if self.select_method == 0:   # Itself
            self.bound_obj_name = self.ui.object_combo.currentText()
            # Get source object.
            try:
                self.bound_obj = self.app.collection.get_by_name(self.bound_obj_name)
            except Exception as e:
                self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), self.bound_obj_name))
                return "Could not retrieve object: %s with error: %s" % (self.bound_obj_name, str(e))

            self.clear_copper(ncc_obj=self.ncc_obj,
                              ncctooldia=self.ncc_dia_list,
                              isotooldia=self.iso_dia_list,
                              outname=self.o_name,
                              tools_storage=self.ncc_tools)
        elif self.select_method == 1:   # Area Selection
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Click the start point of the area."))

            if self.app.is_legacy is False:
                self.app.plotcanvas.graph_event_disconnect('mouse_press', self.app.on_mouse_click_over_plot)
                self.app.plotcanvas.graph_event_disconnect('mouse_move', self.app.on_mouse_move_over_plot)
                self.app.plotcanvas.graph_event_disconnect('mouse_release', self.app.on_mouse_click_release_over_plot)
            else:
                self.app.plotcanvas.graph_event_disconnect(self.app.mp)
                self.app.plotcanvas.graph_event_disconnect(self.app.mm)
                self.app.plotcanvas.graph_event_disconnect(self.app.mr)

            self.mr = self.app.plotcanvas.graph_event_connect('mouse_release', self.on_mouse_release)
            self.mm = self.app.plotcanvas.graph_event_connect('mouse_move', self.on_mouse_move)
            self.kp = self.app.plotcanvas.graph_event_connect('key_press', self.on_key_press)

            # disconnect flags
            self.area_sel_disconnect_flag = True

        elif self.select_method == 2:   # Reference Object
            self.bound_obj_name = self.ui.reference_combo.currentText()
            # Get source object.
            try:
                self.bound_obj = self.app.collection.get_by_name(self.bound_obj_name)
            except Exception as e:
                self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), self.bound_obj_name))
                return "Could not retrieve object: %s. Error: %s" % (self.bound_obj_name, str(e))

            self.clear_copper(ncc_obj=self.ncc_obj,
                              sel_obj=self.bound_obj,
                              ncctooldia=self.ncc_dia_list,
                              isotooldia=self.iso_dia_list,
                              outname=self.o_name)

    # To be called after clicking on the plot.
    def on_mouse_release(self, event):
        if self.app.is_legacy is False:
            event_pos = event.pos
            # event_is_dragging = event.is_dragging
            right_button = 2
        else:
            event_pos = (event.xdata, event.ydata)
            # event_is_dragging = self.app.plotcanvas.is_dragging
            right_button = 3

        event_pos = self.app.plotcanvas.translate_coords(event_pos)
        if self.app.grid_status():
            curr_pos = self.app.geo_editor.snap(event_pos[0], event_pos[1])
        else:
            curr_pos = (event_pos[0], event_pos[1])

        x1, y1 = curr_pos[0], curr_pos[1]

        shape_type = self.ui.area_shape_radio.get_value()

        # do clear area only for left mouse clicks
        if event.button == 1:
            if shape_type == "square":
                if self.first_click is False:
                    self.first_click = True
                    self.app.inform.emit('[WARNING_NOTCL] %s' % _("Click the end point of the area."))

                    self.cursor_pos = self.app.plotcanvas.translate_coords(event_pos)
                    if self.app.grid_status():
                        self.cursor_pos = self.app.geo_editor.snap(event_pos[0], event_pos[1])
                else:
                    self.app.inform.emit(_("Zone added. Click to start adding next zone or right click to finish."))
                    self.app.delete_selection_shape()

                    x0, y0 = self.cursor_pos[0], self.cursor_pos[1]

                    pt1 = (x0, y0)
                    pt2 = (x1, y0)
                    pt3 = (x1, y1)
                    pt4 = (x0, y1)

                    new_rectangle = Polygon([pt1, pt2, pt3, pt4])
                    self.sel_rect.append(new_rectangle)

                    # add a temporary shape on canvas
                    self.draw_tool_selection_shape(old_coords=(x0, y0), coords=(x1, y1))

                    self.first_click = False
                    return
            else:
                self.points.append((x1, y1))

                if len(self.points) > 1:
                    self.poly_drawn = True
                    self.app.inform.emit(_("Click on next Point or click right mouse button to complete ..."))

                return ""
        elif event.button == right_button and self.mouse_is_dragging is False:

            shape_type = self.ui.area_shape_radio.get_value()

            if shape_type == "square":
                self.first_click = False
            else:
                # if we finish to add a polygon
                if self.poly_drawn is True:
                    try:
                        # try to add the point where we last clicked if it is not already in the self.points
                        last_pt = (x1, y1)
                        if last_pt != self.points[-1]:
                            self.points.append(last_pt)
                    except IndexError:
                        pass

                    # we need to add a Polygon and a Polygon can be made only from at least 3 points
                    if len(self.points) > 2:
                        self.delete_moving_selection_shape()
                        pol = Polygon(self.points)
                        # do not add invalid polygons even if they are drawn by utility geometry
                        if pol.is_valid:
                            self.sel_rect.append(pol)
                            self.draw_selection_shape_polygon(points=self.points)
                            self.app.inform.emit(
                                _("Zone added. Click to start adding next zone or right click to finish."))

                    self.points = []
                    self.poly_drawn = False
                    return

            self.delete_tool_selection_shape()

            if self.app.is_legacy is False:
                self.app.plotcanvas.graph_event_disconnect('mouse_release', self.on_mouse_release)
                self.app.plotcanvas.graph_event_disconnect('mouse_move', self.on_mouse_move)
                self.app.plotcanvas.graph_event_disconnect('key_press', self.on_key_press)
            else:
                self.app.plotcanvas.graph_event_disconnect(self.mr)
                self.app.plotcanvas.graph_event_disconnect(self.mm)
                self.app.plotcanvas.graph_event_disconnect(self.kp)

            self.app.mp = self.app.plotcanvas.graph_event_connect('mouse_press',
                                                                  self.app.on_mouse_click_over_plot)
            self.app.mm = self.app.plotcanvas.graph_event_connect('mouse_move',
                                                                  self.app.on_mouse_move_over_plot)
            self.app.mr = self.app.plotcanvas.graph_event_connect('mouse_release',
                                                                  self.app.on_mouse_click_release_over_plot)

            # disconnect flags
            self.area_sel_disconnect_flag = False

            if len(self.sel_rect) == 0:
                return

            self.sel_rect = unary_union(self.sel_rect)

            self.clear_copper(ncc_obj=self.ncc_obj, sel_obj=self.bound_obj, ncctooldia=self.ncc_dia_list,
                              isotooldia=self.iso_dia_list, outname=self.o_name)

    # called on mouse move
    def on_mouse_move(self, event):
        shape_type = self.ui.area_shape_radio.get_value()

        if self.app.is_legacy is False:
            event_pos = event.pos
            event_is_dragging = event.is_dragging
            # right_button = 2
        else:
            event_pos = (event.xdata, event.ydata)
            event_is_dragging = self.app.plotcanvas.is_dragging
            # right_button = 3

        curr_pos = self.app.plotcanvas.translate_coords(event_pos)

        # detect mouse dragging motion
        if event_is_dragging is True:
            self.mouse_is_dragging = True
        else:
            self.mouse_is_dragging = False

        # update the cursor position
        if self.app.grid_status():
            # Update cursor
            curr_pos = self.app.geo_editor.snap(curr_pos[0], curr_pos[1])

            self.app.app_cursor.set_data(np.asarray([(curr_pos[0], curr_pos[1])]),
                                         symbol='++', edge_color=self.app.cursor_color_3D,
                                         edge_width=self.app.defaults["global_cursor_width"],
                                         size=self.app.defaults["global_cursor_size"])

        if self.cursor_pos is None:
            self.cursor_pos = (0, 0)

        self.app.dx = curr_pos[0] - float(self.cursor_pos[0])
        self.app.dy = curr_pos[1] - float(self.cursor_pos[1])

        # # update the positions on status bar
        self.app.ui.position_label.setText("&nbsp;<b>X</b>: %.4f&nbsp;&nbsp;   "
                                           "<b>Y</b>: %.4f&nbsp;" % (curr_pos[0], curr_pos[1]))
        self.app.ui.rel_position_label.setText("<b>Dx</b>: %.4f&nbsp;&nbsp;  <b>Dy</b>: "
                                               "%.4f&nbsp;&nbsp;&nbsp;&nbsp;" % (self.app.dx, self.app.dy))

        units = self.app.defaults["units"].lower()
        self.app.plotcanvas.text_hud.text = \
            'Dx:\t{:<.4f} [{:s}]\nDy:\t{:<.4f} [{:s}]\n\nX:  \t{:<.4f} [{:s}]\nY:  \t{:<.4f} [{:s}]'.format(
                self.app.dx, units, self.app.dy, units, curr_pos[0], units, curr_pos[1], units)

        # draw the utility geometry
        if shape_type == "square":
            if self.first_click:
                self.app.delete_selection_shape()
                self.app.draw_moving_selection_shape(old_coords=(self.cursor_pos[0], self.cursor_pos[1]),
                                                     coords=(curr_pos[0], curr_pos[1]))
        else:
            self.delete_moving_selection_shape()
            self.draw_moving_selection_shape_poly(points=self.points, data=(curr_pos[0], curr_pos[1]))

    def on_key_press(self, event):
        # modifiers = QtWidgets.QApplication.keyboardModifiers()
        # matplotlib_key_flag = False

        # events out of the self.app.collection view (it's about Project Tab) are of type int
        if type(event) is int:
            key = event
        # events from the GUI are of type QKeyEvent
        elif type(event) == QtGui.QKeyEvent:
            key = event.key()
        elif isinstance(event, mpl_key_event):  # MatPlotLib key events are trickier to interpret than the rest
            # matplotlib_key_flag = True

            key = event.key
            key = QtGui.QKeySequence(key)

            # check for modifiers
            key_string = key.toString().lower()
            if '+' in key_string:
                mod, __, key_text = key_string.rpartition('+')
                if mod.lower() == 'ctrl':
                    # modifiers = QtCore.Qt.ControlModifier
                    pass
                elif mod.lower() == 'alt':
                    # modifiers = QtCore.Qt.AltModifier
                    pass
                elif mod.lower() == 'shift':
                    # modifiers = QtCore.Qt.ShiftModifier
                    pass
                else:
                    # modifiers = QtCore.Qt.NoModifier
                    pass
                key = QtGui.QKeySequence(key_text)

        # events from Vispy are of type KeyEvent
        else:
            key = event.key

        if key == QtCore.Qt.Key_Escape or key == 'Escape':

            if self.area_sel_disconnect_flag is True:
                if self.app.is_legacy is False:
                    self.app.plotcanvas.graph_event_disconnect('mouse_release', self.on_mouse_release)
                    self.app.plotcanvas.graph_event_disconnect('mouse_move', self.on_mouse_move)
                    self.app.plotcanvas.graph_event_disconnect('key_press', self.on_key_press)
                else:
                    self.app.plotcanvas.graph_event_disconnect(self.mr)
                    self.app.plotcanvas.graph_event_disconnect(self.mm)
                    self.app.plotcanvas.graph_event_disconnect(self.kp)

                try:
                    # restore the Grid snapping if it was active before
                    if self.grid_status_memory is True:
                        self.app.ui.grid_snap_btn.trigger()

                    if self.app.is_legacy is False:
                        self.app.plotcanvas.graph_event_disconnect('mouse_release', self.on_single_poly_mouse_release)
                        self.app.plotcanvas.graph_event_disconnect('key_press', self.on_key_press)
                    else:
                        self.app.plotcanvas.graph_event_disconnect(self.mr)
                        self.app.plotcanvas.graph_event_disconnect(self.kp)

                    self.app.tool_shapes.clear(update=True)
                except Exception as e:
                    log.debug("ToolPaint.on_key_press() _2 --> %s" % str(e))

                self.app.mp = self.app.plotcanvas.graph_event_connect('mouse_press',
                                                                      self.app.on_mouse_click_over_plot)
                self.app.mm = self.app.plotcanvas.graph_event_connect('mouse_move',
                                                                      self.app.on_mouse_move_over_plot)
                self.app.mr = self.app.plotcanvas.graph_event_connect('mouse_release',
                                                                      self.app.on_mouse_click_release_over_plot)
            self.points = []
            self.poly_drawn = False

            self.delete_moving_selection_shape()
            self.delete_tool_selection_shape()

    def calculate_bounding_box(self, ncc_obj, ncc_select, box_obj=None):
        """
        Will return a geometry that dictate the total extent of the area to be copper cleared

        :param ncc_obj:     The object to be copper cleared
        :param box_obj:     The object whose geometry will be used as delimitation for copper clearing - if selected
        :param ncc_select:  String that choose what kind of reference to be used for copper clearing extent
        :return:            The geometry that surrounds the area to be cleared and the kind of object from which the
                            geometry originated (string: "gerber", "geometry" or None)
        """
        box_kind = box_obj.kind if box_obj is not None else None

        env_obj = None
        if ncc_select == 0:     # _('Itself')
            geo_n = ncc_obj.solid_geometry

            try:
                if isinstance(geo_n, MultiPolygon):
                    env_obj = geo_n.convex_hull
                elif (isinstance(geo_n, MultiPolygon) and len(geo_n) == 1) or \
                        (isinstance(geo_n, list) and len(geo_n) == 1) and isinstance(geo_n[0], Polygon):
                    env_obj = unary_union(geo_n)
                else:
                    env_obj = unary_union(geo_n)
                    env_obj = env_obj.convex_hull
            except Exception as e:
                log.debug("NonCopperClear.calculate_bounding_box() 'itself'  --> %s" % str(e))
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("No object available."))
                return None
        elif ncc_select == 1:   # _("Area Selection")
            env_obj = unary_union(self.sel_rect)
            try:
                __ = iter(env_obj)
            except Exception:
                env_obj = [env_obj]
        elif ncc_select == 2:   # _("Reference Object")
            if box_obj is None:
                return None, None

            box_geo = box_obj.solid_geometry
            if box_kind == 'geometry':
                try:
                    __ = iter(box_geo)
                    env_obj = box_geo
                except Exception:
                    env_obj = [box_geo]

            elif box_kind == 'gerber':
                box_geo = unary_union(box_obj.solid_geometry).convex_hull
                ncc_geo = unary_union(ncc_obj.solid_geometry).convex_hull
                env_obj = ncc_geo.intersection(box_geo)
            else:
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("The reference object type is not supported."))
                return 'fail'

        return env_obj, box_kind

    def apply_margin_to_bounding_box(self, bbox, box_kind, ncc_select, ncc_margin):
        """
        Prepare non-copper polygons.
        Apply a margin to  the bounding box area from which the copper features will be subtracted

        :param bbox:        the Geometry to be used as bounding box after applying the ncc_margin
        :param box_kind:    "geometry" or "gerber"
        :param ncc_select:  the kind of area to be copper cleared
        :param ncc_margin:  the margin around the area to be copper cleared
        :return:            an geometric element (Polygon or MultiPolygon) that specify the area to be copper cleared
        """

        log.debug("NCC Tool. Preparing non-copper polygons.")
        self.app.inform.emit(_("NCC Tool. Preparing non-copper polygons."))

        if bbox is None:
            log.debug("NonCopperClear.apply_margin_to_bounding_box() --> The object is None")
            return 'fail'

        new_bounding_box = None
        if ncc_select == 0:     # _('Itself')
            try:
                new_bounding_box = bbox.buffer(distance=ncc_margin, join_style=base.JOIN_STYLE.mitre)
            except Exception as e:
                log.debug("NonCopperClear.apply_margin_to_bounding_box() 'itself'  --> %s" % str(e))
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("No object available."))
                return 'fail'
        elif ncc_select == 1:   # _("Area Selection")
            geo_buff_list = []
            for poly in bbox:
                if self.app.abort_flag:
                    # graceful abort requested by the user
                    raise grace
                geo_buff_list.append(poly.buffer(distance=ncc_margin, join_style=base.JOIN_STYLE.mitre))
            new_bounding_box = unary_union(geo_buff_list)
        elif ncc_select == 2:   # _("Reference Object")
            if box_kind == 'geometry':
                geo_buff_list = []
                for poly in bbox:
                    if self.app.abort_flag:
                        # graceful abort requested by the user
                        raise grace
                    geo_buff_list.append(poly.buffer(distance=ncc_margin, join_style=base.JOIN_STYLE.mitre))

                new_bounding_box = unary_union(geo_buff_list)
            elif box_kind == 'gerber':
                new_bounding_box = bbox.buffer(distance=ncc_margin, join_style=base.JOIN_STYLE.mitre)
            else:
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("The reference object type is not supported."))
                return 'fail'

        log.debug("NCC Tool. Finished non-copper polygons.")
        return new_bounding_box

    def get_tool_empty_area(self, name, ncc_obj, geo_obj, isotooldia, has_offset, ncc_offset, ncc_margin,
                            bounding_box, tools_storage, work_geo=None):
        """
        Calculate the empty area by subtracting the solid_geometry from the object bounding box geometry.

        :param name:
        :param ncc_obj:
        :param geo_obj:
        :param isotooldia:
        :param has_offset:
        :param ncc_offset:
        :param ncc_margin:
        :param bounding_box:    only this area is kept
        :param tools_storage:
        :param work_geo:        if provided use this geometry to generate the empty area
        :return:
        """

        log.debug("NCC Tool. Calculate 'empty' area.")
        self.app.inform.emit(_("NCC Tool. Calculate 'empty' area."))

        # a flag to signal that the isolation is broken by the bounding box in 'area' and 'box' cases
        # will store the number of tools for which the isolation is broken
        warning_flag = 0

        if work_geo:
            sol_geo = work_geo
            if has_offset is True:
                self.app.inform.emit('[WARNING_NOTCL] %s ...' % _("Buffering"))
                sol_geo = sol_geo.buffer(distance=ncc_offset)
                self.app.inform.emit('[success] %s ...' % _("Buffering finished"))
            empty = self.get_ncc_empty_area(target=sol_geo, boundary=bounding_box)

            if empty == 'fail' or empty.is_empty:
                msg = '[ERROR_NOTCL] %s' % _("Could not get the extent of the area to be non copper cleared.")
                self.app.inform.emit(msg)
                return 'fail'

            if type(empty) is Polygon:
                empty = MultiPolygon([empty])

            log.debug("NCC Tool. Finished calculation of 'empty' area.")
            self.app.inform.emit(_("NCC Tool. Finished calculation of 'empty' area."))

            return empty, warning_flag

        if ncc_obj.kind == 'gerber' and not isotooldia:
            # unfortunately for this function to work time efficient,
            # if the Gerber was loaded without buffering then it require the buffering now.
            if self.app.defaults['gerber_buffering'] == 'no':
                sol_geo = ncc_obj.solid_geometry.buffer(0)
            else:
                sol_geo = ncc_obj.solid_geometry

            if has_offset is True:
                self.app.inform.emit('[WARNING_NOTCL] %s ...' % _("Buffering"))
                if isinstance(sol_geo, list):
                    sol_geo = MultiPolygon(sol_geo)
                sol_geo = sol_geo.buffer(distance=ncc_offset)
                self.app.inform.emit('[success] %s ...' % _("Buffering finished"))

            empty = self.get_ncc_empty_area(target=sol_geo, boundary=bounding_box)
            if empty == 'fail' or empty.is_empty:
                msg = '[ERROR_NOTCL] %s' % _("Could not get the extent of the area to be non copper cleared.")
                self.app.inform.emit(msg)
                return 'fail'

        elif ncc_obj.kind == 'gerber' and isotooldia:
            isolated_geo = []

            # unfortunately for this function to work time efficient,
            # if the Gerber was loaded without buffering then it require the buffering now.
            # TODO 'buffering status' should be a property of the object not the project property
            if self.app.defaults['gerber_buffering'] == 'no':
                self.solid_geometry = ncc_obj.solid_geometry.buffer(0)
            else:
                self.solid_geometry = ncc_obj.solid_geometry

            # if milling type is climb then the move is counter-clockwise around features
            milling_type = self.ui.milling_type_radio.get_value()

            for tool_iso in isotooldia:
                new_geometry = []

                if milling_type == 'cl':
                    isolated_geo = self.generate_envelope(tool_iso / 2, 1)
                else:
                    isolated_geo = self.generate_envelope(tool_iso / 2, 0)

                if isolated_geo == 'fail' or isolated_geo.is_empty:
                    self.app.inform.emit('[ERROR_NOTCL] %s %s' %
                                         (_("Isolation geometry could not be generated."), str(tool_iso)))
                    continue

                if ncc_margin < tool_iso:
                    self.app.inform.emit('[WARNING_NOTCL] %s' % _("Isolation geometry is broken. Margin is less "
                                                                  "than isolation tool diameter."))
                try:
                    for geo_elem in isolated_geo:
                        # provide the app with a way to process the GUI events when in a blocking loop
                        QtWidgets.QApplication.processEvents()

                        if self.app.abort_flag:
                            # graceful abort requested by the user
                            raise grace

                        if isinstance(geo_elem, Polygon):
                            for ring in self.poly2rings(geo_elem):
                                new_geo = ring.intersection(bounding_box)
                                if new_geo and not new_geo.is_empty:
                                    new_geometry.append(new_geo)
                        elif isinstance(geo_elem, MultiPolygon):
                            for poly in geo_elem:
                                for ring in self.poly2rings(poly):
                                    new_geo = ring.intersection(bounding_box)
                                    if new_geo and not new_geo.is_empty:
                                        new_geometry.append(new_geo)
                        elif isinstance(geo_elem, LineString):
                            new_geo = geo_elem.intersection(bounding_box)
                            if new_geo:
                                if not new_geo.is_empty:
                                    new_geometry.append(new_geo)
                        elif isinstance(geo_elem, MultiLineString):
                            for line_elem in geo_elem:
                                new_geo = line_elem.intersection(bounding_box)
                                if new_geo and not new_geo.is_empty:
                                    new_geometry.append(new_geo)
                except TypeError:
                    if isinstance(isolated_geo, Polygon):
                        for ring in self.poly2rings(isolated_geo):
                            new_geo = ring.intersection(bounding_box)
                            if new_geo:
                                if not new_geo.is_empty:
                                    new_geometry.append(new_geo)
                    elif isinstance(isolated_geo, LineString):
                        new_geo = isolated_geo.intersection(bounding_box)
                        if new_geo and not new_geo.is_empty:
                            new_geometry.append(new_geo)
                    elif isinstance(isolated_geo, MultiLineString):
                        for line_elem in isolated_geo:
                            new_geo = line_elem.intersection(bounding_box)
                            if new_geo and not new_geo.is_empty:
                                new_geometry.append(new_geo)

                # a MultiLineString geometry element will show that the isolation is broken for this tool
                for geo_e in new_geometry:
                    if type(geo_e) == MultiLineString:
                        warning_flag += 1
                        break

                for k, v in tools_storage.items():
                    if float('%.*f' % (self.decimals, v['tooldia'])) == float('%.*f' % (self.decimals,
                                                                                        tool_iso)):
                        current_uid = int(k)
                        # add the solid_geometry to the current too in self.paint_tools dictionary
                        # and then reset the temporary list that stored that solid_geometry
                        v['solid_geometry'] = deepcopy(new_geometry)
                        v['data']['name'] = name
                        geo_obj.tools[current_uid] = dict(tools_storage[current_uid])
                        break

            sol_geo = unary_union(isolated_geo)
            if has_offset is True:
                self.app.inform.emit('[WARNING_NOTCL] %s ...' % _("Buffering"))
                sol_geo = sol_geo.buffer(distance=ncc_offset)
                self.app.inform.emit('[success] %s ...' % _("Buffering finished"))

            empty = self.get_ncc_empty_area(target=sol_geo, boundary=bounding_box)
            if empty == 'fail' or empty.is_empty:
                msg = '[ERROR_NOTCL] %s' % _("Could not get the extent of the area to be non copper cleared.")
                self.app.inform.emit(msg)
                return 'fail'

        elif ncc_obj.kind == 'geometry':
            sol_geo = unary_union(ncc_obj.solid_geometry)
            if has_offset is True:
                self.app.inform.emit('[WARNING_NOTCL] %s ...' % _("Buffering"))
                sol_geo = sol_geo.buffer(distance=ncc_offset)
                self.app.inform.emit('[success] %s ...' % _("Buffering finished"))
            empty = self.get_ncc_empty_area(target=sol_geo, boundary=bounding_box)
            if empty == 'fail' or empty.is_empty:
                msg = '[ERROR_NOTCL] %s' % _("Could not get the extent of the area to be non copper cleared.")
                self.app.inform.emit(msg)
                return 'fail'
        else:
            self.app.inform.emit('[ERROR_NOTCL] %s' % _('The selected object is not suitable for copper clearing.'))
            return 'fail'

        if type(empty) is Polygon:
            empty = MultiPolygon([empty])

        log.debug("NCC Tool. Finished calculation of 'empty' area.")
        self.app.inform.emit(_("NCC Tool. Finished calculation of 'empty' area."))

        return empty, warning_flag

    def clear_polygon_worker(self, pol, tooldia, ncc_method, ncc_overlap, ncc_connect, ncc_contour, prog_plot):

        cp = None

        if ncc_method == 0:     # standard
            try:
                cp = self.clear_polygon(pol, tooldia,
                                        steps_per_circle=self.circle_steps,
                                        overlap=ncc_overlap, contour=ncc_contour,
                                        connect=ncc_connect,
                                        prog_plot=prog_plot)
            except grace:
                return "fail"
            except Exception as ee:
                log.debug("NonCopperClear.clear_polygon_worker() Standard --> %s" % str(ee))
        elif ncc_method == 1:   # seed
            try:
                cp = self.clear_polygon2(pol, tooldia,
                                         steps_per_circle=self.circle_steps,
                                         overlap=ncc_overlap, contour=ncc_contour,
                                         connect=ncc_connect,
                                         prog_plot=prog_plot)
            except grace:
                return "fail"
            except Exception as ee:
                log.debug("NonCopperClear.clear_polygon_worker() Seed --> %s" % str(ee))
        elif ncc_method == 2:   # Lines
            try:
                cp = self.clear_polygon3(pol, tooldia,
                                         steps_per_circle=self.circle_steps,
                                         overlap=ncc_overlap, contour=ncc_contour,
                                         connect=ncc_connect,
                                         prog_plot=prog_plot)
            except grace:
                return "fail"
            except Exception as ee:
                log.debug("NonCopperClear.clear_polygon_worker() Lines --> %s" % str(ee))
        elif ncc_method == 3:   # Combo
            try:
                self.app.inform.emit(_("Clearing the polygon with the method: lines."))
                cp = self.clear_polygon3(pol, tooldia,
                                         steps_per_circle=self.circle_steps,
                                         overlap=ncc_overlap, contour=ncc_contour,
                                         connect=ncc_connect,
                                         prog_plot=prog_plot)

                if cp and cp.objects:
                    pass
                else:
                    self.app.inform.emit(_("Failed. Clearing the polygon with the method: seed."))
                    cp = self.clear_polygon2(pol, tooldia,
                                             steps_per_circle=self.circle_steps,
                                             overlap=ncc_overlap, contour=ncc_contour,
                                             connect=ncc_connect,
                                             prog_plot=prog_plot)
                    if cp and cp.objects:
                        pass
                    else:
                        self.app.inform.emit(_("Failed. Clearing the polygon with the method: standard."))
                        cp = self.clear_polygon(pol, tooldia,
                                                steps_per_circle=self.circle_steps,
                                                overlap=ncc_overlap, contour=ncc_contour,
                                                connect=ncc_connect,
                                                prog_plot=prog_plot)
            except grace:
                return "fail"
            except Exception as ee:
                log.debug("NonCopperClear.clear_polygon_worker() Combo --> %s" % str(ee))

        if cp and cp.objects:
            return list(cp.get_objects())
        else:
            pt = pol.representative_point()
            coords = (pt.x, pt.y)
            self.app.inform_shell.emit('%s %s' % (_('Polygon could not be cleared. Location:'), str(coords)))
            return None

    def clear_copper(self, ncc_obj, ncctooldia, isotooldia, sel_obj=None, outname=None, order=None,
                     tools_storage=None, run_threaded=True):
        """
        Clear the excess copper from the entire object.

        :param ncc_obj:         ncc cleared object
        :type ncc_obj:          appObjects.FlatCAMGerber.GerberObject
        :param ncctooldia:      a list of diameters of the tools to be used to ncc clear
        :type ncctooldia:       list
        :param isotooldia:      a list of diameters of the tools to be used for isolation
        :type isotooldia:       list
        :param sel_obj:
        :type sel_obj:
        :param outname:         name of the resulting object
        :type outname:          str
        :param order:           Tools order
        :param tools_storage:   whether to use the current tools_storage self.ncc_tools or a different one.
                                Usage of the different one is related to when this function is called
                                from a TcL command.
        :type tools_storage:    dict

        :param run_threaded:    If True the method will be run in a threaded way suitable for GUI usage; if False
                                it will run non-threaded for TclShell usage
        :type run_threaded:     bool
        :return:
        """
        log.debug("Executing the handler ...")

        if run_threaded:
            proc = self.app.proc_container.new('%s...' % _("Non-Copper Clearing"))
        else:
            self.app.proc_container.view.set_busy('%s...' % _("Non-Copper Clearing"))
            QtWidgets.QApplication.processEvents()

        # ######################################################################################################
        # ######################### Read the parameters ########################################################
        # ######################################################################################################

        units = self.app.defaults['units']
        order = order if order else self.ui.ncc_order_radio.get_value()
        ncc_select = self.ui.select_combo.get_value()
        rest_machining_choice = self.ui.ncc_rest_cb.get_value()

        # determine if to use the progressive plotting
        prog_plot = True if self.app.defaults["tools_ncc_plotting"] == 'progressive' else False

        tools_storage = tools_storage if tools_storage is not None else self.ncc_tools
        sorted_clear_tools = ncctooldia

        if not sorted_clear_tools:
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("There is no copper clearing tool in the selection "
                                                        "and at least one is needed."))
            return 'fail'

        # ########################################################################################################
        # set the name for the future Geometry object
        # I do it here because it is also stored inside the gen_clear_area() and gen_clear_area_rest() methods
        # ########################################################################################################
        name = outname if outname is not None else self.obj_name + "_ncc"

        # ########################################################################################################
        # ######### #####Initializes the new geometry object #####################################################
        # ########################################################################################################
        def gen_clear_area(geo_obj, app_obj):
            log.debug("NCC Tool. Normal copper clearing task started.")
            self.app.inform.emit(_("NCC Tool. Finished non-copper polygons. Normal copper clearing task started."))

            # provide the app with a way to process the GUI events when in a blocking loop
            if not run_threaded:
                QtWidgets.QApplication.processEvents()

            # a flag to signal that the isolation is broken by the bounding box in 'area' and 'box' cases
            # will store the number of tools for which the isolation is broken
            warning_flag = 0

            tool = None

            if order == 'fwd':
                sorted_clear_tools.sort(reverse=False)
            elif order == 'rev':
                sorted_clear_tools.sort(reverse=True)
            else:
                pass

            app_obj.poly_not_cleared = False    # flag for polygons not cleared

            if ncc_select == 2:     # Reference Object
                bbox_geo, bbox_kind = self.calculate_bounding_box(
                    ncc_obj=ncc_obj, box_obj=sel_obj, ncc_select=ncc_select)
            else:
                bbox_geo, bbox_kind = self.calculate_bounding_box(ncc_obj=ncc_obj, ncc_select=ncc_select)

            if bbox_geo is None and bbox_kind is None:
                self.app.inform.emit("[ERROR_NOTCL] %s" % _("NCC Tool failed creating bounding box."))
                return "fail"

            # Bounding box for current tool
            ncc_margin = self.ui.ncc_margin_entry.get_value()
            bbox = self.apply_margin_to_bounding_box(bbox=bbox_geo, box_kind=bbox_kind,
                                                     ncc_select=ncc_select, ncc_margin=ncc_margin)

            # COPPER CLEARING with tools marked for CLEAR#
            for tool in sorted_clear_tools:
                log.debug("Starting geometry processing for tool: %s" % str(tool))
                if self.app.abort_flag:
                    # graceful abort requested by the user
                    raise grace

                # provide the app with a way to process the GUI events when in a blocking loop
                if not run_threaded:
                    QtWidgets.QApplication.processEvents()

                app_obj.inform.emit('[success] %s = %s%s %s' % (
                    _('NCC Tool clearing with tool diameter'), str(tool), units.lower(), _('started.'))
                )
                app_obj.proc_container.update_view_text(' %d%%' % 0)

                # store here the geometry generated by clear operation
                cleared_geo = []

                tool_uid = 0    # find the current tool_uid
                for k, v in self.ncc_tools.items():
                    if float('%.*f' % (self.decimals, v['tooldia'])) == float('%.*f' % (self.decimals, tool)):
                        tool_uid = int(k)
                        break

                # parameters that are particular to the current tool
                ncc_overlap = float(self.ncc_tools[tool_uid]["data"]["tools_ncc_overlap"]) / 100.0
                ncc_method = self.ncc_tools[tool_uid]["data"]["tools_ncc_method"]
                ncc_connect = self.ncc_tools[tool_uid]["data"]["tools_ncc_connect"]
                ncc_contour = self.ncc_tools[tool_uid]["data"]["tools_ncc_contour"]
                has_offset = self.ncc_tools[tool_uid]["data"]["tools_ncc_offset_choice"]
                ncc_offset = float(self.ncc_tools[tool_uid]["data"]["tools_ncc_offset_value"])

                # Area to clear
                area, warning_flag = self.get_tool_empty_area(name=name, ncc_obj=ncc_obj, geo_obj=geo_obj,
                                                              isotooldia=isotooldia, ncc_margin=ncc_margin,
                                                              has_offset=has_offset,  ncc_offset=ncc_offset,
                                                              tools_storage=tools_storage, bounding_box=bbox)

                # Transform area to MultiPolygon
                if isinstance(area, Polygon):
                    area = MultiPolygon([area])

                # variables to display the percentage of work done
                geo_len = len(area.geoms)

                old_disp_number = 0
                log.warning("Total number of polygons to be cleared. %s" % str(geo_len))

                if area.geoms:
                    if len(area.geoms) > 0:
                        pol_nr = 0
                        for p in area.geoms:
                            # provide the app with a way to process the GUI events when in a blocking loop
                            if not run_threaded:
                                QtWidgets.QApplication.processEvents()

                            if self.app.abort_flag:
                                # graceful abort requested by the user
                                raise grace

                            # clean the polygon
                            p = p.buffer(0)

                            if p is not None and p.is_valid:
                                poly_failed = 0
                                try:
                                    for pol in p:
                                        # provide the app with a way to process the GUI events when in a blocking loop
                                        QtWidgets.QApplication.processEvents()

                                        if pol is not None and isinstance(pol, Polygon):
                                            res = self.clear_polygon_worker(pol=pol, tooldia=tool,
                                                                            ncc_method=ncc_method,
                                                                            ncc_overlap=ncc_overlap,
                                                                            ncc_connect=ncc_connect,
                                                                            ncc_contour=ncc_contour,
                                                                            prog_plot=prog_plot)
                                            if res is not None:
                                                cleared_geo += res
                                            else:
                                                poly_failed += 1
                                        else:
                                            log.warning("Expected geo is a Polygon. Instead got a %s" % str(type(pol)))
                                except TypeError:
                                    if isinstance(p, Polygon):
                                        res = self.clear_polygon_worker(pol=p, tooldia=tool,
                                                                        ncc_method=ncc_method,
                                                                        ncc_overlap=ncc_overlap,
                                                                        ncc_connect=ncc_connect,
                                                                        ncc_contour=ncc_contour,
                                                                        prog_plot=prog_plot)
                                        if res is not None:
                                            cleared_geo += res
                                        else:
                                            poly_failed += 1
                                    else:
                                        log.warning("Expected geo is a Polygon. Instead got a %s" % str(type(p)))

                                if poly_failed > 0:
                                    app_obj.poly_not_cleared = True

                                pol_nr += 1
                                disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 100]))
                                # log.debug("Polygons cleared: %d" % pol_nr)

                                if old_disp_number < disp_number <= 100:
                                    self.app.proc_container.update_view_text(' %d%%' % disp_number)
                                    old_disp_number = disp_number
                                    # log.debug("Polygons cleared: %d. Percentage done: %d%%" % (pol_nr, disp_number))

                        # check if there is a geometry at all in the cleared geometry
                        if cleared_geo:
                            formatted_tool = self.app.dec_format(tool, self.decimals)
                            # find the tooluid associated with the current tool_dia so we know where to add the tool
                            # solid_geometry
                            for k, v in tools_storage.items():
                                if self.app.dec_format(v['tooldia'], self.decimals) == formatted_tool:
                                    current_uid = int(k)

                                    # add the solid_geometry to the current too in self.paint_tools dictionary
                                    # and then reset the temporary list that stored that solid_geometry
                                    v['solid_geometry'] = deepcopy(cleared_geo)
                                    v['data']['name'] = name
                                    geo_obj.tools[current_uid] = dict(tools_storage[current_uid])
                                    break
                        else:
                            log.debug("There are no geometries in the cleared polygon.")

            # clean the progressive plotted shapes if it was used
            if self.app.defaults["tools_ncc_plotting"] == 'progressive':
                self.temp_shapes.clear(update=True)

            # delete tools with empty geometry
            # look for keys in the tools_storage dict that have 'solid_geometry' values empty
            for uid, uid_val in list(tools_storage.items()):
                try:
                    # if the solid_geometry (type=list) is empty
                    if not uid_val['solid_geometry']:
                        msg = '%s %s: %s %s: %s' % (
                            _("Could not use the tool for copper clear."),
                            _("Tool"),
                            str(uid),
                            _("with diameter"),
                            str(uid_val['tooldia']))
                        self.app.inform.emit(msg)
                        log.debug("Empty geometry for tool: %s with diameter: %s" % (str(uid), str(uid_val['tooldia'])))
                        tools_storage.pop(uid, None)
                except KeyError:
                    tools_storage.pop(uid, None)

            geo_obj.options["cnctooldia"] = str(tool)

            geo_obj.multigeo = True
            geo_obj.tools = dict(tools_storage)

            # test if at least one tool has solid_geometry. If no tool has solid_geometry we raise an Exception
            has_solid_geo = 0
            for tid in geo_obj.tools:
                if geo_obj.tools[tid]['solid_geometry']:
                    has_solid_geo += 1
            if has_solid_geo == 0:
                msg = '[ERROR] %s' % _("There is no NCC Geometry in the file.\n"
                                       "Usually it means that the tool diameter is too big for the painted geometry.\n"
                                       "Change the painting parameters and try again.")
                app_obj.inform.emit(msg)
                return 'fail'

            # check to see if geo_obj.tools is empty
            # it will be updated only if there is a solid_geometry for tools
            if geo_obj.tools:
                if warning_flag == 0:
                    self.app.inform.emit('[success] %s' % _("NCC Tool clear all done."))
                else:
                    self.app.inform.emit('[WARNING] %s: %s %s.' % (
                        _("NCC Tool clear all done but the copper features isolation is broken for"),
                        str(warning_flag),
                        _("tools")))
                    return

                # create the solid_geometry
                geo_obj.solid_geometry = []
                for tool_id in geo_obj.tools:
                    if geo_obj.tools[tool_id]['solid_geometry']:
                        try:
                            for geo in geo_obj.tools[tool_id]['solid_geometry']:
                                geo_obj.solid_geometry.append(geo)
                        except TypeError:
                            geo_obj.solid_geometry.append(geo_obj.tools[tool_id]['solid_geometry'])
            else:
                # I will use this variable for this purpose although it was meant for something else
                # signal that we have no geo in the object therefore don't create it
                app_obj.poly_not_cleared = False
                return "fail"

            # # Experimental...
            # # print("Indexing...", end=' ')
            # # geo_obj.make_index()

        # ###########################################################################################
        # Initializes the new geometry object for the case of the rest-machining ####################
        # ###########################################################################################
        def gen_clear_area_rest(geo_obj, app_obj):
            log.debug("NCC Tool. Rest machining copper clearing task started.")
            app_obj.inform.emit(_("NCC Tool. Rest machining copper clearing task started."))

            # provide the app with a way to process the GUI events when in a blocking loop
            if not run_threaded:
                QtWidgets.QApplication.processEvents()

            sorted_clear_tools.sort(reverse=True)

            # re purposed flag for final object, geo_obj. True if it has any solid_geometry, False if not.
            app_obj.poly_not_cleared = True

            if ncc_select == 2:     # Reference Object
                env_obj, box_obj_kind = self.calculate_bounding_box(
                    ncc_obj=ncc_obj, box_obj=sel_obj, ncc_select=ncc_select)
            else:
                env_obj, box_obj_kind = self.calculate_bounding_box(ncc_obj=ncc_obj, ncc_select=ncc_select)

            if env_obj is None and box_obj_kind is None:
                self.app.inform.emit("[ERROR_NOTCL] %s" % _("NCC Tool failed creating bounding box."))
                return "fail"

            # log.debug("NCC Tool. Calculate 'empty' area.")
            # app_obj.inform.emit("NCC Tool. Calculate 'empty' area.")

            # Bounding box for current tool
            ncc_margin = self.ui.ncc_margin_entry.get_value()
            bbox = self.apply_margin_to_bounding_box(bbox=env_obj, box_kind=box_obj_kind,
                                                     ncc_select=ncc_select, ncc_margin=ncc_margin)

            ncc_connect = self.ui.rest_ncc_connect_cb.get_value()
            ncc_contour = self.ui.rest_ncc_contour_cb.get_value()
            has_offset = self.ui.rest_ncc_choice_offset_cb.get_value()
            ncc_offset = self.ui.rest_ncc_offset_spinner.get_value()

            # Area to clear
            area, warning_flag = self.get_tool_empty_area(name=name, ncc_obj=ncc_obj, geo_obj=geo_obj,
                                                          isotooldia=isotooldia,
                                                          has_offset=has_offset, ncc_offset=ncc_offset,
                                                          ncc_margin=ncc_margin, tools_storage=tools_storage,
                                                          bounding_box=bbox)

            # for testing purposes ----------------------------------
            # for po in area.geoms:
            #     self.app.tool_shapes.add(po, color=self.app.defaults['global_sel_line'],
            #                              face_color=self.app.defaults['global_sel_line'],
            #                              update=True, layer=0, tolerance=None)
            # -------------------------------------------------------

            # Generate area for each tool
            while sorted_clear_tools:
                tool = sorted_clear_tools.pop(0)

                log.debug("Starting geometry processing for tool: %s" % str(tool))
                if self.app.abort_flag:
                    # graceful abort requested by the user
                    raise grace

                # provide the app with a way to process the GUI events when in a blocking loop
                QtWidgets.QApplication.processEvents()

                app_obj.inform.emit('[success] %s = %s%s %s' % (
                    _('NCC Tool clearing with tool diameter'), str(tool), units.lower(), _('started.'))
                )
                app_obj.proc_container.update_view_text(' %d%%' % 0)

                tool_uid = 0    # find the current tool_uid
                for k, v in self.ncc_tools.items():
                    if self.app.dec_format(v['tooldia'], self.decimals) == self.app.dec_format(tool, self.decimals):
                        tool_uid = int(k)
                        break

                tool_data_dict = self.ncc_tools[tool_uid]["data"]

                # parameters that are particular to the current tool
                ncc_overlap = float(tool_data_dict["tools_ncc_overlap"]) / 100.0
                ncc_method = tool_data_dict["tools_ncc_method"]

                # variables to display the percentage of work done
                geo_len = len(area.geoms)
                old_disp_number = 0
                log.warning("Total number of polygons to be cleared: %s" % str(geo_len))

                # def random_color():
                #     r_color = np.random.rand(4)
                #     r_color[3] = 0.5
                #     return r_color

                # store here the geometry generated by clear operation
                cleared_geo = []

                poly_failed = 0
                if area.geoms and len(area.geoms) > 0:
                    pol_nr = 0
                    for p in area.geoms:
                        if self.app.abort_flag:
                            # graceful abort requested by the user
                            raise grace

                        if p is not None and p.is_valid and not p.is_empty:
                            # provide the app with a way to process the GUI events when in a blocking loop
                            QtWidgets.QApplication.processEvents()

                            # speedup the clearing by not trying to clear polygons that is clear they can't be
                            # cleared with the current tool. this tremendously reduce the clearing time
                            check_dist = -tool / 2
                            check_buff = p.buffer(check_dist, self.circle_steps)
                            if not check_buff or check_buff.is_empty:
                                continue

                            # if self.app.dec_format(float(tool), self.decimals) == 0.15:
                            #     # for testing purposes ----------------------------------
                            #     self.app.tool_shapes.add(p, color=self.app.defaults['global_sel_line'],
                            #                              face_color=random_color(),
                            #                              update=True, layer=0, tolerance=None)
                            #     self.app.tool_shapes.add(check_buff, color=self.app.defaults['global_sel_line'],
                            #                              face_color='#FFFFFFFF',
                            #                              update=True, layer=0, tolerance=None)
                            #     # -------------------------------------------------------

                            # actual copper clearing is done here
                            if isinstance(p, Polygon):
                                res = self.clear_polygon_worker(pol=p, tooldia=tool,
                                                                ncc_method=ncc_method,
                                                                ncc_overlap=ncc_overlap,
                                                                ncc_connect=ncc_connect,
                                                                ncc_contour=ncc_contour,
                                                                prog_plot=prog_plot)

                                if res is not None:
                                    cleared_geo += res
                                else:
                                    poly_failed += 1
                            else:
                                log.warning("Expected geo is a Polygon. Instead got a %s" % str(type(p)))

                            if poly_failed > 0:
                                app_obj.poly_not_cleared = True

                            pol_nr += 1
                            disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 100]))
                            # log.debug("Polygons cleared: %d" % pol_nr)

                            if old_disp_number < disp_number <= 100:
                                self.app.proc_container.update_view_text(' %d%%' % disp_number)
                                old_disp_number = disp_number
                                # log.debug("Polygons cleared: %d. Percentage done: %d%%" % (pol_nr, disp_number))

                    if self.app.abort_flag:
                        raise grace     # graceful abort requested by the user

                    # check if there is a geometry at all in the cleared geometry
                    if cleared_geo:
                        tools_storage[tool_uid]["solid_geometry"] = deepcopy(cleared_geo)
                        tools_storage[tool_uid]["data"]["name"] = name + '_' + str(tool)
                        geo_obj.tools[tool_uid] = dict(tools_storage[tool_uid])
                    else:
                        log.debug("There are no geometries in the cleared polygon.")

                    log.warning("Total number of polygons failed to be cleared: %s" % str(poly_failed))
                else:
                    log.warning("The area to be cleared has no polygons.")

                # # Area to clear next
                # try:
                #     # buffered_cleared = unary_union(cleared_geo).buffer(tool / 2.0)
                #     # area = area.difference(buffered_cleared)
                #     area = area.difference(unary_union(cleared_geo))
                # except Exception as e:
                #     log.debug("Creating new area failed due of: %s" % str(e))

                new_area = MultiPolygon([line.buffer(tool / 1.9999999) for line in cleared_geo])
                new_area = new_area.buffer(0.0000001)

                area = area.difference(new_area)

                new_area = [pol for pol in area if pol.is_valid and not pol.is_empty]
                area = MultiPolygon(new_area)

                # speedup the clearing by not trying to clear polygons that is clear they can't be
                # cleared with any tool. this tremendously reduce the clearing time
                # found_poly_to_clear = False
                # for t in sorted_clear_tools:
                #     check_dist = -t / 2.000000001
                #     for pl in area:
                #         check_buff = pl.buffer(check_dist)
                #         if not check_buff or check_buff.is_empty or not check_buff.is_valid:
                #             continue
                #         else:
                #             found_poly_to_clear = True
                #             break
                #     if found_poly_to_clear is True:
                #         break
                #
                # if found_poly_to_clear is False:
                #     log.warning("The area to be cleared no longer has polygons. Finishing.")
                #     break

                if not area or area.is_empty:
                    break

                # # try to clear the polygons
                # buff_distance = 0.0
                # try:
                #     new_area = [p.buffer(buff_distance) for p in area if not p.is_empty]
                # except TypeError:
                #     new_area = [area.buffer(tool * ncc_overlap)]
                # area = unary_union(area)

            geo_obj.multigeo = True
            geo_obj.options["cnctooldia"] = '0.0'

            # clean the progressive plotted shapes if it was used
            if self.app.defaults["tools_ncc_plotting"] == 'progressive':
                self.temp_shapes.clear(update=True)

            # check to see if geo_obj.tools is empty
            # it will be updated only if there is a solid_geometry for tools
            if geo_obj.tools:
                if warning_flag == 0:
                    self.app.inform.emit('[success] %s' % _("NCC Tool Rest Machining clear all done."))
                else:
                    self.app.inform.emit(
                        '[WARNING] %s: %s %s.' % (_("NCC Tool Rest Machining clear all done but the copper features "
                                                    "isolation is broken for"), str(warning_flag), _("tools")))
                    return

                # create the solid_geometry
                geo_obj.solid_geometry = []
                for tool_uid in geo_obj.tools:
                    if geo_obj.tools[tool_uid]['solid_geometry']:
                        try:
                            for geo in geo_obj.tools[tool_uid]['solid_geometry']:
                                geo_obj.solid_geometry.append(geo)
                        except TypeError:
                            geo_obj.solid_geometry.append(geo_obj.tools[tool_uid]['solid_geometry'])
            else:
                # I will use this variable for this purpose although it was meant for something else
                # signal that we have no geo in the object therefore don't create it
                app_obj.poly_not_cleared = False
                return "fail"

        # ###########################################################################################
        # Create the Job function and send it to the worker to be processed in another thread #######
        # ###########################################################################################
        def job_thread(a_obj):
            try:
                if rest_machining_choice is True:
                    a_obj.app_obj.new_object("geometry", name, gen_clear_area_rest)
                else:
                    a_obj.app_obj.new_object("geometry", name, gen_clear_area)
            except grace:
                if run_threaded:
                    proc.done()
                return
            except Exception:
                if run_threaded:
                    proc.done()
                traceback.print_stack()
                return

            if run_threaded:
                proc.done()
            else:
                a_obj.proc_container.view.set_idle()

            # focus on Properties Tab
            self.app.ui.notebook.setCurrentWidget(self.app.ui.properties_tab)

        if run_threaded:
            # Promise object with the new name
            self.app.collection.promise(name)

            # Background
            self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})
        else:
            job_thread(app_obj=self.app)

    def clear_copper_tcl(self, ncc_obj, sel_obj=None, ncctooldia=None, isotooldia=None, margin=None, has_offset=None,
                         offset=None, select_method=None, outname=None, overlap=None, connect=None, contour=None,
                         order=None, method=None, rest=None, tools_storage=None, plot=True, run_threaded=False):
        """
        Clear the excess copper from the entire object. To be used only in a TCL command.

        :param ncc_obj:         ncc cleared object
        :param sel_obj:
        :param ncctooldia:      a tuple or single element made out of diameters of the tools to be used to ncc clear
        :param isotooldia:      a tuple or single element made out of diameters of the tools to be used for isolation
        :param overlap:         value by which the paths will overlap
        :param order:           if the tools are ordered and how
        :param select_method:   if to do ncc on the whole object, on an defined area or on an area defined by
                                another object
        :param has_offset:      True if an offset is needed
        :param offset:          distance from the copper features where the copper clearing is stopping
        :param margin:          a border around cleared area
        :param outname:         name of the resulting object
        :param connect:         Connect lines to avoid tool lifts.
        :param contour:         Clear around the edges.
        :param method:          choice out of 'seed', 'normal', 'lines'
        :param rest:            True if to use rest-machining
        :param tools_storage:   whether to use the current tools_storage self.ncc_tools or a different one.
                                Usage of the different one is related to when this function is called from a
                                TcL command.
        :param plot:            if True after the job is finished the result will be plotted, else it will not.
        :param run_threaded:    If True the method will be run in a threaded way suitable for GUI usage;
                                if False it will run non-threaded for TclShell usage
        :return:
        """
        if run_threaded:
            proc = self.app.proc_container.new('%s...' % _("Non-Copper Clearing"))
        else:
            self.app.proc_container.view.set_busy('%s...' % _("Non-Copper Clearing"))
            QtWidgets.QApplication.processEvents()

        # #####################################################################
        # ####### Read the parameters #########################################
        # #####################################################################

        units = self.app.defaults['units']

        log.debug("NCC Tool started. Reading parameters.")
        self.app.inform.emit(_("NCC Tool started. Reading parameters."))

        ncc_method = method
        ncc_margin = margin
        ncc_select = select_method
        overlap = overlap

        connect = connect
        contour = contour
        order = order

        if tools_storage is not None:
            tools_storage = tools_storage
        else:
            tools_storage = self.ncc_tools

        ncc_offset = 0.0
        if has_offset is True:
            ncc_offset = offset

        # ######################################################################################################
        # # Read the tooldia parameter and create a sorted list out them - they may be more than one diameter ##
        # ######################################################################################################
        sorted_tools = []
        try:
            sorted_tools = [float(eval(dia)) for dia in ncctooldia.split(",") if dia != '']
        except AttributeError:
            if not isinstance(ncctooldia, list):
                sorted_tools = [float(ncctooldia)]
            else:
                sorted_tools = ncctooldia

        if not sorted_tools:
            return 'fail'

        # ##############################################################################################################
        # Prepare non-copper polygons. Create the bounding box area from which the copper features will be subtracted ##
        # ##############################################################################################################
        log.debug("NCC Tool. Preparing non-copper polygons.")
        self.app.inform.emit(_("NCC Tool. Preparing non-copper polygons."))

        try:
            if sel_obj is None or sel_obj == 0:     # sel_obj == 'itself'
                ncc_sel_obj = ncc_obj
            else:
                ncc_sel_obj = sel_obj
        except Exception as e:
            log.debug("NonCopperClear.clear_copper() --> %s" % str(e))
            return 'fail'

        bounding_box = None
        if ncc_select == 0:     # itself
            geo_n = ncc_sel_obj.solid_geometry

            try:
                if isinstance(geo_n, MultiPolygon):
                    env_obj = geo_n.convex_hull
                elif (isinstance(geo_n, MultiPolygon) and len(geo_n) == 1) or \
                        (isinstance(geo_n, list) and len(geo_n) == 1) and isinstance(geo_n[0], Polygon):
                    env_obj = unary_union(geo_n)
                else:
                    env_obj = unary_union(geo_n)
                    env_obj = env_obj.convex_hull

                bounding_box = env_obj.buffer(distance=ncc_margin, join_style=base.JOIN_STYLE.mitre)
            except Exception as e:
                log.debug("NonCopperClear.clear_copper() 'itself'  --> %s" % str(e))
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("No object available."))
                return 'fail'

        elif ncc_select == 1:   # area
            geo_n = unary_union(self.sel_rect)
            try:
                __ = iter(geo_n)
            except Exception as e:
                log.debug("NonCopperClear.clear_copper() 'area' --> %s" % str(e))
                geo_n = [geo_n]

            geo_buff_list = []
            for poly in geo_n:
                if self.app.abort_flag:
                    # graceful abort requested by the user
                    raise grace
                geo_buff_list.append(poly.buffer(distance=ncc_margin, join_style=base.JOIN_STYLE.mitre))

            bounding_box = unary_union(geo_buff_list)

        elif ncc_select == 2:   # Reference Object
            geo_n = ncc_sel_obj.solid_geometry
            if ncc_sel_obj.kind == 'geometry':
                try:
                    __ = iter(geo_n)
                except Exception as e:
                    log.debug("NonCopperClear.clear_copper() 'Reference Object' --> %s" % str(e))
                    geo_n = [geo_n]

                geo_buff_list = []
                for poly in geo_n:
                    if self.app.abort_flag:
                        # graceful abort requested by the user
                        raise grace
                    geo_buff_list.append(poly.buffer(distance=ncc_margin, join_style=base.JOIN_STYLE.mitre))

                bounding_box = unary_union(geo_buff_list)
            elif ncc_sel_obj.kind == 'gerber':
                geo_n = unary_union(geo_n).convex_hull
                bounding_box = unary_union(self.ncc_obj.solid_geometry).convex_hull.intersection(geo_n)
                bounding_box = bounding_box.buffer(distance=ncc_margin, join_style=base.JOIN_STYLE.mitre)
            else:
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("The reference object type is not supported."))
                return 'fail'

        log.debug("NCC Tool. Finished non-copper polygons.")
        # ########################################################################################################
        # set the name for the future Geometry object
        # I do it here because it is also stored inside the gen_clear_area() and gen_clear_area_rest() methods
        # ########################################################################################################
        rest_machining_choice = rest
        if rest_machining_choice is True:
            name = outname if outname is not None else self.obj_name + "_ncc_rm"
        else:
            name = outname if outname is not None else self.obj_name + "_ncc"

        # ##########################################################################################
        # Initializes the new geometry object ######################################################
        # ##########################################################################################
        def gen_clear_area(geo_obj, app_obj):
            assert geo_obj.kind == 'geometry', \
                "Initializer expected a GeometryObject, got %s" % type(geo_obj)

            # provide the app with a way to process the GUI events when in a blocking loop
            if not run_threaded:
                QtWidgets.QApplication.processEvents()

            log.debug("NCC Tool. Normal copper clearing task started.")
            self.app.inform.emit(_("NCC Tool. Finished non-copper polygons. Normal copper clearing task started."))

            # a flag to signal that the isolation is broken by the bounding box in 'area' and 'box' cases
            # will store the number of tools for which the isolation is broken
            warning_flag = 0

            if order == 'fwd':
                sorted_tools.sort(reverse=False)
            elif order == 'rev':
                sorted_tools.sort(reverse=True)
            else:
                pass

            cleared_geo = []
            # Already cleared area
            cleared = MultiPolygon()

            # flag for polygons not cleared
            app_obj.poly_not_cleared = False

            # Generate area for each tool
            offset_a = sum(sorted_tools)
            current_uid = int(1)
            # try:
            #     tool = eval(self.app.defaults["tools_ncc_tools"])[0]
            # except TypeError:
            #     tool = eval(self.app.defaults["tools_ncc_tools"])

            # ###################################################################################################
            # Calculate the empty area by subtracting the solid_geometry from the object bounding box geometry ##
            # ###################################################################################################
            log.debug("NCC Tool. Calculate 'empty' area.")
            self.app.inform.emit(_("NCC Tool. Calculate 'empty' area."))

            if ncc_obj.kind == 'gerber' and not isotooldia:
                # unfortunately for this function to work time efficient,
                # if the Gerber was loaded without buffering then it require the buffering now.
                if self.app.defaults['gerber_buffering'] == 'no':
                    sol_geo = ncc_obj.solid_geometry.buffer(0)
                else:
                    sol_geo = ncc_obj.solid_geometry
                    if isinstance(sol_geo, list):
                        sol_geo = unary_union(sol_geo)

                if has_offset is True:
                    app_obj.inform.emit('[WARNING_NOTCL] %s ...' % _("Buffering"))
                    sol_geo = sol_geo.buffer(distance=ncc_offset)
                    app_obj.inform.emit('[success] %s ...' % _("Buffering finished"))

                empty = self.get_ncc_empty_area(target=sol_geo, boundary=bounding_box)
                if empty == 'fail':
                    return 'fail'

                if empty.is_empty:
                    app_obj.inform.emit('[ERROR_NOTCL] %s' %
                                        _("Could not get the extent of the area to be non copper cleared."))
                    return 'fail'
            elif ncc_obj.kind == 'gerber' and isotooldia:
                isolated_geo = []

                # unfortunately for this function to work time efficient,
                # if the Gerber was loaded without buffering then it require the buffering now.
                if self.app.defaults['gerber_buffering'] == 'no':
                    self.solid_geometry = ncc_obj.solid_geometry.buffer(0)
                else:
                    self.solid_geometry = ncc_obj.solid_geometry

                # if milling type is climb then the move is counter-clockwise around features
                milling_type = self.app.defaults["tools_ncc_milling_type"]

                for tool_iso in isotooldia:
                    new_geometry = []

                    if milling_type == 'cl':
                        isolated_geo = self.generate_envelope(tool_iso / 2, 1)
                    else:
                        isolated_geo = self.generate_envelope(tool_iso / 2, 0)

                    if isolated_geo == 'fail':
                        app_obj.inform.emit('[ERROR_NOTCL] %s' % _("Isolation geometry could not be generated."))
                    else:
                        if ncc_margin < tool_iso:
                            app_obj.inform.emit('[WARNING_NOTCL] %s' % _("Isolation geometry is broken. Margin is less "
                                                                         "than isolation tool diameter."))
                        try:
                            for geo_elem in isolated_geo:
                                # provide the app with a way to process the GUI events when in a blocking loop
                                QtWidgets.QApplication.processEvents()

                                if self.app.abort_flag:
                                    # graceful abort requested by the user
                                    raise grace

                                if isinstance(geo_elem, Polygon):
                                    for ring in self.poly2rings(geo_elem):
                                        new_geo = ring.intersection(bounding_box)
                                        if new_geo and not new_geo.is_empty:
                                            new_geometry.append(new_geo)
                                elif isinstance(geo_elem, MultiPolygon):
                                    for a_poly in geo_elem:
                                        for ring in self.poly2rings(a_poly):
                                            new_geo = ring.intersection(bounding_box)
                                            if new_geo and not new_geo.is_empty:
                                                new_geometry.append(new_geo)
                                elif isinstance(geo_elem, LineString):
                                    new_geo = geo_elem.intersection(bounding_box)
                                    if new_geo:
                                        if not new_geo.is_empty:
                                            new_geometry.append(new_geo)
                                elif isinstance(geo_elem, MultiLineString):
                                    for line_elem in geo_elem:
                                        new_geo = line_elem.intersection(bounding_box)
                                        if new_geo and not new_geo.is_empty:
                                            new_geometry.append(new_geo)
                        except TypeError:
                            if isinstance(isolated_geo, Polygon):
                                for ring in self.poly2rings(isolated_geo):
                                    new_geo = ring.intersection(bounding_box)
                                    if new_geo:
                                        if not new_geo.is_empty:
                                            new_geometry.append(new_geo)
                            elif isinstance(isolated_geo, LineString):
                                new_geo = isolated_geo.intersection(bounding_box)
                                if new_geo and not new_geo.is_empty:
                                    new_geometry.append(new_geo)
                            elif isinstance(isolated_geo, MultiLineString):
                                for line_elem in isolated_geo:
                                    new_geo = line_elem.intersection(bounding_box)
                                    if new_geo and not new_geo.is_empty:
                                        new_geometry.append(new_geo)

                        # a MultiLineString geometry element will show that the isolation is broken for this tool
                        for geo_e in new_geometry:
                            if type(geo_e) == MultiLineString:
                                warning_flag += 1
                                break

                        for k, v in tools_storage.items():
                            if float('%.*f' % (self.decimals, v['tooldia'])) == float('%.*f' % (self.decimals,
                                                                                                tool_iso)):
                                current_uid = int(k)
                                # add the solid_geometry to the current too in self.paint_tools dictionary
                                # and then reset the temporary list that stored that solid_geometry
                                v['solid_geometry'] = deepcopy(new_geometry)
                                v['data']['name'] = name
                                break
                        geo_obj.tools[current_uid] = dict(tools_storage[current_uid])

                sol_geo = unary_union(isolated_geo)
                if has_offset is True:
                    app_obj.inform.emit('[WARNING_NOTCL] %s ...' % _("Buffering"))
                    sol_geo = sol_geo.buffer(distance=ncc_offset)
                    app_obj.inform.emit('[success] %s ...' % _("Buffering finished"))
                empty = self.get_ncc_empty_area(target=sol_geo, boundary=bounding_box)
                if empty == 'fail':
                    return 'fail'

                if empty.is_empty:
                    app_obj.inform.emit('[ERROR_NOTCL] %s' %
                                        _("Isolation geometry is broken. Margin is less than isolation tool diameter."))
                    return 'fail'

            elif ncc_obj.kind == 'geometry':
                sol_geo = unary_union(ncc_obj.solid_geometry)
                if has_offset is True:
                    app_obj.inform.emit('[WARNING_NOTCL] %s ...' % _("Buffering"))
                    sol_geo = sol_geo.buffer(distance=ncc_offset)
                    app_obj.inform.emit('[success] %s ...' % _("Buffering finished"))
                empty = self.get_ncc_empty_area(target=sol_geo, boundary=bounding_box)
                if empty == 'fail':
                    return 'fail'

                if empty.is_empty:
                    app_obj.inform.emit('[ERROR_NOTCL] %s' %
                                        _("Could not get the extent of the area to be non copper cleared."))
                    return 'fail'

            else:
                app_obj.inform.emit('[ERROR_NOTCL] %s' % _('The selected object is not suitable for copper clearing.'))
                return 'fail'

            if type(empty) is Polygon:
                empty = MultiPolygon([empty])

            log.debug("NCC Tool. Finished calculation of 'empty' area.")
            self.app.inform.emit(_("NCC Tool. Finished calculation of 'empty' area."))

            tool = 1
            # COPPER CLEARING #
            for tool in sorted_tools:
                log.debug("Starting geometry processing for tool: %s" % str(tool))
                if self.app.abort_flag:
                    # graceful abort requested by the user
                    raise grace

                # provide the app with a way to process the GUI events when in a blocking loop
                QtWidgets.QApplication.processEvents()

                app_obj.inform.emit('[success] %s = %s%s %s' % (
                    _('NCC Tool clearing with tool diameter'), str(tool), units.lower(), _('started.'))
                )
                app_obj.proc_container.update_view_text(' %d%%' % 0)

                cleared_geo[:] = []

                # Get remaining tools offset
                offset_a -= (tool - 1e-12)

                # Area to clear
                area = empty.buffer(-offset_a)
                try:
                    area = area.difference(cleared)
                except Exception:
                    continue

                # Transform area to MultiPolygon
                if type(area) is Polygon:
                    area = MultiPolygon([area])

                # variables to display the percentage of work done
                geo_len = len(area.geoms)

                old_disp_number = 0
                log.warning("Total number of polygons to be cleared. %s" % str(geo_len))

                if area.geoms:
                    if len(area.geoms) > 0:
                        pol_nr = 0
                        for p in area.geoms:
                            # provide the app with a way to process the GUI events when in a blocking loop
                            QtWidgets.QApplication.processEvents()

                            if self.app.abort_flag:
                                # graceful abort requested by the user
                                raise grace

                            # clean the polygon
                            p = p.buffer(0)

                            if p is not None and p.is_valid:
                                poly_processed = []
                                try:
                                    for pol in p:
                                        if pol is not None and isinstance(pol, Polygon):
                                            if ncc_method == 0:    # standard
                                                cp = self.clear_polygon(pol, tool,
                                                                        self.circle_steps,
                                                                        overlap=overlap, contour=contour,
                                                                        connect=connect,
                                                                        prog_plot=False)
                                            elif ncc_method == 1:  # seed
                                                cp = self.clear_polygon2(pol, tool,
                                                                         self.circle_steps,
                                                                         overlap=overlap, contour=contour,
                                                                         connect=connect,
                                                                         prog_plot=False)
                                            else:
                                                cp = self.clear_polygon3(pol, tool,
                                                                         self.circle_steps,
                                                                         overlap=overlap, contour=contour,
                                                                         connect=connect,
                                                                         prog_plot=False)
                                            if cp:
                                                cleared_geo += list(cp.get_objects())
                                                poly_processed.append(True)
                                            else:
                                                poly_processed.append(False)
                                                log.warning("Polygon in MultiPolygon can not be cleared.")
                                        else:
                                            log.warning("Geo in Iterable can not be cleared because it is not Polygon. "
                                                        "It is: %s" % str(type(pol)))
                                except TypeError:
                                    if isinstance(p, Polygon):
                                        if ncc_method == 0:    # standard
                                            cp = self.clear_polygon(p, tool, self.circle_steps,
                                                                    overlap=overlap, contour=contour, connect=connect,
                                                                    prog_plot=False)
                                        elif ncc_method == 1:   # seed
                                            cp = self.clear_polygon2(p, tool, self.circle_steps,
                                                                     overlap=overlap, contour=contour, connect=connect,
                                                                     prog_plot=False)
                                        else:
                                            cp = self.clear_polygon3(p, tool, self.circle_steps,
                                                                     overlap=overlap, contour=contour, connect=connect,
                                                                     prog_plot=False)
                                        if cp:
                                            cleared_geo += list(cp.get_objects())
                                            poly_processed.append(True)
                                        else:
                                            poly_processed.append(False)
                                            log.warning("Polygon can not be cleared.")
                                    else:
                                        log.warning("Geo can not be cleared because it is: %s" % str(type(p)))

                                p_cleared = poly_processed.count(True)
                                p_not_cleared = poly_processed.count(False)

                                if p_not_cleared:
                                    app_obj.poly_not_cleared = True

                                if p_cleared == 0:
                                    continue

                                pol_nr += 1
                                disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 100]))
                                # log.debug("Polygons cleared: %d" % pol_nr)

                                if old_disp_number < disp_number <= 100:
                                    self.app.proc_container.update_view_text(' %d%%' % disp_number)
                                    old_disp_number = disp_number
                                    # log.debug("Polygons cleared: %d. Percentage done: %d%%" % (pol_nr, disp_number))

                            # check if there is a geometry at all in the cleared geometry
                        if cleared_geo:
                            # Overall cleared area
                            cleared = empty.buffer(-offset_a * (1 + overlap)).buffer(-tool / 1.999999).buffer(
                                tool / 1.999999)

                            # clean-up cleared geo
                            cleared = cleared.buffer(0)

                            # find the tooluid associated with the current tool_dia so we know where to add the tool
                            # solid_geometry
                            for k, v in tools_storage.items():
                                if float('%.*f' % (self.decimals, v['tooldia'])) == float('%.*f' % (self.decimals,
                                                                                                    tool)):
                                    current_uid = int(k)

                                    # add the solid_geometry to the current too in self.paint_tools dictionary
                                    # and then reset the temporary list that stored that solid_geometry
                                    v['solid_geometry'] = deepcopy(cleared_geo)
                                    v['data']['name'] = name
                                    break
                            geo_obj.tools[current_uid] = dict(tools_storage[current_uid])
                        else:
                            log.debug("There are no geometries in the cleared polygon.")

            # delete tools with empty geometry
            # look for keys in the tools_storage dict that have 'solid_geometry' values empty
            for uid, uid_val in list(tools_storage.items()):
                try:
                    # if the solid_geometry (type=list) is empty
                    if not uid_val['solid_geometry']:
                        tools_storage.pop(uid, None)
                except KeyError:
                    tools_storage.pop(uid, None)

            geo_obj.options["cnctooldia"] = str(tool)

            geo_obj.multigeo = True
            geo_obj.tools.clear()
            geo_obj.tools = dict(tools_storage)

            # test if at least one tool has solid_geometry. If no tool has solid_geometry we raise an Exception
            has_solid_geo = 0
            for tooluid in geo_obj.tools:
                if geo_obj.tools[tooluid]['solid_geometry']:
                    has_solid_geo += 1
            if has_solid_geo == 0:
                app_obj.inform.emit('[ERROR] %s' %
                                    _("There is no NCC Geometry in the file.\n"
                                      "Usually it means that the tool diameter is too big for the painted geometry.\n"
                                      "Change the painting parameters and try again."))
                return 'fail'

            # check to see if geo_obj.tools is empty
            # it will be updated only if there is a solid_geometry for tools
            if geo_obj.tools:
                if warning_flag == 0:
                    self.app.inform.emit('[success] %s' % _("NCC Tool clear all done."))
                else:
                    self.app.inform.emit('[WARNING] %s: %s %s.' % (
                        _("NCC Tool clear all done but the copper features isolation is broken for"),
                        str(warning_flag),
                        _("tools")))
                    return

                # create the solid_geometry
                geo_obj.solid_geometry = []
                for tooluid in geo_obj.tools:
                    if geo_obj.tools[tooluid]['solid_geometry']:
                        try:
                            for geo in geo_obj.tools[tooluid]['solid_geometry']:
                                geo_obj.solid_geometry.append(geo)
                        except TypeError:
                            geo_obj.solid_geometry.append(geo_obj.tools[tooluid]['solid_geometry'])
            else:
                # I will use this variable for this purpose although it was meant for something else
                # signal that we have no geo in the object therefore don't create it
                app_obj.poly_not_cleared = False
                return "fail"

        # ###########################################################################################
        # Initializes the new geometry object for the case of the rest-machining ####################
        # ###########################################################################################
        def gen_clear_area_rest(geo_obj, app_obj):
            assert geo_obj.kind == 'geometry', \
                "Initializer expected a GeometryObject, got %s" % type(geo_obj)

            log.debug("NCC Tool. Rest machining copper clearing task started.")
            app_obj.inform.emit('_(NCC Tool. Rest machining copper clearing task started.')

            # provide the app with a way to process the GUI events when in a blocking loop
            if not run_threaded:
                QtWidgets.QApplication.processEvents()

            # a flag to signal that the isolation is broken by the bounding box in 'area' and 'box' cases
            # will store the number of tools for which the isolation is broken
            warning_flag = 0

            sorted_tools.sort(reverse=True)

            cleared_geo = []
            cleared_by_last_tool = []
            rest_geo = []
            current_uid = 1
            try:
                tool = eval(self.app.defaults["tools_ncc_tools"])[0]
            except TypeError:
                tool = eval(self.app.defaults["tools_ncc_tools"])

            # repurposed flag for final object, geo_obj. True if it has any solid_geometry, False if not.
            app_obj.poly_not_cleared = True
            log.debug("NCC Tool. Calculate 'empty' area.")
            app_obj.inform.emit("NCC Tool. Calculate 'empty' area.")

            # ###################################################################################################
            # Calculate the empty area by subtracting the solid_geometry from the object bounding box geometry ##
            # ###################################################################################################
            if ncc_obj.kind == 'gerber' and not isotooldia:
                sol_geo = ncc_obj.solid_geometry
                if has_offset is True:
                    app_obj.inform.emit('[WARNING_NOTCL] %s ...' % _("Buffering"))
                    sol_geo = sol_geo.buffer(distance=ncc_offset)
                    app_obj.inform.emit('[success] %s ...' % _("Buffering finished"))
                empty = self.get_ncc_empty_area(target=sol_geo, boundary=bounding_box)
                if empty == 'fail':
                    return 'fail'

                if empty.is_empty:
                    app_obj.inform.emit('[ERROR_NOTCL] %s' %
                                        _("Could not get the extent of the area to be non copper cleared."))
                    return 'fail'
            elif ncc_obj.kind == 'gerber' and isotooldia:
                isolated_geo = []
                self.solid_geometry = ncc_obj.solid_geometry

                # if milling type is climb then the move is counter-clockwise around features
                milling_type = self.app.defaults["tools_ncc_milling_type"]

                for tool_iso in isotooldia:
                    new_geometry = []

                    if milling_type == 'cl':
                        isolated_geo = self.generate_envelope(tool_iso, 1)
                    else:
                        isolated_geo = self.generate_envelope(tool_iso, 0)

                    if isolated_geo == 'fail':
                        app_obj.inform.emit('[ERROR_NOTCL] %s' % _("Isolation geometry could not be generated."))
                    else:
                        app_obj.inform.emit('[WARNING_NOTCL] %s' % _("Isolation geometry is broken. Margin is less "
                                                                     "than isolation tool diameter."))

                        try:
                            for geo_elem in isolated_geo:
                                # provide the app with a way to process the GUI events when in a blocking loop
                                QtWidgets.QApplication.processEvents()

                                if self.app.abort_flag:
                                    # graceful abort requested by the user
                                    raise grace

                                if isinstance(geo_elem, Polygon):
                                    for ring in self.poly2rings(geo_elem):
                                        new_geo = ring.intersection(bounding_box)
                                        if new_geo and not new_geo.is_empty:
                                            new_geometry.append(new_geo)
                                elif isinstance(geo_elem, MultiPolygon):
                                    for poly_g in geo_elem:
                                        for ring in self.poly2rings(poly_g):
                                            new_geo = ring.intersection(bounding_box)
                                            if new_geo and not new_geo.is_empty:
                                                new_geometry.append(new_geo)
                                elif isinstance(geo_elem, LineString):
                                    new_geo = geo_elem.intersection(bounding_box)
                                    if new_geo:
                                        if not new_geo.is_empty:
                                            new_geometry.append(new_geo)
                                elif isinstance(geo_elem, MultiLineString):
                                    for line_elem in geo_elem:
                                        new_geo = line_elem.intersection(bounding_box)
                                        if new_geo and not new_geo.is_empty:
                                            new_geometry.append(new_geo)
                        except TypeError:
                            try:
                                if isinstance(isolated_geo, Polygon):
                                    for ring in self.poly2rings(isolated_geo):
                                        new_geo = ring.intersection(bounding_box)
                                        if new_geo:
                                            if not new_geo.is_empty:
                                                new_geometry.append(new_geo)
                                elif isinstance(isolated_geo, LineString):
                                    new_geo = isolated_geo.intersection(bounding_box)
                                    if new_geo and not new_geo.is_empty:
                                        new_geometry.append(new_geo)
                                elif isinstance(isolated_geo, MultiLineString):
                                    for line_elem in isolated_geo:
                                        new_geo = line_elem.intersection(bounding_box)
                                        if new_geo and not new_geo.is_empty:
                                            new_geometry.append(new_geo)
                            except Exception:
                                pass

                        # a MultiLineString geometry element will show that the isolation is broken for this tool
                        for geo_e in new_geometry:
                            if type(geo_e) == MultiLineString:
                                warning_flag += 1
                                break

                        for k, v in tools_storage.items():
                            if float('%.*f' % (self.decimals, v['tooldia'])) == float('%.*f' % (self.decimals,
                                                                                                tool_iso)):
                                current_uid = int(k)
                                # add the solid_geometry to the current too in self.paint_tools dictionary
                                # and then reset the temporary list that stored that solid_geometry
                                v['solid_geometry'] = deepcopy(new_geometry)
                                v['data']['name'] = name
                                break
                        geo_obj.tools[current_uid] = dict(tools_storage[current_uid])

                sol_geo = unary_union(isolated_geo)
                if has_offset is True:
                    app_obj.inform.emit('[WARNING_NOTCL] %s ...' % _("Buffering"))
                    sol_geo = sol_geo.buffer(distance=ncc_offset)
                    app_obj.inform.emit('[success] %s ...' % _("Buffering finished"))
                empty = self.get_ncc_empty_area(target=sol_geo, boundary=bounding_box)
                if empty == 'fail':
                    return 'fail'

                if empty.is_empty:
                    app_obj.inform.emit('[ERROR_NOTCL] %s' %
                                        _("Isolation geometry is broken. Margin is less than isolation tool diameter."))
                    return 'fail'

            elif ncc_obj.kind == 'geometry':
                sol_geo = unary_union(ncc_obj.solid_geometry)
                if has_offset is True:
                    app_obj.inform.emit('[WARNING_NOTCL] %s ...' % _("Buffering"))
                    sol_geo = sol_geo.buffer(distance=ncc_offset)
                    app_obj.inform.emit('[success] %s ...' % _("Buffering finished"))
                empty = self.get_ncc_empty_area(target=sol_geo, boundary=bounding_box)
                if empty == 'fail':
                    return 'fail'

                if empty.is_empty:
                    app_obj.inform.emit('[ERROR_NOTCL] %s' %
                                        _("Could not get the extent of the area to be non copper cleared."))
                    return 'fail'
            else:
                app_obj.inform.emit('[ERROR_NOTCL] %s' % _('The selected object is not suitable for copper clearing.'))
                return

            if self.app.abort_flag:
                # graceful abort requested by the user
                raise grace

            if type(empty) is Polygon:
                empty = MultiPolygon([empty])

            area = empty.buffer(0)

            log.debug("NCC Tool. Finished calculation of 'empty' area.")
            app_obj.inform.emit("NCC Tool. Finished calculation of 'empty' area.")

            # Generate area for each tool
            while sorted_tools:
                if self.app.abort_flag:
                    # graceful abort requested by the user
                    raise grace

                tool = sorted_tools.pop(0)
                log.debug("Starting geometry processing for tool: %s" % str(tool))

                app_obj.inform.emit('[success] %s = %s%s %s' % (
                    _('NCC Tool clearing with tool diameter'), str(tool), units.lower(), _('started.'))
                )
                app_obj.proc_container.update_view_text(' %d%%' % 0)

                tool_used = tool - 1e-12
                cleared_geo[:] = []

                # Area to clear
                for poly_r in cleared_by_last_tool:
                    # provide the app with a way to process the GUI events when in a blocking loop
                    QtWidgets.QApplication.processEvents()

                    if self.app.abort_flag:
                        # graceful abort requested by the user
                        raise grace
                    try:
                        area = area.difference(poly_r)
                    except Exception:
                        pass
                cleared_by_last_tool[:] = []

                # Transform area to MultiPolygon
                if type(area) is Polygon:
                    area = MultiPolygon([area])

                # add the rest that was not able to be cleared previously; area is a MultyPolygon
                # and rest_geo it's a list
                allparts = [p.buffer(0) for p in area.geoms]
                allparts += deepcopy(rest_geo)
                rest_geo[:] = []
                area = MultiPolygon(deepcopy(allparts))
                allparts[:] = []

                # variables to display the percentage of work done
                geo_len = len(area.geoms)
                old_disp_number = 0
                log.warning("Total number of polygons to be cleared. %s" % str(geo_len))

                if area.geoms:
                    if len(area.geoms) > 0:
                        pol_nr = 0
                        for p in area.geoms:
                            if self.app.abort_flag:
                                # graceful abort requested by the user
                                raise grace

                            # clean the polygon
                            p = p.buffer(0)

                            if p is not None and p.is_valid:
                                # provide the app with a way to process the GUI events when in a blocking loop
                                QtWidgets.QApplication.processEvents()

                                if isinstance(p, Polygon):
                                    try:
                                        if ncc_method == 0:     # standard
                                            cp = self.clear_polygon(p, tool_used,
                                                                    self.circle_steps,
                                                                    overlap=overlap, contour=contour, connect=connect,
                                                                    prog_plot=False)
                                        elif ncc_method == 1:   # seed
                                            cp = self.clear_polygon2(p, tool_used,
                                                                     self.circle_steps,
                                                                     overlap=overlap, contour=contour, connect=connect,
                                                                     prog_plot=False)
                                        else:
                                            cp = self.clear_polygon3(p, tool_used,
                                                                     self.circle_steps,
                                                                     overlap=overlap, contour=contour, connect=connect,
                                                                     prog_plot=False)
                                        cleared_geo.append(list(cp.get_objects()))
                                    except Exception as ee:
                                        log.warning("Polygon can't be cleared. %s" % str(ee))
                                        # this polygon should be added to a list and then try clear it with
                                        # a smaller tool
                                        rest_geo.append(p)
                                elif isinstance(p, MultiPolygon):
                                    for poly_p in p:
                                        if poly_p is not None:
                                            # provide the app with a way to process the GUI events when
                                            # in a blocking loop
                                            QtWidgets.QApplication.processEvents()

                                            try:
                                                if ncc_method == 0:     # 'standard'
                                                    cp = self.clear_polygon(poly_p, tool_used,
                                                                            self.circle_steps,
                                                                            overlap=overlap, contour=contour,
                                                                            connect=connect,
                                                                            prog_plot=False)
                                                elif ncc_method == 1:   # 'seed'
                                                    cp = self.clear_polygon2(poly_p, tool_used,
                                                                             self.circle_steps,
                                                                             overlap=overlap, contour=contour,
                                                                             connect=connect,
                                                                             prog_plot=False)
                                                else:
                                                    cp = self.clear_polygon3(poly_p, tool_used,
                                                                             self.circle_steps,
                                                                             overlap=overlap, contour=contour,
                                                                             connect=connect,
                                                                             prog_plot=False)
                                                cleared_geo.append(list(cp.get_objects()))
                                            except Exception as eee:
                                                log.warning("Polygon can't be cleared. %s" % str(eee))
                                                # this polygon should be added to a list and then try clear it with
                                                # a smaller tool
                                                rest_geo.append(poly_p)

                                pol_nr += 1
                                disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 100]))
                                # log.debug("Polygons cleared: %d" % pol_nr)

                                if old_disp_number < disp_number <= 100:
                                    self.app.proc_container.update_view_text(' %d%%' % disp_number)
                                    old_disp_number = disp_number
                                    # log.debug("Polygons cleared: %d. Percentage done: %d%%" % (pol_nr, disp_number))

                        if self.app.abort_flag:
                            # graceful abort requested by the user
                            raise grace

                        # check if there is a geometry at all in the cleared geometry
                        if cleared_geo:
                            # Overall cleared area
                            cleared_area = list(self.flatten_list(cleared_geo))

                            # cleared = MultiPolygon([p.buffer(tool_used / 2).buffer(-tool_used / 2)
                            #                         for p in cleared_area])

                            # here we store the poly's already processed in the original geometry by the current tool
                            # into cleared_by_last_tool list
                            # this will be sutracted from the original geometry_to_be_cleared and make data for
                            # the next tool
                            buffer_value = tool_used / 2
                            for p in cleared_area:
                                if self.app.abort_flag:
                                    # graceful abort requested by the user
                                    raise grace

                                r_poly = p.buffer(buffer_value)
                                cleared_by_last_tool.append(r_poly)

                            # find the tooluid associated with the current tool_dia so we know
                            # where to add the tool solid_geometry
                            for k, v in tools_storage.items():
                                if float('%.*f' % (self.decimals, v['tooldia'])) == float('%.*f' % (self.decimals,
                                                                                                    tool)):
                                    current_uid = int(k)

                                    # add the solid_geometry to the current too in self.paint_tools dictionary
                                    # and then reset the temporary list that stored that solid_geometry
                                    v['solid_geometry'] = deepcopy(cleared_area)
                                    v['data']['name'] = name
                                    cleared_area[:] = []
                                    break

                            geo_obj.tools[current_uid] = dict(tools_storage[current_uid])
                        else:
                            log.debug("There are no geometries in the cleared polygon.")

            geo_obj.multigeo = True
            geo_obj.options["cnctooldia"] = str(tool)

            # check to see if geo_obj.tools is empty
            # it will be updated only if there is a solid_geometry for tools
            if geo_obj.tools:
                if warning_flag == 0:
                    self.app.inform.emit('[success] %s' % _("NCC Tool Rest Machining clear all done."))
                else:
                    self.app.inform.emit(
                        '[WARNING] %s: %s %s.' % (_("NCC Tool Rest Machining clear all done but the copper features "
                                                    "isolation is broken for"), str(warning_flag), _("tools")))
                    return

                # create the solid_geometry
                geo_obj.solid_geometry = []
                for tooluid in geo_obj.tools:
                    if geo_obj.tools[tooluid]['solid_geometry']:
                        try:
                            for geo in geo_obj.tools[tooluid]['solid_geometry']:
                                geo_obj.solid_geometry.append(geo)
                        except TypeError:
                            geo_obj.solid_geometry.append(geo_obj.tools[tooluid]['solid_geometry'])
            else:
                # I will use this variable for this purpose although it was meant for something else
                # signal that we have no geo in the object therefore don't create it
                app_obj.poly_not_cleared = False
                return "fail"

        # ###########################################################################################
        # Create the Job function and send it to the worker to be processed in another thread #######
        # ###########################################################################################
        def job_thread(app_obj):
            try:
                if rest_machining_choice is True:
                    app_obj.app_obj.new_object("geometry", name, gen_clear_area_rest, plot=plot)
                else:
                    app_obj.app_obj.new_object("geometry", name, gen_clear_area, plot=plot)
            except grace:
                if run_threaded:
                    proc.done()
                return
            except Exception:
                if run_threaded:
                    proc.done()
                traceback.print_stack()
                return

            if run_threaded:
                proc.done()
            else:
                app_obj.proc_container.view.set_idle()

            # focus on Properties Tab
            self.app.ui.notebook.setCurrentWidget(self.app.ui.properties_tab)

        if run_threaded:
            # Promise object with the new name
            self.app.collection.promise(name)

            # Background
            self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})
        else:
            job_thread(app_obj=self.app)

    def get_ncc_empty_area(self, target, boundary=None):
        """
        Returns the complement of target geometry within
        the given boundary polygon. If not specified, it defaults to
        the rectangular bounding box of target geometry.

        :param target:      The geometry that is to be 'inverted'
        :param boundary:    A polygon that surrounds the entire solid geometry and from which we subtract in order to
                            create a "negative" geometry (geometry to be emptied of copper)
        :return:
        """
        if isinstance(target, Polygon):
            geo_len = 1
        else:
            geo_len = len(target)

        if isinstance(target, list):
            target = MultiPolygon(target)

        pol_nr = 0
        old_disp_number = 0

        if boundary is None:
            boundary = target.envelope
        else:
            boundary = boundary

        try:
            ret_val = boundary.difference(target)
        except Exception:
            try:
                for el in target:
                    # provide the app with a way to process the GUI events when in a blocking loop
                    QtWidgets.QApplication.processEvents()
                    if self.app.abort_flag:
                        # graceful abort requested by the user
                        raise grace

                    boundary = boundary.difference(el)
                    pol_nr += 1
                    disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 100]))

                    if old_disp_number < disp_number <= 100:
                        self.app.proc_container.update_view_text(' %d%%' % disp_number)
                        old_disp_number = disp_number
                return boundary
            except Exception:
                self.app.inform.emit('[ERROR_NOTCL] %s' %
                                     _("Try to use the Buffering Type = Full in Preferences -> Gerber General. "
                                       "Reload the Gerber file after this change."))
                return 'fail'

        return ret_val

    @staticmethod
    def poly2rings(poly):
        return [poly.exterior] + [interior for interior in poly.interiors]

    def generate_envelope(self, offset, invert, envelope_iso_type=2, follow=None):
        # isolation_geometry produces an envelope that is going on the left of the geometry
        # (the copper features). To leave the least amount of burrs on the features
        # the tool needs to travel on the right side of the features (this is called conventional milling)
        # the first pass is the one cutting all of the features, so it needs to be reversed
        # the other passes overlap preceding ones and cut the left over copper. It is better for them
        # to cut on the right side of the left over copper i.e on the left side of the features.
        try:
            geom = self.isolation_geometry(offset, iso_type=envelope_iso_type, follow=follow)
        except Exception as e:
            log.debug('NonCopperClear.generate_envelope() --> %s' % str(e))
            return 'fail'

        if invert:
            try:
                try:
                    pl = []
                    for p in geom:
                        if p is not None:
                            if isinstance(p, Polygon):
                                pl.append(Polygon(p.exterior.coords[::-1], p.interiors))
                            elif isinstance(p, LinearRing):
                                pl.append(Polygon(p.coords[::-1]))
                    geom = MultiPolygon(pl)
                except TypeError:
                    if isinstance(geom, Polygon) and geom is not None:
                        geom = Polygon(geom.exterior.coords[::-1], geom.interiors)
                    elif isinstance(geom, LinearRing) and geom is not None:
                        geom = Polygon(geom.coords[::-1])
                    else:
                        log.debug("NonCopperClear.generate_envelope() Error --> Unexpected Geometry %s" %
                                  type(geom))
            except Exception as e:
                log.debug("NonCopperClear.generate_envelope() Error --> %s" % str(e))
                return 'fail'
        return geom

    def on_ncc_tool_add_from_db_executed(self, tool):
        """
        Here add the tool from DB  in the selected geometry object
        :return:
        """
        tool_from_db = deepcopy(tool)

        if tool['data']['tool_target'] not in [0, 5]:   # [General, NCC]
            for idx in range(self.app.ui.plot_tab_area.count()):
                if self.app.ui.plot_tab_area.tabText(idx) == _("Tools Database"):
                    wdg = self.app.ui.plot_tab_area.widget(idx)
                    wdg.deleteLater()
                    self.app.ui.plot_tab_area.removeTab(idx)
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Selected tool can't be used here. Pick another."))
            return

        res = self.on_ncc_tool_from_db_inserted(tool=tool_from_db)

        for idx in range(self.app.ui.plot_tab_area.count()):
            if self.app.ui.plot_tab_area.tabText(idx) == _("Tools Database"):
                wdg = self.app.ui.plot_tab_area.widget(idx)
                wdg.deleteLater()
                self.app.ui.plot_tab_area.removeTab(idx)

        if res == 'fail':
            return
        self.app.inform.emit('[success] %s' % _("Tool from DB added in Tool Table."))

        # select last tool added
        toolid = res
        for row in range(self.ui.tools_table.rowCount()):
            if int(self.ui.tools_table.item(row, 3).text()) == toolid:
                self.ui.tools_table.selectRow(row)
        self.on_row_selection_change()

    def on_ncc_tool_from_db_inserted(self, tool):
        """
        Called from the Tools DB object through a App method when adding a tool from Tools Database
        :param tool: a dict with the tool data
        :return: None
        """

        self.ui_disconnect()
        self.units = self.app.defaults['units'].upper()

        tooldia = float(tool['tooldia'])

        # construct a list of all 'tooluid' in the self.tools
        tool_uid_list = [int(tooluid_key) for tooluid_key in self.ncc_tools]

        # find maximum from the temp_uid, add 1 and this is the new 'tooluid'
        max_uid = 0 if not tool_uid_list else max(tool_uid_list)
        tooluid = max_uid + 1

        tool_dias = []
        for k, v in self.ncc_tools.items():
            for tool_v in v.keys():
                if tool_v == 'tooldia':
                    tool_dias.append(self.app.dec_format(v[tool_v], self.decimals))

        truncated_tooldia = self.app.dec_format(tooldia, self.decimals)
        if truncated_tooldia in tool_dias:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled. Tool already in Tool Table."))
            self.ui_connect()
            return 'fail'

        self.ncc_tools.update({
            tooluid: {
                'tooldia':          truncated_tooldia,
                'offset':           deepcopy(tool['offset']),
                'offset_value':     deepcopy(tool['offset_value']),
                'type':             deepcopy(tool['type']),
                'tool_type':        deepcopy(tool['tool_type']),
                'data':             deepcopy(tool['data']),
                'solid_geometry':   []
            }
        })
        self.ncc_tools[tooluid]['data']['name'] = '_ncc'

        self.app.inform.emit('[success] %s' % _("New tool added to Tool Table."))

        self.ui_connect()
        self.build_ui()

        # select the tool just added
        for row in range(self.ui.tools_table.rowCount()):
            if int(self.ui.tools_table.item(row, 3).text()) == self.tooluid:
                self.ui.tools_table.selectRow(row)
                break

    def on_ncc_tool_add_from_db_clicked(self):
        """
        Called when the user wants to add a new tool from Tools Database. It will create the Tools Database object
        and display the Tools Database tab in the form needed for the Tool adding
        :return: None
        """

        # if the Tools Database is already opened focus on it
        for idx in range(self.app.ui.plot_tab_area.count()):
            if self.app.ui.plot_tab_area.tabText(idx) == _("Tools Database"):
                self.app.ui.plot_tab_area.setCurrentWidget(self.app.tools_db_tab)
                break
        ret_val = self.app.on_tools_database(source='ncc')
        if ret_val == 'fail':
            return
        self.app.tools_db_tab.ok_to_add = True
        self.app.tools_db_tab.ui.buttons_frame.hide()
        self.app.tools_db_tab.ui.add_tool_from_db.show()
        self.app.tools_db_tab.ui.cancel_tool_from_db.show()

    def reset_fields(self):
        self.object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))


class NccUI:

    toolName = _("Non-Copper Clearing")

    def __init__(self, layout, app):
        self.app = app
        self.decimals = self.app.decimals
        self.layout = layout

        self.tools_frame = QtWidgets.QFrame()
        self.tools_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.tools_frame)
        self.tools_box = QtWidgets.QVBoxLayout()
        self.tools_box.setContentsMargins(0, 0, 0, 0)
        self.tools_frame.setLayout(self.tools_box)

        # ## Title
        title_label = FCLabel("%s" % self.toolName)
        title_label.setStyleSheet("""
                                QLabel
                                {
                                    font-size: 16px;
                                    font-weight: bold;
                                }
                                """)
        self.tools_box.addWidget(title_label)

        # ## Form Layout
        form_layout = QtWidgets.QFormLayout()
        self.tools_box.addLayout(form_layout)

        self.type_obj_combo_label = FCLabel('%s:' % _("Obj Type"))
        self.type_obj_combo_label.setToolTip(
            _("Specify the type of object to be cleared of excess copper.\n"
              "It can be of type: Gerber or Geometry.\n"
              "What is selected here will dictate the kind\n"
              "of objects that will populate the 'Object' combobox.")
        )
        self.type_obj_combo_label.setMinimumWidth(60)

        self.type_obj_radio = RadioSet([{'label': _("Geometry"), 'value': 'geometry'},
                                        {'label': _("Gerber"), 'value': 'gerber'}])

        form_layout.addRow(self.type_obj_combo_label, self.type_obj_radio)

        # ################################################
        # ##### The object to be copper cleaned ##########
        # ################################################
        self.object_combo = FCComboBox()
        self.object_combo.setModel(self.app.collection)
        self.object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        # self.object_combo.setCurrentIndex(1)
        self.object_combo.is_last = True

        self.object_label = FCLabel('%s:' % _("Object"))
        self.object_label.setToolTip(_("Object to be cleared of excess copper."))

        form_layout.addRow(self.object_label, self.object_combo)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.tools_box.addWidget(separator_line)

        # ### Tools ## ##
        self.tools_table_label = FCLabel('<b>%s</b>' % _('Tools Table'))
        self.tools_table_label.setToolTip(
            _("Tools pool from which the algorithm\n"
              "will pick the ones used for copper clearing.")
        )
        self.tools_box.addWidget(self.tools_table_label)

        self.tools_table = FCTable(drag_drop=True)
        self.tools_box.addWidget(self.tools_table)

        self.tools_table.setColumnCount(4)
        # 3rd column is reserved (and hidden) for the tool ID
        self.tools_table.setHorizontalHeaderLabels(['#', _('Diameter'), _('TT'), ''])
        self.tools_table.setColumnHidden(3, True)
        self.tools_table.setSortingEnabled(False)
        # self.tools_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        self.tools_table.horizontalHeaderItem(0).setToolTip(
            _("This is the Tool Number.\n"
              "Non copper clearing will start with the tool with the biggest \n"
              "diameter, continuing until there are no more tools.\n"
              "Only tools that create NCC clearing geometry will still be present\n"
              "in the resulting geometry. This is because with some tools\n"
              "this function will not be able to create painting geometry.")
        )
        self.tools_table.horizontalHeaderItem(1).setToolTip(
            _("Tool Diameter. Its value\n"
              "is the cut width into the material."))

        self.tools_table.horizontalHeaderItem(2).setToolTip(
            _("The Tool Type (TT) can be:\n"
              "- Circular with 1 ... 4 teeth -> it is informative only. Being circular,\n"
              "the cut width in material is exactly the tool diameter.\n"
              "- Ball -> informative only and make reference to the Ball type endmill.\n"
              "- V-Shape -> it will disable Z-Cut parameter in the resulting geometry UI form\n"
              "and enable two additional UI form fields in the resulting geometry: V-Tip Dia and\n"
              "V-Tip Angle. Adjusting those two values will adjust the Z-Cut parameter such\n"
              "as the cut width into material will be equal with the value in the Tool Diameter\n"
              "column of this table.\n"
              "Choosing the 'V-Shape' Tool Type automatically will select the Operation Type\n"
              "in the resulting geometry as Isolation."))

        # self.tools_table.horizontalHeaderItem(4).setToolTip(
        #     _("The 'Operation' can be:\n"
        #       "- Isolation -> will ensure that the non-copper clearing is always complete.\n"
        #       "If it's not successful then the non-copper clearing will fail, too.\n"
        #       "- Clear -> the regular non-copper clearing."))

        grid1 = QtWidgets.QGridLayout()
        self.tools_box.addLayout(grid1)
        grid1.setColumnStretch(0, 0)
        grid1.setColumnStretch(1, 1)

        # Tool order
        self.ncc_order_label = FCLabel('%s:' % _('Tool order'))
        self.ncc_order_label.setToolTip(_("This set the way that the tools in the tools table are used.\n"
                                          "'No' --> means that the used order is the one in the tool table\n"
                                          "'Forward' --> means that the tools will be ordered from small to big\n"
                                          "'Reverse' --> means that the tools will ordered from big to small\n\n"
                                          "WARNING: using rest machining will automatically set the order\n"
                                          "in reverse and disable this control."))

        self.ncc_order_radio = RadioSet([{'label': _('No'), 'value': 'no'},
                                         {'label': _('Forward'), 'value': 'fwd'},
                                         {'label': _('Reverse'), 'value': 'rev'}])
        self.ncc_order_radio.setToolTip(_("This set the way that the tools in the tools table are used.\n"
                                          "'No' --> means that the used order is the one in the tool table\n"
                                          "'Forward' --> means that the tools will be ordered from small to big\n"
                                          "'Reverse' --> means that the tools will ordered from big to small\n\n"
                                          "WARNING: using rest machining will automatically set the order\n"
                                          "in reverse and disable this control."))

        grid1.addWidget(self.ncc_order_label, 1, 0)
        grid1.addWidget(self.ncc_order_radio, 1, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid1.addWidget(separator_line, 2, 0, 1, 2)

        # #############################################################
        # ############### Tool selection ##############################
        # #############################################################

        self.grid3 = QtWidgets.QGridLayout()
        self.tools_box.addLayout(self.grid3)
        self.grid3.setColumnStretch(0, 0)
        self.grid3.setColumnStretch(1, 1)

        self.tool_sel_label = FCLabel('<b>%s</b>' % _('Add from DB'))
        self.grid3.addWidget(self.tool_sel_label, 0, 0, 1, 2)

        # ### Tool Diameter ####
        self.new_tooldia_lbl = FCLabel('%s:' % _('Tool Dia'))
        self.new_tooldia_lbl.setToolTip(
            _("Diameter for the new tool")
        )
        self.grid3.addWidget(self.new_tooldia_lbl, 2, 0)

        new_tool_lay = QtWidgets.QHBoxLayout()

        self.new_tooldia_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.new_tooldia_entry.set_precision(self.decimals)
        self.new_tooldia_entry.set_range(0.000, 10000.0000)
        self.new_tooldia_entry.setObjectName(_("Tool Dia"))

        new_tool_lay.addWidget(self.new_tooldia_entry)

        # Find Optimal Tooldia
        self.find_optimal_button = QtWidgets.QToolButton()
        self.find_optimal_button.setText(_('Optimal'))
        self.find_optimal_button.setIcon(QtGui.QIcon(self.app.resource_location + '/open_excellon32.png'))
        self.find_optimal_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.find_optimal_button.setToolTip(
            _("Find a tool diameter that is guaranteed\n"
              "to do a complete isolation.")
        )
        new_tool_lay.addWidget(self.find_optimal_button)

        self.grid3.addLayout(new_tool_lay, 2, 1)

        hlay = QtWidgets.QHBoxLayout()

        self.add_newtool_button = FCButton(_('Search and Add'))
        self.add_newtool_button.setIcon(QtGui.QIcon(self.app.resource_location + '/plus16.png'))
        self.add_newtool_button.setToolTip(
            _("Add a new tool to the Tool Table\n"
              "with the diameter specified above.\n"
              "This is done by a background search\n"
              "in the Tools Database. If nothing is found\n"
              "in the Tools DB then a default tool is added.")
        )
        hlay.addWidget(self.add_newtool_button)

        self.addtool_from_db_btn = FCButton(_('Pick from DB'))
        self.addtool_from_db_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/search_db32.png'))
        self.addtool_from_db_btn.setToolTip(
            _("Add a new tool to the Tool Table\n"
              "from the Tools Database.\n"
              "Tools database administration in in:\n"
              "Menu: Options -> Tools Database")
        )
        hlay.addWidget(self.addtool_from_db_btn)

        self.grid3.addLayout(hlay, 7, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.grid3.addWidget(separator_line, 8, 0, 1, 2)

        self.deltool_btn = FCButton(_('Delete'))
        self.deltool_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/trash16.png'))
        self.deltool_btn.setToolTip(
            _("Delete a selection of tools in the Tool Table\n"
              "by first selecting a row in the Tool Table.")
        )
        self.grid3.addWidget(self.deltool_btn, 9, 0, 1, 2)

        # self.grid3.addWidget(FCLabel(''), 10, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.grid3.addWidget(separator_line, 11, 0, 1, 2)

        self.tool_data_label = FCLabel(
            "<b>%s: <font color='#0000FF'>%s %d</font></b>" % (_('Parameters for'), _("Tool"), int(1)))
        self.tool_data_label.setToolTip(
            _(
                "The data used for creating GCode.\n"
                "Each tool store it's own set of such data."
            )
        )
        self.grid3.addWidget(self.tool_data_label, 12, 0, 1, 2)

        # Operation
        op_label = FCLabel('%s:' % _('Operation'))
        op_label.setToolTip(
            _("The 'Operation' can be:\n"
              "- Isolation -> will ensure that the non-copper clearing is always complete.\n"
              "If it's not successful then the non-copper clearing will fail, too.\n"
              "- Clear -> the regular non-copper clearing.")
        )

        self.op_radio = RadioSet([
            {"label": _("Clear"), "value": "clear"},
            {"label": _("Isolation"), "value": "iso"}
        ], orientation='horizontal', stretch=False)
        self.op_radio.setObjectName("n_operation")

        self.grid3.addWidget(op_label, 13, 0)
        self.grid3.addWidget(self.op_radio, 13, 1)

        # Milling Type Radio Button
        self.milling_type_label = FCLabel('%s:' % _('Milling Type'))
        self.milling_type_label.setToolTip(
            _("Milling type:\n"
              "- climb / best for precision milling and to reduce tool usage\n"
              "- conventional / useful when there is no backlash compensation")
        )

        self.milling_type_radio = RadioSet([{'label': _('Climb'), 'value': 'cl'},
                                            {'label': _('Conventional'), 'value': 'cv'}])
        self.milling_type_radio.setToolTip(
            _("Milling type:\n"
              "- climb / best for precision milling and to reduce tool usage\n"
              "- conventional / useful when there is no backlash compensation")
        )
        self.milling_type_radio.setObjectName("n_milling_type")

        self.milling_type_label.setEnabled(False)
        self.milling_type_radio.setEnabled(False)

        self.grid3.addWidget(self.milling_type_label, 14, 0)
        self.grid3.addWidget(self.milling_type_radio, 14, 1)

        # Overlap Entry
        self.nccoverlabel = FCLabel('%s:' % _('Overlap'))
        self.nccoverlabel.setToolTip(
            _("How much (percentage) of the tool width to overlap each tool pass.\n"
              "Adjust the value starting with lower values\n"
              "and increasing it if areas that should be processed are still \n"
              "not processed.\n"
              "Lower values = faster processing, faster execution on CNC.\n"
              "Higher values = slow processing and slow execution on CNC\n"
              "due of too many paths.")
        )
        self.ncc_overlap_entry = FCDoubleSpinner(callback=self.confirmation_message, suffix='%')
        self.ncc_overlap_entry.set_precision(self.decimals)
        self.ncc_overlap_entry.setWrapping(True)
        self.ncc_overlap_entry.setRange(0.000, 99.9999)
        self.ncc_overlap_entry.setSingleStep(0.1)
        self.ncc_overlap_entry.setObjectName("n_overlap")

        self.grid3.addWidget(self.nccoverlabel, 15, 0)
        self.grid3.addWidget(self.ncc_overlap_entry, 15, 1)

        # Method
        self.methodlabel = FCLabel('%s:' % _('Method'))
        self.methodlabel.setToolTip(
            _("Algorithm for copper clearing:\n"
              "- Standard: Fixed step inwards.\n"
              "- Seed-based: Outwards from seed.\n"
              "- Line-based: Parallel lines.")
        )
        # self.ncc_method_radio = RadioSet([
        #     {"label": _("Standard"), "value": "standard"},
        #     {"label": _("Seed-based"), "value": "seed"},
        #     {"label": _("Straight lines"), "value": "lines"}
        # ], orientation='vertical', stretch=False)

        self.ncc_method_combo = FCComboBox2()
        self.ncc_method_combo.addItems(
            [_("Standard"), _("Seed"), _("Lines"), _("Combo")]
        )
        self.ncc_method_combo.setObjectName("n_method")

        self.grid3.addWidget(self.methodlabel, 16, 0)
        self.grid3.addWidget(self.ncc_method_combo, 16, 1)

        # Margin
        self.nccmarginlabel = FCLabel('%s:' % _('Margin'))
        self.nccmarginlabel.setToolTip(
            _("Bounding box margin.")
        )
        self.ncc_margin_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.ncc_margin_entry.set_precision(self.decimals)
        self.ncc_margin_entry.set_range(-10000.0000, 10000.0000)
        self.ncc_margin_entry.setObjectName("n_margin")

        self.grid3.addWidget(self.nccmarginlabel, 17, 0)
        self.grid3.addWidget(self.ncc_margin_entry, 17, 1)

        # Connect lines
        self.ncc_connect_cb = FCCheckBox('%s' % _("Connect"))
        self.ncc_connect_cb.setObjectName("n_connect")

        self.ncc_connect_cb.setToolTip(
            _("Draw lines between resulting\n"
              "segments to minimize tool lifts.")
        )
        self.grid3.addWidget(self.ncc_connect_cb, 18, 0)

        # Contour
        self.ncc_contour_cb = FCCheckBox('%s' % _("Contour"))
        self.ncc_contour_cb.setObjectName("n_contour")

        self.ncc_contour_cb.setToolTip(
            _("Cut around the perimeter of the polygon\n"
              "to trim rough edges.")
        )
        self.grid3.addWidget(self.ncc_contour_cb, 18, 1)

        # ## NCC Offset choice
        self.ncc_choice_offset_cb = FCCheckBox('%s' % _("Offset"))
        self.ncc_choice_offset_cb.setObjectName("n_offset")

        self.ncc_choice_offset_cb.setToolTip(
            _("If used, it will add an offset to the copper features.\n"
              "The copper clearing will finish to a distance\n"
              "from the copper features.")
        )
        self.grid3.addWidget(self.ncc_choice_offset_cb, 19, 0)

        # ## NCC Offset Entry
        self.ncc_offset_spinner = FCDoubleSpinner(callback=self.confirmation_message)
        self.ncc_offset_spinner.set_range(0.00, 10.00)
        self.ncc_offset_spinner.set_precision(4)
        self.ncc_offset_spinner.setWrapping(True)
        self.ncc_offset_spinner.setObjectName("n_offset_value")

        units = self.app.defaults['units'].upper()
        if units == 'MM':
            self.ncc_offset_spinner.setSingleStep(0.1)
        else:
            self.ncc_offset_spinner.setSingleStep(0.01)

        self.grid3.addWidget(self.ncc_offset_spinner, 19, 1)

        self.ois_ncc_offset = OptionalInputSection(self.ncc_choice_offset_cb, [self.ncc_offset_spinner])

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.grid3.addWidget(separator_line, 21, 0, 1, 2)

        self.apply_param_to_all = FCButton(_("Apply parameters to all tools"))
        self.apply_param_to_all.setIcon(QtGui.QIcon(self.app.resource_location + '/param_all32.png'))
        self.apply_param_to_all.setToolTip(
            _("The parameters in the current form will be applied\n"
              "on all the tools from the Tool Table.")
        )
        self.grid3.addWidget(self.apply_param_to_all, 22, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.grid3.addWidget(separator_line, 23, 0, 1, 2)

        # General Parameters
        self.gen_param_label = FCLabel('<b>%s</b>' % _("Common Parameters"))
        self.gen_param_label.setToolTip(
            _("Parameters that are common for all tools.")
        )
        self.grid3.addWidget(self.gen_param_label, 24, 0, 1, 2)

        # Rest Machining
        self.ncc_rest_cb = FCCheckBox('%s' % _("Rest"))
        self.ncc_rest_cb.setObjectName("n_rest_machining")

        self.ncc_rest_cb.setToolTip(
            _("If checked, use 'rest machining'.\n"
              "Basically it will process copper outside PCB features,\n"
              "using the biggest tool and continue with the next tools,\n"
              "from bigger to smaller, to process the copper features that\n"
              "could not be processed by previous tool, until there is\n"
              "nothing left to process or there are no more tools.\n\n"
              "If not checked, use the standard algorithm.")
        )

        self.grid3.addWidget(self.ncc_rest_cb, 25, 0, 1, 2)

        # Rest Margin
        self.rest_nccmarginlabel = FCLabel('%s:' % _('Margin'))
        self.rest_nccmarginlabel.setToolTip(
            _("Bounding box margin.")
        )
        self.rest_ncc_margin_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.rest_ncc_margin_entry.set_precision(self.decimals)
        self.rest_ncc_margin_entry.set_range(-10000.0000, 10000.0000)
        self.rest_ncc_margin_entry.setObjectName("n_margin")

        self.grid3.addWidget(self.rest_nccmarginlabel, 26, 0)
        self.grid3.addWidget(self.rest_ncc_margin_entry, 26, 1)

        # Rest Connect lines
        self.rest_ncc_connect_cb = FCCheckBox('%s' % _("Connect"))
        self.rest_ncc_connect_cb.setToolTip(
            _("Draw lines between resulting\n"
              "segments to minimize tool lifts.")
        )
        self.grid3.addWidget(self.rest_ncc_connect_cb, 27, 0)

        # Rest Contour
        self.rest_ncc_contour_cb = FCCheckBox('%s' % _("Contour"))
        self.rest_ncc_contour_cb.setToolTip(
            _("Cut around the perimeter of the polygon\n"
              "to trim rough edges.")
        )
        self.grid3.addWidget(self.rest_ncc_contour_cb, 27, 1)

        # ## Rest NCC Offset choice
        self.rest_ncc_choice_offset_cb = FCCheckBox('%s' % _("Offset"))
        self.rest_ncc_choice_offset_cb.setToolTip(
            _("If used, it will add an offset to the copper features.\n"
              "The copper clearing will finish to a distance\n"
              "from the copper features.")
        )
        self.grid3.addWidget(self.rest_ncc_choice_offset_cb, 28, 0)

        # ## Rest NCC Offset Entry
        self.rest_ncc_offset_spinner = FCDoubleSpinner(callback=self.confirmation_message)
        self.rest_ncc_offset_spinner.set_range(0.00, 10.00)
        self.rest_ncc_offset_spinner.set_precision(4)
        self.rest_ncc_offset_spinner.setWrapping(True)

        units = self.app.defaults['units'].upper()
        if units == 'MM':
            self.rest_ncc_offset_spinner.setSingleStep(0.1)
        else:
            self.rest_ncc_offset_spinner.setSingleStep(0.01)

        self.grid3.addWidget(self.rest_ncc_offset_spinner, 28, 1)

        self.rest_ois_ncc_offset = OptionalInputSection(self.rest_ncc_choice_offset_cb, [self.rest_ncc_offset_spinner])

        # Reference Selection Combo
        self.select_combo = FCComboBox2()
        self.select_combo.addItems(
            [_("Itself"), _("Area Selection"), _("Reference Object")]
        )
        self.select_combo.setObjectName("n_selection")

        self.select_label = FCLabel('%s:' % _("Selection"))
        self.select_label.setToolTip(
            _("Selection of area to be processed.\n"
              "- 'Itself' - the processing extent is based on the object that is processed.\n "
              "- 'Area Selection' - left mouse click to start selection of the area to be processed.\n"
              "- 'Reference Object' - will process the area specified by another object.")
        )
        self.grid3.addWidget(self.select_label, 29, 0, )
        self.grid3.addWidget(self.select_combo, 29, 1)

        self.reference_combo_type_label = FCLabel('%s:' % _("Type"))
        self.reference_combo_type_label.setToolTip(
            _("The type of FlatCAM object to be used as non copper clearing reference.\n"
              "It can be Gerber, Excellon or Geometry.")
        )
        self.reference_combo_type = FCComboBox2()
        self.reference_combo_type.addItems([_("Gerber"), _("Excellon"), _("Geometry")])

        self.grid3.addWidget(self.reference_combo_type_label, 31, 0, )
        self.grid3.addWidget(self.reference_combo_type, 31, 1)

        self.reference_combo = FCComboBox()
        self.reference_combo.setModel(self.app.collection)
        self.reference_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.reference_combo.is_last = True

        self.grid3.addWidget(self.reference_combo, 33, 0, 1, 2)

        self.reference_combo.hide()
        self.reference_combo_type.hide()
        self.reference_combo_type_label.hide()

        # Area Selection shape
        self.area_shape_label = FCLabel('%s:' % _("Shape"))
        self.area_shape_label.setToolTip(
            _("The kind of selection shape used for area selection.")
        )

        self.area_shape_radio = RadioSet([{'label': _("Square"), 'value': 'square'},
                                          {'label': _("Polygon"), 'value': 'polygon'}])

        self.grid3.addWidget(self.area_shape_label, 35, 0)
        self.grid3.addWidget(self.area_shape_radio, 35, 1)

        self.area_shape_label.hide()
        self.area_shape_radio.hide()

        # Check Tool validity
        self.valid_cb = FCCheckBox(label=_('Check validity'))
        self.valid_cb.setToolTip(
            _("If checked then the tools diameters are verified\n"
              "if they will provide a complete isolation.")
        )
        self.valid_cb.setObjectName("n_check")

        self.grid3.addWidget(self.valid_cb, 37, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.grid3.addWidget(separator_line, 39, 0, 1, 2)

        self.generate_ncc_button = FCButton(_('Generate Geometry'))
        self.generate_ncc_button.setIcon(QtGui.QIcon(self.app.resource_location + '/geometry32.png'))
        self.generate_ncc_button.setToolTip(
            _("Create the Geometry Object\n"
              "for non-copper routing.")
        )
        self.generate_ncc_button.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        self.tools_box.addWidget(self.generate_ncc_button)
        self.tools_box.addStretch()

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
        self.tools_box.addWidget(self.reset_button)
        # ############################ FINSIHED GUI ###################################
        # ############################################################################# 

    def parameters_ui(self, val):
        if val == 'iso':
            self.milling_type_label.setEnabled(True)
            self.milling_type_radio.setEnabled(True)

            self.nccoverlabel.setEnabled(False)
            self.ncc_overlap_entry.setEnabled(False)
            self.methodlabel.setEnabled(False)
            self.ncc_method_combo.setEnabled(False)
            self.nccmarginlabel.setEnabled(False)
            self.ncc_margin_entry.setEnabled(False)
            self.ncc_connect_cb.setEnabled(False)
            self.ncc_contour_cb.setEnabled(False)
            self.ncc_choice_offset_cb.setEnabled(False)
            self.ncc_offset_spinner.setEnabled(False)
        else:
            self.milling_type_label.setEnabled(False)
            self.milling_type_radio.setEnabled(False)

            self.nccoverlabel.setEnabled(True)
            self.ncc_overlap_entry.setEnabled(True)
            self.methodlabel.setEnabled(True)
            self.ncc_method_combo.setEnabled(True)
            self.nccmarginlabel.setEnabled(True)
            self.ncc_margin_entry.setEnabled(True)
            self.ncc_connect_cb.setEnabled(True)
            self.ncc_contour_cb.setEnabled(True)
            self.ncc_choice_offset_cb.setEnabled(True)
            self.ncc_offset_spinner.setEnabled(True)

    def on_toggle_reference(self):
        sel_combo = self.select_combo.get_value()

        if sel_combo == 0:  # itself
            self.reference_combo.hide()
            self.reference_combo_type.hide()
            self.reference_combo_type_label.hide()
            self.area_shape_label.hide()
            self.area_shape_radio.hide()

            # disable rest-machining for area painting
            self.ncc_rest_cb.setDisabled(False)
        elif sel_combo == 1:    # area selection
            self.reference_combo.hide()
            self.reference_combo_type.hide()
            self.reference_combo_type_label.hide()
            self.area_shape_label.show()
            self.area_shape_radio.show()

            # disable rest-machining for area painting
            # self.ncc_rest_cb.set_value(False)
            # self.ncc_rest_cb.setDisabled(True)
        else:
            self.reference_combo.show()
            self.reference_combo_type.show()
            self.reference_combo_type_label.show()
            self.area_shape_label.hide()
            self.area_shape_radio.hide()

            # disable rest-machining for area painting
            self.ncc_rest_cb.setDisabled(False)

    def on_rest_machining_check(self, state):
        if state:
            self.ncc_order_radio.set_value('rev')
            self.ncc_order_label.setDisabled(True)
            self.ncc_order_radio.setDisabled(True)

            self.nccmarginlabel.hide()
            self.ncc_margin_entry.hide()
            self.ncc_connect_cb.hide()
            self.ncc_contour_cb.hide()
            self.ncc_choice_offset_cb.hide()
            self.ncc_offset_spinner.hide()

            self.rest_nccmarginlabel.show()
            self.rest_ncc_margin_entry.show()
            self.rest_ncc_connect_cb.show()
            self.rest_ncc_contour_cb.show()
            self.rest_ncc_choice_offset_cb.show()
            self.rest_ncc_offset_spinner.show()

        else:
            self.ncc_order_label.setDisabled(False)
            self.ncc_order_radio.setDisabled(False)

            self.nccmarginlabel.show()
            self.ncc_margin_entry.show()
            self.ncc_connect_cb.show()
            self.ncc_contour_cb.show()
            self.ncc_choice_offset_cb.show()
            self.ncc_offset_spinner.show()

            self.rest_nccmarginlabel.hide()
            self.rest_ncc_margin_entry.hide()
            self.rest_ncc_connect_cb.hide()
            self.rest_ncc_contour_cb.hide()
            self.rest_ncc_choice_offset_cb.hide()
            self.rest_ncc_offset_spinner.hide()

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
