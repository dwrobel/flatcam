# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 8/17/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import Qt, QSettings

from shapely.geometry import LineString, LinearRing, MultiLineString, Point, Polygon, MultiPolygon, box
from shapely.ops import cascaded_union
import shapely.affinity as affinity

from vispy.geometry import Rect

from copy import copy, deepcopy
import logging

from camlib import distance, arc, three_point_circle
from appGUI.GUIElements import FCEntry, FCComboBox, FCTable, FCDoubleSpinner, FCSpinner, RadioSet, \
    EvalEntry2, FCInputDialog, FCButton, OptionalInputSection, FCCheckBox, NumericalEvalTupleEntry
from appTool import AppTool

import numpy as np
from numpy.linalg import norm as numpy_norm
import math

# from vispy.io import read_png
# import pngcanvas
import traceback
import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class DrawToolShape(object):
    """
    Encapsulates "shapes" under a common class.
    """

    tolerance = None

    @staticmethod
    def get_pts(o):
        """
        Returns a list of all points in the object, where
        the object can be a Polygon, Not a polygon, or a list
        of such. Search is done recursively.

        :param: geometric object
        :return: List of points
        :rtype: list
        """
        pts = []

        # ## Iterable: descend into each item.
        try:
            for sub_o in o:
                pts += DrawToolShape.get_pts(sub_o)

        # Non-iterable
        except TypeError:
            if o is not None:
                # DrawToolShape: descend into .geo.
                if isinstance(o, DrawToolShape):
                    pts += DrawToolShape.get_pts(o.geo)

                # ## Descend into .exerior and .interiors
                elif type(o) == Polygon:
                    pts += DrawToolShape.get_pts(o.exterior)
                    for i in o.interiors:
                        pts += DrawToolShape.get_pts(i)
                elif type(o) == MultiLineString:
                    for line in o:
                        pts += DrawToolShape.get_pts(line)
                # ## Has .coords: list them.
                else:
                    if DrawToolShape.tolerance is not None:
                        pts += list(o.simplify(DrawToolShape.tolerance).coords)
                    else:
                        pts += list(o.coords)
            else:
                return
        return pts

    def __init__(self, geo=None):

        # Shapely type or list of such
        self.geo = geo
        self.utility = False


class DrawToolUtilityShape(DrawToolShape):
    """
    Utility shapes are temporary geometry in the editor
    to assist in the creation of shapes. For example it
    will show the outline of a rectangle from the first
    point to the current mouse pointer before the second
    point is clicked and the final geometry is created.
    """

    def __init__(self, geo=None):
        super(DrawToolUtilityShape, self).__init__(geo=geo)
        self.utility = True


class DrawTool(object):
    """
    Abstract Class representing a tool in the drawing
    program. Can generate geometry, including temporary
    utility geometry that is updated on user clicks
    and mouse motion.
    """

    def __init__(self, draw_app):
        self.draw_app = draw_app
        self.complete = False
        self.points = []
        self.geometry = None  # DrawToolShape or None

    def click(self, point):
        """
        :param point: [x, y] Coordinate pair.
        """
        return ""

    def click_release(self, point):
        """
        :param point: [x, y] Coordinate pair.
        """
        return ""

    def on_key(self, key):
        # Jump to coords
        if key == QtCore.Qt.Key_J or key == 'J':
            self.draw_app.app.on_jump_to()

    def utility_geometry(self, data=None):
        return None

    @staticmethod
    def bounds(obj):
        def bounds_rec(o):
            if type(o) is list:
                minx = np.Inf
                miny = np.Inf
                maxx = -np.Inf
                maxy = -np.Inf

                for k in o:
                    try:
                        minx_, miny_, maxx_, maxy_ = bounds_rec(k)
                    except Exception as e:
                        log.debug("camlib.Gerber.bounds() --> %s" % str(e))
                        return

                    minx = min(minx, minx_)
                    miny = min(miny, miny_)
                    maxx = max(maxx, maxx_)
                    maxy = max(maxy, maxy_)
                return minx, miny, maxx, maxy
            else:
                # it's a Shapely object, return it's bounds
                if 'solid' in o.geo:
                    return o.geo['solid'].bounds

        return bounds_rec(obj)


class FCShapeTool(DrawTool):
    """
    Abstract class for tools that create a shape.
    """

    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.name = None

    def make(self):
        pass


class FCPad(FCShapeTool):
    """
    Resulting type: Polygon
    """

    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.name = 'pad'
        self.draw_app = draw_app

        try:
            QtGui.QGuiApplication.restoreOverrideCursor()
        except Exception:
            pass
        self.cursor = QtGui.QCursor(QtGui.QPixmap(self.draw_app.app.resource_location + '/aero_circle.png'))
        QtGui.QGuiApplication.setOverrideCursor(self.cursor)

        try:
            self.radius = float(self.draw_app.storage_dict[self.draw_app.last_aperture_selected]['size']) / 2
        except KeyError:
            self.draw_app.app.inform.emit('[WARNING_NOTCL] %s' %
                                          _("To add an Pad first select a aperture in Aperture Table"))
            self.draw_app.in_action = False
            self.complete = True
            return

        if self.radius == 0:
            self.draw_app.app.inform.emit('[WARNING_NOTCL] %s' %
                                          _("Aperture size is zero. It needs to be greater than zero."))
            self.dont_execute = True
            return
        else:
            self.dont_execute = False

        self.storage_obj = self.draw_app.storage_dict[self.draw_app.last_aperture_selected]['geometry']
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

        self.draw_app.app.jump_signal.connect(lambda x: self.draw_app.update_utility_geometry(data=x))

        # Switch notebook to Selected page
        self.draw_app.app.ui.notebook.setCurrentWidget(self.draw_app.app.ui.selected_tab)

        self.start_msg = _("Click to place ...")

    def click(self, point):
        self.make()
        return "Done."

    def utility_geometry(self, data=None):
        if self.dont_execute is True:
            self.draw_app.select_tool('select')
            return

        self.points = data
        geo_data = self.util_shape(data)
        if geo_data:
            return DrawToolUtilityShape(geo_data)
        else:
            return None

    def util_shape(self, point):
        # updating values here allows us to change the aperture on the fly, after the Tool has been started
        self.storage_obj = self.draw_app.storage_dict[self.draw_app.last_aperture_selected]['geometry']
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
            new_geo_el = {}

            center = Point([point_x, point_y])
            new_geo_el['solid'] = center.buffer(self.radius)
            new_geo_el['follow'] = center
            return new_geo_el
        elif ap_type == 'R':
            new_geo_el = {}

            p1 = (point_x - self.half_width, point_y - self.half_height)
            p2 = (point_x + self.half_width, point_y - self.half_height)
            p3 = (point_x + self.half_width, point_y + self.half_height)
            p4 = (point_x - self.half_width, point_y + self.half_height)
            center = Point([point_x, point_y])
            new_geo_el['solid'] = Polygon([p1, p2, p3, p4, p1])
            new_geo_el['follow'] = center
            return new_geo_el
        elif ap_type == 'O':
            geo = []
            new_geo_el = {}

            if self.half_height > self.half_width:
                p1 = (point_x - self.half_width, point_y - self.half_height + self.half_width)
                p2 = (point_x + self.half_width, point_y - self.half_height + self.half_width)
                p3 = (point_x + self.half_width, point_y + self.half_height - self.half_width)
                p4 = (point_x - self.half_width, point_y + self.half_height - self.half_width)

                down_center = [point_x, point_y - self.half_height + self.half_width]
                d_start_angle = np.pi
                d_stop_angle = 0.0
                down_arc = arc(down_center, self.half_width, d_start_angle, d_stop_angle, 'ccw', self.steps_per_circ)

                up_center = [point_x, point_y + self.half_height - self.half_width]
                u_start_angle = 0.0
                u_stop_angle = np.pi
                up_arc = arc(up_center, self.half_width, u_start_angle, u_stop_angle, 'ccw', self.steps_per_circ)

                geo.append(p1)
                for pt in down_arc:
                    geo.append(pt)
                geo.append(p2)
                geo.append(p3)
                for pt in up_arc:
                    geo.append(pt)
                geo.append(p4)
                new_geo_el['solid'] = Polygon(geo)
                center = Point([point_x, point_y])
                new_geo_el['follow'] = center
                return new_geo_el

            else:
                p1 = (point_x - self.half_width + self.half_height, point_y - self.half_height)
                p2 = (point_x + self.half_width - self.half_height, point_y - self.half_height)
                p3 = (point_x + self.half_width - self.half_height, point_y + self.half_height)
                p4 = (point_x - self.half_width + self.half_height, point_y + self.half_height)

                left_center = [point_x - self.half_width + self.half_height, point_y]
                d_start_angle = np.pi / 2
                d_stop_angle = 1.5 * np.pi
                left_arc = arc(left_center, self.half_height, d_start_angle, d_stop_angle, 'ccw', self.steps_per_circ)

                right_center = [point_x + self.half_width - self.half_height, point_y]
                u_start_angle = 1.5 * np.pi
                u_stop_angle = np.pi / 2
                right_arc = arc(right_center, self.half_height, u_start_angle, u_stop_angle, 'ccw', self.steps_per_circ)

                geo.append(p1)
                geo.append(p2)
                for pt in right_arc:
                    geo.append(pt)
                geo.append(p3)
                geo.append(p4)
                for pt in left_arc:
                    geo.append(pt)
                new_geo_el['solid'] = Polygon(geo)
                center = Point([point_x, point_y])
                new_geo_el['follow'] = center
                return new_geo_el
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
        self.draw_app.app.inform.emit('[success] %s' % _("Done. Adding Pad completed."))
        self.draw_app.app.jump_signal.disconnect()

    def clean_up(self):
        self.draw_app.selected = []
        self.draw_app.apertures_table.clearSelection()
        self.draw_app.plot_all()
        try:
            self.draw_app.app.jump_signal.disconnect()
        except (TypeError, AttributeError):
            pass


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
            self.draw_app.app.inform.emit('[WARNING_NOTCL] %s' %
                                          _("To add an Pad Array first select a aperture in Aperture Table"))
            self.complete = True
            self.draw_app.in_action = False
            self.draw_app.array_frame.hide()
            return

        if self.radius == 0:
            self.draw_app.app.inform.emit('[WARNING_NOTCL] %s' %
                                          _("Aperture size is zero. It needs to be greater than zero."))
            self.dont_execute = True
            return
        else:
            self.dont_execute = False

        try:
            QtGui.QGuiApplication.restoreOverrideCursor()
        except Exception:
            pass
        self.cursor = QtGui.QCursor(QtGui.QPixmap(self.draw_app.app.resource_location + '/aero_array.png'))
        QtGui.QGuiApplication.setOverrideCursor(self.cursor)

        self.storage_obj = self.draw_app.storage_dict[self.draw_app.last_aperture_selected]['geometry']
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

        geo = self.utility_geometry(data=(self.draw_app.snap_x, self.draw_app.snap_y), static=True)

        if isinstance(geo, DrawToolShape) and geo.geo is not None:
            self.draw_app.draw_utility_geometry(geo=geo)

        self.draw_app.app.inform.emit(_("Click on target location ..."))

        self.draw_app.app.jump_signal.connect(lambda x: self.draw_app.update_utility_geometry(data=x))

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
        if self.dont_execute is True:
            self.draw_app.select_tool('select')
            return

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
                self.draw_app.app.inform.emit('[ERROR_NOTCL] %s' %
                                              _("The value is not Float. Check for comma instead of dot separator."))
                return
        except Exception:
            self.draw_app.app.inform.emit('[ERROR_NOTCL] %s' % _("The value is mistyped. Check the value."))
            return

        if self.pad_array == 'Linear':
            if data[0] is None and data[1] is None:
                dx = self.draw_app.x
                dy = self.draw_app.y
            else:
                dx = data[0]
                dy = data[1]

            geo_el_list = []
            geo_el = []
            self.points = [dx, dy]

            for item in range(self.pad_array_size):
                if self.pad_axis == 'X':
                    geo_el = self.util_shape(((dx + (self.pad_pitch * item)), dy))
                if self.pad_axis == 'Y':
                    geo_el = self.util_shape((dx, (dy + (self.pad_pitch * item))))
                if self.pad_axis == 'A':
                    x_adj = self.pad_pitch * math.cos(math.radians(self.pad_linear_angle))
                    y_adj = self.pad_pitch * math.sin(math.radians(self.pad_linear_angle))
                    geo_el = self.util_shape(
                        ((dx + (x_adj * item)), (dy + (y_adj * item)))
                    )

                if static is None or static is False:
                    new_geo_el = {}

                    if 'solid' in geo_el:
                        new_geo_el['solid'] = affinity.translate(
                            geo_el['solid'], xoff=(dx - self.last_dx), yoff=(dy - self.last_dy)
                        )
                    if 'follow' in geo_el:
                        new_geo_el['follow'] = affinity.translate(
                            geo_el['follow'], xoff=(dx - self.last_dx), yoff=(dy - self.last_dy)
                        )
                    geo_el_list.append(new_geo_el)

                else:
                    geo_el_list.append(geo_el)
            # self.origin = data

            self.last_dx = dx
            self.last_dy = dy
            return DrawToolUtilityShape(geo_el_list)
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
        self.storage_obj = self.draw_app.storage_dict[self.draw_app.last_aperture_selected]['geometry']
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
            new_geo_el = {}

            center = Point([point_x, point_y])
            new_geo_el['solid'] = center.buffer(self.radius)
            new_geo_el['follow'] = center
            return new_geo_el
        elif ap_type == 'R':
            new_geo_el = {}

            p1 = (point_x - self.half_width, point_y - self.half_height)
            p2 = (point_x + self.half_width, point_y - self.half_height)
            p3 = (point_x + self.half_width, point_y + self.half_height)
            p4 = (point_x - self.half_width, point_y + self.half_height)
            new_geo_el['solid'] = Polygon([p1, p2, p3, p4, p1])
            new_geo_el['follow'] = Point([point_x, point_y])
            return new_geo_el
        elif ap_type == 'O':
            geo = []
            new_geo_el = {}

            if self.half_height > self.half_width:
                p1 = (point_x - self.half_width, point_y - self.half_height + self.half_width)
                p2 = (point_x + self.half_width, point_y - self.half_height + self.half_width)
                p3 = (point_x + self.half_width, point_y + self.half_height - self.half_width)
                p4 = (point_x - self.half_width, point_y + self.half_height - self.half_width)

                down_center = [point_x, point_y - self.half_height + self.half_width]
                d_start_angle = np.pi
                d_stop_angle = 0.0
                down_arc = arc(down_center, self.half_width, d_start_angle, d_stop_angle, 'ccw', self.steps_per_circ)

                up_center = [point_x, point_y + self.half_height - self.half_width]
                u_start_angle = 0.0
                u_stop_angle = np.pi
                up_arc = arc(up_center, self.half_width, u_start_angle, u_stop_angle, 'ccw', self.steps_per_circ)

                geo.append(p1)
                for pt in down_arc:
                    geo.append(pt)
                geo.append(p2)
                geo.append(p3)
                for pt in up_arc:
                    geo.append(pt)
                geo.append(p4)

                new_geo_el['solid'] = Polygon(geo)
                center = Point([point_x, point_y])
                new_geo_el['follow'] = center
                return new_geo_el
            else:
                p1 = (point_x - self.half_width + self.half_height, point_y - self.half_height)
                p2 = (point_x + self.half_width - self.half_height, point_y - self.half_height)
                p3 = (point_x + self.half_width - self.half_height, point_y + self.half_height)
                p4 = (point_x - self.half_width + self.half_height, point_y + self.half_height)

                left_center = [point_x - self.half_width + self.half_height, point_y]
                d_start_angle = np.pi / 2
                d_stop_angle = 1.5 * np.pi
                left_arc = arc(left_center, self.half_height, d_start_angle, d_stop_angle, 'ccw', self.steps_per_circ)

                right_center = [point_x + self.half_width - self.half_height, point_y]
                u_start_angle = 1.5 * np.pi
                u_stop_angle = np.pi / 2
                right_arc = arc(right_center, self.half_height, u_start_angle, u_stop_angle, 'ccw', self.steps_per_circ)

                geo.append(p1)
                geo.append(p2)
                for pt in right_arc:
                    geo.append(pt)
                geo.append(p3)
                geo.append(p4)
                for pt in left_arc:
                    geo.append(pt)

                new_geo_el['solid'] = Polygon(geo)
                center = Point([point_x, point_y])
                new_geo_el['follow'] = center
                return new_geo_el
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
                self.draw_app.app.inform.emit('[WARNING_NOTCL] %s' %
                                              _("Too many Pads for the selected spacing angle."))
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
        self.draw_app.app.inform.emit('[success] %s' %
                                      _("Done. Pad Array added."))
        self.draw_app.in_action = False
        self.draw_app.array_frame.hide()
        self.draw_app.app.jump_signal.disconnect()

    def clean_up(self):
        self.draw_app.selected = []
        self.draw_app.apertures_table.clearSelection()
        self.draw_app.plot_all()
        try:
            self.draw_app.app.jump_signal.disconnect()
        except (TypeError, AttributeError):
            pass


class FCPoligonize(FCShapeTool):
    """
    Resulting type: Polygon
    """

    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.name = 'poligonize'
        self.draw_app = draw_app

        self.draw_app.app.inform.emit(_("Select shape(s) and then click ..."))
        self.draw_app.in_action = True
        self.make()

    def click(self, point):
        return ""

    def make(self):
        if not self.draw_app.selected:
            self.draw_app.in_action = False
            self.complete = True
            self.draw_app.app.inform.emit('[ERROR_NOTCL] %s' %
                                          _("Failed. Nothing selected."))
            self.draw_app.select_tool("select")
            return

        apcode_set = set()
        for elem in self.draw_app.selected:
            for apcode in self.draw_app.storage_dict:
                if 'geometry' in self.draw_app.storage_dict[apcode]:
                    if elem in self.draw_app.storage_dict[apcode]['geometry']:
                        apcode_set.add(apcode)
                        break

        if len(apcode_set) > 1:
            self.draw_app.in_action = False
            self.complete = True
            self.draw_app.app.inform.emit('[WARNING_NOTCL] %s' %
                                          _("Failed. Poligonize works only on geometries belonging "
                                            "to the same aperture."))
            self.draw_app.select_tool("select")
            return

        # exterior_geo = [Polygon(sh.geo.exterior) for sh in self.draw_app.selected]

        exterior_geo = []
        for geo_shape in self.draw_app.selected:
            geometric_data = geo_shape.geo
            if 'solid' in geometric_data:
                exterior_geo.append(Polygon(geometric_data['solid'].exterior))

        fused_geo = MultiPolygon(exterior_geo)
        fused_geo = fused_geo.buffer(0.0000001)

        current_storage = self.draw_app.storage_dict[self.draw_app.last_aperture_selected]['geometry']
        if isinstance(fused_geo, MultiPolygon):
            for geo in fused_geo:
                # clean-up the geo
                geo = geo.buffer(0)

                if len(geo.interiors) == 0:
                    try:
                        current_storage = self.draw_app.storage_dict['0']['geometry']
                    except KeyError:
                        self.draw_app.on_aperture_add(apcode='0')
                        current_storage = self.draw_app.storage_dict['0']['geometry']
                new_el = {}
                new_el['solid'] = geo
                new_el['follow'] = geo.exterior
                self.draw_app.on_grb_shape_complete(current_storage, specific_shape=DrawToolShape(deepcopy(new_el)))
        else:
            # clean-up the geo
            fused_geo = fused_geo.buffer(0)

            if len(fused_geo.interiors) == 0 and len(exterior_geo) == 1:
                try:
                    current_storage = self.draw_app.storage_dict['0']['geometry']
                except KeyError:
                    self.draw_app.on_aperture_add(apcode='0')
                    current_storage = self.draw_app.storage_dict['0']['geometry']

            new_el = {}
            new_el['solid'] = fused_geo
            new_el['follow'] = fused_geo.exterior
            self.draw_app.on_grb_shape_complete(current_storage, specific_shape=DrawToolShape(deepcopy(new_el)))

        self.draw_app.delete_selected()
        self.draw_app.plot_all()

        self.draw_app.in_action = False
        self.complete = True
        self.draw_app.app.inform.emit('[success] %s' %
                                      _("Done. Poligonize completed."))

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

        self.steps_per_circle = self.draw_app.app.defaults["gerber_circle_steps"]

        size_ap = float(self.draw_app.storage_dict[self.draw_app.last_aperture_selected]['size'])
        self.buf_val = (size_ap / 2) if size_ap > 0 else 0.0000001

        self.gridx_size = float(self.draw_app.app.ui.grid_gap_x_entry.get_value())
        self.gridy_size = float(self.draw_app.app.ui.grid_gap_y_entry.get_value())

        self.temp_points = []
        # this will store the inflexion point in the geometry
        self.inter_point = None

        try:
            QtGui.QGuiApplication.restoreOverrideCursor()
        except Exception as e:
            log.debug("AppGerberEditor.FCRegion --> %s" % str(e))

        self.cursor = QtGui.QCursor(QtGui.QPixmap(self.draw_app.app.resource_location + '/aero.png'))
        QtGui.QGuiApplication.setOverrideCursor(self.cursor)

        self.draw_app.app.jump_signal.connect(lambda x: self.draw_app.update_utility_geometry(data=x))

        self.draw_app.app.inform.emit(_('Corner Mode 1: 45 degrees ...'))

        self.start_msg = _("Click on 1st point ...")

    def click(self, point):
        self.draw_app.in_action = True

        if self.inter_point is not None:
            self.points.append(self.inter_point)
        self.points.append(point)

        if len(self.points) > 0:
            self.draw_app.app.inform.emit(_("Click on next Point or click Right mouse button to complete ..."))
            return "Click on next point or hit ENTER to complete ..."

        return ""

    def update_grid_info(self):
        self.gridx_size = float(self.draw_app.app.ui.grid_gap_x_entry.get_value())
        self.gridy_size = float(self.draw_app.app.ui.grid_gap_y_entry.get_value())

    def utility_geometry(self, data=None):
        new_geo_el = {}

        x = data[0]
        y = data[1]

        if len(self.points) == 0:
            new_geo_el['solid'] = Point(data).buffer(self.buf_val, resolution=int(self.steps_per_circle / 4))
            return DrawToolUtilityShape(new_geo_el)

        if len(self.points) == 1:
            self.temp_points = [x for x in self.points]

            old_x = self.points[0][0]
            old_y = self.points[0][1]
            mx = abs(round((x - old_x) / self.gridx_size))
            my = abs(round((y - old_y) / self.gridy_size))

            if mx and my:
                if self.draw_app.app.ui.grid_snap_btn.isChecked():
                    if self.draw_app.bend_mode != 5:
                        if self.draw_app.bend_mode == 1:
                            if x > old_x:
                                if mx > my:
                                    self.inter_point = (old_x + self.gridx_size * (mx - my), old_y)
                                if mx < my:
                                    if y < old_y:
                                        self.inter_point = (old_x, old_y - self.gridy_size * (my - mx))
                                    else:
                                        self.inter_point = (old_x, old_y - self.gridy_size * (mx - my))
                            if x < old_x:
                                if mx > my:
                                    self.inter_point = (old_x - self.gridx_size * (mx - my), old_y)
                                if mx < my:
                                    if y < old_y:
                                        self.inter_point = (old_x, old_y - self.gridy_size * (my - mx))
                                    else:
                                        self.inter_point = (old_x, old_y - self.gridy_size * (mx - my))
                        elif self.draw_app.bend_mode == 2:
                            if x > old_x:
                                if mx > my:
                                    self.inter_point = (old_x + self.gridx_size * my, y)
                                if mx < my:
                                    if y < old_y:
                                        self.inter_point = (x, old_y - self.gridy_size * mx)
                                    else:
                                        self.inter_point = (x, old_y + self.gridy_size * mx)
                            if x < old_x:
                                if mx > my:
                                    self.inter_point = (old_x - self.gridx_size * my, y)
                                if mx < my:
                                    if y < old_y:
                                        self.inter_point = (x, old_y - self.gridy_size * mx)
                                    else:
                                        self.inter_point = (x, old_y + self.gridy_size * mx)
                        elif self.draw_app.bend_mode == 3:
                            self.inter_point = (x, old_y)
                        elif self.draw_app.bend_mode == 4:
                            self.inter_point = (old_x, y)

                        if self.inter_point is not None:
                            self.temp_points.append(self.inter_point)
                        else:
                            self.inter_point = data

                else:
                    self.inter_point = data

            self.temp_points.append(data)
            new_geo_el = {}

            if len(self.temp_points) > 1:
                try:
                    new_geo_el['solid'] = LineString(self.temp_points).buffer(self.buf_val,
                                                                              resolution=int(self.steps_per_circle / 4),
                                                                              join_style=1)
                    return DrawToolUtilityShape(new_geo_el)
                except Exception as e:
                    log.debug("AppGerberEditor.FCRegion.utility_geometry() --> %s" % str(e))
            else:
                new_geo_el['solid'] = Point(self.temp_points).buffer(self.buf_val,
                                                                     resolution=int(self.steps_per_circle / 4))
                return DrawToolUtilityShape(new_geo_el)

        if len(self.points) > 2:
            self.temp_points = [x for x in self.points]
            old_x = self.points[-1][0]
            old_y = self.points[-1][1]
            mx = abs(round((x - old_x) / self.gridx_size))
            my = abs(round((y - old_y) / self.gridy_size))

            if mx and my:
                if self.draw_app.app.ui.grid_snap_btn.isChecked():
                    if self.draw_app.bend_mode != 5:
                        if self.draw_app.bend_mode == 1:
                            if x > old_x:
                                if mx > my:
                                    self.inter_point = (old_x + self.gridx_size * (mx - my), old_y)
                                if mx < my:
                                    if y < old_y:
                                        self.inter_point = (old_x, old_y - self.gridy_size * (my - mx))
                                    else:
                                        self.inter_point = (old_x, old_y - self.gridy_size * (mx - my))
                            if x < old_x:
                                if mx > my:
                                    self.inter_point = (old_x - self.gridx_size * (mx - my), old_y)
                                if mx < my:
                                    if y < old_y:
                                        self.inter_point = (old_x, old_y - self.gridy_size * (my - mx))
                                    else:
                                        self.inter_point = (old_x, old_y - self.gridy_size * (mx - my))
                        elif self.draw_app.bend_mode == 2:
                            if x > old_x:
                                if mx > my:
                                    self.inter_point = (old_x + self.gridx_size * my, y)
                                if mx < my:
                                    if y < old_y:
                                        self.inter_point = (x, old_y - self.gridy_size * mx)
                                    else:
                                        self.inter_point = (x, old_y + self.gridy_size * mx)
                            if x < old_x:
                                if mx > my:
                                    self.inter_point = (old_x - self.gridx_size * my, y)
                                if mx < my:
                                    if y < old_y:
                                        self.inter_point = (x, old_y - self.gridy_size * mx)
                                    else:
                                        self.inter_point = (x, old_y + self.gridy_size * mx)
                        elif self.draw_app.bend_mode == 3:
                            self.inter_point = (x, old_y)
                        elif self.draw_app.bend_mode == 4:
                            self.inter_point = (old_x, y)

                        self.temp_points.append(self.inter_point)
            self.temp_points.append(data)
            new_geo_el = {}

            new_geo_el['solid'] = LinearRing(self.temp_points).buffer(self.buf_val,
                                                                      resolution=int(self.steps_per_circle / 4),
                                                                      join_style=1)
            new_geo_el['follow'] = LinearRing(self.temp_points)

            return DrawToolUtilityShape(new_geo_el)

        return None

    def make(self):
        # self.geometry = LinearRing(self.points)
        if len(self.points) > 2:

            # regions are added always in the '0' aperture
            if '0' not in self.draw_app.storage_dict:
                self.draw_app.on_aperture_add(apcode='0')
            else:
                self.draw_app.last_aperture_selected = '0'

            new_geo_el = {}

            new_geo_el['solid'] = Polygon(self.points).buffer(self.buf_val,
                                                              resolution=int(self.steps_per_circle / 4),
                                                              join_style=2)
            new_geo_el['follow'] = Polygon(self.points).exterior

            self.geometry = DrawToolShape(new_geo_el)
        self.draw_app.in_action = False
        self.complete = True

        self.draw_app.app.jump_signal.disconnect()

        self.draw_app.app.inform.emit('[success] %s' % _("Done."))

    def on_key(self, key):
        # Jump to coords
        if key == QtCore.Qt.Key_J or key == 'J':
            self.draw_app.app.on_jump_to()

        if key == 'Backspace' or key == QtCore.Qt.Key_Backspace:
            if len(self.points) > 0:
                if self.draw_app.bend_mode == 5:
                    self.points = self.points[0:-1]
                else:
                    self.points = self.points[0:-2]
                # Remove any previous utility shape
                self.draw_app.tool_shape.clear(update=False)
                geo = self.utility_geometry(data=(self.draw_app.snap_x, self.draw_app.snap_y))
                self.draw_app.draw_utility_geometry(geo=geo)
                return _("Backtracked one point ...")

        if key == 'T' or key == QtCore.Qt.Key_T:
            if self.draw_app.bend_mode == 1:
                self.draw_app.bend_mode = 2
                msg = _('Corner Mode 2: Reverse 45 degrees ...')
            elif self.draw_app.bend_mode == 2:
                self.draw_app.bend_mode = 3
                msg = _('Corner Mode 3: 90 degrees ...')
            elif self.draw_app.bend_mode == 3:
                self.draw_app.bend_mode = 4
                msg = _('Corner Mode 4: Reverse 90 degrees ...')
            elif self.draw_app.bend_mode == 4:
                self.draw_app.bend_mode = 5
                msg = _('Corner Mode 5: Free angle ...')
            else:
                self.draw_app.bend_mode = 1
                msg = _('Corner Mode 1: 45 degrees ...')

            # Remove any previous utility shape
            self.draw_app.tool_shape.clear(update=False)
            geo = self.utility_geometry(data=(self.draw_app.snap_x, self.draw_app.snap_y))
            self.draw_app.draw_utility_geometry(geo=geo)

            return msg

        if key == 'R' or key == QtCore.Qt.Key_R:
            if self.draw_app.bend_mode == 1:
                self.draw_app.bend_mode = 5
                msg = _('Corner Mode 5: Free angle ...')
            elif self.draw_app.bend_mode == 5:
                self.draw_app.bend_mode = 4
                msg = _('Corner Mode 4: Reverse 90 degrees ...')
            elif self.draw_app.bend_mode == 4:
                self.draw_app.bend_mode = 3
                msg = _('Corner Mode 3: 90 degrees ...')
            elif self.draw_app.bend_mode == 3:
                self.draw_app.bend_mode = 2
                msg = _('Corner Mode 2: Reverse 45 degrees ...')
            else:
                self.draw_app.bend_mode = 1
                msg = _('Corner Mode 1: 45 degrees ...')

            # Remove any previous utility shape
            self.draw_app.tool_shape.clear(update=False)
            geo = self.utility_geometry(data=(self.draw_app.snap_x, self.draw_app.snap_y))
            self.draw_app.draw_utility_geometry(geo=geo)

            return msg

    def clean_up(self):
        self.draw_app.selected = []
        self.draw_app.apertures_table.clearSelection()
        self.draw_app.plot_all()
        try:
            self.draw_app.app.jump_signal.disconnect()
        except (TypeError, AttributeError):
            pass


