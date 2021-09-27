# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 5/17/2020                                         #
# MIT Licence                                              #
# ##########################################################

from PyQt6 import QtWidgets, QtCore, QtGui

from appTool import AppTool
from appCommon.Common import LoudDict
from appGUI.GUIElements import FCDoubleSpinner, FCCheckBox, FCComboBox, FCButton, RadioSet, FCLabel, \
    VerticalScrollArea, FCGridLayout, FCFrame
from camlib import flatten_shapely_geometry

from shapely.geometry import MultiPolygon, LineString, Point
from shapely.ops import unary_union

from copy import deepcopy
import logging

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class ToolCorners(AppTool):

    def __init__(self, app):
        AppTool.__init__(self, app)

        self.app = app
        self.canvas = self.app.plotcanvas

        self.decimals = self.app.decimals
        self.units = ''

        # here we store the locations of the selected corners
        self.points = {}

        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = CornersUI(layout=self.layout, app=self.app)
        self.pluginName = self.ui.pluginName
        self.connect_signals_at_init()

        # Objects involved in Copper thieving
        self.grb_object = None

        # store the flattened geometry here:
        self.flat_geometry = []

        self.mr = None

        # Tool properties
        self.fid_dia = None

        self.grb_steps_per_circle = self.app.defaults["gerber_circle_steps"]

        self.handlers_connected = False

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolCorners()")

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

        self.app.ui.notebook.setTabText(2, _("Corners"))

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Alt+B', **kwargs)

    def connect_signals_at_init(self):

        # #############################################################################
        # ############################ SIGNALS ########################################
        # #############################################################################
        self.ui.level.toggled.connect(self.on_level_changed)
        self.ui.add_marker_button.clicked.connect(self.add_markers)
        self.ui.toggle_all_cb.toggled.connect(self.on_toggle_all)
        self.ui.drill_button.clicked.connect(self.on_create_drill_object)
        self.ui.check_button.clicked.connect(self.on_create_check_object)
        self.ui.sel_radio.activated_custom.connect(self.on_selection_changed)

    def set_tool_ui(self):
        self.units = self.app.app_units

        self.clear_ui(self.layout)
        self.ui = CornersUI(layout=self.layout, app=self.app)
        self.pluginName = self.ui.pluginName
        self.connect_signals_at_init()

        self.ui.thick_entry.set_value(self.app.defaults["tools_corners_thickness"])
        self.ui.l_entry.set_value(float(self.app.defaults["tools_corners_length"]))
        self.ui.margin_entry.set_value(float(self.app.defaults["tools_corners_margin"]))
        self.ui.toggle_all_cb.set_value(False)
        self.ui.type_radio.set_value(self.app.defaults["tools_corners_type"])
        self.ui.drill_dia_entry.set_value(self.app.defaults["tools_corners_drill_dia"])
        self.ui.sel_radio.set_value("a")

        # SELECT THE CURRENT OBJECT
        obj = self.app.collection.get_active()
        if obj and obj.kind == 'gerber':
            obj_name = obj.options['name']
            self.ui.object_combo.set_value(obj_name)

        if obj is None:
            self.ui.object_combo.setCurrentIndex(0)

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

            self.ui.drills_label.hide()
            self.ui.drill_frame.hide()
            self.ui.drill_button.hide()
            self.ui.check_label.hide()
            self.ui.check_button.hide()
        else:
            self.ui.level.setText('%s' % _('Advanced'))
            self.ui.level.setStyleSheet("""
                                        QToolButton
                                        {
                                            color: red;
                                        }
                                        """)

            self.ui.drills_label.show()
            self.ui.drill_frame.show()
            self.ui.drill_button.show()
            self.ui.check_label.show()
            self.ui.check_button.show()

    def on_toggle_all(self, val):
        self.ui.bl_cb.set_value(val)
        self.ui.br_cb.set_value(val)
        self.ui.tl_cb.set_value(val)
        self.ui.tr_cb.set_value(val)

    def on_selection_changed(self, val):
        if val == 'a':
            self.ui.locs_label.setDisabled(False)
            self.ui.loc_frame.setDisabled(False)

            self.ui.type_label.setDisabled(False)
            self.ui.type_radio.setDisabled(False)
            self.ui.margin_label.setDisabled(False)
            self.ui.margin_entry.setDisabled(False)
        else:
            self.ui.locs_label.setDisabled(True)
            self.ui.loc_frame.setDisabled(True)

            self.ui.type_label.setDisabled(True)
            self.ui.type_radio.setDisabled(True)
            self.ui.margin_label.setDisabled(True)
            self.ui.margin_entry.setDisabled(True)
            self.ui.type_radio.set_value('c')

    def add_markers(self):
        self.app.call_source = "corners_tool"
        select_type = self.ui.sel_radio.get_value()
        if select_type == 'a':
            self.handle_automatic_placement()
        else:
            self.app.inform.emit('%s' % _("Click to add next marker or right click to finish."))
            # it works only with cross markers
            self.ui.type_radio.set_value('c')
            self.app.ui.notebook.setDisabled(True)
            self.connect_event_handlers()

    def handle_automatic_placement(self):
        tl_state = self.ui.tl_cb.get_value()
        tr_state = self.ui.tr_cb.get_value()
        bl_state = self.ui.bl_cb.get_value()
        br_state = self.ui.br_cb.get_value()

        # get the Gerber object on which the corner marker will be inserted
        selection_index = self.ui.object_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.ui.object_combo.rootModelIndex())

        try:
            self.grb_object = model_index.internalPointer().obj
        except Exception as e:
            log.error("ToolCorners.add_markers() --> %s" % str(e))
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Gerber object loaded ..."))
            self.app.call_source = "app"
            return

        xmin, ymin, xmax, ymax = self.grb_object.bounds()
        self.points = {}
        if tl_state:
            self.points['tl'] = (xmin, ymax)
        if tr_state:
            self.points['tr'] = (xmax, ymax)
        if bl_state:
            self.points['bl'] = (xmin, ymin)
        if br_state:
            self.points['br'] = (xmax, ymin)

        ret_val = self.add_corners_geo(self.points, g_obj=self.grb_object)
        self.app.call_source = "app"
        if ret_val == 'fail':
            self.app.call_source = "app"
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed."))
            return

        self.on_exit(ret_val)

    def handle_manual_placement(self):
        # self.app.inform.emit('[ERROR_NOTCL] %s' % "Not implemented yet.")

        # get the Gerber object on which the corner marker will be inserted
        selection_index = self.ui.object_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.ui.object_combo.rootModelIndex())

        try:
            self.grb_object = model_index.internalPointer().obj
        except Exception as e:
            log.error("ToolCorners.add_markers() --> %s" % str(e))
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Gerber object loaded ..."))
            self.on_exit()
            return

        ret_val = self.add_corners_geo(self.points, g_obj=self.grb_object)
        if ret_val == 'fail':
            self.on_exit(ok=False)
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed."))
            return
        self.on_exit()

    def add_corners_geo(self, points_storage, g_obj):
        """
        Add geometry to the solid_geometry of the copper Gerber object

        :param points_storage:  a dictionary holding the points where to add corners
        :param g_obj:           the Gerber object where to add the geometry
        :return:                None
        """

        marker_type = self.ui.type_radio.get_value()
        line_thickness = self.ui.thick_entry.get_value()
        margin = self.ui.margin_entry.get_value()
        line_length = self.ui.l_entry.get_value() / 2.0

        geo_list = []

        if not points_storage:
            self.app.inform.emit("[ERROR_NOTCL] %s." % _("Please select at least a location"))
            return 'fail'

        for key in points_storage:
            if key == 'tl':
                pt = points_storage[key]
                x = pt[0] - margin - line_thickness / 2.0
                y = pt[1] + margin + line_thickness / 2.0
                if marker_type == 's':
                    line_geo_hor = LineString([
                        (x, y), (x + line_length, y)
                    ])
                    line_geo_vert = LineString([
                        (x, y), (x, y - line_length)
                    ])
                else:
                    line_geo_hor = LineString([
                        (x - line_length, y), (x + line_length, y)
                    ])
                    line_geo_vert = LineString([
                        (x, y + line_length), (x, y - line_length)
                    ])
                geo_list.append(line_geo_hor)
                geo_list.append(line_geo_vert)
            if key == 'tr':
                pt = points_storage[key]
                x = pt[0] + margin + line_thickness / 2.0
                y = pt[1] + margin + line_thickness / 2.0
                if marker_type == 's':
                    line_geo_hor = LineString([
                        (x, y), (x - line_length, y)
                    ])
                    line_geo_vert = LineString([
                        (x, y), (x, y - line_length)
                    ])
                else:
                    line_geo_hor = LineString([
                        (x + line_length, y), (x - line_length, y)
                    ])
                    line_geo_vert = LineString([
                        (x, y + line_length), (x, y - line_length)
                    ])
                geo_list.append(line_geo_hor)
                geo_list.append(line_geo_vert)
            if key == 'bl':
                pt = points_storage[key]
                x = pt[0] - margin - line_thickness / 2.0
                y = pt[1] - margin - line_thickness / 2.0
                if marker_type == 's':
                    line_geo_hor = LineString([
                        (x, y), (x + line_length, y)
                    ])
                    line_geo_vert = LineString([
                        (x, y), (x, y + line_length)
                    ])
                else:
                    line_geo_hor = LineString([
                        (x - line_length, y), (x + line_length, y)
                    ])
                    line_geo_vert = LineString([
                        (x, y - line_length), (x, y + line_length)
                    ])
                geo_list.append(line_geo_hor)
                geo_list.append(line_geo_vert)
            if key == 'br':
                pt = points_storage[key]
                x = pt[0] + margin + line_thickness / 2.0
                y = pt[1] - margin - line_thickness / 2.0
                if marker_type == 's':
                    line_geo_hor = LineString([
                        (x, y), (x - line_length, y)
                    ])
                    line_geo_vert = LineString([
                        (x, y), (x, y + line_length)
                    ])
                else:
                    line_geo_hor = LineString([
                        (x + line_length, y), (x - line_length, y)
                    ])
                    line_geo_vert = LineString([
                        (x, y - line_length), (x, y + line_length)
                    ])
                geo_list.append(line_geo_hor)
                geo_list.append(line_geo_vert)
            if key == 'manual':
                if points_storage['manual']:
                    for man_pt in points_storage['manual']:
                        x = man_pt[0] - line_thickness / 2.0
                        y = man_pt[1] + line_thickness / 2.0
                        line_geo_hor = LineString([
                            (x - line_length, y), (x + line_length, y)
                        ])
                        line_geo_vert = LineString([
                            (x, y + line_length), (x, y - line_length)
                        ])
                        geo_list.append(line_geo_hor)
                        geo_list.append(line_geo_vert)
                else:
                    self.app.log.warning("Not enough points.")
                    return "fail"

        new_apertures = deepcopy(g_obj.tools)

        aperture_found = None
        for ap_id, ap_val in new_apertures.items():
            if ap_val['type'] == 'C' and ap_val['size'] == line_thickness:
                aperture_found = ap_id
                break

        geo_buff_list = []
        if aperture_found:
            for geo in geo_list:
                geo_buff = geo.buffer(line_thickness / 2.0, resolution=self.grb_steps_per_circle, join_style=2)
                geo_buff_list.append(geo_buff)

                dict_el = {'follow': geo, 'solid': geo_buff}
                new_apertures[aperture_found]['geometry'].append(deepcopy(dict_el))
        else:
            ap_keys = list(new_apertures.keys())
            if ap_keys:
                new_apid = int(max(ap_keys)) + 1
            else:
                new_apid = 10

            new_apertures[new_apid] = {
                'type': 'C',
                'size': line_thickness,
                'geometry': []
            }

            for geo in geo_list:
                geo_buff = geo.buffer(line_thickness / 2.0, resolution=self.grb_steps_per_circle, join_style=3)
                geo_buff_list.append(geo_buff)

                dict_el = {'follow': geo, 'solid': geo_buff}
                new_apertures[new_apid]['geometry'].append(deepcopy(dict_el))

        s_list = []
        if g_obj.solid_geometry:
            try:
                for poly in g_obj.solid_geometry:
                    s_list.append(poly)
            except TypeError:
                s_list.append(g_obj.solid_geometry)

        geo_buff_list = MultiPolygon(geo_buff_list)
        geo_buff_list = geo_buff_list.buffer(0)
        geo_buff_list = flatten_shapely_geometry(geo_buff_list)

        try:
            for poly in geo_buff_list:
                s_list.append(poly)
        except TypeError:
            s_list.append(geo_buff_list)

        outname = '%s_%s' % (str(self.grb_object.options['name']), 'corners')

        def initialize(grb_obj, app_obj):
            grb_obj.options = LoudDict()
            for opt in g_obj.options:
                if opt != 'name':
                    grb_obj.options[opt] = deepcopy(g_obj.options[opt])
            grb_obj.options['name'] = outname
            grb_obj.multitool = False
            grb_obj.multigeo = False
            grb_obj.follow = deepcopy(g_obj.follow)
            grb_obj.tools = new_apertures
            grb_obj.solid_geometry = flatten_shapely_geometry(unary_union(s_list))
            grb_obj.follow_geometry = flatten_shapely_geometry(g_obj.follow_geometry + geo_list)

            grb_obj.source_file = app_obj.f_handlers.export_gerber(obj_name=outname, filename=None, local_use=grb_obj,
                                                                   use_thread=False)

        ret = self.app.app_obj.new_object('gerber', outname, initialize, plot=True)

        return ret

    def on_create_drill_object(self):
        self.app.call_source = "corners_tool"

        tooldia = self.ui.drill_dia_entry.get_value()

        if tooldia == 0:
            self.app.inform.emit('[WARNING_NOTCL] %s %s' % (_("Cancelled."), _("The tool diameter is zero.")))
            return

        line_thickness = self.ui.thick_entry.get_value()
        margin = self.ui.margin_entry.get_value()
        tl_state = self.ui.tl_cb.get_value()
        tr_state = self.ui.tr_cb.get_value()
        bl_state = self.ui.bl_cb.get_value()
        br_state = self.ui.br_cb.get_value()

        # get the Gerber object on which the corner marker will be inserted
        selection_index = self.ui.object_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.ui.object_combo.rootModelIndex())

        try:
            self.grb_object = model_index.internalPointer().obj
        except Exception as e:
            log.error("ToolCorners.add_markers() --> %s" % str(e))
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Gerber object loaded ..."))
            self.app.call_source = "app"
            return

        if tl_state is False and tr_state is False and bl_state is False and br_state is False:
            self.app.inform.emit("[ERROR_NOTCL] %s." % _("Please select at least a location"))
            self.app.call_source = "app"
            return

        xmin, ymin, xmax, ymax = self.grb_object.bounds()

        # list of (x,y) tuples. Store here the drill coordinates
        drill_list = []

        if tl_state:
            x = xmin - margin - line_thickness / 2.0 + tooldia / 2.0
            y = ymax + margin + line_thickness / 2.0 - tooldia / 2.0
            drill_list.append(
                Point((x, y))
            )

        if tr_state:
            x = xmax + margin + line_thickness / 2.0 - tooldia / 2.0
            y = ymax + margin + line_thickness / 2.0 - tooldia / 2.0
            drill_list.append(
                Point((x, y))
            )

        if bl_state:
            x = xmin - margin - line_thickness / 2.0 + tooldia / 2.0
            y = ymin - margin - line_thickness / 2.0 + tooldia / 2.0
            drill_list.append(
                Point((x, y))
            )

        if br_state:
            x = xmax + margin + line_thickness / 2.0 - tooldia / 2.0
            y = ymin - margin - line_thickness / 2.0 + tooldia / 2.0
            drill_list.append(
                Point((x, y))
            )

        tools = {
            1: {
                "tooldia": tooldia,
                "drills": drill_list,
                "slots": [],
                "solid_geometry": []
            }
        }

        def obj_init(obj_inst, app_inst):
            obj_inst.options.update({
                'name': outname
            })
            obj_inst.tools = deepcopy(tools)
            obj_inst.create_geometry()
            obj_inst.source_file = app_inst.f_handlers.export_excellon(obj_name=obj_inst.options['name'],
                                                                       local_use=obj_inst,
                                                                       filename=None,
                                                                       use_thread=False)

        outname = '%s_%s' % (str(self.grb_object.options['name']), 'corner_drills')
        ret_val = self.app.app_obj.new_object("excellon", outname, obj_init)

        self.app.call_source = "app"
        if ret_val == 'fail':
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed."))
        else:
            self.app.inform.emit('[success] %s' % _("Excellon object with corner drills created."))

    def on_create_check_object(self):
        self.app.call_source = "corners_tool"

        tooldia = 0.1 if self.units == 'MM' else 0.0254

        if tooldia == 0:
            self.app.inform.emit('[WARNING_NOTCL] %s %s' % (_("Cancelled."), _("The tool diameter is zero.")))
            return

        line_thickness = self.ui.thick_entry.get_value()
        margin = self.ui.margin_entry.get_value()
        tl_state = self.ui.tl_cb.get_value()
        tr_state = self.ui.tr_cb.get_value()
        bl_state = self.ui.bl_cb.get_value()
        br_state = self.ui.br_cb.get_value()

        # get the Gerber object on which the corner marker will be inserted
        selection_index = self.ui.object_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.ui.object_combo.rootModelIndex())

        try:
            self.grb_object = model_index.internalPointer().obj
        except Exception as e:
            log.error("ToolCorners.add_markers() --> %s" % str(e))
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Gerber object loaded ..."))
            self.app.call_source = "app"
            return

        if tl_state is False and tr_state is False and bl_state is False and br_state is False:
            self.app.inform.emit("[ERROR_NOTCL] %s." % _("Please select at least a location"))
            self.app.call_source = "app"
            return

        xmin, ymin, xmax, ymax = self.grb_object.bounds()

        # list of (x,y) tuples. Store here the drill coordinates
        drill_list = []

        if tl_state:
            x = xmin - margin - line_thickness / 2.0 + tooldia / 2.0
            y = ymax + margin + line_thickness / 2.0 - tooldia / 2.0
            drill_list.append(
                Point((x, y))
            )

        if tr_state:
            x = xmax + margin + line_thickness / 2.0 - tooldia / 2.0
            y = ymax + margin + line_thickness / 2.0 - tooldia / 2.0
            drill_list.append(
                Point((x, y))
            )

        if bl_state:
            x = xmin - margin - line_thickness / 2.0 + tooldia / 2.0
            y = ymin - margin - line_thickness / 2.0 + tooldia / 2.0
            drill_list.append(
                Point((x, y))
            )

        if br_state:
            x = xmax + margin + line_thickness / 2.0 - tooldia / 2.0
            y = ymin - margin - line_thickness / 2.0 + tooldia / 2.0
            drill_list.append(
                Point((x, y))
            )

        tools = {
            1: {
                "tooldia": tooldia,
                "drills": drill_list,
                "slots": [],
                'data': {},
                "solid_geometry": []
            }
        }

        def obj_init(new_obj, app_inst):
            new_obj.tools = deepcopy(tools)

            # make sure we use the special preprocessor for checking
            for tool in tools:
                new_obj.tools[tool]['data']['tools_drill_ppname_e'] = 'Check_points'

            new_obj.create_geometry()
            new_obj.options.update({
                'name': outname,
                'tools_drill_cutz': -0.1,
                'tools_drill_ppname_e': 'Check_points'
            })
            new_obj.source_file = app_inst.f_handlers.export_excellon(obj_name=new_obj.options['name'],
                                                                      local_use=new_obj,
                                                                      filename=None,
                                                                      use_thread=False)

        outname = '%s_%s' % (str(self.grb_object.options['name']), 'verification')
        ret_val = self.app.app_obj.new_object("excellon", outname, obj_init)

        self.app.call_source = "app"
        if ret_val == 'fail':
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed."))
        else:
            self.app.inform.emit('[success] %s' % _("Excellon object with corner drills created."))

    def replot(self, obj, run_thread=True):
        def worker_task():
            with self.app.proc_container.new('%s ...' % _("Plotting")):
                obj.plot()
                self.app.app_obj.object_plotted.emit(obj)

        if run_thread:
            self.app.worker_task.emit({'fcn': worker_task, 'params': []})
        else:
            worker_task()

    def on_exit(self, corner_gerber_obj=None, cancelled=None, ok=True):
        # plot the object
        if corner_gerber_obj:
            try:
                for ob in corner_gerber_obj:
                    self.replot(obj=ob)
            except (AttributeError, TypeError):
                self.replot(obj=corner_gerber_obj)
            except Exception:
                return

        # update the bounding box values
        try:
            a, b, c, d = self.grb_object.bounds()
            self.grb_object.options['xmin'] = a
            self.grb_object.options['ymin'] = b
            self.grb_object.options['xmax'] = c
            self.grb_object.options['ymax'] = d
        except Exception as e:
            log.error("ToolCorners.on_exit() copper_obj bounds error --> %s" % str(e))

        self.app.call_source = "app"
        self.app.ui.notebook.setDisabled(False)
        self.disconnect_event_handlers()

        if cancelled is True:
            self.app.delete_selection_shape()
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled by user request."))
            return

        if ok:
            self.app.inform.emit('[success] %s' % _("A Gerber object with corner markers was created."))

    def connect_event_handlers(self):
        if self.handlers_connected is False:
            if self.app.is_legacy is False:
                self.app.plotcanvas.graph_event_disconnect('mouse_press', self.app.on_mouse_click_over_plot)
                self.app.plotcanvas.graph_event_disconnect('mouse_release', self.app.on_mouse_click_release_over_plot)
            else:
                self.app.plotcanvas.graph_event_disconnect(self.app.mp)
                self.app.plotcanvas.graph_event_disconnect(self.app.mr)

            self.mr = self.app.plotcanvas.graph_event_connect('mouse_release', self.on_mouse_release)

            self.handlers_connected = True

    def disconnect_event_handlers(self):
        if self.handlers_connected is True:
            if self.app.is_legacy is False:
                self.app.plotcanvas.graph_event_disconnect('mouse_release', self.on_mouse_release)
            else:
                self.app.plotcanvas.graph_event_disconnect(self.mr)

            self.app.mp = self.app.plotcanvas.graph_event_connect('mouse_press',
                                                                  self.app.on_mouse_click_over_plot)

            self.app.mr = self.app.plotcanvas.graph_event_connect('mouse_release',
                                                                  self.app.on_mouse_click_release_over_plot)
            self.handlers_connected = False
            self.app.ui.notebook.setDisabled(False)

    def on_mouse_move(self, event):
        pass

    def on_mouse_release(self, event):
        if self.app.is_legacy is False:
            event_pos = event.pos
            right_button = 2
            self.app.event_is_dragging = self.app.event_is_dragging
        else:
            event_pos = (event.xdata, event.ydata)
            right_button = 3
            self.app.event_is_dragging = self.app.ui.popMenu.mouse_is_panning

        if event.button == 1:
            pos_canvas = self.canvas.translate_coords(event_pos)
            if self.app.grid_status():
                pos = self.app.geo_editor.snap(pos_canvas[0], pos_canvas[1])
            else:
                pos = (pos_canvas[0], pos_canvas[1])

            if 'manual' not in self.points:
                self.points['manual'] = []
            self.points['manual'].append(pos)

            self.app.inform.emit(
                '%s: %d. %s' %
                (_("Added marker"), len(self.points['manual']),
                 _("Click to add next marker or right click to finish.")))

        elif event.button == right_button and self.app.event_is_dragging is False:
            self.handle_manual_placement()


