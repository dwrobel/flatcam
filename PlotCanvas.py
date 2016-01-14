############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://caram.cl/software/flatcam                         #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
############################################################

from __future__ import division
from PyQt4 import QtGui, QtCore

# Prevent conflict with Qt5 and above.
from matplotlib import use as mpl_use
mpl_use("Qt4Agg")

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_agg import FigureCanvasAgg
import FlatCAMApp
import logging
import numpy as np

# from FlatCAMApp import App
from ObjectCollection import ObjectCollection

log = logging.getLogger('base')


class RenderCache(QtCore.QObject):
    """
    Contains a series of bitmaps, each for a different
    zoom level, but all centered around the same coordinates.
    """

    render_ready = QtCore.pyqtSignal(object)

    def __init__(self, plotcanvas, min_zoom_cache=3, max_zoom_cache=6):

        # super(RenderCache, self).__init__()
        QtCore.QObject.__init__(self)

        self.plotcanvas = plotcanvas

        # Minimum number of zoom levels to store in cache
        # in each direction.
        self.min_zoom_cache = min_zoom_cache

        # Maximum number of zoom levels to store in cache in
        # any direction. If exceeded, the farthest zoom level
        # cache in the opposite direction is deleted.
        self.max_zoom_cache = max_zoom_cache

        # Minimum length in either axis that has to remain in
        # cache outside the visible plot before regenerating
        # the cache. Units is fraction of the visible area.
        self.cache_margin = 1.0

        # List of Render instances in contiguous order of zoom level.
        self.panes = []

        # Index of self.panes that is currently being used. (Visible)
        self.current_pane_index = None

        self.plotcanvas.renderer.new_render.connect(self.insert)

    def reset(self):
        self.panes = []
        self.current_pane_index = None

    # def start(self):
    #     log.debug("RenderCache.start()")

    def check(self):
        """
        Check cache contents for margin.
        """

        log.debug("RenderCache.check()")
        log.debug("len(self.panes)=%d" % len(self.panes))

        if self.plotcanvas.app.collection.count() == 0:  # TODO: Ugly referencing.
            log.debug("RenderCache.check(): Collection is empty. Quitting.")
            return

        if len(self.panes) == 0:
            self.plotcanvas.replot_request.emit(0)

        else:
            above = len(self.panes) - 1 - self.current_pane_index
            below = self.current_pane_index

            if above <= below and above < self.min_zoom_cache:
                new_idx = self.panes[-1].scale_index + 1
                log.debug("RenderCache: Requesting zoom level %d" % new_idx)
                self.plotcanvas.render_request.emit(new_idx)
                # TODO: delete excess cache

            elif below < above and below < self.min_zoom_cache:
                new_idx = self.panes[0].scale_index - 1
                log.debug("RenderCache: Requesting zoom level %d" % new_idx)
                self.plotcanvas.render_request.emit(new_idx)
                # TODO: delete excess cache

            else:
                log.debug("RenderCache: Cache complete.")

    def on_zoom(self, direction):
        """
        Callback for zoom event from PlotCanvas.
        """

        if not direction and len(self.panes) > self.current_pane_index + 1:
            log.debug("RenderCache.on_zoom(true): Render available immediately.")
            self.current_pane_index += 1
            self.render_ready.emit(self.panes[self.current_pane_index])
        elif direction and self.current_pane_index > 0:
            log.debug("RenderCache.on_zoom(true): Render available immediately.")
            self.current_pane_index -= 1
            self.render_ready.emit(self.panes[self.current_pane_index])
        else:
            log.debug("RenderCache.on_zoom(): Render available.")

        self.check()

    def on_pan(self, factor, center):
        pass

    def insert(self, render):
        """
        Renders must be inserted in contiguous order. A new
        render must be the next zoom level above the render
        with the highest zoom level in self.panes or the
        next zoom level below the lowest zoom level in
        self.panes
        """

        assert isinstance(render, Render)

        log.debug(self)

        log.debug("RenderCache.insert(): Received render " + str(render))

        log.debug("RenderCache: Inserting zoom level %d" % render.scale_index)

        if len(self.panes) == 0:
            self.panes = [render]
            self.current_pane_index = 0

            # The app is waiting for the render.

            self.render_ready.emit(render)
            log.debug("RenderCache.insert(): Emitting render_ready(render)")
        else:
            if render.resolution() < self.panes[0].resolution():
                self.panes.append(render)
            else:
                self.panes = [render] + self.panes
                self.current_pane_index += 1

        self.check()


