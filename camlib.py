############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
############################################################

#import traceback

from io import StringIO
from numpy import arctan2, Inf, array, sqrt, pi, ceil, sin, cos, dot, float32, \
    transpose
from numpy.linalg import solve, norm
import re
import sys
import traceback
from decimal import Decimal

import collections

from rtree import index as rtindex

# See: http://toblerity.org/shapely/manual.html
from shapely.geometry import Polygon, LineString, Point, LinearRing, MultiLineString
from shapely.geometry import MultiPoint, MultiPolygon
from shapely.geometry import box as shply_box
from shapely.ops import cascaded_union, unary_union
import shapely.affinity as affinity
from shapely.wkt import loads as sloads
from shapely.wkt import dumps as sdumps
from shapely.geometry.base import BaseGeometry
from shapely.geometry import shape
from shapely import speedups

from collections import Iterable

import numpy as np
import rasterio
from rasterio.features import shapes

# TODO: Commented for FlatCAM packaging with cx_freeze

from xml.dom.minidom import parseString as parse_xml_string

# from scipy.spatial import KDTree, Delaunay

from ParseSVG import *
from ParseDXF import *

import logging
import os
# import pprint
import platform
import FlatCAMApp

import math

if platform.architecture()[0] == '64bit':
    from ortools.constraint_solver import pywrapcp
    from ortools.constraint_solver import routing_enums_pb2


