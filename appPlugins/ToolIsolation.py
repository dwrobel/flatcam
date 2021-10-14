# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File by:  Marius Adrian Stanciu (c)                      #
# Date:     5/25/2020                                      #
# License:  MIT Licence                                    #
# ##########################################################

from PyQt6 import QtWidgets, QtCore, QtGui

from appTool import AppTool
from appGUI.GUIElements import FCCheckBox, FCDoubleSpinner, RadioSet, FCTable, FCButton, \
    FCComboBox, OptionalInputSection, FCSpinner, FCLabel, FCInputDialogSpinnerButton, FCComboBox2, \
    VerticalScrollArea, FCGridLayout, FCFrame
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
        self.pluginName = self.ui.pluginName
        self.connect_signals_at_init()

        self.init_context_menu()

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
            "tools_mill_tool_shape":     self.ui.tool_shape_combo,
            "tools_iso_passes":         self.ui.passes_entry,
            "tools_iso_pad_passes":     self.ui.pad_passes_entry,
            "tools_iso_overlap":        self.ui.iso_overlap_entry,
            "tools_iso_milling_type":   self.ui.milling_type_radio,
            "tools_iso_combine":        self.ui.combine_passes_cb,
            "tools_iso_isotype":        self.ui.iso_type_radio
        }

        self.name2option = {
            "i_tool_shape":     "tools_mill_tool_shape",
            "i_passes":         "tools_iso_passes",
            "i_pad_passes":     "tools_iso_pad_passes",
            "i_overlap":        "tools_iso_overlap",
            "i_milling_type":   "tools_iso_milling_type",
            "i_combine":        "tools_iso_combine",
            "i_iso_type":       "tools_iso_isotype"
        }

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Alt+I', **kwargs)

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolIsolation()")

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

        # reset those objects on a new run
        self.grb_obj = None
        self.obj_name = ''

        self.build_ui()

        # all the tools are selected by default
        self.ui.tools_table.selectAll()

        self.app.ui.notebook.setTabText(2, _("Isolation"))

    def clear_contex_menu(self):
        self.ui.tools_table.removeContextMenu()

    def init_context_menu(self):
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
            self.on_tool_add_from_db_clicked,
            icon=QtGui.QIcon(self.app.resource_location + "/search_db32.png")
        )
        self.ui.tools_table.addContextMenu(
            _("Delete"),
            lambda: self.on_tool_delete(rows_to_delete=None, all_tools=None),
            icon=QtGui.QIcon(self.app.resource_location + "/trash16.png")
        )

    def connect_signals_at_init(self):
        # #############################################################################
        # ############################ SIGNALS ########################################
        # #############################################################################
        self.ui.level.toggled.connect(self.on_level_changed)

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

        # Select All/None when in Polygon Selection mode
        self.ui.sel_all_btn.clicked.connect(self.on_select_all_polygons)
        self.ui.clear_all_btn.clicked.connect(self.on_deselect_all_polygons)

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
        self.units = self.app.app_units.upper()

        self.clear_ui(self.layout)
        self.ui = IsoUI(layout=self.layout, app=self.app)
        self.pluginName = self.ui.pluginName
        self.connect_signals_at_init()

        self.clear_contex_menu()
        self.init_context_menu()

        self.form_fields = {
            "tools_mill_tool_shape":    self.ui.tool_shape_combo,
            "tools_iso_passes":         self.ui.passes_entry,
            "tools_iso_pad_passes":     self.ui.pad_passes_entry,
            "tools_iso_overlap":        self.ui.iso_overlap_entry,
            "tools_iso_milling_type":   self.ui.milling_type_radio,
            "tools_iso_combine":        self.ui.combine_passes_cb,
            "tools_iso_isotype":        self.ui.iso_type_radio
        }

        # reset the value to prepare for another isolation
        self.safe_tooldia = None

        # try to select in the Gerber combobox the active object
        try:
            selected_obj = self.app.collection.get_active()
            if selected_obj is not None and selected_obj.kind == 'gerber':
                current_name = selected_obj.options['name']
                self.ui.object_combo.set_value(current_name)
            if selected_obj is None and [self.ui.object_combo.itemText(i) for i in range(self.ui.object_combo.count())]:
                self.ui.object_combo.setCurrentIndex(0)
        except Exception as ee:
            self.app.log.debug("ToolIsolation.set_tool_ui() Select Gerber object -> %s" % str(ee))

        # Show/Hide Advanced Options
        app_mode = self.app.defaults["global_app_level"]
        self.change_level(app_mode)

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

        self.ui.iso_order_combo.set_value(self.app.defaults["tools_iso_order"])
        self.ui.tool_shape_combo.set_value(self.app.defaults["tools_iso_tool_shape"])
        self.ui.passes_entry.set_value(self.app.defaults["tools_iso_passes"])
        self.ui.pad_passes_entry.set_value(self.app.defaults["tools_iso_pad_passes"])
        self.ui.iso_overlap_entry.set_value(self.app.defaults["tools_iso_overlap"])
        self.ui.milling_type_radio.set_value(self.app.defaults["tools_iso_milling_type"])
        self.ui.combine_passes_cb.set_value(self.app.defaults["tools_iso_combine_passes"])
        self.ui.valid_cb.set_value(self.app.defaults["tools_iso_check_valid"])
        self.ui.area_shape_radio.set_value(self.app.defaults["tools_iso_area_shape"])
        self.ui.poly_int_cb.set_value(self.app.defaults["tools_iso_poly_ints"])
        self.ui.forced_rest_iso_cb.set_value(self.app.defaults["tools_iso_force"])

        self.ui.new_tooldia_entry.set_value(self.app.defaults["tools_iso_newdia"])

        # loaded_obj = self.app.collection.get_by_name(self.ui.object_combo.get_value())
        # if loaded_obj:
        #     outname = loaded_obj.options['name']
        # else:
        #     outname = ''

        # init the working variables
        self.default_data.clear()
        kind = 'geometry'
        for option in self.app.options:
            if option.find(kind + "_") == 0:
                oname = option[len(kind) + 1:]
                self.default_data[oname] = self.app.options[option]

            if option.find('tools_') == 0:
                self.default_data[option] = self.app.options[option]

        # self.default_data.update({
        #     "name":                     outname + '_iso',
        #     "plot":                     self.app.defaults["geometry_plot"],
        #     "cutz":                     float(self.app.defaults["tools_iso_tool_cutz"]),
        #     "vtipdia":                  float(self.app.defaults["tools_iso_tool_vtipdia"]),
        #     "vtipangle":                float(self.app.defaults["tools_iso_tool_vtipangle"]),
        #     "travelz":                  self.app.defaults["geometry_travelz"],
        #     "feedrate":                 self.app.defaults["geometry_feedrate"],
        #     "feedrate_z":               self.app.defaults["geometry_feedrate_z"],
        #     "feedrate_rapid":           self.app.defaults["geometry_feedrate_rapid"],
        #
        #     "multidepth":               self.app.defaults["geometry_multidepth"],
        #     "ppname_g":                 self.app.defaults["geometry_ppname_g"],
        #     "depthperpass":             self.app.defaults["geometry_depthperpass"],
        #     "extracut":                 self.app.defaults["geometry_extracut"],
        #     "extracut_length":          self.app.defaults["geometry_extracut_length"],
        #     "toolchange":               self.app.defaults["geometry_toolchange"],
        #     "toolchangez":              self.app.defaults["geometry_toolchangez"],
        #     "endz":                     self.app.defaults["geometry_endz"],
        #     "endxy":                    self.app.defaults["geometry_endxy"],
        #
        #     "dwell":                    self.app.defaults["geometry_dwell"],
        #     "dwelltime":                self.app.defaults["geometry_dwelltime"],
        #     "spindlespeed":             self.app.defaults["geometry_spindlespeed"],
        #     "spindledir":               self.app.defaults["geometry_spindledir"],
        #
        #     "optimization_type":        self.app.defaults["geometry_optimization_type"],
        #     "search_time":              self.app.defaults["geometry_search_time"],
        #     "toolchangexy":             self.app.defaults["geometry_toolchangexy"],
        #     "startz":                   self.app.defaults["geometry_startz"],
        #
        #     "area_exclusion":           self.app.defaults["geometry_area_exclusion"],
        #     "area_shape":               self.app.defaults["geometry_area_shape"],
        #     "area_strategy":            self.app.defaults["geometry_area_strategy"],
        #     "area_overz":               float(self.app.defaults["geometry_area_overz"]),
        # })

        try:
            dias = [float(self.app.defaults["tools_iso_tooldia"])]
        except (ValueError, TypeError):
            if isinstance(self.app.defaults["tools_iso_tooldia"], str):
                dias = [float(eval(dia)) for dia in self.app.defaults["tools_iso_tooldia"].split(",") if dia != '']
            else:
                dias = self.app.defaults["tools_iso_tooldia"]

        if not dias:
            log.error("At least one tool diameter needed. Verify in Edit -> Preferences -> Plugins -> Isolation Tools.")
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

    def change_level(self, level):
        """

        :param level:   application level: either 'b' or 'a'
        :type level:    str
        :return:
        """

        if level == 'a':
            self.ui.level.setChecked(True)
        else:
            self.ui.level.setChecked(False)
        self.on_level_changed(self.ui.level.isChecked())

    def on_level_changed(self, checked):
        if not checked:
            self.ui.level.setText('%s' % _('Beginner'))
            self.ui.level.setStyleSheet("""
                                        QToolButton
                                        {
                                            color: green;
                                        }
                                        """)

            # Add Tool section
            self.ui.add_tool_frame.hide()

            # Tool parameters section
            if self.iso_tools:
                for tool in self.iso_tools:
                    tool_data = self.iso_tools[tool]['data']

                    tool_data['tools_iso_isotype'] = 'full'

            self.ui.milling_type_label.hide()
            self.ui.milling_type_radio.hide()

            self.ui.iso_type_label.hide()
            self.ui.iso_type_radio.set_value('full')
            self.ui.iso_type_radio.hide()

            # All param section
            self.ui.apply_param_to_all.hide()

            # Common Parameters
            self.ui.rest_cb.set_value(False)
            self.ui.rest_cb.hide()
            self.ui.forced_rest_iso_cb.hide()

            self.ui.except_cb.set_value(False)
            self.ui.except_cb.hide()

            self.ui.type_excobj_radio.hide()
            self.ui.exc_obj_combo.hide()

            self.ui.select_label.hide()
            self.ui.select_combo.hide()

            # make sure that on hide is selected an option that does not display child widgets
            self.ui.select_combo.set_value(0)

            self.ui.reference_combo_type_label.hide()
            self.ui.reference_combo_type.hide()
            self.ui.reference_combo.hide()
            self.ui.poly_int_cb.hide()
            self.ui.sel_all_btn.hide()
            self.ui.clear_all_btn.hide()
            self.ui.area_shape_label.hide()
            self.ui.area_shape_radio.hide()

            # Context Menu section
            self.ui.tools_table.removeContextMenu()
        else:
            self.ui.level.setText('%s' % _('Advanced'))
            self.ui.level.setStyleSheet("""
                                        QToolButton
                                        {
                                            color: red;
                                        }
                                        """)

            # Add Tool section
            self.ui.add_tool_frame.show()

            # Tool parameters section
            app_defaults = self.app.defaults
            if self.iso_tools:
                for tool in self.iso_tools:
                    tool_data = self.iso_tools[tool]['data']
                    tool_data['tools_iso_isotype'] = app_defaults['tools_iso_isotype']
                    tool_data['tools_iso_rest'] = app_defaults['tools_iso_rest']
                    tool_data['tools_iso_isoexcept'] = app_defaults['tools_iso_isoexcept']

            self.ui.milling_type_label.show()
            self.ui.milling_type_radio.show()

            self.ui.iso_type_label.show()
            self.ui.iso_type_radio.set_value(app_defaults['tools_iso_isotype'])
            self.ui.iso_type_radio.show()

            # All param section
            self.ui.apply_param_to_all.show()

            # Common Parameters
            self.ui.rest_cb.set_value(app_defaults['tools_iso_rest'])
            self.ui.rest_cb.show()
            self.ui.forced_rest_iso_cb.show()

            self.ui.except_cb.set_value(app_defaults['tools_iso_isoexcept'])
            self.ui.except_cb.show()

            self.ui.type_excobj_radio.show()
            self.ui.exc_obj_combo.show()

            self.ui.select_label.show()
            self.ui.select_combo.show()

            # Context Menu section
            self.ui.tools_table.setupContextMenu()

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
        units = self.app.app_units.upper()
        self.units = units

        self.sort_iso_tools()

        n = len(self.iso_tools)
        self.ui.tools_table.setRowCount(n)
        tool_id = 0

        for tooluid_key, tooluid_value in self.iso_tools.items():
            tool_id += 1

            # Tool name/id
            id_ = QtWidgets.QTableWidgetItem('%d' % int(tool_id))
            id_.setFlags(QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)
            row_no = tool_id - 1
            self.ui.tools_table.setItem(row_no, 0, id_)

            # Diameter
            truncated_dia = self.app.dec_format(tooluid_value['tooldia'], self.decimals)
            dia = QtWidgets.QTableWidgetItem(str(truncated_dia))
            dia.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
            self.ui.tools_table.setItem(row_no, 1, dia)

            # Tool unique ID
            # REMEMBER: THIS COLUMN IS HIDDEN
            tool_uid_item = QtWidgets.QTableWidgetItem(str(int(tooluid_key)))
            self.ui.tools_table.setItem(row_no, 3, tool_uid_item)

        # make the diameter column editable
        for row in range(tool_id):
            self.ui.tools_table.item(row, 1).setFlags(
                QtCore.Qt.ItemFlag.ItemIsEditable |
                QtCore.Qt.ItemFlag.ItemIsSelectable |
                QtCore.Qt.ItemFlag.ItemIsEnabled)

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

        # Tool Parameters
        for opt in self.form_fields:
            current_widget = self.form_fields[opt]
            if isinstance(current_widget, FCCheckBox):
                current_widget.stateChanged.connect(self.form_to_storage)
            if isinstance(current_widget, RadioSet):
                current_widget.activated_custom.connect(self.form_to_storage)
            elif isinstance(current_widget, FCDoubleSpinner) or isinstance(current_widget, FCSpinner):
                current_widget.returnPressed.connect(self.form_to_storage)
            elif isinstance(current_widget, (FCComboBox, FCComboBox2)):
                current_widget.currentIndexChanged.connect(self.form_to_storage)

        self.ui.rest_cb.stateChanged.connect(self.on_rest_machining_check)
        self.ui.iso_order_combo.currentIndexChanged.connect(self.on_order_changed)

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
            elif isinstance(current_widget, (FCComboBox, FCComboBox2)):
                try:
                    current_widget.currentIndexChanged.disconnect(self.form_to_storage)
                except (TypeError, ValueError):
                    pass

        try:
            self.ui.rest_cb.stateChanged.disconnect()
        except (TypeError, ValueError):
            pass
        try:
            self.ui.iso_order_combo.currentIndexChanged.disconnect()
        except (TypeError, ValueError):
            pass

    def sort_iso_tools(self):
        order = self.ui.iso_order_combo.get_value()
        if order == 0:  # "Default"
            return

        # sort the tools dictionary having the 'tooldia' as sorting key
        new_tools_list = []
        if order == 1:  # "Forward"
            new_tools_list = deepcopy(sorted(self.iso_tools.items(), key=lambda x: x[1]['tooldia'], reverse=False))
        elif order == 2:    # "Reverse"
            new_tools_list = deepcopy(sorted(self.iso_tools.items(), key=lambda x: x[1]['tooldia'], reverse=True))

        # clear the tools dictionary
        self.iso_tools.clear()

        # recreate the tools dictionary in a ordered fashion
        new_toolid = 0
        for tool in new_tools_list:
            new_toolid += 1
            self.iso_tools[new_toolid] = tool[1]

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
                log.error("Tool missing. Add a tool in the Tool Table. %s" % str(e))
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
                    log.error("ToolIsolation ---> update_ui() " + str(e))
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
                        log.error("ToolIsolation.storage_to_form() --> %s" % str(e))
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
            self.ui.sel_all_btn.hide()
            self.ui.clear_all_btn.hide()

            # disable rest-machining for area painting
            self.ui.rest_cb.setDisabled(False)
        elif val == 1:  # Area Selection
            self.ui.reference_combo.hide()
            self.ui.reference_combo_type.hide()
            self.ui.reference_combo_type_label.hide()
            self.ui.area_shape_label.show()
            self.ui.area_shape_radio.show()

            self.ui.poly_int_cb.hide()
            self.ui.sel_all_btn.hide()
            self.ui.clear_all_btn.hide()

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
            self.ui.sel_all_btn.show()
            self.ui.clear_all_btn.show()

        else:   # Reference Object
            self.ui.reference_combo.show()
            self.ui.reference_combo_type.show()
            self.ui.reference_combo_type_label.show()
            self.ui.area_shape_label.hide()
            self.ui.area_shape_radio.hide()

            self.ui.poly_int_cb.hide()
            self.ui.sel_all_btn.hide()
            self.ui.clear_all_btn.hide()

            # disable rest-machining for area painting
            self.ui.rest_cb.setDisabled(False)

    def on_order_changed(self):
        self.build_ui()

    def on_rest_machining_check(self, state):
        if state:
            self.ui.iso_order_combo.set_value(2)    # "Reverse"
            self.ui.order_label.setDisabled(True)
            self.ui.iso_order_combo.setDisabled(True)

            self.old_combine_state = self.ui.combine_passes_cb.get_value()
            self.ui.combine_passes_cb.set_value(True)
            self.ui.combine_passes_cb.setDisabled(True)

            self.ui.forced_rest_iso_cb.setDisabled(False)
        else:
            self.ui.order_label.setDisabled(False)
            self.ui.iso_order_combo.setDisabled(False)

            self.ui.combine_passes_cb.set_value(self.old_combine_state)
            self.ui.combine_passes_cb.setDisabled(False)

            self.ui.forced_rest_iso_cb.setDisabled(True)

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

        if isinstance(total_geo, Polygon):
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
        min_dist -= 10**-decimals  # make sure that this works for isolation case

        return msg, min_dist

    # multiprocessing variant
    def find_safe_tooldia_multiprocessing(self):
        self.app.inform.emit(_("Checking tools for validity."))
        self.units = self.app.app_units.upper()

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

                ap_storage = fcobj.tools

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
                    log.error(str(ee))
                    return

        self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})

    def find_safe_tooldia_worker(self):
        self.app.inform.emit(_("Checking tools for validity."))
        self.units = self.app.app_units.upper()

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

                    for ap in list(fcobj.tools.keys()):
                        if 'geometry' in fcobj.tools[ap]:
                            for geo_el in fcobj.tools[ap]['geometry']:
                                if self.app.abort_flag:
                                    # graceful abort requested by the user
                                    raise grace

                                if 'solid' in geo_el and geo_el['solid'] is not None and geo_el['solid'].is_valid:
                                    total_geo.append(geo_el['solid'])

                    total_geo = MultiPolygon(total_geo)
                    total_geo = total_geo.buffer(0)

                    if isinstance(total_geo, MultiPolygon):
                        geo_len = len(total_geo.geoms)
                        geo_len = (geo_len * (geo_len - 1)) / 2
                    elif isinstance(total_geo, Polygon):
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
                    log.error(str(ee))
                    return

        self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})

    def on_tool_add(self, custom_dia=None):
        self.blockSignals(True)
        self.ui_disconnect()

        filename = self.app.tools_database_path()

        tool_dia = custom_dia if custom_dia is not None else self.ui.new_tooldia_entry.get_value()
        # construct a list of all 'tooluid' in the self.iso_tools
        tool_uid_list = [int(tooluid_key) for tooluid_key in self.iso_tools]

        # find maximum from the temp_uid, add 1 and this is the new 'tooluid'
        max_uid = 0 if not tool_uid_list else max(tool_uid_list)
        tooluid = int(max_uid) + 1

        new_tools_dict = deepcopy(self.default_data)
        updated_tooldia = None

        # determine the new tool diameter
        if tool_dia is None or tool_dia == 0:
            self.build_ui()
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Please enter a tool diameter with non-zero value, "
                                                          "in Float format."))
            self.blockSignals(False)
            self.ui_connect()
            return
        truncated_tooldia = self.app.dec_format(tool_dia, self.decimals)

        # if new tool diameter already in the Tool List then abort
        # if truncated_tooldia in tool_dias:
        #     self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled. Tool already in Tool Table."))
        #     self.blockSignals(False)
        #     return

        # load the database tools from the file
        try:
            with open(filename) as f:
                tools = f.read()
        except IOError:
            self.app.log.error("Could not load tools DB file.")
            self.app.inform.emit('[ERROR] %s' % _("Could not load Tools DB file."))
            self.blockSignals(False)
            self.ui_connect()
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
            self.ui_connect()
            self.on_tool_default_add(dia=tool_dia)
            return

        tool_found = 0

        # look in database tools
        for db_tool, db_tool_val in tools_db_dict.items():
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
                    if d.find('tools_iso_') == 0:
                        new_tools_dict[d] = db_tool_val['data'][d]
                    elif d.find('tools_') == 0:
                        # don't need data for other App Tools; this tests after 'tools_iso_'
                        continue
                    else:
                        new_tools_dict[d] = db_tool_val['data'][d]
            # search for a tool that has a tolerance that the tool fits in
            elif high_limit >= truncated_tooldia >= low_limit:
                tool_found += 1
                updated_tooldia = db_tooldia
                for d in db_tool_val['data']:
                    if d.find('tools_iso_') == 0:
                        new_tools_dict[d] = db_tool_val['data'][d]
                    elif d.find('tools_') == 0:
                        # don't need data for other App Tools; this tests after 'tools_iso_'
                        continue
                    else:
                        new_tools_dict[d] = db_tool_val['data'][d]

        # test we found a suitable tool in Tools Database or if multiple ones
        if tool_found == 0:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Tool not in Tools Database. Adding a default tool."))
            self.on_tool_default_add(dia=tool_dia)
            self.blockSignals(False)
            self.ui_connect()
            return

        if tool_found > 1:
            self.app.inform.emit(
                '[WARNING_NOTCL] %s' % _("Cancelled.\n"
                                         "Multiple tools for one tool diameter found in Tools Database."))
            self.blockSignals(False)
            self.ui_connect()
            return

        # if new tool diameter found in Tools Database already in the Tool List then abort
        # if updated_tooldia is not None and updated_tooldia in tool_dias:
        #     self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled. Tool already in Tool Table."))
        #     self.blockSignals(False)
        #     return

        new_tdia = deepcopy(updated_tooldia) if updated_tooldia is not None else deepcopy(truncated_tooldia)
        self.iso_tools.update({
            tooluid: {
                'tooldia':          new_tdia,
                'data':             deepcopy(new_tools_dict),
                'solid_geometry':   []
            }
        })
        self.blockSignals(False)
        self.ui_connect()
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
        # if truncated_tooldia in tool_dias:
        #     if muted is None:
        #         self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled. Tool already in Tool Table."))
        #     # self.ui.tools_table.itemChanged.connect(self.on_tool_edit)
        #     self.blockSignals(False)
        #     return

        # print("before", self.iso_tools)
        self.iso_tools.update({
            int(self.tooluid): {
                'tooldia':          truncated_tooldia,
                'data':             deepcopy(self.default_data),
                'solid_geometry':   []
            }
        })
        # print("after", self.iso_tools)

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
            log.error(str(e))

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

        def worker_task(iso_class):
            with iso_class.app.proc_container.new('%s ...' % _("Isolating")):
                iso_class.isolate_handler(iso_class.grb_obj)

        self.app.worker_task.emit({'fcn': worker_task, 'params': [self]})

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
                    self.iso_tools[tool_iso][key]["tools_mill_job_type"] = 2    # _("Isolation")
                    self.iso_tools[tool_iso][key]["tools_mill_tool_shape"] = self.ui.tool_shape_combo.get_value()

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

                work_geo = geometry
                if work_geo is None:
                    # we do isolation over all the geometry of the Gerber object
                    # because it is already fused together
                    work_geo = isolated_obj.solid_geometry

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

                tool_dia = tools_storage[tool]['tooldia']
                for i in range(passes):
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
                                                     nr_passes=i, prog_plot=prog_plot)
                    if iso_geo == 'fail':
                        self.app.inform.emit('[ERROR_NOTCL] %s' % _("Isolation geometry could not be generated."))
                        continue

                    # Extra Pads isolations
                    pad_geo = []
                    extra_passes = self.ui.pad_passes_entry.get_value()
                    if extra_passes > 0:
                        solid_geo_union = unary_union(iso_geo)
                        extra_geo = []
                        for apid in self.grb_obj.tools:
                            for t_geo_dict in self.grb_obj.tools[apid]['geometry']:
                                if isinstance(t_geo_dict['follow'], Point):
                                    extra_geo.append(t_geo_dict['solid'])

                        for nr_pass in range(i, extra_passes + i):
                            pad_pass_geo = []
                            for geo in extra_geo:
                                iso_offset = tool_dia * ((2 * nr_pass + 1) / 2.0000001) - (
                                            nr_pass * overlap * tool_dia)
                                if negative_dia:
                                    iso_offset = -iso_offset
                                pad_pass_geo.append(
                                    geo.buffer(iso_offset, int(self.app.defaults["gerber_circle_steps"])))
                            pad_geo.append(unary_union(pad_pass_geo).difference(solid_geo_union))

                    total_geo = []
                    try:
                        for p in iso_geo.geoms:
                            total_geo.append(p)
                    except (AttributeError, TypeError):
                        total_geo.append(iso_geo)

                    for p in pad_geo:
                        total_geo.append(p)
                    iso_geo = total_geo

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
                        geo_obj.options["tools_mill_tooldia"] = str(tool_dia)
                        tool_data["tools_mill_tooldia"] = float(tool_dia)

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

        order = self.ui.iso_order_combo.get_value()
        if order == 1:  # "Forward"
            sorted_tools.sort(reverse=False)
        elif order == 2:    # "Reverse"
            sorted_tools.sort(reverse=True)
        else:
            pass

        # decide to use "progressive" or "normal" plotting
        prog_plot = self.app.defaults["tools_iso_plotting"]

        for sorted_tool in sorted_tools:
            for tool in tools_storage:
                if float('%.*f' % (self.decimals, tools_storage[tool]['tooldia'])) == sorted_tool:

                    tool_dia = tools_storage[tool]['tooldia']
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
                            'data':             tool_data,
                            'solid_geometry':   deepcopy(new_solid_geo)
                        }
                    })
                    tools_storage[tool]['data']['tools_mill_tooldia'] = float(tool_dia)
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
            geo_obj.options["tools_mill_tooldia"] = str(tool_dia)

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
                for __ in tools_storage.keys():
                    # passes_no = float(tools_storage[ky]['data']['tools_iso_passes'])
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
            tool_has_offset = tools_storage[tool]['data']['tools_mill_offset_type']
            tool_offset_value = tools_storage[tool]['data']['tools_mill_offset_value']
            tool_type = tools_storage[tool]['data']['tools_mill_tool_shape']
            tool_data = tools_storage[tool]['data']

            work_geo = geometry
            if work_geo is None:
                work_geo = iso_obj.solid_geometry

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
                                                 nr_passes=nr_pass, prog_plot=prog_plot)
                if iso_geo == 'fail':
                    self.app.inform.emit('[ERROR_NOTCL] %s' % _("Isolation geometry could not be generated."))
                    continue

                if isinstance(iso_geo, (MultiLineString, MultiPolygon)):
                    for geo in iso_geo.geoms:
                        solid_geo.append(geo)
                else:
                    solid_geo.append(iso_geo)

            # Extra Pads isolations
            pad_geo = []
            extra_passes = self.ui.pad_passes_entry.get_value()
            if extra_passes > 0:
                solid_geo_union = unary_union(solid_geo)
                extra_geo = []
                for apid in self.grb_obj.tools:
                    for t_geo_dict in self.grb_obj.tools[apid]['geometry']:
                        if isinstance(t_geo_dict['follow'], Point):
                            extra_geo.append(t_geo_dict['solid'])

                for nr_pass in range(passes, extra_passes + passes):
                    pad_pass_geo = []
                    for geo in extra_geo:
                        iso_offset = tool_dia * ((2 * nr_pass + 1) / 2.0000001) - (nr_pass * overlap * tool_dia)
                        if negative_dia:
                            iso_offset = -iso_offset
                        pad_pass_geo.append(geo.buffer(iso_offset, int(self.app.defaults["gerber_circle_steps"])))
                    pad_geo.append(unary_union(pad_pass_geo).difference(solid_geo_union))

            solid_geo += pad_geo

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
                    'tool_type':        tool_type,
                    'data':             tool_data,
                    'solid_geometry':   deepcopy(new_solid_geo)
                }
            })
            tools_storage[tool]['data']['tools_mill_tooldia'] = float(tool_dia)

            total_solid_geometry += new_solid_geo

        # clean the progressive plotted shapes if it was used
        if prog_plot == 'progressive':
            self.temp_shapes.clear(update=True)

        # remove tools without geometry
        for tool, tool_dict in list(tools_storage.items()):
            if not tool_dict['solid_geometry']:
                tools_storage.pop(tool, None)

        def iso_init(geo_obj, app_obj):
            geo_obj.options["tools_mill_tooldia"] = str(tool_dia)

            geo_obj.tools = dict(tools_storage)
            geo_obj.solid_geometry = total_solid_geometry
            # even if combine is checked, one pass is still single-geo

            if len(tools_storage) > 1:
                geo_obj.multigeo = True
            else:
                # passes_no = 1
                for __ in tools_storage.keys():
                    # passes_no = float(tools_storage[ky]['data']['tools_iso_passes'])
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

    def on_select_all_polygons(self):
        self.app.log.debug("ToolIsolation.on_select_all_polygons()")

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

        try:
            for poly in self.grb_obj.solid_geometry:
                shape_id = self.app.tool_shapes.add(tolerance=self.drawing_tolerance, layer=0, shape=poly,
                                                    color=self.app.defaults['global_sel_draw_color'] + 'AF',
                                                    face_color=self.app.defaults['global_sel_draw_color'] + 'AF',
                                                    visible=True)
                self.poly_dict[shape_id] = poly
        except TypeError:
            poly = self.grb_obj.solid_geometry
            shape_id = self.app.tool_shapes.add(tolerance=self.drawing_tolerance, layer=0, shape=poly,
                                                color=self.app.defaults['global_sel_draw_color'] + 'AF',
                                                face_color=self.app.defaults['global_sel_draw_color'] + 'AF',
                                                visible=True)
            self.poly_dict[shape_id] = poly

        self.app.tool_shapes.redraw()

    def on_deselect_all_polygons(self):
        self.app.log.debug("ToolIsolation.on_deselect_all_polygons()")

        self.poly_dict.clear()
        self.app.tool_shapes.clear(update=True)

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
        # self.app.ui.position_label.setText("&nbsp;<b>X</b>: %.4f&nbsp;&nbsp;   "
        #                                    "<b>Y</b>: %.4f&nbsp;" % (curr_pos[0], curr_pos[1]))
        # self.app.ui.rel_position_label.setText("<b>Dx</b>: %.4f&nbsp;&nbsp;  <b>Dy</b>: "
        #                                        "%.4f&nbsp;&nbsp;&nbsp;&nbsp;" % (self.app.dx, self.app.dy))
        self.app.ui.update_location_labels(self.app.dx, self.app.dy, curr_pos[0], curr_pos[1])

        # units = self.app.app_units.lower()
        # self.app.plotcanvas.text_hud.text = \
        #     'Dx:\t{:<.4f} [{:s}]\nDy:\t{:<.4f} [{:s}]\n\nX:  \t{:<.4f} [{:s}]\nY:  \t{:<.4f} [{:s}]'.format(
        #         self.app.dx, units, self.app.dy, units, curr_pos[0], units, curr_pos[1], units)
        self.app.plotcanvas.on_update_text_hud(self.app.dx, self.app.dy, curr_pos[0], curr_pos[1])

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
                    # modifiers = QtCore.Qt.KeyboardModifier.ControlModifier
                    pass
                elif mod.lower() == 'alt':
                    # modifiers = QtCore.Qt.KeyboardModifier.AltModifier
                    pass
                elif mod.lower() == 'shift':
                    # modifiers = QtCore.Qt.KeyboardModifier.
                    pass
                else:
                    # modifiers = QtCore.Qt.KeyboardModifier.NoModifier
                    pass
                key = QtGui.QKeySequence(key_text)

        # events from Vispy are of type KeyEvent
        else:
            key = event.key

        if key == QtCore.Qt.Key.Key_Escape or key == 'Escape':

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
        self.units = self.app.app_units.upper()

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
        # if truncated_tooldia in tool_dias:
        #     self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled. Tool already in Tool Table."))
        #     self.ui_connect()
        #     return 'fail'

        self.iso_tools.update({
            tooluid: {
                'tooldia':          truncated_tooldia,
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

        return True
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

    def generate_envelope(self, offset, invert, geometry=None, env_iso_type=2, nr_passes=0,
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
        :param geometry:        Shapely Geometry for which to generate envelope
        :type geometry:
        :param env_iso_type:    type of isolation, can be 0 = exteriors or 1 = interiors or 2 = both (complete)
        :type env_iso_type:     int
        :param nr_passes:       Number of passes
        :type nr_passes:        int
        :param prog_plot:       Type of plotting: "normal" or "progressive"
        :type prog_plot:        str
        :return:                The buffered geometry
        :rtype:                 MultiPolygon or Polygon
        """

        try:
            geom_shp = self.grb_obj.isolation_geometry(offset, geometry=geometry, iso_type=env_iso_type,
                                                       passes=nr_passes, prog_plot=prog_plot)
        except Exception as e:
            log.error('ToolIsolation.generate_envelope() --> %s' % str(e))
            return 'fail'

        if isinstance(geom_shp, (MultiPolygon, MultiLineString)):
            geom = geom_shp.geoms
        else:
            geom = geom_shp

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
                log.error("ToolIsolation.generate_envelope() Error --> %s" % str(e))
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

        work_geo_shp = work_geo.geoms if isinstance(work_geo, MultiPolygon) else work_geo
        if invert:
            try:
                pl = []
                for p in work_geo_shp:
                    if p is not None:
                        if isinstance(p, Polygon):
                            pl.append(Polygon(p.exterior.coords[::-1], p.interiors))
                        elif isinstance(p, LinearRing):
                            pl.append(Polygon(p.coords[::-1]))
                work_geo_shp = MultiPolygon(pl)
            except TypeError:
                if isinstance(work_geo_shp, Polygon) and work_geo_shp is not None:
                    work_geo_shp = [Polygon(work_geo_shp.exterior.coords[::-1], work_geo_shp.interiors)]
                elif isinstance(work_geo_shp, LinearRing) and work_geo_shp is not None:
                    work_geo_shp = [Polygon(work_geo_shp.coords[::-1])]
                else:
                    log.debug("ToolIsolation.generate_rest_geometry() Error --> Unexpected Geometry %s" %
                              type(work_geo))
            except Exception as e:
                log.error("ToolIsolation.generate_rest_geometry() Error --> %s" % str(e))
                return 'fail', 'fail'

        actual_geo = work_geo_shp.geoms if isinstance(work_geo, MultiPolygon) else work_geo_shp
        if env_iso_type == 0:  # exterior
            for geo in actual_geo:
                isolated_geo.append(geo.exterior)
        elif env_iso_type == 1:  # interiors
            for geo in actual_geo:
                isolated_geo += [interior for interior in geo.interiors]
        else:  # exterior + interiors
            for geo in actual_geo:
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

    pluginName = _("Isolation")

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
        title_label = FCLabel("%s" % self.pluginName)
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
        self.level = QtWidgets.QToolButton()
        self.level.setToolTip(
            _(
                "Beginner Mode - many parameters are hidden.\n"
                "Advanced Mode - full control.\n"
                "Permanent change is done in 'Preferences' menu."
            )
        )
        self.level.setCheckable(True)
        self.title_box.addWidget(self.level)

        # #############################################################################################################
        # Source Object for Isolation
        # #############################################################################################################
        self.obj_combo_label = FCLabel('<span style="color:darkorange;"><b>%s</b></span>' % _("Source Object"))
        self.obj_combo_label.setToolTip(_("Gerber object for isolation routing."))
        self.tools_box.addWidget(self.obj_combo_label)

        # #############################################################################################################
        # ################################ The object to be isolated ##################################################
        # #############################################################################################################
        self.object_combo = FCComboBox()
        self.object_combo.setModel(self.app.collection)
        self.object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        # self.object_combo.setCurrentIndex(1)
        self.object_combo.is_last = True

        self.tools_box.addWidget(self.object_combo)

        # separator_line = QtWidgets.QFrame()
        # separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        # separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        # self.tools_box.addWidget(separator_line)

        # #############################################################################################################
        # Tool Table Frame
        # #############################################################################################################
        self.tools_table_label = FCLabel('<span style="color:green;"><b>%s</b></span>' % _('Tools Table'))
        self.tools_table_label.setToolTip(
            _("Tools pool from which the algorithm\n"
              "will pick the ones used for copper clearing.")
        )
        self.tools_box.addWidget(self.tools_table_label)

        tt_frame = FCFrame()
        self.tools_box.addWidget(tt_frame)

        # Grid Layout
        tool_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        tt_frame.setLayout(tool_grid)

        self.tools_table = FCTable(drag_drop=True)
        tool_grid.addWidget(self.tools_table, 0, 0, 1, 2)

        self.tools_table.setColumnCount(4)
        # 3rd column is reserved (and hidden) for the tool ID
        self.tools_table.setHorizontalHeaderLabels(['#', _('Diameter'), '', ''])
        self.tools_table.setColumnHidden(2, True)
        self.tools_table.setColumnHidden(3, True)
        self.tools_table.setSortingEnabled(False)
        # self.tools_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)

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

        # Tool order
        self.order_label = FCLabel('%s:' % _('Tool order'))
        self.order_label.setToolTip(_("This set the way that the tools in the tools table are used.\n"
                                      "'Default' --> means that the used order is the one in the tool table\n"
                                      "'Forward' --> means that the tools will be ordered from small to big\n"
                                      "'Reverse' --> means that the tools will ordered from big to small\n\n"
                                      "WARNING: using rest machining will automatically set the order\n"
                                      "in reverse and disable this control."))

        self.iso_order_combo = FCComboBox2()
        self.iso_order_combo.addItems([_('Default'), _('Forward'), _('Reverse')])

        tool_grid.addWidget(self.order_label, 2, 0)
        tool_grid.addWidget(self.iso_order_combo, 2, 1)

        # #############################################################
        # ############### Tool adding #################################
        # #############################################################
        self.add_tool_frame = QtWidgets.QFrame()
        self.add_tool_frame.setContentsMargins(0, 0, 0, 0)
        tool_grid.addWidget(self.add_tool_frame, 4, 0, 1, 2)

        new_tool_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        new_tool_grid.setContentsMargins(0, 0, 0, 0)
        self.add_tool_frame.setLayout(new_tool_grid)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        new_tool_grid.addWidget(separator_line, 0, 0, 1, 3)

        self.tool_sel_label = FCLabel('<b>%s</b>' % _('Add from DB'))
        new_tool_grid.addWidget(self.tool_sel_label, 2, 0, 1, 3)

        # ### Tool Diameter ####
        self.new_tooldia_lbl = FCLabel('%s: ' % _('Tool Dia'))
        self.new_tooldia_lbl.setToolTip(
            _("Diameter for the new tool")
        )
        new_tool_grid.addWidget(self.new_tooldia_lbl, 4, 0)

        # Tool diameter entry
        self.new_tooldia_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.new_tooldia_entry.set_precision(self.decimals)
        self.new_tooldia_entry.set_range(-10000.0000, 10000.0000)
        self.new_tooldia_entry.setObjectName("i_new_tooldia")

        # Find Optimal Tooldia
        self.find_optimal_button = QtWidgets.QToolButton()
        self.find_optimal_button.setText(_('Optimal'))
        self.find_optimal_button.setIcon(QtGui.QIcon(self.app.resource_location + '/open_excellon32.png'))
        self.find_optimal_button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.find_optimal_button.setToolTip(
            _("Find a tool diameter that is guaranteed\n"
              "to do a complete isolation.")
        )

        new_tool_grid.addWidget(self.new_tooldia_entry, 4, 1)
        new_tool_grid.addWidget(self.find_optimal_button, 4, 2)

        # #############################################################################################################
        # ################################    Button Grid   ###########################################################
        # #############################################################################################################
        button_grid = FCGridLayout(v_spacing=5, h_spacing=3, c_stretch=[1, 0])
        new_tool_grid.addLayout(button_grid, 6, 0, 1, 3)

        self.search_and_add_btn = FCButton(_('Search and Add'))
        self.search_and_add_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/plus16.png'))
        self.search_and_add_btn.setToolTip(
            _("Add a new tool to the Tool Table\n"
              "with the diameter specified above.\n"
              "This is done by a background search\n"
              "in the Tools Database. If nothing is found\n"
              "in the Tools DB then a default tool is added.")
        )

        button_grid.addWidget(self.search_and_add_btn, 0, 0)

        self.addtool_from_db_btn = FCButton(_('Pick from DB'))
        self.addtool_from_db_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/search_db32.png'))
        self.addtool_from_db_btn.setToolTip(
            _("Add a new tool to the Tool Table\n"
              "from the Tools Database.\n"
              "Tools database administration in in:\n"
              "Menu: Options -> Tools Database")
        )

        button_grid.addWidget(self.addtool_from_db_btn, 1, 0)

        self.deltool_btn = FCButton()
        self.deltool_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/trash16.png'))
        self.deltool_btn.setToolTip(
            _("Delete a selection of tools in the Tool Table\n"
              "by first selecting a row in the Tool Table.")
        )
        self.deltool_btn.setSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)

        button_grid.addWidget(self.deltool_btn, 0, 1, 2, 1)
        # #############################################################################################################

        # #############################################################################################################
        # ALL Parameters Frame
        # #############################################################################################################
        self.tool_data_label = FCLabel(
            "<b>%s: <font color='#0000FF'>%s %d</font></b>" % (_('Parameters for'), _("Tool"), int(1)))
        self.tool_data_label.setToolTip(
            _(
                "The data used for creating GCode.\n"
                "Each tool store it's own set of such data."
            )
        )
        self.tools_box.addWidget(self.tool_data_label)

        self.param_frame = QtWidgets.QFrame()
        self.param_frame.setContentsMargins(0, 0, 0, 0)
        self.tools_box.addWidget(self.param_frame)

        self.tool_params_box = QtWidgets.QVBoxLayout()
        self.tool_params_box.setContentsMargins(0, 0, 0, 0)
        self.param_frame.setLayout(self.tool_params_box)

        # #############################################################################################################
        # Tool Parameters Frame
        # #############################################################################################################

        tp_frame = FCFrame()
        self.tool_params_box.addWidget(tp_frame)

        # Grid Layout
        tool_param_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        tp_frame.setLayout(tool_param_grid)

        # Tool Type
        self.tool_shape_label = FCLabel('%s:' % _('Shape'))
        self.tool_shape_label.setToolTip(
            _("Tool Shape. \n"
              "Can be:\n"
              "C1 ... C4 = circular tool with x flutes\n"
              "B = ball tip milling tool\n"
              "V = v-shape milling tool")
        )

        self.tool_shape_combo = FCComboBox2(policy=False)
        self.tool_shape_combo.setObjectName('i_tool_shape')
        self.tool_shape_combo.addItems(["C1", "C2", "C3", "C4", "B", "V"])

        idx = int(self.app.defaults['tools_iso_tool_shape'])
        # protection against having this translated or loading a project with translated values
        if idx == -1:
            self.tool_shape_combo.setCurrentIndex(0)
        else:
            self.tool_shape_combo.setCurrentIndex(idx)

        tool_param_grid.addWidget(self.tool_shape_label, 0, 0)
        tool_param_grid.addWidget(self.tool_shape_combo, 0, 1)

        # Passes
        passlabel = FCLabel('%s:' % _('Passes'))
        passlabel.setToolTip(
            _("Width of the isolation gap in\n"
              "number (integer) of tool widths.")
        )
        self.passes_entry = FCSpinner(callback=self.confirmation_message_int)
        self.passes_entry.set_range(1, 999)
        self.passes_entry.setObjectName("i_passes")

        tool_param_grid.addWidget(passlabel, 2, 0)
        tool_param_grid.addWidget(self.passes_entry, 2, 1)

        # Pad Passes
        padpasslabel = FCLabel('%s:' % _('Pad Passes'))
        padpasslabel.setToolTip(
            _("Width of the extra isolation gap for pads only,\n"
              "in number (integer) of tool widths.")
        )
        self.pad_passes_entry = FCSpinner()
        self.pad_passes_entry.set_range(0, 999)
        self.pad_passes_entry.setObjectName("i_pad_passes")

        tool_param_grid.addWidget(padpasslabel, 4, 0)
        tool_param_grid.addWidget(self.pad_passes_entry, 4, 1)

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

        tool_param_grid.addWidget(overlabel, 6, 0)
        tool_param_grid.addWidget(self.iso_overlap_entry, 6, 1)

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

        tool_param_grid.addWidget(self.milling_type_label, 8, 0)
        tool_param_grid.addWidget(self.milling_type_radio, 8, 1)

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

        tool_param_grid.addWidget(self.iso_type_label, 10, 0)
        tool_param_grid.addWidget(self.iso_type_radio, 10, 1)

        # ##############################################################################################################
        # Apply to All Parameters Button
        # ##############################################################################################################
        self.apply_param_to_all = FCButton(_("Apply parameters to all tools"))
        self.apply_param_to_all.setIcon(QtGui.QIcon(self.app.resource_location + '/param_all32.png'))
        self.apply_param_to_all.setToolTip(
            _("The parameters in the current form will be applied\n"
              "on all the tools from the Tool Table.")
        )
        self.tool_params_box.addWidget(self.apply_param_to_all)

        # #############################################################################################################
        # COMMON PARAMETERS
        # #############################################################################################################
        # General Parameters
        self.gen_param_label = FCLabel('<span style="color:indigo;"><b>%s</b></span>' % _("Common Parameters"))
        self.gen_param_label.setToolTip(
            _("Parameters that are common for all tools.")
        )
        self.tool_params_box.addWidget(self.gen_param_label)

        gp_frame = FCFrame()
        self.tool_params_box.addWidget(gp_frame)

        gen_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        gp_frame.setLayout(gen_grid)

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

        gen_grid.addWidget(self.rest_cb, 0, 0)

        # Force isolation even if the interiors are not isolated
        self.forced_rest_iso_cb = FCCheckBox(_("Forced Rest"))
        self.forced_rest_iso_cb.setToolTip(
            _("When checked the isolation will be done with the current tool even if\n"
              "interiors of a polygon (holes in the polygon) could not be isolated.\n"
              "Works when 'rest machining' is used.")
        )

        gen_grid.addWidget(self.forced_rest_iso_cb, 0, 1)

        # Combine All Passes
        self.combine_passes_cb = FCCheckBox(label=_('Combine'))
        self.combine_passes_cb.setToolTip(
            _("Combine all passes into one object")
        )
        self.combine_passes_cb.setObjectName("i_combine")

        gen_grid.addWidget(self.combine_passes_cb, 2, 0, 1, 2)

        # Check Tool validity
        self.valid_cb = FCCheckBox(label=_('Check validity'))
        self.valid_cb.setToolTip(
            _("If checked then the tools diameters are verified\n"
              "if they will provide a complete isolation.")
        )
        self.valid_cb.setObjectName("i_check")

        gen_grid.addWidget(self.valid_cb, 4, 0, 1, 2)

        # Exception Areas
        self.except_cb = FCCheckBox(label=_('Except'))
        self.except_cb.setToolTip(_("When the isolation geometry is generated,\n"
                                    "by checking this, the area of the object below\n"
                                    "will be subtracted from the isolation geometry."))
        self.except_cb.setObjectName("i_except")
        gen_grid.addWidget(self.except_cb, 6, 0)

        # Type of object to be excepted
        self.type_excobj_radio = RadioSet([{'label': _("Geometry"), 'value': 'geometry'},
                                           {'label': _("Gerber"), 'value': 'gerber'}])
        self.type_excobj_radio.setToolTip(
            _("Specify the type of object to be excepted from isolation.\n"
              "It can be of type: Gerber or Geometry.\n"
              "What is selected here will dictate the kind\n"
              "of objects that will populate the 'Object' combobox.")
        )

        gen_grid.addWidget(self.type_excobj_radio, 6, 1)

        # The object to be excepted
        self.exc_obj_combo = FCComboBox()
        self.exc_obj_combo.setToolTip(_("Object whose area will be removed from isolation geometry."))

        # set the model for the Area Exception comboboxes
        self.exc_obj_combo.setModel(self.app.collection)
        self.exc_obj_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.exc_obj_combo.is_last = True
        self.exc_obj_combo.obj_type = "gerber"

        gen_grid.addWidget(self.exc_obj_combo, 8, 0, 1, 2)

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

        gen_grid.addWidget(self.select_label, 10, 0)
        gen_grid.addWidget(self.select_combo, 10, 1)

        # Reference Type
        self.reference_combo_type_label = FCLabel('%s:' % _("Type"))

        self.reference_combo_type = FCComboBox2()
        self.reference_combo_type.addItems([_("Gerber"), _("Excellon"), _("Geometry")])

        gen_grid.addWidget(self.reference_combo_type_label, 12, 0)
        gen_grid.addWidget(self.reference_combo_type, 12, 1)

        self.reference_combo = FCComboBox()
        self.reference_combo.setModel(self.app.collection)
        self.reference_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.reference_combo.is_last = True

        gen_grid.addWidget(self.reference_combo, 14, 0, 1, 2)

        self.reference_combo.hide()
        self.reference_combo_type.hide()
        self.reference_combo_type_label.hide()

        # Polygon interiors selection
        self.poly_int_cb = FCCheckBox(_("Interiors"))
        self.poly_int_cb.setToolTip(
            _("When checked the user can select interiors of a polygon.\n"
              "(holes in the polygon).")
        )

        gen_grid.addWidget(self.poly_int_cb, 16, 0)

        self.poly_int_cb.hide()

        # Select All/None
        sel_hlay = QtWidgets.QHBoxLayout()
        self.sel_all_btn = FCButton(_("Select All"))
        self.sel_all_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/select_all.png'))

        self.sel_all_btn.setToolTip(
            _("Select all available.")
        )
        self.clear_all_btn = FCButton(_("Deselect All"))
        self.clear_all_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/deselect_all32.png'))

        self.clear_all_btn.setToolTip(
            _("Clear the selection.")
        )

        self.sel_all_btn.hide()
        self.clear_all_btn.hide()

        sel_hlay.addWidget(self.sel_all_btn)
        sel_hlay.addWidget(self.clear_all_btn)
        gen_grid.addLayout(sel_hlay, 18, 0, 1, 2)

        # Area Selection shape
        self.area_shape_label = FCLabel('%s:' % _("Shape"))
        self.area_shape_label.setToolTip(
            _("The kind of selection shape used for area selection.")
        )

        self.area_shape_radio = RadioSet([{'label': _("Square"), 'value': 'square'},
                                          {'label': _("Polygon"), 'value': 'polygon'}])

        gen_grid.addWidget(self.area_shape_label, 20, 0)
        gen_grid.addWidget(self.area_shape_radio, 20, 1)

        self.area_shape_label.hide()
        self.area_shape_radio.hide()

        FCGridLayout.set_common_column_size([tool_grid, new_tool_grid, tool_param_grid, gen_grid], 0)

        # #############################################################################################################
        # Generate Geometry object
        # #############################################################################################################
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

        self.tools_box.addStretch(1)

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
