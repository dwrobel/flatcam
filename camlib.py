# ########################################################## ##
# FlatCAM: 2D Post-processing for Manufacturing               #
# http://flatcam.org                                          #
# Author: Juan Pablo Caram (c)                                #
# Date: 2/5/2014                                              #
# MIT Licence                                                 #
# ########################################################## ##


from PyQt5 import QtWidgets, QtCore
from io import StringIO

from numpy.linalg import solve, norm

import platform
from copy import deepcopy

import traceback
from decimal import Decimal

from rtree import index as rtindex
from lxml import etree as ET

# See: http://toblerity.org/shapely/manual.html
from shapely.geometry import Polygon, Point, LinearRing

from shapely.geometry import box as shply_box
from shapely.ops import unary_union, substring, linemerge
import shapely.affinity as affinity
from shapely.wkt import loads as sloads
from shapely.wkt import dumps as sdumps
from shapely.geometry.base import BaseGeometry
from shapely.geometry import shape

# ---------------------------------------
# NEEDED for Legacy mode
# Used for solid polygons in Matplotlib
from descartes.patch import PolygonPatch
# ---------------------------------------

from collections import Iterable

import rasterio
from rasterio.features import shapes
import ezdxf

from appCommon.Common import GracefulException as grace

# Commented for FlatCAM packaging with cx_freeze
# from scipy.spatial import KDTree, Delaunay
# from scipy.spatial import Delaunay

from appParsers.ParseSVG import *
from appParsers.ParseDXF import *

if platform.architecture()[0] == '64bit':
    from ortools.constraint_solver import pywrapcp
    from ortools.constraint_solver import routing_enums_pb2

import logging

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')

log = logging.getLogger('base2')
log.setLevel(logging.DEBUG)

