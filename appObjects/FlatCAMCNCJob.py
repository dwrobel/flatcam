# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
# ##########################################################

# ##########################################################
# File modified by: Marius Stanciu                         #
# ##########################################################

from copy import deepcopy
from io import StringIO
from datetime import datetime

from appEditors.AppTextEditor import AppTextEditor
from appObjects.FlatCAMObj import *

from matplotlib.backend_bases import KeyEvent as mpl_key_event

from camlib import CNCjob

from shapely.ops import unary_union
from shapely.geometry import Point, MultiPoint, Polygon, LineString, box
import shapely.affinity as affinity
try:
    from shapely.ops import voronoi_diagram
    VORONOI_ENABLED = True
    # from appCommon.Common import voronoi_diagram
except Exception:
    VORONOI_ENABLED = False

import os
import sys
import time
import serial
import glob
import math
import numpy as np
import random

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class CNCJobObject(FlatCAMObj, CNCjob):
    """
    Represents G-Code.
    """
    optionChanged = QtCore.pyqtSignal(str)
    build_al_table_sig = QtCore.pyqtSignal()

    ui_type = CNCObjectUI

    def __init__(self, name, units="in", kind="generic", z_move=0.1,
                 feedrate=3.0, feedrate_rapid=3.0, z_cut=-0.002, tooldia=0.0,
                 spindlespeed=None):

        log.debug("Creating CNCJob object...")

        self.decimals = self.app.decimals

        CNCjob.__init__(self, units=units, kind=kind, z_move=z_move,
                        feedrate=feedrate, feedrate_rapid=feedrate_rapid, z_cut=z_cut, tooldia=tooldia,
                        spindlespeed=spindlespeed, steps_per_circle=int(self.app.defaults["cncjob_steps_per_circle"]))

        FlatCAMObj.__init__(self, name)

        self.kind = "cncjob"

        self.options.update({
            "plot": True,
            "tooldia": 0.03937,  # 0.4mm in inches
            "append": "",
            "prepend": "",
            "dwell": False,
            "dwelltime": 1,
            "type": 'Geometry',
            # "toolchange_macro": '',
            # "toolchange_macro_enable": False
        })

        '''
            This is a dict of dictionaries. Each dict is associated with a tool present in the file. The key is the 
            diameter of the tools and the value is another dict that will hold the data under the following form:
               {tooldia:   {
                           'tooluid': 1,
                           'offset': 'Path',
                           'type_item': 'Rough',
                           'tool_type': 'C1',
                           'data': {} # a dict to hold the parameters
                           'gcode': "" # a string with the actual GCODE
                           'gcode_parsed': {} # dictionary holding the CNCJob geometry and type of geometry 
                           (cut or move)
                           'solid_geometry': []
                           },
                           ...
               }
            It is populated in the GeometryObject.mtool_gen_cncjob()
            BEWARE: I rely on the ordered nature of the Python 3.7 dictionary. Things might change ...
        '''
        self.cnc_tools = {}

        '''
           This is a dict of dictionaries. Each dict is associated with a tool present in the file. The key is the 
           diameter of the tools and the value is another dict that will hold the data under the following form:
              {tooldia:   {
                          'tool': int,
                          'nr_drills': int,
                          'nr_slots': int,
                          'offset': float,
                          'data': {},           a dict to hold the parameters
                          'gcode': "",          a string with the actual GCODE
                          'gcode_parsed': [],   list of dicts holding the CNCJob geometry and 
                                                type of geometry (cut or move)
                          'solid_geometry': [],
                          },
                          ...
              }
           It is populated in the ExcellonObject.on_create_cncjob_click() but actually 
           it's done in camlib.CNCJob.generate_from_excellon_by_tool()
           BEWARE: I rely on the ordered nature of the Python 3.7 dictionary. Things might change ...
       '''
        self.exc_cnc_tools = {}

        # flag to store if the CNCJob is part of a special group of CNCJob objects that can't be processed by the
        # default engine of FlatCAM. They generated by some of tools and are special cases of CNCJob objects.
        self.special_group = None

        # for now it show if the plot will be done for multi-tool CNCJob (True) or for single tool
        # (like the one in the TCL Command), False
        self.multitool = False

        # determine if the GCode was generated out of a Excellon object or a Geometry object
        self.origin_kind = None

        self.coords_decimals = 4
        self.fr_decimals = 2

        self.annotations_dict = {}

        # used for parsing the GCode lines to adjust the GCode when the GCode is offseted or scaled
        gcodex_re_string = r'(?=.*(X[-\+]?\d*\.\d*))'
        self.g_x_re = re.compile(gcodex_re_string)
        gcodey_re_string = r'(?=.*(Y[-\+]?\d*\.\d*))'
        self.g_y_re = re.compile(gcodey_re_string)
        gcodez_re_string = r'(?=.*(Z[-\+]?\d*\.\d*))'
        self.g_z_re = re.compile(gcodez_re_string)

        gcodef_re_string = r'(?=.*(F[-\+]?\d*\.\d*))'
        self.g_f_re = re.compile(gcodef_re_string)
        gcodet_re_string = r'(?=.*(\=\s*[-\+]?\d*\.\d*))'
        self.g_t_re = re.compile(gcodet_re_string)

        gcodenr_re_string = r'([+-]?\d*\.\d+)'
        self.g_nr_re = re.compile(gcodenr_re_string)

        if self.app.is_legacy is False:
            self.text_col = self.app.plotcanvas.new_text_collection()
            self.text_col.enabled = True
            self.annotation = self.app.plotcanvas.new_text_group(collection=self.text_col)

        self.gcode_editor_tab = None
        self.gcode_viewer_tab = None

        self.source_file = ''
        self.units_found = self.app.defaults['units']
        self.probing_gcode_text = ''
        self.grbl_probe_result = ''

        # store the current selection shape status to be restored after manual adding test points
        self.old_selection_state = self.app.defaults['global_selection_shape']

        # if mouse is dragging set the object True
        self.mouse_is_dragging = False

        # if mouse events are bound to local methods
        self.mouse_events_connected = False

        # event handlers references
        self.kp = None
        self.mm = None
        self.mr = None

        self.prepend_snippet = ''
        self.append_snippet = ''
        self.gc_header = self.gcode_header()
        self.gc_start = ''
        self.gc_end = ''

        '''
        dictionary of dictionaries to store the information's for the autolevelling
        format when using Voronoi diagram:
        {
            id: {
                    'point': Shapely Point
                    'geo': Shapely Polygon from Voronoi diagram,
                    'height': float
                }
        }
        '''
        self.al_voronoi_geo_storage = {}

        '''
        list of (x, y, x) tuples to store the information's for the autolevelling
        format when using bilinear interpolation:
        [(x0, y0, z0), (x1, y1, z1), ...]
        '''
        self.al_bilinear_geo_storage = []

        self.solid_geo = None
        self.grbl_ser_port = None

        self.pressed_button = None

        if self.app.is_legacy is False:
            self.probing_shapes = ShapeCollection(parent=self.app.plotcanvas.view.scene, layers=1)
        else:
            self.probing_shapes = ShapeCollectionLegacy(obj=self, app=self.app, name=name + "_probing_shapes")

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from predecessors.
        self.ser_attrs += [
            'options', 'kind', 'origin_kind', 'cnc_tools', 'exc_cnc_tools', 'multitool', 'append_snippet',
            'prepend_snippet', 'gc_header'
        ]

    def build_ui(self):
        self.ui_disconnect()

        # FIXME: until Shapely 1.8 comes this is disabled
        self.ui.sal_btn.setChecked(False)
        self.ui.sal_btn.setDisabled(True)
        self.ui.sal_btn.setToolTip("DISABLED. Work in progress!")

        FlatCAMObj.build_ui(self)
        self.units = self.app.defaults['units'].upper()

        # if the FlatCAM object is Excellon don't build the CNC Tools Table but hide it
        self.ui.cnc_tools_table.hide()
        if self.cnc_tools:
            self.ui.cnc_tools_table.show()
            self.build_cnc_tools_table()

        self.ui.exc_cnc_tools_table.hide()
        if self.exc_cnc_tools:
            self.ui.exc_cnc_tools_table.show()
            self.build_excellon_cnc_tools()

        if self.ui.sal_btn.isChecked():
            self.build_al_table()

        self.ui_connect()

    def build_cnc_tools_table(self):
        tool_idx = 0

        n = len(self.cnc_tools)
        self.ui.cnc_tools_table.setRowCount(n)

        for dia_key, dia_value in self.cnc_tools.items():

            tool_idx += 1
            row_no = tool_idx - 1

            t_id = QtWidgets.QTableWidgetItem('%d' % int(tool_idx))
            # id.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.ui.cnc_tools_table.setItem(row_no, 0, t_id)  # Tool name/id

            # Make sure that the tool diameter when in MM is with no more than 2 decimals.
            # There are no tool bits in MM with more than 2 decimals diameter.
            # For INCH the decimals should be no more than 4. There are no tools under 10mils.

            dia_item = QtWidgets.QTableWidgetItem('%.*f' % (self.decimals, float(dia_value['tooldia'])))

            offset_txt = list(str(dia_value['offset']))
            offset_txt[0] = offset_txt[0].upper()
            offset_item = QtWidgets.QTableWidgetItem(''.join(offset_txt))
            type_item = QtWidgets.QTableWidgetItem(str(dia_value['type']))
            tool_type_item = QtWidgets.QTableWidgetItem(str(dia_value['tool_type']))

            t_id.setFlags(QtCore.Qt.ItemIsEnabled)
            dia_item.setFlags(QtCore.Qt.ItemIsEnabled)
            offset_item.setFlags(QtCore.Qt.ItemIsEnabled)
            type_item.setFlags(QtCore.Qt.ItemIsEnabled)
            tool_type_item.setFlags(QtCore.Qt.ItemIsEnabled)

            # hack so the checkbox stay centered in the table cell
            # used this:
            # https://stackoverflow.com/questions/32458111/pyqt-allign-checkbox-and-put-it-in-every-row
            # plot_item = QtWidgets.QWidget()
            # checkbox = FCCheckBox()
            # checkbox.setCheckState(QtCore.Qt.Checked)
            # qhboxlayout = QtWidgets.QHBoxLayout(plot_item)
            # qhboxlayout.addWidget(checkbox)
            # qhboxlayout.setAlignment(QtCore.Qt.AlignCenter)
            # qhboxlayout.setContentsMargins(0, 0, 0, 0)
            plot_item = FCCheckBox()
            plot_item.setLayoutDirection(QtCore.Qt.RightToLeft)
            tool_uid_item = QtWidgets.QTableWidgetItem(str(dia_key))
            if self.ui.plot_cb.isChecked():
                plot_item.setChecked(True)

            self.ui.cnc_tools_table.setItem(row_no, 1, dia_item)  # Diameter
            self.ui.cnc_tools_table.setItem(row_no, 2, offset_item)  # Offset
            self.ui.cnc_tools_table.setItem(row_no, 3, type_item)  # Toolpath Type
            self.ui.cnc_tools_table.setItem(row_no, 4, tool_type_item)  # Tool Type

            # ## REMEMBER: THIS COLUMN IS HIDDEN IN OBJECTUI.PY # ##
            self.ui.cnc_tools_table.setItem(row_no, 5, tool_uid_item)  # Tool unique ID)
            self.ui.cnc_tools_table.setCellWidget(row_no, 6, plot_item)

        # make the diameter column editable
        # for row in range(tool_idx):
        #     self.ui.cnc_tools_table.item(row, 1).setFlags(QtCore.Qt.ItemIsSelectable |
        #                                                   QtCore.Qt.ItemIsEnabled)

        for row in range(tool_idx):
            self.ui.cnc_tools_table.item(row, 0).setFlags(
                self.ui.cnc_tools_table.item(row, 0).flags() ^ QtCore.Qt.ItemIsSelectable)

        self.ui.cnc_tools_table.resizeColumnsToContents()
        self.ui.cnc_tools_table.resizeRowsToContents()

        vertical_header = self.ui.cnc_tools_table.verticalHeader()
        # vertical_header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        vertical_header.hide()
        self.ui.cnc_tools_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        horizontal_header = self.ui.cnc_tools_table.horizontalHeader()
        horizontal_header.setMinimumSectionSize(10)
        horizontal_header.setDefaultSectionSize(70)
        horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(0, 20)
        horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        horizontal_header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(4, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(4, 40)
        horizontal_header.setSectionResizeMode(6, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(4, 17)
        # horizontal_header.setStretchLastSection(True)
        self.ui.cnc_tools_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.ui.cnc_tools_table.setColumnWidth(0, 20)
        self.ui.cnc_tools_table.setColumnWidth(4, 40)
        self.ui.cnc_tools_table.setColumnWidth(6, 17)

        # self.ui.geo_tools_table.setSortingEnabled(True)

        self.ui.cnc_tools_table.setMinimumHeight(self.ui.cnc_tools_table.getHeight())
        self.ui.cnc_tools_table.setMaximumHeight(self.ui.cnc_tools_table.getHeight())

    def build_excellon_cnc_tools(self):
        tool_idx = 0

        n = len(self.exc_cnc_tools)
        self.ui.exc_cnc_tools_table.setRowCount(n)

        for tooldia_key, dia_value in self.exc_cnc_tools.items():

            tool_idx += 1
            row_no = tool_idx - 1

            t_id = QtWidgets.QTableWidgetItem('%d' % int(tool_idx))
            dia_item = QtWidgets.QTableWidgetItem('%.*f' % (self.decimals, float(tooldia_key)))
            nr_drills_item = QtWidgets.QTableWidgetItem('%d' % int(dia_value['nr_drills']))
            nr_slots_item = QtWidgets.QTableWidgetItem('%d' % int(dia_value['nr_slots']))
            try:
                offset_val = self.app.dec_format(float(dia_value['offset']), self.decimals) + self.z_cut
            except KeyError:
                offset_val = self.app.dec_format(float(dia_value['offset_z']), self.decimals) + self.z_cut

            cutz_item = QtWidgets.QTableWidgetItem('%f' % offset_val)

            t_id.setFlags(QtCore.Qt.ItemIsEnabled)
            dia_item.setFlags(QtCore.Qt.ItemIsEnabled)
            nr_drills_item.setFlags(QtCore.Qt.ItemIsEnabled)
            nr_slots_item.setFlags(QtCore.Qt.ItemIsEnabled)
            cutz_item.setFlags(QtCore.Qt.ItemIsEnabled)

            # hack so the checkbox stay centered in the table cell
            # used this:
            # https://stackoverflow.com/questions/32458111/pyqt-allign-checkbox-and-put-it-in-every-row
            # plot_item = QtWidgets.QWidget()
            # checkbox = FCCheckBox()
            # checkbox.setCheckState(QtCore.Qt.Checked)
            # qhboxlayout = QtWidgets.QHBoxLayout(plot_item)
            # qhboxlayout.addWidget(checkbox)
            # qhboxlayout.setAlignment(QtCore.Qt.AlignCenter)
            # qhboxlayout.setContentsMargins(0, 0, 0, 0)

            plot_item = FCCheckBox()
            plot_item.setLayoutDirection(QtCore.Qt.RightToLeft)
            tool_uid_item = QtWidgets.QTableWidgetItem(str(dia_value['tool']))
            if self.ui.plot_cb.isChecked():
                plot_item.setChecked(True)

            self.ui.exc_cnc_tools_table.setItem(row_no, 0, t_id)  # Tool name/id
            self.ui.exc_cnc_tools_table.setItem(row_no, 1, dia_item)  # Diameter
            self.ui.exc_cnc_tools_table.setItem(row_no, 2, nr_drills_item)  # Nr of drills
            self.ui.exc_cnc_tools_table.setItem(row_no, 3, nr_slots_item)  # Nr of slots

            # ## REMEMBER: THIS COLUMN IS HIDDEN IN OBJECTUI.PY # ##
            self.ui.exc_cnc_tools_table.setItem(row_no, 4, tool_uid_item)  # Tool unique ID)
            self.ui.exc_cnc_tools_table.setItem(row_no, 5, cutz_item)
            self.ui.exc_cnc_tools_table.setCellWidget(row_no, 6, plot_item)

        for row in range(tool_idx):
            self.ui.exc_cnc_tools_table.item(row, 0).setFlags(
                self.ui.exc_cnc_tools_table.item(row, 0).flags() ^ QtCore.Qt.ItemIsSelectable)

        self.ui.exc_cnc_tools_table.resizeColumnsToContents()
        self.ui.exc_cnc_tools_table.resizeRowsToContents()

        vertical_header = self.ui.exc_cnc_tools_table.verticalHeader()
        vertical_header.hide()
        self.ui.exc_cnc_tools_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        horizontal_header = self.ui.exc_cnc_tools_table.horizontalHeader()
        horizontal_header.setMinimumSectionSize(10)
        horizontal_header.setDefaultSectionSize(70)
        horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(0, 20)
        horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        horizontal_header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeToContents)

        horizontal_header.setSectionResizeMode(6, QtWidgets.QHeaderView.Fixed)

        # horizontal_header.setStretchLastSection(True)
        self.ui.exc_cnc_tools_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.ui.exc_cnc_tools_table.setColumnWidth(0, 20)
        self.ui.exc_cnc_tools_table.setColumnWidth(6, 17)

        self.ui.exc_cnc_tools_table.setMinimumHeight(self.ui.exc_cnc_tools_table.getHeight())
        self.ui.exc_cnc_tools_table.setMaximumHeight(self.ui.exc_cnc_tools_table.getHeight())

    def build_al_table(self):
        tool_idx = 0

        n = len(self.al_voronoi_geo_storage)
        self.ui.al_probe_points_table.setRowCount(n)

        for id_key, value in self.al_voronoi_geo_storage.items():
            tool_idx += 1
            row_no = tool_idx - 1

            t_id = QtWidgets.QTableWidgetItem('%d' % int(tool_idx))
            x = value['point'].x
            y = value['point'].y
            xy_coords = self.app.dec_format(x, dec=self.app.decimals), self.app.dec_format(y, dec=self.app.decimals)
            coords_item = QtWidgets.QTableWidgetItem(str(xy_coords))
            height = self.app.dec_format(value['height'], dec=self.app.decimals)
            height_item = QtWidgets.QTableWidgetItem(str(height))

            t_id.setFlags(QtCore.Qt.ItemIsEnabled)
            coords_item.setFlags(QtCore.Qt.ItemIsEnabled)
            height_item.setFlags(QtCore.Qt.ItemIsEnabled)

            self.ui.al_probe_points_table.setItem(row_no, 0, t_id)  # Tool name/id
            self.ui.al_probe_points_table.setItem(row_no, 1, coords_item)  # X-Y coords
            self.ui.al_probe_points_table.setItem(row_no, 2, height_item)  # Determined Height

        self.ui.al_probe_points_table.resizeColumnsToContents()
        self.ui.al_probe_points_table.resizeRowsToContents()

        h_header = self.ui.al_probe_points_table.horizontalHeader()
        h_header.setMinimumSectionSize(10)
        h_header.setDefaultSectionSize(70)
        h_header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        h_header.resizeSection(0, 20)
        h_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        h_header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)

        self.ui.al_probe_points_table.setMinimumHeight(self.ui.al_probe_points_table.getHeight())
        self.ui.al_probe_points_table.setMaximumHeight(self.ui.al_probe_points_table.getHeight())

        if self.ui.al_probe_points_table.model().rowCount():
            self.ui.grbl_get_heightmap_button.setDisabled(False)
            self.ui.grbl_save_height_map_button.setDisabled(False)
            self.ui.h_gcode_button.setDisabled(False)
            self.ui.view_h_gcode_button.setDisabled(False)
        else:
            self.ui.grbl_get_heightmap_button.setDisabled(True)
            self.ui.grbl_save_height_map_button.setDisabled(True)
            self.ui.h_gcode_button.setDisabled(True)
            self.ui.view_h_gcode_button.setDisabled(True)

    def set_ui(self, ui):
        FlatCAMObj.set_ui(self, ui)

        log.debug("FlatCAMCNCJob.set_ui()")

        assert isinstance(self.ui, CNCObjectUI), \
            "Expected a CNCObjectUI, got %s" % type(self.ui)

        self.units = self.app.defaults['units'].upper()
        self.units_found = self.app.defaults['units']

        # this signal has to be connected to it's slot before the defaults are populated
        # the decision done in the slot has to override the default value set below
        # self.ui.toolchange_cb.toggled.connect(self.on_toolchange_custom_clicked)

        self.form_fields.update({
            "plot":             self.ui.plot_cb,
            "tooldia":          self.ui.tooldia_entry,
            # "append":         self.ui.append_text,
            # "prepend":        self.ui.prepend_text,
            # "toolchange_macro": self.ui.toolchange_text,
            # "toolchange_macro_enable": self.ui.toolchange_cb,
            "al_travelz":       self.ui.ptravelz_entry,
            "al_probe_depth":   self.ui.pdepth_entry,
            "al_probe_fr":      self.ui.feedrate_probe_entry,
            "al_controller":    self.ui.al_controller_combo,
            "al_method":        self.ui.al_method_radio,
            "al_mode":          self.ui.al_mode_radio,
            "al_rows":          self.ui.al_rows_entry,
            "al_columns":       self.ui.al_columns_entry,
            "al_grbl_jog_step": self.ui.jog_step_entry,
            "al_grbl_jog_fr":   self.ui.jog_fr_entry,
        })

        self.append_snippet = self.app.defaults['cncjob_append']
        self.prepend_snippet = self.app.defaults['cncjob_prepend']

        if self.append_snippet != '' or self.prepend_snippet != '':
            self.ui.snippets_cb.set_value(True)

        # Fill form fields only on object create
        self.to_form()

        # this means that the object that created this CNCJob was an Excellon or Geometry
        try:
            if self.travel_distance:
                self.ui.t_distance_label.show()
                self.ui.t_distance_entry.setVisible(True)
                self.ui.t_distance_entry.setDisabled(True)
                self.ui.t_distance_entry.set_value('%.*f' % (self.decimals, float(self.travel_distance)))
                self.ui.units_label.setText(str(self.units).lower())
                self.ui.units_label.setDisabled(True)

                self.ui.t_time_label.show()
                self.ui.t_time_entry.setVisible(True)
                self.ui.t_time_entry.setDisabled(True)
                # if time is more than 1 then we have minutes, else we have seconds
                if self.routing_time > 1:
                    self.ui.t_time_entry.set_value('%.*f' % (self.decimals, math.ceil(float(self.routing_time))))
                    self.ui.units_time_label.setText('min')
                else:
                    time_r = self.routing_time * 60
                    self.ui.t_time_entry.set_value('%.*f' % (self.decimals, math.ceil(float(time_r))))
                    self.ui.units_time_label.setText('sec')
                self.ui.units_time_label.setDisabled(True)
        except AttributeError:
            pass

        if self.multitool is False:
            self.ui.tooldia_entry.show()
            self.ui.updateplot_button.show()
        else:
            self.ui.tooldia_entry.hide()
            self.ui.updateplot_button.hide()

        # set the kind of geometries are plotted by default with plot2() from camlib.CNCJob
        self.ui.cncplot_method_combo.set_value(self.app.defaults["cncjob_plot_kind"])

        try:
            self.ui.annotation_cb.stateChanged.disconnect(self.on_annotation_change)
        except (TypeError, AttributeError):
            pass
        self.ui.annotation_cb.stateChanged.connect(self.on_annotation_change)

        # set if to display text annotations
        self.ui.annotation_cb.set_value(self.app.defaults["cncjob_annotation"])

        self.ui.updateplot_button.clicked.connect(self.on_updateplot_button_click)
        self.ui.export_gcode_button.clicked.connect(self.on_exportgcode_button_click)
        self.ui.review_gcode_button.clicked.connect(self.on_review_code_click)

        # Editor Signal
        self.ui.editor_button.clicked.connect(lambda: self.app.object2editor())

        # Properties
        self.ui.properties_button.toggled.connect(self.on_properties)
        self.calculations_finished.connect(self.update_area_chull)

        # autolevelling signals
        self.ui.sal_btn.toggled.connect(self.on_toggle_autolevelling)
        self.ui.al_mode_radio.activated_custom.connect(self.on_mode_radio)
        self.ui.al_method_radio.activated_custom.connect(self.on_method_radio)
        self.ui.al_controller_combo.currentIndexChanged.connect(self.on_controller_change)
        self.ui.plot_probing_pts_cb.stateChanged.connect(self.show_probing_geo)
        # GRBL
        self.ui.com_search_button.clicked.connect(self.on_grbl_search_ports)
        self.ui.add_bd_button.clicked.connect(self.on_grbl_add_baudrate)
        self.ui.del_bd_button.clicked.connect(self.on_grbl_delete_baudrate_grbl)
        self.ui.controller_reset_button.clicked.connect(self.on_grbl_reset)
        self.ui.com_connect_button.clicked.connect(self.on_grbl_connect)
        self.ui.grbl_send_button.clicked.connect(self.on_grbl_send_command)
        self.ui.grbl_command_entry.returnPressed.connect(self.on_grbl_send_command)

        # Jog
        self.ui.jog_wdg.jog_up_button.clicked.connect(lambda: self.on_grbl_jog(direction='yplus'))
        self.ui.jog_wdg.jog_down_button.clicked.connect(lambda: self.on_grbl_jog(direction='yminus'))
        self.ui.jog_wdg.jog_right_button.clicked.connect(lambda: self.on_grbl_jog(direction='xplus'))
        self.ui.jog_wdg.jog_left_button.clicked.connect(lambda: self.on_grbl_jog(direction='xminus'))
        self.ui.jog_wdg.jog_z_up_button.clicked.connect(lambda: self.on_grbl_jog(direction='zplus'))
        self.ui.jog_wdg.jog_z_down_button.clicked.connect(lambda: self.on_grbl_jog(direction='zminus'))
        self.ui.jog_wdg.jog_origin_button.clicked.connect(lambda: self.on_grbl_jog(direction='origin'))

        # Zero
        self.ui.zero_axs_wdg.grbl_zerox_button.clicked.connect(lambda: self.on_grbl_zero(axis='x'))
        self.ui.zero_axs_wdg.grbl_zeroy_button.clicked.connect(lambda: self.on_grbl_zero(axis='y'))
        self.ui.zero_axs_wdg.grbl_zeroz_button.clicked.connect(lambda: self.on_grbl_zero(axis='z'))
        self.ui.zero_axs_wdg.grbl_zero_all_button.clicked.connect(lambda: self.on_grbl_zero(axis='all'))
        self.ui.zero_axs_wdg.grbl_homing_button.clicked.connect(self.on_grbl_homing)

        # Sender
        self.ui.grbl_report_button.clicked.connect(lambda: self.send_grbl_command(command='?'))
        self.ui.grbl_get_param_button.clicked.connect(
            lambda: self.on_grbl_get_parameter(param=self.ui.grbl_parameter_entry.get_value()))
        self.ui.view_h_gcode_button.clicked.connect(self.on_edit_probing_gcode)
        self.ui.h_gcode_button.clicked.connect(self.on_save_probing_gcode)
        self.ui.import_heights_button.clicked.connect(self.on_import_height_map)
        self.ui.pause_resume_button.clicked.connect(self.on_grbl_pause_resume)
        self.ui.grbl_get_heightmap_button.clicked.connect(self.on_grbl_autolevel)
        self.ui.grbl_save_height_map_button.clicked.connect(self.on_grbl_heightmap_save)

        self.build_al_table_sig.connect(self.build_al_table)

        # self.ui.tc_variable_combo.currentIndexChanged[str].connect(self.on_cnc_custom_parameters)

        self.ui.cncplot_method_combo.activated_custom.connect(self.on_plot_kind_change)

        # Show/Hide Advanced Options
        if self.app.defaults["global_app_level"] == 'b':
            self.ui.level.setText('<span style="color:green;"><b>%s</b></span>' % _("Basic"))

            self.ui.sal_btn.hide()
            self.ui.sal_btn.setChecked(False)
        else:
            self.ui.level.setText('<span style="color:red;"><b>%s</b></span>' % _("Advanced"))

            if 'Roland' in self.pp_excellon_name or 'Roland' in self.pp_geometry_name or 'hpgl' in \
                    self.pp_geometry_name:
                self.ui.sal_btn.hide()
                self.ui.sal_btn.setChecked(False)
            else:
                self.ui.sal_btn.show()
                self.ui.sal_btn.setChecked(self.app.defaults["cncjob_al_status"])

        preamble = self.prepend_snippet
        postamble = self.append_snippet
        gc = self.export_gcode(preamble=preamble, postamble=postamble, to_file=True)
        self.source_file = gc.getvalue()

        self.ui.al_mode_radio.set_value(self.options['al_mode'])
        self.on_controller_change()

        self.on_mode_radio(val=self.options['al_mode'])
        self.on_method_radio(val=self.options['al_method'])

    # def on_cnc_custom_parameters(self, signal_text):
    #     if signal_text == 'Parameters':
    #         return
    #     else:
    #         self.ui.toolchange_text.insertPlainText('%%%s%%' % signal_text)

    def ui_connect(self):
        for row in range(self.ui.cnc_tools_table.rowCount()):
            self.ui.cnc_tools_table.cellWidget(row, 6).clicked.connect(self.on_plot_cb_click_table)
        for row in range(self.ui.exc_cnc_tools_table.rowCount()):
            self.ui.exc_cnc_tools_table.cellWidget(row, 6).clicked.connect(self.on_plot_cb_click_table)
        self.ui.plot_cb.stateChanged.connect(self.on_plot_cb_click)

        self.ui.al_add_button.clicked.connect(self.on_add_al_probepoints)
        self.ui.show_al_table.stateChanged.connect(self.on_show_al_table)

    def ui_disconnect(self):
        for row in range(self.ui.cnc_tools_table.rowCount()):
            try:
                self.ui.cnc_tools_table.cellWidget(row, 6).clicked.disconnect(self.on_plot_cb_click_table)
            except (TypeError, AttributeError):
                pass

        for row in range(self.ui.exc_cnc_tools_table.rowCount()):
            try:
                self.ui.exc_cnc_tools_table.cellWidget(row, 6).clicked.disconnect(self.on_plot_cb_click_table)
            except (TypeError, AttributeError):
                pass

        try:
            self.ui.plot_cb.stateChanged.disconnect(self.on_plot_cb_click)
        except (TypeError, AttributeError):
            pass

        try:
            self.ui.al_add_button.clicked.disconnect()
        except (TypeError, AttributeError):
            pass

        try:
            self.ui.show_al_table.stateChanged.disconnect()
        except (TypeError, AttributeError):
            pass

    def on_properties(self, state):
        if state:
            self.ui.properties_frame.show()
        else:
            self.ui.properties_frame.hide()
            return

        self.ui.treeWidget.clear()
        self.add_properties_items(obj=self, treeWidget=self.ui.treeWidget)

        self.ui.treeWidget.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.MinimumExpanding)
        # make sure that the FCTree widget columns are resized to content
        self.ui.treeWidget.resize_sig.emit()

    def on_add_al_probepoints(self):
        # create the solid_geo

        self.solid_geo = unary_union([geo['geom'] for geo in self.gcode_parsed if geo['kind'][0] == 'C'])

        # reset al table
        self.ui.al_probe_points_table.setRowCount(0)

        # reset the al dict
        self.al_voronoi_geo_storage.clear()

        xmin, ymin, xmax, ymax = self.solid_geo.bounds

        if self.ui.al_mode_radio.get_value() == 'grid':
            width = abs(xmax - xmin)
            height = abs(ymax - ymin)
            cols = self.ui.al_columns_entry.get_value()
            rows = self.ui.al_rows_entry.get_value()

            dx = 0 if cols == 1 else width / (cols - 1)
            dy = 0 if rows == 1 else height / (rows - 1)

            points = []
            new_y = ymin
            for x in range(rows):
                new_x = xmin
                for y in range(cols):
                    formatted_point = (
                        self.app.dec_format(new_x, self.app.decimals),
                        self.app.dec_format(new_y, self.app.decimals)
                    )
                    points.append(formatted_point)
                    new_x += dx
                new_y += dy

            pt_id = 0
            vor_pts_list = []
            bl_pts_list = []
            for point in points:
                pt_id += 1
                pt = Point(point)
                vor_pts_list.append(pt)
                bl_pts_list.append((point[0], point[1], 0.0))
                new_dict = {
                    'point': pt,
                    'geo': None,
                    'height': 0.0
                }
                self.al_voronoi_geo_storage[pt_id] = deepcopy(new_dict)

            al_method = self.ui.al_method_radio.get_value()
            if al_method == 'v':
                if VORONOI_ENABLED is True:
                    self.generate_voronoi_geometry(pts=vor_pts_list)
                    # generate Probing GCode
                    self.probing_gcode_text = self.probing_gcode(storage=self.al_voronoi_geo_storage)
                else:
                    self.app.inform.emit('[ERROR_NOTCL] %s' % _("Voronoi function can not be loaded.\n"
                                                                "Shapely >= 1.8 is required"))
            else:
                self.generate_bilinear_geometry(pts=bl_pts_list)
                # generate Probing GCode
                self.probing_gcode_text = self.probing_gcode(storage=self.al_bilinear_geo_storage)

            self.build_al_table_sig.emit()
            if self.ui.plot_probing_pts_cb.get_value():
                self.show_probing_geo(state=True, reset=True)
            else:
                # clear probe shapes
                self.plot_probing_geo(None, False)

        else:
            f_probe_pt = Point([xmin, xmin])
            int_keys = [int(k) for k in self.al_voronoi_geo_storage.keys()]
            new_id = max(int_keys) + 1 if int_keys else 1
            new_dict = {
                'point': f_probe_pt,
                'geo': None,
                'height': 0.0
            }
            self.al_voronoi_geo_storage[new_id] = deepcopy(new_dict)

            radius = 0.3 if self.units == 'MM' else 0.012
            fprobe_pt_buff = f_probe_pt.buffer(radius)

            self.app.inform.emit(_("Click on canvas to add a Probe Point..."))
            self.app.defaults['global_selection_shape'] = False

            if self.app.is_legacy is False:
                self.app.plotcanvas.graph_event_disconnect('key_press', self.app.ui.keyPressEvent)
                self.app.plotcanvas.graph_event_disconnect('mouse_press', self.app.on_mouse_click_over_plot)
                self.app.plotcanvas.graph_event_disconnect('mouse_release', self.app.on_mouse_click_release_over_plot)
            else:
                self.app.plotcanvas.graph_event_disconnect(self.app.kp)
                self.app.plotcanvas.graph_event_disconnect(self.app.mp)
                self.app.plotcanvas.graph_event_disconnect(self.app.mr)

            self.kp = self.app.plotcanvas.graph_event_connect('key_press', self.on_key_press)
            self.mr = self.app.plotcanvas.graph_event_connect('mouse_release', self.on_mouse_click_release)

            self.mouse_events_connected = True

            self.build_al_table_sig.emit()
            if self.ui.plot_probing_pts_cb.get_value():
                self.show_probing_geo(state=True, reset=True)
            else:
                # clear probe shapes
                self.plot_probing_geo(None, False)

            self.plot_probing_geo(geometry=fprobe_pt_buff, visibility=True, custom_color="#0000FFFA")

    def show_probing_geo(self, state, reset=False):

        if reset:
            self.probing_shapes.clear(update=True)

        points_geo = []
        poly_geo = []

        al_method = self.ui.al_method_radio.get_value()
        # voronoi diagram
        if al_method == 'v':
            # create the geometry
            radius = 0.1 if self.units == 'MM' else 0.004
            for pt in self.al_voronoi_geo_storage:
                if not self.al_voronoi_geo_storage[pt]['geo']:
                    continue

                p_geo = self.al_voronoi_geo_storage[pt]['point'].buffer(radius)
                s_geo = self.al_voronoi_geo_storage[pt]['geo'].buffer(0.0000001)

                points_geo.append(p_geo)
                poly_geo.append(s_geo)

            if not points_geo and not poly_geo:
                return

            self.plot_probing_geo(geometry=points_geo, visibility=state, custom_color='#000000FF')
            self.plot_probing_geo(geometry=poly_geo, visibility=state)
        # bilinear interpolation
        elif al_method == 'b':
            radius = 0.1 if self.units == 'MM' else 0.004
            for pt in self.al_bilinear_geo_storage:

                x_pt = pt[0]
                y_pt = pt[1]
                p_geo = Point([x_pt, y_pt]).buffer(radius)

                if p_geo.is_valid:
                    points_geo.append(p_geo)

            if not points_geo:
                return

            self.plot_probing_geo(geometry=points_geo, visibility=state, custom_color='#000000FF')

    def plot_probing_geo(self, geometry, visibility, custom_color=None):
        if visibility:
            if self.app.is_legacy is False:
                def random_color():
                    r_color = np.random.rand(4)
                    r_color[3] = 0.5
                    return r_color
            else:
                def random_color():
                    while True:
                        r_color = np.random.rand(4)
                        r_color[3] = 0.5

                        new_color = '#'
                        for idx in range(len(r_color)):
                            new_color += '%x' % int(r_color[idx] * 255)
                        # do it until a valid color is generated
                        # a valid color has the # symbol, another 6 chars for the color and the last 2 chars for alpha
                        # for a total of 9 chars
                        if len(new_color) == 9:
                            break
                    return new_color

            try:
                # if self.app.is_legacy is False:
                #     color = "#0000FFFE"
                # else:
                #     color = "#0000FFFE"
                # for sh in points_geo:
                #     self.add_probing_shape(shape=sh, color=color, face_color=color, visible=True)

                edge_color = "#000000FF"
                try:
                    for sh in geometry:
                        if custom_color is None:
                            self.add_probing_shape(shape=sh, color=edge_color, face_color=random_color(), visible=True)
                        else:
                            self.add_probing_shape(shape=sh, color=custom_color, face_color=custom_color, visible=True)
                except TypeError:
                    if custom_color is None:
                        self.add_probing_shape(
                            shape=geometry, color=edge_color, face_color=random_color(), visible=True)
                    else:
                        self.add_probing_shape(
                            shape=geometry, color=custom_color, face_color=custom_color, visible=True)

                self.probing_shapes.redraw()
            except (ObjectDeleted, AttributeError):
                self.probing_shapes.clear(update=True)
            except Exception as e:
                log.debug("CNCJobObject.plot_probing_geo() --> %s" % str(e))
        else:
            self.probing_shapes.clear(update=True)

    def add_probing_shape(self, **kwargs):
        if self.deleted:
            raise ObjectDeleted()
        else:
            key = self.probing_shapes.add(tolerance=self.drawing_tolerance, layer=0, **kwargs)
        return key

    def generate_voronoi_geometry(self, pts):
        env = self.solid_geo.envelope
        fact = 1 if self.units == 'MM' else 0.039
        env = env.buffer(fact)

        new_pts = deepcopy(pts)
        try:
            pts_union = MultiPoint(pts)
            voronoi_union = voronoi_diagram(geom=pts_union, envelope=env)
        except Exception as e:
            log.debug("CNCJobObject.generate_voronoi_geometry() --> %s" % str(e))
            for pt_index in range(len(pts)):
                new_pts[pt_index] = affinity.translate(
                    new_pts[pt_index], random.random() * 1e-09, random.random() * 1e-09)

            pts_union = MultiPoint(new_pts)
            try:
                voronoi_union = voronoi_diagram(geom=pts_union, envelope=env)
            except Exception:
                return

        new_voronoi = []
        for p in voronoi_union:
            new_voronoi.append(p.intersection(env))

        for pt_key in list(self.al_voronoi_geo_storage.keys()):
            for poly in new_voronoi:
                if self.al_voronoi_geo_storage[pt_key]['point'].within(poly):
                    self.al_voronoi_geo_storage[pt_key]['geo'] = poly

    def generate_bilinear_geometry(self, pts):
        self.al_bilinear_geo_storage = pts

    # To be called after clicking on the plot.
    def on_mouse_click_release(self, event):

        if self.app.is_legacy is False:
            event_pos = event.pos
            # event_is_dragging = event.is_dragging
            right_button = 2
        else:
            event_pos = (event.xdata, event.ydata)
            # event_is_dragging = self.app.plotcanvas.is_dragging
            right_button = 3

        try:
            x = float(event_pos[0])
            y = float(event_pos[1])
        except TypeError:
            return
        event_pos = (x, y)

        # do paint single only for left mouse clicks
        if event.button == 1:
            pos = self.app.plotcanvas.translate_coords(event_pos)

            # use the snapped position as reference
            snapped_pos = self.app.geo_editor.snap(pos[0], pos[1])

            probe_pt = Point(snapped_pos)

            xxmin, yymin, xxmax, yymax = self.solid_geo.bounds
            box_geo = box(xxmin, yymin, xxmax, yymax)
            if not probe_pt.within(box_geo):
                self.app.inform.emit(_("Point is not within the object area. Choose another point."))
                return

            int_keys = [int(k) for k in self.al_voronoi_geo_storage.keys()]
            new_id = max(int_keys) + 1 if int_keys else 1
            new_dict = {
                'point': probe_pt,
                'geo': None,
                'height': 0.0
            }
            self.al_voronoi_geo_storage[new_id] = deepcopy(new_dict)

            # rebuild the al table
            self.build_al_table_sig.emit()

            radius = 0.3 if self.units == 'MM' else 0.012
            probe_pt_buff = probe_pt.buffer(radius)

            self.plot_probing_geo(geometry=probe_pt_buff, visibility=True, custom_color="#0000FFFA")

            self.app.inform.emit(_("Added a Probe Point... Click again to add another or right click to finish ..."))

        # if RMB then we exit
        elif event.button == right_button and self.mouse_is_dragging is False:
            if self.app.is_legacy is False:
                self.app.plotcanvas.graph_event_disconnect('key_press', self.on_key_press)
                self.app.plotcanvas.graph_event_disconnect('mouse_release', self.on_mouse_click_release)
            else:
                self.app.plotcanvas.graph_event_disconnect(self.kp)
                self.app.plotcanvas.graph_event_disconnect(self.mr)

            self.app.kp = self.app.plotcanvas.graph_event_connect('key_press', self.app.ui.keyPressEvent)
            self.app.mp = self.app.plotcanvas.graph_event_connect('mouse_press', self.app.on_mouse_click_over_plot)
            self.app.mr = self.app.plotcanvas.graph_event_connect('mouse_release',
                                                                  self.app.on_mouse_click_release_over_plot)

            # signal that the mouse events are disconnected from local methods
            self.mouse_events_connected = False

            # restore selection
            self.app.defaults['global_selection_shape'] = self.old_selection_state

            self.app.inform.emit(_("Finished adding Probe Points..."))

            al_method = self.ui.al_method_radio.get_value()
            if al_method == 'v':
                if VORONOI_ENABLED is True:
                    pts_list = []
                    for k in self.al_voronoi_geo_storage:
                        pts_list.append(self.al_voronoi_geo_storage[k]['point'])
                    self.generate_voronoi_geometry(pts=pts_list)

                    self.probing_gcode_text = self.probing_gcode(self.al_voronoi_geo_storage)
                else:
                    self.app.inform.emit('[ERROR_NOTCL] %s' % _("Voronoi function can not be loaded.\n"
                                                                "Shapely >= 1.8 is required"))

            # rebuild the al table
            self.build_al_table_sig.emit()

            if self.ui.plot_probing_pts_cb.get_value():
                self.show_probing_geo(state=True, reset=True)
            else:
                # clear probe shapes
                self.plot_probing_geo(None, False)

    def on_key_press(self, event):
        # events out of the self.app.collection view (it's about Project Tab) are of type int
        if type(event) is int:
            key = event
        # events from the GUI are of type QKeyEvent
        elif type(event) == QtGui.QKeyEvent:
            key = event.key()
        elif isinstance(event, mpl_key_event):  # MatPlotLib key events are trickier to interpret than the rest
            key = event.key
            key = QtGui.QKeySequence(key)

            # check for modifiers
            key_string = key.toString().lower()
            if '+' in key_string:
                mod, __, key_text = key_string.rpartition('+')
                if mod.lower() == 'ctrl':
                    # modifiers = QtCore.Qt.ControlModifier
                    pass
                elif mod.lower() == 'alt':
                    # modifiers = QtCore.Qt.AltModifier
                    pass
                elif mod.lower() == 'shift':
                    # modifiers = QtCore.Qt.ShiftModifier
                    pass
                else:
                    # modifiers = QtCore.Qt.NoModifier
                    pass
                key = QtGui.QKeySequence(key_text)
        # events from Vispy are of type KeyEvent
        else:
            key = event.key

        # Escape = Deselect All
        if key == QtCore.Qt.Key_Escape or key == 'Escape':
            if self.mouse_events_connected is True:
                self.mouse_events_connected = False
                if self.app.is_legacy is False:
                    self.app.plotcanvas.graph_event_disconnect('key_press', self.on_key_press)
                    self.app.plotcanvas.graph_event_disconnect('mouse_release', self.on_mouse_click_release)
                else:
                    self.app.plotcanvas.graph_event_disconnect(self.kp)
                    self.app.plotcanvas.graph_event_disconnect(self.mr)

                self.app.kp = self.app.plotcanvas.graph_event_connect('key_press', self.app.ui.keyPressEvent)
                self.app.mp = self.app.plotcanvas.graph_event_connect('mouse_press', self.app.on_mouse_click_over_plot)
                self.app.mr = self.app.plotcanvas.graph_event_connect('mouse_release',
                                                                      self.app.on_mouse_click_release_over_plot)

                if self.ui.big_cursor_cb.get_value():
                    # restore cursor
                    self.app.on_cursor_type(val=self.old_cursor_type)
                # restore selection
                self.app.defaults['global_selection_shape'] = self.old_selection_state

        # Grid toggle
        if key == QtCore.Qt.Key_G or key == 'G':
            self.app.ui.grid_snap_btn.trigger()

        # Jump to coords
        if key == QtCore.Qt.Key_J or key == 'J':
            self.app.on_jump_to()

    def on_toggle_autolevelling(self, state):
        self.ui.al_frame.show() if state else self.ui.al_frame.hide()
        self.app.defaults["cncjob_al_status"] = True if state else False

    def autolevell_gcode(self):
        pass

    def autolevell_gcode_line(self, gcode_line):
        al_method = self.ui.al_method_radio.get_value()

        coords = ()

        if al_method == 'v':
            self.autolevell_voronoi(gcode_line, coords)
        elif al_method == 'b':
            self.autolevell_bilinear(gcode_line, coords)

    def autolevell_bilinear(self, gcode_line, coords):
        pass

    def autolevell_voronoi(self, gcode_line, coords):
        pass

    def on_show_al_table(self, state):
        self.ui.al_probe_points_table.show() if state else self.ui.al_probe_points_table.hide()

    def on_mode_radio(self, val):
        # reset al table
        self.ui.al_probe_points_table.setRowCount(0)

        # reset the al dict
        self.al_voronoi_geo_storage.clear()

        # reset Voronoi Shapes
        self.probing_shapes.clear(update=True)

        # build AL table
        self.build_al_table()

        if val == "manual":
            self.ui.al_rows_entry.setDisabled(True)
            self.ui.al_rows_label.setDisabled(True)
            self.ui.al_columns_entry.setDisabled(True)
            self.ui.al_columns_label.setDisabled(True)
            self.ui.al_method_lbl.setDisabled(True)
            self.ui.al_method_radio.setDisabled(True)
            self.ui.al_method_radio.set_value('v')
        else:
            self.ui.al_rows_entry.setDisabled(False)
            self.ui.al_rows_label.setDisabled(False)
            self.ui.al_columns_entry.setDisabled(False)
            self.ui.al_columns_label.setDisabled(False)
            self.ui.al_method_lbl.setDisabled(False)
            self.ui.al_method_radio.setDisabled(False)
            self.ui.al_method_radio.set_value(self.app.defaults['cncjob_al_method'])

    def on_method_radio(self, val):
        if val == 'b':
            self.ui.al_columns_entry.setMinimum(2)
            self.ui.al_rows_entry.setMinimum(2)
        else:
            self.ui.al_columns_entry.setMinimum(1)
            self.ui.al_rows_entry.setMinimum(1)

    def on_controller_change(self):
        if self.ui.al_controller_combo.get_value() == 'GRBL':
            self.ui.h_gcode_button.hide()
            self.ui.view_h_gcode_button.hide()

            self.ui.import_heights_button.hide()
            self.ui.grbl_frame.show()
            self.on_grbl_search_ports(muted=True)
        else:
            self.ui.h_gcode_button.show()
            self.ui.view_h_gcode_button.show()

            self.ui.import_heights_button.show()
            self.ui.grbl_frame.hide()

        # if the is empty then there is a chance that we've added probe points but the GRBL controller was selected
        # therefore no Probing GCode was genrated (it is different for GRBL on how it gets it's Probing GCode
        if not self.probing_gcode_text or self.probing_gcode_text == '':
            # generate Probing GCode
            al_method = self.ui.al_method_radio.get_value()
            storage = self.al_voronoi_geo_storage if al_method == 'v' else self.al_bilinear_geo_storage
            self.probing_gcode_text = self.probing_gcode(storage=storage)

    @staticmethod
    def on_grbl_list_serial_ports():
        """
        Lists serial port names.
        From here: https://stackoverflow.com/questions/12090503/listing-available-com-ports-with-python

        :raises EnvironmentError:   On unsupported or unknown platforms
        :returns:                   A list of the serial ports available on the system
        """

        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')

        result = []
        s = serial.Serial()

        for port in ports:
            s.port = port

            try:
                s.open()
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                # result.append(port + " (in use)")
                pass

        return result

    def on_grbl_search_ports(self, muted=None):
        port_list = self.on_grbl_list_serial_ports()
        self.ui.com_list_combo.clear()
        self.ui.com_list_combo.addItems(port_list)
        if muted is not True:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("COM list updated ..."))

    def on_grbl_connect(self):
        port_name = self.ui.com_list_combo.currentText()
        if " (" in port_name:
            port_name = port_name.rpartition(" (")[0]

        baudrate = int(self.ui.baudrates_list_combo.currentText())

        try:
            self.grbl_ser_port = serial.serial_for_url(port_name, baudrate,
                                                       bytesize=serial.EIGHTBITS,
                                                       parity=serial.PARITY_NONE,
                                                       stopbits=serial.STOPBITS_ONE,
                                                       timeout=0.1,
                                                       xonxoff=False,
                                                       rtscts=False)

            # Toggle DTR to reset the controller loaded with GRBL (Arduino, ESP32, etc)
            try:
                self.grbl_ser_port.dtr = False
            except IOError:
                pass

            self.grbl_ser_port.reset_input_buffer()

            try:
                self.grbl_ser_port.dtr = True
            except IOError:
                pass

            answer = self.on_grbl_wake()
            answer = ['ok']   # FIXME: hack for development without a GRBL controller connected
            for line in answer:
                if 'ok' in line.lower():
                    self.ui.com_connect_button.setStyleSheet("QPushButton {background-color: seagreen;}")
                    self.ui.com_connect_button.setText(_("Connected"))
                    self.ui.controller_reset_button.setDisabled(False)

                    for idx in range(self.ui.al_toolbar.count()):
                        if self.ui.al_toolbar.tabText(idx) == _("Connect"):
                            self.ui.al_toolbar.tabBar.setTabTextColor(idx, QtGui.QColor('seagreen'))
                        if self.ui.al_toolbar.tabText(idx) == _("Control"):
                            self.ui.al_toolbar.tabBar.setTabEnabled(idx, True)
                        if self.ui.al_toolbar.tabText(idx) == _("Sender"):
                            self.ui.al_toolbar.tabBar.setTabEnabled(idx, True)

                    self.app.inform.emit("%s: %s" % (_("Port connected"), port_name))
                    return

            self.grbl_ser_port.close()
            self.app.inform.emit("[ERROR_NOTCL] %s: %s" % (_("Could not connect to GRBL on port"), port_name))

        except serial.SerialException:
            self.grbl_ser_port = serial.Serial()
            self.grbl_ser_port.port = port_name
            self.grbl_ser_port.close()
            self.ui.com_connect_button.setStyleSheet("QPushButton {background-color: red;}")
            self.ui.com_connect_button.setText(_("Disconnected"))
            self.ui.controller_reset_button.setDisabled(True)

            for idx in range(self.ui.al_toolbar.count()):
                if self.ui.al_toolbar.tabText(idx) == _("Connect"):
                    self.ui.al_toolbar.tabBar.setTabTextColor(idx, QtGui.QColor('red'))
                if self.ui.al_toolbar.tabText(idx) == _("Control"):
                    self.ui.al_toolbar.tabBar.setTabEnabled(idx, False)
                if self.ui.al_toolbar.tabText(idx) == _("Sender"):
                    self.ui.al_toolbar.tabBar.setTabEnabled(idx, False)
            self.app.inform.emit("%s: %s" % (_("Port is connected. Disconnecting"), port_name))
        except Exception:
            self.app.inform.emit("[ERROR_NOTCL] %s: %s" % (_("Could not connect to port"), port_name))

    def on_grbl_add_baudrate(self):
        new_bd = str(self.ui.new_baudrate_entry.get_value())
        if int(new_bd) >= 40 and new_bd not in self.ui.baudrates_list_combo.model().stringList():
            self.ui.baudrates_list_combo.addItem(new_bd)
            self.ui.baudrates_list_combo.setCurrentText(new_bd)

    def on_grbl_delete_baudrate_grbl(self):
        current_idx = self.ui.baudrates_list_combo.currentIndex()
        self.ui.baudrates_list_combo.removeItem(current_idx)

    def on_grbl_wake(self):
        # Wake up grbl
        self.grbl_ser_port.write("\r\n\r\n".encode('utf-8'))
        # Wait for GRBL controller to initialize
        time.sleep(1)

        grbl_out = deepcopy(self.grbl_ser_port.readlines())
        self.grbl_ser_port.reset_input_buffer()

        return grbl_out

    def on_grbl_send_command(self):
        cmd = self.ui.grbl_command_entry.get_value()

        # show the Shell Dock
        self.app.ui.shell_dock.show()

        def worker_task():
            with self.app.proc_container.new(_("Sending GCode...")):
                self.send_grbl_command(command=cmd)

        self.app.worker_task.emit({'fcn': worker_task, 'params': []})

    def send_grbl_command(self, command, echo=True):
        """

        :param command: GCode command
        :type command:  str
        :param echo:    if to send a '\n' char after
        :type echo:     bool
        :return:        the text returned by the GRBL controller after each command
        :rtype:         str
        """
        cmd = command.strip()
        if echo:
            self.app.inform_shell[str, bool].emit(cmd, False)

        # Send Gcode command to GRBL
        snd = cmd + '\n'
        self.grbl_ser_port.write(snd.encode('utf-8'))
        grbl_out = self.grbl_ser_port.readlines()
        if not grbl_out:
            self.app.inform_shell[str, bool].emit('\t\t\t: No answer\n', False)

        result = ''
        for line in grbl_out:
            if echo:
                try:
                    self.app.inform_shell.emit('\t\t\t: ' + line.decode('utf-8').strip().upper())
                except Exception as e:
                    log.debug("CNCJobObject.send_grbl_command() --> %s" % str(e))
            if 'ok' in line:
                result = grbl_out

        return result

    def send_grbl_block(self, command, echo=True):
        stripped_cmd = command.strip()

        for grbl_line in stripped_cmd.split('\n'):
            if echo:
                self.app.inform_shell[str, bool].emit(grbl_line, False)

            # Send Gcode block to GRBL
            snd = grbl_line + '\n'
            self.grbl_ser_port.write(snd.encode('utf-8'))
            grbl_out = self.grbl_ser_port.readlines()

            for line in grbl_out:
                if echo:
                    try:
                        self.app.inform_shell.emit(' : ' + line.decode('utf-8').strip().upper())
                    except Exception as e:
                        log.debug("CNCJobObject.send_grbl_block() --> %s" % str(e))

    def on_grbl_get_parameter(self, param):
        if '$' in param:
            param = param.replace('$', '')

        snd = '$$\n'
        self.grbl_ser_port.write(snd.encode('utf-8'))
        grbl_out = self.grbl_ser_port.readlines()
        for line in grbl_out:
            decoded_line = line.decode('utf-8')
            par = '$%s' % str(param)
            if par in decoded_line:
                result = float(decoded_line.rpartition('=')[2])
                self.app.shell_message("GRBL Parameter: %s = %s" % (str(param), str(result)), show=True)
                return result

    def on_grbl_jog(self, direction=None):
        if direction is None:
            return
        cmd = ''

        step = self.ui.jog_step_entry.get_value(),
        feedrate = self.ui.jog_fr_entry.get_value()
        travelz = float(self.app.defaults["cncjob_al_grbl_travelz"])

        if direction == 'xplus':
            cmd = "$J=G91 %s X%s F%s" % ({'IN': 'G20', 'MM': 'G21'}[self.units], str(step), str(feedrate))
        if direction == 'xminus':
            cmd = "$J=G91 %s X-%s F%s" % ({'IN': 'G20', 'MM': 'G21'}[self.units], str(step), str(feedrate))
        if direction == 'yplus':
            cmd = "$J=G91 %s Y%s F%s" % ({'IN': 'G20', 'MM': 'G21'}[self.units], str(step), str(feedrate))
        if direction == 'yminus':
            cmd = "$J=G91 %s Y-%s F%s" % ({'IN': 'G20', 'MM': 'G21'}[self.units], str(step), str(feedrate))

        if direction == 'zplus':
            cmd = "$J=G91 %s Z%s F%s" % ({'IN': 'G20', 'MM': 'G21'}[self.units], str(step), str(feedrate))
        if direction == 'zminus':
            cmd = "$J=G91 %s Z-%s F%s" % ({'IN': 'G20', 'MM': 'G21'}[self.units], str(step), str(feedrate))

        if direction == 'origin':
            cmd = "$J=G90 %s Z%s F%s" % ({'IN': 'G20', 'MM': 'G21'}[self.units], str(travelz), str(feedrate))
            self.send_grbl_command(command=cmd, echo=False)
            cmd = "$J=G90 %s X0.0 Y0.0 F%s" % ({'IN': 'G20', 'MM': 'G21'}[self.units], str(feedrate))
            self.send_grbl_command(command=cmd, echo=False)
            return

        self.send_grbl_command(command=cmd, echo=False)

    def on_grbl_zero(self, axis):
        current_mode = self.on_grbl_get_parameter('10')
        if current_mode is None:
            return

        cmd = '$10=0'
        self.send_grbl_command(command=cmd, echo=False)

        if axis == 'x':
            cmd = 'G10 L2 P1 X0'
        elif axis == 'y':
            cmd = 'G10 L2 P1 Y0'
        elif axis == 'z':
            cmd = 'G10 L2 P1 Z0'
        else:
            # all
            cmd = 'G10 L2 P1 X0 Y0 Z0'
        self.send_grbl_command(command=cmd, echo=False)

        # restore previous mode
        cmd = '$10=%d' % int(current_mode)
        self.send_grbl_command(command=cmd, echo=False)

    def on_grbl_homing(self):
        cmd = '$H'
        self.app.inform.emit("%s" % _("GRBL is doing a home cycle."))
        self.on_grbl_wake()
        self.send_grbl_command(command=cmd)

    def on_grbl_reset(self):
        cmd = '\x18'
        self.app.inform.emit("%s" % _("GRBL software reset was sent."))
        self.on_grbl_wake()
        self.send_grbl_command(command=cmd)

    def on_grbl_pause_resume(self, checked):
        if checked is False:
            cmd = '~'
            self.send_grbl_command(command=cmd)
            self.app.inform.emit("%s" % _("GRBL resumed."))
        else:
            cmd = '!'
            self.send_grbl_command(command=cmd)
            self.app.inform.emit("%s" % _("GRBL paused."))

    def probing_gcode(self, storage):
        """
        :param storage:         either a dict of dicts (voronoi) or a list of tuples (bilinear)
        :return:                Probing GCode
        :rtype:                 str
        """

        p_gcode = ''
        header = ''
        time_str = "{:%A, %d %B %Y at %H:%M}".format(datetime.now())

        coords = []
        al_method = self.ui.al_method_radio.get_value()
        if al_method == 'v':
            for id_key, value in storage.items():
                x = value['point'].x
                y = value['point'].y
                coords.append(
                    (
                        self.app.dec_format(x, dec=self.app.decimals),
                        self.app.dec_format(y, dec=self.app.decimals)
                    )
                )
        else:
            for pt in storage:
                x = pt[0]
                y = pt[1]
                coords.append(
                    (
                        self.app.dec_format(x, dec=self.app.decimals),
                        self.app.dec_format(y, dec=self.app.decimals)
                    )
                )

        pr_travel = self.ui.ptravelz_entry.get_value()
        probe_fr = self.ui.feedrate_probe_entry.get_value()
        pr_depth = self.ui.pdepth_entry.get_value()
        controller = self.ui.al_controller_combo.get_value()

        header += '(G-CODE GENERATED BY FLATCAM v%s - www.flatcam.org - Version Date: %s)\n' % \
                  (str(self.app.version), str(self.app.version_date)) + '\n'

        header += '(This is a autolevelling probing GCode.)\n' \
                  '(Make sure that before you start the job you first do a zero for all axis.)\n\n'

        header += '(Name: ' + str(self.options['name']) + ')\n'
        header += '(Type: ' + "Autolevelling Probing GCode " + ')\n'

        header += '(Units: ' + self.units.upper() + ')\n'
        header += '(Created on ' + time_str + ')\n'

        # commands
        if controller == 'MACH3':
            probing_command = 'G31'
            # probing_var = '#2002'
            openfile_command = 'M40'
            closefile_command = 'M41'
        elif controller == 'MACH4':
            probing_command = 'G31'
            # probing_var = '#5063'
            openfile_command = 'M40'
            closefile_command = 'M41'
        elif controller == 'LinuxCNC':
            probing_command = 'G38.2'
            # probing_var = '#5422'
            openfile_command = '(PROBEOPEN a_probing_points_file.txt)'
            closefile_command = '(PROBECLOSE)'
        elif controller == 'GRBL':
            # do nothing here because the Probing GCode for GRBL is obtained differently
            return
        else:
            log.debug("CNCJobObject.probing_gcode() -> controller not supported")
            return

        # #############################################################################################################
        # ########################### GCODE construction ##############################################################
        # #############################################################################################################

        # header
        p_gcode += header + '\n'
        # supplementary message for LinuxCNC
        if controller == 'LinuxCNC':
            p_gcode += "The file with the stored probing points can be found\n" \
                       "in the configuration folder for LinuxCNC.\n" \
                       "The name of the file is: a_probing_points_file.txt.\n"
        # units
        p_gcode += 'G21\n' if self.units == 'MM' else 'G20\n'
        # reference mode = absolute
        p_gcode += 'G90\n'
        # open a new file
        p_gcode += openfile_command + '\n'
        # move to safe height (probe travel Z)
        p_gcode += 'G0 Z%s\n' % str(self.app.dec_format(pr_travel, self.coords_decimals))

        # probing points
        for idx, xy_tuple in enumerate(coords, 1):  # index starts from 1
            x = xy_tuple[0]
            y = xy_tuple[1]
            # move to probing point
            p_gcode += "G0 X%sY%s\n" % (
                str(self.app.dec_format(x, self.coords_decimals)),
                str(self.app.dec_format(y, self.coords_decimals))
            )
            # do the probing
            p_gcode += "%s Z%s F%s\n" % (
                probing_command,
                str(self.app.dec_format(pr_depth, self.coords_decimals)),
                str(self.app.dec_format(probe_fr, self.fr_decimals)),
            )
            # store in a global numeric variable the value of the detected probe Z
            # I offset the global numeric variable by 500 so it does not conflict with something else
            # temp_var = int(idx + 500)
            # p_gcode += "#%d = %s\n" % (temp_var, probing_var)

            # move to safe height (probe travel Z)
            p_gcode += 'G0 Z%s\n' % str(self.app.dec_format(pr_travel, self.coords_decimals))

        # close the file
        p_gcode += closefile_command + '\n'
        # finish the GCode
        p_gcode += 'M2'

        return p_gcode

    def on_save_probing_gcode(self):
        lines = StringIO(self.probing_gcode_text)

        _filter_ = self.app.defaults['cncjob_save_filters']
        name = "probing_gcode"
        try:
            dir_file_to_save = self.app.get_last_save_folder() + '/' + str(name)
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Export Code ..."),
                directory=dir_file_to_save,
                ext_filter=_filter_
            )
        except TypeError:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Export Code ..."),
                ext_filter=_filter_)

        if filename == '':
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Export cancelled ..."))
            return
        else:
            try:
                force_windows_line_endings = self.app.defaults['cncjob_line_ending']
                if force_windows_line_endings and sys.platform != 'win32':
                    with open(filename, 'w', newline='\r\n') as f:
                        for line in lines:
                            f.write(line)
                else:
                    with open(filename, 'w') as f:
                        for line in lines:
                            f.write(line)
            except FileNotFoundError:
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("No such file or directory"))
                return
            except PermissionError:
                self.app.inform.emit(
                    '[WARNING] %s' % _("Permission denied, saving not possible.\n"
                                       "Most likely another app is holding the file open and not accessible.")
                )
                return 'fail'

    def on_edit_probing_gcode(self):
        self.app.proc_container.view.set_busy('%s...' % _("Loading"))

        gco = self.probing_gcode_text
        if gco is None or gco == '':
            self.app.inform.emit('[WARNING_NOTCL] %s...' % _('There is nothing to view'))
            return

        self.gcode_viewer_tab = AppTextEditor(app=self.app, plain_text=True)

        # add the tab if it was closed
        self.app.ui.plot_tab_area.addTab(self.gcode_viewer_tab, '%s' % _("Code Viewer"))
        self.gcode_viewer_tab.setObjectName('code_viewer_tab')

        # delete the absolute and relative position and messages in the infobar
        self.app.ui.position_label.setText("")
        self.app.ui.rel_position_label.setText("")

        self.gcode_viewer_tab.code_editor.completer_enable = False
        self.gcode_viewer_tab.buttonRun.hide()

        # Switch plot_area to CNCJob tab
        self.app.ui.plot_tab_area.setCurrentWidget(self.gcode_viewer_tab)

        self.gcode_viewer_tab.t_frame.hide()
        # then append the text from GCode to the text editor
        try:
            self.gcode_viewer_tab.load_text(gco, move_to_start=True, clear_text=True)
        except Exception as e:
            log.debug('FlatCAMCNCJob.on_edit_probing_gcode() -->%s' % str(e))
            return

        self.gcode_viewer_tab.t_frame.show()
        self.app.proc_container.view.set_idle()

        self.gcode_viewer_tab.buttonSave.hide()
        self.gcode_viewer_tab.buttonOpen.hide()
        self.gcode_viewer_tab.buttonPrint.hide()
        self.gcode_viewer_tab.buttonPreview.hide()
        self.gcode_viewer_tab.buttonReplace.hide()
        self.gcode_viewer_tab.sel_all_cb.hide()
        self.gcode_viewer_tab.entryReplace.hide()

        self.gcode_viewer_tab.button_update_code.show()

        # self.gcode_viewer_tab.code_editor.setReadOnly(True)

        self.gcode_viewer_tab.button_update_code.clicked.connect(self.on_update_probing_gcode)

        self.app.inform.emit('[success] %s...' % _('Loaded Machine Code into Code Viewer'))

    def on_update_probing_gcode(self):
        self.probing_gcode_text = self.gcode_viewer_tab.code_editor.toPlainText()

    def on_import_height_map(self):
        """
        Import the height map file into the app
        :return:
        :rtype:
        """

        _filter_ = "Text File .txt (*.txt);;All Files (*.*)"
        try:
            filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Import Height Map"),
                                                                 directory=self.app.get_last_folder(),
                                                                 filter=_filter_)
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Import Height Map"),
                                                                 filter=_filter_)

        filename = str(filename)

        if filename == '':
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
        else:
            self.app.worker_task.emit({'fcn': self.import_height_map, 'params': [filename]})

    def import_height_map(self, filename):
        """

        :param filename:
        :type filename:
        :return:
        :rtype:
        """

        try:
            if filename:
                with open(filename, 'r') as f:
                    stream = f.readlines()
            else:
                return
        except IOError:
            log.error("Failed to open height map file: %s" % filename)
            self.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Failed to open height map file"), filename))
            return

        idx = 0
        if stream is not None and stream != '':
            for line in stream:
                if line != '':
                    idx += 1
                    line = line.replace(' ', ',').replace('\n', '').split(',')
                    if idx not in self.al_voronoi_geo_storage:
                        self.al_voronoi_geo_storage[idx] = {}
                    self.al_voronoi_geo_storage[idx]['height'] = float(line[2])
                    if 'point' not in self.al_voronoi_geo_storage[idx]:
                        x = float(line[0])
                        y = float(line[1])
                        self.al_voronoi_geo_storage[idx]['point'] = Point((x, y))

            self.build_al_table_sig.emit()

    def on_grbl_autolevel(self):
        # show the Shell Dock
        self.app.ui.shell_dock.show()

        def worker_task():
            with self.app.proc_container.new(_("Sending GCode...")):
                self.grbl_probe_result = ''
                pr_travelz = str(self.ui.ptravelz_entry.get_value())
                probe_fr = str(self.ui.feedrate_probe_entry.get_value())
                pr_depth = str(self.ui.pdepth_entry.get_value())

                cmd = 'G21\n'
                self.send_grbl_command(command=cmd)
                cmd = 'G90\n'
                self.send_grbl_command(command=cmd)

                for pt_key in self.al_voronoi_geo_storage:
                    x = str(self.al_voronoi_geo_storage[pt_key]['point'].x)
                    y = str(self.al_voronoi_geo_storage[pt_key]['point'].y)

                    cmd = 'G0 Z%s\n' % pr_travelz
                    self.send_grbl_command(command=cmd)
                    cmd = 'G0 X%s Y%s\n' % (x, y)
                    self.send_grbl_command(command=cmd)
                    cmd = 'G38.2 Z%s F%s' % (pr_depth, probe_fr)
                    output = self.send_grbl_command(command=cmd)

                    self.grbl_probe_result += output + '\n'

                cmd = 'M2\n'
                self.send_grbl_command(command=cmd)
                self.app.inform.emit('%s' % _("Finished probing. Doing the autolevelling."))

                # apply autolevel here
                self.on_grbl_apply_autolevel()

        self.app.inform.emit('%s' % _("Sending probing GCode to the GRBL controller."))
        self.app.worker_task.emit({'fcn': worker_task, 'params': []})

    def on_grbl_heightmap_save(self):
        if self.grbl_probe_result != '':
            _filter_ = "Text File .txt (*.txt);;All Files (*.*)"
            name = "probing_gcode"
            try:
                dir_file_to_save = self.app.get_last_save_folder() + '/' + str(name)
                filename, _f = FCFileSaveDialog.get_saved_filename(
                    caption=_("Export Code ..."),
                    directory=dir_file_to_save,
                    ext_filter=_filter_
                )
            except TypeError:
                filename, _f = FCFileSaveDialog.get_saved_filename(
                    caption=_("Export Code ..."),
                    ext_filter=_filter_)

            if filename == '':
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("Export cancelled ..."))
                return
            else:
                try:
                    force_windows_line_endings = self.app.defaults['cncjob_line_ending']
                    if force_windows_line_endings and sys.platform != 'win32':
                        with open(filename, 'w', newline='\r\n') as f:
                            for line in self.grbl_probe_result:
                                f.write(line)
                    else:
                        with open(filename, 'w') as f:
                            for line in self.grbl_probe_result:
                                f.write(line)
                except FileNotFoundError:
                    self.app.inform.emit('[WARNING_NOTCL] %s' % _("No such file or directory"))
                    return
                except PermissionError:
                    self.app.inform.emit(
                        '[WARNING] %s' % _("Permission denied, saving not possible.\n"
                                           "Most likely another app is holding the file open and not accessible.")
                    )
                    return 'fail'
        else:
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Empty GRBL heightmap."))

    def on_grbl_apply_autolevel(self):
        # TODO here we call the autolevell method
        self.app.inform.emit('%s' % _("Finished autolevelling."))

    def on_updateplot_button_click(self, *args):
        """
        Callback for the "Updata Plot" button. Reads the form for updates
        and plots the object.
        """
        self.read_form()
        self.on_plot_kind_change()

    def on_plot_kind_change(self):
        kind = self.ui.cncplot_method_combo.get_value()

        def worker_task():
            with self.app.proc_container.new('%s ...' % _("Plotting")):
                self.plot(kind=kind)

        self.app.worker_task.emit({'fcn': worker_task, 'params': []})

    def on_exportgcode_button_click(self):
        """
        Handler activated by a button clicked when exporting GCode.

        :param args:
        :return:
        """
        self.app.defaults.report_usage("cncjob_on_exportgcode_button")

        self.read_form()
        name = self.app.collection.get_active().options['name']
        save_gcode = False

        if 'Roland' in self.pp_excellon_name or 'Roland' in self.pp_geometry_name:
            _filter_ = "RML1 Files .rol (*.rol);;All Files (*.*)"
        elif 'hpgl' in self.pp_geometry_name:
            _filter_ = "HPGL Files .plt (*.plt);;All Files (*.*)"
        else:
            save_gcode = True
            _filter_ = self.app.defaults['cncjob_save_filters']

        try:
            dir_file_to_save = self.app.get_last_save_folder() + '/' + str(name)
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Export Code ..."),
                directory=dir_file_to_save,
                ext_filter=_filter_
            )
        except TypeError:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Export Code ..."),
                ext_filter=_filter_)

        self.export_gcode_handler(filename, is_gcode=save_gcode)

    def export_gcode_handler(self, filename, is_gcode=True):
        preamble = ''
        postamble = ''
        filename = str(filename)

        if filename == '':
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Export cancelled ..."))
            return
        else:
            if is_gcode is True:
                used_extension = filename.rpartition('.')[2]
                self.update_filters(last_ext=used_extension, filter_string='cncjob_save_filters')

        new_name = os.path.split(str(filename))[1].rpartition('.')[0]
        self.ui.name_entry.set_value(new_name)
        self.on_name_activate(silent=True)

        try:
            if self.ui.snippets_cb.get_value():
                preamble = self.prepend_snippet
                postamble = self.append_snippet
            gc = self.export_gcode(filename, preamble=preamble, postamble=postamble)
        except Exception as err:
            log.debug("CNCJobObject.export_gcode_handler() --> %s" % str(err))
            gc = self.export_gcode(filename)

        if gc == 'fail':
            return

        if self.app.defaults["global_open_style"] is False:
            self.app.file_opened.emit("gcode", filename)
        self.app.file_saved.emit("gcode", filename)
        self.app.inform.emit('[success] %s: %s' % (_("File saved to"), filename))

    def on_review_code_click(self):
        """
        Handler activated by a button clicked when reviewing GCode.

        :return:
        """

        self.app.proc_container.view.set_busy('%s...' % _("Loading"))

        preamble = self.prepend_snippet
        postamble = self.append_snippet

        gco = self.export_gcode(preamble=preamble, postamble=postamble, to_file=True)
        if gco == 'fail':
            return
        else:
            self.app.gcode_edited = gco

        self.gcode_editor_tab = AppTextEditor(app=self.app, plain_text=True)

        # add the tab if it was closed
        self.app.ui.plot_tab_area.addTab(self.gcode_editor_tab, '%s' % _("Code Review"))
        self.gcode_editor_tab.setObjectName('code_editor_tab')

        # delete the absolute and relative position and messages in the infobar
        self.app.ui.position_label.setText("")
        self.app.ui.rel_position_label.setText("")

        self.gcode_editor_tab.code_editor.completer_enable = False
        self.gcode_editor_tab.buttonRun.hide()

        # Switch plot_area to CNCJob tab
        self.app.ui.plot_tab_area.setCurrentWidget(self.gcode_editor_tab)

        self.gcode_editor_tab.t_frame.hide()
        # then append the text from GCode to the text editor
        try:
            self.gcode_editor_tab.load_text(self.app.gcode_edited.getvalue(), move_to_start=True, clear_text=True)
        except Exception as e:
            log.debug('FlatCAMCNCJob.on_review_code_click() -->%s' % str(e))
            return

        self.gcode_editor_tab.t_frame.show()
        self.app.proc_container.view.set_idle()

        self.gcode_editor_tab.buttonSave.hide()
        self.gcode_editor_tab.buttonOpen.hide()
        # self.gcode_editor_tab.buttonPrint.hide()
        # self.gcode_editor_tab.buttonPreview.hide()
        self.gcode_editor_tab.buttonReplace.hide()
        self.gcode_editor_tab.sel_all_cb.hide()
        self.gcode_editor_tab.entryReplace.hide()
        self.gcode_editor_tab.code_editor.setReadOnly(True)

        self.app.inform.emit('[success] %s...' % _('Loaded Machine Code into Code Editor'))

    def on_update_source_file(self):
        self.source_file = self.gcode_editor_tab.code_editor.toPlainText()

    def gcode_header(self, comment_start_symbol=None, comment_stop_symbol=None):
        """
        Will create a header to be added to all GCode files generated by FlatCAM

        :param comment_start_symbol:    A symbol to be used as the first symbol in a comment
        :param comment_stop_symbol:     A symbol to be used as the last symbol in a comment
        :return:                        A string with a GCode header
        """

        log.debug("FlatCAMCNCJob.gcode_header()")
        time_str = "{:%A, %d %B %Y at %H:%M}".format(datetime.now())
        marlin = False
        hpgl = False
        probe_pp = False
        gcode = ''

        start_comment = comment_start_symbol if comment_start_symbol is not None else '('
        stop_comment = comment_stop_symbol if comment_stop_symbol is not None else ')'

        try:
            for key in self.cnc_tools:
                ppg = self.cnc_tools[key]['data']['ppname_g']
                if 'marlin' in ppg.lower() or 'repetier' in ppg.lower():
                    marlin = True
                    break
                if ppg == 'hpgl':
                    hpgl = True
                    break
                if "toolchange_probe" in ppg.lower():
                    probe_pp = True
                    break
        except KeyError:
            # log.debug("FlatCAMCNCJob.gcode_header() error: --> %s" % str(e))
            pass

        try:
            if 'marlin' in self.options['ppname_e'].lower() or 'repetier' in self.options['ppname_e'].lower():
                marlin = True
        except KeyError:
            # log.debug("FlatCAMCNCJob.gcode_header(): --> There is no such self.option: %s" % str(e))
            pass

        try:
            if "toolchange_probe" in self.options['ppname_e'].lower():
                probe_pp = True
        except KeyError:
            # log.debug("FlatCAMCNCJob.gcode_header(): --> There is no such self.option: %s" % str(e))
            pass

        if marlin is True:
            gcode += ';Marlin(Repetier) G-CODE GENERATED BY FLATCAM v%s - www.flatcam.org - Version Date:    %s\n' % \
                     (str(self.app.version), str(self.app.version_date)) + '\n'

            gcode += ';Name: ' + str(self.options['name']) + '\n'
            gcode += ';Type: ' + "G-code from " + str(self.options['type']) + '\n'

            # if str(p['options']['type']) == 'Excellon' or str(p['options']['type']) == 'Excellon Geometry':
            #     gcode += '(Tools in use: ' + str(p['options']['Tools_in_use']) + ')\n'

            gcode += ';Units: ' + self.units.upper() + '\n' + "\n"
            gcode += ';Created on ' + time_str + '\n' + '\n'
        elif hpgl is True:
            gcode += 'CO "HPGL CODE GENERATED BY FLATCAM v%s - www.flatcam.org - Version Date:    %s' % \
                     (str(self.app.version), str(self.app.version_date)) + '";\n'

            gcode += 'CO "Name: ' + str(self.options['name']) + '";\n'
            gcode += 'CO "Type: ' + "HPGL code from " + str(self.options['type']) + '";\n'

            # if str(p['options']['type']) == 'Excellon' or str(p['options']['type']) == 'Excellon Geometry':
            #     gcode += '(Tools in use: ' + str(p['options']['Tools_in_use']) + ')\n'

            gcode += 'CO "Units: ' + self.units.upper() + '";\n'
            gcode += 'CO "Created on ' + time_str + '";\n'
        elif probe_pp is True:
            gcode += '(G-CODE GENERATED BY FLATCAM v%s - www.flatcam.org - Version Date: %s)\n' % \
                     (str(self.app.version), str(self.app.version_date)) + '\n'

            gcode += '(This GCode tool change is done by using a Probe.)\n' \
                     '(Make sure that before you start the job you first do a rough zero for Z axis.)\n' \
                     '(This means that you need to zero the CNC axis and then jog to the toolchange X, Y location,)\n' \
                     '(mount the probe and adjust the Z so more or less the probe tip touch the plate. ' \
                     'Then zero the Z axis.)\n' + '\n'

            gcode += '(Name: ' + str(self.options['name']) + ')\n'
            gcode += '(Type: ' + "G-code from " + str(self.options['type']) + ')\n'

            # if str(p['options']['type']) == 'Excellon' or str(p['options']['type']) == 'Excellon Geometry':
            #     gcode += '(Tools in use: ' + str(p['options']['Tools_in_use']) + ')\n'

            gcode += '(Units: ' + self.units.upper() + ')\n' + "\n"
            gcode += '(Created on ' + time_str + ')\n' + '\n'
        else:
            gcode += '%sG-CODE GENERATED BY FLATCAM v%s - www.flatcam.org - Version Date: %s%s\n' % \
                     (start_comment, str(self.app.version), str(self.app.version_date), stop_comment) + '\n'

            gcode += '%sName: ' % start_comment + str(self.options['name']) + '%s\n' % stop_comment
            gcode += '%sType: ' % start_comment + "G-code from " + str(self.options['type']) + '%s\n' % stop_comment

            # if str(p['options']['type']) == 'Excellon' or str(p['options']['type']) == 'Excellon Geometry':
            #     gcode += '(Tools in use: ' + str(p['options']['Tools_in_use']) + ')\n'

            gcode += '%sUnits: ' % start_comment + self.units.upper() + '%s\n' % stop_comment + "\n"
            gcode += '%sCreated on ' % start_comment + time_str + '%s\n' % stop_comment + '\n'

        return gcode

    @staticmethod
    def gcode_footer(end_command=None):
        """
        Will add the M02 to the end of GCode, if requested.

        :param end_command: 'M02' or 'M30' - String
        :return:
        """
        if end_command:
            return end_command
        else:
            return 'M02'

    def export_gcode(self, filename=None, preamble='', postamble='', to_file=False, from_tcl=False):
        """
        This will save the GCode from the Gcode object to a file on the OS filesystem

        :param filename:    filename for the GCode file
        :param preamble:    a custom Gcode block to be added at the beginning of the Gcode file
        :param postamble:   a custom Gcode block to be added at the end of the Gcode file
        :param to_file:     if False then no actual file is saved but the app will know that a file was created
        :param from_tcl:    True if run from Tcl Shell
        :return:            None
        """
        # gcode = ''
        # roland = False
        # hpgl = False
        # isel_icp = False

        include_header = True

        if preamble == '':
            preamble = self.app.defaults["cncjob_prepend"]
        if postamble == '':
            postamble = self.app.defaults["cncjob_append"]

        try:
            if self.special_group:
                self.app.inform.emit('[WARNING_NOTCL] %s %s %s.' %
                                     (_("This CNCJob object can't be processed because it is a"),
                                      str(self.special_group),
                                      _("CNCJob object")))
                return 'fail'
        except AttributeError:
            pass

        # if this dict is not empty then the object is a Geometry object
        if self.cnc_tools:
            first_key = next(iter(self.cnc_tools))
            include_header = self.app.preprocessors[self.cnc_tools[first_key]['data']['ppname_g']].include_header

        # if this dict is not empty then the object is an Excellon object
        if self.exc_cnc_tools:
            first_key = next(iter(self.exc_cnc_tools))
            include_header = self.app.preprocessors[
                self.exc_cnc_tools[first_key]['data']['tools_drill_ppname_e']
            ].include_header

        gcode = ''
        if include_header is False:
            # detect if using multi-tool and make the Gcode summation correctly for each case
            if self.multitool is True:
                for tooluid_key in self.cnc_tools:
                    for key, value in self.cnc_tools[tooluid_key].items():
                        if key == 'gcode':
                            gcode += value
                            break
            else:
                gcode += self.gcode

            g = preamble + '\n' + gcode + '\n' + postamble
        else:
            # search for the GCode beginning which is usually a G20 or G21
            # fix so the preamble gets inserted in between the comments header and the actual start of GCODE
            # g_idx = gcode.rfind('G20')
            #
            # # if it did not find 'G20' then search for 'G21'
            # if g_idx == -1:
            #     g_idx = gcode.rfind('G21')
            #
            # # if it did not find 'G20' and it did not find 'G21' then there is an error and return
            # if g_idx == -1:
            #     self.app.inform.emit('[ERROR_NOTCL] %s' % _("G-code does not have a units code: either G20 or G21"))
            #     return

            # detect if using multi-tool and make the Gcode summation correctly for each case
            if self.multitool is True:
                if self.origin_kind == 'excellon':
                    for tooluid_key in self.exc_cnc_tools:
                        for key, value in self.exc_cnc_tools[tooluid_key].items():
                            if key == 'gcode' and value:
                                gcode += value
                                break
                else:
                    for tooluid_key in self.cnc_tools:
                        for key, value in self.cnc_tools[tooluid_key].items():
                            if key == 'gcode' and value:
                                gcode += value
                                break
            else:
                gcode += self.gcode

            end_gcode = self.gcode_footer() if self.app.defaults['cncjob_footer'] is True else ''

            # detect if using a HPGL preprocessor
            hpgl = False
            if self.cnc_tools:
                for key in self.cnc_tools:
                    if 'ppname_g' in self.cnc_tools[key]['data']:
                        if 'hpgl' in self.cnc_tools[key]['data']['ppname_g']:
                            hpgl = True
                            break
            elif self.exc_cnc_tools:
                for key in self.cnc_tools:
                    if 'ppname_e' in self.cnc_tools[key]['data']:
                        if 'hpgl' in self.cnc_tools[key]['data']['ppname_e']:
                            hpgl = True
                            break

            if hpgl:
                processed_body_gcode = ''
                pa_re = re.compile(r"^PA\s*(-?\d+\.\d*),?\s*(-?\d+\.\d*)*;?$")

                # process body gcode
                for gline in gcode.splitlines():
                    match = pa_re.search(gline)
                    if match:
                        x_int = int(float(match.group(1)))
                        y_int = int(float(match.group(2)))
                        new_line = 'PA%d,%d;\n' % (x_int, y_int)
                        processed_body_gcode += new_line
                    else:
                        processed_body_gcode += gline + '\n'

                gcode = processed_body_gcode
                g = self.gc_header + '\n' + self.gc_start + '\n' + preamble + '\n' + \
                    gcode + '\n' + postamble + end_gcode
            else:
                # try:
                #     g_idx = gcode.index('G94')
                #     if preamble != '' and postamble != '':
                #         g = self.gc_header + gcode[:g_idx + 3] + '\n' + preamble + '\n' + \
                #             gcode[(g_idx + 3):] + postamble + end_gcode
                #     elif preamble == '':
                #         g = self.gc_header + gcode[:g_idx + 3] + '\n' + \
                #             gcode[(g_idx + 3):] + postamble + end_gcode
                #     elif postamble == '':
                #         g = self.gc_header + gcode[:g_idx + 3] + '\n' + preamble + '\n' + \
                #             gcode[(g_idx + 3):] + end_gcode
                #     else:
                #         g = self.gc_header + gcode[:g_idx + 3] + gcode[(g_idx + 3):] + end_gcode
                # except ValueError:
                #     self.app.inform.emit('[ERROR_NOTCL] %s' %
                #                          _("G-code does not have a G94 code.\n"
                #                            "Append Code snippet will not be used.."))
                #     g = self.gc_header + '\n' + gcode + postamble + end_gcode
                g = ''
                if preamble != '' and postamble != '':
                    g = self.gc_header + self.gc_start + '\n' + preamble + '\n' + gcode + '\n' + \
                        postamble + '\n' + end_gcode
                if preamble == '':
                    g = self.gc_header + self.gc_start + '\n' + gcode + '\n' + postamble + '\n' + end_gcode
                if postamble == '':
                    g = self.gc_header + self.gc_start + '\n' + preamble + '\n' + gcode + '\n' + end_gcode
                if preamble == '' and postamble == '':
                    g = self.gc_header + self.gc_start + '\n' + gcode + '\n' + end_gcode

        # if toolchange custom is used, replace M6 code with the code from the Toolchange Custom Text box
        # if self.ui.toolchange_cb.get_value() is True:
        #     # match = self.re_toolchange.search(g)
        #     if 'M6' in g:
        #         m6_code = self.parse_custom_toolchange_code(self.ui.toolchange_text.get_value())
        #         if m6_code is None or m6_code == '':
        #             self.app.inform.emit(
        #                 '[ERROR_NOTCL] %s' % _("Cancelled. The Toolchange Custom code is enabled but it's empty.")
        #             )
        #             return 'fail'
        #
        #         g = g.replace('M6', m6_code)
        #         self.app.inform.emit('[success] %s' % _("Toolchange G-code was replaced by a custom code."))

        lines = StringIO(g)

        # Write
        if filename is not None:
            try:
                force_windows_line_endings = self.app.defaults['cncjob_line_ending']
                if force_windows_line_endings and sys.platform != 'win32':
                    with open(filename, 'w', newline='\r\n') as f:
                        for line in lines:
                            f.write(line)
                else:
                    with open(filename, 'w') as f:
                        for line in lines:
                            f.write(line)
            except FileNotFoundError:
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("No such file or directory"))
                return
            except PermissionError:
                self.app.inform.emit(
                    '[WARNING] %s' % _("Permission denied, saving not possible.\n"
                                       "Most likely another app is holding the file open and not accessible.")
                )
                return 'fail'
        elif to_file is False:
            # Just for adding it to the recent files list.
            if self.app.defaults["global_open_style"] is False:
                self.app.file_opened.emit("cncjob", filename)
            self.app.file_saved.emit("cncjob", filename)

            self.app.inform.emit('[success] %s: %s' % (_("Saved to"), filename))
        else:
            return lines

    # def on_toolchange_custom_clicked(self, signal):
    #     """
    #     Handler for clicking toolchange custom.
    #
    #     :param signal:
    #     :return:
    #     """
    #
    #     try:
    #         if 'toolchange_custom' not in str(self.options['ppname_e']).lower():
    #             if self.ui.toolchange_cb.get_value():
    #                 self.ui.toolchange_cb.set_value(False)
    #                 self.app.inform.emit('[WARNING_NOTCL] %s' %
    #                                      _("The used preprocessor file has to have in it's name: 'toolchange_custom'")
    #                                      )
    #     except KeyError:
    #         try:
    #             for key in self.cnc_tools:
    #                 ppg = self.cnc_tools[key]['data']['ppname_g']
    #                 if 'toolchange_custom' not in str(ppg).lower():
    #                     if self.ui.toolchange_cb.get_value():
    #                         self.ui.toolchange_cb.set_value(False)
    #                         self.app.inform.emit('[WARNING_NOTCL] %s' %
    #                                              _("The used preprocessor file has to have in it's name: "
    #                                                "'toolchange_custom'"))
    #         except KeyError:
    #             self.app.inform.emit('[ERROR] %s' % _("There is no preprocessor file."))

    def get_gcode(self, preamble='', postamble=''):
        """
        We need this to be able to get_gcode separately for shell command export_gcode

        :param preamble:    Extra GCode added to the beginning of the GCode
        :param postamble:   Extra GCode added at the end of the GCode
        :return:            The modified GCode
        """
        return preamble + '\n' + self.gcode + "\n" + postamble

    def get_svg(self):
        # we need this to be able get_svg separately for shell command export_svg
        pass

    def on_plot_cb_click(self, *args):
        """
        Handler for clicking on the Plot checkbox.

        :param args:
        :return:
        """
        if self.muted_ui:
            return
        kind = self.ui.cncplot_method_combo.get_value()
        self.plot(kind=kind)
        self.read_form_item('plot')

        self.ui_disconnect()
        cb_flag = self.ui.plot_cb.isChecked()
        for row in range(self.ui.cnc_tools_table.rowCount()):
            table_cb = self.ui.cnc_tools_table.cellWidget(row, 6)
            if cb_flag:
                table_cb.setChecked(True)
            else:
                table_cb.setChecked(False)
        self.ui_connect()

    def on_plot_cb_click_table(self):
        """
        Handler for clicking the plot checkboxes added into a Table on each row. Purpose: toggle visibility for the
        tool/aperture found on that row.
        :return:
        """

        # self.ui.cnc_tools_table.cellWidget(row, 2).widget().setCheckState(QtCore.Qt.Unchecked)
        self.ui_disconnect()
        # cw = self.sender()
        # cw_index = self.ui.cnc_tools_table.indexAt(cw.pos())
        # cw_row = cw_index.row()

        kind = self.ui.cncplot_method_combo.get_value()

        self.shapes.clear(update=True)
        if self.origin_kind == "excellon":
            for r in range(self.ui.exc_cnc_tools_table.rowCount()):
                row_dia = float('%.*f' % (self.decimals, float(self.ui.exc_cnc_tools_table.item(r, 1).text())))
                for tooluid_key in self.exc_cnc_tools:
                    tooldia = float('%.*f' % (self.decimals, float(tooluid_key)))
                    if row_dia == tooldia:
                        gcode_parsed = self.exc_cnc_tools[tooluid_key]['gcode_parsed']
                        if self.ui.exc_cnc_tools_table.cellWidget(r, 6).isChecked():
                            self.plot2(tooldia=tooldia, obj=self, visible=True, gcode_parsed=gcode_parsed, kind=kind)
        else:
            for tooluid_key in self.cnc_tools:
                tooldia = float('%.*f' % (self.decimals, float(self.cnc_tools[tooluid_key]['tooldia'])))
                gcode_parsed = self.cnc_tools[tooluid_key]['gcode_parsed']
                # tool_uid = int(self.ui.cnc_tools_table.item(cw_row, 3).text())

                for r in range(self.ui.cnc_tools_table.rowCount()):
                    if int(self.ui.cnc_tools_table.item(r, 5).text()) == int(tooluid_key):
                        if self.ui.cnc_tools_table.cellWidget(r, 6).isChecked():
                            self.plot2(tooldia=tooldia, obj=self, visible=True, gcode_parsed=gcode_parsed, kind=kind)

        self.shapes.redraw()

        # make sure that the general plot is disabled if one of the row plot's are disabled and
        # if all the row plot's are enabled also enable the general plot checkbox
        cb_cnt = 0
        total_row = self.ui.cnc_tools_table.rowCount()
        for row in range(total_row):
            if self.ui.cnc_tools_table.cellWidget(row, 6).isChecked():
                cb_cnt += 1
            else:
                cb_cnt -= 1
        if cb_cnt < total_row:
            self.ui.plot_cb.setChecked(False)
        else:
            self.ui.plot_cb.setChecked(True)
        self.ui_connect()

    def plot(self, visible=None, kind='all'):
        """
        # Does all the required setup and returns False
        # if the 'ptint' option is set to False.

        :param visible: Boolean to decide if the object will be plotted as visible or disabled on canvas
        :param kind:    String. Can be "all" or "travel" or "cut". For CNCJob plotting
        :return:        None
        """
        if not FlatCAMObj.plot(self):
            return

        visible = visible if visible else self.options['plot']

        # Geometry shapes plotting
        try:
            if self.multitool is False:  # single tool usage
                try:
                    dia_plot = float(self.options["tooldia"])
                except ValueError:
                    # we may have a tuple with only one element and a comma
                    dia_plot = [float(el) for el in self.options["tooldia"].split(',') if el != ''][0]
                self.plot2(tooldia=dia_plot, obj=self, visible=visible, kind=kind)
            else:
                # I do this so the travel lines thickness will reflect the tool diameter
                # may work only for objects created within the app and not Gcode imported from elsewhere for which we
                # don't know the origin
                if self.origin_kind == "excellon":
                    if self.exc_cnc_tools:
                        for tooldia_key in self.exc_cnc_tools:
                            tooldia = float('%.*f' % (self.decimals, float(tooldia_key)))
                            gcode_parsed = self.exc_cnc_tools[tooldia_key]['gcode_parsed']
                            if not gcode_parsed:
                                continue
                            # gcode_parsed = self.gcode_parsed
                            self.plot2(tooldia=tooldia, obj=self, visible=visible, gcode_parsed=gcode_parsed, kind=kind)
                else:
                    # multiple tools usage
                    if self.cnc_tools:
                        for tooluid_key in self.cnc_tools:
                            tooldia = float('%.*f' % (self.decimals, float(self.cnc_tools[tooluid_key]['tooldia'])))
                            gcode_parsed = self.cnc_tools[tooluid_key]['gcode_parsed']
                            self.plot2(tooldia=tooldia, obj=self, visible=visible, gcode_parsed=gcode_parsed, kind=kind)

            self.shapes.redraw()
        except (ObjectDeleted, AttributeError):
            self.shapes.clear(update=True)
            if self.app.is_legacy is False:
                self.annotation.clear(update=True)

        # Annotations shapes plotting
        try:
            if self.app.is_legacy is False:
                if self.ui.annotation_cb.get_value() and visible:
                    self.plot_annotations(obj=self, visible=True)
                else:
                    self.plot_annotations(obj=self, visible=False)

        except (ObjectDeleted, AttributeError):
            if self.app.is_legacy is False:
                self.annotation.clear(update=True)

    def on_annotation_change(self, val):
        """
        Handler for toggling the annotation display by clicking a checkbox.
        :return:
        """

        if self.app.is_legacy is False:
            # self.text_col.visible = True if val == 2 else False
            # self.plot(kind=self.ui.cncplot_method_combo.get_value())
            # Annotations shapes plotting
            try:
                if self.app.is_legacy is False:
                    if val and self.ui.plot_cb.get_value():
                        self.plot_annotations(obj=self, visible=True)
                    else:
                        self.plot_annotations(obj=self, visible=False)

            except (ObjectDeleted, AttributeError):
                if self.app.is_legacy is False:
                    self.annotation.clear(update=True)

            # self.annotation.redraw()
        else:
            kind = self.ui.cncplot_method_combo.get_value()
            self.plot(kind=kind)

    def convert_units(self, units):
        """
        Units conversion used by the CNCJob objects.

        :param units:   Can be "MM" or "IN"
        :return:
        """

        log.debug("FlatCAMObj.FlatCAMECNCjob.convert_units()")

        factor = CNCjob.convert_units(self, units)
        self.options["tooldia"] = float(self.options["tooldia"]) * factor

        param_list = ['cutz', 'depthperpass', 'travelz', 'feedrate', 'feedrate_z', 'feedrate_rapid',
                      'endz', 'toolchangez']

        temp_tools_dict = {}
        tool_dia_copy = {}
        data_copy = {}

        for tooluid_key, tooluid_value in self.cnc_tools.items():
            for dia_key, dia_value in tooluid_value.items():
                if dia_key == 'tooldia':
                    dia_value *= factor
                    dia_value = float('%.*f' % (self.decimals, dia_value))
                    tool_dia_copy[dia_key] = dia_value
                if dia_key == 'offset':
                    tool_dia_copy[dia_key] = dia_value
                if dia_key == 'offset_value':
                    dia_value *= factor
                    tool_dia_copy[dia_key] = dia_value

                if dia_key == 'type':
                    tool_dia_copy[dia_key] = dia_value
                if dia_key == 'tool_type':
                    tool_dia_copy[dia_key] = dia_value
                if dia_key == 'data':
                    for data_key, data_value in dia_value.items():
                        # convert the form fields that are convertible
                        for param in param_list:
                            if data_key == param and data_value is not None:
                                data_copy[data_key] = data_value * factor
                        # copy the other dict entries that are not convertible
                        if data_key not in param_list:
                            data_copy[data_key] = data_value
                    tool_dia_copy[dia_key] = deepcopy(data_copy)
                    data_copy.clear()

                if dia_key == 'gcode':
                    tool_dia_copy[dia_key] = dia_value
                if dia_key == 'gcode_parsed':
                    tool_dia_copy[dia_key] = dia_value
                if dia_key == 'solid_geometry':
                    tool_dia_copy[dia_key] = dia_value

                # if dia_key == 'solid_geometry':
                #     tool_dia_copy[dia_key] = affinity.scale(dia_value, xfact=factor, origin=(0, 0))
                # if dia_key == 'gcode_parsed':
                #     for g in dia_value:
                #         g['geom'] = affinity.scale(g['geom'], factor, factor, origin=(0, 0))
                #
                #     tool_dia_copy['gcode_parsed'] = deepcopy(dia_value)
                #     tool_dia_copy['solid_geometry'] = unary_union([geo['geom'] for geo in dia_value])

            temp_tools_dict.update({
                tooluid_key: deepcopy(tool_dia_copy)
            })
            tool_dia_copy.clear()

        self.cnc_tools.clear()
        self.cnc_tools = deepcopy(temp_tools_dict)
