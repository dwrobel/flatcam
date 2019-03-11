############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
############################################################

############################################################                                      #
# File Modified: Marius Adrian Stanciu (c)                 #
# Date: 3/10/2019                                          #
############################################################

from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import Qt, QSettings
from camlib import *
from FlatCAMTool import FlatCAMTool
from flatcamGUI.ObjectUI import LengthEntry, RadioSet

from shapely.geometry import LineString, LinearRing, MultiLineString
from shapely.ops import cascaded_union
import shapely.affinity as affinity

from numpy import arctan2, Inf, array, sqrt, sign, dot

from rtree import index as rtindex
from flatcamGUI.GUIElements import OptionalInputSection, FCCheckBox, FCEntry, FCComboBox, FCTextAreaRich, \
    FCTable, FCDoubleSpinner, FCButton, EvalEntry2, FCInputDialog
from ParseFont import *

import gettext
import FlatCAMTranslation as fcTranslate

fcTranslate.apply_language('FlatCAMEditor')
import builtins
if '_' not in builtins.__dict__:
    _ = gettext.gettext

class BufferSelectionTool(FlatCAMTool):
    """
    Simple input for buffer distance.
    """

    toolName = "Buffer Selection"

    def __init__(self, app, draw_app):
        FlatCAMTool.__init__(self, app)

        self.draw_app = draw_app

        # Title
        title_label = QtWidgets.QLabel("%s" % ('Editor ' + self.toolName))
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
        self.buffer_distance_entry = FCEntry()
        form_layout.addRow(_("Buffer distance:"), self.buffer_distance_entry)
        self.buffer_corner_lbl = QtWidgets.QLabel(_("Buffer corner:"))
        self.buffer_corner_lbl.setToolTip(
            _("There are 3 types of corners:\n"
            " - 'Round': the corner is rounded for exterior buffer.\n"
            " - 'Square:' the corner is met in a sharp angle for exterior buffer.\n"
            " - 'Beveled:' the corner is a line that directly connects the features meeting in the corner")
        )
        self.buffer_corner_cb = FCComboBox()
        self.buffer_corner_cb.addItem(_("Round"))
        self.buffer_corner_cb.addItem(_("Square"))
        self.buffer_corner_cb.addItem(_("Beveled"))
        form_layout.addRow(self.buffer_corner_lbl, self.buffer_corner_cb)

        # Buttons
        hlay = QtWidgets.QHBoxLayout()
        self.buffer_tools_box.addLayout(hlay)

        self.buffer_int_button = QtWidgets.QPushButton(_("Buffer Interior"))
        hlay.addWidget(self.buffer_int_button)
        self.buffer_ext_button = QtWidgets.QPushButton(_("Buffer Exterior"))
        hlay.addWidget(self.buffer_ext_button)

        hlay1 = QtWidgets.QHBoxLayout()
        self.buffer_tools_box.addLayout(hlay1)

        self.buffer_button = QtWidgets.QPushButton(_("Full Buffer"))
        hlay1.addWidget(self.buffer_button)

        self.layout.addStretch()

        # Signals
        self.buffer_button.clicked.connect(self.on_buffer)
        self.buffer_int_button.clicked.connect(self.on_buffer_int)
        self.buffer_ext_button.clicked.connect(self.on_buffer_ext)

        # Init GUI
        self.buffer_distance_entry.set_value(0.01)

    def run(self):
        self.app.report_usage("Geo Editor ToolBuffer()")
        FlatCAMTool.run(self)

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
                self.app.inform.emit(_("[WARNING_NOTCL] Buffer distance value is missing or wrong format. "
                                     "Add it and retry."))
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
                self.app.inform.emit(_("[WARNING_NOTCL] Buffer distance value is missing or wrong format. "
                                     "Add it and retry."))
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
                self.app.inform.emit(_("[WARNING_NOTCL] Buffer distance value is missing or wrong format. "
                                     "Add it and retry."))
                return
        # the cb index start from 0 but the join styles for the buffer start from 1 therefore the adjustment
        # I populated the combobox such that the index coincide with the join styles value (which is really an INT)
        join_style = self.buffer_corner_cb.currentIndex() + 1
        self.draw_app.buffer_ext(buffer_distance, join_style)

    def hide_tool(self):
        self.buffer_tool_frame.hide()
        self.app.ui.notebook.setCurrentWidget(self.app.ui.project_tab)


class TextInputTool(FlatCAMTool):
    """
    Simple input for buffer distance.
    """

    toolName = "Text Input Tool"

    def __init__(self, app):
        FlatCAMTool.__init__(self, app)

        self.app = app
        self.text_path = []

        self.f_parse = ParseFont(self)
        self.f_parse.get_fonts_by_types()

        # this way I can hide/show the frame
        self.text_tool_frame = QtWidgets.QFrame()
        self.text_tool_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.text_tool_frame)
        self.text_tools_box = QtWidgets.QVBoxLayout()
        self.text_tools_box.setContentsMargins(0, 0, 0, 0)
        self.text_tool_frame.setLayout(self.text_tools_box)

        # Title
        title_label = QtWidgets.QLabel("%s" % ('Editor ' + self.toolName))
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
        self.form_layout.addRow("Font:", self.font_type_cb)

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
        self.font_bold_tb.setIcon(QtGui.QIcon('share/bold32.png'))
        hlay.addWidget(self.font_bold_tb)

        self.font_italic_tb = QtWidgets.QToolButton()
        self.font_italic_tb.setCheckable(True)
        self.font_italic_tb.setIcon(QtGui.QIcon('share/italic32.png'))
        hlay.addWidget(self.font_italic_tb)

        self.form_layout.addRow("Size:", hlay)

        # Text input
        self.text_input_entry = FCTextAreaRich()
        self.text_input_entry.setTabStopWidth(12)
        self.text_input_entry.setMinimumHeight(200)
        # self.text_input_entry.setMaximumHeight(150)
        self.text_input_entry.setCurrentFont(f_current)
        self.text_input_entry.setFontPointSize(10)
        self.form_layout.addRow("Text:", self.text_input_entry)

        # Buttons
        hlay1 = QtWidgets.QHBoxLayout()
        self.form_layout.addRow("", hlay1)
        hlay1.addStretch()
        self.apply_button = QtWidgets.QPushButton("Apply")
        hlay1.addWidget(self.apply_button)

        # self.layout.addStretch()

        # Signals
        self.apply_button.clicked.connect(self.on_apply_button)
        self.font_type_cb.currentFontChanged.connect(self.font_family)
        self.font_size_cb.activated.connect(self.font_size)
        self.font_bold_tb.clicked.connect(self.on_bold_button)
        self.font_italic_tb.clicked.connect(self.on_italic_button)

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

        self.text_path = self.f_parse.font_to_geometry(
                    char_string=string_to_geo,
                    font_name=self.font_name,
                    font_size=font_to_geo_size,
                    font_type=font_to_geo_type,
                    units=self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().upper())

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
        self.app.ui.notebook.setCurrentWidget(self.app.ui.project_tab)


class PaintOptionsTool(FlatCAMTool):
    """
    Inputs to specify how to paint the selected polygons.
    """

    toolName = "Paint Tool"

    def __init__(self, app, fcdraw):
        FlatCAMTool.__init__(self, app)

        self.app = app
        self.fcdraw = fcdraw

        ## Title
        title_label = QtWidgets.QLabel("%s" % ('Editor ' + self.toolName))
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

        # Tool dia
        ptdlabel = QtWidgets.QLabel(_('Tool dia:'))
        ptdlabel.setToolTip(
           _( "Diameter of the tool to\n"
            "be used in the operation.")
        )
        grid.addWidget(ptdlabel, 0, 0)

        self.painttooldia_entry = FCEntry()
        grid.addWidget(self.painttooldia_entry, 0, 1)

        # Overlap
        ovlabel = QtWidgets.QLabel(_('Overlap:'))
        ovlabel.setToolTip(
            _("How much (fraction) of the tool width to overlap each tool pass.\n"
            "Example:\n"
            "A value here of 0.25 means 25% from the tool diameter found above.\n\n"
            "Adjust the value starting with lower values\n"
            "and increasing it if areas that should be painted are still \n"
            "not painted.\n"
            "Lower values = faster processing, faster execution on PCB.\n"
            "Higher values = slow processing and slow execution on CNC\n"
            "due of too many paths.")
        )
        grid.addWidget(ovlabel, 1, 0)
        self.paintoverlap_entry = FCEntry()
        self.paintoverlap_entry.setValidator(QtGui.QDoubleValidator(0.0000, 1.0000, 4))
        grid.addWidget(self.paintoverlap_entry, 1, 1)

        # Margin
        marginlabel = QtWidgets.QLabel(_('Margin:'))
        marginlabel.setToolTip(
           _( "Distance by which to avoid\n"
            "the edges of the polygon to\n"
            "be painted.")
        )
        grid.addWidget(marginlabel, 2, 0)
        self.paintmargin_entry = FCEntry()
        grid.addWidget(self.paintmargin_entry, 2, 1)

        # Method
        methodlabel = QtWidgets.QLabel(_('Method:'))
        methodlabel.setToolTip(
            _("Algorithm to paint the polygon:<BR>"
            "<B>Standard</B>: Fixed step inwards.<BR>"
            "<B>Seed-based</B>: Outwards from seed.")
        )
        grid.addWidget(methodlabel, 3, 0)
        self.paintmethod_combo = RadioSet([
            {"label": _("Standard"), "value": "standard"},
            {"label": _("Seed-based"), "value": "seed"},
            {"label": _("Straight lines"), "value": "lines"}
        ], orientation='vertical', stretch=False)
        grid.addWidget(self.paintmethod_combo, 3, 1)

        # Connect lines
        pathconnectlabel = QtWidgets.QLabel(_("Connect:"))
        pathconnectlabel.setToolTip(
           _( "Draw lines between resulting\n"
            "segments to minimize tool lifts.")
        )
        grid.addWidget(pathconnectlabel, 4, 0)
        self.pathconnect_cb = FCCheckBox()
        grid.addWidget(self.pathconnect_cb, 4, 1)

        contourlabel = QtWidgets.QLabel(_("Contour:"))
        contourlabel.setToolTip(
            _("Cut around the perimeter of the polygon\n"
            "to trim rough edges.")
        )
        grid.addWidget(contourlabel, 5, 0)
        self.paintcontour_cb = FCCheckBox()
        grid.addWidget(self.paintcontour_cb, 5, 1)


        ## Buttons
        hlay = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay)
        hlay.addStretch()
        self.paint_button = QtWidgets.QPushButton(_("Paint"))
        hlay.addWidget(self.paint_button)

        self.layout.addStretch()

        ## Signals
        self.paint_button.clicked.connect(self.on_paint)

        self.set_tool_ui()

    def run(self):
        self.app.report_usage("Geo Editor ToolPaint()")
        FlatCAMTool.run(self)

        # if the splitter us hidden, display it
        if self.app.ui.splitter.sizes()[0] == 0:
            self.app.ui.splitter.setSizes([1, 1])

        self.app.ui.notebook.setTabText(2, _("Paint Tool"))

    def set_tool_ui(self):
        ## Init GUI
        if self.app.defaults["tools_painttooldia"]:
            self.painttooldia_entry.set_value(self.app.defaults["tools_painttooldia"])
        else:
            self.painttooldia_entry.set_value(0.0)

        if self.app.defaults["tools_paintoverlap"]:
            self.paintoverlap_entry.set_value(self.app.defaults["tools_paintoverlap"])
        else:
            self.paintoverlap_entry.set_value(0.0)

        if self.app.defaults["tools_paintmargin"]:
            self.paintmargin_entry.set_value(self.app.defaults["tools_paintmargin"])
        else:
            self.paintmargin_entry.set_value(0.0)

        if self.app.defaults["tools_paintmethod"]:
            self.paintmethod_combo.set_value(self.app.defaults["tools_paintmethod"])
        else:
            self.paintmethod_combo.set_value("seed")

        if self.app.defaults["tools_pathconnect"]:
            self.pathconnect_cb.set_value(self.app.defaults["tools_pathconnect"])
        else:
            self.pathconnect_cb.set_value(False)

        if self.app.defaults["tools_paintcontour"]:
            self.paintcontour_cb.set_value(self.app.defaults["tools_paintcontour"])
        else:
            self.paintcontour_cb.set_value(False)

    def on_paint(self):
        if not self.fcdraw.selected:
            self.app.inform.emit(_("[WARNING_NOTCL] Paint cancelled. No shape selected."))
            return

        try:
            tooldia = float(self.painttooldia_entry.get_value())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                tooldia = float(self.painttooldia_entry.get_value().replace(',', '.'))
                self.painttooldia_entry.set_value(tooldia)
            except ValueError:
                self.app.inform.emit(_("[WARNING_NOTCL] Tool diameter value is missing or wrong format. "
                                     "Add it and retry."))
                return
        try:
            overlap = float(self.paintoverlap_entry.get_value())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                overlap = float(self.paintoverlap_entry.get_value().replace(',', '.'))
                self.paintoverlap_entry.set_value(overlap)
            except ValueError:
                self.app.inform.emit(_("[WARNING_NOTCL] Overlap value is missing or wrong format. "
                                     "Add it and retry."))
                return

        try:
            margin = float(self.paintmargin_entry.get_value())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                margin = float(self.paintmargin_entry.get_value().replace(',', '.'))
                self.paintmargin_entry.set_value(margin)
            except ValueError:
                self.app.inform.emit(_("[WARNING_NOTCL] Margin distance value is missing or wrong format. "
                                     "Add it and retry."))
                return
        method = self.paintmethod_combo.get_value()
        contour = self.paintcontour_cb.get_value()
        connect = self.pathconnect_cb.get_value()

        self.fcdraw.paint(tooldia, overlap, margin, connect=connect, contour=contour, method=method)
        self.fcdraw.select_tool("select")
        self.app.ui.notebook.setTabText(2, _("Tools"))
        self.app.ui.notebook.setCurrentWidget(self.app.ui.project_tab)

        self.app.ui.splitter.setSizes([0, 1])


