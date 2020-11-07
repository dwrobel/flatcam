# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Modified: Marius Adrian Stanciu (c)                 #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt

from appTool import AppTool
from copy import deepcopy

from appParsers.ParseGerber import Gerber
from camlib import Geometry, FlatCAMRTreeStorage, grace
from appGUI.GUIElements import FCTable, FCDoubleSpinner, FCCheckBox, FCInputDoubleSpinner, RadioSet, \
    FCButton, FCComboBox, FCLabel, FCComboBox2

from shapely.geometry import base, Polygon, MultiPolygon, LinearRing, Point
from shapely.ops import unary_union, linemerge

from matplotlib.backend_bases import KeyEvent as mpl_key_event

import numpy as np
from numpy import Inf
import traceback
import sys
import logging
import simplejson as json

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class ToolPaint(AppTool, Gerber):

    def __init__(self, app):
        self.app = app
        self.decimals = self.app.decimals

        AppTool.__init__(self, app)
        Geometry.__init__(self, geo_steps_per_circle=self.app.defaults["geometry_circle_steps"])
        
        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = PaintUI(layout=self.layout, app=self.app)
        self.toolName = self.ui.toolName

        # #############################################################################
        # ########################## VARIABLES ########################################
        # #############################################################################

        self.obj_name = ""
        self.paint_obj = None
        self.bound_obj_name = ""
        self.bound_obj = None

        self.circle_steps = int(self.app.defaults["geometry_circle_steps"])

        self.tooldia_list = []
        self.tooldia = None

        self.sel_rect = None
        self.o_name = None
        self.overlap = None
        self.connect = None
        self.contour = None
        self.select_method = None

        self.units = ''
        self.paint_tools = {}
        self.tooluid = 0

        self.first_click = False
        self.cursor_pos = None
        self.mouse_is_dragging = False

        self.mm = None
        self.mp = None
        self.mr = None
        self.kp = None

        # disconnect flags
        self.area_sel_disconnect_flag = False
        self.poly_sel_disconnect_flag = False

        self.sel_rect = []

        # store here if the grid snapping is active
        self.grid_status_memory = False

        # dict to store the polygons selected for painting; key is the shape added to be plotted and value is the poly
        self.poly_dict = {}

        # store here the default data for Geometry Data
        self.default_data = {}

        self.tool_type_item_options = ["C1", "C2", "C3", "C4", "B", "V"]

        self.form_fields = {
            "tools_paint_overlap":   self.ui.paintoverlap_entry,
            "tools_paint_offset":    self.ui.offset_entry,
            "tools_paint_method":    self.ui.paintmethod_combo,
            "tools_paint_connect":    self.ui.pathconnect_cb,
            "tools_paint_contour":   self.ui.paintcontour_cb,
        }

        self.name2option = {
            'p_overlap':    "tools_paint_overlap",
            'p_offset':     "tools_paint_offset",
            'p_method':     "tools_paint_method",
            'p_connect':    "tools_paint_connect",
            'p_contour':    "tools_paint_contour",
        }

        # store here the points for the "Polygon" area selection shape
        self.points = []
        # set this as True when in middle of drawing a "Polygon" area selection shape
        # it is made False by first click to signify that the shape is complete
        self.poly_drawn = False

        self.connect_signals_at_init()

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

    def on_type_obj_changed(self, val):
        obj_type = 0 if val == 'gerber' else 2
        self.ui.obj_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.ui.obj_combo.setCurrentIndex(0)
        self.ui.obj_combo.obj_type = {"gerber": "Gerber", "geometry": "Geometry"}[val]

        idx = self.ui.paintmethod_combo.findText(_("Laser_lines"))
        if self.ui.type_obj_radio.get_value().lower() == 'gerber':
            self.ui.paintmethod_combo.model().item(idx).setEnabled(True)
        else:
            self.ui.paintmethod_combo.model().item(idx).setEnabled(False)
            if self.ui.paintmethod_combo.get_value() == idx:    # if its Laser Lines
                self.ui.paintmethod_combo.set_value(idx+1)

    def on_reference_combo_changed(self):
        obj_type = self.ui.reference_type_combo.currentIndex()
        self.ui.reference_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.ui.reference_combo.setCurrentIndex(0)
        self.ui.reference_combo.obj_type = {0: "Gerber", 1: "Excellon", 2: "Geometry"}[obj_type]

    def connect_signals_at_init(self):
        # #############################################################################
        # ################################# Signals ###################################
        # #############################################################################
        self.ui.new_tooldia_entry.returnPressed.connect(self.on_tool_add)
        self.ui.deltool_btn.clicked.connect(self.on_tool_delete)

        self.ui.generate_paint_button.clicked.connect(self.on_paint_button_click)
        self.ui.selectmethod_combo.currentIndexChanged.connect(self.ui.on_selection)

        self.ui.reference_type_combo.currentIndexChanged.connect(self.on_reference_combo_changed)
        self.ui.type_obj_radio.activated_custom.connect(self.on_type_obj_changed)

        self.ui.apply_param_to_all.clicked.connect(self.on_apply_param_to_all_clicked)

        # adding tools
        self.ui.add_newtool_button.clicked.connect(lambda: self.on_tool_add())
        self.ui.addtool_from_db_btn.clicked.connect(self.on_paint_tool_add_from_db_clicked)

        self.ui.reset_button.clicked.connect(self.set_tool_ui)

        # Cleanup on Graceful exit (CTRL+ALT+X combo key)
        self.app.cleanup.connect(self.set_tool_ui)

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Alt+P', **kwargs)

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolPaint()")
        log.debug("ToolPaint().run() was launched ...")

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

        # all the tools are selected by default
        self.ui.tools_table.selectAll()

        self.app.ui.notebook.setTabText(2, _("Paint Tool"))

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
            self.ui.generate_paint_button.setDisabled(True)
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("No Tool Selected"))
            )
            self.blockSignals(False)
            return
        else:
            self.ui.generate_paint_button.setDisabled(False)

        for current_row in sel_rows:
            # populate the form with the data from the tool associated with the row parameter
            try:
                item = self.ui.tools_table.item(current_row, 3)
                if item is None:
                    return 'fail'
                tooluid = int(item.text())
            except Exception as e:
                log.debug("Tool missing. Add a tool in the Tool Table. %s" % str(e))
                return

            # update the QLabel that shows for which Tool we have the parameters in the UI form
            if len(sel_rows) == 1:
                cr = self.ui.tools_table.item(current_row, 0).text()
                self.ui.tool_data_label.setText(
                    "<b>%s: <font color='#0000FF'>%s %s</font></b>" % (_('Parameters for'), _("Tool"), cr)
                )

                try:
                    # set the form with data from the newly selected tool
                    for tooluid_key, tooluid_value in list(self.paint_tools.items()):
                        if int(tooluid_key) == tooluid:
                            self.storage_to_form(tooluid_value['data'])
                except Exception as e:
                    log.debug("ToolPaint ---> update_ui() " + str(e))
            else:
                self.ui.tool_data_label.setText(
                    "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("Multiple Tools"))
                )

        self.blockSignals(False)

    def storage_to_form(self, dict_storage):
        for k in self.form_fields:
            try:
                self.form_fields[k].set_value(dict_storage[k])
            except Exception as err:
                log.debug("ToolPaint.storage.form() --> %s" % str(err))

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

            for tooluid_key, tooluid_val in self.paint_tools.items():
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

        for tooluid_key, tooluid_val in self.paint_tools.items():
            if int(tooluid_key) == tooluid_item:
                # this will hold the 'data' key of the self.tools[tool] dictionary that corresponds to
                # the current row in the tool table
                temp_tool_data = tooluid_val['data']
                break

        for tooluid_key, tooluid_val in self.paint_tools.items():
            tooluid_val['data'] = deepcopy(temp_tool_data)

        self.app.inform.emit('[success] %s' % _("Current Tool parameters were applied to all tools."))

        self.blockSignals(False)

    def on_add_tool_by_key(self):
        tool_add_popup = FCInputDoubleSpinner(title='%s...' % _("New Tool"),
                                              text='%s:' % _('Enter a Tool Diameter'),
                                              min=0.0000, max=99.9999, decimals=self.decimals,
                                              parent=self.app.ui)
        tool_add_popup.set_icon(QtGui.QIcon(self.app.resource_location + '/letter_t_32.png'))

        val, ok = tool_add_popup.get_value()
        if ok:
            if float(val) == 0:
                self.app.inform.emit('[WARNING_NOTCL] %s' %
                                     _("Please enter a tool diameter with non-zero value, in Float format."))
                return
            self.on_tool_add(custom_dia=float(val))
        else:
            self.app.inform.emit('[WARNING_NOTCL] %s...' % _("Adding Tool cancelled"))

    def on_tooltable_cellwidget_change(self):
        cw = self.sender()

        assert isinstance(cw, QtWidgets.QComboBox), \
            "Expected a QtWidgets.QComboBox, got %s" % isinstance(cw, QtWidgets.QComboBox)

        cw_index = self.ui.tools_table.indexAt(cw.pos())
        cw_row = cw_index.row()
        cw_col = cw_index.column()

        current_uid = int(self.ui.tools_table.item(cw_row, 3).text())

        # if the sender is in the column with index 2 then we update the tool_type key
        if cw_col == 2:
            tt = cw.currentText()
            typ = 'Iso' if tt == 'V' else 'Rough'

            self.paint_tools[current_uid].update({
                'type': typ,
                'tool_type': tt,
            })

    def on_order_changed(self, order):
        if order != 'no':
            self.build_ui()

    def set_tool_ui(self):
        self.ui.tools_frame.show()
        self.reset_fields()

        # updated units
        self.units = self.app.defaults['units'].upper()

        # set the working variables to a known state
        self.paint_tools.clear()
        self.tooluid = 0

        self.default_data.clear()
        self.default_data.update({
            "name":                 '_paint',
            "plot":                 self.app.defaults["geometry_plot"],
            "cutz":                 float(self.app.defaults["tools_paint_cutz"]),
            "vtipdia":              float(self.app.defaults["tools_paint_tipdia"]),
            "vtipangle":            float(self.app.defaults["tools_paint_tipangle"]),
            "travelz":              float(self.app.defaults["geometry_travelz"]),
            "feedrate":             float(self.app.defaults["geometry_feedrate"]),
            "feedrate_z":           float(self.app.defaults["geometry_feedrate_z"]),
            "feedrate_rapid":       float(self.app.defaults["geometry_feedrate_rapid"]),
            "dwell":                self.app.defaults["geometry_dwell"],
            "dwelltime":            float(self.app.defaults["geometry_dwelltime"]),
            "multidepth":           self.app.defaults["geometry_multidepth"],
            "ppname_g":             self.app.defaults["geometry_ppname_g"],
            "depthperpass":         float(self.app.defaults["geometry_depthperpass"]),
            "extracut":             self.app.defaults["geometry_extracut"],
            "extracut_length":      self.app.defaults["geometry_extracut_length"],
            "toolchange":           self.app.defaults["geometry_toolchange"],
            "toolchangez":          float(self.app.defaults["geometry_toolchangez"]),
            "endz":                 float(self.app.defaults["geometry_endz"]),
            "endxy":                self.app.defaults["geometry_endxy"],

            "spindlespeed":         self.app.defaults["geometry_spindlespeed"],
            "toolchangexy":         self.app.defaults["geometry_toolchangexy"],
            "startz":               self.app.defaults["geometry_startz"],

            "area_exclusion":       self.app.defaults["geometry_area_exclusion"],
            "area_shape":           self.app.defaults["geometry_area_shape"],
            "area_strategy":        self.app.defaults["geometry_area_strategy"],
            "area_overz":           float(self.app.defaults["geometry_area_overz"]),
            "optimization_type":    self.app.defaults["geometry_optimization_type"],

            "tooldia":              self.app.defaults["tools_paint_tooldia"],
            "tools_paint_offset":   self.app.defaults["tools_paint_offset"],
            "tools_paint_method":    self.app.defaults["tools_paint_method"],
            "tools_paint_selectmethod":   self.app.defaults["tools_paint_selectmethod"],
            "tools_paint_connect":    self.app.defaults["tools_paint_connect"],
            "tools_paint_contour":   self.app.defaults["tools_paint_contour"],
            "tools_paint_overlap":   self.app.defaults["tools_paint_overlap"],
            "tools_paint_rest":      self.app.defaults["tools_paint_rest"],
        })

        # ## Init the GUI interface
        self.ui.order_radio.set_value(self.app.defaults["tools_paint_order"])
        self.ui.offset_entry.set_value(self.app.defaults["tools_paint_offset"])
        self.ui.paintmethod_combo.set_value(self.app.defaults["tools_paint_method"])
        self.ui.selectmethod_combo.set_value(self.app.defaults["tools_paint_selectmethod"])
        self.ui.area_shape_radio.set_value(self.app.defaults["tools_paint_area_shape"])
        self.ui.pathconnect_cb.set_value(self.app.defaults["tools_paint_connect"])
        self.ui.paintcontour_cb.set_value(self.app.defaults["tools_paint_contour"])
        self.ui.paintoverlap_entry.set_value(self.app.defaults["tools_paint_overlap"])

        self.ui.new_tooldia_entry.set_value(self.app.defaults["tools_paint_newdia"])
        self.ui.rest_cb.set_value(self.app.defaults["tools_paint_rest"])

        # # make the default object type, "Geometry"
        # self.type_obj_radio.set_value("geometry")

        # use the current selected object and make it visible in the Paint object combobox
        sel_list = self.app.collection.get_selected()
        if len(sel_list) == 1:
            active = self.app.collection.get_active()
            kind = active.kind
            if kind == 'gerber':
                self.ui.type_obj_radio.set_value(kind)
            else:
                kind = 'geometry'
                self.ui.type_obj_radio.set_value(kind)

            # run those once so the obj_type attribute is updated in the FCComboBoxes
            # to make sure that the last loaded object is displayed in the combobox
            self.on_type_obj_changed(val=kind)
            self.on_reference_combo_changed()

            self.ui.obj_combo.set_value(active.options['name'])
        else:
            kind = 'geometry'
            self.ui.type_obj_radio.set_value('geometry')

            # run those once so the obj_type attribute is updated in the FCComboBoxes
            # to make sure that the last loaded object is displayed in the combobox
            self.on_type_obj_changed(val=kind)
            self.on_reference_combo_changed()

        try:
            diameters = [float(self.app.defaults["tools_paint_tooldia"])]
        except (ValueError, TypeError):
            if isinstance(self.app.defaults["tools_paint_tooldia"], str):
                diameters = [eval(x) for x in self.app.defaults["tools_paint_tooldia"].split(",") if x != '']
            else:
                diameters = self.app.defaults["tools_paint_tooldia"]

        if not diameters:
            log.error("At least one tool diameter needed. Verify in Edit -> Preferences -> TOOLS -> NCC Tools.")
            self.build_ui()

            # if the Paint Method is "Single" disable the tool table context menu
            if self.default_data["tools_paint_selectmethod"] == "single":
                self.ui.tools_table.setContextMenuPolicy(Qt.NoContextMenu)
            return

        for dia in diameters:
            self.on_tool_add(custom_dia=dia)

        self.ui.on_rest_machining_check(state=self.app.defaults["tools_paint_rest"])

        # if the Paint Method is "Polygon Selection" disable the tool table context menu
        if self.default_data["tools_paint_selectmethod"] == 1:
            self.ui.tools_table.setContextMenuPolicy(Qt.NoContextMenu)

        # make sure that we can't get selection of Laser Lines for Geometry even if it's set in the Preferences
        # because we don't select the default object type in Preferences but here
        idx = self.ui.paintmethod_combo.findText(_("Laser_lines"))
        if self.ui.type_obj_radio.get_value().lower() == 'gerber':
            self.ui.paintmethod_combo.model().item(idx).setEnabled(True)
        else:
            self.ui.paintmethod_combo.model().item(idx).setEnabled(False)
            if self.ui.paintmethod_combo.get_value() == idx:  # if its Laser Lines
                self.ui.paintmethod_combo.set_value(idx + 1)

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
            new_tools[new_uid] = deepcopy(self.paint_tools[current_uid])
            new_uid += 1

        self.paint_tools = new_tools

        # the tools table changed therefore we need to rebuild it
        QtCore.QTimer.singleShot(20, self.build_ui)

    def build_ui(self):
        self.ui_disconnect()

        # updated units
        self.units = self.app.defaults['units'].upper()

        sorted_tools = []
        for k, v in self.paint_tools.items():
            sorted_tools.append(float('%.*f' % (self.decimals, float(v['tooldia']))))

        order = self.ui.order_radio.get_value()
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
            for tooluid_key, tooluid_value in self.paint_tools.items():
                if float('%.*f' % (self.decimals, tooluid_value['tooldia'])) == tool_sorted:
                    tool_id += 1

                    id_item = QtWidgets.QTableWidgetItem('%d' % int(tool_id))
                    id_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                    row_no = tool_id - 1
                    self.ui.tools_table.setItem(row_no, 0, id_item)  # Tool name/id

                    dia = QtWidgets.QTableWidgetItem('%.*f' % (self.decimals, tooluid_value['tooldia']))
                    dia.setFlags(QtCore.Qt.ItemIsEnabled)
                    self.ui.tools_table.setItem(row_no, 1, dia)  # Diameter

                    tool_type_item = FCComboBox()
                    for item in self.tool_type_item_options:
                        tool_type_item.addItem(item)
                        # tool_type_item.setStyleSheet('background-color: rgb(255,255,255)')
                    idx = tool_type_item.findText(tooluid_value['tool_type'])
                    tool_type_item.setCurrentIndex(idx)

                    tool_uid_item = QtWidgets.QTableWidgetItem(str(int(tooluid_key)))
                    self.ui.tools_table.setCellWidget(row_no, 2, tool_type_item)
                    # ## REMEMBER: THIS COLUMN IS HIDDEN IN OBJECTUI.PY # ##
                    self.ui.tools_table.setItem(row_no, 3, tool_uid_item)  # Tool unique ID

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

        # set the text on tool_data_label after loading the object
        sel_rows = set()
        sel_items = self.ui.tools_table.selectedItems()
        for it in sel_items:
            sel_rows.add(it.row())
        if len(sel_rows) > 1:
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("Multiple Tools"))
            )

    def on_tool_add(self, custom_dia=None):
        self.blockSignals(True)

        filename = self.app.tools_database_path()

        new_tools_dict = deepcopy(self.default_data)
        updated_tooldia = None

        # construct a list of all 'tooluid' in the self.iso_tools
        tool_uid_list = [int(tooluid_key) for tooluid_key in self.paint_tools]

        # find maximum from the temp_uid, add 1 and this is the new 'tooluid'
        max_uid = 0 if not tool_uid_list else max(tool_uid_list)
        tooluid = int(max_uid + 1)

        tool_dias = []
        for k, v in self.paint_tools.items():
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

            # we need only tool marked for Paint Tool
            if db_tool_val['data']['tool_target'] != _('Paint'):
                continue

            # if we find a tool with the same diameter in the Tools DB just update it's data
            if truncated_tooldia == db_tooldia:
                tool_found += 1
                for d in db_tool_val['data']:
                    if d.find('tools_paint') == 0:
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
                    if d.find('tools_paint') == 0:
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
        self.paint_tools.update({
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
        tool_uid_list = [int(tooluid_key) for tooluid_key in self.paint_tools]

        # find maximum from the temp_uid, add 1 and this is the new 'tooluid'
        max_uid = 0 if not tool_uid_list else max(tool_uid_list)
        self.tooluid = int(max_uid + 1)

        tool_dias = []
        for k, v in self.paint_tools.items():
            for tool_v in v.keys():
                if tool_v == 'tooldia':
                    tool_dias.append(self.app.dec_format(v[tool_v], self.decimals))

        truncated_tooldia = self.app.dec_format(tool_dia, self.decimals)
        if truncated_tooldia in tool_dias:
            if muted is None:
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled. Tool already in Tool Table."))
            self.blockSignals(False)
            return

        self.paint_tools.update({
            int(self.tooluid): {
                'tooldia':          truncated_tooldia,
                'offset':           'Path',
                'offset_value':     0.0,
                'type':             'Iso',
                'tool_type':        'V',
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
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("Wrong value format entered, use a number."))
                return

        for k, v in self.paint_tools.items():
            tool_dias = [float('%.*f' % (self.decimals, v[tool_v])) for tool_v in v.keys() if tool_v == 'tooldia']

        # identify the tool that was edited and get it's tooluid
        if new_tool_dia not in tool_dias:
            self.paint_tools[editeduid]['tooldia'] = new_tool_dia
            self.app.inform.emit('[success] %s' % _("Tool from Tool Table was edited."))
            self.blockSignals(False)
            self.build_ui()
            return

        # identify the old tool_dia and restore the text in tool table
        for k, v in self.paint_tools.items():
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
            self.paint_tools.clear()
            self.blockSignals(False)
            self.build_ui()
            return

        if rows_to_delete:
            try:
                for row in rows_to_delete:
                    tooluid_del = int(self.ui.tools_table.item(row, 3).text())
                    deleted_tools_list.append(tooluid_del)
            except TypeError:
                deleted_tools_list.append(rows_to_delete)

            for t in deleted_tools_list:
                self.paint_tools.pop(t, None)

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
                    self.paint_tools.pop(t, None)

        except AttributeError:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Delete failed. Select a tool to delete."))
            self.blockSignals(False)
            return
        except Exception as e:
            log.debug(str(e))

        self.app.inform.emit('[success] %s' % _("Tool(s) deleted from Tool Table."))
        self.blockSignals(False)
        self.build_ui()

    def on_paint_button_click(self):
        """
        Slot for clicking signal
        :return: None
        """

        self.app.defaults.report_usage("on_paint_button_click")

        self.first_click = False
        self.cursor_pos = None
        self.mouse_is_dragging = False

        prog_plot = True if self.app.defaults["tools_paint_plotting"] == 'progressive' else False
        if prog_plot:
            self.temp_shapes.clear(update=True)

        self.sel_rect = []

        obj_type = self.ui.type_obj_radio.get_value()
        self.circle_steps = int(self.app.defaults["gerber_circle_steps"]) if obj_type == 'gerber' else \
            int(self.app.defaults["geometry_circle_steps"])
        self.obj_name = self.ui.obj_combo.currentText()

        # Get source object.
        try:
            self.paint_obj = self.app.collection.get_by_name(str(self.obj_name))
        except Exception as e:
            log.debug("ToolPaint.on_paint_button_click() --> %s" % str(e))
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), self.obj_name))
            return

        if self.paint_obj is None:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Object not found"), self.paint_obj))
            return

        # test if the Geometry Object is multigeo with more than one tool and return Fail if True because
        # for now Paint don't work on MultiGeo with more than one tools
        if self.paint_obj.kind == 'geometry' and self.paint_obj.multigeo is True and len(self.paint_obj.tools) > 1:
            self.app.inform.emit('[ERROR_NOTCL] %s...' % _("Can't do Paint on MultiGeo geometries"))
            return 'Fail'

        self.o_name = '%s_mt_paint' % self.obj_name

        # use the selected tools in the tool table; get diameters
        self.tooldia_list = []
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
                self.tooldia_list.append(self.tooldia)
        else:
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("There are no tools selected in the Tool Table."))
            return

        self.select_method = self.ui.selectmethod_combo.get_value()
        if self.select_method == 0:  # _("All")
            self.paint_poly_all(self.paint_obj, tooldia=self.tooldia_list, outname=self.o_name)

        elif self.select_method == 1:   # _("Polygon Selection")
            # disengage the grid snapping since it may be hard to click on polygons with grid snapping on
            if self.app.ui.grid_snap_btn.isChecked():
                self.grid_status_memory = True
                self.app.ui.grid_snap_btn.trigger()
            else:
                self.grid_status_memory = False

            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Click on a polygon to paint it."))

            self.mr = self.app.plotcanvas.graph_event_connect('mouse_release', self.on_single_poly_mouse_release)
            self.kp = self.app.plotcanvas.graph_event_connect('key_press', self.on_key_press)

            if self.app.is_legacy is False:
                self.app.plotcanvas.graph_event_disconnect('mouse_release', self.app.on_mouse_click_release_over_plot)
                self.app.plotcanvas.graph_event_disconnect('mouse_press', self.app.on_mouse_click_over_plot)
            else:
                self.app.plotcanvas.graph_event_disconnect(self.app.mr)
                self.app.plotcanvas.graph_event_disconnect(self.app.mp)

            # disconnect flags
            self.poly_sel_disconnect_flag = True

        elif self.select_method == 2:   # _("Area Selection")
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

        elif self.select_method == 3:   # _("Reference Object")
            self.bound_obj_name = self.reference_combo.currentText()
            # Get source object.
            try:
                self.bound_obj = self.app.collection.get_by_name(self.bound_obj_name)
            except Exception:
                self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), self.obj_name))
                return "Could not retrieve object: %s" % self.obj_name

            self.paint_poly_ref(obj=self.paint_obj, sel_obj=self.bound_obj, tooldia=self.tooldia_list,
                                outname=self.o_name)

    # To be called after clicking on the plot.
    def on_single_poly_mouse_release(self, event):
        if self.app.is_legacy is False:
            event_pos = event.pos
            right_button = 2
            event_is_dragging = self.app.event_is_dragging
        else:
            event_pos = (event.xdata, event.ydata)
            right_button = 3
            event_is_dragging = self.app.ui.popMenu.mouse_is_panning

        try:
            x = float(event_pos[0])
            y = float(event_pos[1])
        except TypeError:
            return

        event_pos = (x, y)
        curr_pos = self.app.plotcanvas.translate_coords(event_pos)

        # do paint single only for left mouse clicks
        if event.button == 1:
            clicked_poly = self.find_polygon(point=(curr_pos[0], curr_pos[1]), geoset=self.paint_obj.solid_geometry)

            if clicked_poly:
                if clicked_poly not in self.poly_dict.values():
                    shape_id = self.app.tool_shapes.add(tolerance=self.paint_obj.drawing_tolerance,
                                                        layer=0,
                                                        shape=clicked_poly,
                                                        color=self.app.defaults['global_sel_draw_color'] + 'AF',
                                                        face_color=self.app.defaults['global_sel_draw_color'] + 'AF',
                                                        visible=True)
                    self.poly_dict[shape_id] = clicked_poly
                    self.app.inform.emit(
                        '%s: %d. %s' % (_("Added polygon"),
                                        int(len(self.poly_dict)),
                                        _("Click to add next polygon or right click to start."))
                    )
                else:
                    try:
                        for k, v in list(self.poly_dict.items()):
                            if v == clicked_poly:
                                self.app.tool_shapes.remove(k)
                                self.poly_dict.pop(k)
                                break
                    except TypeError:
                        return
                    self.app.inform.emit(
                        '%s. %s' % (_("Removed polygon"),
                                    _("Click to add/remove next polygon or right click to start."))
                    )

                self.app.tool_shapes.redraw()
            else:
                self.app.inform.emit(_("No polygon detected under click position."))

        elif event.button == right_button and event_is_dragging is False:
            # restore the Grid snapping if it was active before
            if self.grid_status_memory is True:
                self.app.ui.grid_snap_btn.trigger()

            if self.app.is_legacy is False:
                self.app.plotcanvas.graph_event_disconnect('mouse_release', self.on_single_poly_mouse_release)
                self.app.plotcanvas.graph_event_disconnect('key_press', self.on_key_press)
            else:
                self.app.plotcanvas.graph_event_disconnect(self.mr)
                self.app.plotcanvas.graph_event_disconnect(self.kp)

            self.app.mp = self.app.plotcanvas.graph_event_connect('mouse_press',
                                                                  self.app.on_mouse_click_over_plot)
            self.app.mr = self.app.plotcanvas.graph_event_connect('mouse_release',
                                                                  self.app.on_mouse_click_release_over_plot)

            # disconnect flags
            self.poly_sel_disconnect_flag = False

            self.app.tool_shapes.clear(update=True)

            if self.poly_dict:
                poly_list = deepcopy(list(self.poly_dict.values()))
                self.paint_poly(self.paint_obj, inside_pt=(curr_pos[0], curr_pos[1]), poly_list=poly_list,
                                tooldia=self.tooldia_list)
                self.poly_dict.clear()
            else:
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("List of single polygons is empty. Aborting."))

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

        try:
            x = float(event_pos[0])
            y = float(event_pos[1])
        except TypeError:
            return

        event_pos = (x, y)

        shape_type = self.ui.area_shape_radio.get_value()

        curr_pos = self.app.plotcanvas.translate_coords(event_pos)
        if self.app.grid_status():
            curr_pos = self.app.geo_editor.snap(curr_pos[0], curr_pos[1])

        x1, y1 = curr_pos[0], curr_pos[1]

        # do paint single only for left mouse clicks
        if event.button == 1:
            if shape_type == "square":
                if not self.first_click:
                    self.first_click = True
                    self.app.inform.emit('[WARNING_NOTCL] %s' % _("Click the end point of the area."))

                    self.cursor_pos = self.app.plotcanvas.translate_coords(event_pos)
                    if self.app.grid_status():
                        self.cursor_pos = self.app.geo_editor.snap(self.cursor_pos[0], self.cursor_pos[1])
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
            self.paint_poly_area(obj=self.paint_obj, tooldia=self.tooldia_list, sel_obj=self.sel_rect,
                                 outname=self.o_name)

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

        try:
            x = float(event_pos[0])
            y = float(event_pos[1])
        except TypeError:
            return

        curr_pos = self.app.plotcanvas.translate_coords((x, y))

        # detect mouse dragging motion
        if event_is_dragging == 1:
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
                try:
                    if self.app.is_legacy is False:
                        self.app.plotcanvas.graph_event_disconnect('mouse_release', self.on_mouse_release)
                        self.app.plotcanvas.graph_event_disconnect('mouse_move', self.on_mouse_move)
                        self.app.plotcanvas.graph_event_disconnect('key_press', self.on_key_press)
                    else:
                        self.app.plotcanvas.graph_event_disconnect(self.mr)
                        self.app.plotcanvas.graph_event_disconnect(self.mm)
                        self.app.plotcanvas.graph_event_disconnect(self.kp)
                except Exception as e:
                    log.debug("ToolPaint.on_key_press() _1 --> %s" % str(e))

                self.app.mp = self.app.plotcanvas.graph_event_connect('mouse_press',
                                                                      self.app.on_mouse_click_over_plot)
                self.app.mm = self.app.plotcanvas.graph_event_connect('mouse_move',
                                                                      self.app.on_mouse_move_over_plot)
                self.app.mr = self.app.plotcanvas.graph_event_connect('mouse_release',
                                                                      self.app.on_mouse_click_release_over_plot)

            if self.poly_sel_disconnect_flag is False:
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

                self.app.mr = self.app.plotcanvas.graph_event_connect('mouse_release',
                                                                      self.app.on_mouse_click_release_over_plot)
                self.app.mp = self.app.plotcanvas.graph_event_connect('mouse_press',
                                                                      self.app.on_mouse_click_over_plot)
            self.points = []
            self.poly_drawn = False
            self.poly_dict.clear()

            self.delete_moving_selection_shape()
            self.delete_tool_selection_shape()

    def paint_polygon_worker(self, polyg, tooldiameter, paint_method, over, conn, cont, prog_plot, obj):

        cpoly = None

        if paint_method == 0:   # _("Standard")
            try:
                # Type(cp) == FlatCAMRTreeStorage | None
                cpoly = self.clear_polygon(polyg,
                                           tooldia=tooldiameter,
                                           steps_per_circle=self.circle_steps,
                                           overlap=over,
                                           contour=cont,
                                           connect=conn,
                                           prog_plot=prog_plot)
            except grace:
                return "fail"
            except Exception as ee:
                log.debug("ToolPaint.paint_polygon_worker() Standard --> %s" % str(ee))
        elif paint_method == 1:  # _("Seed")
            try:
                # Type(cp) == FlatCAMRTreeStorage | None
                cpoly = self.clear_polygon2(polyg,
                                            tooldia=tooldiameter,
                                            steps_per_circle=self.circle_steps,
                                            overlap=over,
                                            contour=cont,
                                            connect=conn,
                                            prog_plot=prog_plot)
            except grace:
                return "fail"
            except Exception as ee:
                log.debug("ToolPaint.paint_polygon_worker() Seed --> %s" % str(ee))
        elif paint_method == 2:  # _("Lines")
            try:
                # Type(cp) == FlatCAMRTreeStorage | None
                cpoly = self.clear_polygon3(polyg,
                                            tooldia=tooldiameter,
                                            steps_per_circle=self.circle_steps,
                                            overlap=over,
                                            contour=cont,
                                            connect=conn,
                                            prog_plot=prog_plot)
            except grace:
                return "fail"
            except Exception as ee:
                log.debug("ToolPaint.paint_polygon_worker() Lines --> %s" % str(ee))
        elif paint_method == 3:  # _("Laser_lines")
            try:
                # line = None
                # aperture_size = None

                # the key is the aperture type and the val is a list of geo elements
                flash_el_dict = {}
                # the key is the aperture size, the val is a list of geo elements
                traces_el_dict = {}

                # find the flashes and the lines that are in the selected polygon and store them separately
                for apid, apval in obj.apertures.items():
                    for geo_el in apval['geometry']:
                        if apval["size"] == 0.0:
                            if apval["size"] in traces_el_dict:
                                traces_el_dict[apval["size"]].append(geo_el)
                            else:
                                traces_el_dict[apval["size"]] = [geo_el]

                        if 'follow' in geo_el and geo_el['follow'].within(polyg):
                            if isinstance(geo_el['follow'], Point):
                                if apval["type"] == 'C':
                                    if 'C' in flash_el_dict:
                                        flash_el_dict['C'].append(geo_el)
                                    else:
                                        flash_el_dict['C'] = [geo_el]
                                elif apval["type"] == 'O':
                                    if 'O' in flash_el_dict:
                                        flash_el_dict['O'].append(geo_el)
                                    else:
                                        flash_el_dict['O'] = [geo_el]
                                elif apval["type"] == 'R':
                                    if 'R' in flash_el_dict:
                                        flash_el_dict['R'].append(geo_el)
                                    else:
                                        flash_el_dict['R'] = [geo_el]
                            else:
                                aperture_size = apval['size']

                                if aperture_size in traces_el_dict:
                                    traces_el_dict[aperture_size].append(geo_el)
                                else:
                                    traces_el_dict[aperture_size] = [geo_el]

                cpoly = FlatCAMRTreeStorage()
                pads_lines_list = []

                # process the flashes found in the selected polygon with the 'lines' method for rectangular
                # flashes and with _("Seed") for oblong and circular flashes
                # and pads (flashes) need the contour therefore I override the GUI settings with always True
                for ap_type in flash_el_dict:
                    for elem in flash_el_dict[ap_type]:
                        if 'solid' in elem:
                            if ap_type == 'C':
                                f_o = self.clear_polygon2(elem['solid'],
                                                          tooldia=tooldiameter,
                                                          steps_per_circle=self.app.defaults[
                                                              "geometry_circle_steps"],
                                                          overlap=over,
                                                          contour=True,
                                                          connect=conn,
                                                          prog_plot=prog_plot)
                                pads_lines_list += [p for p in f_o.get_objects() if p]
                            # this is the same as above but I keep it in case I will modify something in the future
                            elif ap_type == 'O':
                                f_o = self.clear_polygon2(elem['solid'],
                                                          tooldia=tooldiameter,
                                                          steps_per_circle=self.app.defaults[
                                                              "geometry_circle_steps"],
                                                          overlap=over,
                                                          contour=True,
                                                          connect=conn,
                                                          prog_plot=prog_plot)
                                pads_lines_list += [p for p in f_o.get_objects() if p]

                            elif ap_type == 'R':
                                f_o = self.clear_polygon3(elem['solid'],
                                                          tooldia=tooldiameter,
                                                          steps_per_circle=self.app.defaults[
                                                              "geometry_circle_steps"],
                                                          overlap=over,
                                                          contour=True,
                                                          connect=conn,
                                                          prog_plot=prog_plot)

                                pads_lines_list += [p for p in f_o.get_objects() if p]

                # add the lines from pads to the storage
                try:
                    for lin in pads_lines_list:
                        if lin:
                            cpoly.insert(lin)
                except TypeError:
                    cpoly.insert(pads_lines_list)

                copper_lines_list = []
                # process the traces found in the selected polygon using the 'laser_lines' method,
                # method which will follow the 'follow' line therefore use the longer path possible for the
                # laser, therefore the acceleration will play a smaller factor
                for aperture_size in traces_el_dict:
                    for elem in traces_el_dict[aperture_size]:
                        line = elem['follow']
                        if line:
                            t_o = self.fill_with_lines(line, aperture_size,
                                                       tooldia=tooldiameter,
                                                       steps_per_circle=self.app.defaults[
                                                           "geometry_circle_steps"],
                                                       overlap=over,
                                                       contour=cont,
                                                       connect=conn,
                                                       prog_plot=prog_plot)

                            copper_lines_list += [p for p in t_o.get_objects() if p]

                # add the lines from copper features to storage but first try to make as few lines as possible
                # by trying to fuse them
                lines_union = linemerge(unary_union(copper_lines_list))
                try:
                    for lin in lines_union:
                        if lin:
                            cpoly.insert(lin)
                except TypeError:
                    cpoly.insert(lines_union)
                # # determine the Gerber follow line
                # for apid, apval in obj.apertures.items():
                #     for geo_el in apval['geometry']:
                #         if 'solid' in geo_el:
                #             if Point(inside_pt).within(geo_el['solid']):
                #                 if not isinstance(geo_el['follow'], Point):
                #                     line = geo_el['follow']
                #
                #                     if apval['type'] == 'C':
                #                         aperture_size = apval['size']
                #                     else:
                #                         if apval['width'] > apval['height']:
                #                             aperture_size = apval['height']
                #                         else:
                #                             aperture_size = apval['width']
                #
                # if line:
                #     cpoly = self.fill_with_lines(line, aperture_size,
                #                                  tooldia=tooldiameter,
                #                                  steps_per_circle=self.circle_steps,
                #                                  overlap=over,
                #                                  contour=cont,
                #                                  connect=conn,
                #                                  prog_plot=prog_plot)
            except grace:
                return "fail"
            except Exception as ee:
                log.debug("ToolPaint.paint_polygon_worker() Laser Lines --> %s" % str(ee))
        elif paint_method == 4:  # _("Combo")
            try:
                self.app.inform.emit(_("Painting polygon with method: lines."))
                cpoly = self.clear_polygon3(polyg,
                                            tooldia=tooldiameter,
                                            steps_per_circle=self.circle_steps,
                                            overlap=over,
                                            contour=cont,
                                            connect=conn,
                                            prog_plot=prog_plot)

                if cpoly and cpoly.objects:
                    pass
                else:
                    self.app.inform.emit(_("Failed. Painting polygon with method: seed."))
                    cpoly = self.clear_polygon2(polyg,
                                                tooldia=tooldiameter,
                                                steps_per_circle=self.circle_steps,
                                                overlap=over,
                                                contour=cont,
                                                connect=conn,
                                                prog_plot=prog_plot)
                    if cpoly and cpoly.objects:
                        pass
                    else:
                        self.app.inform.emit(_("Failed. Painting polygon with method: standard."))
                        cpoly = self.clear_polygon(polyg,
                                                   tooldia=tooldiameter,
                                                   steps_per_circle=self.circle_steps,
                                                   overlap=over,
                                                   contour=cont,
                                                   connect=conn,
                                                   prog_plot=prog_plot)
            except grace:
                return "fail"
            except Exception as ee:
                log.debug("ToolPaint.paint_polygon_worker() Combo --> %s" % str(ee))

        if cpoly and cpoly.objects:
            return cpoly
        else:
            self.app.inform.emit('[ERROR_NOTCL] %s' % _('Geometry could not be painted completely'))
            return None

    def paint_geo(self, obj, geometry, tooldia=None, order=None, method=None, outname=None,
                  tools_storage=None, plot=True, run_threaded=True):
        """
        Paints a given geometry.

        :param obj:             painted object
        :param geometry:        geometry to Paint
        :param tooldia:         Diameter of the painting tool
        :param order:           if the tools are ordered and how
        :param outname:         Name of the resulting Geometry Object.
        :param method:          choice out of _("Seed"), 'normal', 'lines'
        :param tools_storage:   whether to use the current tools_storage self.paints_tools or a different one.
                                Usage of the different one is related to when this function is called
                                from a TcL command.
        :param plot:
        :param run_threaded:
        :return: None
        """

        paint_method = method if method is not None else self.ui.paintmethod_combo.get_value()
        # determine if to use the progressive plotting
        prog_plot = True if self.app.defaults["tools_paint_plotting"] == 'progressive' else False

        name = outname if outname is not None else self.obj_name + "_paint"
        order = order if order is not None else self.ui.order_radio.get_value()
        tools_storage = self.paint_tools if tools_storage is None else tools_storage

        sorted_tools = []
        if tooldia is not None:
            try:
                sorted_tools = [float(eval(dia)) for dia in tooldia.split(",") if dia != '']
            except AttributeError:
                if not isinstance(tooldia, list):
                    sorted_tools = [float(tooldia)]
                else:
                    sorted_tools = tooldia
        else:
            table_items = self.ui.tools_table.selectedItems()
            sel_rows = {t.row() for t in table_items}
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
                sorted_tools.append(self.tooldia)
            if not sorted_tools:
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("There are no tools selected in the Tool Table."))
                return 'fail'

        # Initializes the new geometry object
        def job_normal_clear(geo_obj, app_obj):
            tool_dia = None
            current_uid = None
            final_solid_geometry = []
            old_disp_number = 0

            # sort the tools if we have an order selected in the UI
            if order == 'fwd':
                sorted_tools.sort(reverse=False)
            elif order == 'rev':
                sorted_tools.sort(reverse=True)
            else:
                pass

            for tool_dia in sorted_tools:
                log.debug("Starting geometry processing for tool: %s" % str(tool_dia))
                msg = '[success] %s %s%s %s' % (_('Painting with tool diameter = '),
                                                str(tool_dia),
                                                self.units.lower(),
                                                _('started'))
                self.app.inform.emit(msg)
                self.app.proc_container.update_view_text(' %d%%' % 0)

                # find the tooluid associated with the current tool_dia so we know what tool to use
                for k, v in tools_storage.items():
                    if float('%.*f' % (self.decimals, v['tooldia'])) == float('%.*f' % (self.decimals, tool_dia)):
                        current_uid = int(k)

                if not current_uid:
                    return "fail"

                # determine the tool parameters to use
                over = float(tools_storage[current_uid]['data']['tools_paint_overlap']) / 100.0
                conn = tools_storage[current_uid]['data']['tools_paint_connect']
                cont = tools_storage[current_uid]['data']['tools_paint_contour']

                paint_offset = float(tools_storage[current_uid]['data']['tools_paint_offset'])

                poly_buf = []
                for pol in geometry:
                    buffered_pol = pol.buffer(-paint_offset)
                    if buffered_pol and not buffered_pol.is_empty:
                        poly_buf.append(buffered_pol)

                if not poly_buf:
                    self.app.inform.emit('[WARNING_NOTCL] %s' % _("Margin parameter too big. Tool is not used"))
                    continue

                # variables to display the percentage of work done
                geo_len = len(poly_buf)

                log.warning("Total number of polygons to be cleared. %s" % str(geo_len))

                pol_nr = 0

                # -----------------------------
                # effective polygon clearing job
                # -----------------------------
                try:
                    cp = []
                    try:
                        for pp in poly_buf:
                            # provide the app with a way to process the GUI events when in a blocking loop
                            QtWidgets.QApplication.processEvents()
                            if self.app.abort_flag:
                                # graceful abort requested by the user
                                raise grace
                            geo_res = self.paint_polygon_worker(pp, tooldiameter=tool_dia, over=over, conn=conn,
                                                                cont=cont, paint_method=paint_method, obj=obj,
                                                                prog_plot=prog_plot)
                            if geo_res:
                                cp.append(geo_res)
                            pol_nr += 1
                            disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 100]))
                            # log.debug("Polygons cleared: %d" % pol_nr)

                            if old_disp_number < disp_number <= 100:
                                self.app.proc_container.update_view_text(' %d%%' % disp_number)
                                old_disp_number = disp_number
                    except TypeError:
                        # provide the app with a way to process the GUI events when in a blocking loop
                        QtWidgets.QApplication.processEvents()
                        if self.app.abort_flag:
                            # graceful abort requested by the user
                            raise grace

                        geo_res = self.paint_polygon_worker(poly_buf, tooldiameter=tool_dia, over=over, conn=conn,
                                                            cont=cont, paint_method=paint_method, obj=obj,
                                                            prog_plot=prog_plot)
                        if geo_res:
                            cp.append(geo_res)

                    total_geometry = []
                    if cp:
                        for x in cp:
                            total_geometry += list(x.get_objects())

                        # clean the geometry
                        new_geo = [g for g in total_geometry if g and not g.is_empty]
                        total_geometry = new_geo
                        final_solid_geometry += total_geometry
                except grace:
                    return "fail"
                except Exception as e:
                    log.debug("Could not Paint the polygons. %s" % str(e))
                    mssg = '[ERROR] %s\n%s' % (_("Could not do Paint. Try a different combination of parameters. "
                                                 "Or a different method of Paint"), str(e))
                    self.app.inform.emit(mssg)
                    continue

                # add the solid_geometry to the current too in self.paint_tools (tools_storage)
                # dictionary and then reset the temporary list that stored that solid_geometry
                tools_storage[current_uid]['solid_geometry'] = deepcopy(total_geometry)
                tools_storage[current_uid]['data']['name'] = name

            # clean the progressive plotted shapes if it was used
            if self.app.defaults["tools_paint_plotting"] == 'progressive':
                self.temp_shapes.clear(update=True)

            # delete tools with empty geometry
            # look for keys in the tools_storage dict that have 'solid_geometry' values empty
            for uid in list(tools_storage.keys()):
                # if the solid_geometry (type=list) is empty
                if not tools_storage[uid]['solid_geometry']:
                    tools_storage.pop(uid, None)

            if not tools_storage:
                return 'fail'

            geo_obj.options["cnctooldia"] = str(tool_dia)
            # this will turn on the FlatCAMCNCJob plot for multiple tools
            geo_obj.multigeo = True
            geo_obj.multitool = True
            geo_obj.tools.clear()
            geo_obj.tools = dict(tools_storage)

            geo_obj.solid_geometry = unary_union(final_solid_geometry)

            try:
                if isinstance(geo_obj.solid_geometry, list):
                    a, b, c, d = MultiPolygon(geo_obj.solid_geometry).bounds
                else:
                    a, b, c, d = geo_obj.solid_geometry.bounds

                geo_obj.options['xmin'] = a
                geo_obj.options['ymin'] = b
                geo_obj.options['xmax'] = c
                geo_obj.options['ymax'] = d
            except Exception as ee:
                log.debug("ToolPaint.paint_poly.job_init() bounds error --> %s" % str(ee))
                return

            # test if at least one tool has solid_geometry. If no tool has solid_geometry we raise an Exception
            has_solid_geo = 0
            for tooluid in geo_obj.tools:
                if geo_obj.tools[tooluid]['solid_geometry']:
                    has_solid_geo += 1

            if has_solid_geo == 0:
                app_obj.inform.emit('[ERROR] %s' %
                                    _("There is no Painting Geometry in the file.\n"
                                      "Usually it means that the tool diameter is too big for the painted geometry.\n"
                                      "Change the painting parameters and try again."))
                return "fail"

            # Experimental...
            # print("Indexing...", end=' ')
            # geo_obj.make_index()

        # Initializes the new geometry object
        def job_rest_clear(geo_obj, app_obj):
            current_uid = None
            final_solid_geometry = []
            old_disp_number = 0

            # sort the tools reversed for the rest machining
            sorted_tools.sort(reverse=True)

            paint_offset = self.ui.rest_offset_entry.get_value()

            poly_buf = []
            for pol in geometry:
                buffered_pol = pol.buffer(-paint_offset)
                if buffered_pol and not buffered_pol.is_empty:
                    try:
                        for x in buffered_pol:
                            poly_buf.append(x)
                    except TypeError:
                        poly_buf.append(buffered_pol)

            poly_buf = unary_union(poly_buf)

            if not poly_buf:
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("Margin parameter too big. Tool is not used"))
                return 'fail'

            # variables to display the percentage of work done
            geo_len = len(poly_buf)

            log.warning("Total number of polygons to be cleared. %s" % str(geo_len))

            for tool_dia in sorted_tools:
                log.debug("Starting geometry processing for tool: %s" % str(tool_dia))
                msg = '[success] %s %s%s %s' % (_('Painting with tool diameter = '),
                                                str(tool_dia),
                                                self.units.lower(),
                                                _('started'))
                self.app.inform.emit(msg)
                self.app.proc_container.update_view_text(' %d%%' % 0)

                # find the tooluid associated with the current tool_dia so we know what tool to use
                for k, v in tools_storage.items():
                    if float('%.*f' % (self.decimals, v['tooldia'])) == float('%.*f' % (self.decimals, tool_dia)):
                        current_uid = int(k)

                if not current_uid:
                    return "fail"

                # store here the cleared geometry
                # cleared_geo = []

                # determine the tool parameters to use
                over = float(tools_storage[current_uid]['data']['tools_paint_overlap']) / 100.0
                conn = tools_storage[current_uid]['data']['tools_paint_connect']
                cont = tools_storage[current_uid]['data']['tools_paint_contour']

                pol_nr = 0

                # store here the parts of polygons that could not be cleared; actually those are parts of polygons
                rest_list = []

                # -----------------------------
                # effective polygon clearing job
                # -----------------------------
                try:
                    cleared_geo = []
                    try:
                        for pp in poly_buf:
                            # provide the app with a way to process the GUI events when in a blocking loop
                            QtWidgets.QApplication.processEvents()
                            if self.app.abort_flag:
                                # graceful abort requested by the user
                                raise grace

                            # speedup the clearing by not trying to clear polygons that is clear they can't be
                            # cleared with the current tool. this tremendously reduce the clearing time
                            check_dist = -tool_dia / 2.0
                            check_buff = pp.buffer(check_dist)
                            if not check_buff or check_buff.is_empty:
                                continue

                            geo_res = self.paint_polygon_worker(pp, tooldiameter=tool_dia, over=over, conn=conn,
                                                                cont=cont, paint_method=paint_method, obj=obj,
                                                                prog_plot=prog_plot)
                            geo_elems = list(geo_res.get_objects())
                            # See if the polygon was completely cleared
                            pp_cleared = unary_union(geo_elems).buffer(tool_dia / 2.0)
                            rest = pp.difference(pp_cleared)
                            if rest and not rest.is_empty:
                                try:
                                    for r in rest:
                                        if r.is_valid:
                                            rest_list.append(r)
                                except TypeError:
                                    if rest.is_valid:
                                        rest_list.append(rest)

                            if geo_res:
                                cleared_geo += geo_elems
                            pol_nr += 1
                            disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 100]))
                            # log.debug("Polygons cleared: %d" % pol_nr)

                            if old_disp_number < disp_number <= 100:
                                self.app.proc_container.update_view_text(' %d%%' % disp_number)
                                old_disp_number = disp_number
                    except TypeError:
                        # provide the app with a way to process the GUI events when in a blocking loop
                        QtWidgets.QApplication.processEvents()
                        if self.app.abort_flag:
                            # graceful abort requested by the user
                            raise grace

                        # speedup the clearing by not trying to clear polygons that is clear they can't be
                        # cleared with the current tool. this tremendously reduce the clearing time
                        check_dist = -tool_dia / 2.0
                        check_buff = poly_buf.buffer(check_dist)
                        if not check_buff or check_buff.is_empty:
                            continue

                        geo_res = self.paint_polygon_worker(poly_buf, tooldiameter=tool_dia, over=over, conn=conn,
                                                            cont=cont, paint_method=paint_method, obj=obj,
                                                            prog_plot=prog_plot)
                        geo_elems = list(geo_res.get_objects())

                        # See if the polygon was completely cleared
                        pp_cleared = unary_union(geo_elems).buffer(tool_dia / 2.0)
                        rest = poly_buf.difference(pp_cleared)
                        if rest and not rest.is_empty:
                            try:
                                for r in rest:
                                    if r.is_valid:
                                        rest_list.append(r)
                            except TypeError:
                                if rest.is_valid:
                                    rest_list.append(rest)

                        if geo_res:
                            cleared_geo += geo_elems

                except grace:
                    return "fail"
                except Exception as e:
                    log.debug("Could not Paint the polygons. %s" % str(e))
                    msg = '[ERROR] %s\n%s' % (_("Could not do Paint. Try a different combination of parameters. "
                                                "Or a different method of Paint"), str(e))
                    self.app.inform.emit(msg)
                    continue

                if cleared_geo:
                    final_solid_geometry += cleared_geo

                    # add the solid_geometry to the current too in self.paint_tools (tools_storage)
                    # dictionary and then reset the temporary list that stored that solid_geometry
                    tools_storage[current_uid]['solid_geometry'] = deepcopy(cleared_geo)
                    tools_storage[current_uid]['data']['name'] = name
                    geo_obj.tools[current_uid] = dict(tools_storage[current_uid])
                else:
                    log.debug("There are no geometries in the cleared polygon.")

                # Area to clear next
                log.debug("Generating rest geometry for the next tool.")

                buffered_cleared = unary_union(cleared_geo)
                buffered_cleared = buffered_cleared.buffer(tool_dia / 2.0)
                poly_buf = poly_buf.difference(buffered_cleared)

                tmp = []
                try:
                    for p in poly_buf:
                        if p.is_valid:
                            tmp.append(p)
                except TypeError:
                    if poly_buf.is_valid:
                        tmp.append(poly_buf)

                tmp += rest_list

                poly_buf = MultiPolygon(tmp)
                if not poly_buf.is_valid:
                    poly_buf = unary_union(tmp)

                if not poly_buf or poly_buf.is_empty or not poly_buf.is_valid:
                    log.debug("Rest geometry empty. Breaking.")
                    break

            geo_obj.multigeo = True
            geo_obj.options["cnctooldia"] = '0.0'

            # clean the progressive plotted shapes if it was used
            if self.app.defaults["tools_paint_plotting"] == 'progressive':
                self.temp_shapes.clear(update=True)

            # delete tools with empty geometry
            # look for keys in the tools_storage dict that have 'solid_geometry' values empty
            for uid in list(tools_storage.keys()):
                # if the solid_geometry (type=list) is empty
                if not tools_storage[uid]['solid_geometry']:
                    tools_storage.pop(uid, None)

            if not tools_storage:
                return 'fail'

            geo_obj.multitool = True

            if geo_obj.tools:
                # test if at least one tool has solid_geometry. If no tool has solid_geometry we raise an Exception
                has_solid_geo = 0
                for tooluid in geo_obj.tools:
                    if geo_obj.tools[tooluid]['solid_geometry']:
                        has_solid_geo += 1

                if has_solid_geo == 0:
                    app_obj.inform.emit(
                        '[ERROR] %s' %
                        _("There is no Painting Geometry in the file.\n"
                          "Usually it means that the tool diameter is too big for the painted geometry.\n"
                          "Change the painting parameters and try again.")
                    )
                    return "fail"
                geo_obj.solid_geometry = unary_union(final_solid_geometry)
            else:
                return 'fail'
            try:
                if isinstance(geo_obj.solid_geometry, list):
                    a, b, c, d = MultiPolygon(geo_obj.solid_geometry).bounds
                else:
                    a, b, c, d = geo_obj.solid_geometry.bounds

                geo_obj.options['xmin'] = a
                geo_obj.options['ymin'] = b
                geo_obj.options['xmax'] = c
                geo_obj.options['ymax'] = d
            except Exception as ee:
                log.debug("ToolPaint.paint_poly.job_init() bounds error --> %s" % str(ee))
                return

            # Experimental...
            # print("Indexing...", end=' ')
            # geo_obj.make_index()

        def job_thread(app_obj):
            try:
                if self.ui.rest_cb.get_value():
                    ret = app_obj.app_obj.new_object("geometry", name, job_rest_clear, plot=plot)
                else:
                    ret = app_obj.app_obj.new_object("geometry", name, job_normal_clear, plot=plot)
            except grace:
                proc.done()
                return
            except Exception as er:
                proc.done()
                app_obj.inform.emit('[ERROR] %s --> %s' % ('PaintTool.paint_geo()', str(er)))
                traceback.print_stack()
                return
            proc.done()

            if ret == 'fail':
                self.app.inform.emit('[ERROR] %s' % _("Failed."))
                return

            # focus on Properties Tab
            # self.app.ui.notebook.setCurrentWidget(self.app.ui.properties_tab)

            self.app.inform.emit('[success] %s' % _("Done."))

        # Promise object with the new name
        self.app.collection.promise(name)

        proc = self.app.proc_container.new(_("Painting ..."))

        if run_threaded:
            # Background
            self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})
        else:
            job_thread(app_obj=self.app)

    def paint_poly(self, obj, inside_pt=None, poly_list=None, tooldia=None, order=None, method=None, outname=None,
                   tools_storage=None, plot=True, run_threaded=True):
        """
        Paints a polygon selected by clicking on its interior or by having a point coordinates given

        Note:
            * The margin is taken directly from the form.

        :param run_threaded:
        :param plot:
        :param poly_list:
        :param obj:             painted object
        :param inside_pt:       [x, y]
        :param tooldia:         Diameter of the painting tool
        :param order:           if the tools are ordered and how
        :param outname:         Name of the resulting Geometry Object.
        :param method:          choice out of _("Seed"), 'normal', 'lines'
        :param tools_storage:   whether to use the current tools_storage self.paints_tools or a different one.
                                Usage of the different one is related to when this function is called
                                from a TcL command.
        :return: None
        """

        if obj.kind == 'gerber':
            # I don't do anything here, like buffering when the Gerber is loaded without buffering????!!!!
            if self.app.defaults["gerber_buffering"] == 'no':
                msg = '%s %s %s' % (_("Paint Tool."),
                                    _("Normal painting polygon task started."),
                                    _("Buffering geometry..."))
                self.app.inform.emit(msg)
            else:
                self.app.inform.emit('%s %s' % (_("Paint Tool."), _("Normal painting polygon task started.")))

            if self.app.defaults["tools_paint_plotting"] == 'progressive':
                if isinstance(obj.solid_geometry, list):
                    obj.solid_geometry = MultiPolygon(obj.solid_geometry).buffer(0)
                else:
                    obj.solid_geometry = obj.solid_geometry.buffer(0)
        else:
            self.app.inform.emit('%s %s' % (_("Paint Tool."), _("Normal painting polygon task started.")))

        if inside_pt and poly_list is None:
            polygon_list = self.find_polygon(point=inside_pt, geoset=obj.solid_geometry)
            if polygon_list:
                polygon_list = [polygon_list]
        elif (inside_pt is None and poly_list) or (inside_pt and poly_list):
            polygon_list = poly_list
        else:
            return

        # No polygon?
        if polygon_list is None:
            self.app.log.warning('No polygon found.')
            self.app.inform.emit('[WARNING] %s' % _('No polygon found.'))
            return "fail"

        self.paint_geo(obj, polygon_list, tooldia=tooldia, order=order, method=method, outname=outname,
                       tools_storage=tools_storage, plot=plot, run_threaded=run_threaded)

    def paint_poly_all(self, obj, tooldia=None, order=None, method=None, outname=None, tools_storage=None, plot=True,
                       run_threaded=True):
        """
        Paints all polygons in this object.

        :param obj:             painted object
        :param tooldia:         a tuple or single element made out of diameters of the tools to be used
        :param order:           if the tools are ordered and how
        :param outname:         name of the resulting object
        :param method:          choice out of _("Seed"), 'normal', 'lines'
        :param tools_storage:   whether to use the current tools_storage self.paints_tools or a different one.
                                Usage of the different one is related to when this function is called from
                                a TcL command.
        :param run_threaded:
        :param plot:
        :return:
        """

        # This is a recursive generator of individual Polygons.
        # Note: Double check correct implementation. Might exit
        #       early if it finds something that is not a Polygon?
        # def recurse(geo):
        #     try:
        #         for subg in geo:
        #             for subsubg in recurse(subg):
        #                 yield subsubg
        #     except TypeError:
        #         if isinstance(geo, Polygon):
        #             yield geo
        #
        #     raise StopIteration

        def recurse(geometry, reset=True):
            """
            Creates a list of non-iterable linear geometry objects.
            Results are placed in self.flat_geometry

            :param geometry: Shapely type or list or list of list of such.
            :param reset: Clears the contents of self.flat_geometry.
            """
            if self.app.abort_flag:
                # graceful abort requested by the user
                raise grace

            if geometry is None:
                return

            if reset:
                self.flat_geometry = []

            # ## If iterable, expand recursively.
            try:
                for geo in geometry:
                    if geo and not geo.is_empty and geo.is_valid:
                        recurse(geometry=geo, reset=False)

            # ## Not iterable, do the actual indexing and add.
            except TypeError:
                if isinstance(geometry, LinearRing):
                    g = Polygon(geometry)
                    self.flat_geometry.append(g)
                else:
                    self.flat_geometry.append(geometry)

            return self.flat_geometry

        if obj.kind == 'gerber':
            # I don't do anything here, like buffering when the Gerber is loaded without buffering????!!!!
            if self.app.defaults["gerber_buffering"] == 'no':
                msg = '%s %s %s' % (_("Paint Tool."), _("Paint all polygons task started."), _("Buffering geometry..."))
                self.app.inform.emit(msg)
            else:
                self.app.inform.emit('%s %s' % (_("Paint Tool."), _("Paint all polygons task started.")))

            if self.app.defaults["tools_paint_plotting"] == 'progressive':
                if isinstance(obj.solid_geometry, list):
                    obj.solid_geometry = MultiPolygon(obj.solid_geometry).buffer(0)
                else:
                    obj.solid_geometry = obj.solid_geometry.buffer(0)
        else:
            self.app.inform.emit('%s %s' % (_("Paint Tool."), _("Paint all polygons task started.")))

        painted_area = recurse(obj.solid_geometry)

        # No polygon?
        if not painted_area:
            self.app.log.warning('No polygon found.')
            self.app.inform.emit('[WARNING] %s' % _('No polygon found.'))
            return

        self.paint_geo(obj, painted_area, tooldia=tooldia, order=order, method=method, outname=outname,
                       tools_storage=tools_storage, plot=plot, run_threaded=run_threaded)

    def paint_poly_area(self, obj, sel_obj, tooldia=None, order=None, method=None, outname=None,
                        tools_storage=None, plot=True, run_threaded=True):
        """
        Paints all polygons in this object that are within the sel_obj object

        :param obj: painted object
        :param sel_obj: paint only what is inside this object bounds
        :param tooldia: a tuple or single element made out of diameters of the tools to be used
        :param order: if the tools are ordered and how
        :param outname: name of the resulting object
        :param method: choice out of _("Seed"), 'normal', 'lines'
        :param tools_storage: whether to use the current tools_storage self.paints_tools or a different one.
        Usage of the different one is related to when this function is called from a TcL command.
        :param run_threaded:
        :param plot:
        :return:
        """

        def recurse(geometry, reset=True):
            """
            Creates a list of non-iterable linear geometry objects.
            Results are placed in self.flat_geometry

            :param geometry: Shapely type or list or list of list of such.
            :param reset: Clears the contents of self.flat_geometry.
            """
            if self.app.abort_flag:
                # graceful abort requested by the user
                raise grace

            if geometry is None:
                return

            if reset:
                self.flat_geometry = []

            # ## If iterable, expand recursively.
            try:
                for geo in geometry:
                    if geo is not None:
                        recurse(geometry=geo, reset=False)

            # ## Not iterable, do the actual indexing and add.
            except TypeError:
                if isinstance(geometry, LinearRing):
                    g = Polygon(geometry)
                    self.flat_geometry.append(g)
                else:
                    self.flat_geometry.append(geometry)

            return self.flat_geometry

        # this is were heavy lifting is done and creating the geometry to be painted
        target_geo = MultiPolygon(obj.solid_geometry)
        if obj.kind == 'gerber':
            # I don't do anything here, like buffering when the Gerber is loaded without buffering????!!!!
            if self.app.defaults["gerber_buffering"] == 'no':
                msg = '%s %s %s' % (_("Paint Tool."),
                                    _("Painting area task started."),
                                    _("Buffering geometry..."))
                self.app.inform.emit(msg)
            else:
                self.app.inform.emit('%s %s' % (_("Paint Tool."), _("Painting area task started.")))

            if obj.kind == 'gerber':
                if self.app.defaults["tools_paint_plotting"] == 'progressive':
                    target_geo = target_geo.buffer(0)
        else:
            self.app.inform.emit('%s %s' % (_("Paint Tool."), _("Painting area task started.")))

        geo_to_paint = target_geo.intersection(sel_obj)
        painted_area = recurse(geo_to_paint)

        # No polygon?
        if not painted_area:
            self.app.log.warning('No polygon found.')
            self.app.inform.emit('[WARNING] %s' % _('No polygon found.'))
            return

        self.paint_geo(obj, painted_area, tooldia=tooldia, order=order, method=method, outname=outname,
                       tools_storage=tools_storage, plot=plot, run_threaded=run_threaded)

    def paint_poly_ref(self, obj, sel_obj, tooldia=None, order=None, method=None, outname=None,
                       tools_storage=None, plot=True, run_threaded=True):
        """
        Paints all polygons in this object that are within the sel_obj object

        :param obj: painted object
        :param sel_obj: paint only what is inside this object bounds
        :param tooldia: a tuple or single element made out of diameters of the tools to be used
        :param order: if the tools are ordered and how
        :param outname: name of the resulting object
        :param method: choice out of _("Seed"), 'normal', 'lines'
        :param tools_storage: whether to use the current tools_storage self.paints_tools or a different one.
        Usage of the different one is related to when this function is called from a TcL command.
        :param run_threaded:
        :param plot:
        :return:
        """
        geo = sel_obj.solid_geometry
        try:
            if isinstance(geo, MultiPolygon):
                env_obj = geo.convex_hull
            elif (isinstance(geo, MultiPolygon) and len(geo) == 1) or \
                    (isinstance(geo, list) and len(geo) == 1) and isinstance(geo[0], Polygon):
                env_obj = unary_union(self.bound_obj.solid_geometry)
            else:
                env_obj = unary_union(self.bound_obj.solid_geometry)
                env_obj = env_obj.convex_hull
            sel_rect = env_obj.buffer(distance=0.0000001, join_style=base.JOIN_STYLE.mitre)
        except Exception as e:
            log.debug("ToolPaint.paint_poly_ref() --> %s" % str(e))
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("No object available."))
            return

        self.paint_poly_area(obj=obj,
                             sel_obj=sel_rect,
                             tooldia=tooldia,
                             order=order,
                             method=method,
                             outname=outname,
                             tools_storage=tools_storage,
                             plot=plot,
                             run_threaded=run_threaded)

    def ui_connect(self):
        self.ui.tools_table.itemChanged.connect(self.on_tool_edit)

        # rows selected
        self.ui.tools_table.clicked.connect(self.on_row_selection_change)
        self.ui.tools_table.horizontalHeader().sectionClicked.connect(self.on_toggle_all_rows)

        # Table widgets
        for row in range(self.ui.tools_table.rowCount()):
            try:
                self.ui.tools_table.cellWidget(row, 2).currentIndexChanged.connect(self.on_tooltable_cellwidget_change)
            except AttributeError:
                pass

            try:
                self.ui.tools_table.cellWidget(row, 4).currentIndexChanged.connect(self.on_tooltable_cellwidget_change)
            except AttributeError:
                pass

        # Parameters FORM UI
        # first disconnect
        for opt in self.form_fields:
            current_widget = self.form_fields[opt]
            if isinstance(current_widget, FCCheckBox):
                try:
                    current_widget.stateChanged.disconnect()
                except (TypeError, ValueError):
                    pass
            if isinstance(current_widget, RadioSet):
                try:
                    current_widget.activated_custom.disconnect()
                except (TypeError, ValueError):
                    pass
            elif isinstance(current_widget, FCDoubleSpinner):
                try:
                    current_widget.returnPressed.disconnect()
                except (TypeError, ValueError):
                    pass

        # then reconnect
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

        self.ui.rest_cb.stateChanged.connect(self.ui.on_rest_machining_check)
        self.ui.order_radio.activated_custom[str].connect(self.on_order_changed)

    def ui_disconnect(self):
        try:
            # if connected, disconnect the signal from the slot on item_changed as it creates issues
            self.ui.tools_table.itemChanged.disconnect()
        except (TypeError, AttributeError):
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

        # Table widgets
        for row in range(self.ui.tools_table.rowCount()):
            for col in [2, 4]:
                try:
                    self.ui.tools_table.cellWidget(row, col).currentIndexChanged.disconnect()
                except (TypeError, AttributeError):
                    pass

        # Parameters FORM UI
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
                    current_widget.currentIndexChanged.connect(self.form_to_storage)
                except (TypeError, ValueError):
                    pass

        try:
            # if connected, disconnect the signal from the slot on item_changed as it creates issues
            self.ui.rest_cb.stateChanged.disconnect()
        except (TypeError, AttributeError):
            pass

        try:
            # if connected, disconnect the signal from the slot on item_changed as it creates issues
            self.ui.order_radio.activated_custom[str].disconnect()
        except (TypeError, AttributeError):
            pass

    @staticmethod
    def paint_bounds(geometry):
        def bounds_rec(o):
            if type(o) is list:
                minx = Inf
                miny = Inf
                maxx = -Inf
                maxy = -Inf

                for k in o:
                    try:
                        minx_, miny_, maxx_, maxy_ = bounds_rec(k)
                    except Exception as e:
                        log.debug("ToolPaint.bounds() --> %s" % str(e))
                        return

                    minx = min(minx, minx_)
                    miny = min(miny, miny_)
                    maxx = max(maxx, maxx_)
                    maxy = max(maxy, maxy_)
                return minx, miny, maxx, maxy
            else:
                # it's a Shapely object, return it's bounds
                return o.bounds

        return bounds_rec(geometry)

    def on_paint_tool_add_from_db_executed(self, tool):
        """
        Here add the tool from DB  in the selected geometry object
        :return:
        """
        tool_from_db = deepcopy(tool)

        if tool['data']['tool_target'] not in [0, 4]:   # [General, Paint]
            for idx in range(self.app.ui.plot_tab_area.count()):
                if self.app.ui.plot_tab_area.tabText(idx) == _("Tools Database"):
                    wdg = self.app.ui.plot_tab_area.widget(idx)
                    wdg.deleteLater()
                    self.app.ui.plot_tab_area.removeTab(idx)
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Selected tool can't be used here. Pick another."))
            return

        res = self.on_paint_tool_from_db_inserted(tool=tool_from_db)

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

    def on_paint_tool_from_db_inserted(self, tool):
        """
        Called from the Tools DB object through a App method when adding a tool from Tools Database
        :param tool: a dict with the tool data
        :return: None
        """

        self.ui_disconnect()
        self.units = self.app.defaults['units'].upper()

        tooldia = float(tool['tooldia'])

        # construct a list of all 'tooluid' in the self.tools
        tool_uid_list = []
        for tooluid_key in self.paint_tools:
            tool_uid_item = int(tooluid_key)
            tool_uid_list.append(tool_uid_item)

        # find maximum from the temp_uid, add 1 and this is the new 'tooluid'
        if not tool_uid_list:
            max_uid = 0
        else:
            max_uid = max(tool_uid_list)
        tooluid = max_uid + 1

        tooldia = self.app.dec_format(tooldia, self.decimals)

        tool_dias = []
        for k, v in self.paint_tools.items():
            for tool_v in v.keys():
                if tool_v == 'tooldia':
                    tool_dias.append(float('%.*f' % (self.decimals, (v[tool_v]))))

        if float('%.*f' % (self.decimals, tooldia)) in tool_dias:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled. Tool already in Tool Table."))
            self.ui_connect()
            return 'fail'

        self.paint_tools.update({
            tooluid: {
                'tooldia': float('%.*f' % (self.decimals, tooldia)),
                'offset': tool['offset'],
                'offset_value': tool['offset_value'],
                'type': tool['type'],
                'tool_type': tool['tool_type'],
                'data': deepcopy(tool['data']),
                'solid_geometry': []
            }
        })
        self.paint_tools[tooluid]['data']['name'] = '_paint'

        self.app.inform.emit('[success] %s' % _("New tool added to Tool Table."))

        self.ui_connect()
        self.build_ui()

        # select the tool just added
        for row in range(self.ui.tools_table.rowCount()):
            if int(self.ui.tools_table.item(row, 3).text()) == tooluid:
                self.ui.tools_table.selectRow(row)
                break

        return tooluid

    def on_paint_tool_add_from_db_clicked(self):
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
        ret_val = self.app.on_tools_database(source='paint')
        if ret_val == 'fail':
            return
        self.app.tools_db_tab.ok_to_add = True
        self.app.tools_db_tab.ui.buttons_frame.hide()
        self.app.tools_db_tab.ui.add_tool_from_db.show()
        self.app.tools_db_tab.ui.cancel_tool_from_db.show()

    def reset_fields(self):
        self.ui.obj_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))


