# ######################################################### ##
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
# ######################################################### ##

# ###########################################################                                      #
# File Modified: Marius Adrian Stanciu (c)                 #
# Date: 3/10/2019                                          #
# ######################################################### ##

from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import Qt

from camlib import distance, arc, three_point_circle, Geometry, FlatCAMRTreeStorage
from appTool import AppTool
from appGUI.GUIElements import OptionalInputSection, FCCheckBox, FCLabel, FCComboBox, FCTextAreaRich, \
    FCDoubleSpinner, FCButton, FCInputDoubleSpinner, FCTree, NumericalEvalTupleEntry
from appParsers.ParseFont import *

from shapely.geometry import LineString, LinearRing, MultiLineString, Polygon, MultiPolygon, Point
from shapely.ops import unary_union, linemerge
import shapely.affinity as affinity
from shapely.geometry.polygon import orient

import numpy as np
from numpy.linalg import norm as numpy_norm
import logging

from rtree import index as rtindex

from copy import deepcopy
# from vispy.io import read_png
import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class BufferSelectionTool(AppTool):
    """
    Simple input for buffer distance.
    """

    toolName = _("Buffer Selection")

    def __init__(self, app, draw_app):
        AppTool.__init__(self, app)

        self.draw_app = draw_app
        self.decimals = app.decimals

        # Title
        title_label = FCLabel("%s" % ('Editor ' + self.toolName))
        title_label.setStyleSheet("""
                        QLabel
                        {
                            font-size: 16px;
                            font-weight: bold;
                        }
                        """)
        self.layout.addWidget(title_label)

        # this way I can hide/show the frame
        self.buffer_tool_frame = QtWidgets.QFrame()
        self.buffer_tool_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.buffer_tool_frame)
        self.buffer_tools_box = QtWidgets.QVBoxLayout()
        self.buffer_tools_box.setContentsMargins(0, 0, 0, 0)
        self.buffer_tool_frame.setLayout(self.buffer_tools_box)

        # Form Layout
        form_layout = QtWidgets.QFormLayout()
        self.buffer_tools_box.addLayout(form_layout)

        # Buffer distance
        self.buffer_distance_entry = FCDoubleSpinner()
        self.buffer_distance_entry.set_precision(self.decimals)
        self.buffer_distance_entry.set_range(0.0000, 9910000.0000)
        form_layout.addRow('%S:' % _("Buffer distance"), self.buffer_distance_entry)
        self.buffer_corner_lbl = FCLabel('%s:' % _("Buffer corner"))
        self.buffer_corner_lbl.setToolTip(
            _("There are 3 types of corners:\n"
              " - 'Round': the corner is rounded for exterior buffer.\n"
              " - 'Square': the corner is met in a sharp angle for exterior buffer.\n"
              " - 'Beveled': the corner is a line that directly connects the features meeting in the corner")
        )
        self.buffer_corner_cb = FCComboBox()
        self.buffer_corner_cb.addItem(_("Round"))
        self.buffer_corner_cb.addItem(_("Square"))
        self.buffer_corner_cb.addItem(_("Beveled"))
        form_layout.addRow(self.buffer_corner_lbl, self.buffer_corner_cb)

        # Buttons
        hlay = QtWidgets.QHBoxLayout()
        self.buffer_tools_box.addLayout(hlay)

        self.buffer_int_button = FCButton(_("Buffer Interior"))
        hlay.addWidget(self.buffer_int_button)
        self.buffer_ext_button = FCButton(_("Buffer Exterior"))
        hlay.addWidget(self.buffer_ext_button)

        hlay1 = QtWidgets.QHBoxLayout()
        self.buffer_tools_box.addLayout(hlay1)

        self.buffer_button = FCButton(_("Full Buffer"))
        hlay1.addWidget(self.buffer_button)

        self.layout.addStretch()

        # Signals
        self.buffer_button.clicked.connect(self.on_buffer)
        self.buffer_int_button.clicked.connect(self.on_buffer_int)
        self.buffer_ext_button.clicked.connect(self.on_buffer_ext)

        # Init appGUI
        self.buffer_distance_entry.set_value(0.01)

    def run(self):
        self.app.defaults.report_usage("Geo Editor ToolBuffer()")
        AppTool.run(self)

        # if the splitter us hidden, display it
        if self.app.ui.splitter.sizes()[0] == 0:
            self.app.ui.splitter.setSizes([1, 1])

        self.app.ui.notebook.setTabText(2, _("Buffer Tool"))

    def on_buffer(self):
        try:
            buffer_distance = float(self.buffer_distance_entry.get_value())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                buffer_distance = float(self.buffer_distance_entry.get_value().replace(',', '.'))
                self.buffer_distance_entry.set_value(buffer_distance)
            except ValueError:
                self.app.inform.emit('[WARNING_NOTCL] %s' %
                                     _("Buffer distance value is missing or wrong format. Add it and retry."))
                return
        # the cb index start from 0 but the join styles for the buffer start from 1 therefore the adjustment
        # I populated the combobox such that the index coincide with the join styles value (which is really an INT)
        join_style = self.buffer_corner_cb.currentIndex() + 1
        self.draw_app.buffer(buffer_distance, join_style)

    def on_buffer_int(self):
        try:
            buffer_distance = float(self.buffer_distance_entry.get_value())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                buffer_distance = float(self.buffer_distance_entry.get_value().replace(',', '.'))
                self.buffer_distance_entry.set_value(buffer_distance)
            except ValueError:
                self.app.inform.emit('[WARNING_NOTCL] %s' %
                                     _("Buffer distance value is missing or wrong format. Add it and retry."))
                return
        # the cb index start from 0 but the join styles for the buffer start from 1 therefore the adjustment
        # I populated the combobox such that the index coincide with the join styles value (which is really an INT)
        join_style = self.buffer_corner_cb.currentIndex() + 1
        self.draw_app.buffer_int(buffer_distance, join_style)

    def on_buffer_ext(self):
        try:
            buffer_distance = float(self.buffer_distance_entry.get_value())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                buffer_distance = float(self.buffer_distance_entry.get_value().replace(',', '.'))
                self.buffer_distance_entry.set_value(buffer_distance)
            except ValueError:
                self.app.inform.emit('[WARNING_NOTCL] %s' %
                                     _("Buffer distance value is missing or wrong format. Add it and retry."))
                return
        # the cb index start from 0 but the join styles for the buffer start from 1 therefore the adjustment
        # I populated the combobox such that the index coincide with the join styles value (which is really an INT)
        join_style = self.buffer_corner_cb.currentIndex() + 1
        self.draw_app.buffer_ext(buffer_distance, join_style)

    def hide_tool(self):
        self.buffer_tool_frame.hide()
        self.app.ui.notebook.setCurrentWidget(self.app.ui.project_tab)


class TextInputTool(AppTool):
    """
    Simple input for buffer distance.
    """

    toolName = _("Text Input Tool")

    def __init__(self, app):
        AppTool.__init__(self, app)

        self.app = app
        self.text_path = []
        self.decimals = self.app.decimals

        self.f_parse = ParseFont(self.app)
        self.f_parse.get_fonts_by_types()

        # this way I can hide/show the frame
        self.text_tool_frame = QtWidgets.QFrame()
        self.text_tool_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.text_tool_frame)
        self.text_tools_box = QtWidgets.QVBoxLayout()
        self.text_tools_box.setContentsMargins(0, 0, 0, 0)
        self.text_tool_frame.setLayout(self.text_tools_box)

        # Title
        title_label = FCLabel("%s" % self.toolName)
        title_label.setStyleSheet("""
                        QLabel
                        {
                            font-size: 16px;
                            font-weight: bold;
                        }
                        """)
        self.text_tools_box.addWidget(title_label)

        # Form Layout
        self.form_layout = QtWidgets.QFormLayout()
        self.text_tools_box.addLayout(self.form_layout)

        # Font type
        if sys.platform == "win32":
            f_current = QtGui.QFont("Arial")
        elif sys.platform == "linux":
            f_current = QtGui.QFont("FreeMono")
        else:
            f_current = QtGui.QFont("Helvetica Neue")

        self.font_name = f_current.family()

        self.font_type_cb = QtWidgets.QFontComboBox(self)
        self.font_type_cb.setCurrentFont(f_current)
        self.form_layout.addRow(FCLabel('%s:' % _("Font")), self.font_type_cb)

        # Flag variables to show if font is bold, italic, both or none (regular)
        self.font_bold = False
        self.font_italic = False

        # # Create dictionaries with the filenames of the fonts
        # # Key: Fontname
        # # Value: Font File Name.ttf
        #
        # # regular fonts
        # self.ff_names_regular ={}
        # # bold fonts
        # self.ff_names_bold = {}
        # # italic fonts
        # self.ff_names_italic = {}
        # # bold and italic fonts
        # self.ff_names_bi = {}
        #
        # if sys.platform == 'win32':
        #     from winreg import ConnectRegistry, OpenKey, EnumValue, HKEY_LOCAL_MACHINE
        #     registry = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
        #     font_key = OpenKey(registry, "SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts")
        #     try:
        #         i = 0
        #         while 1:
        #             name_font, value, type = EnumValue(font_key, i)
        #             k = name_font.replace(" (TrueType)", '')
        #             if 'Bold' in k and 'Italic' in k:
        #                 k = k.replace(" Bold Italic", '')
        #                 self.ff_names_bi.update({k: value})
        #             elif 'Bold' in k:
        #                 k = k.replace(" Bold", '')
        #                 self.ff_names_bold.update({k: value})
        #             elif 'Italic' in k:
        #                 k = k.replace(" Italic", '')
        #                 self.ff_names_italic.update({k: value})
        #             else:
        #                 self.ff_names_regular.update({k: value})
        #             i += 1
        #     except WindowsError:
        #         pass

        # Font size
        self.font_size_cb = FCComboBox()
        self.font_size_cb.setEditable(True)
        self.font_size_cb.setMinimumContentsLength(3)
        self.font_size_cb.setMaximumWidth(70)

        font_sizes = ['6', '7', '8', '9', '10', '11', '12', '13', '14',
                      '15', '16', '18', '20', '22', '24', '26', '28',
                      '32', '36', '40', '44', '48', '54', '60', '66',
                      '72', '80', '88', '96']

        for i in font_sizes:
            self.font_size_cb.addItem(i)
        self.font_size_cb.setCurrentIndex(4)

        hlay = QtWidgets.QHBoxLayout()
        hlay.addWidget(self.font_size_cb)
        hlay.addStretch()

        self.font_bold_tb = QtWidgets.QToolButton()
        self.font_bold_tb.setCheckable(True)
        self.font_bold_tb.setIcon(QtGui.QIcon(self.app.resource_location + '/bold32.png'))
        hlay.addWidget(self.font_bold_tb)

        self.font_italic_tb = QtWidgets.QToolButton()
        self.font_italic_tb.setCheckable(True)
        self.font_italic_tb.setIcon(QtGui.QIcon(self.app.resource_location + '/italic32.png'))
        hlay.addWidget(self.font_italic_tb)

        self.form_layout.addRow(FCLabel('%s:' % _("Size")), hlay)

        # Text input
        self.text_input_entry = FCTextAreaRich()
        self.text_input_entry.setTabStopWidth(12)
        self.text_input_entry.setMinimumHeight(200)
        # self.text_input_entry.setMaximumHeight(150)
        self.text_input_entry.setCurrentFont(f_current)
        self.text_input_entry.setFontPointSize(10)
        self.form_layout.addRow(FCLabel('%s:' % _("Text")), self.text_input_entry)

        # Buttons
        hlay1 = QtWidgets.QHBoxLayout()
        self.form_layout.addRow("", hlay1)
        hlay1.addStretch()
        self.apply_button = FCButton(_("Apply"))
        hlay1.addWidget(self.apply_button)

        # self.layout.addStretch()

        # Signals
        self.apply_button.clicked.connect(self.on_apply_button)
        self.font_type_cb.currentFontChanged.connect(self.font_family)
        self.font_size_cb.activated.connect(self.font_size)
        self.font_bold_tb.clicked.connect(self.on_bold_button)
        self.font_italic_tb.clicked.connect(self.on_italic_button)

    def run(self):
        self.app.defaults.report_usage("Geo Editor TextInputTool()")
        AppTool.run(self)

        # if the splitter us hidden, display it
        if self.app.ui.splitter.sizes()[0] == 0:
            self.app.ui.splitter.setSizes([1, 1])

        self.app.ui.notebook.setTabText(2, _("Text Tool"))

    def on_apply_button(self):
        font_to_geo_type = ""

        if self.font_bold is True:
            font_to_geo_type = 'bold'
        elif self.font_italic is True:
            font_to_geo_type = 'italic'
        elif self.font_bold is True and self.font_italic is True:
            font_to_geo_type = 'bi'
        elif self.font_bold is False and self.font_italic is False:
            font_to_geo_type = 'regular'

        string_to_geo = self.text_input_entry.get_value()
        font_to_geo_size = self.font_size_cb.get_value()

        self.text_path = self.f_parse.font_to_geometry(char_string=string_to_geo, font_name=self.font_name,
                                                       font_size=font_to_geo_size,
                                                       font_type=font_to_geo_type,
                                                       units=self.app.defaults['units'].upper())

    def font_family(self, font):
        self.text_input_entry.selectAll()
        font.setPointSize(float(self.font_size_cb.get_value()))
        self.text_input_entry.setCurrentFont(font)
        self.font_name = self.font_type_cb.currentFont().family()

    def font_size(self):
        self.text_input_entry.selectAll()
        self.text_input_entry.setFontPointSize(float(self.font_size_cb.get_value()))

    def on_bold_button(self):
        if self.font_bold_tb.isChecked():
            self.text_input_entry.selectAll()
            self.text_input_entry.setFontWeight(QtGui.QFont.Bold)
            self.font_bold = True
        else:
            self.text_input_entry.selectAll()
            self.text_input_entry.setFontWeight(QtGui.QFont.Normal)
            self.font_bold = False

    def on_italic_button(self):
        if self.font_italic_tb.isChecked():
            self.text_input_entry.selectAll()
            self.text_input_entry.setFontItalic(True)
            self.font_italic = True
        else:
            self.text_input_entry.selectAll()
            self.text_input_entry.setFontItalic(False)
            self.font_italic = False

    def hide_tool(self):
        self.text_tool_frame.hide()
        self.app.ui.notebook.setCurrentWidget(self.app.ui.properties_tab)
        # self.app.ui.splitter.setSizes([0, 1])
        self.app.ui.notebook.setTabText(2, _("Tool"))


class PaintOptionsTool(AppTool):
    """
    Inputs to specify how to paint the selected polygons.
    """

    toolName = _("Paint Tool")

    def __init__(self, app, fcdraw):
        AppTool.__init__(self, app)

        self.app = app
        self.fcdraw = fcdraw
        self.decimals = self.app.decimals

        # Title
        title_label = FCLabel("%s" % self.toolName)
        title_label.setStyleSheet("""
                        QLabel
                        {
                            font-size: 16px;
                            font-weight: bold;
                        }
                        """)
        self.layout.addWidget(title_label)

        grid = QtWidgets.QGridLayout()
        self.layout.addLayout(grid)
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)

        # Tool dia
        ptdlabel = FCLabel('%s:' % _('Tool Dia'))
        ptdlabel.setToolTip(
           _("Diameter of the tool to be used in the operation.")
        )
        grid.addWidget(ptdlabel, 0, 0)

        self.painttooldia_entry = FCDoubleSpinner()
        self.painttooldia_entry.set_range(-10000.0000, 10000.0000)
        self.painttooldia_entry.set_precision(self.decimals)
        grid.addWidget(self.painttooldia_entry, 0, 1)

        # Overlap
        ovlabel = FCLabel('%s:' % _('Overlap'))
        ovlabel.setToolTip(
            _("How much (percentage) of the tool width to overlap each tool pass.\n"
              "Adjust the value starting with lower values\n"
              "and increasing it if areas that should be processed are still \n"
              "not processed.\n"
              "Lower values = faster processing, faster execution on CNC.\n"
              "Higher values = slow processing and slow execution on CNC\n"
              "due of too many paths.")
        )
        self.paintoverlap_entry = FCDoubleSpinner(suffix='%')
        self.paintoverlap_entry.set_range(0.0000, 99.9999)
        self.paintoverlap_entry.set_precision(self.decimals)
        self.paintoverlap_entry.setWrapping(True)
        self.paintoverlap_entry.setSingleStep(1)

        grid.addWidget(ovlabel, 1, 0)
        grid.addWidget(self.paintoverlap_entry, 1, 1)

        # Margin
        marginlabel = FCLabel('%s:' % _('Margin'))
        marginlabel.setToolTip(
           _("Distance by which to avoid\n"
             "the edges of the polygon to\n"
             "be painted.")
        )
        self.paintmargin_entry = FCDoubleSpinner()
        self.paintmargin_entry.set_range(-10000.0000, 10000.0000)
        self.paintmargin_entry.set_precision(self.decimals)

        grid.addWidget(marginlabel, 2, 0)
        grid.addWidget(self.paintmargin_entry, 2, 1)

        # Method
        methodlabel = FCLabel('%s:' % _('Method'))
        methodlabel.setToolTip(
            _("Algorithm to paint the polygons:\n"
              "- Standard: Fixed step inwards.\n"
              "- Seed-based: Outwards from seed.\n"
              "- Line-based: Parallel lines.")
        )
        # self.paintmethod_combo = RadioSet([
        #     {"label": _("Standard"), "value": "standard"},
        #     {"label": _("Seed-based"), "value": "seed"},
        #     {"label": _("Straight lines"), "value": "lines"}
        # ], orientation='vertical', stretch=False)
        self.paintmethod_combo = FCComboBox()
        self.paintmethod_combo.addItems(
            [_("Standard"), _("Seed"), _("Lines")]
        )

        grid.addWidget(methodlabel, 3, 0)
        grid.addWidget(self.paintmethod_combo, 3, 1)

        # Connect lines
        pathconnectlabel = FCLabel('%s:' % _("Connect"))
        pathconnectlabel.setToolTip(
           _("Draw lines between resulting\n"
             "segments to minimize tool lifts.")
        )
        self.pathconnect_cb = FCCheckBox()

        grid.addWidget(pathconnectlabel, 4, 0)
        grid.addWidget(self.pathconnect_cb, 4, 1)

        contourlabel = FCLabel('%s:' % _("Contour"))
        contourlabel.setToolTip(
            _("Cut around the perimeter of the polygon\n"
              "to trim rough edges.")
        )
        self.paintcontour_cb = FCCheckBox()

        grid.addWidget(contourlabel, 5, 0)
        grid.addWidget(self.paintcontour_cb, 5, 1)

        # Buttons
        hlay = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay)
        self.paint_button = FCButton(_("Paint"))
        hlay.addWidget(self.paint_button)

        self.layout.addStretch()

        # Signals
        self.paint_button.clicked.connect(self.on_paint)

        self.set_tool_ui()

    def run(self):
        self.app.defaults.report_usage("Geo Editor ToolPaint()")
        AppTool.run(self)

        # if the splitter us hidden, display it
        if self.app.ui.splitter.sizes()[0] == 0:
            self.app.ui.splitter.setSizes([1, 1])

        self.app.ui.notebook.setTabText(2, _("Paint Tool"))

    def set_tool_ui(self):
        # Init appGUI
        if self.app.defaults["tools_paint_tooldia"]:
            self.painttooldia_entry.set_value(self.app.defaults["tools_paint_tooldia"])
        else:
            self.painttooldia_entry.set_value(0.0)

        if self.app.defaults["tools_paint_overlap"]:
            self.paintoverlap_entry.set_value(self.app.defaults["tools_paint_overlap"])
        else:
            self.paintoverlap_entry.set_value(0.0)

        if self.app.defaults["tools_paint_offset"]:
            self.paintmargin_entry.set_value(self.app.defaults["tools_paint_offset"])
        else:
            self.paintmargin_entry.set_value(0.0)

        if self.app.defaults["tools_paint_method"]:
            self.paintmethod_combo.set_value(self.app.defaults["tools_paint_method"])
        else:
            self.paintmethod_combo.set_value(_("Seed"))

        if self.app.defaults["tools_paint_connect"]:
            self.pathconnect_cb.set_value(self.app.defaults["tools_paint_connect"])
        else:
            self.pathconnect_cb.set_value(False)

        if self.app.defaults["tools_paint_contour"]:
            self.paintcontour_cb.set_value(self.app.defaults["tools_paint_contour"])
        else:
            self.paintcontour_cb.set_value(False)

    def on_paint(self):
        if not self.fcdraw.selected:
            self.app.inform.emit('[WARNING_NOTCL] %s %s' % (_("Cancelled."), _("No shape selected.")))
            return

        tooldia = self.painttooldia_entry.get_value()
        overlap = self.paintoverlap_entry.get_value() / 100.0
        margin = self.paintmargin_entry.get_value()

        method = self.paintmethod_combo.get_value()
        contour = self.paintcontour_cb.get_value()
        connect = self.pathconnect_cb.get_value()

        self.fcdraw.paint(tooldia, overlap, margin, connect=connect, contour=contour, method=method)
        self.fcdraw.select_tool("select")
        self.app.ui.notebook.setTabText(2, _("Tools"))
        self.app.ui.notebook.setCurrentWidget(self.app.ui.project_tab)

        self.app.ui.splitter.setSizes([0, 1])


