# ############################################################
# FlatCAM: 2D Post-processing for Manufacturing              #
# http://flatcam.org                                         #
# File Author: Marius Adrian Stanciu (c)                     #
# Date: 12/11/2019                                           #
# MIT Licence                                                #
# ############################################################

from camlib import Geometry, arc, arc_angle
import FlatCAMApp

import numpy as np
import re
import logging
import traceback
from copy import deepcopy
import sys

from shapely.ops import cascaded_union, unary_union
from shapely.geometry import Polygon, MultiPolygon, LineString, Point, MultiLineString
import shapely.affinity as affinity
from shapely.geometry import box as shply_box

import FlatCAMTranslation as fcTranslate
import gettext
import builtins

if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class HPGL2(Geometry):
    """
    HPGL2 parsing.
    """

    defaults = {
        "steps_per_circle": 64,
        "use_buffer_for_union": True
    }

    def __init__(self, steps_per_circle=None):
        """
        The constructor takes no parameters.

        :return: Geometry object
        :rtype: Geometry
        """

        # How to approximate a circle with lines.
        self.steps_per_circle = steps_per_circle if steps_per_circle is not None else \
            int(self.app.defaults["geometry_circle_steps"])

        self.decimals = self.app.decimals

        # Initialize parent
        Geometry.__init__(self, geo_steps_per_circle=self.steps_per_circle)

        # Number format
        self.coord_mm_factor = 0.040

        # store the file units here:
        self.units = 'MM'

        # storage for the tools
        self.tools = dict()

        self.default_data = dict()
        self.default_data.update({
            "name": '_ncc',
            "plot": self.app.defaults["geometry_plot"],
            "cutz": self.app.defaults["geometry_cutz"],
            "vtipdia": self.app.defaults["geometry_vtipdia"],
            "vtipangle": self.app.defaults["geometry_vtipangle"],
            "travelz": self.app.defaults["geometry_travelz"],
            "feedrate": self.app.defaults["geometry_feedrate"],
            "feedrate_z": self.app.defaults["geometry_feedrate_z"],
            "feedrate_rapid": self.app.defaults["geometry_feedrate_rapid"],
            "dwell": self.app.defaults["geometry_dwell"],
            "dwelltime": self.app.defaults["geometry_dwelltime"],
            "multidepth": self.app.defaults["geometry_multidepth"],
            "ppname_g": self.app.defaults["geometry_ppname_g"],
            "depthperpass": self.app.defaults["geometry_depthperpass"],
            "extracut": self.app.defaults["geometry_extracut"],
            "extracut_length": self.app.defaults["geometry_extracut_length"],
            "toolchange": self.app.defaults["geometry_toolchange"],
            "toolchangez": self.app.defaults["geometry_toolchangez"],
            "endz": self.app.defaults["geometry_endz"],
            "spindlespeed": self.app.defaults["geometry_spindlespeed"],
            "toolchangexy": self.app.defaults["geometry_toolchangexy"],
            "startz": self.app.defaults["geometry_startz"],

            "tooldia": self.app.defaults["tools_painttooldia"],
            "paintmargin": self.app.defaults["tools_paintmargin"],
            "paintmethod": self.app.defaults["tools_paintmethod"],
            "selectmethod": self.app.defaults["tools_selectmethod"],
            "pathconnect": self.app.defaults["tools_pathconnect"],
            "paintcontour": self.app.defaults["tools_paintcontour"],
            "paintoverlap": self.app.defaults["tools_paintoverlap"],

            "nccoverlap": self.app.defaults["tools_nccoverlap"],
            "nccmargin": self.app.defaults["tools_nccmargin"],
            "nccmethod": self.app.defaults["tools_nccmethod"],
            "nccconnect": self.app.defaults["tools_nccconnect"],
            "ncccontour": self.app.defaults["tools_ncccontour"],
            "nccrest": self.app.defaults["tools_nccrest"]
        })

        # flag to be set True when tool is detected
        self.tool_detected = False

        # will store the geometry's as solids
        self.solid_geometry = None

        # will store the geometry's as paths
        self.follow_geometry = []

        self.source_file = ''

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from Geometry.
        self.ser_attrs += ['solid_geometry', 'follow_geometry', 'source_file']

        # ### Parser patterns ## ##

        # comment
        self.comment_re = re.compile(r"^CO\s*[\"']([a-zA-Z0-9\s]*)[\"'];?$")
        # absolute move to x, y
        self.abs_move_re = re.compile(r"^PA\s*(-?\d+\.?\d+?),?\s*(-?\d+\.?\d+?)*;?$")
        # relative move to x, y
        self.rel_move_re = re.compile(r"^PR\s*(-?\d+\.\d+?),?\s*(-?\d+\.\d+?)*;?$")
        # pen position
        self.pen_re = re.compile(r"^(P[U|D]);?$")
        # Initialize
        self.initialize_re = re.compile(r'^(IN);?$')

        # select pen
        self.sp_re = re.compile(r'SP(\d);?$')

        self.fmt_re_alt = re.compile(r'%FS([LTD])?([AI])X(\d)(\d)Y\d\d\*MO(IN|MM)\*%$')
        self.fmt_re_orcad = re.compile(r'(G\d+)*\**%FS([LTD])?([AI]).*X(\d)(\d)Y\d\d\*%$')

        # G01... - Linear interpolation plus flashes with coordinates
        # Operation code (D0x) missing is deprecated... oh well I will support it.
        self.lin_re = re.compile(r'^(?:G0?(1))?(?=.*X([+-]?\d+))?(?=.*Y([+-]?\d+))?[XY][^DIJ]*(?:D0?([123]))?\*$')

        # G02/3... - Circular interpolation with coordinates
        # 2-clockwise, 3-counterclockwise
        # Operation code (D0x) missing is deprecated... oh well I will support it.
        # Optional start with G02 or G03, optional end with D01 or D02 with
        # optional coordinates but at least one in any order.
        self.circ_re = re.compile(r'^(?:G0?([23]))?(?=.*X([+-]?\d+))?(?=.*Y([+-]?\d+))' +
                                  '?(?=.*I([+-]?\d+))?(?=.*J([+-]?\d+))?[XYIJ][^D]*(?:D0([12]))?\*$')

        # Absolute/Relative G90/1 (OBSOLETE)
        self.absrel_re = re.compile(r'^G9([01])\*$')

        # flag to store if a conversion was done. It is needed because multiple units declarations can be found
        # in a Gerber file (normal or obsolete ones)
        self.conversion_done = False

        self.in_header = None

    def parse_file(self, filename):
        """

        :param filename: HPGL2 file to parse.
        :type filename: str
        :return: None
        """

        with open(filename, 'r') as gfile:
            self.parse_lines([line.rstrip('\n') for line in gfile])

    def parse_lines(self, glines):
        """
        Main HPGL2 parser.

        :param glines: HPGL2 code as list of strings, each element being
            one line of the source file.
        :type glines: list
        :return: None
        :rtype: None
        """

        # Coordinates of the current path, each is [x, y]
        path = list()

        geo_buffer = []

        # Current coordinates
        current_x = None
        current_y = None
        previous_x = None
        previous_y = None

        # store the pen (tool) status
        pen_status = 'up'

        # store the current tool here
        current_tool = None

        # ### Parsing starts here ## ##
        line_num = 0
        gline = ""

        self.app.inform.emit('%s %d %s.' % (_("HPGL2 processing. Parsing"), len(glines), _("lines")))
        try:
            for gline in glines:
                if self.app.abort_flag:
                    # graceful abort requested by the user
                    raise FlatCAMApp.GracefulException

                line_num += 1
                self.source_file += gline + '\n'

                # Cleanup #
                gline = gline.strip(' \r\n')
                # log.debug("Line=%3s %s" % (line_num, gline))

                # ###################
                # Ignored lines #####
                # Comments      #####
                # ###################
                match = self.comment_re.search(gline)
                if match:
                    log.debug(str(match.group(1)))
                    continue

                # #####################################################
                # Absolute/relative coordinates G90/1 OBSOLETE ########
                # #####################################################
                match = self.absrel_re.search(gline)
                if match:
                    absolute = {'0': "Absolute", '1': "Relative"}[match.group(1)]
                    log.warning("Gerber obsolete coordinates type found = %s (Absolute or Relative) " % absolute)
                    continue

                # search for the initialization
                match = self.initialize_re.search(gline)
                if match:
                    self.in_header = False
                    continue

                if self.in_header is False:
                    # tools detection
                    match = self.sp_re.search(gline)
                    if match:
                        tool = match.group(1)
                        # self.tools[tool] = dict()
                        self.tools.update({
                            tool: {
                                'tooldia': float('%.*f' %
                                                 (
                                                     self.decimals,
                                                     float(self.app.defaults['geometry_cnctooldia'])
                                                 )
                                                 ),
                                'offset': 'Path',
                                'offset_value': 0.0,
                                'type': 'Iso',
                                'tool_type': 'C1',
                                'data': deepcopy(self.default_data),
                                'solid_geometry': list()
                            }
                        })

                        if current_tool:
                            if path:
                                geo = LineString(path)
                                self.tools[current_tool]['solid_geometry'].append(geo)
                                geo_buffer.append(geo)
                                path[:] = []

                        current_tool = tool
                        continue

                    # pen status detection
                    match = self.pen_re.search(gline)
                    if match:
                        pen_status = {'PU': 'up', 'PD': 'down'}[match.group(1)]
                        continue

                    # linear move
                    match = self.abs_move_re.search(gline)
                    if match:
                        # Parse coordinates
                        if match.group(1) is not None:
                            linear_x = parse_number(match.group(1))
                            current_x = linear_x
                        else:
                            linear_x = current_x

                        if match.group(2) is not None:
                            linear_y = parse_number(match.group(2))
                            current_y = linear_y
                        else:
                            linear_y = current_y

                        # Pen down: add segment
                        if pen_status == 'down':
                            # if linear_x or linear_y are None, ignore those
                            if current_x is not None and current_y is not None:
                                # only add the point if it's a new one otherwise skip it (harder to process)
                                if path[-1] != [current_x, current_y]:
                                    path.append([current_x, current_y])
                            else:
                                self.app.inform.emit('[WARNING] %s: %s' %
                                                     (_("Coordinates missing, line ignored"), str(gline)))

                        elif pen_status == 'up':
                            if len(path) > 1:
                                geo = LineString(path)
                                self.tools[current_tool]['solid_geometry'].append(geo)
                                geo_buffer.append(geo)
                                path[:] = []

                            # if linear_x or linear_y are None, ignore those
                            if linear_x is not None and linear_y is not None:
                                path = [[linear_x, linear_y]]  # Start new path
                            else:
                                self.app.inform.emit('[WARNING] %s: %s' %
                                                     (_("Coordinates missing, line ignored"), str(gline)))

                        # log.debug("Line_number=%3s X=%s Y=%s (%s)" % (line_num, linear_x, linear_y, gline))
                        continue

                    # ## Circular interpolation
                    # -clockwise,
                    # -counterclockwise
                    match = self.circ_re.search(gline)
                    # if match:
                    #     arcdir = [None, None, "cw", "ccw"]
                    #
                    #     mode, circular_x, circular_y, i, j, d = match.groups()
                    #
                    #     try:
                    #         circular_x = parse_number(circular_x)
                    #     except Exception as e:
                    #         circular_x = current_x
                    #
                    #     try:
                    #         circular_y = parse_number(circular_y)
                    #     except Exception as e:
                    #         circular_y = current_y
                    #
                    #     try:
                    #         i = parse_number(i)
                    #     except Exception as e:
                    #         i = 0
                    #
                    #     try:
                    #         j = parse_number(j)
                    #     except Exception as e:
                    #         j = 0
                    #
                    #     if mode is None and current_interpolation_mode not in [2, 3]:
                    #         log.error("Found arc without circular interpolation mode defined. (%d)" % line_num)
                    #         log.error(gline)
                    #         continue
                    #     elif mode is not None:
                    #         current_interpolation_mode = int(mode)
                    #
                    #     # Set operation code if provided
                    #     if d is not None:
                    #         current_operation_code = int(d)
                    #
                    #     # Nothing created! Pen Up.
                    #     if current_operation_code == 2:
                    #         log.warning("Arc with D2. (%d)" % line_num)
                    #         if len(path) > 1:
                    #             geo_dict = dict()
                    #
                    #             if last_path_aperture is None:
                    #                 log.warning("No aperture defined for curent path. (%d)" % line_num)
                    #
                    #             # --- BUFFERED ---
                    #             width = self.apertures[last_path_aperture]["size"]
                    #
                    #             # this treats the case when we are storing geometry as paths
                    #             geo_f = LineString(path)
                    #             if not geo_f.is_empty:
                    #                 geo_dict['follow'] = geo_f
                    #
                    #             # this treats the case when we are storing geometry as solids
                    #             buffered = LineString(path).buffer(width / 1.999, int(self.steps_per_circle))
                    #
                    #             if last_path_aperture not in self.apertures:
                    #                 self.apertures[last_path_aperture] = dict()
                    #             if 'geometry' not in self.apertures[last_path_aperture]:
                    #                 self.apertures[last_path_aperture]['geometry'] = []
                    #             self.apertures[last_path_aperture]['geometry'].append(deepcopy(geo_dict))
                    #
                    #         current_x = circular_x
                    #         current_y = circular_y
                    #         path = [[current_x, current_y]]  # Start new path
                    #         continue
                    #
                    #     # Flash should not happen here
                    #     if current_operation_code == 3:
                    #         log.error("Trying to flash within arc. (%d)" % line_num)
                    #         continue
                    #
                    #     if quadrant_mode == 'MULTI':
                    #         center = [i + current_x, j + current_y]
                    #         radius = np.sqrt(i ** 2 + j ** 2)
                    #         start = np.arctan2(-j, -i)  # Start angle
                    #         # Numerical errors might prevent start == stop therefore
                    #         # we check ahead of time. This should result in a
                    #         # 360 degree arc.
                    #         if current_x == circular_x and current_y == circular_y:
                    #             stop = start
                    #         else:
                    #             stop = np.arctan2(-center[1] + circular_y, -center[0] + circular_x)  # Stop angle
                    #
                    #         this_arc = arc(center, radius, start, stop,
                    #                        arcdir[current_interpolation_mode],
                    #                        self.steps_per_circle)
                    #
                    #         # The last point in the computed arc can have
                    #         # numerical errors. The exact final point is the
                    #         # specified (x, y). Replace.
                    #         this_arc[-1] = (circular_x, circular_y)
                    #
                    #         # Last point in path is current point
                    #         # current_x = this_arc[-1][0]
                    #         # current_y = this_arc[-1][1]
                    #         current_x, current_y = circular_x, circular_y
                    #
                    #         # Append
                    #         path += this_arc
                    #         last_path_aperture = current_aperture
                    #
                    #         continue
                    #
                    #     if quadrant_mode == 'SINGLE':
                    #
                    #         center_candidates = [
                    #             [i + current_x, j + current_y],
                    #             [-i + current_x, j + current_y],
                    #             [i + current_x, -j + current_y],
                    #             [-i + current_x, -j + current_y]
                    #         ]
                    #
                    #         valid = False
                    #         log.debug("I: %f  J: %f" % (i, j))
                    #         for center in center_candidates:
                    #             radius = np.sqrt(i ** 2 + j ** 2)
                    #
                    #             # Make sure radius to start is the same as radius to end.
                    #             radius2 = np.sqrt((center[0] - circular_x) ** 2 + (center[1] - circular_y) ** 2)
                    #             if radius2 < radius * 0.95 or radius2 > radius * 1.05:
                    #                 continue  # Not a valid center.
                    #
                    #             # Correct i and j and continue as with multi-quadrant.
                    #             i = center[0] - current_x
                    #             j = center[1] - current_y
                    #
                    #             start = np.arctan2(-j, -i)  # Start angle
                    #             stop = np.arctan2(-center[1] + circular_y, -center[0] + circular_x)  # Stop angle
                    #             angle = abs(arc_angle(start, stop, arcdir[current_interpolation_mode]))
                    #             log.debug("ARC START: %f, %f  CENTER: %f, %f  STOP: %f, %f" %
                    #                       (current_x, current_y, center[0], center[1], circular_x, circular_y))
                    #             log.debug("START Ang: %f, STOP Ang: %f, DIR: %s, ABS: %.12f <= %.12f: %s" %
                    #                       (start * 180 / np.pi, stop * 180 / np.pi, arcdir[current_interpolation_mode],
                    #                        angle * 180 / np.pi, np.pi / 2 * 180 / np.pi, angle <= (np.pi + 1e-6) / 2))
                    #
                    #             if angle <= (np.pi + 1e-6) / 2:
                    #                 log.debug("########## ACCEPTING ARC ############")
                    #                 this_arc = arc(center, radius, start, stop,
                    #                                arcdir[current_interpolation_mode],
                    #                                self.steps_per_circle)
                    #
                    #                 # Replace with exact values
                    #                 this_arc[-1] = (circular_x, circular_y)
                    #
                    #                 # current_x = this_arc[-1][0]
                    #                 # current_y = this_arc[-1][1]
                    #                 current_x, current_y = circular_x, circular_y
                    #
                    #                 path += this_arc
                    #                 last_path_aperture = current_aperture
                    #                 valid = True
                    #                 break
                    #
                    #         if valid:
                    #             continue
                    #         else:
                    #             log.warning("Invalid arc in line %d." % line_num)

                # ## Line did not match any pattern. Warn user.
                log.warning("Line ignored (%d): %s" % (line_num, gline))

            if len(geo_buffer) == 0 and len(self.solid_geometry) == 0:
                log.error("Object is not HPGL2 file or empty. Aborting Object creation.")
                return 'fail'

            log.warning("Joining %d polygons." % len(geo_buffer))
            self.app.inform.emit('%s: %d.' % (_("Gerber processing. Joining polygons"), len(geo_buffer)))

            new_poly = unary_union(geo_buffer)
            self.solid_geometry = new_poly

        except Exception as err:
            ex_type, ex, tb = sys.exc_info()
            traceback.print_tb(tb)
            # print traceback.format_exc()

            log.error("HPGL2 PARSING FAILED. Line %d: %s" % (line_num, gline))

            loc = '%s #%d %s: %s\n' % (_("HPGL2 Line"), line_num, _("HPGL2 Line Content"), gline) + repr(err)
            self.app.inform.emit('[ERROR] %s\n%s:' % (_("HPGL2 Parser ERROR"), loc))

    def create_geometry(self):
        """
        :rtype : None
        :return: None
        """
        pass

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

        log.debug("parseGerber.Gerber.bounds()")

        if self.solid_geometry is None:
            log.debug("solid_geometry is None")
            return 0, 0, 0, 0

        def bounds_rec(obj):
            if type(obj) is list and type(obj) is not MultiPolygon:
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

    def convert_units(self, obj_units):
        """
        Converts the units of the object to ``units`` by scaling all
        the geometry appropriately. This call ``scale()``. Don't call
        it again in descendants.

        :param obj_units: "IN" or "MM"
        :type obj_units: str
        :return: Scaling factor resulting from unit change.
        :rtype: float
        """

        if obj_units.upper() == self.units.upper():
            log.debug("parseGerber.Gerber.convert_units() --> Factor: 1")
            return 1.0

        if obj_units.upper() == "MM":
            factor = 25.4
            log.debug("parseGerber.Gerber.convert_units() --> Factor: 25.4")
        elif obj_units.upper() == "IN":
            factor = 1 / 25.4
            log.debug("parseGerber.Gerber.convert_units() --> Factor: %s" % str(1 / 25.4))
        else:
            log.error("Unsupported units: %s" % str(obj_units))
            log.debug("parseGerber.Gerber.convert_units() --> Factor: 1")
            return 1.0

        self.units = obj_units
        self.file_units_factor = factor
        self.scale(factor, factor)
        return factor

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
        :param point: reference point for scaling operation
        :rtype : None
        """
        log.debug("parseGerber.Gerber.scale()")

        try:
            xfactor = float(xfactor)
        except Exception:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Scale factor has to be a number: integer or float."))
            return

        if yfactor is None:
            yfactor = xfactor
        else:
            try:
                yfactor = float(yfactor)
            except Exception:
                self.app.inform.emit('[ERROR_NOTCL] %s' %
                                     _("Scale factor has to be a number: integer or float."))
                return

        if xfactor == 0 and yfactor == 0:
            return

        if point is None:
            px = 0
            py = 0
        else:
            px, py = point

        # variables to display the percentage of work done
        self.geo_len = 0
        try:
            self.geo_len = len(self.solid_geometry)
        except TypeError:
            self.geo_len = 1

        self.old_disp_number = 0
        self.el_count = 0

        def scale_geom(obj):
            if type(obj) is list:
                new_obj = []
                for g in obj:
                    new_obj.append(scale_geom(g))
                return new_obj
            else:
                try:
                    self.el_count += 1
                    disp_number = int(np.interp(self.el_count, [0, self.geo_len], [0, 99]))
                    if self.old_disp_number < disp_number <= 100:
                        self.app.proc_container.update_view_text(' %d%%' % disp_number)
                        self.old_disp_number = disp_number

                    return affinity.scale(obj, xfactor, yfactor, origin=(px, py))
                except AttributeError:
                    return obj

        self.solid_geometry = scale_geom(self.solid_geometry)
        self.follow_geometry = scale_geom(self.follow_geometry)

        # we need to scale the geometry stored in the Gerber apertures, too
        try:
            for apid in self.apertures:
                new_geometry = list()
                if 'geometry' in self.apertures[apid]:
                    for geo_el in self.apertures[apid]['geometry']:
                        new_geo_el = dict()
                        if 'solid' in geo_el:
                            new_geo_el['solid'] = scale_geom(geo_el['solid'])
                        if 'follow' in geo_el:
                            new_geo_el['follow'] = scale_geom(geo_el['follow'])
                        if 'clear' in geo_el:
                            new_geo_el['clear'] = scale_geom(geo_el['clear'])
                        new_geometry.append(new_geo_el)

                self.apertures[apid]['geometry'] = deepcopy(new_geometry)

                try:
                    if str(self.apertures[apid]['type']) == 'R' or str(self.apertures[apid]['type']) == 'O':
                        self.apertures[apid]['width'] *= xfactor
                        self.apertures[apid]['height'] *= xfactor
                    elif str(self.apertures[apid]['type']) == 'P':
                        self.apertures[apid]['diam'] *= xfactor
                        self.apertures[apid]['nVertices'] *= xfactor
                except KeyError:
                    pass

                try:
                    if self.apertures[apid]['size'] is not None:
                        self.apertures[apid]['size'] = float(self.apertures[apid]['size'] * xfactor)
                except KeyError:
                    pass

        except Exception as e:
            log.debug('camlib.Gerber.scale() Exception --> %s' % str(e))
            return 'fail'

        self.app.inform.emit('[success] %s' % _("Gerber Scale done."))
        self.app.proc_container.new_text = ''

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
        log.debug("parseGerber.Gerber.offset()")

        try:
            dx, dy = vect
        except TypeError:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("An (x,y) pair of values are needed. "
                                   "Probable you entered only one value in the Offset field."))
            return

        if dx == 0 and dy == 0:
            return

        # variables to display the percentage of work done
        self.geo_len = 0
        try:
            for __ in self.solid_geometry:
                self.geo_len += 1
        except TypeError:
            self.geo_len = 1

        self.old_disp_number = 0
        self.el_count = 0

        def offset_geom(obj):
            if type(obj) is list:
                new_obj = []
                for g in obj:
                    new_obj.append(offset_geom(g))
                return new_obj
            else:
                try:
                    self.el_count += 1
                    disp_number = int(np.interp(self.el_count, [0, self.geo_len], [0, 99]))
                    if self.old_disp_number < disp_number <= 100:
                        self.app.proc_container.update_view_text(' %d%%' % disp_number)
                        self.old_disp_number = disp_number

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

        self.app.inform.emit('[success] %s' %
                             _("Gerber Offset done."))
        self.app.proc_container.new_text = ''

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
        log.debug("parseGerber.Gerber.mirror()")

        px, py = point
        xscale, yscale = {"X": (1.0, -1.0), "Y": (-1.0, 1.0)}[axis]

        # variables to display the percentage of work done
        self.geo_len = 0
        try:
            for __ in self.solid_geometry:
                self.geo_len += 1
        except TypeError:
            self.geo_len = 1

        self.old_disp_number = 0
        self.el_count = 0

        def mirror_geom(obj):
            if type(obj) is list:
                new_obj = []
                for g in obj:
                    new_obj.append(mirror_geom(g))
                return new_obj
            else:
                try:
                    self.el_count += 1
                    disp_number = int(np.interp(self.el_count, [0, self.geo_len], [0, 99]))
                    if self.old_disp_number < disp_number <= 100:
                        self.app.proc_container.update_view_text(' %d%%' % disp_number)
                        self.old_disp_number = disp_number

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

        self.app.inform.emit('[success] %s' %
                             _("Gerber Mirror done."))
        self.app.proc_container.new_text = ''

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
        :param angle_x: the angle on X axis for skewing
        :param angle_y: the angle on Y axis for skewing
        :param point: reference point for skewing operation
        :return None
        """
        log.debug("parseGerber.Gerber.skew()")

        px, py = point

        if angle_x == 0 and angle_y == 0:
            return

        # variables to display the percentage of work done
        self.geo_len = 0
        try:
            self.geo_len = len(self.solid_geometry)
        except TypeError:
            self.geo_len = 1

        self.old_disp_number = 0
        self.el_count = 0

        def skew_geom(obj):
            if type(obj) is list:
                new_obj = []
                for g in obj:
                    new_obj.append(skew_geom(g))
                return new_obj
            else:
                try:
                    self.el_count += 1
                    disp_number = int(np.interp(self.el_count, [0, self.geo_len], [0, 100]))
                    if self.old_disp_number < disp_number <= 100:
                        self.app.proc_container.update_view_text(' %d%%' % disp_number)
                        self.old_disp_number = disp_number

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

        self.app.inform.emit('[success] %s' % _("Gerber Skew done."))
        self.app.proc_container.new_text = ''

    def rotate(self, angle, point):
        """
        Rotate an object by a given angle around given coords (point)
        :param angle:
        :param point:
        :return:
        """
        log.debug("parseGerber.Gerber.rotate()")

        px, py = point

        if angle == 0:
            return

        # variables to display the percentage of work done
        self.geo_len = 0
        try:
            for __ in self.solid_geometry:
                self.geo_len += 1
        except TypeError:
            self.geo_len = 1

        self.old_disp_number = 0
        self.el_count = 0

        def rotate_geom(obj):
            if type(obj) is list:
                new_obj = []
                for g in obj:
                    new_obj.append(rotate_geom(g))
                return new_obj
            else:
                try:
                    self.el_count += 1
                    disp_number = int(np.interp(self.el_count, [0, self.geo_len], [0, 100]))
                    if self.old_disp_number < disp_number <= 100:
                        self.app.proc_container.update_view_text(' %d%%' % disp_number)
                        self.old_disp_number = disp_number

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
        self.app.inform.emit('[success] %s' %
                             _("Gerber Rotate done."))
        self.app.proc_container.new_text = ''


def parse_number(strnumber):
    """
    Parse a single number of HPGL2 coordinates.

    :param strnumber: String containing a number
    from a coordinate data block, possibly with a leading sign.
    :type strnumber: str
    :return: The number in floating point.
    :rtype: float
    """

    return float(strnumber) / 40.0 # in milimeters

