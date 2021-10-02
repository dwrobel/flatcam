# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File by:  Marius Adrian Stanciu (c)                      #
# Date:     6/15/2020                                      #
# License:  MIT Licence                                    #
# ##########################################################

from PyQt6 import QtWidgets, QtCore, QtGui

from appTool import AppTool
from appGUI.GUIElements import FCCheckBox, FCDoubleSpinner, RadioSet, FCTable, FCButton, \
    FCComboBox, OptionalInputSection, FCSpinner, NumericalEvalEntry, OptionalHideInputSection, FCLabel, \
    NumericalEvalTupleEntry, FCComboBox2, VerticalScrollArea, FCGridLayout, FCFrame
from appParsers.ParseExcellon import Excellon

from copy import deepcopy

import numpy as np

from shapely.geometry import LineString

import json
import sys
import re

from matplotlib.backend_bases import KeyEvent as mpl_key_event

import logging
import gettext
import appTranslation as fcTranslate
import builtins
import platform

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class ToolDrilling(AppTool, Excellon):
    builduiSig = QtCore.pyqtSignal()

    def __init__(self, app):
        self.app = app
        self.dec_format = self.app.dec_format

        AppTool.__init__(self, app)
        Excellon.__init__(self, geo_steps_per_circle=self.app.defaults["geometry_circle_steps"])

        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = None
        self.pluginName = _("Drilling")

        # #############################################################################
        # ########################## VARIABLES ########################################
        # #############################################################################
        self.units = ''
        self.excellon_tools = {}
        self.tooluid = 0
        self.kind = "excellon"

        # dict that holds the object names and the option name
        # the key is the object name (defines in ObjectUI) for each UI element that is a parameter
        # particular for a tool and the value is the actual name of the option that the UI element is changing
        self.name2option = {}

        # store here the default data for Geometry Data
        self.default_data = {}

        self.obj_name = ""
        self.excellon_obj = None

        # this holds the resulting GCode
        self.total_gcode = ''

        # this holds the resulting Parsed Gcode
        self.total_gcode_parsed = []

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

        # Tools Database
        self.tools_db_dict = None

        self.tool_form_fields = {}

        self.general_form_fields = {}

        self.name2option = {}

        self.poly_drawn = False

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Alt+D', **kwargs)

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolDrilling()")

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

        self.set_tool_ui()

        AppTool.run(self)

        self.on_object_changed()
        # self.build_tool_ui()

        # all the tools are selected by default
        self.ui.tools_table.selectAll()

        self.app.ui.notebook.setTabText(2, _("Drilling"))

    def connect_main_signals(self):
        # #############################################################################
        # ############################ SIGNALS ########################################
        # #############################################################################
        self.builduiSig.connect(self.build_tool_ui)

        self.ui.level.toggled.connect(self.on_level_changed)

        self.ui.search_load_db_btn.clicked.connect(self.on_tool_db_load)

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

        self.ui.pp_excellon_name_cb.activated.connect(self.on_pp_changed)

        self.ui.reset_button.clicked.connect(self.set_tool_ui)
        # Cleanup on Graceful exit (CTRL+ALT+X combo key)
        self.app.cleanup.connect(self.set_tool_ui)

    def disconnect_main_signals(self):
        # #############################################################################
        # ############################ SIGNALS ########################################
        # #############################################################################
        try:
            self.builduiSig.disconnect()

        except (TypeError, AttributeError):
            pass
        try:
            self.ui.level.toggled.disconnect()
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.search_load_db_btn.clicked.disconnect()
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.apply_param_to_all.clicked.disconnect()
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.generate_cnc_button.clicked.disconnect()
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.tools_table.drag_drop_sig.disconnect()
        except (TypeError, AttributeError):
            pass

        # Exclusion areas signals
        try:
            self.ui.exclusion_table.horizontalHeader().sectionClicked.disconnect()
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.exclusion_table.lost_focus.disconnect()
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.exclusion_table.itemClicked.disconnect()
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.add_area_button.clicked.disconnect()
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.delete_area_button.clicked.disconnect()
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.delete_sel_area_button.clicked.disconnect()
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.strategy_radio.activated_custom.disconnect()
        except (TypeError, AttributeError):
            pass

        try:
            self.ui.pp_excellon_name_cb.activated.disconnect()
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.reset_button.clicked.disconnect()
        except (TypeError, AttributeError):
            pass
        # Cleanup on Graceful exit (CTRL+ALT+X combo key)
        try:
            self.app.cleanup.disconnect()
        except (TypeError, AttributeError):
            pass

    def set_context_menu(self):
        # #############################################################################################################
        # ############################## EXCLUSION TABLE context menu #################################################
        # #############################################################################################################
        self.ui.exclusion_table.setupContextMenu()
        self.ui.exclusion_table.addContextMenu(
            _("Delete"), self.on_delete_sel_areas, icon=QtGui.QIcon(self.app.resource_location + "/trash16.png")
        )

    def unset_context_menu(self):
        self.ui.exclusion_table.removeContextMenu()

    def init_ui(self):
        self.ui = DrillingUI(layout=self.layout, app=self.app, name=self.pluginName)

    def set_tool_ui(self):
        self.units = self.app.app_units.upper()

        self.clear_ui(self.layout)
        self.init_ui()

        self.disconnect_main_signals()
        self.connect_main_signals()

        self.unset_context_menu()
        self.set_context_menu()

        # try to select in the Excellon combobox the active object
        try:
            selected_obj = self.app.collection.get_active()
            if selected_obj.kind == 'excellon':
                current_name = selected_obj.options['name']
                self.ui.object_combo.set_value(current_name)
        except Exception:
            pass

        try:
            loaded_obj = self.app.collection.get_by_name(self.ui.object_combo.get_value())
        except Exception as err:
            self.app.log.error("ToolDrilling -> Loaded Excellon object error. %s" % str(err))
            return

        self.tool_form_fields.update({
            "tools_drill_cutz": self.ui.cutz_entry,
            "tools_drill_multidepth": self.ui.mpass_cb,
            "tools_drill_depthperpass": self.ui.maxdepth_entry,
            "tools_drill_travelz": self.ui.travelz_entry,
            "tools_drill_feedrate_z": self.ui.feedrate_z_entry,
            "tools_drill_feedrate_rapid": self.ui.feedrate_rapid_entry,

            "tools_drill_spindlespeed": self.ui.spindlespeed_entry,
            "tools_drill_dwell": self.ui.dwell_cb,
            "tools_drill_dwelltime": self.ui.dwelltime_entry,

            "tools_drill_offset": self.ui.offset_entry,

            "tools_drill_drill_slots": self.ui.drill_slots_cb,
            "tools_drill_drill_overlap": self.ui.drill_overlap_entry,
            "tools_drill_last_drill": self.ui.last_drill_cb,
        })

        self.general_form_fields.update({
            "tools_drill_toolchange": self.ui.toolchange_cb,
            "tools_drill_toolchangez": self.ui.toolchangez_entry,
            "tools_drill_toolchangexy": self.ui.toolchangexy_entry,
            "tools_drill_startz": self.ui.estartz_entry,

            "tools_drill_endz": self.ui.endz_entry,
            "tools_drill_endxy": self.ui.endxy_entry,

            "tools_drill_z_pdepth": self.ui.pdepth_entry,
            "tools_drill_feedrate_probe": self.ui.feedrate_probe_entry,

            "tools_drill_ppname_e": self.ui.pp_excellon_name_cb,

            "tools_drill_area_exclusion": self.ui.exclusion_cb,
            "tools_drill_area_strategy": self.ui.strategy_radio,
            "tools_drill_area_overz": self.ui.over_z_entry,
            "tools_drill_area_shape": self.ui.area_shape_radio
        })

        self.name2option.update({
            "e_cutz": "tools_drill_cutz",
            "e_multidepth": "tools_drill_multidepth",
            "e_depthperpass": "tools_drill_depthperpass",
            "e_travelz": "tools_drill_travelz",
            "e_feedratez": "tools_drill_feedrate_z",
            "e_fr_rapid": "tools_drill_feedrate_rapid",

            "e_spindlespeed": "tools_drill_spindlespeed",
            "e_dwell": "tools_drill_dwell",
            "e_dwelltime": "tools_drill_dwelltime",

            "e_offset": "tools_drill_offset",

            "e_drill_slots": "tools_drill_drill_slots",
            "e_drill_slots_overlap": "tools_drill_drill_overlap",
            "e_drill_last_drill": "tools_drill_last_drill",

            # General Parameters
            "e_toolchange": "tools_drill_toolchange",
            "e_toolchangez": "tools_drill_toolchangez",
            "e_toolchangexy": "tools_drill_toolchangexy",

            "e_startz": "tools_drill_startz",

            "e_endz": "tools_drill_endz",
            "e_endxy": "tools_drill_endxy",

            "e_depth_probe": "tools_drill_z_pdepth",
            "e_fr_probe": "tools_drill_feedrate_probe",

            "e_pp": "tools_drill_ppname_e",

            "e_area_exclusion": "tools_drill_area_exclusion",
            "e_area_strategy": "tools_drill_area_strategy",
            "e_area_overz": "tools_drill_area_overz",
            "e_area_shape": "tools_drill_area_shape",
        })

        # reset the Excellon preprocessor combo
        self.ui.pp_excellon_name_cb.clear()
        # populate Excellon preprocessor combobox list
        if loaded_obj and loaded_obj.options['tools_drill_ppname_e'] == 'Check_points':
            pp_list = ['Check_points']
        else:
            pp_list = []
            for name in self.app.preprocessors.keys():
                # the HPGL preprocessor or Paste_ are not for Excellon job therefore don't add it
                if name in ['hpgl', 'Paste_1', 'Check_points']:
                    continue
                pp_list.append(name)
            pp_list.sort()
        if 'default' in pp_list:
            pp_list.remove('default')
            pp_list.insert(0, 'default')
        self.ui.pp_excellon_name_cb.addItems(pp_list)

        # add tooltips
        for it in range(self.ui.pp_excellon_name_cb.count()):
            self.ui.pp_excellon_name_cb.setItemData(it, self.ui.pp_excellon_name_cb.itemText(it), QtCore.Qt.ItemDataRole.ToolTipRole)

        self.ui.order_combo.set_value(self.app.defaults["tools_drill_tool_order"])

        if loaded_obj:
            outname = loaded_obj.options['name']
        else:
            outname = ''

        # init the working variables
        self.default_data.clear()

        # fill in self.default_data values from self.options
        # for opt_key, opt_val in self.app.options.items():
        #     if opt_key.find('excellon_') == 0:
        #         oname = opt_key[len('excellon_'):]
        #         self.default_data[oname] = deepcopy(opt_val)
        #     if opt_key.find('tools_drill_') == 0:
        #         self.default_data[opt_key] = deepcopy(opt_val)
        #     if opt_key.find('tools_mill_') == 0:
        #         self.default_data[opt_key] = deepcopy(opt_val)
        #
        if loaded_obj:
            self.default_data.update(loaded_obj.options)
        else:
            self.default_data.update(self.app.options)

        self.default_data['name'] = outname + '_drill'

        self.first_click = False
        self.cursor_pos = None
        self.mouse_is_dragging = False

        self.units = self.app.app_units.upper()

        # ########################################
        # #######3 TEMP SETTINGS #################
        # ########################################

        self.ui.tools_table.setRowCount(2)
        self.ui.tools_table.setMinimumHeight(self.ui.tools_table.getHeight())
        self.ui.tools_table.setMaximumHeight(self.ui.tools_table.getHeight())

        # make sure to update the UI on init
        try:
            self.excellon_tools = self.excellon_obj.tools
        except AttributeError:
            # no object loaded
            pass
        self.build_tool_ui()

        # #############################################################################################################
        # #############################################################################################################
        # ################################### Fill in the parameters ##################################################
        # #############################################################################################################
        # #############################################################################################################

        # tool parameters
        for key in self.tool_form_fields:
            self.tool_form_fields[key].set_value(self.default_data[key])
        # common parameters
        for key in self.general_form_fields:
            self.general_form_fields[key].set_value(self.default_data[key])

        # preprocessor
        if self.default_data["tools_drill_ppname_e"] in pp_list:
            sel_ppname_e = self.default_data["tools_drill_ppname_e"]
        else:
            sel_ppname_e = 'default'
        self.ui.pp_excellon_name_cb.set_value(sel_ppname_e)

        self.ui.drill_overlap_label.hide()
        self.ui.drill_overlap_entry.hide()
        self.ui.last_drill_cb.hide()

        # Show/Hide Advanced Options
        app_mode = self.app.defaults["global_app_level"]
        self.change_level(app_mode)

        self.ui.tools_frame.show()

        try:
            self.ui.object_combo.currentTextChanged.disconnect()
        except (AttributeError, TypeError):
            pass
        self.ui.object_combo.currentTextChanged.connect(self.on_object_changed)

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

        try:
            loaded_obj = self.app.collection.get_by_name(self.ui.object_combo.get_value())
        except Exception as err:
            self.app.log.error("ToolDrilling -> Loaded Excellon object error. %s" % str(err))
            return

        if not checked:
            self.ui.level.setText('%s' % _('Beginner'))
            self.ui.level.setStyleSheet("""
                                        QToolButton
                                        {
                                            color: green;
                                        }
                                        """)

            # Tool parameters section
            if loaded_obj:
                for tool in loaded_obj.tools:
                    tool_data = loaded_obj.tools[tool]['data']

                    tool_data['tools_drill_multidepth'] = False
                    tool_data['tools_drill_dwell'] = False
                    tool_data['tools_drill_drill_slots'] = False

                    tool_data['tools_drill_area_exclusion'] = False

            self.ui.search_load_db_btn.hide()

            self.ui.mpass_cb.hide()
            self.ui.maxdepth_entry.hide()

            self.ui.tool_offset_label.hide()
            self.ui.offset_entry.hide()

            self.ui.drill_slots_cb.set_value(False)
            self.ui.drill_slots_cb.hide()

            # All param section
            self.ui.apply_param_to_all.hide()

            # General param
            self.ui.estartz_label.hide()
            self.ui.estartz_entry.hide()
            self.ui.endmove_xy_label.hide()
            self.ui.endxy_entry.hide()

            self.ui.exclusion_cb.set_value(False)
            self.ui.exclusion_cb.hide()

        else:
            self.ui.level.setText('%s' % _('Advanced'))
            self.ui.level.setStyleSheet("""
                                        QToolButton
                                        {
                                            color: red;
                                        }
                                        """)

            # Tool parameters section
            if loaded_obj:
                options = loaded_obj.options
                for tool in loaded_obj.tools:
                    tool_data = loaded_obj.tools[tool]['data']

                    tool_data['tools_drill_multidepth'] = options['tools_drill_multidepth']
                    tool_data['tools_drill_dwell'] = options['tools_drill_dwell']
                    tool_data['tools_drill_drill_slots'] = options['tools_drill_drill_slots']

                    tool_data['tools_drill_area_exclusion'] = options['tools_drill_area_exclusion']

            self.ui.search_load_db_btn.show()

            self.ui.mpass_cb.show()
            self.ui.maxdepth_entry.show()

            self.ui.dwell_cb.show()
            self.ui.dwelltime_entry.show()

            self.ui.tool_offset_label.show()
            self.ui.offset_entry.show()

            self.ui.drill_slots_cb.show()

            # All param section
            self.ui.apply_param_to_all.show()

            # General param
            self.ui.estartz_label.show()
            self.ui.estartz_entry.show()
            self.ui.endmove_xy_label.show()
            self.ui.endxy_entry.show()

            self.ui.exclusion_cb.show()

        # update the changes in UI depending on the selected preprocessor in Preferences
        # after this moment all the changes in the Posprocessor combo will be handled by the activated signal of the
        # self.ui.pp_excellon_name_cb combobox
        self.on_pp_changed()

    def rebuild_ui(self):
        # read the table tools uid
        current_uid_list = []
        for row in range(self.ui.tools_table.rowCount()):
            try:
                uid = int(self.ui.tools_table.item(row, 3).text())
                current_uid_list.append(uid)
            except AttributeError:
                continue

        new_tools = {}
        new_uid = 1

        for current_uid in current_uid_list:
            new_tools[new_uid] = deepcopy(self.excellon_tools[current_uid])
            new_uid += 1

        self.excellon_tools = new_tools

        # the tools table changed therefore we need to rebuild it
        QtCore.QTimer.singleShot(20, self.build_tool_ui)

    def build_tool_ui(self):
        log.debug("ToolDrilling.build_tool_ui()")
        self.ui_disconnect()

        # order the tools by tool diameter if it's the case
        sorted_tools = []
        for k, v in self.excellon_tools.items():
            sorted_tools.append(self.dec_format(float(v['tooldia'])))

        order = self.ui.order_combo.get_value()
        if order == 1:  # 'fwd'
            sorted_tools.sort(reverse=False)
        elif order == 2:    # 'rev'
            sorted_tools.sort(reverse=True)
        else:
            pass

        # remake the excellon_tools dict in the order above
        new_id = 1
        new_tools = {}
        for tooldia in sorted_tools:
            for old_tool in self.excellon_tools:
                if self.dec_format(float(self.excellon_tools[old_tool]['tooldia'])) == tooldia:
                    new_tools[new_id] = deepcopy(self.excellon_tools[old_tool])
                    new_id += 1

        self.excellon_tools = new_tools

        if self.excellon_obj and self.excellon_tools:
            self.ui.exc_param_frame.setDisabled(False)
            tools = [k for k in self.excellon_tools]
        else:
            self.ui.exc_param_frame.setDisabled(True)
            self.ui.tools_table.setRowCount(2)
            tools = []

        n = len(tools)
        # we have (n+2) rows because there are 'n' tools, each a row, plus the last 2 rows for totals.
        self.ui.tools_table.setRowCount(n + 2)
        self.tool_row = 0

        tot_drill_cnt = 0
        tot_slot_cnt = 0

        for tool_no in tools:

            # Find no of drills for the current tool
            try:
                drill_cnt = len(self.excellon_tools[tool_no]["drills"])  # variable to store the nr of drills per tool
            except KeyError:
                drill_cnt = 0
            tot_drill_cnt += drill_cnt

            # Find no of slots for the current tool
            try:
                slot_cnt = len(self.excellon_tools[tool_no]["slots"])   # variable to store the nr of slots per tool
            except KeyError:
                slot_cnt = 0
            tot_slot_cnt += slot_cnt

            # Tool name/id
            exc_id_item = QtWidgets.QTableWidgetItem('%d' % int(tool_no))
            exc_id_item.setFlags(QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsDragEnabled)
            self.ui.tools_table.setItem(self.tool_row, 0, exc_id_item)

            # Tool Diameter
            dia_item = QtWidgets.QTableWidgetItem(str(self.dec_format(self.excellon_tools[tool_no]['tooldia'])))
            dia_item.setFlags(QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsDragEnabled)
            self.ui.tools_table.setItem(self.tool_row, 1, dia_item)

            # Number of drills per tool
            drill_count_item = QtWidgets.QTableWidgetItem('%d' % drill_cnt)
            drill_count_item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsDragEnabled)
            self.ui.tools_table.setItem(self.tool_row, 2, drill_count_item)

            # Tool unique ID
            tool_uid_item = QtWidgets.QTableWidgetItem(str(int(tool_no)))
            # ## REMEMBER: THIS COLUMN IS HIDDEN in UI
            self.ui.tools_table.setItem(self.tool_row, 3, tool_uid_item)

            # Number of slots per tool
            # if the slot number is zero is better to not clutter the GUI with zero's so we print a space
            slot_count_str = '%d' % slot_cnt if slot_cnt > 0 else ''
            slot_count_item = QtWidgets.QTableWidgetItem(slot_count_str)
            slot_count_item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsDragEnabled)
            self.ui.tools_table.setItem(self.tool_row, 4, slot_count_item)

            self.tool_row += 1

        # add a last row with the Total number of drills
        empty_1 = QtWidgets.QTableWidgetItem('')
        empty_1.setFlags(~QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)
        empty_1_1 = QtWidgets.QTableWidgetItem('')
        empty_1_1.setFlags(~QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)

        label_tot_drill_count = QtWidgets.QTableWidgetItem(_('Total Drills'))
        label_tot_drill_count.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)

        tot_drill_count = QtWidgets.QTableWidgetItem('%d' % tot_drill_cnt)
        tot_drill_count.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)

        self.ui.tools_table.setItem(self.tool_row, 0, empty_1)
        self.ui.tools_table.setItem(self.tool_row, 1, label_tot_drill_count)
        self.ui.tools_table.setItem(self.tool_row, 2, tot_drill_count)  # Total number of drills
        self.ui.tools_table.setItem(self.tool_row, 4, empty_1_1)

        font = QtGui.QFont()
        font.setBold(True)
        # font.setWeight(75)

        for k in [1, 2]:
            self.ui.tools_table.item(self.tool_row, k).setForeground(QtGui.QColor(127, 0, 255))
            self.ui.tools_table.item(self.tool_row, k).setFont(font)

        self.tool_row += 1

        # add a last row with the Total number of slots
        empty_2 = QtWidgets.QTableWidgetItem('')
        empty_2.setFlags(~QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)
        empty_2_1 = QtWidgets.QTableWidgetItem('')
        empty_2_1.setFlags(~QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)

        label_tot_slot_count = QtWidgets.QTableWidgetItem(_('Total Slots'))
        tot_slot_count = QtWidgets.QTableWidgetItem('%d' % tot_slot_cnt)
        label_tot_slot_count.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
        tot_slot_count.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)

        self.ui.tools_table.setItem(self.tool_row, 0, empty_2)
        self.ui.tools_table.setItem(self.tool_row, 1, label_tot_slot_count)
        self.ui.tools_table.setItem(self.tool_row, 2, empty_2_1)
        self.ui.tools_table.setItem(self.tool_row, 4, tot_slot_count)  # Total number of slots

        for kl in [1, 2, 4]:
            self.ui.tools_table.item(self.tool_row, kl).setFont(font)
            self.ui.tools_table.item(self.tool_row, kl).setForeground(QtGui.QColor(0, 70, 255))

        # make the diameter column editable
        # for row in range(self.ui.tools_table.rowCount() - 2):
        #     self.ui.tools_table.item(row, 1).setFlags(
        #         QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)

        self.ui.tools_table.resizeColumnsToContents()
        self.ui.tools_table.resizeRowsToContents()

        vertical_header = self.ui.tools_table.verticalHeader()
        vertical_header.hide()
        self.ui.tools_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        horizontal_header = self.ui.tools_table.horizontalHeader()
        self.ui.tools_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        horizontal_header.setMinimumSectionSize(10)
        horizontal_header.setDefaultSectionSize(70)

        horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Fixed)
        horizontal_header.resizeSection(0, 20)
        horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        horizontal_header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        horizontal_header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)

        self.ui.tools_table.setSortingEnabled(False)

        self.ui.tools_table.setMinimumHeight(self.ui.tools_table.getHeight())
        self.ui.tools_table.setMaximumHeight(self.ui.tools_table.getHeight())

        # all the tools are selected by default
        self.ui.tools_table.selectAll()

        # #############################################################################################################
        # ################################### Build Exclusion Areas section ###########################################
        # #############################################################################################################
        self.ui_disconnect()

        e_len = len(self.app.exc_areas.exclusion_areas_storage)
        self.ui.exclusion_table.setRowCount(e_len)

        area_id = 0

        for area in range(e_len):
            area_id += 1

            area_dict = self.app.exc_areas.exclusion_areas_storage[area]

            area_id_item = QtWidgets.QTableWidgetItem('%d' % int(area_id))
            area_id_item.setFlags(QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)
            self.ui.exclusion_table.setItem(area, 0, area_id_item)  # Area id

            object_item = QtWidgets.QTableWidgetItem('%s' % area_dict["obj_type"])
            object_item.setFlags(QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)
            self.ui.exclusion_table.setItem(area, 1, object_item)  # Origin Object

            # strategy_item = QtWidgets.QTableWidgetItem('%s' % area_dict["strategy"])
            # strategy_item.setFlags(QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)
            strategy_item = FCComboBox2(policy=False)
            strategy_item.addItems([_("Around"), _("Over")])
            idx = 0 if area_dict["strategy"] == 'around' else 1
            # protection against having this translated or loading a project with translated values
            if idx == -1:
                strategy_item.setCurrentIndex(0)
            else:
                strategy_item.setCurrentIndex(idx)
            self.ui.exclusion_table.setCellWidget(area, 2, strategy_item)  # Strategy

            overz_item = QtWidgets.QTableWidgetItem('%s' % area_dict["overz"])
            overz_item.setFlags(QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)
            self.ui.exclusion_table.setItem(area, 3, overz_item)  # Over Z

        # make the Overz column editable
        for row in range(e_len):
            self.ui.exclusion_table.item(row, 3).setFlags(QtCore.Qt.ItemFlag.ItemIsSelectable |
                                                          QtCore.Qt.ItemFlag.ItemIsEditable |
                                                          QtCore.Qt.ItemFlag.ItemIsEnabled)

        self.ui.exclusion_table.resizeColumnsToContents()
        self.ui.exclusion_table.resizeRowsToContents()

        area_vheader = self.ui.exclusion_table.verticalHeader()
        area_vheader.hide()
        self.ui.exclusion_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        area_hheader = self.ui.exclusion_table.horizontalHeader()
        area_hheader.setMinimumSectionSize(10)
        area_hheader.setDefaultSectionSize(70)

        area_hheader.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Fixed)
        area_hheader.resizeSection(0, 20)
        area_hheader.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        area_hheader.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        area_hheader.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)

        # area_hheader.setStretchLastSection(True)
        self.ui.exclusion_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

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
        elif len(sel_rows) == 1:
            # update the QLabel that shows for which Tool we have the parameters in the UI form
            toolnr = int(self.ui.tools_table.item(list(sel_rows)[0], 0).text())
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s %d</font></b>" % (_('Parameters for'), _("Tool"), toolnr)
            )

    def on_object_changed(self):
        log.debug("ToolDrilling.on_object_changed()")
        # updated units
        self.units = self.app.app_units.upper()

        # load the Excellon object
        self.obj_name = self.ui.object_combo.currentText()

        # Get source object.
        try:
            self.excellon_obj = self.app.collection.get_by_name(self.obj_name)
        except Exception:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), str(self.obj_name)))
            return

        if self.excellon_obj is None:
            self.excellon_tools = {}
            self.ui.exc_param_frame.setDisabled(True)
            self.set_tool_ui()
        else:
            self.app.collection.set_active(self.obj_name)
            self.ui.exc_param_frame.setDisabled(False)

            if self.app.defaults["excellon_autoload_db"]:
                self.excellon_tools = self.excellon_obj.tools
                self.on_tool_db_load()
            else:
                # self.on_tool_db_load() already build once the tool UI, no need to do it twice
                self.excellon_tools = self.excellon_obj.tools
                self.build_tool_ui()

        self.update_ui()

        sel_rows = set()
        table_items = self.ui.tools_table.selectedItems()
        if table_items:
            for it in table_items:
                sel_rows.add(it.row())

        if not sel_rows or len(sel_rows) == 0:
            self.ui.generate_cnc_button.setDisabled(True)
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("No Tool Selected"))
            )
        else:
            self.ui.generate_cnc_button.setDisabled(False)

    def on_object_selection_changed(self, current, previous):
        try:
            sel_obj = current.indexes()[0].internalPointer().obj
            name = sel_obj.options['name']
            kind = sel_obj.kind
            if kind in ['geometry', 'excellon']:
                self.ui.object_combo.set_value(name)
        except Exception:
            pass

    def ui_connect(self):

        # When object selection on canvas change
        # self.app.collection.view.selectionModel().selectionChanged.connect(self.on_object_selection_changed)
        self.app.proj_selection_changed.connect(self.on_object_selection_changed)

        # Area Exception - exclusion shape added signal
        # first disconnect it from any other object
        try:
            self.app.exc_areas.e_shape_modified.disconnect()
        except (TypeError, AttributeError):
            pass
        # then connect it to the current build_tool_ui() method
        self.app.exc_areas.e_shape_modified.connect(self.update_exclusion_table)

        # rows selected
        self.ui.tools_table.clicked.connect(self.on_row_selection_change)
        self.ui.tools_table.horizontalHeader().sectionClicked.connect(self.on_toggle_all_rows)

        # Tool Parameters
        for opt in self.tool_form_fields:
            current_widget = self.tool_form_fields[opt]
            if isinstance(current_widget, FCCheckBox):
                current_widget.stateChanged.connect(self.form_to_storage)
            if isinstance(current_widget, RadioSet):
                current_widget.activated_custom.connect(self.form_to_storage)
            elif isinstance(current_widget, FCDoubleSpinner) or isinstance(current_widget, FCSpinner):
                current_widget.returnPressed.connect(self.form_to_storage)
            elif isinstance(current_widget, FCComboBox):
                current_widget.currentIndexChanged.connect(self.form_to_storage)

        # General Parameters
        for opt in self.general_form_fields:
            current_widget2 = self.general_form_fields[opt]
            if isinstance(current_widget2, FCCheckBox):
                current_widget2.stateChanged.connect(self.form_to_storage)
            if isinstance(current_widget2, RadioSet):
                current_widget2.activated_custom.connect(self.form_to_storage)
            elif isinstance(current_widget2, FCDoubleSpinner) or isinstance(current_widget2, FCSpinner):
                current_widget2.returnPressed.connect(self.form_to_storage)
            elif isinstance(current_widget2, FCComboBox):
                current_widget2.currentIndexChanged.connect(self.form_to_storage)
            elif isinstance(current_widget2, NumericalEvalEntry):
                current_widget2.editingFinished.connect(self.form_to_storage)
            elif isinstance(current_widget2, NumericalEvalTupleEntry):
                current_widget2.editingFinished.connect(self.form_to_storage)

        self.ui.order_combo.currentIndexChanged.connect(self.on_order_changed)

        # Exclusion Table widgets connect
        for row in range(self.ui.exclusion_table.rowCount()):
            self.ui.exclusion_table.cellWidget(row, 2).currentIndexChanged.connect(self.on_exclusion_table_strategy)

        self.ui.exclusion_table.itemChanged.connect(self.on_exclusion_table_overz)

    def ui_disconnect(self):
        # When object selection on canvas change
        # self.app.collection.view.selectionModel().selectionChanged.disconnect()
        try:
            self.app.proj_selection_changed.disconnect()
        except (TypeError, AttributeError):
            pass

        # rows selected
        try:
            self.ui.tools_table.clicked.disconnect(self.on_row_selection_change)
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.tools_table.horizontalHeader().sectionClicked.disconnect(self.on_toggle_all_rows)
        except (TypeError, AttributeError):
            pass

        # tool table widgets
        for row in range(self.ui.tools_table.rowCount()):

            try:
                self.ui.tools_table.cellWidget(row, 2).currentIndexChanged.disconnect()
            except (TypeError, AttributeError):
                pass

        # Tool Parameters
        for opt in self.tool_form_fields:
            current_widget = self.tool_form_fields[opt]
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

        # General Parameters
        for opt in self.general_form_fields:
            current_widget2 = self.general_form_fields[opt]
            if isinstance(current_widget2, FCCheckBox):
                try:
                    current_widget2.stateChanged.disconnect(self.form_to_storage)
                except (TypeError, ValueError):
                    pass
            if isinstance(current_widget2, RadioSet):
                try:
                    current_widget2.activated_custom.disconnect(self.form_to_storage)
                except (TypeError, ValueError):
                    pass
            elif isinstance(current_widget2, FCDoubleSpinner) or isinstance(current_widget2, FCSpinner):
                try:
                    current_widget2.returnPressed.disconnect(self.form_to_storage)
                except (TypeError, ValueError):
                    pass
            elif isinstance(current_widget2, FCComboBox):
                try:
                    current_widget2.currentIndexChanged.disconnect(self.form_to_storage)
                except (TypeError, ValueError):
                    pass
            elif isinstance(current_widget2, NumericalEvalEntry):
                try:
                    current_widget2.editingFinished.disconnect(self.form_to_storage)
                except (TypeError, ValueError):
                    pass
            elif isinstance(current_widget2, NumericalEvalTupleEntry):
                try:
                    current_widget2.editingFinished.disconnect(self.form_to_storage)
                except (TypeError, ValueError):
                    pass
        try:
            self.ui.order_combo.currentIndexChanged.disconnect()
        except (TypeError, ValueError):
            pass

        # Exclusion Table widgets disconnect
        for row in range(self.ui.exclusion_table.rowCount()):
            try:
                self.ui.exclusion_table.cellWidget(row, 2).currentIndexChanged.disconnect()
            except (TypeError, AttributeError):
                pass

        try:
            self.ui.exclusion_table.itemChanged.disconnect()
        except (TypeError, AttributeError):
            pass

    def on_tool_db_load(self):

        filename = self.app.tools_database_path()

        # load the database tools from the file
        try:
            with open(filename) as f:
                tools = f.read()
        except IOError:
            self.app.log.error("Could not load tools DB file.")
            self.app.inform.emit('[ERROR] %s' % _("Could not load Tools DB file."))
            return

        try:
            self.tools_db_dict = json.loads(tools)
        except Exception:
            e = sys.exc_info()[0]
            self.app.log.error(str(e))
            self.app.inform.emit('[ERROR] %s' % _("Failed to parse Tools DB file."))
            return

        if not self.tools_db_dict:
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Tools DB empty."))
            return

        self.replace_tools()

    def replace_tools(self):
        log.debug("ToolDrilling.replace_tools()")

        if self.excellon_obj:
            new_tools_dict = deepcopy(self.excellon_tools)

            for orig_tool, orig_tool_val in self.excellon_tools.items():
                orig_tooldia = orig_tool_val['tooldia']

                tool_found = 0

                # look in database tools
                for db_tool, db_tool_val in self.tools_db_dict.items():
                    db_tooldia = db_tool_val['tooldia']
                    low_limit = float(db_tool_val['data']['tol_min'])
                    high_limit = float(db_tool_val['data']['tol_max'])

                    # test if the targeted tool is Drilling Tool, if not, skip to next tool
                    targeted_tool = db_tool_val['data']['tool_target']
                    if targeted_tool != _("Drilling"):
                        continue

                    # if we find a tool with the same diameter in the Tools DB just update it's data
                    if orig_tooldia == db_tooldia:
                        tool_found += 1
                        for d in db_tool_val['data']:
                            if d.find('tools_drill_') == 0:
                                new_tools_dict[orig_tool]['data'][d] = db_tool_val['data'][d]
                            elif d.find('tools_') == 0:
                                # don't need data for other App Tools; this tests after 'tools_drill_'
                                continue
                            else:
                                new_tools_dict[orig_tool]['data'][d] = db_tool_val['data'][d]
                    # search for a tool that has a tolerance that the tool fits in
                    elif high_limit >= orig_tooldia >= low_limit:
                        tool_found += 1
                        new_tools_dict[orig_tool]['tooldia'] = db_tooldia
                        for d in db_tool_val['data']:
                            if d.find('tools_drill_') == 0:
                                new_tools_dict[orig_tool]['data'][d] = db_tool_val['data'][d]
                            elif d.find('tools_') == 0:
                                # don't need data for other App Tools; this tests after 'tools_drill_'
                                continue
                            else:
                                new_tools_dict[orig_tool]['data'][d] = db_tool_val['data'][d]

                if tool_found > 1:
                    self.app.inform.emit(
                        '[WARNING_NOTCL] %s' % _("Cancelled.\n"
                                                 "Multiple tools for one tool diameter found in Tools Database."))
                    self.blockSignals(False)
                    return

            self.excellon_tools = new_tools_dict
            self.build_tool_ui()

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
            self.ui.exc_param_frame.setDisabled(True)

            self.ui.generate_cnc_button.setDisabled(True)
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("No Tool Selected"))
            )
        else:
            self.ui.tools_table.selectAll()
            self.ui.exc_param_frame.setDisabled(False)
            self.ui.generate_cnc_button.setDisabled(False)
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
        if len(sel_rows) <= 1:
            self.update_ui()

    def update_ui(self):
        self.blockSignals(True)
        self.ui_disconnect()

        sel_rows = set()
        table_items = self.ui.tools_table.selectedItems()
        if table_items:
            for it in table_items:
                sel_rows.add(it.row())
            # sel_rows = sorted(set(index.row() for index in self.ui.tools_table.selectedIndexes()))

        if not sel_rows or len(sel_rows) == 0:
            self.ui.generate_cnc_button.setDisabled(True)
            self.ui.exc_param_frame.setDisabled(True)
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("No Tool Selected"))
            )
            self.blockSignals(False)
            self.ui_connect()
            return
        else:
            self.ui.generate_cnc_button.setDisabled(False)
            self.ui.exc_param_frame.setDisabled(False)

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

        # populate the form with the data from the tool associated with the row parameter for the last row selected
        try:
            item = self.ui.tools_table.item(list(sel_rows)[-1], 3)
            if type(item) is not None:
                tooluid = int(item.text())
                self.storage_to_form(self.excellon_tools[tooluid]['data'])
            else:
                self.blockSignals(False)
                self.ui_connect()
                return
        except Exception as e:
            log.error("Tool missing. Add a tool in the Tool Table. %s" % str(e))
            self.blockSignals(False)
            self.ui_connect()
            return
        self.blockSignals(False)
        self.ui_connect()

    def storage_to_form(self, dict_storage):
        """
        Will update the GUI with data from the "storage" in this case the dict self.tools

        :param dict_storage:    A dictionary holding the data relevant for gnerating Gcode from Excellon
        :type dict_storage:     dict
        :return:                None
        :rtype:
        """

        general_keys = list(self.general_form_fields.keys())
        tool_keys = list(self.tool_form_fields.keys())

        # update the Tool parameters
        for form_key in self.tool_form_fields:
            for storage_key in dict_storage:
                if form_key == storage_key and form_key not in general_keys:
                    try:
                        self.tool_form_fields[form_key].set_value(dict_storage[form_key])
                    except Exception as e:
                        log.error("ToolDrilling.storage_to_form() tool parameters --> %s" % str(e))
                        pass

        # update the Common parameters
        for form_key in self.general_form_fields:
            for storage_key in dict_storage:
                if form_key == storage_key and form_key not in tool_keys:
                    try:
                        self.general_form_fields[form_key].set_value(dict_storage[form_key])
                    except Exception as e:
                        log.error("ToolDrilling.storage_to_form() -> common parameters --> %s" % str(e))
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

        self.ui_disconnect()

        widget_changed = self.sender()
        wdg_objname = widget_changed.objectName()
        option_changed = self.name2option[wdg_objname]

        # row = self.ui.tools_table.currentRow()
        rows = sorted(list(set(index.row() for index in self.ui.tools_table.selectedIndexes())))
        for row in rows:
            if row < 0:
                row = 0
            tooluid_item = int(self.ui.tools_table.item(row, 3).text())

            # update tool parameters
            for tooluid_key, tooluid_val in self.excellon_tools.items():
                if int(tooluid_key) == tooluid_item:
                    if option_changed in self.tool_form_fields:
                        new_option_value = self.tool_form_fields[option_changed].get_value()
                        if option_changed in tooluid_val:
                            self.excellon_tools[tooluid_key][option_changed] = new_option_value
                        if option_changed in tooluid_val['data']:
                            self.excellon_tools[tooluid_key]['data'][option_changed] = new_option_value

        # update general parameters
        # they are updated for all tools
        for tooluid_key, tooluid_val in self.excellon_tools.items():
            if option_changed in self.general_form_fields:
                new_option_value = self.general_form_fields[option_changed].get_value()
                if option_changed in tooluid_val:
                    self.excellon_tools[tooluid_key][option_changed] = new_option_value
                if option_changed in tooluid_val['data']:
                    self.excellon_tools[tooluid_key]['data'][option_changed] = new_option_value
        self.ui_connect()

    def get_selected_tools_table_items(self):
        """
        Returns a list of lists, each list in the list is made out of row elements

        :return:    List of table_tools items.
        :rtype:     list
        """
        table_tools_items = []

        rows = set()
        for x in self.ui.tools_table.selectedItems():
            rows.add(x.row())

        for row in rows:
            txt = ''
            elem = []

            for column in range(self.ui.tools_table.columnCount()):
                if column == 3:
                    # disregard this column since it's the toolID
                    continue

                try:
                    txt = self.ui.tools_table.item(row, column).text()
                except AttributeError:
                    try:
                        txt = self.ui.tools_table.cellWidget(row, column).currentText()
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

        for tooluid_key, tooluid_val in self.excellon_tools.items():
            if int(tooluid_key) == tooluid_item:
                # this will hold the 'data' key of the self.tools[tool] dictionary that corresponds to
                # the current row in the tool table
                temp_tool_data = tooluid_val['data']
                break

        for tooluid_key, tooluid_val in self.excellon_tools.items():
            tooluid_val['data'] = deepcopy(temp_tool_data)

        self.app.inform.emit('[success] %s' % _("Current Tool parameters were applied to all tools."))
        self.blockSignals(False)

    def on_order_changed(self, order):
        if order != 0:  # 'default'
            self.build_tool_ui()

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

            self.excellon_tools[current_uid].update({
                'type': typ,
                'tool_type': tt,
            })

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

        if 'marlin' in current_pp.lower():
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
                self.ui.travelzlabel.show()
                self.ui.travelz_entry.show()

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

            # if in Advanced Mode
            if self.ui.level.isChecked():
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

            self.ui.spindle_label.setText('%s:' % _('Spindle speed'))

            # if in Advanced Mode
            if self.ui.level.isChecked():
                self.ui.dwell_cb.show()
                self.ui.dwelltime_entry.show()

                try:
                    self.ui.tool_offset_label.show()
                    self.ui.offset_entry.show()
                except AttributeError:
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
            self.points = []
            self.poly_drawn = False
            self.delete_moving_selection_shape()
            self.delete_tool_selection_shape()

    def on_add_area_click(self):
        shape_button = self.ui.area_shape_radio
        overz_button = self.ui.over_z_entry
        strategy_radio = self.ui.strategy_radio
        cnc_button = self.ui.generate_cnc_button
        solid_geo = self.excellon_obj.solid_geometry
        obj_type = self.excellon_obj.kind

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

        self.build_tool_ui()
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

    def on_exclusion_table_overz(self, current_item):
        self.ui_disconnect()

        current_row = current_item.row()
        try:
            d = float(self.ui.exclusion_table.item(current_row, 3).text())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                d = float(self.ui.exclusion_table.item(current_row, 3).text().replace(',', '.'))
            except ValueError:
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("Wrong value format entered, use a number."))
                return
        except AttributeError:
            self.ui_connect()
            return

        overz = self.app.dec_format(d, self.decimals)
        idx = int(self.ui.exclusion_table.item(current_row, 0).text())

        for area_dict in self.app.exc_areas.exclusion_areas_storage:
            if area_dict['idx'] == idx:
                area_dict['overz'] = overz

        self.app.inform.emit('[success] %s' % _("Value edited in Exclusion Table."))
        self.ui_connect()
        self.builduiSig.emit()

    def on_exclusion_table_strategy(self):
        cw = self.sender()
        cw_index = self.ui.exclusion_table.indexAt(cw.pos())
        cw_row = cw_index.row()
        idx = int(self.ui.exclusion_table.item(cw_row, 0).text())

        for area_dict in self.app.exc_areas.exclusion_areas_storage:
            if area_dict['idx'] == idx:
                strategy = self.ui.exclusion_table.cellWidget(cw_row, 2).currentIndex()
                area_dict['strategy'] = "around" if strategy == 0 else 'overz'

        self.app.inform.emit('[success] %s' % _("Value edited in Exclusion Table."))
        self.ui_connect()
        self.builduiSig.emit()

    @staticmethod
    def process_slot_as_drills(slot, overlap, add_last_pt=False):

        drills_list = []
        start_pt = slot[0]
        stop_pt = slot[1]
        slot_line = LineString([start_pt, stop_pt])
        drills_list.append(start_pt)

        ii = 0
        while True:
            ii += 1
            target = overlap * ii
            new_pt = slot_line.interpolate(target)
            if new_pt.within(slot_line) is False:
                break
            drills_list.append(new_pt)

        if add_last_pt and stop_pt.distance(drills_list[-1]) >= overlap/10:
            drills_list.append(stop_pt)
        return drills_list

    def is_valid_excellon(self):
        slots_as_drills = self.ui.drill_slots_cb.get_value()

        has_drills = None
        for tool_key, tool_dict in self.excellon_tools.items():
            if 'drills' in tool_dict and tool_dict['drills']:
                has_drills = True
                break
        has_slots = None
        for tool_key, tool_dict in self.excellon_tools.items():
            if 'slots' in tool_dict and tool_dict['slots']:
                has_slots = True
                break

        if not has_drills:
            if slots_as_drills and has_slots:
                return True
            else:
                return False

    def get_selected_tools_uid(self):
        """
        Return a list of the selected tools UID from the Tool Table
        """
        selected_uid = set()
        for sel_it in self.ui.tools_table.selectedItems():
            uid = int(self.ui.tools_table.item(sel_it.row(), 3).text())
            selected_uid.add(uid)
        return list(selected_uid)

    def create_drill_points(self, selected_tools, selected_sorted_tools):
        points = {}

        # create drill points out of the drills locations
        for tool_key, tl_dict in self.excellon_tools.items():
            if tool_key in selected_tools:
                if 'drills' in tl_dict and tl_dict['drills']:
                    for drill_pt in tl_dict['drills']:
                        try:
                            points[tool_key].append(drill_pt)
                        except KeyError:
                            points[tool_key] = [drill_pt]

        log.debug("Found %d TOOLS with drills." % len(points))

        # #############################################################################################################
        # ############ SLOTS TO DRILLS CONVERSION SECTION #############################################################
        # #############################################################################################################

        # convert slots to a sequence of drills and add them to drill points
        should_add_last_pt = self.ui.last_drill_cb.get_value()

        for tool_key, tl_dict in self.excellon_tools.items():
            convert_slots = tl_dict['data']['tools_drill_drill_slots']
            if convert_slots:
                if tool_key in selected_tools:
                    overlap = 1 - (self.ui.drill_overlap_entry.get_value() / 100.0)
                    drill_overlap = 0.0
                    for i in selected_sorted_tools:
                        if i[0] == tool_key:
                            slot_tool_dia = i[1]
                            drill_overlap = overlap * slot_tool_dia
                            break

                    new_drills = []
                    if 'slots' in tl_dict and tl_dict['slots']:
                        for slot in tl_dict['slots']:
                            new_drills += self.process_slot_as_drills(slot=slot, overlap=drill_overlap,
                                                                      add_last_pt=should_add_last_pt)
                        if new_drills:
                            try:
                                points[tool_key] += new_drills
                            except Exception:
                                points[tool_key] = new_drills
        log.debug("Found %d TOOLS with drills after converting slots to drills." % len(points))

        return points

    def check_intersection(self, points):
        for tool_key in points:
            for pt in points[tool_key]:
                for area in self.app.exc_areas.exclusion_areas_storage:
                    pt_buf = pt.buffer(self.excellon_tools[tool_key]['tooldia'] / 2.0)
                    if pt_buf.within(area['shape']) or pt_buf.intersects(area['shape']):
                        return True
        return False

    def on_cnc_button_click(self):
        obj_name = self.ui.object_combo.currentText()
        toolchange = self.ui.toolchange_cb.get_value()

        # Get source object.
        try:
            obj = self.app.collection.get_by_name(obj_name)
        except Exception:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), str(obj_name)))
            return

        if obj is None:
            self.app.inform.emit('[ERROR_NOTCL] %s.' % _("Object not found"))
            return

        # update the Excellon Tools
        # we don't do it here since it will break any changes we've done in the Drilling Tool UI
        # self.excellon_tools = obj.tools

        xmin = obj.options['xmin']
        ymin = obj.options['ymin']
        xmax = obj.options['xmax']
        ymax = obj.options['ymax']

        job_name = obj.options["name"] + "_cnc"
        obj.pp_excellon_name = self.ui.pp_excellon_name_cb.get_value()

        if self.is_valid_excellon() is False:
            log.debug("camlib.CNCJob.generate_from_excellon_by_tool() --> "
                      "The loaded Excellon file has no drills ...")
            self.app.inform.emit('[ERROR_NOTCL] %s...' % _('The loaded Excellon file has no drills'))
            return

        # Get the tools from the Tool Table
        selected_tools_id = self.get_selected_tools_uid()
        if not selected_tools_id:
            # if there is a single tool in the table (remember that the last 2 rows are for totals and do not count in
            # tool number) it means that there are 3 rows (1 tool and 2 totals).
            # in this case regardless of the selection status of that tool, use it.
            if self.ui.tools_table.rowCount() == 3:
                selected_tools_id.append(int(self.ui.tools_table.item(0, 3).text()))
            else:
                msg = '[ERROR_NOTCL] %s' % _("Please select one or more tools from the list and try again.")
                self.app.inform.emit(msg)
                return

        # #############################################################################################################
        # #############################################################################################################
        # TOOLS
        # sort the tools list by the second item in tuple (here we have a dict with diameter of the tool)
        # so we actually are sorting the tools by diameter
        # #############################################################################################################
        # #############################################################################################################
        all_tools = []
        for tool_as_key, v in list(self.excellon_tools.items()):
            all_tools.append((int(tool_as_key), float(v['tooldia'])))

        order = self.ui.order_combo.get_value()
        if order == 'fwd':
            sorted_tools = sorted(all_tools, key=lambda t1: t1[1])
        elif order == 'rev':
            sorted_tools = sorted(all_tools, key=lambda t1: t1[1], reverse=True)
        else:
            sorted_tools = all_tools

        # Create a sorted list of selected sel_tools from the sorted_tools list
        sel_tools = [i for i, j in sorted_tools for k in selected_tools_id if i == k]

        log.debug("Tools sorted are: %s" % str(sel_tools))

        # #############################################################################################################
        # #############################################################################################################
        # #### Create Points (Group by tool): a dictionary of shapely Point geo elements grouped by tool number #######
        # #############################################################################################################
        # #############################################################################################################
        self.app.inform.emit(_("Creating a list of points to drill..."))

        # points is a dictionary: keys are tools ad values are lists of Shapely Points
        points = self.create_drill_points(selected_tools=sel_tools, selected_sorted_tools=sorted_tools)

        # check if there are drill points in the exclusion areas (if any areas)
        if self.app.exc_areas.exclusion_areas_storage and self.check_intersection(points) is True:
            self.app.inform.emit("[ERROR_NOTCL] %s" % _("Failed. Drill points inside the exclusion zones."))
            return 'fail'

        # #############################################################################################################
        # General Parameters
        # #############################################################################################################
        used_exc_optim_type = self.app.defaults["excellon_optimization_type"]
        current_platform = platform.architecture()[0]
        if current_platform != '64bit':
            used_exc_optim_type = 'T'

        # #############################################################################################################
        # #############################################################################################################
        # GCODE creation
        # #############################################################################################################
        # #############################################################################################################
        self.app.inform.emit('%s...' % _("Starting G-Code"))

        # Object initialization function for app.app_obj.new_object()
        def job_init(job_obj, app_obj):
            assert job_obj.kind == 'cncjob', "Initializer expected a CNCJobObject, got %s" % type(job_obj)
            app_obj.inform.emit(_("Generating CNCJob..."))

            # #########################################################################################################
            # #########################################################################################################
            # fill the data into the self.tools dictionary attribute of the CNCJob object
            # #########################################################################################################
            # #########################################################################################################
            job_obj.tools = {}
            for sel_id in sorted_tools:
                for t_id in self.excellon_tools:
                    selected_id = sel_id[0]
                    selected_tooldia = sel_id[1]

                    if selected_id == t_id:
                        job_obj.tools[selected_id] = deepcopy(self.excellon_tools[selected_id])
                        sol_geo = []

                        # solid geometry addition; we look into points because we may have slots converted to drills
                        # therefore more drills than there were originally in
                        # the self.excellon_tools[to_ol]['drills'] list
                        drill_no = 0
                        if selected_id in points and points[selected_id]:
                            drill_no = len(points[selected_id])
                            for drill in points[selected_id]:
                                sol_geo.append(
                                    drill.buffer((selected_tooldia / 2.0), resolution=job_obj.geo_steps_per_circle)
                                )

                        slot_no = 0
                        convert_slots = self.excellon_tools[selected_id]['data']['tools_drill_drill_slots']
                        if 'slots' in self.excellon_tools[selected_id] and convert_slots is False:
                            slot_no = len(self.excellon_tools[selected_id]['slots'])
                            for eslot in self.excellon_tools[selected_id]['slots']:
                                start = (eslot[0].x, eslot[0].y)
                                stop = (eslot[1].x, eslot[1].y)
                                line_geo = LineString([start, stop])
                                sol_geo.append(
                                    line_geo.buffer((selected_tooldia / 2.0), resolution=job_obj.geo_steps_per_circle)
                                )

                        # adjust Offset for current tool
                        try:
                            z_off = float(self.excellon_tools[selected_id]['data']['offset']) * (-1)
                        except KeyError:
                            z_off = 0

                        job_obj.tools[selected_id]['nr_drills'] = drill_no
                        job_obj.tools[selected_id]['nr_slots'] = slot_no
                        job_obj.tools[selected_id]['offset'] = z_off
                        job_obj.tools[selected_id]['gcode'] = ''
                        job_obj.tools[selected_id]['gcode_parsed'] = []
                        job_obj.tools[selected_id]['solid_geometry'] = deepcopy(sol_geo)

            # #########################################################################################################
            # #########################################################################################################
            # Initialization
            # #########################################################################################################
            # #########################################################################################################
            # Preprocessor
            job_obj.pp_excellon_name = self.ui.pp_excellon_name_cb.get_value()
            job_obj.pp_excellon = self.app.preprocessors[job_obj.pp_excellon_name]

            job_obj.options['type'] = 'Excellon'
            job_obj.options['ppname_e'] = obj.pp_excellon_name

            job_obj.options['xmin'] = xmin
            job_obj.options['ymin'] = ymin
            job_obj.options['xmax'] = xmax
            job_obj.options['ymax'] = ymax

            job_obj.use_ui = True

            job_obj.coords_decimals = int(self.app.defaults["cncjob_coords_decimals"])
            job_obj.fr_decimals = int(self.app.defaults["cncjob_fr_decimals"])
            job_obj.multitool = True

            # it does not matter for the Excellon codes because we are not going to autolevel GCode out of Excellon
            # but it is here for uniformity between the Geometry and Excellon objects
            job_obj.segx = self.app.defaults["geometry_segx"]
            job_obj.segy = self.app.defaults["geometry_segy"]

            # first drill point
            # I can read the toolchange x,y point from any tool since it is the same for all, so I read it
            # from the first tool
            job_obj.xy_toolchange = job_obj.tools[1]['data']["tools_drill_toolchangexy"]

            x_tc, y_tc = [0, 0]
            try:
                if job_obj.xy_toolchange != '':
                    tcxy_temp = re.sub('[()\[\]]', '', str(job_obj.xy_toolchange))
                    if tcxy_temp:
                        x_tc, y_tc = [float(eval(a)) for a in tcxy_temp.split(",")]
            except Exception:
                x_tc, y_tc = [0, 0]
                self.app.inform.emit('[ERROR]%s' % _("The Toolchange X,Y format has to be (x, y)."))

            job_obj.oldx = x_tc
            job_obj.oldy = y_tc
            first_drill_point = (job_obj.oldx, job_obj.oldy)

            # #########################################################################################################
            # ####################### NO TOOLCHANGE ###################################################################
            # #########################################################################################################
            if toolchange is False:
                tool_points = []
                for tool in sel_tools:
                    if tool in points:
                        tool_points += points[tool]

                # use the first tool in the selection as the tool that we are going to use
                used_tool = sel_tools[0]
                used_tooldia = self.excellon_tools[used_tool]['tooldia']

                # those are used by the preprocessors to display data on the toolchange line
                job_obj.tool = used_tool
                job_obj.postdata['toolC'] = used_tooldia

                # generate GCode
                tool_gcode, __, start_gcode = job_obj.excellon_tool_gcode_gen(used_tool, tool_points,
                                                                              job_obj.tools,
                                                                              first_pt=first_drill_point,
                                                                              is_first=True,
                                                                              is_last=True,
                                                                              opt_type=used_exc_optim_type,
                                                                              toolchange=False)

                # parse the Gcode
                tool_gcode_parsed = job_obj.excellon_tool_gcode_parse(used_tooldia, gcode=tool_gcode,
                                                                      start_pt=first_drill_point)

                # store the results in Excellon CNC tools storage
                job_obj.tools[used_tool]['gcode'] = tool_gcode
                job_obj.tools[used_tool]['gcode_parsed'] = tool_gcode_parsed

                if start_gcode != '':
                    job_obj.gc_start = start_gcode

                self.total_gcode = tool_gcode
                self.total_gcode_parsed = tool_gcode_parsed

            # ####################### TOOLCHANGE ACTIVE ######################################################
            else:
                for tool_id in sel_tools:
                    tool_points = []
                    if tool_id in points:
                        tool_points = points[tool_id]
                    used_tooldia = self.excellon_tools[tool_id]['tooldia']

                    # those are used by the preprocessors to display data on the toolchange line
                    job_obj.tool = tool_id
                    job_obj.postdata['toolC'] = used_tooldia

                    # if slots are converted to drill for this tool, update the number of drills and make slots nr zero
                    convert_slots = self.excellon_tools[tool_id]['data']['tools_drill_drill_slots']
                    if convert_slots is True:
                        nr_drills = len(tool_points)
                        nr_slots = 0
                        job_obj.tools[used_tooldia]['nr_drills'] = nr_drills
                        job_obj.tools[used_tooldia]['nr_slots'] = nr_slots

                    # calculate if the current tool is the first one or if it is the last one
                    # for the first tool we add some extra GCode (start Gcode, header etc)
                    # for the last tool we add other GCode (the end code, what is happening at the end of the job)
                    is_last_tool = True if tool_id == sel_tools[-1] else False
                    is_first_tool = True if tool_id == sel_tools[0] else False

                    if not tool_points:
                        self.app.log.debug("%s" % "Tool has no drill points. Skipping.")
                        continue

                    # Generate Gcode for the current tool
                    tool_gcode, last_pt, start_gcode = job_obj.excellon_tool_gcode_gen(tool_id, tool_points,
                                                                                       self.excellon_tools,
                                                                                       first_pt=first_drill_point,
                                                                                       is_first=is_first_tool,
                                                                                       is_last=is_last_tool,
                                                                                       opt_type=used_exc_optim_type,
                                                                                       toolchange=True)

                    # parse Gcode for the current tool
                    tool_gcode_parsed = job_obj.excellon_tool_gcode_parse(used_tooldia, gcode=tool_gcode,
                                                                          start_pt=first_drill_point)
                    first_drill_point = last_pt

                    # store the results of GCode generation and parsing
                    job_obj.tools[tool_id]['gcode'] = tool_gcode
                    job_obj.tools[tool_id]['gcode_parsed'] = tool_gcode_parsed

                    if start_gcode != '':
                        job_obj.gc_start = start_gcode

                    self.total_gcode += tool_gcode
                    self.total_gcode_parsed += tool_gcode_parsed

            job_obj.gcode = self.total_gcode
            job_obj.source_file = self.total_gcode
            job_obj.gcode_parsed = self.total_gcode_parsed
            if job_obj.gcode == 'fail':
                return 'fail'

            # create Geometry for plotting
            # FIXME is it necessary? didn't we do it previously when filling data in self.tools dictionary?
            job_obj.create_geometry()

            if used_exc_optim_type == 'M':
                log.debug("The total travel distance with OR-TOOLS Metaheuristics is: %s" %
                          str(job_obj.measured_distance))
            elif used_exc_optim_type == 'B':
                log.debug("The total travel distance with OR-TOOLS Basic Algorithm is: %s" %
                          str(job_obj.measured_distance))
            elif used_exc_optim_type == 'T':
                log.debug(
                    "The total travel distance with Travelling Salesman Algorithm is: %s" %
                    str(job_obj.measured_distance))
            else:
                log.debug("The total travel distance with with no optimization is: %s" %
                          str(job_obj.measured_distance))

            # #########################################################################################################
            # ############################# Calculate DISTANCE and ESTIMATED TIME #####################################
            # #########################################################################################################
            if job_obj.xy_end is None:
                job_obj.xy_end = [job_obj.oldx, job_obj.oldy]

            job_obj.measured_distance += abs(distance_euclidian(
                job_obj.oldx, job_obj.oldy, job_obj.xy_end[0], job_obj.xy_end[1])
            )
            log.debug("The total travel distance including travel to end position is: %s" %
                      str(job_obj.measured_distance) + '\n')
            job_obj.travel_distance = job_obj.measured_distance

            # I use the value of self.feedrate_rapid for the feadrate in case of the measure_lift_distance and for
            # traveled_time because it is not always possible to determine the feedrate that the CNC machine uses
            # for G0 move (the fastest speed available to the CNC router). Although self.feedrate_rapids is used only
            # with Marlin preprocessor and derivatives.
            job_obj.routing_time = \
                (job_obj.measured_down_distance + job_obj.measured_up_to_zero_distance) / job_obj.z_feedrate
            lift_time = job_obj.measured_lift_distance / job_obj.feedrate_rapid
            traveled_time = job_obj.measured_distance / job_obj.feedrate_rapid
            job_obj.routing_time += lift_time + traveled_time

        # To be run in separate thread
        def job_thread(a_obj):
            with self.app.proc_container.new(_("Generating CNC Code")):
                a_obj.app_obj.new_object("cncjob", job_name, job_init)

            # Switch notebook to Properties page
            self.app.ui.notebook.setCurrentWidget(self.app.ui.properties_tab)

        # Create promise for the new name.
        self.app.collection.promise(job_name)

        # Send to worker
        # self.app.worker.add_task(job_thread, [self.app])
        self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})

    def reset_fields(self):
        self.object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))