log = logging.getLogger('base2')
log.setLevel(logging.DEBUG)
# log.setLevel(logging.WARNING)
# log.setLevel(logging.INFO)
formatter = logging.Formatter('[%(levelname)s] %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
log.addHandler(handler)


class ParseError(Exception):
    pass


class Geometry(object):
    """
    Base geometry class.
    """

    defaults = {
        "units": 'in',
        "geo_steps_per_circle": 64
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

        if geo_steps_per_circle is None:
            geo_steps_per_circle = int(Geometry.defaults["geo_steps_per_circle"])
        self.geo_steps_per_circle = geo_steps_per_circle

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
        # TODO: Decide what solid_geometry is supposed to be and how we append to it.

        if self.solid_geometry is None:
            self.solid_geometry = []

        if type(self.solid_geometry) is list:
            self.solid_geometry.append(Point(origin).buffer(radius, int(int(self.geo_steps_per_circle) / 4)))
            return

        try:
            self.solid_geometry = self.solid_geometry.union(Point(origin).buffer(radius,
                                                                                 int(int(self.geo_steps_per_circle) / 4)))
        except:
            #print "Failed to run union on polygons."
            log.error("Failed to run union on polygons.")
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
        except:
            #print "Failed to run union on polygons."
            log.error("Failed to run union on polygons.")
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
        except:
            #print "Failed to run union on polygons."
            log.error("Failed to run union on polylines.")
            return

    def is_empty(self):

        if isinstance(self.solid_geometry, BaseGeometry):
            return self.solid_geometry.is_empty

        if isinstance(self.solid_geometry, list):
            return len(self.solid_geometry) == 0

        self.app.inform.emit("[ERROR_NOTCL] self.solid_geometry is neither BaseGeometry or list.")
        return

    def subtract_polygon(self, points):
        """
        Subtract polygon from the given object. This only operates on the paths in the original geometry, i.e. it converts polygons into paths.

        :param points: The vertices of the polygon.
        :return: none
        """
        if self.solid_geometry is None:
            self.solid_geometry = []

        #pathonly should be allways True, otherwise polygons are not subtracted
        flat_geometry = self.flatten(pathonly=True)
        log.debug("%d paths" % len(flat_geometry))
        polygon=Polygon(points)
        toolgeo=cascaded_union(polygon)
        diffs=[]
        for target in flat_geometry:
            if type(target) == LineString or type(target) == LinearRing:
                diffs.append(target.difference(toolgeo))
            else:
                log.warning("Not implemented.")
        self.solid_geometry=cascaded_union(diffs)

    def bounds(self):
        """
        Returns coordinates of rectangular bounds
        of geometry: (xmin, ymin, xmax, ymax).
        """
        # fixed issue of getting bounds only for one level lists of objects
        # now it can get bounds for nested lists of objects

        log.debug("Geometry->bounds()")
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

        :param poly: See description
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

        ## If iterable, expand recursively.
        try:
            for geo in geometry:
                interiors.extend(self.get_interiors(geometry=geo))

        ## Not iterable, get the interiors if polygon.
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

        ## If iterable, expand recursively.
        try:
            for geo in geometry:
                exteriors.extend(self.get_exteriors(geometry=geo))

        ## Not iterable, get the exterior if polygon.
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

        ## If iterable, expand recursively.
        try:
            for geo in geometry:
                if geo is not None:
                    self.flatten(geometry=geo,
                                 reset=False,
                                 pathonly=pathonly)

        ## Not iterable, do the actual indexing and add.
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
    #     ## If iterable, expand recursively.
    #     try:
    #         for geo in geometry:
    #             self.flatten_to_paths(geometry=geo, reset=False)
    #
    #     ## Not iterable, do the actual indexing and add.
    #     except TypeError:
    #         if type(geometry) == Polygon:
    #             g = geometry.exterior
    #             self.flat_geometry.append(g)
    #
    #             ## Add first and last points of the path to the index.
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
        :type integer
        :param corner: type of corner for the isolation: 0 = round; 1 = square; 2= beveled (line that connects the ends)
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
        if offset == 0:
            if follow:
                geo_iso = self.follow_geometry
            else:
                geo_iso = self.solid_geometry
        else:
            if follow:
                geo_iso = self.follow_geometry
            else:
                if corner is None:
                    geo_iso = self.solid_geometry.buffer(offset, int(int(self.geo_steps_per_circle) / 4))
                else:
                    geo_iso = self.solid_geometry.buffer(offset, int(int(self.geo_steps_per_circle) / 4),
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
        :param flip: Flip the vertically.
        :type flip: bool
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
        self.solid_geometry = cascaded_union(self.solid_geometry)

        geos_text = getsvgtext(svg_root, object_type, units=units)
        if geos_text is not None:
            geos_text_f = []
            if flip:
                # Change origin to bottom left
                for i in geos_text:
                    _, minimy, _, maximy = i.bounds
                    h2 = (maximy - minimy) * 0.5
                    geos_text_f.append(translate(scale(i, 1.0, -1.0, origin=(0, 0)), yoff=(h + h2)))
            self.solid_geometry = [self.solid_geometry, geos_text_f]

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
            except:
                pass

            try:
                blue= src.read(3)
            except:
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
    def clear_polygon(polygon, tooldia, steps_per_circle, overlap=0.15, connect=True,
                        contour=True):
        """
        Creates geometry inside a polygon for a tool to cover
        the whole area.

        This algorithm shrinks the edges of the polygon and takes
        the resulting edges as toolpaths.

        :param polygon: Polygon to clear.
        :param tooldia: Diameter of the tool.
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

        ## The toolpaths
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

        ## The toolpaths
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
                #geoms.append(path)
                #geoms.insert(path)
                # path can be a collection of paths.
                try:
                    for p in path:
                        geoms.insert(p)
                except TypeError:
                    geoms.insert(path)

            radius += tooldia * (1 - overlap)

        # Clean inside edges (contours) of the original polygon
        if contour:
            outer_edges = [x.exterior for x in autolist(polygon_to_clear.buffer(-tooldia / 2, int(steps_per_circle / 4)))]
            inner_edges = []
            for x in autolist(polygon_to_clear.buffer(-tooldia / 2, int(steps_per_circle / 4))):  # Over resulting polygons
                for y in x.interiors:  # Over interiors of each polygon
                    inner_edges.append(y)
            #geoms += outer_edges + inner_edges
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
    def clear_polygon3(polygon, tooldia, steps_per_circle, overlap=0.15, connect=True,
                       contour=True):
        """
        Creates geometry inside a polygon for a tool to cover
        the whole area.

        This algorithm draws horizontal lines inside the polygon.

        :param polygon: The polygon being painted.
        :type polygon: shapely.geometry.Polygon
        :param tooldia: Tool diameter.
        :param overlap: Tool path overlap percentage.
        :param connect: Connect lines to avoid tool lifts.
        :param contour: Paint around the edges.
        :return:
        """

        # log.debug("camlib.clear_polygon3()")

        ## The toolpaths
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
            geoms.insert(margin_poly.exterior)
            for ints in margin_poly.interiors:
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
        :param factor: Number by which to scale.
        :type factor: float
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
        :param max_walk: Maximum allowable distance without lifting tool.
        :type max_walk: float or None
        :return: Optimized geometry.
        :rtype: FlatCAMRTreeStorage
        """

        # If max_walk is not specified, the maximum allowed is
        # 10 times the tool diameter
        max_walk = max_walk or 10 * tooldia

        # Assuming geolist is a flat list of flat elements

        ## Index first and last points in paths
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

        ## Iterate over geometry paths getting the nearest each time.
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
                #log.debug("Path %d" % path_count)

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
                    #log.debug("Walk to path #%d is inside. Joining." % path_count)

                    # Completely inside. Append...
                    geo.coords = list(geo.coords) + list(candidate.coords)
                    # try:
                    #     last = optimized_paths[-1]
                    #     last.coords = list(last.coords) + list(geo.coords)
                    # except IndexError:
                    #     optimized_paths.append(geo)

                else:

                    # Have to lift tool. End path.
                    #log.debug("Path #%d not within boundary. Next." % path_count)
                    #optimized_paths.append(geo)
                    optimized_paths.insert(geo)
                    geo = candidate

                current_pt = geo.coords[-1]

                # Next
                #pt, geo = storage.nearest(current_pt)

        except StopIteration:  # Nothing left in storage.
            #pass
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

        ## Index first and last points in paths
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
        #optimized_geometry = [geo]
        optimized_geometry = FlatCAMRTreeStorage()
        optimized_geometry.get_points = get_pts
        #optimized_geometry.insert(geo)
        try:
            while True:
                path_count += 1

                #print "geo is", geo

                _, left = storage.nearest(geo.coords[0])
                #print "left is", left

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
                #print "right is", right

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
                    # Cannot exteng geo any further. Put it away.
                    optimized_geometry.insert(geo)

                    # Continue with right.
                    geo = right

        except StopIteration:  # Nothing found in storage.
            optimized_geometry.insert(geo)

        #print path_count
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
        log.debug("Geometry.convert_units()")

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
        self.scale(factor)
        self.file_units_factor = factor
        return factor

    def to_dict(self):
        """
        Returns a respresentation of the object as a dictionary.
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

        px, py = point
        xscale, yscale = {"X": (1.0, -1.0), "Y": (-1.0, 1.0)}[axis]

        def mirror_geom(obj):
            if type(obj) is list:
                new_obj = []
                for g in obj:
                    new_obj.append(mirror_geom(g))
                return new_obj
            else:
                return affinity.scale(obj, xscale, yscale, origin=(px,py))

        try:
            if self.multigeo is True:
                for tool in self.tools:
                    self.tools[tool]['solid_geometry'] = mirror_geom(self.tools[tool]['solid_geometry'])
            else:
                self.solid_geometry = mirror_geom(self.solid_geometry)
            self.app.inform.emit('[success]Object was mirrored ...')
        except AttributeError:
            self.app.inform.emit("[ERROR_NOTCL] Failed to mirror. No object selected")

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

        px, py = point

        def rotate_geom(obj):
            if type(obj) is list:
                new_obj = []
                for g in obj:
                    new_obj.append(rotate_geom(g))
                return new_obj
            else:
                return affinity.rotate(obj, angle, origin=(px, py))

        try:
            if self.multigeo is True:
                for tool in self.tools:
                    self.tools[tool]['solid_geometry'] = rotate_geom(self.tools[tool]['solid_geometry'])
            else:
                self.solid_geometry = rotate_geom(self.solid_geometry)
            self.app.inform.emit('[success]Object was rotated ...')
        except AttributeError:
            self.app.inform.emit("[ERROR_NOTCL] Failed to rotate. No object selected")

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
        px, py = point

        def skew_geom(obj):
            if type(obj) is list:
                new_obj = []
                for g in obj:
                    new_obj.append(skew_geom(g))
                return new_obj
            else:
                return affinity.skew(obj, angle_x, angle_y, origin=(px, py))

        try:
            if self.multigeo is True:
                for tool in self.tools:
                    self.tools[tool]['solid_geometry'] = skew_geom(self.tools[tool]['solid_geometry'])
            else:
                self.solid_geometry = skew_geom(self.solid_geometry)
            self.app.inform.emit('[success]Object was skewed ...')
        except AttributeError:
            self.app.inform.emit("[ERROR_NOTCL] Failed to skew. No object selected")

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

    ## Regular expressions
    am1_re = re.compile(r'^%AM([^\*]+)\*(.+)?(%)?$')
    am2_re = re.compile(r'(.*)%$')
    amcomm_re = re.compile(r'^0(.*)')
    amprim_re = re.compile(r'^[1-9].*')
    amvar_re = re.compile(r'^\$([0-9a-zA-z]+)=(.*)')

    def __init__(self, name=None):
        self.name = name
        self.raw = ""

        ## These below are recomputed for every aperture
        ## definition, in other words, are temporary variables.
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

        #### Every part in the macro ####
        for part in parts:
            ### Comments. Ignored.
            match = ApertureMacro.amcomm_re.search(part)
            if match:
                continue

            ### Variables
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

            ### Primitives
            # Each is an array. The first identifies the primitive, while the
            # rest depend on the primitive. All are strings representing a
            # number and may contain variable definition. The values of these
            # variables are defined in an aperture definition.
            match = ApertureMacro.amprim_re.search(part)
            if match:
                ## Replace all variables
                for v in self.locvars:
                    # replaced the following line with the next to fix Mentor custom apertures not parsed OK
                    # part = re.sub(r'\$' + str(v) + r'(?![0-9a-zA-Z])', str(self.locvars[v]), part)
                    part = part.replace('$' + str(v), str(self.locvars[v]))

                # Make all others 0
                part = re.sub(r'\$[0-9a-zA-Z](?![0-9a-zA-Z])', "0", part)

                # Change x with *
                part = re.sub(r'[xX]', "*", part)

                ## Store
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

        ## If the ring does not have an interior it means that it is
        ## a disk. Then stop.
        while len(ring.interiors) > 0 and i < nrings:
            r -= thickness + gap
            if r <= 0:
                break
            ring = Point((x, y)).buffer(r).exterior.buffer(thickness/2.0)
            result = cascaded_union([result, ring])
            i += 1

        ## Crosshair
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

        ## Primitive makers
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

        ## Store modifiers as local variables
        modifiers = modifiers or []
        modifiers = [float(m) for m in modifiers]
        self.locvars = {}
        for i in range(0, len(modifiers)):
            self.locvars[str(i + 1)] = modifiers[i]

        ## Parse
        self.primitives = []  # Cleanup
        self.geometry = Polygon()
        self.parse_content()

        ## Make the geometry
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

    defaults = {
        "steps_per_circle": 56,
        "use_buffer_for_union": True
    }

    def __init__(self, steps_per_circle=None):
        """
        The constructor takes no parameters. Use ``gerber.parse_files()``
        or ``gerber.parse_lines()`` to populate the object from Gerber source.

        :return: Gerber object
        :rtype: Gerber
        """

        # How to discretize a circle.
        if steps_per_circle is None:
            steps_per_circle = int(Gerber.defaults['steps_per_circle'])
        self.steps_per_circle = int(steps_per_circle)

        # Initialize parent
        Geometry.__init__(self, geo_steps_per_circle=int(steps_per_circle))

        # will store the Gerber geometry's as solids
        self.solid_geometry = Polygon()

        # will store the Gerber geometry's as paths
        self.follow_geometry = []

        # Number format
        self.int_digits = 3
        """Number of integer digits in Gerber numbers. Used during parsing."""

        self.frac_digits = 4
        """Number of fraction digits in Gerber numbers. Used during parsing."""

        self.gerber_zeros = 'L'
        """Zeros in Gerber numbers. If 'L' then remove leading zeros, if 'T' remove trailing zeros. Used during parsing.
        """

        ## Gerber elements ##
        # Apertures {'id':{'type':chr, 
        #             ['size':float], ['width':float],
        #             ['height':float]}, ...}
        self.apertures = {}

        # Aperture Macros
        self.aperture_macros = {}

        self.source_file = ''

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from Geometry.
        self.ser_attrs += ['int_digits', 'frac_digits', 'apertures',
                           'aperture_macros', 'solid_geometry', 'source_file']

        #### Parser patterns ####
        # FS - Format Specification
        # The format of X and Y must be the same!
        # L-omit leading zeros, T-omit trailing zeros
        # A-absolute notation, I-incremental notation
        self.fmt_re = re.compile(r'%FS([LT])([AI])X(\d)(\d)Y\d\d\*%$')
        self.fmt_re_alt = re.compile(r'%FS([LT])([AI])X(\d)(\d)Y\d\d\*MO(IN|MM)\*%$')
        self.fmt_re_orcad = re.compile(r'(G\d+)*\**%FS([LT])([AI]).*X(\d)(\d)Y\d\d\*%$')

        # Mode (IN/MM)
        self.mode_re = re.compile(r'^%MO(IN|MM)\*%$')

        # Comment G04|G4
        self.comm_re = re.compile(r'^G0?4(.*)$')

        # AD - Aperture definition
        # Aperture Macro names: Name = [a-zA-Z_.$]{[a-zA-Z_.0-9]+}
        # NOTE: Adding "-" to support output from Upverter.
        self.ad_re = re.compile(r'^%ADD(\d\d+)([a-zA-Z_$\.][a-zA-Z0-9_$\.\-]*)(?:,(.*))?\*%$')

        # AM - Aperture Macro
        # Beginning of macro (Ends with *%):
        #self.am_re = re.compile(r'^%AM([a-zA-Z0-9]*)\*')

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
        self.pol_re = re.compile(r'^%IP(POS|NEG)\*%$')

        # LP - Level polarity
        self.lpol_re = re.compile(r'^%LP([DC])\*%$')

        # Units (OBSOLETE)
        self.units_re = re.compile(r'^G7([01])\*$')

        # Absolute/Relative G90/1 (OBSOLETE)
        self.absrel_re = re.compile(r'^G9([01])\*$')

        # Aperture macros
        self.am1_re = re.compile(r'^%AM([^\*]+)\*([^%]+)?(%)?$')
        self.am2_re = re.compile(r'(.*)%$')

        self.use_buffer_for_union = self.defaults["use_buffer_for_union"]

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
                            # yield cleanline
                            yield line
                            break

            self.parse_lines(line_generator())

    #@profile
    def parse_lines(self, glines):
        """
        Main Gerber parser. Reads Gerber and populates ``self.paths``, ``self.apertures``,
        ``self.flashes``, ``self.regions`` and ``self.units``.

        :param glines: Gerber code as list of strings, each element being
            one line of the source file.
        :type glines: list
        :param follow: If true, will not create polygons, just lines
            following the gerber path.
        :type follow: bool
        :return: None
        :rtype: None
        """

        # Coordinates of the current path, each is [x, y]
        path = []

        # this is for temporary storage of geometry until it is added to poly_buffer
        geo = None

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

        #### Parsing starts here ####
        line_num = 0
        gline = ""
        try:
            for gline in glines:
                line_num += 1

                self.source_file += gline + '\n'

                ### Cleanup
                gline = gline.strip(' \r\n')
                # log.debug("Line=%3s %s" % (line_num, gline))

                #### Ignored lines
                ## Comments
                match = self.comm_re.search(gline)
                if match:
                    continue

                ### Polarity change
                # Example: %LPD*% or %LPC*%
                # If polarity changes, creates geometry from current
                # buffer, then adds or subtracts accordingly.
                match = self.lpol_re.search(gline)
                if match:
                    if len(path) > 1 and current_polarity != match.group(1):

                        # --- Buffered ----
                        width = self.apertures[last_path_aperture]["size"]

                        geo = LineString(path)
                        if not geo.is_empty:
                            follow_buffer.append(geo)

                        geo = LineString(path).buffer(width / 1.999, int(self.steps_per_circle / 4))
                        if not geo.is_empty:
                            poly_buffer.append(geo)

                        path = [path[-1]]

                    # --- Apply buffer ---
                    # If added for testing of bug #83
                    # TODO: Remove when bug fixed
                    if len(poly_buffer) > 0:
                        if current_polarity == 'D':
                            self.follow_geometry = self.solid_geometry.union(cascaded_union(follow_buffer))
                            self.solid_geometry = self.solid_geometry.union(cascaded_union(poly_buffer))

                        else:
                            self.follow_geometry = self.solid_geometry.difference(cascaded_union(follow_buffer))
                            self.solid_geometry = self.solid_geometry.union(cascaded_union(poly_buffer))

                        follow_buffer = []
                        poly_buffer = []

                    current_polarity = match.group(1)
                    continue

                ### Number format
                # Example: %FSLAX24Y24*%
                # TODO: This is ignoring most of the format. Implement the rest.
                match = self.fmt_re.search(gline)
                if match:
                    absolute = {'A': 'Absolute', 'I': 'Relative'}[match.group(2)]
                    self.gerber_zeros = match.group(1)
                    self.int_digits = int(match.group(3))
                    self.frac_digits = int(match.group(4))
                    log.debug("Gerber format found. (%s) " % str(gline))

                    log.debug(
                        "Gerber format found. Gerber zeros = %s (L-omit leading zeros, T-omit trailing zeros)" %
                        self.gerber_zeros)
                    log.debug("Gerber format found. Coordinates type = %s (Absolute or Relative)" % absolute)
                    continue

                ### Mode (IN/MM)
                # Example: %MOIN*%
                match = self.mode_re.search(gline)
                if match:
                    gerber_units = match.group(1)
                    log.debug("Gerber units found = %s" % gerber_units)
                    # Changed for issue #80
                    self.convert_units(match.group(1))
                    continue

                ### Combined Number format and Mode --- Allegro does this
                match = self.fmt_re_alt.search(gline)
                if match:
                    absolute = {'A': 'Absolute', 'I': 'Relative'}[match.group(2)]
                    self.gerber_zeros = match.group(1)
                    self.int_digits = int(match.group(3))
                    self.frac_digits = int(match.group(4))
                    log.debug("Gerber format found. (%s) " % str(gline))
                    log.debug(
                        "Gerber format found. Gerber zeros = %s (L-omit leading zeros, T-omit trailing zeros)" %
                        self.gerber_zeros)
                    log.debug("Gerber format found. Coordinates type = %s (Absolute or Relative)" % absolute)

                    gerber_units = match.group(1)
                    log.debug("Gerber units found = %s" % gerber_units)
                    # Changed for issue #80
                    self.convert_units(match.group(5))
                    continue

                ### Search for OrCAD way for having Number format
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
                            "Gerber format found. Gerber zeros = %s (L-omit leading zeros, T-omit trailing zeros)" %
                            self.gerber_zeros)
                        log.debug("Gerber format found. Coordinates type = %s (Absolute or Relative)" % absolute)

                        gerber_units = match.group(1)
                        log.debug("Gerber units found = %s" % gerber_units)
                        # Changed for issue #80
                        self.convert_units(match.group(5))
                        continue

                ### Units (G70/1) OBSOLETE
                match = self.units_re.search(gline)
                if match:
                    obs_gerber_units = {'0': 'IN', '1': 'MM'}[match.group(1)]
                    log.warning("Gerber obsolete units found = %s" % obs_gerber_units)
                    # Changed for issue #80
                    self.convert_units({'0': 'IN', '1': 'MM'}[match.group(1)])
                    continue

                ### Absolute/relative coordinates G90/1 OBSOLETE
                match = self.absrel_re.search(gline)
                if match:
                    absolute = {'0': "Absolute", '1': "Relative"}[match.group(1)]
                    log.warning("Gerber obsolete coordinates type found = %s (Absolute or Relative) " % absolute)
                    continue

                ### Aperture Macros
                # Having this at the beginning will slow things down
                # but macros can have complicated statements than could
                # be caught by other patterns.
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
                            #self.aperture_macros[current_macro].parse_content()
                            current_macro = None
                            log.debug("Macro complete in 1 line.")
                        continue
                else:  # Continue macro
                    log.debug("Continuing macro. Line %d." % line_num)
                    match = self.am2_re.search(gline)
                    if match:  # Finish macro
                        log.debug("End of macro. Line %d." % line_num)
                        self.aperture_macros[current_macro].append(match.group(1))
                        #self.aperture_macros[current_macro].parse_content()
                        current_macro = None
                    else:  # Append
                        self.aperture_macros[current_macro].append(gline)
                    continue

                ### Aperture definitions %ADD...
                match = self.ad_re.search(gline)
                if match:
                    log.info("Found aperture definition. Line %d: %s" % (line_num, gline))
                    self.aperture_parse(match.group(1), match.group(2), match.group(3))
                    continue

                ### Operation code alone
                # Operation code alone, usually just D03 (Flash)
                # self.opcode_re = re.compile(r'^D0?([123])\*$')
                match = self.opcode_re.search(gline)
                if match:
                    current_operation_code = int(match.group(1))
                    current_d = current_operation_code

                    if current_operation_code == 3:

                        ## --- Buffered ---
                        try:
                            log.debug("Bare op-code %d." % current_operation_code)
                            # flash = Gerber.create_flash_geometry(Point(path[-1]),
                            #                                      self.apertures[current_aperture])
                            flash = Gerber.create_flash_geometry(
                                Point(current_x, current_y), self.apertures[current_aperture],
                                int(self.steps_per_circle))
                            if not flash.is_empty:
                                poly_buffer.append(flash)
                        except IndexError:
                            log.warning("Line %d: %s -> Nothing there to flash!" % (line_num, gline))

                    continue

                ### Tool/aperture change
                # Example: D12*
                match = self.tool_re.search(gline)
                if match:
                    current_aperture = match.group(1)
                    log.debug("Line %d: Aperture change to (%s)" % (line_num, match.group(1)))

                    # If the aperture value is zero then make it something quite small but with a non-zero value
                    # so it can be processed by FlatCAM.
                    # But first test to see if the aperture type is "aperture macro". In that case
                    # we should not test for "size" key as it does not exist in this case.
                    if self.apertures[current_aperture]["type"] is not "AM":
                        if self.apertures[current_aperture]["size"] == 0:
                            self.apertures[current_aperture]["size"] = 1e-12
                    log.debug(self.apertures[current_aperture])

                    # Take care of the current path with the previous tool
                    if len(path) > 1:
                        if self.apertures[last_path_aperture]["type"] == 'R':
                            # do nothing because 'R' type moving aperture is none at once
                            pass
                        else:
                            # --- Buffered ----
                            width = self.apertures[last_path_aperture]["size"]

                            geo = LineString(path)
                            if not geo.is_empty:
                                follow_buffer.append(geo)

                            geo = LineString(path).buffer(width / 1.999, int(self.steps_per_circle / 4))
                            if not geo.is_empty:
                                poly_buffer.append(geo)

                            path = [path[-1]]

                    continue

                ### G36* - Begin region
                if self.regionon_re.search(gline):
                    if len(path) > 1:
                        # Take care of what is left in the path

                        ## --- Buffered ---
                        width = self.apertures[last_path_aperture]["size"]

                        geo = LineString(path)
                        if not geo.is_empty:
                            follow_buffer.append(geo)

                        geo = LineString(path).buffer(width/1.999, int(self.steps_per_circle / 4))
                        if not geo.is_empty:
                            poly_buffer.append(geo)

                        path = [path[-1]]

                    making_region = True
                    continue

                ### G37* - End region
                if self.regionoff_re.search(gline):
                    making_region = False

                    # if D02 happened before G37 we now have a path with 1 element only so we have to add the current
                    # geo to the poly_buffer otherwise we loose it
                    if current_operation_code == 2:
                        if geo:
                            if not geo.is_empty:
                                follow_buffer.append(geo)
                                poly_buffer.append(geo)
                            continue

                    # Only one path defines region?
                    # This can happen if D02 happened before G37 and
                    # is not and error.
                    if len(path) < 3:
                        # print "ERROR: Path contains less than 3 points:"
                        # print path
                        # print "Line (%d): " % line_num, gline
                        # path = []
                        #path = [[current_x, current_y]]
                        continue

                    # For regions we may ignore an aperture that is None
                    # self.regions.append({"polygon": Polygon(path),
                    #                      "aperture": last_path_aperture})

                    # --- Buffered ---

                    region = Polygon()
                    if not region.is_empty:
                        follow_buffer.append(region)

                    region = Polygon(path)
                    if not region.is_valid:
                        region = region.buffer(0, int(self.steps_per_circle / 4))
                    if not region.is_empty:
                        poly_buffer.append(region)

                    path = [[current_x, current_y]]  # Start new path
                    continue

                ### G01/2/3* - Interpolation mode change
                # Can occur along with coordinates and operation code but
                # sometimes by itself (handled here).
                # Example: G01*
                match = self.interp_re.search(gline)
                if match:
                    current_interpolation_mode = int(match.group(1))
                    continue

                ### G01 - Linear interpolation plus flashes
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
                        if linear_x is not None and linear_y is not None:
                            # only add the point if it's a new one otherwise skip it (harder to process)
                            if path[-1] != [linear_x, linear_y]:
                                path.append([linear_x, linear_y])

                            if  making_region is False:
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
                                        poly_buffer.append(shply_box(minx, miny, maxx, maxy))
                                except:
                                    pass
                            last_path_aperture = current_aperture
                        else:
                            self.app.inform.emit("[WARNING] Coordinates missing, line ignored: %s" % str(gline))
                            self.app.inform.emit("[WARNING_NOTCL] GERBER file might be CORRUPT. Check the file !!!")

                    elif current_operation_code == 2:
                        if len(path) > 1:
                            geo = None

                            ## --- BUFFERED ---
                            # this treats the case when we are storing geometry as paths only
                            if making_region:
                                geo = Polygon()
                            else:
                                geo = LineString(path)
                            try:
                                if self.apertures[last_path_aperture]["type"] != 'R':
                                    if not geo.is_empty:
                                        follow_buffer.append(geo)
                            except:
                                follow_buffer.append(geo)

                            # this treats the case when we are storing geometry as solids
                            if making_region:
                                elem = [linear_x, linear_y]
                                if elem != path[-1]:
                                    path.append([linear_x, linear_y])
                                try:
                                    geo = Polygon(path)
                                except ValueError:
                                    log.warning("Problem %s %s" % (gline, line_num))
                                    self.app.inform.emit("[ERROR] Region does not have enough points. "
                                                         "File will be processed but there are parser errors. "
                                                         "Line number: %s" % str(line_num))
                            else:
                                if last_path_aperture is None:
                                    log.warning("No aperture defined for curent path. (%d)" % line_num)
                                width = self.apertures[last_path_aperture]["size"]  # TODO: WARNING this should fail!
                                geo = LineString(path).buffer(width / 1.999, int(self.steps_per_circle / 4))

                            try:
                                if self.apertures[last_path_aperture]["type"] != 'R':
                                    if not geo.is_empty:
                                        poly_buffer.append(geo)
                            except:
                                poly_buffer.append(geo)

                        # if linear_x or linear_y are None, ignore those
                        if linear_x is not None and linear_y is not None:
                            path = [[linear_x, linear_y]]  # Start new path
                        else:
                            self.app.inform.emit("[WARNING] Coordinates missing, line ignored: %s" % str(gline))
                            self.app.inform.emit("[WARNING_NOTCL] GERBER file might be CORRUPT. Check the file !!!")

                    # Flash
                    # Not allowed in region mode.
                    elif current_operation_code == 3:

                        # Create path draw so far.
                        if len(path) > 1:
                            # --- Buffered ----

                            # this treats the case when we are storing geometry as paths
                            geo = LineString(path)
                            if not geo.is_empty:
                                try:
                                    if self.apertures[current_aperture]["type"] != 'R':
                                        follow_buffer.append(geo)
                                except:
                                    follow_buffer.append(geo)

                            # this treats the case when we are storing geometry as solids
                            width = self.apertures[last_path_aperture]["size"]
                            geo = LineString(path).buffer(width / 1.999, int(self.steps_per_circle / 4))
                            if not geo.is_empty:
                                try:
                                    if self.apertures[current_aperture]["type"] != 'R':
                                        poly_buffer.append(geo)
                                except:
                                    poly_buffer.append(geo)

                        # Reset path starting point
                        path = [[linear_x, linear_y]]

                        # --- BUFFERED ---
                        # Draw the flash
                        # this treats the case when we are storing geometry as paths
                        follow_buffer.append(Point([linear_x, linear_y]))

                        # this treats the case when we are storing geometry as solids
                        flash = Gerber.create_flash_geometry(
                            Point( [linear_x, linear_y]),
                            self.apertures[current_aperture],
                            int(self.steps_per_circle)
                        )
                        if not flash.is_empty:
                            poly_buffer.append(flash)

                    # maybe those lines are not exactly needed but it is easier to read the program as those coordinates
                    # are used in case that circular interpolation is encountered within the Gerber file
                    current_x = linear_x
                    current_y = linear_y

                    # log.debug("Line_number=%3s X=%s Y=%s (%s)" % (line_num, linear_x, linear_y, gline))
                    continue

                ### G74/75* - Single or multiple quadrant arcs
                match = self.quad_re.search(gline)
                if match:
                    if match.group(1) == '4':
                        quadrant_mode = 'SINGLE'
                    else:
                        quadrant_mode = 'MULTI'
                    continue

                ### G02/3 - Circular interpolation
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
                    try:
                        current_operation_code = int(d)
                        current_d = current_operation_code
                    except:
                        current_operation_code = current_d

                    # Nothing created! Pen Up.
                    if current_operation_code == 2:
                        log.warning("Arc with D2. (%d)" % line_num)
                        if len(path) > 1:
                            if last_path_aperture is None:
                                log.warning("No aperture defined for curent path. (%d)" % line_num)

                            # --- BUFFERED ---
                            width = self.apertures[last_path_aperture]["size"]

                            # this treats the case when we are storing geometry as paths
                            geo = LineString(path)
                            if not geo.is_empty:
                                follow_buffer.append(geo)

                            # this treats the case when we are storing geometry as solids
                            buffered = LineString(path).buffer(width / 1.999, int(self.steps_per_circle))
                            if not buffered.is_empty:
                                poly_buffer.append(buffered)

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
                                       int(self.steps_per_circle))

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
                                               int(self.steps_per_circle))

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

                ## EOF
                match = self.eof_re.search(gline)
                if match:
                    continue

                ### Line did not match any pattern. Warn user.
                log.warning("Line ignored (%d): %s" % (line_num, gline))

            if len(path) > 1:
                # In case that G01 (moving) aperture is rectangular, there is no need to still create
                # another geo since we already created a shapely box using the start and end coordinates found in
                # path variable. We do it only for other apertures than 'R' type
                if self.apertures[last_path_aperture]["type"] == 'R':
                    pass
                else:
                    # EOF, create shapely LineString if something still in path
                    ## --- Buffered ---

                    # this treats the case when we are storing geometry as paths
                    geo = LineString(path)
                    if not geo.is_empty:
                        follow_buffer.append(geo)

                    # this treats the case when we are storing geometry as solids
                    width = self.apertures[last_path_aperture]["size"]
                    geo = LineString(path).buffer(width / 1.999, int(self.steps_per_circle / 4))
                    if not geo.is_empty:
                        poly_buffer.append(geo)

            # --- Apply buffer ---

            # this treats the case when we are storing geometry as paths
            self.follow_geometry = follow_buffer

            # this treats the case when we are storing geometry as solids
            log.warning("Joining %d polygons." % len(poly_buffer))

            if len(poly_buffer) == 0:
                log.error("Object is not Gerber file or empty. Aborting Object creation.")
                return

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
            #print traceback.format_exc()

            log.error("Gerber PARSING FAILED. Line %d: %s" % (line_num, gline))
            loc = 'Gerber Line #%d Gerber Line Content: %s\n' % (line_num, gline) + repr(err)
            self.app.inform.emit("[ERROR]Gerber Parser ERROR.\n%s:" % loc)

    @staticmethod
    def create_flash_geometry(location, aperture, steps_per_circle=None):

        # log.debug('Flashing @%s, Aperture: %s' % (location, aperture))

        if steps_per_circle is None:
            steps_per_circle = 64

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

        log.debug("Gerber->bounds()")
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
                        try:
                            minx_, miny_, maxx_, maxy_ = bounds_rec(k)
                        except Exception as e:
                            log.debug("camlib.Geometry.bounds() --> %s" % str(e))
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

        :param factor: Number by which to scale.
        :type factor: float
        :rtype : None
        """

        try:
            xfactor = float(xfactor)
        except:
            self.app.inform.emit("[ERROR_NOTCL] Scale factor has to be a number: integer or float.")
            return

        if yfactor is None:
            yfactor = xfactor
        else:
            try:
                yfactor = float(yfactor)
            except:
                self.app.inform.emit("[ERROR_NOTCL] Scale factor has to be a number: integer or float.")
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
                return affinity.scale(obj, xfactor,
                                             yfactor, origin=(px, py))

        self.solid_geometry = scale_geom(self.solid_geometry)
        self.app.inform.emit("[success]Gerber Scale done.")

        ## solid_geometry ???
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
        try:
            dx, dy = vect
        except TypeError:
            self.app.inform.emit("[ERROR_NOTCL]An (x,y) pair of values are needed. "
                                 "Probable you entered only one value in the Offset field.")
            return

        def offset_geom(obj):
            if type(obj) is list:
                new_obj = []
                for g in obj:
                    new_obj.append(offset_geom(g))
                return new_obj
            else:
                return affinity.translate(obj, xoff=dx, yoff=dy)

        ## Solid geometry
        # self.solid_geometry = affinity.translate(self.solid_geometry, xoff=dx, yoff=dy)
        self.solid_geometry = offset_geom(self.solid_geometry)
        self.app.inform.emit("[success]Gerber Offset done.")

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

        px, py = point
        xscale, yscale = {"X": (1.0, -1.0), "Y": (-1.0, 1.0)}[axis]

        def mirror_geom(obj):
            if type(obj) is list:
                new_obj = []
                for g in obj:
                    new_obj.append(mirror_geom(g))
                return new_obj
            else:
                return affinity.scale(obj, xscale, yscale, origin=(px, py))

        self.solid_geometry = mirror_geom(self.solid_geometry)

        #  It's a cascaded union of objects.
        # self.solid_geometry = affinity.scale(self.solid_geometry,
        #                                      xscale, yscale, origin=(px, py))


    def skew(self, angle_x, angle_y, point):
        """
        Shear/Skew the geometries of an object by angles along x and y dimensions.

        Parameters
        ----------
        xs, ys : float, float
            The shear angle(s) for the x and y axes respectively. These can be
            specified in either degrees (default) or radians by setting
            use_radians=True.

        See shapely manual for more information:
        http://toblerity.org/shapely/manual.html#affine-transformations
        """

        px, py = point

        def skew_geom(obj):
            if type(obj) is list:
                new_obj = []
                for g in obj:
                    new_obj.append(skew_geom(g))
                return new_obj
            else:
                return affinity.skew(obj, angle_x, angle_y, origin=(px, py))

        self.solid_geometry = skew_geom(self.solid_geometry)

        # self.solid_geometry = affinity.skew(self.solid_geometry, angle_x, angle_y, origin=(px, py))

    def rotate(self, angle, point):
        """
        Rotate an object by a given angle around given coords (point)
        :param angle:
        :param point:
        :return:
        """

        px, py = point

        def rotate_geom(obj):
            if type(obj) is list:
                new_obj = []
                for g in obj:
                    new_obj.append(rotate_geom(g))
                return new_obj
            else:
                return affinity.rotate(obj, angle, origin=(px, py))

        self.solid_geometry = rotate_geom(self.solid_geometry)

        # self.solid_geometry = affinity.rotate(self.solid_geometry, angle, origin=(px, py))


class Excellon(Geometry):
    """
    *ATTRIBUTES*

    * ``tools`` (dict): The key is the tool name and the value is
      a dictionary specifying the tool:

    ================  ====================================
    Key               Value
    ================  ====================================
    C                 Diameter of the tool
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

        ## IN|MM -> Units are inherited from Geometry
        #self.units = units

        # Trailing "T" or leading "L" (default)
        #self.zeros = "T"
        self.zeros = zeros or self.defaults["zeros"]
        self.zeros_found = self.zeros
        self.units_found = self.units

        # Excellon format
        self.excellon_format_upper_in = excellon_format_upper_in or self.defaults["excellon_format_upper_in"]
        self.excellon_format_lower_in = excellon_format_lower_in or self.defaults["excellon_format_lower_in"]
        self.excellon_format_upper_mm = excellon_format_upper_mm or self.defaults["excellon_format_upper_mm"]
        self.excellon_format_lower_mm = excellon_format_lower_mm or self.defaults["excellon_format_lower_mm"]
        self.excellon_units = excellon_units or self.defaults["excellon_units"]

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from Geometry.
        self.ser_attrs += ['tools', 'drills', 'zeros', 'excellon_format_upper_mm', 'excellon_format_lower_mm',
                           'excellon_format_upper_in', 'excellon_format_lower_in', 'excellon_units', 'slots',
                           'source_file']

        #### Patterns ####
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

        # Number format and units
        # INCH uses 6 digits
        # METRIC uses 5/6
        self.units_re = re.compile(r'^(INCH|METRIC)(?:,([TL])Z)?.*$')

        # Tool definition/parameters (?= is look-ahead
        # NOTE: This might be an overkill!
        # self.toolset_re = re.compile(r'^T(0?\d|\d\d)(?=.*C(\d*\.?\d*))?' +
        #                              r'(?=.*F(\d*\.?\d*))?(?=.*S(\d*\.?\d*))?' +
        #                              r'(?=.*B(\d*\.?\d*))?(?=.*H(\d*\.?\d*))?' +
        #                              r'(?=.*Z([-\+]?\d*\.?\d*))?[CFSBHT]')
        self.toolset_re = re.compile(r'^T(\d+)(?=.*C(\d*\.?\d*))?' +
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
        self.toolset_hl_re = re.compile(r'^T(\d+)(?=.*C(\d*\.?\d*))')

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

        # Parse coordinates
        self.leadingzeros_re = re.compile(r'^[-\+]?(0*)(\d*)')

        # Repeating command
        self.repeat_re = re.compile(r'R(\d+)')

    def parse_file(self, filename):
        """
        Reads the specified file as array of lines as
        passes it to ``parse_lines()``.

        :param filename: The file to be read and parsed.
        :type filename: str
        :return: None
        """
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

        #### Parsing starts here ####
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
                    self.app.inform.emit('[ERROR_NOTCL] This is GCODE mark: %s' % eline)
                    return

                # Header Begin (M48) #
                if self.hbegin_re.search(eline):
                    in_header = True
                    log.warning("Found start of the header: %s" % eline)
                    continue

                # Allegro Header Begin (;HEADER) #
                if self.allegro_hbegin_re.search(eline):
                    in_header = True
                    allegro_warning = True
                    log.warning("Found ALLEGRO start of the header: %s" % eline)
                    continue

                # Header End #
                # Since there might be comments in the header that include char % or M95
                # we ignore the lines starting with ';' which show they are comments
                if self.comm_re.search(eline):
                    match = self.tool_units_re.search(eline)
                    if match:
                        if line_units_found is False:
                            line_units_found = True
                            line_units = match.group(3)
                            self.convert_units({"MILS": "IN", "MM": "MM"}[line_units])
                            log.warning("Type of Allegro UNITS found inline: %s" % line_units)

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
                    else:
                        log.warning("Line ignored, it's a comment: %s" % eline)

                else:
                    if self.hend_re.search(eline):
                        if in_header is False:
                            log.warning("Found end of the header but there is no header: %s" % eline)
                            log.warning("The only useful data in header are tools, units and format.")
                            log.warning("Therefore we will create units and format based on defaults.")
                            headerless = True
                            try:
                                self.convert_units({"INCH": "IN", "METRIC": "MM"}[self.excellon_units])
                                print("Units converted .............................. %s" % self.excellon_units)
                            except Exception as e:
                                log.warning("Units could not be converted: %s" % str(e))

                        in_header = False
                        # for Allegro type of Excellons we reset name_tool variable so we can reuse it for toolchange
                        if allegro_warning is True:
                            name_tool = 0
                        log.warning("Found end of the header: %s" % eline)
                        continue

                ## Alternative units format M71/M72
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

                #### Body ####
                if not in_header:

                    ## Tool change ##
                    match = self.toolsel_re.search(eline)
                    if match:
                        current_tool = str(int(match.group(1)))
                        log.debug("Tool change: %s" % current_tool)
                        if headerless is True:
                            match = self.toolset_hl_re.search(eline)
                            if match:
                                name = str(int(match.group(1)))
                                spec = {
                                    "C": float(match.group(2)),
                                }
                                spec['solid_geometry'] = []
                                self.tools[name] = spec
                                log.debug("  Tool definition out of header: %s %s" % (name, spec))

                        continue

                    ## Allegro Type Tool change ##
                    if allegro_warning is True:
                        match = self.absinc_re.search(eline)
                        match1 = self.stop_re.search(eline)
                        if match or match1:
                            name_tool += 1
                            current_tool = str(name_tool)
                            log.debug(" Tool change for Allegro type of Excellon: %s" % current_tool)
                            continue

                    ## Slots parsing for drilled slots (contain G85)
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

                        # Slot coordinates without period ##
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
                            except:
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

                        # Slot coordinates with period: Use literally. ##
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
                            except:
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

                    ## Coordinates without period ##
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

                        ## Excellon Routing parse
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

                    ## Coordinates with period: Use literally. ##
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

                        ## Excellon Routing parse
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

                #### Header ####
                if in_header:

                    ## Tool definitions ##
                    match = self.toolset_re.search(eline)
                    if match:

                        name = str(int(match.group(1)))
                        spec = {
                            "C": float(match.group(2)),
                            # "F": float(match.group(3)),
                            # "S": float(match.group(4)),
                            # "B": float(match.group(5)),
                            # "H": float(match.group(6)),
                            # "Z": float(match.group(7))
                        }
                        spec['solid_geometry'] = []
                        self.tools[name] = spec
                        log.debug("  Tool definition: %s %s" % (name, spec))
                        continue

                    ## Units and number format ##
                    match = self.units_re.match(eline)
                    if match:
                        self.units_found = match.group(1)
                        self.zeros = match.group(2)  # "T" or "L". Might be empty

                        # self.units = {"INCH": "IN", "METRIC": "MM"}[match.group(1)]

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

                ## Units and number format outside header##
                match = self.units_re.match(eline)
                if match:
                    self.units_found = match.group(1)
                    self.zeros = match.group(2)  # "T" or "L". Might be empty

                    # self.units = {"INCH": "IN", "METRIC": "MM"}[match.group(1)]

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
            msg = "[ERROR_NOTCL] An internal error has ocurred. See shell.\n"
            msg += '[ERROR] Excellon Parser error.\nParsing Failed. Line %d: %s\n' % (line_num, eline)
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
            if self.zeros == "L" or self.zeros == "LZ":
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
                ## flatCAM expects 6digits
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
                self.tools[tool]['solid_geometry'][:] = []

            for drill in self.drills:
                # poly = drill['point'].buffer(self.tools[drill['tool']]["C"]/2.0)
                if drill['tool'] is '':
                    self.app.inform.emit("[WARNING] Excellon.create_geometry() -> a drill location was skipped "
                                         "due of not having a tool associated.\n"
                                         "Check the resulting GCode.")
                    log.debug("Excellon.create_geometry() -> a drill location was skipped "
                              "due of not having a tool associated")
                    continue
                tooldia = self.tools[drill['tool']]['C']
                poly = drill['point'].buffer(tooldia / 2.0, int(int(self.geo_steps_per_circle) / 4))
                # self.solid_geometry.append(poly)
                self.tools[drill['tool']]['solid_geometry'].append(poly)

            for slot in self.slots:
                slot_tooldia = self.tools[slot['tool']]['C']
                start = slot['start']
                stop = slot['stop']

                lines_string = LineString([start, stop])
                poly = lines_string.buffer(slot_tooldia / 2.0, int(int(self.geo_steps_per_circle) / 4))
                # self.solid_geometry.append(poly)
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

        log.debug("Excellon() -> bounds()")
        # if self.solid_geometry is None:
        #     log.debug("solid_geometry is None")
        #     return 0, 0, 0, 0

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
        if yfactor is None:
            yfactor = xfactor

        if point is None:
            px = 0
            py = 0
        else:
            px, py = point

        # Drills
        for drill in self.drills:
            drill['point'] = affinity.scale(drill['point'], xfactor, yfactor, origin=(px, py))

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

        dx, dy = vect

        # Drills
        for drill in self.drills:
            drill['point'] = affinity.translate(drill['point'], xoff=dx, yoff=dy)

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
        px, py = point
        xscale, yscale = {"X": (1.0, -1.0), "Y": (-1.0, 1.0)}[axis]

        # Modify data
        # Drills
        for drill in self.drills:
            drill['point'] = affinity.scale(drill['point'], xscale, yscale, origin=(px, py))

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
        if angle_x is None:
            angle_x = 0.0

        if angle_y is None:
            angle_y = 0.0

        if point is None:
            # Drills
            for drill in self.drills:
                drill['point'] = affinity.skew(drill['point'], angle_x, angle_y,
                                               origin=(0, 0))

            # Slots
            for slot in self.slots:
                slot['stop'] = affinity.skew(slot['stop'], angle_x, angle_y, origin=(0, 0))
                slot['start'] = affinity.skew(slot['start'], angle_x, angle_y, origin=(0, 0))
        else:
            px, py = point
            # Drills
            for drill in self.drills:
                drill['point'] = affinity.skew(drill['point'], angle_x, angle_y,
                                               origin=(px, py))

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
        if point is None:
            # Drills
            for drill in self.drills:
                drill['point'] = affinity.rotate(drill['point'], angle, origin='center')

            # Slots
            for slot in self.slots:
                slot['stop'] = affinity.rotate(slot['stop'], angle, origin='center')
                slot['start'] = affinity.rotate(slot['start'], angle, origin='center')
        else:
            px, py = point
            # Drills
            for drill in self.drills:
                drill['point'] = affinity.rotate(drill['point'], angle, origin=(px, py))

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
        "steps_per_circle": 64
    }

    def __init__(self,
                 units="in", kind="generic", tooldia=0.0,
                 z_cut=-0.002, z_move=0.1,
                 feedrate=3.0, feedrate_z=3.0, feedrate_rapid=3.0, feedrate_probe=3.0,
                 pp_geometry_name='default', pp_excellon_name='default',
                 depthpercut=0.1,z_pdepth=-0.02,
                 spindlespeed=None, dwell=True, dwelltime=1000,
                 toolchangez=0.787402, toolchange_xy=[0.0, 0.0],
                 endz=2.0,
                 segx=None,
                 segy=None,
                 steps_per_circle=None):

        # Used when parsing G-code arcs
        if steps_per_circle is None:
            steps_per_circle = int(CNCjob.defaults["steps_per_circle"])
        self.steps_per_circle = int(steps_per_circle)

        Geometry.__init__(self, geo_steps_per_circle=int(steps_per_circle))

        self.kind = kind
        self.units = units

        self.z_cut = z_cut
        self.tool_offset = {}

        self.z_move = z_move

        self.feedrate = feedrate
        self.feedrate_z = feedrate_z
        self.feedrate_rapid = feedrate_rapid

        self.tooldia = tooldia
        self.toolchangez = toolchangez
        self.toolchange_xy = toolchange_xy
        self.toolchange_xy_type = None

        self.endz = endz
        self.depthpercut = depthpercut

        self.unitcode = {"IN": "G20", "MM": "G21"}

        self.feedminutecode = "G94"
        self.absolutecode = "G90"

        self.gcode = ""
        self.gcode_parsed = None

        self.pp_geometry_name = pp_geometry_name
        self.pp_geometry = self.app.postprocessors[self.pp_geometry_name]

        self.pp_excellon_name = pp_excellon_name
        self.pp_excellon = self.app.postprocessors[self.pp_excellon_name]

        # Controls if the move from Z_Toolchange to Z_Move is done fast with G0 or normally with G1
        self.f_plunge = None

        # Controls if the move from Z_Cutto Z_Move is done fast with G0 or G1 until zero and then G0 to Z_move
        self.f_retract = None

        # how much depth the probe can probe before error
        self.z_pdepth = z_pdepth if z_pdepth else None

        # the feedrate(speed) with which the probel travel while probing
        self.feedrate_probe = feedrate_probe if feedrate_probe else None

        self.spindlespeed = spindlespeed
        self.dwell = dwell
        self.dwelltime = dwelltime

        self.segx = float(segx) if segx is not None else 0.0
        self.segy = float(segy) if segy is not None else 0.0

        self.input_geometry_bounds = None

        self.oldx = None
        self.oldy = None

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from Geometry.
        self.ser_attrs += ['kind', 'z_cut', 'z_move', 'toolchangez', 'feedrate', 'feedrate_z', 'feedrate_rapid',
                           'tooldia', 'gcode', 'input_geometry_bounds', 'gcode_parsed', 'steps_per_circle',
                           'depthpercut', 'spindlespeed', 'dwell', 'dwelltime']

    @property
    def postdata(self):
        return self.__dict__

    def convert_units(self, units):
        factor = Geometry.convert_units(self, units)
        log.debug("CNCjob.convert_units()")

        self.z_cut = float(self.z_cut) * factor
        self.z_move *= factor
        self.feedrate *= factor
        self.feedrate_z *= factor
        self.feedrate_rapid *= factor
        self.tooldia *= factor
        self.toolchangez *= factor
        self.endz *= factor
        self.depthpercut = float(self.depthpercut) * factor

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
        if drillz > 0:
            self.app.inform.emit("[WARNING] The Cut Z parameter has positive value. "
                                 "It is the depth value to drill into material.\n"
                                 "The Cut Z parameter needs to have a negative value, assuming it is a typo "
                                 "therefore the app will convert the value to negative. "
                                 "Check the resulting CNC code (Gcode etc).")
            self.z_cut = -drillz
        elif drillz == 0:
            self.app.inform.emit("[WARNING] The Cut Z parameter is zero. "
                                 "There will be no cut, skipping %s file" % exobj.options['name'])
            return 'fail'
        else:
            self.z_cut = drillz

        self.toolchangez = toolchangez

        try:
            if toolchangexy == '':
                self.toolchange_xy = None
            else:
                self.toolchange_xy = [float(eval(a)) for a in toolchangexy.split(",")]
                if len(self.toolchange_xy) < 2:
                    self.app.inform.emit("[ERROR]The Toolchange X,Y field in Edit -> Preferences has to be "
                                         "in the format (x, y) \nbut now there is only one value, not two. ")
                    return 'fail'
        except Exception as e:
            log.debug("camlib.CNCJob.generate_from_excellon_by_tool() --> %s" % str(e))
            pass

        self.startz = startz
        self.endz = endz

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
            if self.toolchange_xy is not None:
                gcode += self.doformat(p.lift_code, x=self.toolchange_xy[0], y=self.toolchange_xy[1])
                gcode += self.doformat(p.startz_code, x=self.toolchange_xy[0], y=self.toolchange_xy[1])
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

            def Distance(self, from_node, to_node):
                return int(self.matrix[from_node][to_node])

        # Create the data.
        def create_data_array():
            locations = []
            for point in points[tool]:
                locations.append((point.coords.xy[0][0], point.coords.xy[1][0]))
            return locations

        if self.toolchange_xy is not None:
            self.oldx = self.toolchange_xy[0]
            self.oldy = self.toolchange_xy[1]
        else:
            self.oldx = 0.0
            self.oldy = 0.0

        measured_distance = 0

        current_platform = platform.architecture()[0]
        if current_platform == '64bit':
            if excellon_optimization_type == 'M':
                log.debug("Using OR-Tools Metaheuristic Guided Local Search drill path optimization.")
                if exobj.drills:
                    for tool in tools:
                        self.tool=tool
                        self.postdata['toolC']=exobj.tools[tool]["C"]

                        ################################################
                        # Create the data.
                        node_list = []
                        locations = create_data_array()
                        tsp_size = len(locations)
                        num_routes = 1  # The number of routes, which is 1 in the TSP.
                        # Nodes are indexed from 0 to tsp_size - 1. The depot is the starting node of the route.
                        depot = 0
                        # Create routing model.
                        if tsp_size > 0:
                            routing = pywrapcp.RoutingModel(tsp_size, num_routes, depot)
                            search_parameters = pywrapcp.RoutingModel.DefaultSearchParameters()
                            search_parameters.local_search_metaheuristic = (
                                routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)

                            # Set search time limit in milliseconds.
                            if float(self.app.defaults["excellon_search_time"]) != 0:
                                search_parameters.time_limit_ms = int(
                                    float(self.app.defaults["excellon_search_time"]) * 1000)
                            else:
                                search_parameters.time_limit_ms = 3000

                            # Callback to the distance function. The callback takes two
                            # arguments (the from and to node indices) and returns the distance between them.
                            dist_between_locations = CreateDistanceCallback()
                            dist_callback = dist_between_locations.Distance
                            routing.SetArcCostEvaluatorOfAllVehicles(dist_callback)

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
                        ################################################

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
                                current_tooldia = float('%.3f' % float(exobj.tools[tool]["C"]))
                            z_offset = float(self.tool_offset[current_tooldia]) * (-1)
                            self.z_cut += z_offset

                            # Drillling!
                            for k in node_list:
                                locx = locations[k][0]
                                locy = locations[k][1]

                                gcode += self.doformat(p.rapid_code, x=locx, y=locy)
                                gcode += self.doformat(p.down_code, x=locx, y=locy)
                                if self.f_retract is False:
                                    gcode += self.doformat(p.up_to_zero_code, x=locx, y=locy)
                                gcode += self.doformat(p.lift_code, x=locx, y=locy)
                                measured_distance += abs(distance_euclidian(locx, locy, self.oldx, self.oldy))
                                self.oldx = locx
                                self.oldy = locy
                else:
                    log.debug("camlib.CNCJob.generate_from_excellon_by_tool() --> "
                              "The loaded Excellon file has no drills ...")
                    self.app.inform.emit('[ERROR_NOTCL]The loaded Excellon file has no drills ...')
                    return 'fail'

                log.debug("The total travel distance with OR-TOOLS Metaheuristics is: %s" % str(measured_distance))
            elif excellon_optimization_type == 'B':
                log.debug("Using OR-Tools Basic drill path optimization.")
                if exobj.drills:
                    for tool in tools:
                        self.tool=tool
                        self.postdata['toolC']=exobj.tools[tool]["C"]

                        ################################################
                        node_list = []
                        locations = create_data_array()
                        tsp_size = len(locations)
                        num_routes = 1  # The number of routes, which is 1 in the TSP.

                        # Nodes are indexed from 0 to tsp_size - 1. The depot is the starting node of the route.
                        depot = 0

                        # Create routing model.
                        if tsp_size > 0:
                            routing = pywrapcp.RoutingModel(tsp_size, num_routes, depot)
                            search_parameters = pywrapcp.RoutingModel.DefaultSearchParameters()

                            # Callback to the distance function. The callback takes two
                            # arguments (the from and to node indices) and returns the distance between them.
                            dist_between_locations = CreateDistanceCallback()
                            dist_callback = dist_between_locations.Distance
                            routing.SetArcCostEvaluatorOfAllVehicles(dist_callback)

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
                        ################################################

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
                                current_tooldia = float('%.3f' % float(exobj.tools[tool]["C"]))

                            z_offset = float(self.tool_offset[current_tooldia]) * (-1)
                            self.z_cut += z_offset

                            # Drillling!
                            for k in node_list:
                                locx = locations[k][0]
                                locy = locations[k][1]
                                gcode += self.doformat(p.rapid_code, x=locx, y=locy)
                                gcode += self.doformat(p.down_code, x=locx, y=locy)
                                if self.f_retract is False:
                                    gcode += self.doformat(p.up_to_zero_code, x=locx, y=locy)
                                gcode += self.doformat(p.lift_code, x=locx, y=locy)
                                measured_distance += abs(distance_euclidian(locx, locy, self.oldx, self.oldy))
                                self.oldx = locx
                                self.oldy = locy
                else:
                    log.debug("camlib.CNCJob.generate_from_excellon_by_tool() --> "
                              "The loaded Excellon file has no drills ...")
                    self.app.inform.emit('[ERROR_NOTCL]The loaded Excellon file has no drills ...')
                    return 'fail'

                log.debug("The total travel distance with OR-TOOLS Basic Algorithm is: %s" % str(measured_distance))
            else:
                self.app.inform.emit("[ERROR_NOTCL] Wrong optimization type selected.")
                return 'fail'
        else:
            log.debug("Using Travelling Salesman drill path optimization.")
            for tool in tools:
                if exobj.drills:
                    self.tool = tool
                    self.postdata['toolC'] = exobj.tools[tool]["C"]

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
                            current_tooldia = float('%.3f' % float(exobj.tools[tool]["C"]))
                        z_offset = float(self.tool_offset[current_tooldia]) * (-1)
                        self.z_cut += z_offset
                        # Drillling!
                        altPoints = []
                        for point in points[tool]:
                            altPoints.append((point.coords.xy[0][0], point.coords.xy[1][0]))

                        for point in self.optimized_travelling_salesman(altPoints):
                            gcode += self.doformat(p.rapid_code, x=point[0], y=point[1])
                            gcode += self.doformat(p.down_code, x=point[0], y=point[1])
                            if self.f_retract is False:
                                gcode += self.doformat(p.up_to_zero_code, x=point[0], y=point[1])
                            gcode += self.doformat(p.lift_code, x=point[0], y=point[1])
                            measured_distance += abs(distance_euclidian(point[0], point[1], self.oldx, self.oldy))
                            self.oldx = point[0]
                            self.oldy = point[1]
                    else:
                        log.debug("camlib.CNCJob.generate_from_excellon_by_tool() --> "
                                  "The loaded Excellon file has no drills ...")
                        self.app.inform.emit('[ERROR_NOTCL]The loaded Excellon file has no drills ...')
                        return 'fail'
            log.debug("The total travel distance with Travelling Salesman Algorithm is: %s" % str(measured_distance))

        gcode += self.doformat(p.spindle_stop_code)  # Spindle stop
        gcode += self.doformat(p.end_code, x=0, y=0)

        measured_distance += abs(distance_euclidian(self.oldx, self.oldy, 0, 0))
        log.debug("The total travel distance including travel to end position is: %s" %
                  str(measured_distance) + '\n')
        self.travel_distance = measured_distance

        self.gcode = gcode
        return 'OK'

    def generate_from_multitool_geometry(self, geometry, append=True,
                                         tooldia=None, offset=0.0, tolerance=0, z_cut=1.0, z_move=2.0,
                                         feedrate=2.0, feedrate_z=2.0, feedrate_rapid=30,
                                         spindlespeed=None, dwell=False, dwelltime=1.0,
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

        ## Flatten the geometry. Only linear elements (no polygons) remain.
        flat_geometry = self.flatten(temp_solid_geometry, pathonly=True)
        log.debug("%d paths" % len(flat_geometry))

        self.tooldia = float(tooldia) if tooldia else None
        self.z_cut = float(z_cut) if z_cut else None
        self.z_move = float(z_move) if z_move else None

        self.feedrate = float(feedrate) if feedrate else None
        self.feedrate_z = float(feedrate_z) if feedrate_z else None
        self.feedrate_rapid = float(feedrate_rapid) if feedrate_rapid else None

        self.spindlespeed = int(spindlespeed) if spindlespeed else None
        self.dwell = dwell
        self.dwelltime = float(dwelltime) if dwelltime else None

        self.startz = float(startz) if startz else None
        self.endz = float(endz) if endz else None

        self.depthpercut = float(depthpercut) if depthpercut else None
        self.multidepth = multidepth

        self.toolchangez = float(toolchangez) if toolchangez else None

        try:
            if toolchangexy == '':
                self.toolchange_xy = None
            else:
                self.toolchange_xy = [float(eval(a)) for a in toolchangexy.split(",")]
                if len(self.toolchange_xy) < 2:
                    self.app.inform.emit("[ERROR]The Toolchange X,Y field in Edit -> Preferences has to be "
                                         "in the format (x, y) \nbut now there is only one value, not two. ")
                    return 'fail'
        except Exception as e:
            log.debug("camlib.CNCJob.generate_from_multitool_geometry() --> %s" % str(e))
            pass

        self.pp_geometry_name = pp_geometry_name if pp_geometry_name else 'default'
        self.f_plunge = self.app.defaults["geometry_f_plunge"]

        if self.z_cut > 0:
            self.app.inform.emit("[WARNING] The Cut Z parameter has positive value. "
                                 "It is the depth value to cut into material.\n"
                                 "The Cut Z parameter needs to have a negative value, assuming it is a typo "
                                 "therefore the app will convert the value to negative."
                                 "Check the resulting CNC code (Gcode etc).")
            self.z_cut = -self.z_cut
        elif self.z_cut == 0:
            self.app.inform.emit("[WARNING] The Cut Z parameter is zero. "
                                 "There will be no cut, skipping %s file" % self.options['name'])

        ## Index first and last points in paths
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
            #     self.gcode += self.doformat(p.toolchange_code, x=self.toolchange_xy[0], y=self.toolchange_xy[1])
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

        ## Iterate over geometry paths getting the nearest each time.
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

                #---------- Single depth/pass --------
                if not multidepth:
                    self.gcode += self.create_gcode_single_pass(geo, extracut, tolerance)

                #--------- Multi-pass ---------
                else:
                    self.gcode += self.create_gcode_multi_pass(geo, extracut, tolerance,
                                                               postproc=p, current_point=current_pt)

                current_pt = geo.coords[-1]
                pt, geo = storage.nearest(current_pt) # Next

        except StopIteration:  # Nothing found in storage.
            pass

        log.debug("Finishing G-Code... %s paths traced." % path_count)

        # Finish
        self.gcode += self.doformat(p.spindle_stop_code)
        self.gcode += self.doformat(p.lift_code, x=current_pt[0], y=current_pt[1])
        self.gcode += self.doformat(p.end_code, x=0, y=0)

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

        ## Index first and last points in paths
        # What points to index.
        def get_pts(o):
            return [o.coords[0], o.coords[-1]]

        self.gcode = ""

        if not kwargs:
            log.debug("camlib.generate_from_solderpaste_geo() --> No tool in the solderpaste geometry.")
            self.app.inform.emit("[ERROR_NOTCL] There is no tool data in the SolderPaste geometry.")


        # this is the tool diameter, it is used as such to accommodate the postprocessor who need the tool diameter
        # given under the name 'toolC'

        self.postdata['toolC'] = kwargs['tooldia']

        # Initial G-Code
        pp_solderpaste_name = kwargs['data']['tools_solderpaste_pp'] if kwargs['data']['tools_solderpaste_pp'] else \
            self.app.defaults['tools_solderpaste_pp']
        p = self.app.postprocessors[pp_solderpaste_name]

        self.gcode = self.doformat(p.start_code)

        ## Flatten the geometry. Only linear elements (no polygons) remain.
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

        # kwargs length will tell actually the number of tools used so if we have more than one tools then
        # we have toolchange event
        if len(kwargs) > 1:
            self.gcode += self.doformat(p.toolchange_code)
        else:
            self.gcode += self.doformat(p.lift_code, x=0, y=0)  # Move (up) to travel height

        ## Iterate over geometry paths getting the nearest each time.
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

                self.gcode += self.create_soldepaste_gcode(geo, p=p)
                current_pt = geo.coords[-1]
                pt, geo = storage.nearest(current_pt)  # Next

        except StopIteration:  # Nothing found in storage.
            pass

        log.debug("Finishing SolderPste G-Code... %s paths traced." % path_count)

        # Finish
        self.gcode += self.doformat(p.lift_code)
        self.gcode += self.doformat(p.end_code)

        return self.gcode


    def generate_from_geometry_2(self, geometry, append=True,
                                 tooldia=None, offset=0.0, tolerance=0,
                                 z_cut=1.0, z_move=2.0,
                                 feedrate=2.0, feedrate_z=2.0, feedrate_rapid=30,
                                 spindlespeed=None, dwell=False, dwelltime=1.0,
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
            self.app.inform.emit("[ERROR]Expected a Geometry, got %s" % type(geometry))
            return 'fail'
        log.debug("Generate_from_geometry_2()")

        # if solid_geometry is empty raise an exception
        if not geometry.solid_geometry:
            self.app.inform.emit("[ERROR_NOTCL]Trying to generate a CNC Job "
                                 "from a Geometry object without solid_geometry.")

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

            if offset <0:
                a, b, c, d = bounds_rec(geometry.solid_geometry)
                # if the offset is less than half of the total length or less than half of the total width of the
                # solid geometry it's obvious we can't do the offset
                if -offset > ((c - a) / 2) or -offset > ((d - b) / 2):
                    self.app.inform.emit("[ERROR_NOTCL]The Tool Offset value is too negative to use "
                                         "for the current_geometry.\n"
                                         "Raise the value (in module) and try again.")
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

        ## Flatten the geometry. Only linear elements (no polygons) remain.
        flat_geometry = self.flatten(temp_solid_geometry, pathonly=True)
        log.debug("%d paths" % len(flat_geometry))

        self.tooldia = float(tooldia) if tooldia else None

        self.z_cut = float(z_cut) if z_cut else None

        self.z_move = float(z_move) if z_move else None

        self.feedrate = float(feedrate) if feedrate else None

        self.feedrate_z = float(feedrate_z) if feedrate_z else None

        self.feedrate_rapid = float(feedrate_rapid) if feedrate_rapid else None

        self.spindlespeed = int(spindlespeed) if spindlespeed else None

        self.dwell = dwell

        self.dwelltime = float(dwelltime) if dwelltime else None

        self.startz = float(startz) if startz else None

        self.endz = float(endz) if endz else None

        self.depthpercut = float(depthpercut) if depthpercut else None

        self.multidepth = multidepth

        self.toolchangez = float(toolchangez) if toolchangez else None

        try:
            if toolchangexy == '':
                self.toolchange_xy = None
            else:
                self.toolchange_xy = [float(eval(a)) for a in toolchangexy.split(",")]
                if len(self.toolchange_xy) < 2:
                    self.app.inform.emit("[ERROR]The Toolchange X,Y field in Edit -> Preferences has to be "
                                         "in the format (x, y) \nbut now there is only one value, not two. ")
                    return 'fail'
        except Exception as e:
            log.debug("camlib.CNCJob.generate_from_geometry_2() --> %s" % str(e))
            pass

        self.pp_geometry_name = pp_geometry_name if pp_geometry_name else 'default'
        self.f_plunge = self.app.defaults["geometry_f_plunge"]

        if self.z_cut > 0:
            self.app.inform.emit("[WARNING] The Cut Z parameter has positive value. "
                                 "It is the depth value to cut into material.\n"
                                 "The Cut Z parameter needs to have a negative value, assuming it is a typo "
                                 "therefore the app will convert the value to negative."
                                 "Check the resulting CNC code (Gcode etc).")
            self.z_cut = -self.z_cut
        elif self.z_cut == 0:
            self.app.inform.emit("[WARNING] The Cut Z parameter is zero. "
                                 "There will be no cut, skipping %s file" % geometry.options['name'])

        ## Index first and last points in paths
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

        self.oldx = 0.0
        self.oldy = 0.0

        self.gcode = self.doformat(p.start_code)

        self.gcode += self.doformat(p.feedrate_code)        # sets the feed rate

        if toolchange is False:
            self.gcode += self.doformat(p.lift_code, x=self.oldx , y=self.oldy )  # Move (up) to travel height
            self.gcode += self.doformat(p.startz_code, x=self.oldx , y=self.oldy )

        if toolchange:
            # if "line_xyz" in self.pp_geometry_name:
            #     self.gcode += self.doformat(p.toolchange_code, x=self.toolchange_xy[0], y=self.toolchange_xy[1])
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

        ## Iterate over geometry paths getting the nearest each time.
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

                #---------- Single depth/pass --------
                if not multidepth:
                    self.gcode += self.create_gcode_single_pass(geo, extracut, tolerance)

                #--------- Multi-pass ---------
                else:
                    self.gcode += self.create_gcode_multi_pass(geo, extracut, tolerance,
                                                               postproc=p, current_point=current_pt)

                current_pt = geo.coords[-1]
                pt, geo = storage.nearest(current_pt) # Next

        except StopIteration:  # Nothing found in storage.
            pass

        log.debug("Finishing G-Code... %s paths traced." % path_count)

        # Finish
        self.gcode += self.doformat(p.spindle_stop_code)
        self.gcode += self.doformat(p.lift_code, x=current_pt[0], y=current_pt[1])
        self.gcode += self.doformat(p.end_code, x=0, y=0)

        return self.gcode

    def create_soldepaste_gcode(self, geometry, p):
        gcode = ''
        path = self.segment(geometry.coords)

        if type(geometry) == LineString or type(geometry) == LinearRing:
            # Move fast to 1st point
            gcode += self.doformat(p.rapid_code)  # Move to first point

            # Move down to cutting depth
            gcode += self.doformat(p.feedrate_z_code)
            gcode += self.doformat(p.down_z_start_code)
            gcode += self.doformat(p.spindle_on_fwd_code) # Start dispensing
            gcode += self.doformat(p.feedrate_xy_code)

            # Cutting...
            for pt in path[1:]:
                gcode += self.doformat(p.linear_code)  # Linear motion to point

            # Up to travelling height.
            gcode += self.doformat(p.spindle_off_code) # Stop dispensing
            gcode += self.doformat(p.spindle_on_rev_code)
            gcode += self.doformat(p.down_z_stop_code)
            gcode += self.doformat(p.spindle_off_code)
            gcode += self.doformat(p.lift_code)
        elif type(geometry) == Point:
            gcode += self.doformat(p.linear_code)  # Move to first point

            gcode += self.doformat(p.feedrate_z_code)
            gcode += self.doformat(p.down_z_start_code)
            gcode += self.doformat(p.spindle_on_fwd_code) # Start dispensing
            # TODO A dwell time for dispensing?
            gcode += self.doformat(p.spindle_off_code)  # Stop dispensing
            gcode += self.doformat(p.spindle_on_rev_code)
            gcode += self.doformat(p.down_z_stop_code)
            gcode += self.doformat(p.spindle_off_code)
            gcode += self.doformat(p.lift_code)
        return gcode

    def create_gcode_single_pass(self, geometry, extracut, tolerance):
        # G-code. Note: self.linear2gcode() and self.point2gcode() will lower and raise the tool every time.
        gcode_single_pass = ''

        if type(geometry) == LineString or type(geometry) == LinearRing:
            if extracut is False:
                gcode_single_pass = self.linear2gcode(geometry, tolerance=tolerance)
            else:
                if geometry.is_ring:
                    gcode_single_pass = self.linear2gcode_extra(geometry, tolerance=tolerance)
                else:
                    gcode_single_pass = self.linear2gcode(geometry, tolerance=tolerance)
        elif type(geometry) == Point:
            gcode_single_pass = self.point2gcode(geometry)
        else:
            log.warning("G-code generation not implemented for %s" % (str(type(geometry))))
            return

        return gcode_single_pass

    def create_gcode_multi_pass(self, geometry, extracut, tolerance, postproc, current_point):

        gcode_multi_pass = ''

        if isinstance(self.z_cut, Decimal):
            z_cut = self.z_cut
        else:
            z_cut = Decimal(self.z_cut).quantize(Decimal('0.000000001'))

        if self.depthpercut is None:
            self.depthpercut = z_cut
        elif not isinstance(self.depthpercut, Decimal):
            self.depthpercut = Decimal(self.depthpercut).quantize(Decimal('0.000000001'))

        depth = 0
        reverse = False
        while depth > z_cut:

            # Increase depth. Limit to z_cut.
            depth -= self.depthpercut
            if depth < z_cut:
                depth = z_cut

            # Cut at specific depth and do not lift the tool.
            # Note: linear2gcode() will use G00 to move to the first point in the path, but it should be already
            # at the first point if the tool is down (in the material).  So, an extra G00 should show up but
            # is inconsequential.
            if type(geometry) == LineString or type(geometry) == LinearRing:
                if extracut is False:
                    gcode_multi_pass += self.linear2gcode(geometry, tolerance=tolerance, z_cut=depth, up=False)
                else:
                    if geometry.is_ring:
                        gcode_multi_pass += self.linear2gcode_extra(geometry, tolerance=tolerance, z_cut=depth, up=False)
                    else:
                        gcode_multi_pass += self.linear2gcode(geometry, tolerance=tolerance, z_cut=depth, up=False)

            # Ignore multi-pass for points.
            elif type(geometry) == Point:
                gcode_multi_pass += self.point2gcode(geometry)
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
        gcode_multi_pass += self.doformat(postproc.lift_code, x=current_point[0], y=current_point[1])
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

        elif 'grbl_laser' in self.pp_excellon_name or 'grbl_laser' in self.pp_geometry_name:
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
            if '%MO' in line or '%' in line:
                return "fail"

            gobj = self.codes_split(line)

            ## Units
            if 'G' in gobj and (gobj['G'] == 20.0 or gobj['G'] == 21.0):
                self.units = {20.0: "IN", 21.0: "MM"}[gobj['G']]
                continue

            ## Changing height
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

            if 'G' in gobj:
                current['G'] = int(gobj['G'])
                
            if 'X' in gobj or 'Y' in gobj:
                # TODO: I think there is a problem here, current['X] (and the rest of current[...] are not initialized
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
                    path += arc(center, radius, start, stop,
                                arcdir[current['G']],
                                int(self.steps_per_circle / 4))

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
        :return: None
        """

        gcode_parsed = gcode_parsed if gcode_parsed else self.gcode_parsed
        path_num = 0

        if tooldia is None:
            tooldia = self.tooldia

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
            for geo in gcode_parsed:
                path_num += 1

                text.append(str(path_num))
                pos.append(geo['geom'].coords[0])

                poly = geo['geom'].buffer(tooldia / 2.0).simplify(tool_tolerance)
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

            obj.annotation.set(text=text, pos=pos, visible=obj.options['plot'])

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
                     feedrate=None, feedrate_z=None, feedrate_rapid=None, cont=False):
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
            feedrate_z = self.feedrate_z

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

        # Move fast to 1st point
        if not cont:
            gcode += self.doformat(p.rapid_code, x=path[0][0], y=path[0][1])  # Move to first point

        # Move down to cutting depth
        if down:
            # Different feedrate for vertical cut?
            gcode += self.doformat(p.feedrate_z_code)
            # gcode += self.doformat(p.feedrate_code)
            gcode += self.doformat(p.down_code, x=path[0][0], y=path[0][1], z_cut=z_cut)
            gcode += self.doformat(p.feedrate_code, feedrate=feedrate)

        # Cutting...
        for pt in path[1:]:
            gcode += self.doformat(p.linear_code, x=pt[0], y=pt[1], z=z_cut)  # Linear motion to point

        # Up to travelling height.
        if up:
            gcode += self.doformat(p.lift_code, x=pt[0], y=pt[1], z_move=z_move)  # Stop cutting
        return gcode

    def linear2gcode_extra(self, linear, tolerance=0, down=True, up=True,
                     z_cut=None, z_move=None, zdownrate=None,
                     feedrate=None, feedrate_z=None, feedrate_rapid=None, cont=False):
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
            feedrate_z = self.feedrate_z

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

        # Move fast to 1st point
        if not cont:
            gcode += self.doformat(p.rapid_code, x=path[0][0], y=path[0][1])  # Move to first point

        # Move down to cutting depth
        if down:
            # Different feedrate for vertical cut?
            if self.feedrate_z is not None:
                gcode += self.doformat(p.feedrate_z_code)
                # gcode += self.doformat(p.feedrate_code)
                gcode += self.doformat(p.down_code, x=path[0][0], y=path[0][1], z_cut=z_cut)
                gcode += self.doformat(p.feedrate_code, feedrate=feedrate)
            else:
                gcode += self.doformat(p.down_code, x=path[0][0], y=path[0][1], z_cut=z_cut)  # Start cutting

        # Cutting...
        for pt in path[1:]:
            gcode += self.doformat(p.linear_code, x=pt[0], y=pt[1], z=z_cut)  # Linear motion to point

        # this line is added to create an extra cut over the first point in patch
        # to make sure that we remove the copper leftovers
        gcode += self.doformat(p.linear_code, x=path[1][0], y=path[1][1])    # Linear motion to the 1st point in the cut path

        # Up to travelling height.
        if up:
            gcode += self.doformat(p.lift_code, x=path[1][0], y=path[1][1], z_move=z_move)  # Stop cutting

        return gcode

    def point2gcode(self, point):
        gcode = ""

        path = list(point.coords)
        p = self.pp_geometry
        gcode += self.doformat(p.linear_code, x=path[0][0], y=path[0][1])  # Move to first point

        if self.feedrate_z is not None:
            gcode += self.doformat(p.feedrate_z_code)
            gcode += self.doformat(p.down_code, x=path[0][0], y=path[0][1], z_cut = self.z_cut)
            gcode += self.doformat(p.feedrate_code)
        else:
            gcode += self.doformat(p.down_code, x=path[0][0], y=path[0][1], z_cut = self.z_cut)  # Start cutting

        gcode += self.doformat(p.lift_code, x=path[0][0], y=path[0][1])  # Stop cutting
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
            units = self.app.general_options_form.general_app_group.units_radio.get_value().upper()

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
                g['geom'] = affinity.scale(g['geom'], xfactor, yfactor, origin=(px, py))
            self.create_geometry()
        else:
            for k, v in self.cnc_tools.items():
                # scale Gcode
                v['gcode'] = scale_g(v['gcode'])
                # scale gcode_parsed
                for g in v['gcode_parsed']:
                    g['geom'] = affinity.scale(g['geom'], xfactor, yfactor, origin=(px, py))
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
                g['geom'] = affinity.translate(g['geom'], xoff=dx, yoff=dy)
            self.create_geometry()
        else:
            for k, v in self.cnc_tools.items():
                # offset Gcode
                v['gcode'] = offset_g(v['gcode'])
                # offset gcode_parsed
                for g in v['gcode_parsed']:
                    g['geom'] = affinity.translate(g['geom'], xoff=dx, yoff=dy)
                v['solid_geometry'] = cascaded_union([geo['geom'] for geo in v['gcode_parsed']])

    def mirror(self, axis, point):
        """
        Mirror the geometrys of an object by an given axis around the coordinates of the 'point'
        :param angle:
        :param point: tupple of coordinates (x,y)
        :return:
        """
        px, py = point
        xscale, yscale = {"X": (1.0, -1.0), "Y": (-1.0, 1.0)}[axis]

        for g in self.gcode_parsed:
            g['geom'] = affinity.scale(g['geom'], xscale, yscale, origin=(px, py))

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
        px, py = point

        for g in self.gcode_parsed:
            g['geom'] = affinity.skew(g['geom'], angle_x, angle_y,
                                      origin=(px, py))

        self.create_geometry()

    def rotate(self, angle, point):
        """
        Rotate the geometrys of an object by an given angle around the coordinates of the 'point'
        :param angle:
        :param point: tupple of coordinates (x,y)
        :return:
        """

        px, py = point

        for g in self.gcode_parsed:
            g['geom'] = affinity.rotate(g['geom'], angle, origin=(px, py))

        self.create_geometry()

def get_bounds(geometry_list):
    xmin = Inf
    ymin = Inf
    xmax = -Inf
    ymax = -Inf

    #print "Getting bounds of:", str(geometry_set)
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
#         _ = iter(geo)
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
#             _ = iter(g)
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
    :param zeros: If 'L', leading zeros are removed and trailing zeros are kept. If 'T', is in reverse.
    :type zeros: str
    :return: The number in floating point.
    :rtype: float
    """
    if zeros == 'L':
        ret_val = int(strnumber) * (10 ** (-frac_digits))

    if zeros == 'T':
        int_val = int(strnumber)
        ret_val = (int_val * (10 ** ((int_digits + frac_digits) - len(strnumber)))) * (10 ** (-frac_digits))
    return ret_val


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
        _ = iter(obj)
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
    T = solve(transpose(array([-b1, b2])), a1 - a2)

    # Center
    center = a1 + b1 * T[0]

    # Radius
    radius = norm(center - p1)

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

        ## Track object-point relationship
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
            self.rti.delete(self.obj2points[objid][i], (pt[0], pt[1], pt[0], pt[1]))

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

    #@profile
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