class TransformEditorTool(AppTool):
    """
    Inputs to specify how to paint the selected polygons.
    """

    toolName = _("Transform Tool")
    rotateName = _("Rotate")
    skewName = _("Skew/Shear")
    scaleName = _("Scale")
    flipName = _("Mirror (Flip)")
    offsetName = _("Offset")
    bufferName = _("Buffer")

    def __init__(self, app, draw_app):
        AppTool.__init__(self, app)

        self.app = app
        self.draw_app = draw_app
        self.decimals = self.app.decimals

        # ## Title
        title_label = FCLabel("%s" % self.toolName)
        title_label.setStyleSheet("""
                                QLabel
                                {
                                    font-size: 16px;
                                    font-weight: bold;
                                }
                                """)
        self.layout.addWidget(title_label)
        self.layout.addWidget(FCLabel(''))

        # ## Layout
        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        grid0.setColumnStretch(2, 0)

        grid0.addWidget(FCLabel(''))

        # Reference
        ref_label = FCLabel('%s:' % _("Reference"))
        ref_label.setToolTip(
            _("The reference point for Rotate, Skew, Scale, Mirror.\n"
              "Can be:\n"
              "- Origin -> it is the 0, 0 point\n"
              "- Selection -> the center of the bounding box of the selected objects\n"
              "- Point -> a custom point defined by X,Y coordinates\n"
              "- Min Selection -> the point (minx, miny) of the bounding box of the selection")
        )
        self.ref_combo = FCComboBox()
        self.ref_items = [_("Origin"), _("Selection"), _("Point"), _("Minimum")]
        self.ref_combo.addItems(self.ref_items)

        grid0.addWidget(ref_label, 0, 0)
        grid0.addWidget(self.ref_combo, 0, 1, 1, 2)

        self.point_label = FCLabel('%s:' % _("Value"))
        self.point_label.setToolTip(
            _("A point of reference in format X,Y.")
        )
        self.point_entry = NumericalEvalTupleEntry()

        grid0.addWidget(self.point_label, 1, 0)
        grid0.addWidget(self.point_entry, 1, 1, 1, 2)

        self.point_button = FCButton(_("Add"))
        self.point_button.setToolTip(
            _("Add point coordinates from clipboard.")
        )
        grid0.addWidget(self.point_button, 2, 0, 1, 3)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 5, 0, 1, 3)

        # ## Rotate Title
        rotate_title_label = FCLabel("<font size=3><b>%s</b></font>" % self.rotateName)
        grid0.addWidget(rotate_title_label, 6, 0, 1, 3)

        self.rotate_label = FCLabel('%s:' % _("Angle"))
        self.rotate_label.setToolTip(
            _("Angle, in degrees.\n"
              "Float number between -360 and 359.\n"
              "Positive numbers for CW motion.\n"
              "Negative numbers for CCW motion.")
        )

        self.rotate_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.rotate_entry.set_precision(self.decimals)
        self.rotate_entry.setSingleStep(45)
        self.rotate_entry.setWrapping(True)
        self.rotate_entry.set_range(-360, 360)

        # self.rotate_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.rotate_button = FCButton(_("Rotate"))
        self.rotate_button.setToolTip(
            _("Rotate the selected object(s).\n"
              "The point of reference is the middle of\n"
              "the bounding box for all selected objects.")
        )
        self.rotate_button.setMinimumWidth(90)

        grid0.addWidget(self.rotate_label, 7, 0)
        grid0.addWidget(self.rotate_entry, 7, 1)
        grid0.addWidget(self.rotate_button, 7, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 8, 0, 1, 3)

        # ## Skew Title
        skew_title_label = FCLabel("<font size=3><b>%s</b></font>" % self.skewName)
        grid0.addWidget(skew_title_label, 9, 0, 1, 2)

        self.skew_link_cb = FCCheckBox()
        self.skew_link_cb.setText(_("Link"))
        self.skew_link_cb.setToolTip(
            _("Link the Y entry to X entry and copy its content.")
        )

        grid0.addWidget(self.skew_link_cb, 9, 2)

        self.skewx_label = FCLabel('%s:' % _("X angle"))
        self.skewx_label.setToolTip(
            _("Angle for Skew action, in degrees.\n"
              "Float number between -360 and 360.")
        )
        self.skewx_entry = FCDoubleSpinner(callback=self.confirmation_message)
        # self.skewx_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.skewx_entry.set_precision(self.decimals)
        self.skewx_entry.set_range(-360, 360)

        self.skewx_button = FCButton(_("Skew X"))
        self.skewx_button.setToolTip(
            _("Skew/shear the selected object(s).\n"
              "The point of reference is the middle of\n"
              "the bounding box for all selected objects."))
        self.skewx_button.setMinimumWidth(90)

        grid0.addWidget(self.skewx_label, 10, 0)
        grid0.addWidget(self.skewx_entry, 10, 1)
        grid0.addWidget(self.skewx_button, 10, 2)

        self.skewy_label = FCLabel('%s:' % _("Y angle"))
        self.skewy_label.setToolTip(
            _("Angle for Skew action, in degrees.\n"
              "Float number between -360 and 360.")
        )
        self.skewy_entry = FCDoubleSpinner(callback=self.confirmation_message)
        # self.skewy_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.skewy_entry.set_precision(self.decimals)
        self.skewy_entry.set_range(-360, 360)

        self.skewy_button = FCButton(_("Skew Y"))
        self.skewy_button.setToolTip(
            _("Skew/shear the selected object(s).\n"
              "The point of reference is the middle of\n"
              "the bounding box for all selected objects."))
        self.skewy_button.setMinimumWidth(90)

        grid0.addWidget(self.skewy_label, 12, 0)
        grid0.addWidget(self.skewy_entry, 12, 1)
        grid0.addWidget(self.skewy_button, 12, 2)

        self.ois_sk = OptionalInputSection(self.skew_link_cb, [self.skewy_label, self.skewy_entry, self.skewy_button],
                                           logic=False)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 14, 0, 1, 3)

        # ## Scale Title
        scale_title_label = FCLabel("<font size=3><b>%s</b></font>" % self.scaleName)
        grid0.addWidget(scale_title_label, 15, 0, 1, 2)

        self.scale_link_cb = FCCheckBox()
        self.scale_link_cb.setText(_("Link"))
        self.scale_link_cb.setToolTip(
            _("Link the Y entry to X entry and copy its content.")
        )

        grid0.addWidget(self.scale_link_cb, 15, 2)

        self.scalex_label = FCLabel('%s:' % _("X factor"))
        self.scalex_label.setToolTip(
            _("Factor for scaling on X axis.")
        )
        self.scalex_entry = FCDoubleSpinner(callback=self.confirmation_message)
        # self.scalex_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.scalex_entry.set_precision(self.decimals)
        self.scalex_entry.setMinimum(-1e6)

        self.scalex_button = FCButton(_("Scale X"))
        self.scalex_button.setToolTip(
            _("Scale the selected object(s).\n"
              "The point of reference depends on \n"
              "the Scale reference checkbox state."))
        self.scalex_button.setMinimumWidth(90)

        grid0.addWidget(self.scalex_label, 17, 0)
        grid0.addWidget(self.scalex_entry, 17, 1)
        grid0.addWidget(self.scalex_button, 17, 2)

        self.scaley_label = FCLabel('%s:' % _("Y factor"))
        self.scaley_label.setToolTip(
            _("Factor for scaling on Y axis.")
        )
        self.scaley_entry = FCDoubleSpinner(callback=self.confirmation_message)
        # self.scaley_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.scaley_entry.set_precision(self.decimals)
        self.scaley_entry.setMinimum(-1e6)

        self.scaley_button = FCButton(_("Scale Y"))
        self.scaley_button.setToolTip(
            _("Scale the selected object(s).\n"
              "The point of reference depends on \n"
              "the Scale reference checkbox state."))
        self.scaley_button.setMinimumWidth(90)

        grid0.addWidget(self.scaley_label, 19, 0)
        grid0.addWidget(self.scaley_entry, 19, 1)
        grid0.addWidget(self.scaley_button, 19, 2)

        self.ois_s = OptionalInputSection(self.scale_link_cb,
                                          [
                                              self.scaley_label,
                                              self.scaley_entry,
                                              self.scaley_button
                                          ], logic=False)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 21, 0, 1, 3)

        # ## Flip Title
        flip_title_label = FCLabel("<font size=3><b>%s</b></font>" % self.flipName)
        grid0.addWidget(flip_title_label, 23, 0, 1, 3)

        self.flipx_button = FCButton(_("Flip on X"))
        self.flipx_button.setToolTip(
            _("Flip the selected object(s) over the X axis.")
        )

        self.flipy_button = FCButton(_("Flip on Y"))
        self.flipy_button.setToolTip(
            _("Flip the selected object(s) over the X axis.")
        )

        hlay0 = QtWidgets.QHBoxLayout()
        grid0.addLayout(hlay0, 25, 0, 1, 3)

        hlay0.addWidget(self.flipx_button)
        hlay0.addWidget(self.flipy_button)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 27, 0, 1, 3)

        # ## Offset Title
        offset_title_label = FCLabel("<font size=3><b>%s</b></font>" % self.offsetName)
        grid0.addWidget(offset_title_label, 29, 0, 1, 3)

        self.offx_label = FCLabel('%s:' % _("X val"))
        self.offx_label.setToolTip(
            _("Distance to offset on X axis. In current units.")
        )
        self.offx_entry = FCDoubleSpinner(callback=self.confirmation_message)
        # self.offx_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.offx_entry.set_precision(self.decimals)
        self.offx_entry.setMinimum(-1e6)

        self.offx_button = FCButton(_("Offset X"))
        self.offx_button.setToolTip(
            _("Offset the selected object(s).\n"
              "The point of reference is the middle of\n"
              "the bounding box for all selected objects.\n"))
        self.offx_button.setMinimumWidth(90)

        grid0.addWidget(self.offx_label, 31, 0)
        grid0.addWidget(self.offx_entry, 31, 1)
        grid0.addWidget(self.offx_button, 31, 2)

        self.offy_label = FCLabel('%s:' % _("Y val"))
        self.offy_label.setToolTip(
            _("Distance to offset on Y axis. In current units.")
        )
        self.offy_entry = FCDoubleSpinner(callback=self.confirmation_message)
        # self.offy_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.offy_entry.set_precision(self.decimals)
        self.offy_entry.setMinimum(-1e6)

        self.offy_button = FCButton(_("Offset Y"))
        self.offy_button.setToolTip(
            _("Offset the selected object(s).\n"
              "The point of reference is the middle of\n"
              "the bounding box for all selected objects.\n"))
        self.offy_button.setMinimumWidth(90)

        grid0.addWidget(self.offy_label, 32, 0)
        grid0.addWidget(self.offy_entry, 32, 1)
        grid0.addWidget(self.offy_button, 32, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 34, 0, 1, 3)

        # ## Buffer Title
        buffer_title_label = FCLabel("<font size=3><b>%s</b></font>" % self.bufferName)
        grid0.addWidget(buffer_title_label, 35, 0, 1, 2)

        self.buffer_rounded_cb = FCCheckBox('%s' % _("Rounded"))
        self.buffer_rounded_cb.setToolTip(
            _("If checked then the buffer will surround the buffered shape,\n"
              "every corner will be rounded.\n"
              "If not checked then the buffer will follow the exact geometry\n"
              "of the buffered shape.")
        )

        grid0.addWidget(self.buffer_rounded_cb, 35, 2)

        self.buffer_label = FCLabel('%s:' % _("Distance"))
        self.buffer_label.setToolTip(
            _("A positive value will create the effect of dilation,\n"
              "while a negative value will create the effect of erosion.\n"
              "Each geometry element of the object will be increased\n"
              "or decreased with the 'distance'.")
        )

        self.buffer_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.buffer_entry.set_precision(self.decimals)
        self.buffer_entry.setSingleStep(0.1)
        self.buffer_entry.setWrapping(True)
        self.buffer_entry.set_range(-10000.0000, 10000.0000)

        self.buffer_button = FCButton(_("Buffer D"))
        self.buffer_button.setToolTip(
            _("Create the buffer effect on each geometry,\n"
              "element from the selected object, using the distance.")
        )
        self.buffer_button.setMinimumWidth(90)

        grid0.addWidget(self.buffer_label, 37, 0)
        grid0.addWidget(self.buffer_entry, 37, 1)
        grid0.addWidget(self.buffer_button, 37, 2)

        self.buffer_factor_label = FCLabel('%s:' % _("Value"))
        self.buffer_factor_label.setToolTip(
            _("A positive value will create the effect of dilation,\n"
              "while a negative value will create the effect of erosion.\n"
              "Each geometry element of the object will be increased\n"
              "or decreased to fit the 'Value'. Value is a percentage\n"
              "of the initial dimension.")
        )

        self.buffer_factor_entry = FCDoubleSpinner(callback=self.confirmation_message, suffix='%')
        self.buffer_factor_entry.set_range(-100.0000, 1000.0000)
        self.buffer_factor_entry.set_precision(self.decimals)
        self.buffer_factor_entry.setWrapping(True)
        self.buffer_factor_entry.setSingleStep(1)

        self.buffer_factor_button = FCButton(_("Buffer F"))
        self.buffer_factor_button.setToolTip(
            _("Create the buffer effect on each geometry,\n"
              "element from the selected object, using the factor.")
        )
        self.buffer_factor_button.setMinimumWidth(90)

        grid0.addWidget(self.buffer_factor_label, 38, 0)
        grid0.addWidget(self.buffer_factor_entry, 38, 1)
        grid0.addWidget(self.buffer_factor_button, 38, 2)

        grid0.addWidget(FCLabel(''), 42, 0, 1, 3)

        self.layout.addStretch()

        # Signals
        self.ref_combo.currentIndexChanged.connect(self.on_reference_changed)
        self.point_button.clicked.connect(self.on_add_coords)

        self.rotate_button.clicked.connect(self.on_rotate)

        self.skewx_button.clicked.connect(self.on_skewx)
        self.skewy_button.clicked.connect(self.on_skewy)

        self.scalex_button.clicked.connect(self.on_scalex)
        self.scaley_button.clicked.connect(self.on_scaley)

        self.offx_button.clicked.connect(self.on_offx)
        self.offy_button.clicked.connect(self.on_offy)

        self.flipx_button.clicked.connect(self.on_flipx)
        self.flipy_button.clicked.connect(self.on_flipy)

        self.buffer_button.clicked.connect(self.on_buffer_by_distance)
        self.buffer_factor_button.clicked.connect(self.on_buffer_by_factor)

        # self.rotate_entry.editingFinished.connect(self.on_rotate)
        # self.skewx_entry.editingFinished.connect(self.on_skewx)
        # self.skewy_entry.editingFinished.connect(self.on_skewy)
        # self.scalex_entry.editingFinished.connect(self.on_scalex)
        # self.scaley_entry.editingFinished.connect(self.on_scaley)
        # self.offx_entry.editingFinished.connect(self.on_offx)
        # self.offy_entry.editingFinished.connect(self.on_offy)

        self.set_tool_ui()

    def run(self, toggle=True):
        self.app.defaults.report_usage("Geo Editor Transform Tool()")

        # if the splitter us hidden, display it
        if self.app.ui.splitter.sizes()[0] == 0:
            self.app.ui.splitter.setSizes([1, 1])

        if toggle:
            try:
                if self.app.ui.tool_scroll_area.widget().objectName() == self.toolName:
                    self.app.ui.notebook.setCurrentWidget(self.app.ui.properties_tab)
                else:
                    self.app.ui.notebook.setCurrentWidget(self.app.ui.tool_tab)
            except AttributeError:
                pass

        AppTool.run(self)
        self.set_tool_ui()

        self.app.ui.notebook.setTabText(2, _("Transform Tool"))

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Alt+T', **kwargs)

    def set_tool_ui(self):
        # Initialize form
        ref_val = self.app.defaults["tools_transform_reference"]
        if ref_val == _("Object"):
            ref_val = _("Selection")
        self.ref_combo.set_value(ref_val)
        self.point_entry.set_value(self.app.defaults["tools_transform_ref_point"])
        self.rotate_entry.set_value(self.app.defaults["tools_transform_rotate"])

        self.skewx_entry.set_value(self.app.defaults["tools_transform_skew_x"])
        self.skewy_entry.set_value(self.app.defaults["tools_transform_skew_y"])
        self.skew_link_cb.set_value(self.app.defaults["tools_transform_skew_link"])

        self.scalex_entry.set_value(self.app.defaults["tools_transform_scale_x"])
        self.scaley_entry.set_value(self.app.defaults["tools_transform_scale_y"])
        self.scale_link_cb.set_value(self.app.defaults["tools_transform_scale_link"])

        self.offx_entry.set_value(self.app.defaults["tools_transform_offset_x"])
        self.offy_entry.set_value(self.app.defaults["tools_transform_offset_y"])

        self.buffer_entry.set_value(self.app.defaults["tools_transform_buffer_dis"])
        self.buffer_factor_entry.set_value(self.app.defaults["tools_transform_buffer_factor"])
        self.buffer_rounded_cb.set_value(self.app.defaults["tools_transform_buffer_corner"])

        # initial state is hidden
        self.point_label.hide()
        self.point_entry.hide()
        self.point_button.hide()

    def template(self):
        if not self.draw_app.selected:
            self.app.inform.emit('[WARNING_NOTCL] %s %s' % (_("Cancelled."), _("No shape selected.")))
            return

        self.draw_app.select_tool("select")
        self.app.ui.notebook.setTabText(2, "Tools")
        self.app.ui.notebook.setCurrentWidget(self.app.ui.project_tab)

        self.app.ui.splitter.setSizes([0, 1])

    def on_reference_changed(self, index):
        if index == 0 or index == 1:  # "Origin" or "Selection" reference
            self.point_label.hide()
            self.point_entry.hide()
            self.point_button.hide()

        elif index == 2:    # "Point" reference
            self.point_label.show()
            self.point_entry.show()
            self.point_button.show()

    def on_calculate_reference(self, ref_index=None):
        if ref_index:
            ref_val = ref_index
        else:
            ref_val = self.ref_combo.currentIndex()

        if ref_val == 0:    # "Origin" reference
            return 0, 0
        elif ref_val == 1:  # "Selection" reference
            sel_list = self.draw_app.selected
            if sel_list:
                xmin, ymin, xmax, ymax = self.alt_bounds(sel_list)
                px = (xmax + xmin) * 0.5
                py = (ymax + ymin) * 0.5
                return px, py
            else:
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("No shape selected."))
                return "fail"
        elif ref_val == 2:  # "Point" reference
            point_val = self.point_entry.get_value()
            try:
                px, py = eval('{}'.format(point_val))
                return px, py
            except Exception:
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("Incorrect format for Point value. Needs format X,Y"))
                return "fail"
        else:
            sel_list = self.draw_app.selected
            if sel_list:
                xmin, ymin, xmax, ymax = self.alt_bounds(sel_list)
                if ref_val == 3:
                    return xmin, ymin   # lower left corner
                elif ref_val == 4:
                    return xmax, ymin   # lower right corner
                elif ref_val == 5:
                    return xmax, ymax   # upper right corner
                else:
                    return xmin, ymax   # upper left corner
            else:
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("No shape selected."))
                return "fail"

    def on_add_coords(self):
        val = self.app.clipboard.text()
        self.point_entry.set_value(val)

    def on_rotate(self, signal=None, val=None, ref=None):
        value = float(self.rotate_entry.get_value()) if val is None else val
        if value == 0:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Rotate transformation can not be done for a value of 0."))
            return
        point = self.on_calculate_reference() if ref is None else self.on_calculate_reference(ref_index=ref)
        if point == 'fail':
            return
        self.app.worker_task.emit({'fcn': self.on_rotate_action, 'params': [value, point]})

    def on_flipx(self, signal=None, ref=None):
        axis = 'Y'
        point = self.on_calculate_reference() if ref is None else self.on_calculate_reference(ref_index=ref)
        if point == 'fail':
            return
        self.app.worker_task.emit({'fcn': self.on_flip, 'params': [axis, point]})

    def on_flipy(self, signal=None, ref=None):
        axis = 'X'
        point = self.on_calculate_reference() if ref is None else self.on_calculate_reference(ref_index=ref)
        if point == 'fail':
            return
        self.app.worker_task.emit({'fcn': self.on_flip, 'params': [axis, point]})

    def on_skewx(self, signal=None, val=None, ref=None):
        xvalue = float(self.skewx_entry.get_value()) if val is None else val

        if xvalue == 0:
            return

        if self.skew_link_cb.get_value():
            yvalue = xvalue
        else:
            yvalue = 0

        axis = 'X'
        point = self.on_calculate_reference() if ref is None else self.on_calculate_reference(ref_index=ref)
        if point == 'fail':
            return

        self.app.worker_task.emit({'fcn': self.on_skew, 'params': [axis, xvalue, yvalue, point]})

    def on_skewy(self, signal=None, val=None, ref=None):
        xvalue = 0
        yvalue = float(self.skewy_entry.get_value()) if val is None else val

        if yvalue == 0:
            return

        axis = 'Y'
        point = self.on_calculate_reference() if ref is None else self.on_calculate_reference(ref_index=ref)
        if point == 'fail':
            return

        self.app.worker_task.emit({'fcn': self.on_skew, 'params': [axis, xvalue, yvalue, point]})

    def on_scalex(self, signal=None, val=None, ref=None):
        xvalue = float(self.scalex_entry.get_value()) if val is None else val

        if xvalue == 0 or xvalue == 1:
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("Scale transformation can not be done for a factor of 0 or 1."))
            return

        if self.scale_link_cb.get_value():
            yvalue = xvalue
        else:
            yvalue = 1

        axis = 'X'
        point = self.on_calculate_reference() if ref is None else self.on_calculate_reference(ref_index=ref)
        if point == 'fail':
            return

        self.app.worker_task.emit({'fcn': self.on_scale, 'params': [axis, xvalue, yvalue, point]})

    def on_scaley(self, signal=None, val=None, ref=None):
        xvalue = 1
        yvalue = float(self.scaley_entry.get_value()) if val is None else val

        if yvalue == 0 or yvalue == 1:
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("Scale transformation can not be done for a factor of 0 or 1."))
            return

        axis = 'Y'
        point = self.on_calculate_reference() if ref is None else self.on_calculate_reference(ref_index=ref)
        if point == 'fail':
            return

        self.app.worker_task.emit({'fcn': self.on_scale, 'params': [axis, xvalue, yvalue, point]})

    def on_offx(self, signal=None, val=None):
        value = float(self.offx_entry.get_value()) if val is None else val
        if value == 0:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Offset transformation can not be done for a value of 0."))
            return
        axis = 'X'

        self.app.worker_task.emit({'fcn': self.on_offset, 'params': [axis, value]})

    def on_offy(self, signal=None, val=None):
        value = float(self.offy_entry.get_value()) if val is None else val
        if value == 0:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Offset transformation can not be done for a value of 0."))
            return
        axis = 'Y'

        self.app.worker_task.emit({'fcn': self.on_offset, 'params': [axis, value]})

    def on_buffer_by_distance(self):
        value = self.buffer_entry.get_value()
        join = 1 if self.buffer_rounded_cb.get_value() else 2

        self.app.worker_task.emit({'fcn': self.on_buffer_action, 'params': [value, join]})

    def on_buffer_by_factor(self):
        value = 1 + (self.buffer_factor_entry.get_value() / 100.0)
        join = 1 if self.buffer_rounded_cb.get_value() else 2

        # tell the buffer method to use the factor
        factor = True

        self.app.worker_task.emit({'fcn': self.on_buffer_action, 'params': [value, join, factor]})

    def on_rotate_action(self, val, point):
        """
        Rotate geometry

        :param val:     Rotate with a known angle value, val
        :param point:   Reference point for rotation: tuple
        :return:
        """

        with self.app.proc_container.new(_("Appying Rotate")):
            shape_list = self.draw_app.selected
            px, py = point

            if not shape_list:
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("No shape selected."))
                return

            try:
                for sel_sha in shape_list:
                    sel_sha.rotate(-val, point=(px, py))
                    self.draw_app.replot()

                self.app.inform.emit('[success] %s' % _("Done."))
            except Exception as e:
                self.app.inform.emit('[ERROR_NOTCL] %s: %s.' % (_("Action was not executed"), str(e)))
                return

    def on_flip(self, axis, point):
        """
        Mirror (flip) geometry

        :param axis:    Mirror on a known axis given by the axis parameter
        :param point:   Mirror reference point
        :return:
        """

        shape_list = self.draw_app.selected

        if not shape_list:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("No shape selected."))
            return

        with self.app.proc_container.new(_("Applying Flip")):
            try:
                px, py = point

                # execute mirroring
                for sha in shape_list:
                    if axis == 'X':
                        sha.mirror('X', (px, py))
                        self.app.inform.emit('[success] %s...' % _('Flip on Y axis done'))
                    elif axis == 'Y':
                        sha.mirror('Y', (px, py))
                        self.app.inform.emit('[success] %s' % _('Flip on X axis done'))
                    self.draw_app.replot()

            except Exception as e:
                self.app.inform.emit('[ERROR_NOTCL] %s: %s.' % (_("Action was not executed"), str(e)))
                return

    def on_skew(self, axis, xval, yval, point):
        """
        Skew geometry

        :param point:
        :param axis:    Axis on which to deform, skew
        :param xval:    Skew value on X axis
        :param yval:    Skew value on Y axis
        :return:
        """

        shape_list = self.draw_app.selected

        if not shape_list:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("No shape selected."))
            return

        with self.app.proc_container.new(_("Applying Skew")):
            try:
                px, py = point
                for sha in shape_list:
                    sha.skew(xval, yval, point=(px, py))

                    self.draw_app.replot()

                if axis == 'X':
                    self.app.inform.emit('[success] %s...' % _('Skew on the X axis done'))
                else:
                    self.app.inform.emit('[success] %s...' % _('Skew on the Y axis done'))

            except Exception as e:
                self.app.inform.emit('[ERROR_NOTCL] %s: %s.' % (_("Action was not executed"), str(e)))
                return

    def on_scale(self, axis, xfactor, yfactor, point=None):
        """
        Scale geometry

        :param axis:        Axis on which to scale
        :param xfactor:     Factor for scaling on X axis
        :param yfactor:     Factor for scaling on Y axis
        :param point:       Point of origin for scaling

        :return:
        """

        shape_list = self.draw_app.selected

        if not shape_list:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("No shape selected."))
            return

        with self.app.proc_container.new(_("Applying Scale")):
            try:
                px, py = point

                for sha in shape_list:
                    sha.scale(xfactor, yfactor, point=(px, py))
                    self.draw_app.replot()

                if str(axis) == 'X':
                    self.app.inform.emit('[success] %s...' % _('Scale on the X axis done'))
                else:
                    self.app.inform.emit('[success] %s...' % _('Scale on the Y axis done'))
            except Exception as e:
                self.app.inform.emit('[ERROR_NOTCL] %s: %s.' % (_("Action was not executed"), str(e)))
                return

    def on_offset(self, axis, num):
        """
        Offset geometry

        :param axis:        Axis on which to apply offset
        :param num:         The translation factor

        :return:
        """
        shape_list = self.draw_app.selected

        if not shape_list:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("No shape selected."))
            return

        with self.app.proc_container.new(_("Applying Offset")):
            try:
                for sha in shape_list:
                    if axis == 'X':
                        sha.offset((num, 0))
                    elif axis == 'Y':
                        sha.offset((0, num))
                    self.draw_app.replot()

                if axis == 'X':
                    self.app.inform.emit('[success] %s...' % _('Offset on the X axis done'))
                else:
                    self.app.inform.emit('[success] %s...' % _('Offset on the Y axis done'))

            except Exception as e:
                self.app.inform.emit('[ERROR_NOTCL] %s: %s.' % (_("Action was not executed"), str(e)))
                return

    def on_buffer_action(self, value, join, factor=None):
        shape_list = self.draw_app.selected

        if not shape_list:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("No shape selected."))
            return
        else:
            with self.app.proc_container.new(_("Applying Buffer")):
                try:
                    for sel_obj in shape_list:
                        sel_obj.buffer(value, join, factor)

                        self.draw_app.replot()

                    self.app.inform.emit('[success] %s...' % _('Buffer done'))

                except Exception as e:
                    self.app.log.debug("TransformEditorTool.on_buffer_action() --> %s" % str(e))
                    self.app.inform.emit('[ERROR_NOTCL] %s: %s.' % (_("Action was not executed"), str(e)))
                    return

    def on_rotate_key(self):
        val_box = FCInputDoubleSpinner(title=_("Rotate ..."),
                                       text='%s:' % _('Enter an Angle Value (degrees)'),
                                       min=-359.9999, max=360.0000, decimals=self.decimals,
                                       init_val=float(self.app.defaults['tools_transform_rotate']),
                                       parent=self.app.ui)
        val_box.set_icon(QtGui.QIcon(self.app.resource_location + '/rotate.png'))

        val, ok = val_box.get_value()
        if ok:
            self.on_rotate(val=val, ref=1)
            self.app.inform.emit('[success] %s...' % _("Rotate done"))
            return
        else:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Rotate cancelled"))

    def on_offx_key(self):
        units = self.app.defaults['units'].lower()

        val_box = FCInputDoubleSpinner(title=_("Offset on X axis ..."),
                                       text='%s: (%s)' % (_('Enter a distance Value'), str(units)),
                                       min=-10000.0000, max=10000.0000, decimals=self.decimals,
                                       init_val=float(self.app.defaults['tools_transform_offset_x']),
                                       parent=self.app.ui)
        val_box.set_icon(QtGui.QIcon(self.app.resource_location + '/offsetx32.png'))

        val, ok = val_box.get_value()
        if ok:
            self.on_offx(val=val)
            self.app.inform.emit('[success] %s' % _("Offset on the X axis done"))
            return
        else:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Offset X cancelled"))

    def on_offy_key(self):
        units = self.app.defaults['units'].lower()

        val_box = FCInputDoubleSpinner(title=_("Offset on Y axis ..."),
                                       text='%s: (%s)' % (_('Enter a distance Value'), str(units)),
                                       min=-10000.0000, max=10000.0000, decimals=self.decimals,
                                       init_val=float(self.app.defaults['tools_transform_offset_y']),
                                       parent=self.app.ui)
        val_box.set_icon(QtGui.QIcon(self.app.resource_location + '/offsety32.png'))

        val, ok = val_box.get_value()
        if ok:
            self.on_offx(val=val)
            self.app.inform.emit('[success] %s...' % _("Offset on Y axis done"))
            return
        else:
            self.app.inform.emit('[success] %s...' % _("Offset on the Y axis canceled"))

    def on_skewx_key(self):
        val_box = FCInputDoubleSpinner(title=_("Skew on X axis ..."),
                                       text='%s:' % _('Enter an Angle Value (degrees)'),
                                       min=-359.9999, max=360.0000, decimals=self.decimals,
                                       init_val=float(self.app.defaults['tools_transform_skew_x']),
                                       parent=self.app.ui)
        val_box.set_icon(QtGui.QIcon(self.app.resource_location + '/skewX.png'))

        val, ok = val_box.get_value()
        if ok:
            self.on_skewx(val=val, ref=3)
            self.app.inform.emit('[success] %s...' % _("Skew on X axis done"))
            return
        else:
            self.app.inform.emit('[success] %s...' % _("Skew on X axis canceled"))

    def on_skewy_key(self):
        val_box = FCInputDoubleSpinner(title=_("Skew on Y axis ..."),
                                       text='%s:' % _('Enter an Angle Value (degrees)'),
                                       min=-359.9999, max=360.0000, decimals=self.decimals,
                                       init_val=float(self.app.defaults['tools_transform_skew_y']),
                                       parent=self.app.ui)
        val_box.set_icon(QtGui.QIcon(self.app.resource_location + '/skewY.png'))

        val, ok = val_box.get_value()
        if ok:
            self.on_skewx(val=val, ref=3)
            self.app.inform.emit('[success] %s...' % _("Skew on Y axis done"))
            return
        else:
            self.app.inform.emit('[success] %s...' % _("Skew on Y axis canceled"))

    @staticmethod
    def alt_bounds(shapelist):
        """
        Returns coordinates of rectangular bounds of a selection of shapes
        """

        def bounds_rec(lst):
            minx = np.Inf
            miny = np.Inf
            maxx = -np.Inf
            maxy = -np.Inf

            try:
                for shape in lst:
                    minx_, miny_, maxx_, maxy_ = bounds_rec(shape)
                    minx = min(minx, minx_)
                    miny = min(miny, miny_)
                    maxx = max(maxx, maxx_)
                    maxy = max(maxy, maxy_)
                return minx, miny, maxx, maxy
            except TypeError:
                # it's an object, return it's bounds
                return lst.bounds()

        return bounds_rec(shapelist)


