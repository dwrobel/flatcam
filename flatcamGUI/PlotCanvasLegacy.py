############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://caram.cl/software/flatcam                         #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
# Modified by Marius Stanciu 09/21/2019                    #
############################################################

from PyQt5 import QtGui, QtCore, QtWidgets

# Prevent conflict with Qt5 and above.
from matplotlib import use as mpl_use

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.widgets import Cursor

# needed for legacy mode
# Used for solid polygons in Matplotlib
from descartes.patch import PolygonPatch

from shapely.geometry import Polygon, LineString, LinearRing, Point, MultiPolygon, MultiLineString

import FlatCAMApp
from copy import deepcopy
import logging

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

mpl_use("Qt5Agg")
log = logging.getLogger('base')


class CanvasCache(QtCore.QObject):
    """

    Case story #1:

    1) No objects in the project.
    2) Object is created (new_object() emits object_created(obj)).
       on_object_created() adds (i) object to collection and emits
       (ii) new_object_available() then calls (iii) object.plot()
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

        self.canvas = FigureCanvasAgg(self.figure)

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

    # def on_new_object_available(self):
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

        # Options
        self.x_margin = 15  # pixels
        self.y_margin = 25  # Pixels

        # Parent container
        self.container = container

        # Plots go onto a single matplotlib.figure
        self.figure = Figure(dpi=50)  # TODO: dpi needed?
        self.figure.patch.set_visible(False)

        # These axes show the ticks and grid. No plotting done here.
        # New axes must have a label, otherwise mpl returns an existing one.
        self.axes = self.figure.add_axes([0.05, 0.05, 0.9, 0.9], label="base", alpha=0.0)
        self.axes.set_aspect(1)
        self.axes.grid(True)
        self.axes.axhline(color=(0.70, 0.3, 0.3), linewidth=2)
        self.axes.axvline(color=(0.70, 0.3, 0.3), linewidth=2)

        # The canvas is the top level container (FigureCanvasQTAgg)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.canvas.setFocus()
        self.native = self.canvas

        self.adjust_axes(-10, -10, 100, 100)
        # self.canvas.set_can_focus(True)  # For key press

        # Attach to parent
        # self.container.attach(self.canvas, 0, 0, 600, 400)  # TODO: Height and width are num. columns??
        self.container.addWidget(self.canvas)  # Qt

        # Copy a bitmap of the canvas for quick animation.
        # Update every time the canvas is re-drawn.
        self.background = self.canvas.copy_from_bbox(self.axes.bbox)

        # ## Bitmap Cache
        self.cache = CanvasCache(self, self.app)
        self.cache_thread = QtCore.QThread()
        self.cache.moveToThread(self.cache_thread)
        # super(PlotCanvas, self).connect(self.cache_thread, QtCore.SIGNAL("started()"), self.cache.run)
        self.cache_thread.started.connect(self.cache.run)

        self.cache_thread.start()
        self.cache.new_screen.connect(self.on_new_screen)

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

        self.mouse = [0, 0]
        self.key = None

        self.pan_axes = []
        self.panning = False

        # signal is the mouse is dragging
        self.is_dragging = False

        # signal if there is a doubleclick
        self.is_dblclk = False

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

        # self.double_click.disconnect(cid)

        self.canvas.mpl_disconnect(cid)

    def on_new_screen(self):
        pass
        # log.debug("Cache updated the screen!")

    def new_cursor(self, axes=None):
        # if axes is None:
        #     c = MplCursor(axes=self.axes, color='black', linewidth=1)
        # else:
        #     c = MplCursor(axes=axes, color='black', linewidth=1)

        c = FakeCursor()

        return c

    def on_key_down(self, event):
        """

        :param event:
        :return:
        """
        FlatCAMApp.App.log.debug('on_key_down(): ' + str(event.key))
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
            FlatCAMApp.App.log.warning("KeyError in MPL figure.clf()")

        # Re-build
        self.figure.add_axes(self.axes)
        self.axes.set_aspect(1)
        self.axes.grid(True)

        # Re-draw
        self.canvas.draw_idle()

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

        width = xmax - xmin
        height = ymax - ymin
        try:
            r = width / height
        except ZeroDivisionError:
            FlatCAMApp.App.log.error("Height is %f" % height)
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

    def pan(self, x, y):
        xmin, xmax = self.axes.get_xlim()
        ymin, ymax = self.axes.get_ylim()
        width = xmax - xmin
        height = ymax - ymin

        # Adjust axes
        for ax in self.figure.get_axes():
            ax.set_xlim((xmin + x * width, xmax + x * width))
            ax.set_ylim((ymin + y * height, ymax + y * height))

        # Re-draw
        self.canvas.draw_idle()

        # #### Temporary place-holder for cached update #####
        self.update_screen_request.emit([0, 0, 0, 0, 0])

    def new_axes(self, name):
        """
        Creates and returns an Axes object attached to this object's Figure.

        :param name: Unique label for the axes.
        :return: Axes attached to the figure.
        :rtype: Axes
        """

        return self.figure.add_axes([0.05, 0.05, 0.9, 0.9], label=name)

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

    def on_mouse_move(self, event):
        """
        Mouse movement event hadler. Stores the coordinates. Updates view on pan.

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
            # x_pan, y_pan = self.app.geo_editor.snap(event.xdata, event.ydata)
            # self.app.app_cursor.set_data(event, (x_pan, y_pan))
            for a in self.pan_axes:
                a.drag_pan(1, event.key, event.x, event.y)

            # Async re-draw (redraws only on thread idle state, uses timer on backend)
            self.canvas.draw_idle()

            # #### Temporary place-holder for cached update #####
            self.update_screen_request.emit([0, 0, 0, 0, 0])

        x, y = self.app.geo_editor.snap(x, y)
        if self.app.app_cursor.enabled is True:
            # Pointer (snapped)
            elements = self.axes.plot(x, y, 'k+', ms=40, mew=2, animated=True)
            for el in elements:
                self.axes.draw_artist(el)

        self.canvas.blit(self.axes.bbox)

    def translate_coords(self, position):
        """
        This does not do much. It's just for code compatibility

        :param position: Mouse event position
        :return: Tuple with mouse position
        """
        return (position[0], position[1])

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