class TransformEditorTool(FlatCAMTool):
    """
    Inputs to specify how to paint the selected polygons.
    """

    toolName = _("Transform Tool")
    rotateName = _("Rotate")
    skewName = _("Skew/Shear")
    scaleName = _("Scale")
    flipName = _("Mirror (Flip)")
    offsetName = _("Offset")

    def __init__(self, app, draw_app):
        FlatCAMTool.__init__(self, app)

        self.app = app
        self.draw_app = draw_app

        self.transform_lay = QtWidgets.QVBoxLayout()
        self.layout.addLayout(self.transform_lay)
        ## Title
        title_label = QtWidgets.QLabel("%s" % (_('Editor %s') % self.toolName))
        title_label.setStyleSheet("""
                QLabel
                {
                    font-size: 16px;
                    font-weight: bold;
                }
                """)
        self.transform_lay.addWidget(title_label)

        self.empty_label = QtWidgets.QLabel("")
        self.empty_label.setFixedWidth(50)

        self.empty_label1 = QtWidgets.QLabel("")
        self.empty_label1.setFixedWidth(70)
        self.empty_label2 = QtWidgets.QLabel("")
        self.empty_label2.setFixedWidth(70)
        self.empty_label3 = QtWidgets.QLabel("")
        self.empty_label3.setFixedWidth(70)
        self.empty_label4 = QtWidgets.QLabel("")
        self.empty_label4.setFixedWidth(70)
        self.transform_lay.addWidget(self.empty_label)

        ## Rotate Title
        rotate_title_label = QtWidgets.QLabel("<font size=3><b>%s</b></font>" % self.rotateName)
        self.transform_lay.addWidget(rotate_title_label)

        ## Layout
        form_layout = QtWidgets.QFormLayout()
        self.transform_lay.addLayout(form_layout)
        form_child = QtWidgets.QHBoxLayout()

        self.rotate_label = QtWidgets.QLabel(_("Angle:"))
        self.rotate_label.setToolTip(
           _( "Angle for Rotation action, in degrees.\n"
            "Float number between -360 and 359.\n"
            "Positive numbers for CW motion.\n"
            "Negative numbers for CCW motion.")
        )
        self.rotate_label.setFixedWidth(50)

        self.rotate_entry = FCEntry()
        # self.rotate_entry.setFixedWidth(60)
        self.rotate_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.rotate_button = FCButton()
        self.rotate_button.set_value(_("Rotate"))
        self.rotate_button.setToolTip(
            _("Rotate the selected shape(s).\n"
            "The point of reference is the middle of\n"
            "the bounding box for all selected shapes.")
        )
        self.rotate_button.setFixedWidth(60)

        form_child.addWidget(self.rotate_entry)
        form_child.addWidget(self.rotate_button)

        form_layout.addRow(self.rotate_label, form_child)

        self.transform_lay.addWidget(self.empty_label1)

        ## Skew Title
        skew_title_label = QtWidgets.QLabel("<font size=3><b>%s</b></font>" % self.skewName)
        self.transform_lay.addWidget(skew_title_label)

        ## Form Layout
        form1_layout = QtWidgets.QFormLayout()
        self.transform_lay.addLayout(form1_layout)
        form1_child_1 = QtWidgets.QHBoxLayout()
        form1_child_2 = QtWidgets.QHBoxLayout()

        self.skewx_label = QtWidgets.QLabel(_("Angle X:"))
        self.skewx_label.setToolTip(
          _(  "Angle for Skew action, in degrees.\n"
            "Float number between -360 and 359.")
        )
        self.skewx_label.setFixedWidth(50)
        self.skewx_entry = FCEntry()
        self.skewx_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        # self.skewx_entry.setFixedWidth(60)

        self.skewx_button = FCButton()
        self.skewx_button.set_value(_("Skew X"))
        self.skewx_button.setToolTip(
           _( "Skew/shear the selected shape(s).\n"
            "The point of reference is the middle of\n"
            "the bounding box for all selected shapes."))
        self.skewx_button.setFixedWidth(60)

        self.skewy_label = QtWidgets.QLabel(_("Angle Y:"))
        self.skewy_label.setToolTip(
           _( "Angle for Skew action, in degrees.\n"
            "Float number between -360 and 359.")
        )
        self.skewy_label.setFixedWidth(50)
        self.skewy_entry = FCEntry()
        self.skewy_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        # self.skewy_entry.setFixedWidth(60)

        self.skewy_button = FCButton()
        self.skewy_button.set_value(_("Skew Y"))
        self.skewy_button.setToolTip(
            _("Skew/shear the selected shape(s).\n"
            "The point of reference is the middle of\n"
            "the bounding box for all selected shapes."))
        self.skewy_button.setFixedWidth(60)

        form1_child_1.addWidget(self.skewx_entry)
        form1_child_1.addWidget(self.skewx_button)

        form1_child_2.addWidget(self.skewy_entry)
        form1_child_2.addWidget(self.skewy_button)

        form1_layout.addRow(self.skewx_label, form1_child_1)
        form1_layout.addRow(self.skewy_label, form1_child_2)

        self.transform_lay.addWidget(self.empty_label2)

        ## Scale Title
        scale_title_label = QtWidgets.QLabel("<font size=3><b>%s</b></font>" % self.scaleName)
        self.transform_lay.addWidget(scale_title_label)

        ## Form Layout
        form2_layout = QtWidgets.QFormLayout()
        self.transform_lay.addLayout(form2_layout)
        form2_child_1 = QtWidgets.QHBoxLayout()
        form2_child_2 = QtWidgets.QHBoxLayout()

        self.scalex_label = QtWidgets.QLabel(_("Factor X:"))
        self.scalex_label.setToolTip(
            _("Factor for Scale action over X axis.")
        )
        self.scalex_label.setFixedWidth(50)
        self.scalex_entry = FCEntry()
        self.scalex_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        # self.scalex_entry.setFixedWidth(60)

        self.scalex_button = FCButton()
        self.scalex_button.set_value(_("Scale X"))
        self.scalex_button.setToolTip(
           _( "Scale the selected shape(s).\n"
            "The point of reference depends on \n"
            "the Scale reference checkbox state."))
        self.scalex_button.setFixedWidth(60)

        self.scaley_label = QtWidgets.QLabel(_("Factor Y:"))
        self.scaley_label.setToolTip(
            _("Factor for Scale action over Y axis.")
        )
        self.scaley_label.setFixedWidth(50)
        self.scaley_entry = FCEntry()
        self.scaley_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        # self.scaley_entry.setFixedWidth(60)

        self.scaley_button = FCButton()
        self.scaley_button.set_value(_("Scale Y"))
        self.scaley_button.setToolTip(
           _( "Scale the selected shape(s).\n"
            "The point of reference depends on \n"
            "the Scale reference checkbox state."))
        self.scaley_button.setFixedWidth(60)

        self.scale_link_cb = FCCheckBox()
        self.scale_link_cb.set_value(True)
        self.scale_link_cb.setText(_("Link"))
        self.scale_link_cb.setToolTip(
            _("Scale the selected shape(s)\n"
            "using the Scale Factor X for both axis."))
        self.scale_link_cb.setFixedWidth(50)

        self.scale_zero_ref_cb = FCCheckBox()
        self.scale_zero_ref_cb.set_value(True)
        self.scale_zero_ref_cb.setText(_("Scale Reference"))
        self.scale_zero_ref_cb.setToolTip(
            _("Scale the selected shape(s)\n"
            "using the origin reference when checked,\n"
            "and the center of the biggest bounding box\n"
            "of the selected shapes when unchecked."))

        form2_child_1.addWidget(self.scalex_entry)
        form2_child_1.addWidget(self.scalex_button)

        form2_child_2.addWidget(self.scaley_entry)
        form2_child_2.addWidget(self.scaley_button)

        form2_layout.addRow(self.scalex_label, form2_child_1)
        form2_layout.addRow(self.scaley_label, form2_child_2)
        form2_layout.addRow(self.scale_link_cb, self.scale_zero_ref_cb)
        self.ois_scale = OptionalInputSection(self.scale_link_cb, [self.scaley_entry, self.scaley_button], logic=False)

        self.transform_lay.addWidget(self.empty_label3)

        ## Offset Title
        offset_title_label = QtWidgets.QLabel("<font size=3><b>%s</b></font>" % self.offsetName)
        self.transform_lay.addWidget(offset_title_label)

        ## Form Layout
        form3_layout = QtWidgets.QFormLayout()
        self.transform_lay.addLayout(form3_layout)
        form3_child_1 = QtWidgets.QHBoxLayout()
        form3_child_2 = QtWidgets.QHBoxLayout()

        self.offx_label = QtWidgets.QLabel(_("Value X:"))
        self.offx_label.setToolTip(
            _("Value for Offset action on X axis.")
        )
        self.offx_label.setFixedWidth(50)
        self.offx_entry = FCEntry()
        self.offx_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        # self.offx_entry.setFixedWidth(60)

        self.offx_button = FCButton()
        self.offx_button.set_value(_("Offset X"))
        self.offx_button.setToolTip(
           _( "Offset the selected shape(s).\n"
            "The point of reference is the middle of\n"
            "the bounding box for all selected shapes.\n")
        )
        self.offx_button.setFixedWidth(60)

        self.offy_label = QtWidgets.QLabel(_("Value Y:"))
        self.offy_label.setToolTip(
            _("Value for Offset action on Y axis.")
        )
        self.offy_label.setFixedWidth(50)
        self.offy_entry = FCEntry()
        self.offy_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        # self.offy_entry.setFixedWidth(60)

        self.offy_button = FCButton()
        self.offy_button.set_value(_("Offset Y"))
        self.offy_button.setToolTip(
            _("Offset the selected shape(s).\n"
            "The point of reference is the middle of\n"
            "the bounding box for all selected shapes.\n")
        )
        self.offy_button.setFixedWidth(60)

        form3_child_1.addWidget(self.offx_entry)
        form3_child_1.addWidget(self.offx_button)

        form3_child_2.addWidget(self.offy_entry)
        form3_child_2.addWidget(self.offy_button)

        form3_layout.addRow(self.offx_label, form3_child_1)
        form3_layout.addRow(self.offy_label, form3_child_2)

        self.transform_lay.addWidget(self.empty_label4)

        ## Flip Title
        flip_title_label = QtWidgets.QLabel("<font size=3><b>%s</b></font>" % self.flipName)
        self.transform_lay.addWidget(flip_title_label)

        ## Form Layout
        form4_layout = QtWidgets.QFormLayout()
        form4_child_hlay = QtWidgets.QHBoxLayout()
        self.transform_lay.addLayout(form4_child_hlay)
        self.transform_lay.addLayout(form4_layout)
        form4_child_1 = QtWidgets.QHBoxLayout()

        self.flipx_button = FCButton()
        self.flipx_button.set_value(_("Flip on X"))
        self.flipx_button.setToolTip(
            _("Flip the selected shape(s) over the X axis.\n"
            "Does not create a new shape.")
        )
        self.flipx_button.setFixedWidth(60)

        self.flipy_button = FCButton()
        self.flipy_button.set_value(_("Flip on Y"))
        self.flipy_button.setToolTip(
            _("Flip the selected shape(s) over the X axis.\n"
            "Does not create a new shape.")
        )
        self.flipy_button.setFixedWidth(60)

        self.flip_ref_cb = FCCheckBox()
        self.flip_ref_cb.set_value(True)
        self.flip_ref_cb.setText(_("Ref Pt"))
        self.flip_ref_cb.setToolTip(
            _("Flip the selected shape(s)\n"
            "around the point in Point Entry Field.\n"
            "\n"
            "The point coordinates can be captured by\n"
            "left click on canvas together with pressing\n"
            "SHIFT key. \n"
            "Then click Add button to insert coordinates.\n"
            "Or enter the coords in format (x, y) in the\n"
            "Point Entry field and click Flip on X(Y)")
        )
        self.flip_ref_cb.setFixedWidth(50)

        self.flip_ref_label = QtWidgets.QLabel(_("Point:"))
        self.flip_ref_label.setToolTip(
            _("Coordinates in format (x, y) used as reference for mirroring.\n"
            "The 'x' in (x, y) will be used when using Flip on X and\n"
            "the 'y' in (x, y) will be used when using Flip on Y.")
        )
        self.flip_ref_label.setFixedWidth(50)
        self.flip_ref_entry = EvalEntry2("(0, 0)")
        self.flip_ref_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        # self.flip_ref_entry.setFixedWidth(60)

        self.flip_ref_button = FCButton()
        self.flip_ref_button.set_value(_("Add"))
        self.flip_ref_button.setToolTip(
           _( "The point coordinates can be captured by\n"
            "left click on canvas together with pressing\n"
            "SHIFT key. Then click Add button to insert.")
           )
        self.flip_ref_button.setFixedWidth(60)

        form4_child_hlay.addStretch()
        form4_child_hlay.addWidget(self.flipx_button)
        form4_child_hlay.addWidget(self.flipy_button)

        form4_child_1.addWidget(self.flip_ref_entry)
        form4_child_1.addWidget(self.flip_ref_button)

        form4_layout.addRow(self.flip_ref_cb)
        form4_layout.addRow(self.flip_ref_label, form4_child_1)
        self.ois_flip = OptionalInputSection(self.flip_ref_cb,
                                             [self.flip_ref_entry, self.flip_ref_button], logic=True)

        self.transform_lay.addStretch()

        ## Signals
        self.rotate_button.clicked.connect(self.on_rotate)
        self.skewx_button.clicked.connect(self.on_skewx)
        self.skewy_button.clicked.connect(self.on_skewy)
        self.scalex_button.clicked.connect(self.on_scalex)
        self.scaley_button.clicked.connect(self.on_scaley)
        self.offx_button.clicked.connect(self.on_offx)
        self.offy_button.clicked.connect(self.on_offy)
        self.flipx_button.clicked.connect(self.on_flipx)
        self.flipy_button.clicked.connect(self.on_flipy)
        self.flip_ref_button.clicked.connect(self.on_flip_add_coords)

        self.rotate_entry.returnPressed.connect(self.on_rotate)
        self.skewx_entry.returnPressed.connect(self.on_skewx)
        self.skewy_entry.returnPressed.connect(self.on_skewy)
        self.scalex_entry.returnPressed.connect(self.on_scalex)
        self.scaley_entry.returnPressed.connect(self.on_scaley)
        self.offx_entry.returnPressed.connect(self.on_offx)
        self.offy_entry.returnPressed.connect(self.on_offy)

        self.set_tool_ui()

    def run(self):
        self.app.report_usage("Geo Editor Transform Tool()")
        FlatCAMTool.run(self)
        self.set_tool_ui()

        # if the splitter us hidden, display it
        if self.app.ui.splitter.sizes()[0] == 0:
            self.app.ui.splitter.setSizes([1, 1])

        self.app.ui.notebook.setTabText(2, _("Transform Tool"))

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, shortcut='ALT+T', **kwargs)

    def set_tool_ui(self):
        ## Initialize form
        if self.app.defaults["tools_transform_rotate"]:
            self.rotate_entry.set_value(self.app.defaults["tools_transform_rotate"])
        else:
            self.rotate_entry.set_value(0.0)

        if self.app.defaults["tools_transform_skew_x"]:
            self.skewx_entry.set_value(self.app.defaults["tools_transform_skew_x"])
        else:
            self.skewx_entry.set_value(0.0)

        if self.app.defaults["tools_transform_skew_y"]:
            self.skewy_entry.set_value(self.app.defaults["tools_transform_skew_y"])
        else:
            self.skewy_entry.set_value(0.0)

        if self.app.defaults["tools_transform_scale_x"]:
            self.scalex_entry.set_value(self.app.defaults["tools_transform_scale_x"])
        else:
            self.scalex_entry.set_value(1.0)

        if self.app.defaults["tools_transform_scale_y"]:
            self.scaley_entry.set_value(self.app.defaults["tools_transform_scale_y"])
        else:
            self.scaley_entry.set_value(1.0)

        if self.app.defaults["tools_transform_scale_link"]:
            self.scale_link_cb.set_value(self.app.defaults["tools_transform_scale_link"])
        else:
            self.scale_link_cb.set_value(True)

        if self.app.defaults["tools_transform_scale_reference"]:
            self.scale_zero_ref_cb.set_value(self.app.defaults["tools_transform_scale_reference"])
        else:
            self.scale_zero_ref_cb.set_value(True)

        if self.app.defaults["tools_transform_offset_x"]:
            self.offx_entry.set_value(self.app.defaults["tools_transform_offset_x"])
        else:
            self.offx_entry.set_value(0.0)

        if self.app.defaults["tools_transform_offset_y"]:
            self.offy_entry.set_value(self.app.defaults["tools_transform_offset_y"])
        else:
            self.offy_entry.set_value(0.0)

        if self.app.defaults["tools_transform_mirror_reference"]:
            self.flip_ref_cb.set_value(self.app.defaults["tools_transform_mirror_reference"])
        else:
            self.flip_ref_cb.set_value(False)

        if self.app.defaults["tools_transform_mirror_point"]:
            self.flip_ref_entry.set_value(self.app.defaults["tools_transform_mirror_point"])
        else:
            self.flip_ref_entry.set_value((0, 0))

    def template(self):
        if not self.fcdraw.selected:
            self.app.inform.emit(_("[WARNING_NOTCL] Transformation cancelled. No shape selected."))
            return


        self.draw_app.select_tool("select")
        self.app.ui.notebook.setTabText(2, "Tools")
        self.app.ui.notebook.setCurrentWidget(self.app.ui.project_tab)

        self.app.ui.splitter.setSizes([0, 1])

    def on_rotate(self, sig=None, val=None):
        if val:
            value = val
        else:
            try:
                value = float(self.rotate_entry.get_value())
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    value = float(self.rotate_entry.get_value().replace(',', '.'))
                except ValueError:
                    self.app.inform.emit(_("[ERROR_NOTCL]Wrong value format entered for Rotate, "
                                         "use a number."))
                    return
        self.app.worker_task.emit({'fcn': self.on_rotate_action,
                                       'params': [value]})
        # self.on_rotate_action(value)
        return

    def on_flipx(self):
        # self.on_flip("Y")
        axis = 'Y'
        self.app.worker_task.emit({'fcn': self.on_flip,
                                   'params': [axis]})
        return

    def on_flipy(self):
        # self.on_flip("X")
        axis = 'X'
        self.app.worker_task.emit({'fcn': self.on_flip,
                                   'params': [axis]})
        return

    def on_flip_add_coords(self):
        val = self.app.clipboard.text()
        self.flip_ref_entry.set_value(val)

    def on_skewx(self, sig=None, val=None):
        if val:
            value = val
        else:
            try:
                value = float(self.skewx_entry.get_value())
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    value = float(self.skewx_entry.get_value().replace(',', '.'))
                except ValueError:
                    self.app.inform.emit(_("[ERROR_NOTCL]Wrong value format entered for Skew X, "
                                         "use a number."))
                    return

        # self.on_skew("X", value)
        axis = 'X'
        self.app.worker_task.emit({'fcn': self.on_skew,
                                   'params': [axis, value]})
        return

    def on_skewy(self, sig=None, val=None):
        if val:
            value = val
        else:
            try:
                value = float(self.skewy_entry.get_value())
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    value = float(self.skewy_entry.get_value().replace(',', '.'))
                except ValueError:
                    self.app.inform.emit(_("[ERROR_NOTCL]Wrong value format entered for Skew Y, "
                                         "use a number."))
                    return

        # self.on_skew("Y", value)
        axis = 'Y'
        self.app.worker_task.emit({'fcn': self.on_skew,
                                   'params': [axis, value]})
        return

    def on_scalex(self, sig=None, val=None):
        if val:
            xvalue = val
        else:
            try:
                xvalue = float(self.scalex_entry.get_value())
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    xvalue = float(self.scalex_entry.get_value().replace(',', '.'))
                except ValueError:
                    self.app.inform.emit(_("[ERROR_NOTCL]Wrong value format entered for Scale X, "
                                         "use a number."))
                    return

        # scaling to zero has no sense so we remove it, because scaling with 1 does nothing
        if xvalue == 0:
            xvalue = 1
        if self.scale_link_cb.get_value():
            yvalue = xvalue
        else:
            yvalue = 1

        axis = 'X'
        point = (0, 0)
        if self.scale_zero_ref_cb.get_value():
            self.app.worker_task.emit({'fcn': self.on_scale,
                                       'params': [axis, xvalue, yvalue, point]})
            # self.on_scale("X", xvalue, yvalue, point=(0,0))
        else:
            # self.on_scale("X", xvalue, yvalue)
            self.app.worker_task.emit({'fcn': self.on_scale,
                                       'params': [axis, xvalue, yvalue]})

        return

    def on_scaley(self, sig=None, val=None):
        xvalue = 1
        if val:
            yvalue = val
        else:
            try:
                yvalue = float(self.scaley_entry.get_value())
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    yvalue = float(self.scaley_entry.get_value().replace(',', '.'))
                except ValueError:
                    self.app.inform.emit(_("[ERROR_NOTCL]Wrong value format entered for Scale Y, "
                                         "use a number."))
                    return

        # scaling to zero has no sense so we remove it, because scaling with 1 does nothing
        if yvalue == 0:
            yvalue = 1

        axis = 'Y'
        point = (0, 0)
        if self.scale_zero_ref_cb.get_value():
            self.app.worker_task.emit({'fcn': self.on_scale,
                                       'params': [axis, xvalue, yvalue, point]})
            # self.on_scale("Y", xvalue, yvalue, point=(0,0))
        else:
            # self.on_scale("Y", xvalue, yvalue)
            self.app.worker_task.emit({'fcn': self.on_scale,
                                       'params': [axis, xvalue, yvalue]})

        return

    def on_offx(self, sig=None, val=None):
        if val:
            value = val
        else:
            try:
                value = float(self.offx_entry.get_value())
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    value = float(self.offx_entry.get_value().replace(',', '.'))
                except ValueError:
                    self.app.inform.emit(_("[ERROR_NOTCL]Wrong value format entered for Offset X, "
                                         "use a number."))
                    return

        # self.on_offset("X", value)
        axis = 'X'
        self.app.worker_task.emit({'fcn': self.on_offset,
                                   'params': [axis, value]})
        return

    def on_offy(self, sig=None, val=None):
        if val:
            value = val
        else:
            try:
                value = float(self.offy_entry.get_value())
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    value = float(self.offy_entry.get_value().replace(',', '.'))
                except ValueError:
                    self.app.inform.emit(_("[ERROR_NOTCL]Wrong value format entered for Offset Y, "
                                         "use a number."))
                    return

        # self.on_offset("Y", value)
        axis = 'Y'
        self.app.worker_task.emit({'fcn': self.on_offset,
                                   'params': [axis, value]})
        return

    def on_rotate_action(self, num):
        shape_list = self.draw_app.selected
        xminlist = []
        yminlist = []
        xmaxlist = []
        ymaxlist = []

        if not shape_list:
            self.app.inform.emit(_("[WARNING_NOTCL] No shape selected. Please Select a shape to rotate!"))
            return
        else:
            with self.app.proc_container.new(_("Appying Rotate")):
                try:
                    # first get a bounding box to fit all
                    for sha in shape_list:
                        xmin, ymin, xmax, ymax = sha.bounds()
                        xminlist.append(xmin)
                        yminlist.append(ymin)
                        xmaxlist.append(xmax)
                        ymaxlist.append(ymax)

                    # get the minimum x,y and maximum x,y for all objects selected
                    xminimal = min(xminlist)
                    yminimal = min(yminlist)
                    xmaximal = max(xmaxlist)
                    ymaximal = max(ymaxlist)

                    self.app.progress.emit(20)

                    for sel_sha in shape_list:
                        px = 0.5 * (xminimal + xmaximal)
                        py = 0.5 * (yminimal + ymaximal)

                        sel_sha.rotate(-num, point=(px, py))
                        self.draw_app.replot()
                        # self.draw_app.add_shape(DrawToolShape(sel_sha.geo))

                    # self.draw_app.transform_complete.emit()

                    self.app.inform.emit(_("[success] Done. Rotate completed."))

                    self.app.progress.emit(100)

                except Exception as e:
                    self.app.inform.emit(_("[ERROR_NOTCL] Due of %s, rotation movement was not executed.") % str(e))
                    return

    def on_flip(self, axis):
        shape_list = self.draw_app.selected
        xminlist = []
        yminlist = []
        xmaxlist = []
        ymaxlist = []

        if not shape_list:
            self.app.inform.emit(_("[WARNING_NOTCL] No shape selected. Please Select a shape to flip!"))
            return
        else:
            with self.app.proc_container.new(_("Applying Flip")):
                try:
                    # get mirroring coords from the point entry
                    if self.flip_ref_cb.isChecked():
                        px, py = eval('{}'.format(self.flip_ref_entry.text()))
                    # get mirroing coords from the center of an all-enclosing bounding box
                    else:
                        # first get a bounding box to fit all
                        for sha in shape_list:
                            xmin, ymin, xmax, ymax = sha.bounds()
                            xminlist.append(xmin)
                            yminlist.append(ymin)
                            xmaxlist.append(xmax)
                            ymaxlist.append(ymax)

                        # get the minimum x,y and maximum x,y for all objects selected
                        xminimal = min(xminlist)
                        yminimal = min(yminlist)
                        xmaximal = max(xmaxlist)
                        ymaximal = max(ymaxlist)

                        px = 0.5 * (xminimal + xmaximal)
                        py = 0.5 * (yminimal + ymaximal)

                    self.app.progress.emit(20)

                    # execute mirroring
                    for sha in shape_list:
                        if axis is 'X':
                            sha.mirror('X', (px, py))
                            self.app.inform.emit(_('[success] Flip on the Y axis done ...'))
                        elif axis is 'Y':
                            sha.mirror('Y', (px, py))
                            self.app.inform.emit(_('[success] Flip on the X axis done ...'))
                        self.draw_app.replot()

                    #     self.draw_app.add_shape(DrawToolShape(sha.geo))
                    #
                    # self.draw_app.transform_complete.emit()

                    self.app.progress.emit(100)

                except Exception as e:
                    self.app.inform.emit(_("[ERROR_NOTCL] Due of %s, Flip action was not executed.") % str(e))
                    return

    def on_skew(self, axis, num):
        shape_list = self.draw_app.selected
        xminlist = []
        yminlist = []

        if not shape_list:
            self.app.inform.emit(_("[WARNING_NOTCL] No shape selected. Please Select a shape to shear/skew!"))
            return
        else:
            with self.app.proc_container.new(_("Applying Skew")):
                try:
                    # first get a bounding box to fit all
                    for sha in shape_list:
                        xmin, ymin, xmax, ymax = sha.bounds()
                        xminlist.append(xmin)
                        yminlist.append(ymin)

                    # get the minimum x,y and maximum x,y for all objects selected
                    xminimal = min(xminlist)
                    yminimal = min(yminlist)

                    self.app.progress.emit(20)

                    for sha in shape_list:
                        if axis is 'X':
                            sha.skew(num, 0, point=(xminimal, yminimal))
                        elif axis is 'Y':
                            sha.skew(0, num, point=(xminimal, yminimal))
                        self.draw_app.replot()

                    #     self.draw_app.add_shape(DrawToolShape(sha.geo))
                    #
                    # self.draw_app.transform_complete.emit()

                    self.app.inform.emit(_('[success] Skew on the %s axis done ...') % str(axis))
                    self.app.progress.emit(100)

                except Exception as e:
                    self.app.inform.emit(_("[ERROR_NOTCL] Due of %s, Skew action was not executed.") % str(e))
                    return

    def on_scale(self, axis, xfactor, yfactor, point=None):
        shape_list = self.draw_app.selected
        xminlist = []
        yminlist = []
        xmaxlist = []
        ymaxlist = []

        if not shape_list:
            self.app.inform.emit(_("[WARNING_NOTCL] No shape selected. Please Select a shape to scale!"))
            return
        else:
            with self.app.proc_container.new(_("Applying Scale")):
                try:
                    # first get a bounding box to fit all
                    for sha in shape_list:
                        xmin, ymin, xmax, ymax = sha.bounds()
                        xminlist.append(xmin)
                        yminlist.append(ymin)
                        xmaxlist.append(xmax)
                        ymaxlist.append(ymax)

                    # get the minimum x,y and maximum x,y for all objects selected
                    xminimal = min(xminlist)
                    yminimal = min(yminlist)
                    xmaximal = max(xmaxlist)
                    ymaximal = max(ymaxlist)

                    self.app.progress.emit(20)

                    if point is None:
                        px = 0.5 * (xminimal + xmaximal)
                        py = 0.5 * (yminimal + ymaximal)
                    else:
                        px = 0
                        py = 0

                    for sha in shape_list:
                        sha.scale(xfactor, yfactor, point=(px, py))
                        self.draw_app.replot()

                    #     self.draw_app.add_shape(DrawToolShape(sha.geo))
                    #
                    # self.draw_app.transform_complete.emit()

                    self.app.inform.emit(_('[success] Scale on the %s axis done ...') % str(axis))
                    self.app.progress.emit(100)
                except Exception as e:
                    self.app.inform.emit(_("[ERROR_NOTCL] Due of %s, Scale action was not executed.") % str(e))
                    return

    def on_offset(self, axis, num):
        shape_list = self.draw_app.selected
        xminlist = []
        yminlist = []

        if not shape_list:
            self.app.inform.emit(_("[WARNING_NOTCL] No shape selected. Please Select a shape to offset!"))
            return
        else:
            with self.app.proc_container.new(_("Applying Offset")):
                try:
                    # first get a bounding box to fit all
                    for sha in shape_list:
                        xmin, ymin, xmax, ymax = sha.bounds()
                        xminlist.append(xmin)
                        yminlist.append(ymin)

                    # get the minimum x,y and maximum x,y for all objects selected
                    xminimal = min(xminlist)
                    yminimal = min(yminlist)
                    self.app.progress.emit(20)

                    for sha in shape_list:
                        if axis is 'X':
                            sha.offset((num, 0))
                        elif axis is 'Y':
                            sha.offset((0, num))
                        self.draw_app.replot()

                    #     self.draw_app.add_shape(DrawToolShape(sha.geo))
                    #
                    # self.draw_app.transform_complete.emit()

                    self.app.inform.emit(_('[success] Offset on the %s axis done ...') % str(axis))
                    self.app.progress.emit(100)

                except Exception as e:
                    self.app.inform.emit(_("[ERROR_NOTCL] Due of %s, Offset action was not executed.") % str(e))
                    return

    def on_rotate_key(self):
        val_box = FCInputDialog(title=_("Rotate ..."),
                                text=_('Enter an Angle Value (degrees):'),
                                min=-359.9999, max=360.0000, decimals=4,
                                init_val=float(self.app.defaults['tools_transform_rotate']))
        val_box.setWindowIcon(QtGui.QIcon('share/rotate.png'))

        val, ok = val_box.get_value()
        if ok:
            self.on_rotate(val=val)
            self.app.inform.emit(
                _("[success] Geometry shape rotate done...")
                )
            return
        else:
            self.app.inform.emit(
                _("[WARNING_NOTCL] Geometry shape rotate cancelled...")
                )

    def on_offx_key(self):
        units = self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().lower()

        val_box = FCInputDialog(title=_("Offset on X axis ..."),
                                text=(_('Enter a distance Value (%s):') % str(units)),
                                min=-9999.9999, max=10000.0000, decimals=4,
                                init_val=float(self.app.defaults['tools_transform_offset_x']))
        val_box.setWindowIcon(QtGui.QIcon('share/offsetx32.png'))

        val, ok = val_box.get_value()
        if ok:
            self.on_offx(val=val)
            self.app.inform.emit(
                _("[success] Geometry shape offset on X axis done..."))
            return
        else:
            self.app.inform.emit(
                _("[WARNING_NOTCL] Geometry shape offset X cancelled..."))

    def on_offy_key(self):
        units = self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().lower()

        val_box = FCInputDialog(title=_("Offset on Y axis ..."),
                                text=(_('Enter a distance Value (%s):') % str(units)),
                                min=-9999.9999, max=10000.0000, decimals=4,
                                init_val=float(self.app.defaults['tools_transform_offset_y']))
        val_box.setWindowIcon(QtGui.QIcon('share/offsety32.png'))

        val, ok = val_box.get_value()
        if ok:
            self.on_offx(val=val)
            self.app.inform.emit(
                _("[success] Geometry shape offset on Y axis done..."))
            return
        else:
            self.app.inform.emit(
                _("[WARNING_NOTCL] Geometry shape offset Y cancelled..."))

    def on_skewx_key(self):
        val_box = FCInputDialog(title=_("Skew on X axis ..."),
                                text=_('Enter an Angle Value (degrees):'),
                                min=-359.9999, max=360.0000, decimals=4,
                                init_val=float(self.app.defaults['tools_transform_skew_x']))
        val_box.setWindowIcon(QtGui.QIcon('share/skewX.png'))

        val, ok = val_box.get_value()
        if ok:
            self.on_skewx(val=val)
            self.app.inform.emit(
                _("[success] Geometry shape skew on X axis done..."))
            return
        else:
            self.app.inform.emit(
               _( "[WARNING_NOTCL] Geometry shape skew X cancelled..."))

    def on_skewy_key(self):
        val_box = FCInputDialog(title=_("Skew on Y axis ..."),
                                text=_('Enter an Angle Value (degrees):'),
                                min=-359.9999, max=360.0000, decimals=4,
                                init_val=float(self.app.defaults['tools_transform_skew_y']))
        val_box.setWindowIcon(QtGui.QIcon('share/skewY.png'))

        val, ok = val_box.get_value()
        if ok:
            self.on_skewx(val=val)
            self.app.inform.emit(
               _( "[success] Geometry shape skew on Y axis done..."))
            return
        else:
            self.app.inform.emit(
                _("[WARNING_NOTCL] Geometry shape skew Y cancelled..."))


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

        ## Iterable: descend into each item.
        try:
            for subo in o:
                pts += DrawToolShape.get_pts(subo)

        ## Non-iterable
        except TypeError:
            if o is not None:
                ## DrawToolShape: descend into .geo.
                if isinstance(o, DrawToolShape):
                    pts += DrawToolShape.get_pts(o.geo)

                ## Descend into .exerior and .interiors
                elif type(o) == Polygon:
                    pts += DrawToolShape.get_pts(o.exterior)
                    for i in o.interiors:
                        pts += DrawToolShape.get_pts(i)
                elif type(o) == MultiLineString:
                    for line in o:
                        pts += DrawToolShape.get_pts(line)
                ## Has .coords: list them.
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
        def bounds_rec(shape):
            if type(shape) is list:
                minx = Inf
                miny = Inf
                maxx = -Inf
                maxy = -Inf

                for k in shape:
                    minx_, miny_, maxx_, maxy_ = bounds_rec(k)
                    minx = min(minx, minx_)
                    miny = min(miny, miny_)
                    maxx = max(maxx, maxx_)
                    maxy = max(maxy, maxy_)
                return minx, miny, maxx, maxy
            else:
                # it's a Shapely object, return it's bounds
                return shape.bounds

        bounds_coords = bounds_rec(self.geo)
        return bounds_coords

    def mirror(self, axis, point):
        """
        Mirrors the shape around a specified axis passing through
        the given point.

        :param axis: "X" or "Y" indicates around which axis to mirror.
        :type axis: str
        :param point: [x, y] point belonging to the mirror axis.
        :type point: list
        :return: None
        """

        px, py = point
        xscale, yscale = {"X": (1.0, -1.0), "Y": (-1.0, 1.0)}[axis]

        def mirror_geom(shape):
            if type(shape) is list:
                new_obj = []
                for g in shape:
                    new_obj.append(mirror_geom(g))
                return new_obj
            else:
                return affinity.scale(shape, xscale, yscale, origin=(px,py))

        try:
            self.geo = mirror_geom(self.geo)
        except AttributeError:
            log.debug("DrawToolShape.mirror() --> Failed to mirror. No shape selected")

    def rotate(self, angle, point):
        """
        Rotate a shape by an angle (in degrees) around the provided coordinates.

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

        def rotate_geom(shape):
            if type(shape) is list:
                new_obj = []
                for g in shape:
                    new_obj.append(rotate_geom(g))
                return new_obj
            else:
                return affinity.rotate(shape, angle, origin=(px, py))

        try:
            self.geo = rotate_geom(self.geo)
        except AttributeError:
            log.debug("DrawToolShape.rotate() --> Failed to rotate. No shape selected")

    def skew(self, angle_x, angle_y, point):
        """
        Shear/Skew a shape by angles along x and y dimensions.

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

        def skew_geom(shape):
            if type(shape) is list:
                new_obj = []
                for g in shape:
                    new_obj.append(skew_geom(g))
                return new_obj
            else:
                return affinity.skew(shape, angle_x, angle_y, origin=(px, py))

        try:
            self.geo = skew_geom(self.geo)
        except AttributeError:
            log.debug("DrawToolShape.skew() --> Failed to skew. No shape selected")

    def offset(self, vect):
        """
        Offsets all shapes by a given vector/

        :param vect: (x, y) vector by which to offset the shape geometry
        :type vect: tuple
        :return: None
        :rtype: None
        """

        try:
            dx, dy = vect
        except TypeError:
            log.debug("DrawToolShape.offset() --> An (x,y) pair of values are needed. "
                      "Probable you entered only one value in the Offset field.")
            return

        def translate_recursion(geom):
            if type(geom) == list:
                geoms=list()
                for local_geom in geom:
                    geoms.append(translate_recursion(local_geom))
                return geoms
            else:
                return  affinity.translate(geom, xoff=dx, yoff=dy)

        try:
            self.geo = translate_recursion(self.geo)
        except AttributeError:
            log.debug("DrawToolShape.offset() --> Failed to offset. No shape selected")

    def scale(self, xfactor, yfactor=None, point=None):
        """
        Scales all shape geometry by a given factor.

        :param xfactor: Factor by which to scale the shape's geometry/
        :type xfactor: float
        :param yfactor: Factor by which to scale the shape's geometry/
        :type yfactor: float
        :return: None
        :rtype: None
        """

        try:
            xfactor = float(xfactor)
        except:
            log.debug("DrawToolShape.offset() -->  Scale factor has to be a number: integer or float.")
            return

        if yfactor is None:
            yfactor = xfactor
        else:
            try:
                yfactor = float(yfactor)
            except:
                log.debug("DrawToolShape.offset() -->  Scale factor has to be a number: integer or float.")
                return

        if point is None:
            px = 0
            py = 0
        else:
            px, py = point

        def scale_recursion(geom):
            if type(geom) == list:
                geoms=list()
                for local_geom in geom:
                    geoms.append(scale_recursion(local_geom))
                return geoms
            else:
                return  affinity.scale(geom, xfactor, yfactor, origin=(px, py))

        try:
            self.geo = scale_recursion(self.geo)
        except AttributeError:
            log.debug("DrawToolShape.scale() --> Failed to scale. No shape selected")


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
        self.start_msg = "Click on 1st point..."
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
        return None

    def utility_geometry(self, data=None):
        return None


