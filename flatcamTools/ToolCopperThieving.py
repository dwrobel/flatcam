# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 10/25/2019                                         #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtCore

import FlatCAMApp
from FlatCAMTool import FlatCAMTool
from flatcamGUI.GUIElements import FCDoubleSpinner, RadioSet, FCEntry, FCComboBox
from FlatCAMObj import FlatCAMGerber, FlatCAMGeometry, FlatCAMExcellon

import shapely.geometry.base as base
from shapely.ops import cascaded_union, unary_union
from shapely.geometry import Polygon, MultiPolygon, Point, LineString
from shapely.geometry import box as box
import shapely.affinity as affinity

import logging
from copy import deepcopy
import numpy as np
from collections import Iterable

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class ToolCopperThieving(FlatCAMTool):
    work_finished = QtCore.pyqtSignal()

    toolName = _("Copper Thieving Tool")

    def __init__(self, app):
        FlatCAMTool.__init__(self, app)

        self.app = app
        self.canvas = self.app.plotcanvas

        self.decimals = self.app.decimals
        self.units = self.app.defaults['units']

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
        self.layout.addWidget(QtWidgets.QLabel(''))

        # ## Grid Layout
        i_grid_lay = QtWidgets.QGridLayout()
        self.layout.addLayout(i_grid_lay)
        i_grid_lay.setColumnStretch(0, 0)
        i_grid_lay.setColumnStretch(1, 1)

        self.grb_object_combo = FCComboBox()
        self.grb_object_combo.setModel(self.app.collection)
        self.grb_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.grb_object_combo.is_last = True
        self.grb_object_combo.obj_type = 'Gerber'

        self.grbobj_label = QtWidgets.QLabel("<b>%s:</b>" % _("GERBER"))
        self.grbobj_label.setToolTip(
            _("Gerber Object to which will be added a copper thieving.")
        )

        i_grid_lay.addWidget(self.grbobj_label, 0, 0)
        i_grid_lay.addWidget(self.grb_object_combo, 0, 1, 1, 2)
        i_grid_lay.addWidget(QtWidgets.QLabel(''), 1, 0)

        # ## Grid Layout
        grid_lay = QtWidgets.QGridLayout()
        self.layout.addLayout(grid_lay)
        grid_lay.setColumnStretch(0, 0)
        grid_lay.setColumnStretch(1, 1)

        self.copper_fill_label = QtWidgets.QLabel('<b>%s</b>' % _('Parameters'))
        self.copper_fill_label.setToolTip(
            _("Parameters used for this tool.")
        )
        grid_lay.addWidget(self.copper_fill_label, 0, 0, 1, 2)

        # CLEARANCE #
        self.clearance_label = QtWidgets.QLabel('%s:' % _("Clearance"))
        self.clearance_label.setToolTip(
            _("This set the distance between the copper thieving components\n"
              "(the polygon fill may be split in multiple polygons)\n"
              "and the copper traces in the Gerber file.")
        )
        self.clearance_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.clearance_entry.set_range(0.00001, 9999.9999)
        self.clearance_entry.set_precision(self.decimals)
        self.clearance_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.clearance_label, 1, 0)
        grid_lay.addWidget(self.clearance_entry, 1, 1)

        # MARGIN #
        self.margin_label = QtWidgets.QLabel('%s:' % _("Margin"))
        self.margin_label.setToolTip(
            _("Bounding box margin.")
        )
        self.margin_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.margin_entry.set_range(0.0, 9999.9999)
        self.margin_entry.set_precision(self.decimals)
        self.margin_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.margin_label, 2, 0)
        grid_lay.addWidget(self.margin_entry, 2, 1)

        # Reference #
        self.reference_radio = RadioSet([
            {'label': _('Itself'), 'value': 'itself'},
            {"label": _("Area Selection"), "value": "area"},
            {'label':  _("Reference Object"), 'value': 'box'}
        ], orientation='vertical', stretch=False)
        self.reference_label = QtWidgets.QLabel(_("Reference:"))
        self.reference_label.setToolTip(
            _("- 'Itself' - the copper thieving extent is based on the object extent.\n"
              "- 'Area Selection' - left mouse click to start selection of the area to be filled.\n"
              "- 'Reference Object' - will do copper thieving within the area specified by another object.")
        )
        grid_lay.addWidget(self.reference_label, 3, 0)
        grid_lay.addWidget(self.reference_radio, 3, 1)

        self.ref_combo_type_label = QtWidgets.QLabel('%s:' % _("Ref. Type"))
        self.ref_combo_type_label.setToolTip(
            _("The type of FlatCAM object to be used as copper thieving reference.\n"
              "It can be Gerber, Excellon or Geometry.")
        )
        self.ref_combo_type = FCComboBox()
        self.ref_combo_type.addItems([_("Gerber"), _("Excellon"), _("Geometry")])

        grid_lay.addWidget(self.ref_combo_type_label, 4, 0)
        grid_lay.addWidget(self.ref_combo_type, 4, 1)

        self.ref_combo_label = QtWidgets.QLabel('%s:' % _("Ref. Object"))
        self.ref_combo_label.setToolTip(
            _("The FlatCAM object to be used as non copper clearing reference.")
        )
        self.ref_combo = FCComboBox()
        self.ref_combo.setModel(self.app.collection)
        self.ref_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.ref_combo.is_last = True
        self.ref_combo.obj_type = {
            _("Gerber"): "Gerber", _("Excellon"): "Excellon", _("Geometry"): "Geometry"
        }[self.ref_combo_type.get_value()]

        grid_lay.addWidget(self.ref_combo_label, 5, 0)
        grid_lay.addWidget(self.ref_combo, 5, 1)

        self.ref_combo.hide()
        self.ref_combo_label.hide()
        self.ref_combo_type.hide()
        self.ref_combo_type_label.hide()

        # Bounding Box Type #
        self.bbox_type_radio = RadioSet([
            {'label': _('Rectangular'), 'value': 'rect'},
            {"label": _("Minimal"), "value": "min"}
        ], stretch=False)
        self.bbox_type_label = QtWidgets.QLabel(_("Box Type:"))
        self.bbox_type_label.setToolTip(
            _("- 'Rectangular' - the bounding box will be of rectangular shape.\n"
              "- 'Minimal' - the bounding box will be the convex hull shape.")
        )
        grid_lay.addWidget(self.bbox_type_label, 6, 0)
        grid_lay.addWidget(self.bbox_type_radio, 6, 1)
        self.bbox_type_label.hide()
        self.bbox_type_radio.hide()

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line, 7, 0, 1, 2)

        # Fill Type
        self.fill_type_radio = RadioSet([
            {'label': _('Solid'), 'value': 'solid'},
            {"label": _("Dots Grid"), "value": "dot"},
            {"label": _("Squares Grid"), "value": "square"},
            {"label": _("Lines Grid"), "value": "line"}
        ], orientation='vertical', stretch=False)
        self.fill_type_label = QtWidgets.QLabel(_("Fill Type:"))
        self.fill_type_label.setToolTip(
            _("- 'Solid' - copper thieving will be a solid polygon.\n"
              "- 'Dots Grid' - the empty area will be filled with a pattern of dots.\n"
              "- 'Squares Grid' - the empty area will be filled with a pattern of squares.\n"
              "- 'Lines Grid' - the empty area will be filled with a pattern of lines.")
        )
        grid_lay.addWidget(self.fill_type_label, 8, 0)
        grid_lay.addWidget(self.fill_type_radio, 8, 1)

        # DOTS FRAME
        self.dots_frame = QtWidgets.QFrame()
        self.dots_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.dots_frame)
        dots_grid = QtWidgets.QGridLayout()
        dots_grid.setColumnStretch(0, 0)
        dots_grid.setColumnStretch(1, 1)
        dots_grid.setContentsMargins(0, 0, 0, 0)
        self.dots_frame.setLayout(dots_grid)
        self.dots_frame.hide()

        self.dots_label = QtWidgets.QLabel('<b>%s</b>:' % _("Dots Grid Parameters"))
        dots_grid.addWidget(self.dots_label, 0, 0, 1, 2)

        # Dot diameter #
        self.dotdia_label = QtWidgets.QLabel('%s:' % _("Dia"))
        self.dotdia_label.setToolTip(
            _("Dot diameter in Dots Grid.")
        )
        self.dot_dia_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.dot_dia_entry.set_range(0.0, 9999.9999)
        self.dot_dia_entry.set_precision(self.decimals)
        self.dot_dia_entry.setSingleStep(0.1)

        dots_grid.addWidget(self.dotdia_label, 1, 0)
        dots_grid.addWidget(self.dot_dia_entry, 1, 1)

        # Dot spacing #
        self.dotspacing_label = QtWidgets.QLabel('%s:' % _("Spacing"))
        self.dotspacing_label.setToolTip(
            _("Distance between each two dots in Dots Grid.")
        )
        self.dot_spacing_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.dot_spacing_entry.set_range(0.0, 9999.9999)
        self.dot_spacing_entry.set_precision(self.decimals)
        self.dot_spacing_entry.setSingleStep(0.1)

        dots_grid.addWidget(self.dotspacing_label, 2, 0)
        dots_grid.addWidget(self.dot_spacing_entry, 2, 1)

        # SQUARES FRAME
        self.squares_frame = QtWidgets.QFrame()
        self.squares_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.squares_frame)
        squares_grid = QtWidgets.QGridLayout()
        squares_grid.setColumnStretch(0, 0)
        squares_grid.setColumnStretch(1, 1)
        squares_grid.setContentsMargins(0, 0, 0, 0)
        self.squares_frame.setLayout(squares_grid)
        self.squares_frame.hide()

        self.squares_label = QtWidgets.QLabel('<b>%s</b>:' % _("Squares Grid Parameters"))
        squares_grid.addWidget(self.squares_label, 0, 0, 1, 2)

        # Square Size #
        self.square_size_label = QtWidgets.QLabel('%s:' % _("Size"))
        self.square_size_label.setToolTip(
            _("Square side size in Squares Grid.")
        )
        self.square_size_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.square_size_entry.set_range(0.0, 9999.9999)
        self.square_size_entry.set_precision(self.decimals)
        self.square_size_entry.setSingleStep(0.1)

        squares_grid.addWidget(self.square_size_label, 1, 0)
        squares_grid.addWidget(self.square_size_entry, 1, 1)

        # Squares spacing #
        self.squares_spacing_label = QtWidgets.QLabel('%s:' % _("Spacing"))
        self.squares_spacing_label.setToolTip(
            _("Distance between each two squares in Squares Grid.")
        )
        self.squares_spacing_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.squares_spacing_entry.set_range(0.0, 9999.9999)
        self.squares_spacing_entry.set_precision(self.decimals)
        self.squares_spacing_entry.setSingleStep(0.1)

        squares_grid.addWidget(self.squares_spacing_label, 2, 0)
        squares_grid.addWidget(self.squares_spacing_entry, 2, 1)

        # LINES FRAME
        self.lines_frame = QtWidgets.QFrame()
        self.lines_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.lines_frame)
        lines_grid = QtWidgets.QGridLayout()
        lines_grid.setColumnStretch(0, 0)
        lines_grid.setColumnStretch(1, 1)
        lines_grid.setContentsMargins(0, 0, 0, 0)
        self.lines_frame.setLayout(lines_grid)
        self.lines_frame.hide()

        self.lines_label = QtWidgets.QLabel('<b>%s</b>:' % _("Lines Grid Parameters"))
        lines_grid.addWidget(self.lines_label, 0, 0, 1, 2)

        # Square Size #
        self.line_size_label = QtWidgets.QLabel('%s:' % _("Size"))
        self.line_size_label.setToolTip(
            _("Line thickness size in Lines Grid.")
        )
        self.line_size_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.line_size_entry.set_range(0.0, 9999.9999)
        self.line_size_entry.set_precision(self.decimals)
        self.line_size_entry.setSingleStep(0.1)

        lines_grid.addWidget(self.line_size_label, 1, 0)
        lines_grid.addWidget(self.line_size_entry, 1, 1)

        # Lines spacing #
        self.lines_spacing_label = QtWidgets.QLabel('%s:' % _("Spacing"))
        self.lines_spacing_label.setToolTip(
            _("Distance between each two lines in Lines Grid.")
        )
        self.lines_spacing_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.lines_spacing_entry.set_range(0.0, 9999.9999)
        self.lines_spacing_entry.set_precision(self.decimals)
        self.lines_spacing_entry.setSingleStep(0.1)

        lines_grid.addWidget(self.lines_spacing_label, 2, 0)
        lines_grid.addWidget(self.lines_spacing_entry, 2, 1)

        # ## Insert Copper Thieving
        self.fill_button = QtWidgets.QPushButton(_("Insert Copper thieving"))
        self.fill_button.setToolTip(
            _("Will add a polygon (may be split in multiple parts)\n"
              "that will surround the actual Gerber traces at a certain distance.")
        )
        self.fill_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)
        self.layout.addWidget(self.fill_button)

        # ## Grid Layout
        grid_lay_1 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid_lay_1)
        grid_lay_1.setColumnStretch(0, 0)
        grid_lay_1.setColumnStretch(1, 1)
        grid_lay_1.setColumnStretch(2, 0)

        separator_line_1 = QtWidgets.QFrame()
        separator_line_1.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line_1.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay_1.addWidget(separator_line_1, 0, 0, 1, 3)

        grid_lay_1.addWidget(QtWidgets.QLabel(''))

        self.robber_bar_label = QtWidgets.QLabel('<b>%s</b>' % _('Robber Bar Parameters'))
        self.robber_bar_label.setToolTip(
            _("Parameters used for the robber bar.\n"
              "Robber bar = copper border to help in pattern hole plating.")
        )
        grid_lay_1.addWidget(self.robber_bar_label, 1, 0, 1, 3)

        # ROBBER BAR MARGIN #
        self.rb_margin_label = QtWidgets.QLabel('%s:' % _("Margin"))
        self.rb_margin_label.setToolTip(
            _("Bounding box margin for robber bar.")
        )
        self.rb_margin_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.rb_margin_entry.set_range(-9999.9999, 9999.9999)
        self.rb_margin_entry.set_precision(self.decimals)
        self.rb_margin_entry.setSingleStep(0.1)

        grid_lay_1.addWidget(self.rb_margin_label, 2, 0)
        grid_lay_1.addWidget(self.rb_margin_entry, 2, 1, 1, 2)

        # THICKNESS #
        self.rb_thickness_label = QtWidgets.QLabel('%s:' % _("Thickness"))
        self.rb_thickness_label.setToolTip(
            _("The robber bar thickness.")
        )
        self.rb_thickness_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.rb_thickness_entry.set_range(0.0000, 9999.9999)
        self.rb_thickness_entry.set_precision(self.decimals)
        self.rb_thickness_entry.setSingleStep(0.1)

        grid_lay_1.addWidget(self.rb_thickness_label, 3, 0)
        grid_lay_1.addWidget(self.rb_thickness_entry, 3, 1, 1, 2)

        # ## Insert Robber Bar
        self.rb_button = QtWidgets.QPushButton(_("Insert Robber Bar"))
        self.rb_button.setToolTip(
            _("Will add a polygon with a defined thickness\n"
              "that will surround the actual Gerber object\n"
              "at a certain distance.\n"
              "Required when doing holes pattern plating.")
        )
        self.rb_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)
        grid_lay_1.addWidget(self.rb_button, 4, 0, 1, 3)

        separator_line_2 = QtWidgets.QFrame()
        separator_line_2.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line_2.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay_1.addWidget(separator_line_2, 5, 0, 1, 3)

        self.patern_mask_label = QtWidgets.QLabel('<b>%s</b>' % _('Pattern Plating Mask'))
        self.patern_mask_label.setToolTip(
            _("Generate a mask for pattern plating.")
        )
        grid_lay_1.addWidget(self.patern_mask_label, 6, 0, 1, 3)

        self.sm_obj_label = QtWidgets.QLabel("%s:" % _("Select Soldermask object"))
        self.sm_obj_label.setToolTip(
            _("Gerber Object with the soldermask.\n"
              "It will be used as a base for\n"
              "the pattern plating mask.")
        )

        self.sm_object_combo = FCComboBox()
        self.sm_object_combo.setModel(self.app.collection)
        self.sm_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.sm_object_combo.is_last = True
        self.sm_object_combo.obj_type = 'Gerber'

        grid_lay_1.addWidget(self.sm_obj_label, 7, 0, 1, 3)
        grid_lay_1.addWidget(self.sm_object_combo, 8, 0, 1, 3)

        # Openings CLEARANCE #
        self.clearance_ppm_label = QtWidgets.QLabel('%s:' % _("Clearance"))
        self.clearance_ppm_label.setToolTip(
            _("The distance between the possible copper thieving elements\n"
              "and/or robber bar and the actual openings in the mask.")
        )
        self.clearance_ppm_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.clearance_ppm_entry.set_range(-9999.9999, 9999.9999)
        self.clearance_ppm_entry.set_precision(self.decimals)
        self.clearance_ppm_entry.setSingleStep(0.1)

        grid_lay_1.addWidget(self.clearance_ppm_label, 9, 0)
        grid_lay_1.addWidget(self.clearance_ppm_entry, 9, 1, 1, 2)

        # Plated area
        self.plated_area_label = QtWidgets.QLabel('%s:' % _("Plated area"))
        self.plated_area_label.setToolTip(
            _("The area to be plated by pattern plating.\n"
              "Basically is made from the openings in the plating mask.\n\n"
              "<<WARNING>> - the calculated area is actually a bit larger\n"
              "due of the fact that the soldermask openings are by design\n"
              "a bit larger than the copper pads, and this area is\n"
              "calculated from the soldermask openings.")
        )
        self.plated_area_entry = FCEntry()
        self.plated_area_entry.setDisabled(True)

        if self.units.upper() == 'MM':
            self.units_area_label = QtWidgets.QLabel('%s<sup>2</sup>' % _("mm"))
        else:
            self.units_area_label = QtWidgets.QLabel('%s<sup>2</sup>' % _("in"))

        grid_lay_1.addWidget(self.plated_area_label, 10, 0)
        grid_lay_1.addWidget(self.plated_area_entry, 10, 1)
        grid_lay_1.addWidget(self.units_area_label, 10, 2)

        # ## Pattern Plating Mask
        self.ppm_button = QtWidgets.QPushButton(_("Generate pattern plating mask"))
        self.ppm_button.setToolTip(
            _("Will add to the soldermask gerber geometry\n"
              "the geometries of the copper thieving and/or\n"
              "the robber bar if those were generated.")
        )
        self.ppm_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)
        grid_lay_1.addWidget(self.ppm_button, 11, 0, 1, 3)

        self.layout.addStretch()

        # ## Reset Tool
        self.reset_button = QtWidgets.QPushButton(_("Reset Tool"))
        self.reset_button.setToolTip(
            _("Will reset the tool parameters.")
        )
        self.reset_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)
        self.layout.addWidget(self.reset_button)

        # Objects involved in Copper thieving
        self.grb_object = None
        self.ref_obj = None
        self.sel_rect = []
        self.sm_object = None

        # store the flattened geometry here:
        self.flat_geometry = []

        # Events ID
        self.mr = None
        self.mm = None

        # Mouse cursor positions
        self.mouse_is_dragging = False
        self.cursor_pos = (0, 0)
        self.first_click = False

        self.area_method = False

        # Tool properties
        self.clearance_val = None
        self.margin_val = None
        self.geo_steps_per_circle = 128

        # Thieving geometry storage
        self.new_solid_geometry = []

        # Robber bar geometry storage
        self.robber_geo = None
        self.robber_line = None

        self.rb_thickness = None

        # SIGNALS
        self.ref_combo_type.currentIndexChanged.connect(self.on_ref_combo_type_change)
        self.reference_radio.group_toggle_fn = self.on_toggle_reference
        self.fill_type_radio.activated_custom.connect(self.on_thieving_type)

        self.fill_button.clicked.connect(self.execute)
        self.rb_button.clicked.connect(self.add_robber_bar)
        self.ppm_button.clicked.connect(self.on_add_ppm)
        self.reset_button.clicked.connect(self.set_tool_ui)

        self.work_finished.connect(self.on_new_pattern_plating_object)

    def run(self, toggle=True):
        self.app.report_usage("ToolCopperThieving()")

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

        self.app.ui.notebook.setTabText(2, _("Copper Thieving Tool"))

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, shortcut='Alt+F', **kwargs)

    def set_tool_ui(self):
        self.units = self.app.defaults['units']
        self.clearance_entry.set_value(float(self.app.defaults["tools_copper_thieving_clearance"]))
        self.margin_entry.set_value(float(self.app.defaults["tools_copper_thieving_margin"]))
        self.reference_radio.set_value(self.app.defaults["tools_copper_thieving_reference"])
        self.bbox_type_radio.set_value(self.app.defaults["tools_copper_thieving_box_type"])
        self.fill_type_radio.set_value(self.app.defaults["tools_copper_thieving_fill_type"])
        self.geo_steps_per_circle = int(self.app.defaults["tools_copper_thieving_circle_steps"])

        self.dot_dia_entry.set_value(self.app.defaults["tools_copper_thieving_dots_dia"])
        self.dot_spacing_entry.set_value(self.app.defaults["tools_copper_thieving_dots_spacing"])
        self.square_size_entry.set_value(self.app.defaults["tools_copper_thieving_squares_size"])
        self.squares_spacing_entry.set_value(self.app.defaults["tools_copper_thieving_squares_spacing"])
        self.line_size_entry.set_value(self.app.defaults["tools_copper_thieving_lines_size"])
        self.lines_spacing_entry.set_value(self.app.defaults["tools_copper_thieving_lines_spacing"])

        self.rb_margin_entry.set_value(self.app.defaults["tools_copper_thieving_rb_margin"])
        self.rb_thickness_entry.set_value(self.app.defaults["tools_copper_thieving_rb_thickness"])
        self.clearance_ppm_entry.set_value(self.app.defaults["tools_copper_thieving_mask_clearance"])

        # INIT SECTION
        self.area_method = False
        self.robber_geo = None
        self.robber_line = None
        self.new_solid_geometry = None

    def on_ref_combo_type_change(self):
        obj_type = self.ref_combo_type.currentIndex()
        self.ref_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.ref_combo.setCurrentIndex(0)
        self.ref_combo.obj_type = {
            _("Gerber"): "Gerber", _("Excellon"): "Excellon", _("Geometry"): "Geometry"
        }[self.ref_combo_type.get_value()]

    def on_toggle_reference(self):
        if self.reference_radio.get_value() == "itself" or self.reference_radio.get_value() == "area":
            self.ref_combo.hide()
            self.ref_combo_label.hide()
            self.ref_combo_type.hide()
            self.ref_combo_type_label.hide()
        else:
            self.ref_combo.show()
            self.ref_combo_label.show()
            self.ref_combo_type.show()
            self.ref_combo_type_label.show()

        if self.reference_radio.get_value() == "itself":
            self.bbox_type_label.show()
            self.bbox_type_radio.show()
        else:
            if self.fill_type_radio.get_value() == 'line':
                self.reference_radio.set_value('itself')
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("Lines Grid works only for 'itself' reference ..."))
                return

            self.bbox_type_label.hide()
            self.bbox_type_radio.hide()

    def on_thieving_type(self, choice):
        if choice == 'solid':
            self.dots_frame.hide()
            self.squares_frame.hide()
            self.lines_frame.hide()
            self.app.inform.emit(_("Solid fill selected."))
        elif choice == 'dot':
            self.dots_frame.show()
            self.squares_frame.hide()
            self.lines_frame.hide()
            self.app.inform.emit(_("Dots grid fill selected."))
        elif choice == 'square':
            self.dots_frame.hide()
            self.squares_frame.show()
            self.lines_frame.hide()
            self.app.inform.emit(_("Squares grid fill selected."))
        else:
            if self.reference_radio.get_value() != 'itself':
                self.reference_radio.set_value('itself')
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("Lines Grid works only for 'itself' reference ..."))
            self.dots_frame.hide()
            self.squares_frame.hide()
            self.lines_frame.show()

    def add_robber_bar(self):
        rb_margin = self.rb_margin_entry.get_value()
        self.rb_thickness = self.rb_thickness_entry.get_value()

        # get the Gerber object on which the Robber bar will be inserted
        selection_index = self.grb_object_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.grb_object_combo.rootModelIndex())

        try:
            self.grb_object = model_index.internalPointer().obj
        except Exception as e:
            log.debug("ToolCopperThieving.add_robber_bar() --> %s" % str(e))
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Gerber object loaded ..."))
            return 'fail'

        try:
            outline_pol = self.grb_object.solid_geometry.envelope
        except TypeError:
            outline_pol = MultiPolygon(self.grb_object.solid_geometry).envelope

        rb_distance = rb_margin + (self.rb_thickness / 2.0)
        self.robber_line = outline_pol.buffer(rb_distance).exterior

        self.robber_geo = self.robber_line.buffer(self.rb_thickness / 2.0)

        self.app.proc_container.update_view_text(' %s' % _("Append geometry"))

        aperture_found = None
        for ap_id, ap_val in self.grb_object.apertures.items():
            if ap_val['type'] == 'C' and ap_val['size'] == self.rb_thickness:
                aperture_found = ap_id
                break

        if aperture_found:
            geo_elem = {}
            geo_elem['solid'] = self.robber_geo
            geo_elem['follow'] = self.robber_line
            self.grb_object.apertures[aperture_found]['geometry'].append(deepcopy(geo_elem))
        else:
            ap_keys = list(self.grb_object.apertures.keys())
            if ap_keys:
                new_apid = str(int(max(ap_keys)) + 1)
            else:
                new_apid = '10'

            self.grb_object.apertures[new_apid] = {}
            self.grb_object.apertures[new_apid]['type'] = 'C'
            self.grb_object.apertures[new_apid]['size'] = self.rb_thickness
            self.grb_object.apertures[new_apid]['geometry'] = []

            geo_elem = {}
            geo_elem['solid'] = self.robber_geo
            geo_elem['follow'] = self.robber_line
            self.grb_object.apertures[new_apid]['geometry'].append(deepcopy(geo_elem))

        geo_obj = self.grb_object.solid_geometry
        if isinstance(geo_obj, MultiPolygon):
            s_list = []
            for pol in geo_obj.geoms:
                s_list.append(pol)
            s_list.append(self.robber_geo)
            geo_obj = MultiPolygon(s_list)
        elif isinstance(geo_obj, list):
            geo_obj.append(self.robber_geo)
        elif isinstance(geo_obj, Polygon):
            geo_obj = MultiPolygon([geo_obj, self.robber_geo])

        self.grb_object.solid_geometry = geo_obj

        self.app.proc_container.update_view_text(' %s' % _("Append source file"))
        # update the source file with the new geometry:
        self.grb_object.source_file = self.app.export_gerber(obj_name=self.grb_object.options['name'],
                                                             filename=None,
                                                             local_use=self.grb_object,
                                                             use_thread=False)
        self.app.proc_container.update_view_text(' %s' % '')
        self.on_exit()
        self.app.inform.emit('[success] %s' % _("Copper Thieving Tool done."))

    def execute(self):
        self.app.call_source = "copper_thieving_tool"

        self.clearance_val = self.clearance_entry.get_value()
        self.margin_val = self.margin_entry.get_value()
        reference_method = self.reference_radio.get_value()

        # get the Gerber object on which the Copper thieving will be inserted
        selection_index = self.grb_object_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.grb_object_combo.rootModelIndex())

        try:
            self.grb_object = model_index.internalPointer().obj
        except Exception as e:
            log.debug("ToolCopperThieving.execute() --> %s" % str(e))
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Gerber object loaded ..."))
            return 'fail'

        if reference_method == 'itself':
            bound_obj_name = self.grb_object_combo.currentText()

            # Get reference object.
            try:
                self.ref_obj = self.app.collection.get_by_name(bound_obj_name)
            except Exception as e:
                self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), str(e)))
                return "Could not retrieve object: %s" % self.obj_name

            self.on_copper_thieving(
                thieving_obj=self.grb_object,
                c_val=self.clearance_val,
                margin=self.margin_val
            )

        elif reference_method == 'area':
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Click the start point of the area."))

            self.area_method = True

            if self.app.is_legacy is False:
                self.app.plotcanvas.graph_event_disconnect('mouse_press', self.app.on_mouse_click_over_plot)
                self.app.plotcanvas.graph_event_disconnect('mouse_move', self.app.on_mouse_move_over_plot)
                self.app.plotcanvas.graph_event_disconnect('mouse_release', self.app.on_mouse_click_release_over_plot)
            else:
                self.app.plotcanvas.graph_event_disconnect(self.app.mp)
                self.app.plotcanvas.graph_event_disconnect(self.app.mm)
                self.app.plotcanvas.graph_event_disconnect(self.app.mr)

            self.mr = self.app.plotcanvas.graph_event_connect('mouse_release', self.on_mouse_release)
            self.mm = self.app.plotcanvas.graph_event_connect('mouse_move', self.on_mouse_move)

        elif reference_method == 'box':
            bound_obj_name = self.ref_combo.currentText()

            # Get reference object.
            try:
                self.ref_obj = self.app.collection.get_by_name(bound_obj_name)
            except Exception as e:
                self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), bound_obj_name))
                return "Could not retrieve object: %s. Error: %s" % (bound_obj_name, str(e))

            self.on_copper_thieving(
                thieving_obj=self.grb_object,
                ref_obj=self.ref_obj,
                c_val=self.clearance_val,
                margin=self.margin_val
            )

        # To be called after clicking on the plot.

    def on_mouse_release(self, event):
        if self.app.is_legacy is False:
            event_pos = event.pos
            # event_is_dragging = event.is_dragging
            right_button = 2
        else:
            event_pos = (event.xdata, event.ydata)
            # event_is_dragging = self.app.plotcanvas.is_dragging
            right_button = 3

        event_pos = self.app.plotcanvas.translate_coords(event_pos)

        # do clear area only for left mouse clicks
        if event.button == 1:
            if self.first_click is False:
                self.first_click = True
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("Click the end point of the filling area."))

                self.cursor_pos = self.app.plotcanvas.translate_coords(event_pos)
                if self.app.grid_status() is True:
                    self.cursor_pos = self.app.geo_editor.snap(event_pos[0], event_pos[1])
            else:
                self.app.inform.emit(_("Zone added. Click to start adding next zone or right click to finish."))
                self.app.delete_selection_shape()

                if self.app.grid_status() is True:
                    curr_pos = self.app.geo_editor.snap(event_pos[0], event_pos[1])
                else:
                    curr_pos = (event_pos[0], event_pos[1])

                x0, y0 = self.cursor_pos[0], self.cursor_pos[1]
                x1, y1 = curr_pos[0], curr_pos[1]
                pt1 = (x0, y0)
                pt2 = (x1, y0)
                pt3 = (x1, y1)
                pt4 = (x0, y1)

                new_rectangle = Polygon([pt1, pt2, pt3, pt4])
                self.sel_rect.append(new_rectangle)

                # add a temporary shape on canvas
                self.draw_tool_selection_shape(old_coords=(x0, y0), coords=(x1, y1))
                self.first_click = False
                return

        elif event.button == right_button and self.mouse_is_dragging is False:
            self.area_method = False
            self.first_click = False

            self.delete_tool_selection_shape()

            if self.app.is_legacy is False:
                self.app.plotcanvas.graph_event_disconnect('mouse_release', self.on_mouse_release)
                self.app.plotcanvas.graph_event_disconnect('mouse_move', self.on_mouse_move)
            else:
                self.app.plotcanvas.graph_event_disconnect(self.mr)
                self.app.plotcanvas.graph_event_disconnect(self.mm)

            self.app.mp = self.app.plotcanvas.graph_event_connect('mouse_press',
                                                                  self.app.on_mouse_click_over_plot)
            self.app.mm = self.app.plotcanvas.graph_event_connect('mouse_move',
                                                                  self.app.on_mouse_move_over_plot)
            self.app.mr = self.app.plotcanvas.graph_event_connect('mouse_release',
                                                                  self.app.on_mouse_click_release_over_plot)

            if len(self.sel_rect) == 0:
                return

            self.sel_rect = cascaded_union(self.sel_rect)

            if not isinstance(self.sel_rect, Iterable):
                self.sel_rect = [self.sel_rect]

            self.on_copper_thieving(
                thieving_obj=self.grb_object,
                ref_obj=self.sel_rect,
                c_val=self.clearance_val,
                margin=self.margin_val
            )

    # called on mouse move
    def on_mouse_move(self, event):
        if self.app.is_legacy is False:
            event_pos = event.pos
            event_is_dragging = event.is_dragging
            # right_button = 2
        else:
            event_pos = (event.xdata, event.ydata)
            event_is_dragging = self.app.plotcanvas.is_dragging
            # right_button = 3

        curr_pos = self.app.plotcanvas.translate_coords(event_pos)

        # detect mouse dragging motion
        if event_is_dragging is True:
            self.mouse_is_dragging = True
        else:
            self.mouse_is_dragging = False

        # update the cursor position
        if self.app.grid_status() is True:
            # Update cursor
            curr_pos = self.app.geo_editor.snap(curr_pos[0], curr_pos[1])

            self.app.app_cursor.set_data(np.asarray([(curr_pos[0], curr_pos[1])]),
                                         symbol='++', edge_color=self.app.cursor_color_3D,
                                         edge_width=self.app.defaults["global_cursor_width"],
                                         size=self.app.defaults["global_cursor_size"])

        # update the positions on status bar
        self.app.ui.position_label.setText("&nbsp;&nbsp;&nbsp;&nbsp;<b>X</b>: %.4f&nbsp;&nbsp;   "
                                           "<b>Y</b>: %.4f" % (curr_pos[0], curr_pos[1]))
        if self.cursor_pos is None:
            self.cursor_pos = (0, 0)

        self.app.dx = curr_pos[0] - float(self.cursor_pos[0])
        self.app.dy = curr_pos[1] - float(self.cursor_pos[1])
        self.app.ui.rel_position_label.setText("<b>Dx</b>: %.4f&nbsp;&nbsp;  <b>Dy</b>: "
                                               "%.4f&nbsp;&nbsp;&nbsp;&nbsp;" % (self.app.dx, self.app.dy))

        # draw the utility geometry
        if self.first_click:
            self.app.delete_selection_shape()
            self.app.draw_moving_selection_shape(old_coords=(self.cursor_pos[0], self.cursor_pos[1]),
                                                 coords=(curr_pos[0], curr_pos[1]))

    def on_copper_thieving(self, thieving_obj, ref_obj=None, c_val=None, margin=None, run_threaded=True):
        """

        :param thieving_obj:
        :param ref_obj:
        :param c_val:
        :param margin:
        :param run_threaded:
        :return:
        """

        if run_threaded:
            proc = self.app.proc_container.new('%s ...' % _("Thieving"))
        else:
            QtWidgets.QApplication.processEvents()

        self.app.proc_container.view.set_busy('%s ...' % _("Thieving"))

        # #####################################################################
        # ####### Read the parameters #########################################
        # #####################################################################

        log.debug("Copper Thieving Tool started. Reading parameters.")
        self.app.inform.emit(_("Copper Thieving Tool started. Reading parameters."))

        ref_selected = self.reference_radio.get_value()
        if c_val is None:
            c_val = float(self.app.defaults["tools_copperfill_clearance"])
        if margin is None:
            margin = float(self.app.defaults["tools_copperfill_margin"])

        fill_type = self.fill_type_radio.get_value()
        dot_dia = self.dot_dia_entry.get_value()
        dot_spacing = self.dot_spacing_entry.get_value()
        square_size = self.square_size_entry.get_value()
        square_spacing = self.squares_spacing_entry.get_value()
        line_size = self.line_size_entry.get_value()
        line_spacing = self.lines_spacing_entry.get_value()

        # make sure that the source object solid geometry is an Iterable
        if not isinstance(self.grb_object.solid_geometry, Iterable):
            self.grb_object.solid_geometry = [self.grb_object.solid_geometry]

        def job_thread_thieving(app_obj):
            # #########################################################################################
            # Prepare isolation polygon. This will create the clearance over the Gerber features ######
            # #########################################################################################
            log.debug("Copper Thieving Tool. Preparing isolation polygons.")
            app_obj.app.inform.emit(_("Copper Thieving Tool. Preparing isolation polygons."))

            # variables to display the percentage of work done
            geo_len = 0
            try:
                for pol in app_obj.grb_object.solid_geometry:
                    geo_len += 1
            except TypeError:
                geo_len = 1

            old_disp_number = 0
            pol_nr = 0

            clearance_geometry = []
            try:
                for pol in app_obj.grb_object.solid_geometry:
                    if app_obj.app.abort_flag:
                        # graceful abort requested by the user
                        raise FlatCAMApp.GracefulException

                    clearance_geometry.append(
                        pol.buffer(c_val, int(int(app_obj.geo_steps_per_circle) / 4))
                    )

                    pol_nr += 1
                    disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 100]))

                    if old_disp_number < disp_number <= 100:
                        app_obj.app.proc_container.update_view_text(' %s ... %d%%' %
                                                                    (_("Thieving"), int(disp_number)))
                        old_disp_number = disp_number
            except TypeError:
                # taking care of the case when the self.solid_geometry is just a single Polygon, not a list or a
                # MultiPolygon (not an iterable)
                clearance_geometry.append(
                    app_obj.grb_object.solid_geometry.buffer(c_val, int(int(app_obj.geo_steps_per_circle) / 4))
                )

            app_obj.app.proc_container.update_view_text(' %s ...' % _("Buffering"))
            clearance_geometry = unary_union(clearance_geometry)

            # #########################################################################################
            # Prepare the area to fill with copper. ###################################################
            # #########################################################################################
            log.debug("Copper Thieving Tool. Preparing areas to fill with copper.")
            app_obj.app.inform.emit(_("Copper Thieving Tool. Preparing areas to fill with copper."))

            try:
                if ref_obj is None or ref_obj == 'itself':
                    working_obj = thieving_obj
                else:
                    working_obj = ref_obj
            except Exception as e:
                log.debug("ToolCopperThieving.on_copper_thieving() --> %s" % str(e))
                return 'fail'

            app_obj.app.proc_container.update_view_text(' %s' % _("Working..."))
            if ref_selected == 'itself':
                geo_n = working_obj.solid_geometry

                try:
                    if app_obj.bbox_type_radio.get_value() == 'min':
                        if isinstance(geo_n, MultiPolygon):
                            env_obj = geo_n.convex_hull
                        elif (isinstance(geo_n, MultiPolygon) and len(geo_n) == 1) or \
                                (isinstance(geo_n, list) and len(geo_n) == 1) and isinstance(geo_n[0], Polygon):
                            env_obj = cascaded_union(geo_n)
                        else:
                            env_obj = cascaded_union(geo_n)
                            env_obj = env_obj.convex_hull
                        bounding_box = env_obj.buffer(distance=margin, join_style=base.JOIN_STYLE.mitre)
                    else:
                        if isinstance(geo_n, Polygon):
                            bounding_box = geo_n.buffer(distance=margin, join_style=base.JOIN_STYLE.mitre).exterior
                        elif isinstance(geo_n, list):
                            geo_n = unary_union(geo_n)
                            bounding_box = geo_n.buffer(distance=margin, join_style=base.JOIN_STYLE.mitre).exterior
                        elif isinstance(geo_n, MultiPolygon):
                            x0, y0, x1, y1 = geo_n.bounds
                            geo = box(x0, y0, x1, y1)
                            bounding_box = geo.buffer(distance=margin, join_style=base.JOIN_STYLE.mitre)
                        else:
                            app_obj.app.inform.emit(
                                '[ERROR_NOTCL] %s: %s' % (_("Geometry not supported for bounding box"), type(geo_n))
                            )
                            return 'fail'

                except Exception as e:
                    log.debug("ToolCopperFIll.on_copper_thieving()  'itself'  --> %s" % str(e))
                    app_obj.app.inform.emit('[ERROR_NOTCL] %s' % _("No object available."))
                    return 'fail'
            elif ref_selected == 'area':
                geo_buff_list = []
                try:
                    for poly in working_obj:
                        if app_obj.app.abort_flag:
                            # graceful abort requested by the user
                            raise FlatCAMApp.GracefulException
                        geo_buff_list.append(poly.buffer(distance=margin, join_style=base.JOIN_STYLE.mitre))
                except TypeError:
                    geo_buff_list.append(working_obj.buffer(distance=margin, join_style=base.JOIN_STYLE.mitre))

                bounding_box = MultiPolygon(geo_buff_list)
            else:   # ref_selected == 'box'
                geo_n = working_obj.solid_geometry

                if isinstance(working_obj, FlatCAMGeometry):
                    try:
                        __ = iter(geo_n)
                    except Exception as e:
                        log.debug("ToolCopperFIll.on_copper_thieving() 'box' --> %s" % str(e))
                        geo_n = [geo_n]

                    geo_buff_list = []
                    for poly in geo_n:
                        if app_obj.app.abort_flag:
                            # graceful abort requested by the user
                            raise FlatCAMApp.GracefulException
                        geo_buff_list.append(poly.buffer(distance=margin, join_style=base.JOIN_STYLE.mitre))

                    bounding_box = cascaded_union(geo_buff_list)
                elif isinstance(working_obj, FlatCAMGerber):
                    geo_n = cascaded_union(geo_n).convex_hull
                    bounding_box = cascaded_union(thieving_obj.solid_geometry).convex_hull.intersection(geo_n)
                    bounding_box = bounding_box.buffer(distance=margin, join_style=base.JOIN_STYLE.mitre)
                else:
                    app_obj.app.inform.emit('[ERROR_NOTCL] %s' % _("The reference object type is not supported."))
                    return 'fail'

            log.debug("Copper Thieving Tool. Finished creating areas to fill with copper.")

            app_obj.app.inform.emit(_("Copper Thieving Tool. Appending new geometry and buffering."))

            # #########################################################################################
            # ########## Generate filling geometry. ###################################################
            # #########################################################################################

            app_obj.new_solid_geometry = bounding_box.difference(clearance_geometry)

            # determine the bounding box polygon for the entire Gerber object to which we add copper thieving
            # if isinstance(geo_n, list):
            #     env_obj = unary_union(geo_n).buffer(distance=margin, join_style=base.JOIN_STYLE.mitre)
            # else:
            #     env_obj = geo_n.buffer(distance=margin, join_style=base.JOIN_STYLE.mitre)
            #
            # x0, y0, x1, y1 = env_obj.bounds
            # bounding_box = box(x0, y0, x1, y1)
            app_obj.app.proc_container.update_view_text(' %s' % _("Create geometry"))

            bounding_box = thieving_obj.solid_geometry.envelope.buffer(
                distance=margin,
                join_style=base.JOIN_STYLE.mitre
            )
            x0, y0, x1, y1 = bounding_box.bounds

            if fill_type == 'dot' or fill_type == 'square':
                # build the MultiPolygon of dots/squares that will fill the entire bounding box
                thieving_list = []

                if fill_type == 'dot':
                    radius = dot_dia / 2.0
                    new_x = x0 + radius
                    new_y = y0 + radius
                    while new_x <= x1 - radius:
                        while new_y <= y1 - radius:
                            dot_geo = Point((new_x, new_y)).buffer(radius, resolution=64)
                            thieving_list.append(dot_geo)
                            new_y += dot_dia + dot_spacing
                        new_x += dot_dia + dot_spacing
                        new_y = y0 + radius
                else:
                    h_size = square_size / 2.0
                    new_x = x0 + h_size
                    new_y = y0 + h_size
                    while new_x <= x1 - h_size:
                        while new_y <= y1 - h_size:
                            a, b, c, d = (Point((new_x, new_y)).buffer(h_size)).bounds
                            square_geo = box(a, b, c, d)
                            thieving_list.append(square_geo)
                            new_y += square_size + square_spacing
                        new_x += square_size + square_spacing
                        new_y = y0 + h_size

                thieving_box_geo = MultiPolygon(thieving_list)
                dx = bounding_box.centroid.x - thieving_box_geo.centroid.x
                dy = bounding_box.centroid.y - thieving_box_geo.centroid.y

                thieving_box_geo = affinity.translate(thieving_box_geo, xoff=dx, yoff=dy)

                try:
                    _it = iter(app_obj.new_solid_geometry)
                except TypeError:
                    app_obj.new_solid_geometry = [app_obj.new_solid_geometry]

                try:
                    _it = iter(thieving_box_geo)
                except TypeError:
                    thieving_box_geo = [thieving_box_geo]

                thieving_geo = []
                for dot_geo in thieving_box_geo:
                    for geo_t in app_obj.new_solid_geometry:
                        if dot_geo.within(geo_t):
                            thieving_geo.append(dot_geo)

                app_obj.new_solid_geometry = thieving_geo

            if fill_type == 'line':
                half_thick_line = line_size / 2.0

                # create a thick polygon-line that surrounds the copper features
                outline_geometry = []
                try:
                    for pol in app_obj.grb_object.solid_geometry:
                        if app_obj.app.abort_flag:
                            # graceful abort requested by the user
                            raise FlatCAMApp.GracefulException

                        outline_geometry.append(
                            pol.buffer(c_val+half_thick_line, int(int(app_obj.geo_steps_per_circle) / 4))
                        )

                        pol_nr += 1
                        disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 100]))

                        if old_disp_number < disp_number <= 100:
                            app_obj.app.proc_container.update_view_text(' %s ... %d%%' %
                                                                        (_("Buffering"), int(disp_number)))
                            old_disp_number = disp_number
                except TypeError:
                    # taking care of the case when the self.solid_geometry is just a single Polygon, not a list or a
                    # MultiPolygon (not an iterable)
                    outline_geometry.append(
                        app_obj.grb_object.solid_geometry.buffer(
                            c_val+half_thick_line,
                            int(int(app_obj.geo_steps_per_circle) / 4)
                        )
                    )

                app_obj.app.proc_container.update_view_text(' %s' % _("Buffering"))
                outline_geometry = unary_union(outline_geometry)

                outline_line = []
                try:
                    for geo_o in outline_geometry:
                        outline_line.append(
                            geo_o.exterior.buffer(
                                half_thick_line, resolution=int(int(app_obj.geo_steps_per_circle) / 4)
                            )
                        )
                except TypeError:
                    outline_line.append(
                        outline_geometry.exterior.buffer(
                            half_thick_line, resolution=int(int(app_obj.geo_steps_per_circle) / 4)
                        )
                    )

                outline_geometry = unary_union(outline_line)

                # create a polygon-line that surrounds in the inside the bounding box polygon of the target Gerber
                box_outline_geo = box(x0, y0, x1, y1).buffer(-half_thick_line)
                box_outline_geo_exterior = box_outline_geo.exterior
                box_outline_geometry = box_outline_geo_exterior.buffer(
                    half_thick_line,
                    resolution=int(int(app_obj.geo_steps_per_circle) / 4)
                )

                bx0, by0, bx1, by1 = box_outline_geo.bounds
                thieving_lines_geo = []
                new_x = bx0
                new_y = by0
                while new_x <= x1 - half_thick_line:
                    line_geo = LineString([(new_x, by0), (new_x, by1)]).buffer(
                        half_thick_line,
                        resolution=int(int(app_obj.geo_steps_per_circle) / 4)
                    )
                    thieving_lines_geo.append(line_geo)
                    new_x += line_size + line_spacing

                while new_y <= y1 - half_thick_line:
                    line_geo = LineString([(bx0, new_y), (bx1, new_y)]).buffer(
                        half_thick_line,
                        resolution=int(int(app_obj.geo_steps_per_circle) / 4)
                    )
                    thieving_lines_geo.append(line_geo)
                    new_y += line_size + line_spacing

                # merge everything together
                diff_lines_geo = []
                for line_poly in thieving_lines_geo:
                    rest_line = line_poly.difference(clearance_geometry)
                    diff_lines_geo.append(rest_line)
                app_obj.flatten([outline_geometry, box_outline_geometry, diff_lines_geo])
                app_obj.new_solid_geometry = app_obj.flat_geometry

            app_obj.app.proc_container.update_view_text(' %s' % _("Append geometry"))
            geo_list = app_obj.grb_object.solid_geometry
            if isinstance(app_obj.grb_object.solid_geometry, MultiPolygon):
                geo_list = list(app_obj.grb_object.solid_geometry.geoms)

            if '0' not in app_obj.grb_object.apertures:
                app_obj.grb_object.apertures['0'] = {}
                app_obj.grb_object.apertures['0']['geometry'] = []
                app_obj.grb_object.apertures['0']['type'] = 'REG'
                app_obj.grb_object.apertures['0']['size'] = 0.0

            try:
                for poly in app_obj.new_solid_geometry:
                    # append to the new solid geometry
                    geo_list.append(poly)

                    # append into the '0' aperture
                    geo_elem = {}
                    geo_elem['solid'] = poly
                    geo_elem['follow'] = poly.exterior
                    app_obj.grb_object.apertures['0']['geometry'].append(deepcopy(geo_elem))
            except TypeError:
                # append to the new solid geometry
                geo_list.append(app_obj.new_solid_geometry)

                # append into the '0' aperture
                geo_elem = {}
                geo_elem['solid'] = app_obj.new_solid_geometry
                geo_elem['follow'] = app_obj.new_solid_geometry.exterior
                app_obj.grb_object.apertures['0']['geometry'].append(deepcopy(geo_elem))

            app_obj.grb_object.solid_geometry = MultiPolygon(geo_list).buffer(0.0000001).buffer(-0.0000001)

            app_obj.app.proc_container.update_view_text(' %s' % _("Append source file"))
            # update the source file with the new geometry:
            app_obj.grb_object.source_file = app_obj.app.export_gerber(obj_name=app_obj.grb_object.options['name'],
                                                                       filename=None,
                                                                       local_use=app_obj.grb_object,
                                                                       use_thread=False)
            app_obj.app.proc_container.update_view_text(' %s' % '')
            app_obj.on_exit()
            app_obj.app.inform.emit('[success] %s' % _("Copper Thieving Tool done."))

        if run_threaded:
            self.app.worker_task.emit({'fcn': job_thread_thieving, 'params': [self]})
        else:
            job_thread_thieving(self)

    def on_add_ppm(self):
        run_threaded = True

        if run_threaded:
            proc = self.app.proc_container.new('%s ...' % _("P-Plating Mask"))
        else:
            QtWidgets.QApplication.processEvents()

        self.app.proc_container.view.set_busy('%s ...' % _("P-Plating Mask"))

        if run_threaded:
            self.app.worker_task.emit({'fcn': self.on_new_pattern_plating_object, 'params': []})
        else:
            self.on_new_pattern_plating_object()

    def on_new_pattern_plating_object(self):
        # get the Gerber object on which the Copper thieving will be inserted
        selection_index = self.sm_object_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.sm_object_combo.rootModelIndex())

        try:
            self.sm_object = model_index.internalPointer().obj
        except Exception as e:
            log.debug("ToolCopperThieving.on_add_ppm() --> %s" % str(e))
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Gerber object loaded ..."))
            return 'fail'

        ppm_clearance = self.clearance_ppm_entry.get_value()
        rb_thickness = self.rb_thickness

        self.app.proc_container.update_view_text(' %s' % _("Append PP-M geometry"))
        geo_list = self.sm_object.solid_geometry
        if isinstance(self.sm_object.solid_geometry, MultiPolygon):
            geo_list = list(self.sm_object.solid_geometry.geoms)

        # if the clearance is negative apply it to the original soldermask too
        if ppm_clearance < 0:
            temp_geo_list = []
            for geo in geo_list:
                temp_geo_list.append(geo.buffer(ppm_clearance))
            geo_list = temp_geo_list

        plated_area = 0.0
        for geo in geo_list:
            plated_area += geo.area

        if self.new_solid_geometry:
            for geo in self.new_solid_geometry:
                plated_area += geo.area
        if self.robber_geo:
            plated_area += self.robber_geo.area
        self.plated_area_entry.set_value(plated_area)

        thieving_solid_geo = self.new_solid_geometry
        robber_solid_geo = self.robber_geo
        robber_line = self.robber_line

        def obj_init(grb_obj, app_obj):
            grb_obj.multitool = False
            grb_obj.source_file = []
            grb_obj.multigeo = False
            grb_obj.follow = False
            grb_obj.apertures = {}
            grb_obj.solid_geometry = []

            # try:
            #     grb_obj.options['xmin'] = 0
            #     grb_obj.options['ymin'] = 0
            #     grb_obj.options['xmax'] = 0
            #     grb_obj.options['ymax'] = 0
            # except KeyError:
            #     pass

            # if we have copper thieving geometry, add it
            if thieving_solid_geo:
                if '0' not in grb_obj.apertures:
                    grb_obj.apertures['0'] = {}
                    grb_obj.apertures['0']['geometry'] = []
                    grb_obj.apertures['0']['type'] = 'REG'
                    grb_obj.apertures['0']['size'] = 0.0

                try:
                    for poly in thieving_solid_geo:
                        poly_b = poly.buffer(ppm_clearance)

                        # append to the new solid geometry
                        geo_list.append(poly_b)

                        # append into the '0' aperture
                        geo_elem = {}
                        geo_elem['solid'] = poly_b
                        geo_elem['follow'] = poly_b.exterior
                        grb_obj.apertures['0']['geometry'].append(deepcopy(geo_elem))
                except TypeError:
                    # append to the new solid geometry
                    geo_list.append(thieving_solid_geo.buffer(ppm_clearance))

                    # append into the '0' aperture
                    geo_elem = {}
                    geo_elem['solid'] = thieving_solid_geo.buffer(ppm_clearance)
                    geo_elem['follow'] = thieving_solid_geo.buffer(ppm_clearance).exterior
                    grb_obj.apertures['0']['geometry'].append(deepcopy(geo_elem))

            # if we have robber bar geometry, add it
            if robber_solid_geo:
                aperture_found = None
                for ap_id, ap_val in grb_obj.apertures.items():
                    if ap_val['type'] == 'C' and ap_val['size'] == app_obj.rb_thickness + ppm_clearance:
                        aperture_found = ap_id
                        break

                if aperture_found:
                    geo_elem = {}
                    geo_elem['solid'] = robber_solid_geo
                    geo_elem['follow'] = robber_line
                    grb_obj.apertures[aperture_found]['geometry'].append(deepcopy(geo_elem))
                else:
                    ap_keys = list(grb_obj.apertures.keys())
                    max_apid = int(max(ap_keys))
                    if ap_keys and max_apid != 0:
                        new_apid = str(max_apid + 1)
                    else:
                        new_apid = '10'

                    grb_obj.apertures[new_apid] = {}
                    grb_obj.apertures[new_apid]['type'] = 'C'
                    grb_obj.apertures[new_apid]['size'] = rb_thickness + ppm_clearance
                    grb_obj.apertures[new_apid]['geometry'] = []

                    geo_elem = {}
                    geo_elem['solid'] = robber_solid_geo.buffer(ppm_clearance)
                    geo_elem['follow'] = Polygon(robber_line).buffer(ppm_clearance / 2.0).exterior
                    grb_obj.apertures[new_apid]['geometry'].append(deepcopy(geo_elem))

                geo_list.append(robber_solid_geo.buffer(ppm_clearance))

            grb_obj.solid_geometry = MultiPolygon(geo_list).buffer(0.0000001).buffer(-0.0000001)

            app_obj.proc_container.update_view_text(' %s' % _("Append source file"))
            # update the source file with the new geometry:
            grb_obj.source_file = app_obj.export_gerber(obj_name=name,
                                                        filename=None,
                                                        local_use=grb_obj,
                                                        use_thread=False)
            app_obj.proc_container.update_view_text(' %s' % '')

        # Object name
        obj_name, separatpr, obj_extension = self.sm_object.options['name'].rpartition('.')
        name = '%s_%s.%s' % (obj_name, 'plating_mask', obj_extension)

        self.app.new_object('gerber', name, obj_init, autoselected=False)

        # Register recent file
        self.app.file_opened.emit("gerber", name)

        self.on_exit()
        self.app.inform.emit('[success] %s' % _("Generating Pattern Plating Mask done."))

    def replot(self, obj):
        def worker_task():
            with self.app.proc_container.new('%s...' % _("Plotting")):
                obj.plot()

        self.app.worker_task.emit({'fcn': worker_task, 'params': []})

    def on_exit(self):
        # plot the objects
        if self.grb_object:
            self.replot(obj=self.grb_object)

        if self.sm_object:
            self.replot(obj=self.sm_object)

        # update the bounding box values
        try:
            a, b, c, d = self.grb_object.bounds()
            self.grb_object.options['xmin'] = a
            self.grb_object.options['ymin'] = b
            self.grb_object.options['xmax'] = c
            self.grb_object.options['ymax'] = d
        except Exception as e:
            log.debug("ToolCopperThieving.on_exit() bounds -> copper thieving Gerber error --> %s" % str(e))

        # update the bounding box values
        try:
            a, b, c, d = self.sm_object.bounds()
            self.sm_object.options['xmin'] = a
            self.sm_object.options['ymin'] = b
            self.sm_object.options['xmax'] = c
            self.sm_object.options['ymax'] = d
        except Exception as e:
            log.debug("ToolCopperThieving.on_exit() bounds -> pattern plating mask error --> %s" % str(e))

        # reset the variables
        self.grb_object = None
        self.sm_object = None
        self.ref_obj = None
        self.sel_rect = []

        # Events ID
        self.mr = None
        self.mm = None

        # Mouse cursor positions
        self.mouse_is_dragging = False
        self.cursor_pos = (0, 0)
        self.first_click = False

        # if True it means we exited from tool in the middle of area adding therefore disconnect the events
        if self.area_method is True:
            self.app.delete_selection_shape()
            self.area_method = False

            if self.app.is_legacy is False:
                self.app.plotcanvas.graph_event_disconnect('mouse_release', self.on_mouse_release)
                self.app.plotcanvas.graph_event_disconnect('mouse_move', self.on_mouse_move)
            else:
                self.app.plotcanvas.graph_event_disconnect(self.mr)
                self.app.plotcanvas.graph_event_disconnect(self.mm)

            self.app.mp = self.app.plotcanvas.graph_event_connect('mouse_press',
                                                                  self.app.on_mouse_click_over_plot)
            self.app.mm = self.app.plotcanvas.graph_event_connect('mouse_move',
                                                                  self.app.on_mouse_move_over_plot)
            self.app.mr = self.app.plotcanvas.graph_event_connect('mouse_release',
                                                                  self.app.on_mouse_click_release_over_plot)

        self.app.call_source = "app"
        self.app.inform.emit('[success] %s' % _("Copper Thieving Tool exit."))

    def flatten(self, geometry):
        """
        Creates a list of non-iterable linear geometry objects.
        :param geometry: Shapely type or list or list of list of such.

        Results are placed in self.flat_geometry
        """

        # ## If iterable, expand recursively.
        try:
            for geo in geometry:
                if geo is not None:
                    self.flatten(geometry=geo)

        # ## Not iterable, do the actual indexing and add.
        except TypeError:
            self.flat_geometry.append(geometry)

        return self.flat_geometry
