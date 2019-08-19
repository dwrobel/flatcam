# ########################################################## ##
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# File Modified by: Marius Adrian Stanciu (c)              #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ########################################################## ##

from FlatCAMTool import FlatCAMTool
from copy import copy, deepcopy
from ObjectCollection import *
import time
from shapely.geometry import base

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class NonCopperClear(FlatCAMTool, Gerber):

    toolName = _("Non-Copper Clearing")

    def __init__(self, app):
        self.app = app

        FlatCAMTool.__init__(self, app)
        Gerber.__init__(self, steps_per_circle=self.app.defaults["gerber_circle_steps"])

        self.tools_frame = QtWidgets.QFrame()
        self.tools_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.tools_frame)
        self.tools_box = QtWidgets.QVBoxLayout()
        self.tools_box.setContentsMargins(0, 0, 0, 0)
        self.tools_frame.setLayout(self.tools_box)

        # ## Title
        title_label = QtWidgets.QLabel("%s" % self.toolName)
        title_label.setStyleSheet("""
                        QLabel
                        {
                            font-size: 16px;
                            font-weight: bold;
                        }
                        """)
        self.tools_box.addWidget(title_label)

        # ## Form Layout
        form_layout = QtWidgets.QFormLayout()
        self.tools_box.addLayout(form_layout)

        # ## Object
        self.object_combo = QtWidgets.QComboBox()
        self.object_combo.setModel(self.app.collection)
        self.object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.object_combo.setCurrentIndex(1)

        self.object_label = QtWidgets.QLabel("Gerber:")
        self.object_label.setToolTip(
            _("Gerber object to be cleared of excess copper.                        ")
        )
        e_lab_0 = QtWidgets.QLabel('')

        form_layout.addRow(self.object_label, self.object_combo)
        form_layout.addRow(e_lab_0)

        #### Tools ## ##
        self.tools_table_label = QtWidgets.QLabel('<b>%s</b>' % _('Tools Table'))
        self.tools_table_label.setToolTip(
            _("Tools pool from which the algorithm\n"
              "will pick the ones used for copper clearing.")
        )
        self.tools_box.addWidget(self.tools_table_label)

        self.tools_table = FCTable()
        self.tools_box.addWidget(self.tools_table)

        self.tools_table.setColumnCount(4)
        self.tools_table.setHorizontalHeaderLabels(['#', _('Diameter'), _('TT'), ''])
        self.tools_table.setColumnHidden(3, True)
        self.tools_table.setSortingEnabled(False)
        # self.tools_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        self.tools_table.horizontalHeaderItem(0).setToolTip(
            _("This is the Tool Number.\n"
              "Non copper clearing will start with the tool with the biggest \n"
              "diameter, continuing until there are no more tools.\n"
              "Only tools that create NCC clearing geometry will still be present\n"
              "in the resulting geometry. This is because with some tools\n"
              "this function will not be able to create painting geometry.")
            )
        self.tools_table.horizontalHeaderItem(1).setToolTip(
            _("Tool Diameter. It's value (in current FlatCAM units) \n"
              "is the cut width into the material."))

        self.tools_table.horizontalHeaderItem(2).setToolTip(
            _("The Tool Type (TT) can be:<BR>"
              "- <B>Circular</B> with 1 ... 4 teeth -> it is informative only. Being circular, <BR>"
              "the cut width in material is exactly the tool diameter.<BR>"
              "- <B>Ball</B> -> informative only and make reference to the Ball type endmill.<BR>"
              "- <B>V-Shape</B> -> it will disable de Z-Cut parameter in the resulting geometry UI form "
              "and enable two additional UI form fields in the resulting geometry: V-Tip Dia and "
              "V-Tip Angle. Adjusting those two values will adjust the Z-Cut parameter such "
              "as the cut width into material will be equal with the value in the Tool Diameter "
              "column of this table.<BR>"
              "Choosing the <B>V-Shape</B> Tool Type automatically will select the Operation Type "
              "in the resulting geometry as Isolation."))

        self.ncc_order_label = QtWidgets.QLabel('<b>%s:</b>' % _('Tool order'))
        self.ncc_order_label.setToolTip(_("This set the way that the tools in the tools table are used\n"
                                          "for copper clearing.\n"
                                          "'No' --> means that the used order is the one in the tool table\n"
                                          "'Forward' --> means that the tools will be ordered from small to big\n"
                                          "'Reverse' --> menas that the tools will ordered from big to small\n\n"
                                          "WARNING: using rest machining will automatically set the order\n"
                                          "in reverse and disable this control."))

        self.ncc_order_radio = RadioSet([{'label': _('No'), 'value': 'no'},
                                         {'label': _('Forward'), 'value': 'fwd'},
                                         {'label': _('Reverse'), 'value': 'rev'}])
        self.ncc_order_radio.setToolTip(_("This set the way that the tools in the tools table are used\n"
                                          "for copper clearing.\n"
                                          "'No' --> means that the used order is the one in the tool table\n"
                                          "'Forward' --> means that the tools will be ordered from small to big\n"
                                          "'Reverse' --> menas that the tools will ordered from big to small\n\n"
                                          "WARNING: using rest machining will automatically set the order\n"
                                          "in reverse and disable this control."))
        form = QtWidgets.QFormLayout()
        self.tools_box.addLayout(form)
        form.addRow(QtWidgets.QLabel(''), QtWidgets.QLabel(''))
        form.addRow(self.ncc_order_label, self.ncc_order_radio)

        # ### Add a new Tool ####
        self.addtool_entry_lbl = QtWidgets.QLabel('<b>%s:</b>' % _('Tool Dia'))
        self.addtool_entry_lbl.setToolTip(
            _("Diameter for the new tool to add in the Tool Table")
        )
        self.addtool_entry = FCEntry2()
        form.addRow(self.addtool_entry_lbl, self.addtool_entry)

        grid2 = QtWidgets.QGridLayout()
        self.tools_box.addLayout(grid2)

        self.addtool_btn = QtWidgets.QPushButton(_('Add'))
        self.addtool_btn.setToolTip(
            _("Add a new tool to the Tool Table\n"
              "with the diameter specified above.")
        )

        # self.copytool_btn = QtWidgets.QPushButton('Copy')
        # self.copytool_btn.setToolTip(
        #     "Copy a selection of tools in the Tool Table\n"
        #     "by first selecting a row in the Tool Table."
        # )

        self.deltool_btn = QtWidgets.QPushButton(_('Delete'))
        self.deltool_btn.setToolTip(
            _("Delete a selection of tools in the Tool Table\n"
              "by first selecting a row(s) in the Tool Table.")
        )

        grid2.addWidget(self.addtool_btn, 0, 0)
        # grid2.addWidget(self.copytool_btn, 0, 1)
        grid2.addWidget(self.deltool_btn, 0, 2)

        self.empty_label_0 = QtWidgets.QLabel('')
        self.tools_box.addWidget(self.empty_label_0)

        grid3 = QtWidgets.QGridLayout()
        self.tools_box.addLayout(grid3)

        e_lab_1 = QtWidgets.QLabel('<b>%s:</b>' % _("Parameters"))
        grid3.addWidget(e_lab_1, 0, 0)

        nccoverlabel = QtWidgets.QLabel(_('Overlap Rate:'))
        nccoverlabel.setToolTip(
            _("How much (fraction) of the tool width to overlap each tool pass.\n"
              "Example:\n"
              "A value here of 0.25 means 25% from the tool diameter found above.\n\n"
              "Adjust the value starting with lower values\n"
              "and increasing it if areas that should be cleared are still \n"
              "not cleared.\n"
              "Lower values = faster processing, faster execution on PCB.\n"
              "Higher values = slow processing and slow execution on CNC\n"
              "due of too many paths.")
        )
        grid3.addWidget(nccoverlabel, 1, 0)
        self.ncc_overlap_entry = FCEntry()
        grid3.addWidget(self.ncc_overlap_entry, 1, 1)

        nccmarginlabel = QtWidgets.QLabel('%s:' % _('Margin'))
        nccmarginlabel.setToolTip(
            _("Bounding box margin.")
        )
        grid3.addWidget(nccmarginlabel, 2, 0)
        self.ncc_margin_entry = FCEntry()
        grid3.addWidget(self.ncc_margin_entry, 2, 1)

        # Method
        methodlabel = QtWidgets.QLabel('%s:' % _('Method'))
        methodlabel.setToolTip(
            _("Algorithm for non-copper clearing:<BR>"
              "<B>Standard</B>: Fixed step inwards.<BR>"
              "<B>Seed-based</B>: Outwards from seed.<BR>"
              "<B>Line-based</B>: Parallel lines.")
        )
        grid3.addWidget(methodlabel, 3, 0)
        self.ncc_method_radio = RadioSet([
            {"label": _("Standard"), "value": "standard"},
            {"label": _("Seed-based"), "value": "seed"},
            {"label": _("Straight lines"), "value": "lines"}
        ], orientation='vertical', stretch=False)
        grid3.addWidget(self.ncc_method_radio, 3, 1)

        # Connect lines
        pathconnectlabel = QtWidgets.QLabel('%s:' % _("Connect"))
        pathconnectlabel.setToolTip(
            _("Draw lines between resulting\n"
              "segments to minimize tool lifts.")
        )
        grid3.addWidget(pathconnectlabel, 4, 0)
        self.ncc_connect_cb = FCCheckBox()
        grid3.addWidget(self.ncc_connect_cb, 4, 1)

        contourlabel = QtWidgets.QLabel('%s:' % _("Contour"))
        contourlabel.setToolTip(
            _("Cut around the perimeter of the polygon\n"
              "to trim rough edges.")
        )
        grid3.addWidget(contourlabel, 5, 0)
        self.ncc_contour_cb = FCCheckBox()
        grid3.addWidget(self.ncc_contour_cb, 5, 1)

        restlabel = QtWidgets.QLabel('%s:' % _("Rest M."))
        restlabel.setToolTip(
            _("If checked, use 'rest machining'.\n"
              "Basically it will clear copper outside PCB features,\n"
              "using the biggest tool and continue with the next tools,\n"
              "from bigger to smaller, to clear areas of copper that\n"
              "could not be cleared by previous tool, until there is\n"
              "no more copper to clear or there are no more tools.\n"
              "If not checked, use the standard algorithm.")
        )
        grid3.addWidget(restlabel, 6, 0)
        self.ncc_rest_cb = FCCheckBox()
        grid3.addWidget(self.ncc_rest_cb, 6, 1)

        # ## NCC Offset choice
        self.ncc_offset_choice_label = QtWidgets.QLabel('%s:' % _("Offset"))
        self.ncc_offset_choice_label.setToolTip(
            _("If used, it will add an offset to the copper features.\n"
              "The copper clearing will finish to a distance\n"
              "from the copper features.\n"
              "The value can be between 0 and 10 FlatCAM units.")
        )
        grid3.addWidget(self.ncc_offset_choice_label, 7, 0)
        self.ncc_choice_offset_cb = FCCheckBox()
        grid3.addWidget(self.ncc_choice_offset_cb, 7, 1)

        # ## NCC Offset value
        self.ncc_offset_label = QtWidgets.QLabel('%s:' % _("Offset value"))
        self.ncc_offset_label.setToolTip(
            _("If used, it will add an offset to the copper features.\n"
              "The copper clearing will finish to a distance\n"
              "from the copper features.\n"
              "The value can be between 0 and 10 FlatCAM units.")
        )
        grid3.addWidget(self.ncc_offset_label, 8, 0)
        self.ncc_offset_spinner = FCDoubleSpinner()
        self.ncc_offset_spinner.set_range(0.00, 10.00)
        self.ncc_offset_spinner.set_precision(4)
        self.ncc_offset_spinner.setWrapping(True)

        units = self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().upper()
        if units == 'MM':
            self.ncc_offset_spinner.setSingleStep(0.1)
        else:
            self.ncc_offset_spinner.setSingleStep(0.01)

        grid3.addWidget(self.ncc_offset_spinner, 8, 1)

        self.ncc_offset_label.hide()
        self.ncc_offset_spinner.hide()

        # ## Reference
        self.reference_radio = RadioSet([{'label': _('Itself'), 'value': 'itself'},
                                         {'label': _('Box'), 'value': 'box'}])
        self.reference_label = QtWidgets.QLabel(_("Reference:"))
        self.reference_label.setToolTip(
            _("When choosing the 'Itself' option the non copper clearing extent\n"
              "is based on the object that is copper cleared.\n "
              "Choosing the 'Box' option will do non copper clearing within the box\n"
              "specified by another object different than the one that is copper cleared.")
        )
        grid3.addWidget(self.reference_label, 9, 0)
        grid3.addWidget(self.reference_radio, 9, 1)

        grid4 = QtWidgets.QGridLayout()
        self.tools_box.addLayout(grid4)

        self.box_combo_type_label = QtWidgets.QLabel('%s:' % _("Ref. Type"))
        self.box_combo_type_label.setToolTip(
            _("The type of FlatCAM object to be used as non copper clearing reference.\n"
              "It can be Gerber, Excellon or Geometry.")
        )
        self.box_combo_type = QtWidgets.QComboBox()
        self.box_combo_type.addItem(_("Gerber   Reference Box Object"))
        self.box_combo_type.addItem(_("Excellon Reference Box Object"))
        self.box_combo_type.addItem(_("Geometry Reference Box Object"))

        grid4.addWidget(self.box_combo_type_label, 0, 0)
        grid4.addWidget(self.box_combo_type, 0, 1)

        self.box_combo_label = QtWidgets.QLabel('%s:' % _("Ref. Object"))
        self.box_combo_label.setToolTip(
            _("The FlatCAM object to be used as non copper clearing reference.")
        )
        self.box_combo = QtWidgets.QComboBox()
        self.box_combo.setModel(self.app.collection)
        self.box_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.box_combo.setCurrentIndex(1)
        grid4.addWidget(self.box_combo_label, 1, 0)
        grid4.addWidget(self.box_combo, 1, 1)

        self.box_combo.hide()
        self.box_combo_label.hide()
        self.box_combo_type.hide()
        self.box_combo_type_label.hide()

        self.generate_ncc_button = QtWidgets.QPushButton(_('Generate Geometry'))
        self.generate_ncc_button.setToolTip(
            _("Create the Geometry Object\n"
              "for non-copper routing.")
        )
        self.tools_box.addWidget(self.generate_ncc_button)

        self.units = ''
        self.ncc_tools = {}
        self.tooluid = 0
        # store here the default data for Geometry Data
        self.default_data = {}

        self.obj_name = ""
        self.ncc_obj = None

        self.bound_obj_name = ""
        self.bound_obj = None

        self.tools_box.addStretch()

        self.addtool_btn.clicked.connect(self.on_tool_add)
        self.addtool_entry.returnPressed.connect(self.on_tool_add)
        self.deltool_btn.clicked.connect(self.on_tool_delete)
        self.generate_ncc_button.clicked.connect(self.on_ncc)

        self.box_combo_type.currentIndexChanged.connect(self.on_combo_box_type)
        self.reference_radio.group_toggle_fn = self.on_toggle_reference
        self.ncc_choice_offset_cb.stateChanged.connect(self.on_offset_choice)
        self.ncc_rest_cb.stateChanged.connect(self.on_rest_machining_check)
        self.ncc_order_radio.activated_custom[str].connect(self.on_order_changed)

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, shortcut='ALT+N', **kwargs)

    def run(self, toggle=True):
        self.app.report_usage("ToolNonCopperClear()")

        if toggle:
            # if the splitter is hidden, display it, else hide it but only if the current widget is the same
            if self.app.ui.splitter.sizes()[0] == 0:
                self.app.ui.splitter.setSizes([1, 1])
            else:
                try:
                    if self.app.ui.tool_scroll_area.widget().objectName() == self.toolName:
                        self.app.ui.splitter.setSizes([0, 1])
                except AttributeError:
                    pass
        else:
            if self.app.ui.splitter.sizes()[0] == 0:
                self.app.ui.splitter.setSizes([1, 1])

        FlatCAMTool.run(self)
        self.set_tool_ui()

        # reset those objects on a new run
        self.ncc_obj = None
        self.bound_obj = None
        self.obj_name = ''
        self.bound_obj_name = ''

        self.build_ui()
        self.app.ui.notebook.setTabText(2, _("NCC Tool"))

    def set_tool_ui(self):
        self.tools_frame.show()

        self.ncc_order_radio.set_value(self.app.defaults["tools_nccorder"])
        self.ncc_overlap_entry.set_value(self.app.defaults["tools_nccoverlap"])
        self.ncc_margin_entry.set_value(self.app.defaults["tools_nccmargin"])
        self.ncc_method_radio.set_value(self.app.defaults["tools_nccmethod"])
        self.ncc_connect_cb.set_value(self.app.defaults["tools_nccconnect"])
        self.ncc_contour_cb.set_value(self.app.defaults["tools_ncccontour"])
        self.ncc_rest_cb.set_value(self.app.defaults["tools_nccrest"])
        self.reference_radio.set_value(self.app.defaults["tools_nccref"])

        self.tools_table.setupContextMenu()
        self.tools_table.addContextMenu(
            "Add", lambda: self.on_tool_add(dia=None, muted=None), icon=QtGui.QIcon("share/plus16.png"))
        self.tools_table.addContextMenu(
            "Delete", lambda:
            self.on_tool_delete(rows_to_delete=None, all=None), icon=QtGui.QIcon("share/delete32.png"))

        # init the working variables
        self.default_data.clear()
        self.default_data.update({
            "name": '_ncc',
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
            "paintoverlap": self.app.defaults["tools_paintoverlap"],

            "nccoverlap": self.app.defaults["tools_nccoverlap"],
            "nccmargin": self.app.defaults["tools_nccmargin"],
            "nccmethod": self.app.defaults["tools_nccmethod"],
            "nccconnect": self.app.defaults["tools_nccconnect"],
            "ncccontour": self.app.defaults["tools_ncccontour"],
            "nccrest": self.app.defaults["tools_nccrest"]
        })

        try:
            dias = [float(eval(dia)) for dia in self.app.defaults["tools_ncctools"].split(",") if dia != '']
        except Exception as e:
            log.error("At least one tool diameter needed. "
                      "Verify in Edit -> Preferences -> TOOLS -> NCC Tools. %s" % str(e))
            return

        self.tooluid = 0

        self.ncc_tools.clear()
        for tool_dia in dias:
            self.tooluid += 1
            self.ncc_tools.update({
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

        self.obj_name = ""
        self.ncc_obj = None
        self.bound_obj_name = ""
        self.bound_obj = None

        self.tool_type_item_options = ["C1", "C2", "C3", "C4", "B", "V"]
        self.units = self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().upper()

    def build_ui(self):
        self.ui_disconnect()

        # updated units
        self.units = self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().upper()

        if self.units == "IN":
            self.addtool_entry.set_value(0.039)
        else:
            self.addtool_entry.set_value(1)

        sorted_tools = []
        for k, v in self.ncc_tools.items():
            sorted_tools.append(float('%.4f' % float(v['tooldia'])))

        order = self.ncc_order_radio.get_value()
        if order == 'fwd':
            sorted_tools.sort(reverse=False)
        elif order == 'rev':
            sorted_tools.sort(reverse=True)
        else:
            pass

        n = len(sorted_tools)
        self.tools_table.setRowCount(n)
        tool_id = 0

        for tool_sorted in sorted_tools:
            for tooluid_key, tooluid_value in self.ncc_tools.items():
                if float('%.4f' % tooluid_value['tooldia']) == tool_sorted:
                    tool_id += 1
                    id_ = QtWidgets.QTableWidgetItem('%d' % int(tool_id))
                    id_.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                    row_no = tool_id - 1
                    self.tools_table.setItem(row_no, 0, id_)  # Tool name/id

                    # Make sure that the drill diameter when in MM is with no more than 2 decimals
                    # There are no drill bits in MM with more than 3 decimals diameter
                    # For INCH the decimals should be no more than 3. There are no drills under 10mils
                    if self.units == 'MM':
                        dia = QtWidgets.QTableWidgetItem('%.2f' % tooluid_value['tooldia'])
                    else:
                        dia = QtWidgets.QTableWidgetItem('%.4f' % tooluid_value['tooldia'])

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

                    # ## REMEMBER: THIS COLUMN IS HIDDEN IN OBJECTUI.PY # ##
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

        self.ui_connect()

    def ui_connect(self):
        self.tools_table.itemChanged.connect(self.on_tool_edit)

    def ui_disconnect(self):
        try:
            # if connected, disconnect the signal from the slot on item_changed as it creates issues
            self.tools_table.itemChanged.disconnect(self.on_tool_edit)
        except (TypeError, AttributeError):
            pass

    def on_combo_box_type(self):
        obj_type = self.box_combo_type.currentIndex()
        self.box_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.box_combo.setCurrentIndex(0)

    def on_toggle_reference(self):
        if self.reference_radio.get_value() == "itself":
            self.box_combo.hide()
            self.box_combo_label.hide()
            self.box_combo_type.hide()
            self.box_combo_type_label.hide()
        else:
            self.box_combo.show()
            self.box_combo_label.show()
            self.box_combo_type.show()
            self.box_combo_type_label.show()

    def on_offset_choice(self, state):
        if state:
            self.ncc_offset_label.show()
            self.ncc_offset_spinner.show()
        else:
            self.ncc_offset_label.hide()
            self.ncc_offset_spinner.hide()

    def on_order_changed(self, order):
        if order != 'no':
            self.build_ui()

    def on_rest_machining_check(self, state):
        if state:
            self.ncc_order_radio.set_value('rev')
            self.ncc_order_label.setDisabled(True)
            self.ncc_order_radio.setDisabled(True)
        else:
            self.ncc_order_label.setDisabled(False)
            self.ncc_order_radio.setDisabled(False)

    def on_tool_add(self, dia=None, muted=None):

        self.ui_disconnect()

        if dia:
            tool_dia = dia
        else:
            try:
                tool_dia = float(self.addtool_entry.get_value())
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    tool_dia = float(self.addtool_entry.get_value().replace(',', '.'))
                except ValueError:
                    self.app.inform.emit(_("[ERROR_NOTCL] Wrong value format entered, "
                                           "use a number."))
                    return
            if tool_dia is None:
                self.build_ui()
                self.app.inform.emit(_("[WARNING_NOTCL] Please enter a tool diameter to add, in Float format."))
                return

        if tool_dia == 0:
            self.app.inform.emit(_("[WARNING_NOTCL] Please enter a tool diameter with non-zero value, "
                                   "in Float format."))
            return

        # construct a list of all 'tooluid' in the self.tools
        tool_uid_list = []
        for tooluid_key in self.ncc_tools:
            tool_uid_item = int(tooluid_key)
            tool_uid_list.append(tool_uid_item)

        # find maximum from the temp_uid, add 1 and this is the new 'tooluid'
        if not tool_uid_list:
            max_uid = 0
        else:
            max_uid = max(tool_uid_list)
        self.tooluid = int(max_uid + 1)

        tool_dias = []
        for k, v in self.ncc_tools.items():
            for tool_v in v.keys():
                if tool_v == 'tooldia':
                    tool_dias.append(float('%.4f' % v[tool_v]))

        if float('%.4f' % tool_dia) in tool_dias:
            if muted is None:
                self.app.inform.emit(_("[WARNING_NOTCL] Adding tool cancelled. Tool already in Tool Table."))
            self.tools_table.itemChanged.connect(self.on_tool_edit)
            return
        else:
            if muted is None:
                self.app.inform.emit(_("[success] New tool added to Tool Table."))
            self.ncc_tools.update({
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
        self.ui_disconnect()

        tool_dias = []
        for k, v in self.ncc_tools.items():
            for tool_v in v.keys():
                if tool_v == 'tooldia':
                    tool_dias.append(float('%.4f' % v[tool_v]))

        for row in range(self.tools_table.rowCount()):

            try:
                new_tool_dia = float(self.tools_table.item(row, 1).text())
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    new_tool_dia = float(self.tools_table.item(row, 1).text().replace(',', '.'))
                except ValueError:
                    self.app.inform.emit(_("[ERROR_NOTCL] Wrong value format entered, "
                                         "use a number."))
                    return

            tooluid = int(self.tools_table.item(row, 3).text())

            # identify the tool that was edited and get it's tooluid
            if new_tool_dia not in tool_dias:
                self.ncc_tools[tooluid]['tooldia'] = new_tool_dia
                self.app.inform.emit(_("[success] Tool from Tool Table was edited."))
                self.build_ui()
                return
            else:
                # identify the old tool_dia and restore the text in tool table
                for k, v in self.ncc_tools.items():
                    if k == tooluid:
                        old_tool_dia = v['tooldia']
                        break
                restore_dia_item = self.tools_table.item(row, 1)
                restore_dia_item.setText(str(old_tool_dia))
                self.app.inform.emit(_("[WARNING_NOTCL] Edit cancelled. "
                                       "New diameter value is already in the Tool Table."))
        self.build_ui()

    def on_tool_delete(self, rows_to_delete=None, all=None):
        self.ui_disconnect()

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
                self.ncc_tools.pop(t, None)
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
                    self.ncc_tools.pop(t, None)

        except AttributeError:
            self.app.inform.emit(_("[WARNING_NOTCL] Delete failed. Select a tool to delete."))
            return
        except Exception as e:
            log.debug(str(e))

        self.app.inform.emit(_("[success] Tool(s) deleted from Tool Table."))
        self.build_ui()

    def on_ncc(self):
        self.bound_obj = None
        self.ncc_obj = None

        try:
            over = float(self.ncc_overlap_entry.get_value())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                over = float(self.ncc_overlap_entry.get_value().replace(',', '.'))
            except ValueError:
                self.app.inform.emit(_("[ERROR_NOTCL] Wrong value format entered, "
                                       "use a number."))
                return
        over = over if over else self.app.defaults["tools_nccoverlap"]

        if over >= 1 or over < 0:
            self.app.inform.emit(_("[ERROR_NOTCL] Overlap value must be between "
                                   "0 (inclusive) and 1 (exclusive), "))
            return

        try:
            margin = float(self.ncc_margin_entry.get_value())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                margin = float(self.ncc_margin_entry.get_value().replace(',', '.'))
            except ValueError:
                self.app.inform.emit(_("[ERROR_NOTCL] Wrong value format entered, "
                                       "use a number."))
                return
        margin = margin if margin is not None else float(self.app.defaults["tools_nccmargin"])

        try:
            ncc_offset_value = float(self.ncc_offset_spinner.get_value())
        except ValueError:
            self.app.inform.emit(_("[ERROR_NOTCL] Wrong value format entered, "
                                   "use a number."))
            return
        ncc_offset_value = ncc_offset_value if ncc_offset_value is not None \
            else float(self.app.defaults["tools_ncc_offset_value"])

        connect = self.ncc_connect_cb.get_value()
        connect = connect if connect else self.app.defaults["tools_nccconnect"]

        contour = self.ncc_contour_cb.get_value()
        contour = contour if contour else self.app.defaults["tools_ncccontour"]

        clearing_method = self.ncc_rest_cb.get_value()
        clearing_method = clearing_method if clearing_method else self.app.defaults["tools_nccrest"]

        pol_method = self.ncc_method_radio.get_value()
        pol_method = pol_method if pol_method else self.app.defaults["tools_nccmethod"]

        if self.reference_radio.get_value() == 'itself':
            self.bound_obj_name = self.object_combo.currentText()
            # Get source object.
            try:
                self.bound_obj = self.app.collection.get_by_name(self.bound_obj_name)
            except Exception as e:
                self.app.inform.emit(_("[ERROR_NOTCL] Could not retrieve object: %s") % self.obj_name)
                return "Could not retrieve object: %s" % self.obj_name
        else:
            self.bound_obj_name = self.box_combo.currentText()
            # Get source object.
            try:
                self.bound_obj = self.app.collection.get_by_name(self.bound_obj_name)
            except Exception as e:
                self.app.inform.emit(_("[ERROR_NOTCL] Could not retrieve object: %s") % self.obj_name)
                return "Could not retrieve object: %s" % self.obj_name

        self.obj_name = self.object_combo.currentText()
        # Get source object.
        try:
            self.ncc_obj = self.app.collection.get_by_name(self.obj_name)
        except Exception as e:
            self.app.inform.emit(_("[ERROR_NOTCL] Could not retrieve object: %s") % self.obj_name)
            return "Could not retrieve object: %s" % self.obj_name

        # Prepare non-copper polygons
        geo_n = self.bound_obj.solid_geometry
        try:
            if isinstance(geo_n, MultiPolygon):
                env_obj = geo_n.convex_hull
            elif (isinstance(geo_n, MultiPolygon) and len(geo_n) == 1) or \
                    (isinstance(geo_n, list) and len(geo_n) == 1) and isinstance(geo_n[0], Polygon):
                env_obj = cascaded_union(self.bound_obj.solid_geometry)
            else:
                env_obj = cascaded_union(self.bound_obj.solid_geometry)
                env_obj = env_obj.convex_hull
            bounding_box = env_obj.buffer(distance=margin, join_style=base.JOIN_STYLE.mitre)
        except Exception as e:
            log.debug("NonCopperClear.on_ncc() --> %s" % str(e))
            self.app.inform.emit(_("[ERROR_NOTCL] No object available."))
            return

        # calculate the empty area by subtracting the solid_geometry from the object bounding box geometry
        if self.ncc_choice_offset_cb.isChecked():
            self.app.inform.emit(_("[WARNING_NOTCL] Buffering ..."))
            offseted_geo = self.ncc_obj.solid_geometry.buffer(distance=ncc_offset_value)
            self.app.inform.emit(_("[success] Buffering finished ..."))
            empty = self.get_ncc_empty_area(target=offseted_geo, boundary=bounding_box)
        else:
            empty = self.get_ncc_empty_area(target=self.ncc_obj.solid_geometry, boundary=bounding_box)

        if type(empty) is Polygon:
            empty = MultiPolygon([empty])

        if empty.is_empty:
            self.app.inform.emit(_("[ERROR_NOTCL] Could not get the extent of the area to be non copper cleared."))
            return

        # clear non copper using standard algorithm
        if clearing_method is False:
            self.clear_non_copper(
                empty=empty,
                over=over,
                pol_method=pol_method,
                connect=connect,
                contour=contour
            )
        # clear non copper using rest machining algorithm
        else:
            self.clear_non_copper_rest(
                empty=empty,
                over=over,
                pol_method=pol_method,
                connect=connect,
                contour=contour
            )

    def clear_non_copper(self, empty, over, pol_method, outname=None, connect=True, contour=True):

        name = outname if outname else self.obj_name + "_ncc"

        # Sort tools in descending order
        sorted_tools = []
        for k, v in self.ncc_tools.items():
            sorted_tools.append(float('%.4f' % float(v['tooldia'])))

        order = self.ncc_order_radio.get_value()
        if order == 'fwd':
            sorted_tools.sort(reverse=False)
        elif order == 'rev':
            sorted_tools.sort(reverse=True)
        else:
            pass

        # Do job in background
        proc = self.app.proc_container.new(_("Clearing Non-Copper areas."))

        def initialize(geo_obj, app_obj):
            assert isinstance(geo_obj, FlatCAMGeometry), \
                "Initializer expected a FlatCAMGeometry, got %s" % type(geo_obj)

            cleared_geo = []
            # Already cleared area
            cleared = MultiPolygon()

            # flag for polygons not cleared
            app_obj.poly_not_cleared = False

            # Generate area for each tool
            offset = sum(sorted_tools)
            current_uid = int(1)

            for tool in sorted_tools:
                self.app.inform.emit(_('[success] Non-Copper Clearing with ToolDia = %s started.') % str(tool))
                cleared_geo[:] = []

                # Get remaining tools offset
                offset -= (tool - 1e-12)

                # Area to clear
                area = empty.buffer(-offset)
                try:
                    area = area.difference(cleared)
                except Exception as e:
                    continue

                # Transform area to MultiPolygon
                if type(area) is Polygon:
                    area = MultiPolygon([area])

                if area.geoms:
                    if len(area.geoms) > 0:
                        for p in area.geoms:
                            try:
                                if pol_method == 'standard':
                                    cp = self.clear_polygon(p, tool, self.app.defaults["gerber_circle_steps"],
                                                            overlap=over, contour=contour, connect=connect)
                                elif pol_method == 'seed':
                                    cp = self.clear_polygon2(p, tool, self.app.defaults["gerber_circle_steps"],
                                                             overlap=over, contour=contour, connect=connect)
                                else:
                                    cp = self.clear_polygon3(p, tool, self.app.defaults["gerber_circle_steps"],
                                                             overlap=over, contour=contour, connect=connect)
                                if cp:
                                    cleared_geo += list(cp.get_objects())
                            except Exception as e:
                                log.warning("Polygon can not be cleared. %s" % str(e))
                                app_obj.poly_not_cleared = True
                                continue

                        # check if there is a geometry at all in the cleared geometry
                        if cleared_geo:
                            # Overall cleared area
                            cleared = empty.buffer(-offset * (1 + over)).buffer(-tool / 1.999999).buffer(
                                tool / 1.999999)

                            # clean-up cleared geo
                            cleared = cleared.buffer(0)

                            # find the tooluid associated with the current tool_dia so we know where to add the tool
                            # solid_geometry
                            for k, v in self.ncc_tools.items():
                                if float('%.4f' % v['tooldia']) == float('%.4f' % tool):
                                    current_uid = int(k)

                                    # add the solid_geometry to the current too in self.paint_tools dictionary
                                    # and then reset the temporary list that stored that solid_geometry
                                    v['solid_geometry'] = deepcopy(cleared_geo)
                                    v['data']['name'] = name
                                    break
                            geo_obj.tools[current_uid] = dict(self.ncc_tools[current_uid])
                        else:
                            log.debug("There are no geometries in the cleared polygon.")

            geo_obj.options["cnctooldia"] = str(tool)
            geo_obj.multigeo = True

        def job_thread(app_obj):
            try:
                app_obj.new_object("geometry", name, initialize)
            except Exception as e:
                proc.done()
                self.app.inform.emit(_('[ERROR_NOTCL] NCCTool.clear_non_copper() --> %s') % str(e))
                return
            proc.done()

            if app_obj.poly_not_cleared is False:
                self.app.inform.emit(_('[success] NCC Tool finished.'))
            else:
                self.app.inform.emit(_('[WARNING_NOTCL] NCC Tool finished but some PCB features could not be cleared. '
                                     'Check the result.'))
            # reset the variable for next use
            app_obj.poly_not_cleared = False

            # focus on Selected Tab
            self.app.ui.notebook.setCurrentWidget(self.app.ui.selected_tab)
            self.tools_frame.hide()
            self.app.ui.notebook.setTabText(2, _("Tools"))

        # Promise object with the new name
        self.app.collection.promise(name)

        # Background
        self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})

    # clear copper with 'rest-machining' algorithm
    def clear_non_copper_rest(self, empty, over, pol_method, outname=None, connect=True, contour=True):

        name = outname if outname is not None else self.obj_name + "_ncc_rm"

        # Sort tools in descending order
        sorted_tools = []
        for k, v in self.ncc_tools.items():
            sorted_tools.append(float('%.4f' % float(v['tooldia'])))
        sorted_tools.sort(reverse=True)

        # Do job in background
        proc = self.app.proc_container.new(_("Clearing Non-Copper areas."))

        def initialize_rm(geo_obj, app_obj):
            assert isinstance(geo_obj, FlatCAMGeometry), \
                "Initializer expected a FlatCAMGeometry, got %s" % type(geo_obj)

            cleared_geo = []
            cleared_by_last_tool = []
            rest_geo = []
            current_uid = 1

            # repurposed flag for final object, geo_obj. True if it has any solid_geometry, False if not.
            app_obj.poly_not_cleared = True

            area = empty.buffer(0)
            # Generate area for each tool
            while sorted_tools:
                tool = sorted_tools.pop(0)
                self.app.inform.emit(_('[success] Non-Copper Rest Clearing with ToolDia = %s started.') % str(tool))

                tool_used = tool - 1e-12
                cleared_geo[:] = []

                # Area to clear
                for poly in cleared_by_last_tool:
                    try:
                        area = area.difference(poly)
                    except Exception as e:
                        pass
                cleared_by_last_tool[:] = []

                # Transform area to MultiPolygon
                if type(area) is Polygon:
                    area = MultiPolygon([area])

                # add the rest that was not able to be cleared previously; area is a MultyPolygon
                # and rest_geo it's a list
                allparts = [p.buffer(0) for p in area.geoms]
                allparts += deepcopy(rest_geo)
                rest_geo[:] = []
                area = MultiPolygon(deepcopy(allparts))
                allparts[:] = []

                if area.geoms:
                    if len(area.geoms) > 0:
                        for p in area.geoms:
                            try:
                                if pol_method == 'standard':
                                    cp = self.clear_polygon(p, tool_used, self.app.defaults["gerber_circle_steps"],
                                                            overlap=over, contour=contour, connect=connect)
                                elif pol_method == 'seed':
                                    cp = self.clear_polygon2(p, tool_used,
                                                             self.app.defaults["gerber_circle_steps"],
                                                             overlap=over, contour=contour, connect=connect)
                                else:
                                    cp = self.clear_polygon3(p, tool_used,
                                                             self.app.defaults["gerber_circle_steps"],
                                                             overlap=over, contour=contour, connect=connect)
                                cleared_geo.append(list(cp.get_objects()))
                            except:
                                log.warning("Polygon can't be cleared.")
                                # this polygon should be added to a list and then try clear it with a smaller tool
                                rest_geo.append(p)

                        # check if there is a geometry at all in the cleared geometry
                        if cleared_geo:
                            # Overall cleared area
                            cleared_area = list(self.flatten_list(cleared_geo))

                            # cleared = MultiPolygon([p.buffer(tool_used / 2).buffer(-tool_used / 2)
                            #                         for p in cleared_area])

                            # here we store the poly's already processed in the original geometry by the current tool
                            # into cleared_by_last_tool list
                            # this will be sustracted from the original geometry_to_be_cleared and make data for
                            # the next tool
                            buffer_value = tool_used / 2
                            for p in cleared_area:
                                poly = p.buffer(buffer_value)
                                cleared_by_last_tool.append(poly)

                            # find the tooluid associated with the current tool_dia so we know
                            # where to add the tool solid_geometry
                            for k, v in self.ncc_tools.items():
                                if float('%.4f' % v['tooldia']) == float('%.4f' % tool):
                                    current_uid = int(k)

                                    # add the solid_geometry to the current too in self.paint_tools dictionary
                                    # and then reset the temporary list that stored that solid_geometry
                                    v['solid_geometry'] = deepcopy(cleared_area)
                                    v['data']['name'] = name
                                    cleared_area[:] = []
                                    break

                            geo_obj.tools[current_uid] = dict(self.ncc_tools[current_uid])
                        else:
                            log.debug("There are no geometries in the cleared polygon.")

            geo_obj.multigeo = True
            geo_obj.options["cnctooldia"] = str(tool)

            # check to see if geo_obj.tools is empty
            # it will be updated only if there is a solid_geometry for tools
            if geo_obj.tools:
                return
            else:
                # I will use this variable for this purpose although it was meant for something else
                # signal that we have no geo in the object therefore don't create it
                app_obj.poly_not_cleared = False
                return "fail"

        def job_thread(app_obj):
            try:
                app_obj.new_object("geometry", name, initialize_rm)
            except Exception as e:
                proc.done()
                app_obj.inform.emit(_('[ERROR_NOTCL] NCCTool.clear_non_copper_rest() --> %s') % str(e))
                return

            if app_obj.poly_not_cleared is True:
                app_obj.inform.emit('[success] NCC Tool finished.')
                # focus on Selected Tab
                app_obj.ui.notebook.setCurrentWidget(self.app.ui.selected_tab)
            else:
                app_obj.inform.emit(_('[ERROR_NOTCL] NCC Tool finished but could not clear the object '
                                     'with current settings.'))
                # focus on Project Tab
                app_obj.ui.notebook.setCurrentWidget(self.app.ui.project_tab)
            proc.done()
            # reset the variable for next use
            app_obj.poly_not_cleared = False

            self.tools_frame.hide()
            app_obj.ui.notebook.setTabText(2, "Tools")

        # Promise object with the new name
        self.app.collection.promise(name)

        # Background
        self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})

    @staticmethod
    def get_ncc_empty_area(target, boundary=None):
        """
        Returns the complement of target geometry within
        the given boundary polygon. If not specified, it defaults to
        the rectangular bounding box of target geometry.
        """
        if boundary is None:
            boundary = target.envelope
        return boundary.difference(target)

    def reset_fields(self):
        self.object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
