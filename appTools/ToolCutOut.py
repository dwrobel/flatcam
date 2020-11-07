# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtGui, QtCore
from appTool import AppTool
from appGUI.GUIElements import FCDoubleSpinner, FCCheckBox, RadioSet, FCComboBox, OptionalInputSection, FCButton, \
    FCLabel

from shapely.geometry import box, MultiPolygon, Polygon, LineString, LinearRing, MultiLineString
from shapely.ops import unary_union, linemerge
import shapely.affinity as affinity

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

settings = QtCore.QSettings("Open Source", "FlatCAM")
if settings.contains("machinist"):
    machinist_setting = settings.value('machinist', type=int)
else:
    machinist_setting = 0


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
        self.toolName = self.ui.toolName

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

        # Signals
        self.ui.ff_cutout_object_btn.clicked.connect(self.on_freeform_cutout)
        self.ui.rect_cutout_object_btn.clicked.connect(self.on_rectangular_cutout)

        # adding tools
        self.ui.add_newtool_button.clicked.connect(lambda: self.on_tool_add())
        self.ui.addtool_from_db_btn.clicked.connect(self.on_tool_add_from_db_clicked)

        self.ui.type_obj_radio.activated_custom.connect(self.on_type_obj_changed)
        self.ui.man_geo_creation_btn.clicked.connect(self.on_manual_geo)
        self.ui.man_gaps_creation_btn.clicked.connect(self.on_manual_gap_click)
        self.ui.reset_button.clicked.connect(self.set_tool_ui)

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

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolCutOut()")

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

        self.app.ui.notebook.setTabText(2, _("Cutout Tool"))

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Alt+X', **kwargs)

    def set_tool_ui(self):
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

        self.ui.dia.set_value(float(self.app.defaults["tools_cutout_tooldia"]))

        self.default_data.update({
            "plot": True,

            "cutz": float(self.app.defaults["geometry_cutz"]),
            "multidepth": self.app.defaults["geometry_multidepth"],
            "depthperpass": float(self.app.defaults["geometry_depthperpass"]),

            "vtipdia": float(self.app.defaults["geometry_vtipdia"]),
            "vtipangle": float(self.app.defaults["geometry_vtipangle"]),
            "travelz": float(self.app.defaults["geometry_travelz"]),
            "feedrate": float(self.app.defaults["geometry_feedrate"]),
            "feedrate_z": float(self.app.defaults["geometry_feedrate_z"]),
            "feedrate_rapid": float(self.app.defaults["geometry_feedrate_rapid"]),
            "spindlespeed": self.app.defaults["geometry_spindlespeed"],
            "dwell": self.app.defaults["geometry_dwell"],
            "dwelltime": float(self.app.defaults["geometry_dwelltime"]),
            "spindledir": self.app.defaults["geometry_spindledir"],
            "ppname_g": self.app.defaults["geometry_ppname_g"],
            "extracut": self.app.defaults["geometry_extracut"],
            "extracut_length": float(self.app.defaults["geometry_extracut_length"]),
            "toolchange": self.app.defaults["geometry_toolchange"],
            "toolchangexy": self.app.defaults["geometry_toolchangexy"],
            "toolchangez": float(self.app.defaults["geometry_toolchangez"]),
            "startz": self.app.defaults["geometry_startz"],
            "endz": float(self.app.defaults["geometry_endz"]),
            "endxy": self.app.defaults["geometry_endxy"],
            "area_exclusion": self.app.defaults["geometry_area_exclusion"],
            "area_shape": self.app.defaults["geometry_area_shape"],
            "area_strategy": self.app.defaults["geometry_area_strategy"],
            "area_overz": float(self.app.defaults["geometry_area_overz"]),
            "optimization_type": self.app.defaults["geometry_optimization_type"],

            # Cutout
            "tools_cutout_tooldia": self.app.defaults["tools_cutout_tooldia"],
            "tools_cutout_kind": self.app.defaults["tools_cutout_kind"],
            "tools_cutout_margin": float(self.app.defaults["tools_cutout_margin"]),
            "tools_cutout_z": float(self.app.defaults["tools_cutout_z"]),
            "tools_cutout_depthperpass": float(self.app.defaults["tools_cutout_depthperpass"]),
            "tools_cutout_mdepth": self.app.defaults["tools_cutout_mdepth"],
            "tools_cutout_gapsize": float(self.app.defaults["tools_cutout_gapsize"]),
            "tools_cutout_gaps_ff": self.app.defaults["tools_cutout_gaps_ff"],
            "tools_cutout_convexshape": self.app.defaults["tools_cutout_convexshape"],

            "tools_cutout_big_cursor": self.app.defaults["tools_cutout_big_cursor"],
            "tools_cutout_gap_type": self.app.defaults["tools_cutout_gap_type"],
            "tools_cutout_gap_depth": float(self.app.defaults["tools_cutout_gap_depth"]),
            "tools_cutout_mb_dia": float(self.app.defaults["tools_cutout_mb_dia"]),
            "tools_cutout_mb_spacing": float(self.app.defaults["tools_cutout_mb_spacing"]),

        })
        tool_dia = float(self.app.defaults["tools_cutout_tooldia"])
        self.on_tool_add(custom_dia=tool_dia)

    def update_ui(self, tool_dict):
        self.ui.obj_kind_combo.set_value(self.default_data["tools_cutout_kind"])
        self.ui.big_cursor_cb.set_value(self.default_data['tools_cutout_big_cursor'])

        # Entries that may be updated from database
        self.ui.margin.set_value(float(tool_dict["tools_cutout_margin"]))
        self.ui.gapsize.set_value(float(tool_dict["tools_cutout_gapsize"]))
        self.ui.gaptype_radio.set_value(tool_dict["tools_cutout_gap_type"])
        self.ui.thin_depth_entry.set_value(float(tool_dict["tools_cutout_gap_depth"]))
        self.ui.mb_dia_entry.set_value(float(tool_dict["tools_cutout_mb_dia"]))
        self.ui.mb_spacing_entry.set_value(float(tool_dict["tools_cutout_mb_spacing"]))
        self.ui.convex_box_cb.set_value(tool_dict['tools_cutout_convexshape'])
        self.ui.gaps.set_value(tool_dict["tools_cutout_gaps_ff"])

        self.ui.cutz_entry.set_value(float(tool_dict["tools_cutout_z"]))
        self.ui.mpass_cb.set_value(float(tool_dict["tools_cutout_mdepth"]))
        self.ui.maxdepth_entry.set_value(float(tool_dict["tools_cutout_depthperpass"]))

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

            # we need only tool marked for Cutout Tool
            if db_tool_val['data']['tool_target'] != _('Cutout'):
                continue

            # if we find a tool with the same diameter in the Tools DB just update it's data
            if truncated_tooldia == db_tooldia:
                tool_found += 1
                for d in db_tool_val['data']:
                    if d.find('tools_cutout') == 0:
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
                    if d.find('tools_cutout') == 0:
                        new_tools_dict[d] = db_tool_val['data'][d]
                    elif d.find('tools_') == 0:
                        # don't need data for other App Tools; this tests after 'tools_drill_'
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

        # FIXME when the Geometry UI milling functionality will be transferred in the Milling Tool this needs changes
        new_tools_dict["tools_cutout_z"] = deepcopy(new_tools_dict["cutz"])
        new_tools_dict["tools_cutout_mdepth"] = deepcopy(new_tools_dict["multidepth"])
        new_tools_dict["tools_cutout_depthperpass"] = deepcopy(new_tools_dict["depthperpass"])

        new_tdia = deepcopy(updated_tooldia) if updated_tooldia is not None else deepcopy(truncated_tooldia)
        self.cut_tool_dict.update({
            'tooldia': new_tdia,
            'offset': deepcopy(offset),
            'offset_value': deepcopy(offset_val),
            'type': deepcopy(typ),
            'tool_type': deepcopy(tool_type),
            'data': deepcopy(new_tools_dict),
            'solid_geometry': []
        })

        self.update_ui(new_tools_dict)

        self.blockSignals(False)
        self.app.inform.emit('[success] %s' % _("Updated tool from Tools Database."))

    def on_tool_default_add(self, dia=None, muted=None):

        dia = dia if dia else str(self.app.defaults["tools_cutout_tooldia"])
        self.default_data.update({
            "plot": True,

            "cutz": float(self.app.defaults["geometry_cutz"]),
            "multidepth": self.app.defaults["geometry_multidepth"],
            "depthperpass": float(self.app.defaults["geometry_depthperpass"]),

            "vtipdia": float(self.app.defaults["geometry_vtipdia"]),
            "vtipangle": float(self.app.defaults["geometry_vtipangle"]),
            "travelz": float(self.app.defaults["geometry_travelz"]),
            "feedrate": float(self.app.defaults["geometry_feedrate"]),
            "feedrate_z": float(self.app.defaults["geometry_feedrate_z"]),
            "feedrate_rapid": float(self.app.defaults["geometry_feedrate_rapid"]),
            "spindlespeed": self.app.defaults["geometry_spindlespeed"],
            "dwell": self.app.defaults["geometry_dwell"],
            "dwelltime": float(self.app.defaults["geometry_dwelltime"]),
            "spindledir": self.app.defaults["geometry_spindledir"],
            "ppname_g": self.app.defaults["geometry_ppname_g"],
            "extracut": self.app.defaults["geometry_extracut"],
            "extracut_length": float(self.app.defaults["geometry_extracut_length"]),
            "toolchange": self.app.defaults["geometry_toolchange"],
            "toolchangexy": self.app.defaults["geometry_toolchangexy"],
            "toolchangez": float(self.app.defaults["geometry_toolchangez"]),
            "startz": self.app.defaults["geometry_startz"],
            "endz": float(self.app.defaults["geometry_endz"]),
            "endxy": self.app.defaults["geometry_endxy"],
            "area_exclusion": self.app.defaults["geometry_area_exclusion"],
            "area_shape": self.app.defaults["geometry_area_shape"],
            "area_strategy": self.app.defaults["geometry_area_strategy"],
            "area_overz": float(self.app.defaults["geometry_area_overz"]),
            "optimization_type": self.app.defaults["geometry_optimization_type"],

            # Cutout
            "tools_cutout_tooldia": self.app.defaults["tools_cutout_tooldia"],
            "tools_cutout_kind": self.app.defaults["tools_cutout_kind"],
            "tools_cutout_margin": float(self.app.defaults["tools_cutout_margin"]),
            "tools_cutout_z": float(self.app.defaults["tools_cutout_z"]),
            "tools_cutout_depthperpass": float(self.app.defaults["tools_cutout_depthperpass"]),
            "tools_cutout_mdepth": self.app.defaults["tools_cutout_mdepth"],
            "tools_cutout_gapsize": float(self.app.defaults["tools_cutout_gapsize"]),
            "tools_cutout_gaps_ff": self.app.defaults["tools_cutout_gaps_ff"],
            "tools_cutout_convexshape": self.app.defaults["tools_cutout_convexshape"],

            "tools_cutout_big_cursor": self.app.defaults["tools_cutout_big_cursor"],
            "tools_cutout_gap_type": self.app.defaults["tools_cutout_gap_type"],
            "tools_cutout_gap_depth": float(self.app.defaults["tools_cutout_gap_depth"]),
            "tools_cutout_mb_dia": float(self.app.defaults["tools_cutout_mb_dia"]),
            "tools_cutout_mb_spacing": float(self.app.defaults["tools_cutout_mb_spacing"]),

        })

        self.cut_tool_dict.update({
            'tooldia': dia,
            'offset': 'Path',
            'offset_value': 0.0,
            'type': 'Rough',
            'tool_type': 'C1',
            'data': deepcopy(self.default_data),
            'solid_geometry': []
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

        # FIXME when the Geometry UI milling functionality will be transferred in the Milling Tool this needs changes
        tool_from_db['data']["tools_cutout_tooldia"] = deepcopy(tool["tooldia"])
        tool_from_db['data']["tools_cutout_z"] = deepcopy(tool_from_db['data']["cutz"])
        tool_from_db['data']["tools_cutout_mdepth"] = deepcopy(tool_from_db['data']["multidepth"])
        tool_from_db['data']["tools_cutout_depthperpass"] = deepcopy(tool_from_db['data']["depthperpass"])

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
                'tooldia': truncated_tooldia,
                'offset': tool['offset'],
                'offset_value': tool['offset_value'],
                'type': tool['type'],
                'tool_type': tool['tool_type'],
                'data': deepcopy(tool['data']),
                'solid_geometry': []
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

    def on_freeform_cutout(self):
        log.debug("Cutout.on_freeform_cutout() was launched ...")

        name = self.ui.obj_combo.currentText()

        # Get source object.
        try:
            cutout_obj = self.app.collection.get_by_name(str(name))
        except Exception as e:
            log.debug("CutOut.on_freeform_cutout() --> %s" % str(e))
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

        # if cutout_obj.multigeo is True:
        #     self.app.inform.emit('[ERROR] %s' % _("Cutout operation cannot be done on a multi-geo Geometry.\n"
        #                                           "Optionally, this Multi-geo Geometry can be converted to "
        #                                           "Single-geo Geometry,\n"
        #                                           "and after that perform Cutout."))
        #     return

        def cutout_handler(geom, gapsize):
            proc_geometry = []
            rest_geometry = []
            r_temp_geo = []
            initial_geo = deepcopy(geom)

            # Get min and max data for each object as we just cut rectangles across X or Y
            xxmin, yymin, xxmax, yymax = CutOut.recursive_bounds(geom)

            px = 0.5 * (xxmin + xxmax) + margin
            py = 0.5 * (yymin + yymax) + margin
            lenx = (xxmax - xxmin) + (margin * 2)
            leny = (yymax - yymin) + (margin * 2)

            if gaps == 'None':
                pass
            else:
                if gaps == '8' or gaps == '2LR':
                    points = (
                        xxmin - gapsize,  # botleft_x
                        py - gapsize + leny / 4,  # botleft_y
                        xxmax + gapsize,  # topright_x
                        py + gapsize + leny / 4  # topright_y
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
                for g in geom:
                    if g and not g.is_empty:
                        proc_geometry.append(g)
            except TypeError:
                if geom and not geom.is_empty:
                    proc_geometry.append(geom)

            r_temp_geo = CutOut.flatten(r_temp_geo)
            for g in r_temp_geo:
                if g and not g.is_empty:
                    rest_geometry.append(g)

            return proc_geometry, rest_geometry

        with self.app.proc_container.new("Generating Cutout ..."):
            outname = cutout_obj.options["name"] + "_cutout"
            self.app.collection.promise(outname)

            has_mouse_bites = True if self.ui.gaptype_radio.get_value() == 'mb' else False

            outname_exc = cutout_obj.options["name"] + "_mouse_bites"
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
                gap_type = self.ui.gaptype_radio.get_value()
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
                        log.debug("CutOut.on_freeform_cutout().geo_init() --> %s" % str(err))
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
                        else:
                            geo_buf = object_geo.buffer(margin - abs(dia / 2))
                        geo = geo_buf.exterior
                    else:
                        if isinstance(object_geo, MultiPolygon):
                            x0, y0, x1, y1 = object_geo.bounds
                            object_geo = box(x0, y0, x1, y1)
                        geo_buf = object_geo.buffer(0)
                        geo = geo_buf.exterior

                    solid_geo, rest_geo = cutout_handler(geom=geo, gapsize=gapsize)
                    if gap_type == 'bt' and thin_entry != 0:
                        gaps_solid_geo = rest_geo
                else:
                    try:
                        __ = iter(object_geo)
                    except TypeError:
                        object_geo = [object_geo]

                    for geom_struct in object_geo:
                        if cutout_obj.kind == 'gerber':
                            if margin >= 0:
                                geom_struct = (geom_struct.buffer(margin + abs(dia / 2))).exterior
                            else:
                                geom_struct_buff = geom_struct.buffer(-margin + abs(dia / 2))
                                geom_struct = geom_struct_buff.interiors

                        c_geo, r_geo = cutout_handler(geom=geom_struct, gapsize=gapsize)
                        solid_geo += c_geo
                        if gap_type == 'bt' and thin_entry != 0:
                            gaps_solid_geo += r_geo

                if not solid_geo:
                    self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed."))
                    return "fail"

                solid_geo = linemerge(solid_geo)

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

                        __, rest_geo = cutout_handler(geom=mb_geo, gapsize=gapsize)
                        mouse_bites_geo = rest_geo
                    else:
                        try:
                            __ = iter(mb_object_geo)
                        except TypeError:
                            mb_object_geo = [mb_object_geo]

                        for mb_geom_struct in mb_object_geo:
                            if cutout_obj.kind == 'gerber':
                                if margin >= 0:
                                    mb_geom_struct = mb_geom_struct.buffer(margin + mb_buff_val)
                                    mb_geom_struct = mb_geom_struct.exterior
                                else:
                                    mb_geom_struct = mb_geom_struct.buffer(-margin + mb_buff_val)
                                    mb_geom_struct = mb_geom_struct.interiors

                            __, mb_r_geo = cutout_handler(geom=mb_geom_struct, gapsize=gapsize)
                            mouse_bites_geo += mb_r_geo

                    # list of Shapely Points to mark the drill points centers
                    holes = []
                    for line in mouse_bites_geo:
                        calc_len = 0
                        while calc_len < line.length:
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

                    geo_obj.options['cnctooldia'] = str(dia)
                    geo_obj.options['cutz'] = self.ui.cutz_entry.get_value()
                    geo_obj.options['multidepth'] = self.ui.mpass_cb.get_value()
                    geo_obj.options['depthperpass'] = self.ui.maxdepth_entry.get_value()

                    geo_obj.tools[1] = deepcopy(self.cut_tool_dict)
                    geo_obj.tools[1]['tooldia'] = str(dia)
                    geo_obj.tools[1]['solid_geometry'] = geo_obj.solid_geometry

                    geo_obj.tools[1]['data']['name'] = outname
                    geo_obj.tools[1]['data']['cutz'] = self.ui.cutz_entry.get_value()
                    geo_obj.tools[1]['data']['multidepth'] = self.ui.mpass_cb.get_value()
                    geo_obj.tools[1]['data']['depthperpass'] = self.ui.maxdepth_entry.get_value()

                    if not gaps_solid_geo:
                        pass
                    else:
                        geo_obj.tools[9999] = deepcopy(self.cut_tool_dict)
                        geo_obj.tools[9999]['tooldia'] = str(dia)
                        geo_obj.tools[9999]['solid_geometry'] = gaps_solid_geo

                        geo_obj.tools[9999]['data']['name'] = outname
                        geo_obj.tools[9999]['data']['cutz'] = self.ui.thin_depth_entry.get_value()
                        geo_obj.tools[9999]['data']['multidepth'] = self.ui.mpass_cb.get_value()
                        geo_obj.tools[9999]['data']['depthperpass'] = self.ui.maxdepth_entry.get_value()
                        # plot this tool in a different color
                        geo_obj.tools[9999]['data']['override_color'] = "#29a3a3fa"

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
                    if self.ui.gaptype_radio.get_value() == 'mb':
                        ret = app_obj.app_obj.new_object('excellon', outname_exc, excellon_init)
                        if ret == 'fail':
                            app_obj.inform.emit('[ERROR_NOTCL] %s' % _("Mouse bites failed."))

                    ret = app_obj.app_obj.new_object('geometry', outname, geo_init)
                    if ret == 'fail':
                        app_obj.inform.emit('[ERROR_NOTCL] %s' % _("Failed."))
                        return

                    # cutout_obj.plot(plot_tool=1)
                    app_obj.inform.emit('[success] %s' % _("Any-form Cutout operation finished."))
                    # self.app.ui.notebook.setCurrentWidget(self.app.ui.project_tab)
                    app_obj.should_we_save = True
                except Exception as ee:
                    log.debug(str(ee))

            self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})

    def on_rectangular_cutout(self):
        log.debug("Cutout.on_rectangular_cutout() was launched ...")

        name = self.ui.obj_combo.currentText()

        # Get source object.
        try:
            cutout_obj = self.app.collection.get_by_name(str(name))
        except Exception as e:
            log.debug("CutOut.on_rectangular_cutout() --> %s" % str(e))
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), name))
            return "Could not retrieve object: %s" % name

        if cutout_obj is None:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Object not found"), str(name)))

        dia = float(self.ui.dia.get_value())
        if 0 in {dia}:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
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
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("Number of gaps value is missing. Add it and retry."))
            return

        if gaps not in ['None', 'LR', 'TB', '2LR', '2TB', '4', '8']:
            msg = '[WARNING_NOTCL] %s' % _("Gaps value can be only one of: 'None', 'lr', 'tb', '2lr', '2tb', 4 or 8.\n"
                                           "Fill in a correct value and retry.")
            self.app.inform.emit(msg)
            return

        # if cutout_obj.multigeo is True:
        #     self.app.inform.emit('[ERROR] %s' % _("Cutout operation cannot be done on a multi-geo Geometry.\n"
        #                                           "Optionally, this Multi-geo Geometry can be converted to "
        #                                           "Single-geo Geometry,\n"
        #                                           "and after that perform Cutout."))
        #     return

        def cutout_rect_handler(geom, gapsize, xmin, ymin, xmax, ymax):
            proc_geometry = []

            px = 0.5 * (xmin + xmax) + margin
            py = 0.5 * (ymin + ymax) + margin
            lenx = (xmax - xmin) + (margin * 2)
            leny = (ymax - ymin) + (margin * 2)

            if gaps == 'None':
                pass
            else:
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
                for g in geom:
                    proc_geometry.append(g)
            except TypeError:
                proc_geometry.append(geom)
            return proc_geometry

        with self.app.proc_container.new("Generating Cutout ..."):
            outname = cutout_obj.options["name"] + "_cutout"
            self.app.collection.promise(outname)

            has_mouse_bites = True if self.ui.gaptype_radio.get_value() == 'mb' else False

            outname_exc = cutout_obj.options["name"] + "_mouse_bites"
            if has_mouse_bites is True:
                self.app.collection.promise(outname_exc)

            def job_thread(app_obj):
                solid_geo = []
                gaps_solid_geo = []
                mouse_bites_geo = []

                gapsize = self.ui.gapsize.get_value()
                gapsize = gapsize / 2 + (dia / 2)
                mb_dia = self.ui.mb_dia_entry.get_value()
                mb_buff_val = mb_dia / 2.0
                mb_spacing = self.ui.mb_spacing_entry.get_value()
                gap_type = self.ui.gaptype_radio.get_value()
                thin_entry = self.ui.thin_depth_entry.get_value()

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

                    # if Gerber create a buffer at a distance
                    # if Geometry then cut through the geometry
                    if cutout_obj.kind == 'gerber':
                        if margin >= 0:
                            geo = geo.buffer(margin + abs(dia / 2))
                        else:
                            geo = geo.buffer(margin - abs(dia / 2))

                    solid_geo = cutout_rect_handler(geo, gapsize, xmin, ymin, xmax, ymax)

                    if gap_type == 'bt' and thin_entry != 0:
                        gaps_solid_geo = self.subtract_geo(geo, deepcopy(solid_geo))
                else:
                    if cutout_obj.kind == 'geometry':
                        try:
                            __ = iter(object_geo)
                        except TypeError:
                            object_geo = [object_geo]

                        for geom_struct in object_geo:
                            geom_struct = unary_union(geom_struct)
                            xmin, ymin, xmax, ymax = geom_struct.bounds
                            geom_struct = box(xmin, ymin, xmax, ymax)

                            c_geo = cutout_rect_handler(geom_struct, gapsize, xmin, ymin, xmax, ymax)
                            solid_geo += c_geo
                            if gap_type == 'bt' and thin_entry != 0:
                                try:
                                    gaps_solid_geo += self.subtract_geo(geom_struct, c_geo)
                                except TypeError:
                                    gaps_solid_geo.append(self.subtract_geo(geom_struct, c_geo))
                    elif cutout_obj.kind == 'gerber' and margin >= 0:
                        try:
                            __ = iter(object_geo)
                        except TypeError:
                            object_geo = [object_geo]

                        for geom_struct in object_geo:
                            geom_struct = unary_union(geom_struct)
                            xmin, ymin, xmax, ymax = geom_struct.bounds
                            geom_struct = box(xmin, ymin, xmax, ymax)

                            geom_struct = geom_struct.buffer(margin + abs(dia / 2))

                            c_geo = cutout_rect_handler(geom_struct, gapsize, xmin, ymin, xmax, ymax)
                            solid_geo += c_geo
                            if gap_type == 'bt' and thin_entry != 0:
                                try:
                                    gaps_solid_geo += self.subtract_geo(geom_struct, c_geo)
                                except TypeError:
                                    gaps_solid_geo.append(self.subtract_geo(geom_struct, c_geo))
                    elif cutout_obj.kind == 'gerber' and margin < 0:
                        app_obj.inform.emit(
                            '[WARNING_NOTCL] %s' % _("Rectangular cutout with negative margin is not possible."))
                        return "fail"

                if not solid_geo:
                    app_obj.inform.emit('[ERROR_NOTCL] %s' % _("Failed."))
                    return "fail"

                solid_geo = linemerge(solid_geo)

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

                        mb_solid_geo = cutout_rect_handler(mb_geo, gapsize, xmin, ymin, xmax, ymax)

                        mouse_bites_geo = self.subtract_geo(mb_geo, mb_solid_geo)
                    else:
                        if cutout_obj.kind == 'geometry':
                            try:
                                __ = iter(mb_object_geo)
                            except TypeError:
                                mb_object_geo = [mb_object_geo]

                            for mb_geom_struct in mb_object_geo:
                                mb_geom_struct = unary_union(mb_geom_struct)
                                xmin, ymin, xmax, ymax = mb_geom_struct.bounds
                                mb_geom_struct = box(xmin, ymin, xmax, ymax)

                                c_geo = cutout_rect_handler(mb_geom_struct, gapsize, xmin, ymin, xmax, ymax)
                                solid_geo += c_geo

                                try:
                                    mouse_bites_geo += self.subtract_geo(mb_geom_struct, c_geo)
                                except TypeError:
                                    mouse_bites_geo.append(self.subtract_geo(mb_geom_struct, c_geo))
                        elif cutout_obj.kind == 'gerber' and margin >= 0:
                            try:
                                __ = iter(mb_object_geo)
                            except TypeError:
                                mb_object_geo = [mb_object_geo]

                            for mb_geom_struct in mb_object_geo:
                                mb_geom_struct = unary_union(mb_geom_struct)
                                xmin, ymin, xmax, ymax = mb_geom_struct.bounds
                                mb_geom_struct = box(xmin, ymin, xmax, ymax)
                                mb_geom_struct = mb_geom_struct.buffer(margin + mb_buff_val)

                                c_geo = cutout_rect_handler(mb_geom_struct, gapsize, xmin, ymin, xmax, ymax)
                                solid_geo += c_geo

                                try:
                                    mouse_bites_geo += self.subtract_geo(mb_geom_struct, c_geo)
                                except TypeError:
                                    mouse_bites_geo.append(self.subtract_geo(mb_geom_struct, c_geo))
                        elif cutout_obj.kind == 'gerber' and margin < 0:
                            msg = '[WARNING_NOTCL] %s' % \
                                  _("Rectangular cutout with negative margin is not possible.")
                            app_obj.inform.emit(msg)
                            return "fail"

                    # list of Shapely Points to mark the drill points centers
                    holes = []
                    for line in mouse_bites_geo:
                        calc_len = 0
                        while calc_len < line.length:
                            holes.append(line.interpolate(calc_len))
                            calc_len += mb_dia + mb_spacing

                def geo_init(geo_obj, application_obj):
                    geo_obj.multigeo = True
                    geo_obj.solid_geometry = deepcopy(solid_geo)

                    geo_obj.options['xmin'] = xmin
                    geo_obj.options['ymin'] = ymin
                    geo_obj.options['xmax'] = xmax
                    geo_obj.options['ymax'] = ymax

                    geo_obj.options['cnctooldia'] = str(dia)
                    geo_obj.options['cutz'] = self.ui.cutz_entry.get_value()
                    geo_obj.options['multidepth'] = self.ui.mpass_cb.get_value()
                    geo_obj.options['depthperpass'] = self.ui.maxdepth_entry.get_value()

                    geo_obj.tools[1] = deepcopy(self.cut_tool_dict)
                    geo_obj.tools[1]['tooldia'] = str(dia)
                    geo_obj.tools[1]['solid_geometry'] = geo_obj.solid_geometry

                    geo_obj.tools[1]['data']['name'] = outname
                    geo_obj.tools[1]['data']['cutz'] = self.ui.cutz_entry.get_value()
                    geo_obj.tools[1]['data']['multidepth'] = self.ui.mpass_cb.get_value()
                    geo_obj.tools[1]['data']['depthperpass'] = self.ui.maxdepth_entry.get_value()

                    if not gaps_solid_geo:
                        pass
                    else:
                        geo_obj.tools[9999] = deepcopy(self.cut_tool_dict)
                        geo_obj.tools[9999]['tooldia'] = str(dia)
                        geo_obj.tools[9999]['solid_geometry'] = gaps_solid_geo

                        geo_obj.tools[9999]['data']['name'] = outname
                        geo_obj.tools[9999]['data']['cutz'] = self.ui.thin_depth_entry.get_value()
                        geo_obj.tools[9999]['data']['multidepth'] = self.ui.mpass_cb.get_value()
                        geo_obj.tools[9999]['data']['depthperpass'] = self.ui.maxdepth_entry.get_value()
                        geo_obj.tools[9999]['data']['override_color'] = "#29a3a3fa"

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
                    if self.ui.gaptype_radio.get_value() == 'mb':
                        ret = app_obj.app_obj.new_object('excellon', outname_exc, excellon_init)
                        if ret == 'fail':
                            app_obj.inform.emit('[ERROR_NOTCL] %s' % _("Mouse bites failed."))

                    ret = app_obj.app_obj.new_object('geometry', outname, geo_init)
                    if ret == 'fail':
                        app_obj.inform.emit('[ERROR_NOTCL] %s' % _("Failed."))
                        return

                    # cutout_obj.plot(plot_tool=1)
                    app_obj.inform.emit('[success] %s' % _("Rectangular CutOut operation finished."))
                    # self.app.ui.notebook.setCurrentWidget(self.app.ui.project_tab)
                    app_obj.should_we_save = True
                except Exception as ee:
                    log.debug(str(ee))

            self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})

    def on_manual_gap_click(self):
        name = self.ui.man_object_combo.currentText()

        # Get source object.
        try:
            self.man_cutout_obj = self.app.collection.get_by_name(str(name))
        except Exception as e:
            log.debug("CutOut.on_manual_cutout() --> %s" % str(e))
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

        if self.ui.gaptype_radio.get_value() == 'mb':
            mb_dia = self.ui.mb_dia_entry.get_value()
            b_dia = (self.cutting_dia / 2.0) - (mb_dia / 2.0)
            self.mb_manual_solid_geo = self.flatten(unary_union(self.manual_solid_geo).buffer(b_dia).interiors)

        self.cutting_gapsize = self.ui.gapsize.get_value()

        name = self.ui.man_object_combo.currentText()
        # Get Geometry source object to be used as target for Manual adding Gaps
        try:
            self.man_cutout_obj = self.app.collection.get_by_name(str(name))
        except Exception as e:
            log.debug("CutOut.on_manual_cutout() --> %s" % str(e))
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), name))
            return

        if self.app.is_legacy is False:
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

    def on_manual_cutout(self, click_pos):

        if self.man_cutout_obj is None:
            msg = '[ERROR_NOTCL] %s: %s' % (_("Geometry object for manual cutout not found"), self.man_cutout_obj)
            self.app.inform.emit(msg)
            return

        # use the snapped position as reference
        snapped_pos = self.app.geo_editor.snap(click_pos[0], click_pos[1])

        cut_poly = self.cutting_geo(pos=(snapped_pos[0], snapped_pos[1]))

        gap_type = self.ui.gaptype_radio.get_value()
        gaps_solid_geo = None
        if gap_type == 'bt' and self.ui.thin_depth_entry.get_value() != 0:
            gaps_solid_geo = self.intersect_geo(self.manual_solid_geo, cut_poly)

        if gap_type == 'mb':
            rests_geo = self.intersect_geo(self.mb_manual_solid_geo, cut_poly)
            if isinstance(rests_geo, list):
                self.mb_manual_cuts += rests_geo
            else:
                self.mb_manual_cuts.append(rests_geo)

        # first subtract geometry for the total solid_geometry
        new_solid_geometry = CutOut.subtract_geo(self.man_cutout_obj.solid_geometry, cut_poly)
        new_solid_geometry = linemerge(new_solid_geometry)
        self.man_cutout_obj.solid_geometry = new_solid_geometry

        # then do it on each tool in the manual cutout Geometry object
        try:
            self.man_cutout_obj.multigeo = True

            self.man_cutout_obj.tools[1]['solid_geometry'] = new_solid_geometry
            self.man_cutout_obj.tools[1]['data']['name'] = self.man_cutout_obj.options['name'] + '_cutout'
            self.man_cutout_obj.tools[1]['data']['cutz'] = self.ui.cutz_entry.get_value()
            self.man_cutout_obj.tools[1]['data']['multidepth'] = self.ui.mpass_cb.get_value()
            self.man_cutout_obj.tools[1]['data']['depthperpass'] = self.ui.maxdepth_entry.get_value()
        except KeyError:
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("No tool in the Geometry object."))
            return

        dia = self.ui.dia.get_value()
        if gaps_solid_geo:
            if 9999 not in self.man_cutout_obj.tools:
                self.man_cutout_obj.tools.update({
                    9999: self.cut_tool_dict
                })
                self.man_cutout_obj.tools[9999]['tooldia'] = str(dia)
                self.man_cutout_obj.tools[9999]['solid_geometry'] = [gaps_solid_geo]

                self.man_cutout_obj.tools[9999]['data']['name'] = self.man_cutout_obj.options['name'] + '_cutout'
                self.man_cutout_obj.tools[9999]['data']['cutz'] = self.ui.thin_depth_entry.get_value()
                self.man_cutout_obj.tools[9999]['data']['multidepth'] = self.ui.mpass_cb.get_value()
                self.man_cutout_obj.tools[9999]['data']['depthperpass'] = self.ui.maxdepth_entry.get_value()
                self.man_cutout_obj.tools[9999]['data']['override_color'] = "#29a3a3fa"
            else:
                self.man_cutout_obj.tools[9999]['solid_geometry'].append(gaps_solid_geo)

        self.man_cutout_obj.plot(plot_tool=1)
        self.app.inform.emit('%s' % _("Added manual Bridge Gap. Left click to add another or right click to finish."))

        self.app.should_we_save = True

    def on_manual_geo(self):
        name = self.ui.obj_combo.currentText()

        # Get source object.
        try:
            cutout_obj = self.app.collection.get_by_name(str(name))
        except Exception as e:
            log.debug("CutOut.on_manual_geo() --> %s" % str(e))
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
                        (isinstance(geo_union, MultiPolygon) and len(geo_union) == 1):
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

            geo_obj.options['cnctooldia'] = str(dia)
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
            geo_obj.tools[1]['data']['cutz'] = self.ui.cutz_entry.get_value()
            geo_obj.tools[1]['data']['multidepth'] = self.ui.mpass_cb.get_value()
            geo_obj.tools[1]['data']['depthperpass'] = self.ui.maxdepth_entry.get_value()

        outname = cutout_obj.options["name"] + "_cutout"
        self.app.app_obj.new_object('geometry', outname, geo_init)

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

        # do paint single only for left mouse clicks
        if event.button == 1:
            self.app.inform.emit(_("Making manual bridge gap..."))

            pos = self.app.plotcanvas.translate_coords(event_pos)

            self.on_manual_cutout(click_pos=pos)

        # if RMB then we exit
        elif event.button == right_button and self.mouse_is_dragging is False:
            if self.app.is_legacy is False:
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
            if self.ui.gaptype_radio.get_value() == 'mb':
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
                            while calc_len < line.length:
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

            self.app.inform.emit('[success] %s' % _("Finished manual adding of gaps."))

    def on_mouse_move(self, event):

        self.app.on_mouse_move_over_plot(event=event)

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

        try:
            rot_angle = 0
            for geo_el in man_geo:
                if isinstance(geo_el, Polygon):
                    work_geo = geo_el.exterior
                    if cut_geo.intersects(work_geo):
                        rot_angle = get_angle(geo=work_geo)
                    else:
                        rot_angle = 0
                else:
                    rot_angle = 0
                    if cut_geo.intersects(geo_el):
                        rot_angle = get_angle(geo=geo_el)
                if rot_angle != 0:
                    break
        except TypeError:
            if isinstance(man_geo, Polygon):
                work_geo = man_geo.exterior
                if cut_geo.intersects(work_geo):
                    rot_angle = get_angle(geo=work_geo)
                else:
                    rot_angle = 0
            else:
                rot_angle = 0
                if cut_geo.intersects(man_geo):
                    rot_angle = get_angle(geo=man_geo)

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

        # Escape = Deselect All
        if key == QtCore.Qt.Key_Escape or key == 'Escape':
            if self.mouse_events_connected is True:
                self.mouse_events_connected = False
                if self.app.is_legacy is False:
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

        # Grid toggle
        if key == QtCore.Qt.Key_G or key == 'G':
            self.app.ui.grid_snap_btn.trigger()

        # Jump to coords
        if key == QtCore.Qt.Key_J or key == 'J':
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
        try:
            for geo in geometry:
                if geo:
                    flat_geo += CutOut.flatten(geometry=geo)
        except TypeError:
            if isinstance(geometry, Polygon) and not geometry.is_empty:
                flat_geo.append(geometry.exterior)
                CutOut.flatten(geometry=geometry.interiors)
            elif not geometry.is_empty:
                flat_geo.append(geometry)

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

    @staticmethod
    def subtract_geo(target_geo, subtractor):
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
                diffs.append(target.difference(toolgeo))
            else:
                log.warning("Not implemented.")

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
        try:
            __ = iter(target_geo)
        except TypeError:
            target_geo = [target_geo]

        for geo in target_geo:
            if second_geo.intersects(geo):
                results.append(second_geo.intersection(geo))

        return CutOut.flatten(results)

    def reset_fields(self):
        self.ui.obj_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))


