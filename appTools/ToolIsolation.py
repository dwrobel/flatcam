# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File by:  Marius Adrian Stanciu (c)                      #
# Date:     5/25/2020                                      #
# License:  MIT Licence                                    #
# ##########################################################

from PyQt5 import QtWidgets, QtCore, QtGui

from appTool import AppTool
from appGUI.GUIElements import FCCheckBox, FCDoubleSpinner, RadioSet, FCTable, FCButton, \
    FCComboBox, OptionalInputSection, FCSpinner, FCLabel, FCInputDialogSpinnerButton, FCComboBox2
from appParsers.ParseGerber import Gerber
from camlib import grace

from copy import deepcopy

import numpy as np
import simplejson as json
import sys

from shapely.ops import unary_union, nearest_points
from shapely.geometry import MultiPolygon, Polygon, MultiLineString, LineString, LinearRing, Point

from matplotlib.backend_bases import KeyEvent as mpl_key_event

import logging
import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class ToolIsolation(AppTool, Gerber):

    optimal_found_sig = QtCore.pyqtSignal(float)

    def __init__(self, app):
        self.app = app
        self.decimals = self.app.decimals

        AppTool.__init__(self, app)
        Gerber.__init__(self, steps_per_circle=self.app.defaults["gerber_circle_steps"])

        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = IsoUI(layout=self.layout, app=self.app)
        self.toolName = self.ui.toolName

        # #############################################################################
        # ###################### Setup CONTEXT MENU ###################################
        # #############################################################################
        self.ui.tools_table.setupContextMenu()
        self.ui.tools_table.addContextMenu(
            _("Search and Add"),
            self.on_add_tool_by_key,
            icon=QtGui.QIcon(self.app.resource_location + "/plus16.png")
        )
        self.ui.tools_table.addContextMenu(
            _("Pick from DB"),
            self.on_add_tool_by_key,
            icon=QtGui.QIcon(self.app.resource_location + "/search_db32.png")
        )
        self.ui.tools_table.addContextMenu(
            _("Delete"),
            lambda: self.on_tool_delete(rows_to_delete=None, all_tools=None),
            icon=QtGui.QIcon(self.app.resource_location + "/trash16.png")
        )

        # #############################################################################
        # ########################## VARIABLES ########################################
        # #############################################################################
        self.units = ''
        self.iso_tools = {}
        self.tooluid = 0

        # store here the default data for Geometry Data
        self.default_data = {}

        self.obj_name = ""
        self.grb_obj = None

        self.sel_rect = []

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

        # store geometry from Polygon selection
        self.poly_dict = {}

        self.grid_status_memory = self.app.ui.grid_snap_btn.isChecked()

        # store here the state of the combine_cb GUI element
        # used when the rest machining is toggled
        self.old_combine_state = self.app.defaults["tools_iso_combine_passes"]

        # store here solid_geometry when there are tool with isolation job
        self.solid_geometry = []

        self.tool_type_item_options = []

        self.grb_circle_steps = int(self.app.defaults["gerber_circle_steps"])

        self.tooldia = None
        # store here the tool diameter that is guaranteed to isolate the object
        self.safe_tooldia = None

        # multiprocessing
        self.pool = self.app.pool
        self.results = []

        # disconnect flags
        self.area_sel_disconnect_flag = False
        self.poly_sel_disconnect_flag = False

        self.form_fields = {
            "tools_iso_passes":         self.ui.passes_entry,
            "tools_iso_overlap":        self.ui.iso_overlap_entry,
            "tools_iso_milling_type":   self.ui.milling_type_radio,
            "tools_iso_combine":        self.ui.combine_passes_cb,
            "tools_iso_follow":         self.ui.follow_cb,
            "tools_iso_isotype":        self.ui.iso_type_radio
        }

        self.name2option = {
            "i_passes":         "tools_iso_passes",
            "i_overlap":        "tools_iso_overlap",
            "i_milling_type":   "tools_iso_milling_type",
            "i_combine":        "tools_iso_combine",
            "i_follow":         "tools_iso_follow",
            "i_iso_type":       "tools_iso_isotype"
        }

        self.connect_signals_at_init()

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Alt+I', **kwargs)

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolIsolation()")
        log.debug("ToolIsolation().run() was launched ...")

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
        self.grb_obj = None
        self.obj_name = ''

        self.build_ui()

        # all the tools are selected by default
        self.ui.tools_table.selectAll()

        self.app.ui.notebook.setTabText(2, _("Isolation Tool"))

    def connect_signals_at_init(self):
        # #############################################################################
        # ############################ SIGNALS ########################################
        # #############################################################################
        self.ui.deltool_btn.clicked.connect(self.on_tool_delete)

        self.ui.find_optimal_button.clicked.connect(self.on_find_optimal_tooldia)
        # Custom Signal
        self.optimal_found_sig.connect(lambda val: self.ui.new_tooldia_entry.set_value(float(val)))

        self.ui.reference_combo_type.currentIndexChanged.connect(self.on_reference_combo_changed)
        self.ui.select_combo.currentIndexChanged.connect(self.on_toggle_reference)

        self.ui.type_excobj_radio.activated_custom.connect(self.on_type_excobj_index_changed)
        self.ui.apply_param_to_all.clicked.connect(self.on_apply_param_to_all_clicked)

        # adding Tools
        self.ui.search_and_add_btn.clicked.connect(lambda: self.on_tool_add())
        self.ui.addtool_from_db_btn.clicked.connect(self.on_tool_add_from_db_clicked)

        self.ui.generate_iso_button.clicked.connect(self.on_iso_button_click)
        self.ui.reset_button.clicked.connect(self.set_tool_ui)

        # Cleanup on Graceful exit (CTRL+ALT+X combo key)
        self.app.cleanup.connect(self.set_tool_ui)

    def on_type_excobj_index_changed(self, val):
        obj_type = 0 if val == 'gerber' else 2
        self.ui.exc_obj_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.ui.exc_obj_combo.setCurrentIndex(0)
        self.ui.exc_obj_combo.obj_type = {
            "gerber": "Gerber", "geometry": "Geometry"
        }[self.ui.type_excobj_radio.get_value()]

    def set_tool_ui(self):
        self.units = self.app.defaults['units'].upper()

        # reset the value to prepare for another isolation
        self.safe_tooldia = None

        # try to select in the Gerber combobox the active object
        try:
            selected_obj = self.app.collection.get_active()
            if selected_obj.kind == 'gerber':
                current_name = selected_obj.options['name']
                self.ui.object_combo.set_value(current_name)
        except Exception:
            pass

        app_mode = self.app.defaults["global_app_level"]

        # Show/Hide Advanced Options
        if app_mode == 'b':
            self.ui.level.setText('<span style="color:green;"><b>%s</b></span>' % _('Basic'))

            self.ui.milling_type_label.hide()
            self.ui.milling_type_radio.hide()

            self.ui.iso_type_label.hide()
            self.ui.iso_type_radio.set_value('full')
            self.ui.iso_type_radio.hide()

            self.ui.follow_cb.set_value(False)
            self.ui.follow_cb.hide()
            self.ui.follow_label.hide()

            self.ui.rest_cb.set_value(False)
            self.ui.rest_cb.hide()
            self.ui.forced_rest_iso_cb.hide()

            self.ui.except_cb.set_value(False)
            self.ui.except_cb.hide()

            self.ui.type_excobj_radio.hide()
            self.ui.exc_obj_combo.hide()

            self.ui.select_combo.setCurrentIndex(0)
            self.ui.select_combo.hide()
            self.ui.select_label.hide()
        else:
            self.ui.level.setText('<span style="color:red;"><b>%s</b></span>' % _('Advanced'))

            self.ui.milling_type_label.show()
            self.ui.milling_type_radio.show()

            self.ui.iso_type_label.show()
            self.ui.iso_type_radio.set_value(self.app.defaults["tools_iso_isotype"])
            self.ui.iso_type_radio.show()

            self.ui.follow_cb.set_value(self.app.defaults["tools_iso_follow"])
            self.ui.follow_cb.show()
            self.ui.follow_label.show()

            self.ui.rest_cb.set_value(self.app.defaults["tools_iso_rest"])
            self.ui.rest_cb.show()
            self.ui.forced_rest_iso_cb.show()

            self.ui.except_cb.set_value(self.app.defaults["tools_iso_isoexcept"])
            self.ui.except_cb.show()

            self.ui.select_combo.set_value(self.app.defaults["tools_iso_selection"])
            self.ui.select_combo.show()
            self.ui.select_label.show()

        if self.app.defaults["gerber_buffering"] == 'no':
            self.ui.create_buffer_button.show()
            try:
                self.ui.create_buffer_button.clicked.disconnect(self.on_generate_buffer)
            except TypeError:
                pass
            self.ui.create_buffer_button.clicked.connect(self.on_generate_buffer)
        else:
            self.ui.create_buffer_button.hide()

        self.ui.tools_frame.show()

        self.ui.type_excobj_radio.set_value('gerber')

        # run those once so the obj_type attribute is updated for the FCComboboxes
        # so the last loaded object is displayed
        self.on_type_excobj_index_changed(val="gerber")
        self.on_reference_combo_changed()

        self.ui.order_radio.set_value(self.app.defaults["tools_iso_order"])
        self.ui.passes_entry.set_value(self.app.defaults["tools_iso_passes"])
        self.ui.iso_overlap_entry.set_value(self.app.defaults["tools_iso_overlap"])
        self.ui.milling_type_radio.set_value(self.app.defaults["tools_iso_milling_type"])
        self.ui.combine_passes_cb.set_value(self.app.defaults["tools_iso_combine_passes"])
        self.ui.valid_cb.set_value(self.app.defaults["tools_iso_check_valid"])
        self.ui.area_shape_radio.set_value(self.app.defaults["tools_iso_area_shape"])
        self.ui.poly_int_cb.set_value(self.app.defaults["tools_iso_poly_ints"])
        self.ui.forced_rest_iso_cb.set_value(self.app.defaults["tools_iso_force"])

        self.ui.new_tooldia_entry.set_value(self.app.defaults["tools_iso_newdia"])

        loaded_obj = self.app.collection.get_by_name(self.ui.object_combo.get_value())
        if loaded_obj:
            outname = loaded_obj.options['name']
        else:
            outname = ''

        # init the working variables
        self.default_data.clear()
        self.default_data = {
            "name":                     outname + '_iso',
            "plot":                     self.app.defaults["geometry_plot"],
            "cutz":                     float(self.app.defaults["tools_iso_tool_cutz"]),
            "vtipdia":                  float(self.app.defaults["tools_iso_tool_vtipdia"]),
            "vtipangle":                float(self.app.defaults["tools_iso_tool_vtipangle"]),
            "travelz":                  self.app.defaults["geometry_travelz"],
            "feedrate":                 self.app.defaults["geometry_feedrate"],
            "feedrate_z":               self.app.defaults["geometry_feedrate_z"],
            "feedrate_rapid":           self.app.defaults["geometry_feedrate_rapid"],

            "multidepth":               self.app.defaults["geometry_multidepth"],
            "ppname_g":                 self.app.defaults["geometry_ppname_g"],
            "depthperpass":             self.app.defaults["geometry_depthperpass"],
            "extracut":                 self.app.defaults["geometry_extracut"],
            "extracut_length":          self.app.defaults["geometry_extracut_length"],
            "toolchange":               self.app.defaults["geometry_toolchange"],
            "toolchangez":              self.app.defaults["geometry_toolchangez"],
            "endz":                     self.app.defaults["geometry_endz"],
            "endxy":                    self.app.defaults["geometry_endxy"],

            "dwell":                    self.app.defaults["geometry_dwell"],
            "dwelltime":                self.app.defaults["geometry_dwelltime"],
            "spindlespeed":             self.app.defaults["geometry_spindlespeed"],
            "spindledir":               self.app.defaults["geometry_spindledir"],

            "optimization_type":        self.app.defaults["geometry_optimization_type"],
            "search_time":              self.app.defaults["geometry_search_time"],
            "toolchangexy":             self.app.defaults["geometry_toolchangexy"],
            "startz":                   self.app.defaults["geometry_startz"],

            "area_exclusion":           self.app.defaults["geometry_area_exclusion"],
            "area_shape":               self.app.defaults["geometry_area_shape"],
            "area_strategy":            self.app.defaults["geometry_area_strategy"],
            "area_overz":               float(self.app.defaults["geometry_area_overz"]),

            "tools_iso_passes":         self.app.defaults["tools_iso_passes"],
            "tools_iso_overlap":        self.app.defaults["tools_iso_overlap"],
            "tools_iso_milling_type":   self.app.defaults["tools_iso_milling_type"],
            "tools_iso_follow":         self.app.defaults["tools_iso_follow"],
            "tools_iso_isotype":        self.app.defaults["tools_iso_isotype"],

            "tools_iso_rest":           self.app.defaults["tools_iso_rest"],
            "tools_iso_combine_passes": self.app.defaults["tools_iso_combine_passes"],
            "tools_iso_isoexcept":      self.app.defaults["tools_iso_isoexcept"],
            "tools_iso_selection":      self.app.defaults["tools_iso_selection"],
            "tools_iso_poly_ints":      self.app.defaults["tools_iso_poly_ints"],
            "tools_iso_force":          self.app.defaults["tools_iso_force"],
            "tools_iso_area_shape":     self.app.defaults["tools_iso_area_shape"]
        }

        try:
            dias = [float(self.app.defaults["tools_iso_tooldia"])]
        except (ValueError, TypeError):
            if isinstance(self.app.defaults["tools_iso_tooldia"], str):
                dias = [float(eval(dia)) for dia in self.app.defaults["tools_iso_tooldia"].split(",") if dia != '']
            else:
                dias = self.app.defaults["tools_iso_tooldia"]

        if not dias:
            log.error("At least one tool diameter needed. Verify in Edit -> Preferences -> TOOLS -> Isolation Tools.")
            return

        self.tooluid = 0

        self.iso_tools.clear()
        for tool_dia in dias:
            self.on_tool_add(custom_dia=tool_dia)

        self.obj_name = ""
        self.grb_obj = None

        self.first_click = False
        self.cursor_pos = None
        self.mouse_is_dragging = False

        prog_plot = True if self.app.defaults["tools_iso_plotting"] == 'progressive' else False
        if prog_plot:
            self.temp_shapes.clear(update=True)

        self.sel_rect = []

        self.tool_type_item_options = ["C1", "C2", "C3", "C4", "B", "V"]

        self.on_rest_machining_check(state=self.app.defaults["tools_iso_rest"])

        self.ui.tools_table.drag_drop_sig.connect(self.rebuild_ui)

    def rebuild_ui(self):
        # read the table tools uid
        currenuid_list = []
        for row in range(self.ui.tools_table.rowCount()):
            uid = int(self.ui.tools_table.item(row, 3).text())
            currenuid_list.append(uid)

        new_tools = {}
        new_uid = 1

        for currenuid in currenuid_list:
            new_tools[new_uid] = deepcopy(self.iso_tools[currenuid])
            new_uid += 1

        self.iso_tools = new_tools

        # the tools table changed therefore we need to rebuild it
        QtCore.QTimer.singleShot(20, self.build_ui)

    def build_ui(self):
        self.ui_disconnect()

        # updated units
        self.units = self.app.defaults['units'].upper()

        sorted_tools = []
        for k, v in self.iso_tools.items():
            sorted_tools.append(self.app.dec_format(float(v['tooldia']), self.decimals))

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
            for tooluid_key, tooluid_value in self.iso_tools.items():
                truncated_dia = self.app.dec_format(tooluid_value['tooldia'], self.decimals)
                if truncated_dia == tool_sorted:
                    tool_id += 1

                    # Tool name/id
                    id_ = QtWidgets.QTableWidgetItem('%d' % int(tool_id))
                    id_.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                    row_no = tool_id - 1
                    self.ui.tools_table.setItem(row_no, 0, id_)

                    # Diameter
                    dia = QtWidgets.QTableWidgetItem(str(truncated_dia))
                    dia.setFlags(QtCore.Qt.ItemIsEnabled)
                    self.ui.tools_table.setItem(row_no, 1, dia)

                    # Tool Type
                    tool_type_item = FCComboBox()
                    tool_type_item.addItems(self.tool_type_item_options)
                    idx = tool_type_item.findText(tooluid_value['tool_type'])
                    tool_type_item.setCurrentIndex(idx)
                    self.ui.tools_table.setCellWidget(row_no, 2, tool_type_item)

                    # Tool unique ID
                    # REMEMBER: THIS COLUMN IS HIDDEN
                    tool_uid_item = QtWidgets.QTableWidgetItem(str(int(tooluid_key)))
                    self.ui.tools_table.setItem(row_no, 3, tool_uid_item)

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

    def ui_connect(self):
        self.ui.tools_table.itemChanged.connect(self.on_tool_edit)

        # rows selected
        self.ui.tools_table.clicked.connect(self.on_row_selection_change)
        self.ui.tools_table.horizontalHeader().sectionClicked.connect(self.on_toggle_all_rows)

        # tool table widgets
        for row in range(self.ui.tools_table.rowCount()):
            try:
                self.ui.tools_table.cellWidget(row, 2).currentIndexChanged.connect(self.on_tooltable_cellwidget_change)
            except AttributeError:
                pass

        # Tool Parameters
        for opt in self.form_fields:
            current_widget = self.form_fields[opt]
            if isinstance(current_widget, FCCheckBox):
                current_widget.stateChanged.connect(self.form_to_storage)
            if isinstance(current_widget, RadioSet):
                current_widget.activated_custom.connect(self.form_to_storage)
            elif isinstance(current_widget, FCDoubleSpinner) or isinstance(current_widget, FCSpinner):
                current_widget.returnPressed.connect(self.form_to_storage)
            elif isinstance(current_widget, FCComboBox):
                current_widget.currentIndexChanged.connect(self.form_to_storage)

        self.ui.rest_cb.stateChanged.connect(self.on_rest_machining_check)
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

        # tool table widgets
        for row in range(self.ui.tools_table.rowCount()):

            try:
                self.ui.tools_table.cellWidget(row, 2).currentIndexChanged.disconnect()
            except (TypeError, AttributeError):
                pass

        # Tool Parameters
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
            elif isinstance(current_widget, FCDoubleSpinner) or isinstance(current_widget, FCSpinner):
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
            self.ui.rest_cb.stateChanged.disconnect()
        except (TypeError, ValueError):
            pass
        try:
            self.ui.order_radio.activated_custom[str].disconnect()
        except (TypeError, ValueError):
            pass

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
            self.ui.generate_iso_button.setDisabled(True)
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("No Tool Selected"))
            )
            self.blockSignals(False)
            return
        else:
            self.ui.generate_iso_button.setDisabled(False)

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
                    for tooluid_key, tooluid_value in list(self.iso_tools.items()):
                        if int(tooluid_key) == tooluid:
                            for key, value in tooluid_value.items():
                                if key == 'data':
                                    self.storage_to_form(tooluid_value['data'])
                except Exception as e:
                    log.debug("ToolIsolation ---> update_ui() " + str(e))
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
                        log.debug("ToolIsolation.storage_to_form() --> %s" % str(e))
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

            for tooluid_key, tooluid_val in self.iso_tools.items():
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
            log.debug("ToolIsolation.on_apply_param_to_all_clicked() --> no tool in Tools Table, aborting.")
            return

        self.blockSignals(True)

        row = self.ui.tools_table.currentRow()
        if row < 0:
            row = 0

        tooluid_item = int(self.ui.tools_table.item(row, 3).text())
        temp_tool_data = {}

        for tooluid_key, tooluid_val in self.iso_tools.items():
            if int(tooluid_key) == tooluid_item:
                # this will hold the 'data' key of the self.tools[tool] dictionary that corresponds to
                # the current row in the tool table
                temp_tool_data = tooluid_val['data']
                break

        for tooluid_key, tooluid_val in self.iso_tools.items():
            tooluid_val['data'] = deepcopy(temp_tool_data)

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

    def on_reference_combo_changed(self):
        obj_type = self.ui.reference_combo_type.currentIndex()
        self.ui.reference_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.ui.reference_combo.setCurrentIndex(0)
        self.ui.reference_combo.obj_type = {0: "Gerber", 1: "Excellon", 2: "Geometry"}[obj_type]

    def on_toggle_reference(self):
        val = self.ui.select_combo.get_value()

        if val == 0:    # ALl
            self.ui.reference_combo.hide()
            self.ui.reference_combo_type.hide()
            self.ui.reference_combo_type_label.hide()
            self.ui.area_shape_label.hide()
            self.ui.area_shape_radio.hide()
            self.ui.poly_int_cb.hide()

            # disable rest-machining for area painting
            self.ui.rest_cb.setDisabled(False)
        elif val == 1:  # Area Selection
            self.ui.reference_combo.hide()
            self.ui.reference_combo_type.hide()
            self.ui.reference_combo_type_label.hide()
            self.ui.area_shape_label.show()
            self.ui.area_shape_radio.show()
            self.ui.poly_int_cb.hide()

            # disable rest-machining for area isolation
            self.ui.rest_cb.set_value(False)
            self.ui.rest_cb.setDisabled(True)
        elif val == 2:  # Polygon Selection
            self.ui.reference_combo.hide()
            self.ui.reference_combo_type.hide()
            self.ui.reference_combo_type_label.hide()
            self.ui.area_shape_label.hide()
            self.ui.area_shape_radio.hide()
            self.ui.poly_int_cb.show()
        else:   # Reference Object
            self.ui.reference_combo.show()
            self.ui.reference_combo_type.show()
            self.ui.reference_combo_type_label.show()
            self.ui.area_shape_label.hide()
            self.ui.area_shape_radio.hide()
            self.ui.poly_int_cb.hide()

            # disable rest-machining for area painting
            self.ui.rest_cb.setDisabled(False)

    def on_order_changed(self, order):
        if order != 'no':
            self.build_ui()

    def on_rest_machining_check(self, state):
        if state:
            self.ui.order_radio.set_value('rev')
            self.ui.order_label.setDisabled(True)
            self.ui.order_radio.setDisabled(True)

            self.old_combine_state = self.ui.combine_passes_cb.get_value()
            self.ui.combine_passes_cb.set_value(True)
            self.ui.combine_passes_cb.setDisabled(True)

            self.ui.forced_rest_iso_cb.setDisabled(False)
        else:
            self.ui.order_label.setDisabled(False)
            self.ui.order_radio.setDisabled(False)

            self.ui.combine_passes_cb.set_value(self.old_combine_state)
            self.ui.combine_passes_cb.setDisabled(False)

            self.ui.forced_rest_iso_cb.setDisabled(True)

    def on_tooltable_cellwidget_change(self):
        cw = self.sender()
        assert isinstance(cw, QtWidgets.QComboBox), \
            "Expected a QtWidgets.QComboBox, got %s" % isinstance(cw, QtWidgets.QComboBox)

        cw_index = self.ui.tools_table.indexAt(cw.pos())
        cw_row = cw_index.row()
        cw_col = cw_index.column()

        currenuid = int(self.ui.tools_table.item(cw_row, 3).text())

        # if the sender is in the column with index 2 then we update the tool_type key
        if cw_col == 2:
            tt = cw.currentText()
            typ = 'Iso' if tt == 'V' else 'Rough'

            self.iso_tools[currenuid].update({
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

                    if self.safe_tooldia:
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
                        for tool in sorted_tools:
                            tool_dia = float(self.iso_tools[tool]['tooldia'])
                            if tool_dia > self.safe_tooldia:
                                msg = _("Incomplete isolation. "
                                        "At least one tool could not do a complete isolation.")
                                self.app.inform.emit('[WARNING] %s' % msg)
                                break

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
                        msg = _("The Gerber object has one Polygon as geometry.\n"
                                "There are no distances between geometry elements to be found.")
                        app_obj.inform.emit('[ERROR_NOTCL] %s' % msg)
                        return 'fail'

                    min_dict = {}
                    idx = 1
                    for geo in total_geo:
                        for s_geo in total_geo[idx:]:
                            if self.app.abort_flag:
                                # graceful abort requested by the user
                                raise grace

                            # minimize the number of distances by not taking into considerations those
                            # that are too small
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

        tool_dia = custom_dia if custom_dia is not None else self.ui.new_tooldia_entry.get_value()
        # construct a list of all 'tooluid' in the self.iso_tools
        tool_uid_list = [int(tooluid_key) for tooluid_key in self.iso_tools]

        # find maximum from the temp_uid, add 1 and this is the new 'tooluid'
        max_uid = 0 if not tool_uid_list else max(tool_uid_list)
        tooluid = int(max_uid) + 1

        new_tools_dict = deepcopy(self.default_data)
        updated_tooldia = None

        tool_dias = []
        for k, v in self.iso_tools.items():
            for tool_v in v.keys():
                if tool_v == 'tooldia':
                    tool_dias.append(self.app.dec_format(v['tooldia'], self.decimals))

        # determine the new tool diameter
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
            self.app.inform.emit('[ERROR] %s' % _("Could not load Tools DB file."))
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
            if db_tool_val['data']['tool_target'] != 3:     # _('Isolation')
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
        self.iso_tools.update({
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

        tool_dia = dia if dia is not None else self.ui.new_tooldia_entry.get_value()

        if tool_dia is None or tool_dia == 0:
            self.build_ui()
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Please enter a tool diameter with non-zero value, "
                                                          "in Float format."))
            self.blockSignals(False)
            return

        # construct a list of all 'tooluid' in the self.iso_tools
        tool_uid_list = [int(tooluid_key) for tooluid_key in self.iso_tools]

        # find maximum from the temp_uid, add 1 and this is the new 'tooluid'
        max_uid = 0 if not tool_uid_list else max(tool_uid_list)
        self.tooluid = int(max_uid + 1)

        tool_dias = []
        for k, v in self.iso_tools.items():
            for tool_v in v.keys():
                if tool_v == 'tooldia':
                    tool_dias.append(self.app.dec_format(v[tool_v], self.decimals))

        truncated_tooldia = self.app.dec_format(tool_dia, self.decimals)
        if truncated_tooldia in tool_dias:
            if muted is None:
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled. Tool already in Tool Table."))
            # self.ui.tools_table.itemChanged.connect(self.on_tool_edit)
            self.blockSignals(False)
            return

        self.iso_tools.update({
            int(self.tooluid): {
                'tooldia':          truncated_tooldia,
                'offset':           'Path',
                'offset_value':     0.0,
                'type': '           Iso',
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
                self.app.inform.emit('[ERROR_NOTCL]  %s' % _("Wrong value format entered, use a number."))
                self.blockSignals(False)
                return

        for v in self.iso_tools.values():
            tool_dias = [float('%.*f' % (self.decimals, v[tool_v])) for tool_v in v.keys() if tool_v == 'tooldia']

        # identify the tool that was edited and get it's tooluid
        if new_tool_dia not in tool_dias:
            self.iso_tools[editeduid]['tooldia'] = deepcopy(float('%.*f' % (self.decimals, new_tool_dia)))
            self.app.inform.emit('[success] %s' % _("Tool from Tool Table was edited."))
            self.blockSignals(False)
            self.build_ui()
            return

        # identify the old tool_dia and restore the text in tool table
        for k, v in self.iso_tools.items():
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

        :param rows_to_delete:      which rows to delete; can be a list
        :param all_tools:           delete all tools in the tool table
        :return:
        """
        self.blockSignals(True)

        deleted_tools_list = []

        if all_tools:
            self.iso_tools.clear()
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
                self.iso_tools.pop(t, None)

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
                    self.iso_tools.pop(t, None)

        except AttributeError:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Delete failed. Select a tool to delete."))
            self.blockSignals(False)
            return
        except Exception as e:
            log.debug(str(e))

        self.app.inform.emit('[success] %s' % _("Tool(s) deleted from Tool Table."))
        self.blockSignals(False)
        self.build_ui()

    def on_generate_buffer(self):
        self.app.inform.emit('[WARNING_NOTCL] %s...' % _("Buffering solid geometry"))

        self.obj_name = self.ui.object_combo.currentText()

        # Get source object.
        try:
            self.grb_obj = self.app.collection.get_by_name(self.obj_name)
        except Exception as e:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), str(self.obj_name)))
            return "Could not retrieve object: %s with error: %s" % (self.obj_name, str(e))

        if self.grb_obj is None:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Object not found"), str(self.obj_name)))
            return

        def buffer_task(app_obj):
            with app_obj.proc_container.new('%s...' % _("Buffering")):
                if isinstance(self.grb_obj.solid_geometry, list):
                    self.grb_obj.solid_geometry = MultiPolygon(self.grb_obj.solid_geometry)

                self.grb_obj.solid_geometry = self.grb_obj.solid_geometry.buffer(0.0000001)
                self.grb_obj.solid_geometry = self.grb_obj.solid_geometry.buffer(-0.0000001)
                app_obj.inform.emit('[success] %s' % _("Done."))
                self.grb_obj.plot_single_object.emit()

        self.app.worker_task.emit({'fcn': buffer_task, 'params': [self.app]})

    def on_iso_button_click(self):

        self.obj_name = self.ui.object_combo.currentText()

        # Get source object.
        try:
            self.grb_obj = self.app.collection.get_by_name(self.obj_name)
        except Exception:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), str(self.obj_name)))
            return

        if self.grb_obj is None:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Object not found"), str(self.obj_name)))
            return

        if self.ui.valid_cb.get_value() is True:
            self.find_safe_tooldia_multiprocessing()

        def worker_task(iso_obj):
            with self.app.proc_container.new('%s ...' % _("Isolating")):
                self.isolate_handler(iso_obj)

        self.app.worker_task.emit({'fcn': worker_task, 'params': [self.grb_obj]})

    def follow_geo(self, followed_obj, outname):
        """
        Creates a geometry object "following" the gerber paths.

        :param followed_obj:    Gerber object for which to generate the follow geometry
        :type followed_obj:     AppObjects.FlatCAMGerber.GerberObject
        :param outname:         Nme of the resulting Geometry object
        :type outname:          str
        :return: None
        """

        def follow_init(follow_obj, app_obj):
            # Propagate options
            follow_obj.options["cnctooldia"] = str(tooldia)
            follow_obj.solid_geometry = self.grb_obj.follow_geometry
            app_obj.inform.emit('[success] %s.' % _("Following geometry was generated"))

        # in the end toggle the visibility of the origin object so we can see the generated Geometry
        followed_obj.ui.plot_cb.set_value(False)
        follow_name = outname

        for tool in self.iso_tools:
            tooldia = self.iso_tools[tool]['tooldia']
            new_name = "%s_%.*f" % (follow_name, self.decimals, tooldia)

            follow_state = self.iso_tools[tool]['data']['tools_iso_follow']
            if follow_state:
                ret = self.app.app_obj.new_object("geometry", new_name, follow_init)
                if ret == 'fail':
                    self.app.inform.emit("[ERROR_NOTCL] %s: %.*f" % (
                        _("Failed to create Follow Geometry with tool diameter"), self.decimals, tooldia))
                else:
                    self.app.inform.emit("[success] %s: %.*f" % (
                        _("Follow Geometry was created with tool diameter"), self.decimals, tooldia))

    def isolate_handler(self, isolated_obj):
        """
        Creates a geometry object with paths around the gerber features.

        :param isolated_obj:    Gerber object for which to generate the isolating routing geometry
        :type isolated_obj:     AppObjects.FlatCAMGerber.GerberObject
        :return: None
        """
        selection = self.ui.select_combo.get_value()

        if selection == 0:  # ALL
            self.isolate(isolated_obj=isolated_obj)
        elif selection == 1:    # Area Selection
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

        elif selection == 2:    # Polygon Selection
            # disengage the grid snapping since it may be hard to click on polygons with grid snapping on
            if self.app.ui.grid_snap_btn.isChecked():
                self.grid_status_memory = True
                self.app.ui.grid_snap_btn.trigger()
            else:
                self.grid_status_memory = False

            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Click on a polygon to isolate it."))
            self.mr = self.app.plotcanvas.graph_event_connect('mouse_release', self.on_poly_mouse_click_release)
            self.kp = self.app.plotcanvas.graph_event_connect('key_press', self.on_key_press)

            if self.app.is_legacy is False:
                self.app.plotcanvas.graph_event_disconnect('mouse_release',
                                                           self.app.on_mouse_click_release_over_plot)
            else:
                self.app.plotcanvas.graph_event_disconnect(self.app.mr)

            # disconnect flags
            self.poly_sel_disconnect_flag = True

        elif selection == 3:    # Reference Object
            ref_obj = self.app.collection.get_by_name(self.ui.reference_combo.get_value())
            ref_geo = unary_union(ref_obj.solid_geometry)
            use_geo = unary_union(isolated_obj.solid_geometry).difference(ref_geo)
            self.isolate(isolated_obj=isolated_obj, geometry=use_geo)

    def isolate(self, isolated_obj, geometry=None, limited_area=None, negative_dia=None, plot=True):
        """
        Creates an isolation routing geometry object in the project.

        :param isolated_obj:    Gerber object for which to generate the isolating routing geometry
        :type isolated_obj:     AppObjects.FlatCAMGerber.GerberObject
        :param geometry:        specific geometry to isolate
        :type geometry:         List of Shapely polygon
        :param limited_area:    if not None isolate only this area
        :type limited_area:     Shapely Polygon or a list of them
        :param negative_dia:    isolate the geometry with a negative value for the tool diameter
        :type negative_dia:     bool
        :param plot:            if to plot the resulting geometry object
        :type plot:             bool
        :return: None
        """

        combine = self.ui.combine_passes_cb.get_value()
        tools_storage = self.iso_tools

        sorted_tools = []
        table_items = self.ui.tools_table.selectedItems()
        sel_rows = {t.row() for t in table_items}
        for row in sel_rows:
            tid = int(self.ui.tools_table.item(row, 3).text())
            sorted_tools.append(tid)
        if not sorted_tools:
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("There are no tools selected in the Tool Table."))
            return 'fail'

        # update the Common Parameters values in the self.iso_tools
        for tool_iso in self.iso_tools:
            for key in self.iso_tools[tool_iso]:
                if key == 'data':
                    self.iso_tools[tool_iso][key]["tools_iso_rest"] = self.ui.rest_cb.get_value()
                    self.iso_tools[tool_iso][key]["tools_iso_combine_passes"] = combine
                    self.iso_tools[tool_iso][key]["tools_iso_isoexcept"] = self.ui.except_cb.get_value()
                    self.iso_tools[tool_iso][key]["tools_iso_selection"] = self.ui.select_combo.get_value()
                    self.iso_tools[tool_iso][key]["tools_iso_area_shape"] = self.ui.area_shape_radio.get_value()

        if combine:
            if self.ui.rest_cb.get_value():
                self.combined_rest(iso_obj=isolated_obj, iso2geo=geometry, tools_storage=tools_storage,
                                   lim_area=limited_area, negative_dia=negative_dia, plot=plot)
            else:
                self.combined_normal(iso_obj=isolated_obj, iso2geo=geometry, tools_storage=tools_storage,
                                     lim_area=limited_area, negative_dia=negative_dia, plot=plot)

        else:
            prog_plot = self.app.defaults["tools_iso_plotting"]

            for tool in sorted_tools:
                tool_data = tools_storage[tool]['data']
                to_follow = tool_data['tools_iso_follow']

                work_geo = geometry
                if work_geo is None:
                    work_geo = isolated_obj.follow_geometry if to_follow else isolated_obj.solid_geometry

                iso_t = {
                    'ext': 0,
                    'int': 1,
                    'full': 2
                }[tool_data['tools_iso_isotype']]

                passes = tool_data['tools_iso_passes']
                overlap = tool_data['tools_iso_overlap']
                overlap /= 100.0

                milling_type = tool_data['tools_iso_milling_type']

                iso_except = self.ui.except_cb.get_value()

                for i in range(passes):
                    tool_dia = tools_storage[tool]['tooldia']
                    tool_type = tools_storage[tool]['tool_type']

                    iso_offset = tool_dia * ((2 * i + 1) / 2.0000001) - (i * overlap * tool_dia)
                    if negative_dia:
                        iso_offset = -iso_offset

                    outname = "%s_%.*f" % (isolated_obj.options["name"], self.decimals, float(tool_dia))

                    if passes > 1:
                        iso_name = outname + "_iso" + str(i + 1)
                        if iso_t == 0:
                            iso_name = outname + "_ext_iso" + str(i + 1)
                        elif iso_t == 1:
                            iso_name = outname + "_int_iso" + str(i + 1)
                    else:
                        iso_name = outname + "_iso"
                        if iso_t == 0:
                            iso_name = outname + "_ext_iso"
                        elif iso_t == 1:
                            iso_name = outname + "_int_iso"

                    # if milling type is climb then the move is counter-clockwise around features
                    mill_dir = 1 if milling_type == 'cl' else 0

                    iso_geo = self.generate_envelope(iso_offset, mill_dir, geometry=work_geo, env_iso_type=iso_t,
                                                     follow=to_follow, nr_passes=i, prog_plot=prog_plot)
                    if iso_geo == 'fail':
                        self.app.inform.emit('[ERROR_NOTCL] %s' % _("Isolation geometry could not be generated."))
                        continue

                    # ############################################################
                    # ########## AREA SUBTRACTION ################################
                    # ############################################################
                    if iso_except:
                        self.app.proc_container.update_view_text(' %s' % _("Subtracting Geo"))
                        iso_geo = self.area_subtraction(iso_geo)

                    if limited_area:
                        self.app.proc_container.update_view_text(' %s' % _("Intersecting Geo"))
                        iso_geo = self.area_intersection(iso_geo, intersection_geo=limited_area)

                    # make sure that no empty geometry element is in the solid_geometry
                    new_solid_geo = [geo for geo in iso_geo if not geo.is_empty]

                    tool_data.update({
                        "name": iso_name,
                    })

                    def iso_init(geo_obj, fc_obj):
                        # Propagate options
                        geo_obj.options["cnctooldia"] = str(tool_dia)
                        geo_obj.solid_geometry = deepcopy(new_solid_geo)

                        # ############################################################
                        # ########## AREA SUBTRACTION ################################
                        # ############################################################
                        if self.ui.except_cb.get_value():
                            self.app.proc_container.update_view_text(' %s' % _("Subtracting Geo"))
                            geo_obj.solid_geometry = self.area_subtraction(geo_obj.solid_geometry)

                        geo_obj.tools = {'1': {}}
                        geo_obj.tools.update({
                            '1': {
                                'tooldia':          float(tool_dia),
                                'offset':           'Path',
                                'offset_value':     0.0,
                                'type':             'Rough',
                                'tool_type':        tool_type,
                                'data':             tool_data,
                                'solid_geometry':   geo_obj.solid_geometry
                            }
                        })

                        # detect if solid_geometry is empty and this require list flattening which is "heavy"
                        # or just looking in the lists (they are one level depth) and if any is not empty
                        # proceed with object creation, if there are empty and the number of them is the length
                        # of the list then we have an empty solid_geometry which should raise a Custom Exception
                        empty_cnt = 0
                        if not isinstance(geo_obj.solid_geometry, list):
                            geo_obj.solid_geometry = [geo_obj.solid_geometry]

                        for g in geo_obj.solid_geometry:
                            if g:
                                break
                            else:
                                empty_cnt += 1

                        if empty_cnt == len(geo_obj.solid_geometry):
                            fc_obj.inform.emit('[ERROR_NOTCL] %s: %s' % (
                                _("Empty Geometry in"), geo_obj.options["name"]))
                            return 'fail'
                        else:
                            fc_obj.inform.emit('[success] %s: %s' %
                                               (_("Isolation geometry created"), geo_obj.options["name"]))
                        geo_obj.multigeo = True

                    self.app.app_obj.new_object("geometry", iso_name, iso_init, plot=plot)

            # clean the progressive plotted shapes if it was used

            if prog_plot == 'progressive':
                self.temp_shapes.clear(update=True)

        # Switch notebook to Properties page
        self.app.ui.notebook.setCurrentWidget(self.app.ui.properties_tab)

    def combined_rest(self, iso_obj, iso2geo, tools_storage, lim_area, negative_dia=None, plot=True):
        """
        Isolate the provided Gerber object using "rest machining" strategy

        :param iso_obj:         the isolated Gerber object
        :type iso_obj:          AppObjects.FlatCAMGerber.GerberObject
        :param iso2geo:         specific geometry to isolate
        :type iso2geo:          list of Shapely Polygon
        :param tools_storage:   a dictionary that holds the tools and geometry
        :type tools_storage:    dict
        :param lim_area:        if not None restrict isolation to this area
        :type lim_area:         Shapely Polygon or a list of them
        :param negative_dia:    isolate the geometry with a negative value for the tool diameter
        :type negative_dia:     bool
        :param plot:            if to plot the resulting geometry object
        :type plot:             bool
        :return:                Isolated solid geometry
        :rtype:
        """

        log.debug("ToolIsolation.combine_rest()")

        total_solid_geometry = []

        iso_name = iso_obj.options["name"] + '_iso_rest'
        work_geo = iso_obj.solid_geometry if iso2geo is None else iso2geo

        # sorted_tools = []
        # for k, v in self.iso_tools.items():
        #     sorted_tools.append(float('%.*f' % (self.decimals, float(v['tooldia']))))

        sorted_tools = []
        table_items = self.ui.tools_table.selectedItems()
        sel_rows = {t.row() for t in table_items}
        for row in sel_rows:
            try:
                tdia = float(self.ui.tools_table.item(row, 1).text())
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    tdia = float(self.ui.tools_table.item(row, 1).text().replace(',', '.'))
                except ValueError:
                    self.app.inform.emit('[ERROR_NOTCL] %s' % _("Wrong value format entered, use a number."))
                    continue
            sorted_tools.append(float('%.*f' % (self.decimals, tdia)))

        if not sorted_tools:
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("There are no tools selected in the Tool Table."))
            return 'fail'

        order = self.ui.order_radio.get_value()
        if order == 'fwd':
            sorted_tools.sort(reverse=False)
        elif order == 'rev':
            sorted_tools.sort(reverse=True)
        else:
            pass

        # decide to use "progressive" or "normal" plotting
        prog_plot = self.app.defaults["tools_iso_plotting"]

        for sorted_tool in sorted_tools:
            for tool in tools_storage:
                if float('%.*f' % (self.decimals, tools_storage[tool]['tooldia'])) == sorted_tool:

                    tool_dia = tools_storage[tool]['tooldia']
                    tool_type = tools_storage[tool]['tool_type']
                    tool_data = tools_storage[tool]['data']

                    passes = tool_data['tools_iso_passes']
                    overlap = tool_data['tools_iso_overlap']
                    overlap /= 100.0

                    milling_type = tool_data['tools_iso_milling_type']
                    # if milling type is climb then the move is counter-clockwise around features
                    mill_dir = True if milling_type == 'cl' else False
                    iso_t = {
                        'ext': 0,
                        'int': 1,
                        'full': 2
                    }[tool_data['tools_iso_isotype']]

                    forced_rest = self.ui.forced_rest_iso_cb.get_value()
                    iso_except = self.ui.except_cb.get_value()

                    outname = "%s_%.*f" % (iso_obj.options["name"], self.decimals, float(tool_dia))
                    internal_name = outname + "_iso"
                    if iso_t == 0:
                        internal_name = outname + "_ext_iso"
                    elif iso_t == 1:
                        internal_name = outname + "_int_iso"

                    tool_data.update({
                        "name": internal_name,
                    })

                    solid_geo, work_geo = self.generate_rest_geometry(geometry=work_geo, tooldia=tool_dia,
                                                                      passes=passes, overlap=overlap, invert=mill_dir,
                                                                      env_iso_type=iso_t, negative_dia=negative_dia,
                                                                      forced_rest=forced_rest,
                                                                      prog_plot=prog_plot,
                                                                      prog_plot_handler=self.plot_temp_shapes)

                    # ############################################################
                    # ########## AREA SUBTRACTION ################################
                    # ############################################################
                    if iso_except:
                        self.app.proc_container.update_view_text(' %s' % _("Subtracting Geo"))
                        solid_geo = self.area_subtraction(solid_geo)

                    if lim_area:
                        self.app.proc_container.update_view_text(' %s' % _("Intersecting Geo"))
                        solid_geo = self.area_intersection(solid_geo, intersection_geo=lim_area)

                    # make sure that no empty geometry element is in the solid_geometry
                    new_solid_geo = [geo for geo in solid_geo if not geo.is_empty]

                    tools_storage.update({
                        tool: {
                            'tooldia':          float(tool_dia),
                            'offset':           'Path',
                            'offset_value':     0.0,
                            'type':             'Rough',
                            'tool_type':        tool_type,
                            'data':             tool_data,
                            'solid_geometry':   deepcopy(new_solid_geo)
                        }
                    })

                    total_solid_geometry += new_solid_geo

                    # if the geometry is all isolated
                    if not work_geo:
                        break

        # clean the progressive plotted shapes if it was used
        if self.app.defaults["tools_iso_plotting"] == 'progressive':
            self.temp_shapes.clear(update=True)

        # remove tools without geometry
        for tool, tool_dict in list(tools_storage.items()):
            if not tool_dict['solid_geometry']:
                tools_storage.pop(tool, None)

        def iso_init(geo_obj, app_obj):
            geo_obj.options["cnctooldia"] = str(tool_dia)

            geo_obj.tools = dict(tools_storage)
            geo_obj.solid_geometry = total_solid_geometry
            # even if combine is checked, one pass is still single-geo

            # remove the tools that have no geometry
            for geo_tool in list(geo_obj.tools.keys()):
                if not geo_obj.tools[geo_tool]['solid_geometry']:
                    geo_obj.tools.pop(geo_tool, None)

            if len(tools_storage) > 1:
                geo_obj.multigeo = True
            else:
                for ky in tools_storage.keys():
                    passes_no = float(tools_storage[ky]['data']['tools_iso_passes'])
                    geo_obj.multigeo = True
                    break

            # detect if solid_geometry is empty and this require list flattening which is "heavy"
            # or just looking in the lists (they are one level depth) and if any is not empty
            # proceed with object creation, if there are empty and the number of them is the length
            # of the list then we have an empty solid_geometry which should raise a Custom Exception
            empty_cnt = 0
            if not isinstance(geo_obj.solid_geometry, list) and \
                    not isinstance(geo_obj.solid_geometry, MultiPolygon):
                geo_obj.solid_geometry = [geo_obj.solid_geometry]

            for g in geo_obj.solid_geometry:
                if g:
                    break
                else:
                    empty_cnt += 1

            if empty_cnt == len(geo_obj.solid_geometry):
                app_obj.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Empty Geometry in"), geo_obj.options["name"]))
                return 'fail'
            else:
                app_obj.inform.emit('[success] %s: %s' % (_("Isolation geometry created"), geo_obj.options["name"]))

        self.app.app_obj.new_object("geometry", iso_name, iso_init, plot=plot)

        # the tools are finished but the isolation is not finished therefore it failed
        if work_geo:
            self.app.inform.emit("[WARNING] %s" % _("Partial failure. The geometry was processed with all tools.\n"
                                                    "But there are still not-isolated geometry elements. "
                                                    "Try to include a tool with smaller diameter."))
            msg = _("The following are coordinates for the copper features that could not be isolated:")
            self.app.inform_shell.emit(msg)
            msg = ''
            for geo in work_geo:
                pt = geo.representative_point()
                coords = '(%s, %s), ' % (str(pt.x), str(pt.y))
                msg += coords
            self.app.inform_shell.emit(msg=msg)

    def combined_normal(self, iso_obj, iso2geo, tools_storage, lim_area, negative_dia=None, plot=True):
        """

        :param iso_obj:         the isolated Gerber object
        :type iso_obj:          AppObjects.FlatCAMGerber.GerberObject
        :param iso2geo:         specific geometry to isolate
        :type iso2geo:          list of Shapely Polygon
        :param tools_storage:   a dictionary that holds the tools and geometry
        :type tools_storage:    dict
        :param lim_area:        if not None restrict isolation to this area
        :type lim_area:         Shapely Polygon or a list of them
        :param negative_dia:    isolate the geometry with a negative value for the tool diameter
        :type negative_dia:     bool
        :param plot:            if to plot the resulting geometry object
        :type plot:             bool
        :return:                Isolated solid geometry
        :rtype:
        """
        log.debug("ToolIsolation.combined_normal()")

        total_solid_geometry = []

        iso_name = iso_obj.options["name"] + '_iso_combined'
        geometry = iso2geo
        prog_plot = self.app.defaults["tools_iso_plotting"]

        sorted_tools = []
        table_items = self.ui.tools_table.selectedItems()
        sel_rows = {t.row() for t in table_items}
        for row in sel_rows:
            tid = int(self.ui.tools_table.item(row, 3).text())
            sorted_tools.append(tid)
        if not sorted_tools:
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("There are no tools selected in the Tool Table."))
            return 'fail'

        for tool in sorted_tools:
            tool_dia = tools_storage[tool]['tooldia']
            tool_has_offset = tools_storage[tool]['offset']
            tool_offset_value = tools_storage[tool]['offset_value']
            tool_type = tools_storage[tool]['tool_type']
            tool_cut_type = tools_storage[tool]['type']
            tool_data = tools_storage[tool]['data']

            to_follow = tool_data['tools_iso_follow']

            # TODO what to do when the iso2geo param is not None but the Follow cb is checked
            # for the case when limited area is used .... the follow geo should be clipped too
            work_geo = geometry
            if work_geo is None:
                work_geo = iso_obj.follow_geometry if to_follow else iso_obj.solid_geometry

            iso_t = {
                'ext': 0,
                'int': 1,
                'full': 2
            }[tool_data['tools_iso_isotype']]

            passes = tool_data['tools_iso_passes']
            overlap = tool_data['tools_iso_overlap']
            overlap /= 100.0

            milling_type = tool_data['tools_iso_milling_type']

            iso_except = self.ui.except_cb.get_value()

            outname = "%s_%.*f" % (iso_obj.options["name"], self.decimals, float(tool_dia))

            internal_name = outname + "_iso"
            if iso_t == 0:
                internal_name = outname + "_ext_iso"
            elif iso_t == 1:
                internal_name = outname + "_int_iso"

            tool_data.update({
                "name": internal_name,
            })

            solid_geo = []
            for nr_pass in range(passes):
                iso_offset = tool_dia * ((2 * nr_pass + 1) / 2.0000001) - (nr_pass * overlap * tool_dia)
                if negative_dia:
                    iso_offset = -iso_offset

                # if milling type is climb then the move is counter-clockwise around features
                mill_dir = 1 if milling_type == 'cl' else 0

                iso_geo = self.generate_envelope(iso_offset, mill_dir, geometry=work_geo, env_iso_type=iso_t,
                                                 follow=to_follow, nr_passes=nr_pass, prog_plot=prog_plot)
                if iso_geo == 'fail':
                    self.app.inform.emit('[ERROR_NOTCL] %s' % _("Isolation geometry could not be generated."))
                    continue
                try:
                    for geo in iso_geo:
                        solid_geo.append(geo)
                except TypeError:
                    solid_geo.append(iso_geo)

            # ############################################################
            # ########## AREA SUBTRACTION ################################
            # ############################################################
            if iso_except:
                self.app.proc_container.update_view_text(' %s' % _("Subtracting Geo"))
                solid_geo = self.area_subtraction(solid_geo)

            if lim_area:
                self.app.proc_container.update_view_text(' %s' % _("Intersecting Geo"))
                solid_geo = self.area_intersection(solid_geo, intersection_geo=lim_area)

            # make sure that no empty geometry element is in the solid_geometry
            new_solid_geo = [geo for geo in solid_geo if not geo.is_empty]

            tools_storage.update({
                tool: {
                    'tooldia':          float(tool_dia),
                    'offset':           tool_has_offset,
                    'offset_value':     tool_offset_value,
                    'type':             tool_cut_type,
                    'tool_type':        tool_type,
                    'data':             tool_data,
                    'solid_geometry':   deepcopy(new_solid_geo)
                }
            })

            total_solid_geometry += new_solid_geo

        # clean the progressive plotted shapes if it was used
        if prog_plot == 'progressive':
            self.temp_shapes.clear(update=True)

        # remove tools without geometry
        for tool, tool_dict in list(tools_storage.items()):
            if not tool_dict['solid_geometry']:
                tools_storage.pop(tool, None)

        def iso_init(geo_obj, app_obj):
            geo_obj.options["cnctooldia"] = str(tool_dia)

            geo_obj.tools = dict(tools_storage)
            geo_obj.solid_geometry = total_solid_geometry
            # even if combine is checked, one pass is still single-geo

            if len(tools_storage) > 1:
                geo_obj.multigeo = True
            else:
                if to_follow:
                    geo_obj.multigeo = False
                else:
                    passes_no = 1
                    for ky in tools_storage.keys():
                        passes_no = float(tools_storage[ky]['data']['tools_iso_passes'])
                        geo_obj.multigeo = True
                        break
                    geo_obj.multigeo = True

            # detect if solid_geometry is empty and this require list flattening which is "heavy"
            # or just looking in the lists (they are one level depth) and if any is not empty
            # proceed with object creation, if there are empty and the number of them is the length
            # of the list then we have an empty solid_geometry which should raise a Custom Exception
            empty_cnt = 0
            if not isinstance(geo_obj.solid_geometry, list) and \
                    not isinstance(geo_obj.solid_geometry, MultiPolygon):
                geo_obj.solid_geometry = [geo_obj.solid_geometry]

            for g in geo_obj.solid_geometry:
                if g:
                    break
                else:
                    empty_cnt += 1

            if empty_cnt == len(geo_obj.solid_geometry):
                app_obj.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Empty Geometry in"), geo_obj.options["name"]))
                return 'fail'
            else:
                app_obj.inform.emit('[success] %s: %s' % (_("Isolation geometry created"), geo_obj.options["name"]))

        self.app.app_obj.new_object("geometry", iso_name, iso_init, plot=plot)

    def area_subtraction(self, geo, subtraction_geo=None):
        """
        Subtracts the subtraction_geo (if present else self.solid_geometry) from the geo

        :param geo:                 target geometry from which to subtract
        :param subtraction_geo:     geometry that acts as subtraction geo
        :return:
        """
        new_geometry = []
        target_geo = geo

        if subtraction_geo:
            sub_union = unary_union(subtraction_geo)
        else:
            name = self.ui.exc_obj_combo.currentText()
            subtractor_obj = self.app.collection.get_by_name(name)
            sub_union = unary_union(subtractor_obj.solid_geometry)

        try:
            for geo_elem in target_geo:
                if isinstance(geo_elem, Polygon):
                    for ring in self.poly2rings(geo_elem):
                        new_geo = ring.difference(sub_union)
                        if new_geo and not new_geo.is_empty:
                            new_geometry.append(new_geo)
                elif isinstance(geo_elem, MultiPolygon):
                    for poly in geo_elem:
                        for ring in self.poly2rings(poly):
                            new_geo = ring.difference(sub_union)
                            if new_geo and not new_geo.is_empty:
                                new_geometry.append(new_geo)
                elif isinstance(geo_elem, LineString) or isinstance(geo_elem, LinearRing):
                    new_geo = geo_elem.difference(sub_union)
                    if new_geo:
                        if not new_geo.is_empty:
                            new_geometry.append(new_geo)
                elif isinstance(geo_elem, MultiLineString):
                    for line_elem in geo_elem:
                        new_geo = line_elem.difference(sub_union)
                        if new_geo and not new_geo.is_empty:
                            new_geometry.append(new_geo)
        except TypeError:
            if isinstance(target_geo, Polygon):
                for ring in self.poly2rings(target_geo):
                    new_geo = ring.difference(sub_union)
                    if new_geo:
                        if not new_geo.is_empty:
                            new_geometry.append(new_geo)
            elif isinstance(target_geo, LineString) or isinstance(target_geo, LinearRing):
                new_geo = target_geo.difference(sub_union)
                if new_geo and not new_geo.is_empty:
                    new_geometry.append(new_geo)
            elif isinstance(target_geo, MultiLineString):
                for line_elem in target_geo:
                    new_geo = line_elem.difference(sub_union)
                    if new_geo and not new_geo.is_empty:
                        new_geometry.append(new_geo)
        return new_geometry

    def area_intersection(self, geo, intersection_geo=None):
        """
        Return the intersection geometry between geo and intersection_geo

        :param geo:                 target geometry
        :param intersection_geo:    second geometry
        :return:
        """
        new_geometry = []
        target_geo = geo

        intersect_union = unary_union(intersection_geo)

        try:
            for geo_elem in target_geo:
                if isinstance(geo_elem, Polygon):
                    for ring in self.poly2rings(geo_elem):
                        new_geo = ring.intersection(intersect_union)
                        if new_geo and not new_geo.is_empty:
                            new_geometry.append(new_geo)
                elif isinstance(geo_elem, MultiPolygon):
                    for poly in geo_elem:
                        for ring in self.poly2rings(poly):
                            new_geo = ring.intersection(intersect_union)
                            if new_geo and not new_geo.is_empty:
                                new_geometry.append(new_geo)
                elif isinstance(geo_elem, LineString) or isinstance(geo_elem, LinearRing):
                    new_geo = geo_elem.intersection(intersect_union)
                    if new_geo:
                        if not new_geo.is_empty:
                            new_geometry.append(new_geo)
                elif isinstance(geo_elem, MultiLineString):
                    for line_elem in geo_elem:
                        new_geo = line_elem.intersection(intersect_union)
                        if new_geo and not new_geo.is_empty:
                            new_geometry.append(new_geo)
        except TypeError:
            if isinstance(target_geo, Polygon):
                for ring in self.poly2rings(target_geo):
                    new_geo = ring.intersection(intersect_union)
                    if new_geo:
                        if not new_geo.is_empty:
                            new_geometry.append(new_geo)
            elif isinstance(target_geo, LineString) or isinstance(target_geo, LinearRing):
                new_geo = target_geo.intersection(intersect_union)
                if new_geo and not new_geo.is_empty:
                    new_geometry.append(new_geo)
            elif isinstance(target_geo, MultiLineString):
                for line_elem in target_geo:
                    new_geo = line_elem.intersection(intersect_union)
                    if new_geo and not new_geo.is_empty:
                        new_geometry.append(new_geo)
        return new_geometry

    def on_poly_mouse_click_release(self, event):
        if self.app.is_legacy is False:
            event_pos = event.pos
            right_button = 2
            self.app.event_is_dragging = self.app.event_is_dragging
        else:
            event_pos = (event.xdata, event.ydata)
            right_button = 3
            self.app.event_is_dragging = self.app.ui.popMenu.mouse_is_panning

        try:
            x = float(event_pos[0])
            y = float(event_pos[1])
        except TypeError:
            return

        event_pos = (x, y)
        curr_pos = self.app.plotcanvas.translate_coords(event_pos)
        if self.app.grid_status():
            curr_pos = self.app.geo_editor.snap(curr_pos[0], curr_pos[1])
        else:
            curr_pos = (curr_pos[0], curr_pos[1])

        if event.button == 1:
            if self.ui.poly_int_cb.get_value() is True:
                clicked_poly = self.find_polygon_ignore_interiors(point=(curr_pos[0], curr_pos[1]),
                                                                  geoset=self.grb_obj.solid_geometry)

                clicked_poly = self.get_selected_interior(clicked_poly, point=(curr_pos[0], curr_pos[1]))

            else:
                clicked_poly = self.find_polygon(point=(curr_pos[0], curr_pos[1]), geoset=self.grb_obj.solid_geometry)

            if self.app.selection_type is not None:
                self.selection_area_handler(self.app.pos, curr_pos, self.app.selection_type)
                self.app.selection_type = None
            elif clicked_poly:
                if clicked_poly not in self.poly_dict.values():
                    shape_id = self.app.tool_shapes.add(tolerance=self.drawing_tolerance, layer=0, shape=clicked_poly,
                                                        color=self.app.defaults['global_sel_draw_color'] + 'AF',
                                                        face_color=self.app.defaults['global_sel_draw_color'] + 'AF',
                                                        visible=True)
                    self.poly_dict[shape_id] = clicked_poly
                    self.app.inform.emit(
                        '%s: %d. %s' % (_("Added polygon"), int(len(self.poly_dict)),
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
        elif event.button == right_button and self.app.event_is_dragging is False:
            # restore the Grid snapping if it was active before
            if self.grid_status_memory is True:
                self.app.ui.grid_snap_btn.trigger()

            if self.app.is_legacy is False:
                self.app.plotcanvas.graph_event_disconnect('mouse_release', self.on_poly_mouse_click_release)
                self.app.plotcanvas.graph_event_disconnect('key_press', self.on_key_press)
            else:
                self.app.plotcanvas.graph_event_disconnect(self.mr)
                self.app.plotcanvas.graph_event_disconnect(self.kp)

            self.app.mr = self.app.plotcanvas.graph_event_connect('mouse_release',
                                                                  self.app.on_mouse_click_release_over_plot)

            # disconnect flags
            self.poly_sel_disconnect_flag = False

            self.app.tool_shapes.clear(update=True)

            if self.poly_dict:
                poly_list = deepcopy(list(self.poly_dict.values()))
                if self.ui.poly_int_cb.get_value() is True:
                    # isolate the interior polygons with a negative tool
                    self.isolate(isolated_obj=self.grb_obj, geometry=poly_list, negative_dia=True)
                else:
                    self.isolate(isolated_obj=self.grb_obj, geometry=poly_list)
                self.poly_dict.clear()
            else:
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("List of single polygons is empty. Aborting."))

    def selection_area_handler(self, start_pos, end_pos, sel_type):
        """
        :param start_pos: mouse position when the selection LMB click was done
        :param end_pos: mouse position when the left mouse button is released
        :param sel_type: if True it's a left to right selection (enclosure), if False it's a 'touch' selection
        :return:
        """
        poly_selection = Polygon([start_pos, (end_pos[0], start_pos[1]), end_pos, (start_pos[0], end_pos[1])])

        # delete previous selection shape
        self.app.delete_selection_shape()

        added_poly_count = 0
        try:
            for geo in self.solid_geometry:
                if geo not in self.poly_dict.values():
                    if sel_type is True:
                        if geo.within(poly_selection):
                            shape_id = self.app.tool_shapes.add(tolerance=self.drawing_tolerance, layer=0,
                                                                shape=geo,
                                                                color=self.app.defaults['global_sel_draw_color'] + 'AF',
                                                                face_color=self.app.defaults[
                                                                               'global_sel_draw_color'] + 'AF',
                                                                visible=True)
                            self.poly_dict[shape_id] = geo
                            added_poly_count += 1
                    else:
                        if poly_selection.intersects(geo):
                            shape_id = self.app.tool_shapes.add(tolerance=self.drawing_tolerance, layer=0,
                                                                shape=geo,
                                                                color=self.app.defaults['global_sel_draw_color'] + 'AF',
                                                                face_color=self.app.defaults[
                                                                               'global_sel_draw_color'] + 'AF',
                                                                visible=True)
                            self.poly_dict[shape_id] = geo
                            added_poly_count += 1
        except TypeError:
            if self.solid_geometry not in self.poly_dict.values():
                if sel_type is True:
                    if poly_selection.contains(self.solid_geometry):
                        shape_id = self.app.tool_shapes.add(tolerance=self.drawing_tolerance, layer=0,
                                                            shape=self.solid_geometry,
                                                            color=self.app.defaults['global_sel_draw_color'] + 'AF',
                                                            face_color=self.app.defaults[
                                                                           'global_sel_draw_color'] + 'AF',
                                                            visible=True)
                        self.poly_dict[shape_id] = self.solid_geometry
                        added_poly_count += 1
                else:
                    if poly_selection.intersects(self.solid_geometry):
                        shape_id = self.app.tool_shapes.add(tolerance=self.drawing_tolerance, layer=0,
                                                            shape=self.solid_geometry,
                                                            color=self.app.defaults['global_sel_draw_color'] + 'AF',
                                                            face_color=self.app.defaults[
                                                                           'global_sel_draw_color'] + 'AF',
                                                            visible=True)
                        self.poly_dict[shape_id] = self.solid_geometry
                        added_poly_count += 1

        if added_poly_count > 0:
            self.app.tool_shapes.redraw()
            self.app.inform.emit(
                '%s: %d. %s' % (_("Added polygon"),
                                int(added_poly_count),
                                _("Click to add next polygon or right click to start."))
            )
        else:
            self.app.inform.emit(_("No polygon in selection."))

    # To be called after clicking on the plot.
    def on_mouse_release(self, event):
        shape_type = self.ui.area_shape_radio.get_value()

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

        # do clear area only for left mouse clicks
        if event.button == 1:
            if shape_type == "square":
                if self.first_click is False:
                    self.first_click = True
                    self.app.inform.emit('[WARNING_NOTCL] %s' % _("Click the end point of the paint area."))

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
            self.isolate(isolated_obj=self.grb_obj, limited_area=self.sel_rect, plot=True)
            self.sel_rect = []

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

                self.app.mp = self.app.plotcanvas.graph_event_connect('mouse_press',
                                                                      self.app.on_mouse_click_over_plot)
                self.app.mm = self.app.plotcanvas.graph_event_connect('mouse_move',
                                                                      self.app.on_mouse_move_over_plot)
                self.app.mr = self.app.plotcanvas.graph_event_connect('mouse_release',
                                                                      self.app.on_mouse_click_release_over_plot)

            if self.poly_sel_disconnect_flag is False:
                # restore the Grid snapping if it was active before
                if self.grid_status_memory is True:
                    self.app.ui.grid_snap_btn.trigger()

                if self.app.is_legacy is False:
                    self.app.plotcanvas.graph_event_disconnect('mouse_release', self.on_poly_mouse_click_release)
                    self.app.plotcanvas.graph_event_disconnect('key_press', self.on_key_press)
                else:
                    self.app.plotcanvas.graph_event_disconnect(self.mr)
                    self.app.plotcanvas.graph_event_disconnect(self.kp)

                self.app.mr = self.app.plotcanvas.graph_event_connect('mouse_release',
                                                                      self.app.on_mouse_click_release_over_plot)

            self.points = []
            self.poly_drawn = False
            self.delete_moving_selection_shape()
            self.delete_tool_selection_shape()

    def on_iso_tool_add_from_db_executed(self, tool):
        """
        Here add the tool from DB  in the selected geometry object
        :return:
        """
        tool_from_db = deepcopy(tool)

        if tool['data']['tool_target'] not in [0, 3]:   # [General, Isolation]
            for idx in range(self.app.ui.plot_tab_area.count()):
                if self.app.ui.plot_tab_area.tabText(idx) == _("Tools Database"):
                    wdg = self.app.ui.plot_tab_area.widget(idx)
                    wdg.deleteLater()
                    self.app.ui.plot_tab_area.removeTab(idx)
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Selected tool can't be used here. Pick another."))
            return

        res = self.on_tool_from_db_inserted(tool=tool_from_db)

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

    def on_tool_from_db_inserted(self, tool):
        """
        Called from the Tools DB object through a App method when adding a tool from Tools Database
        :param tool: a dict with the tool data
        :return: None
        """

        self.ui_disconnect()
        self.units = self.app.defaults['units'].upper()

        tooldia = float(tool['tooldia'])

        # construct a list of all 'tooluid' in the self.tools
        tool_uid_list = [int(tooluid_key) for tooluid_key in self.iso_tools]

        # find maximum from the temp_uid, add 1 and this is the new 'tooluid'
        max_uid = 0 if not tool_uid_list else max(tool_uid_list)
        tooluid = max_uid + 1

        tool_dias = []
        for k, v in self.iso_tools.items():
            for tool_v in v.keys():
                if tool_v == 'tooldia':
                    tool_dias.append(self.app.dec_format(v[tool_v], self.decimals))

        truncated_tooldia = self.app.dec_format(tooldia, self.decimals)
        if truncated_tooldia in tool_dias:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled. Tool already in Tool Table."))
            self.ui_connect()
            return 'fail'

        self.iso_tools.update({
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

        self.iso_tools[tooluid]['data']['name'] = '_iso'

        self.app.inform.emit('[success] %s' % _("New tool added to Tool Table."))

        self.ui_connect()
        self.build_ui()

        # select the tool just added
        for row in range(self.ui.tools_table.rowCount()):
            if int(self.ui.tools_table.item(row, 3).text()) == self.tooluid:
                self.ui.tools_table.selectRow(row)
                break

        # if self.ui.tools_table.rowCount() != 0:
        #     self.param_frame.setDisabled(False)

    def on_tool_add_from_db_clicked(self):
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
        ret_val = self.app.on_tools_database(source='iso')
        if ret_val == 'fail':
            return
        self.app.tools_db_tab.ok_to_add = True
        self.app.tools_db_tab.ui.buttons_frame.hide()
        self.app.tools_db_tab.ui.add_tool_from_db.show()
        self.app.tools_db_tab.ui.cancel_tool_from_db.show()

    def reset_fields(self):
        self.object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))

    @staticmethod
    def poly2rings(poly):
        return [poly.exterior] + [interior for interior in poly.interiors]

    @staticmethod
    def poly2ext(poly):
        return [poly.exterior]

    @staticmethod
    def poly2ints(poly):
        return [interior for interior in poly.interiors]

    def generate_envelope(self, offset, invert, geometry=None, env_iso_type=2, follow=None, nr_passes=0,
                          prog_plot=False):
        """
        Isolation_geometry produces an envelope that is going on the left of the geometry
        (the copper features). To leave the least amount of burrs on the features
        the tool needs to travel on the right side of the features (this is called conventional milling)
        the first pass is the one cutting all of the features, so it needs to be reversed
        the other passes overlap preceding ones and cut the left over copper. It is better for them
        to cut on the right side of the left over copper i.e on the left side of the features.

        :param offset:          Offset distance to be passed to the obj.isolation_geometry() method
        :type offset:           float
        :param invert:          If to invert the direction of geometry (CW to CCW or reverse)
        :type invert:           int
        :param geometry:        Shapely Geometry for which t ogenerate envelope
        :type geometry:
        :param env_iso_type:    type of isolation, can be 0 = exteriors or 1 = interiors or 2 = both (complete)
        :type env_iso_type:     int
        :param follow:          If the kind of isolation is a "follow" one
        :type follow:           bool
        :param nr_passes:       Number of passes
        :type nr_passes:        int
        :param prog_plot:       Type of plotting: "normal" or "progressive"
        :type prog_plot:        str
        :return:                The buffered geometry
        :rtype:                 MultiPolygon or Polygon
        """

        if follow:
            geom = self.grb_obj.isolation_geometry(offset, geometry=geometry, follow=follow, prog_plot=prog_plot)
            return geom
        else:
            try:
                geom = self.grb_obj.isolation_geometry(offset, geometry=geometry, iso_type=env_iso_type,
                                                       passes=nr_passes, prog_plot=prog_plot)
            except Exception as e:
                log.debug('ToolIsolation.generate_envelope() --> %s' % str(e))
                return 'fail'

        if invert:
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
                    log.debug("ToolIsolation.generate_envelope() Error --> Unexpected Geometry %s" %
                              type(geom))
            except Exception as e:
                log.debug("ToolIsolation.generate_envelope() Error --> %s" % str(e))
                return 'fail'
        return geom

    @staticmethod
    def generate_rest_geometry(geometry, tooldia, passes, overlap, invert, env_iso_type=2, negative_dia=None,
                               forced_rest=False,
                               prog_plot="normal", prog_plot_handler=None):
        """
        Will try to isolate the geometry and return a tuple made of list of paths made through isolation
        and a list of Shapely Polygons that could not be isolated

        :param geometry:            A list of Shapely Polygons to be isolated
        :type geometry:             list
        :param tooldia:             The tool diameter used to do the isolation
        :type tooldia:              float
        :param passes:              Number of passes that will made the isolation
        :type passes:               int
        :param overlap:             How much to overlap the previous pass; in percentage [0.00, 99.99]%
        :type overlap:              float
        :param invert:              If to invert the direction of the resulting isolated geometries
        :type invert:               bool
        :param env_iso_type:        can be either 0 = keep exteriors or 1 = keep interiors or 2 = keep all paths
        :type env_iso_type:         int
        :param negative_dia:        isolate the geometry with a negative value for the tool diameter
        :type negative_dia:         bool
        :param forced_rest:         isolate the polygon even if the interiors can not be isolated
        :type forced_rest:          bool
        :param prog_plot:           kind of plotting: "progressive" or "normal"
        :type prog_plot:            str
        :param prog_plot_handler:   method used to plot shapes if plot_prog is "proggressive"
        :type prog_plot_handler:
        :return:                    Tuple made from list of isolating paths and list of not isolated Polygons
        :rtype:                     tuple
        """

        isolated_geo = []
        not_isolated_geo = []

        work_geo = []

        for idx, geo in enumerate(geometry):
            good_pass_iso = []
            start_idx = idx + 1

            for nr_pass in range(passes):
                iso_offset = tooldia * ((2 * nr_pass + 1) / 2.0) - (nr_pass * overlap * tooldia)
                if negative_dia:
                    iso_offset = -iso_offset

                buf_chek = iso_offset * 2
                check_geo = geo.buffer(buf_chek)

                intersect_flag = False
                # find if current pass for current geo is valid (no intersection with other geos))
                for geo_search_idx in range(idx):
                    if check_geo.intersects(geometry[geo_search_idx]):
                        intersect_flag = True
                        break

                if intersect_flag is False:
                    for geo_search_idx in range(start_idx, len(geometry)):
                        if check_geo.intersects(geometry[geo_search_idx]):
                            intersect_flag = True
                            break

                # if we had an intersection do nothing, else add the geo to the good pass isolation's
                if intersect_flag is False:
                    temp_geo = geo.buffer(iso_offset)
                    # this test is done only for the first pass because this is where is relevant
                    # test if in the first pass, the geo that is isolated has interiors and if it has then test if the
                    # resulting isolated geometry (buffered) number of subgeo is the same as the exterior + interiors
                    # if not it means that the geo interiors most likely could not be isolated with this tool so we
                    # abandon the whole isolation for this geo and add this geo to the not_isolated_geo
                    if nr_pass == 0 and forced_rest is True:
                        if geo.interiors:
                            len_interiors = len(geo.interiors)
                            if len_interiors > 1:
                                total_poly_len = 1 + len_interiors  # one exterior + len_interiors of interiors

                                if isinstance(temp_geo, Polygon):
                                    # calculate the number of subgeos in the buffered geo
                                    temp_geo_len = len([1] + list(temp_geo.interiors))    # one exterior + interiors
                                    if total_poly_len != temp_geo_len:
                                        # some interiors could not be isolated
                                        break
                                else:
                                    try:
                                        temp_geo_len = len(temp_geo)
                                        if total_poly_len != temp_geo_len:
                                            # some interiors could not be isolated
                                            break
                                    except TypeError:
                                        # this means that the buffered geo (temp_geo) is not iterable
                                        # (one geo element only) therefore failure:
                                        # we have more interiors but the resulting geo is only one
                                        break

                    good_pass_iso.append(temp_geo)
                    if prog_plot == 'progressive':
                        prog_plot_handler(temp_geo)

            if good_pass_iso:
                work_geo += good_pass_iso
            else:
                not_isolated_geo.append(geo)

        if invert:
            try:
                pl = []
                for p in work_geo:
                    if p is not None:
                        if isinstance(p, Polygon):
                            pl.append(Polygon(p.exterior.coords[::-1], p.interiors))
                        elif isinstance(p, LinearRing):
                            pl.append(Polygon(p.coords[::-1]))
                work_geo = MultiPolygon(pl)
            except TypeError:
                if isinstance(work_geo, Polygon) and work_geo is not None:
                    work_geo = [Polygon(work_geo.exterior.coords[::-1], work_geo.interiors)]
                elif isinstance(work_geo, LinearRing) and work_geo is not None:
                    work_geo = [Polygon(work_geo.coords[::-1])]
                else:
                    log.debug("ToolIsolation.generate_rest_geometry() Error --> Unexpected Geometry %s" %
                              type(work_geo))
            except Exception as e:
                log.debug("ToolIsolation.generate_rest_geometry() Error --> %s" % str(e))
                return 'fail', 'fail'

        if env_iso_type == 0:  # exterior
            for geo in work_geo:
                isolated_geo.append(geo.exterior)
        elif env_iso_type == 1:  # interiors
            for geo in work_geo:
                isolated_geo += [interior for interior in geo.interiors]
        else:  # exterior + interiors
            for geo in work_geo:
                isolated_geo += [geo.exterior] + [interior for interior in geo.interiors]

        return isolated_geo, not_isolated_geo

    @staticmethod
    def get_selected_interior(poly: Polygon, point: tuple) -> [Polygon, None]:
        try:
            ints = [Polygon(x) for x in poly.interiors]
        except AttributeError:
            return None

        for poly in ints:
            if poly.contains(Point(point)):
                return poly

        return None

    def find_polygon_ignore_interiors(self, point, geoset=None):
        """
        Find an object that object.contains(Point(point)) in
        poly, which can can be iterable, contain iterable of, or
        be itself an implementer of .contains(). Will test the Polygon as it is full with no interiors.

        :param point: See description
        :param geoset: a polygon or list of polygons where to find if the param point is contained
        :return: Polygon containing point or None.
        """

        if geoset is None:
            geoset = self.solid_geometry

        try:  # Iterable
            for sub_geo in geoset:
                p = self.find_polygon_ignore_interiors(point, geoset=sub_geo)
                if p is not None:
                    return p
        except TypeError:  # Non-iterable
            try:  # Implements .contains()
                if isinstance(geoset, LinearRing):
                    geoset = Polygon(geoset)

                poly_ext = Polygon(geoset.exterior)
                if poly_ext.contains(Point(point)):
                    return geoset
            except AttributeError:  # Does not implement .contains()
                return None

        return None


class IsoUI:

    toolName = _("Isolation Tool")

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

        self.title_box = QtWidgets.QHBoxLayout()
        self.tools_box.addLayout(self.title_box)

        # ## Title
        title_label = FCLabel("%s" % self.toolName)
        title_label.setStyleSheet("""
                                QLabel
                                {
                                    font-size: 16px;
                                    font-weight: bold;
                                }
                                """)
        title_label.setToolTip(
            _("Create a Geometry object with\n"
              "toolpaths to cut around polygons.")
        )

        self.title_box.addWidget(title_label)

        # App Level label
        self.level = FCLabel("")
        self.level.setToolTip(
            _(
                "BASIC is suitable for a beginner. Many parameters\n"
                "are hidden from the user in this mode.\n"
                "ADVANCED mode will make available all parameters.\n\n"
                "To change the application LEVEL, go to:\n"
                "Edit -> Preferences -> General and check:\n"
                "'APP. LEVEL' radio button."
            )
        )
        self.level.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.title_box.addWidget(self.level)

        self.obj_combo_label = FCLabel('<b>%s</b>:' % _("GERBER"))
        self.obj_combo_label.setToolTip(
            _("Gerber object for isolation routing.")
        )

        self.tools_box.addWidget(self.obj_combo_label)

        # ################################################
        # ##### The object to be copper cleaned ##########
        # ################################################
        self.object_combo = FCComboBox()
        self.object_combo.setModel(self.app.collection)
        self.object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        # self.object_combo.setCurrentIndex(1)
        self.object_combo.is_last = True

        self.tools_box.addWidget(self.object_combo)

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
              "Isolation routing will start with the tool with the biggest \n"
              "diameter, continuing until there are no more tools.\n"
              "Only tools that create Isolation geometry will still be present\n"
              "in the resulting geometry. This is because with some tools\n"
              "this function will not be able to create routing geometry.")
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

        grid1 = QtWidgets.QGridLayout()
        grid1.setColumnStretch(0, 0)
        grid1.setColumnStretch(1, 1)
        self.tools_box.addLayout(grid1)

        # Tool order
        self.order_label = FCLabel('%s:' % _('Tool order'))
        self.order_label.setToolTip(_("This set the way that the tools in the tools table are used.\n"
                                      "'No' --> means that the used order is the one in the tool table\n"
                                      "'Forward' --> means that the tools will be ordered from small to big\n"
                                      "'Reverse' --> means that the tools will ordered from big to small\n\n"
                                      "WARNING: using rest machining will automatically set the order\n"
                                      "in reverse and disable this control."))

        self.order_radio = RadioSet([{'label': _('No'), 'value': 'no'},
                                     {'label': _('Forward'), 'value': 'fwd'},
                                     {'label': _('Reverse'), 'value': 'rev'}])

        grid1.addWidget(self.order_label, 1, 0)
        grid1.addWidget(self.order_radio, 1, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid1.addWidget(separator_line, 2, 0, 1, 2)

        # #############################################################
        # ############### Tool selection ##############################
        # #############################################################

        self.grid3 = QtWidgets.QGridLayout()
        self.grid3.setColumnStretch(0, 0)
        self.grid3.setColumnStretch(1, 1)
        self.tools_box.addLayout(self.grid3)

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
        self.new_tooldia_entry.setObjectName("i_new_tooldia")

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

        bhlay = QtWidgets.QHBoxLayout()

        self.search_and_add_btn = FCButton(_('Search and Add'))
        self.search_and_add_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/plus16.png'))
        self.search_and_add_btn.setToolTip(
            _("Add a new tool to the Tool Table\n"
              "with the diameter specified above.\n"
              "This is done by a background search\n"
              "in the Tools Database. If nothing is found\n"
              "in the Tools DB then a default tool is added.")
        )
        bhlay.addWidget(self.search_and_add_btn)

        self.addtool_from_db_btn = FCButton(_('Pick from DB'))
        self.addtool_from_db_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/search_db32.png'))
        self.addtool_from_db_btn.setToolTip(
            _("Add a new tool to the Tool Table\n"
              "from the Tools Database.\n"
              "Tools database administration in in:\n"
              "Menu: Options -> Tools Database")
        )
        bhlay.addWidget(self.addtool_from_db_btn)

        self.grid3.addLayout(bhlay, 7, 0, 1, 2)

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

        # Passes
        passlabel = FCLabel('%s:' % _('Passes'))
        passlabel.setToolTip(
            _("Width of the isolation gap in\n"
              "number (integer) of tool widths.")
        )
        self.passes_entry = FCSpinner(callback=self.confirmation_message_int)
        self.passes_entry.set_range(1, 999)
        self.passes_entry.setObjectName("i_passes")

        self.grid3.addWidget(passlabel, 13, 0)
        self.grid3.addWidget(self.passes_entry, 13, 1)

        # Overlap Entry
        overlabel = FCLabel('%s:' % _('Overlap'))
        overlabel.setToolTip(
            _("How much (percentage) of the tool width to overlap each tool pass.")
        )
        self.iso_overlap_entry = FCDoubleSpinner(suffix='%', callback=self.confirmation_message)
        self.iso_overlap_entry.set_precision(self.decimals)
        self.iso_overlap_entry.setWrapping(True)
        self.iso_overlap_entry.set_range(0.0000, 99.9999)
        self.iso_overlap_entry.setSingleStep(0.1)
        self.iso_overlap_entry.setObjectName("i_overlap")

        self.grid3.addWidget(overlabel, 14, 0)
        self.grid3.addWidget(self.iso_overlap_entry, 14, 1)

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
        self.milling_type_radio.setObjectName("i_milling_type")

        self.grid3.addWidget(self.milling_type_label, 15, 0)
        self.grid3.addWidget(self.milling_type_radio, 15, 1)

        # Follow
        self.follow_label = FCLabel('%s:' % _('Follow'))
        self.follow_label.setToolTip(
            _("Generate a 'Follow' geometry.\n"
              "This means that it will cut through\n"
              "the middle of the trace.")
        )

        self.follow_cb = FCCheckBox()
        self.follow_cb.setToolTip(_("Generate a 'Follow' geometry.\n"
                                    "This means that it will cut through\n"
                                    "the middle of the trace."))
        self.follow_cb.setObjectName("i_follow")

        self.grid3.addWidget(self.follow_label, 16, 0)
        self.grid3.addWidget(self.follow_cb, 16, 1)

        # Isolation Type
        self.iso_type_label = FCLabel('%s:' % _('Isolation Type'))
        self.iso_type_label.setToolTip(
            _("Choose how the isolation will be executed:\n"
              "- 'Full' -> complete isolation of polygons\n"
              "- 'Ext' -> will isolate only on the outside\n"
              "- 'Int' -> will isolate only on the inside\n"
              "'Exterior' isolation is almost always possible\n"
              "(with the right tool) but 'Interior'\n"
              "isolation can be done only when there is an opening\n"
              "inside of the polygon (e.g polygon is a 'doughnut' shape).")
        )
        self.iso_type_radio = RadioSet([{'label': _('Full'), 'value': 'full'},
                                        {'label': _('Ext'), 'value': 'ext'},
                                        {'label': _('Int'), 'value': 'int'}])
        self.iso_type_radio.setObjectName("i_iso_type")

        self.grid3.addWidget(self.iso_type_label, 17, 0)
        self.grid3.addWidget(self.iso_type_radio, 17, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.grid3.addWidget(separator_line, 18, 0, 1, 2)

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
        self.rest_cb = FCCheckBox('%s' % _("Rest"))
        self.rest_cb.setObjectName("i_rest")
        self.rest_cb.setToolTip(
            _("If checked, use 'rest machining'.\n"
              "Basically it will process copper outside PCB features,\n"
              "using the biggest tool and continue with the next tools,\n"
              "from bigger to smaller, to process the copper features that\n"
              "could not be processed by previous tool, until there is\n"
              "nothing left to process or there are no more tools.\n\n"
              "If not checked, use the standard algorithm.")
        )

        self.grid3.addWidget(self.rest_cb, 25, 0)

        # Force isolation even if the interiors are not isolated
        self.forced_rest_iso_cb = FCCheckBox(_("Forced Rest"))
        self.forced_rest_iso_cb.setToolTip(
            _("When checked the isolation will be done with the current tool even if\n"
              "interiors of a polygon (holes in the polygon) could not be isolated.\n"
              "Works when 'rest machining' is used.")
        )

        self.grid3.addWidget(self.forced_rest_iso_cb, 25, 1)

        # Combine All Passes
        self.combine_passes_cb = FCCheckBox(label=_('Combine'))
        self.combine_passes_cb.setToolTip(
            _("Combine all passes into one object")
        )
        self.combine_passes_cb.setObjectName("i_combine")

        self.grid3.addWidget(self.combine_passes_cb, 26, 0, 1, 2)

        # Check Tool validity
        self.valid_cb = FCCheckBox(label=_('Check validity'))
        self.valid_cb.setToolTip(
            _("If checked then the tools diameters are verified\n"
              "if they will provide a complete isolation.")
        )
        self.valid_cb.setObjectName("i_check")

        self.grid3.addWidget(self.valid_cb, 28, 0, 1, 2)

        # Exception Areas
        self.except_cb = FCCheckBox(label=_('Except'))
        self.except_cb.setToolTip(_("When the isolation geometry is generated,\n"
                                    "by checking this, the area of the object below\n"
                                    "will be subtracted from the isolation geometry."))
        self.except_cb.setObjectName("i_except")
        self.grid3.addWidget(self.except_cb, 30, 0)

        # Type of object to be excepted
        self.type_excobj_radio = RadioSet([{'label': _("Geometry"), 'value': 'geometry'},
                                           {'label': _("Gerber"), 'value': 'gerber'}])
        self.type_excobj_radio.setToolTip(
            _("Specify the type of object to be excepted from isolation.\n"
              "It can be of type: Gerber or Geometry.\n"
              "What is selected here will dictate the kind\n"
              "of objects that will populate the 'Object' combobox.")
        )

        self.grid3.addWidget(self.type_excobj_radio, 30, 1)

        # The object to be excepted
        self.exc_obj_combo = FCComboBox()
        self.exc_obj_combo.setToolTip(_("Object whose area will be removed from isolation geometry."))

        # set the model for the Area Exception comboboxes
        self.exc_obj_combo.setModel(self.app.collection)
        self.exc_obj_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.exc_obj_combo.is_last = True
        self.exc_obj_combo.obj_type = "gerber"

        self.grid3.addWidget(self.exc_obj_combo, 32, 0, 1, 2)

        self.e_ois = OptionalInputSection(self.except_cb,
                                          [
                                              self.type_excobj_radio,
                                              self.exc_obj_combo
                                          ])

        # Isolation Scope
        self.select_label = FCLabel('%s:' % _("Selection"))
        self.select_label.setToolTip(
            _("Isolation scope. Choose what to isolate:\n"
              "- 'All' -> Isolate all the polygons in the object\n"
              "- 'Area Selection' -> Isolate polygons within a selection area.\n"
              "- 'Polygon Selection' -> Isolate a selection of polygons.\n"
              "- 'Reference Object' - will process the area specified by another object.")
        )
        self.select_combo = FCComboBox2()
        self.select_combo.addItems(
            [_("All"), _("Area Selection"), _("Polygon Selection"), _("Reference Object")]
        )
        self.select_combo.setObjectName("i_selection")

        self.grid3.addWidget(self.select_label, 34, 0)
        self.grid3.addWidget(self.select_combo, 34, 1)

        # Reference Type
        self.reference_combo_type_label = FCLabel('%s:' % _("Type"))

        self.reference_combo_type = FCComboBox2()
        self.reference_combo_type.addItems([_("Gerber"), _("Excellon"), _("Geometry")])

        self.grid3.addWidget(self.reference_combo_type_label, 36, 0)
        self.grid3.addWidget(self.reference_combo_type, 36, 1)

        self.reference_combo = FCComboBox()
        self.reference_combo.setModel(self.app.collection)
        self.reference_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.reference_combo.is_last = True

        self.grid3.addWidget(self.reference_combo, 38, 0, 1, 2)

        self.reference_combo.hide()
        self.reference_combo_type.hide()
        self.reference_combo_type_label.hide()

        # Polygon interiors selection
        self.poly_int_cb = FCCheckBox(_("Interiors"))
        self.poly_int_cb.setToolTip(
            _("When checked the user can select interiors of a polygon.\n"
              "(holes in the polygon).")
        )

        self.grid3.addWidget(self.poly_int_cb, 40, 0)

        self.poly_int_cb.hide()

        # Area Selection shape
        self.area_shape_label = FCLabel('%s:' % _("Shape"))
        self.area_shape_label.setToolTip(
            _("The kind of selection shape used for area selection.")
        )

        self.area_shape_radio = RadioSet([{'label': _("Square"), 'value': 'square'},
                                          {'label': _("Polygon"), 'value': 'polygon'}])

        self.grid3.addWidget(self.area_shape_label, 42, 0)
        self.grid3.addWidget(self.area_shape_radio, 42, 1)

        self.area_shape_label.hide()
        self.area_shape_radio.hide()

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.grid3.addWidget(separator_line, 44, 0, 1, 2)

        self.generate_iso_button = FCButton("%s" % _("Generate Geometry"))
        self.generate_iso_button.setIcon(QtGui.QIcon(self.app.resource_location + '/geometry32.png'))
        self.generate_iso_button.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        self.generate_iso_button.setToolTip(
            _("Create a Geometry object with toolpaths to cut \n"
              "isolation outside, inside or on both sides of the\n"
              "object. For a Gerber object outside means outside\n"
              "of the Gerber feature and inside means inside of\n"
              "the Gerber feature, if possible at all. This means\n"
              "that only if the Gerber feature has openings inside, they\n"
              "will be isolated. If what is wanted is to cut isolation\n"
              "inside the actual Gerber feature, use a negative tool\n"
              "diameter above.")
        )
        self.tools_box.addWidget(self.generate_iso_button)

        self.create_buffer_button = FCButton(_('Buffer Solid Geometry'))
        self.create_buffer_button.setToolTip(
            _("This button is shown only when the Gerber file\n"
              "is loaded without buffering.\n"
              "Clicking this will create the buffered geometry\n"
              "required for isolation.")
        )
        self.tools_box.addWidget(self.create_buffer_button)

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
