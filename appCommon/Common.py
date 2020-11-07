# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
# ##########################################################

# ##########################################################
# File Modified (major mod): Marius Adrian Stanciu         #
# Date: 11/4/2019                                          #
# ##########################################################
from PyQt5 import QtCore

from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union

from appGUI.VisPyVisuals import ShapeCollection
from appTool import AppTool

from copy import deepcopy
import collections

import numpy as np
# from voronoi import Voronoi
# from voronoi import Polygon as voronoi_polygon

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GracefulException(Exception):
    """
    Graceful Exception raised when the user is requesting to cancel the current threaded task
    """

    def __init__(self):
        super().__init__()

    def __str__(self):
        return '\n\n%s' % _("The user requested a graceful exit of the current task.")


class LoudDict(dict):
    """
    A Dictionary with a callback for item changes.
    """

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.callback = lambda x: None

    def __setitem__(self, key, value):
        """
        Overridden __setitem__ method. Will emit 'changed(QString)' if the item was changed, with key as parameter.
        """
        if key in self and self.__getitem__(key) == value:
            return

        dict.__setitem__(self, key, value)
        self.callback(key)

    def update(self, *args, **kwargs):
        if len(args) > 1:
            raise TypeError("update expected at most 1 arguments, got %d" % len(args))
        other = dict(*args, **kwargs)
        for key in other:
            self[key] = other[key]

    def set_change_callback(self, callback):
        """
        Assigns a function as callback on item change. The callback
        will receive the key of the object that was changed.

        :param callback: Function to call on item change.
        :type callback: func
        :return: None
        """

        self.callback = callback


class LoudUniqueList(list, collections.MutableSequence):
    """
    A List with a callback for item changes, callback which returns the index where the items are added/modified.
    A List that will allow adding only items that are not in the list.
    """

    def __init__(self, arg=None):
        super().__init__()
        self.callback = lambda x: None

        if arg is not None:
            if isinstance(arg, list):
                self.extend(arg)
            else:
                self.extend([arg])

    def insert(self, i, v):
        if v in self:
            raise ValueError("One of the added items is already in the list.")
        self.callback(i)
        return super().insert(i, v)

    def append(self, v):
        if v in self:
            raise ValueError("One of the added items is already in the list.")
        le = len(self)
        self.callback(le)
        return super().append(v)

    def extend(self, t):
        for v in t:
            if v in self:
                raise ValueError("One of the added items is already in the list.")
        le = len(self)
        self.callback(le)
        return super().extend(t)

    def __add__(self, t):  # This is for something like `LoudUniqueList([1, 2, 3]) + list([4, 5, 6])`...
        for v in t:
            if v in self:
                raise ValueError("One of the added items is already in the list.")
        le = len(self)
        self.callback(le)
        return super().__add__(t)

    def __iadd__(self, t):  # This is for something like `l = LoudUniqueList(); l += [1, 2, 3]`
        for v in t:
            if v in self:
                raise ValueError("One of the added items is already in the list.")
        le = len(self)
        self.callback(le)
        return super().__iadd__(t)

    def __setitem__(self, i, v):
        try:
            for v1 in v:
                if v1 in self:
                    raise ValueError("One of the modified items is already in the list.")
        except TypeError:
            if v in self:
                raise ValueError("One of the modified items is already in the list.")
        if v is not None:
            self.callback(i)
        return super().__setitem__(i, v)

    def set_callback(self, callback):
        """
        Assigns a function as callback on item change. The callback
        will receive the index of the object that was changed.

        :param callback: Function to call on item change.
        :type callback: func
        :return: None
        """

        self.callback = callback


class FCSignal:
    """
    Taken from here: https://blog.abstractfactory.io/dynamic-signals-in-pyqt/
    """

    def __init__(self):
        self.__subscribers = []

    def emit(self, *args, **kwargs):
        for subs in self.__subscribers:
            subs(*args, **kwargs)

    def connect(self, func):
        self.__subscribers.append(func)

    def disconnect(self, func):
        try:
            self.__subscribers.remove(func)
        except ValueError:
            print('Warning: function %s not removed '
                  'from signal %s' % (func, self))


