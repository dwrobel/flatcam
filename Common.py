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

from shapely.geometry import Polygon, MultiPolygon

from AppGUI.VisPyVisuals import ShapeCollection
from AppTool import AppTool

import numpy as np

import gettext
import AppTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GracefulException(Exception):
    # Graceful Exception raised when the user is requesting to cancel the current threaded task
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
    :param bright_factor:   factor to change the color brightness [0 ... 1]
    :return:                    modified color
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

    e_shape_modified = QtCore.pyqtSignal()

    def __init__(self, app):
        super().__init__()

        self.app = app

        # Storage for shapes, storage that can be used by FlatCAm tools for utility geometry
        # VisPy visuals
        if self.app.is_legacy is False:
            try:
                self.exclusion_shapes = ShapeCollection(parent=self.app.plotcanvas.view.scene, layers=1)
            except AttributeError:
                self.exclusion_shapes = None
        else:
            from AppGUI.PlotCanvasLegacy import ShapeCollectionLegacy
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
            "strategy":   string ("over" or "around")         <- self.strategy
            "overz":      float                               <- self.over_z
        }
        '''
        self.exclusion_areas_storage = []

        self.mouse_is_dragging = False

        self.solid_geometry = []
        self.obj_type = None

        self.shape_type = 'square'  # TODO use the self.app.defaults when made general (not in Geo object Pref UI)
        self.over_z = 0.1
        self.strategy = None
        self.cnc_button = None

    def on_add_area_click(self, shape_button, overz_button, strategy_radio, cnc_button, solid_geo, obj_type):
        """

        :param shape_button:    a FCButton that has the value for the shape
        :param overz_button:    a FCDoubleSpinner that holds the Over Z value
        :param strategy_radio:  a RadioSet button with the strategy value
        :param cnc_button:      a FCButton in Object UI that when clicked the CNCJob is created
                                We have a reference here so we can change the color signifying that exclusion areas are
                                available.
        :param solid_geo:       reference to the object solid geometry for which we add exclusion areas
        :param obj_type:        Type of FlatCAM object that called this method
        :type obj_type:         String: "excellon" or "geometry"
        :return:
        """
        self.app.inform.emit('[WARNING_NOTCL] %s' % _("Click the start point of the area."))
        self.app.call_source = 'geometry'

        self.shape_type = shape_button.get_value()
        self.over_z = overz_button.get_value()
        self.strategy = strategy_radio.get_value()
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

        # shape_type = self.ui.area_shape_radio.get_value()

        # do clear area only for left mouse clicks
        if event.button == 1:
            if self.shape_type == "square":
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
                    #     "strategy":   string("over" or "around") < - self.strategy
                    #     "overz":      float < - self.over_z
                    # }
                    new_el = {
                        "obj_type":     self.obj_type,
                        "shape":        new_rectangle,
                        "strategy":     self.strategy,
                        "overz":        self.over_z
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

            shape_type = self.shape_type

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
                            # {
                            #     "obj_type":   string("excellon" or "geometry") < - self.obj_type
                            #     "shape":      Shapely polygon
                            #     "strategy":   string("over" or "around") < - self.strategy
                            #     "overz":      float < - self.over_z
                            # }
                            new_el = {
                                "obj_type": self.obj_type,
                                "shape": pol,
                                "strategy": self.strategy,
                                "overz": self.over_z
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

            self.app.inform.emit(
                "[success] %s" % _("Exclusion areas added. Checking overlap with the object geometry ..."))

            for el in self.exclusion_areas_storage:
                if el["shape"].intersects(MultiPolygon(self.solid_geometry)):
                    self.on_clear_area_click()
                    self.app.inform.emit(
                        "[ERROR_NOTCL] %s" % _("Failed. Exclusion areas intersects the object geometry ..."))
                    return

            self.app.inform.emit(
                "[success] %s" % _("Exclusion areas added."))
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
            for k in self.exclusion_areas_storage:
                print(k)

    def area_disconnect(self):
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

    # called on mouse move
    def on_mouse_move(self, event):
        shape_type = self.shape_type

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
        # self.app.ui.rel_position_label.setText("<b>Dx</b>: %.4f&nbsp;&nbsp;  <b>Dy</b>: "
        #                                        "%.4f&nbsp;&nbsp;&nbsp;&nbsp;" % (self.app.dx, self.app.dy))

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
        self.exclusion_areas_storage.clear()
        AppTool.delete_moving_selection_shape(self)
        self.app.delete_selection_shape()
        AppTool.delete_tool_selection_shape(self, shapes_storage=self.exclusion_shapes)
        self.app.inform.emit('[success] %s' % _("All exclusion zones deleted."))

    def delete_sel_shapes(self, idxs):
        """

        :param idxs: list of indexes in self.exclusion_areas_storage list to be deleted
        :return:
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

            self.app.inform.emit('[success] %s' % _("All exclusion zones deleted."))
