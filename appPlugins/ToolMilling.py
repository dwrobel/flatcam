# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File by:  Marius Adrian Stanciu (c)                      #
# Date:     6/15/2020                                      #
# License:  MIT Licence                                    #
# ##########################################################

from PyQt6 import QtWidgets, QtCore, QtGui

from appTool import AppTool
from appGUI.GUIElements import FCCheckBox, FCDoubleSpinner, RadioSet, FCTable, FCButton, FCComboBox2, \
    FCComboBox, OptionalInputSection, FCSpinner, NumericalEvalTupleEntry, OptionalHideInputSection, FCLabel, \
    VerticalScrollArea, FCGridLayout, FCFrame
from appParsers.ParseExcellon import Excellon

from camlib import grace

from copy import deepcopy
import math
import simplejson as json
import sys
import traceback

# from appObjects.FlatCAMObj import FlatCAMObj
# import numpy as np
# import math

# from shapely.ops import unary_union
from shapely.geometry import Point, LineString, box

from matplotlib.backend_bases import KeyEvent as mpl_key_event

import logging
import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class ToolMilling(AppTool, Excellon):
    builduiSig = QtCore.pyqtSignal()
    launch_job = QtCore.pyqtSignal()

    def __init__(self, app):
        self.app = app
        self.decimals = self.app.decimals

        AppTool.__init__(self, app)
        Excellon.__init__(self, excellon_circle_steps=self.app.defaults["excellon_circle_steps"])

        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = None
        self.pluginName = _("Milling")

        # #############################################################################
        # ########################## VARIABLES ########################################
        # #############################################################################
        self.units = ''
        self.obj_tools = {}
        self.tooluid = 0

        # dict that holds the object names and the option name
        # the key is the object name (defines in ObjectUI) for each UI element that is a parameter
        # particular for a tool and the value is the actual name of the option that the UI element is changing
        self.name2option = {}

        # store here the default data for Geometry Data
        self.default_data = {}

        # store here the Geometry tools selected in the Geo Tools Table
        self.sel_tools = {}

        self.obj_name = ""
        self.target_obj = None

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

        # variable to store the current row in the (geo) tools table
        self.current_row = -1

        # variable to store the distance travelled
        self.travel_distance = 0.0

        self.grid_status_memory = self.app.ui.grid_snap_btn.isChecked()

        # store here the state of the exclusion checkbox state to be restored after building the UI
        # TODO add this in the self.app.defaults dict and in Preferences
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

        # updated in the self.set_tool_ui()
        self.form_fields = {}
        self.general_form_fields = {}

        self.old_tool_dia = None
        self.poly_drawn = False

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Alt+M', **kwargs)

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolMilling()")

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

        # reset those objects on a new run
        self.target_obj = None
        self.obj_name = ''

        self.build_ui()

        # all the tools are selected by default
        self.ui.tools_table.selectAll()

        self.app.ui.notebook.setTabText(2, _("Milling"))

    def connect_signals(self):
        # #############################################################################
        # ############################ SIGNALS ########################################
        # #############################################################################
        self.builduiSig.connect(self.build_ui)

        self.ui.level.toggled.connect(self.on_level_changed)

        # add Tool
        self.ui.search_and_add_btn.clicked.connect(self.on_tool_add)
        self.ui.deltool_btn.clicked.connect(self.on_tool_delete)
        self.ui.addtool_from_db_btn.clicked.connect(self.on_tool_add_from_db_clicked)

        self.ui.target_radio.activated_custom.connect(self.on_target_changed)
        self.ui.job_type_combo.currentIndexChanged.connect(self.on_job_changed)
        self.ui.offset_type_combo.currentIndexChanged.connect(self.on_offset_type_changed)
        self.ui.pp_geo_name_cb.activated.connect(self.on_pp_changed)

        # V tool shape params changed
        self.ui.tipdia_entry.valueChanged.connect(lambda: self.on_update_cutz())
        self.ui.tipangle_entry.valueChanged.connect(lambda: self.on_update_cutz())

        self.ui.apply_param_to_all.clicked.connect(self.on_apply_param_to_all_clicked)
        self.ui.tools_table.drag_drop_sig.connect(self.on_exc_rebuild_ui)

        # Exclusion areas signals
        self.ui.exclusion_table.horizontalHeader().sectionClicked.connect(self.exclusion_table_toggle_all)
        self.ui.exclusion_table.lost_focus.connect(self.clear_selection)
        self.ui.exclusion_table.itemClicked.connect(self.draw_sel_shape)
        self.ui.add_area_button.clicked.connect(self.on_add_area_click)
        self.ui.delete_area_button.clicked.connect(self.on_clear_area_click)
        self.ui.delete_sel_area_button.clicked.connect(self.on_delete_sel_areas)
        self.ui.strategy_radio.activated_custom.connect(self.on_strategy)

        # Geo Tools Table signals
        self.ui.geo_tools_table.drag_drop_sig.connect(self.on_geo_rebuild_ui)
        self.ui.geo_tools_table.horizontalHeader().sectionClicked.connect(self.on_toggle_all_rows)

        # Generate CNCJob
        self.launch_job.connect(self.mtool_gen_cncjob)
        self.ui.generate_cnc_button.clicked.connect(self.on_generate_cncjob_click)

        # Reset Tool
        self.ui.reset_button.clicked.connect(self.set_tool_ui)
        # Cleanup on Graceful exit (CTRL+ALT+X combo key)
        self.app.cleanup.connect(self.set_tool_ui)

    def disconnect_signals(self):
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

        # add Tool
        try:
            self.ui.search_and_add_btn.clicked.disconnect()
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.deltool_btn.clicked.disconnect()
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.addtool_from_db_btn.clicked.disconnect()
        except (TypeError, AttributeError):
            pass

        try:
            self.ui.target_radio.activated_custom.disconnect()
        except (TypeError, AttributeError):
            pass

        try:
            self.ui.job_type_combo.currentIndexChanged.disconnect()
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.offset_type_combo.currentIndexChanged.disconnect()
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.pp_geo_name_cb.activated.disconnect()
        except (TypeError, AttributeError):
            pass

        # V tool shape params changed
        try:
            self.ui.tipdia_entry.valueChanged.disconnect()
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.tipangle_entry.valueChanged.disconnect()
        except (TypeError, AttributeError):
            pass

        try:
            self.ui.apply_param_to_all.clicked.disconnect()
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

        # Geo Tools Table signals
        try:
            self.ui.geo_tools_table.drag_drop_sig.disconnect()
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.geo_tools_table.horizontalHeader().sectionClicked.disconnect()
        except (TypeError, AttributeError):
            pass

        # Generate CNCJob
        try:
            self.launch_job.disconnect()
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.generate_cnc_button.clicked.disconnect()
        except (TypeError, AttributeError):
            pass

        # Reset Tool
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
        # ############################### TOOLS TABLE context menu ####################################################
        # #############################################################################################################
        self.ui.geo_tools_table.setupContextMenu()
        self.ui.geo_tools_table.addContextMenu(
            _("Pick from DB"), self.on_tool_add_from_db_clicked,
            icon=QtGui.QIcon(self.app.resource_location + "/plus16.png"))
        self.ui.geo_tools_table.addContextMenu(
            _("Copy"), self.on_tool_copy,
            icon=QtGui.QIcon(self.app.resource_location + "/copy16.png"))
        self.ui.geo_tools_table.addContextMenu(
            _("Delete"), lambda: self.on_tool_delete(clicked_signal=None, all_tools=None),
            icon=QtGui.QIcon(self.app.resource_location + "/trash16.png"))

        # #############################################################################################################
        # ############################## EXCLUSION TABLE context menu #################################################
        # #############################################################################################################
        self.ui.exclusion_table.setupContextMenu()
        self.ui.exclusion_table.addContextMenu(
            _("Delete"), self.on_delete_sel_areas, icon=QtGui.QIcon(self.app.resource_location + "/trash16.png")
        )

    def unset_context_menu(self):
        self.ui.geo_tools_table.removeContextMenu()

    def init_ui(self):
        self.ui = MillingUI(layout=self.layout, app=self.app, name=self.pluginName)

    def set_tool_ui(self):
        self.units = self.app.app_units.upper()
        self.old_tool_dia = self.app.defaults["tools_iso_newdia"]

        self.obj_name = ""
        self.target_obj = None

        self.first_click = False
        self.cursor_pos = None
        self.mouse_is_dragging = False

        self.clear_ui(self.layout)
        self.init_ui()

        self.unset_context_menu()
        self.set_context_menu()

        self.disconnect_signals()
        self.connect_signals()

        # try to select in the Target combobox the active object
        selected_obj = self.app.collection.get_active()
        try:

            if not selected_obj:
                self.ui.target_radio.set_value('geo')
                self.ui.object_combo.setCurrentIndex(0)
            else:
                if selected_obj.kind == 'excellon':
                    self.ui.target_radio.set_value('exc')
                    self.ui.object_combo.set_value(selected_obj.options['name'])
                elif selected_obj.kind == 'geometry':
                    self.ui.target_radio.set_value('geo')
                    self.ui.object_combo.set_value(selected_obj.options['name'])
                else:
                    self.ui.target_radio.set_value('geo')
                    self.ui.object_combo.setCurrentIndex(0)

        except Exception as err:
            self.app.log.error("ToolMilling.set_tool_ui() --> %s" % str(err))

        # Update the GUI data holding structures
        self.form_fields = {
            # Excellon properties
            "tools_mill_milling_type": self.ui.milling_type_radio,
            "tools_mill_milling_dia": self.ui.mill_dia_entry,

            # Geometry properties
            # "tools_mill_tooldia": self.ui.addtool_entry,
            "tools_mill_offset_type": self.ui.offset_type_combo,
            "tools_mill_offset_value": self.ui.offset_entry,

            "tools_mill_tool_shape": self.ui.tool_shape_combo,
            "tools_mill_job_type": self.ui.job_type_combo,
            "tools_mill_polish_margin": self.ui.polish_margin_entry,
            "tools_mill_polish_overlap": self.ui.polish_over_entry,
            "tools_mill_polish_method": self.ui.polish_method_combo,

            "tools_mill_vtipdia": self.ui.tipdia_entry,
            "tools_mill_vtipangle": self.ui.tipangle_entry,

            "tools_mill_cutz": self.ui.cutz_entry,
            "tools_mill_multidepth": self.ui.mpass_cb,
            "tools_mill_depthperpass": self.ui.maxdepth_entry,

            "tools_mill_travelz": self.ui.travelz_entry,
            "tools_mill_feedrate": self.ui.xyfeedrate_entry,
            "tools_mill_feedrate_z": self.ui.feedrate_z_entry,
            "tools_mill_feedrate_rapid": self.ui.feedrate_rapid_entry,

            "tools_mill_extracut": self.ui.extracut_cb,
            "tools_mill_extracut_length": self.ui.e_cut_entry,

            "tools_mill_spindlespeed": self.ui.spindlespeed_entry,
            "tools_mill_dwell": self.ui.dwell_cb,
            "tools_mill_dwelltime": self.ui.dwelltime_entry,
        }

        self.general_form_fields = {
            "tools_mill_toolchange": self.ui.toolchange_cb,
            "tools_mill_toolchangez": self.ui.toolchangez_entry,
            "tools_mill_toolchangexy": self.ui.toolchangexy_entry,

            "tools_mill_endz": self.ui.endz_entry,
            "tools_mill_endxy": self.ui.endxy_entry,

            "tools_mill_z_pdepth": self.ui.pdepth_entry,
            "tools_mill_feedrate_probe": self.ui.feedrate_probe_entry,
            "tools_mill_ppname_g": self.ui.pp_geo_name_cb,
            "segx":    self.ui.segx_entry,
            "segy":    self.ui.segy_entry,

            # "gcode_type": self.ui.excellon_gcode_type_radio,
            "tools_mill_area_exclusion": self.ui.exclusion_cb,
            "tools_mill_area_shape": self.ui.area_shape_radio,
            "tools_mill_area_strategy": self.ui.strategy_radio,
            "tools_mill_area_overz": self.ui.over_z_entry,
        }

        self.name2option = {
            "milling_type":     "tools_mill_milling_type",
            "milling_dia":      "tools_mill_milling_dia",

            "mill_offset_type": "tools_mill_offset_type",
            "mill_offset":      "tools_mill_offset_value",

            "mill_tool_shape":   "tools_mill_tool_shape",
            "mill_job_type":       "tools_mill_job_type",

            "mill_polish_margin":   "tools_mill_polish_margin",
            "mill_polish_overlap":          "tools_mill_polish_overlap",
            "mill_polish_method":      "tools_mill_polish_method",

            "mill_tipdia":         "tools_mill_vtipdia",
            "mill_tipangle":    "tools_mill_vtipangle",

            "mill_cutz":    "tools_mill_cutz",
            "mill_multidepth":       "tools_mill_multidepth",
            "mill_depthperpass":       "tools_mill_depthperpass",

            "mill_travelz": "tools_mill_travelz",
            "mill_feedratexy": "tools_mill_feedrate",
            "mill_feedratez": "tools_mill_feedrate_z",
            "mill_fr_rapid": "tools_mill_feedrate_rapid",

            "mill_extracut": "tools_mill_extracut",
            "mill_extracut_length": "tools_mill_extracut_length",

            "mill_spindlespeed": "tools_mill_spindlespeed",
            "mill_dwell": "tools_mill_dwell",
            "mill_dwelltime": "tools_mill_dwelltime",

            # General Parameters
            "mill_toolchange": "tools_mill_toolchange",
            "mill_toolchangez": "tools_mill_toolchangez",
            "mill_toolchangexy": "tools_mill_toolchangexy",

            "mill_endz": "tools_mill_endz",
            "mill_endxy": "tools_mill_endxy",

            "mill_depth_probe": "tools_mill_z_pdepth",
            "mill_fr_probe": "tools_mill_feedrate_probe",
            "mill_ppname_g": "tools_mill_ppname_g",
            "mill_segx":    "segx",
            "mill_segy":    "segy",

            "mill_exclusion": "tools_mill_area_exclusion",
            "mill_area_shape": "tools_mill_area_shape",
            "mill_strategy": "tools_mill_area_strategy",
            "mill_overz": "tools_mill_area_overz",
        }

        # reset the Geometry preprocessor combo
        self.ui.pp_geo_name_cb.clear()
        # populate Geometry (milling) preprocessor combobox list
        for name in list(self.app.preprocessors.keys()):
            self.ui.pp_geo_name_cb.addItem(name)
        # and add ToolTips (useful when names are too long)
        for it in range(self.ui.pp_geo_name_cb.count()):
            self.ui.pp_geo_name_cb.setItemData(it, self.ui.pp_geo_name_cb.itemText(it),
                                               QtCore.Qt.ItemDataRole.ToolTipRole)

        # Fill form fields
        self.to_form()

        self.ui.tools_frame.show()

        self.ui.order_combo.set_value(self.app.defaults["tools_drill_tool_order"])
        self.ui.milling_type_radio.set_value(self.app.defaults["tools_mill_milling_type"])

        # init the working variables
        self.default_data.clear()
        kind = 'geometry'
        for option in self.app.options:
            if option.find(kind + "_") == 0:
                oname = option[len(kind) + 1:]
                self.default_data[oname] = self.app.options[option]

            if option.find('tools_') == 0:
                self.default_data[option] = self.app.options[option]

        # fill in self.default_data values from self.options
        for opt_key, opt_val in self.app.options.items():
            if opt_key.find('geometry_') == 0:
                oname = opt_key[len('geometry_'):]
                self.default_data[oname] = deepcopy(opt_val)
        for opt_key, opt_val in self.app.options.items():
            if opt_key.find('tools_') == 0:
                self.default_data[opt_key] = deepcopy(opt_val)

        # ########################################
        # #######3 TEMP SETTINGS #################
        # ########################################

        self.ui.addtool_entry.set_value(self.app.defaults["tools_mill_tooldia"])

        self.on_object_changed()
        if self.target_obj:
            self.build_ui()

        try:
            self.ui.object_combo.currentIndexChanged.disconnect()
        except (AttributeError, TypeError):
            pass
        self.ui.object_combo.currentIndexChanged.connect(self.on_object_changed)

        self.ui.offset_type_combo.set_value(0)  # 'Path'

        # handle the Plot checkbox
        self.plot_cb_handler()

        # Show/Hide Advanced Options
        app_mode = self.app.defaults["global_app_level"]
        self.change_level(app_mode)

    def plot_cb_handler(self):
        # load the Milling object
        self.obj_name = self.ui.object_combo.currentText()

        # Get source object.
        try:
            self.target_obj = self.app.collection.get_by_name(self.obj_name)
        except Exception:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), str(self.obj_name)))
            return

        try:
            self.ui.plot_cb.stateChanged.disconnect()
        except (AttributeError, TypeError):
            pass

        self.ui.plot_cb.stateChanged.connect(self.on_plot_clicked)
        if self.target_obj is not None:
            self.ui.plot_cb.set_value(self.target_obj.options['plot'])

    def on_plot_clicked(self, state):
        if self.target_obj:
            self.target_obj.options['plot'] = True if state else False

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

        self.target_obj = self.app.collection.get_by_name(self.ui.object_combo.get_value())

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
            if self.ui.target_radio.get_value() == 'geo':
                if self.target_obj:
                    for tool in self.target_obj.tools:
                        tool_data = self.target_obj.tools[tool]['data']

                        tool_data['tools_mill_offset_type'] = 0  # 'Path'
                        tool_data['tools_mill_offset_value'] = 0.0
                        tool_data['tools_mill_job_type'] = 0    # _('Roughing')

                        tool_data['tools_mill_multidepth'] = False
                        tool_data['tools_mill_extracut'] = False
                        tool_data['tools_mill_dwell'] = False
                        tool_data['tools_mill_area_exclusion'] = False

                self.ui.offset_type_lbl.hide()
                self.ui.offset_type_combo.hide()
                self.ui.offset_label.hide()
                self.ui.offset_entry.hide()
                self.ui.offset_type_lbl.hide()
                self.ui.offset_separator_line.hide()
                self.ui.offset_type_lbl.hide()

                self.ui.job_type_lbl.hide()
                self.ui.job_type_combo.hide()
                self.ui.job_separator_line.hide()

                self.ui.mpass_cb.hide()
                self.ui.maxdepth_entry.hide()

                self.ui.extracut_cb.hide()
                self.ui.e_cut_entry.hide()

                # self.ui.dwell_cb.hide()
                # self.ui.dwelltime_entry.hide()

                self.ui.endmove_xy_label.hide()
                self.ui.endxy_entry.hide()

                self.ui.exclusion_cb.hide()

            # All param section
            self.ui.apply_param_to_all.hide()

            # Context Menu section
            self.ui.geo_tools_table.removeContextMenu()
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
            if self.ui.target_radio.get_value() == 'geo':
                if self.target_obj:
                    app_defaults = self.target_obj.options
                    for tool in self.target_obj.tools:
                        tool_data = self.target_obj.tools[tool]['data']

                        tool_data['tools_mill_offset_type'] = app_defaults['tools_mill_offset_type']
                        tool_data['tools_mill_offset_value'] = app_defaults['tools_mill_offset_value']
                        tool_data['tools_mill_job_type'] = app_defaults['tools_mill_job_type']

                        tool_data['tools_mill_multidepth'] = app_defaults['tools_mill_multidepth']
                        tool_data['tools_mill_extracut'] = app_defaults['tools_mill_extracut']
                        tool_data['tools_mill_dwell'] = app_defaults['tools_mill_dwell']
                        tool_data['tools_mill_area_exclusion'] = app_defaults['tools_mill_area_exclusion']

                self.ui.offset_type_lbl.show()
                self.ui.offset_type_combo.show()
                if self.ui.offset_type_combo.get_value() == 3:  # _("Custom")
                    self.ui.offset_label.show()
                    self.ui.offset_entry.show()
                self.ui.offset_type_lbl.show()
                self.ui.offset_separator_line.show()
                self.ui.offset_type_lbl.show()

                self.ui.job_type_lbl.show()
                self.ui.job_type_combo.show()
                self.ui.job_separator_line.show()

                self.ui.mpass_cb.show()
                self.ui.maxdepth_entry.show()

                self.ui.extracut_cb.show()
                self.ui.e_cut_entry.show()

                self.ui.dwell_cb.show()
                self.ui.dwelltime_entry.show()

                self.ui.endmove_xy_label.show()
                self.ui.endxy_entry.show()

                self.ui.exclusion_cb.show()

            # All param section
            self.ui.apply_param_to_all.show()

            # Context Menu section
            self.ui.geo_tools_table.setupContextMenu()

        # update the changes in UI depending on the selected preprocessor in Preferences
        # after this moment all the changes in the Posprocessor combo will be handled by the activated signal of the
        # pp combobox
        self.on_pp_changed()

    def on_exc_rebuild_ui(self):
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

        # the tools table changed therefore we need to rebuild it
        QtCore.QTimer.singleShot(20, self.build_ui)

    def on_geo_rebuild_ui(self):
        # read the table tools uid
        current_uid_list = []
        for row in range(self.ui.geo_tools_table.rowCount()):
            uid = int(self.ui.geo_tools_table.item(row, 3).text())
            current_uid_list.append(uid)

        new_tools = {}
        new_uid = 1

        try:
            for current_uid in current_uid_list:
                new_tools[new_uid] = deepcopy(self.tools[current_uid])
                new_uid += 1
        except Exception as err:
            self.app.log.error("ToolMilling.on_geo_rebuild_ui() -> %s" % str(err))
            return

        self.tools = new_tools

        # the tools table changed therefore we need to reconnect the signals to the cellWidgets
        self.ui_disconnect()
        self.ui_connect()

    def build_ui(self):
        self.ui_disconnect()

        # load the Milling object
        self.obj_name = self.ui.object_combo.currentText()

        # Get source object.
        try:
            self.target_obj = self.app.collection.get_by_name(self.obj_name)
        except Exception as err:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), str(self.obj_name)))
            self.app.log.error("ToolMilling.build_ui() getting the object --> %s" % str(err))
            self.ui_disconnect()
            self.ui_connect()
            return

        # build the UI
        try:
            if self.ui.target_radio.get_value() == 'geo':
                self.build_ui_mill()
            else:
                self.build_ui_exc()
        except Exception as err:
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Could not build the Plugin UI"))
            self.app.log.error("ToolMilling.build_ui() building the UI --> %s" % str(err))
            self.ui_connect()
            return

        # Build Exclusion Areas section
        self.ui_disconnect()
        e_len = len(self.app.exc_areas.exclusion_areas_storage)
        self.ui.exclusion_table.setRowCount(e_len)

        area_id = 0

        for area in range(e_len):
            area_id += 1

            area_dict = self.app.exc_areas.exclusion_areas_storage[area]

            # --------------------  ID  -------------------------------
            area_id_item = QtWidgets.QTableWidgetItem('%d' % int(area_id))
            area_id_item.setFlags(QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)
            self.ui.exclusion_table.setItem(area, 0, area_id_item)  # Area id

            # --------------------  Object Type  ----------------------
            object_item = QtWidgets.QTableWidgetItem('%s' % area_dict["obj_type"])
            object_item.setFlags(QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)
            self.ui.exclusion_table.setItem(area, 1, object_item)  # Origin Object

            # --------------------  Strategy  -------------------------
            strategy_item = FCComboBox2(policy=False)
            strategy_item.addItems([_("Around"), _("Over")])
            idx = 0 if area_dict["strategy"] == 'around' else 1
            # protection against having this translated or loading a project with translated values
            if idx == -1:
                strategy_item.setCurrentIndex(0)
            else:
                strategy_item.setCurrentIndex(idx)
            self.ui.exclusion_table.setCellWidget(area, 2, strategy_item)  # Strategy

            # --------------------  Over Z  ---------------------------
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

    def build_ui_mill(self):
        self.units = self.app.app_units

        if self.target_obj:
            self.ui.param_frame.setDisabled(False)

            tools_dict = self.target_obj.tools

        else:
            tools_dict = {}

        row_idx = 0

        n = len(tools_dict)
        self.ui.geo_tools_table.setRowCount(n)

        for tooluid_key, tooluid_value in tools_dict.items():

            # -------------------- ID ------------------------------------------ #
            tool_id = QtWidgets.QTableWidgetItem('%d' % int(row_idx + 1))
            tool_id.setFlags(QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)
            self.ui.geo_tools_table.setItem(row_idx, 0, tool_id)  # Tool name/id

            # -------------------- DIAMETER ------------------------------------- #
            dia_item = QtWidgets.QTableWidgetItem('%.*f' % (self.decimals, float(tooluid_value['tooldia'])))
            dia_item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
            self.ui.geo_tools_table.setItem(row_idx, 1, dia_item)  # Diameter

            # -------------------- TOOL TYPE ------------------------------------- #
            # tool_type_item = FCComboBox(policy=False)
            # for item in ["C1", "C2", "C3", "C4", "B", "V"]:
            #     tool_type_item.addItem(item)
            # idx = tool_type_item.findText(tooluid_value['data']['tools_mill_tool_type'])
            # # protection against having this translated or loading a project with translated values
            # if idx == -1:
            #     tool_type_item.setCurrentIndex(0)
            # else:
            #     tool_type_item.setCurrentIndex(idx)
            # self.ui.geo_tools_table.setCellWidget(row_idx, 2, tool_type_item)

            # -------------------- TOOL UID   ------------------------------------- #
            tool_uid_item = QtWidgets.QTableWidgetItem(str(tooluid_key))
            # ## REMEMBER: THIS COLUMN IS HIDDEN IN OBJECTUI.PY ###
            self.ui.geo_tools_table.setItem(row_idx, 3, tool_uid_item)  # Tool unique ID

            # -------------------- PLOT       ------------------------------------- #
            empty_plot_item = QtWidgets.QTableWidgetItem('')
            empty_plot_item.setFlags(~QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)
            self.ui.geo_tools_table.setItem(row_idx, 4, empty_plot_item)
            plot_item = FCCheckBox()
            plot_item.setLayoutDirection(QtCore.Qt.LayoutDirection.RightToLeft)
            if self.ui.plot_cb.isChecked():
                plot_item.setChecked(True)
            self.ui.geo_tools_table.setCellWidget(row_idx, 4, plot_item)

            row_idx += 1

        # make the diameter column editable
        for row in range(row_idx):
            self.ui.geo_tools_table.item(row, 1).setFlags(QtCore.Qt.ItemFlag.ItemIsSelectable |
                                                          QtCore.Qt.ItemFlag.ItemIsEditable |
                                                          QtCore.Qt.ItemFlag.ItemIsEnabled)

        # sort the tool diameter column
        # self.ui.geo_tools_table.sortItems(1)
        # all the tools are selected by default
        # self.ui.geo_tools_table.selectColumn(0)

        self.ui.geo_tools_table.resizeColumnsToContents()
        self.ui.geo_tools_table.resizeRowsToContents()

        vertical_header = self.ui.geo_tools_table.verticalHeader()
        # vertical_header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        vertical_header.hide()
        self.ui.geo_tools_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        horizontal_header = self.ui.geo_tools_table.horizontalHeader()
        horizontal_header.setMinimumSectionSize(10)
        horizontal_header.setDefaultSectionSize(70)
        horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Fixed)
        horizontal_header.resizeSection(0, 20)
        horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        # horizontal_header.setSectionResizeMode(2, QtWidgets.QHeaderView.Fixed)
        # horizontal_header.resizeSection(2, 40)
        horizontal_header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.Fixed)
        horizontal_header.resizeSection(4, 17)
        # horizontal_header.setStretchLastSection(True)
        self.ui.geo_tools_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.ui.geo_tools_table.setColumnWidth(0, 20)
        # self.ui.geo_tools_table.setColumnWidth(2, 40)
        self.ui.geo_tools_table.setColumnWidth(4, 17)

        # self.ui.geo_tools_table.setSortingEnabled(True)

        self.ui.geo_tools_table.setMinimumHeight(self.ui.geo_tools_table.getHeight())
        self.ui.geo_tools_table.setMaximumHeight(self.ui.geo_tools_table.getHeight())

        # disable the Plot column in Tool Table if the geometry is SingleGeo as it is not needed
        # and can create some problems
        if self.target_obj and self.target_obj.multigeo is True:
            self.ui.geo_tools_table.setColumnHidden(4, False)
        else:
            self.ui.geo_tools_table.setColumnHidden(4, True)

        self.ui.geo_tools_table.selectAll()

        # set the text on tool_data_label after loading the object
        sel_rows = set()
        sel_items = self.ui.geo_tools_table.selectedItems()
        for it in sel_items:
            sel_rows.add(it.row())
            it.setSelected(True)

        if len(sel_rows) > 1:
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("Multiple Tools"))
            )

    def build_ui_exc(self):
        # updated units
        self.units = self.app.app_units.upper()

        if self.target_obj:
            self.ui.param_frame.setDisabled(False)

            # order the tools by tool diameter if it's the case
            sorted_tools = []
            for k, v in self.obj_tools.items():
                sorted_tools.append(self.app.dec_format(float(v['tooldia'])))

            order = self.ui.order_combo.get_value()
            if order == 1:  # 'fwd'
                sorted_tools.sort(reverse=False)
            elif order == 2:  # 'rev'
                sorted_tools.sort(reverse=True)
            else:
                pass

            # remake the excellon_tools dict in the order above
            new_id = 1
            new_tools = {}
            for tooldia in sorted_tools:
                for old_tool in self.obj_tools:
                    if self.app.dec_format(float(self.obj_tools[old_tool]['tooldia'])) == tooldia:
                        new_tools[new_id] = deepcopy(self.obj_tools[old_tool])
                        new_id += 1

            self.obj_tools = new_tools
            tools = [k for k in self.obj_tools]

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
                drill_cnt = len(self.obj_tools[tool_no]["drills"])
            except KeyError:
                drill_cnt = 0
            self.tot_drill_cnt += drill_cnt

            # Find no of slots for the current tool
            try:
                slot_cnt = len(self.obj_tools[tool_no]["slots"])
            except KeyError:
                slot_cnt = 0
            self.tot_slot_cnt += slot_cnt

            # Tool name/id
            exc_id_item = QtWidgets.QTableWidgetItem('%d' % int(tool_no))
            exc_id_item.setFlags(QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)
            self.ui.tools_table.setItem(self.tool_row, 0, exc_id_item)

            # Tool Diameter
            dia_item = QtWidgets.QTableWidgetItem('%.*f' % (self.decimals, self.obj_tools[tool_no]['tooldia']))
            dia_item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
            self.ui.tools_table.setItem(self.tool_row, 1, dia_item)

            # Number of drills per tool
            drill_count_item = QtWidgets.QTableWidgetItem('%d' % drill_cnt)
            drill_count_item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
            self.ui.tools_table.setItem(self.tool_row, 2, drill_count_item)

            # Tool unique ID
            tool_uid_item = QtWidgets.QTableWidgetItem(str(int(tool_no)))
            # ## REMEMBER: THIS COLUMN IS HIDDEN in UI
            self.ui.tools_table.setItem(self.tool_row, 3, tool_uid_item)

            # Number of slots per tool
            # if the slot number is zero is better to not clutter the GUI with zero's so we print a space
            slot_count_str = '%d' % slot_cnt if slot_cnt > 0 else ''
            slot_count_item = QtWidgets.QTableWidgetItem(slot_count_str)
            slot_count_item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
            self.ui.tools_table.setItem(self.tool_row, 4, slot_count_item)

            self.tool_row += 1

        # add a last row with the Total number of drills
        empty_1 = QtWidgets.QTableWidgetItem('')
        empty_1.setFlags(~QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)
        empty_1_1 = QtWidgets.QTableWidgetItem('')
        empty_1_1.setFlags(~QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)

        label_tot_drill_count = QtWidgets.QTableWidgetItem(_('Total Drills'))
        label_tot_drill_count.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)

        tot_drill_count = QtWidgets.QTableWidgetItem('%d' % self.tot_drill_cnt)
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
        tot_slot_count = QtWidgets.QTableWidgetItem('%d' % self.tot_slot_cnt)
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
        for row in range(self.ui.tools_table.rowCount() - 2):
            self.ui.tools_table.item(row, 1).setFlags(
                QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)

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

    def on_target_changed(self, val):
        # handle the Plot checkbox
        self.plot_cb_handler()

        obj_type = 1 if val == 'exc' else 2
        self.ui.object_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.ui.object_combo.setCurrentIndex(0)
        self.ui.object_combo.obj_type = {
            "exc": "Excellon", "geo": "Geometry"
        }[val]

        if val == 'exc':
            self.ui.tools_table.show()
            self.ui.order_label.show()
            self.ui.order_combo.show()

            self.ui.geo_tools_table.hide()

            self.ui.mill_type_label.show()
            self.ui.milling_type_radio.show()
            self.ui.mill_dia_label.show()
            self.ui.mill_dia_entry.show()

            self.ui.frxylabel.hide()
            self.ui.xyfeedrate_entry.hide()
            self.ui.extracut_cb.hide()
            self.ui.e_cut_entry.hide()

            self.ui.job_type_lbl.hide()
            self.ui.job_type_combo.hide()
            self.ui.job_type_combo.set_value(0)  # 'iso' - will hide the Polish UI elements

            self.ui.offset_separator_line.hide()
            self.ui.tool_shape_label.hide()
            self.ui.tool_shape_combo.hide()

            self.ui.add_tool_frame.hide()
        else:
            self.ui.tools_table.hide()
            self.ui.order_label.hide()
            self.ui.order_combo.hide()

            self.ui.geo_tools_table.show()

            self.ui.mill_type_label.hide()
            self.ui.milling_type_radio.hide()
            self.ui.mill_dia_label.hide()
            self.ui.mill_dia_entry.hide()

            self.ui.frxylabel.show()
            self.ui.xyfeedrate_entry.show()
            self.ui.extracut_cb.show()
            self.ui.e_cut_entry.show()

            self.ui.job_type_lbl.show()
            self.ui.job_type_combo.show()
            # self.ui.job_type_combo.set_value(self.app.defaults["tools_mill_job_val"])

            self.ui.offset_separator_line.show()
            self.ui.tool_shape_label.show()
            self.ui.tool_shape_combo.show()

            self.ui.add_tool_frame.show()

        # set the object as active so the Properties is populated by whatever object is selected
        self.obj_name = self.ui.object_combo.currentText()
        if self.obj_name and self.obj_name != '':
            self.app.collection.set_all_inactive()
            self.app.collection.set_active(self.obj_name)
        # self.build_ui()

        # new object that is now selected
        obj = self.app.collection.get_by_name(self.obj_name)
        if obj is not None and obj.tools:
            last_key = list(obj.tools.keys())[-1]
            self.to_form(storage=obj.tools[last_key]['data'])

    def on_object_changed(self):
        # print(self.app.ui.notebook.currentWidget().objectName() != 'plugin_tab')
        if not self.app.ui.notebook.tabText(2) != _("Milling Tool"):
            return

        # handle the Plot checkbox
        self.plot_cb_handler()
        
        # load the Milling object
        self.obj_name = self.ui.object_combo.currentText()

        # Get source object.
        try:
            self.target_obj = self.app.collection.get_by_name(self.obj_name)
        except Exception:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), str(self.obj_name)))
            return

        if self.target_obj is None:
            self.ui.param_frame.setDisabled(True)
            self.ui.plot_cb.setDisabled(True)
        else:
            self.ui.param_frame.setDisabled(False)
            self.ui.plot_cb.setDisabled(False)

            self.obj_tools = self.target_obj.tools
            # set the object as active so the Properties is populated by whatever object is selected
            if self.obj_name and self.obj_name != '':
                self.app.collection.set_all_inactive()
                self.app.collection.set_active(self.obj_name)
            self.build_ui()

            if self.target_obj.tools:
                self.ui.param_frame.setDisabled(False)
                self.ui.generate_cnc_button.setDisabled(False)
                last_key = list(self.target_obj.tools.keys())[-1]
                self.to_form(storage=self.target_obj.tools[last_key]['data'])
            else:
                self.ui.param_frame.setDisabled(True)
                self.ui.generate_cnc_button.setDisabled(True)

    def on_object_selection_changed(self, current, previous):
        try:
            sel_obj = current.indexes()[0].internalPointer().obj
            name = sel_obj.options['name']
            kind = sel_obj.kind
            if kind == 'excellon':
                self.ui.target_radio.set_value('exc')
                self.ui.object_combo.set_value(name)

            if kind == 'geometry':
                self.ui.target_radio.set_value('geo')
                self.ui.object_combo.set_value(name)
        except Exception:
            pass

    def on_job_changed(self, idx):
        if self.ui.target_radio.get_value() == 'geo':
            if idx == 3:    # 'Polish'
                self.ui.polish_margin_lbl.show()
                self.ui.polish_margin_entry.show()
                self.ui.polish_over_lbl.show()
                self.ui.polish_over_entry.show()
                self.ui.polish_method_lbl.show()
                self.ui.polish_method_combo.show()

                self.ui.cutzlabel.setText('%s:' % _("Pressure"))
                self.ui.cutzlabel.setToolTip(
                    _("Negative value. The higher the absolute value\n"
                      "the stronger the pressure of the brush on the material.")
                )
            else:
                self.ui.polish_margin_lbl.hide()
                self.ui.polish_margin_entry.hide()
                self.ui.polish_over_lbl.hide()
                self.ui.polish_over_entry.hide()
                self.ui.polish_method_lbl.hide()
                self.ui.polish_method_combo.hide()

                self.ui.cutzlabel.setText('%s:' % _('Cut Z'))
                self.ui.cutzlabel.setToolTip(
                    _("Drill depth (negative)\n"
                      "below the copper surface.")
                )

    def on_offset_type_changed(self, idx):
        if idx == 3:    # 'Custom'
            self.ui.offset_label.show()
            self.ui.offset_entry.show()
        else:
            self.ui.offset_label.hide()
            self.ui.offset_entry.hide()

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
        # then connect it to the current build_ui() method
        self.app.exc_areas.e_shape_modified.connect(self.update_exclusion_table)

        # connect Tool Table Widgets
        for row in range(self.ui.geo_tools_table.rowCount()):
            self.ui.geo_tools_table.cellWidget(row, 4).clicked.connect(self.on_plot_cb_click_table)

        # # Geo Tool Table - rows selected
        self.ui.geo_tools_table.clicked.connect(self.on_row_selection_change)
        self.ui.geo_tools_table.itemChanged.connect(self.on_tool_edit)
        self.ui.geo_tools_table.horizontalHeader().sectionClicked.connect(self.on_toggle_all_rows)

        # Excellon Tool Table - rows selected
        self.ui.tools_table.clicked.connect(self.on_row_selection_change)
        self.ui.tools_table.horizontalHeader().sectionClicked.connect(self.on_toggle_all_rows)

        self.ui.tool_shape_combo.currentIndexChanged.connect(self.on_tt_change)

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
            elif isinstance(current_widget, FCComboBox2):
                current_widget.currentIndexChanged.connect(self.form_to_storage)

        # General Parameters
        for opt in self.general_form_fields:
            current_widget = self.general_form_fields[opt]
            if isinstance(current_widget, FCCheckBox):
                current_widget.stateChanged.connect(self.form_to_storage)
            if isinstance(current_widget, RadioSet):
                current_widget.activated_custom.connect(self.form_to_storage)
            elif isinstance(current_widget, FCDoubleSpinner) or isinstance(current_widget, FCSpinner):
                current_widget.returnPressed.connect(self.form_to_storage)
            elif isinstance(current_widget, FCComboBox):
                current_widget.currentIndexChanged.connect(self.form_to_storage)
            elif isinstance(current_widget, FCComboBox2):
                current_widget.currentIndexChanged.connect(self.form_to_storage)

        self.ui.order_combo.currentIndexChanged.connect(self.on_order_changed)

        # Exclusion Table widgets connect
        for row in range(self.ui.exclusion_table.rowCount()):
            self.ui.exclusion_table.cellWidget(row, 2).currentIndexChanged.connect(self.on_exclusion_table_strategy)

        self.ui.exclusion_table.itemChanged.connect(self.on_exclusion_table_overz)

    def ui_disconnect(self):
        try:
            self.app.proj_selection_changed.disconnect()
        except (TypeError, AttributeError):
            pass

        # Excellon Tool Table - rows selected
        try:
            self.ui.tools_table.clicked.disconnect()
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.tools_table.horizontalHeader().sectionClicked.disconnect()
        except (TypeError, AttributeError):
            pass

        # Geo Tool Table
        try:
            self.ui.geo_tools_table.clicked.disconnect()
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.geo_tools_table.itemChanged.disconnect()
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.geo_tools_table.horizontalHeader().sectionClicked.disconnect()
        except (TypeError, AttributeError):
            pass

        # Geometry Tool table widgets
        for row in range(self.ui.geo_tools_table.rowCount()):
            try:
                self.ui.geo_tools_table.cellWidget(row, 4).clicked.disconnect()
            except (TypeError, AttributeError):
                pass

        # Tool Parameters
        for opt in self.form_fields:
            current_widget = self.form_fields[opt]
            if isinstance(current_widget, FCCheckBox):
                try:
                    current_widget.stateChanged.disconnect(self.form_to_storage)
                except (TypeError, ValueError, RuntimeError):
                    pass
            if isinstance(current_widget, RadioSet):
                try:
                    current_widget.activated_custom.disconnect(self.form_to_storage)
                except (TypeError, ValueError, RuntimeError):
                    pass
            elif isinstance(current_widget, FCDoubleSpinner) or isinstance(current_widget, FCSpinner):
                try:
                    current_widget.returnPressed.disconnect(self.form_to_storage)
                except (TypeError, ValueError, RuntimeError):
                    pass
            elif isinstance(current_widget, FCComboBox):
                try:
                    current_widget.currentIndexChanged.disconnect(self.form_to_storage)
                except (TypeError, ValueError, RuntimeError):
                    pass
            elif isinstance(current_widget, FCComboBox2):
                try:
                    current_widget.currentIndexChanged.disconnect(self.form_to_storage)
                except (TypeError, ValueError, RuntimeError):
                    pass

        try:
            self.ui.tool_shape_combo.currentIndexChanged.disconnect(self.on_tt_change)
        except (TypeError, ValueError, RuntimeError):
            pass

        # General Parameters
        for opt in self.general_form_fields:
            current_widget = self.general_form_fields[opt]
            if isinstance(current_widget, FCCheckBox):
                try:
                    current_widget.stateChanged.disconnect(self.form_to_storage)
                except (TypeError, ValueError, RuntimeError):
                    pass
            if isinstance(current_widget, RadioSet):
                try:
                    current_widget.activated_custom.disconnect(self.form_to_storage)
                except (TypeError, ValueError, RuntimeError):
                    pass
            elif isinstance(current_widget, FCDoubleSpinner) or isinstance(current_widget, FCSpinner):
                try:
                    current_widget.returnPressed.disconnect(self.form_to_storage)
                except (TypeError, ValueError, RuntimeError):
                    pass
            elif isinstance(current_widget, FCComboBox):
                try:
                    current_widget.currentIndexChanged.disconnect(self.form_to_storage)
                except (TypeError, ValueError, RuntimeError):
                    pass
            elif isinstance(current_widget, FCComboBox2):
                try:
                    current_widget.currentIndexChanged.disconnect(self.form_to_storage)
                except (TypeError, ValueError, RuntimeError):
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

    def on_toggle_all_rows(self):
        """
        will toggle the selection of all rows in Tools table

        :return:
        """

        self.ui_disconnect()

        if self.ui.target_radio.get_value() == 'exc':
            plugin_table = self.ui.tools_table
        else:
            plugin_table = self.ui.geo_tools_table

        # #########################################################################################################
        # Tool Table
        # #########################################################################################################
        sel_model = plugin_table.selectionModel()
        sel_rows_index_list = sel_model.selectedRows()
        sel_rows = [r.row() for r in sel_rows_index_list]

        if len(sel_rows) == plugin_table.rowCount():
            plugin_table.clearSelection()
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("No Tool Selected"))
            )
        else:
            plugin_table.selectAll()
            if plugin_table.rowCount() == 1:
                # update the QLabel that shows for which Tool we have the parameters in the UI form
                tooluid = int(plugin_table.item(0, 3).text())
                self.ui.tool_data_label.setText(
                    "<b>%s: <font color='#0000FF'>%s %d</font></b>" % (_('Parameters for'), _("Tool"), tooluid)
                )
            else:
                self.ui.tool_data_label.setText(
                    "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("Multiple Tools"))
                )

        sel_rows_index_list = sel_model.selectedRows()
        sel_rows = [r.row() for r in sel_rows_index_list]
        if sel_rows and len(sel_rows) > 0:
            self.ui.param_frame.setDisabled(False)
            self.ui.generate_cnc_button.setDisabled(False)
        else:
            self.ui.param_frame.setDisabled(True)
            self.ui.generate_cnc_button.setDisabled(True)

        self.ui_connect()

    def on_row_selection_change(self):
        if self.ui.target_radio.get_value() == 'exc':
            plugin_table = self.ui.tools_table
        else:
            plugin_table = self.ui.geo_tools_table

        self.update_ui()

        sel_model = plugin_table.selectionModel()
        sel_rows_index_list = sel_model.selectedRows()
        sel_rows = [r.row() for r in sel_rows_index_list]

        if sel_rows and len(sel_rows) > 0:
            self.ui.param_frame.setDisabled(False)
            self.ui.generate_cnc_button.setDisabled(False)
        else:
            self.ui.param_frame.setDisabled(True)
            self.ui.generate_cnc_button.setDisabled(True)

    def update_ui(self):
        self.ui_disconnect()

        if self.ui.target_radio.get_value() == 'exc':
            plugin_table = self.ui.tools_table
        else:
            plugin_table = self.ui.geo_tools_table

        sel_model = plugin_table.selectionModel()
        sel_rows_index_list = sel_model.selectedRows()
        sel_rows = [r.row() for r in sel_rows_index_list]

        if not sel_rows or len(sel_rows) == 0:
            self.ui.generate_cnc_button.setDisabled(True)
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("No Tool Selected"))
            )
            self.ui_connect()
            return
        else:
            self.ui.generate_cnc_button.setDisabled(False)
            self.ui.param_frame.setDisabled(False)

        if len(sel_rows) == 1:
            # update the QLabel that shows for which Tool we have the parameters in the UI form
            tooluid = int(plugin_table.item(list(sel_rows)[0], 0).text())
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s %d</font></b>" % (_('Parameters for'), _("Tool"), tooluid)
            )
        else:
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("Multiple Tools"))
            )
            # update UI only if only one row is selected otherwise having multiple rows selected will deform information
            # for the rows other that the current one (first selected)
            self.ui_connect()
            return

        if self.ui.target_radio.get_value() == 'geo':
            # the last selected row is the current row
            current_row = sel_rows[-1]

            # #########################################################################################################
            # update the form with the V-Shape fields if V-Shape selected in the geo_plugin_table
            # also modify the Cut Z form entry to reflect the calculated Cut Z from values got from V-Shape Fields
            # #########################################################################################################
            try:
                item = self.ui.tool_shape_combo
                if item is not None:
                    tool_type_txt = item.currentText()
                    self.ui_update_v_shape(tool_type_txt=tool_type_txt)
                else:
                    self.ui_connect()
                    return
            except Exception as e:
                self.app.log.error("Tool missing in ui_update_v_shape(). Add a tool in Geo Tool Table. %s" % str(e))
                self.ui_connect()
                return

        for c_row in sel_rows:
            # populate the form with the data from the tool associated with the row parameter
            try:
                item = plugin_table.item(c_row, 3)
                if type(item) is not None:
                    tooluid = item.text()
                    if self.ui.target_radio.get_value() == 'geo':
                        tooluid = int(tooluid)
                    self.storage_to_form(self.obj_tools[tooluid]['data'])
                else:
                    self.ui_connect()
                    return
            except Exception as e:
                self.app.log.error("Tool missing. Add a tool in the Tool Table. %s" % str(e))
                self.ui_connect()
                return

        self.ui_connect()

    def to_form(self, storage=None):
        if storage is None:
            storage = self.app.options

        # calculate self.currnet_row for the cellWidgets in the Tools Table
        if self.ui.target_radio.get_value() == 'geo':
            t_table = self.ui.geo_tools_table
        else:
            t_table = self.ui.tools_table
        self.current_row = t_table.currentRow()

        for k in list(self.form_fields.keys()) + list(self.general_form_fields.keys()):
            for option in storage:
                if option.startswith('tools_mill_'):
                    if k == option:
                        try:
                            if k in self.form_fields:
                                self.form_fields[k].set_value(storage[option])
                            else:
                                self.general_form_fields[k].set_value(storage[option])
                        except Exception:
                            # it may fail for form fields found in the tools tables if there are no rows
                            pass
                elif option.startswith('geometry_'):
                    if k == option.replace('geometry_', ''):
                        try:
                            if k in self.form_fields:
                                self.form_fields[k].set_value(storage[option])
                            else:
                                self.general_form_fields[k].set_value(storage[option])
                        except Exception:
                            # it may fail for form fields found in the tools tables if there are no rows
                            pass

    def storage_to_form(self, dict_storage):
        """
        Will update the GUI with data from the "storage" in this case the dict self.tools

        :param dict_storage:    A dictionary holding the data relevant for generating Gcode
        :type dict_storage:     dict
        :return:                None
        :rtype:
        """

        # we get the current row in the (geo) tools table for the form fields found in the table
        if self.ui.target_radio.get_value() == 'geo':
            t_table = self.ui.geo_tools_table
        else:
            t_table = self.ui.tools_table
        self.current_row = t_table.currentRow()

        for storage_key in dict_storage:
            if storage_key in list(self.form_fields.keys()) and storage_key not in \
                    ["tools_mill_toolchange", "tools_mill_toolchangez", "tools_mill_endxy", "tools_mill_endz",
                     "tools_mill_ppname_g", "tools_mill_area_exclusion",
                     "tools_mill_area_shape", "tools_mill_area_strategy", "tools_mill_area_overz"]:

                try:
                    self.form_fields[storage_key].set_value(dict_storage[storage_key])
                except Exception as e:
                    self.app.log.error(
                        "ToolMilling.storage_to_form() for key: %s with value: %s--> %s" %
                        (str(storage_key), str(dict_storage[storage_key]), str(e))
                    )

    def form_to_storage(self):
        """
        Will update the 'storage' attribute which is the dict self.tools with data collected from GUI

        :return:    None
        :rtype:
        """
        obj_name = self.ui.object_combo.currentText()
        if obj_name is None:
            return

        # the Target Object is Excellon
        if self.ui.target_radio.get_value() == 'exc':
            used_tools_table = self.ui.tools_table
            if used_tools_table.rowCount() == 2:
                # there is no tool in tool table so we can't save the GUI elements values to storage
                # Excellon Tool Table has 2 rows by default
                return

        # the Target Object is Geometry
        else:
            used_tools_table = self.ui.geo_tools_table
            if used_tools_table.rowCount() == 0:
                # there is no tool in tool table so we can't save the GUI elements values to storage
                return

        self.ui_disconnect()

        widget_changed = self.sender()
        wdg_objname = widget_changed.objectName()

        # if the widget objectName is '' then it is a widget that we are not interested into
        if wdg_objname == '':
            self.ui_connect()
            return

        option_changed = self.name2option[wdg_objname]

        # update the tool specific parameters
        rows = sorted(set(index.row() for index in used_tools_table.selectedIndexes()))
        for row in rows:
            if row < 0:
                row = 0
            tooluid_item = int(used_tools_table.item(row, 3).text())

            # update tool parameters
            for tooluid_key, tooluid_val in self.target_obj.tools.items():
                if int(tooluid_key) == tooluid_item:
                    if option_changed in self.form_fields:
                        new_option_value = self.form_fields[option_changed].get_value()

                        try:
                            self.target_obj.tools[tooluid_key]['data'][option_changed] = new_option_value
                        except Exception as e:
                            self.app.log.error(
                                "ToolMilling.form_to_storage() for key: %s with value: %s --> %s" %
                                (str(option_changed), str(new_option_value), str(e))
                            )

        # update the general parameters in all tools
        for tooluid_key, tooluid_val in self.target_obj.tools.items():
            if option_changed in self.general_form_fields:
                new_opt_val = self.general_form_fields[option_changed].get_value()
                try:
                    self.target_obj.tools[tooluid_key]['data'][option_changed] = new_opt_val
                except Exception as err:
                    self.app.log.error("ToolMilling.form_to_storage() general parameters --> %s" % str(err))
        self.ui_connect()

    def on_tt_change(self):
        cw = self.sender()

        tool_type = cw.currentText()
        self.ui_update_v_shape(tool_type)

        self.form_to_storage()

    def ui_update_v_shape(self, tool_type_txt):
        if tool_type_txt == 'V':
            self.ui.tipdialabel.show()
            self.ui.tipdia_entry.show()
            self.ui.tipanglelabel.show()
            self.ui.tipangle_entry.show()
            self.ui.cutzlabel.setToolTip(
                _("For V-shape tools the depth of cut is\n"
                  "calculated from other parameters like:\n"
                  "- 'V-tip Angle' -> angle at the tip of the tool\n"
                  "- 'V-tip Dia' -> diameter at the tip of the tool \n"
                  "- Tool Dia -> 'Dia' column found in the Tool Table\n"
                  "NB: a value of zero means that Tool Dia = 'V-tip Dia'")
            )
            self.ui.job_type_combo.set_value(2)   # 'Isolation'
            self.on_update_cutz()
        else:
            self.ui.tipdialabel.hide()
            self.ui.tipdia_entry.hide()
            self.ui.tipanglelabel.hide()
            self.ui.tipangle_entry.hide()
            self.ui.cutzlabel.setToolTip(
                _("Cutting depth (negative)\n"
                  "below the copper surface.")
            )
            self.ui.cutz_entry.setToolTip('')
            self.ui.job_type_combo.set_value(0)   # 'Roughing'

    def on_update_cutz(self):
        vdia = float(self.ui.tipdia_entry.get_value())
        half_vangle = float(self.ui.tipangle_entry.get_value()) / 2

        row = self.ui.geo_tools_table.currentRow()
        tool_uid_item = self.ui.geo_tools_table.item(row, 3)
        if tool_uid_item is None:
            return
        tool_uid = int(tool_uid_item.text())

        tool_dia_item = self.ui.geo_tools_table.item(row, 1)
        if tool_dia_item is None:
            return
        tooldia = float(tool_dia_item.text())

        try:
            new_cutz = (tooldia - vdia) / (2 * math.tan(math.radians(half_vangle)))
        except ZeroDivisionError:
            new_cutz = self.old_cutz

        new_cutz = self.app.dec_format(new_cutz, self.decimals) * -1.0   # this value has to be negative

        self.ui.cutz_entry.set_value(new_cutz)

        # store the new CutZ value into storage (self.tools)
        for tooluid_key, tooluid_value in self.target_obj.tools.items():
            if int(tooluid_key) == tool_uid:
                tooluid_value['data']['tools_mill_cutz'] = new_cutz

    def get_selected_tools_list(self):
        """
        Returns the keys to the self.tools dictionary corresponding
        to the selections on the tool list in the appGUI.

        :return:    List of tools.
        :rtype:     list
        """

        return [str(x.text()) for x in self.ui.tools_table.selectedItems()]

    def on_apply_param_to_all_clicked(self):
        if self.ui.tools_table.rowCount() == 0:
            # there is no tool in tool table so we can't save the GUI elements values to storage
            self.app.log.debug("ToolDrilling.on_apply_param_to_all_clicked() --> no tool in Tools Table, aborting.")
            return

        self.ui_disconnect()

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
        self.ui_connect()

    def on_order_changed(self, order):
        if order != 0:  # "default"
            self.build_ui()

    def on_tool_add(self, clicked_state, dia=None, new_geo=None):
        self.app.log.debug("GeometryObject.on_add_tool()")

        if self.target_obj is None:
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("No object is selected."))
            return

        self.ui_disconnect()

        filename = self.app.tools_database_path()

        tool_dia = dia if dia is not None else self.ui.addtool_entry.get_value()

        # construct a list of all 'tooluid' in the self.iso_tools
        tool_uid_list = [int(tooluid_key) for tooluid_key in self.target_obj.tools]

        # find maximum from the temp_uid, add 1 and this is the new 'tooluid'
        max_uid = 0 if not tool_uid_list else max(tool_uid_list)
        tooluid = int(max_uid) + 1

        new_tools_dict = deepcopy(self.default_data)
        updated_tooldia = None

        # determine the new tool diameter
        if tool_dia is None or tool_dia == 0:
            self.build_ui()
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Please enter a tool diameter with non-zero value, "
                                                        "in Float format."))
            self.ui_connect()
            return
        truncated_tooldia = self.app.dec_format(tool_dia, self.decimals)

        # load the database tools from the file
        try:
            with open(filename) as f:
                tools = f.read()
        except IOError:
            self.app.log.error("Could not load tools DB file.")
            self.app.inform.emit('[ERROR] %s' % _("Could not load Tools DB file."))
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
            self.ui_connect()
            self.on_tool_default_add(dia=tool_dia)
            return

        tool_found = 0

        # look in database tools
        for db_tool, db_tool_val in tools_db_dict.items():
            db_tooldia = db_tool_val['tooldia']
            low_limit = float(db_tool_val['data']['tol_min'])
            high_limit = float(db_tool_val['data']['tol_max'])

            # we need only tool marked for Milling Tool (Geometry Object)
            if db_tool_val['data']['tool_target'] != 1:     # _('Milling')
                continue

            # if we find a tool with the same diameter in the Tools DB just update it's data
            if truncated_tooldia == db_tooldia:
                tool_found += 1
                for d in db_tool_val['data']:
                    if d.find('tools_mill_') == 0:
                        new_tools_dict[d] = db_tool_val['data'][d]
                    elif d.find('tools_') == 0:
                        # don't need data for other App Tools; this tests after 'tools_mill_'
                        continue
                    else:
                        new_tools_dict[d] = db_tool_val['data'][d]
            # search for a tool that has a tolerance that the tool fits in
            elif high_limit >= truncated_tooldia >= low_limit:
                tool_found += 1
                updated_tooldia = db_tooldia
                for d in db_tool_val['data']:
                    if d.find('tools_mill_') == 0:
                        new_tools_dict[d] = db_tool_val['data'][d]
                    elif d.find('tools_') == 0:
                        # don't need data for other App Tools; this tests after 'tools_mill_'
                        continue
                    else:
                        new_tools_dict[d] = db_tool_val['data'][d]

        # test we found a suitable tool in Tools Database or if multiple ones
        if tool_found == 0:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Tool not in Tools Database. Adding a default tool."))
            self.on_tool_default_add(dia=tool_dia, new_geo=new_geo)
            self.ui_connect()
            return

        # if we found more than one tool then message "warning" and return
        if tool_found > 1:
            self.app.inform.emit(
                '[WARNING_NOTCL] %s' % _("Cancelled.\n"
                                         "Multiple tools for one tool diameter found in Tools Database."))
            self.ui_connect()
            return

        # i we found only one tool then go forward and add it
        new_tdia = deepcopy(updated_tooldia) if updated_tooldia is not None else deepcopy(truncated_tooldia)
        self.target_obj.tools.update({
            tooluid: {
                'tooldia':          new_tdia,
                'data':             deepcopy(new_tools_dict),
                'solid_geometry':   self.target_obj.solid_geometry
            }
        })
        self.ui_connect()
        self.build_ui()
        self.target_obj.build_ui()

        # select the tool just added
        for row in range(self.ui.geo_tools_table.rowCount()):
            if int(self.ui.geo_tools_table.item(row, 3).text()) == tooluid:
                self.ui.geo_tools_table.selectRow(row)
                break

        # update the UI form
        self.update_ui()

        # if there is at least one tool left in the Tools Table, enable the parameters GUI
        if self.ui.geo_tools_table.rowCount() != 0:
            self.ui.param_frame.setDisabled(False)

        self.app.inform.emit('[success] %s' % _("New tool added to Tool Table from Tools Database."))

    def on_tool_default_add(self, dia=None, new_geo=None, muted=None):
        self.ui_disconnect()

        tooldia = dia if dia is not None else self.ui.addtool_entry.get_value()

        if tooldia == 0.0:
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Please enter a tool diameter with non-zero value, "
                                                        "in Float format."))
            self.ui_connect()
            return 'fail'

        tool_uid_list = [int(tooluid_key) for tooluid_key in self.target_obj.tools]

        # find maximum from the temp_uid, add 1 and this is the new 'tooluid'
        max_uid = max(tool_uid_list) if tool_uid_list else 0
        self.tooluid = int(max_uid) + 1

        tooldia = self.app.dec_format(tooldia, self.decimals)

        # here we actually add the new tool; if there is no tool in the tool table we add a tool with default data
        # otherwise we add a tool with data copied from last tool
        if self.target_obj.tools:
            last_data = self.target_obj.tools[max_uid]['data']
            last_solid_geometry = self.target_obj.tools[max_uid]['solid_geometry'] if new_geo is None else new_geo

            # if previous geometry was empty (it may happen for the first tool added)
            # then copy the object.solid_geometry
            if not last_solid_geometry:
                last_solid_geometry = self.target_obj.solid_geometry

            self.target_obj.tools.update({
                self.tooluid: {
                    'tooldia':          tooldia,
                    'data':             deepcopy(last_data),
                    'solid_geometry':   deepcopy(last_solid_geometry)
                }
            })
        else:
            self.target_obj.tools.update({
                self.tooluid: {
                    'tooldia':          tooldia,
                    'data':             deepcopy(self.default_data),
                    'solid_geometry':   self.solid_geometry
                }
            })

        self.target_obj.tools[self.tooluid]['data']['name'] = deepcopy(self.target_obj.options['name'])

        # we do this HACK to make sure the tools attribute to be serialized is updated in the self.ser_attrs list
        try:
            self.target_obj.ser_attrs.remove('tools')
        except TypeError:
            pass
        self.target_obj.ser_attrs.append('tools')

        if muted is None:
            self.app.inform.emit('[success] %s' % _("Tool added in Tool Table."))

        self.ui_connect()
        self.build_ui()
        self.target_obj.build_ui()

        # if there is at least one tool left in the Tools Table, enable the parameters GUI
        if self.ui.geo_tools_table.rowCount() != 0:
            self.ui.param_frame.setDisabled(False)

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
        ret_val = self.app.on_tools_database()
        if ret_val == 'fail':
            return
        self.app.tools_db_tab.ok_to_add = True
        self.app.tools_db_tab.ui.buttons_frame.hide()
        self.app.tools_db_tab.ui.add_tool_from_db.show()
        self.app.tools_db_tab.ui.cancel_tool_from_db.show()

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
        tool_uid_list = []
        for tooluid_key in self.target_obj.tools:
            tool_uid_item = int(tooluid_key)
            tool_uid_list.append(tool_uid_item)

        # find maximum from the temp_uid, add 1 and this is the new 'tooluid'
        if not tool_uid_list:
            max_uid = 0
        else:
            max_uid = max(tool_uid_list)
        self.tooluid = max_uid + 1

        tooldia = float('%.*f' % (self.decimals, tooldia))

        self.target_obj.tools.update({
            self.tooluid: {
                'tooldia': tooldia,
                'data': deepcopy(tool['data']),
                'solid_geometry': self.target_obj.solid_geometry
            }
        })

        self.target_obj.tools[self.tooluid]['data']['name'] = deepcopy(self.target_obj.options['name'])

        # we do this HACK to make sure the tools attribute to be serialized is updated in the self.ser_attrs list
        try:
            self.target_obj.ser_attrs.remove('tools')
        except TypeError:
            pass
        self.target_obj.ser_attrs.append('tools')

        self.ui_connect()
        self.build_ui()

        # if there is no tool left in the Tools Table, enable the parameters appGUI
        if self.ui.geo_tools_table.rowCount() != 0:
            self.ui.param_frame.setDisabled(False)

    def on_tool_edit(self, current_item):
        self.ui_disconnect()

        current_row = current_item.row()
        try:
            dia = float(self.ui.geo_tools_table.item(current_row, 1).text())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                dia = float(self.ui.geo_tools_table.item(current_row, 1).text().replace(',', '.'))
            except ValueError:
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("Wrong value format entered, use a number."))
                return
        except AttributeError:
            self.ui_connect()
            return

        tool_dia = self.app.dec_format(dia, self.decimals)
        tooluid = int(self.ui.geo_tools_table.item(current_row, 3).text())

        # update Tool dia
        self.target_obj.tools[tooluid]['tooldia'] = deepcopy(tool_dia)
        self.target_obj.tools[tooluid]['data']['tools_mill_tooldia'] = deepcopy(tool_dia)

        # update Cut Z if the tool has a V shape tool
        if self.ui.tool_shape_combo.get_value() == 5:   # 'V'
            self.on_update_cutz()

        try:
            self.target_obj.ser_attrs.remove('tools')
            self.target_obj.ser_attrs.append('tools')
        except (TypeError, ValueError):
            pass

        self.app.inform.emit('[success] %s' % _("Tool was edited in Tool Table."))
        self.ui_connect()
        self.builduiSig.emit()
        self.target_obj.build_ui()

    def on_tool_copy(self, all_tools=None):
        self.ui_disconnect()

        # find the tool_uid maximum value in the self.tools
        uid_list = []
        for key in self.target_obj.tools:
            uid_list.append(int(key))
        try:
            max_uid = max(uid_list, key=int)
        except ValueError:
            max_uid = 0

        if all_tools is None:
            if self.ui.geo_tools_table.selectedItems():
                for current_row in self.ui.geo_tools_table.selectedItems():
                    # sometime the header get selected and it has row number -1
                    # we don't want to do anything with the header :)
                    if current_row.row() < 0:
                        continue
                    try:
                        tooluid_copy = int(self.ui.geo_tools_table.item(current_row.row(), 3).text())
                        max_uid += 1
                        self.target_obj.tools[int(max_uid)] = deepcopy(self.target_obj.tools[tooluid_copy])
                    except AttributeError:
                        self.app.inform.emit('[WARNING_NOTCL] %s' % _("Failed. Select a tool to copy."))
                        self.ui_connect()
                        self.builduiSig.emit()
                        return
                    except Exception as e:
                        self.app.log.error("on_tool_copy() --> " + str(e))
                # deselect the table
                # self.ui.geo_tools_table.clearSelection()
            else:
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("Failed. Select a tool to copy."))
                self.ui_connect()
                self.builduiSig.emit()
                return
        else:
            # we copy all tools in geo_tools_table
            try:
                temp_tools = deepcopy(self.target_obj.tools)
                max_uid += 1
                for tooluid in temp_tools:
                    self.target_obj.tools[int(max_uid)] = deepcopy(temp_tools[tooluid])
                temp_tools.clear()
            except Exception as e:
                self.app.log.error("on_tool_copy() --> " + str(e))

        # we do this HACK to make sure the tools attribute to be serialized is updated in the self.ser_attrs list
        try:
            self.target_obj.ser_attrs.remove('tools')
        except ValueError:
            pass
        self.target_obj.ser_attrs.append('tools')

        self.ui_connect()
        self.builduiSig.emit()
        self.app.inform.emit('[success] %s' % _("Tool was copied in Tool Table."))

    def on_tool_delete(self, clicked_signal, all_tools=None):
        """
        It's important to keep the not clicked_signal parameter otherwise the signal will go to the all_tools
        parameter and I might get all the tool deleted
        """
        self.ui_disconnect()

        if all_tools is None:
            if self.ui.geo_tools_table.selectedItems():
                for current_row in self.ui.geo_tools_table.selectedItems():
                    # sometime the header get selected and it has row number -1
                    # we don't want to do anything with the header :)
                    if current_row.row() < 0:
                        continue
                    try:
                        tooluid_del = int(self.ui.geo_tools_table.item(current_row.row(), 3).text())

                        temp_tools = deepcopy(self.target_obj.tools)
                        for tooluid_key in self.target_obj.tools:
                            if int(tooluid_key) == tooluid_del:
                                # if the self.tools has only one tool and we delete it then we move the solid_geometry
                                # as a property of the object otherwise there will be nothing to hold it
                                if len(self.target_obj.tools) == 1:
                                    self.target_obj.solid_geometry = deepcopy(
                                        self.target_obj.tools[tooluid_key]['solid_geometry']
                                    )
                                temp_tools.pop(tooluid_del, None)
                        self.target_obj.tools = deepcopy(temp_tools)
                        temp_tools.clear()
                    except AttributeError:
                        self.app.inform.emit('[WARNING_NOTCL] %s' % _("Failed. Select a tool to delete."))
                        self.ui_connect()
                        self.builduiSig.emit()
                        return
                    except Exception as e:
                        self.app.log.error("on_tool_delete() --> " + str(e))
                # deselect the table
                # self.ui.geo_tools_table.clearSelection()
            else:
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("Failed. Select a tool to delete."))
                self.ui_connect()
                self.builduiSig.emit()
                return
        else:
            # we delete all tools in geo_tools_table
            self.target_obj.tools.clear()

        self.app.plot_all()

        # we do this HACK to make sure the tools attribute to be serialized is updated in the self.ser_attrs list
        try:
            self.target_obj.ser_attrs.remove('tools')
        except TypeError:
            pass
        self.target_obj.ser_attrs.append('tools')

        self.ui_connect()

        self.build_ui()
        self.target_obj.build_ui()
        self.app.inform.emit('[success] %s' % _("Tool was deleted in Tool Table."))

        obj_active = self.target_obj
        # if the object was MultiGeo and now it has no tool at all (therefore no geometry)
        # we make it back SingleGeo
        if self.ui.geo_tools_table.rowCount() <= 0:
            obj_active.multigeo = False
            obj_active.options['xmin'] = 0
            obj_active.options['ymin'] = 0
            obj_active.options['xmax'] = 0
            obj_active.options['ymax'] = 0

        if obj_active.multigeo is True:
            try:
                xmin, ymin, xmax, ymax = obj_active.bounds()
                obj_active.options['xmin'] = xmin
                obj_active.options['ymin'] = ymin
                obj_active.options['xmax'] = xmax
                obj_active.options['ymax'] = ymax
            except Exception:
                obj_active.options['xmin'] = 0
                obj_active.options['ymin'] = 0
                obj_active.options['xmax'] = 0
                obj_active.options['ymax'] = 0

        # if there is no tool left in the Tools Table, disable the parameters appGUI
        if self.ui.geo_tools_table.rowCount() == 0:
            self.ui.param_frame.setDisabled(True)

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
            outname = self.target_obj.options["name"] + "_mill"

        if tooldia is None:
            tooldia = float(self.target_obj.options["tooldia"])

        # Sort tools by diameter. items() -> [('name', diameter), ...]
        sorted_tools = sorted(list(self.tools.items()), key=lambda tl: tl[1]['tooldia'])

        # sort = []
        # for k, v in self.tools.items():
        #     sort.append((k, v.get('tooldia')))
        # sorted_tools = sorted(sort, key=lambda t1: t1[1])

        if tools == "all":
            tools = [i[0] for i in sorted_tools]  # List if ordered tool names.
            self.app.log.debug("Tools 'all' and sorted are: %s" % str(tools))

        if len(tools) == 0:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Please select one or more tools from the list and try again."))
            return False, "Error: No tools."

        for tool in tools:
            if tooldia > self.tools[tool]['data']['tools_mill_tooldia']:
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

            geo_obj.options['type'] = 'Excellon Geometry'
            geo_obj.options["tools_mill_tooldia"] = str(tooldia)
            geo_obj.options["tools_mill_multidepth"] = self.target_obj.options["tools_mill_multidepth"]
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
            outname = self.target_obj.options["name"] + "_slots"

        if tooldia is None:
            tooldia = float(self.target_obj.options["slot_tooldia"])

        # Sort tools by diameter. items() -> [('name', diameter), ...]
        sorted_tools = sorted(list(self.tools.items()), key=lambda tl: tl[1]['tooldia'])
        #
        # sort = []
        # for k, v in self.tools.items():
        #     sort.append((k, v.get('tooldia')))
        # sorted_tools = sorted(sort, key=lambda t1: t1[1])

        if tools == "all":
            tools = [i[0] for i in sorted_tools]  # List if ordered tool names.
            self.app.log.debug("Tools 'all' and sorted are: %s" % str(tools))

        if len(tools) == 0:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Please select one or more tools from the list and try again."))
            return False, "Error: No tools."

        for tool in tools:
            # I add the 0.0001 value to account for the rounding error in converting from IN to MM and reverse
            adj_toolstable_tooldia = float('%.*f' % (self.decimals, float(tooldia)))
            adj_file_tooldia = float('%.*f' % (self.decimals, float(self.tools[tool]['data']['tools_mill_tooldia'])))
            if adj_toolstable_tooldia > adj_file_tooldia + 0.0001:
                self.app.inform.emit('[ERROR_NOTCL] %s' %
                                     _("Milling tool for SLOTS is larger than hole size. Cancelled."))
                return False, "Error: Milling tool is larger than hole."

        def geo_init(geo_obj, app_obj):
            assert geo_obj.kind == 'geometry', "Initializer expected a GeometryObject, got %s" % type(geo_obj)

            app_obj.inform.emit(_("Generating slot milling geometry..."))

            # ## Add properties to the object

            geo_obj.options['type'] = 'Excellon Geometry'
            geo_obj.options["tools_mill_tooldia"] = str(tooldia)
            geo_obj.options["tools_mill_multidepth"] = self.target_obj.options["tools_mill_multidepth"]
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

    def on_generate_cncjob_click(self):
        self.app.delete_selection_shape()

        self.obj_name = self.ui.object_combo.currentText()

        # Get source object.
        try:
            self.target_obj = self.app.collection.get_by_name(self.obj_name)
        except Exception as e:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), str(self.obj_name)))
            return "Could not retrieve object: %s with error: %s" % (self.obj_name, str(e))

        if self.target_obj is None:
            self.app.inform.emit('[ERROR_NOTCL] %s.' % _("Object not found"))
            return

        if self.target_obj.kind == 'geometry':
            self.on_generatecnc_from_geo()
        elif self.target_obj.kind == 'excellon':
            pass

    def on_generatecnc_from_geo(self):
        self.app.log.debug("Generating CNCJob from Geometry ...")

        self.sel_tools.clear()

        self.obj_name = self.ui.object_combo.currentText()

        # Get source object.
        try:
            self.target_obj = self.app.collection.get_by_name(self.obj_name)
        except Exception as e:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), str(self.obj_name)))
            return "Could not retrieve object: %s with error: %s" % (self.obj_name, str(e))

        if self.target_obj is None:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Object not found"), str(self.obj_name)))
            return

        try:
            if self.target_obj.special_group:
                msg = '[WARNING_NOTCL] %s %s %s.' % \
                      (
                          _("This Geometry can't be processed because it is"),
                          str(self.target_obj.special_group),
                          _("Geometry")
                      )
                self.app.inform.emit(msg)
                return
        except AttributeError:
            pass

        # test to see if we have tools available in the tool table
        if self.ui.geo_tools_table.selectedItems():
            for x in self.ui.geo_tools_table.selectedItems():
                tooluid = int(self.ui.geo_tools_table.item(x.row(), 3).text())

                for tooluid_key, tooluid_value in self.target_obj.tools.items():
                    if int(tooluid_key) == tooluid:
                        self.sel_tools.update({
                            tooluid: deepcopy(tooluid_value)
                        })

            self.mtool_gen_cncjob()
            # self.ui.geo_tools_table.clearSelection()

        elif self.ui.geo_tools_table.rowCount() == 1:
            tooluid = int(self.ui.geo_tools_table.item(0, 3).text())

            for tooluid_key, tooluid_value in self.target_obj.tools.items():
                if int(tooluid_key) == tooluid:
                    self.sel_tools.update({
                        tooluid: deepcopy(tooluid_value)
                    })
            self.mtool_gen_cncjob()
            # self.ui.geo_tools_table.clearSelection()
        else:
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed. No tool selected in the tool table ..."))

        # for tooluid_key in list(self.sel_tools.keys()):
        #     # Tooldia update
        #     tooldia_val = self.app.dec_format(
        #         float(self.sel_tools[tooluid_key]['data']['tools_mill_tooldia']), self.decimals)
        #     print(tooldia_val)

    def mtool_gen_cncjob(self, outname=None, tools_dict=None, tools_in_use=None, segx=None, segy=None, toolchange=None,
                         plot=True, use_thread=True):
        """
        Creates a multi-tool CNCJob out of this Geometry object.
        The actual work is done by the target CNCJobObject object's
        `generate_from_geometry_2()` method.

        :param toolchange:
        :param outname:
        :param tools_dict:      a dictionary that holds the whole data needed to create the Gcode
                                (including the solid_geometry)
        :param tools_in_use:    the tools that are used, needed by some preprocessors
        :type  tools_in_use     list of lists, each list in the list is made out of row elements of tools table from GUI
        :param segx:            number of segments on the X axis, for auto-levelling
        :param segy:            number of segments on the Y axis, for auto-levelling
        :param plot:            if True the generated object will be plotted; if False will not be plotted
        :param use_thread:      if True use threading
        :return:                None
        """

        # use the name of the first tool selected in self.geo_tools_table which has the diameter passed as tool_dia
        outname = "%s_%s" % (self.target_obj.options["name"], 'cnc') if outname is None else outname

        tools_dict = self.sel_tools if tools_dict is None else tools_dict
        if not self.target_obj.tools:
            segx = segx if segx is not None else float(self.target_obj.options['segx'])
            segy = segy if segy is not None else float(self.target_obj.options['segy'])
        else:
            tools_list = list(self.target_obj.tools.keys())
            # the segx and segy values are the same for all tools os we just take the values from the first tool
            sel_tool = tools_list[0]
            data_dict = self.target_obj.tools[sel_tool]['data']
            segx = data_dict['segx']
            segy = data_dict['segy']

        try:
            xmin = self.target_obj.options['xmin']
            ymin = self.target_obj.options['ymin']
            xmax = self.target_obj.options['xmax']
            ymax = self.target_obj.options['ymax']
        except Exception as e:
            self.app.log.error("FlatCAMObj.GeometryObject.mtool_gen_cncjob() --> %s\n" % str(e))

            msg = '[ERROR] %s' % _("An internal error has occurred. See shell.\n")
            msg += '%s' % str(e)
            msg += traceback.format_exc()
            self.app.inform.emit(msg)
            return

        # force everything as MULTI-GEO
        # self.multigeo = True

        is_toolchange = toolchange if toolchange is not None else self.ui.toolchange_cb.get_value()

        # Object initialization function for app.app_obj.new_object()
        # RUNNING ON SEPARATE THREAD!
        def job_init_single_geometry(new_cncjob_obj, app_obj):
            self.app.log.debug("Creating a CNCJob out of a single-geometry")
            assert new_cncjob_obj.kind == 'cncjob', "Initializer expected a CNCJobObject, got %s" % type(new_cncjob_obj)

            new_cncjob_obj.options['xmin'] = xmin
            new_cncjob_obj.options['ymin'] = ymin
            new_cncjob_obj.options['xmax'] = xmax
            new_cncjob_obj.options['ymax'] = ymax

            # count the tools
            tool_cnt = 0

            # dia_cnc_dict = {}

            # this turn on the FlatCAMCNCJob plot for multiple tools
            new_cncjob_obj.multitool = True
            new_cncjob_obj.multigeo = False
            new_cncjob_obj.tools.clear()

            new_cncjob_obj.segx = segx
            new_cncjob_obj.segy = segy

            new_cncjob_obj.z_pdepth = float(self.target_obj.options["tools_mill_z_pdepth"])
            new_cncjob_obj.feedrate_probe = float(self.target_obj.options["tools_mill_feedrate_probe"])

            total_gcode = ''
            for tooluid_key in list(tools_dict.keys()):
                tool_cnt += 1

                dia_cnc_dict = deepcopy(tools_dict[tooluid_key])
                tooldia_val = app_obj.dec_format(
                    float(tools_dict[tooluid_key]['data']['tools_mill_tooldia']), self.decimals)
                dia_cnc_dict['data']['tools_mill_tooldia'] = tooldia_val

                if "optimization_type" not in tools_dict[tooluid_key]['data']:
                    def_optimization_type = self.target_obj.options["tools_mill_optimization_type"]
                    tools_dict[tooluid_key]['data']["tools_mill_optimization_type"] = def_optimization_type

                if dia_cnc_dict['data']['tools_mill_offset_type'] == 1:  # 'in'
                    tool_offset = -dia_cnc_dict['tools_mill_tooldia'] / 2
                elif dia_cnc_dict['data']['tools_mill_offset_type'] == 2:  # 'out'
                    tool_offset = dia_cnc_dict['tools_mill_tooldia'] / 2
                elif dia_cnc_dict['data']['tools_mill_offset_type'] == 3:  # 'custom'
                    try:
                        offset_value = float(self.ui.offset_entry.get_value())
                    except ValueError:
                        # try to convert comma to decimal point. if it's still not working error message and return
                        try:
                            offset_value = float(self.ui.offset_entry.get_value().replace(',', '.'))
                        except ValueError:
                            app_obj.inform.emit('[ERROR_NOTCL] %s' % _("Wrong value format entered, use a number."))
                            return
                    if offset_value:
                        tool_offset = float(offset_value)
                    else:
                        app_obj.inform.emit(
                            '[WARNING] %s' % _("Tool Offset is selected in Tool Table but no value is provided.\n"
                                               "Add a Tool Offset or change the Offset Type.")
                        )
                        return
                else:
                    tool_offset = 0.0

                dia_cnc_dict['data']['tools_mill_offset_value'] = tool_offset

                z_cut = tools_dict[tooluid_key]['data']["tools_mill_cutz"]
                z_move = tools_dict[tooluid_key]['data']["tools_mill_travelz"]
                feedrate = tools_dict[tooluid_key]['data']["tools_mill_feedrate"]
                feedrate_z = tools_dict[tooluid_key]['data']["tools_mill_feedrate_z"]
                feedrate_rapid = tools_dict[tooluid_key]['data']["tools_mill_feedrate_rapid"]
                multidepth = tools_dict[tooluid_key]['data']["tools_mill_multidepth"]
                extracut = tools_dict[tooluid_key]['data']["tools_mill_extracut"]
                extracut_length = tools_dict[tooluid_key]['data']["tools_mill_extracut_length"]
                depthpercut = tools_dict[tooluid_key]['data']["tools_mill_depthperpass"]
                toolchange = tools_dict[tooluid_key]['data']["tools_mill_toolchange"]
                toolchangez = tools_dict[tooluid_key]['data']["tools_mill_toolchangez"]
                toolchangexy = tools_dict[tooluid_key]['data']["tools_mill_toolchangexy"]
                startz = tools_dict[tooluid_key]['data']["tools_mill_startz"]
                endz = tools_dict[tooluid_key]['data']["tools_mill_endz"]
                endxy = self.target_obj.options["tools_mill_endxy"]
                spindlespeed = tools_dict[tooluid_key]['data']["tools_mill_spindlespeed"]
                dwell = tools_dict[tooluid_key]['data']["tools_mill_dwell"]
                dwelltime = tools_dict[tooluid_key]['data']["tools_mill_dwelltime"]
                pp_geometry_name = tools_dict[tooluid_key]['data']["tools_mill_ppname_g"]

                spindledir = self.app.defaults['tools_mill_spindledir']
                tool_solid_geometry = self.solid_geometry

                new_cncjob_obj.coords_decimals = self.app.defaults["cncjob_coords_decimals"]
                new_cncjob_obj.fr_decimals = self.app.defaults["cncjob_fr_decimals"]

                # Propagate options
                new_cncjob_obj.options["tooldia"] = tooldia_val
                new_cncjob_obj.options['type'] = 'Geometry'
                new_cncjob_obj.options['tool_dia'] = tooldia_val

                tool_lst = list(tools_dict.keys())
                is_first = True if tooluid_key == tool_lst[0] else False

                # it seems that the tolerance needs to be a lot lower value than 0.01 and it was hardcoded initially
                # to a value of 0.0005 which is 20 times less than 0.01
                glob_tol = float(self.app.defaults['global_tolerance'])
                tol = glob_tol / 20 if self.units.lower() == 'in' else glob_tol

                res, start_gcode = new_cncjob_obj.generate_from_geometry_2(
                    self.target_obj, tooldia=tooldia_val, offset=tool_offset, tolerance=tol,
                    z_cut=z_cut, z_move=z_move,
                    feedrate=feedrate, feedrate_z=feedrate_z, feedrate_rapid=feedrate_rapid,
                    spindlespeed=spindlespeed, spindledir=spindledir, dwell=dwell, dwelltime=dwelltime,
                    multidepth=multidepth, depthpercut=depthpercut,
                    extracut=extracut, extracut_length=extracut_length, startz=startz, endz=endz, endxy=endxy,
                    toolchange=toolchange, toolchangez=toolchangez, toolchangexy=toolchangexy,
                    pp_geometry_name=pp_geometry_name,
                    tool_no=tool_cnt, is_first=is_first)

                if res == 'fail':
                    self.app.log.debug("GeometryObject.mtool_gen_cncjob() --> generate_from_geometry2() failed")
                    return 'fail'

                dia_cnc_dict['gcode'] = res
                if start_gcode != '':
                    new_cncjob_obj.gc_start = start_gcode

                total_gcode += res

                self.app.inform.emit('[success] %s' % _("G-Code parsing in progress..."))
                dia_cnc_dict['gcode_parsed'] = new_cncjob_obj.gcode_parse(tool_data=tools_dict[tooluid_key]['data'])
                app_obj.inform.emit('[success] %s' % _("G-Code parsing finished..."))

                # commented this; there is no need for the actual GCode geometry - the original one will serve as well
                # for bounding box values
                # dia_cnc_dict['solid_geometry'] = unary_union([geo['geom'] for geo in dia_cnc_dict['gcode_parsed']])
                try:
                    dia_cnc_dict['solid_geometry'] = tool_solid_geometry
                    app_obj.inform.emit('[success] %s...' % _("Finished G-Code processing"))
                except Exception as er:
                    app_obj.inform.emit('[ERROR] %s: %s' % (_("G-Code processing failed with error"), str(er)))

                new_cncjob_obj.tools.update({
                    tooluid_key: deepcopy(dia_cnc_dict)
                })
                dia_cnc_dict.clear()

            new_cncjob_obj.source_file = new_cncjob_obj.gc_start + total_gcode

        # Object initialization function for app.app_obj.new_object()
        # RUNNING ON SEPARATE THREAD!
        def job_init_multi_geometry(new_cncjob_obj, app_obj):
            self.app.log.debug("Creating a CNCJob out of a multi-geometry")
            assert new_cncjob_obj.kind == 'cncjob', "Initializer expected a CNCJobObject, got %s" % type(new_cncjob_obj)

            new_cncjob_obj.options['xmin'] = xmin
            new_cncjob_obj.options['ymin'] = ymin
            new_cncjob_obj.options['xmax'] = xmax
            new_cncjob_obj.options['ymax'] = ymax

            # count the tools
            tool_cnt = 0

            # dia_cnc_dict = {}

            # this turn on the FlatCAMCNCJob plot for multiple tools
            new_cncjob_obj.multitool = True
            new_cncjob_obj.multigeo = True
            new_cncjob_obj.tools.clear()

            new_cncjob_obj.segx = segx
            new_cncjob_obj.segy = segy

            new_cncjob_obj.z_pdepth = float(self.target_obj.options["tools_mill_z_pdepth"])
            new_cncjob_obj.feedrate_probe = float(self.target_obj.options["tools_mill_feedrate_probe"])

            # make sure that trying to make a CNCJob from an empty file is not creating an app crash
            if not self.target_obj.solid_geometry:
                a = 0
                for tooluid_key in self.target_obj.tools:
                    if self.target_obj.tools[tooluid_key]['solid_geometry'] is None:
                        a += 1
                if a == len(self.target_obj.tools):
                    app_obj.inform.emit('[ERROR_NOTCL] %s...' % _('Cancelled. Empty file, it has no geometry'))
                    return 'fail'

            total_gcode = ''
            for tooluid_key in list(tools_dict.keys()):
                tool_cnt += 1
                dia_cnc_dict = deepcopy(tools_dict[tooluid_key])

                # Tooldia update
                tooldia_val = app_obj.dec_format(
                    float(tools_dict[tooluid_key]['data']['tools_mill_tooldia']), self.decimals)
                dia_cnc_dict['data']['tools_mill_tooldia'] = deepcopy(tooldia_val)

                if "optimization_type" not in tools_dict[tooluid_key]['data']:
                    def_optimization_type = self.target_obj.options["tools_mill_optimization_type"]
                    tools_dict[tooluid_key]['data']["tools_mill_optimization_type"] = def_optimization_type

                job_type = tools_dict[tooluid_key]['data']['tools_mill_job_type']
                if job_type == 3:   # Polishing
                    self.app.log.debug("Painting the polished area ...")

                    margin = tools_dict[tooluid_key]['data']['tools_mill_polish_margin']
                    overlap = tools_dict[tooluid_key]['data']['tools_mill_polish_overlap'] / 100
                    paint_method = tools_dict[tooluid_key]['data']['tools_mill_polish_method']

                    # create the Paint geometry for this tool
                    bbox = box(xmin-margin, ymin-margin, xmax+margin, ymax+margin)
                    print(bbox.wkt)
                    print(margin, overlap, paint_method)

                    # paint the box
                    try:
                        # provide the app with a way to process the GUI events when in a blocking loop
                        QtWidgets.QApplication.processEvents()
                        if self.app.abort_flag:
                            # graceful abort requested by the user
                            raise grace

                        # Type(cpoly) == FlatCAMRTreeStorage | None
                        cpoly = None
                        if paint_method == 0:  # Standard
                            cpoly = self.clear_polygon(bbox,
                                                       tooldia=tooldia_val,
                                                       steps_per_circle=self.circle_steps,
                                                       overlap=overlap,
                                                       contour=True,
                                                       connect=True,
                                                       prog_plot=False)
                        elif paint_method == 1:  # Seed
                            cpoly = self.clear_polygon2(bbox,
                                                        tooldia=tooldia_val,
                                                        steps_per_circle=self.circle_steps,
                                                        overlap=overlap,
                                                        contour=True,
                                                        connect=True,
                                                        prog_plot=False)
                        elif paint_method == 2:  # Lines
                            cpoly = self.clear_polygon3(bbox,
                                                        tooldia=tooldia_val,
                                                        steps_per_circle=self.circle_steps,
                                                        overlap=overlap,
                                                        contour=True,
                                                        connect=True,
                                                        prog_plot=False)

                        if not cpoly or not cpoly.objects:
                            self.app.inform.emit('[ERROR_NOTCL] %s' % _('Geometry could not be painted completely'))
                            return

                        paint_geo = [g for g in cpoly.get_objects() if g and not g.is_empty]
                    except grace:
                        return "fail"
                    except Exception as ero:
                        self.app.log.error("Could not Paint the polygons. %s" % str(ero))
                        mssg = '[ERROR] %s\n%s' % (_("Could not do Paint. Try a different combination of parameters. "
                                                     "Or a different method of Paint"), str(ero))
                        self.app.inform.emit(mssg)
                        return

                    tools_dict[tooluid_key]['solid_geometry'] = paint_geo
                    self.app.log.debug("Finished painting the polished area ...")

                # #####################################################################################################
                # ############################ COMMON Parameters ######################################################
                # #####################################################################################################

                # Toolchange Z
                tools_dict[tooluid_key]['data']['toolchangez'] = self.ui.toolchangez_entry.get_value()
                # End Move Z
                tools_dict[tooluid_key]['data']['endz'] = self.ui.endz_entry.get_value()
                # End Move XY
                tools_dict[tooluid_key]['data']['endxy'] = self.ui.endxy_entry.get_value()
                # Probe Z
                tools_dict[tooluid_key]['data']['z_pdepth'] = self.ui.pdepth_entry.get_value()
                # Probe FR
                tools_dict[tooluid_key]['data']['feedrate_probe'] = self.ui.feedrate_probe_entry.get_value()

                # Exclusion Areas Enable
                tools_dict[tooluid_key]['data']['area_exclusion'] = self.ui.exclusion_cb.get_value()
                # Exclusion Areas Shape
                tools_dict[tooluid_key]['data']['area_shape'] = self.ui.area_shape_radio.get_value()
                # Exclusion Areas Strategy
                tools_dict[tooluid_key]['data']['area_strategy'] = self.ui.strategy_radio.get_value()
                # Exclusion Areas Overz
                tools_dict[tooluid_key]['data']['area_overz'] = self.ui.over_z_entry.get_value()

                # Preprocessor
                tools_dict[tooluid_key]['data']['ppname_g'] = self.ui.pp_geo_name_cb.get_value()

                # Offset calculation
                offset_type = dia_cnc_dict['data']['tools_mill_offset_type']
                if offset_type == 1:    # 'in'
                    tool_offset = -tooldia_val / 2
                elif offset_type == 2:  # 'out'
                    tool_offset = tooldia_val / 2
                elif offset_type == 3:  # 'custom'
                    offset_value = self.ui.offset_entry.get_value()
                    if offset_value:
                        tool_offset = float(offset_value)
                    else:
                        self.app.inform.emit('[WARNING] %s' %
                                             _("Tool Offset is selected in Tool Table but "
                                               "no value is provided.\n"
                                               "Add a Tool Offset or change the Offset Type."))
                        return
                else:
                    tool_offset = 0.0

                dia_cnc_dict['data']['tools_mill_offset_value'] = tool_offset

                # Solid Geometry
                tool_solid_geometry = self.target_obj.tools[tooluid_key]['solid_geometry']

                # Coordinates
                new_cncjob_obj.coords_decimals = self.app.defaults["cncjob_coords_decimals"]
                new_cncjob_obj.fr_decimals = self.app.defaults["cncjob_fr_decimals"]

                # Propagate options
                new_cncjob_obj.options["tooldia"] = tooldia_val
                new_cncjob_obj.options['type'] = 'Geometry'
                new_cncjob_obj.options['tool_dia'] = tooldia_val

                # it seems that the tolerance needs to be a lot lower value than 0.01 and it was hardcoded initially
                # to a value of 0.0005 which is 20 times less than 0.01
                glob_tol = float(self.app.defaults['global_tolerance'])
                tol = glob_tol / 20 if self.units.lower() == 'in' else glob_tol

                tool_lst = list(tools_dict.keys())
                is_first = True if tooluid_key == tool_lst[0] else False
                is_last = True if tooluid_key == tool_lst[-1] else False
                res, start_gcode = new_cncjob_obj.geometry_tool_gcode_gen(tooluid_key, tools_dict, first_pt=(0, 0),
                                                                          tolerance=tol,
                                                                          is_first=is_first, is_last=is_last,
                                                                          toolchange=is_toolchange)
                if res == 'fail':
                    self.app.log.debug("ToolMilling.mtool_gen_cncjob() --> geometry_tool_gcode_gen() failed")
                    return 'fail'

                # Store the GCode
                dia_cnc_dict['gcode'] = res
                total_gcode += res

                if start_gcode != '':
                    new_cncjob_obj.gc_start = start_gcode

                app_obj.inform.emit('[success] %s' % _("G-Code parsing in progress..."))
                dia_cnc_dict['gcode_parsed'] = new_cncjob_obj.gcode_parse(tool_data=tools_dict[tooluid_key]['data'])
                app_obj.inform.emit('[success] %s' % _("G-Code parsing finished..."))

                # commented this; there is no need for the actual GCode geometry - the original one will serve as well
                # for bounding box values
                # geo_for_bound_values = unary_union([
                #     geo['geom'] for geo in dia_cnc_dict['gcode_parsed'] if geo['geom'].is_valid is True
                # ])
                try:
                    dia_cnc_dict['solid_geometry'] = deepcopy(tool_solid_geometry)
                    app_obj.inform.emit('[success] %s...' % _("Finished G-Code processing"))
                except Exception as ee:
                    app_obj.inform.emit('[ERROR] %s: %s' % (_("G-Code processing failed with error"), str(ee)))

                # tell gcode_parse from which point to start drawing the lines depending on what kind of
                # object is the source of gcode

                # Update the CNCJob tools dictionary
                new_cncjob_obj.tools.update({
                    tooluid_key: deepcopy(dia_cnc_dict)
                })
                dia_cnc_dict.clear()

            new_cncjob_obj.source_file = total_gcode

        if use_thread:
            # To be run in separate thread
            def job_thread(a_obj):
                if self.target_obj.multigeo is False:
                    with self.app.proc_container.new('%s...' % _("Generating")):
                        ret_value = a_obj.app_obj.new_object("cncjob", outname, job_init_single_geometry, plot=plot,
                                                             autoselected=True)
                else:
                    with self.app.proc_container.new('%s...' % _("Generating")):
                        ret_value = a_obj.app_obj.new_object("cncjob", outname, job_init_multi_geometry, plot=plot,
                                                             autoselected=True)

                if ret_value != 'fail':
                    self.app.ui.notebook.setCurrentWidget(self.app.ui.properties_tab)
                    a_obj.inform.emit('[success] %s: %s' % (_("CNCjob created"), outname))

            # Create a promise with the name
            self.app.collection.promise(outname)
            # Send to worker
            self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})
        else:
            if self.target_obj.multigeo is False:
                ret_val = self.app.app_obj.new_object("cncjob", outname, job_init_single_geometry, plot=plot,
                                                      autoselected=True)
            else:
                ret_val = self.app.app_obj.new_object("cncjob", outname, job_init_multi_geometry, plot=plot,
                                                      autoselected=True)
            if ret_val != 'fail':
                self.app.ui.notebook.setCurrentWidget(self.app.ui.properties_tab)
                self.app.inform.emit('[success] %s: %s' % (_("CNCjob created"), outname))

    def on_pp_changed(self):
        current_pp = self.ui.pp_geo_name_cb.get_value()

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

            self.ui.endz_label.hide()
            self.ui.endz_entry.hide()

            self.ui.travelzlabel.hide()
            self.ui.travelz_entry.hide()

            try:
                self.ui.mpass_cb.hide()
                self.ui.maxdepth_entry.hide()
            except AttributeError:
                pass

            try:
                self.ui.frzlabel.hide()
                self.ui.feedrate_z_entry.hide()
            except AttributeError:
                pass

            self.ui.dwell_cb.hide()
            self.ui.dwelltime_entry.hide()

            self.ui.spindle_label.setText('%s:' % _("Laser Power"))
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

            # if in Advanced Mode
            if self.ui.level.isChecked():
                self.ui.dwell_cb.show()
                self.ui.dwelltime_entry.show()

            self.ui.spindle_label.setText('%s:' % _('Spindle speed'))

        if ('marlin' in current_pp.lower() and 'laser' in current_pp.lower()) or 'z_laser' in current_pp.lower():
            self.ui.travelzlabel.setText('%s:' % _("Focus Z"))
            self.ui.travelzlabel.show()
            self.ui.travelz_entry.show()

            self.ui.endz_label.show()
            self.ui.endz_entry.show()

    def on_plot_cb_click(self):
        self.target_obj.plot()

        self.ui_disconnect()
        cb_flag = self.ui.plot_cb.isChecked()
        for row in range(self.ui.geo_tools_table.rowCount()):
            table_cb = self.ui.geo_tools_table.cellWidget(row, 4)
            if cb_flag:
                table_cb.setChecked(True)
            else:
                table_cb.setChecked(False)
        self.ui_connect()

    def on_plot_cb_click_table(self):
        # self.ui.cnc_tools_table.cellWidget(row, 2).widget().setCheckState(QtCore.Qt.Unchecked)
        self.ui_disconnect()
        # cw = self.sender()
        # cw_index = self.ui.geo_tools_table.indexAt(cw.pos())
        # cw_row = cw_index.row()
        check_row = 0

        self.target_obj.shapes.clear(update=True)

        for tooluid_key in self.target_obj.tools:
            solid_geometry = self.target_obj.tools[tooluid_key]['solid_geometry']

            # find the geo_plugin_table row associated with the tooluid_key
            for row in range(self.ui.geo_tools_table.rowCount()):
                tooluid_item = int(self.ui.geo_tools_table.item(row, 3).text())
                if tooluid_item == int(tooluid_key):
                    check_row = row
                    break

            if self.ui.geo_tools_table.cellWidget(check_row, 4).isChecked():
                try:
                    color = self.target_obj.tools[tooluid_key]['data']['override_color']
                    self.target_obj.plot_element(element=solid_geometry, visible=True, color=color)
                except KeyError:
                    self.target_obj.plot_element(element=solid_geometry, visible=True)
        self.target_obj.shapes.redraw()

        # make sure that the general plot is disabled if one of the row plot's are disabled and
        # if all the row plot's are enabled also enable the general plot checkbox
        cb_cnt = 0
        total_row = self.ui.geo_tools_table.rowCount()
        for row in range(total_row):
            if self.ui.geo_tools_table.cellWidget(row, 4).isChecked():
                cb_cnt += 1
            else:
                cb_cnt -= 1
        # if cb_cnt == total_row:
        #     self.ui.plot_cb.setChecked(True)
        # elif cb_cnt == 0:
        #     self.ui.plot_cb.setChecked(False)
        self.ui_connect()

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
        solid_geo = self.target_obj.solid_geometry
        obj_type = self.target_obj.kind

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

    def reset_fields(self):
        self.object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))