def color_variant(hex_color, bright_factor=1):
    """
    Takes a color in HEX format #FF00FF and produces a lighter or darker variant

    :param hex_color:           color to change
    :type hex_color:            str
    :param bright_factor:       factor to change the color brightness [0 ... 1]
    :type bright_factor:        float
    :return:                    Modified color
    :rtype:                     str
    """

    if len(hex_color) != 7:
        print("Color is %s, but needs to be in #FF00FF format. Returning original color." % hex_color)
        return hex_color

    if bright_factor > 1.0:
        bright_factor = 1.0
    if bright_factor < 0.0:
        bright_factor = 0.0

    rgb_hex = [hex_color[x:x + 2] for x in [1, 3, 5]]
    new_rgb = []
    for hex_value in rgb_hex:
        # adjust each color channel and turn it into a INT suitable as argument for hex()
        mod_color = round(int(hex_value, 16) * bright_factor)
        # make sure that each color channel has two digits without the 0x prefix
        mod_color_hex = str(hex(mod_color)[2:]).zfill(2)
        new_rgb.append(mod_color_hex)

    return "#" + "".join([i for i in new_rgb])


class ExclusionAreas(QtCore.QObject):
    """
    Functionality for adding Exclusion Areas for the Excellon and Geometry FlatCAM Objects
    """
    e_shape_modified = QtCore.pyqtSignal()

    def __init__(self, app):
        super().__init__()

        self.app = app

        self.app.log.debug("+ Adding Exclusion Areas")
        # Storage for shapes, storage that can be used by FlatCAm tools for utility geometry
        # VisPy visuals
        if self.app.is_legacy is False:
            try:
                self.exclusion_shapes = ShapeCollection(parent=self.app.plotcanvas.view.scene, layers=1)
            except AttributeError:
                self.exclusion_shapes = None
        else:
            from appGUI.PlotCanvasLegacy import ShapeCollectionLegacy
            self.exclusion_shapes = ShapeCollectionLegacy(obj=self, app=self.app, name="exclusion")

        # Event signals disconnect id holders
        self.mr = None
        self.mm = None
        self.kp = None

        # variables to be used in area exclusion
        self.cursor_pos = (0, 0)
        self.first_click = False
        self.points = []
        self.poly_drawn = False

        '''
        Here we store the exclusion shapes and some other information's
        Each list element is a dictionary with the format:
        
        {
            "obj_type":   string ("excellon" or "geometry")   <- self.obj_type
            "shape":      Shapely polygon
            "strategy":   string ("over" or "around")         <- self.strategy_button
            "overz":      float                               <- self.over_z_button
        }
        '''
        self.exclusion_areas_storage = []

        self.mouse_is_dragging = False

        self.solid_geometry = []
        self.obj_type = None

        self.shape_type_button = None
        self.over_z_button = None
        self.strategy_button = None
        self.cnc_button = None

    def on_add_area_click(self, shape_button, overz_button, strategy_radio, cnc_button, solid_geo, obj_type):
        """

        :param shape_button:    a FCButton that has the value for the shape
        :param overz_button:    a FCDoubleSpinner that holds the Over Z value
        :param strategy_radio:  a RadioSet button with the strategy_button value
        :param cnc_button:      a FCButton in Object UI that when clicked the CNCJob is created
                                We have a reference here so we can change the color signifying that exclusion areas are
                                available.
        :param solid_geo:       reference to the object solid geometry for which we add exclusion areas
        :param obj_type:        Type of FlatCAM object that called this method. String: "excellon" or "geometry"
        :type obj_type:         str
        :return:                None
        """
        self.app.inform.emit('[WARNING_NOTCL] %s' % _("Click the start point of the area."))
        self.app.call_source = 'geometry'

        self.shape_type_button = shape_button

        self.over_z_button = overz_button
        self.strategy_button = strategy_radio
        self.cnc_button = cnc_button

        self.solid_geometry = solid_geo
        self.obj_type = obj_type

        if self.app.is_legacy is False:
            self.app.plotcanvas.graph_event_disconnect('mouse_press', self.app.on_mouse_click_over_plot)
            self.app.plotcanvas.graph_event_disconnect('mouse_move', self.app.on_mouse_move_over_plot)
            self.app.plotcanvas.graph_event_disconnect('mouse_release', self.app.on_mouse_click_release_over_plot)
        else:
            self.app.plotcanvas.graph_event_disconnect(self.app.mp)
            self.app.plotcanvas.graph_event_disconnect(self.app.mm)
            self.app.plotcanvas.graph_event_disconnect(self.app.mr)

        self.mr = self.app.plotcanvas.graph_event_connect('mouse_release', self.on_mouse_release)
        self.mm = self.app.plotcanvas.graph_event_connect('mouse_move', self.on_mouse_move)
        # self.kp = self.app.plotcanvas.graph_event_connect('key_press', self.on_key_press)

    # To be called after clicking on the plot.
    def on_mouse_release(self, event):
        """
        Called on mouse click release.

        :param event:   Mouse event
        :type event:
        :return:        None
        :rtype:
        """
        if self.app.is_legacy is False:
            event_pos = event.pos
            # event_is_dragging = event.is_dragging
            right_button = 2
        else:
            event_pos = (event.xdata, event.ydata)
            # event_is_dragging = self.app.plotcanvas.is_dragging
            right_button = 3

        event_pos = self.app.plotcanvas.translate_coords(event_pos)
        if self.app.grid_status():
            curr_pos = self.app.geo_editor.snap(event_pos[0], event_pos[1])
        else:
            curr_pos = (event_pos[0], event_pos[1])

        x1, y1 = curr_pos[0], curr_pos[1]

        # shape_type_button = self.ui.area_shape_radio.get_value()

        # do clear area only for left mouse clicks
        if event.button == 1:
            if self.shape_type_button.get_value() == "square":
                if self.first_click is False:
                    self.first_click = True
                    self.app.inform.emit('[WARNING_NOTCL] %s' % _("Click the end point of the area."))

                    self.cursor_pos = self.app.plotcanvas.translate_coords(event_pos)
                    if self.app.grid_status():
                        self.cursor_pos = self.app.geo_editor.snap(event_pos[0], event_pos[1])
                else:
                    self.app.inform.emit(_("Zone added. Click to start adding next zone or right click to finish."))
                    self.app.delete_selection_shape()

                    x0, y0 = self.cursor_pos[0], self.cursor_pos[1]

                    pt1 = (x0, y0)
                    pt2 = (x1, y0)
                    pt3 = (x1, y1)
                    pt4 = (x0, y1)

                    new_rectangle = Polygon([pt1, pt2, pt3, pt4])

                    # {
                    #     "obj_type":   string("excellon" or "geometry") < - self.obj_type
                    #     "shape":      Shapely polygon
                    #     "strategy_button":   string("over" or "around") < - self.strategy_button
                    #     "overz":      float < - self.over_z_button
                    # }
                    new_el = {
                        "obj_type": self.obj_type,
                        "shape": new_rectangle,
                        "strategy": self.strategy_button.get_value(),
                        "overz": self.over_z_button.get_value()
                    }
                    self.exclusion_areas_storage.append(new_el)

                    if self.obj_type == 'excellon':
                        color = "#FF7400"
                        face_color = "#FF7400BF"
                    else:
                        color = "#098a8f"
                        face_color = "#FF7400BF"

                    # add a temporary shape on canvas
                    AppTool.draw_tool_selection_shape(
                        self, old_coords=(x0, y0), coords=(x1, y1),
                        color=color,
                        face_color=face_color,
                        shapes_storage=self.exclusion_shapes)

                    self.first_click = False
                    return
            else:
                self.points.append((x1, y1))

                if len(self.points) > 1:
                    self.poly_drawn = True
                    self.app.inform.emit(_("Click on next Point or click right mouse button to complete ..."))

                return ""
        elif event.button == right_button and self.mouse_is_dragging is False:

            shape_type = self.shape_type_button.get_value()

            if shape_type == "square":
                self.first_click = False
            else:
                # if we finish to add a polygon
                if self.poly_drawn is True:
                    try:
                        # try to add the point where we last clicked if it is not already in the self.points
                        last_pt = (x1, y1)
                        if last_pt != self.points[-1]:
                            self.points.append(last_pt)
                    except IndexError:
                        pass

                    # we need to add a Polygon and a Polygon can be made only from at least 3 points
                    if len(self.points) > 2:
                        AppTool.delete_moving_selection_shape(self)
                        pol = Polygon(self.points)
                        # do not add invalid polygons even if they are drawn by utility geometry
                        if pol.is_valid:
                            """
                            {
                                "obj_type":   string("excellon" or "geometry") < - self.obj_type
                                "shape":      Shapely polygon
                                "strategy":   string("over" or "around") < - self.strategy_button
                                "overz":      float < - self.over_z_button
                            }
                            """
                            new_el = {
                                "obj_type": self.obj_type,
                                "shape": pol,
                                "strategy": self.strategy_button.get_value(),
                                "overz": self.over_z_button.get_value()
                            }
                            self.exclusion_areas_storage.append(new_el)

                            if self.obj_type == 'excellon':
                                color = "#FF7400"
                                face_color = "#FF7400BF"
                            else:
                                color = "#098a8f"
                                face_color = "#FF7400BF"

                            AppTool.draw_selection_shape_polygon(
                                self, points=self.points,
                                color=color,
                                face_color=face_color,
                                shapes_storage=self.exclusion_shapes)
                            self.app.inform.emit(
                                _("Zone added. Click to start adding next zone or right click to finish."))

                    self.points = []
                    self.poly_drawn = False
                    return

            # AppTool.delete_tool_selection_shape(self, shapes_storage=self.exclusion_shapes)

            if self.app.is_legacy is False:
                self.app.plotcanvas.graph_event_disconnect('mouse_release', self.on_mouse_release)
                self.app.plotcanvas.graph_event_disconnect('mouse_move', self.on_mouse_move)
                # self.app.plotcanvas.graph_event_disconnect('key_press', self.on_key_press)
            else:
                self.app.plotcanvas.graph_event_disconnect(self.mr)
                self.app.plotcanvas.graph_event_disconnect(self.mm)
                # self.app.plotcanvas.graph_event_disconnect(self.kp)

            self.app.mp = self.app.plotcanvas.graph_event_connect('mouse_press',
                                                                  self.app.on_mouse_click_over_plot)
            self.app.mm = self.app.plotcanvas.graph_event_connect('mouse_move',
                                                                  self.app.on_mouse_move_over_plot)
            self.app.mr = self.app.plotcanvas.graph_event_connect('mouse_release',
                                                                  self.app.on_mouse_click_release_over_plot)

            self.app.call_source = 'app'

            if len(self.exclusion_areas_storage) == 0:
                return

            # since the exclusion areas should apply to all objects in the app collection, this check is limited to
            # only the current object therefore it will not guarantee success
            self.app.inform.emit("%s" % _("Exclusion areas added. Checking overlap with the object geometry ..."))

            for el in self.exclusion_areas_storage:
                if el["shape"].intersects(unary_union(self.solid_geometry)):
                    self.on_clear_area_click()
                    self.app.inform.emit(
                        "[ERROR_NOTCL] %s" % _("Failed. Exclusion areas intersects the object geometry ..."))
                    return

            self.app.inform.emit("[success] %s" % _("Exclusion areas added."))
            self.cnc_button.setStyleSheet("""
                                    QPushButton
                                    {
                                        font-weight: bold;
                                        color: orange;
                                    }
                                    """)
            self.cnc_button.setToolTip(
                '%s %s' % (_("Generate the CNC Job object."), _("With Exclusion areas."))
            )

            self.e_shape_modified.emit()

    def area_disconnect(self):
        """
        Will do the cleanup. Will disconnect the mouse events for the custom handlers in this class and initialize
        certain class attributes.

        :return:    None
        :rtype:
        """
        if self.app.is_legacy is False:
            self.app.plotcanvas.graph_event_disconnect('mouse_release', self.on_mouse_release)
            self.app.plotcanvas.graph_event_disconnect('mouse_move', self.on_mouse_move)
        else:
            self.app.plotcanvas.graph_event_disconnect(self.mr)
            self.app.plotcanvas.graph_event_disconnect(self.mm)
            self.app.plotcanvas.graph_event_disconnect(self.kp)

        self.app.mp = self.app.plotcanvas.graph_event_connect('mouse_press',
                                                              self.app.on_mouse_click_over_plot)
        self.app.mm = self.app.plotcanvas.graph_event_connect('mouse_move',
                                                              self.app.on_mouse_move_over_plot)
        self.app.mr = self.app.plotcanvas.graph_event_connect('mouse_release',
                                                              self.app.on_mouse_click_release_over_plot)
        self.points = []
        self.poly_drawn = False
        self.exclusion_areas_storage = []

        AppTool.delete_moving_selection_shape(self)
        # AppTool.delete_tool_selection_shape(self, shapes_storage=self.exclusion_shapes)

        self.app.call_source = "app"
        self.app.inform.emit("[WARNING_NOTCL] %s" % _("Cancelled. Area exclusion drawing was interrupted."))

    def on_mouse_move(self, event):
        """
        Called on mouse move

        :param event:   mouse event
        :type event:
        :return:        None
        :rtype:
        """
        shape_type = self.shape_type_button.get_value()

        if self.app.is_legacy is False:
            event_pos = event.pos
            event_is_dragging = event.is_dragging
            # right_button = 2
        else:
            event_pos = (event.xdata, event.ydata)
            event_is_dragging = self.app.plotcanvas.is_dragging
            # right_button = 3

        curr_pos = self.app.plotcanvas.translate_coords(event_pos)

        # detect mouse dragging motion
        if event_is_dragging is True:
            self.mouse_is_dragging = True
        else:
            self.mouse_is_dragging = False

        # update the cursor position
        if self.app.grid_status():
            # Update cursor
            curr_pos = self.app.geo_editor.snap(curr_pos[0], curr_pos[1])

            self.app.app_cursor.set_data(np.asarray([(curr_pos[0], curr_pos[1])]),
                                         symbol='++', edge_color=self.app.cursor_color_3D,
                                         edge_width=self.app.defaults["global_cursor_width"],
                                         size=self.app.defaults["global_cursor_size"])

        # update the positions on status bar
        if self.cursor_pos is None:
            self.cursor_pos = (0, 0)

        self.app.dx = curr_pos[0] - float(self.cursor_pos[0])
        self.app.dy = curr_pos[1] - float(self.cursor_pos[1])
        self.app.ui.position_label.setText("&nbsp;<b>X</b>: %.4f&nbsp;&nbsp;   "
                                           "<b>Y</b>: %.4f&nbsp;" % (curr_pos[0], curr_pos[1]))
        self.app.ui.rel_position_label.setText("<b>Dx</b>: %.4f&nbsp;&nbsp;  <b>Dy</b>: "
                                               "%.4f&nbsp;&nbsp;&nbsp;&nbsp;" % (self.app.dx, self.app.dy))

        units = self.app.defaults["units"].lower()
        self.app.plotcanvas.text_hud.text = \
            'Dx:\t{:<.4f} [{:s}]\nDy:\t{:<.4f} [{:s}]\n\nX:  \t{:<.4f} [{:s}]\nY:  \t{:<.4f} [{:s}]'.format(
                self.app.dx, units, self.app.dy, units, curr_pos[0], units, curr_pos[1], units)

        if self.obj_type == 'excellon':
            color = "#FF7400"
            face_color = "#FF7400BF"
        else:
            color = "#098a8f"
            face_color = "#FF7400BF"

        # draw the utility geometry
        if shape_type == "square":
            if self.first_click:
                self.app.delete_selection_shape()

                self.app.draw_moving_selection_shape(old_coords=(self.cursor_pos[0], self.cursor_pos[1]),
                                                     color=color,
                                                     face_color=face_color,
                                                     coords=(curr_pos[0], curr_pos[1]))
        else:
            AppTool.delete_moving_selection_shape(self)
            AppTool.draw_moving_selection_shape_poly(
                self, points=self.points,
                color=color,
                face_color=face_color,
                data=(curr_pos[0], curr_pos[1]))

    def on_clear_area_click(self):
        """
        Slot for clicking the button for Deleting all the Exclusion areas.

        :return:    None
        :rtype:
        """
        self.clear_shapes()

        # restore the default StyleSheet
        self.cnc_button.setStyleSheet("")
        # update the StyleSheet
        self.cnc_button.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        self.cnc_button.setToolTip('%s' % _("Generate the CNC Job object."))

    def clear_shapes(self):
        """
        Will delete all the Exclusion areas; will delete on canvas any possible selection box for the Exclusion areas.

        :return:    None
        :rtype:
        """
        if self.exclusion_areas_storage:
            self.app.inform.emit('%s' % _("All exclusion zones deleted."))
        self.exclusion_areas_storage.clear()
        AppTool.delete_moving_selection_shape(self)
        self.app.delete_selection_shape()
        AppTool.delete_tool_selection_shape(self, shapes_storage=self.exclusion_shapes)

    def delete_sel_shapes(self, idxs):
        """

        :param idxs:    list of indexes in self.exclusion_areas_storage list to be deleted
        :type idxs:     list
        :return:        None
        """

        # delete all plotted shapes
        AppTool.delete_tool_selection_shape(self, shapes_storage=self.exclusion_shapes)

        # delete shapes
        for idx in sorted(idxs, reverse=True):
            del self.exclusion_areas_storage[idx]

        # re-add what's left after deletion in first step
        if self.obj_type == 'excellon':
            color = "#FF7400"
            face_color = "#FF7400BF"
        else:
            color = "#098a8f"
            face_color = "#FF7400BF"

        face_alpha = 0.3
        color_t = face_color[:-2] + str(hex(int(face_alpha * 255)))[2:]

        for geo_el in self.exclusion_areas_storage:
            if isinstance(geo_el['shape'], Polygon):
                self.exclusion_shapes.add(
                    geo_el['shape'], color=color, face_color=color_t, update=True, layer=0, tolerance=None)
        if self.app.is_legacy is True:
            self.exclusion_shapes.redraw()

        # if there are still some exclusion areas in the storage
        if self.exclusion_areas_storage:
            self.app.inform.emit('[success] %s' % _("Selected exclusion zones deleted."))
        else:
            # restore the default StyleSheet
            self.cnc_button.setStyleSheet("")
            # update the StyleSheet
            self.cnc_button.setStyleSheet("""
                                            QPushButton
                                            {
                                                font-weight: bold;
                                            }
                                            """)
            self.cnc_button.setToolTip('%s' % _("Generate the CNC Job object."))

            # there are no more exclusion areas in the storage, all have been selected and deleted
            self.app.inform.emit('%s' % _("All exclusion zones deleted."))

    def travel_coordinates(self, start_point, end_point, tooldia):
        """
        WIll create a path the go around the exclusion areas on the shortest path when travelling (at a Z above the
        material).

        :param start_point:     X,Y coordinates for the start point of the travel line
        :type start_point:      tuple
        :param end_point:       X,Y coordinates for the destination point of the travel line
        :type end_point:        tuple
        :param tooldia:         THe tool diameter used and which generates the travel lines
        :type tooldia           float
        :return:                A list of x,y tuples that describe the avoiding path
        :rtype:                 list
        """

        ret_list = []

        # Travel lines: rapids. Should not pass through Exclusion areas
        travel_line = LineString([start_point, end_point])
        origin_point = Point(start_point)

        buffered_storage = []
        # add a little something to the half diameter, to make sure that we really don't enter in the exclusion zones
        buffered_distance = (tooldia / 2.0) + (0.1 if self.app.defaults['units'] == 'MM' else 0.00393701)

        for area in self.exclusion_areas_storage:
            new_area = deepcopy(area)
            new_area['shape'] = area['shape'].buffer(buffered_distance, join_style=2)
            buffered_storage.append(new_area)

        # sort the Exclusion areas from the closest to the start_point to the farthest
        tmp = []
        for area in buffered_storage:
            dist = Point(start_point).distance(area['shape'])
            tmp.append((dist, area))
        tmp.sort(key=lambda k: k[0])

        sorted_area_storage = [k[1] for k in tmp]

        # process the ordered exclusion areas list
        for area in sorted_area_storage:
            outline = area['shape'].exterior
            if travel_line.intersects(outline):
                intersection_pts = travel_line.intersection(outline)

                if isinstance(intersection_pts, Point):
                    # it's just a touch, continue
                    continue

                entry_pt = nearest_point(origin_point, intersection_pts)
                exit_pt = farthest_point(origin_point, intersection_pts)

                if area['strategy'] == 'around':
                    full_vertex_points = [Point(x) for x in list(outline.coords)]

                    # the last coordinate in outline, a LinearRing, is the closing one
                    # therefore a duplicate of the first one; discard it
                    vertex_points = full_vertex_points[:-1]

                    # dist_from_entry = [(entry_pt.distance(vt), vertex_points.index(vt)) for vt in vertex_points]
                    # closest_point_entry = nsmallest(1, dist_from_entry, key=lambda x: x[0])
                    # start_idx = closest_point_entry[0][1]
                    #
                    # dist_from_exit = [(exit_pt.distance(vt), vertex_points.index(vt)) for vt in vertex_points]
                    # closest_point_exit = nsmallest(1, dist_from_exit, key=lambda x: x[0])
                    # end_idx = closest_point_exit[0][1]

                    # pts_line_entry = None
                    # pts_line_exit = None
                    # for i in range(len(full_vertex_points)):
                    #     try:
                    #         line = LineString(
                    #             [
                    #                 (full_vertex_points[i].x, full_vertex_points[i].y),
                    #                 (full_vertex_points[i + 1].x, full_vertex_points[i + 1].y)
                    #             ]
                    #         )
                    #     except IndexError:
                    #         continue
                    #
                    #     if entry_pt.within(line) or entry_pt.equals(Point(line.coords[0])) or \
                    #             entry_pt.equals(Point(line.coords[1])):
                    #         pts_line_entry = [Point(x) for x in line.coords]
                    #
                    #     if exit_pt.within(line) or exit_pt.equals(Point(line.coords[0])) or \
                    #             exit_pt.equals(Point(line.coords[1])):
                    #         pts_line_exit = [Point(x) for x in line.coords]
                    #
                    # closest_point_entry = nearest_point(entry_pt, pts_line_entry)
                    # start_idx = vertex_points.index(closest_point_entry)
                    #
                    # closest_point_exit = nearest_point(exit_pt, pts_line_exit)
                    # end_idx = vertex_points.index(closest_point_exit)

                    # find all vertexes for which a line from start_point does not cross the Exclusion area polygon
                    # the same for end_point
                    # we don't need closest points for which the path leads to crosses of the Exclusion area

                    close_start_points = []
                    close_end_points = []
                    for i in range(len(vertex_points)):
                        try:
                            start_line = LineString(
                                [
                                    start_point,
                                    (vertex_points[i].x, vertex_points[i].y)
                                ]
                            )
                            end_line = LineString(
                                [
                                    end_point,
                                    (vertex_points[i].x, vertex_points[i].y)
                                ]
                            )
                        except IndexError:
                            continue

                        if not start_line.crosses(area['shape']):
                            close_start_points.append(vertex_points[i])
                        if not end_line.crosses(area['shape']):
                            close_end_points.append(vertex_points[i])

                    closest_point_entry = nearest_point(entry_pt, close_start_points)
                    closest_point_exit = nearest_point(exit_pt, close_end_points)

                    start_idx = vertex_points.index(closest_point_entry)
                    end_idx = vertex_points.index(closest_point_exit)

                    # calculate possible paths: one clockwise the other counterclockwise on the exterior of the
                    # exclusion area outline (Polygon.exterior)
                    vp_len = len(vertex_points)
                    if end_idx > start_idx:
                        path_1 = vertex_points[start_idx:(end_idx + 1)]
                        path_2 = [vertex_points[start_idx]]
                        idx = start_idx
                        for __ in range(vp_len):
                            idx = idx - 1 if idx > 0 else (vp_len - 1)
                            path_2.append(vertex_points[idx])
                            if idx == end_idx:
                                break
                    else:
                        path_1 = vertex_points[end_idx:(start_idx + 1)]
                        path_2 = [vertex_points[end_idx]]
                        idx = end_idx
                        for __ in range(vp_len):
                            idx = idx - 1 if idx > 0 else (vp_len - 1)
                            path_2.append(vertex_points[idx])
                            if idx == start_idx:
                                break
                        path_1.reverse()
                        path_2.reverse()

                    # choose the one with the lesser length
                    length_path_1 = 0
                    for i in range(len(path_1)):
                        try:
                            length_path_1 += path_1[i].distance(path_1[i + 1])
                        except IndexError:
                            pass

                    length_path_2 = 0
                    for i in range(len(path_2)):
                        try:
                            length_path_2 += path_2[i].distance(path_2[i + 1])
                        except IndexError:
                            pass

                    path = path_1 if length_path_1 < length_path_2 else path_2

                    # transform the list of Points into a list of Points coordinates
                    path_coords = [[None, (p.x, p.y)] for p in path]
                    ret_list += path_coords

                else:
                    path_coords = [[float(area['overz']), (entry_pt.x, entry_pt.y)], [None, (exit_pt.x, exit_pt.y)]]
                    ret_list += path_coords

                # create a new LineString to test again for possible other Exclusion zones
                last_pt_in_path = path_coords[-1][1]
                travel_line = LineString([last_pt_in_path, end_point])

        ret_list.append([None, end_point])
        return ret_list