class DrawToolShape(object):
    """
    Encapsulates "shapes" under a common class.
    """

    tolerance = None

    @staticmethod
    def get_pts(o):
        """
        Returns a list of all points in the object, where
        the object can be a Polygon, Not a polygon, or a list
        of such. Search is done recursively.

        :param: geometric object
        :return: List of points
        :rtype: list
        """
        pts = []

        # Iterable: descend into each item.
        try:
            for subo in o:
                pts += DrawToolShape.get_pts(subo)

        # Non-iterable
        except TypeError:
            if o is not None:
                # DrawToolShape: descend into .geo.
                if isinstance(o, DrawToolShape):
                    pts += DrawToolShape.get_pts(o.geo)

                # Descend into .exerior and .interiors
                elif type(o) == Polygon:
                    pts += DrawToolShape.get_pts(o.exterior)
                    for i in o.interiors:
                        pts += DrawToolShape.get_pts(i)
                elif type(o) == MultiLineString:
                    for line in o:
                        pts += DrawToolShape.get_pts(line)
                # Has .coords: list them.
                else:
                    if DrawToolShape.tolerance is not None:
                        pts += list(o.simplify(DrawToolShape.tolerance).coords)
                    else:
                        pts += list(o.coords)
            else:
                return
        return pts

    def __init__(self, geo=[]):

        # Shapely type or list of such
        self.geo = geo
        self.utility = False

    def get_all_points(self):
        return DrawToolShape.get_pts(self)

    def bounds(self):
        """
                Returns coordinates of rectangular bounds
                of geometry: (xmin, ymin, xmax, ymax).
                """
        # fixed issue of getting bounds only for one level lists of objects
        # now it can get bounds for nested lists of objects
        def bounds_rec(shape_el):
            if type(shape_el) is list:
                minx = np.Inf
                miny = np.Inf
                maxx = -np.Inf
                maxy = -np.Inf

                for k in shape_el:
                    minx_, miny_, maxx_, maxy_ = bounds_rec(k)
                    minx = min(minx, minx_)
                    miny = min(miny, miny_)
                    maxx = max(maxx, maxx_)
                    maxy = max(maxy, maxy_)
                return minx, miny, maxx, maxy
            else:
                # it's a Shapely object, return it's bounds
                return shape_el.bounds

        bounds_coords = bounds_rec(self.geo)
        return bounds_coords

    def mirror(self, axis, point):
        """
        Mirrors the shape around a specified axis passing through
        the given point.

        :param axis:    "X" or "Y" indicates around which axis to mirror.
        :type axis:     str
        :param point:   [x, y] point belonging to the mirror axis.
        :type point:    list
        :return:        None
        """

        px, py = point
        xscale, yscale = {"X": (1.0, -1.0), "Y": (-1.0, 1.0)}[axis]

        def mirror_geom(shape_el):
            if type(shape_el) is list:
                new_obj = []
                for g in shape_el:
                    new_obj.append(mirror_geom(g))
                return new_obj
            else:
                return affinity.scale(shape_el, xscale, yscale, origin=(px, py))

        try:
            self.geo = mirror_geom(self.geo)
        except AttributeError:
            log.debug("DrawToolShape.mirror() --> Failed to mirror. No shape selected")

    def rotate(self, angle, point):
        """
        Rotate a shape by an angle (in degrees) around the provided coordinates.


        The angle of rotation are specified in degrees (default). Positive angles are
        counter-clockwise and negative are clockwise rotations.

        The point of origin can be a keyword 'center' for the bounding box
        center (default), 'centroid' for the geometry's centroid, a Point object
        or a coordinate tuple (x0, y0).

        See shapely manual for more information: http://toblerity.org/shapely/manual.html#affine-transformations

        :param angle:   The angle of rotation
        :param point:   The point of origin
        :return:        None
        """

        px, py = point

        def rotate_geom(shape_el):
            if type(shape_el) is list:
                new_obj = []
                for g in shape_el:
                    new_obj.append(rotate_geom(g))
                return new_obj
            else:
                return affinity.rotate(shape_el, angle, origin=(px, py))

        try:
            self.geo = rotate_geom(self.geo)
        except AttributeError:
            log.debug("DrawToolShape.rotate() --> Failed to rotate. No shape selected")

    def skew(self, angle_x, angle_y, point):
        """
        Shear/Skew a shape by angles along x and y dimensions.

        angle_x, angle_y : float, float
            The shear angle(s) for the x and y axes respectively. These can be
            specified in either degrees (default) or radians by setting
            use_radians=True.

        See shapely manual for more information: http://toblerity.org/shapely/manual.html#affine-transformations

        :param angle_x:
        :param angle_y:
        :param point:       tuple of coordinates (x,y)
        :return:
        """
        px, py = point

        def skew_geom(shape_el):
            if type(shape_el) is list:
                new_obj = []
                for g in shape_el:
                    new_obj.append(skew_geom(g))
                return new_obj
            else:
                return affinity.skew(shape_el, angle_x, angle_y, origin=(px, py))

        try:
            self.geo = skew_geom(self.geo)
        except AttributeError:
            log.debug("DrawToolShape.skew() --> Failed to skew. No shape selected")

    def offset(self, vect):
        """
        Offsets all shapes by a given vector

        :param vect:    (x, y) vector by which to offset the shape geometry
        :type vect:     tuple
        :return:        None
        :rtype:         None
        """

        try:
            dx, dy = vect
        except TypeError:
            log.debug("DrawToolShape.offset() --> An (x,y) pair of values are needed. "
                      "Probable you entered only one value in the Offset field.")
            return

        def translate_recursion(geom):
            if type(geom) == list:
                geoms = []
                for local_geom in geom:
                    geoms.append(translate_recursion(local_geom))
                return geoms
            else:
                return affinity.translate(geom, xoff=dx, yoff=dy)

        try:
            self.geo = translate_recursion(self.geo)
        except AttributeError:
            log.debug("DrawToolShape.offset() --> Failed to offset. No shape selected")

    def scale(self, xfactor, yfactor=None, point=None):
        """
        Scales all shape geometry by a given factor.

        :param xfactor:     Factor by which to scale the shape's geometry/
        :type xfactor:      float
        :param yfactor:     Factor by which to scale the shape's geometry/
        :type yfactor:      float
        :param point:       Point of origin; tuple
        :return: None
        :rtype: None
        """

        try:
            xfactor = float(xfactor)
        except Exception:
            log.debug("DrawToolShape.offset() --> Scale factor has to be a number: integer or float.")
            return

        if yfactor is None:
            yfactor = xfactor
        else:
            try:
                yfactor = float(yfactor)
            except Exception:
                log.debug("DrawToolShape.offset() --> Scale factor has to be a number: integer or float.")
                return

        if point is None:
            px = 0
            py = 0
        else:
            px, py = point

        def scale_recursion(geom):
            if type(geom) == list:
                geoms = []
                for local_geom in geom:
                    geoms.append(scale_recursion(local_geom))
                return geoms
            else:
                return affinity.scale(geom, xfactor, yfactor, origin=(px, py))

        try:
            self.geo = scale_recursion(self.geo)
        except AttributeError:
            log.debug("DrawToolShape.scale() --> Failed to scale. No shape selected")

    def buffer(self, value, join=None, factor=None):
        """
        Create a buffered geometry

        :param value:   the distance to which to buffer
        :param join:    the type of connections between nearby buffer lines
        :param factor:  a scaling factor which will do a "sort of" buffer
        :return:        None
        """

        def buffer_recursion(geom):
            if type(geom) == list:
                geoms = []
                for local_geom in geom:
                    geoms.append(buffer_recursion(local_geom))
                return geoms
            else:
                if factor:
                    return affinity.scale(geom, xfact=value, yfact=value, origin='center')
                else:
                    return geom.buffer(value, resolution=32, join_style=join)

        try:
            self.geo = buffer_recursion(self.geo)
        except AttributeError:
            log.debug("DrawToolShape.buffer() --> Failed to buffer. No shape selected")


class DrawToolUtilityShape(DrawToolShape):
    """
    Utility shapes are temporary geometry in the editor
    to assist in the creation of shapes. For example it
    will show the outline of a rectangle from the first
    point to the current mouse pointer before the second
    point is clicked and the final geometry is created.
    """

    def __init__(self, geo=[]):
        super(DrawToolUtilityShape, self).__init__(geo=geo)
        self.utility = True


class DrawTool(object):
    """
    Abstract Class representing a tool in the drawing
    program. Can generate geometry, including temporary
    utility geometry that is updated on user clicks
    and mouse motion.
    """

    def __init__(self, draw_app):
        self.draw_app = draw_app
        self.complete = False
        self.points = []
        self.geometry = None  # DrawToolShape or None

    def click(self, point):
        """
        :param point: [x, y] Coordinate pair.
        """
        return ""

    def click_release(self, point):
        """
        :param point: [x, y] Coordinate pair.
        """
        return ""

    def on_key(self, key):
        # Jump to coords
        if key == QtCore.Qt.Key_J or key == 'J':
            self.draw_app.app.on_jump_to()
        return

    def utility_geometry(self, data=None):
        return None

    @staticmethod
    def bounds(obj):
        def bounds_rec(o):
            if type(o) is list:
                minx = np.Inf
                miny = np.Inf
                maxx = -np.Inf
                maxy = -np.Inf

                for k in o:
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
                return o.geo.bounds

        bounds_coords = bounds_rec(obj)
        return bounds_coords


class FCShapeTool(DrawTool):
    """
    Abstract class for tools that create a shape.
    """

    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)

        self.name = None

    def make(self):
        pass