class PaintUI:

    toolName = _("Paint Tool")

    def __init__(self, layout, app):
        self.app = app
        self.decimals = self.app.decimals
        self.layout = layout

        # ## Title
        title_label = FCLabel("%s" % self.toolName)
        title_label.setStyleSheet("""
                                QLabel
                                {
                                    font-size: 16px;
                                    font-weight: bold;
                                }
                                """)
        self.layout.addWidget(title_label)

        self.tools_frame = QtWidgets.QFrame()
        self.tools_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.tools_frame)
        self.tools_box = QtWidgets.QVBoxLayout()
        self.tools_box.setContentsMargins(0, 0, 0, 0)
        self.tools_frame.setLayout(self.tools_box)

        # ## Form Layout
        grid0 = QtWidgets.QGridLayout()
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        self.tools_box.addLayout(grid0)

        # ################################################
        # ##### Type of object to be painted #############
        # ################################################

        self.type_obj_combo_label = FCLabel('%s:' % _("Obj Type"))
        self.type_obj_combo_label.setToolTip(
            _("Specify the type of object to be painted.\n"
              "It can be of type: Gerber or Geometry.\n"
              "What is selected here will dictate the kind\n"
              "of objects that will populate the 'Object' combobox.")
        )
        self.type_obj_combo_label.setMinimumWidth(60)

        self.type_obj_radio = RadioSet([{'label': "Geometry", 'value': 'geometry'},
                                        {'label': "Gerber", 'value': 'gerber'}])

        grid0.addWidget(self.type_obj_combo_label, 1, 0)
        grid0.addWidget(self.type_obj_radio, 1, 1)

        # ################################################
        # ##### The object to be painted #################
        # ################################################
        self.obj_combo = FCComboBox()
        self.obj_combo.setModel(self.app.collection)
        self.obj_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.obj_combo.is_last = True

        self.object_label = FCLabel('%s:' % _("Object"))
        self.object_label.setToolTip(_("Object to be painted."))

        grid0.addWidget(self.object_label, 2, 0)
        grid0.addWidget(self.obj_combo, 2, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 5, 0, 1, 2)

        # ### Tools ## ##
        self.tools_table_label = FCLabel('<b>%s</b>' % _('Tools Table'))
        self.tools_table_label.setToolTip(
            _("Tools pool from which the algorithm\n"
              "will pick the ones used for painting.")
        )

        self.tools_table = FCTable(drag_drop=True)
        # self.tools_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        grid0.addWidget(self.tools_table_label, 6, 0, 1, 2)
        grid0.addWidget(self.tools_table, 7, 0, 1, 2)

        self.tools_table.setColumnCount(4)
        self.tools_table.setHorizontalHeaderLabels(['#', _('Diameter'), _('TT'), ''])
        self.tools_table.setColumnHidden(3, True)
        # self.tools_table.setSortingEnabled(False)
        # self.tools_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        self.tools_table.horizontalHeaderItem(0).setToolTip(
            _("This is the Tool Number.\n"
              "Painting will start with the tool with the biggest diameter,\n"
              "continuing until there are no more tools.\n"
              "Only tools that create painting geometry will still be present\n"
              "in the resulting geometry. This is because with some tools\n"
              "this function will not be able to create painting geometry.")
        )
        self.tools_table.horizontalHeaderItem(1).setToolTip(
            _("Tool Diameter. Its value\n"
              "is the cut width into the material."))

        self.tools_table.horizontalHeaderItem(2).setToolTip(
            _("The Tool Type (TT) can be:\n"
              "- Circular -> it is informative only. Being circular,\n"
              "the cut width in material is exactly the tool diameter.\n"
              "- Ball -> informative only and make reference to the Ball type endmill.\n"
              "- V-Shape -> it will disable Z-Cut parameter in the resulting geometry UI form\n"
              "and enable two additional UI form fields in the resulting geometry: V-Tip Dia and\n"
              "V-Tip Angle. Adjusting those two values will adjust the Z-Cut parameter such\n"
              "as the cut width into material will be equal with the value in the Tool Diameter\n"
              "column of this table.\n"
              "Choosing the 'V-Shape' Tool Type automatically will select the Operation Type\n"
              "in the resulting geometry as Isolation."))

        self.order_label = FCLabel('<b>%s:</b>' % _('Tool order'))
        self.order_label.setToolTip(_("This set the way that the tools in the tools table are used.\n"
                                      "'No' --> means that the used order is the one in the tool table\n"
                                      "'Forward' --> means that the tools will be ordered from small to big\n"
                                      "'Reverse' --> means that the tools will ordered from big to small\n\n"
                                      "WARNING: using rest machining will automatically set the order\n"
                                      "in reverse and disable this control."))

        self.order_radio = RadioSet([{'label': _('No'), 'value': 'no'},
                                     {'label': _('Forward'), 'value': 'fwd'},
                                     {'label': _('Reverse'), 'value': 'rev'}])
        self.order_radio.setToolTip(_("This set the way that the tools in the tools table are used.\n"
                                      "'No' --> means that the used order is the one in the tool table\n"
                                      "'Forward' --> means that the tools will be ordered from small to big\n"
                                      "'Reverse' --> means that the tools will ordered from big to small\n\n"
                                      "WARNING: using rest machining will automatically set the order\n"
                                      "in reverse and disable this control."))

        grid0.addWidget(self.order_label, 9, 0)
        grid0.addWidget(self.order_radio, 9, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 10, 0, 1, 2)

        # ##############################################################################
        # ###################### ADD A NEW TOOL ########################################
        # ##############################################################################
        
        self.grid3 = QtWidgets.QGridLayout()
        self.grid3.setColumnStretch(0, 0)
        self.grid3.setColumnStretch(1, 1)
        self.tools_box.addLayout(self.grid3)
        
        self.tool_sel_label = FCLabel('<b>%s</b>' % _('Add from DB'))
        self.grid3.addWidget(self.tool_sel_label, 0, 0, 1, 2)

        # ### Tool Diameter ####
        self.new_tooldia_lbl = FCLabel('%s:' % _('Tool Dia'))
        self.new_tooldia_lbl.setToolTip(
            _("Diameter for the new tool to add in the Tool Table.\n"
              "If the tool is V-shape type then this value is automatically\n"
              "calculated from the other parameters.")
        )
        self.new_tooldia_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.new_tooldia_entry.set_precision(self.decimals)
        self.new_tooldia_entry.set_range(0.000, 10000.0000)
        self.new_tooldia_entry.setObjectName('p_tool_dia')

        self.grid3.addWidget(self.new_tooldia_lbl, 2, 0)
        self.grid3.addWidget(self.new_tooldia_entry, 2, 1)

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

        grid4 = QtWidgets.QGridLayout()
        grid4.setColumnStretch(0, 0)
        grid4.setColumnStretch(1, 1)
        self.tools_box.addLayout(grid4)

        # Overlap
        ovlabel = FCLabel('%s:' % _('Overlap'))
        ovlabel.setToolTip(
            _("How much (percentage) of the tool width to overlap each tool pass.\n"
              "Adjust the value starting with lower values\n"
              "and increasing it if areas that should be processed are still \n"
              "not processed.\n"
              "Lower values = faster processing, faster execution on CNC.\n"
              "Higher values = slow processing and slow execution on CNC\n"
              "due of too many paths.")
        )
        self.paintoverlap_entry = FCDoubleSpinner(callback=self.confirmation_message, suffix='%')
        self.paintoverlap_entry.set_precision(3)
        self.paintoverlap_entry.setWrapping(True)
        self.paintoverlap_entry.setRange(0.0000, 99.9999)
        self.paintoverlap_entry.setSingleStep(0.1)
        self.paintoverlap_entry.setObjectName('p_overlap')

        grid4.addWidget(ovlabel, 1, 0)
        grid4.addWidget(self.paintoverlap_entry, 1, 1)

        # Offset
        self.offset_label = FCLabel('%s:' % _('Offset'))
        self.offset_label.setToolTip(
            _("Distance by which to avoid\n"
              "the edges of the polygon to\n"
              "be painted.")
        )
        self.offset_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.offset_entry.set_precision(self.decimals)
        self.offset_entry.set_range(-10000.0000, 10000.0000)
        self.offset_entry.setObjectName('p_offset')

        grid4.addWidget(self.offset_label, 2, 0)
        grid4.addWidget(self.offset_entry, 2, 1)

        # Method
        methodlabel = FCLabel('%s:' % _('Method'))
        methodlabel.setToolTip(
            _("Algorithm for painting:\n"
              "- Standard: Fixed step inwards.\n"
              "- Seed-based: Outwards from seed.\n"
              "- Line-based: Parallel lines.\n"
              "- Laser-lines: Active only for Gerber objects.\n"
              "Will create lines that follow the traces.\n"
              "- Combo: In case of failure a new method will be picked from the above\n"
              "in the order specified.")
        )

        self.paintmethod_combo = FCComboBox2()
        self.paintmethod_combo.addItems(
            [_("Standard"), _("Seed"), _("Lines"), _("Laser_lines"), _("Combo")]
        )
        idx = self.paintmethod_combo.findText(_("Laser_lines"))
        self.paintmethod_combo.model().item(idx).setEnabled(False)

        self.paintmethod_combo.setObjectName('p_method')

        grid4.addWidget(methodlabel, 7, 0)
        grid4.addWidget(self.paintmethod_combo, 7, 1)

        # Connect lines
        self.pathconnect_cb = FCCheckBox('%s' % _("Connect"))
        self.pathconnect_cb.setObjectName('p_connect')
        self.pathconnect_cb.setToolTip(
            _("Draw lines between resulting\n"
              "segments to minimize tool lifts.")
        )

        self.paintcontour_cb = FCCheckBox('%s' % _("Contour"))
        self.paintcontour_cb.setObjectName('p_contour')
        self.paintcontour_cb.setToolTip(
            _("Cut around the perimeter of the polygon\n"
              "to trim rough edges.")
        )

        grid4.addWidget(self.pathconnect_cb, 10, 0)
        grid4.addWidget(self.paintcontour_cb, 10, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid4.addWidget(separator_line, 11, 0, 1, 2)

        self.apply_param_to_all = FCButton(_("Apply parameters to all tools"))
        self.apply_param_to_all.setIcon(QtGui.QIcon(self.app.resource_location + '/param_all32.png'))
        self.apply_param_to_all.setToolTip(
            _("The parameters in the current form will be applied\n"
              "on all the tools from the Tool Table.")
        )
        grid4.addWidget(self.apply_param_to_all, 12, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid4.addWidget(separator_line, 13, 0, 1, 2)

        # General Parameters
        self.gen_param_label = FCLabel('<b>%s</b>' % _("Common Parameters"))
        self.gen_param_label.setToolTip(
            _("Parameters that are common for all tools.")
        )
        grid4.addWidget(self.gen_param_label, 15, 0, 1, 2)

        self.rest_cb = FCCheckBox('%s' % _("Rest"))
        self.rest_cb.setObjectName('p_rest_machining')
        self.rest_cb.setToolTip(
            _("If checked, use 'rest machining'.\n"
              "Basically it will process copper outside PCB features,\n"
              "using the biggest tool and continue with the next tools,\n"
              "from bigger to smaller, to process the copper features that\n"
              "could not be processed by previous tool, until there is\n"
              "nothing left to process or there are no more tools.\n\n"
              "If not checked, use the standard algorithm.")
        )
        grid4.addWidget(self.rest_cb, 16, 0, 1, 2)

        # Rest Offset
        self.rest_offset_label = FCLabel('%s:' % _('Offset'))
        self.rest_offset_label.setToolTip(
            _("Distance by which to avoid\n"
              "the edges of the polygon to\n"
              "be painted.")
        )
        self.rest_offset_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.rest_offset_entry.set_precision(self.decimals)
        self.rest_offset_entry.set_range(-10000.0000, 10000.0000)

        grid4.addWidget(self.rest_offset_label, 17, 0)
        grid4.addWidget(self.rest_offset_entry, 17, 1)

        # Polygon selection
        selectlabel = FCLabel('%s:' % _('Selection'))
        selectlabel.setToolTip(
            _("Selection of area to be processed.\n"
              "- 'Polygon Selection' - left mouse click to add/remove polygons to be processed.\n"
              "- 'Area Selection' - left mouse click to start selection of the area to be processed.\n"
              "Keeping a modifier key pressed (CTRL or SHIFT) will allow to add multiple areas.\n"
              "- 'All Polygons' - the process will start after click.\n"
              "- 'Reference Object' - will process the area specified by another object.")
        )

        self.selectmethod_combo = FCComboBox2()
        self.selectmethod_combo.addItems(
            [_("All"), _("Polygon Selection"), _("Area Selection"), _("Reference Object")]
        )
        self.selectmethod_combo.setObjectName('p_selection')

        grid4.addWidget(selectlabel, 18, 0)
        grid4.addWidget(self.selectmethod_combo, 18, 1)

        # Type of Reference Object
        self.reference_type_label = FCLabel('%s:' % _("Type"))
        self.reference_type_label.setToolTip(
            _("The type of FlatCAM object to be used as paint reference.\n"
              "It can be Gerber, Excellon or Geometry.")
        )
        self.reference_type_combo = FCComboBox2()
        self.reference_type_combo.addItems([_("Gerber"), _("Excellon"), _("Geometry")])

        grid4.addWidget(self.reference_type_label, 20, 0)
        grid4.addWidget(self.reference_type_combo, 20, 1)

        # Reference Object
        self.reference_combo = FCComboBox()
        self.reference_combo.setModel(self.app.collection)
        self.reference_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.reference_combo.is_last = True

        grid4.addWidget(self.reference_combo, 22, 0, 1, 2)

        self.reference_combo.hide()
        self.reference_type_combo.hide()
        self.reference_type_label.hide()

        # Area Selection shape
        self.area_shape_label = FCLabel('%s:' % _("Shape"))
        self.area_shape_label.setToolTip(
            _("The kind of selection shape used for area selection.")
        )

        self.area_shape_radio = RadioSet([{'label': _("Square"), 'value': 'square'},
                                          {'label': _("Polygon"), 'value': 'polygon'}])

        grid4.addWidget(self.area_shape_label, 24, 0)
        grid4.addWidget(self.area_shape_radio, 24, 1)

        self.area_shape_label.hide()
        self.area_shape_radio.hide()

        # GO Button
        self.generate_paint_button = FCButton(_('Generate Geometry'))
        self.generate_paint_button.setIcon(QtGui.QIcon(self.app.resource_location + '/geometry32.png'))
        self.generate_paint_button.setToolTip(
            _("Create a Geometry Object which paints the polygons.")
        )
        self.generate_paint_button.setStyleSheet("""
                                                 QPushButton
                                                 {
                                                     font-weight: bold;
                                                 }
                                                 """)
        self.tools_box.addWidget(self.generate_paint_button)

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

        # #################################### FINSIHED GUI ###########################
        # #############################################################################
    
    def on_rest_machining_check(self, state):
        if state:
            self.order_radio.set_value('rev')
            self.order_label.setDisabled(True)
            self.order_radio.setDisabled(True)

            self.offset_label.hide()
            self.offset_entry.hide()
            self.rest_offset_label.show()
            self.rest_offset_entry.show()
        else:
            self.order_label.setDisabled(False)
            self.order_radio.setDisabled(False)

            self.offset_label.show()
            self.offset_entry.show()
            self.rest_offset_label.hide()
            self.rest_offset_entry.hide()
    
    def on_selection(self):
        sel_combo = self.selectmethod_combo.get_value()

        if sel_combo == 3:  # _("Reference Object")
            self.reference_combo.show()
            self.reference_type_combo.show()
            self.reference_type_label.show()
        else:
            self.reference_combo.hide()
            self.reference_type_combo.hide()
            self.reference_type_label.hide()

        if sel_combo == 1:  # _("Polygon Selection")
            # disable rest-machining for single polygon painting
            # self.ui.rest_cb.set_value(False)
            # self.ui.rest_cb.setDisabled(True)
            pass

        if sel_combo == 2:  # _("Area Selection") index 2 in combobox (FCComboBox2() returns index instead of text)
            # disable rest-machining for area painting
            # self.ui.rest_cb.set_value(False)
            # self.ui.rest_cb.setDisabled(True)

            self.area_shape_label.show()
            self.area_shape_radio.show()
        else:   # All = index 0 in combobox
            self.new_tooldia_entry.setDisabled(False)
            self.add_newtool_button.setDisabled(False)
            self.deltool_btn.setDisabled(False)
            self.tools_table.setContextMenuPolicy(Qt.ActionsContextMenu)

            self.area_shape_label.hide()
            self.area_shape_radio.hide()

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
