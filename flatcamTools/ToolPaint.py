from FlatCAMTool import FlatCAMTool
from copy import copy,deepcopy
from ObjectCollection import *


class ToolPaint(FlatCAMTool, Gerber):

    toolName = "Paint Area"

    def __init__(self, app):
        self.app = app

        FlatCAMTool.__init__(self, app)
        Geometry.__init__(self, geo_steps_per_circle=self.app.defaults["geometry_circle_steps"])

        ## Title
        title_label = QtWidgets.QLabel("<font size=4><b>%s</b></font>" % self.toolName)
        self.layout.addWidget(title_label)

        self.tools_frame = QtWidgets.QFrame()
        self.tools_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.tools_frame)
        self.tools_box = QtWidgets.QVBoxLayout()
        self.tools_box.setContentsMargins(0, 0, 0, 0)
        self.tools_frame.setLayout(self.tools_box)

        ## Form Layout
        form_layout = QtWidgets.QFormLayout()
        self.tools_box.addLayout(form_layout)

        ## Object
        self.object_combo = QtWidgets.QComboBox()
        self.object_combo.setModel(self.app.collection)
        self.object_combo.setRootModelIndex(self.app.collection.index(2, 0, QtCore.QModelIndex()))
        self.object_combo.setCurrentIndex(1)
        self.object_label = QtWidgets.QLabel("Geometry:")
        self.object_label.setToolTip(
            "Geometry object to be painted.                        "
        )
        e_lab_0 = QtWidgets.QLabel('')
        form_layout.addRow(self.object_label, self.object_combo)
        form_layout.addRow(e_lab_0)

        #### Tools ####
        self.tools_table_label = QtWidgets.QLabel('<b>Tools Table</b>')
        self.tools_table_label.setToolTip(
            "Tools pool from which the algorithm\n"
            "will pick the ones used for painting."
        )
        self.tools_box.addWidget(self.tools_table_label)

        self.tools_table = FCTable()
        self.tools_box.addWidget(self.tools_table)

        self.tools_table.setColumnCount(4)
        self.tools_table.setHorizontalHeaderLabels(['#', 'Diameter', 'TT', ''])
        self.tools_table.setColumnHidden(3, True)
        # self.tools_table.setSortingEnabled(False)
        # self.tools_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        self.tools_table.horizontalHeaderItem(0).setToolTip(
            "This is the Tool Number.\n"
            "Painting will start with the tool with the biggest diameter,\n"
            "continuing until there are no more tools.\n"
            "Only tools that create painting geometry will still be present\n"
            "in the resulting geometry. This is because with some tools\n"
            "this function will not be able to create painting geometry."
            )
        self.tools_table.horizontalHeaderItem(1).setToolTip(
            "Tool Diameter. It's value (in current FlatCAM units) \n"
            "is the cut width into the material.")

        self.tools_table.horizontalHeaderItem(2).setToolTip(
            "The Tool Type (TT) can be:<BR>"
            "- <B>Circular</B> with 1 ... 4 teeth -> it is informative only. Being circular, <BR>"
            "the cut width in material is exactly the tool diameter.<BR>"
            "- <B>Ball</B> -> informative only and make reference to the Ball type endmill.<BR>"
            "- <B>V-Shape</B> -> it will disable de Z-Cut parameter in the resulting geometry UI form "
            "and enable two additional UI form fields in the resulting geometry: V-Tip Dia and "
            "V-Tip Angle. Adjusting those two values will adjust the Z-Cut parameter such "
            "as the cut width into material will be equal with the value in the Tool Diameter "
            "column of this table.<BR>"
            "Choosing the <B>V-Shape</B> Tool Type automatically will select the Operation Type "
            "in the resulting geometry as Isolation.")

        self.empty_label = QtWidgets.QLabel('')
        self.tools_box.addWidget(self.empty_label)

        #### Add a new Tool ####
        hlay = QtWidgets.QHBoxLayout()
        self.tools_box.addLayout(hlay)

        self.addtool_entry_lbl = QtWidgets.QLabel('<b>Tool Dia:</b>')
        self.addtool_entry_lbl.setToolTip(
            "Diameter for the new tool."
        )
        self.addtool_entry = FloatEntry()

        # hlay.addWidget(self.addtool_label)
        # hlay.addStretch()
        hlay.addWidget(self.addtool_entry_lbl)
        hlay.addWidget(self.addtool_entry)

        grid2 = QtWidgets.QGridLayout()
        self.tools_box.addLayout(grid2)

        self.addtool_btn = QtWidgets.QPushButton('Add')
        self.addtool_btn.setToolTip(
            "Add a new tool to the Tool Table\n"
            "with the diameter specified above."
        )

        # self.copytool_btn = QtWidgets.QPushButton('Copy')
        # self.copytool_btn.setToolTip(
        #     "Copy a selection of tools in the Tool Table\n"
        #     "by first selecting a row in the Tool Table."
        # )

        self.deltool_btn = QtWidgets.QPushButton('Delete')
        self.deltool_btn.setToolTip(
            "Delete a selection of tools in the Tool Table\n"
            "by first selecting a row(s) in the Tool Table."
        )

        grid2.addWidget(self.addtool_btn, 0, 0)
        # grid2.addWidget(self.copytool_btn, 0, 1)
        grid2.addWidget(self.deltool_btn, 0,2)

        self.empty_label_0 = QtWidgets.QLabel('')
        self.tools_box.addWidget(self.empty_label_0)

        grid3 = QtWidgets.QGridLayout()
        self.tools_box.addLayout(grid3)

        # Overlap
        ovlabel = QtWidgets.QLabel('Overlap:')
        ovlabel.setToolTip(
            "How much (fraction) of the tool width to overlap each tool pass.\n"
            "Example:\n"
            "A value here of 0.25 means 25% from the tool diameter found above.\n\n"
            "Adjust the value starting with lower values\n"
            "and increasing it if areas that should be painted are still \n"
            "not painted.\n"
            "Lower values = faster processing, faster execution on PCB.\n"
            "Higher values = slow processing and slow execution on CNC\n"
            "due of too many paths."
        )
        grid3.addWidget(ovlabel, 1, 0)
        self.paintoverlap_entry = LengthEntry()
        grid3.addWidget(self.paintoverlap_entry, 1, 1)

        # Margin
        marginlabel = QtWidgets.QLabel('Margin:')
        marginlabel.setToolTip(
            "Distance by which to avoid\n"
            "the edges of the polygon to\n"
            "be painted."
        )
        grid3.addWidget(marginlabel, 2, 0)
        self.paintmargin_entry = LengthEntry()
        grid3.addWidget(self.paintmargin_entry, 2, 1)

        # Method
        methodlabel = QtWidgets.QLabel('Method:')
        methodlabel.setToolTip(
            "Algorithm for non-copper clearing:<BR>"
            "<B>Standard</B>: Fixed step inwards.<BR>"
            "<B>Seed-based</B>: Outwards from seed.<BR>"
            "<B>Line-based</B>: Parallel lines."
        )
        grid3.addWidget(methodlabel, 3, 0)
        self.paintmethod_combo = RadioSet([
            {"label": "Standard", "value": "standard"},
            {"label": "Seed-based", "value": "seed"},
            {"label": "Straight lines", "value": "lines"}
        ], orientation='vertical', stretch=False)
        grid3.addWidget(self.paintmethod_combo, 3, 1)

        # Connect lines
        pathconnectlabel = QtWidgets.QLabel("Connect:")
        pathconnectlabel.setToolTip(
            "Draw lines between resulting\n"
            "segments to minimize tool lifts."
        )
        grid3.addWidget(pathconnectlabel, 4, 0)
        self.pathconnect_cb = FCCheckBox()
        grid3.addWidget(self.pathconnect_cb, 4, 1)

        contourlabel = QtWidgets.QLabel("Contour:")
        contourlabel.setToolTip(
            "Cut around the perimeter of the polygon\n"
            "to trim rough edges."
        )
        grid3.addWidget(contourlabel, 5, 0)
        self.paintcontour_cb = FCCheckBox()
        grid3.addWidget(self.paintcontour_cb, 5, 1)

        restlabel = QtWidgets.QLabel("Rest M.:")
        restlabel.setToolTip(
            "If checked, use 'rest machining'.\n"
            "Basically it will clear copper outside PCB features,\n"
            "using the biggest tool and continue with the next tools,\n"
            "from bigger to smaller, to clear areas of copper that\n"
            "could not be cleared by previous tool, until there is\n"
            "no more copper to clear or there are no more tools.\n\n"
            "If not checked, use the standard algorithm."
        )
        grid3.addWidget(restlabel, 6, 0)
        self.rest_cb = FCCheckBox()
        grid3.addWidget(self.rest_cb, 6, 1)

        # Polygon selection
        selectlabel = QtWidgets.QLabel('Selection:')
        selectlabel.setToolTip(
            "How to select the polygons to paint.<BR>"
            "Options:<BR>"
            "- <B>Single</B>: left mouse click on the polygon to be painted.<BR>"
            "- <B>All</B>: paint all polygons."
        )
        grid3.addWidget(selectlabel, 7, 0)
        # grid3 = QtWidgets.QGridLayout()
        self.selectmethod_combo = RadioSet([
            {"label": "Single", "value": "single"},
            {"label": "All", "value": "all"},
            # {"label": "Rectangle", "value": "rectangle"}
        ])
        grid3.addWidget(self.selectmethod_combo, 7, 1)

        # GO Button
        self.generate_paint_button = QtWidgets.QPushButton('Create Paint Geometry')
        self.generate_paint_button.setToolTip(
            "After clicking here, click inside<BR>"
            "the polygon you wish to be painted if <B>Single</B> is selected.<BR>"
            "If <B>All</B>  is selected then the Paint will start after click.<BR>"
            "A new Geometry object with the tool<BR>"
            "paths will be created."
        )
        self.tools_box.addWidget(self.generate_paint_button)

        self.tools_box.addStretch()

        self.obj_name = ""
        self.paint_obj = None

        self.units = ''
        self.paint_tools = {}
        self.tooluid = 0
        # store here the default data for Geometry Data
        self.default_data = {}
        self.default_data.update({
            "name": '_paint',
            "plot": self.app.defaults["geometry_plot"],
            "cutz": self.app.defaults["geometry_cutz"],
            "vtipdia": 0.1,
            "vtipangle": 30,
            "travelz": self.app.defaults["geometry_travelz"],
            "feedrate": self.app.defaults["geometry_feedrate"],
            "feedrate_z": self.app.defaults["geometry_feedrate_z"],
            "feedrate_rapid": self.app.defaults["geometry_feedrate_rapid"],
            "dwell": self.app.defaults["geometry_dwell"],
            "dwelltime": self.app.defaults["geometry_dwelltime"],
            "multidepth": self.app.defaults["geometry_multidepth"],
            "ppname_g": self.app.defaults["geometry_ppname_g"],
            "depthperpass": self.app.defaults["geometry_depthperpass"],
            "extracut": self.app.defaults["geometry_extracut"],
            "toolchange": self.app.defaults["geometry_toolchange"],
            "toolchangez": self.app.defaults["geometry_toolchangez"],
            "endz": self.app.defaults["geometry_endz"],
            "spindlespeed": self.app.defaults["geometry_spindlespeed"],
            "toolchangexy": self.app.defaults["geometry_toolchangexy"],
            "startz": self.app.defaults["geometry_startz"],

            "tooldia": self.app.defaults["tools_painttooldia"],
            "paintmargin": self.app.defaults["tools_paintmargin"],
            "paintmethod": self.app.defaults["tools_paintmethod"],
            "selectmethod": self.app.defaults["tools_selectmethod"],
            "pathconnect": self.app.defaults["tools_pathconnect"],
            "paintcontour": self.app.defaults["tools_paintcontour"],
            "paintoverlap": self.app.defaults["tools_paintoverlap"]
        })

        self.tool_type_item_options = ["C1", "C2", "C3", "C4", "B", "V"]

        ## Signals
        self.addtool_btn.clicked.connect(self.on_tool_add)
        # self.copytool_btn.clicked.connect(lambda: self.on_tool_copy())
        self.tools_table.itemChanged.connect(self.on_tool_edit)
        self.deltool_btn.clicked.connect(self.on_tool_delete)
        self.generate_paint_button.clicked.connect(self.on_paint_button_click)
        self.selectmethod_combo.activated_custom.connect(self.on_radio_selection)


    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, shortcut='ALT+P', **kwargs)

    def run(self):
        FlatCAMTool.run(self)
        self.tools_frame.show()
        self.set_ui()
        self.app.ui.notebook.setTabText(2, "Paint Tool")

    def on_radio_selection(self):
        if self.selectmethod_combo.get_value() == 'single':
            # disable rest-machining for single polygon painting
            self.rest_cb.set_value(False)
            self.rest_cb.setDisabled(True)
            # delete all tools except first row / tool for single polygon painting
            list_to_del = list(range(1, self.tools_table.rowCount()))
            if list_to_del:
                self.on_tool_delete(rows_to_delete=list_to_del)
            # disable addTool and delTool
            self.addtool_entry.setDisabled(True)
            self.addtool_btn.setDisabled(True)
            self.deltool_btn.setDisabled(True)
        else:
            self.rest_cb.setDisabled(False)
            self.addtool_entry.setDisabled(False)
            self.addtool_btn.setDisabled(False)
            self.deltool_btn.setDisabled(False)

    def set_ui(self):
        ## Init the GUI interface
        self.paintmargin_entry.set_value(self.default_data["paintmargin"])
        self.paintmethod_combo.set_value(self.default_data["paintmethod"])
        self.selectmethod_combo.set_value(self.default_data["selectmethod"])
        self.pathconnect_cb.set_value(self.default_data["pathconnect"])
        self.paintcontour_cb.set_value(self.default_data["paintcontour"])
        self.paintoverlap_entry.set_value(self.default_data["paintoverlap"])

        # updated units
        self.units = self.app.general_options_form.general_app_group.units_radio.get_value().upper()

        if self.units == "IN":
            self.addtool_entry.set_value(0.039)
        else:
            self.addtool_entry.set_value(1)

        self.tools_table.setupContextMenu()
        self.tools_table.addContextMenu(
            "Add", lambda: self.on_tool_add(dia=None, muted=None), icon=QtGui.QIcon("share/plus16.png"))
        self.tools_table.addContextMenu(
            "Delete", lambda:
            self.on_tool_delete(rows_to_delete=None, all=None), icon=QtGui.QIcon("share/delete32.png"))

        # set the working variables to a known state
        self.paint_tools.clear()
        self.tooluid = 0

        self.default_data.clear()
        self.default_data.update({
            "name": '_paint',
            "plot": self.app.defaults["geometry_plot"],
            "tooldia": self.app.defaults["geometry_painttooldia"],
            "cutz": self.app.defaults["geometry_cutz"],
            "vtipdia": 0.1,
            "vtipangle": 30,
            "travelz": self.app.defaults["geometry_travelz"],
            "feedrate": self.app.defaults["geometry_feedrate"],
            "feedrate_z": self.app.defaults["geometry_feedrate_z"],
            "feedrate_rapid": self.app.defaults["geometry_feedrate_rapid"],
            "dwell": self.app.defaults["geometry_dwell"],
            "dwelltime": self.app.defaults["geometry_dwelltime"],
            "multidepth": self.app.defaults["geometry_multidepth"],
            "ppname_g": self.app.defaults["geometry_ppname_g"],
            "depthperpass": self.app.defaults["geometry_depthperpass"],
            "extracut": self.app.defaults["geometry_extracut"],
            "toolchange": self.app.defaults["geometry_toolchange"],
            "toolchangez": self.app.defaults["geometry_toolchangez"],
            "endz": self.app.defaults["geometry_endz"],
            "spindlespeed": self.app.defaults["geometry_spindlespeed"],
            "toolchangexy": self.app.defaults["geometry_toolchangexy"],
            "startz": self.app.defaults["geometry_startz"],
            "paintmargin": self.app.defaults["geometry_paintmargin"],
            "paintmethod": self.app.defaults["geometry_paintmethod"],
            "selectmethod": self.app.defaults["geometry_selectmethod"],
            "pathconnect": self.app.defaults["geometry_pathconnect"],
            "paintcontour": self.app.defaults["geometry_paintcontour"],
            "paintoverlap": self.app.defaults["geometry_paintoverlap"]
        })

        # call on self.on_tool_add() counts as an call to self.build_ui()
        # through this, we add a initial row / tool in the tool_table
        self.on_tool_add(self.app.defaults["geometry_painttooldia"], muted=True)

    def build_ui(self):

        try:
            # if connected, disconnect the signal from the slot on item_changed as it creates issues
            self.tools_table.itemChanged.disconnect()
        except:
            pass

        # updated units
        self.units = self.app.general_options_form.general_app_group.units_radio.get_value().upper()

        sorted_tools = []
        for k, v in self.paint_tools.items():
            sorted_tools.append(float('%.4f' % float(v['tooldia'])))
        sorted_tools.sort()

        n = len(sorted_tools)
        self.tools_table.setRowCount(n)
        tool_id = 0

        for tool_sorted in sorted_tools:
            for tooluid_key, tooluid_value in self.paint_tools.items():
                if float('%.4f' % tooluid_value['tooldia']) == tool_sorted:
                    tool_id += 1
                    id = QtWidgets.QTableWidgetItem('%d' % int(tool_id))
                    id.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                    row_no = tool_id - 1
                    self.tools_table.setItem(row_no, 0, id)  # Tool name/id

                    # Make sure that the drill diameter when in MM is with no more than 2 decimals
                    # There are no drill bits in MM with more than 3 decimals diameter
                    # For INCH the decimals should be no more than 3. There are no drills under 10mils
                    if self.units == 'MM':
                        dia = QtWidgets.QTableWidgetItem('%.2f' % tooluid_value['tooldia'])
                    else:
                        dia = QtWidgets.QTableWidgetItem('%.3f' % tooluid_value['tooldia'])

                    dia.setFlags(QtCore.Qt.ItemIsEnabled)

                    tool_type_item = QtWidgets.QComboBox()
                    for item in self.tool_type_item_options:
                        tool_type_item.addItem(item)
                        tool_type_item.setStyleSheet('background-color: rgb(255,255,255)')
                    idx = tool_type_item.findText(tooluid_value['tool_type'])
                    tool_type_item.setCurrentIndex(idx)

                    tool_uid_item = QtWidgets.QTableWidgetItem(str(int(tooluid_key)))

                    self.tools_table.setItem(row_no, 1, dia)  # Diameter
                    self.tools_table.setCellWidget(row_no, 2, tool_type_item)

                    ### REMEMBER: THIS COLUMN IS HIDDEN IN OBJECTUI.PY ###
                    self.tools_table.setItem(row_no, 3, tool_uid_item)  # Tool unique ID

        # make the diameter column editable
        for row in range(tool_id):
            self.tools_table.item(row, 1).setFlags(
                QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

        # all the tools are selected by default
        self.tools_table.selectColumn(0)
        #
        self.tools_table.resizeColumnsToContents()
        self.tools_table.resizeRowsToContents()

        vertical_header = self.tools_table.verticalHeader()
        vertical_header.hide()
        self.tools_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        horizontal_header = self.tools_table.horizontalHeader()
        horizontal_header.setMinimumSectionSize(10)
        horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(0, 20)
        horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)

        # self.tools_table.setSortingEnabled(True)
        # sort by tool diameter
        # self.tools_table.sortItems(1)

        self.tools_table.setMinimumHeight(self.tools_table.getHeight())
        self.tools_table.setMaximumHeight(self.tools_table.getHeight())

        # we reactivate the signals after the after the tool adding as we don't need to see the tool been populated
        self.tools_table.itemChanged.connect(self.on_tool_edit)

    def on_tool_add(self, dia=None, muted=None):

        try:
            self.tools_table.itemChanged.disconnect()
        except:
            pass

        if dia:
            tool_dia = dia
        else:
            tool_dia = self.addtool_entry.get_value()
            if tool_dia is None:
                self.build_ui()
                self.app.inform.emit("[warning_notcl] Please enter a tool diameter to add, in Float format.")
                return

        # construct a list of all 'tooluid' in the self.tools
        tool_uid_list = []
        for tooluid_key in self.paint_tools:
            tool_uid_item = int(tooluid_key)
            tool_uid_list.append(tool_uid_item)

        # find maximum from the temp_uid, add 1 and this is the new 'tooluid'
        if not tool_uid_list:
            max_uid = 0
        else:
            max_uid = max(tool_uid_list)
        self.tooluid = int(max_uid + 1)

        tool_dias = []
        for k, v in self.paint_tools.items():
            for tool_v in v.keys():
                if tool_v == 'tooldia':
                    tool_dias.append(float('%.4f' % v[tool_v]))

        if float('%.4f' % tool_dia) in tool_dias:
            if muted is None:
                self.app.inform.emit("[warning_notcl]Adding tool cancelled. Tool already in Tool Table.")
            self.tools_table.itemChanged.connect(self.on_tool_edit)
            return
        else:
            if muted is None:
                self.app.inform.emit("[success] New tool added to Tool Table.")
            self.paint_tools.update({
                int(self.tooluid): {
                    'tooldia': float('%.4f' % tool_dia),
                    'offset': 'Path',
                    'offset_value': 0.0,
                    'type': 'Iso',
                    'tool_type': 'V',
                    'data': dict(self.default_data),
                    'solid_geometry': []
                }
            })

        self.build_ui()

    def on_tool_edit(self):
        try:
            self.tools_table.itemChanged.disconnect()
        except:
            pass

        tool_dias = []
        for k, v in self.paint_tools.items():
            for tool_v in v.keys():
                if tool_v == 'tooldia':
                    tool_dias.append(float('%.4f' % v[tool_v]))

        for row in range(self.tools_table.rowCount()):
            new_tool_dia = float(self.tools_table.item(row, 1).text())
            tooluid = int(self.tools_table.item(row, 3).text())

            # identify the tool that was edited and get it's tooluid
            if new_tool_dia not in tool_dias:
                self.paint_tools[tooluid]['tooldia'] = new_tool_dia
                self.app.inform.emit("[success] Tool from Tool Table was edited.")
                self.build_ui()
                return
            else:
                # identify the old tool_dia and restore the text in tool table
                for k, v in self.paint_tools.items():
                    if k == tooluid:
                        old_tool_dia = v['tooldia']
                        break
                restore_dia_item = self.tools_table.item(row, 1)
                restore_dia_item.setText(str(old_tool_dia))
                self.app.inform.emit("[warning_notcl] Edit cancelled. New diameter value is already in the Tool Table.")
        self.build_ui()

    # def on_tool_copy(self, all=None):
    #     try:
    #         self.tools_table.itemChanged.disconnect()
    #     except:
    #         pass
    #
    #     # find the tool_uid maximum value in the self.tools
    #     uid_list = []
    #     for key in self.paint_tools:
    #         uid_list.append(int(key))
    #     try:
    #         max_uid = max(uid_list, key=int)
    #     except ValueError:
    #         max_uid = 0
    #
    #     if all is None:
    #         if self.tools_table.selectedItems():
    #             for current_row in self.tools_table.selectedItems():
    #                 # sometime the header get selected and it has row number -1
    #                 # we don't want to do anything with the header :)
    #                 if current_row.row() < 0:
    #                     continue
    #                 try:
    #                     tooluid_copy = int(self.tools_table.item(current_row.row(), 3).text())
    #                     max_uid += 1
    #                     self.paint_tools[int(max_uid)] = dict(self.paint_tools[tooluid_copy])
    #                     for td in self.paint_tools:
    #                         print("COPIED", self.paint_tools[td])
    #                     self.build_ui()
    #                 except AttributeError:
    #                     self.app.inform.emit("[warning_notcl]Failed. Select a tool to copy.")
    #                     self.build_ui()
    #                     return
    #                 except Exception as e:
    #                     log.debug("on_tool_copy() --> " + str(e))
    #             # deselect the table
    #             # self.ui.geo_tools_table.clearSelection()
    #         else:
    #             self.app.inform.emit("[warning_notcl]Failed. Select a tool to copy.")
    #             self.build_ui()
    #             return
    #     else:
    #         # we copy all tools in geo_tools_table
    #         try:
    #             temp_tools = dict(self.paint_tools)
    #             max_uid += 1
    #             for tooluid in temp_tools:
    #                 self.paint_tools[int(max_uid)] = dict(temp_tools[tooluid])
    #             temp_tools.clear()
    #             self.build_ui()
    #         except Exception as e:
    #             log.debug("on_tool_copy() --> " + str(e))
    #
    #     self.app.inform.emit("[success] Tool was copied in the Tool Table.")

    def on_tool_delete(self, rows_to_delete=None, all=None):
        try:
            self.tools_table.itemChanged.disconnect()
        except:
            pass

        deleted_tools_list = []

        if all:
            self.paint_tools.clear()
            self.build_ui()
            return

        if rows_to_delete:
            try:
                for row in rows_to_delete:
                    tooluid_del = int(self.tools_table.item(row, 3).text())
                    deleted_tools_list.append(tooluid_del)
            except TypeError:
                deleted_tools_list.append(rows_to_delete)

            for t in deleted_tools_list:
                self.paint_tools.pop(t, None)
            self.build_ui()
            return

        try:
            if self.tools_table.selectedItems():
                for row_sel in self.tools_table.selectedItems():
                    row = row_sel.row()
                    if row < 0:
                        continue
                    tooluid_del = int(self.tools_table.item(row, 3).text())
                    deleted_tools_list.append(tooluid_del)

                for t in deleted_tools_list:
                    self.paint_tools.pop(t, None)

        except AttributeError:
            self.app.inform.emit("[warning_notcl]Delete failed. Select a tool to delete.")
            return
        except Exception as e:
            log.debug(str(e))

        self.app.inform.emit("[success] Tool(s) deleted from Tool Table.")
        self.build_ui()

    def on_paint_button_click(self):
        self.app.report_usage("geometry_on_paint_button")

        self.app.inform.emit("[warning_notcl]Click inside the desired polygon.")

        overlap = self.paintoverlap_entry.get_value()
        connect = self.pathconnect_cb.get_value()
        contour = self.paintcontour_cb.get_value()
        select_method = self.selectmethod_combo.get_value()

        self.obj_name = self.object_combo.currentText()

        # Get source object.
        try:
            self.paint_obj = self.app.collection.get_by_name(str(self.obj_name))
        except:
            self.app.inform.emit("[error_notcl]Could not retrieve object: %s" % self.obj_name)
            return

        if self.paint_obj is None:
            self.app.inform.emit("[error_notcl]Object not found: %s" % self.paint_obj)
            return

        o_name = '%s_multitool_paint' % (self.obj_name)

        if select_method == "all":
            self.paint_poly_all(self.paint_obj,
                                outname=o_name,
                                overlap=overlap,
                                connect=connect,
                                contour=contour)

        if select_method == "single":
            self.app.inform.emit("[warning_notcl]Click inside the desired polygon.")

            # use the first tool in the tool table; get the diameter
            tooldia = float('%.4f' % float(self.tools_table.item(0, 1).text()))

            # To be called after clicking on the plot.
            def doit(event):
                # do paint single only for left mouse clicks
                if event.button == 1:
                    self.app.inform.emit("Painting polygon...")
                    self.app.plotcanvas.vis_disconnect('mouse_press', doit)
                    pos = self.app.plotcanvas.vispy_canvas.translate_coords(event.pos)
                    self.paint_poly(self.paint_obj,
                                    inside_pt=[pos[0], pos[1]],
                                    tooldia=tooldia,
                                    overlap=overlap,
                                    connect=connect,
                                    contour=contour)

            self.app.plotcanvas.vis_connect('mouse_press', doit)

    def paint_poly(self, obj, inside_pt, tooldia, overlap,
                    outname=None, connect=True,
                    contour=True):
        """
        Paints a polygon selected by clicking on its interior.

        Note:
            * The margin is taken directly from the form.

        :param inside_pt: [x, y]
        :param tooldia: Diameter of the painting tool
        :param overlap: Overlap of the tool between passes.
        :param outname: Name of the resulting Geometry Object.
        :param connect: Connect lines to avoid tool lifts.
        :param contour: Paint around the edges.
        :return: None
        """

        # Which polygon.
        # poly = find_polygon(self.solid_geometry, inside_pt)
        poly = obj.find_polygon(inside_pt)
        paint_method = self.paintmethod_combo.get_value()
        paint_margin = self.paintmargin_entry.get_value()

        # No polygon?
        if poly is None:
            self.app.log.warning('No polygon found.')
            self.app.inform.emit('[warning] No polygon found.')
            return

        proc = self.app.proc_container.new("Painting polygon.")

        name = outname if outname else self.obj_name + "_paint"

        # Initializes the new geometry object
        def gen_paintarea(geo_obj, app_obj):
            assert isinstance(geo_obj, FlatCAMGeometry), \
                "Initializer expected a FlatCAMGeometry, got %s" % type(geo_obj)
            # assert isinstance(app_obj, App)

            def paint_p(polyg):
                if paint_method == "seed":
                    # Type(cp) == FlatCAMRTreeStorage | None
                    cp = self.clear_polygon2(polyg,
                                             tooldia=tooldia,
                                             steps_per_circle=self.app.defaults["geometry_circle_steps"],
                                             overlap=overlap,
                                             contour=contour,
                                             connect=connect)

                elif paint_method == "lines":
                    # Type(cp) == FlatCAMRTreeStorage | None
                    cp = self.clear_polygon3(polyg,
                                             tooldia=tooldia,
                                             steps_per_circle=self.app.defaults["geometry_circle_steps"],
                                             overlap=overlap,
                                             contour=contour,
                                             connect=connect)

                else:
                    # Type(cp) == FlatCAMRTreeStorage | None
                    cp = self.clear_polygon(polyg,
                                             tooldia=tooldia,
                                             steps_per_circle=self.app.defaults["geometry_circle_steps"],
                                             overlap=overlap,
                                             contour=contour,
                                             connect=connect)

                if cp is not None:
                    geo_obj.solid_geometry += list(cp.get_objects())
                    return cp
                else:
                    self.app.inform.emit('[error_notcl] Geometry could not be painted completely')
                    return None

            geo_obj.solid_geometry = []
            try:
                poly_buf = poly.buffer(-paint_margin)
                if isinstance(poly_buf, MultiPolygon):
                    cp = []
                    for pp in poly_buf:
                        cp.append(paint_p(pp))
                else:
                    cp = paint_p(poly_buf)
            except Exception as e:
                log.debug("Could not Paint the polygons. %s" % str(e))
                self.app.inform.emit(
                    "[error] Could not do Paint. Try a different combination of parameters. "
                    "Or a different strategy of paint\n%s" % str(e))
                return

            if cp is not None:
                if isinstance(cp, list):
                    for x in cp:
                        geo_obj.solid_geometry += list(x.get_objects())
                else:
                    geo_obj.solid_geometry = list(cp.get_objects())

            geo_obj.options["cnctooldia"] = tooldia
            # this turn on the FlatCAMCNCJob plot for multiple tools
            geo_obj.multigeo = False
            geo_obj.multitool = True

            current_uid = int(self.tools_table.item(0, 3).text())
            for k, v in self.paint_tools.items():
                if k == current_uid:
                    v['data']['name'] = name

            geo_obj.tools = dict(self.paint_tools)

            # Experimental...
            # print("Indexing...", end=' ')
            # geo_obj.make_index()
            # if errors == 0:
            #     print("[success] Paint single polygon Done")
            #     self.app.inform.emit("[success] Paint single polygon Done")
            # else:
            #     print("[WARNING] Paint single polygon done with errors")
            #     self.app.inform.emit("[warning] Paint single polygon done with errors. "
            #                          "%d area(s) could not be painted.\n"
            #                          "Use different paint parameters or edit the paint geometry and correct"
            #                          "the issue."
            #                          % errors)

        def job_thread(app_obj):
            try:
                app_obj.new_object("geometry", name, gen_paintarea)
            except Exception as e:
                proc.done()
                self.app.inform.emit('[error_notcl] PaintTool.paint_poly() --> %s' % str(e))
                return
            proc.done()
            # focus on Selected Tab
            self.app.ui.notebook.setCurrentWidget(self.app.ui.selected_tab)

        self.app.inform.emit("Polygon Paint started ...")

        # Promise object with the new name
        self.app.collection.promise(name)

        # Background
        self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})

    def paint_poly_all(self, obj, overlap, outname=None,
                       connect=True, contour=True):
        """
        Paints all polygons in this object.

        :param tooldia:
        :param overlap:
        :param outname:
        :param connect: Connect lines to avoid tool lifts.
        :param contour: Paint around the edges.
        :return:
        """
        paint_method = self.paintmethod_combo.get_value()
        paint_margin = self.paintmargin_entry.get_value()

        proc = self.app.proc_container.new("Painting polygon.")

        name = outname if outname else self.obj_name + "_paint"
        over = overlap
        conn = connect
        cont = contour

        # This is a recursive generator of individual Polygons.
        # Note: Double check correct implementation. Might exit
        #       early if it finds something that is not a Polygon?
        # def recurse(geo):
        #     try:
        #         for subg in geo:
        #             for subsubg in recurse(subg):
        #                 yield subsubg
        #     except TypeError:
        #         if isinstance(geo, Polygon):
        #             yield geo
        #
        #     raise StopIteration

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
                self.flat_geometry = []

            ## If iterable, expand recursively.
            try:
                for geo in geometry:
                    if geo is not None:
                        recurse(geometry=geo, reset=False)

            ## Not iterable, do the actual indexing and add.
            except TypeError:
                self.flat_geometry.append(geometry)

            return self.flat_geometry

        # Initializes the new geometry object
        def gen_paintarea(geo_obj, app_obj):
            assert isinstance(geo_obj, FlatCAMGeometry), \
                "Initializer expected a FlatCAMGeometry, got %s" % type(geo_obj)

            sorted_tools = []
            for row in range(self.tools_table.rowCount()):
                sorted_tools.append(float(self.tools_table.item(row, 1).text()))
            sorted_tools.sort(reverse=True)

            total_geometry = []
            current_uid = int(1)
            geo_obj.solid_geometry = []
            for tool_dia in sorted_tools:
                # find the tooluid associated with the current tool_dia so we know where to add the tool solid_geometry
                for k, v in self.paint_tools.items():
                    if float('%.4f' % v['tooldia']) == float('%.4f' % tool_dia):
                        current_uid = int(k)
                        break

                for geo in recurse(obj.solid_geometry):
                    try:
                        if not isinstance(geo, Polygon):
                            geo = Polygon(geo)
                        poly_buf = geo.buffer(-paint_margin)

                        if paint_method == "seed":
                            # Type(cp) == FlatCAMRTreeStorage | None
                            cp = self.clear_polygon2(poly_buf,
                                                     tooldia=tool_dia,
                                                     steps_per_circle=self.app.defaults["geometry_circle_steps"],
                                                     overlap=over,
                                                     contour=cont,
                                                     connect=conn)

                        elif paint_method == "lines":
                            # Type(cp) == FlatCAMRTreeStorage | None
                            cp = self.clear_polygon3(poly_buf,
                                                     tooldia=tool_dia,
                                                     steps_per_circle=self.app.defaults["geometry_circle_steps"],
                                                     overlap=over,
                                                     contour=cont,
                                                     connect=conn)

                        else:
                            # Type(cp) == FlatCAMRTreeStorage | None
                            cp = self.clear_polygon(poly_buf,
                                                     tooldia=tool_dia,
                                                     steps_per_circle=self.app.defaults["geometry_circle_steps"],
                                                     overlap=over,
                                                     contour=cont,
                                                     connect=conn)

                        if cp is not None:
                            total_geometry += list(cp.get_objects())
                    except Exception as e:
                        log.debug("Could not Paint the polygons. %s" % str(e))
                        self.app.inform.emit(
                            "[error] Could not do Paint All. Try a different combination of parameters. "
                            "Or a different Method of paint\n%s" % str(e))
                        return

                # add the solid_geometry to the current too in self.paint_tools dictionary and then reset the
                # temporary list that stored that solid_geometry
                self.paint_tools[current_uid]['solid_geometry'] = deepcopy(total_geometry)

                self.paint_tools[current_uid]['data']['name'] = name
                total_geometry[:] = []

            geo_obj.options["cnctooldia"] = tool_dia
            # this turn on the FlatCAMCNCJob plot for multiple tools
            geo_obj.multigeo = True
            geo_obj.multitool = True
            geo_obj.tools.clear()
            geo_obj.tools = dict(self.paint_tools)

            # test if at least one tool has solid_geometry. If no tool has solid_geometry we raise an Exception
            has_solid_geo = 0
            for tooluid in geo_obj.tools:
                if geo_obj.tools[tooluid]['solid_geometry']:
                    has_solid_geo += 1
            if has_solid_geo == 0:
                self.app.inform.emit("[error] There is no Painting Geometry in the file.\n"
                                      "Usually it means that the tool diameter is too big for the painted geometry.\n"
                                      "Change the painting parameters and try again.")
                return

            # Experimental...
            # print("Indexing...", end=' ')
            # geo_obj.make_index()

            self.app.inform.emit("[success] Paint All Done.")

        # Initializes the new geometry object
        def gen_paintarea_rest_machining(geo_obj, app_obj):
            assert isinstance(geo_obj, FlatCAMGeometry), \
                "Initializer expected a FlatCAMGeometry, got %s" % type(geo_obj)

            sorted_tools = []
            for row in range(self.tools_table.rowCount()):
                sorted_tools.append(float(self.tools_table.item(row, 1).text()))
            sorted_tools.sort(reverse=True)

            cleared_geo = []
            current_uid = int(1)
            geo_obj.solid_geometry = []

            for tool_dia in sorted_tools:
                for geo in recurse(obj.solid_geometry):
                    try:
                        geo = Polygon(geo) if not isinstance(geo, Polygon) else geo
                        poly_buf = geo.buffer(-paint_margin)

                        if paint_method == "standard":
                            # Type(cp) == FlatCAMRTreeStorage | None
                            cp = self.clear_polygon(poly_buf, tooldia=tool_dia,
                                                     steps_per_circle=self.app.defaults["geometry_circle_steps"],
                                                     overlap=over, contour=cont, connect=conn)

                        elif paint_method == "seed":
                            # Type(cp) == FlatCAMRTreeStorage | None
                            cp = self.clear_polygon2(poly_buf, tooldia=tool_dia,
                                                     steps_per_circle=self.app.defaults["geometry_circle_steps"],
                                                     overlap=over, contour=cont, connect=conn)

                        elif paint_method == "lines":
                            # Type(cp) == FlatCAMRTreeStorage | None
                            cp = self.clear_polygon3(poly_buf, tooldia=tool_dia,
                                                    steps_per_circle=self.app.defaults["geometry_circle_steps"],
                                                    overlap=over, contour=cont, connect=conn)

                        if cp is not None:
                            cleared_geo += list(cp.get_objects())

                    except Exception as e:
                        log.debug("Could not Paint the polygons. %s" % str(e))
                        self.app.inform.emit(
                            "[error] Could not do Paint All. Try a different combination of parameters. "
                            "Or a different Method of paint\n%s" % str(e))
                        return

                # find the tooluid associated with the current tool_dia so we know where to add the tool solid_geometry
                for k, v in self.paint_tools.items():
                    if float('%.4f' % v['tooldia']) == float('%.4f' % tool_dia):
                        current_uid = int(k)
                        break

                # add the solid_geometry to the current too in self.paint_tools dictionary and then reset the
                # temporary list that stored that solid_geometry
                self.paint_tools[current_uid]['solid_geometry'] = deepcopy(cleared_geo)

                self.paint_tools[current_uid]['data']['name'] = name
                cleared_geo[:] = []

            geo_obj.options["cnctooldia"] = tool_dia
            # this turn on the FlatCAMCNCJob plot for multiple tools
            geo_obj.multigeo = True
            geo_obj.multitool = True
            geo_obj.tools.clear()
            geo_obj.tools = dict(self.paint_tools)

            # test if at least one tool has solid_geometry. If no tool has solid_geometry we raise an Exception
            has_solid_geo = 0
            for tooluid in geo_obj.tools:
                if geo_obj.tools[tooluid]['solid_geometry']:
                    has_solid_geo += 1
            if has_solid_geo == 0:
                self.app.inform.emit("[error_notcl] There is no Painting Geometry in the file.\n"
                                      "Usually it means that the tool diameter is too big for the painted geometry.\n"
                                      "Change the painting parameters and try again.")
                return

            # Experimental...
            # print("Indexing...", end=' ')
            # geo_obj.make_index()

            self.app.inform.emit("[success] Paint All with Rest-Machining Done.")

        def job_thread(app_obj):
            try:
                if self.rest_cb.isChecked():
                    app_obj.new_object("geometry", name, gen_paintarea_rest_machining)
                else:
                    app_obj.new_object("geometry", name, gen_paintarea)
            except Exception as e:
                proc.done()
                traceback.print_stack()
                return
            proc.done()
            # focus on Selected Tab
            self.app.ui.notebook.setCurrentWidget(self.app.ui.selected_tab)

        self.app.inform.emit("Polygon Paint started ...")

        # Promise object with the new name
        self.app.collection.promise(name)

        # Background
        self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})
