# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt6 import QtWidgets, QtCore
from appTool import AppTool
from appGUI.GUIElements import VerticalScrollArea, FCLabel, FCButton, FCFrame, GLay, FCEntry, FCCheckBox
from appGUI.VisPyVisuals import ShapeCollection
from camlib import AppRTreeStorage
from appEditors.AppGeoEditor import DrawToolShape

import math
import logging
from copy import copy
import numpy as np

from shapely import Polygon, Point, LineString, MultiLineString
from shapely.strtree import STRtree

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class Distance(AppTool):

    def __init__(self, app):
        AppTool.__init__(self, app)

        self.app = app
        self.decimals = self.app.decimals

        self.canvas = self.app.plotcanvas
        self.units = self.app.app_units.lower()

        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = DistanceUI(layout=self.layout, app=self.app)
        self.pluginName = self.ui.pluginName

        # store here the first click and second click of the measurement process
        self.points = []

        self.active = False
        self.clicked_meas = None
        self.meas_line = None

        self.original_call_source = 'app'

        # store here the event connection ID's
        self.mm = None
        self.mr = None

        # monitor if the tool was used
        self.tool_done = False

        # holds the key for the last plotted utility shape
        self.last_shape = None

        self.total_distance = 0.0

        # store the grid status here
        self.grid_status_memory = False

        # store here if the snap button was clicked
        self.snap_toggled = None

        self.mouse_is_dragging = False

        # store here the cursor color
        self.cursor_color_memory = None
        # store the current cursor type to be restored after manual geo
        self.old_cursor_type = self.app.options["global_cursor_type"]

        # VisPy visuals
        if self.app.use_3d_engine:
            self.sel_shapes = ShapeCollection(parent=self.app.plotcanvas.view.scene, layers=1, pool=self.app.pool)
        else:
            from appGUI.PlotCanvasLegacy import ShapeCollectionLegacy
            self.sel_shapes = ShapeCollectionLegacy(obj=self, app=self.app, name='measurement')
        
        # Signals
        self.ui.measure_btn.clicked.connect(self.on_start_measuring)
        self.ui.multipoint_cb.stateChanged.connect(self.on_multipoint_measurement_changed)
        self.ui.big_cursor_cb.stateChanged.connect(self.on_cursor_change)

    def run(self, toggle=False):

        if self.app.plugin_tab_locked is True:
            return

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

                        if self.active:
                            self.on_exit()
                        return
            except AttributeError:
                pass

            super().run()
        else:
            if self.app.ui.splitter.sizes()[0] == 0:
                self.app.ui.splitter.setSizes([1, 1])

        self.old_cursor_type = self.app.options["global_cursor_type"]

        self.on_start_measuring() if self.active is False else self.on_exit()

    def init_plugin(self):
        self.points[:] = []
        self.tool_done = False
        self.last_shape = None
        self.total_distance = 0.0

        self.clicked_meas = 0
        self.original_call_source = copy(self.app.call_source)
        self.units = self.app.app_units.lower()

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Ctrl+M', **kwargs)

    def set_tool_ui(self):
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

        self.app.ui.notebook.setTabText(2, _("Distance"))

        # Remove anything else in the appGUI
        self.app.ui.plugin_scroll_area.takeWidget()

        # Put ourselves in the appGUI
        self.app.ui.plugin_scroll_area.setWidget(self)

        # Switch notebook to tool page
        self.app.ui.notebook.setCurrentWidget(self.app.ui.plugin_tab)
        self.units = self.app.app_units.lower()

        self.app.command_active = "Distance"
        self.tool_done = False
        self.grid_status_memory = True if self.app.ui.grid_snap_btn.isChecked() else False

        self.ui.snap_center_cb.set_value(self.app.options['tools_dist_snap_center'])
        self.ui.big_cursor_cb.set_value(self.app.options['tools_dist_big_cursor'])

        snap_center = self.app.options['tools_dist_snap_center']
        self.on_snap_toggled(snap_center)

        try:
            self.ui.snap_center_cb.toggled.disconnect()
        except (AttributeError, TypeError):
            pass
        self.ui.snap_center_cb.toggled.connect(self.on_snap_toggled)

        # this is a hack; seems that triggering the grid will make the visuals better
        # trigger it twice to return to the original state
        self.app.ui.grid_snap_btn.trigger()
        self.app.ui.grid_snap_btn.trigger()

        # initial view of the layout
        self.initial_view()

        if self.ui.big_cursor_cb.get_value():
            self.app.on_cursor_type(val="big", control_cursor=True)
            self.cursor_color_memory = self.app.plotcanvas.cursor_color

            if self.app.options["global_theme"] in ['default', 'light']:
                if self.app.use_3d_engine is True:
                    self.app.plotcanvas.cursor_color = '#000000FF'
                else:
                    self.app.plotcanvas.cursor_color = '#000000'
            else:
                if self.app.use_3d_engine is True:
                    self.app.plotcanvas.cursor_color = '#AAAAAAFF'
                else:
                    self.app.plotcanvas.cursor_color = '#AAAAAA'
            self.app.app_cursor.enabled = True

        self.app.call_source = 'measurement'

    def initial_view(self):
        self.display_start((0.0, 0.0))
        self.display_end((0.0, 0.0))
        self.ui.angle_entry.set_value('%.*f' % (self.decimals, 0.0))
        self.ui.angle2_entry.set_value('%.*f' % (self.decimals, 0.0))
        self.ui.distance_x_entry.set_value('%.*f' % (self.decimals, 0.0))
        self.ui.distance_y_entry.set_value('%.*f' % (self.decimals, 0.0))
        self.ui.total_distance_entry.set_value('%.*f' % (self.decimals, 0.0))

    def on_snap_toggled(self, state):
        self.app.options['tools_dist_snap_center'] = state
        if state:
            # disengage the grid snapping since it will be hard to find the drills or pads on grid
            if self.app.ui.grid_snap_btn.isChecked():
                self.app.ui.grid_snap_btn.trigger()

    def on_start_measuring(self):
        # ENABLE the Measuring TOOL
        self.active = True

        # disable the measuring button
        self.ui.measure_btn.setDisabled(True)
        self.ui.measure_btn.setText('%s...' % _("Working"))

        self.init_plugin()
        self.ui_connect()
        self.set_tool_ui()

        self.app.inform.emit(_("MEASURING: Click on the Start point ..."))

    def ui_connect(self):
        # we can connect the app mouse events to the measurement tool
        # NEVER DISCONNECT THOSE before connecting some other handlers; it breaks something in VisPy
        self.mm = self.canvas.graph_event_connect('mouse_move', self.on_mouse_move)
        self.mr = self.canvas.graph_event_connect('mouse_release', self.on_mouse_click_release)

        # we disconnect the mouse/key handlers from wherever the measurement tool was called
        if self.app.call_source == 'app':
            if self.app.use_3d_engine:
                self.canvas.graph_event_disconnect('mouse_move', self.app.on_mouse_move_over_plot)
                self.canvas.graph_event_disconnect('mouse_press', self.app.on_mouse_click_over_plot)
                self.canvas.graph_event_disconnect('mouse_release', self.app.on_mouse_click_release_over_plot)
            else:
                self.canvas.graph_event_disconnect(self.app.mm)
                self.canvas.graph_event_disconnect(self.app.mp)
                self.canvas.graph_event_disconnect(self.app.mr)

        elif self.app.call_source == 'geo_editor':
            if self.app.use_3d_engine:
                self.canvas.graph_event_disconnect('mouse_move', self.app.geo_editor.on_canvas_move)
                self.canvas.graph_event_disconnect('mouse_press', self.app.geo_editor.on_canvas_click)
                self.canvas.graph_event_disconnect('mouse_release', self.app.geo_editor.on_canvas_click_release)
            else:
                self.canvas.graph_event_disconnect(self.app.geo_editor.mm)
                self.canvas.graph_event_disconnect(self.app.geo_editor.mp)
                self.canvas.graph_event_disconnect(self.app.geo_editor.mr)

        elif self.app.call_source == 'exc_editor':
            if self.app.use_3d_engine:
                self.canvas.graph_event_disconnect('mouse_move', self.app.exc_editor.on_canvas_move)
                self.canvas.graph_event_disconnect('mouse_press', self.app.exc_editor.on_canvas_click)
                self.canvas.graph_event_disconnect('mouse_release', self.app.exc_editor.on_exc_click_release)
            else:
                self.canvas.graph_event_disconnect(self.app.exc_editor.mm)
                self.canvas.graph_event_disconnect(self.app.exc_editor.mp)
                self.canvas.graph_event_disconnect(self.app.exc_editor.mr)

        elif self.app.call_source == 'grb_editor':
            if self.app.use_3d_engine:
                self.canvas.graph_event_disconnect('mouse_move', self.app.grb_editor.on_canvas_move)
                self.canvas.graph_event_disconnect('mouse_press', self.app.grb_editor.on_canvas_click)
                self.canvas.graph_event_disconnect('mouse_release', self.app.grb_editor.on_canvas_click_release)
            else:
                self.canvas.graph_event_disconnect(self.app.grb_editor.mm)
                self.canvas.graph_event_disconnect(self.app.grb_editor.mp)
                self.canvas.graph_event_disconnect(self.app.grb_editor.mr)

    def ui_disconnect(self):
        if self.original_call_source == 'app':
            self.app.mm = self.canvas.graph_event_connect('mouse_move', self.app.on_mouse_move_over_plot)
            self.app.mp = self.canvas.graph_event_connect('mouse_press', self.app.on_mouse_click_over_plot)
            self.app.mr = self.canvas.graph_event_connect('mouse_release', self.app.on_mouse_click_release_over_plot)

        elif self.original_call_source == 'geo_editor':
            self.app.geo_editor.mm = self.canvas.graph_event_connect('mouse_move', self.app.geo_editor.on_canvas_move)
            self.app.geo_editor.mp = self.canvas.graph_event_connect('mouse_press', self.app.geo_editor.on_canvas_click)
            self.app.geo_editor.mr = self.canvas.graph_event_connect('mouse_release',
                                                                     self.app.geo_editor.on_canvas_click_release)

        elif self.original_call_source == 'exc_editor':
            self.app.exc_editor.mm = self.canvas.graph_event_connect('mouse_move', self.app.exc_editor.on_canvas_move)
            self.app.exc_editor.mp = self.canvas.graph_event_connect('mouse_press', self.app.exc_editor.on_canvas_click)
            self.app.exc_editor.mr = self.canvas.graph_event_connect('mouse_release',
                                                                     self.app.exc_editor.on_exc_click_release)

        elif self.original_call_source == 'grb_editor':
            self.app.grb_editor.mm = self.canvas.graph_event_connect('mouse_move', self.app.grb_editor.on_canvas_move)
            self.app.grb_editor.mp = self.canvas.graph_event_connect('mouse_press', self.app.grb_editor.on_canvas_click)
            self.app.grb_editor.mr = self.canvas.graph_event_connect('mouse_release',
                                                                     self.app.grb_editor.on_canvas_click_release)

        # disconnect the mouse/key events from functions of measurement tool
        if self.app.use_3d_engine:
            self.canvas.graph_event_disconnect('mouse_move', self.on_mouse_move)
            self.canvas.graph_event_disconnect('mouse_release', self.on_mouse_click_release)
        else:
            self.canvas.graph_event_disconnect(self.mm)
            self.canvas.graph_event_disconnect(self.mr)

    def on_exit(self):
        # DISABLE the Measuring TOOL
        self.active = False
        self.points = []
        self.last_shape = None
        self.total_distance = 0.0

        # enable the measuring button
        self.ui.measure_btn.setDisabled(False)
        self.ui.measure_btn.setText(_("Measure"))

        self.app.call_source = copy(self.original_call_source)

        self.ui_disconnect()

        self.app.command_active = None

        # delete the measuring line
        self.delete_all_shapes()

        # restore cursor
        self.app.on_cursor_type(val=self.old_cursor_type, control_cursor=False)
        self.app.plotcanvas.cursor_color = self.cursor_color_memory

        # restore the grid status
        if self.app.ui.grid_snap_btn.isChecked() != self.grid_status_memory:
            self.app.ui.grid_snap_btn.trigger()

        if self.tool_done is False:
            self.tool_done = True
            self.app.inform.emit('%s' % _("Done."))

    def calculate_distance(self, pos):
        multipoint = self.ui.multipoint_cb.get_value()

        if multipoint is False:
            if len(self.points) == 1:
                self.ui.start_entry.set_value("(%.*f, %.*f)" % (self.decimals, pos[0], self.decimals, pos[1]))
                self.app.inform.emit(_("Click on the DESTINATION point ..."))
                return

            if len(self.points) == 2:
                self.ui.stop_entry.set_value("(%.*f, %.*f)" % (self.decimals, pos[0], self.decimals, pos[1]))

                dx = self.points[1][0] - self.points[0][0]
                dy = self.points[1][1] - self.points[0][1]
                d = math.sqrt(dx ** 2 + dy ** 2)
                self.ui.total_distance_entry.set_value('%.*f' % (self.decimals, abs(d)))

                self.app.ui.rel_position_label.setText(
                    "<b>Dx</b>: {}&nbsp;&nbsp;  <b>Dy</b>: {}&nbsp;&nbsp;&nbsp;&nbsp;".format(
                        '%.*f' % (self.decimals, pos[0]), '%.*f' % (self.decimals, pos[1])
                    )
                )

                self.tool_done = True
                self.on_exit()
                self.app.inform.emit("[success] %s" % _("Done."))
        else:
            # update utility geometry
            if not self.points:
                self.add_utility_shape(pos)
            else:
                # update utility geometry
                # delete last shape and redd it correctly when using the snap and multipoint
                self.delete_utility_shape(self.last_shape)
                try:
                    self.add_utility_shape(start_pos=self.points[-2], end_pos=self.points[-1])
                except IndexError:
                    pass
                self.add_utility_shape(start_pos=self.points[-1], end_pos=pos)

            if len(self.points) == 1:
                # update start point
                self.ui.start_entry.set_value("(%.*f, %.*f)" % (self.decimals, pos[0], self.decimals, pos[1]))
            elif len(self.points) > 1:
                # update the distance
                self.total_distance += self.update_distance(pos, self.points[-2])
            else:
                self.total_distance += self.update_distance(pos)
            self.display_distance(self.total_distance)
            self.app.inform.emit('%s' % _("Click to add next point or right click to finish."))

    def snap_handler(self, pos):
        current_pt = Point(pos)
        shapes_storage = self.make_storage()

        if self.original_call_source == 'exc_editor':
            for storage in self.app.exc_editor.storage_dict:
                __, st_closest_shape = self.app.exc_editor.storage_dict[storage].nearest(pos)
                shapes_storage.insert(st_closest_shape)

            __, closest_shape = shapes_storage.nearest(pos)

            # if it's a drill
            if isinstance(closest_shape.geo, MultiLineString):
                radius = closest_shape.geo.geoms[0].length / 2.0
                center_pt = closest_shape.geo.centroid

                geo_buffered = center_pt.buffer(radius)

                if current_pt.within(geo_buffered):
                    pos = (center_pt.x, center_pt.y)

            # if it's a slot
            elif isinstance(closest_shape.geo, Polygon):
                geo_buffered = closest_shape.geo.buffer(0)
                center_pt = geo_buffered.centroid

                if current_pt.within(geo_buffered):
                    pos = (center_pt.x, center_pt.y)

        elif self.original_call_source == 'grb_editor':
            clicked_pads = []
            for storage in self.app.grb_editor.storage_dict:
                try:
                    for shape_stored in self.app.grb_editor.storage_dict[storage]['geometry']:
                        if 'solid' in shape_stored.geo:
                            geometric_data = shape_stored.geo['solid']
                            if current_pt.within(geometric_data):
                                if isinstance(shape_stored.geo['follow'], Point):
                                    clicked_pads.append(shape_stored.geo['follow'])
                except KeyError:
                    pass

            if len(clicked_pads) > 1:
                self.tool_done = True
                self.on_exit()
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("Pads overlapped. Aborting."))
                return

            if clicked_pads:
                pos = (clicked_pads[0].x, clicked_pads[0].y)

        elif self.original_call_source == 'app':
            loaded_obj_list = self.app.collection.get_list()
            snapable_obj_list = [o for o in loaded_obj_list if o.kind == 'excellon' or o.kind == 'gerber']
            if not snapable_obj_list:
                return pos

            clicked_geo = []
            for obj in snapable_obj_list:
                if obj.kind == 'gerber':
                    for t in obj.tools:
                        if obj.tools[t]['geometry']:
                            for geo_dict in obj.tools[t]['geometry']:
                                if isinstance(geo_dict['follow'], Point):
                                    if current_pt.within(geo_dict['solid']):
                                        clicked_geo.append(geo_dict['follow'])
                elif obj.kind == 'excellon':
                    for t in obj.tools:
                        if obj.tools[t]['solid_geometry']:
                            for drill_geo in obj.tools[t]['solid_geometry']:
                                if current_pt.within(drill_geo):
                                    clicked_geo.append(drill_geo.centroid)

            if clicked_geo:
                # search for 'pad within pad' or 'drill within drill' situation and choose the closest geo center
                tree = STRtree(clicked_geo)
                closest_pt = tree.nearest(current_pt)
                assert isinstance(closest_pt, Point)
                # snap to the closest geometry in the clicked_geo list
                pos = (closest_pt.x, closest_pt.y)
            else:
                return pos
        else:
            return pos

        self.app.on_jump_to(custom_location=pos, fit_center=False)
        # Update cursor
        self.app.app_cursor.enabled = True
        if self.ui.big_cursor_cb.get_value():
            self.app.on_cursor_type(val="big", control_cursor=True)
            self.cursor_color_memory = self.app.plotcanvas.cursor_color
            if self.app.use_3d_engine is True:
                self.app.plotcanvas.cursor_color = '#000000FF'
            else:
                self.app.plotcanvas.cursor_color = '#000000'

        self.app.app_cursor.set_data(np.asarray([(pos[0], pos[1])]),
                                     symbol='++', edge_color='#000000',
                                     edge_width=self.app.options["global_cursor_width"],
                                     size=self.app.options["global_cursor_size"])
        return pos

    def on_multipoint_measurement_changed(self, val):
        if val:
            self.ui.distance_x_label.setDisabled(True)
            self.ui.distance_x_entry.setDisabled(True)
            self.ui.distance_y_label.setDisabled(True)
            self.ui.distance_y_entry.setDisabled(True)
            self.ui.angle_label.setDisabled(True)
            self.ui.angle_entry.setDisabled(True)
            self.ui.angle2_label.setDisabled(True)
            self.ui.angle2_entry.setDisabled(True)
        else:
            self.ui.distance_x_label.setDisabled(False)
            self.ui.distance_x_entry.setDisabled(False)
            self.ui.distance_y_label.setDisabled(False)
            self.ui.distance_y_entry.setDisabled(False)
            self.ui.angle_label.setDisabled(False)
            self.ui.angle_entry.setDisabled(False)
            self.ui.angle2_label.setDisabled(False)
            self.ui.angle2_entry.setDisabled(False)

    def on_cursor_change(self, val):
        if val:
            self.app.options['tools_dist_big_cursor'] = True
            self.app.on_cursor_type(val="big", control_cursor=True)
        else:
            self.app.options['tools_dist_big_cursor'] = False
            self.app.on_cursor_type(val="small", control_cursor=True)

    def update_position_info(self, pos_canvas):
        big_cursor_state = self.ui.big_cursor_cb.get_value()
        grid_snap_state = self.app.grid_status()

        if big_cursor_state is False:
            if grid_snap_state:
                pos = self.app.geo_editor.snap(pos_canvas[0], pos_canvas[1])
                # Update cursor
                self.app.app_cursor.set_data(np.asarray([(pos[0], pos[1])]),
                                             symbol='++', edge_color=self.app.plotcanvas.cursor_color,
                                             edge_width=self.app.options["global_cursor_width"],
                                             size=self.app.options["global_cursor_size"])
            else:
                pos = (pos_canvas[0], pos_canvas[1])
        else:
            if grid_snap_state:
                pos = self.app.geo_editor.snap(pos_canvas[0], pos_canvas[1])
            else:
                if self.app.app_cursor.enabled is False:
                    self.app.app_cursor.enabled = True
                pos = (pos_canvas[0], pos_canvas[1])
            # Update cursor
            self.app.app_cursor.set_data(np.asarray([(pos[0], pos[1])]),
                                         symbol='++', edge_color=self.app.plotcanvas.cursor_color,
                                         edge_width=self.app.options["global_cursor_width"],
                                         size=self.app.options["global_cursor_size"])

        return pos

    def on_mouse_click_release(self, event):
        # mouse click releases will be accepted only if the left button is clicked
        # this is necessary because right mouse click or middle mouse click
        # are used for panning on the canvas
        # log.debug("Distance Tool --> mouse click release")

        snap_enabled = self.ui.snap_center_cb.get_value()
        multipoint = self.ui.multipoint_cb.get_value()

        if self.app.use_3d_engine:
            event_pos = event.pos
            right_button = 2
            event_is_dragging = self.mouse_is_dragging
        else:
            event_pos = (event.xdata, event.ydata)
            right_button = 3
            event_is_dragging = self.app.plotcanvas.is_dragging

        pos_canvas = self.canvas.translate_coords(event_pos)
        if snap_enabled is False:
            # if GRID is active we need to get the snapped positions
            if self.app.grid_status():
                pos = self.app.geo_editor.snap(pos_canvas[0], pos_canvas[1])
            else:
                pos = pos_canvas[0], pos_canvas[1]
        else:
            pos = self.snap_handler(pos=(pos_canvas[0], pos_canvas[1]))

        if event.button == 1:
            # Reset here the relative coordinates so there is a new reference on the click position
            if len(self.points) == 1:
                self.app.ui.rel_position_label.setText("<b>Dx</b>: %.*f&nbsp;&nbsp;  <b>Dy</b>: "
                                                       "%.*f&nbsp;&nbsp;&nbsp;&nbsp;" %
                                                       (self.decimals, 0.0, self.decimals, 0.0))

            self.points.append(pos)
            self.calculate_distance(pos=pos)
        elif event.button == right_button and event_is_dragging is False:
            if multipoint is False:
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
            else:
                # update end point
                try:
                    end_val = self.update_end_point(self.points[-1])
                except IndexError:
                    end_val = self.update_end_point((0.0, 0.0))
                self.display_end(end_val)
                self.app.inform.emit("[success] %s" % _("Done."))
            self.on_exit()

    def on_mouse_move(self, event):
        multipoint = self.ui.multipoint_cb.get_value()

        try:  # May fail in case mouse not within axes
            if self.app.use_3d_engine:
                event_pos = event.pos
                self.mouse_is_dragging = event.is_dragging
            else:
                event_pos = (event.xdata, event.ydata)

            try:
                x = float(event_pos[0])
                y = float(event_pos[1])
            except TypeError:
                return
            pos_canvas = self.app.plotcanvas.translate_coords((x, y))

            # update position info
            pos = self.update_position_info(pos_canvas)

            # ------------------------------------------------------------
            # Update Status Bar location labels
            # ------------------------------------------------------------
            dx = pos[0]
            dy = pos[1]
            if len(self.points) == 1:
                dx = pos[0] - float(self.points[0][0])
                dy = pos[1] - float(self.points[0][1])
            elif len(self.points) == 2:
                dx = float(self.points[1][0]) - float(self.points[0][0])
                dy = float(self.points[1][1]) - float(self.points[0][1])
            self.app.ui.update_location_labels(dx=dx, dy=dy, x=pos[0], y=pos[1])

            # self.app.ui.update_location_labels(dx=None, dy=None, x=pos[0], y=pos[1])
            self.app.plotcanvas.on_update_text_hud(dx, dy, pos[0], pos[1])

        except Exception as e:
            self.app.log.error("Distance.on_mouse_move() position --> %s" % str(e))
            self.app.ui.update_location_labels(dx=None, dy=None, x=None, y=None)
            self.app.plotcanvas.on_update_text_hud('0.0', '0.0', '0.0', '0.0')
            return

        try:
            if multipoint is False:
                if len(self.points) == 1:
                    # update utility geometry
                    self.delete_all_shapes()
                    self.add_utility_shape(start_pos=pos)
                    # update angle
                    angle_val = self.update_angle(dx=dx, dy=dy)
                    self.display_angle(angle_val)
                    # update end_point
                    end_val = self.update_end_point(pos=pos)
                    self.display_end(end_val)
                    # update deltas
                    deltax, deltay = self.update_deltas(pos=pos)
                    self.display_deltas(deltax, deltay)
                    # update distance
                    dist_val = self.update_distance(pos=pos)
                    self.display_distance(dist_val)
            else:
                # update utility geometry
                self.delete_utility_shape(self.last_shape)
                if self.points:
                    self.add_utility_shape(start_pos=self.points[-1], end_pos=pos)
                    self.display_distance(self.total_distance + self.update_distance(pos, prev_pos=self.points[-1]))
        except Exception as e:
            self.app.log.error("Distance.on_mouse_move() update --> %s" % str(e))
            self.app.ui.position_label.setText("")
            self.app.ui.rel_position_label.setText("")

    def update_angle(self, dx, dy):
        try:
            angle = math.degrees(math.atan2(dy, dx))
            if angle < 0:
                angle += 360
        except Exception as e:
            self.app.log.error("Distance.update_angle() -> %s" % str(e))
            return None
        return angle

    def display_angle(self, val):
        if val is not None:
            self.ui.angle_entry.set_value(str(self.app.dec_format(val, self.decimals)))
            if val > 180:
                val = 360 - val
                val = -val
            self.ui.angle2_entry.set_value(str(self.app.dec_format(val, self.decimals)))

    def display_start(self, val):
        if val:
            self.ui.start_entry.set_value(str(val))

    def update_end_point(self, pos):
        # update the end point value
        end_val = (
            self.app.dec_format(pos[0], self.decimals),
            self.app.dec_format(pos[1], self.decimals)
        )
        return end_val

    def display_end(self, val):
        if val:
            self.ui.stop_entry.set_value(str(val))

    def update_deltas(self, pos):
        dx = pos[0] - self.points[0][0]
        dy = pos[1] - self.points[0][1]
        return dx, dy

    def display_deltas(self, dx, dy):
        if dx:
            self.ui.distance_x_entry.set_value(str(self.app.dec_format(abs(dx), self.decimals)))
        if dy:
            self.ui.distance_y_entry.set_value(str(self.app.dec_format(abs(dy), self.decimals)))

    def update_distance(self, pos, prev_pos=None):
        if prev_pos is None:
            prev_pos = self.points[0]
        dx = pos[0] - prev_pos[0]
        dy = pos[1] - prev_pos[1]
        return math.sqrt(dx ** 2 + dy ** 2)

    def display_distance(self, val):
        if val:
            self.ui.total_distance_entry.set_value('%.*f' % (self.decimals, abs(val)))

    def add_utility_shape(self, start_pos, end_pos=None):
        # draw the new shape of the utility geometry
        if end_pos is None:
            meas_line = LineString([start_pos, self.points[0]])
        else:
            meas_line = LineString([start_pos, end_pos])

        settings = QtCore.QSettings("Open Source", "FlatCAM_EVO")
        if settings.contains("theme"):
            theme = settings.value('theme', type=str)
        else:
            theme = 'default'

        if settings.contains("dark_canvas"):
            dark_canvas = settings.value('dark_canvas', type=bool)
        else:
            dark_canvas = False

        if self.app.use_3d_engine:
            if (theme == 'default' or theme == 'light') and not dark_canvas:
                color = '#000000FF'
            else:
                color = '#FFFFFFFF'
        else:
            if (theme == 'default' or theme == 'light') and not dark_canvas:
                color = '#000000'
            else:
                color = '#FFFFFF'

        self.last_shape = self.sel_shapes.add(meas_line, color=color, update=True, layer=0, tolerance=None, linewidth=2)
        self.sel_shapes.redraw()

    def delete_all_shapes(self):
        self.sel_shapes.clear()
        self.sel_shapes.redraw()

    def delete_utility_shape(self, shape):
        if shape:
            self.sel_shapes.remove(shape, update=True)

    @staticmethod
    def make_storage():
        # ## Shape storage.
        storage = AppRTreeStorage()
        storage.get_points = DrawToolShape.get_pts

        return storage

    def on_plugin_cleanup(self):
        self.on_exit()


