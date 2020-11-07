# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtCore, QtGui

from appTool import AppTool
from appGUI.GUIElements import FCDoubleSpinner, EvalEntry, FCCheckBox, OptionalInputSection, FCEntry
from appGUI.GUIElements import FCTable, FCComboBox, RadioSet
from appEditors.AppTextEditor import AppTextEditor

from shapely.geometry import Point
from shapely.geometry.base import *
from shapely.affinity import scale, skew

import math
from datetime import datetime
import logging
from copy import deepcopy

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class ToolCalibration(AppTool):

    def __init__(self, app):
        AppTool.__init__(self, app)

        self.app = app
        self.canvas = self.app.plotcanvas

        self.decimals = self.app.decimals

        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = CalibUI(layout=self.layout, app=self.app)
        self.toolName = self.ui.toolName

        self.mr = None
        self.units = ''

        # here store 4 points to be used for calibration
        self.click_points = [[], [], [], []]

        # store the status of the grid
        self.grid_status_memory = None

        self.target_obj = None

        # if the mouse events are connected to a local method set this True
        self.local_connected = False

        # reference for the tab where to open and view the verification GCode
        self.gcode_editor_tab = None

        # calibrated object
        self.cal_object = None

        # ## Signals
        self.ui.cal_source_radio.activated_custom.connect(self.on_cal_source_radio)
        self.ui.obj_type_combo.currentIndexChanged.connect(self.on_obj_type_combo)
        self.ui.adj_object_type_combo.currentIndexChanged.connect(self.on_adj_obj_type_combo)

        self.ui.start_button.clicked.connect(self.on_start_collect_points)

        self.ui.gcode_button.clicked.connect(self.generate_verification_gcode)
        self.ui.adj_gcode_button.clicked.connect(self.generate_verification_gcode)

        self.ui.generate_factors_button.clicked.connect(self.calculate_factors)

        self.ui.scale_button.clicked.connect(self.on_scale_button)
        self.ui.skew_button.clicked.connect(self.on_skew_button)

        self.ui.cal_button.clicked.connect(self.on_cal_button_click)
        self.ui.reset_button.clicked.connect(self.set_tool_ui)

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolCalibration()")

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

        self.app.ui.notebook.setTabText(2, _("Calibration Tool"))

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Alt+E', **kwargs)

    def set_tool_ui(self):
        self.units = self.app.defaults['units'].upper()

        if self.local_connected is True:
            self.disconnect_cal_events()

        self.ui.bottom_left_coordx_found.set_value(_("Origin"))
        self.ui.bottom_left_coordy_found.set_value(_("Origin"))

        self.reset_calibration_points()

        self.ui.cal_source_radio.set_value(self.app.defaults['tools_cal_calsource'])
        self.ui.travelz_entry.set_value(self.app.defaults['tools_cal_travelz'])
        self.ui.verz_entry.set_value(self.app.defaults['tools_cal_verz'])
        self.ui.zeroz_cb.set_value(self.app.defaults['tools_cal_zeroz'])
        self.ui.toolchangez_entry.set_value(self.app.defaults['tools_cal_toolchangez'])
        self.ui.toolchange_xy_entry.set_value(self.app.defaults['tools_cal_toolchange_xy'])

        self.ui.second_point_radio.set_value(self.app.defaults['tools_cal_sec_point'])

        self.ui.scalex_entry.set_value(1.0)
        self.ui.scaley_entry.set_value(1.0)
        self.ui.skewx_entry.set_value(0.0)
        self.ui.skewy_entry.set_value(0.0)

        # default object selection is Excellon = index_1
        self.ui.obj_type_combo.setCurrentIndex(1)
        self.on_obj_type_combo()

        self.ui.adj_object_type_combo.setCurrentIndex(0)
        self.on_adj_obj_type_combo()
        # self.adj_object_combo.setCurrentIndex(0)

        # calibrated object
        self.cal_object = None

        self.app.inform.emit('%s...' % _("Tool initialized"))

    def on_obj_type_combo(self):
        obj_type = self.ui.obj_type_combo.currentIndex()
        self.ui.object_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        # self.object_combo.setCurrentIndex(0)
        self.ui.object_combo.obj_type = {
            _("Gerber"): "Gerber", _("Excellon"): "Excellon"
        }[self.ui.obj_type_combo.get_value()]

    def on_adj_obj_type_combo(self):
        obj_type = self.ui.adj_object_type_combo.currentIndex()
        self.ui.adj_object_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        # self.adj_object_combo.setCurrentIndex(0)
        self.ui.adj_object_combo.obj_type = {
            _("Gerber"): "Gerber", _("Excellon"): "Excellon", _("Geometry"): "Geometry"
        }[self.ui.adj_object_type_combo.get_value()]

    def on_cal_source_radio(self, val):
        if val == 'object':
            self.ui.obj_type_label.setDisabled(False)
            self.ui.obj_type_combo.setDisabled(False)
            self.ui.object_label.setDisabled(False)
            self.ui.object_combo.setDisabled(False)
        else:
            self.ui.obj_type_label.setDisabled(True)
            self.ui.obj_type_combo.setDisabled(True)
            self.ui.object_label.setDisabled(True)
            self.ui.object_combo.setDisabled(True)

    def on_start_collect_points(self):

        if self.ui.cal_source_radio.get_value() == 'object':
            selection_index = self.ui.object_combo.currentIndex()
            model_index = self.app.collection.index(selection_index, 0, self.ui.object_combo.rootModelIndex())
            try:
                self.target_obj = model_index.internalPointer().obj
            except AttributeError:
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no source FlatCAM object selected..."))
                return

        # disengage the grid snapping since it will be hard to find the drills on grid
        if self.app.ui.grid_snap_btn.isChecked():
            self.grid_status_memory = True
            self.app.ui.grid_snap_btn.trigger()
        else:
            self.grid_status_memory = False

        self.mr = self.canvas.graph_event_connect('mouse_release', self.on_mouse_click_release)

        if self.app.is_legacy is False:
            self.canvas.graph_event_disconnect('mouse_release', self.app.on_mouse_click_release_over_plot)
        else:
            self.canvas.graph_event_disconnect(self.app.mr)

        self.local_connected = True

        self.reset_calibration_points()

        self.app.inform.emit(_("Get First calibration point. Bottom Left..."))

    def on_mouse_click_release(self, event):
        if self.app.is_legacy is False:
            event_pos = event.pos
            right_button = 2
            self.app.event_is_dragging = self.app.event_is_dragging
        else:
            event_pos = (event.xdata, event.ydata)
            right_button = 3
            self.app.event_is_dragging = self.app.ui.popMenu.mouse_is_panning

        pos_canvas = self.canvas.translate_coords(event_pos)

        if event.button == 1:
            click_pt = Point([pos_canvas[0], pos_canvas[1]])

            if self.app.selection_type is not None:
                # delete previous selection shape
                self.app.delete_selection_shape()
                self.app.selection_type = None
            else:
                if self.ui.cal_source_radio.get_value() == 'object':
                    if self.target_obj.kind.lower() == 'excellon':
                        for tool, tool_dict in self.target_obj.tools.items():
                            for geo in tool_dict['solid_geometry']:
                                if click_pt.within(geo):
                                    center_pt = geo.centroid
                                    self.click_points.append(
                                        [
                                            float('%.*f' % (self.decimals, center_pt.x)),
                                            float('%.*f' % (self.decimals, center_pt.y))
                                        ]
                                    )
                                    self.check_points()
                    else:
                        for apid, apid_val in self.target_obj.apertures.items():
                            for geo_el in apid_val['geometry']:
                                if 'solid' in geo_el:
                                    if click_pt.within(geo_el['solid']):
                                        if isinstance(geo_el['follow'], Point):
                                            center_pt = geo_el['solid'].centroid
                                            self.click_points.append(
                                                [
                                                    float('%.*f' % (self.decimals, center_pt.x)),
                                                    float('%.*f' % (self.decimals, center_pt.y))
                                                ]
                                            )
                                            self.check_points()
                else:
                    self.click_points.append(
                        [
                            float('%.*f' % (self.decimals, click_pt.x)),
                            float('%.*f' % (self.decimals, click_pt.y))
                        ]
                    )
                    self.check_points()
        elif event.button == right_button and self.app.event_is_dragging is False:
            if len(self.click_points) != 4:
                self.reset_calibration_points()
                self.disconnect_cal_events()
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled by user request."))

    def check_points(self):
        if len(self.click_points) == 1:
            self.ui.bottom_left_coordx_tgt.set_value(self.click_points[0][0])
            self.ui.bottom_left_coordy_tgt.set_value(self.click_points[0][1])
            self.app.inform.emit(_("Get Second calibration point. Bottom Right (Top Left)..."))
        elif len(self.click_points) == 2:
            self.ui.bottom_right_coordx_tgt.set_value(self.click_points[1][0])
            self.ui.bottom_right_coordy_tgt.set_value(self.click_points[1][1])
            self.app.inform.emit(_("Get Third calibration point. Top Left (Bottom Right)..."))
        elif len(self.click_points) == 3:
            self.ui.top_left_coordx_tgt.set_value(self.click_points[2][0])
            self.ui.top_left_coordy_tgt.set_value(self.click_points[2][1])
            self.app.inform.emit(_("Get Forth calibration point. Top Right..."))
        elif len(self.click_points) == 4:
            self.ui.top_right_coordx_tgt.set_value(self.click_points[3][0])
            self.ui.top_right_coordy_tgt.set_value(self.click_points[3][1])
            self.app.inform.emit('[success] %s' % _("Done."))
            self.disconnect_cal_events()

    def reset_calibration_points(self):
        self.click_points = []

        self.ui.bottom_left_coordx_tgt.set_value('')
        self.ui.bottom_left_coordy_tgt.set_value('')

        self.ui.bottom_right_coordx_tgt.set_value('')
        self.ui.bottom_right_coordy_tgt.set_value('')

        self.ui.top_left_coordx_tgt.set_value('')
        self.ui.top_left_coordy_tgt.set_value('')

        self.ui.top_right_coordx_tgt.set_value('')
        self.ui.top_right_coordy_tgt.set_value('')

        self.ui.bottom_right_coordx_found.set_value('')
        self.ui.bottom_right_coordy_found.set_value('')

        self.ui.top_left_coordx_found.set_value('')
        self.ui.top_left_coordy_found.set_value('')

    def gcode_header(self):
        log.debug("ToolCalibration.gcode_header()")
        time_str = "{:%A, %d %B %Y at %H:%M}".format(datetime.now())

        gcode = '(G-CODE GENERATED BY FLATCAM v%s - www.flatcam.org - Version Date: %s)\n' % \
                (str(self.app.version), str(self.app.version_date)) + '\n'

        gcode += '(Name: ' + _('Verification GCode for FlatCAM Calibration Tool') + ')\n'

        gcode += '(Units: ' + self.units.upper() + ')\n\n'
        gcode += '(Created on ' + time_str + ')\n\n'
        gcode += 'G20\n' if self.units.upper() == 'IN' else 'G21\n'
        gcode += 'G90\n'
        gcode += 'G17\n'
        gcode += 'G94\n\n'
        return gcode

    def close_tab(self):
        for idx in range(self.app.ui.plot_tab_area.count()):
            if self.app.ui.plot_tab_area.tabText(idx) == _("Gcode Viewer"):
                wdg = self.app.ui.plot_tab_area.widget(idx)
                wdg.deleteLater()
                self.app.ui.plot_tab_area.removeTab(idx)

    def generate_verification_gcode(self):
        sec_point = self.ui.second_point_radio.get_value()

        travel_z = '%.*f' % (self.decimals, self.ui.travelz_entry.get_value())
        toolchange_z = '%.*f' % (self.decimals, self.ui.toolchangez_entry.get_value())
        toolchange_xy_temp = self.ui.toolchange_xy_entry.get_value().split(",")
        toolchange_xy = [float(eval(a)) for a in toolchange_xy_temp if a != '']

        verification_z = '%.*f' % (self.decimals, self.ui.verz_entry.get_value())

        if len(self.click_points) != 4:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled. Four points are needed for GCode generation."))
            return 'fail'

        gcode = self.gcode_header()
        if self.ui.zeroz_cb.get_value():
            gcode += 'M5\n'
            gcode += 'G00 Z%s\n' % toolchange_z
            if toolchange_xy:
                gcode += 'G00 X%s Y%s\n' % (toolchange_xy[0], toolchange_xy[1])
            gcode += 'M0\n'
            gcode += 'G01 Z0\n'
            gcode += 'M0\n'
            gcode += 'G00 Z%s\n' % toolchange_z
            gcode += 'M0\n'

        # first point: bottom - left -> ORIGIN set
        gcode += 'G00 Z%s\n' % travel_z
        gcode += 'G00 X%s Y%s\n' % (self.click_points[0][0], self.click_points[0][1])
        gcode += 'G01 Z%s\n' % verification_z
        gcode += 'M0\n'

        if sec_point == 'tl':
            # second point: top - left -> align the PCB to this point
            gcode += 'G00 Z%s\n' % travel_z
            gcode += 'G00 X%s Y%s\n' % (self.click_points[2][0], self.click_points[2][1])
            gcode += 'G01 Z%s\n' % verification_z
            gcode += 'M0\n'

            # third point: bottom - right -> check for scale on X axis or for skew on Y axis
            gcode += 'G00 Z%s\n' % travel_z
            gcode += 'G00 X%s Y%s\n' % (self.click_points[1][0], self.click_points[1][1])
            gcode += 'G01 Z%s\n' % verification_z
            gcode += 'M0\n'

            # forth point: top - right -> verification point
            gcode += 'G00 Z%s\n' % travel_z
            gcode += 'G00 X%s Y%s\n' % (self.click_points[3][0], self.click_points[3][1])
            gcode += 'G01 Z%s\n' % verification_z
            gcode += 'M0\n'
        else:
            # second point: bottom - right -> align the PCB to this point
            gcode += 'G00 Z%s\n' % travel_z
            gcode += 'G00 X%s Y%s\n' % (self.click_points[1][0], self.click_points[1][1])
            gcode += 'G01 Z%s\n' % verification_z
            gcode += 'M0\n'

            # third point: top - left -> check for scale on Y axis or for skew on X axis
            gcode += 'G00 Z%s\n' % travel_z
            gcode += 'G00 X%s Y%s\n' % (self.click_points[2][0], self.click_points[2][1])
            gcode += 'G01 Z%s\n' % verification_z
            gcode += 'M0\n'

            # forth point: top - right -> verification point
            gcode += 'G00 Z%s\n' % travel_z
            gcode += 'G00 X%s Y%s\n' % (self.click_points[3][0], self.click_points[3][1])
            gcode += 'G01 Z%s\n' % verification_z
            gcode += 'M0\n'

        # return to (toolchange_xy[0], toolchange_xy[1], toolchange_z) point for toolchange event
        gcode += 'G00 Z%s\n' % travel_z
        gcode += 'G00 X0 Y0\n'
        gcode += 'G00 Z%s\n' % toolchange_z
        if toolchange_xy:
            gcode += 'G00 X%s Y%s\n' % (toolchange_xy[0], toolchange_xy[1])

        gcode += 'M2'

        self.gcode_editor_tab = AppTextEditor(app=self.app, plain_text=True)

        # add the tab if it was closed
        self.app.ui.plot_tab_area.addTab(self.gcode_editor_tab, '%s' % _("Gcode Viewer"))
        self.gcode_editor_tab.setObjectName('gcode_viewer_tab')

        # delete the absolute and relative position and messages in the infobar
        self.app.ui.position_label.setText("")
        self.app.ui.rel_position_label.setText("")

        self.gcode_editor_tab.code_editor.completer_enable = False
        self.gcode_editor_tab.buttonRun.hide()

        # Switch plot_area to CNCJob tab
        self.app.ui.plot_tab_area.setCurrentWidget(self.gcode_editor_tab)

        self.gcode_editor_tab.t_frame.hide()
        # then append the text from GCode to the text editor
        try:
            self.gcode_editor_tab.load_text(gcode, move_to_start=True, clear_text=True)
        except Exception as e:
            self.app.inform.emit('[ERROR] %s %s' % ('ERROR -->', str(e)))
            return

        self.gcode_editor_tab.t_frame.show()
        self.app.proc_container.view.set_idle()

        self.app.inform.emit('[success] %s...' % _('Loaded Machine Code into Code Editor'))

        _filter_ = "G-Code Files (*.nc);;All Files (*.*)"
        self.gcode_editor_tab.buttonSave.clicked.disconnect()
        self.gcode_editor_tab.buttonSave.clicked.connect(
            lambda: self.gcode_editor_tab.handleSaveGCode(name='fc_ver_gcode', filt=_filter_, callback=self.close_tab))

    def calculate_factors(self):
        origin_x = self.click_points[0][0]
        origin_y = self.click_points[0][1]

        top_left_x = self.click_points[2][0]
        top_left_y = self.click_points[2][1]

        bot_right_x = self.click_points[1][0]
        bot_right_y = self.click_points[1][1]

        try:
            top_left_dx = float(self.ui.top_left_coordx_found.get_value())
        except TypeError:
            top_left_dx = top_left_x

        try:
            top_left_dy = float(self.ui.top_left_coordy_found.get_value())
        except TypeError:
            top_left_dy = top_left_y

        try:
            bot_right_dx = float(self.ui.bottom_right_coordx_found.get_value())
        except TypeError:
            bot_right_dx = bot_right_x

        try:
            bot_right_dy = float(self.ui.bottom_right_coordy_found.get_value())
        except TypeError:
            bot_right_dy = bot_right_y

        # ------------------------------------------------------------------------------- #
        # --------------------------- FACTORS CALCULUS ---------------------------------- #
        # ------------------------------------------------------------------------------- #
        if bot_right_dx != float('%.*f' % (self.decimals, bot_right_x)):
            # we have scale on X
            scale_x = (bot_right_dx / (bot_right_x - origin_x)) + 1
            self.ui.scalex_entry.set_value(scale_x)

        if top_left_dy != float('%.*f' % (self.decimals, top_left_y)):
            # we have scale on Y
            scale_y = (top_left_dy / (top_left_y - origin_y)) + 1
            self.ui.scaley_entry.set_value(scale_y)

        if top_left_dx != float('%.*f' % (self.decimals, top_left_x)):
            # we have skew on X
            dx = top_left_dx
            dy = top_left_y - origin_y
            skew_angle_x = math.degrees(math.atan(dx / dy))
            self.ui.skewx_entry.set_value(skew_angle_x)

        if bot_right_dy != float('%.*f' % (self.decimals, bot_right_y)):
            # we have skew on Y
            dx = bot_right_x - origin_x
            dy = bot_right_dy + origin_y
            skew_angle_y = math.degrees(math.atan(dy / dx))
            self.ui.skewy_entry.set_value(skew_angle_y)

    @property
    def target_values_in_table(self):
        self.click_points[0][0] = self.ui.bottom_left_coordx_tgt.get_value()
        self.click_points[0][1] = self.ui.bottom_left_coordy_tgt.get_value()

        self.click_points[1][0] = self.ui.bottom_right_coordx_tgt.get_value()
        self.click_points[1][1] = self.ui.bottom_right_coordy_tgt.get_value()

        self.click_points[2][0] = self.ui.top_left_coordx_tgt.get_value()
        self.click_points[2][1] = self.ui.top_left_coordy_tgt.get_value()

        self.click_points[3][0] = self.ui.top_right_coordx_tgt.get_value()
        self.click_points[3][1] = self.ui.top_right_coordy_tgt.get_value()

        return self.click_points

    @target_values_in_table.setter
    def target_values_in_table(self, param):
        bl_pt, br_pt, tl_pt, tr_pt = param

        self.click_points[0] = [bl_pt[0], bl_pt[1]]
        self.click_points[1] = [br_pt[0], br_pt[1]]
        self.click_points[2] = [tl_pt[0], tl_pt[1]]
        self.click_points[3] = [tr_pt[0], tr_pt[1]]

        self.ui.bottom_left_coordx_tgt.set_value(float('%.*f' % (self.decimals, bl_pt[0])))
        self.ui.bottom_left_coordy_tgt.set_value(float('%.*f' % (self.decimals, bl_pt[1])))

        self.ui.bottom_right_coordx_tgt.set_value(float('%.*f' % (self.decimals, br_pt[0])))
        self.ui.bottom_right_coordy_tgt.set_value(float('%.*f' % (self.decimals, br_pt[1])))

        self.ui.top_left_coordx_tgt.set_value(float('%.*f' % (self.decimals, tl_pt[0])))
        self.ui.top_left_coordy_tgt.set_value(float('%.*f' % (self.decimals, tl_pt[1])))

        self.ui.top_right_coordx_tgt.set_value(float('%.*f' % (self.decimals, tr_pt[0])))
        self.ui.top_right_coordy_tgt.set_value(float('%.*f' % (self.decimals, tr_pt[1])))

    def on_scale_button(self):
        scalex_fact = self.ui.scalex_entry.get_value()
        scaley_fact = self.ui.scaley_entry.get_value()
        bl, br, tl, tr = self.target_values_in_table

        bl_geo = Point(bl[0], bl[1])
        br_geo = Point(br[0], br[1])
        tl_geo = Point(tl[0], tl[1])
        tr_geo = Point(tr[0], tr[1])

        bl_scaled = scale(bl_geo, xfact=scalex_fact, yfact=scaley_fact, origin=(bl[0], bl[1]))
        br_scaled = scale(br_geo, xfact=scalex_fact, yfact=scaley_fact, origin=(bl[0], bl[1]))
        tl_scaled = scale(tl_geo, xfact=scalex_fact, yfact=scaley_fact, origin=(bl[0], bl[1]))
        tr_scaled = scale(tr_geo, xfact=scalex_fact, yfact=scaley_fact, origin=(bl[0], bl[1]))

        scaled_values = [
            [bl_scaled.x, bl_scaled.y],
            [br_scaled.x, br_scaled.y],
            [tl_scaled.x, tl_scaled.y],
            [tr_scaled.x, tr_scaled.y]
        ]
        self.target_values_in_table = scaled_values

    def on_skew_button(self):
        skewx_angle = self.ui.skewx_entry.get_value()
        skewy_angle = self.ui.skewy_entry.get_value()
        bl, br, tl, tr = self.target_values_in_table

        bl_geo = Point(bl[0], bl[1])
        br_geo = Point(br[0], br[1])
        tl_geo = Point(tl[0], tl[1])
        tr_geo = Point(tr[0], tr[1])

        bl_skewed = skew(bl_geo, xs=skewx_angle, ys=skewy_angle, origin=(bl[0], bl[1]))
        br_skewed = skew(br_geo, xs=skewx_angle, ys=skewy_angle, origin=(bl[0], bl[1]))
        tl_skewed = skew(tl_geo, xs=skewx_angle, ys=skewy_angle, origin=(bl[0], bl[1]))
        tr_skewed = skew(tr_geo, xs=skewx_angle, ys=skewy_angle, origin=(bl[0], bl[1]))

        skewed_values = [
            [bl_skewed.x, bl_skewed.y],
            [br_skewed.x, br_skewed.y],
            [tl_skewed.x, tl_skewed.y],
            [tr_skewed.x, tr_skewed.y]
        ]
        self.target_values_in_table = skewed_values

    def on_cal_button_click(self):
        # get the FlatCAM object to calibrate
        selection_index = self.ui.adj_object_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.ui.adj_object_combo.rootModelIndex())

        try:
            self.cal_object = model_index.internalPointer().obj
        except Exception as e:
            log.debug("ToolCalibration.on_cal_button_click() --> %s" % str(e))
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("No object is selected."))
            return 'fail'

        obj_name = self.cal_object.options["name"] + "_calibrated"

        self.app.worker_task.emit({'fcn': self.new_calibrated_object, 'params': [obj_name]})

    def new_calibrated_object(self, obj_name):

        try:
            origin_x = self.click_points[0][0]
            origin_y = self.click_points[0][1]
        except IndexError as e:
            log.debug("ToolCalibration.new_calibrated_object() --> %s" % str(e))
            return 'fail'

        scalex = self.ui.scalex_entry.get_value()
        scaley = self.ui.scaley_entry.get_value()

        skewx = self.ui.skewx_entry.get_value()
        skewy = self.ui.skewy_entry.get_value()

        # create a new object adjusted (calibrated)
        def initialize_geometry(obj_init, app):
            obj_init.solid_geometry = deepcopy(obj.solid_geometry)
            try:
                obj_init.follow_geometry = deepcopy(obj.follow_geometry)
            except AttributeError:
                pass

            try:
                obj_init.apertures = deepcopy(obj.apertures)
            except AttributeError:
                pass

            try:
                if obj.tools:
                    obj_init.tools = deepcopy(obj.tools)
            except Exception as ee:
                app.log.debug("ToolCalibration.new_calibrated_object.initialize_geometry() --> %s" % str(ee))

            obj_init.scale(xfactor=scalex, yfactor=scaley, point=(origin_x, origin_y))
            obj_init.skew(angle_x=skewx, angle_y=skewy, point=(origin_x, origin_y))

            try:
                obj_init.source_file = deepcopy(obj.source_file)
            except (AttributeError, TypeError):
                pass

        def initialize_gerber(obj_init, app_obj):
            obj_init.solid_geometry = deepcopy(obj.solid_geometry)
            try:
                obj_init.follow_geometry = deepcopy(obj.follow_geometry)
            except AttributeError:
                pass

            try:
                obj_init.apertures = deepcopy(obj.apertures)
            except AttributeError:
                pass

            try:
                if obj.tools:
                    obj_init.tools = deepcopy(obj.tools)
            except Exception as err:
                log.debug("ToolCalibration.new_calibrated_object.initialize_gerber() --> %s" % str(err))

            obj_init.scale(xfactor=scalex, yfactor=scaley, point=(origin_x, origin_y))
            obj_init.skew(angle_x=skewx, angle_y=skewy, point=(origin_x, origin_y))

            try:
                obj_init.source_file = app_obj.f_handlers.export_gerber(obj_name=obj_name, filename=None,
                                                                        local_use=obj_init, use_thread=False)
            except (AttributeError, TypeError):
                pass

        def initialize_excellon(obj_init, app_obj):
            obj_init.tools = deepcopy(obj.tools)

            # drills are offset, so they need to be deep copied
            obj_init.drills = deepcopy(obj.drills)
            # slots are offset, so they need to be deep copied
            obj_init.slots = deepcopy(obj.slots)

            obj_init.scale(xfactor=scalex, yfactor=scaley, point=(origin_x, origin_y))
            obj_init.skew(angle_x=skewx, angle_y=skewy, point=(origin_x, origin_y))

            obj_init.create_geometry()

            obj_init.source_file = app_obj.f_handlers.export_excellon(obj_name=obj_name, local_use=obj, filename=None,
                                                                      use_thread=False)

        obj = self.cal_object
        obj_name = obj_name

        if obj is None:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("No object is selected."))
            log.debug("ToolCalibration.new_calibrated_object() --> No object to calibrate")
            return 'fail'

        try:
            if obj.kind.lower() == 'excellon':
                self.app.app_obj.new_object("excellon", str(obj_name), initialize_excellon)
            elif obj.kind.lower() == 'gerber':
                self.app.app_obj.new_object("gerber", str(obj_name), initialize_gerber)
            elif obj.kind.lower() == 'geometry':
                self.app.app_obj.new_object("geometry", str(obj_name), initialize_geometry)
        except Exception as e:
            log.debug("ToolCalibration.new_calibrated_object() --> %s" % str(e))
            return "Operation failed: %s" % str(e)

    def disconnect_cal_events(self):
        # restore the Grid snapping if it was active before
        if self.grid_status_memory is True:
            self.app.ui.grid_snap_btn.trigger()

        self.app.mr = self.canvas.graph_event_connect('mouse_release', self.app.on_mouse_click_release_over_plot)

        if self.app.is_legacy is False:
            self.canvas.graph_event_disconnect('mouse_release', self.on_mouse_click_release)
        else:
            self.canvas.graph_event_disconnect(self.mr)

        self.local_connected = False

    def reset_fields(self):
        self.ui.object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.ui.adj_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))


