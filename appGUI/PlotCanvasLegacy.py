############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://caram.cl/software/flatcam                         #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
# Modified by Marius Stanciu 09/21/2019                    #
############################################################

from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal

# needed for legacy mode
# Used for solid polygons in Matplotlib
from descartes.patch import PolygonPatch

from shapely.geometry import Polygon, LineString, LinearRing

from copy import deepcopy
import logging

import numpy as np

import gettext
import appTranslation as fcTranslate
import builtins

# Prevent conflict with Qt5 and above.
from matplotlib import use as mpl_use
mpl_use("Qt5Agg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.lines import Line2D
from matplotlib.offsetbox import AnchoredText
# from matplotlib.widgets import Cursor

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class CanvasCache(QtCore.QObject):
    """

    Case story #1:

    1) No objects in the project.
    2) Object is created (app_obj.new_object() emits object_created(obj)).
       on_object_created() adds (i) object to collection and emits
       (ii) app_obj.new_object_available() then calls (iii) object.plot()
    3) object.plot() creates axes if necessary on
       app.collection.figure. Then plots on it.
    4) Plots on a cache-size canvas (in background).
    5) Plot completes. Bitmap is generated.
    6) Visible canvas is painted.

    """

    # Signals:
    # A bitmap is ready to be displayed.
    new_screen = QtCore.pyqtSignal()

    def __init__(self, plotcanvas, app, dpi=50):

        super(CanvasCache, self).__init__()

        self.app = app

        self.plotcanvas = plotcanvas
        self.dpi = dpi

        self.figure = Figure(dpi=dpi)

        self.axes = self.figure.add_axes([0.0, 0.0, 1.0, 1.0], alpha=1.0)
        self.axes.set_frame_on(False)
        self.axes.set_xticks([])
        self.axes.set_yticks([])

        if self.app.defaults['global_theme'] == 'white':
            self.axes.set_facecolor('#FFFFFF')
        else:
            self.axes.set_facecolor('#000000')

        self.canvas = FigureCanvas(self.figure)

        self.cache = None

    def run(self):

        log.debug("CanvasCache Thread Started!")
        self.plotcanvas.update_screen_request.connect(self.on_update_req)

    def on_update_req(self, extents):
        """
        Event handler for an updated display request.

        :param extents: [xmin, xmax, ymin, ymax, zoom(optional)]
        """

        # log.debug("Canvas update requested: %s" % str(extents))

        # Note: This information below might be out of date. Establish
        # a protocol regarding when to change the canvas in the main
        # thread and when to check these values here in the background,
        # or pass this data in the signal (safer).
        # log.debug("Size: %s [px]" % str(self.plotcanvas.get_axes_pixelsize()))
        # log.debug("Density: %s [units/px]" % str(self.plotcanvas.get_density()))

        # Move the requested screen portion to the main thread
        # and inform about the update:

        self.new_screen.emit()

        # Continue to update the cache.

    # def on_app_obj.new_object_available(self):
    #
    #     log.debug("A new object is available. Should plot it!")


class PlotCanvasLegacy(QtCore.QObject):
    """
    Class handling the plotting area in the application.
    """

    # Signals:
    # Request for new bitmap to display. The parameter
    # is a list with [xmin, xmax, ymin, ymax, zoom(optional)]
    update_screen_request = QtCore.pyqtSignal(list)

    double_click = QtCore.pyqtSignal(object)

    def __init__(self, container, app):
        """
        The constructor configures the Matplotlib figure that
        will contain all plots, creates the base axes and connects
        events to the plotting area.

        :param container: The parent container in which to draw plots.
        :rtype: PlotCanvas
        """

        super(PlotCanvasLegacy, self).__init__()

        self.app = app

        if self.app.defaults['global_theme'] == 'white':
            theme_color = '#FFFFFF'
            tick_color = '#000000'
            self.rect_hud_color = '#0000FF10'
            self.text_hud_color = '#000000'
        else:
            theme_color = '#000000'
            tick_color = '#FFFFFF'
            self.rect_hud_color = '#80808040'
            self.text_hud_color = '#FFFFFF'

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

        # Options
        self.x_margin = 15  # pixels
        self.y_margin = 25  # Pixels

        # Parent container
        self.container = container

        # Plots go onto a single matplotlib.figure
        self.figure = Figure(dpi=50)
        self.figure.patch.set_visible(True)
        self.figure.set_facecolor(theme_color)

        # These axes show the ticks and grid. No plotting done here.
        # New axes must have a label, otherwise mpl returns an existing one.
        self.axes = self.figure.add_axes([0.05, 0.05, 0.9, 0.9], label="base", alpha=0.0)
        self.axes.set_aspect(1)
        self.axes.grid(True, color='gray')
        self.h_line = self.axes.axhline(color=(0.70, 0.3, 0.3), linewidth=2)
        self.v_line = self.axes.axvline(color=(0.70, 0.3, 0.3), linewidth=2)

        self.axes.tick_params(axis='x', color=tick_color, labelcolor=tick_color)
        self.axes.tick_params(axis='y', color=tick_color, labelcolor=tick_color)
        self.axes.spines['bottom'].set_color(tick_color)
        self.axes.spines['top'].set_color(tick_color)
        self.axes.spines['right'].set_color(tick_color)
        self.axes.spines['left'].set_color(tick_color)

        self.axes.set_facecolor(theme_color)

        self.ch_line = None
        self.cv_line = None

        # The canvas is the top level container (FigureCanvasQTAgg)
        self.canvas = FigureCanvas(self.figure)

        self.canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.canvas.setFocus()
        self.native = self.canvas

        self.adjust_axes(-10, -10, 100, 100)
        # self.canvas.set_can_focus(True)  # For key press

        # Attach to parent
        # self.container.attach(self.canvas, 0, 0, 600, 400)
        self.container.addWidget(self.canvas)  # Qt

        # Copy a bitmap of the canvas for quick animation.
        # Update every time the canvas is re-drawn.
        self.background = self.canvas.copy_from_bbox(self.axes.bbox)

        # ################### NOT IMPLEMENTED YET - EXPERIMENTAL #######################
        # ## Bitmap Cache
        # self.cache = CanvasCache(self, self.app)
        # self.cache_thread = QtCore.QThread()
        # self.cache.moveToThread(self.cache_thread)
        # # super(PlotCanvas, self).connect(self.cache_thread, QtCore.SIGNAL("started()"), self.cache.run)
        # self.cache_thread.started.connect(self.cache.run)
        #
        # self.cache_thread.start()
        # self.cache.new_screen.connect(self.on_new_screen)
        # ##############################################################################

        # Events
        self.mp = self.graph_event_connect('button_press_event', self.on_mouse_press)
        self.mr = self.graph_event_connect('button_release_event', self.on_mouse_release)
        self.mm = self.graph_event_connect('motion_notify_event', self.on_mouse_move)
        # self.canvas.connect('configure-event', self.auto_adjust_axes)
        self.aaa = self.graph_event_connect('resize_event', self.auto_adjust_axes)
        # self.canvas.add_events(Gdk.EventMask.SMOOTH_SCROLL_MASK)
        # self.canvas.connect("scroll-event", self.on_scroll)
        self.osc = self.graph_event_connect('scroll_event', self.on_scroll)
        # self.graph_event_connect('key_press_event', self.on_key_down)
        # self.graph_event_connect('key_release_event', self.on_key_up)
        self.odr = self.graph_event_connect('draw_event', self.on_draw)

        self.key = None

        self.pan_axes = []
        self.panning = False
        self.mouse = [0, 0]
        self.big_cursor = False
        self.big_cursor_isdisabled = None

        # signal is the mouse is dragging
        self.is_dragging = False

        self.mouse_press_pos = None

        # signal if there is a doubleclick
        self.is_dblclk = False

        # HUD Display
        self.hud_enabled = False
        self.text_hud = self.Thud(plotcanvas=self)

        if self.app.defaults['global_hud'] is True:
            self.on_toggle_hud(state=True, silent=None)

        # enable Grid lines
        self.grid_lines_enabled = True

        # draw a rectangle made out of 4 lines on the canvas to serve as a hint for the work area
        # all CNC have a limited workspace
        if self.app.defaults['global_workspace'] is True:
            self.draw_workspace(workspace_size=self.app.defaults["global_workspaceT"])

        # Axis Display
        self.axis_enabled = True

        # enable Axis
        self.on_toggle_axis(state=True, silent=True)
        self.app.ui.axis_status_label.setStyleSheet("""
                                                    QLabel
                                                    {
                                                        color: black;
                                                        background-color: orange;
                                                    }
                                                    """)

    def on_toggle_axis(self, signal=None, state=None, silent=None):
        if not state:
            state = not self.axis_enabled

        if state:
            self.axis_enabled = True
            self.app.defaults['global_axis'] = True
            if self.h_line not in self.axes.lines and self.v_line not in self.axes.lines:
                self.h_line = self.axes.axhline(color=(0.70, 0.3, 0.3), linewidth=2)
                self.v_line = self.axes.axvline(color=(0.70, 0.3, 0.3), linewidth=2)
                self.app.ui.axis_status_label.setStyleSheet("""
                                                            QLabel
                                                            {
                                                                color: black;
                                                                background-color: orange;
                                                            }
                                                            """)
                if silent is None:
                    self.app.inform[str, bool].emit(_("Axis enabled."), False)
        else:
            self.axis_enabled = False
            self.app.defaults['global_axis'] = False
            if self.h_line in self.axes.lines and self.v_line in self.axes.lines:
                self.axes.lines.remove(self.h_line)
                self.axes.lines.remove(self.v_line)
                self.app.ui.axis_status_label.setStyleSheet("")
                if silent is None:
                    self.app.inform[str, bool].emit(_("Axis disabled."), False)

        self.canvas.draw()

    def on_toggle_hud(self, signal=None, state=None, silent=None):
        if state is None:
            state = not self.hud_enabled

        if state:
            self.hud_enabled = True
            self.text_hud.add_artist()
            self.app.defaults['global_hud'] = True

            self.app.ui.hud_label.setStyleSheet("""
                                                QLabel
                                                {
                                                    color: black;
                                                    background-color: mediumpurple;
                                                }
                                                """)
            if silent is None:
                self.app.inform[str, bool].emit(_("HUD enabled."), False)
        else:
            self.hud_enabled = False
            self.text_hud.remove_artist()
            self.app.defaults['global_hud'] = False
            self.app.ui.hud_label.setStyleSheet("")
            if silent is None:
                self.app.inform[str, bool].emit(_("HUD disabled."), False)

        self.canvas.draw()

    class Thud(QtCore.QObject):
        text_changed = QtCore.pyqtSignal(str)

        def __init__(self, plotcanvas):
            super().__init__()

            self.p = plotcanvas
            units = self.p.app.defaults['units']
            self._text = 'Dx:    %s [%s]\nDy:    %s [%s]\n\nX:      %s [%s]\nY:      %s [%s]' % \
                         ('0.0000', units, '0.0000', units, '0.0000', units, '0.0000', units)

            # set font size
            qsettings = QtCore.QSettings("Open Source", "FlatCAM")
            if qsettings.contains("hud_font_size"):
                # I multiply with 2.5 because this seems to be the difference between the value taken by the VisPy (3D)
                # and Matplotlib (Legacy2D FlatCAM graphic engine)
                fsize = int(qsettings.value('hud_font_size', type=int) * 2.5)
            else:
                fsize = 20

            self.hud_holder = AnchoredText(self._text, prop=dict(size=fsize), frameon=True, loc='upper left')
            self.hud_holder.patch.set_boxstyle("round,pad=0.,rounding_size=0.2")

            fc_color = self.p.rect_hud_color[:-2]
            fc_alpha = int(self.p.rect_hud_color[-2:], 16) / 255
            text_color = self.p.text_hud_color

            self.hud_holder.patch.set_facecolor(fc_color)
            self.hud_holder.patch.set_alpha(fc_alpha)
            self.hud_holder.patch.set_edgecolor((0, 0, 0, 0))

            self. hud_holder.txt._text.set_color(color=text_color)
            self.text_changed.connect(self.on_text_changed)

        @property
        def text(self):
            return self._text

        @text.setter
        def text(self, val):
            self.text_changed.emit(val)
            self._text = val

        def on_text_changed(self, txt):
            try:
                txt = txt.replace('\t', '    ')
                self.hud_holder.txt.set_text(txt)
                self.p.canvas.draw()
            except Exception:
                pass

        def add_artist(self):
            if self.hud_holder not in self.p.axes.artists:
                self.p.axes.add_artist(self.hud_holder)

        def remove_artist(self):
            if self.hud_holder in self.p.axes.artists:
                self.p.axes.artists.remove(self.hud_holder)

    def on_toggle_grid_lines(self, signal=None, silent=None):
        state = not self.grid_lines_enabled

        if state:
            self.app.defaults['global_grid_lines'] = True
            self.grid_lines_enabled = True
            self.axes.grid(True)
            try:
                self.canvas.draw()
            except IndexError:
                pass
            if silent is None:
                self.app.inform[str, bool].emit(_("Grid enabled."), False)
        else:
            self.app.defaults['global_grid_lines'] = False
            self.grid_lines_enabled = False
            self.axes.grid(False)
            try:
                self.canvas.draw()
            except IndexError:
                pass
            if silent is None:
                self.app.inform[str, bool].emit(_("Grid disabled."), False)

    def draw_workspace(self, workspace_size):
        """
        Draw a rectangular shape on canvas to specify our valid workspace.
        :param workspace_size: the workspace size; tuple
        :return:
        """
        try:
            if self.app.defaults['units'].upper() == 'MM':
                dims = self.pagesize_dict[workspace_size]
            else:
                dims = (self.pagesize_dict[workspace_size][0]/25.4, self.pagesize_dict[workspace_size][1]/25.4)
        except Exception as e:
            log.debug("PlotCanvasLegacy.draw_workspace() --> %s" % str(e))
            return

        if self.app.defaults['global_workspace_orientation'] == 'l':
            dims = (dims[1], dims[0])

        xdata = [0, dims[0], dims[0], 0, 0]
        ydata = [0, 0, dims[1], dims[1], 0]

        if self.workspace_line not in self.axes.lines:
            self.workspace_line = Line2D(xdata=xdata, ydata=ydata, linewidth=2, antialiased=True, color='#b34d4d')
            self.axes.add_line(self.workspace_line)
            self.canvas.draw()

        self.app.ui.wplace_label.set_value(workspace_size[:3])
        self.app.ui.wplace_label.setToolTip(workspace_size)
        self.fcapp.ui.wplace_label.setStyleSheet("""
                        QLabel
                        {
                            color: black;
                            background-color: olivedrab;
                        }
                        """)

    def delete_workspace(self):
        try:
            self.axes.lines.remove(self.workspace_line)
            self.canvas.draw()
        except Exception:
            pass
        self.fcapp.ui.wplace_label.setStyleSheet("")

    def graph_event_connect(self, event_name, callback):
        """
        Attach an event handler to the canvas through the Matplotlib interface.

        :param event_name: Name of the event
        :type event_name: str
        :param callback: Function to call
        :type callback: func
        :return: Connection id
        :rtype: int
        """
        if event_name == 'mouse_move':
            event_name = 'motion_notify_event'
        if event_name == 'mouse_press':
            event_name = 'button_press_event'
        if event_name == 'mouse_release':
            event_name = 'button_release_event'
        if event_name == 'mouse_double_click':
            return self.double_click.connect(callback)

        if event_name == 'key_press':
            event_name = 'key_press_event'

        return self.canvas.mpl_connect(event_name, callback)

    def graph_event_disconnect(self, cid):
        """
        Disconnect callback with the give id.
        :param cid: Callback id.
        :return: None
        """

        self.canvas.mpl_disconnect(cid)

    def on_new_screen(self):
        pass
        # log.debug("Cache updated the screen!")

    def new_cursor(self, axes=None, big=None):
        # if axes is None:
        #     c = MplCursor(axes=self.axes, color='black', linewidth=1)
        # else:
        #     c = MplCursor(axes=axes, color='black', linewidth=1)

        if self.app.defaults["global_cursor_color_enabled"]:
            color = self.app.defaults["global_cursor_color"]
        else:
            if self.app.defaults['global_theme'] == 'white':
                color = '#000000'
            else:
                color = '#FFFFFF'

        if big is True:
            self.big_cursor = True
            self.ch_line = self.axes.axhline(color=color, linewidth=self.app.defaults["global_cursor_width"])
            self.cv_line = self.axes.axvline(color=color, linewidth=self.app.defaults["global_cursor_width"])
            self.big_cursor_isdisabled = False
        else:
            self.big_cursor = False

        c = FakeCursor()
        c.mouse_state_updated.connect(self.clear_cursor)

        return c

    def draw_cursor(self, x_pos, y_pos, color=None):
        """
        Draw a cursor at the mouse grid snapped position

        :param x_pos: mouse x position
        :param y_pos: mouse y position
        :param color: custom color of the mouse
        :return:
        """

        # there is no point in drawing mouse cursor when panning as it jumps in a confusing way
        if self.app.app_cursor.enabled is True and self.panning is False:
            if color:
                color = color
            else:
                if self.app.defaults['global_theme'] == 'white':
                    color = '#000000'
                else:
                    color = '#FFFFFF'

            if self.big_cursor is False:
                try:
                    x, y = self.snap(x_pos, y_pos)

                    # Pointer (snapped)
                    # The size of the cursor is multiplied by 1.65 because that value made the cursor similar with the
                    # one in the OpenGL(3D) graphic engine
                    pointer_size = int(float(self.app.defaults["global_cursor_size"]) * 1.65)
                    elements = self.axes.plot(x, y, '+', color=color, ms=pointer_size,
                                              mew=self.app.defaults["global_cursor_width"], animated=True)
                    for el in elements:
                        self.axes.draw_artist(el)
                except Exception as e:
                    # this happen at app initialization since self.app.geo_editor does not exist yet
                    # I could reshuffle the object instantiating order but what's the point?
                    # I could crash something else and that's pythonic, too
                    log.debug("PlotCanvasLegacy.draw_cursor() big_cursor is False --> %s" % str(e))
            else:
                try:
                    self.ch_line.set_markeredgewidth(self.app.defaults["global_cursor_width"])
                    self.cv_line.set_markeredgewidth(self.app.defaults["global_cursor_width"])
                except Exception:
                    pass

                try:
                    x, y = self.app.geo_editor.snap(x_pos, y_pos)
                    self.ch_line.set_ydata(y)
                    self.cv_line.set_xdata(x)
                except Exception:
                    # this happen at app initialization since self.app.geo_editor does not exist yet
                    # I could reshuffle the object instantiating order but what's the point?
                    # I could crash something else and that's pythonic, too
                    pass
                self.canvas.draw_idle()

            self.canvas.blit(self.axes.bbox)

    def clear_cursor(self, state):
        if state is True:
            if self.big_cursor is True and self.big_cursor_isdisabled is True:
                if self.app.defaults["global_cursor_color_enabled"]:
                    color = self.app.defaults["global_cursor_color"]
                else:
                    if self.app.defaults['global_theme'] == 'white':
                        color = '#000000'
                    else:
                        color = '#FFFFFF'

                self.ch_line = self.axes.axhline(color=color, linewidth=self.app.defaults["global_cursor_width"])
                self.cv_line = self.axes.axvline(color=color, linewidth=self.app.defaults["global_cursor_width"])
                self.big_cursor_isdisabled = False
            if self.app.defaults["global_cursor_color_enabled"] is True:
                self.draw_cursor(x_pos=self.mouse[0], y_pos=self.mouse[1], color=self.app.cursor_color_3D)
            else:
                self.draw_cursor(x_pos=self.mouse[0], y_pos=self.mouse[1])
        else:
            if self.big_cursor is True:
                self.big_cursor_isdisabled = True
                try:
                    self.ch_line.remove()
                    self.cv_line.remove()
                    self.canvas.draw_idle()
                except Exception as e:
                    log.debug("PlotCanvasLegacy.clear_cursor() big_cursor is True --> %s" % str(e))
            self.canvas.restore_region(self.background)
            self.canvas.blit(self.axes.bbox)

    def on_key_down(self, event):
        """

        :param event:
        :return:
        """
        log.debug('on_key_down(): ' + str(event.key))
        self.key = event.key

    def on_key_up(self, event):
        """

        :param event:
        :return:
        """
        self.key = None

    def connect(self, event_name, callback):
        """
        Attach an event handler to the canvas through the native Qt interface.

        :param event_name: Name of the event
        :type event_name: str
        :param callback: Function to call
        :type callback: function
        :return: Nothing
        """
        self.canvas.connect(event_name, callback)

    def clear(self):
        """
        Clears axes and figure.

        :return: None
        """

        # Clear
        self.axes.cla()
        try:
            self.figure.clf()
        except KeyError:
            log.warning("KeyError in MPL figure.clf()")

        # Re-build
        self.figure.add_axes(self.axes)
        self.axes.set_aspect(1)
        self.axes.grid(True)
        self.axes.axhline(color=(0.70, 0.3, 0.3), linewidth=2)
        self.axes.axvline(color=(0.70, 0.3, 0.3), linewidth=2)

        self.adjust_axes(-10, -10, 100, 100)

        # Re-draw
        self.canvas.draw_idle()

    def redraw(self):
        """
        Created only to serve for compatibility with the VisPy plotcanvas (the other graphic engine, 3D)
        :return:
        """
        self.clear()

    def adjust_axes(self, xmin, ymin, xmax, ymax):
        """
        Adjusts all axes while maintaining the use of the whole canvas
        and an aspect ratio to 1:1 between x and y axes. The parameters are an original
        request that will be modified to fit these restrictions.

        :param xmin: Requested minimum value for the X axis.
        :type xmin: float
        :param ymin: Requested minimum value for the Y axis.
        :type ymin: float
        :param xmax: Requested maximum value for the X axis.
        :type xmax: float
        :param ymax: Requested maximum value for the Y axis.
        :type ymax: float
        :return: None
        """

        # FlatCAMApp.App.log.debug("PC.adjust_axes()")

        if not self.app.collection.get_list():
            xmin = -10
            ymin = -10
            xmax = 100
            ymax = 100

        width = xmax - xmin
        height = ymax - ymin
        try:
            r = width / height
        except ZeroDivisionError:
            log.error("Height is %f" % height)
            return
        canvas_w, canvas_h = self.canvas.get_width_height()
        canvas_r = float(canvas_w) / canvas_h
        x_ratio = float(self.x_margin) / canvas_w
        y_ratio = float(self.y_margin) / canvas_h

        if r > canvas_r:
            ycenter = (ymin + ymax) / 2.0
            newheight = height * r / canvas_r
            ymin = ycenter - newheight / 2.0
            ymax = ycenter + newheight / 2.0
        else:
            xcenter = (xmax + xmin) / 2.0
            newwidth = width * canvas_r / r
            xmin = xcenter - newwidth / 2.0
            xmax = xcenter + newwidth / 2.0

        # Adjust axes
        for ax in self.figure.get_axes():
            if ax._label != 'base':
                ax.set_frame_on(False)  # No frame
                ax.set_xticks([])  # No tick
                ax.set_yticks([])  # No ticks
                ax.patch.set_visible(False)  # No background
                ax.set_aspect(1)
            ax.set_xlim((xmin, xmax))
            ax.set_ylim((ymin, ymax))
            ax.set_position([x_ratio, y_ratio, 1 - 2 * x_ratio, 1 - 2 * y_ratio])

        # Sync re-draw to proper paint on form resize
        self.canvas.draw()

        # #### Temporary place-holder for cached update #####
        self.update_screen_request.emit([0, 0, 0, 0, 0])

    def auto_adjust_axes(self, *args):
        """
        Calls ``adjust_axes()`` using the extents of the base axes.

        :rtype : None
        :return: None
        """

        xmin, xmax = self.axes.get_xlim()
        ymin, ymax = self.axes.get_ylim()
        self.adjust_axes(xmin, ymin, xmax, ymax)

    def fit_view(self):
        self.auto_adjust_axes()

    def fit_center(self, loc, rect=None):
        x = loc[0]
        y = loc[1]

        xmin, xmax = self.axes.get_xlim()
        ymin, ymax = self.axes.get_ylim()
        half_width = (xmax - xmin) / 2
        half_height = (ymax - ymin) / 2

        # Adjust axes
        for ax in self.figure.get_axes():
            ax.set_xlim((x - half_width, x + half_width))
            ax.set_ylim((y - half_height, y + half_height))

        # Re-draw
        self.canvas.draw()

        # #### Temporary place-holder for cached update #####
        self.update_screen_request.emit([0, 0, 0, 0, 0])

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

        factor = 1 / factor

        xmin, xmax = self.axes.get_xlim()
        ymin, ymax = self.axes.get_ylim()

        width = xmax - xmin
        height = ymax - ymin

        if center is None or center == [None, None]:
            center = [(xmin + xmax) / 2.0, (ymin + ymax) / 2.0]

        # For keeping the point at the pointer location
        relx = (xmax - center[0]) / width
        rely = (ymax - center[1]) / height

        new_width = width / factor
        new_height = height / factor

        xmin = center[0] - new_width * (1 - relx)
        xmax = center[0] + new_width * relx
        ymin = center[1] - new_height * (1 - rely)
        ymax = center[1] + new_height * rely

        # Adjust axes
        for ax in self.figure.get_axes():
            ax.set_xlim((xmin, xmax))
            ax.set_ylim((ymin, ymax))
        # Async re-draw
        self.canvas.draw_idle()

        # #### Temporary place-holder for cached update #####
        self.update_screen_request.emit([0, 0, 0, 0, 0])

    def pan(self, x, y, idle=True):
        xmin, xmax = self.axes.get_xlim()
        ymin, ymax = self.axes.get_ylim()
        width = xmax - xmin
        height = ymax - ymin

        # Adjust axes
        for ax in self.figure.get_axes():
            ax.set_xlim((xmin + x * width, xmax + x * width))
            ax.set_ylim((ymin + y * height, ymax + y * height))

        # Re-draw
        if idle:
            self.canvas.draw_idle()
        else:
            self.canvas.draw()

        # #### Temporary place-holder for cached update #####
        self.update_screen_request.emit([0, 0, 0, 0, 0])

    def new_axes(self, name):
        """
        Creates and returns an Axes object attached to this object's Figure.

        :param name: Unique label for the axes.
        :return: Axes attached to the figure.
        :rtype: Axes
        """
        new_ax = self.figure.add_axes([0.05, 0.05, 0.9, 0.9], label=name)
        return new_ax

    def remove_current_axes(self):
        """

        :return: The name of the deleted axes
        """

        axes_to_remove = self.figure.axes.gca()
        current_axes_name = deepcopy(axes_to_remove._label)
        self.figure.axes.remove(axes_to_remove)

        return current_axes_name

    def on_scroll(self, event):
        """
        Scroll event handler.

        :param event: Event object containing the event information.
        :return: None
        """

        # So it can receive key presses
        # self.canvas.grab_focus()
        self.canvas.setFocus()

        # Event info
        # z, direction = event.get_scroll_direction()

        if self.key is None:

            if event.button == 'up':
                self.zoom(1 / 1.5, self.mouse)
            else:
                self.zoom(1.5, self.mouse)
            return

        if self.key == 'shift':

            if event.button == 'up':
                self.pan(0.3, 0)
            else:
                self.pan(-0.3, 0)
            return

        if self.key == 'control':

            if event.button == 'up':
                self.pan(0, 0.3)
            else:
                self.pan(0, -0.3)
            return

    def on_mouse_press(self, event):

        self.is_dragging = True
        self.mouse_press_pos = (event.x, event.y)

        # Check for middle mouse button press
        if self.app.defaults["global_pan_button"] == '2':
            pan_button = 3  # right button for Matplotlib
        else:
            pan_button = 2  # middle button for Matplotlib

        if event.button == pan_button:
            # Prepare axes for pan (using 'matplotlib' pan function)
            self.pan_axes = []
            for a in self.figure.get_axes():
                if (event.x is not None and event.y is not None and a.in_axes(event) and
                        a.get_navigate() and a.can_pan()):
                    a.start_pan(event.x, event.y, 1)
                    self.pan_axes.append(a)

            # Set pan view flag
            if len(self.pan_axes) > 0:
                self.panning = True

        if event.dblclick:
            self.double_click.emit(event)

    def on_mouse_release(self, event):

        mouse_release_pos = (event.x, event.y)
        delta = 0.05

        if abs(self.distance(self.mouse_press_pos, mouse_release_pos)) < delta:
            self.is_dragging = False

        # Check for middle mouse button release to complete pan procedure
        # Check for middle mouse button press
        if self.app.defaults["global_pan_button"] == '2':
            pan_button = 3  # right button for Matplotlib
        else:
            pan_button = 2  # middle button for Matplotlib

        if event.button == pan_button:
            for a in self.pan_axes:
                a.end_pan()

            # Clear pan flag
            self.panning = False

            # And update the cursor
            if self.app.defaults["global_cursor_color_enabled"] is True:
                self.draw_cursor(x_pos=self.mouse[0], y_pos=self.mouse[1], color=self.app.cursor_color_3D)
            else:
                self.draw_cursor(x_pos=self.mouse[0], y_pos=self.mouse[1])

    def on_mouse_move(self, event):
        """
        Mouse movement event handler. Stores the coordinates. Updates view on pan.

        :param event: Contains information about the event.
        :return: None
        """

        try:
            x = float(event.xdata)
            y = float(event.ydata)
        except TypeError:
            return

        self.mouse = [event.xdata, event.ydata]

        self.canvas.restore_region(self.background)

        # Update pan view on mouse move
        if self.panning is True:
            for a in self.pan_axes:
                a.drag_pan(1, event.key, event.x, event.y)

            # x_pan, y_pan = self.app.geo_editor.snap(event.xdata, event.ydata)
            # self.draw_cursor(x_pos=x_pan, y_pos=y_pan)

            # Async re-draw (redraws only on thread idle state, uses timer on backend)
            self.canvas.draw_idle()

            # #### Temporary place-holder for cached update #####
            # self.update_screen_request.emit([0, 0, 0, 0, 0])

        if self.app.defaults["global_cursor_color_enabled"] is True:
            self.draw_cursor(x_pos=x, y_pos=y, color=self.app.cursor_color_3D)
        else:
            self.draw_cursor(x_pos=x, y_pos=y)
        # self.canvas.blit(self.axes.bbox)

    def translate_coords(self, position):
        """
        This does not do much. It's just for code compatibility

        :param position: Mouse event position
        :return: Tuple with mouse position
        """
        return position[0], position[1]

    def on_draw(self, renderer):

        # Store background on canvas redraw
        self.background = self.canvas.copy_from_bbox(self.axes.bbox)

    def get_axes_pixelsize(self):
        """
        Axes size in pixels.

        :return: Pixel width and height
        :rtype: tuple
        """
        bbox = self.axes.get_window_extent().transformed(self.figure.dpi_scale_trans.inverted())
        width, height = bbox.width, bbox.height
        width *= self.figure.dpi
        height *= self.figure.dpi
        return width, height

    def get_density(self):
        """
        Returns unit length per pixel on horizontal
        and vertical axes.

        :return: X and Y density
        :rtype: tuple
        """
        xpx, ypx = self.get_axes_pixelsize()

        xmin, xmax = self.axes.get_xlim()
        ymin, ymax = self.axes.get_ylim()
        width = xmax - xmin
        height = ymax - ymin

        return width / xpx, height / ypx

    def snap(self, x, y):
        """
        Adjusts coordinates to snap settings.

        :param x: Input coordinate X
        :param y: Input coordinate Y
        :return: Snapped (x, y)
        """

        snap_x, snap_y = (x, y)
        snap_distance = np.Inf

        # ### Grid snap
        if self.app.grid_status():
            if self.app.defaults["global_gridx"] != 0:
                try:
                    snap_x_ = round(x / float(self.app.defaults["global_gridx"])) * \
                              float(self.app.defaults["global_gridx"])
                except TypeError:
                    snap_x_ = x
            else:
                snap_x_ = x

            # If the Grid_gap_linked on Grid Toolbar is checked then the snap distance on GridY entry will be ignored
            # and it will use the snap distance from GridX entry
            if self.app.ui.grid_gap_link_cb.isChecked():
                if self.app.defaults["global_gridx"] != 0:
                    try:
                        snap_y_ = round(y / float(self.app.defaults["global_gridx"])) * \
                                  float(self.app.defaults["global_gridx"])
                    except TypeError:
                        snap_y_ = y
                else:
                    snap_y_ = y
            else:
                if self.app.defaults["global_gridy"] != 0:
                    try:
                        snap_y_ = round(y / float(self.app.defaults["global_gridy"])) * \
                                  float(self.app.defaults["global_gridy"])
                    except TypeError:
                        snap_y_ = y
                else:
                    snap_y_ = y
            nearest_grid_distance = self.distance((x, y), (snap_x_, snap_y_))
            if nearest_grid_distance < snap_distance:
                snap_x, snap_y = (snap_x_, snap_y_)

        return snap_x, snap_y

    @staticmethod
    def distance(pt1, pt2):
        return np.sqrt((pt1[0] - pt2[0]) ** 2 + (pt1[1] - pt2[1]) ** 2)


class FakeCursor(QtCore.QObject):
    """
    This is a fake cursor to ensure compatibility with the OpenGL engine (VisPy).
    This way I don't have to chane (disable) things related to the cursor all over when
    using the low performance Matplotlib 2D graphic engine.
    """

    mouse_state_updated = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self._enabled = True

    @property
    def enabled(self):
        return True if self._enabled else False

    @enabled.setter
    def enabled(self, value):
        self._enabled = value
        self.mouse_state_updated.emit(value)

    def set_data(self, pos, **kwargs):
        """Internal event handler to draw the cursor when the mouse moves."""
        return


class ShapeCollectionLegacy:
    """
    This will create the axes for each collection of shapes and will also
    hold the collection of shapes into a dict self._shapes.
    This handles the shapes redraw on canvas.
    """
    def __init__(self, obj, app, name=None, annotation_job=None, linewidth=1):
        """

        :param obj:             This is the object to which the shapes collection is attached and for
                                which it will have to draw shapes
        :param app:             This is the FLatCAM.App usually, needed because we have to access attributes there
        :param name:            This is the name given to the Matplotlib axes; it needs to be unique due of
                                Matplotlib requurements
        :param annotation_job:  Make this True if the job needed is just for annotation
        :param linewidth:       THe width of the line (outline where is the case)
        """
        self.obj = obj
        self.app = app
        self.annotation_job = annotation_job

        self._shapes = {}
        self.shape_dict = {}
        self.shape_id = 0

        self._color = None
        self._face_color = None
        self._visible = True
        self._update = False
        self._alpha = None
        self._tool_tolerance = None
        self._tooldia = None

        self._obj = None
        self._gcode_parsed = None

        self._linewidth = linewidth

        if name is None:
            axes_name = self.obj.options['name']
        else:
            axes_name = name

        # Axes must exist and be attached to canvas.
        if axes_name not in self.app.plotcanvas.figure.axes:
            self.axes = self.app.plotcanvas.new_axes(axes_name)

    def add(self, shape=None, color=None, face_color=None, alpha=None, visible=True,
            update=False, layer=1, tolerance=0.01, obj=None, gcode_parsed=None, tool_tolerance=None, tooldia=None,
            linewidth=None):
        """
        This function will add shapes to the shape collection

        :param shape: the Shapely shape to be added to the shape collection
        :param color: edge color of the shape, hex value
        :param face_color: the body color of the shape, hex value
        :param alpha: level of transparency of the shape [0.0 ... 1.0]; Float
        :param visible: if True will allow the shapes to be added
        :param update: not used; just for compatibility with VIsPy canvas
        :param layer: just for compatibility with VIsPy canvas
        :param tolerance: just for compatibility with VIsPy canvas
        :param obj: not used
        :param gcode_parsed: not used; just for compatibility with VIsPy canvas
        :param tool_tolerance: just for compatibility with VIsPy canvas
        :param tooldia:
        :param linewidth: the width of the line
        :return:
        """
        self._color = color if color is not None else "#006E20"
        # self._face_color = face_color if face_color is not None else "#BBF268"
        self._face_color = face_color

        if linewidth is None:
            line_width = self._linewidth
        else:
            line_width = linewidth

        if len(self._color) > 7:
            self._color = self._color[:7]

        if self._face_color is not None:
            if len(self._face_color) > 7:
                self._face_color = self._face_color[:7]
                # self._alpha = int(self._face_color[-2:], 16) / 255

        self._alpha = 0.75

        if alpha is not None:
            self._alpha = alpha

        self._visible = visible
        self._update = update

        # CNCJob object related arguments
        self._obj = obj
        self._gcode_parsed = gcode_parsed
        self._tool_tolerance = tool_tolerance
        self._tooldia = tooldia

        # if self._update:
        #     self.clear()

        try:
            for sh in shape:
                self.shape_id += 1
                self.shape_dict.update({
                    'color': self._color,
                    'face_color': self._face_color,
                    'linewidth': line_width,
                    'alpha': self._alpha,
                    'visible': self._visible,
                    'shape': sh
                })

                self._shapes.update({
                    self.shape_id: deepcopy(self.shape_dict)
                })
        except TypeError:
            self.shape_id += 1
            self.shape_dict.update({
                'color': self._color,
                'face_color': self._face_color,
                'linewidth': line_width,
                'alpha': self._alpha,
                'visible': self._visible,
                'shape': shape
            })

            self._shapes.update({
                self.shape_id: deepcopy(self.shape_dict)
            })

        return self.shape_id

    def remove(self, shape_id, update=None):
        for k in list(self._shapes.keys()):
            if shape_id == k:
                self._shapes.pop(k, None)

        if update is True:
            self.redraw()

    def clear(self, update=None):
        """
        Clear the canvas of the shapes.

        :param update:
        :return: None
        """
        self._shapes.clear()
        self.shape_id = 0

        self.axes.cla()
        try:
            self.app.plotcanvas.auto_adjust_axes()
        except Exception as e:
            log.debug("ShapeCollectionLegacy.clear() --> %s" % str(e))

        if update is True:
            self.redraw()

    def redraw(self, update_colors=None):
        """
        This draw the shapes in the shapes collection, on canvas

        :return: None
        """

        path_num = 0
        local_shapes = deepcopy(self._shapes)

        try:
            obj_type = self.obj.kind
        except AttributeError:
            obj_type = 'utility'

        # if we don't use this then when adding each new shape, the old ones will be added again, too
        # if obj_type == 'utility':
        #     self.axes.patches.clear()
        self.axes.patches.clear()

        for element in local_shapes:
            if local_shapes[element]['visible'] is True:
                if obj_type == 'excellon':
                    # Plot excellon (All polygons?)
                    if self.obj.options["solid"] and isinstance(local_shapes[element]['shape'], Polygon):
                        try:
                            patch = PolygonPatch(local_shapes[element]['shape'],
                                                 facecolor=local_shapes[element]['face_color'],
                                                 edgecolor=local_shapes[element]['color'],
                                                 alpha=local_shapes[element]['alpha'],
                                                 zorder=3,
                                                 linewidth=local_shapes[element]['linewidth']
                                                 )
                            self.axes.add_patch(patch)
                        except Exception as e:
                            log.debug("ShapeCollectionLegacy.redraw() excellon poly --> %s" % str(e))
                    else:
                        try:
                            if isinstance(local_shapes[element]['shape'], Polygon):
                                x, y = local_shapes[element]['shape'].exterior.coords.xy
                                self.axes.plot(x, y, 'r-', linewidth=local_shapes[element]['linewidth'])
                                for ints in local_shapes[element]['shape'].interiors:
                                    x, y = ints.coords.xy
                                    self.axes.plot(x, y, 'o-', linewidth=local_shapes[element]['linewidth'])
                            elif isinstance(local_shapes[element]['shape'], LinearRing):
                                x, y = local_shapes[element]['shape'].coords.xy
                                self.axes.plot(x, y, 'r-', linewidth=local_shapes[element]['linewidth'])
                        except Exception as e:
                            log.debug("ShapeCollectionLegacy.redraw() excellon no poly --> %s" % str(e))
                elif obj_type == 'geometry':
                    if type(local_shapes[element]['shape']) == Polygon:
                        try:
                            x, y = local_shapes[element]['shape'].exterior.coords.xy
                            self.axes.plot(x, y, local_shapes[element]['color'],
                                           linestyle='-',
                                           linewidth=local_shapes[element]['linewidth'])
                            for ints in local_shapes[element]['shape'].interiors:
                                x, y = ints.coords.xy
                                self.axes.plot(x, y, local_shapes[element]['color'],
                                               linestyle='-',
                                               linewidth=local_shapes[element]['linewidth'])
                        except Exception as e:
                            log.debug("ShapeCollectionLegacy.redraw() geometry poly --> %s" % str(e))
                    elif type(local_shapes[element]['shape']) == LineString or \
                            type(local_shapes[element]['shape']) == LinearRing:

                        try:
                            x, y = local_shapes[element]['shape'].coords.xy
                            self.axes.plot(x, y, local_shapes[element]['color'],
                                           linestyle='-',
                                           linewidth=local_shapes[element]['linewidth'])
                        except Exception as e:
                            log.debug("ShapeCollectionLegacy.redraw() geometry no poly --> %s" % str(e))
                elif obj_type == 'gerber':
                    if self.obj.options["multicolored"]:
                        linespec = '-'
                    else:
                        linespec = 'k-'

                    if self.obj.options["solid"]:
                        if update_colors:
                            gerber_fill_color = update_colors[0]
                            gerber_outline_color = update_colors[1]
                        else:
                            gerber_fill_color = local_shapes[element]['face_color']
                            gerber_outline_color = local_shapes[element]['color']

                        try:
                            patch = PolygonPatch(local_shapes[element]['shape'],
                                                 facecolor=gerber_fill_color,
                                                 edgecolor=gerber_outline_color,
                                                 alpha=local_shapes[element]['alpha'],
                                                 zorder=2,
                                                 linewidth=local_shapes[element]['linewidth'])
                            self.axes.add_patch(patch)
                        except AssertionError:
                            log.warning("A geometry component was not a polygon:")
                            log.warning(str(element))
                        except Exception as e:
                            log.debug(
                                "PlotCanvasLegacy.ShepeCollectionLegacy.redraw() gerber 'solid' --> %s" % str(e))
                    else:
                        try:
                            x, y = local_shapes[element]['shape'].exterior.xy
                            self.axes.plot(x, y, linespec, linewidth=local_shapes[element]['linewidth'])
                            for ints in local_shapes[element]['shape'].interiors:
                                x, y = ints.coords.xy
                                self.axes.plot(x, y, linespec, linewidth=local_shapes[element]['linewidth'])
                        except Exception as e:
                            log.debug("ShapeCollectionLegacy.redraw() gerber no 'solid' --> %s" % str(e))
                elif obj_type == 'cncjob':

                    if local_shapes[element]['face_color'] is None:
                        try:
                            linespec = '--'
                            linecolor = local_shapes[element]['color']
                            # if geo['kind'][0] == 'C':
                            #     linespec = 'k-'
                            x, y = local_shapes[element]['shape'].coords.xy
                            self.axes.plot(x, y, linespec, color=linecolor,
                                           linewidth=local_shapes[element]['linewidth'])
                        except Exception as e:
                            log.debug("ShapeCollectionLegacy.redraw() cncjob with face_color --> %s" % str(e))
                    else:
                        try:
                            path_num += 1
                            if self.obj.ui.annotation_cb.get_value():
                                if isinstance(local_shapes[element]['shape'], Polygon):
                                    self.axes.annotate(
                                        str(path_num),
                                        xy=local_shapes[element]['shape'].exterior.coords[0],
                                        xycoords='data', fontsize=20)
                                else:
                                    self.axes.annotate(
                                        str(path_num),
                                        xy=local_shapes[element]['shape'].coords[0],
                                        xycoords='data', fontsize=20)

                            patch = PolygonPatch(local_shapes[element]['shape'],
                                                 facecolor=local_shapes[element]['face_color'],
                                                 edgecolor=local_shapes[element]['color'],
                                                 alpha=local_shapes[element]['alpha'], zorder=2,
                                                 linewidth=local_shapes[element]['linewidth'])
                            self.axes.add_patch(patch)
                        except Exception as e:
                            log.debug("ShapeCollectionLegacy.redraw() cncjob no face_color --> %s" % str(e))
                elif obj_type == 'utility':
                    # not a FlatCAM object, must be utility
                    if local_shapes[element]['face_color']:
                        try:
                            patch = PolygonPatch(local_shapes[element]['shape'],
                                                 facecolor=local_shapes[element]['face_color'],
                                                 edgecolor=local_shapes[element]['color'],
                                                 alpha=local_shapes[element]['alpha'],
                                                 zorder=2,
                                                 linewidth=local_shapes[element]['linewidth'])

                            self.axes.add_patch(patch)
                        except Exception as e:
                            log.debug("ShapeCollectionLegacy.redraw() utility poly with face_color --> %s" % str(e))
                    else:
                        if isinstance(local_shapes[element]['shape'], Polygon):
                            try:
                                ext_shape = local_shapes[element]['shape'].exterior
                                if ext_shape is not None:
                                    x, y = ext_shape.xy
                                    self.axes.plot(x, y, local_shapes[element]['color'], linestyle='-',
                                                   linewidth=local_shapes[element]['linewidth'])
                                for ints in local_shapes[element]['shape'].interiors:
                                    if ints is not None:
                                        x, y = ints.coords.xy
                                        self.axes.plot(x, y, local_shapes[element]['color'], linestyle='-',
                                                       linewidth=local_shapes[element]['linewidth'])
                            except Exception as e:
                                log.debug("ShapeCollectionLegacy.redraw() utility poly no face_color --> %s" % str(e))
                        else:
                            try:
                                if local_shapes[element]['shape'] is not None:
                                    x, y = local_shapes[element]['shape'].coords.xy
                                    self.axes.plot(x, y, local_shapes[element]['color'], linestyle='-',
                                                   linewidth=local_shapes[element]['linewidth'])
                            except Exception as e:
                                log.debug("ShapeCollectionLegacy.redraw() utility lines no face_color --> %s" % str(e))
        self.app.plotcanvas.auto_adjust_axes()

    def set(self, text, pos, visible=True, font_size=16, color=None):
        """
        This will set annotations on the canvas.

        :param text: a list of text elements to be used as annotations
        :param pos: a list of positions for showing the text elements above
        :param visible: if True will display annotations, if False will clear them on canvas
        :param font_size: the font size or the annotations
        :param color: color of the annotations
        :return: None
        """
        if color is None:
            color = "#000000FF"

        if visible is not True:
            self.clear()
            return

        if len(text) != len(pos):
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Could not annotate due of a difference between the number "
                                                        "of text elements and the number of text positions."))
            return

        for idx in range(len(text)):
            try:
                self.axes.annotate(text[idx], xy=pos[idx], xycoords='data', fontsize=font_size, color=color)
            except Exception as e:
                log.debug("ShapeCollectionLegacy.set() --> %s" % str(e))

        self.app.plotcanvas.auto_adjust_axes()

    @property
    def visible(self):
        return self._visible

    @visible.setter
    def visible(self, value):
        if value is False:
            self.axes.cla()
            self.app.plotcanvas.auto_adjust_axes()
        else:
            if self._visible is False:
                self.redraw()
        self._visible = value

    def update_visibility(self, state, indexes=None):
        if indexes:
            for i in indexes:
                if i in self._shapes:
                    self._shapes[i]['visible'] = state
        else:
            for i in self._shapes:
                self._shapes[i]['visible'] = state

        self.redraw()

    @property
    def enabled(self):
        return self._visible

    @enabled.setter
    def enabled(self, value):
        if value is False:
            self.axes.cla()
            self.app.plotcanvas.auto_adjust_axes()
        else:
            if self._visible is False:
                self.redraw()
        self._visible = value