class CutoutUI:
    toolName = _("Cutout PCB")

    def __init__(self, layout, app):
        self.app = app
        self.decimals = self.app.decimals
        self.layout = layout

        # Title
        title_label = QtWidgets.QLabel("%s" % self.toolName)
        title_label.setStyleSheet("""
                                QLabel
                                {
                                    font-size: 16px;
                                    font-weight: bold;
                                }
                                """)
        self.layout.addWidget(title_label)

        self.layout.addWidget(QtWidgets.QLabel(''))

        # Form Layout
        grid0 = QtWidgets.QGridLayout()
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        self.layout.addLayout(grid0)

        self.object_label = QtWidgets.QLabel('<b>%s:</b>' % _("Source Object"))
        self.object_label.setToolTip('%s.' % _("Object to be cutout"))

        grid0.addWidget(self.object_label, 0, 0, 1, 2)

        # Object kind
        self.kindlabel = QtWidgets.QLabel('%s:' % _('Kind'))
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
        grid0.addWidget(self.kindlabel, 2, 0)
        grid0.addWidget(self.obj_kind_combo, 2, 1)

        # Type of object to be cutout
        self.type_obj_radio = RadioSet([
            {"label": _("Gerber"), "value": "grb"},
            {"label": _("Geometry"), "value": "geo"},
        ])

        self.type_obj_combo_label = QtWidgets.QLabel('%s:' % _("Type"))
        self.type_obj_combo_label.setToolTip(
            _("Specify the type of object to be cutout.\n"
              "It can be of type: Gerber or Geometry.\n"
              "What is selected here will dictate the kind\n"
              "of objects that will populate the 'Object' combobox.")
        )

        grid0.addWidget(self.type_obj_combo_label, 4, 0)
        grid0.addWidget(self.type_obj_radio, 4, 1)

        # Object to be cutout
        self.obj_combo = FCComboBox()
        self.obj_combo.setModel(self.app.collection)
        self.obj_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.obj_combo.is_last = True

        grid0.addWidget(self.obj_combo, 6, 0, 1, 2)

        # Convex Shape
        # Surrounding convex box shape
        self.convex_box_label = QtWidgets.QLabel('%s:' % _("Convex Shape"))
        self.convex_box_label.setToolTip(
            _("Create a convex shape surrounding the entire PCB.\n"
              "Used only if the source object type is Gerber.")
        )
        self.convex_box_cb = FCCheckBox()
        self.convex_box_cb.setToolTip(
            _("Create a convex shape surrounding the entire PCB.\n"
              "Used only if the source object type is Gerber.")
        )
        grid0.addWidget(self.convex_box_label, 8, 0)
        grid0.addWidget(self.convex_box_cb, 8, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 10, 0, 1, 2)

        self.tool_sel_label = FCLabel('<b>%s</b>' % _('Cutout Tool'))
        grid0.addWidget(self.tool_sel_label, 12, 0, 1, 2)

        # Tool Diameter
        self.dia = FCDoubleSpinner(callback=self.confirmation_message)
        self.dia.set_precision(self.decimals)
        self.dia.set_range(0.0000, 10000.0000)

        self.dia_label = QtWidgets.QLabel('%s:' % _("Tool Dia"))
        self.dia_label.setToolTip(
            _("Diameter of the tool used to cutout\n"
              "the PCB shape out of the surrounding material.")
        )
        grid0.addWidget(self.dia_label, 14, 0)
        grid0.addWidget(self.dia, 14, 1)

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

        grid0.addLayout(hlay, 16, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 18, 0, 1, 2)

        self.param_label = QtWidgets.QLabel('<b>%s:</b>' % _("Tool Parameters"))
        grid0.addWidget(self.param_label, 20, 0, 1, 2)

        # Cut Z
        cutzlabel = QtWidgets.QLabel('%s:' % _('Cut Z'))
        cutzlabel.setToolTip(
            _(
                "Cutting depth (negative)\n"
                "below the copper surface."
            )
        )
        self.cutz_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.cutz_entry.set_precision(self.decimals)

        if machinist_setting == 0:
            self.cutz_entry.setRange(-10000.0000, -0.00001)
        else:
            self.cutz_entry.setRange(-10000.0000, 10000.0000)

        self.cutz_entry.setSingleStep(0.1)

        grid0.addWidget(cutzlabel, 22, 0)
        grid0.addWidget(self.cutz_entry, 22, 1)

        # Multi-pass
        self.mpass_cb = FCCheckBox('%s:' % _("Multi-Depth"))
        self.mpass_cb.setToolTip(
            _(
                "Use multiple passes to limit\n"
                "the cut depth in each pass. Will\n"
                "cut multiple times until Cut Z is\n"
                "reached."
            )
        )

        self.maxdepth_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.maxdepth_entry.set_precision(self.decimals)
        self.maxdepth_entry.setRange(0, 10000.0000)
        self.maxdepth_entry.setSingleStep(0.1)

        self.maxdepth_entry.setToolTip(
            _(
                "Depth of each pass (positive)."
            )
        )

        grid0.addWidget(self.mpass_cb, 24, 0)
        grid0.addWidget(self.maxdepth_entry, 24, 1)

        self.ois_mpass_geo = OptionalInputSection(self.mpass_cb, [self.maxdepth_entry])

        # Margin
        self.margin = FCDoubleSpinner(callback=self.confirmation_message)
        self.margin.set_range(-10000.0000, 10000.0000)
        self.margin.setSingleStep(0.1)
        self.margin.set_precision(self.decimals)

        self.margin_label = QtWidgets.QLabel('%s:' % _("Margin"))
        self.margin_label.setToolTip(
            _("Margin over bounds. A positive value here\n"
              "will make the cutout of the PCB further from\n"
              "the actual PCB border")
        )
        grid0.addWidget(self.margin_label, 26, 0)
        grid0.addWidget(self.margin, 26, 1)

        # Gapsize
        self.gapsize_label = QtWidgets.QLabel('%s:' % _("Gap size"))
        self.gapsize_label.setToolTip(
            _("The size of the bridge gaps in the cutout\n"
              "used to keep the board connected to\n"
              "the surrounding material (the one \n"
              "from which the PCB is cutout).")
        )

        self.gapsize = FCDoubleSpinner(callback=self.confirmation_message)
        self.gapsize.set_precision(self.decimals)

        grid0.addWidget(self.gapsize_label, 28, 0)
        grid0.addWidget(self.gapsize, 28, 1)

        # Gap Type
        self.gaptype_label = FCLabel('%s:' % _("Gap type"))
        self.gaptype_label.setToolTip(
            _("The type of gap:\n"
              "- Bridge -> the cutout will be interrupted by bridges\n"
              "- Thin -> same as 'bridge' but it will be thinner by partially milling the gap\n"
              "- M-Bites -> 'Mouse Bites' - same as 'bridge' but covered with drill holes")
        )

        self.gaptype_radio = RadioSet(
            [
                {'label': _('Bridge'), 'value': 'b'},
                {'label': _('Thin'), 'value': 'bt'},
                {'label': "M-Bites", 'value': 'mb'}
            ],
            stretch=True
        )

        grid0.addWidget(self.gaptype_label, 30, 0)
        grid0.addWidget(self.gaptype_radio, 30, 1)

        # Thin gaps Depth
        self.thin_depth_label = FCLabel('%s:' % _("Depth"))
        self.thin_depth_label.setToolTip(
            _("The depth until the milling is done\n"
              "in order to thin the gaps.")
        )
        self.thin_depth_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.thin_depth_entry.set_precision(self.decimals)
        if machinist_setting == 0:
            self.thin_depth_entry.setRange(-10000.0000, -0.00001)
        else:
            self.thin_depth_entry.setRange(-10000.0000, 10000.0000)
        self.thin_depth_entry.setSingleStep(0.1)

        grid0.addWidget(self.thin_depth_label, 32, 0)
        grid0.addWidget(self.thin_depth_entry, 32, 1)

        # Mouse Bites Tool Diameter
        self.mb_dia_label = FCLabel('%s:' % _("Tool Diameter"))
        self.mb_dia_label.setToolTip(
            _("The drill hole diameter when doing mouse bites.")
        )
        self.mb_dia_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.mb_dia_entry.set_precision(self.decimals)
        self.mb_dia_entry.setRange(0, 100.0000)

        grid0.addWidget(self.mb_dia_label, 34, 0)
        grid0.addWidget(self.mb_dia_entry, 34, 1)

        # Mouse Bites Holes Spacing
        self.mb_spacing_label = FCLabel('%s:' % _("Spacing"))
        self.mb_spacing_label.setToolTip(
            _("The spacing between drill holes when doing mouse bites.")
        )
        self.mb_spacing_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.mb_spacing_entry.set_precision(self.decimals)
        self.mb_spacing_entry.setRange(0, 100.0000)

        grid0.addWidget(self.mb_spacing_label, 36, 0)
        grid0.addWidget(self.mb_spacing_entry, 36, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 38, 0, 1, 2)

        # Title2
        title_param_label = QtWidgets.QLabel("<b>%s %s</b>:" % (_('Automatic'), _("Bridge Gaps")))
        title_param_label.setToolTip(
            _("This section handle creation of automatic bridge gaps.")
        )
        grid0.addWidget(title_param_label, 40, 0, 1, 2)

        # Gaps
        # How gaps wil be rendered:
        # lr    - left + right
        # tb    - top + bottom
        # 4     - left + right +top + bottom
        # 2lr   - 2*left + 2*right
        # 2tb   - 2*top + 2*bottom
        # 8     - 2*left + 2*right +2*top + 2*bottom
        gaps_label = QtWidgets.QLabel('%s:' % _('Gaps'))
        gaps_label.setToolTip(
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
        grid0.addWidget(gaps_label, 42, 0)
        grid0.addWidget(self.gaps, 42, 1)

        # Buttons
        self.ff_cutout_object_btn = FCButton(_("Generate Geometry"))
        self.ff_cutout_object_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/irregular32.png'))
        self.ff_cutout_object_btn.setToolTip(
            _("Cutout the selected object.\n"
              "The cutout shape can be of any shape.\n"
              "Useful when the PCB has a non-rectangular shape.")
        )
        self.ff_cutout_object_btn.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        grid0.addWidget(self.ff_cutout_object_btn, 44, 0, 1, 2)

        self.rect_cutout_object_btn = FCButton(_("Generate Geometry"))
        self.rect_cutout_object_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/rectangle32.png'))
        self.rect_cutout_object_btn.setToolTip(
            _("Cutout the selected object.\n"
              "The resulting cutout shape is\n"
              "always a rectangle shape and it will be\n"
              "the bounding box of the Object.")
        )
        self.rect_cutout_object_btn.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        grid0.addWidget(self.rect_cutout_object_btn, 46, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 48, 0, 1, 2)

        # MANUAL BRIDGE GAPS
        title_manual_label = QtWidgets.QLabel("<b>%s %s</b>:" % (_('Manual'), _("Bridge Gaps")))
        title_manual_label.setToolTip(
            _("This section handle creation of manual bridge gaps.\n"
              "This is done by mouse clicking on the perimeter of the\n"
              "Geometry object that is used as a cutout object. ")
        )
        grid0.addWidget(title_manual_label, 50, 0, 1, 2)

        # Big Cursor
        big_cursor_label = QtWidgets.QLabel('%s:' % _("Big cursor"))
        big_cursor_label.setToolTip(
            _("Use a big cursor when adding manual gaps."))
        self.big_cursor_cb = FCCheckBox()

        grid0.addWidget(big_cursor_label, 52, 0)
        grid0.addWidget(self.big_cursor_cb, 52, 1)

        # Generate a surrounding Geometry object
        self.man_geo_creation_btn = FCButton(_("Generate Manual Geometry"))
        self.man_geo_creation_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/rectangle32.png'))
        self.man_geo_creation_btn.setToolTip(
            _("If the object to be cutout is a Gerber\n"
              "first create a Geometry that surrounds it,\n"
              "to be used as the cutout, if one doesn't exist yet.\n"
              "Select the source Gerber file in the top object combobox.")
        )
        # self.man_geo_creation_btn.setStyleSheet("""
        #                         QPushButton
        #                         {
        #                             font-weight: bold;
        #                         }
        #                         """)
        grid0.addWidget(self.man_geo_creation_btn, 54, 0, 1, 2)

        # Manual Geo Object
        self.man_object_combo = FCComboBox()
        self.man_object_combo.setModel(self.app.collection)
        self.man_object_combo.setRootModelIndex(self.app.collection.index(2, 0, QtCore.QModelIndex()))
        self.man_object_combo.is_last = True
        self.man_object_combo.obj_type = "Geometry"

        self.man_object_label = QtWidgets.QLabel('%s:' % _("Manual cutout Geometry"))
        self.man_object_label.setToolTip(
            _("Geometry object used to create the manual cutout.")
        )
        # self.man_object_label.setMinimumWidth(60)

        grid0.addWidget(self.man_object_label, 56, 0, 1, 2)
        grid0.addWidget(self.man_object_combo, 56, 0, 1, 2)

        self.man_gaps_creation_btn = FCButton(_("Manual Add Bridge Gaps"))
        self.man_gaps_creation_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/gaps32.png'))
        self.man_gaps_creation_btn.setToolTip(
            _("Use the left mouse button (LMB) click\n"
              "to create a bridge gap to separate the PCB from\n"
              "the surrounding material.\n"
              "The LMB click has to be done on the perimeter of\n"
              "the Geometry object used as a cutout geometry.")
        )
        self.man_gaps_creation_btn.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        grid0.addWidget(self.man_gaps_creation_btn, 58, 0, 1, 2)

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

        self.gaptype_radio.activated_custom.connect(self.on_gap_type_radio)

        # ############################ FINSIHED GUI ###################################
        # #############################################################################

    def on_gap_type_radio(self, val):
        if val == 'b':
            self.thin_depth_label.hide()
            self.thin_depth_entry.hide()
            self.mb_dia_label.hide()
            self.mb_dia_entry.hide()
            self.mb_spacing_label.hide()
            self.mb_spacing_entry.hide()
        elif val == 'bt':
            self.thin_depth_label.show()
            self.thin_depth_entry.show()
            self.mb_dia_label.hide()
            self.mb_dia_entry.hide()
            self.mb_spacing_label.hide()
            self.mb_spacing_entry.hide()
        elif val == 'mb':
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