formatter = logging.Formatter('[%(levelname)s] %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
log.addHandler(handler)

if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ParseError(Exception):
    pass


class ApertureMacro:
    """
    Syntax of aperture macros.

    <AM command>:           AM<Aperture macro name>*<Macro content>
    <Macro content>:        {{<Variable definition>*}{<Primitive>*}}
    <Variable definition>:  $K=<Arithmetic expression>
    <Primitive>:            <Primitive code>,<Modifier>{,<Modifier>}|<Comment>
    <Modifier>:             $M|< Arithmetic expression>
    <Comment>:              0 <Text>
    """

    # ## Regular expressions
    am1_re = re.compile(r'^%AM([^\*]+)\*(.+)?(%)?$')
    am2_re = re.compile(r'(.*)%$')
    amcomm_re = re.compile(r'^0(.*)')
    amprim_re = re.compile(r'^[1-9].*')
    amvar_re = re.compile(r'^\$([0-9a-zA-z]+)=(.*)')

    def __init__(self, name=None):
        self.name = name
        self.raw = ""

        # ## These below are recomputed for every aperture
        # ## definition, in other words, are temporary variables.
        self.primitives = []
        self.locvars = {}
        self.geometry = None

    def to_dict(self):
        """
        Returns the object in a serializable form. Only the name and
        raw are required.

        :return: Dictionary representing the object. JSON ready.
        :rtype: dict
        """

        return {
            'name': self.name,
            'raw': self.raw
        }

    def from_dict(self, d):
        """
        Populates the object from a serial representation created
        with ``self.to_dict()``.

        :param d: Serial representation of an ApertureMacro object.
        :return: None
        """
        for attr in ['name', 'raw']:
            setattr(self, attr, d[attr])

    def parse_content(self):
        """
        Creates numerical lists for all primitives in the aperture
        macro (in ``self.raw``) by replacing all variables by their
        values iteratively and evaluating expressions. Results
        are stored in ``self.primitives``.

        :return: None
        """
        # Cleanup
        self.raw = self.raw.replace('\n', '').replace('\r', '').strip(" *")
        self.primitives = []

        # Separate parts
        parts = self.raw.split('*')

        # ### Every part in the macro ####
        for part in parts:
            # ## Comments. Ignored.
            match = ApertureMacro.amcomm_re.search(part)
            if match:
                continue

            # ## Variables
            # These are variables defined locally inside the macro. They can be
            # numerical constant or defined in terms of previously define
            # variables, which can be defined locally or in an aperture
            # definition. All replacements occur here.
            match = ApertureMacro.amvar_re.search(part)
            if match:
                var = match.group(1)
                val = match.group(2)

                # Replace variables in value
                for v in self.locvars:
                    # replaced the following line with the next to fix Mentor custom apertures not parsed OK
                    # val = re.sub((r'\$'+str(v)+r'(?![0-9a-zA-Z])'), str(self.locvars[v]), val)
                    val = val.replace('$' + str(v), str(self.locvars[v]))

                # Make all others 0
                val = re.sub(r'\$[0-9a-zA-Z](?![0-9a-zA-Z])', "0", val)
                # Change x with *
                val = re.sub(r'[xX]', "*", val)

                # Eval() and store.
                self.locvars[var] = eval(val)
                continue

            # ## Primitives
            # Each is an array. The first identifies the primitive, while the
            # rest depend on the primitive. All are strings representing a
            # number and may contain variable definition. The values of these
            # variables are defined in an aperture definition.
            match = ApertureMacro.amprim_re.search(part)
            if match:
                # ## Replace all variables
                for v in self.locvars:
                    # replaced the following line with the next to fix Mentor custom apertures not parsed OK
                    # part = re.sub(r'\$' + str(v) + r'(?![0-9a-zA-Z])', str(self.locvars[v]), part)
                    part = part.replace('$' + str(v), str(self.locvars[v]))

                # Make all others 0
                part = re.sub(r'\$[0-9a-zA-Z](?![0-9a-zA-Z])', "0", part)

                # Change x with *
                part = re.sub(r'[xX]', "*", part)

                # ## Store
                elements = part.split(",")
                self.primitives.append([eval(x) for x in elements])
                continue

            log.warning("Unknown syntax of aperture macro part: %s" % str(part))

    def append(self, data):
        """
        Appends a string to the raw macro.

        :param data: Part of the macro.
        :type data: str
        :return: None
        """
        self.raw += data

    @staticmethod
    def default2zero(n, mods):
        """
        Pads the ``mods`` list with zeros resulting in an
        list of length n.

        :param n:       Length of the resulting list.
        :type n:        int
        :param mods:    List to be padded.
        :type mods:     list
        :return:        Zero-padded list.
        :rtype:         list
        """

        x = [0.0] * n
        na = len(mods)
        x[0:na] = mods
        return x

    @staticmethod
    def make_circle(mods):
        """

        :param mods: (Exposure 0/1, Diameter >=0, X-coord, Y-coord)
        :return:
        """
        val = ApertureMacro.default2zero(4, mods)
        pol = val[0]
        dia = val[1]
        x = val[2]
        y = val[3]
        # pol, dia, x, y = ApertureMacro.default2zero(4, mods)
        return {"pol": int(pol), "geometry": Point(x, y).buffer(dia / 2)}

    @staticmethod
    def make_vectorline(mods):
        """

        :param mods: (Exposure 0/1, Line width >= 0, X-start, Y-start, X-end, Y-end,
            rotation angle around origin in degrees)
        :return:
        """
        val = ApertureMacro.default2zero(7, mods)
        pol = val[0]
        width = val[1]
        xs = val[2]
        ys = val[3]
        xe = val[4]
        ye = val[5]
        angle = val[6]
        # pol, width, xs, ys, xe, ye, angle = ApertureMacro.default2zero(7, mods)

        line = LineString([(xs, ys), (xe, ye)])
        box = line.buffer(width / 2, cap_style=2)
        box_rotated = affinity.rotate(box, angle, origin=(0, 0))

        return {"pol": int(pol), "geometry": box_rotated}

    @staticmethod
    def make_centerline(mods):
        """

        :param mods: (Exposure 0/1, width >=0, height >=0, x-center, y-center,
            rotation angle around origin in degrees)
        :return:
        """

        # pol, width, height, x, y, angle = ApertureMacro.default2zero(4, mods)
        val = ApertureMacro.default2zero(4, mods)
        pol = val[0]
        width = val[1]
        height = val[2]
        x = val[3]
        y = val[4]
        angle = val[5]

        box = shply_box(x - width / 2, y - height / 2, x + width / 2, y + height / 2)
        box_rotated = affinity.rotate(box, angle, origin=(0, 0))

        return {"pol": int(pol), "geometry": box_rotated}

    @staticmethod
    def make_lowerleftline(mods):
        """

        :param mods: (exposure 0/1, width >=0, height >=0, x-lowerleft, y-lowerleft,
            rotation angle around origin in degrees)
        :return:
        """

        # pol, width, height, x, y, angle = ApertureMacro.default2zero(6, mods)
        val = ApertureMacro.default2zero(6, mods)
        pol = val[0]
        width = val[1]
        height = val[2]
        x = val[3]
        y = val[4]
        angle = val[5]

        box = shply_box(x, y, x + width, y + height)
        box_rotated = affinity.rotate(box, angle, origin=(0, 0))

        return {"pol": int(pol), "geometry": box_rotated}

    @staticmethod
    def make_outline(mods):
        """

        :param mods:
        :return:
        """

        pol = mods[0]
        n = mods[1]
        points = [(0, 0)] * (n + 1)

        for i in range(n + 1):
            points[i] = mods[2 * i + 2:2 * i + 4]

        angle = mods[2 * n + 4]

        poly = Polygon(points)
        poly_rotated = affinity.rotate(poly, angle, origin=(0, 0))

        return {"pol": int(pol), "geometry": poly_rotated}

    @staticmethod
    def make_polygon(mods):
        """
        Note: Specs indicate that rotation is only allowed if the center
        (x, y) == (0, 0). I will tolerate breaking this rule.

        :param mods: (exposure 0/1, n_verts 3<=n<=12, x-center, y-center,
            diameter of circumscribed circle >=0, rotation angle around origin)
        :return:
        """

        # pol, nverts, x, y, dia, angle = ApertureMacro.default2zero(6, mods)
        val = ApertureMacro.default2zero(6, mods)
        pol = val[0]
        nverts = val[1]
        x = val[2]
        y = val[3]
        dia = val[4]
        angle = val[5]

        points = [(0, 0)] * nverts

        for i in range(nverts):
            points[i] = (x + 0.5 * dia * np.cos(2 * np.pi * i / nverts),
                         y + 0.5 * dia * np.sin(2 * np.pi * i / nverts))

        poly = Polygon(points)
        poly_rotated = affinity.rotate(poly, angle, origin=(0, 0))

        return {"pol": int(pol), "geometry": poly_rotated}

    @staticmethod
    def make_moire(mods):
        """
        Note: Specs indicate that rotation is only allowed if the center
        (x, y) == (0, 0). I will tolerate breaking this rule.

        :param mods: (x-center, y-center, outer_dia_outer_ring, ring thickness,
            gap, max_rings, crosshair_thickness, crosshair_len, rotation
            angle around origin in degrees)
        :return:
        """

        # x, y, dia, thickness, gap, nrings, cross_th, cross_len, angle = ApertureMacro.default2zero(9, mods)
        val = ApertureMacro.default2zero(9, mods)
        x = val[0]
        y = val[1]
        dia = val[2]
        thickness = val[3]
        gap = val[4]
        nrings = val[5]
        cross_th = val[6]
        cross_len = val[7]
        angle = val[8]

        r = dia / 2 - thickness / 2
        result = Point((x, y)).buffer(r).exterior.buffer(thickness / 2.0)
        ring = Point((x, y)).buffer(r).exterior.buffer(thickness / 2.0)  # Need a copy!

        i = 1  # Number of rings created so far

        # ## If the ring does not have an interior it means that it is
        # ## a disk. Then stop.
        while len(ring.interiors) > 0 and i < nrings:
            r -= thickness + gap
            if r <= 0:
                break
            ring = Point((x, y)).buffer(r).exterior.buffer(thickness / 2.0)
            result = unary_union([result, ring])
            i += 1

        # ## Crosshair
        hor = LineString([(x - cross_len, y), (x + cross_len, y)]).buffer(cross_th / 2.0, cap_style=2)
        ver = LineString([(x, y - cross_len), (x, y + cross_len)]).buffer(cross_th / 2.0, cap_style=2)
        result = unary_union([result, hor, ver])

        return {"pol": 1, "geometry": result}

    @staticmethod
    def make_thermal(mods):
        """
        Note: Specs indicate that rotation is only allowed if the center
        (x, y) == (0, 0). I will tolerate breaking this rule.

        :param mods: [x-center, y-center, diameter-outside, diameter-inside,
            gap-thickness, rotation angle around origin]
        :return:
        """

        # x, y, dout, din, t, angle = ApertureMacro.default2zero(6, mods)
        val = ApertureMacro.default2zero(6, mods)
        x = val[0]
        y = val[1]
        dout = val[2]
        din = val[3]
        t = val[4]
        angle = val[5]

        ring = Point((x, y)).buffer(dout / 2.0).difference(Point((x, y)).buffer(din / 2.0))
        hline = LineString([(x - dout / 2.0, y), (x + dout / 2.0, y)]).buffer(t / 2.0, cap_style=3)
        vline = LineString([(x, y - dout / 2.0), (x, y + dout / 2.0)]).buffer(t / 2.0, cap_style=3)
        thermal = ring.difference(hline.union(vline))

        return {"pol": 1, "geometry": thermal}

    def make_geometry(self, modifiers):
        """
        Runs the macro for the given modifiers and generates
        the corresponding geometry.

        :param modifiers: Modifiers (parameters) for this macro
        :type modifiers: list
        :return: Shapely geometry
        :rtype: shapely.geometry.polygon
        """

        # ## Primitive makers
        makers = {
            "1": ApertureMacro.make_circle,
            "2": ApertureMacro.make_vectorline,
            "20": ApertureMacro.make_vectorline,
            "21": ApertureMacro.make_centerline,
            "22": ApertureMacro.make_lowerleftline,
            "4": ApertureMacro.make_outline,
            "5": ApertureMacro.make_polygon,
            "6": ApertureMacro.make_moire,
            "7": ApertureMacro.make_thermal
        }

        # ## Store modifiers as local variables
        modifiers = modifiers or []
        modifiers = [float(m) for m in modifiers]
        self.locvars = {}
        for i in range(0, len(modifiers)):
            self.locvars[str(i + 1)] = modifiers[i]

        # ## Parse
        self.primitives = []  # Cleanup
        self.geometry = Polygon()
        self.parse_content()

        # ## Make the geometry
        for primitive in self.primitives:
            # Make the primitive
            prim_geo = makers[str(int(primitive[0]))](primitive[1:])

            # Add it (according to polarity)
            # if self.geometry is None and prim_geo['pol'] == 1:
            #     self.geometry = prim_geo['geometry']
            #     continue
            if prim_geo['pol'] == 1:
                self.geometry = self.geometry.union(prim_geo['geometry'])
                continue
            if prim_geo['pol'] == 0:
                self.geometry = self.geometry.difference(prim_geo['geometry'])
                continue

        return self.geometry


class Geometry(object):
    """
    Base geometry class.
    """

    defaults = {
        "units": 'mm',
        # "geo_steps_per_circle": 128
    }

    def __init__(self, geo_steps_per_circle=None):
        # Units (in or mm)
        self.units = self.app.defaults["units"]
        self.decimals = self.app.decimals

        self.drawing_tolerance = 0.0
        self.tools = None

        # Final geometry: MultiPolygon or list (of geometry constructs)
        self.solid_geometry = None

        # Final geometry: MultiLineString or list (of LineString or Points)
        self.follow_geometry = None

        # Flattened geometry (list of paths only)
        self.flat_geometry = []

        # this is the calculated conversion factor when the file units are different than the ones in the app
        self.file_units_factor = 1

        # Index
        self.index = None

        self.geo_steps_per_circle = geo_steps_per_circle

        # variables to display the percentage of work done
        self.geo_len = 0
        self.old_disp_number = 0
        self.el_count = 0

        if self.app.is_legacy is False:
            self.temp_shapes = self.app.plotcanvas.new_shape_collection(layers=1)
        else:
            from appGUI.PlotCanvasLegacy import ShapeCollectionLegacy
            self.temp_shapes = ShapeCollectionLegacy(obj=self, app=self.app, name='camlib.geometry')

        # Attributes to be included in serialization
        self.ser_attrs = ["units", 'solid_geometry', 'follow_geometry', 'tools']

    def plot_temp_shapes(self, element, color='red'):

        try:
            for sub_el in element:
                self.plot_temp_shapes(sub_el)
        except TypeError:  # Element is not iterable...
            # self.add_shape(shape=element, color=color, visible=visible, layer=0)
            self.temp_shapes.add(tolerance=float(self.app.defaults["global_tolerance"]),
                                 shape=element, color=color, visible=True, layer=0)

    def make_index(self):
        self.flatten()
        self.index = FlatCAMRTree()

        for i, g in enumerate(self.flat_geometry):
            self.index.insert(i, g)

    def add_circle(self, origin, radius, tool=None):
        """
        Adds a circle to the object.

        :param origin:  Center of the circle.
        :param radius:  Radius of the circle.
        :param tool:    A tool in the Tools dictionary attribute of the object
        :return: None
        """

        if self.solid_geometry is None:
            self.solid_geometry = []

        new_circle = Point(origin).buffer(radius, int(self.geo_steps_per_circle))
        if not new_circle.is_valid:
            return "fail"

        # add to the solid_geometry
        try:
            self.solid_geometry.append(new_circle)
        except TypeError:
            try:
                self.solid_geometry = self.solid_geometry.union(new_circle)
            except Exception as e:
                log.error("Failed to run union on polygons. %s" % str(e))
                return "fail"

        # add in tools solid_geometry
        if tool is None or tool not in self.tools:
            tool = 1
        self.tools[tool]['solid_geometry'].append(new_circle)

        # calculate bounds
        try:
            xmin, ymin, xmax, ymax = self.bounds()

            self.options['xmin'] = xmin
            self.options['ymin'] = ymin
            self.options['xmax'] = xmax
            self.options['ymax'] = ymax
        except Exception as e:
            log.error("Failed. The object has no bounds properties. %s" % str(e))

    def add_polygon(self, points, tool=None):
        """
        Adds a polygon to the object (by union)

        :param points:  The vertices of the polygon.
        :param tool:    A tool in the Tools dictionary attribute of the object
        :return:        None
        """
        if self.solid_geometry is None:
            self.solid_geometry = []

        new_poly = Polygon(points)
        if not new_poly.is_valid:
            return "fail"

        # add to the solid_geometry
        if type(self.solid_geometry) is list:
            self.solid_geometry.append(new_poly)
        else:
            try:
                self.solid_geometry = self.solid_geometry.union(Polygon(points))
            except Exception as e:
                log.error("Failed to run union on polygons. %s" % str(e))
                return "fail"

        # add in tools solid_geometry
        if tool is None or tool not in self.tools:
            tool = 1
        self.tools[tool]['solid_geometry'].append(new_poly)

        # calculate bounds
        try:
            xmin, ymin, xmax, ymax = self.bounds()

            self.options['xmin'] = xmin
            self.options['ymin'] = ymin
            self.options['xmax'] = xmax
            self.options['ymax'] = ymax
        except Exception as e:
            log.error("Failed. The object has no bounds properties. %s" % str(e))

    def add_polyline(self, points, tool=None):
        """
        Adds a polyline to the object (by union)

        :param points:  The vertices of the polyline.
        :param tool:    A tool in the Tools dictionary attribute of the object
        :return:        None
        """
        if self.solid_geometry is None:
            self.solid_geometry = []

        new_line = LineString(points)
        if not new_line.is_valid:
            return "fail"

        # add to the solid_geometry
        if type(self.solid_geometry) is list:
            self.solid_geometry.append(new_line)
        else:
            try:
                self.solid_geometry = self.solid_geometry.union(new_line)
            except Exception as e:
                log.error("Failed to run union on polylines. %s" % str(e))
                return "fail"

        # add in tools solid_geometry
        if tool is None or tool not in self.tools:
            tool = 1
        self.tools[tool]['solid_geometry'].append(new_line)

        # calculate bounds
        try:
            xmin, ymin, xmax, ymax = self.bounds()

            self.options['xmin'] = xmin
            self.options['ymin'] = ymin
            self.options['xmax'] = xmax
            self.options['ymax'] = ymax
        except Exception as e:
            log.error("Failed. The object has no bounds properties. %s" % str(e))

    def is_empty(self):
        if isinstance(self.solid_geometry, BaseGeometry) or isinstance(self.solid_geometry, Polygon) or \
                isinstance(self.solid_geometry, MultiPolygon):
            return self.solid_geometry.is_empty

        if isinstance(self.solid_geometry, list):
            return len(self.solid_geometry) == 0

        self.app.inform.emit('[ERROR_NOTCL] %s' % _("self.solid_geometry is neither BaseGeometry or list."))
        return

    def subtract_polygon(self, points):
        """
        Subtract polygon from the given object. This only operates on the paths in the original geometry,
        i.e. it converts polygons into paths.

        :param points: The vertices of the polygon.
        :return: none
        """
        if self.solid_geometry is None:
            self.solid_geometry = []

        # pathonly should be allways True, otherwise polygons are not subtracted
        flat_geometry = self.flatten(pathonly=True)
        log.debug("%d paths" % len(flat_geometry))

        if not isinstance(points, Polygon):
            polygon = Polygon(points)
        else:
            polygon = points
        toolgeo = unary_union(polygon)
        diffs = []
        for target in flat_geometry:
            if isinstance(target, LineString) or isinstance(target, LineString) or isinstance(target, MultiLineString):
                diffs.append(target.difference(toolgeo))
            else:
                log.warning("Not implemented.")

        self.solid_geometry = unary_union(diffs)

    def bounds(self, flatten=False):
        """
        Returns coordinates of rectangular bounds
        of geometry: (xmin, ymin, xmax, ymax).
        :param flatten: will flatten the solid_geometry if True
        :return:
        """
        # fixed issue of getting bounds only for one level lists of objects
        # now it can get bounds for nested lists of objects

        log.debug("camlib.Geometry.bounds()")

        if self.solid_geometry is None:
            log.debug("solid_geometry is None")
            return 0, 0, 0, 0

        def bounds_rec(obj):
            if type(obj) is list:
                gminx = np.Inf
                gminy = np.Inf
                gmaxx = -np.Inf
                gmaxy = -np.Inf

                for k in obj:
                    if type(k) is dict:
                        for key in k:
                            minx_, miny_, maxx_, maxy_ = bounds_rec(k[key])
                            gminx = min(gminx, minx_)
                            gminy = min(gminy, miny_)
                            gmaxx = max(gmaxx, maxx_)
                            gmaxy = max(gmaxy, maxy_)
                    else:
                        try:
                            if k.is_empty:
                                continue
                        except Exception:
                            pass

                        minx_, miny_, maxx_, maxy_ = bounds_rec(k)
                        gminx = min(gminx, minx_)
                        gminy = min(gminy, miny_)
                        gmaxx = max(gmaxx, maxx_)
                        gmaxy = max(gmaxy, maxy_)
                return gminx, gminy, gmaxx, gmaxy
            else:
                # it's a Shapely object, return it's bounds
                return obj.bounds

        if self.multigeo is True:
            minx_list = []
            miny_list = []
            maxx_list = []
            maxy_list = []

            for tool in self.tools:
                working_geo = self.tools[tool]['solid_geometry']

                if flatten:
                    self.flatten(geometry=working_geo, reset=True)
                    working_geo = self.flat_geometry

                minx, miny, maxx, maxy = bounds_rec(working_geo)
                minx_list.append(minx)
                miny_list.append(miny)
                maxx_list.append(maxx)
                maxy_list.append(maxy)

            return min(minx_list), min(miny_list), max(maxx_list), max(maxy_list)
        else:
            if flatten:
                self.flatten(reset=True)
                self.solid_geometry = self.flat_geometry

            bounds_coords = bounds_rec(self.solid_geometry)
            return bounds_coords

        # try:
        #     # from here: http://rightfootin.blogspot.com/2006/09/more-on-python-flatten.html
        #     def flatten(l, ltypes=(list, tuple)):
        #         ltype = type(l)
        #         l = list(l)
        #         i = 0
        #         while i < len(l):
        #             while isinstance(l[i], ltypes):
        #                 if not l[i]:
        #                     l.pop(i)
        #                     i -= 1
        #                     break
        #                 else:
        #                     l[i:i + 1] = l[i]
        #             i += 1
        #         return ltype(l)
        #
        #     log.debug("Geometry->bounds()")
        #     if self.solid_geometry is None:
        #         log.debug("solid_geometry is None")
        #         return 0, 0, 0, 0
        #
        #     if type(self.solid_geometry) is list:
        #         if len(self.solid_geometry) == 0:
        #             log.debug('solid_geometry is empty []')
        #             return 0, 0, 0, 0
        #         return unary_union(flatten(self.solid_geometry)).bounds
        #     else:
        #         return self.solid_geometry.bounds
        # except Exception as e:
        #     self.app.inform.emit("[ERROR_NOTCL] Error cause: %s" % str(e))

        # log.debug("Geometry->bounds()")
        # if self.solid_geometry is None:
        #     log.debug("solid_geometry is None")
        #     return 0, 0, 0, 0
        #
        # if type(self.solid_geometry) is list:
        #     if len(self.solid_geometry) == 0:
        #         log.debug('solid_geometry is empty []')
        #         return 0, 0, 0, 0
        #     return unary_union(self.solid_geometry).bounds
        # else:
        #     return self.solid_geometry.bounds

    def find_polygon(self, point, geoset=None):
        """
        Find an object that object.contains(Point(point)) in
        poly, which can can be iterable, contain iterable of, or
        be itself an implementer of .contains().

        :param point: See description
        :param geoset: a polygon or list of polygons where to find if the param point is contained
        :return: Polygon containing point or None.
        """

        if geoset is None:
            geoset = self.solid_geometry

        try:  # Iterable
            for sub_geo in geoset:
                p = self.find_polygon(point, geoset=sub_geo)
                if p is not None:
                    return p
        except TypeError:  # Non-iterable
            try:  # Implements .contains()
                if isinstance(geoset, LinearRing):
                    geoset = Polygon(geoset)
                if geoset.contains(Point(point)):
                    return geoset
            except AttributeError:  # Does not implement .contains()
                return None

        return None

    def get_interiors(self, geometry=None):

        interiors = []

        if geometry is None:
            geometry = self.solid_geometry

        # ## If iterable, expand recursively.
        try:
            for geo in geometry:
                interiors.extend(self.get_interiors(geometry=geo))

        # ## Not iterable, get the interiors if polygon.
        except TypeError:
            if type(geometry) == Polygon:
                interiors.extend(geometry.interiors)

        return interiors

    def get_exteriors(self, geometry=None):
        """
        Returns all exteriors of polygons in geometry. Uses
        ``self.solid_geometry`` if geometry is not provided.

        :param geometry: Shapely type or list or list of list of such.
        :return: List of paths constituting the exteriors
           of polygons in geometry.
        """

        exteriors = []

        if geometry is None:
            geometry = self.solid_geometry

        # ## If iterable, expand recursively.
        try:
            for geo in geometry:
                exteriors.extend(self.get_exteriors(geometry=geo))

        # ## Not iterable, get the exterior if polygon.
        except TypeError:
            if type(geometry) == Polygon:
                exteriors.append(geometry.exterior)

        return exteriors

    def flatten(self, geometry=None, reset=True, pathonly=False):
        """
        Creates a list of non-iterable linear geometry objects.
        Polygons are expanded into its exterior and interiors if specified.

        Results are placed in self.flat_geometry

        :param geometry: Shapely type or list or list of list of such.
        :param reset: Clears the contents of self.flat_geometry.
        :param pathonly: Expands polygons into linear elements.
        """

        if geometry is None:
            geometry = self.solid_geometry

        if reset:
            self.flat_geometry = []

        # ## If iterable, expand recursively.
        try:
            for geo in geometry:
                if geo is not None:
                    self.flatten(geometry=geo,
                                 reset=False,
                                 pathonly=pathonly)

        # ## Not iterable, do the actual indexing and add.
        except TypeError:
            if pathonly and type(geometry) == Polygon:
                self.flat_geometry.append(geometry.exterior)
                self.flatten(geometry=geometry.interiors,
                             reset=False,
                             pathonly=True)
            else:
                self.flat_geometry.append(geometry)

        return self.flat_geometry

    # def make2Dstorage(self):
    #
    #     self.flatten()
    #
    #     def get_pts(o):
    #         pts = []
    #         if type(o) == Polygon:
    #             g = o.exterior
    #             pts += list(g.coords)
    #             for i in o.interiors:
    #                 pts += list(i.coords)
    #         else:
    #             pts += list(o.coords)
    #         return pts
    #
    #     storage = FlatCAMRTreeStorage()
    #     storage.get_points = get_pts
    #     for shape in self.flat_geometry:
    #         storage.insert(shape)
    #     return storage

    # def flatten_to_paths(self, geometry=None, reset=True):
    #     """
    #     Creates a list of non-iterable linear geometry elements and
    #     indexes them in rtree.
    #
    #     :param geometry: Iterable geometry
    #     :param reset: Wether to clear (True) or append (False) to self.flat_geometry
    #     :return: self.flat_geometry, self.flat_geometry_rtree
    #     """
    #
    #     if geometry is None:
    #         geometry = self.solid_geometry
    #
    #     if reset:
    #         self.flat_geometry = []
    #
    #     # ## If iterable, expand recursively.
    #     try:
    #         for geo in geometry:
    #             self.flatten_to_paths(geometry=geo, reset=False)
    #
    #     # ## Not iterable, do the actual indexing and add.
    #     except TypeError:
    #         if type(geometry) == Polygon:
    #             g = geometry.exterior
    #             self.flat_geometry.append(g)
    #
    #             # ## Add first and last points of the path to the index.
    #             self.flat_geometry_rtree.insert(len(self.flat_geometry) - 1, g.coords[0])
    #             self.flat_geometry_rtree.insert(len(self.flat_geometry) - 1, g.coords[-1])
    #
    #             for interior in geometry.interiors:
    #                 g = interior
    #                 self.flat_geometry.append(g)
    #                 self.flat_geometry_rtree.insert(len(self.flat_geometry) - 1, g.coords[0])
    #                 self.flat_geometry_rtree.insert(len(self.flat_geometry) - 1, g.coords[-1])
    #         else:
    #             g = geometry
    #             self.flat_geometry.append(g)
    #             self.flat_geometry_rtree.insert(len(self.flat_geometry) - 1, g.coords[0])
    #             self.flat_geometry_rtree.insert(len(self.flat_geometry) - 1, g.coords[-1])
    #
    #     return self.flat_geometry, self.flat_geometry_rtree

    def isolation_geometry(self, offset, geometry=None, iso_type=2, corner=None, follow=None, passes=0,
                           prog_plot=False):
        """
        Creates contours around geometry at a given
        offset distance.

        :param offset:      Offset distance.
        :type offset:       float
        :param geometry     The geometry to work with
        :param iso_type:    type of isolation, can be 0 = exteriors or 1 = interiors or 2 = both (complete)
        :param corner:      type of corner for the isolation:
                            0 = round; 1 = square; 2= beveled (line that connects the ends)
        :param follow:      whether the geometry to be isolated is a follow_geometry
        :param passes:      current pass out of possible multiple passes for which the isolation is done
        :param prog_plot:   type of plotting: "normal" or "progressive"
        :return:            The buffered geometry.
        :rtype:             Shapely.MultiPolygon or Shapely.Polygon
        """

        if self.app.abort_flag:
            # graceful abort requested by the user
            raise grace

        geo_iso = []

        if follow:
            return geometry

        if geometry:
            working_geo = geometry
        else:
            working_geo = self.solid_geometry

        try:
            geo_len = len(working_geo)
        except TypeError:
            geo_len = 1

        old_disp_number = 0
        pol_nr = 0
        # yet, it can be done by issuing an unary_union in the end, thus getting rid of the overlapping geo
        try:
            for pol in working_geo:
                if self.app.abort_flag:
                    # graceful abort requested by the user
                    raise grace
                if offset == 0:
                    temp_geo = pol
                else:
                    corner_type = 1 if corner is None else corner
                    temp_geo = pol.buffer(offset, int(self.geo_steps_per_circle), join_style=corner_type)

                geo_iso.append(temp_geo)

                pol_nr += 1

                # activity view update
                disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 100]))

                if old_disp_number < disp_number <= 100:
                    self.app.proc_container.update_view_text(' %s %d: %d%%' %
                                                             (_("Pass"), int(passes + 1), int(disp_number)))
                    old_disp_number = disp_number
        except TypeError:
            # taking care of the case when the self.solid_geometry is just a single Polygon, not a list or a
            # MultiPolygon (not an iterable)
            if offset == 0:
                temp_geo = working_geo
            else:
                corner_type = 1 if corner is None else corner
                temp_geo = working_geo.buffer(offset, int(self.geo_steps_per_circle), join_style=corner_type)

            geo_iso.append(temp_geo)

        self.app.proc_container.update_view_text(' %s' % _("Buffering"))
        geo_iso = unary_union(geo_iso)

        self.app.proc_container.update_view_text('')
        # end of replaced block

        if iso_type == 2:
            ret_geo = geo_iso
        elif iso_type == 0:
            self.app.proc_container.update_view_text(' %s' % _("Get Exteriors"))
            ret_geo = self.get_exteriors(geo_iso)
        elif iso_type == 1:
            self.app.proc_container.update_view_text(' %s' % _("Get Interiors"))
            ret_geo =  self.get_interiors(geo_iso)
        else:
            log.debug("Geometry.isolation_geometry() --> Type of isolation not supported")
            return "fail"

        if prog_plot == 'progressive':
            for elem in ret_geo:
                self.plot_temp_shapes(elem)

        return ret_geo

    def flatten_list(self, obj_list):
        for item in obj_list:
            if isinstance(item, Iterable) and not isinstance(item, (str, bytes)):
                yield from self.flatten_list(item)
            else:
                yield item

    def import_svg(self, filename, object_type=None, flip=True, units=None):
        """
        Imports shapes from an SVG file into the object's geometry.

        :param filename:    Path to the SVG file.
        :type filename:     str
        :param object_type: parameter passed further along
        :param flip:        Flip the vertically.
        :type flip:         bool
        :param units:       FlatCAM units
        :return:            None
        """

        log.debug("camlib.Geometry.import_svg()")

        # Parse into list of shapely objects
        svg_tree = ET.parse(filename)
        svg_root = svg_tree.getroot()

        # Change origin to bottom left
        # h = float(svg_root.get('height'))
        # w = float(svg_root.get('width'))
        h = svgparselength(svg_root.get('height'))[0]  # TODO: No units support yet

        units = self.app.defaults['units'] if units is None else units
        res = self.app.defaults['geometry_circle_steps']
        factor = svgparse_viewbox(svg_root)

        geos = getsvggeo(svg_root, object_type, units=units, res=res, factor=factor)
        if flip:
            geos = [translate(scale(g, 1.0, -1.0, origin=(0, 0)), yoff=h) for g in geos]

        # trying to optimize the resulting geometry by merging contiguous lines
        geos = list(self.flatten_list(geos))
        geos_polys = []
        geos_lines = []
        for g in geos:
            if isinstance(g, Polygon):
                geos_polys.append(g)
            else:
                geos_lines.append(g)

        merged_lines = linemerge(geos_lines)
        geos = geos_polys
        try:
            for l in merged_lines:
                geos.append(l)
        except TypeError:
            geos.append(merged_lines)
            
        # Add to object
        if self.solid_geometry is None:
            self.solid_geometry = []

        if type(self.solid_geometry) is list:
            if type(geos) is list:
                self.solid_geometry += geos
            else:
                self.solid_geometry.append(geos)
        else:  # It's shapely geometry
            self.solid_geometry = [self.solid_geometry, geos]

        # flatten the self.solid_geometry list for import_svg() to import SVG as Gerber
        self.solid_geometry = list(self.flatten_list(self.solid_geometry))

        geos_text = getsvgtext(svg_root, object_type, units=units)
        if geos_text is not None:
            geos_text_f = []
            if flip:
                # Change origin to bottom left
                for i in geos_text:
                    __, minimy, __, maximy = i.bounds
                    h2 = (maximy - minimy) * 0.5
                    geos_text_f.append(translate(scale(i, 1.0, -1.0, origin=(0, 0)), yoff=(h + h2)))
            if geos_text_f:
                self.solid_geometry = self.solid_geometry + geos_text_f

        tooldia = float(self.app.defaults["geometry_cnctooldia"])
        tooldia = float('%.*f' % (self.decimals, tooldia))

        new_data = {k: v for k, v in self.options.items()}

        self.tools.update({
            1: {
                'tooldia': tooldia,
                'offset': 'Path',
                'offset_value': 0.0,
                'type': 'Rough',
                'tool_type': 'C1',
                'data': deepcopy(new_data),
                'solid_geometry': self.solid_geometry
            }
        })

        self.tools[1]['data']['name'] = self.options['name']

    def import_dxf_as_geo(self, filename, units='MM'):
        """
        Imports shapes from an DXF file into the object's geometry.

        :param filename:    Path to the DXF file.
        :type filename:     str
        :param units:       Application units
        :return: None
        """
        log.debug("Parsing DXF file geometry into a Geometry object solid geometry.")

        # Parse into list of shapely objects
        dxf = ezdxf.readfile(filename)
        geos = getdxfgeo(dxf)

        # trying to optimize the resulting geometry by merging contiguous lines
        geos = list(self.flatten_list(geos))
        geos_polys = []
        geos_lines = []
        for g in geos:
            if isinstance(g, Polygon):
                geos_polys.append(g)
            else:
                geos_lines.append(g)

        merged_lines = linemerge(geos_lines)
        geos = geos_polys
        for l in merged_lines:
            geos.append(l)

        # Add to object
        if self.solid_geometry is None:
            self.solid_geometry = []

        if type(self.solid_geometry) is list:
            if type(geos) is list:
                self.solid_geometry += geos
            else:
                self.solid_geometry.append(geos)
        else:  # It's shapely geometry
            self.solid_geometry = [self.solid_geometry, geos]

        tooldia = float(self.app.defaults["geometry_cnctooldia"])
        tooldia = float('%.*f' % (self.decimals, tooldia))

        new_data = {k: v for k, v in self.options.items()}

        self.tools.update({
            1: {
                'tooldia': tooldia,
                'offset': 'Path',
                'offset_value': 0.0,
                'type': 'Rough',
                'tool_type': 'C1',
                'data': deepcopy(new_data),
                'solid_geometry': self.solid_geometry
            }
        })

        self.tools[1]['data']['name'] = self.options['name']

        # commented until this function is ready
        # geos_text = getdxftext(dxf, object_type, units=units)
        # if geos_text is not None:
        #     geos_text_f = []
        #     self.solid_geometry = [self.solid_geometry, geos_text_f]

    def import_image(self, filename, flip=True, units='MM', dpi=96, mode='black', mask=None):
        """
        Imports shapes from an IMAGE file into the object's geometry.

        :param filename:    Path to the IMAGE file.
        :type filename:     str
        :param flip:        Flip the object vertically.
        :type flip:         bool
        :param units:       FlatCAM units
        :type units:        str
        :param dpi:         dots per inch on the imported image
        :param mode:        how to import the image: as 'black' or 'color'
        :type mode:         str
        :param mask:        level of detail for the import
        :return:            None
        """
        if mask is None:
            mask = [128, 128, 128, 128]

        scale_factor = 25.4 / dpi if units.lower() == 'mm' else 1 / dpi

        geos = []
        unscaled_geos = []

        with rasterio.open(filename) as src:
            # if filename.lower().rpartition('.')[-1] == 'bmp':
            #     red = green = blue = src.read(1)
            #     print("BMP")
            # elif filename.lower().rpartition('.')[-1] == 'png':
            #     red, green, blue, alpha = src.read()
            # elif filename.lower().rpartition('.')[-1] == 'jpg':
            #     red, green, blue = src.read()

            red = green = blue = src.read(1)

            try:
                green = src.read(2)
            except Exception:
                pass

            try:
                blue = src.read(3)
            except Exception:
                pass

        if mode == 'black':
            mask_setting = red <= mask[0]
            total = red
            log.debug("Image import as monochrome.")
        else:
            mask_setting = (red <= mask[1]) + (green <= mask[2]) + (blue <= mask[3])
            total = np.zeros(red.shape, dtype=np.float32)
            for band in red, green, blue:
                total += band
            total /= 3
            log.debug("Image import as colored. Thresholds are: R = %s , G = %s, B = %s" %
                      (str(mask[1]), str(mask[2]), str(mask[3])))

        for geom, val in shapes(total, mask=mask_setting):
            unscaled_geos.append(shape(geom))

        for g in unscaled_geos:
            geos.append(scale(g, scale_factor, scale_factor, origin=(0, 0)))

        if flip:
            geos = [translate(scale(g, 1.0, -1.0, origin=(0, 0))) for g in geos]

        # Add to object
        if self.solid_geometry is None:
            self.solid_geometry = []

        if type(self.solid_geometry) is list:
            # self.solid_geometry.append(unary_union(geos))
            if type(geos) is list:
                self.solid_geometry += geos
            else:
                self.solid_geometry.append(geos)
        else:  # It's shapely geometry
            self.solid_geometry = [self.solid_geometry, geos]

        # flatten the self.solid_geometry list for import_svg() to import SVG as Gerber
        self.solid_geometry = list(self.flatten_list(self.solid_geometry))
        self.solid_geometry = unary_union(self.solid_geometry)

        # self.solid_geometry = MultiPolygon(self.solid_geometry)
        # self.solid_geometry = self.solid_geometry.buffer(0.00000001)
        # self.solid_geometry = self.solid_geometry.buffer(-0.00000001)

    def size(self):
        """
        Returns (width, height) of rectangular
        bounds of geometry.
        """
        if self.solid_geometry is None:
            log.warning("Solid_geometry not computed yet.")
            return 0
        bounds = self.bounds()
        return bounds[2] - bounds[0], bounds[3] - bounds[1]

    def get_empty_area(self, boundary=None):
        """
        Returns the complement of self.solid_geometry within
        the given boundary polygon. If not specified, it defaults to
        the rectangular bounding box of self.solid_geometry.
        """
        if boundary is None:
            boundary = self.solid_geometry.envelope
        return boundary.difference(self.solid_geometry)

    def clear_polygon(self, polygon, tooldia, steps_per_circle, overlap=0.15, connect=True, contour=True,
                      prog_plot=False):
        """
        Creates geometry inside a polygon for a tool to cover
        the whole area.

        This algorithm shrinks the edges of the polygon and takes
        the resulting edges as toolpaths.

        :param polygon:             Polygon to clear.
        :param tooldia:             Diameter of the tool.
        :param steps_per_circle:    number of linear segments to be used to approximate a circle
        :param overlap:             Overlap of toolpasses.
        :param connect:             Draw lines between disjoint segments to
                                    minimize tool lifts.
        :param contour:             Paint around the edges. Inconsequential in
                                    this painting method.
        :param prog_plot:           boolean; if Ture use the progressive plotting
        :return:
        """

        # log.debug("camlib.clear_polygon()")
        assert type(polygon) == Polygon or type(polygon) == MultiPolygon, \
            "Expected a Polygon or MultiPolygon, got %s" % type(polygon)

        # ## The toolpaths
        # Index first and last points in paths
        def get_pts(o):
            return [o.coords[0], o.coords[-1]]

        geoms = FlatCAMRTreeStorage()
        geoms.get_points = get_pts

        # Can only result in a Polygon or MultiPolygon
        # NOTE: The resulting polygon can be "empty".
        current = polygon.buffer((-tooldia / 1.999999), int(steps_per_circle))
        if current.area == 0:
            # Otherwise, trying to to insert current.exterior == None
            # into the FlatCAMStorage will fail.
            # print("Area is None")
            return None

        # current can be a MultiPolygon
        try:
            for p in current:
                geoms.insert(p.exterior)
                for i in p.interiors:
                    geoms.insert(i)

        # Not a Multipolygon. Must be a Polygon
        except TypeError:
            geoms.insert(current.exterior)
            for i in current.interiors:
                geoms.insert(i)

        while True:
            if self.app.abort_flag:
                # graceful abort requested by the user
                raise grace

            # provide the app with a way to process the GUI events when in a blocking loop
            QtWidgets.QApplication.processEvents()

            # Can only result in a Polygon or MultiPolygon
            current = current.buffer(-tooldia * (1 - overlap), int(steps_per_circle))
            if current.area > 0:

                # current can be a MultiPolygon
                try:
                    for p in current:
                        geoms.insert(p.exterior)
                        for i in p.interiors:
                            geoms.insert(i)
                            if prog_plot:
                                self.plot_temp_shapes(p)

                # Not a Multipolygon. Must be a Polygon
                except TypeError:
                    geoms.insert(current.exterior)
                    if prog_plot:
                        self.plot_temp_shapes(current.exterior)
                    for i in current.interiors:
                        geoms.insert(i)
                        if prog_plot:
                            self.plot_temp_shapes(i)
            else:
                log.debug("camlib.Geometry.clear_polygon() --> Current Area is zero")
                break

        if prog_plot:
            self.temp_shapes.redraw()

        # Optimization: Reduce lifts
        if connect:
            # log.debug("Reducing tool lifts...")
            geoms = Geometry.paint_connect(geoms, polygon, tooldia, int(steps_per_circle))

        return geoms

    def clear_polygon2(self, polygon_to_clear, tooldia, steps_per_circle, seedpoint=None, overlap=0.15,
                       connect=True, contour=True, prog_plot=False):
        """
        Creates geometry inside a polygon for a tool to cover
        the whole area.

        This algorithm starts with a seed point inside the polygon
        and draws circles around it. Arcs inside the polygons are
        valid cuts. Finalizes by cutting around the inside edge of
        the polygon.

        :param polygon_to_clear:    Shapely.geometry.Polygon
        :param steps_per_circle:    how many linear segments to use to approximate a circle
        :param tooldia:             Diameter of the tool
        :param seedpoint:           Shapely.geometry.Point or None
        :param overlap:             Tool fraction overlap bewteen passes
        :param connect:             Connect disjoint segment to minumize tool lifts
        :param contour:             Cut countour inside the polygon.
        :param prog_plot:           boolean; if True use the progressive plotting
        :return:                    List of toolpaths covering polygon.
        :rtype:                     FlatCAMRTreeStorage | None
        """

        # log.debug("camlib.clear_polygon2()")

        # Current buffer radius
        radius = tooldia / 2 * (1 - overlap)

        # ## The toolpaths
        # Index first and last points in paths
        def get_pts(o):
            return [o.coords[0], o.coords[-1]]

        geoms = FlatCAMRTreeStorage()
        geoms.get_points = get_pts

        # Path margin
        path_margin = polygon_to_clear.buffer(-tooldia / 2, int(steps_per_circle))

        if path_margin.is_empty or path_margin is None:
            return None

        # Estimate good seedpoint if not provided.
        if seedpoint is None:
            seedpoint = path_margin.representative_point()

        # Grow from seed until outside the box. The polygons will
        # never have an interior, so take the exterior LinearRing.
        while True:
            if self.app.abort_flag:
                # graceful abort requested by the user
                raise grace

            # provide the app with a way to process the GUI events when in a blocking loop
            QtWidgets.QApplication.processEvents()

            path = Point(seedpoint).buffer(radius, int(steps_per_circle)).exterior
            path = path.intersection(path_margin)

            # Touches polygon?
            if path.is_empty:
                break
            else:
                # geoms.append(path)
                # geoms.insert(path)
                # path can be a collection of paths.
                try:
                    for p in path:
                        geoms.insert(p)
                        if prog_plot:
                            self.plot_temp_shapes(p)
                except TypeError:
                    geoms.insert(path)
                    if prog_plot:
                        self.plot_temp_shapes(path)

                if prog_plot:
                    self.temp_shapes.redraw()

            radius += tooldia * (1 - overlap)

        # Clean inside edges (contours) of the original polygon
        if contour:
            buffered_poly = autolist(polygon_to_clear.buffer(-tooldia / 2, int(steps_per_circle)))
            outer_edges = [x.exterior for x in buffered_poly]

            inner_edges = []
            # Over resulting polygons
            for x in buffered_poly:
                for y in x.interiors:  # Over interiors of each polygon
                    inner_edges.append(y)
            # geoms += outer_edges + inner_edges
            for g in outer_edges + inner_edges:
                if g and not g.is_empty:
                    geoms.insert(g)
                    if prog_plot:
                        self.plot_temp_shapes(g)

        if prog_plot:
            self.temp_shapes.redraw()

        # Optimization connect touching paths
        # log.debug("Connecting paths...")
        # geoms = Geometry.path_connect(geoms)

        # Optimization: Reduce lifts
        if connect:
            # log.debug("Reducing tool lifts...")
            geoms_conn = Geometry.paint_connect(geoms, polygon_to_clear, tooldia, steps_per_circle)
            if geoms_conn:
                return geoms_conn

        return geoms

    def clear_polygon3(self, polygon, tooldia, steps_per_circle, overlap=0.15, connect=True, contour=True,
                       prog_plot=False):
        """
        Creates geometry inside a polygon for a tool to cover
        the whole area.

        This algorithm draws horizontal lines inside the polygon.

        :param polygon:             The polygon being painted.
        :type polygon:              shapely.geometry.Polygon
        :param tooldia:             Tool diameter.
        :param steps_per_circle:    how many linear segments to use to approximate a circle
        :param overlap:             Tool path overlap percentage.
        :param connect:             Connect lines to avoid tool lifts.
        :param contour:             Paint around the edges.
        :param prog_plot:           boolean; if to use the progressive plotting
        :return:
        """

        # log.debug("camlib.clear_polygon3()")
        if not isinstance(polygon, Polygon):
            log.debug("camlib.Geometry.clear_polygon3() --> Not a Polygon but %s" % str(type(polygon)))
            return None

        # ## The toolpaths
        # Index first and last points in paths
        def get_pts(o):
            return [o.coords[0], o.coords[-1]]

        geoms = FlatCAMRTreeStorage()
        geoms.get_points = get_pts

        lines_trimmed = []

        # Bounding box
        left, bot, right, top = polygon.bounds

        try:
            margin_poly = polygon.buffer(-tooldia / 1.99999999, (int(steps_per_circle)))
        except Exception:
            log.debug("camlib.Geometry.clear_polygon3() --> Could not buffer the Polygon")
            return None

        # decide the direction of the lines
        if abs(left - right) >= abs(top - bot):
            # First line
            try:
                y = top - tooldia / 1.99999999
                while y > bot + tooldia / 1.999999999:
                    if self.app.abort_flag:
                        # graceful abort requested by the user
                        raise grace

                    # provide the app with a way to process the GUI events when in a blocking loop
                    QtWidgets.QApplication.processEvents()

                    line = LineString([(left, y), (right, y)])
                    line = line.intersection(margin_poly)
                    lines_trimmed.append(line)
                    y -= tooldia * (1 - overlap)
                    if prog_plot:
                        self.plot_temp_shapes(line)
                        self.temp_shapes.redraw()

                # Last line
                y = bot + tooldia / 2
                line = LineString([(left, y), (right, y)])
                line = line.intersection(margin_poly)

                try:
                    for ll in line:
                        lines_trimmed.append(ll)
                        if prog_plot:
                            self.plot_temp_shapes(ll)
                except TypeError:
                    lines_trimmed.append(line)
                    if prog_plot:
                        self.plot_temp_shapes(line)
            except Exception as e:
                log.debug('camlib.Geometry.clear_polygon3() Processing poly --> %s' % str(e))
                return None
        else:
            # First line
            try:
                x = left + tooldia / 1.99999999
                while x < right - tooldia / 1.999999999:
                    if self.app.abort_flag:
                        # graceful abort requested by the user
                        raise grace

                    # provide the app with a way to process the GUI events when in a blocking loop
                    QtWidgets.QApplication.processEvents()

                    line = LineString([(x, top), (x, bot)])
                    line = line.intersection(margin_poly)
                    lines_trimmed.append(line)
                    x += tooldia * (1 - overlap)
                    if prog_plot:
                        self.plot_temp_shapes(line)
                        self.temp_shapes.redraw()

                # Last line
                x = right + tooldia / 2
                line = LineString([(x, top), (x, bot)])
                line = line.intersection(margin_poly)

                try:
                    for ll in line:
                        lines_trimmed.append(ll)
                        if prog_plot:
                            self.plot_temp_shapes(ll)
                except TypeError:
                    lines_trimmed.append(line)
                    if prog_plot:
                        self.plot_temp_shapes(line)
            except Exception as e:
                log.debug('camlib.Geometry.clear_polygon3() Processing poly --> %s' % str(e))
                return None

        if prog_plot:
            self.temp_shapes.redraw()

        lines_trimmed = unary_union(lines_trimmed)

        # Add lines to storage
        try:
            for line in lines_trimmed:
                if isinstance(line, LineString) or isinstance(line, LinearRing):
                    if not line.is_empty:
                        geoms.insert(line)
                else:
                    log.debug("camlib.Geometry.clear_polygon3(). Not a line: %s" % str(type(line)))
        except TypeError:
            # in case lines_trimmed are not iterable (Linestring, LinearRing)
            if not lines_trimmed.is_empty:
                geoms.insert(lines_trimmed)

        # Add margin (contour) to storage
        if contour:
            try:
                for poly in margin_poly:
                    if isinstance(poly, Polygon) and not poly.is_empty:
                        geoms.insert(poly.exterior)
                        if prog_plot:
                            self.plot_temp_shapes(poly.exterior)
                        for ints in poly.interiors:
                            geoms.insert(ints)
                            if prog_plot:
                                self.plot_temp_shapes(ints)
            except TypeError:
                if isinstance(margin_poly, Polygon) and not margin_poly.is_empty:
                    marg_ext = margin_poly.exterior
                    geoms.insert(marg_ext)
                    if prog_plot:
                        self.plot_temp_shapes(margin_poly.exterior)
                    for ints in margin_poly.interiors:
                        geoms.insert(ints)
                        if prog_plot:
                            self.plot_temp_shapes(ints)

        if prog_plot:
            self.temp_shapes.redraw()

        # Optimization: Reduce lifts
        if connect:
            # log.debug("Reducing tool lifts...")
            geoms_conn = Geometry.paint_connect(geoms, polygon, tooldia, steps_per_circle)
            if geoms_conn:
                return geoms_conn

        return geoms

    def fill_with_lines(self, line, aperture_size, tooldia, steps_per_circle, overlap=0.15, connect=True, contour=True,
                        prog_plot=False):
        """
        Creates geometry of lines inside a polygon for a tool to cover
        the whole area.

        This algorithm draws parallel lines inside the polygon.

        :param line:                The target line that create painted polygon.
        :param aperture_size:       the size of the aperture that is used to draw the 'line' as a polygon
        :type line:                 shapely.geometry.LineString or shapely.geometry.MultiLineString
        :param tooldia:             Tool diameter.
        :param steps_per_circle:    how many linear segments to use to approximate a circle
        :param overlap:             Tool path overlap percentage.
        :param connect:             Connect lines to avoid tool lifts.
        :param contour:             Paint around the edges.
        :param prog_plot:           boolean; if to use the progressive plotting
        :return:
        """

        # log.debug("camlib.fill_with_lines()")
        if not isinstance(line, LineString):
            log.debug("camlib.Geometry.fill_with_lines() --> Not a LineString/MultiLineString but %s" % str(type(line)))
            return None

        # ## The toolpaths
        # Index first and last points in paths
        def get_pts(o):
            return [o.coords[0], o.coords[-1]]

        geoms = FlatCAMRTreeStorage()
        geoms.get_points = get_pts

        lines_trimmed = []

        polygon = line.buffer(aperture_size / 2.0, int(steps_per_circle))

        try:
            margin_poly = polygon.buffer(-tooldia / 2.0, int(steps_per_circle))
        except Exception:
            log.debug("camlib.Geometry.fill_with_lines() --> Could not buffer the Polygon, tool diameter too high")
            return None

        # First line
        try:
            delta = 0
            while delta < aperture_size / 2:
                if self.app.abort_flag:
                    # graceful abort requested by the user
                    raise grace

                # provide the app with a way to process the GUI events when in a blocking loop
                QtWidgets.QApplication.processEvents()

                new_line = line.parallel_offset(distance=delta, side='left', resolution=int(steps_per_circle))
                new_line = new_line.intersection(margin_poly)
                lines_trimmed.append(new_line)

                new_line = line.parallel_offset(distance=delta, side='right', resolution=int(steps_per_circle))
                new_line = new_line.intersection(margin_poly)
                lines_trimmed.append(new_line)

                delta += tooldia * (1 - overlap)
                if prog_plot:
                    self.plot_temp_shapes(new_line)
                    self.temp_shapes.redraw()

            # Last line
            delta = (aperture_size / 2) - (tooldia / 2.00000001)

            new_line = line.parallel_offset(distance=delta, side='left', resolution=int(steps_per_circle))
            new_line = new_line.intersection(margin_poly)
        except Exception as e:
            log.debug('camlib.Geometry.fill_with_lines() Processing poly --> %s' % str(e))
            return None

        try:
            for ll in new_line:
                lines_trimmed.append(ll)
                if prog_plot:
                    self.plot_temp_shapes(ll)
        except TypeError:
            lines_trimmed.append(new_line)
            if prog_plot:
                self.plot_temp_shapes(new_line)

        new_line = line.parallel_offset(distance=delta, side='right', resolution=int(steps_per_circle))
        new_line = new_line.intersection(margin_poly)

        try:
            for ll in new_line:
                lines_trimmed.append(ll)
                if prog_plot:
                    self.plot_temp_shapes(ll)
        except TypeError:
            lines_trimmed.append(new_line)
            if prog_plot:
                self.plot_temp_shapes(new_line)

        if prog_plot:
            self.temp_shapes.redraw()

        lines_trimmed = unary_union(lines_trimmed)

        # Add lines to storage
        try:
            for line in lines_trimmed:
                if isinstance(line, LineString) or isinstance(line, LinearRing):
                    geoms.insert(line)
                else:
                    log.debug("camlib.Geometry.fill_with_lines(). Not a line: %s" % str(type(line)))
        except TypeError:
            # in case lines_trimmed are not iterable (Linestring, LinearRing)
            geoms.insert(lines_trimmed)

        # Add margin (contour) to storage
        if contour:
            try:
                for poly in margin_poly:
                    if isinstance(poly, Polygon) and not poly.is_empty:
                        geoms.insert(poly.exterior)
                        if prog_plot:
                            self.plot_temp_shapes(poly.exterior)
                        for ints in poly.interiors:
                            geoms.insert(ints)
                            if prog_plot:
                                self.plot_temp_shapes(ints)
            except TypeError:
                if isinstance(margin_poly, Polygon) and not margin_poly.is_empty:
                    marg_ext = margin_poly.exterior
                    geoms.insert(marg_ext)
                    if prog_plot:
                        self.plot_temp_shapes(margin_poly.exterior)
                    for ints in margin_poly.interiors:
                        geoms.insert(ints)
                        if prog_plot:
                            self.plot_temp_shapes(ints)

        if prog_plot:
            self.temp_shapes.redraw()

        # Optimization: Reduce lifts
        if connect:
            # log.debug("Reducing tool lifts...")
            geoms_conn = Geometry.paint_connect(geoms, polygon, tooldia, steps_per_circle)
            if geoms_conn:
                return geoms_conn

        return geoms

    def scale(self, xfactor, yfactor, point=None):
        """
        Scales all of the object's geometry by a given factor. Override
        this method.
        :param xfactor: Number by which to scale on X axis.
        :type xfactor: float
        :param yfactor: Number by which to scale on Y axis.
        :type yfactor: float
        :param point: point to be used as reference for scaling; a tuple
        :return: None
        :rtype: None
        """
        return

    def offset(self, vect):
        """
        Offset the geometry by the given vector. Override this method.

        :param vect: (x, y) vector by which to offset the object.
        :type vect: tuple
        :return: None
        """
        return

    @staticmethod
    def paint_connect(storage, boundary, tooldia, steps_per_circle, max_walk=None):
        """
        Connects paths that results in a connection segment that is
        within the paint area. This avoids unnecessary tool lifting.

        :param storage: Geometry to be optimized.
        :type storage: FlatCAMRTreeStorage
        :param boundary: Polygon defining the limits of the paintable area.
        :type boundary: Polygon
        :param tooldia: Tool diameter.
        :rtype tooldia: float
        :param steps_per_circle: how many linear segments to use to approximate a circle
        :param max_walk: Maximum allowable distance without lifting tool.
        :type max_walk: float or None
        :return: Optimized geometry.
        :rtype: FlatCAMRTreeStorage
        """

        # If max_walk is not specified, the maximum allowed is
        # 10 times the tool diameter
        max_walk = max_walk or 10 * tooldia

        # Assuming geolist is a flat list of flat elements

        # ## Index first and last points in paths
        def get_pts(o):
            return [o.coords[0], o.coords[-1]]

        # storage = FlatCAMRTreeStorage()
        # storage.get_points = get_pts
        #
        # for shape in geolist:
        #     if shape is not None:
        #         # Make LlinearRings into linestrings otherwise
        #         # When chaining the coordinates path is messed up.
        #         storage.insert(LineString(shape))
        #         #storage.insert(shape)

        # ## Iterate over geometry paths getting the nearest each time.
        # optimized_paths = []
        optimized_paths = FlatCAMRTreeStorage()
        optimized_paths.get_points = get_pts
        path_count = 0
        current_pt = (0, 0)
        try:
            pt, geo = storage.nearest(current_pt)
        except StopIteration:
            log.debug("camlib.Geometry.paint_connect(). Storage empty")
            return None

        storage.remove(geo)

        geo = LineString(geo)
        current_pt = geo.coords[-1]
        try:
            while True:
                path_count += 1
                # log.debug("Path %d" % path_count)

                pt, candidate = storage.nearest(current_pt)
                storage.remove(candidate)

                candidate = LineString(candidate)

                # If last point in geometry is the nearest
                # then reverse coordinates.
                # but prefer the first one if last == first
                if pt != candidate.coords[0] and pt == candidate.coords[-1]:
                    # in place coordinates update deprecated in Shapely 2.0
                    # candidate.coords = list(candidate.coords)[::-1]
                    candidate = LineString(list(candidate.coords)[::-1])

                # Straight line from current_pt to pt.
                # Is the toolpath inside the geometry?
                walk_path = LineString([current_pt, pt])
                walk_cut = walk_path.buffer(tooldia / 2, int(steps_per_circle))

                if walk_cut.within(boundary) and walk_path.length < max_walk:
                    # log.debug("Walk to path #%d is inside. Joining." % path_count)

                    # Completely inside. Append...
                    # in place coordinates update deprecated in Shapely 2.0
                    # geo.coords = list(geo.coords) + list(candidate.coords)
                    geo = LineString(list(geo.coords) + list(candidate.coords))
                    # try:
                    #     last = optimized_paths[-1]
                    #     last.coords = list(last.coords) + list(geo.coords)
                    # except IndexError:
                    #     optimized_paths.append(geo)

                else:

                    # Have to lift tool. End path.
                    # log.debug("Path #%d not within boundary. Next." % path_count)
                    # optimized_paths.append(geo)
                    optimized_paths.insert(geo)
                    geo = candidate

                current_pt = geo.coords[-1]

                # Next
                # pt, geo = storage.nearest(current_pt)

        except StopIteration:  # Nothing left in storage.
            # pass
            optimized_paths.insert(geo)

        return optimized_paths

    @staticmethod
    def path_connect(storage, origin=(0, 0)):
        """
        Simplifies paths in the FlatCAMRTreeStorage storage by
        connecting paths that touch on their endpoints.

        :param storage:     Storage containing the initial paths.
        :rtype storage:     FlatCAMRTreeStorage
        :param origin:      tuple; point from which to calculate the nearest point
        :return:            Simplified storage.
        :rtype:             FlatCAMRTreeStorage
        """

        log.debug("path_connect()")

        # ## Index first and last points in paths
        def get_pts(o):
            return [o.coords[0], o.coords[-1]]

        #
        # storage = FlatCAMRTreeStorage()
        # storage.get_points = get_pts
        #
        # for shape in pathlist:
        #     if shape is not None:
        #         storage.insert(shape)

        path_count = 0
        pt, geo = storage.nearest(origin)
        storage.remove(geo)
        # optimized_geometry = [geo]
        optimized_geometry = FlatCAMRTreeStorage()
        optimized_geometry.get_points = get_pts
        # optimized_geometry.insert(geo)
        try:
            while True:
                path_count += 1
                _, left = storage.nearest(geo.coords[0])

                # If left touches geo, remove left from original
                # storage and append to geo.
                if type(left) == LineString:
                    if left.coords[0] == geo.coords[0]:
                        storage.remove(left)
                        # geo.coords = list(geo.coords)[::-1] + list(left.coords)   # Shapely 2.0
                        geo = LineString(list(geo.coords)[::-1] + list(left.coords))
                        continue

                    if left.coords[-1] == geo.coords[0]:
                        storage.remove(left)
                        # geo.coords = list(left.coords) + list(geo.coords)  # Shapely 2.0
                        geo = LineString(list(geo.coords)[::-1] + list(left.coords))
                        continue

                    if left.coords[0] == geo.coords[-1]:
                        storage.remove(left)
                        # geo.coords = list(geo.coords) + list(left.coords) # Shapely 2.0
                        geo = LineString(list(geo.coords) + list(left.coords))
                        continue

                    if left.coords[-1] == geo.coords[-1]:
                        storage.remove(left)
                        # geo.coords = list(geo.coords) + list(left.coords)[::-1] # Shapely 2.0
                        geo = LineString(list(geo.coords) + list(left.coords)[::-1])
                        continue

                _, right = storage.nearest(geo.coords[-1])

                # If right touches geo, remove left from original
                # storage and append to geo.
                if type(right) == LineString:
                    if right.coords[0] == geo.coords[-1]:
                        storage.remove(right)
                        # geo.coords = list(geo.coords) + list(right.coords)  # Shapely 2.0
                        geo = LineString(list(geo.coords) + list(right.coords))
                        continue

                    if right.coords[-1] == geo.coords[-1]:
                        storage.remove(right)
                        # geo.coords = list(geo.coords) + list(right.coords)[::-1]    # Shapely 2.0
                        geo = LineString(list(geo.coords) + list(right.coords)[::-1])
                        continue

                    if right.coords[0] == geo.coords[0]:
                        storage.remove(right)
                        # geo.coords = list(geo.coords)[::-1] + list(right.coords)    # Shapely 2.0
                        geo = LineString(list(geo.coords)[::-1] + list(right.coords))
                        continue

                    if right.coords[-1] == geo.coords[0]:
                        storage.remove(right)
                        # geo.coords = list(left.coords) + list(geo.coords)   # Shapely 2.0
                        geo = LineString(list(left.coords) + list(geo.coords))
                        continue

                # right is either a LinearRing or it does not connect
                # to geo (nothing left to connect to geo), so we continue
                # with right as geo.
                storage.remove(right)

                if type(right) == LinearRing:
                    optimized_geometry.insert(right)
                else:
                    # Cannot extend geo any further. Put it away.
                    optimized_geometry.insert(geo)

                    # Continue with right.
                    geo = right

        except StopIteration:  # Nothing found in storage.
            optimized_geometry.insert(geo)

        # print path_count
        log.debug("path_count = %d" % path_count)

        return optimized_geometry

    def convert_units(self, obj_units):
        """
        Converts the units of the object to ``units`` by scaling all
        the geometry appropriately. This call ``scale()``. Don't call
        it again in descendents.

        :param obj_units:   "IN" or "MM"
        :type obj_units:    str
        :return:            Scaling factor resulting from unit change.
        :rtype:             float
        """

        if obj_units.upper() == self.units.upper():
            log.debug("camlib.Geometry.convert_units() --> Factor: 1")
            return 1.0

        if obj_units.upper() == "MM":
            factor = 25.4
            log.debug("camlib.Geometry.convert_units() --> Factor: 25.4")
        elif obj_units.upper() == "IN":
            factor = 1 / 25.4
            log.debug("camlib.Geometry.convert_units() --> Factor: %s" % str(1 / 25.4))
        else:
            log.error("Unsupported units: %s" % str(obj_units))
            log.debug("camlib.Geometry.convert_units() --> Factor: 1")
            return 1.0

        self.units = obj_units
        self.scale(factor, factor)
        self.file_units_factor = factor
        return factor

    def to_dict(self):
        """
        Returns a representation of the object as a dictionary.
        Attributes to include are listed in ``self.ser_attrs``.

        :return:    A dictionary-encoded copy of the object.
        :rtype:     dict
        """
        d = {}
        for attr in self.ser_attrs:
            d[attr] = getattr(self, attr)
        return d

    def from_dict(self, d):
        """
        Sets object's attributes from a dictionary.
        Attributes to include are listed in ``self.ser_attrs``.
        This method will look only for only and all the
        attributes in ``self.ser_attrs``. They must all
        be present. Use only for deserializing saved
        objects.

        :param d:   Dictionary of attributes to set in the object.
        :type d:    dict
        :return:    None
        """
        for attr in self.ser_attrs:
            setattr(self, attr, d[attr])

    def union(self):
        """
        Runs a unary_union on the list of objects in
        solid_geometry.

        :return: None
        """
        self.solid_geometry = [unary_union(self.solid_geometry)]

    def export_svg(self, scale_stroke_factor=0.00,
                   scale_factor_x=None, scale_factor_y=None,
                   skew_factor_x=None, skew_factor_y=None,
                   skew_reference='center', scale_reference='center',
                   mirror=None):
        """
        Exports the Geometry Object as a SVG Element

        :return: SVG Element
        """

        # Make sure we see a Shapely Geometry class and not a list
        if self.kind.lower() == 'geometry':
            flat_geo = []
            if self.multigeo:
                for tool in self.tools:
                    flat_geo += self.flatten(self.tools[tool]['solid_geometry'])
                geom_svg = unary_union(flat_geo)
            else:
                geom_svg = unary_union(self.flatten())
        else:
            geom_svg = unary_union(self.flatten())

        skew_ref = 'center'
        if skew_reference != 'center':
            xmin, ymin, xmax, ymax = geom_svg.bounds
            if skew_reference == 'topleft':
                skew_ref = (xmin, ymax)
            elif skew_reference == 'bottomleft':
                skew_ref = (xmin, ymin)
            elif skew_reference == 'topright':
                skew_ref = (xmax, ymax)
            elif skew_reference == 'bottomright':
                skew_ref = (xmax, ymin)

        geom = geom_svg

        if scale_factor_x and not scale_factor_y:
            geom = affinity.scale(geom_svg, scale_factor_x, 1.0, origin=scale_reference)
        elif not scale_factor_x and scale_factor_y:
            geom = affinity.scale(geom_svg, 1.0, scale_factor_y, origin=scale_reference)
        elif scale_factor_x and scale_factor_y:
            geom = affinity.scale(geom_svg, scale_factor_x, scale_factor_y, origin=scale_reference)

        if skew_factor_x and not skew_factor_y:
            geom = affinity.skew(geom_svg, skew_factor_x, 0.0, origin=skew_ref)
        elif not skew_factor_x and skew_factor_y:
            geom = affinity.skew(geom_svg, 0.0, skew_factor_y, origin=skew_ref)
        elif skew_factor_x and skew_factor_y:
            geom = affinity.skew(geom_svg, skew_factor_x, skew_factor_y, origin=skew_ref)

        if mirror:
            if mirror == 'x':
                geom = affinity.scale(geom_svg, 1.0, -1.0)
            if mirror == 'y':
                geom = affinity.scale(geom_svg, -1.0, 1.0)
            if mirror == 'both':
                geom = affinity.scale(geom_svg, -1.0, -1.0)

        # scale_factor is a multiplication factor for the SVG stroke-width used within shapely's svg export
        # If 0 or less which is invalid then default to 0.01
        # This value appears to work for zooming, and getting the output svg line width
        # to match that viewed on screen with FlatCam
        # MS: I choose a factor of 0.01 so the scale is right for PCB UV film
        if scale_stroke_factor <= 0:
            scale_stroke_factor = 0.01

        # Convert to a SVG
        svg_elem = geom.svg(scale_factor=scale_stroke_factor)
        return svg_elem

    def mirror(self, axis, point):
        """
        Mirrors the object around a specified axis passign through
        the given point.

        :param axis:    "X" or "Y" indicates around which axis to mirror.
        :type axis:     str
        :param point:   [x, y] point belonging to the mirror axis.
        :type point:    list
        :return:        None
        """
        log.debug("camlib.Geometry.mirror()")

        px, py = point
        xscale, yscale = {"X": (1.0, -1.0), "Y": (-1.0, 1.0)}[axis]

        def mirror_geom(obj):
            if type(obj) is list:
                new_obj = []
                for g in obj:
                    new_obj.append(mirror_geom(g))
                return new_obj
            else:
                try:
                    self.el_count += 1
                    disp_number = int(np.interp(self.el_count, [0, self.geo_len], [0, 100]))
                    if self.old_disp_number < disp_number <= 100:
                        self.app.proc_container.update_view_text(' %d%%' % disp_number)
                        self.old_disp_number = disp_number

                    return affinity.scale(obj, xscale, yscale, origin=(px, py))
                except AttributeError:
                    return obj

        try:
            if self.multigeo is True:
                for tool in self.tools:
                    # variables to display the percentage of work done
                    self.geo_len = 0
                    try:
                        self.geo_len = len(self.tools[tool]['solid_geometry'])
                    except TypeError:
                        self.geo_len = 1
                    self.old_disp_number = 0
                    self.el_count = 0

                    self.tools[tool]['solid_geometry'] = mirror_geom(self.tools[tool]['solid_geometry'])
            else:
                # variables to display the percentage of work done
                self.geo_len = 0
                try:
                    self.geo_len = len(self.solid_geometry)
                except TypeError:
                    self.geo_len = 1
                self.old_disp_number = 0
                self.el_count = 0

                self.solid_geometry = mirror_geom(self.solid_geometry)
            self.app.inform.emit('[success] %s...' % _('Object was mirrored'))
        except AttributeError:
            self.app.inform.emit('[ERROR_NOTCL] %s %s' % (_("Failed."), _("No object is selected.")))


        self.app.proc_container.new_text = ''

    def rotate(self, angle, point):
        """
        Rotate an object by an angle (in degrees) around the provided coordinates.

        :param angle:
        The angle of rotation are specified in degrees (default). Positive angles are
        counter-clockwise and negative are clockwise rotations.

        :param point:
        The point of origin can be a keyword 'center' for the bounding box
        center (default), 'centroid' for the geometry's centroid, a Point object
        or a coordinate tuple (x0, y0).

        See shapely manual for more information: http://toblerity.org/shapely/manual.html#affine-transformations
        """
        log.debug("camlib.Geometry.rotate()")

        px, py = point

        def rotate_geom(obj):
            try:
                new_obj = []
                for g in obj:
                    new_obj.append(rotate_geom(g))
                return new_obj
            except TypeError:
                try:
                    self.el_count += 1
                    disp_number = int(np.interp(self.el_count, [0, self.geo_len], [0, 100]))
                    if self.old_disp_number < disp_number <= 100:
                        self.app.proc_container.update_view_text(' %d%%' % disp_number)
                        self.old_disp_number = disp_number

                    return affinity.rotate(obj, angle, origin=(px, py))
                except AttributeError:
                    return obj

        try:
            if self.multigeo is True:
                for tool in self.tools:
                    # variables to display the percentage of work done
                    self.geo_len = 0
                    try:
                        self.geo_len = len(self.tools[tool]['solid_geometry'])
                    except TypeError:
                        self.geo_len = 1
                    self.old_disp_number = 0
                    self.el_count = 0

                    self.tools[tool]['solid_geometry'] = rotate_geom(self.tools[tool]['solid_geometry'])
            else:
                # variables to display the percentage of work done
                self.geo_len = 0
                try:
                    self.geo_len = len(self.solid_geometry)
                except TypeError:
                    self.geo_len = 1
                self.old_disp_number = 0
                self.el_count = 0

                self.solid_geometry = rotate_geom(self.solid_geometry)
            self.app.inform.emit('[success] %s...' % _('Object was rotated'))
        except AttributeError:
            self.app.inform.emit('[ERROR_NOTCL] %s %s' % (_("Failed."), _("No object is selected.")))

        self.app.proc_container.new_text = ''

    def skew(self, angle_x, angle_y, point):
        """
        Shear/Skew the geometries of an object by angles along x and y dimensions.

        :param angle_x:
        :param angle_y:
        angle_x, angle_y : float, float
            The shear angle(s) for the x and y axes respectively. These can be
            specified in either degrees (default) or radians by setting
            use_radians=True.

        :param point:   Origin point for Skew
        point: tuple of coordinates (x,y)

        See shapely manual for more information: http://toblerity.org/shapely/manual.html#affine-transformations
        """
        log.debug("camlib.Geometry.skew()")

        px, py = point

        def skew_geom(obj):
            try:
                new_obj = []
                for g in obj:
                    new_obj.append(skew_geom(g))
                return new_obj
            except TypeError:
                try:
                    self.el_count += 1
                    disp_number = int(np.interp(self.el_count, [0, self.geo_len], [0, 100]))
                    if self.old_disp_number < disp_number <= 100:
                        self.app.proc_container.update_view_text(' %d%%' % disp_number)
                        self.old_disp_number = disp_number

                    return affinity.skew(obj, angle_x, angle_y, origin=(px, py))
                except AttributeError:
                    return obj

        try:
            if self.multigeo is True:
                for tool in self.tools:
                    # variables to display the percentage of work done
                    self.geo_len = 0
                    try:
                        self.geo_len = len(self.tools[tool]['solid_geometry'])
                    except TypeError:
                        self.geo_len = 1
                    self.old_disp_number = 0
                    self.el_count = 0

                    self.tools[tool]['solid_geometry'] = skew_geom(self.tools[tool]['solid_geometry'])
            else:
                # variables to display the percentage of work done
                self.geo_len = 0
                try:
                    self.geo_len = len(self.solid_geometry)
                except TypeError:
                    self.geo_len = 1
                self.old_disp_number = 0
                self.el_count = 0

                self.solid_geometry = skew_geom(self.solid_geometry)
            self.app.inform.emit('[success] %s...' % _('Object was skewed'))
        except AttributeError:
            self.app.inform.emit('[ERROR_NOTCL] %s %s' % (_("Failed."), _("No object is selected.")))

        self.app.proc_container.new_text = ''

        # if type(self.solid_geometry) == list:
        #     self.solid_geometry = [affinity.skew(g, angle_x, angle_y, origin=(px, py))
        #                            for g in self.solid_geometry]
        # else:
        #     self.solid_geometry = affinity.skew(self.solid_geometry, angle_x, angle_y,
        #                                         origin=(px, py))

    def buffer(self, distance, join, factor):
        """

        :param distance:    if 'factor' is True then distance is the factor
        :param join:        The kind of join used by the shapely buffer method: round, square or bevel
        :param factor:      True or False (None)
        :return:
        """

        log.debug("camlib.Geometry.buffer()")

        if distance == 0:
            return

        def buffer_geom(obj):
            if type(obj) is list:
                new_obj = []
                for g in obj:
                    new_obj.append(buffer_geom(g))
                return new_obj
            else:
                try:
                    self.el_count += 1
                    disp_number = int(np.interp(self.el_count, [0, self.geo_len], [0, 100]))
                    if self.old_disp_number < disp_number <= 100:
                        self.app.proc_container.update_view_text(' %d%%' % disp_number)
                        self.old_disp_number = disp_number

                    if factor is None:
                        return obj.buffer(distance, resolution=self.geo_steps_per_circle, join_style=join)
                    else:
                        return affinity.scale(obj, xfact=distance, yfact=distance, origin='center')
                except AttributeError:
                    return obj

        try:
            if self.multigeo is True:
                for tool in self.tools:
                    # variables to display the percentage of work done
                    self.geo_len = 0
                    try:
                        self.geo_len += len(self.tools[tool]['solid_geometry'])
                    except TypeError:
                        self.geo_len += 1
                    self.old_disp_number = 0
                    self.el_count = 0

                    res = buffer_geom(self.tools[tool]['solid_geometry'])
                    try:
                        __ = iter(res)
                        self.tools[tool]['solid_geometry'] = res
                    except TypeError:
                        self.tools[tool]['solid_geometry'] = [res]

            # variables to display the percentage of work done
            self.geo_len = 0
            try:
                self.geo_len = len(self.solid_geometry)
            except TypeError:
                self.geo_len = 1
            self.old_disp_number = 0
            self.el_count = 0

            self.solid_geometry = buffer_geom(self.solid_geometry)

            self.app.inform.emit('[success] %s...' % _('Object was buffered'))
        except AttributeError:
            self.app.inform.emit('[ERROR_NOTCL] %s %s' % (_("Failed."), _("No object is selected.")))

        self.app.proc_container.new_text = ''


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