class FCShapeTool(DrawTool):
    """
    Abstract class for tools that create a shape.
    """

    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)

    def make(self):
        pass


class FCCircle(FCShapeTool):
    """
    Resulting type: Polygon
    """

    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.name = 'circle'

        self.start_msg = _("Click on CENTER ...")
        self.steps_per_circ = self.draw_app.app.defaults["geometry_circle_steps"]

    def click(self, point):
        self.points.append(point)

        if len(self.points) == 1:
            self.draw_app.app.inform.emit(_("Click on Circle perimeter point to complete ..."))
            return "Click on perimeter to complete ..."

        if len(self.points) == 2:
            self.make()
            return "Done."

        return ""

    def utility_geometry(self, data=None):
        if len(self.points) == 1:
            p1 = self.points[0]
            p2 = data
            radius = sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)
            return DrawToolUtilityShape(Point(p1).buffer(radius, int(self.steps_per_circ / 4)))

        return None

    def make(self):
        p1 = self.points[0]
        p2 = self.points[1]
        radius = distance(p1, p2)
        self.geometry = DrawToolShape(Point(p1).buffer(radius, int(self.steps_per_circ / 4)))
        self.complete = True
        self.draw_app.app.inform.emit(_("[success]Done. Adding Circle completed."))


class FCArc(FCShapeTool):
    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.name = 'arc'

        self.start_msg = _("Click on CENTER ...")

        # Direction of rotation between point 1 and 2.
        # 'cw' or 'ccw'. Switch direction by hitting the
        # 'o' key.
        self.direction = "cw"

        # Mode
        # C12 = Center, p1, p2
        # 12C = p1, p2, Center
        # 132 = p1, p3, p2
        self.mode = "c12"  # Center, p1, p2

        self.steps_per_circ = self.draw_app.app.defaults["geometry_circle_steps"]

    def click(self, point):
        self.points.append(point)

        if len(self.points) == 1:
            self.draw_app.app.inform.emit(_("Click on Start arc point ..."))
            return "Click on 1st point ..."

        if len(self.points) == 2:
            self.draw_app.app.inform.emit(_("Click on End arc point to complete ..."))
            return "Click on 2nd point to complete ..."

        if len(self.points) == 3:
            self.make()
            return "Done."

        return ""

    def on_key(self, key):
        if key == 'o':
            self.direction = 'cw' if self.direction == 'ccw' else 'ccw'
            return 'Direction: ' + self.direction.upper()

        if key == 'p':
            if self.mode == 'c12':
                self.mode = '12c'
            elif self.mode == '12c':
                self.mode = '132'
            else:
                self.mode = 'c12'
            return 'Mode: ' + self.mode

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

                radius = sqrt((center[0] - p1[0]) ** 2 + (center[1] - p1[1]) ** 2)
                startangle = arctan2(p1[1] - center[1], p1[0] - center[0])
                stopangle = arctan2(p2[1] - center[1], p2[0] - center[0])

                return DrawToolUtilityShape([LineString(arc(center, radius, startangle, stopangle,
                                                            self.direction, self.steps_per_circ)),
                                             Point(center)])

            elif self.mode == '132':
                p1 = array(self.points[0])
                p3 = array(self.points[1])
                p2 = array(data)

                center, radius, t = three_point_circle(p1, p2, p3)
                direction = 'cw' if sign(t) > 0 else 'ccw'

                startangle = arctan2(p1[1] - center[1], p1[0] - center[0])
                stopangle = arctan2(p3[1] - center[1], p3[0] - center[0])

                return DrawToolUtilityShape([LineString(arc(center, radius, startangle, stopangle,
                                                            direction, self.steps_per_circ)),
                                             Point(center), Point(p1), Point(p3)])

            else:  # '12c'
                p1 = array(self.points[0])
                p2 = array(self.points[1])

                # Midpoint
                a = (p1 + p2) / 2.0

                # Parallel vector
                c = p2 - p1

                # Perpendicular vector
                b = dot(c, array([[0, -1], [1, 0]], dtype=float32))
                b /= norm(b)

                # Distance
                t = distance(data, a)

                # Which side? Cross product with c.
                # cross(M-A, B-A), where line is AB and M is test point.
                side = (data[0] - p1[0]) * c[1] - (data[1] - p1[1]) * c[0]
                t *= sign(side)

                # Center = a + bt
                center = a + b * t

                radius = norm(center - p1)
                startangle = arctan2(p1[1] - center[1], p1[0] - center[0])
                stopangle = arctan2(p2[1] - center[1], p2[0] - center[0])

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
            startangle = arctan2(p1[1] - center[1], p1[0] - center[0])
            stopangle = arctan2(p2[1] - center[1], p2[0] - center[0])
            self.geometry = DrawToolShape(LineString(arc(center, radius, startangle, stopangle,
                                                         self.direction, self.steps_per_circ)))

        elif self.mode == '132':
            p1 = array(self.points[0])
            p3 = array(self.points[1])
            p2 = array(self.points[2])

            center, radius, t = three_point_circle(p1, p2, p3)
            direction = 'cw' if sign(t) > 0 else 'ccw'

            startangle = arctan2(p1[1] - center[1], p1[0] - center[0])
            stopangle = arctan2(p3[1] - center[1], p3[0] - center[0])

            self.geometry = DrawToolShape(LineString(arc(center, radius, startangle, stopangle,
                                                         direction, self.steps_per_circ)))

        else:  # self.mode == '12c'
            p1 = array(self.points[0])
            p2 = array(self.points[1])
            pc = array(self.points[2])

            # Midpoint
            a = (p1 + p2) / 2.0

            # Parallel vector
            c = p2 - p1

            # Perpendicular vector
            b = dot(c, array([[0, -1], [1, 0]], dtype=float32))
            b /= norm(b)

            # Distance
            t = distance(pc, a)

            # Which side? Cross product with c.
            # cross(M-A, B-A), where line is AB and M is test point.
            side = (pc[0] - p1[0]) * c[1] - (pc[1] - p1[1]) * c[0]
            t *= sign(side)

            # Center = a + bt
            center = a + b * t

            radius = norm(center - p1)
            startangle = arctan2(p1[1] - center[1], p1[0] - center[0])
            stopangle = arctan2(p2[1] - center[1], p2[0] - center[0])

            self.geometry = DrawToolShape(LineString(arc(center, radius, startangle, stopangle,
                                                         self.direction, self.steps_per_circ)))
        self.complete = True
        self.draw_app.app.inform.emit(_("[success]Done. Arc completed."))


class FCRectangle(FCShapeTool):
    """
    Resulting type: Polygon
    """

    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.name = 'rectangle'

        self.start_msg = _("Click on 1st corner ...")

    def click(self, point):
        self.points.append(point)

        if len(self.points) == 1:
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
        p1 = self.points[0]
        p2 = self.points[1]
        # self.geometry = LinearRing([p1, (p2[0], p1[1]), p2, (p1[0], p2[1])])
        self.geometry = DrawToolShape(Polygon([p1, (p2[0], p1[1]), p2, (p1[0], p2[1])]))
        self.complete = True
        self.draw_app.app.inform.emit("_([success]Done. Rectangle completed.")


class FCPolygon(FCShapeTool):
    """
    Resulting type: Polygon
    """

    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.name = 'polygon'

        self.start_msg = _("Click on 1st point ...")

    def click(self, point):
        self.draw_app.in_action = True
        self.points.append(point)

        if len(self.points) > 0:
            self.draw_app.app.inform.emit(_("Click on next Point or click Right mouse button to complete ..."))
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
        # self.geometry = LinearRing(self.points)
        self.geometry = DrawToolShape(Polygon(self.points))
        self.draw_app.in_action = False
        self.complete = True
        self.draw_app.app.inform.emit(_("[success]Done. Polygon completed."))

    def on_key(self, key):
        if key == 'backspace':
            if len(self.points) > 0:
                self.points = self.points[0:-1]


class FCPath(FCPolygon):
    """
    Resulting type: LineString
    """

    def make(self):
        self.geometry = DrawToolShape(LineString(self.points))
        self.name = 'path'

        self.draw_app.in_action = False
        self.complete = True
        self.draw_app.app.inform.emit(_("[success]Done. Path completed."))

    def utility_geometry(self, data=None):
        if len(self.points) > 0:
            temp_points = [x for x in self.points]
            temp_points.append(data)
            return DrawToolUtilityShape(LineString(temp_points))

        return None

    def on_key(self, key):
        if key == 'backspace':
            if len(self.points) > 0:
                self.points = self.points[0:-1]


class FCSelect(DrawTool):
    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.name = 'select'

        self.storage = self.draw_app.storage
        # self.shape_buffer = self.draw_app.shape_buffer
        # self.selected = self.draw_app.selected

    def click_release(self, point):

        self.select_shapes(point)
        return ""

    def select_shapes(self, pos):
        # list where we store the overlapped shapes under our mouse left click position
        over_shape_list = []

        # pos[0] and pos[1] are the mouse click coordinates (x, y)
        for obj_shape in self.storage.get_objects():
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
                _, closest_shape = self.storage.nearest(pos)
            except StopIteration:
                return ""

            over_shape_list.append(closest_shape)

        try:
            # if there is no shape under our click then deselect all shapes
            # it will not work for 3rd method of click selection
            if not over_shape_list:
                self.draw_app.selected = []
                FlatCAMGeoEditor.draw_shape_idx = -1
            else:
                # if there are shapes under our click then advance through the list of them, one at the time in a
                # circular way
                FlatCAMGeoEditor.draw_shape_idx = (FlatCAMGeoEditor.draw_shape_idx + 1) % len(over_shape_list)
                obj_to_add = over_shape_list[int(FlatCAMGeoEditor.draw_shape_idx)]

                key_modifier = QtWidgets.QApplication.keyboardModifiers()
                if self.draw_app.app.defaults["global_mselect_key"] == 'Control':
                    # if CONTROL key is pressed then we add to the selected list the current shape but if it's already
                    # in the selected list, we removed it. Therefore first click selects, second deselects.
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


class FCDrillSelect(DrawTool):
    def __init__(self, exc_editor_app):
        DrawTool.__init__(self, exc_editor_app)
        self.name = 'drill_select'

        self.exc_editor_app = exc_editor_app
        self.storage = self.exc_editor_app.storage_dict
        # self.selected = self.exc_editor_app.selected

        # here we store all shapes that were selected so we can search for the nearest to our click location
        self.sel_storage = FlatCAMExcEditor.make_storage()

        self.exc_editor_app.resize_frame.hide()
        self.exc_editor_app.array_frame.hide()

    def click(self, point):
        key_modifier = QtWidgets.QApplication.keyboardModifiers()
        if self.exc_editor_app.app.defaults["global_mselect_key"] == 'Control':
            if key_modifier == Qt.ControlModifier:
                pass
            else:
                self.exc_editor_app.selected = []
        else:
            if key_modifier == Qt.ShiftModifier:
                pass
            else:
                self.exc_editor_app.selected = []

    def click_release(self, point):
        self.select_shapes(point)
        return ""

    def select_shapes(self, pos):
        self.exc_editor_app.tools_table_exc.clearSelection()

        try:
            # for storage in self.exc_editor_app.storage_dict:
            #     _, partial_closest_shape = self.exc_editor_app.storage_dict[storage].nearest(pos)
            #     if partial_closest_shape is not None:
            #         self.sel_storage.insert(partial_closest_shape)
            #
            # _, closest_shape = self.sel_storage.nearest(pos)

            for storage in self.exc_editor_app.storage_dict:
                for shape in self.exc_editor_app.storage_dict[storage].get_objects():
                    self.sel_storage.insert(shape)

            _, closest_shape = self.sel_storage.nearest(pos)


            # constrain selection to happen only within a certain bounding box
            x_coord, y_coord = closest_shape.geo[0].xy
            delta = (x_coord[1] - x_coord[0])
            # closest_shape_coords = (((x_coord[0] + delta / 2)), y_coord[0])
            xmin = x_coord[0] - (0.7 * delta)
            xmax = x_coord[0] + (1.7 * delta)
            ymin = y_coord[0] - (0.7 * delta)
            ymax = y_coord[0] + (1.7 * delta)
        except StopIteration:
            return ""

        if pos[0] < xmin or pos[0] > xmax or pos[1] < ymin or pos[1] > ymax:
            self.exc_editor_app.selected = []
        else:
            key_modifier = QtWidgets.QApplication.keyboardModifiers()
            if self.exc_editor_app.app.defaults["global_mselect_key"] == 'Control':
                # if CONTROL key is pressed then we add to the selected list the current shape but if it's already
                # in the selected list, we removed it. Therefore first click selects, second deselects.
                if key_modifier == Qt.ControlModifier:
                    if closest_shape in self.exc_editor_app.selected:
                        self.exc_editor_app.selected.remove(closest_shape)
                    else:
                        self.exc_editor_app.selected.append(closest_shape)
                else:
                    self.exc_editor_app.selected = []
                    self.exc_editor_app.selected.append(closest_shape)
            else:
                if key_modifier == Qt.ShiftModifier:
                    if closest_shape in self.exc_editor_app.selected:
                        self.exc_editor_app.selected.remove(closest_shape)
                    else:
                        self.exc_editor_app.selected.append(closest_shape)
                else:
                    self.exc_editor_app.selected = []
                    self.exc_editor_app.selected.append(closest_shape)

            # select the diameter of the selected shape in the tool table
            for storage in self.exc_editor_app.storage_dict:
                for shape_s in self.exc_editor_app.selected:
                    if shape_s in self.exc_editor_app.storage_dict[storage].get_objects():
                        for key in self.exc_editor_app.tool2tooldia:
                            if self.exc_editor_app.tool2tooldia[key] == storage:
                                item = self.exc_editor_app.tools_table_exc.item((key - 1), 1)
                                self.exc_editor_app.tools_table_exc.setCurrentItem(item)
                                # item.setSelected(True)
                                # self.exc_editor_app.tools_table_exc.selectItem(key - 1)
                                # midx = self.exc_editor_app.tools_table_exc.model().index((key - 1), 0)
                                # self.exc_editor_app.tools_table_exc.setCurrentIndex(midx)
                                self.draw_app.last_tool_selected = key
        # delete whatever is in selection storage, there is no longer need for those shapes
        self.sel_storage = FlatCAMExcEditor.make_storage()

        return ""

        # pos[0] and pos[1] are the mouse click coordinates (x, y)
        # for storage in self.exc_editor_app.storage_dict:
        #     for obj_shape in self.exc_editor_app.storage_dict[storage].get_objects():
        #         minx, miny, maxx, maxy = obj_shape.geo.bounds
        #         if (minx <= pos[0] <= maxx) and (miny <= pos[1] <= maxy):
        #             over_shape_list.append(obj_shape)
        #
        # try:
        #     # if there is no shape under our click then deselect all shapes
        #     if not over_shape_list:
        #         self.exc_editor_app.selected = []
        #         FlatCAMExcEditor.draw_shape_idx = -1
        #         self.exc_editor_app.tools_table_exc.clearSelection()
        #     else:
        #         # if there are shapes under our click then advance through the list of them, one at the time in a
        #         # circular way
        #         FlatCAMExcEditor.draw_shape_idx = (FlatCAMExcEditor.draw_shape_idx + 1) % len(over_shape_list)
        #         obj_to_add = over_shape_list[int(FlatCAMExcEditor.draw_shape_idx)]
        #
        #         if self.exc_editor_app.app.defaults["global_mselect_key"] == 'Shift':
        #             if self.exc_editor_app.modifiers == Qt.ShiftModifier:
        #                 if obj_to_add in self.exc_editor_app.selected:
        #                     self.exc_editor_app.selected.remove(obj_to_add)
        #                 else:
        #                     self.exc_editor_app.selected.append(obj_to_add)
        #             else:
        #                 self.exc_editor_app.selected = []
        #                 self.exc_editor_app.selected.append(obj_to_add)
        #         else:
        #             # if CONTROL key is pressed then we add to the selected list the current shape but if it's already
        #             # in the selected list, we removed it. Therefore first click selects, second deselects.
        #             if self.exc_editor_app.modifiers == Qt.ControlModifier:
        #                 if obj_to_add in self.exc_editor_app.selected:
        #                     self.exc_editor_app.selected.remove(obj_to_add)
        #                 else:
        #                     self.exc_editor_app.selected.append(obj_to_add)
        #             else:
        #                 self.exc_editor_app.selected = []
        #                 self.exc_editor_app.selected.append(obj_to_add)
        #
        #     for storage in self.exc_editor_app.storage_dict:
        #         for shape in self.exc_editor_app.selected:
        #             if shape in self.exc_editor_app.storage_dict[storage].get_objects():
        #                 for key in self.exc_editor_app.tool2tooldia:
        #                     if self.exc_editor_app.tool2tooldia[key] == storage:
        #                         item = self.exc_editor_app.tools_table_exc.item((key - 1), 1)
        #                         item.setSelected(True)
        #                         # self.exc_editor_app.tools_table_exc.selectItem(key - 1)
        #
        # except Exception as e:
        #     log.error("[ERROR] Something went bad. %s" % str(e))
        #     raise


class FCMove(FCShapeTool):
    def __init__(self, draw_app):
        FCShapeTool.__init__(self, draw_app)
        self.name = 'move'

        # self.shape_buffer = self.draw_app.shape_buffer
        if not self.draw_app.selected:
            self.draw_app.app.inform.emit(_("[WARNING_NOTCL] Move cancelled. No shape selected."))
            return
        self.origin = None
        self.destination = None
        self.start_msg = _("Click on reference point.")

    def set_origin(self, origin):
        self.draw_app.app.inform.emit(_("Click on destination point."))
        self.origin = origin

    def click(self, point):
        if len(self.draw_app.get_selected()) == 0:
            return "Nothing to move."

        if self.origin is None:
            self.set_origin(point)
            return "Click on final location."
        else:
            self.destination = point
            self.make()
            return "Done."

    def make(self):
        # Create new geometry
        dx = self.destination[0] - self.origin[0]
        dy = self.destination[1] - self.origin[1]
        self.geometry = [DrawToolShape(affinity.translate(geom.geo, xoff=dx, yoff=dy))
                         for geom in self.draw_app.get_selected()]

        # Delete old
        self.draw_app.delete_selected()

        # # Select the new
        # for g in self.geometry:
        #     # Note that g is not in the app's buffer yet!
        #     self.draw_app.set_selected(g)

        self.complete = True
        self.draw_app.app.inform.emit(_("[success]Done. Geometry(s) Move completed."))

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
        # return DrawToolUtilityShape([affinity.translate(geom.geo, xoff=dx, yoff=dy)
        #                              for geom in self.draw_app.get_selected()])


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
        self.draw_app.app.inform.emit(_("[success]Done. Geometry(s) Copy completed."))


class FCText(FCShapeTool):
    def __init__(self, draw_app):
        FCShapeTool.__init__(self, draw_app)
        self.name = 'text'

        # self.shape_buffer = self.draw_app.shape_buffer
        self.draw_app = draw_app
        self.app = draw_app.app

        self.start_msg = _("Click on the Destination point...")
        self.origin = (0, 0)

        self.text_gui = TextInputTool(self.app)
        self.text_gui.run()

    def click(self, point):
        # Create new geometry
        dx = point[0]
        dy = point[1]
        try:
            self.geometry = DrawToolShape(affinity.translate(self.text_gui.text_path, xoff=dx, yoff=dy))
        except Exception as e:
            log.debug("Font geometry is empty or incorrect: %s" % str(e))
            self.draw_app.app.inform.emit(_("[ERROR]Font not supported. Only Regular, Bold, Italic and BoldItalic are "
                                          "supported. Error: %s") % str(e))
            self.text_gui.text_path = []
            self.text_gui.hide_tool()
            self.draw_app.select_tool('select')
            return

        self.text_gui.text_path = []
        self.text_gui.hide_tool()
        self.complete = True
        self.draw_app.app.inform.emit(_("[success]Done. Adding Text completed."))

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
        except:
            return


