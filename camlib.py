# ########################################################## ##
# FlatCAM: 2D Post-processing for Manufacturing               #
# http://flatcam.org                                          #
# Author: Juan Pablo Caram (c)                                #
# Date: 2/5/2014                                              #
# MIT Licence                                                 #
# ########################################################## ##


from io import StringIO

import numpy as np
from numpy import arctan2, Inf, array, sqrt, pi, ceil, sin, cos, dot, float32, \
    transpose
from numpy.linalg import solve, norm

import re, sys, os, platform
import math
from copy import deepcopy

import traceback
from decimal import Decimal

from rtree import index as rtindex
from lxml import etree as ET

# See: http://toblerity.org/shapely/manual.html

from shapely.geometry import Polygon, LineString, Point, LinearRing, MultiLineString
from shapely.geometry import MultiPoint, MultiPolygon
from shapely.geometry import box as shply_box
from shapely.ops import cascaded_union, unary_union, polygonize
import shapely.affinity as affinity
from shapely.wkt import loads as sloads
from shapely.wkt import dumps as sdumps
from shapely.geometry.base import BaseGeometry
from shapely.geometry import shape

import collections
from collections import Iterable

import rasterio
from rasterio.features import shapes
import ezdxf

# TODO: Commented for FlatCAM packaging with cx_freeze
# from scipy.spatial import KDTree, Delaunay
# from scipy.spatial import Delaunay

from flatcamParsers.ParseSVG import *
from flatcamParsers.ParseDXF import *

import logging
import FlatCAMApp
import gettext
import FlatCAMTranslation as fcTranslate
import builtins

if platform.architecture()[0] == '64bit':
    from ortools.constraint_solver import pywrapcp
    from ortools.constraint_solver import routing_enums_pb2

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