def farthest_point(origin, points_list):
    """
    Calculate the farthest Point in a list from another Point

    :param origin:      Reference Point
    :type origin:       Point
    :param points_list: List of Points or a MultiPoint
    :type points_list:  list
    :return:            Farthest Point
    :rtype:             Point
    """
    old_dist = 0
    fartherst_pt = None

    for pt in points_list:
        dist = abs(origin.distance(pt))
        if dist >= old_dist:
            fartherst_pt = pt
            old_dist = dist

    return fartherst_pt


# def voronoi_diagram(geom, envelope, edges=False):
#     """
#
#     :param geom:        a collection of Shapely Points from which to build the Voronoi diagram
#     :type geom:          MultiPoint
#     :param envelope:    a bounding box to constrain the diagram (Shapely Polygon)
#     :type envelope:     Polygon
#     :param edges:       If False, return regions as polygons. Else, return only
#                         edges e.g. LineStrings.
#     :type edges:        bool, False
#     :return:
#     :rtype:
#     """
#
#     if not isinstance(geom, MultiPoint):
#         return False
#
#     coords = list(envelope.exterior.coords)
#     v_poly = voronoi_polygon(coords)
#
#     vp = Voronoi(v_poly)
#
#     points = []
#     for pt in geom:
#         points.append((pt.x, pt.y))
#     vp.create_diagram(points=points, vis_steps=False, verbose=False, vis_result=False, vis_tree=False)
#
#     if edges is True:
#         return vp.edges
#     else:
#         voronoi_polygons = []
#         for pt in vp.points:
#             try:
#                 poly_coords = list(pt.get_coordinates())
#                 new_poly_coords = []
#                 for coord in poly_coords:
#                     new_poly_coords.append((coord.x, coord.y))
#
#                 voronoi_polygons.append(Polygon(new_poly_coords))
#             except Exception:
#                 print(traceback.format_exc())
#
#         return voronoi_polygons

def nearest_point(origin, points_list):
    """
    Calculate the nearest Point in a list from another Point

    :param origin:      Reference Point
    :type origin:       Point
    :param points_list: List of Points or a MultiPoint
    :type points_list:  list
    :return:            Nearest Point
    :rtype:             Point
    """
    old_dist = np.Inf
    nearest_pt = None

    for pt in points_list:
        dist = abs(origin.distance(pt))
        if dist <= old_dist:
            nearest_pt = pt
            old_dist = dist

    return nearest_pt
