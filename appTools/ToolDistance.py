# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtCore

from appTool import AppTool
from appGUI.VisPyVisuals import *
from appGUI.GUIElements import FCEntry, FCButton, FCCheckBox, FCLabel

from shapely.geometry import Point, MultiLineString, Polygon

import appTranslation as fcTranslate
from camlib import FlatCAMRTreeStorage
from appEditors.AppGeoEditor import DrawToolShape

from copy import copy
import math
import logging
import gettext
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
        self.units = self.app.defaults['units'].lower()

        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = DistUI(layout=self.layout, app=self.app)
        self.toolName = self.ui.toolName

        # store here the first click and second click of the measurement process
        self.points = []

        self.rel_point1 = None
        self.rel_point2 = None

        self.active = False
        self.clicked_meas = None
        self.meas_line = None

        self.original_call_source = 'app'

        # store here the event connection ID's
        self.mm = None
        self.mr = None

        # monitor if the tool was used
        self.tool_done = False

        # store the grid status here
        self.grid_status_memory = False

        # store here if the snap button was clicked
        self.snap_toggled = None

        self.mouse_is_dragging = False

        # VisPy visuals
        if self.app.is_legacy is False:
            self.sel_shapes = ShapeCollection(parent=self.app.plotcanvas.view.scene, layers=1)
        else:
            from appGUI.PlotCanvasLegacy import ShapeCollectionLegacy
            self.sel_shapes = ShapeCollectionLegacy(obj=self, app=self.app, name='measurement')
        
        # Signals
        self.ui.measure_btn.clicked.connect(self.activate_measure_tool)

    def run(self, toggle=False):
        self.app.defaults.report_usage("ToolDistance()")

        self.points[:] = []

        self.rel_point1 = None
        self.rel_point2 = None

        self.tool_done = False

        if self.app.tool_tab_locked is True:
            return

        self.app.ui.notebook.setTabText(2, _("Distance Tool"))

        # if the splitter is hidden, display it
        if self.app.ui.splitter.sizes()[0] == 0:
            self.app.ui.splitter.setSizes([1, 1])
        if toggle:
            pass

        if self.active is False:
            self.activate_measure_tool()
        else:
            self.deactivate_measure_tool()

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Ctrl+M', **kwargs)

    def set_tool_ui(self):
        # Remove anything else in the appGUI
        self.app.ui.tool_scroll_area.takeWidget()

        # Put ourselves in the appGUI
        self.app.ui.tool_scroll_area.setWidget(self)

        # Switch notebook to tool page
        self.app.ui.notebook.setCurrentWidget(self.app.ui.tool_tab)
        self.units = self.app.defaults['units'].lower()

        self.app.command_active = "Distance"

        # initial view of the layout
        self.ui.start_entry.set_value('(0, 0)')
        self.ui.stop_entry.set_value('(0, 0)')

        self.ui.distance_x_entry.set_value('0.0')
        self.ui.distance_y_entry.set_value('0.0')
        self.ui.angle_entry.set_value('0.0')
        self.ui.total_distance_entry.set_value('0.0')

        self.ui.snap_center_cb.set_value(self.app.defaults['tools_dist_snap_center'])

        # snap center works only for Gerber and Execellon Editor's
        if self.original_call_source == 'exc_editor' or self.original_call_source == 'grb_editor':
            self.ui.snap_center_cb.show()
            snap_center = self.app.defaults['tools_dist_snap_center']
            self.on_snap_toggled(snap_center)

            self.ui.snap_center_cb.toggled.connect(self.on_snap_toggled)
        else:
            self.ui.snap_center_cb.hide()
            try:
                self.ui.snap_center_cb.toggled.disconnect(self.on_snap_toggled)
            except (TypeError, AttributeError):
                pass

        # this is a hack; seems that triggering the grid will make the visuals better
        # trigger it twice to return to the original state
        self.app.ui.grid_snap_btn.trigger()
        self.app.ui.grid_snap_btn.trigger()

        if self.app.ui.grid_snap_btn.isChecked():
            self.grid_status_memory = True

        log.debug("Distance Tool --> tool initialized")

    def on_snap_toggled(self, state):
        self.app.defaults['tools_dist_snap_center'] = state
        if state:
            # disengage the grid snapping since it will be hard to find the drills or pads on grid
            if self.app.ui.grid_snap_btn.isChecked():
                self.app.ui.grid_snap_btn.trigger()

    def activate_measure_tool(self):
        # ENABLE the Measuring TOOL
        self.active = True

        # disable the measuring button
        self.ui.measure_btn.setDisabled(True)
        self.ui.measure_btn.setText('%s...' % _("Working"))

        self.clicked_meas = 0
        self.original_call_source = copy(self.app.call_source)

        self.app.inform.emit(_("MEASURING: Click on the Start point ..."))
        self.units = self.app.defaults['units'].lower()

        # we can connect the app mouse events to the measurement tool
        # NEVER DISCONNECT THOSE before connecting some other handlers; it breaks something in VisPy
        self.mm = self.canvas.graph_event_connect('mouse_move', self.on_mouse_move_meas)
        self.mr = self.canvas.graph_event_connect('mouse_release', self.on_mouse_click_release)

        # we disconnect the mouse/key handlers from wherever the measurement tool was called
        if self.app.call_source == 'app':
            if self.app.is_legacy is False:
                self.canvas.graph_event_disconnect('mouse_move', self.app.on_mouse_move_over_plot)
                self.canvas.graph_event_disconnect('mouse_press', self.app.on_mouse_click_over_plot)
                self.canvas.graph_event_disconnect('mouse_release', self.app.on_mouse_click_release_over_plot)
            else:
                self.canvas.graph_event_disconnect(self.app.mm)
                self.canvas.graph_event_disconnect(self.app.mp)
                self.canvas.graph_event_disconnect(self.app.mr)

        elif self.app.call_source == 'geo_editor':
            if self.app.is_legacy is False:
                self.canvas.graph_event_disconnect('mouse_move', self.app.geo_editor.on_canvas_move)
                self.canvas.graph_event_disconnect('mouse_press', self.app.geo_editor.on_canvas_click)
                self.canvas.graph_event_disconnect('mouse_release', self.app.geo_editor.on_geo_click_release)
            else:
                self.canvas.graph_event_disconnect(self.app.geo_editor.mm)
                self.canvas.graph_event_disconnect(self.app.geo_editor.mp)
                self.canvas.graph_event_disconnect(self.app.geo_editor.mr)

        elif self.app.call_source == 'exc_editor':
            if self.app.is_legacy is False:
                self.canvas.graph_event_disconnect('mouse_move', self.app.exc_editor.on_canvas_move)
                self.canvas.graph_event_disconnect('mouse_press', self.app.exc_editor.on_canvas_click)
                self.canvas.graph_event_disconnect('mouse_release', self.app.exc_editor.on_exc_click_release)
            else:
                self.canvas.graph_event_disconnect(self.app.exc_editor.mm)
                self.canvas.graph_event_disconnect(self.app.exc_editor.mp)
                self.canvas.graph_event_disconnect(self.app.exc_editor.mr)

        elif self.app.call_source == 'grb_editor':
            if self.app.is_legacy is False:
                self.canvas.graph_event_disconnect('mouse_move', self.app.grb_editor.on_canvas_move)
                self.canvas.graph_event_disconnect('mouse_press', self.app.grb_editor.on_canvas_click)
                self.canvas.graph_event_disconnect('mouse_release', self.app.grb_editor.on_grb_click_release)
            else:
                self.canvas.graph_event_disconnect(self.app.grb_editor.mm)
                self.canvas.graph_event_disconnect(self.app.grb_editor.mp)
                self.canvas.graph_event_disconnect(self.app.grb_editor.mr)

        self.app.call_source = 'measurement'

        self.set_tool_ui()

    def deactivate_measure_tool(self):
        # DISABLE the Measuring TOOL
        self.active = False
        self.points = []

        # disable the measuring button
        self.ui.measure_btn.setDisabled(False)
        self.ui.measure_btn.setText(_("Measure"))

        self.app.call_source = copy(self.original_call_source)
        if self.original_call_source == 'app':
            self.app.mm = self.canvas.graph_event_connect('mouse_move', self.app.on_mouse_move_over_plot)
            self.app.mp = self.canvas.graph_event_connect('mouse_press', self.app.on_mouse_click_over_plot)
            self.app.mr = self.canvas.graph_event_connect('mouse_release', self.app.on_mouse_click_release_over_plot)

        elif self.original_call_source == 'geo_editor':
            self.app.geo_editor.mm = self.canvas.graph_event_connect('mouse_move', self.app.geo_editor.on_canvas_move)
            self.app.geo_editor.mp = self.canvas.graph_event_connect('mouse_press', self.app.geo_editor.on_canvas_click)
            self.app.geo_editor.mr = self.canvas.graph_event_connect('mouse_release',
                                                                     self.app.geo_editor.on_geo_click_release)

        elif self.original_call_source == 'exc_editor':
            self.app.exc_editor.mm = self.canvas.graph_event_connect('mouse_move', self.app.exc_editor.on_canvas_move)
            self.app.exc_editor.mp = self.canvas.graph_event_connect('mouse_press', self.app.exc_editor.on_canvas_click)
            self.app.exc_editor.mr = self.canvas.graph_event_connect('mouse_release',
                                                                     self.app.exc_editor.on_exc_click_release)

        elif self.original_call_source == 'grb_editor':
            self.app.grb_editor.mm = self.canvas.graph_event_connect('mouse_move', self.app.grb_editor.on_canvas_move)
            self.app.grb_editor.mp = self.canvas.graph_event_connect('mouse_press', self.app.grb_editor.on_canvas_click)
            self.app.grb_editor.mr = self.canvas.graph_event_connect('mouse_release',
                                                                     self.app.grb_editor.on_grb_click_release)

        # disconnect the mouse/key events from functions of measurement tool
        if self.app.is_legacy is False:
            self.canvas.graph_event_disconnect('mouse_move', self.on_mouse_move_meas)
            self.canvas.graph_event_disconnect('mouse_release', self.on_mouse_click_release)
        else:
            self.canvas.graph_event_disconnect(self.mm)
            self.canvas.graph_event_disconnect(self.mr)

        # self.app.ui.notebook.setTabText(2, _("Tools"))
        # self.app.ui.notebook.setCurrentWidget(self.app.ui.project_tab)

        self.app.command_active = None

        # delete the measuring line
        self.delete_shape()

        # restore the grid status
        if (self.app.ui.grid_snap_btn.isChecked() and self.grid_status_memory is False) or \
                (not self.app.ui.grid_snap_btn.isChecked() and self.grid_status_memory is True):
            self.app.ui.grid_snap_btn.trigger()

        log.debug("Distance Tool --> exit tool")

        if self.tool_done is False:
            self.app.inform.emit('%s' % _("Distance Tool finished."))

    def on_mouse_click_release(self, event):
        # mouse click releases will be accepted only if the left button is clicked
        # this is necessary because right mouse click or middle mouse click
        # are used for panning on the canvas
        log.debug("Distance Tool --> mouse click release")

        if self.app.is_legacy is False:
            event_pos = event.pos
            right_button = 2
            event_is_dragging = self.mouse_is_dragging
        else:
            event_pos = (event.xdata, event.ydata)
            right_button = 3
            event_is_dragging = self.app.plotcanvas.is_dragging

        if event.button == 1:
            pos_canvas = self.canvas.translate_coords(event_pos)

            if self.ui.snap_center_cb.get_value() is False:
                # if GRID is active we need to get the snapped positions
                if self.app.grid_status():
                    pos = self.app.geo_editor.snap(pos_canvas[0], pos_canvas[1])
                else:
                    pos = pos_canvas[0], pos_canvas[1]
            else:
                pos = (pos_canvas[0], pos_canvas[1])
                current_pt = Point(pos)
                shapes_storage = self.make_storage()

                if self.original_call_source == 'exc_editor':
                    for storage in self.app.exc_editor.storage_dict:
                        __, st_closest_shape = self.app.exc_editor.storage_dict[storage].nearest(pos)
                        shapes_storage.insert(st_closest_shape)

                    __, closest_shape = shapes_storage.nearest(pos)

                    # if it's a drill
                    if isinstance(closest_shape.geo, MultiLineString):
                        radius = closest_shape.geo[0].length / 2.0
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
                                    if Point(current_pt).within(geometric_data):
                                        if isinstance(shape_stored.geo['follow'], Point):
                                            clicked_pads.append(shape_stored.geo['follow'])
                        except KeyError:
                            pass

                    if len(clicked_pads) > 1:
                        self.tool_done = True
                        self.deactivate_measure_tool()
                        self.app.inform.emit('[WARNING_NOTCL] %s' % _("Pads overlapped. Aborting."))
                        return

                    if clicked_pads:
                        pos = (clicked_pads[0].x, clicked_pads[0].y)

                self.app.on_jump_to(custom_location=pos, fit_center=False)
                # Update cursor
                self.app.app_cursor.enabled = True
                self.app.app_cursor.set_data(np.asarray([(pos[0], pos[1])]),
                                             symbol='++', edge_color='#000000',
                                             edge_width=self.app.defaults["global_cursor_width"],
                                             size=self.app.defaults["global_cursor_size"])

            self.points.append(pos)

            # Reset here the relative coordinates so there is a new reference on the click position
            if self.rel_point1 is None:
                self.app.ui.rel_position_label.setText("<b>Dx</b>: %.*f&nbsp;&nbsp;  <b>Dy</b>: "
                                                       "%.*f&nbsp;&nbsp;&nbsp;&nbsp;" %
                                                       (self.decimals, 0.0, self.decimals, 0.0))
                self.rel_point1 = pos
            else:
                self.rel_point2 = copy(self.rel_point1)
                self.rel_point1 = pos

            self.calculate_distance(pos=pos)
        elif event.button == right_button and event_is_dragging is False:
            self.deactivate_measure_tool()
            self.app.inform.emit(_("Distance Tool cancelled."))

    def calculate_distance(self, pos):
        if len(self.points) == 1:
            self.ui.start_entry.set_value("(%.*f, %.*f)" % (self.decimals, pos[0], self.decimals, pos[1]))
            self.app.inform.emit(_("Click on the DESTINATION point ..."))
        elif len(self.points) == 2:
            # self.app.app_cursor.enabled = False
            dx = self.points[1][0] - self.points[0][0]
            dy = self.points[1][1] - self.points[0][1]
            d = math.sqrt(dx ** 2 + dy ** 2)
            self.ui.stop_entry.set_value("(%.*f, %.*f)" % (self.decimals, pos[0], self.decimals, pos[1]))

            self.app.inform.emit("{tx1}: {tx2} D(x) = {d_x} | D(y) = {d_y} | {tx3} = {d_z}".format(
                tx1=_("MEASURING"),
                tx2=_("Result"),
                tx3=_("Distance"),
                d_x='%*f' % (self.decimals, abs(dx)),
                d_y='%*f' % (self.decimals, abs(dy)),
                d_z='%*f' % (self.decimals, abs(d)))
            )

            self.ui.distance_x_entry.set_value('%.*f' % (self.decimals, abs(dx)))
            self.ui.distance_y_entry.set_value('%.*f' % (self.decimals, abs(dy)))

            try:
                angle = math.degrees(math.atan2(dy, dx))
                if angle < 0:
                    angle += 360
                self.ui.angle_entry.set_value('%.*f' % (self.decimals, angle))
            except Exception:
                pass

            self.ui.total_distance_entry.set_value('%.*f' % (self.decimals, abs(d)))
            self.app.ui.rel_position_label.setText(
                "<b>Dx</b>: {}&nbsp;&nbsp;  <b>Dy</b>: {}&nbsp;&nbsp;&nbsp;&nbsp;".format(
                    '%.*f' % (self.decimals, pos[0]), '%.*f' % (self.decimals, pos[1])
                )
            )
            self.tool_done = True
            self.deactivate_measure_tool()

    def on_mouse_move_meas(self, event):
        try:  # May fail in case mouse not within axes
            if self.app.is_legacy is False:
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

            if self.app.grid_status():
                pos = self.app.geo_editor.snap(pos_canvas[0], pos_canvas[1])

                # Update cursor
                self.app.app_cursor.set_data(np.asarray([(pos[0], pos[1])]),
                                             symbol='++', edge_color=self.app.cursor_color_3D,
                                             edge_width=self.app.defaults["global_cursor_width"],
                                             size=self.app.defaults["global_cursor_size"])
            else:
                pos = (pos_canvas[0], pos_canvas[1])

            self.app.ui.position_label.setText(
                "&nbsp;&nbsp;&nbsp;&nbsp;<b>X</b>: {}&nbsp;&nbsp;   <b>Y</b>: {}".format(
                    '%.*f' % (self.decimals, pos[0]), '%.*f' % (self.decimals, pos[1])
                )
            )

            units = self.app.defaults["units"].lower()
            self.app.plotcanvas.text_hud.text = \
                'Dx:\t{:<.4f} [{:s}]\nDy:\t{:<.4f} [{:s}]\n\nX:  \t{:<.4f} [{:s}]\nY:  \t{:<.4f} [{:s}]'.format(
                    0.0000, units, 0.0000, units, pos[0], units, pos[1], units)

            if self.rel_point1 is not None:
                dx = pos[0] - float(self.rel_point1[0])
                dy = pos[1] - float(self.rel_point1[1])
            else:
                dx = pos[0]
                dy = pos[1]

            self.app.ui.rel_position_label.setText(
                "<b>Dx</b>: {}&nbsp;&nbsp;  <b>Dy</b>: {}&nbsp;&nbsp;&nbsp;&nbsp;".format(
                    '%.*f' % (self.decimals, dx), '%.*f' % (self.decimals, dy)
                )
            )

            # update utility geometry
            if len(self.points) == 1:
                self.utility_geometry(pos=pos)
                # and display the temporary angle
                try:
                    angle = math.degrees(math.atan2(dy, dx))
                    if angle < 0:
                        angle += 360
                    self.ui.angle_entry.set_value('%.*f' % (self.decimals, angle))
                except Exception as e:
                    log.debug("Distance.on_mouse_move_meas() -> update utility geometry -> %s" % str(e))
                    pass

        except Exception as e:
            log.debug("Distance.on_mouse_move_meas() --> %s" % str(e))
            self.app.ui.position_label.setText("")
            self.app.ui.rel_position_label.setText("")

    def utility_geometry(self, pos):
        # first delete old shape
        self.delete_shape()

        # second draw the new shape of the utility geometry
        meas_line = LineString([pos, self.points[0]])

        settings = QtCore.QSettings("Open Source", "FlatCAM")
        if settings.contains("theme"):
            theme = settings.value('theme', type=str)
        else:
            theme = 'white'

        if theme == 'white':
            color = '#000000FF'
        else:
            color = '#FFFFFFFF'

        self.sel_shapes.add(meas_line, color=color, update=True, layer=0, tolerance=None, linewidth=2)

        if self.app.is_legacy is True:
            self.sel_shapes.redraw()

    def delete_shape(self):
        self.sel_shapes.clear()
        self.sel_shapes.redraw()

    @staticmethod
    def make_storage():
        # ## Shape storage.
        storage = FlatCAMRTreeStorage()
        storage.get_points = DrawToolShape.get_pts

        return storage

    # def set_meas_units(self, units):
    #     self.meas.units_label.setText("[" + self.app.options["units"].lower() + "]")


