############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
############################################################

from FlatCAMTool import FlatCAMTool
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import cascaded_union, unary_union

from FlatCAMObj import *

import math
from copy import copy, deepcopy
import numpy as np

import zlib
import re

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ToolPDF(FlatCAMTool):
    """
    Parse a PDF file.
    Reference here: https://www.adobe.com/content/dam/acom/en/devnet/pdf/pdfs/pdf_reference_archives/PDFReference.pdf
    Return a list of geometries
    """
    toolName = _("PDF Import Tool")

    def __init__(self, app):
        FlatCAMTool.__init__(self, app)
        self.app = app
        self.step_per_circles = self.app.defaults["gerber_circle_steps"]

        self.stream_re = re.compile(b'.*?FlateDecode.*?stream(.*?)endstream', re.S)

        # detect 're' command
        self.rect_re = re.compile(r'^(-?\d+\.?\d*)\s(-?\d+\.?\d*)\s(-?\d+\.?\d*)\s(-?\d+\.?\d*)\s*re$')
        # detect 'm' command
        self.start_subpath_re = re.compile(r'^(-?\d+\.?\d*)\s(-?\d+\.?\d*)\sm$')
        # detect 'l' command
        self.draw_line_re = re.compile(r'^(-?\d+\.?\d*)\s(-?\d+\.?\d*)\sl')
        # detect 'c' command
        self.draw_arc_3pt_re = re.compile(r'^(-?\d+\.?\d*)\s(-?\d+\.?\d*)\s(-?\d+\.?\d*)\s(-?\d+\.?\d*)\s(-?\d+\.?\d*)'
                                          r'\s(-?\d+\.?\d*)\s*c$')
        # detect 'v' command
        self.draw_arc_2pt_c1start_re = re.compile(r'^(-?\d+\.?\d*)\s(-?\d+\.?\d*)\s(-?\d+\.?\d*)\s(-?\d+\.?\d*)\s*v$')
        # detect 'y' command
        self.draw_arc_2pt_c2stop_re = re.compile(r'^(-?\d+\.?\d*)\s(-?\d+\.?\d*)\s(-?\d+\.?\d*)\s(-?\d+\.?\d*)\s*y$')
        # detect 'h' command
        self.end_subpath_re = re.compile(r'^h$')

        # detect 'w' command
        self.strokewidth_re = re.compile(r'^(\d+\.?\d*)\s*w$')
        # detect 'S' command
        self.stroke_path__re = re.compile(r'^S\s?[Q]?$')
        # detect 's' command
        self.close_stroke_path__re = re.compile(r'^s$')
        # detect 'f' or 'f*' command
        self.fill_path_re = re.compile(r'^[f|F][*]?$')
        # detect 'B' or 'B*' command
        self.fill_stroke_path_re = re.compile(r'^B[*]?$')
        # detect 'b' or 'b*' command
        self.close_fill_stroke_path_re = re.compile(r'^b[*]?$')
        # detect 'n'
        self.no_op_re = re.compile(r'^n$')

        # detect offset transformation. Pattern: (1) (0) (0) (1) (x) (y)
        self.offset_re = re.compile(r'^1\.?0*\s0?\.?0*\s0?\.?0*\s1\.?0*\s(-?\d+\.?\d*)\s(-?\d+\.?\d*)\s*cm$')
        # detect scale transformation. Pattern: (factor_x) (0) (0) (factor_y) (0) (0)
        self.scale_re = re.compile(r'^q? (-?\d+\.?\d*) 0\.?0* 0\.?0* (-?\d+\.?\d*) 0\.?0* 0\.?0*\s+cm$')
        # detect combined transformation. Should always be the last
        self.combined_transform_re = re.compile(r'^q?\s*(-?\d+\.?\d*) (-?\d+\.?\d*) (-?\d+\.?\d*) (-?\d+\.?\d*) '
                                                r'(-?\d+\.?\d*) (-?\d+\.?\d*)\s+cm$')

        # detect clipping path
        self.clip_path_re = re.compile(r'^W[*]? n?$')

        self.geo_buffer = []
        self.pdf_parsed = ''

        # conversion factor to INCH
        self.point_to_unit_factor = 0.01388888888

    def run(self, toggle=True):
        self.app.report_usage("ToolPDF()")

        # init variables for reuse
        self.geo_buffer = []
        self.pdf_parsed = ''

        # the UNITS in PDF files are points and here we set the factor to convert them to real units (either MM or INCH)
        if self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().upper() == 'MM':
            # 1 inch = 72 points => 1 point = 1 / 72 = 0.01388888888 inch = 0.01388888888 inch * 25.4 = 0.35277777778 mm
            self.point_to_unit_factor = 0.35277777778
        else:
            # 1 inch = 72 points => 1 point = 1 / 72 = 0.01388888888 inch
            self.point_to_unit_factor = 0.01388888888

        self.set_tool_ui()
        self.on_open_pdf_click()

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, shortcut='ALT+Q', **kwargs)

    def set_tool_ui(self):
        pass

    def on_open_pdf_click(self):
        """
        File menu callback for opening an PDF file.

        :return: None
        """

        self.app.report_usage("ToolPDF.on_open_pdf_click()")
        self.app.log.debug("ToolPDF.on_open_pdf_click()")

        _filter_ = "Adobe PDF Files (*.pdf);;" \
                   "All Files (*.*)"

        try:
            filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Open PDF"),
                                                                   directory=self.app.get_last_folder(),
                                                                   filter=_filter_)
        except TypeError:
            filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Open PDF"), filter=_filter_)

        if len(filenames) == 0:
            self.app.inform.emit(_("[WARNING_NOTCL] Open PDF cancelled."))
        else:
            for filename in filenames:
                if filename != '':
                    self.app.worker_task.emit({'fcn': self.open_pdf, 'params': [filename]})

    def open_pdf(self, filename):
        new_name = filename.split('/')[-1].split('\\')[-1]

        def obj_init(grb_obj, app_obj):
            with open(filename, "rb") as f:
                pdf = f.read()

            stream_nr = 0
            for s in re.findall(self.stream_re, pdf):
                stream_nr += 1
                log.debug(" PDF STREAM: %d\n" % stream_nr)
                s = s.strip(b'\r\n')
                try:
                    self.pdf_parsed += (zlib.decompress(s).decode('UTF-8') + '\r\n')
                except Exception as e:
                    app_obj.log.debug("ToolPDF.open_pdf().obj_init() --> %s" % str(e))

            ap_dict = self.parse_pdf(pdf_content=self.pdf_parsed)
            grb_obj.apertures = deepcopy(ap_dict)

            poly_buff = []
            for ap in ap_dict:
                for k in ap_dict[ap]:
                    if k == 'solid_geometry':
                        poly_buff += ap_dict[ap][k]

            poly_buff = unary_union(poly_buff)
            poly_buff = poly_buff.buffer(0.0000001)
            poly_buff = poly_buff.buffer(-0.0000001)

            grb_obj.solid_geometry = deepcopy(poly_buff)

        with self.app.proc_container.new(_("Opening PDF.")):

            ret = self.app.new_object("gerber", new_name, obj_init, autoselected=False)
            if ret == 'fail':
                self.app.inform.emit(_('[ERROR_NOTCL] Open PDF file failed.'))
                return

            # Register recent file
            self.app.file_opened.emit("gerber", new_name)

            # GUI feedback
            self.app.inform.emit(_("[success] Opened: %s") % filename)

    def parse_pdf(self, pdf_content):
        path = dict()
        path['lines'] = []      # it's a list of lines subpaths
        path['bezier'] = []     # it's a list of bezier arcs subpaths
        path['rectangle'] = []  # it's a list of rectangle subpaths

        subpath = dict()
        subpath['lines'] = []      # it's a list of points
        subpath['bezier'] = []     # it's a list of sublists each like this [start, c1, c2, stop]
        subpath['rectangle'] = []  # it's a list of sublists of points

        # store the start point (when 'm' command is encountered)
        current_subpath = None

        # set True when 'h' command is encountered (close path)
        close_path = False

        start_point = None
        current_point = None
        size = 0

        # initial values for the transformations, in case they are not encountered in the PDF file
        offset_geo = [0, 0]
        scale_geo = [1, 1]

        c_offset_f= [0, 0]
        c_scale_f = [1, 1]

        # initial aperture
        aperture = 10

        # store the apertures here
        apertures_dict = {}

        # it seems that first transform apply to the whole PDF; signal here if it's first
        first_transform = True

        line_nr = 0
        lines = pdf_content.splitlines()

        for pline in lines:
            line_nr += 1
            log.debug("line %d: %s" % (line_nr, pline))

            # TRANSFORMATIONS DETECTION #

            # # Detect Scale transform
            # match = self.scale_re.search(pline)
            # if match:
            #     log.debug(
            #         "ToolPDF.parse_pdf() --> SCALE transformation found on line: %s --> %s" % (line_nr, pline))
            #     if first_transform:
            #         first_transform = False
            #         c_scale_f = [float(match.group(1)), float(match.group(2))]
            #     else:
            #         scale_geo = [float(match.group(1)), float(match.group(2))]
            #     continue

            # # Detect Offset transform
            # match = self.offset_re.search(pline)
            # if match:
            #     log.debug(
            #         "ToolPDF.parse_pdf() --> OFFSET transformation found on line: %s --> %s" % (line_nr, pline))
            #     offset_geo = [float(match.group(1)), float(match.group(2))]
            #     continue

            # Detect combined transformation. Must be always the last from transformations to be checked.
            match = self.combined_transform_re.search(pline)
            if match:
                # transformation = TRANSLATION (OFFSET)
                if (float(match.group(2)) == 0 and float(match.group(3)) == 0) and \
                        (float(match.group(5)) != 0 or float(match.group(6)) != 0):
                    log.debug(
                        "ToolPDF.parse_pdf() --> OFFSET transformation found on line: %s --> %s" % (line_nr, pline))
                    if first_transform:
                        c_offset_f = [float(match.group(5)), float(match.group(6))]
                    else:
                        offset_geo = [float(match.group(5)), float(match.group(6))]

                # transformation = SCALING
                if float(match.group(1)) != 1 and float(match.group(4)) != 1:
                    log.debug(
                        "ToolPDF.parse_pdf() --> SCALE transformation found on line: %s --> %s" % (line_nr, pline))
                    if first_transform:
                        c_scale_f = [float(match.group(1)), float(match.group(4))]
                    else:
                        scale_geo = [float(match.group(1)), float(match.group(4))]

                if first_transform:
                    first_transform = False
                continue

            # PATH CONSTRUCTION #

            # Start SUBPATH
            match = self.start_subpath_re.search(pline)
            if match:
                # we just started a subpath so we mark it as not closed yet
                close_path = False

                # init subpaths
                subpath['lines'] = []
                subpath['bezier'] = []
                subpath['rectangle'] = []

                # detect start point to move to
                x = float(match.group(1)) + offset_geo[0]
                y = float(match.group(2)) + offset_geo[1]
                pt = (x * self.point_to_unit_factor * scale_geo[0] * c_scale_f[0],
                      y * self.point_to_unit_factor * scale_geo[1] * c_scale_f[1])
                start_point = pt

                # add the start point to subpaths
                subpath['lines'].append(start_point)
                # subpath['bezier'].append(start_point)
                subpath['rectangle'].append(start_point)
                current_point = start_point
                continue

            # Draw Line
            match = self.draw_line_re.search(pline)
            if match:
                current_subpath = 'lines'
                x = float(match.group(1)) + offset_geo[0]
                y = float(match.group(2)) + offset_geo[1]
                pt = (x * self.point_to_unit_factor * scale_geo[0] * c_scale_f[0],
                      y * self.point_to_unit_factor * scale_geo[1] * c_scale_f[1])
                subpath['lines'].append(pt)
                current_point = pt
                continue

            # Draw Bezier 'c'
            match = self.draw_arc_3pt_re.search(pline)
            if match:
                current_subpath = 'bezier'
                start = current_point
                x = float(match.group(1)) + offset_geo[0]
                y = float(match.group(2)) + offset_geo[1]
                c1 = (x * self.point_to_unit_factor * scale_geo[0] * c_scale_f[0],
                      y * self.point_to_unit_factor * scale_geo[1] * c_scale_f[1])
                x = float(match.group(3)) + offset_geo[0]
                y = float(match.group(4)) + offset_geo[1]
                c2 = (x * self.point_to_unit_factor * scale_geo[0] * c_scale_f[0],
                      y * self.point_to_unit_factor * scale_geo[1] * c_scale_f[1])
                x = float(match.group(5)) + offset_geo[0]
                y = float(match.group(6)) + offset_geo[1]
                stop = (x * self.point_to_unit_factor * scale_geo[0] * c_scale_f[0],
                        y * self.point_to_unit_factor * scale_geo[1] * c_scale_f[1])

                subpath['bezier'].append([start, c1, c2, stop])
                current_point = stop
                continue

            # Draw Bezier 'v'
            match = self.draw_arc_2pt_c1start_re.search(pline)
            if match:
                current_subpath = 'bezier'
                start = current_point
                x = float(match.group(1)) + offset_geo[0]
                y = float(match.group(2)) + offset_geo[1]
                c2 = (x * self.point_to_unit_factor * scale_geo[0] * c_scale_f[0],
                      y * self.point_to_unit_factor * scale_geo[1] * c_scale_f[1])
                x = float(match.group(3)) + offset_geo[0]
                y = float(match.group(4)) + offset_geo[1]
                stop = (x * self.point_to_unit_factor * scale_geo[0] * c_scale_f[0],
                        y * self.point_to_unit_factor * scale_geo[1] * c_scale_f[1])

                subpath['bezier'].append([start, start, c2, stop])
                current_point = stop
                continue

            # Draw Bezier 'y'
            match = self.draw_arc_2pt_c2stop_re.search(pline)
            if match:
                start = current_point
                x = float(match.group(1)) + offset_geo[0]
                y = float(match.group(2)) + offset_geo[1]
                c1 = (x * self.point_to_unit_factor * scale_geo[0] * c_scale_f[0],
                      y * self.point_to_unit_factor * scale_geo[1] * c_scale_f[1])
                x = float(match.group(3)) + offset_geo[0]
                y = float(match.group(4)) + offset_geo[1]
                stop = (x * self.point_to_unit_factor * scale_geo[0] * c_scale_f[0],
                        y * self.point_to_unit_factor * scale_geo[1] * c_scale_f[1])

                subpath['bezier'].append([start, c1, stop, stop])
                print(subpath['bezier'])
                current_point = stop
                continue

            # Draw RECTANGLE
            match = self.rect_re.search(pline)
            if match:
                current_subpath = 'rectangle'
                x = (float(match.group(1)) + offset_geo[0]) * self.point_to_unit_factor * scale_geo[0] * c_scale_f[0]
                y = (float(match.group(2)) + offset_geo[1]) * self.point_to_unit_factor * scale_geo[1] * c_scale_f[1]
                width = (float(match.group(3)) + offset_geo[0]) * \
                        self.point_to_unit_factor * scale_geo[0] * c_scale_f[0]
                height = (float(match.group(4)) + offset_geo[1]) * \
                         self.point_to_unit_factor * scale_geo[1] * c_scale_f[1]
                pt1 = (x, y)
                pt2 = (x+width, y)
                pt3 = (x+width, y+height)
                pt4 = (x, y+height)
                # TODO: I'm not sure if rectangles are a subpath in themselves that autoclose
                subpath['rectangle'] += [pt1, pt2, pt3, pt4, pt1]
                current_point = pt1
                continue

            # Detect clipping path set
            # ignore this and delete the current subpath
            match = self.clip_path_re.search(pline)
            if match:
                subpath['lines'] = []
                subpath['bezier'] = []
                subpath['rectangle'] = []
                # it measns that we've already added the subpath to path and we need to delete it
                # clipping path is usually either rectangle or lines
                if close_path is True:
                    close_path = False
                    if current_subpath == 'lines':
                        path['lines'].pop(-1)
                    if current_subpath == 'rectangle':
                        path['rectangle'].pop(-1)
                continue

            # Close SUBPATH
            match = self.end_subpath_re.search(pline)
            if match:
                close_path = True
                if current_subpath == 'lines':
                    subpath['lines'].append(start_point)
                    # since we are closing the subpath add it to the path, a path may have chained subpaths
                    path['lines'].append(copy(subpath['lines']))
                    subpath['lines'] = []
                elif current_subpath == 'bezier':
                    # subpath['bezier'].append(start_point)
                    # since we are closing the subpath add it to the path, a path may have chained subpaths
                    path['bezier'].append(copy(subpath['bezier']))
                    subpath['bezier'] = []
                elif current_subpath == 'rectangle':
                    subpath['rectangle'].append(start_point)
                    # since we are closing the subpath add it to the path, a path may have chained subpaths
                    path['rectangle'].append(copy(subpath['rectangle']))
                    subpath['rectangle'] = []
                continue

            # PATH PAINTING #

            # Detect Stroke width / aperture
            match = self.strokewidth_re.search(pline)
            if match:
                size = float(match.group(1))
                # flag = 0
                #
                # if not apertures_dict:
                #     apertures_dict[str(aperture)] = dict()
                #     apertures_dict[str(aperture)]['size'] = size
                #     apertures_dict[str(aperture)]['type'] = 'C'
                #     apertures_dict[str(aperture)]['solid_geometry'] = []
                # else:
                #     for k in apertures_dict:
                #         if size == apertures_dict[k]['size']:
                #             flag = 1
                #             break
                #     if flag == 0:
                #         aperture += 1
                #         apertures_dict[str(aperture)] = dict()
                #         apertures_dict[str(aperture)]['size'] = size
                #         apertures_dict[str(aperture)]['type'] = 'C'
                #         apertures_dict[str(aperture)]['solid_geometry'] = []
                continue

            # Detect No_Op command, ignore the current subpath
            match = self.no_op_re.search(pline)
            if match:
                subpath['lines'] = []
                subpath['bezier'] = []
                subpath['rectangle'] = []
                continue

            # Stroke the path
            match = self.stroke_path__re.search(pline)
            if match:
                # scale the size here; some PDF printers apply transformation after the size is declared
                applied_size = size * scale_geo[0] * c_scale_f[0] * self.point_to_unit_factor

                path_geo = list()
                if current_subpath == 'lines':
                    if path['lines']:
                        for subp in path['lines']:
                            geo = copy(subp)
                            geo = LineString(geo).buffer((float(applied_size) / 2), resolution=self.step_per_circles)
                            path_geo.append(geo)
                        # the path was painted therefore initialize it
                        path['lines'] = []
                    else:
                        geo = copy(subpath['lines'])
                        geo = LineString(geo).buffer((float(applied_size) / 2), resolution=self.step_per_circles)
                        path_geo.append(geo)
                        subpath['lines'] = []

                if current_subpath == 'bezier':
                    if path['bezier']:
                        for subp in path['bezier']:
                            geo = []
                            for b in subp:
                                geo += self.bezier_to_points(start=b[0], c1=b[1], c2=b[2], stop=b[3])
                            geo = LineString(geo).buffer((float(applied_size) / 2), resolution=self.step_per_circles)
                            path_geo.append(geo)
                        # the path was painted therefore initialize it
                        path['bezier'] = []
                    else:
                        geo = []
                        for b in subpath['bezier']:
                            geo += self.bezier_to_points(start=b[0], c1=b[1], c2=b[2], stop=b[3])
                        geo = LineString(geo).buffer((float(applied_size) / 2), resolution=self.step_per_circles)
                        path_geo.append(geo)
                        subpath['bezier'] = []

                if current_subpath == 'rectangle':
                    if path['rectangle']:
                        for subp in path['rectangle']:
                            geo = copy(subp)
                            geo = LineString(geo).buffer((float(applied_size) / 2), resolution=self.step_per_circles)
                            path_geo.append(geo)
                        # the path was painted therefore initialize it
                        path['rectangle'] = []
                    else:
                        geo = copy(subpath['rectangle'])
                        geo = LineString(geo).buffer((float(applied_size) / 2), resolution=self.step_per_circles)
                        path_geo.append(geo)
                        subpath['rectangle'] = []

                try:
                    apertures_dict[str(aperture)]['solid_geometry'] += path_geo
                except KeyError:
                    # in case there is no stroke width yet therefore no aperture
                    apertures_dict[str(aperture)] = {}
                    apertures_dict[str(aperture)]['size'] = applied_size
                    apertures_dict[str(aperture)]['type'] = 'C'
                    apertures_dict[str(aperture)]['solid_geometry'] = []
                    apertures_dict[str(aperture)]['solid_geometry'] += path_geo

                continue

            # Fill the path
            match = self.fill_path_re.search(pline)
            if match:
                # scale the size here; some PDF printers apply transformation after the size is declared
                applied_size = size * scale_geo[0] * c_scale_f[0] * self.point_to_unit_factor

                path_geo = list()
                if current_subpath == 'lines':
                    if path['lines']:
                        for subp in path['lines']:
                            geo = copy(subp)
                            # close the subpath if it was not closed already
                            if close_path is False:
                                geo.append(geo[0])
                            geo_el = Polygon(geo).buffer(0.0000001, resolution=self.step_per_circles)
                            path_geo.append(geo_el)
                        # the path was painted therefore initialize it
                        path['lines'] = []
                    else:
                        geo = copy(subpath['lines'])
                        # close the subpath if it was not closed already
                        if close_path is False:
                            geo.append(start_point)
                        geo_el = Polygon(geo).buffer(0.0000001, resolution=self.step_per_circles)
                        path_geo.append(geo_el)
                        subpath['lines'] = []

                if current_subpath == 'bezier':
                    geo = []
                    if path['bezier']:
                        for subp in path['bezier']:
                            for b in subp:
                                geo += self.bezier_to_points(start=b[0], c1=b[1], c2=b[2], stop=b[3])
                                # close the subpath if it was not closed already
                                if close_path is False:
                                    geo.append(geo[0])
                                geo_el = Polygon(geo).buffer(0.0000001, resolution=self.step_per_circles)
                                path_geo.append(geo_el)
                        # the path was painted therefore initialize it
                        path['bezier'] = []
                    else:
                        for b in subpath['bezier']:
                            geo += self.bezier_to_points(start=b[0], c1=b[1], c2=b[2], stop=b[3])
                        if close_path is False:
                            geo.append(start_point)
                        geo_el = Polygon(geo).buffer(0.0000001, resolution=self.step_per_circles)
                        path_geo.append(geo_el)
                        subpath['bezier'] = []

                if current_subpath == 'rectangle':
                    if path['rectangle']:
                        for subp in path['rectangle']:
                            geo = copy(subp)
                            # close the subpath if it was not closed already
                            if close_path is False:
                                geo.append(geo[0])
                            geo_el = Polygon(geo).buffer(0.0000001, resolution=self.step_per_circles)
                            path_geo.append(geo_el)
                        # the path was painted therefore initialize it
                        path['rectangle'] = []
                    else:
                        geo = copy(subpath['rectangle'])
                        # close the subpath if it was not closed already
                        if close_path is False:
                            geo.append(start_point)
                        geo_el = Polygon(geo).buffer(0.0000001, resolution=self.step_per_circles)
                        path_geo.append(geo_el)
                        subpath['rectangle'] = []

                # we finished painting and also closed the path if it was the case
                close_path = True

                try:
                    apertures_dict['0']['solid_geometry'] += path_geo
                except KeyError:
                    # in case there is no stroke width yet therefore no aperture
                    apertures_dict['0'] = {}
                    apertures_dict['0']['size'] = applied_size
                    apertures_dict['0']['type'] = 'C'
                    apertures_dict['0']['solid_geometry'] = []
                    apertures_dict['0']['solid_geometry'] += path_geo
                continue

            # fill and stroke the path
            match = self.fill_stroke_path_re.search(pline)
            if match:
                # scale the size here; some PDF printers apply transformation after the size is declared
                applied_size = size * scale_geo[0] * c_scale_f[0] * self.point_to_unit_factor

                path_geo = list()
                if current_subpath == 'lines':
                    if path['lines']:
                        # fill
                        for subp in path['lines']:
                            geo = copy(subp)
                            # close the subpath if it was not closed already
                            if close_path is False:
                                geo.append(geo[0])
                            geo_el = Polygon(geo).buffer(0.0000001, resolution=self.step_per_circles)
                            path_geo.append(geo_el)
                        # stroke
                        for subp in path['lines']:
                            geo = copy(subp)
                            geo = LineString(geo).buffer((float(applied_size) / 2), resolution=self.step_per_circles)
                            path_geo.append(geo)
                        # the path was painted therefore initialize it
                        path['lines'] = []
                    else:
                        # fill
                        geo = copy(subpath['lines'])
                        # close the subpath if it was not closed already
                        if close_path is False:
                            geo.append(start_point)
                        geo_el = Polygon(geo).buffer(0.0000001, resolution=self.step_per_circles)
                        path_geo.append(geo_el)
                        # stroke
                        geo = copy(subpath['lines'])
                        geo = LineString(geo).buffer((float(applied_size) / 2), resolution=self.step_per_circles)
                        path_geo.append(geo)
                        subpath['lines'] = []
                        subpath['lines'] = []

                if current_subpath == 'bezier':
                    geo = []
                    if path['bezier']:
                        # fill
                        for subp in path['bezier']:
                            for b in subp:
                                geo += self.bezier_to_points(start=b[0], c1=b[1], c2=b[2], stop=b[3])
                                # close the subpath if it was not closed already
                                if close_path is False:
                                    geo.append(geo[0])
                                geo_el = Polygon(geo).buffer(0.0000001, resolution=self.step_per_circles)
                                path_geo.append(geo_el)
                        # stroke
                        for subp in path['bezier']:
                            geo = []
                            for b in subp:
                                geo += self.bezier_to_points(start=b[0], c1=b[1], c2=b[2], stop=b[3])
                            geo = LineString(geo).buffer((float(applied_size) / 2), resolution=self.step_per_circles)
                            path_geo.append(geo)
                        # the path was painted therefore initialize it
                        path['bezier'] = []
                    else:
                        # fill
                        for b in subpath['bezier']:
                            geo += self.bezier_to_points(start=b[0], c1=b[1], c2=b[2], stop=b[3])
                        if close_path is False:
                            geo.append(start_point)
                        geo_el = Polygon(geo).buffer(0.0000001, resolution=self.step_per_circles)
                        path_geo.append(geo_el)
                        # stroke
                        geo = []
                        for b in subpath['bezier']:
                            geo += self.bezier_to_points(start=b[0], c1=b[1], c2=b[2], stop=b[3])
                        geo = LineString(geo).buffer((float(applied_size) / 2), resolution=self.step_per_circles)
                        path_geo.append(geo)
                        subpath['bezier'] = []

                if current_subpath == 'rectangle':
                    if path['rectangle']:
                        # fill
                        for subp in path['rectangle']:
                            geo = copy(subp)
                            # close the subpath if it was not closed already
                            if close_path is False:
                                geo.append(geo[0])
                            geo_el = Polygon(geo).buffer(0.0000001, resolution=self.step_per_circles)
                            path_geo.append(geo_el)
                        # stroke
                        for subp in path['rectangle']:
                            geo = copy(subp)
                            geo = LineString(geo).buffer((float(applied_size) / 2), resolution=self.step_per_circles)
                            path_geo.append(geo)
                        # the path was painted therefore initialize it
                        path['rectangle'] = []
                    else:
                        # fill
                        geo = copy(subpath['rectangle'])
                        # close the subpath if it was not closed already
                        if close_path is False:
                            geo.append(start_point)
                        geo_el = Polygon(geo).buffer(0.0000001, resolution=self.step_per_circles)
                        path_geo.append(geo_el)
                        # stroke
                        geo = copy(subpath['rectangle'])
                        geo = LineString(geo).buffer((float(applied_size) / 2), resolution=self.step_per_circles)
                        path_geo.append(geo)
                        subpath['rectangle'] = []

                # we finished painting and also closed the path if it was the case
                close_path = True

                try:
                    apertures_dict['0']['solid_geometry'] += path_geo
                except KeyError:
                    # in case there is no stroke width yet therefore no aperture
                    apertures_dict['0'] = {}
                    apertures_dict['0']['size'] = applied_size
                    apertures_dict['0']['type'] = 'C'
                    apertures_dict['0']['solid_geometry'] = []
                    apertures_dict['0']['solid_geometry'] += path_geo
                continue
        return apertures_dict

    def bezier_to_points(self, start, c1, c2, stop):
        """
        # Equation Bezier, page 184 PDF 1.4 reference
        # https://www.adobe.com/content/dam/acom/en/devnet/pdf/pdfs/pdf_reference_archives/PDFReference.pdf
        # Given the coordinates of the four points, the curve is generated by varying the parameter t from 0.0 to 1.0
        # in the following equation:
        # R(t) = P0*(1 - t) ** 3 + P1*3*t*(1 - t) ** 2 + P2 * 3*(1 - t) * t ** 2  + P3*t ** 3
        # When t = 0.0, the value from the function coincides with the current point P0; when t = 1.0, R(t) coincides
        # with the final point P3. Intermediate values of t generate intermediate points along the curve.
        # The curve does not, in general, pass through the two control points P1 and P2

        :return: LineString geometry
        """

        # here we store the geometric points
        points = []

        nr_points = np.arange(0.0, 1.0, (1 / self.step_per_circles))
        for t in nr_points:
            term_p0 = (1 - t) ** 3
            term_p1 = 3 * t * (1 - t) ** 2
            term_p2 = 3 * (1 - t) * t ** 2
            term_p3 = t ** 3

            x = start[0] * term_p0 + c1[0] * term_p1 + c2[0] * term_p2 + stop[0] * term_p3
            y = start[1] * term_p0 + c1[1] * term_p1 + c2[1] * term_p2 + stop[1] * term_p3
            points.append([x, y])

        return points

    # def bezier_to_circle(self, path):
    #     lst = []
    #     for el in range(len(path)):
    #         if type(path) is list:
    #             for coord in path[el]:
    #                 lst.append(coord)
    #         else:
    #             lst.append(el)
    #
    #     if lst:
    #         minx = min(lst, key=lambda t: t[0])[0]
    #         miny = min(lst, key=lambda t: t[1])[1]
    #         maxx = max(lst, key=lambda t: t[0])[0]
    #         maxy = max(lst, key=lambda t: t[1])[1]
    #         center = (maxx-minx, maxy-miny)
    #         radius = (maxx-minx) / 2
    #         return [center, radius]
    #
    # def circle_to_points(self, center, radius):
    #     geo = Point(center).buffer(radius, resolution=self.step_per_circles)
    #     return LineString(list(geo.exterior.coords))
    #