class FCTrack(FCShapeTool):
    """
    Resulting type: Polygon
    """
    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.name = 'track'
        self.draw_app = draw_app

        self.steps_per_circle = self.draw_app.app.defaults["gerber_circle_steps"]

        size_ap = float(self.draw_app.storage_dict[self.draw_app.last_aperture_selected]['size'])
        self.buf_val = (size_ap / 2) if size_ap > 0 else 0.0000001

        self.gridx_size = float(self.draw_app.app.ui.grid_gap_x_entry.get_value())
        self.gridy_size = float(self.draw_app.app.ui.grid_gap_y_entry.get_value())

        self.temp_points = []

        self. final_click = False
        try:
            QtGui.QGuiApplication.restoreOverrideCursor()
        except Exception as e:
            log.debug("AppGerberEditor.FCTrack.__init__() --> %s" % str(e))

        self.cursor = QtGui.QCursor(QtGui.QPixmap(self.draw_app.app.resource_location +
                                                  '/aero_path%s.png' % self.draw_app.bend_mode))
        QtGui.QGuiApplication.setOverrideCursor(self.cursor)

        self.draw_app.app.jump_signal.connect(lambda x: self.draw_app.update_utility_geometry(data=x))

        self.draw_app.app.inform.emit(_('Track Mode 1: 45 degrees ...'))

    def click(self, point):
        self.draw_app.in_action = True

        if not self.points:
            self.points.append(point)
        elif point != self.points[-1]:
            self.points.append(point)
        else:
            return

        new_geo_el = {}

        if len(self.temp_points) == 1:
            new_geo_el['solid'] = Point(self.temp_points).buffer(self.buf_val, int(self.steps_per_circle))
            new_geo_el['follow'] = Point(self.temp_points)
        else:
            new_geo_el['solid'] = LineString(self.temp_points).buffer(self.buf_val, int(self.steps_per_circle))
            new_geo_el['follow'] = LineString(self.temp_points)

        self.draw_app.add_gerber_shape(DrawToolShape(new_geo_el),
                                       self.draw_app.storage_dict[self.draw_app.last_aperture_selected]['geometry'])

        self.draw_app.plot_all()
        if len(self.points) > 0:
            self.draw_app.app.inform.emit(_("Click on next Point or click Right mouse button to complete ..."))
            return "Click on next point or hit ENTER to complete ..."

        return ""

    def update_grid_info(self):
        self.gridx_size = float(self.draw_app.app.ui.grid_gap_x_entry.get_value())
        self.gridy_size = float(self.draw_app.app.ui.grid_gap_y_entry.get_value())

    def utility_geometry(self, data=None):
        self.update_grid_info()
        new_geo_el = {}

        if not self.points:
            new_geo_el['solid'] = Point(data).buffer(self.buf_val, int(self.steps_per_circle))
            return DrawToolUtilityShape(new_geo_el)
        else:
            old_x = self.points[-1][0]
            old_y = self.points[-1][1]
            x = data[0]
            y = data[1]

            self.temp_points = [self.points[-1]]

            mx = abs(round((x - old_x) / self.gridx_size))
            my = abs(round((y - old_y) / self.gridy_size))

            if self.draw_app.app.ui.grid_snap_btn.isChecked():
                if self.draw_app.bend_mode == 1:
                    if x > old_x:
                        if mx > my:
                            self.temp_points.append((old_x + self.gridx_size*(mx-my), old_y))
                        if mx < my:
                            if y < old_y:
                                self.temp_points.append((old_x, old_y - self.gridy_size * (my-mx)))
                            else:
                                self.temp_points.append((old_x, old_y - self.gridy_size * (mx-my)))
                    if x < old_x:
                        if mx > my:
                            self.temp_points.append((old_x - self.gridx_size*(mx-my), old_y))
                        if mx < my:
                            if y < old_y:
                                self.temp_points.append((old_x, old_y - self.gridy_size * (my-mx)))
                            else:
                                self.temp_points.append((old_x, old_y - self.gridy_size * (mx-my)))
                elif self.draw_app.bend_mode == 2:
                    if x > old_x:
                        if mx > my:
                            self.temp_points.append((old_x + self.gridx_size*my, y))
                        if mx < my:
                            if y < old_y:
                                self.temp_points.append((x, old_y - self.gridy_size * mx))
                            else:
                                self.temp_points.append((x, old_y + self.gridy_size * mx))
                    if x < old_x:
                        if mx > my:
                            self.temp_points.append((old_x - self.gridx_size * my, y))
                        if mx < my:
                            if y < old_y:
                                self.temp_points.append((x, old_y - self.gridy_size * mx))
                            else:
                                self.temp_points.append((x, old_y + self.gridy_size * mx))
                elif self.draw_app.bend_mode == 3:
                    self.temp_points.append((x, old_y))
                elif self.draw_app.bend_mode == 4:
                    self.temp_points.append((old_x, y))
                else:
                    pass

            self.temp_points.append(data)
            if len(self.temp_points) == 1:
                new_geo_el['solid'] = Point(self.temp_points).buffer(self.buf_val, int(self.steps_per_circle))
                return DrawToolUtilityShape(new_geo_el)

            new_geo_el['solid'] = LineString(self.temp_points).buffer(self.buf_val, int(self.steps_per_circle))
            return DrawToolUtilityShape(new_geo_el)

    def make(self):
        new_geo_el = {}
        if len(self.temp_points) == 1:
            new_geo_el['solid'] = Point(self.temp_points).buffer(self.buf_val, int(self.steps_per_circle))
            new_geo_el['follow'] = Point(self.temp_points)
        else:
            new_geo_el['solid'] = LineString(self.temp_points).buffer(self.buf_val, int(self.steps_per_circle))
            new_geo_el['solid'] = new_geo_el['solid'].buffer(0)     # try to clean the geometry
            new_geo_el['follow'] = LineString(self.temp_points)

        self.geometry = DrawToolShape(new_geo_el)

        self.draw_app.in_action = False
        self.complete = True

        self.draw_app.app.jump_signal.disconnect()
        self.draw_app.app.inform.emit('[success] %s' % _("Done."))

    def on_key(self, key):
        if key == 'Backspace' or key == QtCore.Qt.Key_Backspace:
            if len(self.points) > 0:
                self.temp_points = self.points[0:-1]
                # Remove any previous utility shape
                self.draw_app.tool_shape.clear(update=False)
                geo = self.utility_geometry(data=(self.draw_app.snap_x, self.draw_app.snap_y))
                self.draw_app.draw_utility_geometry(geo=geo)
                return _("Backtracked one point ...")

        # Jump to coords
        if key == QtCore.Qt.Key_J or key == 'J':
            self.draw_app.app.on_jump_to()

        if key == 'T' or key == QtCore.Qt.Key_T:
            try:
                QtGui.QGuiApplication.restoreOverrideCursor()
            except Exception as e:
                log.debug("AppGerberEditor.FCTrack.on_key() --> %s" % str(e))

            if self.draw_app.bend_mode == 1:
                self.draw_app.bend_mode = 2
                self.cursor = QtGui.QCursor(QtGui.QPixmap(self.draw_app.app.resource_location + '/aero_path2.png'))
                QtGui.QGuiApplication.setOverrideCursor(self.cursor)
                msg = _('Track Mode 2: Reverse 45 degrees ...')
            elif self.draw_app.bend_mode == 2:
                self.draw_app.bend_mode = 3
                self.cursor = QtGui.QCursor(QtGui.QPixmap(self.draw_app.app.resource_location + '/aero_path3.png'))
                QtGui.QGuiApplication.setOverrideCursor(self.cursor)
                msg = _('Track Mode 3: 90 degrees ...')
            elif self.draw_app.bend_mode == 3:
                self.draw_app.bend_mode = 4
                self.cursor = QtGui.QCursor(QtGui.QPixmap(self.draw_app.app.resource_location + '/aero_path4.png'))
                QtGui.QGuiApplication.setOverrideCursor(self.cursor)
                msg = _('Track Mode 4: Reverse 90 degrees ...')
            elif self.draw_app.bend_mode == 4:
                self.draw_app.bend_mode = 5
                self.cursor = QtGui.QCursor(QtGui.QPixmap(self.draw_app.app.resource_location + '/aero_path5.png'))
                QtGui.QGuiApplication.setOverrideCursor(self.cursor)
                msg = _('Track Mode 5: Free angle ...')
            else:
                self.draw_app.bend_mode = 1
                self.cursor = QtGui.QCursor(QtGui.QPixmap(self.draw_app.app.resource_location + '/aero_path1.png'))
                QtGui.QGuiApplication.setOverrideCursor(self.cursor)
                msg = _('Track Mode 1: 45 degrees ...')

            # Remove any previous utility shape
            self.draw_app.tool_shape.clear(update=False)
            geo = self.utility_geometry(data=(self.draw_app.snap_x, self.draw_app.snap_y))
            self.draw_app.draw_utility_geometry(geo=geo)

            return msg

        if key == 'R' or key == QtCore.Qt.Key_R:
            try:
                QtGui.QGuiApplication.restoreOverrideCursor()
            except Exception as e:
                log.debug("AppGerberEditor.FCTrack.on_key() --> %s" % str(e))

            if self.draw_app.bend_mode == 1:
                self.draw_app.bend_mode = 5
                self.cursor = QtGui.QCursor(QtGui.QPixmap(self.draw_app.app.resource_location + '/aero_path5.png'))
                QtGui.QGuiApplication.setOverrideCursor(self.cursor)
                msg = _('Track Mode 5: Free angle ...')
            elif self.draw_app.bend_mode == 5:
                self.draw_app.bend_mode = 4
                self.cursor = QtGui.QCursor(QtGui.QPixmap(self.draw_app.app.resource_location + '/aero_path4.png'))
                QtGui.QGuiApplication.setOverrideCursor(self.cursor)
                msg = _('Track Mode 4: Reverse 90 degrees ...')
            elif self.draw_app.bend_mode == 4:
                self.draw_app.bend_mode = 3
                self.cursor = QtGui.QCursor(QtGui.QPixmap(self.draw_app.app.resource_location + '/aero_path3.png'))
                QtGui.QGuiApplication.setOverrideCursor(self.cursor)
                msg = _('Track Mode 3: 90 degrees ...')
            elif self.draw_app.bend_mode == 3:
                self.draw_app.bend_mode = 2
                self.cursor = QtGui.QCursor(QtGui.QPixmap(self.draw_app.app.resource_location + '/aero_path2.png'))
                QtGui.QGuiApplication.setOverrideCursor(self.cursor)
                msg = _('Track Mode 2: Reverse 45 degrees ...')
            else:
                self.draw_app.bend_mode = 1
                self.cursor = QtGui.QCursor(QtGui.QPixmap(self.draw_app.app.resource_location + '/aero_path1.png'))
                QtGui.QGuiApplication.setOverrideCursor(self.cursor)
                msg = _('Track Mode 1: 45 degrees ...')

            # Remove any previous utility shape
            self.draw_app.tool_shape.clear(update=False)
            geo = self.utility_geometry(data=(self.draw_app.snap_x, self.draw_app.snap_y))
            self.draw_app.draw_utility_geometry(geo=geo)

            return msg

    def clean_up(self):
        self.draw_app.selected = []
        self.draw_app.apertures_table.clearSelection()
        self.draw_app.plot_all()
        try:
            self.draw_app.app.jump_signal.disconnect()
        except (TypeError, AttributeError):
            pass


class FCDisc(FCShapeTool):
    """
    Resulting type: Polygon
    """

    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.name = 'disc'

        try:
            QtGui.QGuiApplication.restoreOverrideCursor()
        except Exception:
            pass
        self.cursor = QtGui.QCursor(QtGui.QPixmap(self.draw_app.app.resource_location + '/aero_disc.png'))
        QtGui.QGuiApplication.setOverrideCursor(self.cursor)

        size_ap = float(self.draw_app.storage_dict[self.draw_app.last_aperture_selected]['size'])
        self.buf_val = (size_ap / 2) if size_ap > 0 else 0.0000001

        if '0' in self.draw_app.storage_dict:
            self.storage_obj = self.draw_app.storage_dict['0']['geometry']
        else:
            self.draw_app.storage_dict['0'] = {}
            self.draw_app.storage_dict['0']['type'] = 'C'
            self.draw_app.storage_dict['0']['size'] = 0.0
            self.draw_app.storage_dict['0']['geometry'] = []
            self.storage_obj = self.draw_app.storage_dict['0']['geometry']

        self.draw_app.app.inform.emit(_("Click on Center point ..."))

        self.draw_app.app.jump_signal.connect(lambda x: self.draw_app.update_utility_geometry(data=x))

        self.steps_per_circ = self.draw_app.app.defaults["gerber_circle_steps"]

    def click(self, point):
        self.points.append(point)

        if len(self.points) == 1:
            self.draw_app.app.inform.emit(_("Click on Perimeter point to complete ..."))
            return "Click on Perimeter to complete ..."

        if len(self.points) == 2:
            self.make()
            return "Done."

        return ""

    def utility_geometry(self, data=None):
        new_geo_el = {}
        if len(self.points) == 1:
            p1 = self.points[0]
            p2 = data
            radius = math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)
            new_geo_el['solid'] = Point(p1).buffer((radius + self.buf_val / 2), int(self.steps_per_circ / 4))
            return DrawToolUtilityShape(new_geo_el)

        return None

    def make(self):
        new_geo_el = {}

        try:
            QtGui.QGuiApplication.restoreOverrideCursor()
        except Exception as e:
            log.debug("AppGerberEditor.FCDisc --> %s" % str(e))

        self.draw_app.current_storage = self.storage_obj

        p1 = self.points[0]
        p2 = self.points[1]
        radius = distance(p1, p2)

        new_geo_el['solid'] = Point(p1).buffer((radius + self.buf_val / 2), int(self.steps_per_circ / 4))
        new_geo_el['follow'] = Point(p1).buffer((radius + self.buf_val / 2), int(self.steps_per_circ / 4)).exterior
        self.geometry = DrawToolShape(new_geo_el)

        self.draw_app.in_action = False
        self.complete = True

        self.draw_app.app.jump_signal.disconnect()

        self.draw_app.app.inform.emit('[success] %s' % _("Done."))

    def clean_up(self):
        self.draw_app.selected = []
        self.draw_app.apertures_table.clearSelection()
        self.draw_app.plot_all()
        try:
            self.draw_app.app.jump_signal.disconnect()
        except (TypeError, AttributeError):
            pass


class FCSemiDisc(FCShapeTool):
    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.name = 'semidisc'

        try:
            QtGui.QGuiApplication.restoreOverrideCursor()
        except Exception as e:
            log.debug("AppGerberEditor.FCSemiDisc --> %s" % str(e))

        self.cursor = QtGui.QCursor(QtGui.QPixmap(self.draw_app.app.resource_location + '/aero_semidisc.png'))
        QtGui.QGuiApplication.setOverrideCursor(self.cursor)

        self.draw_app.app.inform.emit(_("Click on Center point ..."))

        # Direction of rotation between point 1 and 2.
        # 'cw' or 'ccw'. Switch direction by hitting the
        # 'o' key.
        self.direction = "cw"

        # Mode
        # C12 = Center, p1, p2
        # 12C = p1, p2, Center
        # 132 = p1, p3, p2
        self.mode = "c12"  # Center, p1, p2

        size_ap = float(self.draw_app.storage_dict[self.draw_app.last_aperture_selected]['size'])
        self.buf_val = (size_ap / 2) if size_ap > 0 else 0.0000001

        if '0' in self.draw_app.storage_dict:
            self.storage_obj = self.draw_app.storage_dict['0']['geometry']
        else:
            self.draw_app.storage_dict['0'] = {}
            self.draw_app.storage_dict['0']['type'] = 'C'
            self.draw_app.storage_dict['0']['size'] = 0.0
            self.draw_app.storage_dict['0']['geometry'] = []
            self.storage_obj = self.draw_app.storage_dict['0']['geometry']

        self.steps_per_circ = self.draw_app.app.defaults["gerber_circle_steps"]
        self.draw_app.app.jump_signal.connect(lambda x: self.draw_app.update_utility_geometry(data=x))

    def click(self, point):
        self.points.append(point)

        if len(self.points) == 1:
            if self.mode == 'c12':
                self.draw_app.app.inform.emit(_("Click on Start point ..."))
            elif self.mode == '132':
                self.draw_app.app.inform.emit(_("Click on Point3 ..."))
            else:
                self.draw_app.app.inform.emit(_("Click on Stop point ..."))
            return "Click on 1st point ..."

        if len(self.points) == 2:
            if self.mode == 'c12':
                self.draw_app.app.inform.emit(_("Click on Stop point to complete ..."))
            elif self.mode == '132':
                self.draw_app.app.inform.emit(_("Click on Point2 to complete ..."))
            else:
                self.draw_app.app.inform.emit(_("Click on Center point to complete ..."))
            return "Click on 2nd point to complete ..."

        if len(self.points) == 3:
            self.make()
            return "Done."

        return ""

    def on_key(self, key):
        if key == 'D' or key == QtCore.Qt.Key_D:
            self.direction = 'cw' if self.direction == 'ccw' else 'ccw'
            return '%s: %s' % (_('Direction'), self.direction.upper())

        # Jump to coords
        if key == QtCore.Qt.Key_J or key == 'J':
            self.draw_app.app.on_jump_to()

        if key == 'M' or key == QtCore.Qt.Key_M:
            # delete the possible points made before this action; we want to start anew
            self.points = []
            # and delete the utility geometry made up until this point
            self.draw_app.delete_utility_geometry()

            if self.mode == 'c12':
                self.mode = '12c'
                return _('Mode: Start -> Stop -> Center. Click on Start point ...')
            elif self.mode == '12c':
                self.mode = '132'
                return _('Mode: Point1 -> Point3 -> Point2. Click on Point1 ...')
            else:
                self.mode = 'c12'
                return _('Mode: Center -> Start -> Stop. Click on Center point ...')

    def utility_geometry(self, data=None):
        new_geo_el = {}
        new_geo_el_pt1 = {}
        new_geo_el_pt2 = {}
        new_geo_el_pt3 = {}

        if len(self.points) == 1:  # Show the radius
            center = self.points[0]
            p1 = data
            new_geo_el['solid'] = LineString([center, p1])
            return DrawToolUtilityShape(new_geo_el)

        if len(self.points) == 2:  # Show the arc

            if self.mode == 'c12':
                center = self.points[0]
                p1 = self.points[1]
                p2 = data

                radius = np.sqrt((center[0] - p1[0]) ** 2 + (center[1] - p1[1]) ** 2) + (self.buf_val / 2)
                startangle = np.arctan2(p1[1] - center[1], p1[0] - center[0])
                stopangle = np.arctan2(p2[1] - center[1], p2[0] - center[0])

                new_geo_el['solid'] = LineString(
                    arc(center, radius, startangle, stopangle, self.direction, self.steps_per_circ))
                new_geo_el_pt1['solid'] = Point(center)
                return DrawToolUtilityShape([new_geo_el, new_geo_el_pt1])

            elif self.mode == '132':
                p1 = np.array(self.points[0])
                p3 = np.array(self.points[1])
                p2 = np.array(data)

                try:
                    center, radius, t = three_point_circle(p1, p2, p3)
                except TypeError:
                    return

                direction = 'cw' if np.sign(t) > 0 else 'ccw'
                radius += (self.buf_val / 2)

                startangle = np.arctan2(p1[1] - center[1], p1[0] - center[0])
                stopangle = np.arctan2(p3[1] - center[1], p3[0] - center[0])

                new_geo_el['solid'] = LineString(
                    arc(center, radius, startangle, stopangle, direction, self.steps_per_circ))
                new_geo_el_pt2['solid'] = Point(center)
                new_geo_el_pt1['solid'] = Point(p1)
                new_geo_el_pt3['solid'] = Point(p3)

                return DrawToolUtilityShape([new_geo_el, new_geo_el_pt2, new_geo_el_pt1, new_geo_el_pt3])

            else:  # '12c'
                p1 = np.array(self.points[0])
                p2 = np.array(self.points[1])
                # Midpoint
                a = (p1 + p2) / 2.0

                # Parallel vector
                c = p2 - p1

                # Perpendicular vector
                b = np.dot(c, np.array([[0, -1], [1, 0]], dtype=np.float32))
                b /= numpy_norm(b)

                # Distance
                t = distance(data, a)

                # Which side? Cross product with c.
                # cross(M-A, B-A), where line is AB and M is test point.
                side = (data[0] - p1[0]) * c[1] - (data[1] - p1[1]) * c[0]
                t *= np.sign(side)

                # Center = a + bt
                center = a + b * t

                radius = numpy_norm(center - p1) + (self.buf_val / 2)
                startangle = np.arctan2(p1[1] - center[1], p1[0] - center[0])
                stopangle = np.arctan2(p2[1] - center[1], p2[0] - center[0])

                new_geo_el['solid'] = LineString(
                    arc(center, radius, startangle, stopangle, self.direction, self.steps_per_circ))
                new_geo_el_pt2['solid'] = Point(center)

                return DrawToolUtilityShape([new_geo_el, new_geo_el_pt2])

        return None

    def make(self):
        self.draw_app.current_storage = self.storage_obj
        new_geo_el = {}

        if self.mode == 'c12':
            center = self.points[0]
            p1 = self.points[1]
            p2 = self.points[2]

            radius = distance(center, p1) + (self.buf_val / 2)
            start_angle = np.arctan2(p1[1] - center[1], p1[0] - center[0])
            stop_angle = np.arctan2(p2[1] - center[1], p2[0] - center[0])
            new_geo_el['solid'] = Polygon(
                arc(center, radius, start_angle, stop_angle, self.direction, self.steps_per_circ))
            new_geo_el['follow'] = Polygon(
                arc(center, radius, start_angle, stop_angle, self.direction, self.steps_per_circ)).exterior
            self.geometry = DrawToolShape(new_geo_el)

        elif self.mode == '132':
            p1 = np.array(self.points[0])
            p3 = np.array(self.points[1])
            p2 = np.array(self.points[2])

            center, radius, t = three_point_circle(p1, p2, p3)
            direction = 'cw' if np.sign(t) > 0 else 'ccw'
            radius += (self.buf_val / 2)

            start_angle = np.arctan2(p1[1] - center[1], p1[0] - center[0])
            stop_angle = np.arctan2(p3[1] - center[1], p3[0] - center[0])

            new_geo_el['solid'] = Polygon(arc(center, radius, start_angle, stop_angle, direction, self.steps_per_circ))
            new_geo_el['follow'] = Polygon(
                arc(center, radius, start_angle, stop_angle, direction, self.steps_per_circ)).exterior
            self.geometry = DrawToolShape(new_geo_el)

        else:  # self.mode == '12c'
            p1 = np.array(self.points[0])
            p2 = np.array(self.points[1])
            pc = np.array(self.points[2])

            # Midpoint
            a = (p1 + p2) / 2.0

            # Parallel vector
            c = p2 - p1

            # Perpendicular vector
            b = np.dot(c, np.array([[0, -1], [1, 0]], dtype=np.float32))
            b /= numpy_norm(b)

            # Distance
            t = distance(pc, a)

            # Which side? Cross product with c.
            # cross(M-A, B-A), where line is AB and M is test point.
            side = (pc[0] - p1[0]) * c[1] - (pc[1] - p1[1]) * c[0]
            t *= np.sign(side)

            # Center = a + bt
            center = a + b * t

            radius = numpy_norm(center - p1) + (self.buf_val / 2)
            start_angle = np.arctan2(p1[1] - center[1], p1[0] - center[0])
            stop_angle = np.arctan2(p2[1] - center[1], p2[0] - center[0])

            new_geo_el['solid'] = Polygon(
                arc(center, radius, start_angle, stop_angle, self.direction, self.steps_per_circ))
            new_geo_el['follow'] = Polygon(
                arc(center, radius, start_angle, stop_angle, self.direction, self.steps_per_circ)).exterior
            self.geometry = DrawToolShape(new_geo_el)

        self.draw_app.in_action = False
        self.complete = True

        self.draw_app.app.jump_signal.disconnect()

        self.draw_app.app.inform.emit('[success] %s' % _("Done."))

    def clean_up(self):
        self.draw_app.selected = []
        self.draw_app.apertures_table.clearSelection()
        self.draw_app.plot_all()
        try:
            self.draw_app.app.jump_signal.disconnect()
        except (TypeError, AttributeError):
            pass


