# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# Author: Dennis Hayrullin (c)                             #
# Date: 2016                                               #
# MIT Licence                                              #
# ##########################################################

from PyQt6 import QtCore
from PyQt6.QtGui import QPalette
# from PyQt6.QtCore import QSettings

import time

import vispy.scene as scene
from vispy.scene.cameras.base_camera import BaseCamera
from vispy.scene.cameras.perspective import PerspectiveCamera
from vispy.util import keys
from vispy.color import Color
from appGUI.VisPyVisuals import ShapeGroup, ShapeCollection, TextCollection, TextGroup, Cursor
from vispy.scene.visuals import InfiniteLine, Line, Rectangle, Text, XYZAxis

import gettext
import appTranslation as fcTranslate
import builtins

import numpy as np
from vispy.geometry import Rect

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

white = Color("#ffffff")
black = Color("#000000")


class PlotCanvas3d(QtCore.QObject, scene.SceneCanvas):
    """
    Class handling the plotting area in the application.
    """

    def __init__(self, container, fcapp):
        """
        The constructor configures the VisPy figure that
        will contain all plots, creates the base axes and connects
        events to the plotting area.

        :param container: The parent container in which to draw plots.
        :rtype: PlotCanvas
        """

        # super(PlotCanvas, self).__init__()
        # QtCore.QObject.__init__(self)
        # VisPyCanvas.__init__(self)
        super().__init__()

        # VisPyCanvas does not allow new attributes. Override.
        self.unfreeze()

        self.fcapp = fcapp

        # Parent container
        self.container = container

        settings = QtCore.QSettings("Open Source", "FlatCAM")
        if settings.contains("theme"):
            theme = settings.value('theme', type=str)
        else:
            theme = 'white'

        if settings.contains("axis_font_size"):
            a_fsize = settings.value('axis_font_size', type=int)
        else:
            a_fsize = 8

        if theme == 'white':
            theme_color = Color('#FFFFFF')
            tick_color = Color('#000000')
            back_color = str(QPalette().color(QPalette.ColorRole.Window).name())
        else:
            theme_color = Color('#000000')
            tick_color = Color('gray')
            back_color = Color('#000000')

        self.central_widget.bgcolor = back_color
        self.central_widget.border_color = back_color

        self.grid_widget = self.central_widget.add_grid()
        self.grid_widget.spacing = 0

        top_padding = self.grid_widget.add_widget(row=0, col=0, col_span=2)
        top_padding.height_max = 0

        # self.yaxis = scene.AxisWidget(
        #     orientation='left', axis_color=tick_color, text_color=tick_color, font_size=a_fsize, axis_width=1
        # )
        # self.yaxis.width_max = 55
        # self.grid_widget.add_widget(self.yaxis, row=1, col=0)
        #
        # self.xaxis = scene.AxisWidget(
        #     orientation='bottom', axis_color=tick_color, text_color=tick_color, font_size=a_fsize, axis_width=1,
        #     anchors=['center', 'bottom']
        # )
        # self.xaxis.height_max = 30
        # self.grid_widget.add_widget(self.xaxis, row=2, col=1)

        right_padding = self.grid_widget.add_widget(row=0, col=2, row_span=2)
        # right_padding.width_max = 24
        right_padding.width_max = 0

        self.view = self.grid_widget.add_view(row=1, col=1, border_color=tick_color, bgcolor=theme_color)
        # self.view.camera = Camera_3D(aspect=1, rect=(-25, -25, 150, 150))
        self.view.camera = Camera_3D()

        xax = scene.Axis(pos=[[0, 0], [0, 500]], tick_direction=(0, 1), domain=(0, 500),
                         font_size=16, axis_color='k', tick_color='k', text_color='k',
                         parent=self.view.scene)
        xax.transform = scene.STTransform(translate=(0, 0, -0.2))

        yax = scene.Axis(pos=[[0, 0], [500, 0]], tick_direction=(1, 0), domain=(0, 500),
                         font_size=16, axis_color='k', tick_color='k', text_color='k',
                         parent=self.view.scene)
        yax.transform = scene.STTransform(translate=(0, 0, -0.2))

        self.xyz_axis = XYZAxis(parent=self.view.scene)

        # Following function was removed from 'prepare_draw()' of 'Grid' class by patch,
        # it is necessary to call manually
        # self.grid_widget._update_child_widget_dim()

        # self.xaxis.link_view(self.view)
        # self.yaxis.link_view(self.view)

        # if theme == 'white':
        #     self.grid = scene.GridLines(parent=self.view.scene, color='dimgray')
        # else:
        #     self.grid = scene.GridLines(parent=self.view.scene, color='#dededeff')
        #
        # self.grid.set_gl_state(depth_test=False)

        # workspace lines; I didn't use the rectangle because I didn't want to add another VisPy Node,
        # which might decrease performance
        # self.b_line, self.r_line, self.t_line, self.l_line = None, None, None, None
        self.workspace_line = None

        # <VisPyCanvas>
        self.create_native()
        self.native.setParent(self.fcapp.ui)

        # <QtCore.QObject>
        self.container.addWidget(self.native)

        self.line_parent = None
        if self.fcapp.defaults["global_cursor_color_enabled"]:
            c_color = Color(self.fcapp.defaults["global_cursor_color"]).rgba
        else:
            c_color = self.line_color

        # font size
        qsettings = QtCore.QSettings("Open Source", "FlatCAM")
        if qsettings.contains("hud_font_size"):
            fsize = qsettings.value('hud_font_size', type=int)
        else:
            fsize = 8

        # units
        # units = self.fcapp.app_units.upper()

        # coordinates and anchors
        height = fsize * 11     # 90. Constant 11 is something that works
        width = height * 2      # width is double the height = it is something that works
        # center_x = (width / 2) + 5
        # center_y = (height / 2) + 5

        # enable Grid lines
        self.grid_lines_enabled = True

        self.shape_collections = []

        self.shape_collection = self.new_shape_collection()
        self.fcapp.pool_recreated.connect(self.on_pool_recreated)

        self.text_collection = self.new_text_collection()
        self.text_collection.enabled = True

        self.c = None

        # Keep VisPy canvas happy by letting it be "frozen" again.
        self.freeze()
        self.fit_view()

        # self.graph_event_connect('mouse_wheel', self.on_mouse_scroll)

    def graph_event_connect(self, event_name, callback):
        return getattr(self.events, event_name).connect(callback)

    def graph_event_disconnect(self, event_name, callback=None):
        if callback is None:
            getattr(self.events, event_name).disconnect()
        else:
            getattr(self.events, event_name).disconnect(callback)

    def translate_coords(self, pos):
        """
        Translate pixels to FlatCAM units.

        """
        tr = self.grid.get_transform('canvas', 'visual')
        return tr.map(pos)

    def translate_coords_2(self, pos):
        """
        Translate FlatCAM units to pixels.
        """
        tr = self.grid.get_transform('visual', 'document')
        return tr.map(pos)

    def zoom(self, factor, center=None):
        """
        Zooms the plot by factor around a given
        center point. Takes care of re-drawing.

        :param factor: Number by which to scale the plot.
        :type factor: float
        :param center: Coordinates [x, y] of the point around which to scale the plot.
        :type center: list
        :return: None
        """
        self.view.camera.zoom(factor, center)

    def new_shape_group(self, shape_collection=None):
        if shape_collection:
            return ShapeGroup(shape_collection)
        return ShapeGroup(self.shape_collection)

    def new_shape_collection(self, **kwargs):
        # sc = ShapeCollection(parent=self.view.scene, pool=self.app.pool, **kwargs)
        # self.shape_collections.append(sc)
        # return sc
        return ShapeCollection(parent=self.view.scene, pool=self.fcapp.pool, **kwargs)

    def new_cursor(self):
        """
        Will create a mouse cursor pointer on canvas

        :return: the mouse cursor object
        """
        self.c = Cursor(pos=np.empty((0, 2)), parent=self.view.scene)
        self.c.antialias = 0
        return self.c

    def on_mouse_scroll(self, event):
        # key modifiers
        modifiers = event.modifiers

        pan_delta_x = self.fcapp.defaults["global_gridx"]
        pan_delta_y = self.fcapp.defaults["global_gridy"]
        curr_pos = event.pos

        # Controlled pan by mouse wheel
        if 'Shift' in modifiers:
            p1 = np.array(curr_pos)[:2]

            if event.delta[1] > 0:
                curr_pos[0] -= pan_delta_x
            else:
                curr_pos[0] += pan_delta_x
            p2 = np.array(curr_pos)[:2]
            self.view.camera.pan(p2 - p1)
        elif 'Control' in modifiers:
            p1 = np.array(curr_pos)[:2]

            if event.delta[1] > 0:
                curr_pos[1] += pan_delta_y
            else:
                curr_pos[1] -= pan_delta_y
            p2 = np.array(curr_pos)[:2]
            self.view.camera.pan(p2 - p1)

        # if self.fcapp.grid_status():
        #     pos_canvas = self.translate_coords(curr_pos)
        #     pos = self.fcapp.geo_editor.snap(pos_canvas[0], pos_canvas[1])
        #
        #     # Update cursor
        #     self.fcapp.app_cursor.set_data(np.asarray([(pos[0], pos[1])]),
        #                                    symbol='++', edge_color=self.fcapp.cursor_color_3D,
        #                                    edge_width=self.fcapp.defaults["global_cursor_width"],
        #                                    size=self.fcapp.defaults["global_cursor_size"])

    def new_text_group(self, collection=None):
        if collection:
            return TextGroup(collection)
        else:
            return TextGroup(self.text_collection)

    def new_text_collection(self, **kwargs):
        return TextCollection(parent=self.view.scene, **kwargs)

    def fit_view(self, rect=None):

        # Lock updates in other threads
        self.shape_collection.lock_updates()

        if not rect:
            rect = Rect(-1, -1, 20, 20)
            try:
                rect.left, rect.right = self.shape_collection.bounds(axis=0)
                rect.bottom, rect.top = self.shape_collection.bounds(axis=1)
            except TypeError:
                pass

        # adjust the view camera to be slightly bigger than the bounds so the shape collection can be seen clearly
        # otherwise the shape collection boundary will have no border
        dx = rect.right - rect.left
        dy = rect.top - rect.bottom
        x_factor = dx * 0.02
        y_factor = dy * 0.02

        rect.left -= x_factor
        rect.bottom -= y_factor
        rect.right += x_factor
        rect.top += y_factor

        self.view.camera.rect = rect

        self.shape_collection.unlock_updates()

    def fit_center(self, loc, rect=None):

        # Lock updates in other threads
        self.shape_collection.lock_updates()

        if not rect:
            try:
                rect = Rect(loc[0]-20, loc[1]-20, 40, 40)
            except TypeError:
                pass

        self.view.camera.rect = rect

        self.shape_collection.unlock_updates()

    def clear(self):
        pass

    def redraw(self):
        self.shape_collection.redraw([])
        self.text_collection.redraw()

    def on_pool_recreated(self, pool):
        self.shape_collection.pool = pool