class FCCircle(FCShapeTool):
    """
    Resulting type: Polygon
    """

    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.name = 'circle'

        self.draw_app = draw_app

        try:
            QtGui.QGuiApplication.restoreOverrideCursor()
        except Exception:
            pass
        self.cursor = QtGui.QCursor(QtGui.QPixmap(self.draw_app.app.resource_location + '/aero_circle_geo.png'))
        QtGui.QGuiApplication.setOverrideCursor(self.cursor)

        self.draw_app.app.jump_signal.connect(lambda x: self.draw_app.update_utility_geometry(data=x))

        self.draw_app.app.inform.emit(_("Click on Center point ..."))
        self.steps_per_circ = self.draw_app.app.defaults["geometry_circle_steps"]

    def click(self, point):
        try:
            self.draw_app.app.jump_signal.disconnect()
        except (TypeError, AttributeError):
            pass
        self.draw_app.app.jump_signal.connect(lambda x: self.draw_app.update_utility_geometry(data=x))

        self.points.append(point)

        if len(self.points) == 1:
            self.draw_app.app.inform.emit(_("Click on Perimeter point to complete ..."))
            return "Click on perimeter to complete ..."

        if len(self.points) == 2:
            self.make()
            return "Done."

        return ""

    def utility_geometry(self, data=None):
        if len(self.points) == 1:
            p1 = self.points[0]
            p2 = data
            radius = np.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)
            return DrawToolUtilityShape(Point(p1).buffer(radius, int(self.steps_per_circ / 4)))

        return None

    def make(self):
        try:
            QtGui.QGuiApplication.restoreOverrideCursor()
        except Exception:
            pass

        p1 = self.points[0]
        p2 = self.points[1]
        radius = distance(p1, p2)
        self.geometry = DrawToolShape(Point(p1).buffer(radius, int(self.steps_per_circ / 4)))
        self.complete = True

        self.draw_app.app.jump_signal.disconnect()

        self.draw_app.app.inform.emit('[success] %s' % _("Done."))

    def clean_up(self):
        self.draw_app.selected = []
        self.draw_app.plot_all()

        try:
            self.draw_app.app.jump_signal.disconnect()
        except (TypeError, AttributeError):
            pass


class FCArc(FCShapeTool):
    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.name = 'arc'

        self.draw_app = draw_app

        try:
            QtGui.QGuiApplication.restoreOverrideCursor()
        except Exception:
            pass
        self.cursor = QtGui.QCursor(QtGui.QPixmap(self.draw_app.app.resource_location + '/aero_arc.png'))
        QtGui.QGuiApplication.setOverrideCursor(self.cursor)

        self.draw_app.app.inform.emit(_("Click on Center point ..."))

        # Direction of rotation between point 1 and 2.
        # 'cw' or 'ccw'. Switch direction by hitting the
        # 'o' key.
        self.direction = "cw"

        # Mode
        # C12 = Center, p1, p2
        # 12C = p1, p2, Center
        # 132 = p1, p3, p2
        self.mode = "c12"  # Center, p1, p2

        self.draw_app.app.jump_signal.connect(lambda x: self.draw_app.update_utility_geometry(data=x))

        self.steps_per_circ = self.draw_app.app.defaults["geometry_circle_steps"]

    def click(self, point):
        try:
            self.draw_app.app.jump_signal.disconnect()
        except (TypeError, AttributeError):
            pass
        self.draw_app.app.jump_signal.connect(lambda x: self.draw_app.update_utility_geometry(data=x))

        self.points.append(point)

        if len(self.points) == 1:
            if self.mode == 'c12':
                self.draw_app.app.inform.emit(_("Click on Start point ..."))
            elif self.mode == '132':
                self.draw_app.app.inform.emit(_("Click on Point3 ..."))
            else:
                self.draw_app.app.inform.emit(_("Click on Stop point ..."))
            return "Click on 1st point ..."

        if len(self.points) == 2:
            if self.mode == 'c12':
                self.draw_app.app.inform.emit(_("Click on Stop point to complete ..."))
            elif self.mode == '132':
                self.draw_app.app.inform.emit(_("Click on Point2 to complete ..."))
            else:
                self.draw_app.app.inform.emit(_("Click on Center point to complete ..."))
            return "Click on 2nd point to complete ..."

        if len(self.points) == 3:
            self.make()
            return "Done."

        return ""

    def on_key(self, key):
        if key == 'D' or key == QtCore.Qt.Key_D:
            self.direction = 'cw' if self.direction == 'ccw' else 'ccw'
            return '%s: %s' % (_('Direction'), self.direction.upper())

        # Jump to coords
        if key == QtCore.Qt.Key_J or key == 'J':
            self.draw_app.app.on_jump_to()

        if key == 'M' or key == QtCore.Qt.Key_M:
            # delete the possible points made before this action; we want to start anew
            self.points[:] = []
            # and delete the utility geometry made up until this point
            self.draw_app.delete_utility_geometry()

            if self.mode == 'c12':
                self.mode = '12c'
                return _('Mode: Start -> Stop -> Center. Click on Start point ...')
            elif self.mode == '12c':
                self.mode = '132'
                return _('Mode: Point1 -> Point3 -> Point2. Click on Point1 ...')
            else:
                self.mode = 'c12'
                return _('Mode: Center -> Start -> Stop. Click on Center point ...')

    def utility_geometry(self, data=None):
        if len(self.points) == 1:  # Show the radius
            center = self.points[0]
            p1 = data

            return DrawToolUtilityShape(LineString([center, p1]))

        if len(self.points) == 2:  # Show the arc

            if self.mode == 'c12':
                center = self.points[0]
                p1 = self.points[1]
                p2 = data

                radius = np.sqrt((center[0] - p1[0]) ** 2 + (center[1] - p1[1]) ** 2)
                startangle = np.arctan2(p1[1] - center[1], p1[0] - center[0])
                stopangle = np.arctan2(p2[1] - center[1], p2[0] - center[0])

                return DrawToolUtilityShape([LineString(arc(center, radius, startangle, stopangle,
                                                            self.direction, self.steps_per_circ)),
                                             Point(center)])

            elif self.mode == '132':
                p1 = np.array(self.points[0])
                p3 = np.array(self.points[1])
                p2 = np.array(data)

                try:
                    center, radius, t = three_point_circle(p1, p2, p3)
                except TypeError:
                    return

                direction = 'cw' if np.sign(t) > 0 else 'ccw'

                startangle = np.arctan2(p1[1] - center[1], p1[0] - center[0])
                stopangle = np.arctan2(p3[1] - center[1], p3[0] - center[0])

                return DrawToolUtilityShape([LineString(arc(center, radius, startangle, stopangle,
                                                            direction, self.steps_per_circ)),
                                             Point(center), Point(p1), Point(p3)])

            else:  # '12c'
                p1 = np.array(self.points[0])
                p2 = np.array(self.points[1])

                # Midpoint
                a = (p1 + p2) / 2.0

                # Parallel vector
                c = p2 - p1

                # Perpendicular vector
                b = np.dot(c, np.array([[0, -1], [1, 0]], dtype=np.float32))
                b /= numpy_norm(b)

                # Distance
                t = distance(data, a)

                # Which side? Cross product with c.
                # cross(M-A, B-A), where line is AB and M is test point.
                side = (data[0] - p1[0]) * c[1] - (data[1] - p1[1]) * c[0]
                t *= np.sign(side)

                # Center = a + bt
                center = a + b * t

                radius = numpy_norm(center - p1)
                startangle = np.arctan2(p1[1] - center[1], p1[0] - center[0])
                stopangle = np.arctan2(p2[1] - center[1], p2[0] - center[0])

                return DrawToolUtilityShape([LineString(arc(center, radius, startangle, stopangle,
                                                            self.direction, self.steps_per_circ)),
                                             Point(center)])

        return None

    def make(self):

        if self.mode == 'c12':
            center = self.points[0]
            p1 = self.points[1]
            p2 = self.points[2]

            radius = distance(center, p1)
            startangle = np.arctan2(p1[1] - center[1], p1[0] - center[0])
            stopangle = np.arctan2(p2[1] - center[1], p2[0] - center[0])
            self.geometry = DrawToolShape(LineString(arc(center, radius, startangle, stopangle,
                                                         self.direction, self.steps_per_circ)))

        elif self.mode == '132':
            p1 = np.array(self.points[0])
            p3 = np.array(self.points[1])
            p2 = np.array(self.points[2])

            center, radius, t = three_point_circle(p1, p2, p3)
            direction = 'cw' if np.sign(t) > 0 else 'ccw'

            startangle = np.arctan2(p1[1] - center[1], p1[0] - center[0])
            stopangle = np.arctan2(p3[1] - center[1], p3[0] - center[0])

            self.geometry = DrawToolShape(LineString(arc(center, radius, startangle, stopangle,
                                                         direction, self.steps_per_circ)))

        else:  # self.mode == '12c'
            p1 = np.array(self.points[0])
            p2 = np.array(self.points[1])
            pc = np.array(self.points[2])

            # Midpoint
            a = (p1 + p2) / 2.0

            # Parallel vector
            c = p2 - p1

            # Perpendicular vector
            b = np.dot(c, np.array([[0, -1], [1, 0]], dtype=np.float32))
            b /= numpy_norm(b)

            # Distance
            t = distance(pc, a)

            # Which side? Cross product with c.
            # cross(M-A, B-A), where line is AB and M is test point.
            side = (pc[0] - p1[0]) * c[1] - (pc[1] - p1[1]) * c[0]
            t *= np.sign(side)

            # Center = a + bt
            center = a + b * t

            radius = numpy_norm(center - p1)
            startangle = np.arctan2(p1[1] - center[1], p1[0] - center[0])
            stopangle = np.arctan2(p2[1] - center[1], p2[0] - center[0])

            self.geometry = DrawToolShape(LineString(arc(center, radius, startangle, stopangle,
                                                         self.direction, self.steps_per_circ)))
        self.complete = True

        self.draw_app.app.jump_signal.disconnect()

        self.draw_app.app.inform.emit('[success] %s' % _("Done."))

    def clean_up(self):
        self.draw_app.selected = []
        self.draw_app.plot_all()

        try:
            self.draw_app.app.jump_signal.disconnect()
        except (TypeError, AttributeError):
            pass


class FCRectangle(FCShapeTool):
    """
    Resulting type: Polygon
    """

    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.name = 'rectangle'
        self.draw_app = draw_app

        try:
            QtGui.QGuiApplication.restoreOverrideCursor()
        except Exception:
            pass
        self.cursor = QtGui.QCursor(QtGui.QPixmap(self.draw_app.app.resource_location + '/aero.png'))
        QtGui.QGuiApplication.setOverrideCursor(self.cursor)

        self.draw_app.app.jump_signal.connect(lambda x: self.draw_app.update_utility_geometry(data=x))

        self.draw_app.app.inform.emit(_("Click on 1st corner ..."))

    def click(self, point):
        try:
            self.draw_app.app.jump_signal.disconnect()
        except (TypeError, AttributeError):
            pass
        self.draw_app.app.jump_signal.connect(lambda x: self.draw_app.update_utility_geometry(data=x))

        self.points.append(point)

        if len(self.points) == 1:
            self.draw_app.app.inform.emit(_("Click on opposite corner to complete ..."))
            return "Click on opposite corner to complete ..."

        if len(self.points) == 2:
            self.make()
            return "Done."

        return ""

    def utility_geometry(self, data=None):
        if len(self.points) == 1:
            p1 = self.points[0]
            p2 = data
            return DrawToolUtilityShape(LinearRing([p1, (p2[0], p1[1]), p2, (p1[0], p2[1])]))

        return None

    def make(self):
        try:
            QtGui.QGuiApplication.restoreOverrideCursor()
        except Exception:
            pass

        p1 = self.points[0]
        p2 = self.points[1]
        # self.geometry = LinearRing([p1, (p2[0], p1[1]), p2, (p1[0], p2[1])])
        self.geometry = DrawToolShape(Polygon([p1, (p2[0], p1[1]), p2, (p1[0], p2[1])]))
        self.complete = True

        self.draw_app.app.jump_signal.disconnect()
        self.draw_app.app.inform.emit('[success] %s' % _("Done."))

    def clean_up(self):
        self.draw_app.selected = []
        self.draw_app.plot_all()

        try:
            self.draw_app.app.jump_signal.disconnect()
        except (TypeError, AttributeError):
            pass


class FCPolygon(FCShapeTool):
    """
    Resulting type: Polygon
    """

    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.name = 'polygon'
        self.draw_app = draw_app

        try:
            QtGui.QGuiApplication.restoreOverrideCursor()
        except Exception:
            pass
        self.cursor = QtGui.QCursor(QtGui.QPixmap(self.draw_app.app.resource_location + '/aero.png'))
        QtGui.QGuiApplication.setOverrideCursor(self.cursor)

        self.draw_app.app.jump_signal.connect(lambda x: self.draw_app.update_utility_geometry(data=x))

        self.draw_app.app.inform.emit(_("Click on 1st corner ..."))

    def click(self, point):
        try:
            self.draw_app.app.jump_signal.disconnect()
        except (TypeError, AttributeError):
            pass
        self.draw_app.app.jump_signal.connect(lambda x: self.draw_app.update_utility_geometry(data=x))

        self.draw_app.in_action = True
        self.points.append(point)

        if len(self.points) > 0:
            self.draw_app.app.inform.emit(_("Click on next Point or click right mouse button to complete ..."))
            return "Click on next point or hit ENTER to complete ..."

        return ""

    def utility_geometry(self, data=None):
        if len(self.points) == 1:
            temp_points = [x for x in self.points]
            temp_points.append(data)
            return DrawToolUtilityShape(LineString(temp_points))

        if len(self.points) > 1:
            temp_points = [x for x in self.points]
            temp_points.append(data)
            return DrawToolUtilityShape(LinearRing(temp_points))

        return None

    def make(self):
        try:
            QtGui.QGuiApplication.restoreOverrideCursor()
        except Exception:
            pass

        # self.geometry = LinearRing(self.points)
        self.geometry = DrawToolShape(Polygon(self.points))
        self.draw_app.in_action = False
        self.complete = True

        self.draw_app.app.jump_signal.disconnect()

        self.draw_app.app.inform.emit('[success] %s' % _("Done."))

    def on_key(self, key):
        # Jump to coords
        if key == QtCore.Qt.Key_J or key == 'J':
            self.draw_app.app.on_jump_to()

        if key == 'Backspace' or key == QtCore.Qt.Key_Backspace:
            if len(self.points) > 0:
                self.points = self.points[0:-1]
                # Remove any previous utility shape
                self.draw_app.tool_shape.clear(update=False)
                geo = self.utility_geometry(data=(self.draw_app.snap_x, self.draw_app.snap_y))
                self.draw_app.draw_utility_geometry(geo=geo)
                return _("Backtracked one point ...")

    def clean_up(self):
        self.draw_app.selected = []
        self.draw_app.plot_all()

        try:
            self.draw_app.app.jump_signal.disconnect()
        except (TypeError, AttributeError):
            pass


class FCPath(FCPolygon):
    """
    Resulting type: LineString
    """
    def __init__(self, draw_app):
        FCPolygon.__init__(self, draw_app)
        self.draw_app = draw_app

        try:
            QtGui.QGuiApplication.restoreOverrideCursor()
        except Exception:
            pass
        self.cursor = QtGui.QCursor(QtGui.QPixmap(self.draw_app.app.resource_location + '/aero_path5.png'))
        QtGui.QGuiApplication.setOverrideCursor(self.cursor)

        self.draw_app.app.jump_signal.connect(lambda x: self.draw_app.update_utility_geometry(data=x))

    def make(self):
        self.geometry = DrawToolShape(LineString(self.points))
        self.name = 'path'

        try:
            QtGui.QGuiApplication.restoreOverrideCursor()
        except Exception as e:
            pass

        self.draw_app.in_action = False
        self.complete = True

        self.draw_app.app.jump_signal.disconnect()

        self.draw_app.app.inform.emit('[success] %s' % _("Done."))

    def utility_geometry(self, data=None):
        if len(self.points) > 0:
            temp_points = [x for x in self.points]
            temp_points.append(data)
            return DrawToolUtilityShape(LineString(temp_points))

        return None

    def on_key(self, key):
        # Jump to coords
        if key == QtCore.Qt.Key_J or key == 'J':
            self.draw_app.app.on_jump_to()

        if key == 'Backspace' or key == QtCore.Qt.Key_Backspace:
            if len(self.points) > 0:
                self.points = self.points[0:-1]
                # Remove any previous utility shape
                self.draw_app.tool_shape.clear(update=False)
                geo = self.utility_geometry(data=(self.draw_app.snap_x, self.draw_app.snap_y))
                self.draw_app.draw_utility_geometry(geo=geo)
                return _("Backtracked one point ...")

    def clean_up(self):
        self.draw_app.selected = []
        self.draw_app.plot_all()

        try:
            self.draw_app.app.jump_signal.disconnect()
        except (TypeError, AttributeError):
            pass


class FCSelect(DrawTool):
    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.name = 'select'
        self.draw_app = draw_app

        try:
            QtGui.QGuiApplication.restoreOverrideCursor()
        except Exception:
            pass

        self.storage = self.draw_app.storage
        # self.shape_buffer = self.draw_app.shape_buffer
        # self.selected = self.draw_app.selected

    def click_release(self, point):
        """

        :param point:   The point for which to find the neasrest shape
        :return:
        """

        # list where we store the overlapped shapes under our mouse left click position
        over_shape_list = []

        # pos[0] and pos[1] are the mouse click coordinates (x, y)
        for ____ in self.storage.get_objects():
            # first method of click selection -> inconvenient
            # minx, miny, maxx, maxy = obj_shape.geo.bounds
            # if (minx <= pos[0] <= maxx) and (miny <= pos[1] <= maxy):
            #     over_shape_list.append(obj_shape)

            # second method of click selection -> slow
            # outside = obj_shape.geo.buffer(0.1)
            # inside = obj_shape.geo.buffer(-0.1)
            # shape_band = outside.difference(inside)
            # if Point(pos).within(shape_band):
            #     over_shape_list.append(obj_shape)

            # 3rd method of click selection -> inconvenient
            try:
                __, closest_shape = self.storage.nearest(point)
            except StopIteration:
                return ""

            over_shape_list.append(closest_shape)

        try:
            # if there is no shape under our click then deselect all shapes
            # it will not work for 3rd method of click selection
            if not over_shape_list:
                self.draw_app.selected = []
                AppGeoEditor.draw_shape_idx = -1
            else:
                # if there are shapes under our click then advance through the list of them, one at the time in a
                # circular way
                AppGeoEditor.draw_shape_idx = (AppGeoEditor.draw_shape_idx + 1) % len(over_shape_list)
                obj_to_add = over_shape_list[int(AppGeoEditor.draw_shape_idx)]

                key_modifier = QtWidgets.QApplication.keyboardModifiers()

                if key_modifier == QtCore.Qt.ShiftModifier:
                    mod_key = 'Shift'
                elif key_modifier == QtCore.Qt.ControlModifier:
                    mod_key = 'Control'
                else:
                    mod_key = None

                if mod_key == self.draw_app.app.defaults["global_mselect_key"]:
                    # if modifier key is pressed then we add to the selected list the current shape but if it's already
                    # in the selected list, we removed it. Therefore first click selects, second deselects.
                    if obj_to_add in self.draw_app.selected:
                        self.draw_app.selected.remove(obj_to_add)
                    else:
                        self.draw_app.selected.append(obj_to_add)
                else:
                    self.draw_app.selected = []
                    self.draw_app.selected.append(obj_to_add)
        except Exception as e:
            log.error("[ERROR] AppGeoEditor.FCSelect.click_release() -> Something went bad. %s" % str(e))

        # if selection is done on canvas update the Tree in Selected Tab with the selection
        try:
            self.draw_app.tw.itemSelectionChanged.disconnect(self.draw_app.on_tree_selection_change)
        except (AttributeError, TypeError):
            pass

        self.draw_app.tw.selectionModel().clearSelection()
        for sel_shape in self.draw_app.selected:
            iterator = QtWidgets.QTreeWidgetItemIterator(self.draw_app.tw)
            while iterator.value():
                item = iterator.value()
                try:
                    if int(item.text(1)) == id(sel_shape):
                        item.setSelected(True)
                except ValueError:
                    pass

                iterator += 1

        self.draw_app.tw.itemSelectionChanged.connect(self.draw_app.on_tree_selection_change)

        return ""

    def clean_up(self):
        pass


class FCExplode(FCShapeTool):
    def __init__(self, draw_app):
        FCShapeTool.__init__(self, draw_app)
        self.name = 'explode'
        self.draw_app = draw_app

        try:
            QtGui.QGuiApplication.restoreOverrideCursor()
        except Exception:
            pass

        self.storage = self.draw_app.storage
        self.origin = (0, 0)
        self.destination = None

        self.draw_app.active_tool = self
        if len(self.draw_app.get_selected()) == 0:
            self.draw_app.app.inform.emit('[WARNING_NOTCL] %s' % _("No shape selected."))
        else:
            self.make()

    def make(self):
        to_be_deleted_list = []
        lines = []

        for shape in self.draw_app.get_selected():
            to_be_deleted_list.append(shape)
            geo = shape.geo
            ext_coords = list(geo.exterior.coords)

            for c in range(len(ext_coords)):
                if c < len(ext_coords) - 1:
                    lines.append(LineString([ext_coords[c], ext_coords[c + 1]]))

            for int_geo in geo.interiors:
                int_coords = list(int_geo.coords)
                for c in range(len(int_coords)):
                    if c < len(int_coords):
                        lines.append(LineString([int_coords[c], int_coords[c + 1]]))

        for shape in to_be_deleted_list:
            self.draw_app.storage.remove(shape)
            if shape in self.draw_app.selected:
                self.draw_app.selected.remove(shape)

        geo_list = []
        for line in lines:
            geo_list.append(DrawToolShape(line))
        self.geometry = geo_list
        self.draw_app.on_shape_complete()
        self.draw_app.app.inform.emit('[success] %s...' % _("Done."))

    def clean_up(self):
        self.draw_app.selected = []
        self.draw_app.plot_all()

        try:
            self.draw_app.app.jump_signal.disconnect()
        except (TypeError, AttributeError):
            pass