class FCScale(FCShapeTool):
    def __init__(self, draw_app):
        FCShapeTool.__init__(self, draw_app)
        self.name = 'scale'

        # self.shape_buffer = self.draw_app.shape_buffer
        self.draw_app = draw_app
        self.app = draw_app.app

        self.draw_app.app.inform.emit(_("Scale the selected Gerber apertures ..."))
        self.origin = (0, 0)

        if self.draw_app.app.ui.splitter.sizes()[0] == 0:
            self.draw_app.app.ui.splitter.setSizes([1, 1])
        self.activate_scale()

    def activate_scale(self):
        self.draw_app.hide_tool('all')
        self.draw_app.scale_tool_frame.show()

        try:
            self.draw_app.scale_button.clicked.disconnect()
        except (TypeError, AttributeError):
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

    def clean_up(self):
        self.draw_app.selected = []
        self.draw_app.apertures_table.clearSelection()
        self.draw_app.plot_all()


class FCBuffer(FCShapeTool):
    def __init__(self, draw_app):
        FCShapeTool.__init__(self, draw_app)
        self.name = 'buffer'

        # self.shape_buffer = self.draw_app.shape_buffer
        self.draw_app = draw_app
        self.app = draw_app.app

        self.draw_app.app.inform.emit(_("Buffer the selected apertures ..."))
        self.origin = (0, 0)

        if self.draw_app.app.ui.splitter.sizes()[0] == 0:
            self.draw_app.app.ui.splitter.setSizes([1, 1])
        self.activate_buffer()

    def activate_buffer(self):
        self.draw_app.hide_tool('all')
        self.draw_app.buffer_tool_frame.show()

        try:
            self.draw_app.buffer_button.clicked.disconnect()
        except (TypeError, AttributeError):
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

    def clean_up(self):
        self.draw_app.selected = []
        self.draw_app.apertures_table.clearSelection()
        self.draw_app.plot_all()


class FCMarkArea(FCShapeTool):
    def __init__(self, draw_app):
        FCShapeTool.__init__(self, draw_app)
        self.name = 'markarea'

        # self.shape_buffer = self.draw_app.shape_buffer
        self.draw_app = draw_app
        self.app = draw_app.app

        self.draw_app.app.inform.emit(_("Mark polygon areas in the edited Gerber ..."))
        self.origin = (0, 0)

        if self.draw_app.app.ui.splitter.sizes()[0] == 0:
            self.draw_app.app.ui.splitter.setSizes([1, 1])
        self.activate_markarea()

    def activate_markarea(self):
        self.draw_app.ma_tool_frame.show()

        # clear previous marking
        self.draw_app.ma_annotation.clear(update=True)

        try:
            self.draw_app.ma_threshold_button.clicked.disconnect()
        except (TypeError, AttributeError):
            pass
        self.draw_app.ma_threshold_button.clicked.connect(self.on_markarea_click)

        try:
            self.draw_app.ma_delete_button.clicked.disconnect()
        except TypeError:
            pass
        self.draw_app.ma_delete_button.clicked.connect(self.on_markarea_delete)

        try:
            self.draw_app.ma_clear_button.clicked.disconnect()
        except TypeError:
            pass
        self.draw_app.ma_clear_button.clicked.connect(self.on_markarea_clear)

    def deactivate_markarea(self):
        self.draw_app.ma_threshold_button.clicked.disconnect()
        self.complete = True
        self.draw_app.select_tool("select")
        self.draw_app.hide_tool(self.name)

    def on_markarea_click(self):
        self.draw_app.on_markarea()

    def on_markarea_clear(self):
        self.draw_app.ma_annotation.clear(update=True)
        self.deactivate_markarea()

    def on_markarea_delete(self):
        self.draw_app.delete_marked_polygons()
        self.on_markarea_clear()

    def clean_up(self):
        self.draw_app.selected = []
        self.draw_app.apertures_table.clearSelection()
        self.draw_app.plot_all()


class FCApertureMove(FCShapeTool):
    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.name = 'move'

        # self.shape_buffer = self.draw_app.shape_buffer
        self.origin = None
        self.destination = None
        self.selected_apertures = []

        if len(self.draw_app.get_selected()) == 0:
            self.draw_app.app.inform.emit('[WARNING_NOTCL] %s...' %
                                          _("Nothing selected to move"))
            self.complete = True
            self.draw_app.select_tool("select")
            return

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

        self.draw_app.app.jump_signal.connect(lambda x: self.draw_app.update_utility_geometry(data=x))

        self.sel_limit = self.draw_app.app.defaults["gerber_editor_sel_limit"]
        self.selection_shape = self.selection_bbox()

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

    # def create_png(self):
    #     """
    #     Create a PNG file out of a list of Shapely polygons
    #     :return:
    #     """
    #     if len(self.draw_app.get_selected()) == 0:
    #         return None
    #
    #     geo_list = [geoms.geo for geoms in self.draw_app.get_selected()]
    #     xmin, ymin, xmax, ymax = get_shapely_list_bounds(geo_list)
    #
    #     iwidth = (xmax - xmin)
    #     iwidth = int(round(iwidth))
    #     iheight = (ymax - ymin)
    #     iheight = int(round(iheight))
    #     c = pngcanvas.PNGCanvas(iwidth, iheight)
    #
    #     pixels = []
    #     for geom in self.draw_app.get_selected():
    #         m = mapping(geom.geo.exterior)
    #         pixels += [[coord[0], coord[1]] for coord in m['coordinates']]
    #         for g in geom.geo.interiors:
    #             m = mapping(g)
    #             pixels += [[coord[0], coord[1]] for coord in m['coordinates']]
    #         c.polyline(pixels)
    #         pixels = []
    #
    #     f = open("%s.png" % 'D:\\shapely_image', "wb")
    #     f.write(c.dump())
    #     f.close()

    def selection_bbox(self):
        geo_list = []

        for select_shape in self.draw_app.get_selected():
            geometric_data = select_shape.geo
            geo_list.append(geometric_data['solid'])

        xmin, ymin, xmax, ymax = get_shapely_list_bounds(geo_list)

        pt1 = (xmin, ymin)
        pt2 = (xmax, ymin)
        pt3 = (xmax, ymax)
        pt4 = (xmin, ymax)

        return Polygon([pt1, pt2, pt3, pt4])

    def make(self):
        # Create new geometry
        dx = self.destination[0] - self.origin[0]
        dy = self.destination[1] - self.origin[1]
        sel_shapes_to_be_deleted = []

        for sel_dia in self.selected_apertures:
            self.current_storage = self.draw_app.storage_dict[sel_dia]['geometry']
            for select_shape in self.draw_app.get_selected():
                if select_shape in self.current_storage:
                    geometric_data = select_shape.geo
                    new_geo_el = {}
                    if 'solid' in geometric_data:
                        new_geo_el['solid'] = affinity.translate(geometric_data['solid'], xoff=dx, yoff=dy)
                    if 'follow' in geometric_data:
                        new_geo_el['follow'] = affinity.translate(geometric_data['follow'], xoff=dx, yoff=dy)
                    if 'clear' in geometric_data:
                        new_geo_el['clear'] = affinity.translate(geometric_data['clear'], xoff=dx, yoff=dy)

                    self.geometry.append(DrawToolShape(new_geo_el))
                    self.current_storage.remove(select_shape)
                    sel_shapes_to_be_deleted.append(select_shape)
                    self.draw_app.on_grb_shape_complete(self.current_storage, no_plot=True)
                    self.geometry = []

            for shp in sel_shapes_to_be_deleted:
                self.draw_app.selected.remove(shp)
            sel_shapes_to_be_deleted = []

        self.draw_app.plot_all()
        self.draw_app.build_ui()
        self.draw_app.app.inform.emit('[success] %s' % _("Done. Apertures Move completed."))
        self.draw_app.app.jump_signal.disconnect()

    def clean_up(self):
        self.draw_app.selected = []
        self.draw_app.apertures_table.clearSelection()
        self.draw_app.plot_all()

        try:
            self.draw_app.app.jump_signal.disconnect()
        except (TypeError, AttributeError):
            pass

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

        if len(self.draw_app.get_selected()) <= self.sel_limit:
            for geom in self.draw_app.get_selected():
                new_geo_el = {}
                if 'solid' in geom.geo:
                    new_geo_el['solid'] = affinity.translate(geom.geo['solid'], xoff=dx, yoff=dy)
                if 'follow' in geom.geo:
                    new_geo_el['follow'] = affinity.translate(geom.geo['follow'], xoff=dx, yoff=dy)
                if 'clear' in geom.geo:
                    new_geo_el['clear'] = affinity.translate(geom.geo['clear'], xoff=dx, yoff=dy)
                geo_list.append(deepcopy(new_geo_el))
            return DrawToolUtilityShape(geo_list)
        else:
            ss_el = {}
            ss_el['solid'] = affinity.translate(self.selection_shape, xoff=dx, yoff=dy)
            return DrawToolUtilityShape(ss_el)


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
            self.current_storage = self.draw_app.storage_dict[sel_dia]['geometry']
            for select_shape in self.draw_app.get_selected():
                if select_shape in self.current_storage:
                    geometric_data = select_shape.geo
                    new_geo_el = {}
                    if 'solid' in geometric_data:
                        new_geo_el['solid'] = affinity.translate(geometric_data['solid'], xoff=dx, yoff=dy)
                    if 'follow' in geometric_data:
                        new_geo_el['follow'] = affinity.translate(geometric_data['follow'], xoff=dx, yoff=dy)
                    if 'clear' in geometric_data:
                        new_geo_el['clear'] = affinity.translate(geometric_data['clear'], xoff=dx, yoff=dy)
                    self.geometry.append(DrawToolShape(new_geo_el))

                    sel_shapes_to_be_deleted.append(select_shape)
                    self.draw_app.on_grb_shape_complete(self.current_storage)
                    self.geometry = []

            for shp in sel_shapes_to_be_deleted:
                self.draw_app.selected.remove(shp)
            sel_shapes_to_be_deleted = []

        self.draw_app.build_ui()
        self.draw_app.app.inform.emit('[success] %s' % _("Done. Apertures copied."))
        self.draw_app.app.jump_signal.disconnect()


class FCEraser(FCShapeTool):
    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.name = 'eraser'

        self.origin = None
        self.destination = None
        self.selected_apertures = []

        if len(self.draw_app.get_selected()) == 0:
            if self.draw_app.launched_from_shortcuts is True:
                self.draw_app.launched_from_shortcuts = False
                self.draw_app.app.inform.emit(_("Select a shape to act as deletion area ..."))
        else:
            self.draw_app.app.inform.emit(_("Click to pick-up the erase shape..."))

        self.current_storage = None
        self.geometry = []

        for index in self.draw_app.apertures_table.selectedIndexes():
            row = index.row()
            # on column 1 in tool tables we hold the aperture codes, and we retrieve them as strings
            aperture_on_row = self.draw_app.apertures_table.item(row, 1).text()
            self.selected_apertures.append(aperture_on_row)

        # Switch notebook to Selected page
        self.draw_app.app.ui.notebook.setCurrentWidget(self.draw_app.app.ui.selected_tab)

        self.draw_app.app.jump_signal.connect(lambda x: self.draw_app.update_utility_geometry(data=x))

        self.sel_limit = self.draw_app.app.defaults["gerber_editor_sel_limit"]

    def set_origin(self, origin):
        self.origin = origin

    def click(self, point):
        if len(self.draw_app.get_selected()) == 0:
            self.draw_app.apertures_table.clearSelection()
            sel_aperture = set()

            for storage in self.draw_app.storage_dict:
                try:
                    for geo_el in self.draw_app.storage_dict[storage]['geometry']:
                        if 'solid' in geo_el.geo:
                            geometric_data = geo_el.geo['solid']
                            if Point(point).within(geometric_data):
                                self.draw_app.selected = []
                                self.draw_app.selected.append(geo_el)
                                sel_aperture.add(storage)
                except KeyError:
                    pass

            # select the aperture in the Apertures Table that is associated with the selected shape
            try:
                self.draw_app.apertures_table.cellPressed.disconnect()
            except Exception as e:
                log.debug("AppGerberEditor.FCEraser.click_release() --> %s" % str(e))

            self.draw_app.apertures_table.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
            for aper in sel_aperture:
                for row in range(self.draw_app.apertures_table.rowCount()):
                    if str(aper) == self.draw_app.apertures_table.item(row, 1).text():
                        self.draw_app.apertures_table.selectRow(row)
                        self.draw_app.last_aperture_selected = aper
            self.draw_app.apertures_table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

            self.draw_app.apertures_table.cellPressed.connect(self.draw_app.on_row_selected)

        if len(self.draw_app.get_selected()) == 0:
            return "Nothing to ersase."

        if self.origin is None:
            self.set_origin(point)
            self.draw_app.app.inform.emit(_("Click to erase ..."))
            return
        else:
            self.destination = point
            self.make()

            # self.draw_app.select_tool("select")
            return

    def make(self):
        eraser_sel_shapes = []

        # create the eraser shape from selection
        for eraser_shape in self.utility_geometry(data=self.destination).geo:
            temp_shape = eraser_shape['solid'].buffer(0.0000001)
            temp_shape = Polygon(temp_shape.exterior)
            eraser_sel_shapes.append(temp_shape)
        eraser_sel_shapes = cascaded_union(eraser_sel_shapes)

        for storage in self.draw_app.storage_dict:
            try:
                for geo_el in self.draw_app.storage_dict[storage]['geometry']:
                    if 'solid' in geo_el.geo:
                        geometric_data = geo_el.geo['solid']
                        if eraser_sel_shapes.within(geometric_data) or eraser_sel_shapes.intersects(geometric_data):
                            geos = geometric_data.difference(eraser_sel_shapes)
                            geos = geos.buffer(0)
                            geo_el.geo['solid'] = deepcopy(geos)
            except KeyError:
                pass

        self.draw_app.delete_utility_geometry()
        self.draw_app.plot_all()
        self.draw_app.app.inform.emit('[success] %s' % _("Done. Eraser tool action completed."))
        self.draw_app.app.jump_signal.disconnect()

    def clean_up(self):
        self.draw_app.selected = []
        self.draw_app.apertures_table.clearSelection()
        self.draw_app.plot_all()
        try:
            self.draw_app.app.jump_signal.disconnect()
        except (TypeError, AttributeError):
            pass

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
            new_geo_el = {}
            if 'solid' in geom.geo:
                new_geo_el['solid'] = affinity.translate(geom.geo['solid'], xoff=dx, yoff=dy)
            if 'follow' in geom.geo:
                new_geo_el['follow'] = affinity.translate(geom.geo['follow'], xoff=dx, yoff=dy)
            if 'clear' in geom.geo:
                new_geo_el['clear'] = affinity.translate(geom.geo['clear'], xoff=dx, yoff=dy)
            geo_list.append(deepcopy(new_geo_el))
        return DrawToolUtilityShape(geo_list)


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

        # since FCApertureSelect tool is activated whenever a tool is exited I place here the reinitialization of the
        # bending modes using in FCRegion and FCTrack
        self.grb_editor_app.bend_mode = 1

        # here store the selected apertures
        self.sel_aperture = []

        try:
            self.grb_editor_app.apertures_table.clearSelection()
        except Exception as e:
            log.error("FlatCAMGerbEditor.FCApertureSelect.__init__() --> %s" % str(e))

        self.grb_editor_app.hide_tool('all')
        self.grb_editor_app.hide_tool('select')
        self.grb_editor_app.array_frame.hide()

        try:
            QtGui.QGuiApplication.restoreOverrideCursor()
        except Exception as e:
            log.debug("AppGerberEditor.FCApertureSelect --> %s" % str(e))

    def set_origin(self, origin):
        self.origin = origin

    def click(self, point):
        key_modifier = QtWidgets.QApplication.keyboardModifiers()

        if key_modifier == QtCore.Qt.ShiftModifier:
            mod_key = 'Shift'
        elif key_modifier == QtCore.Qt.ControlModifier:
            mod_key = 'Control'
        else:
            mod_key = None

        if mod_key == self.grb_editor_app.app.defaults["global_mselect_key"]:
            pass
        else:
            self.grb_editor_app.selected = []

    def click_release(self, point):
        self.grb_editor_app.apertures_table.clearSelection()
        key_modifier = QtWidgets.QApplication.keyboardModifiers()

        if key_modifier == QtCore.Qt.ShiftModifier:
            mod_key = 'Shift'
        elif key_modifier == QtCore.Qt.ControlModifier:
            mod_key = 'Control'
        else:
            mod_key = None

        if mod_key != self.grb_editor_app.app.defaults["global_mselect_key"]:
            self.grb_editor_app.selected.clear()
            self.sel_aperture.clear()

        for storage in self.grb_editor_app.storage_dict:
            try:
                for shape_stored in self.grb_editor_app.storage_dict[storage]['geometry']:
                    if 'solid' in shape_stored.geo:
                        geometric_data = shape_stored.geo['solid']
                        if Point(point).within(geometric_data):
                            if shape_stored in self.grb_editor_app.selected:
                                self.grb_editor_app.selected.remove(shape_stored)
                            else:
                                # add the object to the selected shapes
                                self.grb_editor_app.selected.append(shape_stored)
            except KeyError:
                pass

        # select the aperture in the Apertures Table that is associated with the selected shape
        self.sel_aperture.clear()

        self.grb_editor_app.apertures_table.clearSelection()
        try:
            self.grb_editor_app.apertures_table.cellPressed.disconnect()
        except Exception as e:
            log.debug("AppGerberEditor.FCApertureSelect.click_release() --> %s" % str(e))

        for shape_s in self.grb_editor_app.selected:
            for storage in self.grb_editor_app.storage_dict:
                if shape_s in self.grb_editor_app.storage_dict[storage]['geometry']:
                    self.sel_aperture.append(storage)

        # self.grb_editor_app.apertures_table.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        for aper in self.sel_aperture:
            for row in range(self.grb_editor_app.apertures_table.rowCount()):
                if str(aper) == self.grb_editor_app.apertures_table.item(row, 1).text():
                    if not self.grb_editor_app.apertures_table.item(row, 0).isSelected():
                        self.grb_editor_app.apertures_table.selectRow(row)
                        self.grb_editor_app.last_aperture_selected = aper
        # self.grb_editor_app.apertures_table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        self.grb_editor_app.apertures_table.cellPressed.connect(self.grb_editor_app.on_row_selected)

        return ""

    def clean_up(self):
        self.grb_editor_app.plot_all()


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

    def clean_up(self):
        self.draw_app.selected = []
        self.draw_app.apertures_table.clearSelection()
        self.draw_app.plot_all()