class DistanceUI:
    
    pluginName = _("Distance")

    def __init__(self, layout, app):
        self.app = app
        self.decimals = self.app.decimals
        self.layout = layout
        self.units = self.app.app_units.lower()

        # ## Title
        title_label = FCLabel("<font size=4><b>%s</b></font><br>" % self.pluginName)
        self.layout.addWidget(title_label)

        # #############################################################################################################
        # Parameters Frame
        # #############################################################################################################
        self.param_label = FCLabel('%s' % _("Parameters"), color='blue', bold=True)
        self.layout.addWidget(self.param_label)

        self.par_frame = FCFrame()
        self.layout.addWidget(self.par_frame)

        param_grid = GLay(v_spacing=5, h_spacing=3)
        self.par_frame.setLayout(param_grid)

        self.snap_center_cb = FCCheckBox(_("Snap to center"))
        self.snap_center_cb.setToolTip(
            _("Mouse cursor will snap to the center of the pad/drill\n"
              "when it is hovering over the geometry of the pad/drill.")
        )
        param_grid.addWidget(self.snap_center_cb, 0, 0, 1, 2)

        self.multipoint_cb = FCCheckBox(_("Multi-Point"))
        self.multipoint_cb.setToolTip(
            _("Make a measurement over multiple distance segments.")
        )
        param_grid.addWidget(self.multipoint_cb, 2, 0, 1, 2)

        # Big Cursor
        self.big_cursor_cb = FCCheckBox('%s' % _("Big cursor"))
        self.big_cursor_cb.setToolTip(
            _("Use a big cursor."))
        param_grid.addWidget(self.big_cursor_cb, 4, 0, 1, 2)

        # #############################################################################################################
        # Coordinates Frame
        # #############################################################################################################
        self.coords_label = FCLabel('%s' % _("Coordinates"), color='green', bold=True)
        self.layout.addWidget(self.coords_label)

        coords_frame = FCFrame()
        self.layout.addWidget(coords_frame)

        coords_grid = GLay(v_spacing=5, h_spacing=3)
        coords_frame.setLayout(coords_grid)

        # separator_line = QtWidgets.QFrame()
        # separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        # separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        # param_grid.addWidget(separator_line, 6, 0, 1, 2)

        # Start Point
        self.start_label = FCLabel("%s:" % _('Start point'))
        self.start_label.setToolTip(_("This is measuring Start point coordinates."))

        self.start_entry = FCEntry()
        self.start_entry.setReadOnly(True)
        self.start_entry.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.start_entry.setToolTip(_("This is measuring Start point coordinates."))

        coords_grid.addWidget(self.start_label, 0, 0)
        coords_grid.addWidget(self.start_entry, 0, 1)
        coords_grid.addWidget(FCLabel("%s" % self.units), 0, 2)

        # End Point
        self.stop_label = FCLabel("%s:" % _('End point'))
        self.stop_label.setToolTip(_("This is the measuring Stop point coordinates."))

        self.stop_entry = FCEntry()
        self.stop_entry.setReadOnly(True)
        self.stop_entry.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.stop_entry.setToolTip(_("This is the measuring Stop point coordinates."))

        coords_grid.addWidget(self.stop_label, 2, 0)
        coords_grid.addWidget(self.stop_entry, 2, 1)
        coords_grid.addWidget(FCLabel("%s" % self.units), 2, 2)

        # #############################################################################################################
        # Coordinates Frame
        # #############################################################################################################
        self.res_label = FCLabel('%s' % _("Results"), color='red', bold=True)
        self.layout.addWidget(self.res_label)

        res_frame = FCFrame()
        self.layout.addWidget(res_frame)

        res_grid = GLay(v_spacing=5, h_spacing=3)
        res_frame.setLayout(res_grid)

        # DX distance
        self.distance_x_label = FCLabel('%s:' % _("Dx"))
        self.distance_x_label.setToolTip(_("This is the distance measured over the X axis."))

        self.distance_x_entry = FCEntry()
        self.distance_x_entry.setReadOnly(True)
        self.distance_x_entry.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.distance_x_entry.setToolTip(_("This is the distance measured over the X axis."))

        res_grid.addWidget(self.distance_x_label, 0, 0)
        res_grid.addWidget(self.distance_x_entry, 0, 1)
        res_grid.addWidget(FCLabel("%s" % self.units), 0, 2)

        # DY distance
        self.distance_y_label = FCLabel('%s:' % _("Dy"))
        self.distance_y_label.setToolTip(_("This is the distance measured over the Y axis."))

        self.distance_y_entry = FCEntry()
        self.distance_y_entry.setReadOnly(True)
        self.distance_y_entry.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.distance_y_entry.setToolTip(_("This is the distance measured over the Y axis."))

        res_grid.addWidget(self.distance_y_label, 2, 0)
        res_grid.addWidget(self.distance_y_entry, 2, 1)
        res_grid.addWidget(FCLabel("%s" % self.units), 2, 2)

        # Angle
        self.angle_label = FCLabel('%s:' % _("Angle"))
        self.angle_label.setToolTip(_("This is orientation angle of the measuring line."))

        self.angle_entry = FCEntry()
        self.angle_entry.setReadOnly(True)
        self.angle_entry.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.angle_entry.setToolTip(_("This is orientation angle of the measuring line."))

        res_grid.addWidget(self.angle_label, 4, 0)
        res_grid.addWidget(self.angle_entry, 4, 1)
        res_grid.addWidget(FCLabel("%s" % "°"), 4, 2)

        # Angle 2
        self.angle2_label = FCLabel('%s 2:' % _("Angle"))
        self.angle2_label.setToolTip(_("This is orientation angle of the measuring line."))

        self.angle2_entry = FCEntry()
        self.angle2_entry.setReadOnly(True)
        self.angle2_entry.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.angle2_entry.setToolTip(_("This is orientation angle of the measuring line."))

        res_grid.addWidget(self.angle2_label, 6, 0)
        res_grid.addWidget(self.angle2_entry, 6, 1)
        res_grid.addWidget(FCLabel("%s" % "°"), 6, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        res_grid.addWidget(separator_line, 8, 0, 1, 3)

        # Distance
        self.total_distance_label = FCLabel('%s:' % _('DISTANCE'), bold=True)
        self.total_distance_label.setToolTip(_("This is the point to point Euclidian distance."))

        self.total_distance_entry = FCEntry()
        self.total_distance_entry.setReadOnly(True)
        self.total_distance_entry.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight |
                                               QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.total_distance_entry.setToolTip(_("This is the point to point Euclidian distance."))

        res_grid.addWidget(self.total_distance_label, 10, 0)
        res_grid.addWidget(self.total_distance_entry, 10, 1)
        res_grid.addWidget(FCLabel("%s" % self.units), 10, 2)

        # Buttons
        self.measure_btn = FCButton(_("Measure"))
        self.layout.addWidget(self.measure_btn)

        GLay.set_common_column_size([param_grid, coords_grid, res_grid], 0)

        self.layout.addStretch(1)

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
