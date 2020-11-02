# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# Author: Dennis Hayrullin (c)                             #
# Date: 2016                                               #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtCore

import logging
from appGUI.VisPyCanvas import VisPyCanvas, Color
from appGUI.VisPyVisuals import ShapeGroup, ShapeCollection, TextCollection, TextGroup, Cursor
from vispy.scene.visuals import InfiniteLine, Line, Rectangle, Text

import gettext
import appTranslation as fcTranslate
import builtins

import numpy as np
from vispy.geometry import Rect

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class PlotCanvas(QtCore.QObject, VisPyCanvas):
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

        if theme == 'white':
            self.line_color = (0.3, 0.0, 0.0, 1.0)
            self.rect_hud_color = Color('#0000FF10')
            self.text_hud_color = 'black'
        else:
            self.line_color = (0.4, 0.4, 0.4, 1.0)
            self.rect_hud_color = Color('#80808040')
            self.text_hud_color = 'white'

        # workspace lines; I didn't use the rectangle because I didn't want to add another VisPy Node,
        # which might decrease performance
        # self.b_line, self.r_line, self.t_line, self.l_line = None, None, None, None
        self.workspace_line = None

        self.pagesize_dict = {}
        self.pagesize_dict.update(
            {
                'A0': (841, 1189),
                'A1': (594, 841),
                'A2': (420, 594),
                'A3': (297, 420),
                'A4': (210, 297),
                'A5': (148, 210),
                'A6': (105, 148),
                'A7': (74, 105),
                'A8': (52, 74),
                'A9': (37, 52),
                'A10': (26, 37),

                'B0': (1000, 1414),
                'B1': (707, 1000),
                'B2': (500, 707),
                'B3': (353, 500),
                'B4': (250, 353),
                'B5': (176, 250),
                'B6': (125, 176),
                'B7': (88, 125),
                'B8': (62, 88),
                'B9': (44, 62),
                'B10': (31, 44),

                'C0': (917, 1297),
                'C1': (648, 917),
                'C2': (458, 648),
                'C3': (324, 458),
                'C4': (229, 324),
                'C5': (162, 229),
                'C6': (114, 162),
                'C7': (81, 114),
                'C8': (57, 81),
                'C9': (40, 57),
                'C10': (28, 40),

                # American paper sizes
                'LETTER': (8.5*25.4, 11*25.4),
                'LEGAL': (8.5*25.4, 14*25.4),
                'ELEVENSEVENTEEN': (11*25.4, 17*25.4),

                # From https://en.wikipedia.org/wiki/Paper_size
                'JUNIOR_LEGAL': (5*25.4, 8*25.4),
                'HALF_LETTER': (5.5*25.4, 8*25.4),
                'GOV_LETTER': (8*25.4, 10.5*25.4),
                'GOV_LEGAL': (8.5*25.4, 13*25.4),
                'LEDGER': (17*25.4, 11*25.4),
            }
        )

        # <VisPyCanvas>
        self.create_native()
        self.native.setParent(self.fcapp.ui)

        # <QtCore.QObject>
        self.container.addWidget(self.native)

        # ## AXIS # ##
        self.v_line = InfiniteLine(pos=0, color=(0.70, 0.3, 0.3, 0.8), vertical=True,
                                   parent=self.view.scene)

        self.h_line = InfiniteLine(pos=0, color=(0.70, 0.3, 0.3, 0.8), vertical=False,
                                   parent=self.view.scene)

        self.line_parent = None
        if self.fcapp.defaults["global_cursor_color_enabled"]:
            c_color = Color(self.fcapp.defaults["global_cursor_color"]).rgba
        else:
            c_color = self.line_color

        self.cursor_v_line = InfiniteLine(pos=None, color=c_color, vertical=True,
                                          parent=self.line_parent)

        self.cursor_h_line = InfiniteLine(pos=None, color=c_color, vertical=False,
                                          parent=self.line_parent)

        # font size
        qsettings = QtCore.QSettings("Open Source", "FlatCAM")
        if qsettings.contains("hud_font_size"):
            fsize = qsettings.value('hud_font_size', type=int)
        else:
            fsize = 8

        # units
        units = self.fcapp.defaults["units"].lower()

        # coordinates and anchors
        height = fsize * 11     # 90. Constant 11 is something that works
        width = height * 2      # width is double the height = it is something that works
        center_x = (width / 2) + 5
        center_y = (height / 2) + 5

        # text
        self.text_hud = Text('', color=self.text_hud_color, pos=(10, center_y), method='gpu', anchor_x='left',
                             parent=None)
        self.text_hud.font_size = fsize
        self.text_hud.text = 'Dx:\t%s [%s]\nDy:\t%s [%s]\n\nX:  \t%s [%s]\nY:  \t%s [%s]' % \
                             ('0.0000', units, '0.0000', units, '0.0000', units, '0.0000', units)

        # rectangle
        self.rect_hud = Rectangle(center=(center_x, center_y), width=width, height=height, radius=[5, 5, 5, 5],
                                  border_color=self.rect_hud_color, color=self.rect_hud_color, parent=None)
        self.rect_hud.set_gl_state(depth_test=False)

        # draw a rectangle made out of 4 lines on the canvas to serve as a hint for the work area
        # all CNC have a limited workspace
        if self.fcapp.defaults['global_workspace'] is True:
            self.draw_workspace(workspace_size=self.fcapp.defaults["global_workspaceT"])

        # HUD Display
        self.hud_enabled = False

        # enable the HUD if it is activated in FlatCAM Preferences
        if self.fcapp.defaults['global_hud'] is True:
            self.on_toggle_hud(state=True, silent=True)

        # Axis Display
        self.axis_enabled = True

        # enable Axis
        self.on_toggle_axis(state=True, silent=True)

        # enable Grid lines
        self.grid_lines_enabled = True

        self.shape_collections = []

        self.shape_collection = self.new_shape_collection()
        self.fcapp.pool_recreated.connect(self.on_pool_recreated)
        self.text_collection = self.new_text_collection()

        self.text_collection.enabled = True

        self.c = None
        self.big_cursor = None
        # Keep VisPy canvas happy by letting it be "frozen" again.
        self.freeze()
        self.fit_view()

        self.graph_event_connect('mouse_wheel', self.on_mouse_scroll)

    def on_toggle_axis(self, signal=None, state=None, silent=None):
        if not state:
            state = not self.axis_enabled

        if state:
            self.axis_enabled = True
            self.fcapp.defaults['global_axis'] = True
            self.v_line.parent = self.view.scene
            self.h_line.parent = self.view.scene
            self.fcapp.ui.axis_status_label.setStyleSheet("""
                                                          QLabel
                                                          {
                                                              color: black;
                                                              background-color: orange;
                                                          }
                                                          """)
            if silent is None:
                self.fcapp.inform[str, bool].emit(_("Axis enabled."), False)
        else:
            self.axis_enabled = False
            self.fcapp.defaults['global_axis'] = False
            self.v_line.parent = None
            self.h_line.parent = None
            self.fcapp.ui.axis_status_label.setStyleSheet("")
            if silent is None:
                self.fcapp.inform[str, bool].emit(_("Axis disabled."), False)

    def on_toggle_hud(self, signal=None, state=None, silent=None):
        if state is None:
            state = not self.hud_enabled

        if state:
            self.hud_enabled = True
            self.rect_hud.parent = self.view
            self.text_hud.parent = self.view
            self.fcapp.defaults['global_hud'] = True
            self.fcapp.ui.hud_label.setStyleSheet("""
                                                  QLabel
                                                  {
                                                      color: black;
                                                      background-color: mediumpurple;
                                                  }
                                                  """)
            if silent is None:
                self.fcapp.inform[str, bool].emit(_("HUD enabled."), False)

        else:
            self.hud_enabled = False
            self.rect_hud.parent = None
            self.text_hud.parent = None
            self.fcapp.defaults['global_hud'] = False
            self.fcapp.ui.hud_label.setStyleSheet("")
            if silent is None:
                self.fcapp.inform[str, bool].emit(_("HUD disabled."), False)

    def on_toggle_grid_lines(self, signal=None, silent=None):
        state = not self.grid_lines_enabled

        if state:
            self.fcapp.defaults['global_grid_lines'] = True
            self.grid_lines_enabled = True
            self.grid.parent = self.view.scene
            if silent is None:
                self.fcapp.inform[str, bool].emit(_("Grid enabled."), False)
        else:
            self.fcapp.defaults['global_grid_lines'] = False
            self.grid_lines_enabled = False
            self.grid.parent = None
            if silent is None:
                self.fcapp.inform[str, bool].emit(_("Grid disabled."), False)

        # HACK: enabling/disabling the cursor seams to somehow update the shapes on screen
        # - perhaps is a bug in VisPy implementation
        if self.fcapp.grid_status():
            self.fcapp.app_cursor.enabled = False
            self.fcapp.app_cursor.enabled = True
        else:
            self.fcapp.app_cursor.enabled = True
            self.fcapp.app_cursor.enabled = False

    def draw_workspace(self, workspace_size):
        """
        Draw a rectangular shape on canvas to specify our valid workspace.
        :param workspace_size: the workspace size; tuple
        :return:
        """
        try:
            if self.fcapp.defaults['units'].upper() == 'MM':
                dims = self.pagesize_dict[workspace_size]
            else:
                dims = (self.pagesize_dict[workspace_size][0]/25.4, self.pagesize_dict[workspace_size][1]/25.4)
        except Exception as e:
            log.debug("PlotCanvas.draw_workspace() --> %s" % str(e))
            return

        if self.fcapp.defaults['global_workspace_orientation'] == 'l':
            dims = (dims[1], dims[0])

        a = np.array([(0, 0), (dims[0], 0), (dims[0], dims[1]), (0, dims[1])])

        # if not self.workspace_line:
        #     self.workspace_line = Line(pos=np.array((a[0], a[1], a[2], a[3], a[0])), color=(0.70, 0.3, 0.3, 0.7),
        #                                antialias=True, method='agg', parent=self.view.scene)
        # else:
        #     self.workspace_line.parent = self.view.scene
        self.workspace_line = Line(pos=np.array((a[0], a[1], a[2], a[3], a[0])), color=(0.70, 0.3, 0.3, 0.7),
                                   antialias=True, method='agg', parent=self.view.scene)

        self.fcapp.ui.wplace_label.set_value(workspace_size[:3])
        self.fcapp.ui.wplace_label.setToolTip(workspace_size)
        self.fcapp.ui.wplace_label.setStyleSheet("""
                        QLabel
                        {
                            color: black;
                            background-color: olivedrab;
                        }
                        """)

    def delete_workspace(self):
        try:
            self.workspace_line.parent = None
        except Exception:
            pass
        self.fcapp.ui.wplace_label.setStyleSheet("")

    # redraw the workspace lines on the plot by re adding them to the parent view.scene
    def restore_workspace(self):
        try:
            self.workspace_line.parent = self.view.scene
        except Exception:
            pass

    def graph_event_connect(self, event_name, callback):
        return getattr(self.events, event_name).connect(callback)

    def graph_event_disconnect(self, event_name, callback=None):
        if callback is None:
            getattr(self.events, event_name).disconnect()
        else:
            getattr(self.events, event_name).disconnect(callback)

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

    def new_cursor(self, big=None):
        """
        Will create a mouse cursor pointer on canvas

        :param big: if True will create a mouse cursor made out of infinite lines
        :return: the mouse cursor object
        """
        if big is True:
            self.big_cursor = True
            self.c = CursorBig(app=self.fcapp)

            # in case there are multiple new_cursor calls, best to disconnect first the signals
            try:
                self.c.mouse_state_updated.disconnect(self.on_mouse_state)
            except (TypeError, AttributeError):
                pass
            try:
                self.c.mouse_position_updated.disconnect(self.on_mouse_position)
            except (TypeError, AttributeError):
                pass

            self.c.mouse_state_updated.connect(self.on_mouse_state)
            self.c.mouse_position_updated.connect(self.on_mouse_position)
        else:
            self.big_cursor = False
            self.c = Cursor(pos=np.empty((0, 2)), parent=self.view.scene)
            self.c.antialias = 0

        return self.c

    def on_mouse_state(self, state):
        if state:
            self.cursor_h_line.parent = self.view.scene
            self.cursor_v_line.parent = self.view.scene
        else:
            self.cursor_h_line.parent = None
            self.cursor_v_line.parent = None

    def on_mouse_position(self, pos):

        if self.fcapp.defaults['global_cursor_color_enabled']:
            color = Color(self.fcapp.defaults['global_cursor_color']).rgba
        else:
            color = self.line_color

        self.cursor_h_line.set_data(pos=pos[1], color=color)
        self.cursor_v_line.set_data(pos=pos[0], color=color)
        self.view.scene.update()

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

        if self.fcapp.grid_status():
            pos_canvas = self.translate_coords(curr_pos)
            pos = self.fcapp.geo_editor.snap(pos_canvas[0], pos_canvas[1])

            # Update cursor
            self.fcapp.app_cursor.set_data(np.asarray([(pos[0], pos[1])]),
                                           symbol='++', edge_color=self.fcapp.cursor_color_3D,
                                           edge_width=self.fcapp.defaults["global_cursor_width"],
                                           size=self.fcapp.defaults["global_cursor_size"])

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

        # rect.left *= 0.96
        # rect.bottom *= 0.96
        # rect.right *= 1.04
        # rect.top *= 1.04

        # units = self.fcapp.defaults['units'].upper()
        # if units == 'MM':
        #     compensation = 0.5
        # else:
        #     compensation = 0.5 / 25.4
        # rect.left -= compensation
        # rect.bottom -= compensation
        # rect.right += compensation
        # rect.top += compensation

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


class CursorBig(QtCore.QObject):
    """
    This is a fake cursor to ensure compatibility with the OpenGL engine (VisPy).
    This way I don't have to chane (disable) things related to the cursor all over when
    using the low performance Matplotlib 2D graphic engine.
    """

    mouse_state_updated = QtCore.pyqtSignal(bool)
    mouse_position_updated = QtCore.pyqtSignal(list)

    def __init__(self, app):
        super().__init__()
        self.app = app
        self._enabled = None

    @property
    def enabled(self):
        return True if self._enabled else False

    @enabled.setter
    def enabled(self, value):
        self._enabled = value
        self.mouse_state_updated.emit(value)

    def set_data(self, pos, **kwargs):
        """Internal event handler to draw the cursor when the mouse moves."""
        # if 'edge_color' in kwargs:
        #     color = kwargs['edge_color']
        # else:
        #     if self.app.defaults['global_theme'] == 'white':
        #         color = '#000000FF'
        #     else:
        #         color = '#FFFFFFFF'

        position = [pos[0][0], pos[0][1]]
        self.mouse_position_updated.emit(position)
