# ########################################################## ##
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://caram.cl/software/flatcam                         #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
# ########################################################## ##

from PyQt5 import QtCore

import logging
from flatcamGUI.VisPyCanvas import VisPyCanvas, time
from flatcamGUI.VisPyVisuals import ShapeGroup, ShapeCollection, TextCollection, TextGroup, Cursor
from vispy.scene.visuals import InfiniteLine, Line
import numpy as np
from vispy.geometry import Rect

log = logging.getLogger('base')


class PlotCanvas(QtCore.QObject):
    """
    Class handling the plotting area in the application.
    """

    def __init__(self, container, app):
        """
        The constructor configures the VisPy figure that
        will contain all plots, creates the base axes and connects
        events to the plotting area.

        :param container: The parent container in which to draw plots.
        :rtype: PlotCanvas
        """

        super(PlotCanvas, self).__init__()

        self.app = app

        # Parent container
        self.container = container

        # workspace lines; I didn't use the rectangle because I didn't want to add another VisPy Node,
        # which might decrease performance
        self.b_line, self.r_line, self.t_line, self.l_line = None, None, None, None

        # Attach to parent
        self.vispy_canvas = VisPyCanvas()

        self.vispy_canvas.create_native()
        self.vispy_canvas.native.setParent(self.app.ui)
        self.container.addWidget(self.vispy_canvas.native)

        # ## AXIS # ##
        self.v_line = InfiniteLine(pos=0, color=(0.70, 0.3, 0.3, 1.0), vertical=True,
                                   parent=self.vispy_canvas.view.scene)

        self.h_line = InfiniteLine(pos=0, color=(0.70, 0.3, 0.3, 1.0), vertical=False,
                                   parent=self.vispy_canvas.view.scene)

        # draw a rectangle made out of 4 lines on the canvas to serve as a hint for the work area
        # all CNC have a limited workspace

        self.draw_workspace()

        # if self.app.defaults['global_workspace'] is True:
        #     if self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().upper() == 'MM':
        #         self.wkspace_t = Line(pos=)

        self.shape_collections = []

        self.shape_collection = self.new_shape_collection()
        self.app.pool_recreated.connect(self.on_pool_recreated)
        self.text_collection = self.new_text_collection()

        # TODO: Should be setting to show/hide CNC job annotations (global or per object)
        self.text_collection.enabled = True

    # draw a rectangle made out of 4 lines on the canvas to serve as a hint for the work area
    # all CNC have a limited workspace
    def draw_workspace(self):
        a = np.empty((0, 0))

        a4p_in = np.array([(0, 0), (8.3, 0), (8.3, 11.7), (0, 11.7)])
        a4l_in = np.array([(0, 0), (11.7, 0), (11.7, 8.3), (0, 8.3)])
        a3p_in = np.array([(0, 0), (11.7, 0), (11.7, 16.5), (0, 16.5)])
        a3l_in = np.array([(0, 0), (16.5, 0), (16.5, 11.7), (0, 11.7)])

        a4p_mm = np.array([(0, 0), (210, 0), (210, 297), (0, 297)])
        a4l_mm = np.array([(0, 0), (297, 0), (297,210), (0, 210)])
        a3p_mm = np.array([(0, 0), (297, 0), (297, 420), (0, 420)])
        a3l_mm = np.array([(0, 0), (420, 0), (420, 297), (0, 297)])

        if self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().upper() == 'MM':
            if self.app.defaults['global_workspaceT'] == 'A4P':
                a = a4p_mm
            elif self.app.defaults['global_workspaceT'] == 'A4L':
                a = a4l_mm
            elif self.app.defaults['global_workspaceT'] == 'A3P':
                a = a3p_mm
            elif self.app.defaults['global_workspaceT'] == 'A3L':
                a = a3l_mm
        else:
            if self.app.defaults['global_workspaceT'] == 'A4P':
                a = a4p_in
            elif self.app.defaults['global_workspaceT'] == 'A4L':
                a = a4l_in
            elif self.app.defaults['global_workspaceT'] == 'A3P':
                a = a3p_in
            elif self.app.defaults['global_workspaceT'] == 'A3L':
                a = a3l_in

        self.delete_workspace()

        self.b_line = Line(pos=a[0:2], color=(0.70, 0.3, 0.3, 1.0),
                           antialias= True, method='agg', parent=self.vispy_canvas.view.scene)
        self.r_line = Line(pos=a[1:3], color=(0.70, 0.3, 0.3, 1.0),
                           antialias= True, method='agg', parent=self.vispy_canvas.view.scene)

        self.t_line = Line(pos=a[2:4], color=(0.70, 0.3, 0.3, 1.0),
                           antialias= True, method='agg', parent=self.vispy_canvas.view.scene)
        self.l_line = Line(pos=np.array((a[0], a[3])), color=(0.70, 0.3, 0.3, 1.0),
                           antialias= True, method='agg', parent=self.vispy_canvas.view.scene)

        if self.app.defaults['global_workspace'] is False:
            self.delete_workspace()

    # delete the workspace lines from the plot by removing the parent
    def delete_workspace(self):
        try:
            self.b_line.parent = None
            self.r_line.parent = None
            self.t_line.parent = None
            self.l_line.parent = None
        except Exception as e:
            pass

    # redraw the workspace lines on the plot by readding them to the parent view.scene
    def restore_workspace(self):
        try:
            self.b_line.parent = self.vispy_canvas.view.scene
            self.r_line.parent = self.vispy_canvas.view.scene
            self.t_line.parent = self.vispy_canvas.view.scene
            self.l_line.parent = self.vispy_canvas.view.scene
        except Exception as e:
            pass

    def vis_connect(self, event_name, callback):
        return getattr(self.vispy_canvas.events, event_name).connect(callback)

    def vis_disconnect(self, event_name, callback=None):
        if callback is None:
            getattr(self.vispy_canvas.events, event_name).disconnect()
        else:
            getattr(self.vispy_canvas.events, event_name).disconnect(callback)

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
        self.vispy_canvas.view.camera.zoom(factor, center)

    def new_shape_group(self, shape_collection=None):
        if shape_collection:
            return ShapeGroup(shape_collection)
        return ShapeGroup(self.shape_collection)

    def new_shape_collection(self, **kwargs):
        # sc = ShapeCollection(parent=self.vispy_canvas.view.scene, pool=self.app.pool, **kwargs)
        # self.shape_collections.append(sc)
        # return sc
        return ShapeCollection(parent=self.vispy_canvas.view.scene, pool=self.app.pool, **kwargs)

    def new_cursor(self):
        c = Cursor(pos=np.empty((0, 2)), parent=self.vispy_canvas.view.scene)
        c.antialias = 0
        return c

    def new_text_group(self):
        return TextGroup(self.text_collection)

    def new_text_collection(self, **kwargs):
        return TextCollection(parent=self.vispy_canvas.view.scene, **kwargs)

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

        # adjust the view camera to be slightly bigger than the bounds so the shape colleaction can be seen clearly
        # otherwise the shape collection boundary will have no border
        rect.left *= 0.96
        rect.bottom *= 0.96
        rect.right *= 1.01
        rect.top *= 1.01

        self.vispy_canvas.view.camera.rect = rect

        self.shape_collection.unlock_updates()

    def fit_center(self, loc, rect=None):

        # Lock updates in other threads
        self.shape_collection.lock_updates()

        if not rect:
            try:
                rect = Rect(loc[0]-20, loc[1]-20, 40, 40)
            except TypeError:
                pass

        self.vispy_canvas.view.camera.rect = rect

        self.shape_collection.unlock_updates()

    def clear(self):
        pass

    def redraw(self):
        self.shape_collection.redraw([])
        self.text_collection.redraw()

    def on_pool_recreated(self, pool):
        self.shape_collection.pool = pool
