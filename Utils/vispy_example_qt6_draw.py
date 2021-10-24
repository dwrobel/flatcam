from PyQt6.QtGui import QPalette, QScreen
from PyQt6 import QtCore, QtWidgets

import threading
import time
import numpy as np

from OpenGL import GLU

import vispy.scene as scene
from vispy.scene.cameras.base_camera import BaseCamera
from vispy.color import Color
from vispy.visuals import CompoundVisual, MeshVisual, LineVisual
from vispy.scene.visuals import VisualNode, generate_docstring, visuals
from vispy.gloo import set_state

from shapely.geometry import Polygon, LineString, LinearRing

import sys


class VisPyCanvas(scene.SceneCanvas):

    def __init__(self, config=None):
        super().__init__(config=config, keys=None)

        self.unfreeze()

        # Colors used by the Scene
        theme_color = Color('#FFFFFF')
        tick_color = Color('#000000')
        back_color = str(QPalette().color(QPalette.ColorRole.Window).name())

        # Central Widget Colors
        self.central_widget.bgcolor = back_color
        self.central_widget.border_color = back_color

        # Add a Grid Widget
        self.grid_widget = self.central_widget.add_grid(margin=10)
        self.grid_widget.spacing = 0

        # TOP Padding
        top_padding = self.grid_widget.add_widget(row=0, col=0, col_span=2)
        top_padding.height_max = 0

        # RIGHT Padding
        right_padding = self.grid_widget.add_widget(row=0, col=2, row_span=2)
        right_padding.width_max = 0

        # X Axis
        self.xaxis = scene.AxisWidget(
            orientation='bottom', axis_color=tick_color, text_color=tick_color,
            font_size=8, axis_width=1,
            anchors=['center', 'bottom']
        )
        self.xaxis.height_max = 40
        self.grid_widget.add_widget(self.xaxis, row=2, col=1)

        # Y Axis
        self.yaxis = scene.AxisWidget(
            orientation='left', axis_color=tick_color, text_color=tick_color,
            font_size=8, axis_width=1
        )
        self.yaxis.width_max = 70
        self.grid_widget.add_widget(self.yaxis, row=1, col=0)

        # View & Camera
        self.view = self.grid_widget.add_view(row=1, col=1, border_color=tick_color,
                                              bgcolor=theme_color)
        self.view.camera = MyCamera(aspect=1, rect=(-25, -25, 150, 150))

        self.xaxis.link_view(self.view)
        self.yaxis.link_view(self.view)

        # add GridLines
        self.grid = scene.GridLines(parent=self.view.scene, color='dimgray')
        self.grid.set_gl_state(depth_test=False)

        self.freeze()


class MyCamera(scene.PanZoomCamera):

    def __init__(self, **kwargs):
        super(MyCamera, self).__init__(**kwargs)

        self.minimum_scene_size = 0.01
        self.maximum_scene_size = 10000

        self.last_event = None
        self.last_time = 0

        # Default mouse button for panning is RMB
        self.pan_button_setting = "2"

    def zoom(self, factor, center=None):
        center = center if (center is not None) else self.center
        super(MyCamera, self).zoom(factor, center)

    def viewbox_mouse_event(self, event):
        """
        The SubScene received a mouse event; update transform
        accordingly.

        Parameters
        ----------
        event : instance of Event
            The event.
        """
        if event.handled or not self.interactive:
            return

        # key modifiers
        modifiers = event.mouse_event.modifiers

        # Limit mouse move events
        last_event = event.last_event
        t = time.time()
        if t - self.last_time > 0.015:
            self.last_time = t
            if self.last_event:
                last_event = self.last_event
                self.last_event = None
        else:
            if not self.last_event:
                self.last_event = last_event
            event.handled = True
            return

        # ################### Scrolling ##########################
        BaseCamera.viewbox_mouse_event(self, event)

        if event.type == 'mouse_wheel':
            if not modifiers:
                center = self._scene_transform.imap(event.pos)
                scale = (1 + self.zoom_factor) ** (-event.delta[1] * 30)
                self.limited_zoom(scale, center)
            event.handled = True

        elif event.type == 'mouse_move':
            if event.press_event is None:
                return

            # ################ Panning ############################
            if event.button == int(self.pan_button_setting) and not modifiers:
                # Translate
                p1 = np.array(last_event.pos)[:2]
                p2 = np.array(event.pos)[:2]
                p1s = self._transform.imap(p1)
                p2s = self._transform.imap(p2)
                self.pan(p1s-p2s)
                event.handled = True
            elif event.button in [2, 3] and 'Shift' in modifiers:
                # Zoom
                p1c = np.array(last_event.pos)[:2]
                p2c = np.array(event.pos)[:2]
                scale = ((1 + self.zoom_factor) **
                         ((p1c-p2c) * np.array([1, -1])))
                center = self._transform.imap(event.press_event.pos[:2])
                self.limited_zoom(scale, center)
                event.handled = True
            else:
                event.handled = False
        elif event.type == 'mouse_press':
            # accept the event if it is button 1 or 2.
            # This is required in order to receive future events
            event.handled = event.button in [1, 2, 3]
        else:
            event.handled = False

    def limited_zoom(self, scale, center):

        try:
            zoom_in = scale[1] < 1
        except IndexError:
            zoom_in = scale < 1

        if (not zoom_in and self.rect.width < self.maximum_scene_size) \
                or (zoom_in and self.rect.width > self.minimum_scene_size):
            self.zoom(scale, center)


