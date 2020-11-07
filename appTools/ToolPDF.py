# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 4/23/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtCore

from appTool import AppTool

from appParsers.ParsePDF import PdfParser, grace
from shapely.geometry import Point, MultiPolygon
from shapely.ops import unary_union

from copy import deepcopy

import zlib
import re
import time
import logging
import traceback

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class ToolPDF(AppTool):
    """
    Parse a PDF file.
    Reference here: https://www.adobe.com/content/dam/acom/en/devnet/pdf/pdfs/pdf_reference_archives/PDFReference.pdf
    Return a list of geometries
    """
    toolName = _("PDF Import Tool")

    def __init__(self, app):
        AppTool.__init__(self, app)
        self.app = app
        self.decimals = self.app.decimals

        self.stream_re = re.compile(b'.*?FlateDecode.*?stream(.*?)endstream', re.S)

        self.pdf_decompressed = {}

        # key = file name and extension
        # value is a dict to store the parsed content of the PDF
        self.pdf_parsed = {}

        # QTimer for periodic check
        self.check_thread = QtCore.QTimer()

        # Every time a parser is started we add a promise; every time a parser finished we remove a promise
        # when empty we start the layer rendering
        self.parsing_promises = []

        self.parser = PdfParser(app=self.app)

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolPDF()")

        self.set_tool_ui()
        self.on_open_pdf_click()

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Ctrl+Q', **kwargs)

    def set_tool_ui(self):
        pass

    def on_open_pdf_click(self):
        """
        File menu callback for opening an PDF file.

        :return: None
        """

        self.app.defaults.report_usage("ToolPDF.on_open_pdf_click()")
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
            self.app.inform.emit('[WARNING_NOTCL] %s.' % _("Open PDF cancelled"))
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

        self.pdf_parsed[short_name] = {
            'pdf': {},
            'filename': filename
        }

        self.pdf_decompressed[short_name] = ''

        if self.app.abort_flag:
            # graceful abort requested by the user
            raise grace

        with self.app.proc_container.new(_("Parsing ...")):
            with open(filename, "rb") as f:
                pdf = f.read()

            stream_nr = 0
            for s in re.findall(self.stream_re, pdf):
                if self.app.abort_flag:
                    # graceful abort requested by the user
                    raise grace

                stream_nr += 1
                log.debug("PDF STREAM: %d\n" % stream_nr)
                s = s.strip(b'\r\n')
                try:
                    self.pdf_decompressed[short_name] += (zlib.decompress(s).decode('UTF-8') + '\r\n')
                except Exception as e:
                    self.app.inform.emit('[ERROR_NOTCL] %s: %s\n%s' % (_("Failed to open"), str(filename), str(e)))
                    log.debug("ToolPDF.open_pdf().obj_init() --> %s" % str(e))
                    return

            self.pdf_parsed[short_name]['pdf'] = self.parser.parse_pdf(pdf_content=self.pdf_decompressed[short_name])
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
        self.app.inform.emit('[success] %s: %s' % (_("Opened"),  str(filename)))

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
                tool = str(name_tool)

                exc_obj.tools[tool] = {
                    'tooldia': dia,
                    'drills': [],
                    'solid_geometry': []
                }

                # update the drill list
                for dia_points in points:
                    if dia == dia_points:
                        for pt in points[dia_points]:
                            exc_obj.tools[tool]['drills'].append(Point(pt))
                        break

            ret = exc_obj.create_geometry()
            if ret == 'fail':
                log.debug("Could not create geometry for Excellon object.")
                return "fail"

            for tool in exc_obj.tools:
                if exc_obj.tools[tool]['solid_geometry']:
                    return
            app_obj.inform.emit('[ERROR_NOTCL] %s: %s' % (_("No geometry found in file"), outname))
            return "fail"

        with self.app.proc_container.new(_("Rendering PDF layer #%d ...") % int(layer_nr)):

            ret_val = self.app.app_obj.new_object("excellon", outname, obj_init, autoselected=False)
            if ret_val == 'fail':
                self.app.inform.emit('[ERROR_NOTCL] %s' % _('Open PDF file failed.'))
                return
            # Register recent file
            self.app.file_opened.emit("excellon", filename)
            # GUI feedback
            self.app.inform.emit('[success] %s: %s' % (_("Rendered"),  outname))

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

            ret = self.app.app_obj.new_object('gerber', outname, obj_init, autoselected=False)
            if ret == 'fail':
                self.app.inform.emit('[ERROR_NOTCL] %s' % _('Open PDF file failed.'))
                return
            # Register recent file
            self.app.file_opened.emit('gerber', filename)
            # GUI feedback
            self.app.inform.emit('[success] %s: %s' % (_("Rendered"), outname))

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
        except (TypeError, AttributeError):
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
                log.debug("PDF --> start rendering")
                # parsing finished start the layer rendering
                if self.pdf_parsed:
                    obj_to_delete = []
                    for object_name in self.pdf_parsed:
                        if self.app.abort_flag:
                            # graceful abort requested by the user
                            raise grace

                        filename = deepcopy(self.pdf_parsed[object_name]['filename'])
                        pdf_content = deepcopy(self.pdf_parsed[object_name]['pdf'])
                        obj_to_delete.append(object_name)
                        for k in pdf_content:
                            if self.app.abort_flag:
                                # graceful abort requested by the user
                                raise grace

                            ap_dict = pdf_content[k]
                            print(k, ap_dict)
                            if ap_dict:
                                layer_nr = k
                                if k == 0:
                                    self.app.worker_task.emit({'fcn': self.layer_rendering_as_excellon,
                                                               'params': [filename, ap_dict, layer_nr]})
                                else:
                                    self.app.worker_task.emit({'fcn': self.layer_rendering_as_gerber,
                                                               'params': [filename, ap_dict, layer_nr]})
                    # delete the object already processed so it will not be processed again for other objects
                    # that were opened at the same time; like in drag & drop on appGUI
                    for obj_name in obj_to_delete:
                        if obj_name in self.pdf_parsed:
                            self.pdf_parsed.pop(obj_name)

                log.debug("ToolPDF --> Periodic check finished.")
        except Exception:
            traceback.print_exc()