class CNCjob(Geometry):
    """
    Represents work to be done by a CNC machine.

    *ATTRIBUTES*

    * ``gcode_parsed`` (list): Each is a dictionary:

    =====================  =========================================
    Key                    Value
    =====================  =========================================
    geom                   (Shapely.LineString) Tool path (XY plane)
    kind                   (string) "AB", A is "T" (travel) or
                           "C" (cut). B is "F" (fast) or "S" (slow).
    =====================  =========================================
    """

    defaults = {
        "global_zdownrate": None,
        "pp_geometry_name": 'default',
        "pp_excellon_name": 'default',
        "excellon_optimization_type": "B",
    }

    settings = QtCore.QSettings("Open Source", "FlatCAM")
    if settings.contains("machinist"):
        machinist_setting = settings.value('machinist', type=int)
    else:
        machinist_setting = 0

    def __init__(self,
                 units="in", kind="generic", tooldia=0.0,
                 z_cut=-0.002, z_move=0.1,
                 feedrate=3.0, feedrate_z=3.0, feedrate_rapid=3.0, feedrate_probe=3.0,
                 pp_geometry_name='default', pp_excellon_name='default',
                 depthpercut=0.1, z_pdepth=-0.02,
                 spindlespeed=None, spindledir='CW', dwell=True, dwelltime=1000,
                 toolchangez=0.787402, toolchange_xy='0.0,0.0',
                 endz=2.0, endxy='',
                 segx=None,
                 segy=None,
                 steps_per_circle=None):

        self.decimals = self.app.decimals

        # Used when parsing G-code arcs
        self.steps_per_circle = steps_per_circle if steps_per_circle is not None else \
            int(self.app.defaults['cncjob_steps_per_circle'])

        Geometry.__init__(self, geo_steps_per_circle=self.steps_per_circle)

        self.kind = kind
        self.units = units

        self.z_cut = z_cut
        self.multidepth = False
        self.z_depthpercut = depthpercut
        self.z_move = z_move

        self.feedrate = feedrate
        self.z_feedrate = feedrate_z
        self.feedrate_rapid = feedrate_rapid

        self.tooldia = tooldia
        self.toolC = tooldia
        self.toolchange = False
        self.z_toolchange = toolchangez
        self.xy_toolchange = toolchange_xy
        self.toolchange_xy_type = None

        self.startz = None
        self.z_end = endz
        self.xy_end = endxy

        self.extracut = False
        self.extracut_length = None

        self.tolerance = self.drawing_tolerance

        # used by the self.generate_from_excellon_by_tool() method
        # but set directly before the actual usage of the method with obj.excellon_optimization_type = value
        self.excellon_optimization_type = 'No'

        # if set True then the GCode generation will use UI; used in Excellon GVode for now
        self.use_ui = False

        self.unitcode = {"IN": "G20", "MM": "G21"}

        self.feedminutecode = "G94"
        # self.absolutecode = "G90"
        # self.incrementalcode = "G91"
        self.coordinates_type = self.app.defaults["cncjob_coords_type"]

        self.gcode = ""
        self.gcode_parsed = None

        self.pp_geometry_name = pp_geometry_name
        self.pp_geometry = self.app.preprocessors[self.pp_geometry_name]

        self.pp_excellon_name = pp_excellon_name
        self.pp_excellon = self.app.preprocessors[self.pp_excellon_name]

        self.pp_solderpaste_name = None

        # Controls if the move from Z_Toolchange to Z_Move is done fast with G0 or normally with G1
        self.f_plunge = None

        # Controls if the move from Z_Cutto Z_Move is done fast with G0 or G1 until zero and then G0 to Z_move
        self.f_retract = None

        # how much depth the probe can probe before error
        self.z_pdepth = z_pdepth if z_pdepth else None

        # the feedrate(speed) with which the probel travel while probing
        self.feedrate_probe = feedrate_probe if feedrate_probe else None

        self.spindlespeed = spindlespeed
        self.spindledir = spindledir
        self.dwell = dwell
        self.dwelltime = dwelltime

        self.segx = float(segx) if segx is not None else 0.0
        self.segy = float(segy) if segy is not None else 0.0

        self.input_geometry_bounds = None

        self.oldx = None
        self.oldy = None

        self.tool = 0.0

        self.measured_distance = 0.0
        self.measured_down_distance = 0.0
        self.measured_up_to_zero_distance = 0.0
        self.measured_lift_distance = 0.0

        # here store the travelled distance
        self.travel_distance = 0.0
        # here store the routing time
        self.routing_time = 0.0

        # store here the Excellon source object tools to be accessible locally
        self.exc_tools = None

        # search for toolchange parameters in the Toolchange Custom Code
        self.re_toolchange_custom = re.compile(r'(%[a-zA-Z0-9\-_]+%)')

        # search for toolchange code: M6
        self.re_toolchange = re.compile(r'^\s*(M6)$')

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from Geometry.
        self.ser_attrs += ['kind', 'z_cut', 'z_move', 'z_toolchange', 'feedrate', 'z_feedrate', 'feedrate_rapid',
                           'tooldia', 'gcode', 'input_geometry_bounds', 'gcode_parsed', 'steps_per_circle',
                           'z_depthpercut', 'spindlespeed', 'dwell', 'dwelltime']

    @property
    def postdata(self):
        """
        This will return all the attributes of the class in the form of a dictionary

        :return:    Class attributes
        :rtype:     dict
        """
        return self.__dict__

    def convert_units(self, units):
        """
        Will convert the parameters in the class that are relevant, from metric to imperial and reverse

        :param units:   FlatCAM units
        :type units:    str
        :return:        conversion factor
        :rtype:         float
        """
        log.debug("camlib.CNCJob.convert_units()")

        factor = Geometry.convert_units(self, units)

        self.z_cut = float(self.z_cut) * factor
        self.z_move *= factor
        self.feedrate *= factor
        self.z_feedrate *= factor
        self.feedrate_rapid *= factor
        self.tooldia *= factor
        self.z_toolchange *= factor
        self.z_end *= factor
        self.z_depthpercut = float(self.z_depthpercut) * factor

        return factor

    def doformat(self, fun, **kwargs):
        return self.doformat2(fun, **kwargs) + "\n"

    def doformat2(self, fun, **kwargs):
        """
        This method will call one of the current preprocessor methods having as parameters all the attributes of
        current class to which will add the kwargs parameters

        :param fun:     One of the methods inside the preprocessor classes which get loaded here in the 'p' object
        :type fun:      class 'function'
        :param kwargs:  keyword args which will update attributes of the current class
        :type kwargs:   dict
        :return:        Gcode line
        :rtype:         str
        """
        attributes = AttrDict()
        attributes.update(self.postdata)
        attributes.update(kwargs)
        try:
            returnvalue = fun(attributes)
            return returnvalue
        except Exception:
            self.app.log.error('Exception occurred within a preprocessor: ' + traceback.format_exc())
            return ''

    def parse_custom_toolchange_code(self, data):
        """
        Will parse a text and get a toolchange sequence in text format suitable to be included in a Gcode file.
        The '%' symbol is used to surround class variables name and must be removed in the returned string.
        After that, the class variables (attributes) are replaced with the current values. The result is returned.

        :param data:    Toolchange sequence
        :type data:     str
        :return:        Processed toolchange sequence
        :rtype:         str
        """
        text = data
        match_list = self.re_toolchange_custom.findall(text)

        if match_list:
            for match in match_list:
                command = match.strip('%')
                try:
                    value = getattr(self, command)
                except AttributeError:
                    self.app.inform.emit('[ERROR] %s: %s' %
                                         (_("There is no such parameter"), str(match)))
                    log.debug("CNCJob.parse_custom_toolchange_code() --> AttributeError ")
                    return 'fail'
                text = text.replace(match, str(value))
            return text

    # Distance callback
    class CreateDistanceCallback(object):
        """Create callback to calculate distances between points."""

        def __init__(self, locs, manager):
            self.manager = manager
            self.matrix = {}

            if locs:
                size = len(locs)

                for from_node in range(size):
                    self.matrix[from_node] = {}
                    for to_node in range(size):
                        if from_node == to_node:
                            self.matrix[from_node][to_node] = 0
                        else:
                            x1 = locs[from_node][0]
                            y1 = locs[from_node][1]
                            x2 = locs[to_node][0]
                            y2 = locs[to_node][1]
                            self.matrix[from_node][to_node] = distance_euclidian(x1, y1, x2, y2)

        # def Distance(self, from_node, to_node):
        #     return int(self.matrix[from_node][to_node])
        def Distance(self, from_index, to_index):
            # Convert from routing variable Index to distance matrix NodeIndex.
            from_node = self.manager.IndexToNode(from_index)
            to_node = self.manager.IndexToNode(to_index)
            return self.matrix[from_node][to_node]

    @staticmethod
    def create_tool_data_array(points):
        # Create the data.
        return [(pt.coords.xy[0][0], pt.coords.xy[1][0]) for pt in points]

    def optimized_ortools_meta(self, locations, start=None, opt_time=0):
        optimized_path = []

        tsp_size = len(locations)
        num_routes = 1  # The number of routes, which is 1 in the TSP.
        # Nodes are indexed from 0 to tsp_size - 1. The depot is the starting node of the route.

        depot = 0 if start is None else start

        # Create routing model.
        if tsp_size == 0:
            log.warning('OR-tools metaheuristics - Specify an instance greater than 0.')
            return optimized_path

        manager = pywrapcp.RoutingIndexManager(tsp_size, num_routes, depot)
        routing = pywrapcp.RoutingModel(manager)
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)

        # Set search time limit in milliseconds.
        if float(opt_time) != 0:
            search_parameters.time_limit.seconds = int(
                float(opt_time))
        else:
            search_parameters.time_limit.seconds = 3

        # Callback to the distance function. The callback takes two
        # arguments (the from and to node indices) and returns the distance between them.
        dist_between_locations = self.CreateDistanceCallback(locs=locations, manager=manager)

        # if there are no distances then go to the next tool
        if not dist_between_locations:
            return

        dist_callback = dist_between_locations.Distance
        transit_callback_index = routing.RegisterTransitCallback(dist_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # Solve, returns a solution if any.
        assignment = routing.SolveWithParameters(search_parameters)

        if assignment:
            # Solution cost.
            log.info("OR-tools metaheuristics - Total distance: " + str(assignment.ObjectiveValue()))

            # Inspect solution.
            # Only one route here; otherwise iterate from 0 to routing.vehicles() - 1.
            route_number = 0
            node = routing.Start(route_number)
            start_node = node

            while not routing.IsEnd(node):
                if self.app.abort_flag:
                    # graceful abort requested by the user
                    raise grace

                optimized_path.append(node)
                node = assignment.Value(routing.NextVar(node))
        else:
            log.warning('OR-tools metaheuristics - No solution found.')

        return optimized_path
        # ############################################# ##

    def optimized_ortools_basic(self, locations, start=None):
        optimized_path = []

        tsp_size = len(locations)
        num_routes = 1  # The number of routes, which is 1 in the TSP.

        # Nodes are indexed from 0 to tsp_size - 1. The depot is the starting node of the route.
        depot = 0 if start is None else start

        # Create routing model.
        if tsp_size == 0:
            log.warning('Specify an instance greater than 0.')
            return optimized_path

        manager = pywrapcp.RoutingIndexManager(tsp_size, num_routes, depot)
        routing = pywrapcp.RoutingModel(manager)
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()

        # Callback to the distance function. The callback takes two
        # arguments (the from and to node indices) and returns the distance between them.
        dist_between_locations = self.CreateDistanceCallback(locs=locations, manager=manager)

        # if there are no distances then go to the next tool
        if not dist_between_locations:
            return

        dist_callback = dist_between_locations.Distance
        transit_callback_index = routing.RegisterTransitCallback(dist_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # Solve, returns a solution if any.
        assignment = routing.SolveWithParameters(search_parameters)

        if assignment:
            # Solution cost.
            log.info("Total distance: " + str(assignment.ObjectiveValue()))

            # Inspect solution.
            # Only one route here; otherwise iterate from 0 to routing.vehicles() - 1.
            route_number = 0
            node = routing.Start(route_number)
            start_node = node

            while not routing.IsEnd(node):
                optimized_path.append(node)
                node = assignment.Value(routing.NextVar(node))
        else:
            log.warning('No solution found.')

        return optimized_path
        # ############################################# ##

    def optimized_travelling_salesman(self, points, start=None):
        """
        As solving the problem in the brute force way is too slow,
        this function implements a simple heuristic: always
        go to the nearest city.

        Even if this algorithm is extremely simple, it works pretty well
        giving a solution only about 25%% longer than the optimal one (cit. Wikipedia),
        and runs very fast in O(N^2) time complexity.

        >>> optimized_travelling_salesman([[i,j] for i in range(5) for j in range(5)])
        [[0, 0], [0, 1], [0, 2], [0, 3], [0, 4], [1, 4], [1, 3], [1, 2], [1, 1], [1, 0], [2, 0], [2, 1], [2, 2],
        [2, 3], [2, 4], [3, 4], [3, 3], [3, 2], [3, 1], [3, 0], [4, 0], [4, 1], [4, 2], [4, 3], [4, 4]]
        >>> optimized_travelling_salesman([[0,0],[10,0],[6,0]])
        [[0, 0], [6, 0], [10, 0]]

        :param points:  List of tuples with x, y coordinates
        :type points:   list
        :param start:   a tuple with a x,y coordinates of the start point
        :type start:    tuple
        :return:        List of points ordered in a optimized way
        :rtype:         list
        """

        if start is None:
            start = points[0]
        must_visit = points
        path = [start]
        # must_visit.remove(start)
        while must_visit:
            nearest = min(must_visit, key=lambda x: distance(path[-1], x))
            path.append(nearest)
            must_visit.remove(nearest)
        return path

    def geo_optimized_rtree(self, geometry):
        locations = []

        # ## Index first and last points in paths. What points to index.
        def get_pts(o):
            return [o.coords[0], o.coords[-1]]

        # Create the indexed storage.
        storage = FlatCAMRTreeStorage()
        storage.get_points = get_pts

        # Store the geometry
        log.debug("Indexing geometry before generating G-Code...")
        self.app.inform.emit(_("Indexing geometry before generating G-Code..."))

        for geo_shape in geometry:
            if self.app.abort_flag:
                # graceful abort requested by the user
                raise grace

            if geo_shape is not None:
                storage.insert(geo_shape)

        current_pt = (0, 0)
        pt, geo = storage.nearest(current_pt)
        try:
            while True:
                storage.remove(geo)
                locations.append((pt, geo))
                current_pt = geo.coords[-1]
                pt, geo = storage.nearest(current_pt)
        except StopIteration:
            pass

        # if there are no locations then go to the next tool
        if not locations:
            return 'fail'

        return locations

    def check_zcut(self, zcut):
        if zcut > 0:
            self.app.inform.emit('[WARNING] %s' %
                                 _("The Cut Z parameter has positive value. "
                                   "It is the depth value to drill into material.\n"
                                   "The Cut Z parameter needs to have a negative value, assuming it is a typo "
                                   "therefore the app will convert the value to negative. "
                                   "Check the resulting CNC code (Gcode etc)."))
            return -zcut
        elif zcut == 0:
            self.app.inform.emit('[WARNING] %s.' % _("The Cut Z parameter is zero. There will be no cut, aborting"))
            return 'fail'

    # used in Tool Drilling
    def excellon_tool_gcode_gen(self, tool, points, tools, first_pt, is_first=False, is_last=False, opt_type='T',
                                toolchange=False):
        """
        Creates Gcode for this object from an Excellon object
        for the specified tools.



        :return:            A tuple made from tool_gcode,  another tuple holding the coordinates of the last point
                            and the start gcode
        :rtype:             tuple
        """
        log.debug("Creating CNC Job from Excellon for tool: %s" % str(tool))

        self.exc_tools = deepcopy(tools)
        t_gcode = ''

        # holds the temporary coordinates of the processed drill point
        locx, locy = first_pt
        temp_locx, temp_locy = first_pt

        # #############################################################################################################
        # #############################################################################################################
        # ##################################   DRILLING !!!   #########################################################
        # #############################################################################################################
        # #############################################################################################################
        if opt_type == 'M':
            log.debug("Using OR-Tools Metaheuristic Guided Local Search drill path optimization.")
        elif opt_type == 'B':
            log.debug("Using OR-Tools Basic drill path optimization.")
        elif opt_type == 'T':
            log.debug("Using Travelling Salesman drill path optimization.")
        else:
            log.debug("Using no path optimization.")

        tool_dict = tools[tool]['data']
        # check if it has drills
        if not points:
            log.debug("Failed. No drills for tool: %s" % str(tool))
            return 'fail'

        if self.app.abort_flag:
            # graceful abort requested by the user
            raise grace

        # #########################################################################################################
        # #########################################################################################################
        # ############# PARAMETERS used in PREPROCESSORS so they need to be updated ###############################
        # #########################################################################################################
        # #########################################################################################################
        self.tool = str(tool)
        # Preprocessor
        p = self.pp_excellon

        # Z_cut parameter
        if self.machinist_setting == 0:
            self.z_cut = self.check_zcut(zcut=tool_dict["tools_drill_cutz"])
            if self.z_cut == 'fail':
                return 'fail'

        # Depth parameters
        self.z_cut = tool_dict['tools_drill_cutz']
        old_zcut = deepcopy(tool_dict["tools_drill_cutz"])      # multidepth use this
        self.multidepth = tool_dict['tools_drill_multidepth']
        self.z_depthpercut = tool_dict['tools_drill_depthperpass']
        self.z_move = tool_dict['tools_drill_travelz']
        self.f_plunge = tool_dict["tools_drill_f_plunge"]       # used directly in the preprocessor Toolchange method
        self.f_retract = tool_dict["tools_drill_f_retract"]     # used in the current method

        # Feedrate parameters
        self.z_feedrate = tool_dict['tools_drill_feedrate_z']
        self.feedrate = tool_dict['tools_drill_feedrate_z']
        self.feedrate_rapid = tool_dict['tools_drill_feedrate_rapid']

        # Spindle parameters
        self.spindlespeed = tool_dict['tools_drill_spindlespeed']
        self.dwell = tool_dict['tools_drill_dwell']
        self.dwelltime = tool_dict['tools_drill_dwelltime']
        self.spindledir = tool_dict['tools_drill_spindledir']

        self.tooldia = tools[tool]["tooldia"]
        self.postdata['toolC'] = tools[tool]["tooldia"]
        self.toolchange = toolchange

        # Z_toolchange parameter
        self.z_toolchange = tool_dict['tools_drill_toolchangez']
        # XY_toolchange parameter
        self.xy_toolchange = tool_dict["tools_drill_toolchangexy"]
        try:
            if self.xy_toolchange == '':
                self.xy_toolchange = None
            else:
                # either originally it was a string or not, xy_toolchange will be made string
                self.xy_toolchange = re.sub('[()\[\]]', '', str(self.xy_toolchange)) if self.xy_toolchange else None

                # and now, xy_toolchange is made into a list of floats in format [x, y]
                if self.xy_toolchange:
                    self.xy_toolchange = [float(eval(a)) for a in self.xy_toolchange.split(",")]

                if self.xy_toolchange and len(self.xy_toolchange) != 2:
                    self.app.inform.emit('[ERROR] %s' % _("The Toolchange X,Y format has to be (x, y)."))
                    return 'fail'
        except Exception as e:
            log.debug("camlib.CNCJob.generate_from_excellon_by_tool() xy_toolchange --> %s" % str(e))
            self.xy_toolchange = [0, 0]

        # End position parameters
        self.startz = tool_dict["tools_drill_startz"]
        if self.startz == '':
            self.startz = None
        self.z_end = tool_dict["tools_drill_endz"]
        self.xy_end = tool_dict["tools_drill_endxy"]

        try:
            if self.xy_end == '':
                self.xy_end = None
            else:
                # either originally it was a string or not, xy_end will be made string
                self.xy_end = re.sub('[()\[\]]', '', str(self.xy_end)) if self.xy_end else None

                # and now, xy_end is made into a list of floats in format [x, y]
                if self.xy_end:
                    self.xy_end = [float(eval(a)) for a in self.xy_end.split(",")]

                if self.xy_end and len(self.xy_end) != 2:
                    self.app.inform.emit('[ERROR] %s' % _("The End X,Y format has to be (x, y)."))
                    return 'fail'
        except Exception as e:
            log.debug("camlib.CNCJob.generate_from_excellon_by_tool() xy_end --> %s" % str(e))
            self.xy_end = [0, 0]

        # Probe parameters
        self.z_pdepth = tool_dict["tools_drill_z_pdepth"]
        self.feedrate_probe = tool_dict["tools_drill_feedrate_probe"]
        # #########################################################################################################
        # #########################################################################################################

        # #########################################################################################################
        # ############ Create the data. ###########################################################################
        # #########################################################################################################
        locations = []
        optimized_path = []

        if opt_type == 'M':
            locations = self.create_tool_data_array(points=points)
            # if there are no locations then go to the next tool
            if not locations:
                return 'fail'
            opt_time = self.app.defaults["excellon_search_time"]
            optimized_path = self.optimized_ortools_meta(locations=locations, opt_time=opt_time)
        elif opt_type == 'B':
            locations = self.create_tool_data_array(points=points)
            # if there are no locations then go to the next tool
            if not locations:
                return 'fail'
            optimized_path = self.optimized_ortools_basic(locations=locations)
        elif opt_type == 'T':
            locations = self.create_tool_data_array(points=points)
            # if there are no locations then go to the next tool
            if not locations:
                return 'fail'
            optimized_path = self.optimized_travelling_salesman(locations)
        else:
            # it's actually not optimized path but here we build a list of (x,y) coordinates
            # out of the tool's drills
            for drill in tools[tool]['drills']:
                unoptimized_coords = (
                    drill.x,
                    drill.y
                )
                optimized_path.append(unoptimized_coords)
        # #########################################################################################################
        # #########################################################################################################

        # Only if there are locations to drill
        if not optimized_path:
            log.debug("CNCJob.excellon_tool_gcode_gen() -> Optimized path is empty.")
            return 'fail'

        if self.app.abort_flag:
            # graceful abort requested by the user
            raise grace

        start_gcode = ''
        if is_first:
            start_gcode = self.doformat(p.start_code)
            # t_gcode += start_gcode

        # do the ToolChange event
        t_gcode += self.doformat(p.z_feedrate_code)
        t_gcode += self.doformat(p.toolchange_code, toolchangexy=(temp_locx, temp_locy))
        t_gcode += self.doformat(p.z_feedrate_code)

        # Spindle start
        t_gcode += self.doformat(p.spindle_code)
        # Dwell time
        if self.dwell is True:
            t_gcode += self.doformat(p.dwell_code)

        current_tooldia = self.app.dec_format(float(tools[tool]["tooldia"]), self.decimals)
        self.app.inform.emit(
            '%s: %s%s.' % (_("Starting G-Code for tool with diameter"), str(current_tooldia), str(self.units))
        )

        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # APPLY Offset only when using the appGUI, for TclCommand this will create an error
        # because the values for Z offset are created in build_tool_ui()
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        try:
            z_offset = float(tool_dict['tools_drill_offset']) * (-1)
        except KeyError:
            z_offset = 0
        self.z_cut = z_offset + old_zcut

        self.coordinates_type = self.app.defaults["cncjob_coords_type"]
        if self.coordinates_type == "G90":
            # Drillling! for Absolute coordinates type G90
            # variables to display the percentage of work done
            geo_len = len(optimized_path)

            old_disp_number = 0
            log.warning("Number of drills for which to generate GCode: %s" % str(geo_len))

            loc_nr = 0
            for point in optimized_path:
                if self.app.abort_flag:
                    # graceful abort requested by the user
                    raise grace

                # if we use Traveling Salesman Algorithm as an optimization
                if opt_type == 'T':
                    locx = point[0]
                    locy = point[1]
                else:
                    locx = locations[point][0]
                    locy = locations[point][1]

                travels = self.app.exc_areas.travel_coordinates(start_point=(temp_locx, temp_locy),
                                                                end_point=(locx, locy),
                                                                tooldia=current_tooldia)
                prev_z = None
                for travel in travels:
                    locx = travel[1][0]
                    locy = travel[1][1]

                    if travel[0] is not None:
                        # move to next point
                        t_gcode += self.doformat(p.rapid_code, x=locx, y=locy)

                        # raise to safe Z (travel[0]) each time because safe Z may be different
                        self.z_move = travel[0]
                        t_gcode += self.doformat(p.lift_code, x=locx, y=locy)

                        # restore z_move
                        self.z_move = tool_dict['tools_drill_travelz']
                    else:
                        if prev_z is not None:
                            # move to next point
                            t_gcode += self.doformat(p.rapid_code, x=locx, y=locy)

                            # we assume that previously the z_move was altered therefore raise to
                            # the travel_z (z_move)
                            self.z_move = tool_dict['tools_drill_travelz']
                            t_gcode += self.doformat(p.lift_code, x=locx, y=locy)
                        else:
                            # move to next point
                            t_gcode += self.doformat(p.rapid_code, x=locx, y=locy)

                    # store prev_z
                    prev_z = travel[0]

                # t_gcode += self.doformat(p.rapid_code, x=locx, y=locy)

                if self.multidepth and abs(self.z_cut) > abs(self.z_depthpercut):
                    doc = deepcopy(self.z_cut)
                    self.z_cut = 0.0

                    while abs(self.z_cut) < abs(doc):

                        self.z_cut -= self.z_depthpercut
                        if abs(doc) < abs(self.z_cut) < (abs(doc) + self.z_depthpercut):
                            self.z_cut = doc
                        # Move down the drill bit
                        t_gcode += self.doformat(p.down_code, x=locx, y=locy)

                        # Update the distance travelled down with the current one
                        self.measured_down_distance += abs(self.z_cut) + abs(self.z_move)

                        if self.f_retract is False:
                            t_gcode += self.doformat(p.up_to_zero_code, x=locx, y=locy)
                            self.measured_up_to_zero_distance += abs(self.z_cut)
                            self.measured_lift_distance += abs(self.z_move)
                        else:
                            self.measured_lift_distance += abs(self.z_cut) + abs(self.z_move)

                        t_gcode += self.doformat(p.lift_code, x=locx, y=locy)

                else:
                    t_gcode += self.doformat(p.down_code, x=locx, y=locy)

                    self.measured_down_distance += abs(self.z_cut) + abs(self.z_move)

                    if self.f_retract is False:
                        t_gcode += self.doformat(p.up_to_zero_code, x=locx, y=locy)
                        self.measured_up_to_zero_distance += abs(self.z_cut)
                        self.measured_lift_distance += abs(self.z_move)
                    else:
                        self.measured_lift_distance += abs(self.z_cut) + abs(self.z_move)

                    t_gcode += self.doformat(p.lift_code, x=locx, y=locy)

                self.measured_distance += abs(distance_euclidian(locx, locy, temp_locx, temp_locy))
                temp_locx = locx
                temp_locy = locy
                self.oldx = locx
                self.oldy = locy

                loc_nr += 1
                disp_number = int(np.interp(loc_nr, [0, geo_len], [0, 100]))

                if old_disp_number < disp_number <= 100:
                    self.app.proc_container.update_view_text(' %d%%' % disp_number)
                    old_disp_number = disp_number

        else:
            self.app.inform.emit('[ERROR_NOTCL] %s...' % _('G91 coordinates not implemented'))
            return 'fail'
        self.z_cut = deepcopy(old_zcut)

        if is_last:
            t_gcode += self.doformat(p.spindle_stop_code)
            # Move to End position
            t_gcode += self.doformat(p.end_code, x=0, y=0)

        self.app.inform.emit('%s %s' % (_("Finished G-Code generation for tool:"), str(tool)))
        return t_gcode, (locx, locy), start_gcode

    # used in Geometry (and soon in Tool Milling)
    def geometry_tool_gcode_gen(self, tool, tools, first_pt, tolerance, is_first=False, is_last=False,
                                toolchange=False):
        """
        Algorithm to generate GCode from multitool Geometry.

        :param tool:        tool number for which to generate GCode
        :type tool:         int
        :param tools:       a dictionary holding all the tools and data
        :type tools:        dict
        :param first_pt:    a tuple of coordinates for the first point of the current tool
        :type first_pt:     tuple
        :param tolerance:   geometry tolerance
        :type tolerance:
        :param is_first:    if the current tool is the first tool (for this we need to add start GCode)
        :type is_first:     bool
        :param is_last:     if the current tool is the last tool (for this we need to add the end GCode)
        :type is_last:      bool
        :param toolchange:  add toolchange event
        :type toolchange:   bool
        :return:            GCode
        :rtype:             str
        """

        log.debug("geometry_tool_gcode_gen()")

        t_gcode = ''
        temp_solid_geometry = []

        # The Geometry from which we create GCode
        geometry = tools[tool]['solid_geometry']
        # ## Flatten the geometry. Only linear elements (no polygons) remain.
        flat_geometry = self.flatten(geometry, reset=True, pathonly=True)
        log.debug("%d paths" % len(flat_geometry))

        # #########################################################################################################
        # #########################################################################################################
        # ############# PARAMETERS used in PREPROCESSORS so they need to be updated ###############################
        # #########################################################################################################
        # #########################################################################################################
        self.tool = str(tool)
        tool_dict = tools[tool]['data']
        # this is the tool diameter, it is used as such to accommodate the preprocessor who need the tool diameter
        # given under the name 'toolC'
        self.postdata['toolC'] = float(tools[tool]['tooldia'])
        self.tooldia = float(tools[tool]['tooldia'])
        self.use_ui = True
        self.tolerance = tolerance

        # Optimization type. Can be: 'M', 'B', 'T', 'R', 'No'
        opt_type = tool_dict['optimization_type']
        opt_time = tool_dict['search_time'] if 'search_time' in tool_dict else 'R'

        if opt_type == 'M':
            log.debug("Using OR-Tools Metaheuristic Guided Local Search path optimization.")
        elif opt_type == 'B':
            log.debug("Using OR-Tools Basic path optimization.")
        elif opt_type == 'T':
            log.debug("Using Travelling Salesman path optimization.")
        elif opt_type == 'R':
            log.debug("Using RTree path optimization.")
        else:
            log.debug("Using no path optimization.")

        # Preprocessor
        self.pp_geometry_name = tool_dict['ppname_g']
        self.pp_geometry = self.app.preprocessors[self.pp_geometry_name]
        p = self.pp_geometry

        # Offset the Geometry if it is the case
        if tools[tool]['offset'].lower() == 'in':
            tool_offset = -float(tools[tool]['tooldia']) / 2.0
        elif tools[tool]['offset'].lower() == 'out':
            tool_offset = float(tools[tool]['tooldia']) / 2.0
        elif tools[tool]['offset'].lower() == 'custom':
            tool_offset = tools[tool]['offset_value']
        else:
            tool_offset = 0.0

        if tool_offset != 0.0:
            for it in flat_geometry:
                # if the geometry is a closed shape then create a Polygon out of it
                if isinstance(it, LineString):
                    if it.is_ring:
                        it = Polygon(it)
                temp_solid_geometry.append(it.buffer(tool_offset, join_style=2))
            temp_solid_geometry = self.flatten(temp_solid_geometry, reset=True, pathonly=True)
        else:
            temp_solid_geometry = flat_geometry

        if self.z_cut is None:
            if 'laser' not in self.pp_geometry_name:
                self.app.inform.emit(
                    '[ERROR_NOTCL] %s' % _("Cut_Z parameter is None or zero. Most likely a bad combinations of "
                                           "other parameters."))
                return 'fail'
            else:
                self.z_cut = 0
        if self.machinist_setting == 0:
            if self.z_cut > 0:
                self.app.inform.emit('[WARNING] %s' %
                                     _("The Cut Z parameter has positive value. "
                                       "It is the depth value to cut into material.\n"
                                       "The Cut Z parameter needs to have a negative value, assuming it is a typo "
                                       "therefore the app will convert the value to negative."
                                       "Check the resulting CNC code (Gcode etc)."))
                self.z_cut = -self.z_cut
            elif self.z_cut == 0 and 'laser' not in self.pp_geometry_name:
                self.app.inform.emit('[WARNING] %s: %s' %
                                     (_("The Cut Z parameter is zero. There will be no cut, skipping file"),
                                      self.options['name']))
                return 'fail'

            if self.z_move is None:
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("Travel Z parameter is None or zero."))
                return 'fail'

            if self.z_move < 0:
                self.app.inform.emit('[WARNING] %s' %
                                     _("The Travel Z parameter has negative value. "
                                       "It is the height value to travel between cuts.\n"
                                       "The Z Travel parameter needs to have a positive value, assuming it is a typo "
                                       "therefore the app will convert the value to positive."
                                       "Check the resulting CNC code (Gcode etc)."))
                self.z_move = -self.z_move
            elif self.z_move == 0:
                self.app.inform.emit('[WARNING] %s: %s' %
                                     (_("The Z Travel parameter is zero. This is dangerous, skipping file"),
                                      self.options['name']))
                return 'fail'

        # made sure that depth_per_cut is no more then the z_cut
        if abs(self.z_cut) < self.z_depthpercut:
            self.z_depthpercut = abs(self.z_cut)

        # Depth parameters
        self.z_cut = float(tool_dict['cutz'])
        self.multidepth = tool_dict['multidepth']
        self.z_depthpercut = float(tool_dict['depthperpass'])
        self.z_move = float(tool_dict['travelz'])
        self.f_plunge = self.app.defaults["geometry_f_plunge"]

        self.feedrate = float(tool_dict['feedrate'])
        self.z_feedrate = float(tool_dict['feedrate_z'])
        self.feedrate_rapid = float(tool_dict['feedrate_rapid'])

        self.spindlespeed = float(tool_dict['spindlespeed'])
        try:
            self.spindledir = tool_dict['spindledir']
        except KeyError:
            self.spindledir = self.app.defaults["geometry_spindledir"]

        self.dwell = tool_dict['dwell']
        self.dwelltime = float(tool_dict['dwelltime'])

        self.startz = float(tool_dict['startz']) if tool_dict['startz'] else None
        if self.startz == '':
            self.startz = None

        self.z_end = float(tool_dict['endz'])
        self.xy_end = tool_dict['endxy']
        try:
            if self.xy_end == '' or self.xy_end is None:
                self.xy_end = None
            else:
                # either originally it was a string or not, xy_end will be made string
                self.xy_end = re.sub('[()\[\]]', '', str(self.xy_end)) if self.xy_end else None

                # and now, xy_end is made into a list of floats in format [x, y]
                if self.xy_end:
                    self.xy_end = [float(eval(a)) for a in self.xy_end.split(",")]

                if self.xy_end and len(self.xy_end) != 2:
                    self.app.inform.emit('[ERROR]%s' % _("The End X,Y format has to be (x, y)."))
                    return 'fail'
        except Exception as e:
            log.debug("camlib.CNCJob.geometry_from_excellon_by_tool() xy_end --> %s" % str(e))
            self.xy_end = [0, 0]

        self.z_toolchange = tool_dict['toolchangez']
        self.xy_toolchange = tool_dict["toolchangexy"]
        try:
            if self.xy_toolchange == '':
                self.xy_toolchange = None
            else:
                # either originally it was a string or not, xy_toolchange will be made string
                self.xy_toolchange = re.sub('[()\[\]]', '', str(self.xy_toolchange)) if self.xy_toolchange else None

                # and now, xy_toolchange is made into a list of floats in format [x, y]
                if self.xy_toolchange:
                    self.xy_toolchange = [float(eval(a)) for a in self.xy_toolchange.split(",")]

                if self.xy_toolchange and len(self.xy_toolchange) != 2:
                    self.app.inform.emit('[ERROR] %s' % _("The Toolchange X,Y format has to be (x, y)."))
                    return 'fail'
        except Exception as e:
            log.debug("camlib.CNCJob.geometry_from_excellon_by_tool() --> %s" % str(e))
            pass

        self.extracut = tool_dict['extracut']
        self.extracut_length = tool_dict['extracut_length']

        # Probe parameters
        # self.z_pdepth = tool_dict["tools_drill_z_pdepth"]
        # self.feedrate_probe = tool_dict["tools_drill_feedrate_probe"]

        # #########################################################################################################
        # ############ Create the data. ###########################################################################
        # #########################################################################################################
        optimized_path = []

        geo_storage = {}
        for geo in temp_solid_geometry:
            if not geo is None:
                geo_storage[geo.coords[0]] = geo
        locations = list(geo_storage.keys())

        if opt_type == 'M':
            # if there are no locations then go to the next tool
            if not locations:
                return 'fail'
            optimized_locations = self.optimized_ortools_meta(locations=locations, opt_time=opt_time)
            optimized_path = [(locations[loc], geo_storage[locations[loc]]) for loc in optimized_locations]
        elif opt_type == 'B':
            # if there are no locations then go to the next tool
            if not locations:
                return 'fail'
            optimized_locations = self.optimized_ortools_basic(locations=locations)
            optimized_path = [(locations[loc], geo_storage[locations[loc]]) for loc in optimized_locations]
        elif opt_type == 'T':
            # if there are no locations then go to the next tool
            if not locations:
                return 'fail'
            optimized_locations = self.optimized_travelling_salesman(locations)
            optimized_path = [(loc, geo_storage[loc]) for loc in optimized_locations]
        elif opt_type == 'R':
            optimized_path = self.geo_optimized_rtree(temp_solid_geometry)
            if optimized_path == 'fail':
                return 'fail'
        else:
            # it's actually not optimized path but here we build a list of (x,y) coordinates
            # out of the tool's drills
            for geo in temp_solid_geometry:
                optimized_path.append(geo.coords[0])
        # #########################################################################################################
        # #########################################################################################################

        # Only if there are locations to mill
        if not optimized_path:
            log.debug("camlib.CNCJob.geometry_tool_gcode_gen() -> Optimized path is empty.")
            return 'fail'

        if self.app.abort_flag:
            # graceful abort requested by the user
            raise grace

        # #############################################################################################################
        # #############################################################################################################
        # ################# MILLING !!! ##############################################################################
        # #############################################################################################################
        # #############################################################################################################
        log.debug("Starting G-Code...")

        current_tooldia = float('%.*f' % (self.decimals, float(self.tooldia)))
        self.app.inform.emit('%s: %s%s.' % (_("Starting G-Code for tool with diameter"),
                                            str(current_tooldia),
                                            str(self.units)))

        # Measurements
        total_travel = 0.0
        total_cut = 0.0

        # Start GCode
        start_gcode = ''
        if is_first:
            start_gcode = self.doformat(p.start_code)
            # t_gcode += start_gcode

        # Toolchange code
        t_gcode += self.doformat(p.feedrate_code)  # sets the feed rate
        if toolchange:
            t_gcode += self.doformat(p.toolchange_code)

            if 'laser' not in self.pp_geometry_name.lower():
                t_gcode += self.doformat(p.spindle_code)  # Spindle start
            else:
                # for laser this will disable the laser
                t_gcode += self.doformat(p.lift_code, x=self.oldx, y=self.oldy)  # Move (up) to travel height

            if self.dwell:
                t_gcode += self.doformat(p.dwell_code)  # Dwell time
        else:
            t_gcode += self.doformat(p.lift_code, x=0, y=0)  # Move (up) to travel height
            t_gcode += self.doformat(p.startz_code, x=0, y=0)

            if 'laser' not in self.pp_geometry_name.lower():
                t_gcode += self.doformat(p.spindle_code)  # Spindle start

            if self.dwell is True:
                t_gcode += self.doformat(p.dwell_code)  # Dwell time
        t_gcode += self.doformat(p.feedrate_code)  # sets the feed rate

        # ## Iterate over geometry paths getting the nearest each time.
        path_count = 0

        # variables to display the percentage of work done
        geo_len = len(flat_geometry)
        log.warning("Number of paths for which to generate GCode: %s" % str(geo_len))
        old_disp_number = 0

        current_pt = (0, 0)
        for pt, geo in optimized_path:
            if self.app.abort_flag:
                # graceful abort requested by the user
                raise grace

            path_count += 1

            # If last point in geometry is the nearest but prefer the first one if last point == first point
            # then reverse coordinates.
            if pt != geo.coords[0] and pt == geo.coords[-1]:
                geo = LineString(list(geo.coords)[::-1])

            # ---------- Single depth/pass --------
            if not self.multidepth:
                # calculate the cut distance
                total_cut = total_cut + geo.length

                t_gcode += self.create_gcode_single_pass(geo, current_tooldia, self.extracut,
                                                         self.extracut_length, self.tolerance,
                                                         z_move=self.z_move, old_point=current_pt)

            # --------- Multi-pass ---------
            else:
                # calculate the cut distance
                # due of the number of cuts (multi depth) it has to multiplied by the number of cuts
                nr_cuts = 0
                depth = abs(self.z_cut)
                while depth > 0:
                    nr_cuts += 1
                    depth -= float(self.z_depthpercut)

                total_cut += (geo.length * nr_cuts)

                gc, geo = self.create_gcode_multi_pass(geo, current_tooldia, self.extracut,
                                                       self.extracut_length, self.tolerance,
                                                       z_move=self.z_move, postproc=p, old_point=current_pt)
                t_gcode += gc

            # calculate the total distance
            total_travel = total_travel + abs(distance(pt1=current_pt, pt2=pt))
            current_pt = geo.coords[-1]

            disp_number = int(np.interp(path_count, [0, geo_len], [0, 100]))
            if old_disp_number < disp_number <= 100:
                self.app.proc_container.update_view_text(' %d%%' % disp_number)
                old_disp_number = disp_number

        log.debug("Finished G-Code... %s paths traced." % path_count)

        # add move to end position
        total_travel += abs(distance_euclidian(current_pt[0], current_pt[1], 0, 0))
        self.travel_distance += total_travel + total_cut
        self.routing_time += total_cut / self.feedrate

        # Finish
        if is_last:
            t_gcode += self.doformat(p.spindle_stop_code)
            t_gcode += self.doformat(p.lift_code, x=current_pt[0], y=current_pt[1])
            t_gcode += self.doformat(p.end_code, x=0, y=0)
            self.app.inform.emit(
                '%s... %s %s.' % (_("Finished G-Code generation"), str(path_count), _("paths traced"))
            )

        self.gcode = t_gcode
        return self.gcode, start_gcode

    # used by the Tcl command Drillcncjob
    def generate_from_excellon_by_tool(self, exobj, tools="all", order='fwd', is_first=False, use_ui=False):
        """
        Creates Gcode for this object from an Excellon object
        for the specified tools.

        :param exobj:       Excellon object to process
        :type exobj:        Excellon
        :param tools:       Comma separated tool names
        :type tools:        str
        :param order:       order of tools processing: "fwd", "rev" or "no"
        :type order:        str
        :param is_first:    if the tool is the first one should generate the start gcode (not that it matter much
                            which is the one doing it)
        :type is_first:     bool
        :param use_ui:      if True the method will use parameters set in UI
        :type use_ui:       bool
        :return:            None
        :rtype:             None
        """

        # #############################################################################################################
        # #############################################################################################################
        # create a local copy of the exobj.tools so it can be used for creating drill CCode geometry
        # #############################################################################################################
        # #############################################################################################################
        self.exc_tools = deepcopy(exobj.tools)

        # the Excellon GCode preprocessor will use this info in the start_code() method
        self.use_ui = True if use_ui else False

        # Z_cut parameter
        if self.machinist_setting == 0:
            self.z_cut = self.check_zcut(zcut=self.z_cut)
            if self.z_cut == 'fail':
                return 'fail'
        # multidepth use this
        old_zcut = deepcopy(self.z_cut)

        # XY_toolchange parameter
        try:
            if self.xy_toolchange == '':
                self.xy_toolchange = None
            else:
                self.xy_toolchange = re.sub('[()\[\]]', '', str(self.xy_toolchange)) if self.xy_toolchange else None

                if self.xy_toolchange:
                    self.xy_toolchange = [float(eval(a)) for a in self.xy_toolchange.split(",")]

                if self.xy_toolchange and len(self.xy_toolchange) != 2:
                    self.app.inform.emit('[ERROR]%s' %
                                         _("The Toolchange X,Y field in Edit -> Preferences has to be "
                                           "in the format (x, y) \nbut now there is only one value, not two. "))
                    return 'fail'
        except Exception as e:
            log.debug("camlib.CNCJob.generate_from_excellon_by_tool() --> %s" % str(e))
            pass

        # XY_end parameter
        self.xy_end = re.sub('[()\[\]]', '', str(self.xy_end)) if self.xy_end else None
        if self.xy_end and self.xy_end != '':
            self.xy_end = [float(eval(a)) for a in self.xy_end.split(",")]
        if self.xy_end and len(self.xy_end) < 2:
            self.app.inform.emit('[ERROR]  %s' % _("The End Move X,Y field in Edit -> Preferences has to be "
                                                   "in the format (x, y) but now there is only one value, not two."))
            return 'fail'

        # Prepprocessor
        self.pp_excellon = self.app.preprocessors[self.pp_excellon_name]
        p = self.pp_excellon

        log.debug("Creating CNC Job from Excellon...")

        # #############################################################################################################
        # #############################################################################################################
        # TOOLS
        # sort the tools list by the second item in tuple (here we have a dict with diameter of the tool)
        # so we actually are sorting the tools by diameter
        # #############################################################################################################
        # #############################################################################################################
        all_tools = []
        for tool_as_key, v in list(self.exc_tools.items()):
            all_tools.append((int(tool_as_key), float(v['tooldia'])))

        if order == 'fwd':
            sorted_tools = sorted(all_tools, key=lambda t1: t1[1])
        elif order == 'rev':
            sorted_tools = sorted(all_tools, key=lambda t1: t1[1], reverse=True)
        else:
            sorted_tools = all_tools

        if tools == "all":
            selected_tools = [i[0] for i in all_tools]  # we get a array of ordered tools
        else:
            selected_tools = eval(tools)

        # Create a sorted list of selected tools from the sorted_tools list
        tools = [i for i, j in sorted_tools for k in selected_tools if i == k]

        log.debug("Tools sorted are: %s" % str(tools))

        # #############################################################################################################
        # #############################################################################################################
        # build a self.options['Tools_in_use'] list from scratch if we don't have one like in the case of
        # running this method from a Tcl Command
        # #############################################################################################################
        # #############################################################################################################
        build_tools_in_use_list = False
        if 'Tools_in_use' not in self.options:
            self.options['Tools_in_use'] = []

        # if the list is empty (either we just added the key or it was already there but empty) signal to build it
        if not self.options['Tools_in_use']:
            build_tools_in_use_list = True

        # #############################################################################################################
        # #############################################################################################################
        # fill the data into the self.exc_cnc_tools dictionary
        # #############################################################################################################
        # #############################################################################################################
        for it in all_tools:
            for to_ol in tools:
                if to_ol == it[0]:
                    sol_geo = []

                    drill_no = 0
                    if 'drills' in exobj.tools[to_ol]:
                        drill_no = len(exobj.tools[to_ol]['drills'])
                        for drill in exobj.tools[to_ol]['drills']:
                            sol_geo.append(drill.buffer((it[1] / 2.0), resolution=self.geo_steps_per_circle))

                    slot_no = 0
                    if 'slots' in exobj.tools[to_ol]:
                        slot_no = len(exobj.tools[to_ol]['slots'])
                        for slot in exobj.tools[to_ol]['slots']:
                            start = (slot[0].x, slot[0].y)
                            stop = (slot[1].x, slot[1].y)
                            sol_geo.append(
                                LineString([start, stop]).buffer((it[1] / 2.0), resolution=self.geo_steps_per_circle)
                            )

                    if self.use_ui:
                        try:
                            z_off = float(exobj.tools[it[0]]['data']['tools_drill_offset']) * (-1)
                        except KeyError:
                            z_off = 0
                    else:
                        z_off = 0

                    default_data = {}
                    for k, v in list(self.options.items()):
                        default_data[k] = deepcopy(v)

                    # it[1] is the tool diameter
                    self.exc_cnc_tools[it[1]] = {}
                    self.exc_cnc_tools[it[1]]['tool'] = it[0]
                    self.exc_cnc_tools[it[1]]['nr_drills'] = drill_no
                    self.exc_cnc_tools[it[1]]['nr_slots'] = slot_no
                    self.exc_cnc_tools[it[1]]['offset_z'] = z_off
                    self.exc_cnc_tools[it[1]]['data'] = default_data
                    self.exc_cnc_tools[it[1]]['solid_geometry'] = deepcopy(sol_geo)

                    # build a self.options['Tools_in_use'] list from scratch if we don't have one like in the case of
                    # running this method from a Tcl Command
                    if build_tools_in_use_list is True:
                        self.options['Tools_in_use'].append(
                            [it[0], it[1], drill_no, slot_no]
                        )

        self.app.inform.emit(_("Creating a list of points to drill..."))

        # #############################################################################################################
        # #############################################################################################################
        # Points (Group by tool): a dictionary of shapely Point geo elements grouped by tool number
        # #############################################################################################################
        # #############################################################################################################
        points = {}
        for tool, tool_dict in self.exc_tools.items():
            if tool in tools:
                if self.app.abort_flag:
                    # graceful abort requested by the user
                    raise grace

                if 'drills' in tool_dict and tool_dict['drills']:
                    for drill_pt in tool_dict['drills']:
                        try:
                            points[tool].append(drill_pt)
                        except KeyError:
                            points[tool] = [drill_pt]
        log.debug("Found %d TOOLS with drills." % len(points))

        # check if there are drill points in the exclusion areas.
        # If we find any within the exclusion areas return 'fail'
        for tool in points:
            for pt in points[tool]:
                for area in self.app.exc_areas.exclusion_areas_storage:
                    pt_buf = pt.buffer(self.exc_tools[tool]['tooldia'] / 2.0)
                    if pt_buf.within(area['shape']) or pt_buf.intersects(area['shape']):
                        self.app.inform.emit("[ERROR_NOTCL] %s" % _("Failed. Drill points inside the exclusion zones."))
                        return 'fail'

        # this holds the resulting GCode
        self.gcode = []
        # #############################################################################################################
        # #############################################################################################################
        # Initialization
        # #############################################################################################################
        # #############################################################################################################
        gcode = ''
        start_gcode = ''
        if is_first:
            start_gcode = self.doformat(p.start_code)

        if use_ui is False:
            gcode += self.doformat(p.z_feedrate_code)

        if self.toolchange is False:
            if self.xy_toolchange is not None:
                gcode += self.doformat(p.lift_code, x=self.xy_toolchange[0], y=self.xy_toolchange[1])
                gcode += self.doformat(p.startz_code, x=self.xy_toolchange[0], y=self.xy_toolchange[1])
            else:
                gcode += self.doformat(p.lift_code, x=0.0, y=0.0)
                gcode += self.doformat(p.startz_code, x=0.0, y=0.0)

        if self.xy_toolchange is not None:
            self.oldx = self.xy_toolchange[0]
            self.oldy = self.xy_toolchange[1]
        else:
            self.oldx = 0.0
            self.oldy = 0.0

        measured_distance = 0.0
        measured_down_distance = 0.0
        measured_up_to_zero_distance = 0.0
        measured_lift_distance = 0.0

        # #############################################################################################################
        # #############################################################################################################
        # GCODE creation
        # #############################################################################################################
        # #############################################################################################################
        self.app.inform.emit('%s...' % _("Starting G-Code"))

        has_drills = None
        for tool, tool_dict in self.exc_tools.items():
            if 'drills' in tool_dict and tool_dict['drills']:
                has_drills = True
                break
        if not has_drills:
            log.debug("camlib.CNCJob.generate_from_excellon_by_tool() --> "
                      "The loaded Excellon file has no drills ...")
            self.app.inform.emit('[ERROR_NOTCL] %s...' % _('The loaded Excellon file has no drills'))
            return 'fail'

        current_platform = platform.architecture()[0]
        if current_platform == '64bit':
            used_excellon_optimization_type = self.excellon_optimization_type
        else:
            used_excellon_optimization_type = 'T'

        # #############################################################################################################
        # #############################################################################################################
        # ##################################   DRILLING !!!   #########################################################
        # #############################################################################################################
        # #############################################################################################################
        if used_excellon_optimization_type == 'M':
            log.debug("Using OR-Tools Metaheuristic Guided Local Search drill path optimization.")
        elif used_excellon_optimization_type == 'B':
            log.debug("Using OR-Tools Basic drill path optimization.")
        elif used_excellon_optimization_type == 'T':
            log.debug("Using Travelling Salesman drill path optimization.")
        else:
            log.debug("Using no path optimization.")

        if self.toolchange is True:
            for tool in tools:
                # check if it has drills
                if not self.exc_tools[tool]['drills']:
                    continue

                if self.app.abort_flag:
                    # graceful abort requested by the user
                    raise grace

                self.tool = tool
                self.tooldia = self.exc_tools[tool]["tooldia"]
                self.postdata['toolC'] = self.tooldia

                if self.use_ui:
                    self.z_feedrate = self.exc_tools[tool]['data']['tools_drill_feedrate_z']
                    self.feedrate = self.exc_tools[tool]['data']['tools_drill_feedrate_z']
                    self.z_cut = self.exc_tools[tool]['data']['tools_drill_cutz']
                    gcode += self.doformat(p.z_feedrate_code)

                    if self.machinist_setting == 0:
                        if self.z_cut > 0:
                            self.app.inform.emit('[WARNING] %s' %
                                                 _("The Cut Z parameter has positive value. "
                                                   "It is the depth value to drill into material.\n"
                                                   "The Cut Z parameter needs to have a negative value, "
                                                   "assuming it is a typo "
                                                   "therefore the app will convert the value to negative. "
                                                   "Check the resulting CNC code (Gcode etc)."))
                            self.z_cut = -self.z_cut
                        elif self.z_cut == 0:
                            self.app.inform.emit('[WARNING] %s: %s' %
                                                 (_(
                                                     "The Cut Z parameter is zero. There will be no cut, "
                                                     "skipping file"),
                                                  exobj.options['name']))
                            return 'fail'

                    old_zcut = deepcopy(self.z_cut)

                    self.z_move = self.exc_tools[tool]['data']['tools_drill_travelz']
                    self.spindlespeed = self.exc_tools[tool]['data']['tools_drill_spindlespeed']
                    self.dwell = self.exc_tools[tool]['data']['tools_drill_dwell']
                    self.dwelltime = self.exc_tools[tool]['data']['tools_drill_dwelltime']
                    self.multidepth = self.exc_tools[tool]['data']['tools_drill_multidepth']
                    self.z_depthpercut = self.exc_tools[tool]['data']['tools_drill_depthperpass']
                else:
                    old_zcut = deepcopy(self.z_cut)

                # #########################################################################################################
                # ############ Create the data. #################
                # #########################################################################################################
                locations = []
                altPoints = []
                optimized_path = []

                if used_excellon_optimization_type == 'M':
                    if tool in points:
                        locations = self.create_tool_data_array(points=points[tool])
                    # if there are no locations then go to the next tool
                    if not locations:
                        continue
                    opt_time = self.app.defaults["excellon_search_time"]
                    optimized_path = self.optimized_ortools_meta(locations=locations, opt_time=opt_time)
                elif used_excellon_optimization_type == 'B':
                    if tool in points:
                        locations = self.create_tool_data_array(points=points[tool])
                    # if there are no locations then go to the next tool
                    if not locations:
                        continue
                    optimized_path = self.optimized_ortools_basic(locations=locations)
                elif used_excellon_optimization_type == 'T':
                    for point in points[tool]:
                        altPoints.append((point.coords.xy[0][0], point.coords.xy[1][0]))
                    optimized_path = self.optimized_travelling_salesman(altPoints)
                else:
                    # it's actually not optimized path but here we build a list of (x,y) coordinates
                    # out of the tool's drills
                    for drill in self.exc_tools[tool]['drills']:
                        unoptimized_coords = (
                            drill.x,
                            drill.y
                        )
                        optimized_path.append(unoptimized_coords)
                # #########################################################################################################
                # #########################################################################################################

                # Only if there are locations to drill
                if not optimized_path:
                    continue

                if self.app.abort_flag:
                    # graceful abort requested by the user
                    raise grace

                # Tool change sequence (optional)
                if self.toolchange:
                    gcode += self.doformat(p.toolchange_code, toolchangexy=(self.oldx, self.oldy))
                # Spindle start
                gcode += self.doformat(p.spindle_code)
                # Dwell time
                if self.dwell is True:
                    gcode += self.doformat(p.dwell_code)

                current_tooldia = float('%.*f' % (self.decimals, float(self.exc_tools[tool]["tooldia"])))

                self.app.inform.emit(
                    '%s: %s%s.' % (_("Starting G-Code for tool with diameter"),
                                   str(current_tooldia),
                                   str(self.units))
                )

                # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                # APPLY Offset only when using the appGUI, for TclCommand this will create an error
                # because the values for Z offset are created in build_ui()
                # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                try:
                    z_offset = float(self.exc_tools[tool]['data']['tools_drill_offset']) * (-1)
                except KeyError:
                    z_offset = 0
                self.z_cut = z_offset + old_zcut

                self.coordinates_type = self.app.defaults["cncjob_coords_type"]
                if self.coordinates_type == "G90":
                    # Drillling! for Absolute coordinates type G90
                    # variables to display the percentage of work done
                    geo_len = len(optimized_path)

                    old_disp_number = 0
                    log.warning("Number of drills for which to generate GCode: %s" % str(geo_len))

                    loc_nr = 0
                    for point in optimized_path:
                        if self.app.abort_flag:
                            # graceful abort requested by the user
                            raise grace

                        if used_excellon_optimization_type == 'T':
                            locx = point[0]
                            locy = point[1]
                        else:
                            locx = locations[point][0]
                            locy = locations[point][1]

                        travels = self.app.exc_areas.travel_coordinates(start_point=(self.oldx, self.oldy),
                                                                        end_point=(locx, locy),
                                                                        tooldia=current_tooldia)
                        prev_z = None
                        for travel in travels:
                            locx = travel[1][0]
                            locy = travel[1][1]

                            if travel[0] is not None:
                                # move to next point
                                gcode += self.doformat(p.rapid_code, x=locx, y=locy)

                                # raise to safe Z (travel[0]) each time because safe Z may be different
                                self.z_move = travel[0]
                                gcode += self.doformat(p.lift_code, x=locx, y=locy)

                                # restore z_move
                                self.z_move = self.exc_tools[tool]['data']['tools_drill_travelz']
                            else:
                                if prev_z is not None:
                                    # move to next point
                                    gcode += self.doformat(p.rapid_code, x=locx, y=locy)

                                    # we assume that previously the z_move was altered therefore raise to
                                    # the travel_z (z_move)
                                    self.z_move = self.exc_tools[tool]['data']['tools_drill_travelz']
                                    gcode += self.doformat(p.lift_code, x=locx, y=locy)
                                else:
                                    # move to next point
                                    gcode += self.doformat(p.rapid_code, x=locx, y=locy)

                            # store prev_z
                            prev_z = travel[0]

                        # gcode += self.doformat(p.rapid_code, x=locx, y=locy)

                        if self.multidepth and abs(self.z_cut) > abs(self.z_depthpercut):
                            doc = deepcopy(self.z_cut)
                            self.z_cut = 0.0

                            while abs(self.z_cut) < abs(doc):

                                self.z_cut -= self.z_depthpercut
                                if abs(doc) < abs(self.z_cut) < (abs(doc) + self.z_depthpercut):
                                    self.z_cut = doc
                                gcode += self.doformat(p.down_code, x=locx, y=locy)

                                measured_down_distance += abs(self.z_cut) + abs(self.z_move)

                                if self.f_retract is False:
                                    gcode += self.doformat(p.up_to_zero_code, x=locx, y=locy)
                                    measured_up_to_zero_distance += abs(self.z_cut)
                                    measured_lift_distance += abs(self.z_move)
                                else:
                                    measured_lift_distance += abs(self.z_cut) + abs(self.z_move)

                                gcode += self.doformat(p.lift_code, x=locx, y=locy)

                        else:
                            gcode += self.doformat(p.down_code, x=locx, y=locy)

                            measured_down_distance += abs(self.z_cut) + abs(self.z_move)

                            if self.f_retract is False:
                                gcode += self.doformat(p.up_to_zero_code, x=locx, y=locy)
                                measured_up_to_zero_distance += abs(self.z_cut)
                                measured_lift_distance += abs(self.z_move)
                            else:
                                measured_lift_distance += abs(self.z_cut) + abs(self.z_move)

                            gcode += self.doformat(p.lift_code, x=locx, y=locy)

                        measured_distance += abs(distance_euclidian(locx, locy, self.oldx, self.oldy))
                        self.oldx = locx
                        self.oldy = locy

                        loc_nr += 1
                        disp_number = int(np.interp(loc_nr, [0, geo_len], [0, 100]))

                        if old_disp_number < disp_number <= 100:
                            self.app.proc_container.update_view_text(' %d%%' % disp_number)
                            old_disp_number = disp_number

                else:
                    self.app.inform.emit('[ERROR_NOTCL] %s...' % _('G91 coordinates not implemented'))
                    return 'fail'
                self.z_cut = deepcopy(old_zcut)
        else:
            # We are not using Toolchange therefore we need to decide which tool properties to use
            one_tool = 1

            all_points = []
            for tool in points:
                # check if it has drills
                if not points[tool]:
                    continue
                all_points += points[tool]

            if self.app.abort_flag:
                # graceful abort requested by the user
                raise grace

            self.tool = one_tool
            self.tooldia = self.exc_tools[one_tool]["tooldia"]
            self.postdata['toolC'] = self.tooldia

            if self.use_ui:
                self.z_feedrate = self.exc_tools[one_tool]['data']['tools_drill_feedrate_z']
                self.feedrate = self.exc_tools[one_tool]['data']['tools_drill_feedrate_z']
                self.z_cut = self.exc_tools[one_tool]['data']['tools_drill_cutz']
                gcode += self.doformat(p.z_feedrate_code)

                if self.machinist_setting == 0:
                    if self.z_cut > 0:
                        self.app.inform.emit('[WARNING] %s' %
                                             _("The Cut Z parameter has positive value. "
                                               "It is the depth value to drill into material.\n"
                                               "The Cut Z parameter needs to have a negative value, "
                                               "assuming it is a typo "
                                               "therefore the app will convert the value to negative. "
                                               "Check the resulting CNC code (Gcode etc)."))
                        self.z_cut = -self.z_cut
                    elif self.z_cut == 0:
                        self.app.inform.emit('[WARNING] %s: %s' %
                                             (_(
                                                 "The Cut Z parameter is zero. There will be no cut, "
                                                 "skipping file"),
                                              exobj.options['name']))
                        return 'fail'

                old_zcut = deepcopy(self.z_cut)

                self.z_move = self.exc_tools[one_tool]['data']['tools_drill_travelz']
                self.spindlespeed = self.exc_tools[one_tool]['data']['tools_drill_spindlespeed']
                self.dwell = self.exc_tools[one_tool]['data']['tools_drill_dwell']
                self.dwelltime = self.exc_tools[one_tool]['data']['tools_drill_dwelltime']
                self.multidepth = self.exc_tools[one_tool]['data']['tools_drill_multidepth']
                self.z_depthpercut = self.exc_tools[one_tool]['data']['tools_drill_depthperpass']
            else:
                old_zcut = deepcopy(self.z_cut)

            # #########################################################################################################
            # ############ Create the data. #################
            # #########################################################################################################
            locations = []
            altPoints = []
            optimized_path = []

            if used_excellon_optimization_type == 'M':
                if all_points:
                    locations = self.create_tool_data_array(points=all_points)
                # if there are no locations then go to the next tool
                if not locations:
                    return 'fail'
                opt_time = self.app.defaults["excellon_search_time"]
                optimized_path = self.optimized_ortools_meta(locations=locations, opt_time=opt_time)
            elif used_excellon_optimization_type == 'B':
                if all_points:
                    locations = self.create_tool_data_array(points=all_points)
                # if there are no locations then go to the next tool
                if not locations:
                    return 'fail'
                optimized_path = self.optimized_ortools_basic(locations=locations)
            elif used_excellon_optimization_type == 'T':
                for point in all_points:
                    altPoints.append((point.coords.xy[0][0], point.coords.xy[1][0]))
                optimized_path = self.optimized_travelling_salesman(altPoints)
            else:
                # it's actually not optimized path but here we build a list of (x,y) coordinates
                # out of the tool's drills
                for pt in all_points:
                    unoptimized_coords = (
                        pt.x,
                        pt.y
                    )
                    optimized_path.append(unoptimized_coords)
            # #########################################################################################################
            # #########################################################################################################

            # Only if there are locations to drill
            if not optimized_path:
                return 'fail'

            if self.app.abort_flag:
                # graceful abort requested by the user
                raise grace

            # Spindle start
            gcode += self.doformat(p.spindle_code)
            # Dwell time
            if self.dwell is True:
                gcode += self.doformat(p.dwell_code)

            current_tooldia = float('%.*f' % (self.decimals, float(self.exc_tools[one_tool]["tooldia"])))

            self.app.inform.emit(
                '%s: %s%s.' % (_("Starting G-Code for tool with diameter"),
                               str(current_tooldia),
                               str(self.units))
            )

            # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            # APPLY Offset only when using the appGUI, for TclCommand this will create an error
            # because the values for Z offset are created in build_ui()
            # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            try:
                z_offset = float(self.exc_tools[one_tool]['data']['tools_drill_offset']) * (-1)
            except KeyError:
                z_offset = 0
            self.z_cut = z_offset + old_zcut

            self.coordinates_type = self.app.defaults["cncjob_coords_type"]
            if self.coordinates_type == "G90":
                # Drillling! for Absolute coordinates type G90
                # variables to display the percentage of work done
                geo_len = len(optimized_path)

                old_disp_number = 0
                log.warning("Number of drills for which to generate GCode: %s" % str(geo_len))

                loc_nr = 0
                for point in optimized_path:
                    if self.app.abort_flag:
                        # graceful abort requested by the user
                        raise grace

                    if used_excellon_optimization_type == 'T':
                        locx = point[0]
                        locy = point[1]
                    else:
                        locx = locations[point][0]
                        locy = locations[point][1]

                    travels = self.app.exc_areas.travel_coordinates(start_point=(self.oldx, self.oldy),
                                                                    end_point=(locx, locy),
                                                                    tooldia=current_tooldia)
                    prev_z = None
                    for travel in travels:
                        locx = travel[1][0]
                        locy = travel[1][1]

                        if travel[0] is not None:
                            # move to next point
                            gcode += self.doformat(p.rapid_code, x=locx, y=locy)

                            # raise to safe Z (travel[0]) each time because safe Z may be different
                            self.z_move = travel[0]
                            gcode += self.doformat(p.lift_code, x=locx, y=locy)

                            # restore z_move
                            self.z_move = self.exc_tools[one_tool]['data']['tools_drill_travelz']
                        else:
                            if prev_z is not None:
                                # move to next point
                                gcode += self.doformat(p.rapid_code, x=locx, y=locy)

                                # we assume that previously the z_move was altered therefore raise to
                                # the travel_z (z_move)
                                self.z_move = self.exc_tools[one_tool]['data']['tools_drill_travelz']
                                gcode += self.doformat(p.lift_code, x=locx, y=locy)
                            else:
                                # move to next point
                                gcode += self.doformat(p.rapid_code, x=locx, y=locy)

                        # store prev_z
                        prev_z = travel[0]

                    # gcode += self.doformat(p.rapid_code, x=locx, y=locy)

                    if self.multidepth and abs(self.z_cut) > abs(self.z_depthpercut):
                        doc = deepcopy(self.z_cut)
                        self.z_cut = 0.0

                        while abs(self.z_cut) < abs(doc):

                            self.z_cut -= self.z_depthpercut
                            if abs(doc) < abs(self.z_cut) < (abs(doc) + self.z_depthpercut):
                                self.z_cut = doc
                            gcode += self.doformat(p.down_code, x=locx, y=locy)

                            measured_down_distance += abs(self.z_cut) + abs(self.z_move)

                            if self.f_retract is False:
                                gcode += self.doformat(p.up_to_zero_code, x=locx, y=locy)
                                measured_up_to_zero_distance += abs(self.z_cut)
                                measured_lift_distance += abs(self.z_move)
                            else:
                                measured_lift_distance += abs(self.z_cut) + abs(self.z_move)

                            gcode += self.doformat(p.lift_code, x=locx, y=locy)

                    else:
                        gcode += self.doformat(p.down_code, x=locx, y=locy)

                        measured_down_distance += abs(self.z_cut) + abs(self.z_move)

                        if self.f_retract is False:
                            gcode += self.doformat(p.up_to_zero_code, x=locx, y=locy)
                            measured_up_to_zero_distance += abs(self.z_cut)
                            measured_lift_distance += abs(self.z_move)
                        else:
                            measured_lift_distance += abs(self.z_cut) + abs(self.z_move)

                        gcode += self.doformat(p.lift_code, x=locx, y=locy)

                    measured_distance += abs(distance_euclidian(locx, locy, self.oldx, self.oldy))
                    self.oldx = locx
                    self.oldy = locy

                    loc_nr += 1
                    disp_number = int(np.interp(loc_nr, [0, geo_len], [0, 100]))

                    if old_disp_number < disp_number <= 100:
                        self.app.proc_container.update_view_text(' %d%%' % disp_number)
                        old_disp_number = disp_number

            else:
                self.app.inform.emit('[ERROR_NOTCL] %s...' % _('G91 coordinates not implemented'))
                return 'fail'
            self.z_cut = deepcopy(old_zcut)

        if used_excellon_optimization_type == 'M':
            log.debug("The total travel distance with OR-TOOLS Metaheuristics is: %s" % str(measured_distance))
        elif used_excellon_optimization_type == 'B':
            log.debug("The total travel distance with OR-TOOLS Basic Algorithm is: %s" % str(measured_distance))
        elif used_excellon_optimization_type == 'T':
            log.debug("The total travel distance with Travelling Salesman Algorithm is: %s" % str(measured_distance))
        else:
            log.debug("The total travel distance with with no optimization is: %s" % str(measured_distance))

        # if used_excellon_optimization_type == 'M':
        #     log.debug("Using OR-Tools Metaheuristic Guided Local Search drill path optimization.")
        #
        #     if has_drills:
        #         for tool in tools:
        #             if self.app.abort_flag:
        #                 # graceful abort requested by the user
        #                 raise grace
        #
        #             self.tool = tool
        #             self.tooldia = self.exc_tools[tool]["tooldia"]
        #             self.postdata['toolC'] = self.tooldia
        #
        #             if self.use_ui:
        #                 self.z_feedrate = self.exc_tools[tool]['data']['feedrate_z']
        #                 self.feedrate = self.exc_tools[tool]['data']['feedrate']
        #                 gcode += self.doformat(p.z_feedrate_code)
        #                 self.z_cut = self.exc_tools[tool]['data']['cutz']
        #
        #                 if self.machinist_setting == 0:
        #                     if self.z_cut > 0:
        #                         self.app.inform.emit('[WARNING] %s' %
        #                                              _("The Cut Z parameter has positive value. "
        #                                                "It is the depth value to drill into material.\n"
        #                                                "The Cut Z parameter needs to have a negative value, "
        #                                                "assuming it is a typo "
        #                                                "therefore the app will convert the value to negative. "
        #                                                "Check the resulting CNC code (Gcode etc)."))
        #                         self.z_cut = -self.z_cut
        #                     elif self.z_cut == 0:
        #                         self.app.inform.emit('[WARNING] %s: %s' %
        #                                              (_(
        #                                                  "The Cut Z parameter is zero. There will be no cut, "
        #                                                  "skipping file"),
        #                                               exobj.options['name']))
        #                         return 'fail'
        #
        #                 old_zcut = deepcopy(self.z_cut)
        #
        #                 self.z_move = self.exc_tools[tool]['data']['travelz']
        #                 self.spindlespeed = self.exc_tools[tool]['data']['spindlespeed']
        #                 self.dwell = self.exc_tools[tool]['data']['dwell']
        #                 self.dwelltime = self.exc_tools[tool]['data']['dwelltime']
        #                 self.multidepth = self.exc_tools[tool]['data']['multidepth']
        #                 self.z_depthpercut = self.exc_tools[tool]['data']['depthperpass']
        #             else:
        #                 old_zcut = deepcopy(self.z_cut)
        #
        #             # ###############################################
        #             # ############ Create the data. #################
        #             # ###############################################
        #             locations = self.create_tool_data_array(tool=tool, points=points)
        #             # if there are no locations then go to the next tool
        #             if not locations:
        #                 continue
        #             optimized_path = self.optimized_ortools_meta(locations=locations)
        #
        #             # Only if tool has points.
        #             if tool in points:
        #                 if self.app.abort_flag:
        #                     # graceful abort requested by the user
        #                     raise grace
        #
        #                 # Tool change sequence (optional)
        #                 if self.toolchange:
        #                     gcode += self.doformat(p.toolchange_code, toolchangexy=(self.oldx, self.oldy))
        #                 # Spindle start
        #                 gcode += self.doformat(p.spindle_code)
        #                 # Dwell time
        #                 if self.dwell is True:
        #                     gcode += self.doformat(p.dwell_code)
        #
        #                 current_tooldia = float('%.*f' % (self.decimals, float(self.exc_tools[tool]["tooldia"])))
        #
        #                 self.app.inform.emit(
        #                     '%s: %s%s.' % (_("Starting G-Code for tool with diameter"),
        #                                    str(current_tooldia),
        #                                    str(self.units))
        #                 )
        #
        #                 # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        #                 # APPLY Offset only when using the appGUI, for TclCommand this will create an error
        #                 # because the values for Z offset are created in build_ui()
        #                 # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        #                 try:
        #                     z_offset = float(self.exc_tools[tool]['data']['offset']) * (-1)
        #                 except KeyError:
        #                     z_offset = 0
        #                 self.z_cut = z_offset + old_zcut
        #
        #                 self.coordinates_type = self.app.defaults["cncjob_coords_type"]
        #                 if self.coordinates_type == "G90":
        #                     # Drillling! for Absolute coordinates type G90
        #                     # variables to display the percentage of work done
        #                     geo_len = len(optimized_path)
        #
        #                     old_disp_number = 0
        #                     log.warning("Number of drills for which to generate GCode: %s" % str(geo_len))
        #
        #                     loc_nr = 0
        #                     for k in optimized_path:
        #                         if self.app.abort_flag:
        #                             # graceful abort requested by the user
        #                             raise grace
        #
        #                         locx = locations[k][0]
        #                         locy = locations[k][1]
        #
        #                         travels = self.app.exc_areas.travel_coordinates(start_point=(self.oldx, self.oldy),
        #                                                                         end_point=(locx, locy),
        #                                                                         tooldia=current_tooldia)
        #                         prev_z = None
        #                         for travel in travels:
        #                             locx = travel[1][0]
        #                             locy = travel[1][1]
        #
        #                             if travel[0] is not None:
        #                                 # move to next point
        #                                 gcode += self.doformat(p.rapid_code, x=locx, y=locy)
        #
        #                                 # raise to safe Z (travel[0]) each time because safe Z may be different
        #                                 self.z_move = travel[0]
        #                                 gcode += self.doformat(p.lift_code, x=locx, y=locy)
        #
        #                                 # restore z_move
        #                                 self.z_move = self.exc_tools[tool]['data']['travelz']
        #                             else:
        #                                 if prev_z is not None:
        #                                     # move to next point
        #                                     gcode += self.doformat(p.rapid_code, x=locx, y=locy)
        #
        #                                     # we assume that previously the z_move was altered therefore raise to
        #                                     # the travel_z (z_move)
        #                                     self.z_move = self.exc_tools[tool]['data']['travelz']
        #                                     gcode += self.doformat(p.lift_code, x=locx, y=locy)
        #                                 else:
        #                                     # move to next point
        #                                     gcode += self.doformat(p.rapid_code, x=locx, y=locy)
        #
        #                             # store prev_z
        #                             prev_z = travel[0]
        #
        #                         # gcode += self.doformat(p.rapid_code, x=locx, y=locy)
        #
        #                         if self.multidepth and abs(self.z_cut) > abs(self.z_depthpercut):
        #                             doc = deepcopy(self.z_cut)
        #                             self.z_cut = 0.0
        #
        #                             while abs(self.z_cut) < abs(doc):
        #
        #                                 self.z_cut -= self.z_depthpercut
        #                                 if abs(doc) < abs(self.z_cut) < (abs(doc) + self.z_depthpercut):
        #                                     self.z_cut = doc
        #                                 gcode += self.doformat(p.down_code, x=locx, y=locy)
        #
        #                                 measured_down_distance += abs(self.z_cut) + abs(self.z_move)
        #
        #                                 if self.f_retract is False:
        #                                     gcode += self.doformat(p.up_to_zero_code, x=locx, y=locy)
        #                                     measured_up_to_zero_distance += abs(self.z_cut)
        #                                     measured_lift_distance += abs(self.z_move)
        #                                 else:
        #                                     measured_lift_distance += abs(self.z_cut) + abs(self.z_move)
        #
        #                                 gcode += self.doformat(p.lift_code, x=locx, y=locy)
        #
        #                         else:
        #                             gcode += self.doformat(p.down_code, x=locx, y=locy)
        #
        #                             measured_down_distance += abs(self.z_cut) + abs(self.z_move)
        #
        #                             if self.f_retract is False:
        #                                 gcode += self.doformat(p.up_to_zero_code, x=locx, y=locy)
        #                                 measured_up_to_zero_distance += abs(self.z_cut)
        #                                 measured_lift_distance += abs(self.z_move)
        #                             else:
        #                                 measured_lift_distance += abs(self.z_cut) + abs(self.z_move)
        #
        #                             gcode += self.doformat(p.lift_code, x=locx, y=locy)
        #
        #                         measured_distance += abs(distance_euclidian(locx, locy, self.oldx, self.oldy))
        #                         self.oldx = locx
        #                         self.oldy = locy
        #
        #                         loc_nr += 1
        #                         disp_number = int(np.interp(loc_nr, [0, geo_len], [0, 100]))
        #
        #                         if old_disp_number < disp_number <= 100:
        #                             self.app.proc_container.update_view_text(' %d%%' % disp_number)
        #                             old_disp_number = disp_number
        #
        #                 else:
        #                     self.app.inform.emit('[ERROR_NOTCL] %s...' % _('G91 coordinates not implemented'))
        #                     return 'fail'
        #             self.z_cut = deepcopy(old_zcut)
        #     else:
        #         log.debug("camlib.CNCJob.generate_from_excellon_by_tool() --> "
        #                   "The loaded Excellon file has no drills ...")
        #         self.app.inform.emit('[ERROR_NOTCL] %s...' % _('The loaded Excellon file has no drills'))
        #         return 'fail'
        #
        #     log.debug("The total travel distance with OR-TOOLS Metaheuristics is: %s" % str(measured_distance))
        #
        # elif used_excellon_optimization_type == 'B':
        #     log.debug("Using OR-Tools Basic drill path optimization.")
        #
        #     if has_drills:
        #         for tool in tools:
        #             if self.app.abort_flag:
        #                 # graceful abort requested by the user
        #                 raise grace
        #
        #             self.tool = tool
        #             self.tooldia = self.exc_tools[tool]["tooldia"]
        #             self.postdata['toolC'] = self.tooldia
        #
        #             if self.use_ui:
        #                 self.z_feedrate = self.exc_tools[tool]['data']['feedrate_z']
        #                 self.feedrate = self.exc_tools[tool]['data']['feedrate']
        #                 gcode += self.doformat(p.z_feedrate_code)
        #                 self.z_cut = self.exc_tools[tool]['data']['cutz']
        #
        #                 if self.machinist_setting == 0:
        #                     if self.z_cut > 0:
        #                         self.app.inform.emit('[WARNING] %s' %
        #                                              _("The Cut Z parameter has positive value. "
        #                                                "It is the depth value to drill into material.\n"
        #                                                "The Cut Z parameter needs to have a negative value, "
        #                                                "assuming it is a typo "
        #                                                "therefore the app will convert the value to negative. "
        #                                                "Check the resulting CNC code (Gcode etc)."))
        #                         self.z_cut = -self.z_cut
        #                     elif self.z_cut == 0:
        #                         self.app.inform.emit('[WARNING] %s: %s' %
        #                                              (_(
        #                                                  "The Cut Z parameter is zero. There will be no cut, "
        #                                                  "skipping file"),
        #                                               exobj.options['name']))
        #                         return 'fail'
        #
        #                 old_zcut = deepcopy(self.z_cut)
        #
        #                 self.z_move = self.exc_tools[tool]['data']['travelz']
        #
        #                 self.spindlespeed = self.exc_tools[tool]['data']['spindlespeed']
        #                 self.dwell = self.exc_tools[tool]['data']['dwell']
        #                 self.dwelltime = self.exc_tools[tool]['data']['dwelltime']
        #                 self.multidepth = self.exc_tools[tool]['data']['multidepth']
        #                 self.z_depthpercut = self.exc_tools[tool]['data']['depthperpass']
        #             else:
        #                 old_zcut = deepcopy(self.z_cut)
        #
        #             # ###############################################
        #             # ############ Create the data. #################
        #             # ###############################################
        #             locations = self.create_tool_data_array(tool=tool, points=points)
        #             # if there are no locations then go to the next tool
        #             if not locations:
        #                 continue
        #             optimized_path = self.optimized_ortools_basic(locations=locations)
        #
        #             # Only if tool has points.
        #             if tool in points:
        #                 if self.app.abort_flag:
        #                     # graceful abort requested by the user
        #                     raise grace
        #
        #                 # Tool change sequence (optional)
        #                 if self.toolchange:
        #                     gcode += self.doformat(p.toolchange_code, toolchangexy=(self.oldx, self.oldy))
        #                     gcode += self.doformat(p.spindle_code)  # Spindle start)
        #                     if self.dwell is True:
        #                         gcode += self.doformat(p.dwell_code)  # Dwell time
        #                 else:
        #                     gcode += self.doformat(p.spindle_code)
        #                     if self.dwell is True:
        #                         gcode += self.doformat(p.dwell_code)  # Dwell time
        #
        #                 current_tooldia = float('%.*f' % (self.decimals, float(self.exc_tools[tool]["tooldia"])))
        #
        #                 self.app.inform.emit(
        #                     '%s: %s%s.' % (_("Starting G-Code for tool with diameter"),
        #                                    str(current_tooldia),
        #                                    str(self.units))
        #                 )
        #
        #                 # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        #                 # APPLY Offset only when using the appGUI, for TclCommand this will create an error
        #                 # because the values for Z offset are created in build_ui()
        #                 # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        #                 try:
        #                     z_offset = float(self.exc_tools[tool]['data']['offset']) * (-1)
        #                 except KeyError:
        #                     z_offset = 0
        #                 self.z_cut = z_offset + old_zcut
        #
        #                 self.coordinates_type = self.app.defaults["cncjob_coords_type"]
        #                 if self.coordinates_type == "G90":
        #                     # Drillling! for Absolute coordinates type G90
        #                     # variables to display the percentage of work done
        #                     geo_len = len(optimized_path)
        #                     old_disp_number = 0
        #                     log.warning("Number of drills for which to generate GCode: %s" % str(geo_len))
        #
        #                     loc_nr = 0
        #                     for k in optimized_path:
        #                         if self.app.abort_flag:
        #                             # graceful abort requested by the user
        #                             raise grace
        #
        #                         locx = locations[k][0]
        #                         locy = locations[k][1]
        #
        #                         travels = self.app.exc_areas.travel_coordinates(start_point=(self.oldx, self.oldy),
        #                                                                         end_point=(locx, locy),
        #                                                                         tooldia=current_tooldia)
        #                         prev_z = None
        #                         for travel in travels:
        #                             locx = travel[1][0]
        #                             locy = travel[1][1]
        #
        #                             if travel[0] is not None:
        #                                 # move to next point
        #                                 gcode += self.doformat(p.rapid_code, x=locx, y=locy)
        #
        #                                 # raise to safe Z (travel[0]) each time because safe Z may be different
        #                                 self.z_move = travel[0]
        #                                 gcode += self.doformat(p.lift_code, x=locx, y=locy)
        #
        #                                 # restore z_move
        #                                 self.z_move = self.exc_tools[tool]['data']['travelz']
        #                             else:
        #                                 if prev_z is not None:
        #                                     # move to next point
        #                                     gcode += self.doformat(p.rapid_code, x=locx, y=locy)
        #
        #                                     # we assume that previously the z_move was altered therefore raise to
        #                                     # the travel_z (z_move)
        #                                     self.z_move = self.exc_tools[tool]['data']['travelz']
        #                                     gcode += self.doformat(p.lift_code, x=locx, y=locy)
        #                                 else:
        #                                     # move to next point
        #                                     gcode += self.doformat(p.rapid_code, x=locx, y=locy)
        #
        #                             # store prev_z
        #                             prev_z = travel[0]
        #
        #                         # gcode += self.doformat(p.rapid_code, x=locx, y=locy)
        #
        #                         if self.multidepth and abs(self.z_cut) > abs(self.z_depthpercut):
        #                             doc = deepcopy(self.z_cut)
        #                             self.z_cut = 0.0
        #
        #                             while abs(self.z_cut) < abs(doc):
        #
        #                                 self.z_cut -= self.z_depthpercut
        #                                 if abs(doc) < abs(self.z_cut) < (abs(doc) + self.z_depthpercut):
        #                                     self.z_cut = doc
        #                                 gcode += self.doformat(p.down_code, x=locx, y=locy)
        #
        #                                 measured_down_distance += abs(self.z_cut) + abs(self.z_move)
        #
        #                                 if self.f_retract is False:
        #                                     gcode += self.doformat(p.up_to_zero_code, x=locx, y=locy)
        #                                     measured_up_to_zero_distance += abs(self.z_cut)
        #                                     measured_lift_distance += abs(self.z_move)
        #                                 else:
        #                                     measured_lift_distance += abs(self.z_cut) + abs(self.z_move)
        #
        #                                 gcode += self.doformat(p.lift_code, x=locx, y=locy)
        #
        #                         else:
        #                             gcode += self.doformat(p.down_code, x=locx, y=locy)
        #
        #                             measured_down_distance += abs(self.z_cut) + abs(self.z_move)
        #
        #                             if self.f_retract is False:
        #                                 gcode += self.doformat(p.up_to_zero_code, x=locx, y=locy)
        #                                 measured_up_to_zero_distance += abs(self.z_cut)
        #                                 measured_lift_distance += abs(self.z_move)
        #                             else:
        #                                 measured_lift_distance += abs(self.z_cut) + abs(self.z_move)
        #
        #                             gcode += self.doformat(p.lift_code, x=locx, y=locy)
        #
        #                         measured_distance += abs(distance_euclidian(locx, locy, self.oldx, self.oldy))
        #                         self.oldx = locx
        #                         self.oldy = locy
        #
        #                         loc_nr += 1
        #                         disp_number = int(np.interp(loc_nr, [0, geo_len], [0, 100]))
        #
        #                         if old_disp_number < disp_number <= 100:
        #                             self.app.proc_container.update_view_text(' %d%%' % disp_number)
        #                             old_disp_number = disp_number
        #
        #                 else:
        #                     self.app.inform.emit('[ERROR_NOTCL] %s...' % _('G91 coordinates not implemented'))
        #                     return 'fail'
        #             self.z_cut = deepcopy(old_zcut)
        #     else:
        #         log.debug("camlib.CNCJob.generate_from_excellon_by_tool() --> "
        #                   "The loaded Excellon file has no drills ...")
        #         self.app.inform.emit('[ERROR_NOTCL] %s...' % _('The loaded Excellon file has no drills'))
        #         return 'fail'
        #
        #     log.debug("The total travel distance with OR-TOOLS Basic Algorithm is: %s" % str(measured_distance))
        #
        # elif used_excellon_optimization_type == 'T':
        #     log.debug("Using Travelling Salesman drill path optimization.")
        #
        #     for tool in tools:
        #         if self.app.abort_flag:
        #             # graceful abort requested by the user
        #             raise grace
        #
        #         if has_drills:
        #             self.tool = tool
        #             self.tooldia = self.exc_tools[tool]["tooldia"]
        #             self.postdata['toolC'] = self.tooldia
        #
        #             if self.use_ui:
        #                 self.z_feedrate = self.exc_tools[tool]['data']['feedrate_z']
        #                 self.feedrate = self.exc_tools[tool]['data']['feedrate']
        #                 gcode += self.doformat(p.z_feedrate_code)
        #
        #                 self.z_cut = self.exc_tools[tool]['data']['cutz']
        #
        #                 if self.machinist_setting == 0:
        #                     if self.z_cut > 0:
        #                         self.app.inform.emit('[WARNING] %s' %
        #                                              _("The Cut Z parameter has positive value. "
        #                                                "It is the depth value to drill into material.\n"
        #                                                "The Cut Z parameter needs to have a negative value, "
        #                                                "assuming it is a typo "
        #                                                "therefore the app will convert the value to negative. "
        #                                                "Check the resulting CNC code (Gcode etc)."))
        #                         self.z_cut = -self.z_cut
        #                     elif self.z_cut == 0:
        #                         self.app.inform.emit('[WARNING] %s: %s' %
        #                                              (_(
        #                                                  "The Cut Z parameter is zero. There will be no cut, "
        #                                                  "skipping file"),
        #                                               exobj.options['name']))
        #                         return 'fail'
        #
        #                 old_zcut = deepcopy(self.z_cut)
        #
        #                 self.z_move = self.exc_tools[tool]['data']['travelz']
        #                 self.spindlespeed = self.exc_tools[tool]['data']['spindlespeed']
        #                 self.dwell = self.exc_tools[tool]['data']['dwell']
        #                 self.dwelltime = self.exc_tools[tool]['data']['dwelltime']
        #                 self.multidepth = self.exc_tools[tool]['data']['multidepth']
        #                 self.z_depthpercut = self.exc_tools[tool]['data']['depthperpass']
        #             else:
        #                 old_zcut = deepcopy(self.z_cut)
        #
        #             # ###############################################
        #             # ############ Create the data. #################
        #             # ###############################################
        #             altPoints = []
        #             for point in points[tool]:
        #                 altPoints.append((point.coords.xy[0][0], point.coords.xy[1][0]))
        #             optimized_path = self.optimized_travelling_salesman(altPoints)
        #
        #             # Only if tool has points.
        #             if tool in points:
        #                 if self.app.abort_flag:
        #                     # graceful abort requested by the user
        #                     raise grace
        #
        #                 # Tool change sequence (optional)
        #                 if self.toolchange:
        #                     gcode += self.doformat(p.toolchange_code, toolchangexy=(self.oldx, self.oldy))
        #                     gcode += self.doformat(p.spindle_code)  # Spindle start)
        #                     if self.dwell is True:
        #                         gcode += self.doformat(p.dwell_code)  # Dwell time
        #                 else:
        #                     gcode += self.doformat(p.spindle_code)
        #                     if self.dwell is True:
        #                         gcode += self.doformat(p.dwell_code)  # Dwell time
        #
        #                 current_tooldia = float('%.*f' % (self.decimals, float(self.exc_tools[tool]["tooldia"])))
        #
        #                 self.app.inform.emit(
        #                     '%s: %s%s.' % (_("Starting G-Code for tool with diameter"),
        #                                    str(current_tooldia),
        #                                    str(self.units))
        #                 )
        #
        #                 # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        #                 # APPLY Offset only when using the appGUI, for TclCommand this will create an error
        #                 # because the values for Z offset are created in build_ui()
        #                 # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        #                 try:
        #                     z_offset = float(self.exc_tools[tool]['data']['offset']) * (-1)
        #                 except KeyError:
        #                     z_offset = 0
        #                 self.z_cut = z_offset + old_zcut
        #
        #                 self.coordinates_type = self.app.defaults["cncjob_coords_type"]
        #                 if self.coordinates_type == "G90":
        #                     # Drillling! for Absolute coordinates type G90
        #                     # variables to display the percentage of work done
        #                     geo_len = len(optimized_path)
        #                     old_disp_number = 0
        #                     log.warning("Number of drills for which to generate GCode: %s" % str(geo_len))
        #
        #                     loc_nr = 0
        #                     for point in optimized_path:
        #                         if self.app.abort_flag:
        #                             # graceful abort requested by the user
        #                             raise grace
        #
        #                         locx = point[0]
        #                         locy = point[1]
        #
        #                         travels = self.app.exc_areas.travel_coordinates(start_point=(self.oldx, self.oldy),
        #                                                                         end_point=(locx, locy),
        #                                                                         tooldia=current_tooldia)
        #                         prev_z = None
        #                         for travel in travels:
        #                             locx = travel[1][0]
        #                             locy = travel[1][1]
        #
        #                             if travel[0] is not None:
        #                                 # move to next point
        #                                 gcode += self.doformat(p.rapid_code, x=locx, y=locy)
        #
        #                                 # raise to safe Z (travel[0]) each time because safe Z may be different
        #                                 self.z_move = travel[0]
        #                                 gcode += self.doformat(p.lift_code, x=locx, y=locy)
        #
        #                                 # restore z_move
        #                                 self.z_move = self.exc_tools[tool]['data']['travelz']
        #                             else:
        #                                 if prev_z is not None:
        #                                     # move to next point
        #                                     gcode += self.doformat(p.rapid_code, x=locx, y=locy)
        #
        #                                     # we assume that previously the z_move was altered therefore raise to
        #                                     # the travel_z (z_move)
        #                                     self.z_move = self.exc_tools[tool]['data']['travelz']
        #                                     gcode += self.doformat(p.lift_code, x=locx, y=locy)
        #                                 else:
        #                                     # move to next point
        #                                     gcode += self.doformat(p.rapid_code, x=locx, y=locy)
        #
        #                             # store prev_z
        #                             prev_z = travel[0]
        #
        #                         # gcode += self.doformat(p.rapid_code, x=locx, y=locy)
        #
        #                         if self.multidepth and abs(self.z_cut) > abs(self.z_depthpercut):
        #                             doc = deepcopy(self.z_cut)
        #                             self.z_cut = 0.0
        #
        #                             while abs(self.z_cut) < abs(doc):
        #
        #                                 self.z_cut -= self.z_depthpercut
        #                                 if abs(doc) < abs(self.z_cut) < (abs(doc) + self.z_depthpercut):
        #                                     self.z_cut = doc
        #                                 gcode += self.doformat(p.down_code, x=locx, y=locy)
        #
        #                                 measured_down_distance += abs(self.z_cut) + abs(self.z_move)
        #
        #                                 if self.f_retract is False:
        #                                     gcode += self.doformat(p.up_to_zero_code, x=locx, y=locy)
        #                                     measured_up_to_zero_distance += abs(self.z_cut)
        #                                     measured_lift_distance += abs(self.z_move)
        #                                 else:
        #                                     measured_lift_distance += abs(self.z_cut) + abs(self.z_move)
        #
        #                                 gcode += self.doformat(p.lift_code, x=locx, y=locy)
        #
        #                         else:
        #                             gcode += self.doformat(p.down_code, x=locx, y=locy)
        #
        #                             measured_down_distance += abs(self.z_cut) + abs(self.z_move)
        #
        #                             if self.f_retract is False:
        #                                 gcode += self.doformat(p.up_to_zero_code, x=locx, y=locy)
        #                                 measured_up_to_zero_distance += abs(self.z_cut)
        #                                 measured_lift_distance += abs(self.z_move)
        #                             else:
        #                                 measured_lift_distance += abs(self.z_cut) + abs(self.z_move)
        #
        #                             gcode += self.doformat(p.lift_code, x=locx, y=locy)
        #
        #                         measured_distance += abs(distance_euclidian(locx, locy, self.oldx, self.oldy))
        #                         self.oldx = locx
        #                         self.oldy = locy
        #
        #                         loc_nr += 1
        #                         disp_number = int(np.interp(loc_nr, [0, geo_len], [0, 100]))
        #
        #                         if old_disp_number < disp_number <= 100:
        #                             self.app.proc_container.update_view_text(' %d%%' % disp_number)
        #                             old_disp_number = disp_number
        #                 else:
        #                     self.app.inform.emit('[ERROR_NOTCL] %s...' % _('G91 coordinates not implemented'))
        #                     return 'fail'
        #             else:
        #                 log.debug("camlib.CNCJob.generate_from_excellon_by_tool() --> "
        #                           "The loaded Excellon file has no drills ...")
        #                 self.app.inform.emit('[ERROR_NOTCL] %s...' % _('The loaded Excellon file has no drills'))
        #                 return 'fail'
        #         self.z_cut = deepcopy(old_zcut)
        #     log.debug("The total travel distance with Travelling Salesman Algorithm is: %s" % str(measured_distance))
        #
        # else:
        #     log.debug("camlib.CNCJob.generate_from_excellon_by_tool(): Chosen drill optimization doesn't exist.")
        #     return 'fail'

        # Spindle stop
        gcode += self.doformat(p.spindle_stop_code)
        # Move to End position
        gcode += self.doformat(p.end_code, x=0, y=0)

        # #############################################################################################################
        # ############################# Calculate DISTANCE and ESTIMATED TIME #########################################
        # #############################################################################################################
        measured_distance += abs(distance_euclidian(self.oldx, self.oldy, 0, 0))
        log.debug("The total travel distance including travel to end position is: %s" %
                  str(measured_distance) + '\n')
        self.travel_distance = measured_distance

        # I use the value of self.feedrate_rapid for the feadrate in case of the measure_lift_distance and for
        # traveled_time because it is not always possible to determine the feedrate that the CNC machine uses
        # for G0 move (the fastest speed available to the CNC router). Although self.feedrate_rapids is used only with
        # Marlin preprocessor and derivatives.
        self.routing_time = (measured_down_distance + measured_up_to_zero_distance) / self.feedrate
        lift_time = measured_lift_distance / self.feedrate_rapid
        traveled_time = measured_distance / self.feedrate_rapid
        self.routing_time += lift_time + traveled_time

        # #############################################################################################################
        # ############################# Store the GCODE for further usage ############################################
        # #############################################################################################################
        self.gcode = gcode

        self.app.inform.emit('%s ...' % _("Finished G-Code generation"))
        return gcode, start_gcode

    # no longer used
    def generate_from_multitool_geometry(self, geometry, append=True, tooldia=None, offset=0.0, tolerance=0, z_cut=1.0,
                                         z_move=2.0, feedrate=2.0, feedrate_z=2.0, feedrate_rapid=30,
                                         spindlespeed=None, spindledir='CW', dwell=False, dwelltime=1.0,
                                         multidepth=False, depthpercut=None, toolchange=False, toolchangez=1.0,
                                         toolchangexy="0.0, 0.0", extracut=False, extracut_length=0.2,
                                         startz=None, endz=2.0, endxy='', pp_geometry_name=None, tool_no=1):
        """
        Algorithm to generate from multitool Geometry.

        Algorithm description:
        ----------------------
        Uses RTree to find the nearest path to follow.

        :param geometry:
        :param append:
        :param tooldia:
        :param offset:
        :param tolerance:
        :param z_cut:
        :param z_move:
        :param feedrate:
        :param feedrate_z:
        :param feedrate_rapid:
        :param spindlespeed:
        :param spindledir:          Direction of rotation for the spindle. If using GRBL laser mode will
        adjust the laser mode

        :param dwell:
        :param dwelltime:
        :param multidepth:          If True, use multiple passes to reach the desired depth.
        :param depthpercut:         Maximum depth in each pass.
        :param toolchange:
        :param toolchangez:
        :param toolchangexy:
        :param extracut:            Adds (or not) an extra cut at the end of each path overlapping the
                                    first point in path to ensure complete copper removal
        :param extracut_length:     Extra cut legth at the end of the path
        :param startz:
        :param endz:
        :param endxy:
        :param pp_geometry_name:
        :param tool_no:
        :return:                    GCode - string
        """

        log.debug("generate_from_multitool_geometry()")

        temp_solid_geometry = []
        if offset != 0.0:
            for it in geometry:
                # if the geometry is a closed shape then create a Polygon out of it
                if isinstance(it, LineString):
                    c = it.coords
                    if c[0] == c[-1]:
                        it = Polygon(it)
                temp_solid_geometry.append(it.buffer(offset, join_style=2))
        else:
            temp_solid_geometry = geometry

        # ## Flatten the geometry. Only linear elements (no polygons) remain.
        flat_geometry = self.flatten(temp_solid_geometry, pathonly=True)
        log.debug("%d paths" % len(flat_geometry))

        try:
            self.tooldia = float(tooldia)
        except Exception as e:
            self.app.inform.emit('[ERROR] %s\n%s' % (_("Failed."), str(e)))
            return 'fail'

        self.z_cut = float(z_cut) if z_cut else None
        self.z_move = float(z_move) if z_move is not None else None

        self.feedrate = float(feedrate) if feedrate else  self.app.defaults["geometry_feedrate"]
        self.z_feedrate = float(feedrate_z) if feedrate_z is not None else self.app.defaults["geometry_feedrate_z"]
        self.feedrate_rapid = float(feedrate_rapid) if feedrate_rapid else self.app.defaults["geometry_feedrate_rapid"]

        self.spindlespeed = int(spindlespeed) if spindlespeed != 0 else None
        self.spindledir = spindledir
        self.dwell = dwell
        self.dwelltime = float(dwelltime) if dwelltime else  self.app.defaults["geometry_dwelltime"]

        self.startz = float(startz) if startz is not None else  self.app.defaults["geometry_startz"]
        self.z_end = float(endz) if endz is not None else  self.app.defaults["geometry_endz"]

        self.xy_end = re.sub('[()\[\]]', '', str(endxy)) if endxy else  self.app.defaults["geometry_endxy"]

        if self.xy_end and self.xy_end != '':
            self.xy_end = [float(eval(a)) for a in self.xy_end.split(",")]

        if self.xy_end and len(self.xy_end) < 2:
            self.app.inform.emit('[ERROR]  %s' % _("The End Move X,Y field in Edit -> Preferences has to be "
                                                   "in the format (x, y) but now there is only one value, not two."))
            return 'fail'

        self.z_depthpercut = float(depthpercut) if depthpercut else self.app.defaults["geometry_depthperpass"]
        self.multidepth = multidepth

        self.z_toolchange = float(toolchangez) if toolchangez is not None else self.app.defaults["geometry_toolchangez"]

        # it servers in the preprocessor file
        self.tool = tool_no

        try:
            if toolchangexy == '':
                self.xy_toolchange = None
            else:
                self.xy_toolchange = re.sub('[()\[\]]', '', str(toolchangexy)) \
                    if toolchangexy else self.app.defaults["geometry_toolchangexy"]

                if self.xy_toolchange and self.xy_toolchange != '':
                    self.xy_toolchange = [float(eval(a)) for a in self.xy_toolchange.split(",")]

                if len(self.xy_toolchange) < 2:
                    self.app.inform.emit('[ERROR]  %s' % _("The Toolchange X,Y field in Edit -> Preferences has to be "
                                                           "in the format (x, y) \n"
                                                           "but now there is only one value, not two."))
                    return 'fail'
        except Exception as e:
            log.debug("camlib.CNCJob.generate_from_multitool_geometry() --> %s" % str(e))
            pass

        self.pp_geometry_name = pp_geometry_name if pp_geometry_name else 'default'
        self.f_plunge = self.app.defaults["geometry_f_plunge"]

        if self.z_cut is None:
            if 'laser' not in self.pp_geometry_name:
                self.app.inform.emit(
                    '[ERROR_NOTCL] %s' % _("Cut_Z parameter is None or zero. Most likely a bad combinations of "
                                           "other parameters."))
                return 'fail'
            else:
                self.z_cut = 0

        if self.machinist_setting == 0:
            if self.z_cut > 0:
                self.app.inform.emit('[WARNING] %s' %
                                     _("The Cut Z parameter has positive value. "
                                       "It is the depth value to cut into material.\n"
                                       "The Cut Z parameter needs to have a negative value, assuming it is a typo "
                                       "therefore the app will convert the value to negative."
                                       "Check the resulting CNC code (Gcode etc)."))
                self.z_cut = -self.z_cut
            elif self.z_cut == 0 and 'laser' not in self.pp_geometry_name:
                self.app.inform.emit('[WARNING] %s: %s' %
                                     (_("The Cut Z parameter is zero. There will be no cut, skipping file"),
                                      self.options['name']))
                return 'fail'

            if self.z_move is None:
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("Travel Z parameter is None or zero."))
                return 'fail'

            if self.z_move < 0:
                self.app.inform.emit('[WARNING] %s' %
                                     _("The Travel Z parameter has negative value. "
                                       "It is the height value to travel between cuts.\n"
                                       "The Z Travel parameter needs to have a positive value, assuming it is a typo "
                                       "therefore the app will convert the value to positive."
                                       "Check the resulting CNC code (Gcode etc)."))
                self.z_move = -self.z_move
            elif self.z_move == 0:
                self.app.inform.emit('[WARNING] %s: %s' %
                                     (_("The Z Travel parameter is zero. This is dangerous, skipping file"),
                                      self.options['name']))
                return 'fail'

        # made sure that depth_per_cut is no more then the z_cut
        if abs(self.z_cut) < self.z_depthpercut:
            self.z_depthpercut = abs(self.z_cut)

        # ## Index first and last points in paths
        # What points to index.
        def get_pts(o):
            return [o.coords[0], o.coords[-1]]

        # Create the indexed storage.
        storage = FlatCAMRTreeStorage()
        storage.get_points = get_pts

        # Store the geometry
        log.debug("Indexing geometry before generating G-Code...")
        self.app.inform.emit(_("Indexing geometry before generating G-Code..."))

        for geo_shape in flat_geometry:
            if self.app.abort_flag:
                # graceful abort requested by the user
                raise grace

            if geo_shape is not None:
                storage.insert(geo_shape)

        # self.input_geometry_bounds = geometry.bounds()

        if not append:
            self.gcode = ""

        # tell preprocessor the number of tool (for toolchange)
        self.tool = tool_no

        # this is the tool diameter, it is used as such to accommodate the preprocessor who need the tool diameter
        # given under the name 'toolC'
        self.postdata['toolC'] = self.tooldia

        # Initial G-Code
        self.pp_geometry = self.app.preprocessors[self.pp_geometry_name]
        p = self.pp_geometry

        self.gcode = self.doformat(p.start_code)

        self.gcode += self.doformat(p.feedrate_code)  # sets the feed rate

        if toolchange is False:
            self.gcode += self.doformat(p.lift_code, x=0, y=0)  # Move (up) to travel height
            self.gcode += self.doformat(p.startz_code, x=0, y=0)

        if toolchange:
            # if "line_xyz" in self.pp_geometry_name:
            #     self.gcode += self.doformat(p.toolchange_code, x=self.xy_toolchange[0], y=self.xy_toolchange[1])
            # else:
            #     self.gcode += self.doformat(p.toolchange_code)
            self.gcode += self.doformat(p.toolchange_code)

            if 'laser' not in self.pp_geometry_name:
                self.gcode += self.doformat(p.spindle_code)  # Spindle start
            else:
                # for laser this will disable the laser
                self.gcode += self.doformat(p.lift_code, x=self.oldx, y=self.oldy)  # Move (up) to travel height

            if self.dwell is True:
                self.gcode += self.doformat(p.dwell_code)  # Dwell time
        else:
            if 'laser' not in self.pp_geometry_name:
                self.gcode += self.doformat(p.spindle_code)  # Spindle start

            if self.dwell is True:
                self.gcode += self.doformat(p.dwell_code)  # Dwell time

        total_travel = 0.0
        total_cut = 0.0

        # ## Iterate over geometry paths getting the nearest each time.
        log.debug("Starting G-Code...")
        self.app.inform.emit('%s...' % _("Starting G-Code"))

        path_count = 0
        current_pt = (0, 0)

        # variables to display the percentage of work done
        geo_len = len(flat_geometry)

        old_disp_number = 0
        log.warning("Number of paths for which to generate GCode: %s" % str(geo_len))

        current_tooldia = float('%.*f' % (self.decimals, float(self.tooldia)))

        self.app.inform.emit('%s: %s%s.' % (_("Starting G-Code for tool with diameter"),
                                            str(current_tooldia),
                                            str(self.units)))

        pt, geo = storage.nearest(current_pt)

        try:
            while True:
                if self.app.abort_flag:
                    # graceful abort requested by the user
                    raise grace

                path_count += 1

                # Remove before modifying, otherwise deletion will fail.
                storage.remove(geo)

                # If last point in geometry is the nearest but prefer the first one if last point == first point
                # then reverse coordinates.
                if pt != geo.coords[0] and pt == geo.coords[-1]:
                    # geo.coords = list(geo.coords)[::-1] # Shapley 2.0
                    geo = LineString(list(geo.coords)[::-1])

                # ---------- Single depth/pass --------
                if not multidepth:
                    # calculate the cut distance
                    total_cut = total_cut + geo.length

                    self.gcode += self.create_gcode_single_pass(geo, current_tooldia, extracut, extracut_length,
                                                                tolerance, z_move=z_move, old_point=current_pt)

                # --------- Multi-pass ---------
                else:
                    # calculate the cut distance
                    # due of the number of cuts (multi depth) it has to multiplied by the number of cuts
                    nr_cuts = 0
                    depth = abs(self.z_cut)
                    while depth > 0:
                        nr_cuts += 1
                        depth -= float(self.z_depthpercut)

                    total_cut += (geo.length * nr_cuts)

                    gc, geo = self.create_gcode_multi_pass(geo, current_tooldia, extracut, extracut_length,
                                                           tolerance,  z_move=z_move, postproc=p,
                                                           old_point=current_pt)
                    self.gcode += gc

                # calculate the total distance
                total_travel = total_travel + abs(distance(pt1=current_pt, pt2=pt))
                current_pt = geo.coords[-1]

                pt, geo = storage.nearest(current_pt)  # Next

                disp_number = int(np.interp(path_count, [0, geo_len], [0, 100]))
                if old_disp_number < disp_number <= 100:
                    self.app.proc_container.update_view_text(' %d%%' % disp_number)
                    old_disp_number = disp_number
        except StopIteration:  # Nothing found in storage.
            pass

        log.debug("Finished G-Code... %s paths traced." % path_count)

        # add move to end position
        total_travel += abs(distance_euclidian(current_pt[0], current_pt[1], 0, 0))
        self.travel_distance += total_travel + total_cut
        self.routing_time += total_cut / self.feedrate

        # Finish
        self.gcode += self.doformat(p.spindle_stop_code)
        self.gcode += self.doformat(p.lift_code, x=current_pt[0], y=current_pt[1])
        self.gcode += self.doformat(p.end_code, x=0, y=0)
        self.app.inform.emit(
            '%s... %s %s.' % (_("Finished G-Code generation"), str(path_count), _("paths traced"))
        )
        return self.gcode

    def generate_from_geometry_2(self, geometry, append=True, tooldia=None, offset=0.0, tolerance=0, z_cut=None,
                                 z_move=None, feedrate=None, feedrate_z=None, feedrate_rapid=None, spindlespeed=None,
                                 spindledir='CW', dwell=False, dwelltime=None, multidepth=False, depthpercut=None,
                                 toolchange=False, toolchangez=None, toolchangexy="0.0, 0.0", extracut=False,
                                 extracut_length=None, startz=None, endz=None, endxy='', pp_geometry_name=None,
                                 tool_no=1, is_first=False):
        """
        Second algorithm to generate from Geometry.

        Algorithm description:
        ----------------------
        Uses RTree to find the nearest path to follow.

        :param geometry:
        :param append:
        :param tooldia:
        :param offset:
        :param tolerance:
        :param z_cut:
        :param z_move:
        :param feedrate:
        :param feedrate_z:
        :param feedrate_rapid:
        :param spindlespeed:
        :param spindledir:
        :param dwell:
        :param dwelltime:
        :param multidepth:          If True, use multiple passes to reach the desired depth.
        :param depthpercut:         Maximum depth in each pass.
        :param toolchange:
        :param toolchangez:
        :param toolchangexy:
        :param extracut:            Adds (or not) an extra cut at the end of each path overlapping the first point in
                                    path to ensure complete copper removal
        :param extracut_length:     The extra cut length
        :param startz:
        :param endz:
        :param endxy:
        :param pp_geometry_name:
        :param tool_no:
        :param is_first:            if the processed tool is the first one and if we should process the start gcode
        :return:                    None
        """
        log.debug("Executing camlib.CNCJob.generate_from_geometry_2()")

        # if solid_geometry is empty raise an exception
        if not geometry.solid_geometry:
            self.app.inform.emit(
                '[ERROR_NOTCL] %s' % _("Trying to generate a CNC Job from a Geometry object without solid_geometry.")
            )
            return 'fail'

        def bounds_rec(obj):
            if type(obj) is list:
                minx = np.Inf
                miny = np.Inf
                maxx = -np.Inf
                maxy = -np.Inf

                for k in obj:
                    if type(k) is dict:
                        for key in k:
                            minx_, miny_, maxx_, maxy_ = bounds_rec(k[key])
                            minx = min(minx, minx_)
                            miny = min(miny, miny_)
                            maxx = max(maxx, maxx_)
                            maxy = max(maxy, maxy_)
                    else:
                        minx_, miny_, maxx_, maxy_ = bounds_rec(k)
                        minx = min(minx, minx_)
                        miny = min(miny, miny_)
                        maxx = max(maxx, maxx_)
                        maxy = max(maxy, maxy_)
                return minx, miny, maxx, maxy
            else:
                # it's a Shapely object, return it's bounds
                return obj.bounds

        # Create the solid geometry which will be used to generate GCode
        temp_solid_geometry = []
        if offset != 0.0:
            offset_for_use = offset

            if offset < 0:
                a, b, c, d = bounds_rec(geometry.solid_geometry)
                # if the offset is less than half of the total length or less than half of the total width of the
                # solid geometry it's obvious we can't do the offset
                if -offset > ((c - a) / 2) or -offset > ((d - b) / 2):
                    self.app.inform.emit(
                        '[ERROR_NOTCL] %s' %
                        _("The Tool Offset value is too negative to use for the current_geometry.\n"
                          "Raise the value (in module) and try again.")
                    )
                    return 'fail'
                # hack: make offset smaller by 0.0000000001 which is insignificant difference but allow the job
                # to continue
                elif -offset == ((c - a) / 2) or -offset == ((d - b) / 2):
                    offset_for_use = offset - 0.0000000001

            for it in geometry.solid_geometry:
                # if the geometry is a closed shape then create a Polygon out of it
                if isinstance(it, LineString):
                    c = it.coords
                    if c[0] == c[-1]:
                        it = Polygon(it)
                temp_solid_geometry.append(it.buffer(offset_for_use, join_style=2))
        else:
            temp_solid_geometry = geometry.solid_geometry

        # ## Flatten the geometry. Only linear elements (no polygons) remain.
        flat_geometry = self.flatten(temp_solid_geometry, pathonly=True)
        log.debug("%d paths" % len(flat_geometry))

        default_dia = None
        if isinstance(self.app.defaults["geometry_cnctooldia"], float):
            default_dia = self.app.defaults["geometry_cnctooldia"]
        else:
            try:
                tools_string = self.app.defaults["geometry_cnctooldia"].split(",")
                tools_diameters = [eval(a) for a in tools_string if a != '']
                default_dia = tools_diameters[0] if tools_diameters else 0.0
            except Exception as e:
                self.app.log.debug("camlib.CNCJob.generate_from_geometry_2() --> %s" % str(e))

        try:
            self.tooldia = float(tooldia) if tooldia else default_dia
        except ValueError:
            self.tooldia = [float(el) for el in tooldia.split(',') if el != ''] if tooldia is not None else default_dia

        if self.tooldia is None:
            self.app.inform.emit('[ERROR] %s' % _("Failed."))
            return 'fail'

        self.z_cut = float(z_cut) if z_cut is not None else self.app.defaults["geometry_cutz"]
        self.z_move = float(z_move) if z_move is not None else self.app.defaults["geometry_travelz"]

        self.feedrate = float(feedrate) if feedrate is not None else self.app.defaults["geometry_feedrate"]
        self.z_feedrate = float(feedrate_z) if feedrate_z is not None else self.app.defaults["geometry_feedrate_z"]
        self.feedrate_rapid = float(feedrate_rapid) if feedrate_rapid is not None else \
            self.app.defaults["geometry_feedrate_rapid"]

        self.spindlespeed = int(spindlespeed) if spindlespeed != 0 and spindlespeed is not None else None
        self.spindledir = spindledir
        self.dwell = dwell
        self.dwelltime = float(dwelltime) if dwelltime is not None else self.app.defaults["geometry_dwelltime"]

        self.startz = float(startz) if startz is not None and startz != '' else self.app.defaults["geometry_startz"]

        self.z_end = float(endz) if endz is not None else self.app.defaults["geometry_endz"]

        self.xy_end = endxy if endxy != '' and endxy else self.app.defaults["geometry_endxy"]
        self.xy_end = re.sub('[()\[\]]', '', str(self.xy_end)) if self.xy_end else None

        if self.xy_end is not None and self.xy_end != '':
            self.xy_end = [float(eval(a)) for a in self.xy_end.split(",")]

        if self.xy_end and len(self.xy_end) < 2:
            self.app.inform.emit('[ERROR]  %s' % _("The End Move X,Y field in Edit -> Preferences has to be "
                                                   "in the format (x, y) but now there is only one value, not two."))
            return 'fail'

        self.z_depthpercut = float(depthpercut) if depthpercut is not None and depthpercut != 0 else abs(self.z_cut)
        self.multidepth = multidepth
        self.z_toolchange = float(toolchangez) if toolchangez is not None else self.app.defaults["geometry_toolchangez"]
        self.extracut_length = float(extracut_length) if extracut_length is not None else \
            self.app.defaults["geometry_extracut_length"]

        try:
            if toolchangexy == '':
                self.xy_toolchange = None
            else:
                self.xy_toolchange = re.sub('[()\[\]]', '', str(toolchangexy)) if self.xy_toolchange else None

                if self.xy_toolchange and self.xy_toolchange != '':
                    self.xy_toolchange = [float(eval(a)) for a in self.xy_toolchange.split(",")]

                if len(self.xy_toolchange) < 2:
                    self.app.inform.emit('[ERROR] %s' % _("The Toolchange X,Y format has to be (x, y)."))
                    return 'fail'
        except Exception as e:
            log.debug("camlib.CNCJob.generate_from_geometry_2() --> %s" % str(e))
            pass

        self.pp_geometry_name = pp_geometry_name if pp_geometry_name else 'default'
        self.f_plunge = self.app.defaults["geometry_f_plunge"]

        if self.machinist_setting == 0:
            if self.z_cut is None:
                if 'laser' not in self.pp_geometry_name:
                    self.app.inform.emit(
                        '[ERROR_NOTCL] %s' % _("Cut_Z parameter is None or zero. Most likely a bad combinations of "
                                               "other parameters.")
                    )
                    return 'fail'
                else:
                    self.z_cut = 0.0

            if self.z_cut > 0:
                self.app.inform.emit('[WARNING] %s' %
                                     _("The Cut Z parameter has positive value. "
                                       "It is the depth value to cut into material.\n"
                                       "The Cut Z parameter needs to have a negative value, assuming it is a typo "
                                       "therefore the app will convert the value to negative."
                                       "Check the resulting CNC code (Gcode etc)."))
                self.z_cut = -self.z_cut
            elif self.z_cut == 0 and 'laser' not in self.pp_geometry_name:
                self.app.inform.emit(
                    '[WARNING] %s: %s' % (_("The Cut Z parameter is zero. There will be no cut, skipping file"),
                                          geometry.options['name'])
                )
                return 'fail'

            if self.z_move is None:
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("Travel Z parameter is None or zero."))
                return 'fail'

            if self.z_move < 0:
                self.app.inform.emit('[WARNING] %s' %
                                     _("The Travel Z parameter has negative value. "
                                       "It is the height value to travel between cuts.\n"
                                       "The Z Travel parameter needs to have a positive value, assuming it is a typo "
                                       "therefore the app will convert the value to positive."
                                       "Check the resulting CNC code (Gcode etc)."))
                self.z_move = -self.z_move
            elif self.z_move == 0:
                self.app.inform.emit(
                    '[WARNING] %s: %s' % (_("The Z Travel parameter is zero. This is dangerous, skipping file"),
                                          self.options['name'])
                )
                return 'fail'

        # made sure that depth_per_cut is no more then the z_cut
        try:
            if abs(self.z_cut) < self.z_depthpercut:
                self.z_depthpercut = abs(self.z_cut)
        except TypeError:
            self.z_depthpercut = abs(self.z_cut)

        # ## Index first and last points in paths
        # What points to index.
        def get_pts(o):
            return [o.coords[0], o.coords[-1]]

        # Create the indexed storage.
        storage = FlatCAMRTreeStorage()
        storage.get_points = get_pts

        # Store the geometry
        log.debug("Indexing geometry before generating G-Code...")
        self.app.inform.emit(_("Indexing geometry before generating G-Code..."))

        for geo_shape in flat_geometry:
            if self.app.abort_flag:
                # graceful abort requested by the user
                raise grace

            if geo_shape is not None:
                storage.insert(geo_shape)

        if not append:
            self.gcode = ""

        # tell preprocessor the number of tool (for toolchange)
        self.tool = tool_no

        # this is the tool diameter, it is used as such to accommodate the preprocessor who need the tool diameter
        # given under the name 'toolC'
        # this is a fancy way of adding a class attribute (which should be added in the __init__ method) without doing
        # it there :)
        self.postdata['toolC'] = self.tooldia

        # Initial G-Code
        self.pp_geometry = self.app.preprocessors[self.pp_geometry_name]

        # the 'p' local attribute is a reference to the current preprocessor class
        p = self.pp_geometry

        self.oldx = 0.0
        self.oldy = 0.0

        start_gcode = ''
        if is_first:
            start_gcode = self.doformat(p.start_code)

        # self.gcode = self.doformat(p.start_code)
        self.gcode += self.doformat(p.feedrate_code)  # sets the feed rate

        if toolchange is False:
            # all the x and y parameters in self.doformat() are used only by some preprocessors not by all
            self.gcode += self.doformat(p.lift_code, x=self.oldx, y=self.oldy)  # Move (up) to travel height
            self.gcode += self.doformat(p.startz_code, x=self.oldx, y=self.oldy)

        if toolchange:
            # if "line_xyz" in self.pp_geometry_name:
            #     self.gcode += self.doformat(p.toolchange_code, x=self.xy_toolchange[0], y=self.xy_toolchange[1])
            # else:
            #     self.gcode += self.doformat(p.toolchange_code)
            self.gcode += self.doformat(p.toolchange_code)

            if 'laser' not in self.pp_geometry_name:
                self.gcode += self.doformat(p.spindle_code)  # Spindle start
            else:
                # for laser this will disable the laser
                self.gcode += self.doformat(p.lift_code, x=self.oldx, y=self.oldy)  # Move (up) to travel height

            if self.dwell is True:
                self.gcode += self.doformat(p.dwell_code)  # Dwell time
        else:
            if 'laser' not in self.pp_geometry_name:
                self.gcode += self.doformat(p.spindle_code)  # Spindle start

            if self.dwell is True:
                self.gcode += self.doformat(p.dwell_code)  # Dwell time

        total_travel = 0.0
        total_cut = 0.0

        # Iterate over geometry paths getting the nearest each time.
        log.debug("Starting G-Code...")
        self.app.inform.emit('%s...' % _("Starting G-Code"))

        # variables to display the percentage of work done
        geo_len = len(flat_geometry)

        old_disp_number = 0
        log.warning("Number of paths for which to generate GCode: %s" % str(geo_len))

        current_tooldia = float('%.*f' % (self.decimals, float(self.tooldia)))

        self.app.inform.emit(
            '%s: %s%s.' % (_("Starting G-Code for tool with diameter"), str(current_tooldia), str(self.units))
        )

        path_count = 0
        current_pt = (0, 0)
        pt, geo = storage.nearest(current_pt)

        # when nothing is left in the storage a StopIteration exception will be raised therefore stopping
        # the whole process including the infinite loop while True below.
        try:
            while True:
                if self.app.abort_flag:
                    # graceful abort requested by the user
                    raise grace

                path_count += 1

                # Remove before modifying, otherwise deletion will fail.
                storage.remove(geo)

                # If last point in geometry is the nearest but prefer the first one if last point == first point
                # then reverse coordinates.
                if pt != geo.coords[0] and pt == geo.coords[-1]:
                    # geo.coords = list(geo.coords)[::-1] # Shapely 2.0
                    geo = LineString(list(geo.coords)[::-1])

                # ---------- Single depth/pass --------
                if not multidepth:
                    # calculate the cut distance
                    total_cut += geo.length
                    self.gcode += self.create_gcode_single_pass(geo, current_tooldia, extracut, self.extracut_length,
                                                                tolerance, z_move=z_move, old_point=current_pt)

                # --------- Multi-pass ---------
                else:
                    # calculate the cut distance
                    # due of the number of cuts (multi depth) it has to multiplied by the number of cuts
                    nr_cuts = 0
                    depth = abs(self.z_cut)
                    while depth > 0:
                        nr_cuts += 1
                        depth -= float(self.z_depthpercut)

                    total_cut += (geo.length * nr_cuts)

                    gc, geo = self.create_gcode_multi_pass(geo, current_tooldia, extracut, self.extracut_length,
                                                           tolerance, z_move=z_move, postproc=p,
                                                           old_point=current_pt)
                    self.gcode += gc

                # calculate the travel distance
                total_travel += abs(distance(pt1=current_pt, pt2=pt))
                current_pt = geo.coords[-1]

                pt, geo = storage.nearest(current_pt)  # Next

                # update the activity counter (lower left side of the app, status bar)
                disp_number = int(np.interp(path_count, [0, geo_len], [0, 100]))
                if old_disp_number < disp_number <= 100:
                    self.app.proc_container.update_view_text(' %d%%' % disp_number)
                    old_disp_number = disp_number
        except StopIteration:  # Nothing found in storage.
            pass

        log.debug("Finishing G-Code... %s paths traced." % path_count)

        # add move to end position
        total_travel += abs(distance_euclidian(current_pt[0], current_pt[1], 0, 0))
        self.travel_distance += total_travel + total_cut
        self.routing_time += total_cut / self.feedrate

        # Finish
        self.gcode += self.doformat(p.spindle_stop_code)
        self.gcode += self.doformat(p.lift_code, x=current_pt[0], y=current_pt[1])
        self.gcode += self.doformat(p.end_code, x=0, y=0)
        self.app.inform.emit(
            '%s... %s %s.' % (_("Finished G-Code generation"), str(path_count), _("paths traced"))
        )

        return self.gcode, start_gcode

    def generate_gcode_from_solderpaste_geo(self, **kwargs):
        """
               Algorithm to generate from multitool Geometry.

               Algorithm description:
               ----------------------
               Uses RTree to find the nearest path to follow.

               :return: Gcode string
               """

        log.debug("Generate_from_solderpaste_geometry()")

        # ## Index first and last points in paths
        # What points to index.
        def get_pts(o):
            return [o.coords[0], o.coords[-1]]

        self.gcode = ""

        if not kwargs:
            log.debug("camlib.generate_from_solderpaste_geo() --> No tool in the solderpaste geometry.")
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("There is no tool data in the SolderPaste geometry."))

        # this is the tool diameter, it is used as such to accommodate the preprocessor who need the tool diameter
        # given under the name 'toolC'

        self.postdata['z_start'] = kwargs['data']['tools_solderpaste_z_start']
        self.postdata['z_dispense'] = kwargs['data']['tools_solderpaste_z_dispense']
        self.postdata['z_stop'] = kwargs['data']['tools_solderpaste_z_stop']
        self.postdata['z_travel'] = kwargs['data']['tools_solderpaste_z_travel']
        self.postdata['z_toolchange'] = kwargs['data']['tools_solderpaste_z_toolchange']
        self.postdata['xy_toolchange'] = kwargs['data']['tools_solderpaste_xy_toolchange']
        self.postdata['frxy'] = kwargs['data']['tools_solderpaste_frxy']
        self.postdata['frz'] = kwargs['data']['tools_solderpaste_frz']
        self.postdata['frz_dispense'] = kwargs['data']['tools_solderpaste_frz_dispense']
        self.postdata['speedfwd'] = kwargs['data']['tools_solderpaste_speedfwd']
        self.postdata['dwellfwd'] = kwargs['data']['tools_solderpaste_dwellfwd']
        self.postdata['speedrev'] = kwargs['data']['tools_solderpaste_speedrev']
        self.postdata['dwellrev'] = kwargs['data']['tools_solderpaste_dwellrev']
        self.postdata['pp_solderpaste_name'] = kwargs['data']['tools_solderpaste_pp']

        self.postdata['toolC'] = kwargs['tooldia']

        self.pp_solderpaste_name = kwargs['data']['tools_solderpaste_pp'] if kwargs['data']['tools_solderpaste_pp'] \
            else self.app.defaults['tools_solderpaste_pp']
        p = self.app.preprocessors[self.pp_solderpaste_name]

        # ## Flatten the geometry. Only linear elements (no polygons) remain.
        flat_geometry = self.flatten(kwargs['solid_geometry'], pathonly=True)
        log.debug("%d paths" % len(flat_geometry))

        # Create the indexed storage.
        storage = FlatCAMRTreeStorage()
        storage.get_points = get_pts

        # Store the geometry
        log.debug("Indexing geometry before generating G-Code...")
        for geo_shape in flat_geometry:
            if self.app.abort_flag:
                # graceful abort requested by the user
                raise grace

            if geo_shape is not None:
                storage.insert(geo_shape)

        # Initial G-Code
        self.gcode = self.doformat(p.start_code)
        self.gcode += self.doformat(p.spindle_off_code)
        self.gcode += self.doformat(p.toolchange_code)

        # ## Iterate over geometry paths getting the nearest each time.
        log.debug("Starting SolderPaste G-Code...")
        path_count = 0
        current_pt = (0, 0)

        # variables to display the percentage of work done
        geo_len = len(flat_geometry)
        old_disp_number = 0

        pt, geo = storage.nearest(current_pt)

        try:
            while True:
                if self.app.abort_flag:
                    # graceful abort requested by the user
                    raise grace

                path_count += 1

                # Remove before modifying, otherwise deletion will fail.
                storage.remove(geo)

                # If last point in geometry is the nearest but prefer the first one if last point == first point
                # then reverse coordinates.
                if pt != geo.coords[0] and pt == geo.coords[-1]:
                    # geo.coords = list(geo.coords)[::-1] # Shapely 2.0
                    geo = LineString(list(geo.coords)[::-1])

                self.gcode += self.create_soldepaste_gcode(geo, p=p, old_point=current_pt)
                current_pt = geo.coords[-1]
                pt, geo = storage.nearest(current_pt)  # Next

                disp_number = int(np.interp(path_count, [0, geo_len], [0, 100]))
                if old_disp_number < disp_number <= 100:
                    self.app.proc_container.update_view_text(' %d%%' % disp_number)
                    old_disp_number = disp_number
        except StopIteration:  # Nothing found in storage.
            pass

        log.debug("Finishing SolderPste G-Code... %s paths traced." % path_count)
        self.app.inform.emit(
            '%s... %s %s.' % (_("Finished SolderPaste G-Code generation"), str(path_count), _("paths traced"))
        )

        # Finish
        self.gcode += self.doformat(p.lift_code)
        self.gcode += self.doformat(p.end_code)

        return self.gcode

    def create_soldepaste_gcode(self, geometry, p, old_point=(0, 0)):
        gcode = ''
        path = geometry.coords

        self.coordinates_type = self.app.defaults["cncjob_coords_type"]
        if self.coordinates_type == "G90":
            # For Absolute coordinates type G90
            first_x = path[0][0]
            first_y = path[0][1]
        else:
            # For Incremental coordinates type G91
            first_x = path[0][0] - old_point[0]
            first_y = path[0][1] - old_point[1]

        if type(geometry) == LineString or type(geometry) == LinearRing:
            # Move fast to 1st point
            gcode += self.doformat(p.rapid_code, x=first_x, y=first_y)  # Move to first point

            # Move down to cutting depth
            gcode += self.doformat(p.z_feedrate_code)
            gcode += self.doformat(p.down_z_start_code)
            gcode += self.doformat(p.spindle_fwd_code)  # Start dispensing
            gcode += self.doformat(p.dwell_fwd_code)
            gcode += self.doformat(p.feedrate_z_dispense_code)
            gcode += self.doformat(p.lift_z_dispense_code)
            gcode += self.doformat(p.feedrate_xy_code)

            # Cutting...
            prev_x = first_x
            prev_y = first_y
            for pt in path[1:]:
                if self.coordinates_type == "G90":
                    # For Absolute coordinates type G90
                    next_x = pt[0]
                    next_y = pt[1]
                else:
                    # For Incremental coordinates type G91
                    next_x = pt[0] - prev_x
                    next_y = pt[1] - prev_y
                gcode += self.doformat(p.linear_code, x=next_x, y=next_y)  # Linear motion to point
                prev_x = next_x
                prev_y = next_y

            # Up to travelling height.
            gcode += self.doformat(p.spindle_off_code)  # Stop dispensing
            gcode += self.doformat(p.spindle_rev_code)
            gcode += self.doformat(p.down_z_stop_code)
            gcode += self.doformat(p.spindle_off_code)
            gcode += self.doformat(p.dwell_rev_code)
            gcode += self.doformat(p.z_feedrate_code)
            gcode += self.doformat(p.lift_code)
        elif type(geometry) == Point:
            gcode += self.doformat(p.linear_code, x=first_x, y=first_y)  # Move to first point

            gcode += self.doformat(p.feedrate_z_dispense_code)
            gcode += self.doformat(p.down_z_start_code)
            gcode += self.doformat(p.spindle_fwd_code)  # Start dispensing
            gcode += self.doformat(p.dwell_fwd_code)
            gcode += self.doformat(p.lift_z_dispense_code)

            gcode += self.doformat(p.spindle_off_code)  # Stop dispensing
            gcode += self.doformat(p.spindle_rev_code)
            gcode += self.doformat(p.spindle_off_code)
            gcode += self.doformat(p.down_z_stop_code)
            gcode += self.doformat(p.dwell_rev_code)
            gcode += self.doformat(p.z_feedrate_code)
            gcode += self.doformat(p.lift_code)
        return gcode

    def create_gcode_single_pass(self, geometry, cdia, extracut, extracut_length, tolerance, z_move, old_point=(0, 0)):
        """
        # G-code. Note: self.linear2gcode() and self.point2gcode() will lower and raise the tool every time.

        :param geometry:            A Shapely Geometry (LineString or LinearRing) which is the path to be cut
        :type geometry:             LineString, LinearRing
        :param cdia:                Tool diameter
        :type cdia:                 float
        :param extracut:            Will add an extra cut over the point where start of the cut is met with the end cut
        :type extracut:             bool
        :param extracut_length:     The length of the extra cut: half before the meeting point, half after
        :type extracut_length:      float
        :param tolerance:           Tolerance used to simplify the paths (making them mre rough)
        :type tolerance:            float
        :param z_move:              Travel Z
        :type z_move:               float
        :param old_point:           Previous point
        :type old_point:            tuple
        :return:                    Gcode
        :rtype:                     str
        """
        # p = postproc

        if type(geometry) == LineString or type(geometry) == LinearRing:
            if extracut is False or not geometry.is_ring:
                gcode_single_pass = self.linear2gcode(geometry, cdia, z_move=z_move, tolerance=tolerance,
                                                      old_point=old_point)
            else:
                gcode_single_pass = self.linear2gcode_extra(geometry, cdia, extracut_length, tolerance=tolerance,
                                                            z_move=z_move, old_point=old_point)

        elif type(geometry) == Point:
            gcode_single_pass = self.point2gcode(geometry, cdia, z_move=z_move, old_point=old_point)
        else:
            log.warning("G-code generation not implemented for %s" % (str(type(geometry))))
            return

        return gcode_single_pass

    def create_gcode_multi_pass(self, geometry, cdia, extracut, extracut_length, tolerance, postproc, z_move,
                                old_point=(0, 0)):
        """

        :param geometry:            A Shapely Geometry (LineString or LinearRing) which is the path to be cut
        :type geometry:             LineString, LinearRing
        :param cdia:                Tool diameter
        :type cdia:                 float
        :param extracut:            Will add an extra cut over the point where start of the cut is met with the end cut
        :type extracut:             bool
        :param extracut_length:     The length of the extra cut: half before the meeting point, half after
        :type extracut_length:      float
        :param tolerance:           Tolerance used to simplify the paths (making them mre rough)
        :type tolerance:            float
        :param postproc:            Preprocessor class
        :type postproc:             class
        :param z_move:              Travel Z
        :type z_move:               float
        :param old_point:           Previous point
        :type old_point:            tuple
        :return:                    Gcode
        :rtype:                     str
        """
        p = postproc

        gcode_multi_pass = ''

        if isinstance(self.z_cut, Decimal):
            z_cut = self.z_cut
        else:
            z_cut = Decimal(self.z_cut).quantize(Decimal('0.000000001'))

        if self.z_depthpercut is None:
            self.z_depthpercut = z_cut
        elif not isinstance(self.z_depthpercut, Decimal):
            self.z_depthpercut = Decimal(self.z_depthpercut).quantize(Decimal('0.000000001'))

        depth = 0
        reverse = False
        while depth > z_cut:

            # Increase depth. Limit to z_cut.
            depth -= self.z_depthpercut
            if depth < z_cut:
                depth = z_cut

            # Cut at specific depth and do not lift the tool.
            # Note: linear2gcode() will use G00 to move to the first point in the path, but it should be already
            # at the first point if the tool is down (in the material).  So, an extra G00 should show up but
            # is inconsequential.
            if type(geometry) == LineString or type(geometry) == LinearRing:
                if extracut is False or not geometry.is_ring:
                    gcode_multi_pass += self.linear2gcode(geometry, cdia, tolerance=tolerance, z_cut=depth, up=False,
                                                          z_move=z_move, old_point=old_point)
                else:
                    gcode_multi_pass += self.linear2gcode_extra(geometry, cdia, extracut_length, tolerance=tolerance,
                                                                z_move=z_move, z_cut=depth, up=False,
                                                                old_point=old_point)

            # Ignore multi-pass for points.
            elif type(geometry) == Point:
                gcode_multi_pass += self.point2gcode(geometry, cdia, z_move=z_move, old_point=old_point)
                break  # Ignoring ...
            else:
                log.warning("G-code generation not implemented for %s" % (str(type(geometry))))

            # Reverse coordinates if not a loop so we can continue cutting without returning to the beginning.
            if type(geometry) == LineString:
                geometry = LineString(list(geometry.coords)[::-1])
                reverse = True

        # If geometry is reversed, revert.
        if reverse:
            if type(geometry) == LineString:
                geometry = LineString(list(geometry.coords)[::-1])

        # Lift the tool
        gcode_multi_pass += self.doformat(p.lift_code, x=old_point[0], y=old_point[1])
        return gcode_multi_pass, geometry

    def codes_split(self, gline):
        """
        Parses a line of G-Code such as "G01 X1234 Y987" into
        a dictionary: {'G': 1.0, 'X': 1234.0, 'Y': 987.0}

        :param gline:       G-Code line string
        :type gline:        str
        :return:            Dictionary with parsed line.
        :rtype:             dict
        """

        command = {}

        if 'Roland' in self.pp_excellon_name or 'Roland' in self.pp_geometry_name:
            match_z = re.search(r"^Z(\s*-?\d+\.\d+?),(\s*\s*-?\d+\.\d+?),(\s*\s*-?\d+\.\d+?)*;$", gline)
            if match_z:
                command['G'] = 0
                command['X'] = float(match_z.group(1).replace(" ", "")) * 0.025
                command['Y'] = float(match_z.group(2).replace(" ", "")) * 0.025
                command['Z'] = float(match_z.group(3).replace(" ", "")) * 0.025

        elif 'hpgl' in self.pp_excellon_name or 'hpgl' in self.pp_geometry_name:
            match_pa = re.search(r"^PA(\s*-?\d+\.\d+?),(\s*\s*-?\d+\.\d+?)*;$", gline)
            if match_pa:
                command['G'] = 0
                command['X'] = float(match_pa.group(1).replace(" ", "")) / 40
                command['Y'] = float(match_pa.group(2).replace(" ", "")) / 40
            match_pen = re.search(r"^(P[U|D])", gline)
            if match_pen:
                if match_pen.group(1) == 'PU':
                    # the value does not matter, only that it is positive so the gcode_parse() know it is > 0,
                    # therefore the move is of kind T (travel)
                    command['Z'] = 1
                else:
                    command['Z'] = 0

        elif 'laser' in self.pp_excellon_name.lower() or 'laser' in self.pp_geometry_name.lower() or \
                (self.pp_solderpaste_name is not None and 'paste' in self.pp_solderpaste_name.lower()):
            match_lsr = re.search(r"X([\+-]?\d+.[\+-]?\d+)\s*Y([\+-]?\d+.[\+-]?\d+)", gline)
            if match_lsr:
                command['X'] = float(match_lsr.group(1).replace(" ", ""))
                command['Y'] = float(match_lsr.group(2).replace(" ", ""))

            match_lsr_pos = re.search(r"^(M0?[3-5])", gline)
            if match_lsr_pos:
                if 'M05' in match_lsr_pos.group(1) or 'M5' in match_lsr_pos.group(1):
                    # the value does not matter, only that it is positive so the gcode_parse() know it is > 0,
                    # therefore the move is of kind T (travel)
                    command['Z'] = 1
                else:
                    command['Z'] = 0

            match_lsr_pos_2 = re.search(r"^(M10[6|7])", gline)
            if match_lsr_pos_2:
                if 'M107' in match_lsr_pos_2.group(1):
                    command['Z'] = 1
                else:
                    command['Z'] = 0
        elif self.pp_solderpaste_name is not None:
            if 'Paste' in self.pp_solderpaste_name:
                match_paste = re.search(r"X([\+-]?\d+.[\+-]?\d+)\s*Y([\+-]?\d+.[\+-]?\d+)", gline)
                if match_paste:
                    command['X'] = float(match_paste.group(1).replace(" ", ""))
                    command['Y'] = float(match_paste.group(2).replace(" ", ""))
        else:
            match = re.search(r'^\s*([A-Z])\s*([\+\-\.\d\s]+)', gline)
            while match:
                command[match.group(1)] = float(match.group(2).replace(" ", ""))
                gline = gline[match.end():]
                match = re.search(r'^\s*([A-Z])\s*([\+\-\.\d\s]+)', gline)
        return command

    def gcode_parse(self, force_parsing=None):
        """
        G-Code parser (from self.gcode). Generates dictionary with
        single-segment LineString's and "kind" indicating cut or travel,
        fast or feedrate speed.

        Will return a list of dict in the format:
        {
            "geom": LineString(path),
            "kind": kind
        }
        where kind can be either ["C", "F"]  # T=travel, C=cut, F=fast, S=slow

        :param force_parsing:
        :type force_parsing:
        :return:
        :rtype:                 dict
        """

        kind = ["C", "F"]  # T=travel, C=cut, F=fast, S=slow

        # Results go here
        geometry = []

        # Last known instruction
        current = {'X': 0.0, 'Y': 0.0, 'Z': 0.0, 'G': 0}

        # Current path: temporary storage until tool is
        # lifted or lowered.
        if self.toolchange_xy_type == "excellon":
            if self.app.defaults["tools_drill_toolchangexy"] == '' or \
                    self.app.defaults["tools_drill_toolchangexy"] is None:
                pos_xy = (0, 0)
            else:
                pos_xy = self.app.defaults["tools_drill_toolchangexy"]
                try:
                    pos_xy = [float(eval(a)) for a in pos_xy.split(",")]
                except Exception:
                    if len(pos_xy) != 2:
                        pos_xy = (0, 0)
        else:
            if self.app.defaults["geometry_toolchangexy"] == '' or self.app.defaults["geometry_toolchangexy"] is None:
                pos_xy = (0, 0)
            else:
                pos_xy = self.app.defaults["geometry_toolchangexy"]
                try:
                    pos_xy = [float(eval(a)) for a in pos_xy.split(",")]
                except Exception:
                    if len(pos_xy) != 2:
                        pos_xy = (0, 0)

        path = [pos_xy]
        # path = [(0, 0)]

        gcode_lines_list = self.gcode.splitlines()
        self.app.inform.emit('%s: %d' % (_("Parsing GCode file. Number of lines"), len(gcode_lines_list)))

        # Process every instruction
        for line in gcode_lines_list:
            if force_parsing is False or force_parsing is None:
                if '%MO' in line or '%' in line or 'MOIN' in line or 'MOMM' in line:
                    return "fail"

            gobj = self.codes_split(line)

            # ## Units
            if 'G' in gobj and (gobj['G'] == 20.0 or gobj['G'] == 21.0):
                self.units = {20.0: "IN", 21.0: "MM"}[gobj['G']]
                continue

            # TODO take into consideration the tools and update the travel line thickness
            if 'T' in gobj:
                pass

            # ## Changing height
            if 'Z' in gobj:
                if 'Roland' in self.pp_excellon_name or 'Roland' in self.pp_geometry_name:
                    pass
                elif 'hpgl' in self.pp_excellon_name or 'hpgl' in self.pp_geometry_name:
                    pass
                elif 'laser' in self.pp_excellon_name or 'laser' in self.pp_geometry_name:
                    pass
                elif ('X' in gobj or 'Y' in gobj) and gobj['Z'] != current['Z']:
                    if self.pp_geometry_name == 'line_xyz' or self.pp_excellon_name == 'line_xyz':
                        pass
                    else:
                        log.warning("Non-orthogonal motion: From %s" % str(current))
                        log.warning("  To: %s" % str(gobj))

                current['Z'] = gobj['Z']
                # Store the path into geometry and reset path
                if len(path) > 1:
                    geometry.append({"geom": LineString(path),
                                     "kind": kind})
                    path = [path[-1]]  # Start with the last point of last path.

                # create the geometry for the holes created when drilling Excellon drills
                if self.origin_kind == 'excellon':
                    if current['Z'] < 0:
                        current_drill_point_coords = (
                            float('%.*f' % (self.decimals, current['X'])),
                            float('%.*f' % (self.decimals, current['Y']))
                        )

                        # find the drill diameter knowing the drill coordinates
                        break_loop = False
                        for tool, tool_dict in self.exc_tools.items():
                            if 'drills' in tool_dict:
                                for drill_pt in tool_dict['drills']:
                                    point_in_dict_coords = (
                                        float('%.*f' % (self.decimals, drill_pt.x)),
                                        float('%.*f' % (self.decimals, drill_pt.y))
                                    )
                                    if point_in_dict_coords == current_drill_point_coords:
                                        dia = self.exc_tools[tool]['tooldia']
                                        kind = ['C', 'F']
                                        geometry.append(
                                            {
                                                "geom": Point(current_drill_point_coords).buffer(dia / 2.0).exterior,
                                                "kind": kind
                                            }
                                        )
                                        break_loop = True
                                        break
                                if break_loop:
                                    break

            if 'G' in gobj:
                current['G'] = int(gobj['G'])

            if 'X' in gobj or 'Y' in gobj:
                if 'X' in gobj:
                    x = gobj['X']
                    # current['X'] = x
                else:
                    x = current['X']

                if 'Y' in gobj:
                    y = gobj['Y']
                else:
                    y = current['Y']

                kind = ["C", "F"]  # T=travel, C=cut, F=fast, S=slow

                if current['Z'] > 0:
                    kind[0] = 'T'
                if current['G'] > 0:
                    kind[1] = 'S'

                if current['G'] in [0, 1]:  # line
                    path.append((x, y))

                arcdir = [None, None, "cw", "ccw"]
                if current['G'] in [2, 3]:  # arc
                    center = [gobj['I'] + current['X'], gobj['J'] + current['Y']]
                    radius = np.sqrt(gobj['I'] ** 2 + gobj['J'] ** 2)
                    start = np.arctan2(-gobj['J'], -gobj['I'])
                    stop = np.arctan2(-center[1] + y, -center[0] + x)
                    path += arc(center, radius, start, stop, arcdir[current['G']], int(self.steps_per_circle))

                current['X'] = x
                current['Y'] = y

            # Update current instruction
            for code in gobj:
                current[code] = gobj[code]

        self.app.inform.emit('%s...' % _("Creating Geometry from the parsed GCode file. "))
        # There might not be a change in height at the
        # end, therefore, see here too if there is
        # a final path.
        if len(path) > 1:
            geometry.append(
                {
                    "geom": LineString(path),
                    "kind": kind
                }
            )

        self.gcode_parsed = geometry
        return geometry

    def excellon_tool_gcode_parse(self, dia, gcode, start_pt=(0, 0), force_parsing=None):
        """
        G-Code parser (from self.exc_cnc_tools['tooldia']['gcode']). Generates dictionary with
        single-segment LineString's and "kind" indicating cut or travel,
        fast or feedrate speed.

        Will return the Geometry as a list of dict in the format:
        {
            "geom": LineString(path),
            "kind": kind
        }
        where kind can be either ["C", "F"]  # T=travel, C=cut, F=fast, S=slow

        :param dia:             the dia is a tool diameter which is the key in self.exc_cnc_tools dict
        :type dia:              float
        :param gcode:           Gcode to parse
        :type gcode:            str
        :param start_pt:        the point coordinates from where to start the parsing
        :type start_pt:         tuple
        :param force_parsing:
        :type force_parsing:    bool
        :return:                Geometry as a list of dictionaries
        :rtype:                 list
        """

        kind = ["C", "F"]  # T=travel, C=cut, F=fast, S=slow

        # Results go here
        geometry = []

        # Last known instruction
        current = {'X': 0.0, 'Y': 0.0, 'Z': 0.0, 'G': 0}

        # Current path: temporary storage until tool is
        # lifted or lowered.
        pos_xy = start_pt

        path = [pos_xy]
        # path = [(0, 0)]

        gcode_lines_list = gcode.splitlines()
        self.app.inform.emit(
            '%s: %s. %s: %d' % (_("Parsing GCode file for tool diameter"),
                                str(dia), _("Number of lines"),
                                len(gcode_lines_list))
        )

        # Process every instruction
        for line in gcode_lines_list:
            if force_parsing is False or force_parsing is None:
                if '%MO' in line or '%' in line or 'MOIN' in line or 'MOMM' in line:
                    return "fail"

            gobj = self.codes_split(line)

            # ## Units
            if 'G' in gobj and (gobj['G'] == 20.0 or gobj['G'] == 21.0):
                self.units = {20.0: "IN", 21.0: "MM"}[gobj['G']]
                continue

            # TODO take into consideration the tools and update the travel line thickness
            if 'T' in gobj:
                pass

            # ## Changing height
            if 'Z' in gobj:
                if 'Roland' in self.pp_excellon_name or 'Roland' in self.pp_geometry_name:
                    pass
                elif 'hpgl' in self.pp_excellon_name or 'hpgl' in self.pp_geometry_name:
                    pass
                elif 'laser' in self.pp_excellon_name or 'laser' in self.pp_geometry_name:
                    pass
                elif ('X' in gobj or 'Y' in gobj) and gobj['Z'] != current['Z']:
                    if self.pp_geometry_name == 'line_xyz' or self.pp_excellon_name == 'line_xyz':
                        pass
                    else:
                        log.warning("Non-orthogonal motion: From %s" % str(current))
                        log.warning("  To: %s" % str(gobj))

                current['Z'] = gobj['Z']
                # Store the path into geometry and reset path
                if len(path) > 1:
                    geometry.append({"geom": LineString(path),
                                     "kind": kind})
                    path = [path[-1]]  # Start with the last point of last path.

                # create the geometry for the holes created when drilling Excellon drills
                if current['Z'] < 0:
                    current_drill_point_coords = (
                        float('%.*f' % (self.decimals, current['X'])),
                        float('%.*f' % (self.decimals, current['Y']))
                    )

                    kind = ['C', 'F']
                    geometry.append(
                        {
                            "geom": Point(current_drill_point_coords).buffer(dia/2.0).exterior,
                            "kind": kind
                        }
                    )

            if 'G' in gobj:
                current['G'] = int(gobj['G'])

            if 'X' in gobj or 'Y' in gobj:
                x = gobj['X'] if 'X' in gobj else current['X']
                y = gobj['Y'] if 'Y' in gobj else current['Y']

                kind = ["C", "F"]  # T=travel, C=cut, F=fast, S=slow

                if current['Z'] > 0:
                    kind[0] = 'T'
                if current['G'] > 0:
                    kind[1] = 'S'
                if current['G'] in [0, 1]:  # line
                    path.append((x, y))

                arcdir = [None, None, "cw", "ccw"]
                if current['G'] in [2, 3]:  # arc
                    center = [gobj['I'] + current['X'], gobj['J'] + current['Y']]
                    radius = np.sqrt(gobj['I'] ** 2 + gobj['J'] ** 2)
                    start = np.arctan2(-gobj['J'], -gobj['I'])
                    stop = np.arctan2(-center[1] + y, -center[0] + x)
                    path += arc(center, radius, start, stop, arcdir[current['G']], int(self.steps_per_circle))

                current['X'] = x
                current['Y'] = y

            # Update current instruction
            for code in gobj:
                current[code] = gobj[code]

        self.app.inform.emit('%s: %s' % (_("Creating Geometry from the parsed GCode file for tool diameter"), str(dia)))
        # There might not be a change in height at the end, therefore, see here too if there is a final path.
        if len(path) > 1:
            geometry.append(
                {
                    "geom": LineString(path),
                    "kind": kind
                }
            )
        return geometry

    # def plot(self, tooldia=None, dpi=75, margin=0.1,
    #          color={"T": ["#F0E24D", "#B5AB3A"], "C": ["#5E6CFF", "#4650BD"]},
    #          alpha={"T": 0.3, "C": 1.0}):
    #     """
    #     Creates a Matplotlib figure with a plot of the
    #     G-code job.
    #     """
    #     if tooldia is None:
    #         tooldia = self.tooldia
    #
    #     fig = Figure(dpi=dpi)
    #     ax = fig.add_subplot(111)
    #     ax.set_aspect(1)
    #     xmin, ymin, xmax, ymax = self.input_geometry_bounds
    #     ax.set_xlim(xmin-margin, xmax+margin)
    #     ax.set_ylim(ymin-margin, ymax+margin)
    #
    #     if tooldia == 0:
    #         for geo in self.gcode_parsed:
    #             linespec = '--'
    #             linecolor = color[geo['kind'][0]][1]
    #             if geo['kind'][0] == 'C':
    #                 linespec = 'k-'
    #             x, y = geo['geom'].coords.xy
    #             ax.plot(x, y, linespec, color=linecolor)
    #     else:
    #         for geo in self.gcode_parsed:
    #             poly = geo['geom'].buffer(tooldia/2.0)
    #             patch = PolygonPatch(poly, facecolor=color[geo['kind'][0]][0],
    #                                  edgecolor=color[geo['kind'][0]][1],
    #                                  alpha=alpha[geo['kind'][0]], zorder=2)
    #             ax.add_patch(patch)
    #
    #     return fig

    def plot2(self, tooldia=None, dpi=75, margin=0.1, gcode_parsed=None,
              color=None, alpha={"T": 0.3, "C": 1.0}, tool_tolerance=0.0005, obj=None, visible=False, kind='all'):
        """
        Plots the G-code job onto the given axes.

        :param tooldia:             Tool diameter.
        :type tooldia:              float
        :param dpi:                 Not used!
        :type dpi:                  float
        :param margin:              Not used!
        :type margin:               float
        :param gcode_parsed:        Parsed Gcode
        :type gcode_parsed:         str
        :param color:               Color specification.
        :type color:                str
        :param alpha:               Transparency specification.
        :type alpha:                dict
        :param tool_tolerance:      Tolerance when drawing the toolshape.
        :type tool_tolerance:       float
        :param obj:                 The object for whih to plot
        :type obj:                  class
        :param visible:             Visibility status
        :type visible:              bool
        :param kind:                Can be: "travel", "cut", "all"
        :type kind:                 str
        :return:                    None
        :rtype:
        """
        # units = self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().upper()

        if color is None:
            color = {
                "T": [self.app.defaults["cncjob_travel_fill"], self.app.defaults["cncjob_travel_line"]],
                "C": [self.app.defaults["cncjob_plot_fill"], self.app.defaults["cncjob_plot_line"]]
            }

        gcode_parsed = gcode_parsed if gcode_parsed else self.gcode_parsed

        if tooldia is None:
            tooldia = self.tooldia

        # this should be unlikely unless when upstream the tooldia is a tuple made by one dia and a comma like (2.4,)
        if isinstance(tooldia, list):
            tooldia = tooldia[0] if tooldia[0] is not None else self.tooldia

        if tooldia == 0:
            for geo in gcode_parsed:
                if kind == 'all':
                    obj.add_shape(shape=geo['geom'], color=color[geo['kind'][0]][1], visible=visible)
                elif kind == 'travel':
                    if geo['kind'][0] == 'T':
                        obj.add_shape(shape=geo['geom'], color=color['T'][1], visible=visible)
                elif kind == 'cut':
                    if geo['kind'][0] == 'C':
                        obj.add_shape(shape=geo['geom'], color=color['C'][1], visible=visible)
        else:
            path_num = 0

            self.coordinates_type = self.app.defaults["cncjob_coords_type"]
            if self.coordinates_type == "G90":
                # For Absolute coordinates type G90
                for geo in gcode_parsed:
                    if geo['kind'][0] == 'T':
                        start_position = geo['geom'].coords[0]

                        if tooldia not in obj.annotations_dict:
                            obj.annotations_dict[tooldia] = {
                                'pos': [],
                                'text': []
                            }
                        if start_position not in obj.annotations_dict[tooldia]['pos']:
                            path_num += 1
                            obj.annotations_dict[tooldia]['pos'].append(start_position)
                            obj.annotations_dict[tooldia]['text'].append(str(path_num))

                        end_position = geo['geom'].coords[-1]

                        if tooldia not in obj.annotations_dict:
                            obj.annotations_dict[tooldia] = {
                                'pos': [],
                                'text': []
                            }
                        if end_position not in obj.annotations_dict[tooldia]['pos']:
                            path_num += 1
                            obj.annotations_dict[tooldia]['pos'].append(end_position)
                            obj.annotations_dict[tooldia]['text'].append(str(path_num))

                    # plot the geometry of Excellon objects
                    if self.origin_kind == 'excellon':
                        try:
                            # if the geos are travel lines
                            if geo['kind'][0] == 'T':
                                poly = geo['geom'].buffer(distance=(tooldia / 1.99999999),
                                                          resolution=self.steps_per_circle)
                            else:
                                poly = Polygon(geo['geom'])

                            poly = poly.simplify(tool_tolerance)
                        except Exception:
                            # deal here with unexpected plot errors due of LineStrings not valid
                            continue
                    else:
                        # plot the geometry of any objects other than Excellon
                        poly = geo['geom'].buffer(distance=(tooldia / 1.99999999), resolution=self.steps_per_circle)
                        poly = poly.simplify(tool_tolerance)

                    if kind == 'all':
                        obj.add_shape(shape=poly, color=color[geo['kind'][0]][1], face_color=color[geo['kind'][0]][0],
                                      visible=visible, layer=1 if geo['kind'][0] == 'C' else 2)
                    elif kind == 'travel':
                        if geo['kind'][0] == 'T':
                            obj.add_shape(shape=poly, color=color['T'][1], face_color=color['T'][0],
                                          visible=visible, layer=2)
                    elif kind == 'cut':
                        if geo['kind'][0] == 'C':
                            obj.add_shape(shape=poly, color=color['C'][1], face_color=color['C'][0],
                                          visible=visible, layer=1)
            else:
                self.app.inform.emit('[ERROR_NOTCL] %s...' % _('G91 coordinates not implemented'))
                return 'fail'

    def plot_annotations(self, obj, visible=True):
        """
        Plot annotations.

        :param obj:         FlatCAM CNCJob object for which to plot the annotations
        :type obj:
        :param visible:     annotations visibility
        :type visible:      bool
        :return:            Nothing
        :rtype:
        """

        if not obj.annotations_dict:
            return

        if visible is True:
            if self.app.is_legacy is False:
                obj.annotation.clear(update=True)
            obj.text_col.visible = True
        else:
            obj.text_col.visible = False
            return

        text = []
        pos = []
        for tooldia in obj.annotations_dict:
            pos += obj.annotations_dict[tooldia]['pos']
            text += obj.annotations_dict[tooldia]['text']

        if not text or not pos:
            return

        try:
            if self.app.defaults['global_theme'] == 'white':
                obj.annotation.set(text=text, pos=pos, visible=obj.options['plot'],
                                   font_size=self.app.defaults["cncjob_annotation_fontsize"],
                                   color=self.app.defaults["cncjob_annotation_fontcolor"])
            else:
                # invert the color
                old_color = self.app.defaults["cncjob_annotation_fontcolor"].lower()
                new_color = ''
                code = {}
                l1 = "#;0123456789abcdef"
                l2 = "#;fedcba9876543210"
                for i in range(len(l1)):
                    code[l1[i]] = l2[i]

                for x in range(len(old_color)):
                    new_color += code[old_color[x]]

                obj.annotation.set(text=text, pos=pos, visible=obj.options['plot'],
                                   font_size=self.app.defaults["cncjob_annotation_fontsize"],
                                   color=new_color)
        except Exception as e:
            log.debug("CNCJob.plot2() --> annotations --> %s" % str(e))
            if self.app.is_legacy is False:
                obj.annotation.clear(update=True)

        obj.annotation.redraw()

    def create_geometry(self):
        """
        It is used by the Excellon objects. Will create the solid_geometry which will be an attribute of the
        Excellon object class.

        :return:    List of Shapely geometry elements
        :rtype:     list
        """

        # This takes forever. Too much data?
        # self.app.inform.emit('%s: %s' % (_("Unifying Geometry from parsed Geometry segments"),
        #                                  str(len(self.gcode_parsed))))
        # self.solid_geometry = unary_union([geo['geom'] for geo in self.gcode_parsed])

        # This is much faster but not so nice to look at as you can see different segments of the geometry
        self.solid_geometry = [geo['geom'] for geo in self.gcode_parsed]

        return self.solid_geometry

    def segment(self, coords):
        """
        Break long linear lines to make it more auto level friendly.
        Code snippet added by Lei Zheng in a rejected pull request on FlatCAM https://bitbucket.org/realthunder/

        :param coords:  List of coordinates tuples
        :type coords:   list
        :return:        A path; list with the multiple coordinates breaking a line.
        :rtype:         list
        """

        if len(coords) < 2 or self.segx <= 0 and self.segy <= 0:
            return list(coords)

        path = [coords[0]]

        # break the line in either x or y dimension only
        def linebreak_single(line, dim, dmax):
            if dmax <= 0:
                return None

            if line[1][dim] > line[0][dim]:
                sign = 1.0
                d = line[1][dim] - line[0][dim]
            else:
                sign = -1.0
                d = line[0][dim] - line[1][dim]
            if d > dmax:
                # make sure we don't make any new lines too short
                if d > dmax * 2:
                    dd = dmax
                else:
                    dd = d / 2
                other = dim ^ 1
                return (line[0][dim] + dd * sign, line[0][other] + \
                        dd * (line[1][other] - line[0][other]) / d)
            return None

        # recursively breaks down a given line until it is within the
        # required step size
        def linebreak(line):
            pt_new = linebreak_single(line, 0, self.segx)
            if pt_new is None:
                pt_new2 = linebreak_single(line, 1, self.segy)
            else:
                pt_new2 = linebreak_single((line[0], pt_new), 1, self.segy)
            if pt_new2 is not None:
                pt_new = pt_new2[::-1]

            if pt_new is None:
                path.append(line[1])
            else:
                path.append(pt_new)
                linebreak((pt_new, line[1]))

        for pt in coords[1:]:
            linebreak((path[-1], pt))

        return path

    def linear2gcode(self, linear, dia, tolerance=0, down=True, up=True, z_cut=None, z_move=None, zdownrate=None,
                     feedrate=None, feedrate_z=None, feedrate_rapid=None, cont=False, old_point=(0, 0)):
        """

        Generates G-code to cut along the linear feature.

        :param linear:          The path to cut along.
        :type:                  Shapely.LinearRing or Shapely.Linear String
        :param dia:             The tool diameter that is going on the path
        :type dia:              float
        :param tolerance:       All points in the simplified object will be within the
                                tolerance distance of the original geometry.
        :type tolerance:        float
        :param down:
        :param up:
        :param z_cut:
        :param z_move:
        :param zdownrate:
        :param feedrate:        speed for cut on X - Y plane
        :param feedrate_z:      speed for cut on Z plane
        :param feedrate_rapid:  speed to move between cuts; usually is G0 but some CNC require to specify it
        :param cont:
        :param old_point:
        :return:                G-code to cut along the linear feature.
        """

        if z_cut is None:
            z_cut = self.z_cut

        if z_move is None:
            z_move = self.z_move
        #
        # if zdownrate is None:
        #     zdownrate = self.zdownrate

        if feedrate is None:
            feedrate = self.feedrate

        if feedrate_z is None:
            feedrate_z = self.z_feedrate

        if feedrate_rapid is None:
            feedrate_rapid = self.feedrate_rapid

        # Simplify paths?
        if tolerance > 0:
            target_linear = linear.simplify(tolerance)
        else:
            target_linear = linear

        gcode = ""

        # path = list(target_linear.coords)
        path = self.segment(target_linear.coords)

        p = self.pp_geometry

        self.coordinates_type = self.app.defaults["cncjob_coords_type"]
        if self.coordinates_type == "G90":
            # For Absolute coordinates type G90
            first_x = path[0][0]
            first_y = path[0][1]
        else:
            # For Incremental coordinates type G91
            first_x = path[0][0] - old_point[0]
            first_y = path[0][1] - old_point[1]

        # Move fast to 1st point
        if not cont:
            current_tooldia = dia
            travels = self.app.exc_areas.travel_coordinates(start_point=(old_point[0], old_point[1]),
                                                            end_point=(first_x, first_y),
                                                            tooldia=current_tooldia)
            prev_z = None
            for travel in travels:
                locx = travel[1][0]
                locy = travel[1][1]

                if travel[0] is not None:
                    # move to next point
                    gcode += self.doformat(p.rapid_code, x=locx, y=locy)

                    # raise to safe Z (travel[0]) each time because safe Z may be different
                    self.z_move = travel[0]
                    gcode += self.doformat(p.lift_code, x=locx, y=locy)

                    # restore z_move
                    self.z_move = z_move
                else:
                    if prev_z is not None:
                        # move to next point
                        gcode += self.doformat(p.rapid_code, x=locx, y=locy)

                        # we assume that previously the z_move was altered therefore raise to
                        # the travel_z (z_move)
                        self.z_move = z_move
                        gcode += self.doformat(p.lift_code, x=locx, y=locy)
                    else:
                        # move to next point
                        gcode += self.doformat(p.rapid_code, x=locx, y=locy)

                # store prev_z
                prev_z = travel[0]

            # gcode += self.doformat(p.rapid_code, x=first_x, y=first_y)  # Move to first point

        # Move down to cutting depth
        if down:
            # Different feedrate for vertical cut?
            gcode += self.doformat(p.z_feedrate_code)
            # gcode += self.doformat(p.feedrate_code)
            gcode += self.doformat(p.down_code, x=first_x, y=first_y, z_cut=z_cut)
            gcode += self.doformat(p.feedrate_code, feedrate=feedrate)

        # Cutting...
        prev_x = first_x
        prev_y = first_y
        for pt in path[1:]:
            if self.app.abort_flag:
                # graceful abort requested by the user
                raise grace

            if self.coordinates_type == "G90":
                # For Absolute coordinates type G90
                next_x = pt[0]
                next_y = pt[1]
            else:
                # For Incremental coordinates type G91
                # next_x = pt[0] - prev_x
                # next_y = pt[1] - prev_y
                self.app.inform.emit('[ERROR_NOTCL] %s...' % _('G91 coordinates not implemented'))
                next_x = pt[0]
                next_y = pt[1]

            gcode += self.doformat(p.linear_code, x=next_x, y=next_y, z=z_cut)  # Linear motion to point
            prev_x = pt[0]
            prev_y = pt[1]

        # Up to travelling height.
        if up:
            gcode += self.doformat(p.lift_code, x=prev_x, y=prev_y, z_move=z_move)  # Stop cutting
        return gcode

    def linear2gcode_extra(self, linear, dia, extracut_length, tolerance=0, down=True, up=True,
                           z_cut=None, z_move=None, zdownrate=None,
                           feedrate=None, feedrate_z=None, feedrate_rapid=None, cont=False, old_point=(0, 0)):
        """

        Generates G-code to cut along the linear feature.

        :param linear:              The path to cut along.
        :type:                      Shapely.LinearRing or Shapely.Linear String
        :param dia:                 The tool diameter that is going on the path
        :type dia:                  float
        :param extracut_length:     how much to cut extra over the first point at the end of the path
        :param tolerance:           All points in the simplified object will be within the
                                    tolerance distance of the original geometry.
        :type tolerance:            float
        :param down:
        :param up:
        :param z_cut:
        :param z_move:
        :param zdownrate:
        :param feedrate:            speed for cut on X - Y plane
        :param feedrate_z:          speed for cut on Z plane
        :param feedrate_rapid:      speed to move between cuts; usually is G0 but some CNC require to specify it
        :param cont:
        :param old_point:
        :return:                    G-code to cut along the linear feature.
        :rtype:                     str
        """

        if z_cut is None:
            z_cut = self.z_cut

        if z_move is None:
            z_move = self.z_move
        #
        # if zdownrate is None:
        #     zdownrate = self.zdownrate

        if feedrate is None:
            feedrate = self.feedrate

        if feedrate_z is None:
            feedrate_z = self.z_feedrate

        if feedrate_rapid is None:
            feedrate_rapid = self.feedrate_rapid

        # Simplify paths?
        if tolerance > 0:
            target_linear = linear.simplify(tolerance)
        else:
            target_linear = linear

        gcode = ""

        path = list(target_linear.coords)
        p = self.pp_geometry

        self.coordinates_type = self.app.defaults["cncjob_coords_type"]
        if self.coordinates_type == "G90":
            # For Absolute coordinates type G90
            first_x = path[0][0]
            first_y = path[0][1]
        else:
            # For Incremental coordinates type G91
            first_x = path[0][0] - old_point[0]
            first_y = path[0][1] - old_point[1]

        # Move fast to 1st point
        if not cont:
            current_tooldia = dia
            travels = self.app.exc_areas.travel_coordinates(start_point=(old_point[0], old_point[1]),
                                                            end_point=(first_x, first_y),
                                                            tooldia=current_tooldia)
            prev_z = None
            for travel in travels:
                locx = travel[1][0]
                locy = travel[1][1]

                if travel[0] is not None:
                    # move to next point
                    gcode += self.doformat(p.rapid_code, x=locx, y=locy)

                    # raise to safe Z (travel[0]) each time because safe Z may be different
                    self.z_move = travel[0]
                    gcode += self.doformat(p.lift_code, x=locx, y=locy)

                    # restore z_move
                    self.z_move = z_move
                else:
                    if prev_z is not None:
                        # move to next point
                        gcode += self.doformat(p.rapid_code, x=locx, y=locy)

                        # we assume that previously the z_move was altered therefore raise to
                        # the travel_z (z_move)
                        self.z_move = z_move
                        gcode += self.doformat(p.lift_code, x=locx, y=locy)
                    else:
                        # move to next point
                        gcode += self.doformat(p.rapid_code, x=locx, y=locy)

                # store prev_z
                prev_z = travel[0]

            # gcode += self.doformat(p.rapid_code, x=first_x, y=first_y)  # Move to first point

        # Move down to cutting depth
        if down:
            # Different feedrate for vertical cut?
            if self.z_feedrate is not None:
                gcode += self.doformat(p.z_feedrate_code)
                # gcode += self.doformat(p.feedrate_code)
                gcode += self.doformat(p.down_code, x=first_x, y=first_y, z_cut=z_cut)
                gcode += self.doformat(p.feedrate_code, feedrate=feedrate)
            else:
                gcode += self.doformat(p.down_code, x=first_x, y=first_y, z_cut=z_cut)  # Start cutting

        # Cutting...
        prev_x = first_x
        prev_y = first_y
        for pt in path[1:]:
            if self.app.abort_flag:
                # graceful abort requested by the user
                raise grace

            if self.coordinates_type == "G90":
                # For Absolute coordinates type G90
                next_x = pt[0]
                next_y = pt[1]
            else:
                # For Incremental coordinates type G91
                # For Incremental coordinates type G91
                # next_x = pt[0] - prev_x
                # next_y = pt[1] - prev_y
                self.app.inform.emit('[ERROR_NOTCL] %s...' % _('G91 coordinates not implemented'))
                next_x = pt[0]
                next_y = pt[1]

            gcode += self.doformat(p.linear_code, x=next_x, y=next_y, z=z_cut)  # Linear motion to point
            prev_x = next_x
            prev_y = next_y

        # this line is added to create an extra cut over the first point in patch
        # to make sure that we remove the copper leftovers
        # Linear motion to the 1st point in the cut path
        # if self.coordinates_type == "G90":
        #     # For Absolute coordinates type G90
        #     last_x = path[1][0]
        #     last_y = path[1][1]
        # else:
        #     # For Incremental coordinates type G91
        #     last_x = path[1][0] - first_x
        #     last_y = path[1][1] - first_y
        # gcode += self.doformat(p.linear_code, x=last_x, y=last_y)

        # the first point for extracut is always mandatory if the extracut is enabled. But if the length of distance
        # between point 0 and point 1 is more than the distance we set for the extra cut then make an interpolation
        # along the path and find the point at the distance extracut_length

        if extracut_length == 0.0:
            extra_path = [path[-1], path[0], path[1]]
            new_x = extra_path[0][0]
            new_y = extra_path[0][1]

            # this is an extra line therefore lift the milling bit
            gcode += self.doformat(p.lift_code, x=prev_x, y=prev_y, z_move=z_move)  # lift

            # move fast to the new first point
            gcode += self.doformat(p.rapid_code, x=new_x, y=new_y)

            # lower the milling bit
            # Different feedrate for vertical cut?
            if self.z_feedrate is not None:
                gcode += self.doformat(p.z_feedrate_code)
                gcode += self.doformat(p.down_code, x=new_x, y=new_y, z_cut=z_cut)
                gcode += self.doformat(p.feedrate_code, feedrate=feedrate)
            else:
                gcode += self.doformat(p.down_code, x=new_x, y=new_y, z_cut=z_cut)  # Start cutting

            # start cutting the extra line
            last_pt = extra_path[0]
            for pt in extra_path[1:]:
                gcode += self.doformat(p.linear_code, x=pt[0], y=pt[1])
                last_pt = pt

            # go back to the original point
            gcode += self.doformat(p.linear_code, x=path[0][0], y=path[0][1])
            last_pt = path[0]
        else:
            # go to the point that is 5% in length before the end (therefore 95% length from start of the line),
            # along the line to be cut
            if extracut_length >= target_linear.length:
                extracut_length = target_linear.length

            # ---------------------------------------------
            # first half
            # ---------------------------------------------
            start_length = target_linear.length - (extracut_length * 0.5)
            extra_line = substring(target_linear, start_length, target_linear.length)
            extra_path = list(extra_line.coords)
            new_x = extra_path[0][0]
            new_y = extra_path[0][1]

            # this is an extra line therefore lift the milling bit
            gcode += self.doformat(p.lift_code, x=prev_x, y=prev_y, z_move=z_move)  # lift

            # move fast to the new first point
            gcode += self.doformat(p.rapid_code, x=new_x, y=new_y)

            # lower the milling bit
            # Different feedrate for vertical cut?
            if self.z_feedrate is not None:
                gcode += self.doformat(p.z_feedrate_code)
                gcode += self.doformat(p.down_code, x=new_x, y=new_y, z_cut=z_cut)
                gcode += self.doformat(p.feedrate_code, feedrate=feedrate)
            else:
                gcode += self.doformat(p.down_code, x=new_x, y=new_y, z_cut=z_cut)  # Start cutting

            # start cutting the extra line
            for pt in extra_path[1:]:
                gcode += self.doformat(p.linear_code, x=pt[0], y=pt[1])

            # ---------------------------------------------
            # second half
            # ---------------------------------------------
            extra_line = substring(target_linear, 0, (extracut_length * 0.5))
            extra_path = list(extra_line.coords)

            # start cutting the extra line
            last_pt = extra_path[0]
            for pt in extra_path[1:]:
                gcode += self.doformat(p.linear_code, x=pt[0], y=pt[1])
                last_pt = pt

            # ---------------------------------------------
            # back to original start point, cutting
            # ---------------------------------------------
            extra_line = substring(target_linear, 0, (extracut_length * 0.5))
            extra_path = list(extra_line.coords)[::-1]

            # start cutting the extra line
            last_pt = extra_path[0]
            for pt in extra_path[1:]:
                gcode += self.doformat(p.linear_code, x=pt[0], y=pt[1])
                last_pt = pt

        # if extracut_length == 0.0:
        #     gcode += self.doformat(p.linear_code, x=path[1][0], y=path[1][1])
        #     last_pt = path[1]
        # else:
        #     if abs(distance(path[1], path[0])) > extracut_length:
        #         i_point = LineString([path[0], path[1]]).interpolate(extracut_length)
        #         gcode += self.doformat(p.linear_code, x=i_point.x, y=i_point.y)
        #         last_pt = (i_point.x, i_point.y)
        #     else:
        #         last_pt = path[0]
        #         for pt in path[1:]:
        #             extracut_distance = abs(distance(pt, last_pt))
        #             if extracut_distance <= extracut_length:
        #                 gcode += self.doformat(p.linear_code, x=pt[0], y=pt[1])
        #                 last_pt = pt
        #             else:
        #                 break

        # Up to travelling height.
        if up:
            gcode += self.doformat(p.lift_code, x=last_pt[0], y=last_pt[1], z_move=z_move)  # Stop cutting

        return gcode

    def point2gcode(self, point, dia, z_move=None, old_point=(0, 0)):
        """

        :param point:               A Shapely Point
        :type point:                Point
        :param dia:                 The tool diameter that is going on the path
        :type dia:                  float
        :param z_move:              Travel Z
        :type z_move:               float
        :param old_point:           Old point coordinates from which we moved to the 'point'
        :type old_point:            tuple
        :return:                    G-code to cut on the Point feature.
        :rtype:                     str
        """
        gcode = ""

        if self.app.abort_flag:
            # graceful abort requested by the user
            raise grace

        path = list(point.coords)
        p = self.pp_geometry

        self.coordinates_type = self.app.defaults["cncjob_coords_type"]
        if self.coordinates_type == "G90":
            # For Absolute coordinates type G90
            first_x = path[0][0]
            first_y = path[0][1]
        else:
            # For Incremental coordinates type G91
            # first_x = path[0][0] - old_point[0]
            # first_y = path[0][1] - old_point[1]
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _('G91 coordinates not implemented ...'))
            first_x = path[0][0]
            first_y = path[0][1]

        current_tooldia = dia
        travels = self.app.exc_areas.travel_coordinates(start_point=(old_point[0], old_point[1]),
                                                        end_point=(first_x, first_y),
                                                        tooldia=current_tooldia)
        prev_z = None
        for travel in travels:
            locx = travel[1][0]
            locy = travel[1][1]

            if travel[0] is not None:
                # move to next point
                gcode += self.doformat(p.rapid_code, x=locx, y=locy)

                # raise to safe Z (travel[0]) each time because safe Z may be different
                self.z_move = travel[0]
                gcode += self.doformat(p.lift_code, x=locx, y=locy)

                # restore z_move
                self.z_move = z_move
            else:
                if prev_z is not None:
                    # move to next point
                    gcode += self.doformat(p.rapid_code, x=locx, y=locy)

                    # we assume that previously the z_move was altered therefore raise to
                    # the travel_z (z_move)
                    self.z_move = z_move
                    gcode += self.doformat(p.lift_code, x=locx, y=locy)
                else:
                    # move to next point
                    gcode += self.doformat(p.rapid_code, x=locx, y=locy)

            # store prev_z
            prev_z = travel[0]

        # gcode += self.doformat(p.linear_code, x=first_x, y=first_y)  # Move to first point

        if self.z_feedrate is not None:
            gcode += self.doformat(p.z_feedrate_code)
            gcode += self.doformat(p.down_code, x=first_x, y=first_y, z_cut=self.z_cut)
            gcode += self.doformat(p.feedrate_code)
        else:
            gcode += self.doformat(p.down_code, x=first_x, y=first_y, z_cut=self.z_cut)  # Start cutting

        gcode += self.doformat(p.lift_code, x=first_x, y=first_y)  # Stop cutting
        return gcode

    def export_svg(self, scale_stroke_factor=0.00):
        """
        Exports the CNC Job as a SVG Element

        :param scale_stroke_factor:     A factor to scale the SVG geometry
        :type scale_stroke_factor:      float
        :return:                        SVG Element string
        :rtype:                         str
        """
        # scale_factor is a multiplication factor for the SVG stroke-width used within shapely's svg export
        # If not specified then try and use the tool diameter
        # This way what is on screen will match what is outputed for the svg
        # This is quite a useful feature for svg's used with visicut

        if scale_stroke_factor <= 0:
            scale_stroke_factor = self.options['tooldia'] / 2

        # If still 0 then default to 0.05
        # This value appears to work for zooming, and getting the output svg line width
        # to match that viewed on screen with FlatCam
        if scale_stroke_factor == 0:
            scale_stroke_factor = 0.01

        # Separate the list of cuts and travels into 2 distinct lists
        # This way we can add different formatting / colors to both
        cuts = []
        travels = []
        cutsgeom = ''
        travelsgeom = ''

        for g in self.gcode_parsed:
            if self.app.abort_flag:
                # graceful abort requested by the user
                raise grace

            if g['kind'][0] == 'C':
                cuts.append(g)
            if g['kind'][0] == 'T':
                travels.append(g)

        # Used to determine the overall board size
        self.solid_geometry = unary_union([geo['geom'] for geo in self.gcode_parsed])

        # Convert the cuts and travels into single geometry objects we can render as svg xml
        if travels:
            travelsgeom = unary_union([geo['geom'] for geo in travels])

        if self.app.abort_flag:
            # graceful abort requested by the user
            raise grace

        if cuts:
            cutsgeom = unary_union([geo['geom'] for geo in cuts])

        # Render the SVG Xml
        # The scale factor affects the size of the lines, and the stroke color adds different formatting for each set
        # It's better to have the travels sitting underneath the cuts for visicut
        svg_elem = ""
        if travels:
            svg_elem = travelsgeom.svg(scale_factor=scale_stroke_factor, stroke_color="#F0E24D")
        if cuts:
            svg_elem += cutsgeom.svg(scale_factor=scale_stroke_factor, stroke_color="#5E6CFF")

        return svg_elem

    def bounds(self, flatten=None):
        """
        Returns coordinates of rectangular bounds of geometry: (xmin, ymin, xmax, ymax).

        :param flatten:     Not used, it is here for compatibility with base class method
        :type flatten:      bool
        :return:            Bounding values in format (xmin, ymin, xmax, ymax)
        :rtype:             tuple
        """

        log.debug("camlib.CNCJob.bounds()")

        def bounds_rec(obj):
            if type(obj) is list:
                cminx = np.Inf
                cminy = np.Inf
                cmaxx = -np.Inf
                cmaxy = -np.Inf

                for k in obj:
                    if type(k) is dict:
                        for key in k:
                            minx_, miny_, maxx_, maxy_ = bounds_rec(k[key])
                            cminx = min(cminx, minx_)
                            cminy = min(cminy, miny_)
                            cmaxx = max(cmaxx, maxx_)
                            cmaxy = max(cmaxy, maxy_)
                    else:
                        minx_, miny_, maxx_, maxy_ = bounds_rec(k)
                        cminx = min(cminx, minx_)
                        cminy = min(cminy, miny_)
                        cmaxx = max(cmaxx, maxx_)
                        cmaxy = max(cmaxy, maxy_)
                return cminx, cminy, cmaxx, cmaxy
            else:
                # it's a Shapely object, return it's bounds
                return obj.bounds

        if self.multitool is False:
            log.debug("CNCJob->bounds()")
            if self.solid_geometry is None:
                log.debug("solid_geometry is None")
                return 0, 0, 0, 0

            bounds_coords = bounds_rec(self.solid_geometry)
        else:
            minx = np.Inf
            miny = np.Inf
            maxx = -np.Inf
            maxy = -np.Inf
            if self.cnc_tools:
                for k, v in self.cnc_tools.items():
                    minx = np.Inf
                    miny = np.Inf
                    maxx = -np.Inf
                    maxy = -np.Inf
                    try:
                        for k in v['solid_geometry']:
                            minx_, miny_, maxx_, maxy_ = bounds_rec(k)
                            minx = min(minx, minx_)
                            miny = min(miny, miny_)
                            maxx = max(maxx, maxx_)
                            maxy = max(maxy, maxy_)
                    except TypeError:
                        minx_, miny_, maxx_, maxy_ = bounds_rec(v['solid_geometry'])
                        minx = min(minx, minx_)
                        miny = min(miny, miny_)
                        maxx = max(maxx, maxx_)
                        maxy = max(maxy, maxy_)

            if self.exc_cnc_tools:
                for k, v in self.exc_cnc_tools.items():
                    minx = np.Inf
                    miny = np.Inf
                    maxx = -np.Inf
                    maxy = -np.Inf
                    try:
                        for k in v['solid_geometry']:
                            minx_, miny_, maxx_, maxy_ = bounds_rec(k)
                            minx = min(minx, minx_)
                            miny = min(miny, miny_)
                            maxx = max(maxx, maxx_)
                            maxy = max(maxy, maxy_)
                    except TypeError:
                        minx_, miny_, maxx_, maxy_ = bounds_rec(v['solid_geometry'])
                        minx = min(minx, minx_)
                        miny = min(miny, miny_)
                        maxx = max(maxx, maxx_)
                        maxy = max(maxy, maxy_)

            bounds_coords = minx, miny, maxx, maxy
        return bounds_coords

    # TODO This function should be replaced at some point with a "real" function. Until then it's an ugly hack ...
    def scale(self, xfactor, yfactor=None, point=None):
        """
        Scales all the geometry on the XY plane in the object by the
        given factor. Tool sizes, feedrates, or Z-axis dimensions are
        not altered.

        :param factor:  Number by which to scale the object.
        :type factor:   float
        :param point:   the (x,y) coords for the point of origin of scale
        :type           tuple of floats
        :return:        None
        :rtype:         None
        """
        log.debug("camlib.CNCJob.scale()")

        if yfactor is None:
            yfactor = xfactor

        if point is None:
            px = 0
            py = 0
        else:
            px, py = point

        def scale_g(g):
            """

            :param g: 'g' parameter it's a gcode string
            :return:  scaled gcode string
            """

            temp_gcode = ''
            header_start = False
            header_stop = False
            units = self.app.defaults['units'].upper()

            lines = StringIO(g)
            for line in lines:

                # this changes the GCODE header ---- UGLY HACK
                if "TOOL DIAMETER" in line or "Feedrate:" in line:
                    header_start = True

                if "G20" in line or "G21" in line:
                    header_start = False
                    header_stop = True

                if header_start is True:
                    header_stop = False
                    if "in" in line:
                        if units == 'MM':
                            line = line.replace("in", "mm")
                    if "mm" in line:
                        if units == 'IN':
                            line = line.replace("mm", "in")

                    # find any float number in header (even multiple on the same line) and convert it
                    numbers_in_header = re.findall(self.g_nr_re, line)
                    if numbers_in_header:
                        for nr in numbers_in_header:
                            new_nr = float(nr) * xfactor
                            # replace the updated string
                            line = line.replace(nr, ('%.*f' % (self.app.defaults["cncjob_coords_decimals"], new_nr))
                                                )

                # this scales all the X and Y and Z and F values and also the Tool Dia in the toolchange message
                if header_stop is True:
                    if "G20" in line:
                        if units == 'MM':
                            line = line.replace("G20", "G21")
                    if "G21" in line:
                        if units == 'IN':
                            line = line.replace("G21", "G20")

                    # find the X group
                    match_x = self.g_x_re.search(line)
                    if match_x:
                        if match_x.group(1) is not None:
                            new_x = float(match_x.group(1)[1:]) * xfactor
                            # replace the updated string
                            line = line.replace(
                                match_x.group(1),
                                'X%.*f' % (self.app.defaults["cncjob_coords_decimals"], new_x)
                            )
                    # find the Y group
                    match_y = self.g_y_re.search(line)
                    if match_y:
                        if match_y.group(1) is not None:
                            new_y = float(match_y.group(1)[1:]) * yfactor
                            line = line.replace(
                                match_y.group(1),
                                'Y%.*f' % (self.app.defaults["cncjob_coords_decimals"], new_y)
                            )
                    # find the Z group
                    match_z = self.g_z_re.search(line)
                    if match_z:
                        if match_z.group(1) is not None:
                            new_z = float(match_z.group(1)[1:]) * xfactor
                            line = line.replace(
                                match_z.group(1),
                                'Z%.*f' % (self.app.defaults["cncjob_coords_decimals"], new_z)
                            )

                    # find the F group
                    match_f = self.g_f_re.search(line)
                    if match_f:
                        if match_f.group(1) is not None:
                            new_f = float(match_f.group(1)[1:]) * xfactor
                            line = line.replace(
                                match_f.group(1),
                                'F%.*f' % (self.app.defaults["cncjob_fr_decimals"], new_f)
                            )
                    # find the T group (tool dia on toolchange)
                    match_t = self.g_t_re.search(line)
                    if match_t:
                        if match_t.group(1) is not None:
                            new_t = float(match_t.group(1)[1:]) * xfactor
                            line = line.replace(
                                match_t.group(1),
                                '= %.*f' % (self.app.defaults["cncjob_coords_decimals"], new_t)
                            )

                temp_gcode += line
            lines.close()
            header_stop = False
            return temp_gcode

        if self.multitool is False:
            # offset Gcode
            self.gcode = scale_g(self.gcode)

            # variables to display the percentage of work done
            self.geo_len = 0
            try:
                self.geo_len = len(self.gcode_parsed)
            except TypeError:
                self.geo_len = 1
            self.old_disp_number = 0
            self.el_count = 0

            # scale geometry
            for g in self.gcode_parsed:
                try:
                    g['geom'] = affinity.scale(g['geom'], xfactor, yfactor, origin=(px, py))
                except AttributeError:
                    return g['geom']

                self.el_count += 1
                disp_number = int(np.interp(self.el_count, [0, self.geo_len], [0, 100]))
                if self.old_disp_number < disp_number <= 100:
                    self.app.proc_container.update_view_text(' %d%%' % disp_number)
                    self.old_disp_number = disp_number

            self.create_geometry()
        else:
            for k, v in self.cnc_tools.items():
                # scale Gcode
                v['gcode'] = scale_g(v['gcode'])

                # variables to display the percentage of work done
                self.geo_len = 0
                try:
                    self.geo_len = len(v['gcode_parsed'])
                except TypeError:
                    self.geo_len = 1
                self.old_disp_number = 0
                self.el_count = 0

                # scale gcode_parsed
                for g in v['gcode_parsed']:
                    try:
                        g['geom'] = affinity.scale(g['geom'], xfactor, yfactor, origin=(px, py))
                    except AttributeError:
                        return g['geom']

                    self.el_count += 1
                    disp_number = int(np.interp(self.el_count, [0, self.geo_len], [0, 100]))
                    if self.old_disp_number < disp_number <= 100:
                        self.app.proc_container.update_view_text(' %d%%' % disp_number)
                        self.old_disp_number = disp_number

                v['solid_geometry'] = unary_union([geo['geom'] for geo in v['gcode_parsed']])
        self.create_geometry()
        self.app.proc_container.new_text = ''

    def offset(self, vect):
        """
        Offsets all the geometry on the XY plane in the object by the
        given vector.
        Offsets all the GCODE on the XY plane in the object by the
        given vector.

        g_offsetx_re, g_offsety_re, multitool, cnnc_tools are attributes of FlatCAMCNCJob class in camlib

        :param vect:    (x, y) offset vector.
        :type vect:     tuple
        :return:        None
        """
        log.debug("camlib.CNCJob.offset()")

        dx, dy = vect

        def offset_g(g):
            """

            :param g: 'g' parameter it's a gcode string
            :return:  offseted gcode string
            """

            temp_gcode = ''
            lines = StringIO(g)
            for line in lines:
                # find the X group
                match_x = self.g_x_re.search(line)
                if match_x:
                    if match_x.group(1) is not None:
                        # get the coordinate and add X offset
                        new_x = float(match_x.group(1)[1:]) + dx
                        # replace the updated string
                        line = line.replace(
                            match_x.group(1),
                            'X%.*f' % (self.app.defaults["cncjob_coords_decimals"], new_x)
                        )
                match_y = self.g_y_re.search(line)
                if match_y:
                    if match_y.group(1) is not None:
                        new_y = float(match_y.group(1)[1:]) + dy
                        line = line.replace(
                            match_y.group(1),
                            'Y%.*f' % (self.app.defaults["cncjob_coords_decimals"], new_y)
                        )
                temp_gcode += line
            lines.close()
            return temp_gcode

        if self.multitool is False:
            # offset Gcode
            self.gcode = offset_g(self.gcode)

            # variables to display the percentage of work done
            self.geo_len = 0
            try:
                self.geo_len = len(self.gcode_parsed)
            except TypeError:
                self.geo_len = 1
            self.old_disp_number = 0
            self.el_count = 0

            # offset geometry
            for g in self.gcode_parsed:
                try:
                    g['geom'] = affinity.translate(g['geom'], xoff=dx, yoff=dy)
                except AttributeError:
                    return g['geom']

                self.el_count += 1
                disp_number = int(np.interp(self.el_count, [0, self.geo_len], [0, 100]))
                if self.old_disp_number < disp_number <= 100:
                    self.app.proc_container.update_view_text(' %d%%' % disp_number)
                    self.old_disp_number = disp_number

            self.create_geometry()
        else:
            for k, v in self.cnc_tools.items():
                # offset Gcode
                v['gcode'] = offset_g(v['gcode'])

                # variables to display the percentage of work done
                self.geo_len = 0
                try:
                    self.geo_len = len(v['gcode_parsed'])
                except TypeError:
                    self.geo_len = 1
                self.old_disp_number = 0
                self.el_count = 0

                # offset gcode_parsed
                for g in v['gcode_parsed']:
                    try:
                        g['geom'] = affinity.translate(g['geom'], xoff=dx, yoff=dy)
                    except AttributeError:
                        return g['geom']

                    self.el_count += 1
                    disp_number = int(np.interp(self.el_count, [0, self.geo_len], [0, 100]))
                    if self.old_disp_number < disp_number <= 100:
                        self.app.proc_container.update_view_text(' %d%%' % disp_number)
                        self.old_disp_number = disp_number

                # for the bounding box
                v['solid_geometry'] = unary_union([geo['geom'] for geo in v['gcode_parsed']])

        self.app.proc_container.new_text = ''

    def mirror(self, axis, point):
        """
        Mirror the geometry of an object by an given axis around the coordinates of the 'point'

        :param axis:    Axis for Mirror
        :param point:   tuple of coordinates (x,y). Point of origin for Mirror
        :return:
        """
        log.debug("camlib.CNCJob.mirror()")

        px, py = point
        xscale, yscale = {"X": (1.0, -1.0), "Y": (-1.0, 1.0)}[axis]

        # variables to display the percentage of work done
        self.geo_len = 0
        try:
            self.geo_len = len(self.gcode_parsed)
        except TypeError:
            self.geo_len = 1
        self.old_disp_number = 0
        self.el_count = 0

        for g in self.gcode_parsed:
            try:
                g['geom'] = affinity.scale(g['geom'], xscale, yscale, origin=(px, py))
            except AttributeError:
                return g['geom']

            self.el_count += 1
            disp_number = int(np.interp(self.el_count, [0, self.geo_len], [0, 100]))
            if self.old_disp_number < disp_number <= 100:
                self.app.proc_container.update_view_text(' %d%%' % disp_number)
                self.old_disp_number = disp_number

        self.create_geometry()
        self.app.proc_container.new_text = ''

    def skew(self, angle_x, angle_y, point):
        """
        Shear/Skew the geometries of an object by angles along x and y dimensions.

        :param angle_x:
        :param angle_y:
        angle_x, angle_y : float, float
            The shear angle(s) for the x and y axes respectively. These can be
            specified in either degrees (default) or radians by setting
            use_radians=True.

        :param point:   tupple of coordinates (x,y)

        See shapely manual for more information: http://toblerity.org/shapely/manual.html#affine-transformations
        """
        log.debug("camlib.CNCJob.skew()")

        px, py = point

        # variables to display the percentage of work done
        self.geo_len = 0
        try:
            self.geo_len = len(self.gcode_parsed)
        except TypeError:
            self.geo_len = 1
        self.old_disp_number = 0
        self.el_count = 0

        for g in self.gcode_parsed:
            try:
                g['geom'] = affinity.skew(g['geom'], angle_x, angle_y, origin=(px, py))
            except AttributeError:
                return g['geom']

            self.el_count += 1
            disp_number = int(np.interp(self.el_count, [0, self.geo_len], [0, 100]))
            if self.old_disp_number < disp_number <= 100:
                self.app.proc_container.update_view_text(' %d%%' % disp_number)
                self.old_disp_number = disp_number

        self.create_geometry()
        self.app.proc_container.new_text = ''

    def rotate(self, angle, point):
        """
        Rotate the geometry of an object by an given angle around the coordinates of the 'point'

        :param angle:   Angle of Rotation
        :param point:   tuple of coordinates (x,y). Origin point for Rotation
        :return:
        """
        log.debug("camlib.CNCJob.rotate()")

        px, py = point

        # variables to display the percentage of work done
        self.geo_len = 0
        try:
            self.geo_len = len(self.gcode_parsed)
        except TypeError:
            self.geo_len = 1
        self.old_disp_number = 0
        self.el_count = 0

        for g in self.gcode_parsed:
            try:
                g['geom'] = affinity.rotate(g['geom'], angle, origin=(px, py))
            except AttributeError:
                return g['geom']

            self.el_count += 1
            disp_number = int(np.interp(self.el_count, [0, self.geo_len], [0, 100]))
            if self.old_disp_number < disp_number <= 100:
                self.app.proc_container.update_view_text(' %d%%' % disp_number)
                self.old_disp_number = disp_number

        self.create_geometry()
        self.app.proc_container.new_text = ''