class FakeCursor:
    """
    This is a fake cursor to ensure compatibility with the OpenGL engine (VisPy).
    This way I don't have to chane (disable) things related to the cursor all over when
    using the low performance Matplotlib 2D graphic engine.
    """
    def __init__(self):
        self._enabled = True

    @property
    def enabled(self):
        return True if self._enabled else False

    @enabled.setter
    def enabled(self, value):
        self._enabled = value

    def set_data(self, pos, **kwargs):
        """Internal event handler to draw the cursor when the mouse moves."""
        pass


class MplCursor(Cursor):
    """
    Unfortunately this gets attached to the current axes and if a new axes is added
    it will not be showed until that axes is deleted.
    Not the kind of behavior needed here so I don't use it anymore.
    """
    def __init__(self, axes, color='red', linewidth=1):

        super().__init__(ax=axes, useblit=True, color=color, linewidth=linewidth)
        self._enabled = True

        self.axes = axes
        self.color = color
        self.linewidth = linewidth

        self.x = None
        self.y = None

    @property
    def enabled(self):
        return True if self._enabled else False

    @enabled.setter
    def enabled(self, value):
        self._enabled = value
        self.visible = self._enabled
        self.canvas.draw()

    def onmove(self, event):
        pass

    def set_data(self, event, pos):
        """Internal event handler to draw the cursor when the mouse moves."""
        self.x = pos[0]
        self.y = pos[1]

        if self.ignore(event):
            return
        if not self.canvas.widgetlock.available(self):
            return
        if event.inaxes != self.ax:
            self.linev.set_visible(False)
            self.lineh.set_visible(False)

            if self.needclear:
                self.canvas.draw()
                self.needclear = False
            return
        self.needclear = True
        if not self.visible:
            return
        self.linev.set_xdata((self.x, self.x))

        self.lineh.set_ydata((self.y, self.y))
        self.linev.set_visible(self.visible and self.vertOn)
        self.lineh.set_visible(self.visible and self.horizOn)

        self._update()


