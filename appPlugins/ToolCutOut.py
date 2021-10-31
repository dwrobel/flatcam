# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt6 import QtWidgets, QtGui, QtCore
from appTool import AppTool
from appGUI.GUIElements import FCDoubleSpinner, FCCheckBox, RadioSet, FCComboBox, OptionalInputSection, FCButton, \
    FCLabel, VerticalScrollArea, FCGridLayout, FCFrame, FCComboBox2

from shapely.geometry import box, MultiPolygon, Polygon, LineString, LinearRing, MultiLineString, Point
from shapely.ops import unary_union, linemerge
import shapely.affinity as affinity
from camlib import flatten_shapely_geometry

from matplotlib.backend_bases import KeyEvent as mpl_key_event

from numpy import Inf
from copy import deepcopy
import math
import logging
import gettext
import sys
import simplejson as json

import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class CutOut(AppTool):

    def __init__(self, app):
        AppTool.__init__(self, app)

        self.app = app
        self.canvas = app.plotcanvas
        self.decimals = self.app.decimals

        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = CutoutUI(layout=self.layout, app=self.app)
        self.pluginName = self.ui.pluginName
        self.connect_signals_at_init()

        self.cutting_gapsize = 0.0
        self.cutting_dia = 0.0

        # true if we want to repeat the gap without clicking again on the button
        self.repeat_gap = False

        self.flat_geometry = []

        # this is the Geometry object generated in this class to be used for adding manual gaps
        self.man_cutout_obj = None

        # if mouse is dragging set the object True
        self.mouse_is_dragging = False

        # if mouse events are bound to local methods
        self.mouse_events_connected = False

        # event handlers references
        self.kp = None
        self.mm = None
        self.mr = None

        # hold the mouse position here
        self.x_pos = None
        self.y_pos = None

        # store the default data for the resulting Geometry Object
        self.default_data = {}

        # store the current cursor type to be restored after manual geo
        self.old_cursor_type = self.app.defaults["global_cursor_type"]

        # store the current selection shape status to be restored after manual geo
        self.old_selection_state = self.app.defaults['global_selection_shape']

        # store original geometry for manual cutout
        self.manual_solid_geo = None

        # here will store the original geometry for manual cutout with mouse bytes
        self.mb_manual_solid_geo = None

        # here will store the geo rests when doing manual cutouts with mouse bites
        self.mb_manual_cuts = []

        # here store the tool data for the Cutout Tool
        self.cut_tool_dict = {}

    def on_type_obj_changed(self, val):
        obj_type = {'grb': 0, 'geo': 2}[val]
        self.ui.obj_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.ui.obj_combo.setCurrentIndex(0)
        self.ui.obj_combo.obj_type = {"grb": "Gerber", "geo": "Geometry"}[val]

        if val == 'grb':
            self.ui.convex_box_label.setDisabled(False)
            self.ui.convex_box_cb.setDisabled(False)
        else:
            self.ui.convex_box_label.setDisabled(True)
            self.ui.convex_box_cb.setDisabled(True)

    def on_object_selection_changed(self, current, previous):
        found_idx = None
        for tab_idx in range(self.app.ui.notebook.count()):
            if self.app.ui.notebook.tabText(tab_idx) == self.ui.pluginName:
                found_idx = True
                break

        if found_idx:
            try:
                name = current.indexes()[0].internalPointer().obj.options['name']
                kind = current.indexes()[0].internalPointer().obj.kind

                if kind in ['gerber', 'geometry']:
                    obj_type = {'gerber': 'grb', 'geometry': 'geo'}[kind]
                    self.ui.type_obj_radio.set_value(obj_type)

                self.ui.obj_combo.set_value(name)
            except IndexError:
                pass

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolCutOut()")

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

        self.app.ui.notebook.setTabText(2, _("Cutout"))

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Alt+X', **kwargs)

    def connect_signals_at_init(self):
        # #############################################################################
        # ############################ SIGNALS ########################################
        # #############################################################################
        self.ui.level.toggled.connect(self.on_level_changed)

        self.ui.generate_cutout_btn.clicked.connect(self.on_cutout_generation)

        # adding tools
        self.ui.add_newtool_button.clicked.connect(lambda: self.on_tool_add())
        self.ui.addtool_from_db_btn.clicked.connect(self.on_tool_add_from_db_clicked)

        self.ui.type_obj_radio.activated_custom.connect(self.on_type_obj_changed)
        self.ui.cutout_shape_cb.stateChanged.connect(self.on_cutout_shape_changed)

        self.ui.cutout_type_radio.activated_custom.connect(self.on_cutout_type)

        self.ui.man_geo_creation_btn.clicked.connect(self.on_manual_geo)
        self.ui.man_gaps_creation_btn.clicked.connect(self.on_manual_gap_click)
        self.ui.drillcut_btn.clicked.connect(self.on_drill_cut_click)

        self.app.proj_selection_changed.connect(self.on_object_selection_changed)

        self.ui.reset_button.clicked.connect(self.set_tool_ui)

    def set_tool_ui(self):

        self.clear_ui(self.layout)
        self.ui = CutoutUI(layout=self.layout, app=self.app)
        self.pluginName = self.ui.pluginName
        self.connect_signals_at_init()

        self.reset_fields()

        # use the current selected object and make it visible in the object combobox
        sel_list = self.app.collection.get_selected()
        if len(sel_list) == 1:
            active = self.app.collection.get_active()
            kind = active.kind
            if kind == 'gerber':
                self.ui.type_obj_radio.set_value('grb')
            else:
                self.ui.type_obj_radio.set_value('geo')

            # run those once so the obj_type attribute is updated for the FCComboboxes
            # so the last loaded object is displayed
            if kind == 'gerber':
                self.on_type_obj_changed(val='grb')
            else:
                self.on_type_obj_changed(val='geo')

            self.ui.obj_combo.set_value(active.options['name'])
        else:
            kind = 'gerber'
            self.ui.type_obj_radio.set_value('grb')

            # run those once so the obj_type attribute is updated for the FCComboboxes
            # so the last loaded object is displayed
            if kind == 'gerber':
                self.on_type_obj_changed(val='grb')
            else:
                self.on_type_obj_changed(val='geo')

        # init the working variables
        self.default_data.clear()
        kind = 'geometry'
        for option in self.app.options:
            if option.find(kind + "_") == 0:
                oname = option[len(kind) + 1:]
                self.default_data[oname] = self.app.options[option]

            if option.find('tools_') == 0:
                self.default_data[option] = self.app.options[option]

        self.ui.gaptype_combo.set_value(self.app.defaults["tools_cutout_gap_type"])
        self.ui.on_gap_type_radio(self.ui.gaptype_combo.get_value())

        # add a default tool
        self.ui.dia.set_value(float(self.app.defaults["tools_cutout_tooldia"]))
        tool_dia = float(self.app.defaults["tools_cutout_tooldia"])
        self.on_tool_add(custom_dia=tool_dia)

        # set as default the automatic adding of gaps
        self.ui.cutout_type_radio.set_value('a')
        self.on_cutout_type(val='a')

        self.ui.cutout_shape_cb.set_value(False)
        self.on_cutout_shape_changed(self.ui.cutout_shape_cb.get_value())

        # set the Cut By Drilling parameters
        self.ui.drill_dia_entry.set_value(float(self.app.defaults["tools_cutout_drill_dia"]))
        self.ui.drill_pitch_entry.set_value(float(self.app.defaults["tools_cutout_drill_pitch"]))
        self.ui.drill_margin_entry.set_value(float(self.app.defaults["tools_cutout_drill_margin"]))

        # Show/Hide Advanced Options
        app_mode = self.app.defaults["global_app_level"]
        self.change_level(app_mode)

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

            self.ui.convex_box_label.hide()
            self.ui.convex_box_cb.hide()

            # Add Tool section
            # self.ui.tool_sel_label.hide()
            self.ui.add_newtool_button.hide()
            self.ui.addtool_from_db_btn.hide()

            # Tool parameters section
            if self.cut_tool_dict:
                tool_data = self.cut_tool_dict['data']

                tool_data['tools_cutout_convexshape'] = False
                tool_data['tools_cutout_gap_type'] = 0  # "Basic Type of Gap"

            self.ui.gaptype_label.hide()
            self.ui.gaptype_combo.hide()
            self.ui.cutout_type_label.hide()
            self.ui.cutout_type_radio.hide()
            self.ui.cutout_type_radio.set_value('a')

            self.ui.separator_line.hide()

            self.ui.drill_cut_frame.hide()
            self.ui.title_drillcut_label.hide()
            self.ui.drillcut_btn.hide()

        else:
            self.ui.level.setText('%s' % _('Advanced'))
            self.ui.level.setStyleSheet("""
                                        QToolButton
                                        {
                                            color: red;
                                        }
                                        """)

            self.ui.convex_box_label.show()
            self.ui.convex_box_cb.show()

            # Add Tool section
            # self.ui.tool_sel_label.show()
            self.ui.add_newtool_button.show()
            self.ui.addtool_from_db_btn.show()

            # Tool parameters section
            if self.cut_tool_dict:
                app_defaults = self.app.defaults
                tool_data = self.cut_tool_dict['data']

                tool_data['tools_cutout_convexshape'] = app_defaults['tools_cutout_convexshape']
                tool_data['tools_cutout_gap_type'] = app_defaults['tools_cutout_gap_type']

            self.ui.gaptype_label.show()
            self.ui.gaptype_combo.show()
            self.ui.cutout_type_label.show()
            self.ui.cutout_type_radio.show()
            self.ui.cutout_type_radio.set_value('a')

            self.ui.separator_line.show()

            self.ui.drill_cut_frame.show()
            self.ui.title_drillcut_label.show()
            self.ui.drillcut_btn.show()

        if self.cut_tool_dict:
            tool_data = self.cut_tool_dict['data']
            self.ui.on_gap_type_radio(tool_data['tools_cutout_gap_type'])

    def update_ui(self, tool_dict):
        self.ui.obj_kind_combo.set_value(self.default_data["tools_cutout_kind"])
        self.ui.big_cursor_cb.set_value(self.default_data['tools_cutout_big_cursor'])

        # Entries that may be updated from database
        self.ui.margin.set_value(float(tool_dict["tools_cutout_margin"]))
        self.ui.gapsize.set_value(float(tool_dict["tools_cutout_gapsize"]))
        self.ui.gaptype_combo.set_value(tool_dict["tools_cutout_gap_type"])
        self.on_cutout_type(self.ui.gaptype_combo.get_value())

        self.ui.thin_depth_entry.set_value(float(tool_dict["tools_cutout_gap_depth"]))
        self.ui.mb_dia_entry.set_value(float(tool_dict["tools_cutout_mb_dia"]))
        self.ui.mb_spacing_entry.set_value(float(tool_dict["tools_cutout_mb_spacing"]))
        self.ui.convex_box_cb.set_value(tool_dict['tools_cutout_convexshape'])
        self.ui.gaps.set_value(tool_dict["tools_cutout_gaps_ff"])

        self.ui.cutz_entry.set_value(float(tool_dict["tools_cutout_z"]))
        self.ui.mpass_cb.set_value(float(tool_dict["tools_cutout_mdepth"]))
        self.ui.maxdepth_entry.set_value(float(tool_dict["tools_cutout_depthperpass"]))

    def on_cutout_type(self, val):
        if val == 'a':
            self.ui.gaps_label.show()
            self.ui.gaps.show()
            self.ui.generate_cutout_btn.show()

            self.ui.man_geo_creation_btn.hide()
            self.ui.man_gaps_creation_btn.hide()
            self.ui.man_frame.hide()
        else:
            self.ui.gaps_label.hide()
            self.ui.gaps.hide()
            self.ui.generate_cutout_btn.hide()

            self.ui.man_geo_creation_btn.show()
            self.ui.man_gaps_creation_btn.show()
            self.ui.man_frame.show()

    def on_cutout_shape_changed(self, state):
        if state:
            self.ui.generate_cutout_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/rectangle32.png'))
            self.ui.cutout_shape_cb.setText('%s' % _("Rectangular"))
        else:
            self.ui.generate_cutout_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/irregular32.png'))
            self.ui.cutout_shape_cb.setText('%s' % _("Any"))

    def on_tool_add(self, custom_dia=None):
        self.blockSignals(True)

        filename = self.app.tools_database_path()

        new_tools_dict = deepcopy(self.default_data)
        updated_tooldia = None

        # determine the new tool diameter
        if custom_dia is None:
            tool_dia = self.ui.dia.get_value()
        else:
            tool_dia = custom_dia

        if tool_dia is None or tool_dia == 0:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Please enter a tool diameter with non-zero value, "
                                                          "in Float format."))
            self.blockSignals(False)
            return

        truncated_tooldia = self.app.dec_format(tool_dia, self.decimals)

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

        # look in database tools
        for db_tool, db_tool_val in tools_db_dict.items():
            db_tooldia = db_tool_val['tooldia']
            low_limit = float(db_tool_val['data']['tol_min'])
            high_limit = float(db_tool_val['data']['tol_max'])

            # we need only tool marked for Cutout Tool
            if db_tool_val['data']['tool_target'] != _('Cutout'):
                continue

            # if we find a tool with the same diameter in the Tools DB just update it's data
            if truncated_tooldia == db_tooldia:
                tool_found += 1
                for d in db_tool_val['data']:
                    if d.find('tools_cutout_') == 0:
                        new_tools_dict[d] = db_tool_val['data'][d]
                    elif d.find('tools_') == 0:
                        # don't need data for other App Tools; this tests after 'tools_cutout_'
                        continue
                    else:
                        new_tools_dict[d] = db_tool_val['data'][d]
            # search for a tool that has a tolerance that the tool fits in
            elif high_limit >= truncated_tooldia >= low_limit:
                tool_found += 1
                updated_tooldia = db_tooldia
                for d in db_tool_val['data']:
                    if d.find('tools_cutout_') == 0:
                        new_tools_dict[d] = db_tool_val['data'][d]
                    elif d.find('tools_') == 0:
                        # don't need data for other App Tools; this tests after 'tools_cutout_'
                        continue
                    else:
                        new_tools_dict[d] = db_tool_val['data'][d]

        # test we found a suitable tool in Tools Database or if multiple ones
        if tool_found == 0:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Tool not in Tools Database. Adding a default tool."))
            self.on_tool_default_add()
            self.blockSignals(False)
            return

        if tool_found > 1:
            self.app.inform.emit(
                '[WARNING_NOTCL] %s' % _("Cancelled.\n"
                                         "Multiple tools for one tool diameter found in Tools Database."))
            self.blockSignals(False)
            return

        new_tools_dict["tools_cutout_z"] = deepcopy(new_tools_dict["tools_mill_cutz"])
        new_tools_dict["tools_cutout_mdepth"] = deepcopy(new_tools_dict["tools_mill_multidepth"])
        new_tools_dict["tools_cutout_depthperpass"] = deepcopy(new_tools_dict["tools_mill_depthperpass"])

        new_tdia = deepcopy(updated_tooldia) if updated_tooldia is not None else deepcopy(truncated_tooldia)
        self.cut_tool_dict.update({
            'tooldia':          new_tdia,
            'data':             deepcopy(new_tools_dict),
            'solid_geometry':   []
        })

        self.update_ui(new_tools_dict)

        self.blockSignals(False)
        self.app.inform.emit('[success] %s' % _("Updated tool from Tools Database."))

    def on_tool_default_add(self, dia=None, muted=None):

        dia = dia if dia else str(self.app.defaults["tools_cutout_tooldia"])

        # init the working variables
        self.default_data.clear()
        kind = 'geometry'
        for option in self.app.options:
            if option.find(kind + "_") == 0:
                oname = option[len(kind) + 1:]
                self.default_data[oname] = self.app.options[option]

            if option.find('tools_') == 0:
                self.default_data[option] = self.app.options[option]

        self.cut_tool_dict.update({
            'tooldia':          dia,
            'data':             deepcopy(self.default_data),
            'solid_geometry':   []
        })

        self.update_ui(self.default_data)

        if muted is None:
            self.app.inform.emit('[success] %s' % _("Default tool added."))

    def on_cutout_tool_add_from_db_executed(self, tool):
        """
        Here add the tool from DB  in the selected geometry object
        :return:
        """

        if tool['data']['tool_target'] not in [0, 6]:   # [General, Cutout Tool]
            for idx in range(self.app.ui.plot_tab_area.count()):
                if self.app.ui.plot_tab_area.tabText(idx) == _("Tools Database"):
                    wdg = self.app.ui.plot_tab_area.widget(idx)
                    wdg.deleteLater()
                    self.app.ui.plot_tab_area.removeTab(idx)
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Selected tool can't be used here. Pick another."))
            return
        tool_from_db = deepcopy(self.default_data)
        tool_from_db.update(tool)

        tool_from_db['data']["tools_cutout_tooldia"] = deepcopy(tool["tooldia"])
        tool_from_db['data']["tools_cutout_z"] = deepcopy(tool_from_db['data']["tools_mill_cutz"])
        tool_from_db['data']["tools_cutout_mdepth"] = deepcopy(tool_from_db['data']["tools_mill_multidepth"])
        tool_from_db['data']["tools_cutout_depthperpass"] = deepcopy(tool_from_db['data']["tools_mill_depthperpass"])

        self.cut_tool_dict.update(tool_from_db)
        self.cut_tool_dict['solid_geometry'] = []

        self.update_ui(tool_from_db['data'])
        self.ui.dia.set_value(float(tool_from_db['data']["tools_cutout_tooldia"]))

        for idx in range(self.app.ui.plot_tab_area.count()):
            if self.app.ui.plot_tab_area.tabText(idx) == _("Tools Database"):
                wdg = self.app.ui.plot_tab_area.widget(idx)
                wdg.deleteLater()
                self.app.ui.plot_tab_area.removeTab(idx)

        self.app.inform.emit('[success] %s' % _("Tool updated from Tools Database."))

    def on_tool_from_db_inserted(self, tool):
        """
        Called from the Tools DB object through a App method when adding a tool from Tools Database
        :param tool: a dict with the tool data
        :return: None
        """

        tooldia = float(tool['tooldia'])

        truncated_tooldia = self.app.dec_format(tooldia, self.decimals)
        self.cutout_tools.update({
            1: {
                'tooldia':          truncated_tooldia,
                'data':             deepcopy(tool['data']),
                'solid_geometry':   []
            }
        })
        self.cutout_tools[1]['data']['name'] = '_cutout'

        return 1

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
        ret_val = self.app.on_tools_database(source='cutout')
        if ret_val == 'fail':
            return
        self.app.tools_db_tab.ok_to_add = True
        self.app.tools_db_tab.ui.buttons_frame.hide()
        self.app.tools_db_tab.ui.add_tool_from_db.show()
        self.app.tools_db_tab.ui.cancel_tool_from_db.show()

    def on_cutout_generation(self):
        cutout_rect_shape = self.ui.cutout_shape_cb.get_value()
        if cutout_rect_shape:
            self.on_rectangular_cutout()
        else:
            self.on_freeform_cutout()

    def on_freeform_cutout(self):

        name = self.ui.obj_combo.currentText()

        # Get source object.
        try:
            cutout_obj = self.app.collection.get_by_name(str(name))
        except Exception as e:
            log.error("CutOut.on_freeform_cutout() --> %s" % str(e))
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), name))
            return "Could not retrieve object: %s" % name

        if cutout_obj is None:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("There is no object selected for Cutout.\nSelect one and try again."))
            return

        dia = self.ui.dia.get_value()
        if 0 in {dia}:
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("Tool Diameter is zero value. Change it to a positive real number."))
            return "Tool Diameter is zero value. Change it to a positive real number."

        try:
            kind = self.ui.obj_kind_combo.get_value()
        except ValueError:
            return

        margin = self.ui.margin.get_value()

        try:
            gaps = self.ui.gaps.get_value()
        except TypeError:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Number of gaps value is missing. Add it and retry."))
            return

        if gaps not in ['None', 'LR', 'TB', '2LR', '2TB', '4', '8']:
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("Gaps value can be only one of: 'None', 'lr', 'tb', '2lr', '2tb', 4 or 8.\n"
                                   "Fill in a correct value and retry."))
            return

        def any_cutout_handler(geom, gapsize):
            r_temp_geo = []
            initial_geo = deepcopy(geom)

            # Get min and max data for each object as we just cut rectangles across X or Y
            xxmin, yymin, xxmax, yymax = CutOut.recursive_bounds(geom)

            px = 0.5 * (xxmin + xxmax) + margin     # center X
            py = 0.5 * (yymin + yymax) + margin     # center Y
            lenx = (xxmax - xxmin) + (margin * 2)
            leny = (yymax - yymin) + (margin * 2)

            if gaps != 'None':
                if gaps == '8' or gaps == '2LR':
                    points = (
                        xxmin - gapsize,                # botleft_x
                        py - gapsize + leny / 4,        # botleft_y
                        xxmax + gapsize,                # topright_x
                        py + gapsize + leny / 4         # topright_y
                    )
                    geom = self.subtract_poly_from_geo(geom, points)
                    r_temp_geo.append(
                        self.intersect_geo(initial_geo, box(points[0], points[1], points[2], points[3]))
                    )

                    points = (
                        xxmin - gapsize,
                        py - gapsize - leny / 4,
                        xxmax + gapsize,
                        py + gapsize - leny / 4
                    )
                    geom = self.subtract_poly_from_geo(geom, points)
                    r_temp_geo.append(
                        self.intersect_geo(initial_geo, box(points[0], points[1], points[2], points[3]))
                    )

                if gaps == '8' or gaps == '2TB':
                    points = (
                        px - gapsize + lenx / 4,
                        yymin - gapsize,
                        px + gapsize + lenx / 4,
                        yymax + gapsize
                    )
                    geom = self.subtract_poly_from_geo(geom, points)
                    r_temp_geo.append(
                        self.intersect_geo(initial_geo, box(points[0], points[1], points[2], points[3]))
                    )

                    points = (
                        px - gapsize - lenx / 4,
                        yymin - gapsize,
                        px + gapsize - lenx / 4,
                        yymax + gapsize
                    )
                    geom = self.subtract_poly_from_geo(geom, points)
                    r_temp_geo.append(
                        self.intersect_geo(initial_geo, box(points[0], points[1], points[2], points[3]))
                    )

                if gaps == '4' or gaps == 'LR':
                    points = (
                        xxmin - gapsize,
                        py - gapsize,
                        xxmax + gapsize,
                        py + gapsize
                    )
                    geom = self.subtract_poly_from_geo(geom, points)
                    r_temp_geo.append(
                        self.intersect_geo(initial_geo, box(points[0], points[1], points[2], points[3]))
                    )

                if gaps == '4' or gaps == 'TB':
                    points = (
                        px - gapsize,
                        yymin - gapsize,
                        px + gapsize,
                        yymax + gapsize
                    )
                    geom = self.subtract_poly_from_geo(geom, points)
                    r_temp_geo.append(
                        self.intersect_geo(initial_geo, box(points[0], points[1], points[2], points[3]))
                    )

            try:
                # for g in geom:
                #     proc_geometry.append(g)
                work_geom = geom.geoms if isinstance(geom, (MultiPolygon, MultiLineString)) else geom
                proc_geometry = [g for g in work_geom if not g.is_empty]
            except TypeError:
                # proc_geometry.append(geom)
                proc_geometry = [geom]

            r_temp_geo = CutOut.flatten(r_temp_geo)
            rest_geometry = [g for g in r_temp_geo if g and not g.is_empty]

            return proc_geometry, rest_geometry

        with self.app.proc_container.new("Generating Cutout ..."):
            formatted_name = cutout_obj.options["name"].rpartition('.')[0]
            outname = "%s_cutout" % formatted_name
            self.app.collection.promise(outname)

            has_mouse_bites = True if self.ui.gaptype_combo.get_value() == 2 else False     # "mouse bytes"

            outname_exc = "%s_mouse_bites" % formatted_name
            if has_mouse_bites is True:
                self.app.collection.promise(outname_exc)

            def job_thread(app_obj):
                solid_geo = []
                gaps_solid_geo = []
                mouse_bites_geo = []

                convex_box = self.ui.convex_box_cb.get_value()
                gapsize = self.ui.gapsize.get_value()
                gapsize = gapsize / 2 + (dia / 2)
                mb_dia = self.ui.mb_dia_entry.get_value()
                mb_buff_val = mb_dia / 2.0
                mb_spacing = self.ui.mb_spacing_entry.get_value()
                gap_type = self.ui.gaptype_combo.get_value()
                thin_entry = self.ui.thin_depth_entry.get_value()

                if cutout_obj.kind == 'gerber':
                    if isinstance(cutout_obj.solid_geometry, list):
                        cutout_obj.solid_geometry = MultiPolygon(cutout_obj.solid_geometry)
                    try:
                        if convex_box:
                            object_geo = cutout_obj.solid_geometry.convex_hull
                        else:
                            object_geo = cutout_obj.solid_geometry
                    except Exception as err:
                        log.error("CutOut.on_freeform_cutout().geo_init() --> %s" % str(err))
                        object_geo = cutout_obj.solid_geometry
                else:
                    if cutout_obj.multigeo is False:
                        object_geo = cutout_obj.solid_geometry
                    else:
                        # first tool in the tools dict
                        t_first = list(cutout_obj.tools.keys())[0]
                        object_geo = cutout_obj.tools[t_first]['solid_geometry']

                if kind == 'single':
                    object_geo = unary_union(object_geo)

                    # for geo in object_geo:
                    if cutout_obj.kind == 'gerber':
                        if isinstance(object_geo, MultiPolygon):
                            x0, y0, x1, y1 = object_geo.bounds
                            object_geo = box(x0, y0, x1, y1)
                        if margin >= 0:
                            geo_buf = object_geo.buffer(margin + abs(dia / 2))
                            geo = geo_buf.exterior
                        else:
                            geo_buf = object_geo.buffer(- margin + abs(dia / 2))
                            geo = unary_union(geo_buf.interiors)
                    else:
                        if isinstance(object_geo, MultiPolygon):
                            x0, y0, x1, y1 = object_geo.bounds
                            object_geo = box(x0, y0, x1, y1)
                        geo_buf = object_geo.buffer(0)
                        geo = geo_buf.exterior

                    if geo.is_empty:
                        self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed."))
                        return 'fail'

                    solid_geo, rest_geo = any_cutout_handler(geom=geo, gapsize=gapsize)
                    if gap_type == 1 and thin_entry != 0:   # "Thin gaps"
                        gaps_solid_geo = rest_geo
                else:
                    object_geo = flatten_shapely_geometry(object_geo)
                    for geom_struct in object_geo:
                        if cutout_obj.kind == 'gerber':
                            if margin >= 0:
                                geom_struct = (geom_struct.buffer(margin + abs(dia / 2))).exterior
                            else:
                                geom_struct_buff = geom_struct.buffer(-margin + abs(dia / 2))
                                geom_struct = geom_struct_buff.interiors

                        c_geo, r_geo = any_cutout_handler(geom=geom_struct, gapsize=gapsize)
                        solid_geo += c_geo
                        if gap_type == 1 and thin_entry != 0:   # "Thin gaps"
                            gaps_solid_geo += r_geo

                if not solid_geo:
                    self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed."))
                    return "fail"

                try:
                    solid_geo = linemerge(solid_geo)
                except Exception:
                    # there ar enot lines but polygons
                    pass

                # If it has mouse bytes
                if has_mouse_bites is True:
                    gapsize -= dia / 2
                    mb_object_geo = deepcopy(object_geo)
                    if kind == 'single':
                        mb_object_geo = unary_union(mb_object_geo)

                        # for geo in object_geo:
                        if cutout_obj.kind == 'gerber':
                            if isinstance(mb_object_geo, MultiPolygon):
                                x0, y0, x1, y1 = mb_object_geo.bounds
                                mb_object_geo = box(x0, y0, x1, y1)
                            if margin >= 0:
                                geo_buf = mb_object_geo.buffer(margin + mb_buff_val)
                            else:
                                geo_buf = mb_object_geo.buffer(margin - mb_buff_val)
                            mb_geo = geo_buf.exterior
                        else:
                            if isinstance(mb_object_geo, MultiPolygon):
                                x0, y0, x1, y1 = mb_object_geo.bounds
                                mb_object_geo = box(x0, y0, x1, y1)
                            geo_buf = mb_object_geo.buffer(0)
                            mb_geo = geo_buf.exterior

                        __, rest_geo = any_cutout_handler(geom=mb_geo, gapsize=gapsize)
                        mouse_bites_geo = rest_geo
                    else:
                        mb_object_geo = flatten_shapely_geometry(mb_object_geo)
                        for mb_geom_struct in mb_object_geo:
                            if cutout_obj.kind == 'gerber':
                                if margin >= 0:
                                    mb_geom_struct = mb_geom_struct.buffer(margin + mb_buff_val)
                                    mb_geom_struct = mb_geom_struct.exterior
                                else:
                                    mb_geom_struct = mb_geom_struct.buffer(-margin + mb_buff_val)
                                    mb_geom_struct = mb_geom_struct.interiors

                            __, mb_r_geo = any_cutout_handler(geom=mb_geom_struct, gapsize=gapsize)
                            mouse_bites_geo += mb_r_geo

                    # list of Shapely Points to mark the drill points centers
                    holes = []
                    for line in mouse_bites_geo:
                        calc_len = 0
                        while calc_len <= line.length:
                            holes.append(line.interpolate(calc_len))
                            calc_len += mb_dia + mb_spacing

                def geo_init(geo_obj, app_object):
                    geo_obj.multigeo = True
                    geo_obj.solid_geometry = deepcopy(solid_geo)

                    xmin, ymin, xmax, ymax = CutOut.recursive_bounds(geo_obj.solid_geometry)
                    geo_obj.options['xmin'] = xmin
                    geo_obj.options['ymin'] = ymin
                    geo_obj.options['xmax'] = xmax
                    geo_obj.options['ymax'] = ymax

                    geo_obj.options['tools_mill_tooldia'] = str(dia)
                    geo_obj.options['tools_mill_cutz'] = self.ui.cutz_entry.get_value()
                    geo_obj.options['tools_mill_multidepth'] = self.ui.mpass_cb.get_value()
                    geo_obj.options['tools_mill_depthperpass'] = self.ui.maxdepth_entry.get_value()

                    geo_obj.tools[1] = deepcopy(self.cut_tool_dict)
                    geo_obj.tools[1]['tooldia'] = str(dia)
                    geo_obj.tools[1]['solid_geometry'] = geo_obj.solid_geometry

                    geo_obj.tools[1]['data']['name'] = outname
                    geo_obj.tools[1]['data']['tools_mill_tooldia'] = str(dia)
                    geo_obj.tools[1]['data']['tools_mill_cutz'] = self.ui.cutz_entry.get_value()
                    geo_obj.tools[1]['data']['tools_mill_multidepth'] = self.ui.mpass_cb.get_value()
                    geo_obj.tools[1]['data']['tools_mill_depthperpass'] = self.ui.maxdepth_entry.get_value()

                    if not gaps_solid_geo:
                        pass
                    else:
                        geo_obj.tools[99] = deepcopy(self.cut_tool_dict)
                        geo_obj.tools[99]['tooldia'] = str(dia)
                        geo_obj.tools[99]['solid_geometry'] = gaps_solid_geo

                        geo_obj.tools[99]['data']['name'] = outname
                        geo_obj.tools[99]['data']['tools_mill_tooldia'] = str(dia)
                        geo_obj.tools[99]['data']['tools_mill_cutz'] = self.ui.thin_depth_entry.get_value()
                        geo_obj.tools[99]['data']['tools_mill_multidepth'] = self.ui.mpass_cb.get_value()
                        geo_obj.tools[99]['data']['tools_mill_depthperpass'] = self.ui.maxdepth_entry.get_value()
                        # plot this tool in a different color
                        geo_obj.tools[99]['data']['override_color'] = "#29a3a3fa"

                def excellon_init(exc_obj, app_o):
                    if not holes:
                        return 'fail'

                    tools = {
                        1: {
                            "tooldia": mb_dia,
                            "drills": holes,
                            "solid_geometry": []
                        }
                    }

                    exc_obj.tools = tools
                    exc_obj.create_geometry()
                    exc_obj.source_file = app_o.f_handlers.export_excellon(obj_name=exc_obj.options['name'],
                                                                           local_use=exc_obj, filename=None,
                                                                           use_thread=False)
                    # calculate the bounds
                    xmin, ymin, xmax, ymax = CutOut.recursive_bounds(exc_obj.solid_geometry)
                    exc_obj.options['xmin'] = xmin
                    exc_obj.options['ymin'] = ymin
                    exc_obj.options['xmax'] = xmax
                    exc_obj.options['ymax'] = ymax

                try:
                    if self.ui.gaptype_combo.get_value() == 2:  # "mouse bytes"
                        ret = app_obj.app_obj.new_object('excellon', outname_exc, excellon_init, autoselected=False)
                        if ret == 'fail':
                            app_obj.inform.emit('[ERROR_NOTCL] %s' % _("Mouse bites failed."))

                    ret = app_obj.app_obj.new_object('geometry', outname, geo_init, autoselected=False)
                    if ret == 'fail':
                        app_obj.inform.emit('[ERROR_NOTCL] %s' % _("Failed."))
                        return

                    # cutout_obj.plot(plot_tool=1)
                    app_obj.inform.emit('[success] %s' % _("Any-form Cutout operation finished."))
                    # self.app.ui.notebook.setCurrentWidget(self.app.ui.project_tab)
                    app_obj.should_we_save = True
                except Exception as ee:
                    log.error(str(ee))

            self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})

    def on_rectangular_cutout(self):
        name = self.ui.obj_combo.currentText()

        # Get source object.
        try:
            cutout_obj = self.app.collection.get_by_name(str(name))
        except Exception as e:
            log.error("CutOut.on_rectangular_cutout() --> %s" % str(e))
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), name))
            return "Could not retrieve object: %s" % name

        if cutout_obj is None:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Object not found"), str(name)))
            return

        dia_val = float(self.ui.dia.get_value())
        if 0 in {dia_val}:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Tool Diameter is zero value. Change it to a positive real number."))
            return "Tool Diameter is zero value. Change it to a positive real number."

        try:
            kind = self.ui.obj_kind_combo.get_value()
        except ValueError:
            return

        margin_val = self.ui.margin.get_value()

        try:
            gaps_val = self.ui.gaps.get_value()
        except TypeError:
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("Number of gaps value is missing. Add it and retry."))
            return

        if gaps_val not in ['None', 'LR', 'TB', '2LR', '2TB', '4', '8']:
            msg = '[WARNING_NOTCL] %s' % _("Gaps value can be only one of: 'None', 'lr', 'tb', '2lr', '2tb', 4 or 8.\n"
                                           "Fill in a correct value and retry.")
            self.app.inform.emit(msg)
            return

        gapsize_val = (dia_val / 2) + self.ui.gapsize.get_value() / 2
        mb_dia_val = self.ui.mb_dia_entry.get_value()
        mb_spacing_val = self.ui.mb_spacing_entry.get_value()
        gap_type_val = self.ui.gaptype_combo.get_value()
        thin_entry_val = self.ui.thin_depth_entry.get_value()
        has_mouse_bites_val = True if self.ui.gaptype_combo.get_value() == 2 else False  # "mouse bytes"

        formatted_name = cutout_obj.options["name"].rpartition('.')[0]
        outname = "%s_cutout" % formatted_name
        self.app.collection.promise(outname)

        outname_exc = cutout_obj.options["name"] + "_mouse_bites"
        if has_mouse_bites_val is True:
            self.app.collection.promise(outname_exc)

        with self.app.proc_container.new("Generating Cutout ..."):
            def job_thread(self_c, app_obj, gaps, gapsize, gap_type, dia, margin, mb_dia, mb_spacing, thin_entry,
                           has_mouse_bites):
                solid_geo = []
                gaps_solid_geo = []
                mouse_bites_geo = []

                mb_buff_val = mb_dia / 2.0

                if cutout_obj.multigeo is False:
                    object_geo = cutout_obj.solid_geometry
                else:
                    # first tool in the tools dict
                    t_first = list(cutout_obj.tools.keys())[0]
                    object_geo = cutout_obj.tools[t_first]['solid_geometry']

                if kind == 'single':
                    # fuse the lines
                    object_geo = unary_union(object_geo)

                    xmin, ymin, xmax, ymax = object_geo.bounds
                    geo = box(xmin, ymin, xmax, ymax)

                    # if Geometry then cut through the geometry

                    # if Gerber create a buffer at a distance
                    if cutout_obj.kind == 'gerber':
                        if margin >= 0:
                            work_margin = margin + abs(dia / 2)
                        else:
                            work_margin = margin - abs(dia / 2)
                        geo = geo.buffer(work_margin)

                    # w_gapsize = gapsize - abs(dia)
                    solid_geo = self.rect_cutout_handler(geo, gaps, gapsize, margin, xmin, ymin, xmax, ymax)

                    if gap_type == 1 and thin_entry != 0:   # "Thin gaps"
                        gaps_solid_geo = self_c.subtract_geo(geo, deepcopy(solid_geo))
                else:
                    if cutout_obj.kind == 'geometry':
                        object_geo = flatten_shapely_geometry(object_geo)
                        for geom_struct in object_geo:
                            geom_struct = unary_union(geom_struct)
                            xmin, ymin, xmax, ymax = geom_struct.bounds
                            # for geometry we don't buffer this with `margin` parameter
                            geom_struct = box(xmin, ymin, xmax, ymax)

                            c_geo = self.rect_cutout_handler(geom_struct, gaps, gapsize, margin, xmin, ymin, xmax, ymax)
                            solid_geo += c_geo
                            if gap_type == 1 and thin_entry != 0:   # "Thin gaps"
                                try:
                                    gaps_solid_geo += self_c.subtract_geo(geom_struct, c_geo)
                                except TypeError:
                                    gaps_solid_geo.append(self_c.subtract_geo(geom_struct, c_geo))
                    elif cutout_obj.kind == 'gerber' and margin >= 0:
                        object_geo = flatten_shapely_geometry(object_geo)
                        for geom_struct in object_geo:
                            geom_struct = unary_union(geom_struct)
                            xmin, ymin, xmax, ymax = geom_struct.bounds
                            geom_struct = box(xmin, ymin, xmax, ymax)

                            geom_struct = geom_struct.buffer(margin + abs(dia / 2))

                            c_geo = self.rect_cutout_handler(geom_struct, gaps, gapsize, margin, xmin, ymin, xmax, ymax)
                            solid_geo += c_geo
                            if gap_type == 1 and thin_entry != 0:   # "Thin gaps"
                                try:
                                    gaps_solid_geo += self_c.subtract_geo(geom_struct, c_geo)
                                except TypeError:
                                    gaps_solid_geo.append(self_c.subtract_geo(geom_struct, c_geo))
                    elif cutout_obj.kind == 'gerber' and margin < 0:
                        msg = '[WARNING_NOTCL] %s' % _("Rectangular cutout with negative margin is not possible.")
                        app_obj.inform.emit(msg)
                        return "fail"

                if not solid_geo:
                    app_obj.inform.emit('[ERROR_NOTCL] %s' % _("Failed."))
                    return "fail"

                try:
                    solid_geo = linemerge(solid_geo)
                except Exception:
                    # there are not lines but polygon
                    pass

                if has_mouse_bites is True:
                    gapsize -= dia / 2
                    mb_object_geo = deepcopy(object_geo)

                    if kind == 'single':
                        # fuse the lines
                        mb_object_geo = unary_union(mb_object_geo)

                        xmin, ymin, xmax, ymax = mb_object_geo.bounds
                        mb_geo = box(xmin, ymin, xmax, ymax)

                        # if Gerber create a buffer at a distance
                        # if Geometry then cut through the geometry
                        if cutout_obj.kind == 'gerber':
                            if margin >= 0:
                                mb_geo = mb_geo.buffer(margin + mb_buff_val)
                            else:
                                mb_geo = mb_geo.buffer(margin - mb_buff_val)
                        else:
                            mb_geo = mb_geo.buffer(0)

                        mb_solid_geo = self.rect_cutout_handler(mb_geo, gaps, gapsize, margin, xmin, ymin, xmax, ymax)

                        mouse_bites_geo = self_c.subtract_geo(mb_geo, mb_solid_geo)
                    else:
                        if cutout_obj.kind == 'geometry':
                            mb_object_geo = flatten_shapely_geometry(mb_object_geo)
                            for mb_geom_struct in mb_object_geo:
                                mb_geom_struct = unary_union(mb_geom_struct)
                                xmin, ymin, xmax, ymax = mb_geom_struct.bounds
                                mb_geom_struct = box(xmin, ymin, xmax, ymax)

                                c_geo = self.rect_cutout_handler(mb_geom_struct, gaps, gapsize, margin, xmin, ymin,
                                                                 xmax, ymax)
                                solid_geo += c_geo

                                try:
                                    mouse_bites_geo += self_c.subtract_geo(mb_geom_struct, c_geo)
                                except TypeError:
                                    mouse_bites_geo.append(self_c.subtract_geo(mb_geom_struct, c_geo))
                        elif cutout_obj.kind == 'gerber' and margin >= 0:
                            mb_object_geo = flatten_shapely_geometry(mb_object_geo)
                            for mb_geom_struct in mb_object_geo:
                                mb_geom_struct = unary_union(mb_geom_struct)
                                xmin, ymin, xmax, ymax = mb_geom_struct.bounds
                                mb_geom_struct = box(xmin, ymin, xmax, ymax)
                                mb_geom_struct = mb_geom_struct.buffer(margin + mb_buff_val)

                                c_geo = self.rect_cutout_handler(mb_geom_struct, gaps, gapsize, margin, xmin, ymin,
                                                                 xmax, ymax)
                                solid_geo += c_geo

                                try:
                                    mouse_bites_geo += self_c.subtract_geo(mb_geom_struct, c_geo)
                                except TypeError:
                                    mouse_bites_geo.append(self_c.subtract_geo(mb_geom_struct, c_geo))
                        elif cutout_obj.kind == 'gerber' and margin < 0:
                            msg2 = '[WARNING_NOTCL] %s' % \
                                  _("Rectangular cutout with negative margin is not possible.")
                            app_obj.inform.emit(msg2)
                            return "fail"

                    # list of Shapely Points to mark the drill points centers
                    holes = []
                    for line in mouse_bites_geo:
                        calc_len = 0
                        while calc_len <= line.length:
                            holes.append(line.interpolate(calc_len))
                            calc_len += mb_dia + mb_spacing

                def geo_init(geo_obj, application_obj):
                    geo_obj.multigeo = True
                    geo_obj.solid_geometry = deepcopy(solid_geo)

                    geo_obj.options['xmin'] = xmin
                    geo_obj.options['ymin'] = ymin
                    geo_obj.options['xmax'] = xmax
                    geo_obj.options['ymax'] = ymax

                    geo_obj.options['tools_mill_tooldia'] = str(dia)
                    geo_obj.options['cutz'] = self_c.ui.cutz_entry.get_value()
                    geo_obj.options['multidepth'] = self_c.ui.mpass_cb.get_value()
                    geo_obj.options['depthperpass'] = self_c.ui.maxdepth_entry.get_value()

                    geo_obj.tools[1] = deepcopy(self_c.cut_tool_dict)
                    geo_obj.tools[1]['tooldia'] = str(dia)
                    geo_obj.tools[1]['solid_geometry'] = geo_obj.solid_geometry

                    geo_obj.tools[1]['data']['name'] = outname
                    geo_obj.tools[1]['data']['tools_mill_cutz'] = self_c.ui.cutz_entry.get_value()
                    geo_obj.tools[1]['data']['tools_mill_multidepth'] = self_c.ui.mpass_cb.get_value()
                    geo_obj.tools[1]['data']['tools_mill_depthperpass'] = self_c.ui.maxdepth_entry.get_value()

                    if not gaps_solid_geo:
                        pass
                    else:
                        geo_obj.tools[99] = deepcopy(self_c.cut_tool_dict)
                        geo_obj.tools[99]['tooldia'] = str(dia)
                        geo_obj.tools[99]['solid_geometry'] = gaps_solid_geo

                        geo_obj.tools[99]['data']['name'] = outname
                        geo_obj.tools[99]['data']['tools_mill_cutz'] = self_c.ui.thin_depth_entry.get_value()
                        geo_obj.tools[99]['data']['tools_mill_multidepth'] = self_c.ui.mpass_cb.get_value()
                        geo_obj.tools[99]['data']['tools_mill_depthperpass'] = self_c.ui.maxdepth_entry.get_value()
                        geo_obj.tools[99]['data']['override_color'] = "#29a3a3fa"

                def excellon_init(exc_obj, app_o):
                    if not holes:
                        return 'fail'

                    tools = {
                        1: {
                            "tooldia": mb_dia,
                            "drills": holes,
                            "solid_geometry": []
                        }
                    }

                    exc_obj.tools = tools
                    exc_obj.create_geometry()
                    exc_obj.source_file = app_o.f_handlers.export_excellon(obj_name=exc_obj.options['name'],
                                                                           local_use=exc_obj,
                                                                           filename=None,
                                                                           use_thread=False)
                    # calculate the bounds
                    e_xmin, e_ymin, e_xmax, e_ymax = CutOut.recursive_bounds(exc_obj.solid_geometry)
                    exc_obj.options['xmin'] = e_xmin
                    exc_obj.options['ymin'] = e_ymin
                    exc_obj.options['xmax'] = e_xmax
                    exc_obj.options['ymax'] = e_ymax

                try:
                    if self_c.ui.gaptype_combo.get_value() == 2:  # "mouse bytes"
                        ret = app_obj.app_obj.new_object('excellon', outname_exc, excellon_init, autoselected=False)
                        if ret == 'fail':
                            app_obj.inform.emit('[ERROR_NOTCL] %s' % _("Mouse bites failed."))

                    ret = app_obj.app_obj.new_object('geometry', outname, geo_init, autoselected=False)
                    if ret == 'fail':
                        app_obj.inform.emit('[ERROR_NOTCL] %s' % _("Failed."))
                        return

                    # cutout_obj.plot(plot_tool=1)
                    app_obj.inform.emit('[success] %s' % _("Rectangular CutOut operation finished."))
                    # self_c.app.ui.notebook.setCurrentWidget(self_c.app.ui.project_tab)
                    app_obj.should_we_save = True
                except Exception as ee:
                    log.error(str(ee))

            self.app.worker_task.emit(
                {
                    'fcn': job_thread,
                    'params': [
                        self, self.app, gaps_val, gapsize_val, gap_type_val, dia_val, margin_val, mb_dia_val,
                        mb_spacing_val, thin_entry_val, has_mouse_bites_val
                    ]
                })

    def rect_cutout_handler(self, geom, gaps, gapsize, margin, xmin, ymin, xmax, ymax):
        px = (0.5 * (xmin + xmax)) + margin  # center X
        py = (0.5 * (ymin + ymax)) + margin  # center Y
        lenx = (xmax - xmin) + (margin * 2)
        leny = (ymax - ymin) + (margin * 2)
        # gapsize /= 2

        if gaps != 'None':
            if gaps == '8' or gaps == '2LR':
                points = (
                    xmin - gapsize,  # botleft_x
                    py - gapsize + leny / 4,  # botleft_y
                    xmax + gapsize,  # topright_x
                    py + gapsize + leny / 4  # topright_y
                )
                geom = self.subtract_poly_from_geo(geom, points)
                points = (
                    xmin - gapsize,
                    py - gapsize - leny / 4,
                    xmax + gapsize,
                    py + gapsize - leny / 4
                )
                geom = self.subtract_poly_from_geo(geom, points)

            if gaps == '8' or gaps == '2TB':
                points = (
                    px - gapsize + lenx / 4,
                    ymin - gapsize,
                    px + gapsize + lenx / 4,
                    ymax + gapsize
                )
                geom = self.subtract_poly_from_geo(geom, points)
                points = (
                    px - gapsize - lenx / 4,
                    ymin - gapsize,
                    px + gapsize - lenx / 4,
                    ymax + gapsize
                )
                geom = self.subtract_poly_from_geo(geom, points)

            if gaps == '4' or gaps == 'LR':
                points = (
                    xmin - gapsize,
                    py - gapsize,
                    xmax + gapsize,
                    py + gapsize
                )
                geom = self.subtract_poly_from_geo(geom, points)

            if gaps == '4' or gaps == 'TB':
                points = (
                    px - gapsize,
                    ymin - gapsize,
                    px + gapsize,
                    ymax + gapsize
                )
                geom = self.subtract_poly_from_geo(geom, points)

        try:
            # for g in geom:
            #     proc_geometry.append(g)
            work_geom = geom.geoms if isinstance(geom, (MultiPolygon, MultiLineString)) else geom
            proc_geometry = [g for g in work_geom if not g.is_empty]
        except TypeError:
            # proc_geometry.append(geom)
            proc_geometry = [geom]
        return proc_geometry

    def on_drill_cut_click(self):

        margin = self.ui.drill_margin_entry.get_value()
        pitch = self.ui.drill_pitch_entry.get_value()
        drill_dia = self.ui.drill_dia_entry.get_value()

        name = self.ui.drillcut_object_combo.currentText()

        # Get source object.
        try:
            obj = self.app.collection.get_by_name(str(name))
        except Exception as e:
            log.error("CutOut.on_freeform_cutout() --> %s" % str(e))
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), name))
            return "Could not retrieve object: %s" % name

        if obj is None:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("There is no object selected for Cutout.\nSelect one and try again."))
            return

        cut_geo_solid = unary_union(obj.solid_geometry)

        drill_list = []
        try:
            for geo in cut_geo_solid:
                if isinstance(geo, LineString):
                    cut_geo = geo.parallel_offset(margin, side='left')
                elif isinstance(geo, Polygon):
                    cut_geo = geo.buffer(margin).exterior
                else:
                    self.app.inform.emit('[WARNING_NOTCL] %s %s' % (_("Failed."), _("Could not add drills.")))
                    return

                geo_length = cut_geo.length

                dist = 0
                while dist <= geo_length:
                    drill_list.append(cut_geo.interpolate(dist))
                    dist += pitch

                if dist < geo_length:
                    drill_list.append(Point(list(cut_geo.coords)[-1]))
        except TypeError:
            if isinstance(cut_geo_solid, LineString):
                cut_geo = cut_geo_solid.parallel_offset(margin, side='left')
            elif isinstance(cut_geo_solid, Polygon):
                cut_geo = cut_geo_solid.buffer(margin).exterior
            else:
                self.app.inform.emit('[WARNING_NOTCL] %s %s' % (_("Failed."), _("Could not add drills.")))
                return

            geo_length = cut_geo.length

            dist = 0
            while dist <= geo_length:
                drill_list.append(cut_geo.interpolate(dist))
                dist += pitch

            if dist < geo_length:
                drill_list.append(Point(list(cut_geo.coords)[-1]))

        if not drill_list:
            self.app.inform.emit('[WARNING_NOTCL] %s %s' % (_("Failed."), _("Could not add drills.")))
            return

        tools = {
            1: {
                "tooldia": drill_dia,
                "drills": drill_list,
                "slots": [],
                "solid_geometry": []
            }
        }

        formatted_name = obj.options['name'].rpartition('.')[0]
        if formatted_name == '':
            formatted_name = obj.options['name']
        outname = '%s_drillcut' % formatted_name

        def obj_init(obj_inst, app_inst):
            obj_inst.tools = deepcopy(tools)
            obj_inst.create_geometry()
            obj_inst.source_file = app_inst.f_handlers.export_excellon(obj_name=outname, local_use=obj_inst,
                                                                       filename=None,
                                                                       use_thread=False)

        with self.app.proc_container.new('%s...' % _("Working")):
            try:
                ret = self.app.app_obj.new_object("excellon", outname, obj_init, autoselected=False)
            except Exception as e:
                log.error("Error on Drill Cutting Excellon object creation: %s" % str(e))
                return

            if ret != 'fail':
                self.app.inform.emit('[success] %s' % _("Done."))

    def on_manual_gap_click(self):
        name = self.ui.man_object_combo.currentText()

        # Get source object.
        try:
            self.man_cutout_obj = self.app.collection.get_by_name(str(name))
        except Exception as e:
            log.error("CutOut.on_manual_cutout() --> %s" % str(e))
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), name))
            return

        if self.man_cutout_obj is None:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' %
                                 (_("Geometry object for manual cutout not found"), self.man_cutout_obj))
            return

        self.app.inform.emit(_("Click on the selected geometry object perimeter to create a bridge gap ..."))
        self.app.geo_editor.tool_shape.enabled = True

        self.manual_solid_geo = deepcopy(self.flatten(self.man_cutout_obj.solid_geometry))

        self.cutting_dia = self.ui.dia.get_value()
        if 0 in {self.cutting_dia}:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Tool Diameter is zero value. Change it to a positive real number."))
            return

        if self.ui.gaptype_combo.get_value() == 2:  # "mouse bytes"
            mb_dia = self.ui.mb_dia_entry.get_value()
            b_dia = (self.cutting_dia / 2.0) - (mb_dia / 2.0)
            # flaten manual geometry
            unified_man_geo = unary_union(self.manual_solid_geo)
            buff_man_geo = unified_man_geo.buffer(b_dia)
            if isinstance(buff_man_geo, MultiPolygon):
                int_list = []
                for b_geo in buff_man_geo.geoms:
                    int_list += b_geo.interiors
            elif isinstance(buff_man_geo, Polygon):
                int_list = buff_man_geo.interiors
            else:
                self.app.log.debug("Not supported geometry at the moment: %s" % type(buff_man_geo))
                return
            self.mb_manual_solid_geo = self.flatten(int_list)

        self.cutting_gapsize = self.ui.gapsize.get_value()

        name = self.ui.man_object_combo.currentText()
        # Get Geometry source object to be used as target for Manual adding Gaps
        try:
            self.man_cutout_obj = self.app.collection.get_by_name(str(name))
        except Exception as e:
            log.error("CutOut.on_manual_cutout() --> %s" % str(e))
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), name))
            return

        if self.app.use_3d_engine:
            self.app.plotcanvas.graph_event_disconnect('key_press', self.app.ui.keyPressEvent)
            self.app.plotcanvas.graph_event_disconnect('mouse_press', self.app.on_mouse_click_over_plot)
            self.app.plotcanvas.graph_event_disconnect('mouse_release', self.app.on_mouse_click_release_over_plot)
            self.app.plotcanvas.graph_event_disconnect('mouse_move', self.app.on_mouse_move_over_plot)
        else:
            self.app.plotcanvas.graph_event_disconnect(self.app.kp)
            self.app.plotcanvas.graph_event_disconnect(self.app.mp)
            self.app.plotcanvas.graph_event_disconnect(self.app.mr)
            self.app.plotcanvas.graph_event_disconnect(self.app.mm)

        self.kp = self.app.plotcanvas.graph_event_connect('key_press', self.on_key_press)
        self.mm = self.app.plotcanvas.graph_event_connect('mouse_move', self.on_mouse_move)
        self.mr = self.app.plotcanvas.graph_event_connect('mouse_release', self.on_mouse_click_release)

        self.mouse_events_connected = True

        if self.ui.big_cursor_cb.get_value():
            self.old_cursor_type = self.app.defaults["global_cursor_type"]
            self.app.on_cursor_type(val="big")

        self.app.defaults['global_selection_shape'] = False
        # disable the notebook until finished
        self.app.ui.notebook.setDisabled(True)

    def on_manual_cutout(self, click_pos):

        if self.man_cutout_obj is None:
            msg = '[ERROR_NOTCL] %s: %s' % (_("Geometry object for manual cutout not found"), self.man_cutout_obj)
            self.app.inform.emit(msg)
            return

        # use the snapped position as reference
        snapped_pos = self.app.geo_editor.snap(click_pos[0], click_pos[1])

        cut_poly = self.cutting_geo(pos=(snapped_pos[0], snapped_pos[1]))

        gap_type = self.ui.gaptype_combo.get_value()
        gaps_solid_geo = None
        if gap_type == 1 and self.ui.thin_depth_entry.get_value() != 0:     # "Thin gaps"
            gaps_solid_geo = self.intersect_geo(self.manual_solid_geo, cut_poly)

        if gap_type == 2:   # "Mouse Bytes"
            rests_geo = self.intersect_geo(self.mb_manual_solid_geo, cut_poly)
            if isinstance(rests_geo, list):
                self.mb_manual_cuts += rests_geo
            else:
                self.mb_manual_cuts.append(rests_geo)

        # first subtract geometry for the total solid_geometry
        new_solid_geometry = CutOut.subtract_geo(self.man_cutout_obj.solid_geometry, cut_poly)
        try:
            new_solid_geometry = linemerge(new_solid_geometry)
        except ValueError:
            pass
        self.man_cutout_obj.solid_geometry = new_solid_geometry

        # then do it on each tool in the manual cutout Geometry object
        try:
            self.man_cutout_obj.multigeo = True

            self.man_cutout_obj.tools[1]['solid_geometry'] = new_solid_geometry
            self.man_cutout_obj.tools[1]['data']['name'] = self.man_cutout_obj.options['name'] + '_cutout'
            self.man_cutout_obj.tools[1]['data']['tools_mill_cutz'] = self.ui.cutz_entry.get_value()
            self.man_cutout_obj.tools[1]['data']['tools_mill_multidepth'] = self.ui.mpass_cb.get_value()
            self.man_cutout_obj.tools[1]['data']['tools_mill_depthperpass'] = self.ui.maxdepth_entry.get_value()
        except KeyError:
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("No tool in the Geometry object."))
            return

        dia = self.ui.dia.get_value()
        if gaps_solid_geo:
            if 99 not in self.man_cutout_obj.tools:
                self.man_cutout_obj.tools.update({
                    99: self.cut_tool_dict
                })
                self.man_cutout_obj.tools[99]['tooldia'] = str(dia)
                self.man_cutout_obj.tools[99]['solid_geometry'] = [gaps_solid_geo]

                self.man_cutout_obj.tools[99]['data']['name'] = self.man_cutout_obj.options['name'] + '_cutout'
                self.man_cutout_obj.tools[99]['data']['tools_mill_cutz'] = self.ui.thin_depth_entry.get_value()
                self.man_cutout_obj.tools[99]['data']['tools_mill_multidepth'] = self.ui.mpass_cb.get_value()
                self.man_cutout_obj.tools[99]['data']['tools_mill_depthperpass'] = self.ui.maxdepth_entry.get_value()
                self.man_cutout_obj.tools[99]['data']['override_color'] = "#29a3a3fa"
            else:
                self.man_cutout_obj.tools[99]['solid_geometry'].append(gaps_solid_geo)

        self.man_cutout_obj.plot(plot_tool=1)
        self.app.inform.emit('%s' % _("Added manual Bridge Gap. Left click to add another or right click to finish."))

        self.app.should_we_save = True

    def on_manual_geo(self):
        name = self.ui.obj_combo.currentText()

        # Get source object.
        try:
            cutout_obj = self.app.collection.get_by_name(str(name))
        except Exception as e:
            log.error("CutOut.on_manual_geo() --> %s" % str(e))
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), name))
            return "Could not retrieve object: %s" % name

        if cutout_obj is None:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("There is no Gerber object selected for Cutout.\n"
                                   "Select one and try again."))
            return

        if cutout_obj.kind != 'gerber':
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("The selected object has to be of Gerber type.\n"
                                   "Select a Gerber file and try again."))
            return

        dia = float(self.ui.dia.get_value())
        if 0 in {dia}:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Tool Diameter is zero value. Change it to a positive real number."))
            return

        try:
            kind = self.ui.obj_kind_combo.get_value()
        except ValueError:
            return

        margin = float(self.ui.margin.get_value())
        convex_box = self.ui.convex_box_cb.get_value()

        def geo_init(geo_obj, app_obj):
            geo_union = unary_union(cutout_obj.solid_geometry)

            if convex_box:
                geo = geo_union.convex_hull
                geo_obj.solid_geometry = geo.buffer(margin + abs(dia / 2))
            elif kind == 'single':
                if isinstance(geo_union, Polygon) or \
                        (isinstance(geo_union, list) and len(geo_union) == 1) or \
                        (isinstance(geo_union, MultiPolygon) and len(geo_union.geoms) == 1):
                    geo_obj.solid_geometry = geo_union.buffer(margin + abs(dia / 2)).exterior
                elif isinstance(geo_union, MultiPolygon):
                    x0, y0, x1, y1 = geo_union.bounds
                    geo = box(x0, y0, x1, y1)
                    geo_obj.solid_geometry = geo.buffer(margin + abs(dia / 2))
                else:
                    app_obj.inform.emit('[ERROR_NOTCL] %s: %s' % (
                        _("Geometry not supported"), type(geo_union)))
                    return 'fail'
            else:
                geo = geo_union
                geo = geo.buffer(margin + abs(dia / 2))
                if isinstance(geo, Polygon):
                    geo_obj.solid_geometry = geo.exterior
                elif isinstance(geo, MultiPolygon):
                    solid_geo = []
                    for poly in geo:
                        solid_geo.append(poly.exterior)
                    geo_obj.solid_geometry = deepcopy(solid_geo)

            geo_obj.options['tools_mill_tooldia'] = str(dia)
            geo_obj.options['cutz'] = self.ui.cutz_entry.get_value()
            geo_obj.options['multidepth'] = self.ui.mpass_cb.get_value()
            geo_obj.options['depthperpass'] = self.ui.maxdepth_entry.get_value()

            geo_obj.multigeo = True

            geo_obj.tools.update({
                1: self.cut_tool_dict
            })
            geo_obj.tools[1]['tooldia'] = str(dia)
            geo_obj.tools[1]['solid_geometry'] = geo_obj.solid_geometry

            geo_obj.tools[1]['data']['name'] = outname
            geo_obj.tools[1]['data']['tools_mill_cutz'] = self.ui.cutz_entry.get_value()
            geo_obj.tools[1]['data']['tools_mill_multidepth'] = self.ui.mpass_cb.get_value()
            geo_obj.tools[1]['data']['tools_mill_depthperpass'] = self.ui.maxdepth_entry.get_value()

        outname = cutout_obj.options["name"] + "_cutout"
        self.app.app_obj.new_object('geometry', outname, geo_init, autoselected=False)

    def cutting_geo(self, pos):
        self.cutting_dia = float(self.ui.dia.get_value())
        self.cutting_gapsize = float(self.ui.gapsize.get_value())

        offset = self.cutting_dia / 2 + self.cutting_gapsize / 2

        # cutting area definition
        orig_x = pos[0]
        orig_y = pos[1]
        xmin = orig_x - offset
        ymin = orig_y - offset
        xmax = orig_x + offset
        ymax = orig_y + offset

        cut_poly = box(xmin, ymin, xmax, ymax)
        return cut_poly

    # To be called after clicking on the plot.
    def on_mouse_click_release(self, event):

        if self.app.use_3d_engine:
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

        # do paint single only for left mouse clicks
        if event.button == 1:
            self.app.inform.emit(_("Making manual bridge gap..."))

            pos = self.app.plotcanvas.translate_coords(event_pos)

            self.on_manual_cutout(click_pos=pos)

        # if RMB then we exit
        elif event.button == right_button and self.mouse_is_dragging is False:
            if self.app.use_3d_engine:
                self.app.plotcanvas.graph_event_disconnect('key_press', self.on_key_press)
                self.app.plotcanvas.graph_event_disconnect('mouse_move', self.on_mouse_move)
                self.app.plotcanvas.graph_event_disconnect('mouse_release', self.on_mouse_click_release)
            else:
                self.app.plotcanvas.graph_event_disconnect(self.kp)
                self.app.plotcanvas.graph_event_disconnect(self.mm)
                self.app.plotcanvas.graph_event_disconnect(self.mr)

            self.app.kp = self.app.plotcanvas.graph_event_connect('key_press', self.app.ui.keyPressEvent)
            self.app.mp = self.app.plotcanvas.graph_event_connect('mouse_press', self.app.on_mouse_click_over_plot)
            self.app.mr = self.app.plotcanvas.graph_event_connect('mouse_release',
                                                                  self.app.on_mouse_click_release_over_plot)
            self.app.mm = self.app.plotcanvas.graph_event_connect('mouse_move', self.app.on_mouse_move_over_plot)

            # Remove any previous utility shape
            self.app.geo_editor.tool_shape.clear(update=True)
            self.app.geo_editor.tool_shape.enabled = False

            # signal that the mouse events are disconnected from local methods
            self.mouse_events_connected = False

            if self.ui.big_cursor_cb.get_value():
                # restore cursor
                self.app.on_cursor_type(val=self.old_cursor_type)
            # restore selection
            self.app.defaults['global_selection_shape'] = self.old_selection_state

            # rebuild the manual Geometry object
            self.man_cutout_obj.build_ui()

            # plot the final object
            self.man_cutout_obj.plot()

            # mouse bytes
            if self.ui.gaptype_combo.get_value() == 2:  # "mouse bytes"
                with self.app.proc_container.new("Generating Excellon ..."):
                    outname_exc = self.man_cutout_obj.options["name"] + "_mouse_bites"
                    self.app.collection.promise(outname_exc)

                    def job_thread(app_obj):
                        # list of Shapely Points to mark the drill points centers
                        holes = []
                        mb_dia = self.ui.mb_dia_entry.get_value()
                        mb_spacing = self.ui.mb_spacing_entry.get_value()
                        for line in self.mb_manual_cuts:
                            calc_len = 0
                            while calc_len <= line.length:
                                holes.append(line.interpolate(calc_len))
                                calc_len += mb_dia + mb_spacing
                        self.mb_manual_cuts[:] = []

                        def excellon_init(exc_obj, app_o):
                            if not holes:
                                return 'fail'

                            tools = {
                                1: {
                                    "tooldia": mb_dia,
                                    "drills": holes,
                                    "solid_geometry": []
                                }
                            }

                            exc_obj.tools = tools
                            exc_obj.create_geometry()
                            exc_obj.source_file = app_o.f_handlers.export_excellon(obj_name=exc_obj.options['name'],
                                                                                   local_use=exc_obj,
                                                                                   filename=None,
                                                                                   use_thread=False)
                            # calculate the bounds
                            xmin, ymin, xmax, ymax = CutOut.recursive_bounds(exc_obj.solid_geometry)
                            exc_obj.options['xmin'] = xmin
                            exc_obj.options['ymin'] = ymin
                            exc_obj.options['xmax'] = xmax
                            exc_obj.options['ymax'] = ymax

                        ret = app_obj.app_obj.new_object('excellon', outname_exc, excellon_init)
                        if ret == 'fail':
                            app_obj.inform.emit('[ERROR_NOTCL] %s' % _("Mouse bites failed."))

                    self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})

            self.app.ui.notebook.setDisabled(False)
            self.app.inform.emit('[success] %s' % _("Finished manual adding of gaps."))

    def on_mouse_move(self, event):

        self.app.on_mouse_move_over_plot(event=event)

        if self.app.use_3d_engine:
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
        event_pos = (x, y)

        pos = self.canvas.translate_coords(event_pos)
        event.xdata, event.ydata = pos[0], pos[1]

        if event_is_dragging is True:
            self.mouse_is_dragging = True
        else:
            self.mouse_is_dragging = False

        try:
            x = float(event.xdata)
            y = float(event.ydata)
        except TypeError:
            return

        if self.app.grid_status():
            snap_x, snap_y = self.app.geo_editor.snap(x, y)
        else:
            snap_x, snap_y = x, y

        self.x_pos, self.y_pos = snap_x, snap_y

        # #################################################
        # ### This section makes the cutting geo to #######
        # ### rotate if it intersects the target geo ######
        # #################################################
        cut_geo = self.cutting_geo(pos=(snap_x, snap_y))
        man_geo = self.man_cutout_obj.solid_geometry

        def get_angle(geo):
            line = cut_geo.intersection(geo)

            try:
                pt1_x = line.coords[0][0]
                pt1_y = line.coords[0][1]
                pt2_x = line.coords[1][0]
                pt2_y = line.coords[1][1]
                dx = pt1_x - pt2_x
                dy = pt1_y - pt2_y

                if dx == 0 or dy == 0:
                    angle = 0
                else:
                    radian = math.atan(dx / dy)
                    angle = radian * 180 / math.pi
            except Exception:
                angle = 0
            return angle

        r_man_geo = man_geo.geoms if isinstance(man_geo, (MultiPolygon, MultiLineString)) else man_geo
        try:
            rot_angle = 0
            for geo_el in r_man_geo:
                if isinstance(geo_el, Polygon):
                    work_geo = geo_el.exterior
                    rot_angle = get_angle(geo=work_geo) if cut_geo.intersects(work_geo) else 0
                else:
                    rot_angle = get_angle(geo=geo_el) if cut_geo.intersects(geo_el) else 0

                if rot_angle != 0:
                    break
        except TypeError:
            if isinstance(r_man_geo, Polygon):
                work_geo = r_man_geo.exterior
                rot_angle = get_angle(geo=work_geo) if cut_geo.intersects(work_geo) else 0
            else:
                rot_angle = get_angle(geo=r_man_geo) if cut_geo.intersects(r_man_geo) else 0

        # rotate only if there is an angle to rotate to
        if rot_angle != 0:
            cut_geo = affinity.rotate(cut_geo, -rot_angle)

        # Remove any previous utility shape
        self.app.geo_editor.tool_shape.clear(update=True)
        self.draw_utility_geometry(geo=cut_geo)

    def draw_utility_geometry(self, geo):
        self.app.geo_editor.tool_shape.add(
            shape=geo,
            color=(self.app.defaults["global_draw_color"] + '80'),
            update=False,
            layer=0,
            tolerance=None)
        self.app.geo_editor.tool_shape.redraw()

    def on_key_press(self, event):
        # events out of the self.app.collection view (it's about Project Tab) are of type int
        if type(event) is int:
            key = event
        # events from the GUI are of type QKeyEvent
        elif type(event) == QtGui.QKeyEvent:
            key = event.key()
        elif isinstance(event, mpl_key_event):  # MatPlotLib key events are trickier to interpret than the rest
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
                    # modifiers = QtCore.Qt.KeyboardModifier.ShiftModifier
                    pass
                else:
                    # modifiers = QtCore.Qt.KeyboardModifier.NoModifier
                    pass
                key = QtGui.QKeySequence(key_text)
        # events from Vispy are of type KeyEvent
        else:
            key = event.key

        # Escape = Deselect All
        if key == QtCore.Qt.Key.Key_Escape or key == 'Escape':
            if self.mouse_events_connected is True:
                self.mouse_events_connected = False
                if self.app.use_3d_engine:
                    self.app.plotcanvas.graph_event_disconnect('key_press', self.on_key_press)
                    self.app.plotcanvas.graph_event_disconnect('mouse_move', self.on_mouse_move)
                    self.app.plotcanvas.graph_event_disconnect('mouse_release', self.on_mouse_click_release)
                else:
                    self.app.plotcanvas.graph_event_disconnect(self.kp)
                    self.app.plotcanvas.graph_event_disconnect(self.mm)
                    self.app.plotcanvas.graph_event_disconnect(self.mr)

                self.app.kp = self.app.plotcanvas.graph_event_connect('key_press', self.app.ui.keyPressEvent)
                self.app.mp = self.app.plotcanvas.graph_event_connect('mouse_press', self.app.on_mouse_click_over_plot)
                self.app.mr = self.app.plotcanvas.graph_event_connect('mouse_release',
                                                                      self.app.on_mouse_click_release_over_plot)
                self.app.mm = self.app.plotcanvas.graph_event_connect('mouse_move', self.app.on_mouse_move_over_plot)

                if self.ui.big_cursor_cb.get_value():
                    # restore cursor
                    self.app.on_cursor_type(val=self.old_cursor_type)
                # restore selection
                self.app.defaults['global_selection_shape'] = self.old_selection_state

            # Remove any previous utility shape
            self.app.geo_editor.tool_shape.clear(update=True)
            self.app.geo_editor.tool_shape.enabled = False

            # restore the notebook state
            self.app.ui.notebook.setDisabled(False)
            self.app.inform.emit("[WARNING_NOTCL] %s" % _("Cancelled."))

        # Grid toggle
        if key == QtCore.Qt.Key.Key_G or key == 'G':
            self.app.ui.grid_snap_btn.trigger()

        # Jump to coords
        if key == QtCore.Qt.Key.Key_J or key == 'J':
            l_x, l_y = self.app.on_jump_to()
            self.app.geo_editor.tool_shape.clear(update=True)
            geo = self.cutting_geo(pos=(l_x, l_y))
            self.draw_utility_geometry(geo=geo)

    @staticmethod
    def subtract_poly_from_geo(solid_geo, pts):
        """
        Subtract polygon made from points from the given object.
        This only operates on the paths in the original geometry,
        i.e. it converts polygons into paths.

        :param solid_geo:   Geometry from which to subtract.
        :param pts:         a tuple of coordinates in format (x0, y0, x1, y1)
        :type pts:          tuple

        x0: x coord for lower left vertex of the polygon.
        y0: y coord for lower left vertex of the polygon.
        x1: x coord for upper right vertex of the polygon.
        y1: y coord for upper right vertex of the polygon.

        :return: none
        """

        x0 = pts[0]
        y0 = pts[1]
        x1 = pts[2]
        y1 = pts[3]

        points = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

        # pathonly should be always True, otherwise polygons are not subtracted
        flat_geometry = CutOut.flatten(geometry=solid_geo)

        log.debug("%d paths" % len(flat_geometry))

        polygon = Polygon(points)
        toolgeo = unary_union(polygon)
        diffs = []
        for target in flat_geometry:
            if type(target) == LineString or type(target) == LinearRing:
                diffs.append(target.difference(toolgeo))
            else:
                log.warning("Not implemented.")

        return unary_union(diffs)

    @staticmethod
    def flatten(geometry):
        """
        Creates a list of non-iterable linear geometry objects.
        Polygons are expanded into its exterior and interiors.

        Results are placed in self.flat_geometry

        :param geometry: Shapely type or list or list of list of such.
        """
        flat_geo = []
        work_geo = geometry.geoms if isinstance(geometry, (MultiPolygon, MultiLineString)) else geometry
        try:
            for geo in work_geo:
                if geo:
                    flat_geo += CutOut.flatten(geometry=geo)
        except TypeError:
            if isinstance(work_geo, Polygon) and not work_geo.is_empty:
                flat_geo.append(work_geo.exterior)
                CutOut.flatten(geometry=work_geo.interiors)
            elif not work_geo.is_empty:
                flat_geo.append(work_geo)

        return flat_geo

    @staticmethod
    def recursive_bounds(geometry):
        """
        Return the bounds of the biggest bounding box in geometry, one that include all.

        :param geometry:    a iterable object that holds geometry
        :return:            Returns coordinates of rectangular bounds of geometry: (xmin, ymin, xmax, ymax).
        """

        # now it can get bounds for nested lists of objects

        def bounds_rec(obj):
            try:
                minx = Inf
                miny = Inf
                maxx = -Inf
                maxy = -Inf

                for k in obj:
                    minx_, miny_, maxx_, maxy_ = bounds_rec(k)
                    minx = min(minx, minx_)
                    miny = min(miny, miny_)
                    maxx = max(maxx, maxx_)
                    maxy = max(maxy, maxy_)
                return minx, miny, maxx, maxy
            except TypeError:
                # it's a Shapely object, return it's bounds
                if obj:
                    return obj.bounds

        return bounds_rec(geometry)

    def subtract_geo(self, target_geo, subtractor):
        """
        Subtract subtractor polygon from the target_geo. This only operates on the paths in the target_geo,
        i.e. it converts polygons into paths.

        :param target_geo:      geometry from which to subtract
        :param subtractor:      a list of Points, a LinearRing or a Polygon that will be subtracted from target_geo
        :return:                a unary_union of the resulting geometry
        """

        if target_geo is None:
            target_geo = []

        # flatten() takes care of possible empty geometry making sure that is filtered
        flat_geometry = CutOut.flatten(target_geo)
        log.debug("%d paths" % len(flat_geometry))

        toolgeo = unary_union(subtractor)

        diffs = []
        for target in flat_geometry:
            if isinstance(target, LineString) or isinstance(target, LinearRing) or isinstance(target, MultiLineString):
                d_geo = target.difference(toolgeo)
                if not d_geo.is_empty:
                    diffs.append(d_geo)
            else:
                self.app.log.warning("Not implemented.")

        return unary_union(diffs)

    @staticmethod
    def intersect_geo(target_geo, second_geo):
        """

        :param target_geo:
        :type target_geo:
        :param second_geo:
        :type second_geo:
        :return:
        :rtype:
        """

        results = []
        target_geo = flatten_shapely_geometry(target_geo)
        for geo in target_geo:
            if second_geo.intersects(geo):
                results.append(second_geo.intersection(geo))

        return CutOut.flatten(results)

    def reset_fields(self):
        self.ui.obj_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))