class MillingUI:

    def __init__(self, layout, app, name):
        self.app = app
        self.decimals = self.app.decimals
        self.layout = layout

        self.title_box = QtWidgets.QHBoxLayout()
        self.layout.addLayout(self.title_box)

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
            _("Create CNCJob with toolpaths for milling either Geometry or drill holes.")
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

        self.tools_frame = QtWidgets.QFrame()
        self.tools_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.tools_frame)
        self.tools_box = QtWidgets.QVBoxLayout()
        self.tools_box.setContentsMargins(0, 0, 0, 0)
        self.tools_frame.setLayout(self.tools_box)

        # #############################################################################################################
        # Source Object for Milling Frame
        # #############################################################################################################
        self.obj_combo_label = FCLabel('<span style="color:darkorange;"><b>%s</b></span>' % _("Source Object"))
        self.obj_combo_label.setToolTip(
            _("Source object for milling operation.")
        )
        self.tools_box.addWidget(self.obj_combo_label)

        obj_frame = FCFrame()
        self.tools_box.addWidget(obj_frame)

        # Grid Layout
        obj_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        obj_frame.setLayout(obj_grid)

        self.target_label = FCLabel('%s:' % _("Type"))
        self.target_label.setToolTip(
            _("Object for milling operation.")
        )

        self.target_radio = RadioSet(
            [
                {'label': _('Geometry'), 'value': 'geo'},
                {'label': _('Excellon'), 'value': 'exc'}
            ],
            compact=True)

        obj_grid.addWidget(self.target_label, 0, 0)
        obj_grid.addWidget(self.target_radio, 0, 1)

        # ################################################
        # ##### The object to be milled #################
        # ################################################
        self.object_combo = FCComboBox()
        self.object_combo.setModel(self.app.collection)
        self.object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        # self.object_combo.setCurrentIndex(1)
        self.object_combo.is_last = True

        obj_grid.addWidget(self.object_combo, 2, 0, 1, 2)

        # separator_line = QtWidgets.QFrame()
        # separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        # separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        # obj_grid.addWidget(separator_line, 4, 0, 1, 2)

        # #############################################################################################################
        # Tool Table Frame
        # #############################################################################################################

        # Grid Layout
        tool_title_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        self.tools_box.addLayout(tool_title_grid)

        self.tools_table_label = FCLabel('<span style="color:green;"><b>%s</b></span>' % _('Tools Table'))
        self.tools_table_label.setToolTip(
            _("Tools in the object used for milling.")
        )
        tool_title_grid.addWidget(self.tools_table_label, 0, 0)

        # Plot CB
        self.plot_cb = FCCheckBox(_('Plot Object'))
        self.plot_cb.setToolTip(_("Plot (show) this object."))
        self.plot_cb.setLayoutDirection(QtCore.Qt.LayoutDirection.RightToLeft)
        tool_title_grid.addWidget(self.plot_cb, 0, 1)

        tt_frame = FCFrame()
        self.tools_box.addWidget(tt_frame)

        # Grid Layout
        tool_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        tt_frame.setLayout(tool_grid)

        # ################################################
        # ########## Excellon Tool Table #################
        # ################################################
        self.tools_table = FCTable(drag_drop=True)
        self.tools_table.setRowCount(2)
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
        self.tools_table.horizontalHeaderItem(3).setToolTip(
            _("The number of Slot holes. Holes that are created by\n"
              "milling them with an endmill bit."))

        # #############################################################################################################
        # This should not be done this, it's the job of the build_mill_ui() from the Milling class
        # #############################################################################################################
        # add a last row with the Total number of drills
        empty_1 = QtWidgets.QTableWidgetItem('')
        empty_1.setFlags(~QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)
        empty_1_1 = QtWidgets.QTableWidgetItem('')
        empty_1_1.setFlags(~QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)

        label_tot_drill_count = QtWidgets.QTableWidgetItem(_('Total Drills'))
        label_tot_drill_count.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)

        tot_drill_count = QtWidgets.QTableWidgetItem('%d' % 0)
        tot_drill_count.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)

        self.tools_table.setItem(0, 0, empty_1)
        self.tools_table.setItem(0, 1, label_tot_drill_count)
        self.tools_table.setItem(0, 2, tot_drill_count)  # Total number of drills
        self.tools_table.setItem(0, 4, empty_1_1)

        font = QtGui.QFont()
        font.setBold(True)

        for k in [1, 2]:
            self.tools_table.item(0, k).setForeground(QtGui.QColor(127, 0, 255))
            self.tools_table.item(0, k).setFont(font)

        # add a last row with the Total number of slots
        empty_2 = QtWidgets.QTableWidgetItem('')
        empty_2.setFlags(~QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)
        empty_2_1 = QtWidgets.QTableWidgetItem('')
        empty_2_1.setFlags(~QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)

        label_tot_slot_count = QtWidgets.QTableWidgetItem(_('Total Slots'))
        tot_slot_count = QtWidgets.QTableWidgetItem('%d' % 0)
        label_tot_slot_count.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
        tot_slot_count.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)

        self.tools_table.setItem(1, 0, empty_2)
        self.tools_table.setItem(1, 1, label_tot_slot_count)
        self.tools_table.setItem(1, 2, empty_2_1)
        self.tools_table.setItem(1, 4, tot_slot_count)  # Total number of slots

        for kl in [1, 2, 4]:
            self.tools_table.item(1, kl).setFont(font)
            self.tools_table.item(1, kl).setForeground(QtGui.QColor(0, 70, 255))

        self.tools_table.resizeColumnsToContents()
        self.tools_table.resizeRowsToContents()

        vertical_header = self.tools_table.verticalHeader()
        vertical_header.hide()
        self.tools_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        horizontal_header = self.tools_table.horizontalHeader()
        self.tools_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        horizontal_header.setMinimumSectionSize(10)
        horizontal_header.setDefaultSectionSize(70)

        horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Fixed)
        horizontal_header.resizeSection(0, 20)
        horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        horizontal_header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        horizontal_header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)

        self.tools_table.setSortingEnabled(False)

        self.tools_table.setMinimumHeight(self.tools_table.getHeight())
        self.tools_table.setMaximumHeight(self.tools_table.getHeight())

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

        # ************************************************************************
        # ************** Geometry Tool Table *************************************
        # ************************************************************************

        # Tool Table for Geometry
        self.geo_tools_table = FCTable(drag_drop=False)
        self.geo_tools_table.setRowCount(0)
        self.geo_tools_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.geo_tools_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)

        tool_grid.addWidget(self.geo_tools_table, 4, 0, 1, 2)

        self.geo_tools_table.setColumnCount(5)
        self.geo_tools_table.setColumnWidth(0, 20)
        self.geo_tools_table.setHorizontalHeaderLabels(['#', _('Dia'), '', '', 'P'])
        self.geo_tools_table.setColumnHidden(2, True)
        self.geo_tools_table.setColumnHidden(3, True)

        self.geo_tools_table.horizontalHeaderItem(0).setToolTip(
            _(
                "This is the Tool Number.\n"
                "When ToolChange is checked, on toolchange event this value\n"
                "will be showed as a T1, T2 ... Tn")
        )
        self.geo_tools_table.horizontalHeaderItem(1).setToolTip(
            _("Tool Diameter. Its value\n"
              "is the cut width into the material."))

        self.geo_tools_table.horizontalHeaderItem(4).setToolTip(
            _(
                "Plot column. It is visible only for MultiGeo geometries, meaning geometries that holds the geometry\n"
                "data into the tools. For those geometries, deleting the tool will delete the geometry data also,\n"
                "so be WARNED. From the checkboxes on each row it can be enabled/disabled the plot on canvas\n"
                "for the corresponding tool."
            ))

        # Hide the Tools Table on start
        self.tools_table.hide()
        self.geo_tools_table.hide()
        self.order_label.hide()
        self.order_combo.hide()

        # #############################################################################################################
        # ADD TOOLS FOR GEOMETRY OBJECT
        # #############################################################################################################
        self.add_tool_frame = QtWidgets.QFrame()
        self.add_tool_frame.setContentsMargins(0, 0, 0, 0)
        tool_grid.addWidget(self.add_tool_frame, 6, 0, 1, 2)

        new_tool_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        new_tool_grid.setContentsMargins(0, 0, 0, 0)
        self.add_tool_frame.setLayout(new_tool_grid)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        new_tool_grid.addWidget(separator_line, 0, 0, 1, 2)

        self.tool_sel_label = FCLabel('<b>%s</b>' % _("Add from DB"))
        new_tool_grid.addWidget(self.tool_sel_label, 2, 0, 1, 2)

        self.addtool_entry_lbl = FCLabel('%s:' % _('Tool Dia'))
        self.addtool_entry_lbl.setToolTip(
            _("Diameter for the new tool")
        )
        self.addtool_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.addtool_entry.set_precision(self.decimals)
        self.addtool_entry.set_range(0.00001, 10000.0000)
        self.addtool_entry.setSingleStep(0.1)
        self.addtool_entry.setObjectName("mill_cnctooldia")

        new_tool_grid.addWidget(self.addtool_entry_lbl, 3, 0)
        new_tool_grid.addWidget(self.addtool_entry, 3, 1)

        # #############################################################################################################
        # ################################    Button Grid   ###########################################################
        # #############################################################################################################
        button_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        button_grid.setColumnStretch(0, 1)
        button_grid.setColumnStretch(1, 0)
        new_tool_grid.addLayout(button_grid, 5, 0, 1, 2)

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

        self.add_tool_frame.hide()

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
        param_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        tp_frame.setLayout(param_grid)

        # Milling Type
        self.mill_type_label = FCLabel('%s:' % _('Milling Type'))
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
        self.milling_type_radio.setObjectName("milling_type")

        param_grid.addWidget(self.mill_type_label, 0, 0)
        param_grid.addWidget(self.milling_type_radio, 1, 0, 1, 2)

        # Milling Diameter
        self.mill_dia_label = FCLabel('%s:' % _('Milling Diameter'))
        self.mill_dia_label.setToolTip(
            _("The diameter of the tool who will do the milling")
        )

        self.mill_dia_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.mill_dia_entry.set_precision(self.decimals)
        self.mill_dia_entry.set_range(0.0000, 10000.0000)
        self.mill_dia_entry.setObjectName("milling_dia")

        param_grid.addWidget(self.mill_dia_label, 2, 0)
        param_grid.addWidget(self.mill_dia_entry, 2, 1)

        self.mill_type_label.hide()
        self.milling_type_radio.hide()
        self.mill_dia_label.hide()
        self.mill_dia_entry.hide()

        # Offset Type
        self.offset_type_lbl = FCLabel('%s:' % _('Offset Type'))
        self.offset_type_lbl.setToolTip(
            _(
                "The value for the Offset can be:\n"
                "- Path -> There is no offset, the tool cut will be done through the geometry line.\n"
                "- In(side) -> The tool cut will follow the geometry inside. It will create a 'pocket'.\n"
                "- Out(side) -> The tool cut will follow the geometry line on the outside.\n"
                "- Custom -> The tool will cut at an chosen offset."
            ))

        self.offset_type_combo = FCComboBox2()
        self.offset_type_combo.addItems(
            [_("Path"), _("In"), _("Out"), _("Custom")]
        )
        self.offset_type_combo.setObjectName('mill_offset_type')

        param_grid.addWidget(self.offset_type_lbl, 4, 0)
        param_grid.addWidget(self.offset_type_combo, 4, 1)

        # Tool Offset
        self.offset_label = FCLabel('%s:' % _('Custom'))
        self.offset_label.setToolTip(
            _(
                "The value to offset the cut when \n"
                "the Offset type selected is 'Custom'.\n"
                "The value can be positive for 'outside'\n"
                "cut and negative for 'inside' cut."
            )
        )

        self.offset_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.offset_entry.set_precision(self.decimals)
        self.offset_entry.set_range(-10000.0000, 10000.0000)
        self.offset_entry.setObjectName("mill_offset")

        self.offset_label.hide()
        self.offset_entry.hide()

        param_grid.addWidget(self.offset_label, 6, 0)
        param_grid.addWidget(self.offset_entry, 6, 1)

        self.offset_separator_line = QtWidgets.QFrame()
        self.offset_separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.offset_separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        param_grid.addWidget(self.offset_separator_line, 7, 0, 1, 2)

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
        self.tool_shape_combo.setObjectName('mill_tool_shape')
        self.tool_shape_combo.addItems(["C1", "C2", "C3", "C4", "B", "V"])

        idx = int(self.app.defaults['tools_mill_tool_shape'])
        # protection against having this translated or loading a project with translated values
        if idx == -1:
            self.tool_shape_combo.setCurrentIndex(0)
        else:
            self.tool_shape_combo.setCurrentIndex(idx)

        param_grid.addWidget(self.tool_shape_label, 8, 0)
        param_grid.addWidget(self.tool_shape_combo, 8, 1)

        # Job Type
        self.job_type_lbl = FCLabel('%s:' % _('Job'))
        self.job_type_lbl.setToolTip(
            _(
                "- Isolation -> informative - lower Feedrate as it uses a milling bit with a fine tip.\n"
                "- Roughing  -> informative - lower Feedrate and multiDepth cut.\n"
                "- Finishing -> informative - higher Feedrate, without multiDepth.\n"
                "- Polish -> adds a painting sequence over the whole area of the object"
            )
        )

        self.job_type_combo = FCComboBox2()
        self.job_type_combo.addItems(
            [_('Roughing'), _('Finishing'), _('Isolation'), _('Polishing')]
        )
        self.job_type_combo.setObjectName('mill_job_type')

        param_grid.addWidget(self.job_type_lbl, 10, 0)
        param_grid.addWidget(self.job_type_combo, 10, 1)

        # Polish Margin
        self.polish_margin_lbl = FCLabel('%s:' % _('Margin'))
        self.polish_margin_lbl.setToolTip(
            _("Bounding box margin.")
        )
        self.polish_margin_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.polish_margin_entry.set_precision(self.decimals)
        self.polish_margin_entry.set_range(-10000.0000, 10000.0000)
        self.polish_margin_entry.setObjectName("mill_polish_margin")

        param_grid.addWidget(self.polish_margin_lbl, 12, 0)
        param_grid.addWidget(self.polish_margin_entry, 12, 1)

        # Polish Overlap
        self.polish_over_lbl = FCLabel('%s:' % _('Overlap'))
        self.polish_over_lbl.setToolTip(
            _("How much (percentage) of the tool width to overlap each tool pass.")
        )
        self.polish_over_entry = FCDoubleSpinner(suffix='%', callback=self.confirmation_message)
        self.polish_over_entry.set_precision(self.decimals)
        self.polish_over_entry.setWrapping(True)
        self.polish_over_entry.set_range(0.0000, 99.9999)
        self.polish_over_entry.setSingleStep(0.1)
        self.polish_over_entry.setObjectName("mill_polish_overlap")

        param_grid.addWidget(self.polish_over_lbl, 14, 0)
        param_grid.addWidget(self.polish_over_entry, 14, 1)

        # Polish Method
        self.polish_method_lbl = FCLabel('%s:' % _('Method'))
        self.polish_method_lbl.setToolTip(
            _("Algorithm for polishing:\n"
              "- Standard: Fixed step inwards.\n"
              "- Seed-based: Outwards from seed.\n"
              "- Line-based: Parallel lines.")
        )

        self.polish_method_combo = FCComboBox2()
        self.polish_method_combo.addItems(
            [_("Standard"), _("Seed"), _("Lines")]
        )
        self.polish_method_combo.setObjectName('mill_polish_method')

        param_grid.addWidget(self.polish_method_lbl, 16, 0)
        param_grid.addWidget(self.polish_method_combo, 16, 1)

        self.polish_margin_lbl.hide()
        self.polish_margin_entry.hide()
        self.polish_over_lbl.hide()
        self.polish_over_entry.hide()
        self.polish_method_lbl.hide()
        self.polish_method_combo.hide()

        self.job_separator_line = QtWidgets.QFrame()
        self.job_separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.job_separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        param_grid.addWidget(self.job_separator_line, 18, 0, 1, 2)

        # Tip Dia
        self.tipdialabel = FCLabel('%s:' % _('V-Tip Dia'))
        self.tipdialabel.setToolTip(
            _(
                "The tip diameter for V-Shape Tool"
            )
        )
        self.tipdia_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.tipdia_entry.set_precision(self.decimals)
        self.tipdia_entry.set_range(0.00001, 10000.0000)
        self.tipdia_entry.setSingleStep(0.1)
        self.tipdia_entry.setObjectName("mill_tipdia")

        param_grid.addWidget(self.tipdialabel, 20, 0)
        param_grid.addWidget(self.tipdia_entry, 20, 1)

        # Tip Angle
        self.tipanglelabel = FCLabel('%s:' % _('V-Tip Angle'))
        self.tipanglelabel.setToolTip(
            _(
                "The tip angle for V-Shape Tool.\n"
                "In degree."
            )
        )
        self.tipangle_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.tipangle_entry.set_precision(self.decimals)
        self.tipangle_entry.set_range(1.0, 180.0)
        self.tipangle_entry.setSingleStep(1)
        self.tipangle_entry.setObjectName("mill_tipangle")

        param_grid.addWidget(self.tipanglelabel, 22, 0)
        param_grid.addWidget(self.tipangle_entry, 22, 1)

        self.tipdialabel.hide()
        self.tipdia_entry.hide()
        self.tipanglelabel.hide()
        self.tipangle_entry.hide()

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
        self.cutz_entry.setObjectName("mill_cutz")

        param_grid.addWidget(self.cutzlabel, 24, 0)
        param_grid.addWidget(self.cutz_entry, 24, 1)

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
        self.mpass_cb.setObjectName("mill_multidepth")

        self.maxdepth_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.maxdepth_entry.set_precision(self.decimals)
        self.maxdepth_entry.set_range(0, 10000.0000)
        self.maxdepth_entry.setSingleStep(0.1)

        self.maxdepth_entry.setToolTip(_("Depth of each pass (positive)."))
        self.maxdepth_entry.setObjectName("mill_depthperpass")

        self.mis_mpass_geo = OptionalInputSection(self.mpass_cb, [self.maxdepth_entry])

        param_grid.addWidget(self.mpass_cb, 26, 0)
        param_grid.addWidget(self.maxdepth_entry, 26, 1)

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
        self.travelz_entry.setObjectName("mill_travelz")

        param_grid.addWidget(self.travelzlabel, 28, 0)
        param_grid.addWidget(self.travelz_entry, 28, 1)

        # Feedrate X-Y
        self.frxylabel = FCLabel('%s:' % _('Feedrate X-Y'))
        self.frxylabel.setToolTip(
            _("Cutting speed in the XY\n"
              "plane in units per minute")
        )
        self.xyfeedrate_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.xyfeedrate_entry.set_precision(self.decimals)
        self.xyfeedrate_entry.set_range(0, 10000.0000)
        self.xyfeedrate_entry.setSingleStep(0.1)
        self.xyfeedrate_entry.setObjectName("mill_feedratexy")

        param_grid.addWidget(self.frxylabel, 30, 0)
        param_grid.addWidget(self.xyfeedrate_entry, 30, 1)

        self.frxylabel.hide()
        self.xyfeedrate_entry.hide()

        # Feedrate Z
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
        self.feedrate_z_entry.setObjectName("mill_feedratez")

        param_grid.addWidget(self.frzlabel, 32, 0)
        param_grid.addWidget(self.feedrate_z_entry, 32, 1)

        # Rapid Feedrate
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
        self.feedrate_rapid_entry.setObjectName("mill_fr_rapid")

        param_grid.addWidget(self.feedrate_rapid_label, 34, 0)
        param_grid.addWidget(self.feedrate_rapid_entry, 34, 1)

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
        self.extracut_cb.setObjectName("mill_extracut")

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
        self.e_cut_entry.setObjectName("mill_extracut_length")

        self.ois_recut = OptionalInputSection(self.extracut_cb, [self.e_cut_entry])

        self.extracut_cb.hide()
        self.e_cut_entry.hide()

        param_grid.addWidget(self.extracut_cb, 36, 0)
        param_grid.addWidget(self.e_cut_entry, 36, 1)

        # Spindlespeed
        self.spindle_label = FCLabel('%s:' % _('Spindle speed'))
        self.spindle_label.setToolTip(
            _("Speed of the spindle\n"
              "in RPM (optional)")
        )

        self.spindlespeed_entry = FCSpinner(callback=self.confirmation_message_int)
        self.spindlespeed_entry.set_range(0, 1000000)
        self.spindlespeed_entry.set_step(100)
        self.spindlespeed_entry.setObjectName("mill_spindlespeed")

        param_grid.addWidget(self.spindle_label, 38, 0)
        param_grid.addWidget(self.spindlespeed_entry, 38, 1)

        # Dwell
        self.dwell_cb = FCCheckBox('%s:' % _('Dwell'))
        self.dwell_cb.setToolTip(
            _("Pause to allow the spindle to reach its\n"
              "speed before cutting.")
        )
        self.dwell_cb.setObjectName("mill_dwell")

        self.dwelltime_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.dwelltime_entry.set_precision(self.decimals)
        self.dwelltime_entry.set_range(0.0, 10000.0000)
        self.dwelltime_entry.setSingleStep(0.1)

        self.dwelltime_entry.setToolTip(
            _("Number of time units for spindle to dwell.")
        )
        self.dwelltime_entry.setObjectName("mill_dwelltime")

        param_grid.addWidget(self.dwell_cb, 40, 0)
        param_grid.addWidget(self.dwelltime_entry, 40, 1)

        self.ois_dwell = OptionalInputSection(self.dwell_cb, [self.dwelltime_entry])

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

        # Tool change Z:
        self.toolchange_cb = FCCheckBox('%s:' % _("Tool change Z"))
        self.toolchange_cb.setToolTip(
            _("Include tool-change sequence\n"
              "in G-Code (Pause for tool change).")
        )
        self.toolchange_cb.setObjectName("mill_toolchange")

        self.toolchangez_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.toolchangez_entry.set_precision(self.decimals)
        self.toolchangez_entry.setToolTip(
            _("Z-axis position (height) for\n"
              "tool change.")
        )
        self.toolchangez_entry.set_range(-10000.0000, 10000.0000)
        self.toolchangez_entry.setObjectName("mill_toolchangez")

        self.toolchangez_entry.setSingleStep(0.1)

        gen_grid.addWidget(self.toolchange_cb, 0, 0)
        gen_grid.addWidget(self.toolchangez_entry, 0, 1)

        # Tool change X-Y
        self.toolchange_xy_label = FCLabel('%s:' % _('Toolchange X-Y'))
        self.toolchange_xy_label.setToolTip(
            _("Toolchange X,Y position.")
        )
        self.toolchangexy_entry = NumericalEvalTupleEntry(border_color='#0069A9')
        self.toolchangexy_entry.setObjectName("mill_toolchangexy")

        gen_grid.addWidget(self.toolchange_xy_label, 2, 0)
        gen_grid.addWidget(self.toolchangexy_entry, 2, 1)

        self.ois_tcz_e = OptionalInputSection(self.toolchange_cb,
                                              [
                                                  self.toolchangez_entry,
                                                  self.toolchange_xy_label,
                                                  self.toolchangexy_entry
                                              ])

        # End move Z:
        self.endz_label = FCLabel('%s:' % _("End move Z"))
        self.endz_label.setToolTip(
            _("Height of the tool after\n"
              "the last move at the end of the job.")
        )
        self.endz_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.endz_entry.set_precision(self.decimals)
        self.endz_entry.set_range(-10000.0000, 10000.0000)
        self.endz_entry.setObjectName("mill_endz")

        self.endz_entry.setSingleStep(0.1)

        gen_grid.addWidget(self.endz_label, 4, 0)
        gen_grid.addWidget(self.endz_entry, 4, 1)

        # End Move X,Y
        self.endmove_xy_label = FCLabel('%s:' % _('End move X,Y'))
        self.endmove_xy_label.setToolTip(
            _("End move X,Y position. In format (x,y).\n"
              "If no value is entered then there is no move\n"
              "on X,Y plane at the end of the job.")
        )
        self.endxy_entry = NumericalEvalTupleEntry(border_color='#0069A9')
        self.endxy_entry.setPlaceholderText(_("X,Y coordinates"))
        self.endxy_entry.setObjectName("mill_endxy")

        gen_grid.addWidget(self.endmove_xy_label, 6, 0)
        gen_grid.addWidget(self.endxy_entry, 6, 1)

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
        self.pdepth_entry.setObjectName("mill_depth_probe")

        gen_grid.addWidget(self.pdepth_label, 8, 0)
        gen_grid.addWidget(self.pdepth_entry, 8, 1)

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
        self.feedrate_probe_entry.setObjectName("mill_fr_probe")

        gen_grid.addWidget(self.feedrate_probe_label, 10, 0)
        gen_grid.addWidget(self.feedrate_probe_entry, 10, 1)

        self.feedrate_probe_label.hide()
        self.feedrate_probe_entry.setVisible(False)

        # Preprocessor Geometry selection
        pp_geo_label = FCLabel('%s:' % _("Preprocessor"))
        pp_geo_label.setToolTip(
            _("The preprocessor JSON file that dictates\n"
              "Gcode output for Geometry (Milling) Objects.")
        )
        self.pp_geo_name_cb = FCComboBox()
        self.pp_geo_name_cb.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.pp_geo_name_cb.setObjectName("mill_ppname_g")

        gen_grid.addWidget(pp_geo_label, 12, 0)
        gen_grid.addWidget(self.pp_geo_name_cb, 12, 1)

        # Allow Levelling
        self.allow_level_cb = FCCheckBox('%s' % _("Allow levelling"))
        self.allow_level_cb.setToolTip(
            _("Allow levelling by having segments size more than zero.")
        )
        self.allow_level_cb.setObjectName("mill_allow_level")

        gen_grid.addWidget(self.allow_level_cb, 14, 0, 1, 2)

        # Size of trace segment on X axis
        segx_label = FCLabel('%s:' % _("Segment X size"))
        segx_label.setToolTip(
            _("The size of the trace segment on the X axis.\n"
              "Useful for auto-leveling.\n"
              "A value of 0 means no segmentation on the X axis.")
        )
        self.segx_entry = FCDoubleSpinner()
        self.segx_entry.set_range(0, 99999)
        self.segx_entry.set_precision(self.decimals)
        self.segx_entry.setSingleStep(0.1)
        self.segx_entry.setWrapping(True)
        self.segx_entry.setObjectName("mill_segx")

        gen_grid.addWidget(segx_label, 16, 0)
        gen_grid.addWidget(self.segx_entry, 16, 1)

        # Size of trace segment on Y axis
        segy_label = FCLabel('%s:' % _("Segment Y size"))
        segy_label.setToolTip(
            _("The size of the trace segment on the Y axis.\n"
              "Useful for auto-leveling.\n"
              "A value of 0 means no segmentation on the Y axis.")
        )
        self.segy_entry = FCDoubleSpinner()
        self.segy_entry.set_range(0, 99999)
        self.segy_entry.set_precision(self.decimals)
        self.segy_entry.setSingleStep(0.1)
        self.segy_entry.setWrapping(True)
        self.segy_entry.setObjectName("mill_segy")

        gen_grid.addWidget(segy_label, 18, 0)
        gen_grid.addWidget(self.segy_entry, 18, 1)

        self.oih = OptionalHideInputSection(self.allow_level_cb,
                                            [segx_label, self.segx_entry, segy_label, self.segy_entry])

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
        self.exclusion_cb.setObjectName("mill_exclusion")

        gen_grid.addWidget(self.exclusion_cb, 20, 0, 1, 2)

        self.exclusion_frame = QtWidgets.QFrame()
        self.exclusion_frame.setContentsMargins(0, 0, 0, 0)
        gen_grid.addWidget(self.exclusion_frame, 22, 0, 1, 2)

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

        grid_a1 = FCGridLayout(v_spacing=5, h_spacing=3)
        self.exclusion_box.addLayout(grid_a1)

        # Chose Strategy
        self.strategy_label = FCLabel('%s:' % _("Strategy"))
        self.strategy_label.setToolTip(_("The strategy followed when encountering an exclusion area.\n"
                                         "Can be:\n"
                                         "- Over -> when encountering the area, the tool will go to a set height\n"
                                         "- Around -> will avoid the exclusion area by going around the area"))
        self.strategy_radio = RadioSet([{'label': _('Over'), 'value': 'over'},
                                        {'label': _('Around'), 'value': 'around'}])
        self.strategy_radio.setObjectName("mill_strategy")

        grid_a1.addWidget(self.strategy_label, 1, 0)
        grid_a1.addWidget(self.strategy_radio, 1, 1)

        # Over Z
        self.over_z_label = FCLabel('%s:' % _("Over Z"))
        self.over_z_label.setToolTip(_("The height Z to which the tool will rise in order to avoid\n"
                                       "an interdiction area."))
        self.over_z_entry = FCDoubleSpinner()
        self.over_z_entry.set_range(-10000.0000, 10000.0000)
        self.over_z_entry.set_precision(self.decimals)
        self.over_z_entry.setObjectName("mill_overz")

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
        self.area_shape_radio.setObjectName("mill_area_shape")

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

        FCGridLayout.set_common_column_size(
            [obj_grid, tool_title_grid, tool_grid, new_tool_grid, param_grid, gen_grid], 0)

        # #############################################################################################################
        # Generate CNC Job object
        # #############################################################################################################
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
        self.tool_params_box.addWidget(self.generate_cnc_button)

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
