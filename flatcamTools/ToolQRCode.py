# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtCore

from FlatCAMTool import FlatCAMTool
from flatcamGUI.GUIElements import FCDoubleSpinner, EvalEntry, FCCheckBox
from camlib import *

from shapely.geometry import Point
from shapely.geometry.base import *

import math
import io
from datetime import datetime
import logging
import pyqrcode
from lxml import etree as ET

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class QRCode(FlatCAMTool):

    toolName = _("QRCode Tool")

    def __init__(self, app):
        FlatCAMTool.__init__(self, app)

        self.app = app
        self.canvas = self.app.plotcanvas

        self.decimals = 4
        self.units = ''

        # ## Title
        title_label = QtWidgets.QLabel("%s" % self.toolName)
        title_label.setStyleSheet("""
                        QLabel
                        {
                            font-size: 16px;
                            font-weight: bold;
                        }
                        """)
        self.layout.addWidget(title_label)

    def run(self, toggle=True):
        self.app.report_usage("QRCode()")

        if toggle:
            # if the splitter is hidden, display it, else hide it but only if the current widget is the same
            if self.app.ui.splitter.sizes()[0] == 0:
                self.app.ui.splitter.setSizes([1, 1])
            else:
                try:
                    if self.app.ui.tool_scroll_area.widget().objectName() == self.toolName:
                        # if tab is populated with the tool but it does not have the focus, focus on it
                        if not self.app.ui.notebook.currentWidget() is self.app.ui.tool_tab:
                            # focus on Tool Tab
                            self.app.ui.notebook.setCurrentWidget(self.app.ui.tool_tab)
                        else:
                            self.app.ui.splitter.setSizes([0, 1])
                except AttributeError:
                    pass
        else:
            if self.app.ui.splitter.sizes()[0] == 0:
                self.app.ui.splitter.setSizes([1, 1])

        FlatCAMTool.run(self)

        self.set_tool_ui()

        self.app.ui.notebook.setTabText(2, _("QRCode Tool"))

        self.execute()

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, shortcut='ALT+Q', **kwargs)

    def set_tool_ui(self):
        self.units = self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().upper()

    def execute(self):
        svg_file = io.StringIO('')
        svg_class = pyqrcode.QRCode("FlatCAM - 2D - Computer aided PCB Manufacturing Tool")
        svg_class.svg(svg_file, scale=4, xmldecl=False)

        def obj_init(geo_obj, app_obj):
            print(svg_file)
            geo_obj.import_svg(svg_file)

        with self.app.proc_container.new("Import SVG"):

            # Object creation
            self.app.new_object('geometry', 'generated_qrcode', obj_init, plot=False)

            # # Register recent file
            # self.app.file_opened.emit("svg", img)
            #
            # # GUI feedback
            # self.app.inform.emit("Opened: " + img)