class Render(QtCore.QObject):
    """
    Contains one bitmap and the extent of the image
    in user units.
    """

    def __init__(self, bitmap, extent, scale_index):
        # super(Render, self).__init__()
        QtCore.QObject.__init__(self)
        self.bitmap = bitmap
        self.extent = extent
        self.scale_index = scale_index

    def resolution(self):
        """
        Pixels per user units in both x and y axes.
        """
        hpx, wpx, _ = self.bitmap.shape
        w = self.extent[2] - self.extent[0]
        h = self.extent[3] - self.extent[1]
        return wpx / w, hpx / h


class Renderer(QtCore.QObject):
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
    new_render = QtCore.pyqtSignal(object)

    renderer_cleared = QtCore.pyqtSignal()

    def __init__(self, plotcanvas, app, dpi=50, zoom_ratio=1.5):

        # super(Renderer, self).__init__()
        QtCore.QObject.__init__(self)

        assert isinstance(plotcanvas, PlotCanvas)
        assert isinstance(app, FlatCAMApp.App)

        self.app = app
        self.plotcanvas = plotcanvas
        self.dpi = dpi
        self.zoom_ratio = zoom_ratio

        self.figure = Figure(figsize=(10, 10),
                             dpi=dpi,
                             facecolor='white',
                             frameon=False)

        # Each object has its own axes, indexed by the
        # object's id.
        self.obj_axes = {}

        self.canvas = FigureCanvasAgg(self.figure)

        self.render_size = 5

    def new_axes(self):
        axes = self.figure.add_axes([0.0, 0.0, 1.0, 1.0],
                                    # alpha=1.0,
                                    # frameon=False,
                                    # visible=False,
                                    # axis_bgcolor='white',
                                    # frame_on=False,
                                    # xticks=[],
                                    # yticks=[],
                                    # axisbelow=True
                                    )
        # axes.set_aspect(1)
        # axes.patch.set_visible(False)
        # axes.set_frame_on(False)
        # axes.set_xticks([])
        # axes.set_yticks([])
        axes.axis('off')

        return axes

    def run(self):

        log.debug("CanvasCache Thread Started!")

        self.plotcanvas.replot_request.connect(self.on_replot_request)
        self.plotcanvas.render_request.connect(self.render)

    # def on_new_object_available(self, obj):
    #
    #     log.debug("A new object is available. Should plot it!")
    #
    #     # Size of the visible plot area in pixels
    #     size_px = self.plotcanvas.get_axes_pixelsize()
    #
    #     # Size of the visible plot area in inches (image size)
    #     size_in = self.plotcanvas.figure.bbox_inches.size
    #
    #     # Size of the object in user units
    #     obj_bounds = obj.bounds()
    #
    #     # Add 10% margin
    #     width = obj_bounds[2] - obj_bounds[0]
    #     height = obj_bounds[3] - obj_bounds[1]
    #     new_bounds = [
    #         obj_bounds[0] - 0.1 * width,
    #         obj_bounds[1] - 0.1 * height,
    #         obj_bounds[2] + 0.1 * width,
    #         obj_bounds[3] + 0.1 * height
    #     ]
    #
    #     if len(self.app.collection.get_list()) == 1:
    #
    #         # Plot
    #         self.figure.set_size_inches(*size_in)
    #         self.obj_axes[id(obj)] = self.new_axes()
    #         obj.plot(self.obj_axes[id(obj)])
    #         self.set_lims(*new_bounds)
    #         self.canvas.draw()
    #
    #         # Rasterize
    #         buf = self.canvas.tostring_rgb()
    #         ncols, nrows = self.canvas.get_width_height()
    #         img = np.fromstring(buf, dtype=np.uint8).reshape(nrows, ncols, 3)
    #
    #         log.debug("Canvas rendered. Emiting signal.")
    #
    #         render = Render(img, new_bounds)
    #         render.moveToThread(QtGui.QApplication.instance().thread())
    #         self.new_render.emit(render)

    def set_lims(self, xmin, ymin, xmax, ymax):
        for key, axes in self.obj_axes.iteritems():
            axes.set_xlim(xmin, xmax)
            axes.set_ylim(ymin, ymax)

    def on_replot_request(self, collection):
        log.debug("Renderer.on_replot_request()")

        assert isinstance(collection, ObjectCollection)

        w_px, h_px = self.plotcanvas.get_axes_pixelsize()
        log.debug("Renderer.on_replot_request(): Visible Canvas size = %.1f %.1f [px]" % (w_px, h_px))
        log.debug("Renderer.on_replot_request(): Visible Canvas W/H = %.3f " % (w_px / h_px))

        self.figure.clear()  # Alias of clf()

        # Canvas width in pixels:
        # Wpx = self.render_size * w_px = self.dpi * Winches
        # Winches = self.render_size * w_px / self.dpi
        w_rfig = self.render_size * w_px / self.dpi
        h_rfig = self.render_size * h_px / self.dpi

        self.figure.set_size_inches(
            w_rfig,
            h_rfig
        )
        log.debug("Renderer.on_replot_request(): Resizing renderer figure to %.3f %.3f inches" % (w_rfig, h_rfig))

        # Plot all objects
        for obj in collection.get_list():

            # Axes
            self.obj_axes[id(obj)] = self.new_axes()

            # Plot
            obj.plot(self.obj_axes[id(obj)])

        self.render(scale_index=0)

    def render(self, scale_index=0):

        log.debug("Renderer.render(): Rendering level %d" % scale_index)

        # Set limits
        collection_bounds = self.app.collection.get_bounds()
        log.debug("Renderer.render(): Collection bounds = %.3f %.3f %.3f %.3f [user units]" % tuple(collection_bounds))

        collection_width = (collection_bounds[2] - collection_bounds[0])
        collection_height = (collection_bounds[3] - collection_bounds[1])
        log.debug("Renderer.render(): Collection size = %.3f %.3f [user units]" % (collection_width, collection_height))

        center_x = collection_bounds[0] + collection_width / 2
        center_y = collection_bounds[1] + collection_height / 2

        visual_bounds = [
            center_x - 1.1 * collection_width / 2,
            center_y - 1.1 * collection_height / 2,
            center_x + 1.1 * collection_width / 2,
            center_y + 1.1 * collection_height / 2
        ]

        render_bounds = self.plotcanvas.axes_limits_for_box(visual_bounds)
        render_width = render_bounds[2] - render_bounds[0]
        render_height = render_bounds[3] - render_bounds[1]

        render_bounds = [
            center_x - render_width / 2 * self.render_size * self.zoom_ratio ** scale_index,
            center_y - render_height / 2 * self.render_size * self.zoom_ratio ** scale_index,
            center_x + render_width / 2 * self.render_size * self.zoom_ratio ** scale_index,
            center_y + render_height / 2 * self.render_size * self.zoom_ratio ** scale_index
        ]
        render_width = render_bounds[2] - render_bounds[0]
        render_height = render_bounds[3] - render_bounds[1]

        log.debug("Renderer.render(): Render size = %.3f %.3f [user units]" % (render_width, render_height))

        self.set_lims(*render_bounds)

        # Draw
        self.canvas.draw()

        # Rasterize
        # buf = self.canvas.tostring_rgb()
        buf = self.canvas.buffer_rgba()
        ncols, nrows = self.canvas.get_width_height()
        img = np.fromstring(buf, dtype=np.uint8).reshape(nrows, ncols, 4)

        render = Render(img, render_bounds, scale_index)

        log.debug("Renderer.render(): Render Shape [px] = " + str(img.shape))
        log.debug("Renderer.render(): Resolution = %.3f %.3f" % render.resolution())

        render.moveToThread(QtGui.QApplication.instance().thread())

        log.debug("Renderer.render(): Canvas rendered. Emiting signal. Renderer.new_render(render)")
        self.new_render.emit(render)

    def on_object_deleted(self, obj):
        try:
            a = self.obj_axes[id(obj)]
            self.figure.delaxes(a)
            del a
        except IndexError:
            log.debug("ERROR: Axes not present in Renderer.")

    def clear(self):
        self.figure.clear()
        self.obj_axes = []
        self.canvas.draw()
        self.renderer_cleared.emit()