class FCBuffer(FCShapeTool):
    def __init__(self, draw_app):
        FCShapeTool.__init__(self, draw_app)
        self.name = 'buffer'

        # self.shape_buffer = self.draw_app.shape_buffer
        self.draw_app = draw_app
        self.app = draw_app.app

        self.start_msg = _("Create buffer geometry ...")
        self.origin = (0, 0)
        self.buff_tool = BufferSelectionTool(self.app, self.draw_app)
        self.buff_tool.run()
        self.app.ui.notebook.setTabText(2, _("Buffer Tool"))
        if self.draw_app.app.ui.splitter.sizes()[0] == 0:
            self.draw_app.app.ui.splitter.setSizes([1, 1])
        self.activate()

    def on_buffer(self):
        if not self.draw_app.selected:
            self.app.inform.emit(_("[WARNING_NOTCL] Buffer cancelled. No shape selected."))
            return

        try:
            buffer_distance = float(self.buff_tool.buffer_distance_entry.get_value())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                buffer_distance = float(self.buff_tool.buffer_distance_entry.get_value().replace(',', '.'))
                self.buff_tool.buffer_distance_entry.set_value(buffer_distance)
            except ValueError:
                self.app.inform.emit(_("[WARNING_NOTCL] Buffer distance value is missing or wrong format. "
                                     "Add it and retry."))
                return
        # the cb index start from 0 but the join styles for the buffer start from 1 therefore the adjustment
        # I populated the combobox such that the index coincide with the join styles value (whcih is really an INT)
        join_style = self.buff_tool.buffer_corner_cb.currentIndex() + 1
        self.draw_app.buffer(buffer_distance, join_style)
        self.app.ui.notebook.setTabText(2, _("Tools"))
        self.draw_app.app.ui.splitter.setSizes([0, 1])

        self.disactivate()
        self.draw_app.app.inform.emit(_("[success]Done. Buffer Tool completed."))

    def on_buffer_int(self):
        if not self.draw_app.selected:
            self.app.inform.emit(_("[WARNING_NOTCL] Buffer cancelled. No shape selected."))
            return

        try:
            buffer_distance = float(self.buff_tool.buffer_distance_entry.get_value())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                buffer_distance = float(self.buff_tool.buffer_distance_entry.get_value().replace(',', '.'))
                self.buff_tool.buffer_distance_entry.set_value(buffer_distance)
            except ValueError:
                self.app.inform.emit(_("[WARNING_NOTCL] Buffer distance value is missing or wrong format. "
                                     "Add it and retry."))
                return
        # the cb index start from 0 but the join styles for the buffer start from 1 therefore the adjustment
        # I populated the combobox such that the index coincide with the join styles value (whcih is really an INT)
        join_style = self.buff_tool.buffer_corner_cb.currentIndex() + 1
        self.draw_app.buffer_int(buffer_distance, join_style)
        self.app.ui.notebook.setTabText(2, _("Tools"))
        self.draw_app.app.ui.splitter.setSizes([0, 1])

        self.disactivate()
        self.draw_app.app.inform.emit(_("[success]Done. Buffer Int Tool completed."))

    def on_buffer_ext(self):
        if not self.draw_app.selected:
            self.app.inform.emit(_("[WARNING_NOTCL] Buffer cancelled. No shape selected."))
            return

        try:
            buffer_distance = float(self.buff_tool.buffer_distance_entry.get_value())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                buffer_distance = float(self.buff_tool.buffer_distance_entry.get_value().replace(',', '.'))
                self.buff_tool.buffer_distance_entry.set_value(buffer_distance)
            except ValueError:
                self.app.inform.emit(_("[WARNING_NOTCL] Buffer distance value is missing or wrong format. "
                                     "Add it and retry."))
                return
        # the cb index start from 0 but the join styles for the buffer start from 1 therefore the adjustment
        # I populated the combobox such that the index coincide with the join styles value (whcih is really an INT)
        join_style = self.buff_tool.buffer_corner_cb.currentIndex() + 1
        self.draw_app.buffer_ext(buffer_distance, join_style)
        self.app.ui.notebook.setTabText(2, _("Tools"))
        self.draw_app.app.ui.splitter.setSizes([0, 1])

        self.disactivate()
        self.draw_app.app.inform.emit(_("[success]Done. Buffer Ext Tool completed."))

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


class FCPaint(FCShapeTool):
    def __init__(self, draw_app):
        FCShapeTool.__init__(self, draw_app)
        self.name = 'paint'

        # self.shape_buffer = self.draw_app.shape_buffer
        self.draw_app = draw_app
        self.app = draw_app.app

        self.start_msg = _("Create Paint geometry ...")
        self.origin = (0, 0)
        self.draw_app.paint_tool.run()


class FCTransform(FCShapeTool):
    def __init__(self, draw_app):
        FCShapeTool.__init__(self, draw_app)
        self.name = 'transformation'

        # self.shape_buffer = self.draw_app.shape_buffer
        self.draw_app = draw_app
        self.app = draw_app.app

        self.start_msg = _("Shape transformations ...")
        self.origin = (0, 0)
        self.draw_app.transform_tool.run()


class FCDrillAdd(FCShapeTool):
    """
    Resulting type: MultiLineString
    """

    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.name = 'drill_add'

        self.selected_dia = None
        try:
            self.draw_app.app.inform.emit(self.start_msg)
            # self.selected_dia = self.draw_app.tool2tooldia[self.draw_app.tools_table_exc.currentRow() + 1]
            self.selected_dia = self.draw_app.tool2tooldia[self.draw_app.last_tool_selected]
            # as a visual marker, select again in tooltable the actual tool that we are using
            # remember that it was deselected when clicking on canvas
            item = self.draw_app.tools_table_exc.item((self.draw_app.last_tool_selected - 1), 1)
            self.draw_app.tools_table_exc.setCurrentItem(item)

        except KeyError:
            self.draw_app.app.inform.emit(_("[WARNING_NOTCL] To add a drill first select a tool"))
            self.draw_app.select_tool("select")
            return

        geo = self.utility_geometry(data=(self.draw_app.snap_x, self.draw_app.snap_y))

        if isinstance(geo, DrawToolShape) and geo.geo is not None:
            self.draw_app.draw_utility_geometry(geo=geo)

        self.draw_app.app.inform.emit(_("Click on target location ..."))

        # Switch notebook to Selected page
        self.draw_app.app.ui.notebook.setCurrentWidget(self.draw_app.app.ui.selected_tab)

    def click(self, point):
        self.make()
        return "Done."

    def utility_geometry(self, data=None):
        self.points = data
        return DrawToolUtilityShape(self.util_shape(data))

    def util_shape(self, point):
        if point[0] is None and point[1] is None:
            point_x = self.draw_app.x
            point_y = self.draw_app.y
        else:
            point_x = point[0]
            point_y = point[1]

        start_hor_line = ((point_x - (self.selected_dia / 2)), point_y)
        stop_hor_line = ((point_x + (self.selected_dia / 2)), point_y)
        start_vert_line = (point_x, (point_y - (self.selected_dia / 2)))
        stop_vert_line = (point_x, (point_y + (self.selected_dia / 2)))

        return MultiLineString([(start_hor_line, stop_hor_line), (start_vert_line, stop_vert_line)])

    def make(self):

        # add the point to drills if the diameter is a key in the dict, if not, create it add the drill location
        # to the value, as a list of itself
        if self.selected_dia in self.draw_app.points_edit:
            self.draw_app.points_edit[self.selected_dia].append(self.points)
        else:
            self.draw_app.points_edit[self.selected_dia] = [self.points]

        self.draw_app.current_storage = self.draw_app.storage_dict[self.selected_dia]
        self.geometry = DrawToolShape(self.util_shape(self.points))
        self.complete = True
        self.draw_app.app.inform.emit(_("[success]Done. Drill added."))


class FCDrillArray(FCShapeTool):
    """
    Resulting type: MultiLineString
    """

    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.name = 'drill_array'

        self.draw_app.array_frame.show()

        self.selected_dia = None
        self.drill_axis = 'X'
        self.drill_array = 'linear'
        self.drill_array_size = None
        self.drill_pitch = None
        self.drill_linear_angle = None

        self.drill_angle = None
        self.drill_direction = None
        self.drill_radius = None

        self.origin = None
        self.destination = None
        self.flag_for_circ_array = None

        self.last_dx = 0
        self.last_dy = 0

        self.pt = []

        try:
            self.draw_app.app.inform.emit(self.start_msg)
            self.selected_dia = self.draw_app.tool2tooldia[self.draw_app.last_tool_selected]
            # as a visual marker, select again in tooltable the actual tool that we are using
            # remember that it was deselected when clicking on canvas
            item = self.draw_app.tools_table_exc.item((self.draw_app.last_tool_selected - 1), 1)
            self.draw_app.tools_table_exc.setCurrentItem(item)
        except KeyError:
            self.draw_app.app.inform.emit(_("[WARNING_NOTCL] To add an Drill Array first select a tool in Tool Table"))
            return

        geo = self.utility_geometry(data=(self.draw_app.snap_x, self.draw_app.snap_y), static=True)

        if isinstance(geo, DrawToolShape) and geo.geo is not None:
            self.draw_app.draw_utility_geometry(geo=geo)

        self.draw_app.app.inform.emit(_("Click on target location ..."))

        # Switch notebook to Selected page
        self.draw_app.app.ui.notebook.setCurrentWidget(self.draw_app.app.ui.selected_tab)

    def click(self, point):

        if self.drill_array == 'Linear':
            self.make()
            return
        else:
            if self.flag_for_circ_array is None:
                self.draw_app.in_action = True
                self.pt.append(point)

                self.flag_for_circ_array = True
                self.set_origin(point)
                self.draw_app.app.inform.emit(_("Click on the Drill Circular Array Start position"))
            else:
                self.destination = point
                self.make()
                self.flag_for_circ_array = None
                return

    def set_origin(self, origin):
        self.origin = origin

    def utility_geometry(self, data=None, static=None):
        self.drill_axis = self.draw_app.drill_axis_radio.get_value()
        self.drill_direction = self.draw_app.drill_direction_radio.get_value()
        self.drill_array = self.draw_app.array_type_combo.get_value()
        try:
            self.drill_array_size = int(self.draw_app.drill_array_size_entry.get_value())
            try:
                self.drill_pitch = float(self.draw_app.drill_pitch_entry.get_value())
                self.drill_linear_angle = float(self.draw_app.linear_angle_spinner.get_value())
                self.drill_angle = float(self.draw_app.drill_angle_entry.get_value())
            except TypeError:
                self.draw_app.app.inform.emit(
                    _("[ERROR_NOTCL] The value is not Float. Check for comma instead of dot separator."))
                return
        except Exception as e:
            self.draw_app.app.inform.emit(_("[ERROR_NOTCL] The value is mistyped. Check the value."))
            return

        if self.drill_array == 'Linear':
            if data[0] is None and data[1] is None:
                dx = self.draw_app.x
                dy = self.draw_app.y
            else:
                dx = data[0]
                dy = data[1]

            geo_list = []
            geo = None
            self.points = [dx, dy]

            for item in range(self.drill_array_size):
                if self.drill_axis == 'X':
                    geo = self.util_shape(((dx + (self.drill_pitch * item)), dy))
                if self.drill_axis == 'Y':
                    geo = self.util_shape((dx, (dy + (self.drill_pitch * item))))
                if self.drill_axis == 'A':
                    x_adj = self.drill_pitch * math.cos(math.radians(self.drill_linear_angle))
                    y_adj = self.drill_pitch * math.sin(math.radians(self.drill_linear_angle))
                    geo = self.util_shape(
                        ((dx + (x_adj * item)), (dy + (y_adj * item)))
                    )

                if static is None or static is False:
                    geo_list.append(affinity.translate(geo, xoff=(dx - self.last_dx), yoff=(dy - self.last_dy)))
                else:
                    geo_list.append(geo)
            # self.origin = data

            self.last_dx = dx
            self.last_dy = dy
            return DrawToolUtilityShape(geo_list)
        else:
            if data[0] is None and data[1] is None:
                cdx = self.draw_app.x
                cdy = self.draw_app.y
            else:
                cdx = data[0]
                cdy = data[1]

            if len(self.pt) > 0:
                temp_points = [x for x in self.pt]
                temp_points.append([cdx, cdy])
                return DrawToolUtilityShape(LineString(temp_points))

    def util_shape(self, point):
        if point[0] is None and point[1] is None:
            point_x = self.draw_app.x
            point_y = self.draw_app.y
        else:
            point_x = point[0]
            point_y = point[1]

        start_hor_line = ((point_x - (self.selected_dia / 2)), point_y)
        stop_hor_line = ((point_x + (self.selected_dia / 2)), point_y)
        start_vert_line = (point_x, (point_y - (self.selected_dia / 2)))
        stop_vert_line = (point_x, (point_y + (self.selected_dia / 2)))

        return MultiLineString([(start_hor_line, stop_hor_line), (start_vert_line, stop_vert_line)])

    def make(self):
        self.geometry = []
        geo = None

        # add the point to drills if the diameter is a key in the dict, if not, create it add the drill location
        # to the value, as a list of itself
        if self.selected_dia not in self.draw_app.points_edit:
            self.draw_app.points_edit[self.selected_dia] = []
        for i in range(self.drill_array_size):
            self.draw_app.points_edit[self.selected_dia].append(self.points)

        self.draw_app.current_storage = self.draw_app.storage_dict[self.selected_dia]

        if self.drill_array == 'Linear':
            for item in range(self.drill_array_size):
                if self.drill_axis == 'X':
                    geo = self.util_shape(((self.points[0] + (self.drill_pitch * item)), self.points[1]))
                if self.drill_axis == 'Y':
                    geo = self.util_shape((self.points[0], (self.points[1] + (self.drill_pitch * item))))
                if self.drill_axis == 'A':
                    x_adj = self.drill_pitch * math.cos(math.radians(self.drill_linear_angle))
                    y_adj = self.drill_pitch * math.sin(math.radians(self.drill_linear_angle))
                    geo = self.util_shape(
                        ((self.points[0] + (x_adj * item)), (self.points[1] + (y_adj * item)))
                    )

                self.geometry.append(DrawToolShape(geo))
        else:
            if (self.drill_angle * self.drill_array_size) > 360:
                self.draw_app.app.inform.emit(_("[WARNING_NOTCL]Too many drills for the selected spacing angle."))
                return

            radius = distance(self.destination, self.origin)
            initial_angle = math.asin((self.destination[1] - self.origin[1]) / radius)
            for i in range(self.drill_array_size):
                angle_radians = math.radians(self.drill_angle * i)
                if self.drill_direction == 'CW':
                    x = self.origin[0] + radius * math.cos(-angle_radians + initial_angle)
                    y = self.origin[1] + radius * math.sin(-angle_radians + initial_angle)
                else:
                    x = self.origin[0] + radius * math.cos(angle_radians + initial_angle)
                    y = self.origin[1] + radius * math.sin(angle_radians + initial_angle)

                geo = self.util_shape((x, y))
                self.geometry.append(DrawToolShape(geo))
        self.complete = True
        self.draw_app.app.inform.emit(_("[success]Done. Drill Array added."))
        self.draw_app.in_action = True
        self.draw_app.array_frame.hide()
        return


class FCDrillResize(FCShapeTool):
    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.name = 'drill_resize'

        self.draw_app.app.inform.emit(_("Click on the Drill(s) to resize ..."))
        self.resize_dia = None
        self.draw_app.resize_frame.show()
        self.points = None
        self.selected_dia_list = []
        self.current_storage = None
        self.geometry = []
        self.destination_storage = None

        self.draw_app.resize_btn.clicked.connect(self.make)

        # Switch notebook to Selected page
        self.draw_app.app.ui.notebook.setCurrentWidget(self.draw_app.app.ui.selected_tab)

    def make(self):
        self.draw_app.is_modified = True

        try:
            new_dia = self.draw_app.resdrill_entry.get_value()
        except:
            self.draw_app.app.inform.emit(_("[ERROR_NOTCL]Resize drill(s) failed. Please enter a diameter for resize."))
            return

        if new_dia not in self.draw_app.olddia_newdia:
            self.destination_storage = FlatCAMGeoEditor.make_storage()
            self.draw_app.storage_dict[new_dia] = self.destination_storage

            # self.olddia_newdia dict keeps the evidence on current tools diameters as keys and gets updated on values
            # each time a tool diameter is edited or added
            self.draw_app.olddia_newdia[new_dia] = new_dia
        else:
            self.destination_storage = self.draw_app.storage_dict[new_dia]

        for index in self.draw_app.tools_table_exc.selectedIndexes():
            row = index.row()
            # on column 1 in tool tables we hold the diameters, and we retrieve them as strings
            # therefore below we convert to float
            dia_on_row = self.draw_app.tools_table_exc.item(row, 1).text()
            self.selected_dia_list.append(float(dia_on_row))

        # since we add a new tool, we update also the intial state of the tool_table through it's dictionary
        # we add a new entry in the tool2tooldia dict
        self.draw_app.tool2tooldia[len(self.draw_app.olddia_newdia)] = new_dia

        sel_shapes_to_be_deleted = []

        for sel_dia in self.selected_dia_list:
            self.current_storage = self.draw_app.storage_dict[sel_dia]
            for select_shape in self.draw_app.get_selected():
                if select_shape in self.current_storage.get_objects():
                    factor = new_dia / sel_dia
                    self.geometry.append(
                        DrawToolShape(affinity.scale(select_shape.geo, xfact=factor, yfact=factor, origin='center'))
                    )
                    self.current_storage.remove(select_shape)
                    # a hack to make the tool_table display less drills per diameter when shape(drill) is deleted
                    # self.points_edit it's only useful first time when we load the data into the storage
                    # but is still used as reference when building tool_table in self.build_ui()
                    # the number of drills displayed in column 2 is just a len(self.points_edit) therefore
                    # deleting self.points_edit elements (doesn't matter who but just the number)
                    # solved the display issue.
                    del self.draw_app.points_edit[sel_dia][0]

                    sel_shapes_to_be_deleted.append(select_shape)

                    self.draw_app.on_exc_shape_complete(self.destination_storage)
                    # a hack to make the tool_table display more drills per diameter when shape(drill) is added
                    # self.points_edit it's only useful first time when we load the data into the storage
                    # but is still used as reference when building tool_table in self.build_ui()
                    # the number of drills displayed in column 2 is just a len(self.points_edit) therefore
                    # deleting self.points_edit elements (doesn't matter who but just the number)
                    # solved the display issue.
                    if new_dia not in self.draw_app.points_edit:
                        self.draw_app.points_edit[new_dia] = [(0, 0)]
                    else:
                        self.draw_app.points_edit[new_dia].append((0,0))
                    self.geometry = []

                    # if following the resize of the drills there will be no more drills for the selected tool then
                    # delete that tool
                    if not self.draw_app.points_edit[sel_dia]:
                        self.draw_app.on_tool_delete(sel_dia)

            for shp in sel_shapes_to_be_deleted:
                self.draw_app.selected.remove(shp)
            sel_shapes_to_be_deleted = []

        self.draw_app.build_ui()
        self.draw_app.replot()

        self.draw_app.resize_frame.hide()
        self.complete = True
        self.draw_app.app.inform.emit(_("[success]Done. Drill Resize completed."))

        # MS: always return to the Select Tool
        self.draw_app.select_tool("select")


class FCDrillMove(FCShapeTool):
    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.name = 'drill_move'

        # self.shape_buffer = self.draw_app.shape_buffer
        self.origin = None
        self.destination = None
        self.selected_dia_list = []

        if self.draw_app.launched_from_shortcuts is True:
            self.draw_app.launched_from_shortcuts = False
            self.draw_app.app.inform.emit(_("Click on target location ..."))
        else:
            self.draw_app.app.inform.emit(_("Click on reference location ..."))
        self.current_storage = None
        self.geometry = []

        for index in self.draw_app.tools_table_exc.selectedIndexes():
            row = index.row()
            # on column 1 in tool tables we hold the diameters, and we retrieve them as strings
            # therefore below we convert to float
            dia_on_row = self.draw_app.tools_table_exc.item(row, 1).text()
            self.selected_dia_list.append(float(dia_on_row))

        # Switch notebook to Selected page
        self.draw_app.app.ui.notebook.setCurrentWidget(self.draw_app.app.ui.selected_tab)

    def set_origin(self, origin):
        self.origin = origin

    def click(self, point):
        if len(self.draw_app.get_selected()) == 0:
            return "Nothing to move."

        if self.origin is None:
            self.set_origin(point)
            self.draw_app.app.inform.emit(_("Click on target location ..."))
            return
        else:
            self.destination = point
            self.make()

            # MS: always return to the Select Tool
            self.draw_app.select_tool("select")
            return

    def make(self):
        # Create new geometry
        dx = self.destination[0] - self.origin[0]
        dy = self.destination[1] - self.origin[1]
        sel_shapes_to_be_deleted = []

        for sel_dia in self.selected_dia_list:
            self.current_storage = self.draw_app.storage_dict[sel_dia]
            for select_shape in self.draw_app.get_selected():
                if select_shape in self.current_storage.get_objects():

                    self.geometry.append(DrawToolShape(affinity.translate(select_shape.geo, xoff=dx, yoff=dy)))
                    self.current_storage.remove(select_shape)
                    sel_shapes_to_be_deleted.append(select_shape)
                    self.draw_app.on_exc_shape_complete(self.current_storage)
                    self.geometry = []

            for shp in sel_shapes_to_be_deleted:
                self.draw_app.selected.remove(shp)
            sel_shapes_to_be_deleted = []

        self.draw_app.build_ui()
        self.draw_app.app.inform.emit(_("[success]Done. Drill(s) Move completed."))

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
        for geom in self.draw_app.get_selected():
            geo_list.append(affinity.translate(geom.geo, xoff=dx, yoff=dy))
        return DrawToolUtilityShape(geo_list)


class FCDrillCopy(FCDrillMove):
    def __init__(self, draw_app):
        FCDrillMove.__init__(self, draw_app)
        self.name = 'drill_copy'

    def make(self):
        # Create new geometry
        dx = self.destination[0] - self.origin[0]
        dy = self.destination[1] - self.origin[1]
        sel_shapes_to_be_deleted = []

        for sel_dia in self.selected_dia_list:
            self.current_storage = self.draw_app.storage_dict[sel_dia]
            for select_shape in self.draw_app.get_selected():
                if select_shape in self.current_storage.get_objects():
                    self.geometry.append(DrawToolShape(affinity.translate(select_shape.geo, xoff=dx, yoff=dy)))

                    # add some fake drills into the self.draw_app.points_edit to update the drill count in tool table
                    self.draw_app.points_edit[sel_dia].append((0, 0))

                    sel_shapes_to_be_deleted.append(select_shape)
                    self.draw_app.on_exc_shape_complete(self.current_storage)
                    self.geometry = []

            for shp in sel_shapes_to_be_deleted:
                self.draw_app.selected.remove(shp)
            sel_shapes_to_be_deleted = []

        self.draw_app.build_ui()
        self.draw_app.app.inform.emit(_("[success]Done. Drill(s) copied."))


