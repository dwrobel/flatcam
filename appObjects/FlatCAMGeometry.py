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

from shapely.geometry import MultiLineString, LineString, LinearRing, box
import shapely.affinity as affinity

from camlib import Geometry, grace

from appObjects.FlatCAMObj import *

import ezdxf
import math
import numpy as np
from copy import deepcopy
import traceback
from collections import defaultdict
from functools import reduce

import simplejson as json

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GeometryObject(FlatCAMObj, Geometry):
    """
    Geometric object not associated with a specific
    format.
    """
    optionChanged = QtCore.pyqtSignal(str)
    builduiSig = QtCore.pyqtSignal()
    launch_job = QtCore.pyqtSignal()

    ui_type = GeometryObjectUI

    def __init__(self, name):
        self.decimals = self.app.decimals

        self.circle_steps = int(self.app.defaults["geometry_circle_steps"])

        FlatCAMObj.__init__(self, name)
        Geometry.__init__(self, geo_steps_per_circle=self.circle_steps)

        self.kind = "geometry"

        self.options.update({
            "plot": True,
            "multicolored": False,
            "cutz": -0.002,
            "vtipdia": 0.1,
            "vtipangle": 30,
            "travelz": 0.1,
            "feedrate": 5.0,
            "feedrate_z": 5.0,
            "feedrate_rapid": 5.0,
            "spindlespeed": 0,
            "dwell": True,
            "dwelltime": 1000,
            "multidepth": False,
            "depthperpass": 0.002,
            "extracut": False,
            "extracut_length": 0.1,
            "endz": 2.0,
            "endxy": '',
            "area_exclusion": False,
            "area_shape": "polygon",
            "area_strategy": "over",
            "area_overz": 1.0,

            "startz": None,
            "toolchange": False,
            "toolchangez": 1.0,
            "toolchangexy": "0.0, 0.0",
            "ppname_g": 'default',
            "z_pdepth": -0.02,
            "feedrate_probe": 3.0,
        })

        if "cnctooldia" not in self.options:
            if type(self.app.defaults["geometry_cnctooldia"]) == float:
                self.options["cnctooldia"] = self.app.defaults["geometry_cnctooldia"]
            else:
                try:
                    tools_string = self.app.defaults["geometry_cnctooldia"].split(",")
                    tools_diameters = [eval(a) for a in tools_string if a != '']
                    self.options["cnctooldia"] = tools_diameters[0] if tools_diameters else 0.0
                except Exception as e:
                    log.debug("FlatCAMObj.GeometryObject.init() --> %s" % str(e))

        self.options["startz"] = self.app.defaults["geometry_startz"]

        # this will hold the tool unique ID that is useful when having multiple tools with same diameter
        self.tooluid = 0

        '''
            self.tools = {}
            This is a dictionary. Each dict key is associated with a tool used in geo_tools_table. The key is the 
            tool_id of the tools and the value is another dict that will hold the data under the following form:
                {tooluid:   {
                            'tooldia': 1,
                            'offset': 'Path',
                            'offset_value': 0.0
                            'type': 'Rough',
                            'tool_type': 'C1',
                            'data': self.default_tool_data
                            'solid_geometry': []
                            }
                }
        '''
        self.tools = {}

        # this dict is to store those elements (tools) of self.tools that are selected in the self.geo_tools_table
        # those elements are the ones used for generating GCode
        self.sel_tools = {}

        self.offset_item_options = ["Path", "In", "Out", "Custom"]
        self.type_item_options = ['Iso', 'Rough', 'Finish']
        self.tool_type_item_options = ["C1", "C2", "C3", "C4", "B", "V"]

        # flag to store if the V-Shape tool is selected in self.ui.geo_tools_table
        self.v_tool_type = None

        # flag to store if the Geometry is type 'multi-geometry' meaning that each tool has it's own geometry
        # the default value is False
        self.multigeo = False

        # flag to store if the geometry is part of a special group of geometries that can't be processed by the default
        # engine of FlatCAM. Most likely are generated by some of tools and are special cases of geometries.
        self.special_group = None

        self.old_pp_state = self.app.defaults["geometry_multidepth"]
        self.old_toolchangeg_state = self.app.defaults["geometry_toolchange"]
        self.units_found = self.app.defaults['units']

        # this variable can be updated by the Object that generates the geometry
        self.tool_type = 'C1'

        # save here the old value for the Cut Z before it is changed by selecting a V-shape type tool in the tool table
        self.old_cutz = self.app.defaults["geometry_cutz"]

        self.fill_color = self.app.defaults['geometry_plot_line']
        self.outline_color = self.app.defaults['geometry_plot_line']
        self.alpha_level = 'FF'

        self.param_fields = {}

        # store here the state of the exclusion checkbox state to be restored after building the UI
        self.exclusion_area_cb_is_checked = self.app.defaults["geometry_area_exclusion"]

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from predecessors.
        self.ser_attrs += ['options', 'kind', 'multigeo', 'fill_color', 'outline_color', 'alpha_level']

    def build_ui(self):
        self.ui_disconnect()
        FlatCAMObj.build_ui(self)

        # Area Exception - exclusion shape added signal
        # first disconnect it from any other object
        try:
            self.app.exc_areas.e_shape_modified.disconnect()
        except (TypeError, AttributeError):
            pass
        # then connect it to the current build_ui() method
        self.app.exc_areas.e_shape_modified.connect(self.update_exclusion_table)

        self.units = self.app.defaults['units']

        row_idx = 0

        n = len(self.tools)
        self.ui.geo_tools_table.setRowCount(n)

        for tooluid_key, tooluid_value in self.tools.items():

            # -------------------- ID ------------------------------------------ #
            tool_id = QtWidgets.QTableWidgetItem('%d' % int(row_idx + 1))
            tool_id.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.ui.geo_tools_table.setItem(row_idx, 0, tool_id)  # Tool name/id

            # Make sure that the tool diameter when in MM is with no more than 2 decimals.
            # There are no tool bits in MM with more than 3 decimals diameter.
            # For INCH the decimals should be no more than 3. There are no tools under 10mils.

            # -------------------- DIAMETER ------------------------------------- #
            dia_item = QtWidgets.QTableWidgetItem('%.*f' % (self.decimals, float(tooluid_value['tooldia'])))
            dia_item.setFlags(QtCore.Qt.ItemIsEnabled)
            self.ui.geo_tools_table.setItem(row_idx, 1, dia_item)  # Diameter

            # -------------------- OFFSET   ------------------------------------- #
            offset_item = FCComboBox(policy=False)
            for item in self.offset_item_options:
                offset_item.addItem(item)
            idx = offset_item.findText(tooluid_value['offset'])
            # protection against having this translated or loading a project with translated values
            if idx == -1:
                offset_item.setCurrentIndex(0)
            else:
                offset_item.setCurrentIndex(idx)
            self.ui.geo_tools_table.setCellWidget(row_idx, 2, offset_item)

            # -------------------- TYPE     ------------------------------------- #
            type_item = FCComboBox(policy=False)
            for item in self.type_item_options:
                type_item.addItem(item)
            idx = type_item.findText(tooluid_value['type'])
            # protection against having this translated or loading a project with translated values
            if idx == -1:
                type_item.setCurrentIndex(0)
            else:
                type_item.setCurrentIndex(idx)
            self.ui.geo_tools_table.setCellWidget(row_idx, 3, type_item)

            # -------------------- TOOL TYPE ------------------------------------- #
            tool_type_item = FCComboBox(policy=False)
            for item in self.tool_type_item_options:
                tool_type_item.addItem(item)
            idx = tool_type_item.findText(tooluid_value['tool_type'])
            # protection against having this translated or loading a project with translated values
            if idx == -1:
                tool_type_item.setCurrentIndex(0)
            else:
                tool_type_item.setCurrentIndex(idx)
            self.ui.geo_tools_table.setCellWidget(row_idx, 4, tool_type_item)

            # -------------------- TOOL UID   ------------------------------------- #
            tool_uid_item = QtWidgets.QTableWidgetItem(str(tooluid_key))
            # ## REMEMBER: THIS COLUMN IS HIDDEN IN OBJECTUI.PY ###
            self.ui.geo_tools_table.setItem(row_idx, 5, tool_uid_item)  # Tool unique ID

            # -------------------- PLOT       ------------------------------------- #
            plot_item = FCCheckBox()
            plot_item.setLayoutDirection(QtCore.Qt.RightToLeft)
            if self.ui.plot_cb.isChecked():
                plot_item.setChecked(True)
            self.ui.geo_tools_table.setCellWidget(row_idx, 6, plot_item)

            # set an initial value for the OFFSET ENTRY
            try:
                self.ui.tool_offset_entry.set_value(tooluid_value['offset_value'])
            except Exception as e:
                log.debug("build_ui() --> Could not set the 'offset_value' key in self.tools. Error: %s" % str(e))

            row_idx += 1

        # make the diameter column editable
        for row in range(row_idx):
            self.ui.geo_tools_table.item(row, 1).setFlags(QtCore.Qt.ItemIsSelectable |
                                                          QtCore.Qt.ItemIsEditable |
                                                          QtCore.Qt.ItemIsEnabled)

        # sort the tool diameter column
        # self.ui.geo_tools_table.sortItems(1)
        # all the tools are selected by default
        # self.ui.geo_tools_table.selectColumn(0)

        self.ui.geo_tools_table.resizeColumnsToContents()
        self.ui.geo_tools_table.resizeRowsToContents()

        vertical_header = self.ui.geo_tools_table.verticalHeader()
        # vertical_header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        vertical_header.hide()
        self.ui.geo_tools_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        horizontal_header = self.ui.geo_tools_table.horizontalHeader()
        horizontal_header.setMinimumSectionSize(10)
        horizontal_header.setDefaultSectionSize(70)
        horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(0, 20)
        horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        # horizontal_header.setColumnWidth(2, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(4, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(4, 40)
        horizontal_header.setSectionResizeMode(6, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(4, 17)
        # horizontal_header.setStretchLastSection(True)
        self.ui.geo_tools_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.ui.geo_tools_table.setColumnWidth(0, 20)
        self.ui.geo_tools_table.setColumnWidth(4, 40)
        self.ui.geo_tools_table.setColumnWidth(6, 17)

        # self.ui.geo_tools_table.setSortingEnabled(True)

        self.ui.geo_tools_table.setMinimumHeight(self.ui.geo_tools_table.getHeight())
        self.ui.geo_tools_table.setMaximumHeight(self.ui.geo_tools_table.getHeight())

        # update UI for all rows - useful after units conversion but only if there is at least one row
        row_cnt = self.ui.geo_tools_table.rowCount()
        if row_cnt > 0:
            for r in range(row_cnt):
                self.update_ui(r)

        # select only the first tool / row
        selected_row = 0
        try:
            self.select_tools_table_row(selected_row, clearsel=True)
            # update the Geometry UI
            self.update_ui()
        except Exception as e:
            # when the tools table is empty there will be this error but once the table is populated it will go away
            log.debug(str(e))

        # disable the Plot column in Tool Table if the geometry is SingleGeo as it is not needed
        # and can create some problems
        if self.multigeo is False:
            self.ui.geo_tools_table.setColumnHidden(6, True)
        else:
            self.ui.geo_tools_table.setColumnHidden(6, False)

        self.set_tool_offset_visibility(selected_row)

        # -----------------------------
        # Build Exclusion Areas section
        # -----------------------------
        e_len = len(self.app.exc_areas.exclusion_areas_storage)
        self.ui.exclusion_table.setRowCount(e_len)

        area_id = 0

        for area in range(e_len):
            area_id += 1

            area_dict = self.app.exc_areas.exclusion_areas_storage[area]

            area_id_item = QtWidgets.QTableWidgetItem('%d' % int(area_id))
            area_id_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.ui.exclusion_table.setItem(area, 0, area_id_item)  # Area id

            object_item = QtWidgets.QTableWidgetItem('%s' % area_dict["obj_type"])
            object_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.ui.exclusion_table.setItem(area, 1, object_item)  # Origin Object

            strategy_item = QtWidgets.QTableWidgetItem('%s' % area_dict["strategy"])
            strategy_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.ui.exclusion_table.setItem(area, 2, strategy_item)  # Strategy

            overz_item = QtWidgets.QTableWidgetItem('%s' % area_dict["overz"])
            overz_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.ui.exclusion_table.setItem(area, 3, overz_item)  # Over Z

        self.ui.exclusion_table.resizeColumnsToContents()
        self.ui.exclusion_table.resizeRowsToContents()

        area_vheader = self.ui.exclusion_table.verticalHeader()
        area_vheader.hide()
        self.ui.exclusion_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        area_hheader = self.ui.exclusion_table.horizontalHeader()
        area_hheader.setMinimumSectionSize(10)
        area_hheader.setDefaultSectionSize(70)

        area_hheader.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        area_hheader.resizeSection(0, 20)
        area_hheader.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        area_hheader.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        area_hheader.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)

        # area_hheader.setStretchLastSection(True)
        self.ui.exclusion_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.ui.exclusion_table.setColumnWidth(0, 20)

        self.ui.exclusion_table.setMinimumHeight(self.ui.exclusion_table.getHeight())
        self.ui.exclusion_table.setMaximumHeight(self.ui.exclusion_table.getHeight())

        # End Build Exclusion Areas
        # -----------------------------

        # HACK: for whatever reasons the name in Selected tab is reverted to the original one after a successful rename
        # done in the collection view but only for Geometry objects. Perhaps some references remains. Should be fixed.
        self.ui.name_entry.set_value(self.options['name'])
        self.ui_connect()

        self.ui.e_cut_entry.setDisabled(False) if self.ui.extracut_cb.get_value() else \
            self.ui.e_cut_entry.setDisabled(True)

        # set the text on tool_data_label after loading the object
        sel_rows = []
        sel_items = self.ui.geo_tools_table.selectedItems()
        for it in sel_items:
            new_row = it.row()
            if new_row not in sel_rows:
                sel_rows.append(new_row)
        if len(sel_rows) > 1:
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("Multiple Tools"))
            )

    def set_ui(self, ui):
        FlatCAMObj.set_ui(self, ui)

        log.debug("GeometryObject.set_ui()")

        assert isinstance(self.ui, GeometryObjectUI), \
            "Expected a GeometryObjectUI, got %s" % type(self.ui)

        self.units = self.app.defaults['units'].upper()
        self.units_found = self.app.defaults['units']

        # make sure the preprocessor combobox is clear
        self.ui.pp_geometry_name_cb.clear()
        # populate preprocessor names in the combobox
        for name in list(self.app.preprocessors.keys()):
            self.ui.pp_geometry_name_cb.addItem(name)
        # add tooltips
        for it in range(self.ui.pp_geometry_name_cb.count()):
            self.ui.pp_geometry_name_cb.setItemData(
                it, self.ui.pp_geometry_name_cb.itemText(it), QtCore.Qt.ToolTipRole)

        self.form_fields.update({
            "plot": self.ui.plot_cb,
            "multicolored": self.ui.multicolored_cb,
            "cutz": self.ui.cutz_entry,
            "vtipdia": self.ui.tipdia_entry,
            "vtipangle": self.ui.tipangle_entry,
            "travelz": self.ui.travelz_entry,
            "feedrate": self.ui.cncfeedrate_entry,
            "feedrate_z": self.ui.feedrate_z_entry,
            "feedrate_rapid": self.ui.feedrate_rapid_entry,
            "spindlespeed": self.ui.cncspindlespeed_entry,
            "dwell": self.ui.dwell_cb,
            "dwelltime": self.ui.dwelltime_entry,
            "multidepth": self.ui.mpass_cb,
            "ppname_g": self.ui.pp_geometry_name_cb,
            "z_pdepth": self.ui.pdepth_entry,
            "feedrate_probe": self.ui.feedrate_probe_entry,
            "depthperpass": self.ui.maxdepth_entry,
            "extracut": self.ui.extracut_cb,
            "extracut_length": self.ui.e_cut_entry,
            "toolchange": self.ui.toolchangeg_cb,
            "toolchangez": self.ui.toolchangez_entry,
            "endz": self.ui.endz_entry,
            "endxy": self.ui.endxy_entry,
            "cnctooldia": self.ui.addtool_entry,
            "area_exclusion": self.ui.exclusion_cb,
            "area_shape": self.ui.area_shape_radio,
            "area_strategy": self.ui.strategy_radio,
            "area_overz": self.ui.over_z_entry,
            "polish": self.ui.polish_cb,
            "polish_dia": self.ui.polish_dia_entry,
            "polish_pressure": self.ui.polish_pressure_entry,
            "polish_travelz": self.ui.polish_travelz_entry,
            "polish_margin": self.ui.polish_margin_entry,
            "polish_overlap": self.ui.polish_over_entry,
            "polish_method": self.ui.polish_method_combo,
        })

        self.param_fields.update({
            "vtipdia": self.ui.tipdia_entry,
            "vtipangle": self.ui.tipangle_entry,
            "cutz": self.ui.cutz_entry,
            "depthperpass": self.ui.maxdepth_entry,
            "multidepth": self.ui.mpass_cb,
            "travelz": self.ui.travelz_entry,
            "feedrate": self.ui.cncfeedrate_entry,
            "feedrate_z": self.ui.feedrate_z_entry,
            "feedrate_rapid": self.ui.feedrate_rapid_entry,
            "extracut": self.ui.extracut_cb,
            "extracut_length": self.ui.e_cut_entry,
            "spindlespeed": self.ui.cncspindlespeed_entry,
            "dwelltime": self.ui.dwelltime_entry,
            "dwell": self.ui.dwell_cb,
            "pdepth": self.ui.pdepth_entry,
            "pfeedrate": self.ui.feedrate_probe_entry,
        })
        # Fill form fields only on object create
        self.to_form()

        # update the changes in UI depending on the selected preprocessor in Preferences
        # after this moment all the changes in the Posprocessor combo will be handled by the activated signal of the
        # self.ui.pp_geometry_name_cb combobox
        self.on_pp_changed()

        self.ui.tipdialabel.hide()
        self.ui.tipdia_entry.hide()
        self.ui.tipanglelabel.hide()
        self.ui.tipangle_entry.hide()
        self.ui.cutz_entry.setDisabled(False)

        # store here the default data for Geometry Data
        self.default_data = {}

        for opt_key, opt_val in self.app.options.items():
            if opt_key.find('geometry' + "_") == 0:
                oname = opt_key[len('geometry') + 1:]
                self.default_data[oname] = self.app.options[opt_key]
            if opt_key.find('tools_mill' + "_") == 0:
                oname = opt_key[len('tools_mill') + 1:]
                self.default_data[oname] = self.app.options[opt_key]
        # fill in self.default_data values from self.options
        # for def_key in self.default_data:
        #     for opt_key, opt_val in self.options.items():
        #         if def_key == opt_key:
        #             self.default_data[def_key] = deepcopy(opt_val)

        if type(self.options["cnctooldia"]) == float:
            tools_list = [self.options["cnctooldia"]]
        else:
            try:
                temp_tools = self.options["cnctooldia"].split(",")
                tools_list = [
                    float(eval(dia)) for dia in temp_tools if dia != ''
                ]
            except Exception as e:
                log.error("GeometryObject.set_ui() -> At least one tool diameter needed. "
                          "Verify in Edit -> Preferences -> Geometry General -> Tool dia. %s" % str(e))
                return

        self.tooluid += 1

        if not self.tools:
            for toold in tools_list:
                new_data = deepcopy(self.default_data)
                self.tools.update({
                    self.tooluid: {
                        'tooldia': self.app.dec_format(float(toold), self.decimals),
                        'offset': 'Path',
                        'offset_value': 0.0,
                        'type': 'Rough',
                        'tool_type': self.tool_type,
                        'data': new_data,
                        'solid_geometry': self.solid_geometry
                    }
                })
                self.tooluid += 1
        else:
            # if self.tools is not empty then it can safely be assumed that it comes from an opened project.
            # Because of the serialization the self.tools list on project save, the dict keys (members of self.tools
            # are each a dict) are turned into strings so we rebuild the self.tools elements so the keys are
            # again float type; dict's don't like having keys changed when iterated through therefore the need for the
            # following convoluted way of changing the keys from string to float type
            temp_tools = {}
            for tooluid_key in self.tools:
                val = deepcopy(self.tools[tooluid_key])
                new_key = deepcopy(int(tooluid_key))
                temp_tools[new_key] = val

            self.tools.clear()
            self.tools = deepcopy(temp_tools)

        self.ui.tool_offset_entry.hide()
        self.ui.tool_offset_lbl.hide()

        # used to store the state of the mpass_cb if the selected preprocessor for geometry is hpgl
        self.old_pp_state = self.default_data['multidepth']
        self.old_toolchangeg_state = self.default_data['toolchange']

        if not isinstance(self.ui, GeometryObjectUI):
            log.debug("Expected a GeometryObjectUI, got %s" % type(self.ui))
            return

        self.ui.geo_tools_table.setupContextMenu()
        self.ui.geo_tools_table.addContextMenu(
            _("Pick from DB"), self.on_tool_add_from_db_clicked,
            icon=QtGui.QIcon(self.app.resource_location + "/plus16.png"))
        self.ui.geo_tools_table.addContextMenu(
            _("Copy"), self.on_tool_copy,
            icon=QtGui.QIcon(self.app.resource_location + "/copy16.png"))
        self.ui.geo_tools_table.addContextMenu(
            _("Delete"), lambda: self.on_tool_delete(all_tools=None),
            icon=QtGui.QIcon(self.app.resource_location + "/trash16.png"))

        # Show/Hide Advanced Options
        if self.app.defaults["global_app_level"] == 'b':
            self.ui.level.setText('<span style="color:green;"><b>%s</b></span>' % _('Basic'))

            self.ui.geo_tools_table.setColumnHidden(2, True)
            self.ui.geo_tools_table.setColumnHidden(3, True)
            # self.ui.geo_tools_table.setColumnHidden(4, True)
            self.ui.addtool_entry_lbl.hide()
            self.ui.addtool_entry.hide()
            self.ui.search_and_add_btn.hide()
            self.ui.deltool_btn.hide()
            # self.ui.endz_label.hide()
            # self.ui.endz_entry.hide()
            self.ui.fr_rapidlabel.hide()
            self.ui.feedrate_rapid_entry.hide()
            self.ui.extracut_cb.hide()
            self.ui.e_cut_entry.hide()
            self.ui.pdepth_label.hide()
            self.ui.pdepth_entry.hide()
            self.ui.feedrate_probe_label.hide()
            self.ui.feedrate_probe_entry.hide()
        else:
            self.ui.level.setText('<span style="color:red;"><b>%s</b></span>' % _('Advanced'))

        self.builduiSig.connect(self.build_ui)

        self.ui.e_cut_entry.setDisabled(False) if self.app.defaults['geometry_extracut'] else \
            self.ui.e_cut_entry.setDisabled(True)
        self.ui.extracut_cb.toggled.connect(lambda state: self.ui.e_cut_entry.setDisabled(not state))

        self.ui.plot_cb.stateChanged.connect(self.on_plot_cb_click)
        self.ui.multicolored_cb.stateChanged.connect(self.on_multicolored_cb_click)

        # Editor Signal
        self.ui.editor_button.clicked.connect(self.app.object2editor)

        # Properties
        self.ui.properties_button.toggled.connect(self.on_properties)
        self.calculations_finished.connect(self.update_area_chull)

        self.ui.generate_cnc_button.clicked.connect(self.on_generatecnc_button_click)
        self.ui.paint_tool_button.clicked.connect(lambda: self.app.paint_tool.run(toggle=False))
        self.ui.generate_ncc_button.clicked.connect(lambda: self.app.ncclear_tool.run(toggle=False))
        self.ui.pp_geometry_name_cb.activated.connect(self.on_pp_changed)

        self.ui.tipdia_entry.valueChanged.connect(self.update_cutz)
        self.ui.tipangle_entry.valueChanged.connect(self.update_cutz)

        self.ui.addtool_from_db_btn.clicked.connect(self.on_tool_add_from_db_clicked)
        self.ui.apply_param_to_all.clicked.connect(self.on_apply_param_to_all_clicked)
        self.ui.cutz_entry.returnPressed.connect(self.on_cut_z_changed)

        # Exclusion areas signals
        self.ui.exclusion_table.horizontalHeader().sectionClicked.connect(self.exclusion_table_toggle_all)
        self.ui.exclusion_table.lost_focus.connect(self.clear_selection)
        self.ui.exclusion_table.itemClicked.connect(self.draw_sel_shape)
        self.ui.add_area_button.clicked.connect(self.on_add_area_click)
        self.ui.delete_area_button.clicked.connect(self.on_clear_area_click)
        self.ui.delete_sel_area_button.clicked.connect(self.on_delete_sel_areas)
        self.ui.strategy_radio.activated_custom.connect(self.on_strategy)

        self.ui.geo_tools_table.drag_drop_sig.connect(self.rebuild_ui)

        self.launch_job.connect(self.mtool_gen_cncjob)

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

    def rebuild_ui(self):
        # read the table tools uid
        current_uid_list = []
        for row in range(self.ui.geo_tools_table.rowCount()):
            uid = int(self.ui.geo_tools_table.item(row, 5).text())
            current_uid_list.append(uid)

        new_tools = {}
        new_uid = 1

        for current_uid in current_uid_list:
            new_tools[new_uid] = deepcopy(self.tools[current_uid])
            new_uid += 1

        self.tools = new_tools

        # the tools table changed therefore we need to reconnect the signals to the cellWidgets
        self.ui_disconnect()
        self.ui_connect()

    def on_cut_z_changed(self):
        self.old_cutz = self.ui.cutz_entry.get_value()

    def set_tool_offset_visibility(self, current_row):
        if current_row is None:
            return
        try:
            tool_offset = self.ui.geo_tools_table.cellWidget(current_row, 2)
            if tool_offset is not None:
                tool_offset_txt = tool_offset.currentText()
                if tool_offset_txt == 'Custom':
                    self.ui.tool_offset_entry.show()
                    self.ui.tool_offset_lbl.show()
                else:
                    self.ui.tool_offset_entry.hide()
                    self.ui.tool_offset_lbl.hide()
        except Exception as e:
            log.debug("set_tool_offset_visibility() --> " + str(e))
            return

    def on_offset_value_edited(self):
        """
        This will save the offset_value into self.tools storage whenever the offset value is edited
        :return:
        """

        for current_row in self.ui.geo_tools_table.selectedItems():
            # sometime the header get selected and it has row number -1
            # we don't want to do anything with the header :)
            if current_row.row() < 0:
                continue
            tool_uid = int(self.ui.geo_tools_table.item(current_row.row(), 5).text())
            self.set_tool_offset_visibility(current_row.row())

            for tooluid_key, tooluid_value in self.tools.items():
                if int(tooluid_key) == tool_uid:
                    try:
                        tooluid_value['offset_value'] = float(self.ui.tool_offset_entry.get_value())
                    except ValueError:
                        # try to convert comma to decimal point. if it's still not working error message and return
                        try:
                            tooluid_value['offset_value'] = float(
                                self.ui.tool_offset_entry.get_value().replace(',', '.')
                            )
                        except ValueError:
                            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Wrong value format entered, use a number."))
                            return

    def ui_connect(self):
        # on any change to the widgets that matter it will be called self.gui_form_to_storage which will save the
        # changes in geometry UI
        for i in self.param_fields:
            current_widget = self.param_fields[i]

            if isinstance(current_widget, FCCheckBox):
                current_widget.stateChanged.connect(self.gui_form_to_storage)
            elif isinstance(current_widget, FCComboBox):
                current_widget.currentIndexChanged.connect(self.gui_form_to_storage)
            elif isinstance(current_widget, FloatEntry) or isinstance(current_widget, LengthEntry) or \
                    isinstance(current_widget, FCEntry) or isinstance(current_widget, IntEntry) or \
                    isinstance(current_widget, NumericalEvalTupleEntry):
                current_widget.editingFinished.connect(self.gui_form_to_storage)
            elif isinstance(current_widget, FCSpinner) or isinstance(current_widget, FCDoubleSpinner):
                current_widget.returnPressed.connect(self.gui_form_to_storage)

        for row in range(self.ui.geo_tools_table.rowCount()):
            for col in [2, 3, 4]:
                self.ui.geo_tools_table.cellWidget(row, col).currentIndexChanged.connect(
                    self.on_tooltable_cellwidget_change)

        self.ui.search_and_add_btn.clicked.connect(self.on_tool_add)

        self.ui.deltool_btn.clicked.connect(self.on_tool_delete)

        self.ui.geo_tools_table.clicked.connect(self.on_row_selection_change)
        self.ui.geo_tools_table.horizontalHeader().sectionClicked.connect(self.on_toggle_all_rows)

        self.ui.geo_tools_table.itemChanged.connect(self.on_tool_edit)
        self.ui.tool_offset_entry.returnPressed.connect(self.on_offset_value_edited)

        for row in range(self.ui.geo_tools_table.rowCount()):
            self.ui.geo_tools_table.cellWidget(row, 6).clicked.connect(self.on_plot_cb_click_table)

        self.ui.plot_cb.stateChanged.connect(self.on_plot_cb_click)

        # common parameters update
        self.ui.toolchangeg_cb.stateChanged.connect(self.update_common_param_in_storage)
        self.ui.toolchangez_entry.editingFinished.connect(self.update_common_param_in_storage)
        self.ui.endz_entry.editingFinished.connect(self.update_common_param_in_storage)
        self.ui.endxy_entry.editingFinished.connect(self.update_common_param_in_storage)
        self.ui.pp_geometry_name_cb.currentIndexChanged.connect(self.update_common_param_in_storage)
        self.ui.exclusion_cb.stateChanged.connect(self.update_common_param_in_storage)
        self.ui.polish_cb.stateChanged.connect(self.update_common_param_in_storage)

    def ui_disconnect(self):

        # on any change to the widgets that matter it will be called self.gui_form_to_storage which will save the
        # changes in geometry UI
        for i in self.param_fields:
            # current_widget = self.ui.grid3.itemAt(i).widget()
            current_widget = self.param_fields[i]
            if isinstance(current_widget, FCCheckBox):
                try:
                    current_widget.stateChanged.disconnect(self.gui_form_to_storage)
                except (TypeError, AttributeError):
                    pass
            elif isinstance(current_widget, FCComboBox):
                try:
                    current_widget.currentIndexChanged.disconnect(self.gui_form_to_storage)
                except (TypeError, AttributeError):
                    pass
            elif isinstance(current_widget, LengthEntry) or isinstance(current_widget, IntEntry) or \
                    isinstance(current_widget, FCEntry) or isinstance(current_widget, FloatEntry) or \
                    isinstance(current_widget, NumericalEvalTupleEntry):
                try:
                    current_widget.editingFinished.disconnect(self.gui_form_to_storage)
                except (TypeError, AttributeError):
                    pass
            elif isinstance(current_widget, FCSpinner) or isinstance(current_widget, FCDoubleSpinner):
                try:
                    current_widget.returnPressed.disconnect(self.gui_form_to_storage)
                except TypeError:
                    pass

        for row in range(self.ui.geo_tools_table.rowCount()):
            for col in [2, 3, 4]:
                try:
                    self.ui.geo_tools_table.cellWidget(row, col).currentIndexChanged.disconnect()
                except (TypeError, AttributeError):
                    pass

        try:
            self.ui.search_and_add_btn.clicked.disconnect()
        except (TypeError, AttributeError):
            pass

        try:
            self.ui.deltool_btn.clicked.disconnect()
        except (TypeError, AttributeError):
            pass

        try:
            self.ui.geo_tools_table.clicked.disconnect()
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.geo_tools_table.horizontalHeader().sectionClicked.disconnect()
        except (TypeError, AttributeError):
            pass

        try:
            self.ui.geo_tools_table.itemChanged.disconnect()
        except (TypeError, AttributeError):
            pass

        try:
            self.ui.tool_offset_entry.returnPressed.disconnect()
        except (TypeError, AttributeError):
            pass

        for row in range(self.ui.geo_tools_table.rowCount()):
            try:
                self.ui.geo_tools_table.cellWidget(row, 6).clicked.disconnect()
            except (TypeError, AttributeError):
                pass

        try:
            self.ui.plot_cb.stateChanged.disconnect()
        except (TypeError, AttributeError):
            pass

        # common parameters update
        try:
            self.ui.toolchangeg_cb.stateChanged.disconnect(self.update_common_param_in_storage)
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.toolchangez_entry.editingFinished.disconnect(self.update_common_param_in_storage)
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.endz_entry.editingFinished.disconnect(self.update_common_param_in_storage)
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.endxy_entry.editingFinished.disconnect(self.update_common_param_in_storage)
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.pp_geometry_name_cb.currentIndexChanged.disconnect(self.update_common_param_in_storage)
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.exclusion_cb.stateChanged.disconnect(self.update_common_param_in_storage)
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.polish_cb.stateChanged.disconnect(self.update_common_param_in_storage)
        except (TypeError, AttributeError):
            pass

    def on_toggle_all_rows(self):
        """
        will toggle the selection of all rows in Tools table

        :return:
        """
        sel_model = self.ui.geo_tools_table.selectionModel()
        sel_indexes = sel_model.selectedIndexes()

        # it will iterate over all indexes which means all items in all columns too but I'm interested only on rows
        sel_rows = set()
        for idx in sel_indexes:
            sel_rows.add(idx.row())

        if len(sel_rows) == self.ui.geo_tools_table.rowCount():
            self.ui.geo_tools_table.clearSelection()
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("No Tool Selected"))
            )
        else:
            self.ui.geo_tools_table.selectAll()
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("Multiple Tools"))
            )

    def on_row_selection_change(self):
        sel_model = self.ui.geo_tools_table.selectionModel()
        sel_indexes = sel_model.selectedIndexes()

        # it will iterate over all indexes which means all items in all columns too but I'm interested only on rows
        sel_rows = set()
        for idx in sel_indexes:
            sel_rows.add(idx.row())

        # update UI only if only one row is selected otherwise having multiple rows selected will deform information
        # for the rows other that the current one (first selected)
        if len(sel_rows) == 1:
            self.update_ui()

    def update_ui(self, row=None):
        self.ui_disconnect()

        if row is None:
            sel_rows = []
            sel_items = self.ui.geo_tools_table.selectedItems()
            for it in sel_items:
                new_row = it.row()
                if new_row not in sel_rows:
                    sel_rows.append(new_row)
        else:
            sel_rows = row if type(row) == list else [row]

        if not sel_rows:
            # sel_rows = [0]
            self.ui.generate_cnc_button.setDisabled(True)
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("No Tool Selected"))
            )
            self.ui_connect()
            return
        else:
            self.ui.generate_cnc_button.setDisabled(False)

        # update the QLabel that shows for which Tool we have the parameters in the UI form
        if len(sel_rows) == 1:
            current_row = sel_rows[0]

            # populate the form with the data from the tool associated with the row parameter
            try:
                item = self.ui.geo_tools_table.item(current_row, 5)
                if type(item) is not None:
                    tooluid = int(item.text())
                else:
                    self.ui_connect()
                    return
            except Exception as e:
                log.debug("Tool missing. Add a tool in Geo Tool Table. %s" % str(e))
                self.ui_connect()
                return

            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s %d</font></b>" % (_('Parameters for'), _("Tool"), tooluid)
            )
        else:
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("Multiple Tools"))
            )

        for current_row in sel_rows:
            self.set_tool_offset_visibility(current_row)

            # populate the form with the data from the tool associated with the row parameter
            try:
                item = self.ui.geo_tools_table.item(current_row, 5)
                if type(item) is not None:
                    tooluid = int(item.text())
                else:
                    self.ui_connect()
                    return
            except Exception as e:
                log.debug("Tool missing. Add a tool in Geo Tool Table. %s" % str(e))
                self.ui_connect()
                return

            # update the form with the V-Shape fields if V-Shape selected in the geo_tool_table
            # also modify the Cut Z form entry to reflect the calculated Cut Z from values got from V-Shape Fields
            try:
                item = self.ui.geo_tools_table.cellWidget(current_row, 4)
                if item is not None:
                    tool_type_txt = item.currentText()
                    self.ui_update_v_shape(tool_type_txt=tool_type_txt)
                else:
                    self.ui_connect()
                    return
            except Exception as e:
                log.debug("Tool missing in ui_update_v_shape(). Add a tool in Geo Tool Table. %s" % str(e))
                return

            try:
                # set the form with data from the newly selected tool
                for tooluid_key, tooluid_value in list(self.tools.items()):
                    if int(tooluid_key) == tooluid:
                        for key, value in list(tooluid_value.items()):
                            if key == 'data':
                                form_value_storage = tooluid_value['data']
                                self.update_form(form_value_storage)
                            if key == 'offset_value':
                                # update the offset value in the entry even if the entry is hidden
                                self.ui.tool_offset_entry.set_value(tooluid_value['offset_value'])

                            if key == 'tool_type' and value == 'V':
                                self.update_cutz()
            except Exception as e:
                log.debug("GeometryObject.update_ui() -> %s " % str(e))

        self.ui_connect()

    def on_tool_add(self, clicked_state, dia=None, new_geo=None):
        log.debug("GeometryObject.on_add_tool()")

        self.ui_disconnect()

        filename = self.app.tools_database_path()

        tool_dia = dia if dia is not None else self.ui.addtool_entry.get_value()

        # construct a list of all 'tooluid' in the self.iso_tools
        tool_uid_list = [int(tooluid_key) for tooluid_key in self.tools]

        # find maximum from the temp_uid, add 1 and this is the new 'tooluid'
        max_uid = 0 if not tool_uid_list else max(tool_uid_list)
        tooluid = int(max_uid) + 1

        new_tools_dict = deepcopy(self.default_data)
        updated_tooldia = None

        # determine the new tool diameter
        if tool_dia is None or tool_dia == 0:
            self.build_ui()
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Please enter a tool diameter with non-zero value, "
                                                          "in Float format."))
            self.ui_connect()
            return
        truncated_tooldia = self.app.dec_format(tool_dia, self.decimals)

        # load the database tools from the file
        try:
            with open(filename) as f:
                tools = f.read()
        except IOError:
            self.app.log.error("Could not load tools DB file.")
            self.app.inform.emit('[ERROR] %s' % _("Could not load Tools DB file."))
            self.ui_connect()
            self.on_tool_default_add(dia=tool_dia)
            return

        try:
            # store here the tools from Tools Database when searching in Tools Database
            tools_db_dict = json.loads(tools)
        except Exception:
            e = sys.exc_info()[0]
            self.app.log.error(str(e))
            self.app.inform.emit('[ERROR] %s' % _("Failed to parse Tools DB file."))
            self.ui_connect()
            self.on_tool_default_add(dia=tool_dia)
            return

        tool_found = 0

        offset = 'Path'
        offset_val = 0.0
        typ = 'Rough'
        tool_type = 'C1'
        # look in database tools
        for db_tool, db_tool_val in tools_db_dict.items():
            offset = db_tool_val['offset']
            offset_val = db_tool_val['offset_value']
            typ = db_tool_val['type']
            tool_type = db_tool_val['tool_type']

            db_tooldia = db_tool_val['tooldia']
            low_limit = float(db_tool_val['data']['tol_min'])
            high_limit = float(db_tool_val['data']['tol_max'])

            # we need only tool marked for Milling Tool (Geometry Object)
            if db_tool_val['data']['tool_target'] != 1:     # _('Milling')
                continue

            # if we find a tool with the same diameter in the Tools DB just update it's data
            if truncated_tooldia == db_tooldia:
                tool_found += 1
                for d in db_tool_val['data']:
                    if d.find('tools_mill_') == 0:
                        new_tools_dict[d] = db_tool_val['data'][d]
                    elif d.find('tools_') == 0:
                        # don't need data for other App Tools; this tests after 'tools_mill_'
                        continue
                    else:
                        new_tools_dict[d] = db_tool_val['data'][d]
            # search for a tool that has a tolerance that the tool fits in
            elif high_limit >= truncated_tooldia >= low_limit:
                tool_found += 1
                updated_tooldia = db_tooldia
                for d in db_tool_val['data']:
                    if d.find('tools_iso') == 0:
                        new_tools_dict[d] = db_tool_val['data'][d]
                    elif d.find('tools_') == 0:
                        # don't need data for other App Tools; this tests after 'tools_drill_'
                        continue
                    else:
                        new_tools_dict[d] = db_tool_val['data'][d]

        # test we found a suitable tool in Tools Database or if multiple ones
        if tool_found == 0:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Tool not in Tools Database. Adding a default tool."))
            self.on_tool_default_add(dia=tool_dia, new_geo=new_geo)
            self.ui_connect()
            return

        if tool_found > 1:
            self.app.inform.emit(
                '[WARNING_NOTCL] %s' % _("Cancelled.\n"
                                         "Multiple tools for one tool diameter found in Tools Database."))
            self.ui_connect()
            return

        new_tdia = deepcopy(updated_tooldia) if updated_tooldia is not None else deepcopy(truncated_tooldia)
        self.tools.update({
            tooluid: {
                'tooldia': new_tdia,
                'offset': deepcopy(offset),
                'offset_value': deepcopy(offset_val),
                'type': deepcopy(typ),
                'tool_type': deepcopy(tool_type),
                'data': deepcopy(new_tools_dict),
                'solid_geometry': self.solid_geometry
            }
        })
        self.ui_connect()
        self.build_ui()

        # select the tool just added
        for row in range(self.ui.geo_tools_table.rowCount()):
            if int(self.ui.geo_tools_table.item(row, 5).text()) == tooluid:
                self.ui.geo_tools_table.selectRow(row)
                break

        # update the UI form
        self.update_ui()

        # if there is at least one tool left in the Tools Table, enable the parameters GUI
        if self.ui.geo_tools_table.rowCount() != 0:
            self.ui.geo_param_frame.setDisabled(False)

        self.app.inform.emit('[success] %s' % _("New tool added to Tool Table from Tools Database."))

    def on_tool_default_add(self, dia=None, new_geo=None, muted=None):
        self.ui_disconnect()

        tooldia = dia if dia is not None else self.ui.addtool_entry.get_value()
        tool_uid_list = [int(tooluid_key) for tooluid_key in self.tools]

        # find maximum from the temp_uid, add 1 and this is the new 'tooluid'
        max_uid = max(tool_uid_list) if tool_uid_list else 0
        self.tooluid = int(max_uid) + 1

        tooldia = self.app.dec_format(tooldia, self.decimals)

        # here we actually add the new tool; if there is no tool in the tool table we add a tool with default data
        # otherwise we add a tool with data copied from last tool
        if self.tools:
            last_data = self.tools[max_uid]['data']
            last_offset = self.tools[max_uid]['offset']
            last_offset_value = self.tools[max_uid]['offset_value']
            last_type = self.tools[max_uid]['type']
            last_tool_type = self.tools[max_uid]['tool_type']

            last_solid_geometry = self.tools[max_uid]['solid_geometry'] if new_geo is None else new_geo

            # if previous geometry was empty (it may happen for the first tool added)
            # then copy the object.solid_geometry
            if not last_solid_geometry:
                last_solid_geometry = self.solid_geometry

            self.tools.update({
                self.tooluid: {
                    'tooldia': tooldia,
                    'offset': last_offset,
                    'offset_value': last_offset_value,
                    'type': last_type,
                    'tool_type': last_tool_type,
                    'data': deepcopy(last_data),
                    'solid_geometry': deepcopy(last_solid_geometry)
                }
            })
        else:
            self.tools.update({
                self.tooluid: {
                    'tooldia': tooldia,
                    'offset': 'Path',
                    'offset_value': 0.0,
                    'type': 'Rough',
                    'tool_type': 'C1',
                    'data': deepcopy(self.default_data),
                    'solid_geometry': self.solid_geometry
                }
            })

        self.tools[self.tooluid]['data']['name'] = self.options['name']

        self.ui.tool_offset_entry.hide()
        self.ui.tool_offset_lbl.hide()

        # we do this HACK to make sure the tools attribute to be serialized is updated in the self.ser_attrs list
        try:
            self.ser_attrs.remove('tools')
        except TypeError:
            pass
        self.ser_attrs.append('tools')

        if muted is None:
            self.app.inform.emit('[success] %s' % _("Tool added in Tool Table."))
        self.ui_connect()
        self.build_ui()

        # if there is at least one tool left in the Tools Table, enable the parameters GUI
        if self.ui.geo_tools_table.rowCount() != 0:
            self.ui.geo_param_frame.setDisabled(False)

    def on_tool_add_from_db_clicked(self):
        """
        Called when the user wants to add a new tool from Tools Database. It will create the Tools Database object
        and display the Tools Database tab in the form needed for the Tool adding
        :return: None
        """

        # if the Tools Database is already opened focus on it
        for idx in range(self.app.ui.plot_tab_area.count()):
            if self.app.ui.plot_tab_area.tabText(idx) == _("Tools Database"):
                self.app.ui.plot_tab_area.setCurrentWidget(self.app.tools_db_tab)
                break
        ret_val = self.app.on_tools_database()
        if ret_val == 'fail':
            return
        self.app.tools_db_tab.ok_to_add = True
        self.app.tools_db_tab.ui.buttons_frame.hide()
        self.app.tools_db_tab.ui.add_tool_from_db.show()
        self.app.tools_db_tab.ui.cancel_tool_from_db.show()

    def on_tool_from_db_inserted(self, tool):
        """
        Called from the Tools DB object through a App method when adding a tool from Tools Database
        :param tool: a dict with the tool data
        :return: None
        """

        self.ui_disconnect()
        self.units = self.app.defaults['units'].upper()

        tooldia = float(tool['tooldia'])

        # construct a list of all 'tooluid' in the self.tools
        tool_uid_list = []
        for tooluid_key in self.tools:
            tool_uid_item = int(tooluid_key)
            tool_uid_list.append(tool_uid_item)

        # find maximum from the temp_uid, add 1 and this is the new 'tooluid'
        if not tool_uid_list:
            max_uid = 0
        else:
            max_uid = max(tool_uid_list)
        self.tooluid = max_uid + 1

        tooldia = float('%.*f' % (self.decimals, tooldia))

        self.tools.update({
            self.tooluid: {
                'tooldia': tooldia,
                'offset': tool['offset'],
                'offset_value': float(tool['offset_value']),
                'type': tool['type'],
                'tool_type': tool['tool_type'],
                'data': deepcopy(tool['data']),
                'solid_geometry': self.solid_geometry
            }
        })

        self.tools[self.tooluid]['data']['name'] = self.options['name']

        self.ui.tool_offset_entry.hide()
        self.ui.tool_offset_lbl.hide()

        # we do this HACK to make sure the tools attribute to be serialized is updated in the self.ser_attrs list
        try:
            self.ser_attrs.remove('tools')
        except TypeError:
            pass
        self.ser_attrs.append('tools')

        self.ui_connect()
        self.build_ui()

        # if there is no tool left in the Tools Table, enable the parameters appGUI
        if self.ui.geo_tools_table.rowCount() != 0:
            self.ui.geo_param_frame.setDisabled(False)

    def on_tool_copy(self, all_tools=None):
        self.ui_disconnect()

        # find the tool_uid maximum value in the self.tools
        uid_list = []
        for key in self.tools:
            uid_list.append(int(key))
        try:
            max_uid = max(uid_list, key=int)
        except ValueError:
            max_uid = 0

        if all_tools is None:
            if self.ui.geo_tools_table.selectedItems():
                for current_row in self.ui.geo_tools_table.selectedItems():
                    # sometime the header get selected and it has row number -1
                    # we don't want to do anything with the header :)
                    if current_row.row() < 0:
                        continue
                    try:
                        tooluid_copy = int(self.ui.geo_tools_table.item(current_row.row(), 5).text())
                        self.set_tool_offset_visibility(current_row.row())
                        max_uid += 1
                        self.tools[int(max_uid)] = deepcopy(self.tools[tooluid_copy])
                    except AttributeError:
                        self.app.inform.emit('[WARNING_NOTCL] %s' % _("Failed. Select a tool to copy."))
                        self.ui_connect()
                        self.builduiSig.emit()
                        return
                    except Exception as e:
                        log.debug("on_tool_copy() --> " + str(e))
                # deselect the table
                # self.ui.geo_tools_table.clearSelection()
            else:
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("Failed. Select a tool to copy."))
                self.ui_connect()
                self.builduiSig.emit()
                return
        else:
            # we copy all tools in geo_tools_table
            try:
                temp_tools = deepcopy(self.tools)
                max_uid += 1
                for tooluid in temp_tools:
                    self.tools[int(max_uid)] = deepcopy(temp_tools[tooluid])
                temp_tools.clear()
            except Exception as e:
                log.debug("on_tool_copy() --> " + str(e))

        # if there are no more tools in geo tools table then hide the tool offset
        if not self.tools:
            self.ui.tool_offset_entry.hide()
            self.ui.tool_offset_lbl.hide()

        # we do this HACK to make sure the tools attribute to be serialized is updated in the self.ser_attrs list
        try:
            self.ser_attrs.remove('tools')
        except ValueError:
            pass
        self.ser_attrs.append('tools')

        self.ui_connect()
        self.builduiSig.emit()
        self.app.inform.emit('[success] %s' % _("Tool was copied in Tool Table."))

    def on_tool_edit(self, current_item):
        self.ui_disconnect()

        current_row = current_item.row()
        try:
            d = float(self.ui.geo_tools_table.item(current_row, 1).text())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                d = float(self.ui.geo_tools_table.item(current_row, 1).text().replace(',', '.'))
            except ValueError:
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("Wrong value format entered, use a number."))
                return
        except AttributeError:
            self.ui_connect()
            return

        tool_dia = float('%.*f' % (self.decimals, d))
        tooluid = int(self.ui.geo_tools_table.item(current_row, 5).text())

        self.tools[tooluid]['tooldia'] = tool_dia

        try:
            self.ser_attrs.remove('tools')
            self.ser_attrs.append('tools')
        except (TypeError, ValueError):
            pass

        self.app.inform.emit('[success] %s' % _("Tool was edited in Tool Table."))
        self.ui_connect()
        self.builduiSig.emit()

    def on_tool_delete(self, clicked_signal, all_tools=None):
        """
        It's important to keep the not clicked_signal parameter otherwise the signal will go to the all_tools
        parameter and I might get all the tool deleted
        """
        self.ui_disconnect()

        if all_tools is None:
            if self.ui.geo_tools_table.selectedItems():
                for current_row in self.ui.geo_tools_table.selectedItems():
                    # sometime the header get selected and it has row number -1
                    # we don't want to do anything with the header :)
                    if current_row.row() < 0:
                        continue
                    try:
                        tooluid_del = int(self.ui.geo_tools_table.item(current_row.row(), 5).text())
                        self.set_tool_offset_visibility(current_row.row())

                        temp_tools = deepcopy(self.tools)
                        for tooluid_key in self.tools:
                            if int(tooluid_key) == tooluid_del:
                                # if the self.tools has only one tool and we delete it then we move the solid_geometry
                                # as a property of the object otherwise there will be nothing to hold it
                                if len(self.tools) == 1:
                                    self.solid_geometry = deepcopy(self.tools[tooluid_key]['solid_geometry'])
                                temp_tools.pop(tooluid_del, None)
                        self.tools = deepcopy(temp_tools)
                        temp_tools.clear()
                    except AttributeError:
                        self.app.inform.emit('[WARNING_NOTCL] %s' % _("Failed. Select a tool to delete."))
                        self.ui_connect()
                        self.builduiSig.emit()
                        return
                    except Exception as e:
                        log.debug("on_tool_delete() --> " + str(e))
                # deselect the table
                # self.ui.geo_tools_table.clearSelection()
            else:
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("Failed. Select a tool to delete."))
                self.ui_connect()
                self.builduiSig.emit()
                return
        else:
            # we delete all tools in geo_tools_table
            self.tools.clear()

        self.app.plot_all()

        # if there are no more tools in geo tools table then hide the tool offset
        if not self.tools:
            self.ui.tool_offset_entry.hide()
            self.ui.tool_offset_lbl.hide()

        # we do this HACK to make sure the tools attribute to be serialized is updated in the self.ser_attrs list
        try:
            self.ser_attrs.remove('tools')
        except TypeError:
            pass
        self.ser_attrs.append('tools')

        self.ui_connect()
        self.build_ui()
        self.app.inform.emit('[success] %s' % _("Tool was deleted in Tool Table."))

        obj_active = self.app.collection.get_active()
        # if the object was MultiGeo and now it has no tool at all (therefore no geometry)
        # we make it back SingleGeo
        if self.ui.geo_tools_table.rowCount() <= 0:
            obj_active.multigeo = False
            obj_active.options['xmin'] = 0
            obj_active.options['ymin'] = 0
            obj_active.options['xmax'] = 0
            obj_active.options['ymax'] = 0

        if obj_active.multigeo is True:
            try:
                xmin, ymin, xmax, ymax = obj_active.bounds()
                obj_active.options['xmin'] = xmin
                obj_active.options['ymin'] = ymin
                obj_active.options['xmax'] = xmax
                obj_active.options['ymax'] = ymax
            except Exception:
                obj_active.options['xmin'] = 0
                obj_active.options['ymin'] = 0
                obj_active.options['xmax'] = 0
                obj_active.options['ymax'] = 0

        # if there is no tool left in the Tools Table, disable the parameters appGUI
        if self.ui.geo_tools_table.rowCount() == 0:
            self.ui.geo_param_frame.setDisabled(True)

    def ui_update_v_shape(self, tool_type_txt):
        if tool_type_txt == 'V':
            self.ui.tipdialabel.show()
            self.ui.tipdia_entry.show()
            self.ui.tipanglelabel.show()
            self.ui.tipangle_entry.show()
            self.ui.cutz_entry.setDisabled(True)
            self.ui.cutzlabel.setToolTip(
                _("Disabled because the tool is V-shape.\n"
                  "For V-shape tools the depth of cut is\n"
                  "calculated from other parameters like:\n"
                  "- 'V-tip Angle' -> angle at the tip of the tool\n"
                  "- 'V-tip Dia' -> diameter at the tip of the tool \n"
                  "- Tool Dia -> 'Dia' column found in the Tool Table\n"
                  "NB: a value of zero means that Tool Dia = 'V-tip Dia'")
            )
            self.ui.cutz_entry.setToolTip(
                _("Disabled because the tool is V-shape.\n"
                  "For V-shape tools the depth of cut is\n"
                  "calculated from other parameters like:\n"
                  "- 'V-tip Angle' -> angle at the tip of the tool\n"
                  "- 'V-tip Dia' -> diameter at the tip of the tool \n"
                  "- Tool Dia -> 'Dia' column found in the Tool Table\n"
                  "NB: a value of zero means that Tool Dia = 'V-tip Dia'")
            )

            self.update_cutz()
        else:
            self.ui.tipdialabel.hide()
            self.ui.tipdia_entry.hide()
            self.ui.tipanglelabel.hide()
            self.ui.tipangle_entry.hide()
            self.ui.cutz_entry.setDisabled(False)
            self.ui.cutzlabel.setToolTip(
                _("Cutting depth (negative)\n"
                  "below the copper surface.")
            )
            self.ui.cutz_entry.setToolTip('')

    def update_cutz(self):
        vdia = float(self.ui.tipdia_entry.get_value())
        half_vangle = float(self.ui.tipangle_entry.get_value()) / 2

        row = self.ui.geo_tools_table.currentRow()
        tool_uid_item = self.ui.geo_tools_table.item(row, 5)
        if tool_uid_item is None:
            return
        tool_uid = int(tool_uid_item.text())

        tool_dia_item = self.ui.geo_tools_table.item(row, 1)
        if tool_dia_item is None:
            return
        tooldia = float(tool_dia_item.text())

        try:
            new_cutz = (tooldia - vdia) / (2 * math.tan(math.radians(half_vangle)))
        except ZeroDivisionError:
            new_cutz = self.old_cutz

        new_cutz = float('%.*f' % (self.decimals, new_cutz)) * -1.0   # this value has to be negative

        self.ui.cutz_entry.set_value(new_cutz)

        # store the new CutZ value into storage (self.tools)
        for tooluid_key, tooluid_value in self.tools.items():
            if int(tooluid_key) == tool_uid:
                tooluid_value['data']['cutz'] = new_cutz

    def on_tooltable_cellwidget_change(self):
        cw = self.sender()
        # assert isinstance(cw, FCComboBox) or isinstance(cw, FCCheckBox),\
        #     "Expected a FCCombobox or a FCCheckbox got %s" % type(cw)
        cw_index = self.ui.geo_tools_table.indexAt(cw.pos())
        cw_row = cw_index.row()
        cw_col = cw_index.column()
        current_uid = int(self.ui.geo_tools_table.item(cw_row, 5).text())

        # store the text of the cellWidget that changed it's index in the self.tools
        for tooluid_key, tooluid_value in self.tools.items():
            if int(tooluid_key) == current_uid:
                cb_txt = cw.currentText()
                if cw_col == 2:
                    tooluid_value['offset'] = cb_txt
                    if cb_txt == 'Custom':
                        self.ui.tool_offset_entry.show()
                        self.ui.tool_offset_lbl.show()
                    else:
                        self.ui.tool_offset_entry.hide()
                        self.ui.tool_offset_lbl.hide()
                        # reset the offset_value in storage self.tools
                        tooluid_value['offset_value'] = 0.0
                elif cw_col == 3:
                    # force toolpath type as 'Iso' if the tool type is V-Shape
                    if self.ui.geo_tools_table.cellWidget(cw_row, 4).currentText() == 'V':
                        tooluid_value['type'] = 'Iso'
                        idx = self.ui.geo_tools_table.cellWidget(cw_row, 3).findText('Iso')
                        self.ui.geo_tools_table.cellWidget(cw_row, 3).setCurrentIndex(idx)
                    else:
                        tooluid_value['type'] = cb_txt
                elif cw_col == 4:
                    tooluid_value['tool_type'] = cb_txt

                    # if the tool_type selected is V-Shape then autoselect the toolpath type as Iso
                    if cb_txt == 'V':
                        idx = self.ui.geo_tools_table.cellWidget(cw_row, 3).findText('Iso')
                        self.ui.geo_tools_table.cellWidget(cw_row, 3).setCurrentIndex(idx)
                    else:
                        self.ui.cutz_entry.set_value(self.old_cutz)

                self.ui_update_v_shape(tool_type_txt=self.ui.geo_tools_table.cellWidget(cw_row, 4).currentText())

    def update_form(self, dict_storage):
        for form_key in self.form_fields:
            for storage_key in dict_storage:
                if form_key == storage_key:
                    try:
                        self.form_fields[form_key].set_value(dict_storage[form_key])
                    except Exception as e:
                        log.debug(str(e))

        # this is done here because those buttons control through OptionalInputSelection if some entry's are Enabled
        # or not. But due of using the ui_disconnect() status is no longer updated and I had to do it here
        self.ui.ois_dwell_geo.on_cb_change()
        self.ui.ois_mpass_geo.on_cb_change()
        self.ui.ois_tcz_geo.on_cb_change()

    def on_apply_param_to_all_clicked(self):
        if self.ui.geo_tools_table.rowCount() == 0:
            # there is no tool in tool table so we can't save the GUI elements values to storage
            log.debug("GeometryObject.gui_form_to_storage() --> no tool in Tools Table, aborting.")
            return

        self.ui_disconnect()

        row = self.ui.geo_tools_table.currentRow()
        if row < 0:
            row = 0

        # store all the data associated with the row parameter to the self.tools storage
        tooldia_item = float(self.ui.geo_tools_table.item(row, 1).text())
        offset_item = self.ui.geo_tools_table.cellWidget(row, 2).currentText()
        type_item = self.ui.geo_tools_table.cellWidget(row, 3).currentText()
        tool_type_item = self.ui.geo_tools_table.cellWidget(row, 4).currentText()

        offset_value_item = float(self.ui.tool_offset_entry.get_value())

        # this new dict will hold the actual useful data, another dict that is the value of key 'data'
        temp_tools = {}
        temp_dia = {}
        temp_data = {}

        for tooluid_key, tooluid_value in self.tools.items():
            for key, value in tooluid_value.items():
                if key == 'tooldia':
                    temp_dia[key] = tooldia_item
                # update the 'offset', 'type' and 'tool_type' sections
                if key == 'offset':
                    temp_dia[key] = offset_item
                if key == 'type':
                    temp_dia[key] = type_item
                if key == 'tool_type':
                    temp_dia[key] = tool_type_item
                if key == 'offset_value':
                    temp_dia[key] = offset_value_item

                if key == 'data':
                    # update the 'data' section
                    for data_key in tooluid_value[key].keys():
                        for form_key, form_value in self.form_fields.items():
                            if form_key == data_key:
                                temp_data[data_key] = form_value.get_value()
                        # make sure we make a copy of the keys not in the form (we may use 'data' keys that are
                        # updated from self.app.defaults
                        if data_key not in self.form_fields:
                            temp_data[data_key] = value[data_key]
                    temp_dia[key] = deepcopy(temp_data)
                    temp_data.clear()

                if key == 'solid_geometry':
                    temp_dia[key] = deepcopy(self.tools[tooluid_key]['solid_geometry'])

                temp_tools[tooluid_key] = deepcopy(temp_dia)

        self.tools.clear()
        self.tools = deepcopy(temp_tools)
        temp_tools.clear()

        self.ui_connect()

    def gui_form_to_storage(self):
        self.ui_disconnect()

        if self.ui.geo_tools_table.rowCount() == 0:
            # there is no tool in tool table so we can't save the GUI elements values to storage
            log.debug("GeometryObject.gui_form_to_storage() --> no tool in Tools Table, aborting.")
            return

        widget_changed = self.sender()
        try:
            widget_idx = self.ui.grid3.indexOf(widget_changed)
            # those are the indexes for the V-Tip Dia and V-Tip Angle, if edited calculate the new Cut Z
            if widget_idx == 1 or widget_idx == 3:
                self.update_cutz()
        except Exception as e:
            log.debug("GeometryObject.gui_form_to_storage() -- wdg index -> %s" % str(e))

        # the original connect() function of the OptionalInputSelection is no longer working because of the
        # ui_diconnect() so I use this 'hack'
        if isinstance(widget_changed, FCCheckBox):
            if widget_changed.text() == 'Multi-Depth:':
                self.ui.ois_mpass_geo.on_cb_change()

            if widget_changed.text() == 'Tool change':
                self.ui.ois_tcz_geo.on_cb_change()

            if widget_changed.text() == 'Dwell:':
                self.ui.ois_dwell_geo.on_cb_change()

        row = self.ui.geo_tools_table.currentRow()
        if row < 0:
            row = 0

        # store all the data associated with the row parameter to the self.tools storage
        tooldia_item = float(self.ui.geo_tools_table.item(row, 1).text())
        offset_item = self.ui.geo_tools_table.cellWidget(row, 2).currentText()
        type_item = self.ui.geo_tools_table.cellWidget(row, 3).currentText()
        tool_type_item = self.ui.geo_tools_table.cellWidget(row, 4).currentText()
        tooluid_item = int(self.ui.geo_tools_table.item(row, 5).text())

        offset_value_item = float(self.ui.tool_offset_entry.get_value())

        # this new dict will hold the actual useful data, another dict that is the value of key 'data'
        temp_tools = {}
        temp_dia = {}
        temp_data = {}

        for tooluid_key, tooluid_value in self.tools.items():
            if int(tooluid_key) == tooluid_item:
                for key, value in tooluid_value.items():
                    if key == 'tooldia':
                        temp_dia[key] = tooldia_item
                    # update the 'offset', 'type' and 'tool_type' sections
                    if key == 'offset':
                        temp_dia[key] = offset_item
                    if key == 'type':
                        temp_dia[key] = type_item
                    if key == 'tool_type':
                        temp_dia[key] = tool_type_item
                    if key == 'offset_value':
                        temp_dia[key] = offset_value_item

                    if key == 'data':
                        # update the 'data' section
                        for data_key in tooluid_value[key].keys():
                            for form_key, form_value in self.form_fields.items():
                                if form_key == data_key:
                                    temp_data[data_key] = form_value.get_value()
                            # make sure we make a copy of the keys not in the form (we may use 'data' keys that are
                            # updated from self.app.defaults
                            if data_key not in self.form_fields:
                                temp_data[data_key] = value[data_key]
                        temp_dia[key] = deepcopy(temp_data)
                        temp_data.clear()

                    if key == 'solid_geometry':
                        temp_dia[key] = deepcopy(self.tools[tooluid_key]['solid_geometry'])

                    temp_tools[tooluid_key] = deepcopy(temp_dia)
            else:
                temp_tools[tooluid_key] = deepcopy(tooluid_value)

        self.tools.clear()
        self.tools = deepcopy(temp_tools)
        temp_tools.clear()
        self.ui_connect()

    def update_common_param_in_storage(self):
        for tooluid_value in self.tools.values():
            tooluid_value['data']['toolchange'] = self.ui.toolchangeg_cb.get_value()
            tooluid_value['data']['toolchangez'] = self.ui.toolchangez_entry.get_value()
            tooluid_value['data']['endz'] = self.ui.endz_entry.get_value()
            tooluid_value['data']['endxy'] = self.ui.endxy_entry.get_value()
            tooluid_value['data']['ppname_g'] = self.ui.pp_geometry_name_cb.get_value()
            tooluid_value['data']['area_exclusion'] = self.ui.exclusion_cb.get_value()
            tooluid_value['data']['polish'] = self.ui.polish_cb.get_value()

    def select_tools_table_row(self, row, clearsel=None):
        if clearsel:
            self.ui.geo_tools_table.clearSelection()

        if self.ui.geo_tools_table.rowCount() > 0:
            # self.ui.geo_tools_table.item(row, 0).setSelected(True)
            self.ui.geo_tools_table.setCurrentItem(self.ui.geo_tools_table.item(row, 0))

    def export_dxf(self):
        dwg = None
        try:
            dwg = ezdxf.new('R2010')
            msp = dwg.modelspace()

            def g2dxf(dxf_space, geo_obj):
                if isinstance(geo_obj, MultiPolygon):
                    for poly in geo_obj:
                        ext_points = list(poly.exterior.coords)
                        dxf_space.add_lwpolyline(ext_points)
                        for interior in poly.interiors:
                            dxf_space.add_lwpolyline(list(interior.coords))
                if isinstance(geo_obj, Polygon):
                    ext_points = list(geo_obj.exterior.coords)
                    dxf_space.add_lwpolyline(ext_points)
                    for interior in geo_obj.interiors:
                        dxf_space.add_lwpolyline(list(interior.coords))
                if isinstance(geo_obj, MultiLineString):
                    for line in geo_obj:
                        dxf_space.add_lwpolyline(list(line.coords))
                if isinstance(geo_obj, LineString) or isinstance(geo_obj, LinearRing):
                    dxf_space.add_lwpolyline(list(geo_obj.coords))

            multigeo_solid_geometry = []
            if self.multigeo:
                for tool in self.tools:
                    multigeo_solid_geometry += self.tools[tool]['solid_geometry']
            else:
                multigeo_solid_geometry = self.solid_geometry

            for geo in multigeo_solid_geometry:
                if type(geo) == list:
                    for g in geo:
                        g2dxf(msp, g)
                else:
                    g2dxf(msp, geo)

                # points = GeometryObject.get_pts(geo)
                # msp.add_lwpolyline(points)
        except Exception as e:
            log.debug(str(e))

        return dwg

    def get_selected_tools_table_items(self):
        """
        Returns a list of lists, each list in the list is made out of row elements

        :return: List of table_tools items.
        :rtype: list
        """
        table_tools_items = []
        if self.multigeo:
            for x in self.ui.geo_tools_table.selectedItems():
                elem = []
                txt = ''

                for column in range(0, self.ui.geo_tools_table.columnCount()):
                    try:
                        txt = self.ui.geo_tools_table.item(x.row(), column).text()
                    except AttributeError:
                        try:
                            txt = self.ui.geo_tools_table.cellWidget(x.row(), column).currentText()
                        except AttributeError:
                            pass
                    elem.append(txt)
                table_tools_items.append(deepcopy(elem))
                # table_tools_items.append([self.ui.geo_tools_table.item(x.row(), column).text()
                #                           for column in range(0, self.ui.geo_tools_table.columnCount())])
        else:
            for x in self.ui.geo_tools_table.selectedItems():
                r = []
                txt = ''

                # the last 2 columns for single-geo geometry are irrelevant and create problems reading
                # so we don't read them
                for column in range(0, self.ui.geo_tools_table.columnCount() - 2):
                    # the columns have items that have text but also have items that are widgets
                    # for which the text they hold has to be read differently
                    try:
                        txt = self.ui.geo_tools_table.item(x.row(), column).text()
                    except AttributeError:
                        try:
                            txt = self.ui.geo_tools_table.cellWidget(x.row(), column).currentText()
                        except AttributeError:
                            pass
                    r.append(txt)
                table_tools_items.append(r)

        for item in table_tools_items:
            item[0] = str(item[0])
        return table_tools_items

    def on_pp_changed(self):
        current_pp = self.ui.pp_geometry_name_cb.get_value()
        if current_pp == 'hpgl':
            self.old_pp_state = self.ui.mpass_cb.get_value()
            self.old_toolchangeg_state = self.ui.toolchangeg_cb.get_value()

            self.ui.mpass_cb.set_value(False)
            self.ui.mpass_cb.setDisabled(True)

            self.ui.toolchangeg_cb.set_value(True)
            self.ui.toolchangeg_cb.setDisabled(True)
        else:
            self.ui.mpass_cb.set_value(self.old_pp_state)
            self.ui.mpass_cb.setDisabled(False)

            self.ui.toolchangeg_cb.set_value(self.old_toolchangeg_state)
            self.ui.toolchangeg_cb.setDisabled(False)

        if "toolchange_probe" in current_pp.lower():
            self.ui.pdepth_entry.setVisible(True)
            self.ui.pdepth_label.show()

            self.ui.feedrate_probe_entry.setVisible(True)
            self.ui.feedrate_probe_label.show()
        else:
            self.ui.pdepth_entry.setVisible(False)
            self.ui.pdepth_label.hide()

            self.ui.feedrate_probe_entry.setVisible(False)
            self.ui.feedrate_probe_label.hide()

        if 'marlin' in current_pp.lower() or 'custom' in current_pp.lower():
            self.ui.fr_rapidlabel.show()
            self.ui.feedrate_rapid_entry.show()
        else:
            self.ui.fr_rapidlabel.hide()
            self.ui.feedrate_rapid_entry.hide()

        if 'laser' in current_pp.lower():
            self.ui.cutzlabel.hide()
            self.ui.cutz_entry.hide()
            try:
                self.ui.mpass_cb.hide()
                self.ui.maxdepth_entry.hide()
            except AttributeError:
                pass

            if 'marlin' in current_pp.lower():
                self.ui.travelzlabel.setText('%s:' % _("Focus Z"))
                self.ui.endz_label.show()
                self.ui.endz_entry.show()
            else:
                self.ui.travelzlabel.hide()
                self.ui.travelz_entry.hide()

                self.ui.endz_label.hide()
                self.ui.endz_entry.hide()

            try:
                self.ui.frzlabel.hide()
                self.ui.feedrate_z_entry.hide()
            except AttributeError:
                pass

            self.ui.dwell_cb.hide()
            self.ui.dwelltime_entry.hide()

            self.ui.spindle_label.setText('%s:' % _("Laser Power"))

            try:
                self.ui.tool_offset_label.hide()
                self.ui.offset_entry.hide()
            except AttributeError:
                pass
        else:
            self.ui.cutzlabel.show()
            self.ui.cutz_entry.show()
            try:
                self.ui.mpass_cb.show()
                self.ui.maxdepth_entry.show()
            except AttributeError:
                pass

            self.ui.travelzlabel.setText('%s:' % _('Travel Z'))

            self.ui.travelzlabel.show()
            self.ui.travelz_entry.show()

            self.ui.endz_label.show()
            self.ui.endz_entry.show()

            try:
                self.ui.frzlabel.show()
                self.ui.feedrate_z_entry.show()
            except AttributeError:
                pass
            self.ui.dwell_cb.show()
            self.ui.dwelltime_entry.show()

            self.ui.spindle_label.setText('%s:' % _('Spindle speed'))

            try:
                self.ui.tool_offset_lbl.show()
                self.ui.offset_entry.show()
            except AttributeError:
                pass

    def on_generatecnc_button_click(self):
        log.debug("Generating CNCJob from Geometry ...")
        self.app.defaults.report_usage("geometry_on_generatecnc_button")

        # this reads the values in the UI form to the self.options dictionary
        self.read_form()

        self.sel_tools = {}

        try:
            if self.special_group:
                self.app.inform.emit(
                    '[WARNING_NOTCL] %s %s %s.' %
                    (_("This Geometry can't be processed because it is"), str(self.special_group), _("Geometry"))
                )
                return
        except AttributeError:
            pass

        # test to see if we have tools available in the tool table
        if self.ui.geo_tools_table.selectedItems():
            for x in self.ui.geo_tools_table.selectedItems():
                tooluid = int(self.ui.geo_tools_table.item(x.row(), 5).text())

                for tooluid_key, tooluid_value in self.tools.items():
                    if int(tooluid_key) == tooluid:
                        self.sel_tools.update({
                            tooluid: deepcopy(tooluid_value)
                        })

            if self.ui.polish_cb.get_value():
                self.on_polish()
            else:
                self.mtool_gen_cncjob()
            self.ui.geo_tools_table.clearSelection()

        elif self.ui.geo_tools_table.rowCount() == 1:
            tooluid = int(self.ui.geo_tools_table.item(0, 5).text())

            for tooluid_key, tooluid_value in self.tools.items():
                if int(tooluid_key) == tooluid:
                    self.sel_tools.update({
                        tooluid: deepcopy(tooluid_value)
                    })
            if self.ui.polish_cb.get_value():
                self.on_polish()
            else:
                self.mtool_gen_cncjob()
            self.ui.geo_tools_table.clearSelection()
        else:
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed. No tool selected in the tool table ..."))

    def mtool_gen_cncjob(self, outname=None, tools_dict=None, tools_in_use=None, segx=None, segy=None,
                         plot=True, use_thread=True):
        """
        Creates a multi-tool CNCJob out of this Geometry object.
        The actual work is done by the target CNCJobObject object's
        `generate_from_geometry_2()` method.

        :param outname:
        :param tools_dict:      a dictionary that holds the whole data needed to create the Gcode
                                (including the solid_geometry)
        :param tools_in_use:    the tools that are used, needed by some preprocessors
        :type  tools_in_use     list of lists, each list in the list is made out of row elements of tools table from GUI
        :param segx:            number of segments on the X axis, for auto-levelling
        :param segy:            number of segments on the Y axis, for auto-levelling
        :param plot:            if True the generated object will be plotted; if False will not be plotted
        :param use_thread:      if True use threading
        :return:                None
        """

        # use the name of the first tool selected in self.geo_tools_table which has the diameter passed as tool_dia
        outname = "%s_%s" % (self.options["name"], 'cnc') if outname is None else outname

        tools_dict = self.sel_tools if tools_dict is None else tools_dict
        tools_in_use = tools_in_use if tools_in_use is not None else self.get_selected_tools_table_items()
        segx = segx if segx is not None else float(self.app.defaults['geometry_segx'])
        segy = segy if segy is not None else float(self.app.defaults['geometry_segy'])

        try:
            xmin = self.options['xmin']
            ymin = self.options['ymin']
            xmax = self.options['xmax']
            ymax = self.options['ymax']
        except Exception as e:
            log.debug("FlatCAMObj.GeometryObject.mtool_gen_cncjob() --> %s\n" % str(e))

            msg = '[ERROR] %s' % _("An internal error has occurred. See shell.\n")
            msg += '%s' % str(e)
            msg += traceback.format_exc()
            self.app.inform.emit(msg)
            return

        self.multigeo = True

        # Object initialization function for app.app_obj.new_object()
        # RUNNING ON SEPARATE THREAD!
        def job_init_single_geometry(job_obj, app_obj):
            log.debug("Creating a CNCJob out of a single-geometry")
            assert job_obj.kind == 'cncjob', "Initializer expected a CNCJobObject, got %s" % type(job_obj)

            job_obj.options['xmin'] = xmin
            job_obj.options['ymin'] = ymin
            job_obj.options['xmax'] = xmax
            job_obj.options['ymax'] = ymax

            # count the tools
            tool_cnt = 0

            # dia_cnc_dict = {}

            # this turn on the FlatCAMCNCJob plot for multiple tools
            job_obj.multitool = True
            job_obj.multigeo = False
            job_obj.cnc_tools.clear()

            job_obj.options['Tools_in_use'] = tools_in_use
            job_obj.segx = segx if segx else float(self.app.defaults["geometry_segx"])
            job_obj.segy = segy if segy else float(self.app.defaults["geometry_segy"])

            job_obj.z_pdepth = float(self.app.defaults["geometry_z_pdepth"])
            job_obj.feedrate_probe = float(self.app.defaults["geometry_feedrate_probe"])

            total_gcode = ''
            for tooluid_key in list(tools_dict.keys()):
                tool_cnt += 1

                dia_cnc_dict = deepcopy(tools_dict[tooluid_key])
                tooldia_val = app_obj.dec_format(float(tools_dict[tooluid_key]['tooldia']), self.decimals)
                dia_cnc_dict.update({
                    'tooldia': tooldia_val
                })

                if dia_cnc_dict['offset'] == 'in':
                    tool_offset = -dia_cnc_dict['tooldia'] / 2
                elif dia_cnc_dict['offset'].lower() == 'out':
                    tool_offset = dia_cnc_dict['tooldia'] / 2
                elif dia_cnc_dict['offset'].lower() == 'custom':
                    try:
                        offset_value = float(self.ui.tool_offset_entry.get_value())
                    except ValueError:
                        # try to convert comma to decimal point. if it's still not working error message and return
                        try:
                            offset_value = float(self.ui.tool_offset_entry.get_value().replace(',', '.'))
                        except ValueError:
                            app_obj.inform.emit('[ERROR_NOTCL] %s' % _("Wrong value format entered, use a number."))
                            return
                    if offset_value:
                        tool_offset = float(offset_value)
                    else:
                        app_obj.inform.emit(
                            '[WARNING] %s' % _("Tool Offset is selected in Tool Table but no value is provided.\n"
                                               "Add a Tool Offset or change the Offset Type.")
                        )
                        return
                else:
                    tool_offset = 0.0

                dia_cnc_dict.update({
                    'offset_value': tool_offset
                })

                z_cut = tools_dict[tooluid_key]['data']["cutz"]
                z_move = tools_dict[tooluid_key]['data']["travelz"]
                feedrate = tools_dict[tooluid_key]['data']["feedrate"]
                feedrate_z = tools_dict[tooluid_key]['data']["feedrate_z"]
                feedrate_rapid = tools_dict[tooluid_key]['data']["feedrate_rapid"]
                multidepth = tools_dict[tooluid_key]['data']["multidepth"]
                extracut = tools_dict[tooluid_key]['data']["extracut"]
                extracut_length = tools_dict[tooluid_key]['data']["extracut_length"]
                depthpercut = tools_dict[tooluid_key]['data']["depthperpass"]
                toolchange = tools_dict[tooluid_key]['data']["toolchange"]
                toolchangez = tools_dict[tooluid_key]['data']["toolchangez"]
                toolchangexy = tools_dict[tooluid_key]['data']["toolchangexy"]
                startz = tools_dict[tooluid_key]['data']["startz"]
                endz = tools_dict[tooluid_key]['data']["endz"]
                endxy = self.options["endxy"]
                spindlespeed = tools_dict[tooluid_key]['data']["spindlespeed"]
                dwell = tools_dict[tooluid_key]['data']["dwell"]
                dwelltime = tools_dict[tooluid_key]['data']["dwelltime"]
                pp_geometry_name = tools_dict[tooluid_key]['data']["ppname_g"]

                spindledir = self.app.defaults['geometry_spindledir']
                tool_solid_geometry = self.solid_geometry

                job_obj.coords_decimals = self.app.defaults["cncjob_coords_decimals"]
                job_obj.fr_decimals = self.app.defaults["cncjob_fr_decimals"]

                # Propagate options
                job_obj.options["tooldia"] = tooldia_val
                job_obj.options['type'] = 'Geometry'
                job_obj.options['tool_dia'] = tooldia_val

                tool_lst = list(tools_dict.keys())
                is_first = True if tooluid_key == tool_lst[0] else False

                # it seems that the tolerance needs to be a lot lower value than 0.01 and it was hardcoded initially
                # to a value of 0.0005 which is 20 times less than 0.01
                tol = float(self.app.defaults['global_tolerance']) / 20
                res, start_gcode = job_obj.generate_from_geometry_2(
                    self, tooldia=tooldia_val, offset=tool_offset, tolerance=tol,
                    z_cut=z_cut, z_move=z_move,
                    feedrate=feedrate, feedrate_z=feedrate_z, feedrate_rapid=feedrate_rapid,
                    spindlespeed=spindlespeed, spindledir=spindledir, dwell=dwell, dwelltime=dwelltime,
                    multidepth=multidepth, depthpercut=depthpercut,
                    extracut=extracut, extracut_length=extracut_length, startz=startz, endz=endz, endxy=endxy,
                    toolchange=toolchange, toolchangez=toolchangez, toolchangexy=toolchangexy,
                    pp_geometry_name=pp_geometry_name,
                    tool_no=tool_cnt, is_first=is_first)

                if res == 'fail':
                    log.debug("GeometryObject.mtool_gen_cncjob() --> generate_from_geometry2() failed")
                    return 'fail'

                dia_cnc_dict['gcode'] = res
                if start_gcode != '':
                    job_obj.gc_start = start_gcode

                total_gcode += res

                # tell gcode_parse from which point to start drawing the lines depending on what kind of
                # object is the source of gcode
                job_obj.toolchange_xy_type = "geometry"

                self.app.inform.emit('[success] %s' % _("G-Code parsing in progress..."))
                dia_cnc_dict['gcode_parsed'] = job_obj.gcode_parse()
                app_obj.inform.emit('[success] %s' % _("G-Code parsing finished..."))

                # commented this; there is no need for the actual GCode geometry - the original one will serve as well
                # for bounding box values
                # dia_cnc_dict['solid_geometry'] = unary_union([geo['geom'] for geo in dia_cnc_dict['gcode_parsed']])
                try:
                    dia_cnc_dict['solid_geometry'] = tool_solid_geometry
                    app_obj.inform.emit('[success] %s...' % _("Finished G-Code processing"))
                except Exception as er:
                    app_obj.inform.emit('[ERROR] %s: %s' % (_("G-Code processing failed with error"), str(er)))

                job_obj.cnc_tools.update({
                    tooluid_key: deepcopy(dia_cnc_dict)
                })
                dia_cnc_dict.clear()

            job_obj.source_file = job_obj.gc_start + total_gcode

        # Object initialization function for app.app_obj.new_object()
        # RUNNING ON SEPARATE THREAD!
        def job_init_multi_geometry(job_obj, app_obj):
            log.debug("Creating a CNCJob out of a multi-geometry")
            assert job_obj.kind == 'cncjob', "Initializer expected a CNCJobObject, got %s" % type(job_obj)

            job_obj.options['xmin'] = xmin
            job_obj.options['ymin'] = ymin
            job_obj.options['xmax'] = xmax
            job_obj.options['ymax'] = ymax

            # count the tools
            tool_cnt = 0

            # dia_cnc_dict = {}

            # this turn on the FlatCAMCNCJob plot for multiple tools
            job_obj.multitool = True
            job_obj.multigeo = True
            job_obj.cnc_tools.clear()

            job_obj.options['Tools_in_use'] = tools_in_use
            job_obj.segx = segx if segx else float(self.app.defaults["geometry_segx"])
            job_obj.segy = segy if segy else float(self.app.defaults["geometry_segy"])

            job_obj.z_pdepth = float(self.app.defaults["geometry_z_pdepth"])
            job_obj.feedrate_probe = float(self.app.defaults["geometry_feedrate_probe"])

            # make sure that trying to make a CNCJob from an empty file is not creating an app crash
            if not self.solid_geometry:
                a = 0
                for tooluid_key in self.tools:
                    if self.tools[tooluid_key]['solid_geometry'] is None:
                        a += 1
                if a == len(self.tools):
                    app_obj.inform.emit('[ERROR_NOTCL] %s...' % _('Cancelled. Empty file, it has no geometry'))
                    return 'fail'

            total_gcode = ''
            for tooluid_key in list(tools_dict.keys()):
                tool_cnt += 1
                dia_cnc_dict = deepcopy(tools_dict[tooluid_key])
                tooldia_val = app_obj.dec_format(float(tools_dict[tooluid_key]['tooldia']), self.decimals)
                dia_cnc_dict.update({
                    'tooldia': tooldia_val
                })

                # find the tool_dia associated with the tooluid_key
                # search in the self.tools for the sel_tool_dia and when found see what tooluid has
                # on the found tooluid in self.tools we also have the solid_geometry that interest us
                # for k, v in self.tools.items():
                #     if float('%.*f' % (self.decimals, float(v['tooldia']))) == tooldia_val:
                #         current_uid = int(k)
                #         break

                if dia_cnc_dict['offset'].lower() == 'in':
                    tool_offset = -tooldia_val / 2
                elif dia_cnc_dict['offset'].lower() == 'out':
                    tool_offset = tooldia_val / 2
                elif dia_cnc_dict['offset'].lower() == 'custom':
                    offset_value = float(self.ui.tool_offset_entry.get_value())
                    if offset_value:
                        tool_offset = float(offset_value)
                    else:
                        self.app.inform.emit('[WARNING] %s' %
                                             _("Tool Offset is selected in Tool Table but "
                                               "no value is provided.\n"
                                               "Add a Tool Offset or change the Offset Type."))
                        return
                else:
                    tool_offset = 0.0

                dia_cnc_dict.update({
                    'offset_value': tool_offset
                })

                # z_cut = tools_dict[tooluid_key]['data']["cutz"]
                # z_move = tools_dict[tooluid_key]['data']["travelz"]
                # feedrate = tools_dict[tooluid_key]['data']["feedrate"]
                # feedrate_z = tools_dict[tooluid_key]['data']["feedrate_z"]
                # feedrate_rapid = tools_dict[tooluid_key]['data']["feedrate_rapid"]
                # multidepth = tools_dict[tooluid_key]['data']["multidepth"]
                # extracut = tools_dict[tooluid_key]['data']["extracut"]
                # extracut_length = tools_dict[tooluid_key]['data']["extracut_length"]
                # depthpercut = tools_dict[tooluid_key]['data']["depthperpass"]
                # toolchange = tools_dict[tooluid_key]['data']["toolchange"]
                # toolchangez = tools_dict[tooluid_key]['data']["toolchangez"]
                # toolchangexy = tools_dict[tooluid_key]['data']["toolchangexy"]
                # startz = tools_dict[tooluid_key]['data']["startz"]
                # endz = tools_dict[tooluid_key]['data']["endz"]
                # endxy = self.options["endxy"]
                # spindlespeed = tools_dict[tooluid_key]['data']["spindlespeed"]
                # dwell = tools_dict[tooluid_key]['data']["dwell"]
                # dwelltime = tools_dict[tooluid_key]['data']["dwelltime"]
                # pp_geometry_name = tools_dict[tooluid_key]['data']["ppname_g"]
                #
                # spindledir = self.app.defaults['geometry_spindledir']
                tool_solid_geometry = self.tools[tooluid_key]['solid_geometry']

                job_obj.coords_decimals = self.app.defaults["cncjob_coords_decimals"]
                job_obj.fr_decimals = self.app.defaults["cncjob_fr_decimals"]

                # Propagate options
                job_obj.options["tooldia"] = tooldia_val
                job_obj.options['type'] = 'Geometry'
                job_obj.options['tool_dia'] = tooldia_val

                # it seems that the tolerance needs to be a lot lower value than 0.01 and it was hardcoded initially
                # to a value of 0.0005 which is 20 times less than 0.01
                tol = float(self.app.defaults['global_tolerance']) / 20

                tool_lst = list(tools_dict.keys())
                is_first = True if tooluid_key == tool_lst[0] else False
                is_last = True if tooluid_key == tool_lst[-1] else False
                res, start_gcode = job_obj.geometry_tool_gcode_gen(tooluid_key, tools_dict, first_pt=(0, 0),
                                                                   tolerance=tol,
                                                                   is_first=is_first, is_last=is_last,
                                                                   toolchange=True)
                if res == 'fail':
                    log.debug("GeometryObject.mtool_gen_cncjob() --> generate_from_geometry2() failed")
                    return 'fail'
                else:
                    dia_cnc_dict['gcode'] = res
                total_gcode += res

                if start_gcode != '':
                    job_obj.gc_start = start_gcode

                app_obj.inform.emit('[success] %s' % _("G-Code parsing in progress..."))
                dia_cnc_dict['gcode_parsed'] = job_obj.gcode_parse()
                app_obj.inform.emit('[success] %s' % _("G-Code parsing finished..."))

                # commented this; there is no need for the actual GCode geometry - the original one will serve as well
                # for bounding box values
                # geo_for_bound_values = unary_union([
                #     geo['geom'] for geo in dia_cnc_dict['gcode_parsed'] if geo['geom'].is_valid is True
                # ])
                try:
                    dia_cnc_dict['solid_geometry'] = deepcopy(tool_solid_geometry)
                    app_obj.inform.emit('[success] %s...' % _("Finished G-Code processing"))
                except Exception as ee:
                    app_obj.inform.emit('[ERROR] %s: %s' % (_("G-Code processing failed with error"), str(ee)))

                # tell gcode_parse from which point to start drawing the lines depending on what kind of
                # object is the source of gcode
                job_obj.toolchange_xy_type = "geometry"

                job_obj.cnc_tools.update({
                    tooluid_key: deepcopy(dia_cnc_dict)
                })
                dia_cnc_dict.clear()

            job_obj.source_file = total_gcode

        if use_thread:
            # To be run in separate thread
            def job_thread(a_obj):
                if self.multigeo is False:
                    with self.app.proc_container.new(_("Generating CNC Code")):
                        ret_val = a_obj.app_obj.new_object("cncjob", outname, job_init_single_geometry, plot=plot)
                        if ret_val != 'fail':
                            a_obj.inform.emit('[success] %s: %s' % (_("CNCjob created"), outname))
                else:
                    with self.app.proc_container.new(_("Generating CNC Code")):
                        ret_val = a_obj.app_obj.new_object("cncjob", outname, job_init_multi_geometry, plot=plot)
                        if ret_val != 'fail':
                            a_obj.inform.emit('[success] %s: %s' % (_("CNCjob created"), outname))

            # Create a promise with the name
            self.app.collection.promise(outname)
            # Send to worker
            self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})
        else:
            if self.solid_geometry:
                self.app.app_obj.new_object("cncjob", outname, job_init_single_geometry, plot=plot)
            else:
                self.app.app_obj.new_object("cncjob", outname, job_init_multi_geometry, plot=plot)

    def generatecncjob(self, outname=None, dia=None, offset=None, z_cut=None, z_move=None, feedrate=None,
                       feedrate_z=None, feedrate_rapid=None, spindlespeed=None, dwell=None, dwelltime=None,
                       multidepth=None, dpp=None, toolchange=None, toolchangez=None, toolchangexy=None,
                       extracut=None, extracut_length=None, startz=None, endz=None, endxy=None, pp=None,
                       segx=None, segy=None, use_thread=True, plot=True):
        """
        Only used by the TCL Command Cncjob.
        Creates a CNCJob out of this Geometry object. The actual
        work is done by the target camlib.CNCjob
        `generate_from_geometry_2()` method.

        :param outname:         Name of the new object
        :param dia:             Tool diameter
        :param offset:
        :param z_cut:           Cut depth (negative value)
        :param z_move:          Height of the tool when travelling (not cutting)
        :param feedrate:        Feed rate while cutting on X - Y plane
        :param feedrate_z:      Feed rate while cutting on Z plane
        :param feedrate_rapid:  Feed rate while moving with rapids
        :param spindlespeed:    Spindle speed (RPM)
        :param dwell:
        :param dwelltime:
        :param multidepth:
        :param dpp:             Depth for each pass when multidepth parameter is True
        :param toolchange:
        :param toolchangez:
        :param toolchangexy:    A sequence ox X,Y coordinates: a 2-length tuple or a string.
                                Coordinates in X,Y plane for the Toolchange event
        :param extracut:
        :param extracut_length:
        :param startz:
        :param endz:
        :param endxy:           A sequence ox X,Y coordinates: a 2-length tuple or a string.
                                Coordinates in X, Y plane for the last move after ending the job.
        :param pp:              Name of the preprocessor
        :param segx:
        :param segy:
        :param use_thread:
        :param plot:
        :return: None
        """

        tooldia = dia if dia else float(self.options["cnctooldia"])
        outname = outname if outname is not None else self.options["name"]

        z_cut = z_cut if z_cut is not None else float(self.options["cutz"])
        z_move = z_move if z_move is not None else float(self.options["travelz"])

        feedrate = feedrate if feedrate is not None else float(self.options["feedrate"])
        feedrate_z = feedrate_z if feedrate_z is not None else float(self.options["feedrate_z"])
        feedrate_rapid = feedrate_rapid if feedrate_rapid is not None else float(self.options["feedrate_rapid"])

        multidepth = multidepth if multidepth is not None else self.options["multidepth"]
        depthperpass = dpp if dpp is not None else float(self.options["depthperpass"])

        segx = segx if segx is not None else float(self.app.defaults['geometry_segx'])
        segy = segy if segy is not None else float(self.app.defaults['geometry_segy'])

        extracut = extracut if extracut is not None else float(self.options["extracut"])
        extracut_length = extracut_length if extracut_length is not None else float(self.options["extracut_length"])

        startz = startz if startz is not None else self.options["startz"]
        endz = endz if endz is not None else float(self.options["endz"])

        endxy = endxy if endxy else self.options["endxy"]
        if isinstance(endxy, str):
            endxy = re.sub('[()\[\]]', '', endxy)
            if endxy and endxy != '':
                endxy = [float(eval(a)) for a in endxy.split(",")]

        toolchangez = toolchangez if toolchangez else float(self.options["toolchangez"])

        toolchangexy = toolchangexy if toolchangexy else self.options["toolchangexy"]
        if isinstance(toolchangexy, str):
            toolchangexy = re.sub('[()\[\]]', '', toolchangexy)
            if toolchangexy and toolchangexy != '':
                toolchangexy = [float(eval(a)) for a in toolchangexy.split(",")]

        toolchange = toolchange if toolchange else self.options["toolchange"]

        offset = offset if offset else 0.0

        # int or None.
        spindlespeed = spindlespeed if spindlespeed else self.options['spindlespeed']
        dwell = dwell if dwell else self.options["dwell"]
        dwelltime = dwelltime if dwelltime else float(self.options["dwelltime"])

        ppname_g = pp if pp else self.options["ppname_g"]

        # Object initialization function for app.app_obj.new_object()
        # RUNNING ON SEPARATE THREAD!
        def job_init(job_obj, app_obj):
            assert job_obj.kind == 'cncjob', "Initializer expected a CNCJobObject, got %s" % type(job_obj)

            # Propagate options
            job_obj.options["tooldia"] = tooldia

            job_obj.coords_decimals = self.app.defaults["cncjob_coords_decimals"]
            job_obj.fr_decimals = self.app.defaults["cncjob_fr_decimals"]

            job_obj.options['type'] = 'Geometry'
            job_obj.options['tool_dia'] = tooldia

            job_obj.segx = segx
            job_obj.segy = segy

            job_obj.z_pdepth = float(self.options["z_pdepth"])
            job_obj.feedrate_probe = float(self.options["feedrate_probe"])

            job_obj.options['xmin'] = self.options['xmin']
            job_obj.options['ymin'] = self.options['ymin']
            job_obj.options['xmax'] = self.options['xmax']
            job_obj.options['ymax'] = self.options['ymax']

            # it seems that the tolerance needs to be a lot lower value than 0.01 and it was hardcoded initially
            # to a value of 0.0005 which is 20 times less than 0.01
            tol = float(self.app.defaults['global_tolerance']) / 20
            res, start_gcode = job_obj.generate_from_geometry_2(
                self, tooldia=tooldia, offset=offset, tolerance=tol, z_cut=z_cut, z_move=z_move, feedrate=feedrate,
                feedrate_z=feedrate_z, feedrate_rapid=feedrate_rapid, spindlespeed=spindlespeed, dwell=dwell,
                dwelltime=dwelltime, multidepth=multidepth, depthpercut=depthperpass, toolchange=toolchange,
                toolchangez=toolchangez, toolchangexy=toolchangexy, extracut=extracut, extracut_length=extracut_length,
                startz=startz, endz=endz, endxy=endxy, pp_geometry_name=ppname_g, is_first=True)

            if start_gcode != '':
                job_obj.gc_start = start_gcode

            job_obj.source_file = start_gcode + res
            # tell gcode_parse from which point to start drawing the lines depending on what kind of object is the
            # source of gcode
            job_obj.toolchange_xy_type = "geometry"
            job_obj.gcode_parse()
            app_obj.inform.emit('[success] %s...' % _("Finished G-Code processing"))

        if use_thread:
            # To be run in separate thread
            def job_thread(app_obj):
                with self.app.proc_container.new(_("Generating CNC Code")):
                    app_obj.app_obj.new_object("cncjob", outname, job_init, plot=plot)
                    app_obj.inform.emit('[success] %s: %s' % (_("CNCjob created")), outname)

            # Create a promise with the name
            self.app.collection.promise(outname)
            # Send to worker
            self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})
        else:
            self.app.app_obj.new_object("cncjob", outname, job_init, plot=plot)

    def on_polish(self):

        def job_thread(obj):
            with obj.app.proc_container.new(_("Working ...")):
                tooldia = obj.ui.polish_dia_entry.get_value()
                depth = obj.ui.polish_pressure_entry.get_value()
                travelz = obj.ui.polish_travelz_entry.get_value()
                margin = obj.ui.polish_margin_entry.get_value()
                overlap = obj.ui.polish_over_entry.get_value() / 100
                paint_method = obj.ui.polish_method_combo.get_value()

                # calculate the max uid form the keys of the self.tools
                max_uid = max(list(obj.tools.keys()))
                new_uid = max_uid + 1

                # add a new key in the dict
                new_data = deepcopy(obj.default_data)
                new_data["travelz"] = travelz
                new_data["cutz"] = depth
                new_dict = {
                    new_uid: {
                        'tooldia': obj.app.dec_format(float(tooldia), obj.decimals),
                        'offset': 'Path',
                        'offset_value': 0.0,
                        'type': _('Polish'),
                        'tool_type': 'C1',
                        'data': new_data,
                        'solid_geometry': []
                    }
                }
                obj.tools.update(new_dict)
                obj.sel_tools.update(new_dict)

                # make a box polygon out of the bounds of the current object
                # apply the margin
                xmin, ymin, xmax, ymax = obj.bounds()
                bbox = box(xmin-margin, ymin-margin, xmax+margin, ymax+margin)

                # paint the box
                try:
                    # provide the app with a way to process the GUI events when in a blocking loop
                    QtWidgets.QApplication.processEvents()
                    if self.app.abort_flag:
                        # graceful abort requested by the user
                        raise grace

                    # Type(cpoly) == FlatCAMRTreeStorage | None
                    cpoly = None
                    if paint_method == 0:       # Standard
                        cpoly = self.clear_polygon(bbox,
                                                   tooldia=tooldia,
                                                   steps_per_circle=obj.circle_steps,
                                                   overlap=overlap,
                                                   contour=True,
                                                   connect=True,
                                                   prog_plot=False)
                    elif paint_method == 1:     # Seed
                        cpoly = self.clear_polygon2(bbox,
                                                    tooldia=tooldia,
                                                    steps_per_circle=obj.circle_steps,
                                                    overlap=overlap,
                                                    contour=True,
                                                    connect=True,
                                                    prog_plot=False)
                    elif paint_method == 2:     # Lines
                        cpoly = self.clear_polygon3(bbox,
                                                    tooldia=tooldia,
                                                    steps_per_circle=obj.circle_steps,
                                                    overlap=overlap,
                                                    contour=True,
                                                    connect=True,
                                                    prog_plot=False)

                    if not cpoly or not cpoly.objects:
                        obj.app.inform.emit('[ERROR_NOTCL] %s' % _('Geometry could not be painted completely'))
                        return

                    paint_geo = [g for g in cpoly.get_objects() if g and not g.is_empty]
                except grace:
                    return "fail"
                except Exception as e:
                    log.debug("Could not Paint the polygons. %s" % str(e))
                    mssg = '[ERROR] %s\n%s' % (_("Could not do Paint. Try a different combination of parameters. "
                                                 "Or a different method of Paint"), str(e))
                    self.app.inform.emit(mssg)
                    return

                obj.sel_tools[new_uid]['solid_geometry'] = paint_geo

                # and now create the CNCJob
                obj.launch_job.emit()

        # Send to worker
        self.app.worker_task.emit({'fcn': job_thread, 'params': [self]})

    def scale(self, xfactor, yfactor=None, point=None):
        """
        Scales all geometry by a given factor.

        :param xfactor:     Factor by which to scale the object's geometry/
        :type xfactor:      float
        :param yfactor:     Factor by which to scale the object's geometry/
        :type yfactor:      float
        :param point:       Point around which to scale
        :return: None
        :rtype: None
        """
        log.debug("FlatCAMObj.GeometryObject.scale()")

        try:
            xfactor = float(xfactor)
        except Exception:
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Scale factor has to be a number: integer or float."))
            return

        if yfactor is None:
            yfactor = xfactor
        else:
            try:
                yfactor = float(yfactor)
            except Exception:
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("Scale factor has to be a number: integer or float."))
                return

        if xfactor == 1 and yfactor == 1:
            return

        if point is None:
            px = 0
            py = 0
        else:
            px, py = point

        self.geo_len = 0
        self.old_disp_number = 0
        self.el_count = 0

        def scale_recursion(geom):
            if type(geom) is list:
                geoms = []
                for local_geom in geom:
                    geoms.append(scale_recursion(local_geom))
                return geoms
            else:
                try:
                    self.el_count += 1
                    disp_number = int(np.interp(self.el_count, [0, self.geo_len], [0, 100]))
                    if self.old_disp_number < disp_number <= 100:
                        self.app.proc_container.update_view_text(' %d%%' % disp_number)
                        self.old_disp_number = disp_number

                    return affinity.scale(geom, xfactor, yfactor, origin=(px, py))
                except AttributeError:
                    return geom

        if self.multigeo is True:
            for tool in self.tools:
                # variables to display the percentage of work done
                self.geo_len = 0
                try:
                    self.geo_len = len(self.tools[tool]['solid_geometry'])
                except TypeError:
                    self.geo_len = 1
                self.old_disp_number = 0
                self.el_count = 0

                self.tools[tool]['solid_geometry'] = scale_recursion(self.tools[tool]['solid_geometry'])

        try:
            # variables to display the percentage of work done
            self.geo_len = 0
            try:
                self.geo_len = len(self.solid_geometry)
            except TypeError:
                self.geo_len = 1
            self.old_disp_number = 0
            self.el_count = 0

            self.solid_geometry = scale_recursion(self.solid_geometry)
        except AttributeError:
            self.solid_geometry = []
            return

        self.app.proc_container.new_text = ''
        self.app.inform.emit('[success] %s' % _("Done."))

    def offset(self, vect):
        """
        Offsets all geometry by a given vector/

        :param vect: (x, y) vector by which to offset the object's geometry.
        :type vect: tuple
        :return: None
        :rtype: None
        """
        log.debug("FlatCAMObj.GeometryObject.offset()")

        try:
            dx, dy = vect
        except TypeError:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("An (x,y) pair of values are needed. "
                                   "Probable you entered only one value in the Offset field.")
                                 )
            return

        if dx == 0 and dy == 0:
            return

        self.geo_len = 0
        self.old_disp_number = 0
        self.el_count = 0

        def translate_recursion(geom):
            if type(geom) is list:
                geoms = []
                for local_geom in geom:
                    geoms.append(translate_recursion(local_geom))
                return geoms
            else:
                try:
                    self.el_count += 1
                    disp_number = int(np.interp(self.el_count, [0, self.geo_len], [0, 100]))
                    if self.old_disp_number < disp_number <= 100:
                        self.app.proc_container.update_view_text(' %d%%' % disp_number)
                        self.old_disp_number = disp_number

                    return affinity.translate(geom, xoff=dx, yoff=dy)
                except AttributeError:
                    return geom

        if self.multigeo is True:
            for tool in self.tools:
                # variables to display the percentage of work done
                self.geo_len = 0
                try:
                    self.geo_len = len(self.tools[tool]['solid_geometry'])
                except TypeError:
                    self.geo_len = 1
                self.old_disp_number = 0
                self.el_count = 0

                self.tools[tool]['solid_geometry'] = translate_recursion(self.tools[tool]['solid_geometry'])

        # variables to display the percentage of work done
        self.geo_len = 0
        try:
            self.geo_len = len(self.solid_geometry)
        except TypeError:
            self.geo_len = 1

        self.old_disp_number = 0
        self.el_count = 0

        self.solid_geometry = translate_recursion(self.solid_geometry)

        self.app.proc_container.new_text = ''
        self.app.inform.emit('[success] %s' % _("Done."))

    def convert_units(self, units):
        log.debug("FlatCAMObj.GeometryObject.convert_units()")

        self.ui_disconnect()

        factor = Geometry.convert_units(self, units)

        self.options['cutz'] = float(self.options['cutz']) * factor
        self.options['depthperpass'] = float(self.options['depthperpass']) * factor
        self.options['travelz'] = float(self.options['travelz']) * factor
        self.options['feedrate'] = float(self.options['feedrate']) * factor
        self.options['feedrate_z'] = float(self.options['feedrate_z']) * factor
        self.options['feedrate_rapid'] = float(self.options['feedrate_rapid']) * factor
        self.options['endz'] = float(self.options['endz']) * factor
        # self.options['cnctooldia'] *= factor
        # self.options['painttooldia'] *= factor
        # self.options['paintmargin'] *= factor
        # self.options['paintoverlap'] *= factor

        self.options["toolchangez"] = float(self.options["toolchangez"]) * factor

        if self.app.defaults["geometry_toolchangexy"] == '':
            self.options['toolchangexy'] = "0.0, 0.0"
        else:
            coords_xy = [float(eval(coord)) for coord in self.app.defaults["geometry_toolchangexy"].split(",")]
            if len(coords_xy) < 2:
                self.app.inform.emit('[ERROR] %s' %
                                     _("The Toolchange X,Y field in Edit -> Preferences "
                                       "has to be in the format (x, y)\n"
                                       "but now there is only one value, not two.")
                                     )
                return 'fail'
            coords_xy[0] *= factor
            coords_xy[1] *= factor
            self.options['toolchangexy'] = "%f, %f" % (coords_xy[0], coords_xy[1])

        if self.options['startz'] is not None:
            self.options['startz'] = float(self.options['startz']) * factor

        param_list = ['cutz', 'depthperpass', 'travelz', 'feedrate', 'feedrate_z', 'feedrate_rapid',
                      'endz', 'toolchangez']

        if isinstance(self, GeometryObject):
            temp_tools_dict = {}
            tool_dia_copy = {}
            data_copy = {}
            for tooluid_key, tooluid_value in self.tools.items():
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

                        # convert the value in the Custom Tool Offset entry in UI
                        custom_offset = None
                        try:
                            custom_offset = float(self.ui.tool_offset_entry.get_value())
                        except ValueError:
                            # try to convert comma to decimal point. if it's still not working error message and return
                            try:
                                custom_offset = float(self.ui.tool_offset_entry.get_value().replace(',', '.'))
                            except ValueError:
                                self.app.inform.emit('[ERROR_NOTCL] %s' %
                                                     _("Wrong value format entered, use a number."))
                                return
                        except TypeError:
                            pass

                        if custom_offset:
                            custom_offset *= factor
                            self.ui.tool_offset_entry.set_value(custom_offset)

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

                temp_tools_dict.update({
                    tooluid_key: deepcopy(tool_dia_copy)
                })
                tool_dia_copy.clear()

            self.tools.clear()
            self.tools = deepcopy(temp_tools_dict)

        # if there is a value in the new tool field then convert that one too
        try:
            self.ui.addtool_entry.returnPressed.disconnect()
        except TypeError:
            pass
        tooldia = self.ui.addtool_entry.get_value()
        if tooldia:
            tooldia *= factor
            tooldia = float('%.*f' % (self.decimals, tooldia))

            self.ui.addtool_entry.set_value(tooldia)
        self.ui.addtool_entry.returnPressed.connect(self.on_tool_default_add)

        return factor

    def on_add_area_click(self):
        shape_button = self.ui.area_shape_radio
        overz_button = self.ui.over_z_entry
        strategy_radio = self.ui.strategy_radio
        cnc_button = self.ui.generate_cnc_button
        solid_geo = self.solid_geometry
        obj_type = self.kind

        self.app.exc_areas.on_add_area_click(
            shape_button=shape_button, overz_button=overz_button, cnc_button=cnc_button, strategy_radio=strategy_radio,
            solid_geo=solid_geo, obj_type=obj_type)

    def on_clear_area_click(self):
        if not self.app.exc_areas.exclusion_areas_storage:
            self.app.inform.emit("[WARNING_NOTCL] %s" % _("Delete failed. There are no exclusion areas to delete."))
            return

        self.app.exc_areas.on_clear_area_click()
        self.app.exc_areas.e_shape_modified.emit()

    def on_delete_sel_areas(self):
        sel_model = self.ui.exclusion_table.selectionModel()
        sel_indexes = sel_model.selectedIndexes()

        # it will iterate over all indexes which means all items in all columns too but I'm interested only on rows
        # so the duplicate rows will not be added
        sel_rows = set()
        for idx in sel_indexes:
            sel_rows.add(idx.row())

        if not sel_rows:
            self.app.inform.emit("[WARNING_NOTCL] %s" % _("Delete failed. Nothing is selected."))
            return

        self.app.exc_areas.delete_sel_shapes(idxs=list(sel_rows))
        self.app.exc_areas.e_shape_modified.emit()

    def draw_sel_shape(self):
        sel_model = self.ui.exclusion_table.selectionModel()
        sel_indexes = sel_model.selectedIndexes()

        # it will iterate over all indexes which means all items in all columns too but I'm interested only on rows
        sel_rows = set()
        for idx in sel_indexes:
            sel_rows.add(idx.row())

        self.delete_sel_shape()

        if self.app.is_legacy is False:
            face = self.app.defaults['global_sel_fill'][:-2] + str(hex(int(0.2 * 255)))[2:]
            outline = self.app.defaults['global_sel_line'][:-2] + str(hex(int(0.8 * 255)))[2:]
        else:
            face = self.app.defaults['global_sel_fill'][:-2] + str(hex(int(0.4 * 255)))[2:]
            outline = self.app.defaults['global_sel_line'][:-2] + str(hex(int(1.0 * 255)))[2:]

        for row in sel_rows:
            sel_rect = self.app.exc_areas.exclusion_areas_storage[row]['shape']
            self.app.move_tool.sel_shapes.add(sel_rect, color=outline, face_color=face, update=True, layer=0,
                                              tolerance=None)
        if self.app.is_legacy is True:
            self.app.move_tool.sel_shapes.redraw()

    def clear_selection(self):
        self.app.delete_selection_shape()
        # self.ui.exclusion_table.clearSelection()

    def delete_sel_shape(self):
        self.app.delete_selection_shape()

    def update_exclusion_table(self):
        self.exclusion_area_cb_is_checked = True if self.ui.exclusion_cb.isChecked() else False

        self.build_ui()
        self.ui.exclusion_cb.set_value(self.exclusion_area_cb_is_checked)

    def on_strategy(self, val):
        if val == 'around':
            self.ui.over_z_label.setDisabled(True)
            self.ui.over_z_entry.setDisabled(True)
        else:
            self.ui.over_z_label.setDisabled(False)
            self.ui.over_z_entry.setDisabled(False)

    def exclusion_table_toggle_all(self):
        """
        will toggle the selection of all rows in Exclusion Areas table

        :return:
        """
        sel_model = self.ui.exclusion_table.selectionModel()
        sel_indexes = sel_model.selectedIndexes()

        # it will iterate over all indexes which means all items in all columns too but I'm interested only on rows
        sel_rows = set()
        for idx in sel_indexes:
            sel_rows.add(idx.row())

        if sel_rows:
            self.ui.exclusion_table.clearSelection()
            self.delete_sel_shape()
        else:
            self.ui.exclusion_table.selectAll()
            self.draw_sel_shape()

    def plot_element(self, element, color=None, visible=None):

        if color is None:
            color = '#FF0000FF'

        visible = visible if visible else self.options['plot']
        try:
            for sub_el in element:
                self.plot_element(sub_el, color=color)

        except TypeError:  # Element is not iterable...
            # if self.app.is_legacy is False:
            self.add_shape(shape=element, color=color, visible=visible, layer=0)

    def plot(self, visible=None, kind=None, plot_tool=None):
        """
        Plot the object.

        :param visible:     Controls if the added shape is visible of not
        :param kind:        added so there is no error when a project is loaded and it has both geometry and CNCJob,
                            because CNCJob require the 'kind' parameter. Perhaps the FlatCAMObj.plot()
                            has to be rewritten
        :param plot_tool:   plot a specific tool for multigeo objects
        :return:
        """

        # Does all the required setup and returns False
        # if the 'ptint' option is set to False.
        if not FlatCAMObj.plot(self):
            return

        if self.app.is_legacy is False:
            def random_color():
                r_color = np.random.rand(4)
                r_color[3] = 1
                return r_color
        else:
            def random_color():
                while True:
                    r_color = np.random.rand(4)
                    r_color[3] = 1

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
            # plot solid geometries found as members of self.tools attribute dict
            # for MultiGeo
            if self.multigeo is True:  # geo multi tool usage
                if plot_tool is None:
                    for tooluid_key in self.tools:
                        solid_geometry = self.tools[tooluid_key]['solid_geometry']
                        if 'override_color' in self.tools[tooluid_key]['data']:
                            color = self.tools[tooluid_key]['data']['override_color']
                        else:
                            color = random_color() if self.options['multicolored'] else \
                                self.app.defaults["geometry_plot_line"]

                        self.plot_element(solid_geometry, visible=visible, color=color)
                else:
                    solid_geometry = self.tools[plot_tool]['solid_geometry']
                    if 'override_color' in self.tools[plot_tool]['data']:
                        color = self.tools[plot_tool]['data']['override_color']
                    else:
                        color = random_color() if self.options['multicolored'] else \
                            self.app.defaults["geometry_plot_line"]

                    self.plot_element(solid_geometry, visible=visible, color=color)
            else:
                # plot solid geometry that may be an direct attribute of the geometry object
                # for SingleGeo
                if self.solid_geometry:
                    solid_geometry = self.solid_geometry
                    color = self.app.defaults["geometry_plot_line"]

                    self.plot_element(solid_geometry, visible=visible, color=color)

            # self.plot_element(self.solid_geometry, visible=self.options['plot'])

            self.shapes.redraw()

        except (ObjectDeleted, AttributeError):
            self.shapes.clear(update=True)

    def on_plot_cb_click(self):
        if self.muted_ui:
            return
        self.read_form_item('plot')
        self.plot()

        self.ui_disconnect()
        cb_flag = self.ui.plot_cb.isChecked()
        for row in range(self.ui.geo_tools_table.rowCount()):
            table_cb = self.ui.geo_tools_table.cellWidget(row, 6)
            if cb_flag:
                table_cb.setChecked(True)
            else:
                table_cb.setChecked(False)
        self.ui_connect()

    def on_plot_cb_click_table(self):
        # self.ui.cnc_tools_table.cellWidget(row, 2).widget().setCheckState(QtCore.Qt.Unchecked)
        self.ui_disconnect()
        # cw = self.sender()
        # cw_index = self.ui.geo_tools_table.indexAt(cw.pos())
        # cw_row = cw_index.row()
        check_row = 0

        self.shapes.clear(update=True)

        for tooluid_key in self.tools:
            solid_geometry = self.tools[tooluid_key]['solid_geometry']

            # find the geo_tool_table row associated with the tooluid_key
            for row in range(self.ui.geo_tools_table.rowCount()):
                tooluid_item = int(self.ui.geo_tools_table.item(row, 5).text())
                if tooluid_item == int(tooluid_key):
                    check_row = row
                    break

            if self.ui.geo_tools_table.cellWidget(check_row, 6).isChecked():
                try:
                    color = self.tools[tooluid_key]['data']['override_color']
                    self.plot_element(element=solid_geometry, visible=True, color=color)
                except KeyError:
                    self.plot_element(element=solid_geometry, visible=True)
        self.shapes.redraw()

        # make sure that the general plot is disabled if one of the row plot's are disabled and
        # if all the row plot's are enabled also enable the general plot checkbox
        cb_cnt = 0
        total_row = self.ui.geo_tools_table.rowCount()
        for row in range(total_row):
            if self.ui.geo_tools_table.cellWidget(row, 6).isChecked():
                cb_cnt += 1
            else:
                cb_cnt -= 1
        if cb_cnt < total_row:
            self.ui.plot_cb.setChecked(False)
        else:
            self.ui.plot_cb.setChecked(True)
        self.ui_connect()

    def on_multicolored_cb_click(self):
        if self.muted_ui:
            return
        self.read_form_item('multicolored')
        self.plot()

    @staticmethod
    def merge(geo_list, geo_final, multi_geo=None, fuse_tools=None):
        """
        Merges the geometry of objects in grb_list into the geometry of geo_final.

        :param geo_list:    List of GerberObject Objects to join.
        :param geo_final:   Destination GerberObject object.
        :param multi_geo:   if the merged geometry objects are of type MultiGeo
        :param fuse_tools:  If True will try to fuse tools of the same type for the Geometry objects
        :return: None
        """

        if geo_final.solid_geometry is None:
            geo_final.solid_geometry = []

        try:
            __ = iter(geo_final.solid_geometry)
        except TypeError:
            geo_final.solid_geometry = [geo_final.solid_geometry]

        new_solid_geometry = []
        new_options = {}
        new_tools = {}

        for geo_obj in geo_list:
            for option in geo_obj.options:
                if option != 'name':
                    try:
                        new_options[option] = deepcopy(geo_obj.options[option])
                    except Exception as e:
                        log.warning("Failed to copy option %s. Error: %s" % (str(option), str(e)))

            # Expand lists
            if type(geo_obj) is list:
                GeometryObject.merge(geo_list=geo_obj, geo_final=geo_final)
            # If not list, just append
            else:
                if multi_geo is None or multi_geo is False:
                    geo_final.multigeo = False
                else:
                    geo_final.multigeo = True

                try:
                    new_solid_geometry += deepcopy(geo_obj.solid_geometry)
                except Exception as e:
                    log.debug("GeometryObject.merge() --> %s" % str(e))

                # find the tool_uid maximum value in the geo_final
                try:
                    max_uid = max([int(i) for i in new_tools.keys()])
                except ValueError:
                    max_uid = 0

                # add and merge tools. If what we try to merge as Geometry is Excellon's and/or Gerber's then don't try
                # to merge the obj.tools as it is likely there is none to merge.
                if geo_obj.kind != 'gerber' and geo_obj.kind != 'excellon':
                    for tool_uid in geo_obj.tools:
                        max_uid += 1
                        new_tools[max_uid] = deepcopy(geo_obj.tools[tool_uid])

        geo_final.options.update(new_options)
        geo_final.solid_geometry = new_solid_geometry

        if new_tools and fuse_tools is True:
            # merge the geometries of the tools that share the same tool diameter and the same tool_type
            # and the same type
            final_tools = {}
            same_dia = defaultdict(list)
            same_type = defaultdict(list)
            same_tool_type = defaultdict(list)

            # find tools that have the same diameter and group them by diameter
            for k, v in new_tools.items():
                same_dia[v['tooldia']].append(k)

            # find tools that have the same type and group them by type
            for k, v in new_tools.items():
                same_type[v['type']].append(k)

            # find tools that have the same tool_type and group them by tool_type
            for k, v in new_tools.items():
                same_tool_type[v['tool_type']].append(k)

            # find the intersections in the above groups
            intersect_list = []
            for dia, dia_list in same_dia.items():
                for ty, type_list in same_type.items():
                    for t_ty, tool_type_list in same_tool_type.items():
                        intersection = reduce(np.intersect1d, (dia_list, type_list, tool_type_list)).tolist()
                        if intersection:
                            intersect_list.append(intersection)

            new_tool_nr = 1
            for i_lst in intersect_list:
                new_solid_geo = []
                last_tool = None
                for old_tool in i_lst:
                    new_solid_geo += new_tools[old_tool]['solid_geometry']
                    last_tool = old_tool

                if new_solid_geo and last_tool:
                    final_tools[new_tool_nr] = \
                        {
                            k: deepcopy(new_tools[last_tool][k]) for k in new_tools[last_tool] if k != 'solid_geometry'
                        }
                    final_tools[new_tool_nr]['solid_geometry'] = deepcopy(new_solid_geo)
                    new_tool_nr += 1
        else:
            final_tools = new_tools

        # if not final_tools:
        #     return 'fail'
        geo_final.tools = final_tools

    @staticmethod
    def get_pts(o):
        """
        Returns a list of all points in the object, where
        the object can be a MultiPolygon, Polygon, Not a polygon, or a list
        of such. Search is done recursively.

        :param: geometric object
        :return: List of points
        :rtype: list
        """
        pts = []

        # Iterable: descend into each item.
        try:
            for subo in o:
                pts += GeometryObject.get_pts(subo)

        # Non-iterable
        except TypeError:
            if o is not None:
                if type(o) == MultiPolygon:
                    for poly in o:
                        pts += GeometryObject.get_pts(poly)
                # ## Descend into .exerior and .interiors
                elif type(o) == Polygon:
                    pts += GeometryObject.get_pts(o.exterior)
                    for i in o.interiors:
                        pts += GeometryObject.get_pts(i)
                elif type(o) == MultiLineString:
                    for line in o:
                        pts += GeometryObject.get_pts(line)
                # ## Has .coords: list them.
                else:
                    pts += list(o.coords)
            else:
                return
        return pts