class Camera_3D(scene.ArcballCamera):

    def __init__(self, **kwargs):
        super(Camera_3D, self).__init__(**kwargs)

        self.minimum_scene_size = 0.01
        self.maximum_scene_size = 10000

        self.last_event = None
        self.last_time = 0

        # Default mouse button for panning is RMB
        self.pan_button_setting = "2"

    def zoom(self, factor, center=None):
        pass

    # def viewbox_mouse_event(self, event):
    #     """
    #     The SubScene received a mouse event; update transform
    #     accordingly.
    #
    #     Parameters
    #     ----------
    #     event : instance of Event
    #         The event.
    #     """
    #     if event.handled or not self.interactive:
    #         return
    #
    #     # key modifiers
    #     modifiers = event.mouse_event.modifiers
    #
    #     # Limit mouse move events
    #     last_event = event.last_event
    #     t = time.time()
    #     if t - self.last_time > 0.015:
    #         self.last_time = t
    #         if self.last_event:
    #             last_event = self.last_event
    #             self.last_event = None
    #     else:
    #         if not self.last_event:
    #             self.last_event = last_event
    #         event.handled = True
    #         return
    #
    #     # ################### Scrolling ##########################
    #     BaseCamera.viewbox_mouse_event(self, event)
    #
    #     if event.type == 'mouse_wheel':
    #         if not modifiers:
    #             center = self._scene_transform.imap(event.pos)
    #             scale = (1 + self.zoom_factor) ** (-event.delta[1] * 30)
    #             self.limited_zoom(scale, center)
    #         event.handled = True
    #
    #     elif event.type == 'mouse_move':
    #         if event.press_event is None:
    #             return
    #
    #         # ################ Panning ############################
    #         # self.pan_button_setting is actually self.FlatCAM.APP.defaults['global_pan_button']
    #         if event.button == int(self.pan_button_setting) and not modifiers:
    #             # Translate
    #             p1 = np.array(last_event.pos)[:2]
    #             p2 = np.array(event.pos)[:2]
    #             p1s = self._transform.imap(p1)
    #             p2s = self._transform.imap(p2)
    #             self.pan(p1s-p2s)
    #             event.handled = True
    #         elif event.button in [2, 3] and 'Shift' in modifiers:
    #             # Zoom
    #             p1c = np.array(last_event.pos)[:2]
    #             p2c = np.array(event.pos)[:2]
    #             scale = ((1 + self.zoom_factor) **
    #                      ((p1c-p2c) * np.array([1, -1])))
    #             center = self._transform.imap(event.press_event.pos[:2])
    #             self.limited_zoom(scale, center)
    #             event.handled = True
    #         else:
    #             event.handled = False
    #     elif event.type == 'mouse_press':
    #         # accept the event if it is button 1 or 2.
    #         # This is required in order to receive future events
    #         event.handled = event.button in [1, 2, 3]
    #     else:
    #         event.handled = False

    def viewbox_mouse_event(self, event):
        """
        The viewbox received a mouse event; update transform
        accordingly.

        Parameters
        ----------
        event : instance of Event
            The event.
        """
        if event.handled or not self.interactive:
            return

        PerspectiveCamera.viewbox_mouse_event(self, event)

        if event.type == 'mouse_release':
            self._event_value = None  # Reset
        elif event.type == 'mouse_press':
            event.handled = True
        elif event.type == 'mouse_move':
            if event.press_event is None:
                return

            modifiers = event.mouse_event.modifiers
            p1 = event.mouse_event.press_event.pos
            p2 = event.mouse_event.pos
            d = p2 - p1

            if 1 in event.buttons and not modifiers:
                # Rotate
                self._update_rotation(event)

            elif 1 in event.buttons and keys.SHIFT in modifiers:
                # Zoom
                if self._event_value is None:
                    self._event_value = (self._scale_factor, self._distance)
                zoomy = (1 + self.zoom_factor) ** d[1]

                self.scale_factor = self._event_value[0] * zoomy
                # Modify distance if its given
                if self._distance is not None:
                    self._distance = self._event_value[1] * zoomy
                self.view_changed()

            elif 2 in event.buttons and not modifiers:
                # Translate
                norm = np.mean(self._viewbox.size)
                if self._event_value is None or len(self._event_value) == 2:
                    self._event_value = self.center
                dist = (p1 - p2) / norm * self._scale_factor
                dist[1] *= -1
                # Black magic part 1: turn 2D into 3D translations
                dx, dy, dz = self._dist_to_trans(dist)
                # Black magic part 2: take up-vector and flipping into account
                ff = self._flip_factors
                up, forward, right = self._get_dim_vectors()
                dx, dy, dz = right * dx + forward * dy + up * dz
                dx, dy, dz = ff[0] * dx, ff[1] * dy, dz * ff[2]
                c = self._event_value
                self.center = c[0] + dx, c[1] + dy, c[2] + dz

            elif 2 in event.buttons and keys.SHIFT in modifiers:
                # Change fov
                if self._event_value is None:
                    self._event_value = self._fov
                fov = self._event_value - d[1] / 5.0
                self.fov = min(180.0, max(0.0, fov))

    def limited_zoom(self, scale, center):

        try:
            zoom_in = scale[1] < 1
        except IndexError:
            zoom_in = scale < 1

        if (not zoom_in and self.rect.width < self.maximum_scene_size) \
                or (zoom_in and self.rect.width > self.minimum_scene_size):
            self.zoom(scale, center)
