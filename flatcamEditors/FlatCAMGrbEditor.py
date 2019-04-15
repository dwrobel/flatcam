from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import Qt, QSettings

from shapely.geometry import LineString, LinearRing, MultiLineString
from shapely.ops import cascaded_union, unary_union
import shapely.affinity as affinity

from numpy import arctan2, Inf, array, sqrt, sign, dot
from rtree import index as rtindex
import threading, time
from copy import copy, deepcopy

from camlib import *
from flatcamGUI.GUIElements import FCEntry, FCComboBox, FCTable, FCDoubleSpinner, LengthEntry, RadioSet, \
    SpinBoxDelegate, EvalEntry, EvalEntry2, FCInputDialog, FCButton, OptionalInputSection, FCCheckBox
from flatcamEditors.FlatCAMGeoEditor import FCShapeTool, DrawTool, DrawToolShape, DrawToolUtilityShape, FlatCAMGeoEditor
from FlatCAMObj import FlatCAMGerber
from FlatCAMTool import FlatCAMTool

import gettext
import FlatCAMTranslation as fcTranslate

fcTranslate.apply_language('strings')
import builtins
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class FCPad(FCShapeTool):
    """
    Resulting type: Polygon
    """

    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.name = 'pad'
        self.draw_app = draw_app

        try:
            self.radius = float(self.draw_app.storage_dict[self.draw_app.last_aperture_selected]['size']) / 2
        except KeyError:
            self.draw_app.app.inform.emit(_("[WARNING_NOTCL] To add a Pad, first select a tool in Tool Table"))
            self.draw_app.in_action = False
            self.complete = True
            return
        self.storage_obj = self.draw_app.storage_dict[self.draw_app.last_aperture_selected]['solid_geometry']
        self.steps_per_circ = self.draw_app.app.defaults["geometry_circle_steps"]

        # if those cause KeyError exception it means that the aperture type is not 'R'. Only 'R' type has those keys
        try:
            self.half_width = float(self.draw_app.storage_dict[self.draw_app.last_aperture_selected]['width']) / 2
        except KeyError:
            pass
        try:
            self.half_height = float(self.draw_app.storage_dict[self.draw_app.last_aperture_selected]['height']) / 2
        except KeyError:
            pass

        geo = self.utility_geometry(data=(self.draw_app.snap_x, self.draw_app.snap_y))
        if isinstance(geo, DrawToolShape) and geo.geo is not None:
            self.draw_app.draw_utility_geometry(geo=geo)

        self.draw_app.app.inform.emit(_("Click to place ..."))

        # Switch notebook to Selected page
        self.draw_app.app.ui.notebook.setCurrentWidget(self.draw_app.app.ui.selected_tab)

        self.start_msg = _("Click to place ...")

    def click(self, point):
        self.make()
        return "Done."

    def utility_geometry(self, data=None):
        self.points = data
        geo_data = self.util_shape(data)
        if geo_data:
            return DrawToolUtilityShape(geo_data)
        else:
            return None

    def util_shape(self, point):
        # updating values here allows us to change the aperture on the fly, after the Tool has been started
        self.storage_obj = self.draw_app.storage_dict[self.draw_app.last_aperture_selected]['solid_geometry']
        self.radius = float(self.draw_app.storage_dict[self.draw_app.last_aperture_selected]['size']) / 2
        self.steps_per_circ = self.draw_app.app.defaults["geometry_circle_steps"]

        # if those cause KeyError exception it means that the aperture type is not 'R'. Only 'R' type has those keys
        try:
            self.half_width = float(self.draw_app.storage_dict[self.draw_app.last_aperture_selected]['width']) / 2
        except KeyError:
            pass
        try:
            self.half_height = float(self.draw_app.storage_dict[self.draw_app.last_aperture_selected]['height']) / 2
        except KeyError:
            pass

        if point[0] is None and point[1] is None:
            point_x = self.draw_app.x
            point_y = self.draw_app.y
        else:
            point_x = point[0]
            point_y = point[1]

        ap_type = self.draw_app.storage_dict[self.draw_app.last_aperture_selected]['type']
        if ap_type == 'C':
            center = Point([point_x, point_y])
            return center.buffer(self.radius)
        elif ap_type == 'R':
            p1 = (point_x - self.half_width, point_y - self.half_height)
            p2 = (point_x + self.half_width, point_y - self.half_height)
            p3 = (point_x + self.half_width, point_y + self.half_height)
            p4 = (point_x - self.half_width, point_y + self.half_height)
            return Polygon([p1, p2, p3, p4, p1])
        elif ap_type == 'O':
            geo = []
            if self.half_height > self.half_width:
                p1 = (point_x - self.half_width, point_y - self.half_height + self.half_width)
                p2 = (point_x + self.half_width, point_y - self.half_height + self.half_width)
                p3 = (point_x + self.half_width, point_y + self.half_height - self.half_width)
                p4 = (point_x - self.half_width, point_y + self.half_height - self.half_width)

                down_center = (point_x, point_y - self.half_height + self.half_width)
                d_start_angle = math.pi
                d_stop_angle = 0.0
                down_arc = arc(down_center, self.half_width, d_start_angle, d_stop_angle, 'ccw', self.steps_per_circ)

                up_center = (point_x, point_y + self.half_height - self.half_width)
                u_start_angle = 0.0
                u_stop_angle = math.pi
                up_arc = arc(up_center, self.half_width, u_start_angle, u_stop_angle, 'ccw', self.steps_per_circ)

                geo.append(p1)
                for pt in down_arc:
                    geo.append(pt)
                geo.append(p2)
                geo.append(p3)
                for pt in up_arc:
                    geo.append(pt)
                geo.append(p4)
                return Polygon(geo)
            else:
                p1 = (point_x - self.half_width + self.half_height, point_y - self.half_height)
                p2 = (point_x + self.half_width - self.half_height, point_y - self.half_height)
                p3 = (point_x + self.half_width - self.half_height, point_y + self.half_height)
                p4 = (point_x - self.half_width + self.half_height, point_y + self.half_height)

                left_center = (point_x - self.half_width + self.half_height, point_y)
                d_start_angle = math.pi / 2
                d_stop_angle = 1.5 * math.pi
                left_arc = arc(left_center, self.half_height, d_start_angle, d_stop_angle, 'ccw', self.steps_per_circ)

                right_center = (point_x + self.half_width - self.half_height, point_y)
                u_start_angle = 1.5 * math.pi
                u_stop_angle = math.pi / 2
                right_arc = arc(right_center, self.half_height, u_start_angle, u_stop_angle, 'ccw', self.steps_per_circ)

                geo.append(p1)
                geo.append(p2)
                for pt in right_arc:
                    geo.append(pt)
                geo.append(p3)
                geo.append(p4)
                for pt in left_arc:
                    geo.append(pt)
                return Polygon(geo)
        else:
            self.draw_app.app.inform.emit(_(
                "Incompatible aperture type. Select an aperture with type 'C', 'R' or 'O'."))
            return None

    def make(self):
        self.draw_app.current_storage = self.storage_obj
        try:
            self.geometry = DrawToolShape(self.util_shape(self.points))
        except Exception as e:
            log.debug("FCPad.make() --> %s" % str(e))

        self.draw_app.in_action = False
        self.complete = True
        self.draw_app.app.inform.emit(_("[success] Done. Adding Pad completed."))

    def clean_up(self):
        self.draw_app.selected = []
        self.draw_app.apertures_table.clearSelection()
        self.draw_app.plot_all()


class FCPadArray(FCShapeTool):
    """
    Resulting type: MultiPolygon
    """

    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.name = 'array'
        self.draw_app = draw_app

        try:
            self.radius = float(self.draw_app.storage_dict[self.draw_app.last_aperture_selected]['size']) / 2
        except KeyError:
            self.draw_app.app.inform.emit(_("[WARNING_NOTCL] To add an Pad Array first select a tool in Tool Table"))
            self.complete = True
            self.draw_app.in_action = False
            self.draw_app.array_frame.hide()
            return
        self.storage_obj = self.draw_app.storage_dict[self.draw_app.last_aperture_selected]['solid_geometry']
        self.steps_per_circ = self.draw_app.app.defaults["geometry_circle_steps"]

        # if those cause KeyError exception it means that the aperture type is not 'R'. Only 'R' type has those keys
        try:
            self.half_width = float(self.draw_app.storage_dict[self.draw_app.last_aperture_selected]['width']) / 2
        except KeyError:
            pass
        try:
            self.half_height = float(self.draw_app.storage_dict[self.draw_app.last_aperture_selected]['height']) / 2
        except KeyError:
            pass

        self.draw_app.array_frame.show()

        self.selected_size = None
        self.pad_axis = 'X'
        self.pad_array = 'linear'
        self.pad_array_size = None
        self.pad_pitch = None
        self.pad_linear_angle = None

        self.pad_angle = None
        self.pad_direction = None
        self.pad_radius = None

        self.origin = None
        self.destination = None
        self.flag_for_circ_array = None

        self.last_dx = 0
        self.last_dy = 0

        self.pt = []

        self.draw_app.app.inform.emit(self.start_msg)

        geo = self.utility_geometry(data=(self.draw_app.snap_x, self.draw_app.snap_y), static=True)

        if isinstance(geo, DrawToolShape) and geo.geo is not None:
            self.draw_app.draw_utility_geometry(geo=geo)

        self.draw_app.app.inform.emit(_("Click on target location ..."))

        # Switch notebook to Selected page
        self.draw_app.app.ui.notebook.setCurrentWidget(self.draw_app.app.ui.selected_tab)

    def click(self, point):

        if self.pad_array == 'Linear':
            self.make()
            return
        else:
            if self.flag_for_circ_array is None:
                self.draw_app.in_action = True
                self.pt.append(point)

                self.flag_for_circ_array = True
                self.set_origin(point)
                self.draw_app.app.inform.emit(_("Click on the Pad Circular Array Start position"))
            else:
                self.destination = point
                self.make()
                self.flag_for_circ_array = None
                return

    def set_origin(self, origin):
        self.origin = origin

    def utility_geometry(self, data=None, static=None):
        self.pad_axis = self.draw_app.pad_axis_radio.get_value()
        self.pad_direction = self.draw_app.pad_direction_radio.get_value()
        self.pad_array = self.draw_app.array_type_combo.get_value()
        try:
            self.pad_array_size = int(self.draw_app.pad_array_size_entry.get_value())
            try:
                self.pad_pitch = float(self.draw_app.pad_pitch_entry.get_value())
                self.pad_linear_angle = float(self.draw_app.linear_angle_spinner.get_value())
                self.pad_angle = float(self.draw_app.pad_angle_entry.get_value())
            except TypeError:
                self.draw_app.app.inform.emit(
                    _("[ERROR_NOTCL] The value is not Float. Check for comma instead of dot separator."))
                return
        except Exception as e:
            self.draw_app.app.inform.emit(_("[ERROR_NOTCL] The value is mistyped. Check the value."))
            return

        if self.pad_array == 'Linear':
            if data[0] is None and data[1] is None:
                dx = self.draw_app.x
                dy = self.draw_app.y
            else:
                dx = data[0]
                dy = data[1]

            geo_list = []
            geo = None
            self.points = [dx, dy]

            for item in range(self.pad_array_size):
                if self.pad_axis == 'X':
                    geo = self.util_shape(((dx + (self.pad_pitch * item)), dy))
                if self.pad_axis == 'Y':
                    geo = self.util_shape((dx, (dy + (self.pad_pitch * item))))
                if self.pad_axis == 'A':
                    x_adj = self.pad_pitch * math.cos(math.radians(self.pad_linear_angle))
                    y_adj = self.pad_pitch * math.sin(math.radians(self.pad_linear_angle))
                    geo = self.util_shape(
                        ((dx + (x_adj * item)), (dy + (y_adj * item)))
                    )

                if static is None or static is False:
                    geo_list.append(affinity.translate(geo, xoff=(dx - self.last_dx), yoff=(dy - self.last_dy)))
                else:
                    geo_list.append(geo)
            # self.origin = data

            self.last_dx = dx
            self.last_dy = dy
            return DrawToolUtilityShape(geo_list)
        else:
            if data[0] is None and data[1] is None:
                cdx = self.draw_app.x
                cdy = self.draw_app.y
            else:
                cdx = data[0]
                cdy = data[1]

            if len(self.pt) > 0:
                temp_points = [x for x in self.pt]
                temp_points.append([cdx, cdy])
                return DrawToolUtilityShape(LineString(temp_points))

    def util_shape(self, point):
        # updating values here allows us to change the aperture on the fly, after the Tool has been started
        self.storage_obj = self.draw_app.storage_dict[self.draw_app.last_aperture_selected]['solid_geometry']
        self.radius = float(self.draw_app.storage_dict[self.draw_app.last_aperture_selected]['size']) / 2
        self.steps_per_circ = self.draw_app.app.defaults["geometry_circle_steps"]

        # if those cause KeyError exception it means that the aperture type is not 'R'. Only 'R' type has those keys
        try:
            self.half_width = float(self.draw_app.storage_dict[self.draw_app.last_aperture_selected]['width']) / 2
        except KeyError:
            pass
        try:
            self.half_height = float(self.draw_app.storage_dict[self.draw_app.last_aperture_selected]['height']) / 2
        except KeyError:
            pass

        if point[0] is None and point[1] is None:
            point_x = self.draw_app.x
            point_y = self.draw_app.y
        else:
            point_x = point[0]
            point_y = point[1]

        ap_type = self.draw_app.storage_dict[self.draw_app.last_aperture_selected]['type']
        if ap_type == 'C':
            center = Point([point_x, point_y])
            return center.buffer(self.radius)
        elif ap_type == 'R':
            p1 = (point_x - self.half_width, point_y - self.half_height)
            p2 = (point_x + self.half_width, point_y - self.half_height)
            p3 = (point_x + self.half_width, point_y + self.half_height)
            p4 = (point_x - self.half_width, point_y + self.half_height)
            return Polygon([p1, p2, p3, p4, p1])
        elif ap_type == 'O':
            geo = []
            if self.half_height > self.half_width:
                p1 = (point_x - self.half_width, point_y - self.half_height + self.half_width)
                p2 = (point_x + self.half_width, point_y - self.half_height + self.half_width)
                p3 = (point_x + self.half_width, point_y + self.half_height - self.half_width)
                p4 = (point_x - self.half_width, point_y + self.half_height - self.half_width)

                down_center = (point_x, point_y - self.half_height + self.half_width)
                d_start_angle = math.pi
                d_stop_angle = 0.0
                down_arc = arc(down_center, self.half_width, d_start_angle, d_stop_angle, 'ccw', self.steps_per_circ)

                up_center = (point_x, point_y + self.half_height - self.half_width)
                u_start_angle = 0.0
                u_stop_angle = math.pi
                up_arc = arc(up_center, self.half_width, u_start_angle, u_stop_angle, 'ccw', self.steps_per_circ)

                geo.append(p1)
                for pt in down_arc:
                    geo.append(pt)
                geo.append(p2)
                geo.append(p3)
                for pt in up_arc:
                    geo.append(pt)
                geo.append(p4)
                return Polygon(geo)
            else:
                p1 = (point_x - self.half_width + self.half_height, point_y - self.half_height)
                p2 = (point_x + self.half_width - self.half_height, point_y - self.half_height)
                p3 = (point_x + self.half_width - self.half_height, point_y + self.half_height)
                p4 = (point_x - self.half_width + self.half_height, point_y + self.half_height)

                left_center = (point_x - self.half_width + self.half_height, point_y)
                d_start_angle = math.pi / 2
                d_stop_angle = 1.5 * math.pi
                left_arc = arc(left_center, self.half_height, d_start_angle, d_stop_angle, 'ccw', self.steps_per_circ)

                right_center = (point_x + self.half_width - self.half_height, point_y)
                u_start_angle = 1.5 * math.pi
                u_stop_angle = math.pi / 2
                right_arc = arc(right_center, self.half_height, u_start_angle, u_stop_angle, 'ccw', self.steps_per_circ)

                geo.append(p1)
                geo.append(p2)
                for pt in right_arc:
                    geo.append(pt)
                geo.append(p3)
                geo.append(p4)
                for pt in left_arc:
                    geo.append(pt)
                return Polygon(geo)
        else:
            self.draw_app.app.inform.emit(_(
                "Incompatible aperture type. Select an aperture with type 'C', 'R' or 'O'."))
            return None

    def make(self):
        self.geometry = []
        geo = None

        self.draw_app.current_storage = self.storage_obj

        if self.pad_array == 'Linear':
            for item in range(self.pad_array_size):
                if self.pad_axis == 'X':
                    geo = self.util_shape(((self.points[0] + (self.pad_pitch * item)), self.points[1]))
                if self.pad_axis == 'Y':
                    geo = self.util_shape((self.points[0], (self.points[1] + (self.pad_pitch * item))))
                if self.pad_axis == 'A':
                    x_adj = self.pad_pitch * math.cos(math.radians(self.pad_linear_angle))
                    y_adj = self.pad_pitch * math.sin(math.radians(self.pad_linear_angle))
                    geo = self.util_shape(
                        ((self.points[0] + (x_adj * item)), (self.points[1] + (y_adj * item)))
                    )

                self.geometry.append(DrawToolShape(geo))
        else:
            if (self.pad_angle * self.pad_array_size) > 360:
                self.draw_app.app.inform.emit(_("[WARNING_NOTCL] Too many Pads for the selected spacing angle."))
                return

            radius = distance(self.destination, self.origin)
            initial_angle = math.asin((self.destination[1] - self.origin[1]) / radius)
            for i in range(self.pad_array_size):
                angle_radians = math.radians(self.pad_angle * i)
                if self.pad_direction == 'CW':
                    x = self.origin[0] + radius * math.cos(-angle_radians + initial_angle)
                    y = self.origin[1] + radius * math.sin(-angle_radians + initial_angle)
                else:
                    x = self.origin[0] + radius * math.cos(angle_radians + initial_angle)
                    y = self.origin[1] + radius * math.sin(angle_radians + initial_angle)

                geo = self.util_shape((x, y))
                if self.pad_direction == 'CW':
                    geo = affinity.rotate(geo, angle=(math.pi - angle_radians), use_radians=True)
                else:
                    geo = affinity.rotate(geo, angle=(angle_radians - math.pi), use_radians=True)

                self.geometry.append(DrawToolShape(geo))
        self.complete = True
        self.draw_app.app.inform.emit(_("[success] Done. Pad Array added."))
        self.draw_app.in_action = False
        self.draw_app.array_frame.hide()
        return

    def clean_up(self):
        self.draw_app.selected = []
        self.draw_app.apertures_table.clearSelection()
        self.draw_app.plot_all()


