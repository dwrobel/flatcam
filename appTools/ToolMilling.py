# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File by:  Marius Adrian Stanciu (c)                      #
# Date:     6/15/2020                                      #
# License:  MIT Licence                                    #
# ##########################################################

from PyQt5 import QtWidgets, QtCore, QtGui

from appTool import AppTool
from appGUI.GUIElements import FCCheckBox, FCDoubleSpinner, RadioSet, FCTable, FCButton, \
    FCComboBox, OptionalInputSection, FCSpinner, NumericalEvalEntry, OptionalHideInputSection, FCLabel
from appParsers.ParseExcellon import Excellon

from copy import deepcopy

# import numpy as np
# import math

# from shapely.ops import unary_union
from shapely.geometry import Point, LineString

from matplotlib.backend_bases import KeyEvent as mpl_key_event

import logging
import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')

settings = QtCore.QSettings("Open Source", "FlatCAM")
if settings.contains("machinist"):
    machinist_setting = settings.value('machinist', type=int)
else:
    machinist_setting = 0


class ToolMilling(AppTool, Excellon):

    def __init__(self, app):
        self.app = app
        self.decimals = self.app.decimals

        AppTool.__init__(self, app)
        Excellon.__init__(self, geo_steps_per_circle=self.app.defaults["geometry_circle_steps"])

        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = MillingUI(layout=self.layout, app=self.app)
        self.toolName = self.ui.toolName

        # #############################################################################
        # ########################## VARIABLES ########################################
        # #############################################################################
        self.units = ''
        self.excellon_tools = {}
        self.tooluid = 0

        # dict that holds the object names and the option name
        # the key is the object name (defines in ObjectUI) for each UI element that is a parameter
        # particular for a tool and the value is the actual name of the option that the UI element is changing
        self.name2option = {}

        # store here the default data for Geometry Data
        self.default_data = {}

        self.obj_name = ""
        self.excellon_obj = None

        self.first_click = False
        self.cursor_pos = None
        self.mouse_is_dragging = False

        # store here the points for the "Polygon" area selection shape
        self.points = []

        self.mm = None
        self.mr = None
        self.kp = None

        # variable to store the total amount of drills per job
        self.tot_drill_cnt = 0
        self.tool_row = 0

        # variable to store the total amount of slots per job
        self.tot_slot_cnt = 0
        self.tool_row_slots = 0

        # variable to store the distance travelled
        self.travel_distance = 0.0

        self.grid_status_memory = self.app.ui.grid_snap_btn.isChecked()

        # store here the state of the exclusion checkbox state to be restored after building the UI
        # TODO add this in the sel.app.defaults dict and in Preferences
        self.exclusion_area_cb_is_checked = False

        # store here solid_geometry when there are tool with isolation job
        self.solid_geometry = []

        self.circle_steps = int(self.app.defaults["geometry_circle_steps"])

        self.tooldia = None

        # multiprocessing
        self.pool = self.app.pool
        self.results = []

        # disconnect flags
        self.area_sel_disconnect_flag = False
        self.poly_sel_disconnect_flag = False

        self.form_fields = {
            "excellon_milling_type":   self.ui.milling_type_radio,
        }

        self.name2option = {
            "e_milling_type":   "excellon_milling_type",
        }

        self.old_tool_dia = None
        self.poly_drawn = False
        self.connect_signals_at_init()

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Alt+D', **kwargs)

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolDrilling()")
        log.debug("ToolDrilling().run() was launched ...")

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
        self.excellon_obj = None
        self.obj_name = ''

        self.build_ui()

        # all the tools are selected by default
        self.ui.tools_table.selectAll()

        self.app.ui.notebook.setTabText(2, _("Drilling Tool"))

    def connect_signals_at_init(self):
        # #############################################################################
        # ############################ SIGNALS ########################################
        # #############################################################################

        self.ui.apply_param_to_all.clicked.connect(self.on_apply_param_to_all_clicked)
        self.ui.generate_cnc_button.clicked.connect(self.on_cnc_button_click)
        self.ui.tools_table.drag_drop_sig.connect(self.rebuild_ui)

        # Exclusion areas signals
        self.ui.exclusion_table.horizontalHeader().sectionClicked.connect(self.exclusion_table_toggle_all)
        self.ui.exclusion_table.lost_focus.connect(self.clear_selection)
        self.ui.exclusion_table.itemClicked.connect(self.draw_sel_shape)
        self.ui.add_area_button.clicked.connect(self.on_add_area_click)
        self.ui.delete_area_button.clicked.connect(self.on_clear_area_click)
        self.ui.delete_sel_area_button.clicked.connect(self.on_delete_sel_areas)
        self.ui.strategy_radio.activated_custom.connect(self.on_strategy)

        self.on_operation_type(val='drill')
        self.ui.operation_radio.activated_custom.connect(self.on_operation_type)

        self.ui.pp_excellon_name_cb.activated.connect(self.on_pp_changed)

        self.ui.reset_button.clicked.connect(self.set_tool_ui)
        # Cleanup on Graceful exit (CTRL+ALT+X combo key)
        self.app.cleanup.connect(self.set_tool_ui)

    def set_tool_ui(self):
        self.units = self.app.defaults['units'].upper()
        self.old_tool_dia = self.app.defaults["tools_iso_newdia"]

        # try to select in the Gerber combobox the active object
        try:
            selected_obj = self.app.collection.get_active()
            if selected_obj.kind == 'excellon':
                current_name = selected_obj.options['name']
                self.ui.object_combo.set_value(current_name)
        except Exception:
            pass

        self.form_fields.update({

            "operation": self.ui.operation_radio,
            "milling_type": self.ui.milling_type_radio,

            "milling_dia": self.ui.mill_dia_entry,
            "cutz": self.ui.cutz_entry,
            "multidepth": self.ui.mpass_cb,
            "depthperpass": self.ui.maxdepth_entry,
            "travelz": self.ui.travelz_entry,
            "feedrate_z": self.ui.feedrate_z_entry,
            "feedrate": self.ui.xyfeedrate_entry,
            "feedrate_rapid": self.ui.feedrate_rapid_entry,
            # "tooldia": self.ui.tooldia_entry,
            # "slot_tooldia": self.ui.slot_tooldia_entry,
            "toolchange": self.ui.toolchange_cb,
            "toolchangez": self.ui.toolchangez_entry,
            "extracut": self.ui.extracut_cb,
            "extracut_length": self.ui.e_cut_entry,

            "spindlespeed": self.ui.spindlespeed_entry,
            "dwell": self.ui.dwell_cb,
            "dwelltime": self.ui.dwelltime_entry,

            "startz": self.ui.estartz_entry,
            "endz": self.ui.endz_entry,
            "endxy": self.ui.endxy_entry,

            "offset": self.ui.offset_entry,

            "ppname_e": self.ui.pp_excellon_name_cb,
            "ppname_g": self.ui.pp_geo_name_cb,
            "z_pdepth": self.ui.pdepth_entry,
            "feedrate_probe": self.ui.feedrate_probe_entry,
            # "gcode_type": self.ui.excellon_gcode_type_radio,
            "area_exclusion": self.ui.exclusion_cb,
            "area_shape": self.ui.area_shape_radio,
            "area_strategy": self.ui.strategy_radio,
            "area_overz": self.ui.over_z_entry,
        })

        self.name2option = {
            "e_operation": "operation",
            "e_milling_type": "milling_type",
            "e_milling_dia": "milling_dia",
            "e_cutz": "cutz",
            "e_multidepth": "multidepth",
            "e_depthperpass": "depthperpass",

            "e_travelz": "travelz",
            "e_feedratexy": "feedrate",
            "e_feedratez": "feedrate_z",
            "e_fr_rapid": "feedrate_rapid",
            "e_extracut": "extracut",
            "e_extracut_length": "extracut_length",
            "e_spindlespeed": "spindlespeed",
            "e_dwell": "dwell",
            "e_dwelltime": "dwelltime",
            "e_offset": "offset",
        }

        # populate Excellon preprocessor combobox list
        for name in list(self.app.preprocessors.keys()):
            # the HPGL preprocessor is only for Geometry not for Excellon job therefore don't add it
            if name == 'hpgl':
                continue
            self.ui.pp_excellon_name_cb.addItem(name)

        # populate Geometry (milling) preprocessor combobox list
        for name in list(self.app.preprocessors.keys()):
            self.ui.pp_geo_name_cb.addItem(name)

        # Fill form fields
        # self.to_form()

        # update the changes in UI depending on the selected preprocessor in Preferences
        # after this moment all the changes in the Posprocessor combo will be handled by the activated signal of the
        # self.ui.pp_excellon_name_cb combobox
        self.on_pp_changed()

        app_mode = self.app.defaults["global_app_level"]
        # Show/Hide Advanced Options
        if app_mode == 'b':
            self.ui.level.setText('<span style="color:green;"><b>%s</b></span>' % _('Basic'))
            self.ui.estartz_label.hide()
            self.ui.estartz_entry.hide()
            self.ui.feedrate_rapid_label.hide()
            self.ui.feedrate_rapid_entry.hide()
            self.ui.pdepth_label.hide()
            self.ui.pdepth_entry.hide()
            self.ui.feedrate_probe_label.hide()
            self.ui.feedrate_probe_entry.hide()

        else:
            self.ui.level.setText('<span style="color:red;"><b>%s</b></span>' % _('Advanced'))

        self.ui.tools_frame.show()

        self.ui.order_radio.set_value(self.app.defaults["excellon_tool_order"])
        self.ui.milling_type_radio.set_value(self.app.defaults["excellon_milling_type"])

        loaded_obj = self.app.collection.get_by_name(self.ui.object_combo.get_value())
        if loaded_obj:
            outname = loaded_obj.options['name']
        else:
            outname = ''

        # init the working variables
        self.default_data.clear()
        self.default_data = {
            "name":                     outname + '_iso',
            "plot":                     self.app.defaults["excellon_plot"],
            "solid": False,
            "multicolored": False,

            "operation": "drill",
            "milling_type": "drills",

            "milling_dia": 0.04,

            "cutz": -0.1,
            "multidepth": False,
            "depthperpass": 0.7,
            "travelz": 0.1,
            "feedrate": self.app.defaults["geometry_feedrate"],
            "feedrate_z": 5.0,
            "feedrate_rapid": 5.0,
            "tooldia": 0.1,
            "slot_tooldia": 0.1,
            "toolchange": False,
            "toolchangez": 1.0,
            "toolchangexy": "0.0, 0.0",
            "extracut": self.app.defaults["geometry_extracut"],
            "extracut_length": self.app.defaults["geometry_extracut_length"],
            "endz": 2.0,
            "endxy": '',

            "startz": None,
            "offset": 0.0,
            "spindlespeed": 0,
            "dwell": True,
            "dwelltime": 1000,
            "ppname_e": 'default',
            "ppname_g": self.app.defaults["geometry_ppname_g"],
            "z_pdepth": -0.02,
            "feedrate_probe": 3.0,
            "optimization_type": "B",
        }

        # fill in self.default_data values from self.options
        for opt_key, opt_val in self.app.options.items():
            if opt_key.find('excellon_') == 0:
                self.default_data[opt_key] = deepcopy(opt_val)
        for opt_key, opt_val in self.app.options.items():
            if opt_key.find('geometry_') == 0:
                self.default_data[opt_key] = deepcopy(opt_val)

        self.obj_name = ""
        self.excellon_obj = None

        self.first_click = False
        self.cursor_pos = None
        self.mouse_is_dragging = False

        self.units = self.app.defaults['units'].upper()

        # ########################################
        # #######3 TEMP SETTINGS #################
        # ########################################
        self.ui.operation_radio.set_value("drill")
        self.ui.operation_radio.setEnabled(False)

        self.on_object_changed()
        if self.excellon_obj:
            self.build_ui()

        try:
            self.ui.object_combo.currentIndexChanged.disconnect()
        except (AttributeError, TypeError):
            pass
        self.ui.object_combo.currentIndexChanged.connect(self.on_object_changed)

    def rebuild_ui(self):
        # read the table tools uid
        current_uid_list = []
        for row in range(self.ui.tools_table.rowCount()):
            uid = int(self.ui.tools_table.item(row, 3).text())
            current_uid_list.append(uid)

        new_tools = {}
        new_uid = 1

        for current_uid in current_uid_list:
            new_tools[new_uid] = deepcopy(self.iso_tools[current_uid])
            new_uid += 1

        self.iso_tools = new_tools

        # the tools table changed therefore we need to rebuild it
        QtCore.QTimer.singleShot(20, self.build_ui)

    def build_ui(self):
        self.ui_disconnect()

        # updated units
        self.units = self.app.defaults['units'].upper()

        self.obj_name = self.ui.object_combo.currentText()

        # Get source object.
        try:
            self.excellon_obj = self.app.collection.get_by_name(self.obj_name)
        except Exception as e:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), str(self.obj_name)))
            return "Could not retrieve object: %s with error: %s" % (self.obj_name, str(e))

        if self.excellon_obj:
            self.ui.exc_param_frame.setDisabled(False)

            tools = [k for k in self.excellon_tools]

        else:
            tools = []

        n = len(tools)
        # we have (n+2) rows because there are 'n' tools, each a row, plus the last 2 rows for totals.
        self.ui.tools_table.setRowCount(n + 2)
        self.tool_row = 0

        for tool_no in tools:

            drill_cnt = 0  # variable to store the nr of drills per tool
            slot_cnt = 0  # variable to store the nr of slots per tool

            # Find no of drills for the current tool
            try:
                drill_cnt = len(self.excellon_tools[tool_no]["drills"])
            except KeyError:
                drill_cnt = 0
            self.tot_drill_cnt += drill_cnt

            # Find no of slots for the current tool
            try:
                slot_cnt = len(self.excellon_tools[tool_no]["slots"])
            except KeyError:
                slot_cnt = 0
            self.tot_slot_cnt += slot_cnt

            # Tool name/id
            exc_id_item = QtWidgets.QTableWidgetItem('%d' % int(tool_no))
            exc_id_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.ui.tools_table.setItem(self.tool_row, 0, exc_id_item)

            # Tool Diameter
            dia_item = QtWidgets.QTableWidgetItem('%.*f' % (self.decimals, self.excellon_tools[tool_no]['tooldia']))
            dia_item.setFlags(QtCore.Qt.ItemIsEnabled)
            self.ui.tools_table.setItem(self.tool_row, 1, dia_item)

            # Number of drills per tool
            drill_count_item = QtWidgets.QTableWidgetItem('%d' % drill_cnt)
            drill_count_item.setFlags(QtCore.Qt.ItemIsEnabled)
            self.ui.tools_table.setItem(self.tool_row, 2, drill_count_item)

            # Tool unique ID
            tool_uid_item = QtWidgets.QTableWidgetItem(str(int(tool_no)))
            # ## REMEMBER: THIS COLUMN IS HIDDEN in UI
            self.ui.tools_table.setItem(self.tool_row, 3, tool_uid_item)

            # Number of slots per tool
            # if the slot number is zero is better to not clutter the GUI with zero's so we print a space
            slot_count_str = '%d' % slot_cnt if slot_cnt > 0 else ''
            slot_count_item = QtWidgets.QTableWidgetItem(slot_count_str)
            slot_count_item.setFlags(QtCore.Qt.ItemIsEnabled)
            self.ui.tools_table.setItem(self.tool_row, 4, slot_count_item)

            self.tool_row += 1

        # add a last row with the Total number of drills
        empty_1 = QtWidgets.QTableWidgetItem('')
        empty_1.setFlags(~QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        empty_1_1 = QtWidgets.QTableWidgetItem('')
        empty_1_1.setFlags(~QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

        label_tot_drill_count = QtWidgets.QTableWidgetItem(_('Total Drills'))
        label_tot_drill_count.setFlags(QtCore.Qt.ItemIsEnabled)

        tot_drill_count = QtWidgets.QTableWidgetItem('%d' % self.tot_drill_cnt)
        tot_drill_count.setFlags(QtCore.Qt.ItemIsEnabled)

        self.ui.tools_table.setItem(self.tool_row, 0, empty_1)
        self.ui.tools_table.setItem(self.tool_row, 1, label_tot_drill_count)
        self.ui.tools_table.setItem(self.tool_row, 2, tot_drill_count)  # Total number of drills
        self.ui.tools_table.setItem(self.tool_row, 4, empty_1_1)

        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)

        for k in [1, 2]:
            self.ui.tools_table.item(self.tool_row, k).setForeground(QtGui.QColor(127, 0, 255))
            self.ui.tools_table.item(self.tool_row, k).setFont(font)

        self.tool_row += 1

        # add a last row with the Total number of slots
        empty_2 = QtWidgets.QTableWidgetItem('')
        empty_2.setFlags(~QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        empty_2_1 = QtWidgets.QTableWidgetItem('')
        empty_2_1.setFlags(~QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

        label_tot_slot_count = QtWidgets.QTableWidgetItem(_('Total Slots'))
        tot_slot_count = QtWidgets.QTableWidgetItem('%d' % self.tot_slot_cnt)
        label_tot_slot_count.setFlags(QtCore.Qt.ItemIsEnabled)
        tot_slot_count.setFlags(QtCore.Qt.ItemIsEnabled)

        self.ui.tools_table.setItem(self.tool_row, 0, empty_2)
        self.ui.tools_table.setItem(self.tool_row, 1, label_tot_slot_count)
        self.ui.tools_table.setItem(self.tool_row, 2, empty_2_1)
        self.ui.tools_table.setItem(self.tool_row, 4, tot_slot_count)  # Total number of slots

        for kl in [1, 2, 4]:
            self.ui.tools_table.item(self.tool_row, kl).setFont(font)
            self.ui.tools_table.item(self.tool_row, kl).setForeground(QtGui.QColor(0, 70, 255))

        # make the diameter column editable
        for row in range(self.ui.tools_table.rowCount() - 2):
            self.ui.tools_table.item(row, 1).setFlags(
                QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

        self.ui.tools_table.resizeColumnsToContents()
        self.ui.tools_table.resizeRowsToContents()

        vertical_header = self.ui.tools_table.verticalHeader()
        vertical_header.hide()
        self.ui.tools_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        horizontal_header = self.ui.tools_table.horizontalHeader()
        self.ui.tools_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        horizontal_header.setMinimumSectionSize(10)
        horizontal_header.setDefaultSectionSize(70)

        horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(0, 20)
        horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        horizontal_header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)

        self.ui.tools_table.setSortingEnabled(False)

        self.ui.tools_table.setMinimumHeight(self.ui.tools_table.getHeight())
        self.ui.tools_table.setMaximumHeight(self.ui.tools_table.getHeight())

        # all the tools are selected by default
        self.ui.tools_table.selectAll()

        # Build Exclusion Areas section
        e_len = len(self.app.exc_areas.exclusion_areas_storage)
        self.ui.exclusion_table.setRowCount(e_len)

        area_id = 0

        for area in range(e_len):
            area_id += 1

            area_dict = self.app.exc_areas.exclusion_areas_storage[area]

            area_id_item = QtWidgets.QTableWidgetItem('%d' % int(area_id))
            area_id_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.ui.exclusion_table.setItem(area, 0, area_id_item)  # Area id

            object_item = QtWidgets.QTableWidgetItem('%s' % area_dict["obj_type"])
            object_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.ui.exclusion_table.setItem(area, 1, object_item)  # Origin Object

            strategy_item = QtWidgets.QTableWidgetItem('%s' % area_dict["strategy"])
            strategy_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.ui.exclusion_table.setItem(area, 2, strategy_item)  # Strategy

            overz_item = QtWidgets.QTableWidgetItem('%s' % area_dict["overz"])
            overz_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.ui.exclusion_table.setItem(area, 3, overz_item)  # Over Z

        self.ui.exclusion_table.resizeColumnsToContents()
        self.ui.exclusion_table.resizeRowsToContents()

        area_vheader = self.ui.exclusion_table.verticalHeader()
        area_vheader.hide()
        self.ui.exclusion_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        area_hheader = self.ui.exclusion_table.horizontalHeader()
        area_hheader.setMinimumSectionSize(10)
        area_hheader.setDefaultSectionSize(70)

        area_hheader.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        area_hheader.resizeSection(0, 20)
        area_hheader.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        area_hheader.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        area_hheader.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)

        # area_hheader.setStretchLastSection(True)
        self.ui.exclusion_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.ui.exclusion_table.setColumnWidth(0, 20)

        self.ui.exclusion_table.setMinimumHeight(self.ui.exclusion_table.getHeight())
        self.ui.exclusion_table.setMaximumHeight(self.ui.exclusion_table.getHeight())

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

    def on_object_changed(self):
        # load the Excellon object
        self.obj_name = self.ui.object_combo.currentText()

        # Get source object.
        try:
            self.excellon_obj = self.app.collection.get_by_name(self.obj_name)
        except Exception:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), str(self.obj_name)))
            return

        if self.excellon_obj is None:
            self.ui.exc_param_frame.setDisabled(True)
        else:
            self.ui.exc_param_frame.setDisabled(False)
            self.excellon_tools = self.excellon_obj.tools

            self.build_ui()

    def ui_connect(self):

        # Area Exception - exclusion shape added signal
        # first disconnect it from any other object
        try:
            self.app.exc_areas.e_shape_modified.disconnect()
        except (TypeError, AttributeError):
            pass
        # then connect it to the current build_ui() method
        self.app.exc_areas.e_shape_modified.connect(self.update_exclusion_table)

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
            elif isinstance(current_widget, FCComboBox):
                current_widget.currentIndexChanged.connect(self.form_to_storage)

        self.ui.order_radio.activated_custom[str].connect(self.on_order_changed)

    def ui_disconnect(self):
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
            self.ui.generate_cnc_button.setDisabled(True)
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("No Tool Selected"))
            )
            self.blockSignals(False)
            return
        else:
            self.ui.generate_cnc_button.setDisabled(False)

        if len(sel_rows) == 1:
            # update the QLabel that shows for which Tool we have the parameters in the UI form
            tooluid = int(self.ui.tools_table.item(list(sel_rows)[0], 0).text())
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s %d</font></b>" % (_('Parameters for'), _("Tool"), tooluid)
            )
        else:
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("Multiple Tools"))
            )

        for c_row in sel_rows:
            # populate the form with the data from the tool associated with the row parameter
            try:
                item = self.ui.tools_table.item(c_row, 3)
                if type(item) is not None:
                    tooluid = item.text()
                    self.storage_to_form(self.excellon_tools[str(tooluid)]['data'])
                else:
                    self.blockSignals(False)
                    return
            except Exception as e:
                log.debug("Tool missing. Add a tool in the Tool Table. %s" % str(e))
                self.blockSignals(False)
                return
        self.blockSignals(False)

    def storage_to_form(self, dict_storage):
        """
        Will update the GUI with data from the "storage" in this case the dict self.tools

        :param dict_storage:    A dictionary holding the data relevant for gnerating Gcode from Excellon
        :type dict_storage:     dict
        :return:                None
        :rtype:
        """
        for form_key in self.form_fields:
            for storage_key in dict_storage:
                if form_key == storage_key and form_key not in \
                        ["toolchange", "toolchangez", "startz", "endz", "ppname_e", "ppname_g"]:
                    try:
                        self.form_fields[form_key].set_value(dict_storage[form_key])
                    except Exception as e:
                        log.debug("ToolDrilling.storage_to_form() --> %s" % str(e))
                        pass

    def form_to_storage(self):
        """
        Will update the 'storage' attribute which is the dict self.tools with data collected from GUI

        :return:    None
        :rtype:
        """
        if self.ui.tools_table.rowCount() == 2:
            # there is no tool in tool table so we can't save the GUI elements values to storage
            # Excellon Tool Table has 2 rows by default
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

            for tooluid_key, tooluid_val in self.excellon_tools.items():
                if int(tooluid_key) == tooluid_item:
                    new_option_value = self.form_fields[option_changed].get_value()
                    if option_changed in tooluid_val:
                        tooluid_val[option_changed] = new_option_value
                    if option_changed in tooluid_val['data']:
                        tooluid_val['data'][option_changed] = new_option_value

        self.blockSignals(False)

    def on_operation_type(self, val):
        """
        Called by a RadioSet activated_custom signal

        :param val:     Parameter passes by the signal that called this method
        :type val:      str
        :return:        None
        :rtype:
        """
        if val == 'mill':
            self.ui.mill_type_label.show()
            self.ui.milling_type_radio.show()
            self.ui.mill_dia_label.show()
            self.ui.mill_dia_entry.show()
            self.ui.frxylabel.show()
            self.ui.xyfeedrate_entry.show()
            self.ui.extracut_cb.show()
            self.ui.e_cut_entry.show()
        else:
            self.ui.mill_type_label.hide()
            self.ui.milling_type_radio.hide()
            self.ui.mill_dia_label.hide()
            self.ui.mill_dia_entry.hide()

            self.ui.frxylabel.hide()
            self.ui.xyfeedrate_entry.hide()
            self.ui.extracut_cb.hide()
            self.ui.e_cut_entry.hide()

    def get_selected_tools_list(self):
        """
        Returns the keys to the self.tools dictionary corresponding
        to the selections on the tool list in the appGUI.

        :return:    List of tools.
        :rtype:     list
        """

        return [str(x.text()) for x in self.ui.tools_table.selectedItems()]

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

    def on_apply_param_to_all_clicked(self):
        if self.ui.tools_table.rowCount() == 0:
            # there is no tool in tool table so we can't save the GUI elements values to storage
            log.debug("ToolDrilling.on_apply_param_to_all_clicked() --> no tool in Tools Table, aborting.")
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

    def on_order_changed(self, order):
        if order != 'no':
            self.build_ui()

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

            self.iso_tools[current_uid].update({
                'type': typ,
                'tool_type': tt,
            })

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
            tooldia = float(self.options["tooldia"])

        # Sort tools by diameter. items() -> [('name', diameter), ...]
        # sorted_tools = sorted(list(self.tools.items()), key=lambda tl: tl[1]) # no longer works in Python3

        sort = []
        for k, v in self.tools.items():
            sort.append((k, v.get('tooldia')))
        sorted_tools = sorted(sort, key=lambda t1: t1[1])

        if tools == "all":
            tools = [i[0] for i in sorted_tools]  # List if ordered tool names.
            log.debug("Tools 'all' and sorted are: %s" % str(tools))

        if len(tools) == 0:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Please select one or more tools from the list and try again."))
            return False, "Error: No tools."

        for tool in tools:
            if tooldia > self.tools[tool]["C"]:
                self.app.inform.emit(
                    '[ERROR_NOTCL] %s %s: %s' % (
                        _("Milling tool for DRILLS is larger than hole size. Cancelled."),
                        _("Tool"),
                        str(tool)
                    )
                )
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

            app_obj.inform.emit(_("Generating drills milling geometry..."))

            # ## Add properties to the object

            # get the tool_table items in a list of row items
            tool_table_items = self.get_selected_tools_table_items()
            # insert an information only element in the front
            tool_table_items.insert(0, [_("Tool_nr"), _("Diameter"), _("Drills_Nr"), _("Slots_Nr")])

            geo_obj.options['Tools_in_use'] = tool_table_items
            geo_obj.options['type'] = 'Excellon Geometry'
            geo_obj.options["cnctooldia"] = str(tooldia)
            geo_obj.options["multidepth"] = self.options["multidepth"]
            geo_obj.solid_geometry = []

            # in case that the tool used has the same diameter with the hole, and since the maximum resolution
            # for FlatCAM is 6 decimals,
            # we add a tenth of the minimum value, meaning 0.0000001, which from our point of view is "almost zero"
            for hole in self.drills:
                if hole['tool'] in tools:
                    buffer_value = self.tools[hole['tool']]["C"] / 2 - tooldia / 2
                    if buffer_value == 0:
                        geo_obj.solid_geometry.append(
                            Point(hole['point']).buffer(0.0000001).exterior)
                    else:
                        geo_obj.solid_geometry.append(
                            Point(hole['point']).buffer(buffer_value).exterior)

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
            sort.append((k, v.get('tooldia')))
        sorted_tools = sorted(sort, key=lambda t1: t1[1])

        if tools == "all":
            tools = [i[0] for i in sorted_tools]  # List if ordered tool names.
            log.debug("Tools 'all' and sorted are: %s" % str(tools))

        if len(tools) == 0:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Please select one or more tools from the list and try again."))
            return False, "Error: No tools."

        for tool in tools:
            # I add the 0.0001 value to account for the rounding error in converting from IN to MM and reverse
            adj_toolstable_tooldia = float('%.*f' % (self.decimals, float(tooldia)))
            adj_file_tooldia = float('%.*f' % (self.decimals, float(self.tools[tool]["C"])))
            if adj_toolstable_tooldia > adj_file_tooldia + 0.0001:
                self.app.inform.emit('[ERROR_NOTCL] %s' %
                                     _("Milling tool for SLOTS is larger than hole size. Cancelled."))
                return False, "Error: Milling tool is larger than hole."

        def geo_init(geo_obj, app_obj):
            assert geo_obj.kind == 'geometry', "Initializer expected a GeometryObject, got %s" % type(geo_obj)

            app_obj.inform.emit(_("Generating slot milling geometry..."))

            # ## Add properties to the object
            # get the tool_table items in a list of row items
            tool_table_items = self.get_selected_tools_table_items()
            # insert an information only element in the front
            tool_table_items.insert(0, [_("Tool_nr"), _("Diameter"), _("Drills_Nr"), _("Slots_Nr")])

            geo_obj.options['Tools_in_use'] = tool_table_items
            geo_obj.options['type'] = 'Excellon Geometry'
            geo_obj.options["cnctooldia"] = str(tooldia)
            geo_obj.options["multidepth"] = self.options["multidepth"]
            geo_obj.solid_geometry = []

            # in case that the tool used has the same diameter with the hole, and since the maximum resolution
            # for FlatCAM is 6 decimals,
            # we add a tenth of the minimum value, meaning 0.0000001, which from our point of view is "almost zero"
            for slot in self.slots:
                if slot['tool'] in tools:
                    toolstable_tool = float('%.*f' % (self.decimals, float(tooldia)))
                    file_tool = float('%.*f' % (self.decimals, float(self.tools[tool]["C"])))

                    # I add the 0.0001 value to account for the rounding error in converting from IN to MM and reverse
                    # for the file_tool (tooldia actually)
                    buffer_value = float(file_tool / 2) - float(toolstable_tool / 2) + 0.0001
                    if buffer_value == 0:
                        start = slot['start']
                        stop = slot['stop']

                        lines_string = LineString([start, stop])
                        poly = lines_string.buffer(0.0000001, int(self.geo_steps_per_circle)).exterior
                        geo_obj.solid_geometry.append(poly)
                    else:
                        start = slot['start']
                        stop = slot['stop']

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

    def on_pp_changed(self):
        current_pp = self.ui.pp_excellon_name_cb.get_value()

        if "toolchange_probe" in current_pp.lower():
            self.ui.pdepth_entry.setVisible(True)
            self.ui.pdepth_label.show()

            self.ui.feedrate_probe_entry.setVisible(True)
            self.ui.feedrate_probe_label.show()
        else:
            self.ui.pdepth_entry.setVisible(False)
            self.ui.pdepth_label.hide()

            self.ui.feedrate_probe_entry.setVisible(False)
            self.ui.feedrate_probe_label.hide()

        if 'marlin' in current_pp.lower() or 'custom' in current_pp.lower():
            self.ui.feedrate_rapid_label.show()
            self.ui.feedrate_rapid_entry.show()
        else:
            self.ui.feedrate_rapid_label.hide()
            self.ui.feedrate_rapid_entry.hide()

        if 'laser' in current_pp.lower():
            self.ui.cutzlabel.hide()
            self.ui.cutz_entry.hide()
            try:
                self.ui.mpass_cb.hide()
                self.ui.maxdepth_entry.hide()
            except AttributeError:
                pass

            if 'marlin' in current_pp.lower():
                self.ui.travelzlabel.setText('%s:' % _("Focus Z"))
                self.ui.endz_label.show()
                self.ui.endz_entry.show()
            else:
                self.ui.travelzlabel.hide()
                self.ui.travelz_entry.hide()

                self.ui.endz_label.hide()
                self.ui.endz_entry.hide()

            try:
                self.ui.frzlabel.hide()
                self.ui.feedrate_z_entry.hide()
            except AttributeError:
                pass

            self.ui.dwell_cb.hide()
            self.ui.dwelltime_entry.hide()

            self.ui.spindle_label.setText('%s:' % _("Laser Power"))

            try:
                self.ui.tool_offset_label.hide()
                self.ui.offset_entry.hide()
            except AttributeError:
                pass
        else:
            self.ui.cutzlabel.show()
            self.ui.cutz_entry.show()
            try:
                self.ui.mpass_cb.show()
                self.ui.maxdepth_entry.show()
            except AttributeError:
                pass

            self.ui.travelzlabel.setText('%s:' % _('Travel Z'))

            self.ui.travelzlabel.show()
            self.ui.travelz_entry.show()

            self.ui.endz_label.show()
            self.ui.endz_entry.show()

            try:
                self.ui.frzlabel.show()
                self.ui.feedrate_z_entry.show()
            except AttributeError:
                pass
            self.ui.dwell_cb.show()
            self.ui.dwelltime_entry.show()

            self.ui.spindle_label.setText('%s:' % _('Spindle speed'))

            try:
                # self.ui.tool_offset_lbl.show()
                self.ui.offset_entry.show()
            except AttributeError:
                pass

    def on_cnc_button_click(self):
        self.obj_name = self.ui.object_combo.currentText()

        # Get source object.
        try:
            self.excellon_obj = self.app.collection.get_by_name(self.obj_name)
        except Exception as e:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), str(self.obj_name)))
            return "Could not retrieve object: %s with error: %s" % (self.obj_name, str(e))

        if self.excellon_obj is None:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Object not found"), str(self.obj_name)))
            return

        # Get the tools from the list
        tools = self.get_selected_tools_list()

        if len(tools) == 0:
            # if there is a single tool in the table (remember that the last 2 rows are for totals and do not count in
            # tool number) it means that there are 3 rows (1 tool and 2 totals).
            # in this case regardless of the selection status of that tool, use it.
            if self.ui.tools_table.rowCount() == 3:
                tools.append(self.ui.tools_table.item(0, 0).text())
            else:
                self.app.inform.emit('[ERROR_NOTCL] %s' %
                                     _("Please select one or more tools from the list and try again."))
                return

        xmin = self.options['xmin']
        ymin = self.options['ymin']
        xmax = self.options['xmax']
        ymax = self.options['ymax']

        job_name = self.options["name"] + "_cnc"
        pp_excellon_name = self.options["ppname_e"]

        # Object initialization function for app.app_obj.new_object()
        def job_init(job_obj, app_obj):
            assert job_obj.kind == 'cncjob', "Initializer expected a CNCJobObject, got %s" % type(job_obj)

            app_obj.inform.emit(_("Generating CNCJob..."))

            # get the tool_table items in a list of row items
            tool_table_items = self.get_selected_tools_table_items()
            # insert an information only element in the front
            tool_table_items.insert(0, [_("Tool_nr"), _("Diameter"), _("Drills_Nr"), _("Slots_Nr")])

            # ## Add properties to the object

            job_obj.origin_kind = 'excellon'

            job_obj.options['Tools_in_use'] = tool_table_items
            job_obj.options['type'] = 'Excellon'
            job_obj.options['ppname_e'] = pp_excellon_name

            job_obj.multidepth = self.options["multidepth"]
            job_obj.z_depthpercut = self.options["depthperpass"]

            job_obj.z_move = float(self.options["travelz"])
            job_obj.feedrate = float(self.options["feedrate_z"])
            job_obj.z_feedrate = float(self.options["feedrate_z"])
            job_obj.feedrate_rapid = float(self.options["feedrate_rapid"])

            job_obj.spindlespeed = float(self.options["spindlespeed"]) if self.options["spindlespeed"] != 0 else None
            job_obj.spindledir = self.app.defaults['excellon_spindledir']
            job_obj.dwell = self.options["dwell"]
            job_obj.dwelltime = float(self.options["dwelltime"])

            job_obj.pp_excellon_name = pp_excellon_name

            job_obj.toolchange_xy_type = "excellon"
            job_obj.coords_decimals = int(self.app.defaults["cncjob_coords_decimals"])
            job_obj.fr_decimals = int(self.app.defaults["cncjob_fr_decimals"])

            job_obj.options['xmin'] = xmin
            job_obj.options['ymin'] = ymin
            job_obj.options['xmax'] = xmax
            job_obj.options['ymax'] = ymax

            job_obj.z_pdepth = float(self.options["z_pdepth"])
            job_obj.feedrate_probe = float(self.options["feedrate_probe"])

            job_obj.z_cut = float(self.options['cutz'])
            job_obj.toolchange = self.options["toolchange"]
            job_obj.xy_toolchange = self.app.defaults["excellon_toolchangexy"]
            job_obj.z_toolchange = float(self.options["toolchangez"])
            job_obj.startz = float(self.options["startz"]) if self.options["startz"] else None
            job_obj.endz = float(self.options["endz"])
            job_obj.xy_end = self.options["endxy"]
            job_obj.excellon_optimization_type = self.app.defaults["excellon_optimization_type"]

            tools_csv = ','.join(tools)
            ret_val = job_obj.generate_from_excellon_by_tool(self, tools_csv, use_ui=True)

            if ret_val == 'fail':
                return 'fail'

            job_obj.gcode_parse()
            job_obj.create_geometry()

        # To be run in separate thread
        def job_thread(a_obj):
            with self.app.proc_container.new(_("Generating CNC Code")):
                a_obj.app_obj.new_object("cncjob", job_name, job_init)

        # Create promise for the new name.
        self.app.collection.promise(job_name)

        # Send to worker
        # self.app.worker.add_task(job_thread, [self.app])
        self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})

    def drilling_handler(self, obj):
        pass

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
            self.points = []
            self.poly_drawn = False
            self.delete_moving_selection_shape()
            self.delete_tool_selection_shape()

    def on_add_area_click(self):
        shape_button = self.ui.area_shape_radio
        overz_button = self.ui.over_z_entry
        strategy_radio = self.ui.strategy_radio
        cnc_button = self.ui.generate_cnc_button
        solid_geo = self.solid_geometry
        obj_type = self.kind

        self.app.exc_areas.on_add_area_click(
            shape_button=shape_button, overz_button=overz_button, cnc_button=cnc_button, strategy_radio=strategy_radio,
            solid_geo=solid_geo, obj_type=obj_type)

    def on_clear_area_click(self):
        if not self.app.exc_areas.exclusion_areas_storage:
            self.app.inform.emit("[WARNING_NOTCL] %s" % _("Delete failed. There are no exclusion areas to delete."))
            return

        self.app.exc_areas.on_clear_area_click()
        self.app.exc_areas.e_shape_modified.emit()

    def on_delete_sel_areas(self):
        sel_model = self.ui.exclusion_table.selectionModel()
        sel_indexes = sel_model.selectedIndexes()

        # it will iterate over all indexes which means all items in all columns too but I'm interested only on rows
        # so the duplicate rows will not be added
        sel_rows = set()
        for idx in sel_indexes:
            sel_rows.add(idx.row())

        if not sel_rows:
            self.app.inform.emit("[WARNING_NOTCL] %s" % _("Delete failed. Nothing is selected."))
            return

        self.app.exc_areas.delete_sel_shapes(idxs=list(sel_rows))
        self.app.exc_areas.e_shape_modified.emit()

    def draw_sel_shape(self):
        sel_model = self.ui.exclusion_table.selectionModel()
        sel_indexes = sel_model.selectedIndexes()

        # it will iterate over all indexes which means all items in all columns too but I'm interested only on rows
        sel_rows = set()
        for idx in sel_indexes:
            sel_rows.add(idx.row())

        self.delete_sel_shape()

        if self.app.is_legacy is False:
            face = self.app.defaults['global_sel_fill'][:-2] + str(hex(int(0.2 * 255)))[2:]
            outline = self.app.defaults['global_sel_line'][:-2] + str(hex(int(0.8 * 255)))[2:]
        else:
            face = self.app.defaults['global_sel_fill'][:-2] + str(hex(int(0.4 * 255)))[2:]
            outline = self.app.defaults['global_sel_line'][:-2] + str(hex(int(1.0 * 255)))[2:]

        for row in sel_rows:
            sel_rect = self.app.exc_areas.exclusion_areas_storage[row]['shape']
            self.app.move_tool.sel_shapes.add(sel_rect, color=outline, face_color=face, update=True, layer=0,
                                              tolerance=None)
        if self.app.is_legacy is True:
            self.app.move_tool.sel_shapes.redraw()

    def clear_selection(self):
        self.app.delete_selection_shape()
        # self.ui.exclusion_table.clearSelection()

    def delete_sel_shape(self):
        self.app.delete_selection_shape()

    def update_exclusion_table(self):
        self.exclusion_area_cb_is_checked = True if self.ui.exclusion_cb.isChecked() else False

        self.build_ui()
        self.ui.exclusion_cb.set_value(self.exclusion_area_cb_is_checked)

    def on_strategy(self, val):
        if val == 'around':
            self.ui.over_z_label.setDisabled(True)
            self.ui.over_z_entry.setDisabled(True)
        else:
            self.ui.over_z_label.setDisabled(False)
            self.ui.over_z_entry.setDisabled(False)

    def exclusion_table_toggle_all(self):
        """
        will toggle the selection of all rows in Exclusion Areas table

        :return:
        """
        sel_model = self.ui.exclusion_table.selectionModel()
        sel_indexes = sel_model.selectedIndexes()

        # it will iterate over all indexes which means all items in all columns too but I'm interested only on rows
        sel_rows = set()
        for idx in sel_indexes:
            sel_rows.add(idx.row())

        if sel_rows:
            self.ui.exclusion_table.clearSelection()
            self.delete_sel_shape()
        else:
            self.ui.exclusion_table.selectAll()
            self.draw_sel_shape()

    def reset_fields(self):
        self.object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))