class MyGui(QtWidgets.QMainWindow):

    def __init__(self, app):
        super().__init__()

        self.setWindowTitle("VisPy Test")

        self.my_app = app

        # add Menubar
        self.menu = self.menuBar()
        self.menufile = self.menu.addMenu("File")
        self.menuedit = self.menu.addMenu("Edit")
        self.menufhelp = self.menu.addMenu("Help")

        # add a Toolbar
        self.file_toolbar = QtWidgets.QToolBar("File Toolbar")
        self.addToolBar(self.file_toolbar)
        self.button = self.file_toolbar.addAction("Open")

        # add Central Widget
        self.c_widget = QtWidgets.QWidget()
        self.central_layout = QtWidgets.QVBoxLayout()
        self.c_widget.setLayout(self.central_layout)
        self.setCentralWidget(self.c_widget)

        # add InfoBar
        self.infobar = self.statusBar()
        self.fps_label = QtWidgets.QLabel("FPS: 0.0")
        self.infobar.addWidget(self.fps_label)


class MyApp(QtCore.QObject):

    def __init__(self):
        super().__init__()

        self.ui = MyGui(app=self)

        # VisPyCanvas instance
        self.vispy_canvas = VisPyCanvas()

        self.vispy_canvas.unfreeze()
        self.vispy_canvas.create_native()
        self.vispy_canvas.native.setParent(self.ui)
        self.ui.central_layout.addWidget(self.vispy_canvas.native)
        self.vispy_canvas.freeze()

        self.ui.show()

        # add a shape on canvas
        self.shape_collection = ShapeCollection(parent=self.vispy_canvas.view.scene, layers=1)
        element = Polygon([(1, 1), (110, 1), (110, 110), (1, 110), (1, 1)])
        self.shape_collection.add(shape=element, color='red', face_color='#0000FAAF', update=True)
        # show FPS
        self.vispy_canvas.measure_fps(callback=self.show_fps)

    def show_fps(self, fps_val):
        self.ui.fps_label.setText("FPS: %1.1f" % float(fps_val))