class FCPoligonize(FCShapeTool):
    """
    Resulting type: Polygon
    """

    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.name = 'poligonize'
        self.draw_app = draw_app

        self.start_msg = _("Select shape(s) and then click ...")
        self.draw_app.in_action = True
        self.make()

    def click(self, point):
        return ""

    def make(self):

        if not self.draw_app.selected:
            self.draw_app.in_action = False
            self.complete = True
            self.draw_app.app.inform.emit(_("[ERROR_NOTCL] Failed. Nothing selected."))
            self.draw_app.select_tool("select")
            return

        try:
            current_storage = self.draw_app.storage_dict['0']['solid_geometry']
        except KeyError:
            self.draw_app.on_aperture_add(apid='0')
            current_storage = self.draw_app.storage_dict['0']['solid_geometry']

        fused_geo = [Polygon(sh.geo.exterior) for sh in self.draw_app.selected]

        fused_geo = MultiPolygon(fused_geo)
        fused_geo = fused_geo.buffer(0.0000001)
        if isinstance(fused_geo, MultiPolygon):
            for geo in fused_geo:
                self.draw_app.on_grb_shape_complete(current_storage, specific_shape=DrawToolShape(geo))
        else:
            self.draw_app.on_grb_shape_complete(current_storage, specific_shape=DrawToolShape(fused_geo))

        self.draw_app.delete_selected()
        self.draw_app.plot_all()

        self.draw_app.in_action = False
        self.complete = True
        self.draw_app.app.inform.emit(_("[success] Done. Poligonize completed."))

        # MS: always return to the Select Tool if modifier key is not pressed
        # else return to the current tool
        key_modifier = QtWidgets.QApplication.keyboardModifiers()
        if self.draw_app.app.defaults["global_mselect_key"] == 'Control':
            modifier_to_use = Qt.ControlModifier
        else:
            modifier_to_use = Qt.ShiftModifier
        # if modifier key is pressed then we add to the selected list the current shape but if it's already
        # in the selected list, we removed it. Therefore first click selects, second deselects.
        if key_modifier == modifier_to_use:
            self.draw_app.select_tool(self.draw_app.active_tool.name)
        else:
            self.draw_app.select_tool("select")
            return

    def clean_up(self):
        self.draw_app.selected = []
        self.draw_app.apertures_table.clearSelection()
        self.draw_app.plot_all()


class FCRegion(FCShapeTool):
    """
    Resulting type: Polygon
    """

    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.name = 'region'
        self.draw_app = draw_app

        size_ap = float(self.draw_app.storage_dict[self.draw_app.last_aperture_selected]['size'])
        self.buf_val = (size_ap / 2) if size_ap > 0 else 0.0000001

        self.start_msg = _("Click on 1st point ...")

    def click(self, point):
        self.draw_app.in_action = True
        self.points.append(point)

        if len(self.points) > 0:
            self.draw_app.app.inform.emit(_("Click on next Point or click Right mouse button to complete ..."))
            return "Click on next point or hit ENTER to complete ..."

        return ""

    def utility_geometry(self, data=None):

        if len(self.points) == 1:
            temp_points = [x for x in self.points]
            temp_points.append(data)
            return DrawToolUtilityShape(LineString(temp_points).buffer(self.buf_val, join_style=1))

        if len(self.points) > 1:
            temp_points = [x for x in self.points]
            temp_points.append(data)
            return DrawToolUtilityShape(LinearRing(temp_points).buffer(self.buf_val, join_style=1))
        return None

    def make(self):
        # self.geometry = LinearRing(self.points)
        self.geometry = DrawToolShape(Polygon(self.points).buffer(self.buf_val, join_style=2))
        self.draw_app.in_action = False
        self.complete = True
        self.draw_app.app.inform.emit(_("[success] Done. Region completed."))

    def clean_up(self):
        self.draw_app.selected = []
        self.draw_app.apertures_table.clearSelection()
        self.draw_app.plot_all()

    def on_key(self, key):
        if key == 'Backspace' or key == QtCore.Qt.Key_Backspace:
            if len(self.points) > 0:
                self.points = self.points[0:-1]
                # Remove any previous utility shape
                self.draw_app.tool_shape.clear(update=False)
                geo = self.utility_geometry(data=(self.draw_app.snap_x, self.draw_app.snap_y))
                self.draw_app.draw_utility_geometry(geo=geo)
                return _("Backtracked one point ...")


class FCTrack(FCRegion):
    """
    Resulting type: Polygon
    """

    def make(self):

        self.geometry = DrawToolShape(LineString(self.points).buffer(self.buf_val))
        self.name = 'track'

        self.draw_app.in_action = False
        self.complete = True
        self.draw_app.app.inform.emit(_("[success] Done. Path completed."))

    def clean_up(self):
        self.draw_app.selected = []
        self.draw_app.apertures_table.clearSelection()
        self.draw_app.plot_all()

    def utility_geometry(self, data=None):
        if len(self.points) > 0:
            temp_points = [x for x in self.points]
            temp_points.append(data)

            return DrawToolUtilityShape(LineString(temp_points).buffer(self.buf_val))
        return None

    def on_key(self, key):
        if key == 'Backspace' or key == QtCore.Qt.Key_Backspace:
            if len(self.points) > 0:
                self.points = self.points[0:-1]
                # Remove any previous utility shape
                self.draw_app.tool_shape.clear(update=False)
                geo = self.utility_geometry(data=(self.draw_app.snap_x, self.draw_app.snap_y))
                self.draw_app.draw_utility_geometry(geo=geo)
                return _("Backtracked one point ...")


class FCScale(FCShapeTool):
    def __init__(self, draw_app):
        FCShapeTool.__init__(self, draw_app)
        self.name = 'scale'

        # self.shape_buffer = self.draw_app.shape_buffer
        self.draw_app = draw_app
        self.app = draw_app.app

        self.start_msg = _("Scale the selected Gerber apertures ...")
        self.origin = (0, 0)

        if self.draw_app.app.ui.splitter.sizes()[0] == 0:
            self.draw_app.app.ui.splitter.setSizes([1, 1])
        self.activate_scale()

    def activate_scale(self):
        self.draw_app.hide_tool('all')
        self.draw_app.scale_tool_frame.show()

        try:
            self.draw_app.scale_button.clicked.disconnect()
        except TypeError:
            pass
        self.draw_app.scale_button.clicked.connect(self.on_scale_click)

    def deactivate_scale(self):
        self.draw_app.scale_button.clicked.disconnect()
        self.complete = True
        self.draw_app.select_tool("select")
        self.draw_app.hide_tool(self.name)

    def on_scale_click(self):
        self.draw_app.on_scale()
        self.deactivate_scale()


class FCBuffer(FCShapeTool):
    def __init__(self, draw_app):
        FCShapeTool.__init__(self, draw_app)
        self.name = 'buffer'

        # self.shape_buffer = self.draw_app.shape_buffer
        self.draw_app = draw_app
        self.app = draw_app.app

        self.start_msg = _("Buffer the selected apertures ...")
        self.origin = (0, 0)

        if self.draw_app.app.ui.splitter.sizes()[0] == 0:
            self.draw_app.app.ui.splitter.setSizes([1, 1])
        self.activate_buffer()

    def activate_buffer(self):
        self.draw_app.hide_tool('all')
        self.draw_app.buffer_tool_frame.show()

        try:
            self.draw_app.buffer_button.clicked.disconnect()
        except TypeError:
            pass
        self.draw_app.buffer_button.clicked.connect(self.on_buffer_click)

    def deactivate_buffer(self):
        self.draw_app.buffer_button.clicked.disconnect()
        self.complete = True
        self.draw_app.select_tool("select")
        self.draw_app.hide_tool(self.name)

    def on_buffer_click(self):
        self.draw_app.on_buffer()
        self.deactivate_buffer()


class FCApertureMove(FCShapeTool):
    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.name = 'move'

        # self.shape_buffer = self.draw_app.shape_buffer
        self.origin = None
        self.destination = None
        self.selected_apertures = []

        if self.draw_app.launched_from_shortcuts is True:
            self.draw_app.launched_from_shortcuts = False
            self.draw_app.app.inform.emit(_("Click on target location ..."))
        else:
            self.draw_app.app.inform.emit(_("Click on reference location ..."))
        self.current_storage = None
        self.geometry = []

        for index in self.draw_app.apertures_table.selectedIndexes():
            row = index.row()
            # on column 1 in tool tables we hold the aperture codes, and we retrieve them as strings
            aperture_on_row = self.draw_app.apertures_table.item(row, 1).text()
            self.selected_apertures.append(aperture_on_row)

        # Switch notebook to Selected page
        self.draw_app.app.ui.notebook.setCurrentWidget(self.draw_app.app.ui.selected_tab)

    def set_origin(self, origin):
        self.origin = origin

    def click(self, point):
        if len(self.draw_app.get_selected()) == 0:
            return "Nothing to move."

        if self.origin is None:
            self.set_origin(point)
            self.draw_app.app.inform.emit(_("Click on target location ..."))
            return
        else:
            self.destination = point
            self.make()

            # MS: always return to the Select Tool
            self.draw_app.select_tool("select")
            return

    def make(self):
        # Create new geometry
        dx = self.destination[0] - self.origin[0]
        dy = self.destination[1] - self.origin[1]
        sel_shapes_to_be_deleted = []

        for sel_dia in self.selected_apertures:
            self.current_storage = self.draw_app.storage_dict[sel_dia]['solid_geometry']
            for select_shape in self.draw_app.get_selected():
                if select_shape in self.current_storage:

                    self.geometry.append(DrawToolShape(affinity.translate(select_shape.geo, xoff=dx, yoff=dy)))
                    self.current_storage.remove(select_shape)
                    sel_shapes_to_be_deleted.append(select_shape)
                    self.draw_app.on_grb_shape_complete(self.current_storage)
                    self.geometry = []

            for shp in sel_shapes_to_be_deleted:
                self.draw_app.selected.remove(shp)
            sel_shapes_to_be_deleted = []

        self.draw_app.build_ui()
        self.draw_app.app.inform.emit(_("[success] Done. Apertures Move completed."))

    def clean_up(self):
        self.draw_app.selected = []
        self.draw_app.apertures_table.clearSelection()
        self.draw_app.plot_all()

    def utility_geometry(self, data=None):
        """
        Temporary geometry on screen while using this tool.

        :param data:
        :return:
        """
        geo_list = []

        if self.origin is None:
            return None

        if len(self.draw_app.get_selected()) == 0:
            return None

        dx = data[0] - self.origin[0]
        dy = data[1] - self.origin[1]
        for geom in self.draw_app.get_selected():
            geo_list.append(affinity.translate(geom.geo, xoff=dx, yoff=dy))
        return DrawToolUtilityShape(geo_list)


class FCApertureCopy(FCApertureMove):
    def __init__(self, draw_app):
        FCApertureMove.__init__(self, draw_app)
        self.name = 'copy'

    def make(self):
        # Create new geometry
        dx = self.destination[0] - self.origin[0]
        dy = self.destination[1] - self.origin[1]
        sel_shapes_to_be_deleted = []

        for sel_dia in self.selected_apertures:
            self.current_storage = self.draw_app.storage_dict[sel_dia]['solid_geometry']
            for select_shape in self.draw_app.get_selected():
                if select_shape in self.current_storage:
                    self.geometry.append(DrawToolShape(affinity.translate(select_shape.geo, xoff=dx, yoff=dy)))

                    sel_shapes_to_be_deleted.append(select_shape)
                    self.draw_app.on_grb_shape_complete(self.current_storage)
                    self.geometry = []

            for shp in sel_shapes_to_be_deleted:
                self.draw_app.selected.remove(shp)
            sel_shapes_to_be_deleted = []

        self.draw_app.build_ui()
        self.draw_app.app.inform.emit(_("[success] Done. Apertures copied."))


class FCApertureSelect(DrawTool):
    def __init__(self, grb_editor_app):
        DrawTool.__init__(self, grb_editor_app)
        self.name = 'select'
        self.origin = None

        self.grb_editor_app = grb_editor_app
        self.storage = self.grb_editor_app.storage_dict
        # self.selected = self.grb_editor_app.selected

        # here we store all shapes that were selected
        self.sel_storage = []

        self.grb_editor_app.apertures_table.clearSelection()
        self.grb_editor_app.hide_tool('all')
        self.grb_editor_app.hide_tool('select')

    def set_origin(self, origin):
        self.origin = origin

    def click(self, point):
        key_modifier = QtWidgets.QApplication.keyboardModifiers()
        if self.grb_editor_app.app.defaults["global_mselect_key"] == 'Control':
            if key_modifier == Qt.ControlModifier:
                pass
            else:
                self.grb_editor_app.selected = []
        else:
            if key_modifier == Qt.ShiftModifier:
                pass
            else:
                self.grb_editor_app.selected = []

    def click_release(self, point):
        self.grb_editor_app.apertures_table.clearSelection()
        sel_aperture = set()
        key_modifier = QtWidgets.QApplication.keyboardModifiers()

        for storage in self.grb_editor_app.storage_dict:
            for shape in self.grb_editor_app.storage_dict[storage]['solid_geometry']:
                if Point(point).within(shape.geo):
                    if (self.grb_editor_app.app.defaults["global_mselect_key"] == 'Control' and
                        key_modifier == Qt.ControlModifier) or \
                            (self.grb_editor_app.app.defaults["global_mselect_key"] == 'Shift' and
                             key_modifier == Qt.ShiftModifier):

                        if shape in self.draw_app.selected:
                            self.draw_app.selected.remove(shape)
                        else:
                            # add the object to the selected shapes
                            self.draw_app.selected.append(shape)
                            sel_aperture.add(storage)
                    else:
                        self.draw_app.selected.append(shape)
                        sel_aperture.add(storage)

        # select the aperture in the Apertures Table that is associated with the selected shape
        try:
            self.draw_app.apertures_table.cellPressed.disconnect()
        except:
            pass

        self.grb_editor_app.apertures_table.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        for aper in sel_aperture:
            for row in range(self.grb_editor_app.apertures_table.rowCount()):
                if str(aper) == self.grb_editor_app.apertures_table.item(row, 1).text():
                    self.grb_editor_app.apertures_table.selectRow(row)
                    self.draw_app.last_aperture_selected = aper
        self.grb_editor_app.apertures_table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        self.draw_app.apertures_table.cellPressed.connect(self.draw_app.on_row_selected)

        return ""

    def clean_up(self):
        self.draw_app.plot_all()


class FCTransform(FCShapeTool):
    def __init__(self, draw_app):
        FCShapeTool.__init__(self, draw_app)
        self.name = 'transformation'

        # self.shape_buffer = self.draw_app.shape_buffer
        self.draw_app = draw_app
        self.app = draw_app.app

        self.start_msg = _("Shape transformations ...")
        self.origin = (0, 0)
        self.draw_app.transform_tool.run()