class Geometry(object):
    """
    Base geometry class.
    """

    defaults = {
        "units": 'in',
        "geo_steps_per_circle": 128
    }

    def __init__(self, geo_steps_per_circle=None):
        # Units (in or mm)
        self.units = Geometry.defaults["units"]
        
        # Final geometry: MultiPolygon or list (of geometry constructs)
        self.solid_geometry = None

        # Final geometry: MultiLineString or list (of LineString or Points)
        self.follow_geometry = None

        # Attributes to be included in serialization
        self.ser_attrs = ["units", 'solid_geometry', 'follow_geometry']

        # Flattened geometry (list of paths only)
        self.flat_geometry = []

        # this is the calculated conversion factor when the file units are different than the ones in the app
        self.file_units_factor = 1

        # Index
        self.index = None

        self.geo_steps_per_circle = geo_steps_per_circle

        # if geo_steps_per_circle is None:
        #     geo_steps_per_circle = int(Geometry.defaults["geo_steps_per_circle"])
        # self.geo_steps_per_circle = geo_steps_per_circle

    def make_index(self):
        self.flatten()
        self.index = FlatCAMRTree()

        for i, g in enumerate(self.flat_geometry):
            self.index.insert(i, g)

    def add_circle(self, origin, radius):
        """
        Adds a circle to the object.

        :param origin: Center of the circle.
        :param radius: Radius of the circle.
        :return: None
        """

        if self.solid_geometry is None:
            self.solid_geometry = []

        if type(self.solid_geometry) is list:
            self.solid_geometry.append(Point(origin).buffer(
                radius, int(int(self.geo_steps_per_circle) / 4)))
            return

        try:
            self.solid_geometry = self.solid_geometry.union(Point(origin).buffer(
                radius, int(int(self.geo_steps_per_circle) / 4)))
        except Exception as e:
            log.error("Failed to run union on polygons. %s" % str(e))
            return

    def add_polygon(self, points):
        """
        Adds a polygon to the object (by union)

        :param points: The vertices of the polygon.
        :return: None
        """
        if self.solid_geometry is None:
            self.solid_geometry = []

        if type(self.solid_geometry) is list:
            self.solid_geometry.append(Polygon(points))
            return

        try:
            self.solid_geometry = self.solid_geometry.union(Polygon(points))
        except Exception as e:
            log.error("Failed to run union on polygons. %s" % str(e))
            return

    def add_polyline(self, points):
        """
        Adds a polyline to the object (by union)

        :param points: The vertices of the polyline.
        :return: None
        """
        if self.solid_geometry is None:
            self.solid_geometry = []

        if type(self.solid_geometry) is list:
            self.solid_geometry.append(LineString(points))
            return

        try:
            self.solid_geometry = self.solid_geometry.union(LineString(points))
        except Exception as e:
            log.error("Failed to run union on polylines. %s" % str(e))
            return

    def is_empty(self):
        if isinstance(self.solid_geometry, BaseGeometry):
            return self.solid_geometry.is_empty

        if isinstance(self.solid_geometry, list):
            return len(self.solid_geometry) == 0

        self.app.inform.emit(_("[ERROR_NOTCL] self.solid_geometry is neither BaseGeometry or list."))
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
        polygon = Polygon(points)
        toolgeo = cascaded_union(polygon)
        diffs = []
        for target in flat_geometry:
            if type(target) == LineString or type(target) == LinearRing:
                diffs.append(target.difference(toolgeo))
            else:
                log.warning("Not implemented.")
        self.solid_geometry = cascaded_union(diffs)

    def bounds(self):
        """
        Returns coordinates of rectangular bounds
        of geometry: (xmin, ymin, xmax, ymax).
        """
        # fixed issue of getting bounds only for one level lists of objects
        # now it can get bounds for nested lists of objects

        log.debug("camlib.Geometry.bounds()")

        if self.solid_geometry is None:
            log.debug("solid_geometry is None")
            return 0, 0, 0, 0

        def bounds_rec(obj):
            if type(obj) is list:
                minx = Inf
                miny = Inf
                maxx = -Inf
                maxy = -Inf

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

        if self.multigeo is True:
            minx_list = []
            miny_list = []
            maxx_list = []
            maxy_list = []

            for tool in self.tools:
                minx, miny, maxx, maxy = bounds_rec(self.tools[tool]['solid_geometry'])
                minx_list.append(minx)
                miny_list.append(miny)
                maxx_list.append(maxx)
                maxy_list.append(maxy)

            return(min(minx_list), min(miny_list), max(maxx_list), max(maxy_list))
        else:
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
        #         # TODO: This can be done faster. See comment from Shapely mailing lists.
        #         if len(self.solid_geometry) == 0:
        #             log.debug('solid_geometry is empty []')
        #             return 0, 0, 0, 0
        #         return cascaded_union(flatten(self.solid_geometry)).bounds
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
        #     # TODO: This can be done faster. See comment from Shapely mailing lists.
        #     if len(self.solid_geometry) == 0:
        #         log.debug('solid_geometry is empty []')
        #         return 0, 0, 0, 0
        #     return cascaded_union(self.solid_geometry).bounds
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

    def isolation_geometry(self, offset, iso_type=2, corner=None, follow=None):
        """
        Creates contours around geometry at a given
        offset distance.

        :param offset: Offset distance.
        :type offset: float
        :param iso_type: type of isolation, can be 0 = exteriors or 1 = interiors or 2 = both (complete)
        :param corner: type of corner for the isolation: 0 = round; 1 = square; 2= beveled (line that connects the ends)
        :param follow: whether the geometry to be isolated is a follow_geometry
        :return: The buffered geometry.
        :rtype: Shapely.MultiPolygon or Shapely.Polygon
        """

        # geo_iso = []
        # In case that the offset value is zero we don't use the buffer as the resulting geometry is actually the
        # original solid_geometry
        # if offset == 0:
        #     geo_iso = self.solid_geometry
        # else:
        #     flattened_geo = self.flatten_list(self.solid_geometry)
        #     try:
        #         for mp_geo in flattened_geo:
        #             geo_iso.append(mp_geo.buffer(offset, int(int(self.geo_steps_per_circle) / 4)))
        #     except TypeError:
        #         geo_iso.append(self.solid_geometry.buffer(offset, int(int(self.geo_steps_per_circle) / 4)))
        # return geo_iso

        # commented this because of the bug with multiple passes cutting out of the copper
        # geo_iso = []
        # flattened_geo = self.flatten_list(self.solid_geometry)
        # try:
        #     for mp_geo in flattened_geo:
        #         geo_iso.append(mp_geo.buffer(offset, int(int(self.geo_steps_per_circle) / 4)))
        # except TypeError:
        #     geo_iso.append(self.solid_geometry.buffer(offset, int(int(self.geo_steps_per_circle) / 4)))

        # the previously commented block is replaced with this block - regression - to solve the bug with multiple
        # isolation passes cutting from the copper features

        geo_iso = []
        if offset == 0:
            if follow:
                geo_iso = self.follow_geometry
            else:
                geo_iso = self.solid_geometry
        else:
            if follow:
                geo_iso = self.follow_geometry
            else:
                if isinstance(self.solid_geometry, list):
                    temp_geo = cascaded_union(self.solid_geometry)
                else:
                    temp_geo = self.solid_geometry

                # Remember: do not make a buffer for each element in the solid_geometry because it will cut into
                # other copper features
                if corner is None:
                    geo_iso = temp_geo.buffer(offset, int(int(self.geo_steps_per_circle) / 4))
                else:
                    geo_iso = temp_geo.buffer(offset, int(int(self.geo_steps_per_circle) / 4),
                                              join_style=corner)

        # end of replaced block
        if follow:
            return geo_iso
        elif iso_type == 2:
            return geo_iso
        elif iso_type == 0:
            return self.get_exteriors(geo_iso)
        elif iso_type == 1:
            return self.get_interiors(geo_iso)
        else:
            log.debug("Geometry.isolation_geometry() --> Type of isolation not supported")
            return "fail"

    def flatten_list(self, list):
        for item in list:
            if isinstance(item, Iterable) and not isinstance(item, (str, bytes)):
                yield from self.flatten_list(item)
            else:
                yield item

    def import_svg(self, filename, object_type=None, flip=True, units='MM'):
        """
        Imports shapes from an SVG file into the object's geometry.

        :param filename: Path to the SVG file.
        :type filename: str
        :param object_type: parameter passed further along
        :param flip: Flip the vertically.
        :type flip: bool
        :param units: FlatCAM units
        :return: None
        """

        # Parse into list of shapely objects
        svg_tree = ET.parse(filename)
        svg_root = svg_tree.getroot()

        # Change origin to bottom left
        # h = float(svg_root.get('height'))
        # w = float(svg_root.get('width'))
        h = svgparselength(svg_root.get('height'))[0]  # TODO: No units support yet
        geos = getsvggeo(svg_root, object_type)
        if flip:
            geos = [translate(scale(g, 1.0, -1.0, origin=(0, 0)), yoff=h) for g in geos]

        # Add to object
        if self.solid_geometry is None:
            self.solid_geometry = []

        if type(self.solid_geometry) is list:
            # self.solid_geometry.append(cascaded_union(geos))
            if type(geos) is list:
                self.solid_geometry += geos
            else:
                self.solid_geometry.append(geos)
        else:  # It's shapely geometry
            # self.solid_geometry = cascaded_union([self.solid_geometry,
            #                                       cascaded_union(geos)])
            self.solid_geometry = [self.solid_geometry, geos]

        # flatten the self.solid_geometry list for import_svg() to import SVG as Gerber
        self.solid_geometry = list(self.flatten_list(self.solid_geometry))

        geos_text = getsvgtext(svg_root, object_type, units=units)
        if geos_text is not None:
            geos_text_f = []
            if flip:
                # Change origin to bottom left
                for i in geos_text:
                    _, minimy, _, maximy = i.bounds
                    h2 = (maximy - minimy) * 0.5
                    geos_text_f.append(translate(scale(i, 1.0, -1.0, origin=(0, 0)), yoff=(h + h2)))
            if geos_text_f:
                self.solid_geometry = self.solid_geometry + geos_text_f

    def import_dxf(self, filename, object_type=None, units='MM'):
        """
        Imports shapes from an DXF file into the object's geometry.

        :param filename: Path to the DXF file.
        :type filename: str
        :param units: Application units
        :type flip: str
        :return: None
        """

        # Parse into list of shapely objects
        dxf = ezdxf.readfile(filename)
        geos = getdxfgeo(dxf)

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

        # flatten the self.solid_geometry list for import_dxf() to import DXF as Gerber
        self.solid_geometry = list(self.flatten_list(self.solid_geometry))
        if self.solid_geometry is not None:
            self.solid_geometry = cascaded_union(self.solid_geometry)
        else:
            return

        # commented until this function is ready
        # geos_text = getdxftext(dxf, object_type, units=units)
        # if geos_text is not None:
        #     geos_text_f = []
        #     self.solid_geometry = [self.solid_geometry, geos_text_f]

    def import_image(self, filename, flip=True, units='MM', dpi=96, mode='black', mask=[128, 128, 128, 128]):
        """
        Imports shapes from an IMAGE file into the object's geometry.

        :param filename: Path to the IMAGE file.
        :type filename: str
        :param flip: Flip the object vertically.
        :type flip: bool
        :param units: FlatCAM units
        :param dpi: dots per inch on the imported image
        :param mode: how to import the image: as 'black' or 'color'
        :param mask: level of detail for the import
        :return: None
        """
        scale_factor = 0.264583333

        if units.lower() == 'mm':
            scale_factor = 25.4 / dpi
        else:
            scale_factor = 1 / dpi

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
            except Exception as e:
                pass

            try:
                blue = src.read(3)
            except Exception as e:
                pass

        if mode == 'black':
            mask_setting = red <= mask[0]
            total = red
            log.debug("Image import as monochrome.")
        else:
            mask_setting = (red <= mask[1]) + (green <= mask[2]) + (blue <= mask[3])
            total = np.zeros(red.shape, dtype=float32)
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
            # self.solid_geometry.append(cascaded_union(geos))
            if type(geos) is list:
                self.solid_geometry += geos
            else:
                self.solid_geometry.append(geos)
        else:  # It's shapely geometry
            self.solid_geometry = [self.solid_geometry, geos]

        # flatten the self.solid_geometry list for import_svg() to import SVG as Gerber
        self.solid_geometry = list(self.flatten_list(self.solid_geometry))
        self.solid_geometry = cascaded_union(self.solid_geometry)

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
        
    @staticmethod
    def clear_polygon(polygon, tooldia, steps_per_circle, overlap=0.15, connect=True, contour=True):
        """
        Creates geometry inside a polygon for a tool to cover
        the whole area.

        This algorithm shrinks the edges of the polygon and takes
        the resulting edges as toolpaths.

        :param polygon: Polygon to clear.
        :param tooldia: Diameter of the tool.
        :param steps_per_circle: number of linear segments to be used to approximate a circle
        :param overlap: Overlap of toolpasses.
        :param connect: Draw lines between disjoint segments to
                        minimize tool lifts.
        :param contour: Paint around the edges. Inconsequential in
                        this painting method.
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
        current = polygon.buffer((-tooldia / 1.999999), int(int(steps_per_circle) / 4))
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

            # Can only result in a Polygon or MultiPolygon
            current = current.buffer(-tooldia * (1 - overlap), int(int(steps_per_circle) / 4))
            if current.area > 0:

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
            else:
                log.debug("camlib.Geometry.clear_polygon() --> Current Area is zero")
                break

        # Optimization: Reduce lifts
        if connect:
            # log.debug("Reducing tool lifts...")
            geoms = Geometry.paint_connect(geoms, polygon, tooldia, int(steps_per_circle))

        return geoms

    @staticmethod
    def clear_polygon2(polygon_to_clear, tooldia, steps_per_circle, seedpoint=None, overlap=0.15,
                       connect=True, contour=True):
        """
        Creates geometry inside a polygon for a tool to cover
        the whole area.

        This algorithm starts with a seed point inside the polygon
        and draws circles around it. Arcs inside the polygons are
        valid cuts. Finalizes by cutting around the inside edge of
        the polygon.

        :param polygon_to_clear: Shapely.geometry.Polygon
        :param steps_per_circle: how many linear segments to use to approximate a circle
        :param tooldia: Diameter of the tool
        :param seedpoint: Shapely.geometry.Point or None
        :param overlap: Tool fraction overlap bewteen passes
        :param connect: Connect disjoint segment to minumize tool lifts
        :param contour: Cut countour inside the polygon.
        :return: List of toolpaths covering polygon.
        :rtype: FlatCAMRTreeStorage | None
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
        path_margin = polygon_to_clear.buffer(-tooldia / 2, int(steps_per_circle / 4))

        if path_margin.is_empty or path_margin is None:
            return

        # Estimate good seedpoint if not provided.
        if seedpoint is None:
            seedpoint = path_margin.representative_point()

        # Grow from seed until outside the box. The polygons will
        # never have an interior, so take the exterior LinearRing.
        while 1:
            path = Point(seedpoint).buffer(radius, int(steps_per_circle / 4)).exterior
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
                except TypeError:
                    geoms.insert(path)

            radius += tooldia * (1 - overlap)

        # Clean inside edges (contours) of the original polygon
        if contour:
            outer_edges = [x.exterior for x in autolist(
                polygon_to_clear.buffer(-tooldia / 2, int(steps_per_circle / 4)))]
            inner_edges = []
            # Over resulting polygons
            for x in autolist(polygon_to_clear.buffer(-tooldia / 2, int(steps_per_circle / 4))):
                for y in x.interiors:  # Over interiors of each polygon
                    inner_edges.append(y)
            # geoms += outer_edges + inner_edges
            for g in outer_edges + inner_edges:
                geoms.insert(g)

        # Optimization connect touching paths
        # log.debug("Connecting paths...")
        # geoms = Geometry.path_connect(geoms)

        # Optimization: Reduce lifts
        if connect:
            # log.debug("Reducing tool lifts...")
            geoms = Geometry.paint_connect(geoms, polygon_to_clear, tooldia, steps_per_circle)

        return geoms

    @staticmethod
    def clear_polygon3(polygon, tooldia, steps_per_circle, overlap=0.15, connect=True, contour=True):
        """
        Creates geometry inside a polygon for a tool to cover
        the whole area.

        This algorithm draws horizontal lines inside the polygon.

        :param polygon: The polygon being painted.
        :type polygon: shapely.geometry.Polygon
        :param tooldia: Tool diameter.
        :param steps_per_circle: how many linear segments to use to approximate a circle
        :param overlap: Tool path overlap percentage.
        :param connect: Connect lines to avoid tool lifts.
        :param contour: Paint around the edges.
        :return:
        """

        # log.debug("camlib.clear_polygon3()")

        # ## The toolpaths
        # Index first and last points in paths
        def get_pts(o):
            return [o.coords[0], o.coords[-1]]

        geoms = FlatCAMRTreeStorage()
        geoms.get_points = get_pts

        lines = []

        # Bounding box
        left, bot, right, top = polygon.bounds

        # First line
        y = top - tooldia / 1.99999999
        while y > bot + tooldia / 1.999999999:
            line = LineString([(left, y), (right, y)])
            lines.append(line)
            y -= tooldia * (1 - overlap)

        # Last line
        y = bot + tooldia / 2
        line = LineString([(left, y), (right, y)])
        lines.append(line)

        # Combine
        linesgeo = unary_union(lines)

        # Trim to the polygon
        margin_poly = polygon.buffer(-tooldia / 1.99999999, (int(steps_per_circle)))
        lines_trimmed = linesgeo.intersection(margin_poly)

        # Add lines to storage
        try:
            for line in lines_trimmed:
                geoms.insert(line)
        except TypeError:
            # in case lines_trimmed are not iterable (Linestring, LinearRing)
            geoms.insert(lines_trimmed)

        # Add margin (contour) to storage
        if contour:
            if isinstance(margin_poly, Polygon):
                geoms.insert(margin_poly.exterior)
                for ints in margin_poly.interiors:
                    geoms.insert(ints)
            elif isinstance(margin_poly, MultiPolygon):
                for poly in margin_poly:
                    geoms.insert(poly.exterior)
                    for ints in poly.interiors:
                        geoms.insert(ints)

        # Optimization: Reduce lifts
        if connect:
            # log.debug("Reducing tool lifts...")
            geoms = Geometry.paint_connect(geoms, polygon, tooldia, steps_per_circle)

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
        #     if shape is not None:  # TODO: This shouldn't have happened.
        #         # Make LlinearRings into linestrings otherwise
        #         # When chaining the coordinates path is messed up.
        #         storage.insert(LineString(shape))
        #         #storage.insert(shape)

        # ## Iterate over geometry paths getting the nearest each time.
        #optimized_paths = []
        optimized_paths = FlatCAMRTreeStorage()
        optimized_paths.get_points = get_pts
        path_count = 0
        current_pt = (0, 0)
        pt, geo = storage.nearest(current_pt)
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
                    candidate.coords = list(candidate.coords)[::-1]

                # Straight line from current_pt to pt.
                # Is the toolpath inside the geometry?
                walk_path = LineString([current_pt, pt])
                walk_cut = walk_path.buffer(tooldia / 2, int(steps_per_circle / 4))

                if walk_cut.within(boundary) and walk_path.length < max_walk:
                    # log.debug("Walk to path #%d is inside. Joining." % path_count)

                    # Completely inside. Append...
                    geo.coords = list(geo.coords) + list(candidate.coords)
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
        connecting paths that touch on their enpoints.

        :param storage: Storage containing the initial paths.
        :rtype storage: FlatCAMRTreeStorage
        :return: Simplified storage.
        :rtype: FlatCAMRTreeStorage
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
        #     if shape is not None:  # TODO: This shouldn't have happened.
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
                        geo.coords = list(geo.coords)[::-1] + list(left.coords)
                        continue

                    if left.coords[-1] == geo.coords[0]:
                        storage.remove(left)
                        geo.coords = list(left.coords) + list(geo.coords)
                        continue

                    if left.coords[0] == geo.coords[-1]:
                        storage.remove(left)
                        geo.coords = list(geo.coords) + list(left.coords)
                        continue

                    if left.coords[-1] == geo.coords[-1]:
                        storage.remove(left)
                        geo.coords = list(geo.coords) + list(left.coords)[::-1]
                        continue

                _, right = storage.nearest(geo.coords[-1])

                # If right touches geo, remove left from original
                # storage and append to geo.
                if type(right) == LineString:
                    if right.coords[0] == geo.coords[-1]:
                        storage.remove(right)
                        geo.coords = list(geo.coords) + list(right.coords)
                        continue

                    if right.coords[-1] == geo.coords[-1]:
                        storage.remove(right)
                        geo.coords = list(geo.coords) + list(right.coords)[::-1]
                        continue

                    if right.coords[0] == geo.coords[0]:
                        storage.remove(right)
                        geo.coords = list(geo.coords)[::-1] + list(right.coords)
                        continue

                    if right.coords[-1] == geo.coords[0]:
                        storage.remove(right)
                        geo.coords = list(left.coords) + list(geo.coords)
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

    def convert_units(self, units):
        """
        Converts the units of the object to ``units`` by scaling all
        the geometry appropriately. This call ``scale()``. Don't call
        it again in descendents.

        :param units: "IN" or "MM"
        :type units: str
        :return: Scaling factor resulting from unit change.
        :rtype: float
        """
        log.debug("camlib.Geometry.convert_units()")

        if units.upper() == self.units.upper():
            return 1.0

        if units.upper() == "MM":
            factor = 25.4
        elif units.upper() == "IN":
            factor = 1 / 25.4
        else:
            log.error("Unsupported units: %s" % str(units))
            return 1.0

        self.units = units
        self.scale(factor, factor)
        self.file_units_factor = factor
        return factor

    def to_dict(self):
        """
        Returns a representation of the object as a dictionary.
        Attributes to include are listed in ``self.ser_attrs``.

        :return: A dictionary-encoded copy of the object.
        :rtype: dict
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

        :param d: Dictionary of attributes to set in the object.
        :type d: dict
        :return: None
        """
        for attr in self.ser_attrs:
            setattr(self, attr, d[attr])

    def union(self):
        """
        Runs a cascaded union on the list of objects in
        solid_geometry.

        :return: None
        """
        self.solid_geometry = [cascaded_union(self.solid_geometry)]

    def export_svg(self, scale_factor=0.00):
        """
        Exports the Geometry Object as a SVG Element

        :return: SVG Element
        """

        # Make sure we see a Shapely Geometry class and not a list

        if str(type(self)) == "<class 'FlatCAMObj.FlatCAMGeometry'>":
            flat_geo = []
            if self.multigeo:
                for tool in self.tools:
                    flat_geo += self.flatten(self.tools[tool]['solid_geometry'])
                geom = cascaded_union(flat_geo)
            else:
                geom = cascaded_union(self.flatten())
        else:
            geom = cascaded_union(self.flatten())

        # scale_factor is a multiplication factor for the SVG stroke-width used within shapely's svg export

        # If 0 or less which is invalid then default to 0.05
        # This value appears to work for zooming, and getting the output svg line width
        # to match that viewed on screen with FlatCam
        # MS: I choose a factor of 0.01 so the scale is right for PCB UV film
        if scale_factor <= 0:
            scale_factor = 0.01

        # Convert to a SVG
        svg_elem = geom.svg(scale_factor=scale_factor)
        return svg_elem

    def mirror(self, axis, point):
        """
        Mirrors the object around a specified axis passign through
        the given point.

        :param axis: "X" or "Y" indicates around which axis to mirror.
        :type axis: str
        :param point: [x, y] point belonging to the mirror axis.
        :type point: list
        :return: None
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
                    return affinity.scale(obj, xscale, yscale, origin=(px, py))
                except AttributeError:
                    return obj

        try:
            if self.multigeo is True:
                for tool in self.tools:
                    self.tools[tool]['solid_geometry'] = mirror_geom(self.tools[tool]['solid_geometry'])
            else:
                self.solid_geometry = mirror_geom(self.solid_geometry)
            self.app.inform.emit(_('[success] Object was mirrored ...'))
        except AttributeError:
            self.app.inform.emit(_("[ERROR_NOTCL] Failed to mirror. No object selected"))

    def rotate(self, angle, point):
        """
        Rotate an object by an angle (in degrees) around the provided coordinates.

        Parameters
        ----------
        The angle of rotation are specified in degrees (default). Positive angles are
        counter-clockwise and negative are clockwise rotations.

        The point of origin can be a keyword 'center' for the bounding box
        center (default), 'centroid' for the geometry's centroid, a Point object
        or a coordinate tuple (x0, y0).

        See shapely manual for more information:
        http://toblerity.org/shapely/manual.html#affine-transformations
        """
        log.debug("camlib.Geometry.rotate()")

        px, py = point

        def rotate_geom(obj):
            if type(obj) is list:
                new_obj = []
                for g in obj:
                    new_obj.append(rotate_geom(g))
                return new_obj
            else:
                try:
                    return affinity.rotate(obj, angle, origin=(px, py))
                except AttributeError:
                    return obj

        try:
            if self.multigeo is True:
                for tool in self.tools:
                    self.tools[tool]['solid_geometry'] = rotate_geom(self.tools[tool]['solid_geometry'])
            else:
                self.solid_geometry = rotate_geom(self.solid_geometry)
            self.app.inform.emit(_('[success] Object was rotated ...'))
        except AttributeError:
            self.app.inform.emit(_("[ERROR_NOTCL] Failed to rotate. No object selected"))

    def skew(self, angle_x, angle_y, point):
        """
        Shear/Skew the geometries of an object by angles along x and y dimensions.

        Parameters
        ----------
        angle_x, angle_y : float, float
            The shear angle(s) for the x and y axes respectively. These can be
            specified in either degrees (default) or radians by setting
            use_radians=True.
        point: tuple of coordinates (x,y)

        See shapely manual for more information:
        http://toblerity.org/shapely/manual.html#affine-transformations
        """
        log.debug("camlib.Geometry.skew()")

        px, py = point

        def skew_geom(obj):
            if type(obj) is list:
                new_obj = []
                for g in obj:
                    new_obj.append(skew_geom(g))
                return new_obj
            else:
                try:
                    return affinity.skew(obj, angle_x, angle_y, origin=(px, py))
                except AttributeError:
                    return obj

        try:
            if self.multigeo is True:
                for tool in self.tools:
                    self.tools[tool]['solid_geometry'] = skew_geom(self.tools[tool]['solid_geometry'])
            else:
                self.solid_geometry = skew_geom(self.solid_geometry)
            self.app.inform.emit(_('[success] Object was skewed ...'))
        except AttributeError:
            self.app.inform.emit(_("[ERROR_NOTCL] Failed to skew. No object selected"))

        # if type(self.solid_geometry) == list:
        #     self.solid_geometry = [affinity.skew(g, angle_x, angle_y, origin=(px, py))
        #                            for g in self.solid_geometry]
        # else:
        #     self.solid_geometry = affinity.skew(self.solid_geometry, angle_x, angle_y,
        #                                         origin=(px, py))


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
            # numerical constant or defind in terms of previously define
            # variables, which can be defined locally or in an aperture
            # definition. All replacements ocurr here.
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

        :param n: Length of the resulting list.
        :type n: int
        :param mods: List to be padded.
        :type mods: list
        :return: Zero-padded list.
        :rtype: list
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

        pol, dia, x, y = ApertureMacro.default2zero(4, mods)

        return {"pol": int(pol), "geometry": Point(x, y).buffer(dia/2)}

    @staticmethod
    def make_vectorline(mods):
        """

        :param mods: (Exposure 0/1, Line width >= 0, X-start, Y-start, X-end, Y-end,
            rotation angle around origin in degrees)
        :return:
        """
        pol, width, xs, ys, xe, ye, angle = ApertureMacro.default2zero(7, mods)

        line = LineString([(xs, ys), (xe, ye)])
        box = line.buffer(width/2, cap_style=2)
        box_rotated = affinity.rotate(box, angle, origin=(0, 0))

        return {"pol": int(pol), "geometry": box_rotated}

    @staticmethod
    def make_centerline(mods):
        """

        :param mods: (Exposure 0/1, width >=0, height >=0, x-center, y-center,
            rotation angle around origin in degrees)
        :return:
        """

        pol, width, height, x, y, angle = ApertureMacro.default2zero(6, mods)

        box = shply_box(x-width/2, y-height/2, x+width/2, y+height/2)
        box_rotated = affinity.rotate(box, angle, origin=(0, 0))

        return {"pol": int(pol), "geometry": box_rotated}

    @staticmethod
    def make_lowerleftline(mods):
        """

        :param mods: (exposure 0/1, width >=0, height >=0, x-lowerleft, y-lowerleft,
            rotation angle around origin in degrees)
        :return:
        """

        pol, width, height, x, y, angle = ApertureMacro.default2zero(6, mods)

        box = shply_box(x, y, x+width, y+height)
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
        points = [(0, 0)]*(n+1)

        for i in range(n+1):
            points[i] = mods[2*i + 2:2*i + 4]

        angle = mods[2*n + 4]

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

        pol, nverts, x, y, dia, angle = ApertureMacro.default2zero(6, mods)
        points = [(0, 0)]*nverts

        for i in range(nverts):
            points[i] = (x + 0.5 * dia * cos(2*pi * i/nverts),
                         y + 0.5 * dia * sin(2*pi * i/nverts))

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

        x, y, dia, thickness, gap, nrings, cross_th, cross_len, angle = ApertureMacro.default2zero(9, mods)

        r = dia/2 - thickness/2
        result = Point((x, y)).buffer(r).exterior.buffer(thickness/2.0)
        ring = Point((x, y)).buffer(r).exterior.buffer(thickness/2.0)  # Need a copy!

        i = 1  # Number of rings created so far

        # ## If the ring does not have an interior it means that it is
        # ## a disk. Then stop.
        while len(ring.interiors) > 0 and i < nrings:
            r -= thickness + gap
            if r <= 0:
                break
            ring = Point((x, y)).buffer(r).exterior.buffer(thickness/2.0)
            result = cascaded_union([result, ring])
            i += 1

        # ## Crosshair
        hor = LineString([(x - cross_len, y), (x + cross_len, y)]).buffer(cross_th/2.0, cap_style=2)
        ver = LineString([(x, y-cross_len), (x, y + cross_len)]).buffer(cross_th/2.0, cap_style=2)
        result = cascaded_union([result, hor, ver])

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

        x, y, dout, din, t, angle = ApertureMacro.default2zero(6, mods)

        ring = Point((x, y)).buffer(dout/2.0).difference(Point((x, y)).buffer(din/2.0))
        hline = LineString([(x - dout/2.0, y), (x + dout/2.0, y)]).buffer(t/2.0, cap_style=3)
        vline = LineString([(x, y - dout/2.0), (x, y + dout/2.0)]).buffer(t/2.0, cap_style=3)
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


class Gerber (Geometry):
    """
    Here it is done all the Gerber parsing.

    **ATTRIBUTES**

    * ``apertures`` (dict): The keys are names/identifiers of each aperture.
      The values are dictionaries key/value pairs which describe the aperture. The
      type key is always present and the rest depend on the key:

    +-----------+-----------------------------------+
    | Key       | Value                             |
    +===========+===================================+
    | type      | (str) "C", "R", "O", "P", or "AP" |
    +-----------+-----------------------------------+
    | others    | Depend on ``type``                |
    +-----------+-----------------------------------+
    | solid_geometry      | (list)                  |
    +-----------+-----------------------------------+
    * ``aperture_macros`` (dictionary): Are predefined geometrical structures
      that can be instantiated with different parameters in an aperture
      definition. See ``apertures`` above. The key is the name of the macro,
      and the macro itself, the value, is a ``Aperture_Macro`` object.

    * ``flash_geometry`` (list): List of (Shapely) geometric object resulting
      from ``flashes``. These are generated from ``flashes`` in ``do_flashes()``.

    * ``buffered_paths`` (list): List of (Shapely) polygons resulting from
      *buffering* (or thickening) the ``paths`` with the aperture. These are
      generated from ``paths`` in ``buffer_paths()``.

    **USAGE**::

        g = Gerber()
        g.parse_file(filename)
        g.create_geometry()
        do_something(s.solid_geometry)

    """

    # defaults = {
    #     "steps_per_circle": 128,
    #     "use_buffer_for_union": True
    # }

    def __init__(self, steps_per_circle=None):
        """
        The constructor takes no parameters. Use ``gerber.parse_files()``
        or ``gerber.parse_lines()`` to populate the object from Gerber source.

        :return: Gerber object
        :rtype: Gerber
        """

        # How to approximate a circle with lines.
        self.steps_per_circle = int(self.app.defaults["gerber_circle_steps"])

        # Initialize parent
        Geometry.__init__(self, geo_steps_per_circle=int(self.app.defaults["gerber_circle_steps"]))

        # Number format
        self.int_digits = 3
        """Number of integer digits in Gerber numbers. Used during parsing."""

        self.frac_digits = 4
        """Number of fraction digits in Gerber numbers. Used during parsing."""

        self.gerber_zeros = 'L'
        """Zeros in Gerber numbers. If 'L' then remove leading zeros, if 'T' remove trailing zeros. Used during parsing.
        """

        # ## Gerber elements # ##
        '''
        apertures = {
            'id':{
                'type':string, 
                'size':float, 
                'width':float,
                'height':float,
                'geometry': [],
            }
        }
        apertures['geometry'] list elements are dicts
        dict = {
            'solid': [],
            'follow': [],
            'clear': []
        }
        '''

        # store the file units here:
        self.gerber_units = 'IN'

        # aperture storage
        self.apertures = {}

        # Aperture Macros
        self.aperture_macros = {}

        # will store the Gerber geometry's as solids
        self.solid_geometry = Polygon()

        # will store the Gerber geometry's as paths
        self.follow_geometry = []

        # made True when the LPC command is encountered in Gerber parsing
        # it allows adding data into the clear_geometry key of the self.apertures[aperture] dict
        self.is_lpc = False

        self.source_file = ''

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from Geometry.
        self.ser_attrs += ['int_digits', 'frac_digits', 'apertures',
                           'aperture_macros', 'solid_geometry', 'source_file']

        # ### Parser patterns ## ##
        # FS - Format Specification
        # The format of X and Y must be the same!
        # L-omit leading zeros, T-omit trailing zeros, D-no zero supression
        # A-absolute notation, I-incremental notation
        self.fmt_re = re.compile(r'%?FS([LTD])([AI])X(\d)(\d)Y\d\d\*%?$')
        self.fmt_re_alt = re.compile(r'%FS([LT])([AI])X(\d)(\d)Y\d\d\*MO(IN|MM)\*%$')
        self.fmt_re_orcad = re.compile(r'(G\d+)*\**%FS([LT])([AI]).*X(\d)(\d)Y\d\d\*%$')

        # Mode (IN/MM)
        self.mode_re = re.compile(r'^%?MO(IN|MM)\*%?$')

        # Comment G04|G4
        self.comm_re = re.compile(r'^G0?4(.*)$')

        # AD - Aperture definition
        # Aperture Macro names: Name = [a-zA-Z_.$]{[a-zA-Z_.0-9]+}
        # NOTE: Adding "-" to support output from Upverter.
        self.ad_re = re.compile(r'^%ADD(\d\d+)([a-zA-Z_$\.][a-zA-Z0-9_$\.\-]*)(?:,(.*))?\*%$')

        # AM - Aperture Macro
        # Beginning of macro (Ends with *%):
        # self.am_re = re.compile(r'^%AM([a-zA-Z0-9]*)\*')

        # Tool change
        # May begin with G54 but that is deprecated
        self.tool_re = re.compile(r'^(?:G54)?D(\d\d+)\*$')

        # G01... - Linear interpolation plus flashes with coordinates
        # Operation code (D0x) missing is deprecated... oh well I will support it.
        self.lin_re = re.compile(r'^(?:G0?(1))?(?=.*X([\+-]?\d+))?(?=.*Y([\+-]?\d+))?[XY][^DIJ]*(?:D0?([123]))?\*$')

        # Operation code alone, usually just D03 (Flash)
        self.opcode_re = re.compile(r'^D0?([123])\*$')

        # G02/3... - Circular interpolation with coordinates
        # 2-clockwise, 3-counterclockwise
        # Operation code (D0x) missing is deprecated... oh well I will support it.
        # Optional start with G02 or G03, optional end with D01 or D02 with
        # optional coordinates but at least one in any order.
        self.circ_re = re.compile(r'^(?:G0?([23]))?(?=.*X([\+-]?\d+))?(?=.*Y([\+-]?\d+))' +
                                  '?(?=.*I([\+-]?\d+))?(?=.*J([\+-]?\d+))?[XYIJ][^D]*(?:D0([12]))?\*$')

        # G01/2/3 Occurring without coordinates
        self.interp_re = re.compile(r'^(?:G0?([123]))\*')

        # Single G74 or multi G75 quadrant for circular interpolation
        self.quad_re = re.compile(r'^G7([45]).*\*$')

        # Region mode on
        # In region mode, D01 starts a region
        # and D02 ends it. A new region can be started again
        # with D01. All contours must be closed before
        # D02 or G37.
        self.regionon_re = re.compile(r'^G36\*$')

        # Region mode off
        # Will end a region and come off region mode.
        # All contours must be closed before D02 or G37.
        self.regionoff_re = re.compile(r'^G37\*$')

        # End of file
        self.eof_re = re.compile(r'^M02\*')

        # IP - Image polarity
        self.pol_re = re.compile(r'^%?IP(POS|NEG)\*%?$')

        # LP - Level polarity
        self.lpol_re = re.compile(r'^%LP([DC])\*%$')

        # Units (OBSOLETE)
        self.units_re = re.compile(r'^G7([01])\*$')

        # Absolute/Relative G90/1 (OBSOLETE)
        self.absrel_re = re.compile(r'^G9([01])\*$')

        # Aperture macros
        self.am1_re = re.compile(r'^%AM([^\*]+)\*([^%]+)?(%)?$')
        self.am2_re = re.compile(r'(.*)%$')

        self.use_buffer_for_union = self.app.defaults["gerber_use_buffer_for_union"]

    def aperture_parse(self, apertureId, apertureType, apParameters):
        """
        Parse gerber aperture definition into dictionary of apertures.
        The following kinds and their attributes are supported:

        * *Circular (C)*: size (float)
        * *Rectangle (R)*: width (float), height (float)
        * *Obround (O)*: width (float), height (float).
        * *Polygon (P)*: diameter(float), vertices(int), [rotation(float)]
        * *Aperture Macro (AM)*: macro (ApertureMacro), modifiers (list)

        :param apertureId: Id of the aperture being defined.
        :param apertureType: Type of the aperture.
        :param apParameters: Parameters of the aperture.
        :type apertureId: str
        :type apertureType: str
        :type apParameters: str
        :return: Identifier of the aperture.
        :rtype: str
        """

        # Found some Gerber with a leading zero in the aperture id and the
        # referenced it without the zero, so this is a hack to handle that.
        apid = str(int(apertureId))

        try:  # Could be empty for aperture macros
            paramList = apParameters.split('X')
        except:
            paramList = None

        if apertureType == "C":  # Circle, example: %ADD11C,0.1*%
            self.apertures[apid] = {"type": "C",
                                    "size": float(paramList[0])}
            return apid
        
        if apertureType == "R":  # Rectangle, example: %ADD15R,0.05X0.12*%
            self.apertures[apid] = {"type": "R",
                                    "width": float(paramList[0]),
                                    "height": float(paramList[1]),
                                    "size": sqrt(float(paramList[0])**2 + float(paramList[1])**2)}  # Hack
            return apid

        if apertureType == "O":  # Obround
            self.apertures[apid] = {"type": "O",
                                    "width": float(paramList[0]),
                                    "height": float(paramList[1]),
                                    "size": sqrt(float(paramList[0])**2 + float(paramList[1])**2)}  # Hack
            return apid
        
        if apertureType == "P":  # Polygon (regular)
            self.apertures[apid] = {"type": "P",
                                    "diam": float(paramList[0]),
                                    "nVertices": int(paramList[1]),
                                    "size": float(paramList[0])}  # Hack
            if len(paramList) >= 3:
                self.apertures[apid]["rotation"] = float(paramList[2])
            return apid

        if apertureType in self.aperture_macros:
            self.apertures[apid] = {"type": "AM",
                                    "macro": self.aperture_macros[apertureType],
                                    "modifiers": paramList}
            return apid

        log.warning("Aperture not implemented: %s" % str(apertureType))
        return None
        
    def parse_file(self, filename, follow=False):
        """
        Calls Gerber.parse_lines() with generator of lines
        read from the given file. Will split the lines if multiple
        statements are found in a single original line.

        The following line is split into two::

            G54D11*G36*

        First is ``G54D11*`` and seconds is ``G36*``.

        :param filename: Gerber file to parse.
        :type filename: str
        :param follow: If true, will not create polygons, just lines
            following the gerber path.
        :type follow: bool
        :return: None
        """

        with open(filename, 'r') as gfile:

            def line_generator():
                for line in gfile:
                    line = line.strip(' \r\n')
                    while len(line) > 0:

                        # If ends with '%' leave as is.
                        if line[-1] == '%':
                            yield line
                            break

                        # Split after '*' if any.
                        starpos = line.find('*')
                        if starpos > -1:
                            cleanline = line[:starpos + 1]
                            yield cleanline
                            line = line[starpos + 1:]

                        # Otherwise leave as is.
                        else:
                            # yield clean line
                            yield line
                            break

            processed_lines = list(line_generator())
            self.parse_lines(processed_lines)

    # @profile
    def parse_lines(self, glines):
        """
        Main Gerber parser. Reads Gerber and populates ``self.paths``, ``self.apertures``,
        ``self.flashes``, ``self.regions`` and ``self.units``.

        :param glines: Gerber code as list of strings, each element being
            one line of the source file.
        :type glines: list
        :return: None
        :rtype: None
        """

        # Coordinates of the current path, each is [x, y]
        path = []

        # store the file units here:
        self.gerber_units = 'IN'

        # this is for temporary storage of solid geometry until it is added to poly_buffer
        geo_s = None

        # this is for temporary storage of follow geometry until it is added to follow_buffer
        geo_f = None

        # Polygons are stored here until there is a change in polarity.
        # Only then they are combined via cascaded_union and added or
        # subtracted from solid_geometry. This is ~100 times faster than
        # applying a union for every new polygon.
        poly_buffer = []

        # store here the follow geometry
        follow_buffer = []

        last_path_aperture = None
        current_aperture = None

        # 1,2 or 3 from "G01", "G02" or "G03"
        current_interpolation_mode = None

        # 1 or 2 from "D01" or "D02"
        # Note this is to support deprecated Gerber not putting
        # an operation code at the end of every coordinate line.
        current_operation_code = None

        # Current coordinates
        current_x = None
        current_y = None
        previous_x = None
        previous_y = None

        current_d = None

        # Absolute or Relative/Incremental coordinates
        # Not implemented
        absolute = True

        # How to interpret circular interpolation: SINGLE or MULTI
        quadrant_mode = None

        # Indicates we are parsing an aperture macro
        current_macro = None

        # Indicates the current polarity: D-Dark, C-Clear
        current_polarity = 'D'

        # If a region is being defined
        making_region = False

        # ### Parsing starts here ## ##
        line_num = 0
        gline = ""
        try:
            for gline in glines:
                line_num += 1
                self.source_file += gline + '\n'

                # Cleanup #
                gline = gline.strip(' \r\n')
                # log.debug("Line=%3s %s" % (line_num, gline))

                # ###################
                # Ignored lines #####
                # Comments      #####
                # ###################
                match = self.comm_re.search(gline)
                if match:
                    continue

                # Polarity change ###### ##
                # Example: %LPD*% or %LPC*%
                # If polarity changes, creates geometry from current
                # buffer, then adds or subtracts accordingly.
                match = self.lpol_re.search(gline)
                if match:
                    new_polarity = match.group(1)
                    # log.info("Polarity CHANGE, LPC = %s, poly_buff = %s" % (self.is_lpc, poly_buffer))
                    self.is_lpc = True if new_polarity == 'C' else False
                    if len(path) > 1 and current_polarity != new_polarity:

                        # finish the current path and add it to the storage
                        # --- Buffered ----
                        width = self.apertures[last_path_aperture]["size"]

                        geo_dict = dict()
                        geo_f = LineString(path)
                        if not geo_f.is_empty:
                            follow_buffer.append(geo_f)
                            geo_dict['follow'] = geo_f

                        geo_s = LineString(path).buffer(width / 1.999, int(self.steps_per_circle / 4))
                        if not geo_s.is_empty:
                            poly_buffer.append(geo_s)
                            if self.is_lpc is True:
                                geo_dict['clear'] = geo_s
                            else:
                                geo_dict['solid'] = geo_s

                        if last_path_aperture not in self.apertures:
                            self.apertures[last_path_aperture] = dict()
                        if 'geometry' not in self.apertures[last_path_aperture]:
                            self.apertures[last_path_aperture]['geometry'] = []
                        self.apertures[last_path_aperture]['geometry'].append(deepcopy(geo_dict))

                        path = [path[-1]]

                    # --- Apply buffer ---
                    # If added for testing of bug #83
                    # TODO: Remove when bug fixed
                    if len(poly_buffer) > 0:
                        if current_polarity == 'D':
                            # self.follow_geometry = self.follow_geometry.union(cascaded_union(follow_buffer))
                            self.solid_geometry = self.solid_geometry.union(cascaded_union(poly_buffer))

                        else:
                            # self.follow_geometry = self.follow_geometry.difference(cascaded_union(follow_buffer))
                            self.solid_geometry = self.solid_geometry.difference(cascaded_union(poly_buffer))

                        # follow_buffer = []
                        poly_buffer = []

                    current_polarity = new_polarity
                    continue

                # ############################################################# ##
                # Number format ############################################### ##
                # Example: %FSLAX24Y24*%
                # ############################################################# ##
                # TODO: This is ignoring most of the format. Implement the rest.
                match = self.fmt_re.search(gline)
                if match:
                    absolute = {'A': 'Absolute', 'I': 'Relative'}[match.group(2)]
                    self.gerber_zeros = match.group(1)
                    self.int_digits = int(match.group(3))
                    self.frac_digits = int(match.group(4))
                    log.debug("Gerber format found. (%s) " % str(gline))

                    log.debug(
                        "Gerber format found. Gerber zeros = %s (L-omit leading zeros, T-omit trailing zeros, "
                        "D-no zero supression)" % self.gerber_zeros)
                    log.debug("Gerber format found. Coordinates type = %s (Absolute or Relative)" % absolute)
                    continue

                # ## Mode (IN/MM)
                # Example: %MOIN*%
                match = self.mode_re.search(gline)
                if match:
                    self.gerber_units = match.group(1)
                    log.debug("Gerber units found = %s" % self.gerber_units)
                    # Changed for issue #80
                    self.convert_units(match.group(1))
                    continue

                # ############################################################# ##
                # Combined Number format and Mode --- Allegro does this ####### ##
                # ############################################################# ##
                match = self.fmt_re_alt.search(gline)
                if match:
                    absolute = {'A': 'Absolute', 'I': 'Relative'}[match.group(2)]
                    self.gerber_zeros = match.group(1)
                    self.int_digits = int(match.group(3))
                    self.frac_digits = int(match.group(4))
                    log.debug("Gerber format found. (%s) " % str(gline))
                    log.debug(
                        "Gerber format found. Gerber zeros = %s (L-omit leading zeros, T-omit trailing zeros, "
                        "D-no zero suppression)" % self.gerber_zeros)
                    log.debug("Gerber format found. Coordinates type = %s (Absolute or Relative)" % absolute)

                    self.gerber_units = match.group(5)
                    log.debug("Gerber units found = %s" % self.gerber_units)
                    # Changed for issue #80
                    self.convert_units(match.group(5))
                    continue

                # ############################################################# ##
                # Search for OrCAD way for having Number format
                # ############################################################# ##
                match = self.fmt_re_orcad.search(gline)
                if match:
                    if match.group(1) is not None:
                        if match.group(1) == 'G74':
                            quadrant_mode = 'SINGLE'
                        elif match.group(1) == 'G75':
                            quadrant_mode = 'MULTI'
                        absolute = {'A': 'Absolute', 'I': 'Relative'}[match.group(3)]
                        self.gerber_zeros = match.group(2)
                        self.int_digits = int(match.group(4))
                        self.frac_digits = int(match.group(5))
                        log.debug("Gerber format found. (%s) " % str(gline))
                        log.debug(
                            "Gerber format found. Gerber zeros = %s (L-omit leading zeros, T-omit trailing zeros, "
                            "D-no zerosuppressionn)" % self.gerber_zeros)
                        log.debug("Gerber format found. Coordinates type = %s (Absolute or Relative)" % absolute)

                        self.gerber_units = match.group(1)
                        log.debug("Gerber units found = %s" % self.gerber_units)
                        # Changed for issue #80
                        self.convert_units(match.group(5))
                        continue

                # ############################################################# ##
                # Units (G70/1) OBSOLETE
                # ############################################################# ##
                match = self.units_re.search(gline)
                if match:
                    obs_gerber_units = {'0': 'IN', '1': 'MM'}[match.group(1)]
                    log.warning("Gerber obsolete units found = %s" % obs_gerber_units)
                    # Changed for issue #80
                    self.convert_units({'0': 'IN', '1': 'MM'}[match.group(1)])
                    continue

                # ############################################################# ##
                # Absolute/relative coordinates G90/1 OBSOLETE ######## ##
                # ##################################################### ##
                match = self.absrel_re.search(gline)
                if match:
                    absolute = {'0': "Absolute", '1': "Relative"}[match.group(1)]
                    log.warning("Gerber obsolete coordinates type found = %s (Absolute or Relative) " % absolute)
                    continue

                # ############################################################# ##
                # Aperture Macros ##################################### ##
                # Having this at the beginning will slow things down
                # but macros can have complicated statements than could
                # be caught by other patterns.
                # ############################################################# ##
                if current_macro is None:  # No macro started yet
                    match = self.am1_re.search(gline)
                    # Start macro if match, else not an AM, carry on.
                    if match:
                        log.debug("Starting macro. Line %d: %s" % (line_num, gline))
                        current_macro = match.group(1)
                        self.aperture_macros[current_macro] = ApertureMacro(name=current_macro)
                        if match.group(2):  # Append
                            self.aperture_macros[current_macro].append(match.group(2))
                        if match.group(3):  # Finish macro
                            # self.aperture_macros[current_macro].parse_content()
                            current_macro = None
                            log.debug("Macro complete in 1 line.")
                        continue
                else:  # Continue macro
                    log.debug("Continuing macro. Line %d." % line_num)
                    match = self.am2_re.search(gline)
                    if match:  # Finish macro
                        log.debug("End of macro. Line %d." % line_num)
                        self.aperture_macros[current_macro].append(match.group(1))
                        # self.aperture_macros[current_macro].parse_content()
                        current_macro = None
                    else:  # Append
                        self.aperture_macros[current_macro].append(gline)
                    continue

                # ## Aperture definitions %ADD...
                match = self.ad_re.search(gline)
                if match:
                    # log.info("Found aperture definition. Line %d: %s" % (line_num, gline))
                    self.aperture_parse(match.group(1), match.group(2), match.group(3))
                    continue

                # ############################################################# ##
                # Operation code alone ###################### ##
                # Operation code alone, usually just D03 (Flash)
                # self.opcode_re = re.compile(r'^D0?([123])\*$')
                # ############################################################# ##
                match = self.opcode_re.search(gline)
                if match:
                    current_operation_code = int(match.group(1))
                    current_d = current_operation_code

                    if current_operation_code == 3:

                        # --- Buffered ---
                        try:
                            log.debug("Bare op-code %d." % current_operation_code)
                            geo_dict = dict()
                            flash = self.create_flash_geometry(
                                Point(current_x, current_y), self.apertures[current_aperture],
                                self.steps_per_circle)

                            geo_dict['follow'] = Point([current_x, current_y])

                            if not flash.is_empty:
                                poly_buffer.append(flash)
                                if self.is_lpc is True:
                                    geo_dict['clear'] = flash
                                else:
                                    geo_dict['solid'] = flash

                                if current_aperture not in self.apertures:
                                    self.apertures[current_aperture] = dict()
                                if 'geometry' not in self.apertures[current_aperture]:
                                    self.apertures[current_aperture]['geometry'] = []
                                self.apertures[current_aperture]['geometry'].append(deepcopy(geo_dict))

                        except IndexError:
                            log.warning("Line %d: %s -> Nothing there to flash!" % (line_num, gline))

                    continue

                # ############################################################# ##
                # Tool/aperture change
                # Example: D12*
                # ############################################################# ##
                match = self.tool_re.search(gline)
                if match:
                    current_aperture = match.group(1)
                    # log.debug("Line %d: Aperture change to (%s)" % (line_num, current_aperture))

                    # If the aperture value is zero then make it something quite small but with a non-zero value
                    # so it can be processed by FlatCAM.
                    # But first test to see if the aperture type is "aperture macro". In that case
                    # we should not test for "size" key as it does not exist in this case.
                    if self.apertures[current_aperture]["type"] is not "AM":
                        if self.apertures[current_aperture]["size"] == 0:
                            self.apertures[current_aperture]["size"] = 1e-12
                    # log.debug(self.apertures[current_aperture])

                    # Take care of the current path with the previous tool
                    if len(path) > 1:
                        if self.apertures[last_path_aperture]["type"] == 'R':
                            # do nothing because 'R' type moving aperture is none at once
                            pass
                        else:
                            geo_dict = dict()
                            geo_f = LineString(path)
                            if not geo_f.is_empty:
                                follow_buffer.append(geo_f)
                                geo_dict['follow'] = geo_f

                            # --- Buffered ----
                            width = self.apertures[last_path_aperture]["size"]
                            geo_s = LineString(path).buffer(width / 1.999, int(self.steps_per_circle / 4))
                            if not geo_s.is_empty:
                                poly_buffer.append(geo_s)
                                if self.is_lpc is True:
                                    geo_dict['clear'] = geo_s
                                else:
                                    geo_dict['solid'] = geo_s

                            if last_path_aperture not in self.apertures:
                                self.apertures[last_path_aperture] = dict()
                            if 'geometry' not in self.apertures[last_path_aperture]:
                                self.apertures[last_path_aperture]['geometry'] = []
                            self.apertures[last_path_aperture]['geometry'].append(deepcopy(geo_dict))

                            path = [path[-1]]

                    continue

                # ############################################################# ##
                # G36* - Begin region
                # ############################################################# ##
                if self.regionon_re.search(gline):
                    if len(path) > 1:
                        # Take care of what is left in the path

                        geo_dict = dict()
                        geo_f = LineString(path)
                        if not geo_f.is_empty:
                            follow_buffer.append(geo_f)
                            geo_dict['follow'] = geo_f

                        # --- Buffered ----
                        width = self.apertures[last_path_aperture]["size"]
                        geo_s = LineString(path).buffer(width / 1.999, int(self.steps_per_circle / 4))
                        if not geo_s.is_empty:
                            poly_buffer.append(geo_s)
                            if self.is_lpc is True:
                                geo_dict['clear'] = geo_s
                            else:
                                geo_dict['solid'] = geo_s

                        if last_path_aperture not in self.apertures:
                            self.apertures[last_path_aperture] = dict()
                        if 'geometry' not in self.apertures[last_path_aperture]:
                            self.apertures[last_path_aperture]['geometry'] = []
                        self.apertures[last_path_aperture]['geometry'].append(deepcopy(geo_dict))

                        path = [path[-1]]

                    making_region = True
                    continue

                # ############################################################# ##
                # G37* - End region
                # ############################################################# ##
                if self.regionoff_re.search(gline):
                    making_region = False

                    if '0' not in self.apertures:
                        self.apertures['0'] = {}
                        self.apertures['0']['type'] = 'REG'
                        self.apertures['0']['size'] = 0.0
                        self.apertures['0']['geometry'] = []

                    # if D02 happened before G37 we now have a path with 1 element only; we have to add the current
                    # geo to the poly_buffer otherwise we loose it
                    if current_operation_code == 2:
                        if len(path) == 1:
                            # this means that the geometry was prepared previously and we just need to add it
                            geo_dict = dict()
                            if geo_f:
                                if not geo_f.is_empty:
                                    follow_buffer.append(geo_f)
                                    geo_dict['follow'] = geo_f
                            if geo_s:
                                if not geo_s.is_empty:
                                    poly_buffer.append(geo_s)
                                    if self.is_lpc is True:
                                        geo_dict['clear'] = geo_s
                                    else:
                                        geo_dict['solid'] = geo_s

                            if geo_s or geo_f:
                                self.apertures['0']['geometry'].append(deepcopy(geo_dict))

                            path = [[current_x, current_y]]  # Start new path

                    # Only one path defines region?
                    # This can happen if D02 happened before G37 and
                    # is not and error.
                    if len(path) < 3:
                        # print "ERROR: Path contains less than 3 points:"
                        # path = [[current_x, current_y]]
                        continue

                    # For regions we may ignore an aperture that is None

                    # --- Buffered ---
                    geo_dict = dict()
                    region_f = Polygon(path).exterior
                    if not region_f.is_empty:
                        follow_buffer.append(region_f)
                        geo_dict['follow'] = region_f

                    region_s = Polygon(path)
                    if not region_s.is_valid:
                        region_s = region_s.buffer(0, int(self.steps_per_circle / 4))

                    if not region_s.is_empty:
                        poly_buffer.append(region_s)
                        if self.is_lpc is True:
                            geo_dict['clear'] = region_s
                        else:
                            geo_dict['solid'] = region_s

                    if not region_s.is_empty or not region_f.is_empty:
                        self.apertures['0']['geometry'].append(deepcopy(geo_dict))

                    path = [[current_x, current_y]]  # Start new path
                    continue

                # ## G01/2/3* - Interpolation mode change
                # Can occur along with coordinates and operation code but
                # sometimes by itself (handled here).
                # Example: G01*
                match = self.interp_re.search(gline)
                if match:
                    current_interpolation_mode = int(match.group(1))
                    continue

                # ## G01 - Linear interpolation plus flashes
                # Operation code (D0x) missing is deprecated... oh well I will support it.
                # REGEX: r'^(?:G0?(1))?(?:X(-?\d+))?(?:Y(-?\d+))?(?:D0([123]))?\*$'
                match = self.lin_re.search(gline)
                if match:
                    # Dxx alone?
                    # if match.group(1) is None and match.group(2) is None and match.group(3) is None:
                    #     try:
                    #         current_operation_code = int(match.group(4))
                    #     except:
                    #         pass  # A line with just * will match too.
                    #     continue
                    # NOTE: Letting it continue allows it to react to the
                    #       operation code.

                    # Parse coordinates
                    if match.group(2) is not None:
                        linear_x = parse_gerber_number(match.group(2),
                                                       self.int_digits, self.frac_digits, self.gerber_zeros)
                        current_x = linear_x
                    else:
                        linear_x = current_x
                    if match.group(3) is not None:
                        linear_y = parse_gerber_number(match.group(3),
                                                       self.int_digits, self.frac_digits, self.gerber_zeros)
                        current_y = linear_y
                    else:
                        linear_y = current_y

                    # Parse operation code
                    if match.group(4) is not None:
                        current_operation_code = int(match.group(4))

                    # Pen down: add segment
                    if current_operation_code == 1:
                        # if linear_x or linear_y are None, ignore those
                        if current_x is not None and current_y is not None:
                            # only add the point if it's a new one otherwise skip it (harder to process)
                            if path[-1] != [current_x, current_y]:
                                path.append([current_x, current_y])

                            if making_region is False:
                                # if the aperture is rectangle then add a rectangular shape having as parameters the
                                # coordinates of the start and end point and also the width and height
                                # of the 'R' aperture
                                try:
                                    if self.apertures[current_aperture]["type"] == 'R':
                                        width = self.apertures[current_aperture]['width']
                                        height = self.apertures[current_aperture]['height']
                                        minx = min(path[0][0], path[1][0]) - width / 2
                                        maxx = max(path[0][0], path[1][0]) + width / 2
                                        miny = min(path[0][1], path[1][1]) - height / 2
                                        maxy = max(path[0][1], path[1][1]) + height / 2
                                        log.debug("Coords: %s - %s - %s - %s" % (minx, miny, maxx, maxy))

                                        geo_dict = dict()
                                        geo_f = Point([current_x, current_y])
                                        follow_buffer.append(geo_f)
                                        geo_dict['follow'] = geo_f

                                        geo_s = shply_box(minx, miny, maxx, maxy)
                                        poly_buffer.append(geo_s)
                                        if self.is_lpc is True:
                                            geo_dict['clear'] = geo_s
                                        else:
                                            geo_dict['solid'] = geo_s

                                        if current_aperture not in self.apertures:
                                            self.apertures[current_aperture] = dict()
                                        if 'geometry' not in self.apertures[current_aperture]:
                                            self.apertures[current_aperture]['geometry'] = []
                                        self.apertures[current_aperture]['geometry'].append(deepcopy(geo_dict))
                                except Exception as e:
                                    pass
                            last_path_aperture = current_aperture
                            # we do this for the case that a region is done without having defined any aperture
                            if last_path_aperture is None:
                                if '0' not in self.apertures:
                                    self.apertures['0'] = {}
                                    self.apertures['0']['type'] = 'REG'
                                    self.apertures['0']['size'] = 0.0
                                    self.apertures['0']['geometry'] = []
                                last_path_aperture = '0'
                        else:
                            self.app.inform.emit(_("[WARNING] Coordinates missing, line ignored: %s") % str(gline))
                            self.app.inform.emit(_("[WARNING_NOTCL] GERBER file might be CORRUPT. Check the file !!!"))

                    elif current_operation_code == 2:
                        if len(path) > 1:
                            geo_s = None
                            geo_f = None

                            geo_dict = dict()
                            # --- BUFFERED ---
                            # this treats the case when we are storing geometry as paths only
                            if making_region:
                                # we do this for the case that a region is done without having defined any aperture
                                if last_path_aperture is None:
                                    if '0' not in self.apertures:
                                        self.apertures['0'] = {}
                                        self.apertures['0']['type'] = 'REG'
                                        self.apertures['0']['size'] = 0.0
                                        self.apertures['0']['geometry'] = []
                                    last_path_aperture = '0'
                                geo_f = Polygon()
                            else:
                                geo_f = LineString(path)

                            try:
                                if self.apertures[last_path_aperture]["type"] != 'R':
                                    if not geo_f.is_empty:
                                        follow_buffer.append(geo_f)
                                        geo_dict['follow'] = geo_f
                            except Exception as e:
                                log.debug("camlib.Gerber.parse_lines() --> %s" % str(e))
                                if not geo_f.is_empty:
                                    follow_buffer.append(geo_f)
                                    geo_dict['follow'] = geo_f

                            # this treats the case when we are storing geometry as solids
                            if making_region:
                                # we do this for the case that a region is done without having defined any aperture
                                if last_path_aperture is None:
                                    if '0' not in self.apertures:
                                        self.apertures['0'] = {}
                                        self.apertures['0']['type'] = 'REG'
                                        self.apertures['0']['size'] = 0.0
                                        self.apertures['0']['geometry'] = []
                                    last_path_aperture = '0'

                                try:
                                    geo_s = Polygon(path)
                                except ValueError:
                                    log.warning("Problem %s %s" % (gline, line_num))
                                    self.app.inform.emit(_("[ERROR] Region does not have enough points. "
                                                           "File will be processed but there are parser errors. "
                                                           "Line number: %s") % str(line_num))
                            else:
                                if last_path_aperture is None:
                                    log.warning("No aperture defined for curent path. (%d)" % line_num)
                                width = self.apertures[last_path_aperture]["size"]  # TODO: WARNING this should fail!
                                geo_s = LineString(path).buffer(width / 1.999, int(self.steps_per_circle / 4))

                            try:
                                if self.apertures[last_path_aperture]["type"] != 'R':
                                    if not geo_s.is_empty:
                                        poly_buffer.append(geo_s)
                                        if self.is_lpc is True:
                                            geo_dict['clear'] = geo_s
                                        else:
                                            geo_dict['solid'] = geo_s
                            except Exception as e:
                                log.debug("camlib.Gerber.parse_lines() --> %s" % str(e))
                                poly_buffer.append(geo_s)
                                if self.is_lpc is True:
                                    geo_dict['clear'] = geo_s
                                else:
                                    geo_dict['solid'] = geo_s

                            if last_path_aperture not in self.apertures:
                                self.apertures[last_path_aperture] = dict()
                            if 'geometry' not in self.apertures[last_path_aperture]:
                                self.apertures[last_path_aperture]['geometry'] = []
                            self.apertures[last_path_aperture]['geometry'].append(deepcopy(geo_dict))

                        # if linear_x or linear_y are None, ignore those
                        if linear_x is not None and linear_y is not None:
                            path = [[linear_x, linear_y]]  # Start new path
                        else:
                            self.app.inform.emit(_("[WARNING] Coordinates missing, line ignored: %s") % str(gline))
                            self.app.inform.emit(_("[WARNING_NOTCL] GERBER file might be CORRUPT. Check the file !!!"))

                    # Flash
                    # Not allowed in region mode.
                    elif current_operation_code == 3:

                        # Create path draw so far.
                        if len(path) > 1:
                            # --- Buffered ----
                            geo_dict = dict()

                            # this treats the case when we are storing geometry as paths
                            geo_f = LineString(path)
                            if not geo_f.is_empty:
                                try:
                                    if self.apertures[last_path_aperture]["type"] != 'R':
                                        follow_buffer.append(geo_f)
                                        geo_dict['follow'] = geo_f
                                except Exception as e:
                                    log.debug("camlib.Gerber.parse_lines() --> G01 match D03 --> %s" % str(e))
                                    follow_buffer.append(geo_f)
                                    geo_dict['follow'] = geo_f

                            # this treats the case when we are storing geometry as solids
                            width = self.apertures[last_path_aperture]["size"]
                            geo_s = LineString(path).buffer(width / 1.999, int(self.steps_per_circle / 4))
                            if not geo_s.is_empty:
                                try:
                                    if self.apertures[last_path_aperture]["type"] != 'R':
                                        poly_buffer.append(geo_s)
                                        if self.is_lpc is True:
                                            geo_dict['clear'] = geo_s
                                        else:
                                            geo_dict['solid'] = geo_s
                                except:
                                    poly_buffer.append(geo_s)
                                    if self.is_lpc is True:
                                        geo_dict['clear'] = geo_s
                                    else:
                                        geo_dict['solid'] = geo_s

                            if last_path_aperture not in self.apertures:
                                self.apertures[last_path_aperture] = dict()
                            if 'geometry' not in self.apertures[last_path_aperture]:
                                self.apertures[last_path_aperture]['geometry'] = []
                            self.apertures[last_path_aperture]['geometry'].append(deepcopy(geo_dict))

                        # Reset path starting point
                        path = [[linear_x, linear_y]]

                        # --- BUFFERED ---
                        # Draw the flash
                        # this treats the case when we are storing geometry as paths
                        geo_dict = dict()
                        geo_flash = Point([linear_x, linear_y])
                        follow_buffer.append(geo_flash)
                        geo_dict['follow'] = geo_flash

                        # this treats the case when we are storing geometry as solids
                        flash = self.create_flash_geometry(
                            Point([linear_x, linear_y]),
                            self.apertures[current_aperture],
                            self.steps_per_circle
                        )
                        if not flash.is_empty:
                            poly_buffer.append(flash)
                            if self.is_lpc is True:
                                geo_dict['clear'] = flash
                            else:
                                geo_dict['solid'] = flash

                        if current_aperture not in self.apertures:
                            self.apertures[current_aperture] = dict()
                        if 'geometry' not in self.apertures[current_aperture]:
                            self.apertures[current_aperture]['geometry'] = []
                        self.apertures[current_aperture]['geometry'].append(deepcopy(geo_dict))

                    # maybe those lines are not exactly needed but it is easier to read the program as those coordinates
                    # are used in case that circular interpolation is encountered within the Gerber file
                    current_x = linear_x
                    current_y = linear_y

                    # log.debug("Line_number=%3s X=%s Y=%s (%s)" % (line_num, linear_x, linear_y, gline))
                    continue

                # ## G74/75* - Single or multiple quadrant arcs
                match = self.quad_re.search(gline)
                if match:
                    if match.group(1) == '4':
                        quadrant_mode = 'SINGLE'
                    else:
                        quadrant_mode = 'MULTI'
                    continue

                # ## G02/3 - Circular interpolation
                # 2-clockwise, 3-counterclockwise
                # Ex. format: G03 X0 Y50 I-50 J0 where the X, Y coords are the coords of the End Point
                match = self.circ_re.search(gline)
                if match:
                    arcdir = [None, None, "cw", "ccw"]

                    mode, circular_x, circular_y, i, j, d = match.groups()

                    try:
                        circular_x = parse_gerber_number(circular_x,
                                                         self.int_digits, self.frac_digits, self.gerber_zeros)
                    except:
                        circular_x = current_x

                    try:
                        circular_y = parse_gerber_number(circular_y,
                                                         self.int_digits, self.frac_digits, self.gerber_zeros)
                    except:
                        circular_y = current_y

                    # According to Gerber specification i and j are not modal, which means that when i or j are missing,
                    # they are to be interpreted as being zero
                    try:
                        i = parse_gerber_number(i, self.int_digits, self.frac_digits, self.gerber_zeros)
                    except:
                        i = 0

                    try:
                        j = parse_gerber_number(j, self.int_digits, self.frac_digits, self.gerber_zeros)
                    except:
                        j = 0

                    if quadrant_mode is None:
                        log.error("Found arc without preceding quadrant specification G74 or G75. (%d)" % line_num)
                        log.error(gline)
                        continue

                    if mode is None and current_interpolation_mode not in [2, 3]:
                        log.error("Found arc without circular interpolation mode defined. (%d)" % line_num)
                        log.error(gline)
                        continue
                    elif mode is not None:
                        current_interpolation_mode = int(mode)

                    # Set operation code if provided
                    if d is not None:
                        current_operation_code = int(d)

                    # Nothing created! Pen Up.
                    if current_operation_code == 2:
                        log.warning("Arc with D2. (%d)" % line_num)
                        if len(path) > 1:
                            geo_dict = dict()

                            if last_path_aperture is None:
                                log.warning("No aperture defined for curent path. (%d)" % line_num)

                            # --- BUFFERED ---
                            width = self.apertures[last_path_aperture]["size"]

                            # this treats the case when we are storing geometry as paths
                            geo_f = LineString(path)
                            if not geo_f.is_empty:
                                follow_buffer.append(geo_f)
                                geo_dict['follow'] = geo_f

                            # this treats the case when we are storing geometry as solids
                            buffered = LineString(path).buffer(width / 1.999, int(self.steps_per_circle))
                            if not buffered.is_empty:
                                poly_buffer.append(buffered)
                                if self.is_lpc is True:
                                    geo_dict['clear'] = buffered
                                else:
                                    geo_dict['solid'] = buffered

                            if last_path_aperture not in self.apertures:
                                self.apertures[last_path_aperture] = dict()
                            if 'geometry' not in self.apertures[last_path_aperture]:
                                self.apertures[last_path_aperture]['geometry'] = []
                            self.apertures[last_path_aperture]['geometry'].append(deepcopy(geo_dict))

                        current_x = circular_x
                        current_y = circular_y
                        path = [[current_x, current_y]]  # Start new path
                        continue

                    # Flash should not happen here
                    if current_operation_code == 3:
                        log.error("Trying to flash within arc. (%d)" % line_num)
                        continue

                    if quadrant_mode == 'MULTI':
                        center = [i + current_x, j + current_y]
                        radius = sqrt(i ** 2 + j ** 2)
                        start = arctan2(-j, -i)  # Start angle
                        # Numerical errors might prevent start == stop therefore
                        # we check ahead of time. This should result in a
                        # 360 degree arc.
                        if current_x == circular_x and current_y == circular_y:
                            stop = start
                        else:
                            stop = arctan2(-center[1] + circular_y, -center[0] + circular_x)  # Stop angle

                        this_arc = arc(center, radius, start, stop,
                                       arcdir[current_interpolation_mode],
                                       self.steps_per_circle)

                        # The last point in the computed arc can have
                        # numerical errors. The exact final point is the
                        # specified (x, y). Replace.
                        this_arc[-1] = (circular_x, circular_y)

                        # Last point in path is current point
                        # current_x = this_arc[-1][0]
                        # current_y = this_arc[-1][1]
                        current_x, current_y = circular_x, circular_y

                        # Append
                        path += this_arc
                        last_path_aperture = current_aperture

                        continue

                    if quadrant_mode == 'SINGLE':

                        center_candidates = [
                            [i + current_x, j + current_y],
                            [-i + current_x, j + current_y],
                            [i + current_x, -j + current_y],
                            [-i + current_x, -j + current_y]
                        ]

                        valid = False
                        log.debug("I: %f  J: %f" % (i, j))
                        for center in center_candidates:
                            radius = sqrt(i ** 2 + j ** 2)

                            # Make sure radius to start is the same as radius to end.
                            radius2 = sqrt((center[0] - circular_x) ** 2 + (center[1] - circular_y) ** 2)
                            if radius2 < radius * 0.95 or radius2 > radius * 1.05:
                                continue  # Not a valid center.

                            # Correct i and j and continue as with multi-quadrant.
                            i = center[0] - current_x
                            j = center[1] - current_y

                            start = arctan2(-j, -i)  # Start angle
                            stop = arctan2(-center[1] + circular_y, -center[0] + circular_x)  # Stop angle
                            angle = abs(arc_angle(start, stop, arcdir[current_interpolation_mode]))
                            log.debug("ARC START: %f, %f  CENTER: %f, %f  STOP: %f, %f" %
                                      (current_x, current_y, center[0], center[1], circular_x, circular_y))
                            log.debug("START Ang: %f, STOP Ang: %f, DIR: %s, ABS: %.12f <= %.12f: %s" %
                                      (start * 180 / pi, stop * 180 / pi, arcdir[current_interpolation_mode],
                                       angle * 180 / pi, pi / 2 * 180 / pi, angle <= (pi + 1e-6) / 2))

                            if angle <= (pi + 1e-6) / 2:
                                log.debug("########## ACCEPTING ARC ############")
                                this_arc = arc(center, radius, start, stop,
                                               arcdir[current_interpolation_mode],
                                               self.steps_per_circle)

                                # Replace with exact values
                                this_arc[-1] = (circular_x, circular_y)

                                # current_x = this_arc[-1][0]
                                # current_y = this_arc[-1][1]
                                current_x, current_y = circular_x, circular_y

                                path += this_arc
                                last_path_aperture = current_aperture
                                valid = True
                                break

                        if valid:
                            continue
                        else:
                            log.warning("Invalid arc in line %d." % line_num)

                # ## EOF
                match = self.eof_re.search(gline)
                if match:
                    continue

                # ## Line did not match any pattern. Warn user.
                log.warning("Line ignored (%d): %s" % (line_num, gline))

            if len(path) > 1:
                # In case that G01 (moving) aperture is rectangular, there is no need to still create
                # another geo since we already created a shapely box using the start and end coordinates found in
                # path variable. We do it only for other apertures than 'R' type
                if self.apertures[last_path_aperture]["type"] == 'R':
                    pass
                else:
                    # EOF, create shapely LineString if something still in path
                    # ## --- Buffered ---

                    geo_dict = dict()
                    # this treats the case when we are storing geometry as paths
                    geo_f = LineString(path)
                    if not geo_f.is_empty:
                        follow_buffer.append(geo_f)
                        geo_dict['follow'] = geo_f

                    # this treats the case when we are storing geometry as solids
                    width = self.apertures[last_path_aperture]["size"]
                    geo_s = LineString(path).buffer(width / 1.999, int(self.steps_per_circle / 4))
                    if not geo_s.is_empty:
                        poly_buffer.append(geo_s)
                        if self.is_lpc is True:
                            geo_dict['clear'] = geo_s
                        else:
                            geo_dict['solid'] = geo_s

                    if last_path_aperture not in self.apertures:
                        self.apertures[last_path_aperture] = dict()
                    if 'geometry' not in self.apertures[last_path_aperture]:
                        self.apertures[last_path_aperture]['geometry'] = []
                    self.apertures[last_path_aperture]['geometry'].append(deepcopy(geo_dict))

            # TODO: make sure to keep track of units changes because right now it seems to happen in a weird way
            # find out the conversion factor used to convert inside the self.apertures keys: size, width, height
            file_units = self.gerber_units if self.gerber_units else 'IN'
            app_units = self.app.defaults['units']

            conversion_factor = 25.4 if file_units == 'IN' else (1/25.4) if file_units != app_units else 1

            # --- Apply buffer ---
            # this treats the case when we are storing geometry as paths
            self.follow_geometry = follow_buffer

            # this treats the case when we are storing geometry as solids
            log.warning("Joining %d polygons." % len(poly_buffer))

            if len(poly_buffer) == 0:
                log.error("Object is not Gerber file or empty. Aborting Object creation.")
                return 'fail'

            if self.use_buffer_for_union:
                log.debug("Union by buffer...")

                new_poly = MultiPolygon(poly_buffer)
                new_poly = new_poly.buffer(0.00000001)
                new_poly = new_poly.buffer(-0.00000001)
                log.warning("Union(buffer) done.")
            else:
                log.debug("Union by union()...")
                new_poly = cascaded_union(poly_buffer)
                new_poly = new_poly.buffer(0, int(self.steps_per_circle / 4))
                log.warning("Union done.")
            if current_polarity == 'D':
                self.solid_geometry = self.solid_geometry.union(new_poly)
            else:
                self.solid_geometry = self.solid_geometry.difference(new_poly)

        except Exception as err:
            ex_type, ex, tb = sys.exc_info()
            traceback.print_tb(tb)
            # print traceback.format_exc()

            log.error("Gerber PARSING FAILED. Line %d: %s" % (line_num, gline))
            loc = 'Gerber Line #%d Gerber Line Content: %s\n' % (line_num, gline) + repr(err)
            self.app.inform.emit(_("[ERROR]Gerber Parser ERROR.\n%s:") % loc)

    @staticmethod
    def create_flash_geometry(location, aperture, steps_per_circle=None):

        # log.debug('Flashing @%s, Aperture: %s' % (location, aperture))

        if type(location) == list:
            location = Point(location)

        if aperture['type'] == 'C':  # Circles
            return location.buffer(aperture['size'] / 2, int(steps_per_circle / 4))

        if aperture['type'] == 'R':  # Rectangles
            loc = location.coords[0]
            width = aperture['width']
            height = aperture['height']
            minx = loc[0] - width / 2
            maxx = loc[0] + width / 2
            miny = loc[1] - height / 2
            maxy = loc[1] + height / 2
            return shply_box(minx, miny, maxx, maxy)

        if aperture['type'] == 'O':  # Obround
            loc = location.coords[0]
            width = aperture['width']
            height = aperture['height']
            if width > height:
                p1 = Point(loc[0] + 0.5 * (width - height), loc[1])
                p2 = Point(loc[0] - 0.5 * (width - height), loc[1])
                c1 = p1.buffer(height * 0.5, int(steps_per_circle / 4))
                c2 = p2.buffer(height * 0.5, int(steps_per_circle / 4))
            else:
                p1 = Point(loc[0], loc[1] + 0.5 * (height - width))
                p2 = Point(loc[0], loc[1] - 0.5 * (height - width))
                c1 = p1.buffer(width * 0.5, int(steps_per_circle / 4))
                c2 = p2.buffer(width * 0.5, int(steps_per_circle / 4))
            return cascaded_union([c1, c2]).convex_hull

        if aperture['type'] == 'P':  # Regular polygon
            loc = location.coords[0]
            diam = aperture['diam']
            n_vertices = aperture['nVertices']
            points = []
            for i in range(0, n_vertices):
                x = loc[0] + 0.5 * diam * (cos(2 * pi * i / n_vertices))
                y = loc[1] + 0.5 * diam * (sin(2 * pi * i / n_vertices))
                points.append((x, y))
            ply = Polygon(points)
            if 'rotation' in aperture:
                ply = affinity.rotate(ply, aperture['rotation'])
            return ply

        if aperture['type'] == 'AM':  # Aperture Macro
            loc = location.coords[0]
            flash_geo = aperture['macro'].make_geometry(aperture['modifiers'])
            if flash_geo.is_empty:
                log.warning("Empty geometry for Aperture Macro: %s" % str(aperture['macro'].name))
            return affinity.translate(flash_geo, xoff=loc[0], yoff=loc[1])

        log.warning("Unknown aperture type: %s" % aperture['type'])
        return None
    
    def create_geometry(self):
        """
        Geometry from a Gerber file is made up entirely of polygons.
        Every stroke (linear or circular) has an aperture which gives
        it thickness. Additionally, aperture strokes have non-zero area,
        and regions naturally do as well.

        :rtype : None
        :return: None
        """
        pass
        # self.buffer_paths()
        #
        # self.fix_regions()
        #
        # self.do_flashes()
        #
        # self.solid_geometry = cascaded_union(self.buffered_paths +
        #                                      [poly['polygon'] for poly in self.regions] +
        #                                      self.flash_geometry)

    def get_bounding_box(self, margin=0.0, rounded=False):
        """
        Creates and returns a rectangular polygon bounding at a distance of
        margin from the object's ``solid_geometry``. If margin > 0, the polygon
        can optionally have rounded corners of radius equal to margin.

        :param margin: Distance to enlarge the rectangular bounding
         box in both positive and negative, x and y axes.
        :type margin: float
        :param rounded: Wether or not to have rounded corners.
        :type rounded: bool
        :return: The bounding box.
        :rtype: Shapely.Polygon
        """

        bbox = self.solid_geometry.envelope.buffer(margin)
        if not rounded:
            bbox = bbox.envelope
        return bbox

    def bounds(self):
        """
        Returns coordinates of rectangular bounds
        of Gerber geometry: (xmin, ymin, xmax, ymax).
        """
        # fixed issue of getting bounds only for one level lists of objects
        # now it can get bounds for nested lists of objects

        log.debug("camlib.Gerber.bounds()")

        if self.solid_geometry is None:
            log.debug("solid_geometry is None")
            return 0, 0, 0, 0

        def bounds_rec(obj):
            if type(obj) is list and type(obj) is not MultiPolygon:
                minx = Inf
                miny = Inf
                maxx = -Inf
                maxy = -Inf

                for k in obj:
                    if type(k) is dict:
                        for key in k:
                            minx_, miny_, maxx_, maxy_ = bounds_rec(k[key])
                            minx = min(minx, minx_)
                            miny = min(miny, miny_)
                            maxx = max(maxx, maxx_)
                            maxy = max(maxy, maxy_)
                    else:
                        if not k.is_empty:
                            try:
                                minx_, miny_, maxx_, maxy_ = bounds_rec(k)
                            except Exception as e:
                                log.debug("camlib.Gerber.bounds() --> %s" % str(e))
                                return

                            minx = min(minx, minx_)
                            miny = min(miny, miny_)
                            maxx = max(maxx, maxx_)
                            maxy = max(maxy, maxy_)
                return minx, miny, maxx, maxy
            else:
                # it's a Shapely object, return it's bounds
                return obj.bounds

        bounds_coords = bounds_rec(self.solid_geometry)
        return bounds_coords

    def scale(self, xfactor, yfactor=None, point=None):
        """
        Scales the objects' geometry on the XY plane by a given factor.
        These are:

        * ``buffered_paths``
        * ``flash_geometry``
        * ``solid_geometry``
        * ``regions``

        NOTE:
        Does not modify the data used to create these elements. If these
        are recreated, the scaling will be lost. This behavior was modified
        because of the complexity reached in this class.

        :param xfactor: Number by which to scale on X axis.
        :type xfactor: float
        :param yfactor: Number by which to scale on Y axis.
        :type yfactor: float
        :rtype : None
        """
        log.debug("camlib.Gerber.scale()")

        try:
            xfactor = float(xfactor)
        except:
            self.app.inform.emit(_("[ERROR_NOTCL] Scale factor has to be a number: integer or float."))
            return

        if yfactor is None:
            yfactor = xfactor
        else:
            try:
                yfactor = float(yfactor)
            except:
                self.app.inform.emit(_("[ERROR_NOTCL] Scale factor has to be a number: integer or float."))
                return

        if point is None:
            px = 0
            py = 0
        else:
            px, py = point

        def scale_geom(obj):
            if type(obj) is list:
                new_obj = []
                for g in obj:
                    new_obj.append(scale_geom(g))
                return new_obj
            else:
                try:
                    return affinity.scale(obj, xfactor, yfactor, origin=(px, py))
                except AttributeError:
                    return obj

        self.solid_geometry = scale_geom(self.solid_geometry)
        self.follow_geometry = scale_geom(self.follow_geometry)

        # we need to scale the geometry stored in the Gerber apertures, too
        try:
            for apid in self.apertures:
                if 'geometry' in self.apertures[apid]:
                    for geo_el in self.apertures[apid]['geometry']:
                        if 'solid' in geo_el:
                            geo_el['solid'] = scale_geom(geo_el['solid'])
                        if 'follow' in geo_el:
                            geo_el['follow'] = scale_geom(geo_el['follow'])
                        if 'clear' in geo_el:
                            geo_el['clear'] = scale_geom(geo_el['clear'])

        except Exception as e:
            log.debug('camlib.Gerber.scale() Exception --> %s' % str(e))
            return 'fail'

        self.app.inform.emit(_("[success] Gerber Scale done."))

        # ## solid_geometry ???
        #  It's a cascaded union of objects.
        # self.solid_geometry = affinity.scale(self.solid_geometry, factor,
        #                                      factor, origin=(0, 0))

        # # Now buffered_paths, flash_geometry and solid_geometry
        # self.create_geometry()

    def offset(self, vect):
        """
        Offsets the objects' geometry on the XY plane by a given vector.
        These are:

        * ``buffered_paths``
        * ``flash_geometry``
        * ``solid_geometry``
        * ``regions``

        NOTE:
        Does not modify the data used to create these elements. If these
        are recreated, the scaling will be lost. This behavior was modified
        because of the complexity reached in this class.

        :param vect: (x, y) offset vector.
        :type vect: tuple
        :return: None
        """
        log.debug("camlib.Gerber.offset()")

        try:
            dx, dy = vect
        except TypeError:
            self.app.inform.emit(_("[ERROR_NOTCL] An (x,y) pair of values are needed. "
                                 "Probable you entered only one value in the Offset field."))
            return

        def offset_geom(obj):
            if type(obj) is list:
                new_obj = []
                for g in obj:
                    new_obj.append(offset_geom(g))
                return new_obj
            else:
                try:
                    return affinity.translate(obj, xoff=dx, yoff=dy)
                except AttributeError:
                    return obj

        # ## Solid geometry
        self.solid_geometry = offset_geom(self.solid_geometry)
        self.follow_geometry = offset_geom(self.follow_geometry)

        # we need to offset the geometry stored in the Gerber apertures, too
        try:
            for apid in self.apertures:
                if 'geometry' in self.apertures[apid]:
                    for geo_el in self.apertures[apid]['geometry']:
                        if 'solid' in geo_el:
                            geo_el['solid'] = offset_geom(geo_el['solid'])
                        if 'follow' in geo_el:
                            geo_el['follow'] = offset_geom(geo_el['follow'])
                        if 'clear' in geo_el:
                            geo_el['clear'] = offset_geom(geo_el['clear'])

        except Exception as e:
            log.debug('camlib.Gerber.offset() Exception --> %s' % str(e))
            return 'fail'

        self.app.inform.emit(_("[success] Gerber Offset done."))

    def mirror(self, axis, point):
        """
        Mirrors the object around a specified axis passing through
        the given point. What is affected:

        * ``buffered_paths``
        * ``flash_geometry``
        * ``solid_geometry``
        * ``regions``

        NOTE:
        Does not modify the data used to create these elements. If these
        are recreated, the scaling will be lost. This behavior was modified
        because of the complexity reached in this class.

        :param axis: "X" or "Y" indicates around which axis to mirror.
        :type axis: str
        :param point: [x, y] point belonging to the mirror axis.
        :type point: list
        :return: None
        """
        log.debug("camlib.Gerber.mirror()")

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
                    return affinity.scale(obj, xscale, yscale, origin=(px, py))
                except AttributeError:
                    return obj

        self.solid_geometry = mirror_geom(self.solid_geometry)
        self.follow_geometry = mirror_geom(self.follow_geometry)

        # we need to mirror the geometry stored in the Gerber apertures, too
        try:
            for apid in self.apertures:
                if 'geometry' in self.apertures[apid]:
                    for geo_el in self.apertures[apid]['geometry']:
                        if 'solid' in geo_el:
                            geo_el['solid'] = mirror_geom(geo_el['solid'])
                        if 'follow' in geo_el:
                            geo_el['follow'] = mirror_geom(geo_el['follow'])
                        if 'clear' in geo_el:
                            geo_el['clear'] = mirror_geom(geo_el['clear'])
        except Exception as e:
            log.debug('camlib.Gerber.mirror() Exception --> %s' % str(e))
            return 'fail'

        self.app.inform.emit(_("[success] Gerber Mirror done."))

    def skew(self, angle_x, angle_y, point):
        """
        Shear/Skew the geometries of an object by angles along x and y dimensions.

        Parameters
        ----------
        angle_x, angle_y : float, float
            The shear angle(s) for the x and y axes respectively. These can be
            specified in either degrees (default) or radians by setting
            use_radians=True.

        See shapely manual for more information:
        http://toblerity.org/shapely/manual.html#affine-transformations
        """
        log.debug("camlib.Gerber.skew()")

        px, py = point

        def skew_geom(obj):
            if type(obj) is list:
                new_obj = []
                for g in obj:
                    new_obj.append(skew_geom(g))
                return new_obj
            else:
                try:
                    return affinity.skew(obj, angle_x, angle_y, origin=(px, py))
                except AttributeError:
                    return obj

        self.solid_geometry = skew_geom(self.solid_geometry)
        self.follow_geometry = skew_geom(self.follow_geometry)

        # we need to skew the geometry stored in the Gerber apertures, too
        try:
            for apid in self.apertures:
                if 'geometry' in self.apertures[apid]:
                    for geo_el in self.apertures[apid]['geometry']:
                        if 'solid' in geo_el:
                            geo_el['solid'] = skew_geom(geo_el['solid'])
                        if 'follow' in geo_el:
                            geo_el['follow'] = skew_geom(geo_el['follow'])
                        if 'clear' in geo_el:
                            geo_el['clear'] = skew_geom(geo_el['clear'])
        except Exception as e:
            log.debug('camlib.Gerber.skew() Exception --> %s' % str(e))
            return 'fail'

        self.app.inform.emit(_("[success] Gerber Skew done."))

    def rotate(self, angle, point):
        """
        Rotate an object by a given angle around given coords (point)
        :param angle:
        :param point:
        :return:
        """
        log.debug("camlib.Gerber.rotate()")

        px, py = point

        def rotate_geom(obj):
            if type(obj) is list:
                new_obj = []
                for g in obj:
                    new_obj.append(rotate_geom(g))
                return new_obj
            else:
                try:
                    return affinity.rotate(obj, angle, origin=(px, py))
                except AttributeError:
                    return obj

        self.solid_geometry = rotate_geom(self.solid_geometry)
        self.follow_geometry = rotate_geom(self.follow_geometry)

        # we need to rotate the geometry stored in the Gerber apertures, too
        try:
            for apid in self.apertures:
                if 'geometry' in self.apertures[apid]:
                    for geo_el in self.apertures[apid]['geometry']:
                        if 'solid' in geo_el:
                            geo_el['solid'] = rotate_geom(geo_el['solid'])
                        if 'follow' in geo_el:
                            geo_el['follow'] = rotate_geom(geo_el['follow'])
                        if 'clear' in geo_el:
                            geo_el['clear'] = rotate_geom(geo_el['clear'])
        except Exception as e:
            log.debug('camlib.Gerber.rotate() Exception --> %s' % str(e))
            return 'fail'
        self.app.inform.emit(_("[success] Gerber Rotate done."))


class Excellon(Geometry):
    """
    Here it is done all the Excellon parsing.

    *ATTRIBUTES*

    * ``tools`` (dict): The key is the tool name and the value is
      a dictionary specifying the tool:

    ================  ====================================
    Key               Value
    ================  ====================================
    C                 Diameter of the tool
    solid_geometry    Geometry list for each tool
    Others            Not supported (Ignored).
    ================  ====================================

    * ``drills`` (list): Each is a dictionary:

    ================  ====================================
    Key               Value
    ================  ====================================
    point             (Shapely.Point) Where to drill
    tool              (str) A key in ``tools``
    ================  ====================================

    * ``slots`` (list): Each is a dictionary

    ================  ====================================
    Key               Value
    ================  ====================================
    start             (Shapely.Point) Start point of the slot
    stop              (Shapely.Point) Stop point of the slot
    tool              (str) A key in ``tools``
    ================  ====================================
    """

    defaults = {
        "zeros": "L",
        "excellon_format_upper_mm": '3',
        "excellon_format_lower_mm": '3',
        "excellon_format_upper_in": '2',
        "excellon_format_lower_in": '4',
        "excellon_units": 'INCH',
        "geo_steps_per_circle": '64'
    }

    def __init__(self, zeros=None, excellon_format_upper_mm=None, excellon_format_lower_mm=None,
                 excellon_format_upper_in=None, excellon_format_lower_in=None, excellon_units=None,
                 geo_steps_per_circle=None):
        """
        The constructor takes no parameters.

        :return: Excellon object.
        :rtype: Excellon
        """

        if geo_steps_per_circle is None:
            geo_steps_per_circle = int(Excellon.defaults['geo_steps_per_circle'])
        self.geo_steps_per_circle = int(geo_steps_per_circle)

        Geometry.__init__(self, geo_steps_per_circle=int(geo_steps_per_circle))

        # dictionary to store tools, see above for description
        self.tools = {}
        # list to store the drills, see above for description
        self.drills = []

        # self.slots (list) to store the slots; each is a dictionary
        self.slots = []

        self.source_file = ''

        # it serve to flag if a start routing or a stop routing was encountered
        # if a stop is encounter and this flag is still 0 (so there is no stop for a previous start) issue error
        self.routing_flag = 1

        self.match_routing_start = None
        self.match_routing_stop = None

        self.num_tools = []  # List for keeping the tools sorted
        self.index_per_tool = {}  # Dictionary to store the indexed points for each tool

        # ## IN|MM -> Units are inherited from Geometry
        #self.units = units

        # Trailing "T" or leading "L" (default)
        #self.zeros = "T"
        self.zeros = zeros or self.defaults["zeros"]
        self.zeros_found = self.zeros
        self.units_found = self.units

        # this will serve as a default if the Excellon file has no info regarding of tool diameters (this info may be
        # in another file like for PCB WIzard ECAD software
        self.toolless_diam = 1.0
        # signal that the Excellon file has no tool diameter informations and the tools have bogus (random) diameter
        self.diameterless = False

        # Excellon format
        self.excellon_format_upper_in = excellon_format_upper_in or self.defaults["excellon_format_upper_in"]
        self.excellon_format_lower_in = excellon_format_lower_in or self.defaults["excellon_format_lower_in"]
        self.excellon_format_upper_mm = excellon_format_upper_mm or self.defaults["excellon_format_upper_mm"]
        self.excellon_format_lower_mm = excellon_format_lower_mm or self.defaults["excellon_format_lower_mm"]
        self.excellon_units = excellon_units or self.defaults["excellon_units"]
        # detected Excellon format is stored here:
        self.excellon_format = None

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from Geometry.
        self.ser_attrs += ['tools', 'drills', 'zeros', 'excellon_format_upper_mm', 'excellon_format_lower_mm',
                           'excellon_format_upper_in', 'excellon_format_lower_in', 'excellon_units', 'slots',
                           'source_file']

        # ### Patterns ####
        # Regex basics:
        # ^ - beginning
        # $ - end
        # *: 0 or more, +: 1 or more, ?: 0 or 1

        # M48 - Beginning of Part Program Header
        self.hbegin_re = re.compile(r'^M48$')

        # ;HEADER - Beginning of Allegro Program Header
        self.allegro_hbegin_re = re.compile(r'\;\s*(HEADER)')

        # M95 or % - End of Part Program Header
        # NOTE: % has different meaning in the body
        self.hend_re = re.compile(r'^(?:M95|%)$')

        # FMAT Excellon format
        # Ignored in the parser
        #self.fmat_re = re.compile(r'^FMAT,([12])$')

        # Uunits and possible Excellon zeros and possible Excellon format
        # INCH uses 6 digits
        # METRIC uses 5/6
        self.units_re = re.compile(r'^(INCH|METRIC)(?:,([TL])Z)?,?(\d*\.\d+)?.*$')

        # Tool definition/parameters (?= is look-ahead
        # NOTE: This might be an overkill!
        # self.toolset_re = re.compile(r'^T(0?\d|\d\d)(?=.*C(\d*\.?\d*))?' +
        #                              r'(?=.*F(\d*\.?\d*))?(?=.*S(\d*\.?\d*))?' +
        #                              r'(?=.*B(\d*\.?\d*))?(?=.*H(\d*\.?\d*))?' +
        #                              r'(?=.*Z([-\+]?\d*\.?\d*))?[CFSBHT]')
        self.toolset_re = re.compile(r'^T(\d+)(?=.*C,?(\d*\.?\d*))?' +
                                     r'(?=.*F(\d*\.?\d*))?(?=.*S(\d*\.?\d*))?' +
                                     r'(?=.*B(\d*\.?\d*))?(?=.*H(\d*\.?\d*))?' +
                                     r'(?=.*Z([-\+]?\d*\.?\d*))?[CFSBHT]')

        self.detect_gcode_re = re.compile(r'^G2([01])$')

        # Tool select
        # Can have additional data after tool number but
        # is ignored if present in the header.
        # Warning: This will match toolset_re too.
        # self.toolsel_re = re.compile(r'^T((?:\d\d)|(?:\d))')
        self.toolsel_re = re.compile(r'^T(\d+)')

        # Headerless toolset
        # self.toolset_hl_re = re.compile(r'^T(\d+)(?=.*C(\d*\.?\d*))')
        self.toolset_hl_re = re.compile(r'^T(\d+)(?:.?C(\d+\.?\d*))?')

        # Comment
        self.comm_re = re.compile(r'^;(.*)$')

        # Absolute/Incremental G90/G91
        self.absinc_re = re.compile(r'^G9([01])$')

        # Modes of operation
        # 1-linear, 2-circCW, 3-cirCCW, 4-vardwell, 5-Drill
        self.modes_re = re.compile(r'^G0([012345])')

        # Measuring mode
        # 1-metric, 2-inch
        self.meas_re = re.compile(r'^M7([12])$')

        # Coordinates
        # self.xcoord_re = re.compile(r'^X(\d*\.?\d*)(?:Y\d*\.?\d*)?$')
        # self.ycoord_re = re.compile(r'^(?:X\d*\.?\d*)?Y(\d*\.?\d*)$')
        coordsperiod_re_string = r'(?=.*X([-\+]?\d*\.\d*))?(?=.*Y([-\+]?\d*\.\d*))?[XY]'
        self.coordsperiod_re = re.compile(coordsperiod_re_string)

        coordsnoperiod_re_string = r'(?!.*\.)(?=.*X([-\+]?\d*))?(?=.*Y([-\+]?\d*))?[XY]'
        self.coordsnoperiod_re = re.compile(coordsnoperiod_re_string)

        # Slots parsing
        slots_re_string = r'^([^G]+)G85(.*)$'
        self.slots_re = re.compile(slots_re_string)

        # R - Repeat hole (# times, X offset, Y offset)
        self.rep_re = re.compile(r'^R(\d+)(?=.*[XY])+(?:X([-\+]?\d*\.?\d*))?(?:Y([-\+]?\d*\.?\d*))?$')

        # Various stop/pause commands
        self.stop_re = re.compile(r'^((G04)|(M09)|(M06)|(M00)|(M30))')

        # Allegro Excellon format support
        self.tool_units_re = re.compile(r'(\;\s*Holesize \d+.\s*\=\s*(\d+.\d+).*(MILS|MM))')

        # Altium Excellon format support
        # it's a comment like this: ";FILE_FORMAT=2:5"
        self.altium_format = re.compile(r'^;\s*(?:FILE_FORMAT)?(?:Format)?[=|:]\s*(\d+)[:|.](\d+).*$')

        # Parse coordinates
        self.leadingzeros_re = re.compile(r'^[-\+]?(0*)(\d*)')

        # Repeating command
        self.repeat_re = re.compile(r'R(\d+)')

    def parse_file(self, filename=None, file_obj=None):
        """
        Reads the specified file as array of lines as
        passes it to ``parse_lines()``.

        :param filename: The file to be read and parsed.
        :type filename: str
        :return: None
        """
        if file_obj:
            estr = file_obj
        else:
            if filename is None:
                return "fail"
            efile = open(filename, 'r')
            estr = efile.readlines()
            efile.close()

        try:
            self.parse_lines(estr)
        except:
            return "fail"

    def parse_lines(self, elines):
        """
        Main Excellon parser.

        :param elines: List of strings, each being a line of Excellon code.
        :type elines: list
        :return: None
        """

        # State variables
        current_tool = ""
        in_header = False
        headerless = False
        current_x = None
        current_y = None

        slot_current_x = None
        slot_current_y = None

        name_tool = 0
        allegro_warning = False
        line_units_found = False

        repeating_x = 0
        repeating_y = 0
        repeat = 0

        line_units = ''

        #### Parsing starts here ## ##
        line_num = 0  # Line number
        eline = ""
        try:
            for eline in elines:
                line_num += 1
                # log.debug("%3d %s" % (line_num, str(eline)))

                self.source_file += eline

                # Cleanup lines
                eline = eline.strip(' \r\n')

                # Excellon files and Gcode share some extensions therefore if we detect G20 or G21 it's GCODe
                # and we need to exit from here
                if self.detect_gcode_re.search(eline):
                    log.warning("This is GCODE mark: %s" % eline)
                    self.app.inform.emit(_('[ERROR_NOTCL] This is GCODE mark: %s') % eline)
                    return

                # Header Begin (M48) #
                if self.hbegin_re.search(eline):
                    in_header = True
                    headerless = False
                    log.warning("Found start of the header: %s" % eline)
                    continue

                # Allegro Header Begin (;HEADER) #
                if self.allegro_hbegin_re.search(eline):
                    in_header = True
                    allegro_warning = True
                    log.warning("Found ALLEGRO start of the header: %s" % eline)
                    continue

                # Search for Header End #
                # Since there might be comments in the header that include header end char (% or M95)
                # we ignore the lines starting with ';' that contains such header end chars because it is not a
                # real header end.
                if self.comm_re.search(eline):
                    match = self.tool_units_re.search(eline)
                    if match:
                        if line_units_found is False:
                            line_units_found = True
                            line_units = match.group(3)
                            self.convert_units({"MILS": "IN", "MM": "MM"}[line_units])
                            log.warning("Type of Allegro UNITS found inline in comments: %s" % line_units)

                        if match.group(2):
                            name_tool += 1
                            if line_units == 'MILS':
                                spec = {"C": (float(match.group(2)) / 1000)}
                                self.tools[str(name_tool)] = spec
                                log.debug("  Tool definition: %s %s" % (name_tool, spec))
                            else:
                                spec = {"C": float(match.group(2))}
                                self.tools[str(name_tool)] = spec
                                log.debug("  Tool definition: %s %s" % (name_tool, spec))
                            spec['solid_geometry'] = []
                            continue
                    # search for Altium Excellon Format / Sprint Layout who is included as a comment
                    match = self.altium_format.search(eline)
                    if match:
                        self.excellon_format_upper_mm = match.group(1)
                        self.excellon_format_lower_mm = match.group(2)

                        self.excellon_format_upper_in = match.group(1)
                        self.excellon_format_lower_in = match.group(2)
                        log.warning("Altium Excellon format preset found in comments: %s:%s" %
                                    (match.group(1), match.group(2)))
                        continue
                    else:
                        log.warning("Line ignored, it's a comment: %s" % eline)
                else:
                    if self.hend_re.search(eline):
                        if in_header is False or bool(self.tools) is False:
                            log.warning("Found end of the header but there is no header: %s" % eline)
                            log.warning("The only useful data in header are tools, units and format.")
                            log.warning("Therefore we will create units and format based on defaults.")
                            headerless = True
                            try:
                                self.convert_units({"INCH": "IN", "METRIC": "MM"}[self.excellon_units])
                            except Exception as e:
                                log.warning("Units could not be converted: %s" % str(e))

                        in_header = False
                        # for Allegro type of Excellons we reset name_tool variable so we can reuse it for toolchange
                        if allegro_warning is True:
                            name_tool = 0
                        log.warning("Found end of the header: %s" % eline)
                        continue

                # ## Alternative units format M71/M72
                # Supposed to be just in the body (yes, the body)
                # but some put it in the header (PADS for example).
                # Will detect anywhere. Occurrence will change the
                # object's units.
                match = self.meas_re.match(eline)
                if match:
                    #self.units = {"1": "MM", "2": "IN"}[match.group(1)]

                    # Modified for issue #80
                    self.convert_units({"1": "MM", "2": "IN"}[match.group(1)])
                    log.debug("  Units: %s" % self.units)
                    if self.units == 'MM':
                        log.warning("Excellon format preset is: %s" % self.excellon_format_upper_mm + \
                                    ':' + str(self.excellon_format_lower_mm))
                    else:
                        log.warning("Excellon format preset is: %s" % self.excellon_format_upper_in + \
                        ':' + str(self.excellon_format_lower_in))
                    continue

                # ### Body ####
                if not in_header:

                    # ## Tool change ###
                    match = self.toolsel_re.search(eline)
                    if match:
                        current_tool = str(int(match.group(1)))
                        log.debug("Tool change: %s" % current_tool)
                        if bool(headerless):
                            match = self.toolset_hl_re.search(eline)
                            if match:
                                name = str(int(match.group(1)))
                                try:
                                    diam = float(match.group(2))
                                except:
                                    # it's possible that tool definition has only tool number and no diameter info
                                    # (those could be in another file like PCB Wizard do)
                                    # then match.group(2) = None and float(None) will create the exception
                                    # the bellow construction is so each tool will have a slightly different diameter
                                    # starting with a default value, to allow Excellon editing after that
                                    self.diameterless = True
                                    self.app.inform.emit(_("[WARNING] No tool diameter info's. See shell.\n"
                                                           "A tool change event: T%s was found but the Excellon file "
                                                           "have no informations regarding the tool "
                                                           "diameters therefore the application will try to load it by "
                                                           "using some 'fake' diameters.\nThe user needs to edit the "
                                                           "resulting Excellon object and change the diameters to "
                                                           "reflect the real diameters.") % current_tool)

                                    if self.excellon_units == 'MM':
                                        diam = self.toolless_diam + (int(current_tool) - 1) / 100
                                    else:
                                        diam = (self.toolless_diam + (int(current_tool) - 1) / 100) / 25.4

                                spec = {"C": diam, 'solid_geometry': []}
                                self.tools[name] = spec
                                log.debug("Tool definition out of header: %s %s" % (name, spec))

                        continue

                    # ## Allegro Type Tool change ###
                    if allegro_warning is True:
                        match = self.absinc_re.search(eline)
                        match1 = self.stop_re.search(eline)
                        if match or match1:
                            name_tool += 1
                            current_tool = str(name_tool)
                            log.debug("Tool change for Allegro type of Excellon: %s" % current_tool)
                            continue

                    # ## Slots parsing for drilled slots (contain G85)
                    # a Excellon drilled slot line may look like this:
                    # X01125Y0022244G85Y0027756
                    match = self.slots_re.search(eline)
                    if match:
                        # signal that there are milling slots operations
                        self.defaults['excellon_drills'] = False

                        # the slot start coordinates group is to the left of G85 command (group(1) )
                        # the slot stop coordinates group is to the right of G85 command (group(2) )
                        start_coords_match = match.group(1)
                        stop_coords_match = match.group(2)

                        # Slot coordinates without period # ##
                        # get the coordinates for slot start and for slot stop into variables
                        start_coords_noperiod = self.coordsnoperiod_re.search(start_coords_match)
                        stop_coords_noperiod = self.coordsnoperiod_re.search(stop_coords_match)
                        if start_coords_noperiod:
                            try:
                                slot_start_x = self.parse_number(start_coords_noperiod.group(1))
                                slot_current_x = slot_start_x
                            except TypeError:
                                slot_start_x = slot_current_x
                            except:
                                return

                            try:
                                slot_start_y = self.parse_number(start_coords_noperiod.group(2))
                                slot_current_y = slot_start_y
                            except TypeError:
                                slot_start_y = slot_current_y
                            except:
                                return

                            try:
                                slot_stop_x = self.parse_number(stop_coords_noperiod.group(1))
                                slot_current_x = slot_stop_x
                            except TypeError:
                                slot_stop_x = slot_current_x
                            except:
                                return

                            try:
                                slot_stop_y = self.parse_number(stop_coords_noperiod.group(2))
                                slot_current_y = slot_stop_y
                            except TypeError:
                                slot_stop_y = slot_current_y
                            except:
                                return

                            if (slot_start_x is None or slot_start_y is None or
                                                slot_stop_x is None or slot_stop_y is None):
                                log.error("Slots are missing some or all coordinates.")
                                continue

                            # we have a slot
                            log.debug('Parsed a slot with coordinates: ' + str([slot_start_x,
                                                                               slot_start_y, slot_stop_x,
                                                                               slot_stop_y]))

                            # store current tool diameter as slot diameter
                            slot_dia = 0.05
                            try:
                                slot_dia = float(self.tools[current_tool]['C'])
                            except Exception as e:
                                pass
                            log.debug(
                                'Milling/Drilling slot with tool %s, diam=%f' % (
                                    current_tool,
                                    slot_dia
                                )
                            )

                            self.slots.append(
                                {
                                    'start': Point(slot_start_x, slot_start_y),
                                    'stop': Point(slot_stop_x, slot_stop_y),
                                    'tool': current_tool
                                }
                            )
                            continue

                        # Slot coordinates with period: Use literally. ###
                        # get the coordinates for slot start and for slot stop into variables
                        start_coords_period = self.coordsperiod_re.search(start_coords_match)
                        stop_coords_period = self.coordsperiod_re.search(stop_coords_match)
                        if start_coords_period:

                            try:
                                slot_start_x = float(start_coords_period.group(1))
                                slot_current_x = slot_start_x
                            except TypeError:
                                slot_start_x = slot_current_x
                            except:
                                return

                            try:
                                slot_start_y = float(start_coords_period.group(2))
                                slot_current_y = slot_start_y
                            except TypeError:
                                slot_start_y = slot_current_y
                            except:
                                return

                            try:
                                slot_stop_x = float(stop_coords_period.group(1))
                                slot_current_x = slot_stop_x
                            except TypeError:
                                slot_stop_x = slot_current_x
                            except:
                                return

                            try:
                                slot_stop_y = float(stop_coords_period.group(2))
                                slot_current_y = slot_stop_y
                            except TypeError:
                                slot_stop_y = slot_current_y
                            except:
                                return

                            if (slot_start_x is None or slot_start_y is None or
                                                slot_stop_x is None or slot_stop_y is None):
                                log.error("Slots are missing some or all coordinates.")
                                continue

                            # we have a slot
                            log.debug('Parsed a slot with coordinates: ' + str([slot_start_x,
                                                                            slot_start_y, slot_stop_x, slot_stop_y]))

                            # store current tool diameter as slot diameter
                            slot_dia = 0.05
                            try:
                                slot_dia = float(self.tools[current_tool]['C'])
                            except Exception as e:
                                pass
                            log.debug(
                                'Milling/Drilling slot with tool %s, diam=%f' % (
                                    current_tool,
                                    slot_dia
                                )
                            )

                            self.slots.append(
                                {
                                    'start': Point(slot_start_x, slot_start_y),
                                    'stop': Point(slot_stop_x, slot_stop_y),
                                    'tool': current_tool
                                }
                            )
                        continue

                    # ## Coordinates without period # ##
                    match = self.coordsnoperiod_re.search(eline)
                    if match:
                        matchr = self.repeat_re.search(eline)
                        if matchr:
                            repeat = int(matchr.group(1))

                        try:
                            x = self.parse_number(match.group(1))
                            repeating_x = current_x
                            current_x = x
                        except TypeError:
                            x = current_x
                            repeating_x = 0
                        except:
                            return

                        try:
                            y = self.parse_number(match.group(2))
                            repeating_y = current_y
                            current_y = y
                        except TypeError:
                            y = current_y
                            repeating_y = 0
                        except:
                            return

                        if x is None or y is None:
                            log.error("Missing coordinates")
                            continue

                        # ## Excellon Routing parse
                        if len(re.findall("G00", eline)) > 0:
                            self.match_routing_start = 'G00'

                            # signal that there are milling slots operations
                            self.defaults['excellon_drills'] = False

                            self.routing_flag = 0
                            slot_start_x = x
                            slot_start_y = y
                            continue

                        if self.routing_flag == 0:
                            if len(re.findall("G01", eline)) > 0:
                                self.match_routing_stop = 'G01'

                                # signal that there are milling slots operations
                                self.defaults['excellon_drills'] = False

                                self.routing_flag = 1
                                slot_stop_x = x
                                slot_stop_y = y
                                self.slots.append(
                                    {
                                        'start': Point(slot_start_x, slot_start_y),
                                        'stop': Point(slot_stop_x, slot_stop_y),
                                        'tool': current_tool
                                    }
                                )
                                continue

                        if self.match_routing_start is None and self.match_routing_stop is None:
                            if repeat == 0:
                                # signal that there are drill operations
                                self.defaults['excellon_drills'] = True
                                self.drills.append({'point': Point((x, y)), 'tool': current_tool})
                            else:
                                coordx = x
                                coordy = y
                                while repeat > 0:
                                    if repeating_x:
                                        coordx = (repeat * x) + repeating_x
                                    if repeating_y:
                                        coordy = (repeat * y) + repeating_y
                                    self.drills.append({'point': Point((coordx, coordy)), 'tool': current_tool})
                                    repeat -= 1
                            repeating_x = repeating_y = 0
                            # log.debug("{:15} {:8} {:8}".format(eline, x, y))
                            continue

                    # ## Coordinates with period: Use literally. # ##
                    match = self.coordsperiod_re.search(eline)
                    if match:
                        matchr = self.repeat_re.search(eline)
                        if matchr:
                            repeat = int(matchr.group(1))

                    if match:
                        # signal that there are drill operations
                        self.defaults['excellon_drills'] = True
                        try:
                            x = float(match.group(1))
                            repeating_x = current_x
                            current_x = x
                        except TypeError:
                            x = current_x
                            repeating_x = 0

                        try:
                            y = float(match.group(2))
                            repeating_y = current_y
                            current_y = y
                        except TypeError:
                            y = current_y
                            repeating_y = 0

                        if x is None or y is None:
                            log.error("Missing coordinates")
                            continue

                        # ## Excellon Routing parse
                        if len(re.findall("G00", eline)) > 0:
                            self.match_routing_start = 'G00'

                            # signal that there are milling slots operations
                            self.defaults['excellon_drills'] = False

                            self.routing_flag = 0
                            slot_start_x = x
                            slot_start_y = y
                            continue

                        if self.routing_flag == 0:
                            if len(re.findall("G01", eline)) > 0:
                                self.match_routing_stop = 'G01'

                                # signal that there are milling slots operations
                                self.defaults['excellon_drills'] = False

                                self.routing_flag = 1
                                slot_stop_x = x
                                slot_stop_y = y
                                self.slots.append(
                                    {
                                        'start': Point(slot_start_x, slot_start_y),
                                        'stop': Point(slot_stop_x, slot_stop_y),
                                        'tool': current_tool
                                    }
                                )
                                continue

                        if self.match_routing_start is None and self.match_routing_stop is None:
                            # signal that there are drill operations
                            if repeat == 0:
                                # signal that there are drill operations
                                self.defaults['excellon_drills'] = True
                                self.drills.append({'point': Point((x, y)), 'tool': current_tool})
                            else:
                                coordx = x
                                coordy = y
                                while repeat > 0:
                                    if repeating_x:
                                        coordx = (repeat * x) + repeating_x
                                    if repeating_y:
                                        coordy = (repeat * y) + repeating_y
                                    self.drills.append({'point': Point((coordx, coordy)), 'tool': current_tool})
                                    repeat -= 1
                            repeating_x = repeating_y = 0
                            # log.debug("{:15} {:8} {:8}".format(eline, x, y))
                            continue

                # ### Header ####
                if in_header:

                    # ## Tool definitions # ##
                    match = self.toolset_re.search(eline)
                    if match:

                        name = str(int(match.group(1)))
                        spec = {"C": float(match.group(2)), 'solid_geometry': []}
                        self.tools[name] = spec
                        log.debug("  Tool definition: %s %s" % (name, spec))
                        continue

                    # ## Units and number format # ##
                    match = self.units_re.match(eline)
                    if match:
                        self.units_found = match.group(1)
                        self.zeros = match.group(2)  # "T" or "L". Might be empty
                        self.excellon_format = match.group(3)
                        if self.excellon_format:
                            upper = len(self.excellon_format.partition('.')[0])
                            lower = len(self.excellon_format.partition('.')[2])
                            if self.units == 'MM':
                                self.excellon_format_upper_mm = upper
                                self.excellon_format_lower_mm = lower
                            else:
                                self.excellon_format_upper_in = upper
                                self.excellon_format_lower_in = lower

                        # Modified for issue #80
                        self.convert_units({"INCH": "IN", "METRIC": "MM"}[self.units_found])
                        # log.warning("  Units/Format: %s %s" % (self.units, self.zeros))
                        log.warning("Units: %s" % self.units)
                        if self.units == 'MM':
                            log.warning("Excellon format preset is: %s" % str(self.excellon_format_upper_mm) +
                                        ':' + str(self.excellon_format_lower_mm))
                        else:
                            log.warning("Excellon format preset is: %s" % str(self.excellon_format_upper_in) +
                                        ':' + str(self.excellon_format_lower_in))
                        log.warning("Type of zeros found inline: %s" % self.zeros)
                        continue

                    # Search for units type again it might be alone on the line
                    if "INCH" in eline:
                        line_units = "INCH"
                        # Modified for issue #80
                        self.convert_units({"INCH": "IN", "METRIC": "MM"}[line_units])
                        log.warning("Type of UNITS found inline: %s" % line_units)
                        log.warning("Excellon format preset is: %s" % str(self.excellon_format_upper_in) +
                                    ':' + str(self.excellon_format_lower_in))
                        # TODO: not working
                        #FlatCAMApp.App.inform.emit("Detected INLINE: %s" % str(eline))
                        continue
                    elif "METRIC" in eline:
                        line_units = "METRIC"
                        # Modified for issue #80
                        self.convert_units({"INCH": "IN", "METRIC": "MM"}[line_units])
                        log.warning("Type of UNITS found inline: %s" % line_units)
                        log.warning("Excellon format preset is: %s" % str(self.excellon_format_upper_mm) +
                                    ':' + str(self.excellon_format_lower_mm))
                        # TODO: not working
                        #FlatCAMApp.App.inform.emit("Detected INLINE: %s" % str(eline))
                        continue

                    # Search for zeros type again because it might be alone on the line
                    match = re.search(r'[LT]Z',eline)
                    if match:
                        self.zeros = match.group()
                        log.warning("Type of zeros found: %s" % self.zeros)
                        continue

                # ## Units and number format outside header# ##
                match = self.units_re.match(eline)
                if match:
                    self.units_found = match.group(1)
                    self.zeros = match.group(2)  # "T" or "L". Might be empty
                    self.excellon_format = match.group(3)
                    if self.excellon_format:
                        upper = len(self.excellon_format.partition('.')[0])
                        lower = len(self.excellon_format.partition('.')[2])
                        if self.units == 'MM':
                            self.excellon_format_upper_mm = upper
                            self.excellon_format_lower_mm = lower
                        else:
                            self.excellon_format_upper_in = upper
                            self.excellon_format_lower_in = lower

                    # Modified for issue #80
                    self.convert_units({"INCH": "IN", "METRIC": "MM"}[self.units_found])
                    # log.warning("  Units/Format: %s %s" % (self.units, self.zeros))
                    log.warning("Units: %s" % self.units)
                    if self.units == 'MM':
                        log.warning("Excellon format preset is: %s" % str(self.excellon_format_upper_mm) +
                                    ':' + str(self.excellon_format_lower_mm))
                    else:
                        log.warning("Excellon format preset is: %s" % str(self.excellon_format_upper_in) +
                                    ':' + str(self.excellon_format_lower_in))
                    log.warning("Type of zeros found outside header, inline: %s" % self.zeros)

                    log.warning("UNITS found outside header")
                    continue

                log.warning("Line ignored: %s" % eline)

            # make sure that since we are in headerless mode, we convert the tools only after the file parsing
            # is finished since the tools definitions are spread in the Excellon body. We use as units the value
            # from self.defaults['excellon_units']
            log.info("Zeros: %s, Units %s." % (self.zeros, self.units))
        except Exception as e:
            log.error("Excellon PARSING FAILED. Line %d: %s" % (line_num, eline))
            msg = _("[ERROR_NOTCL] An internal error has ocurred. See shell.\n")
            msg += _('[ERROR] Excellon Parser error.\nParsing Failed. Line {l_nr}: {line}\n').format(l_nr=line_num,
                                                                                                     line=eline)
            msg += traceback.format_exc()
            self.app.inform.emit(msg)

            return "fail"
        
    def parse_number(self, number_str):
        """
        Parses coordinate numbers without period.

        :param number_str: String representing the numerical value.
        :type number_str: str
        :return: Floating point representation of the number
        :rtype: float
        """

        match = self.leadingzeros_re.search(number_str)
        nr_length = len(match.group(1)) + len(match.group(2))
        try:
            if self.zeros == "L" or self.zeros == "LZ": # Leading
                # With leading zeros, when you type in a coordinate,
                # the leading zeros must always be included.  Trailing zeros
                # are unneeded and may be left off. The CNC-7 will automatically add them.
                # r'^[-\+]?(0*)(\d*)'
                # 6 digits are divided by 10^4
                # If less than size digits, they are automatically added,
                # 5 digits then are divided by 10^3 and so on.

                if self.units.lower() == "in":
                    result = float(number_str) / (10 ** (float(nr_length) - float(self.excellon_format_upper_in)))
                else:
                    result = float(number_str) / (10 ** (float(nr_length) - float(self.excellon_format_upper_mm)))
                return result
            else:  # Trailing
                # You must show all zeros to the right of the number and can omit
                # all zeros to the left of the number. The CNC-7 will count the number
                # of digits you typed and automatically fill in the missing zeros.
                # ## flatCAM expects 6digits
                # flatCAM expects the number of digits entered into the defaults

                if self.units.lower() == "in":  # Inches is 00.0000
                    result = float(number_str) / (10 ** (float(self.excellon_format_lower_in)))
                else:   # Metric is 000.000
                    result = float(number_str) / (10 ** (float(self.excellon_format_lower_mm)))
                return result
        except Exception as e:
            log.error("Aborted. Operation could not be completed due of %s" % str(e))
            return

    def create_geometry(self):
        """
        Creates circles of the tool diameter at every point
        specified in ``self.drills``. Also creates geometries (polygons)
        for the slots as specified in ``self.slots``
        All the resulting geometry is stored into self.solid_geometry list.
        The list self.solid_geometry has 2 elements: first is a dict with the drills geometry,
        and second element is another similar dict that contain the slots geometry.

        Each dict has as keys the tool diameters and as values lists with Shapely objects, the geometries
        ================  ====================================
        Key               Value
        ================  ====================================
        tool_diameter     list of (Shapely.Point) Where to drill
        ================  ====================================

        :return: None
        """
        self.solid_geometry = []
        try:
            # clear the solid_geometry in self.tools
            for tool in self.tools:
                try:
                    self.tools[tool]['solid_geometry'][:] = []
                except KeyError:
                    self.tools[tool]['solid_geometry'] = []

            for drill in self.drills:
                # poly = drill['point'].buffer(self.tools[drill['tool']]["C"]/2.0)
                if drill['tool'] is '':
                    self.app.inform.emit(_("[WARNING] Excellon.create_geometry() -> a drill location was skipped "
                                           "due of not having a tool associated.\n"
                                           "Check the resulting GCode."))
                    log.debug("Excellon.create_geometry() -> a drill location was skipped "
                              "due of not having a tool associated")
                    continue
                tooldia = self.tools[drill['tool']]['C']
                poly = drill['point'].buffer(tooldia / 2.0, int(int(self.geo_steps_per_circle) / 4))
                self.solid_geometry.append(poly)
                self.tools[drill['tool']]['solid_geometry'].append(poly)

            for slot in self.slots:
                slot_tooldia = self.tools[slot['tool']]['C']
                start = slot['start']
                stop = slot['stop']

                lines_string = LineString([start, stop])
                poly = lines_string.buffer(slot_tooldia / 2.0, int(int(self.geo_steps_per_circle) / 4))
                self.solid_geometry.append(poly)
                self.tools[slot['tool']]['solid_geometry'].append(poly)

        except Exception as e:
            log.debug("Excellon geometry creation failed due of ERROR: %s" % str(e))
            return "fail"

        # drill_geometry = {}
        # slot_geometry = {}
        #
        # def insertIntoDataStruct(dia, drill_geo, aDict):
        #     if not dia in aDict:
        #         aDict[dia] = [drill_geo]
        #     else:
        #         aDict[dia].append(drill_geo)
        #
        # for tool in self.tools:
        #     tooldia = self.tools[tool]['C']
        #     for drill in self.drills:
        #         if drill['tool'] == tool:
        #             poly = drill['point'].buffer(tooldia / 2.0)
        #             insertIntoDataStruct(tooldia, poly, drill_geometry)
        #
        # for tool in self.tools:
        #     slot_tooldia = self.tools[tool]['C']
        #     for slot in self.slots:
        #         if slot['tool'] == tool:
        #             start = slot['start']
        #             stop = slot['stop']
        #             lines_string = LineString([start, stop])
        #             poly = lines_string.buffer(slot_tooldia/2.0, self.geo_steps_per_circle)
        #             insertIntoDataStruct(slot_tooldia, poly, drill_geometry)
        #
        # self.solid_geometry = [drill_geometry, slot_geometry]

    def bounds(self):
        """
        Returns coordinates of rectangular bounds
        of Gerber geometry: (xmin, ymin, xmax, ymax).
        """
        # fixed issue of getting bounds only for one level lists of objects
        # now it can get bounds for nested lists of objects

        log.debug("camlib.Excellon.bounds()")
        if self.solid_geometry is None:
            log.debug("solid_geometry is None")
            return 0, 0, 0, 0

        def bounds_rec(obj):
            if type(obj) is list:
                minx = Inf
                miny = Inf
                maxx = -Inf
                maxy = -Inf

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

        minx_list = []
        miny_list = []
        maxx_list = []
        maxy_list = []

        for tool in self.tools:
            minx, miny, maxx, maxy = bounds_rec(self.tools[tool]['solid_geometry'])
            minx_list.append(minx)
            miny_list.append(miny)
            maxx_list.append(maxx)
            maxy_list.append(maxy)

        return (min(minx_list), min(miny_list), max(maxx_list), max(maxy_list))

    def convert_units(self, units):
        """
        This function first convert to the the units found in the Excellon file but it converts tools that
        are not there yet so it has no effect other than it signal that the units are the ones in the file.

        On object creation, in new_object(), true conversion is done because this is done at the end of the
        Excellon file parsing, the tools are inside and self.tools is really converted from the units found
        inside the file to the FlatCAM units.

        Kind of convolute way to make the conversion and it is based on the assumption that the Excellon file
        will have detected the units before the tools are parsed and stored in self.tools
        :param units:
        :type str: IN or MM
        :return:
        """
        log.debug("camlib.Excellon.convert_units()")

        factor = Geometry.convert_units(self, units)

        # Tools
        for tname in self.tools:
            self.tools[tname]["C"] *= factor

        self.create_geometry()

        return factor

    def scale(self, xfactor, yfactor=None, point=None):
        """
        Scales geometry on the XY plane in the object by a given factor.
        Tool sizes, feedrates an Z-plane dimensions are untouched.

        :param factor: Number by which to scale the object.
        :type factor: float
        :return: None
        :rtype: NOne
        """
        log.debug("camlib.Excellon.scale()")

        if yfactor is None:
            yfactor = xfactor

        if point is None:
            px = 0
            py = 0
        else:
            px, py = point

        def scale_geom(obj):
            if type(obj) is list:
                new_obj = []
                for g in obj:
                    new_obj.append(scale_geom(g))
                return new_obj
            else:
                try:
                    return affinity.scale(obj, xfactor, yfactor, origin=(px, py))
                except AttributeError:
                    return obj

        # Drills
        for drill in self.drills:
            drill['point'] = affinity.scale(drill['point'], xfactor, yfactor, origin=(px, py))

        # scale solid_geometry
        for tool in self.tools:
            self.tools[tool]['solid_geometry'] = scale_geom(self.tools[tool]['solid_geometry'])

        # Slots
        for slot in self.slots:
            slot['stop'] = affinity.scale(slot['stop'], xfactor, yfactor, origin=(px, py))
            slot['start'] = affinity.scale(slot['start'], xfactor, yfactor, origin=(px, py))

        self.create_geometry()

    def offset(self, vect):
        """
        Offsets geometry on the XY plane in the object by a given vector.

        :param vect: (x, y) offset vector.
        :type vect: tuple
        :return: None
        """
        log.debug("camlib.Excellon.offset()")

        dx, dy = vect

        def offset_geom(obj):
            if type(obj) is list:
                new_obj = []
                for g in obj:
                    new_obj.append(offset_geom(g))
                return new_obj
            else:
                try:
                    return affinity.translate(obj, xoff=dx, yoff=dy)
                except AttributeError:
                    return obj

        # Drills
        for drill in self.drills:
            drill['point'] = affinity.translate(drill['point'], xoff=dx, yoff=dy)

        # offset solid_geometry
        for tool in self.tools:
            self.tools[tool]['solid_geometry'] = offset_geom(self.tools[tool]['solid_geometry'])

        # Slots
        for slot in self.slots:
            slot['stop'] = affinity.translate(slot['stop'], xoff=dx, yoff=dy)
            slot['start'] = affinity.translate(slot['start'],xoff=dx, yoff=dy)

        # Recreate geometry
        self.create_geometry()

    def mirror(self, axis, point):
        """

        :param axis: "X" or "Y" indicates around which axis to mirror.
        :type axis: str
        :param point: [x, y] point belonging to the mirror axis.
        :type point: list
        :return: None
        """
        log.debug("camlib.Excellon.mirror()")

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
                    return affinity.scale(obj, xscale, yscale, origin=(px, py))
                except AttributeError:
                    return obj

        # Modify data
        # Drills
        for drill in self.drills:
            drill['point'] = affinity.scale(drill['point'], xscale, yscale, origin=(px, py))

        # mirror solid_geometry
        for tool in self.tools:
            self.tools[tool]['solid_geometry'] = mirror_geom(self.tools[tool]['solid_geometry'])

        # Slots
        for slot in self.slots:
            slot['stop'] = affinity.scale(slot['stop'], xscale, yscale, origin=(px, py))
            slot['start'] = affinity.scale(slot['start'], xscale, yscale, origin=(px, py))

        # Recreate geometry
        self.create_geometry()

    def skew(self, angle_x=None, angle_y=None, point=None):
        """
        Shear/Skew the geometries of an object by angles along x and y dimensions.
        Tool sizes, feedrates an Z-plane dimensions are untouched.

        Parameters
        ----------
        xs, ys : float, float
            The shear angle(s) for the x and y axes respectively. These can be
            specified in either degrees (default) or radians by setting
            use_radians=True.

        See shapely manual for more information:
        http://toblerity.org/shapely/manual.html#affine-transformations
        """
        log.debug("camlib.Excellon.skew()")

        if angle_x is None:
            angle_x = 0.0

        if angle_y is None:
            angle_y = 0.0

        def skew_geom(obj):
            if type(obj) is list:
                new_obj = []
                for g in obj:
                    new_obj.append(skew_geom(g))
                return new_obj
            else:
                try:
                    return affinity.skew(obj, angle_x, angle_y, origin=(px, py))
                except AttributeError:
                    return obj

        if point is None:
            px, py = 0, 0

            # Drills
            for drill in self.drills:
                drill['point'] = affinity.skew(drill['point'], angle_x, angle_y,
                                               origin=(px, py))
            # skew solid_geometry
            for tool in self.tools:
                self.tools[tool]['solid_geometry'] = skew_geom(self.tools[tool]['solid_geometry'])

            # Slots
            for slot in self.slots:
                slot['stop'] = affinity.skew(slot['stop'], angle_x, angle_y, origin=(px, py))
                slot['start'] = affinity.skew(slot['start'], angle_x, angle_y, origin=(px, py))
        else:
            px, py = point
            # Drills
            for drill in self.drills:
                drill['point'] = affinity.skew(drill['point'], angle_x, angle_y,
                                               origin=(px, py))

            # skew solid_geometry
            for tool in self.tools:
                self.tools[tool]['solid_geometry'] = skew_geom( self.tools[tool]['solid_geometry'])

            # Slots
            for slot in self.slots:
                slot['stop'] = affinity.skew(slot['stop'], angle_x, angle_y, origin=(px, py))
                slot['start'] = affinity.skew(slot['start'], angle_x, angle_y, origin=(px, py))

        self.create_geometry()

    def rotate(self, angle, point=None):
        """
        Rotate the geometry of an object by an angle around the 'point' coordinates
        :param angle:
        :param point: tuple of coordinates (x, y)
        :return:
        """
        log.debug("camlib.Excellon.rotate()")

        def rotate_geom(obj, origin=None):
            if type(obj) is list:
                new_obj = []
                for g in obj:
                    new_obj.append(rotate_geom(g))
                return new_obj
            else:
                if origin:
                    try:
                        return affinity.rotate(obj, angle, origin=origin)
                    except AttributeError:
                        return obj
                else:
                    try:
                        return affinity.rotate(obj, angle, origin=(px, py))
                    except AttributeError:
                        return obj

        if point is None:
            # Drills
            for drill in self.drills:
                drill['point'] = affinity.rotate(drill['point'], angle, origin='center')

            # rotate solid_geometry
            for tool in self.tools:
                self.tools[tool]['solid_geometry'] = rotate_geom(self.tools[tool]['solid_geometry'], origin='center')

            # Slots
            for slot in self.slots:
                slot['stop'] = affinity.rotate(slot['stop'], angle, origin='center')
                slot['start'] = affinity.rotate(slot['start'], angle, origin='center')
        else:
            px, py = point
            # Drills
            for drill in self.drills:
                drill['point'] = affinity.rotate(drill['point'], angle, origin=(px, py))

            # rotate solid_geometry
            for tool in self.tools:
                self.tools[tool]['solid_geometry'] = rotate_geom(self.tools[tool]['solid_geometry'])

            # Slots
            for slot in self.slots:
                slot['stop'] = affinity.rotate(slot['stop'], angle, origin=(px, py))
                slot['start'] = affinity.rotate(slot['start'], angle, origin=(px, py))

        self.create_geometry()


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
        "pp_geometry_name":'default',
        "pp_excellon_name":'default',
        "excellon_optimization_type": "B",
    }

    def __init__(self,
                 units="in", kind="generic", tooldia=0.0,
                 z_cut=-0.002, z_move=0.1,
                 feedrate=3.0, feedrate_z=3.0, feedrate_rapid=3.0, feedrate_probe=3.0,
                 pp_geometry_name='default', pp_excellon_name='default',
                 depthpercut=0.1,z_pdepth=-0.02,
                 spindlespeed=None, spindledir='CW', dwell=True, dwelltime=1000,
                 toolchangez=0.787402, toolchange_xy=[0.0, 0.0],
                 endz=2.0,
                 segx=None,
                 segy=None,
                 steps_per_circle=None):

        # Used when parsing G-code arcs
        self.steps_per_circle = int(self.app.defaults['cncjob_steps_per_circle'])

        Geometry.__init__(self, geo_steps_per_circle=self.steps_per_circle)

        self.kind = kind
        self.origin_kind = None

        self.units = units

        self.z_cut = z_cut
        self.tool_offset = {}

        self.z_move = z_move

        self.feedrate = feedrate
        self.z_feedrate = feedrate_z
        self.feedrate_rapid = feedrate_rapid

        self.tooldia = tooldia
        self.z_toolchange = toolchangez
        self.xy_toolchange = toolchange_xy
        self.toolchange_xy_type = None

        self.toolC = tooldia

        self.z_end = endz
        self.z_depthpercut = depthpercut

        self.unitcode = {"IN": "G20", "MM": "G21"}

        self.feedminutecode = "G94"
        # self.absolutecode = "G90"
        # self.incrementalcode = "G91"
        self.coordinates_type = self.app.defaults["cncjob_coords_type"]

        self.gcode = ""
        self.gcode_parsed = None

        self.pp_geometry_name = pp_geometry_name
        self.pp_geometry = self.app.postprocessors[self.pp_geometry_name]

        self.pp_excellon_name = pp_excellon_name
        self.pp_excellon = self.app.postprocessors[self.pp_excellon_name]

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

        # here store the travelled distance
        self.travel_distance = 0.0
        # here store the routing time
        self.routing_time = 0.0

        # used for creating drill CCode geometry; will be updated in the generate_from_excellon_by_tool()
        self.exc_drills = None
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
        return self.__dict__

    def convert_units(self, units):
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
        attributes = AttrDict()
        attributes.update(self.postdata)
        attributes.update(kwargs)
        try:
            returnvalue = fun(attributes)
            return returnvalue
        except Exception as e:
            self.app.log.error('Exception occurred within a postprocessor: ' + traceback.format_exc())
            return ''

    def parse_custom_toolchange_code(self, data):
        text = data
        match_list = self.re_toolchange_custom.findall(text)

        if match_list:
            for match in match_list:
                command = match.strip('%')
                try:
                    value = getattr(self, command)
                except AttributeError:
                    self.app.inform.emit(_("[ERROR] There is no such parameter: %s") % str(match))
                    log.debug("CNCJob.parse_custom_toolchange_code() --> AttributeError ")
                    return 'fail'
                text = text.replace(match, str(value))
            return text

    def optimized_travelling_salesman(self, points, start=None):
        """
        As solving the problem in the brute force way is too slow,
        this function implements a simple heuristic: always
        go to the nearest city.

        Even if this algorithm is extremely simple, it works pretty well
        giving a solution only about 25% longer than the optimal one (cit. Wikipedia),
        and runs very fast in O(N^2) time complexity.

        >>> optimized_travelling_salesman([[i,j] for i in range(5) for j in range(5)])
        [[0, 0], [0, 1], [0, 2], [0, 3], [0, 4], [1, 4], [1, 3], [1, 2], [1, 1], [1, 0], [2, 0], [2, 1], [2, 2],
        [2, 3], [2, 4], [3, 4], [3, 3], [3, 2], [3, 1], [3, 0], [4, 0], [4, 1], [4, 2], [4, 3], [4, 4]]
        >>> optimized_travelling_salesman([[0,0],[10,0],[6,0]])
        [[0, 0], [6, 0], [10, 0]]
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

    def generate_from_excellon_by_tool(self, exobj, tools="all", drillz = 3.0,
                                       toolchange=False, toolchangez=0.1, toolchangexy='',
                                       endz=2.0, startz=None,
                                       excellon_optimization_type='B'):
        """
        Creates gcode for this object from an Excellon object
        for the specified tools.

        :param exobj: Excellon object to process
        :type exobj: Excellon
        :param tools: Comma separated tool names
        :type: tools: str
        :param drillz: drill Z depth
        :type drillz: float
        :param toolchange: Use tool change sequence between tools.
        :type toolchange: bool
        :param toolchangez: Height at which to perform the tool change.
        :type toolchangez: float
        :param toolchangexy: Toolchange X,Y position
        :type toolchangexy: String containing 2 floats separated by comma
        :param startz: Z position just before starting the job
        :type startz: float
        :param endz: final Z position to move to at the end of the CNC job
        :type endz: float
        :param excellon_optimization_type: Single character that defines which drill re-ordering optimisation algorithm
        is to be used: 'M' for meta-heuristic and 'B' for basic
        :type excellon_optimization_type: string
        :return: None
        :rtype: None
        """

        # create a local copy of the exobj.drills so it can be used for creating drill CCode geometry
        self.exc_drills = deepcopy(exobj.drills)
        self.exc_tools = deepcopy(exobj.tools)

        if drillz > 0:
            self.app.inform.emit(_("[WARNING] The Cut Z parameter has positive value. "
                                   "It is the depth value to drill into material.\n"
                                   "The Cut Z parameter needs to have a negative value, assuming it is a typo "
                                   "therefore the app will convert the value to negative. "
                                   "Check the resulting CNC code (Gcode etc)."))
            self.z_cut = -drillz
        elif drillz == 0:
            self.app.inform.emit(_("[WARNING] The Cut Z parameter is zero. "
                                   "There will be no cut, skipping %s file") % exobj.options['name'])
            return 'fail'
        else:
            self.z_cut = drillz

        self.z_toolchange = toolchangez

        try:
            if toolchangexy == '':
                self.xy_toolchange = None
            else:
                self.xy_toolchange = [float(eval(a)) for a in toolchangexy.split(",")]
                if len(self.xy_toolchange) < 2:
                    self.app.inform.emit(_("[ERROR]The Toolchange X,Y field in Edit -> Preferences has to be "
                                           "in the format (x, y) \nbut now there is only one value, not two. "))
                    return 'fail'
        except Exception as e:
            log.debug("camlib.CNCJob.generate_from_excellon_by_tool() --> %s" % str(e))
            pass

        self.startz = startz
        self.z_end = endz

        self.pp_excellon = self.app.postprocessors[self.pp_excellon_name]
        p = self.pp_excellon

        log.debug("Creating CNC Job from Excellon...")

        # Tools
        
        # sort the tools list by the second item in tuple (here we have a dict with diameter of the tool)
        # so we actually are sorting the tools by diameter
        #sorted_tools = sorted(exobj.tools.items(), key=lambda t1: t1['C'])

        sort = []
        for k, v in list(exobj.tools.items()):
            sort.append((k, v.get('C')))
        sorted_tools = sorted(sort,key=lambda t1: t1[1])

        if tools == "all":
            tools = [i[0] for i in sorted_tools]   # we get a array of ordered tools
            log.debug("Tools 'all' and sorted are: %s" % str(tools))
        else:
            selected_tools = [x.strip() for x in tools.split(",")]  # we strip spaces and also separate the tools by ','
            selected_tools = [t1 for t1 in selected_tools if t1 in selected_tools]

            # Create a sorted list of selected tools from the sorted_tools list
            tools = [i for i, j in sorted_tools for k in selected_tools if i == k]
            log.debug("Tools selected and sorted are: %s" % str(tools))

        # Points (Group by tool)
        points = {}
        for drill in exobj.drills:
            if drill['tool'] in tools:
                try:
                    points[drill['tool']].append(drill['point'])
                except KeyError:
                    points[drill['tool']] = [drill['point']]

        #log.debug("Found %d drills." % len(points))

        self.gcode = []

        self.f_plunge = self.app.defaults["excellon_f_plunge"]
        self.f_retract = self.app.defaults["excellon_f_retract"]

        # Initialization
        gcode = self.doformat(p.start_code)
        gcode += self.doformat(p.feedrate_code)

        if toolchange is False:
            if self.xy_toolchange is not None:
                gcode += self.doformat(p.lift_code, x=self.xy_toolchange[0], y=self.xy_toolchange[1])
                gcode += self.doformat(p.startz_code, x=self.xy_toolchange[0], y=self.xy_toolchange[1])
            else:
                gcode += self.doformat(p.lift_code, x=0.0, y=0.0)
                gcode += self.doformat(p.startz_code, x=0.0, y=0.0)

        # Distance callback
        class CreateDistanceCallback(object):
            """Create callback to calculate distances between points."""

            def __init__(self):
                """Initialize distance array."""
                locations = create_data_array()
                size = len(locations)
                self.matrix = {}

                for from_node in range(size):
                    self.matrix[from_node] = {}
                    for to_node in range(size):
                        if from_node == to_node:
                            self.matrix[from_node][to_node] = 0
                        else:
                            x1 = locations[from_node][0]
                            y1 = locations[from_node][1]
                            x2 = locations[to_node][0]
                            y2 = locations[to_node][1]
                            self.matrix[from_node][to_node] = distance_euclidian(x1, y1, x2, y2)

            # def Distance(self, from_node, to_node):
            #     return int(self.matrix[from_node][to_node])
            def Distance(self, from_index, to_index):
                # Convert from routing variable Index to distance matrix NodeIndex.
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                return self.matrix[from_node][to_node]

        # Create the data.
        def create_data_array():
            locations = []
            for point in points[tool]:
                locations.append((point.coords.xy[0][0], point.coords.xy[1][0]))
            return locations

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

        current_platform = platform.architecture()[0]
        if current_platform == '64bit':
            if excellon_optimization_type == 'M':
                log.debug("Using OR-Tools Metaheuristic Guided Local Search drill path optimization.")
                if exobj.drills:
                    for tool in tools:
                        self.tool=tool
                        self.postdata['toolC'] = exobj.tools[tool]["C"]
                        self.tooldia = exobj.tools[tool]["C"]

                        # ###############################################
                        # ############ Create the data. #################
                        # ###############################################

                        node_list = []
                        locations = create_data_array()
                        tsp_size = len(locations)
                        num_routes = 1  # The number of routes, which is 1 in the TSP.
                        # Nodes are indexed from 0 to tsp_size - 1. The depot is the starting node of the route.
                        depot = 0
                        # Create routing model.
                        if tsp_size > 0:
                            manager = pywrapcp.RoutingIndexManager(tsp_size, num_routes, depot)
                            routing = pywrapcp.RoutingModel(manager)
                            search_parameters = pywrapcp.DefaultRoutingSearchParameters()
                            search_parameters.local_search_metaheuristic = (
                                routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)

                            # Set search time limit in milliseconds.
                            if float(self.app.defaults["excellon_search_time"]) != 0:
                                search_parameters.time_limit.seconds = int(
                                    float(self.app.defaults["excellon_search_time"]))
                            else:
                                search_parameters.time_limit.seconds = 3

                            # Callback to the distance function. The callback takes two
                            # arguments (the from and to node indices) and returns the distance between them.
                            dist_between_locations = CreateDistanceCallback()
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
                                    node_list.append(node)
                                    node = assignment.Value(routing.NextVar(node))
                            else:
                                log.warning('No solution found.')
                        else:
                            log.warning('Specify an instance greater than 0.')
                        # ############################################# ##

                        # Only if tool has points.
                        if tool in points:
                            # Tool change sequence (optional)
                            if toolchange:
                                gcode += self.doformat(p.toolchange_code,toolchangexy=(self.oldx, self.oldy))
                                gcode += self.doformat(p.spindle_code)  # Spindle start
                                if self.dwell is True:
                                    gcode += self.doformat(p.dwell_code)  # Dwell time
                            else:
                                gcode += self.doformat(p.spindle_code)
                                if self.dwell is True:
                                    gcode += self.doformat(p.dwell_code)  # Dwell time

                            if self.units == 'MM':
                                current_tooldia = float('%.2f' % float(exobj.tools[tool]["C"]))
                            else:
                                current_tooldia = float('%.4f' % float(exobj.tools[tool]["C"]))

                            # TODO apply offset only when using the GUI, for TclCommand this will create an error
                            # because the values for Z offset are created in build_ui()
                            try:
                                z_offset = float(self.tool_offset[current_tooldia]) * (-1)
                            except KeyError:
                                z_offset = 0
                            self.z_cut += z_offset

                            self.coordinates_type = self.app.defaults["cncjob_coords_type"]
                            if self.coordinates_type == "G90":
                                # Drillling! for Absolute coordinates type G90
                                for k in node_list:
                                    locx = locations[k][0]
                                    locy = locations[k][1]

                                    gcode += self.doformat(p.rapid_code, x=locx, y=locy)
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
                            else:
                                # Drillling! for Incremental coordinates type G91
                                for k in node_list:
                                    locx = locations[k][0] - self.oldx
                                    locy = locations[k][1] - self.oldy

                                    gcode += self.doformat(p.rapid_code, x=locx, y=locy)
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
                else:
                    log.debug("camlib.CNCJob.generate_from_excellon_by_tool() --> "
                              "The loaded Excellon file has no drills ...")
                    self.app.inform.emit(_('[ERROR_NOTCL] The loaded Excellon file has no drills ...'))
                    return 'fail'

                log.debug("The total travel distance with OR-TOOLS Metaheuristics is: %s" % str(measured_distance))
            elif excellon_optimization_type == 'B':
                log.debug("Using OR-Tools Basic drill path optimization.")
                if exobj.drills:
                    for tool in tools:
                        self.tool=tool
                        self.postdata['toolC']=exobj.tools[tool]["C"]
                        self.tooldia = exobj.tools[tool]["C"]

                        # ############################################# ##
                        node_list = []
                        locations = create_data_array()
                        tsp_size = len(locations)
                        num_routes = 1  # The number of routes, which is 1 in the TSP.

                        # Nodes are indexed from 0 to tsp_size - 1. The depot is the starting node of the route.
                        depot = 0

                        # Create routing model.
                        if tsp_size > 0:
                            manager = pywrapcp.RoutingIndexManager(tsp_size, num_routes, depot)
                            routing = pywrapcp.RoutingModel(manager)
                            search_parameters = pywrapcp.DefaultRoutingSearchParameters()

                            # Callback to the distance function. The callback takes two
                            # arguments (the from and to node indices) and returns the distance between them.
                            dist_between_locations = CreateDistanceCallback()
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
                                    node_list.append(node)
                                    node = assignment.Value(routing.NextVar(node))
                            else:
                                log.warning('No solution found.')
                        else:
                            log.warning('Specify an instance greater than 0.')
                        # ############################################# ##

                        # Only if tool has points.
                        if tool in points:
                            # Tool change sequence (optional)
                            if toolchange:
                                gcode += self.doformat(p.toolchange_code,toolchangexy=(self.oldx, self.oldy))
                                gcode += self.doformat(p.spindle_code)  # Spindle start)
                                if self.dwell is True:
                                    gcode += self.doformat(p.dwell_code)  # Dwell time
                            else:
                                gcode += self.doformat(p.spindle_code)
                                if self.dwell is True:
                                    gcode += self.doformat(p.dwell_code)  # Dwell time

                            if self.units == 'MM':
                                current_tooldia = float('%.2f' % float(exobj.tools[tool]["C"]))
                            else:
                                current_tooldia = float('%.4f' % float(exobj.tools[tool]["C"]))

                            # TODO apply offset only when using the GUI, for TclCommand this will create an error
                            # because the values for Z offset are created in build_ui()
                            try:
                                z_offset = float(self.tool_offset[current_tooldia]) * (-1)
                            except KeyError:
                                z_offset = 0
                            self.z_cut += z_offset

                            self.coordinates_type = self.app.defaults["cncjob_coords_type"]
                            if self.coordinates_type == "G90":
                                # Drillling! for Absolute coordinates type G90
                                for k in node_list:
                                    locx = locations[k][0]
                                    locy = locations[k][1]

                                    gcode += self.doformat(p.rapid_code, x=locx, y=locy)
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
                            else:
                                # Drillling! for Incremental coordinates type G91
                                for k in node_list:
                                    locx = locations[k][0] - self.oldx
                                    locy = locations[k][1] - self.oldy

                                    gcode += self.doformat(p.rapid_code, x=locx, y=locy)
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
                else:
                    log.debug("camlib.CNCJob.generate_from_excellon_by_tool() --> "
                              "The loaded Excellon file has no drills ...")
                    self.app.inform.emit(_('[ERROR_NOTCL] The loaded Excellon file has no drills ...'))
                    return 'fail'

                log.debug("The total travel distance with OR-TOOLS Basic Algorithm is: %s" % str(measured_distance))
            else:
                self.app.inform.emit(_("[ERROR_NOTCL] Wrong optimization type selected."))
                return 'fail'
        else:
            log.debug("Using Travelling Salesman drill path optimization.")
            for tool in tools:
                if exobj.drills:
                    self.tool = tool
                    self.postdata['toolC'] = exobj.tools[tool]["C"]
                    self.tooldia = exobj.tools[tool]["C"]

                    # Only if tool has points.
                    if tool in points:
                        # Tool change sequence (optional)
                        if toolchange:
                            gcode += self.doformat(p.toolchange_code, toolchangexy=(self.oldx, self.oldy))
                            gcode += self.doformat(p.spindle_code)  # Spindle start)
                            if self.dwell is True:
                                gcode += self.doformat(p.dwell_code)  # Dwell time
                        else:
                            gcode += self.doformat(p.spindle_code)
                            if self.dwell is True:
                                gcode += self.doformat(p.dwell_code)  # Dwell time

                        if self.units == 'MM':
                            current_tooldia = float('%.2f' % float(exobj.tools[tool]["C"]))
                        else:
                            current_tooldia = float('%.4f' % float(exobj.tools[tool]["C"]))

                        # TODO apply offset only when using the GUI, for TclCommand this will create an error
                        # because the values for Z offset are created in build_ui()
                        try:
                            z_offset = float(self.tool_offset[current_tooldia]) * (-1)
                        except KeyError:
                            z_offset = 0
                        self.z_cut += z_offset

                        self.coordinates_type = self.app.defaults["cncjob_coords_type"]
                        if self.coordinates_type == "G90":
                            # Drillling! for Absolute coordinates type G90
                            altPoints = []
                            for point in points[tool]:
                                altPoints.append((point.coords.xy[0][0], point.coords.xy[1][0]))

                            for point in self.optimized_travelling_salesman(altPoints):
                                gcode += self.doformat(p.rapid_code, x=point[0], y=point[1])
                                gcode += self.doformat(p.down_code, x=point[0], y=point[1])

                                measured_down_distance += abs(self.z_cut) + abs(self.z_move)

                                if self.f_retract is False:
                                    gcode += self.doformat(p.up_to_zero_code, x=point[0], y=point[1])
                                    measured_up_to_zero_distance += abs(self.z_cut)
                                    measured_lift_distance += abs(self.z_move)
                                else:
                                    measured_lift_distance += abs(self.z_cut) + abs(self.z_move)

                                gcode += self.doformat(p.lift_code, x=point[0], y=point[1])
                                measured_distance += abs(distance_euclidian(point[0], point[1], self.oldx, self.oldy))
                                self.oldx = point[0]
                                self.oldy = point[1]
                        else:
                            # Drillling! for Incremental coordinates type G91
                            altPoints = []
                            for point in points[tool]:
                                altPoints.append((point.coords.xy[0][0], point.coords.xy[1][0]))

                            for point in self.optimized_travelling_salesman(altPoints):
                                point[0] = point[0] - self.oldx
                                point[1] = point[1] - self.oldy

                                gcode += self.doformat(p.rapid_code, x=point[0], y=point[1])
                                gcode += self.doformat(p.down_code, x=point[0], y=point[1])

                                measured_down_distance += abs(self.z_cut) + abs(self.z_move)

                                if self.f_retract is False:
                                    gcode += self.doformat(p.up_to_zero_code, x=point[0], y=point[1])
                                    measured_up_to_zero_distance += abs(self.z_cut)
                                    measured_lift_distance += abs(self.z_move)
                                else:
                                    measured_lift_distance += abs(self.z_cut) + abs(self.z_move)

                                gcode += self.doformat(p.lift_code, x=point[0], y=point[1])
                                measured_distance += abs(distance_euclidian(point[0], point[1], self.oldx, self.oldy))
                                self.oldx = point[0]
                                self.oldy = point[1]
                    else:
                        log.debug("camlib.CNCJob.generate_from_excellon_by_tool() --> "
                                  "The loaded Excellon file has no drills ...")
                        self.app.inform.emit(_('[ERROR_NOTCL] The loaded Excellon file has no drills ...'))
                        return 'fail'
            log.debug("The total travel distance with Travelling Salesman Algorithm is: %s" % str(measured_distance))

        gcode += self.doformat(p.spindle_stop_code)  # Spindle stop
        gcode += self.doformat(p.end_code, x=0, y=0)

        measured_distance += abs(distance_euclidian(self.oldx, self.oldy, 0, 0))
        log.debug("The total travel distance including travel to end position is: %s" %
                  str(measured_distance) + '\n')
        self.travel_distance = measured_distance

        # I use the value of self.feedrate_rapid for the feadrate in case of the measure_lift_distance and for
        # traveled_time because it is not always possible to determine the feedrate that the CNC machine uses
        # for G0 move (the fastest speed available to the CNC router). Although self.feedrate_rapids is used only with
        # Marlin postprocessor and derivatives.
        self.routing_time = (measured_down_distance + measured_up_to_zero_distance) / self.feedrate
        lift_time = measured_lift_distance / self.feedrate_rapid
        traveled_time = measured_distance / self.feedrate_rapid
        self.routing_time += lift_time + traveled_time

        self.gcode = gcode
        return 'OK'

    def generate_from_multitool_geometry(self, geometry, append=True,
                                         tooldia=None, offset=0.0, tolerance=0, z_cut=1.0, z_move=2.0,
                                         feedrate=2.0, feedrate_z=2.0, feedrate_rapid=30,
                                         spindlespeed=None, spindledir='CW', dwell=False, dwelltime=1.0,
                                         multidepth=False, depthpercut=None,
                                         toolchange=False, toolchangez=1.0, toolchangexy="0.0, 0.0", extracut=False,
                                         startz=None, endz=2.0, pp_geometry_name=None, tool_no=1):
        """
        Algorithm to generate from multitool Geometry.

        Algorithm description:
        ----------------------
        Uses RTree to find the nearest path to follow.

        :param geometry:
        :param append:
        :param tooldia:
        :param tolerance:
        :param multidepth: If True, use multiple passes to reach
           the desired depth.
        :param depthpercut: Maximum depth in each pass.
        :param extracut: Adds (or not) an extra cut at the end of each path
            overlapping the first point in path to ensure complete copper removal
        :return: GCode - string
        """

        log.debug("Generate_from_multitool_geometry()")

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

        self.tooldia = float(tooldia) if tooldia else None
        self.z_cut = float(z_cut) if z_cut else None
        self.z_move = float(z_move) if z_move else None

        self.feedrate = float(feedrate) if feedrate else None
        self.z_feedrate = float(feedrate_z) if feedrate_z else None
        self.feedrate_rapid = float(feedrate_rapid) if feedrate_rapid else None

        self.spindlespeed = int(spindlespeed) if spindlespeed else None
        self.spindledir = spindledir
        self.dwell = dwell
        self.dwelltime = float(dwelltime) if dwelltime else None

        self.startz = float(startz) if startz else None
        self.z_end = float(endz) if endz else None

        self.z_depthpercut = float(depthpercut) if depthpercut else None
        self.multidepth = multidepth

        self.z_toolchange = float(toolchangez) if toolchangez else None

        # it servers in the postprocessor file
        self.tool = tool_no

        try:
            if toolchangexy == '':
                self.xy_toolchange = None
            else:
                self.xy_toolchange = [float(eval(a)) for a in toolchangexy.split(",")]
                if len(self.xy_toolchange) < 2:
                    self.app.inform.emit(_("[ERROR]The Toolchange X,Y field in Edit -> Preferences has to be "
                                         "in the format (x, y) \nbut now there is only one value, not two. "))
                    return 'fail'
        except Exception as e:
            log.debug("camlib.CNCJob.generate_from_multitool_geometry() --> %s" % str(e))
            pass

        self.pp_geometry_name = pp_geometry_name if pp_geometry_name else 'default'
        self.f_plunge = self.app.defaults["geometry_f_plunge"]

        if self.z_cut is None:
            self.app.inform.emit(_("[ERROR_NOTCL] Cut_Z parameter is None or zero. Most likely a bad combinations of "
                                 "other parameters."))
            return 'fail'

        if self.z_cut > 0:
            self.app.inform.emit(_("[WARNING] The Cut Z parameter has positive value. "
                                 "It is the depth value to cut into material.\n"
                                 "The Cut Z parameter needs to have a negative value, assuming it is a typo "
                                 "therefore the app will convert the value to negative."
                                 "Check the resulting CNC code (Gcode etc)."))
            self.z_cut = -self.z_cut
        elif self.z_cut == 0:
            self.app.inform.emit(_("[WARNING] The Cut Z parameter is zero. "
                                 "There will be no cut, skipping %s file") % self.options['name'])
            return 'fail'

        # made sure that depth_per_cut is no more then the z_cut
        if abs(self.z_cut) < self.z_depthpercut:
            self.z_depthpercut = abs(self.z_cut)

        if self.z_move is None:
            self.app.inform.emit(_("[ERROR_NOTCL] Travel Z parameter is None or zero."))
            return 'fail'

        if self.z_move < 0:
            self.app.inform.emit(_("[WARNING] The Travel Z parameter has negative value. "
                                 "It is the height value to travel between cuts.\n"
                                 "The Z Travel parameter needs to have a positive value, assuming it is a typo "
                                 "therefore the app will convert the value to positive."
                                 "Check the resulting CNC code (Gcode etc)."))
            self.z_move = -self.z_move
        elif self.z_move == 0:
            self.app.inform.emit(_("[WARNING] The Z Travel parameter is zero. "
                                 "This is dangerous, skipping %s file") % self.options['name'])
            return 'fail'

        # ## Index first and last points in paths
        # What points to index.
        def get_pts(o):
            return [o.coords[0], o.coords[-1]]

        # Create the indexed storage.
        storage = FlatCAMRTreeStorage()
        storage.get_points = get_pts

        # Store the geometry
        log.debug("Indexing geometry before generating G-Code...")
        for shape in flat_geometry:
            if shape is not None:  # TODO: This shouldn't have happened.
                storage.insert(shape)

        # self.input_geometry_bounds = geometry.bounds()

        if not append:
            self.gcode = ""

        # tell postprocessor the number of tool (for toolchange)
        self.tool = tool_no

        # this is the tool diameter, it is used as such to accommodate the postprocessor who need the tool diameter
        # given under the name 'toolC'
        self.postdata['toolC'] = self.tooldia

        # Initial G-Code
        self.pp_geometry = self.app.postprocessors[self.pp_geometry_name]
        p = self.pp_geometry

        self.gcode = self.doformat(p.start_code)

        self.gcode += self.doformat(p.feedrate_code)        # sets the feed rate

        if toolchange is False:
            self.gcode += self.doformat(p.lift_code, x=0, y=0)  # Move (up) to travel height
            self.gcode += self.doformat(p.startz_code, x=0, y=0)

        if toolchange:
            # if "line_xyz" in self.pp_geometry_name:
            #     self.gcode += self.doformat(p.toolchange_code, x=self.xy_toolchange[0], y=self.xy_toolchange[1])
            # else:
            #     self.gcode += self.doformat(p.toolchange_code)
            self.gcode += self.doformat(p.toolchange_code)

            self.gcode += self.doformat(p.spindle_code)     # Spindle start
            if self.dwell is True:
                self.gcode += self.doformat(p.dwell_code)   # Dwell time
        else:
            self.gcode += self.doformat(p.spindle_code)     # Spindle start
            if self.dwell is True:
                self.gcode += self.doformat(p.dwell_code)   # Dwell time

        total_travel = 0.0
        total_cut = 0.0

        # ## Iterate over geometry paths getting the nearest each time.
        log.debug("Starting G-Code...")
        path_count = 0
        current_pt = (0, 0)

        pt, geo = storage.nearest(current_pt)

        try:
            while True:
                path_count += 1

                # Remove before modifying, otherwise deletion will fail.
                storage.remove(geo)

                # If last point in geometry is the nearest but prefer the first one if last point == first point
                # then reverse coordinates.
                if pt != geo.coords[0] and pt == geo.coords[-1]:
                    geo.coords = list(geo.coords)[::-1]

                # ---------- Single depth/pass --------
                if not multidepth:
                    # calculate the cut distance
                    total_cut = total_cut + geo.length

                    self.gcode += self.create_gcode_single_pass(geo, extracut, tolerance, old_point=current_pt)

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

                    self.gcode += self.create_gcode_multi_pass(geo, extracut, tolerance,
                                                               postproc=p, old_point=current_pt)

                # calculate the total distance
                total_travel = total_travel + abs(distance(pt1=current_pt, pt2=pt))
                current_pt = geo.coords[-1]

                pt, geo = storage.nearest(current_pt) # Next
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
        self.app.inform.emit(_("Finished G-Code generation... %s paths traced.") % str(path_count))
        return self.gcode

    def generate_from_geometry_2(self, geometry, append=True,
                                 tooldia=None, offset=0.0, tolerance=0,
                                 z_cut=1.0, z_move=2.0,
                                 feedrate=2.0, feedrate_z=2.0, feedrate_rapid=30,
                                 spindlespeed=None, spindledir='CW', dwell=False, dwelltime=1.0,
                                 multidepth=False, depthpercut=None,
                                 toolchange=False, toolchangez=1.0, toolchangexy="0.0, 0.0",
                                 extracut=False, startz=None, endz=2.0,
                                 pp_geometry_name=None, tool_no=1):
        """
        Second algorithm to generate from Geometry.

        Algorithm description:
        ----------------------
        Uses RTree to find the nearest path to follow.

        :param geometry:
        :param append:
        :param tooldia:
        :param tolerance:
        :param multidepth: If True, use multiple passes to reach
           the desired depth.
        :param depthpercut: Maximum depth in each pass.
        :param extracut: Adds (or not) an extra cut at the end of each path
            overlapping the first point in path to ensure complete copper removal
        :return: None
        """

        if not isinstance(geometry, Geometry):
            self.app.inform.emit(_("[ERROR]Expected a Geometry, got %s") % type(geometry))
            return 'fail'
        log.debug("Generate_from_geometry_2()")

        # if solid_geometry is empty raise an exception
        if not geometry.solid_geometry:
            self.app.inform.emit(_("[ERROR_NOTCL] Trying to generate a CNC Job "
                                 "from a Geometry object without solid_geometry."))

        temp_solid_geometry = []

        def bounds_rec(obj):
            if type(obj) is list:
                minx = Inf
                miny = Inf
                maxx = -Inf
                maxy = -Inf

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

        if offset != 0.0:
            offset_for_use = offset

            if offset < 0:
                a, b, c, d = bounds_rec(geometry.solid_geometry)
                # if the offset is less than half of the total length or less than half of the total width of the
                # solid geometry it's obvious we can't do the offset
                if -offset > ((c - a) / 2) or -offset > ((d - b) / 2):
                    self.app.inform.emit(_("[ERROR_NOTCL] The Tool Offset value is too negative to use "
                                           "for the current_geometry.\n"
                                           "Raise the value (in module) and try again."))
                    return 'fail'
                # hack: make offset smaller by 0.0000000001 which is insignificant difference but allow the job
                # to continue
                elif  -offset == ((c - a) / 2) or -offset == ((d - b) / 2):
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

        try:
            self.tooldia = float(tooldia) if tooldia else None
        except ValueError:
            self.tooldia = [float(el) for el in tooldia.split(',') if el != ''] if tooldia else None

        self.z_cut = float(z_cut) if z_cut else None
        self.z_move = float(z_move) if z_move else None

        self.feedrate = float(feedrate) if feedrate else None
        self.z_feedrate = float(feedrate_z) if feedrate_z else None
        self.feedrate_rapid = float(feedrate_rapid) if feedrate_rapid else None

        self.spindlespeed = int(spindlespeed) if spindlespeed else None
        self.spindledir = spindledir
        self.dwell = dwell
        self.dwelltime = float(dwelltime) if dwelltime else None

        self.startz = float(startz) if startz else None
        self.z_end = float(endz) if endz else None
        self.z_depthpercut = float(depthpercut) if depthpercut else None
        self.multidepth = multidepth
        self.z_toolchange = float(toolchangez) if toolchangez else None

        try:
            if toolchangexy == '':
                self.xy_toolchange = None
            else:
                self.xy_toolchange = [float(eval(a)) for a in toolchangexy.split(",")]
                if len(self.xy_toolchange) < 2:
                    self.app.inform.emit(_("[ERROR]The Toolchange X,Y field in Edit -> Preferences has to be "
                                           "in the format (x, y) \nbut now there is only one value, not two. "))
                    return 'fail'
        except Exception as e:
            log.debug("camlib.CNCJob.generate_from_geometry_2() --> %s" % str(e))
            pass

        self.pp_geometry_name = pp_geometry_name if pp_geometry_name else 'default'
        self.f_plunge = self.app.defaults["geometry_f_plunge"]

        if self.z_cut is None:
            self.app.inform.emit(_("[ERROR_NOTCL] Cut_Z parameter is None or zero. Most likely a bad combinations of "
                                   "other parameters."))
            return 'fail'

        if self.z_cut > 0:
            self.app.inform.emit(_("[WARNING] The Cut Z parameter has positive value. "
                                   "It is the depth value to cut into material.\n"
                                   "The Cut Z parameter needs to have a negative value, assuming it is a typo "
                                   "therefore the app will convert the value to negative."
                                   "Check the resulting CNC code (Gcode etc)."))
            self.z_cut = -self.z_cut
        elif self.z_cut == 0:
            self.app.inform.emit(_("[WARNING] The Cut Z parameter is zero. "
                                   "There will be no cut, skipping %s file") % geometry.options['name'])
            return 'fail'

        if self.z_move is None:
            self.app.inform.emit(_("[ERROR_NOTCL] Travel Z parameter is None or zero."))
            return 'fail'

        if self.z_move < 0:
            self.app.inform.emit(_("[WARNING] The Travel Z parameter has negative value. "
                                   "It is the height value to travel between cuts.\n"
                                   "The Z Travel parameter needs to have a positive value, assuming it is a typo "
                                   "therefore the app will convert the value to positive."
                                   "Check the resulting CNC code (Gcode etc)."))
            self.z_move = -self.z_move
        elif self.z_move == 0:
            self.app.inform.emit(_("[WARNING] The Z Travel parameter is zero. "
                                   "This is dangerous, skipping %s file") % self.options['name'])
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
        for shape in flat_geometry:
            if shape is not None:  # TODO: This shouldn't have happened.
                storage.insert(shape)

        if not append:
            self.gcode = ""

        # tell postprocessor the number of tool (for toolchange)
        self.tool = tool_no

        # this is the tool diameter, it is used as such to accommodate the postprocessor who need the tool diameter
        # given under the name 'toolC'
        self.postdata['toolC'] = self.tooldia

        # Initial G-Code
        self.pp_geometry = self.app.postprocessors[self.pp_geometry_name]
        p = self.pp_geometry

        self.oldx = 0.0
        self.oldy = 0.0

        self.gcode = self.doformat(p.start_code)

        self.gcode += self.doformat(p.feedrate_code)        # sets the feed rate

        if toolchange is False:
            self.gcode += self.doformat(p.lift_code, x=self.oldx , y=self.oldy )  # Move (up) to travel height
            self.gcode += self.doformat(p.startz_code, x=self.oldx , y=self.oldy )

        if toolchange:
            # if "line_xyz" in self.pp_geometry_name:
            #     self.gcode += self.doformat(p.toolchange_code, x=self.xy_toolchange[0], y=self.xy_toolchange[1])
            # else:
            #     self.gcode += self.doformat(p.toolchange_code)
            self.gcode += self.doformat(p.toolchange_code)

            self.gcode += self.doformat(p.spindle_code)     # Spindle start

            if self.dwell is True:
                self.gcode += self.doformat(p.dwell_code)   # Dwell time

        else:
            self.gcode += self.doformat(p.spindle_code)     # Spindle start
            if self.dwell is True:
                self.gcode += self.doformat(p.dwell_code)   # Dwell time

        total_travel = 0.0
        total_cut = 0.0

        # Iterate over geometry paths getting the nearest each time.
        log.debug("Starting G-Code...")
        path_count = 0
        current_pt = (0, 0)
        pt, geo = storage.nearest(current_pt)
        try:
            while True:
                path_count += 1

                # Remove before modifying, otherwise deletion will fail.
                storage.remove(geo)

                # If last point in geometry is the nearest but prefer the first one if last point == first point
                # then reverse coordinates.
                if pt != geo.coords[0] and pt == geo.coords[-1]:
                    geo.coords = list(geo.coords)[::-1]

                # ---------- Single depth/pass --------
                if not multidepth:
                    # calculate the cut distance
                    total_cut += geo.length
                    self.gcode += self.create_gcode_single_pass(geo, extracut, tolerance, old_point=current_pt)

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

                    self.gcode += self.create_gcode_multi_pass(geo, extracut, tolerance,
                                                               postproc=p, old_point=current_pt)

                # calculate the travel distance
                total_travel += abs(distance(pt1=current_pt, pt2=pt))
                current_pt = geo.coords[-1]

                pt, geo = storage.nearest(current_pt) # Next
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
        self.app.inform.emit(_("Finished G-Code generation... %s paths traced.") % str(path_count))

        return self.gcode

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
            self.app.inform.emit(_("[ERROR_NOTCL] There is no tool data in the SolderPaste geometry."))


        # this is the tool diameter, it is used as such to accommodate the postprocessor who need the tool diameter
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
        p = self.app.postprocessors[self.pp_solderpaste_name]

        # ## Flatten the geometry. Only linear elements (no polygons) remain.
        flat_geometry = self.flatten(kwargs['solid_geometry'], pathonly=True)
        log.debug("%d paths" % len(flat_geometry))

        # Create the indexed storage.
        storage = FlatCAMRTreeStorage()
        storage.get_points = get_pts

        # Store the geometry
        log.debug("Indexing geometry before generating G-Code...")
        for shape in flat_geometry:
            if shape is not None:
                storage.insert(shape)

        # Initial G-Code
        self.gcode = self.doformat(p.start_code)
        self.gcode += self.doformat(p.spindle_off_code)
        self.gcode += self.doformat(p.toolchange_code)

        # ## Iterate over geometry paths getting the nearest each time.
        log.debug("Starting SolderPaste G-Code...")
        path_count = 0
        current_pt = (0, 0)

        pt, geo = storage.nearest(current_pt)

        try:
            while True:
                path_count += 1

                # Remove before modifying, otherwise deletion will fail.
                storage.remove(geo)

                # If last point in geometry is the nearest but prefer the first one if last point == first point
                # then reverse coordinates.
                if pt != geo.coords[0] and pt == geo.coords[-1]:
                    geo.coords = list(geo.coords)[::-1]

                self.gcode += self.create_soldepaste_gcode(geo, p=p, old_point=current_pt)
                current_pt = geo.coords[-1]
                pt, geo = storage.nearest(current_pt)  # Next

        except StopIteration:  # Nothing found in storage.
            pass

        log.debug("Finishing SolderPste G-Code... %s paths traced." % path_count)

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
            gcode += self.doformat(p.spindle_fwd_code) # Start dispensing
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
            gcode += self.doformat(p.spindle_off_code) # Stop dispensing
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
            gcode += self.doformat(p.spindle_fwd_code) # Start dispensing
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

    def create_gcode_single_pass(self, geometry, extracut, tolerance, old_point=(0, 0)):
        # G-code. Note: self.linear2gcode() and self.point2gcode() will lower and raise the tool every time.
        gcode_single_pass = ''

        if type(geometry) == LineString or type(geometry) == LinearRing:
            if extracut is False:
                gcode_single_pass = self.linear2gcode(geometry, tolerance=tolerance, old_point=old_point)
            else:
                if geometry.is_ring:
                    gcode_single_pass = self.linear2gcode_extra(geometry, tolerance=tolerance, old_point=old_point)
                else:
                    gcode_single_pass = self.linear2gcode(geometry, tolerance=tolerance, old_point=old_point)
        elif type(geometry) == Point:
            gcode_single_pass = self.point2gcode(geometry)
        else:
            log.warning("G-code generation not implemented for %s" % (str(type(geometry))))
            return

        return gcode_single_pass

    def create_gcode_multi_pass(self, geometry, extracut, tolerance, postproc, old_point=(0, 0)):

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
                if extracut is False:
                    gcode_multi_pass += self.linear2gcode(geometry, tolerance=tolerance, z_cut=depth, up=False,
                                                          old_point=old_point)
                else:
                    if geometry.is_ring:
                        gcode_multi_pass += self.linear2gcode_extra(geometry, tolerance=tolerance, z_cut=depth,
                                                                    up=False, old_point=old_point)
                    else:
                        gcode_multi_pass += self.linear2gcode(geometry, tolerance=tolerance, z_cut=depth, up=False,
                                                              old_point=old_point)

            # Ignore multi-pass for points.
            elif type(geometry) == Point:
                gcode_multi_pass += self.point2gcode(geometry, old_point=old_point)
                break  # Ignoring ...
            else:
                log.warning("G-code generation not implemented for %s" % (str(type(geometry))))

            # Reverse coordinates if not a loop so we can continue cutting without returning to the beginning.
            if type(geometry) == LineString:
                geometry.coords = list(geometry.coords)[::-1]
                reverse = True

        # If geometry is reversed, revert.
        if reverse:
            if type(geometry) == LineString:
                geometry.coords = list(geometry.coords)[::-1]

        # Lift the tool
        gcode_multi_pass += self.doformat(postproc.lift_code, x=old_point[0], y=old_point[1])
        return gcode_multi_pass

    def codes_split(self, gline):
        """
        Parses a line of G-Code such as "G01 X1234 Y987" into
        a dictionary: {'G': 1.0, 'X': 1234.0, 'Y': 987.0}

        :param gline: G-Code line string
        :return: Dictionary with parsed line.
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
                command['X'] = float(match_pa.group(1).replace(" ", ""))
                command['Y'] = float(match_pa.group(2).replace(" ", ""))
            match_pen = re.search(r"^(P[U|D])", gline)
            if match_pen:
                if match_pen.group(1) == 'PU':
                    # the value does not matter, only that it is positive so the gcode_parse() know it is > 0,
                    # therefore the move is of kind T (travel)
                    command['Z'] = 1
                else:
                    command['Z'] = 0

        elif 'grbl_laser' in self.pp_excellon_name or 'grbl_laser' in self.pp_geometry_name or \
                (self.pp_solderpaste_name is not None and 'Paste' in self.pp_solderpaste_name):
            match_lsr = re.search(r"X([\+-]?\d+.[\+-]?\d+)\s*Y([\+-]?\d+.[\+-]?\d+)", gline)
            if match_lsr:
                command['X'] = float(match_lsr.group(1).replace(" ", ""))
                command['Y'] = float(match_lsr.group(2).replace(" ", ""))

            match_lsr_pos = re.search(r"^(M0[3|5])", gline)
            if match_lsr_pos:
                if match_lsr_pos.group(1) == 'M05':
                    # the value does not matter, only that it is positive so the gcode_parse() know it is > 0,
                    # therefore the move is of kind T (travel)
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

    def gcode_parse(self):
        """
        G-Code parser (from self.gcode). Generates dictionary with
        single-segment LineString's and "kind" indicating cut or travel,
        fast or feedrate speed.
        """

        kind = ["C", "F"]  # T=travel, C=cut, F=fast, S=slow

        # Results go here
        geometry = []        

        # Last known instruction
        current = {'X': 0.0, 'Y': 0.0, 'Z': 0.0, 'G': 0}

        # Current path: temporary storage until tool is
        # lifted or lowered.
        if self.toolchange_xy_type == "excellon":
            if self.app.defaults["excellon_toolchangexy"] == '':
                pos_xy = [0, 0]
            else:
                pos_xy = [float(eval(a)) for a in self.app.defaults["excellon_toolchangexy"].split(",")]
        else:
            if self.app.defaults["geometry_toolchangexy"] == '':
                pos_xy = [0, 0]
            else:
                pos_xy = [float(eval(a)) for a in self.app.defaults["geometry_toolchangexy"].split(",")]

        path = [pos_xy]
        # path = [(0, 0)]

        # Process every instruction
        for line in StringIO(self.gcode):
            if '%MO' in line or '%' in line or 'MOIN' in line or 'MOMM' in line:
                return "fail"

            gobj = self.codes_split(line)

            # ## Units
            if 'G' in gobj and (gobj['G'] == 20.0 or gobj['G'] == 21.0):
                self.units = {20.0: "IN", 21.0: "MM"}[gobj['G']]
                continue

            # ## Changing height
            if 'Z' in gobj:
                if 'Roland' in self.pp_excellon_name or 'Roland' in self.pp_geometry_name:
                    pass
                elif 'hpgl' in self.pp_excellon_name or 'hpgl' in self.pp_geometry_name:
                    pass
                elif 'grbl_laser' in self.pp_excellon_name or 'grbl_laser' in self.pp_geometry_name:
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
                        current_drill_point_coords = (float('%.4f' % current['X']), float('%.4f' % current['Y']))
                        # find the drill diameter knowing the drill coordinates
                        for pt_dict in self.exc_drills:
                            point_in_dict_coords = (float('%.4f' % pt_dict['point'].x),
                                                   float('%.4f' % pt_dict['point'].y))
                            if point_in_dict_coords == current_drill_point_coords:
                                tool = pt_dict['tool']
                                dia = self.exc_tools[tool]['C']
                                kind = ['C', 'F']
                                geometry.append({"geom": Point(current_drill_point_coords).
                                                buffer(dia/2).exterior,
                                                 "kind": kind})
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
                    radius = sqrt(gobj['I']**2 + gobj['J']**2)
                    start = arctan2(-gobj['J'], -gobj['I'])
                    stop = arctan2(-center[1] + y, -center[0] + x)
                    path += arc(center, radius, start, stop, arcdir[current['G']], int(self.steps_per_circle / 4))

            # Update current instruction
            for code in gobj:
                current[code] = gobj[code]

        # There might not be a change in height at the
        # end, therefore, see here too if there is
        # a final path.
        if len(path) > 1:
            geometry.append({"geom": LineString(path),
                             "kind": kind})

        self.gcode_parsed = geometry
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
              color={"T": ["#F0E24D4C", "#B5AB3A4C"], "C": ["#5E6CFFFF", "#4650BDFF"]},
              alpha={"T": 0.3, "C": 1.0}, tool_tolerance=0.0005, obj=None, visible=False, kind='all'):
        """
        Plots the G-code job onto the given axes.

        :param tooldia: Tool diameter.
        :param dpi: Not used!
        :param margin: Not used!
        :param color: Color specification.
        :param alpha: Transparency specification.
        :param tool_tolerance: Tolerance when drawing the toolshape.
        :param obj
        :param visible
        :param kind
        :return: None
        """
        # units = self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().upper()

        gcode_parsed = gcode_parsed if gcode_parsed else self.gcode_parsed
        path_num = 0

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
            text = []
            pos = []
            self.coordinates_type = self.app.defaults["cncjob_coords_type"]
            if self.coordinates_type == "G90":
                # For Absolute coordinates type G90
                for geo in gcode_parsed:
                    if geo['kind'][0] == 'T':
                        current_position = geo['geom'].coords[0]
                        if current_position not in pos:
                            pos.append(current_position)
                            path_num += 1
                            text.append(str(path_num))

                        current_position = geo['geom'].coords[-1]
                        if current_position not in pos:
                            pos.append(current_position)
                            path_num += 1
                            text.append(str(path_num))

                    # plot the geometry of Excellon objects
                    if self.origin_kind == 'excellon':
                        try:
                            poly = Polygon(geo['geom'])
                        except ValueError:
                            # if the geos are travel lines it will enter into Exception
                            poly = geo['geom'].buffer(distance=(tooldia / 1.99999999), resolution=self.steps_per_circle)
                            poly = poly.simplify(tool_tolerance)
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
                # For Incremental coordinates type G91
                current_x = gcode_parsed[0]['geom'].coords[0][0]
                current_y = gcode_parsed[0]['geom'].coords[0][1]
                old_pos = (
                    current_x,
                    current_y
                )

                for geo in gcode_parsed:
                    if geo['kind'][0] == 'T':
                        current_position = (
                            geo['geom'].coords[0][0] + old_pos[0],
                            geo['geom'].coords[0][1] + old_pos[1]
                        )
                        if current_position not in pos:
                            pos.append(current_position)
                            path_num += 1
                            text.append(str(path_num))

                        delta = (
                            geo['geom'].coords[-1][0] - geo['geom'].coords[0][0],
                            geo['geom'].coords[-1][1] - geo['geom'].coords[0][1]
                        )
                        current_position = (
                            current_position[0] + geo['geom'].coords[-1][0],
                            current_position[1] + geo['geom'].coords[-1][1]
                        )
                        if current_position not in pos:
                            pos.append(current_position)
                            path_num += 1
                            text.append(str(path_num))

                    # plot the geometry of Excellon objects
                    if self.origin_kind == 'excellon':
                        if isinstance(geo['geom'], Point):
                            # if geo is Point
                            current_position = (
                                current_position[0] + geo['geom'].x,
                                current_position[1] + geo['geom'].y
                            )
                            poly = Polygon(Point(current_position))
                        elif isinstance(geo['geom'], LineString):
                            # if the geos are travel lines (LineStrings)
                            new_line_pts = []
                            old_line_pos = deepcopy(current_position)
                            for p in list(geo['geom'].coords):
                                current_position = (
                                    current_position[0] + p[0],
                                    current_position[1] + p[1]
                                )
                                new_line_pts.append(current_position)
                                old_line_pos = p
                            new_line = LineString(new_line_pts)

                            poly = new_line.buffer(distance=(tooldia / 1.99999999), resolution=self.steps_per_circle)
                            poly = poly.simplify(tool_tolerance)
                    else:
                        # plot the geometry of any objects other than Excellon
                        new_line_pts = []
                        old_line_pos = deepcopy(current_position)
                        for p in list(geo['geom'].coords):
                            current_position = (
                                current_position[0] + p[0],
                                current_position[1] + p[1]
                            )
                            new_line_pts.append(current_position)
                            old_line_pos = p
                        new_line = LineString(new_line_pts)

                        poly = new_line.buffer(distance=(tooldia / 1.99999999), resolution=self.steps_per_circle)
                        poly = poly.simplify(tool_tolerance)

                    old_pos = deepcopy(current_position)

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
            try:
                obj.annotation.set(text=text, pos=pos, visible=obj.options['plot'],
                                   font_size=self.app.defaults["cncjob_annotation_fontsize"],
                                   color=self.app.defaults["cncjob_annotation_fontcolor"])
            except Exception as e:
                pass

    def create_geometry(self):
        # TODO: This takes forever. Too much data?
        self.solid_geometry = cascaded_union([geo['geom'] for geo in self.gcode_parsed])
        return self.solid_geometry

    # code snippet added by Lei Zheng in a rejected pull request on FlatCAM https://bitbucket.org/realthunder/
    def segment(self, coords):
        """
        break long linear lines to make it more auto level friendly
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

    def linear2gcode(self, linear, tolerance=0, down=True, up=True,
                     z_cut=None, z_move=None, zdownrate=None,
                     feedrate=None, feedrate_z=None, feedrate_rapid=None, cont=False, old_point=(0, 0)):
        """
        Generates G-code to cut along the linear feature.

        :param linear: The path to cut along.
        :type: Shapely.LinearRing or Shapely.Linear String
        :param tolerance: All points in the simplified object will be within the
            tolerance distance of the original geometry.
        :type tolerance: float
        :param feedrate: speed for cut on X - Y plane
        :param feedrate_z: speed for cut on Z plane
        :param feedrate_rapid: speed to move between cuts; usually is G0 but some CNC require to specify it
        :return: G-code to cut along the linear feature.
        :rtype: str
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
            gcode += self.doformat(p.rapid_code, x=first_x, y=first_y)  # Move to first point

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
            if self.coordinates_type == "G90":
                # For Absolute coordinates type G90
                next_x = pt[0]
                next_y = pt[1]
            else:
                # For Incremental coordinates type G91
                next_x = pt[0] - prev_x
                next_y = pt[1] - prev_y
            gcode += self.doformat(p.linear_code, x=next_x, y=next_y, z=z_cut)  # Linear motion to point
            prev_x = pt[0]
            prev_y = pt[1]
        # Up to travelling height.
        if up:
            gcode += self.doformat(p.lift_code, x=prev_x, y=prev_y, z_move=z_move)  # Stop cutting
        return gcode

    def linear2gcode_extra(self, linear, tolerance=0, down=True, up=True,
                     z_cut=None, z_move=None, zdownrate=None,
                     feedrate=None, feedrate_z=None, feedrate_rapid=None, cont=False, old_point=(0, 0)):
        """
        Generates G-code to cut along the linear feature.

        :param linear: The path to cut along.
        :type: Shapely.LinearRing or Shapely.Linear String
        :param tolerance: All points in the simplified object will be within the
            tolerance distance of the original geometry.
        :type tolerance: float
        :param feedrate: speed for cut on X - Y plane
        :param feedrate_z: speed for cut on Z plane
        :param feedrate_rapid: speed to move between cuts; usually is G0 but some CNC require to specify it
        :return: G-code to cut along the linear feature.
        :rtype: str
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
            gcode += self.doformat(p.rapid_code, x=first_x, y=first_y)  # Move to first point

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
            if self.coordinates_type == "G90":
                # For Absolute coordinates type G90
                next_x = pt[0]
                next_y = pt[1]
            else:
                # For Incremental coordinates type G91
                next_x = pt[0] - prev_x
                next_y = pt[1] - prev_y
            gcode += self.doformat(p.linear_code, x=next_x, y=next_y, z=z_cut)  # Linear motion to point
            prev_x = pt[0]
            prev_y = pt[1]

        # this line is added to create an extra cut over the first point in patch
        # to make sure that we remove the copper leftovers
        # Linear motion to the 1st point in the cut path
        if self.coordinates_type == "G90":
            # For Absolute coordinates type G90
            last_x = path[1][0]
            last_y = path[1][1]
        else:
            # For Incremental coordinates type G91
            last_x = path[1][0] - first_x
            last_y = path[1][1] - first_y
        gcode += self.doformat(p.linear_code, x=last_x, y=last_y)

        # Up to travelling height.
        if up:
            gcode += self.doformat(p.lift_code, x=last_x, y=last_y, z_move=z_move)  # Stop cutting

        return gcode

    def point2gcode(self, point, old_point=(0, 0)):
        gcode = ""

        path = list(point.coords)
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

        gcode += self.doformat(p.linear_code, x=first_x, y=first_y)  # Move to first point

        if self.z_feedrate is not None:
            gcode += self.doformat(p.z_feedrate_code)
            gcode += self.doformat(p.down_code, x=first_x, y=first_y, z_cut = self.z_cut)
            gcode += self.doformat(p.feedrate_code)
        else:
            gcode += self.doformat(p.down_code, x=first_x, y=first_y, z_cut = self.z_cut)  # Start cutting

        gcode += self.doformat(p.lift_code, x=first_x, y=first_y)  # Stop cutting
        return gcode

    def export_svg(self, scale_factor=0.00):
        """
        Exports the CNC Job as a SVG Element

        :scale_factor: float
        :return: SVG Element string
        """
        # scale_factor is a multiplication factor for the SVG stroke-width used within shapely's svg export
        # If not specified then try and use the tool diameter
        # This way what is on screen will match what is outputed for the svg
        # This is quite a useful feature for svg's used with visicut

        if scale_factor <= 0:
            scale_factor = self.options['tooldia'] / 2

        # If still 0 then default to 0.05
        # This value appears to work for zooming, and getting the output svg line width
        # to match that viewed on screen with FlatCam
        if scale_factor == 0:
            scale_factor = 0.01

        # Separate the list of cuts and travels into 2 distinct lists
        # This way we can add different formatting / colors to both
        cuts = []
        travels = []
        for g in self.gcode_parsed:
            if g['kind'][0] == 'C': cuts.append(g)
            if g['kind'][0] == 'T': travels.append(g)

        # Used to determine the overall board size
        self.solid_geometry = cascaded_union([geo['geom'] for geo in self.gcode_parsed])

        # Convert the cuts and travels into single geometry objects we can render as svg xml
        if travels:
            travelsgeom = cascaded_union([geo['geom'] for geo in travels])
        if cuts:
            cutsgeom = cascaded_union([geo['geom'] for geo in cuts])

        # Render the SVG Xml
        # The scale factor affects the size of the lines, and the stroke color adds different formatting for each set
        # It's better to have the travels sitting underneath the cuts for visicut
        svg_elem = ""
        if travels:
            svg_elem = travelsgeom.svg(scale_factor=scale_factor, stroke_color="#F0E24D")
        if cuts:
            svg_elem += cutsgeom.svg(scale_factor=scale_factor, stroke_color="#5E6CFF")

        return svg_elem

    def bounds(self):
        """
        Returns coordinates of rectangular bounds
        of geometry: (xmin, ymin, xmax, ymax).
        """
        # fixed issue of getting bounds only for one level lists of objects
        # now it can get bounds for nested lists of objects

        log.debug("camlib.CNCJob.bounds()")

        def bounds_rec(obj):
            if type(obj) is list:
                minx = Inf
                miny = Inf
                maxx = -Inf
                maxy = -Inf

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

        if self.multitool is False:
            log.debug("CNCJob->bounds()")
            if self.solid_geometry is None:
                log.debug("solid_geometry is None")
                return 0, 0, 0, 0

            bounds_coords = bounds_rec(self.solid_geometry)
        else:
            minx = Inf
            miny = Inf
            maxx = -Inf
            maxy = -Inf
            for k, v in self.cnc_tools.items():
                minx = Inf
                miny = Inf
                maxx = -Inf
                maxy = -Inf
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

        :param factor: Number by which to scale the object.
        :type factor: float
        :param point: the (x,y) coords for the point of origin of scale
        :type tuple of floats
        :return: None
        :rtype: None
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
            units = self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().upper()

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
            # offset geometry
            for g in self.gcode_parsed:
                try:
                    g['geom'] = affinity.scale(g['geom'], xfactor, yfactor, origin=(px, py))
                except AttributeError:
                    return g['geom']
            self.create_geometry()
        else:
            for k, v in self.cnc_tools.items():
                # scale Gcode
                v['gcode'] = scale_g(v['gcode'])
                # scale gcode_parsed
                for g in v['gcode_parsed']:
                    try:
                        g['geom'] = affinity.scale(g['geom'], xfactor, yfactor, origin=(px, py))
                    except AttributeError:
                        return g['geom']
                v['solid_geometry'] = cascaded_union([geo['geom'] for geo in v['gcode_parsed']])
        self.create_geometry()

    def offset(self, vect):
        """
        Offsets all the geometry on the XY plane in the object by the
        given vector.
        Offsets all the GCODE on the XY plane in the object by the
        given vector.

        g_offsetx_re, g_offsety_re, multitool, cnnc_tools are attributes of FlatCAMCNCJob class in camlib

        :param vect: (x, y) offset vector.
        :type vect: tuple
        :return: None
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
            # offset geometry
            for g in self.gcode_parsed:
                try:
                    g['geom'] = affinity.translate(g['geom'], xoff=dx, yoff=dy)
                except AttributeError:
                    return g['geom']
            self.create_geometry()
        else:
            for k, v in self.cnc_tools.items():
                # offset Gcode
                v['gcode'] = offset_g(v['gcode'])
                # offset gcode_parsed
                for g in v['gcode_parsed']:
                    try:
                        g['geom'] = affinity.translate(g['geom'], xoff=dx, yoff=dy)
                    except AttributeError:
                        return g['geom']
                v['solid_geometry'] = cascaded_union([geo['geom'] for geo in v['gcode_parsed']])

    def mirror(self, axis, point):
        """
        Mirror the geometrys of an object by an given axis around the coordinates of the 'point'
        :param angle:
        :param point: tupple of coordinates (x,y)
        :return:
        """
        log.debug("camlib.CNCJob.mirror()")

        px, py = point
        xscale, yscale = {"X": (1.0, -1.0), "Y": (-1.0, 1.0)}[axis]

        for g in self.gcode_parsed:
            try:
                g['geom'] = affinity.scale(g['geom'], xscale, yscale, origin=(px, py))
            except AttributeError:
                return g['geom']
        self.create_geometry()

    def skew(self, angle_x, angle_y, point):
        """
        Shear/Skew the geometries of an object by angles along x and y dimensions.

        Parameters
        ----------
        angle_x, angle_y : float, float
            The shear angle(s) for the x and y axes respectively. These can be
            specified in either degrees (default) or radians by setting
            use_radians=True.
        point: tupple of coordinates (x,y)

        See shapely manual for more information:
        http://toblerity.org/shapely/manual.html#affine-transformations
        """
        log.debug("camlib.CNCJob.skew()")

        px, py = point

        for g in self.gcode_parsed:
            try:
                g['geom'] = affinity.skew(g['geom'], angle_x, angle_y, origin=(px, py))
            except AttributeError:
                return g['geom']
        self.create_geometry()

    def rotate(self, angle, point):
        """
        Rotate the geometrys of an object by an given angle around the coordinates of the 'point'
        :param angle:
        :param point: tupple of coordinates (x,y)
        :return:
        """
        log.debug("camlib.CNCJob.rotate()")

        px, py = point

        for g in self.gcode_parsed:
            try:
                g['geom'] = affinity.rotate(g['geom'], angle, origin=(px, py))
            except AttributeError:
                return g['geom']
        self.create_geometry()


def get_bounds(geometry_list):
    xmin = Inf
    ymin = Inf
    xmax = -Inf
    ymax = -Inf

    for gs in geometry_list:
        try:
            gxmin, gymin, gxmax, gymax = gs.bounds()
            xmin = min([xmin, gxmin])
            ymin = min([ymin, gymin])
            xmax = max([xmax, gxmax])
            ymax = max([ymax, gymax])
        except:
            log.warning("DEVELOPMENT: Tried to get bounds of empty geometry.")

    return [xmin, ymin, xmax, ymax]


def arc(center, radius, start, stop, direction, steps_per_circ):
    """
    Creates a list of point along the specified arc.

    :param center: Coordinates of the center [x, y]
    :type center: list
    :param radius: Radius of the arc.
    :type radius: float
    :param start: Starting angle in radians
    :type start: float
    :param stop: End angle in radians
    :type stop: float
    :param direction: Orientation of the arc, "CW" or "CCW"
    :type direction: string
    :param steps_per_circ: Number of straight line segments to
        represent a circle.
    :type steps_per_circ: int
    :return: The desired arc, as list of tuples
    :rtype: list
    """
    # TODO: Resolution should be established by maximum error from the exact arc.

    da_sign = {"cw": -1.0, "ccw": 1.0}
    points = []
    if direction == "ccw" and stop <= start:
        stop += 2 * pi
    if direction == "cw" and stop >= start:
        stop -= 2 * pi
    
    angle = abs(stop - start)
        
    #angle = stop-start
    steps = max([int(ceil(angle / (2 * pi) * steps_per_circ)), 2])
    delta_angle = da_sign[direction] * angle * 1.0 / steps
    for i in range(steps + 1):
        theta = start + delta_angle * i
        points.append((center[0] + radius * cos(theta), center[1] + radius * sin(theta)))
    return points


def arc2(p1, p2, center, direction, steps_per_circ):
    r = sqrt((center[0] - p1[0]) ** 2 + (center[1] - p1[1]) ** 2)
    start = arctan2(p1[1] - center[1], p1[0] - center[0])
    stop = arctan2(p2[1] - center[1], p2[0] - center[0])
    return arc(center, r, start, stop, direction, steps_per_circ)


def arc_angle(start, stop, direction):
    if direction == "ccw" and stop <= start:
        stop += 2 * pi
    if direction == "cw" and stop >= start:
        stop -= 2 * pi

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

    :param obj: Shapely geometry.
    :type obj: BaseGeometry
    :return: Dictionary with serializable form if ``obj`` was
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

    :param d:  Serializable dictionary representation of an object
        to be reconstructed.
    :return: Reconstructed object.
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


def parse_gerber_number(strnumber, int_digits, frac_digits, zeros):
    """
    Parse a single number of Gerber coordinates.

    :param strnumber: String containing a number in decimal digits
    from a coordinate data block, possibly with a leading sign.
    :type strnumber: str
    :param int_digits: Number of digits used for the integer
    part of the number
    :type frac_digits: int
    :param frac_digits: Number of digits used for the fractional
    part of the number
    :type frac_digits: int
    :param zeros: If 'L', leading zeros are removed and trailing zeros are kept. Same situation for 'D' when
    no zero suppression is done. If 'T', is in reverse.
    :type zeros: str
    :return: The number in floating point.
    :rtype: float
    """

    ret_val = None

    if zeros == 'L' or zeros == 'D':
        ret_val = int(strnumber) * (10 ** (-frac_digits))

    if zeros == 'T':
        int_val = int(strnumber)
        ret_val = (int_val * (10 ** ((int_digits + frac_digits) - len(strnumber)))) * (10 ** (-frac_digits))

    return ret_val


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
#     return cascaded_union(triangles), edge_points

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
#             connections = filter(lambda k: p != k and (p[0] == k[0] or p[0] == k[1] or p[1] == k[0] or p[1] == k[1]), lineIndices_)
#             # connections = filter(lambda (i1_, i2_): (i1, i2) != (i1_, i2_) and (i1 == i1_ or i1 == i2_ or i2 == i1_ or i2 == i2_), lineIndices_)
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
#     polys = dict()
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

    :param p1: Point 1
    :param p2: Point 2
    :param p3: Point 3
    :return: center, radius
    """
    # Midpoints
    a1 = (p1 + p2) / 2.0
    a2 = (p2 + p3) / 2.0

    # Normals
    b1 = dot((p2 - p1), array([[0, -1], [1, 0]], dtype=float32))
    b2 = dot((p3 - p2), array([[0, 1], [-1, 0]], dtype=float32))

    # Params
    try:
        T = solve(transpose(array([-b1, b2])), a1 - a2)
    except Exception as e:
        log.debug("camlib.three_point_circle() --> %s" % str(e))
        return

    # Center
    center = a1 + b1 * T[0]

    # Radius
    radius = np.linalg.norm(center - p1)

    return center, radius, T[0]


def distance(pt1, pt2):
    return sqrt((pt1[0] - pt2[0]) ** 2 + (pt1[1] - pt2[1]) ** 2)


def distance_euclidian(x1, y1, x2, y2):
    return sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


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

        # Note: Shapely objects are not hashable any more, althought
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
