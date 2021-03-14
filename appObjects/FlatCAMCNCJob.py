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

from io import StringIO
from datetime import datetime

from appEditors.AppTextEditor import AppTextEditor
from appObjects.FlatCAMObj import *

from camlib import CNCjob

import os
import sys
import math

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

        self.app.log.debug("Creating CNCJob object...")

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
            "tools_al_travelz": self.app.defaults["tools_al_travelz"],
            "tools_al_probe_depth": self.app.defaults["tools_al_probe_depth"],
            "tools_al_probe_fr": self.app.defaults["tools_al_probe_fr"],
            "tools_al_controller": self.app.defaults["tools_al_controller"],
            "tools_al_method": self.app.defaults["tools_al_method"],
            "tools_al_mode": self.app.defaults["tools_al_mode"],
            "tools_al_rows": self.app.defaults["tools_al_rows"],
            "tools_al_columns": self.app.defaults["tools_al_columns"],
            "tools_al_grbl_jog_step": self.app.defaults["tools_al_grbl_jog_step"],
            "tools_al_grbl_jog_fr": self.app.defaults["tools_al_grbl_jog_fr"],
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
        self.tools = {}

        # the current tool that is used to generate GCode
        self.tool = None

        # flag to store if the CNCJob is part of a special group of CNCJob objects that can't be processed by the
        # default engine of FlatCAM. They generated by some of tools and are special cases of CNCJob objects.
        self.special_group = None

        # for now it show if the plot will be done for multi-tool CNCJob (True) or for single tool
        # (like the one in the TCL Command), False
        self.multitool = False

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

        self.prepend_snippet = ''
        self.append_snippet = ''
        self.gc_header = self.gcode_header()
        self.gc_start = ''
        self.gc_end = ''

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from predecessors.
        self.ser_attrs += [
            'options', 'kind', 'origin_kind', 'cnc_tools', 'exc_cnc_tools', 'multitool', 'append_snippet',
            'prepend_snippet', 'gc_header'
        ]

    def build_ui(self):
        self.ui_disconnect()

        FlatCAMObj.build_ui(self)
        self.units = self.app.defaults['units'].upper()

        # if the FlatCAM object is Excellon don't build the CNC Tools Table but hide it
        self.ui.cnc_tools_table.hide()
        self.ui.exc_cnc_tools_table.hide()

        if self.options['type'].lower() == 'geometry':
            self.ui.cnc_tools_table.show()
            self.build_cnc_tools_table()

        if self.options['type'].lower() == 'excellon':
            self.ui.exc_cnc_tools_table.show()
            self.build_excellon_cnc_tools()

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
        # for the case that self.tools is empty: old projects
        if not self.tools:
            return

        n = len(self.tools)
        self.ui.exc_cnc_tools_table.setRowCount(n)

        row_no = 1
        for t_id, dia_value in self.tools.items():
            tooldia = self.tools[t_id]['tooldia']

            row_no = t_id - 1

            t_id_item = QtWidgets.QTableWidgetItem('%d' % int(t_id))
            dia_item = QtWidgets.QTableWidgetItem('%.*f' % (self.decimals, float(tooldia)))
            nr_drills_item = QtWidgets.QTableWidgetItem('%d' % int(dia_value['nr_drills']))
            nr_slots_item = QtWidgets.QTableWidgetItem('%d' % int(dia_value['nr_slots']))
            try:
                offset_val = self.app.dec_format(float(dia_value['offset']), self.decimals) + self.z_cut
            except KeyError:
                offset_val = self.app.dec_format(float(dia_value['offset_z']), self.decimals) + self.z_cut

            cutz_item = QtWidgets.QTableWidgetItem('%f' % offset_val)

            t_id_item.setFlags(QtCore.Qt.ItemIsEnabled)
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

            if self.ui.plot_cb.isChecked():
                plot_item.setChecked(True)

            self.ui.exc_cnc_tools_table.setItem(row_no, 0, t_id_item)  # Tool name/id
            self.ui.exc_cnc_tools_table.setItem(row_no, 1, dia_item)  # Diameter
            self.ui.exc_cnc_tools_table.setItem(row_no, 2, nr_drills_item)  # Nr of drills
            self.ui.exc_cnc_tools_table.setItem(row_no, 3, nr_slots_item)  # Nr of slots

            # ## REMEMBER: THIS COLUMN IS HIDDEN IN OBJECTUI.PY # ##
            self.ui.exc_cnc_tools_table.setItem(row_no, 4, t_id_item)  # Tool unique ID)
            self.ui.exc_cnc_tools_table.setItem(row_no, 5, cutz_item)
            self.ui.exc_cnc_tools_table.setCellWidget(row_no, 6, plot_item)

        for row in range(row_no):
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
        })

        # Fill form fields only on object create
        self.to_form()

        # this means that the object that created this CNCJob was an Excellon or Geometry
        try:
            if self.travel_distance:
                self.ui.t_distance_label.show()
                self.ui.t_distance_entry.setVisible(True)
                self.ui.t_distance_entry.setDisabled(True)
                self.ui.t_distance_entry.set_value(self.app.dec_format(self.travel_distance, self.decimals))
                self.ui.units_label.setText(str(self.units).lower())
                self.ui.units_label.setDisabled(True)

                self.ui.t_time_label.show()
                self.ui.t_time_entry.setVisible(True)
                self.ui.t_time_entry.setDisabled(True)
                # if time is more than 1 then we have minutes, else we have seconds
                if self.routing_time > 1:
                    time_r = self.app.dec_format(math.ceil(float(self.routing_time)), self.decimals)
                    self.ui.t_time_entry.set_value(time_r)
                    self.ui.units_time_label.setText('min')
                else:
                    time_r = self.routing_time * 60
                    time_r = self.app.dec_format(math.ceil(float(time_r)), self.decimals)
                    self.ui.t_time_entry.set_value(time_r)
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

        # #############################################################################################################
        # ##################################### SIGNALS CONNECTIONS ###################################################
        # #############################################################################################################

        self.ui.level.toggled.connect(self.on_level_changed)

        # annotation signal
        try:
            self.ui.annotation_cb.stateChanged.disconnect(self.on_annotation_change)
        except (TypeError, AttributeError):
            pass
        self.ui.annotation_cb.stateChanged.connect(self.on_annotation_change)

        # set if to display text annotations
        self.ui.annotation_cb.set_value(self.app.defaults["cncjob_annotation"])

        # update plot button - active only for SingleGeo type objects
        self.ui.updateplot_button.clicked.connect(self.on_updateplot_button_click)

        # Plot Kind
        self.ui.cncplot_method_combo.activated_custom.connect(self.on_plot_kind_change)

        # Export/REview GCode buttons signals
        self.ui.export_gcode_button.clicked.connect(self.on_exportgcode_button_click)
        self.ui.review_gcode_button.clicked.connect(self.on_review_code_click)

        # Editor Signal
        self.ui.editor_button.clicked.connect(lambda: self.app.object2editor())

        # Properties
        self.ui.info_button.toggled.connect(self.on_properties)
        self.calculations_finished.connect(self.update_area_chull)
        self.ui.treeWidget.itemExpanded.connect(self.on_properties_expanded)
        self.ui.treeWidget.itemCollapsed.connect(self.on_properties_expanded)

        # Include CNC Job Snippets changed
        self.ui.snippets_cb.toggled.connect(self.on_update_source_file)

        self.ui.autolevel_button.clicked.connect(lambda: self.app.levelling_tool.run(toggle=True))

        # ###################################### END Signal connections ###############################################
        # #############################################################################################################

        self.append_snippet = self.app.defaults['cncjob_append']
        self.prepend_snippet = self.app.defaults['cncjob_prepend']

        if self.append_snippet != '' or self.prepend_snippet != '':
            self.ui.snippets_cb.set_value(True)

        # On CNCJob object creation, generate the GCode
        preamble = ''
        postamble = ''
        if self.append_snippet != '' or self.prepend_snippet != '':
            preamble = self.prepend_snippet
            postamble = self.append_snippet
        gc = self.export_gcode(preamble=preamble, postamble=postamble, to_file=True)

        # set the Source File attribute with the calculated GCode
        try:
            # gc is StringIO
            self.source_file = gc.getvalue()
        except AttributeError:
            # gc is text
            self.source_file = gc

        # Show/Hide Advanced Options
        app_mode = self.app.defaults["global_app_level"]
        self.change_level(app_mode)

    def change_level(self, level):
        """

        :param level:   application level: either 'b' or 'a'
        :type level:    str
        :return:
        """

        if level == 'a':
            self.ui.level.setChecked(True)
        else:
            self.ui.level.setChecked(False)
        self.on_level_changed(self.ui.level.isChecked())

    def on_level_changed(self, checked):
        if not checked:
            self.ui.level.setText('%s' % _('Beginner'))
            self.ui.level.setStyleSheet("""
                                                QToolButton
                                                {
                                                    color: green;
                                                }
                                                """)

            self.ui.annotation_cb.hide()
        else:
            self.ui.level.setText('%s' % _('Advanced'))
            self.ui.level.setStyleSheet("""
                                                QToolButton
                                                {
                                                    color: red;
                                                }
                                                """)

            self.ui.annotation_cb.show()

    def ui_connect(self):
        for row in range(self.ui.cnc_tools_table.rowCount()):
            self.ui.cnc_tools_table.cellWidget(row, 6).clicked.connect(self.on_plot_cb_click_table)
        for row in range(self.ui.exc_cnc_tools_table.rowCount()):
            self.ui.exc_cnc_tools_table.cellWidget(row, 6).clicked.connect(self.on_plot_cb_click_table)
        self.ui.plot_cb.stateChanged.connect(self.on_plot_cb_click)

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

    def on_properties(self, state):
        if state:
            self.ui.info_frame.show()
        else:
            self.ui.info_frame.hide()
            return

        self.ui.treeWidget.clear()
        self.add_properties_items(obj=self, treeWidget=self.ui.treeWidget)

        self.ui.treeWidget.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.MinimumExpanding)
        # make sure that the FCTree widget columns are resized to content
        self.ui.treeWidget.resize_sig.emit()

    def on_properties_expanded(self):
        for col in range(self.treeWidget.columnCount()):
            self.ui.treeWidget.resizeColumnToContents(col)

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

    def export_gcode_handler(self, filename, is_gcode=True, rename_object=True):
        # preamble = ''
        # postamble = ''
        filename = str(filename)

        if filename == '':
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Export cancelled ..."))
            return
        else:
            if is_gcode is True:
                used_extension = filename.rpartition('.')[2]
                self.update_filters(last_ext=used_extension, filter_string='cncjob_save_filters')

        if rename_object:
            new_name = os.path.split(str(filename))[1].rpartition('.')[0]
            self.ui.name_entry.set_value(new_name)
            self.on_name_activate(silent=True)

        # try:
        #     if self.ui.snippets_cb.get_value():
        #         preamble = self.prepend_snippet
        #         postamble = self.append_snippet
        #     gc = self.export_gcode(filename, preamble=preamble, postamble=postamble)
        # except Exception as err:
        #     log.error("CNCJobObject.export_gcode_handler() --> %s" % str(err))
        #     gc = self.export_gcode(filename)
        #
        # if gc == 'fail':
        #     return

        if self.source_file == '':
            return 'fail'

        try:
            force_windows_line_endings = self.app.defaults['cncjob_line_ending']
            if force_windows_line_endings and sys.platform != 'win32':
                with open(filename, 'w', newline='\r\n') as f:
                    for line in self.source_file:
                        f.write(line)
            else:
                with open(filename, 'w') as f:
                    for line in self.source_file:
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

        # preamble = self.prepend_snippet
        # postamble = self.append_snippet
        #
        # gco = self.export_gcode(preamble=preamble, postamble=postamble, to_file=True)
        # if gco == 'fail':
        #     return
        # else:
        #     self.app.gcode_edited = gco
        self.app.gcode_edited = self.source_file

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
            # self.gcode_editor_tab.load_text(self.app.gcode_edited.getvalue(), move_to_start=True, clear_text=True)
            self.gcode_editor_tab.load_text(self.app.gcode_edited, move_to_start=True, clear_text=True)
        except Exception as e:
            self.app.log.error('FlatCAMCNCJob.on_review_code_click() -->%s' % str(e))
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
        preamble = ''
        postamble = ''
        if self.ui.snippets_cb.get_value():
            preamble = self.prepend_snippet
            postamble = self.append_snippet

        gco = self.export_gcode(preamble=preamble, postamble=postamble, to_file=True)
        if gco == 'fail':
            self.app.inform.emit('[ERROR_NOTCL] %s %s...' % (_('Failed.'), _('CNC Machine Code could not be updated')))
            return
        else:
            self.source_file = gco.getvalue()
            self.app.inform.emit('[success] %s...' % _('CNC Machine Code was updated'))

    def gcode_header(self, comment_start_symbol=None, comment_stop_symbol=None):
        """
        Will create a header to be added to all GCode files generated by FlatCAM

        :param comment_start_symbol:    A symbol to be used as the first symbol in a comment
        :param comment_stop_symbol:     A symbol to be used as the last symbol in a comment
        :return:                        A string with a GCode header
        """

        self.app.log.debug("FlatCAMCNCJob.gcode_header()")
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
            # self.app.log.debug("FlatCAMCNCJob.gcode_header() error: --> %s" % str(e))
            pass

        try:
            if 'marlin' in self.options['ppname_e'].lower() or 'repetier' in self.options['ppname_e'].lower():
                marlin = True
        except KeyError:
            # self.app.log.debug("FlatCAMCNCJob.gcode_header(): --> There is no such self.option: %s" % str(e))
            pass

        try:
            if "toolchange_probe" in self.options['ppname_e'].lower():
                probe_pp = True
        except KeyError:
            # self.app.log.debug("FlatCAMCNCJob.gcode_header(): --> There is no such self.option: %s" % str(e))
            pass

        if marlin is True:
            gcode += ';Marlin(Repetier) G-CODE GENERATED BY FLATCAM v%s - www.flatcam.org - Version Date:    %s\n' % \
                     (str(self.app.version), str(self.app.version_date)) + '\n'

            gcode += ';Name: ' + str(self.options['name']) + '\n'
            gcode += ';Type: ' + "G-code from " + str(self.options['type']) + '\n'

            gcode += ';Units: ' + self.units.upper() + '\n' + "\n"
            gcode += ';Created on ' + time_str + '\n' + '\n'
        elif hpgl is True:
            gcode += 'CO "HPGL CODE GENERATED BY FLATCAM v%s - www.flatcam.org - Version Date:    %s' % \
                     (str(self.app.version), str(self.app.version_date)) + '";\n'

            gcode += 'CO "Name: ' + str(self.options['name']) + '";\n'
            gcode += 'CO "Type: ' + "HPGL code from " + str(self.options['type']) + '";\n'

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

            gcode += '(Units: ' + self.units.upper() + ')\n' + "\n"
            gcode += '(Created on ' + time_str + ')\n' + '\n'
        else:
            gcode += '%sG-CODE GENERATED BY FLATCAM v%s - www.flatcam.org - Version Date: %s%s\n' % \
                     (start_comment, str(self.app.version), str(self.app.version_date), stop_comment) + '\n'

            gcode += '%sName: ' % start_comment + str(self.options['name']) + '%s\n' % stop_comment
            gcode += '%sType: ' % start_comment + "G-code from " + str(self.options['type']) + '%s\n' % stop_comment

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
            include_header = self.app.preprocessors[self.cnc_tools[first_key]['data']['tools_mill_ppname_g']]
            include_header = include_header.include_header

        # if this dict is not empty then the object is an Excellon object
        if self.options['type'].lower() == 'excellon':
            # for the case that self.tools is empty: old projects
            try:
                first_key = next(iter(self.tools))
                try:
                    include_header = self.app.preprocessors[
                        self.tools[first_key]['data']['tools_drill_ppname_e']
                    ].include_header
                except KeyError:
                    # for older loaded projects
                    include_header = self.app.preprocessors[
                        self.tools[first_key]['data']['ppname_e']
                    ].include_header
            except TypeError:
                # when self.tools is empty - old projects
                include_header = self.app.preprocessors['default'].include_header

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
                # for the case that self.tools is empty: old projects
                try:
                    if self.options['type'].lower() == 'excellon':
                        for tooluid_key in self.tools:
                            for key, value in self.tools[tooluid_key].items():
                                if key == 'gcode' and value:
                                    gcode += value
                                    break
                    else:
                        for tooluid_key in self.cnc_tools:
                            for key, value in self.cnc_tools[tooluid_key].items():
                                if key == 'gcode' and value:
                                    gcode += value
                                    break
                except TypeError:
                    pass
            else:
                gcode += self.gcode

            end_gcode = self.gcode_footer() if self.app.defaults['cncjob_footer'] is True else ''

            # detect if using a HPGL preprocessor
            hpgl = False
            # for the case that self.tools is empty: old projects
            try:
                if self.options['type'].lower() == 'geometry':
                    for key in self.cnc_tools:
                        if 'tools_mill_ppname_g' in self.cnc_tools[key]['data']:
                            if 'hpgl' in self.cnc_tools[key]['data']['tools_mill_ppname_g']:
                                hpgl = True
                                break
                elif self.options['type'].lower() == 'excellon':
                    for key in self.tools:
                        if 'ppname_e' in self.tools[key]['data']:
                            if 'hpgl' in self.tools[key]['data']['ppname_e']:
                                hpgl = True
                                break
            except TypeError:
                hpgl = False

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
        if self.options['type'].lower() == "excellon":
            for r in range(self.ui.exc_cnc_tools_table.rowCount()):
                row_dia = float('%.*f' % (self.decimals, float(self.ui.exc_cnc_tools_table.item(r, 1).text())))
                for tooluid_key in self.tools:
                    tooldia = float('%.*f' % (self.decimals, float(self.tools[tooluid_key]['tooldia'])))
                    if row_dia == tooldia:
                        gcode_parsed = self.tools[tooluid_key]['gcode_parsed']
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
                if self.options['type'].lower() == "excellon":
                    try:
                        dia_plot = float(self.options["tooldia"])
                    except ValueError:
                        # we may have a tuple with only one element and a comma
                        dia_plot = [float(el) for el in self.options["tooldia"].split(',') if el != ''][0]
                else:
                    try:
                        dia_plot = float(self.options["tools_mill_tooldia"])
                    except ValueError:
                        # we may have a tuple with only one element and a comma
                        dia_plot = [float(el) for el in self.options["tools_mill_tooldia"].split(',') if el != ''][0]
                self.plot2(tooldia=dia_plot, obj=self, visible=visible, kind=kind)
            else:
                # I do this so the travel lines thickness will reflect the tool diameter
                # may work only for objects created within the app and not Gcode imported from elsewhere for which we
                # don't know the origin
                if self.options['type'].lower() == "excellon":
                    if self.tools:
                        for toolid_key in self.tools:
                            tooldia = self.app.dec_format(float(self.tools[toolid_key]['tooldia']), self.decimals)
                            gcode_parsed = self.tools[toolid_key]['gcode_parsed']
                            if not gcode_parsed:
                                continue
                            # gcode_parsed = self.gcode_parsed
                            self.plot2(tooldia=tooldia, obj=self, visible=visible, gcode_parsed=gcode_parsed, kind=kind)
                else:
                    # multiple tools usage
                    if self.cnc_tools:
                        for tooluid_key in self.cnc_tools:
                            tooldia = self.app.dec_format(
                                float(self.cnc_tools[tooluid_key]['data']['tools_mill_tooldia']),
                                self.decimals
                            )
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