class AppGerberEditor(QtCore.QObject):

    draw_shape_idx = -1
    # plot_finished = QtCore.pyqtSignal()
    mp_finished = QtCore.pyqtSignal(list)

    def __init__(self, app):
        # assert isinstance(app, FlatCAMApp.App), \
        #     "Expected the app to be a FlatCAMApp.App, got %s" % type(app)

        super(AppGerberEditor, self).__init__()

        self.app = app
        self.canvas = self.app.plotcanvas
        self.decimals = self.app.decimals

        # Current application units in Upper Case
        self.units = self.app.defaults['units'].upper()

        self.grb_edit_widget = QtWidgets.QWidget()

        layout = QtWidgets.QVBoxLayout()
        self.grb_edit_widget.setLayout(layout)

        # Page Title box (spacing between children)
        self.title_box = QtWidgets.QHBoxLayout()
        layout.addLayout(self.title_box)

        # Page Title icon
        pixmap = QtGui.QPixmap(self.app.resource_location + '/flatcam_icon32.png')
        self.icon = QtWidgets.QLabel()
        self.icon.setPixmap(pixmap)
        self.title_box.addWidget(self.icon, stretch=0)

        # Title label
        self.title_label = QtWidgets.QLabel("<font size=5><b>%s</b></font>" % _('Gerber Editor'))
        self.title_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.title_box.addWidget(self.title_label, stretch=1)

        # Object name
        self.name_box = QtWidgets.QHBoxLayout()
        layout.addLayout(self.name_box)
        name_label = QtWidgets.QLabel(_("Name:"))
        self.name_box.addWidget(name_label)
        self.name_entry = FCEntry()
        self.name_box.addWidget(self.name_entry)

        # Box for custom widgets
        # This gets populated in offspring implementations.
        self.custom_box = QtWidgets.QVBoxLayout()
        layout.addLayout(self.custom_box)

        # #########################
        # ### Gerber Apertures ####
        # #########################
        self.apertures_table_label = QtWidgets.QLabel('<b>%s:</b>' % _('Apertures'))
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
        self.apertures_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

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

        # # ## Add/Delete an new Aperture ## ##

        grid1 = QtWidgets.QGridLayout()
        self.apertures_box.addLayout(grid1)
        grid1.setColumnStretch(0, 0)
        grid1.setColumnStretch(1, 1)

        apcode_lbl = QtWidgets.QLabel('%s:' % _('Aperture Code'))
        apcode_lbl.setToolTip(_("Code for the new aperture"))
        grid1.addWidget(apcode_lbl, 1, 0)

        self.apcode_entry = FCSpinner()
        self.apcode_entry.set_range(0, 999)
        self.apcode_entry.setWrapping(True)

        grid1.addWidget(self.apcode_entry, 1, 1)

        apsize_lbl = QtWidgets.QLabel('%s:' % _('Aperture Size'))
        apsize_lbl.setToolTip(
            _("Size for the new aperture.\n"
              "If aperture type is 'R' or 'O' then\n"
              "this value is automatically\n"
              "calculated as:\n"
              "sqrt(width**2 + height**2)")
        )
        grid1.addWidget(apsize_lbl, 2, 0)

        self.apsize_entry = FCDoubleSpinner()
        self.apsize_entry.set_precision(self.decimals)
        self.apsize_entry.set_range(0.0, 9999)

        grid1.addWidget(self.apsize_entry, 2, 1)

        aptype_lbl = QtWidgets.QLabel('%s:' % _('Aperture Type'))
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

        self.apdim_lbl = QtWidgets.QLabel('%s:' % _('Aperture Dim'))
        self.apdim_lbl.setToolTip(
            _("Dimensions for the new aperture.\n"
              "Active only for rectangular apertures (type R).\n"
              "The format is (width, height)")
        )
        grid1.addWidget(self.apdim_lbl, 4, 0)

        self.apdim_entry = EvalEntry2()
        grid1.addWidget(self.apdim_entry, 4, 1)

        apadd_del_lbl = QtWidgets.QLabel('<b>%s:</b>' % _('Add/Delete Aperture'))
        apadd_del_lbl.setToolTip(
            _("Add/Delete an aperture in the aperture table")
        )
        self.apertures_box.addWidget(apadd_del_lbl)

        hlay_ad = QtWidgets.QHBoxLayout()
        self.apertures_box.addLayout(hlay_ad)

        self.addaperture_btn = QtWidgets.QPushButton(_('Add'))
        self.addaperture_btn.setToolTip(
           _("Add a new aperture to the aperture list.")
        )

        self.delaperture_btn = QtWidgets.QPushButton(_('Delete'))
        self.delaperture_btn.setToolTip(
           _("Delete a aperture in the aperture list")
        )
        hlay_ad.addWidget(self.addaperture_btn)
        hlay_ad.addWidget(self.delaperture_btn)

        # ###################
        # ### BUFFER TOOL ###
        # ###################
        self.buffer_tool_frame = QtWidgets.QFrame()
        self.buffer_tool_frame.setContentsMargins(0, 0, 0, 0)
        self.custom_box.addWidget(self.buffer_tool_frame)
        self.buffer_tools_box = QtWidgets.QVBoxLayout()
        self.buffer_tools_box.setContentsMargins(0, 0, 0, 0)
        self.buffer_tool_frame.setLayout(self.buffer_tools_box)
        self.buffer_tool_frame.hide()

        # Title
        buf_title_lbl = QtWidgets.QLabel('<b>%s:</b>' % _('Buffer Aperture'))
        buf_title_lbl.setToolTip(
            _("Buffer a aperture in the aperture list")
        )
        self.buffer_tools_box.addWidget(buf_title_lbl)

        # Form Layout
        buf_form_layout = QtWidgets.QFormLayout()
        self.buffer_tools_box.addLayout(buf_form_layout)

        # Buffer distance
        self.buffer_distance_entry = FCDoubleSpinner()
        self.buffer_distance_entry.set_precision(self.decimals)
        self.buffer_distance_entry.set_range(-9999.9999, 9999.9999)

        buf_form_layout.addRow('%s:' % _("Buffer distance"), self.buffer_distance_entry)
        self.buffer_corner_lbl = QtWidgets.QLabel('%s:' % _("Buffer corner"))
        self.buffer_corner_lbl.setToolTip(
            _("There are 3 types of corners:\n"
              " - 'Round': the corner is rounded.\n"
              " - 'Square': the corner is met in a sharp angle.\n"
              " - 'Beveled': the corner is a line that directly connects the features meeting in the corner")
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

        # ##################
        # ### SCALE TOOL ###
        # ##################
        self.scale_tool_frame = QtWidgets.QFrame()
        self.scale_tool_frame.setContentsMargins(0, 0, 0, 0)
        self.custom_box.addWidget(self.scale_tool_frame)
        self.scale_tools_box = QtWidgets.QVBoxLayout()
        self.scale_tools_box.setContentsMargins(0, 0, 0, 0)
        self.scale_tool_frame.setLayout(self.scale_tools_box)
        self.scale_tool_frame.hide()

        # Title
        scale_title_lbl = QtWidgets.QLabel('<b>%s:</b>' % _('Scale Aperture'))
        scale_title_lbl.setToolTip(
            _("Scale a aperture in the aperture list")
        )
        self.scale_tools_box.addWidget(scale_title_lbl)

        # Form Layout
        scale_form_layout = QtWidgets.QFormLayout()
        self.scale_tools_box.addLayout(scale_form_layout)

        self.scale_factor_lbl = QtWidgets.QLabel('%s:' % _("Scale factor"))
        self.scale_factor_lbl.setToolTip(
            _("The factor by which to scale the selected aperture.\n"
              "Values can be between 0.0000 and 999.9999")
        )
        self.scale_factor_entry = FCDoubleSpinner()
        self.scale_factor_entry.set_precision(self.decimals)
        self.scale_factor_entry.set_range(0.0000, 9999.9999)

        scale_form_layout.addRow(self.scale_factor_lbl, self.scale_factor_entry)

        # Buttons
        hlay_scale = QtWidgets.QHBoxLayout()
        self.scale_tools_box.addLayout(hlay_scale)

        self.scale_button = QtWidgets.QPushButton(_("Scale"))
        hlay_scale.addWidget(self.scale_button)

        # ######################
        # ### Mark Area TOOL ###
        # ######################
        self.ma_tool_frame = QtWidgets.QFrame()
        self.ma_tool_frame.setContentsMargins(0, 0, 0, 0)
        self.custom_box.addWidget(self.ma_tool_frame)
        self.ma_tools_box = QtWidgets.QVBoxLayout()
        self.ma_tools_box.setContentsMargins(0, 0, 0, 0)
        self.ma_tool_frame.setLayout(self.ma_tools_box)
        self.ma_tool_frame.hide()

        # Title
        ma_title_lbl = QtWidgets.QLabel('<b>%s:</b>' % _('Mark polygons'))
        ma_title_lbl.setToolTip(
            _("Mark the polygon areas.")
        )
        self.ma_tools_box.addWidget(ma_title_lbl)

        # Form Layout
        ma_form_layout = QtWidgets.QFormLayout()
        self.ma_tools_box.addLayout(ma_form_layout)

        self.ma_upper_threshold_lbl = QtWidgets.QLabel('%s:' % _("Area UPPER threshold"))
        self.ma_upper_threshold_lbl.setToolTip(
            _("The threshold value, all areas less than this are marked.\n"
              "Can have a value between 0.0000 and 9999.9999")
        )
        self.ma_upper_threshold_entry = FCDoubleSpinner()
        self.ma_upper_threshold_entry.set_precision(self.decimals)
        self.ma_upper_threshold_entry.set_range(0, 10000)

        self.ma_lower_threshold_lbl = QtWidgets.QLabel('%s:' % _("Area LOWER threshold"))
        self.ma_lower_threshold_lbl.setToolTip(
            _("The threshold value, all areas more than this are marked.\n"
              "Can have a value between 0.0000 and 9999.9999")
        )
        self.ma_lower_threshold_entry = FCDoubleSpinner()
        self.ma_lower_threshold_entry.set_precision(self.decimals)
        self.ma_lower_threshold_entry.set_range(0, 10000)

        ma_form_layout.addRow(self.ma_lower_threshold_lbl, self.ma_lower_threshold_entry)
        ma_form_layout.addRow(self.ma_upper_threshold_lbl, self.ma_upper_threshold_entry)

        # Buttons
        hlay_ma = QtWidgets.QHBoxLayout()
        self.ma_tools_box.addLayout(hlay_ma)

        self.ma_threshold_button = QtWidgets.QPushButton(_("Mark"))
        self.ma_threshold_button.setToolTip(
            _("Mark the polygons that fit within limits.")
        )
        hlay_ma.addWidget(self.ma_threshold_button)

        self.ma_delete_button = QtWidgets.QPushButton(_("Delete"))
        self.ma_delete_button.setToolTip(
            _("Delete all the marked polygons.")
        )
        hlay_ma.addWidget(self.ma_delete_button)

        self.ma_clear_button = QtWidgets.QPushButton(_("Clear"))
        self.ma_clear_button.setToolTip(
            _("Clear all the markings.")
        )
        hlay_ma.addWidget(self.ma_clear_button)

        # ######################
        # ### Add Pad Array ####
        # ######################
        # add a frame and inside add a vertical box layout. Inside this vbox layout I add
        # all the add Pad array  widgets
        # this way I can hide/show the frame
        self.array_frame = QtWidgets.QFrame()
        self.array_frame.setContentsMargins(0, 0, 0, 0)
        self.custom_box.addWidget(self.array_frame)
        self.array_box = QtWidgets.QVBoxLayout()
        self.array_box.setContentsMargins(0, 0, 0, 0)
        self.array_frame.setLayout(self.array_box)

        self.emptyarray_label = QtWidgets.QLabel('')
        self.array_box.addWidget(self.emptyarray_label)

        self.padarray_label = QtWidgets.QLabel('<b>%s</b>' % _("Add Pad Array"))
        self.padarray_label.setToolTip(
            _("Add an array of pads (linear or circular array)")
        )
        self.array_box.addWidget(self.padarray_label)

        self.array_type_combo = FCComboBox()
        self.array_type_combo.setToolTip(
           _("Select the type of pads array to create.\n"
             "It can be Linear X(Y) or Circular")
        )
        self.array_type_combo.addItem(_("Linear"))
        self.array_type_combo.addItem(_("Circular"))

        self.array_box.addWidget(self.array_type_combo)

        self.array_form = QtWidgets.QFormLayout()
        self.array_box.addLayout(self.array_form)

        self.pad_array_size_label = QtWidgets.QLabel('%s:' % _('Nr of pads'))
        self.pad_array_size_label.setToolTip(
            _("Specify how many pads to be in the array.")
        )
        self.pad_array_size_label.setMinimumWidth(100)

        self.pad_array_size_entry = FCSpinner()
        self.pad_array_size_entry.set_range(1, 9999)

        self.array_form.addRow(self.pad_array_size_label, self.pad_array_size_entry)

        self.array_linear_frame = QtWidgets.QFrame()
        self.array_linear_frame.setContentsMargins(0, 0, 0, 0)
        self.array_box.addWidget(self.array_linear_frame)
        self.linear_box = QtWidgets.QVBoxLayout()
        self.linear_box.setContentsMargins(0, 0, 0, 0)
        self.array_linear_frame.setLayout(self.linear_box)

        self.linear_form = QtWidgets.QFormLayout()
        self.linear_box.addLayout(self.linear_form)

        self.pad_axis_label = QtWidgets.QLabel('%s:' % _('Direction'))
        self.pad_axis_label.setToolTip(
            _("Direction on which the linear array is oriented:\n"
              "- 'X' - horizontal axis \n"
              "- 'Y' - vertical axis or \n"
              "- 'Angle' - a custom angle for the array inclination")
        )
        self.pad_axis_label.setMinimumWidth(100)

        self.pad_axis_radio = RadioSet([{'label': _('X'), 'value': 'X'},
                                        {'label': _('Y'), 'value': 'Y'},
                                        {'label': _('Angle'), 'value': 'A'}])
        self.pad_axis_radio.set_value('X')
        self.linear_form.addRow(self.pad_axis_label, self.pad_axis_radio)

        self.pad_pitch_label = QtWidgets.QLabel('%s:' % _('Pitch'))
        self.pad_pitch_label.setToolTip(
            _("Pitch = Distance between elements of the array.")
        )
        self.pad_pitch_label.setMinimumWidth(100)

        self.pad_pitch_entry = FCDoubleSpinner()
        self.pad_pitch_entry.set_precision(self.decimals)
        self.pad_pitch_entry.set_range(0.0000, 9999.9999)
        self.pad_pitch_entry.setSingleStep(0.1)

        self.linear_form.addRow(self.pad_pitch_label, self.pad_pitch_entry)

        self.linear_angle_label = QtWidgets.QLabel('%s:' % _('Angle'))
        self.linear_angle_label.setToolTip(
           _("Angle at which the linear array is placed.\n"
             "The precision is of max 2 decimals.\n"
             "Min value is: -359.99 degrees.\n"
             "Max value is:  360.00 degrees.")
        )
        self.linear_angle_label.setMinimumWidth(100)

        self.linear_angle_spinner = FCDoubleSpinner()
        self.linear_angle_spinner.set_precision(self.decimals)
        self.linear_angle_spinner.setRange(-360.00, 360.00)
        self.linear_form.addRow(self.linear_angle_label, self.linear_angle_spinner)

        self.array_circular_frame = QtWidgets.QFrame()
        self.array_circular_frame.setContentsMargins(0, 0, 0, 0)
        self.array_box.addWidget(self.array_circular_frame)
        self.circular_box = QtWidgets.QVBoxLayout()
        self.circular_box.setContentsMargins(0, 0, 0, 0)
        self.array_circular_frame.setLayout(self.circular_box)

        self.pad_direction_label = QtWidgets.QLabel('%s:' % _('Direction'))
        self.pad_direction_label.setToolTip(
           _("Direction for circular array."
             "Can be CW = clockwise or CCW = counter clockwise.")
        )
        self.pad_direction_label.setMinimumWidth(100)

        self.circular_form = QtWidgets.QFormLayout()
        self.circular_box.addLayout(self.circular_form)

        self.pad_direction_radio = RadioSet([{'label': _('CW'), 'value': 'CW'},
                                             {'label': _('CCW'), 'value': 'CCW'}])
        self.pad_direction_radio.set_value('CW')
        self.circular_form.addRow(self.pad_direction_label, self.pad_direction_radio)

        self.pad_angle_label = QtWidgets.QLabel('%s:' % _('Angle'))
        self.pad_angle_label.setToolTip(
            _("Angle at which each element in circular array is placed.")
        )
        self.pad_angle_label.setMinimumWidth(100)

        self.pad_angle_entry = FCDoubleSpinner()
        self.pad_angle_entry.set_precision(self.decimals)
        self.pad_angle_entry.set_range(-360.00, 360.00)
        self.pad_angle_entry.setSingleStep(0.1)

        self.circular_form.addRow(self.pad_angle_label, self.pad_angle_entry)

        self.array_circular_frame.hide()

        self.linear_angle_spinner.hide()
        self.linear_angle_label.hide()

        self.array_frame.hide()

        layout.addStretch()

        # Editor
        self.exit_editor_button = QtWidgets.QPushButton(_('Exit Editor'))
        self.exit_editor_button.setToolTip(
            _("Exit from Editor.")
        )
        self.exit_editor_button.setStyleSheet("""
                                      QPushButton
                                      {
                                          font-weight: bold;
                                      }
                                      """)
        layout.addWidget(self.exit_editor_button)

        self.exit_editor_button.clicked.connect(lambda: self.app.editor2object())

        # Toolbar events and properties
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
            "semidisc": {"button": self.app.ui.grb_add_semidisc_btn,
                         "constructor": FCSemiDisc},
            "disc": {"button": self.app.ui.grb_add_disc_btn,
                     "constructor": FCDisc},
            "buffer": {"button": self.app.ui.aperture_buffer_btn,
                       "constructor": FCBuffer},
            "scale": {"button": self.app.ui.aperture_scale_btn,
                      "constructor": FCScale},
            "markarea": {"button": self.app.ui.aperture_markarea_btn,
                         "constructor": FCMarkArea},
            "eraser": {"button": self.app.ui.aperture_eraser_btn,
                       "constructor": FCEraser},
            "copy": {"button": self.app.ui.aperture_copy_btn,
                     "constructor": FCApertureCopy},
            "transform": {"button": self.app.ui.grb_transform_btn,
                          "constructor": FCTransform},
            "move": {"button": self.app.ui.aperture_move_btn,
                     "constructor": FCApertureMove},
        }

        # # ## Data
        self.active_tool = None

        self.storage_dict = {}
        self.current_storage = []

        self.sorted_apcode = []

        self.new_apertures = {}
        self.new_aperture_macros = {}

        # store here the plot promises, if empty the delayed plot will be activated
        self.grb_plot_promises = []

        # dictionary to store the tool_row and aperture codes in Tool_table
        # it will be updated everytime self.build_ui() is called
        self.oldapcode_newapcode = {}

        self.tid2apcode = {}

        # this will store the value for the last selected tool, for use after clicking on canvas when the selection
        # is cleared but as a side effect also the selected tool is cleared
        self.last_aperture_selected = None
        self.utility = []

        # this will store the polygons marked by mark are to be perhaps deleted
        self.geo_to_delete = []

        # this will flag if the Editor "tools" are launched from key shortcuts (True) or from menu toolbar (False)
        self.launched_from_shortcuts = False

        # this var will store the state of the toolbar before starting the editor
        self.toolbar_old_state = False

        # Init appGUI
        self.apdim_lbl.hide()
        self.apdim_entry.hide()
        self.gerber_obj = None
        self.gerber_obj_options = {}

        # VisPy Visuals
        if self.app.is_legacy is False:
            self.shapes = self.canvas.new_shape_collection(layers=1)
            self.tool_shape = self.canvas.new_shape_collection(layers=1)
            self.ma_annotation = self.canvas.new_text_group()
        else:
            from appGUI.PlotCanvasLegacy import ShapeCollectionLegacy
            self.shapes = ShapeCollectionLegacy(obj=self, app=self.app, name='shapes_grb_editor')
            self.tool_shape = ShapeCollectionLegacy(obj=self, app=self.app, name='tool_shapes_grb_editor')
            self.ma_annotation = ShapeCollectionLegacy(
                obj=self,
                app=self.app,
                name='ma_anno_grb_editor',
                annotation_job=True)

        self.app.pool_recreated.connect(self.pool_recreated)

        # Event signals disconnect id holders
        self.mp = None
        self.mm = None
        self.mr = None

        # Remove from scene
        self.shapes.enabled = False
        self.tool_shape.enabled = False

        # List of selected geometric elements.
        self.selected = []

        self.key = None  # Currently pressed key
        self.modifiers = None
        self.x = None  # Current mouse cursor pos
        self.y = None
        # Current snapped mouse pos
        self.snap_x = None
        self.snap_y = None
        self.pos = None

        # used in FCRegion and FCTrack. Will store the bending mode
        self.bend_mode = 1

        # signal that there is an action active like polygon or path
        self.in_action = False
        # this will flag if the Editor "tools" are launched from key shortcuts (True) or from menu toolbar (False)
        self.launched_from_shortcuts = False

        def_tol_val = float(self.app.defaults["global_tolerance"])
        self.tolerance = def_tol_val if self.units == 'MM'else def_tol_val / 20

        def make_callback(the_tool):
            def f():
                self.on_tool_select(the_tool)
            return f

        for tool in self.tools_gerber:
            self.tools_gerber[tool]["button"].triggered.connect(make_callback(tool))  # Events
            self.tools_gerber[tool]["button"].setCheckable(True)

        self.options = {
            "global_gridx": 0.1,
            "global_gridy": 0.1,
            "snap_max": 0.05,
            "grid_snap": True,
            "corner_snap": False,
            "grid_gap_link": True
        }
        self.options.update(self.app.options)

        for option in self.options:
            if option in self.app.options:
                self.options[option] = self.app.options[option]

        # flag to show if the object was modified
        self.is_modified = False
        self.edited_obj_name = ""
        self.tool_row = 0

        # Multiprocessing pool
        self.pool = self.app.pool

        # Multiprocessing results
        self.results = []

        # A QTimer
        self.plot_thread = None

        # a QThread for the edit process
        self.thread = QtCore.QThread()

        # store the status of the editor so the Delete at object level will not work until the edit is finished
        self.editor_active = False

        # def entry2option(option, entry):
        #     self.options[option] = float(entry.text())

        self.transform_tool = TransformEditorTool(self.app, self)

        # Signals
        self.buffer_button.clicked.connect(self.on_buffer)
        self.scale_button.clicked.connect(self.on_scale)

        self.app.ui.aperture_delete_btn.triggered.connect(self.on_delete_btn)
        self.name_entry.returnPressed.connect(self.on_name_activate)

        self.aptype_cb.currentIndexChanged[str].connect(self.on_aptype_changed)

        self.addaperture_btn.clicked.connect(self.on_aperture_add)
        self.apsize_entry.returnPressed.connect(self.on_aperture_add)
        self.apdim_entry.returnPressed.connect(self.on_aperture_add)

        self.delaperture_btn.clicked.connect(self.on_aperture_delete)
        self.apertures_table.cellPressed.connect(self.on_row_selected)

        self.app.ui.grb_add_pad_menuitem.triggered.connect(self.on_pad_add)
        self.app.ui.grb_add_pad_array_menuitem.triggered.connect(self.on_pad_add_array)

        self.app.ui.grb_add_track_menuitem.triggered.connect(self.on_track_add)
        self.app.ui.grb_add_region_menuitem.triggered.connect(self.on_region_add)

        self.app.ui.grb_convert_poly_menuitem.triggered.connect(self.on_poligonize)
        self.app.ui.grb_add_semidisc_menuitem.triggered.connect(self.on_add_semidisc)
        self.app.ui.grb_add_disc_menuitem.triggered.connect(self.on_disc_add)
        self.app.ui.grb_add_buffer_menuitem.triggered.connect(self.on_buffer)
        self.app.ui.grb_add_scale_menuitem.triggered.connect(self.on_scale)
        self.app.ui.grb_add_eraser_menuitem.triggered.connect(self.on_eraser)
        self.app.ui.grb_add_markarea_menuitem.triggered.connect(self.on_markarea)

        self.app.ui.grb_transform_menuitem.triggered.connect(self.transform_tool.run)

        self.app.ui.grb_copy_menuitem.triggered.connect(self.on_copy_button)
        self.app.ui.grb_delete_menuitem.triggered.connect(self.on_delete_btn)

        self.app.ui.grb_move_menuitem.triggered.connect(self.on_move_button)

        self.array_type_combo.currentIndexChanged.connect(self.on_array_type_combo)
        self.pad_axis_radio.activated_custom.connect(self.on_linear_angle_radio)

        self.mp_finished.connect(self.on_multiprocessing_finished)

        # store the status of the editor so the Delete at object level will not work until the edit is finished
        self.editor_active = False

        self.conversion_factor = 1

        self.apertures_row = 0

        self.complete = True

        self.set_ui()
        log.debug("Initialization of the Gerber Editor is finished ...")

    def pool_recreated(self, pool):
        self.shapes.pool = pool
        self.tool_shape.pool = pool
        self.pool = pool

    def set_ui(self):
        # updated units
        self.units = self.app.defaults['units'].upper()
        self.decimals = self.app.decimals

        self.oldapcode_newapcode.clear()
        self.tid2apcode.clear()

        # update the oldapcode_newapcode dict to make sure we have an updated state of the tool_table
        for key in self.storage_dict:
            self.oldapcode_newapcode[key] = key

        sort_temp = []
        for aperture in self.oldapcode_newapcode:
            sort_temp.append(int(aperture))
        self.sorted_apcode = sorted(sort_temp)

        # populate self.intial_table_rows dict with the tool number as keys and aperture codes as values
        for i in range(len(self.sorted_apcode)):
            tt_aperture = self.sorted_apcode[i]
            self.tid2apcode[i + 1] = tt_aperture

        # Init appGUI

        self.buffer_distance_entry.set_value(self.app.defaults["gerber_editor_buff_f"])
        self.scale_factor_entry.set_value(self.app.defaults["gerber_editor_scale_f"])
        self.ma_upper_threshold_entry.set_value(self.app.defaults["gerber_editor_ma_high"])
        self.ma_lower_threshold_entry.set_value(self.app.defaults["gerber_editor_ma_low"])

        self.apsize_entry.set_value(self.app.defaults["gerber_editor_newsize"])
        self.aptype_cb.set_value(self.app.defaults["gerber_editor_newtype"])
        self.apdim_entry.set_value(self.app.defaults["gerber_editor_newdim"])

        self.pad_array_size_entry.set_value(int(self.app.defaults["gerber_editor_array_size"]))
        # linear array
        self.pad_axis_radio.set_value(self.app.defaults["gerber_editor_lin_axis"])
        self.pad_pitch_entry.set_value(float(self.app.defaults["gerber_editor_lin_pitch"]))
        self.linear_angle_spinner.set_value(self.app.defaults["gerber_editor_lin_angle"])
        # circular array
        self.pad_direction_radio.set_value(self.app.defaults["gerber_editor_circ_dir"])
        self.pad_angle_entry.set_value(float(self.app.defaults["gerber_editor_circ_angle"]))

    def build_ui(self, first_run=None):

        try:
            # if connected, disconnect the signal from the slot on item_changed as it creates issues
            self.apertures_table.itemChanged.disconnect()
        except (TypeError, AttributeError):
            pass

        try:
            self.apertures_table.cellPressed.disconnect()
        except (TypeError, AttributeError):
            pass

        # updated units
        self.units = self.app.defaults['units'].upper()

        # make a new name for the new Excellon object (the one with edited content)
        self.edited_obj_name = self.gerber_obj.options['name']
        self.name_entry.set_value(self.edited_obj_name)

        self.apertures_row = 0
        # aper_no = self.apertures_row + 1

        sort = []
        for k, v in list(self.storage_dict.items()):
            sort.append(int(k))

        sorted_apertures = sorted(sort)

        # sort = []
        # for k, v in list(self.gerber_obj.aperture_macros.items()):
        #     sort.append(k)
        # sorted_macros = sorted(sort)

        # n = len(sorted_apertures) + len(sorted_macros)
        n = len(sorted_apertures)
        self.apertures_table.setRowCount(n)

        for ap_code in sorted_apertures:
            ap_code = str(ap_code)

            ap_code_item = QtWidgets.QTableWidgetItem('%d' % int(self.apertures_row + 1))
            ap_code_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.apertures_table.setItem(self.apertures_row, 0, ap_code_item)  # Tool name/id

            ap_code_item = QtWidgets.QTableWidgetItem(ap_code)
            ap_code_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

            ap_type_item = QtWidgets.QTableWidgetItem(str(self.storage_dict[ap_code]['type']))
            ap_type_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

            if str(self.storage_dict[ap_code]['type']) == 'R' or str(self.storage_dict[ap_code]['type']) == 'O':
                ap_dim_item = QtWidgets.QTableWidgetItem(
                    '%.*f, %.*f' % (self.decimals, self.storage_dict[ap_code]['width'],
                                    self.decimals, self.storage_dict[ap_code]['height']
                                    )
                )
                ap_dim_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable)
            elif str(self.storage_dict[ap_code]['type']) == 'P':
                ap_dim_item = QtWidgets.QTableWidgetItem(
                    '%.*f, %.*f' % (self.decimals, self.storage_dict[ap_code]['diam'],
                                    self.decimals, self.storage_dict[ap_code]['nVertices'])
                )
                ap_dim_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable)
            else:
                ap_dim_item = QtWidgets.QTableWidgetItem('')
                ap_dim_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

            try:
                if self.storage_dict[ap_code]['size'] is not None:
                    ap_size_item = QtWidgets.QTableWidgetItem('%.*f' % (self.decimals,
                                                                        float(self.storage_dict[ap_code]['size'])))
                else:
                    ap_size_item = QtWidgets.QTableWidgetItem('')
            except KeyError:
                ap_size_item = QtWidgets.QTableWidgetItem('')

            if str(self.storage_dict[ap_code]['type']) == 'C':
                ap_size_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable)
            else:
                ap_size_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

            self.apertures_table.setItem(self.apertures_row, 1, ap_code_item)  # Aperture Code
            self.apertures_table.setItem(self.apertures_row, 2, ap_type_item)  # Aperture Type
            self.apertures_table.setItem(self.apertures_row, 3, ap_size_item)  # Aperture Size
            self.apertures_table.setItem(self.apertures_row, 4, ap_dim_item)  # Aperture Dimensions

            self.apertures_row += 1
            if first_run is True:
                # set now the last aperture selected
                self.last_aperture_selected = ap_code

        # for ap_code in sorted_macros:
        #     ap_code = str(ap_code)
        #
        #     ap_code_item = QtWidgets.QTableWidgetItem('%d' % int(self.apertures_row + 1))
        #     ap_code_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        #     self.apertures_table.setItem(self.apertures_row, 0, ap_code_item)  # Tool name/id
        #
        #     ap_code_item = QtWidgets.QTableWidgetItem(ap_code)
        #
        #     ap_type_item = QtWidgets.QTableWidgetItem('AM')
        #     ap_type_item.setFlags(QtCore.Qt.ItemIsEnabled)
        #
        #     self.apertures_table.setItem(self.apertures_row, 1, ap_code_item)  # Aperture Code
        #     self.apertures_table.setItem(self.apertures_row, 2, ap_type_item)  # Aperture Type
        #
        #     self.apertures_row += 1
        #     if first_run is True:
        #         # set now the last aperture selected
        #         self.last_aperture_selected = ap_code

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
        horizontal_header.resizeSection(0, 27)
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
        # Put ourselves in the GUI Selected Tab
        self.app.ui.selected_scroll_area.setWidget(self.grb_edit_widget)
        # Switch notebook to Selected page
        self.app.ui.notebook.setCurrentWidget(self.app.ui.selected_tab)

        # we reactivate the signals after the after the tool adding as we don't need to see the tool been populated
        self.apertures_table.itemChanged.connect(self.on_tool_edit)
        self.apertures_table.cellPressed.connect(self.on_row_selected)

        # for convenience set the next aperture code in the apcode field
        try:
            self.apcode_entry.set_value(max(self.tid2apcode.values()) + 1)
        except ValueError:
            # this means that the edited object has no apertures so we start with 10 (Gerber specifications)
            self.apcode_entry.set_value(self.app.defaults["gerber_editor_newcode"])

    def on_aperture_add(self, apcode=None):
        self.is_modified = True
        if apcode:
            ap_code = apcode
        else:
            try:
                ap_code = str(self.apcode_entry.get_value())
            except ValueError:
                self.app.inform.emit('[WARNING_NOTCL] %s' %
                                     _("Aperture code value is missing or wrong format. Add it and retry."))
                return
            if ap_code == '':
                self.app.inform.emit('[WARNING_NOTCL] %s' %
                                     _("Aperture code value is missing or wrong format. Add it and retry."))
                return

        if ap_code == '0':
            if ap_code not in self.tid2apcode:
                self.storage_dict[ap_code] = {}
                self.storage_dict[ap_code]['type'] = 'REG'
                size_val = 0
                self.apsize_entry.set_value(size_val)
                self.storage_dict[ap_code]['size'] = size_val

                self.storage_dict[ap_code]['geometry'] = []

                # self.oldapcode_newapcode dict keeps the evidence on current aperture codes as keys and
                # gets updated on values each time a aperture code is edited or added
                self.oldapcode_newapcode[ap_code] = ap_code
        else:
            if ap_code not in self.oldapcode_newapcode:
                self.storage_dict[ap_code] = {}

                type_val = self.aptype_cb.currentText()
                self.storage_dict[ap_code]['type'] = type_val

                if type_val == 'R' or type_val == 'O':
                    try:
                        dims = self.apdim_entry.get_value()
                        self.storage_dict[ap_code]['width'] = dims[0]
                        self.storage_dict[ap_code]['height'] = dims[1]

                        size_val = np.sqrt((dims[0] ** 2) + (dims[1] ** 2))
                        self.apsize_entry.set_value(size_val)

                    except Exception as e:
                        log.error("AppGerberEditor.on_aperture_add() --> the R or O aperture dims has to be in a "
                                  "tuple format (x,y)\nError: %s" % str(e))
                        self.app.inform.emit('[WARNING_NOTCL] %s' %
                                             _("Aperture dimensions value is missing or wrong format. "
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
                            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                                 _("Aperture size value is missing or wrong format. Add it and retry."))
                            return
                self.storage_dict[ap_code]['size'] = size_val

                self.storage_dict[ap_code]['geometry'] = []

                # self.oldapcode_newapcode dict keeps the evidence on current aperture codes as keys and gets updated on
                # values  each time a aperture code is edited or added
                self.oldapcode_newapcode[ap_code] = ap_code
            else:
                self.app.inform.emit('[WARNING_NOTCL] %s' %
                                     _("Aperture already in the aperture table."))
                return

        # since we add a new tool, we update also the initial state of the tool_table through it's dictionary
        # we add a new entry in the tid2apcode dict
        self.tid2apcode[len(self.oldapcode_newapcode)] = int(ap_code)

        self.app.inform.emit('[success] %s: %s' % (_("Added new aperture with code"), str(ap_code)))

        self.build_ui()

        self.last_aperture_selected = ap_code

        # make a quick sort through the tid2apcode dict so we find which row to select
        row_to_be_selected = None
        for key in sorted(self.tid2apcode):
            if self.tid2apcode[key] == int(ap_code):
                row_to_be_selected = int(key) - 1
                break
        self.apertures_table.selectRow(row_to_be_selected)

    def on_aperture_delete(self, ap_code=None):
        """
        Called for aperture deletion.

        :param ap_code:     An Aperture code; String
        :return:
        """
        self.is_modified = True

        try:
            if ap_code:
                try:
                    deleted_apcode_list = [dd for dd in ap_code]
                except TypeError:
                    deleted_apcode_list = [ap_code]
            else:
                # deleted_tool_dia = float(self.apertures_table.item(self.apertures_table.currentRow(), 1).text())
                if len(self.apertures_table.selectionModel().selectedRows()) == 0:
                    self.app.inform.emit('[WARNING_NOTCL] %s' % _(" Select an aperture in Aperture Table"))
                    return

                deleted_apcode_list = []
                for index in self.apertures_table.selectionModel().selectedRows():
                    row = index.row()
                    deleted_apcode_list.append(self.apertures_table.item(row, 1).text())
        except Exception as exc:
            self.app.inform.emit('[WARNING_NOTCL] %s %s' % (_("Select an aperture in Aperture Table -->", str(exc))))
            return

        if deleted_apcode_list:
            for deleted_aperture in deleted_apcode_list:
                # delete the storage used for that tool
                self.storage_dict.pop(deleted_aperture, None)

                for deleted_tool in list(self.tid2apcode.keys()):
                    if self.tid2apcode[deleted_tool] == deleted_aperture:
                        # delete the tool
                        self.tid2apcode.pop(deleted_tool, None)

                self.oldapcode_newapcode.pop(deleted_aperture, None)
                self.app.inform.emit('[success] %s: %s' % (_("Deleted aperture with code"), str(deleted_aperture)))

        self.plot_all()
        self.build_ui()

        # if last aperture selected was in the apertures deleted than make sure to select a
        # 'new' last aperture selected because there are tools who depend on it.
        # if there is no aperture left, then add a default one :)
        if self.last_aperture_selected in deleted_apcode_list:
            if self.apertures_table.rowCount() == 0:
                self.on_aperture_add('10')
                self.last_aperture_selected = '10'
            else:
                self.last_aperture_selected = self.apertures_table.item(0, 1).text()

    def on_tool_edit(self):
        if self.apertures_table.currentItem() is None:
            return

        # if connected, disconnect the signal from the slot on item_changed as it creates issues
        self.apertures_table.itemChanged.disconnect()
        # self.apertures_table.cellPressed.disconnect()

        self.is_modified = True
        val_edited = None

        row_of_item_changed = self.apertures_table.currentRow()
        col_of_item_changed = self.apertures_table.currentColumn()

        # rows start with 0, tools start with 1 so we adjust the value by 1
        key_in_tid2apcode = row_of_item_changed + 1
        ap_code_old = str(self.tid2apcode[key_in_tid2apcode])

        ap_code_new = self.apertures_table.item(row_of_item_changed, 1).text()

        if col_of_item_changed == 1:
            # we edited the Aperture Code column (int)
            try:
                val_edited = int(self.apertures_table.currentItem().text())
            except ValueError as e:
                log.debug("AppGerberEditor.on_tool_edit() --> %s" % str(e))
                # self.apertures_table.setCurrentItem(None)
                # we reactivate the signals after the after the tool editing
                self.apertures_table.itemChanged.connect(self.on_tool_edit)
                return
        elif col_of_item_changed == 3:
            # we edited the Size column (float)
            try:
                val_edited = float(self.apertures_table.currentItem().text())
            except ValueError as e:
                log.debug("AppGerberEditor.on_tool_edit() --> %s" % str(e))
                # self.apertures_table.setCurrentItem(None)
                # we reactivate the signals after the after the tool editing
                self.apertures_table.itemChanged.connect(self.on_tool_edit)
                return
        elif col_of_item_changed == 4:
            # we edit the Dimensions column (tuple)
            try:
                val_edited = [
                    float(x.strip()) for x in self.apertures_table.currentItem().text().split(",") if x != ''
                ]
            except ValueError as e:
                log.debug("AppGerberEditor.on_tool_edit() --> %s" % str(e))
                # we reactivate the signals after the after the tool editing
                self.apertures_table.itemChanged.connect(self.on_tool_edit)
                return

            if len(val_edited) != 2:
                self.app.inform.emit("[WARNING_NOTCL] %s" % _("Dimensions need two float values separated by comma."))
                old_dims_txt = '%s, %s' % (str(self.storage_dict[ap_code_new]['width']),
                                           str(self.storage_dict[ap_code_new]['height']))

                self.apertures_table.currentItem().setText(old_dims_txt)
                # we reactivate the signals after the after the tool editing
                self.apertures_table.itemChanged.connect(self.on_tool_edit)
                return
            else:
                self.app.inform.emit("[success] %s" % _("Dimensions edited."))

        # In case we edited the Aperture Code therefore the val_edited holds a new Aperture Code
        # TODO Edit of the Aperture Code is not active yet
        if col_of_item_changed == 1:
            # aperture code is not used so we create a new Aperture with the desired Aperture Code
            if val_edited not in self.oldapcode_newapcode.values():
                # update the dict that holds as keys old Aperture Codes and as values the new Aperture Codes
                self.oldapcode_newapcode[ap_code_old] = val_edited
                # update the dict that holds tool_no as key and tool_dia as value
                self.tid2apcode[key_in_tid2apcode] = val_edited

                old_aperture_val = self.storage_dict.pop(ap_code_old)
                self.storage_dict[val_edited] = old_aperture_val

            else:
                # aperture code is already in use so we move the pads from the prior tool to the new tool
                # but only if they are of the same type

                if self.storage_dict[ap_code_old]['type'] == self.storage_dict[ap_code_new]['type']:
                    # TODO I have to work here; if type == 'R' or 'O' have t otake care of all attributes ...
                    factor = val_edited / float(ap_code_old)
                    geometry = []
                    for geo_el in self.storage_dict[ap_code_old]:
                        geometric_data = geo_el.geo
                        new_geo_el = {}
                        if 'solid' in geometric_data:
                            new_geo_el['solid'] = deepcopy(affinity.scale(geometric_data['solid'],
                                                                          xfact=factor, yfact=factor))
                        if 'follow' in geometric_data:
                            new_geo_el['follow'] = deepcopy(affinity.scale(geometric_data['follow'],
                                                                           xfact=factor, yfact=factor))
                        if 'clear' in geometric_data:
                            new_geo_el['clear'] = deepcopy(affinity.scale(geometric_data['clear'],
                                                                          xfact=factor, yfact=factor))
                        geometry.append(new_geo_el)

                    self.add_gerber_shape(geometry, self.storage_dict[val_edited])

                    self.on_aperture_delete(apcode=ap_code_old)

        # In case we edited the Size of the Aperture therefore the val_edited holds the new Aperture Size
        # It will happen only for the Aperture Type == 'C' - I make sure of that in the self.build_ui()
        elif col_of_item_changed == 3:
            old_size = float(self.storage_dict[ap_code_old]['size'])
            new_size = float(val_edited)
            adjust_size = (new_size - old_size) / 2
            geometry = []
            for geo_el in self.storage_dict[ap_code_old]['geometry']:
                g_data = geo_el.geo
                new_geo_el = {}
                if 'solid' in g_data:
                    if 'follow' in g_data:
                        if isinstance(g_data['follow'], Point):
                            new_geo_el['solid'] = deepcopy(g_data['solid'].buffer(adjust_size))
                        else:
                            new_geo_el['solid'] = deepcopy(g_data['solid'].buffer(adjust_size, join_style=2))
                if 'follow' in g_data:
                    new_geo_el['follow'] = deepcopy(g_data['follow'])
                if 'clear' in g_data:
                    new_geo_el['clear'] = deepcopy(g_data['clear'].buffer(adjust_size, join_style=2))
                geometry.append(DrawToolShape(new_geo_el))

            self.storage_dict[ap_code_old]['geometry'].clear()
            self.add_gerber_shape(geometry, self.storage_dict[ap_code_old]['geometry'])
            # self.storage_dict[ap_code_old]['geometry'] = geometry

        # In case we edited the Dims of the Aperture therefore the val_edited holds a list with the dimensions
        # in the format [width, height]
        # It will happen only for the Aperture Type in ['R', 'O'] - I make sure of that in the self.build_ui()
        # and below
        elif col_of_item_changed == 4:
            if str(self.storage_dict[ap_code_old]['type']) == 'R' or str(self.storage_dict[ap_code_old]['type']) == 'O':
                # use the biggest from them
                buff_val_lines = max(val_edited)
                new_width = val_edited[0]
                new_height = val_edited[1]

                geometry = []
                for geo_el in self.storage_dict[ap_code_old]['geometry']:
                    g_data = geo_el.geo
                    new_geo_el = {}
                    if 'solid' in g_data:
                        if 'follow' in g_data:
                            if isinstance(g_data['follow'], Point):
                                x = g_data['follow'].x
                                y = g_data['follow'].y
                                minx = x - (new_width / 2)
                                miny = y - (new_height / 2)
                                maxx = x + (new_width / 2)
                                maxy = y + (new_height / 2)
                                geo = box(minx=minx, miny=miny, maxx=maxx, maxy=maxy)
                                new_geo_el['solid'] = deepcopy(geo)
                            else:
                                new_geo_el['solid'] = deepcopy(g_data['solid'].buffer(buff_val_lines))
                    if 'follow' in g_data:
                        new_geo_el['follow'] = deepcopy(g_data['follow'])
                    if 'clear' in g_data:
                        if 'follow' in g_data:
                            if isinstance(g_data['follow'], Point):
                                x = g_data['follow'].x
                                y = g_data['follow'].y
                                minx = x - (new_width / 2)
                                miny = y - (new_height / 2)
                                maxx = x + (new_width / 2)
                                maxy = y + (new_height / 2)
                                geo = box(minx=minx, miny=miny, maxx=maxx, maxy=maxy)
                                new_geo_el['clear'] = deepcopy(geo)
                            else:
                                new_geo_el['clear'] = deepcopy(g_data['clear'].buffer(buff_val_lines, join_style=2))
                    geometry.append(DrawToolShape(new_geo_el))

                self.storage_dict[ap_code_old]['geometry'].clear()
                self.add_gerber_shape(geometry, self.storage_dict[ap_code_old]['geometry'])

        self.plot_all()

        # we reactivate the signals after the after the tool editing
        self.apertures_table.itemChanged.connect(self.on_tool_edit)
        # self.apertures_table.cellPressed.connect(self.on_row_selected)

    def on_name_activate(self):
        self.edited_obj_name = self.name_entry.get_value()

    def on_aptype_changed(self, current_text):
        # 'O' is letter O not zero.
        if current_text == 'R' or current_text == 'O':
            self.apdim_lbl.show()
            self.apdim_entry.show()
            self.apsize_entry.setDisabled(True)
        else:
            self.apdim_lbl.hide()
            self.apdim_entry.hide()
            self.apsize_entry.setDisabled(False)

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
        self.sorted_apcode = []
        self.new_apertures = {}
        self.new_aperture_macros = {}
        self.grb_plot_promises = []
        self.oldapcode_newapcode = {}
        self.tid2apcode = {}

        self.shapes.enabled = True
        self.tool_shape.enabled = True

        self.app.ui.corner_snap_btn.setVisible(True)
        self.app.ui.snap_magnet.setVisible(True)

        self.app.ui.grb_editor_menu.setDisabled(False)
        self.app.ui.grb_editor_menu.menuAction().setVisible(True)

        self.app.ui.update_obj_btn.setEnabled(True)
        self.app.ui.grb_editor_cmenu.setEnabled(True)

        self.app.ui.grb_edit_toolbar.setDisabled(False)
        self.app.ui.grb_edit_toolbar.setVisible(True)
        # self.app.ui.grid_toolbar.setDisabled(False)

        # start with GRID toolbar activated
        if self.app.ui.grid_snap_btn.isChecked() is False:
            self.app.ui.grid_snap_btn.trigger()

        # adjust the visibility of some of the canvas context menu
        self.app.ui.popmenu_edit.setVisible(False)
        self.app.ui.popmenu_save.setVisible(True)

        self.app.ui.popmenu_disable.setVisible(False)
        self.app.ui.cmenu_newmenu.menuAction().setVisible(False)
        self.app.ui.popmenu_properties.setVisible(False)
        self.app.ui.grb_editor_cmenu.menuAction().setVisible(True)

        # Tell the App that the editor is active
        self.editor_active = True

    def deactivate_grb_editor(self):
        try:
            QtGui.QGuiApplication.restoreOverrideCursor()
        except Exception as e:
            log.debug("AppGerberEditor.deactivate_grb_editor() --> %s" % str(e))

        self.clear()

        # adjust the status of the menu entries related to the editor
        self.app.ui.menueditedit.setDisabled(False)
        self.app.ui.menueditok.setDisabled(True)
        # adjust the visibility of some of the canvas context menu
        self.app.ui.popmenu_edit.setVisible(True)
        self.app.ui.popmenu_save.setVisible(False)

        self.disconnect_canvas_event_handlers()
        self.app.ui.grb_edit_toolbar.setDisabled(True)

        self.app.ui.corner_snap_btn.setVisible(False)
        self.app.ui.snap_magnet.setVisible(False)

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

        # adjust the visibility of some of the canvas context menu
        self.app.ui.popmenu_edit.setVisible(True)
        self.app.ui.popmenu_save.setVisible(False)

        self.app.ui.popmenu_disable.setVisible(True)
        self.app.ui.cmenu_newmenu.menuAction().setVisible(True)
        self.app.ui.popmenu_properties.setVisible(True)
        self.app.ui.g_editor_cmenu.menuAction().setVisible(False)
        self.app.ui.e_editor_cmenu.menuAction().setVisible(False)
        self.app.ui.grb_editor_cmenu.menuAction().setVisible(False)

        # Show original geometry
        if self.gerber_obj:
            self.gerber_obj.visible = True

    def connect_canvas_event_handlers(self):
        # Canvas events

        # make sure that the shortcuts key and mouse events will no longer be linked to the methods from FlatCAMApp
        # but those from AppGeoEditor

        # first connect to new, then disconnect the old handlers
        # don't ask why but if there is nothing connected I've seen issues
        self.mp = self.canvas.graph_event_connect('mouse_press', self.on_canvas_click)
        self.mm = self.canvas.graph_event_connect('mouse_move', self.on_canvas_move)
        self.mr = self.canvas.graph_event_connect('mouse_release', self.on_grb_click_release)

        if self.app.is_legacy is False:
            self.canvas.graph_event_disconnect('mouse_press', self.app.on_mouse_click_over_plot)
            self.canvas.graph_event_disconnect('mouse_move', self.app.on_mouse_move_over_plot)
            self.canvas.graph_event_disconnect('mouse_release', self.app.on_mouse_click_release_over_plot)
            self.canvas.graph_event_disconnect('mouse_double_click', self.app.on_mouse_double_click_over_plot)
        else:
            self.canvas.graph_event_disconnect(self.app.mp)
            self.canvas.graph_event_disconnect(self.app.mm)
            self.canvas.graph_event_disconnect(self.app.mr)
            self.canvas.graph_event_disconnect(self.app.mdc)

        self.app.collection.view.clicked.disconnect()

        self.app.ui.popmenu_copy.triggered.disconnect()
        self.app.ui.popmenu_delete.triggered.disconnect()
        self.app.ui.popmenu_move.triggered.disconnect()

        self.app.ui.popmenu_copy.triggered.connect(self.on_copy_button)
        self.app.ui.popmenu_delete.triggered.connect(self.on_delete_btn)
        self.app.ui.popmenu_move.triggered.connect(self.on_move_button)

        # Gerber Editor
        self.app.ui.grb_draw_pad.triggered.connect(self.on_pad_add)
        self.app.ui.grb_draw_pad_array.triggered.connect(self.on_pad_add_array)
        self.app.ui.grb_draw_track.triggered.connect(self.on_track_add)
        self.app.ui.grb_draw_region.triggered.connect(self.on_region_add)

        self.app.ui.grb_draw_poligonize.triggered.connect(self.on_poligonize)
        self.app.ui.grb_draw_semidisc.triggered.connect(self.on_add_semidisc)
        self.app.ui.grb_draw_disc.triggered.connect(self.on_disc_add)
        self.app.ui.grb_draw_buffer.triggered.connect(lambda: self.select_tool("buffer"))
        self.app.ui.grb_draw_scale.triggered.connect(lambda: self.select_tool("scale"))
        self.app.ui.grb_draw_markarea.triggered.connect(lambda: self.select_tool("markarea"))
        self.app.ui.grb_draw_eraser.triggered.connect(self.on_eraser)
        self.app.ui.grb_draw_transformations.triggered.connect(self.on_transform)

    def disconnect_canvas_event_handlers(self):

        # we restore the key and mouse control to FlatCAMApp method
        # first connect to new, then disconnect the old handlers
        # don't ask why but if there is nothing connected I've seen issues
        self.app.mp = self.canvas.graph_event_connect('mouse_press', self.app.on_mouse_click_over_plot)
        self.app.mm = self.canvas.graph_event_connect('mouse_move', self.app.on_mouse_move_over_plot)
        self.app.mr = self.canvas.graph_event_connect('mouse_release', self.app.on_mouse_click_release_over_plot)
        self.app.mdc = self.canvas.graph_event_connect('mouse_double_click', self.app.on_mouse_double_click_over_plot)
        self.app.collection.view.clicked.connect(self.app.collection.on_mouse_down)

        if self.app.is_legacy is False:
            self.canvas.graph_event_disconnect('mouse_press', self.on_canvas_click)
            self.canvas.graph_event_disconnect('mouse_move', self.on_canvas_move)
            self.canvas.graph_event_disconnect('mouse_release', self.on_grb_click_release)
        else:
            self.canvas.graph_event_disconnect(self.mp)
            self.canvas.graph_event_disconnect(self.mm)
            self.canvas.graph_event_disconnect(self.mr)

        try:
            self.app.ui.popmenu_copy.triggered.disconnect(self.on_copy_button)
        except (TypeError, AttributeError):
            pass

        try:
            self.app.ui.popmenu_delete.triggered.disconnect(self.on_delete_btn)
        except (TypeError, AttributeError):
            pass

        try:
            self.app.ui.popmenu_move.triggered.disconnect(self.on_move_button)
        except (TypeError, AttributeError):
            pass

        self.app.ui.popmenu_copy.triggered.connect(self.app.on_copy_command)
        self.app.ui.popmenu_delete.triggered.connect(self.app.on_delete)
        self.app.ui.popmenu_move.triggered.connect(self.app.obj_move)

        # Gerber Editor

        try:
            self.app.ui.grb_draw_pad.triggered.disconnect(self.on_pad_add)
        except (TypeError, AttributeError):
            pass

        try:
            self.app.ui.grb_draw_pad_array.triggered.disconnect(self.on_pad_add_array)
        except (TypeError, AttributeError):
            pass

        try:
            self.app.ui.grb_draw_track.triggered.disconnect(self.on_track_add)
        except (TypeError, AttributeError):
            pass

        try:
            self.app.ui.grb_draw_region.triggered.disconnect(self.on_region_add)
        except (TypeError, AttributeError):
            pass

        try:
            self.app.ui.grb_draw_poligonize.triggered.disconnect(self.on_poligonize)
        except (TypeError, AttributeError):
            pass
        try:
            self.app.ui.grb_draw_semidisc.triggered.diconnect(self.on_add_semidisc)
        except (TypeError, AttributeError):
            pass
        try:
            self.app.ui.grb_draw_disc.triggered.disconnect(self.on_disc_add)
        except (TypeError, AttributeError):
            pass
        try:
            self.app.ui.grb_draw_buffer.triggered.disconnect()
        except (TypeError, AttributeError):
            pass
        try:
            self.app.ui.grb_draw_scale.triggered.disconnect()
        except (TypeError, AttributeError):
            pass
        try:
            self.app.ui.grb_draw_markarea.triggered.disconnect()
        except (TypeError, AttributeError):
            pass
        try:
            self.app.ui.grb_draw_eraser.triggered.disconnect(self.on_eraser)
        except (TypeError, AttributeError):
            pass
        try:
            self.app.ui.grb_draw_transformations.triggered.disconnect(self.on_transform)
        except (TypeError, AttributeError):
            pass

        try:
            self.app.jump_signal.disconnect()
        except (TypeError, AttributeError):
            pass

    def clear(self):
        self.thread.quit()

        self.active_tool = None
        self.selected = []
        self.storage_dict.clear()
        self.results.clear()

        self.shapes.clear(update=True)
        self.tool_shape.clear(update=True)
        self.ma_annotation.clear(update=True)

    def edit_fcgerber(self, orig_grb_obj):
        """
        Imports the geometry found in self.apertures from the given FlatCAM Gerber object
        into the editor.

        :param orig_grb_obj: ExcellonObject
        :return: None
        """

        self.deactivate_grb_editor()
        self.activate_grb_editor()

        # reset the tool table
        self.apertures_table.clear()

        self.apertures_table.setHorizontalHeaderLabels(['#', _('Code'), _('Type'), _('Size'), _('Dim')])
        self.last_aperture_selected = None

        # create a reference to the source object
        self.gerber_obj = orig_grb_obj
        self.gerber_obj_options = orig_grb_obj.options

        file_units = self.gerber_obj.units if self.gerber_obj.units else 'IN'
        app_units = self.app.defaults['units']
        # self.conversion_factor = 25.4 if file_units == 'IN' else (1 / 25.4) if file_units != app_units else 1

        if file_units == app_units:
            self.conversion_factor = 1
        else:
            if file_units == 'IN':
                self.conversion_factor = 25.4
            else:
                self.conversion_factor = 0.0393700787401575


        # Hide original geometry
        orig_grb_obj.visible = False

        # Set selection tolerance
        # DrawToolShape.tolerance = fc_excellon.drawing_tolerance * 10

        self.select_tool("select")

        try:
            # we activate this after the initial build as we don't need to see the tool been populated
            self.apertures_table.itemChanged.connect(self.on_tool_edit)
        except Exception as e:
            log.debug("AppGerberEditor.edit_fcgerber() --> %s" % str(e))

        # apply the conversion factor on the obj.apertures
        conv_apertures = deepcopy(self.gerber_obj.apertures)
        for apcode in self.gerber_obj.apertures:
            for key in self.gerber_obj.apertures[apcode]:
                if key == 'width':
                    conv_apertures[apcode]['width'] = self.gerber_obj.apertures[apcode]['width'] * \
                                                      self.conversion_factor
                elif key == 'height':
                    conv_apertures[apcode]['height'] = self.gerber_obj.apertures[apcode]['height'] * \
                                                       self.conversion_factor
                elif key == 'diam':
                    conv_apertures[apcode]['diam'] = self.gerber_obj.apertures[apcode]['diam'] * self.conversion_factor
                elif key == 'size':
                    conv_apertures[apcode]['size'] = self.gerber_obj.apertures[apcode]['size'] * self.conversion_factor
                else:
                    conv_apertures[apcode][key] = self.gerber_obj.apertures[apcode][key]

        self.gerber_obj.apertures = conv_apertures
        self.gerber_obj.units = app_units

        # # and then add it to the storage elements (each storage elements is a member of a list
        # def job_thread(aperture_id):
        #     with self.app.proc_container.new('%s: %s ...' %
        #                                      (_("Adding geometry for aperture"),  str(aperture_id))):
        #         storage_elem = []
        #         self.storage_dict[aperture_id] = {}
        #
        #         # add the Gerber geometry to editor storage
        #         for k, v in self.gerber_obj.apertures[aperture_id].items():
        #             try:
        #                 if k == 'geometry':
        #                     for geo_el in v:
        #                         if geo_el:
        #                             self.add_gerber_shape(DrawToolShape(geo_el), storage_elem)
        #                     self.storage_dict[aperture_id][k] = storage_elem
        #                 else:
        #                     self.storage_dict[aperture_id][k] = self.gerber_obj.apertures[aperture_id][k]
        #             except Exception as e:
        #                 log.debug("AppGerberEditor.edit_fcgerber().job_thread() --> %s" % str(e))
        #
        #         # Check promises and clear if exists
        #         while True:
        #             try:
        #                 self.grb_plot_promises.remove(aperture_id)
        #                 time.sleep(0.5)
        #             except ValueError:
        #                 break
        #
        # # we create a job work each aperture, job that work in a threaded way to store the geometry in local storage
        # # as DrawToolShapes
        # for ap_code in self.gerber_obj.apertures:
        #     self.grb_plot_promises.append(ap_code)
        #     self.app.worker_task.emit({'fcn': job_thread, 'params': [ap_code]})
        #
        # self.set_ui()
        #
        # # do the delayed plot only if there is something to plot (the gerber is not empty)
        # try:
        #     if bool(self.gerber_obj.apertures):
        #         self.start_delayed_plot(check_period=1000)
        #     else:
        #         raise AttributeError
        # except AttributeError:
        #     # now that we have data (empty data actually), create the GUI interface and add it to the Tool Tab
        #     self.build_ui(first_run=True)
        #     # and add the first aperture to have something to play with
        #     self.on_aperture_add('10')

        # self.app.worker_task.emit({'fcn': worker_job, 'params': [self]})

        class Execute_Edit(QtCore.QObject):

            start = QtCore.pyqtSignal(str)

            def __init__(self, app):
                super(Execute_Edit, self).__init__()
                self.app = app
                self.start.connect(self.run)

            @staticmethod
            def worker_job(app_obj):
                with app_obj.app.proc_container.new('%s ...' % _("Loading Gerber into Editor")):
                    # ###############################################################
                    # APPLY CLEAR_GEOMETRY on the SOLID_GEOMETRY
                    # ###############################################################

                    # list of clear geos that are to be applied to the entire file
                    global_clear_geo = []

                    # create one big geometry made out of all 'negative' (clear) polygons
                    for aper_id in app_obj.gerber_obj.apertures:
                        # first check if we have any clear_geometry (LPC) and if yes added it to the global_clear_geo
                        if 'geometry' in app_obj.gerber_obj.apertures[aper_id]:
                            for elem in app_obj.gerber_obj.apertures[aper_id]['geometry']:
                                if 'clear' in elem:
                                    global_clear_geo.append(elem['clear'])
                    log.warning("Found %d clear polygons." % len(global_clear_geo))

                    if global_clear_geo:
                        global_clear_geo = MultiPolygon(global_clear_geo)
                        if isinstance(global_clear_geo, Polygon):
                            global_clear_geo = [global_clear_geo]

                    # we subtract the big "negative" (clear) geometry from each solid polygon but only the part of
                    # clear geometry that fits inside the solid. otherwise we may loose the solid
                    for ap_code in app_obj.gerber_obj.apertures:
                        temp_solid_geometry = []
                        if 'geometry' in app_obj.gerber_obj.apertures[ap_code]:
                            # for elem in self.gerber_obj.apertures[apcode]['geometry']:
                            #     if 'solid' in elem:
                            #         solid_geo = elem['solid']
                            #         for clear_geo in global_clear_geo:
                            #             # Make sure that the clear_geo is within the solid_geo otherwise we loose
                            #             # the solid_geometry. We want for clear_geometry just to cut
                            #             # into solid_geometry not to delete it
                            #             if clear_geo.within(solid_geo):
                            #                 solid_geo = solid_geo.difference(clear_geo)
                            #         try:
                            #             for poly in solid_geo:
                            #                 new_elem = {}
                            #
                            #                 new_elem['solid'] = poly
                            #                 if 'clear' in elem:
                            #                     new_elem['clear'] = poly
                            #                 if 'follow' in elem:
                            #                     new_elem['follow'] = poly
                            #                 temp_elem.append(deepcopy(new_elem))
                            #         except TypeError:
                            #             new_elem = {}
                            #             new_elem['solid'] = solid_geo
                            #             if 'clear' in elem:
                            #                 new_elem['clear'] = solid_geo
                            #             if 'follow' in elem:
                            #                 new_elem['follow'] = solid_geo
                            #             temp_elem.append(deepcopy(new_elem))
                            for elem in app_obj.gerber_obj.apertures[ap_code]['geometry']:
                                new_elem = {}
                                if 'solid' in elem:
                                    solid_geo = elem['solid']
                                    if not global_clear_geo or global_clear_geo.is_empty:
                                        pass
                                    else:
                                        for clear_geo in global_clear_geo:
                                            # Make sure that the clear_geo is within the solid_geo otherwise we loose
                                            # the solid_geometry. We want for clear_geometry just to cut into
                                            # solid_geometry not to delete it
                                            if clear_geo.within(solid_geo):
                                                solid_geo = solid_geo.difference(clear_geo)

                                    new_elem['solid'] = solid_geo
                                if 'clear' in elem:
                                    new_elem['clear'] = elem['clear']
                                if 'follow' in elem:
                                    new_elem['follow'] = elem['follow']
                                temp_solid_geometry.append(deepcopy(new_elem))

                            app_obj.gerber_obj.apertures[ap_code]['geometry'] = deepcopy(temp_solid_geometry)

                    log.warning("Polygon difference done for %d apertures." % len(app_obj.gerber_obj.apertures))

                    try:
                        # Loading the Geometry into Editor Storage
                        for ap_code, ap_dict in app_obj.gerber_obj.apertures.items():
                            app_obj.results.append(
                                app_obj.pool.apply_async(app_obj.add_apertures, args=(ap_code, ap_dict))
                            )
                    except Exception as ee:
                        log.debug(
                            "AppGerberEditor.edit_fcgerber.worker_job() Adding processes to pool --> %s" % str(ee))
                        traceback.print_exc()

                    output = []
                    for p in app_obj.results:
                        output.append(p.get())

                    for elem in output:
                        app_obj.storage_dict[elem[0]] = deepcopy(elem[1])

                    app_obj.mp_finished.emit(output)

            def run(self):
                self.worker_job(self.app)

        self.thread.start(QtCore.QThread.NormalPriority)

        executable_edit = Execute_Edit(app=self)
        executable_edit.moveToThread(self.thread)
        executable_edit.start.emit("Started")

    @staticmethod
    def add_apertures(aperture_id, aperture_dict):
        storage_elem = []
        storage_dict = {}

        for k, v in list(aperture_dict.items()):
            try:
                if k == 'geometry':
                    for geo_el in v:
                        if geo_el:
                            storage_elem.append(DrawToolShape(geo_el))
                    storage_dict[k] = storage_elem
                else:
                    storage_dict[k] = aperture_dict[k]
            except Exception as e:
                log.debug("AppGerberEditor.edit_fcgerber().job_thread() --> %s" % str(e))

        return [aperture_id, storage_dict]

    def on_multiprocessing_finished(self):
        self.app.proc_container.update_view_text(' %s' % _("Setting up the UI"))
        self.app.inform.emit('[success] %s.' % _("Adding geometry finished. Preparing the GUI"))
        self.set_ui()
        self.build_ui(first_run=True)
        self.plot_all()

        # HACK: enabling/disabling the cursor seams to somehow update the shapes making them more 'solid'
        # - perhaps is a bug in VisPy implementation
        self.app.app_cursor.enabled = False
        self.app.app_cursor.enabled = True
        self.app.inform.emit('[success] %s' % _("Finished loading the Gerber object into the editor."))

    def update_fcgerber(self):
        """
        Create a new Gerber object that contain the edited content of the source Gerber object

        :return: None
        """
        new_grb_name = self.edited_obj_name

        # if the 'delayed plot' malfunctioned stop the QTimer
        try:
            self.plot_thread.stop()
        except Exception as e:
            log.debug("AppGerberEditor.update_fcgerber() --> %s" % str(e))

        if "_edit" in self.edited_obj_name:
            try:
                _id = int(self.edited_obj_name[-1]) + 1
                new_grb_name = self.edited_obj_name[:-1] + str(_id)
            except ValueError:
                new_grb_name += "_1"
        else:
            new_grb_name = self.edited_obj_name + "_edit"

        self.app.worker_task.emit({'fcn': self.new_edited_gerber, 'params': [new_grb_name, self.storage_dict]})
        # self.new_edited_gerber(new_grb_name, self.storage_dict)

    @staticmethod
    def update_options(obj):
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

    def new_edited_gerber(self, outname, aperture_storage):
        """
        Creates a new Gerber object for the edited Gerber. Thread-safe.

        :param outname:             Name of the resulting object. None causes the name to be that of the file.
        :type outname:              str
        :param aperture_storage:    a dictionary that holds all the objects geometry
        :type aperture_storage:     dict
        :return: None
        """

        self.app.log.debug("Update the Gerber object with edited content. Source is: %s" %
                           self.gerber_obj.options['name'].upper())

        out_name = outname
        storage_dict = aperture_storage

        local_storage_dict = {}
        for aperture in storage_dict:
            if 'geometry' in storage_dict[aperture]:
                # add aperture only if it has geometry
                if len(storage_dict[aperture]['geometry']) > 0:
                    local_storage_dict[aperture] = deepcopy(storage_dict[aperture])

        # How the object should be initialized
        def obj_init(grb_obj, app_obj):

            poly_buffer = []
            follow_buffer = []

            for storage_apcode, storage_val in local_storage_dict.items():
                grb_obj.apertures[storage_apcode] = {}

                for k, val in storage_val.items():
                    if k == 'geometry':
                        grb_obj.apertures[storage_apcode][k] = []
                        for geo_el in val:
                            geometric_data = geo_el.geo
                            new_geo_el = {}
                            if 'solid' in geometric_data:
                                new_geo_el['solid'] = geometric_data['solid']
                                poly_buffer.append(deepcopy(new_geo_el['solid']))

                            if 'follow' in geometric_data:
                                # if isinstance(geometric_data['follow'], Polygon):
                                #     buff_val = -(int(storage_val['size']) / 2)
                                #     geo_f = (geometric_data['follow'].buffer(buff_val)).exterior
                                #     new_geo_el['follow'] = geo_f
                                # else:
                                #     new_geo_el['follow'] = geometric_data['follow']
                                new_geo_el['follow'] = geometric_data['follow']
                                follow_buffer.append(deepcopy(new_geo_el['follow']))
                            else:
                                if 'solid' in geometric_data:
                                    geo_f = geometric_data['solid'].exterior
                                    new_geo_el['follow'] = geo_f
                                    follow_buffer.append(deepcopy(new_geo_el['follow']))

                            if 'clear' in geometric_data:
                                new_geo_el['clear'] = geometric_data['clear']

                            if new_geo_el:
                                grb_obj.apertures[storage_apcode][k].append(deepcopy(new_geo_el))
                    else:
                        grb_obj.apertures[storage_apcode][k] = val

            grb_obj.aperture_macros = deepcopy(self.gerber_obj.aperture_macros)

            new_poly = MultiPolygon(poly_buffer)
            new_poly = new_poly.buffer(0.00000001)
            new_poly = new_poly.buffer(-0.00000001)

            # for ad in grb_obj.apertures:
            #     print(ad, grb_obj.apertures[ad])

            try:
                __ = iter(new_poly)
            except TypeError:
                new_poly = [new_poly]

            grb_obj.solid_geometry = deepcopy(new_poly)
            grb_obj.follow_geometry = deepcopy(follow_buffer)

            for k, v in self.gerber_obj_options.items():
                if k == 'name':
                    grb_obj.options[k] = out_name
                else:
                    grb_obj.options[k] = deepcopy(v)

            grb_obj.multigeo = False
            grb_obj.follow = False
            grb_obj.units = app_obj.defaults['units']

            try:
                grb_obj.create_geometry()
            except KeyError:
                self.app.inform.emit('[ERROR_NOTCL] %s' %
                                     _("There are no Aperture definitions in the file. Aborting Gerber creation."))
            except Exception:
                msg = '[ERROR] %s' % _("An internal error has occurred. See shell.\n")
                msg += traceback.format_exc()
                app_obj.inform.emit(msg)
                raise

            grb_obj.source_file = self.app.export_gerber(obj_name=out_name, filename=None,
                                                         local_use=grb_obj, use_thread=False)

        with self.app.proc_container.new(_("Creating Gerber.")):
            try:
                self.app.app_obj.new_object("gerber", outname, obj_init)
            except Exception as e:
                log.error("Error on Edited object creation: %s" % str(e))
                # make sure to clean the previous results
                self.results = []
                return

            # make sure to clean the previous results
            self.results = []
            self.deactivate_grb_editor()
            self.app.inform.emit('[success] %s' % _("Done. Gerber editing finished."))

    def on_tool_select(self, tool):
        """
        Behavior of the toolbar. Tool initialization.

        :rtype : None
        """
        current_tool = tool

        self.app.log.debug("on_tool_select('%s')" % tool)

        if self.last_aperture_selected is None and current_tool != 'select':
            # self.draw_app.select_tool('select')
            self.complete = True
            current_tool = 'select'
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled. No aperture is selected"))

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
        # if col == 0:
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
            selected_ap_code = self.apertures_table.item(row, 1).text()
            self.last_aperture_selected = copy(selected_ap_code)

            for obj in self.storage_dict[selected_ap_code]['geometry']:
                self.selected.append(obj)
        except Exception as e:
            self.app.log.debug(str(e))

        self.plot_all()

    # def toolbar_tool_toggle(self, key):
    #     """
    #
    #     :param key: key to update in self.options dictionary
    #     :return:
    #     """
    #     self.options[key] = self.sender().isChecked()
    #     return self.options[key]

    def on_grb_shape_complete(self, storage=None, specific_shape=None, no_plot=False):
        """

        :param storage: where to store the shape
        :param specific_shape: optional, the shape to be stored
        :param no_plot: use this if you want the added shape not plotted
        :return:
        """
        self.app.log.debug("on_grb_shape_complete()")

        if specific_shape:
            geo = specific_shape
        else:
            geo = deepcopy(self.active_tool.geometry)
            if geo is None:
                return

        if storage is not None:
            # Add shape
            self.add_gerber_shape(geo, storage)
        else:
            stora = self.storage_dict[self.last_aperture_selected]['geometry']
            self.add_gerber_shape(geo, storage=stora)

        # Remove any utility shapes
        self.delete_utility_geometry()
        self.tool_shape.clear(update=True)

        if no_plot is False:
            # Re-plot and reset tool.
            self.plot_all()

    def add_gerber_shape(self, shape_element, storage):
        """
        Adds a shape to the shape storage.

        :param shape_element: Shape to be added.
        :type shape_element: DrawToolShape or DrawToolUtilityShape Geometry is stored as a dict with keys: solid,
        follow, clear, each value being a list of Shapely objects. The dict can have at least one of the mentioned keys
        :param storage: Where to store the shape
        :return: None
        """
        # List of DrawToolShape?

        if isinstance(shape_element, list):
            for subshape in shape_element:
                self.add_gerber_shape(subshape, storage)
            return

        assert isinstance(shape_element, DrawToolShape), \
            "Expected a DrawToolShape, got %s" % str(type(shape_element))

        assert shape_element.geo is not None, \
            "Shape object has empty geometry (None)"

        assert(isinstance(shape_element.geo, list) and len(shape_element.geo) > 0) or not \
            isinstance(shape_element.geo, list), "Shape objects has empty geometry ([])"

        if isinstance(shape_element, DrawToolUtilityShape):
            self.utility.append(shape_element)
        else:
            storage.append(shape_element)

    def on_canvas_click(self, event):
        """
        event.x and .y have canvas coordinates
        event.xdata and .ydata have plot coordinates

        :param event: Event object dispatched by VisPy
        :return: None
        """
        if self.app.is_legacy is False:
            event_pos = event.pos
            # event_is_dragging = event.is_dragging
            # right_button = 2
        else:
            event_pos = (event.xdata, event.ydata)
            # event_is_dragging = self.app.plotcanvas.is_dragging
            # right_button = 3

        self.pos = self.canvas.translate_coords(event_pos)

        if self.app.grid_status():
            self.pos = self.app.geo_editor.snap(self.pos[0], self.pos[1])
        else:
            self.pos = (self.pos[0], self.pos[1])

        if event.button == 1:
            self.app.ui.rel_position_label.setText("<b>Dx</b>: %.4f&nbsp;&nbsp;  <b>Dy</b>: "
                                                   "%.4f&nbsp;&nbsp;&nbsp;&nbsp;" % (0, 0))

            # Selection with left mouse button
            if self.active_tool is not None:
                modifiers = QtWidgets.QApplication.keyboardModifiers()

                # If the SHIFT key is pressed when LMB is clicked then the coordinates are copied to clipboard
                if modifiers == QtCore.Qt.ShiftModifier:
                    self.app.clipboard.setText(
                        self.app.defaults["global_point_clipboard_format"] %
                        (self.decimals, self.pos[0], self.decimals, self.pos[1])
                    )
                    self.app.inform.emit('[success] %s' % _("Coordinates copied to clipboard."))
                    return

                # Dispatch event to active_tool
                self.active_tool.click(self.app.geo_editor.snap(self.pos[0], self.pos[1]))

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
                        # return to Select tool but not for FCPad
                        if isinstance(self.active_tool, FCPad):
                            self.select_tool(self.active_tool.name)
                        else:
                            self.select_tool("select")
                        return

                if isinstance(self.active_tool, FCApertureSelect):
                    self.plot_all()
            else:
                self.app.log.debug("No active tool to respond to click!")

    def on_grb_click_release(self, event):
        self.modifiers = QtWidgets.QApplication.keyboardModifiers()
        if self.app.is_legacy is False:
            event_pos = event.pos
            # event_is_dragging = event.is_dragging
            right_button = 2
        else:
            event_pos = (event.xdata, event.ydata)
            # event_is_dragging = self.app.plotcanvas.is_dragging
            right_button = 3

        pos_canvas = self.canvas.translate_coords(event_pos)
        if self.app.grid_status():
            pos = self.app.geo_editor.snap(pos_canvas[0], pos_canvas[1])
        else:
            pos = (pos_canvas[0], pos_canvas[1])

        # if the released mouse button was RMB then test if it was a panning motion or not, if not it was a context
        # canvas menu
        try:
            if event.button == right_button:  # right click
                if self.app.ui.popMenu.mouse_is_panning is False:
                    if self.in_action is False:
                        try:
                            QtGui.QGuiApplication.restoreOverrideCursor()
                        except Exception as e:
                            log.debug("AppGerberEditor.on_grb_click_release() --> %s" % str(e))

                        if self.active_tool.complete is False and not isinstance(self.active_tool, FCApertureSelect):
                            self.active_tool.complete = True
                            self.in_action = False
                            self.delete_utility_geometry()
                            self.app.inform.emit('[success] %s' %
                                                 _("Done."))
                            self.select_tool('select')
                        else:
                            self.app.cursor = QtGui.QCursor()
                            self.app.populate_cmenu_grids()
                            self.app.ui.popMenu.popup(self.app.cursor.pos())
                    else:
                        # if right click on canvas and the active tool need to be finished (like Path or Polygon)
                        # right mouse click will finish the action
                        if isinstance(self.active_tool, FCShapeTool):
                            if isinstance(self.active_tool, FCTrack):
                                self.active_tool.make()
                            else:
                                self.active_tool.click(self.app.geo_editor.snap(self.x, self.y))
                                self.active_tool.make()
                            if self.active_tool.complete:
                                self.on_grb_shape_complete()
                                self.app.inform.emit('[success] %s' % _("Done."))

                                # MS: always return to the Select Tool if modifier key is not pressed
                                # else return to the current tool but not for FCTrack

                                if isinstance(self.active_tool, FCTrack):
                                    self.select_tool(self.active_tool.name)
                                else:
                                    key_modifier = QtWidgets.QApplication.keyboardModifiers()
                                    if (self.app.defaults["global_mselect_key"] == 'Control' and
                                        key_modifier == Qt.ControlModifier) or \
                                            (self.app.defaults["global_mselect_key"] == 'Shift' and
                                             key_modifier == Qt.ShiftModifier):

                                        self.select_tool(self.active_tool.name)
                                    else:
                                        self.select_tool("select")
        except Exception as e:
            log.warning("AppGerberEditor.on_grb_click_release() RMB click --> Error: %s" % str(e))
            raise

        # if the released mouse button was LMB then test if we had a right-to-left selection or a left-to-right
        # selection and then select a type of selection ("enclosing" or "touching")
        try:
            if event.button == 1:  # left click
                if self.app.selection_type is not None:
                    self.draw_selection_area_handler(self.pos, pos, self.app.selection_type)
                    self.app.selection_type = None

                elif isinstance(self.active_tool, FCApertureSelect):
                    self.active_tool.click_release((self.pos[0], self.pos[1]))

                    # if there are selected objects then plot them
                    if self.selected:
                        self.plot_all()
        except Exception as e:
            log.warning("AppGerberEditor.on_grb_click_release() LMB click --> Error: %s" % str(e))
            raise

    def draw_selection_area_handler(self, start_pos, end_pos, sel_type):
        """
        :param start_pos: mouse position when the selection LMB click was done
        :param end_pos: mouse position when the left mouse button is released
        :param sel_type: if True it's a left to right selection (enclosure), if False it's a 'touch' selection
        :return:
        """

        poly_selection = Polygon([start_pos, (end_pos[0], start_pos[1]), end_pos, (start_pos[0], end_pos[1])])
        sel_aperture = set()
        self.apertures_table.clearSelection()

        self.app.delete_selection_shape()
        for storage in self.storage_dict:
            for obj in self.storage_dict[storage]['geometry']:
                if 'solid' in obj.geo:
                    geometric_data = obj.geo['solid']
                    if (sel_type is True and poly_selection.contains(geometric_data)) or \
                            (sel_type is False and poly_selection.intersects(geometric_data)):
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
        except Exception as e:
            log.debug("AppGerberEditor.draw_selection_Area_handler() --> %s" % str(e))
        # select the aperture code of the selected geometry, in the tool table
        self.apertures_table.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        for aper in sel_aperture:
            for row_to_sel in range(self.apertures_table.rowCount()):
                if str(aper) == self.apertures_table.item(row_to_sel, 1).text():
                    if row_to_sel not in set(index.row() for index in self.apertures_table.selectedIndexes()):
                        self.apertures_table.selectRow(row_to_sel)
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
        if self.app.is_legacy is False:
            event_pos = event.pos
            event_is_dragging = event.is_dragging
            right_button = 2
        else:
            event_pos = (event.xdata, event.ydata)
            event_is_dragging = self.app.plotcanvas.is_dragging
            right_button = 3

        pos_canvas = self.canvas.translate_coords(event_pos)
        event.xdata, event.ydata = pos_canvas[0], pos_canvas[1]

        self.x = event.xdata
        self.y = event.ydata

        self.app.ui.popMenu.mouse_is_panning = False

        # if the RMB is clicked and mouse is moving over plot then 'panning_action' is True
        if event.button == right_button and event_is_dragging == 1:
            self.app.ui.popMenu.mouse_is_panning = True
            return

        try:
            x = float(event.xdata)
            y = float(event.ydata)
        except TypeError:
            return

        if self.active_tool is None:
            return

        # # ## Snap coordinates
        if self.app.grid_status():
            x, y = self.app.geo_editor.snap(x, y)

            # Update cursor
            self.app.app_cursor.set_data(np.asarray([(x, y)]), symbol='++', edge_color=self.app.cursor_color_3D,
                                         edge_width=self.app.defaults["global_cursor_width"],
                                         size=self.app.defaults["global_cursor_size"])

        self.snap_x = x
        self.snap_y = y

        self.app.mouse = [x, y]

        if self.pos is None:
            self.pos = (0, 0)
        self.app.dx = x - self.pos[0]
        self.app.dy = y - self.pos[1]

        # # update the position label in the infobar since the APP mouse event handlers are disconnected
        self.app.ui.position_label.setText("&nbsp;<b>X</b>: %.4f&nbsp;&nbsp;   "
                                           "<b>Y</b>: %.4f&nbsp;" % (x, y))

        # update the reference position label in the infobar since the APP mouse event handlers are disconnected
        self.app.ui.rel_position_label.setText("<b>Dx</b>: %.4f&nbsp;&nbsp;  <b>Dy</b>: "
                                               "%.4f&nbsp;&nbsp;&nbsp;&nbsp;" % (self.app.dx, self.app.dy))

        units = self.app.defaults["units"].lower()
        self.app.plotcanvas.text_hud.text = \
            'Dx:\t{:<.4f} [{:s}]\nDy:\t{:<.4f} [{:s}]\n\nX:  \t{:<.4f} [{:s}]\nY:  \t{:<.4f} [{:s}]'.format(
                self.app.dx, units, self.app.dy, units, x, units, y, units)

        self.update_utility_geometry(data=(x, y))

        # # ## Selection area on canvas section # ##
        if event_is_dragging == 1 and event.button == 1:
            # I make an exception for FCRegion and FCTrack because clicking and dragging while making regions can
            # create strange issues like missing a point in a track/region
            if isinstance(self.active_tool, FCRegion) or isinstance(self.active_tool, FCTrack):
                pass
            else:
                dx = pos_canvas[0] - self.pos[0]
                self.app.delete_selection_shape()
                if dx < 0:
                    self.app.draw_moving_selection_shape((self.pos[0], self.pos[1]), (x, y),
                                                         color=self.app.defaults["global_alt_sel_line"],
                                                         face_color=self.app.defaults['global_alt_sel_fill'])
                    self.app.selection_type = False
                else:
                    self.app.draw_moving_selection_shape((self.pos[0], self.pos[1]), (x, y))
                    self.app.selection_type = True
        else:
            self.app.selection_type = None

    def update_utility_geometry(self, data):
        # # ## Utility geometry (animated)
        geo = self.active_tool.utility_geometry(data=data)

        if isinstance(geo, DrawToolShape) and geo.geo is not None:
            # Remove any previous utility shape
            self.tool_shape.clear(update=True)
            self.draw_utility_geometry(geo=geo)

    def draw_utility_geometry(self, geo):
        if type(geo.geo) == list:
            for el in geo.geo:
                geometric_data = el['solid']
                # Add the new utility shape
                self.tool_shape.add(
                    shape=geometric_data, color=(self.app.defaults["global_draw_color"] + '80'),
                    # face_color=self.app.defaults['global_alt_sel_fill'],
                    update=False, layer=0, tolerance=None
                )
        else:
            geometric_data = geo.geo['solid']
            # Add the new utility shape
            self.tool_shape.add(
                shape=geometric_data,
                color=(self.app.defaults["global_draw_color"] + '80'),
                # face_color=self.app.defaults['global_alt_sel_fill'],
                update=False, layer=0, tolerance=None
            )

        self.tool_shape.redraw()

    def plot_all(self):
        """
        Plots all shapes in the editor.

        :return: None
        :rtype: None
        """
        with self.app.proc_container.new("Plotting"):
            self.shapes.clear(update=True)

            for storage in self.storage_dict:
                # fix for apertures with now geometry inside
                if 'geometry' in self.storage_dict[storage]:
                    for elem in self.storage_dict[storage]['geometry']:
                        if 'solid' in elem.geo:
                            geometric_data = elem.geo['solid']
                            if geometric_data is None:
                                continue

                            if elem in self.selected:
                                self.plot_shape(geometry=geometric_data,
                                                color=self.app.defaults['global_sel_draw_color'] + 'FF',
                                                linewidth=2)
                            else:
                                self.plot_shape(geometry=geometric_data,
                                                color=self.app.defaults['global_draw_color'] + 'FF')

            if self.utility:
                for elem in self.utility:
                    geometric_data = elem.geo['solid']
                    self.plot_shape(geometry=geometric_data, linewidth=1)
                    continue

            self.shapes.redraw()

    def plot_shape(self, geometry=None, color='#000000FF', linewidth=1):
        """
        Plots a geometric object or list of objects without rendering. Plotted objects
        are returned as a list. This allows for efficient/animated rendering.

        :param geometry:    Geometry to be plotted (Any Shapely.geom kind or list of such)
        :param color:       Shape color
        :param linewidth:   Width of lines in # of pixels.
        :return:            List of plotted elements.
        """

        if geometry is None:
            geometry = self.active_tool.geometry

        try:
            self.shapes.add(shape=geometry.geo, color=color, face_color=color, layer=0, tolerance=self.tolerance)
        except AttributeError:
            if type(geometry) == Point:
                return
            if len(color) == 9:
                color = color[:7] + 'AF'
            self.shapes.add(shape=geometry, color=color, face_color=color, layer=0, tolerance=self.tolerance)

    # def start_delayed_plot(self, check_period):
    #     """
    #     This function starts an QTImer and it will periodically check if all the workers finish the plotting functions
    #
    #     :param check_period: time at which to check periodically if all plots finished to be plotted
    #     :return:
    #     """
    #
    #     # self.plot_thread = threading.Thread(target=lambda: self.check_plot_finished(check_period))
    #     # self.plot_thread.start()
    #     log.debug("AppGerberEditor --> Delayed Plot started.")
    #     self.plot_thread = QtCore.QTimer()
    #     self.plot_thread.setInterval(check_period)
    #     self.plot_finished.connect(self.setup_ui_after_delayed_plot)
    #     self.plot_thread.timeout.connect(self.check_plot_finished)
    #     self.plot_thread.start()
    #
    # def check_plot_finished(self):
    #     """
    #     If all the promises made are finished then all the shapes are in shapes_storage and can be plotted safely and
    #     then the UI is rebuilt accordingly.
    #     :return:
    #     """
    #
    #     try:
    #         if not self.grb_plot_promises:
    #             self.plot_thread.stop()
    #             self.plot_finished.emit()
    #             log.debug("AppGerberEditor --> delayed_plot finished")
    #     except Exception as e:
    #         traceback.print_exc()
    #
    # def setup_ui_after_delayed_plot(self):
    #     self.plot_finished.disconnect()
    #
    #     # now that we have data, create the GUI interface and add it to the Tool Tab
    #     self.build_ui(first_run=True)
    #     self.plot_all()
    #
    #     # HACK: enabling/disabling the cursor seams to somehow update the shapes making them more 'solid'
    #     # - perhaps is a bug in VisPy implementation
    #     self.app.app_cursor.enabled = False
    #     self.app.app_cursor.enabled = True

    def on_zoom_fit(self):
        """
        Callback for zoom-fit request in Gerber Editor

        :return:        None
        """
        log.debug("AppGerberEditor.on_zoom_fit()")

        # calculate all the geometry in the edited Gerber object
        edit_geo = []
        for ap_code in self.storage_dict:
            for geo_el in self.storage_dict[ap_code]['geometry']:
                actual_geo = geo_el.geo
                if 'solid' in actual_geo:
                    edit_geo.append(actual_geo['solid'])

        all_geo = cascaded_union(edit_geo)

        # calculate the bounds values for the edited Gerber object
        xmin, ymin, xmax, ymax = all_geo.bounds

        if self.app.is_legacy is False:
            new_rect = Rect(xmin, ymin, xmax, ymax)
            self.app.plotcanvas.fit_view(rect=new_rect)
        else:
            width = xmax - xmin
            height = ymax - ymin
            xmin -= 0.05 * width
            xmax += 0.05 * width
            ymin -= 0.05 * height
            ymax += 0.05 * height
            self.app.plotcanvas.adjust_axes(xmin, ymin, xmax, ymax)

    def get_selected(self):
        """
        Returns list of shapes that are selected in the editor.

        :return: List of shapes.
        """
        # return [shape for shape in self.shape_buffer if shape["selected"]]
        return self.selected

    def delete_selected(self):
        temp_ref = [s for s in self.selected]

        if len(temp_ref) == 0:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Failed. No aperture geometry is selected."))
            return

        for shape_sel in temp_ref:
            self.delete_shape(shape_sel)

        self.selected = []
        self.build_ui()
        self.app.inform.emit('[success] %s' %
                             _("Done. Apertures geometry deleted."))

    def delete_shape(self, geo_el):
        self.is_modified = True

        if geo_el in self.utility:
            self.utility.remove(geo_el)
            return

        for storage in self.storage_dict:
            try:
                if geo_el in self.storage_dict[storage]['geometry']:
                    self.storage_dict[storage]['geometry'].remove(geo_el)
            except KeyError:
                pass
        if geo_el in self.selected:
            self.selected.remove(geo_el)  # TODO: Check performance

    def delete_utility_geometry(self):
        # for_deletion = [shape for shape in self.shape_buffer if shape.utility]
        # for_deletion = [shape for shape in self.storage.get_objects() if shape.utility]
        for_deletion = [geo_el for geo_el in self.utility]
        for geo_el in for_deletion:
            self.delete_shape(geo_el)

        self.tool_shape.clear(update=True)
        self.tool_shape.redraw()

    def on_delete_btn(self):
        self.delete_selected()
        self.plot_all()

    def select_tool(self, toolname):
        """
        Selects a drawing tool. Impacts the object and appGUI.

        :param toolname: Name of the tool.
        :return: None
        """
        self.tools_gerber[toolname]["button"].setChecked(True)
        self.on_tool_select(toolname)

    def set_selected(self, geo_el):

        # Remove and add to the end.
        if geo_el in self.selected:
            self.selected.remove(geo_el)

        self.selected.append(geo_el)

    def set_unselected(self, geo_el):
        if geo_el in self.selected:
            self.selected.remove(geo_el)

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

    def on_disc_add(self):
        self.select_tool('disc')

    def on_add_semidisc(self):
        self.select_tool('semidisc')

    def on_buffer(self):
        buff_value = 0.01
        log.debug("AppGerberEditor.on_buffer()")

        try:
            buff_value = float(self.buffer_distance_entry.get_value())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                buff_value = float(self.buffer_distance_entry.get_value().replace(',', '.'))
                self.buffer_distance_entry.set_value(buff_value)
            except ValueError:
                self.app.inform.emit('[WARNING_NOTCL] %s' %
                                     _("Buffer distance value is missing or wrong format. Add it and retry."))
                return
        # the cb index start from 0 but the join styles for the buffer start from 1 therefore the adjustment
        # I populated the combobox such that the index coincide with the join styles value (which is really an INT)
        join_style = self.buffer_corner_cb.currentIndex() + 1

        def buffer_recursion(geom_el, selection):
            if type(geom_el) == list:
                geoms = []
                for local_geom in geom_el:
                    geoms.append(buffer_recursion(local_geom, selection=selection))
                return geoms
            else:
                if geom_el in selection:
                    geometric_data = geom_el.geo
                    buffered_geom_el = {}
                    if 'solid' in geometric_data:
                        buffered_geom_el['solid'] = geometric_data['solid'].buffer(buff_value, join_style=join_style)
                    if 'follow' in geometric_data:
                        buffered_geom_el['follow'] = geometric_data['follow'].buffer(buff_value, join_style=join_style)
                    if 'clear' in geometric_data:
                        buffered_geom_el['clear'] = geometric_data['clear'].buffer(buff_value, join_style=join_style)
                    return DrawToolShape(buffered_geom_el)
                else:
                    return geom_el

        if not self.apertures_table.selectedItems():
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("No aperture to buffer. Select at least one aperture and try again."))
            return

        for x in self.apertures_table.selectedItems():
            try:
                apcode = self.apertures_table.item(x.row(), 1).text()

                temp_storage = deepcopy(buffer_recursion(self.storage_dict[apcode]['geometry'], self.selected))
                self.storage_dict[apcode]['geometry'] = []
                self.storage_dict[apcode]['geometry'] = temp_storage
            except Exception as e:
                log.debug("AppGerberEditor.buffer() --> %s" % str(e))
                self.app.inform.emit('[ERROR_NOTCL] %s\n%s' % (_("Failed."), str(traceback.print_exc())))
                return

        self.plot_all()
        self.app.inform.emit('[success] %s' % _("Done. Buffer Tool completed."))

    def on_scale(self):
        scale_factor = 1.0
        log.debug("AppGerberEditor.on_scale()")

        try:
            scale_factor = float(self.scale_factor_entry.get_value())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                scale_factor = float(self.scale_factor_entry.get_value().replace(',', '.'))
                self.scale_factor_entry.set_value(scale_factor)
            except ValueError:
                self.app.inform.emit('[WARNING_NOTCL] %s' %
                                     _("Scale factor value is missing or wrong format. Add it and retry."))
                return

        def scale_recursion(geom_el, selection):
            if type(geom_el) == list:
                geoms = []
                for local_geom in geom_el:
                    geoms.append(scale_recursion(local_geom, selection=selection))
                return geoms
            else:
                if geom_el in selection:
                    geometric_data = geom_el.geo
                    scaled_geom_el = {}
                    if 'solid' in geometric_data:
                        scaled_geom_el['solid'] = affinity.scale(
                            geometric_data['solid'], scale_factor, scale_factor, origin='center'
                        )
                    if 'follow' in geometric_data:
                        scaled_geom_el['follow'] = affinity.scale(
                            geometric_data['follow'], scale_factor, scale_factor, origin='center'
                        )
                    if 'clear' in geometric_data:
                        scaled_geom_el['clear'] = affinity.scale(
                            geometric_data['clear'], scale_factor, scale_factor, origin='center'
                        )

                    return DrawToolShape(scaled_geom_el)
                else:
                    return geom_el

        if not self.apertures_table.selectedItems():
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("No aperture to scale. Select at least one aperture and try again."))
            return

        for x in self.apertures_table.selectedItems():
            try:
                apcode = self.apertures_table.item(x.row(), 1).text()

                temp_storage = deepcopy(scale_recursion(self.storage_dict[apcode]['geometry'], self.selected))
                self.storage_dict[apcode]['geometry'] = []
                self.storage_dict[apcode]['geometry'] = temp_storage

            except Exception as e:
                log.debug("AppGerberEditor.on_scale() --> %s" % str(e))

        self.plot_all()
        self.app.inform.emit('[success] %s' %
                             _("Done. Scale Tool completed."))

    def on_markarea(self):
        # clear previous marking
        self.ma_annotation.clear(update=True)

        self.units = self.app.defaults['units'].upper()

        text = []
        position = []

        for apcode in self.storage_dict:
            if 'geometry' in self.storage_dict[apcode]:
                for geo_el in self.storage_dict[apcode]['geometry']:
                    if 'solid' in geo_el.geo:
                        area = geo_el.geo['solid'].area
                        try:
                            upper_threshold_val = self.ma_upper_threshold_entry.get_value()
                        except Exception:
                            return

                        try:
                            lower_threshold_val = self.ma_lower_threshold_entry.get_value()
                        except Exception:
                            lower_threshold_val = 0.0

                        if float(upper_threshold_val) > area > float(lower_threshold_val):
                            current_pos = geo_el.geo['solid'].exterior.coords[-1]
                            text_elem = '%.*f' % (self.decimals, area)
                            text.append(text_elem)
                            position.append(current_pos)
                            self.geo_to_delete.append(geo_el)

        if text:
            self.ma_annotation.set(text=text, pos=position, visible=True,
                                   font_size=self.app.defaults["cncjob_annotation_fontsize"],
                                   color='#000000FF')
            self.app.inform.emit('[success] %s' %
                                 _("Polygons marked."))
        else:
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("No polygons were marked. None fit within the limits."))

    def delete_marked_polygons(self):
        for shape_sel in self.geo_to_delete:
            self.delete_shape(shape_sel)

        self.build_ui()
        self.plot_all()
        self.app.inform.emit('[success] %s' % _("Done. Apertures geometry deleted."))

    def on_eraser(self):
        self.select_tool('eraser')

    def on_transform(self):
        if type(self.active_tool) == FCTransform:
            self.select_tool('select')
        else:
            self.select_tool('transform')

    def hide_tool(self, tool_name):
        # self.app.ui.notebook.setTabText(2, _("Tools"))
        try:
            if tool_name == 'all':
                self.apertures_frame.hide()
            if tool_name == 'select':
                self.apertures_frame.show()
            if tool_name == 'buffer' or tool_name == 'all':
                self.buffer_tool_frame.hide()
            if tool_name == 'scale' or tool_name == 'all':
                self.scale_tool_frame.hide()
            if tool_name == 'markarea' or tool_name == 'all':
                self.ma_tool_frame.hide()
        except Exception as e:
            log.debug("AppGerberEditor.hide_tool() --> %s" % str(e))
        self.app.ui.notebook.setCurrentWidget(self.app.ui.selected_tab)