def get_bounds(geometry_list):
    """
    Will return limit values for a list of geometries

    :param geometry_list:   List of geometries for which to calculate the bounds limits
    :return:
    """
    xmin = np.Inf
    ymin = np.Inf
    xmax = -np.Inf
    ymax = -np.Inf

    for gs in geometry_list:
        try:
            gxmin, gymin, gxmax, gymax = gs.bounds()
            xmin = min([xmin, gxmin])
            ymin = min([ymin, gymin])
            xmax = max([xmax, gxmax])
            ymax = max([ymax, gymax])
        except Exception:
            log.warning("DEVELOPMENT: Tried to get bounds of empty geometry.")

    return [xmin, ymin, xmax, ymax]


def arc(center, radius, start, stop, direction, steps_per_circ):
    """
    Creates a list of point along the specified arc.

    :param center:          Coordinates of the center [x, y]
    :type center:           list
    :param radius:          Radius of the arc.
    :type radius:           float
    :param start:           Starting angle in radians
    :type start:            float
    :param stop:            End angle in radians
    :type stop:             float
    :param direction:       Orientation of the arc, "CW" or "CCW"
    :type direction:        string
    :param steps_per_circ:  Number of straight line segments to
                            represent a circle.
    :type steps_per_circ:   int
    :return:                The desired arc, as list of tuples
    :rtype:                 list
    """
    # TODO: Resolution should be established by maximum error from the exact arc.

    da_sign = {"cw": -1.0, "ccw": 1.0}
    points = []
    if direction == "ccw" and stop <= start:
        stop += 2 * np.pi
    if direction == "cw" and stop >= start:
        stop -= 2 * np.pi

    angle = abs(stop - start)

    # angle = stop-start
    steps = max([int(np.ceil(angle / (2 * np.pi) * steps_per_circ)), 2])
    delta_angle = da_sign[direction] * angle * 1.0 / steps
    for i in range(steps + 1):
        theta = start + delta_angle * i
        points.append((center[0] + radius * np.cos(theta), center[1] + radius * np.sin(theta)))
    return points