class ShapeCollectionLegacy:
    """
    This will create the axes for each collection of shapes and will also
    hold the collection of shapes into a dict self._shapes.
    This handles the shapes redraw on canvas.
    """
    def __init__(self, obj, app, name=None, annotation_job=None):
        """

        :param obj: this is the object to which the shapes collection is attached and for
        which it will have to draw shapes
        :param app: this is the FLatCAM.App usually, needed because we have to access attributes there
        :param name: this is the name given to the Matplotlib axes; it needs to be unique due of Matplotlib requurements
        :param annotation_job: make this True if the job needed is just for annotation
        """
        self.obj = obj
        self.app = app
        self.annotation_job = annotation_job

        self._shapes = dict()
        self.shape_dict = dict()
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

        if name is None:
            axes_name = self.obj.options['name']
        else:
            axes_name = name

        # Axes must exist and be attached to canvas.
        if axes_name not in self.app.plotcanvas.figure.axes:
            self.axes = self.app.plotcanvas.new_axes(axes_name)

    def add(self, shape=None, color=None, face_color=None, alpha=None, visible=True,
            update=False, layer=1, tolerance=0.01, obj=None, gcode_parsed=None, tool_tolerance=None, tooldia=None):

        self._color = color[:-2] if color is not None else None
        self._face_color = face_color[:-2] if face_color is not None else None
        self._alpha = int(face_color[-2:], 16) / 255 if face_color is not None else 0.75

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
                    'alpha': self._alpha,
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
                'alpha': self._alpha,
                'shape': shape
            })

            self._shapes.update({
                self.shape_id: deepcopy(self.shape_dict)
            })

        return self.shape_id

    def clear(self, update=None):
        self._shapes.clear()
        self.shape_id = 0

        self.axes.cla()
        self.app.plotcanvas.auto_adjust_axes()

        if update is True:
            self.redraw()

    def redraw(self):
        path_num = 0
        local_shapes = deepcopy(self._shapes)

        try:
            obj_type = self.obj.kind
        except AttributeError:
            obj_type = 'utility'

        if self._visible:
            for element in local_shapes:
                if obj_type == 'excellon':
                    # Plot excellon (All polygons?)
                    if self.obj.options["solid"] and isinstance(local_shapes[element]['shape'], Polygon):
                        patch = PolygonPatch(local_shapes[element]['shape'],
                                             facecolor="#C40000",
                                             edgecolor="#750000",
                                             alpha=local_shapes[element]['alpha'],
                                             zorder=3)
                        self.axes.add_patch(patch)
                    else:
                        x, y = local_shapes[element]['shape'].exterior.coords.xy
                        self.axes.plot(x, y, 'r-')
                        for ints in local_shapes[element]['shape'].interiors:
                            x, y = ints.coords.xy
                            self.axes.plot(x, y, 'o-')
                elif obj_type == 'geometry':
                    if type(local_shapes[element]['shape']) == Polygon:
                        x, y = local_shapes[element]['shape'].exterior.coords.xy
                        self.axes.plot(x, y, local_shapes[element]['color'], linestyle='-')
                        for ints in local_shapes[element]['shape'].interiors:
                            x, y = ints.coords.xy
                            self.axes.plot(x, y, local_shapes[element]['color'], linestyle='-')
                    elif type(local_shapes[element]['shape']) == LineString or \
                            type(local_shapes[element]['shape']) == LinearRing:

                        x, y = local_shapes[element]['shape'].coords.xy
                        self.axes.plot(x, y, local_shapes[element]['color'], linestyle='-')

                elif obj_type == 'gerber':
                    if self.obj.options["multicolored"]:
                        linespec = '-'
                    else:
                        linespec = 'k-'

                    if self.obj.options["solid"]:
                        try:
                            patch = PolygonPatch(local_shapes[element]['shape'],
                                                 facecolor=local_shapes[element]['face_color'],
                                                 edgecolor=local_shapes[element]['color'],
                                                 alpha=local_shapes[element]['alpha'],
                                                 zorder=2)
                            self.axes.add_patch(patch)
                        except AssertionError:
                            FlatCAMApp.App.log.warning("A geometry component was not a polygon:")
                            FlatCAMApp.App.log.warning(str(element))
                    else:
                        x, y = local_shapes[element]['shape'].exterior.xy
                        self.axes.plot(x, y, linespec)
                        for ints in local_shapes[element]['shape'].interiors:
                            x, y = ints.coords.xy
                            self.axes.plot(x, y, linespec)
                elif obj_type == 'cncjob':

                    if local_shapes[element]['face_color'] is None:
                        linespec = '--'
                        linecolor = local_shapes[element]['color']
                        # if geo['kind'][0] == 'C':
                        #     linespec = 'k-'
                        x, y = local_shapes[element]['shape'].coords.xy
                        self.axes.plot(x, y, linespec, color=linecolor)
                    else:
                        path_num += 1
                        if isinstance(local_shapes[element]['shape'], Polygon):
                            self.axes.annotate(str(path_num), xy=local_shapes[element]['shape'].exterior.coords[0],
                                               xycoords='data', fontsize=20)
                        else:
                            self.axes.annotate(str(path_num), xy=local_shapes[element]['shape'].coords[0],
                                               xycoords='data', fontsize=20)

                        patch = PolygonPatch(local_shapes[element]['shape'],
                                             facecolor=local_shapes[element]['face_color'],
                                             edgecolor=local_shapes[element]['color'],
                                             alpha=local_shapes[element]['alpha'], zorder=2)
                        self.axes.add_patch(patch)
                elif obj_type == 'utility':
                    # not a FlatCAM object, must be utility
                    if local_shapes[element]['face_color']:
                        try:
                            patch = PolygonPatch(local_shapes[element]['shape'],
                                                 facecolor=local_shapes[element]['face_color'],
                                                 edgecolor=local_shapes[element]['color'],
                                                 alpha=local_shapes[element]['alpha'],
                                                 zorder=2)
                            self.axes.add_patch(patch)
                        except Exception as e:
                            log.debug("ShapeCollectionLegacy.redraw() --> %s" % str(e))
                    else:
                        if isinstance(local_shapes[element]['shape'], Polygon):
                            x, y = local_shapes[element]['shape'].exterior.xy
                            self.axes.plot(x, y, local_shapes[element]['color'], linestyle='-')
                            for ints in local_shapes[element]['shape'].interiors:
                                x, y = ints.coords.xy
                                self.axes.plot(x, y, local_shapes[element]['color'], linestyle='-')
                        else:
                            x, y = local_shapes[element]['shape'].coords.xy
                            self.axes.plot(x, y, local_shapes[element]['color'], linestyle='-')

        self.app.plotcanvas.auto_adjust_axes()

    def set(self, text, pos, visible=True, font_size=16, color=None):

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
