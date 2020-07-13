from PyQt5 import QtGui, QtCore, QtWidgets
from appGUI.GUIElements import FCTable, FCEntry, FCButton, FCDoubleSpinner, FCComboBox, FCCheckBox, FCSpinner, \
    FCTree, RadioSet, FCFileSaveDialog
from camlib import to_dict

import sys
import json

from copy import deepcopy
from datetime import datetime
import math

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ToolsDB(QtWidgets.QWidget):

    mark_tools_rows = QtCore.pyqtSignal()

    def __init__(self, app, callback_on_edited, callback_on_tool_request, parent=None):
        super(ToolsDB, self).__init__(parent)

        self.app = app
        self.decimals = 4
        self.callback_app = callback_on_edited

        self.on_tool_request = callback_on_tool_request

        self.offset_item_options = ["Path", "In", "Out", "Custom"]
        self.type_item_options = ["Iso", "Rough", "Finish"]
        self.tool_type_item_options = ["C1", "C2", "C3", "C4", "B", "V"]

        '''
        dict to hold all the tools in the Tools DB
        format:
        {
            tool_id: {
                'name': 'new_tool'
                'tooldia': self.app.defaults["geometry_cnctooldia"]
                'offset': 'Path'
                'offset_value': 0.0
                'type':  _('Rough'),
                'tool_type': 'C1'
                'data': dict()
            }
        }
        '''
        self.db_tool_dict = {}

        # layouts
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        table_hlay = QtWidgets.QHBoxLayout()
        layout.addLayout(table_hlay)

        self.table_widget = FCTable(drag_drop=True)
        self.table_widget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table_hlay.addWidget(self.table_widget)

        # set the number of columns and the headers tool tips
        self.configure_table()

        # pal = QtGui.QPalette()
        # pal.setColor(QtGui.QPalette.Background, Qt.white)

        # New Bookmark
        new_vlay = QtWidgets.QVBoxLayout()
        layout.addLayout(new_vlay)

        # new_tool_lbl = QtWidgets.QLabel('<b>%s</b>' % _("New Tool"))
        # new_vlay.addWidget(new_tool_lbl, alignment=QtCore.Qt.AlignBottom)

        self.buttons_frame = QtWidgets.QFrame()
        self.buttons_frame.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.buttons_frame)
        self.buttons_box = QtWidgets.QHBoxLayout()
        self.buttons_box.setContentsMargins(0, 0, 0, 0)
        self.buttons_frame.setLayout(self.buttons_box)
        self.buttons_frame.show()

        add_entry_btn = FCButton(_("Add Geometry Tool in DB"))
        add_entry_btn.setToolTip(
            _("Add a new tool in the Tools Database.\n"
              "It will be used in the Geometry UI.\n"
              "You can edit it after it is added.")
        )
        self.buttons_box.addWidget(add_entry_btn)

        # add_fct_entry_btn = FCButton(_("Add Paint/NCC Tool in DB"))
        # add_fct_entry_btn.setToolTip(
        #     _("Add a new tool in the Tools Database.\n"
        #       "It will be used in the Paint/NCC Tools UI.\n"
        #       "You can edit it after it is added.")
        # )
        # self.buttons_box.addWidget(add_fct_entry_btn)

        remove_entry_btn = FCButton(_("Delete Tool from DB"))
        remove_entry_btn.setToolTip(
            _("Remove a selection of tools in the Tools Database.")
        )
        self.buttons_box.addWidget(remove_entry_btn)

        export_db_btn = FCButton(_("Export DB"))
        export_db_btn.setToolTip(
            _("Save the Tools Database to a custom text file.")
        )
        self.buttons_box.addWidget(export_db_btn)

        import_db_btn = FCButton(_("Import DB"))
        import_db_btn.setToolTip(
            _("Load the Tools Database information's from a custom text file.")
        )
        self.buttons_box.addWidget(import_db_btn)

        self.add_tool_from_db = FCButton(_("Transfer the Tool"))
        self.add_tool_from_db.setToolTip(
            _("Add a new tool in the Tools Table of the\n"
              "active Geometry object after selecting a tool\n"
              "in the Tools Database.")
        )
        self.add_tool_from_db.hide()

        self.cancel_tool_from_db = FCButton(_("Cancel"))
        self.cancel_tool_from_db.hide()

        hlay = QtWidgets.QHBoxLayout()
        layout.addLayout(hlay)
        hlay.addWidget(self.add_tool_from_db)
        hlay.addWidget(self.cancel_tool_from_db)
        hlay.addStretch()

        # ##############################################################################
        # ######################## SIGNALS #############################################
        # ##############################################################################

        add_entry_btn.clicked.connect(self.on_tool_add)
        remove_entry_btn.clicked.connect(self.on_tool_delete)
        export_db_btn.clicked.connect(self.on_export_tools_db_file)
        import_db_btn.clicked.connect(self.on_import_tools_db_file)
        # closebtn.clicked.connect(self.accept)

        self.add_tool_from_db.clicked.connect(self.on_tool_requested_from_app)
        self.cancel_tool_from_db.clicked.connect(self.on_cancel_tool)

        self.setup_db_ui()

    def configure_table(self):
        self.table_widget.setColumnCount(27)
        # self.table_widget.setColumnWidth(0, 20)
        self.table_widget.setHorizontalHeaderLabels(
            [
                '#',
                _("Tool Name"),
                _("Tool Dia"),
                _("Tool Offset"),
                _("Custom Offset"),
                _("Tool Type"),
                _("Tool Shape"),
                _("Cut Z"),
                _("MultiDepth"),
                _("DPP"),
                _("V-Dia"),
                _("V-Angle"),
                _("Travel Z"),
                _("FR"),
                _("FR Z"),
                _("FR Rapids"),
                _("Spindle Speed"),
                _("Dwell"),
                _("Dwelltime"),
                _("Preprocessor"),
                _("ExtraCut"),
                _("E-Cut Length"),
                _("Toolchange"),
                _("Toolchange XY"),
                _("Toolchange Z"),
                _("Start Z"),
                _("End Z"),
            ]
        )
        self.table_widget.horizontalHeaderItem(0).setToolTip(
            _("Tool Index."))
        self.table_widget.horizontalHeaderItem(1).setToolTip(
            _("Tool name.\n"
              "This is not used in the app, it's function\n"
              "is to serve as a note for the user."))
        self.table_widget.horizontalHeaderItem(2).setToolTip(
            _("Tool Diameter."))
        self.table_widget.horizontalHeaderItem(3).setToolTip(
            _("Tool Offset.\n"
              "Can be of a few types:\n"
              "Path = zero offset\n"
              "In = offset inside by half of tool diameter\n"
              "Out = offset outside by half of tool diameter\n"
              "Custom = custom offset using the Custom Offset value"))
        self.table_widget.horizontalHeaderItem(4).setToolTip(
            _("Custom Offset.\n"
              "A value to be used as offset from the current path."))
        self.table_widget.horizontalHeaderItem(5).setToolTip(
            _("Tool Type.\n"
              "Can be:\n"
              "Iso = isolation cut\n"
              "Rough = rough cut, low feedrate, multiple passes\n"
              "Finish = finishing cut, high feedrate"))
        self.table_widget.horizontalHeaderItem(6).setToolTip(
            _("Tool Shape. \n"
              "Can be:\n"
              "C1 ... C4 = circular tool with x flutes\n"
              "B = ball tip milling tool\n"
              "V = v-shape milling tool"))
        self.table_widget.horizontalHeaderItem(7).setToolTip(
            _("Cutting Depth.\n"
              "The depth at which to cut into material."))
        self.table_widget.horizontalHeaderItem(8).setToolTip(
            _("Multi Depth.\n"
              "Selecting this will allow cutting in multiple passes,\n"
              "each pass adding a DPP parameter depth."))
        self.table_widget.horizontalHeaderItem(9).setToolTip(
            _("DPP. Depth per Pass.\n"
              "The value used to cut into material on each pass."))
        self.table_widget.horizontalHeaderItem(10).setToolTip(
            _("V-Dia.\n"
              "Diameter of the tip for V-Shape Tools."))
        self.table_widget.horizontalHeaderItem(11).setToolTip(
            _("V-Agle.\n"
              "Angle at the tip for the V-Shape Tools."))
        self.table_widget.horizontalHeaderItem(12).setToolTip(
            _("Clearance Height.\n"
              "Height at which the milling bit will travel between cuts,\n"
              "above the surface of the material, avoiding all fixtures."))
        self.table_widget.horizontalHeaderItem(13).setToolTip(
            _("FR. Feedrate\n"
              "The speed on XY plane used while cutting into material."))
        self.table_widget.horizontalHeaderItem(14).setToolTip(
            _("FR Z. Feedrate Z\n"
              "The speed on Z plane."))
        self.table_widget.horizontalHeaderItem(15).setToolTip(
            _("FR Rapids. Feedrate Rapids\n"
              "Speed used while moving as fast as possible.\n"
              "This is used only by some devices that can't use\n"
              "the G0 g-code command. Mostly 3D printers."))
        self.table_widget.horizontalHeaderItem(16).setToolTip(
            _("Spindle Speed.\n"
              "If it's left empty it will not be used.\n"
              "The speed of the spindle in RPM."))
        self.table_widget.horizontalHeaderItem(17).setToolTip(
            _("Dwell.\n"
              "Check this if a delay is needed to allow\n"
              "the spindle motor to reach it's set speed."))
        self.table_widget.horizontalHeaderItem(18).setToolTip(
            _("Dwell Time.\n"
              "A delay used to allow the motor spindle reach it's set speed."))
        self.table_widget.horizontalHeaderItem(19).setToolTip(
            _("Preprocessor.\n"
              "A selection of files that will alter the generated G-code\n"
              "to fit for a number of use cases."))
        self.table_widget.horizontalHeaderItem(20).setToolTip(
            _("Extra Cut.\n"
              "If checked, after a isolation is finished an extra cut\n"
              "will be added where the start and end of isolation meet\n"
              "such as that this point is covered by this extra cut to\n"
              "ensure a complete isolation."))
        self.table_widget.horizontalHeaderItem(21).setToolTip(
            _("Extra Cut length.\n"
              "If checked, after a isolation is finished an extra cut\n"
              "will be added where the start and end of isolation meet\n"
              "such as that this point is covered by this extra cut to\n"
              "ensure a complete isolation. This is the length of\n"
              "the extra cut."))
        self.table_widget.horizontalHeaderItem(22).setToolTip(
            _("Toolchange.\n"
              "It will create a toolchange event.\n"
              "The kind of toolchange is determined by\n"
              "the preprocessor file."))
        self.table_widget.horizontalHeaderItem(23).setToolTip(
            _("Toolchange XY.\n"
              "A set of coordinates in the format (x, y).\n"
              "Will determine the cartesian position of the point\n"
              "where the tool change event take place."))
        self.table_widget.horizontalHeaderItem(24).setToolTip(
            _("Toolchange Z.\n"
              "The position on Z plane where the tool change event take place."))
        self.table_widget.horizontalHeaderItem(25).setToolTip(
            _("Start Z.\n"
              "If it's left empty it will not be used.\n"
              "A position on Z plane to move immediately after job start."))
        self.table_widget.horizontalHeaderItem(26).setToolTip(
            _("End Z.\n"
              "A position on Z plane to move immediately after job stop."))

    def setup_db_ui(self):
        filename = self.app.data_path + '/geo_tools_db.FlatDB'

        # load the database tools from the file
        try:
            with open(filename) as f:
                tools = f.read()
        except IOError:
            self.app.log.error("Could not load tools DB file.")
            self.app.inform.emit('[ERROR] %s' % _("Could not load Tools DB file."))
            return

        try:
            self.db_tool_dict = json.loads(tools)
        except Exception:
            e = sys.exc_info()[0]
            self.app.log.error(str(e))
            self.app.inform.emit('[ERROR] %s' % _("Failed to parse Tools DB file."))
            return

        self.app.inform.emit('[success] %s: %s' % (_("Loaded Tools DB from"), filename))

        self.build_db_ui()

        self.table_widget.setupContextMenu()
        self.table_widget.addContextMenu(
            _("Add to DB"), self.on_tool_add, icon=QtGui.QIcon(self.app.resource_location + "/plus16.png"))
        self.table_widget.addContextMenu(
            _("Copy from DB"), self.on_tool_copy, icon=QtGui.QIcon(self.app.resource_location + "/copy16.png"))
        self.table_widget.addContextMenu(
            _("Delete from DB"), self.on_tool_delete, icon=QtGui.QIcon(self.app.resource_location + "/delete32.png"))

    def build_db_ui(self):
        self.ui_disconnect()
        self.table_widget.setRowCount(len(self.db_tool_dict))

        nr_crt = 0

        for toolid, dict_val in self.db_tool_dict.items():
            row = nr_crt
            nr_crt += 1

            t_name = dict_val['name']
            try:
                self.add_tool_table_line(row, name=t_name, widget=self.table_widget, tooldict=dict_val)
            except Exception as e:
                self.app.log.debug("ToolDB.build_db_ui.add_tool_table_line() --> %s" % str(e))
            vertical_header = self.table_widget.verticalHeader()
            vertical_header.hide()

            horizontal_header = self.table_widget.horizontalHeader()
            horizontal_header.setMinimumSectionSize(10)
            horizontal_header.setDefaultSectionSize(70)

            self.table_widget.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
            for x in range(27):
                self.table_widget.resizeColumnToContents(x)

            horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
            # horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
            # horizontal_header.setSectionResizeMode(13, QtWidgets.QHeaderView.Fixed)

            horizontal_header.resizeSection(0, 20)
            # horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
            # horizontal_header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)

        self.ui_connect()

    def add_tool_table_line(self, row, name, widget, tooldict):
        data = tooldict['data']

        nr_crt = row + 1
        id_item = QtWidgets.QTableWidgetItem('%d' % int(nr_crt))
        # id_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        flags = id_item.flags() & ~QtCore.Qt.ItemIsEditable
        id_item.setFlags(flags)
        widget.setItem(row, 0, id_item)  # Tool name/id

        tool_name_item = QtWidgets.QTableWidgetItem(name)
        widget.setItem(row, 1, tool_name_item)

        dia_item = FCDoubleSpinner()
        dia_item.set_precision(self.decimals)
        dia_item.setSingleStep(0.1)
        dia_item.set_range(0.0, 9999.9999)
        dia_item.set_value(float(tooldict['tooldia']))
        widget.setCellWidget(row, 2, dia_item)

        tool_offset_item = FCComboBox()
        for item in self.offset_item_options:
            tool_offset_item.addItem(item)
        tool_offset_item.set_value(tooldict['offset'])
        widget.setCellWidget(row, 3, tool_offset_item)

        c_offset_item = FCDoubleSpinner()
        c_offset_item.set_precision(self.decimals)
        c_offset_item.setSingleStep(0.1)
        c_offset_item.set_range(-9999.9999, 9999.9999)
        c_offset_item.set_value(float(tooldict['offset_value']))
        widget.setCellWidget(row, 4, c_offset_item)

        tt_item = FCComboBox()
        for item in self.type_item_options:
            tt_item.addItem(item)
        tt_item.set_value(tooldict['type'])
        widget.setCellWidget(row, 5, tt_item)

        tshape_item = FCComboBox()
        for item in self.tool_type_item_options:
            tshape_item.addItem(item)
        tshape_item.set_value(tooldict['tool_type'])
        widget.setCellWidget(row, 6, tshape_item)

        cutz_item = FCDoubleSpinner()
        cutz_item.set_precision(self.decimals)
        cutz_item.setSingleStep(0.1)
        if self.app.defaults['global_machinist_setting']:
            cutz_item.set_range(-9999.9999, 9999.9999)
        else:
            cutz_item.set_range(-9999.9999, -0.0000)

        cutz_item.set_value(float(data['cutz']))
        widget.setCellWidget(row, 7, cutz_item)

        multidepth_item = FCCheckBox()
        multidepth_item.set_value(data['multidepth'])
        widget.setCellWidget(row, 8, multidepth_item)

        # to make the checkbox centered but it can no longer have it's value accessed - needs a fix using findchild()
        # multidepth_item = QtWidgets.QWidget()
        # cb = FCCheckBox()
        # cb.set_value(data['multidepth'])
        # qhboxlayout = QtWidgets.QHBoxLayout(multidepth_item)
        # qhboxlayout.addWidget(cb)
        # qhboxlayout.setAlignment(QtCore.Qt.AlignCenter)
        # qhboxlayout.setContentsMargins(0, 0, 0, 0)
        # widget.setCellWidget(row, 8, multidepth_item)

        depth_per_pass_item = FCDoubleSpinner()
        depth_per_pass_item.set_precision(self.decimals)
        depth_per_pass_item.setSingleStep(0.1)
        depth_per_pass_item.set_range(0.0, 9999.9999)
        depth_per_pass_item.set_value(float(data['depthperpass']))
        widget.setCellWidget(row, 9, depth_per_pass_item)

        vtip_dia_item = FCDoubleSpinner()
        vtip_dia_item.set_precision(self.decimals)
        vtip_dia_item.setSingleStep(0.1)
        vtip_dia_item.set_range(0.0, 9999.9999)
        vtip_dia_item.set_value(float(data['vtipdia']))
        widget.setCellWidget(row, 10, vtip_dia_item)

        vtip_angle_item = FCDoubleSpinner()
        vtip_angle_item.set_precision(self.decimals)
        vtip_angle_item.setSingleStep(0.1)
        vtip_angle_item.set_range(-360.0, 360.0)
        vtip_angle_item.set_value(float(data['vtipangle']))
        widget.setCellWidget(row, 11, vtip_angle_item)

        travelz_item = FCDoubleSpinner()
        travelz_item.set_precision(self.decimals)
        travelz_item.setSingleStep(0.1)
        if self.app.defaults['global_machinist_setting']:
            travelz_item.set_range(-9999.9999, 9999.9999)
        else:
            travelz_item.set_range(0.0000, 9999.9999)

        travelz_item.set_value(float(data['travelz']))
        widget.setCellWidget(row, 12, travelz_item)

        fr_item = FCDoubleSpinner()
        fr_item.set_precision(self.decimals)
        fr_item.set_range(0.0, 9999.9999)
        fr_item.set_value(float(data['feedrate']))
        widget.setCellWidget(row, 13, fr_item)

        frz_item = FCDoubleSpinner()
        frz_item.set_precision(self.decimals)
        frz_item.set_range(0.0, 9999.9999)
        frz_item.set_value(float(data['feedrate_z']))
        widget.setCellWidget(row, 14, frz_item)

        frrapids_item = FCDoubleSpinner()
        frrapids_item.set_precision(self.decimals)
        frrapids_item.set_range(0.0, 9999.9999)
        frrapids_item.set_value(float(data['feedrate_rapid']))
        widget.setCellWidget(row, 15, frrapids_item)

        spindlespeed_item = FCSpinner()
        spindlespeed_item.set_range(0, 1000000)
        spindlespeed_item.set_value(int(data['spindlespeed']))
        spindlespeed_item.set_step(100)
        widget.setCellWidget(row, 16, spindlespeed_item)

        dwell_item = FCCheckBox()
        dwell_item.set_value(data['dwell'])
        widget.setCellWidget(row, 17, dwell_item)

        dwelltime_item = FCDoubleSpinner()
        dwelltime_item.set_precision(self.decimals)
        dwelltime_item.set_range(0.0000, 9999.9999)
        dwelltime_item.set_value(float(data['dwelltime']))
        widget.setCellWidget(row, 18, dwelltime_item)

        pp_item = FCComboBox()
        for item in self.app.preprocessors:
            pp_item.addItem(item)
        pp_item.set_value(data['ppname_g'])
        widget.setCellWidget(row, 19, pp_item)

        ecut_item = FCCheckBox()
        ecut_item.set_value(data['extracut'])
        widget.setCellWidget(row, 20, ecut_item)

        ecut_length_item = FCDoubleSpinner()
        ecut_length_item.set_precision(self.decimals)
        ecut_length_item.set_range(0.0000, 9999.9999)
        ecut_length_item.set_value(data['extracut_length'])
        widget.setCellWidget(row, 21, ecut_length_item)

        toolchange_item = FCCheckBox()
        toolchange_item.set_value(data['toolchange'])
        widget.setCellWidget(row, 22, toolchange_item)

        toolchangexy_item = QtWidgets.QTableWidgetItem(str(data['toolchangexy']) if data['toolchangexy'] else '')
        widget.setItem(row, 23, toolchangexy_item)

        toolchangez_item = FCDoubleSpinner()
        toolchangez_item.set_precision(self.decimals)
        toolchangez_item.setSingleStep(0.1)
        if self.app.defaults['global_machinist_setting']:
            toolchangez_item.set_range(-9999.9999, 9999.9999)
        else:
            toolchangez_item.set_range(0.0000, 9999.9999)

        toolchangez_item.set_value(float(data['toolchangez']))
        widget.setCellWidget(row, 24, toolchangez_item)

        startz_item = QtWidgets.QTableWidgetItem(str(data['startz']) if data['startz'] else '')
        widget.setItem(row, 25, startz_item)

        endz_item = FCDoubleSpinner()
        endz_item.set_precision(self.decimals)
        endz_item.setSingleStep(0.1)
        if self.app.defaults['global_machinist_setting']:
            endz_item.set_range(-9999.9999, 9999.9999)
        else:
            endz_item.set_range(0.0000, 9999.9999)

        endz_item.set_value(float(data['endz']))
        widget.setCellWidget(row, 26, endz_item)

    def on_tool_add(self):
        """
        Add a tool in the DB Tool Table
        :return: None
        """

        default_data = {}
        default_data.update({
            "cutz": float(self.app.defaults["geometry_cutz"]),
            "multidepth": self.app.defaults["geometry_multidepth"],
            "depthperpass": float(self.app.defaults["geometry_depthperpass"]),
            "vtipdia": float(self.app.defaults["geometry_vtipdia"]),
            "vtipangle": float(self.app.defaults["geometry_vtipangle"]),
            "travelz": float(self.app.defaults["geometry_travelz"]),
            "feedrate": float(self.app.defaults["geometry_feedrate"]),
            "feedrate_z": float(self.app.defaults["geometry_feedrate_z"]),
            "feedrate_rapid": float(self.app.defaults["geometry_feedrate_rapid"]),
            "spindlespeed": self.app.defaults["geometry_spindlespeed"],
            "dwell": self.app.defaults["geometry_dwell"],
            "dwelltime": float(self.app.defaults["geometry_dwelltime"]),
            "ppname_g": self.app.defaults["geometry_ppname_g"],
            "extracut": self.app.defaults["geometry_extracut"],
            "extracut_length": float(self.app.defaults["geometry_extracut_length"]),
            "toolchange": self.app.defaults["geometry_toolchange"],
            "toolchangexy": self.app.defaults["geometry_toolchangexy"],
            "toolchangez": float(self.app.defaults["geometry_toolchangez"]),
            "startz": self.app.defaults["geometry_startz"],
            "endz": float(self.app.defaults["geometry_endz"])
        })

        dict_elem = {}
        dict_elem['name'] = 'new_tool'
        if type(self.app.defaults["geometry_cnctooldia"]) == float:
            dict_elem['tooldia'] = self.app.defaults["geometry_cnctooldia"]
        else:
            try:
                tools_string = self.app.defaults["geometry_cnctooldia"].split(",")
                tools_diameters = [eval(a) for a in tools_string if a != '']
                dict_elem['tooldia'] = tools_diameters[0] if tools_diameters else 0.0
            except Exception as e:
                self.app.log.debug("ToolDB.on_tool_add() --> %s" % str(e))
                return

        dict_elem['offset'] = 'Path'
        dict_elem['offset_value'] = 0.0
        dict_elem['type'] = 'Rough'
        dict_elem['tool_type'] = 'C1'
        dict_elem['data'] = default_data

        new_toolid = len(self.db_tool_dict) + 1
        self.db_tool_dict[new_toolid] = deepcopy(dict_elem)

        # add the new entry to the Tools DB table
        self.build_db_ui()
        self.callback_on_edited()
        self.app.inform.emit('[success] %s' % _("Tool added to DB."))

    def on_tool_copy(self):
        """
        Copy a selection of Tools in the Tools DB table
        :return:
        """
        new_tool_id = self.table_widget.rowCount() + 1
        for model_index in self.table_widget.selectionModel().selectedRows():
            # index = QtCore.QPersistentModelIndex(model_index)
            old_tool_id = self.table_widget.item(model_index.row(), 0).text()
            new_tool_id += 1

            for toolid, dict_val in list(self.db_tool_dict.items()):
                if int(old_tool_id) == int(toolid):
                    self.db_tool_dict.update({
                        new_tool_id: deepcopy(dict_val)
                    })

        self.build_db_ui()
        self.callback_on_edited()
        self.app.inform.emit('[success] %s' % _("Tool copied from Tools DB."))

    def on_tool_delete(self):
        """
        Delete a selection of Tools in the Tools DB table
        :return:
        """
        for model_index in self.table_widget.selectionModel().selectedRows():
            # index = QtCore.QPersistentModelIndex(model_index)
            toolname_to_remove = self.table_widget.item(model_index.row(), 0).text()

            for toolid, dict_val in list(self.db_tool_dict.items()):
                if int(toolname_to_remove) == int(toolid):
                    # remove from the storage
                    self.db_tool_dict.pop(toolid, None)

        self.build_db_ui()
        self.callback_on_edited()
        self.app.inform.emit('[success] %s' % _("Tool removed from Tools DB."))

    def on_export_tools_db_file(self):
        self.app.defaults.report_usage("on_export_tools_db_file")
        self.app.log.debug("on_export_tools_db_file()")

        date = str(datetime.today()).rpartition('.')[0]
        date = ''.join(c for c in date if c not in ':-')
        date = date.replace(' ', '_')

        filter__ = "Text File (*.TXT);;All Files (*.*)"
        filename, _f = FCFileSaveDialog.get_saved_filename(caption=_("Export Tools Database"),
                                                           directory='{l_save}/FlatCAM_{n}_{date}'.format(
                                                               l_save=str(self.app.get_last_save_folder()),
                                                               n=_("Tools_Database"),
                                                               date=date),
                                                           ext_filter=filter__)

        filename = str(filename)

        if filename == "":
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
            return
        else:
            try:
                f = open(filename, 'w')
                f.close()
            except PermissionError:
                self.app.inform.emit('[WARNING] %s' %
                                     _("Permission denied, saving not possible.\n"
                                       "Most likely another app is holding the file open and not accessible."))
                return
            except IOError:
                self.app.log.debug('Creating a new Tools DB file ...')
                f = open(filename, 'w')
                f.close()
            except Exception:
                e = sys.exc_info()[0]
                self.app.log.error("Could not load Tools DB file.")
                self.app.log.error(str(e))
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("Could not load Tools DB file."))
                return

            # Save update options
            try:
                # Save Tools DB in a file
                try:
                    with open(filename, "w") as f:
                        json.dump(self.db_tool_dict, f, default=to_dict, indent=2)
                except Exception as e:
                    self.app.log.debug("App.on_save_tools_db() --> %s" % str(e))
                    self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed to write Tools DB to file."))
                    return
            except Exception:
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed to write Tools DB to file."))
                return

        self.app.inform.emit('[success] %s: %s' % (_("Exported Tools DB to"), filename))

    def on_import_tools_db_file(self):
        self.app.defaults.report_usage("on_import_tools_db_file")
        self.app.log.debug("on_import_tools_db_file()")

        filter__ = "Text File (*.TXT);;All Files (*.*)"
        filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Import FlatCAM Tools DB"), filter=filter__)

        if filename == "":
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
        else:
            try:
                with open(filename) as f:
                    tools_in_db = f.read()
            except IOError:
                self.app.log.error("Could not load Tools DB file.")
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("Could not load Tools DB file."))
                return

            try:
                self.db_tool_dict = json.loads(tools_in_db)
            except Exception:
                e = sys.exc_info()[0]
                self.app.log.error(str(e))
                self.app.inform.emit('[ERROR] %s' % _("Failed to parse Tools DB file."))
                return

            self.app.inform.emit('[success] %s: %s' % (_("Loaded Tools DB from"), filename))
            self.build_db_ui()
            self.callback_on_edited()

    def on_save_tools_db(self, silent=False):
        self.app.log.debug("ToolsDB.on_save_button() --> Saving Tools Database to file.")

        filename = self.app.data_path + "/geo_tools_db.FlatDB"

        # Preferences save, update the color of the Tools DB Tab text
        for idx in range(self.app_ui.plot_tab_area.count()):
            if self.app_ui.plot_tab_area.tabText(idx) == _("Tools Database"):
                self.app_ui.plot_tab_area.tabBar.setTabTextColor(idx, QtGui.QColor('black'))

                # Save Tools DB in a file
                try:
                    f = open(filename, "w")
                    json.dump(self.db_tool_dict, f, default=to_dict, indent=2)
                    f.close()
                except Exception as e:
                    self.app.log.debug("ToolsDB.on_save_tools_db() --> %s" % str(e))
                    self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed to write Tools DB to file."))
                    return

                if not silent:
                    self.app.inform.emit('[success] %s' % _("Saved Tools DB."))

    def ui_connect(self):
        try:
            try:
                self.table_widget.itemChanged.disconnect(self.callback_on_edited)
            except (TypeError, AttributeError):
                pass
            self.table_widget.itemChanged.connect(self.callback_on_edited)
        except AttributeError:
            pass

        for row in range(self.table_widget.rowCount()):
            for col in range(self.table_widget.columnCount()):
                # ComboBox
                try:
                    try:
                        self.table_widget.cellWidget(row, col).currentIndexChanged.disconnect(self.callback_on_edited)
                    except (TypeError, AttributeError):
                        pass
                    self.table_widget.cellWidget(row, col).currentIndexChanged.connect(self.callback_on_edited)
                except AttributeError:
                    pass

                # CheckBox
                try:
                    try:
                        self.table_widget.cellWidget(row, col).toggled.disconnect(self.callback_on_edited)
                    except (TypeError, AttributeError):
                        pass
                    self.table_widget.cellWidget(row, col).toggled.connect(self.callback_on_edited)
                except AttributeError:
                    pass

                # SpinBox, DoubleSpinBox
                try:
                    try:
                        self.table_widget.cellWidget(row, col).valueChanged.disconnect(self.callback_on_edited)
                    except (TypeError, AttributeError):
                        pass
                    self.table_widget.cellWidget(row, col).valueChanged.connect(self.callback_on_edited)
                except AttributeError:
                    pass

    def ui_disconnect(self):
        try:
            self.table_widget.itemChanged.disconnect(self.callback_on_edited)
        except (TypeError, AttributeError):
            pass

        for row in range(self.table_widget.rowCount()):
            for col in range(self.table_widget.columnCount()):
                # ComboBox
                try:
                    self.table_widget.cellWidget(row, col).currentIndexChanged.disconnect(self.callback_on_edited)
                except (TypeError, AttributeError):
                    pass

                # CheckBox
                try:
                    self.table_widget.cellWidget(row, col).toggled.disconnect(self.callback_on_edited)
                except (TypeError, AttributeError):
                    pass

                # SpinBox, DoubleSpinBox
                try:
                    self.table_widget.cellWidget(row, col).valueChanged.disconnect(self.callback_on_edited)
                except (TypeError, AttributeError):
                    pass

    def callback_on_edited(self):

        # update the dictionary storage self.db_tool_dict
        self.db_tool_dict.clear()
        dict_elem = {}
        default_data = {}

        for row in range(self.table_widget.rowCount()):
            new_toolid = row + 1
            for col in range(self.table_widget.columnCount()):
                column_header_text = self.table_widget.horizontalHeaderItem(col).text()
                if column_header_text == _('Tool Name'):
                    dict_elem['name'] = self.table_widget.item(row, col).text()
                elif column_header_text == _('Tool Dia'):
                    dict_elem['tooldia'] = self.table_widget.cellWidget(row, col).get_value()
                elif column_header_text == _('Tool Offset'):
                    dict_elem['offset'] = self.table_widget.cellWidget(row, col).get_value()
                elif column_header_text == _('Custom Offset'):
                    dict_elem['offset_value'] = self.table_widget.cellWidget(row, col).get_value()
                elif column_header_text == _('Tool Type'):
                    dict_elem['type'] = self.table_widget.cellWidget(row, col).get_value()
                elif column_header_text == _('Tool Shape'):
                    dict_elem['tool_type'] = self.table_widget.cellWidget(row, col).get_value()
                else:
                    if column_header_text == _('Cut Z'):
                        default_data['cutz'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _('MultiDepth'):
                        default_data['multidepth'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _('DPP'):
                        default_data['depthperpass'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _('V-Dia'):
                        default_data['vtipdia'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _('V-Angle'):
                        default_data['vtipangle'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _('Travel Z'):
                        default_data['travelz'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _('FR'):
                        default_data['feedrate'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _('FR Z'):
                        default_data['feedrate_z'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _('FR Rapids'):
                        default_data['feedrate_rapid'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _('Spindle Speed'):
                        default_data['spindlespeed'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _('Dwell'):
                        default_data['dwell'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _('Dwelltime'):
                        default_data['dwelltime'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _('Preprocessor'):
                        default_data['ppname_g'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _('ExtraCut'):
                        default_data['extracut'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _("E-Cut Length"):
                        default_data['extracut_length'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _('Toolchange'):
                        default_data['toolchange'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _('Toolchange XY'):
                        default_data['toolchangexy'] = self.table_widget.item(row, col).text()
                    elif column_header_text == _('Toolchange Z'):
                        default_data['toolchangez'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _('Start Z'):
                        default_data['startz'] = float(self.table_widget.item(row, col).text()) \
                            if self.table_widget.item(row, col).text() != '' else None
                    elif column_header_text == _('End Z'):
                        default_data['endz'] = self.table_widget.cellWidget(row, col).get_value()

            dict_elem['data'] = default_data
            self.db_tool_dict.update(
                {
                    new_toolid: deepcopy(dict_elem)
                }
            )

        self.callback_app()

    def on_tool_requested_from_app(self):
        if not self.table_widget.selectionModel().selectedRows():
            self.app.inform.emit('[WARNING_NOTCL] %s...' % _("No Tool/row selected in the Tools Database table"))
            return

        model_index_list = self.table_widget.selectionModel().selectedRows()
        for model_index in model_index_list:
            selected_row = model_index.row()
            tool_uid = selected_row + 1
            for key in self.db_tool_dict.keys():
                if str(key) == str(tool_uid):
                    selected_tool = self.db_tool_dict[key]
                    self.on_tool_request(tool=selected_tool)

    def on_cancel_tool(self):
        for idx in range(self.app_ui.plot_tab_area.count()):
            if self.app_ui.plot_tab_area.tabText(idx) == _("Tools Database"):
                wdg = self.app_ui.plot_tab_area.widget(idx)
                wdg.deleteLater()
                self.app_ui.plot_tab_area.removeTab(idx)
        self.app.inform.emit('%s' % _("Cancelled adding tool from DB."))

    # def resize_new_tool_table_widget(self, min_size, max_size):
    #     """
    #     Resize the table widget responsible for adding new tool in the Tool Database
    #
    #     :param min_size: passed by rangeChanged signal or the self.new_tool_table_widget.horizontalScrollBar()
    #     :param max_size: passed by rangeChanged signal or the self.new_tool_table_widget.horizontalScrollBar()
    #     :return:
    #     """
    #     t_height = self.t_height
    #     if max_size > min_size:
    #         t_height = self.t_height + self.new_tool_table_widget.verticalScrollBar().height()
    #
    #     self.new_tool_table_widget.setMaximumHeight(t_height)

    def closeEvent(self, QCloseEvent):
        super().closeEvent(QCloseEvent)


class ToolsDB2UI:
    
    def __init__(self, app, grid_layout):
        self.app = app
        self.decimals = self.app.decimals
        
        settings = QtCore.QSettings("Open Source", "FlatCAM")
        if settings.contains("machinist"):
            self.machinist_setting = settings.value('machinist', type=int)
        else:
            self.machinist_setting = 0
        
        g_lay = grid_layout
        
        tree_layout = QtWidgets.QVBoxLayout()
        g_lay.addLayout(tree_layout, 0, 0)

        self.tree_widget = FCTree(columns=2, header_hidden=False, protected_column=[0])
        self.tree_widget.setHeaderLabels(["ID", "Tool Name"])
        self.tree_widget.setIndentation(0)
        self.tree_widget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tree_widget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        # set alternating colors
        # self.tree_widget.setAlternatingRowColors(True)
        # p = QtGui.QPalette()
        # p.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(226, 237, 253) )
        # self.tree_widget.setPalette(p)

        self.tree_widget.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        tree_layout.addWidget(self.tree_widget)

        param_hlay = QtWidgets.QHBoxLayout()
        param_area = QtWidgets.QScrollArea()
        param_widget = QtWidgets.QWidget()
        param_widget.setLayout(param_hlay)

        param_area.setWidget(param_widget)
        param_area.setWidgetResizable(True)

        g_lay.addWidget(param_area, 0, 1)

        # ###########################################################################
        # ############## The UI form ################################################
        # ###########################################################################

        # Tool description box
        self.tool_description_box = QtWidgets.QGroupBox()
        self.tool_description_box.setStyleSheet("""
        QGroupBox
        {
            font-size: 16px;
            font-weight: bold;
        }
        """)
        self.description_vlay = QtWidgets.QVBoxLayout()
        self.tool_description_box.setTitle(_("Tool Description"))
        self.tool_description_box.setFixedWidth(250)

        # Geometry Basic box
        self.basic_box = QtWidgets.QGroupBox()
        self.basic_box.setStyleSheet("""
        QGroupBox
        {
            font-size: 16px;
            font-weight: bold;
        }
        """)
        self.basic_vlay = QtWidgets.QVBoxLayout()
        self.basic_box.setTitle(_("Basic Geo Parameters"))
        self.basic_box.setFixedWidth(250)

        # Geometry Advanced box
        self.advanced_box = QtWidgets.QGroupBox()
        self.advanced_box.setStyleSheet("""
                QGroupBox
                {
                    font-size: 16px;
                    font-weight: bold;
                }
                """)
        self.advanced_vlay = QtWidgets.QVBoxLayout()
        self.advanced_box.setTitle(_("Advanced Geo Parameters"))
        self.advanced_box.setFixedWidth(250)

        # NCC TOOL BOX
        self.ncc_box = QtWidgets.QGroupBox()
        self.ncc_box.setStyleSheet("""
                        QGroupBox
                        {
                            font-size: 16px;
                            font-weight: bold;
                        }
                        """)
        self.ncc_vlay = QtWidgets.QVBoxLayout()
        self.ncc_box.setTitle(_("NCC Parameters"))
        self.ncc_box.setFixedWidth(250)

        # PAINT TOOL BOX
        self.paint_box = QtWidgets.QGroupBox()
        self.paint_box.setStyleSheet("""
                        QGroupBox
                        {
                            font-size: 16px;
                            font-weight: bold;
                        }
                        """)
        self.paint_vlay = QtWidgets.QVBoxLayout()
        self.paint_box.setTitle(_("Paint Parameters"))
        self.paint_box.setFixedWidth(250)

        # ISOLATION TOOL BOX
        self.iso_box = QtWidgets.QGroupBox()
        self.iso_box.setStyleSheet("""
                     QGroupBox
                     {
                         font-size: 16px;
                         font-weight: bold;
                     }
                     """)
        self.iso_vlay = QtWidgets.QVBoxLayout()
        self.iso_box.setTitle(_("Isolation Parameters"))
        self.iso_box.setFixedWidth(250)

        # DRILLING TOOL BOX
        self.drill_box = QtWidgets.QGroupBox()
        self.drill_box.setStyleSheet("""
                     QGroupBox
                     {
                         font-size: 16px;
                         font-weight: bold;
                     }
                     """)
        self.drill_vlay = QtWidgets.QVBoxLayout()
        self.drill_box.setTitle(_("Drilling Parameters"))
        self.drill_box.setFixedWidth(250)

        # Layout Constructor
        self.tool_description_box.setLayout(self.description_vlay)
        self.basic_box.setLayout(self.basic_vlay)
        self.advanced_box.setLayout(self.advanced_vlay)
        self.ncc_box.setLayout(self.ncc_vlay)
        self.paint_box.setLayout(self.paint_vlay)
        self.iso_box.setLayout(self.iso_vlay)
        self.drill_box.setLayout(self.drill_vlay)

        geo_vlay = QtWidgets.QVBoxLayout()
        geo_vlay.addWidget(self.tool_description_box)
        geo_vlay.addWidget(self.basic_box)
        geo_vlay.addWidget(self.advanced_box)
        geo_vlay.addStretch()

        tools_vlay = QtWidgets.QVBoxLayout()
        tools_vlay.addWidget(self.ncc_box)
        tools_vlay.addWidget(self.paint_box)
        tools_vlay.addWidget(self.iso_box)
        tools_vlay.addWidget(self.drill_box)
        tools_vlay.addStretch()

        param_hlay.addLayout(geo_vlay)
        param_hlay.addLayout(tools_vlay)
        param_hlay.addStretch()

        # ###########################################################################
        # ################ Tool UI form #############################################
        # ###########################################################################
        self.grid_tool = QtWidgets.QGridLayout()
        self.description_vlay.addLayout(self.grid_tool)
        self.grid_tool.setColumnStretch(0, 0)
        self.grid_tool.setColumnStretch(1, 1)
        self.description_vlay.addStretch()

        # Tool Name
        self.name_label = QtWidgets.QLabel('<span style="color:red;"><b>%s:</b></span>' % _('Tool Name'))
        self.name_label.setToolTip(
            _("Tool name.\n"
              "This is not used in the app, it's function\n"
              "is to serve as a note for the user."))

        self.name_entry = FCEntry()
        self.name_entry.setObjectName('gdb_name')

        self.grid_tool.addWidget(self.name_label, 0, 0)
        self.grid_tool.addWidget(self.name_entry, 0, 1)

        # Tool Dia
        self.dia_label = QtWidgets.QLabel('%s:' % _('Tool Dia'))
        self.dia_label.setToolTip(
            _("Tool Diameter."))

        self.dia_entry = FCDoubleSpinner()
        self.dia_entry.set_range(-9999.9999, 9999.9999)
        self.dia_entry.set_precision(self.decimals)
        self.dia_entry.setObjectName('gdb_dia')

        self.grid_tool.addWidget(self.dia_label, 1, 0)
        self.grid_tool.addWidget(self.dia_entry, 1, 1)

        # Tool Object Type
        self.tool_object_label = QtWidgets.QLabel('<b>%s:</b>' % _('Object Type'))
        self.tool_object_label.setToolTip(
            _("The kind of application object where the tool is to be used."))

        self.object_type_combo = FCComboBox()
        self.object_type_combo.addItems([_("General"), _("Milling"), _("Drilling")])
        self.object_type_combo.setObjectName('gdb_object_type')

        self.grid_tool.addWidget(self.tool_object_label, 2, 0)
        self.grid_tool.addWidget(self.object_type_combo, 2, 1)

        # Tool Tolerance
        self.tol_label = QtWidgets.QLabel("<b>%s:</b>" % _("Tolerance"))
        self.tol_label.setToolTip(
            _("Tool tolerance. If there is a tool in the Excellon object with\n"
              "the value within the limits then this tool from DB will be used.\n"
              "This behavior is enabled in the Drilling Tool.")
        )
        self.grid_tool.addWidget(self.tol_label, 4, 0, 1, 2)

        # Tolerance Min Limit
        self.min_limit_label = QtWidgets.QLabel('%s:' % _("Min"))
        self.min_limit_label.setToolTip(
            _("Set the tool tolerance minimum.")
        )
        self.tol_min_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.tol_min_entry.set_precision(self.decimals)
        self.tol_min_entry.set_range(0, 9999.9999)
        self.tol_min_entry.setSingleStep(0.1)
        self.tol_min_entry.setObjectName("gdb_tol_min")

        self.grid_tool.addWidget(self.min_limit_label, 6, 0)
        self.grid_tool.addWidget(self.tol_min_entry, 6, 1)

        # Tolerance Min Limit
        self.max_limit_label = QtWidgets.QLabel('%s:' % _("Max"))
        self.max_limit_label.setToolTip(
            _("Set the tool tolerance maximum.")
        )
        self.tol_max_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.tol_max_entry.set_precision(self.decimals)
        self.tol_max_entry.set_range(0, 9999.9999)
        self.tol_max_entry.setSingleStep(0.1)
        self.tol_max_entry.setObjectName("gdb_tol_max")

        self.grid_tool.addWidget(self.max_limit_label, 7, 0)
        self.grid_tool.addWidget(self.tol_max_entry, 7, 1)

        # ###########################################################################
        # ############### BASIC GEOMETRY UI form ####################################
        # ###########################################################################
        self.grid0 = QtWidgets.QGridLayout()
        self.basic_vlay.addLayout(self.grid0)
        self.grid0.setColumnStretch(0, 0)
        self.grid0.setColumnStretch(1, 1)
        self.basic_vlay.addStretch()

        # Tool Shape
        self.shape_label = QtWidgets.QLabel('%s:' % _('Tool Shape'))
        self.shape_label.setToolTip(
            _("Tool Shape. \n"
              "Can be:\n"
              "C1 ... C4 = circular tool with x flutes\n"
              "B = ball tip milling tool\n"
              "V = v-shape milling tool"))

        self.shape_combo = FCComboBox()
        self.shape_combo.addItems(["C1", "C2", "C3", "C4", "B", "V"])
        self.shape_combo.setObjectName('gdb_shape')

        self.grid0.addWidget(self.shape_label, 2, 0)
        self.grid0.addWidget(self.shape_combo, 2, 1)

        # Cut Z
        self.cutz_label = QtWidgets.QLabel('%s:' % _("Cut Z"))
        self.cutz_label.setToolTip(
            _("Cutting Depth.\n"
              "The depth at which to cut into material."))

        self.cutz_entry = FCDoubleSpinner()
        self.cutz_entry.set_range(-9999.9999, 9999.9999)
        self.cutz_entry.set_precision(self.decimals)
        self.cutz_entry.setObjectName('gdb_cutz')

        self.grid0.addWidget(self.cutz_label, 4, 0)
        self.grid0.addWidget(self.cutz_entry, 4, 1)

        # Multi Depth
        self.multidepth_label = QtWidgets.QLabel('%s:' % _("MultiDepth"))
        self.multidepth_label.setToolTip(
            _("Multi Depth.\n"
              "Selecting this will allow cutting in multiple passes,\n"
              "each pass adding a DPP parameter depth."))

        self.multidepth_cb = FCCheckBox()
        self.multidepth_cb.setObjectName('gdb_multidepth')

        self.grid0.addWidget(self.multidepth_label, 5, 0)
        self.grid0.addWidget(self.multidepth_cb, 5, 1)

        # Depth Per Pass
        self.dpp_label = QtWidgets.QLabel('%s:' % _("DPP"))
        self.dpp_label.setToolTip(
            _("DPP. Depth per Pass.\n"
              "The value used to cut into material on each pass."))

        self.multidepth_entry = FCDoubleSpinner()
        self.multidepth_entry.set_range(-9999.9999, 9999.9999)
        self.multidepth_entry.set_precision(self.decimals)
        self.multidepth_entry.setObjectName('gdb_multidepth_entry')

        self.grid0.addWidget(self.dpp_label, 7, 0)
        self.grid0.addWidget(self.multidepth_entry, 7, 1)

        # Travel Z
        self.travelz_label = QtWidgets.QLabel('%s:' % _("Travel Z"))
        self.travelz_label.setToolTip(
            _("Clearance Height.\n"
              "Height at which the milling bit will travel between cuts,\n"
              "above the surface of the material, avoiding all fixtures."))

        self.travelz_entry = FCDoubleSpinner()
        self.travelz_entry.set_range(-9999.9999, 9999.9999)
        self.travelz_entry.set_precision(self.decimals)
        self.travelz_entry.setObjectName('gdb_travel')

        self.grid0.addWidget(self.travelz_label, 9, 0)
        self.grid0.addWidget(self.travelz_entry, 9, 1)

        # Feedrate X-Y
        self.frxy_label = QtWidgets.QLabel('%s:' % _("Feedrate X-Y"))
        self.frxy_label.setToolTip(
            _("Feedrate X-Y. Feedrate\n"
              "The speed on XY plane used while cutting into material."))

        self.frxy_entry = FCDoubleSpinner()
        self.frxy_entry.set_range(-999999.9999, 999999.9999)
        self.frxy_entry.set_precision(self.decimals)
        self.frxy_entry.setObjectName('gdb_frxy')

        self.grid0.addWidget(self.frxy_label, 12, 0)
        self.grid0.addWidget(self.frxy_entry, 12, 1)

        # Feedrate Z
        self.frz_label = QtWidgets.QLabel('%s:' % _("Feedrate Z"))
        self.frz_label.setToolTip(
            _("Feedrate Z\n"
              "The speed on Z plane."))

        self.frz_entry = FCDoubleSpinner()
        self.frz_entry.set_range(-999999.9999, 999999.9999)
        self.frz_entry.set_precision(self.decimals)
        self.frz_entry.setObjectName('gdb_frz')

        self.grid0.addWidget(self.frz_label, 14, 0)
        self.grid0.addWidget(self.frz_entry, 14, 1)

        # Spindle Spped
        self.spindle_label = QtWidgets.QLabel('%s:' % _("Spindle Speed"))
        self.spindle_label.setToolTip(
            _("Spindle Speed.\n"
              "If it's left empty it will not be used.\n"
              "The speed of the spindle in RPM."))

        self.spindle_entry = FCDoubleSpinner()
        self.spindle_entry.set_range(-999999.9999, 999999.9999)
        self.spindle_entry.set_precision(self.decimals)
        self.spindle_entry.setObjectName('gdb_spindle')

        self.grid0.addWidget(self.spindle_label, 15, 0)
        self.grid0.addWidget(self.spindle_entry, 15, 1)

        # Dwell
        self.dwell_label = QtWidgets.QLabel('%s:' % _("Dwell"))
        self.dwell_label.setToolTip(
            _("Dwell.\n"
              "Check this if a delay is needed to allow\n"
              "the spindle motor to reach it's set speed."))

        self.dwell_cb = FCCheckBox()
        self.dwell_cb.setObjectName('gdb_dwell')

        self.grid0.addWidget(self.dwell_label, 16, 0)
        self.grid0.addWidget(self.dwell_cb, 16, 1)

        # Dwell Time
        self.dwelltime_label = QtWidgets.QLabel('%s:' % _("Dwelltime"))
        self.dwelltime_label.setToolTip(
            _("Dwell Time.\n"
              "A delay used to allow the motor spindle reach it's set speed."))

        self.dwelltime_entry = FCDoubleSpinner()
        self.dwelltime_entry.set_range(0.0000, 9999.9999)
        self.dwelltime_entry.set_precision(self.decimals)
        self.dwelltime_entry.setObjectName('gdb_dwelltime')

        self.grid0.addWidget(self.dwelltime_label, 17, 0)
        self.grid0.addWidget(self.dwelltime_entry, 17, 1)

        # ###########################################################################
        # ############### ADVANCED GEOMETRY UI form #################################
        # ###########################################################################

        self.grid1 = QtWidgets.QGridLayout()
        self.advanced_vlay.addLayout(self.grid1)
        self.grid1.setColumnStretch(0, 0)
        self.grid1.setColumnStretch(1, 1)
        self.advanced_vlay.addStretch()

        # Tool Type
        self.type_label = QtWidgets.QLabel('%s:' % _("Tool Type"))
        self.type_label.setToolTip(
            _("Tool Type.\n"
              "Can be:\n"
              "Iso = isolation cut\n"
              "Rough = rough cut, low feedrate, multiple passes\n"
              "Finish = finishing cut, high feedrate"))

        self.type_combo = FCComboBox()
        self.type_combo.addItems(["Iso", "Rough", "Finish"])
        self.type_combo.setObjectName('gdb_type')

        self.grid1.addWidget(self.type_label, 0, 0)
        self.grid1.addWidget(self.type_combo, 0, 1)

        # Tool Offset
        self.tooloffset_label = QtWidgets.QLabel('%s:' % _('Tool Offset'))
        self.tooloffset_label.setToolTip(
            _("Tool Offset.\n"
              "Can be of a few types:\n"
              "Path = zero offset\n"
              "In = offset inside by half of tool diameter\n"
              "Out = offset outside by half of tool diameter\n"
              "Custom = custom offset using the Custom Offset value"))

        self.tooloffset_combo = FCComboBox()
        self.tooloffset_combo.addItems(["Path", "In", "Out", "Custom"])
        self.tooloffset_combo.setObjectName('gdb_tool_offset')

        self.grid1.addWidget(self.tooloffset_label, 2, 0)
        self.grid1.addWidget(self.tooloffset_combo, 2, 1)

        # Custom Offset
        self.custom_offset_label = QtWidgets.QLabel('%s:' % _("Custom Offset"))
        self.custom_offset_label.setToolTip(
            _("Custom Offset.\n"
              "A value to be used as offset from the current path."))

        self.custom_offset_entry = FCDoubleSpinner()
        self.custom_offset_entry.set_range(-9999.9999, 9999.9999)
        self.custom_offset_entry.set_precision(self.decimals)
        self.custom_offset_entry.setObjectName('gdb_custom_offset')

        self.grid1.addWidget(self.custom_offset_label, 5, 0)
        self.grid1.addWidget(self.custom_offset_entry, 5, 1)

        # V-Dia
        self.vdia_label = QtWidgets.QLabel('%s:' % _("V-Dia"))
        self.vdia_label.setToolTip(
            _("V-Dia.\n"
              "Diameter of the tip for V-Shape Tools."))

        self.vdia_entry = FCDoubleSpinner()
        self.vdia_entry.set_range(0.0000, 9999.9999)
        self.vdia_entry.set_precision(self.decimals)
        self.vdia_entry.setObjectName('gdb_vdia')

        self.grid1.addWidget(self.vdia_label, 7, 0)
        self.grid1.addWidget(self.vdia_entry, 7, 1)

        # V-Angle
        self.vangle_label = QtWidgets.QLabel('%s:' % _("V-Angle"))
        self.vangle_label.setToolTip(
            _("V-Agle.\n"
              "Angle at the tip for the V-Shape Tools."))

        self.vangle_entry = FCDoubleSpinner()
        self.vangle_entry.set_range(-360.0, 360.0)
        self.vangle_entry.set_precision(self.decimals)
        self.vangle_entry.setObjectName('gdb_vangle')

        self.grid1.addWidget(self.vangle_label, 8, 0)
        self.grid1.addWidget(self.vangle_entry, 8, 1)

        # Feedrate Rapids
        self.frapids_label = QtWidgets.QLabel('%s:' % _("FR Rapids"))
        self.frapids_label.setToolTip(
            _("FR Rapids. Feedrate Rapids\n"
              "Speed used while moving as fast as possible.\n"
              "This is used only by some devices that can't use\n"
              "the G0 g-code command. Mostly 3D printers."))

        self.frapids_entry = FCDoubleSpinner()
        self.frapids_entry.set_range(0.0000, 9999.9999)
        self.frapids_entry.set_precision(self.decimals)
        self.frapids_entry.setObjectName('gdb_frapids')

        self.grid1.addWidget(self.frapids_label, 10, 0)
        self.grid1.addWidget(self.frapids_entry, 10, 1)

        # Extra Cut
        self.ecut_label = QtWidgets.QLabel('%s:' % _("ExtraCut"))
        self.ecut_label.setToolTip(
            _("Extra Cut.\n"
              "If checked, after a isolation is finished an extra cut\n"
              "will be added where the start and end of isolation meet\n"
              "such as that this point is covered by this extra cut to\n"
              "ensure a complete isolation."))

        self.ecut_cb = FCCheckBox()
        self.ecut_cb.setObjectName('gdb_ecut')

        self.grid1.addWidget(self.ecut_label, 12, 0)
        self.grid1.addWidget(self.ecut_cb, 12, 1)

        # Extra Cut Length
        self.ecut_length_label = QtWidgets.QLabel('%s:' % _("E-Cut Length"))
        self.ecut_length_label.setToolTip(
            _("Extra Cut length.\n"
              "If checked, after a isolation is finished an extra cut\n"
              "will be added where the start and end of isolation meet\n"
              "such as that this point is covered by this extra cut to\n"
              "ensure a complete isolation. This is the length of\n"
              "the extra cut."))

        self.ecut_length_entry = FCDoubleSpinner()
        self.ecut_length_entry.set_range(0.0000, 9999.9999)
        self.ecut_length_entry.set_precision(self.decimals)
        self.ecut_length_entry.setObjectName('gdb_ecut_length')

        self.grid1.addWidget(self.ecut_length_label, 13, 0)
        self.grid1.addWidget(self.ecut_length_entry, 13, 1)

        # ###########################################################################
        # ############### NCC UI form ###############################################
        # ###########################################################################

        self.grid2 = QtWidgets.QGridLayout()
        self.ncc_vlay.addLayout(self.grid2)
        self.grid2.setColumnStretch(0, 0)
        self.grid2.setColumnStretch(1, 1)
        self.ncc_vlay.addStretch()

        # Operation
        op_label = QtWidgets.QLabel('%s:' % _('Operation'))
        op_label.setToolTip(
            _("The 'Operation' can be:\n"
              "- Isolation -> will ensure that the non-copper clearing is always complete.\n"
              "If it's not successful then the non-copper clearing will fail, too.\n"
              "- Clear -> the regular non-copper clearing.")
        )

        self.op_radio = RadioSet([
            {"label": _("Clear"), "value": "clear"},
            {"label": _("Isolation"), "value": "iso"}
        ], orientation='horizontal', stretch=False)
        self.op_radio.setObjectName("gdb_n_operation")

        self.grid2.addWidget(op_label, 13, 0)
        self.grid2.addWidget(self.op_radio, 13, 1)

        # Milling Type Radio Button
        self.milling_type_label = QtWidgets.QLabel('%s:' % _('Milling Type'))
        self.milling_type_label.setToolTip(
            _("Milling type when the selected tool is of type: 'iso_op':\n"
              "- climb / best for precision milling and to reduce tool usage\n"
              "- conventional / useful when there is no backlash compensation")
        )

        self.milling_type_radio = RadioSet([{'label': _('Climb'), 'value': 'cl'},
                                            {'label': _('Conventional'), 'value': 'cv'}])
        self.milling_type_radio.setToolTip(
            _("Milling type when the selected tool is of type: 'iso_op':\n"
              "- climb / best for precision milling and to reduce tool usage\n"
              "- conventional / useful when there is no backlash compensation")
        )
        self.milling_type_radio.setObjectName("gdb_n_milling_type")

        self.grid2.addWidget(self.milling_type_label, 14, 0)
        self.grid2.addWidget(self.milling_type_radio, 14, 1)

        # Overlap Entry
        nccoverlabel = QtWidgets.QLabel('%s:' % _('Overlap'))
        nccoverlabel.setToolTip(
            _("How much (percentage) of the tool width to overlap each tool pass.\n"
              "Adjust the value starting with lower values\n"
              "and increasing it if areas that should be cleared are still \n"
              "not cleared.\n"
              "Lower values = faster processing, faster execution on CNC.\n"
              "Higher values = slow processing and slow execution on CNC\n"
              "due of too many paths.")
        )
        self.ncc_overlap_entry = FCDoubleSpinner(suffix='%')
        self.ncc_overlap_entry.set_precision(self.decimals)
        self.ncc_overlap_entry.setWrapping(True)
        self.ncc_overlap_entry.setRange(0.000, 99.9999)
        self.ncc_overlap_entry.setSingleStep(0.1)
        self.ncc_overlap_entry.setObjectName("gdb_n_overlap")

        self.grid2.addWidget(nccoverlabel, 15, 0)
        self.grid2.addWidget(self.ncc_overlap_entry, 15, 1)

        # Margin
        nccmarginlabel = QtWidgets.QLabel('%s:' % _('Margin'))
        nccmarginlabel.setToolTip(
            _("Bounding box margin.")
        )
        self.ncc_margin_entry = FCDoubleSpinner()
        self.ncc_margin_entry.set_precision(self.decimals)
        self.ncc_margin_entry.set_range(-9999.9999, 9999.9999)
        self.ncc_margin_entry.setObjectName("gdb_n_margin")

        self.grid2.addWidget(nccmarginlabel, 16, 0)
        self.grid2.addWidget(self.ncc_margin_entry, 16, 1)

        # Method
        methodlabel = QtWidgets.QLabel('%s:' % _('Method'))
        methodlabel.setToolTip(
            _("Algorithm for copper clearing:\n"
              "- Standard: Fixed step inwards.\n"
              "- Seed-based: Outwards from seed.\n"
              "- Line-based: Parallel lines.")
        )

        self.ncc_method_combo = FCComboBox()
        self.ncc_method_combo.addItems(
            [_("Standard"), _("Seed"), _("Lines"), _("Combo")]
        )
        self.ncc_method_combo.setObjectName("gdb_n_method")

        self.grid2.addWidget(methodlabel, 17, 0)
        self.grid2.addWidget(self.ncc_method_combo, 17, 1)

        # Connect lines
        self.ncc_connect_cb = FCCheckBox('%s' % _("Connect"))
        self.ncc_connect_cb.setObjectName("gdb_n_connect")

        self.ncc_connect_cb.setToolTip(
            _("Draw lines between resulting\n"
              "segments to minimize tool lifts.")
        )
        self.grid2.addWidget(self.ncc_connect_cb, 18, 0)

        # Contour
        self.ncc_contour_cb = FCCheckBox('%s' % _("Contour"))
        self.ncc_contour_cb.setObjectName("gdb_n_contour")

        self.ncc_contour_cb.setToolTip(
            _("Cut around the perimeter of the polygon\n"
              "to trim rough edges.")
        )
        self.grid2.addWidget(self.ncc_contour_cb, 18, 1)

        # ## NCC Offset choice
        self.ncc_choice_offset_cb = FCCheckBox('%s' % _("Offset"))
        self.ncc_choice_offset_cb.setObjectName("gdb_n_offset")

        self.ncc_choice_offset_cb.setToolTip(
            _("If used, it will add an offset to the copper features.\n"
              "The copper clearing will finish to a distance\n"
              "from the copper features.\n"
              "The value can be between 0 and 10 FlatCAM units.")
        )
        self.grid2.addWidget(self.ncc_choice_offset_cb, 19, 0)

        # ## NCC Offset Entry
        self.ncc_offset_spinner = FCDoubleSpinner()
        self.ncc_offset_spinner.set_range(0.00, 10.00)
        self.ncc_offset_spinner.set_precision(4)
        self.ncc_offset_spinner.setWrapping(True)
        self.ncc_offset_spinner.setObjectName("gdb_n_offset_value")

        units = self.app.defaults['units'].upper()
        if units == 'MM':
            self.ncc_offset_spinner.setSingleStep(0.1)
        else:
            self.ncc_offset_spinner.setSingleStep(0.01)

        self.grid2.addWidget(self.ncc_offset_spinner, 19, 1)

        # ###########################################################################
        # ############### Paint UI form #############################################
        # ###########################################################################

        self.grid3 = QtWidgets.QGridLayout()
        self.paint_vlay.addLayout(self.grid3)
        self.grid3.setColumnStretch(0, 0)
        self.grid3.setColumnStretch(1, 1)
        self.paint_vlay.addStretch()

        # Overlap
        ovlabel = QtWidgets.QLabel('%s:' % _('Overlap'))
        ovlabel.setToolTip(
            _("How much (percentage) of the tool width to overlap each tool pass.\n"
              "Adjust the value starting with lower values\n"
              "and increasing it if areas that should be painted are still \n"
              "not painted.\n"
              "Lower values = faster processing, faster execution on CNC.\n"
              "Higher values = slow processing and slow execution on CNC\n"
              "due of too many paths.")
        )
        self.paintoverlap_entry = FCDoubleSpinner(suffix='%')
        self.paintoverlap_entry.set_precision(3)
        self.paintoverlap_entry.setWrapping(True)
        self.paintoverlap_entry.setRange(0.0000, 99.9999)
        self.paintoverlap_entry.setSingleStep(0.1)
        self.paintoverlap_entry.setObjectName('gdb_p_overlap')

        self.grid3.addWidget(ovlabel, 1, 0)
        self.grid3.addWidget(self.paintoverlap_entry, 1, 1)

        # Margin
        marginlabel = QtWidgets.QLabel('%s:' % _('Offset'))
        marginlabel.setToolTip(
            _("Distance by which to avoid\n"
              "the edges of the polygon to\n"
              "be painted.")
        )
        self.paint_offset_entry = FCDoubleSpinner()
        self.paint_offset_entry.set_precision(self.decimals)
        self.paint_offset_entry.set_range(-9999.9999, 9999.9999)
        self.paint_offset_entry.setObjectName('gdb_p_offset')

        self.grid3.addWidget(marginlabel, 2, 0)
        self.grid3.addWidget(self.paint_offset_entry, 2, 1)

        # Method
        methodlabel = QtWidgets.QLabel('%s:' % _('Method'))
        methodlabel.setToolTip(
            _("Algorithm for painting:\n"
              "- Standard: Fixed step inwards.\n"
              "- Seed-based: Outwards from seed.\n"
              "- Line-based: Parallel lines.\n"
              "- Laser-lines: Active only for Gerber objects.\n"
              "Will create lines that follow the traces.\n"
              "- Combo: In case of failure a new method will be picked from the above\n"
              "in the order specified.")
        )

        self.paintmethod_combo = FCComboBox()
        self.paintmethod_combo.addItems(
            [_("Standard"), _("Seed"), _("Lines"), _("Laser_lines"), _("Combo")]
        )
        idx = self.paintmethod_combo.findText(_("Laser_lines"))
        self.paintmethod_combo.model().item(idx).setEnabled(False)

        self.paintmethod_combo.setObjectName('gdb_p_method')

        self.grid3.addWidget(methodlabel, 7, 0)
        self.grid3.addWidget(self.paintmethod_combo, 7, 1)

        # Connect lines
        self.pathconnect_cb = FCCheckBox('%s' % _("Connect"))
        self.pathconnect_cb.setObjectName('gdb_p_connect')
        self.pathconnect_cb.setToolTip(
            _("Draw lines between resulting\n"
              "segments to minimize tool lifts.")
        )

        self.paintcontour_cb = FCCheckBox('%s' % _("Contour"))
        self.paintcontour_cb.setObjectName('gdb_p_contour')
        self.paintcontour_cb.setToolTip(
            _("Cut around the perimeter of the polygon\n"
              "to trim rough edges.")
        )

        self.grid3.addWidget(self.pathconnect_cb, 10, 0)
        self.grid3.addWidget(self.paintcontour_cb, 10, 1)

        # ###########################################################################
        # ############### Isolation UI form #########################################
        # ###########################################################################

        self.grid4 = QtWidgets.QGridLayout()
        self.iso_vlay.addLayout(self.grid4)
        self.grid4.setColumnStretch(0, 0)
        self.grid4.setColumnStretch(1, 1)
        self.iso_vlay.addStretch()

        # Passes
        passlabel = QtWidgets.QLabel('%s:' % _('Passes'))
        passlabel.setToolTip(
            _("Width of the isolation gap in\n"
              "number (integer) of tool widths.")
        )
        self.passes_entry = FCSpinner()
        self.passes_entry.set_range(1, 999)
        self.passes_entry.setObjectName("gdb_i_passes")

        self.grid4.addWidget(passlabel, 0, 0)
        self.grid4.addWidget(self.passes_entry, 0, 1)

        # Overlap Entry
        overlabel = QtWidgets.QLabel('%s:' % _('Overlap'))
        overlabel.setToolTip(
            _("How much (percentage) of the tool width to overlap each tool pass.")
        )
        self.iso_overlap_entry = FCDoubleSpinner(suffix='%')
        self.iso_overlap_entry.set_precision(self.decimals)
        self.iso_overlap_entry.setWrapping(True)
        self.iso_overlap_entry.set_range(0.0000, 99.9999)
        self.iso_overlap_entry.setSingleStep(0.1)
        self.iso_overlap_entry.setObjectName("gdb_i_overlap")

        self.grid4.addWidget(overlabel, 2, 0)
        self.grid4.addWidget(self.iso_overlap_entry, 2, 1)

        # Milling Type Radio Button
        self.milling_type_label = QtWidgets.QLabel('%s:' % _('Milling Type'))
        self.milling_type_label.setToolTip(
            _("Milling type when the selected tool is of type: 'iso_op':\n"
              "- climb / best for precision milling and to reduce tool usage\n"
              "- conventional / useful when there is no backlash compensation")
        )

        self.milling_type_radio = RadioSet([{'label': _('Climb'), 'value': 'cl'},
                                            {'label': _('Conventional'), 'value': 'cv'}])
        self.milling_type_radio.setToolTip(
            _("Milling type when the selected tool is of type: 'iso_op':\n"
              "- climb / best for precision milling and to reduce tool usage\n"
              "- conventional / useful when there is no backlash compensation")
        )
        self.milling_type_radio.setObjectName("gdb_i_milling_type")

        self.grid4.addWidget(self.milling_type_label, 4, 0)
        self.grid4.addWidget(self.milling_type_radio, 4, 1)

        # Follow
        self.follow_label = QtWidgets.QLabel('%s:' % _('Follow'))
        self.follow_label.setToolTip(
            _("Generate a 'Follow' geometry.\n"
              "This means that it will cut through\n"
              "the middle of the trace.")
        )

        self.follow_cb = FCCheckBox()
        self.follow_cb.setToolTip(_("Generate a 'Follow' geometry.\n"
                                    "This means that it will cut through\n"
                                    "the middle of the trace."))
        self.follow_cb.setObjectName("gdb_i_follow")

        self.grid4.addWidget(self.follow_label, 6, 0)
        self.grid4.addWidget(self.follow_cb, 6, 1)

        # Isolation Type
        self.iso_type_label = QtWidgets.QLabel('%s:' % _('Isolation Type'))
        self.iso_type_label.setToolTip(
            _("Choose how the isolation will be executed:\n"
              "- 'Full' -> complete isolation of polygons\n"
              "- 'Ext' -> will isolate only on the outside\n"
              "- 'Int' -> will isolate only on the inside\n"
              "'Exterior' isolation is almost always possible\n"
              "(with the right tool) but 'Interior'\n"
              "isolation can be done only when there is an opening\n"
              "inside of the polygon (e.g polygon is a 'doughnut' shape).")
        )
        self.iso_type_radio = RadioSet([{'label': _('Full'), 'value': 'full'},
                                        {'label': _('Ext'), 'value': 'ext'},
                                        {'label': _('Int'), 'value': 'int'}])
        self.iso_type_radio.setObjectName("gdb_i_iso_type")

        self.grid4.addWidget(self.iso_type_label, 8, 0)
        self.grid4.addWidget(self.iso_type_radio, 8, 1)


        # ###########################################################################
        # ################ DRILLING UI form #########################################
        # ###########################################################################
        self.grid5 = QtWidgets.QGridLayout()
        self.drill_vlay.addLayout(self.grid5)
        self.grid5.setColumnStretch(0, 0)
        self.grid5.setColumnStretch(1, 1)
        self.drill_vlay.addStretch()

        # Cut Z
        self.cutzlabel = QtWidgets.QLabel('%s:' % _('Cut Z'))
        self.cutzlabel.setToolTip(
            _("Drill depth (negative)\n"
              "below the copper surface.")
        )

        self.cutz_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.cutz_entry.set_precision(self.decimals)

        if self.machinist_setting == 0:
            self.cutz_entry.set_range(-9999.9999, 0.0000)
        else:
            self.cutz_entry.set_range(-9999.9999, 9999.9999)

        self.cutz_entry.setSingleStep(0.1)
        self.cutz_entry.setObjectName("gdb_e_cutz")

        self.grid5.addWidget(self.cutzlabel, 4, 0)
        self.grid5.addWidget(self.cutz_entry, 4, 1)

        # Multi-Depth
        self.mpass_cb = FCCheckBox('%s:' % _("Multi-Depth"))
        self.mpass_cb.setToolTip(
            _(
                "Use multiple passes to limit\n"
                "the cut depth in each pass. Will\n"
                "cut multiple times until Cut Z is\n"
                "reached."
            )
        )
        self.mpass_cb.setObjectName("gdb_e_multidepth")

        self.maxdepth_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.maxdepth_entry.set_precision(self.decimals)
        self.maxdepth_entry.set_range(0, 9999.9999)
        self.maxdepth_entry.setSingleStep(0.1)

        self.maxdepth_entry.setToolTip(_("Depth of each pass (positive)."))
        self.maxdepth_entry.setObjectName("gdb_e_depthperpass")

        self.grid5.addWidget(self.mpass_cb, 5, 0)
        self.grid5.addWidget(self.maxdepth_entry, 5, 1)

        # Travel Z (z_move)
        self.travelzlabel = QtWidgets.QLabel('%s:' % _('Travel Z'))
        self.travelzlabel.setToolTip(
            _("Tool height when travelling\n"
              "across the XY plane.")
        )

        self.travelz_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.travelz_entry.set_precision(self.decimals)

        if self.machinist_setting == 0:
            self.travelz_entry.set_range(0.00001, 9999.9999)
        else:
            self.travelz_entry.set_range(-9999.9999, 9999.9999)

        self.travelz_entry.setSingleStep(0.1)
        self.travelz_entry.setObjectName("gdb_e_travelz")

        self.grid5.addWidget(self.travelzlabel, 6, 0)
        self.grid5.addWidget(self.travelz_entry, 6, 1)

        # Excellon Feedrate Z
        self.frzlabel = QtWidgets.QLabel('%s:' % _('Feedrate Z'))
        self.frzlabel.setToolTip(
            _("Tool speed while drilling\n"
              "(in units per minute).\n"
              "So called 'Plunge' feedrate.\n"
              "This is for linear move G01.")
        )
        self.feedrate_z_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.feedrate_z_entry.set_precision(self.decimals)
        self.feedrate_z_entry.set_range(0.0, 99999.9999)
        self.feedrate_z_entry.setSingleStep(0.1)
        self.feedrate_z_entry.setObjectName("gdb_e_feedratez")

        self.grid5.addWidget(self.frzlabel, 14, 0)
        self.grid5.addWidget(self.feedrate_z_entry, 14, 1)

        # Excellon Rapid Feedrate
        self.feedrate_rapid_label = QtWidgets.QLabel('%s:' % _('Feedrate Rapids'))
        self.feedrate_rapid_label.setToolTip(
            _("Tool speed while drilling\n"
              "(in units per minute).\n"
              "This is for the rapid move G00.\n"
              "It is useful only for Marlin,\n"
              "ignore for any other cases.")
        )
        self.feedrate_rapid_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.feedrate_rapid_entry.set_precision(self.decimals)
        self.feedrate_rapid_entry.set_range(0.0, 99999.9999)
        self.feedrate_rapid_entry.setSingleStep(0.1)
        self.feedrate_rapid_entry.setObjectName("gdb_e_fr_rapid")

        self.grid5.addWidget(self.feedrate_rapid_label, 16, 0)
        self.grid5.addWidget(self.feedrate_rapid_entry, 16, 1)

        # Spindlespeed
        self.spindle_label = QtWidgets.QLabel('%s:' % _('Spindle speed'))
        self.spindle_label.setToolTip(
            _("Speed of the spindle\n"
              "in RPM (optional)")
        )

        self.spindlespeed_entry = FCSpinner(callback=self.confirmation_message_int)
        self.spindlespeed_entry.set_range(0, 1000000)
        self.spindlespeed_entry.set_step(100)
        self.spindlespeed_entry.setObjectName("gdb_e_spindlespeed")

        self.grid5.addWidget(self.spindle_label, 19, 0)
        self.grid5.addWidget(self.spindlespeed_entry, 19, 1)

        # Dwell
        self.dwell_cb = FCCheckBox('%s:' % _('Dwell'))
        self.dwell_cb.setToolTip(
            _("Pause to allow the spindle to reach its\n"
              "speed before cutting.")
        )
        self.dwell_cb.setObjectName("gdb_e_dwell")

        # Dwelltime
        self.dwelltime_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.dwelltime_entry.set_precision(self.decimals)
        self.dwelltime_entry.set_range(0.0, 9999.9999)
        self.dwelltime_entry.setSingleStep(0.1)

        self.dwelltime_entry.setToolTip(
            _("Number of time units for spindle to dwell.")
        )
        self.dwelltime_entry.setObjectName("gdb_e_dwelltime")

        self.grid5.addWidget(self.dwell_cb, 20, 0)
        self.grid5.addWidget(self.dwelltime_entry, 20, 1)

        # Tool Offset
        self.tool_offset_label = QtWidgets.QLabel('%s:' % _('Offset Z'))
        self.tool_offset_label.setToolTip(
            _("Some drill bits (the larger ones) need to drill deeper\n"
              "to create the desired exit hole diameter due of the tip shape.\n"
              "The value here can compensate the Cut Z parameter.")
        )

        self.offset_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.offset_entry.set_precision(self.decimals)
        self.offset_entry.set_range(-9999.9999, 9999.9999)
        self.offset_entry.setObjectName("gdb_e_offset")

        self.grid5.addWidget(self.tool_offset_label, 25, 0)
        self.grid5.addWidget(self.offset_entry, 25, 1)

        # Drill slots
        self.drill_slots_cb = FCCheckBox('%s' % _('Drill slots'))
        self.drill_slots_cb.setToolTip(
            _("If the selected tool has slots then they will be drilled.")
        )
        self.drill_slots_cb.setObjectName("gdb_e_drill_slots")
        self.grid5.addWidget(self.drill_slots_cb, 27, 0, 1, 2)

        # Drill Overlap
        self.drill_overlap_label = QtWidgets.QLabel('%s:' % _('Overlap'))
        self.drill_overlap_label.setToolTip(
            _("How much (percentage) of the tool diameter to overlap previous drill hole.")
        )

        self.drill_overlap_entry = FCDoubleSpinner(suffix='%', callback=self.confirmation_message)
        self.drill_overlap_entry.set_precision(self.decimals)
        self.drill_overlap_entry.set_range(0.0, 100.0000)
        self.drill_overlap_entry.setSingleStep(0.1)

        self.drill_overlap_entry.setObjectName("gdb_e_drill_slots_over")

        self.grid5.addWidget(self.drill_overlap_label, 28, 0)
        self.grid5.addWidget(self.drill_overlap_entry, 28, 1)

        # Last drill in slot
        self.last_drill_cb = FCCheckBox('%s' % _('Last drill'))
        self.last_drill_cb.setToolTip(
            _("If the slot length is not completely covered by drill holes,\n"
              "add a drill hole on the slot end point.")
        )
        self.last_drill_cb.setObjectName("gdb_e_drill_last_drill")
        self.grid5.addWidget(self.last_drill_cb, 30, 0, 1, 2)

        # ####################################################################
        # ####################################################################
        # GUI for the lower part of the window
        # ####################################################################
        # ####################################################################

        new_vlay = QtWidgets.QVBoxLayout()
        g_lay.addLayout(new_vlay, 1, 0, 1, 2)

        self.buttons_frame = QtWidgets.QFrame()
        self.buttons_frame.setContentsMargins(0, 0, 0, 0)
        new_vlay.addWidget(self.buttons_frame)
        self.buttons_box = QtWidgets.QHBoxLayout()
        self.buttons_box.setContentsMargins(0, 0, 0, 0)
        self.buttons_frame.setLayout(self.buttons_box)
        self.buttons_frame.show()

        self.add_entry_btn = FCButton(_("Add Tool in DB"))
        self.add_entry_btn.setToolTip(
            _("Add a new tool in the Tools Database.\n"
              "It will be used in the Geometry UI.\n"
              "You can edit it after it is added.")
        )
        self.buttons_box.addWidget(self.add_entry_btn)

        # add_fct_entry_btn = FCButton(_("Add Paint/NCC Tool in DB"))
        # add_fct_entry_btn.setToolTip(
        #     _("Add a new tool in the Tools Database.\n"
        #       "It will be used in the Paint/NCC Tools UI.\n"
        #       "You can edit it after it is added.")
        # )
        # self.buttons_box.addWidget(add_fct_entry_btn)

        self.remove_entry_btn = FCButton(_("Delete Tool from DB"))
        self.remove_entry_btn.setToolTip(
            _("Remove a selection of tools in the Tools Database.")
        )
        self.buttons_box.addWidget(self.remove_entry_btn)

        self.export_db_btn = FCButton(_("Export DB"))
        self.export_db_btn.setToolTip(
            _("Save the Tools Database to a custom text file.")
        )
        self.buttons_box.addWidget(self.export_db_btn)

        self.import_db_btn = FCButton(_("Import DB"))
        self.import_db_btn.setToolTip(
            _("Load the Tools Database information's from a custom text file.")
        )
        self.buttons_box.addWidget(self.import_db_btn)

        self.save_db_btn = FCButton(_("Save DB"))
        self.save_db_btn.setToolTip(
            _("Save the Tools Database information's.")
        )
        self.buttons_box.addWidget(self.save_db_btn)

        self.add_tool_from_db = FCButton(_("Transfer the Tool"))
        self.add_tool_from_db.setToolTip(
            _("Insert a new tool in the Tools Table of the\n"
              "object/application tool after selecting a tool\n"
              "in the Tools Database.")
        )
        self.add_tool_from_db.setStyleSheet("""
                                            QPushButton
                                            {
                                                font-weight: bold;
                                                color: green;
                                            }
                                            """)
        self.add_tool_from_db.hide()

        self.cancel_tool_from_db = FCButton(_("Cancel"))
        self.cancel_tool_from_db.hide()

        hlay = QtWidgets.QHBoxLayout()
        tree_layout.addLayout(hlay)
        hlay.addWidget(self.add_tool_from_db)
        hlay.addWidget(self.cancel_tool_from_db)
        # hlay.addStretch()
        # ############################ FINSIHED GUI ###################################
        # #############################################################################

    def confirmation_message(self, accepted, minval, maxval):
        if accepted is False:
            self.app.inform[str, bool].emit('[WARNING_NOTCL] %s: [%.*f, %.*f]' % (_("Edited value is out of range"),
                                                                                  self.decimals,
                                                                                  minval,
                                                                                  self.decimals,
                                                                                  maxval), False)
        else:
            self.app.inform[str, bool].emit('[success] %s' % _("Edited value is within limits."), False)

    def confirmation_message_int(self, accepted, minval, maxval):
        if accepted is False:
            self.app.inform[str, bool].emit('[WARNING_NOTCL] %s: [%d, %d]' %
                                            (_("Edited value is out of range"), minval, maxval), False)
        else:
            self.app.inform[str, bool].emit('[success] %s' % _("Edited value is within limits."), False)
        

class ToolsDB2(QtWidgets.QWidget):

    mark_tools_rows = QtCore.pyqtSignal()

    def __init__(self, app, callback_on_edited, callback_on_tool_request, parent=None):
        super(ToolsDB2, self).__init__(parent)

        self.app = app
        self.app_ui = self.app.ui
        self.decimals = self.app.decimals
        self.callback_app = callback_on_edited

        self.on_tool_request = callback_on_tool_request

        self.offset_item_options = ["Path", "In", "Out", "Custom"]
        self.type_item_options = ["Iso", "Rough", "Finish"]
        self.tool_type_item_options = ["C1", "C2", "C3", "C4", "B", "V"]

        '''
        dict to hold all the tools in the Tools DB
        format:
        {
            tool_id: {
                'name': 'new_tool'
                'tooldia': self.app.defaults["geometry_cnctooldia"]
                'offset': 'Path'
                'offset_value': 0.0
                'type':  _('Rough'),
                'tool_type': 'C1'
                'data': dict()
            }
        }
        '''
        self.db_tool_dict = {}

        # ##############################################################################
        # ##############################################################################
        # TOOLS DATABASE UI
        # ##############################################################################
        # ##############################################################################
        layout = QtWidgets.QGridLayout()
        layout.setColumnStretch(0, 0)
        layout.setColumnStretch(1, 1)
        self.setLayout(layout)
        self.ui = ToolsDB2UI(app=self.app, grid_layout=layout)

        # ##############################################################################
        # ##############################################################################
        # ########## SETUP THE DICTIONARIES THAT HOLD THE WIDGETS #####################
        # ##############################################################################
        # ##############################################################################

        self.form_fields = {
            "object_type":      self.ui.object_type_combo,
            "tol_min":          self.ui.tol_min_entry,
            "tol_max":          self.ui.tol_max_entry,
            # Basic
            "name":             self.ui.name_entry,
            "tooldia":          self.ui.dia_entry,
            "tool_type":        self.ui.shape_combo,
            "cutz":             self.ui.cutz_entry,
            "multidepth":       self.ui.multidepth_cb,
            "depthperpass":     self.ui.multidepth_entry,
            "travelz":          self.ui.travelz_entry,
            "feedrate":         self.ui.frxy_entry,
            "feedrate_z":       self.ui.frz_entry,
            "spindlespeed":     self.ui.spindle_entry,
            "dwell":            self.ui.dwell_cb,
            "dwelltime":        self.ui.dwelltime_entry,

            # Advanced
            "type":             self.ui.type_combo,
            "offset":           self.ui.tooloffset_combo,
            "offset_value":     self.ui.custom_offset_entry,
            "vtipdia":          self.ui.vdia_entry,
            "vtipangle":        self.ui.vangle_entry,
            "feedrate_rapid":   self.ui.frapids_entry,
            "extracut":         self.ui.ecut_cb,
            "extracut_length":  self.ui.ecut_length_entry,

            # NCC
            "tools_nccoperation":       self.ui.op_radio,
            "tools_nccmilling_type":    self.ui.milling_type_radio,
            "tools_nccoverlap":         self.ui.ncc_overlap_entry,
            "tools_nccmargin":          self.ui.ncc_margin_entry,
            "tools_nccmethod":          self.ui.ncc_method_combo,
            "tools_nccconnect":         self.ui.ncc_connect_cb,
            "tools_ncccontour":         self.ui.ncc_contour_cb,
            "tools_ncc_offset_choice":  self.ui.ncc_choice_offset_cb,
            "tools_ncc_offset_value":   self.ui.ncc_offset_spinner,

            # Paint
            "tools_paintoverlap":       self.ui.paintoverlap_entry,
            "tools_paintoffset":       self.ui.paint_offset_entry,
            "tools_paintmethod":        self.ui.paintmethod_combo,
            "tools_pathconnect":        self.ui.pathconnect_cb,
            "tools_paintcontour":       self.ui.paintcontour_cb,

            # Isolation
            "tools_iso_passes":         self.ui.passes_entry,
            "tools_iso_overlap":        self.ui.iso_overlap_entry,
            "tools_iso_milling_type":   self.ui.milling_type_radio,
            "tools_iso_follow":         self.ui.follow_cb,
            "tools_iso_isotype":        self.ui.iso_type_radio,

            # Drilling
            "tools_drill_cutz":             self.ui.cutz_entry,
            "tools_drill_multidepth":       self.ui.mpass_cb,
            "tools_drill_depthperpass":     self.ui.maxdepth_entry,
            "tools_drill_travelz":          self.ui.travelz_entry,
            "tools_drill_feedrate_z":       self.ui.feedrate_z_entry,

            "tools_drill_feedrate_rapid":   self.ui.feedrate_rapid_entry,
            "tools_drill_spindlespeed":     self.ui.spindlespeed_entry,
            "tools_drill_dwell":            self.ui.dwell_cb,
            "tools_drill_dwelltime":        self.ui.dwelltime_entry,

            "tools_drill_offset":           self.ui.offset_entry,
            "tools_drill_drill_slots":      self.ui.drill_slots_cb,
            "tools_drill_drill_overlap":    self.ui.drill_overlap_entry,
            "tools_drill_last_drill":       self.ui.last_drill_cb,

        }

        self.name2option = {
            "gdb_object_type":      "object_type",
            "gdb_tol_min":          "tol_min",
            "gdb_tol_max":          "tol_max",

            # Basic
            "gdb_name":             "name",
            "gdb_dia":              "tooldia",
            "gdb_shape":            "tool_type",
            "gdb_cutz":             "cutz",
            "gdb_multidepth":       "multidepth",
            "gdb_multidepth_entry": "depthperpass",
            "gdb_travel":           "travelz",
            "gdb_frxy":             "feedrate",
            "gdb_frz":              "feedrate_z",
            "gdb_spindle":          "spindlespeed",
            "gdb_dwell":            "dwell",
            "gdb_dwelltime":        "dwelltime",

            # Advanced
            "gdb_type":             "type",
            "gdb_tool_offset":      "offset",
            "gdb_custom_offset":    "offset_value",
            "gdb_vdia":             "vtipdia",
            "gdb_vangle":           "vtipangle",
            "gdb_frapids":          "feedrate_rapid",
            "gdb_ecut":             "extracut",
            "gdb_ecut_length":      "extracut_length",

            # NCC
            "gdb_n_operation":      "tools_nccoperation",
            "gdb_n_overlap":        "tools_nccoverlap",
            "gdb_n_margin":         "tools_nccmargin",
            "gdb_n_method":         "tools_nccmethod",
            "gdb_n_connect":        "tools_nccconnect",
            "gdb_n_contour":        "tools_ncccontour",
            "gdb_n_offset":         "tools_ncc_offset_choice",
            "gdb_n_offset_value":   "tools_ncc_offset_value",
            "gdb_n_milling_type":   "tools_nccmilling_type",

            # Paint
            'gdb_p_overlap':        "tools_paintoverlap",
            'gdb_p_offset':         "tools_paintoffset",
            'gdb_p_method':         "tools_paintmethod",
            'gdb_p_connect':        "tools_pathconnect",
            'gdb_p_contour':        "tools_paintcontour",

            # Isolation
            "gdb_i_passes":         "tools_iso_passes",
            "gdb_i_overlap":        "tools_iso_overlap",
            "gdb_i_milling_type":   "tools_iso_milling_type",
            "gdb_i_follow":         "tools_iso_follow",
            "gdb_i_iso_type":       "tools_iso_isotype",

            # Drilling
            "gdb_e_cutz":               "tools_drill_cutz",
            "gdb_e_multidepth":         "tools_drill_multidepth",
            "gdb_e_depthperpass":       "tools_drill_depthperpass",
            "gdb_e_travelz":            "tools_drill_travelz",

            "gdb_e_feedratez":          "tools_drill_feedrate_z",
            "gdb_e_fr_rapid":           "tools_drill_feedrate_rapid",
            "gdb_e_spindlespeed":       "tools_drill_spindlespeed",
            "gdb_e_dwell":              "tools_drill_dwell",
            "gdb_e_dwelltime":          "tools_drill_dwelltime",

            "gdb_e_offset":             "tools_drill_offset",
            "gdb_e_drill_slots":        "tools_drill_drill_slots",
            "gdb_e_drill_slots_over":   "tools_drill_drill_overlap",
            "gdb_e_drill_last_drill":   "tools_drill_last_drill",

        }

        self.current_toolid = None

        # variable to show if double clicking and item will trigger adding a tool from DB
        self.ok_to_add = False

        # ##############################################################################
        # ######################## SIGNALS #############################################
        # ##############################################################################

        self.ui.add_entry_btn.clicked.connect(self.on_tool_add)
        self.ui.remove_entry_btn.clicked.connect(self.on_tool_delete)
        self.ui.export_db_btn.clicked.connect(self.on_export_tools_db_file)
        self.ui.import_db_btn.clicked.connect(self.on_import_tools_db_file)
        self.ui.save_db_btn.clicked.connect(self.on_save_db_btn_click)
        # closebtn.clicked.connect(self.accept)

        self.ui.add_tool_from_db.clicked.connect(self.on_tool_requested_from_app)
        self.ui.cancel_tool_from_db.clicked.connect(self.on_cancel_tool)

        # self.ui.tree_widget.selectionModel().selectionChanged.connect(self.on_list_selection_change)
        self.ui.tree_widget.currentItemChanged.connect(self.on_list_selection_change)
        self.ui.tree_widget.itemChanged.connect(self.on_list_item_edited)
        self.ui.tree_widget.customContextMenuRequested.connect(self.on_menu_request)

        self.ui.tree_widget.itemDoubleClicked.connect(self.on_item_double_clicked)

        self.ui.object_type_combo.currentIndexChanged.connect(self.on_object_type_changed)

        self.setup_db_ui()

    def on_menu_request(self, pos):

        menu = QtWidgets.QMenu()
        add_tool = menu.addAction(QtGui.QIcon(self.app.resource_location + '/plus16.png'), _("Add to DB"))
        add_tool.triggered.connect(self.on_tool_add)

        copy_tool = menu.addAction(QtGui.QIcon(self.app.resource_location + '/copy16.png'), _("Copy from DB"))
        copy_tool.triggered.connect(self.on_tool_copy)

        delete_tool = menu.addAction(QtGui.QIcon(self.app.resource_location + '/delete32.png'), _("Delete from DB"))
        delete_tool.triggered.connect(self.on_tool_delete)

        # sep = menu.addSeparator()

        save_changes = menu.addAction(QtGui.QIcon(self.app.resource_location + '/save_as.png'), _("Save changes"))
        save_changes.triggered.connect(self.on_save_changes)

        # tree_item = self.ui.tree_widget.itemAt(pos)
        menu.exec(self.ui.tree_widget.viewport().mapToGlobal(pos))

    def on_save_changes(self):
        widget_name = self.app_ui.plot_tab_area.currentWidget().objectName()
        if widget_name == 'database_tab':
            # Tools DB saved, update flag
            self.app.tools_db_changed_flag = False
            self.app.tools_db_tab.on_save_tools_db()

    def on_item_double_clicked(self, item, column):
        if column == 0 and self.ok_to_add is True:
            self.ok_to_add = False
            self.on_tool_requested_from_app()

    def on_list_selection_change(self, current, previous):
        self.ui_disconnect()
        self.current_toolid = int(current.text(0))
        self.storage_to_form(self.db_tool_dict[current.text(0)])
        self.ui_connect()

    def on_list_item_edited(self, item, column):
        if column == 0:
            return

        self.ui.name_entry.set_value(item.text(1))

    def storage_to_form(self, dict_storage):
        for form_key in self.form_fields:
            for storage_key in dict_storage:
                if form_key == storage_key:
                    try:
                        self.form_fields[form_key].set_value(dict_storage[form_key])
                    except Exception as e:
                        print(str(e))
                if storage_key == 'data':
                    for data_key in dict_storage[storage_key]:
                        if form_key == data_key:
                            try:
                                self.form_fields[form_key].set_value(dict_storage['data'][data_key])
                            except Exception as e:
                                print(str(e))

    def form_to_storage(self, tool):
        self.blockSignals(True)

        widget_changed = self.sender()
        wdg_objname = widget_changed.objectName()
        option_changed = self.name2option[wdg_objname]
        tooluid_item = int(tool)

        for tooluid_key, tooluid_val in self.db_tool_dict.items():
            if int(tooluid_key) == tooluid_item:
                new_option_value = self.form_fields[option_changed].get_value()
                if option_changed in tooluid_val:
                    tooluid_val[option_changed] = new_option_value
                if option_changed in tooluid_val['data']:
                    tooluid_val['data'][option_changed] = new_option_value
        self.blockSignals(False)

    def setup_db_ui(self):
        filename = self.app.data_path + '\\geo_tools_db.FlatDB'

        # load the database tools from the file
        try:
            with open(filename) as f:
                tools = f.read()
        except IOError:
            self.app.log.error("Could not load tools DB file.")
            self.app.inform.emit('[ERROR] %s' % _("Could not load Tools DB file."))
            return

        try:
            self.db_tool_dict = json.loads(tools)
        except Exception:
            e = sys.exc_info()[0]
            self.app.log.error(str(e))
            self.app.inform.emit('[ERROR] %s' % _("Failed to parse Tools DB file."))
            return

        self.app.inform.emit('[success] %s: %s' % (_("Loaded Tools DB from"), filename))

        self.build_db_ui()

    def build_db_ui(self):
        self.ui_disconnect()
        nr_crt = 0

        parent = self.ui.tree_widget
        self.ui.tree_widget.blockSignals(True)
        self.ui.tree_widget.clear()
        self.ui.tree_widget.blockSignals(False)

        for toolid, dict_val in self.db_tool_dict.items():
            row = nr_crt
            nr_crt += 1

            t_name = dict_val['name']
            try:
                # self.add_tool_table_line(row, name=t_name, tooldict=dict_val)
                self.ui.tree_widget.blockSignals(True)
                try:
                    self.ui.tree_widget.addParentEditable(parent=parent, title=[str(row+1), t_name], editable=True)
                except Exception as e:
                    print('FlatCAMCoomn.ToolDB2.build_db_ui() -> ', str(e))
                self.ui.tree_widget.blockSignals(False)
            except Exception as e:
                self.app.log.debug("ToolDB.build_db_ui.add_tool_table_line() --> %s" % str(e))

        if self.current_toolid is None or self.current_toolid < 1:
            if self.db_tool_dict:
                self.storage_to_form(self.db_tool_dict['1'])

                # Enable appGUI
                self.ui.tool_description_box.setEnabled(True)
                self.ui.basic_box.setEnabled(True)
                self.ui.advanced_box.setEnabled(True)
                self.ui.ncc_box.setEnabled(True)
                self.ui.paint_box.setEnabled(True)
                self.ui.iso_box.setEnabled(True)
                self.ui.drill_box.setEnabled(True)

                self.ui.tree_widget.setCurrentItem(self.ui.tree_widget.topLevelItem(0))
                # self.ui.tree_widget.setFocus()

            else:
                # Disable appGUI
                self.ui.tool_description_box.setEnabled(False)
                self.ui.basic_box.setEnabled(False)
                self.ui.advanced_box.setEnabled(False)
                self.ui.ncc_box.setEnabled(False)
                self.ui.paint_box.setEnabled(False)
                self.ui.iso_box.setEnabled(False)
                self.ui.drill_box.setEnabled(False)
        else:
            self.storage_to_form(self.db_tool_dict[str(self.current_toolid)])

        self.ui_connect()

    def on_object_type_changed(self, index=None, val=None):

        if val is None:
            object_type = self.ui.object_type_combo.get_value()
        else:
            object_type = val

        self.ui.tool_description_box.setEnabled(True)
        if self.db_tool_dict:
            if object_type == _("General"):
                self.ui.basic_box.setEnabled(True)
                self.ui.advanced_box.setEnabled(True)
                self.ui.ncc_box.setEnabled(True)
                self.ui.paint_box.setEnabled(True)
                self.ui.iso_box.setEnabled(True)
                self.ui.drill_box.setEnabled(True)

            if object_type == _("Milling"):
                self.ui.basic_box.setEnabled(True)
                self.ui.advanced_box.setEnabled(True)
                self.ui.ncc_box.setEnabled(False)
                self.ui.paint_box.setEnabled(False)
                self.ui.iso_box.setEnabled(False)
                self.ui.drill_box.setEnabled(False)

            if object_type == _("Drilling"):
                self.ui.basic_box.setEnabled(False)
                self.ui.advanced_box.setEnabled(False)
                self.ui.ncc_box.setEnabled(False)
                self.ui.paint_box.setEnabled(False)
                self.ui.iso_box.setEnabled(False)
                self.ui.drill_box.setEnabled(True)

    def on_tool_add(self):
        """
        Add a tool in the DB Tool Table
        :return: None
        """

        default_data = {}
        default_data.update({
            "plot":             True,
            "cutz":             float(self.app.defaults["geometry_cutz"]),
            "multidepth":       self.app.defaults["geometry_multidepth"],
            "depthperpass":     float(self.app.defaults["geometry_depthperpass"]),
            "vtipdia":          float(self.app.defaults["geometry_vtipdia"]),
            "vtipangle":        float(self.app.defaults["geometry_vtipangle"]),
            "travelz":          float(self.app.defaults["geometry_travelz"]),
            "feedrate":         float(self.app.defaults["geometry_feedrate"]),
            "feedrate_z":       float(self.app.defaults["geometry_feedrate_z"]),
            "feedrate_rapid":   float(self.app.defaults["geometry_feedrate_rapid"]),
            "spindlespeed":     self.app.defaults["geometry_spindlespeed"],
            "dwell":            self.app.defaults["geometry_dwell"],
            "dwelltime":        float(self.app.defaults["geometry_dwelltime"]),
            "ppname_g":         self.app.defaults["geometry_ppname_g"],
            "extracut":         self.app.defaults["geometry_extracut"],
            "extracut_length":  float(self.app.defaults["geometry_extracut_length"]),
            "toolchange":       self.app.defaults["geometry_toolchange"],
            "toolchangexy":     self.app.defaults["geometry_toolchangexy"],
            "toolchangez":      float(self.app.defaults["geometry_toolchangez"]),
            "startz":           self.app.defaults["geometry_startz"],
            "endz":             float(self.app.defaults["geometry_endz"]),

            "object_type":      _("General"),
            "tol_min":          0.0,
            "tol_max":          0.0,

            # NCC
            "tools_nccoperation":       self.app.defaults["tools_nccoperation"],
            "tools_nccmilling_type":    self.app.defaults["tools_nccmilling_type"],
            "tools_nccoverlap":         float(self.app.defaults["tools_nccoverlap"]),
            "tools_nccmargin":          float(self.app.defaults["tools_nccmargin"]),
            "tools_nccmethod":          self.app.defaults["tools_nccmethod"],
            "tools_nccconnect":         self.app.defaults["tools_nccconnect"],
            "tools_ncccontour":         self.app.defaults["tools_ncccontour"],
            "tools_ncc_offset_choice":  self.app.defaults["tools_ncc_offset_choice"],
            "tools_ncc_offset_value":   float(self.app.defaults["tools_ncc_offset_value"]),

            # Paint
            "tools_paintoverlap":       float(self.app.defaults["tools_paintoverlap"]),
            "tools_paintoffset":        float(self.app.defaults["tools_paintoffset"]),
            "tools_paintmethod":        self.app.defaults["tools_paintmethod"],
            "tools_pathconnect":        self.app.defaults["tools_pathconnect"],
            "tools_paintcontour":       self.app.defaults["tools_paintcontour"],

            # Isolation
            "tools_iso_passes":         int(self.app.defaults["tools_iso_passes"]),
            "tools_iso_overlap":        float(self.app.defaults["tools_iso_overlap"]),
            "tools_iso_milling_type":   self.app.defaults["tools_iso_milling_type"],
            "tools_iso_follow":         self.app.defaults["tools_iso_follow"],
            "tools_iso_isotype":        self.app.defaults["tools_iso_isotype"],

            # Drilling
            "tools_drill_cutz":             float(self.app.defaults["tools_drill_cutz"]),
            "tools_drill_multidepth":       self.app.defaults["tools_drill_multidepth"],
            "tools_drill_depthperpass":     float(self.app.defaults["tools_drill_depthperpass"]),
            "tools_drill_travelz":          float(self.app.defaults["tools_drill_travelz"]),

            "tools_drill_feedrate_z":       float(self.app.defaults["tools_drill_feedrate_z"]),
            "tools_drill_feedrate_rapid":   float(self.app.defaults["tools_drill_feedrate_rapid"]),
            "tools_drill_spindlespeed":     float(self.app.defaults["tools_drill_spindlespeed"]),
            "tools_drill_dwell":            self.app.defaults["tools_drill_dwell"],

            "tools_drill_offset":           float(self.app.defaults["tools_drill_offset"]),
            "tools_drill_drill_slots":      self.app.defaults["tools_drill_drill_slots"],
            "tools_drill_drill_overlap":    float(self.app.defaults["tools_drill_drill_overlap"]),
            "tools_drill_last_drill":       self.app.defaults["tools_drill_last_drill"],

        })

        temp = []
        for k, v in self.db_tool_dict.items():
            if "new_tool_" in v['name']:
                temp.append(float(v['name'].rpartition('_')[2]))

        if temp:
            new_name = "new_tool_%d" % int(max(temp) + 1)
        else:
            new_name = "new_tool_1"

        dict_elem = {}
        dict_elem['name'] = new_name
        if type(self.app.defaults["geometry_cnctooldia"]) == float:
            dict_elem['tooldia'] = self.app.defaults["geometry_cnctooldia"]
        else:
            try:
                tools_string = self.app.defaults["geometry_cnctooldia"].split(",")
                tools_diameters = [eval(a) for a in tools_string if a != '']
                dict_elem['tooldia'] = tools_diameters[0] if tools_diameters else 0.0
            except Exception as e:
                self.app.log.debug("ToolDB.on_tool_add() --> %s" % str(e))
                return

        dict_elem['offset'] = 'Path'
        dict_elem['offset_value'] = 0.0
        dict_elem['type'] = 'Rough'
        dict_elem['tool_type'] = 'C1'
        dict_elem['data'] = default_data

        new_toolid = len(self.db_tool_dict) + 1
        self.db_tool_dict[str(new_toolid)] = deepcopy(dict_elem)

        # add the new entry to the Tools DB table
        self.update_storage()
        self.build_db_ui()

        # select the last Tree item just added
        nr_items = self.ui.tree_widget.topLevelItemCount()
        if nr_items:
            last_item = self.ui.tree_widget.topLevelItem(nr_items - 1)
            self.ui.tree_widget.setCurrentItem(last_item)
            last_item.setSelected(True)

        self.on_object_type_changed(val=dict_elem['data']['object_type'])
        self.app.inform.emit('[success] %s' % _("Tool added to DB."))

    def on_tool_copy(self):
        """
        Copy a selection of Tools in the Tools DB table
        :return:
        """
        new_tool_id = len(self.db_tool_dict)
        for item in self.ui.tree_widget.selectedItems():
            old_tool_id = item.data(0, QtCore.Qt.DisplayRole)

            for toolid, dict_val in list(self.db_tool_dict.items()):
                if int(old_tool_id) == int(toolid):
                    new_tool_id += 1
                    new_key = str(new_tool_id)

                    self.db_tool_dict.update({
                        new_key: deepcopy(dict_val)
                    })

        self.current_toolid = new_tool_id

        self.update_storage()
        self.build_db_ui()

        # select the last Tree item just added
        nr_items = self.ui.tree_widget.topLevelItemCount()
        if nr_items:
            last_item = self.ui.tree_widget.topLevelItem(nr_items - 1)
            self.ui.tree_widget.setCurrentItem(last_item)
            last_item.setSelected(True)

        self.callback_app()
        self.app.inform.emit('[success] %s' % _("Tool copied from Tools DB."))

    def on_tool_delete(self):
        """
        Delete a selection of Tools in the Tools DB table
        :return:
        """
        for item in self.ui.tree_widget.selectedItems():
            toolname_to_remove = item.data(0, QtCore.Qt.DisplayRole)

            for toolid, dict_val in list(self.db_tool_dict.items()):
                if int(toolname_to_remove) == int(toolid):
                    # remove from the storage
                    self.db_tool_dict.pop(toolid, None)

        self.current_toolid -= 1

        self.update_storage()
        self.build_db_ui()

        # select the first Tree item
        nr_items = self.ui.tree_widget.topLevelItemCount()
        if nr_items:
            first_item = self.ui.tree_widget.topLevelItem(0)
            self.ui.tree_widget.setCurrentItem(first_item)
            first_item.setSelected(True)

        self.app.inform.emit('[success] %s' % _("Tool removed from Tools DB."))

    def on_export_tools_db_file(self):
        self.app.defaults.report_usage("on_export_tools_db_file")
        self.app.log.debug("on_export_tools_db_file()")

        date = str(datetime.today()).rpartition('.')[0]
        date = ''.join(c for c in date if c not in ':-')
        date = date.replace(' ', '_')

        filter__ = "Text File (*.TXT);;All Files (*.*)"
        filename, _f = FCFileSaveDialog.get_saved_filename(caption=_("Export Tools Database"),
                                                           directory='{l_save}/FlatCAM_{n}_{date}'.format(
                                                                l_save=str(self.app.get_last_save_folder()),
                                                                n=_("Tools_Database"),
                                                                date=date),
                                                           ext_filter=filter__)

        filename = str(filename)

        if filename == "":
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
            return
        else:
            try:
                f = open(filename, 'w')
                f.close()
            except PermissionError:
                self.app.inform.emit('[WARNING] %s' %
                                     _("Permission denied, saving not possible.\n"
                                       "Most likely another app is holding the file open and not accessible."))
                return
            except IOError:
                self.app.log.debug('Creating a new Tools DB file ...')
                f = open(filename, 'w')
                f.close()
            except Exception:
                e = sys.exc_info()[0]
                self.app.log.error("Could not load Tools DB file.")
                self.app.log.error(str(e))
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("Could not load Tools DB file."))
                return

            # Save update options
            try:
                # Save Tools DB in a file
                try:
                    with open(filename, "w") as f:
                        json.dump(self.db_tool_dict, f, default=to_dict, indent=2)
                except Exception as e:
                    self.app.log.debug("App.on_save_tools_db() --> %s" % str(e))
                    self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed to write Tools DB to file."))
                    return
            except Exception:
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed to write Tools DB to file."))
                return

        self.app.inform.emit('[success] %s: %s' % (_("Exported Tools DB to"), filename))

    def on_import_tools_db_file(self):
        self.app.defaults.report_usage("on_import_tools_db_file")
        self.app.log.debug("on_import_tools_db_file()")

        filter__ = "Text File (*.TXT);;All Files (*.*)"
        filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Import FlatCAM Tools DB"), filter=filter__)

        if filename == "":
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
        else:
            try:
                with open(filename) as f:
                    tools_in_db = f.read()
            except IOError:
                self.app.log.error("Could not load Tools DB file.")
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("Could not load Tools DB file."))
                return

            try:
                self.db_tool_dict = json.loads(tools_in_db)
            except Exception:
                e = sys.exc_info()[0]
                self.app.log.error(str(e))
                self.app.inform.emit('[ERROR] %s' % _("Failed to parse Tools DB file."))
                return

            self.app.inform.emit('[success] %s: %s' % (_("Loaded Tools DB from"), filename))
            self.build_db_ui()
            self.update_storage()

    def on_save_tools_db(self, silent=False):
        self.app.log.debug("ToolsDB.on_save_button() --> Saving Tools Database to file.")

        filename = self.app.data_path + "/geo_tools_db.FlatDB"

        # Preferences save, update the color of the Tools DB Tab text
        for idx in range(self.app_ui.plot_tab_area.count()):
            if self.app_ui.plot_tab_area.tabText(idx) == _("Tools Database"):
                self.app_ui.plot_tab_area.tabBar.setTabTextColor(idx, QtGui.QColor('black'))
                self.ui.save_db_btn.setStyleSheet("")

                # Save Tools DB in a file
                try:
                    f = open(filename, "w")
                    json.dump(self.db_tool_dict, f, default=to_dict, indent=2)
                    f.close()
                except Exception as e:
                    self.app.log.debug("ToolsDB.on_save_tools_db() --> %s" % str(e))
                    self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed to write Tools DB to file."))
                    return

                if not silent:
                    self.app.inform.emit('[success] %s' % _("Saved Tools DB."))

    def on_save_db_btn_click(self):
        self.app.tools_db_changed_flag = False
        self.on_save_tools_db()

    def on_calculate_tooldia(self):
        if self.ui.shape_combo.get_value() == 'V':
            tip_dia = float(self.ui.vdia_entry.get_value())
            half_tip_angle = float(self.ui.vangle_entry.get_value()) / 2.0
            cut_z = float(self.ui.cutz_entry.get_value())
            cut_z = -cut_z if cut_z < 0 else cut_z

            # calculated tool diameter so the cut_z parameter is obeyed
            tool_dia = tip_dia + (2 * cut_z * math.tan(math.radians(half_tip_angle)))

            self.ui.dia_entry.set_value(tool_dia)

    def ui_connect(self):
        # make sure that we don't make multiple connections to the widgets
        self.ui_disconnect()

        self.ui.name_entry.editingFinished.connect(self.update_tree_name)

        for key in self.form_fields:
            wdg = self.form_fields[key]

            # FCEntry
            if isinstance(wdg, FCEntry):
                wdg.textChanged.connect(self.update_storage)

            # ComboBox
            if isinstance(wdg, FCComboBox):
                wdg.currentIndexChanged.connect(self.update_storage)

            # CheckBox
            if isinstance(wdg, FCCheckBox):
                wdg.toggled.connect(self.update_storage)

            # FCRadio
            if isinstance(wdg, RadioSet):
                wdg.activated_custom.connect(self.update_storage)

            # SpinBox, DoubleSpinBox
            if isinstance(wdg, FCSpinner) or isinstance(wdg, FCDoubleSpinner):
                wdg.valueChanged.connect(self.update_storage)

        # connect the calculate tooldia method to the controls
        # if the tool shape is 'V' the tool dia will be calculated to obey Cut Z parameter
        self.ui.shape_combo.currentIndexChanged.connect(self.on_calculate_tooldia)
        self.ui.cutz_entry.valueChanged.connect(self.on_calculate_tooldia)
        self.ui.vdia_entry.valueChanged.connect(self.on_calculate_tooldia)
        self.ui.vangle_entry.valueChanged.connect(self.on_calculate_tooldia)

    def ui_disconnect(self):
        try:
            self.ui.name_entry.editingFinished.disconnect(self.update_tree_name)
        except (TypeError, AttributeError):
            pass

        try:
            self.ui.shape_combo.currentIndexChanged.disconnect(self.on_calculate_tooldia)
        except (TypeError, AttributeError):
            pass

        try:
            self.ui.cutz_entry.valueChanged.disconnect(self.on_calculate_tooldia)
        except (TypeError, AttributeError):
            pass

        try:
            self.ui.vdia_entry.valueChanged.disconnect(self.on_calculate_tooldia)
        except (TypeError, AttributeError):
            pass

        try:
            self.ui.vangle_entry.valueChanged.disconnect(self.on_calculate_tooldia)
        except (TypeError, AttributeError):
            pass

        for key in self.form_fields:
            wdg = self.form_fields[key]

            # FCEntry
            if isinstance(wdg, FCEntry):
                try:
                    wdg.textChanged.disconnect(self.update_storage)
                except (TypeError, AttributeError):
                    pass

            # ComboBox
            if isinstance(wdg, FCComboBox):
                try:
                    wdg.currentIndexChanged.disconnect(self.update_storage)
                except (TypeError, AttributeError):
                    pass

            # CheckBox
            if isinstance(wdg, FCCheckBox):
                try:
                    wdg.toggled.disconnect(self.update_storage)
                except (TypeError, AttributeError):
                    pass

            # FCRadio
            if isinstance(wdg, RadioSet):
                try:
                    wdg.activated_custom.disconnect(self.update_storage)
                except (TypeError, AttributeError):
                    pass

            # SpinBox, DoubleSpinBox
            if isinstance(wdg, FCSpinner) or isinstance(wdg, FCDoubleSpinner):
                try:
                    wdg.valueChanged.disconnect(self.update_storage)
                except (TypeError, AttributeError):
                    pass

    def update_tree_name(self):
        val = self.ui.name_entry.get_value()

        item = self.ui.tree_widget.currentItem()
        if item is None:
            return
        # I'm setting the value for the second column (designated by 1) because first column holds the ID
        # and second column holds the Name (this behavior is set in the build_ui method)
        item.setData(1, QtCore.Qt.DisplayRole, val)

    def update_storage(self):
        """
        Update the dictionary that is the storage of the tools 'database'
        :return:
        """
        tool_id = str(self.current_toolid)

        try:
            wdg = self.sender()

            assert isinstance(wdg, QtWidgets.QWidget) or isinstance(wdg, QtWidgets.QAction), \
                "Expected a QWidget got %s" % type(wdg)

            if wdg is None:
                return

            wdg_name = wdg.objectName()
            val = wdg.get_value()
        except AttributeError:
            return

        if wdg_name == "gdb_name":
            self.db_tool_dict[tool_id]['name'] = val
        elif wdg_name == "gdb_dia":
            self.db_tool_dict[tool_id]['tooldia'] = val
        elif wdg_name == "gdb_tool_offset":
            self.db_tool_dict[tool_id]['offset'] = val
        elif wdg_name == "gdb_custom_offset":
            self.db_tool_dict[tool_id]['offset_value'] = val
        elif wdg_name == "gdb_type":
            self.db_tool_dict[tool_id]['type'] = val
        elif wdg_name == "gdb_shape":
            self.db_tool_dict[tool_id]['tool_type'] = val
        else:
            if wdg_name == "gdb_object_type":
                self.db_tool_dict[tool_id]['data']['object_type'] = val
            elif wdg_name == "gdb_tol_min":
                self.db_tool_dict[tool_id]['data']['tol_min'] = val
            elif wdg_name == "gdb_tol_max":
                self.db_tool_dict[tool_id]['data']['tol_max'] = val

            elif wdg_name == "gdb_cutz":
                self.db_tool_dict[tool_id]['data']['cutz'] = val
            elif wdg_name == "gdb_multidepth":
                self.db_tool_dict[tool_id]['data']['multidepth'] = val
            elif wdg_name == "gdb_multidepth_entry":
                self.db_tool_dict[tool_id]['data']['depthperpass'] = val

            elif wdg_name == "gdb_travel":
                self.db_tool_dict[tool_id]['data']['travelz'] = val
            elif wdg_name == "gdb_frxy":
                self.db_tool_dict[tool_id]['data']['feedrate'] = val
            elif wdg_name == "gdb_frz":
                self.db_tool_dict[tool_id]['data']['feedrate_z'] = val
            elif wdg_name == "gdb_spindle":
                self.db_tool_dict[tool_id]['data']['spindlespeed'] = val
            elif wdg_name == "gdb_dwell":
                self.db_tool_dict[tool_id]['data']['dwell'] = val
            elif wdg_name == "gdb_dwelltime":
                self.db_tool_dict[tool_id]['data']['dwelltime'] = val

            elif wdg_name == "gdb_vdia":
                self.db_tool_dict[tool_id]['data']['vtipdia'] = val
            elif wdg_name == "gdb_vangle":
                self.db_tool_dict[tool_id]['data']['vtipangle'] = val
            elif wdg_name == "gdb_frapids":
                self.db_tool_dict[tool_id]['data']['feedrate_rapid'] = val
            elif wdg_name == "gdb_ecut":
                self.db_tool_dict[tool_id]['data']['extracut'] = val
            elif wdg_name == "gdb_ecut_length":
                self.db_tool_dict[tool_id]['data']['extracut_length'] = val

            # NCC Tool
            elif wdg_name == "gdb_n_operation":
                self.db_tool_dict[tool_id]['data']['tools_nccoperation'] = val
            elif wdg_name == "gdb_n_overlap":
                self.db_tool_dict[tool_id]['data']['tools_nccoverlap'] = val
            elif wdg_name == "gdb_n_margin":
                self.db_tool_dict[tool_id]['data']['tools_nccmargin'] = val
            elif wdg_name == "gdb_n_method":
                self.db_tool_dict[tool_id]['data']['tools_nccmethod'] = val
            elif wdg_name == "gdb_n_connect":
                self.db_tool_dict[tool_id]['data']['tools_nccconnect'] = val
            elif wdg_name == "gdb_n_contour":
                self.db_tool_dict[tool_id]['data']['tools_ncccontour'] = val
            elif wdg_name == "gdb_n_offset":
                self.db_tool_dict[tool_id]['data']['tools_ncc_offset_choice'] = val
            elif wdg_name == "gdb_n_offset_value":
                self.db_tool_dict[tool_id]['data']['tools_ncc_offset_value'] = val
            elif wdg_name == "gdb_n_milling_type":
                self.db_tool_dict[tool_id]['data']['tools_nccmilling_type'] = val

            # Paint Tool
            elif wdg_name == "gdb_p_overlap":
                self.db_tool_dict[tool_id]['data']['tools_paintoverlap'] = val
            elif wdg_name == "gdb_p_offset":
                self.db_tool_dict[tool_id]['data']['tools_paintoffset'] = val
            elif wdg_name == "gdb_p_method":
                self.db_tool_dict[tool_id]['data']['tools_paintmethod'] = val
            elif wdg_name == "gdb_p_connect":
                self.db_tool_dict[tool_id]['data']['tools_pathconnect'] = val
            elif wdg_name == "gdb_p_contour":
                self.db_tool_dict[tool_id]['data']['tools_paintcontour'] = val

            # Isolation Tool
            elif wdg_name == "gdb_i_passes":
                self.db_tool_dict[tool_id]['data']['tools_iso_passes'] = val
            elif wdg_name == "gdb_i_overlap":
                self.db_tool_dict[tool_id]['data']['tools_iso_overlap'] = val
            elif wdg_name == "gdb_i_milling_type":
                self.db_tool_dict[tool_id]['data']['tools_iso_milling_type'] = val
            elif wdg_name == "gdb_i_follow":
                self.db_tool_dict[tool_id]['data']['tools_iso_follow'] = val
            elif wdg_name == "gdb_i_iso_type":
                self.db_tool_dict[tool_id]['data']['tools_iso_isotype'] = val

            # Drilling Tool
            elif wdg_name == "gdb_e_cutz":
                self.db_tool_dict[tool_id]['data']['tools_drill_cutz'] = val
            elif wdg_name == "gdb_e_multidepth":
                self.db_tool_dict[tool_id]['data']['tools_drill_multidepth'] = val
            elif wdg_name == "gdb_e_depthperpass":
                self.db_tool_dict[tool_id]['data']['tools_drill_depthperpass'] = val
            elif wdg_name == "gdb_e_travelz":
                self.db_tool_dict[tool_id]['data']['tools_drill_travelz'] = val

            elif wdg_name == "gdb_e_feedratez":
                self.db_tool_dict[tool_id]['data']['tools_drill_feedrate_z'] = val
            elif wdg_name == "gdb_e_fr_rapid":
                self.db_tool_dict[tool_id]['data']['tools_drill_feedrate_rapid'] = val
            elif wdg_name == "gdb_e_spindlespeed":
                self.db_tool_dict[tool_id]['data']['tools_drill_spindlespeed'] = val
            elif wdg_name == "gdb_e_dwell":
                self.db_tool_dict[tool_id]['data']['tools_drill_dwell'] = val
            elif wdg_name == "gdb_e_dwelltime":
                self.db_tool_dict[tool_id]['data']['tools_drill_dwelltime'] = val

            elif wdg_name == "gdb_e_offset":
                self.db_tool_dict[tool_id]['data']['tools_drill_offset'] = val
            elif wdg_name == "gdb_e_drill_slots":
                self.db_tool_dict[tool_id]['data']['tools_drill_drill_slots'] = val
            elif wdg_name == "gdb_e_drill_slots_over":
                self.db_tool_dict[tool_id]['data']['tools_drill_drill_overlap'] = val
            elif wdg_name == "gdb_e_drill_last_drill":
                self.db_tool_dict[tool_id]['data']['tools_drill_last_drill'] = val

        self.callback_app()

    def on_tool_requested_from_app(self):
        if not self.ui.tree_widget.selectedItems():
            self.app.inform.emit('[WARNING_NOTCL] %s...' % _("No Tool/row selected in the Tools Database table"))
            return

        for item in self.ui.tree_widget.selectedItems():
            tool_uid = item.data(0, QtCore.Qt.DisplayRole)

            for key in self.db_tool_dict.keys():
                if str(key) == str(tool_uid):
                    selected_tool = self.db_tool_dict[key]
                    self.on_tool_request(tool=selected_tool)

    def on_cancel_tool(self):
        for idx in range(self.app_ui.plot_tab_area.count()):
            if self.app_ui.plot_tab_area.tabText(idx) == _("Tools Database"):
                wdg = self.app_ui.plot_tab_area.widget(idx)
                wdg.deleteLater()
                self.app_ui.plot_tab_area.removeTab(idx)
        self.app.inform.emit('%s' % _("Cancelled adding tool from DB."))

    # def resize_new_tool_table_widget(self, min_size, max_size):
    #     """
    #     Resize the table widget responsible for adding new tool in the Tool Database
    #
    #     :param min_size: passed by rangeChanged signal or the self.new_tool_table_widget.horizontalScrollBar()
    #     :param max_size: passed by rangeChanged signal or the self.new_tool_table_widget.horizontalScrollBar()
    #     :return:
    #     """
    #     t_height = self.t_height
    #     if max_size > min_size:
    #         t_height = self.t_height + self.new_tool_table_widget.verticalScrollBar().height()
    #
    #     self.new_tool_table_widget.setMaximumHeight(t_height)

    def closeEvent(self, QCloseEvent):
        super().closeEvent(QCloseEvent)