def arc2(p1, p2, center, direction, steps_per_circ):
    r = np.sqrt((center[0] - p1[0]) ** 2 + (center[1] - p1[1]) ** 2)
    start = np.arctan2(p1[1] - center[1], p1[0] - center[0])
    stop = np.arctan2(p2[1] - center[1], p2[0] - center[0])
    return arc(center, r, start, stop, direction, steps_per_circ)


def arc_angle(start, stop, direction):
    if direction == "ccw" and stop <= start:
        stop += 2 * np.pi
    if direction == "cw" and stop >= start:
        stop -= 2 * np.pi

    angle = abs(stop - start)
    return angle


# def find_polygon(poly, point):
#     """
#     Find an object that object.contains(Point(point)) in
#     poly, which can can be iterable, contain iterable of, or
#     be itself an implementer of .contains().
#
#     :param poly: See description
#     :return: Polygon containing point or None.
#     """
#
#     if poly is None:
#         return None
#
#     try:
#         for sub_poly in poly:
#             p = find_polygon(sub_poly, point)
#             if p is not None:
#                 return p
#     except TypeError:
#         try:
#             if poly.contains(Point(point)):
#                 return poly
#         except AttributeError:
#             return None
#
#     return None


def to_dict(obj):
    """
    Makes the following types into serializable form:

    * ApertureMacro
    * BaseGeometry

    :param obj:     Shapely geometry.
    :type obj:      BaseGeometry
    :return:        Dictionary with serializable form if ``obj`` was
                    BaseGeometry or ApertureMacro, otherwise returns ``obj``.
    """
    if isinstance(obj, ApertureMacro):
        return {
            "__class__": "ApertureMacro",
            "__inst__": obj.to_dict()
        }
    if isinstance(obj, BaseGeometry):
        return {
            "__class__": "Shply",
            "__inst__": sdumps(obj)
        }
    return obj


