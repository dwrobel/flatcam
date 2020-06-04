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


from shapely.geometry import Point, LineString

from copy import deepcopy

from appParsers.ParseExcellon import Excellon
from appObjects.FlatCAMObj import *

import itertools
import numpy as np

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ExcellonObject(FlatCAMObj, Excellon):
    """
    Represents Excellon/Drill code. An object stored in the FlatCAM objects collection (a dict)
    """

    ui_type = ExcellonObjectUI
    optionChanged = QtCore.pyqtSignal(str)

    def __init__(self, name):
        self.decimals = self.app.decimals

        self.circle_steps = int(self.app.defaults["geometry_circle_steps"])

        Excellon.__init__(self, geo_steps_per_circle=self.circle_steps)
        FlatCAMObj.__init__(self, name)

        self.kind = "excellon"

        self.options.update({
            "plot": True,
            "solid": False,
            "multicolored": False,

            "operation": "drill",
            "milling_type": "drills",

            "milling_dia": 0.04,

            "cutz": -0.1,
            "multidepth": False,
            "depthperpass": 0.7,
            "travelz": 0.1,
            "feedrate": self.app.defaults["geometry_feedrate"],
            "feedrate_z": 5.0,
            "feedrate_rapid": 5.0,
            "tooldia": 0.1,
            "slot_tooldia": 0.1,
            "toolchange": False,
            "toolchangez": 1.0,
            "toolchangexy": "0.0, 0.0",
            "extracut": self.app.defaults["geometry_extracut"],
            "extracut_length": self.app.defaults["geometry_extracut_length"],
            "endz": 2.0,
            "endxy": '',

            "startz": None,
            "offset": 0.0,
            "spindlespeed": 0,
            "dwell": True,
            "dwelltime": 1000,
            "ppname_e": 'default',
            "ppname_g": self.app.defaults["geometry_ppname_g"],
            "z_pdepth": -0.02,
            "feedrate_probe": 3.0,
            "optimization_type": "B",
        })

        # TODO: Document this.
        self.tool_cbs = {}

        # dict that holds the object names and the option name
        # the key is the object name (defines in ObjectUI) for each UI element that is a parameter
        # particular for a tool and the value is the actual name of the option that the UI element is changing
        self.name2option = {}

        # default set of data to be added to each tool in self.tools as self.tools[tool]['data'] = self.default_data
        self.default_data = {}

        # fill in self.default_data values from self.options
        for opt_key, opt_val in self.app.options.items():
            if opt_key.find('excellon_') == 0:
                self.default_data[opt_key] = deepcopy(opt_val)
        for opt_key, opt_val in self.app.options.items():
            if opt_key.find('geometry_') == 0:
                self.default_data[opt_key] = deepcopy(opt_val)

        # variable to store the total amount of drills per job
        self.tot_drill_cnt = 0
        self.tool_row = 0

        # variable to store the total amount of slots per job
        self.tot_slot_cnt = 0
        self.tool_row_slots = 0

        # variable to store the distance travelled
        self.travel_distance = 0.0

        # store the source file here
        self.source_file = ""

        self.multigeo = False
        self.units_found = self.app.defaults['units']

        self.fill_color = self.app.defaults['excellon_plot_fill']
        self.outline_color = self.app.defaults['excellon_plot_line']
        self.alpha_level = 'bf'

        # store here the state of the exclusion checkbox state to be restored after building the UI
        # TODO add this in the sel.app.defaults dict and in Preferences
        self.exclusion_area_cb_is_checked = False

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from predecessors.
        self.ser_attrs += ['options', 'kind']

    @staticmethod
    def merge(exc_list, exc_final, decimals=None):
        """
        Merge Excellon objects found in exc_list parameter into exc_final object.
        Options are always copied from source .

        Tools are disregarded, what is taken in consideration is the unique drill diameters found as values in the
        exc_list tools dict's. In the reconstruction section for each unique tool diameter it will be created a
        tool_name to be used in the final Excellon object, exc_final.

        If only one object is in exc_list parameter then this function will copy that object in the exc_final

        :param exc_list:    List or one object of ExcellonObject Objects to join.
        :type exc_list:     list
        :param exc_final:   Destination ExcellonObject object.
        :type exc_final:    class
        :return:            None
        """

        if decimals is None:
            decimals = 4
        decimals_exc = decimals

        # flag to signal that we need to reorder the tools dictionary and drills and slots lists
        flag_order = False

        try:
            flattened_list = list(itertools.chain(*exc_list))
        except TypeError:
            flattened_list = exc_list

        # this dict will hold the unique tool diameters found in the exc_list objects as the dict keys and the dict
        # values will be list of Shapely Points; for drills
        custom_dict_drills = {}

        # this dict will hold the unique tool diameters found in the exc_list objects as the dict keys and the dict
        # values will be list of Shapely Points; for slots
        custom_dict_slots = {}

        for exc in flattened_list:
            # copy options of the current excellon obj to the final excellon obj
            for option in exc.options:
                if option != 'name':
                    try:
                        exc_final.options[option] = exc.options[option]
                    except Exception:
                        exc.app.log.warning("Failed to copy option.", option)

            for drill in exc.drills:
                exc_tool_dia = float('%.*f' % (decimals_exc, exc.tools[drill['tool']]['C']))

                if exc_tool_dia not in custom_dict_drills:
                    custom_dict_drills[exc_tool_dia] = [drill['point']]
                else:
                    custom_dict_drills[exc_tool_dia].append(drill['point'])

            for slot in exc.slots:
                exc_tool_dia = float('%.*f' % (decimals_exc, exc.tools[slot['tool']]['C']))

                if exc_tool_dia not in custom_dict_slots:
                    custom_dict_slots[exc_tool_dia] = [[slot['start'], slot['stop']]]
                else:
                    custom_dict_slots[exc_tool_dia].append([slot['start'], slot['stop']])

            # add the zeros and units to the exc_final object
            exc_final.zeros = exc.zeros
            exc_final.units = exc.units

        # ##########################################
        # Here we add data to the exc_final object #
        # ##########################################

        # variable to make tool_name for the tools
        current_tool = 0
        # The tools diameter are now the keys in the drill_dia dict and the values are the Shapely Points in case of
        # drills
        for tool_dia in custom_dict_drills:
            # we create a tool name for each key in the drill_dia dict (the key is a unique drill diameter)
            current_tool += 1

            tool_name = str(current_tool)
            spec = {"C": float(tool_dia)}
            exc_final.tools[tool_name] = spec

            # rebuild the drills list of dict's that belong to the exc_final object
            for point in custom_dict_drills[tool_dia]:
                exc_final.drills.append(
                    {
                        "point": point,
                        "tool": str(current_tool)
                    }
                )

        # The tools diameter are now the keys in the drill_dia dict and the values are a list ([start, stop])
        # of two Shapely Points in case of slots
        for tool_dia in custom_dict_slots:
            # we create a tool name for each key in the slot_dia dict (the key is a unique slot diameter)
            # but only if there are no drills
            if not exc_final.tools:
                current_tool += 1
                tool_name = str(current_tool)
                spec = {"C": float(tool_dia)}
                exc_final.tools[tool_name] = spec
            else:
                dia_list = []
                for v in exc_final.tools.values():
                    dia_list.append(float(v["C"]))

                if tool_dia not in dia_list:
                    flag_order = True

                    current_tool = len(dia_list) + 1
                    tool_name = str(current_tool)
                    spec = {"C": float(tool_dia)}
                    exc_final.tools[tool_name] = spec

                else:
                    for k, v in exc_final.tools.items():
                        if v["C"] == tool_dia:
                            current_tool = int(k)
                            break

            # rebuild the slots list of dict's that belong to the exc_final object
            for point in custom_dict_slots[tool_dia]:
                exc_final.slots.append(
                    {
                        "start": point[0],
                        "stop": point[1],
                        "tool": str(current_tool)
                    }
                )

        # flag_order == True means that there was an slot diameter not in the tools and we also have drills
        # and the new tool was added to self.tools therefore we need to reorder the tools and drills and slots
        current_tool = 0
        if flag_order is True:
            dia_list = []
            temp_drills = []
            temp_slots = []
            temp_tools = {}
            for v in exc_final.tools.values():
                dia_list.append(float(v["C"]))
            dia_list.sort()
            for ordered_dia in dia_list:
                current_tool += 1
                tool_name_temp = str(current_tool)
                spec_temp = {"C": float(ordered_dia)}
                temp_tools[tool_name_temp] = spec_temp

                for drill in exc_final.drills:
                    exc_tool_dia = float('%.*f' % (decimals_exc, exc_final.tools[drill['tool']]['C']))
                    if exc_tool_dia == ordered_dia:
                        temp_drills.append(
                            {
                                "point": drill["point"],
                                "tool": str(current_tool)
                            }
                        )

                for slot in exc_final.slots:
                    slot_tool_dia = float('%.*f' % (decimals_exc, exc_final.tools[slot['tool']]['C']))
                    if slot_tool_dia == ordered_dia:
                        temp_slots.append(
                            {
                                "start": slot["start"],
                                "stop": slot["stop"],
                                "tool": str(current_tool)
                            }
                        )

            # delete the exc_final tools, drills and slots
            exc_final.tools = {}
            exc_final.drills[:] = []
            exc_final.slots[:] = []

            # update the exc_final tools, drills and slots with the ordered values
            exc_final.tools = temp_tools
            exc_final.drills[:] = temp_drills
            exc_final.slots[:] = temp_slots

        # create the geometry for the exc_final object
        exc_final.create_geometry()

    def build_ui(self):
        """
        Will (re)build the Excellon UI updating it (the tool table)

        :return:    None
        :rtype:
        """
        FlatCAMObj.build_ui(self)

        # Area Exception - exclusion shape added signal
        # first disconnect it from any other object
        try:
            self.app.exc_areas.e_shape_modified.disconnect()
        except (TypeError, AttributeError):
            pass
        # then connect it to the current build_ui() method
        self.app.exc_areas.e_shape_modified.connect(self.update_exclusion_table)

        self.units = self.app.defaults['units'].upper()

        for row in range(self.ui.tools_table.rowCount()):
            try:
                # if connected, disconnect the signal from the slot on item_changed as it creates issues
                offset_spin_widget = self.ui.tools_table.cellWidget(row, 4)
                offset_spin_widget.valueChanged.disconnect()
            except (TypeError, AttributeError):
                pass

        n = len(self.tools)
        # we have (n+2) rows because there are 'n' tools, each a row, plus the last 2 rows for totals.
        self.ui.tools_table.setRowCount(n + 2)

        self.tot_drill_cnt = 0
        self.tot_slot_cnt = 0

        self.tool_row = 0

        sort = []
        for k, v in list(self.tools.items()):
            sort.append((k, v.get('C')))
        sorted_tools = sorted(sort, key=lambda t1: t1[1])
        tools = [i[0] for i in sorted_tools]

        new_options = {}
        for opt in self.options:
            new_options[opt] = self.options[opt]

        for tool_no in tools:

            # add the data dictionary for each tool with the default values
            self.tools[tool_no]['data'] = deepcopy(new_options)
            # self.tools[tool_no]['data']["tooldia"] = self.tools[tool_no]["C"]
            # self.tools[tool_no]['data']["slot_tooldia"] = self.tools[tool_no]["C"]

            drill_cnt = 0  # variable to store the nr of drills per tool
            slot_cnt = 0  # variable to store the nr of slots per tool

            # Find no of drills for the current tool
            for drill in self.drills:
                if drill['tool'] == tool_no:
                    drill_cnt += 1

            self.tot_drill_cnt += drill_cnt

            # Find no of slots for the current tool
            for slot in self.slots:
                if slot['tool'] == tool_no:
                    slot_cnt += 1

            self.tot_slot_cnt += slot_cnt

            exc_id_item = QtWidgets.QTableWidgetItem('%d' % int(tool_no))
            exc_id_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

            dia_item = QtWidgets.QTableWidgetItem('%.*f' % (self.decimals, self.tools[tool_no]['C']))
            dia_item.setFlags(QtCore.Qt.ItemIsEnabled)

            drill_count_item = QtWidgets.QTableWidgetItem('%d' % drill_cnt)
            drill_count_item.setFlags(QtCore.Qt.ItemIsEnabled)

            # if the slot number is zero is better to not clutter the GUI with zero's so we print a space
            slot_count_str = '%d' % slot_cnt if slot_cnt > 0 else ''
            slot_count_item = QtWidgets.QTableWidgetItem(slot_count_str)
            slot_count_item.setFlags(QtCore.Qt.ItemIsEnabled)

            plot_item = FCCheckBox()
            plot_item.setLayoutDirection(QtCore.Qt.RightToLeft)
            if self.ui.plot_cb.isChecked():
                plot_item.setChecked(True)

            self.ui.tools_table.setItem(self.tool_row, 0, exc_id_item)  # Tool name/id
            self.ui.tools_table.setItem(self.tool_row, 1, dia_item)  # Diameter
            self.ui.tools_table.setItem(self.tool_row, 2, drill_count_item)  # Number of drills per tool
            self.ui.tools_table.setItem(self.tool_row, 3, slot_count_item)  # Number of drills per tool
            empty_plot_item = QtWidgets.QTableWidgetItem('')
            empty_plot_item.setFlags(~QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.ui.tools_table.setItem(self.tool_row, 5, empty_plot_item)
            self.ui.tools_table.setCellWidget(self.tool_row, 5, plot_item)

            self.tool_row += 1

        # add a last row with the Total number of drills
        empty_1 = QtWidgets.QTableWidgetItem('')
        empty_1.setFlags(~QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        empty_1_1 = QtWidgets.QTableWidgetItem('')
        empty_1_1.setFlags(~QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        empty_1_2 = QtWidgets.QTableWidgetItem('')
        empty_1_2.setFlags(~QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        empty_1_3 = QtWidgets.QTableWidgetItem('')
        empty_1_3.setFlags(~QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

        label_tot_drill_count = QtWidgets.QTableWidgetItem(_('Total Drills'))
        tot_drill_count = QtWidgets.QTableWidgetItem('%d' % self.tot_drill_cnt)
        label_tot_drill_count.setFlags(QtCore.Qt.ItemIsEnabled)
        tot_drill_count.setFlags(QtCore.Qt.ItemIsEnabled)

        self.ui.tools_table.setItem(self.tool_row, 0, empty_1)
        self.ui.tools_table.setItem(self.tool_row, 1, label_tot_drill_count)
        self.ui.tools_table.setItem(self.tool_row, 2, tot_drill_count)  # Total number of drills
        self.ui.tools_table.setItem(self.tool_row, 3, empty_1_1)
        self.ui.tools_table.setItem(self.tool_row, 5, empty_1_3)

        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)

        for k in [1, 2]:
            self.ui.tools_table.item(self.tool_row, k).setForeground(QtGui.QColor(127, 0, 255))
            self.ui.tools_table.item(self.tool_row, k).setFont(font)

        self.tool_row += 1

        # add a last row with the Total number of slots
        empty_2 = QtWidgets.QTableWidgetItem('')
        empty_2.setFlags(~QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        empty_2_1 = QtWidgets.QTableWidgetItem('')
        empty_2_1.setFlags(~QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        empty_2_2 = QtWidgets.QTableWidgetItem('')
        empty_2_2.setFlags(~QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        empty_2_3 = QtWidgets.QTableWidgetItem('')
        empty_2_3.setFlags(~QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

        label_tot_slot_count = QtWidgets.QTableWidgetItem(_('Total Slots'))
        tot_slot_count = QtWidgets.QTableWidgetItem('%d' % self.tot_slot_cnt)
        label_tot_slot_count.setFlags(QtCore.Qt.ItemIsEnabled)
        tot_slot_count.setFlags(QtCore.Qt.ItemIsEnabled)

        self.ui.tools_table.setItem(self.tool_row, 0, empty_2)
        self.ui.tools_table.setItem(self.tool_row, 1, label_tot_slot_count)
        self.ui.tools_table.setItem(self.tool_row, 2, empty_2_1)
        self.ui.tools_table.setItem(self.tool_row, 3, tot_slot_count)  # Total number of slots
        self.ui.tools_table.setItem(self.tool_row, 5, empty_2_3)

        for kl in [1, 2, 3]:
            self.ui.tools_table.item(self.tool_row, kl).setFont(font)
            self.ui.tools_table.item(self.tool_row, kl).setForeground(QtGui.QColor(0, 70, 255))

        # sort the tool diameter column
        # self.ui.tools_table.sortItems(1)

        # all the tools are selected by default
        self.ui.tools_table.selectColumn(0)

        self.ui.tools_table.resizeColumnsToContents()
        self.ui.tools_table.resizeRowsToContents()

        vertical_header = self.ui.tools_table.verticalHeader()
        # vertical_header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        vertical_header.hide()
        self.ui.tools_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        horizontal_header = self.ui.tools_table.horizontalHeader()
        horizontal_header.setMinimumSectionSize(10)
        horizontal_header.setDefaultSectionSize(70)
        horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(0, 20)

        horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)

        horizontal_header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(5, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(5, 17)
        self.ui.tools_table.setColumnWidth(5, 17)

        # horizontal_header.setStretchLastSection(True)
        # horizontal_header.setColumnWidth(2, QtWidgets.QHeaderView.ResizeToContents)

        # horizontal_header.setStretchLastSection(True)
        self.ui.tools_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.ui.tools_table.setSortingEnabled(False)

        self.ui.tools_table.setMinimumHeight(self.ui.tools_table.getHeight())
        self.ui.tools_table.setMaximumHeight(self.ui.tools_table.getHeight())

        if not self.drills:
            self.ui.tooldia_entry.hide()
            self.ui.generate_milling_button.hide()
        else:
            self.ui.tooldia_entry.show()
            self.ui.generate_milling_button.show()

        if not self.slots:
            self.ui.slot_tooldia_entry.hide()
            self.ui.generate_milling_slots_button.hide()
        else:
            self.ui.slot_tooldia_entry.show()
            self.ui.generate_milling_slots_button.show()

        # set the text on tool_data_label after loading the object
        sel_items = self.ui.tools_table.selectedItems()
        sel_rows = [it.row() for it in sel_items]
        if len(sel_rows) > 1:
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("Multiple Tools"))
            )

        # Build Exclusion Areas section
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

        self.ui_connect()

    def set_ui(self, ui):
        """
        Configures the user interface for this object.
        Connects options to form fields.

        :param ui:  User interface object.
        :type ui:   ExcellonObjectUI
        :return:    None
        """
        FlatCAMObj.set_ui(self, ui)

        log.debug("ExcellonObject.set_ui()")

        self.units = self.app.defaults['units'].upper()

        self.form_fields.update({
            "plot": self.ui.plot_cb,
            "solid": self.ui.solid_cb,
            "multicolored": self.ui.multicolored_cb,

            "operation": self.ui.operation_radio,
            "milling_type": self.ui.milling_type_radio,

            "milling_dia": self.ui.mill_dia_entry,
            "cutz": self.ui.cutz_entry,
            "multidepth": self.ui.mpass_cb,
            "depthperpass": self.ui.maxdepth_entry,
            "travelz": self.ui.travelz_entry,
            "feedrate_z": self.ui.feedrate_z_entry,
            "feedrate": self.ui.xyfeedrate_entry,
            "feedrate_rapid": self.ui.feedrate_rapid_entry,
            "tooldia": self.ui.tooldia_entry,
            "slot_tooldia": self.ui.slot_tooldia_entry,
            "toolchange": self.ui.toolchange_cb,
            "toolchangez": self.ui.toolchangez_entry,
            "extracut": self.ui.extracut_cb,
            "extracut_length": self.ui.e_cut_entry,

            "spindlespeed": self.ui.spindlespeed_entry,
            "dwell": self.ui.dwell_cb,
            "dwelltime": self.ui.dwelltime_entry,

            "startz": self.ui.estartz_entry,
            "endz": self.ui.endz_entry,
            "endxy": self.ui.endxy_entry,

            "offset": self.ui.offset_entry,

            "ppname_e": self.ui.pp_excellon_name_cb,
            "ppname_g": self.ui.pp_geo_name_cb,
            "z_pdepth": self.ui.pdepth_entry,
            "feedrate_probe": self.ui.feedrate_probe_entry,
            # "gcode_type": self.ui.excellon_gcode_type_radio,
            "area_exclusion": self.ui.exclusion_cb,
            "area_shape": self.ui.area_shape_radio,
            "area_strategy": self.ui.strategy_radio,
            "area_overz": self.ui.over_z_entry,
        })

        self.name2option = {
            "e_operation": "operation",
            "e_milling_type": "milling_type",
            "e_milling_dia": "milling_dia",
            "e_cutz": "cutz",
            "e_multidepth": "multidepth",
            "e_depthperpass": "depthperpass",

            "e_travelz": "travelz",
            "e_feedratexy": "feedrate",
            "e_feedratez": "feedrate_z",
            "e_fr_rapid": "feedrate_rapid",
            "e_extracut": "extracut",
            "e_extracut_length": "extracut_length",
            "e_spindlespeed": "spindlespeed",
            "e_dwell": "dwell",
            "e_dwelltime": "dwelltime",
            "e_offset": "offset",
        }

        # populate Excellon preprocessor combobox list
        for name in list(self.app.preprocessors.keys()):
            # the HPGL preprocessor is only for Geometry not for Excellon job therefore don't add it
            if name == 'hpgl':
                continue
            self.ui.pp_excellon_name_cb.addItem(name)

        # populate Geometry (milling) preprocessor combobox list
        for name in list(self.app.preprocessors.keys()):
            self.ui.pp_geo_name_cb.addItem(name)

        # Fill form fields
        self.to_form()

        # update the changes in UI depending on the selected preprocessor in Preferences
        # after this moment all the changes in the Posprocessor combo will be handled by the activated signal of the
        # self.ui.pp_excellon_name_cb combobox
        self.on_pp_changed()

        # Show/Hide Advanced Options
        if self.app.defaults["global_app_level"] == 'b':
            self.ui.level.setText('<span style="color:green;"><b>%s</b></span>' % _('Basic'))

            self.ui.tools_table.setColumnHidden(4, True)
            self.ui.tools_table.setColumnHidden(5, True)
            self.ui.estartz_label.hide()
            self.ui.estartz_entry.hide()
            self.ui.feedrate_rapid_label.hide()
            self.ui.feedrate_rapid_entry.hide()
            self.ui.pdepth_label.hide()
            self.ui.pdepth_entry.hide()
            self.ui.feedrate_probe_label.hide()
            self.ui.feedrate_probe_entry.hide()
        else:
            self.ui.level.setText('<span style="color:red;"><b>%s</b></span>' % _('Advanced'))

        assert isinstance(self.ui, ExcellonObjectUI), \
            "Expected a ExcellonObjectUI, got %s" % type(self.ui)

        self.ui.plot_cb.stateChanged.connect(self.on_plot_cb_click)
        self.ui.solid_cb.stateChanged.connect(self.on_solid_cb_click)
        self.ui.multicolored_cb.stateChanged.connect(self.on_multicolored_cb_click)

        self.ui.generate_cnc_button.clicked.connect(self.on_create_cncjob_button_click)
        self.ui.generate_milling_button.clicked.connect(self.on_generate_milling_button_click)
        self.ui.generate_milling_slots_button.clicked.connect(self.on_generate_milling_slots_button_click)

        # Exclusion areas signals
        self.ui.exclusion_table.horizontalHeader().sectionClicked.connect(self.exclusion_table_toggle_all)
        self.ui.exclusion_table.lost_focus.connect(self.clear_selection)
        self.ui.exclusion_table.itemClicked.connect(self.draw_sel_shape)
        self.ui.add_area_button.clicked.connect(self.on_add_area_click)
        self.ui.delete_area_button.clicked.connect(self.on_clear_area_click)
        self.ui.delete_sel_area_button.clicked.connect(self.on_delete_sel_areas)
        self.ui.strategy_radio.activated_custom.connect(self.on_strategy)

        self.on_operation_type(val='drill')
        self.ui.operation_radio.activated_custom.connect(self.on_operation_type)

        self.ui.pp_excellon_name_cb.activated.connect(self.on_pp_changed)

        self.ui.apply_param_to_all.clicked.connect(self.on_apply_param_to_all_clicked)

        self.units_found = self.app.defaults['units']

        # ########################################
        # #######3 TEMP SETTINGS #################
        # ########################################
        self.ui.operation_radio.set_value("drill")
        self.ui.operation_radio.setEnabled(False)

    def ui_connect(self):
        """
        Will connect all signals in the Excellon UI that needs to be connected

        :return:    None
        :rtype:
        """

        # selective plotting
        for row in range(self.ui.tools_table.rowCount() - 2):
            self.ui.tools_table.cellWidget(row, 5).clicked.connect(self.on_plot_cb_click_table)
        self.ui.plot_cb.stateChanged.connect(self.on_plot_cb_click)

        # rows selected
        self.ui.tools_table.clicked.connect(self.on_row_selection_change)
        self.ui.tools_table.horizontalHeader().sectionClicked.connect(self.on_row_selection_change)

        # value changed in the particular parameters of a tool
        for key, option in self.name2option.items():
            current_widget = self.form_fields[option]

            if isinstance(current_widget, FCCheckBox):
                current_widget.stateChanged.connect(self.form_to_storage)
            if isinstance(current_widget, RadioSet):
                current_widget.activated_custom.connect(self.form_to_storage)
            elif isinstance(current_widget, FCDoubleSpinner) or isinstance(current_widget, FCSpinner):
                current_widget.returnPressed.connect(self.form_to_storage)

    def ui_disconnect(self):
        """
        Will disconnect all signals in the Excellon UI that needs to be disconnected

        :return:    None
        :rtype:
        """
        # selective plotting
        for row in range(self.ui.tools_table.rowCount()):
            try:
                self.ui.tools_table.cellWidget(row, 5).clicked.disconnect()
            except (TypeError, AttributeError):
                pass
        try:
            self.ui.plot_cb.stateChanged.disconnect()
        except (TypeError, AttributeError):
            pass

        # rows selected
        try:
            self.ui.tools_table.clicked.disconnect()
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.tools_table.horizontalHeader().sectionClicked.disconnect()
        except (TypeError, AttributeError):
            pass

        # value changed in the particular parameters of a tool
        for key, option in self.name2option.items():
            current_widget = self.form_fields[option]

            if isinstance(current_widget, FCCheckBox):
                try:
                    current_widget.stateChanged.disconnect(self.form_to_storage)
                except (TypeError, ValueError):
                    pass
            if isinstance(current_widget, RadioSet):
                try:
                    current_widget.activated_custom.disconnect(self.form_to_storage)
                except (TypeError, ValueError):
                    pass
            elif isinstance(current_widget, FCDoubleSpinner) or isinstance(current_widget, FCSpinner):
                try:
                    current_widget.returnPressed.disconnect(self.form_to_storage)
                except (TypeError, ValueError):
                    pass

    def on_row_selection_change(self):
        """
        Called when the user clicks on a row in Tools Table

        :return:    None
        :rtype:
        """
        self.ui_disconnect()

        sel_rows = []
        sel_items = self.ui.tools_table.selectedItems()
        for it in sel_items:
            sel_rows.append(it.row())

        if not sel_rows:
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("No Tool Selected"))
            )
            self.ui.generate_cnc_button.setDisabled(True)
            self.ui.generate_milling_button.setDisabled(True)
            self.ui.generate_milling_slots_button.setDisabled(True)
            self.ui_connect()
            return
        else:
            self.ui.generate_cnc_button.setDisabled(False)
            self.ui.generate_milling_button.setDisabled(False)
            self.ui.generate_milling_slots_button.setDisabled(False)

        if len(sel_rows) == 1:
            # update the QLabel that shows for which Tool we have the parameters in the UI form
            tooluid = int(self.ui.tools_table.item(sel_rows[0], 0).text())
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s %d</font></b>" % (_('Parameters for'), _("Tool"), tooluid)
            )
        else:
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("Multiple Tools"))
            )

        for c_row in sel_rows:
            # populate the form with the data from the tool associated with the row parameter
            try:
                item = self.ui.tools_table.item(c_row, 0)
                if type(item) is not None:
                    tooluid = item.text()
                    self.storage_to_form(self.tools[str(tooluid)]['data'])
                else:
                    self.ui_connect()
                    return
            except Exception as e:
                log.debug("Tool missing. Add a tool in Geo Tool Table. %s" % str(e))
                self.ui_connect()
                return

        self.ui_connect()

    def storage_to_form(self, dict_storage):
        """
        Will update the GUI with data from the "storage" in this case the dict self.tools

        :param dict_storage:    A dictionary holding the data relevant for gnerating Gcode from Excellon
        :type dict_storage:     dict
        :return:                None
        :rtype:
        """
        for form_key in self.form_fields:
            for storage_key in dict_storage:
                if form_key == storage_key and form_key not in \
                        ["toolchange", "toolchangez", "startz", "endz", "ppname_e", "ppname_g"]:
                    try:
                        self.form_fields[form_key].set_value(dict_storage[form_key])
                    except Exception as e:
                        log.debug("ExcellonObject.storage_to_form() --> %s" % str(e))
                        pass

    def form_to_storage(self):
        """
        Will update the 'storage' attribute which is the dict self.tools with data collected from GUI

        :return:    None
        :rtype:
        """
        if self.ui.tools_table.rowCount() == 0:
            # there is no tool in tool table so we can't save the GUI elements values to storage
            return

        self.ui_disconnect()

        widget_changed = self.sender()
        wdg_objname = widget_changed.objectName()
        option_changed = self.name2option[wdg_objname]

        # row = self.ui.tools_table.currentRow()
        rows = sorted(set(index.row() for index in self.ui.tools_table.selectedIndexes()))
        for row in rows:
            if row < 0:
                row = 0
            tooluid_item = int(self.ui.tools_table.item(row, 0).text())

            for tooluid_key, tooluid_val in self.tools.items():
                if int(tooluid_key) == tooluid_item:
                    new_option_value = self.form_fields[option_changed].get_value()
                    if option_changed in tooluid_val:
                        tooluid_val[option_changed] = new_option_value
                    if option_changed in tooluid_val['data']:
                        tooluid_val['data'][option_changed] = new_option_value

        self.ui_connect()

    def on_operation_type(self, val):
        """
        Called by a RadioSet activated_custom signal

        :param val:     Parameter passes by the signal that called this method
        :type val:      str
        :return:        None
        :rtype:
        """
        if val == 'mill':
            self.ui.mill_type_label.show()
            self.ui.milling_type_radio.show()
            self.ui.mill_dia_label.show()
            self.ui.mill_dia_entry.show()
            self.ui.frxylabel.show()
            self.ui.xyfeedrate_entry.show()
            self.ui.extracut_cb.show()
            self.ui.e_cut_entry.show()

            # if 'laser' not in self.ui.pp_excellon_name_cb.get_value().lower():
            #     self.ui.mpass_cb.show()
            #     self.ui.maxdepth_entry.show()
        else:
            self.ui.mill_type_label.hide()
            self.ui.milling_type_radio.hide()
            self.ui.mill_dia_label.hide()
            self.ui.mill_dia_entry.hide()
            # self.ui.mpass_cb.hide()
            # self.ui.maxdepth_entry.hide()
            self.ui.frxylabel.hide()
            self.ui.xyfeedrate_entry.hide()
            self.ui.extracut_cb.hide()
            self.ui.e_cut_entry.hide()

    def get_selected_tools_list(self):
        """
        Returns the keys to the self.tools dictionary corresponding
        to the selections on the tool list in the appGUI.

        :return:    List of tools.
        :rtype:     list
        """

        return [str(x.text()) for x in self.ui.tools_table.selectedItems()]

    def get_selected_tools_table_items(self):
        """
        Returns a list of lists, each list in the list is made out of row elements

        :return:    List of table_tools items.
        :rtype:     list
        """
        table_tools_items = []
        for x in self.ui.tools_table.selectedItems():
            # from the columnCount we subtract a value of 1 which represent the last column (plot column)
            # which does not have text
            txt = ''
            elem = []

            for column in range(0, self.ui.tools_table.columnCount() - 1):
                try:
                    txt = self.ui.tools_table.item(x.row(), column).text()
                except AttributeError:
                    try:
                        txt = self.ui.tools_table.cellWidget(x.row(), column).currentText()
                    except AttributeError:
                        pass
                elem.append(txt)
            table_tools_items.append(deepcopy(elem))
            # table_tools_items.append([self.ui.tools_table.item(x.row(), column).text()
            #                           for column in range(0, self.ui.tools_table.columnCount() - 1)])
        for item in table_tools_items:
            item[0] = str(item[0])
        return table_tools_items

    def export_excellon(self, whole, fract, e_zeros=None, form='dec', factor=1, slot_type='routing'):
        """
        Returns two values, first is a boolean , if 1 then the file has slots and second contain the Excellon code

        :param whole:       Integer part digits
        :type whole:        int
        :param fract:       Fractional part digits
        :type fract:        int
        :param e_zeros:     Excellon zeros suppression: LZ or TZ
        :type e_zeros:      str
        :param form:        Excellon format: 'dec',
        :type form:         str
        :param factor:      Conversion factor
        :type factor:       float
        :param slot_type:   How to treat slots: "routing" or "drilling"
        :type slot_type:    str
        :return:            A tuple: (has_slots, Excellon_code) -> (bool, str)
        :rtype:             tuple
        """

        excellon_code = ''

        # store here if the file has slots, return 1 if any slots, 0 if only drills
        has_slots = 0

        # drills processing
        try:
            if self.drills:
                length = whole + fract
                for tool in self.tools:
                    excellon_code += 'T0%s\n' % str(tool) if int(tool) < 10 else 'T%s\n' % str(tool)

                    for drill in self.drills:
                        if form == 'dec' and tool == drill['tool']:
                            drill_x = drill['point'].x * factor
                            drill_y = drill['point'].y * factor
                            excellon_code += "X{:.{dec}f}Y{:.{dec}f}\n".format(drill_x, drill_y, dec=fract)
                        elif e_zeros == 'LZ' and tool == drill['tool']:
                            drill_x = drill['point'].x * factor
                            drill_y = drill['point'].y * factor

                            exc_x_formatted = "{:.{dec}f}".format(drill_x, dec=fract)
                            exc_y_formatted = "{:.{dec}f}".format(drill_y, dec=fract)

                            # extract whole part and decimal part
                            exc_x_formatted = exc_x_formatted.partition('.')
                            exc_y_formatted = exc_y_formatted.partition('.')

                            # left padd the 'whole' part with zeros
                            x_whole = exc_x_formatted[0].rjust(whole, '0')
                            y_whole = exc_y_formatted[0].rjust(whole, '0')

                            # restore the coordinate padded in the left with 0 and added the decimal part
                            # without the decinal dot
                            exc_x_formatted = x_whole + exc_x_formatted[2]
                            exc_y_formatted = y_whole + exc_y_formatted[2]

                            excellon_code += "X{xform}Y{yform}\n".format(xform=exc_x_formatted,
                                                                         yform=exc_y_formatted)
                        elif tool == drill['tool']:
                            drill_x = drill['point'].x * factor
                            drill_y = drill['point'].y * factor

                            exc_x_formatted = "{:.{dec}f}".format(drill_x, dec=fract).replace('.', '')
                            exc_y_formatted = "{:.{dec}f}".format(drill_y, dec=fract).replace('.', '')

                            # pad with rear zeros
                            exc_x_formatted.ljust(length, '0')
                            exc_y_formatted.ljust(length, '0')

                            excellon_code += "X{xform}Y{yform}\n".format(xform=exc_x_formatted,
                                                                         yform=exc_y_formatted)
        except Exception as e:
            log.debug(str(e))

        # slots processing
        try:
            if self.slots:
                has_slots = 1
                for tool in self.tools:
                    excellon_code += 'G05\n'

                    if int(tool) < 10:
                        excellon_code += 'T0' + str(tool) + '\n'
                    else:
                        excellon_code += 'T' + str(tool) + '\n'

                    for slot in self.slots:
                        if form == 'dec' and tool == slot['tool']:
                            start_slot_x = slot['start'].x * factor
                            start_slot_y = slot['start'].y * factor
                            stop_slot_x = slot['stop'].x * factor
                            stop_slot_y = slot['stop'].y * factor
                            if slot_type == 'routing':
                                excellon_code += "G00X{:.{dec}f}Y{:.{dec}f}\nM15\n".format(start_slot_x,
                                                                                           start_slot_y,
                                                                                           dec=fract)
                                excellon_code += "G01X{:.{dec}f}Y{:.{dec}f}\nM16\n".format(stop_slot_x,
                                                                                           stop_slot_y,
                                                                                           dec=fract)
                            elif slot_type == 'drilling':
                                excellon_code += "X{:.{dec}f}Y{:.{dec}f}G85X{:.{dec}f}Y{:.{dec}f}\nG05\n".format(
                                    start_slot_x, start_slot_y, stop_slot_x, stop_slot_y, dec=fract
                                )

                        elif e_zeros == 'LZ' and tool == slot['tool']:
                            start_slot_x = slot['start'].x * factor
                            start_slot_y = slot['start'].y * factor
                            stop_slot_x = slot['stop'].x * factor
                            stop_slot_y = slot['stop'].y * factor

                            start_slot_x_formatted = "{:.{dec}f}".format(start_slot_x, dec=fract).replace('.', '')
                            start_slot_y_formatted = "{:.{dec}f}".format(start_slot_y, dec=fract).replace('.', '')
                            stop_slot_x_formatted = "{:.{dec}f}".format(stop_slot_x, dec=fract).replace('.', '')
                            stop_slot_y_formatted = "{:.{dec}f}".format(stop_slot_y, dec=fract).replace('.', '')

                            # extract whole part and decimal part
                            start_slot_x_formatted = start_slot_x_formatted.partition('.')
                            start_slot_y_formatted = start_slot_y_formatted.partition('.')
                            stop_slot_x_formatted = stop_slot_x_formatted.partition('.')
                            stop_slot_y_formatted = stop_slot_y_formatted.partition('.')

                            # left padd the 'whole' part with zeros
                            start_x_whole = start_slot_x_formatted[0].rjust(whole, '0')
                            start_y_whole = start_slot_y_formatted[0].rjust(whole, '0')
                            stop_x_whole = stop_slot_x_formatted[0].rjust(whole, '0')
                            stop_y_whole = stop_slot_y_formatted[0].rjust(whole, '0')

                            # restore the coordinate padded in the left with 0 and added the decimal part
                            # without the decinal dot
                            start_slot_x_formatted = start_x_whole + start_slot_x_formatted[2]
                            start_slot_y_formatted = start_y_whole + start_slot_y_formatted[2]
                            stop_slot_x_formatted = stop_x_whole + stop_slot_x_formatted[2]
                            stop_slot_y_formatted = stop_y_whole + stop_slot_y_formatted[2]

                            if slot_type == 'routing':
                                excellon_code += "G00X{xstart}Y{ystart}\nM15\n".format(xstart=start_slot_x_formatted,
                                                                                       ystart=start_slot_y_formatted)
                                excellon_code += "G01X{xstop}Y{ystop}\nM16\n".format(xstop=stop_slot_x_formatted,
                                                                                     ystop=stop_slot_y_formatted)
                            elif slot_type == 'drilling':
                                excellon_code += "{xstart}Y{ystart}G85X{xstop}Y{ystop}\nG05\n".format(
                                    xstart=start_slot_x_formatted, ystart=start_slot_y_formatted,
                                    xstop=stop_slot_x_formatted, ystop=stop_slot_y_formatted
                                )
                        elif tool == slot['tool']:
                            start_slot_x = slot['start'].x * factor
                            start_slot_y = slot['start'].y * factor
                            stop_slot_x = slot['stop'].x * factor
                            stop_slot_y = slot['stop'].y * factor
                            length = whole + fract

                            start_slot_x_formatted = "{:.{dec}f}".format(start_slot_x, dec=fract).replace('.', '')
                            start_slot_y_formatted = "{:.{dec}f}".format(start_slot_y, dec=fract).replace('.', '')
                            stop_slot_x_formatted = "{:.{dec}f}".format(stop_slot_x, dec=fract).replace('.', '')
                            stop_slot_y_formatted = "{:.{dec}f}".format(stop_slot_y, dec=fract).replace('.', '')

                            # pad with rear zeros
                            start_slot_x_formatted.ljust(length, '0')
                            start_slot_y_formatted.ljust(length, '0')
                            stop_slot_x_formatted.ljust(length, '0')
                            stop_slot_y_formatted.ljust(length, '0')

                            if slot_type == 'routing':
                                excellon_code += "G00X{xstart}Y{ystart}\nM15\n".format(xstart=start_slot_x_formatted,
                                                                                       ystart=start_slot_y_formatted)
                                excellon_code += "G01X{xstop}Y{ystop}\nM16\n".format(xstop=stop_slot_x_formatted,
                                                                                     ystop=stop_slot_y_formatted)
                            elif slot_type == 'drilling':
                                excellon_code += "{xstart}Y{ystart}G85X{xstop}Y{ystop}\nG05\n".format(
                                    xstart=start_slot_x_formatted, ystart=start_slot_y_formatted,
                                    xstop=stop_slot_x_formatted, ystop=stop_slot_y_formatted
                                )
        except Exception as e:
            log.debug(str(e))

        if not self.drills and not self.slots:
            log.debug("FlatCAMObj.ExcellonObject.export_excellon() --> Excellon Object is empty: no drills, no slots.")
            return 'fail'

        return has_slots, excellon_code

    def generate_milling_drills(self, tools=None, outname=None, tooldia=None, plot=False, use_thread=False):
        """
        Will generate an Geometry Object allowing to cut a drill hole instead of drilling it.

        Note: This method is a good template for generic operations as
        it takes it's options from parameters or otherwise from the
        object's options and returns a (success, msg) tuple as feedback
        for shell operations.

        :param tools:       A list of tools where the drills are to be milled or a string: "all"
        :type tools:
        :param outname:     the name of the resulting Geometry object
        :type outname:      str
        :param tooldia:     the tool diameter to be used in creation of the milling path (Geometry Object)
        :type tooldia:      float
        :param plot:        if to plot the resulting object
        :type plot:         bool
        :param use_thread:  if to use threading for creation of the Geometry object
        :type use_thread:   bool
        :return:            Success/failure condition tuple (bool, str).
        :rtype:             tuple
        """

        # Get the tools from the list. These are keys
        # to self.tools
        if tools is None:
            tools = self.get_selected_tools_list()

        if outname is None:
            outname = self.options["name"] + "_mill"

        if tooldia is None:
            tooldia = float(self.options["tooldia"])

        # Sort tools by diameter. items() -> [('name', diameter), ...]
        # sorted_tools = sorted(list(self.tools.items()), key=lambda tl: tl[1]) # no longer works in Python3

        sort = []
        for k, v in self.tools.items():
            sort.append((k, v.get('C')))
        sorted_tools = sorted(sort, key=lambda t1: t1[1])

        if tools == "all":
            tools = [i[0] for i in sorted_tools]  # List if ordered tool names.
            log.debug("Tools 'all' and sorted are: %s" % str(tools))

        if len(tools) == 0:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Please select one or more tools from the list and try again."))
            return False, "Error: No tools."

        for tool in tools:
            if tooldia > self.tools[tool]["C"]:
                self.app.inform.emit(
                    '[ERROR_NOTCL] %s %s: %s' % (
                        _("Milling tool for DRILLS is larger than hole size. Cancelled."),
                        _("Tool"),
                        str(tool)
                    )
                )
                return False, "Error: Milling tool is larger than hole."

        def geo_init(geo_obj, app_obj):
            """

            :param geo_obj:     New object
            :type geo_obj:      GeometryObject
            :param app_obj:     App
            :type app_obj:      FlatCAMApp.App
            :return:
            :rtype:
            """
            assert geo_obj.kind == 'geometry', "Initializer expected a GeometryObject, got %s" % type(geo_obj)

            # ## Add properties to the object

            # get the tool_table items in a list of row items
            tool_table_items = self.get_selected_tools_table_items()
            # insert an information only element in the front
            tool_table_items.insert(0, [_("Tool_nr"), _("Diameter"), _("Drills_Nr"), _("Slots_Nr")])

            geo_obj.options['Tools_in_use'] = tool_table_items
            geo_obj.options['type'] = 'Excellon Geometry'
            geo_obj.options["cnctooldia"] = str(tooldia)
            geo_obj.options["multidepth"] = self.options["multidepth"]
            geo_obj.solid_geometry = []

            # in case that the tool used has the same diameter with the hole, and since the maximum resolution
            # for FlatCAM is 6 decimals,
            # we add a tenth of the minimum value, meaning 0.0000001, which from our point of view is "almost zero"
            for hole in self.drills:
                if hole['tool'] in tools:
                    buffer_value = self.tools[hole['tool']]["C"] / 2 - tooldia / 2
                    if buffer_value == 0:
                        geo_obj.solid_geometry.append(
                            Point(hole['point']).buffer(0.0000001).exterior)
                    else:
                        geo_obj.solid_geometry.append(
                            Point(hole['point']).buffer(buffer_value).exterior)

        if use_thread:
            def geo_thread(a_obj):
                a_obj.app_obj.new_object("geometry", outname, geo_init, plot=plot)

            # Create a promise with the new name
            self.app.collection.promise(outname)

            # Send to worker
            self.app.worker_task.emit({'fcn': geo_thread, 'params': [self.app]})
        else:
            self.app.app_obj.new_object("geometry", outname, geo_init, plot=plot)

        return True, ""

    def generate_milling_slots(self, tools=None, outname=None, tooldia=None, plot=False, use_thread=False):
        """
        Will generate an Geometry Object allowing to cut/mill a slot hole.

        Note: This method is a good template for generic operations as
        it takes it's options from parameters or otherwise from the
        object's options and returns a (success, msg) tuple as feedback
        for shell operations.

        :param tools:       A list of tools where the drills are to be milled or a string: "all"
        :type tools:
        :param outname:     the name of the resulting Geometry object
        :type outname:      str
        :param tooldia:     the tool diameter to be used in creation of the milling path (Geometry Object)
        :type tooldia:      float
        :param plot:        if to plot the resulting object
        :type plot:         bool
        :param use_thread:  if to use threading for creation of the Geometry object
        :type use_thread:   bool
        :return:            Success/failure condition tuple (bool, str).
        :rtype:             tuple
        """

        # Get the tools from the list. These are keys
        # to self.tools
        if tools is None:
            tools = self.get_selected_tools_list()

        if outname is None:
            outname = self.options["name"] + "_mill"

        if tooldia is None:
            tooldia = float(self.options["slot_tooldia"])

        # Sort tools by diameter. items() -> [('name', diameter), ...]
        # sorted_tools = sorted(list(self.tools.items()), key=lambda tl: tl[1]) # no longer works in Python3

        sort = []
        for k, v in self.tools.items():
            sort.append((k, v.get('C')))
        sorted_tools = sorted(sort, key=lambda t1: t1[1])

        if tools == "all":
            tools = [i[0] for i in sorted_tools]  # List if ordered tool names.
            log.debug("Tools 'all' and sorted are: %s" % str(tools))

        if len(tools) == 0:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Please select one or more tools from the list and try again."))
            return False, "Error: No tools."

        for tool in tools:
            # I add the 0.0001 value to account for the rounding error in converting from IN to MM and reverse
            adj_toolstable_tooldia = float('%.*f' % (self.decimals, float(tooldia)))
            adj_file_tooldia = float('%.*f' % (self.decimals, float(self.tools[tool]["C"])))
            if adj_toolstable_tooldia > adj_file_tooldia + 0.0001:
                self.app.inform.emit('[ERROR_NOTCL] %s' %
                                     _("Milling tool for SLOTS is larger than hole size. Cancelled."))
                return False, "Error: Milling tool is larger than hole."

        def geo_init(geo_obj, app_obj):
            assert geo_obj.kind == 'geometry', "Initializer expected a GeometryObject, got %s" % type(geo_obj)

            # ## Add properties to the object

            # get the tool_table items in a list of row items
            tool_table_items = self.get_selected_tools_table_items()
            # insert an information only element in the front
            tool_table_items.insert(0, [_("Tool_nr"), _("Diameter"), _("Drills_Nr"), _("Slots_Nr")])

            geo_obj.options['Tools_in_use'] = tool_table_items
            geo_obj.options['type'] = 'Excellon Geometry'
            geo_obj.options["cnctooldia"] = str(tooldia)
            geo_obj.options["multidepth"] = self.options["multidepth"]
            geo_obj.solid_geometry = []

            # in case that the tool used has the same diameter with the hole, and since the maximum resolution
            # for FlatCAM is 6 decimals,
            # we add a tenth of the minimum value, meaning 0.0000001, which from our point of view is "almost zero"
            for slot in self.slots:
                if slot['tool'] in tools:
                    toolstable_tool = float('%.*f' % (self.decimals, float(tooldia)))
                    file_tool = float('%.*f' % (self.decimals, float(self.tools[tool]["C"])))

                    # I add the 0.0001 value to account for the rounding error in converting from IN to MM and reverse
                    # for the file_tool (tooldia actually)
                    buffer_value = float(file_tool / 2) - float(toolstable_tool / 2) + 0.0001
                    if buffer_value == 0:
                        start = slot['start']
                        stop = slot['stop']

                        lines_string = LineString([start, stop])
                        poly = lines_string.buffer(0.0000001, int(self.geo_steps_per_circle)).exterior
                        geo_obj.solid_geometry.append(poly)
                    else:
                        start = slot['start']
                        stop = slot['stop']

                        lines_string = LineString([start, stop])
                        poly = lines_string.buffer(buffer_value, int(self.geo_steps_per_circle)).exterior
                        geo_obj.solid_geometry.append(poly)

        if use_thread:
            def geo_thread(a_obj):
                a_obj.app_obj.new_object("geometry", outname + '_slot', geo_init, plot=plot)

            # Create a promise with the new name
            self.app.collection.promise(outname)

            # Send to worker
            self.app.worker_task.emit({'fcn': geo_thread, 'params': [self.app]})
        else:
            self.app.app_obj.new_object("geometry", outname + '_slot', geo_init, plot=plot)

        return True, ""

    def on_generate_milling_button_click(self, *args):
        self.app.defaults.report_usage("excellon_on_create_milling_drills button")
        self.read_form()

        self.generate_milling_drills(use_thread=False, plot=True)

    def on_generate_milling_slots_button_click(self, *args):
        self.app.defaults.report_usage("excellon_on_create_milling_slots_button")
        self.read_form()

        self.generate_milling_slots(use_thread=False, plot=True)

    def on_pp_changed(self):
        current_pp = self.ui.pp_excellon_name_cb.get_value()

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
            self.ui.feedrate_rapid_label.show()
            self.ui.feedrate_rapid_entry.show()
        else:
            self.ui.feedrate_rapid_label.hide()
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

    def on_create_cncjob_button_click(self, *args):
        self.app.defaults.report_usage("excellon_on_create_cncjob_button")
        self.read_form()

        # Get the tools from the list
        tools = self.get_selected_tools_list()

        if len(tools) == 0:
            # if there is a single tool in the table (remember that the last 2 rows are for totals and do not count in
            # tool number) it means that there are 3 rows (1 tool and 2 totals).
            # in this case regardless of the selection status of that tool, use it.
            if self.ui.tools_table.rowCount() == 3:
                tools.append(self.ui.tools_table.item(0, 0).text())
            else:
                self.app.inform.emit('[ERROR_NOTCL] %s' %
                                     _("Please select one or more tools from the list and try again."))
                return

        xmin = self.options['xmin']
        ymin = self.options['ymin']
        xmax = self.options['xmax']
        ymax = self.options['ymax']

        job_name = self.options["name"] + "_cnc"
        pp_excellon_name = self.options["ppname_e"]

        # Object initialization function for app.app_obj.new_object()
        def job_init(job_obj, app_obj):
            assert job_obj.kind == 'cncjob', "Initializer expected a CNCJobObject, got %s" % type(job_obj)

            # get the tool_table items in a list of row items
            tool_table_items = self.get_selected_tools_table_items()
            # insert an information only element in the front
            tool_table_items.insert(0, [_("Tool_nr"), _("Diameter"), _("Drills_Nr"), _("Slots_Nr")])

            # ## Add properties to the object

            job_obj.origin_kind = 'excellon'

            job_obj.options['Tools_in_use'] = tool_table_items
            job_obj.options['type'] = 'Excellon'
            job_obj.options['ppname_e'] = pp_excellon_name

            job_obj.multidepth = self.options["multidepth"]
            job_obj.z_depthpercut = self.options["depthperpass"]

            job_obj.z_move = float(self.options["travelz"])
            job_obj.feedrate = float(self.options["feedrate_z"])
            job_obj.z_feedrate = float(self.options["feedrate_z"])
            job_obj.feedrate_rapid = float(self.options["feedrate_rapid"])

            job_obj.spindlespeed = float(self.options["spindlespeed"]) if self.options["spindlespeed"] != 0 else None
            job_obj.spindledir = self.app.defaults['excellon_spindledir']
            job_obj.dwell = self.options["dwell"]
            job_obj.dwelltime = float(self.options["dwelltime"])

            job_obj.pp_excellon_name = pp_excellon_name

            job_obj.toolchange_xy_type = "excellon"
            job_obj.coords_decimals = int(self.app.defaults["cncjob_coords_decimals"])
            job_obj.fr_decimals = int(self.app.defaults["cncjob_fr_decimals"])

            job_obj.options['xmin'] = xmin
            job_obj.options['ymin'] = ymin
            job_obj.options['xmax'] = xmax
            job_obj.options['ymax'] = ymax

            job_obj.z_pdepth = float(self.options["z_pdepth"])
            job_obj.feedrate_probe = float(self.options["feedrate_probe"])

            job_obj.z_cut = float(self.options['cutz'])
            job_obj.toolchange = self.options["toolchange"]
            job_obj.xy_toolchange = self.app.defaults["excellon_toolchangexy"]
            job_obj.z_toolchange = float(self.options["toolchangez"])
            job_obj.startz = float(self.options["startz"]) if self.options["startz"] else None
            job_obj.endz = float(self.options["endz"])
            job_obj.xy_end = self.options["endxy"]
            job_obj.excellon_optimization_type = self.app.defaults["excellon_optimization_type"]

            tools_csv = ','.join(tools)
            ret_val = job_obj.generate_from_excellon_by_tool(self, tools_csv, use_ui=True)

            if ret_val == 'fail':
                return 'fail'

            job_obj.gcode_parse()
            job_obj.create_geometry()

        # To be run in separate thread
        def job_thread(a_obj):
            with self.app.proc_container.new(_("Generating CNC Code")):
                a_obj.app_obj.new_object("cncjob", job_name, job_init)

        # Create promise for the new name.
        self.app.collection.promise(job_name)

        # Send to worker
        # self.app.worker.add_task(job_thread, [self.app])
        self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})

    def convert_units(self, units):
        log.debug("FlatCAMObj.ExcellonObject.convert_units()")

        Excellon.convert_units(self, units)

        # factor = Excellon.convert_units(self, units)
        # self.options['drillz'] = float(self.options['drillz']) * factor
        # self.options['travelz'] = float(self.options['travelz']) * factor
        # self.options['feedrate'] = float(self.options['feedrate']) * factor
        # self.options['feedrate_rapid'] = float(self.options['feedrate_rapid']) * factor
        # self.options['toolchangez'] = float(self.options['toolchangez']) * factor
        #
        # if self.app.defaults["excellon_toolchangexy"] == '':
        #     self.options['toolchangexy'] = "0.0, 0.0"
        # else:
        #     coords_xy = [float(eval(coord)) for coord in self.app.defaults["excellon_toolchangexy"].split(",")]
        #     if len(coords_xy) < 2:
        #         self.app.inform.emit('[ERROR] %s' % _("The Toolchange X,Y field in Edit -> Preferences has to be "
        #                                               "in the format (x, y) \n"
        #                                               "but now there is only one value, not two. "))
        #         return 'fail'
        #     coords_xy[0] *= factor
        #     coords_xy[1] *= factor
        #     self.options['toolchangexy'] = "%f, %f" % (coords_xy[0], coords_xy[1])
        #
        # if self.options['startz'] is not None:
        #     self.options['startz'] = float(self.options['startz']) * factor
        # self.options['endz'] = float(self.options['endz']) * factor

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

    def on_solid_cb_click(self, *args):
        if self.muted_ui:
            return
        self.read_form_item('solid')
        self.plot()

    def on_multicolored_cb_click(self, *args):
        if self.muted_ui:
            return
        self.read_form_item('multicolored')
        self.plot()

    def on_plot_cb_click(self, *args):
        if self.muted_ui:
            return
        self.plot()
        self.read_form_item('plot')

        self.ui_disconnect()
        cb_flag = self.ui.plot_cb.isChecked()
        for row in range(self.ui.tools_table.rowCount() - 2):
            table_cb = self.ui.tools_table.cellWidget(row, 5)
            if cb_flag:
                table_cb.setChecked(True)
            else:
                table_cb.setChecked(False)

        self.ui_connect()

    def on_plot_cb_click_table(self):
        # self.ui.cnc_tools_table.cellWidget(row, 2).widget().setCheckState(QtCore.Qt.Unchecked)
        self.ui_disconnect()
        # cw = self.sender()
        # cw_index = self.ui.tools_table.indexAt(cw.pos())
        # cw_row = cw_index.row()
        check_row = 0

        self.shapes.clear(update=True)
        for tool_key in self.tools:
            solid_geometry = self.tools[tool_key]['solid_geometry']

            # find the geo_tool_table row associated with the tool_key
            for row in range(self.ui.tools_table.rowCount()):
                tool_item = int(self.ui.tools_table.item(row, 0).text())
                if tool_item == int(tool_key):
                    check_row = row
                    break
            if self.ui.tools_table.cellWidget(check_row, 5).isChecked():
                self.options['plot'] = True
                # self.plot_element(element=solid_geometry, visible=True)
                # Plot excellon (All polygons?)
                if self.options["solid"]:
                    for geo in solid_geometry:
                        self.add_shape(shape=geo, color='#750000BF', face_color='#C40000BF',
                                       visible=self.options['plot'],
                                       layer=2)
                else:
                    for geo in solid_geometry:
                        self.add_shape(shape=geo.exterior, color='red', visible=self.options['plot'])
                        for ints in geo.interiors:
                            self.add_shape(shape=ints, color='green', visible=self.options['plot'])
        self.shapes.redraw()

        # make sure that the general plot is disabled if one of the row plot's are disabled and
        # if all the row plot's are enabled also enable the general plot checkbox
        cb_cnt = 0
        total_row = self.ui.tools_table.rowCount()
        for row in range(total_row - 2):
            if self.ui.tools_table.cellWidget(row, 5).isChecked():
                cb_cnt += 1
            else:
                cb_cnt -= 1
        if cb_cnt < total_row - 2:
            self.ui.plot_cb.setChecked(False)
        else:
            self.ui.plot_cb.setChecked(True)
        self.ui_connect()

    def plot(self, visible=None, kind=None):

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

        # try:
        #     # Plot Excellon (All polygons?)
        #     if self.options["solid"]:
        #         for tool in self.tools:
        #             for geo in self.tools[tool]['solid_geometry']:
        #                 self.add_shape(shape=geo, color='#750000BF', face_color='#C40000BF',
        #                                visible=self.options['plot'],
        #                                layer=2)
        #     else:
        #         for tool in self.tools:
        #             for geo in self.tools[tool]['solid_geometry']:
        #                 self.add_shape(shape=geo.exterior, color='red', visible=self.options['plot'])
        #                 for ints in geo.interiors:
        #                     self.add_shape(shape=ints, color='orange', visible=self.options['plot'])
        #
        #     self.shapes.redraw()
        #     return
        # except (ObjectDeleted, AttributeError, KeyError):
        #     self.shapes.clear(update=True)

        # this stays for compatibility reasons, in case we try to open old projects
        try:
            __ = iter(self.solid_geometry)
        except TypeError:
            self.solid_geometry = [self.solid_geometry]

        visible = visible if visible else self.options['plot']

        try:
            # Plot Excellon (All polygons?)
            if self.options["solid"]:
                # for geo in self.solid_geometry:
                #     self.add_shape(shape=geo,
                #                    color=self.outline_color,
                #                    face_color=random_color() if self.options['multicolored'] else self.fill_color,
                #                    visible=visible,
                #                    layer=2)

                # plot polygons for each tool separately
                for tool in self.tools:
                    # set the color here so we have one color for each tool
                    geo_color = random_color()

                    # tool is a dict also
                    for geo in self.tools[tool]["solid_geometry"]:
                        self.add_shape(shape=geo,
                                       color=geo_color if self.options['multicolored'] else self.outline_color,
                                       face_color=geo_color if self.options['multicolored'] else self.fill_color,
                                       visible=visible,
                                       layer=2)

            else:
                for geo in self.solid_geometry:
                    self.add_shape(shape=geo.exterior, color='red', visible=visible)
                    for ints in geo.interiors:
                        self.add_shape(shape=ints, color='orange', visible=visible)

            self.shapes.redraw()
        except (ObjectDeleted, AttributeError):
            self.shapes.clear(update=True)

    def on_apply_param_to_all_clicked(self):
        if self.ui.tools_table.rowCount() == 0:
            # there is no tool in tool table so we can't save the GUI elements values to storage
            log.debug("ExcellonObject.on_apply_param_to_all_clicked() --> no tool in Tools Table, aborting.")
            return

        self.ui_disconnect()

        row = self.ui.tools_table.currentRow()
        if row < 0:
            row = 0

        tooluid_item = int(self.ui.tools_table.item(row, 0).text())
        temp_tool_data = {}

        for tooluid_key, tooluid_val in self.tools.items():
            if int(tooluid_key) == tooluid_item:
                # this will hold the 'data' key of the self.tools[tool] dictionary that corresponds to
                # the current row in the tool table
                temp_tool_data = tooluid_val['data']
                break

        for tooluid_key, tooluid_val in self.tools.items():
            tooluid_val['data'] = deepcopy(temp_tool_data)

        self.app.inform.emit('[success] %s' % _("Current Tool parameters were applied to all tools."))

        self.ui_connect()
