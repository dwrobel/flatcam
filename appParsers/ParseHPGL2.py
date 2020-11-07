# ############################################################
# FlatCAM: 2D Post-processing for Manufacturing              #
# http://flatcam.org                                         #
# File Author: Marius Adrian Stanciu (c)                     #
# Date: 12/12/2019                                           #
# MIT Licence                                                #
# ############################################################

from camlib import arc, three_point_circle, grace

import numpy as np
import re
import logging
import traceback
from copy import deepcopy
import sys

from shapely.ops import unary_union
from shapely.geometry import LineString, Point

# import AppTranslation as fcTranslate
import gettext
import builtins

if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class HPGL2:
    """
    HPGL2 parsing.
    """

    def __init__(self, app):
        """
        The constructor takes FlatCAMApp.App as parameter.

        """
        self.app = app

        # How to approximate a circle with lines.
        self.steps_per_circle = int(self.app.defaults["geometry_circle_steps"])
        self.decimals = self.app.decimals

        # store the file units here
        self.units = 'MM'

        # storage for the tools
        self.tools = {}

        self.default_data = {}
        self.default_data.update({
            "name":                     '_ncc',
            "plot":                     self.app.defaults["geometry_plot"],
            "cutz":                     self.app.defaults["geometry_cutz"],
            "vtipdia":                  self.app.defaults["geometry_vtipdia"],
            "vtipangle":                self.app.defaults["geometry_vtipangle"],
            "travelz":                  self.app.defaults["geometry_travelz"],
            "feedrate":                 self.app.defaults["geometry_feedrate"],
            "feedrate_z":               self.app.defaults["geometry_feedrate_z"],
            "feedrate_rapid":           self.app.defaults["geometry_feedrate_rapid"],
            "dwell":                    self.app.defaults["geometry_dwell"],
            "dwelltime":                self.app.defaults["geometry_dwelltime"],
            "multidepth":               self.app.defaults["geometry_multidepth"],
            "ppname_g":                 self.app.defaults["geometry_ppname_g"],
            "depthperpass":             self.app.defaults["geometry_depthperpass"],
            "extracut":                 self.app.defaults["geometry_extracut"],
            "extracut_length":          self.app.defaults["geometry_extracut_length"],
            "toolchange":               self.app.defaults["geometry_toolchange"],
            "toolchangez":              self.app.defaults["geometry_toolchangez"],
            "endz":                     self.app.defaults["geometry_endz"],
            "endxy":                    self.app.defaults["geometry_endxy"],
            "area_exclusion":           self.app.defaults["geometry_area_exclusion"],
            "area_shape":               self.app.defaults["geometry_area_shape"],
            "area_strategy":            self.app.defaults["geometry_area_strategy"],
            "area_overz":               self.app.defaults["geometry_area_overz"],

            "spindlespeed":             self.app.defaults["geometry_spindlespeed"],
            "toolchangexy":             self.app.defaults["geometry_toolchangexy"],
            "startz":                   self.app.defaults["geometry_startz"],

            "tooldia":                  self.app.defaults["tools_paint_tooldia"],
            "tools_paint_offset":       self.app.defaults["tools_paint_offset"],
            "tools_paint_method":       self.app.defaults["tools_paint_method"],
            "tools_paint_selectmethod": self.app.defaults["tools_paint_selectmethod"],
            "tools_paint_connect":      self.app.defaults["tools_paint_connect"],
            "tools_paint_contour":      self.app.defaults["tools_paint_contour"],
            "tools_paint_overlap":      self.app.defaults["tools_paint_overlap"],
            "tools_paint_rest":         self.app.defaults["tools_paint_rest"],

            "tools_ncc_operation":      self.app.defaults["tools_ncc_operation"],
            "tools_ncc_margin":         self.app.defaults["tools_ncc_margin"],
            "tools_ncc_method":         self.app.defaults["tools_ncc_method"],
            "tools_ncc_connect":        self.app.defaults["tools_ncc_connect"],
            "tools_ncc_contour":        self.app.defaults["tools_ncc_contour"],
            "tools_ncc_overlap":        self.app.defaults["tools_ncc_overlap"],
            "tools_ncc_rest":           self.app.defaults["tools_ncc_rest"],
            "tools_ncc_ref":            self.app.defaults["tools_ncc_ref"],
            "tools_ncc_offset_choice":  self.app.defaults["tools_ncc_offset_choice"],
            "tools_ncc_offset_value":   self.app.defaults["tools_ncc_offset_value"],
            "tools_ncc_milling_type":   self.app.defaults["tools_ncc_milling_type"],

            "tools_iso_passes":         self.app.defaults["tools_iso_passes"],
            "tools_iso_overlap":        self.app.defaults["tools_iso_overlap"],
            "tools_iso_milling_type":   self.app.defaults["tools_iso_milling_type"],
            "tools_iso_follow":         self.app.defaults["tools_iso_follow"],
            "tools_iso_isotype":        self.app.defaults["tools_iso_isotype"],

            "tools_iso_rest":           self.app.defaults["tools_iso_rest"],
            "tools_iso_combine_passes": self.app.defaults["tools_iso_combine_passes"],
            "tools_iso_isoexcept":      self.app.defaults["tools_iso_isoexcept"],
            "tools_iso_selection":      self.app.defaults["tools_iso_selection"],
            "tools_iso_poly_ints":      self.app.defaults["tools_iso_poly_ints"],
            "tools_iso_force":          self.app.defaults["tools_iso_force"],
            "tools_iso_area_shape":     self.app.defaults["tools_iso_area_shape"]
        })

        # will store the geometry here for compatibility reason
        self.solid_geometry = None

        self.source_file = ''

        # ### Parser patterns ## ##

        # comment
        self.comment_re = re.compile(r"^CO\s*[\"']([a-zA-Z0-9\s]*)[\"'];?$")

        # select pen
        self.sp_re = re.compile(r'SP(\d);?$')
        # pen position
        self.pen_re = re.compile(r"^(P[U|D]);?$")

        # Initialize
        self.initialize_re = re.compile(r'^(IN);?$')

        # Absolute linear interpolation
        self.abs_move_re = re.compile(r"^PA\s*(-?\d+\.?\d*),?\s*(-?\d+\.?\d*)*;?$")
        # Relative linear interpolation
        self.rel_move_re = re.compile(r"^PR\s*(-?\d+\.?\d*),?\s*(-?\d+\.?\d*)*;?$")

        # Circular interpolation with radius
        self.circ_re = re.compile(r"^CI\s*(\+?\d+\.?\d+?)?\s*;?\s*$")

        # Arc interpolation with radius
        self.arc_re = re.compile(r"^AA\s*([+-]?\d+),?\s*([+-]?\d+),?\s*([+-]?\d+);?$")

        # Arc interpolation with 3 points
        self.arc_3pt_re = re.compile(r"^AT\s*([+-]?\d+),?\s*([+-]?\d+),?\s*([+-]?\d+),?\s*([+-]?\d+);?$")

        self.init_done = None

    def parse_file(self, filename):
        """
        Creates a list of lines from the HPGL2 file and send it to the main parser.

        :param filename: HPGL2 file to parse.
        :type filename: str
        :return: None
        """

        with open(filename, 'r') as gfile:
            glines = [line.rstrip('\n') for line in gfile]
            self.parse_lines(glines=glines)

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
        path = []

        geo_buffer = []

        # Current coordinates
        current_x = None
        current_y = None

        # Found coordinates
        linear_x = None
        linear_y = None

        # store the pen (tool) status
        pen_status = 'up'

        # store the current tool here
        current_tool = None

        # ### Parsing starts here ## ##
        line_num = 0
        gline = ""

        self.app.inform.emit('%s %d %s.' % (_("HPGL2 processing. Parsing"), len(glines), _("Lines").lower()))
        try:
            for gline in glines:
                if self.app.abort_flag:
                    # graceful abort requested by the user
                    raise grace

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

                # search for the initialization
                match = self.initialize_re.search(gline)
                if match:
                    self.init_done = True
                    continue

                if self.init_done is True:
                    # tools detection
                    match = self.sp_re.search(gline)
                    if match:
                        tool = match.group(1)
                        # self.tools[tool] = {}
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

                    # Linear interpolation
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

                    # Circular interpolation
                    match = self.circ_re.search(gline)
                    if match:
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

                        if current_x is not None and current_y is not None:
                            radius = float(match.group(1))
                            geo = Point((current_x, current_y)).buffer(radius, int(self.steps_per_circle))
                            geo_line = geo.exterior
                            self.tools[current_tool]['solid_geometry'].append(geo_line)
                            geo_buffer.append(geo_line)
                            continue

                    # Arc interpolation with radius
                    match = self.arc_re.search(gline)
                    if match:
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

                        if current_x is not None and current_y is not None:
                            center = [parse_number(match.group(1)), parse_number(match.group(2))]
                            angle = np.deg2rad(float(match.group(3)))
                            p1 = [current_x, current_y]

                            arcdir = "ccw" if angle >= 0.0 else "cw"
                            radius = np.sqrt((center[0] - p1[0]) ** 2 + (center[1] - p1[1]) ** 2)
                            startangle = np.arctan2(p1[1] - center[1], p1[0] - center[0])
                            stopangle = startangle + angle

                            geo = LineString(arc(center, radius, startangle, stopangle, arcdir, self.steps_per_circle))
                            self.tools[current_tool]['solid_geometry'].append(geo)
                            geo_buffer.append(geo)

                            line_coords = list(geo.coords)
                            current_x = line_coords[0]
                            current_y = line_coords[1]
                            continue

                    # Arc interpolation with 3 points
                    match = self.arc_3pt_re.search(gline)
                    if match:
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

                        if current_x is not None and current_y is not None:
                            p1 = [current_x, current_y]
                            p3 = [parse_number(match.group(1)), parse_number(match.group(2))]
                            p2 = [parse_number(match.group(3)), parse_number(match.group(4))]

                            try:
                                center, radius, t = three_point_circle(p1, p2, p3)
                            except TypeError:
                                return

                            direction = 'cw' if np.sign(t) > 0 else 'ccw'

                            startangle = np.arctan2(p1[1] - center[1], p1[0] - center[0])
                            stopangle = np.arctan2(p3[1] - center[1], p3[0] - center[0])

                            geo = LineString(arc(center, radius, startangle, stopangle,
                                                 direction, self.steps_per_circle))
                            self.tools[current_tool]['solid_geometry'].append(geo)
                            geo_buffer.append(geo)

                            # p2 is the end point for the 3-pt circle
                            current_x = p2[0]
                            current_y = p2[1]
                            continue

                # ## Line did not match any pattern. Warn user.
                log.warning("Line ignored (%d): %s" % (line_num, gline))

            if not geo_buffer and not self.solid_geometry:
                log.error("Object is not HPGL2 file or empty. Aborting Object creation.")
                return 'fail'

            log.warning("Joining %d polygons." % len(geo_buffer))
            self.app.inform.emit('%s: %d.' % (_("Gerber processing. Joining polygons"), len(geo_buffer)))

            new_poly = unary_union(geo_buffer)
            self.solid_geometry = new_poly

        except Exception as err:
            ex_type, ex, tb = sys.exc_info()
            traceback.print_tb(tb)
            print(traceback.format_exc())

            log.error("HPGL2 PARSING FAILED. Line %d: %s" % (line_num, gline))

            loc = '%s #%d %s: %s\n' % (_("HPGL2 Line"), line_num, _("HPGL2 Line Content"), gline) + repr(err)
            self.app.inform.emit('[ERROR] %s\n%s:' % (_("HPGL2 Parser ERROR"), loc))


def parse_number(strnumber):
    """
    Parse a single number of HPGL2 coordinates.

    :param strnumber: String containing a number
    from a coordinate data block, possibly with a leading sign.
    :type strnumber: str
    :return: The number in floating point.
    :rtype: float
    """

    return float(strnumber) / 40.0  # in milimeters