def dict2obj(d):
    """
    Default deserializer.

    :param d:   Serializable dictionary representation of an object
                to be reconstructed.
    :return:    Reconstructed object.
    """
    if '__class__' in d and '__inst__' in d:
        if d['__class__'] == "Shply":
            return sloads(d['__inst__'])
        if d['__class__'] == "ApertureMacro":
            am = ApertureMacro()
            am.from_dict(d['__inst__'])
            return am
        return d
    else:
        return d


# def plotg(geo, solid_poly=False, color="black"):
#     try:
#         __ = iter(geo)
#     except:
#         geo = [geo]
#
#     for g in geo:
#         if type(g) == Polygon:
#             if solid_poly:
#                 patch = PolygonPatch(g,
#                                      facecolor="#BBF268",
#                                      edgecolor="#006E20",
#                                      alpha=0.75,
#                                      zorder=2)
#                 ax = subplot(111)
#                 ax.add_patch(patch)
#             else:
#                 x, y = g.exterior.coords.xy
#                 plot(x, y, color=color)
#                 for ints in g.interiors:
#                     x, y = ints.coords.xy
#                     plot(x, y, color=color)
#                 continue
#
#         if type(g) == LineString or type(g) == LinearRing:
#             x, y = g.coords.xy
#             plot(x, y, color=color)
#             continue
#
#         if type(g) == Point:
#             x, y = g.coords.xy
#             plot(x, y, 'o')
#             continue
#
#         try:
#             __ = iter(g)
#             plotg(g, color=color)
#         except:
#             log.error("Cannot plot: " + str(type(g)))
#             continue