class TransformEditorTool(AppTool):
    """
    Inputs to specify how to paint the selected polygons.
    """

    toolName = _("Transform Tool")
    rotateName = _("Rotate")
    skewName = _("Skew/Shear")
    scaleName = _("Scale")
    flipName = _("Mirror (Flip)")
    offsetName = _("Offset")
    bufferName = _("Buffer")

    def __init__(self, app, draw_app):
        AppTool.__init__(self, app)

        self.app = app
        self.draw_app = draw_app
        self.decimals = self.app.decimals

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
        self.layout.addWidget(QtWidgets.QLabel(''))

        # ## Layout
        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        grid0.setColumnStretch(2, 0)

        grid0.addWidget(QtWidgets.QLabel(''))

        # Reference
        ref_label = QtWidgets.QLabel('%s:' % _("Reference"))
        ref_label.setToolTip(
            _("The reference point for Rotate, Skew, Scale, Mirror.\n"
              "Can be:\n"
              "- Origin -> it is the 0, 0 point\n"
              "- Selection -> the center of the bounding box of the selected objects\n"
              "- Point -> a custom point defined by X,Y coordinates\n"
              "- Min Selection -> the point (minx, miny) of the bounding box of the selection")
        )
        self.ref_combo = FCComboBox()
        self.ref_items = [_("Origin"), _("Selection"), _("Point"), _("Minimum")]
        self.ref_combo.addItems(self.ref_items)

        grid0.addWidget(ref_label, 0, 0)
        grid0.addWidget(self.ref_combo, 0, 1, 1, 2)

        self.point_label = QtWidgets.QLabel('%s:' % _("Value"))
        self.point_label.setToolTip(
            _("A point of reference in format X,Y.")
        )
        self.point_entry = NumericalEvalTupleEntry()

        grid0.addWidget(self.point_label, 1, 0)
        grid0.addWidget(self.point_entry, 1, 1, 1, 2)

        self.point_button = FCButton(_("Add"))
        self.point_button.setToolTip(
            _("Add point coordinates from clipboard.")
        )
        grid0.addWidget(self.point_button, 2, 0, 1, 3)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 5, 0, 1, 3)

        # ## Rotate Title
        rotate_title_label = QtWidgets.QLabel("<font size=3><b>%s</b></font>" % self.rotateName)
        grid0.addWidget(rotate_title_label, 6, 0, 1, 3)

        self.rotate_label = QtWidgets.QLabel('%s:' % _("Angle"))
        self.rotate_label.setToolTip(
            _("Angle for Rotation action, in degrees.\n"
              "Float number between -360 and 359.\n"
              "Positive numbers for CW motion.\n"
              "Negative numbers for CCW motion.")
        )

        self.rotate_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.rotate_entry.set_precision(self.decimals)
        self.rotate_entry.setSingleStep(45)
        self.rotate_entry.setWrapping(True)
        self.rotate_entry.set_range(-360, 360)

        # self.rotate_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.rotate_button = FCButton(_("Rotate"))
        self.rotate_button.setToolTip(
            _("Rotate the selected object(s).\n"
              "The point of reference is the middle of\n"
              "the bounding box for all selected objects.")
        )
        self.rotate_button.setMinimumWidth(90)

        grid0.addWidget(self.rotate_label, 7, 0)
        grid0.addWidget(self.rotate_entry, 7, 1)
        grid0.addWidget(self.rotate_button, 7, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 8, 0, 1, 3)

        # ## Skew Title
        skew_title_label = QtWidgets.QLabel("<font size=3><b>%s</b></font>" % self.skewName)
        grid0.addWidget(skew_title_label, 9, 0, 1, 2)

        self.skew_link_cb = FCCheckBox()
        self.skew_link_cb.setText(_("Link"))
        self.skew_link_cb.setToolTip(
            _("Link the Y entry to X entry and copy its content.")
        )

        grid0.addWidget(self.skew_link_cb, 9, 2)

        self.skewx_label = QtWidgets.QLabel('%s:' % _("X angle"))
        self.skewx_label.setToolTip(
            _("Angle for Skew action, in degrees.\n"
              "Float number between -360 and 360.")
        )
        self.skewx_entry = FCDoubleSpinner(callback=self.confirmation_message)
        # self.skewx_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.skewx_entry.set_precision(self.decimals)
        self.skewx_entry.set_range(-360, 360)

        self.skewx_button = FCButton(_("Skew X"))
        self.skewx_button.setToolTip(
            _("Skew/shear the selected object(s).\n"
              "The point of reference is the middle of\n"
              "the bounding box for all selected objects."))
        self.skewx_button.setMinimumWidth(90)

        grid0.addWidget(self.skewx_label, 10, 0)
        grid0.addWidget(self.skewx_entry, 10, 1)
        grid0.addWidget(self.skewx_button, 10, 2)

        self.skewy_label = QtWidgets.QLabel('%s:' % _("Y angle"))
        self.skewy_label.setToolTip(
            _("Angle for Skew action, in degrees.\n"
              "Float number between -360 and 360.")
        )
        self.skewy_entry = FCDoubleSpinner(callback=self.confirmation_message)
        # self.skewy_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.skewy_entry.set_precision(self.decimals)
        self.skewy_entry.set_range(-360, 360)

        self.skewy_button = FCButton(_("Skew Y"))
        self.skewy_button.setToolTip(
            _("Skew/shear the selected object(s).\n"
              "The point of reference is the middle of\n"
              "the bounding box for all selected objects."))
        self.skewy_button.setMinimumWidth(90)

        grid0.addWidget(self.skewy_label, 12, 0)
        grid0.addWidget(self.skewy_entry, 12, 1)
        grid0.addWidget(self.skewy_button, 12, 2)

        self.ois_sk = OptionalInputSection(self.skew_link_cb, [self.skewy_label, self.skewy_entry, self.skewy_button],
                                           logic=False)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 14, 0, 1, 3)

        # ## Scale Title
        scale_title_label = QtWidgets.QLabel("<font size=3><b>%s</b></font>" % self.scaleName)
        grid0.addWidget(scale_title_label, 15, 0, 1, 2)

        self.scale_link_cb = FCCheckBox()
        self.scale_link_cb.setText(_("Link"))
        self.scale_link_cb.setToolTip(
            _("Link the Y entry to X entry and copy its content.")
        )

        grid0.addWidget(self.scale_link_cb, 15, 2)

        self.scalex_label = QtWidgets.QLabel('%s:' % _("X factor"))
        self.scalex_label.setToolTip(
            _("Factor for scaling on X axis.")
        )
        self.scalex_entry = FCDoubleSpinner(callback=self.confirmation_message)
        # self.scalex_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.scalex_entry.set_precision(self.decimals)
        self.scalex_entry.setMinimum(-1e6)

        self.scalex_button = FCButton(_("Scale X"))
        self.scalex_button.setToolTip(
            _("Scale the selected object(s).\n"
              "The point of reference depends on \n"
              "the Scale reference checkbox state."))
        self.scalex_button.setMinimumWidth(90)

        grid0.addWidget(self.scalex_label, 17, 0)
        grid0.addWidget(self.scalex_entry, 17, 1)
        grid0.addWidget(self.scalex_button, 17, 2)

        self.scaley_label = QtWidgets.QLabel('%s:' % _("Y factor"))
        self.scaley_label.setToolTip(
            _("Factor for scaling on Y axis.")
        )
        self.scaley_entry = FCDoubleSpinner(callback=self.confirmation_message)
        # self.scaley_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.scaley_entry.set_precision(self.decimals)
        self.scaley_entry.setMinimum(-1e6)

        self.scaley_button = FCButton(_("Scale Y"))
        self.scaley_button.setToolTip(
            _("Scale the selected object(s).\n"
              "The point of reference depends on \n"
              "the Scale reference checkbox state."))
        self.scaley_button.setMinimumWidth(90)

        grid0.addWidget(self.scaley_label, 19, 0)
        grid0.addWidget(self.scaley_entry, 19, 1)
        grid0.addWidget(self.scaley_button, 19, 2)

        self.ois_s = OptionalInputSection(self.scale_link_cb,
                                          [
                                              self.scaley_label,
                                              self.scaley_entry,
                                              self.scaley_button
                                          ], logic=False)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 21, 0, 1, 3)

        # ## Flip Title
        flip_title_label = QtWidgets.QLabel("<font size=3><b>%s</b></font>" % self.flipName)
        grid0.addWidget(flip_title_label, 23, 0, 1, 3)

        self.flipx_button = FCButton(_("Flip on X"))
        self.flipx_button.setToolTip(
            _("Flip the selected object(s) over the X axis.")
        )

        self.flipy_button = FCButton(_("Flip on Y"))
        self.flipy_button.setToolTip(
            _("Flip the selected object(s) over the X axis.")
        )

        hlay0 = QtWidgets.QHBoxLayout()
        grid0.addLayout(hlay0, 25, 0, 1, 3)

        hlay0.addWidget(self.flipx_button)
        hlay0.addWidget(self.flipy_button)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 27, 0, 1, 3)

        # ## Offset Title
        offset_title_label = QtWidgets.QLabel("<font size=3><b>%s</b></font>" % self.offsetName)
        grid0.addWidget(offset_title_label, 29, 0, 1, 3)

        self.offx_label = QtWidgets.QLabel('%s:' % _("X val"))
        self.offx_label.setToolTip(
            _("Distance to offset on X axis. In current units.")
        )
        self.offx_entry = FCDoubleSpinner(callback=self.confirmation_message)
        # self.offx_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.offx_entry.set_precision(self.decimals)
        self.offx_entry.setMinimum(-1e6)

        self.offx_button = FCButton(_("Offset X"))
        self.offx_button.setToolTip(
            _("Offset the selected object(s).\n"
              "The point of reference is the middle of\n"
              "the bounding box for all selected objects.\n"))
        self.offx_button.setMinimumWidth(90)

        grid0.addWidget(self.offx_label, 31, 0)
        grid0.addWidget(self.offx_entry, 31, 1)
        grid0.addWidget(self.offx_button, 31, 2)

        self.offy_label = QtWidgets.QLabel('%s:' % _("Y val"))
        self.offy_label.setToolTip(
            _("Distance to offset on Y axis. In current units.")
        )
        self.offy_entry = FCDoubleSpinner(callback=self.confirmation_message)
        # self.offy_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.offy_entry.set_precision(self.decimals)
        self.offy_entry.setMinimum(-1e6)

        self.offy_button = FCButton(_("Offset Y"))
        self.offy_button.setToolTip(
            _("Offset the selected object(s).\n"
              "The point of reference is the middle of\n"
              "the bounding box for all selected objects.\n"))
        self.offy_button.setMinimumWidth(90)

        grid0.addWidget(self.offy_label, 32, 0)
        grid0.addWidget(self.offy_entry, 32, 1)
        grid0.addWidget(self.offy_button, 32, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 34, 0, 1, 3)

        # ## Buffer Title
        buffer_title_label = QtWidgets.QLabel("<font size=3><b>%s</b></font>" % self.bufferName)
        grid0.addWidget(buffer_title_label, 35, 0, 1, 2)

        self.buffer_rounded_cb = FCCheckBox('%s' % _("Rounded"))
        self.buffer_rounded_cb.setToolTip(
            _("If checked then the buffer will surround the buffered shape,\n"
              "every corner will be rounded.\n"
              "If not checked then the buffer will follow the exact geometry\n"
              "of the buffered shape.")
        )

        grid0.addWidget(self.buffer_rounded_cb, 35, 2)

        self.buffer_label = QtWidgets.QLabel('%s:' % _("Distance"))
        self.buffer_label.setToolTip(
            _("A positive value will create the effect of dilation,\n"
              "while a negative value will create the effect of erosion.\n"
              "Each geometry element of the object will be increased\n"
              "or decreased with the 'distance'.")
        )

        self.buffer_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.buffer_entry.set_precision(self.decimals)
        self.buffer_entry.setSingleStep(0.1)
        self.buffer_entry.setWrapping(True)
        self.buffer_entry.set_range(-9999.9999, 9999.9999)

        self.buffer_button = FCButton(_("Buffer D"))
        self.buffer_button.setToolTip(
            _("Create the buffer effect on each geometry,\n"
              "element from the selected object, using the distance.")
        )
        self.buffer_button.setMinimumWidth(90)

        grid0.addWidget(self.buffer_label, 37, 0)
        grid0.addWidget(self.buffer_entry, 37, 1)
        grid0.addWidget(self.buffer_button, 37, 2)

        self.buffer_factor_label = QtWidgets.QLabel('%s:' % _("Value"))
        self.buffer_factor_label.setToolTip(
            _("A positive value will create the effect of dilation,\n"
              "while a negative value will create the effect of erosion.\n"
              "Each geometry element of the object will be increased\n"
              "or decreased to fit the 'Value'. Value is a percentage\n"
              "of the initial dimension.")
        )

        self.buffer_factor_entry = FCDoubleSpinner(callback=self.confirmation_message, suffix='%')
        self.buffer_factor_entry.set_range(-100.0000, 1000.0000)
        self.buffer_factor_entry.set_precision(self.decimals)
        self.buffer_factor_entry.setWrapping(True)
        self.buffer_factor_entry.setSingleStep(1)

        self.buffer_factor_button = FCButton(_("Buffer F"))
        self.buffer_factor_button.setToolTip(
            _("Create the buffer effect on each geometry,\n"
              "element from the selected object, using the factor.")
        )
        self.buffer_factor_button.setMinimumWidth(90)

        grid0.addWidget(self.buffer_factor_label, 38, 0)
        grid0.addWidget(self.buffer_factor_entry, 38, 1)
        grid0.addWidget(self.buffer_factor_button, 38, 2)

        grid0.addWidget(QtWidgets.QLabel(''), 42, 0, 1, 3)

        self.layout.addStretch()

        # Signals
        self.ref_combo.currentIndexChanged.connect(self.on_reference_changed)
        self.point_button.clicked.connect(self.on_add_coords)

        self.rotate_button.clicked.connect(self.on_rotate)

        self.skewx_button.clicked.connect(self.on_skewx)
        self.skewy_button.clicked.connect(self.on_skewy)

        self.scalex_button.clicked.connect(self.on_scalex)
        self.scaley_button.clicked.connect(self.on_scaley)

        self.offx_button.clicked.connect(self.on_offx)
        self.offy_button.clicked.connect(self.on_offy)

        self.flipx_button.clicked.connect(self.on_flipx)
        self.flipy_button.clicked.connect(self.on_flipy)

        self.buffer_button.clicked.connect(self.on_buffer_by_distance)
        self.buffer_factor_button.clicked.connect(self.on_buffer_by_factor)

        # self.rotate_entry.editingFinished.connect(self.on_rotate)
        # self.skewx_entry.editingFinished.connect(self.on_skewx)
        # self.skewy_entry.editingFinished.connect(self.on_skewy)
        # self.scalex_entry.editingFinished.connect(self.on_scalex)
        # self.scaley_entry.editingFinished.connect(self.on_scaley)
        # self.offx_entry.editingFinished.connect(self.on_offx)
        # self.offy_entry.editingFinished.connect(self.on_offy)

        self.set_tool_ui()

    def run(self, toggle=True):
        self.app.defaults.report_usage("Gerber Editor Transform Tool()")

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

        AppTool.run(self)
        self.set_tool_ui()

        self.app.ui.notebook.setTabText(2, _("Transform Tool"))

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Alt+T', **kwargs)

    def set_tool_ui(self):
        # Initialize form
        ref_val = self.app.defaults["tools_transform_reference"]
        if ref_val == _("Object"):
            ref_val = _("Selection")
        self.ref_combo.set_value(ref_val)
        self.point_entry.set_value(self.app.defaults["tools_transform_ref_point"])
        self.rotate_entry.set_value(self.app.defaults["tools_transform_rotate"])

        self.skewx_entry.set_value(self.app.defaults["tools_transform_skew_x"])
        self.skewy_entry.set_value(self.app.defaults["tools_transform_skew_y"])
        self.skew_link_cb.set_value(self.app.defaults["tools_transform_skew_link"])

        self.scalex_entry.set_value(self.app.defaults["tools_transform_scale_x"])
        self.scaley_entry.set_value(self.app.defaults["tools_transform_scale_y"])
        self.scale_link_cb.set_value(self.app.defaults["tools_transform_scale_link"])

        self.offx_entry.set_value(self.app.defaults["tools_transform_offset_x"])
        self.offy_entry.set_value(self.app.defaults["tools_transform_offset_y"])

        self.buffer_entry.set_value(self.app.defaults["tools_transform_buffer_dis"])
        self.buffer_factor_entry.set_value(self.app.defaults["tools_transform_buffer_factor"])
        self.buffer_rounded_cb.set_value(self.app.defaults["tools_transform_buffer_corner"])

        # initial state is hidden
        self.point_label.hide()
        self.point_entry.hide()
        self.point_button.hide()

    def template(self):
        if not self.draw_app.selected:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled. No shape selected."))
            return

        self.draw_app.select_tool("select")
        self.app.ui.notebook.setTabText(2, "Tools")
        self.app.ui.notebook.setCurrentWidget(self.app.ui.project_tab)

        self.app.ui.splitter.setSizes([0, 1])

    def on_reference_changed(self, index):
        if index == 0 or index == 1:  # "Origin" or "Selection" reference
            self.point_label.hide()
            self.point_entry.hide()
            self.point_button.hide()

        elif index == 2:    # "Point" reference
            self.point_label.show()
            self.point_entry.show()
            self.point_button.show()

    def on_calculate_reference(self, ref_index=None):
        if ref_index:
            ref_val = ref_index
        else:
            ref_val = self.ref_combo.currentIndex()

        if ref_val == 0:    # "Origin" reference
            return 0, 0
        elif ref_val == 1:  # "Selection" reference
            sel_list = self.draw_app.selected
            if sel_list:
                xmin, ymin, xmax, ymax = self.alt_bounds(sel_list)
                px = (xmax + xmin) * 0.5
                py = (ymax + ymin) * 0.5
                return px, py
            else:
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("No shape selected."))
                return "fail"
        elif ref_val == 2:  # "Point" reference
            point_val = self.point_entry.get_value()
            try:
                px, py = eval('{}'.format(point_val))
                return px, py
            except Exception:
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("Incorrect format for Point value. Needs format X,Y"))
                return "fail"
        else:
            sel_list = self.draw_app.selected
            if sel_list:
                xmin, ymin, xmax, ymax = self.alt_bounds(sel_list)
                if ref_val == 3:
                    return xmin, ymin   # lower left corner
                elif ref_val == 4:
                    return xmax, ymin   # lower right corner
                elif ref_val == 5:
                    return xmax, ymax   # upper right corner
                else:
                    return xmin, ymax   # upper left corner
            else:
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("No shape selected."))
                return "fail"

    def on_add_coords(self):
        val = self.app.clipboard.text()
        self.point_entry.set_value(val)

    def on_rotate(self, sig=None, val=None, ref=None):
        value = float(self.rotate_entry.get_value()) if val is None else val
        if value == 0:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Rotate transformation can not be done for a value of 0."))
            return
        point = self.on_calculate_reference() if ref is None else self.on_calculate_reference(ref_index=ref)
        if point == 'fail':
            return
        self.app.worker_task.emit({'fcn': self.on_rotate_action, 'params': [value, point]})

    def on_flipx(self, signal=None, ref=None):
        axis = 'Y'
        point = self.on_calculate_reference() if ref is None else self.on_calculate_reference(ref_index=ref)
        if point == 'fail':
            return
        self.app.worker_task.emit({'fcn': self.on_flip, 'params': [axis, point]})

    def on_flipy(self, signal=None, ref=None):
        axis = 'X'
        point = self.on_calculate_reference() if ref is None else self.on_calculate_reference(ref_index=ref)
        if point == 'fail':
            return
        self.app.worker_task.emit({'fcn': self.on_flip, 'params': [axis, point]})

    def on_skewx(self, signal=None, val=None, ref=None):
        xvalue = float(self.skewx_entry.get_value()) if val is None else val

        if xvalue == 0:
            return

        if self.skew_link_cb.get_value():
            yvalue = xvalue
        else:
            yvalue = 0

        axis = 'X'
        point = self.on_calculate_reference() if ref is None else self.on_calculate_reference(ref_index=ref)
        if point == 'fail':
            return

        self.app.worker_task.emit({'fcn': self.on_skew, 'params': [axis, xvalue, yvalue, point]})

    def on_skewy(self, signal=None, val=None, ref=None):
        xvalue = 0
        yvalue = float(self.skewy_entry.get_value()) if val is None else val

        if yvalue == 0:
            return

        axis = 'Y'
        point = self.on_calculate_reference() if ref is None else self.on_calculate_reference(ref_index=ref)
        if point == 'fail':
            return

        self.app.worker_task.emit({'fcn': self.on_skew, 'params': [axis, xvalue, yvalue, point]})

    def on_scalex(self, signal=None, val=None, ref=None):
        xvalue = float(self.scalex_entry.get_value()) if val is None else val

        if xvalue == 0 or xvalue == 1:
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("Scale transformation can not be done for a factor of 0 or 1."))
            return

        if self.scale_link_cb.get_value():
            yvalue = xvalue
        else:
            yvalue = 1

        axis = 'X'
        point = self.on_calculate_reference() if ref is None else self.on_calculate_reference(ref_index=ref)
        if point == 'fail':
            return

        self.app.worker_task.emit({'fcn': self.on_scale, 'params': [axis, xvalue, yvalue, point]})

    def on_scaley(self, signal=None, val=None, ref=None):
        xvalue = 1
        yvalue = float(self.scaley_entry.get_value()) if val is None else val

        if yvalue == 0 or yvalue == 1:
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("Scale transformation can not be done for a factor of 0 or 1."))
            return

        axis = 'Y'
        point = self.on_calculate_reference() if ref is None else self.on_calculate_reference(ref_index=ref)
        if point == 'fail':
            return

        self.app.worker_task.emit({'fcn': self.on_scale, 'params': [axis, xvalue, yvalue, point]})

    def on_offx(self, signal=None, val=None):
        value = float(self.offx_entry.get_value()) if val is None else val
        if value == 0:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Offset transformation can not be done for a value of 0."))
            return
        axis = 'X'

        self.app.worker_task.emit({'fcn': self.on_offset, 'params': [axis, value]})

    def on_offy(self, signal=None, val=None):
        value = float(self.offy_entry.get_value()) if val is None else val
        if value == 0:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Offset transformation can not be done for a value of 0."))
            return
        axis = 'Y'

        self.app.worker_task.emit({'fcn': self.on_offset, 'params': [axis, value]})

    def on_buffer_by_distance(self):
        value = self.buffer_entry.get_value()
        join = 1 if self.buffer_rounded_cb.get_value() else 2

        self.app.worker_task.emit({'fcn': self.on_buffer_action, 'params': [value, join]})

    def on_buffer_by_factor(self):
        value = 1 + (self.buffer_factor_entry.get_value() / 100.0)
        join = 1 if self.buffer_rounded_cb.get_value() else 2

        # tell the buffer method to use the factor
        factor = True

        self.app.worker_task.emit({'fcn': self.on_buffer_action, 'params': [value, join, factor]})

    def on_rotate_action(self, val, point):
        """
        Rotate geometry

        :param num:     Rotate with a known angle value, val
        :param point:   Reference point for rotation: tuple
        :return:
        """

        elem_list = self.draw_app.selected
        px, py = point

        if not elem_list:
            self.app.inform.emit('[WARNING_NOTCL] %s' %_("No shape selected."))
            return

        with self.app.proc_container.new(_("Appying Rotate")):
            try:
                for sel_el_shape in elem_list:
                    sel_el = sel_el_shape.geo
                    if 'solid' in sel_el:
                        sel_el['solid'] = affinity.rotate(sel_el['solid'], angle=-val, origin=(px, py))
                    if 'follow' in sel_el:
                        sel_el['follow'] = affinity.rotate(sel_el['follow'], angle=-val, origin=(px, py))
                    if 'clear' in sel_el:
                        sel_el['clear'] = affinity.rotate(sel_el['clear'], angle=-val, origin=(px, py))
                self.draw_app.plot_all()

                self.app.inform.emit('[success] %s' % _("Done. Rotate completed."))
            except Exception as e:
                self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Rotation action was not executed."), str(e)))
                return

    def on_flip(self, axis, point):
        """
        Mirror (flip) geometry

        :param axis:    Mirror on a known axis given by the axis parameter
        :param point:   Mirror reference point
        :return:
        """

        elem_list = self.draw_app.selected
        px, py = point

        if not elem_list:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("No shape selected."))
            return

        with self.app.proc_container.new(_("Applying Flip")):
            try:
                # execute mirroring
                for sel_el_shape in elem_list:
                    sel_el = sel_el_shape.geo
                    if axis == 'X':
                        if 'solid' in sel_el:
                            sel_el['solid'] = affinity.scale(sel_el['solid'], xfact=1, yfact=-1, origin=(px, py))
                        if 'follow' in sel_el:
                            sel_el['follow'] = affinity.scale(sel_el['follow'], xfact=1, yfact=-1, origin=(px, py))
                        if 'clear' in sel_el:
                            sel_el['clear'] = affinity.scale(sel_el['clear'], xfact=1, yfact=-1, origin=(px, py))
                        self.app.inform.emit('[success] %s...' % _('Flip on the Y axis done'))
                    elif axis == 'Y':
                        if 'solid' in sel_el:
                            sel_el['solid'] = affinity.scale(sel_el['solid'], xfact=-1, yfact=1, origin=(px, py))
                        if 'follow' in sel_el:
                            sel_el['follow'] = affinity.scale(sel_el['follow'], xfact=-1, yfact=1, origin=(px, py))
                        if 'clear' in sel_el:
                            sel_el['clear'] = affinity.scale(sel_el['clear'], xfact=-1, yfact=1, origin=(px, py))
                        self.app.inform.emit('[success] %s...' % _('Flip on the X axis done'))
                self.draw_app.plot_all()
            except Exception as e:
                self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Flip action was not executed."), str(e)))
                return

    def on_skew(self, axis, xval, yval, point):
        """
        Skew geometry

        :param axis:    Axis on which to deform, skew
        :param xval:    Skew value on X axis
        :param yval:    Skew value on Y axis
        :param point:   Point of reference for deformation: tuple
        :return:
        """
        elem_list = self.draw_app.selected
        px, py = point

        if not elem_list:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("No shape selected."))
            return

        with self.app.proc_container.new(_("Applying Skew")):
            try:

                for sel_el_shape in elem_list:
                    sel_el = sel_el_shape.geo

                    if 'solid' in sel_el:
                        sel_el['solid'] = affinity.skew(sel_el['solid'], xval, yval, origin=(px, py))
                    if 'follow' in sel_el:
                        sel_el['follow'] = affinity.skew(sel_el['follow'], xval, yval, origin=(px, py))
                    if 'clear' in sel_el:
                        sel_el['clear'] = affinity.skew(sel_el['clear'], xval, yval, origin=(px, py))

                self.draw_app.plot_all()

                if str(axis) == 'X':
                    self.app.inform.emit('[success] %s...' % _('Skew on the X axis done'))
                else:
                    self.app.inform.emit('[success] %s...' % _('Skew on the Y axis done'))
            except Exception as e:
                self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Skew action was not executed."), str(e)))
                return

    def on_scale(self, axis, xfactor, yfactor, point=None):
        """
        Scale geometry

        :param axis:        Axis on which to scale
        :param xfactor:     Factor for scaling on X axis
        :param yfactor:     Factor for scaling on Y axis
        :param point:       Point of origin for scaling

        :return:
        """
        elem_list = self.draw_app.selected
        px, py = point

        if not elem_list:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("No shape selected."))
            return
        else:
            with self.app.proc_container.new(_("Applying Scale")):
                try:
                    for sel_el_shape in elem_list:
                        sel_el = sel_el_shape.geo
                        if 'solid' in sel_el:
                            sel_el['solid'] = affinity.scale(sel_el['solid'], xfactor, yfactor, origin=(px, py))
                        if 'follow' in sel_el:
                            sel_el['follow'] = affinity.scale(sel_el['follow'], xfactor, yfactor, origin=(px, py))
                        if 'clear' in sel_el:
                            sel_el['clear'] = affinity.scale(sel_el['clear'], xfactor, yfactor, origin=(px, py))
                    self.draw_app.plot_all()

                    if str(axis) == 'X':
                        self.app.inform.emit('[success] %s...' % _('Scale on the X axis done'))
                    else:
                        self.app.inform.emit('[success] %s...' % _('Scale on the Y axis done'))

                except Exception as e:
                    self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Scale action was not executed."), str(e)))
                    return

    def on_offset(self, axis, num):
        """
        Offset geometry

        :param axis:        Axis on which to apply offset
        :param num:         The translation factor

        :return:
        """
        elem_list = self.draw_app.selected

        if not elem_list:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("No shape selected."))
            return

        with self.app.proc_container.new(_("Applying Offset")):
            try:
                for sel_el_shape in elem_list:
                    sel_el = sel_el_shape.geo
                    if axis == 'X':
                        if 'solid' in sel_el:
                            sel_el['solid'] = affinity.translate(sel_el['solid'], num, 0)
                        if 'follow' in sel_el:
                            sel_el['follow'] = affinity.translate(sel_el['follow'], num, 0)
                        if 'clear' in sel_el:
                            sel_el['clear'] = affinity.translate(sel_el['clear'], num, 0)
                    elif axis == 'Y':
                        if 'solid' in sel_el:
                            sel_el['solid'] = affinity.translate(sel_el['solid'], 0, num)
                        if 'follow' in sel_el:
                            sel_el['follow'] = affinity.translate(sel_el['follow'], 0, num)
                        if 'clear' in sel_el:
                            sel_el['clear'] = affinity.translate(sel_el['clear'], 0, num)
                    self.draw_app.plot_all()

                if str(axis) == 'X':
                    self.app.inform.emit('[success] %s...' % _('Offset on the X axis done'))
                else:
                    self.app.inform.emit('[success] %s...' % _('Offset on the Y axis done'))

            except Exception as e:
                self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Offset action was not executed."), str(e)))
                return

    def on_buffer_action(self, value, join, factor=None):
        elem_list = self.draw_app.selected

        if not elem_list:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("No shape selected"))
            return

        with self.app.proc_container.new(_("Applying Buffer")):
            try:
                for sel_el_shape in elem_list:
                    sel_el = sel_el_shape.geo

                    if factor:
                        if 'solid' in sel_el:
                            sel_el['solid'] = affinity.scale(sel_el['solid'], value, value, origin='center')
                        if 'follow' in sel_el:
                            sel_el['follow'] = affinity.scale(sel_el['solid'], value, value, origin='center')
                        if 'clear' in sel_el:
                            sel_el['clear'] = affinity.scale(sel_el['solid'], value, value, origin='center')
                    else:
                        if 'solid' in sel_el:
                            sel_el['solid'] = sel_el['solid'].buffer(
                                value, resolution=self.app.defaults["gerber_circle_steps"], join_style=join)
                        if 'clear' in sel_el:
                            sel_el['clear'] = sel_el['clear'].buffer(
                                value, resolution=self.app.defaults["gerber_circle_steps"], join_style=join)

                    self.draw_app.plot_all()

                self.app.inform.emit('[success] %s...' % _('Buffer done'))

            except Exception as e:
                self.app.log.debug("TransformEditorTool.on_buffer_action() --> %s" % str(e))
                self.app.inform.emit('[ERROR_NOTCL] %s: %s.' % (_("Action was not executed, due of"), str(e)))
                return

    def on_rotate_key(self):
        val_box = FCInputDialog(title=_("Rotate ..."),
                                text='%s:' % _('Enter an Angle Value (degrees)'),
                                min=-359.9999, max=360.0000, decimals=self.decimals,
                                init_val=float(self.app.defaults['tools_transform_rotate']))
        val_box.setWindowIcon(QtGui.QIcon(self.app.resource_location + '/rotate.png'))

        val, ok = val_box.get_value()
        if ok:
            self.on_rotate(val=val, ref=1)
            self.app.inform.emit('[success] %s...' % _("Geometry shape rotate done"))
            return
        else:
            self.app.inform.emit('[WARNING_NOTCL] %s...' % _("Geometry shape rotate cancelled"))

    def on_offx_key(self):
        units = self.app.defaults['units'].lower()

        val_box = FCInputDialog(title=_("Offset on X axis ..."),
                                text='%s: (%s)' % (_('Enter a distance Value'), str(units)),
                                min=-9999.9999, max=10000.0000, decimals=self.decimals,
                                init_val=float(self.app.defaults['tools_transform_offset_x']))
        val_box.setWindowIcon(QtGui.QIcon(self.app.resource_location + '/offsetx32.png'))

        val, ok = val_box.get_value()
        if ok:
            self.on_offx(val=val)
            self.app.inform.emit('[success] %s...' % _("Geometry shape offset on X axis done"))
            return
        else:
            self.app.inform.emit('[WARNING_NOTCL] %s...' % _("Geometry shape offset X cancelled"))

    def on_offy_key(self):
        units = self.app.defaults['units'].lower()

        val_box = FCInputDialog(title=_("Offset on Y axis ..."),
                                text='%s: (%s)' % (_('Enter a distance Value'), str(units)),
                                min=-9999.9999, max=10000.0000, decimals=self.decimals,
                                init_val=float(self.app.defaults['tools_transform_offset_y']))
        val_box.setWindowIcon(QtGui.QIcon(self.app.resource_location + '/offsety32.png'))

        val, ok = val_box.get_value()
        if ok:
            self.on_offx(val=val)
            self.app.inform.emit('[success] %s...' % _("Geometry shape offset on Y axis done"))
            return
        else:
            self.app.inform.emit('[WARNING_NOTCL] %s...' % _("Geometry shape offset Y cancelled"))

    def on_skewx_key(self):
        val_box = FCInputDialog(title=_("Skew on X axis ..."),
                                text='%s:' % _('Enter an Angle Value (degrees)'),
                                min=-359.9999, max=360.0000, decimals=self.decimals,
                                init_val=float(self.app.defaults['tools_transform_skew_x']))
        val_box.setWindowIcon(QtGui.QIcon(self.app.resource_location + '/skewX.png'))

        val, ok = val_box.get_value()
        if ok:
            self.on_skewx(val=val, ref=3)
            self.app.inform.emit('[success] %s...' % _("Geometry shape skew on X axis done"))
            return
        else:
            self.app.inform.emit('[WARNING_NOTCL] %s...' % _("Geometry shape skew X cancelled"))

    def on_skewy_key(self):
        val_box = FCInputDialog(title=_("Skew on Y axis ..."),
                                text='%s:' % _('Enter an Angle Value (degrees)'),
                                min=-359.9999, max=360.0000, decimals=self.decimals,
                                init_val=float(self.app.defaults['tools_transform_skew_y']))
        val_box.setWindowIcon(QtGui.QIcon(self.app.resource_location + '/skewY.png'))

        val, ok = val_box.get_value()
        if ok:
            self.on_skewx(val=val, ref=3)
            self.app.inform.emit('[success] %s...' % _("Geometry shape skew on Y axis done"))
            return
        else:
            self.app.inform.emit('[WARNING_NOTCL] %s...' % _("Geometry shape skew Y cancelled"))

    @staticmethod
    def alt_bounds(shapelist):
        """
        Returns coordinates of rectangular bounds of a selection of shapes
        """

        def bounds_rec(lst):
            minx = np.Inf
            miny = np.Inf
            maxx = -np.Inf
            maxy = -np.Inf

            try:
                for shape in lst:
                    el = shape.geo
                    if 'solid' in el:
                        minx_, miny_, maxx_, maxy_ = bounds_rec(el['solid'])
                        minx = min(minx, minx_)
                        miny = min(miny, miny_)
                        maxx = max(maxx, maxx_)
                        maxy = max(maxy, maxy_)
                return minx, miny, maxx, maxy
            except TypeError:
                # it's an object, return it's bounds
                return lst.bounds

        return bounds_rec(shapelist)

def get_shapely_list_bounds(geometry_list):
    xmin = np.Inf
    ymin = np.Inf
    xmax = -np.Inf
    ymax = -np.Inf

    for gs in geometry_list:
        try:
            gxmin, gymin, gxmax, gymax = gs.bounds
            xmin = min([xmin, gxmin])
            ymin = min([ymin, gymin])
            xmax = max([xmax, gxmax])
            ymax = max([ymax, gymax])
        except Exception as e:
            log.warning("DEVELOPMENT: Tried to get bounds of empty geometry. --> %s" % str(e))

    return [xmin, ymin, xmax, ymax]