class FCMove(FCShapeTool):
    def __init__(self, draw_app):
        FCShapeTool.__init__(self, draw_app)
        self.name = 'move'
        self.draw_app = draw_app

        try:
            QtGui.QGuiApplication.restoreOverrideCursor()
        except Exception:
            pass

        self.storage = self.draw_app.storage

        self.origin = None
        self.destination = None
        self.sel_limit = self.draw_app.app.defaults["geometry_editor_sel_limit"]
        self.selection_shape = self.selection_bbox()

        if len(self.draw_app.get_selected()) == 0:
            self.draw_app.app.inform.emit('[WARNING_NOTCL] %s' % _("No shape selected."))
            return
        else:
            self.draw_app.app.inform.emit(_("Click on reference location ..."))

        self.draw_app.app.jump_signal.connect(lambda x: self.draw_app.update_utility_geometry(data=x))

    def set_origin(self, origin):
        self.draw_app.app.inform.emit(_("Click on destination point ..."))
        self.origin = origin

    def click(self, point):
        try:
            self.draw_app.app.jump_signal.disconnect()
        except (TypeError, AttributeError):
            pass
        self.draw_app.app.jump_signal.connect(lambda x: self.draw_app.update_utility_geometry(data=x))

        if len(self.draw_app.get_selected()) == 0:
            # self.complete = True
            # self.draw_app.app.inform.emit(_("[WARNING_NOTCL] Move cancelled. No shape selected."))
            self.select_shapes(point)
            self.draw_app.replot()
            self.draw_app.app.inform.emit(_("Click on reference location ..."))
            return

        if self.origin is None:
            self.set_origin(point)
            self.selection_shape = self.selection_bbox()
            return "Click on final location."
        else:
            self.destination = point
            self.make()
            # self.draw_app.app.worker_task.emit(({'fcn': self.make,
            #                                      'params': []}))
            return "Done."

    def make(self):
        with self.draw_app.app.proc_container.new(_("Moving ...")):
            # Create new geometry
            dx = self.destination[0] - self.origin[0]
            dy = self.destination[1] - self.origin[1]
            self.geometry = [DrawToolShape(affinity.translate(geom.geo, xoff=dx, yoff=dy))
                             for geom in self.draw_app.get_selected()]

            # Delete old
            self.draw_app.delete_selected()
            self.complete = True
            self.draw_app.app.inform.emit('[success] %s' % _("Done."))
            try:
                self.draw_app.app.jump_signal.disconnect()
            except TypeError:
                pass

    def selection_bbox(self):
        geo_list = []
        for select_shape in self.draw_app.get_selected():
            geometric_data = select_shape.geo
            try:
                for g in geometric_data:
                    geo_list.append(g)
            except TypeError:
                geo_list.append(geometric_data)

        xmin, ymin, xmax, ymax = get_shapely_list_bounds(geo_list)

        pt1 = (xmin, ymin)
        pt2 = (xmax, ymin)
        pt3 = (xmax, ymax)
        pt4 = (xmin, ymax)

        return Polygon([pt1, pt2, pt3, pt4])

    def utility_geometry(self, data=None):
        """
        Temporary geometry on screen while using this tool.

        :param data:
        :return:
        """
        geo_list = []

        if self.origin is None:
            return None

        if len(self.draw_app.get_selected()) == 0:
            return None

        dx = data[0] - self.origin[0]
        dy = data[1] - self.origin[1]

        if len(self.draw_app.get_selected()) <= self.sel_limit:
            try:
                for geom in self.draw_app.get_selected():
                    geo_list.append(affinity.translate(geom.geo, xoff=dx, yoff=dy))
            except AttributeError:
                self.draw_app.select_tool('select')
                self.draw_app.selected = []
                return
            return DrawToolUtilityShape(geo_list)
        else:
            try:
                ss_el = affinity.translate(self.selection_shape, xoff=dx, yoff=dy)
            except ValueError:
                ss_el = None
            return DrawToolUtilityShape(ss_el)

    def select_shapes(self, pos):
        # list where we store the overlapped shapes under our mouse left click position
        over_shape_list = []

        try:
            _, closest_shape = self.storage.nearest(pos)
        except StopIteration:
            return ""

        over_shape_list.append(closest_shape)

        try:
            # if there is no shape under our click then deselect all shapes
            # it will not work for 3rd method of click selection
            if not over_shape_list:
                self.draw_app.selected = []
                self.draw_app.draw_shape_idx = -1
            else:
                # if there are shapes under our click then advance through the list of them, one at the time in a
                # circular way
                self.draw_app.draw_shape_idx = (AppGeoEditor.draw_shape_idx + 1) % len(over_shape_list)
                try:
                    obj_to_add = over_shape_list[int(AppGeoEditor.draw_shape_idx)]
                except IndexError:
                    return

                key_modifier = QtWidgets.QApplication.keyboardModifiers()
                if self.draw_app.app.defaults["global_mselect_key"] == 'Control':
                    # if CONTROL key is pressed then we add to the selected list the current shape but if it's
                    # already in the selected list, we removed it. Therefore first click selects, second deselects.
                    if key_modifier == Qt.ControlModifier:
                        if obj_to_add in self.draw_app.selected:
                            self.draw_app.selected.remove(obj_to_add)
                        else:
                            self.draw_app.selected.append(obj_to_add)
                    else:
                        self.draw_app.selected = []
                        self.draw_app.selected.append(obj_to_add)
                else:
                    if key_modifier == Qt.ShiftModifier:
                        if obj_to_add in self.draw_app.selected:
                            self.draw_app.selected.remove(obj_to_add)
                        else:
                            self.draw_app.selected.append(obj_to_add)
                    else:
                        self.draw_app.selected = []
                        self.draw_app.selected.append(obj_to_add)

        except Exception as e:
            log.error("[ERROR] Something went bad. %s" % str(e))
            raise

    def clean_up(self):
        self.draw_app.selected = []
        self.draw_app.plot_all()

        try:
            self.draw_app.app.jump_signal.disconnect()
        except (TypeError, AttributeError):
            pass


class FCCopy(FCMove):
    def __init__(self, draw_app):
        FCMove.__init__(self, draw_app)
        self.name = 'copy'

    def make(self):
        # Create new geometry
        dx = self.destination[0] - self.origin[0]
        dy = self.destination[1] - self.origin[1]
        self.geometry = [DrawToolShape(affinity.translate(geom.geo, xoff=dx, yoff=dy))
                         for geom in self.draw_app.get_selected()]
        self.complete = True
        self.draw_app.app.inform.emit('[success] %s' % _("Done."))
        try:
            self.draw_app.app.jump_signal.disconnect()
        except (TypeError, AttributeError):
            pass

    def clean_up(self):
        self.draw_app.selected = []
        self.draw_app.plot_all()

        try:
            self.draw_app.app.jump_signal.disconnect()
        except (TypeError, AttributeError):
            pass


class FCText(FCShapeTool):
    def __init__(self, draw_app):
        FCShapeTool.__init__(self, draw_app)
        self.name = 'text'
        self.draw_app = draw_app

        try:
            QtGui.QGuiApplication.restoreOverrideCursor()
        except Exception:
            pass
        self.cursor = QtGui.QCursor(QtGui.QPixmap(self.draw_app.app.resource_location + '/aero_text.png'))
        QtGui.QGuiApplication.setOverrideCursor(self.cursor)

        self.app = draw_app.app

        self.draw_app.app.inform.emit(_("Click on 1st point ..."))
        self.origin = (0, 0)

        self.text_gui = TextInputTool(app=self.app)
        self.text_gui.run()
        self.draw_app.app.jump_signal.connect(lambda x: self.draw_app.update_utility_geometry(data=x))

    def click(self, point):
        try:
            self.draw_app.app.jump_signal.disconnect()
        except (TypeError, AttributeError):
            pass
        self.draw_app.app.jump_signal.connect(lambda x: self.draw_app.update_utility_geometry(data=x))

        # Create new geometry
        dx = point[0]
        dy = point[1]

        if self.text_gui.text_path:
            try:
                self.geometry = DrawToolShape(affinity.translate(self.text_gui.text_path, xoff=dx, yoff=dy))
            except Exception as e:
                log.debug("Font geometry is empty or incorrect: %s" % str(e))
                self.draw_app.app.inform.emit('[ERROR] %s: %s' %
                                              (_("Font not supported. Only Regular, Bold, Italic and BoldItalic are "
                                                 "supported. Error"), str(e)))
                self.text_gui.text_path = []
                self.text_gui.hide_tool()
                self.draw_app.select_tool('select')
                self.draw_app.app.jump_signal.disconnect()
                return
        else:
            self.draw_app.app.inform.emit('[WARNING_NOTCL] %s' % _("No text to add."))
            try:
                self.draw_app.app.jump_signal.disconnect()
            except (TypeError, AttributeError):
                pass
            return

        self.text_gui.text_path = []
        self.text_gui.hide_tool()
        self.complete = True
        self.draw_app.app.inform.emit('[success]%s' % _("Done."))

    def utility_geometry(self, data=None):
        """
        Temporary geometry on screen while using this tool.

        :param data: mouse position coords
        :return:
        """

        dx = data[0] - self.origin[0]
        dy = data[1] - self.origin[1]

        try:
            return DrawToolUtilityShape(affinity.translate(self.text_gui.text_path, xoff=dx, yoff=dy))
        except Exception:
            return

    def clean_up(self):
        self.draw_app.selected = []
        self.draw_app.plot_all()

        try:
            self.draw_app.app.jump_signal.disconnect()
        except (TypeError, AttributeError):
            pass


class FCBuffer(FCShapeTool):
    def __init__(self, draw_app):
        FCShapeTool.__init__(self, draw_app)
        self.name = 'buffer'

        # self.shape_buffer = self.draw_app.shape_buffer
        self.draw_app = draw_app
        self.app = draw_app.app

        self.draw_app.app.inform.emit(_("Create buffer geometry ..."))
        self.origin = (0, 0)
        self.buff_tool = BufferSelectionTool(self.app, self.draw_app)
        self.buff_tool.run()
        self.app.ui.notebook.setTabText(2, _("Buffer Tool"))
        if self.draw_app.app.ui.splitter.sizes()[0] == 0:
            self.draw_app.app.ui.splitter.setSizes([1, 1])
        self.activate()

    def on_buffer(self):
        if not self.draw_app.selected:
            self.draw_app.app.inform.emit('[WARNING_NOTCL] %s %s' % (_("Cancelled."), _("No shape selected.")))
            return

        try:
            buffer_distance = float(self.buff_tool.buffer_distance_entry.get_value())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                buffer_distance = float(self.buff_tool.buffer_distance_entry.get_value().replace(',', '.'))
                self.buff_tool.buffer_distance_entry.set_value(buffer_distance)
            except ValueError:
                self.app.inform.emit('[WARNING_NOTCL] %s' %
                                     _("Buffer distance value is missing or wrong format. Add it and retry."))
                return
        # the cb index start from 0 but the join styles for the buffer start from 1 therefore the adjustment
        # I populated the combobox such that the index coincide with the join styles value (whcih is really an INT)
        join_style = self.buff_tool.buffer_corner_cb.currentIndex() + 1
        ret_val = self.draw_app.buffer(buffer_distance, join_style)
        self.app.ui.notebook.setTabText(2, _("Tools"))
        self.draw_app.app.ui.splitter.setSizes([0, 1])

        self.disactivate()
        if ret_val == 'fail':
            return
        self.draw_app.app.inform.emit('[success] %s' % _("Done."))

    def on_buffer_int(self):
        if not self.draw_app.selected:
            self.draw_app.app.inform.emit('[WARNING_NOTCL] %s %s' % (_("Cancelled."), _("No shape selected.")))
            return

        try:
            buffer_distance = float(self.buff_tool.buffer_distance_entry.get_value())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                buffer_distance = float(self.buff_tool.buffer_distance_entry.get_value().replace(',', '.'))
                self.buff_tool.buffer_distance_entry.set_value(buffer_distance)
            except ValueError:
                self.app.inform.emit('[WARNING_NOTCL] %s' %
                                     _("Buffer distance value is missing or wrong format. Add it and retry."))
                return
        # the cb index start from 0 but the join styles for the buffer start from 1 therefore the adjustment
        # I populated the combobox such that the index coincide with the join styles value (whcih is really an INT)
        join_style = self.buff_tool.buffer_corner_cb.currentIndex() + 1
        ret_val = self.draw_app.buffer_int(buffer_distance, join_style)
        self.app.ui.notebook.setTabText(2, _("Tools"))
        self.draw_app.app.ui.splitter.setSizes([0, 1])

        self.disactivate()
        if ret_val == 'fail':
            return
        self.draw_app.app.inform.emit('[success] %s' % _("Done."))

    def on_buffer_ext(self):
        if not self.draw_app.selected:
            self.draw_app.app.inform.emit('[WARNING_NOTCL] %s %s' % (_("Cancelled."), _("No shape selected.")))
            return

        try:
            buffer_distance = float(self.buff_tool.buffer_distance_entry.get_value())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                buffer_distance = float(self.buff_tool.buffer_distance_entry.get_value().replace(',', '.'))
                self.buff_tool.buffer_distance_entry.set_value(buffer_distance)
            except ValueError:
                self.draw_app.app.inform.emit('[WARNING_NOTCL] %s' %
                                     _("Buffer distance value is missing or wrong format. Add it and retry."))
                return
        # the cb index start from 0 but the join styles for the buffer start from 1 therefore the adjustment
        # I populated the combobox such that the index coincide with the join styles value (whcih is really an INT)
        join_style = self.buff_tool.buffer_corner_cb.currentIndex() + 1
        ret_val = self.draw_app.buffer_ext(buffer_distance, join_style)
        self.app.ui.notebook.setTabText(2, _("Tools"))
        self.draw_app.app.ui.splitter.setSizes([0, 1])

        self.disactivate()
        if ret_val == 'fail':
            return
        self.draw_app.app.inform.emit('[success] %s' % _("Done."))

    def activate(self):
        self.buff_tool.buffer_button.clicked.disconnect()
        self.buff_tool.buffer_int_button.clicked.disconnect()
        self.buff_tool.buffer_ext_button.clicked.disconnect()

        self.buff_tool.buffer_button.clicked.connect(self.on_buffer)
        self.buff_tool.buffer_int_button.clicked.connect(self.on_buffer_int)
        self.buff_tool.buffer_ext_button.clicked.connect(self.on_buffer_ext)

    def disactivate(self):
        self.buff_tool.buffer_button.clicked.disconnect()
        self.buff_tool.buffer_int_button.clicked.disconnect()
        self.buff_tool.buffer_ext_button.clicked.disconnect()

        self.buff_tool.buffer_button.clicked.connect(self.buff_tool.on_buffer)
        self.buff_tool.buffer_int_button.clicked.connect(self.buff_tool.on_buffer_int)
        self.buff_tool.buffer_ext_button.clicked.connect(self.buff_tool.on_buffer_ext)
        self.complete = True
        self.draw_app.select_tool("select")
        self.buff_tool.hide_tool()
        try:
            self.draw_app.app.jump_signal.disconnect()
        except (TypeError, AttributeError):
            pass

    def clean_up(self):
        self.draw_app.selected = []
        self.draw_app.plot_all()

        try:
            self.draw_app.app.jump_signal.disconnect()
        except (TypeError, AttributeError):
            pass


class FCEraser(FCShapeTool):
    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.name = 'eraser'
        self.draw_app = draw_app

        self.origin = None
        self.destination = None

        if len(self.draw_app.get_selected()) == 0:
            if self.draw_app.launched_from_shortcuts is True:
                self.draw_app.launched_from_shortcuts = False
            self.draw_app.app.inform.emit(_("Select a shape to act as deletion area ..."))
        else:
            self.draw_app.app.inform.emit(_("Click to pick-up the erase shape..."))

        self.geometry = []
        self.storage = self.draw_app.storage

        # Switch notebook to Properties page
        self.draw_app.app.ui.notebook.setCurrentWidget(self.draw_app.app.ui.properties_tab)
        self.draw_app.app.jump_signal.connect(lambda x: self.draw_app.update_utility_geometry(data=x))

    def set_origin(self, origin):
        self.origin = origin

    def click(self, point):
        try:
            self.draw_app.app.jump_signal.disconnect()
        except (TypeError, AttributeError):
            pass
        self.draw_app.app.jump_signal.connect(lambda x: self.draw_app.update_utility_geometry(data=x))

        if len(self.draw_app.get_selected()) == 0:
            for ____ in self.storage.get_objects():
                try:
                    __, closest_shape = self.storage.nearest(point)
                    self.draw_app.selected.append(closest_shape)
                except StopIteration:
                    if len(self.draw_app.selected) > 0:
                        self.draw_app.app.inform.emit(_("Click to pick-up the erase shape..."))
                    return ""

        if len(self.draw_app.get_selected()) == 0:
            return "Nothing to ersase."
        else:
            self.draw_app.app.inform.emit(_("Click to pick-up the erase shape..."))

        if self.origin is None:
            self.set_origin(point)
            self.draw_app.app.inform.emit(_("Click to erase ..."))
            return
        else:
            self.destination = point
            self.make()

            # self.draw_app.select_tool("select")
            return

    def make(self):
        eraser_sel_shapes = []

        # create the eraser shape from selection
        for eraser_shape in self.utility_geometry(data=self.destination).geo:
            temp_shape = eraser_shape.buffer(0.0000001)
            temp_shape = Polygon(temp_shape.exterior)
            eraser_sel_shapes.append(temp_shape)
        eraser_sel_shapes = unary_union(eraser_sel_shapes)

        for obj_shape in self.storage.get_objects():
            try:
                geometric_data = obj_shape.geo
                if eraser_sel_shapes.intersects(geometric_data):
                    obj_shape.geo = geometric_data.difference(eraser_sel_shapes)
            except KeyError:
                pass

        self.draw_app.delete_utility_geometry()
        self.draw_app.plot_all()
        self.draw_app.app.inform.emit('[success] %s' % _("Done."))
        try:
            self.draw_app.app.jump_signal.disconnect()
        except (TypeError, AttributeError):
            pass

    def utility_geometry(self, data=None):
        """
        Temporary geometry on screen while using this tool.

        :param data:
        :return:
        """
        geo_list = []

        if self.origin is None:
            return None

        if len(self.draw_app.get_selected()) == 0:
            return None

        dx = data[0] - self.origin[0]
        dy = data[1] - self.origin[1]

        try:
            for geom in self.draw_app.get_selected():
                geo_list.append(affinity.translate(geom.geo, xoff=dx, yoff=dy))
        except AttributeError:
            self.draw_app.select_tool('select')
            self.draw_app.selected = []
            return
        return DrawToolUtilityShape(geo_list)

    def clean_up(self):
        self.draw_app.selected = []
        self.draw_app.plot_all()

        try:
            self.draw_app.app.jump_signal.disconnect()
        except (TypeError, AttributeError):
            pass


class FCPaint(FCShapeTool):
    def __init__(self, draw_app):
        FCShapeTool.__init__(self, draw_app)
        self.name = 'paint'
        self.draw_app = draw_app
        self.app = draw_app.app

        self.draw_app.app.inform.emit(_("Create Paint geometry ..."))
        self.origin = (0, 0)
        self.draw_app.paint_tool.run()


class FCTransform(FCShapeTool):
    def __init__(self, draw_app):
        FCShapeTool.__init__(self, draw_app)
        self.name = 'transformation'

        self.draw_app = draw_app
        self.app = draw_app.app

        self.draw_app.app.inform.emit(_("Shape transformations ..."))
        self.origin = (0, 0)
        self.draw_app.transform_tool.run()