########################
### Main Application ###
########################
class FlatCAMGeoEditor(QtCore.QObject):

    transform_complete = QtCore.pyqtSignal()

    draw_shape_idx = -1

    def __init__(self, app, disabled=False):
        assert isinstance(app, FlatCAMApp.App), \
            "Expected the app to be a FlatCAMApp.App, got %s" % type(app)

        super(FlatCAMGeoEditor, self).__init__()

        self.app = app
        self.canvas = app.plotcanvas

        self.app.ui.geo_add_circle_menuitem.triggered.connect(lambda: self.select_tool('circle'))
        self.app.ui.geo_add_arc_menuitem.triggered.connect(lambda: self.select_tool('arc'))
        self.app.ui.geo_add_rectangle_menuitem.triggered.connect(lambda: self.select_tool('rectangle'))
        self.app.ui.geo_add_polygon_menuitem.triggered.connect(lambda: self.select_tool('polygon'))
        self.app.ui.geo_add_path_menuitem.triggered.connect(lambda: self.select_tool('path'))
        self.app.ui.geo_add_text_menuitem.triggered.connect(lambda: self.select_tool('text'))
        self.app.ui.geo_paint_menuitem.triggered.connect(self.on_paint_tool)
        self.app.ui.geo_buffer_menuitem.triggered.connect(self.on_buffer_tool)
        self.app.ui.geo_transform_menuitem.triggered.connect(self.on_transform_tool)

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

        ## Toolbar events and properties
        self.tools = {
            "select": {"button": self.app.ui.geo_select_btn,
                       "constructor": FCSelect},
            "arc": {"button": self.app.ui.geo_add_arc_btn,
                    "constructor": FCArc},
            "circle": {"button": self.app.ui.geo_add_circle_btn,
                       "constructor": FCCircle},
            "path": {"button": self.app.ui.geo_add_path_btn,
                     "constructor": FCPath},
            "rectangle": {"button": self.app.ui.geo_add_rectangle_btn,
                          "constructor": FCRectangle},
            "polygon": {"button": self.app.ui.geo_add_polygon_btn,
                        "constructor": FCPolygon},
            "text": {"button": self.app.ui.geo_add_text_btn,
                     "constructor": FCText},
            "buffer": {"button": self.app.ui.geo_add_buffer_btn,
                     "constructor": FCBuffer},
            "paint": {"button": self.app.ui.geo_add_paint_btn,
                       "constructor": FCPaint},
            "move": {"button": self.app.ui.geo_move_btn,
                     "constructor": FCMove},
            "transform": {"button": self.app.ui.geo_transform_btn,
                      "constructor": FCTransform},
            "copy": {"button": self.app.ui.geo_copy_btn,
                     "constructor": FCCopy}
        }

        ### Data
        self.active_tool = None

        self.storage = FlatCAMGeoEditor.make_storage()
        self.utility = []

        # VisPy visuals
        self.fcgeometry = None
        self.shapes = self.app.plotcanvas.new_shape_collection(layers=1)
        self.tool_shape = self.app.plotcanvas.new_shape_collection(layers=1)
        self.app.pool_recreated.connect(self.pool_recreated)

        # Remove from scene
        self.shapes.enabled = False
        self.tool_shape.enabled = False

        ## List of selected shapes.
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

        # Current snapped mouse pos
        self.snap_x = None
        self.snap_y = None
        self.pos = None

        # signal that there is an action active like polygon or path
        self.in_action = False

        # this will flag if the Editor "tools" are launched from key shortcuts (True) or from menu toolbar (False)
        self.launched_from_shortcuts = False

        def make_callback(thetool):
            def f():
                self.on_tool_select(thetool)
            return f

        for tool in self.tools:
            self.tools[tool]["button"].triggered.connect(make_callback(tool))  # Events
            self.tools[tool]["button"].setCheckable(True)  # Checkable

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
        self.app.options_read_form()

        for option in self.options:
            if option in self.app.options:
                self.options[option] = self.app.options[option]

        self.app.ui.grid_gap_x_entry.setText(str(self.options["global_gridx"]))
        self.app.ui.grid_gap_y_entry.setText(str(self.options["global_gridy"]))
        self.app.ui.snap_max_dist_entry.setText(str(self.options["global_snap_max"]))
        self.app.ui.grid_gap_link_cb.setChecked(True)

        self.rtree_index = rtindex.Index()

        def entry2option(option, entry):
            try:
                self.options[option] = float(entry.text())
            except Exception as e:
                log.debug("FlatCAMGeoEditor.__init__().entry2option() --> %s" % str(e))
                return

        def gridx_changed(goption, gentry):
            entry2option(option=goption, entry=gentry)
            # if the grid link is checked copy the value in the GridX field to GridY
            if self.app.ui.grid_gap_link_cb.isChecked():
                self.app.ui.grid_gap_y_entry.set_value(self.app.ui.grid_gap_x_entry.get_value())

        self.app.ui.grid_gap_x_entry.setValidator(QtGui.QDoubleValidator())
        self.app.ui.grid_gap_x_entry.textChanged.connect(
            lambda: gridx_changed("global_gridx", self.app.ui.grid_gap_x_entry))

        self.app.ui.grid_gap_y_entry.setValidator(QtGui.QDoubleValidator())
        self.app.ui.grid_gap_y_entry.textChanged.connect(
            lambda: entry2option("global_gridy", self.app.ui.grid_gap_y_entry))

        self.app.ui.snap_max_dist_entry.setValidator(QtGui.QDoubleValidator())
        self.app.ui.snap_max_dist_entry.textChanged.connect(
            lambda: entry2option("snap_max", self.app.ui.snap_max_dist_entry))

        # store the status of the editor so the Delete at object level will not work until the edit is finished
        self.editor_active = False

        # if using Paint store here the tool diameter used
        self.paint_tooldia = None

        self.paint_tool = PaintOptionsTool(self.app, self)
        self.transform_tool = TransformEditorTool(self.app, self)

    def pool_recreated(self, pool):
        self.shapes.pool = pool
        self.tool_shape.pool = pool

    def on_transform_complete(self):
        self.delete_selected()
        self.replot()

    def activate(self):
        self.connect_canvas_event_handlers()
        self.shapes.enabled = True
        self.tool_shape.enabled = True
        self.app.app_cursor.enabled = True

        self.app.ui.snap_max_dist_entry.setEnabled(True)
        self.app.ui.corner_snap_btn.setEnabled(True)
        self.app.ui.snap_magnet.setVisible(True)
        self.app.ui.corner_snap_btn.setVisible(True)

        self.app.ui.geo_editor_menu.setDisabled(False)
        self.app.ui.geo_editor_menu.menuAction().setVisible(True)

        self.app.ui.update_obj_btn.setEnabled(True)
        self.app.ui.g_editor_cmenu.setEnabled(True)

        self.app.ui.geo_edit_toolbar.setDisabled(False)
        self.app.ui.geo_edit_toolbar.setVisible(True)
        self.app.ui.snap_toolbar.setDisabled(False)

        # prevent the user to change anything in the Selected Tab while the Geo Editor is active
        sel_tab_widget_list = self.app.ui.selected_tab.findChildren(QtWidgets.QWidget)
        for w in sel_tab_widget_list:
            w.setEnabled(False)

        # Tell the App that the editor is active
        self.editor_active = True

    def deactivate(self):
        self.disconnect_canvas_event_handlers()
        self.clear()
        self.app.ui.geo_edit_toolbar.setDisabled(True)

        settings = QSettings("Open Source", "FlatCAM")
        if settings.contains("layout"):
            layout = settings.value('layout', type=str)
            if layout == 'standard':
                # self.app.ui.geo_edit_toolbar.setVisible(False)

                self.app.ui.snap_max_dist_entry.setEnabled(False)
                self.app.ui.corner_snap_btn.setEnabled(False)
                self.app.ui.snap_magnet.setVisible(False)
                self.app.ui.corner_snap_btn.setVisible(False)
            elif layout == 'compact':
                # self.app.ui.geo_edit_toolbar.setVisible(True)

                self.app.ui.snap_max_dist_entry.setEnabled(False)
                self.app.ui.corner_snap_btn.setEnabled(False)
        else:
            # self.app.ui.geo_edit_toolbar.setVisible(False)

            self.app.ui.snap_magnet.setVisible(False)
            self.app.ui.corner_snap_btn.setVisible(False)
            self.app.ui.snap_max_dist_entry.setEnabled(False)
            self.app.ui.corner_snap_btn.setEnabled(False)

        # set the Editor Toolbar visibility to what was before entering in the Editor
        self.app.ui.geo_edit_toolbar.setVisible(False) if self.toolbar_old_state is False \
            else self.app.ui.geo_edit_toolbar.setVisible(True)

        # Disable visuals
        self.shapes.enabled = False
        self.tool_shape.enabled = False
        self.app.app_cursor.enabled = False

        self.app.ui.geo_editor_menu.setDisabled(True)
        self.app.ui.geo_editor_menu.menuAction().setVisible(False)

        self.app.ui.update_obj_btn.setEnabled(False)

        self.app.ui.g_editor_cmenu.setEnabled(False)
        self.app.ui.e_editor_cmenu.setEnabled(False)

        # Tell the app that the editor is no longer active
        self.editor_active = False

        # Show original geometry
        if self.fcgeometry:
            self.fcgeometry.visible = True

    def connect_canvas_event_handlers(self):
        ## Canvas events

        # make sure that the shortcuts key and mouse events will no longer be linked to the methods from FlatCAMApp
        # but those from FlatCAMGeoEditor

        self.app.plotcanvas.vis_disconnect('mouse_press', self.app.on_mouse_click_over_plot)
        self.app.plotcanvas.vis_disconnect('mouse_move', self.app.on_mouse_move_over_plot)
        self.app.plotcanvas.vis_disconnect('mouse_release', self.app.on_mouse_click_release_over_plot)
        self.app.plotcanvas.vis_disconnect('mouse_double_click', self.app.on_double_click_over_plot)

        self.app.collection.view.clicked.disconnect()

        self.canvas.vis_connect('mouse_press', self.on_canvas_click)
        self.canvas.vis_connect('mouse_move', self.on_canvas_move)
        self.canvas.vis_connect('mouse_release', self.on_canvas_click_release)


    def disconnect_canvas_event_handlers(self):

        self.canvas.vis_disconnect('mouse_press', self.on_canvas_click)
        self.canvas.vis_disconnect('mouse_move', self.on_canvas_move)
        self.canvas.vis_disconnect('mouse_release', self.on_canvas_click_release)

        # we restore the key and mouse control to FlatCAMApp method
        self.app.plotcanvas.vis_connect('mouse_press', self.app.on_mouse_click_over_plot)
        self.app.plotcanvas.vis_connect('mouse_move', self.app.on_mouse_move_over_plot)
        self.app.plotcanvas.vis_connect('mouse_release', self.app.on_mouse_click_release_over_plot)
        self.app.plotcanvas.vis_connect('mouse_double_click', self.app.on_double_click_over_plot)
        self.app.collection.view.clicked.connect(self.app.collection.on_mouse_down)

    def add_shape(self, shape):
        """
        Adds a shape to the shape storage.

        :param shape: Shape to be added.
        :type shape: DrawToolShape
        :return: None
        """

        # List of DrawToolShape?
        if isinstance(shape, list):
            for subshape in shape:
                self.add_shape(subshape)
            return

        assert isinstance(shape, DrawToolShape), \
            "Expected a DrawToolShape, got %s" % type(shape)

        assert shape.geo is not None, \
            "Shape object has empty geometry (None)"

        assert (isinstance(shape.geo, list) and len(shape.geo) > 0) or \
               not isinstance(shape.geo, list), \
            "Shape objects has empty geometry ([])"

        if isinstance(shape, DrawToolUtilityShape):
            self.utility.append(shape)
        else:
            self.storage.insert(shape)  # TODO: Check performance

    def delete_utility_geometry(self):
        # for_deletion = [shape for shape in self.shape_buffer if shape.utility]
        # for_deletion = [shape for shape in self.storage.get_objects() if shape.utility]
        for_deletion = [shape for shape in self.utility]
        for shape in for_deletion:
            self.delete_shape(shape)

        self.tool_shape.clear(update=True)
        self.tool_shape.redraw()

    def cutpath(self):
        selected = self.get_selected()
        tools = selected[1:]
        toolgeo = cascaded_union([shp.geo for shp in tools])

        target = selected[0]
        if type(target.geo) == Polygon:
            for ring in poly2rings(target.geo):
                self.add_shape(DrawToolShape(ring.difference(toolgeo)))
            self.delete_shape(target)
        elif type(target.geo) == LineString or type(target.geo) == LinearRing:
            self.add_shape(DrawToolShape(target.geo.difference(toolgeo)))
            self.delete_shape(target)
        elif type(target.geo) == MultiLineString:
            try:
                for linestring in target.geo:
                    self.add_shape(DrawToolShape(linestring.difference(toolgeo)))
            except:
                self.app.log.warning("Current LinearString does not intersect the target")
            self.delete_shape(target)
        else:
            self.app.log.warning("Not implemented. Object type: %s" % str(type(target.geo)))

        self.replot()

    def toolbar_tool_toggle(self, key):
        self.options[key] = self.sender().isChecked()
        if self.options[key] == True:
            return 1
        else:
            return 0

    def clear(self):
        self.active_tool = None
        # self.shape_buffer = []
        self.selected = []
        self.shapes.clear(update=True)
        self.tool_shape.clear(update=True)

        self.storage = FlatCAMGeoEditor.make_storage()
        self.replot()

    def edit_fcgeometry(self, fcgeometry):
        """
        Imports the geometry from the given FlatCAM Geometry object
        into the editor.

        :param fcgeometry: FlatCAMGeometry
        :return: None
        """
        assert isinstance(fcgeometry, Geometry), \
            "Expected a Geometry, got %s" % type(fcgeometry)

        self.deactivate()
        self.activate()

        # Hide original geometry
        self.fcgeometry = fcgeometry
        fcgeometry.visible = False

        # Set selection tolerance
        DrawToolShape.tolerance = fcgeometry.drawing_tolerance * 10

        self.select_tool("select")

        # Link shapes into editor.
        for shape in fcgeometry.flatten():
            if shape is not None:  # TODO: Make flatten never create a None
                if type(shape) == Polygon:
                    self.add_shape(DrawToolShape(shape.exterior))
                    for inter in shape.interiors:
                        self.add_shape(DrawToolShape(inter))
                else:
                    self.add_shape(DrawToolShape(shape))

        self.replot()


        # start with GRID toolbar activated
        if self.app.ui.grid_snap_btn.isChecked() == False:
            self.app.ui.grid_snap_btn.trigger()

    def on_buffer_tool(self):
        buff_tool = BufferSelectionTool(self.app, self)
        buff_tool.run()

    def on_paint_tool(self):
        paint_tool = PaintOptionsTool(self.app, self)
        paint_tool.run()

    def on_transform_tool(self):
        transform_tool = TransformEditorTool(self.app, self)
        transform_tool.run()

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
                if not isinstance(self.active_tool, FCSelect):
                    self.app.inform.emit(self.active_tool.start_msg)
            else:
                self.app.log.debug("%s is NOT checked." % tool)
                for t in self.tools:
                    self.tools[t]["button"].setChecked(False)
                self.active_tool = None

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
            self.app.app_cursor.enabled = True
        else:
            self.app.app_cursor.enabled = False

    def on_canvas_click(self, event):
        """
        event.x and .y have canvas coordinates
        event.xdaya and .ydata have plot coordinates

        :param event: Event object dispatched by Matplotlib
        :return: None
        """

        if event.button is 1:
            self.app.ui.rel_position_label.setText("<b>Dx</b>: %.4f&nbsp;&nbsp;  <b>Dy</b>: "
                                                   "%.4f&nbsp;&nbsp;&nbsp;&nbsp;" % (0, 0))
            self.pos = self.canvas.vispy_canvas.translate_coords(event.pos)

            ### Snap coordinates
            x, y = self.snap(self.pos[0], self.pos[1])

            self.pos = (x, y)

            modifiers = QtWidgets.QApplication.keyboardModifiers()
            # If the SHIFT key is pressed when LMB is clicked then the coordinates are copied to clipboard
            if modifiers == QtCore.Qt.ShiftModifier:
                self.app.clipboard.setText(
                    self.app.defaults["global_point_clipboard_format"] % (self.pos[0], self.pos[1]))
                return

            # Selection with left mouse button
            if self.active_tool is not None and event.button is 1:
                # Dispatch event to active_tool
                # msg = self.active_tool.click(self.snap(event.xdata, event.ydata))
                msg = self.active_tool.click(self.snap(self.pos[0], self.pos[1]))

                # If it is a shape generating tool
                if isinstance(self.active_tool, FCShapeTool) and self.active_tool.complete:
                    self.on_shape_complete()

                    # MS: always return to the Select Tool if modifier key is not pressed
                    # else return to the current tool
                    key_modifier = QtWidgets.QApplication.keyboardModifiers()
                    if self.app.defaults["global_mselect_key"] == 'Control':
                        modifier_to_use = Qt.ControlModifier
                    else:
                        modifier_to_use = Qt.ShiftModifier

                    # if modifier key is pressed then we add to the selected list the current shape but if
                    # it's already in the selected list, we removed it. Therefore first click selects, second deselects.
                    if key_modifier == modifier_to_use:
                        self.select_tool(self.active_tool.name)
                    else:
                        self.select_tool("select")
                        return

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

        pos = self.canvas.vispy_canvas.translate_coords(event.pos)
        event.xdata, event.ydata = pos[0], pos[1]

        self.x = event.xdata
        self.y = event.ydata

        # Prevent updates on pan
        # if len(event.buttons) > 0:
        #     return

        # if the RMB is clicked and mouse is moving over plot then 'panning_action' is True
        if event.button == 2:
            self.app.panning_action = True
            return
        else:
            self.app.panning_action = False

        try:
            x = float(event.xdata)
            y = float(event.ydata)
        except TypeError:
            return

        if self.active_tool is None:
            return

        ### Snap coordinates
        x, y = self.snap(x, y)

        self.snap_x = x
        self.snap_y = y

        # update the position label in the infobar since the APP mouse event handlers are disconnected
        self.app.ui.position_label.setText("&nbsp;&nbsp;&nbsp;&nbsp;<b>X</b>: %.4f&nbsp;&nbsp;   "
                                       "<b>Y</b>: %.4f" % (x, y))

        if self.pos is None:
            self.pos = (0, 0)
        dx = x - self.pos[0]
        dy = y - self.pos[1]

        # update the reference position label in the infobar since the APP mouse event handlers are disconnected
        self.app.ui.rel_position_label.setText("<b>Dx</b>: %.4f&nbsp;&nbsp;  <b>Dy</b>: "
                                           "%.4f&nbsp;&nbsp;&nbsp;&nbsp;" % (dx, dy))

        ### Utility geometry (animated)
        geo = self.active_tool.utility_geometry(data=(x, y))

        if isinstance(geo, DrawToolShape) and geo.geo is not None:
            # Remove any previous utility shape
            self.tool_shape.clear(update=True)
            self.draw_utility_geometry(geo=geo)

        ### Selection area on canvas section ###
        dx = pos[0] - self.pos[0]
        if event.is_dragging == 1 and event.button == 1:
            self.app.delete_selection_shape()
            if dx < 0:
                self.app.draw_moving_selection_shape((self.pos[0], self.pos[1]), (x,y),
                     color=self.app.defaults["global_alt_sel_line"],
                     face_color=self.app.defaults['global_alt_sel_fill'])
                self.app.selection_type = False
            else:
                self.app.draw_moving_selection_shape((self.pos[0], self.pos[1]), (x,y))
                self.app.selection_type = True
        else:
            self.app.selection_type = None

        # Update cursor
        self.app.app_cursor.set_data(np.asarray([(x, y)]), symbol='++', edge_color='black', size=20)

    def on_canvas_click_release(self, event):
        pos_canvas = self.canvas.vispy_canvas.translate_coords(event.pos)

        if self.app.grid_status():
            pos = self.snap(pos_canvas[0], pos_canvas[1])
        else:
            pos = (pos_canvas[0], pos_canvas[1])

        # if the released mouse button was RMB then test if it was a panning motion or not, if not it was a context
        # canvas menu
        try:
            if event.button == 2:  # right click
                if self.app.panning_action is True:
                    self.app.panning_action = False
                else:
                    if self.in_action is False:
                        self.app.cursor = QtGui.QCursor()
                        self.app.ui.popMenu.popup(self.app.cursor.pos())
                    else:
                        # if right click on canvas and the active tool need to be finished (like Path or Polygon)
                        # right mouse click will finish the action
                        if isinstance(self.active_tool, FCShapeTool):
                            self.active_tool.click(self.snap(self.x, self.y))
                            self.active_tool.make()
                            if self.active_tool.complete:
                                self.on_shape_complete()
                                self.app.inform.emit(_("[success]Done."))

                                # MS: always return to the Select Tool if modifier key is not pressed
                                # else return to the current tool
                                key_modifier = QtWidgets.QApplication.keyboardModifiers()
                                if self.app.defaults["global_mselect_key"] == 'Control':
                                    modifier_to_use = Qt.ControlModifier
                                else:
                                    modifier_to_use = Qt.ShiftModifier

                                if key_modifier == modifier_to_use:
                                    self.select_tool(self.active_tool.name)
                                else:
                                    self.select_tool("select")

        except Exception as e:
            log.warning("Error: %s" % str(e))
            return

        # if the released mouse button was LMB then test if we had a right-to-left selection or a left-to-right
        # selection and then select a type of selection ("enclosing" or "touching")
        try:
            if event.button == 1:  # left click
                if self.app.selection_type is not None:
                    self.draw_selection_area_handler(self.pos, pos, self.app.selection_type)
                    self.app.selection_type = None
                elif isinstance(self.active_tool, FCSelect):
                    # Dispatch event to active_tool
                    # msg = self.active_tool.click(self.snap(event.xdata, event.ydata))
                    msg = self.active_tool.click_release((self.pos[0], self.pos[1]))
                    # self.app.inform.emit(msg)
                    self.replot()
        except Exception as e:
            log.warning("Error: %s" % str(e))
            return

    def draw_selection_area_handler(self, start_pos, end_pos, sel_type):
        """

        :param start_pos: mouse position when the selection LMB click was done
        :param end_pos: mouse position when the left mouse button is released
        :param sel_type: if True it's a left to right selection (enclosure), if False it's a 'touch' selection
        :type Bool
        :return:
        """
        poly_selection = Polygon([start_pos, (end_pos[0], start_pos[1]), end_pos, (start_pos[0], end_pos[1])])

        self.app.delete_selection_shape()
        for obj in self.storage.get_objects():
            if (sel_type is True and poly_selection.contains(obj.geo)) or \
                    (sel_type is False and poly_selection.intersects(obj.geo)):
                    if self.key == self.app.defaults["global_mselect_key"]:
                        if obj in self.selected:
                            self.selected.remove(obj)
                        else:
                            # add the object to the selected shapes
                            self.selected.append(obj)
                    else:
                        if obj not in self.selected:
                            self.selected.append(obj)
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

    def delete_shape(self, shape):

        if shape in self.utility:
            self.utility.remove(shape)
            return

        self.storage.remove(shape)
        if shape in self.selected:
            self.selected.remove(shape)  # TODO: Check performance

    def on_move(self):
        self.app.ui.geo_move_btn.setChecked(True)
        self.on_tool_select('move')

    def on_move_click(self):
        if not self.selected:
            self.app.inform.emit(_("[WARNING_NOTCL] Move cancelled. No shape selected."))
            return
        self.on_move()
        self.active_tool.set_origin(self.snap(self.x, self.y))

    def on_copy_click(self):
        if not self.selected:
            self.app.inform.emit(_("[WARNING_NOTCL] Copy cancelled. No shape selected."))
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

    def plot_shape(self, geometry=None, color='black', linewidth=1):
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

        ## Non-iterable
        except TypeError:

            ## DrawToolShape
            if isinstance(geometry, DrawToolShape):
                plot_elements += self.plot_shape(geometry=geometry.geo, color=color, linewidth=linewidth)

            ## Polygon: Descend into exterior and each interior.
            if type(geometry) == Polygon:
                plot_elements += self.plot_shape(geometry=geometry.exterior, color=color, linewidth=linewidth)
                plot_elements += self.plot_shape(geometry=geometry.interiors, color=color, linewidth=linewidth)

            if type(geometry) == LineString or type(geometry) == LinearRing:
                plot_elements.append(self.shapes.add(shape=geometry, color=color, layer=0,
                                                     tolerance=self.fcgeometry.drawing_tolerance))

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
                self.plot_shape(geometry=shape.geo, color=self.app.defaults['global_sel_draw_color'], linewidth=2)
                continue

            self.plot_shape(geometry=shape.geo, color=self.app.defaults['global_draw_color'])

        for shape in self.utility:
            self.plot_shape(geometry=shape.geo, linewidth=1)
            continue

        self.shapes.redraw()

    def replot(self):
        self.plot_all()

    def on_shape_complete(self):
        self.app.log.debug("on_shape_complete()")

        # Add shape
        self.add_shape(self.active_tool.geometry)

        # Remove any utility shapes
        self.delete_utility_geometry()
        self.tool_shape.clear(update=True)

        # Replot and reset tool.
        self.replot()
        # self.active_tool = type(self.active_tool)(self)

    @staticmethod
    def make_storage():

        ## Shape storage.
        storage = FlatCAMRTreeStorage()
        storage.get_points = DrawToolShape.get_pts

        return storage

    def select_tool(self, toolname):
        """
        Selects a drawing tool. Impacts the object and GUI.

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
        snap_distance = Inf

        ### Object (corner?) snap
        ### No need for the objects, just the coordinates
        ### in the index.
        if self.options["corner_snap"]:
            try:
                nearest_pt, shape = self.storage.nearest((x, y))

                nearest_pt_distance = distance((x, y), nearest_pt)
                if nearest_pt_distance <= float(self.options["global_snap_max"]):
                    snap_distance = nearest_pt_distance
                    snap_x, snap_y = nearest_pt
            except (StopIteration, AssertionError):
                pass

        ### Grid snap
        if self.options["grid_snap"]:
            if self.options["global_gridx"] != 0:
                snap_x_ = round(x / self.options["global_gridx"]) * self.options['global_gridx']
            else:
                snap_x_ = x

            # If the Grid_gap_linked on Grid Toolbar is checked then the snap distance on GridY entry will be ignored
            # and it will use the snap distance from GridX entry
            if self.app.ui.grid_gap_link_cb.isChecked():
                if self.options["global_gridx"] != 0:
                    snap_y_ = round(y / self.options["global_gridx"]) * self.options['global_gridx']
                else:
                    snap_y_ = y
            else:
                if self.options["global_gridy"] != 0:
                    snap_y_ = round(y / self.options["global_gridy"]) * self.options['global_gridy']
                else:
                    snap_y_ = y
            nearest_grid_distance = distance((x, y), (snap_x_, snap_y_))
            if nearest_grid_distance < snap_distance:
                snap_x, snap_y = (snap_x_, snap_y_)

        return snap_x, snap_y

    def update_fcgeometry(self, fcgeometry):
        """
        Transfers the geometry tool shape buffer to the selected geometry
        object. The geometry already in the object are removed.

        :param fcgeometry: FlatCAMGeometry
        :return: None
        """
        fcgeometry.solid_geometry = []
        # for shape in self.shape_buffer:
        for shape in self.storage.get_objects():
            fcgeometry.solid_geometry.append(shape.geo)

        # re-enable all the widgets in the Selected Tab that were disabled after entering in Edit Geometry Mode
        sel_tab_widget_list = self.app.ui.selected_tab.findChildren(QtWidgets.QWidget)
        for w in sel_tab_widget_list:
            w.setEnabled(True)

    def update_options(self, obj):
        if self.paint_tooldia:
            obj.options['cnctooldia'] = self.paint_tooldia
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

        results = cascaded_union([t.geo for t in self.get_selected()])

        # Delete originals.
        for_deletion = [s for s in self.get_selected()]
        for shape in for_deletion:
            self.delete_shape(shape)

        # Selected geometry is now gone!
        self.selected = []

        self.add_shape(DrawToolShape(results))

        self.replot()

    def intersection(self):
        """
        Makes intersectino of selected polygons. Original polygons are deleted.

        :return: None
        """

        shapes = self.get_selected()

        try:
            results = shapes[0].geo
        except Exception as e:
            log.debug("FlatCAMGeoEditor.intersection() --> %s" % str(e))
            self.app.inform.emit(_("[WARNING_NOTCL]A selection of at least 2 geo items is required to do Intersection."))
            self.select_tool('select')
            return

        for shape in shapes[1:]:
            results = results.intersection(shape.geo)

        # Delete originals.
        for_deletion = [s for s in self.get_selected()]
        for shape in for_deletion:
            self.delete_shape(shape)

        # Selected geometry is now gone!
        self.selected = []

        self.add_shape(DrawToolShape(results))

        self.replot()

    def subtract(self):
        selected = self.get_selected()
        try:
            tools = selected[1:]
            toolgeo = cascaded_union([shp.geo for shp in tools])
            result = selected[0].geo.difference(toolgeo)

            self.delete_shape(selected[0])
            self.add_shape(DrawToolShape(result))

            self.replot()
        except Exception as e:
            log.debug(str(e))

    def buffer(self, buf_distance, join_style):
        selected = self.get_selected()

        if buf_distance < 0:
            self.app.inform.emit(
               _( "[ERROR_NOTCL]Negative buffer value is not accepted. Use Buffer interior to generate an 'inside' shape"))

            # deselect everything
            self.selected = []
            self.replot()
            return

        if len(selected) == 0:
            self.app.inform.emit(_("[WARNING_NOTCL] Nothing selected for buffering."))
            return

        if not isinstance(buf_distance, float):
            self.app.inform.emit(_("[WARNING_NOTCL] Invalid distance for buffering."))

            # deselect everything
            self.selected = []
            self.replot()
            return

        pre_buffer = cascaded_union([t.geo for t in selected])
        results = pre_buffer.buffer(buf_distance - 1e-10, resolution=32, join_style=join_style)
        if results.is_empty:
            self.app.inform.emit(_("[ERROR_NOTCL]Failed, the result is empty. Choose a different buffer value."))
            # deselect everything
            self.selected = []
            self.replot()
            return
        self.add_shape(DrawToolShape(results))

        self.replot()
        self.app.inform.emit(_("[success]Full buffer geometry created."))

    def buffer_int(self, buf_distance, join_style):
        selected = self.get_selected()

        if buf_distance < 0:
            self.app.inform.emit(
                _("[ERROR_NOTCL]Negative buffer value is not accepted. "
                    "Use Buffer interior to generate an 'inside' shape")
            )
            # deselect everything
            self.selected = []
            self.replot()
            return

        if len(selected) == 0:
            self.app.inform.emit(_("[WARNING_NOTCL] Nothing selected for buffering."))
            return

        if not isinstance(buf_distance, float):
            self.app.inform.emit(_("[WARNING_NOTCL] Invalid distance for buffering."))
            # deselect everything
            self.selected = []
            self.replot()
            return

        pre_buffer = cascaded_union([t.geo for t in selected])
        results = pre_buffer.buffer(-buf_distance + 1e-10, resolution=32, join_style=join_style)
        if results.is_empty:
            self.app.inform.emit(_("[ERROR_NOTCL]Failed, the result is empty. Choose a smaller buffer value."))
            # deselect everything
            self.selected = []
            self.replot()
            return
        if type(results) == MultiPolygon:
            for poly in results:
                self.add_shape(DrawToolShape(poly.exterior))
        else:
            self.add_shape(DrawToolShape(results.exterior))

        self.replot()
        self.app.inform.emit(_("[success]Exterior buffer geometry created."))
        # selected = self.get_selected()
        #
        # if len(selected) == 0:
        #     self.app.inform.emit("[WARNING] Nothing selected for buffering.")
        #     return
        #
        # if not isinstance(buf_distance, float):
        #     self.app.inform.emit("[WARNING] Invalid distance for buffering.")
        #     return
        #
        # pre_buffer = cascaded_union([t.geo for t in selected])
        # results = pre_buffer.buffer(buf_distance)
        # if results.is_empty:
        #     self.app.inform.emit("Failed. Choose a smaller buffer value.")
        #     return
        #
        # int_geo = []
        # if type(results) == MultiPolygon:
        #     for poly in results:
        #         for g in poly.interiors:
        #             int_geo.append(g)
        #         res = cascaded_union(int_geo)
        #         self.add_shape(DrawToolShape(res))
        # else:
        #     print(results.interiors)
        #     for g in results.interiors:
        #         int_geo.append(g)
        #     res = cascaded_union(int_geo)
        #     self.add_shape(DrawToolShape(res))
        #
        # self.replot()
        # self.app.inform.emit("Interior buffer geometry created.")

    def buffer_ext(self, buf_distance, join_style):
        selected = self.get_selected()

        if buf_distance < 0:
            self.app.inform.emit(_("[ERROR_NOTCL]Negative buffer value is not accepted. "
                                 "Use Buffer interior to generate an 'inside' shape"))
            # deselect everything
            self.selected = []
            self.replot()
            return

        if len(selected) == 0:
            self.app.inform.emit(_("[WARNING_NOTCL] Nothing selected for buffering."))
            return

        if not isinstance(buf_distance, float):
            self.app.inform.emit(_("[WARNING_NOTCL] Invalid distance for buffering."))
            # deselect everything
            self.selected = []
            self.replot()
            return

        pre_buffer = cascaded_union([t.geo for t in selected])
        results = pre_buffer.buffer(buf_distance - 1e-10, resolution=32, join_style=join_style)
        if results.is_empty:
            self.app.inform.emit(_("[ERROR_NOTCL]Failed, the result is empty. Choose a different buffer value."))
            # deselect everything
            self.selected = []
            self.replot()
            return
        if type(results) == MultiPolygon:
            for poly in results:
                self.add_shape(DrawToolShape(poly.exterior))
        else:
            self.add_shape(DrawToolShape(results.exterior))

        self.replot()
        self.app.inform.emit(_("[success]Exterior buffer geometry created."))

    # def paint(self, tooldia, overlap, margin, method):
    #     selected = self.get_selected()
    #
    #     if len(selected) == 0:
    #         self.app.inform.emit("[WARNING] Nothing selected for painting.")
    #         return
    #
    #     for param in [tooldia, overlap, margin]:
    #         if not isinstance(param, float):
    #             param_name = [k for k, v in locals().items() if v is param][0]
    #             self.app.inform.emit("[WARNING] Invalid value for {}".format(param))
    #
    #     # Todo: Check for valid method.
    #
    #     # Todo: This is the 3rd implementation on painting polys... try to consolidate
    #
    #     results = []
    #
    #     def recurse(geo):
    #         try:
    #             for subg in geo:
    #                 for subsubg in recurse(subg):
    #                     yield subsubg
    #         except TypeError:
    #             if isinstance(geo, LinearRing):
    #                 yield geo
    #
    #         raise StopIteration
    #
    #     for geo in selected:
    #         print(type(geo.geo))
    #
    #         local_results = []
    #         for poly in recurse(geo.geo):
    #             if method == "seed":
    #                 # Type(cp) == FlatCAMRTreeStorage | None
    #                 cp = Geometry.clear_polygon2(poly.buffer(-margin),
    #                                              tooldia, overlap=overlap)
    #
    #             else:
    #                 # Type(cp) == FlatCAMRTreeStorage | None
    #                 cp = Geometry.clear_polygon(poly.buffer(-margin),
    #                                             tooldia, overlap=overlap)
    #
    #             if cp is not None:
    #                 local_results += list(cp.get_objects())
    #
    #             results.append(cascaded_union(local_results))
    #
    #     # This is a dirty patch:
    #     for r in results:
    #         self.add_shape(DrawToolShape(r))
    #
    #     self.replot()

    def paint(self, tooldia, overlap, margin, connect, contour, method):

        self.paint_tooldia = tooldia

        selected = self.get_selected()

        if len(selected) == 0:
            self.app.inform.emit(_("[WARNING_NOTCL]Nothing selected for painting."))
            return

        for param in [tooldia, overlap, margin]:
            if not isinstance(param, float):
                param_name = [k for k, v in locals().items() if v is param][0]
                self.app.inform.emit(_("[WARNING] Invalid value for {}").format(param))

        results = []

        if overlap >= 1:
            self.app.inform.emit(
                _("[ERROR_NOTCL] Could not do Paint. Overlap value has to be less than 1.00 (100%)."))
            return

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

            ## If iterable, expand recursively.
            try:
                for geo in geometry:
                    if geo is not None:
                        recurse(geometry=geo, reset=False)

            ## Not iterable, do the actual indexing and add.
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

                    if method == "seed":
                        cp = Geometry.clear_polygon2(poly_buf,
                                                 tooldia, self.app.defaults["geometry_circle_steps"],
                                                 overlap=overlap, contour=contour, connect=connect)
                    elif method == "lines":
                        cp = Geometry.clear_polygon3(poly_buf,
                                                 tooldia, self.app.defaults["geometry_circle_steps"],
                                                 overlap=overlap, contour=contour, connect=connect)

                    else:
                        cp = Geometry.clear_polygon(poly_buf,
                                                tooldia, self.app.defaults["geometry_circle_steps"],
                                                overlap=overlap, contour=contour, connect=connect)

                    if cp is not None:
                        local_results += list(cp.get_objects())
                except Exception as e:
                    log.debug("Could not Paint the polygons. %s" % str(e))
                    self.app.inform.emit(
                        _("[ERROR] Could not do Paint. Try a different combination of parameters. "
                        "Or a different method of Paint\n%s") % str(e))
                    return

                # add the result to the results list
                results.append(cascaded_union(local_results))

        # This is a dirty patch:
        for r in results:
            self.add_shape(DrawToolShape(r))
        self.app.inform.emit(
            _("[success] Paint done."))
        self.replot()


class FlatCAMExcEditor(QtCore.QObject):

    draw_shape_idx = -1

    def __init__(self, app):
        assert isinstance(app, FlatCAMApp.App), \
            "Expected the app to be a FlatCAMApp.App, got %s" % type(app)

        super(FlatCAMExcEditor, self).__init__()

        self.app = app
        self.canvas = self.app.plotcanvas

        self.exc_edit_widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        self.exc_edit_widget.setLayout(layout)

        ## Page Title box (spacing between children)
        self.title_box = QtWidgets.QHBoxLayout()
        layout.addLayout(self.title_box)

        ## Page Title icon
        pixmap = QtGui.QPixmap('share/flatcam_icon32.png')
        self.icon = QtWidgets.QLabel()
        self.icon.setPixmap(pixmap)
        self.title_box.addWidget(self.icon, stretch=0)

        ## Title label
        self.title_label = QtWidgets.QLabel("<font size=5><b>%s</b></font>" % _('Excellon Editor'))
        self.title_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.title_box.addWidget(self.title_label, stretch=1)

        ## Object name
        self.name_box = QtWidgets.QHBoxLayout()
        layout.addLayout(self.name_box)
        name_label = QtWidgets.QLabel(_("Name:"))
        self.name_box.addWidget(name_label)
        self.name_entry = FCEntry()
        self.name_box.addWidget(self.name_entry)

        ## Box box for custom widgets
        # This gets populated in offspring implementations.
        self.custom_box = QtWidgets.QVBoxLayout()
        layout.addLayout(self.custom_box)

        # add a frame and inside add a vertical box layout. Inside this vbox layout I add all the Drills widgets
        # this way I can hide/show the frame
        self.drills_frame = QtWidgets.QFrame()
        self.drills_frame.setContentsMargins(0, 0, 0, 0)
        self.custom_box.addWidget(self.drills_frame)
        self.tools_box = QtWidgets.QVBoxLayout()
        self.tools_box.setContentsMargins(0, 0, 0, 0)
        self.drills_frame.setLayout(self.tools_box)

        #### Tools Drills ####
        self.tools_table_label = QtWidgets.QLabel("<b>%s</b>" % _('Tools Table'))
        self.tools_table_label.setToolTip(
           _( "Tools in this Excellon object\n"
            "when are used for drilling.")
        )
        self.tools_box.addWidget(self.tools_table_label)

        self.tools_table_exc = FCTable()
        self.tools_box.addWidget(self.tools_table_exc)

        self.tools_table_exc.setColumnCount(4)
        self.tools_table_exc.setHorizontalHeaderLabels(['#', _('Diameter'), 'D', 'S'])
        self.tools_table_exc.setSortingEnabled(False)
        self.tools_table_exc.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        self.empty_label = QtWidgets.QLabel('')
        self.tools_box.addWidget(self.empty_label)

        #### Add a new Tool ####
        self.addtool_label = QtWidgets.QLabel('<b>%s</b>' % _('Add/Delete Tool'))
        self.addtool_label.setToolTip(
            _("Add/Delete a tool to the tool list\n"
            "for this Excellon object.")
        )
        self.tools_box.addWidget(self.addtool_label)

        grid1 = QtWidgets.QGridLayout()
        self.tools_box.addLayout(grid1)

        addtool_entry_lbl = QtWidgets.QLabel(_('Tool Dia:'))
        addtool_entry_lbl.setToolTip(
        _("Diameter for the new tool")
        )
        grid1.addWidget(addtool_entry_lbl, 0, 0)

        hlay = QtWidgets.QHBoxLayout()
        self.addtool_entry = FCEntry()
        self.addtool_entry.setValidator(QtGui.QDoubleValidator(0.0001, 99.9999, 4))
        hlay.addWidget(self.addtool_entry)

        self.addtool_btn = QtWidgets.QPushButton(_('Add Tool'))
        self.addtool_btn.setToolTip(
           _( "Add a new tool to the tool list\n"
            "with the diameter specified above.")
        )
        self.addtool_btn.setFixedWidth(80)
        hlay.addWidget(self.addtool_btn)
        grid1.addLayout(hlay, 0, 1)

        grid2 = QtWidgets.QGridLayout()
        self.tools_box.addLayout(grid2)

        self.deltool_btn = QtWidgets.QPushButton(_('Delete Tool'))
        self.deltool_btn.setToolTip(
           _( "Delete a tool in the tool list\n"
            "by selecting a row in the tool table.")
        )
        grid2.addWidget(self.deltool_btn, 0, 1)

        # add a frame and inside add a vertical box layout. Inside this vbox layout I add all the Drills widgets
        # this way I can hide/show the frame
        self.resize_frame = QtWidgets.QFrame()
        self.resize_frame.setContentsMargins(0, 0, 0, 0)
        self.tools_box.addWidget(self.resize_frame)
        self.resize_box = QtWidgets.QVBoxLayout()
        self.resize_box.setContentsMargins(0, 0, 0, 0)
        self.resize_frame.setLayout(self.resize_box)

        #### Resize a  drill ####
        self.emptyresize_label = QtWidgets.QLabel('')
        self.resize_box.addWidget(self.emptyresize_label)

        self.drillresize_label = QtWidgets.QLabel('<b>%s</b>' % _("Resize Drill(s)"))
        self.drillresize_label.setToolTip(
            _("Resize a drill or a selection of drills.")
        )
        self.resize_box.addWidget(self.drillresize_label)

        grid3 = QtWidgets.QGridLayout()
        self.resize_box.addLayout(grid3)

        res_entry_lbl = QtWidgets.QLabel(_('Resize Dia:'))
        res_entry_lbl.setToolTip(
           _( "Diameter to resize to.")
        )
        grid3.addWidget(addtool_entry_lbl, 0, 0)

        hlay2 = QtWidgets.QHBoxLayout()
        self.resdrill_entry = LengthEntry()
        hlay2.addWidget(self.resdrill_entry)

        self.resize_btn = QtWidgets.QPushButton(_('Resize'))
        self.resize_btn.setToolTip(
            _("Resize drill(s)")
        )
        self.resize_btn.setFixedWidth(80)
        hlay2.addWidget(self.resize_btn)
        grid3.addLayout(hlay2, 0, 1)

        self.resize_frame.hide()

        # add a frame and inside add a vertical box layout. Inside this vbox layout I add
        # all the add drill array  widgets
        # this way I can hide/show the frame
        self.array_frame = QtWidgets.QFrame()
        self.array_frame.setContentsMargins(0, 0, 0, 0)
        self.tools_box.addWidget(self.array_frame)
        self.array_box = QtWidgets.QVBoxLayout()
        self.array_box.setContentsMargins(0, 0, 0, 0)
        self.array_frame.setLayout(self.array_box)

        #### Add DRILL Array ####
        self.emptyarray_label = QtWidgets.QLabel('')
        self.array_box.addWidget(self.emptyarray_label)

        self.drillarray_label = QtWidgets.QLabel('<b>%s</b>' % _("Add Drill Array"))
        self.drillarray_label.setToolTip(
            _("Add an array of drills (linear or circular array)")
        )
        self.array_box.addWidget(self.drillarray_label)

        self.array_type_combo = FCComboBox()
        self.array_type_combo.setToolTip(
           _( "Select the type of drills array to create.\n"
            "It can be Linear X(Y) or Circular")
        )
        self.array_type_combo.addItem(_("Linear"))
        self.array_type_combo.addItem(_("Circular"))

        self.array_box.addWidget(self.array_type_combo)

        self.array_form = QtWidgets.QFormLayout()
        self.array_box.addLayout(self.array_form)

        self.drill_array_size_label = QtWidgets.QLabel(_('Nr of drills:'))
        self.drill_array_size_label.setToolTip(
            _("Specify how many drills to be in the array.")
        )
        self.drill_array_size_label.setFixedWidth(100)

        self.drill_array_size_entry = LengthEntry()
        self.array_form.addRow(self.drill_array_size_label, self.drill_array_size_entry)

        self.array_linear_frame = QtWidgets.QFrame()
        self.array_linear_frame.setContentsMargins(0, 0, 0, 0)
        self.array_box.addWidget(self.array_linear_frame)
        self.linear_box = QtWidgets.QVBoxLayout()
        self.linear_box.setContentsMargins(0, 0, 0, 0)
        self.array_linear_frame.setLayout(self.linear_box)

        self.linear_form = QtWidgets.QFormLayout()
        self.linear_box.addLayout(self.linear_form)

        self.drill_axis_label = QtWidgets.QLabel(_('Direction:'))
        self.drill_axis_label.setToolTip(
            _("Direction on which the linear array is oriented:\n"
            "- 'X' - horizontal axis \n"
            "- 'Y' - vertical axis or \n"
            "- 'Angle' - a custom angle for the array inclination")
        )
        self.drill_axis_label.setFixedWidth(100)

        self.drill_axis_radio = RadioSet([{'label': 'X', 'value': 'X'},
                                          {'label': 'Y', 'value': 'Y'},
                                          {'label': _('Angle'), 'value': 'A'}])
        self.drill_axis_radio.set_value('X')
        self.linear_form.addRow(self.drill_axis_label, self.drill_axis_radio)

        self.drill_pitch_label = QtWidgets.QLabel(_('Pitch:'))
        self.drill_pitch_label.setToolTip(
            _("Pitch = Distance between elements of the array.")
        )
        self.drill_pitch_label.setFixedWidth(100)

        self.drill_pitch_entry = LengthEntry()
        self.linear_form.addRow(self.drill_pitch_label, self.drill_pitch_entry)

        self.linear_angle_label = QtWidgets.QLabel(_('Angle:'))
        self.linear_angle_label.setToolTip(
           _( "Angle at which the linear array is placed.\n"
            "The precision is of max 2 decimals.\n"
            "Min value is: -359.99 degrees.\n"
            "Max value is:  360.00 degrees.")
        )
        self.linear_angle_label.setFixedWidth(100)

        self.linear_angle_spinner = FCDoubleSpinner()
        self.linear_angle_spinner.set_precision(2)
        self.linear_angle_spinner.setRange(-359.99, 360.00)
        self.linear_form.addRow(self.linear_angle_label, self.linear_angle_spinner)

        self.array_circular_frame = QtWidgets.QFrame()
        self.array_circular_frame.setContentsMargins(0, 0, 0, 0)
        self.array_box.addWidget(self.array_circular_frame)
        self.circular_box = QtWidgets.QVBoxLayout()
        self.circular_box.setContentsMargins(0, 0, 0, 0)
        self.array_circular_frame.setLayout(self.circular_box)

        self.drill_direction_label = QtWidgets.QLabel(_('Direction:'))
        self.drill_direction_label.setToolTip(
           _( "Direction for circular array."
            "Can be CW = clockwise or CCW = counter clockwise.")
        )
        self.drill_direction_label.setFixedWidth(100)

        self.circular_form = QtWidgets.QFormLayout()
        self.circular_box.addLayout(self.circular_form)

        self.drill_direction_radio = RadioSet([{'label': 'CW', 'value': 'CW'},
                                               {'label': 'CCW.', 'value': 'CCW'}])
        self.drill_direction_radio.set_value('CW')
        self.circular_form.addRow(self.drill_direction_label, self.drill_direction_radio)

        self.drill_angle_label = QtWidgets.QLabel(_('Angle:'))
        self.drill_angle_label.setToolTip(
            _("Angle at which each element in circular array is placed.")
        )
        self.drill_angle_label.setFixedWidth(100)

        self.drill_angle_entry = LengthEntry()
        self.circular_form.addRow(self.drill_angle_label, self.drill_angle_entry)

        self.array_circular_frame.hide()

        self.linear_angle_spinner.hide()
        self.linear_angle_label.hide()

        self.array_frame.hide()
        self.tools_box.addStretch()

        ## Toolbar events and properties
        self.tools_exc = {
            "select": {"button": self.app.ui.select_drill_btn,
                       "constructor": FCDrillSelect},
            "drill_add": {"button": self.app.ui.add_drill_btn,
                    "constructor": FCDrillAdd},
            "drill_array": {"button": self.app.ui.add_drill_array_btn,
                          "constructor": FCDrillArray},
            "drill_resize": {"button": self.app.ui.resize_drill_btn,
                       "constructor": FCDrillResize},
            "drill_copy": {"button": self.app.ui.copy_drill_btn,
                     "constructor": FCDrillCopy},
            "drill_move": {"button": self.app.ui.move_drill_btn,
                     "constructor": FCDrillMove},
        }

        ### Data
        self.active_tool = None

        self.storage_dict = {}
        self.current_storage = []

        # build the data from the Excellon point into a dictionary
        #  {tool_dia: [geometry_in_points]}
        self.points_edit = {}
        self.sorted_diameters =[]

        self.new_drills = []
        self.new_tools = {}
        self.new_slots = {}
        self.new_tool_offset = {}

        # dictionary to store the tool_row and diameters in Tool_table
        # it will be updated everytime self.build_ui() is called
        self.olddia_newdia = {}

        self.tool2tooldia = {}

        # this will store the value for the last selected tool, for use after clicking on canvas when the selection
        # is cleared but as a side effect also the selected tool is cleared
        self.last_tool_selected = None
        self.utility = []

        # this will flag if the Editor "tools" are launched from key shortcuts (True) or from menu toolbar (False)
        self.launched_from_shortcuts = False

        # this var will store the state of the toolbar before starting the editor
        self.toolbar_old_state = False

        self.app.ui.delete_drill_btn.triggered.connect(self.on_delete_btn)
        self.name_entry.returnPressed.connect(self.on_name_activate)
        self.addtool_btn.clicked.connect(self.on_tool_add)
        # self.addtool_entry.editingFinished.connect(self.on_tool_add)
        self.deltool_btn.clicked.connect(self.on_tool_delete)
        self.tools_table_exc.selectionModel().currentChanged.connect(self.on_row_selected)
        self.array_type_combo.currentIndexChanged.connect(self.on_array_type_combo)

        self.drill_axis_radio.activated_custom.connect(self.on_linear_angle_radio)

        self.app.ui.exc_add_array_drill_menuitem.triggered.connect(self.exc_add_drill_array)
        self.app.ui.exc_add_drill_menuitem.triggered.connect(self.exc_add_drill)

        self.app.ui.exc_resize_drill_menuitem.triggered.connect(self.exc_resize_drills)
        self.app.ui.exc_copy_drill_menuitem.triggered.connect(self.exc_copy_drills)
        self.app.ui.exc_delete_drill_menuitem.triggered.connect(self.on_delete_btn)

        self.app.ui.exc_move_drill_menuitem.triggered.connect(self.exc_move_drills)


        # Init GUI
        self.drill_array_size_entry.set_value(5)
        self.drill_pitch_entry.set_value(2.54)
        self.drill_angle_entry.set_value(12)
        self.drill_direction_radio.set_value('CW')
        self.drill_axis_radio.set_value('X')
        self.exc_obj = None

        # VisPy Visuals
        self.shapes = self.app.plotcanvas.new_shape_collection(layers=1)
        self.tool_shape = self.app.plotcanvas.new_shape_collection(layers=1)
        self.app.pool_recreated.connect(self.pool_recreated)

        # Remove from scene
        self.shapes.enabled = False
        self.tool_shape.enabled = False

        ## List of selected shapes.
        self.selected = []

        self.move_timer = QtCore.QTimer()
        self.move_timer.setSingleShot(True)

        ## Current application units in Upper Case
        self.units = self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().upper()

        self.key = None  # Currently pressed key
        self.modifiers = None
        self.x = None  # Current mouse cursor pos
        self.y = None
        # Current snapped mouse pos
        self.snap_x = None
        self.snap_y = None
        self.pos = None

        def make_callback(thetool):
            def f():
                self.on_tool_select(thetool)
            return f

        for tool in self.tools_exc:
            self.tools_exc[tool]["button"].triggered.connect(make_callback(tool))  # Events
            self.tools_exc[tool]["button"].setCheckable(True)  # Checkable

        self.options = {
            "global_gridx": 0.1,
            "global_gridy": 0.1,
            "snap_max": 0.05,
            "grid_snap": True,
            "corner_snap": False,
            "grid_gap_link": True
        }
        self.app.options_read_form()

        for option in self.options:
            if option in self.app.options:
                self.options[option] = self.app.options[option]

        self.rtree_exc_index = rtindex.Index()
        # flag to show if the object was modified
        self.is_modified = False

        self.edited_obj_name = ""

        # variable to store the total amount of drills per job
        self.tot_drill_cnt = 0
        self.tool_row = 0

        # variable to store the total amount of slots per job
        self.tot_slot_cnt = 0
        self.tool_row_slots = 0

        self.tool_row = 0

        # store the status of the editor so the Delete at object level will not work until the edit is finished
        self.editor_active = False

        def entry2option(option, entry):
            self.options[option] = float(entry.text())

        # store the status of the editor so the Delete at object level will not work until the edit is finished
        self.editor_active = False

    def pool_recreated(self, pool):
        self.shapes.pool = pool
        self.tool_shape.pool = pool

    @staticmethod
    def make_storage():

        ## Shape storage.
        storage = FlatCAMRTreeStorage()
        storage.get_points = DrawToolShape.get_pts

        return storage

    def set_ui(self):
        # updated units
        self.units = self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().upper()

        self.olddia_newdia.clear()
        self.tool2tooldia.clear()

        # build the self.points_edit dict {dimaters: [point_list]}
        for drill in self.exc_obj.drills:
            if drill['tool'] in self.exc_obj.tools:
                if self.units == 'IN':
                    tool_dia = float('%.3f' % self.exc_obj.tools[drill['tool']]['C'])
                else:
                    tool_dia = float('%.2f' % self.exc_obj.tools[drill['tool']]['C'])

                try:
                    self.points_edit[tool_dia].append(drill['point'])
                except KeyError:
                    self.points_edit[tool_dia] = [drill['point']]
        # update the olddia_newdia dict to make sure we have an updated state of the tool_table
        for key in self.points_edit:
            self.olddia_newdia[key] = key

        sort_temp = []
        for diam in self.olddia_newdia:
            sort_temp.append(float(diam))
        self.sorted_diameters = sorted(sort_temp)

        # populate self.intial_table_rows dict with the tool number as keys and tool diameters as values
        for i in range(len(self.sorted_diameters)):
            tt_dia = self.sorted_diameters[i]
            self.tool2tooldia[i + 1] = tt_dia

    def build_ui(self):

        try:
            # if connected, disconnect the signal from the slot on item_changed as it creates issues
            self.tools_table_exc.itemChanged.disconnect()
        except:
            pass

        # updated units
        self.units = self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().upper()

        # make a new name for the new Excellon object (the one with edited content)
        self.edited_obj_name = self.exc_obj.options['name']
        self.name_entry.set_value(self.edited_obj_name)

        if self.units == "IN":
            self.addtool_entry.set_value(0.039)
        else:
            self.addtool_entry.set_value(1.00)

        sort_temp = []

        for diam in self.olddia_newdia:
            sort_temp.append(float(diam))
        self.sorted_diameters = sorted(sort_temp)

        # here, self.sorted_diameters will hold in a oblique way, the number of tools
        n = len(self.sorted_diameters)
        # we have (n+2) rows because there are 'n' tools, each a row, plus the last 2 rows for totals.
        self.tools_table_exc.setRowCount(n + 2)

        self.tot_drill_cnt = 0
        self.tot_slot_cnt = 0

        self.tool_row = 0
        # this variable will serve as the real tool_number
        tool_id = 0

        for tool_no in self.sorted_diameters:
            tool_id += 1
            drill_cnt = 0  # variable to store the nr of drills per tool
            slot_cnt = 0  # variable to store the nr of slots per tool

            # Find no of drills for the current tool
            for tool_dia in self.points_edit:
                if float(tool_dia) == tool_no:
                    drill_cnt = len(self.points_edit[tool_dia])

            self.tot_drill_cnt += drill_cnt

            try:
                # Find no of slots for the current tool
                for slot in self.slots:
                    if slot['tool'] == tool_no:
                        slot_cnt += 1

                self.tot_slot_cnt += slot_cnt
            except AttributeError:
                # log.debug("No slots in the Excellon file")
                # slot editing not implemented
                pass

            id = QtWidgets.QTableWidgetItem('%d' % int(tool_id))
            id.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.tools_table_exc.setItem(self.tool_row, 0, id)  # Tool name/id

            # Make sure that the drill diameter when in MM is with no more than 2 decimals
            # There are no drill bits in MM with more than 3 decimals diameter
            # For INCH the decimals should be no more than 3. There are no drills under 10mils
            if self.units == 'MM':
                dia = QtWidgets.QTableWidgetItem('%.2f' % self.olddia_newdia[tool_no])
            else:
                dia = QtWidgets.QTableWidgetItem('%.3f' % self.olddia_newdia[tool_no])

            dia.setFlags(QtCore.Qt.ItemIsEnabled)

            drill_count = QtWidgets.QTableWidgetItem('%d' % drill_cnt)
            drill_count.setFlags(QtCore.Qt.ItemIsEnabled)

            # if the slot number is zero is better to not clutter the GUI with zero's so we print a space
            if slot_cnt > 0:
                slot_count = QtWidgets.QTableWidgetItem('%d' % slot_cnt)
            else:
                slot_count = QtWidgets.QTableWidgetItem('')
            slot_count.setFlags(QtCore.Qt.ItemIsEnabled)

            self.tools_table_exc.setItem(self.tool_row, 1, dia)  # Diameter
            self.tools_table_exc.setItem(self.tool_row, 2, drill_count)  # Number of drills per tool
            self.tools_table_exc.setItem(self.tool_row, 3, slot_count)  # Number of drills per tool
            self.tool_row += 1

        # make the diameter column editable
        for row in range(self.tool_row):
            self.tools_table_exc.item(row, 1).setFlags(
                QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.tools_table_exc.item(row, 2).setForeground(QtGui.QColor(0, 0, 0))
            self.tools_table_exc.item(row, 3).setForeground(QtGui.QColor(0, 0, 0))

        # add a last row with the Total number of drills
        # HACK: made the text on this cell '9999' such it will always be the one before last when sorting
        # it will have to have the foreground color (font color) white
        empty = QtWidgets.QTableWidgetItem('9998')
        empty.setForeground(QtGui.QColor(255, 255, 255))

        empty.setFlags(empty.flags() ^ QtCore.Qt.ItemIsEnabled)
        empty_b = QtWidgets.QTableWidgetItem('')
        empty_b.setFlags(empty_b.flags() ^ QtCore.Qt.ItemIsEnabled)

        label_tot_drill_count = QtWidgets.QTableWidgetItem(_('Total Drills'))
        tot_drill_count = QtWidgets.QTableWidgetItem('%d' % self.tot_drill_cnt)

        label_tot_drill_count.setFlags(label_tot_drill_count.flags() ^ QtCore.Qt.ItemIsEnabled)
        tot_drill_count.setFlags(tot_drill_count.flags() ^ QtCore.Qt.ItemIsEnabled)

        self.tools_table_exc.setItem(self.tool_row, 0, empty)
        self.tools_table_exc.setItem(self.tool_row, 1, label_tot_drill_count)
        self.tools_table_exc.setItem(self.tool_row, 2, tot_drill_count)  # Total number of drills
        self.tools_table_exc.setItem(self.tool_row, 3, empty_b)

        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)

        for k in [1, 2]:
            self.tools_table_exc.item(self.tool_row, k).setForeground(QtGui.QColor(127, 0, 255))
            self.tools_table_exc.item(self.tool_row, k).setFont(font)

        self.tool_row += 1

        # add a last row with the Total number of slots
        # HACK: made the text on this cell '9999' such it will always be the last when sorting
        # it will have to have the foreground color (font color) white
        empty_2 = QtWidgets.QTableWidgetItem('9999')
        empty_2.setForeground(QtGui.QColor(255, 255, 255))

        empty_2.setFlags(empty_2.flags() ^ QtCore.Qt.ItemIsEnabled)

        empty_3 = QtWidgets.QTableWidgetItem('')
        empty_3.setFlags(empty_3.flags() ^ QtCore.Qt.ItemIsEnabled)

        label_tot_slot_count = QtWidgets.QTableWidgetItem(_('Total Slots'))
        tot_slot_count = QtWidgets.QTableWidgetItem('%d' % self.tot_slot_cnt)
        label_tot_slot_count.setFlags(label_tot_slot_count.flags() ^ QtCore.Qt.ItemIsEnabled)
        tot_slot_count.setFlags(tot_slot_count.flags() ^ QtCore.Qt.ItemIsEnabled)

        self.tools_table_exc.setItem(self.tool_row, 0, empty_2)
        self.tools_table_exc.setItem(self.tool_row, 1, label_tot_slot_count)
        self.tools_table_exc.setItem(self.tool_row, 2, empty_3)
        self.tools_table_exc.setItem(self.tool_row, 3, tot_slot_count)  # Total number of slots

        for kl in [1, 2, 3]:
            self.tools_table_exc.item(self.tool_row, kl).setFont(font)
            self.tools_table_exc.item(self.tool_row, kl).setForeground(QtGui.QColor(0, 70, 255))


        # all the tools are selected by default
        self.tools_table_exc.selectColumn(0)
        #
        self.tools_table_exc.resizeColumnsToContents()
        self.tools_table_exc.resizeRowsToContents()

        vertical_header = self.tools_table_exc.verticalHeader()
        # vertical_header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        vertical_header.hide()
        self.tools_table_exc.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        horizontal_header = self.tools_table_exc.horizontalHeader()
        horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        horizontal_header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        # horizontal_header.setStretchLastSection(True)

        # self.tools_table_exc.setSortingEnabled(True)
        # sort by tool diameter
        self.tools_table_exc.sortItems(1)

        # After sorting, to display also the number of drills in the right row we need to update self.initial_rows dict
        # with the new order. Of course the last 2 rows in the tool table are just for display therefore we don't
        # use them
        self.tool2tooldia.clear()
        for row in range(self.tools_table_exc.rowCount() - 2):
            tool = int(self.tools_table_exc.item(row, 0).text())
            diameter = float(self.tools_table_exc.item(row, 1).text())
            self.tool2tooldia[tool] = diameter

        self.tools_table_exc.setMinimumHeight(self.tools_table_exc.getHeight())
        self.tools_table_exc.setMaximumHeight(self.tools_table_exc.getHeight())

        # make sure no rows are selected so the user have to click the correct row, meaning selecting the correct tool
        self.tools_table_exc.clearSelection()

        # Remove anything else in the GUI Selected Tab
        self.app.ui.selected_scroll_area.takeWidget()
        # Put ourself in the GUI Selected Tab
        self.app.ui.selected_scroll_area.setWidget(self.exc_edit_widget)
        # Switch notebook to Selected page
        self.app.ui.notebook.setCurrentWidget(self.app.ui.selected_tab)

        # we reactivate the signals after the after the tool adding as we don't need to see the tool been populated
        self.tools_table_exc.itemChanged.connect(self.on_tool_edit)

    def on_tool_add(self, tooldia=None):
        self.is_modified = True
        if tooldia:
            tool_dia = tooldia
        else:
            try:
                tool_dia = float(self.addtool_entry.get_value())
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    tool_dia = float(self.addtool_entry.get_value().replace(',', '.'))
                except ValueError:
                    self.app.inform.emit(_("[ERROR_NOTCL]Wrong value format entered, "
                                         "use a number.")
                                         )
                    return

        if tool_dia not in self.olddia_newdia:
            storage_elem = FlatCAMGeoEditor.make_storage()
            self.storage_dict[tool_dia] = storage_elem

            # self.olddia_newdia dict keeps the evidence on current tools diameters as keys and gets updated on values
            # each time a tool diameter is edited or added
            self.olddia_newdia[tool_dia] = tool_dia
        else:
            self.app.inform.emit(_("[WARNING_NOTCL]Tool already in the original or actual tool list.\n"
                                 "Save and reedit Excellon if you need to add this tool. ")
                                 )
            return

        # since we add a new tool, we update also the initial state of the tool_table through it's dictionary
        # we add a new entry in the tool2tooldia dict
        self.tool2tooldia[len(self.olddia_newdia)] = tool_dia

        self.app.inform.emit(_("[success]Added new tool with dia: %s %s") % (str(tool_dia), str(self.units)))

        self.build_ui()

        # make a quick sort through the tool2tooldia dict so we find which row to select
        row_to_be_selected = None
        for key in sorted(self.tool2tooldia):
            if self.tool2tooldia[key] == tool_dia:
                row_to_be_selected = int(key) - 1
                break

        self.tools_table_exc.selectRow(row_to_be_selected)

    def on_tool_delete(self, dia=None):
        self.is_modified = True
        deleted_tool_dia_list = []
        deleted_tool_offset_list = []

        try:
            if dia is None or dia is False:
                # deleted_tool_dia = float(self.tools_table_exc.item(self.tools_table_exc.currentRow(), 1).text())
                for index in self.tools_table_exc.selectionModel().selectedRows():
                    row = index.row()
                    deleted_tool_dia_list.append(float(self.tools_table_exc.item(row, 1).text()))
            else:
                if isinstance(dia, list):
                    for dd in dia:
                        deleted_tool_dia_list.append(float('%.4f' % dd))
                else:
                    deleted_tool_dia_list.append(float('%.4f' % dia))
        except:
            self.app.inform.emit(_("[WARNING_NOTCL]Select a tool in Tool Table"))
            return

        for deleted_tool_dia in deleted_tool_dia_list:

            # delete de tool offset
            self.exc_obj.tool_offset.pop(float(deleted_tool_dia), None)

            # delete the storage used for that tool
            storage_elem = FlatCAMGeoEditor.make_storage()
            self.storage_dict[deleted_tool_dia] = storage_elem
            self.storage_dict.pop(deleted_tool_dia, None)

            # I've added this flag_del variable because dictionary don't like
            # having keys deleted while iterating through them
            flag_del = []
            # self.points_edit.pop(deleted_tool_dia, None)
            for deleted_tool in self.tool2tooldia:
                if self.tool2tooldia[deleted_tool] == deleted_tool_dia:
                    flag_del.append(deleted_tool)

            if flag_del:
                for tool_to_be_deleted in flag_del:
                    # delete the tool
                    self.tool2tooldia.pop(tool_to_be_deleted, None)

                    # delete also the drills from points_edit dict just in case we add the tool again, we don't want to show the
                    # number of drills from before was deleter
                    self.points_edit[deleted_tool_dia] = []
                flag_del = []

            self.olddia_newdia.pop(deleted_tool_dia, None)

            self.app.inform.emit(_("[success]Deleted tool with dia: %s %s") % (str(deleted_tool_dia), str(self.units)))

        self.replot()
        # self.app.inform.emit("Could not delete selected tool")

        self.build_ui()

    def on_tool_edit(self):
        # if connected, disconnect the signal from the slot on item_changed as it creates issues
        self.tools_table_exc.itemChanged.disconnect()
        # self.tools_table_exc.selectionModel().currentChanged.disconnect()

        self.is_modified = True
        geometry = []
        current_table_dia_edited = None

        if self.tools_table_exc.currentItem() is not None:
            current_table_dia_edited = float(self.tools_table_exc.currentItem().text())

        row_of_item_changed = self.tools_table_exc.currentRow()

        # rows start with 0, tools start with 1 so we adjust the value by 1
        key_in_tool2tooldia = row_of_item_changed + 1

        dia_changed = self.tool2tooldia[key_in_tool2tooldia]

        # tool diameter is not used so we create a new tool with the desired diameter
        if current_table_dia_edited not in self.olddia_newdia.values():
            # update the dict that holds as keys our initial diameters and as values the edited diameters
            self.olddia_newdia[dia_changed] = current_table_dia_edited
            # update the dict that holds tool_no as key and tool_dia as value
            self.tool2tooldia[key_in_tool2tooldia] = current_table_dia_edited

            # update the tool offset
            modified_offset = self.exc_obj.tool_offset.pop(dia_changed)
            self.exc_obj.tool_offset[current_table_dia_edited] = modified_offset

            self.replot()
        else:
            # tool diameter is already in use so we move the drills from the prior tool to the new tool
            factor = current_table_dia_edited / dia_changed
            for shape in self.storage_dict[dia_changed].get_objects():
                geometry.append(DrawToolShape(
                    MultiLineString([affinity.scale(subgeo, xfact=factor, yfact=factor) for subgeo in shape.geo])))

                self.points_edit[current_table_dia_edited].append((0, 0))
            self.add_exc_shape(geometry, self.storage_dict[current_table_dia_edited])

            self.on_tool_delete(dia=dia_changed)

            # delete the tool offset
            self.exc_obj.tool_offset.pop(dia_changed, None)

        # we reactivate the signals after the after the tool editing
        self.tools_table_exc.itemChanged.connect(self.on_tool_edit)
        # self.tools_table_exc.selectionModel().currentChanged.connect(self.on_row_selected)

    def on_name_activate(self):
        self.edited_obj_name = self.name_entry.get_value()

    def activate(self):
        self.connect_canvas_event_handlers()

        # self.app.collection.view.keyPressed.connect(self.on_canvas_key)

        self.shapes.enabled = True
        self.tool_shape.enabled = True
        # self.app.app_cursor.enabled = True

        self.app.ui.snap_max_dist_entry.setEnabled(True)
        self.app.ui.corner_snap_btn.setEnabled(True)
        self.app.ui.snap_magnet.setVisible(True)
        self.app.ui.corner_snap_btn.setVisible(True)

        self.app.ui.exc_editor_menu.setDisabled(False)
        self.app.ui.exc_editor_menu.menuAction().setVisible(True)

        self.app.ui.update_obj_btn.setEnabled(True)
        self.app.ui.e_editor_cmenu.setEnabled(True)

        self.app.ui.exc_edit_toolbar.setDisabled(False)
        self.app.ui.exc_edit_toolbar.setVisible(True)
        # self.app.ui.snap_toolbar.setDisabled(False)

        # start with GRID toolbar activated
        if self.app.ui.grid_snap_btn.isChecked() is False:
            self.app.ui.grid_snap_btn.trigger()

        # Tell the App that the editor is active
        self.editor_active = True

    def deactivate(self):
        self.disconnect_canvas_event_handlers()
        self.clear()
        self.app.ui.exc_edit_toolbar.setDisabled(True)

        settings = QSettings("Open Source", "FlatCAM")
        if settings.contains("layout"):
            layout = settings.value('layout', type=str)
            if layout == 'standard':
                # self.app.ui.exc_edit_toolbar.setVisible(False)

                self.app.ui.snap_max_dist_entry.setEnabled(False)
                self.app.ui.corner_snap_btn.setEnabled(False)
                self.app.ui.snap_magnet.setVisible(False)
                self.app.ui.corner_snap_btn.setVisible(False)
            elif layout == 'compact':
                # self.app.ui.exc_edit_toolbar.setVisible(True)

                self.app.ui.snap_max_dist_entry.setEnabled(False)
                self.app.ui.corner_snap_btn.setEnabled(False)
                self.app.ui.snap_magnet.setVisible(True)
                self.app.ui.corner_snap_btn.setVisible(True)
        else:
            # self.app.ui.exc_edit_toolbar.setVisible(False)

            self.app.ui.snap_max_dist_entry.setEnabled(False)
            self.app.ui.corner_snap_btn.setEnabled(False)
            self.app.ui.snap_magnet.setVisible(False)
            self.app.ui.corner_snap_btn.setVisible(False)

        # set the Editor Toolbar visibility to what was before entering in the Editor
        self.app.ui.exc_edit_toolbar.setVisible(False) if self.toolbar_old_state is False \
            else self.app.ui.exc_edit_toolbar.setVisible(True)

        # Disable visuals
        self.shapes.enabled = False
        self.tool_shape.enabled = False
        # self.app.app_cursor.enabled = False

        # Tell the app that the editor is no longer active
        self.editor_active = False

        self.app.ui.exc_editor_menu.setDisabled(True)
        self.app.ui.exc_editor_menu.menuAction().setVisible(False)

        self.app.ui.update_obj_btn.setEnabled(False)

        self.app.ui.g_editor_cmenu.setEnabled(False)
        self.app.ui.e_editor_cmenu.setEnabled(False)

        # Show original geometry
        if self.exc_obj:
            self.exc_obj.visible = True

    def connect_canvas_event_handlers(self):
        ## Canvas events

        # make sure that the shortcuts key and mouse events will no longer be linked to the methods from FlatCAMApp
        # but those from FlatCAMGeoEditor

        self.app.plotcanvas.vis_disconnect('mouse_press', self.app.on_mouse_click_over_plot)
        self.app.plotcanvas.vis_disconnect('mouse_move', self.app.on_mouse_move_over_plot)
        self.app.plotcanvas.vis_disconnect('mouse_release', self.app.on_mouse_click_release_over_plot)
        self.app.plotcanvas.vis_disconnect('mouse_double_click', self.app.on_double_click_over_plot)
        self.app.collection.view.clicked.disconnect()

        self.canvas.vis_connect('mouse_press', self.on_canvas_click)
        self.canvas.vis_connect('mouse_move', self.on_canvas_move)
        self.canvas.vis_connect('mouse_release', self.on_canvas_click_release)

    def disconnect_canvas_event_handlers(self):
        self.canvas.vis_disconnect('mouse_press', self.on_canvas_click)
        self.canvas.vis_disconnect('mouse_move', self.on_canvas_move)
        self.canvas.vis_disconnect('mouse_release', self.on_canvas_click_release)

        # we restore the key and mouse control to FlatCAMApp method
        self.app.plotcanvas.vis_connect('mouse_press', self.app.on_mouse_click_over_plot)
        self.app.plotcanvas.vis_connect('mouse_move', self.app.on_mouse_move_over_plot)
        self.app.plotcanvas.vis_connect('mouse_release', self.app.on_mouse_click_release_over_plot)
        self.app.plotcanvas.vis_connect('mouse_double_click', self.app.on_double_click_over_plot)
        self.app.collection.view.clicked.connect(self.app.collection.on_mouse_down)

    def clear(self):
        self.active_tool = None
        # self.shape_buffer = []
        self.selected = []

        self.points_edit = {}
        self.new_tools = {}
        self.new_drills = []

        self.storage_dict = {}

        self.shapes.clear(update=True)
        self.tool_shape.clear(update=True)

        # self.storage = FlatCAMExcEditor.make_storage()
        self.replot()

    def edit_fcexcellon(self, exc_obj):
        """
        Imports the geometry from the given FlatCAM Excellon object
        into the editor.

        :param fcgeometry: FlatCAMExcellon
        :return: None
        """

        assert isinstance(exc_obj, Excellon), \
            "Expected an Excellon Object, got %s" % type(exc_obj)

        self.deactivate()
        self.activate()

        # Hide original geometry
        self.exc_obj = exc_obj
        exc_obj.visible = False

        # Set selection tolerance
        # DrawToolShape.tolerance = fc_excellon.drawing_tolerance * 10

        self.select_tool("select")

        self.set_ui()

        # now that we hava data, create the GUI interface and add it to the Tool Tab
        self.build_ui()

        # we activate this after the initial build as we don't need to see the tool been populated
        self.tools_table_exc.itemChanged.connect(self.on_tool_edit)

        # build the geometry for each tool-diameter, each drill will be represented by a '+' symbol
        # and then add it to the storage elements (each storage elements is a member of a list
        for tool_dia in self.points_edit:
            storage_elem = FlatCAMGeoEditor.make_storage()
            for point in self.points_edit[tool_dia]:
                # make a '+' sign, the line length is the tool diameter
                start_hor_line = ((point.x - (tool_dia / 2)), point.y)
                stop_hor_line = ((point.x + (tool_dia / 2)), point.y)
                start_vert_line = (point.x, (point.y - (tool_dia / 2)))
                stop_vert_line = (point.x, (point.y + (tool_dia / 2)))
                shape = MultiLineString([(start_hor_line, stop_hor_line),(start_vert_line, stop_vert_line)])
                if shape is not None:
                    self.add_exc_shape(DrawToolShape(shape), storage_elem)
            self.storage_dict[tool_dia] = storage_elem

        self.replot()

        # add a first tool in the Tool Table but only if the Excellon Object is empty
        if not self.tool2tooldia:
            self.on_tool_add(tooldia=1.00)

    def update_fcexcellon(self, exc_obj):
        """
        Create a new Excellon object that contain the edited content of the source Excellon object

        :param exc_obj: FlatCAMExcellon
        :return: None
        """

        # this dictionary will contain tooldia's as keys and a list of coordinates tuple as values
        # the values of this dict are coordinates of the holes (drills)
        edited_points = {}
        for storage_tooldia in self.storage_dict:
            for x in self.storage_dict[storage_tooldia].get_objects():

                # all x.geo in self.storage_dict[storage] are MultiLinestring objects
                # each MultiLineString is made out of Linestrings
                # select first Linestring object in the current MultiLineString
                first_linestring = x.geo[0]
                # get it's coordinates
                first_linestring_coords = first_linestring.coords
                x_coord = first_linestring_coords[0][0] + (float(storage_tooldia) / 2)
                y_coord = first_linestring_coords[0][1]

                # create a tuple with the coordinates (x, y) and add it to the list that is the value of the
                # edited_points dictionary
                point = (x_coord, y_coord)
                if not storage_tooldia in edited_points:
                    edited_points[storage_tooldia] = [point]
                else:
                    edited_points[storage_tooldia].append(point)

        # recreate the drills and tools to be added to the new Excellon edited object
        # first, we look in the tool table if one of the tool diameters was changed then
        # append that a tuple formed by (old_dia, edited_dia) to a list
        changed_key = []
        for initial_dia in self.olddia_newdia:
            edited_dia = self.olddia_newdia[initial_dia]
            if edited_dia != initial_dia:
                for old_dia in edited_points:
                    if old_dia == initial_dia:
                        changed_key.append((old_dia, edited_dia))
            # if the initial_dia is not in edited_points it means it is a new tool with no drill points
            # (and we have to add it)
            # because in case we have drill points it will have to be already added in edited_points
            # if initial_dia not in edited_points.keys():
            #     edited_points[initial_dia] = []

        for el in changed_key:
            edited_points[el[1]] = edited_points.pop(el[0])

        # Let's sort the edited_points dictionary by keys (diameters) and store the result in a zipped list
        # ordered_edited_points is a ordered list of tuples;
        # element[0] of the tuple is the diameter and
        # element[1] of the tuple is a list of coordinates (a tuple themselves)
        ordered_edited_points = sorted(zip(edited_points.keys(), edited_points.values()))

        current_tool = 0
        for tool_dia in ordered_edited_points:
            current_tool += 1

            # create the self.tools for the new Excellon object (the one with edited content)
            name = str(current_tool)
            spec = {"C": float(tool_dia[0])}
            self.new_tools[name] = spec

            # add in self.tools the 'solid_geometry' key, the value (a list) is populated bellow
            self.new_tools[name]['solid_geometry'] = []

            # create the self.drills for the new Excellon object (the one with edited content)
            for point in tool_dia[1]:
                self.new_drills.append(
                    {
                        'point': Point(point),
                        'tool': str(current_tool)
                    }
                )
                # repopulate the 'solid_geometry' for each tool
                poly = Point(point).buffer(float(tool_dia[0]) / 2.0, int(int(exc_obj.geo_steps_per_circle) / 4))
                self.new_tools[name]['solid_geometry'].append(poly)

        if self.is_modified is True:
            if "_edit" in self.edited_obj_name:
                try:
                    id = int(self.edited_obj_name[-1]) + 1
                    self.edited_obj_name = self.edited_obj_name[:-1] + str(id)
                except ValueError:
                    self.edited_obj_name += "_1"
            else:
                self.edited_obj_name += "_edit"

        self.app.worker_task.emit({'fcn': self.new_edited_excellon,
                                   'params': [self.edited_obj_name]})

        if self.exc_obj.slots:
            self.new_slots = self.exc_obj.slots

        self.new_tool_offset = self.exc_obj.tool_offset

        # reset the tool table
        self.tools_table_exc.clear()
        self.tools_table_exc.setHorizontalHeaderLabels(['#', _('Diameter'), 'D', 'S'])
        self.last_tool_selected = None

        # delete the edited Excellon object which will be replaced by a new one having the edited content of the first
        self.app.collection.set_active(self.exc_obj.options['name'])
        self.app.collection.delete_active()

        # restore GUI to the Selected TAB
        # Remove anything else in the GUI
        self.app.ui.tool_scroll_area.takeWidget()
        # Switch notebook to Selected page
        self.app.ui.notebook.setCurrentWidget(self.app.ui.selected_tab)

    def update_options(self, obj):
        try:
            if not obj.options:
                obj.options = {}
                obj.options['xmin'] = 0
                obj.options['ymin'] = 0
                obj.options['xmax'] = 0
                obj.options['ymax'] = 0
                return True
            else:
                return False
        except AttributeError:
            obj.options = {}
            return True

    def new_edited_excellon(self, outname):
        """
        Creates a new Excellon object for the edited Excellon. Thread-safe.

        :param outname: Name of the resulting object. None causes the
            name to be that of the file.
        :type outname: str
        :return: None
        """

        self.app.log.debug("Update the Excellon object with edited content. Source is %s" %
                           self.exc_obj.options['name'])

        # How the object should be initialized
        def obj_init(excellon_obj, app_obj):
            # self.progress.emit(20)
            excellon_obj.drills = self.new_drills
            excellon_obj.tools = self.new_tools
            excellon_obj.slots = self.new_slots
            excellon_obj.tool_offset = self.new_tool_offset
            excellon_obj.options['name'] = outname

            try:
                excellon_obj.create_geometry()
            except KeyError:
                self.app.inform.emit(
                   _( "[ERROR_NOTCL] There are no Tools definitions in the file. Aborting Excellon creation.")
                )
            except:
                msg = _("[ERROR] An internal error has ocurred. See shell.\n")
                msg += traceback.format_exc()
                app_obj.inform.emit(msg)
                raise
                # raise

        with self.app.proc_container.new(_("Creating Excellon.")):

            try:
                self.app.new_object("excellon", outname, obj_init)
            except Exception as e:
                log.error("Error on object creation: %s" % str(e))
                self.app.progress.emit(100)
                return

            self.app.inform.emit(_("[success]Excellon editing finished."))
            # self.progress.emit(100)

    def on_tool_select(self, tool):
        """
        Behavior of the toolbar. Tool initialization.

        :rtype : None
        """
        current_tool = tool

        self.app.log.debug("on_tool_select('%s')" % tool)

        if self.last_tool_selected is None and current_tool is not 'select':
            # self.draw_app.select_tool('select')
            self.complete = True
            current_tool = 'select'
            self.app.inform.emit(_("[WARNING_NOTCL]Cancelled. There is no Tool/Drill selected"))

        # This is to make the group behave as radio group
        if current_tool in self.tools_exc:
            if self.tools_exc[current_tool]["button"].isChecked():
                self.app.log.debug("%s is checked." % current_tool)
                for t in self.tools_exc:
                    if t != current_tool:
                        self.tools_exc[t]["button"].setChecked(False)

                # this is where the Editor toolbar classes (button's) are instantiated
                self.active_tool = self.tools_exc[current_tool]["constructor"](self)
                # self.app.inform.emit(self.active_tool.start_msg)
            else:
                self.app.log.debug("%s is NOT checked." % current_tool)
                for t in self.tools_exc:
                    self.tools_exc[t]["button"].setChecked(False)
                self.active_tool = None

    def on_row_selected(self):
        self.selected = []

        try:
            selected_dia = self.tool2tooldia[self.tools_table_exc.currentRow() + 1]
            self.last_tool_selected = self.tools_table_exc.currentRow() + 1
            for obj in self.storage_dict[selected_dia].get_objects():
                self.selected.append(obj)
        except Exception as e:
            self.app.log.debug(str(e))

        self.replot()

    def toolbar_tool_toggle(self, key):
        self.options[key] = self.sender().isChecked()
        if self.options[key] == True:
            return 1
        else:
            return 0

    def on_canvas_click(self, event):
        """
        event.x and .y have canvas coordinates
        event.xdaya and .ydata have plot coordinates

        :param event: Event object dispatched by Matplotlib
        :return: None
        """

        if event.button is 1:
            self.app.ui.rel_position_label.setText("<b>Dx</b>: %.4f&nbsp;&nbsp;  <b>Dy</b>: "
                                                   "%.4f&nbsp;&nbsp;&nbsp;&nbsp;" % (0, 0))
            self.pos = self.canvas.vispy_canvas.translate_coords(event.pos)

            ### Snap coordinates
            x, y = self.app.geo_editor.snap(self.pos[0], self.pos[1])

            self.pos = (x, y)
            # print(self.active_tool)

            # Selection with left mouse button
            if self.active_tool is not None and event.button is 1:
                # Dispatch event to active_tool
                # msg = self.active_tool.click(self.app.geo_editor.snap(event.xdata, event.ydata))
                msg = self.active_tool.click(self.app.geo_editor.snap(self.pos[0], self.pos[1]))

                # If it is a shape generating tool
                if isinstance(self.active_tool, FCShapeTool) and self.active_tool.complete:
                    if self.current_storage is not None:
                        self.on_exc_shape_complete(self.current_storage)
                        self.build_ui()
                    # MS: always return to the Select Tool if modifier key is not pressed
                    # else return to the current tool
                    key_modifier = QtWidgets.QApplication.keyboardModifiers()
                    if self.draw_app.app.defaults["global_mselect_key"] == 'Control':
                        modifier_to_use = Qt.ControlModifier
                    else:
                        modifier_to_use = Qt.ShiftModifier
                    # if modifier key is pressed then we add to the selected list the current shape but if it's already
                    # in the selected list, we removed it. Therefore first click selects, second deselects.
                    if key_modifier == modifier_to_use:
                        self.select_tool(self.active_tool.name)
                    else:
                        self.select_tool("select")
                        return

                if isinstance(self.active_tool, FCDrillSelect):
                    # self.app.log.debug("Replotting after click.")
                    self.replot()
            else:
                self.app.log.debug("No active tool to respond to click!")

    def on_exc_shape_complete(self, storage):
        self.app.log.debug("on_shape_complete()")

        # Add shape
        if type(storage) is list:
            for item_storage in storage:
                self.add_exc_shape(self.active_tool.geometry, item_storage)
        else:
            self.add_exc_shape(self.active_tool.geometry, storage)

        # Remove any utility shapes
        self.delete_utility_geometry()
        self.tool_shape.clear(update=True)

        # Replot and reset tool.
        self.replot()
        # self.active_tool = type(self.active_tool)(self)

    def add_exc_shape(self, shape, storage):
        """
        Adds a shape to the shape storage.

        :param shape: Shape to be added.
        :type shape: DrawToolShape
        :return: None
        """
        # List of DrawToolShape?
        if isinstance(shape, list):
            for subshape in shape:
                self.add_exc_shape(subshape, storage)
            return

        assert isinstance(shape, DrawToolShape), \
            "Expected a DrawToolShape, got %s" % str(type(shape))

        assert shape.geo is not None, \
            "Shape object has empty geometry (None)"

        assert (isinstance(shape.geo, list) and len(shape.geo) > 0) or \
               not isinstance(shape.geo, list), \
            "Shape objects has empty geometry ([])"

        if isinstance(shape, DrawToolUtilityShape):
            self.utility.append(shape)
        else:
            storage.insert(shape)  # TODO: Check performance

    def add_shape(self, shape):
        """
        Adds a shape to the shape storage.

        :param shape: Shape to be added.
        :type shape: DrawToolShape
        :return: None
        """

        # List of DrawToolShape?
        if isinstance(shape, list):
            for subshape in shape:
                self.add_shape(subshape)
            return

        assert isinstance(shape, DrawToolShape), \
            "Expected a DrawToolShape, got %s" % type(shape)

        assert shape.geo is not None, \
            "Shape object has empty geometry (None)"

        assert (isinstance(shape.geo, list) and len(shape.geo) > 0) or \
               not isinstance(shape.geo, list), \
            "Shape objects has empty geometry ([])"

        if isinstance(shape, DrawToolUtilityShape):
            self.utility.append(shape)
        else:
            self.storage.insert(shape)  # TODO: Check performance

    def on_canvas_click_release(self, event):
        pos_canvas = self.canvas.vispy_canvas.translate_coords(event.pos)

        self.modifiers = QtWidgets.QApplication.keyboardModifiers()

        if self.app.grid_status():
            pos = self.app.geo_editor.snap(pos_canvas[0], pos_canvas[1])
        else:
            pos = (pos_canvas[0], pos_canvas[1])

        # if the released mouse button was RMB then test if it was a panning motion or not, if not it was a context
        # canvas menu
        try:
            if event.button == 2:  # right click
                if self.app.panning_action is True:
                    self.app.panning_action = False
                else:
                    self.app.cursor = QtGui.QCursor()
                    self.app.ui.popMenu.popup(self.app.cursor.pos())
        except Exception as e:
            log.warning("Error: %s" % str(e))
            raise

        # if the released mouse button was LMB then test if we had a right-to-left selection or a left-to-right
        # selection and then select a type of selection ("enclosing" or "touching")
        try:
            if event.button == 1:  # left click
                if self.app.selection_type is not None:
                    self.draw_selection_area_handler(self.pos, pos, self.app.selection_type)
                    self.app.selection_type = None
                elif isinstance(self.active_tool, FCDrillSelect):
                    # Dispatch event to active_tool
                    # msg = self.active_tool.click(self.app.geo_editor.snap(event.xdata, event.ydata))
                    # msg = self.active_tool.click_release((self.pos[0], self.pos[1]))
                    # self.app.inform.emit(msg)
                    self.active_tool.click_release((self.pos[0], self.pos[1]))
                    self.replot()
        except Exception as e:
            log.warning("Error: %s" % str(e))
            raise

    def draw_selection_area_handler(self, start_pos, end_pos, sel_type):
        """
        :param start_pos: mouse position when the selection LMB click was done
        :param end_pos: mouse position when the left mouse button is released
        :param sel_type: if True it's a left to right selection (enclosure), if False it's a 'touch' selection
        :type Bool
        :return:
        """
        poly_selection = Polygon([start_pos, (end_pos[0], start_pos[1]), end_pos, (start_pos[0], end_pos[1])])

        self.app.delete_selection_shape()
        for storage in self.storage_dict:
            for obj in self.storage_dict[storage].get_objects():
                if (sel_type is True and poly_selection.contains(obj.geo)) or \
                        (sel_type is False and poly_selection.intersects(obj.geo)):
                    if self.key == self.app.defaults["global_mselect_key"]:
                        if obj in self.selected:
                            self.selected.remove(obj)
                        else:
                            # add the object to the selected shapes
                            self.selected.append(obj)
                    else:
                        self.selected.append(obj)

        # select the diameter of the selected shape in the tool table
        for storage in self.storage_dict:
            for shape_s in self.selected:
                if shape_s in self.storage_dict[storage].get_objects():
                    for key in self.tool2tooldia:
                        if self.tool2tooldia[key] == storage:
                            item = self.tools_table_exc.item((key - 1), 1)
                            self.tools_table_exc.setCurrentItem(item)
                            self.last_tool_selected = key
                            # item.setSelected(True)
                            # self.exc_editor_app.tools_table_exc.selectItem(key - 1)

        self.replot()

    def on_canvas_move(self, event):
        """
        Called on 'mouse_move' event

        event.pos have canvas screen coordinates

        :param event: Event object dispatched by VisPy SceneCavas
        :return: None
        """

        pos = self.canvas.vispy_canvas.translate_coords(event.pos)
        event.xdata, event.ydata = pos[0], pos[1]

        self.x = event.xdata
        self.y = event.ydata

        # Prevent updates on pan
        # if len(event.buttons) > 0:
        #     return

        # if the RMB is clicked and mouse is moving over plot then 'panning_action' is True
        if event.button == 2:
            self.app.panning_action = True
            return
        else:
            self.app.panning_action = False

        try:
            x = float(event.xdata)
            y = float(event.ydata)
        except TypeError:
            return

        if self.active_tool is None:
            return

        ### Snap coordinates
        x, y = self.app.geo_editor.app.geo_editor.snap(x, y)

        self.snap_x = x
        self.snap_y = y

        # update the position label in the infobar since the APP mouse event handlers are disconnected
        self.app.ui.position_label.setText("&nbsp;&nbsp;&nbsp;&nbsp;<b>X</b>: %.4f&nbsp;&nbsp;   "
                                       "<b>Y</b>: %.4f" % (x, y))

        if self.pos is None:
            self.pos = (0, 0)
        dx = x - self.pos[0]
        dy = y - self.pos[1]

        # update the reference position label in the infobar since the APP mouse event handlers are disconnected
        self.app.ui.rel_position_label.setText("<b>Dx</b>: %.4f&nbsp;&nbsp;  <b>Dy</b>: "
                                           "%.4f&nbsp;&nbsp;&nbsp;&nbsp;" % (dx, dy))

        ### Utility geometry (animated)
        geo = self.active_tool.utility_geometry(data=(x, y))

        if isinstance(geo, DrawToolShape) and geo.geo is not None:

            # Remove any previous utility shape
            self.tool_shape.clear(update=True)
            self.draw_utility_geometry(geo=geo)

        ### Selection area on canvas section ###
        dx = pos[0] - self.pos[0]
        if event.is_dragging == 1 and event.button == 1:
            self.app.delete_selection_shape()
            if dx < 0:
                self.app.draw_moving_selection_shape((self.pos[0], self.pos[1]), (x,y),
                     color=self.app.defaults["global_alt_sel_line"],
                     face_color=self.app.defaults['global_alt_sel_fill'])
                self.app.selection_type = False
            else:
                self.app.draw_moving_selection_shape((self.pos[0], self.pos[1]), (x,y))
                self.app.selection_type = True
        else:
            self.app.selection_type = None

        # Update cursor
        self.app.app_cursor.set_data(np.asarray([(x, y)]), symbol='++', edge_color='black', size=20)

    def on_canvas_key_release(self, event):
        self.key = None

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


    def replot(self):
        self.plot_all()

    def plot_all(self):
        """
        Plots all shapes in the editor.

        :return: None
        :rtype: None
        """
        # self.app.log.debug("plot_all()")
        self.shapes.clear(update=True)

        for storage in self.storage_dict:
            for shape_plus in self.storage_dict[storage].get_objects():
                if shape_plus.geo is None:
                    continue

                if shape_plus in self.selected:
                    self.plot_shape(geometry=shape_plus.geo, color=self.app.defaults['global_sel_draw_color'],
                                    linewidth=2)
                    continue
                self.plot_shape(geometry=shape_plus.geo, color=self.app.defaults['global_draw_color'])

        # for shape in self.storage.get_objects():
        #     if shape.geo is None:  # TODO: This shouldn't have happened
        #         continue
        #
        #     if shape in self.selected:
        #         self.plot_shape(geometry=shape.geo, color=self.app.defaults['global_sel_draw_color'], linewidth=2)
        #         continue
        #
        #     self.plot_shape(geometry=shape.geo, color=self.app.defaults['global_draw_color'])



        for shape in self.utility:
            self.plot_shape(geometry=shape.geo, linewidth=1)
            continue

        self.shapes.redraw()

    def plot_shape(self, geometry=None, color='black', linewidth=1):
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

        ## Non-iterable
        except TypeError:

            ## DrawToolShape
            if isinstance(geometry, DrawToolShape):
                plot_elements += self.plot_shape(geometry=geometry.geo, color=color, linewidth=linewidth)

            ## Polygon: Descend into exterior and each interior.
            if type(geometry) == Polygon:
                plot_elements += self.plot_shape(geometry=geometry.exterior, color=color, linewidth=linewidth)
                plot_elements += self.plot_shape(geometry=geometry.interiors, color=color, linewidth=linewidth)

            if type(geometry) == LineString or type(geometry) == LinearRing:
                plot_elements.append(self.shapes.add(shape=geometry, color=color, layer=0))

            if type(geometry) == Point:
                pass

        return plot_elements

    def on_shape_complete(self):
        self.app.log.debug("on_shape_complete()")

        # Add shape
        self.add_shape(self.active_tool.geometry)

        # Remove any utility shapes
        self.delete_utility_geometry()
        self.tool_shape.clear(update=True)

        # Replot and reset tool.
        self.replot()
        # self.active_tool = type(self.active_tool)(self)

    def get_selected(self):
        """
        Returns list of shapes that are selected in the editor.

        :return: List of shapes.
        """
        # return [shape for shape in self.shape_buffer if shape["selected"]]
        return self.selected

    def delete_selected(self):
        temp_ref = [s for s in self.selected]
        for shape_sel in temp_ref:
            self.delete_shape(shape_sel)

        self.selected = []
        self.build_ui()
        self.app.inform.emit(_("[success]Done. Drill(s) deleted."))

    def delete_shape(self, shape):
        self.is_modified = True

        if shape in self.utility:
            self.utility.remove(shape)
            return

        for storage in self.storage_dict:
            # try:
            #     self.storage_dict[storage].remove(shape)
            # except:
            #     pass
            if shape in self.storage_dict[storage].get_objects():
                self.storage_dict[storage].remove(shape)
                # a hack to make the tool_table display less drills per diameter
                # self.points_edit it's only useful first time when we load the data into the storage
                # but is still used as referecen when building tool_table in self.build_ui()
                # the number of drills displayed in column 2 is just a len(self.points_edit) therefore
                # deleting self.points_edit elements (doesn't matter who but just the number) solved the display issue.
                del self.points_edit[storage][0]

        if shape in self.selected:
            self.selected.remove(shape)  # TODO: Check performance

    def delete_utility_geometry(self):
        # for_deletion = [shape for shape in self.shape_buffer if shape.utility]
        # for_deletion = [shape for shape in self.storage.get_objects() if shape.utility]
        for_deletion = [shape for shape in self.utility]
        for shape in for_deletion:
            self.delete_shape(shape)

        self.tool_shape.clear(update=True)
        self.tool_shape.redraw()

    def on_delete_btn(self):
        self.delete_selected()
        self.replot()

    def select_tool(self, toolname):
        """
        Selects a drawing tool. Impacts the object and GUI.

        :param toolname: Name of the tool.
        :return: None
        """
        self.tools_exc[toolname]["button"].setChecked(True)
        self.on_tool_select(toolname)

    def set_selected(self, shape):

        # Remove and add to the end.
        if shape in self.selected:
            self.selected.remove(shape)

        self.selected.append(shape)

    def set_unselected(self, shape):
        if shape in self.selected:
            self.selected.remove(shape)

    def on_array_type_combo(self):
        if self.array_type_combo.currentIndex() == 0:
            self.array_circular_frame.hide()
            self.array_linear_frame.show()
        else:
            self.delete_utility_geometry()
            self.array_circular_frame.show()
            self.array_linear_frame.hide()
            self.app.inform.emit(_("Click on the circular array Center position"))

    def on_linear_angle_radio(self):
        val = self.drill_axis_radio.get_value()
        if val == 'A':
            self.linear_angle_spinner.show()
            self.linear_angle_label.show()
        else:
            self.linear_angle_spinner.hide()
            self.linear_angle_label.hide()

    def exc_add_drill(self):
        self.select_tool('add')
        return

    def exc_add_drill_array(self):
        self.select_tool('add_array')
        return

    def exc_resize_drills(self):
        self.select_tool('resize')
        return

    def exc_copy_drills(self):
        self.select_tool('copy')
        return

    def exc_move_drills(self):
        self.select_tool('move')
        return

def distance(pt1, pt2):
    return sqrt((pt1[0] - pt2[0]) ** 2 + (pt1[1] - pt2[1]) ** 2)


def mag(vec):
    return sqrt(vec[0] ** 2 + vec[1] ** 2)


def poly2rings(poly):
    return [poly.exterior] + [interior for interior in poly.interiors]