# class MplCursor(Cursor):
#     """
#     Unfortunately this gets attached to the current axes and if a new axes is added
#     it will not be showed until that axes is deleted.
#     Not the kind of behavior needed here so I don't use it anymore.
#     """
#     def __init__(self, axes, color='red', linewidth=1):
#
#         super().__init__(ax=axes, useblit=True, color=color, linewidth=linewidth)
#         self._enabled = True
#
#         self.axes = axes
#         self.color = color
#         self.linewidth = linewidth
#
#         self.x = None
#         self.y = None
#
#     @property
#     def enabled(self):
#         return True if self._enabled else False
#
#     @enabled.setter
#     def enabled(self, value):
#         self._enabled = value
#         self.visible = self._enabled
#         self.canvas.draw()
#
#     def onmove(self, event):
#         pass
#
#     def set_data(self, event, pos):
#         """Internal event handler to draw the cursor when the mouse moves."""
#         self.x = pos[0]
#         self.y = pos[1]
#
#         if self.ignore(event):
#             return
#         if not self.canvas.widgetlock.available(self):
#             return
#         if event.inaxes != self.ax:
#             self.linev.set_visible(False)
#             self.lineh.set_visible(False)
#
#             if self.needclear:
#                 self.canvas.draw()
#                 self.needclear = False
#             return
#         self.needclear = True
#         if not self.visible:
#             return
#         self.linev.set_xdata((self.x, self.x))
#
#         self.lineh.set_ydata((self.y, self.y))
#         self.linev.set_visible(self.visible and self.vertOn)
#         self.lineh.set_visible(self.visible and self.horizOn)
#
#         self._update()
