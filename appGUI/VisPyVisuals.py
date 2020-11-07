# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# File Author: Dennis Hayrullin                            #
# Date: 2/5/2016                                           #
# MIT Licence                                              #
# ##########################################################

from vispy.visuals import CompoundVisual, LineVisual, MeshVisual, TextVisual, MarkersVisual
from vispy.scene.visuals import VisualNode, generate_docstring, visuals
from vispy.gloo import set_state
from vispy.color import Color
from shapely.geometry import Polygon, LineString, LinearRing
import threading
import numpy as np
from appGUI.VisPyTesselators import GLUTess


class FlatCAMLineVisual(LineVisual):
    def __init__(self, pos=None, color=(0.5, 0.5, 0.5, 1), width=1, connect='strip', method='gl', antialias=False):
        LineVisual.__init__(self, pos=pos, color=color, width=width, connect=connect,
                            method=method, antialias=True)

    def clear_data(self):
        self._bounds = None
        self._pos = None
        self._changed['pos'] = True
        self.update()


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


class ShapeGroup(object):
    def __init__(self, collection):
        """
        Represents group of shapes in collection
        :param collection: ShapeCollection
            Collection to work with
        """
        self._collection = collection
        self._indexes = []
        self._visible = True
        self._color = None

    def add(self, **kwargs):
        """
        Adds shape to collection and store index in group
        :param kwargs: keyword arguments
            Arguments for ShapeCollection.add function
        """
        key = self._collection.add(**kwargs)
        self._indexes.append(key)
        return key

    def remove(self, idx, update=False):
        self._indexes.remove(idx)
        self._collection.remove(idx, False)
        if update:
            self._collection.redraw([])             # Skip waiting results

    def clear(self, update=False):
        """
        Removes group shapes from collection, clear indexes
        :param update: bool
            Set True to redraw collection
        """
        for i in self._indexes:
            self._collection.remove(i, False)

        del self._indexes[:]

        if update:
            self._collection.redraw([])             # Skip waiting results

    def redraw(self, update_colors=None):
        """
        Redraws shape collection
        """
        if update_colors:
            self._collection.redraw(self._indexes, update_colors=update_colors)
        else:
            self._collection.redraw(self._indexes)

    @property
    def visible(self):
        """
        Visibility of group
        :return: bool
        """
        return self._visible

    @visible.setter
    def visible(self, value):
        """
        Visibility of group
        :param value: bool
        """
        self._visible = value
        for i in self._indexes:
            self._collection.data[i]['visible'] = value

        self._collection.redraw([])

    def update_visibility(self, state, indexes=None):
        if indexes:
            for i in indexes:
                if i in self._indexes:
                    self._collection.data[i]['visible'] = state
        else:
            for i in self._indexes:
                self._collection.data[i]['visible'] = state

        self._collection.redraw([])


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
        self.pool = pool
        self.results = {}

        self._meshes = [MeshVisual() for _ in range(0, layers)]
        # self._lines = [LineVisual(antialias=True) for _ in range(0, layers)]
        self._lines = [FlatCAMLineVisual(antialias=True) for _ in range(0, layers)]

        self._line_width = linewidth
        self._triangulation = triangulation

        visuals_ = [self._lines[i // 2] if i % 2 else self._meshes[i // 2] for i in range(0, layers * 2)]

        CompoundVisual.__init__(self, visuals_, **kwargs)

        for m in self._meshes:
            pass
            m.set_gl_state(polygon_offset_fill=True, polygon_offset=(1, 1), cull_face=False)

        for lne in self._lines:
            pass
            lne.set_gl_state(blend=True)

        self.freeze()

    def add(self, shape=None, color=None, face_color=None, alpha=None, visible=True,
            update=False, layer=1, tolerance=0.01, linewidth=None):
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

        # Add data to process pool if pool exists
        try:
            self.results[key] = self.pool.map_async(_update_shape_buffers, [self.data[key]])
        except Exception:
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

    def update_color(self, new_mesh_color=None, new_line_color=None, indexes=None):
        if new_mesh_color is None and new_line_color is None:
            return

        if not self.data:
            return

        # if a new color is empty string then make it None so it will not be updated
        # if a new color is valid then transform it here in a format palatable
        mesh_color_rgba = None
        line_color_rgba = None
        if new_mesh_color:
            if new_mesh_color != '':
                mesh_color_rgba = Color(new_mesh_color).rgba
            else:
                new_mesh_color = None
        if new_line_color:
            if new_line_color != '':
                line_color_rgba = Color(new_line_color).rgba
            else:
                new_line_color = None

        mesh_colors = [[] for _ in range(0, len(self._meshes))]     # Face colors
        line_colors = [[] for _ in range(0, len(self._meshes))]     # Line colors
        line_pts = [[] for _ in range(0, len(self._lines))]         # Vertices for line

        # Lock sub-visuals updates
        self.update_lock.acquire(True)
        # Merge shapes buffers

        if indexes is None:
            for k, data in list(self.data.items()):
                if data['visible'] and 'line_pts' in data:
                    if new_mesh_color and new_mesh_color != '':
                        dim_mesh_tris = (len(data['mesh_tris']) // 3)
                        if dim_mesh_tris != 0:
                            try:
                                mesh_colors[data['layer']] += [mesh_color_rgba] * dim_mesh_tris
                                self.data[k]['face_color'] = new_mesh_color

                                data['mesh_colors'] = [mesh_color_rgba for __ in range(len(data['mesh_colors']))]
                            except Exception as e:
                                print("VisPyVisuals.ShapeCollectionVisual.update_color(). "
                                      "Create mesh colors --> Data error. %s" % str(e))

                    if new_line_color and new_line_color != '':
                        dim_line_pts = (len(data['line_pts']))
                        if dim_line_pts != 0:
                            try:
                                line_pts[data['layer']] += data['line_pts']
                                line_colors[data['layer']] += [line_color_rgba] * dim_line_pts
                                self.data[k]['color'] = new_line_color

                                data['line_colors'] = [mesh_color_rgba for __ in range(len(data['line_colors']))]
                            except Exception as e:
                                print("VisPyVisuals.ShapeCollectionVisual.update_color(). "
                                      "Create line colors --> Data error. %s" % str(e))
        else:
            for k, data in list(self.data.items()):
                if data['visible'] and 'line_pts' in data:
                    dim_mesh_tris = (len(data['mesh_tris']) // 3)
                    dim_line_pts = (len(data['line_pts']))

                    if k in indexes:
                        if new_mesh_color and new_mesh_color != '':
                            if dim_mesh_tris != 0:
                                try:
                                    mesh_colors[data['layer']] += [mesh_color_rgba] * dim_mesh_tris
                                    self.data[k]['face_color'] = new_mesh_color

                                    data['mesh_colors'] = [mesh_color_rgba for __ in range(len(data['mesh_colors']))]
                                except Exception as e:
                                    print("VisPyVisuals.ShapeCollectionVisual.update_color(). "
                                          "Create mesh colors --> Data error. %s" % str(e))
                        if new_line_color and new_line_color != '':
                            if dim_line_pts != 0:
                                try:
                                    line_pts[data['layer']] += data['line_pts']
                                    line_colors[data['layer']] += [line_color_rgba] * dim_line_pts
                                    self.data[k]['color'] = new_line_color

                                    data['line_colors'] = [mesh_color_rgba for __ in range(len(data['line_colors']))]
                                except Exception as e:
                                    print("VisPyVisuals.ShapeCollectionVisual.update_color(). "
                                          "Create line colors --> Data error. %s" % str(e))
                    else:
                        if dim_mesh_tris != 0:
                            try:
                                mesh_colors[data['layer']] += [Color(data['face_color']).rgba] * dim_mesh_tris
                            except Exception as e:
                                print("VisPyVisuals.ShapeCollectionVisual.update_color(). "
                                      "Create mesh colors --> Data error. %s" % str(e))

                        if dim_line_pts != 0:
                            try:
                                line_pts[data['layer']] += data['line_pts']
                                line_colors[data['layer']] += [Color(data['color']).rgba] * dim_line_pts
                            except Exception as e:
                                print("VisPyVisuals.ShapeCollectionVisual.update_color(). "
                                      "Create line colors --> Data error. %s" % str(e))

        # Updating meshes
        if new_mesh_color and new_mesh_color != '':
            for i, mesh in enumerate(self._meshes):
                if mesh_colors[i]:
                    try:
                        mesh._meshdata.set_face_colors(colors=np.asarray(mesh_colors[i]))
                        mesh.mesh_data_changed()
                    except Exception as e:
                        print("VisPyVisuals.ShapeCollectionVisual.update_color(). "
                              "Apply mesh colors --> Data error. %s" % str(e))

        # Updating lines
        if new_line_color and new_line_color != '':
            for i, line in enumerate(self._lines):
                if len(line_pts[i]) > 0:
                    try:
                        line._color = np.asarray(line_colors[i])
                        line._changed['color'] = True
                        line.update()
                    except Exception as e:
                        print("VisPyVisuals.ShapeCollectionVisual.update_color(). "
                              "Apply line colors --> Data error. %s" % str(e))
                else:
                    line.clear_data()

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
                line.set_data(
                    pos=np.asarray(line_pts[i]),
                    color=np.asarray(line_colors[i]),
                    width=self._line_width,
                    connect='segments')
            else:
                line.clear_data()

            line._bounds_changed()

        self._bounds_changed()
        self.update_lock.release()

    def redraw(self, indexes=None, update_colors=None):
        """
        Redraws collection
        :param indexes:     list
            Shape indexes to get from process pool
        :param update_colors:
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

        if update_colors is None or update_colors is False:
            self.__update()
        else:
            try:
                self.update_color(
                    new_mesh_color=update_colors[0],
                    new_line_color=update_colors[1],
                    indexes=indexes
                )
            except Exception as e:
                print("VisPyVisuals.ShapeCollectionVisual.redraw() --> Update colors error = %s." % str(e))

    def lock_updates(self):
        self.update_lock.acquire(True)

    def unlock_updates(self):
        self.update_lock.release()


class TextGroup(object):
    def __init__(self, collection):
        self._collection = collection
        self._index = None
        self._visible = None

    def set(self, **kwargs):
        """
        Adds text to collection and store index
        :param kwargs: keyword arguments
            Arguments for TextCollection.add function
        """
        self._index = self._collection.add(**kwargs)

    def clear(self, update=False):
        """
        Removes text from collection, clear index
        :param update: bool
            Set True to redraw collection
        """

        if self._index is not None:
            self._collection.remove(self._index, False)
            self._index = None

        if update:
            self._collection.redraw()

    def redraw(self):
        """
        Redraws text collection
        """
        self._collection.redraw()

    @property
    def visible(self):
        """
        Visibility of group
        :return: bool
        """
        return self._visible

    @visible.setter
    def visible(self, value):
        """
        Visibility of group
        :param value: bool
        """
        self._visible = value
        if self._index:
            try:
                self._collection.data[self._index]['visible'] = value
            except KeyError as e:
                print("VisPyVisuals.TextGroup.visible --> KeyError --> %s" % str(e))
                pass
            self._collection.redraw()


class TextCollectionVisual(TextVisual):

    def __init__(self, **kwargs):
        """
        Represents collection of shapes to draw on VisPy scene
        :param kwargs: keyword arguments
            Arguments to pass for TextVisual
        """
        self.data = {}
        self.last_key = -1
        self.lock = threading.Lock()
        self.method = 'gpu'
        super(TextCollectionVisual, self).__init__(**kwargs)

        self.freeze()

    def add(self, text, pos, visible=True, update=True, font_size=9, color='black'):
        """
        Adds array of text to collection
        :param text: list
            Array of strings ['str1', 'str2', ... ]
        :param pos: list
            Array of string positions   [(0, 0), (10, 10), ... ]
        :param visible: bool
        |   Set True to make it visible
        :param update: bool
            Set True to redraw collection
        :param font_size: int
            Set font size to redraw collection
        :param color: string
            Set font color to redraw collection
        :return: int
            Index of array
        """
        # Get new key
        self.lock.acquire(True)
        self.last_key += 1
        key = self.last_key
        self.lock.release()

        # Prepare data for translation
        self.data[key] = {'text': text, 'pos': pos, 'visible': visible, 'font_size': font_size, 'color': color}

        if update:
            self.redraw()

        return key

    def remove(self, key, update=False):
        """
        Removes shape from collection
        :param key: int
            Shape index to remove
        :param update:
            Set True to redraw collection
        """
        del self.data[key]

        if update:
            self.__update()

    def clear(self, update=False):
        """
        Removes all shapes from collection
        :param update: bool
            Set True to redraw collection
        """
        self.data.clear()
        if update:
            self.__update()

    def __update(self):
        """
        Merges internal buffers, sets data to visuals, redraws collection on scene
        """
        labels = []
        pos = []
        font_s = 9
        color = 'black'

        # Merge buffers
        for data in list(self.data.values()):
            if data['visible']:
                try:
                    labels += data['text']
                    pos += data['pos']
                    font_s = data['font_size']
                    color = data['color']
                except Exception as e:
                    print("VisPyVisuals.TextCollectionVisual._update() --> Data error. %s" % str(e))

        # Updating text
        if len(labels) > 0:
            self.text = labels
            self.pos = pos
            self.font_size = font_s
            self.color = color
        else:
            self.text = None
            self.pos = (0, 0)

        self._bounds_changed()

    def redraw(self):
        """
        Redraws collection
        """
        self.__update()


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
TextCollection = create_fast_node(TextCollectionVisual)
Cursor = create_fast_node(MarkersVisual)
