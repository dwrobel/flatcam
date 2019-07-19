# ########################################################## ##
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 4/23/2019                                          #
# MIT Licence                                              #
# ########################################################## ##

from FlatCAMTool import FlatCAMTool
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import cascaded_union, unary_union

from FlatCAMObj import *

import math
from copy import copy, deepcopy
import numpy as np

import zlib
import re
import time

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

        # detect stroke color change; it means a new object to be created
        self.stroke_color_re = re.compile(r'^\s*(\d+\.?\d*) (\d+\.?\d*) (\d+\.?\d*)\s*RG$')

        # detect fill color change; we check here for white color (transparent geometry);
        # if detected we create an Excellon from it
        self.fill_color_re = re.compile(r'^\s*(\d+\.?\d*) (\d+\.?\d*) (\d+\.?\d*)\s*rg$')

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
        # self.offset_re = re.compile(r'^1\.?0*\s0?\.?0*\s0?\.?0*\s1\.?0*\s(-?\d+\.?\d*)\s(-?\d+\.?\d*)\s*cm$')
        # detect scale transformation. Pattern: (factor_x) (0) (0) (factor_y) (0) (0)
        # self.scale_re = re.compile(r'^q? (-?\d+\.?\d*) 0\.?0* 0\.?0* (-?\d+\.?\d*) 0\.?0* 0\.?0*\s+cm$')
        # detect combined transformation. Should always be the last
        self.combined_transform_re = re.compile(r'^(q)?\s*(-?\d+\.?\d*) (-?\d+\.?\d*) (-?\d+\.?\d*) (-?\d+\.?\d*) '
                                                r'(-?\d+\.?\d*) (-?\d+\.?\d*)\s+cm$')

        # detect clipping path
        self.clip_path_re = re.compile(r'^W[*]? n?$')

        # detect save graphic state in graphic stack
        self.save_gs_re = re.compile(r'^q.*?$')

        # detect restore graphic state from graphic stack
        self.restore_gs_re = re.compile(r'^.*Q.*$')

        # graphic stack where we save parameters like transformation, line_width
        self.gs = dict()
        # each element is a list composed of sublist elements
        # (each sublist has 2 lists each having 2 elements: first is offset like:
        # offset_geo = [off_x, off_y], second element is scale list with 2 elements, like: scale_geo = [sc_x, sc_yy])
        self.gs['transform'] = []
        self.gs['line_width'] = []   # each element is a float

        self.pdf_decompressed = {}

        # key = file name and extension
        # value is a dict to store the parsed content of the PDF
        self.pdf_parsed = {}

        # QTimer for periodic check
        self.check_thread = QtCore.QTimer()

        # Every time a parser is started we add a promise; every time a parser finished we remove a promise
        # when empty we start the layer rendering
        self.parsing_promises = []

        # conversion factor to INCH
        self.point_to_unit_factor = 0.01388888888

    def run(self, toggle=True):
        self.app.report_usage("ToolPDF()")

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
            # start the parsing timer with a period of 1 second
            self.periodic_check(1000)

            for filename in filenames:
                if filename != '':
                    self.app.worker_task.emit({'fcn': self.open_pdf,
                                               'params': [filename]})

    def open_pdf(self, filename):
        short_name = filename.split('/')[-1].split('\\')[-1]
        self.parsing_promises.append(short_name)
        self.pdf_parsed[short_name] = {}
        self.pdf_parsed[short_name]['pdf'] = {}
        self.pdf_parsed[short_name]['filename'] = filename

        self.pdf_decompressed[short_name] = ''

        # the UNITS in PDF files are points and here we set the factor to convert them to real units (either MM or INCH)
        if self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().upper() == 'MM':
            # 1 inch = 72 points => 1 point = 1 / 72 = 0.01388888888 inch = 0.01388888888 inch * 25.4 = 0.35277777778 mm
            self.point_to_unit_factor = 25.4 / 72
        else:
            # 1 inch = 72 points => 1 point = 1 / 72 = 0.01388888888 inch
            self.point_to_unit_factor = 1 / 72

        with self.app.proc_container.new(_("Parsing PDF file ...")):
            with open(filename, "rb") as f:
                pdf = f.read()

            stream_nr = 0
            for s in re.findall(self.stream_re, pdf):
                stream_nr += 1
                log.debug(" PDF STREAM: %d\n" % stream_nr)
                s = s.strip(b'\r\n')
                try:
                    self.pdf_decompressed[short_name] += (zlib.decompress(s).decode('UTF-8') + '\r\n')
                except Exception as e:
                    log.debug("ToolPDF.open_pdf().obj_init() --> %s" % str(e))

            self.pdf_parsed[short_name]['pdf'] = self.parse_pdf(pdf_content=self.pdf_decompressed[short_name])
            # we used it, now we delete it
            self.pdf_decompressed[short_name] = ''

        # removal from list is done in a multithreaded way therefore not always the removal can be done
        # try to remove until it's done
        try:
            while True:
                self.parsing_promises.remove(short_name)
                time.sleep(0.1)
        except Exception as e:
            log.debug("ToolPDF.open_pdf() --> %s" % str(e))
        self.app.inform.emit(_("[success] Opened: %s") % filename)

    def layer_rendering_as_excellon(self, filename, ap_dict, layer_nr):
        outname = filename.split('/')[-1].split('\\')[-1] + "_%s" % str(layer_nr)

        # store the points here until reconstitution:
        # keys are diameters and values are list of (x,y) coords
        points = {}

        def obj_init(exc_obj, app_obj):
            clear_geo = [geo_el['clear'] for geo_el in ap_dict['0']['geometry']]

            for geo in clear_geo:
                xmin, ymin, xmax, ymax = geo.bounds
                center = (((xmax - xmin) / 2) + xmin, ((ymax - ymin) / 2) + ymin)

                # for drill bits, even in INCH, it's enough 3 decimals
                correction_factor = 0.974
                dia = (xmax - xmin) * correction_factor
                dia = round(dia, 3)
                if dia in points:
                    points[dia].append(center)
                else:
                    points[dia] = [center]

            sorted_dia = sorted(points.keys())

            name_tool = 0
            for dia in sorted_dia:
                name_tool += 1

                # create tools dictionary
                spec = {"C": dia}
                spec['solid_geometry'] = []
                exc_obj.tools[str(name_tool)] = spec

                # create drill list of dictionaries
                for dia_points in points:
                    if dia == dia_points:
                        for pt in points[dia_points]:
                            exc_obj.drills.append({'point': Point(pt), 'tool': str(name_tool)})
                        break

            ret = exc_obj.create_geometry()
            if ret == 'fail':
                log.debug("Could not create geometry for Excellon object.")
                return "fail"
            for tool in exc_obj.tools:
                if exc_obj.tools[tool]['solid_geometry']:
                    return
            app_obj.inform.emit(_("[ERROR_NOTCL] No geometry found in file: %s") % outname)
            return "fail"

        with self.app.proc_container.new(_("Rendering PDF layer #%d ...") % int(layer_nr)):

            ret_val = self.app.new_object("excellon", outname, obj_init, autoselected=False)
            if ret_val == 'fail':
                self.app.inform.emit(_('[ERROR_NOTCL] Open PDF file failed.'))
                return
            # Register recent file
            self.app.file_opened.emit("excellon", filename)
            # GUI feedback
            self.app.inform.emit(_("[success] Rendered: %s") % outname)

    def layer_rendering_as_gerber(self, filename, ap_dict, layer_nr):
        outname = filename.split('/')[-1].split('\\')[-1] + "_%s" % str(layer_nr)

        def obj_init(grb_obj, app_obj):

            grb_obj.apertures = ap_dict

            poly_buff = []
            follow_buf = []
            for ap in grb_obj.apertures:
                for k in grb_obj.apertures[ap]:
                    if k == 'geometry':
                        for geo_el in ap_dict[ap][k]:
                            if 'solid' in geo_el:
                                poly_buff.append(geo_el['solid'])
                            if 'follow' in geo_el:
                                follow_buf.append(geo_el['follow'])
            poly_buff = unary_union(poly_buff)

            if '0' in grb_obj.apertures:
                global_clear_geo = []
                if 'geometry' in grb_obj.apertures['0']:
                    for geo_el in ap_dict['0']['geometry']:
                        if 'clear' in geo_el:
                            global_clear_geo.append(geo_el['clear'])

                if global_clear_geo:
                    solid = []
                    for apid in grb_obj.apertures:
                        if 'geometry' in grb_obj.apertures[apid]:
                            for elem in grb_obj.apertures[apid]['geometry']:
                                if 'solid' in elem:
                                    solid_geo = deepcopy(elem['solid'])
                                    for clear_geo in global_clear_geo:
                                        # Make sure that the clear_geo is within the solid_geo otherwise we loose
                                        # the solid_geometry. We want for clear_geometry just to cut into solid_geometry
                                        # not to delete it
                                        if clear_geo.within(solid_geo):
                                            solid_geo = solid_geo.difference(clear_geo)
                                        if solid_geo.is_empty:
                                            solid_geo = elem['solid']
                                    try:
                                        for poly in solid_geo:
                                            solid.append(poly)
                                    except TypeError:
                                        solid.append(solid_geo)
                    poly_buff = deepcopy(MultiPolygon(solid))

            follow_buf = unary_union(follow_buf)

            try:
                poly_buff = poly_buff.buffer(0.0000001)
            except ValueError:
                pass
            try:
                poly_buff = poly_buff.buffer(-0.0000001)
            except ValueError:
                pass

            grb_obj.solid_geometry = deepcopy(poly_buff)
            grb_obj.follow_geometry = deepcopy(follow_buf)

        with self.app.proc_container.new(_("Rendering PDF layer #%d ...") % int(layer_nr)):

            ret = self.app.new_object('gerber', outname, obj_init, autoselected=False)
            if ret == 'fail':
                self.app.inform.emit(_('[ERROR_NOTCL] Open PDF file failed.'))
                return
            # Register recent file
            self.app.file_opened.emit('gerber', filename)
            # GUI feedback
            self.app.inform.emit(_("[success] Rendered: %s") % outname)

    def periodic_check(self, check_period):
        """
        This function starts an QTimer and it will periodically check if parsing was done

        :param check_period: time at which to check periodically if all plots finished to be plotted
        :return:
        """

        # self.plot_thread = threading.Thread(target=lambda: self.check_plot_finished(check_period))
        # self.plot_thread.start()
        log.debug("ToolPDF --> Periodic Check started.")

        try:
            self.check_thread.stop()
        except TypeError:
            pass

        self.check_thread.setInterval(check_period)
        try:
            self.check_thread.timeout.disconnect(self.periodic_check_handler)
        except TypeError:
            pass

        self.check_thread.timeout.connect(self.periodic_check_handler)
        self.check_thread.start(QtCore.QThread.HighPriority)

    def periodic_check_handler(self):
        """
        If the parsing worker finished then start multithreaded rendering
        :return:
        """
        # log.debug("checking parsing --> %s" % str(self.parsing_promises))

        try:
            if not self.parsing_promises:
                self.check_thread.stop()
                # parsing finished start the layer rendering
                if self.pdf_parsed:
                    obj_to_delete = []
                    for object_name in self.pdf_parsed:
                        filename = deepcopy(self.pdf_parsed[object_name]['filename'])
                        pdf_content = deepcopy(self.pdf_parsed[object_name]['pdf'])
                        obj_to_delete.append(object_name)
                        for k in pdf_content:
                            ap_dict = pdf_content[k]
                            if ap_dict:
                                layer_nr = k
                                if k == 0:
                                    self.app.worker_task.emit({'fcn': self.layer_rendering_as_excellon,
                                                               'params': [filename, ap_dict, layer_nr]})
                                else:
                                    self.app.worker_task.emit({'fcn': self.layer_rendering_as_gerber,
                                                               'params': [filename, ap_dict, layer_nr]})
                    # delete the object already processed so it will not be processed again for other objects
                    # that were opened at the same time; like in drag & drop on GUI
                    for obj_name in obj_to_delete:
                        if obj_name in self.pdf_parsed:
                            self.pdf_parsed.pop(obj_name)

                log.debug("ToolPDF --> Periodic check finished.")
        except Exception:
            traceback.print_exc()

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

        # set True when 'h' command is encountered (close subpath)
        close_subpath = False

        start_point = None
        current_point = None
        size = 0

        # initial values for the transformations, in case they are not encountered in the PDF file
        offset_geo = [0, 0]
        scale_geo = [1, 1]

        # store the objects to be transformed into Gerbers
        object_dict = {}
        # will serve as key in the object_dict
        layer_nr = 1
        # create first object
        object_dict[layer_nr] = {}

        # store the apertures here
        apertures_dict = {}

        # initial aperture
        aperture = 10

        # store the apertures with clear geometry here
        # we are interested only in the circular geometry (drill holes) therefore we target only Bezier subpaths
        clear_apertures_dict = dict()
        # everything will be stored in the '0' aperture since we are dealing with clear polygons not strokes
        clear_apertures_dict['0'] = dict()
        clear_apertures_dict['0']['size'] = 0.0
        clear_apertures_dict['0']['type'] = 'C'
        clear_apertures_dict['0']['geometry'] = []

        # on stroke color change we create a new apertures dictionary and store the old one in a storage from where
        # it will be transformed into Gerber object
        old_color = [None, None, None]

        # signal that we have clear geometry and the geometry will be added to a special layer_nr = 0
        flag_clear_geo = False

        line_nr = 0
        lines = pdf_content.splitlines()

        for pline in lines:
            line_nr += 1
            log.debug("line %d: %s" % (line_nr, pline))

            # COLOR DETECTION / OBJECT DETECTION
            match = self.stroke_color_re.search(pline)
            if match:
                color = [float(match.group(1)), float(match.group(2)), float(match.group(3))]
                log.debug(
                    "ToolPDF.parse_pdf() --> STROKE Color change on line: %s --> RED=%f GREEN=%f BLUE=%f" %
                    (line_nr, color[0], color[1], color[2]))

                if color[0] == old_color[0] and color[1] == old_color[1] and color[2] == old_color[2]:
                    # same color, do nothing
                    continue
                else:
                    if apertures_dict:
                        object_dict[layer_nr] = deepcopy(apertures_dict)
                        apertures_dict.clear()
                        layer_nr += 1

                        object_dict[layer_nr] = dict()
                old_color = copy(color)
                # we make sure that the following geometry is added to the right storage
                flag_clear_geo = False
                continue

            # CLEAR GEOMETRY detection
            match = self.fill_color_re.search(pline)
            if match:
                fill_color = [float(match.group(1)), float(match.group(2)), float(match.group(3))]
                log.debug(
                    "ToolPDF.parse_pdf() --> FILL Color change on line: %s --> RED=%f GREEN=%f BLUE=%f" %
                    (line_nr, fill_color[0], fill_color[1], fill_color[2]))
                # if the color is white we are seeing 'clear_geometry' that can't be seen. It may be that those
                # geometries are actually holes from which we can make an Excellon file
                if fill_color[0] == 1 and fill_color[1] == 1 and fill_color[2] == 1:
                    flag_clear_geo = True
                else:
                    flag_clear_geo = False
                continue

            # TRANSFORMATIONS DETECTION #

            # Detect combined transformation.
            match = self.combined_transform_re.search(pline)
            if match:
                # detect save graphic stack event
                # sometimes they combine save_to_graphics_stack with the transformation on the same line
                if match.group(1) == 'q':
                    log.debug(
                        "ToolPDF.parse_pdf() --> Save to GS found on line: %s --> offset=[%f, %f] ||| scale=[%f, %f]" %
                        (line_nr, offset_geo[0], offset_geo[1], scale_geo[0], scale_geo[1]))

                    self.gs['transform'].append(deepcopy([offset_geo, scale_geo]))
                    self.gs['line_width'].append(deepcopy(size))

                # transformation = TRANSLATION (OFFSET)
                if (float(match.group(3)) == 0 and float(match.group(4)) == 0) and \
                        (float(match.group(6)) != 0 or float(match.group(7)) != 0):
                    log.debug(
                        "ToolPDF.parse_pdf() --> OFFSET transformation found on line: %s --> %s" % (line_nr, pline))

                    offset_geo[0] += float(match.group(6))
                    offset_geo[1] += float(match.group(7))
                    # log.debug("Offset= [%f, %f]" % (offset_geo[0], offset_geo[1]))

                # transformation = SCALING
                if float(match.group(2)) != 1 and float(match.group(5)) != 1:
                    log.debug(
                        "ToolPDF.parse_pdf() --> SCALE transformation found on line: %s --> %s" % (line_nr, pline))

                    scale_geo[0] *= float(match.group(2))
                    scale_geo[1] *= float(match.group(5))
                # log.debug("Scale= [%f, %f]" % (scale_geo[0], scale_geo[1]))

                continue

            # detect save graphic stack event
            match = self.save_gs_re.search(pline)
            if match:
                log.debug(
                    "ToolPDF.parse_pdf() --> Save to GS found on line: %s --> offset=[%f, %f] ||| scale=[%f, %f]" %
                    (line_nr, offset_geo[0], offset_geo[1], scale_geo[0], scale_geo[1]))
                self.gs['transform'].append(deepcopy([offset_geo, scale_geo]))
                self.gs['line_width'].append(deepcopy(size))

            # detect restore from graphic stack event
            match = self.restore_gs_re.search(pline)
            if match:
                try:
                    restored_transform = self.gs['transform'].pop(-1)
                    offset_geo = restored_transform[0]
                    scale_geo = restored_transform[1]
                except IndexError:
                    # nothing to remove
                    log.debug("ToolPDF.parse_pdf() --> Nothing to restore")
                    pass

                try:
                    size = self.gs['line_width'].pop(-1)
                except IndexError:
                    log.debug("ToolPDF.parse_pdf() --> Nothing to restore")
                    # nothing to remove
                    pass

                log.debug(
                    "ToolPDF.parse_pdf() --> Restore from GS found on line: %s --> "
                    "restored_offset=[%f, %f] ||| restored_scale=[%f, %f]" %
                    (line_nr, offset_geo[0], offset_geo[1], scale_geo[0], scale_geo[1]))
                # log.debug("Restored Offset= [%f, %f]" % (offset_geo[0], offset_geo[1]))
                # log.debug("Restored Scale= [%f, %f]" % (scale_geo[0], scale_geo[1]))

            # PATH CONSTRUCTION #

            # Start SUBPATH
            match = self.start_subpath_re.search(pline)
            if match:
                # we just started a subpath so we mark it as not closed yet
                close_subpath = False

                # init subpaths
                subpath['lines'] = []
                subpath['bezier'] = []
                subpath['rectangle'] = []

                # detect start point to move to
                x = float(match.group(1)) + offset_geo[0]
                y = float(match.group(2)) + offset_geo[1]
                pt = (x * self.point_to_unit_factor * scale_geo[0],
                      y * self.point_to_unit_factor * scale_geo[1])
                start_point = pt

                # add the start point to subpaths
                subpath['lines'].append(start_point)
                # subpath['bezier'].append(start_point)
                # subpath['rectangle'].append(start_point)
                current_point = start_point
                continue

            # Draw Line
            match = self.draw_line_re.search(pline)
            if match:
                current_subpath = 'lines'
                x = float(match.group(1)) + offset_geo[0]
                y = float(match.group(2)) + offset_geo[1]
                pt = (x * self.point_to_unit_factor * scale_geo[0],
                      y * self.point_to_unit_factor * scale_geo[1])
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
                c1 = (x * self.point_to_unit_factor * scale_geo[0],
                      y * self.point_to_unit_factor * scale_geo[1])
                x = float(match.group(3)) + offset_geo[0]
                y = float(match.group(4)) + offset_geo[1]
                c2 = (x * self.point_to_unit_factor * scale_geo[0],
                      y * self.point_to_unit_factor * scale_geo[1])
                x = float(match.group(5)) + offset_geo[0]
                y = float(match.group(6)) + offset_geo[1]
                stop = (x * self.point_to_unit_factor * scale_geo[0],
                        y * self.point_to_unit_factor * scale_geo[1])

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
                c2 = (x * self.point_to_unit_factor * scale_geo[0],
                      y * self.point_to_unit_factor * scale_geo[1])
                x = float(match.group(3)) + offset_geo[0]
                y = float(match.group(4)) + offset_geo[1]
                stop = (x * self.point_to_unit_factor * scale_geo[0],
                        y * self.point_to_unit_factor * scale_geo[1])

                subpath['bezier'].append([start, start, c2, stop])
                current_point = stop
                continue

            # Draw Bezier 'y'
            match = self.draw_arc_2pt_c2stop_re.search(pline)
            if match:
                start = current_point
                x = float(match.group(1)) + offset_geo[0]
                y = float(match.group(2)) + offset_geo[1]
                c1 = (x * self.point_to_unit_factor * scale_geo[0],
                      y * self.point_to_unit_factor * scale_geo[1])
                x = float(match.group(3)) + offset_geo[0]
                y = float(match.group(4)) + offset_geo[1]
                stop = (x * self.point_to_unit_factor * scale_geo[0],
                        y * self.point_to_unit_factor * scale_geo[1])

                subpath['bezier'].append([start, c1, stop, stop])
                current_point = stop
                continue

            # Draw Rectangle 're'
            match = self.rect_re.search(pline)
            if match:
                current_subpath = 'rectangle'
                x = (float(match.group(1)) + offset_geo[0]) * self.point_to_unit_factor * scale_geo[0]
                y = (float(match.group(2)) + offset_geo[1]) * self.point_to_unit_factor * scale_geo[1]
                width = (float(match.group(3)) + offset_geo[0]) * self.point_to_unit_factor * scale_geo[0]
                height = (float(match.group(4)) + offset_geo[1]) * self.point_to_unit_factor * scale_geo[1]
                pt1 = (x, y)
                pt2 = (x+width, y)
                pt3 = (x+width, y+height)
                pt4 = (x, y+height)
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
                # it means that we've already added the subpath to path and we need to delete it
                # clipping path is usually either rectangle or lines
                if close_subpath is True:
                    close_subpath = False
                    if current_subpath == 'lines':
                        path['lines'].pop(-1)
                    if current_subpath == 'rectangle':
                        path['rectangle'].pop(-1)
                continue

            # Close SUBPATH
            match = self.end_subpath_re.search(pline)
            if match:
                close_subpath = True
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
                    # subpath['rectangle'].append(start_point)
                    # since we are closing the subpath add it to the path, a path may have chained subpaths
                    path['rectangle'].append(copy(subpath['rectangle']))
                    subpath['rectangle'] = []
                continue

            # PATH PAINTING #

            # Detect Stroke width / aperture
            match = self.strokewidth_re.search(pline)
            if match:
                size = float(match.group(1))
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
                applied_size = size * scale_geo[0] * self.point_to_unit_factor
                path_geo = list()
                if current_subpath == 'lines':
                    if path['lines']:
                        for subp in path['lines']:
                            geo = copy(subp)
                            try:
                                geo = LineString(geo).buffer((float(applied_size) / 2),
                                                             resolution=self.step_per_circles)
                                path_geo.append(geo)
                            except ValueError:
                                pass
                        # the path was painted therefore initialize it
                        path['lines'] = []
                    else:
                        geo = copy(subpath['lines'])
                        try:
                            geo = LineString(geo).buffer((float(applied_size) / 2), resolution=self.step_per_circles)
                            path_geo.append(geo)
                        except ValueError:
                            pass
                        subpath['lines'] = []

                if current_subpath == 'bezier':
                    if path['bezier']:
                        for subp in path['bezier']:
                            geo = []
                            for b in subp:
                                geo += self.bezier_to_points(start=b[0], c1=b[1], c2=b[2], stop=b[3])
                            try:
                                geo = LineString(geo).buffer((float(applied_size) / 2),
                                                             resolution=self.step_per_circles)
                                path_geo.append(geo)
                            except ValueError:
                                pass
                        # the path was painted therefore initialize it
                        path['bezier'] = []
                    else:
                        geo = []
                        for b in subpath['bezier']:
                            geo += self.bezier_to_points(start=b[0], c1=b[1], c2=b[2], stop=b[3])
                        try:
                            geo = LineString(geo).buffer((float(applied_size) / 2), resolution=self.step_per_circles)
                            path_geo.append(geo)
                        except ValueError:
                            pass
                        subpath['bezier'] = []

                if current_subpath == 'rectangle':
                    if path['rectangle']:
                        for subp in path['rectangle']:
                            geo = copy(subp)
                            try:
                                geo = LineString(geo).buffer((float(applied_size) / 2),
                                                             resolution=self.step_per_circles)
                                path_geo.append(geo)
                            except ValueError:
                                pass
                        # the path was painted therefore initialize it
                        path['rectangle'] = []
                    else:
                        geo = copy(subpath['rectangle'])
                        try:
                            geo = LineString(geo).buffer((float(applied_size) / 2), resolution=self.step_per_circles)
                            path_geo.append(geo)
                        except ValueError:
                            pass
                        subpath['rectangle'] = []

                # store the found geometry
                found_aperture = None
                if apertures_dict:
                    for apid in apertures_dict:
                        # if we already have an aperture with the current size (rounded to 5 decimals)
                        if apertures_dict[apid]['size'] == round(applied_size, 5):
                            found_aperture = apid
                            break

                    if found_aperture:
                        for pdf_geo in path_geo:
                            if isinstance(pdf_geo, MultiPolygon):
                                for poly in pdf_geo:
                                    new_el = dict()
                                    new_el['solid'] = poly
                                    new_el['follow'] = poly.exterior
                                    apertures_dict[copy(found_aperture)]['geometry'].append(deepcopy(new_el))
                            else:
                                new_el = dict()
                                new_el['solid'] = pdf_geo
                                new_el['follow'] = pdf_geo.exterior
                                apertures_dict[copy(found_aperture)]['geometry'].append(deepcopy(new_el))
                        found_aperture = None
                    else:
                        if str(aperture) in apertures_dict.keys():
                            aperture += 1
                        apertures_dict[str(aperture)] = {}
                        apertures_dict[str(aperture)]['size'] = round(applied_size, 5)
                        apertures_dict[str(aperture)]['type'] = 'C'
                        apertures_dict[str(aperture)]['geometry'] = []
                        for pdf_geo in path_geo:
                            if isinstance(pdf_geo, MultiPolygon):
                                for poly in pdf_geo:
                                    new_el = dict()
                                    new_el['solid'] = poly
                                    new_el['follow'] = poly.exterior
                                    apertures_dict[str(aperture)]['geometry'].append(deepcopy(new_el))
                            else:
                                new_el = dict()
                                new_el['solid'] = pdf_geo
                                new_el['follow'] = pdf_geo.exterior
                                apertures_dict[str(aperture)]['geometry'].append(deepcopy(new_el))
                else:
                    apertures_dict[str(aperture)] = {}
                    apertures_dict[str(aperture)]['size'] = round(applied_size, 5)
                    apertures_dict[str(aperture)]['type'] = 'C'
                    apertures_dict[str(aperture)]['geometry'] = []
                    for pdf_geo in path_geo:
                        if isinstance(pdf_geo, MultiPolygon):
                            for poly in pdf_geo:
                                new_el = dict()
                                new_el['solid'] = poly
                                new_el['follow'] = poly.exterior
                                apertures_dict[str(aperture)]['geometry'].append(deepcopy(new_el))
                        else:
                            new_el = dict()
                            new_el['solid'] = pdf_geo
                            new_el['follow'] = pdf_geo.exterior
                            apertures_dict[str(aperture)]['geometry'].append(deepcopy(new_el))

                continue

            # Fill the path
            match = self.fill_path_re.search(pline)
            if match:
                # scale the size here; some PDF printers apply transformation after the size is declared
                applied_size = size * scale_geo[0] * self.point_to_unit_factor
                path_geo = list()

                if current_subpath == 'lines':
                    if path['lines']:
                        for subp in path['lines']:
                            geo = copy(subp)
                            # close the subpath if it was not closed already
                            if close_subpath is False:
                                geo.append(geo[0])
                            try:
                                geo_el = Polygon(geo).buffer(0.0000001, resolution=self.step_per_circles)
                                path_geo.append(geo_el)
                            except ValueError:
                                pass
                        # the path was painted therefore initialize it
                        path['lines'] = []
                    else:
                        geo = copy(subpath['lines'])
                        # close the subpath if it was not closed already
                        if close_subpath is False:
                            geo.append(start_point)
                        try:
                            geo_el = Polygon(geo).buffer(0.0000001, resolution=self.step_per_circles)
                            path_geo.append(geo_el)
                        except ValueError:
                            pass
                        subpath['lines'] = []

                if current_subpath == 'bezier':
                    geo = []
                    if path['bezier']:
                        for subp in path['bezier']:
                            for b in subp:
                                geo += self.bezier_to_points(start=b[0], c1=b[1], c2=b[2], stop=b[3])
                                # close the subpath if it was not closed already
                                if close_subpath is False:
                                    geo.append(geo[0])
                                try:
                                    geo_el = Polygon(geo).buffer(0.0000001, resolution=self.step_per_circles)
                                    path_geo.append(geo_el)
                                except ValueError:
                                    pass
                        # the path was painted therefore initialize it
                        path['bezier'] = []
                    else:
                        for b in subpath['bezier']:
                            geo += self.bezier_to_points(start=b[0], c1=b[1], c2=b[2], stop=b[3])
                        if close_subpath is False:
                            geo.append(start_point)
                        try:
                            geo_el = Polygon(geo).buffer(0.0000001, resolution=self.step_per_circles)
                            path_geo.append(geo_el)
                        except ValueError:
                            pass
                        subpath['bezier'] = []

                if current_subpath == 'rectangle':
                    if path['rectangle']:
                        for subp in path['rectangle']:
                            geo = copy(subp)
                            # # close the subpath if it was not closed already
                            # if close_subpath is False and start_point is not None:
                            #     geo.append(start_point)
                            try:
                                geo_el = Polygon(geo).buffer(0.0000001, resolution=self.step_per_circles)
                                path_geo.append(geo_el)
                            except ValueError:
                                pass
                        # the path was painted therefore initialize it
                        path['rectangle'] = []
                    else:
                        geo = copy(subpath['rectangle'])
                        # # close the subpath if it was not closed already
                        # if close_subpath is False and start_point is not None:
                        #     geo.append(start_point)
                        try:
                            geo_el = Polygon(geo).buffer(0.0000001, resolution=self.step_per_circles)
                            path_geo.append(geo_el)
                        except ValueError:
                            pass
                        subpath['rectangle'] = []

                # we finished painting and also closed the path if it was the case
                close_subpath = True

                # in case that a color change to white (transparent) occurred
                if flag_clear_geo is True:
                    # if there was a fill color change we look for circular geometries from which we can make
                    # drill holes for the Excellon file
                    if current_subpath == 'bezier':
                        # if there are geometries in the list
                        if path_geo:
                            try:
                                for g in path_geo:
                                    new_el = dict()
                                    new_el['clear'] = g
                                    clear_apertures_dict['0']['geometry'].append(new_el)
                            except TypeError:
                                new_el = dict()
                                new_el['clear'] = path_geo
                                clear_apertures_dict['0']['geometry'].append(new_el)

                    # now that we finished searching for drill holes (this is not very precise because holes in the
                    # polygon pours may appear as drill too, but .. hey you can't have it all ...) we add
                    # clear_geometry
                    try:
                        for pdf_geo in path_geo:
                            if isinstance(pdf_geo, MultiPolygon):
                                for poly in pdf_geo:
                                    new_el = dict()
                                    new_el['clear'] = poly
                                    apertures_dict['0']['geometry'].append(deepcopy(new_el))
                            else:
                                new_el = dict()
                                new_el['clear'] = pdf_geo
                                apertures_dict['0']['geometry'].append(deepcopy(new_el))
                    except KeyError:
                        # in case there is no stroke width yet therefore no aperture
                        apertures_dict['0'] = {}
                        apertures_dict['0']['size'] = applied_size
                        apertures_dict['0']['type'] = 'C'
                        apertures_dict['0']['geometry'] = []
                        for pdf_geo in path_geo:
                            if isinstance(pdf_geo, MultiPolygon):
                                for poly in pdf_geo:
                                    new_el = dict()
                                    new_el['clear'] = poly
                                    apertures_dict['0']['geometry'].append(deepcopy(new_el))
                            else:
                                new_el = dict()
                                new_el['clear'] = pdf_geo
                                apertures_dict['0']['geometry'].append(deepcopy(new_el))
                else:
                    # else, add the geometry as usual
                    try:
                        for pdf_geo in path_geo:
                            if isinstance(pdf_geo, MultiPolygon):
                                for poly in pdf_geo:
                                    new_el = dict()
                                    new_el['solid'] = poly
                                    new_el['follow'] = poly.exterior
                                    apertures_dict['0']['geometry'].append(deepcopy(new_el))
                            else:
                                new_el = dict()
                                new_el['solid'] = pdf_geo
                                new_el['follow'] = pdf_geo.exterior
                                apertures_dict['0']['geometry'].append(deepcopy(new_el))
                    except KeyError:
                        # in case there is no stroke width yet therefore no aperture
                        apertures_dict['0'] = {}
                        apertures_dict['0']['size'] = applied_size
                        apertures_dict['0']['type'] = 'C'
                        apertures_dict['0']['geometry'] = []
                        for pdf_geo in path_geo:
                            if isinstance(pdf_geo, MultiPolygon):
                                for poly in pdf_geo:
                                    new_el = dict()
                                    new_el['solid'] = poly
                                    new_el['follow'] = poly.exterior
                                    apertures_dict['0']['geometry'].append(deepcopy(new_el))
                            else:
                                new_el = dict()
                                new_el['solid'] = pdf_geo
                                new_el['follow'] = pdf_geo.exterior
                                apertures_dict['0']['geometry'].append(deepcopy(new_el))
                    continue

            # Fill and Stroke the path
            match = self.fill_stroke_path_re.search(pline)
            if match:
                # scale the size here; some PDF printers apply transformation after the size is declared
                applied_size = size * scale_geo[0] * self.point_to_unit_factor
                path_geo = list()
                fill_geo = list()

                if current_subpath == 'lines':
                    if path['lines']:
                        # fill
                        for subp in path['lines']:
                            geo = copy(subp)
                            # close the subpath if it was not closed already
                            if close_subpath is False:
                                geo.append(geo[0])
                            try:
                                geo_el = Polygon(geo).buffer(0.0000001, resolution=self.step_per_circles)
                                fill_geo.append(geo_el)
                            except ValueError:
                                pass
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
                        if close_subpath is False:
                            geo.append(start_point)
                        try:
                            geo_el = Polygon(geo).buffer(0.0000001, resolution=self.step_per_circles)
                            fill_geo.append(geo_el)
                        except ValueError:
                            pass
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
                                if close_subpath is False:
                                    geo.append(geo[0])
                                try:
                                    geo_el = Polygon(geo).buffer(0.0000001, resolution=self.step_per_circles)
                                    fill_geo.append(geo_el)
                                except ValueError:
                                    pass
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
                        if close_subpath is False:
                            geo.append(start_point)
                        try:
                            geo_el = Polygon(geo).buffer(0.0000001, resolution=self.step_per_circles)
                            fill_geo.append(geo_el)
                        except ValueError:
                            pass
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
                            # # close the subpath if it was not closed already
                            # if close_subpath is False:
                            #     geo.append(geo[0])
                            try:
                                geo_el = Polygon(geo).buffer(0.0000001, resolution=self.step_per_circles)
                                fill_geo.append(geo_el)
                            except ValueError:
                                pass
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
                        # # close the subpath if it was not closed already
                        # if close_subpath is False:
                        #     geo.append(start_point)
                        try:
                            geo_el = Polygon(geo).buffer(0.0000001, resolution=self.step_per_circles)
                            fill_geo.append(geo_el)
                        except ValueError:
                            pass
                        # stroke
                        geo = copy(subpath['rectangle'])
                        geo = LineString(geo).buffer((float(applied_size) / 2), resolution=self.step_per_circles)
                        path_geo.append(geo)
                        subpath['rectangle'] = []

                # we finished painting and also closed the path if it was the case
                close_subpath = True

                # store the found geometry for stroking the path
                found_aperture = None
                if apertures_dict:
                    for apid in apertures_dict:
                        # if we already have an aperture with the current size (rounded to 5 decimals)
                        if apertures_dict[apid]['size'] == round(applied_size, 5):
                            found_aperture = apid
                            break

                    if found_aperture:
                        for pdf_geo in path_geo:
                            if isinstance(pdf_geo, MultiPolygon):
                                for poly in pdf_geo:
                                    new_el = dict()
                                    new_el['solid'] = poly
                                    new_el['follow'] = poly.exterior
                                    apertures_dict[copy(found_aperture)]['geometry'].append(deepcopy(new_el))
                            else:
                                new_el = dict()
                                new_el['solid'] = pdf_geo
                                new_el['follow'] = pdf_geo.exterior
                                apertures_dict[copy(found_aperture)]['geometry'].append(deepcopy(new_el))
                        found_aperture = None
                    else:
                        if str(aperture) in apertures_dict.keys():
                            aperture += 1
                        apertures_dict[str(aperture)] = {}
                        apertures_dict[str(aperture)]['size'] = round(applied_size, 5)
                        apertures_dict[str(aperture)]['type'] = 'C'
                        apertures_dict[str(aperture)]['geometry'] = []
                        for pdf_geo in path_geo:
                            if isinstance(pdf_geo, MultiPolygon):
                                for poly in pdf_geo:
                                    new_el = dict()
                                    new_el['solid'] = poly
                                    new_el['follow'] = poly.exterior
                                    apertures_dict[str(aperture)]['geometry'].append(deepcopy(new_el))
                            else:
                                new_el = dict()
                                new_el['solid'] = pdf_geo
                                new_el['follow'] = pdf_geo.exterior
                                apertures_dict[str(aperture)]['geometry'].append(deepcopy(new_el))
                else:
                    apertures_dict[str(aperture)] = {}
                    apertures_dict[str(aperture)]['size'] = round(applied_size, 5)
                    apertures_dict[str(aperture)]['type'] = 'C'
                    apertures_dict[str(aperture)]['geometry'] = []
                    for pdf_geo in path_geo:
                        if isinstance(pdf_geo, MultiPolygon):
                            for poly in pdf_geo:
                                new_el = dict()
                                new_el['solid'] = poly
                                new_el['follow'] = poly.exterior
                                apertures_dict[str(aperture)]['geometry'].append(deepcopy(new_el))
                        else:
                            new_el = dict()
                            new_el['solid'] = pdf_geo
                            new_el['follow'] = pdf_geo.exterior
                            apertures_dict[str(aperture)]['geometry'].append(deepcopy(new_el))

                # ############################################# ##
                # store the found geometry for filling the path #
                # ############################################# ##

                # in case that a color change to white (transparent) occurred
                if flag_clear_geo is True:
                    try:
                        for pdf_geo in path_geo:
                            if isinstance(pdf_geo, MultiPolygon):
                                for poly in fill_geo:
                                    new_el = dict()
                                    new_el['clear'] = poly
                                    apertures_dict['0']['geometry'].append(deepcopy(new_el))
                            else:
                                new_el = dict()
                                new_el['clear'] = pdf_geo
                                apertures_dict['0']['geometry'].append(deepcopy(new_el))
                    except KeyError:
                        # in case there is no stroke width yet therefore no aperture
                        apertures_dict['0'] = {}
                        apertures_dict['0']['size'] = round(applied_size, 5)
                        apertures_dict['0']['type'] = 'C'
                        apertures_dict['0']['geometry'] = []
                        for pdf_geo in fill_geo:
                            if isinstance(pdf_geo, MultiPolygon):
                                for poly in pdf_geo:
                                    new_el = dict()
                                    new_el['clear'] = poly
                                    apertures_dict['0']['geometry'].append(deepcopy(new_el))
                            else:
                                new_el = dict()
                                new_el['clear'] = pdf_geo
                                apertures_dict['0']['geometry'].append(deepcopy(new_el))
                else:
                    try:
                        for pdf_geo in path_geo:
                            if isinstance(pdf_geo, MultiPolygon):
                                for poly in fill_geo:
                                    new_el = dict()
                                    new_el['solid'] = poly
                                    new_el['follow'] = poly.exterior
                                    apertures_dict['0']['geometry'].append(deepcopy(new_el))
                            else:
                                new_el = dict()
                                new_el['solid'] = pdf_geo
                                new_el['follow'] = pdf_geo.exterior
                                apertures_dict['0']['geometry'].append(deepcopy(new_el))
                    except KeyError:
                        # in case there is no stroke width yet therefore no aperture
                        apertures_dict['0'] = {}
                        apertures_dict['0']['size'] = round(applied_size, 5)
                        apertures_dict['0']['type'] = 'C'
                        apertures_dict['0']['geometry'] = []
                        for pdf_geo in fill_geo:
                            if isinstance(pdf_geo, MultiPolygon):
                                for poly in pdf_geo:
                                    new_el = dict()
                                    new_el['solid'] = poly
                                    new_el['follow'] = poly.exterior
                                    apertures_dict['0']['geometry'].append(deepcopy(new_el))
                            else:
                                new_el = dict()
                                new_el['solid'] = pdf_geo
                                new_el['follow'] = pdf_geo.exterior
                                apertures_dict['0']['geometry'].append(deepcopy(new_el))

                continue

        # tidy up. copy the current aperture dict to the object dict but only if it is not empty
        if apertures_dict:
            object_dict[layer_nr] = deepcopy(apertures_dict)

        if clear_apertures_dict['0']['geometry']:
            object_dict[0] = deepcopy(clear_apertures_dict)

        # delete keys (layers) with empty values
        empty_layers = []
        for layer in object_dict:
            if not object_dict[layer]:
                empty_layers.append(layer)
        for x in empty_layers:
            if x in object_dict:
                object_dict.pop(x)

        return object_dict

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

        :return: A list of point coordinates tuples (x, y)
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