# def alpha_shape(points, alpha):
#     """
#     Compute the alpha shape (concave hull) of a set of points.
#
#     @param points: Iterable container of points.
#     @param alpha: alpha value to influence the gooeyness of the border. Smaller
#                   numbers don't fall inward as much as larger numbers. Too large,
#                   and you lose everything!
#     """
#     if len(points) < 4:
#         # When you have a triangle, there is no sense in computing an alpha
#         # shape.
#         return MultiPoint(list(points)).convex_hull
#
#     def add_edge(edges, edge_points, coords, i, j):
#         """Add a line between the i-th and j-th points, if not in the list already"""
#         if (i, j) in edges or (j, i) in edges:
#             # already added
#             return
#         edges.add( (i, j) )
#         edge_points.append(coords[ [i, j] ])
#
#     coords = np.array([point.coords[0] for point in points])
#
#     tri = Delaunay(coords)
#     edges = set()
#     edge_points = []
#     # loop over triangles:
#     # ia, ib, ic = indices of corner points of the triangle
#     for ia, ib, ic in tri.vertices:
#         pa = coords[ia]
#         pb = coords[ib]
#         pc = coords[ic]
#
#         # Lengths of sides of triangle
#         a = math.sqrt((pa[0]-pb[0])**2 + (pa[1]-pb[1])**2)
#         b = math.sqrt((pb[0]-pc[0])**2 + (pb[1]-pc[1])**2)
#         c = math.sqrt((pc[0]-pa[0])**2 + (pc[1]-pa[1])**2)
#
#         # Semiperimeter of triangle
#         s = (a + b + c)/2.0
#
#         # Area of triangle by Heron's formula
#         area = math.sqrt(s*(s-a)*(s-b)*(s-c))
#         circum_r = a*b*c/(4.0*area)
#
#         # Here's the radius filter.
#         #print circum_r
#         if circum_r < 1.0/alpha:
#             add_edge(edges, edge_points, coords, ia, ib)
#             add_edge(edges, edge_points, coords, ib, ic)
#             add_edge(edges, edge_points, coords, ic, ia)
#
#     m = MultiLineString(edge_points)
#     triangles = list(polygonize(m))
#     return unary_union(triangles), edge_points