class PlotCanvas(QtCore.QObject):
    """
    Class handling the plotting area in the application.
    """

    # Signals:
    render_request = QtCore.pyqtSignal(int)
    replot_request = QtCore.pyqtSignal(object)
    zoom_change = QtCore.pyqtSignal(bool)
    # pan_change = QtCore.pyqtSignal(float, float, float, float)

    def __init__(self, container, app):
        """
        The constructor configures the Matplotlib figure that
        will contain all plots, creates the base axes and connects
        events to the plotting area.

        :param container: The parent container in which to draw plots.
        :rtype: PlotCanvas
        """

        # assert isinstance(app, FlatCAMApp.App)

        # super(PlotCanvas, self).__init__()
        QtCore.QObject.__init__(self)

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
        self.figure.set_snap(True)  # Snap vertices to the nearest pixel center.
        self.axes = self.figure.add_axes([0.05, 0.05, 0.9, 0.9],
                                         label="base", alpha=0.0)
        self.axes.set_aspect(1)
        self.axes.grid(True)

        # The canvas is the top level container (FigureCanvasQTAgg)
        self.canvas = FigureCanvas(self.figure)
        # self.canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
        # self.canvas.setFocus()

        #self.canvas.set_hexpand(1)
        #self.canvas.set_vexpand(1)
        #self.canvas.set_can_focus(True)  # For key press

        # Attach to parent
        #self.container.attach(self.canvas, 0, 0, 600, 400)  # TODO: Height and width are num. columns??
        self.container.addWidget(self.canvas)  # Qt

        # Copy a bitmap of the canvas for quick animation.
        # Update every time the canvas is re-drawn.
        self.background = self.canvas.copy_from_bbox(self.axes.bbox)

        ### Renderer
        self.renderer = Renderer(self, self.app)
        self.renderer_thread = QtCore.QThread()
        self.renderer.moveToThread(self.renderer_thread)
        super(PlotCanvas, self).connect(self.renderer_thread, QtCore.SIGNAL("started()"), self.renderer.run)
        # self.connect()

        # self.renderer.new_render.connect(self.on_new_render)

        ### Cache
        self.cache = RenderCache(self)
        log.debug("PlotCanvas.__init__(): [1] self.cache is " + str(self.cache))
        log.debug(self)
        self.zoom_change.connect(self.cache.on_zoom)
        # self.pan_change.connect(self.cache.on_pan)

        # Events
        self.canvas.mpl_connect('button_press_event', self.on_mouse_press)
        self.canvas.mpl_connect('button_release_event', self.on_mouse_release)
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        #self.canvas.connect('configure-event', self.auto_adjust_axes)
        self.canvas.mpl_connect('resize_event', self.auto_adjust_axes)
        #self.canvas.add_events(Gdk.EventMask.SMOOTH_SCROLL_MASK)
        #self.canvas.connect("scroll-event", self.on_scroll)
        self.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.canvas.mpl_connect('key_press_event', self.on_key_down)
        self.canvas.mpl_connect('key_release_event', self.on_key_up)
        self.canvas.mpl_connect('draw_event', self.on_draw)

        self.cache.render_ready.connect(self.on_new_render)

        self.mouse = [0, 0]
        self.key = None

        self.pan_axes = []
        self.panning = False

    def on_object_deleted(self):
        self.reset_cache()  # TODO: This will request a re-plot (unnecessary)

    def on_new_object(self, obj):
        log.debug("PlotCanvas: on_new_object(), resetting cache.")
        # self.replot_request.emit(self.app.collection)
        self.auto_adjust_axes()

        self.reset_cache()

        log.debug("PlotCanvas.one_new_object(): [3] self.cache is " + str(self.cache))
        log.debug(self)

    def start(self):
        log.debug("PlotCanvas.start()")
        log.debug("PlotCanvas.start(): [2] self.cache is " + str(self.cache))
        log.debug(self)

        self.app.collection.new_object_available.connect(self.on_new_object)
        self.app.collection.object_deleted.connect(self.on_object_deleted)
        self.renderer_thread.start()

    def on_new_render(self, render):

        extent = (render.extent[0], render.extent[2],
                  render.extent[1], render.extent[3])
        w = render.extent[2] - render.extent[0]
        h = render.extent[3] - render.extent[1]

        s = self.renderer.render_size

        log.debug("PlotCanvas.on_new_render(): extent = %.3f %.3f %.3f %.3f" % extent)
        log.debug("PlotCanvas.on_new_render(): scale_index = %.3f" % render.scale_index)
        log.debug("PlotCanvas.on_new_render(): shape = " + str(render.bitmap.shape))
        log.debug("PlotCanvas.on_new_render(): resolution = %.3f %.3f" % render.resolution())
        log.debug("PlotCanvas.on_new_render(): Screen resolution = %.3f %.3f" % self.get_resolution())

        # self.axes.cla()
        self.axes.imshow(render.bitmap, extent=extent, interpolation="nearest")

        # self.axes.set_xlim(
        #     render.extent[0] + w * (s - 1) / 2,
        #     render.extent[2] - w * (s - 1) / 2
        # )
        # self.axes.set_ylim(
        #     render.extent[1] + h * (s - 1) / 2,
        #     render.extent[3] - h * (s - 1) / 2
        # )
        self.canvas.draw_idle()

    def reset_cache(self):
        log.debug("PlotCanvas.reset_cache(): Resetting cache and clearing.")
        self.cache.reset()
        self.clear()
        self.auto_adjust_axes()
        self.replot_request.emit(self.app.collection)

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

    def mpl_connect(self, event_name, callback):
        """
        Attach an event handler to the canvas through the Matplotlib interface.

        :param event_name: Name of the event
        :type event_name: str
        :param callback: Function to call
        :type callback: func
        :return: Connection id
        :rtype: int
        """
        return self.canvas.mpl_connect(event_name, callback)

    def mpl_disconnect(self, cid):
        """
        Disconnect callback with the give id.
        :param cid: Callback id.
        :return: None
        """
        self.canvas.mpl_disconnect(cid)

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

    def axes_limits_for_box(self, box):

        x0, y0, x1, y1 = box
        w = x1 - x0
        h = y1 - y0
        r = w / h
        xcenter = (x0 + x1) / 2
        ycenter = (y0 + y1) / 2

        ax0, ax1 = self.axes.get_xlim()
        ay0, ay1 = self.axes.get_ylim()
        aw = ax1 - ax0
        ah = ay1 - ay0
        ar = aw / ah

        if r > ar:
            return x0, ycenter - ah / 2, x1, ycenter + ah / 2
        else:
            return xcenter - aw / 2, y0, xcenter + aw / 2, y1

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

    def auto_adjust_axes(self, *args):
        """
        Calls ``adjust_axes()`` using the extents of the base axes.

        :rtype : None
        :return: None
        """

        xmin, xmax = self.axes.get_xlim()
        ymin, ymax = self.axes.get_ylim()
        self.adjust_axes(xmin, ymin, xmax, ymax)

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

        self.axes.cla()
        self.axes.grid()

        # Adjust axes
        for ax in self.figure.get_axes():
            ax.set_xlim((xmin, xmax))
            ax.set_ylim((ymin, ymax))

        # Async re-draw
        # self.canvas.draw_idle()

        # Signal that the zoom level has changed.
        # Cache should signal when the new zoom level image is ready.
        self.zoom_change.emit(factor > 1)

    def pan(self, x, y):
        xmin, xmax = self.axes.get_xlim()
        ymin, ymax = self.axes.get_ylim()
        width = xmax - xmin
        height = ymax - ymin

        # New extents
        xmin = xmin + x * width
        xmax = xmax + x * width
        ymin = ymin + y * height
        ymax = ymax + y * height

        # Adjust axes
        for ax in self.figure.get_axes():
            ax.set_xlim((xmin, xmax))
            ax.set_ylim((ymin, ymax))

        # Re-draw
        self.canvas.draw_idle()

        # Signal that the extents have changed
        # Cache should signal if a new bitmap has been computed.
        self.pan_change.emit(xmin, ymin, xmax, ymax)

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
                self.zoom(1.5, self.mouse)
            else:
                self.zoom(1 / 1.5, self.mouse)
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

        # Check for middle mouse button press
        if event.button == 2:

            # Prepare axes for pan (using 'matplotlib' pan function)
            self.pan_axes = []
            for a in self.figure.get_axes():
                if (event.x is not None and event.y is not None and a.in_axes(event) and
                        a.get_navigate() and a.can_pan()):
                    a.start_pan(event.x, event.y, 1)
                    self.pan_axes.append(a)

            # Set pan view flag
            if len(self.pan_axes) > 0: self.panning = True;

    def on_mouse_release(self, event):

        # Check for middle mouse button release to complete pan procedure
        if event.button == 2:
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
        self.mouse = [event.xdata, event.ydata]

        # Update pan view on mouse move
        if self.panning is True:
            for a in self.pan_axes:
                a.drag_pan(1, event.key, event.x, event.y)

            # Async re-draw (redraws only on thread idle state, uses timer on backend)
            self.canvas.draw_idle()

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

    def get_resolution(self):
        """
        Returns pixels per unit length.

        :return: X and Y density
        :rtype: tuple
        """
        xpx, ypx = self.get_axes_pixelsize()

        xmin, xmax = self.axes.get_xlim()
        ymin, ymax = self.axes.get_ylim()
        width = xmax - xmin
        height = ymax - ymin

        return xpx / width, ypx / height