class CutoutUI:
    pluginName = _("Cutout")

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

        # Title
        title_label = FCLabel("%s" % self.pluginName)
        title_label.setStyleSheet("""
                                QLabel
                                {
                                    font-size: 16px;
                                    font-weight: bold;
                                }
                                """)
        title_label.setToolTip(
            _("Create a Geometry object with toolpaths\n"
              "for cutting out the object from the surrounding material.")
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

        self.object_label = FCLabel('<span style="color:darkorange;"><b>%s</b></span>' % _("Source Object"))
        self.object_label.setToolTip('%s.' % _("Object to be cutout"))
        self.tools_box.addWidget(self.object_label)

        # #############################################################################################################
        # Object Frame
        # #############################################################################################################
        obj_frame = FCFrame()
        self.tools_box.addWidget(obj_frame)

        # Grid Layout
        obj_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        obj_frame.setLayout(obj_grid)

        # Object kind
        self.kindlabel = FCLabel('%s:' % _('Kind'))
        self.kindlabel.setToolTip(
            _("Choice of what kind the object we want to cutout is.\n"
              "- Single: contain a single PCB Gerber outline object.\n"
              "- Panel: a panel PCB Gerber object, which is made\n"
              "out of many individual PCB outlines.")
        )
        self.obj_kind_combo = RadioSet([
            {"label": _("Single"), "value": "single"},
            {"label": _("Panel"), "value": "panel"},
        ])
        obj_grid.addWidget(self.kindlabel, 2, 0)
        obj_grid.addWidget(self.obj_kind_combo, 2, 1)

        # Type of object to be cutout
        self.type_obj_radio = RadioSet([
            {"label": _("Gerber"), "value": "grb"},
            {"label": _("Geometry"), "value": "geo"},
        ])

        self.type_obj_combo_label = FCLabel('%s:' % _("Type"))
        self.type_obj_combo_label.setToolTip(
            _("Specify the type of object to be cutout.\n"
              "It can be of type: Gerber or Geometry.\n"
              "What is selected here will dictate the kind\n"
              "of objects that will populate the 'Object' combobox.")
        )

        obj_grid.addWidget(self.type_obj_combo_label, 4, 0)
        obj_grid.addWidget(self.type_obj_radio, 4, 1)

        # Object to be cutout
        self.obj_combo = FCComboBox()
        self.obj_combo.setModel(self.app.collection)
        self.obj_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.obj_combo.is_last = False

        obj_grid.addWidget(self.obj_combo, 6, 0, 1, 2)

        self.tool_sel_label = FCLabel('<span style="color:indigo;"><b>%s</b></span>' % _('Cutout Tool'))
        self.tools_box.addWidget(self.tool_sel_label)

        # #############################################################################################################
        # Tool Frame
        # #############################################################################################################
        tool_frame = FCFrame()
        self.tools_box.addWidget(tool_frame)

        # Grid Layout
        tool_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        tool_frame.setLayout(tool_grid)

        # Tool Diameter
        self.dia = FCDoubleSpinner(callback=self.confirmation_message)
        self.dia.set_precision(self.decimals)
        self.dia.set_range(0.0000, 10000.0000)

        self.dia_label = FCLabel('%s:' % _("Tool Dia"))
        self.dia_label.setToolTip(
            _("Diameter of the tool used to cutout\n"
              "the PCB shape out of the surrounding material.")
        )
        tool_grid.addWidget(self.dia_label, 0, 0)
        tool_grid.addWidget(self.dia, 0, 1)

        hlay = QtWidgets.QHBoxLayout()

        # Search and Add new Tool
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

        # Pick from DB new Tool
        self.addtool_from_db_btn = FCButton(_('Pick from DB'))
        self.addtool_from_db_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/search_db32.png'))
        self.addtool_from_db_btn.setToolTip(
            _("Add a new tool to the Tool Table\n"
              "from the Tools Database.\n"
              "Tools database administration in in:\n"
              "Menu: Options -> Tools Database")
        )
        hlay.addWidget(self.addtool_from_db_btn)

        tool_grid.addLayout(hlay, 2, 0, 1, 2)

        # separator_line = QtWidgets.QFrame()
        # separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        # separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        # obj_grid.addWidget(separator_line, 18, 0, 1, 2)

        self.param_label = FCLabel('<span style="color:blue;"><b>%s</b></span>' % _("Tool Parameters"))
        self.tools_box.addWidget(self.param_label)

        # #############################################################################################################
        # Tool Params Frame
        # #############################################################################################################
        tool_par_frame = FCFrame()
        self.tools_box.addWidget(tool_par_frame)

        # Grid Layout
        param_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        tool_par_frame.setLayout(param_grid)

        # Convex Shape
        # Surrounding convex box shape
        self.convex_box_label = FCLabel('%s:' % _("Convex Shape"))
        self.convex_box_label.setToolTip(
            _("Create a convex shape surrounding the entire PCB.\n"
              "Used only if the source object type is Gerber.")
        )
        self.convex_box_cb = FCCheckBox()
        self.convex_box_cb.setToolTip(
            _("Create a convex shape surrounding the entire PCB.\n"
              "Used only if the source object type is Gerber.")
        )
        param_grid.addWidget(self.convex_box_label, 0, 0)
        param_grid.addWidget(self.convex_box_cb, 0, 1)

        # Cut Z
        cutzlabel = FCLabel('%s:' % _('Cut Z'))
        cutzlabel.setToolTip(
            _("Cutting depth (negative)\n"
              "below the copper surface.")
        )
        self.cutz_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.cutz_entry.set_precision(self.decimals)
        self.cutz_entry.setRange(-10000.0000, 10000.0000)

        self.cutz_entry.setSingleStep(0.1)

        param_grid.addWidget(cutzlabel, 2, 0)
        param_grid.addWidget(self.cutz_entry, 2, 1)

        # Multi-pass
        self.mpass_cb = FCCheckBox('%s:' % _("Multi-Depth"))
        self.mpass_cb.setToolTip(
            _("Use multiple passes to limit\n"
              "the cut depth in each pass. Will\n"
              "cut multiple times until Cut Z is\n"
              "reached.")
        )

        self.maxdepth_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.maxdepth_entry.set_precision(self.decimals)
        self.maxdepth_entry.setRange(0, 10000.0000)
        self.maxdepth_entry.setSingleStep(0.1)

        self.maxdepth_entry.setToolTip(_("Depth of each pass (positive)."))

        param_grid.addWidget(self.mpass_cb, 4, 0)
        param_grid.addWidget(self.maxdepth_entry, 4, 1)

        self.ois_mpass_geo = OptionalInputSection(self.mpass_cb, [self.maxdepth_entry])

        # Margin
        self.margin = FCDoubleSpinner(callback=self.confirmation_message)
        self.margin.set_range(-10000.0000, 10000.0000)
        self.margin.setSingleStep(0.1)
        self.margin.set_precision(self.decimals)

        self.margin_label = FCLabel('%s:' % _("Margin"))
        self.margin_label.setToolTip(
            _("Margin over bounds. A positive value here\n"
              "will make the cutout of the PCB further from\n"
              "the actual PCB border")
        )
        param_grid.addWidget(self.margin_label, 6, 0)
        param_grid.addWidget(self.margin, 6, 1)

        self.gaps_label = FCLabel('<span style="color:green;"><b>%s</b></span>' % _("Gaps"))
        self.tools_box.addWidget(self.gaps_label)

        # #############################################################################################################
        # Gaps Frame
        # #############################################################################################################
        gaps_frame = FCFrame()
        self.tools_box.addWidget(gaps_frame)

        # Grid Layout
        gaps_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        gaps_frame.setLayout(gaps_grid)

        # Gapsize
        self.gapsize_label = FCLabel('%s:' % _("Size"))
        self.gapsize_label.setToolTip(
            _("The size of the bridge gaps in the cutout\n"
              "used to keep the board connected to\n"
              "the surrounding material (the one \n"
              "from which the PCB is cutout).")
        )

        self.gapsize = FCDoubleSpinner(callback=self.confirmation_message)
        self.gapsize.setRange(0.0000, 10000.0000)
        self.gapsize.set_precision(self.decimals)

        gaps_grid.addWidget(self.gapsize_label, 2, 0)
        gaps_grid.addWidget(self.gapsize, 2, 1)

        # Gap Type
        self.gaptype_label = FCLabel('%s:' % _("Type"))
        self.gaptype_label.setToolTip(
            _("The type of gap:\n"
              "- Bridge -> the cutout will be interrupted by bridges\n"
              "- Thin -> same as 'bridge' but it will be thinner by partially milling the gap\n"
              "- M-Bites -> 'Mouse Bites' - same as 'bridge' but covered with drill holes")
        )

        # self.gaptype_combo = RadioSet(
        #     [
        #         {'label': _('Bridge'), 'value': 'b'},
        #         {'label': _('Thin'), 'value': 'bt'},
        #         {'label': "M-Bites", 'value': 'mb'}
        #     ],
        #     compact=True
        # )
        self.gaptype_combo = FCComboBox2()
        self.gaptype_combo.addItems([_('Bridge'), _('Thin'), _("Mouse Bytes")])

        gaps_grid.addWidget(self.gaptype_label, 4, 0)
        gaps_grid.addWidget(self.gaptype_combo, 4, 1)

        # Thin gaps Depth
        self.thin_depth_label = FCLabel('%s:' % _("Depth"))
        self.thin_depth_label.setToolTip(
            _("The depth until the milling is done\n"
              "in order to thin the gaps.")
        )
        self.thin_depth_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.thin_depth_entry.set_precision(self.decimals)
        self.thin_depth_entry.setRange(-10000.0000, 10000.0000)
        self.thin_depth_entry.setSingleStep(0.1)

        gaps_grid.addWidget(self.thin_depth_label, 6, 0)
        gaps_grid.addWidget(self.thin_depth_entry, 6, 1)

        # Mouse Bites Tool Diameter
        self.mb_dia_label = FCLabel('%s:' % _("Tool Dia"))
        self.mb_dia_label.setToolTip(
            _("The drill hole diameter when doing mouse bites.")
        )
        self.mb_dia_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.mb_dia_entry.set_precision(self.decimals)
        self.mb_dia_entry.setRange(0, 10000.0000)

        gaps_grid.addWidget(self.mb_dia_label, 8, 0)
        gaps_grid.addWidget(self.mb_dia_entry, 8, 1)

        # Mouse Bites Holes Spacing
        self.mb_spacing_label = FCLabel('%s:' % _("Spacing"))
        self.mb_spacing_label.setToolTip(
            _("The spacing between drill holes when doing mouse bites.")
        )
        self.mb_spacing_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.mb_spacing_entry.set_precision(self.decimals)
        self.mb_spacing_entry.setRange(0, 10000.0000)

        gaps_grid.addWidget(self.mb_spacing_label, 10, 0)
        gaps_grid.addWidget(self.mb_spacing_entry, 10, 1)

        self.separator_line = QtWidgets.QFrame()
        self.separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        gaps_grid.addWidget(self.separator_line, 12, 0, 1, 2)

        # ##############################################################################################################
        # ######################################## Type of CUTOUT ######################################################
        # ##############################################################################################################
        self.cutout_type_label = FCLabel('%s:' % _("Bridge"))
        self.cutout_type_label.setToolTip(
            _("Selection of the type of cutout.")
        )

        self.cutout_type_radio = RadioSet([
            {"label": _("Automatic"), "value": "a"},
            {"label": _("Manual"), "value": "m"},
        ])

        gaps_grid.addWidget(self.cutout_type_label, 14, 0)
        gaps_grid.addWidget(self.cutout_type_radio, 14, 1)

        # Gaps
        # How gaps wil be rendered:
        # lr    - left + right
        # tb    - top + bottom
        # 4     - left + right +top + bottom
        # 2lr   - 2*left + 2*right
        # 2tb   - 2*top + 2*bottom
        # 8     - 2*left + 2*right +2*top + 2*bottom
        self.gaps_label = FCLabel('%s:' % _('Gaps'))
        self.gaps_label.setToolTip(
            _("Number of gaps used for the Automatic cutout.\n"
              "There can be maximum 8 bridges/gaps.\n"
              "The choices are:\n"
              "- None  - no gaps\n"
              "- lr    - left + right\n"
              "- tb    - top + bottom\n"
              "- 4     - left + right +top + bottom\n"
              "- 2lr   - 2*left + 2*right\n"
              "- 2tb  - 2*top + 2*bottom\n"
              "- 8     - 2*left + 2*right +2*top + 2*bottom")
        )
        # gaps_label.setMinimumWidth(60)

        self.gaps = FCComboBox()
        gaps_items = ['None', 'LR', 'TB', '4', '2LR', '2TB', '8']
        for it in gaps_items:
            self.gaps.addItem(it)
            # self.gaps.setStyleSheet('background-color: rgb(255,255,255)')
        gaps_grid.addWidget(self.gaps_label, 16, 0)
        gaps_grid.addWidget(self.gaps, 16, 1)

        # Type of generated cutout: Rectangular or Any Form
        self.cutout_shape_label = FCLabel('%s:' % _("Shape"))
        self.cutout_shape_label.setToolTip(
            _("Checked: the cutout shape is rectangular.\n"
              "Unchecked: any-form cutout shape.")
        )
        self.cutout_shape_cb = FCCheckBox('%s' % _("Any"))

        gaps_grid.addWidget(self.cutout_shape_label, 18, 0)
        gaps_grid.addWidget(self.cutout_shape_cb, 18, 1)

        # #############################################################################################################
        # Manual Gaps Frame
        # #############################################################################################################
        self.man_frame = QtWidgets.QFrame()
        self.man_frame.setContentsMargins(0, 0, 0, 0)
        gaps_grid.addWidget(self.man_frame, 20, 0, 1, 2)

        man_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        man_grid.setContentsMargins(0, 0, 0, 0)
        self.man_frame.setLayout(man_grid)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        man_grid.addWidget(separator_line, 0, 0, 1, 2)

        # Big Cursor
        self.big_cursor_label = FCLabel('%s:' % _("Big cursor"))
        self.big_cursor_label.setToolTip(
            _("Use a big cursor when adding manual gaps."))
        self.big_cursor_cb = FCCheckBox()

        man_grid.addWidget(self.big_cursor_label, 2, 0)
        man_grid.addWidget(self.big_cursor_cb, 2, 1)

        # Manual Geo Object
        self.man_object_combo = FCComboBox()
        self.man_object_combo.setModel(self.app.collection)
        self.man_object_combo.setRootModelIndex(self.app.collection.index(2, 0, QtCore.QModelIndex()))
        self.man_object_combo.is_last = True
        self.man_object_combo.obj_type = "Geometry"

        self.man_object_label = FCLabel('%s:' % _("Manual cutout Geometry"))
        self.man_object_label.setToolTip(
            _("Geometry object used to create the manual cutout.")
        )
        # self.man_object_label.setMinimumWidth(60)

        man_grid.addWidget(self.man_object_label, 4, 0, 1, 2)
        man_grid.addWidget(self.man_object_combo, 6, 0, 1, 2)

        # #############################################################################################################
        # Buttons
        # #############################################################################################################

        man_hlay = QtWidgets.QHBoxLayout()
        self.tools_box.addLayout(man_hlay)

        # Generate a surrounding Geometry object Button
        self.man_geo_creation_btn = FCButton(_("Manual Geometry"))
        self.man_geo_creation_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/rectangle32.png'))
        self.man_geo_creation_btn.setToolTip(
            _("Generate a Geometry to be used as cutout.")
        )
        # self.man_geo_creation_btn.setStyleSheet("""
        #                         QPushButton
        #                         {
        #                             font-weight: bold;
        #                         }
        #                         """)

        # Manual Add of Gaps Button
        self.man_gaps_creation_btn = QtWidgets.QToolButton()
        self.man_gaps_creation_btn.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.man_gaps_creation_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/plus32.png'))
        self.man_gaps_creation_btn.setText(_("Gaps"))
        self.man_gaps_creation_btn.setToolTip(
            _("Add new gaps on the selected Geometry object\n"
              "by clicking mouse left button on the Geometry outline.")
        )
        man_hlay.addWidget(self.man_geo_creation_btn)
        man_hlay.addWidget(self.man_gaps_creation_btn)

        # Generate Geometry Button
        self.generate_cutout_btn = FCButton(_("Generate Geometry"))
        self.generate_cutout_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/irregular32.png'))
        self.generate_cutout_btn.setToolTip(
            _("Generate the cutout geometry.")
        )
        self.generate_cutout_btn.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        self.tools_box.addWidget(self.generate_cutout_btn)

        # self.tool_param_separator_line = QtWidgets.QFrame()
        # self.tool_param_separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        # self.tool_param_separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        # obj_grid.addWidget(self.tool_param_separator_line, 60, 0, 1, 2)

        # obj_grid.addWidget(FCLabel(""), 62, 0, 1, 2)

        # Cut by Drilling Title
        self.title_drillcut_label = FCLabel('<span style="color:red;"><b>%s</b></span>' % _('Cut by Drilling'))
        self.title_drillcut_label.setToolTip(_("Create a series of drill holes following a geometry line."))
        self.tools_box.addWidget(self.title_drillcut_label)

        # #############################################################################################################
        # Cut by Drilling Frame
        # #############################################################################################################
        self.drill_cut_frame = FCFrame()
        self.tools_box.addWidget(self.drill_cut_frame)

        # Grid Layout
        drill_cut_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        self.drill_cut_frame.setLayout(drill_cut_grid)

        # Drilling Geo Object Label
        self.drillcut_object_lbl = FCLabel('%s:' % _("Geometry"))
        self.drillcut_object_lbl.setToolTip(
            _("Geometry object used to create the manual cutout.")
        )

        drill_cut_grid.addWidget(self.drillcut_object_lbl, 0, 0, 1, 2)

        # Drilling Geo Object
        self.drillcut_object_combo = FCComboBox()
        self.drillcut_object_combo.setModel(self.app.collection)
        self.drillcut_object_combo.setRootModelIndex(self.app.collection.index(2, 0, QtCore.QModelIndex()))
        self.drillcut_object_combo.is_last = False
        self.drillcut_object_combo.obj_type = "Geometry"

        drill_cut_grid.addWidget(self.drillcut_object_combo, 2, 0, 1, 2)

        # Drill Tool Diameter
        self.drill_dia_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.drill_dia_entry.set_precision(self.decimals)
        self.drill_dia_entry.set_range(0.0000, 10000.0000)

        self.drill_dia_label = FCLabel('%s:' % _("Drill Dia"))
        self.drill_dia_label.setToolTip(
            _("Diameter of the tool used to cutout\n"
              "the PCB by drilling.")
        )
        drill_cut_grid.addWidget(self.drill_dia_label, 4, 0)
        drill_cut_grid.addWidget(self.drill_dia_entry, 4, 1)

        # Drill Tool Pitch
        self.drill_pitch_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.drill_pitch_entry.set_precision(self.decimals)
        self.drill_pitch_entry.set_range(0.0000, 10000.0000)

        self.drill_pitch_label = FCLabel('%s:' % _("Pitch"))
        self.drill_pitch_label.setToolTip(
            _("Distance between the center of\n"
              "two neighboring drill holes.")
        )
        drill_cut_grid.addWidget(self.drill_pitch_label, 6, 0)
        drill_cut_grid.addWidget(self.drill_pitch_entry, 6, 1)

        # Drill Tool Margin
        self.drill_margin_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.drill_margin_entry.set_precision(self.decimals)
        self.drill_margin_entry.set_range(0.0000, 10000.0000)

        self.drill_margin_label = FCLabel('%s:' % _("Margin"))
        self.drill_margin_label.setToolTip(
            _("Margin over bounds. A positive value here\n"
              "will make the cutout of the PCB further from\n"
              "the actual PCB border")
        )
        drill_cut_grid.addWidget(self.drill_margin_label, 8, 0)
        drill_cut_grid.addWidget(self.drill_margin_entry, 8, 1)

        FCGridLayout.set_common_column_size([obj_grid, tool_grid, param_grid, man_grid, drill_cut_grid, gaps_grid], 0)

        # Drill Cut Button
        self.drillcut_btn = FCButton(_("Cut by Drilling"))
        self.drillcut_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/drill16.png'))
        self.drillcut_btn.setToolTip(
            _("Create a series of drill holes following a geometry line.")
        )
        self.drillcut_btn.setStyleSheet("""
                                        QPushButton
                                        {
                                            font-weight: bold;
                                        }
                                        """)
        self.tools_box.addWidget(self.drillcut_btn)

        self.layout.addStretch()

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

        self.gaptype_combo.currentIndexChanged.connect(self.on_gap_type_radio)

        # ############################ FINSIHED GUI ###################################
        # #############################################################################

    def on_gap_type_radio(self, index):
        if index == 0:    # Normal gap
            self.thin_depth_label.hide()
            self.thin_depth_entry.hide()
            self.mb_dia_label.hide()
            self.mb_dia_entry.hide()
            self.mb_spacing_label.hide()
            self.mb_spacing_entry.hide()
        elif index == 1:  # "Thin gaps"
            self.thin_depth_label.show()
            self.thin_depth_entry.show()
            self.mb_dia_label.hide()
            self.mb_dia_entry.hide()
            self.mb_spacing_label.hide()
            self.mb_spacing_entry.hide()
        elif index == 2:  # "Mouse Bytes"
            self.thin_depth_label.hide()
            self.thin_depth_entry.hide()
            self.mb_dia_label.show()
            self.mb_dia_entry.show()
            self.mb_spacing_label.show()
            self.mb_spacing_entry.show()

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
