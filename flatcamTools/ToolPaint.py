# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# File Modified: Marius Adrian Stanciu (c)                 #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from FlatCAMTool import FlatCAMTool
from copy import copy, deepcopy
from ObjectCollection import *
from shapely.geometry import base

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ToolPaint(FlatCAMTool, Gerber):

    toolName = _("Paint Tool")

    def __init__(self, app):
        self.app = app

        FlatCAMTool.__init__(self, app)
        Geometry.__init__(self, geo_steps_per_circle=self.app.defaults["geometry_circle_steps"])

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

        self.tools_frame = QtWidgets.QFrame()
        self.tools_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.tools_frame)
        self.tools_box = QtWidgets.QVBoxLayout()
        self.tools_box.setContentsMargins(0, 0, 0, 0)
        self.tools_frame.setLayout(self.tools_box)

        # ## Form Layout
        form_layout = QtWidgets.QFormLayout()
        self.tools_box.addLayout(form_layout)

        # ################################################
        # ##### Type of object to be painted #############
        # ################################################
        self.type_obj_combo = QtWidgets.QComboBox()
        self.type_obj_combo.addItem("Gerber")
        self.type_obj_combo.addItem("Excellon")
        self.type_obj_combo.addItem("Geometry")

        # we get rid of item1 ("Excellon") as it is not suitable
        self.type_obj_combo.view().setRowHidden(1, True)
        self.type_obj_combo.setItemIcon(0, QtGui.QIcon("share/flatcam_icon16.png"))
        self.type_obj_combo.setItemIcon(2, QtGui.QIcon("share/geometry16.png"))

        self.type_obj_combo_label = QtWidgets.QLabel('%s:' % _("Obj Type"))
        self.type_obj_combo_label.setToolTip(
            _("Specify the type of object to be painted.\n"
              "It can be of type: Gerber or Geometry.\n"
              "What is selected here will dictate the kind\n"
              "of objects that will populate the 'Object' combobox.")
        )
        self.type_obj_combo_label.setMinimumWidth(60)
        form_layout.addRow(self.type_obj_combo_label, self.type_obj_combo)

        # ################################################
        # ##### The object to be painted #################
        # ################################################
        self.obj_combo = QtWidgets.QComboBox()
        self.obj_combo.setModel(self.app.collection)
        self.obj_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.obj_combo.setCurrentIndex(1)

        self.object_label = QtWidgets.QLabel('%s:' % _("Object"))
        self.object_label.setToolTip(_("Object to be painted."))

        form_layout.addRow(self.object_label, self.obj_combo)

        e_lab_0 = QtWidgets.QLabel('')
        form_layout.addRow(e_lab_0)

        # ### Tools ## ##
        self.tools_table_label = QtWidgets.QLabel('<b>%s</b>' % _('Tools Table'))
        self.tools_table_label.setToolTip(
            _("Tools pool from which the algorithm\n"
              "will pick the ones used for painting.")
        )
        self.tools_box.addWidget(self.tools_table_label)

        self.tools_table = FCTable()
        self.tools_box.addWidget(self.tools_table)

        self.tools_table.setColumnCount(4)
        self.tools_table.setHorizontalHeaderLabels(['#', _('Diameter'), _('TT'), ''])
        self.tools_table.setColumnHidden(3, True)
        # self.tools_table.setSortingEnabled(False)
        # self.tools_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        self.tools_table.horizontalHeaderItem(0).setToolTip(
            _("This is the Tool Number.\n"
              "Painting will start with the tool with the biggest diameter,\n"
              "continuing until there are no more tools.\n"
              "Only tools that create painting geometry will still be present\n"
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

        self.order_label = QtWidgets.QLabel('<b>%s:</b>' % _('Tool order'))
        self.order_label.setToolTip(_("This set the way that the tools in the tools table are used.\n"
                                      "'No' --> means that the used order is the one in the tool table\n"
                                      "'Forward' --> means that the tools will be ordered from small to big\n"
                                      "'Reverse' --> menas that the tools will ordered from big to small\n\n"
                                      "WARNING: using rest machining will automatically set the order\n"
                                      "in reverse and disable this control."))

        self.order_radio = RadioSet([{'label': _('No'), 'value': 'no'},
                                     {'label': _('Forward'), 'value': 'fwd'},
                                     {'label': _('Reverse'), 'value': 'rev'}])
        self.order_radio.setToolTip(_("This set the way that the tools in the tools table are used.\n"
                                      "'No' --> means that the used order is the one in the tool table\n"
                                      "'Forward' --> means that the tools will be ordered from small to big\n"
                                      "'Reverse' --> menas that the tools will ordered from big to small\n\n"
                                      "WARNING: using rest machining will automatically set the order\n"
                                      "in reverse and disable this control."))
        form = QtWidgets.QFormLayout()
        self.tools_box.addLayout(form)
        form.addRow(QtWidgets.QLabel(''), QtWidgets.QLabel(''))
        form.addRow(self.order_label, self.order_radio)

        # ### Add a new Tool ## ##
        hlay = QtWidgets.QHBoxLayout()
        self.tools_box.addLayout(hlay)

        self.addtool_entry_lbl = QtWidgets.QLabel('<b>%s:</b>' % _('Tool Dia'))
        self.addtool_entry_lbl.setToolTip(
            _("Diameter for the new tool.")
        )
        self.addtool_entry = FCEntry2()

        # hlay.addWidget(self.addtool_label)
        # hlay.addStretch()
        hlay.addWidget(self.addtool_entry_lbl)
        hlay.addWidget(self.addtool_entry)

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

        # Overlap
        ovlabel = QtWidgets.QLabel('%s:' % _('Overlap Rate'))
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
        grid3.addWidget(ovlabel, 1, 0)
        self.paintoverlap_entry = FCEntry()
        grid3.addWidget(self.paintoverlap_entry, 1, 1)

        # Margin
        marginlabel = QtWidgets.QLabel('%s:' % _('Margin'))
        marginlabel.setToolTip(
            _("Distance by which to avoid\n"
              "the edges of the polygon to\n"
              "be painted.")
        )
        grid3.addWidget(marginlabel, 2, 0)
        self.paintmargin_entry = FCEntry()
        grid3.addWidget(self.paintmargin_entry, 2, 1)

        # Method
        methodlabel = QtWidgets.QLabel('%s:' % _('Method'))
        methodlabel.setToolTip(
            _("Algorithm for painting:\n"
              "- Standard: Fixed step inwards.\n"
              "- Seed-based: Outwards from seed.\n"
              "- Line-based: Parallel lines.")
        )
        grid3.addWidget(methodlabel, 3, 0)
        self.paintmethod_combo = RadioSet([
            {"label": _("Standard"), "value": "standard"},
            {"label": _("Seed-based"), "value": "seed"},
            {"label": _("Straight lines"), "value": "lines"}
        ], orientation='vertical', stretch=False)
        grid3.addWidget(self.paintmethod_combo, 3, 1)

        # Connect lines
        pathconnectlabel = QtWidgets.QLabel('%s:' % _("Connect"))
        pathconnectlabel.setToolTip(
            _("Draw lines between resulting\n"
              "segments to minimize tool lifts.")
        )
        grid3.addWidget(pathconnectlabel, 4, 0)
        self.pathconnect_cb = FCCheckBox()
        grid3.addWidget(self.pathconnect_cb, 4, 1)

        contourlabel = QtWidgets.QLabel('%s:' % _("Contour"))
        contourlabel.setToolTip(
            _("Cut around the perimeter of the polygon\n"
              "to trim rough edges.")
        )
        grid3.addWidget(contourlabel, 5, 0)
        self.paintcontour_cb = FCCheckBox()
        grid3.addWidget(self.paintcontour_cb, 5, 1)

        restlabel = QtWidgets.QLabel('%s:' % _("Rest M."))
        restlabel.setToolTip(
            _("If checked, use 'rest machining'.\n"
              "Basically it will clear copper outside PCB features,\n"
              "using the biggest tool and continue with the next tools,\n"
              "from bigger to smaller, to clear areas of copper that\n"
              "could not be cleared by previous tool, until there is\n"
              "no more copper to clear or there are no more tools.\n\n"
              "If not checked, use the standard algorithm.")
        )
        grid3.addWidget(restlabel, 6, 0)
        self.rest_cb = FCCheckBox()
        grid3.addWidget(self.rest_cb, 6, 1)

        # Polygon selection
        selectlabel = QtWidgets.QLabel('%s:' % _('Selection'))
        selectlabel.setToolTip(
            _("How to select Polygons to be painted.\n\n"
              "- 'Area Selection' - left mouse click to start selection of the area to be painted.\n"
              "Keeping a modifier key pressed (CTRL or SHIFT) will allow to add multiple areas.\n"
              "- 'All Polygons' - the Paint will start after click.\n"
              "- 'Reference Object' -  will do non copper clearing within the area\n"
              "specified by another object.")
        )
        grid3.addWidget(selectlabel, 7, 0)
        # grid3 = QtWidgets.QGridLayout()
        self.selectmethod_combo = RadioSet([
            {"label": _("Single Polygon"), "value": "single"},
            {"label": _("Area Selection"), "value": "area"},
            {"label": _("All Polygons"), "value": "all"},
            {"label": _("Reference Object"), "value": "ref"}
        ], orientation='vertical', stretch=False)
        self.selectmethod_combo.setToolTip(
            _("How to select Polygons to be painted.\n\n"
              "- 'Area Selection' - left mouse click to start selection of the area to be painted.\n"
              "Keeping a modifier key pressed (CTRL or SHIFT) will allow to add multiple areas.\n"
              "- 'All Polygons' - the Paint will start after click.\n"
              "- 'Reference Object' -  will do non copper clearing within the area\n"
              "specified by another object.")
        )
        grid3.addWidget(self.selectmethod_combo, 7, 1)

        form1 = QtWidgets.QFormLayout()
        self.tools_box.addLayout(form1)

        self.box_combo_type_label = QtWidgets.QLabel('%s:' % _("Ref. Type"))
        self.box_combo_type_label.setToolTip(
            _("The type of FlatCAM object to be used as paint reference.\n"
              "It can be Gerber, Excellon or Geometry.")
        )
        self.box_combo_type = QtWidgets.QComboBox()
        self.box_combo_type.addItem(_("Gerber   Reference Box Object"))
        self.box_combo_type.addItem(_("Excellon Reference Box Object"))
        self.box_combo_type.addItem(_("Geometry Reference Box Object"))
        form1.addRow(self.box_combo_type_label, self.box_combo_type)

        self.box_combo_label = QtWidgets.QLabel('%s:' % _("Ref. Object"))
        self.box_combo_label.setToolTip(
            _("The FlatCAM object to be used as non copper clearing reference.")
        )
        self.box_combo = QtWidgets.QComboBox()
        self.box_combo.setModel(self.app.collection)
        self.box_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.box_combo.setCurrentIndex(1)
        form1.addRow(self.box_combo_label, self.box_combo)

        self.box_combo.hide()
        self.box_combo_label.hide()
        self.box_combo_type.hide()
        self.box_combo_type_label.hide()

        # GO Button
        self.generate_paint_button = QtWidgets.QPushButton(_('Create Paint Geometry'))
        self.generate_paint_button.setToolTip(
            _("- 'Area Selection' - left mouse click to start selection of the area to be painted.\n"
              "Keeping a modifier key pressed (CTRL or SHIFT) will allow to add multiple areas.\n"
              "- 'All Polygons' - the Paint will start after click.\n"
              "- 'Reference Object' -  will do non copper clearing within the area\n"
              "specified by another object.")
        )
        self.tools_box.addWidget(self.generate_paint_button)

        self.tools_box.addStretch()

        self.obj_name = ""
        self.paint_obj = None

        self.units = ''
        self.paint_tools = {}
        self.tooluid = 0
        self.first_click = False
        self.cursor_pos = None
        self.mouse_is_dragging = False

        self.sel_rect = []

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

        # ## Signals
        self.addtool_btn.clicked.connect(self.on_tool_add)
        self.addtool_entry.returnPressed.connect(self.on_tool_add)
        # self.copytool_btn.clicked.connect(lambda: self.on_tool_copy())
        self.tools_table.itemChanged.connect(self.on_tool_edit)
        self.deltool_btn.clicked.connect(self.on_tool_delete)
        self.generate_paint_button.clicked.connect(self.on_paint_button_click)
        self.selectmethod_combo.activated_custom.connect(self.on_radio_selection)
        self.order_radio.activated_custom[str].connect(self.on_order_changed)
        self.rest_cb.stateChanged.connect(self.on_rest_machining_check)

        self.box_combo_type.currentIndexChanged.connect(self.on_combo_box_type)
        self.type_obj_combo.currentIndexChanged.connect(self.on_type_obj_index_changed)

    def on_type_obj_index_changed(self, index):
        obj_type = self.type_obj_combo.currentIndex()
        self.obj_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.obj_combo.setCurrentIndex(0)

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, shortcut='ALT+P', **kwargs)

    def run(self, toggle=True):
        self.app.report_usage("ToolPaint()")

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

        self.app.ui.notebook.setTabText(2, _("Paint Tool"))

    def reset_usage(self):
        self.obj_name = ""
        self.paint_obj = None
        self.bound_obj = None

        self.first_click = False
        self.cursor_pos = None
        self.mouse_is_dragging = False

        self.sel_rect = []

    def on_radio_selection(self):
        if self.selectmethod_combo.get_value() == "ref":
            self.box_combo.show()
            self.box_combo_label.show()
            self.box_combo_type.show()
            self.box_combo_type_label.show()
        else:
            self.box_combo.hide()
            self.box_combo_label.hide()
            self.box_combo_type.hide()
            self.box_combo_type_label.hide()

        if self.selectmethod_combo.get_value() == 'single':
            # disable rest-machining for single polygon painting
            self.rest_cb.set_value(False)
            self.rest_cb.setDisabled(True)
            # delete all tools except first row / tool for single polygon painting
            # list_to_del = list(range(1, self.tools_table.rowCount()))
            # if list_to_del:
            #     self.on_tool_delete(rows_to_delete=list_to_del)
            # # disable addTool and delTool
            # self.addtool_entry.setDisabled(True)
            # self.addtool_btn.setDisabled(True)
            # self.deltool_btn.setDisabled(True)
            # self.tools_table.setContextMenuPolicy(Qt.NoContextMenu)
        if self.selectmethod_combo.get_value() == 'area':
            # disable rest-machining for single polygon painting
            self.rest_cb.set_value(False)
            self.rest_cb.setDisabled(True)
        else:
            self.rest_cb.setDisabled(False)
            self.addtool_entry.setDisabled(False)
            self.addtool_btn.setDisabled(False)
            self.deltool_btn.setDisabled(False)
            self.tools_table.setContextMenuPolicy(Qt.ActionsContextMenu)

    def on_order_changed(self, order):
        if order != 'no':
            self.build_ui()

    def on_rest_machining_check(self, state):
        if state:
            self.order_radio.set_value('rev')
            self.order_label.setDisabled(True)
            self.order_radio.setDisabled(True)
        else:
            self.order_label.setDisabled(False)
            self.order_radio.setDisabled(False)

    def set_tool_ui(self):
        self.tools_frame.show()
        self.reset_fields()

        # ## Init the GUI interface
        self.order_radio.set_value(self.app.defaults["tools_paintorder"])
        self.paintmargin_entry.set_value(self.default_data["paintmargin"])
        self.paintmethod_combo.set_value(self.default_data["paintmethod"])
        self.selectmethod_combo.set_value(self.default_data["selectmethod"])
        self.pathconnect_cb.set_value(self.default_data["pathconnect"])
        self.paintcontour_cb.set_value(self.default_data["paintcontour"])
        self.paintoverlap_entry.set_value(self.default_data["paintoverlap"])

        # updated units
        self.units = self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().upper()

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

        # call on self.on_tool_add() counts as an call to self.build_ui()
        # through this, we add a initial row / tool in the tool_table
        self.on_tool_add(self.app.defaults["tools_painttooldia"], muted=True)

        # if the Paint Method is "Single" disable the tool table context menu
        if self.default_data["selectmethod"] == "single":
            self.tools_table.setContextMenuPolicy(Qt.NoContextMenu)

    def build_ui(self):
        try:
            # if connected, disconnect the signal from the slot on item_changed as it creates issues
            self.tools_table.itemChanged.disconnect()
        except (TypeError, AttributeError):
            pass

        # updated units
        self.units = self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().upper()

        sorted_tools = []
        for k, v in self.paint_tools.items():
            sorted_tools.append(float('%.4f' % float(v['tooldia'])))

        order = self.order_radio.get_value()
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

        # we reactivate the signals after the after the tool adding as we don't need to see the tool been populated
        self.tools_table.itemChanged.connect(self.on_tool_edit)

    def on_combo_box_type(self):
        obj_type = self.box_combo_type.currentIndex()
        self.box_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.box_combo.setCurrentIndex(0)

    def on_tool_add(self, dia=None, muted=None):

        try:
            self.tools_table.itemChanged.disconnect()
        except Exception as e:
            log.debug("ToolPaint.on_tool_add() --> %s" % str(e))

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
                    self.app.inform.emit('[ERROR_NOTCL] %s' %
                                         _("Wrong value format entered, use a number."))
                    return

            if tool_dia is None:
                self.build_ui()
                self.app.inform.emit('[WARNING_NOTCL] %s' %
                                     _("Please enter a tool diameter to add, in Float format."))
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
                self.app.inform.emit('[WARNING_NOTCL] %s' %
                                     _("Adding tool cancelled. Tool already in Tool Table."))
            self.tools_table.itemChanged.connect(self.on_tool_edit)
            return
        else:
            if muted is None:
                self.app.inform.emit('[success] %s' %
                                     _("New tool added to Tool Table."))
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
        old_tool_dia = ''

        try:
            self.tools_table.itemChanged.disconnect()
        except Exception as e:
            log.debug("ToolPaint.on_tool_edit() --> %s" % str(e))

        tool_dias = []
        for k, v in self.paint_tools.items():
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
                    self.app.inform.emit('[ERROR_NOTCL] %s' %
                                         _("Wrong value format entered, use a number."))
                    return
            tooluid = int(self.tools_table.item(row, 3).text())

            # identify the tool that was edited and get it's tooluid
            if new_tool_dia not in tool_dias:
                self.paint_tools[tooluid]['tooldia'] = new_tool_dia
                self.app.inform.emit('[success] %s' %
                                     _("Tool from Tool Table was edited."))
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
                self.app.inform.emit('[WARNING_NOTCL] %s' %
                                     _("Edit cancelled. New diameter value is already in the Tool Table."))
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
    #                     self.app.inform.emit("[WARNING_NOTCL] Failed. Select a tool to copy.")
    #                     self.build_ui()
    #                     return
    #                 except Exception as e:
    #                     log.debug("on_tool_copy() --> " + str(e))
    #             # deselect the table
    #             # self.ui.geo_tools_table.clearSelection()
    #         else:
    #             self.app.inform.emit("[WARNING_NOTCL] Failed. Select a tool to copy.")
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
        except Exception as e:
            log.debug("ToolPaint.on_tool_delete() --> %s" % str(e))
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
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("Delete failed. Select a tool to delete."))
            return
        except Exception as e:
            log.debug(str(e))

        self.app.inform.emit('[success] %s' %
                             _("Tool(s) deleted from Tool Table."))
        self.build_ui()

    def on_paint_button_click(self):

        # init values for the next usage
        self.reset_usage()

        self.app.report_usage(_("on_paint_button_click"))
        # self.app.call_source = 'paint'

        # #####################################################
        # ######### Reading Parameters ########################
        # #####################################################
        self.app.inform.emit(_("Paint Tool. Reading parameters."))

        try:
            overlap = float(self.paintoverlap_entry.get_value())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                overlap = float(self.paintoverlap_entry.get_value().replace(',', '.'))
            except ValueError:
                self.app.inform.emit('[ERROR_NOTCL] %s' %
                                     _("Wrong value format entered, use a number."))
                return

        if overlap >= 1 or overlap < 0:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Overlap value must be between 0 (inclusive) and 1 (exclusive)"))
            return

        self.app.inform.emit('[WARNING_NOTCL] %s' %
                             _("Click inside the desired polygon."))

        connect = self.pathconnect_cb.get_value()
        contour = self.paintcontour_cb.get_value()
        select_method = self.selectmethod_combo.get_value()

        self.obj_name = self.obj_combo.currentText()

        # Get source object.
        try:
            self.paint_obj = self.app.collection.get_by_name(str(self.obj_name))
        except Exception as e:
            log.debug("ToolPaint.on_paint_button_click() --> %s" % str(e))
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' %
                                 (_("Could not retrieve object: %s"),
                                  self.obj_name))
            return

        if self.paint_obj is None:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' %
                                 (_("Object not found"),
                                  self.paint_obj))
            return

        # test if the Geometry Object is multigeo and return Fail if True because
        # for now Paint don't work on MultiGeo
        if self.paint_obj.multigeo is True:
            self.app.inform.emit('[ERROR_NOTCL] %s...' %
                                 _("Can't do Paint on MultiGeo geometries"))
            return 'Fail'

        o_name = '%s_multitool_paint' % self.obj_name

        # use the selected tools in the tool table; get diameters
        tooldia_list = list()
        if self.tools_table.selectedItems():
            for x in self.tools_table.selectedItems():
                try:
                    tooldia = float(self.tools_table.item(x.row(), 1).text())
                except ValueError:
                    # try to convert comma to decimal point. if it's still not working error message and return
                    try:
                        tooldia = float(self.tools_table.item(x.row(), 1).text().replace(',', '.'))
                    except ValueError:
                        self.app.inform.emit('[ERROR_NOTCL] %s' %
                                             _("Wrong value format entered, use a number."))
                        continue
                tooldia_list.append(tooldia)
        else:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("No selected tools in Tool Table."))
            return

        if select_method == "all":
            self.paint_poly_all(self.paint_obj,
                                tooldia=tooldia_list,
                                outname=o_name,
                                overlap=overlap,
                                connect=connect,
                                contour=contour)

        elif select_method == "single":
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("Click inside the desired polygon."))

            # use the first tool in the tool table; get the diameter
            # tooldia = float('%.4f' % float(self.tools_table.item(0, 1).text()))

            # To be called after clicking on the plot.
            def doit(event):
                # do paint single only for left mouse clicks
                if event.button == 1:
                    self.app.inform.emit(_("Painting polygon..."))
                    self.app.plotcanvas.vis_disconnect('mouse_press', doit)

                    pos = self.app.plotcanvas.translate_coords(event.pos)
                    if self.app.grid_status() == True:
                        pos = self.app.geo_editor.snap(pos[0], pos[1])

                    self.paint_poly(self.paint_obj,
                                    inside_pt=[pos[0], pos[1]],
                                    tooldia=tooldia_list,
                                    overlap=overlap,
                                    connect=connect,
                                    contour=contour)
                    self.app.plotcanvas.vis_connect('mouse_press', self.app.on_mouse_click_over_plot)
                    self.app.plotcanvas.vis_connect('mouse_release', self.app.on_mouse_click_release_over_plot)

            self.app.plotcanvas.vis_disconnect('mouse_release', self.app.on_mouse_click_release_over_plot)
            self.app.plotcanvas.vis_disconnect('mouse_press', self.app.on_mouse_click_over_plot)
            self.app.plotcanvas.vis_connect('mouse_press', doit)

        elif select_method == "area":
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("Click the start point of the paint area."))

            # use the first tool in the tool table; get the diameter
            # tooldia = float('%.4f' % float(self.tools_table.item(0, 1).text()))

            # To be called after clicking on the plot.
            def on_mouse_release(event):
                # do paint single only for left mouse clicks
                if event.button == 1:
                    if not self.first_click:
                        self.first_click = True
                        self.app.inform.emit('[WARNING_NOTCL] %s' %
                                             _("Click the end point of the paint area."))

                        self.cursor_pos = self.app.plotcanvas.translate_coords(event.pos)
                        if self.app.grid_status() == True:
                            self.cursor_pos = self.app.geo_editor.snap(self.cursor_pos[0], self.cursor_pos[1])
                    else:
                        self.app.inform.emit(_("Zone added. Click to start adding next zone or right click to finish."))
                        self.app.delete_selection_shape()

                        curr_pos = self.app.plotcanvas.translate_coords(event.pos)
                        if self.app.grid_status() == True:
                            curr_pos = self.app.geo_editor.snap(curr_pos[0], curr_pos[1])

                        x0, y0 = self.cursor_pos[0], self.cursor_pos[1]
                        x1, y1 = curr_pos[0], curr_pos[1]
                        pt1 = (x0, y0)
                        pt2 = (x1, y0)
                        pt3 = (x1, y1)
                        pt4 = (x0, y1)
                        self.sel_rect.append(Polygon([pt1, pt2, pt3, pt4]))
                        self.first_click = False
                        return
                        # modifiers = QtWidgets.QApplication.keyboardModifiers()
                        #
                        # if modifiers == QtCore.Qt.ShiftModifier:
                        #     mod_key = 'Shift'
                        # elif modifiers == QtCore.Qt.ControlModifier:
                        #     mod_key = 'Control'
                        # else:
                        #     mod_key = None
                        #
                        # if mod_key == self.app.defaults["global_mselect_key"]:
                        #     self.first_click = False
                        #     return
                        #
                        # self.sel_rect = cascaded_union(self.sel_rect)
                        # self.paint_poly_area(obj=self.paint_obj,
                        #                      tooldia=tooldia_list,
                        #                      sel_obj= self.sel_rect,
                        #                      outname=o_name,
                        #                      overlap=overlap,
                        #                      connect=connect,
                        #                      contour=contour)
                        #
                        # self.app.plotcanvas.vis_disconnect('mouse_release', on_mouse_release)
                        # self.app.plotcanvas.vis_disconnect('mouse_move', on_mouse_move)
                        #
                        # self.app.plotcanvas.vis_connect('mouse_press', self.app.on_mouse_click_over_plot)
                        # self.app.plotcanvas.vis_connect('mouse_move', self.app.on_mouse_move_over_plot)
                        # self.app.plotcanvas.vis_connect('mouse_release', self.app.on_mouse_click_release_over_plot)
                elif event.button == 2 and self.mouse_is_dragging is False:
                    self.first_click = False

                    self.app.plotcanvas.vis_disconnect('mouse_release', on_mouse_release)
                    self.app.plotcanvas.vis_disconnect('mouse_move', on_mouse_move)

                    self.app.plotcanvas.vis_connect('mouse_press', self.app.on_mouse_click_over_plot)
                    self.app.plotcanvas.vis_connect('mouse_move', self.app.on_mouse_move_over_plot)
                    self.app.plotcanvas.vis_connect('mouse_release', self.app.on_mouse_click_release_over_plot)

                    if len(self.sel_rect) == 0:
                        return

                    self.sel_rect = cascaded_union(self.sel_rect)
                    self.paint_poly_area(obj=self.paint_obj,
                                         tooldia=tooldia_list,
                                         sel_obj=self.sel_rect,
                                         outname=o_name,
                                         overlap=overlap,
                                         connect=connect,
                                         contour=contour)

            # called on mouse move
            def on_mouse_move(event):
                curr_pos = self.app.plotcanvas.translate_coords(event.pos)
                self.app.app_cursor.enabled = False

                # detect mouse dragging motion
                if event.is_dragging is True:
                    self.mouse_is_dragging = True
                else:
                    self.mouse_is_dragging = False

                # update the cursor position
                if self.app.grid_status() == True:
                    self.app.app_cursor.enabled = True
                    # Update cursor
                    curr_pos = self.app.geo_editor.snap(curr_pos[0], curr_pos[1])
                    self.app.app_cursor.set_data(np.asarray([(curr_pos[0], curr_pos[1])]),
                                                 symbol='++', edge_color='black', size=20)

                # draw the utility geometry
                if self.first_click:
                    self.app.delete_selection_shape()
                    self.app.draw_moving_selection_shape(old_coords=(self.cursor_pos[0], self.cursor_pos[1]),
                                                         coords=(curr_pos[0], curr_pos[1]),
                                                         face_alpha=0.0)

            self.app.plotcanvas.vis_disconnect('mouse_press', self.app.on_mouse_click_over_plot)
            self.app.plotcanvas.vis_disconnect('mouse_move', self.app.on_mouse_move_over_plot)
            self.app.plotcanvas.vis_disconnect('mouse_release', self.app.on_mouse_click_release_over_plot)

            self.app.plotcanvas.vis_connect('mouse_release', on_mouse_release)
            self.app.plotcanvas.vis_connect('mouse_move', on_mouse_move)

        elif select_method == 'ref':
            self.bound_obj_name = self.box_combo.currentText()
            # Get source object.
            try:
                self.bound_obj = self.app.collection.get_by_name(self.bound_obj_name)
            except Exception as e:
                self.app.inform.emit('[ERROR_NOTCL] %s: %s' %
                                     (_("Could not retrieve object"),
                                      self.obj_name))
                return "Could not retrieve object: %s" % self.obj_name

            self.paint_poly_ref(obj=self.paint_obj,
                                sel_obj=self.bound_obj,
                                tooldia=tooldia_list,
                                overlap=overlap,
                                outname=o_name,
                                connect=connect,
                                contour=contour)

    def paint_poly(self, obj,
                   inside_pt=None,
                   tooldia=None,
                   overlap=None,
                   order=None,
                   margin=None,
                   method=None,
                   outname=None,
                   connect=None,
                   contour=None,
                   tools_storage=None):
        """
        Paints a polygon selected by clicking on its interior or by having a point coordinates given

        Note:
            * The margin is taken directly from the form.
        :param obj: painted object
        :param inside_pt: [x, y]
        :param tooldia: Diameter of the painting tool
        :param overlap: Overlap of the tool between passes.
        :param order: if the tools are ordered and how
        :param margin: a border around painting area
        :param outname: Name of the resulting Geometry Object.
        :param connect: Connect lines to avoid tool lifts.
        :param contour: Paint around the edges.
        :param method: choice out of 'seed', 'normal', 'lines'
        :param tools_storage: whether to use the current tools_storage self.paints_tools or a different one.
        Usage of the different one is related to when this function is called from a TcL command.
        :return: None
        """

        # Which polygon.
        # poly = find_polygon(self.solid_geometry, inside_pt)
        poly = self.find_polygon(point=inside_pt, geoset=obj.solid_geometry)
        paint_method = method if method is None else self.paintmethod_combo.get_value()

        if margin is not None:
            paint_margin = margin
        else:
            try:
                paint_margin = float(self.paintmargin_entry.get_value())
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    paint_margin = float(self.paintmargin_entry.get_value().replace(',', '.'))
                except ValueError:
                    self.app.inform.emit('[ERROR_NOTCL] %s' %
                                         _("Wrong value format entered, use a number."))
                    return

        # No polygon?
        if poly is None:
            self.app.log.warning('No polygon found.')
            self.app.inform.emit(_('[WARNING] No polygon found.'))
            return

        proc = self.app.proc_container.new(_("Painting polygon..."))
        self.app.inform.emit(_("Paint Tool. Painting polygon at location: %s") % str(inside_pt))

        name = outname if outname is not None else self.obj_name + "_paint"

        over = overlap if overlap is not None else float(self.app.defaults["tools_paintoverlap"])
        conn = connect if connect is not None else self.app.defaults["tools_pathconnect"]
        cont = contour if contour is not None else self.app.defaults["tools_paintcontour"]
        order = order if order is not None else self.order_radio.get_value()

        sorted_tools = []
        if tooldia is not None:
            try:
                sorted_tools = [float(eval(dia)) for dia in tooldia.split(",") if dia != '']
            except AttributeError:
                if not isinstance(tooldia, list):
                    sorted_tools = [float(tooldia)]
                else:
                    sorted_tools = tooldia
        else:
            for row in range(self.tools_table.rowCount()):
                sorted_tools.append(float(self.tools_table.item(row, 1).text()))

        if tools_storage is not None:
            tools_storage = tools_storage
        else:
            tools_storage = self.paint_tools

        # Initializes the new geometry object
        def gen_paintarea(geo_obj, app_obj):
            # assert isinstance(geo_obj, FlatCAMGeometry), \
            #     "Initializer expected a FlatCAMGeometry, got %s" % type(geo_obj)
            # assert isinstance(app_obj, App)

            tool_dia = None
            if order == 'fwd':
                sorted_tools.sort(reverse=False)
            elif order == 'rev':
                sorted_tools.sort(reverse=True)
            else:
                pass

            def paint_p(polyg, tooldia):
                cpoly = None
                try:
                    if paint_method == "seed":
                        # Type(cp) == FlatCAMRTreeStorage | None
                        cpoly = self.clear_polygon2(polyg,
                                                    tooldia=tooldia,
                                                    steps_per_circle=self.app.defaults["geometry_circle_steps"],
                                                    overlap=over,
                                                    contour=cont,
                                                    connect=conn)

                    elif paint_method == "lines":
                        # Type(cp) == FlatCAMRTreeStorage | None
                        cpoly = self.clear_polygon3(polyg,
                                                    tooldia=tooldia,
                                                    steps_per_circle=self.app.defaults["geometry_circle_steps"],
                                                    overlap=over,
                                                    contour=cont,
                                                    connect=conn)

                    else:
                        # Type(cp) == FlatCAMRTreeStorage | None
                        cpoly = self.clear_polygon(polyg,
                                                   tooldia=tooldia,
                                                   steps_per_circle=self.app.defaults["geometry_circle_steps"],
                                                   overlap=over,
                                                   contour=cont,
                                                   connect=conn)
                except FlatCAMApp.GracefulException:
                    return "fail"
                except Exception as e:
                    log.debug("ToolPaint.paint_poly().gen_paintarea().paint_p() --> %s" % str(e))

                if cpoly is not None:
                    geo_obj.solid_geometry += list(cpoly.get_objects())
                    return cpoly
                else:
                    self.app.inform.emit('[ERROR_NOTCL] %s' %
                                         _('Geometry could not be painted completely'))
                    return None

            try:
                a, b, c, d = poly.bounds
                geo_obj.options['xmin'] = a
                geo_obj.options['ymin'] = b
                geo_obj.options['xmax'] = c
                geo_obj.options['ymax'] = d
            except Exception as e:
                log.debug("ToolPaint.paint_poly.gen_paintarea() bounds error --> %s" % str(e))
                return

            total_geometry = []
            current_uid = int(1)

            geo_obj.solid_geometry = []

            for tool_dia in sorted_tools:
                # find the tooluid associated with the current tool_dia so we know where to add the tool solid_geometry
                for k, v in tools_storage.items():
                    if float('%.4f' % v['tooldia']) == float('%.4f' % tool_dia):
                        current_uid = int(k)
                        break

                try:
                    poly_buf = poly.buffer(-paint_margin)
                    if isinstance(poly_buf, MultiPolygon):
                        cp = []
                        for pp in poly_buf:
                            cp.append(paint_p(pp, tooldia=tool_dia))
                    else:
                        cp = paint_p(poly_buf, tooldia=tool_dia)

                    if cp is not None:
                        if isinstance(cp, list):
                            for x in cp:
                                total_geometry += list(x.get_objects())
                        else:
                            total_geometry = list(cp.get_objects())
                except FlatCAMApp.GracefulException:
                    return "fail"
                except Exception as e:
                    log.debug("Could not Paint the polygons. %s" % str(e))
                    self.app.inform.emit('[ERROR] %s\n%s' %
                                         (_("Could not do Paint. Try a different combination of parameters. "
                                            "Or a different strategy of paint"),
                                          str(e)))
                    return "fail"

                # add the solid_geometry to the current too in self.paint_tools (tools_storage)
                # dictionary and then reset the temporary list that stored that solid_geometry
                tools_storage[current_uid]['solid_geometry'] = deepcopy(total_geometry)

                tools_storage[current_uid]['data']['name'] = name
                total_geometry[:] = []

            # delete tools with empty geometry
            keys_to_delete = []
            # look for keys in the tools_storage dict that have 'solid_geometry' values empty
            for uid in tools_storage:
                # if the solid_geometry (type=list) is empty
                if not tools_storage[uid]['solid_geometry']:
                    keys_to_delete.append(uid)

            # actual delete of keys from the tools_storage dict
            for k in keys_to_delete:
                tools_storage.pop(k, None)

            geo_obj.options["cnctooldia"] = str(tool_dia)
            # this turn on the FlatCAMCNCJob plot for multiple tools
            geo_obj.multigeo = True
            geo_obj.multitool = True
            geo_obj.tools.clear()
            geo_obj.tools = dict(tools_storage)

            # test if at least one tool has solid_geometry. If no tool has solid_geometry we raise an Exception
            has_solid_geo = 0
            for tooluid in geo_obj.tools:
                if geo_obj.tools[tooluid]['solid_geometry']:
                    has_solid_geo += 1
            if has_solid_geo == 0:
                self.app.inform.emit('[ERROR] %s' %
                                     _("There is no Painting Geometry in the file.\n"
                                       "Usually it means that the tool diameter is too big for the painted geometry.\n"
                                       "Change the painting parameters and try again."))
                return

            self.app.inform.emit('[success] %s' % _("Paint Single Done."))

            # Experimental...
            # print("Indexing...", end=' ')
            # geo_obj.make_index()
            # if errors == 0:
            #     print("[success] Paint single polygon Done")
            #     self.app.inform.emit("[success] Paint single polygon Done")
            # else:
            #     print("[WARNING] Paint single polygon done with errors")
            #     self.app.inform.emit("[WARNING] Paint single polygon done with errors. "
            #                          "%d area(s) could not be painted.\n"
            #                          "Use different paint parameters or edit the paint geometry and correct"
            #                          "the issue."
            #                          % errors)

        def job_thread(app_obj):
            try:
                app_obj.new_object("geometry", name, gen_paintarea)
            except FlatCAMApp.GracefulException:
                proc.done()
                return
            except Exception as e:
                proc.done()
                self.app.inform.emit('[ERROR_NOTCL] %s --> %s' %
                                     (_('PaintTool.paint_poly()'),
                                      str(e)))
                return
            proc.done()
            # focus on Selected Tab
            self.app.ui.notebook.setCurrentWidget(self.app.ui.selected_tab)

        self.app.inform.emit(_("Polygon Paint started ..."))

        # Promise object with the new name
        self.app.collection.promise(name)

        # Background
        self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})

    def paint_poly_all(self, obj,
                       tooldia=None,
                       overlap=None,
                       order=None,
                       margin=None,
                       method=None,
                       outname=None,
                       connect=None,
                       contour=None,
                       tools_storage=None):
        """
        Paints all polygons in this object.

        :param obj: painted object
        :param tooldia: a tuple or single element made out of diameters of the tools to be used
        :param overlap: value by which the paths will overlap
        :param order: if the tools are ordered and how
        :param margin: a border around painting area
        :param outname: name of the resulting object
        :param connect: Connect lines to avoid tool lifts.
        :param contour: Paint around the edges.
        :param method: choice out of 'seed', 'normal', 'lines'
        :param tools_storage: whether to use the current tools_storage self.paints_tools or a different one.
        Usage of the different one is related to when this function is called from a TcL command.
        :return:
        """
        paint_method = method if method is None else self.paintmethod_combo.get_value()

        if margin is not None:
            paint_margin = margin
        else:
            try:
                paint_margin = float(self.paintmargin_entry.get_value())
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    paint_margin = float(self.paintmargin_entry.get_value().replace(',', '.'))
                except ValueError:
                    self.app.inform.emit('[ERROR_NOTCL] %s' %
                                         _("Wrong value format entered, use a number."))
                    return

        proc = self.app.proc_container.new(_("Painting polygons..."))
        name = outname if outname is not None else self.obj_name + "_paint"

        over = overlap if overlap is not None else float(self.app.defaults["tools_paintoverlap"])
        conn = connect if connect is not None else self.app.defaults["tools_pathconnect"]
        cont = contour if contour is not None else self.app.defaults["tools_paintcontour"]
        order = order if order is not None else self.order_radio.get_value()

        sorted_tools = []
        if tooldia is not None:
            try:
                sorted_tools = [float(eval(dia)) for dia in tooldia.split(",") if dia != '']
            except AttributeError:
                if not isinstance(tooldia, list):
                    sorted_tools = [float(tooldia)]
                else:
                    sorted_tools = tooldia
        else:
            for row in range(self.tools_table.rowCount()):
                sorted_tools.append(float(self.tools_table.item(row, 1).text()))

        if tools_storage is not None:
            tools_storage = tools_storage
        else:
            tools_storage = self.paint_tools
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
            if self.app.abort_flag:
                # graceful abort requested by the user
                raise FlatCAMApp.GracefulException

            if geometry is None:
                return

            if reset:
                self.flat_geometry = []

            # ## If iterable, expand recursively.
            try:
                for geo in geometry:
                    if geo is not None:
                        recurse(geometry=geo, reset=False)

            # ## Not iterable, do the actual indexing and add.
            except TypeError:
                if isinstance(geometry, LinearRing):
                    g = Polygon(geometry)
                    self.flat_geometry.append(g)
                else:
                    self.flat_geometry.append(geometry)

            return self.flat_geometry

        # Initializes the new geometry object
        def gen_paintarea(geo_obj, app_obj):
            # assert isinstance(geo_obj, FlatCAMGeometry), \
            #     "Initializer expected a FlatCAMGeometry, got %s" % type(geo_obj)

            log.debug("Paint Tool. Normal painting all task started.")
            app_obj.inform.emit(_("Paint Tool. Normal painting all task started."))

            tool_dia = None
            if order == 'fwd':
                sorted_tools.sort(reverse=False)
            elif order == 'rev':
                sorted_tools.sort(reverse=True)
            else:
                pass

            try:
                a, b, c, d = obj.bounds()
                geo_obj.options['xmin'] = a
                geo_obj.options['ymin'] = b
                geo_obj.options['xmax'] = c
                geo_obj.options['ymax'] = d
            except Exception as e:
                log.debug("ToolPaint.paint_poly.gen_paintarea() bounds error --> %s" % str(e))
                return

            total_geometry = []
            current_uid = int(1)

            geo_obj.solid_geometry = []
            for tool_dia in sorted_tools:
                log.debug("Starting geometry processing for tool: %s" % str(tool_dia))
                app_obj.inform.emit(
                    '[success] %s %s%s %s' % (_('Painting with tool diameter = '),
                                              str(tool_dia),
                                              self.units.lower(),
                                              _('started'))
                )
                app_obj.proc_container.update_view_text(' %d%%' % 0)

                # find the tooluid associated with the current tool_dia so we know where to add the tool solid_geometry
                for k, v in tools_storage.items():
                    if float('%.4f' % v['tooldia']) == float('%.4f' % tool_dia):
                        current_uid = int(k)
                        break

                painted_area = recurse(obj.solid_geometry)
                # variables to display the percentage of work done
                geo_len = len(painted_area)
                disp_number = 0
                old_disp_number = 0
                log.warning("Total number of polygons to be cleared. %s" % str(geo_len))

                pol_nr = 0
                for geo in painted_area:
                    try:
                        # Polygons are the only really paintable geometries, lines in theory have no area to be painted
                        if not isinstance(geo, Polygon):
                            continue
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
                    except FlatCAMApp.GracefulException:
                        return "fail"
                    except Exception as e:
                        log.debug("Could not Paint the polygons. %s" % str(e))
                        self.app.inform.emit('[ERROR] %s\n%s' %
                                             (_("Could not do Paint All. Try a different combination of parameters. "
                                                "Or a different Method of paint"),
                                              str(e)))
                        return "fail"

                    pol_nr += 1
                    disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 99]))
                    # log.debug("Polygons cleared: %d" % pol_nr)

                    if old_disp_number < disp_number <= 100:
                        app_obj.proc_container.update_view_text(' %d%%' % disp_number)
                        old_disp_number = disp_number
                        # log.debug("Polygons cleared: %d. Percentage done: %d%%" % (pol_nr, disp_number))

                # add the solid_geometry to the current too in self.paint_tools (tools_storage)
                # dictionary and then reset the temporary list that stored that solid_geometry
                tools_storage[current_uid]['solid_geometry'] = deepcopy(total_geometry)

                tools_storage[current_uid]['data']['name'] = name
                total_geometry[:] = []

            # delete tools with empty geometry
            keys_to_delete = []
            # look for keys in the tools_storage dict that have 'solid_geometry' values empty
            for uid in tools_storage:
                # if the solid_geometry (type=list) is empty
                if not tools_storage[uid]['solid_geometry']:
                    keys_to_delete.append(uid)

            # actual delete of keys from the tools_storage dict
            for k in keys_to_delete:
                tools_storage.pop(k, None)

            geo_obj.options["cnctooldia"] = str(tool_dia)
            # this turn on the FlatCAMCNCJob plot for multiple tools
            geo_obj.multigeo = True
            geo_obj.multitool = True
            geo_obj.tools.clear()
            geo_obj.tools = dict(tools_storage)

            # test if at least one tool has solid_geometry. If no tool has solid_geometry we raise an Exception
            has_solid_geo = 0
            for tooluid in geo_obj.tools:
                if geo_obj.tools[tooluid]['solid_geometry']:
                    has_solid_geo += 1
            if has_solid_geo == 0:
                self.app.inform.emit('[ERROR] %s' %
                                     _("There is no Painting Geometry in the file.\n"
                                       "Usually it means that the tool diameter is too big for the painted geometry.\n"
                                       "Change the painting parameters and try again."))
                return

            # Experimental...
            # print("Indexing...", end=' ')
            # geo_obj.make_index()

            self.app.inform.emit(_("[success] Paint All Done."))

        # Initializes the new geometry object
        def gen_paintarea_rest_machining(geo_obj, app_obj):
            assert isinstance(geo_obj, FlatCAMGeometry), \
                "Initializer expected a FlatCAMGeometry, got %s" % type(geo_obj)

            log.debug("Paint Tool. Rest machining painting all task started.")
            app_obj.inform.emit(_("Paint Tool. Rest machining painting all task started."))

            tool_dia = None
            sorted_tools.sort(reverse=True)

            cleared_geo = []
            current_uid = int(1)
            geo_obj.solid_geometry = []

            try:
                a, b, c, d = obj.bounds()
                geo_obj.options['xmin'] = a
                geo_obj.options['ymin'] = b
                geo_obj.options['xmax'] = c
                geo_obj.options['ymax'] = d
            except Exception as e:
                log.debug("ToolPaint.paint_poly.gen_paintarea() bounds error --> %s" % str(e))
                return

            for tool_dia in sorted_tools:
                log.debug("Starting geometry processing for tool: %s" % str(tool_dia))
                app_obj.inform.emit(
                    '[success] %s %s%s %s' % (_('Painting with tool diameter = '),
                                              str(tool_dia),
                                              self.units.lower(),
                                              _('started'))
                )
                app_obj.proc_container.update_view_text(' %d%%' % 0)

                painted_area = recurse(obj.solid_geometry)
                # variables to display the percentage of work done
                geo_len = int(len(painted_area) / 100)
                disp_number = 0
                old_disp_number = 0
                log.warning("Total number of polygons to be cleared. %s" % str(geo_len))

                pol_nr = 0
                for geo in painted_area:
                    try:
                        geo = Polygon(geo) if not isinstance(geo, Polygon) else geo
                        poly_buf = geo.buffer(-paint_margin)
                        cp = None

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
                    except FlatCAMApp.GracefulException:
                        return "fail"
                    except Exception as e:
                        log.debug("Could not Paint the polygons. %s" % str(e))
                        self.app.inform.emit('[ERROR] %s\n%s' %
                                             (_("Could not do Paint All. Try a different combination of parameters. "
                                                "Or a different Method of paint"),
                                              str(e)))
                        return "fail"

                    pol_nr += 1
                    disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 99]))
                    # log.debug("Polygons cleared: %d" % pol_nr)

                    if old_disp_number < disp_number <= 100:
                        app_obj.proc_container.update_view_text(' %d%%' % disp_number)
                        old_disp_number = disp_number
                        # log.debug("Polygons cleared: %d. Percentage done: %d%%" % (pol_nr, disp_number))

                # find the tooluid associated with the current tool_dia so we know where to add the tool solid_geometry
                for k, v in tools_storage.items():
                    if float('%.4f' % v['tooldia']) == float('%.4f' % tool_dia):
                        current_uid = int(k)
                        break

                # add the solid_geometry to the current too in self.paint_tools (or tools_storage) dictionary and
                # then reset the temporary list that stored that solid_geometry
                tools_storage[current_uid]['solid_geometry'] = deepcopy(cleared_geo)

                tools_storage[current_uid]['data']['name'] = name
                cleared_geo[:] = []

            geo_obj.options["cnctooldia"] = str(tool_dia)
            # this turn on the FlatCAMCNCJob plot for multiple tools
            geo_obj.multigeo = True
            geo_obj.multitool = True
            geo_obj.tools.clear()
            geo_obj.tools = dict(tools_storage)

            # test if at least one tool has solid_geometry. If no tool has solid_geometry we raise an Exception
            has_solid_geo = 0
            for tooluid in geo_obj.tools:
                if geo_obj.tools[tooluid]['solid_geometry']:
                    has_solid_geo += 1
            if has_solid_geo == 0:
                self.app.inform.emit('[ERROR_NOTCL] %s' %
                                     _("There is no Painting Geometry in the file.\n"
                                       "Usually it means that the tool diameter is too big for the painted geometry.\n"
                                       "Change the painting parameters and try again."))
                return

            # Experimental...
            # print("Indexing...", end=' ')
            # geo_obj.make_index()

            self.app.inform.emit('[success] %s' % _("Paint All with Rest-Machining done."))

        def job_thread(app_obj):
            try:
                if self.rest_cb.isChecked():
                    app_obj.new_object("geometry", name, gen_paintarea_rest_machining)
                else:
                    app_obj.new_object("geometry", name, gen_paintarea)
            except FlatCAMApp.GracefulException:
                proc.done()
                return
            except Exception as e:
                proc.done()
                traceback.print_stack()
                return
            proc.done()
            # focus on Selected Tab
            self.app.ui.notebook.setCurrentWidget(self.app.ui.selected_tab)

        self.app.inform.emit(_("Polygon Paint started ..."))

        # Promise object with the new name
        self.app.collection.promise(name)

        # Background
        self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})

    def paint_poly_area(self, obj, sel_obj,
                        tooldia=None,
                        overlap=None,
                        order=None,
                        margin=None,
                        method=None,
                        outname=None,
                        connect=None,
                        contour=None,
                        tools_storage=None):
        """
        Paints all polygons in this object that are within the sel_obj object

        :param obj: painted object
        :param sel_obj: paint only what is inside this object bounds
        :param tooldia: a tuple or single element made out of diameters of the tools to be used
        :param overlap: value by which the paths will overlap
        :param order: if the tools are ordered and how
        :param margin: a border around painting area
        :param outname: name of the resulting object
        :param connect: Connect lines to avoid tool lifts.
        :param contour: Paint around the edges.
        :param method: choice out of 'seed', 'normal', 'lines'
        :param tools_storage: whether to use the current tools_storage self.paints_tools or a different one.
        Usage of the different one is related to when this function is called from a TcL command.
        :return:
        """
        paint_method = method if method is None else self.paintmethod_combo.get_value()

        if margin is not None:
            paint_margin = margin
        else:
            try:
                paint_margin = float(self.paintmargin_entry.get_value())
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    paint_margin = float(self.paintmargin_entry.get_value().replace(',', '.'))
                except ValueError:
                    self.app.inform.emit('[ERROR_NOTCL] %s' %
                                         _("Wrong value format entered, use a number."))
                    return

        proc = self.app.proc_container.new(_("Painting polygons..."))
        name = outname if outname is not None else self.obj_name + "_paint"

        over = overlap if overlap is not None else float(self.app.defaults["tools_paintoverlap"])
        conn = connect if connect is not None else self.app.defaults["tools_pathconnect"]
        cont = contour if contour is not None else self.app.defaults["tools_paintcontour"]
        order = order if order is not None else self.order_radio.get_value()

        sorted_tools = []
        if tooldia is not None:
            try:
                sorted_tools = [float(eval(dia)) for dia in tooldia.split(",") if dia != '']
            except AttributeError:
                if not isinstance(tooldia, list):
                    sorted_tools = [float(tooldia)]
                else:
                    sorted_tools = tooldia
        else:
            for row in range(self.tools_table.rowCount()):
                sorted_tools.append(float(self.tools_table.item(row, 1).text()))

        if tools_storage is not None:
            tools_storage = tools_storage
        else:
            tools_storage = self.paint_tools

        def recurse(geometry, reset=True):
            """
            Creates a list of non-iterable linear geometry objects.
            Results are placed in self.flat_geometry

            :param geometry: Shapely type or list or list of list of such.
            :param reset: Clears the contents of self.flat_geometry.
            """
            if self.app.abort_flag:
                # graceful abort requested by the user
                raise FlatCAMApp.GracefulException

            if geometry is None:
                return

            if reset:
                self.flat_geometry = []

            # ## If iterable, expand recursively.
            try:
                for geo in geometry:
                    if geo is not None:
                        recurse(geometry=geo, reset=False)

            # ## Not iterable, do the actual indexing and add.
            except TypeError:
                if isinstance(geometry, LinearRing):
                    g = Polygon(geometry)
                    self.flat_geometry.append(g)
                else:
                    self.flat_geometry.append(geometry)

            return self.flat_geometry

        # Initializes the new geometry object
        def gen_paintarea(geo_obj, app_obj):
            # assert isinstance(geo_obj, FlatCAMGeometry), \
            #     "Initializer expected a FlatCAMGeometry, got %s" % type(geo_obj)

            log.debug("Paint Tool. Normal painting area task started.")
            app_obj.inform.emit(_("Paint Tool. Normal painting area task started."))

            tool_dia = None
            if order == 'fwd':
                sorted_tools.sort(reverse=False)
            elif order == 'rev':
                sorted_tools.sort(reverse=True)
            else:
                pass

            # this is were heavy lifting is done and creating the geometry to be painted
            geo_to_paint = []
            if not isinstance(obj.solid_geometry, list):
                target_geo = [obj.solid_geometry]
            else:
                target_geo = obj.solid_geometry

            for poly in target_geo:
                new_pol = poly.intersection(sel_obj)
                geo_to_paint.append(new_pol)

            try:
                a, b, c, d = self.paint_bounds(geo_to_paint)
                geo_obj.options['xmin'] = a
                geo_obj.options['ymin'] = b
                geo_obj.options['xmax'] = c
                geo_obj.options['ymax'] = d
            except Exception as e:
                log.debug("ToolPaint.paint_poly.gen_paintarea() bounds error --> %s" % str(e))
                return

            total_geometry = []
            current_uid = int(1)

            geo_obj.solid_geometry = []
            for tool_dia in sorted_tools:
                log.debug("Starting geometry processing for tool: %s" % str(tool_dia))
                app_obj.inform.emit(
                    '[success] %s %s%s %s' % (_('Painting with tool diameter = '),
                                              str(tool_dia),
                                              self.units.lower(),
                                              _('started'))
                )
                app_obj.proc_container.update_view_text(' %d%%' % 0)

                # find the tooluid associated with the current tool_dia so we know where to add the tool solid_geometry
                for k, v in tools_storage.items():
                    if float('%.4f' % v['tooldia']) == float('%.4f' % tool_dia):
                        current_uid = int(k)
                        break

                painted_area = recurse(geo_to_paint)
                # variables to display the percentage of work done
                geo_len = len(painted_area)
                disp_number = 0
                old_disp_number = 0
                log.warning("Total number of polygons to be cleared. %s" % str(geo_len))

                pol_nr = 0
                for geo in painted_area:
                    try:
                        # Polygons are the only really paintable geometries, lines in theory have no area to be painted
                        if not isinstance(geo, Polygon):
                            continue
                        poly_buf = geo.buffer(-paint_margin)

                        cp = None
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
                    except FlatCAMApp.GracefulException:
                        return "fail"
                    except Exception as e:
                        log.debug("Could not Paint the polygons. %s" % str(e))
                        self.app.inform.emit('[ERROR] %s' %
                                             _("Could not do Paint All. Try a different combination of parameters. "
                                               "Or a different Method of paint\n%s") % str(e))
                        return

                    pol_nr += 1
                    disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 99]))
                    # log.debug("Polygons cleared: %d" % pol_nr)

                    if old_disp_number < disp_number <= 100:
                        app_obj.proc_container.update_view_text(' %d%%' % disp_number)
                        old_disp_number = disp_number
                        # log.debug("Polygons cleared: %d. Percentage done: %d%%" % (pol_nr, disp_number))

                # add the solid_geometry to the current too in self.paint_tools (tools_storage)
                # dictionary and then reset the temporary list that stored that solid_geometry
                tools_storage[current_uid]['solid_geometry'] = deepcopy(total_geometry)

                tools_storage[current_uid]['data']['name'] = name
                total_geometry[:] = []

            # delete tools with empty geometry
            keys_to_delete = []
            # look for keys in the tools_storage dict that have 'solid_geometry' values empty
            for uid in tools_storage:
                # if the solid_geometry (type=list) is empty
                if not tools_storage[uid]['solid_geometry']:
                    keys_to_delete.append(uid)

            # actual delete of keys from the tools_storage dict
            for k in keys_to_delete:
                tools_storage.pop(k, None)

            geo_obj.options["cnctooldia"] = str(tool_dia)
            # this turn on the FlatCAMCNCJob plot for multiple tools
            geo_obj.multigeo = True
            geo_obj.multitool = True
            geo_obj.tools.clear()
            geo_obj.tools = dict(tools_storage)

            # test if at least one tool has solid_geometry. If no tool has solid_geometry we raise an Exception
            has_solid_geo = 0
            for tooluid in geo_obj.tools:
                if geo_obj.tools[tooluid]['solid_geometry']:
                    has_solid_geo += 1
            if has_solid_geo == 0:
                self.app.inform.emit('[ERROR] %s' %
                                     _("There is no Painting Geometry in the file.\n"
                                       "Usually it means that the tool diameter is too big for the painted geometry.\n"
                                       "Change the painting parameters and try again."))
                return

            # Experimental...
            # print("Indexing...", end=' ')
            # geo_obj.make_index()

            self.app.inform.emit(_("[success] Paint Area Done."))

        # Initializes the new geometry object
        def gen_paintarea_rest_machining(geo_obj, app_obj):
            assert isinstance(geo_obj, FlatCAMGeometry), \
                "Initializer expected a FlatCAMGeometry, got %s" % type(geo_obj)

            log.debug("Paint Tool. Rest machining painting area task started.")
            app_obj.inform.emit(_("Paint Tool. Rest machining painting area task started."))

            tool_dia = None
            sorted_tools.sort(reverse=True)

            cleared_geo = []
            current_uid = int(1)
            geo_obj.solid_geometry = []

            try:
                a, b, c, d = obj.bounds()
                geo_obj.options['xmin'] = a
                geo_obj.options['ymin'] = b
                geo_obj.options['xmax'] = c
                geo_obj.options['ymax'] = d
            except Exception as e:
                log.debug("ToolPaint.paint_poly.gen_paintarea() bounds error --> %s" % str(e))
                return

            for tool_dia in sorted_tools:
                log.debug("Starting geometry processing for tool: %s" % str(tool_dia))
                app_obj.inform.emit(
                    '[success] %s %s%s %s' % (_('Painting with tool diameter = '),
                                              str(tool_dia),
                                              self.units.lower(),
                                              _('started'))
                )
                app_obj.proc_container.update_view_text(' %d%%' % 0)

                painted_area = recurse(obj.solid_geometry)
                # variables to display the percentage of work done
                geo_len = len(painted_area)
                disp_number = 0
                old_disp_number = 0
                log.warning("Total number of polygons to be cleared. %s" % str(geo_len))

                pol_nr = 0
                for geo in painted_area:
                    try:
                        geo = Polygon(geo) if not isinstance(geo, Polygon) else geo
                        poly_buf = geo.buffer(-paint_margin)
                        cp = None

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
                    except FlatCAMApp.GracefulException:
                        return "fail"
                    except Exception as e:
                        log.debug("Could not Paint the polygons. %s" % str(e))
                        self.app.inform.emit('[ERROR] %s' %
                                             _("Could not do Paint All. Try a different combination of parameters. "
                                               "Or a different Method of paint\n%s") % str(e))
                        return

                    pol_nr += 1
                    disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 99]))
                    # log.debug("Polygons cleared: %d" % pol_nr)

                    if old_disp_number < disp_number <= 100:
                        app_obj.proc_container.update_view_text(' %d%%' % disp_number)
                        old_disp_number = disp_number
                        # log.debug("Polygons cleared: %d. Percentage done: %d%%" % (pol_nr, disp_number))

                # find the tooluid associated with the current tool_dia so we know where to add the tool solid_geometry
                for k, v in tools_storage.items():
                    if float('%.4f' % v['tooldia']) == float('%.4f' % tool_dia):
                        current_uid = int(k)
                        break

                # add the solid_geometry to the current too in self.paint_tools (or tools_storage) dictionary and
                # then reset the temporary list that stored that solid_geometry
                tools_storage[current_uid]['solid_geometry'] = deepcopy(cleared_geo)

                tools_storage[current_uid]['data']['name'] = name
                cleared_geo[:] = []

            geo_obj.options["cnctooldia"] = str(tool_dia)
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
                self.app.inform.emit('[ERROR_NOTCL] %s' %
                                     _("There is no Painting Geometry in the file.\n"
                                       "Usually it means that the tool diameter is too big for the painted geometry.\n"
                                       "Change the painting parameters and try again."))
                return

            # Experimental...
            # print("Indexing...", end=' ')
            # geo_obj.make_index()

            self.app.inform.emit('[success] %s' % _("Paint All with Rest-Machining done."))

        def job_thread(app_obj):
            try:
                if self.rest_cb.isChecked():
                    app_obj.new_object("geometry", name, gen_paintarea_rest_machining)
                else:
                    app_obj.new_object("geometry", name, gen_paintarea)
            except FlatCAMApp.GracefulException:
                proc.done()
                return
            except Exception as e:
                proc.done()
                traceback.print_stack()
                return
            proc.done()
            # focus on Selected Tab
            self.app.ui.notebook.setCurrentWidget(self.app.ui.selected_tab)

        self.app.inform.emit(_("Polygon Paint started ..."))

        # Promise object with the new name
        self.app.collection.promise(name)

        # Background
        self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})

    def paint_poly_ref(self, obj, sel_obj,
                       tooldia=None,
                       overlap=None,
                       order=None,
                       margin=None,
                       method=None,
                       outname=None,
                       connect=None,
                       contour=None,
                       tools_storage=None):
        """
        Paints all polygons in this object that are within the sel_obj object

        :param obj: painted object
        :param sel_obj: paint only what is inside this object bounds
        :param tooldia: a tuple or single element made out of diameters of the tools to be used
        :param overlap: value by which the paths will overlap
        :param order: if the tools are ordered and how
        :param margin: a border around painting area
        :param outname: name of the resulting object
        :param connect: Connect lines to avoid tool lifts.
        :param contour: Paint around the edges.
        :param method: choice out of 'seed', 'normal', 'lines'
        :param tools_storage: whether to use the current tools_storage self.paints_tools or a different one.
        Usage of the different one is related to when this function is called from a TcL command.
        :return:
        """
        geo = sel_obj.solid_geometry
        try:
            if isinstance(geo, MultiPolygon):
                env_obj = geo.convex_hull
            elif (isinstance(geo, MultiPolygon) and len(geo) == 1) or \
                    (isinstance(geo, list) and len(geo) == 1) and isinstance(geo[0], Polygon):
                env_obj = cascaded_union(self.bound_obj.solid_geometry)
            else:
                env_obj = cascaded_union(self.bound_obj.solid_geometry)
                env_obj = env_obj.convex_hull
            sel_rect = env_obj.buffer(distance=0.0000001, join_style=base.JOIN_STYLE.mitre)
        except Exception as e:
            log.debug("ToolPaint.on_paint_button_click() --> %s" % str(e))
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("No object available."))
            return

        self.paint_poly_area(obj=obj,
                             sel_obj=sel_rect,
                             tooldia=tooldia,
                             overlap=overlap,
                             order=order,
                             margin=margin,
                             method=method,
                             outname=outname,
                             connect=connect,
                             contour=contour,
                             tools_storage=tools_storage)

    @staticmethod
    def paint_bounds(geometry):
        def bounds_rec(o):
            if type(o) is list:
                minx = Inf
                miny = Inf
                maxx = -Inf
                maxy = -Inf

                for k in o:
                    try:
                        minx_, miny_, maxx_, maxy_ = bounds_rec(k)
                    except Exception as e:
                        log.debug("ToolPaint.bounds() --> %s" % str(e))
                        return

                    minx = min(minx, minx_)
                    miny = min(miny, miny_)
                    maxx = max(maxx, maxx_)
                    maxy = max(maxy, maxy_)
                return minx, miny, maxx, maxy
            else:
                # it's a Shapely object, return it's bounds
                return o.bounds

        return bounds_rec(geometry)

    def reset_fields(self):
        self.obj_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