class FlatCAMGrbEditor(QtCore.QObject):

    draw_shape_idx = -1

    def __init__(self, app):
        assert isinstance(app, FlatCAMApp.App), \
            "Expected the app to be a FlatCAMApp.App, got %s" % type(app)

        super(FlatCAMGrbEditor, self).__init__()

        self.app = app
        self.canvas = self.app.plotcanvas

        ## Current application units in Upper Case
        self.units = self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().upper()

        self.grb_edit_widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        self.grb_edit_widget.setLayout(layout)

        ## Page Title box (spacing between children)
        self.title_box = QtWidgets.QHBoxLayout()
        layout.addLayout(self.title_box)

        ## Page Title icon
        pixmap = QtGui.QPixmap('share/flatcam_icon32.png')
        self.icon = QtWidgets.QLabel()
        self.icon.setPixmap(pixmap)
        self.title_box.addWidget(self.icon, stretch=0)

        ## Title label
        self.title_label = QtWidgets.QLabel("<font size=5><b>%s</b></font>" % _('Gerber Editor'))
        self.title_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.title_box.addWidget(self.title_label, stretch=1)

        ## Object name
        self.name_box = QtWidgets.QHBoxLayout()
        layout.addLayout(self.name_box)
        name_label = QtWidgets.QLabel(_("Name:"))
        self.name_box.addWidget(name_label)
        self.name_entry = FCEntry()
        self.name_box.addWidget(self.name_entry)

        ## Box for custom widgets
        # This gets populated in offspring implementations.
        self.custom_box = QtWidgets.QVBoxLayout()
        layout.addLayout(self.custom_box)


        #### Gerber Apertures ####
        self.apertures_table_label = QtWidgets.QLabel(_('<b>Apertures:</b>'))
        self.apertures_table_label.setToolTip(
            _("Apertures Table for the Gerber Object.")
        )
        self.custom_box.addWidget(self.apertures_table_label)

        self.apertures_table = FCTable()
        # delegate = SpinBoxDelegate(units=self.units)
        # self.apertures_table.setItemDelegateForColumn(1, delegate)

        self.custom_box.addWidget(self.apertures_table)

        self.apertures_table.setColumnCount(5)
        self.apertures_table.setHorizontalHeaderLabels(['#', _('Code'), _('Type'), _('Size'), _('Dim')])
        self.apertures_table.setSortingEnabled(False)

        self.apertures_table.horizontalHeaderItem(0).setToolTip(
            _("Index"))
        self.apertures_table.horizontalHeaderItem(1).setToolTip(
            _("Aperture Code"))
        self.apertures_table.horizontalHeaderItem(2).setToolTip(
            _("Type of aperture: circular, rectangle, macros etc"))
        self.apertures_table.horizontalHeaderItem(4).setToolTip(
            _("Aperture Size:"))
        self.apertures_table.horizontalHeaderItem(4).setToolTip(
            _("Aperture Dimensions:\n"
              " - (width, height) for R, O type.\n"
              " - (dia, nVertices) for P type"))

        self.empty_label = QtWidgets.QLabel('')
        self.custom_box.addWidget(self.empty_label)

        # add a frame and inside add a vertical box layout. Inside this vbox layout I add all the Apertures widgets
        # this way I can hide/show the frame
        self.apertures_frame = QtWidgets.QFrame()
        self.apertures_frame.setContentsMargins(0, 0, 0, 0)
        self.custom_box.addWidget(self.apertures_frame)
        self.apertures_box = QtWidgets.QVBoxLayout()
        self.apertures_box.setContentsMargins(0, 0, 0, 0)
        self.apertures_frame.setLayout(self.apertures_box)

        #### Add/Delete an new Aperture ####

        grid1 = QtWidgets.QGridLayout()
        self.apertures_box.addLayout(grid1)

        apcode_lbl = QtWidgets.QLabel(_('Aperture Code:'))
        apcode_lbl.setToolTip(
        _("Code for the new aperture")
        )
        grid1.addWidget(apcode_lbl, 1, 0)

        self.apcode_entry = FCEntry()
        self.apcode_entry.setValidator(QtGui.QIntValidator(0, 999))
        grid1.addWidget(self.apcode_entry, 1, 1)

        apsize_lbl = QtWidgets.QLabel(_('Aperture Size:'))
        apsize_lbl.setToolTip(
        _("Size for the new aperture.\n"
          "If aperture type is 'R' or 'O' then\n"
          "this value is automatically\n"
          "calculated as:\n"
          "sqrt(width**2 + height**2)")
        )
        grid1.addWidget(apsize_lbl, 2, 0)

        self.apsize_entry = FCEntry()
        self.apsize_entry.setValidator(QtGui.QDoubleValidator(0.0001, 99.9999, 4))
        grid1.addWidget(self.apsize_entry, 2, 1)

        aptype_lbl = QtWidgets.QLabel(_('Aperture Type:'))
        aptype_lbl.setToolTip(
        _("Select the type of new aperture. Can be:\n"
          "C = circular\n"
          "R = rectangular\n"
          "O = oblong")
        )
        grid1.addWidget(aptype_lbl, 3, 0)

        self.aptype_cb = FCComboBox()
        self.aptype_cb.addItems(['C', 'R', 'O'])
        grid1.addWidget(self.aptype_cb, 3, 1)

        self.apdim_lbl = QtWidgets.QLabel(_('Aperture Dim:'))
        self.apdim_lbl.setToolTip(
        _("Dimensions for the new aperture.\n"
          "Active only for rectangular apertures (type R).\n"
          "The format is (width, height)")
        )
        grid1.addWidget(self.apdim_lbl, 4, 0)

        self.apdim_entry = EvalEntry()
        grid1.addWidget(self.apdim_entry, 4, 1)

        apadd_lbl = QtWidgets.QLabel('<b>%s</b>' % _('Add Aperture:'))
        apadd_lbl.setToolTip(
            _("Add an aperture to the aperture list")
        )
        grid1.addWidget(apadd_lbl, 5, 0)

        self.addaperture_btn = QtWidgets.QPushButton(_('Go'))
        self.addaperture_btn.setToolTip(
           _( "Add a new aperture to the aperture list.")
        )
        grid1.addWidget(self.addaperture_btn, 5, 1)

        apdelete_lbl = QtWidgets.QLabel('<b>%s</b>' % _('Del Aperture:'))
        apdelete_lbl.setToolTip(
            _( "Delete a aperture in the aperture list.\n"
               "It will delete also the associated geometry.")
        )
        grid1.addWidget(apdelete_lbl, 6, 0)

        self.delaperture_btn = QtWidgets.QPushButton(_('Go'))
        self.delaperture_btn.setToolTip(
           _( "Delete a aperture in the aperture list")
        )
        grid1.addWidget(self.delaperture_btn, 6, 1)

        ### BUFFER TOOL ###

        self.buffer_tool_frame = QtWidgets.QFrame()
        self.buffer_tool_frame.setContentsMargins(0, 0, 0, 0)
        self.custom_box.addWidget(self.buffer_tool_frame)
        self.buffer_tools_box = QtWidgets.QVBoxLayout()
        self.buffer_tools_box.setContentsMargins(0, 0, 0, 0)
        self.buffer_tool_frame.setLayout(self.buffer_tools_box)
        self.buffer_tool_frame.hide()

        # Title
        buf_title_lbl = QtWidgets.QLabel('<b>%s</b>' % _('Buffer Aperture:'))
        buf_title_lbl.setToolTip(
            _("Buffer a aperture in the aperture list")
        )
        self.buffer_tools_box.addWidget(buf_title_lbl)

        # Form Layout
        buf_form_layout = QtWidgets.QFormLayout()
        self.buffer_tools_box.addLayout(buf_form_layout)

        # Buffer distance
        self.buffer_distance_entry = FCEntry()
        buf_form_layout.addRow(_("Buffer distance:"), self.buffer_distance_entry)
        self.buffer_corner_lbl = QtWidgets.QLabel(_("Buffer corner:"))
        self.buffer_corner_lbl.setToolTip(
            _("There are 3 types of corners:\n"
              " - 'Round': the corner is rounded.\n"
              " - 'Square:' the corner is met in a sharp angle.\n"
              " - 'Beveled:' the corner is a line that directly connects the features meeting in the corner")
        )
        self.buffer_corner_cb = FCComboBox()
        self.buffer_corner_cb.addItem(_("Round"))
        self.buffer_corner_cb.addItem(_("Square"))
        self.buffer_corner_cb.addItem(_("Beveled"))
        buf_form_layout.addRow(self.buffer_corner_lbl, self.buffer_corner_cb)

        # Buttons
        hlay_buf = QtWidgets.QHBoxLayout()
        self.buffer_tools_box.addLayout(hlay_buf)

        self.buffer_button = QtWidgets.QPushButton(_("Buffer"))
        hlay_buf.addWidget(self.buffer_button)

        ### SCALE TOOL ###

        self.scale_tool_frame = QtWidgets.QFrame()
        self.scale_tool_frame.setContentsMargins(0, 0, 0, 0)
        self.custom_box.addWidget(self.scale_tool_frame)
        self.scale_tools_box = QtWidgets.QVBoxLayout()
        self.scale_tools_box.setContentsMargins(0, 0, 0, 0)
        self.scale_tool_frame.setLayout(self.scale_tools_box)
        self.scale_tool_frame.hide()

        # Title
        scale_title_lbl = QtWidgets.QLabel('<b>%s</b>' % _('Scale Aperture:'))
        scale_title_lbl.setToolTip(
            _("Scale a aperture in the aperture list")
        )
        self.scale_tools_box.addWidget(scale_title_lbl)

        # Form Layout
        scale_form_layout = QtWidgets.QFormLayout()
        self.scale_tools_box.addLayout(scale_form_layout)

        self.scale_factor_lbl = QtWidgets.QLabel(_("Scale factor:"))
        self.scale_factor_lbl.setToolTip(
            _("The factor by which to scale the selected aperture.\n"
              "Values can be between 0.0000 and 999.9999")
        )
        self.scale_factor_entry = FCEntry()
        self.scale_factor_entry.setValidator(QtGui.QDoubleValidator(0.0000, 999.9999, 4))
        scale_form_layout.addRow(self.scale_factor_lbl, self.scale_factor_entry)

        # Buttons
        hlay_scale = QtWidgets.QHBoxLayout()
        self.scale_tools_box.addLayout(hlay_scale)

        self.scale_button = QtWidgets.QPushButton(_("Scale"))
        hlay_scale.addWidget(self.scale_button)

        # add a frame and inside add a vertical box layout. Inside this vbox layout I add
        # all the add Pad array  widgets
        # this way I can hide/show the frame
        self.array_frame = QtWidgets.QFrame()
        self.array_frame.setContentsMargins(0, 0, 0, 0)
        self.custom_box.addWidget(self.array_frame)
        self.array_box = QtWidgets.QVBoxLayout()
        self.array_box.setContentsMargins(0, 0, 0, 0)
        self.array_frame.setLayout(self.array_box)

        #### Add Pad Array ####
        self.emptyarray_label = QtWidgets.QLabel('')
        self.array_box.addWidget(self.emptyarray_label)

        self.padarray_label = QtWidgets.QLabel('<b>%s</b>' % _("Add Pad Array"))
        self.padarray_label.setToolTip(
            _("Add an array of pads (linear or circular array)")
        )
        self.array_box.addWidget(self.padarray_label)

        self.array_type_combo = FCComboBox()
        self.array_type_combo.setToolTip(
           _( "Select the type of pads array to create.\n"
            "It can be Linear X(Y) or Circular")
        )
        self.array_type_combo.addItem(_("Linear"))
        self.array_type_combo.addItem(_("Circular"))

        self.array_box.addWidget(self.array_type_combo)

        self.array_form = QtWidgets.QFormLayout()
        self.array_box.addLayout(self.array_form)

        self.pad_array_size_label = QtWidgets.QLabel(_('Nr of pads:'))
        self.pad_array_size_label.setToolTip(
            _("Specify how many pads to be in the array.")
        )
        self.pad_array_size_label.setFixedWidth(100)

        self.pad_array_size_entry = LengthEntry()
        self.array_form.addRow(self.pad_array_size_label, self.pad_array_size_entry)

        self.array_linear_frame = QtWidgets.QFrame()
        self.array_linear_frame.setContentsMargins(0, 0, 0, 0)
        self.array_box.addWidget(self.array_linear_frame)
        self.linear_box = QtWidgets.QVBoxLayout()
        self.linear_box.setContentsMargins(0, 0, 0, 0)
        self.array_linear_frame.setLayout(self.linear_box)

        self.linear_form = QtWidgets.QFormLayout()
        self.linear_box.addLayout(self.linear_form)

        self.pad_axis_label = QtWidgets.QLabel(_('Direction:'))
        self.pad_axis_label.setToolTip(
            _("Direction on which the linear array is oriented:\n"
            "- 'X' - horizontal axis \n"
            "- 'Y' - vertical axis or \n"
            "- 'Angle' - a custom angle for the array inclination")
        )
        self.pad_axis_label.setFixedWidth(100)

        self.pad_axis_radio = RadioSet([{'label': 'X', 'value': 'X'},
                                          {'label': 'Y', 'value': 'Y'},
                                          {'label': _('Angle'), 'value': 'A'}])
        self.pad_axis_radio.set_value('X')
        self.linear_form.addRow(self.pad_axis_label, self.pad_axis_radio)

        self.pad_pitch_label = QtWidgets.QLabel(_('Pitch:'))
        self.pad_pitch_label.setToolTip(
            _("Pitch = Distance between elements of the array.")
        )
        self.pad_pitch_label.setFixedWidth(100)

        self.pad_pitch_entry = LengthEntry()
        self.linear_form.addRow(self.pad_pitch_label, self.pad_pitch_entry)

        self.linear_angle_label = QtWidgets.QLabel(_('Angle:'))
        self.linear_angle_label.setToolTip(
           _( "Angle at which the linear array is placed.\n"
            "The precision is of max 2 decimals.\n"
            "Min value is: -359.99 degrees.\n"
            "Max value is:  360.00 degrees.")
        )
        self.linear_angle_label.setFixedWidth(100)

        self.linear_angle_spinner = FCDoubleSpinner()
        self.linear_angle_spinner.set_precision(2)
        self.linear_angle_spinner.setRange(-359.99, 360.00)
        self.linear_form.addRow(self.linear_angle_label, self.linear_angle_spinner)

        self.array_circular_frame = QtWidgets.QFrame()
        self.array_circular_frame.setContentsMargins(0, 0, 0, 0)
        self.array_box.addWidget(self.array_circular_frame)
        self.circular_box = QtWidgets.QVBoxLayout()
        self.circular_box.setContentsMargins(0, 0, 0, 0)
        self.array_circular_frame.setLayout(self.circular_box)

        self.pad_direction_label = QtWidgets.QLabel(_('Direction:'))
        self.pad_direction_label.setToolTip(
           _( "Direction for circular array."
            "Can be CW = clockwise or CCW = counter clockwise.")
        )
        self.pad_direction_label.setFixedWidth(100)

        self.circular_form = QtWidgets.QFormLayout()
        self.circular_box.addLayout(self.circular_form)

        self.pad_direction_radio = RadioSet([{'label': 'CW', 'value': 'CW'},
                                               {'label': 'CCW.', 'value': 'CCW'}])
        self.pad_direction_radio.set_value('CW')
        self.circular_form.addRow(self.pad_direction_label, self.pad_direction_radio)

        self.pad_angle_label = QtWidgets.QLabel(_('Angle:'))
        self.pad_angle_label.setToolTip(
            _("Angle at which each element in circular array is placed.")
        )
        self.pad_angle_label.setFixedWidth(100)

        self.pad_angle_entry = LengthEntry()
        self.circular_form.addRow(self.pad_angle_label, self.pad_angle_entry)

        self.array_circular_frame.hide()

        self.linear_angle_spinner.hide()
        self.linear_angle_label.hide()

        self.array_frame.hide()

        self.custom_box.addStretch()

        ## Toolbar events and properties
        self.tools_gerber = {
            "select": {"button": self.app.ui.grb_select_btn,
                       "constructor": FCApertureSelect},
            "pad": {"button": self.app.ui.grb_add_pad_btn,
                              "constructor": FCPad},
            "array": {"button": self.app.ui.add_pad_ar_btn,
                    "constructor": FCPadArray},
            "track": {"button": self.app.ui.grb_add_track_btn,
                              "constructor": FCTrack},
            "region": {"button": self.app.ui.grb_add_region_btn,
                              "constructor": FCRegion},
            "poligonize": {"button": self.app.ui.grb_convert_poly_btn,
                       "constructor": FCPoligonize},
            "buffer": {"button": self.app.ui.aperture_buffer_btn,
                                "constructor": FCBuffer},
            "scale": {"button": self.app.ui.aperture_scale_btn,
                                "constructor": FCScale},
            "copy": {"button": self.app.ui.aperture_copy_btn,
                     "constructor": FCApertureCopy},
            "transform": {"button": self.app.ui.grb_transform_btn,
                          "constructor": FCTransform},
            "move": {"button": self.app.ui.aperture_move_btn,
                     "constructor": FCApertureMove},
        }

        ### Data
        self.active_tool = None

        self.storage_dict = {}
        self.current_storage = []

        self.sorted_apid =[]

        self.new_apertures = {}
        self.new_aperture_macros = {}

        # store here the plot promises, if empty the delayed plot will be activated
        self.grb_plot_promises = []

        # dictionary to store the tool_row and aperture codes in Tool_table
        # it will be updated everytime self.build_ui() is called
        self.olddia_newdia = {}

        self.tool2tooldia = {}

        # this will store the value for the last selected tool, for use after clicking on canvas when the selection
        # is cleared but as a side effect also the selected tool is cleared
        self.last_aperture_selected = None
        self.utility = []

        # this will flag if the Editor "tools" are launched from key shortcuts (True) or from menu toolbar (False)
        self.launched_from_shortcuts = False

        # this var will store the state of the toolbar before starting the editor
        self.toolbar_old_state = False

        # holds flattened geometry
        self.flat_geometry = []

        # Init GUI
        self.apdim_lbl.hide()
        self.apdim_entry.hide()
        self.gerber_obj = None
        self.gerber_obj_options = {}

        self.buffer_distance_entry.set_value(0.01)
        self.scale_factor_entry.set_value(1.0)

        # VisPy Visuals
        self.shapes = self.app.plotcanvas.new_shape_collection(layers=1)
        self.tool_shape = self.app.plotcanvas.new_shape_collection(layers=1)
        self.app.pool_recreated.connect(self.pool_recreated)

        # Remove from scene
        self.shapes.enabled = False
        self.tool_shape.enabled = False

        ## List of selected shapes.
        self.selected = []

        self.key = None  # Currently pressed key
        self.modifiers = None
        self.x = None  # Current mouse cursor pos
        self.y = None
        # Current snapped mouse pos
        self.snap_x = None
        self.snap_y = None
        self.pos = None

        # signal that there is an action active like polygon or path
        self.in_action = False
        # this will flag if the Editor "tools" are launched from key shortcuts (True) or from menu toolbar (False)
        self.launched_from_shortcuts = False

        def make_callback(thetool):
            def f():
                self.on_tool_select(thetool)
            return f

        for tool in self.tools_gerber:
            self.tools_gerber[tool]["button"].triggered.connect(make_callback(tool))  # Events
            self.tools_gerber[tool]["button"].setCheckable(True)  # Checkable

        self.options = {
            "global_gridx": 0.1,
            "global_gridy": 0.1,
            "snap_max": 0.05,
            "grid_snap": True,
            "corner_snap": False,
            "grid_gap_link": True
        }
        self.app.options_read_form()

        for option in self.options:
            if option in self.app.options:
                self.options[option] = self.app.options[option]

        # flag to show if the object was modified
        self.is_modified = False

        self.edited_obj_name = ""

        self.tool_row = 0

        # store the status of the editor so the Delete at object level will not work until the edit is finished
        self.editor_active = False

        def entry2option(option, entry):
            self.options[option] = float(entry.text())

        self.transform_tool = TransformEditorTool(self.app, self)

        # Signals
        self.buffer_button.clicked.connect(self.on_buffer)
        self.scale_button.clicked.connect(self.on_scale)

        self.app.ui.aperture_delete_btn.triggered.connect(self.on_delete_btn)
        self.name_entry.returnPressed.connect(self.on_name_activate)

        self.aptype_cb.currentIndexChanged[str].connect(self.on_aptype_changed)

        self.addaperture_btn.clicked.connect(self.on_aperture_add)
        self.delaperture_btn.clicked.connect(self.on_aperture_delete)
        self.apertures_table.cellPressed.connect(self.on_row_selected)

        self.app.ui.grb_add_pad_menuitem.triggered.connect(self.on_pad_add)
        self.app.ui.grb_add_pad_array_menuitem.triggered.connect(self.on_pad_add_array)

        self.app.ui.grb_add_track_menuitem.triggered.connect(self.on_track_add)
        self.app.ui.grb_add_region_menuitem.triggered.connect(self.on_region_add)

        self.app.ui.grb_convert_poly_menuitem.triggered.connect(self.on_poligonize)
        self.app.ui.grb_add_buffer_menuitem.triggered.connect(self.on_buffer)
        self.app.ui.grb_add_scale_menuitem.triggered.connect(self.on_scale)
        self.app.ui.grb_transform_menuitem.triggered.connect(self.transform_tool.run)

        self.app.ui.grb_copy_menuitem.triggered.connect(self.on_copy_button)
        self.app.ui.grb_delete_menuitem.triggered.connect(self.on_delete_btn)

        self.app.ui.grb_move_menuitem.triggered.connect(self.on_move_button)

        self.array_type_combo.currentIndexChanged.connect(self.on_array_type_combo)
        self.pad_axis_radio.activated_custom.connect(self.on_linear_angle_radio)

        # store the status of the editor so the Delete at object level will not work until the edit is finished
        self.editor_active = False

    def pool_recreated(self, pool):
        self.shapes.pool = pool
        self.tool_shape.pool = pool

    def set_ui(self):
        # updated units
        self.units = self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().upper()

        self.olddia_newdia.clear()
        self.tool2tooldia.clear()

        # update the olddia_newdia dict to make sure we have an updated state of the tool_table
        for key in self.storage_dict:
            self.olddia_newdia[key] = key

        sort_temp = []
        for aperture in self.olddia_newdia:
            sort_temp.append(int(aperture))
        self.sorted_apid = sorted(sort_temp)

        # populate self.intial_table_rows dict with the tool number as keys and aperture codes as values
        for i in range(len(self.sorted_apid)):
            tt_aperture = self.sorted_apid[i]
            self.tool2tooldia[i + 1] = tt_aperture

        if self.units == "IN":
            self.apsize_entry.set_value(0.039)
        else:
            self.apsize_entry.set_value(1.00)

        # Init GUI
        self.pad_array_size_entry.set_value(5)
        self.pad_pitch_entry.set_value(2.54)
        self.pad_angle_entry.set_value(12)
        self.pad_direction_radio.set_value('CW')
        self.pad_axis_radio.set_value('X')

    def build_ui(self, first_run=None):

        try:
            # if connected, disconnect the signal from the slot on item_changed as it creates issues
            self.apertures_table.itemChanged.disconnect()
        except:
            pass

        try:
            self.apertures_table.cellPressed.disconnect()
        except:
            pass

        # updated units
        self.units = self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().upper()

        # make a new name for the new Excellon object (the one with edited content)
        self.edited_obj_name = self.gerber_obj.options['name']
        self.name_entry.set_value(self.edited_obj_name)

        self.apertures_row = 0
        aper_no = self.apertures_row + 1

        sort = []
        for k, v in list(self.storage_dict.items()):
            sort.append(int(k))

        sorted_apertures = sorted(sort)

        sort = []
        for k, v in list(self.gerber_obj.aperture_macros.items()):
            sort.append(k)
        sorted_macros = sorted(sort)

        n = len(sorted_apertures) + len(sorted_macros)
        self.apertures_table.setRowCount(n)

        for ap_code in sorted_apertures:
            ap_code = str(ap_code)

            ap_id_item = QtWidgets.QTableWidgetItem('%d' % int(self.apertures_row + 1))
            ap_id_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.apertures_table.setItem(self.apertures_row, 0, ap_id_item)  # Tool name/id

            ap_code_item = QtWidgets.QTableWidgetItem(ap_code)
            ap_code_item.setFlags(QtCore.Qt.ItemIsEnabled)

            ap_type_item = QtWidgets.QTableWidgetItem(str(self.storage_dict[ap_code]['type']))
            ap_type_item.setFlags(QtCore.Qt.ItemIsEnabled)

            if str(self.storage_dict[ap_code]['type']) == 'R' or str(self.storage_dict[ap_code]['type']) == 'O':
                ap_dim_item = QtWidgets.QTableWidgetItem(
                    '%.4f, %.4f' % (self.storage_dict[ap_code]['width'],
                                    self.storage_dict[ap_code]['height']
                                    )
                )
                ap_dim_item.setFlags(QtCore.Qt.ItemIsEnabled)
            elif str(self.storage_dict[ap_code]['type']) == 'P':
                ap_dim_item = QtWidgets.QTableWidgetItem(
                    '%.4f, %.4f' % (self.storage_dict[ap_code]['diam'],
                                    self.storage_dict[ap_code]['nVertices'])
                )
                ap_dim_item.setFlags(QtCore.Qt.ItemIsEnabled)
            else:
                ap_dim_item = QtWidgets.QTableWidgetItem('')
                ap_dim_item.setFlags(QtCore.Qt.ItemIsEnabled)

            try:
                if self.storage_dict[ap_code]['size'] is not None:
                    ap_size_item = QtWidgets.QTableWidgetItem('%.4f' %
                                                              float(self.storage_dict[ap_code]['size']))
                else:
                    ap_size_item = QtWidgets.QTableWidgetItem('')
            except KeyError:
                ap_size_item = QtWidgets.QTableWidgetItem('')
            ap_size_item.setFlags(QtCore.Qt.ItemIsEnabled)

            self.apertures_table.setItem(self.apertures_row, 1, ap_code_item)  # Aperture Code
            self.apertures_table.setItem(self.apertures_row, 2, ap_type_item)  # Aperture Type
            self.apertures_table.setItem(self.apertures_row, 3, ap_size_item)  # Aperture Dimensions
            self.apertures_table.setItem(self.apertures_row, 4, ap_dim_item)  # Aperture Dimensions

            self.apertures_row += 1
            if first_run is True:
                # set now the last aperture selected
                self.last_aperture_selected = ap_code

        for ap_code in sorted_macros:
            ap_code = str(ap_code)

            ap_id_item = QtWidgets.QTableWidgetItem('%d' % int(self.apertures_row + 1))
            ap_id_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.apertures_table.setItem(self.apertures_row, 0, ap_id_item)  # Tool name/id

            ap_code_item = QtWidgets.QTableWidgetItem(ap_code)

            ap_type_item = QtWidgets.QTableWidgetItem('AM')
            ap_type_item.setFlags(QtCore.Qt.ItemIsEnabled)

            self.apertures_table.setItem(self.apertures_row, 1, ap_code_item)  # Aperture Code
            self.apertures_table.setItem(self.apertures_row, 2, ap_type_item)  # Aperture Type

            self.apertures_row += 1
            if first_run is True:
                # set now the last aperture selected
                self.last_aperture_selected = ap_code

        self.apertures_table.selectColumn(0)
        self.apertures_table.resizeColumnsToContents()
        self.apertures_table.resizeRowsToContents()

        vertical_header = self.apertures_table.verticalHeader()
        # vertical_header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        vertical_header.hide()
        self.apertures_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        horizontal_header = self.apertures_table.horizontalHeader()
        horizontal_header.setMinimumSectionSize(10)
        horizontal_header.setDefaultSectionSize(70)
        horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(0, 20)
        horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(4, QtWidgets.QHeaderView.Stretch)

        self.apertures_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.apertures_table.setSortingEnabled(False)
        self.apertures_table.setMinimumHeight(self.apertures_table.getHeight())
        self.apertures_table.setMaximumHeight(self.apertures_table.getHeight())

        # make sure no rows are selected so the user have to click the correct row, meaning selecting the correct tool
        self.apertures_table.clearSelection()

        # Remove anything else in the GUI Selected Tab
        self.app.ui.selected_scroll_area.takeWidget()
        # Put ourself in the GUI Selected Tab
        self.app.ui.selected_scroll_area.setWidget(self.grb_edit_widget)
        # Switch notebook to Selected page
        self.app.ui.notebook.setCurrentWidget(self.app.ui.selected_tab)

        # we reactivate the signals after the after the tool adding as we don't need to see the tool been populated
        self.apertures_table.itemChanged.connect(self.on_tool_edit)
        self.apertures_table.cellPressed.connect(self.on_row_selected)

        # for convenience set the next aperture code in the apcode field
        try:
            self.apcode_entry.set_value(max(self.tool2tooldia.values()) + 1)
        except ValueError:
            # this means that the edited object has no apertures so we start with 10 (Gerber specifications)
            self.apcode_entry.set_value(10)

    def on_aperture_add(self, apid=None):
        self.is_modified = True
        if apid:
            ap_id = apid
        else:
            try:
                ap_id = str(self.apcode_entry.get_value())
            except ValueError:
                self.app.inform.emit(_("[WARNING_NOTCL] Aperture code value is missing or wrong format. "
                                       "Add it and retry."))
                return
            if ap_id == '':
                self.app.inform.emit(_("[WARNING_NOTCL] Aperture code value is missing or wrong format. "
                                       "Add it and retry."))
                return

        if ap_id == '0':
            if ap_id not in self.olddia_newdia:
                self.storage_dict[ap_id] = {}
                self.storage_dict[ap_id]['type'] = 'REG'
                size_val = 0
                self.apsize_entry.set_value(size_val)
                self.storage_dict[ap_id]['size'] = size_val

                self.storage_dict[ap_id]['solid_geometry'] = []
                self.storage_dict[ap_id]['follow_geometry'] = []

                # self.olddia_newdia dict keeps the evidence on current aperture codes as keys and gets updated on values
                # each time a aperture code is edited or added
                self.olddia_newdia[ap_id] = ap_id
        else:
            if ap_id not in self.olddia_newdia:
                self.storage_dict[ap_id] = {}

                type_val = self.aptype_cb.currentText()
                self.storage_dict[ap_id]['type'] = type_val

                if type_val == 'R' or type_val == 'O':
                    try:
                        dims = self.apdim_entry.get_value()
                        self.storage_dict[ap_id]['width'] = dims[0]
                        self.storage_dict[ap_id]['height'] = dims[1]

                        size_val = math.sqrt((dims[0] ** 2) + (dims[1] ** 2))
                        self.apsize_entry.set_value(size_val)

                    except Exception as e:
                        log.error("FlatCAMGrbEditor.on_aperture_add() --> the R or O aperture dims has to be in a "
                                  "tuple format (x,y)\nError: %s" % str(e))
                        self.app.inform.emit(_("[WARNING_NOTCL] Aperture dimensions value is missing or wrong format. "
                                               "Add it in format (width, height) and retry."))
                        return
                else:
                    try:
                        size_val = float(self.apsize_entry.get_value())
                    except ValueError:
                        # try to convert comma to decimal point. if it's still not working error message and return
                        try:
                            size_val = float(self.apsize_entry.get_value().replace(',', '.'))
                            self.apsize_entry.set_value(size_val)
                        except ValueError:
                            self.app.inform.emit(_("[WARNING_NOTCL] Aperture size value is missing or wrong format. "
                                                   "Add it and retry."))
                            return
                self.storage_dict[ap_id]['size'] = size_val

                self.storage_dict[ap_id]['solid_geometry'] = []
                self.storage_dict[ap_id]['follow_geometry'] = []

                # self.olddia_newdia dict keeps the evidence on current aperture codes as keys and gets updated on values
                # each time a aperture code is edited or added
                self.olddia_newdia[ap_id] = ap_id
            else:
                self.app.inform.emit(_("[WARNING_NOTCL] Aperture already in the aperture table."))
                return

        # since we add a new tool, we update also the initial state of the tool_table through it's dictionary
        # we add a new entry in the tool2tooldia dict
        self.tool2tooldia[len(self.olddia_newdia)] = int(ap_id)

        self.app.inform.emit(_("[success] Added new aperture with code: {apid}").format(apid=str(ap_id)))

        self.build_ui()

        self.last_aperture_selected = ap_id

        # make a quick sort through the tool2tooldia dict so we find which row to select
        row_to_be_selected = None
        for key in sorted(self.tool2tooldia):
            if self.tool2tooldia[key] == int(ap_id):
                row_to_be_selected = int(key) - 1
                break
        self.apertures_table.selectRow(row_to_be_selected)

    def on_aperture_delete(self, apid=None):
        self.is_modified = True
        deleted_apcode_list = []
        deleted_tool_offset_list = []

        try:
            if apid is None or apid is False:
                # deleted_tool_dia = float(self.apertures_table.item(self.apertures_table.currentRow(), 1).text())
                for index in self.apertures_table.selectionModel().selectedRows():
                    row = index.row()
                    deleted_apcode_list.append(self.apertures_table.item(row, 1).text())
            else:
                if isinstance(apid, list):
                    for dd in apid:
                        deleted_apcode_list.append(dd)
                else:
                    deleted_apcode_list.append(apid)
        except:
            self.app.inform.emit(_("[WARNING_NOTCL] Select a tool in Tool Table"))
            return

        for deleted_aperture in deleted_apcode_list:
            # delete the storage used for that tool
            self.storage_dict.pop(deleted_aperture, None)

            # I've added this flag_del variable because dictionary don't like
            # having keys deleted while iterating through them
            flag_del = []
            for deleted_tool in self.tool2tooldia:
                if self.tool2tooldia[deleted_tool] == deleted_aperture:
                    flag_del.append(deleted_tool)

            if flag_del:
                for aperture_to_be_deleted in flag_del:
                    # delete the tool
                    self.tool2tooldia.pop(aperture_to_be_deleted, None)
                flag_del = []

            self.olddia_newdia.pop(deleted_aperture, None)

            self.app.inform.emit(_("[success] Deleted aperture with code: {del_dia}").format(
                del_dia=str(deleted_aperture)))

        self.plot_all()
        self.build_ui()

    def on_tool_edit(self, item_changed):

        # if connected, disconnect the signal from the slot on item_changed as it creates issues
        self.apertures_table.itemChanged.disconnect()
        # self.apertures_table.cellPressed.disconnect()

        self.is_modified = True
        geometry = []
        current_table_dia_edited = None

        if self.apertures_table.currentItem() is not None:
            try:
                current_table_dia_edited = float(self.apertures_table.currentItem().text())
            except ValueError as e:
                log.debug("FlatCAMExcEditor.on_tool_edit() --> %s" % str(e))
                self.apertures_table.setCurrentItem(None)
                return

        row_of_item_changed = self.apertures_table.currentRow()

        # rows start with 0, tools start with 1 so we adjust the value by 1
        key_in_tool2tooldia = row_of_item_changed + 1

        dia_changed = self.tool2tooldia[key_in_tool2tooldia]

        # aperture code is not used so we create a new tool with the desired diameter
        if current_table_dia_edited not in self.olddia_newdia.values():
            # update the dict that holds as keys our initial diameters and as values the edited diameters
            self.olddia_newdia[dia_changed] = current_table_dia_edited
            # update the dict that holds tool_no as key and tool_dia as value
            self.tool2tooldia[key_in_tool2tooldia] = current_table_dia_edited

            # update the tool offset
            modified_offset = self.gerber_obj.tool_offset.pop(dia_changed)
            self.gerber_obj.tool_offset[current_table_dia_edited] = modified_offset

            self.plot_all()
        else:
            # aperture code is already in use so we move the pads from the prior tool to the new tool
            factor = current_table_dia_edited / dia_changed
            for shape in self.storage_dict[dia_changed].get_objects():
                geometry.append(DrawToolShape(
                    MultiLineString([affinity.scale(subgeo, xfact=factor, yfact=factor) for subgeo in shape.geo])))

                self.points_edit[current_table_dia_edited].append((0, 0))
            self.add_gerber_shape(geometry, self.storage_dict[current_table_dia_edited])

            self.on_aperture_delete(apid=dia_changed)

            # delete the tool offset
            self.gerber_obj.tool_offset.pop(dia_changed, None)

        # we reactivate the signals after the after the tool editing
        self.apertures_table.itemChanged.connect(self.on_tool_edit)
        # self.apertures_table.cellPressed.connect(self.on_row_selected)

    def on_name_activate(self):
        self.edited_obj_name = self.name_entry.get_value()

    def on_aptype_changed(self, current_text):
        if current_text == 'R' or current_text == 'O':
            self.apdim_lbl.show()
            self.apdim_entry.show()
            self.apsize_entry.setReadOnly(True)
        else:
            self.apdim_lbl.hide()
            self.apdim_entry.hide()
            self.apsize_entry.setReadOnly(False)

    def activate_grb_editor(self):
        # adjust the status of the menu entries related to the editor
        self.app.ui.menueditedit.setDisabled(True)
        self.app.ui.menueditok.setDisabled(False)
        # adjust the visibility of some of the canvas context menu
        self.app.ui.popmenu_edit.setVisible(False)
        self.app.ui.popmenu_save.setVisible(True)

        self.connect_canvas_event_handlers()

        # init working objects
        self.storage_dict = {}
        self.current_storage = []
        self.sorted_apid = []
        self.new_apertures = {}
        self.new_aperture_macros = {}
        self.grb_plot_promises = []
        self.olddia_newdia = {}
        self.tool2tooldia = {}

        self.shapes.enabled = True
        self.tool_shape.enabled = True

        self.app.ui.snap_max_dist_entry.setEnabled(True)
        self.app.ui.corner_snap_btn.setEnabled(True)
        self.app.ui.snap_magnet.setVisible(True)
        self.app.ui.corner_snap_btn.setVisible(True)

        self.app.ui.grb_editor_menu.setDisabled(False)
        self.app.ui.grb_editor_menu.menuAction().setVisible(True)

        self.app.ui.update_obj_btn.setEnabled(True)
        self.app.ui.grb_editor_cmenu.setEnabled(True)

        self.app.ui.grb_edit_toolbar.setDisabled(False)
        self.app.ui.grb_edit_toolbar.setVisible(True)
        # self.app.ui.snap_toolbar.setDisabled(False)

        # start with GRID toolbar activated
        if self.app.ui.grid_snap_btn.isChecked() is False:
            self.app.ui.grid_snap_btn.trigger()

        # adjust the visibility of some of the canvas context menu
        self.app.ui.popmenu_edit.setVisible(False)
        self.app.ui.popmenu_save.setVisible(True)

        # Tell the App that the editor is active
        self.editor_active = True

    def deactivate_grb_editor(self):
        # adjust the status of the menu entries related to the editor
        self.app.ui.menueditedit.setDisabled(False)
        self.app.ui.menueditok.setDisabled(True)
        # adjust the visibility of some of the canvas context menu
        self.app.ui.popmenu_edit.setVisible(True)
        self.app.ui.popmenu_save.setVisible(False)

        self.disconnect_canvas_event_handlers()
        self.clear()
        self.app.ui.grb_edit_toolbar.setDisabled(True)

        settings = QSettings("Open Source", "FlatCAM")
        if settings.contains("layout"):
            layout = settings.value('layout', type=str)
            if layout == 'standard':
                # self.app.ui.exc_edit_toolbar.setVisible(False)

                self.app.ui.snap_max_dist_entry.setEnabled(False)
                self.app.ui.corner_snap_btn.setEnabled(False)
                self.app.ui.snap_magnet.setVisible(False)
                self.app.ui.corner_snap_btn.setVisible(False)
            elif layout == 'compact':
                # self.app.ui.exc_edit_toolbar.setVisible(True)

                self.app.ui.snap_max_dist_entry.setEnabled(False)
                self.app.ui.corner_snap_btn.setEnabled(False)
                self.app.ui.snap_magnet.setVisible(True)
                self.app.ui.corner_snap_btn.setVisible(True)
        else:
            # self.app.ui.exc_edit_toolbar.setVisible(False)

            self.app.ui.snap_max_dist_entry.setEnabled(False)
            self.app.ui.corner_snap_btn.setEnabled(False)
            self.app.ui.snap_magnet.setVisible(False)
            self.app.ui.corner_snap_btn.setVisible(False)

        # set the Editor Toolbar visibility to what was before entering in the Editor
        self.app.ui.grb_edit_toolbar.setVisible(False) if self.toolbar_old_state is False \
            else self.app.ui.grb_edit_toolbar.setVisible(True)

        # Disable visuals
        self.shapes.enabled = False
        self.tool_shape.enabled = False
        # self.app.app_cursor.enabled = False

        # Tell the app that the editor is no longer active
        self.editor_active = False

        self.app.ui.grb_editor_menu.setDisabled(True)
        self.app.ui.grb_editor_menu.menuAction().setVisible(False)

        self.app.ui.update_obj_btn.setEnabled(False)

        self.app.ui.g_editor_cmenu.setEnabled(False)
        self.app.ui.grb_editor_cmenu.setEnabled(False)
        self.app.ui.e_editor_cmenu.setEnabled(False)

        # adjust the visibility of some of the canvas context menu
        self.app.ui.popmenu_edit.setVisible(True)
        self.app.ui.popmenu_save.setVisible(False)

        # Show original geometry
        if self.gerber_obj:
            self.gerber_obj.visible = True

    def connect_canvas_event_handlers(self):
        ## Canvas events

        # make sure that the shortcuts key and mouse events will no longer be linked to the methods from FlatCAMApp
        # but those from FlatCAMGeoEditor

        # first connect to new, then disconnect the old handlers
        # don't ask why but if there is nothing connected I've seen issues
        self.canvas.vis_connect('mouse_press', self.on_canvas_click)
        self.canvas.vis_connect('mouse_move', self.on_canvas_move)
        self.canvas.vis_connect('mouse_release', self.on_grb_click_release)

        self.app.plotcanvas.vis_disconnect('mouse_press', self.app.on_mouse_click_over_plot)
        self.app.plotcanvas.vis_disconnect('mouse_move', self.app.on_mouse_move_over_plot)
        self.app.plotcanvas.vis_disconnect('mouse_release', self.app.on_mouse_click_release_over_plot)
        self.app.plotcanvas.vis_disconnect('mouse_double_click', self.app.on_double_click_over_plot)
        self.app.collection.view.clicked.disconnect()

    def disconnect_canvas_event_handlers(self):

        # we restore the key and mouse control to FlatCAMApp method
        # first connect to new, then disconnect the old handlers
        # don't ask why but if there is nothing connected I've seen issues
        self.app.plotcanvas.vis_connect('mouse_press', self.app.on_mouse_click_over_plot)
        self.app.plotcanvas.vis_connect('mouse_move', self.app.on_mouse_move_over_plot)
        self.app.plotcanvas.vis_connect('mouse_release', self.app.on_mouse_click_release_over_plot)
        self.app.plotcanvas.vis_connect('mouse_double_click', self.app.on_double_click_over_plot)
        self.app.collection.view.clicked.connect(self.app.collection.on_mouse_down)

        self.canvas.vis_disconnect('mouse_press', self.on_canvas_click)
        self.canvas.vis_disconnect('mouse_move', self.on_canvas_move)
        self.canvas.vis_disconnect('mouse_release', self.on_grb_click_release)

    def clear(self):
        self.active_tool = None
        # self.shape_buffer = []
        self.selected = []

        self.shapes.clear(update=True)
        self.tool_shape.clear(update=True)

    def flatten(self, geometry=None, reset=True, pathonly=False):
        """
        Creates a list of non-iterable linear geometry objects.
        Polygons are expanded into its exterior pathonly param if specified.

        Results are placed in flat_geometry

        :param geometry: Shapely type or list or list of list of such.
        :param reset: Clears the contents of self.flat_geometry.
        :param pathonly: Expands polygons into linear elements from the exterior attribute.
        """

        if reset:
            self.flat_geometry = []
        ## If iterable, expand recursively.
        try:
            for geo in geometry:
                if geo is not None:
                    self.flatten(geometry=geo, reset=False, pathonly=pathonly)

        ## Not iterable, do the actual indexing and add.
        except TypeError:
            if pathonly and type(geometry) == Polygon:
                self.flat_geometry.append(geometry.exterior)
                self.flatten(geometry=geometry.interiors,
                             reset=False,
                             pathonly=True)
            else:
                self.flat_geometry.append(geometry)
        return self.flat_geometry

    def edit_fcgerber(self, orig_grb_obj):
        """
        Imports the geometry found in self.apertures from the given FlatCAM Gerber object
        into the editor.

        :param fcgeometry: FlatCAMExcellon
        :return: None
        """

        self.deactivate_grb_editor()
        self.activate_grb_editor()

        # create a reference to the source object
        self.gerber_obj = orig_grb_obj
        self.gerber_obj_options = orig_grb_obj.options

        # Hide original geometry
        orig_grb_obj.visible = False

        # Set selection tolerance
        # DrawToolShape.tolerance = fc_excellon.drawing_tolerance * 10

        self.select_tool("select")

        # we activate this after the initial build as we don't need to see the tool been populated
        self.apertures_table.itemChanged.connect(self.on_tool_edit)

        # and then add it to the storage elements (each storage elements is a member of a list

        def job_thread(self, apid):
            with self.app.proc_container.new(_("Adding aperture: %s geo ...") % str(apid)):
                solid_storage_elem = []
                follow_storage_elem = []

                self.storage_dict[apid] = {}

                # add the Gerber geometry to editor storage
                for k, v in self.gerber_obj.apertures[apid].items():
                    try:
                        if k == 'solid_geometry':
                            for geo in v:
                                if geo:
                                    self.add_gerber_shape(DrawToolShape(geo), solid_storage_elem)
                            self.storage_dict[apid][k] = solid_storage_elem
                        elif k == 'follow_geometry':
                            for geo in v:
                                if geo is not None:
                                    self.add_gerber_shape(DrawToolShape(geo), follow_storage_elem)
                            self.storage_dict[apid][k] = follow_storage_elem
                        else:
                            self.storage_dict[apid][k] = v
                    except Exception as e:
                        log.debug("FlatCAMGrbEditor.edit_fcgerber().job_thread() --> %s" % str(e))
                # Check promises and clear if exists
                while True:
                    try:
                        self.grb_plot_promises.remove(apid)
                        time.sleep(0.5)
                    except ValueError:
                        break

        for apid in self.gerber_obj.apertures:
            self.grb_plot_promises.append(apid)
            self.app.worker_task.emit({'fcn': job_thread, 'params': [self, apid]})

        # do the delayed plot only if there is something to plot (the gerber is not empty)
        if bool(self.gerber_obj.apertures):
            self.start_delayed_plot(check_period=1000)
        else:
            self.set_ui()
            # now that we have data (empty data actually), create the GUI interface and add it to the Tool Tab
            self.build_ui(first_run=True)

    def update_fcgerber(self, grb_obj):
        """
        Create a new Gerber object that contain the edited content of the source Gerber object

        :param grb_obj: FlatCAMGerber
        :return: None
        """

        new_grb_name = self.edited_obj_name

        # if the 'delayed plot' malfunctioned stop the QTimer
        try:
            self.plot_thread.stop()
        except:
            pass

        if "_edit" in self.edited_obj_name:
            try:
                id = int(self.edited_obj_name[-1]) + 1
                new_grb_name= self.edited_obj_name[:-1] + str(id)
            except ValueError:
                new_grb_name += "_1"
        else:
            new_grb_name = self.edited_obj_name + "_edit"

        self.app.worker_task.emit({'fcn': self.new_edited_gerber,
                                   'params': [new_grb_name]})

        # reset the tool table
        self.apertures_table.clear()

        self.apertures_table.setHorizontalHeaderLabels(['#', _('Code'), _('Type'), _('Size'), _('Dim')])
        self.last_aperture_selected = None

        # restore GUI to the Selected TAB
        # Remove anything else in the GUI
        self.app.ui.selected_scroll_area.takeWidget()
        # Switch notebook to Selected page
        self.app.ui.notebook.setCurrentWidget(self.app.ui.selected_tab)

    def update_options(self, obj):
        try:
            if not obj.options:
                obj.options = {}
                obj.options['xmin'] = 0
                obj.options['ymin'] = 0
                obj.options['xmax'] = 0
                obj.options['ymax'] = 0
                return True
            else:
                return False
        except AttributeError:
            obj.options = {}
            return True

    def new_edited_gerber(self, outname):
        """
        Creates a new Gerber object for the edited Gerber. Thread-safe.

        :param outname: Name of the resulting object. None causes the name to be that of the file.
        :type outname: str
        :return: None
        """

        self.app.log.debug("Update the Gerber object with edited content. Source is: %s" %
                           self.gerber_obj.options['name'].upper())

        out_name = outname
        local_storage_dict = deepcopy(self.storage_dict)

        # How the object should be initialized
        def obj_init(grb_obj, app_obj):

            poly_buffer = []
            follow_buffer = []

            for storage_apid, storage_val in local_storage_dict.items():
                grb_obj.apertures[storage_apid] = {}

                for k, v in storage_val.items():
                    if k == 'solid_geometry':
                        grb_obj.apertures[storage_apid][k] = []
                        for geo in v:
                            new_geo = deepcopy(geo.geo)
                            grb_obj.apertures[storage_apid][k].append(new_geo)
                            poly_buffer.append(new_geo)

                    elif k == 'follow_geometry':
                        grb_obj.apertures[storage_apid][k] = []
                        for geo in v:
                            new_geo = deepcopy(geo.geo)
                            grb_obj.apertures[storage_apid][k].append(new_geo)
                            follow_buffer.append(new_geo)
                    else:
                        grb_obj.apertures[storage_apid][k] = deepcopy(v)

            grb_obj.aperture_macros = deepcopy(self.gerber_obj.aperture_macros)

            new_poly = MultiPolygon(poly_buffer)
            new_poly = new_poly.buffer(0.00000001)
            new_poly = new_poly.buffer(-0.00000001)
            grb_obj.solid_geometry = new_poly

            grb_obj.follow_geometry = deepcopy(follow_buffer)

            for k, v in self.gerber_obj_options.items():
                if k == 'name':
                    grb_obj.options[k] = out_name
                else:
                    grb_obj.options[k] = deepcopy(v)

            grb_obj.source_file = []
            grb_obj.multigeo = False
            grb_obj.follow = False

            try:
                grb_obj.create_geometry()
            except KeyError:
                self.app.inform.emit(
                   _( "[ERROR_NOTCL] There are no Aperture definitions in the file. Aborting Gerber creation.")
                )
            except:
                msg = _("[ERROR] An internal error has ocurred. See shell.\n")
                msg += traceback.format_exc()
                app_obj.inform.emit(msg)
                raise
                # raise

        with self.app.proc_container.new(_("Creating Gerber.")):
            try:
                self.app.new_object("gerber", outname, obj_init)
            except Exception as e:
                log.error("Error on object creation: %s" % str(e))
                self.app.progress.emit(100)
                return

            self.app.inform.emit(_("[success] Gerber editing finished."))
            # self.progress.emit(100)

    def on_tool_select(self, tool):
        """
        Behavior of the toolbar. Tool initialization.

        :rtype : None
        """
        current_tool = tool

        self.app.log.debug("on_tool_select('%s')" % tool)

        if self.last_aperture_selected is None and current_tool is not 'select':
            # self.draw_app.select_tool('select')
            self.complete = True
            current_tool = 'select'
            self.app.inform.emit(_("[WARNING_NOTCL] Cancelled. No aperture is selected"))

        # This is to make the group behave as radio group
        if current_tool in self.tools_gerber:
            if self.tools_gerber[current_tool]["button"].isChecked():
                self.app.log.debug("%s is checked." % current_tool)
                for t in self.tools_gerber:
                    if t != current_tool:
                        self.tools_gerber[t]["button"].setChecked(False)

                # this is where the Editor toolbar classes (button's) are instantiated
                self.active_tool = self.tools_gerber[current_tool]["constructor"](self)
                # self.app.inform.emit(self.active_tool.start_msg)
            else:
                self.app.log.debug("%s is NOT checked." % current_tool)
                for t in self.tools_gerber:
                    self.tools_gerber[t]["button"].setChecked(False)

                self.select_tool('select')
                self.active_tool = FCApertureSelect(self)

    def on_row_selected(self, row, col):
        if col == 0:
            key_modifier = QtWidgets.QApplication.keyboardModifiers()
            if self.app.defaults["global_mselect_key"] == 'Control':
                modifier_to_use = Qt.ControlModifier
            else:
                modifier_to_use = Qt.ShiftModifier

            if key_modifier == modifier_to_use:
                pass
            else:
                self.selected = []

            try:
                # selected_apid = str(self.tool2tooldia[row + 1])
                selected_apid = self.apertures_table.item(row, 1).text()
                self.last_aperture_selected = copy(selected_apid)

                for obj in self.storage_dict[selected_apid]['solid_geometry']:
                    self.selected.append(obj)
            except Exception as e:
                self.app.log.debug(str(e))

            self.plot_all()

    def toolbar_tool_toggle(self, key):
        self.options[key] = self.sender().isChecked()
        return self.options[key]

    def on_grb_shape_complete(self, storage=None, specific_shape=None):
        self.app.log.debug("on_shape_complete()")

        if specific_shape:
            geo = specific_shape
        else:
            geo = self.active_tool.geometry
            if geo is None:
                return

        if storage is not None:
            # Add shape
            self.add_gerber_shape(geo, storage)
        else:
            stora = self.storage_dict[self.last_aperture_selected]['solid_geometry']
            self.add_gerber_shape(geo, storage=stora)

        # Remove any utility shapes
        self.delete_utility_geometry()
        self.tool_shape.clear(update=True)

        # Replot and reset tool.
        self.plot_all()

    def add_gerber_shape(self, shape, storage):
        """
        Adds a shape to the shape storage.

        :param shape: Shape to be added.
        :type shape: DrawToolShape
        :return: None
        """
        # List of DrawToolShape?

        if isinstance(shape, list):
            for subshape in shape:
                self.add_gerber_shape(subshape, storage)
            return

        assert isinstance(shape, DrawToolShape), \
            "Expected a DrawToolShape, got %s" % str(type(shape))

        assert shape.geo is not None, \
            "Shape object has empty geometry (None)"

        assert (isinstance(shape.geo, list) and len(shape.geo) > 0) or \
               not isinstance(shape.geo, list), \
            "Shape objects has empty geometry ([])"

        if isinstance(shape, DrawToolUtilityShape):
            self.utility.append(shape)
        else:
            storage.append(shape)  # TODO: Check performance

    def on_canvas_click(self, event):
        """
        event.x and .y have canvas coordinates
        event.xdaya and .ydata have plot coordinates

        :param event: Event object dispatched by Matplotlib
        :return: None
        """

        if event.button is 1:
            self.app.ui.rel_position_label.setText("<b>Dx</b>: %.4f&nbsp;&nbsp;  <b>Dy</b>: "
                                                   "%.4f&nbsp;&nbsp;&nbsp;&nbsp;" % (0, 0))
            self.pos = self.canvas.vispy_canvas.translate_coords(event.pos)

            ### Snap coordinates
            x, y = self.app.geo_editor.snap(self.pos[0], self.pos[1])

            self.pos = (x, y)

            # Selection with left mouse button
            if self.active_tool is not None and event.button is 1:
                # Dispatch event to active_tool
                # msg = self.active_tool.click(self.app.geo_editor.snap(event.xdata, event.ydata))
                msg = self.active_tool.click(self.app.geo_editor.snap(self.pos[0], self.pos[1]))

                # If it is a shape generating tool
                if isinstance(self.active_tool, FCShapeTool) and self.active_tool.complete:
                    if self.current_storage is not None:
                        self.on_grb_shape_complete(self.current_storage)
                        self.build_ui()
                    # MS: always return to the Select Tool if modifier key is not pressed
                    # else return to the current tool
                    key_modifier = QtWidgets.QApplication.keyboardModifiers()
                    if self.app.defaults["global_mselect_key"] == 'Control':
                        modifier_to_use = Qt.ControlModifier
                    else:
                        modifier_to_use = Qt.ShiftModifier
                    # if modifier key is pressed then we add to the selected list the current shape but if it's already
                    # in the selected list, we removed it. Therefore first click selects, second deselects.
                    if key_modifier == modifier_to_use:
                        self.select_tool(self.active_tool.name)
                    else:
                        self.select_tool("select")
                        return

                if isinstance(self.active_tool, FCApertureSelect):
                    # self.app.log.debug("Replotting after click.")
                    self.plot_all()
            else:
                self.app.log.debug("No active tool to respond to click!")

    def on_grb_click_release(self, event):
        pos_canvas = self.canvas.vispy_canvas.translate_coords(event.pos)

        self.modifiers = QtWidgets.QApplication.keyboardModifiers()

        if self.app.grid_status():
            pos = self.app.geo_editor.snap(pos_canvas[0], pos_canvas[1])
        else:
            pos = (pos_canvas[0], pos_canvas[1])

        # if the released mouse button was RMB then test if it was a panning motion or not, if not it was a context
        # canvas menu
        try:
            if event.button == 2:  # right click
                if self.app.panning_action is True:
                    self.app.panning_action = False
                else:
                    if self.in_action is False:
                        self.app.cursor = QtGui.QCursor()
                        self.app.ui.popMenu.popup(self.app.cursor.pos())
                    else:
                        # if right click on canvas and the active tool need to be finished (like Path or Polygon)
                        # right mouse click will finish the action
                        if isinstance(self.active_tool, FCShapeTool):
                            self.active_tool.click(self.app.geo_editor.snap(self.x, self.y))
                            self.active_tool.make()
                            if self.active_tool.complete:
                                self.on_grb_shape_complete()
                                self.app.inform.emit(_("[success] Done."))

                                # MS: always return to the Select Tool if modifier key is not pressed
                                # else return to the current tool
                                key_modifier = QtWidgets.QApplication.keyboardModifiers()
                                if (self.app.defaults["global_mselect_key"] == 'Control' and
                                    key_modifier == Qt.ControlModifier) or \
                                        (self.app.defaults["global_mselect_key"] == 'Shift' and
                                         key_modifier == Qt.ShiftModifier):

                                    self.select_tool(self.active_tool.name)
                                else:
                                    self.select_tool("select")
        except Exception as e:
            log.warning("Error: %s" % str(e))
            raise

        # if the released mouse button was LMB then test if we had a right-to-left selection or a left-to-right
        # selection and then select a type of selection ("enclosing" or "touching")
        try:
            if event.button == 1:  # left click
                if self.app.selection_type is not None:
                    self.draw_selection_area_handler(self.pos, pos, self.app.selection_type)
                    self.app.selection_type = None

                elif isinstance(self.active_tool, FCApertureSelect):
                    # Dispatch event to active_tool
                    # msg = self.active_tool.click(self.app.geo_editor.snap(event.xdata, event.ydata))
                    # msg = self.active_tool.click_release((self.pos[0], self.pos[1]))
                    # self.app.inform.emit(msg)
                    self.active_tool.click_release((self.pos[0], self.pos[1]))

                    # if there are selected objects then plot them
                    if self.selected:
                        self.plot_all()
        except Exception as e:
            log.warning("Error: %s" % str(e))
            raise

    def draw_selection_area_handler(self, start_pos, end_pos, sel_type):
        """
        :param start_pos: mouse position when the selection LMB click was done
        :param end_pos: mouse position when the left mouse button is released
        :param sel_type: if True it's a left to right selection (enclosure), if False it's a 'touch' selection
        :type Bool
        :return:
        """
        poly_selection = Polygon([start_pos, (end_pos[0], start_pos[1]), end_pos, (start_pos[0], end_pos[1])])

        sel_aperture = set()
        self.apertures_table.clearSelection()

        self.app.delete_selection_shape()
        for storage in self.storage_dict:
            for obj in self.storage_dict[storage]['solid_geometry']:
                if (sel_type is True and poly_selection.contains(obj.geo)) or \
                        (sel_type is False and poly_selection.intersects(obj.geo)):
                    if self.key == self.app.defaults["global_mselect_key"]:
                        if obj in self.selected:
                            self.selected.remove(obj)
                        else:
                            # add the object to the selected shapes
                            self.selected.append(obj)
                            sel_aperture.add(storage)
                    else:
                        self.selected.append(obj)
                        sel_aperture.add(storage)

        try:
            self.apertures_table.cellPressed.disconnect()
        except:
            pass
        # select the aperture code of the selected geometry, in the tool table
        self.apertures_table.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        for aper in sel_aperture:
            for row in range(self.apertures_table.rowCount()):
                if str(aper) == self.apertures_table.item(row, 1).text():
                    self.apertures_table.selectRow(row)
                    self.last_aperture_selected = aper
        self.apertures_table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        self.apertures_table.cellPressed.connect(self.on_row_selected)
        self.plot_all()

    def on_canvas_move(self, event):
        """
        Called on 'mouse_move' event

        event.pos have canvas screen coordinates

        :param event: Event object dispatched by VisPy SceneCavas
        :return: None
        """

        pos = self.canvas.vispy_canvas.translate_coords(event.pos)
        event.xdata, event.ydata = pos[0], pos[1]

        self.x = event.xdata
        self.y = event.ydata

        # Prevent updates on pan
        # if len(event.buttons) > 0:
        #     return

        # if the RMB is clicked and mouse is moving over plot then 'panning_action' is True
        if event.button == 2:
            self.app.panning_action = True
            return
        else:
            self.app.panning_action = False

        try:
            x = float(event.xdata)
            y = float(event.ydata)
        except TypeError:
            return

        if self.active_tool is None:
            return

        ### Snap coordinates
        x, y = self.app.geo_editor.app.geo_editor.snap(x, y)

        self.snap_x = x
        self.snap_y = y

        # update the position label in the infobar since the APP mouse event handlers are disconnected
        self.app.ui.position_label.setText("&nbsp;&nbsp;&nbsp;&nbsp;<b>X</b>: %.4f&nbsp;&nbsp;   "
                                       "<b>Y</b>: %.4f" % (x, y))

        if self.pos is None:
            self.pos = (0, 0)
        dx = x - self.pos[0]
        dy = y - self.pos[1]

        # update the reference position label in the infobar since the APP mouse event handlers are disconnected
        self.app.ui.rel_position_label.setText("<b>Dx</b>: %.4f&nbsp;&nbsp;  <b>Dy</b>: "
                                           "%.4f&nbsp;&nbsp;&nbsp;&nbsp;" % (dx, dy))

        ### Utility geometry (animated)
        geo = self.active_tool.utility_geometry(data=(x, y))

        if isinstance(geo, DrawToolShape) and geo.geo is not None:

            # Remove any previous utility shape
            self.tool_shape.clear(update=True)
            self.draw_utility_geometry(geo=geo)

        ### Selection area on canvas section ###
        dx = pos[0] - self.pos[0]
        if event.is_dragging == 1 and event.button == 1:
            self.app.delete_selection_shape()
            if dx < 0:
                self.app.draw_moving_selection_shape((self.pos[0], self.pos[1]), (x,y),
                     color=self.app.defaults["global_alt_sel_line"],
                     face_color=self.app.defaults['global_alt_sel_fill'])
                self.app.selection_type = False
            else:
                self.app.draw_moving_selection_shape((self.pos[0], self.pos[1]), (x,y))
                self.app.selection_type = True
        else:
            self.app.selection_type = None

        # Update cursor
        self.app.app_cursor.set_data(np.asarray([(x, y)]), symbol='++', edge_color='black', size=20)

    def on_canvas_key_release(self, event):
        self.key = None

    def draw_utility_geometry(self, geo):
        if type(geo.geo) == list:
            for el in geo.geo:
                # Add the new utility shape
                self.tool_shape.add(
                    shape=el, color=(self.app.defaults["global_draw_color"] + '80'),
                    update=False, layer=0, tolerance=None)
        else:
            # Add the new utility shape
            self.tool_shape.add(
                shape=geo.geo, color=(self.app.defaults["global_draw_color"] + '80'),
                update=False, layer=0, tolerance=None)

        self.tool_shape.redraw()

    def plot_all(self):
        """
        Plots all shapes in the editor.

        :return: None
        :rtype: None
        """
        with self.app.proc_container.new("Plotting"):
            # self.app.log.debug("plot_all()")
            self.shapes.clear(update=True)

            for storage in self.storage_dict:
                for shape in self.storage_dict[storage]['solid_geometry']:
                    if shape.geo is None:
                        continue

                    if shape in self.selected:
                        self.plot_shape(geometry=shape.geo, color=self.app.defaults['global_sel_draw_color'],
                                        linewidth=2)
                        continue
                    self.plot_shape(geometry=shape.geo, color=self.app.defaults['global_draw_color'])

            for shape in self.utility:
                self.plot_shape(geometry=shape.geo, linewidth=1)
                continue

            self.shapes.redraw()

    def plot_shape(self, geometry=None, color='black', linewidth=1):
        """
        Plots a geometric object or list of objects without rendering. Plotted objects
        are returned as a list. This allows for efficient/animated rendering.

        :param geometry: Geometry to be plotted (Any Shapely.geom kind or list of such)
        :param color: Shape color
        :param linewidth: Width of lines in # of pixels.
        :return: List of plotted elements.
        """
        # plot_elements = []

        if geometry is None:
            geometry = self.active_tool.geometry

        try:
            self.shapes.add(shape=geometry.geo, color=color, face_color=color, layer=0)
        except AttributeError:
            if type(geometry) == Point:
                return
            self.shapes.add(shape=geometry, color=color, face_color=color+'AF', layer=0)

    def start_delayed_plot(self, check_period):
        # self.plot_thread = threading.Thread(target=lambda: self.check_plot_finished(check_period))
        # self.plot_thread.start()
        log.debug("FlatCAMGrbEditor --> Delayed Plot started.")
        self.plot_thread = QtCore.QTimer()
        self.plot_thread.setInterval(check_period)
        self.plot_thread.timeout.connect(self.check_plot_finished)
        self.plot_thread.start()

    def check_plot_finished(self):
        # print(self.grb_plot_promises)
        try:
            if not self.grb_plot_promises:
                self.plot_thread.stop()

                self.set_ui()
                # now that we have data, create the GUI interface and add it to the Tool Tab
                self.build_ui(first_run=True)
                self.plot_all()

                # HACK: enabling/disabling the cursor seams to somehow update the shapes making them more 'solid'
                # - perhaps is a bug in VisPy implementation
                self.app.app_cursor.enabled = False
                self.app.app_cursor.enabled = True

                log.debug("FlatCAMGrbEditor --> delayed_plot finished")
        except Exception:
            traceback.print_exc()

    def on_shape_complete(self):
        self.app.log.debug("on_shape_complete()")

        # Add shape
        self.add_gerber_shape(self.active_tool.geometry)

        # Remove any utility shapes
        self.delete_utility_geometry()
        self.tool_shape.clear(update=True)

        # Replot and reset tool.
        self.plot_all()
        # self.active_tool = type(self.active_tool)(self)

    def get_selected(self):
        """
        Returns list of shapes that are selected in the editor.

        :return: List of shapes.
        """
        # return [shape for shape in self.shape_buffer if shape["selected"]]
        return self.selected

    def delete_selected(self):
        temp_ref = [s for s in self.selected]
        for shape_sel in temp_ref:
            self.delete_shape(shape_sel)

        self.selected = []
        self.build_ui()
        self.app.inform.emit(_("[success] Done. Apertures deleted."))

    def delete_shape(self, shape):
        self.is_modified = True

        if shape in self.utility:
            self.utility.remove(shape)
            return

        for storage in self.storage_dict:
            # try:
            #     self.storage_dict[storage].remove(shape)
            # except:
            #     pass
            if shape in self.storage_dict[storage]['solid_geometry']:
                self.storage_dict[storage]['solid_geometry'].remove(shape)

        if shape in self.selected:
            self.selected.remove(shape)  # TODO: Check performance

    def delete_utility_geometry(self):
        # for_deletion = [shape for shape in self.shape_buffer if shape.utility]
        # for_deletion = [shape for shape in self.storage.get_objects() if shape.utility]
        for_deletion = [shape for shape in self.utility]
        for shape in for_deletion:
            self.delete_shape(shape)

        self.tool_shape.clear(update=True)
        self.tool_shape.redraw()

    def on_delete_btn(self):
        self.delete_selected()
        self.plot_all()

    def select_tool(self, toolname):
        """
        Selects a drawing tool. Impacts the object and GUI.

        :param toolname: Name of the tool.
        :return: None
        """
        self.tools_gerber[toolname]["button"].setChecked(True)
        self.on_tool_select(toolname)

    def set_selected(self, shape):

        # Remove and add to the end.
        if shape in self.selected:
            self.selected.remove(shape)

        self.selected.append(shape)

    def set_unselected(self, shape):
        if shape in self.selected:
            self.selected.remove(shape)

    def on_array_type_combo(self):
        if self.array_type_combo.currentIndex() == 0:
            self.array_circular_frame.hide()
            self.array_linear_frame.show()
        else:
            self.delete_utility_geometry()
            self.array_circular_frame.show()
            self.array_linear_frame.hide()
            self.app.inform.emit(_("Click on the circular array Center position"))

    def on_linear_angle_radio(self):
        val = self.pad_axis_radio.get_value()
        if val == 'A':
            self.linear_angle_spinner.show()
            self.linear_angle_label.show()
        else:
            self.linear_angle_spinner.hide()
            self.linear_angle_label.hide()

    def on_copy_button(self):
        self.select_tool('copy')
        return

    def on_move_button(self):
        self.select_tool('move')
        return

    def on_pad_add(self):
        self.select_tool('pad')

    def on_pad_add_array(self):
        self.select_tool('array')

    def on_track_add(self):
        self.select_tool('track')

    def on_region_add(self):
        self.select_tool('region')

    def on_poligonize(self):
        self.select_tool('poligonize')

    def on_buffer(self):
        buff_value = 0.01
        log.debug("FlatCAMGrbEditor.on_buffer()")

        try:
            buff_value = float(self.buffer_distance_entry.get_value())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                buff_value = float(self.buffer_distance_entry.get_value().replace(',', '.'))
                self.buffer_distance_entry.set_value(buff_value)
            except ValueError:
                self.app.inform.emit(_("[WARNING_NOTCL] Buffer distance value is missing or wrong format. "
                                     "Add it and retry."))
                return
        # the cb index start from 0 but the join styles for the buffer start from 1 therefore the adjustment
        # I populated the combobox such that the index coincide with the join styles value (whcih is really an INT)
        join_style = self.buffer_corner_cb.currentIndex() + 1

        def buffer_recursion(geom, selection):
            if type(geom) == list or type(geom) is MultiPolygon:
                geoms = list()
                for local_geom in geom:
                    geoms.append(buffer_recursion(local_geom, selection=selection))
                return geoms
            else:
                if geom in selection:
                    return DrawToolShape(geom.geo.buffer(buff_value, join_style=join_style))
                else:
                    return geom

        if not self.apertures_table.selectedItems():
            self.app.inform.emit(_(
                "[WARNING_NOTCL] No aperture to buffer. Select at least one aperture and try again."
            ))
            return

        for x in self.apertures_table.selectedItems():
            try:
                apid = self.apertures_table.item(x.row(), 1).text()

                temp_storage = deepcopy(buffer_recursion(self.storage_dict[apid]['solid_geometry'], self.selected))
                self.storage_dict[apid]['solid_geometry'] = []
                self.storage_dict[apid]['solid_geometry'] = temp_storage

            except Exception as e:
                log.debug("FlatCAMGrbEditor.buffer() --> %s" % str(e))
        self.plot_all()
        self.app.inform.emit(_("[success] Done. Buffer Tool completed."))

    def on_scale(self):
        scale_factor = 1.0
        log.debug("FlatCAMGrbEditor.on_scale()")

        try:
            scale_factor = float(self.scale_factor_entry.get_value())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                scale_factor = float(self.scale_factor_entry.get_value().replace(',', '.'))
                self.scale_factor_entry.set_value(scale_factor)
            except ValueError:
                self.app.inform.emit(_("[WARNING_NOTCL] Scale factor value is missing or wrong format. "
                                     "Add it and retry."))
                return

        def scale_recursion(geom, selection):
            if type(geom) == list or type(geom) is MultiPolygon:
                geoms = list()
                for local_geom in geom:
                    geoms.append(scale_recursion(local_geom, selection=selection))
                return geoms
            else:
                if geom in selection:
                    return DrawToolShape(affinity.scale(geom.geo, scale_factor, scale_factor, origin='center'))
                else:
                    return geom

        if not self.apertures_table.selectedItems():
            self.app.inform.emit(_(
                "[WARNING_NOTCL] No aperture to scale. Select at least one aperture and try again."
            ))
            return

        for x in self.apertures_table.selectedItems():
            try:
                apid = self.apertures_table.item(x.row(), 1).text()

                temp_storage = deepcopy(scale_recursion(self.storage_dict[apid]['solid_geometry'], self.selected))
                self.storage_dict[apid]['solid_geometry'] = []
                self.storage_dict[apid]['solid_geometry'] = temp_storage

            except Exception as e:
                log.debug("FlatCAMGrbEditor.on_scale() --> %s" % str(e))

        self.plot_all()
        self.app.inform.emit(_("[success] Done. Scale Tool completed."))

    def on_transform(self):
        if type(self.active_tool) == FCTransform:
            self.select_tool('select')
        else:
            self.select_tool('transform')

    def hide_tool(self, tool_name):
        # self.app.ui.notebook.setTabText(2, _("Tools"))

        if tool_name == 'all':
            self.apertures_frame.hide()
        if tool_name == 'select':
            self.apertures_frame.show()
        if tool_name == 'buffer' or tool_name == 'all':
            self.buffer_tool_frame.hide()
        if tool_name == 'scale' or tool_name == 'all':
            self.scale_tool_frame.hide()

        self.app.ui.notebook.setCurrentWidget(self.app.ui.selected_tab)