# ###############################################
# ################ Main Application #############
# ###############################################
class AppGeoEditor(QtCore.QObject):

    # will emit the name of the object that was just selected
    item_selected = QtCore.pyqtSignal(str)

    transform_complete = QtCore.pyqtSignal()

    draw_shape_idx = -1

    def __init__(self, app, disabled=False):
        # assert isinstance(app, FlatCAMApp.App), \
        #     "Expected the app to be a FlatCAMApp.App, got %s" % type(app)

        super(AppGeoEditor, self).__init__()

        self.app = app
        self.canvas = app.plotcanvas
        self.decimals = app.decimals

        self.geo_edit_widget = QtWidgets.QWidget()
        # ## Box for custom widgets
        # This gets populated in offspring implementations.
        layout = QtWidgets.QVBoxLayout()
        self.geo_edit_widget.setLayout(layout)

        # add a frame and inside add a vertical box layout. Inside this vbox layout I add all the Drills widgets
        # this way I can hide/show the frame
        self.geo_frame = QtWidgets.QFrame()
        self.geo_frame.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.geo_frame)
        self.tools_box = QtWidgets.QVBoxLayout()
        self.tools_box.setContentsMargins(0, 0, 0, 0)
        self.geo_frame.setLayout(self.tools_box)

        if disabled:
            self.geo_frame.setDisabled(True)

        # ## Page Title box (spacing between children)
        self.title_box = QtWidgets.QHBoxLayout()
        self.tools_box.addLayout(self.title_box)

        # ## Page Title icon
        pixmap = QtGui.QPixmap(self.app.resource_location + '/flatcam_icon32.png')
        self.icon = FCLabel()
        self.icon.setPixmap(pixmap)
        self.title_box.addWidget(self.icon, stretch=0)

        # ## Title label
        self.title_label = FCLabel("<font size=5><b>%s</b></font>" % _('Geometry Editor'))
        self.title_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.title_box.addWidget(self.title_label, stretch=1)
        self.title_box.addWidget(FCLabel(''))

        self.tw = FCTree(columns=3, header_hidden=False, protected_column=[0, 1], extended_sel=True)
        self.tw.setHeaderLabels(["ID", _("Type"), _("Name")])
        self.tw.setIndentation(0)
        self.tw.header().setStretchLastSection(True)
        self.tw.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.tools_box.addWidget(self.tw)

        self.geo_font = QtGui.QFont()
        self.geo_font.setBold(True)

        self.geo_parent = self.tw.invisibleRootItem()

        layout.addStretch()

        # Editor
        self.exit_editor_button = FCButton(_('Exit Editor'))
        self.exit_editor_button.setIcon(QtGui.QIcon(self.app.resource_location + '/power16.png'))
        self.exit_editor_button.setToolTip(
            _("Exit from Editor.")
        )
        self.exit_editor_button.setStyleSheet("""
                                      QPushButton
                                      {
                                          font-weight: bold;
                                      }
                                      """)
        layout.addWidget(self.exit_editor_button)

        self.exit_editor_button.clicked.connect(lambda: self.app.editor2object())

        # ## Toolbar events and properties
        self.tools = {}

        # # ## Data
        self.active_tool = None

        self.storage = AppGeoEditor.make_storage()
        self.utility = []

        # VisPy visuals
        self.fcgeometry = None
        if self.app.is_legacy is False:
            self.shapes = self.app.plotcanvas.new_shape_collection(layers=1)
            self.tool_shape = self.app.plotcanvas.new_shape_collection(layers=1)
        else:
            from appGUI.PlotCanvasLegacy import ShapeCollectionLegacy
            self.shapes = ShapeCollectionLegacy(obj=self, app=self.app, name='shapes_geo_editor')
            self.tool_shape = ShapeCollectionLegacy(obj=self, app=self.app, name='tool_shapes_geo_editor')

        self.app.pool_recreated.connect(self.pool_recreated)

        # Remove from scene
        self.shapes.enabled = False
        self.tool_shape.enabled = False

        # List of selected shapes.
        self.selected = []

        self.flat_geo = []

        self.move_timer = QtCore.QTimer()
        self.move_timer.setSingleShot(True)

        # this var will store the state of the toolbar before starting the editor
        self.toolbar_old_state = False

        self.key = None  # Currently pressed key
        self.geo_key_modifiers = None
        self.x = None  # Current mouse cursor pos
        self.y = None

        # if we edit a multigeo geometry store here the tool number
        self.multigeo_tool = None

        # Current snapped mouse pos
        self.snap_x = None
        self.snap_y = None
        self.pos = None

        # signal that there is an action active like polygon or path
        self.in_action = False

        self.units = None

        # this will flag if the Editor "tools" are launched from key shortcuts (True) or from menu toolbar (False)
        self.launched_from_shortcuts = False

        self.app.ui.grid_snap_btn.triggered.connect(self.on_grid_toggled)
        self.app.ui.corner_snap_btn.setCheckable(True)
        self.app.ui.corner_snap_btn.triggered.connect(lambda: self.toolbar_tool_toggle("corner_snap"))

        self.options = {
            "global_gridx": 0.1,
            "global_gridy": 0.1,
            "global_snap_max": 0.05,
            "grid_snap": True,
            "corner_snap": False,
            "grid_gap_link": True
        }
        self.options.update(self.app.options)

        for option in self.options:
            if option in self.app.options:
                self.options[option] = self.app.options[option]

        self.app.ui.grid_gap_x_entry.setText(str(self.options["global_gridx"]))
        self.app.ui.grid_gap_y_entry.setText(str(self.options["global_gridy"]))
        self.app.ui.snap_max_dist_entry.setText(str(self.options["global_snap_max"]))
        self.app.ui.grid_gap_link_cb.setChecked(True)

        self.rtree_index = rtindex.Index()

        self.app.ui.grid_gap_x_entry.setValidator(QtGui.QDoubleValidator())
        self.app.ui.grid_gap_x_entry.textChanged.connect(self.on_gridx_val_changed)

        self.app.ui.grid_gap_y_entry.setValidator(QtGui.QDoubleValidator())
        self.app.ui.grid_gap_y_entry.textChanged.connect(self.on_gridy_val_changed)

        self.app.ui.snap_max_dist_entry.setValidator(QtGui.QDoubleValidator())
        self.app.ui.snap_max_dist_entry.textChanged.connect(
            lambda: self.entry2option("snap_max", self.app.ui.snap_max_dist_entry))

        # if using Paint store here the tool diameter used
        self.paint_tooldia = None

        self.paint_tool = PaintOptionsTool(self.app, self)
        self.transform_tool = TransformEditorTool(self.app, self)

        # #############################################################################################################
        # ####################### GEOMETRY Editor Signals #############################################################
        # #############################################################################################################

        # connect the toolbar signals
        self.connect_geo_toolbar_signals()

        # connect Geometry Editor Menu signals
        self.app.ui.geo_add_circle_menuitem.triggered.connect(lambda: self.select_tool('circle'))
        self.app.ui.geo_add_arc_menuitem.triggered.connect(lambda: self.select_tool('arc'))
        self.app.ui.geo_add_rectangle_menuitem.triggered.connect(lambda: self.select_tool('rectangle'))
        self.app.ui.geo_add_polygon_menuitem.triggered.connect(lambda: self.select_tool('polygon'))
        self.app.ui.geo_add_path_menuitem.triggered.connect(lambda: self.select_tool('path'))
        self.app.ui.geo_add_text_menuitem.triggered.connect(lambda: self.select_tool('text'))
        self.app.ui.geo_paint_menuitem.triggered.connect(self.on_paint_tool)
        self.app.ui.geo_buffer_menuitem.triggered.connect(self.on_buffer_tool)
        self.app.ui.geo_transform_menuitem.triggered.connect(self.transform_tool.run)

        self.app.ui.geo_delete_menuitem.triggered.connect(self.on_delete_btn)
        self.app.ui.geo_union_menuitem.triggered.connect(self.union)
        self.app.ui.geo_intersection_menuitem.triggered.connect(self.intersection)
        self.app.ui.geo_subtract_menuitem.triggered.connect(self.subtract)
        self.app.ui.geo_cutpath_menuitem.triggered.connect(self.cutpath)
        self.app.ui.geo_copy_menuitem.triggered.connect(lambda: self.select_tool('copy'))

        self.app.ui.geo_union_btn.triggered.connect(self.union)
        self.app.ui.geo_intersection_btn.triggered.connect(self.intersection)
        self.app.ui.geo_subtract_btn.triggered.connect(self.subtract)
        self.app.ui.geo_cutpath_btn.triggered.connect(self.cutpath)
        self.app.ui.geo_delete_btn.triggered.connect(self.on_delete_btn)

        self.app.ui.geo_move_menuitem.triggered.connect(self.on_move)
        self.app.ui.geo_cornersnap_menuitem.triggered.connect(self.on_corner_snap)

        self.transform_complete.connect(self.on_transform_complete)

        # Event signals disconnect id holders
        self.mp = None
        self.mm = None
        self.mr = None

        log.debug("Initialization of the Geometry Editor is finished ...")

    def make_callback(self, thetool):
        def f():
            self.on_tool_select(thetool)

        return f

    def connect_geo_toolbar_signals(self):
        self.tools.update({
            "select": {"button": self.app.ui.geo_select_btn, "constructor": FCSelect},
            "arc": {"button": self.app.ui.geo_add_arc_btn, "constructor": FCArc},
            "circle": {"button": self.app.ui.geo_add_circle_btn, "constructor": FCCircle},
            "path": {"button": self.app.ui.geo_add_path_btn, "constructor": FCPath},
            "rectangle": {"button": self.app.ui.geo_add_rectangle_btn, "constructor": FCRectangle},
            "polygon": {"button": self.app.ui.geo_add_polygon_btn, "constructor": FCPolygon},
            "text": {"button": self.app.ui.geo_add_text_btn, "constructor": FCText},
            "buffer": {"button": self.app.ui.geo_add_buffer_btn, "constructor": FCBuffer},
            "paint": {"button": self.app.ui.geo_add_paint_btn, "constructor": FCPaint},
            "eraser": {"button": self.app.ui.geo_eraser_btn, "constructor": FCEraser},
            "move": {"button": self.app.ui.geo_move_btn, "constructor": FCMove},
            "transform": {"button": self.app.ui.geo_transform_btn, "constructor": FCTransform},
            "copy": {"button": self.app.ui.geo_copy_btn, "constructor": FCCopy},
            "explode": {"button": self.app.ui.geo_explode_btn, "constructor": FCExplode}
        })

        for tool in self.tools:
            self.tools[tool]["button"].triggered.connect(self.make_callback(tool))  # Events
            self.tools[tool]["button"].setCheckable(True)  # Checkable

    def pool_recreated(self, pool):
        self.shapes.pool = pool
        self.tool_shape.pool = pool

    def on_transform_complete(self):
        self.delete_selected()
        self.replot()

    def entry2option(self, opt, entry):
        """

        :param opt:     A option from the self.options dictionary
        :param entry:   A GUI element which text value is used
        :return:
        """
        try:
            text_value = entry.text()
            if ',' in text_value:
                text_value = text_value.replace(',', '.')
            self.options[opt] = float(text_value)
        except Exception as e:
            entry.set_value(self.app.defaults[opt])
            log.debug("AppGeoEditor.__init__().entry2option() --> %s" % str(e))
            return

    def grid_changed(self, goption, gentry):
        """

        :param goption:     String. Can be either 'global_gridx' or 'global_gridy'
        :param gentry:      A GUI element which text value is read and used
        :return:
        """
        if goption not in ['global_gridx', 'global_gridy']:
            return

        self.entry2option(opt=goption, entry=gentry)
        # if the grid link is checked copy the value in the GridX field to GridY
        try:
            text_value = gentry.text()
            if ',' in text_value:
                text_value = text_value.replace(',', '.')
            val = float(text_value)
        except ValueError:
            return

        if self.app.ui.grid_gap_link_cb.isChecked():
            self.app.ui.grid_gap_y_entry.set_value(val, decimals=self.decimals)

    def on_gridx_val_changed(self):
        self.grid_changed("global_gridx", self.app.ui.grid_gap_x_entry)
        # try:
        #     self.app.defaults["global_gridx"] =  float(self.app.ui.grid_gap_x_entry.get_value())
        # except ValueError:
        #     return

    def on_gridy_val_changed(self):
        self.entry2option("global_gridy", self.app.ui.grid_gap_y_entry)

    def set_ui(self):
        # updated units
        self.units = self.app.defaults['units'].upper()
        self.decimals = self.app.decimals

        # Remove anything else in the GUI Selected Tab
        self.app.ui.properties_scroll_area.takeWidget()
        # Put ourselves in the appGUI Properties Tab
        self.app.ui.properties_scroll_area.setWidget(self.geo_edit_widget)
        # Switch notebook to Properties page
        self.app.ui.notebook.setCurrentWidget(self.app.ui.properties_tab)

    def build_ui(self):
        """
        Build the appGUI in the Properties Tab for this editor

        :return:
        """

        iterator = QtWidgets.QTreeWidgetItemIterator(self.geo_parent)
        to_delete = []
        while iterator.value():
            item = iterator.value()
            to_delete.append(item)
            iterator += 1
        for it in to_delete:
            self.geo_parent.removeChild(it)

        for elem in self.storage.get_objects():
            geo_type = type(elem.geo)
            el_type = None
            if geo_type is LinearRing:
                el_type = _('Ring')
            elif geo_type is LineString:
                el_type = _('Line')
            elif geo_type is Polygon:
                el_type = _('Polygon')
            elif geo_type is MultiLineString:
                el_type = _('Multi-Line')
            elif geo_type is MultiPolygon:
                el_type = _('Multi-Polygon')

            self.tw.addParentEditable(
                self.geo_parent,
                [
                    str(id(elem)),
                    '%s' % el_type,
                    _("Geo Elem")
                ],
                font=self.geo_font,
                font_items=2,
                # color=QtGui.QColor("#FF0000"),
                editable=True
            )

        self.tw.resize_sig.emit()

    def on_geo_elem_selected(self):
        pass

    def on_tree_selection_change(self):
        self.selected = []
        selected_tree_items = self.tw.selectedItems()
        for sel in selected_tree_items:
            for obj_shape in self.storage.get_objects():
                try:
                    if id(obj_shape) == int(sel.text(0)):
                        self.selected.append(obj_shape)
                except ValueError:
                    pass
        self.replot()

    def activate(self):
        # adjust the status of the menu entries related to the editor
        self.app.ui.menueditedit.setDisabled(True)
        self.app.ui.menueditok.setDisabled(False)

        # adjust the visibility of some of the canvas context menu
        self.app.ui.popmenu_edit.setVisible(False)
        self.app.ui.popmenu_save.setVisible(True)

        self.connect_canvas_event_handlers()

        # initialize working objects
        self.storage = AppGeoEditor.make_storage()
        self.utility = []
        self.selected = []

        self.shapes.enabled = True
        self.tool_shape.enabled = True
        self.app.app_cursor.enabled = True

        self.app.ui.corner_snap_btn.setVisible(True)
        self.app.ui.snap_magnet.setVisible(True)

        self.app.ui.geo_editor_menu.setDisabled(False)
        self.app.ui.geo_editor_menu.menuAction().setVisible(True)

        self.app.ui.update_obj_btn.setEnabled(True)
        self.app.ui.g_editor_cmenu.setEnabled(True)

        self.app.ui.geo_edit_toolbar.setDisabled(False)
        self.app.ui.geo_edit_toolbar.setVisible(True)

        self.app.ui.status_toolbar.setDisabled(False)

        self.app.ui.popmenu_disable.setVisible(False)
        self.app.ui.cmenu_newmenu.menuAction().setVisible(False)
        self.app.ui.popmenu_properties.setVisible(False)
        self.app.ui.g_editor_cmenu.menuAction().setVisible(True)

        # prevent the user to change anything in the Properties Tab while the Geo Editor is active
        # sel_tab_widget_list = self.app.ui.properties_tab.findChildren(QtWidgets.QWidget)
        # for w in sel_tab_widget_list:
        #     w.setEnabled(False)

        self.item_selected.connect(self.on_geo_elem_selected)

        # ## appGUI Events
        self.tw.itemSelectionChanged.connect(self.on_tree_selection_change)
        # self.tw.keyPressed.connect(self.app.ui.keyPressEvent)
        # self.tw.customContextMenuRequested.connect(self.on_menu_request)

        self.geo_frame.show()

        log.debug("Finished activating the Geometry Editor...")

    def deactivate(self):
        try:
            QtGui.QGuiApplication.restoreOverrideCursor()
        except Exception:
            pass

        # adjust the status of the menu entries related to the editor
        self.app.ui.menueditedit.setDisabled(False)
        self.app.ui.menueditok.setDisabled(True)

        # adjust the visibility of some of the canvas context menu
        self.app.ui.popmenu_edit.setVisible(True)
        self.app.ui.popmenu_save.setVisible(False)

        self.disconnect_canvas_event_handlers()
        self.clear()
        self.app.ui.geo_edit_toolbar.setDisabled(True)

        self.app.ui.corner_snap_btn.setVisible(False)
        self.app.ui.snap_magnet.setVisible(False)

        # set the Editor Toolbar visibility to what was before entering in the Editor
        self.app.ui.geo_edit_toolbar.setVisible(False) if self.toolbar_old_state is False \
            else self.app.ui.geo_edit_toolbar.setVisible(True)

        # Disable visuals
        self.shapes.enabled = False
        self.tool_shape.enabled = False

        self.app.ui.geo_editor_menu.setDisabled(True)
        self.app.ui.geo_editor_menu.menuAction().setVisible(False)

        self.app.ui.update_obj_btn.setEnabled(False)

        self.app.ui.g_editor_cmenu.setEnabled(False)
        self.app.ui.e_editor_cmenu.setEnabled(False)

        self.app.ui.popmenu_disable.setVisible(True)
        self.app.ui.cmenu_newmenu.menuAction().setVisible(True)
        self.app.ui.popmenu_properties.setVisible(True)
        self.app.ui.grb_editor_cmenu.menuAction().setVisible(False)
        self.app.ui.e_editor_cmenu.menuAction().setVisible(False)
        self.app.ui.g_editor_cmenu.menuAction().setVisible(False)

        try:
            self.item_selected.disconnect()
        except (AttributeError, TypeError):
            pass

        try:
            # ## appGUI Events
            self.tw.itemSelectionChanged.disconnect(self.on_tree_selection_change)
            # self.tw.keyPressed.connect(self.app.ui.keyPressEvent)
            # self.tw.customContextMenuRequested.connect(self.on_menu_request)
        except (AttributeError, TypeError):
            pass

        # try:
        #     # re-enable all the widgets in the Selected Tab that were disabled after entering in Edit Geometry Mode
        #     sel_tab_widget_list = self.app.ui.properties_tab.findChildren(QtWidgets.QWidget)
        #     for w in sel_tab_widget_list:
        #         w.setEnabled(True)
        # except Exception as e:
        #     log.debug("AppGeoEditor.deactivate() --> %s" % str(e))

        # Show original geometry
        if self.fcgeometry:
            self.fcgeometry.visible = True

        # clear the Tree
        self.tw.clear()
        self.geo_parent = self.tw.invisibleRootItem()

        # hide the UI
        self.geo_frame.hide()

        log.debug("Finished deactivating the Geometry Editor...")

    def connect_canvas_event_handlers(self):
        # Canvas events

        # first connect to new, then disconnect the old handlers
        # don't ask why but if there is nothing connected I've seen issues
        self.mp = self.canvas.graph_event_connect('mouse_press', self.on_canvas_click)
        self.mm = self.canvas.graph_event_connect('mouse_move', self.on_canvas_move)
        self.mr = self.canvas.graph_event_connect('mouse_release', self.on_geo_click_release)

        if self.app.is_legacy is False:
            # make sure that the shortcuts key and mouse events will no longer be linked to the methods from FlatCAMApp
            # but those from AppGeoEditor
            self.app.plotcanvas.graph_event_disconnect('mouse_press', self.app.on_mouse_click_over_plot)
            self.app.plotcanvas.graph_event_disconnect('mouse_move', self.app.on_mouse_move_over_plot)
            self.app.plotcanvas.graph_event_disconnect('mouse_release', self.app.on_mouse_click_release_over_plot)
            self.app.plotcanvas.graph_event_disconnect('mouse_double_click', self.app.on_mouse_double_click_over_plot)
        else:

            self.app.plotcanvas.graph_event_disconnect(self.app.mp)
            self.app.plotcanvas.graph_event_disconnect(self.app.mm)
            self.app.plotcanvas.graph_event_disconnect(self.app.mr)
            self.app.plotcanvas.graph_event_disconnect(self.app.mdc)

        # self.app.collection.view.clicked.disconnect()
        self.app.ui.popmenu_copy.triggered.disconnect()
        self.app.ui.popmenu_delete.triggered.disconnect()
        self.app.ui.popmenu_move.triggered.disconnect()

        self.app.ui.popmenu_copy.triggered.connect(lambda: self.select_tool('copy'))
        self.app.ui.popmenu_delete.triggered.connect(self.on_delete_btn)
        self.app.ui.popmenu_move.triggered.connect(lambda: self.select_tool('move'))

        # Geometry Editor
        self.app.ui.draw_line.triggered.connect(self.draw_tool_path)
        self.app.ui.draw_rect.triggered.connect(self.draw_tool_rectangle)

        self.app.ui.draw_circle.triggered.connect(lambda: self.select_tool('circle'))
        self.app.ui.draw_poly.triggered.connect(lambda: self.select_tool('polygon'))
        self.app.ui.draw_arc.triggered.connect(lambda: self.select_tool('arc'))

        self.app.ui.draw_text.triggered.connect(lambda: self.select_tool('text'))
        self.app.ui.draw_buffer.triggered.connect(lambda: self.select_tool('buffer'))
        self.app.ui.draw_paint.triggered.connect(lambda: self.select_tool('paint'))
        self.app.ui.draw_eraser.triggered.connect(lambda: self.select_tool('eraser'))

        self.app.ui.draw_union.triggered.connect(self.union)
        self.app.ui.draw_intersect.triggered.connect(self.intersection)
        self.app.ui.draw_substract.triggered.connect(self.subtract)
        self.app.ui.draw_cut.triggered.connect(self.cutpath)
        self.app.ui.draw_transform.triggered.connect(lambda: self.select_tool('transform'))

        self.app.ui.draw_move.triggered.connect(self.on_move)

    def disconnect_canvas_event_handlers(self):
        # we restore the key and mouse control to FlatCAMApp method
        # first connect to new, then disconnect the old handlers
        # don't ask why but if there is nothing connected I've seen issues
        self.app.mp = self.app.plotcanvas.graph_event_connect('mouse_press', self.app.on_mouse_click_over_plot)
        self.app.mm = self.app.plotcanvas.graph_event_connect('mouse_move', self.app.on_mouse_move_over_plot)
        self.app.mr = self.app.plotcanvas.graph_event_connect('mouse_release',
                                                              self.app.on_mouse_click_release_over_plot)
        self.app.mdc = self.app.plotcanvas.graph_event_connect('mouse_double_click',
                                                               self.app.on_mouse_double_click_over_plot)
        # self.app.collection.view.clicked.connect(self.app.collection.on_mouse_down)

        if self.app.is_legacy is False:
            self.canvas.graph_event_disconnect('mouse_press', self.on_canvas_click)
            self.canvas.graph_event_disconnect('mouse_move', self.on_canvas_move)
            self.canvas.graph_event_disconnect('mouse_release', self.on_geo_click_release)
        else:
            self.canvas.graph_event_disconnect(self.mp)
            self.canvas.graph_event_disconnect(self.mm)
            self.canvas.graph_event_disconnect(self.mr)

        try:
            self.app.ui.popmenu_copy.triggered.disconnect(lambda: self.select_tool('copy'))
        except (TypeError, AttributeError):
            pass
        try:
            self.app.ui.popmenu_delete.triggered.disconnect(self.on_delete_btn)
        except (TypeError, AttributeError):
            pass
        try:
            self.app.ui.popmenu_move.triggered.disconnect(lambda: self.select_tool('move'))
        except (TypeError, AttributeError):
            pass

        self.app.ui.popmenu_copy.triggered.connect(self.app.on_copy_command)
        self.app.ui.popmenu_delete.triggered.connect(self.app.on_delete)
        self.app.ui.popmenu_move.triggered.connect(self.app.obj_move)

        # Geometry Editor
        try:
            self.app.ui.draw_line.triggered.disconnect(self.draw_tool_path)
        except (TypeError, AttributeError):
            pass

        try:
            self.app.ui.draw_rect.triggered.disconnect(self.draw_tool_rectangle)
        except (TypeError, AttributeError):
            pass

        try:
            self.app.ui.draw_cut.triggered.disconnect(self.cutpath)
        except (TypeError, AttributeError):
            pass

        try:
            self.app.ui.draw_move.triggered.disconnect(self.on_move)
        except (TypeError, AttributeError):
            pass

        try:
            self.app.ui.draw_circle.triggered.disconnect()
        except (TypeError, AttributeError):
            pass

        try:
            self.app.ui.draw_poly.triggered.disconnect()
        except (TypeError, AttributeError):
            pass

        try:
            self.app.ui.draw_arc.triggered.disconnect()
        except (TypeError, AttributeError):
            pass

        try:
            self.app.ui.draw_text.triggered.disconnect()
        except (TypeError, AttributeError):
            pass

        try:
            self.app.ui.draw_buffer.triggered.disconnect()
        except (TypeError, AttributeError):
            pass

        try:
            self.app.ui.draw_paint.triggered.disconnect()
        except (TypeError, AttributeError):
            pass

        try:
            self.app.ui.draw_eraser.triggered.disconnect()
        except (TypeError, AttributeError):
            pass

        try:
            self.app.ui.draw_union.triggered.disconnect(self.union)
        except (TypeError, AttributeError):
            pass

        try:
            self.app.ui.draw_intersect.triggered.disconnect(self.intersection)
        except (TypeError, AttributeError):
            pass

        try:
            self.app.ui.draw_substract.triggered.disconnect(self.subtract)
        except (TypeError, AttributeError):
            pass

        try:
            self.app.ui.draw_transform.triggered.disconnect()
        except (TypeError, AttributeError):
            pass

        try:
            self.app.jump_signal.disconnect()
        except (TypeError, AttributeError):
            pass

    def add_shape(self, shape):
        """
        Adds a shape to the shape storage.

        :param shape:   Shape to be added.
        :type shape:    DrawToolShape
        :return:        None
        """

        if shape is None:
            return

        # List of DrawToolShape?
        if isinstance(shape, list):
            for subshape in shape:
                self.add_shape(subshape)
            return

        assert isinstance(shape, DrawToolShape), "Expected a DrawToolShape, got %s" % type(shape)
        assert shape.geo is not None, "Shape object has empty geometry (None)"
        assert (isinstance(shape.geo, list) and len(shape.geo) > 0) or not isinstance(shape.geo, list), \
            "Shape objects has empty geometry ([])"

        if isinstance(shape, DrawToolUtilityShape):
            self.utility.append(shape)
        else:
            self.storage.insert(shape)  # TODO: Check performance
            self.build_ui()

    def delete_utility_geometry(self):
        """
        Will delete the shapes in the utility shapes storage.

        :return:    None
        """

        # for_deletion = [shape for shape in self.shape_buffer if shape.utility]
        # for_deletion = [shape for shape in self.storage.get_objects() if shape.utility]
        for_deletion = [shape for shape in self.utility]
        for shape in for_deletion:
            self.delete_shape(shape)

        self.tool_shape.clear(update=True)
        self.tool_shape.redraw()

    def toolbar_tool_toggle(self, key):
        """
        It is used as a slot by the Snap buttons.

        :param key:     Key in the self.options dictionary that is to be updated
        :return:        Boolean. Status of the checkbox that toggled the Editor Tool
        """
        cb_widget = self.sender()
        assert isinstance(cb_widget, QtWidgets.QAction), "Expected a QAction got %s" % type(cb_widget)
        self.options[key] = cb_widget.isChecked()

        return 1 if self.options[key] is True else 0

    def clear(self):
        """
        Will clear the storage for the Editor shapes, the selected shapes storage and replot. Clean up method.

        :return:    None
        """
        self.active_tool = None
        # self.shape_buffer = []
        self.selected = []
        self.shapes.clear(update=True)
        self.tool_shape.clear(update=True)

        # self.storage = AppGeoEditor.make_storage()
        self.replot()

    def on_buffer_tool(self):
        buff_tool = BufferSelectionTool(self.app, self)
        buff_tool.run()

    def on_paint_tool(self):
        paint_tool = PaintOptionsTool(self.app, self)
        paint_tool.run()

    def on_tool_select(self, tool):
        """
        Behavior of the toolbar. Tool initialization.

        :rtype : None
        """
        self.app.log.debug("on_tool_select('%s')" % tool)

        # This is to make the group behave as radio group
        if tool in self.tools:
            if self.tools[tool]["button"].isChecked():
                self.app.log.debug("%s is checked." % tool)
                for t in self.tools:
                    if t != tool:
                        self.tools[t]["button"].setChecked(False)

                self.active_tool = self.tools[tool]["constructor"](self)
            else:
                self.app.log.debug("%s is NOT checked." % tool)
                for t in self.tools:
                    self.tools[t]["button"].setChecked(False)

                self.select_tool('select')
                self.active_tool = FCSelect(self)

    def draw_tool_path(self):
        self.select_tool('path')
        return

    def draw_tool_rectangle(self):
        self.select_tool('rectangle')
        return

    def on_grid_toggled(self):
        self.toolbar_tool_toggle("grid_snap")

        # make sure that the cursor shape is enabled/disabled, too
        if self.options['grid_snap'] is True:
            self.app.defaults['global_grid_snap'] = True
            self.app.inform[str, bool].emit(_("Grid Snap enabled."), False)
            self.app.app_cursor.enabled = True
        else:
            self.app.defaults['global_grid_snap'] = False
            self.app.app_cursor.enabled = False
            self.app.inform[str, bool].emit(_("Grid Snap disabled."), False)

    def on_canvas_click(self, event):
        """
        event.x and .y have canvas coordinates
        event.xdaya and .ydata have plot coordinates

        :param event: Event object dispatched by Matplotlib
        :return: None
        """
        if self.app.is_legacy is False:
            event_pos = event.pos
        else:
            event_pos = (event.xdata, event.ydata)

        self.pos = self.canvas.translate_coords(event_pos)

        if self.app.grid_status():
            self.pos = self.app.geo_editor.snap(self.pos[0], self.pos[1])
        else:
            self.pos = (self.pos[0], self.pos[1])

        if event.button == 1:
            self.app.ui.rel_position_label.setText("<b>Dx</b>: %.4f&nbsp;&nbsp;  <b>Dy</b>: "
                                                   "%.4f&nbsp;&nbsp;&nbsp;&nbsp;" % (0, 0))

            modifiers = QtWidgets.QApplication.keyboardModifiers()
            # If the SHIFT key is pressed when LMB is clicked then the coordinates are copied to clipboard
            if modifiers == QtCore.Qt.ShiftModifier:
                self.app.clipboard.setText(
                    self.app.defaults["global_point_clipboard_format"] %
                    (self.decimals, self.pos[0], self.decimals, self.pos[1])
                )
                return

            # Selection with left mouse button
            if self.active_tool is not None and event.button == 1:

                # Dispatch event to active_tool
                self.active_tool.click(self.snap(self.pos[0], self.pos[1]))

                # If it is a shape generating tool
                if isinstance(self.active_tool, FCShapeTool) and self.active_tool.complete:
                    self.on_shape_complete()

                    if isinstance(self.active_tool, FCText):
                        self.select_tool("select")
                    else:
                        self.select_tool(self.active_tool.name)

                if isinstance(self.active_tool, FCSelect):
                    # self.app.log.debug("Replotting after click.")
                    self.replot()
            else:
                self.app.log.debug("No active tool to respond to click!")

    def on_canvas_move(self, event):
        """
        Called on 'mouse_move' event
        event.pos have canvas screen coordinates

        :param event: Event object dispatched by VisPy SceneCavas
        :return: None
        """
        if self.app.is_legacy is False:
            event_pos = event.pos
            event_is_dragging = event.is_dragging
            right_button = 2
        else:
            event_pos = (event.xdata, event.ydata)
            event_is_dragging = self.app.plotcanvas.is_dragging
            right_button = 3

        pos = self.canvas.translate_coords(event_pos)
        event.xdata, event.ydata = pos[0], pos[1]

        self.x = event.xdata
        self.y = event.ydata

        self.app.ui.popMenu.mouse_is_panning = False

        # if the RMB is clicked and mouse is moving over plot then 'panning_action' is True
        if event.button == right_button:
            if event_is_dragging:
                self.app.ui.popMenu.mouse_is_panning = True
                # return
            else:
                self.app.ui.popMenu.mouse_is_panning = False

        if self.active_tool is None:
            return

        try:
            x = float(event.xdata)
            y = float(event.ydata)
        except TypeError:
            return

        # ### Snap coordinates ###
        if self.app.grid_status():
            x, y = self.snap(x, y)

            # Update cursor
            self.app.app_cursor.set_data(np.asarray([(x, y)]), symbol='++', edge_color=self.app.cursor_color_3D,
                                         edge_width=self.app.defaults["global_cursor_width"],
                                         size=self.app.defaults["global_cursor_size"])

        self.snap_x = x
        self.snap_y = y
        self.app.mouse = [x, y]

        if self.pos is None:
            self.pos = (0, 0)
        self.app.dx = x - self.pos[0]
        self.app.dy = y - self.pos[1]

        # # update the position label in the infobar since the APP mouse event handlers are disconnected
        self.app.ui.position_label.setText("&nbsp;<b>X</b>: %.4f&nbsp;&nbsp;   "
                                           "<b>Y</b>: %.4f&nbsp;" % (x, y))
        #
        # # update the reference position label in the infobar since the APP mouse event handlers are disconnected
        self.app.ui.rel_position_label.setText("<b>Dx</b>: %.4f&nbsp;&nbsp;  <b>Dy</b>: "
                                               "%.4f&nbsp;&nbsp;&nbsp;&nbsp;" % (self.app.dx, self.app.dy))

        units = self.app.defaults["units"].lower()
        self.app.plotcanvas.text_hud.text = \
            'Dx:\t{:<.4f} [{:s}]\nDy:\t{:<.4f} [{:s}]\n\nX:  \t{:<.4f} [{:s}]\nY:  \t{:<.4f} [{:s}]'.format(
                self.app.dx, units, self.app.dy, units, x, units, y, units)

        if event.button == 1 and event_is_dragging and isinstance(self.active_tool, FCEraser):
            pass
        else:
            self.update_utility_geometry(data=(x, y))

        # ### Selection area on canvas section ###
        dx = pos[0] - self.pos[0]
        if event_is_dragging and event.button == 1:
            self.app.delete_selection_shape()
            if dx < 0:
                self.app.draw_moving_selection_shape((self.pos[0], self.pos[1]), (x, y),
                                                     color=self.app.defaults["global_alt_sel_line"],
                                                     face_color=self.app.defaults['global_alt_sel_fill'])
                self.app.selection_type = False
            else:
                self.app.draw_moving_selection_shape((self.pos[0], self.pos[1]), (x, y))
                self.app.selection_type = True
        else:
            self.app.selection_type = None

    def update_utility_geometry(self, data):
        # ### Utility geometry (animated) ###
        geo = self.active_tool.utility_geometry(data=data)
        if isinstance(geo, DrawToolShape) and geo.geo is not None:
            # Remove any previous utility shape
            self.tool_shape.clear(update=True)
            self.draw_utility_geometry(geo=geo)

    def on_geo_click_release(self, event):
        if self.app.is_legacy is False:
            event_pos = event.pos
            # event_is_dragging = event.is_dragging
            right_button = 2
        else:
            event_pos = (event.xdata, event.ydata)
            # event_is_dragging = self.app.plotcanvas.is_dragging
            right_button = 3

        pos_canvas = self.canvas.translate_coords(event_pos)

        if self.app.grid_status():
            pos = self.snap(pos_canvas[0], pos_canvas[1])
        else:
            pos = (pos_canvas[0], pos_canvas[1])

        # if the released mouse button was RMB then test if it was a panning motion or not, if not it was a context
        # canvas menu
        try:
            # if the released mouse button was LMB then test if we had a right-to-left selection or a left-to-right
            # selection and then select a type of selection ("enclosing" or "touching")
            if event.button == 1:  # left click
                if self.app.selection_type is not None:
                    self.draw_selection_area_handler(self.pos, pos, self.app.selection_type)
                    self.app.selection_type = None
                elif isinstance(self.active_tool, FCSelect):
                    # Dispatch event to active_tool
                    # msg = self.active_tool.click(self.snap(event.xdata, event.ydata))
                    self.active_tool.click_release((self.pos[0], self.pos[1]))
                    # self.app.inform.emit(msg)
                    self.replot()
            elif event.button == right_button:  # right click
                if self.app.ui.popMenu.mouse_is_panning is False:
                    if self.in_action is False:
                        try:
                            QtGui.QGuiApplication.restoreOverrideCursor()
                        except Exception:
                            pass

                        if self.active_tool.complete is False and not isinstance(self.active_tool, FCSelect):
                            self.active_tool.complete = True
                            self.in_action = False
                            self.delete_utility_geometry()
                            self.app.inform.emit('[success] %s' % _("Done."))
                            self.select_tool('select')
                        else:
                            self.app.cursor = QtGui.QCursor()
                            self.app.populate_cmenu_grids()
                            self.app.ui.popMenu.popup(self.app.cursor.pos())
                    else:
                        # if right click on canvas and the active tool need to be finished (like Path or Polygon)
                        # right mouse click will finish the action
                        if isinstance(self.active_tool, FCShapeTool):
                            self.active_tool.click(self.snap(self.x, self.y))
                            self.active_tool.make()
                            if self.active_tool.complete:
                                self.on_shape_complete()
                                self.app.inform.emit('[success] %s' % _("Done."))
                                self.select_tool(self.active_tool.name)
        except Exception as e:
            log.warning("FLatCAMGeoEditor.on_geo_click_release() --> Error: %s" % str(e))
            return

    def draw_selection_area_handler(self, start_pos, end_pos, sel_type):
        """

        :param start_pos: mouse position when the selection LMB click was done
        :param end_pos: mouse position when the left mouse button is released
        :param sel_type: if True it's a left to right selection (enclosure), if False it's a 'touch' selection
        :return:
        """
        poly_selection = Polygon([start_pos, (end_pos[0], start_pos[1]), end_pos, (start_pos[0], end_pos[1])])

        key_modifier = QtWidgets.QApplication.keyboardModifiers()

        if key_modifier == QtCore.Qt.ShiftModifier:
            mod_key = 'Shift'
        elif key_modifier == QtCore.Qt.ControlModifier:
            mod_key = 'Control'
        else:
            mod_key = None

        self.app.delete_selection_shape()

        sel_objects_list = []
        for obj in self.storage.get_objects():
            if (sel_type is True and poly_selection.contains(obj.geo)) or (sel_type is False and
                                                                           poly_selection.intersects(obj.geo)):
                sel_objects_list.append(obj)

        if mod_key == self.app.defaults["global_mselect_key"]:
            for obj in sel_objects_list:
                if obj in self.selected:
                    self.selected.remove(obj)
                else:
                    # add the object to the selected shapes
                    self.selected.append(obj)
        else:
            self.selected = []
            self.selected = sel_objects_list

        # if selection is done on canvas update the Tree in Selected Tab with the selection
        try:
            self.tw.itemSelectionChanged.disconnect(self.on_tree_selection_change)
        except (AttributeError, TypeError):
            pass

        self.tw.selectionModel().clearSelection()
        for sel_shape in self.selected:
            iterator = QtWidgets.QTreeWidgetItemIterator(self.tw)
            while iterator.value():
                item = iterator.value()
                try:
                    if int(item.text(1)) == id(sel_shape):
                        item.setSelected(True)
                except ValueError:
                    pass

                iterator += 1

        self.tw.itemSelectionChanged.connect(self.on_tree_selection_change)

        self.replot()

    def draw_utility_geometry(self, geo):
        # Add the new utility shape
        try:
            # this case is for the Font Parse
            for el in list(geo.geo):
                if type(el) == MultiPolygon:
                    for poly in el:
                        self.tool_shape.add(
                            shape=poly,
                            color=(self.app.defaults["global_draw_color"] + '80'),
                            update=False,
                            layer=0,
                            tolerance=None
                        )
                elif type(el) == MultiLineString:
                    for linestring in el:
                        self.tool_shape.add(
                            shape=linestring,
                            color=(self.app.defaults["global_draw_color"] + '80'),
                            update=False,
                            layer=0,
                            tolerance=None
                        )
                else:
                    self.tool_shape.add(
                        shape=el,
                        color=(self.app.defaults["global_draw_color"] + '80'),
                        update=False,
                        layer=0,
                        tolerance=None
                    )
        except TypeError:
            self.tool_shape.add(
                shape=geo.geo, color=(self.app.defaults["global_draw_color"] + '80'),
                update=False, layer=0, tolerance=None)

        self.tool_shape.redraw()

    def on_delete_btn(self):
        self.delete_selected()
        self.replot()

    def delete_selected(self):
        tempref = [s for s in self.selected]
        for shape in tempref:
            self.delete_shape(shape)
        self.selected = []
        self.build_ui()

    def delete_shape(self, shape):

        if shape in self.utility:
            self.utility.remove(shape)
            return

        self.storage.remove(shape)
        if shape in self.selected:
            self.selected.remove(shape)  # TODO: Check performance

    def on_move(self):
        # if not self.selected:
        #     self.app.inform.emit(_("[WARNING_NOTCL] Move cancelled. No shape selected."))
        #     return
        self.app.ui.geo_move_btn.setChecked(True)
        self.on_tool_select('move')

    def on_move_click(self):
        try:
            x, y = self.snap(self.x, self.y)
        except TypeError:
            return
        self.on_move()
        self.active_tool.set_origin((x, y))

    def on_copy_click(self):
        if not self.selected:
            self.app.inform.emit('[WARNING_NOTCL] %s %s' % (_("Cancelled."), _("No shape selected.")))
            return

        self.app.ui.geo_copy_btn.setChecked(True)
        self.app.geo_editor.on_tool_select('copy')
        self.app.geo_editor.active_tool.set_origin(self.app.geo_editor.snap(
            self.app.geo_editor.x, self.app.geo_editor.y))
        self.app.inform.emit(_("Click on target point."))

    def on_corner_snap(self):
        self.app.ui.corner_snap_btn.trigger()

    def get_selected(self):
        """
        Returns list of shapes that are selected in the editor.

        :return: List of shapes.
        """
        # return [shape for shape in self.shape_buffer if shape["selected"]]
        return self.selected

    def plot_shape(self, geometry=None, color='#000000FF', linewidth=1):
        """
        Plots a geometric object or list of objects without rendering. Plotted objects
        are returned as a list. This allows for efficient/animated rendering.

        :param geometry: Geometry to be plotted (Any Shapely.geom kind or list of such)
        :param color: Shape color
        :param linewidth: Width of lines in # of pixels.
        :return: List of plotted elements.
        """
        plot_elements = []

        if geometry is None:
            geometry = self.active_tool.geometry

        try:
            for geo in geometry:
                plot_elements += self.plot_shape(geometry=geo, color=color, linewidth=linewidth)
        # Non-iterable
        except TypeError:

            # DrawToolShape
            if isinstance(geometry, DrawToolShape):
                plot_elements += self.plot_shape(geometry=geometry.geo, color=color, linewidth=linewidth)

            # Polygon: Descend into exterior and each interior.
            if type(geometry) == Polygon:
                plot_elements += self.plot_shape(geometry=geometry.exterior, color=color, linewidth=linewidth)
                plot_elements += self.plot_shape(geometry=geometry.interiors, color=color, linewidth=linewidth)

            if type(geometry) == LineString or type(geometry) == LinearRing:
                plot_elements.append(self.shapes.add(shape=geometry, color=color, layer=0,
                                                     tolerance=self.fcgeometry.drawing_tolerance,
                                                     linewidth=linewidth))

            if type(geometry) == Point:
                pass

        return plot_elements

    def plot_all(self):
        """
        Plots all shapes in the editor.

        :return: None
        :rtype: None
        """
        # self.app.log.debug("plot_all()")
        self.shapes.clear(update=True)

        for shape in self.storage.get_objects():

            if shape.geo is None:  # TODO: This shouldn't have happened
                continue

            if shape in self.selected:
                self.plot_shape(geometry=shape.geo,
                                color=self.app.defaults['global_sel_draw_color'] + 'FF',
                                linewidth=2)
                continue

            self.plot_shape(geometry=shape.geo,
                            color=self.app.defaults['global_draw_color'] + "FF")

        for shape in self.utility:
            self.plot_shape(geometry=shape.geo,
                            linewidth=1)
            continue

        self.shapes.redraw()

    def replot(self):
        self.plot_all()

    def on_shape_complete(self):
        self.app.log.debug("on_shape_complete()")

        geom = []
        try:
            for shape in self.active_tool.geometry:
                geom.append(shape.geo)
        except TypeError:
            geom = self.active_tool.geometry.geo

        if self.app.defaults['geometry_editor_milling_type'] == 'cl':
            # reverse the geometry coordinates direction to allow creation of Gcode for  climb milling
            try:
                pl = []
                for p in geom:
                    if p is not None:
                        if isinstance(p, Polygon):
                            pl.append(Polygon(p.exterior.coords[::-1], p.interiors))
                        elif isinstance(p, LinearRing):
                            pl.append(Polygon(p.coords[::-1]))
                        elif isinstance(p, LineString):
                            pl.append(LineString(p.coords[::-1]))
                try:
                    geom = MultiPolygon(pl)
                except TypeError:
                    # this may happen if the geom elements are made out of LineStrings because you can't create a
                    # MultiPolygon out of LineStrings
                    pass
            except TypeError:
                if isinstance(geom, Polygon) and geom is not None:
                    geom = Polygon(geom.exterior.coords[::-1], geom.interiors)
                elif isinstance(geom, LinearRing) and geom is not None:
                    geom = Polygon(geom.coords[::-1])
                elif isinstance(geom, LineString) and geom is not None:
                    geom = LineString(geom.coords[::-1])
                else:
                    log.debug("AppGeoEditor.on_shape_complete() Error --> Unexpected Geometry %s" %
                              type(geom))
            except Exception as e:
                log.debug("AppGeoEditor.on_shape_complete() Error --> %s" % str(e))
                return 'fail'

        shape_list = []
        try:
            for geo in geom:
                shape_list.append(DrawToolShape(geo))
        except TypeError:
            shape_list.append(DrawToolShape(geom))

        # Add shape
        self.add_shape(shape_list)

        # Remove any utility shapes
        self.delete_utility_geometry()
        self.tool_shape.clear(update=True)

        # Replot and reset tool.
        self.replot()
        # self.active_tool = type(self.active_tool)(self)

    @staticmethod
    def make_storage():

        # Shape storage.
        storage = FlatCAMRTreeStorage()
        storage.get_points = DrawToolShape.get_pts

        return storage

    def select_tool(self, toolname):
        """
        Selects a drawing tool. Impacts the object and appGUI.

        :param toolname: Name of the tool.
        :return: None
        """
        self.tools[toolname]["button"].setChecked(True)
        self.on_tool_select(toolname)

    def set_selected(self, shape):

        # Remove and add to the end.
        if shape in self.selected:
            self.selected.remove(shape)

        self.selected.append(shape)

    def set_unselected(self, shape):
        if shape in self.selected:
            self.selected.remove(shape)

    def snap(self, x, y):
        """
        Adjusts coordinates to snap settings.

        :param x: Input coordinate X
        :param y: Input coordinate Y
        :return: Snapped (x, y)
        """

        snap_x, snap_y = (x, y)
        snap_distance = np.Inf

        # # ## Object (corner?) snap
        # # ## No need for the objects, just the coordinates
        # # ## in the index.
        if self.options["corner_snap"]:
            try:
                nearest_pt, shape = self.storage.nearest((x, y))

                nearest_pt_distance = distance((x, y), nearest_pt)
                if nearest_pt_distance <= float(self.options["global_snap_max"]):
                    snap_distance = nearest_pt_distance
                    snap_x, snap_y = nearest_pt
            except (StopIteration, AssertionError):
                pass

        # # ## Grid snap
        if self.options["grid_snap"]:
            if self.options["global_gridx"] != 0:
                try:
                    snap_x_ = round(x / float(self.options["global_gridx"])) * float(self.options['global_gridx'])
                except TypeError:
                    snap_x_ = x
            else:
                snap_x_ = x

            # If the Grid_gap_linked on Grid Toolbar is checked then the snap distance on GridY entry will be ignored
            # and it will use the snap distance from GridX entry
            if self.app.ui.grid_gap_link_cb.isChecked():
                if self.options["global_gridx"] != 0:
                    try:
                        snap_y_ = round(y / float(self.options["global_gridx"])) * float(self.options['global_gridx'])
                    except TypeError:
                        snap_y_ = y
                else:
                    snap_y_ = y
            else:
                if self.options["global_gridy"] != 0:
                    try:
                        snap_y_ = round(y / float(self.options["global_gridy"])) * float(self.options['global_gridy'])
                    except TypeError:
                        snap_y_ = y
                else:
                    snap_y_ = y
            nearest_grid_distance = distance((x, y), (snap_x_, snap_y_))
            if nearest_grid_distance < snap_distance:
                snap_x, snap_y = (snap_x_, snap_y_)

        return snap_x, snap_y

    def edit_fcgeometry(self, fcgeometry, multigeo_tool=None):
        """
        Imports the geometry from the given FlatCAM Geometry object
        into the editor.

        :param fcgeometry:      GeometryObject
        :param multigeo_tool:   A tool for the case of the edited geometry being of type 'multigeo'
        :return:                None
        """
        assert isinstance(fcgeometry, Geometry), "Expected a Geometry, got %s" % type(fcgeometry)

        self.deactivate()
        self.activate()

        self.set_ui()

        # Hide original geometry
        self.fcgeometry = fcgeometry
        fcgeometry.visible = False

        # Set selection tolerance
        DrawToolShape.tolerance = fcgeometry.drawing_tolerance * 10

        self.select_tool("select")

        if self.app.defaults['geometry_spindledir'] == 'CW':
            if self.app.defaults['geometry_editor_milling_type'] == 'cl':
                milling_type = 1    # CCW motion = climb milling (spindle is rotating CW)
            else:
                milling_type = -1   # CW motion = conventional milling (spindle is rotating CW)
        else:
            if self.app.defaults['geometry_editor_milling_type'] == 'cl':
                milling_type = -1    # CCW motion = climb milling (spindle is rotating CCW)
            else:
                milling_type = 1   # CW motion = conventional milling (spindle is rotating CCW)

        # Link shapes into editor.
        if multigeo_tool:
            self.multigeo_tool = multigeo_tool
            geo_to_edit = self.flatten(geometry=fcgeometry.tools[self.multigeo_tool]['solid_geometry'],
                                       orient_val=milling_type)
            self.app.inform.emit(
                '[WARNING_NOTCL] %s: %s %s: %s' % (
                    _("Editing MultiGeo Geometry, tool"),
                    str(self.multigeo_tool),
                    _("with diameter"),
                    str(fcgeometry.tools[self.multigeo_tool]['tooldia'])
                )
            )
        else:
            geo_to_edit = self.flatten(geometry=fcgeometry.solid_geometry, orient_val=milling_type)

        for shape in geo_to_edit:
            if shape is not None:
                if type(shape) == Polygon:
                    self.add_shape(DrawToolShape(shape.exterior))
                    for inter in shape.interiors:
                        self.add_shape(DrawToolShape(inter))
                else:
                    self.add_shape(DrawToolShape(shape))

        self.replot()

        # updated units
        self.units = self.app.defaults['units'].upper()
        self.decimals = self.app.decimals

        # start with GRID toolbar activated
        if self.app.ui.grid_snap_btn.isChecked() is False:
            self.app.ui.grid_snap_btn.trigger()

    def update_fcgeometry(self, fcgeometry):
        """
        Transfers the geometry tool shape buffer to the selected geometry
        object. The geometry already in the object are removed.

        :param fcgeometry:  GeometryObject
        :return:            None
        """
        if self.multigeo_tool:
            fcgeometry.tools[self.multigeo_tool]['solid_geometry'] = []
            # for shape in self.shape_buffer:
            for shape in self.storage.get_objects():
                new_geo = shape.geo

                # simplify the MultiLineString
                if isinstance(new_geo, MultiLineString):
                    new_geo = linemerge(new_geo)

                fcgeometry.tools[self.multigeo_tool]['solid_geometry'].append(new_geo)
            self.multigeo_tool = None

        fcgeometry.solid_geometry = []
        # for shape in self.shape_buffer:
        for shape in self.storage.get_objects():
            new_geo = shape.geo

            # simplify the MultiLineString
            if isinstance(new_geo, MultiLineString):
                new_geo = linemerge(new_geo)
            fcgeometry.solid_geometry.append(new_geo)

        self.deactivate()

    def update_options(self, obj):
        if self.paint_tooldia:
            obj.options['cnctooldia'] = deepcopy(str(self.paint_tooldia))
            self.paint_tooldia = None
            return True
        else:
            return False

    def union(self):
        """
        Makes union of selected polygons. Original polygons
        are deleted.

        :return: None.
        """

        results = unary_union([t.geo for t in self.get_selected()])

        # Delete originals.
        for_deletion = [s for s in self.get_selected()]
        for shape in for_deletion:
            self.delete_shape(shape)

        # Selected geometry is now gone!
        self.selected = []

        self.add_shape(DrawToolShape(results))

        self.replot()

    def intersection_2(self):
        """
        Makes intersection of selected polygons. Original polygons are deleted.

        :return: None
        """

        geo_shapes = self.get_selected()

        try:
            results = geo_shapes[0].geo
        except Exception as e:
            log.debug("AppGeoEditor.intersection() --> %s" % str(e))
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("A selection of minimum two items is required to do Intersection."))
            self.select_tool('select')
            return

        for shape_el in geo_shapes[1:]:
            results = results.intersection(shape_el.geo)

        # Delete originals.
        for_deletion = [s for s in self.get_selected()]
        for shape_el in for_deletion:
            self.delete_shape(shape_el)

        # Selected geometry is now gone!
        self.selected = []

        self.add_shape(DrawToolShape(results))

        self.replot()

    def intersection(self):
        """
        Makes intersection of selected polygons. Original polygons are deleted.

        :return: None
        """

        geo_shapes = self.get_selected()
        results = []
        intact = []

        try:
            intersector = geo_shapes[0].geo
        except Exception as e:
            log.debug("AppGeoEditor.intersection() --> %s" % str(e))
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("A selection of minimum two items is required to do Intersection."))
            self.select_tool('select')
            return

        for shape_el in geo_shapes[1:]:
            if intersector.intersects(shape_el.geo):
                results.append(intersector.intersection(shape_el.geo))
            else:
                intact.append(shape_el)

        if len(results) != 0:
            # Delete originals.
            for_deletion = [s for s in self.get_selected()]
            for shape_el in for_deletion:
                if shape_el not in intact:
                    self.delete_shape(shape_el)

            for geo in results:
                self.add_shape(DrawToolShape(geo))

        # Selected geometry is now gone!
        self.selected = []
        self.replot()

    def subtract(self):
        selected = self.get_selected()
        try:
            tools = selected[1:]
            toolgeo = unary_union([shp.geo for shp in tools]).buffer(0.0000001)
            target = selected[0].geo
            target = target.buffer(0.0000001)
            result = target.difference(toolgeo)

            for_deletion = [s for s in self.get_selected()]
            for shape in for_deletion:
                self.delete_shape(shape)

            self.add_shape(DrawToolShape(result))

            self.replot()
        except Exception as e:
            log.debug(str(e))

    def subtract_2(self):
        selected = self.get_selected()
        try:
            tools = selected[1:]
            toolgeo = unary_union([shp.geo for shp in tools])
            result = selected[0].geo.difference(toolgeo)

            self.delete_shape(selected[0])
            self.add_shape(DrawToolShape(result))

            self.replot()
        except Exception as e:
            log.debug(str(e))

    def cutpath(self):
        selected = self.get_selected()
        tools = selected[1:]
        toolgeo = unary_union([shp.geo for shp in tools])

        target = selected[0]
        if type(target.geo) == Polygon:
            for ring in poly2rings(target.geo):
                self.add_shape(DrawToolShape(ring.difference(toolgeo)))
        elif type(target.geo) == LineString or type(target.geo) == LinearRing:
            self.add_shape(DrawToolShape(target.geo.difference(toolgeo)))
        elif type(target.geo) == MultiLineString:
            try:
                for linestring in target.geo:
                    self.add_shape(DrawToolShape(linestring.difference(toolgeo)))
            except Exception as e:
                self.app.log.warning("Current LinearString does not intersect the target. %s" % str(e))
        else:
            self.app.log.warning("Not implemented. Object type: %s" % str(type(target.geo)))
            return

        self.delete_shape(target)
        self.replot()

    def buffer(self, buf_distance, join_style):
        selected = self.get_selected()

        if buf_distance < 0:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Negative buffer value is not accepted. Use Buffer interior to generate an "
                                   "'inside' shape"))

            # deselect everything
            self.selected = []
            self.replot()
            return 'fail'

        if len(selected) == 0:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Nothing selected."))
            return 'fail'

        if not isinstance(buf_distance, float):
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Invalid distance."))

            # deselect everything
            self.selected = []
            self.replot()
            return 'fail'

        results = []
        for t in selected:
            if isinstance(t.geo, Polygon) and not t.geo.is_empty:
                results.append(t.geo.exterior.buffer(
                    buf_distance - 1e-10,
                    resolution=int(int(self.app.defaults["geometry_circle_steps"]) / 4),
                    join_style=join_style)
                )
            else:
                results.append(t.geo.buffer(
                    buf_distance - 1e-10,
                    resolution=int(int(self.app.defaults["geometry_circle_steps"]) / 4),
                    join_style=join_style)
                )

        if not results:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Failed, the result is empty. Choose a different buffer value."))
            # deselect everything
            self.selected = []
            self.replot()
            return 'fail'

        for sha in results:
            self.add_shape(DrawToolShape(sha))

        self.replot()
        self.app.inform.emit('[success] %s' %
                             _("Full buffer geometry created."))

    def buffer_int(self, buf_distance, join_style):
        selected = self.get_selected()

        if buf_distance < 0:
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Negative buffer value is not accepted."))
            # deselect everything
            self.selected = []
            self.replot()
            return 'fail'

        if len(selected) == 0:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Nothing selected."))
            return 'fail'

        if not isinstance(buf_distance, float):
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Invalid distance."))
            # deselect everything
            self.selected = []
            self.replot()
            return 'fail'

        results = []
        for t in selected:
            if isinstance(t.geo, LinearRing):
                t.geo = Polygon(t.geo)

            if isinstance(t.geo, Polygon) and not t.geo.is_empty:
                results.append(t.geo.buffer(
                    -buf_distance + 1e-10,
                    resolution=int(int(self.app.defaults["geometry_circle_steps"]) / 4),
                    join_style=join_style)
                )

        if not results:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Failed, the result is empty. Choose a different buffer value."))
            # deselect everything
            self.selected = []
            self.replot()
            return 'fail'

        for sha in results:
            self.add_shape(DrawToolShape(sha))

        self.replot()
        self.app.inform.emit('[success] %s' % _("Interior buffer geometry created."))

    def buffer_ext(self, buf_distance, join_style):
        selected = self.get_selected()

        if buf_distance < 0:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Negative buffer value is not accepted. Use Buffer interior to generate an "
                                   "'inside' shape"))
            # deselect everything
            self.selected = []
            self.replot()
            return

        if len(selected) == 0:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Nothing selected."))
            return

        if not isinstance(buf_distance, float):
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Invalid distance."))
            # deselect everything
            self.selected = []
            self.replot()
            return

        results = []
        for t in selected:
            if isinstance(t.geo, LinearRing):
                t.geo = Polygon(t.geo)

            if isinstance(t.geo, Polygon) and not t.geo.is_empty:
                results.append(t.geo.buffer(
                    buf_distance,
                    resolution=int(int(self.app.defaults["geometry_circle_steps"]) / 4),
                    join_style=join_style)
                )

        if not results:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Failed, the result is empty. Choose a different buffer value."))
            # deselect everything
            self.selected = []
            self.replot()
            return

        for sha in results:
            self.add_shape(DrawToolShape(sha))

        self.replot()
        self.app.inform.emit('[success] %s' % _("Exterior buffer geometry created."))

    def paint(self, tooldia, overlap, margin, connect, contour, method):

        if overlap >= 100:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Could not do Paint. Overlap value has to be less than 100%%."))
            return

        self.paint_tooldia = tooldia
        selected = self.get_selected()

        if len(selected) == 0:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Nothing selected."))
            return

        for param in [tooldia, overlap, margin]:
            if not isinstance(param, float):
                param_name = [k for k, v in locals().items() if v is param][0]
                self.app.inform.emit('[WARNING] %s: %s' % (_("Invalid value for"), str(param)))

        results = []

        def recurse(geometry, reset=True):
            """
            Creates a list of non-iterable linear geometry objects.
            Results are placed in self.flat_geometry

            :param geometry: Shapely type or list or list of list of such.
            :param reset: Clears the contents of self.flat_geometry.
            """

            if geometry is None:
                return

            if reset:
                self.flat_geo = []

            # If iterable, expand recursively.
            try:
                for geo_el in geometry:
                    if geo_el is not None:
                        recurse(geometry=geo_el, reset=False)

            # Not iterable, do the actual indexing and add.
            except TypeError:
                self.flat_geo.append(geometry)

            return self.flat_geo

        for geo in selected:

            local_results = []
            for geo_obj in recurse(geo.geo):
                try:
                    if type(geo_obj) == Polygon:
                        poly_buf = geo_obj.buffer(-margin)
                    else:
                        poly_buf = Polygon(geo_obj).buffer(-margin)

                    if method == _("Seed"):
                        cp = Geometry.clear_polygon2(self, polygon_to_clear=poly_buf, tooldia=tooldia,
                                                     steps_per_circle=self.app.defaults["geometry_circle_steps"],
                                                     overlap=overlap, contour=contour, connect=connect)
                    elif method == _("Lines"):
                        cp = Geometry.clear_polygon3(self, polygon=poly_buf, tooldia=tooldia,
                                                     steps_per_circle=self.app.defaults["geometry_circle_steps"],
                                                     overlap=overlap, contour=contour, connect=connect)
                    else:
                        cp = Geometry.clear_polygon(self, polygon=poly_buf, tooldia=tooldia,
                                                    steps_per_circle=self.app.defaults["geometry_circle_steps"],
                                                    overlap=overlap, contour=contour, connect=connect)

                    if cp is not None:
                        local_results += list(cp.get_objects())
                except Exception as e:
                    log.debug("Could not Paint the polygons. %s" % str(e))
                    self.app.inform.emit(
                        '[ERROR] %s\n%s' % (_("Could not do Paint. Try a different combination of parameters. "
                                              "Or a different method of Paint"), str(e))
                    )
                    return

                # add the result to the results list
                results.append(unary_union(local_results))

        # This is a dirty patch:
        for r in results:
            self.add_shape(DrawToolShape(r))
        self.app.inform.emit('[success] %s' % _("Done."))
        self.replot()

    def flatten(self, geometry, orient_val=1, reset=True, pathonly=False):
        """
        Creates a list of non-iterable linear geometry objects.
        Polygons are expanded into its exterior and interiors if specified.

        Results are placed in self.flat_geometry

        :param geometry: Shapely type or list or list of list of such.
        :param orient_val: will orient the exterior coordinates CW if 1 and CCW for else (whatever else means ...)
        https://shapely.readthedocs.io/en/stable/manual.html#polygons
        :param reset: Clears the contents of self.flat_geometry.
        :param pathonly: Expands polygons into linear elements.
        """

        if reset:
            self.flat_geo = []

        # ## If iterable, expand recursively.
        try:
            for geo in geometry:
                if geo is not None:
                    self.flatten(geometry=geo,
                                 orient_val=orient_val,
                                 reset=False,
                                 pathonly=pathonly)

        # ## Not iterable, do the actual indexing and add.
        except TypeError:
            if type(geometry) == Polygon:
                geometry = orient(geometry, orient_val)

            if pathonly and type(geometry) == Polygon:
                self.flat_geo.append(geometry.exterior)
                self.flatten(geometry=geometry.interiors,
                             reset=False,
                             pathonly=True)
            else:
                self.flat_geo.append(geometry)

        return self.flat_geo


def distance(pt1, pt2):
    return np.sqrt((pt1[0] - pt2[0]) ** 2 + (pt1[1] - pt2[1]) ** 2)


def mag(vec):
    return np.sqrt(vec[0] ** 2 + vec[1] ** 2)


def poly2rings(poly):
    return [poly.exterior] + [interior for interior in poly.interiors]


def get_shapely_list_bounds(geometry_list):
    xmin = np.Inf
    ymin = np.Inf
    xmax = -np.Inf
    ymax = -np.Inf

    for gs in geometry_list:
        try:
            gxmin, gymin, gxmax, gymax = gs.bounds
            xmin = min([xmin, gxmin])
            ymin = min([ymin, gymin])
            xmax = max([xmax, gxmax])
            ymax = max([ymax, gymax])
        except Exception as e:
            log.warning("DEVELOPMENT: Tried to get bounds of empty geometry. --> %s" % str(e))

    return [xmin, ymin, xmax, ymax]