class CalibUI:

    toolName = _("Calibration Tool")

    def __init__(self, layout, app):
        self.app = app
        self.decimals = self.app.decimals
        self.layout = layout

        # ## Title
        title_label = QtWidgets.QLabel("%s" % self.toolName)
        title_label.setStyleSheet("""
                                QLabel
                                {
                                    font-size: 16px;
                                    font-weight: bold;
                                }
                                """)
        self.layout.addWidget(title_label)

        self.layout.addWidget(QtWidgets.QLabel(""))

        # ## Grid Layout
        grid_lay = QtWidgets.QGridLayout()
        self.layout.addLayout(grid_lay)
        grid_lay.setColumnStretch(0, 0)
        grid_lay.setColumnStretch(1, 1)
        grid_lay.setColumnStretch(2, 0)

        self.gcode_title_label = QtWidgets.QLabel('<b>%s:</b>' % _('Parameters'))
        self.gcode_title_label.setToolTip(
            _("Parameters used when creating the GCode in this tool.")
        )
        grid_lay.addWidget(self.gcode_title_label, 0, 0, 1, 3)

        # Travel Z entry
        travelz_lbl = QtWidgets.QLabel('%s:' % _("Travel Z"))
        travelz_lbl.setToolTip(
            _("Height (Z) for travelling between the points.")
        )

        self.travelz_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.travelz_entry.set_range(-10000.0000, 10000.0000)
        self.travelz_entry.set_precision(self.decimals)
        self.travelz_entry.setSingleStep(0.1)

        grid_lay.addWidget(travelz_lbl, 1, 0)
        grid_lay.addWidget(self.travelz_entry, 1, 1, 1, 2)

        # Verification Z entry
        verz_lbl = QtWidgets.QLabel('%s:' % _("Verification Z"))
        verz_lbl.setToolTip(
            _("Height (Z) for checking the point.")
        )

        self.verz_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.verz_entry.set_range(-10000.0000, 10000.0000)
        self.verz_entry.set_precision(self.decimals)
        self.verz_entry.setSingleStep(0.1)

        grid_lay.addWidget(verz_lbl, 2, 0)
        grid_lay.addWidget(self.verz_entry, 2, 1, 1, 2)

        # Zero the Z of the verification tool
        self.zeroz_cb = FCCheckBox('%s' % _("Zero Z tool"))
        self.zeroz_cb.setToolTip(
            _("Include a sequence to zero the height (Z)\n"
              "of the verification tool.")
        )

        grid_lay.addWidget(self.zeroz_cb, 3, 0, 1, 3)

        # Toolchange Z entry
        toolchangez_lbl = QtWidgets.QLabel('%s:' % _("Toolchange Z"))
        toolchangez_lbl.setToolTip(
            _("Height (Z) for mounting the verification probe.")
        )

        self.toolchangez_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.toolchangez_entry.set_range(0.0000, 10000.0000)
        self.toolchangez_entry.set_precision(self.decimals)
        self.toolchangez_entry.setSingleStep(0.1)

        grid_lay.addWidget(toolchangez_lbl, 4, 0)
        grid_lay.addWidget(self.toolchangez_entry, 4, 1, 1, 2)

        # Toolchange X-Y entry
        toolchangexy_lbl = QtWidgets.QLabel('%s:' % _('Toolchange X-Y'))
        toolchangexy_lbl.setToolTip(
            _("Toolchange X,Y position.\n"
              "If no value is entered then the current\n"
              "(x, y) point will be used,")
        )

        self.toolchange_xy_entry = FCEntry()

        grid_lay.addWidget(toolchangexy_lbl, 5, 0)
        grid_lay.addWidget(self.toolchange_xy_entry, 5, 1, 1, 2)

        self.z_ois = OptionalInputSection(
            self.zeroz_cb,
            [
                toolchangez_lbl,
                self.toolchangez_entry,
                toolchangexy_lbl,
                self.toolchange_xy_entry
            ]
        )

        separator_line1 = QtWidgets.QFrame()
        separator_line1.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line1.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line1, 6, 0, 1, 3)

        # Second point choice
        second_point_lbl = QtWidgets.QLabel('%s:' % _("Second point"))
        second_point_lbl.setToolTip(
            _("Second point in the Gcode verification can be:\n"
              "- top-left -> the user will align the PCB vertically\n"
              "- bottom-right -> the user will align the PCB horizontally")
        )
        self.second_point_radio = RadioSet([{'label': _('Top Left'), 'value': 'tl'},
                                            {'label': _('Bottom Right'), 'value': 'br'}],
                                           orientation='vertical')

        grid_lay.addWidget(second_point_lbl, 7, 0)
        grid_lay.addWidget(self.second_point_radio, 7, 1, 1, 2)

        separator_line1 = QtWidgets.QFrame()
        separator_line1.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line1.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line1, 8, 0, 1, 3)

        grid_lay.addWidget(QtWidgets.QLabel(''), 9, 0, 1, 3)

        step_1 = QtWidgets.QLabel('<b>%s</b>' % _("STEP 1: Acquire Calibration Points"))
        step_1.setToolTip(
            _("Pick four points by clicking on canvas.\n"
              "Those four points should be in the four\n"
              "(as much as possible) corners of the object.")
        )
        grid_lay.addWidget(step_1, 10, 0, 1, 3)

        self.cal_source_lbl = QtWidgets.QLabel("<b>%s:</b>" % _("Source Type"))
        self.cal_source_lbl.setToolTip(_("The source of calibration points.\n"
                                         "It can be:\n"
                                         "- Object -> click a hole geo for Excellon or a pad for Gerber\n"
                                         "- Free -> click freely on canvas to acquire the calibration points"))
        self.cal_source_radio = RadioSet([{'label': _('Object'), 'value': 'object'},
                                          {'label': _('Free'), 'value': 'free'}],
                                         stretch=False)

        grid_lay.addWidget(self.cal_source_lbl, 11, 0)
        grid_lay.addWidget(self.cal_source_radio, 11, 1, 1, 2)

        self.obj_type_label = QtWidgets.QLabel("%s:" % _("Object Type"))

        self.obj_type_combo = FCComboBox()
        self.obj_type_combo.addItem(_("Gerber"))
        self.obj_type_combo.addItem(_("Excellon"))

        self.obj_type_combo.setItemIcon(0, QtGui.QIcon(self.app.resource_location + "/flatcam_icon16.png"))
        self.obj_type_combo.setItemIcon(1, QtGui.QIcon(self.app.resource_location + "/drill16.png"))

        grid_lay.addWidget(self.obj_type_label, 12, 0)
        grid_lay.addWidget(self.obj_type_combo, 12, 1, 1, 2)

        self.object_combo = FCComboBox()
        self.object_combo.setModel(self.app.collection)
        self.object_combo.setRootModelIndex(self.app.collection.index(1, 0, QtCore.QModelIndex()))
        self.object_combo.is_last = True

        self.object_label = QtWidgets.QLabel("%s:" % _("Source object selection"))
        self.object_label.setToolTip(
            _("FlatCAM Object to be used as a source for reference points.")
        )

        grid_lay.addWidget(self.object_label, 13, 0, 1, 3)
        grid_lay.addWidget(self.object_combo, 14, 0, 1, 3)

        self.points_table_label = QtWidgets.QLabel('<b>%s</b>' % _('Calibration Points'))
        self.points_table_label.setToolTip(
            _("Contain the expected calibration points and the\n"
              "ones measured.")
        )
        grid_lay.addWidget(self.points_table_label, 15, 0, 1, 3)

        self.points_table = FCTable()
        self.points_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        # self.points_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        grid_lay.addWidget(self.points_table, 16, 0, 1, 3)

        self.points_table.setColumnCount(4)
        self.points_table.setHorizontalHeaderLabels(
            [
                '#',
                _("Name"),
                _("Target"),
                _("Found Delta")
            ]
        )
        self.points_table.setRowCount(8)
        row = 0

        # BOTTOM LEFT
        id_item_1 = QtWidgets.QTableWidgetItem('%d' % 1)
        flags = QtCore.Qt.ItemIsEnabled
        id_item_1.setFlags(flags)
        self.points_table.setItem(row, 0, id_item_1)  # Tool name/id

        self.bottom_left_coordx_lbl = QtWidgets.QLabel('%s' % _('Bot Left X'))
        self.points_table.setCellWidget(row, 1, self.bottom_left_coordx_lbl)
        self.bottom_left_coordx_tgt = EvalEntry()
        self.points_table.setCellWidget(row, 2, self.bottom_left_coordx_tgt)
        self.bottom_left_coordx_tgt.setReadOnly(True)
        self.bottom_left_coordx_found = EvalEntry()
        self.points_table.setCellWidget(row, 3, self.bottom_left_coordx_found)
        row += 1

        self.bottom_left_coordy_lbl = QtWidgets.QLabel('%s' % _('Bot Left Y'))
        self.points_table.setCellWidget(row, 1, self.bottom_left_coordy_lbl)
        self.bottom_left_coordy_tgt = EvalEntry()
        self.points_table.setCellWidget(row, 2, self.bottom_left_coordy_tgt)
        self.bottom_left_coordy_tgt.setReadOnly(True)
        self.bottom_left_coordy_found = EvalEntry()
        self.points_table.setCellWidget(row, 3, self.bottom_left_coordy_found)

        self.bottom_left_coordx_found.setDisabled(True)
        self.bottom_left_coordy_found.setDisabled(True)
        row += 1

        # BOTTOM RIGHT
        id_item_2 = QtWidgets.QTableWidgetItem('%d' % 2)
        flags = QtCore.Qt.ItemIsEnabled
        id_item_2.setFlags(flags)
        self.points_table.setItem(row, 0, id_item_2)  # Tool name/id

        self.bottom_right_coordx_lbl = QtWidgets.QLabel('%s' % _('Bot Right X'))
        self.points_table.setCellWidget(row, 1, self.bottom_right_coordx_lbl)
        self.bottom_right_coordx_tgt = EvalEntry()
        self.points_table.setCellWidget(row, 2, self.bottom_right_coordx_tgt)
        self.bottom_right_coordx_tgt.setReadOnly(True)
        self.bottom_right_coordx_found = EvalEntry()
        self.points_table.setCellWidget(row, 3, self.bottom_right_coordx_found)

        row += 1

        self.bottom_right_coordy_lbl = QtWidgets.QLabel('%s' % _('Bot Right Y'))
        self.points_table.setCellWidget(row, 1, self.bottom_right_coordy_lbl)
        self.bottom_right_coordy_tgt = EvalEntry()
        self.points_table.setCellWidget(row, 2, self.bottom_right_coordy_tgt)
        self.bottom_right_coordy_tgt.setReadOnly(True)
        self.bottom_right_coordy_found = EvalEntry()
        self.points_table.setCellWidget(row, 3, self.bottom_right_coordy_found)
        row += 1

        # TOP LEFT
        id_item_3 = QtWidgets.QTableWidgetItem('%d' % 3)
        flags = QtCore.Qt.ItemIsEnabled
        id_item_3.setFlags(flags)
        self.points_table.setItem(row, 0, id_item_3)  # Tool name/id

        self.top_left_coordx_lbl = QtWidgets.QLabel('%s' % _('Top Left X'))
        self.points_table.setCellWidget(row, 1, self.top_left_coordx_lbl)
        self.top_left_coordx_tgt = EvalEntry()
        self.points_table.setCellWidget(row, 2, self.top_left_coordx_tgt)
        self.top_left_coordx_tgt.setReadOnly(True)
        self.top_left_coordx_found = EvalEntry()
        self.points_table.setCellWidget(row, 3, self.top_left_coordx_found)
        row += 1

        self.top_left_coordy_lbl = QtWidgets.QLabel('%s' % _('Top Left Y'))
        self.points_table.setCellWidget(row, 1, self.top_left_coordy_lbl)
        self.top_left_coordy_tgt = EvalEntry()
        self.points_table.setCellWidget(row, 2, self.top_left_coordy_tgt)
        self.top_left_coordy_tgt.setReadOnly(True)
        self.top_left_coordy_found = EvalEntry()
        self.points_table.setCellWidget(row, 3, self.top_left_coordy_found)
        row += 1

        # TOP RIGHT
        id_item_4 = QtWidgets.QTableWidgetItem('%d' % 4)
        flags = QtCore.Qt.ItemIsEnabled
        id_item_4.setFlags(flags)
        self.points_table.setItem(row, 0, id_item_4)  # Tool name/id

        self.top_right_coordx_lbl = QtWidgets.QLabel('%s' % _('Top Right X'))
        self.points_table.setCellWidget(row, 1, self.top_right_coordx_lbl)
        self.top_right_coordx_tgt = EvalEntry()
        self.points_table.setCellWidget(row, 2, self.top_right_coordx_tgt)
        self.top_right_coordx_tgt.setReadOnly(True)
        self.top_right_coordx_found = EvalEntry()
        self.top_right_coordx_found.setDisabled(True)
        self.points_table.setCellWidget(row, 3, self.top_right_coordx_found)
        row += 1

        self.top_right_coordy_lbl = QtWidgets.QLabel('%s' % _('Top Right Y'))
        self.points_table.setCellWidget(row, 1, self.top_right_coordy_lbl)
        self.top_right_coordy_tgt = EvalEntry()
        self.points_table.setCellWidget(row, 2, self.top_right_coordy_tgt)
        self.top_right_coordy_tgt.setReadOnly(True)
        self.top_right_coordy_found = EvalEntry()
        self.top_right_coordy_found.setDisabled(True)
        self.points_table.setCellWidget(row, 3, self.top_right_coordy_found)

        vertical_header = self.points_table.verticalHeader()
        vertical_header.hide()
        self.points_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        horizontal_header = self.points_table.horizontalHeader()
        horizontal_header.setMinimumSectionSize(10)
        horizontal_header.setDefaultSectionSize(70)

        self.points_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        # for x in range(4):
        #     self.points_table.resizeColumnToContents(x)
        self.points_table.resizeColumnsToContents()
        self.points_table.resizeRowsToContents()

        horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(0, 20)
        horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        horizontal_header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        horizontal_header.setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)

        self.points_table.setMinimumHeight(self.points_table.getHeight() + 2)
        self.points_table.setMaximumHeight(self.points_table.getHeight() + 3)

        # ## Get Points Button
        self.start_button = QtWidgets.QPushButton(_("Get Points"))
        self.start_button.setToolTip(
            _("Pick four points by clicking on canvas if the source choice\n"
              "is 'free' or inside the object geometry if the source is 'object'.\n"
              "Those four points should be in the four squares of\n"
              "the object.")
        )
        self.start_button.setStyleSheet("""
                               QPushButton
                               {
                                   font-weight: bold;
                               }
                               """)
        grid_lay.addWidget(self.start_button, 17, 0, 1, 3)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line, 18, 0, 1, 3)

        grid_lay.addWidget(QtWidgets.QLabel(''), 19, 0)

        # STEP 2 #
        step_2 = QtWidgets.QLabel('<b>%s</b>' % _("STEP 2: Verification GCode"))
        step_2.setToolTip(
            _("Generate GCode file to locate and align the PCB by using\n"
              "the four points acquired above.\n"
              "The points sequence is:\n"
              "- first point -> set the origin\n"
              "- second point -> alignment point. Can be: top-left or bottom-right.\n"
              "- third point -> check point. Can be: top-left or bottom-right.\n"
              "- forth point -> final verification point. Just for evaluation.")
        )
        grid_lay.addWidget(step_2, 20, 0, 1, 3)

        # ## GCode Button
        self.gcode_button = QtWidgets.QPushButton(_("Generate GCode"))
        self.gcode_button.setToolTip(
            _("Generate GCode file to locate and align the PCB by using\n"
              "the four points acquired above.\n"
              "The points sequence is:\n"
              "- first point -> set the origin\n"
              "- second point -> alignment point. Can be: top-left or bottom-right.\n"
              "- third point -> check point. Can be: top-left or bottom-right.\n"
              "- forth point -> final verification point. Just for evaluation.")
        )
        self.gcode_button.setStyleSheet("""
                               QPushButton
                               {
                                   font-weight: bold;
                               }
                               """)
        grid_lay.addWidget(self.gcode_button, 21, 0, 1, 3)

        separator_line1 = QtWidgets.QFrame()
        separator_line1.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line1.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line1, 22, 0, 1, 3)

        grid_lay.addWidget(QtWidgets.QLabel(''), 23, 0, 1, 3)

        # STEP 3 #
        step_3 = QtWidgets.QLabel('<b>%s</b>' % _("STEP 3: Adjustments"))
        step_3.setToolTip(
            _("Calculate Scale and Skew factors based on the differences (delta)\n"
              "found when checking the PCB pattern. The differences must be filled\n"
              "in the fields Found (Delta).")
        )
        grid_lay.addWidget(step_3, 24, 0, 1, 3)

        # ## Factors Button
        self.generate_factors_button = QtWidgets.QPushButton(_("Calculate Factors"))
        self.generate_factors_button.setToolTip(
            _("Calculate Scale and Skew factors based on the differences (delta)\n"
              "found when checking the PCB pattern. The differences must be filled\n"
              "in the fields Found (Delta).")
        )
        self.generate_factors_button.setStyleSheet("""
                               QPushButton
                               {
                                   font-weight: bold;
                               }
                               """)
        grid_lay.addWidget(self.generate_factors_button, 25, 0, 1, 3)

        separator_line1 = QtWidgets.QFrame()
        separator_line1.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line1.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line1, 26, 0, 1, 3)

        grid_lay.addWidget(QtWidgets.QLabel(''), 27, 0, 1, 3)

        # STEP 4 #
        step_4 = QtWidgets.QLabel('<b>%s</b>' % _("STEP 4: Adjusted GCode"))
        step_4.setToolTip(
            _("Generate verification GCode file adjusted with\n"
              "the factors above.")
        )
        grid_lay.addWidget(step_4, 28, 0, 1, 3)

        self.scalex_label = QtWidgets.QLabel(_("Scale Factor X:"))
        self.scalex_label.setToolTip(
            _("Factor for Scale action over X axis.")
        )
        self.scalex_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.scalex_entry.set_range(0, 10000.0000)
        self.scalex_entry.set_precision(self.decimals)
        self.scalex_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.scalex_label, 29, 0)
        grid_lay.addWidget(self.scalex_entry, 29, 1, 1, 2)

        self.scaley_label = QtWidgets.QLabel(_("Scale Factor Y:"))
        self.scaley_label.setToolTip(
            _("Factor for Scale action over Y axis.")
        )
        self.scaley_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.scaley_entry.set_range(0, 10000.0000)
        self.scaley_entry.set_precision(self.decimals)
        self.scaley_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.scaley_label, 30, 0)
        grid_lay.addWidget(self.scaley_entry, 30, 1, 1, 2)

        self.scale_button = QtWidgets.QPushButton(_("Apply Scale Factors"))
        self.scale_button.setToolTip(
            _("Apply Scale factors on the calibration points.")
        )
        self.scale_button.setStyleSheet("""
                                      QPushButton
                                      {
                                          font-weight: bold;
                                      }
                                      """)
        grid_lay.addWidget(self.scale_button, 31, 0, 1, 3)

        self.skewx_label = QtWidgets.QLabel(_("Skew Angle X:"))
        self.skewx_label.setToolTip(
            _("Angle, in degrees.\n"
              "Float number between -360 and 359.")
        )
        self.skewx_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.skewx_entry.set_range(-360, 360)
        self.skewx_entry.set_precision(self.decimals)
        self.skewx_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.skewx_label, 32, 0)
        grid_lay.addWidget(self.skewx_entry, 32, 1, 1, 2)

        self.skewy_label = QtWidgets.QLabel(_("Skew Angle Y:"))
        self.skewy_label.setToolTip(
            _("Angle, in degrees.\n"
              "Float number between -360 and 359.")
        )
        self.skewy_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.skewy_entry.set_range(-360, 360)
        self.skewy_entry.set_precision(self.decimals)
        self.skewy_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.skewy_label, 33, 0)
        grid_lay.addWidget(self.skewy_entry, 33, 1, 1, 2)

        self.skew_button = QtWidgets.QPushButton(_("Apply Skew Factors"))
        self.skew_button.setToolTip(
            _("Apply Skew factors on the calibration points.")
        )
        self.skew_button.setStyleSheet("""
                                      QPushButton
                                      {
                                          font-weight: bold;
                                      }
                                      """)
        grid_lay.addWidget(self.skew_button, 34, 0, 1, 3)

        # final_factors_lbl = QtWidgets.QLabel('<b>%s</b>' % _("Final Factors"))
        # final_factors_lbl.setToolTip(
        #     _("Generate verification GCode file adjusted with\n"
        #       "the factors above.")
        # )
        # grid_lay.addWidget(final_factors_lbl, 27, 0, 1, 3)
        #
        # self.fin_scalex_label = QtWidgets.QLabel(_("Scale Factor X:"))
        # self.fin_scalex_label.setToolTip(
        #     _("Final factor for Scale action over X axis.")
        # )
        # self.fin_scalex_entry = FCDoubleSpinner(callback=self.confirmation_message)
        # self.fin_scalex_entry.set_range(0, 10000.0000)
        # self.fin_scalex_entry.set_precision(self.decimals)
        # self.fin_scalex_entry.setSingleStep(0.1)
        #
        # grid_lay.addWidget(self.fin_scalex_label, 28, 0)
        # grid_lay.addWidget(self.fin_scalex_entry, 28, 1, 1, 2)
        #
        # self.fin_scaley_label = QtWidgets.QLabel(_("Scale Factor Y:"))
        # self.fin_scaley_label.setToolTip(
        #     _("Final factor for Scale action over Y axis.")
        # )
        # self.fin_scaley_entry = FCDoubleSpinner(callback=self.confirmation_message)
        # self.fin_scaley_entry.set_range(0, 10000.0000)
        # self.fin_scaley_entry.set_precision(self.decimals)
        # self.fin_scaley_entry.setSingleStep(0.1)
        #
        # grid_lay.addWidget(self.fin_scaley_label, 29, 0)
        # grid_lay.addWidget(self.fin_scaley_entry, 29, 1, 1, 2)
        #
        # self.fin_skewx_label = QtWidgets.QLabel(_("Skew Angle X:"))
        # self.fin_skewx_label.setToolTip(
        #     _("Final value for angle for Skew action, in degrees.\n"
        #       "Float number between -360 and 359.")
        # )
        # self.fin_skewx_entry = FCDoubleSpinner(callback=self.confirmation_message)
        # self.fin_skewx_entry.set_range(-360, 360)
        # self.fin_skewx_entry.set_precision(self.decimals)
        # self.fin_skewx_entry.setSingleStep(0.1)
        #
        # grid_lay.addWidget(self.fin_skewx_label, 30, 0)
        # grid_lay.addWidget(self.fin_skewx_entry, 30, 1, 1, 2)
        #
        # self.fin_skewy_label = QtWidgets.QLabel(_("Skew Angle Y:"))
        # self.fin_skewy_label.setToolTip(
        #     _("Final value for angle for Skew action, in degrees.\n"
        #       "Float number between -360 and 359.")
        # )
        # self.fin_skewy_entry = FCDoubleSpinner(callback=self.confirmation_message)
        # self.fin_skewy_entry.set_range(-360, 360)
        # self.fin_skewy_entry.set_precision(self.decimals)
        # self.fin_skewy_entry.setSingleStep(0.1)
        #
        # grid_lay.addWidget(self.fin_skewy_label, 31, 0)
        # grid_lay.addWidget(self.fin_skewy_entry, 31, 1, 1, 2)

        # ## Adjusted GCode Button

        self.adj_gcode_button = QtWidgets.QPushButton(_("Generate Adjusted GCode"))
        self.adj_gcode_button.setToolTip(
            _("Generate verification GCode file adjusted with\n"
              "the factors set above.\n"
              "The GCode parameters can be readjusted\n"
              "before clicking this button.")
        )
        self.adj_gcode_button.setStyleSheet("""
                               QPushButton
                               {
                                   font-weight: bold;
                               }
                               """)
        grid_lay.addWidget(self.adj_gcode_button, 42, 0, 1, 3)

        separator_line1 = QtWidgets.QFrame()
        separator_line1.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line1.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line1, 43, 0, 1, 3)

        grid_lay.addWidget(QtWidgets.QLabel(''), 44, 0, 1, 3)

        # STEP 5 #
        step_5 = QtWidgets.QLabel('<b>%s</b>' % _("STEP 5: Calibrate FlatCAM Objects"))
        step_5.setToolTip(
            _("Adjust the FlatCAM objects\n"
              "with the factors determined and verified above.")
        )
        grid_lay.addWidget(step_5, 45, 0, 1, 3)

        self.adj_object_type_combo = FCComboBox()
        self.adj_object_type_combo.addItems([_("Gerber"), _("Excellon"), _("Geometry")])

        self.adj_object_type_combo.setItemIcon(0, QtGui.QIcon(self.app.resource_location + "/flatcam_icon16.png"))
        self.adj_object_type_combo.setItemIcon(1, QtGui.QIcon(self.app.resource_location + "/drill16.png"))
        self.adj_object_type_combo.setItemIcon(2, QtGui.QIcon(self.app.resource_location + "/geometry16.png"))

        self.adj_object_type_label = QtWidgets.QLabel("%s:" % _("Adjusted object type"))
        self.adj_object_type_label.setToolTip(_("Type of the FlatCAM Object to be adjusted."))

        grid_lay.addWidget(self.adj_object_type_label, 46, 0, 1, 3)
        grid_lay.addWidget(self.adj_object_type_combo, 47, 0, 1, 3)

        self.adj_object_combo = FCComboBox()
        self.adj_object_combo.setModel(self.app.collection)
        self.adj_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.adj_object_combo.is_last = True
        self.adj_object_combo.obj_type = {
            _("Gerber"): "Gerber", _("Excellon"): "Excellon", _("Geometry"): "Geometry"
        }[self.adj_object_type_combo.get_value()]

        self.adj_object_label = QtWidgets.QLabel("%s:" % _("Adjusted object selection"))
        self.adj_object_label.setToolTip(
            _("The FlatCAM Object to be adjusted.")
        )

        grid_lay.addWidget(self.adj_object_label, 48, 0, 1, 3)
        grid_lay.addWidget(self.adj_object_combo, 49, 0, 1, 3)

        # ## Adjust Objects Button
        self.cal_button = QtWidgets.QPushButton(_("Calibrate"))
        self.cal_button.setToolTip(
            _("Adjust (scale and/or skew) the objects\n"
              "with the factors determined above.")
        )
        self.cal_button.setStyleSheet("""
                               QPushButton
                               {
                                   font-weight: bold;
                               }
                               """)
        grid_lay.addWidget(self.cal_button, 50, 0, 1, 3)

        separator_line2 = QtWidgets.QFrame()
        separator_line2.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line2.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line2, 51, 0, 1, 3)

        grid_lay.addWidget(QtWidgets.QLabel(''), 52, 0, 1, 3)

        self.layout.addStretch()

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