class MillingUI:

    toolName = _("Milling Holes Tool")

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
        title_label = QtWidgets.QLabel("%s" % self.toolName)
        title_label.setStyleSheet("""
                                QLabel
                                {
                                    font-size: 16px;
                                    font-weight: bold;
                                }
                                """)
        title_label.setToolTip(
            _("Create CNCJob with toolpaths for drilling or milling holes.")
        )

        self.title_box.addWidget(title_label)

        # App Level label
        self.level = QtWidgets.QLabel("")
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

        # Grid Layout
        grid0 = QtWidgets.QGridLayout()
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        self.tools_box.addLayout(grid0)

        self.obj_combo_label = QtWidgets.QLabel('<b>%s</b>:' % _("EXCELLON"))
        self.obj_combo_label.setToolTip(
            _("Excellon object for drilling/milling operation.")
        )

        grid0.addWidget(self.obj_combo_label, 0, 0, 1, 2)

        # ################################################
        # ##### The object to be drilled #################
        # ################################################
        self.object_combo = FCComboBox()
        self.object_combo.setModel(self.app.collection)
        self.object_combo.setRootModelIndex(self.app.collection.index(1, 0, QtCore.QModelIndex()))
        # self.object_combo.setCurrentIndex(1)
        self.object_combo.is_last = True

        grid0.addWidget(self.object_combo, 1, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 2, 0, 1, 2)

        # ################################################
        # ########## Excellon Tool Table #################
        # ################################################
        self.tools_table = FCTable(drag_drop=True)
        grid0.addWidget(self.tools_table, 3, 0, 1, 2)

        self.tools_table.setColumnCount(5)
        self.tools_table.setColumnHidden(3, True)
        self.tools_table.setSortingEnabled(False)

        self.tools_table.setHorizontalHeaderLabels(['#', _('Diameter'), _('Drills'), '', _('Slots')])
        self.tools_table.horizontalHeaderItem(0).setToolTip(
            _("This is the Tool Number.\n"
              "When ToolChange is checked, on toolchange event this value\n"
              "will be showed as a T1, T2 ... Tn in the Machine Code.\n\n"
              "Here the tools are selected for G-code generation."))
        self.tools_table.horizontalHeaderItem(1).setToolTip(
            _("Tool Diameter. Its value\n"
              "is the cut width into the material."))
        self.tools_table.horizontalHeaderItem(2).setToolTip(
            _("The number of Drill holes. Holes that are drilled with\n"
              "a drill bit."))
        self.tools_table.horizontalHeaderItem(3).setToolTip(
            _("The number of Slot holes. Holes that are created by\n"
              "milling them with an endmill bit."))

        # Tool order
        self.order_label = QtWidgets.QLabel('%s:' % _('Tool order'))
        self.order_label.setToolTip(_("This set the way that the tools in the tools table are used.\n"
                                      "'No' --> means that the used order is the one in the tool table\n"
                                      "'Forward' --> means that the tools will be ordered from small to big\n"
                                      "'Reverse' --> means that the tools will ordered from big to small\n\n"
                                      "WARNING: using rest machining will automatically set the order\n"
                                      "in reverse and disable this control."))

        self.order_radio = RadioSet([{'label': _('No'), 'value': 'no'},
                                     {'label': _('Forward'), 'value': 'fwd'},
                                     {'label': _('Reverse'), 'value': 'rev'}])

        grid0.addWidget(self.order_label, 4, 0)
        grid0.addWidget(self.order_radio, 4, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 5, 0, 1, 2)

        # ###########################################################
        # ############# Create CNC Job ##############################
        # ###########################################################
        self.tool_data_label = QtWidgets.QLabel(
            "<b>%s: <font color='#0000FF'>%s %d</font></b>" % (_('Parameters for'), _("Tool"), int(1)))
        self.tool_data_label.setToolTip(
            _(
                "The data used for creating GCode.\n"
                "Each tool store it's own set of such data."
            )
        )
        grid0.addWidget(self.tool_data_label, 6, 0, 1, 2)

        self.exc_param_frame = QtWidgets.QFrame()
        self.exc_param_frame.setContentsMargins(0, 0, 0, 0)
        grid0.addWidget(self.exc_param_frame, 7, 0, 1, 2)

        self.exc_tools_box = QtWidgets.QVBoxLayout()
        self.exc_tools_box.setContentsMargins(0, 0, 0, 0)
        self.exc_param_frame.setLayout(self.exc_tools_box)

        # #################################################################
        # ################# GRID LAYOUT 3   ###############################
        # #################################################################

        self.grid1 = QtWidgets.QGridLayout()
        self.grid1.setColumnStretch(0, 0)
        self.grid1.setColumnStretch(1, 1)
        self.exc_tools_box.addLayout(self.grid1)

        # Operation Type
        self.operation_label = QtWidgets.QLabel('<b>%s:</b>' % _('Operation'))
        self.operation_label.setToolTip(
            _("Operation type:\n"
              "- Drilling -> will drill the drills/slots associated with this tool\n"
              "- Milling -> will mill the drills/slots")
        )
        self.operation_radio = RadioSet(
            [
                {'label': _('Drilling'), 'value': 'drill'},
                {'label': _("Milling"), 'value': 'mill'}
            ]
        )
        self.operation_radio.setObjectName("e_operation")

        self.grid1.addWidget(self.operation_label, 0, 0)
        self.grid1.addWidget(self.operation_radio, 0, 1)

        # separator_line = QtWidgets.QFrame()
        # separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        # separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        # self.grid3.addWidget(separator_line, 1, 0, 1, 2)

        self.mill_type_label = QtWidgets.QLabel('%s:' % _('Milling Type'))
        self.mill_type_label.setToolTip(
            _("Milling type:\n"
              "- Drills -> will mill the drills associated with this tool\n"
              "- Slots -> will mill the slots associated with this tool\n"
              "- Both -> will mill both drills and mills or whatever is available")
        )
        self.milling_type_radio = RadioSet(
            [
                {'label': _('Drills'), 'value': 'drills'},
                {'label': _("Slots"), 'value': 'slots'},
                {'label': _("Both"), 'value': 'both'},
            ]
        )
        self.milling_type_radio.setObjectName("e_milling_type")

        self.grid1.addWidget(self.mill_type_label, 2, 0)
        self.grid1.addWidget(self.milling_type_radio, 2, 1)

        self.mill_dia_label = QtWidgets.QLabel('%s:' % _('Milling Diameter'))
        self.mill_dia_label.setToolTip(
            _("The diameter of the tool who will do the milling")
        )

        self.mill_dia_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.mill_dia_entry.set_precision(self.decimals)
        self.mill_dia_entry.set_range(0.0000, 10000.0000)
        self.mill_dia_entry.setObjectName("e_milling_dia")

        self.grid1.addWidget(self.mill_dia_label, 3, 0)
        self.grid1.addWidget(self.mill_dia_entry, 3, 1)

        # Cut Z
        self.cutzlabel = QtWidgets.QLabel('%s:' % _('Cut Z'))
        self.cutzlabel.setToolTip(
            _("Drill depth (negative)\n"
              "below the copper surface.")
        )

        self.cutz_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.cutz_entry.set_precision(self.decimals)

        if machinist_setting == 0:
            self.cutz_entry.set_range(-10000.0000, 0.0000)
        else:
            self.cutz_entry.set_range(-10000.0000, 10000.0000)

        self.cutz_entry.setSingleStep(0.1)
        self.cutz_entry.setObjectName("e_cutz")

        self.grid1.addWidget(self.cutzlabel, 4, 0)
        self.grid1.addWidget(self.cutz_entry, 4, 1)

        # Multi-Depth
        self.mpass_cb = FCCheckBox('%s:' % _("Multi-Depth"))
        self.mpass_cb.setToolTip(
            _(
                "Use multiple passes to limit\n"
                "the cut depth in each pass. Will\n"
                "cut multiple times until Cut Z is\n"
                "reached."
            )
        )
        self.mpass_cb.setObjectName("e_multidepth")

        self.maxdepth_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.maxdepth_entry.set_precision(self.decimals)
        self.maxdepth_entry.set_range(0, 10000.0000)
        self.maxdepth_entry.setSingleStep(0.1)

        self.maxdepth_entry.setToolTip(_("Depth of each pass (positive)."))
        self.maxdepth_entry.setObjectName("e_depthperpass")

        self.mis_mpass_geo = OptionalInputSection(self.mpass_cb, [self.maxdepth_entry])

        self.grid1.addWidget(self.mpass_cb, 5, 0)
        self.grid1.addWidget(self.maxdepth_entry, 5, 1)

        # Travel Z (z_move)
        self.travelzlabel = QtWidgets.QLabel('%s:' % _('Travel Z'))
        self.travelzlabel.setToolTip(
            _("Tool height when travelling\n"
              "across the XY plane.")
        )

        self.travelz_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.travelz_entry.set_precision(self.decimals)

        if machinist_setting == 0:
            self.travelz_entry.set_range(0.00001, 10000.0000)
        else:
            self.travelz_entry.set_range(-10000.0000, 10000.0000)

        self.travelz_entry.setSingleStep(0.1)
        self.travelz_entry.setObjectName("e_travelz")

        self.grid1.addWidget(self.travelzlabel, 6, 0)
        self.grid1.addWidget(self.travelz_entry, 6, 1)

        # Feedrate X-Y
        self.frxylabel = QtWidgets.QLabel('%s:' % _('Feedrate X-Y'))
        self.frxylabel.setToolTip(
            _("Cutting speed in the XY\n"
              "plane in units per minute")
        )
        self.xyfeedrate_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.xyfeedrate_entry.set_precision(self.decimals)
        self.xyfeedrate_entry.set_range(0, 10000.0000)
        self.xyfeedrate_entry.setSingleStep(0.1)
        self.xyfeedrate_entry.setObjectName("e_feedratexy")

        self.grid1.addWidget(self.frxylabel, 12, 0)
        self.grid1.addWidget(self.xyfeedrate_entry, 12, 1)

        # Excellon Feedrate Z
        self.frzlabel = QtWidgets.QLabel('%s:' % _('Feedrate Z'))
        self.frzlabel.setToolTip(
            _("Tool speed while drilling\n"
              "(in units per minute).\n"
              "So called 'Plunge' feedrate.\n"
              "This is for linear move G01.")
        )
        self.feedrate_z_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.feedrate_z_entry.set_precision(self.decimals)
        self.feedrate_z_entry.set_range(0.0, 910000.0000)
        self.feedrate_z_entry.setSingleStep(0.1)
        self.feedrate_z_entry.setObjectName("e_feedratez")

        self.grid1.addWidget(self.frzlabel, 14, 0)
        self.grid1.addWidget(self.feedrate_z_entry, 14, 1)

        # Excellon Rapid Feedrate
        self.feedrate_rapid_label = QtWidgets.QLabel('%s:' % _('Feedrate Rapids'))
        self.feedrate_rapid_label.setToolTip(
            _("Tool speed while drilling\n"
              "(in units per minute).\n"
              "This is for the rapid move G00.\n"
              "It is useful only for Marlin,\n"
              "ignore for any other cases.")
        )
        self.feedrate_rapid_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.feedrate_rapid_entry.set_precision(self.decimals)
        self.feedrate_rapid_entry.set_range(0.0, 910000.0000)
        self.feedrate_rapid_entry.setSingleStep(0.1)
        self.feedrate_rapid_entry.setObjectName("e_fr_rapid")

        self.grid1.addWidget(self.feedrate_rapid_label, 16, 0)
        self.grid1.addWidget(self.feedrate_rapid_entry, 16, 1)

        # default values is to hide
        self.feedrate_rapid_label.hide()
        self.feedrate_rapid_entry.hide()

        # Cut over 1st point in path
        self.extracut_cb = FCCheckBox('%s:' % _('Re-cut'))
        self.extracut_cb.setToolTip(
            _("In order to remove possible\n"
              "copper leftovers where first cut\n"
              "meet with last cut, we generate an\n"
              "extended cut over the first cut section.")
        )
        self.extracut_cb.setObjectName("e_extracut")

        self.e_cut_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.e_cut_entry.set_range(0, 99999)
        self.e_cut_entry.set_precision(self.decimals)
        self.e_cut_entry.setSingleStep(0.1)
        self.e_cut_entry.setWrapping(True)
        self.e_cut_entry.setToolTip(
            _("In order to remove possible\n"
              "copper leftovers where first cut\n"
              "meet with last cut, we generate an\n"
              "extended cut over the first cut section.")
        )
        self.e_cut_entry.setObjectName("e_extracut_length")

        self.ois_recut = OptionalInputSection(self.extracut_cb, [self.e_cut_entry])

        self.grid1.addWidget(self.extracut_cb, 17, 0)
        self.grid1.addWidget(self.e_cut_entry, 17, 1)

        # Spindlespeed
        self.spindle_label = QtWidgets.QLabel('%s:' % _('Spindle speed'))
        self.spindle_label.setToolTip(
            _("Speed of the spindle\n"
              "in RPM (optional)")
        )

        self.spindlespeed_entry = FCSpinner(callback=self.confirmation_message_int)
        self.spindlespeed_entry.set_range(0, 1000000)
        self.spindlespeed_entry.set_step(100)
        self.spindlespeed_entry.setObjectName("e_spindlespeed")

        self.grid1.addWidget(self.spindle_label, 19, 0)
        self.grid1.addWidget(self.spindlespeed_entry, 19, 1)

        # Dwell
        self.dwell_cb = FCCheckBox('%s:' % _('Dwell'))
        self.dwell_cb.setToolTip(
            _("Pause to allow the spindle to reach its\n"
              "speed before cutting.")
        )
        self.dwell_cb.setObjectName("e_dwell")

        self.dwelltime_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.dwelltime_entry.set_precision(self.decimals)
        self.dwelltime_entry.set_range(0.0, 10000.0000)
        self.dwelltime_entry.setSingleStep(0.1)

        self.dwelltime_entry.setToolTip(
            _("Number of time units for spindle to dwell.")
        )
        self.dwelltime_entry.setObjectName("e_dwelltime")

        self.grid1.addWidget(self.dwell_cb, 20, 0)
        self.grid1.addWidget(self.dwelltime_entry, 20, 1)

        self.ois_dwell = OptionalInputSection(self.dwell_cb, [self.dwelltime_entry])

        # Tool Offset
        self.tool_offset_label = QtWidgets.QLabel('%s:' % _('Offset Z'))
        self.tool_offset_label.setToolTip(
            _("Some drill bits (the larger ones) need to drill deeper\n"
              "to create the desired exit hole diameter due of the tip shape.\n"
              "The value here can compensate the Cut Z parameter.")
        )

        self.offset_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.offset_entry.set_precision(self.decimals)
        self.offset_entry.set_range(-10000.0000, 10000.0000)
        self.offset_entry.setObjectName("e_offset")

        self.grid1.addWidget(self.tool_offset_label, 25, 0)
        self.grid1.addWidget(self.offset_entry, 25, 1)

        # #################################################################
        # ################# GRID LAYOUT 4   ###############################
        # #################################################################

        # self.grid4 = QtWidgets.QGridLayout()
        # self.exc_tools_box.addLayout(self.grid4)
        # self.grid4.setColumnStretch(0, 0)
        # self.grid4.setColumnStretch(1, 1)
        #
        # # choose_tools_label = QtWidgets.QLabel(
        # #     _("Select from the Tools Table above the hole dias to be\n"
        # #       "drilled. Use the # column to make the selection.")
        # # )
        # # grid2.addWidget(choose_tools_label, 0, 0, 1, 3)
        #
        # # ### Choose what to use for Gcode creation: Drills, Slots or Both
        # gcode_type_label = QtWidgets.QLabel('<b>%s</b>' % _('Gcode'))
        # gcode_type_label.setToolTip(
        #     _("Choose what to use for GCode generation:\n"
        #       "'Drills', 'Slots' or 'Both'.\n"
        #       "When choosing 'Slots' or 'Both', slots will be\n"
        #       "converted to a series of drills.")
        # )
        # self.excellon_gcode_type_radio = RadioSet([{'label': 'Drills', 'value': 'drills'},
        #                                            {'label': 'Slots', 'value': 'slots'},
        #                                            {'label': 'Both', 'value': 'both'}])
        # self.grid4.addWidget(gcode_type_label, 1, 0)
        # self.grid4.addWidget(self.excellon_gcode_type_radio, 1, 1)
        # # temporary action until I finish the feature
        # self.excellon_gcode_type_radio.setVisible(False)
        # gcode_type_label.hide()

        # #################################################################
        # ################# GRID LAYOUT 5   ###############################
        # #################################################################
        # ################# COMMON PARAMETERS #############################

        self.grid3 = QtWidgets.QGridLayout()
        self.grid3.setColumnStretch(0, 0)
        self.grid3.setColumnStretch(1, 1)
        self.exc_tools_box.addLayout(self.grid3)

        separator_line2 = QtWidgets.QFrame()
        separator_line2.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line2.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.grid3.addWidget(separator_line2, 0, 0, 1, 2)

        self.apply_param_to_all = FCButton(_("Apply parameters to all tools"))
        self.apply_param_to_all.setIcon(QtGui.QIcon(self.app.resource_location + '/param_all32.png'))
        self.apply_param_to_all.setToolTip(
            _("The parameters in the current form will be applied\n"
              "on all the tools from the Tool Table.")
        )
        self.grid3.addWidget(self.apply_param_to_all, 1, 0, 1, 2)

        separator_line2 = QtWidgets.QFrame()
        separator_line2.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line2.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.grid3.addWidget(separator_line2, 2, 0, 1, 2)

        # General Parameters
        self.gen_param_label = QtWidgets.QLabel('<b>%s</b>' % _("Common Parameters"))
        self.gen_param_label.setToolTip(
            _("Parameters that are common for all tools.")
        )
        self.grid3.addWidget(self.gen_param_label, 3, 0, 1, 2)

        # Tool change Z:
        self.toolchange_cb = FCCheckBox('%s:' % _("Tool change Z"))
        self.toolchange_cb.setToolTip(
            _("Include tool-change sequence\n"
              "in G-Code (Pause for tool change).")
        )

        self.toolchangez_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.toolchangez_entry.set_precision(self.decimals)
        self.toolchangez_entry.setToolTip(
            _("Z-axis position (height) for\n"
              "tool change.")
        )
        if machinist_setting == 0:
            self.toolchangez_entry.set_range(0.0, 10000.0000)
        else:
            self.toolchangez_entry.set_range(-10000.0000, 10000.0000)

        self.toolchangez_entry.setSingleStep(0.1)
        self.ois_tcz_e = OptionalInputSection(self.toolchange_cb, [self.toolchangez_entry])

        self.grid3.addWidget(self.toolchange_cb, 8, 0)
        self.grid3.addWidget(self.toolchangez_entry, 8, 1)

        # Start move Z:
        self.estartz_label = QtWidgets.QLabel('%s:' % _("Start Z"))
        self.estartz_label.setToolTip(
            _("Height of the tool just after starting the work.\n"
              "Delete the value if you don't need this feature.")
        )
        self.estartz_entry = NumericalEvalEntry(border_color='#0069A9')

        self.grid3.addWidget(self.estartz_label, 9, 0)
        self.grid3.addWidget(self.estartz_entry, 9, 1)

        # End move Z:
        self.endz_label = QtWidgets.QLabel('%s:' % _("End move Z"))
        self.endz_label.setToolTip(
            _("Height of the tool after\n"
              "the last move at the end of the job.")
        )
        self.endz_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.endz_entry.set_precision(self.decimals)

        if machinist_setting == 0:
            self.endz_entry.set_range(0.0, 10000.0000)
        else:
            self.endz_entry.set_range(-10000.0000, 10000.0000)

        self.endz_entry.setSingleStep(0.1)

        self.grid3.addWidget(self.endz_label, 11, 0)
        self.grid3.addWidget(self.endz_entry, 11, 1)

        # End Move X,Y
        endmove_xy_label = QtWidgets.QLabel('%s:' % _('End move X,Y'))
        endmove_xy_label.setToolTip(
            _("End move X,Y position. In format (x,y).\n"
              "If no value is entered then there is no move\n"
              "on X,Y plane at the end of the job.")
        )
        self.endxy_entry = NumericalEvalEntry(border_color='#0069A9')
        self.endxy_entry.setPlaceholderText(_("X,Y coordinates"))
        self.grid3.addWidget(endmove_xy_label, 12, 0)
        self.grid3.addWidget(self.endxy_entry, 12, 1)

        # Probe depth
        self.pdepth_label = QtWidgets.QLabel('%s:' % _("Probe Z depth"))
        self.pdepth_label.setToolTip(
            _("The maximum depth that the probe is allowed\n"
              "to probe. Negative value, in current units.")
        )

        self.pdepth_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.pdepth_entry.set_precision(self.decimals)
        self.pdepth_entry.set_range(-10000.0000, 10000.0000)
        self.pdepth_entry.setSingleStep(0.1)
        self.pdepth_entry.setObjectName("e_depth_probe")

        self.grid3.addWidget(self.pdepth_label, 13, 0)
        self.grid3.addWidget(self.pdepth_entry, 13, 1)

        self.pdepth_label.hide()
        self.pdepth_entry.setVisible(False)

        # Probe feedrate
        self.feedrate_probe_label = QtWidgets.QLabel('%s:' % _("Feedrate Probe"))
        self.feedrate_probe_label.setToolTip(
            _("The feedrate used while the probe is probing.")
        )

        self.feedrate_probe_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.feedrate_probe_entry.set_precision(self.decimals)
        self.feedrate_probe_entry.set_range(0.0, 10000.0000)
        self.feedrate_probe_entry.setSingleStep(0.1)
        self.feedrate_probe_entry.setObjectName("e_fr_probe")

        self.grid3.addWidget(self.feedrate_probe_label, 14, 0)
        self.grid3.addWidget(self.feedrate_probe_entry, 14, 1)

        self.feedrate_probe_label.hide()
        self.feedrate_probe_entry.setVisible(False)

        # Preprocessor Excellon selection
        pp_excellon_label = QtWidgets.QLabel('%s:' % _("Preprocessor"))
        pp_excellon_label.setToolTip(
            _("The preprocessor JSON file that dictates\n"
              "Gcode output for Excellon Objects.")
        )
        self.pp_excellon_name_cb = FCComboBox()
        self.pp_excellon_name_cb.setFocusPolicy(QtCore.Qt.StrongFocus)

        self.grid3.addWidget(pp_excellon_label, 15, 0)
        self.grid3.addWidget(self.pp_excellon_name_cb, 15, 1)

        # Preprocessor Geometry selection
        pp_geo_label = QtWidgets.QLabel('%s:' % _("Preprocessor"))
        pp_geo_label.setToolTip(
            _("The preprocessor JSON file that dictates\n"
              "Gcode output for Geometry (Milling) Objects.")
        )
        self.pp_geo_name_cb = FCComboBox()
        self.pp_geo_name_cb.setFocusPolicy(QtCore.Qt.StrongFocus)

        self.grid3.addWidget(pp_geo_label, 16, 0)
        self.grid3.addWidget(self.pp_geo_name_cb, 16, 1)

        # ------------------------------------------------------------------------------------------------------------
        # ------------------------- EXCLUSION AREAS ------------------------------------------------------------------
        # ------------------------------------------------------------------------------------------------------------

        # Exclusion Areas
        self.exclusion_cb = FCCheckBox('%s' % _("Add exclusion areas"))
        self.exclusion_cb.setToolTip(
            _(
                "Include exclusion areas.\n"
                "In those areas the travel of the tools\n"
                "is forbidden."
            )
        )
        self.grid3.addWidget(self.exclusion_cb, 20, 0, 1, 2)

        self.exclusion_frame = QtWidgets.QFrame()
        self.exclusion_frame.setContentsMargins(0, 0, 0, 0)
        self.grid3.addWidget(self.exclusion_frame, 22, 0, 1, 2)

        self.exclusion_box = QtWidgets.QVBoxLayout()
        self.exclusion_box.setContentsMargins(0, 0, 0, 0)
        self.exclusion_frame.setLayout(self.exclusion_box)

        self.exclusion_table = FCTable()
        self.exclusion_box.addWidget(self.exclusion_table)
        self.exclusion_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)

        self.exclusion_table.setColumnCount(4)
        self.exclusion_table.setColumnWidth(0, 20)
        self.exclusion_table.setHorizontalHeaderLabels(['#', _('Object'), _('Strategy'), _('Over Z')])

        self.exclusion_table.horizontalHeaderItem(0).setToolTip(_("This is the Area ID."))
        self.exclusion_table.horizontalHeaderItem(1).setToolTip(
            _("Type of the object where the exclusion area was added."))
        self.exclusion_table.horizontalHeaderItem(2).setToolTip(
            _("The strategy used for exclusion area. Go around the exclusion areas or over it."))
        self.exclusion_table.horizontalHeaderItem(3).setToolTip(
            _("If the strategy is to go over the area then this is the height at which the tool will go to avoid the "
              "exclusion area."))

        self.exclusion_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        grid_a1 = QtWidgets.QGridLayout()
        grid_a1.setColumnStretch(0, 0)
        grid_a1.setColumnStretch(1, 1)
        self.exclusion_box.addLayout(grid_a1)

        # Chose Strategy
        self.strategy_label = FCLabel('%s:' % _("Strategy"))
        self.strategy_label.setToolTip(_("The strategy followed when encountering an exclusion area.\n"
                                         "Can be:\n"
                                         "- Over -> when encountering the area, the tool will go to a set height\n"
                                         "- Around -> will avoid the exclusion area by going around the area"))
        self.strategy_radio = RadioSet([{'label': _('Over'), 'value': 'over'},
                                        {'label': _('Around'), 'value': 'around'}])

        grid_a1.addWidget(self.strategy_label, 1, 0)
        grid_a1.addWidget(self.strategy_radio, 1, 1)

        # Over Z
        self.over_z_label = FCLabel('%s:' % _("Over Z"))
        self.over_z_label.setToolTip(_("The height Z to which the tool will rise in order to avoid\n"
                                       "an interdiction area."))
        self.over_z_entry = FCDoubleSpinner()
        self.over_z_entry.set_range(0.000, 10000.0000)
        self.over_z_entry.set_precision(self.decimals)

        grid_a1.addWidget(self.over_z_label, 2, 0)
        grid_a1.addWidget(self.over_z_entry, 2, 1)

        # Button Add Area
        self.add_area_button = QtWidgets.QPushButton(_('Add Area:'))
        self.add_area_button.setToolTip(_("Add an Exclusion Area."))

        # Area Selection shape
        self.area_shape_radio = RadioSet([{'label': _("Square"), 'value': 'square'},
                                          {'label': _("Polygon"), 'value': 'polygon'}])
        self.area_shape_radio.setToolTip(
            _("The kind of selection shape used for area selection.")
        )

        grid_a1.addWidget(self.add_area_button, 4, 0)
        grid_a1.addWidget(self.area_shape_radio, 4, 1)

        h_lay_1 = QtWidgets.QHBoxLayout()
        self.exclusion_box.addLayout(h_lay_1)

        # Button Delete All Areas
        self.delete_area_button = QtWidgets.QPushButton(_('Delete All'))
        self.delete_area_button.setToolTip(_("Delete all exclusion areas."))

        # Button Delete Selected Areas
        self.delete_sel_area_button = QtWidgets.QPushButton(_('Delete Selected'))
        self.delete_sel_area_button.setToolTip(_("Delete all exclusion areas that are selected in the table."))

        h_lay_1.addWidget(self.delete_area_button)
        h_lay_1.addWidget(self.delete_sel_area_button)

        self.ois_exclusion_exc = OptionalHideInputSection(self.exclusion_cb, [self.exclusion_frame])
        # -------------------------- EXCLUSION AREAS END -------------------------------------------------------------
        # ------------------------------------------------------------------------------------------------------------

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.grid3.addWidget(separator_line, 25, 0, 1, 2)

        # #################################################################
        # ################# GRID LAYOUT 6   ###############################
        # #################################################################
        self.grid4 = QtWidgets.QGridLayout()
        self.grid4.setColumnStretch(0, 0)
        self.grid4.setColumnStretch(1, 1)
        self.tools_box.addLayout(self.grid4)

        self.generate_cnc_button = QtWidgets.QPushButton(_('Generate CNCJob object'))
        self.generate_cnc_button.setIcon(QtGui.QIcon(self.app.resource_location + '/cnc16.png'))
        self.generate_cnc_button.setToolTip(
            _("Generate the CNC Job.\n"
              "If milling then an additional Geometry object will be created.\n"
              "Add / Select at least one tool in the tool-table.\n"
              "Click the # header to select all, or Ctrl + LMB\n"
              "for custom selection of tools.")
        )
        self.generate_cnc_button.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        self.grid4.addWidget(self.generate_cnc_button, 3, 0, 1, 3)

        self.tools_box.addStretch()

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
