############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
############################################################

from FlatCAMTool import FlatCAMTool
from FlatCAMObj import *
import math
import numpy as np
import scipy.interpolate

import zlib
import re

import gettext
import FlatCAMTranslation as fcTranslate

fcTranslate.apply_language('strings')
import builtins
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ToolPDF(FlatCAMTool):
    '''
    Parse a PDF file.
    Reference here: https://www.adobe.com/content/dam/acom/en/devnet/pdf/pdfs/pdf_reference_archives/PDFReference.pdf
    Return a list of geometries
    '''
    toolName = _("PDF Import Tool")

    def __init__(self, app):
        FlatCAMTool.__init__(self, app)
        self.app = app
        self.step_per_circles = self.app.defaults["gerber_circle_steps"]

        self.stream_re = re.compile(b'.*?FlateDecode.*?stream(.*?)endstream', re.S)

        # detect 'w' command
        self.strokewidth_re = re.compile(r'^(\d+\.?\d*)\s*w$')
        # detect 're' command
        self.rect_re = re.compile(r'^(-?\d+\.?\d*)\s(-?\d+\.?\d*)\s(-?\d+\.?\d*)\s(-?\d+\.?\d*)\sre$')
        # detect 'm' command
        self.start_path_re = re.compile(r'(-?\d+\.?\d*)\s(-?\d+\.?\d*)\sm$')
        # detect 'l' command
        self.draw_line_re = re.compile(r'(-?\d+\.?\d*)\s(-?\d+\.?\d*)\sl')
        # detect 'c' command
        self.draw_arc_3pt_re = re.compile(r'(-?\d+\.?\d*)\s(-?\d+\.?\d*)\s(-?\d+\.?\d*)\s(-?\d+\.?\d*)\s(-?\d+\.?\d*)\s(-?\d+\.?\d*)\sc$')
        # detect 'v' command
        self.draw_arc_2pt_23_re = re.compile(r'(-?\d+\.?\d*)\s(-?\d+\.?\d*)\s(-?\d+\.?\d*)\s(-?\d+\.?\d*)\sv$')
        # detect 'y' command
        self.draw_arc_2pt_13_re = re.compile(r'(-?\d+\.?\d*)\s(-?\d+\.?\d*)\s(-?\d+\.?\d*)\s(-?\d+\.?\d*)\sy$')
        # detect 'h' command
        self.end_path_re = re.compile(r'^h$')


        self.pdf_parsed = ''

    def run(self, toggle=True):
        self.app.report_usage("ToolPDF()")

        # if toggle:
        #     # if the splitter is hidden, display it, else hide it but only if the current widget is the same
        #     if self.app.ui.splitter.sizes()[0] == 0:
        #         self.app.ui.splitter.setSizes([1, 1])
        #     else:
        #         try:
        #             if self.app.ui.tool_scroll_area.widget().objectName() == self.toolName:
        #                 self.app.ui.splitter.setSizes([0, 1])
        #         except AttributeError:
        #             pass
        # else:
        #     if self.app.ui.splitter.sizes()[0] == 0:
        #         self.app.ui.splitter.setSizes([1, 1])
        #
        # FlatCAMTool.run(self)

        self.set_tool_ui()
        self.on_open_pdf_click()

        # self.app.ui.notebook.setTabText(2, "PDF Tool")

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
                                                                   directory=self.app.get_last_folder(), filter=_filter_)
        except TypeError:
            filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Open PDF"), filter=_filter_)

        filenames = [str(filename) for filename in filenames]

        if len(filenames) == 0:
            self.app.inform.emit(_("[WARNING_NOTCL] Open PDF cancelled."))
        else:
            for filename in filenames:
                if filename != '':
                    self.app.worker_task.emit({'fcn': self.open_pdf,
                                           'params': [filename]})

    def open_pdf(self, filename):

        def obj_init(grb_obj, app_obj):
            with open(filename, "rb") as f:
                pdf = f.read()

            for s in re.findall(self.stream_re, pdf):
                s = s.strip(b'\r\n')
                try:
                    self.pdf_parsed += zlib.decompress(s).decode('UTF-8')
                except:
                    pass
            grb_obj.solid_geometry = [self.bezier_to_linestring(0, 0, 0, 0)]


        with self.app.proc_container.new(_("Opening PDF.")):
            # obj_init()
            self.parse_pdf()
            ret = self.app.new_object("geometry", "bla", obj_init, autoselected=False)
                # Register recent file
            self.app.file_opened.emit("geometry", "bla")
            # # Object name
            # name = outname or filename.split('/')[-1].split('\\')[-1]
            #
            # ret = self.new_object("excellon", name, obj_init, autoselected=False)
            # if ret == 'fail':
            #     self.inform.emit(_('[ERROR_NOTCL] Open Excellon file failed. Probable not an Excellon file.'))
            #     return
            #
            #     # Register recent file
            # self.file_opened.emit("excellon", filename)
            #
            # # GUI feedback
            # self.inform.emit(_("[success] Opened: %s") % filename)
            # # self.progress.emit(100)

    def parse_pdf(self):
        for pline in self.pdf_parsed:
            pass

    def bezier_to_linestring(self, start, stop, c1, c2):
        """
        From here: https://gis.stackexchange.com/questions/106937/python-library-or-algorithm-to-generate-arc-geometry-from-three-coordinate-pairs
        :return: LineString geometry
        """
        coords = np.array([[0, 0], [25, 10], [33, 39], [53, 53]])

        # equation Bezier, page 184 PDF 1.4 reference
        # https://www.adobe.com/content/dam/acom/en/devnet/pdf/pdfs/pdf_reference_archives/PDFReference.pdf
        # R(t) = P0*(1 - t) ** 3 + P1*3*t*(1 - 5) ** 2 + P2 * 3*(1 - t) * t ** 2  + P3*t ** 3

        domain = []
        i = 0
        while i <=1:
            domain.append(i)
        for i in domain:

        return even_line