# def voronoi(P):
#     """
#     Returns a list of all edges of the voronoi diagram for the given input points.
#     """
#     delauny = Delaunay(P)
#     triangles = delauny.points[delauny.vertices]
#
#     circum_centers = np.array([triangle_csc(tri) for tri in triangles])
#     long_lines_endpoints = []
#
#     lineIndices = []
#     for i, triangle in enumerate(triangles):
#         circum_center = circum_centers[i]
#         for j, neighbor in enumerate(delauny.neighbors[i]):
#             if neighbor != -1:
#                 lineIndices.append((i, neighbor))
#             else:
#                 ps = triangle[(j+1)%3] - triangle[(j-1)%3]
#                 ps = np.array((ps[1], -ps[0]))
#
#                 middle = (triangle[(j+1)%3] + triangle[(j-1)%3]) * 0.5
#                 di = middle - triangle[j]
#
#                 ps /= np.linalg.norm(ps)
#                 di /= np.linalg.norm(di)
#
#                 if np.dot(di, ps) < 0.0:
#                     ps *= -1000.0
#                 else:
#                     ps *= 1000.0
#
#                 long_lines_endpoints.append(circum_center + ps)
#                 lineIndices.append((i, len(circum_centers) + len(long_lines_endpoints)-1))
#
#     vertices = np.vstack((circum_centers, long_lines_endpoints))
#
#     # filter out any duplicate lines
#     lineIndicesSorted = np.sort(lineIndices) # make (1,2) and (2,1) both (1,2)
#     lineIndicesTupled = [tuple(row) for row in lineIndicesSorted]
#     lineIndicesUnique = np.unique(lineIndicesTupled)
#
#     return vertices, lineIndicesUnique
#
#
# def triangle_csc(pts):
#     rows, cols = pts.shape
#
#     A = np.bmat([[2 * np.dot(pts, pts.T), np.ones((rows, 1))],
#                  [np.ones((1, rows)), np.zeros((1, 1))]])
#
#     b = np.hstack((np.sum(pts * pts, axis=1), np.ones((1))))
#     x = np.linalg.solve(A,b)
#     bary_coords = x[:-1]
#     return np.sum(pts * np.tile(bary_coords.reshape((pts.shape[0], 1)), (1, pts.shape[1])), axis=0)
#
#
# def voronoi_cell_lines(points, vertices, lineIndices):
#     """
#     Returns a mapping from a voronoi cell to its edges.
#
#     :param points: shape (m,2)
#     :param vertices: shape (n,2)
#     :param lineIndices: shape (o,2)
#     :rtype: dict point index -> list of shape (n,2) with vertex indices
#     """
#     kd = KDTree(points)
#
#     cells = collections.defaultdict(list)
#     for i1, i2 in lineIndices:
#         v1, v2 = vertices[i1], vertices[i2]
#         mid = (v1+v2)/2
#         _, (p1Idx, p2Idx) = kd.query(mid, 2)
#         cells[p1Idx].append((i1, i2))
#         cells[p2Idx].append((i1, i2))
#
#     return cells
#
#
# def voronoi_edges2polygons(cells):
#     """
#     Transforms cell edges into polygons.
#
#     :param cells: as returned from voronoi_cell_lines
#     :rtype: dict point index -> list of vertex indices which form a polygon
#     """
#
#     # first, close the outer cells
#     for pIdx, lineIndices_ in cells.items():
#         dangling_lines = []
#         for i1, i2 in lineIndices_:
#             p = (i1, i2)
#             connections = filter(lambda k: p != k and
#             (p[0] == k[0] or p[0] == k[1] or p[1] == k[0] or p[1] == k[1]), lineIndices_)
#             # connections = filter(lambda (i1_, i2_): (i1, i2) != (i1_, i2_) and
#             (i1 == i1_ or i1 == i2_ or i2 == i1_ or i2 == i2_), lineIndices_)
#             assert 1 <= len(connections) <= 2
#             if len(connections) == 1:
#                 dangling_lines.append((i1, i2))
#         assert len(dangling_lines) in [0, 2]
#         if len(dangling_lines) == 2:
#             (i11, i12), (i21, i22) = dangling_lines
#             s = (i11, i12)
#             t = (i21, i22)
#
#             # determine which line ends are unconnected
#             connected = filter(lambda k: k != s and (k[0] == s[0] or k[1] == s[0]), lineIndices_)
#             # connected = filter(lambda (i1,i2): (i1,i2) != (i11,i12) and (i1 == i11 or i2 == i11), lineIndices_)
#             i11Unconnected = len(connected) == 0
#
#             connected = filter(lambda k: k != t and (k[0] == t[0] or k[1] == t[0]), lineIndices_)
#             # connected = filter(lambda (i1,i2): (i1,i2) != (i21,i22) and (i1 == i21 or i2 == i21), lineIndices_)
#             i21Unconnected = len(connected) == 0
#
#             startIdx = i11 if i11Unconnected else i12
#             endIdx = i21 if i21Unconnected else i22
#
#             cells[pIdx].append((startIdx, endIdx))
#
#     # then, form polygons by storing vertex indices in (counter-)clockwise order
#     polys = {}
#     for pIdx, lineIndices_ in cells.items():
#         # get a directed graph which contains both directions and arbitrarily follow one of both
#         directedGraph = lineIndices_ + [(i2, i1) for (i1, i2) in lineIndices_]
#         directedGraphMap = collections.defaultdict(list)
#         for (i1, i2) in directedGraph:
#             directedGraphMap[i1].append(i2)
#         orderedEdges = []
#         currentEdge = directedGraph[0]
#         while len(orderedEdges) < len(lineIndices_):
#             i1 = currentEdge[1]
#             i2 = directedGraphMap[i1][0] if directedGraphMap[i1][0] != currentEdge[0] else directedGraphMap[i1][1]
#             nextEdge = (i1, i2)
#             orderedEdges.append(nextEdge)
#             currentEdge = nextEdge
#
#         polys[pIdx] = [i1 for (i1, i2) in orderedEdges]
#
#     return polys
#
#
# def voronoi_polygons(points):
#     """
#     Returns the voronoi polygon for each input point.
#
#     :param points: shape (n,2)
#     :rtype: list of n polygons where each polygon is an array of vertices
#     """
#     vertices, lineIndices = voronoi(points)
#     cells = voronoi_cell_lines(points, vertices, lineIndices)
#     polys = voronoi_edges2polygons(cells)
#     polylist = []
#     for i in range(len(points)):
#         poly = vertices[np.asarray(polys[i])]
#         polylist.append(poly)
#     return polylist
#
#
# class Zprofile:
#     def __init__(self):
#
#         # data contains lists of [x, y, z]
#         self.data = []
#
#         # Computed voronoi polygons (shapely)
#         self.polygons = []
#         pass
#
#     # def plot_polygons(self):
#     #     axes = plt.subplot(1, 1, 1)
#     #
#     #     plt.axis([-0.05, 1.05, -0.05, 1.05])
#     #
#     #     for poly in self.polygons:
#     #         p = PolygonPatch(poly, facecolor=np.random.rand(3, 1), alpha=0.3)
#     #         axes.add_patch(p)
#
#     def init_from_csv(self, filename):
#         pass
#
#     def init_from_string(self, zpstring):
#         pass
#
#     def init_from_list(self, zplist):
#         self.data = zplist
#
#     def generate_polygons(self):
#         self.polygons = [Polygon(p) for p in voronoi_polygons(array([[x[0], x[1]] for x in self.data]))]
#
#     def normalize(self, origin):
#         pass
#
#     def paste(self, path):
#         """
#         Return a list of dictionaries containing the parts of the original
#         path and their z-axis offset.
#         """
#
#         # At most one region/polygon will contain the path
#         containing = [i for i in range(len(self.polygons)) if self.polygons[i].contains(path)]
#
#         if len(containing) > 0:
#             return [{"path": path, "z": self.data[containing[0]][2]}]
#
#         # All region indexes that intersect with the path
#         crossing = [i for i in range(len(self.polygons)) if self.polygons[i].intersects(path)]
#
#         return [{"path": path.intersection(self.polygons[i]),
#                  "z": self.data[i][2]} for i in crossing]


def autolist(obj):
    try:
        __ = iter(obj)
        return obj
    except TypeError:
        return [obj]


def three_point_circle(p1, p2, p3):
    """
    Computes the center and radius of a circle from
    3 points on its circumference.

    :param p1:  Point 1
    :param p2:  Point 2
    :param p3:  Point 3
    :return:    center, radius
    """
    # Midpoints
    a1 = (p1 + p2) / 2.0
    a2 = (p2 + p3) / 2.0

    # Normals
    b1 = np.dot((p2 - p1), np.array([[0, -1], [1, 0]], dtype=np.float32))
    b2 = np.dot((p3 - p2), np.array([[0, 1], [-1, 0]], dtype=np.float32))

    # Params
    try:
        T = solve(np.transpose(np.array([-b1, b2])), a1 - a2)
    except Exception as e:
        log.debug("camlib.three_point_circle() --> %s" % str(e))
        return

    # Center
    center = a1 + b1 * T[0]

    # Radius
    radius = np.linalg.norm(center - p1)

    return center, radius, T[0]


def distance(pt1, pt2):
    return np.sqrt((pt1[0] - pt2[0]) ** 2 + (pt1[1] - pt2[1]) ** 2)


def distance_euclidian(x1, y1, x2, y2):
    return np.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


class FlatCAMRTree(object):
    """
    Indexes geometry (Any object with "cooords" property containing
    a list of tuples with x, y values). Objects are indexed by
    all their points by default. To index by arbitrary points,
    override self.points2obj.
    """

    def __init__(self):
        # Python RTree Index
        self.rti = rtindex.Index()

        # ## Track object-point relationship
        # Each is list of points in object.
        self.obj2points = []

        # Index is index in rtree, value is index of
        # object in obj2points.
        self.points2obj = []

        self.get_points = lambda go: go.coords

    def grow_obj2points(self, idx):
        """
        Increases the size of self.obj2points to fit
        idx + 1 items.

        :param idx: Index to fit into list.
        :return: None
        """
        if len(self.obj2points) > idx:
            # len == 2, idx == 1, ok.
            return
        else:
            # len == 2, idx == 2, need 1 more.
            # range(2, 3)
            for i in range(len(self.obj2points), idx + 1):
                self.obj2points.append([])

    def insert(self, objid, obj):
        self.grow_obj2points(objid)
        self.obj2points[objid] = []

        for pt in self.get_points(obj):
            self.rti.insert(len(self.points2obj), (pt[0], pt[1], pt[0], pt[1]), obj=objid)
            self.obj2points[objid].append(len(self.points2obj))
            self.points2obj.append(objid)

    def remove_obj(self, objid, obj):
        # Use all ptids to delete from index
        for i, pt in enumerate(self.get_points(obj)):
            try:
                self.rti.delete(self.obj2points[objid][i], (pt[0], pt[1], pt[0], pt[1]))
            except IndexError:
                pass

    def nearest(self, pt):
        """
        Will raise StopIteration if no items are found.

        :param pt:
        :return:
        """
        return next(self.rti.nearest(pt, objects=True))

    def intersection(self, pt):
        """
        Will raise StopIteration if no items are found.

        :param pt:
        :return:
        """
        return next(self.rti.intersection(pt, objects=True))


class FlatCAMRTreeStorage(FlatCAMRTree):
    """
    Just like FlatCAMRTree it indexes geometry, but also serves
    as storage for the geometry.
    """

    def __init__(self):
        # super(FlatCAMRTreeStorage, self).__init__()
        super().__init__()

        self.objects = []

        # Optimization attempt!
        self.indexes = {}

    def insert(self, obj):
        self.objects.append(obj)
        idx = len(self.objects) - 1

        # Note: Shapely objects are not hashable any more, although
        # there seem to be plans to re-introduce the feature in
        # version 2.0. For now, we will index using the object's id,
        # but it's important to remember that shapely geometry is
        # mutable, ie. it can be modified to a totally different shape
        # and continue to have the same id.
        # self.indexes[obj] = idx
        self.indexes[id(obj)] = idx

        # super(FlatCAMRTreeStorage, self).insert(idx, obj)
        super().insert(idx, obj)

    # @profile
    def remove(self, obj):
        # See note about self.indexes in insert().
        # objidx = self.indexes[obj]
        objidx = self.indexes[id(obj)]

        # Remove from list
        self.objects[objidx] = None

        # Remove from index
        self.remove_obj(objidx, obj)

    def get_objects(self):
        return (o for o in self.objects if o is not None)

    def nearest(self, pt):
        """
        Returns the nearest matching points and the object
        it belongs to.

        :param pt: Query point.
        :return: (match_x, match_y), Object owner of
          matching point.
        :rtype: tuple
        """
        tidx = super(FlatCAMRTreeStorage, self).nearest(pt)
        return (tidx.bbox[0], tidx.bbox[1]), self.objects[tidx.object]

# class myO:
#     def __init__(self, coords):
#         self.coords = coords
#
#
# def test_rti():
#
#     o1 = myO([(0, 0), (0, 1), (1, 1)])
#     o2 = myO([(2, 0), (2, 1), (2, 1)])
#     o3 = myO([(2, 0), (2, 1), (3, 1)])
#
#     os = [o1, o2]
#
#     idx = FlatCAMRTree()
#
#     for o in range(len(os)):
#         idx.insert(o, os[o])
#
#     print [x.bbox for x in idx.rti.nearest((0, 0), num_results=20, objects=True)]
#
#     idx.remove_obj(0, o1)
#
#     print [x.bbox for x in idx.rti.nearest((0, 0), num_results=20, objects=True)]
#
#     idx.remove_obj(1, o2)
#
#     print [x.bbox for x in idx.rti.nearest((0, 0), num_results=20, objects=True)]
#
#
# def test_rtis():
#
#     o1 = myO([(0, 0), (0, 1), (1, 1)])
#     o2 = myO([(2, 0), (2, 1), (2, 1)])
#     o3 = myO([(2, 0), (2, 1), (3, 1)])
#
#     os = [o1, o2]
#
#     idx = FlatCAMRTreeStorage()
#
#     for o in range(len(os)):
#         idx.insert(os[o])
#
#     #os = None
#     #o1 = None
#     #o2 = None
#
#     print [x.bbox for x in idx.rti.nearest((0, 0), num_results=20, objects=True)]
#
#     idx.remove(idx.nearest((2,0))[1])
#
#     print [x.bbox for x in idx.rti.nearest((0, 0), num_results=20, objects=True)]
#
#     idx.remove(idx.nearest((0,0))[1])
#
#     print [x.bbox for x in idx.rti.nearest((0, 0), num_results=20, objects=True)]