class CornersUI:

    pluginName = _("Corner Markers")

    def __init__(self, layout, app):
        self.app = app
        self.decimals = self.app.decimals
        self.layout = layout

        self.title_box = QtWidgets.QHBoxLayout()
        self.layout.addLayout(self.title_box)

        # ## Title
        title_label = FCLabel("%s" % self.pluginName)
        title_label.setStyleSheet("""
                                QLabel
                                {
                                    font-size: 16px;
                                    font-weight: bold;
                                }
                                """)
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

        self.title_box = QtWidgets.QHBoxLayout()
        self.layout.addLayout(self.title_box)

        self.tools_frame = QtWidgets.QFrame()
        self.tools_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.tools_frame)
        self.tools_box = QtWidgets.QVBoxLayout()
        self.tools_box.setContentsMargins(0, 0, 0, 0)
        self.tools_frame.setLayout(self.tools_box)

        # #############################################################################################################
        # Gerber Source Object Frame
        # #############################################################################################################

        # Gerber object #
        self.object_label = FCLabel('<span style="color:darkorange;"><b>%s</b></span>' % _("Source Object"))
        self.object_label.setToolTip(_("The Gerber object to which will be added corner markers."))

        self.object_combo = FCComboBox()
        self.object_combo.setModel(self.app.collection)
        self.object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.object_combo.is_last = True
        self.object_combo.obj_type = "Gerber"

        self.tools_box.addWidget(self.object_label)
        self.tools_box.addWidget(self.object_combo)

        # separator_line = QtWidgets.QFrame()
        # separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        # separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        # self.layout.addWidget(separator_line)

        # #############################################################################################################
        # Parameters Frame
        # #############################################################################################################
        self.param_label = FCLabel('<span style="color:blue;"><b>%s</b></span>' % _('Parameters'))
        self.param_label.setToolTip(_("Parameters used for this tool."))
        self.tools_box.addWidget(self.param_label)

        par_frame = FCFrame()
        self.tools_box.addWidget(par_frame)

        # ## Grid Layout
        par_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        par_frame.setLayout(par_grid)

        # Type of Marker
        self.type_label = FCLabel('%s:' % _("Type"))
        self.type_label.setToolTip(
            _("Shape of the marker.")
        )

        self.type_radio = RadioSet([
            {"label": _("Semi-Cross"), "value": "s"},
            {"label": _("Cross"), "value": "c"},
        ])

        par_grid.addWidget(self.type_label, 2, 0)
        par_grid.addWidget(self.type_radio, 2, 1)

        # Thickness #
        self.thick_label = FCLabel('%s:' % _("Thickness"))
        self.thick_label.setToolTip(
            _("The thickness of the line that makes the corner marker.")
        )
        self.thick_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.thick_entry.set_range(0.0000, 10.0000)
        self.thick_entry.set_precision(self.decimals)
        self.thick_entry.setWrapping(True)
        self.thick_entry.setSingleStep(10 ** -self.decimals)

        par_grid.addWidget(self.thick_label, 4, 0)
        par_grid.addWidget(self.thick_entry, 4, 1)

        # Length #
        self.l_label = FCLabel('%s:' % _("Length"))
        self.l_label.setToolTip(
            _("The length of the line that makes the corner marker.")
        )
        self.l_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.l_entry.set_range(-10000.0000, 10000.0000)
        self.l_entry.set_precision(self.decimals)
        self.l_entry.setSingleStep(10 ** -self.decimals)

        par_grid.addWidget(self.l_label, 6, 0)
        par_grid.addWidget(self.l_entry, 6, 1)

        # Margin #
        self.margin_label = FCLabel('%s:' % _("Margin"))
        self.margin_label.setToolTip(
            _("Bounding box margin.")
        )
        self.margin_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.margin_entry.set_range(-10000.0000, 10000.0000)
        self.margin_entry.set_precision(self.decimals)
        self.margin_entry.setSingleStep(0.1)

        par_grid.addWidget(self.margin_label, 8, 0)
        par_grid.addWidget(self.margin_entry, 8, 1)

        # #############################################################################################################
        # Locations Frame
        # #############################################################################################################
        self.locs_label = FCLabel('<span style="color:red;"><b>%s</b></span>' % _('Locations'))
        self.locs_label.setToolTip(_("Locations where to place corner markers."))
        self.tools_box.addWidget(self.locs_label)

        self.loc_frame = FCFrame()
        self.tools_box.addWidget(self.loc_frame)

        # Grid Layout
        grid_loc = FCGridLayout(v_spacing=5, h_spacing=3)
        self.loc_frame.setLayout(grid_loc)

        # TOP LEFT
        self.tl_cb = FCCheckBox(_("Top Left"))
        grid_loc.addWidget(self.tl_cb, 0, 0)

        # TOP RIGHT
        self.tr_cb = FCCheckBox(_("Top Right"))
        grid_loc.addWidget(self.tr_cb, 0, 1)

        # BOTTOM LEFT
        self.bl_cb = FCCheckBox(_("Bottom Left"))
        grid_loc.addWidget(self.bl_cb, 2, 0)

        # BOTTOM RIGHT
        self.br_cb = FCCheckBox(_("Bottom Right"))
        grid_loc.addWidget(self.br_cb, 2, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        grid_loc.addWidget(separator_line, 4, 0, 1, 2)

        # Toggle ALL
        self.toggle_all_cb = FCCheckBox(_("Toggle ALL"))
        grid_loc.addWidget(self.toggle_all_cb, 6, 0, 1, 2)

        # #############################################################################################################
        # Selection Frame
        # #############################################################################################################
        # Selection
        self.sel_label = FCLabel('<span style="color:green;"><b>%s</b></span>' % _("Selection"))
        self.tools_box.addWidget(self.sel_label)

        self.s_frame = FCFrame()
        self.tools_box.addWidget(self.s_frame)

        # Grid Layout
        grid_sel = FCGridLayout(v_spacing=5, h_spacing=3)
        self.s_frame.setLayout(grid_sel)

        # Type of placement of markers
        self.sel_label = FCLabel('%s: ' % _("Mode"))
        self.sel_label.setToolTip(
            _("When the manual type is chosen, the markers\n"
              "are manually placed on canvas.")
        )

        self.sel_radio = RadioSet([
            {"label": _("Auto"), "value": "a"},
            {"label": _("Manual"), "value": "m"},
        ])

        grid_sel.addWidget(self.sel_label, 0, 0)
        grid_sel.addWidget(self.sel_radio, 0, 1)

        # #############################################################################################################
        # ## Insert Corner Marker Button
        # #############################################################################################################
        self.add_marker_button = FCButton(_("Add Marker"))
        self.add_marker_button.setIcon(QtGui.QIcon(self.app.resource_location + '/corners_32.png'))
        self.add_marker_button.setToolTip(
            _("Will add corner markers to the selected Gerber file.")
        )
        self.add_marker_button.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        self.tools_box.addWidget(self.add_marker_button,)

        # #############################################################################################################
        # Drill in Corners Frame
        # #############################################################################################################
        # Drill is corners
        self.drills_label = FCLabel('<span style="color:brown;"><b>%s</b></span>' % _('Drills in Locations'))
        self.tools_box.addWidget(self.drills_label)

        self.drill_frame = FCFrame()
        self.tools_box.addWidget(self.drill_frame)

        # Grid Layout
        grid_drill = FCGridLayout(v_spacing=5, h_spacing=3)
        self.drill_frame.setLayout(grid_drill)

        # Drill Tooldia #
        self.drill_dia_label = FCLabel('%s:' % _("Drill Dia"))
        self.drill_dia_label.setToolTip(
            '%s.' % _("Drill Diameter")
        )
        self.drill_dia_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.drill_dia_entry.set_range(0.0000, 100.0000)
        self.drill_dia_entry.set_precision(self.decimals)
        self.drill_dia_entry.setWrapping(True)

        grid_drill.addWidget(self.drill_dia_label, 0, 0)
        grid_drill.addWidget(self.drill_dia_entry, 0, 1)

        FCGridLayout.set_common_column_size([grid_sel, par_grid, grid_loc, grid_drill], 0)

        # ## Create an Excellon object
        self.drill_button = FCButton(_("Create Excellon Object"))
        self.drill_button.setIcon(QtGui.QIcon(self.app.resource_location + '/drill32.png'))
        self.drill_button.setToolTip(
            _("Will add drill holes in the center of the markers.")
        )
        self.drill_button.setStyleSheet("""
                                        QPushButton
                                        {
                                            font-weight: bold;
                                        }
                                        """)
        self.tools_box.addWidget(self.drill_button)

        # #############################################################################################################
        # Check in Locations Frame
        # #############################################################################################################
        # Check in corners
        self.check_label = FCLabel('<span style="color:indigo;"><b>%s</b></span>' % _('Check in Locations'))
        self.tools_box.addWidget(self.check_label)

        # ## Create an Excellon object for checking the positioning
        self.check_button = FCButton(_("Create Excellon Object"))
        self.check_button.setIcon(QtGui.QIcon(self.app.resource_location + '/drill32.png'))
        self.check_button.setToolTip(
            _("Will create an Excellon object using a special preprocessor.\n"
              "The spindle will not start and the mounted probe will move to\n"
              "the corner locations, wait for the user interaction and then\n"
              "move to the next location until the last one.")
        )
        self.check_button.setStyleSheet("""
                                        QPushButton
                                        {
                                            font-weight: bold;
                                        }
                                        """)
        self.tools_box.addWidget(self.check_button)

        self.layout.addStretch(1)

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