class ShapeCollectionVisual(CompoundVisual):

    def __init__(self, linewidth=1, triangulation='vispy', layers=3, pool=None, **kwargs):
        """
        Represents collection of shapes to draw on VisPy scene
        :param linewidth: float
            Width of lines/edges
        :param triangulation: str
            Triangulation method used for polygons translation
            'vispy' - VisPy lib triangulation
            'gpc' - Polygon2 lib
        :param layers: int
            Layers count
            Each layer adds 2 visuals on VisPy scene. Be careful: more layers cause less fps
        :param kwargs:
        """
        self.data = {}
        self.last_key = -1

        # Thread locks
        self.key_lock = threading.Lock()
        self.results_lock = threading.Lock()
        self.update_lock = threading.Lock()

        # Process pool
        self.results = {}

        self._meshes = [MeshVisual() for _ in range(0, layers)]
        self._lines = [LineVisual(antialias=True) for _ in range(0, layers)]

        self._line_width = linewidth
        self._triangulation = triangulation

        visuals_ = [self._lines[i // 2] if i % 2 else self._meshes[i // 2] for i in range(0, layers * 2)]

        CompoundVisual.__init__(self, visuals_, **kwargs)

        for m in self._meshes:
            m.set_gl_state(polygon_offset_fill=True, polygon_offset=(1, 1), cull_face=False)

        for lne in self._lines:
            lne.set_gl_state(blend=True)

        self.freeze()

    def add(self, shape=None, color=None, face_color=None, alpha=None, visible=True,
            update=False, layer=0, tolerance=None, linewidth=None):
        """
        Adds shape to collection
        :return:
        :param shape: shapely.geometry
            Shapely geometry object
        :param color: str, tuple
            Line/edge color
        :param face_color: str, tuple
            Polygon face color
        :param alpha: str
            Polygon transparency
        :param visible: bool
            Shape visibility
        :param update: bool
            Set True to redraw collection
        :param layer: int
            Layer number. 0 - lowest.
        :param tolerance: float
            Geometry simplifying tolerance
        :param linewidth: int
            Width of the line
        :return: int
            Index of shape
        """
        # Get new key
        self.key_lock.acquire(True)
        self.last_key += 1
        key = self.last_key
        self.key_lock.release()

        # Prepare data for translation
        self.data[key] = {'geometry': shape, 'color': color, 'alpha': alpha, 'face_color': face_color,
                          'visible': visible, 'layer': layer, 'tolerance': tolerance}

        if linewidth:
            self._line_width = linewidth

        self.data[key] = _update_shape_buffers(self.data[key])

        if update:
            self.redraw()   # redraw() waits for pool process end

        return key

    def remove(self, key, update=False):
        """
        Removes shape from collection
        :param key: int
            Shape index to remove
        :param update:
            Set True to redraw collection
        """
        # Remove process result
        self.results_lock.acquire(True)
        if key in list(self.results.copy().keys()):
            del self.results[key]
        self.results_lock.release()

        # Remove data
        del self.data[key]

        if update:
            self.__update()

    def clear(self, update=False):
        """
        Removes all shapes from collection
        :param update: bool
            Set True to redraw collection
        """
        self.last_key = -1
        self.data.clear()
        if update:
            self.__update()

    def update_visibility(self, state: bool, indexes=None) -> None:
        # Lock sub-visuals updates
        self.update_lock.acquire(True)
        if indexes is None:
            for k, data in list(self.data.items()):
                self.data[k]['visible'] = state
        else:
            for k, data in list(self.data.items()):
                if k in indexes:
                    self.data[k]['visible'] = state

        self.update_lock.release()

    def __update(self):
        """
        Merges internal buffers, sets data to visuals, redraws collection on scene
        """
        mesh_vertices = [[] for _ in range(0, len(self._meshes))]       # Vertices for mesh
        mesh_tris = [[] for _ in range(0, len(self._meshes))]           # Faces for mesh
        mesh_colors = [[] for _ in range(0, len(self._meshes))]         # Face colors
        line_pts = [[] for _ in range(0, len(self._lines))]             # Vertices for line
        line_colors = [[] for _ in range(0, len(self._lines))]          # Line color

        # Lock sub-visuals updates
        self.update_lock.acquire(True)

        # Merge shapes buffers
        for data in list(self.data.values()):
            if data['visible'] and 'line_pts' in data:
                try:
                    line_pts[data['layer']] += data['line_pts']
                    line_colors[data['layer']] += data['line_colors']

                    mesh_tris[data['layer']] += [x + len(mesh_vertices[data['layer']]) for x in data['mesh_tris']]
                    mesh_vertices[data['layer']] += data['mesh_vertices']
                    mesh_colors[data['layer']] += data['mesh_colors']
                except Exception as e:
                    print("VisPyVisuals.ShapeCollectionVisual._update() --> Data error. %s" % str(e))

        # Updating meshes
        for i, mesh in enumerate(self._meshes):
            if len(mesh_vertices[i]) > 0:
                set_state(polygon_offset_fill=False)
                faces_array = np.asarray(mesh_tris[i], dtype=np.uint32)
                mesh.set_data(
                    vertices=np.asarray(mesh_vertices[i]),
                    faces=faces_array.reshape((-1, 3)),
                    face_colors=np.asarray(mesh_colors[i])
                )
            else:
                mesh.set_data()

            mesh._bounds_changed()

        # Updating lines
        for i, line in enumerate(self._lines):
            if len(line_pts[i]) > 0:
                line.visible = True
                line.set_data(
                    pos=np.asarray(line_pts[i]),
                    color=np.asarray(line_colors[i]),
                    width=self._line_width,
                    connect='segments')
            else:
                # line.clear_data()
                line.visible = False

            line._bounds_changed()

        self._bounds_changed()
        self.update_lock.release()

    def redraw(self, indexes=None):
        """
        Redraws collection
        :param indexes:     list
            Shape indexes to get from process pool
        """
        # Only one thread can update data
        self.results_lock.acquire(True)

        for i in list(self.data.keys()) if not indexes else indexes:
            if i in list(self.results.keys()):
                try:
                    self.results[i].wait()                                  # Wait for process results
                    if i in self.data:
                        self.data[i] = self.results[i].get()[0]             # Store translated data
                        del self.results[i]
                except Exception as e:
                    print("VisPyVisuals.ShapeCollectionVisual.redraw() --> Data error = %s. Indexes = %s" %
                          (str(e), str(indexes)))

        self.results_lock.release()

        self.__update()

    def lock_updates(self):
        self.update_lock.acquire(True)

    def unlock_updates(self):
        self.update_lock.release()


def _update_shape_buffers(data, triangulation='glu'):
    """
    Translates Shapely geometry to internal buffers for speedup redraws
    :param data: dict
        Input shape data
    :param triangulation: str
        Triangulation engine
    """
    mesh_vertices = []                                              # Vertices for mesh
    mesh_tris = []                                                  # Faces for mesh
    mesh_colors = []                                                # Face colors
    line_pts = []                                                   # Vertices for line
    line_colors = []                                                # Line color

    geo, color, face_color, tolerance = data['geometry'], data['color'], data['face_color'], data['tolerance']

    if geo is not None and not geo.is_empty:
        simplified_geo = geo.simplify(tolerance) if tolerance else geo      # Simplified shape
        pts = []                                                            # Shape line points
        tri_pts = []                                                        # Mesh vertices
        tri_tris = []                                                       # Mesh faces

        if type(geo) == LineString:
            # Prepare lines
            pts = _linestring_to_segments(list(simplified_geo.coords))

        elif type(geo) == LinearRing:
            # Prepare lines
            pts = _linearring_to_segments(list(simplified_geo.coords))

        elif type(geo) == Polygon:
            # Prepare polygon faces
            if face_color is not None:
                if triangulation == 'glu':
                    gt = GLUTess()
                    tri_tris, tri_pts = gt.triangulate(simplified_geo)
                else:
                    print("Triangulation type '%s' isn't implemented. Drawing only edges." % triangulation)

            # Prepare polygon edges
            if color is not None:
                pts = _linearring_to_segments(list(simplified_geo.exterior.coords))
                for ints in simplified_geo.interiors:
                    pts += _linearring_to_segments(list(ints.coords))

        # Appending data for mesh
        if len(tri_pts) > 0 and len(tri_tris) > 0:
            mesh_tris += tri_tris
            mesh_vertices += tri_pts
            face_color_rgba = Color(face_color).rgba
            # mesh_colors += [face_color_rgba] * (len(tri_tris) // 3)
            mesh_colors += [face_color_rgba for __ in range(len(tri_tris) // 3)]

        # Appending data for line
        if len(pts) > 0:
            line_pts += pts
            colo_rgba = Color(color).rgba
            # line_colors += [colo_rgba] * len(pts)
            line_colors += [colo_rgba for __ in range(len(pts))]

    # Store buffers
    data['line_pts'] = line_pts
    data['line_colors'] = line_colors
    data['mesh_vertices'] = mesh_vertices
    data['mesh_tris'] = mesh_tris
    data['mesh_colors'] = mesh_colors

    # Clear shapely geometry
    del data['geometry']

    return data


def _linearring_to_segments(arr):
    # Close linear ring
    """
    Translates linear ring to line segments
    :param arr: numpy.array
        Array of linear ring vertices
    :return: numpy.array
        Line segments
    """
    if arr[0] != arr[-1]:
        arr.append(arr[0])

    return _linestring_to_segments(arr)


def _linestring_to_segments(arr):
    """
    Translates line strip to segments
    :param arr: numpy.array
        Array of line strip vertices
    :return: numpy.array
        Line segments
    """
    return [arr[i // 2] for i in range(0, len(arr) * 2)][1:-1]


# Add 'enabled' property to visual nodes
def create_fast_node(subclass):
    # Create a new subclass of Node.

    # Decide on new class name
    clsname = subclass.__name__
    if not (clsname.endswith('Visual') and
            issubclass(subclass, visuals.BaseVisual)):
        raise RuntimeError('Class "%s" must end with Visual, and must '
                           'subclass BaseVisual' % clsname)
    clsname = clsname[:-6]

    # Generate new docstring based on visual docstring
    try:
        doc = generate_docstring(subclass, clsname)
    except Exception:
        # If parsing fails, just return the original Visual docstring
        doc = subclass.__doc__

    # New __init__ method
    def __init__(self, *args, **kwargs):
        parent = kwargs.pop('parent', None)
        name = kwargs.pop('name', None)
        self.name = name  # to allow __str__ before Node.__init__
        self._visual_superclass = subclass

        # parent: property,
        # _parent: attribute of Node class
        # __parent: attribute of fast_node class
        self.__parent = parent
        self._enabled = False

        subclass.__init__(self, *args, **kwargs)
        self.unfreeze()
        VisualNode.__init__(self, parent=parent, name=name)
        self.freeze()

    # Create new class
    cls = type(clsname, (VisualNode, subclass),
               {'__init__': __init__, '__doc__': doc})

    # 'Enabled' property clears/restores 'parent' property of Node class
    # Scene will be painted quicker than when using 'visible' property
    def get_enabled(self):
        return self._enabled

    def set_enabled(self, enabled):
        if enabled:
            self.parent = self.__parent                 # Restore parent
        else:
            if self.parent:                             # Store parent
                self.__parent = self.parent
            self.parent = None

    cls.enabled = property(get_enabled, set_enabled)

    return cls


ShapeCollection = create_fast_node(ShapeCollectionVisual)


class GLUTess:
    def __init__(self):
        """
        OpenGL GLU triangulation class
        """
        self.tris = []
        self.pts = []
        self.vertex_index = 0

    def _on_begin_primitive(self, type):
        pass

    def _on_new_vertex(self, vertex):
        self.tris.append(vertex)

    # Force GLU to return separate triangles (GLU_TRIANGLES)
    def _on_edge_flag(self, flag):
        pass

    def _on_combine(self, coords, data, weight):
        return coords[0], coords[1], coords[2]

    @staticmethod
    def _on_error(errno):
        print("GLUTess error:", errno)

    def _on_end_primitive(self):
        pass

    def triangulate(self, polygon):
        """
        Triangulates polygon
        :param polygon: shapely.geometry.polygon
            Polygon to tessellate
        :return: list, list
            Array of triangle vertex indices [t0i0, t0i1, t0i2, t1i0, t1i1, ... ]
            Array of polygon points [(x0, y0), (x1, y1), ... ]
        """
        # Create tessellation object
        tess = GLU.gluNewTess()

        # Setup callbacks
        GLU.gluTessCallback(tess, GLU.GLU_TESS_BEGIN, self._on_begin_primitive)
        GLU.gluTessCallback(tess, GLU.GLU_TESS_VERTEX, self._on_new_vertex)
        GLU.gluTessCallback(tess, GLU.GLU_TESS_EDGE_FLAG, self._on_edge_flag)
        GLU.gluTessCallback(tess, GLU.GLU_TESS_COMBINE, self._on_combine)
        GLU.gluTessCallback(tess, GLU.GLU_TESS_ERROR, self._on_error)
        GLU.gluTessCallback(tess, GLU.GLU_TESS_END, self._on_end_primitive)

        # Reset data
        del self.tris[:]
        del self.pts[:]
        self.vertex_index = 0

        # Define polygon
        GLU.gluTessBeginPolygon(tess, None)

        def define_contour(contour):
            vertices = list(contour.coords)             # Get vertices coordinates
            if vertices[0] == vertices[-1]:             # Open ring
                vertices = vertices[:-1]

            self.pts += vertices

            GLU.gluTessBeginContour(tess)               # Start contour

            # Set vertices
            for vertex in vertices:
                point = (vertex[0], vertex[1], 0)
                GLU.gluTessVertex(tess, point, self.vertex_index)
                self.vertex_index += 1

            GLU.gluTessEndContour(tess)                 # End contour

        # Polygon exterior
        define_contour(polygon.exterior)

        # Interiors
        for interior in polygon.interiors:
            define_contour(interior)

        # Start tessellation
        GLU.gluTessEndPolygon(tess)

        # Free resources
        GLU.gluDeleteTess(tess)

        return self.tris, self.pts


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    m_app = MyApp()
    sys.exit(app.exec())