class TransformEditorTool(FlatCAMTool):
    """
    Inputs to specify how to paint the selected polygons.
    """

    toolName = _("Transform Tool")
    rotateName = _("Rotate")
    skewName = _("Skew/Shear")
    scaleName = _("Scale")
    flipName = _("Mirror (Flip)")
    offsetName = _("Offset")

    def __init__(self, app, draw_app):
        FlatCAMTool.__init__(self, app)

        self.app = app
        self.draw_app = draw_app

        self.transform_lay = QtWidgets.QVBoxLayout()
        self.layout.addLayout(self.transform_lay)
        ## Title
        title_label = QtWidgets.QLabel("%s" % (_('Editor %s') % self.toolName))
        title_label.setStyleSheet("""
                QLabel
                {
                    font-size: 16px;
                    font-weight: bold;
                }
                """)
        self.transform_lay.addWidget(title_label)

        self.empty_label = QtWidgets.QLabel("")
        self.empty_label.setFixedWidth(50)

        self.empty_label1 = QtWidgets.QLabel("")
        self.empty_label1.setFixedWidth(70)
        self.empty_label2 = QtWidgets.QLabel("")
        self.empty_label2.setFixedWidth(70)
        self.empty_label3 = QtWidgets.QLabel("")
        self.empty_label3.setFixedWidth(70)
        self.empty_label4 = QtWidgets.QLabel("")
        self.empty_label4.setFixedWidth(70)
        self.transform_lay.addWidget(self.empty_label)

        ## Rotate Title
        rotate_title_label = QtWidgets.QLabel("<font size=3><b>%s</b></font>" % self.rotateName)
        self.transform_lay.addWidget(rotate_title_label)

        ## Layout
        form_layout = QtWidgets.QFormLayout()
        self.transform_lay.addLayout(form_layout)
        form_child = QtWidgets.QHBoxLayout()

        self.rotate_label = QtWidgets.QLabel(_("Angle:"))
        self.rotate_label.setToolTip(
            _("Angle for Rotation action, in degrees.\n"
              "Float number between -360 and 359.\n"
              "Positive numbers for CW motion.\n"
              "Negative numbers for CCW motion.")
        )
        self.rotate_label.setFixedWidth(50)

        self.rotate_entry = FCEntry()
        # self.rotate_entry.setFixedWidth(60)
        self.rotate_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.rotate_button = FCButton()
        self.rotate_button.set_value(_("Rotate"))
        self.rotate_button.setToolTip(
            _("Rotate the selected shape(s).\n"
              "The point of reference is the middle of\n"
              "the bounding box for all selected shapes.")
        )
        self.rotate_button.setFixedWidth(60)

        form_child.addWidget(self.rotate_entry)
        form_child.addWidget(self.rotate_button)

        form_layout.addRow(self.rotate_label, form_child)

        self.transform_lay.addWidget(self.empty_label1)

        ## Skew Title
        skew_title_label = QtWidgets.QLabel("<font size=3><b>%s</b></font>" % self.skewName)
        self.transform_lay.addWidget(skew_title_label)

        ## Form Layout
        form1_layout = QtWidgets.QFormLayout()
        self.transform_lay.addLayout(form1_layout)
        form1_child_1 = QtWidgets.QHBoxLayout()
        form1_child_2 = QtWidgets.QHBoxLayout()

        self.skewx_label = QtWidgets.QLabel(_("Angle X:"))
        self.skewx_label.setToolTip(
            _("Angle for Skew action, in degrees.\n"
              "Float number between -360 and 359.")
        )
        self.skewx_label.setFixedWidth(50)
        self.skewx_entry = FCEntry()
        self.skewx_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        # self.skewx_entry.setFixedWidth(60)

        self.skewx_button = FCButton()
        self.skewx_button.set_value(_("Skew X"))
        self.skewx_button.setToolTip(
            _("Skew/shear the selected shape(s).\n"
              "The point of reference is the middle of\n"
              "the bounding box for all selected shapes."))
        self.skewx_button.setFixedWidth(60)

        self.skewy_label = QtWidgets.QLabel(_("Angle Y:"))
        self.skewy_label.setToolTip(
            _("Angle for Skew action, in degrees.\n"
              "Float number between -360 and 359.")
        )
        self.skewy_label.setFixedWidth(50)
        self.skewy_entry = FCEntry()
        self.skewy_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        # self.skewy_entry.setFixedWidth(60)

        self.skewy_button = FCButton()
        self.skewy_button.set_value(_("Skew Y"))
        self.skewy_button.setToolTip(
            _("Skew/shear the selected shape(s).\n"
              "The point of reference is the middle of\n"
              "the bounding box for all selected shapes."))
        self.skewy_button.setFixedWidth(60)

        form1_child_1.addWidget(self.skewx_entry)
        form1_child_1.addWidget(self.skewx_button)

        form1_child_2.addWidget(self.skewy_entry)
        form1_child_2.addWidget(self.skewy_button)

        form1_layout.addRow(self.skewx_label, form1_child_1)
        form1_layout.addRow(self.skewy_label, form1_child_2)

        self.transform_lay.addWidget(self.empty_label2)

        ## Scale Title
        scale_title_label = QtWidgets.QLabel("<font size=3><b>%s</b></font>" % self.scaleName)
        self.transform_lay.addWidget(scale_title_label)

        ## Form Layout
        form2_layout = QtWidgets.QFormLayout()
        self.transform_lay.addLayout(form2_layout)
        form2_child_1 = QtWidgets.QHBoxLayout()
        form2_child_2 = QtWidgets.QHBoxLayout()

        self.scalex_label = QtWidgets.QLabel(_("Factor X:"))
        self.scalex_label.setToolTip(
            _("Factor for Scale action over X axis.")
        )
        self.scalex_label.setFixedWidth(50)
        self.scalex_entry = FCEntry()
        self.scalex_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        # self.scalex_entry.setFixedWidth(60)

        self.scalex_button = FCButton()
        self.scalex_button.set_value(_("Scale X"))
        self.scalex_button.setToolTip(
            _("Scale the selected shape(s).\n"
              "The point of reference depends on \n"
              "the Scale reference checkbox state."))
        self.scalex_button.setFixedWidth(60)

        self.scaley_label = QtWidgets.QLabel(_("Factor Y:"))
        self.scaley_label.setToolTip(
            _("Factor for Scale action over Y axis.")
        )
        self.scaley_label.setFixedWidth(50)
        self.scaley_entry = FCEntry()
        self.scaley_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        # self.scaley_entry.setFixedWidth(60)

        self.scaley_button = FCButton()
        self.scaley_button.set_value(_("Scale Y"))
        self.scaley_button.setToolTip(
            _("Scale the selected shape(s).\n"
              "The point of reference depends on \n"
              "the Scale reference checkbox state."))
        self.scaley_button.setFixedWidth(60)

        self.scale_link_cb = FCCheckBox()
        self.scale_link_cb.set_value(True)
        self.scale_link_cb.setText(_("Link"))
        self.scale_link_cb.setToolTip(
            _("Scale the selected shape(s)\n"
              "using the Scale Factor X for both axis."))
        self.scale_link_cb.setFixedWidth(50)

        self.scale_zero_ref_cb = FCCheckBox()
        self.scale_zero_ref_cb.set_value(True)
        self.scale_zero_ref_cb.setText(_("Scale Reference"))
        self.scale_zero_ref_cb.setToolTip(
            _("Scale the selected shape(s)\n"
              "using the origin reference when checked,\n"
              "and the center of the biggest bounding box\n"
              "of the selected shapes when unchecked."))

        form2_child_1.addWidget(self.scalex_entry)
        form2_child_1.addWidget(self.scalex_button)

        form2_child_2.addWidget(self.scaley_entry)
        form2_child_2.addWidget(self.scaley_button)

        form2_layout.addRow(self.scalex_label, form2_child_1)
        form2_layout.addRow(self.scaley_label, form2_child_2)
        form2_layout.addRow(self.scale_link_cb, self.scale_zero_ref_cb)
        self.ois_scale = OptionalInputSection(self.scale_link_cb, [self.scaley_entry, self.scaley_button],
                                              logic=False)

        self.transform_lay.addWidget(self.empty_label3)

        ## Offset Title
        offset_title_label = QtWidgets.QLabel("<font size=3><b>%s</b></font>" % self.offsetName)
        self.transform_lay.addWidget(offset_title_label)

        ## Form Layout
        form3_layout = QtWidgets.QFormLayout()
        self.transform_lay.addLayout(form3_layout)
        form3_child_1 = QtWidgets.QHBoxLayout()
        form3_child_2 = QtWidgets.QHBoxLayout()

        self.offx_label = QtWidgets.QLabel(_("Value X:"))
        self.offx_label.setToolTip(
            _("Value for Offset action on X axis.")
        )
        self.offx_label.setFixedWidth(50)
        self.offx_entry = FCEntry()
        self.offx_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        # self.offx_entry.setFixedWidth(60)

        self.offx_button = FCButton()
        self.offx_button.set_value(_("Offset X"))
        self.offx_button.setToolTip(
            _("Offset the selected shape(s).\n"
              "The point of reference is the middle of\n"
              "the bounding box for all selected shapes.\n")
        )
        self.offx_button.setFixedWidth(60)

        self.offy_label = QtWidgets.QLabel(_("Value Y:"))
        self.offy_label.setToolTip(
            _("Value for Offset action on Y axis.")
        )
        self.offy_label.setFixedWidth(50)
        self.offy_entry = FCEntry()
        self.offy_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        # self.offy_entry.setFixedWidth(60)

        self.offy_button = FCButton()
        self.offy_button.set_value(_("Offset Y"))
        self.offy_button.setToolTip(
            _("Offset the selected shape(s).\n"
              "The point of reference is the middle of\n"
              "the bounding box for all selected shapes.\n")
        )
        self.offy_button.setFixedWidth(60)

        form3_child_1.addWidget(self.offx_entry)
        form3_child_1.addWidget(self.offx_button)

        form3_child_2.addWidget(self.offy_entry)
        form3_child_2.addWidget(self.offy_button)

        form3_layout.addRow(self.offx_label, form3_child_1)
        form3_layout.addRow(self.offy_label, form3_child_2)

        self.transform_lay.addWidget(self.empty_label4)

        ## Flip Title
        flip_title_label = QtWidgets.QLabel("<font size=3><b>%s</b></font>" % self.flipName)
        self.transform_lay.addWidget(flip_title_label)

        ## Form Layout
        form4_layout = QtWidgets.QFormLayout()
        form4_child_hlay = QtWidgets.QHBoxLayout()
        self.transform_lay.addLayout(form4_child_hlay)
        self.transform_lay.addLayout(form4_layout)
        form4_child_1 = QtWidgets.QHBoxLayout()

        self.flipx_button = FCButton()
        self.flipx_button.set_value(_("Flip on X"))
        self.flipx_button.setToolTip(
            _("Flip the selected shape(s) over the X axis.\n"
              "Does not create a new shape.")
        )
        self.flipx_button.setFixedWidth(60)

        self.flipy_button = FCButton()
        self.flipy_button.set_value(_("Flip on Y"))
        self.flipy_button.setToolTip(
            _("Flip the selected shape(s) over the X axis.\n"
              "Does not create a new shape.")
        )
        self.flipy_button.setFixedWidth(60)

        self.flip_ref_cb = FCCheckBox()
        self.flip_ref_cb.set_value(True)
        self.flip_ref_cb.setText(_("Ref Pt"))
        self.flip_ref_cb.setToolTip(
            _("Flip the selected shape(s)\n"
              "around the point in Point Entry Field.\n"
              "\n"
              "The point coordinates can be captured by\n"
              "left click on canvas together with pressing\n"
              "SHIFT key. \n"
              "Then click Add button to insert coordinates.\n"
              "Or enter the coords in format (x, y) in the\n"
              "Point Entry field and click Flip on X(Y)")
        )
        self.flip_ref_cb.setFixedWidth(50)

        self.flip_ref_label = QtWidgets.QLabel(_("Point:"))
        self.flip_ref_label.setToolTip(
            _("Coordinates in format (x, y) used as reference for mirroring.\n"
              "The 'x' in (x, y) will be used when using Flip on X and\n"
              "the 'y' in (x, y) will be used when using Flip on Y.")
        )
        self.flip_ref_label.setFixedWidth(50)
        self.flip_ref_entry = EvalEntry2("(0, 0)")
        self.flip_ref_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        # self.flip_ref_entry.setFixedWidth(60)

        self.flip_ref_button = FCButton()
        self.flip_ref_button.set_value(_("Add"))
        self.flip_ref_button.setToolTip(
            _("The point coordinates can be captured by\n"
              "left click on canvas together with pressing\n"
              "SHIFT key. Then click Add button to insert.")
        )
        self.flip_ref_button.setFixedWidth(60)

        form4_child_hlay.addStretch()
        form4_child_hlay.addWidget(self.flipx_button)
        form4_child_hlay.addWidget(self.flipy_button)

        form4_child_1.addWidget(self.flip_ref_entry)
        form4_child_1.addWidget(self.flip_ref_button)

        form4_layout.addRow(self.flip_ref_cb)
        form4_layout.addRow(self.flip_ref_label, form4_child_1)
        self.ois_flip = OptionalInputSection(self.flip_ref_cb,
                                             [self.flip_ref_entry, self.flip_ref_button], logic=True)

        self.transform_lay.addStretch()

        ## Signals
        self.rotate_button.clicked.connect(self.on_rotate)
        self.skewx_button.clicked.connect(self.on_skewx)
        self.skewy_button.clicked.connect(self.on_skewy)
        self.scalex_button.clicked.connect(self.on_scalex)
        self.scaley_button.clicked.connect(self.on_scaley)
        self.offx_button.clicked.connect(self.on_offx)
        self.offy_button.clicked.connect(self.on_offy)
        self.flipx_button.clicked.connect(self.on_flipx)
        self.flipy_button.clicked.connect(self.on_flipy)
        self.flip_ref_button.clicked.connect(self.on_flip_add_coords)

        self.rotate_entry.returnPressed.connect(self.on_rotate)
        self.skewx_entry.returnPressed.connect(self.on_skewx)
        self.skewy_entry.returnPressed.connect(self.on_skewy)
        self.scalex_entry.returnPressed.connect(self.on_scalex)
        self.scaley_entry.returnPressed.connect(self.on_scaley)
        self.offx_entry.returnPressed.connect(self.on_offx)
        self.offy_entry.returnPressed.connect(self.on_offy)

        self.set_tool_ui()

    def run(self, toggle=True):
        self.app.report_usage("Geo Editor Transform Tool()")

        # if the splitter is hidden, display it, else hide it but only if the current widget is the same
        if self.app.ui.splitter.sizes()[0] == 0:
            self.app.ui.splitter.setSizes([1, 1])

        if toggle:
            try:
                if self.app.ui.tool_scroll_area.widget().objectName() == self.toolName:
                    self.app.ui.notebook.setCurrentWidget(self.app.ui.selected_tab)
                else:
                    self.app.ui.notebook.setCurrentWidget(self.app.ui.tool_tab)
            except AttributeError:
                pass

        FlatCAMTool.run(self)
        self.set_tool_ui()

        self.app.ui.notebook.setTabText(2, _("Transform Tool"))

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, shortcut='ALT+T', **kwargs)

    def set_tool_ui(self):
        ## Initialize form
        if self.app.defaults["tools_transform_rotate"]:
            self.rotate_entry.set_value(self.app.defaults["tools_transform_rotate"])
        else:
            self.rotate_entry.set_value(0.0)

        if self.app.defaults["tools_transform_skew_x"]:
            self.skewx_entry.set_value(self.app.defaults["tools_transform_skew_x"])
        else:
            self.skewx_entry.set_value(0.0)

        if self.app.defaults["tools_transform_skew_y"]:
            self.skewy_entry.set_value(self.app.defaults["tools_transform_skew_y"])
        else:
            self.skewy_entry.set_value(0.0)

        if self.app.defaults["tools_transform_scale_x"]:
            self.scalex_entry.set_value(self.app.defaults["tools_transform_scale_x"])
        else:
            self.scalex_entry.set_value(1.0)

        if self.app.defaults["tools_transform_scale_y"]:
            self.scaley_entry.set_value(self.app.defaults["tools_transform_scale_y"])
        else:
            self.scaley_entry.set_value(1.0)

        if self.app.defaults["tools_transform_scale_link"]:
            self.scale_link_cb.set_value(self.app.defaults["tools_transform_scale_link"])
        else:
            self.scale_link_cb.set_value(True)

        if self.app.defaults["tools_transform_scale_reference"]:
            self.scale_zero_ref_cb.set_value(self.app.defaults["tools_transform_scale_reference"])
        else:
            self.scale_zero_ref_cb.set_value(True)

        if self.app.defaults["tools_transform_offset_x"]:
            self.offx_entry.set_value(self.app.defaults["tools_transform_offset_x"])
        else:
            self.offx_entry.set_value(0.0)

        if self.app.defaults["tools_transform_offset_y"]:
            self.offy_entry.set_value(self.app.defaults["tools_transform_offset_y"])
        else:
            self.offy_entry.set_value(0.0)

        if self.app.defaults["tools_transform_mirror_reference"]:
            self.flip_ref_cb.set_value(self.app.defaults["tools_transform_mirror_reference"])
        else:
            self.flip_ref_cb.set_value(False)

        if self.app.defaults["tools_transform_mirror_point"]:
            self.flip_ref_entry.set_value(self.app.defaults["tools_transform_mirror_point"])
        else:
            self.flip_ref_entry.set_value((0, 0))

    def template(self):
        if not self.fcdraw.selected:
            self.app.inform.emit(_("[WARNING_NOTCL] Transformation cancelled. No shape selected."))
            return

        self.draw_app.select_tool("select")
        self.app.ui.notebook.setTabText(2, "Tools")
        self.app.ui.notebook.setCurrentWidget(self.app.ui.project_tab)

        self.app.ui.splitter.setSizes([0, 1])

    def on_rotate(self, sig=None, val=None):
        if val:
            value = val
        else:
            try:
                value = float(self.rotate_entry.get_value())
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    value = float(self.rotate_entry.get_value().replace(',', '.'))
                except ValueError:
                    self.app.inform.emit(_("[ERROR_NOTCL] Wrong value format entered for Rotate, "
                                           "use a number."))
                    return
        self.app.worker_task.emit({'fcn': self.on_rotate_action,
                                   'params': [value]})
        # self.on_rotate_action(value)
        return

    def on_flipx(self):
        # self.on_flip("Y")
        axis = 'Y'
        self.app.worker_task.emit({'fcn': self.on_flip,
                                   'params': [axis]})
        return

    def on_flipy(self):
        # self.on_flip("X")
        axis = 'X'
        self.app.worker_task.emit({'fcn': self.on_flip,
                                   'params': [axis]})
        return

    def on_flip_add_coords(self):
        val = self.app.clipboard.text()
        self.flip_ref_entry.set_value(val)

    def on_skewx(self, sig=None, val=None):
        if val:
            value = val
        else:
            try:
                value = float(self.skewx_entry.get_value())
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    value = float(self.skewx_entry.get_value().replace(',', '.'))
                except ValueError:
                    self.app.inform.emit(_("[ERROR_NOTCL] Wrong value format entered for Skew X, "
                                           "use a number."))
                    return

        # self.on_skew("X", value)
        axis = 'X'
        self.app.worker_task.emit({'fcn': self.on_skew,
                                   'params': [axis, value]})
        return

    def on_skewy(self, sig=None, val=None):
        if val:
            value = val
        else:
            try:
                value = float(self.skewy_entry.get_value())
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    value = float(self.skewy_entry.get_value().replace(',', '.'))
                except ValueError:
                    self.app.inform.emit(_("[ERROR_NOTCL] Wrong value format entered for Skew Y, "
                                           "use a number."))
                    return

        # self.on_skew("Y", value)
        axis = 'Y'
        self.app.worker_task.emit({'fcn': self.on_skew,
                                   'params': [axis, value]})
        return

    def on_scalex(self, sig=None, val=None):
        if val:
            xvalue = val
        else:
            try:
                xvalue = float(self.scalex_entry.get_value())
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    xvalue = float(self.scalex_entry.get_value().replace(',', '.'))
                except ValueError:
                    self.app.inform.emit(_("[ERROR_NOTCL] Wrong value format entered for Scale X, "
                                           "use a number."))
                    return

        # scaling to zero has no sense so we remove it, because scaling with 1 does nothing
        if xvalue == 0:
            xvalue = 1
        if self.scale_link_cb.get_value():
            yvalue = xvalue
        else:
            yvalue = 1

        axis = 'X'
        point = (0, 0)
        if self.scale_zero_ref_cb.get_value():
            self.app.worker_task.emit({'fcn': self.on_scale,
                                       'params': [axis, xvalue, yvalue, point]})
            # self.on_scale("X", xvalue, yvalue, point=(0,0))
        else:
            # self.on_scale("X", xvalue, yvalue)
            self.app.worker_task.emit({'fcn': self.on_scale,
                                       'params': [axis, xvalue, yvalue]})

        return

    def on_scaley(self, sig=None, val=None):
        xvalue = 1
        if val:
            yvalue = val
        else:
            try:
                yvalue = float(self.scaley_entry.get_value())
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    yvalue = float(self.scaley_entry.get_value().replace(',', '.'))
                except ValueError:
                    self.app.inform.emit(_("[ERROR_NOTCL] Wrong value format entered for Scale Y, "
                                           "use a number."))
                    return

        # scaling to zero has no sense so we remove it, because scaling with 1 does nothing
        if yvalue == 0:
            yvalue = 1

        axis = 'Y'
        point = (0, 0)
        if self.scale_zero_ref_cb.get_value():
            self.app.worker_task.emit({'fcn': self.on_scale,
                                       'params': [axis, xvalue, yvalue, point]})
            # self.on_scale("Y", xvalue, yvalue, point=(0,0))
        else:
            # self.on_scale("Y", xvalue, yvalue)
            self.app.worker_task.emit({'fcn': self.on_scale,
                                       'params': [axis, xvalue, yvalue]})

        return

    def on_offx(self, sig=None, val=None):
        if val:
            value = val
        else:
            try:
                value = float(self.offx_entry.get_value())
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    value = float(self.offx_entry.get_value().replace(',', '.'))
                except ValueError:
                    self.app.inform.emit(_("[ERROR_NOTCL] Wrong value format entered for Offset X, "
                                           "use a number."))
                    return

        # self.on_offset("X", value)
        axis = 'X'
        self.app.worker_task.emit({'fcn': self.on_offset,
                                   'params': [axis, value]})
        return

    def on_offy(self, sig=None, val=None):
        if val:
            value = val
        else:
            try:
                value = float(self.offy_entry.get_value())
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    value = float(self.offy_entry.get_value().replace(',', '.'))
                except ValueError:
                    self.app.inform.emit(_("[ERROR_NOTCL] Wrong value format entered for Offset Y, "
                                           "use a number."))
                    return

        # self.on_offset("Y", value)
        axis = 'Y'
        self.app.worker_task.emit({'fcn': self.on_offset,
                                   'params': [axis, value]})
        return

    def on_rotate_action(self, num):
        shape_list = self.draw_app.selected
        xminlist = []
        yminlist = []
        xmaxlist = []
        ymaxlist = []

        if not shape_list:
            self.app.inform.emit(_("[WARNING_NOTCL] No shape selected. Please Select a shape to rotate!"))
            return
        else:
            with self.app.proc_container.new(_("Appying Rotate")):
                try:
                    # first get a bounding box to fit all
                    for sha in shape_list:
                        xmin, ymin, xmax, ymax = sha.bounds()
                        xminlist.append(xmin)
                        yminlist.append(ymin)
                        xmaxlist.append(xmax)
                        ymaxlist.append(ymax)

                    # get the minimum x,y and maximum x,y for all objects selected
                    xminimal = min(xminlist)
                    yminimal = min(yminlist)
                    xmaximal = max(xmaxlist)
                    ymaximal = max(ymaxlist)

                    self.app.progress.emit(20)

                    for sel_sha in shape_list:
                        px = 0.5 * (xminimal + xmaximal)
                        py = 0.5 * (yminimal + ymaximal)

                        sel_sha.rotate(-num, point=(px, py))
                        self.draw_app.plot_all()
                        # self.draw_app.add_shape(DrawToolShape(sel_sha.geo))

                    # self.draw_app.transform_complete.emit()

                    self.app.inform.emit(_("[success] Done. Rotate completed."))

                    self.app.progress.emit(100)

                except Exception as e:
                    self.app.inform.emit(_("[ERROR_NOTCL] Due of %s, rotation movement was not executed.") % str(e))
                    return

    def on_flip(self, axis):
        shape_list = self.draw_app.selected
        xminlist = []
        yminlist = []
        xmaxlist = []
        ymaxlist = []

        if not shape_list:
            self.app.inform.emit(_("[WARNING_NOTCL] No shape selected. Please Select a shape to flip!"))
            return
        else:
            with self.app.proc_container.new(_("Applying Flip")):
                try:
                    # get mirroring coords from the point entry
                    if self.flip_ref_cb.isChecked():
                        px, py = eval('{}'.format(self.flip_ref_entry.text()))
                    # get mirroing coords from the center of an all-enclosing bounding box
                    else:
                        # first get a bounding box to fit all
                        for sha in shape_list:
                            xmin, ymin, xmax, ymax = sha.bounds()
                            xminlist.append(xmin)
                            yminlist.append(ymin)
                            xmaxlist.append(xmax)
                            ymaxlist.append(ymax)

                        # get the minimum x,y and maximum x,y for all objects selected
                        xminimal = min(xminlist)
                        yminimal = min(yminlist)
                        xmaximal = max(xmaxlist)
                        ymaximal = max(ymaxlist)

                        px = 0.5 * (xminimal + xmaximal)
                        py = 0.5 * (yminimal + ymaximal)

                    self.app.progress.emit(20)

                    # execute mirroring
                    for sha in shape_list:
                        if axis is 'X':
                            sha.mirror('X', (px, py))
                            self.app.inform.emit(_('[success] Flip on the Y axis done ...'))
                        elif axis is 'Y':
                            sha.mirror('Y', (px, py))
                            self.app.inform.emit(_('[success] Flip on the X axis done ...'))
                        self.draw_app.plot_all()

                    #     self.draw_app.add_shape(DrawToolShape(sha.geo))
                    #
                    # self.draw_app.transform_complete.emit()

                    self.app.progress.emit(100)

                except Exception as e:
                    self.app.inform.emit(_("[ERROR_NOTCL] Due of %s, Flip action was not executed.") % str(e))
                    return

    def on_skew(self, axis, num):
        shape_list = self.draw_app.selected
        xminlist = []
        yminlist = []

        if not shape_list:
            self.app.inform.emit(_("[WARNING_NOTCL] No shape selected. Please Select a shape to shear/skew!"))
            return
        else:
            with self.app.proc_container.new(_("Applying Skew")):
                try:
                    # first get a bounding box to fit all
                    for sha in shape_list:
                        xmin, ymin, xmax, ymax = sha.bounds()
                        xminlist.append(xmin)
                        yminlist.append(ymin)

                    # get the minimum x,y and maximum x,y for all objects selected
                    xminimal = min(xminlist)
                    yminimal = min(yminlist)

                    self.app.progress.emit(20)

                    for sha in shape_list:
                        if axis is 'X':
                            sha.skew(num, 0, point=(xminimal, yminimal))
                        elif axis is 'Y':
                            sha.skew(0, num, point=(xminimal, yminimal))
                        self.draw_app.plot_all()

                    #     self.draw_app.add_shape(DrawToolShape(sha.geo))
                    #
                    # self.draw_app.transform_complete.emit()

                    self.app.inform.emit(_('[success] Skew on the %s axis done ...') % str(axis))
                    self.app.progress.emit(100)

                except Exception as e:
                    self.app.inform.emit(_("[ERROR_NOTCL] Due of %s, Skew action was not executed.") % str(e))
                    return

    def on_scale(self, axis, xfactor, yfactor, point=None):
        shape_list = self.draw_app.selected
        xminlist = []
        yminlist = []
        xmaxlist = []
        ymaxlist = []

        if not shape_list:
            self.app.inform.emit(_("[WARNING_NOTCL] No shape selected. Please Select a shape to scale!"))
            return
        else:
            with self.app.proc_container.new(_("Applying Scale")):
                try:
                    # first get a bounding box to fit all
                    for sha in shape_list:
                        xmin, ymin, xmax, ymax = sha.bounds()
                        xminlist.append(xmin)
                        yminlist.append(ymin)
                        xmaxlist.append(xmax)
                        ymaxlist.append(ymax)

                    # get the minimum x,y and maximum x,y for all objects selected
                    xminimal = min(xminlist)
                    yminimal = min(yminlist)
                    xmaximal = max(xmaxlist)
                    ymaximal = max(ymaxlist)

                    self.app.progress.emit(20)

                    if point is None:
                        px = 0.5 * (xminimal + xmaximal)
                        py = 0.5 * (yminimal + ymaximal)
                    else:
                        px = 0
                        py = 0

                    for sha in shape_list:
                        sha.scale(xfactor, yfactor, point=(px, py))
                        self.draw_app.plot_all()

                    #     self.draw_app.add_shape(DrawToolShape(sha.geo))
                    #
                    # self.draw_app.transform_complete.emit()

                    self.app.inform.emit(_('[success] Scale on the %s axis done ...') % str(axis))
                    self.app.progress.emit(100)
                except Exception as e:
                    self.app.inform.emit(_("[ERROR_NOTCL] Due of %s, Scale action was not executed.") % str(e))
                    return

    def on_offset(self, axis, num):
        shape_list = self.draw_app.selected
        xminlist = []
        yminlist = []

        if not shape_list:
            self.app.inform.emit(_("[WARNING_NOTCL] No shape selected. Please Select a shape to offset!"))
            return
        else:
            with self.app.proc_container.new(_("Applying Offset")):
                try:
                    # first get a bounding box to fit all
                    for sha in shape_list:
                        xmin, ymin, xmax, ymax = sha.bounds()
                        xminlist.append(xmin)
                        yminlist.append(ymin)

                    # get the minimum x,y and maximum x,y for all objects selected
                    xminimal = min(xminlist)
                    yminimal = min(yminlist)
                    self.app.progress.emit(20)

                    for sha in shape_list:
                        if axis is 'X':
                            sha.offset((num, 0))
                        elif axis is 'Y':
                            sha.offset((0, num))
                        self.draw_app.plot_all()

                    #     self.draw_app.add_shape(DrawToolShape(sha.geo))
                    #
                    # self.draw_app.transform_complete.emit()

                    self.app.inform.emit(_('[success] Offset on the %s axis done ...') % str(axis))
                    self.app.progress.emit(100)

                except Exception as e:
                    self.app.inform.emit(_("[ERROR_NOTCL] Due of %s, Offset action was not executed.") % str(e))
                    return

    def on_rotate_key(self):
        val_box = FCInputDialog(title=_("Rotate ..."),
                                text=_('Enter an Angle Value (degrees):'),
                                min=-359.9999, max=360.0000, decimals=4,
                                init_val=float(self.app.defaults['tools_transform_rotate']))
        val_box.setWindowIcon(QtGui.QIcon('share/rotate.png'))

        val, ok = val_box.get_value()
        if ok:
            self.on_rotate(val=val)
            self.app.inform.emit(
                _("[success] Geometry shape rotate done...")
            )
            return
        else:
            self.app.inform.emit(
                _("[WARNING_NOTCL] Geometry shape rotate cancelled...")
            )

    def on_offx_key(self):
        units = self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().lower()

        val_box = FCInputDialog(title=_("Offset on X axis ..."),
                                text=(_('Enter a distance Value (%s):') % str(units)),
                                min=-9999.9999, max=10000.0000, decimals=4,
                                init_val=float(self.app.defaults['tools_transform_offset_x']))
        val_box.setWindowIcon(QtGui.QIcon('share/offsetx32.png'))

        val, ok = val_box.get_value()
        if ok:
            self.on_offx(val=val)
            self.app.inform.emit(
                _("[success] Geometry shape offset on X axis done..."))
            return
        else:
            self.app.inform.emit(
                _("[WARNING_NOTCL] Geometry shape offset X cancelled..."))

    def on_offy_key(self):
        units = self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().lower()

        val_box = FCInputDialog(title=_("Offset on Y axis ..."),
                                text=(_('Enter a distance Value (%s):') % str(units)),
                                min=-9999.9999, max=10000.0000, decimals=4,
                                init_val=float(self.app.defaults['tools_transform_offset_y']))
        val_box.setWindowIcon(QtGui.QIcon('share/offsety32.png'))

        val, ok = val_box.get_value()
        if ok:
            self.on_offx(val=val)
            self.app.inform.emit(
                _("[success] Geometry shape offset on Y axis done..."))
            return
        else:
            self.app.inform.emit(
                _("[WARNING_NOTCL] Geometry shape offset Y cancelled..."))

    def on_skewx_key(self):
        val_box = FCInputDialog(title=_("Skew on X axis ..."),
                                text=_('Enter an Angle Value (degrees):'),
                                min=-359.9999, max=360.0000, decimals=4,
                                init_val=float(self.app.defaults['tools_transform_skew_x']))
        val_box.setWindowIcon(QtGui.QIcon('share/skewX.png'))

        val, ok = val_box.get_value()
        if ok:
            self.on_skewx(val=val)
            self.app.inform.emit(
                _("[success] Geometry shape skew on X axis done..."))
            return
        else:
            self.app.inform.emit(
                _("[WARNING_NOTCL] Geometry shape skew X cancelled..."))

    def on_skewy_key(self):
        val_box = FCInputDialog(title=_("Skew on Y axis ..."),
                                text=_('Enter an Angle Value (degrees):'),
                                min=-359.9999, max=360.0000, decimals=4,
                                init_val=float(self.app.defaults['tools_transform_skew_y']))
        val_box.setWindowIcon(QtGui.QIcon('share/skewY.png'))

        val, ok = val_box.get_value()
        if ok:
            self.on_skewx(val=val)
            self.app.inform.emit(
                _("[success] Geometry shape skew on Y axis done..."))
            return
        else:
            self.app.inform.emit(
                _("[WARNING_NOTCL] Geometry shape skew Y cancelled..."))