class DistUI:
    
    toolName = _("Distance Tool")

    def __init__(self, layout, app):
        self.app = app
        self.decimals = self.app.decimals
        self.layout = layout
        self.units = self.app.defaults['units'].lower()

        # ## Title
        title_label = FCLabel("<font size=4><b>%s</b></font><br>" % self.toolName)
        self.layout.addWidget(title_label)

        # ## Form Layout
        grid0 = QtWidgets.QGridLayout()
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        self.layout.addLayout(grid0)

        self.units_label = FCLabel('%s:' % _("Units"))
        self.units_label.setToolTip(_("Those are the units in which the distance is measured."))
        self.units_value = FCLabel("%s" % str({'mm': _("METRIC (mm)"), 'in': _("INCH (in)")}[self.units]))
        self.units_value.setDisabled(True)

        grid0.addWidget(self.units_label, 0, 0)
        grid0.addWidget(self.units_value, 0, 1)

        self.snap_center_cb = FCCheckBox(_("Snap to center"))
        self.snap_center_cb.setToolTip(
            _("Mouse cursor will snap to the center of the pad/drill\n"
              "when it is hovering over the geometry of the pad/drill.")
        )
        grid0.addWidget(self.snap_center_cb, 1, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 2, 0, 1, 2)

        self.start_label = FCLabel("%s:" % _('Start Coords'))
        self.start_label.setToolTip(_("This is measuring Start point coordinates."))

        self.start_entry = FCEntry()
        self.start_entry.setReadOnly(True)
        self.start_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.start_entry.setToolTip(_("This is measuring Start point coordinates."))

        grid0.addWidget(self.start_label, 3, 0)
        grid0.addWidget(self.start_entry, 3, 1)

        self.stop_label = FCLabel("%s:" % _('Stop Coords'))
        self.stop_label.setToolTip(_("This is the measuring Stop point coordinates."))

        self.stop_entry = FCEntry()
        self.stop_entry.setReadOnly(True)
        self.stop_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.stop_entry.setToolTip(_("This is the measuring Stop point coordinates."))

        grid0.addWidget(self.stop_label, 4, 0)
        grid0.addWidget(self.stop_entry, 4, 1)

        self.distance_x_label = FCLabel('%s:' % _("Dx"))
        self.distance_x_label.setToolTip(_("This is the distance measured over the X axis."))

        self.distance_x_entry = FCEntry()
        self.distance_x_entry.setReadOnly(True)
        self.distance_x_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.distance_x_entry.setToolTip(_("This is the distance measured over the X axis."))

        grid0.addWidget(self.distance_x_label, 5, 0)
        grid0.addWidget(self.distance_x_entry, 5, 1)

        self.distance_y_label = FCLabel('%s:' % _("Dy"))
        self.distance_y_label.setToolTip(_("This is the distance measured over the Y axis."))

        self.distance_y_entry = FCEntry()
        self.distance_y_entry.setReadOnly(True)
        self.distance_y_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.distance_y_entry.setToolTip(_("This is the distance measured over the Y axis."))

        grid0.addWidget(self.distance_y_label, 6, 0)
        grid0.addWidget(self.distance_y_entry, 6, 1)

        self.angle_label = FCLabel('%s:' % _("Angle"))
        self.angle_label.setToolTip(_("This is orientation angle of the measuring line."))

        self.angle_entry = FCEntry()
        self.angle_entry.setReadOnly(True)
        self.angle_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.angle_entry.setToolTip(_("This is orientation angle of the measuring line."))

        grid0.addWidget(self.angle_label, 7, 0)
        grid0.addWidget(self.angle_entry, 7, 1)

        self.total_distance_label = FCLabel("<b>%s:</b>" % _('DISTANCE'))
        self.total_distance_label.setToolTip(_("This is the point to point Euclidian distance."))

        self.total_distance_entry = FCEntry()
        self.total_distance_entry.setReadOnly(True)
        self.total_distance_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.total_distance_entry.setToolTip(_("This is the point to point Euclidian distance."))

        grid0.addWidget(self.total_distance_label, 8, 0)
        grid0.addWidget(self.total_distance_entry, 8, 1)

        self.measure_btn = FCButton(_("Measure"))
        # self.measure_btn.setFixedWidth(70)
        self.layout.addWidget(self.measure_btn)

        self.layout.addStretch()

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