class DrillingUI:

    def __init__(self, layout, app, name):
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
        title_label = FCLabel("%s" % name)
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
        self.level = QtWidgets.QToolButton()
        self.level.setToolTip(
            _(
                "Beginner Mode - many parameters are hidden.\n"
                "Advanced Mode - full control.\n"
                "Permanent change is done in 'Preferences' menu."
            )
        )
        # self.level.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.level.setCheckable(True)
        self.title_box.addWidget(self.level)

        # #############################################################################################################
        # Excellon Source Object Frame
        # #############################################################################################################
        self.obj_combo_label = FCLabel('<span style="color:darkorange;"><b>%s</b></span>' % _("Source Object"))
        self.obj_combo_label.setToolTip(
            _("Excellon object for drilling/milling operation.")
        )
        self.tools_box.addWidget(self.obj_combo_label)

        # Grid Layout
        obj_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        self.tools_box.addLayout(obj_grid)

        # ################################################
        # ##### The object to be drilled #################
        # ################################################
        self.object_combo = FCComboBox()
        self.object_combo.setModel(self.app.collection)
        self.object_combo.setRootModelIndex(self.app.collection.index(1, 0, QtCore.QModelIndex()))
        # self.object_combo.setCurrentIndex(1)
        self.object_combo.is_last = True

        obj_grid.addWidget(self.object_combo, 0, 0, 1, 2)

        # separator_line = QtWidgets.QFrame()
        # separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        # separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        # obj_grid.addWidget(separator_line, 2, 0, 1, 2)

        # #############################################################################################################
        # Excellon Tool Table Frame
        # #############################################################################################################
        self.tools_table_label = FCLabel('<span style="color:green;"><b>%s</b></span>' % _('Tools Table'))
        self.tools_table_label.setToolTip(_("Tools in the object used for drilling."))
        self.tools_box.addWidget(self.tools_table_label)

        tt_frame = FCFrame()
        self.tools_box.addWidget(tt_frame)

        tool_grid = FCGridLayout(v_spacing=5, h_spacing=3, c_stretch=[0, 0])
        tt_frame.setLayout(tool_grid)

        # Tools Table
        self.tools_table = FCTable(drag_drop=True)
        tool_grid.addWidget(self.tools_table, 0, 0, 1, 2)

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
        self.tools_table.horizontalHeaderItem(4).setToolTip(
            _("The number of Slot holes. Holes that are created by\n"
              "milling them with an endmill bit."))

        # Tool order
        self.order_label = FCLabel('%s:' % _('Tool order'))
        self.order_label.setToolTip(_("This set the way that the tools in the tools table are used.\n"
                                      "'Default' --> the order from the Excellon file\n"
                                      "'Forward' --> tools will be ordered from small to big\n"
                                      "'Reverse' --> tools will ordered from big to small\n\n"
                                      "WARNING: using rest machining will automatically set the order\n"
                                      "in reverse and disable this control."))

        self.order_combo = FCComboBox2()
        self.order_combo.addItems([_('Default'), _('Forward'), _('Reverse')])

        tool_grid.addWidget(self.order_label, 2, 0)
        tool_grid.addWidget(self.order_combo, 2, 1)

        # Manual Load of Tools from DB
        self.search_load_db_btn = FCButton(_("Search DB"))
        self.search_load_db_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/search_db32.png'))
        self.search_load_db_btn.setToolTip(
            _("Will search and try to replace the tools from Tools Table\n"
              "with tools from DB that have a close diameter value.")
        )

        tool_grid.addWidget(self.search_load_db_btn, 4, 0, 1, 2)

        # #############################################################################################################
        # ALL Parameters Frame
        # #############################################################################################################
        self.tool_data_label = FCLabel(
            '<span style="color:blue;"><b>%s: %s %d</b></span>' % (_('Parameters for'), _("Tool"), int(1)))
        self.tool_data_label.setToolTip(
            _(
                "The data used for creating GCode.\n"
                "Each tool store it's own set of such data."
            )
        )
        self.tools_box.addWidget(self.tool_data_label)

        self.exc_param_frame = QtWidgets.QFrame()
        self.exc_param_frame.setContentsMargins(0, 0, 0, 0)
        self.tools_box.addWidget(self.exc_param_frame)

        self.exc_tools_box = QtWidgets.QVBoxLayout()
        self.exc_tools_box.setContentsMargins(0, 0, 0, 0)
        self.exc_param_frame.setLayout(self.exc_tools_box)

        # #############################################################################################################
        # Tool Parameters Frame
        # #############################################################################################################
        tp_frame = FCFrame()
        self.exc_tools_box.addWidget(tp_frame)

        # Grid Layout
        param_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        tp_frame.setLayout(param_grid)

        # Cut Z
        self.cutzlabel = FCLabel('%s:' % _('Cut Z'))
        self.cutzlabel.setToolTip(
            _("Drill depth (negative)\n"
              "below the copper surface.")
        )

        self.cutz_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.cutz_entry.set_precision(self.decimals)
        self.cutz_entry.set_range(-10000.0000, 10000.0000)

        self.cutz_entry.setSingleStep(0.1)
        self.cutz_entry.setObjectName("e_cutz")

        param_grid.addWidget(self.cutzlabel, 4, 0)
        param_grid.addWidget(self.cutz_entry, 4, 1)

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

        param_grid.addWidget(self.mpass_cb, 5, 0)
        param_grid.addWidget(self.maxdepth_entry, 5, 1)

        # Travel Z (z_move)
        self.travelzlabel = FCLabel('%s:' % _('Travel Z'))
        self.travelzlabel.setToolTip(
            _("Tool height when travelling\n"
              "across the XY plane.")
        )

        self.travelz_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.travelz_entry.set_precision(self.decimals)
        self.travelz_entry.set_range(-10000.0000, 10000.0000)

        self.travelz_entry.setSingleStep(0.1)
        self.travelz_entry.setObjectName("e_travelz")

        param_grid.addWidget(self.travelzlabel, 6, 0)
        param_grid.addWidget(self.travelz_entry, 6, 1)

        # Excellon Feedrate Z
        self.frzlabel = FCLabel('%s:' % _('Feedrate Z'))
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

        param_grid.addWidget(self.frzlabel, 14, 0)
        param_grid.addWidget(self.feedrate_z_entry, 14, 1)

        # Excellon Rapid Feedrate
        self.feedrate_rapid_label = FCLabel('%s:' % _('Feedrate Rapids'))
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

        param_grid.addWidget(self.feedrate_rapid_label, 16, 0)
        param_grid.addWidget(self.feedrate_rapid_entry, 16, 1)

        # default values is to hide
        self.feedrate_rapid_label.hide()
        self.feedrate_rapid_entry.hide()

        # Spindlespeed
        self.spindle_label = FCLabel('%s:' % _('Spindle speed'))
        self.spindle_label.setToolTip(
            _("Speed of the spindle\n"
              "in RPM (optional)")
        )

        self.spindlespeed_entry = FCSpinner(callback=self.confirmation_message_int)
        self.spindlespeed_entry.set_range(0, 1000000)
        self.spindlespeed_entry.set_step(100)
        self.spindlespeed_entry.setObjectName("e_spindlespeed")

        param_grid.addWidget(self.spindle_label, 19, 0)
        param_grid.addWidget(self.spindlespeed_entry, 19, 1)

        # Dwell
        self.dwell_cb = FCCheckBox('%s:' % _('Dwell'))
        self.dwell_cb.setToolTip(
            _("Pause to allow the spindle to reach its\n"
              "speed before cutting.")
        )
        self.dwell_cb.setObjectName("e_dwell")

        # Dwelltime
        self.dwelltime_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.dwelltime_entry.set_precision(self.decimals)
        self.dwelltime_entry.set_range(0.0, 10000.0000)
        self.dwelltime_entry.setSingleStep(0.1)

        self.dwelltime_entry.setToolTip(
            _("Number of time units for spindle to dwell.")
        )
        self.dwelltime_entry.setObjectName("e_dwelltime")

        param_grid.addWidget(self.dwell_cb, 20, 0)
        param_grid.addWidget(self.dwelltime_entry, 20, 1)

        self.ois_dwell = OptionalInputSection(self.dwell_cb, [self.dwelltime_entry])

        # Tool Offset
        self.tool_offset_label = FCLabel('%s:' % _('Offset Z'))
        self.tool_offset_label.setToolTip(
            _("Some drill bits (the larger ones) need to drill deeper\n"
              "to create the desired exit hole diameter due of the tip shape.\n"
              "The value here can compensate the Cut Z parameter.")
        )

        self.offset_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.offset_entry.set_precision(self.decimals)
        self.offset_entry.set_range(-10000.0000, 10000.0000)
        self.offset_entry.setObjectName("e_offset")

        param_grid.addWidget(self.tool_offset_label, 25, 0)
        param_grid.addWidget(self.offset_entry, 25, 1)

        # Drill slots
        self.drill_slots_cb = FCCheckBox('%s' % _('Drill slots'))
        self.drill_slots_cb.setToolTip(
            _("If the selected tool has slots then they will be drilled.")
        )
        self.drill_slots_cb.setObjectName("e_drill_slots")
        param_grid.addWidget(self.drill_slots_cb, 27, 0, 1, 2)

        # Drill Overlap
        self.drill_overlap_label = FCLabel('%s:' % _('Overlap'))
        self.drill_overlap_label.setToolTip(
            _("How much (percentage) of the tool diameter to overlap previous drill hole.")
        )

        self.drill_overlap_entry = FCDoubleSpinner(suffix='%', callback=self.confirmation_message)
        self.drill_overlap_entry.set_precision(self.decimals)
        self.drill_overlap_entry.set_range(0.0, 100.0000)
        self.drill_overlap_entry.setSingleStep(0.1)

        self.drill_overlap_entry.setObjectName("e_drill_slots_overlap")

        param_grid.addWidget(self.drill_overlap_label, 28, 0)
        param_grid.addWidget(self.drill_overlap_entry, 28, 1)

        # Last drill in slot
        self.last_drill_cb = FCCheckBox('%s' % _('Last drill'))
        self.last_drill_cb.setToolTip(
            _("If the slot length is not completely covered by drill holes,\n"
              "add a drill hole on the slot end point.")
        )
        self.last_drill_cb.setObjectName("e_drill_last_drill")
        param_grid.addWidget(self.last_drill_cb, 30, 0, 1, 2)

        self.drill_overlap_label.hide()
        self.drill_overlap_entry.hide()
        self.last_drill_cb.hide()

        self.ois_drill_overlap = OptionalHideInputSection(
            self.drill_slots_cb,
            [
                self.drill_overlap_label,
                self.drill_overlap_entry,
                self.last_drill_cb
            ]
        )

        self.apply_param_to_all = FCButton(_("Apply parameters to all tools"))
        self.apply_param_to_all.setIcon(QtGui.QIcon(self.app.resource_location + '/param_all32.png'))
        self.apply_param_to_all.setToolTip(
            _("The parameters in the current form will be applied\n"
              "on all the tools from the Tool Table.")
        )
        self.exc_tools_box.addWidget(self.apply_param_to_all)

        # #############################################################################################################
        # COMMON PARAMETERS Frame
        # #############################################################################################################
        # General Parameters
        self.gen_param_label = FCLabel('<span style="color:indigo;"><b>%s</b></span>' % _("Common Parameters"))
        self.gen_param_label.setToolTip(
            _("Parameters that are common for all tools.")
        )
        self.exc_tools_box.addWidget(self.gen_param_label)

        gp_frame = FCFrame()
        self.exc_tools_box.addWidget(gp_frame)

        all_par_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        gp_frame.setLayout(all_par_grid)

        # Tool change
        self.toolchange_cb = FCCheckBox('%s:' % _("Tool change Z"))
        self.toolchange_cb.setToolTip(
            _("Include tool-change sequence\n"
              "in G-Code (Pause for tool change).")
        )
        self.toolchange_cb.setObjectName("e_toolchange")

        # Tool change Z
        self.toolchangez_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.toolchangez_entry.setToolTip(
            _("Z-axis position (height) for\n"
              "tool change.")
        )
        self.toolchangez_entry.set_precision(self.decimals)
        self.toolchangez_entry.setObjectName("e_toolchangez")
        self.toolchangez_entry.set_range(-10000.0000, 10000.0000)

        self.toolchangez_entry.setSingleStep(0.1)

        all_par_grid.addWidget(self.toolchange_cb, 0, 0)
        all_par_grid.addWidget(self.toolchangez_entry, 0, 1)

        # Tool change X-Y
        self.toolchange_xy_label = FCLabel('%s:' % _('Toolchange X-Y'))
        self.toolchange_xy_label.setToolTip(
            _("Toolchange X,Y position.")
        )
        self.toolchangexy_entry = NumericalEvalTupleEntry(border_color='#0069A9')
        self.toolchangexy_entry.setObjectName("e_toolchangexy")

        all_par_grid.addWidget(self.toolchange_xy_label, 2, 0)
        all_par_grid.addWidget(self.toolchangexy_entry, 2, 1)

        self.ois_tcz_e = OptionalInputSection(self.toolchange_cb,
                                              [
                                                  self.toolchangez_entry,
                                                  self.toolchange_xy_label,
                                                  self.toolchangexy_entry
                                              ])

        # Start move Z:
        self.estartz_label = FCLabel('%s:' % _("Start Z"))
        self.estartz_label.setToolTip(
            _("Height of the tool just after starting the work.\n"
              "Delete the value if you don't need this feature.")
        )
        self.estartz_entry = NumericalEvalEntry(border_color='#0069A9')
        self.estartz_entry.setObjectName("e_startz")

        all_par_grid.addWidget(self.estartz_label, 4, 0)
        all_par_grid.addWidget(self.estartz_entry, 4, 1)

        # End move Z:
        self.endz_label = FCLabel('%s:' % _("End move Z"))
        self.endz_label.setToolTip(
            _("Height of the tool after\n"
              "the last move at the end of the job.")
        )
        self.endz_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.endz_entry.set_precision(self.decimals)
        self.endz_entry.setObjectName("e_endz")
        self.endz_entry.set_range(-10000.0000, 10000.0000)

        self.endz_entry.setSingleStep(0.1)

        all_par_grid.addWidget(self.endz_label, 6, 0)
        all_par_grid.addWidget(self.endz_entry, 6, 1)

        # End Move X,Y
        self.endmove_xy_label = FCLabel('%s:' % _('End move X,Y'))
        self.endmove_xy_label.setToolTip(
            _("End move X,Y position. In format (x,y).\n"
              "If no value is entered then there is no move\n"
              "on X,Y plane at the end of the job.")
        )
        self.endxy_entry = NumericalEvalTupleEntry(border_color='#0069A9')
        self.endxy_entry.setPlaceholderText(_("X,Y coordinates"))
        self.endxy_entry.setObjectName("e_endxy")

        all_par_grid.addWidget(self.endmove_xy_label, 8, 0)
        all_par_grid.addWidget(self.endxy_entry, 8, 1)

        # Probe depth
        self.pdepth_label = FCLabel('%s:' % _("Probe Z depth"))
        self.pdepth_label.setToolTip(
            _("The maximum depth that the probe is allowed\n"
              "to probe. Negative value, in current units.")
        )

        self.pdepth_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.pdepth_entry.set_precision(self.decimals)
        self.pdepth_entry.set_range(-10000.0000, 10000.0000)
        self.pdepth_entry.setSingleStep(0.1)
        self.pdepth_entry.setObjectName("e_depth_probe")

        all_par_grid.addWidget(self.pdepth_label, 10, 0)
        all_par_grid.addWidget(self.pdepth_entry, 10, 1)

        self.pdepth_label.hide()
        self.pdepth_entry.setVisible(False)

        # Probe feedrate
        self.feedrate_probe_label = FCLabel('%s:' % _("Feedrate Probe"))
        self.feedrate_probe_label.setToolTip(
            _("The feedrate used while the probe is probing.")
        )

        self.feedrate_probe_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.feedrate_probe_entry.set_precision(self.decimals)
        self.feedrate_probe_entry.set_range(0.0, 10000.0000)
        self.feedrate_probe_entry.setSingleStep(0.1)
        self.feedrate_probe_entry.setObjectName("e_fr_probe")

        all_par_grid.addWidget(self.feedrate_probe_label, 12, 0)
        all_par_grid.addWidget(self.feedrate_probe_entry, 12, 1)

        self.feedrate_probe_label.hide()
        self.feedrate_probe_entry.setVisible(False)

        # Preprocessor Excellon selection
        pp_excellon_label = FCLabel('%s:' % _("Preprocessor"))
        pp_excellon_label.setToolTip(
            _("The preprocessor JSON file that dictates\n"
              "Gcode output for Excellon Objects.")
        )
        self.pp_excellon_name_cb = FCComboBox()
        self.pp_excellon_name_cb.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.pp_excellon_name_cb.setObjectName("e_pp")

        all_par_grid.addWidget(pp_excellon_label, 14, 0)
        all_par_grid.addWidget(self.pp_excellon_name_cb, 14, 1)

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
            ))
        self.exclusion_cb.setObjectName("e_area_exclusion")

        all_par_grid.addWidget(self.exclusion_cb, 16, 0, 1, 2)

        self.exclusion_frame = QtWidgets.QFrame()
        self.exclusion_frame.setContentsMargins(0, 0, 0, 0)
        all_par_grid.addWidget(self.exclusion_frame, 18, 0, 1, 2)

        self.exclusion_box = QtWidgets.QVBoxLayout()
        self.exclusion_box.setContentsMargins(0, 0, 0, 0)
        self.exclusion_frame.setLayout(self.exclusion_box)

        self.exclusion_table = FCTable()
        self.exclusion_box.addWidget(self.exclusion_table)
        self.exclusion_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)

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

        self.exclusion_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)

        exclud_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        self.exclusion_box.addLayout(exclud_grid)

        # Chose Strategy
        self.strategy_label = FCLabel('%s:' % _("Strategy"))
        self.strategy_label.setToolTip(_("The strategy followed when encountering an exclusion area.\n"
                                         "Can be:\n"
                                         "- Over -> when encountering the area, the tool will go to a set height\n"
                                         "- Around -> will avoid the exclusion area by going around the area"))
        self.strategy_radio = RadioSet([{'label': _('Over'), 'value': 'over'},
                                        {'label': _('Around'), 'value': 'around'}])
        self.strategy_radio.setObjectName("e_area_strategy")

        exclud_grid.addWidget(self.strategy_label, 1, 0)
        exclud_grid.addWidget(self.strategy_radio, 1, 1)

        # Over Z
        self.over_z_label = FCLabel('%s:' % _("Over Z"))
        self.over_z_label.setToolTip(_("The height Z to which the tool will rise in order to avoid\n"
                                       "an interdiction area."))
        self.over_z_entry = FCDoubleSpinner()
        self.over_z_entry.set_range(-10000.0000, 10000.0000)
        self.over_z_entry.set_precision(self.decimals)
        self.over_z_entry.setObjectName("e_area_overz")

        exclud_grid.addWidget(self.over_z_label, 2, 0)
        exclud_grid.addWidget(self.over_z_entry, 2, 1)

        # Button Add Area
        self.add_area_button = QtWidgets.QPushButton(_('Add Area:'))
        self.add_area_button.setToolTip(_("Add an Exclusion Area."))

        # Area Selection shape
        self.area_shape_radio = RadioSet([{'label': _("Square"), 'value': 'square'},
                                          {'label': _("Polygon"), 'value': 'polygon'}])
        self.area_shape_radio.setToolTip(
            _("The kind of selection shape used for area selection.")
        )
        self.area_shape_radio.setObjectName("e_area_shape")

        exclud_grid.addWidget(self.add_area_button, 4, 0)
        exclud_grid.addWidget(self.area_shape_radio, 4, 1)

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

        # separator_line = QtWidgets.QFrame()
        # separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        # separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        # all_par_grid.addWidget(separator_line, 25, 0, 1, 2)

        FCGridLayout.set_common_column_size([obj_grid, tool_grid, param_grid, all_par_grid], 0)

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
        self.tools_box.addWidget(self.generate_cnc_button)

        self.tools_box.addStretch(1)

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


def distance(pt1, pt2):
    return np.sqrt((pt1[0] - pt2[0]) ** 2 + (pt1[1] - pt2[1]) ** 2)


def distance_euclidian(x1, y1, x2, y2):
    return np.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
