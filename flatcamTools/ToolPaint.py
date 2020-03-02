# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Modified: Marius Adrian Stanciu (c)                 #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt

from FlatCAMTool import FlatCAMTool
from copy import deepcopy
# from ObjectCollection import *
from flatcamParsers.ParseGerber import Gerber
from FlatCAMObj import FlatCAMGerber, FlatCAMGeometry
from camlib import Geometry, FlatCAMRTreeStorage
from flatcamGUI.GUIElements import FCTable, FCDoubleSpinner, FCCheckBox, FCInputDialog, RadioSet, FCButton, FCComboBox
import FlatCAMApp

from shapely.geometry import base, Polygon, MultiPolygon, LinearRing, Point, MultiLineString
from shapely.ops import cascaded_union, unary_union, linemerge

import numpy as np
import math
from numpy import Inf
import traceback
import logging

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class ToolPaint(FlatCAMTool, Gerber):

    toolName = _("Paint Tool")

    def __init__(self, app):
        self.app = app
        self.decimals = self.app.decimals

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
        grid0 = QtWidgets.QGridLayout()
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        self.tools_box.addLayout(grid0)

        # ################################################
        # ##### Type of object to be painted #############
        # ################################################

        self.type_obj_combo_label = QtWidgets.QLabel('%s:' % _("Obj Type"))
        self.type_obj_combo_label.setToolTip(
            _("Specify the type of object to be painted.\n"
              "It can be of type: Gerber or Geometry.\n"
              "What is selected here will dictate the kind\n"
              "of objects that will populate the 'Object' combobox.")
        )
        self.type_obj_combo_label.setMinimumWidth(60)

        self.type_obj_combo = RadioSet([{'label': "Geometry", 'value': 'geometry'},
                                        {'label': "Gerber", 'value': 'gerber'}])

        grid0.addWidget(self.type_obj_combo_label, 1, 0)
        grid0.addWidget(self.type_obj_combo, 1, 1)

        # ################################################
        # ##### The object to be painted #################
        # ################################################
        self.obj_combo = FCComboBox()
        self.obj_combo.setModel(self.app.collection)
        self.obj_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.obj_combo.set_last = True

        self.object_label = QtWidgets.QLabel('%s:' % _("Object"))
        self.object_label.setToolTip(_("Object to be painted."))

        grid0.addWidget(self.object_label, 2, 0)
        grid0.addWidget(self.obj_combo, 2, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 5, 0, 1, 2)

        # ### Tools ## ##
        self.tools_table_label = QtWidgets.QLabel('<b>%s</b>' % _('Tools Table'))
        self.tools_table_label.setToolTip(
            _("Tools pool from which the algorithm\n"
              "will pick the ones used for painting.")
        )

        self.tools_table = FCTable()

        grid0.addWidget(self.tools_table_label, 6, 0, 1, 2)
        grid0.addWidget(self.tools_table, 7, 0, 1, 2)

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

        grid0.addWidget(self.order_label, 9, 0)
        grid0.addWidget(self.order_radio, 9, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 10, 0, 1, 2)

        self.grid3 = QtWidgets.QGridLayout()
        self.tools_box.addLayout(self.grid3)
        self.grid3.setColumnStretch(0, 0)
        self.grid3.setColumnStretch(1, 1)

        # ##############################################################################
        # ###################### ADD A NEW TOOL ########################################
        # ##############################################################################
        self.tool_sel_label = QtWidgets.QLabel('<b>%s</b>' % _("New Tool"))
        self.grid3.addWidget(self.tool_sel_label, 1, 0, 1, 2)

        # Tool Type Radio Button
        self.tool_type_label = QtWidgets.QLabel('%s:' % _('Tool Type'))
        self.tool_type_label.setToolTip(
            _("Default tool type:\n"
              "- 'V-shape'\n"
              "- Circular")
        )

        self.tool_type_radio = RadioSet([{'label': _('V-shape'), 'value': 'V'},
                                         {'label': _('Circular'), 'value': 'C1'}])
        self.tool_type_radio.setToolTip(
            _("Default tool type:\n"
              "- 'V-shape'\n"
              "- Circular")
        )
        self.tool_type_radio.setObjectName('p_tool_type')

        self.grid3.addWidget(self.tool_type_label, 2, 0)
        self.grid3.addWidget(self.tool_type_radio, 2, 1)

        # Tip Dia
        self.tipdialabel = QtWidgets.QLabel('%s:' % _('V-Tip Dia'))
        self.tipdialabel.setToolTip(
            _("The tip diameter for V-Shape Tool"))
        self.tipdia_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.tipdia_entry.set_precision(self.decimals)
        self.tipdia_entry.set_range(0.0000, 9999.9999)
        self.tipdia_entry.setSingleStep(0.1)
        self.tipdia_entry.setObjectName('p_vtip_dia')

        self.grid3.addWidget(self.tipdialabel, 3, 0)
        self.grid3.addWidget(self.tipdia_entry, 3, 1)

        # Tip Angle
        self.tipanglelabel = QtWidgets.QLabel('%s:' % _('V-Tip Angle'))
        self.tipanglelabel.setToolTip(
            _("The tip angle for V-Shape Tool.\n"
              "In degree."))
        self.tipangle_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.tipangle_entry.set_precision(self.decimals)
        self.tipangle_entry.set_range(0.0000, 180.0000)
        self.tipangle_entry.setSingleStep(5)
        self.tipangle_entry.setObjectName('p_vtip_angle')

        self.grid3.addWidget(self.tipanglelabel, 4, 0)
        self.grid3.addWidget(self.tipangle_entry, 4, 1)

        # Cut Z entry
        cutzlabel = QtWidgets.QLabel('%s:' % _('Cut Z'))
        cutzlabel.setToolTip(
            _("Depth of cut into material. Negative value.\n"
              "In FlatCAM units.")
        )
        self.cutz_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.cutz_entry.set_precision(self.decimals)
        self.cutz_entry.set_range(-99999.9999, 0.0000)
        self.cutz_entry.setObjectName('p_cutz')

        self.cutz_entry.setToolTip(
            _("Depth of cut into material. Negative value.\n"
              "In FlatCAM units.")
        )
        self.grid3.addWidget(cutzlabel, 5, 0)
        self.grid3.addWidget(self.cutz_entry, 5, 1)

        # ### Tool Diameter ####
        self.addtool_entry_lbl = QtWidgets.QLabel('<b>%s:</b>' % _('Tool Dia'))
        self.addtool_entry_lbl.setToolTip(
            _("Diameter for the new tool to add in the Tool Table.\n"
              "If the tool is V-shape type then this value is automatically\n"
              "calculated from the other parameters.")
        )
        self.addtool_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.addtool_entry.set_precision(self.decimals)
        self.addtool_entry.set_range(0.000, 9999.9999)
        self.addtool_entry.setObjectName('p_tool_dia')

        self.grid3.addWidget(self.addtool_entry_lbl, 6, 0)
        self.grid3.addWidget(self.addtool_entry, 6, 1)

        hlay = QtWidgets.QHBoxLayout()

        self.addtool_btn = QtWidgets.QPushButton(_('Add'))
        self.addtool_btn.setToolTip(
            _("Add a new tool to the Tool Table\n"
              "with the diameter specified above.")
        )

        self.addtool_from_db_btn = QtWidgets.QPushButton(_('Add from DB'))
        self.addtool_from_db_btn.setToolTip(
            _("Add a new tool to the Tool Table\n"
              "from the Tool DataBase.")
        )

        hlay.addWidget(self.addtool_btn)
        hlay.addWidget(self.addtool_from_db_btn)

        self.grid3.addLayout(hlay, 7, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.grid3.addWidget(separator_line, 8, 0, 1, 2)

        self.deltool_btn = QtWidgets.QPushButton(_('Delete'))
        self.deltool_btn.setToolTip(
            _("Delete a selection of tools in the Tool Table\n"
              "by first selecting a row(s) in the Tool Table.")
        )
        self.grid3.addWidget(self.deltool_btn, 9, 0, 1, 2)

        self.grid3.addWidget(QtWidgets.QLabel(''), 10, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.grid3.addWidget(separator_line, 11, 0, 1, 2)

        self.tool_data_label = QtWidgets.QLabel(
            "<b>%s: <font color='#0000FF'>%s %d</font></b>" % (_('Parameters for'), _("Tool"), int(1)))
        self.tool_data_label.setToolTip(
            _(
                "The data used for creating GCode.\n"
                "Each tool store it's own set of such data."
            )
        )
        self.grid3.addWidget(self.tool_data_label, 12, 0, 1, 2)

        grid4 = QtWidgets.QGridLayout()
        grid4.setColumnStretch(0, 0)
        grid4.setColumnStretch(1, 1)
        self.tools_box.addLayout(grid4)

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
        self.paintoverlap_entry = FCDoubleSpinner(callback=self.confirmation_message, suffix='%')
        self.paintoverlap_entry.set_precision(3)
        self.paintoverlap_entry.setWrapping(True)
        self.paintoverlap_entry.setRange(0.0000, 99.9999)
        self.paintoverlap_entry.setSingleStep(0.1)
        self.paintoverlap_entry.setObjectName('p_overlap')

        grid4.addWidget(ovlabel, 1, 0)
        grid4.addWidget(self.paintoverlap_entry, 1, 1)

        # Margin
        marginlabel = QtWidgets.QLabel('%s:' % _('Margin'))
        marginlabel.setToolTip(
            _("Distance by which to avoid\n"
              "the edges of the polygon to\n"
              "be painted.")
        )
        self.paintmargin_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.paintmargin_entry.set_precision(self.decimals)
        self.paintmargin_entry.set_range(-9999.9999, 9999.9999)
        self.paintmargin_entry.setObjectName('p_margin')

        grid4.addWidget(marginlabel, 2, 0)
        grid4.addWidget(self.paintmargin_entry, 2, 1)

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
        # self.paintmethod_combo = RadioSet([
        #     {"label": _("Standard"), "value": "standard"},
        #     {"label": _("Seed-based"), "value": _("Seed")},
        #     {"label": _("Straight lines"), "value": _("Lines")},
        #     {"label": _("Laser lines"), "value": _("Laser_lines")},
        #     {"label": _("Combo"), "value": _("Combo")}
        # ], orientation='vertical', stretch=False)

        # for choice in self.paintmethod_combo.choices:
        #     if choice['value'] == _("Laser_lines"):
        #         choice["radio"].setEnabled(False)

        self.paintmethod_combo = FCComboBox()
        self.paintmethod_combo.addItems(
            [_("Standard"), _("Seed"), _("Lines"), _("Laser_lines"), _("Combo")]
        )
        idx = self.paintmethod_combo.findText(_("Laser_lines"))
        self.paintmethod_combo.model().item(idx).setEnabled(False)

        self.paintmethod_combo.setObjectName('p_method')

        grid4.addWidget(methodlabel, 7, 0)
        grid4.addWidget(self.paintmethod_combo, 7, 1)

        # Connect lines
        self.pathconnect_cb = FCCheckBox('%s' % _("Connect"))
        self.pathconnect_cb.setObjectName('p_connect')
        self.pathconnect_cb.setToolTip(
            _("Draw lines between resulting\n"
              "segments to minimize tool lifts.")
        )

        self.paintcontour_cb = FCCheckBox('%s' % _("Contour"))
        self.paintcontour_cb.setObjectName('p_contour')
        self.paintcontour_cb.setToolTip(
            _("Cut around the perimeter of the polygon\n"
              "to trim rough edges.")
        )

        grid4.addWidget(self.pathconnect_cb, 10, 0)
        grid4.addWidget(self.paintcontour_cb, 10, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid4.addWidget(separator_line, 11, 0, 1, 2)

        self.apply_param_to_all = FCButton(_("Apply parameters to all tools"))
        self.apply_param_to_all.setToolTip(
            _("The parameters in the current form will be applied\n"
              "on all the tools from the Tool Table.")
        )
        grid4.addWidget(self.apply_param_to_all, 12, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid4.addWidget(separator_line, 13, 0, 1, 2)

        # General Parameters
        self.gen_param_label = QtWidgets.QLabel('<b>%s</b>' % _("Common Parameters"))
        self.gen_param_label.setToolTip(
            _("Parameters that are common for all tools.")
        )
        grid4.addWidget(self.gen_param_label, 15, 0, 1, 2)

        self.rest_cb = FCCheckBox('%s' % _("Rest Machining"))
        self.rest_cb.setObjectName('p_rest_machining')
        self.rest_cb.setToolTip(
            _("If checked, use 'rest machining'.\n"
              "Basically it will clear copper outside PCB features,\n"
              "using the biggest tool and continue with the next tools,\n"
              "from bigger to smaller, to clear areas of copper that\n"
              "could not be cleared by previous tool, until there is\n"
              "no more copper to clear or there are no more tools.\n\n"
              "If not checked, use the standard algorithm.")
        )
        grid4.addWidget(self.rest_cb, 16, 0, 1, 2)

        # Polygon selection
        selectlabel = QtWidgets.QLabel('%s:' % _('Selection'))
        selectlabel.setToolTip(
            _("Selection of area to be processed.\n"
              "- 'Polygon Selection' - left mouse click to add/remove polygons to be processed.\n"
              "- 'Area Selection' - left mouse click to start selection of the area to be processed.\n"
              "Keeping a modifier key pressed (CTRL or SHIFT) will allow to add multiple areas.\n"
              "- 'All Polygons' - the process will start after click.\n"
              "- 'Reference Object' - will process the area specified by another object.")
        )

        # grid3 = QtWidgets.QGridLayout()
        # self.selectmethod_combo = RadioSet([
        #     {"label": _("Polygon Selection"), "value": "single"},
        #     {"label": _("Area Selection"), "value": "area"},
        #     {"label": _("All Polygons"), "value": "all"},
        #     {"label": _("Reference Object"), "value": "ref"}
        # ], orientation='vertical', stretch=False)
        # self.selectmethod_combo.setObjectName('p_selection')
        # self.selectmethod_combo.setToolTip(
        #     _("How to select Polygons to be painted.\n"
        #       "- 'Polygon Selection' - left mouse click to add/remove polygons to be painted.\n"
        #       "- 'Area Selection' - left mouse click to start selection of the area to be painted.\n"
        #       "Keeping a modifier key pressed (CTRL or SHIFT) will allow to add multiple areas.\n"
        #       "- 'All Polygons' - the Paint will start after click.\n"
        #       "- 'Reference Object' - will do non copper clearing within the area\n"
        #       "specified by another object.")
        # )

        self.selectmethod_combo = FCComboBox()
        self.selectmethod_combo.addItems(
            [_("Polygon Selection"), _("Area Selection"), _("All Polygons"), _("Reference Object")]
        )
        self.selectmethod_combo.setObjectName('p_selection')

        grid4.addWidget(selectlabel, 18, 0)
        grid4.addWidget(self.selectmethod_combo, 18, 1)

        form1 = QtWidgets.QFormLayout()
        grid4.addLayout(form1, 20, 0, 1, 2)

        self.box_combo_type_label = QtWidgets.QLabel('%s:' % _("Ref. Type"))
        self.box_combo_type_label.setToolTip(
            _("The type of FlatCAM object to be used as paint reference.\n"
              "It can be Gerber, Excellon or Geometry.")
        )
        self.box_combo_type = FCComboBox()
        self.box_combo_type.addItem(_("Reference Gerber"))
        self.box_combo_type.addItem(_("Reference Excellon"))
        self.box_combo_type.addItem(_("Reference Geometry"))
        form1.addRow(self.box_combo_type_label, self.box_combo_type)

        self.box_combo_label = QtWidgets.QLabel('%s:' % _("Ref. Object"))
        self.box_combo_label.setToolTip(
            _("The FlatCAM object to be used as non copper clearing reference.")
        )
        self.box_combo = FCComboBox()
        self.box_combo.setModel(self.app.collection)
        self.box_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.box_combo.set_last = True
        form1.addRow(self.box_combo_label, self.box_combo)

        self.box_combo.hide()
        self.box_combo_label.hide()
        self.box_combo_type.hide()
        self.box_combo_type_label.hide()

        # GO Button
        self.generate_paint_button = QtWidgets.QPushButton(_('Generate Geometry'))
        self.generate_paint_button.setToolTip(
            _("- 'Area Selection' - left mouse click to start selection of the area to be painted.\n"
              "Keeping a modifier key pressed (CTRL or SHIFT) will allow to add multiple areas.\n"
              "- 'All Polygons' - the Paint will start after click.\n"
              "- 'Reference Object' -  will do non copper clearing within the area\n"
              "specified by another object.")
        )
        self.generate_paint_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)
        self.tools_box.addWidget(self.generate_paint_button)

        self.tools_box.addStretch()

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
        self.tools_box.addWidget(self.reset_button)

        # #################################### FINSIHED GUI ###########################
        # #############################################################################

        # #############################################################################
        # ########################## VARIABLES ########################################
        # #############################################################################

        self.obj_name = ""
        self.paint_obj = None
        self.bound_obj_name = ""
        self.bound_obj = None

        self.tooldia_list = []
        self.tooldia = None

        self.sel_rect = None
        self.o_name = None
        self.overlap = None
        self.connect = None
        self.contour = None
        self.select_method = None

        self.units = ''
        self.paint_tools = {}
        self.tooluid = 0
        self.first_click = False
        self.cursor_pos = None
        self.mouse_is_dragging = False

        self.mm = None
        self.mp = None
        self.mr = None

        self.sel_rect = []

        # store here if the grid snapping is active
        self.grid_status_memory = False

        # dict to store the polygons selected for painting; key is the shape added to be plotted and value is the poly
        self.poly_dict = {}

        # store here the default data for Geometry Data
        self.default_data = {}

        self.tool_type_item_options = ["C1", "C2", "C3", "C4", "B", "V"]

        self.form_fields = {
            "paintoverlap": self.paintoverlap_entry,
            "paintmargin": self.paintmargin_entry,
            "paintmethod": self.paintmethod_combo,
            "pathconnect": self.pathconnect_cb,
            "paintcontour": self.paintcontour_cb,
        }

        self.name2option = {
            'p_overlap': "paintoverlap",
            'p_margin': "paintmargin",
            'p_method': "paintmethod",
            'p_connect': "pathconnect",
            'p_contour': "paintcontour",
        }

        self.old_tool_dia = None

        # #############################################################################
        # ################################# Signals ###################################
        # #############################################################################
        self.addtool_btn.clicked.connect(self.on_tool_add)
        self.addtool_entry.returnPressed.connect(self.on_tool_add)
        self.deltool_btn.clicked.connect(self.on_tool_delete)

        self.tipdia_entry.returnPressed.connect(self.on_calculate_tooldia)
        self.tipangle_entry.returnPressed.connect(self.on_calculate_tooldia)
        self.cutz_entry.returnPressed.connect(self.on_calculate_tooldia)

        # self.copytool_btn.clicked.connect(lambda: self.on_tool_copy())
        # self.tools_table.itemChanged.connect(self.on_tool_edit)
        self.tools_table.clicked.connect(self.on_row_selection_change)

        self.generate_paint_button.clicked.connect(self.on_paint_button_click)
        self.selectmethod_combo.currentIndexChanged.connect(self.on_selection)
        self.order_radio.activated_custom[str].connect(self.on_order_changed)
        self.rest_cb.stateChanged.connect(self.on_rest_machining_check)

        self.box_combo_type.currentIndexChanged.connect(self.on_combo_box_type)
        self.type_obj_combo.activated_custom.connect(self.on_type_obj_changed)

        self.apply_param_to_all.clicked.connect(self.on_apply_param_to_all_clicked)

        self.reset_button.clicked.connect(self.set_tool_ui)

        # #############################################################################
        # ###################### Setup CONTEXT MENU ###################################
        # #############################################################################
        self.tools_table.setupContextMenu()
        self.tools_table.addContextMenu(
            _("Add"), self.on_add_tool_by_key, icon=QtGui.QIcon(self.app.resource_location + "/plus16.png")
        )
        self.tools_table.addContextMenu(
            _("Add from DB"), self.on_add_tool_by_key, icon=QtGui.QIcon(self.app.resource_location + "/plus16.png")
        )
        self.tools_table.addContextMenu(
            _("Delete"), lambda:
            self.on_tool_delete(rows_to_delete=None, all_tools=None),
            icon=QtGui.QIcon(self.app.resource_location + "/delete32.png")
        )

    def on_type_obj_changed(self, val):
        obj_type = 0 if val == 'gerber' else 2
        self.obj_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.obj_combo.setCurrentIndex(0)

        idx = self.paintmethod_combo.findText(_("Laser_lines"))
        if self.type_obj_combo.get_value().lower() == 'gerber':
            self.paintmethod_combo.model().item(idx).setEnabled(True)
        else:
            self.paintmethod_combo.model().item(idx).setEnabled(False)
            if self.paintmethod_combo.get_value() == _("Laser_lines"):
                self.paintmethod_combo.set_value(_("Lines"))

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, shortcut='ALT+P', **kwargs)

    def run(self, toggle=True):
        self.app.report_usage("ToolPaint()")
        log.debug("ToolPaint().run() was launched ...")

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

    def on_row_selection_change(self):
        self.blockSignals(True)

        sel_rows = [it.row() for it in self.tools_table.selectedItems()]
        # sel_rows = sorted(set(index.row() for index in self.tools_table.selectedIndexes()))

        if not sel_rows:
            sel_rows = [0]

        for current_row in sel_rows:
            # populate the form with the data from the tool associated with the row parameter
            try:
                item = self.tools_table.item(current_row, 3)
                if item is None:
                    return 'fail'
                tooluid = int(item.text())
            except Exception as e:
                log.debug("Tool missing. Add a tool in the Tool Table. %s" % str(e))
                return

            # update the QLabel that shows for which Tool we have the parameters in the UI form
            if len(sel_rows) == 1:
                cr = self.tools_table.item(current_row, 0).text()
                self.tool_data_label.setText(
                    "<b>%s: <font color='#0000FF'>%s %s</font></b>" % (_('Parameters for'), _("Tool"), cr)
                )

                try:
                    # set the form with data from the newly selected tool
                    for tooluid_key, tooluid_value in list(self.paint_tools.items()):
                        if int(tooluid_key) == tooluid:
                            for key, value in tooluid_value.items():
                                if key == 'data':
                                    form_value_storage = tooluid_value[key]
                                    self.storage_to_form(form_value_storage)
                except Exception as e:
                    log.debug("ToolPaint ---> update_ui() " + str(e))
            else:
                self.tool_data_label.setText(
                    "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("Multiple Tools"))
                )

        self.blockSignals(False)

    def storage_to_form(self, dict_storage):
        for form_key in self.form_fields:
            for storage_key in dict_storage:
                if form_key == storage_key:
                    try:
                        self.form_fields[form_key].set_value(dict_storage[form_key])
                    except Exception:
                        pass

    def form_to_storage(self):
        if self.tools_table.rowCount() == 0:
            # there is no tool in tool table so we can't save the GUI elements values to storage
            return

        self.blockSignals(True)

        widget_changed = self.sender()
        wdg_objname = widget_changed.objectName()
        option_changed = self.name2option[wdg_objname]

        # row = self.tools_table.currentRow()
        rows = sorted(set(index.row() for index in self.tools_table.selectedIndexes()))
        for row in rows:
            if row < 0:
                row = 0
            tooluid_item = int(self.tools_table.item(row, 3).text())

            for tooluid_key, tooluid_val in self.paint_tools.items():
                if int(tooluid_key) == tooluid_item:
                    new_option_value = self.form_fields[option_changed].get_value()
                    if option_changed in tooluid_val:
                        tooluid_val[option_changed] = new_option_value
                    if option_changed in tooluid_val['data']:
                        tooluid_val['data'][option_changed] = new_option_value

        self.blockSignals(False)

    def on_apply_param_to_all_clicked(self):
        if self.tools_table.rowCount() == 0:
            # there is no tool in tool table so we can't save the GUI elements values to storage
            log.debug("NonCopperClear.on_apply_param_to_all_clicked() --> no tool in Tools Table, aborting.")
            return

        self.blockSignals(True)

        row = self.tools_table.currentRow()
        if row < 0:
            row = 0

        tooluid_item = int(self.tools_table.item(row, 3).text())
        temp_tool_data = {}

        for tooluid_key, tooluid_val in self.paint_tools.items():
            if int(tooluid_key) == tooluid_item:
                # this will hold the 'data' key of the self.tools[tool] dictionary that corresponds to
                # the current row in the tool table
                temp_tool_data = tooluid_val['data']
                break

        for tooluid_key, tooluid_val in self.paint_tools.items():
            tooluid_val['data'] = deepcopy(temp_tool_data)

        self.app.inform.emit('[success] %s' % _("Current Tool parameters were applied to all tools."))

        self.blockSignals(False)

    def on_add_tool_by_key(self):
        tool_add_popup = FCInputDialog(title='%s...' % _("New Tool"),
                                       text='%s:' % _('Enter a Tool Diameter'),
                                       min=0.0000, max=99.9999, decimals=4)
        tool_add_popup.setWindowIcon(QtGui.QIcon(self.app.resource_location + '/letter_t_32.png'))

        val, ok = tool_add_popup.get_value()
        if ok:
            if float(val) == 0:
                self.app.inform.emit('[WARNING_NOTCL] %s' %
                                     _("Please enter a tool diameter with non-zero value, in Float format."))
                return
            self.on_tool_add(dia=float(val))
        else:
            self.app.inform.emit('[WARNING_NOTCL] %s...' % _("Adding Tool cancelled"))

    def on_tooltable_cellwidget_change(self):
        cw = self.sender()
        cw_index = self.tools_table.indexAt(cw.pos())
        cw_row = cw_index.row()
        cw_col = cw_index.column()

        current_uid = int(self.tools_table.item(cw_row, 3).text())

        # if the sender is in the column with index 2 then we update the tool_type key
        if cw_col == 2:
            tt = cw.currentText()
            typ = 'Iso' if tt == 'V' else "Rough"

            self.paint_tools[current_uid].update({
                'type': typ,
                'tool_type': tt,
            })

    def on_tool_type(self, val):
        if val == 'V':
            self.addtool_entry_lbl.setDisabled(True)
            self.addtool_entry.setDisabled(True)
            self.tipdialabel.show()
            self.tipdia_entry.show()
            self.tipanglelabel.show()
            self.tipangle_entry.show()

            self.on_calculate_tooldia()
        else:
            self.addtool_entry_lbl.setDisabled(False)
            self.addtool_entry.setDisabled(False)
            self.tipdialabel.hide()
            self.tipdia_entry.hide()
            self.tipanglelabel.hide()
            self.tipangle_entry.hide()

            self.addtool_entry.set_value(self.old_tool_dia)

    def on_calculate_tooldia(self):
        if self.tool_type_radio.get_value() == 'V':
            tip_dia = float(self.tipdia_entry.get_value())
            tip_angle = float(self.tipangle_entry.get_value()) / 2.0
            cut_z = float(self.cutz_entry.get_value())
            cut_z = -cut_z if cut_z < 0 else cut_z

            # calculated tool diameter so the cut_z parameter is obeyed
            tool_dia = tip_dia + (2 * cut_z * math.tan(math.radians(tip_angle)))

            # update the default_data so it is used in the ncc_tools dict
            self.default_data.update({
                "vtipdia": tip_dia,
                "vtipangle": (tip_angle * 2),
            })

            self.addtool_entry.set_value(tool_dia)

            return tool_dia
        else:
            return float(self.addtool_entry.get_value())

    def on_selection(self):
        if self.selectmethod_combo.get_value() == _("Reference Object"):
            self.box_combo.show()
            self.box_combo_label.show()
            self.box_combo_type.show()
            self.box_combo_type_label.show()
        else:
            self.box_combo.hide()
            self.box_combo_label.hide()
            self.box_combo_type.hide()
            self.box_combo_type_label.hide()

        if self.selectmethod_combo.get_value() == _("Polygon Selection"):
            # disable rest-machining for single polygon painting
            self.rest_cb.set_value(False)
            self.rest_cb.setDisabled(True)
        if self.selectmethod_combo.get_value() == _("Area Selection"):
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

        self.old_tool_dia = self.app.defaults["tools_paintnewdia"]

        # updated units
        self.units = self.app.defaults['units'].upper()

        # set the working variables to a known state
        self.paint_tools.clear()
        self.tooluid = 0

        self.default_data.clear()
        self.default_data.update({
            "name": '_paint',
            "plot": self.app.defaults["geometry_plot"],
            "cutz": float(self.cutz_entry.get_value()),
            "vtipdia": float(self.tipdia_entry.get_value()),
            "vtipangle": float(self.tipangle_entry.get_value()),
            "travelz": float(self.app.defaults["geometry_travelz"]),
            "feedrate": float(self.app.defaults["geometry_feedrate"]),
            "feedrate_z": float(self.app.defaults["geometry_feedrate_z"]),
            "feedrate_rapid": float(self.app.defaults["geometry_feedrate_rapid"]),
            "dwell": self.app.defaults["geometry_dwell"],
            "dwelltime": float(self.app.defaults["geometry_dwelltime"]),
            "multidepth": self.app.defaults["geometry_multidepth"],
            "ppname_g": self.app.defaults["geometry_ppname_g"],
            "depthperpass": float(self.app.defaults["geometry_depthperpass"]),
            "extracut": self.app.defaults["geometry_extracut"],
            "extracut_length": self.app.defaults["geometry_extracut_length"],
            "toolchange": self.app.defaults["geometry_toolchange"],
            "toolchangez": float(self.app.defaults["geometry_toolchangez"]),
            "endz": float(self.app.defaults["geometry_endz"]),
            "endxy": self.app.defaults["geometry_endxy"],

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
            "paintrest": self.app.defaults["tools_paintrest"],
        })

        # ## Init the GUI interface
        self.order_radio.set_value(self.app.defaults["tools_paintorder"])
        self.paintmargin_entry.set_value(self.app.defaults["tools_paintmargin"])
        self.paintmethod_combo.set_value(self.app.defaults["tools_paintmethod"])
        self.selectmethod_combo.set_value(self.app.defaults["tools_selectmethod"])
        self.pathconnect_cb.set_value(self.app.defaults["tools_pathconnect"])
        self.paintcontour_cb.set_value(self.app.defaults["tools_paintcontour"])
        self.paintoverlap_entry.set_value(self.app.defaults["tools_paintoverlap"])

        self.cutz_entry.set_value(self.app.defaults["tools_paintcutz"])
        self.tool_type_radio.set_value(self.app.defaults["tools_painttool_type"])
        self.tipdia_entry.set_value(self.app.defaults["tools_painttipdia"])
        self.tipangle_entry.set_value(self.app.defaults["tools_painttipangle"])
        self.addtool_entry.set_value(self.app.defaults["tools_paintnewdia"])
        self.rest_cb.set_value(self.app.defaults["tools_paintrest"])

        self.on_tool_type(val=self.tool_type_radio.get_value())

        # make the default object type, "Geometry"
        self.type_obj_combo.set_value("geometry")

        try:
            diameters = [float(self.app.defaults["tools_painttooldia"])]
        except (ValueError, TypeError):
            diameters = [eval(x) for x in self.app.defaults["tools_painttooldia"].split(",") if x != '']

        if not diameters:
            log.error("At least one tool diameter needed. Verify in Edit -> Preferences -> TOOLS -> NCC Tools.")
            self.build_ui()
            # if the Paint Method is "Single" disable the tool table context menu
            if self.default_data["selectmethod"] == "single":
                self.tools_table.setContextMenuPolicy(Qt.NoContextMenu)
            return

        # call on self.on_tool_add() counts as an call to self.build_ui()
        # through this, we add a initial row / tool in the tool_table
        for dia in diameters:
            self.on_tool_add(dia, muted=True)

        # if the Paint Method is "Single" disable the tool table context menu
        if self.default_data["selectmethod"] == "single":
            self.tools_table.setContextMenuPolicy(Qt.NoContextMenu)

    def build_ui(self):
        self.ui_disconnect()

        # updated units
        self.units = self.app.defaults['units'].upper()

        sorted_tools = []
        for k, v in self.paint_tools.items():
            sorted_tools.append(float('%.*f' % (self.decimals, float(v['tooldia']))))

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
                if float('%.*f' % (self.decimals, tooluid_value['tooldia'])) == tool_sorted:
                    tool_id += 1
                    id_item = QtWidgets.QTableWidgetItem('%d' % int(tool_id))
                    id_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                    row_no = tool_id - 1
                    self.tools_table.setItem(row_no, 0, id_item)  # Tool name/id

                    # Make sure that the drill diameter when in MM is with no more than 2 decimals
                    # There are no drill bits in MM with more than 2 decimals diameter
                    # For INCH the decimals should be no more than 4. There are no drills under 10mils

                    dia = QtWidgets.QTableWidgetItem('%.*f' % (self.decimals, tooluid_value['tooldia']))

                    dia.setFlags(QtCore.Qt.ItemIsEnabled)

                    tool_type_item = FCComboBox()
                    for item in self.tool_type_item_options:
                        tool_type_item.addItem(item)
                        # tool_type_item.setStyleSheet('background-color: rgb(255,255,255)')
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

    def on_combo_box_type(self):
        obj_type = self.box_combo_type.currentIndex()
        self.box_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.box_combo.setCurrentIndex(0)

    def on_tool_add(self, dia=None, muted=None):
        self.blockSignals(True)

        if dia:
            tool_dia = dia
        else:
            tool_dia = self.on_calculate_tooldia()

            if tool_dia is None:
                self.build_ui()
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("Please enter a tool diameter to add, in Float format."))
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
                    tool_dias.append(float('%.*f' % (self.decimals, v[tool_v])))

        if float('%.*f' % (self.decimals, tool_dia)) in tool_dias:
            if muted is None:
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("Adding tool cancelled. Tool already in Tool Table."))
            self.tools_table.itemChanged.connect(self.on_tool_edit)
            return
        else:
            if muted is None:
                self.app.inform.emit('[success] %s' % _("New tool added to Tool Table."))
            self.paint_tools.update({
                int(self.tooluid): {
                    'tooldia': float('%.*f' % (self.decimals, tool_dia)),
                    'offset': 'Path',
                    'offset_value': 0.0,
                    'type': 'Iso',
                    'tool_type': self.tool_type_radio.get_value(),
                    'data': dict(self.default_data),
                    'solid_geometry': []
                }
            })

        self.blockSignals(False)
        self.build_ui()

    def on_tool_edit(self):
        self.blockSignals(True)

        old_tool_dia = ''

        tool_dias = []
        for k, v in self.paint_tools.items():
            for tool_v in v.keys():
                if tool_v == 'tooldia':
                    tool_dias.append(float('%.*f' % (self.decimals, v[tool_v])))

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
        self.blockSignals(False)
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

    def on_tool_delete(self, rows_to_delete=None, all_tools=None):
        self.blockSignals(True)

        deleted_tools_list = []

        if all_tools:
            self.paint_tools.clear()
            self.blockSignals(False)
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

            self.blockSignals(False)
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
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Delete failed. Select a tool to delete."))
            self.blockSignals(False)
            return
        except Exception as e:
            log.debug(str(e))

        self.app.inform.emit('[success] %s' % _("Tool(s) deleted from Tool Table."))
        self.blockSignals(False)
        self.build_ui()

    def on_paint_button_click(self):

        # init values for the next usage
        self.reset_usage()

        self.app.report_usage("on_paint_button_click")
        # self.app.call_source = 'paint'

        # #####################################################
        # ######### Reading Parameters ########################
        # #####################################################
        self.app.inform.emit(_("Paint Tool. Reading parameters."))

        self.overlap = float(self.paintoverlap_entry.get_value()) / 100.0

        self.connect = self.pathconnect_cb.get_value()
        self.contour = self.paintcontour_cb.get_value()
        self.select_method = self.selectmethod_combo.get_value()
        self.obj_name = self.obj_combo.currentText()

        # Get source object.
        try:
            self.paint_obj = self.app.collection.get_by_name(str(self.obj_name))
        except Exception as e:
            log.debug("ToolPaint.on_paint_button_click() --> %s" % str(e))
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object: %s"), self.obj_name))
            return

        if self.paint_obj is None:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Object not found"), self.paint_obj))
            return

        # test if the Geometry Object is multigeo and return Fail if True because
        # for now Paint don't work on MultiGeo
        if self.paint_obj.multigeo is True:
            self.app.inform.emit('[ERROR_NOTCL] %s...' % _("Can't do Paint on MultiGeo geometries"))
            return 'Fail'

        self.o_name = '%s_mt_paint' % self.obj_name

        # use the selected tools in the tool table; get diameters
        self.tooldia_list = []
        if self.tools_table.selectedItems():
            for x in self.tools_table.selectedItems():
                try:
                    self.tooldia = float(self.tools_table.item(x.row(), 1).text())
                except ValueError:
                    # try to convert comma to decimal point. if it's still not working error message and return
                    try:
                        self.tooldia = float(self.tools_table.item(x.row(), 1).text().replace(',', '.'))
                    except ValueError:
                        self.app.inform.emit('[ERROR_NOTCL] %s' % _("Wrong value format entered, use a number."))
                        continue
                self.tooldia_list.append(self.tooldia)
        else:
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("No selected tools in Tool Table."))
            return

        if self.select_method == _("All Polygons"):
            self.paint_poly_all(self.paint_obj,
                                tooldia=self.tooldia_list,
                                outname=self.o_name,
                                overlap=self.overlap,
                                connect=self.connect,
                                contour=self.contour)

        elif self.select_method == _("Polygon Selection"):
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Click on a polygon to paint it."))

            # disengage the grid snapping since it may be hard to click on polygons with grid snapping on
            if self.app.ui.grid_snap_btn.isChecked():
                self.grid_status_memory = True
                self.app.ui.grid_snap_btn.trigger()
            else:
                self.grid_status_memory = False

            self.mr = self.app.plotcanvas.graph_event_connect('mouse_release', self.on_single_poly_mouse_release)

            if self.app.is_legacy is False:
                self.app.plotcanvas.graph_event_disconnect('mouse_release', self.app.on_mouse_click_release_over_plot)
                self.app.plotcanvas.graph_event_disconnect('mouse_press', self.app.on_mouse_click_over_plot)
            else:
                self.app.plotcanvas.graph_event_disconnect(self.app.mr)
                self.app.plotcanvas.graph_event_disconnect(self.app.mp)

        elif self.select_method == _("Area Selection"):
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Click the start point of the paint area."))

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
        elif self.select_method == _("Reference Object"):
            self.bound_obj_name = self.box_combo.currentText()
            # Get source object.
            try:
                self.bound_obj = self.app.collection.get_by_name(self.bound_obj_name)
            except Exception:
                self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), self.obj_name))
                return "Could not retrieve object: %s" % self.obj_name

            self.paint_poly_ref(obj=self.paint_obj,
                                sel_obj=self.bound_obj,
                                tooldia=self.tooldia_list,
                                overlap=self.overlap,
                                outname=self.o_name,
                                connect=self.connect,
                                contour=self.contour)

    # To be called after clicking on the plot.
    def on_single_poly_mouse_release(self, event):
        if self.app.is_legacy is False:
            event_pos = event.pos
            right_button = 2
            event_is_dragging = self.app.event_is_dragging
        else:
            event_pos = (event.xdata, event.ydata)
            right_button = 3
            event_is_dragging = self.app.ui.popMenu.mouse_is_panning

        try:
            x = float(event_pos[0])
            y = float(event_pos[1])
        except TypeError:
            return

        event_pos = (x, y)
        curr_pos = self.app.plotcanvas.translate_coords(event_pos)

        # do paint single only for left mouse clicks
        if event.button == 1:
            clicked_poly = self.find_polygon(point=(curr_pos[0], curr_pos[1]), geoset=self.paint_obj.solid_geometry)

            if clicked_poly:
                if clicked_poly not in self.poly_dict.values():
                    shape_id = self.app.tool_shapes.add(tolerance=self.paint_obj.drawing_tolerance,
                                                        layer=0,
                                                        shape=clicked_poly,
                                                        color=self.app.defaults['global_sel_draw_color'] + 'AF',
                                                        face_color=self.app.defaults['global_sel_draw_color'] + 'AF',
                                                        visible=True)
                    self.poly_dict[shape_id] = clicked_poly
                    self.app.inform.emit(
                        '%s: %d. %s' % (_("Added polygon"),
                                        int(len(self.poly_dict)),
                                        _("Click to add next polygon or right click to start painting."))
                    )
                else:
                    try:
                        for k, v in list(self.poly_dict.items()):
                            if v == clicked_poly:
                                self.app.tool_shapes.remove(k)
                                self.poly_dict.pop(k)
                                break
                    except TypeError:
                        return
                    self.app.inform.emit(
                        '%s. %s' % (_("Removed polygon"),
                                    _("Click to add/remove next polygon or right click to start painting."))
                    )

                self.app.tool_shapes.redraw()
            else:
                self.app.inform.emit(_("No polygon detected under click position."))

        elif event.button == right_button and event_is_dragging is False:
            # restore the Grid snapping if it was active before
            if self.grid_status_memory is True:
                self.app.ui.grid_snap_btn.trigger()

            if self.app.is_legacy is False:
                self.app.plotcanvas.graph_event_disconnect('mouse_release', self.on_single_poly_mouse_release)
            else:
                self.app.plotcanvas.graph_event_disconnect(self.mr)

            self.app.mp = self.app.plotcanvas.graph_event_connect('mouse_press',
                                                                  self.app.on_mouse_click_over_plot)
            self.app.mr = self.app.plotcanvas.graph_event_connect('mouse_release',
                                                                  self.app.on_mouse_click_release_over_plot)

            self.app.tool_shapes.clear(update=True)

            if self.poly_dict:
                poly_list = deepcopy(list(self.poly_dict.values()))
                self.paint_poly(self.paint_obj,
                                inside_pt=(curr_pos[0], curr_pos[1]),
                                poly_list=poly_list,
                                tooldia=self.tooldia_list,
                                overlap=self.overlap,
                                connect=self.connect,
                                contour=self.contour)
                self.poly_dict.clear()
            else:
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("List of single polygons is empty. Aborting."))

    # To be called after clicking on the plot.
    def on_mouse_release(self, event):
        if self.app.is_legacy is False:
            event_pos = event.pos
            event_is_dragging = event.is_dragging
            right_button = 2
        else:
            event_pos = (event.xdata, event.ydata)
            event_is_dragging = self.app.plotcanvas.is_dragging
            right_button = 3

        try:
            x = float(event_pos[0])
            y = float(event_pos[1])
        except TypeError:
            return

        event_pos = (x, y)

        # do paint single only for left mouse clicks
        if event.button == 1:
            if not self.first_click:
                self.first_click = True
                self.app.inform.emit('[WARNING_NOTCL] %s' %
                                     _("Click the end point of the paint area."))

                self.cursor_pos = self.app.plotcanvas.translate_coords(event_pos)
                if self.app.grid_status():
                    self.cursor_pos = self.app.geo_editor.snap(self.cursor_pos[0], self.cursor_pos[1])
            else:
                self.app.inform.emit(_("Zone added. Click to start adding next zone or right click to finish."))
                self.app.delete_selection_shape()

                curr_pos = self.app.plotcanvas.translate_coords(event_pos)
                if self.app.grid_status():
                    curr_pos = self.app.geo_editor.snap(curr_pos[0], curr_pos[1])

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
            self.paint_poly_area(obj=self.paint_obj,
                                 tooldia=self.tooldia_list,
                                 sel_obj=self.sel_rect,
                                 outname=self.o_name,
                                 overlap=self.overlap,
                                 connect=self.connect,
                                 contour=self.contour)

    # called on mouse move
    def on_mouse_move(self, event):
        if self.app.is_legacy is False:
            event_pos = event.pos
            event_is_dragging = event.is_dragging
            right_button = 2
        else:
            event_pos = (event.xdata, event.ydata)
            event_is_dragging = self.app.plotcanvas.is_dragging
            right_button = 3

        try:
            x = float(event_pos[0])
            y = float(event_pos[1])
        except TypeError:
            return

        curr_pos = self.app.plotcanvas.translate_coords((x, y))

        # detect mouse dragging motion
        if event_is_dragging == 1:
            self.mouse_is_dragging = True
        else:
            self.mouse_is_dragging = False

        # update the cursor position
        if self.app.grid_status():
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

        dx = curr_pos[0] - float(self.cursor_pos[0])
        dy = curr_pos[1] - float(self.cursor_pos[1])
        self.app.ui.rel_position_label.setText("<b>Dx</b>: %.4f&nbsp;&nbsp;  <b>Dy</b>: "
                                               "%.4f&nbsp;&nbsp;&nbsp;&nbsp;" % (dx, dy))

        # draw the utility geometry
        if self.first_click:
            self.app.delete_selection_shape()
            self.app.draw_moving_selection_shape(old_coords=(self.cursor_pos[0], self.cursor_pos[1]),
                                                 coords=(curr_pos[0], curr_pos[1]))

    def paint_poly(self, obj, inside_pt=None, poly_list=None, tooldia=None, overlap=None, order=None,
                   margin=None, method=None, outname=None, connect=None, contour=None, tools_storage=None,
                   plot=True, run_threaded=True):
        """
        Paints a polygon selected by clicking on its interior or by having a point coordinates given

        Note:
            * The margin is taken directly from the form.
        :param run_threaded:
        :param plot:
        :param poly_list:
        :param obj: painted object
        :param inside_pt: [x, y]
        :param tooldia: Diameter of the painting tool
        :param overlap: Overlap of the tool between passes.
        :param order: if the tools are ordered and how
        :param margin: a border around painting area
        :param outname: Name of the resulting Geometry Object.
        :param connect: Connect lines to avoid tool lifts.
        :param contour: Paint around the edges.
        :param method: choice out of _("Seed"), 'normal', 'lines'
        :param tools_storage: whether to use the current tools_storage self.paints_tools or a different one.
        Usage of the different one is related to when this function is called from a TcL command.
        :return: None
        """

        if isinstance(obj, FlatCAMGerber):
            if self.app.defaults["gerber_buffering"] == 'no':
                self.app.inform.emit('%s %s %s' %
                                     (_("Paint Tool."), _("Normal painting polygon task started."),
                                      _("Buffering geometry...")))
            else:
                self.app.inform.emit('%s %s' % (_("Paint Tool."), _("Normal painting polygon task started.")))
        else:
            self.app.inform.emit('%s %s' % (_("Paint Tool."), _("Normal painting polygon task started.")))

        if isinstance(obj, FlatCAMGerber):
            if self.app.defaults["tools_paint_plotting"] == 'progressive':
                if isinstance(obj.solid_geometry, list):
                    obj.solid_geometry = MultiPolygon(obj.solid_geometry).buffer(0)
                else:
                    obj.solid_geometry = obj.solid_geometry.buffer(0)

        polygon_list = None
        if inside_pt and poly_list is None:
            polygon_list = [self.find_polygon(point=inside_pt, geoset=obj.solid_geometry)]
        elif (inside_pt is None and poly_list) or (inside_pt and poly_list):
            polygon_list = poly_list

        # No polygon?
        if polygon_list is None:
            self.app.log.warning('No polygon found.')
            self.app.inform.emit('[WARNING] %s' % _('No polygon found.'))
            return

        paint_method = method if method is not None else self.paintmethod_combo.get_value()
        paint_margin = float(self.paintmargin_entry.get_value()) if margin is None else margin
        # determine if to use the progressive plotting
        prog_plot = True if self.app.defaults["tools_paint_plotting"] == 'progressive' else False

        name = outname if outname is not None else self.obj_name + "_paint"
        over = overlap if overlap is not None else float(self.app.defaults["tools_paintoverlap"]) / 100.0
        conn = connect if connect is not None else self.app.defaults["tools_pathconnect"]
        cont = contour if contour is not None else self.app.defaults["tools_paintcontour"]
        order = order if order is not None else self.order_radio.get_value()
        tools_storage = self.paint_tools if tools_storage is None else tools_storage

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

        # sort the tools if we have an order selected in the UI
        if order == 'fwd':
            sorted_tools.sort(reverse=False)
        elif order == 'rev':
            sorted_tools.sort(reverse=True)

        proc = self.app.proc_container.new(_("Painting polygon..."))

        # Initializes the new geometry object
        def gen_paintarea(geo_obj, app_obj):
            geo_obj.solid_geometry = []

            def paint_p(polyg, tooldiameter):
                cpoly = None
                try:
                    if paint_method == _("Standard"):
                        # Type(cp) == FlatCAMRTreeStorage | None
                        cpoly = self.clear_polygon(polyg,
                                                   tooldia=tooldiameter,
                                                   steps_per_circle=self.app.defaults["geometry_circle_steps"],
                                                   overlap=over,
                                                   contour=cont,
                                                   connect=conn,
                                                   prog_plot=prog_plot)

                    elif paint_method == _("Seed"):
                        # Type(cp) == FlatCAMRTreeStorage | None
                        cpoly = self.clear_polygon2(polyg,
                                                    tooldia=tooldiameter,
                                                    steps_per_circle=self.app.defaults["geometry_circle_steps"],
                                                    overlap=over,
                                                    contour=cont,
                                                    connect=conn,
                                                    prog_plot=prog_plot)

                    elif paint_method == _("Lines"):
                        # Type(cp) == FlatCAMRTreeStorage | None
                        cpoly = self.clear_polygon3(polyg,
                                                    tooldia=tooldiameter,
                                                    steps_per_circle=self.app.defaults["geometry_circle_steps"],
                                                    overlap=over,
                                                    contour=cont,
                                                    connect=conn,
                                                    prog_plot=prog_plot)

                    elif paint_method == _("Laser_lines"):
                        # line = None
                        # aperture_size = None

                        # the key is the aperture type and the val is a list of geo elements
                        flash_el_dict = {}
                        # the key is the aperture size, the val is a list of geo elements
                        traces_el_dict = {}

                        # find the flashes and the lines that are in the selected polygon and store them separately
                        for apid, apval in obj.apertures.items():
                            for geo_el in apval['geometry']:
                                if apval["size"] == 0.0:
                                    if apval["size"] in traces_el_dict:
                                        traces_el_dict[apval["size"]].append(geo_el)
                                    else:
                                        traces_el_dict[apval["size"]] = [geo_el]

                                if 'follow' in geo_el and geo_el['follow'].within(polyg):
                                    if isinstance(geo_el['follow'], Point):
                                        if apval["type"] == 'C':
                                            if 'C' in flash_el_dict:
                                                flash_el_dict['C'].append(geo_el)
                                            else:
                                                flash_el_dict['C'] = [geo_el]
                                        elif apval["type"] == 'O':
                                            if 'O' in flash_el_dict:
                                                flash_el_dict['O'].append(geo_el)
                                            else:
                                                flash_el_dict['O'] = [geo_el]
                                        elif apval["type"] == 'R':
                                            if 'R' in flash_el_dict:
                                                flash_el_dict['R'].append(geo_el)
                                            else:
                                                flash_el_dict['R'] = [geo_el]
                                    else:
                                        aperture_size = apval['size']

                                        if aperture_size in traces_el_dict:
                                            traces_el_dict[aperture_size].append(geo_el)
                                        else:
                                            traces_el_dict[aperture_size] = [geo_el]

                        cpoly = FlatCAMRTreeStorage()
                        pads_lines_list = []

                        # process the flashes found in the selected polygon with the 'lines' method for rectangular
                        # flashes and with _("Seed") for oblong and circular flashes
                        # and pads (flahes) need the contour therefore I override the GUI settings with always True
                        for ap_type in flash_el_dict:
                            for elem in flash_el_dict[ap_type]:
                                if 'solid' in elem:
                                    if ap_type == 'C':
                                        f_o = self.clear_polygon2(elem['solid'],
                                                                  tooldia=tooldiameter,
                                                                  steps_per_circle=self.app.defaults[
                                                                      "geometry_circle_steps"],
                                                                  overlap=over,
                                                                  contour=True,
                                                                  connect=conn,
                                                                  prog_plot=prog_plot)
                                        pads_lines_list += [p for p in f_o.get_objects() if p]

                                    elif ap_type == 'O':
                                        f_o = self.clear_polygon2(elem['solid'],
                                                                  tooldia=tooldiameter,
                                                                  steps_per_circle=self.app.defaults[
                                                                      "geometry_circle_steps"],
                                                                  overlap=over,
                                                                  contour=True,
                                                                  connect=conn,
                                                                  prog_plot=prog_plot)
                                        pads_lines_list += [p for p in f_o.get_objects() if p]

                                    elif ap_type == 'R':
                                        f_o = self.clear_polygon3(elem['solid'],
                                                                  tooldia=tooldiameter,
                                                                  steps_per_circle=self.app.defaults[
                                                                      "geometry_circle_steps"],
                                                                  overlap=over,
                                                                  contour=True,
                                                                  connect=conn,
                                                                  prog_plot=prog_plot)

                                        pads_lines_list += [p for p in f_o.get_objects() if p]

                        # add the lines from pads to the storage
                        try:
                            for lin in pads_lines_list:
                                if lin:
                                    cpoly.insert(lin)
                        except TypeError:
                            cpoly.insert(pads_lines_list)

                        copper_lines_list = []
                        # process the traces found in the selected polygon using the 'laser_lines' method,
                        # method which will follow the 'follow' line therefore use the longer path possible for the
                        # laser, therefore the acceleration will play a smaller factor
                        for aperture_size in traces_el_dict:
                            for elem in traces_el_dict[aperture_size]:
                                line = elem['follow']
                                if line:
                                    t_o = self.fill_with_lines(line, aperture_size,
                                                               tooldia=tooldiameter,
                                                               steps_per_circle=self.app.defaults[
                                                                   "geometry_circle_steps"],
                                                               overlap=over,
                                                               contour=cont,
                                                               connect=conn,
                                                               prog_plot=prog_plot)

                                    copper_lines_list += [p for p in t_o.get_objects() if p]

                        # add the lines from copper features to storage but first try to make as few lines as possible
                        # by trying to fuse them
                        lines_union = linemerge(unary_union(copper_lines_list))
                        try:
                            for lin in lines_union:
                                if lin:
                                    cpoly.insert(lin)
                        except TypeError:
                            cpoly.insert(lines_union)
                        # # determine the Gerber follow line
                        # for apid, apval in obj.apertures.items():
                        #     for geo_el in apval['geometry']:
                        #         if 'solid' in geo_el:
                        #             if Point(inside_pt).within(geo_el['solid']):
                        #                 if not isinstance(geo_el['follow'], Point):
                        #                     line = geo_el['follow']
                        #
                        #                     if apval['type'] == 'C':
                        #                         aperture_size = apval['size']
                        #                     else:
                        #                         if apval['width'] > apval['height']:
                        #                             aperture_size = apval['height']
                        #                         else:
                        #                             aperture_size = apval['width']
                        #
                        # if line:
                        #     cpoly = self.fill_with_lines(line, aperture_size,
                        #                                  tooldia=tooldiameter,
                        #                                  steps_per_circle=self.app.defaults["geometry_circle_steps"],
                        #                                  overlap=over,
                        #                                  contour=cont,
                        #                                  connect=conn,
                        #                                  prog_plot=prog_plot)

                    elif paint_method == _("Combo"):
                        self.app.inform.emit(_("Painting polygon with method: lines."))
                        cpoly = self.clear_polygon3(polyg,
                                                    tooldia=tooldiameter,
                                                    steps_per_circle=self.app.defaults["geometry_circle_steps"],
                                                    overlap=over,
                                                    contour=cont,
                                                    connect=conn,
                                                    prog_plot=prog_plot)

                        if cpoly and cpoly.objects:
                            pass
                        else:
                            self.app.inform.emit(_("Failed. Painting polygon with method: seed."))
                            cpoly = self.clear_polygon2(polyg,
                                                        tooldia=tooldiameter,
                                                        steps_per_circle=self.app.defaults["geometry_circle_steps"],
                                                        overlap=over,
                                                        contour=cont,
                                                        connect=conn,
                                                        prog_plot=prog_plot)
                            if cpoly and cpoly.objects:
                                pass
                            else:
                                self.app.inform.emit(_("Failed. Painting polygon with method: standard."))
                                cpoly = self.clear_polygon(polyg,
                                                           tooldia=tooldiameter,
                                                           steps_per_circle=self.app.defaults["geometry_circle_steps"],
                                                           overlap=over,
                                                           contour=cont,
                                                           connect=conn,
                                                           prog_plot=prog_plot)
                except FlatCAMApp.GracefulException:
                    return "fail"
                except Exception as ee:
                    log.debug("ToolPaint.paint_poly().gen_paintarea().paint_p() --> %s" % str(ee))

                if cpoly and cpoly.objects:
                    geo_obj.solid_geometry += list(cpoly.get_objects())
                    return cpoly
                else:
                    app_obj.inform.emit('[ERROR_NOTCL] %s' % _('Geometry could not be painted completely'))
                    return None

            current_uid = int(1)
            tool_dia = None
            for tool_dia in sorted_tools:
                # find the tooluid associated with the current tool_dia so we know where to add the tool solid_geometry
                for k, v in tools_storage.items():
                    if float('%.*f' % (self.decimals, v['tooldia'])) == float('%.*f' % (self.decimals, tool_dia)):
                        current_uid = int(k)
                        break

            try:
                poly_buf = [pol.buffer(-paint_margin) for pol in polygon_list]
                cp = []
                try:
                    for pp in poly_buf:
                        cp.append(paint_p(pp, tooldiameter=tool_dia))
                except TypeError:
                    cp = paint_p(poly_buf, tooldiameter=tool_dia)

                total_geometry = []
                if cp:
                    try:
                        for x in cp:
                            total_geometry += list(x.get_objects())
                    except TypeError:
                        total_geometry = list(cp.get_objects())
            except FlatCAMApp.GracefulException:
                return "fail"
            except Exception as e:
                log.debug("Could not Paint the polygons. %s" % str(e))
                app_obj.inform.emit('[ERROR] %s\n%s' %
                                    (_("Could not do Paint. Try a different combination of parameters. "
                                       "Or a different strategy of paint"),
                                     str(e)
                                     )
                                    )
                return "fail"

            # add the solid_geometry to the current too in self.paint_tools (tools_storage)
            # dictionary and then reset the temporary list that stored that solid_geometry
            tools_storage[current_uid]['solid_geometry'] = deepcopy(total_geometry)

            tools_storage[current_uid]['data']['name'] = name

            # clean the progressive plotted shapes if it was used
            if self.app.defaults["tools_paint_plotting"] == 'progressive':
                self.temp_shapes.clear(update=True)

            # delete tools with empty geometry
            # look for keys in the tools_storage dict that have 'solid_geometry' values empty
            for uid in list(tools_storage.keys()):
                # if the solid_geometry (type=list) is empty
                if not tools_storage[uid]['solid_geometry']:
                    tools_storage.pop(uid, None)

            geo_obj.options["cnctooldia"] = str(tool_dia)

            # this will turn on the FlatCAMCNCJob plot for multiple tools
            geo_obj.multigeo = True
            geo_obj.multitool = True
            geo_obj.tools.clear()
            geo_obj.tools = dict(tools_storage)

            geo_obj.solid_geometry = cascaded_union(tools_storage[current_uid]['solid_geometry'])

            try:
                if isinstance(geo_obj.solid_geometry, list):
                    a, b, c, d = MultiPolygon(geo_obj.solid_geometry).bounds
                else:
                    a, b, c, d = geo_obj.solid_geometry.bounds

                geo_obj.options['xmin'] = a
                geo_obj.options['ymin'] = b
                geo_obj.options['xmax'] = c
                geo_obj.options['ymax'] = d
            except Exception as e:
                log.debug("ToolPaint.paint_poly.gen_paintarea() bounds error --> %s" % str(e))
                return

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

            total_geometry[:] = []
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
                app_obj.new_object("geometry", name, gen_paintarea, plot=plot)
            except FlatCAMApp.GracefulException:
                proc.done()
                return
            except Exception as e:
                proc.done()
                self.app.inform.emit('[ERROR_NOTCL] %s --> %s' %
                                     ('PaintTool.paint_poly()',
                                      str(e)))
                return
            proc.done()
            # focus on Selected Tab
            self.app.ui.notebook.setCurrentWidget(self.app.ui.selected_tab)

        self.app.inform.emit(_("Polygon Paint started ..."))

        # Promise object with the new name
        self.app.collection.promise(name)

        if run_threaded:
            # Background
            self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})
        else:
            job_thread(app_obj=self.app)

    def paint_poly_all(self, obj, tooldia=None, overlap=None, order=None, margin=None, method=None, outname=None,
                       connect=None, contour=None, tools_storage=None, plot=True, run_threaded=True):
        """
        Paints all polygons in this object.

        :param run_threaded:
        :param plot:
        :param obj: painted object
        :param tooldia: a tuple or single element made out of diameters of the tools to be used
        :param overlap: value by which the paths will overlap
        :param order: if the tools are ordered and how
        :param margin: a border around painting area
        :param outname: name of the resulting object
        :param connect: Connect lines to avoid tool lifts.
        :param contour: Paint around the edges.
        :param method: choice out of _("Seed"), 'normal', 'lines'
        :param tools_storage: whether to use the current tools_storage self.paints_tools or a different one.
        Usage of the different one is related to when this function is called from a TcL command.
        :return:
        """
        paint_method = method if method is not None else self.paintmethod_combo.get_value()

        if margin is not None:
            paint_margin = margin
        else:
            paint_margin = float(self.paintmargin_entry.get_value())

        # determine if to use the progressive plotting
        if self.app.defaults["tools_paint_plotting"] == 'progressive':
            prog_plot = True
        else:
            prog_plot = False

        proc = self.app.proc_container.new(_("Painting polygons..."))
        name = outname if outname is not None else self.obj_name + "_paint"

        over = overlap if overlap is not None else float(self.app.defaults["tools_paintoverlap"]) / 100.0
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
            if isinstance(obj, FlatCAMGerber):
                if app_obj.defaults["gerber_buffering"] == 'no':
                    app_obj.inform.emit('%s %s' %
                                        (_("Paint Tool. Normal painting all task started."),
                                         _("Buffering geometry...")))
                else:
                    app_obj.inform.emit(_("Paint Tool. Normal painting all task started."))
            else:
                app_obj.inform.emit(_("Paint Tool. Normal painting all task started."))

            tool_dia = None
            if order == 'fwd':
                sorted_tools.sort(reverse=False)
            elif order == 'rev':
                sorted_tools.sort(reverse=True)
            else:
                pass

            if isinstance(obj, FlatCAMGerber):
                if self.app.defaults["tools_paint_plotting"] == 'progressive':
                    if isinstance(obj.solid_geometry, list):
                        obj.solid_geometry = MultiPolygon(obj.solid_geometry).buffer(0)
                    else:
                        obj.solid_geometry = obj.solid_geometry.buffer(0)

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
                    if float('%.*f' % (self.decimals, v['tooldia'])) == float('%.*f' % (self.decimals, tool_dia)):
                        current_uid = int(k)
                        break

                painted_area = recurse(obj.solid_geometry)
                # variables to display the percentage of work done
                geo_len = len(painted_area)

                old_disp_number = 0
                log.warning("Total number of polygons to be cleared. %s" % str(geo_len))

                pol_nr = 0
                for geo in painted_area:

                    # provide the app with a way to process the GUI events when in a blocking loop
                    QtWidgets.QApplication.processEvents()

                    if self.app.abort_flag:
                        # graceful abort requested by the user
                        raise FlatCAMApp.GracefulException

                    # try to clean the Polygon but it may result into a MultiPolygon
                    geo = geo.buffer(0)
                    poly_buf = geo.buffer(-paint_margin)

                    if geo is not None and geo.is_valid:
                        poly_processed = []
                        try:
                            for pol in poly_buf:
                                if pol is not None and isinstance(pol, Polygon):
                                    cp = None
                                    if paint_method == _("Standard"):
                                        cp = self.clear_polygon(pol,
                                                                tooldia=tool_dia,
                                                                steps_per_circle=self.app.defaults[
                                                                    "geometry_circle_steps"],
                                                                overlap=over,
                                                                contour=cont,
                                                                connect=conn,
                                                                prog_plot=prog_plot)
                                    elif paint_method == _("Seed"):
                                        cp = self.clear_polygon2(pol,
                                                                 tooldia=tool_dia,
                                                                 steps_per_circle=self.app.defaults[
                                                                     "geometry_circle_steps"],
                                                                 overlap=over,
                                                                 contour=cont,
                                                                 connect=conn,
                                                                 prog_plot=prog_plot)
                                    elif paint_method == _("Lines"):
                                        cp = self.clear_polygon3(pol,
                                                                 tooldia=tool_dia,
                                                                 steps_per_circle=self.app.defaults[
                                                                     "geometry_circle_steps"],
                                                                 overlap=over,
                                                                 contour=cont,
                                                                 connect=conn,
                                                                 prog_plot=prog_plot)
                                    elif paint_method == _("Laser_lines"):
                                        # line = None
                                        # aperture_size = None

                                        # the key is the aperture type and the val is a list of geo elements
                                        flash_el_dict = {}
                                        # the key is the aperture size, the val is a list of geo elements
                                        traces_el_dict = {}

                                        # find the flashes and the lines that are in the selected polygon and store
                                        # them separately
                                        for apid, apval in obj.apertures.items():
                                            for geo_el in apval['geometry']:
                                                if apval["size"] == 0.0:
                                                    if apval["size"] in traces_el_dict:
                                                        traces_el_dict[apval["size"]].append(geo_el)
                                                    else:
                                                        traces_el_dict[apval["size"]] = [geo_el]

                                                if 'follow' in geo_el and geo_el['follow'].within(pol):
                                                    if isinstance(geo_el['follow'], Point):
                                                        if apval["type"] == 'C':
                                                            if 'C' in flash_el_dict:
                                                                flash_el_dict['C'].append(geo_el)
                                                            else:
                                                                flash_el_dict['C'] = [geo_el]
                                                        elif apval["type"] == 'O':
                                                            if 'O' in flash_el_dict:
                                                                flash_el_dict['O'].append(geo_el)
                                                            else:
                                                                flash_el_dict['O'] = [geo_el]
                                                        elif apval["type"] == 'R':
                                                            if 'R' in flash_el_dict:
                                                                flash_el_dict['R'].append(geo_el)
                                                            else:
                                                                flash_el_dict['R'] = [geo_el]
                                                    else:
                                                        aperture_size = apval['size']

                                                        if aperture_size in traces_el_dict:
                                                            traces_el_dict[aperture_size].append(geo_el)
                                                        else:
                                                            traces_el_dict[aperture_size] = [geo_el]

                                        cp = FlatCAMRTreeStorage()
                                        pads_lines_list = []

                                        # process the flashes found in the selected polygon with the 'lines' method
                                        # for rectangular flashes and with _("Seed") for oblong and circular flashes
                                        # and pads (flahes) need the contour therefore I override the GUI settings
                                        # with always True
                                        for ap_type in flash_el_dict:
                                            for elem in flash_el_dict[ap_type]:
                                                if 'solid' in elem:
                                                    if ap_type == 'C':
                                                        f_o = self.clear_polygon2(elem['solid'],
                                                                                  tooldia=tool_dia,
                                                                                  steps_per_circle=self.app.defaults[
                                                                                      "geometry_circle_steps"],
                                                                                  overlap=over,
                                                                                  contour=True,
                                                                                  connect=conn,
                                                                                  prog_plot=prog_plot)
                                                        pads_lines_list += [p for p in f_o.get_objects() if p]

                                                    elif ap_type == 'O':
                                                        f_o = self.clear_polygon2(elem['solid'],
                                                                                  tooldia=tool_dia,
                                                                                  steps_per_circle=self.app.defaults[
                                                                                      "geometry_circle_steps"],
                                                                                  overlap=over,
                                                                                  contour=True,
                                                                                  connect=conn,
                                                                                  prog_plot=prog_plot)
                                                        pads_lines_list += [p for p in f_o.get_objects() if p]

                                                    elif ap_type == 'R':
                                                        f_o = self.clear_polygon3(elem['solid'],
                                                                                  tooldia=tool_dia,
                                                                                  steps_per_circle=self.app.defaults[
                                                                                      "geometry_circle_steps"],
                                                                                  overlap=over,
                                                                                  contour=True,
                                                                                  connect=conn,
                                                                                  prog_plot=prog_plot)

                                                        pads_lines_list += [p for p in f_o.get_objects() if p]

                                        # add the lines from pads to the storage
                                        try:
                                            for lin in pads_lines_list:
                                                if lin:
                                                    cp.insert(lin)
                                        except TypeError:
                                            cp.insert(pads_lines_list)

                                        copper_lines_list = []
                                        # process the traces found in the selected polygon using the 'laser_lines'
                                        # method, method which will follow the 'follow' line therefore use the longer
                                        # path possible for the laser, therefore the acceleration will play
                                        # a smaller factor
                                        for aperture_size in traces_el_dict:
                                            for elem in traces_el_dict[aperture_size]:
                                                line = elem['follow']
                                                if line:
                                                    t_o = self.fill_with_lines(line, aperture_size,
                                                                               tooldia=tool_dia,
                                                                               steps_per_circle=self.app.defaults[
                                                                                   "geometry_circle_steps"],
                                                                               overlap=over,
                                                                               contour=cont,
                                                                               connect=conn,
                                                                               prog_plot=prog_plot)

                                                    copper_lines_list += [p for p in t_o.get_objects() if p]

                                        # add the lines from copper features to storage but first try to make as few
                                        # lines as possible
                                        # by trying to fuse them
                                        lines_union = linemerge(unary_union(copper_lines_list))
                                        try:
                                            for lin in lines_union:
                                                if lin:
                                                    cp.insert(lin)
                                        except TypeError:
                                            cp.insert(lines_union)
                                    elif paint_method == _("Combo"):
                                        self.app.inform.emit(_("Painting polygons with method: lines."))
                                        cp = self.clear_polygon3(pol,
                                                                 tooldia=tool_dia,
                                                                 steps_per_circle=self.app.defaults[
                                                                     "geometry_circle_steps"],
                                                                 overlap=over,
                                                                 contour=cont,
                                                                 connect=conn,
                                                                 prog_plot=prog_plot)

                                        if cp and cp.objects:
                                            pass
                                        else:
                                            self.app.inform.emit(_("Failed. Painting polygons with method: seed."))
                                            cp = self.clear_polygon2(pol,
                                                                     tooldia=tool_dia,
                                                                     steps_per_circle=self.app.defaults[
                                                                         "geometry_circle_steps"],
                                                                     overlap=over,
                                                                     contour=cont,
                                                                     connect=conn,
                                                                     prog_plot=prog_plot)
                                            if cp and cp.objects:
                                                pass
                                            else:
                                                self.app.inform.emit(
                                                    _("Failed. Painting polygons with method: standard."))

                                                cp = self.clear_polygon(pol,
                                                                        tooldia=tool_dia,
                                                                        steps_per_circle=self.app.defaults[
                                                                            "geometry_circle_steps"],
                                                                        overlap=over,
                                                                        contour=cont,
                                                                        connect=conn,
                                                                        prog_plot=prog_plot)
                                    if cp and cp.objects:
                                        total_geometry += list(cp.get_objects())
                                        poly_processed.append(True)
                                    else:
                                        poly_processed.append(False)
                                        log.warning("Polygon in MultiPolygon can not be cleared.")
                                else:
                                    log.warning("Geo in Iterable can not be cleared because it is not Polygon. "
                                                "It is: %s" % str(type(pol)))
                        except TypeError:
                            if isinstance(poly_buf, Polygon):
                                cp = None
                                if paint_method == _("Standard"):
                                    cp = self.clear_polygon(poly_buf,
                                                            tooldia=tool_dia,
                                                            steps_per_circle=self.app.defaults[
                                                                "geometry_circle_steps"],
                                                            overlap=over,
                                                            contour=cont,
                                                            connect=conn,
                                                            prog_plot=prog_plot)
                                elif paint_method == _("Seed"):
                                    cp = self.clear_polygon2(poly_buf,
                                                             tooldia=tool_dia,
                                                             steps_per_circle=self.app.defaults[
                                                                 "geometry_circle_steps"],
                                                             overlap=over,
                                                             contour=cont,
                                                             connect=conn,
                                                             prog_plot=prog_plot)
                                elif paint_method == _("Lines"):
                                    cp = self.clear_polygon3(poly_buf,
                                                             tooldia=tool_dia,
                                                             steps_per_circle=self.app.defaults[
                                                                 "geometry_circle_steps"],
                                                             overlap=over,
                                                             contour=cont,
                                                             connect=conn,
                                                             prog_plot=prog_plot)
                                elif paint_method == _("Laser_lines"):
                                    # line = None
                                    # aperture_size = None

                                    # the key is the aperture type and the val is a list of geo elements
                                    flash_el_dict = {}
                                    # the key is the aperture size, the val is a list of geo elements
                                    traces_el_dict = {}

                                    # find the flashes and the lines that are in the selected polygon and store
                                    # them separately
                                    for apid, apval in obj.apertures.items():
                                        for geo_el in apval['geometry']:
                                            if apval["size"] == 0.0:
                                                if apval["size"] in traces_el_dict:
                                                    traces_el_dict[apval["size"]].append(geo_el)
                                                else:
                                                    traces_el_dict[apval["size"]] = [geo_el]

                                            if 'follow' in geo_el and geo_el['follow'].within(poly_buf):
                                                if isinstance(geo_el['follow'], Point):
                                                    if apval["type"] == 'C':
                                                        if 'C' in flash_el_dict:
                                                            flash_el_dict['C'].append(geo_el)
                                                        else:
                                                            flash_el_dict['C'] = [geo_el]
                                                    elif apval["type"] == 'O':
                                                        if 'O' in flash_el_dict:
                                                            flash_el_dict['O'].append(geo_el)
                                                        else:
                                                            flash_el_dict['O'] = [geo_el]
                                                    elif apval["type"] == 'R':
                                                        if 'R' in flash_el_dict:
                                                            flash_el_dict['R'].append(geo_el)
                                                        else:
                                                            flash_el_dict['R'] = [geo_el]
                                                else:
                                                    aperture_size = apval['size']

                                                    if aperture_size in traces_el_dict:
                                                        traces_el_dict[aperture_size].append(geo_el)
                                                    else:
                                                        traces_el_dict[aperture_size] = [geo_el]

                                    cp = FlatCAMRTreeStorage()
                                    pads_lines_list = []

                                    # process the flashes found in the selected polygon with the 'lines' method
                                    # for rectangular flashes and with _("Seed") for oblong and circular flashes
                                    # and pads (flahes) need the contour therefore I override the GUI settings
                                    # with always True
                                    for ap_type in flash_el_dict:
                                        for elem in flash_el_dict[ap_type]:
                                            if 'solid' in elem:
                                                if ap_type == 'C':
                                                    f_o = self.clear_polygon2(elem['solid'],
                                                                              tooldia=tool_dia,
                                                                              steps_per_circle=self.app.defaults[
                                                                                  "geometry_circle_steps"],
                                                                              overlap=over,
                                                                              contour=True,
                                                                              connect=conn,
                                                                              prog_plot=prog_plot)
                                                    pads_lines_list += [p for p in f_o.get_objects() if p]

                                                elif ap_type == 'O':
                                                    f_o = self.clear_polygon2(elem['solid'],
                                                                              tooldia=tool_dia,
                                                                              steps_per_circle=self.app.defaults[
                                                                                  "geometry_circle_steps"],
                                                                              overlap=over,
                                                                              contour=True,
                                                                              connect=conn,
                                                                              prog_plot=prog_plot)
                                                    pads_lines_list += [p for p in f_o.get_objects() if p]

                                                elif ap_type == 'R':
                                                    f_o = self.clear_polygon3(elem['solid'],
                                                                              tooldia=tool_dia,
                                                                              steps_per_circle=self.app.defaults[
                                                                                  "geometry_circle_steps"],
                                                                              overlap=over,
                                                                              contour=True,
                                                                              connect=conn,
                                                                              prog_plot=prog_plot)

                                                    pads_lines_list += [p for p in f_o.get_objects() if p]

                                    # add the lines from pads to the storage
                                    try:
                                        for lin in pads_lines_list:
                                            if lin:
                                                cp.insert(lin)
                                    except TypeError:
                                        cp.insert(pads_lines_list)

                                    copper_lines_list = []
                                    # process the traces found in the selected polygon using the 'laser_lines'
                                    # method, method which will follow the 'follow' line therefore use the longer
                                    # path possible for the laser, therefore the acceleration will play
                                    # a smaller factor
                                    for aperture_size in traces_el_dict:
                                        for elem in traces_el_dict[aperture_size]:
                                            line = elem['follow']
                                            if line:
                                                t_o = self.fill_with_lines(line, aperture_size,
                                                                           tooldia=tool_dia,
                                                                           steps_per_circle=self.app.defaults[
                                                                               "geometry_circle_steps"],
                                                                           overlap=over,
                                                                           contour=cont,
                                                                           connect=conn,
                                                                           prog_plot=prog_plot)

                                                copper_lines_list += [p for p in t_o.get_objects() if p]

                                    # add the lines from copper features to storage but first try to make as few
                                    # lines as possible
                                    # by trying to fuse them
                                    lines_union = linemerge(unary_union(copper_lines_list))
                                    try:
                                        for lin in lines_union:
                                            if lin:
                                                cp.insert(lin)
                                    except TypeError:
                                        cp.insert(lines_union)
                                elif paint_method == _("Combo"):
                                    self.app.inform.emit(_("Painting polygons with method: lines."))
                                    cp = self.clear_polygon3(poly_buf,
                                                             tooldia=tool_dia,
                                                             steps_per_circle=self.app.defaults[
                                                                 "geometry_circle_steps"],
                                                             overlap=over,
                                                             contour=cont,
                                                             connect=conn,
                                                             prog_plot=prog_plot)

                                    if cp and cp.objects:
                                        pass
                                    else:
                                        self.app.inform.emit(_("Failed. Painting polygons with method: seed."))
                                        cp = self.clear_polygon2(poly_buf,
                                                                 tooldia=tool_dia,
                                                                 steps_per_circle=self.app.defaults[
                                                                     "geometry_circle_steps"],
                                                                 overlap=over,
                                                                 contour=cont,
                                                                 connect=conn,
                                                                 prog_plot=prog_plot)
                                        if cp and cp.objects:
                                            pass
                                        else:
                                            self.app.inform.emit(_("Failed. Painting polygons with method: standard."))
                                            cp = self.clear_polygon(poly_buf,
                                                                    tooldia=tool_dia,
                                                                    steps_per_circle=self.app.defaults[
                                                                        "geometry_circle_steps"],
                                                                    overlap=over,
                                                                    contour=cont,
                                                                    connect=conn,
                                                                    prog_plot=prog_plot)
                                if cp:
                                    total_geometry += list(cp.get_objects())
                                    poly_processed.append(True)
                                else:
                                    poly_processed.append(False)
                                    log.warning("Polygon can not be cleared.")
                            else:
                                log.warning("Geo can not be cleared because it is: %s" % str(type(poly_buf)))

                        p_cleared = poly_processed.count(True)
                        p_not_cleared = poly_processed.count(False)

                        if p_not_cleared:
                            app_obj.poly_not_cleared = True

                        if p_cleared == 0:
                            continue

                    # try:
                    #     # Polygons are the only really paintable geometries,
                    #     # lines in theory have no area to be painted
                    #     if not isinstance(geo, Polygon):
                    #         continue
                    #     poly_buf = geo.buffer(-paint_margin)
                    #
                    #     if paint_method == _("Seed"):
                    #         # Type(cp) == FlatCAMRTreeStorage | None
                    #         cp = self.clear_polygon2(poly_buf,
                    #                                  tooldia=tool_dia,
                    #                                  steps_per_circle=self.app.defaults["geometry_circle_steps"],
                    #                                  overlap=over,
                    #                                  contour=cont,
                    #                                  connect=conn,
                    #                                  prog_plot=prog_plot)
                    #
                    #     elif paint_method == _("Lines"):
                    #         # Type(cp) == FlatCAMRTreeStorage | None
                    #         cp = self.clear_polygon3(poly_buf,
                    #                                  tooldia=tool_dia,
                    #                                  steps_per_circle=self.app.defaults["geometry_circle_steps"],
                    #                                  overlap=over,
                    #                                  contour=cont,
                    #                                  connect=conn,
                    #                                  prog_plot=prog_plot)
                    #
                    #     else:
                    #         # Type(cp) == FlatCAMRTreeStorage | None
                    #         cp = self.clear_polygon(poly_buf,
                    #                                 tooldia=tool_dia,
                    #                                 steps_per_circle=self.app.defaults["geometry_circle_steps"],
                    #                                 overlap=over,
                    #                                 contour=cont,
                    #                                 connect=conn,
                    #                                 prog_plot=prog_plot)
                    #
                    #     if cp is not None:
                    #         total_geometry += list(cp.get_objects())
                    # except FlatCAMApp.GracefulException:
                    #     return "fail"
                    # except Exception as e:
                    #     log.debug("Could not Paint the polygons. %s" % str(e))
                    #     self.app.inform.emit('[ERROR] %s\n%s' %
                    #                          (_("Could not do Paint All. Try a different combination of parameters. "
                    #                             "Or a different Method of paint"),
                    #                           str(e)))
                    #     return "fail"

                        pol_nr += 1
                        disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 100]))
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

            # clean the progressive plotted shapes if it was used
            if self.app.defaults["tools_paint_plotting"] == 'progressive':
                self.temp_shapes.clear(update=True)

            # # delete tools with empty geometry
            # keys_to_delete = []
            # # look for keys in the tools_storage dict that have 'solid_geometry' values empty
            # for uid in tools_storage:
            #     # if the solid_geometry (type=list) is empty
            #     if not tools_storage[uid]['solid_geometry']:
            #         keys_to_delete.append(uid)
            #
            # # actual delete of keys from the tools_storage dict
            # for k in keys_to_delete:
            #     tools_storage.pop(k, None)

            # delete tools with empty geometry
            # look for keys in the tools_storage dict that have 'solid_geometry' values empty
            for uid in list(tools_storage.keys()):
                # if the solid_geometry (type=list) is empty
                if not tools_storage[uid]['solid_geometry']:
                    tools_storage.pop(uid, None)

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

            self.app.inform.emit('[success] %s' % _("Paint All Done."))

        # Initializes the new geometry object
        def gen_paintarea_rest_machining(geo_obj, app_obj):
            assert isinstance(geo_obj, FlatCAMGeometry), \
                "Initializer expected a FlatCAMGeometry, got %s" % type(geo_obj)

            log.debug("Paint Tool. Rest machining painting all task started.")
            if isinstance(obj, FlatCAMGerber):
                if app_obj.defaults["gerber_buffering"] == 'no':
                    app_obj.inform.emit('%s %s %s' %
                                        (_("Paint Tool."), _("Rest machining painting all task started."),
                                         _("Buffering geometry...")))
                else:
                    app_obj.inform.emit('%s %s' %
                                        (_("Paint Tool."), _("Rest machining painting all task started.")))
            else:
                app_obj.inform.emit('%s %s' %
                                    (_("Paint Tool."), _("Rest machining painting all task started.")))

            tool_dia = None
            sorted_tools.sort(reverse=True)

            cleared_geo = []
            current_uid = int(1)
            geo_obj.solid_geometry = []

            if isinstance(obj, FlatCAMGerber):
                if self.app.defaults["tools_paint_plotting"] == 'progressive':
                    if isinstance(obj.solid_geometry, list):
                        obj.solid_geometry = MultiPolygon(obj.solid_geometry).buffer(0)
                    else:
                        obj.solid_geometry = obj.solid_geometry.buffer(0)

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

                old_disp_number = 0
                log.warning("Total number of polygons to be cleared. %s" % str(geo_len))

                pol_nr = 0
                for geo in painted_area:
                    try:
                        geo = Polygon(geo) if not isinstance(geo, Polygon) else geo
                        poly_buf = geo.buffer(-paint_margin)
                        cp = None

                        if paint_method == _("Standard"):
                            # Type(cp) == FlatCAMRTreeStorage | None
                            cp = self.clear_polygon(poly_buf, tooldia=tool_dia,
                                                    steps_per_circle=self.app.defaults["geometry_circle_steps"],
                                                    overlap=over, contour=cont, connect=conn,
                                                    prog_plot=prog_plot)

                        elif paint_method == _("Seed"):
                            # Type(cp) == FlatCAMRTreeStorage | None
                            cp = self.clear_polygon2(poly_buf, tooldia=tool_dia,
                                                     steps_per_circle=self.app.defaults["geometry_circle_steps"],
                                                     overlap=over, contour=cont, connect=conn,
                                                     prog_plot=prog_plot)

                        elif paint_method == _("Lines"):
                            # Type(cp) == FlatCAMRTreeStorage | None
                            cp = self.clear_polygon3(poly_buf, tooldia=tool_dia,
                                                     steps_per_circle=self.app.defaults["geometry_circle_steps"],
                                                     overlap=over, contour=cont, connect=conn,
                                                     prog_plot=prog_plot)
                        elif paint_method == _("Laser_lines"):
                            # line = None
                            # aperture_size = None

                            # the key is the aperture type and the val is a list of geo elements
                            flash_el_dict = {}
                            # the key is the aperture size, the val is a list of geo elements
                            traces_el_dict = {}

                            # find the flashes and the lines that are in the selected polygon and store
                            # them separately
                            for apid, apval in obj.apertures.items():
                                for geo_el in apval['geometry']:
                                    if apval["size"] == 0.0:
                                        if apval["size"] in traces_el_dict:
                                            traces_el_dict[apval["size"]].append(geo_el)
                                        else:
                                            traces_el_dict[apval["size"]] = [geo_el]

                                    if 'follow' in geo_el and geo_el['follow'].within(poly_buf):
                                        if isinstance(geo_el['follow'], Point):
                                            if apval["type"] == 'C':
                                                if 'C' in flash_el_dict:
                                                    flash_el_dict['C'].append(geo_el)
                                                else:
                                                    flash_el_dict['C'] = [geo_el]
                                            elif apval["type"] == 'O':
                                                if 'O' in flash_el_dict:
                                                    flash_el_dict['O'].append(geo_el)
                                                else:
                                                    flash_el_dict['O'] = [geo_el]
                                            elif apval["type"] == 'R':
                                                if 'R' in flash_el_dict:
                                                    flash_el_dict['R'].append(geo_el)
                                                else:
                                                    flash_el_dict['R'] = [geo_el]
                                        else:
                                            aperture_size = apval['size']

                                            if aperture_size in traces_el_dict:
                                                traces_el_dict[aperture_size].append(geo_el)
                                            else:
                                                traces_el_dict[aperture_size] = [geo_el]

                            cp = FlatCAMRTreeStorage()
                            pads_lines_list = []

                            # process the flashes found in the selected polygon with the 'lines' method
                            # for rectangular flashes and with _("Seed") for oblong and circular flashes
                            # and pads (flahes) need the contour therefore I override the GUI settings
                            # with always True
                            for ap_type in flash_el_dict:
                                for elem in flash_el_dict[ap_type]:
                                    if 'solid' in elem:
                                        if ap_type == 'C':
                                            f_o = self.clear_polygon2(elem['solid'],
                                                                      tooldia=tool_dia,
                                                                      steps_per_circle=self.app.defaults[
                                                                          "geometry_circle_steps"],
                                                                      overlap=over,
                                                                      contour=True,
                                                                      connect=conn,
                                                                      prog_plot=prog_plot)
                                            pads_lines_list += [p for p in f_o.get_objects() if p]

                                        elif ap_type == 'O':
                                            f_o = self.clear_polygon2(elem['solid'],
                                                                      tooldia=tool_dia,
                                                                      steps_per_circle=self.app.defaults[
                                                                          "geometry_circle_steps"],
                                                                      overlap=over,
                                                                      contour=True,
                                                                      connect=conn,
                                                                      prog_plot=prog_plot)
                                            pads_lines_list += [p for p in f_o.get_objects() if p]

                                        elif ap_type == 'R':
                                            f_o = self.clear_polygon3(elem['solid'],
                                                                      tooldia=tool_dia,
                                                                      steps_per_circle=self.app.defaults[
                                                                          "geometry_circle_steps"],
                                                                      overlap=over,
                                                                      contour=True,
                                                                      connect=conn,
                                                                      prog_plot=prog_plot)

                                            pads_lines_list += [p for p in f_o.get_objects() if p]

                            # add the lines from pads to the storage
                            try:
                                for lin in pads_lines_list:
                                    if lin:
                                        cp.insert(lin)
                            except TypeError:
                                cp.insert(pads_lines_list)

                            copper_lines_list = []
                            # process the traces found in the selected polygon using the 'laser_lines'
                            # method, method which will follow the 'follow' line therefore use the longer
                            # path possible for the laser, therefore the acceleration will play
                            # a smaller factor
                            for aperture_size in traces_el_dict:
                                for elem in traces_el_dict[aperture_size]:
                                    line = elem['follow']
                                    if line:
                                        t_o = self.fill_with_lines(line, aperture_size,
                                                                   tooldia=tool_dia,
                                                                   steps_per_circle=self.app.defaults[
                                                                       "geometry_circle_steps"],
                                                                   overlap=over,
                                                                   contour=cont,
                                                                   connect=conn,
                                                                   prog_plot=prog_plot)

                                        copper_lines_list += [p for p in t_o.get_objects() if p]

                            # add the lines from copper features to storage but first try to make as few
                            # lines as possible
                            # by trying to fuse them
                            lines_union = linemerge(unary_union(copper_lines_list))
                            try:
                                for lin in lines_union:
                                    if lin:
                                        cp.insert(lin)
                            except TypeError:
                                cp.insert(lines_union)
                        elif paint_method == _("Combo"):
                            self.app.inform.emit(_("Painting polygons with method: lines."))
                            cp = self.clear_polygon3(poly_buf,
                                                     tooldia=tool_dia,
                                                     steps_per_circle=self.app.defaults[
                                                         "geometry_circle_steps"],
                                                     overlap=over,
                                                     contour=cont,
                                                     connect=conn,
                                                     prog_plot=prog_plot)

                            if cp and cp.objects:
                                pass
                            else:
                                self.app.inform.emit(_("Failed. Painting polygons with method: seed."))
                                cp = self.clear_polygon2(poly_buf,
                                                         tooldia=tool_dia,
                                                         steps_per_circle=self.app.defaults[
                                                             "geometry_circle_steps"],
                                                         overlap=over,
                                                         contour=cont,
                                                         connect=conn,
                                                         prog_plot=prog_plot)
                                if cp and cp.objects:
                                    pass
                                else:
                                    self.app.inform.emit(_("Failed. Painting polygons with method: standard."))
                                    cp = self.clear_polygon(poly_buf,
                                                            tooldia=tool_dia,
                                                            steps_per_circle=self.app.defaults[
                                                                "geometry_circle_steps"],
                                                            overlap=over,
                                                            contour=cont,
                                                            connect=conn,
                                                            prog_plot=prog_plot)

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
                    disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 100]))
                    # log.debug("Polygons cleared: %d" % pol_nr)

                    if old_disp_number < disp_number <= 100:
                        app_obj.proc_container.update_view_text(' %d%%' % disp_number)
                        old_disp_number = disp_number
                        # log.debug("Polygons cleared: %d. Percentage done: %d%%" % (pol_nr, disp_number))

                # find the tooluid associated with the current tool_dia so we know where to add the tool solid_geometry
                for k, v in tools_storage.items():
                    if float('%.*f' % (self.decimals, v['tooldia'])) == float('%.*f' % (self.decimals, tool_dia)):
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

            # clean the progressive plotted shapes if it was used
            if self.app.defaults["tools_paint_plotting"] == 'progressive':
                self.temp_shapes.clear(update=True)

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
                    app_obj.new_object("geometry", name, gen_paintarea_rest_machining, plot=plot)
                else:
                    app_obj.new_object("geometry", name, gen_paintarea, plot=plot)
            except FlatCAMApp.GracefulException:
                proc.done()
                return
            except Exception:
                proc.done()
                traceback.print_stack()
                return
            proc.done()
            # focus on Selected Tab
            self.app.ui.notebook.setCurrentWidget(self.app.ui.selected_tab)

        self.app.inform.emit(_("Polygon Paint started ..."))

        # Promise object with the new name
        self.app.collection.promise(name)

        if run_threaded:
            # Background
            self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})
        else:
            job_thread(app_obj=self.app)

    def paint_poly_area(self, obj, sel_obj,
                        tooldia=None,
                        overlap=None,
                        order=None,
                        margin=None,
                        method=None,
                        outname=None,
                        connect=None,
                        contour=None,
                        tools_storage=None,
                        plot=True,
                        run_threaded=True):
        """
        Paints all polygons in this object that are within the sel_obj object

        :param run_threaded:
        :param plot:
        :param obj: painted object
        :param sel_obj: paint only what is inside this object bounds
        :param tooldia: a tuple or single element made out of diameters of the tools to be used
        :param overlap: value by which the paths will overlap
        :param order: if the tools are ordered and how
        :param margin: a border around painting area
        :param outname: name of the resulting object
        :param connect: Connect lines to avoid tool lifts.
        :param contour: Paint around the edges.
        :param method: choice out of _("Seed"), 'normal', 'lines'
        :param tools_storage: whether to use the current tools_storage self.paints_tools or a different one.
        Usage of the different one is related to when this function is called from a TcL command.
        :return:
        """
        paint_method = method if method is not None else self.paintmethod_combo.get_value()

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

        # determine if to use the progressive plotting
        if self.app.defaults["tools_paint_plotting"] == 'progressive':
            prog_plot = True
        else:
            prog_plot = False

        proc = self.app.proc_container.new(_("Painting polygons..."))
        name = outname if outname is not None else self.obj_name + "_paint"

        over = overlap if overlap is not None else float(self.app.defaults["tools_paintoverlap"]) / 100.0
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
            if isinstance(obj, FlatCAMGerber):
                if app_obj.defaults["gerber_buffering"] == 'no':
                    app_obj.inform.emit('%s %s %s' %
                                        (_("Paint Tool."),
                                         _("Normal painting area task started."),
                                         _("Buffering geometry...")))
                else:
                    app_obj.inform.emit('%s %s' %
                                        (_("Paint Tool."), _("Normal painting area task started.")))
            else:
                app_obj.inform.emit('%s %s' %
                                    (_("Paint Tool."), _("Normal painting area task started.")))

            tool_dia = None
            if order == 'fwd':
                sorted_tools.sort(reverse=False)
            elif order == 'rev':
                sorted_tools.sort(reverse=True)
            else:
                pass

            # this is were heavy lifting is done and creating the geometry to be painted
            target_geo = MultiPolygon(obj.solid_geometry)

            if isinstance(obj, FlatCAMGerber):
                if self.app.defaults["tools_paint_plotting"] == 'progressive':
                    if isinstance(target_geo, list):
                        target_geo = MultiPolygon(target_geo).buffer(0)
                    else:
                        target_geo = target_geo.buffer(0)

            geo_to_paint = target_geo.intersection(sel_obj)

            painted_area = recurse(geo_to_paint)

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
                    if float('%.*f' % (self.decimals, v['tooldia'])) == float('%.*f' % (self.decimals, tool_dia)):
                        current_uid = int(k)
                        break

                # variables to display the percentage of work done
                geo_len = len(painted_area)
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
                        if paint_method == _("Seed"):
                            # Type(cp) == FlatCAMRTreeStorage | None
                            cp = self.clear_polygon2(poly_buf,
                                                     tooldia=tool_dia,
                                                     steps_per_circle=self.app.defaults["geometry_circle_steps"],
                                                     overlap=over,
                                                     contour=cont,
                                                     connect=conn,
                                                     prog_plot=prog_plot)

                        elif paint_method == _("Lines"):
                            # Type(cp) == FlatCAMRTreeStorage | None
                            cp = self.clear_polygon3(poly_buf,
                                                     tooldia=tool_dia,
                                                     steps_per_circle=self.app.defaults["geometry_circle_steps"],
                                                     overlap=over,
                                                     contour=cont,
                                                     connect=conn,
                                                     prog_plot=prog_plot)

                        elif paint_method == _("Standard"):
                            # Type(cp) == FlatCAMRTreeStorage | None
                            cp = self.clear_polygon(poly_buf,
                                                    tooldia=tool_dia,
                                                    steps_per_circle=self.app.defaults["geometry_circle_steps"],
                                                    overlap=over,
                                                    contour=cont,
                                                    connect=conn,
                                                    prog_plot=prog_plot)
                        elif paint_method == _("Laser_lines"):
                            # line = None
                            # aperture_size = None

                            # the key is the aperture type and the val is a list of geo elements
                            flash_el_dict = {}
                            # the key is the aperture size, the val is a list of geo elements
                            traces_el_dict = {}

                            # find the flashes and the lines that are in the selected polygon and store
                            # them separately
                            for apid, apval in obj.apertures.items():
                                for geo_el in apval['geometry']:
                                    if apval["size"] == 0.0:
                                        if apval["size"] in traces_el_dict:
                                            traces_el_dict[apval["size"]].append(geo_el)
                                        else:
                                            traces_el_dict[apval["size"]] = [geo_el]

                                    if 'follow' in geo_el and geo_el['follow'].within(poly_buf):
                                        if isinstance(geo_el['follow'], Point):
                                            if apval["type"] == 'C':
                                                if 'C' in flash_el_dict:
                                                    flash_el_dict['C'].append(geo_el)
                                                else:
                                                    flash_el_dict['C'] = [geo_el]
                                            elif apval["type"] == 'O':
                                                if 'O' in flash_el_dict:
                                                    flash_el_dict['O'].append(geo_el)
                                                else:
                                                    flash_el_dict['O'] = [geo_el]
                                            elif apval["type"] == 'R':
                                                if 'R' in flash_el_dict:
                                                    flash_el_dict['R'].append(geo_el)
                                                else:
                                                    flash_el_dict['R'] = [geo_el]
                                        else:
                                            aperture_size = apval['size']

                                            if aperture_size in traces_el_dict:
                                                traces_el_dict[aperture_size].append(geo_el)
                                            else:
                                                traces_el_dict[aperture_size] = [geo_el]

                            cp = FlatCAMRTreeStorage()
                            pads_lines_list = []

                            # process the flashes found in the selected polygon with the 'lines' method
                            # for rectangular flashes and with _("Seed") for oblong and circular flashes
                            # and pads (flahes) need the contour therefore I override the GUI settings
                            # with always True
                            for ap_type in flash_el_dict:
                                for elem in flash_el_dict[ap_type]:
                                    if 'solid' in elem:
                                        if ap_type == 'C':
                                            f_o = self.clear_polygon2(elem['solid'],
                                                                      tooldia=tool_dia,
                                                                      steps_per_circle=self.app.defaults[
                                                                          "geometry_circle_steps"],
                                                                      overlap=over,
                                                                      contour=True,
                                                                      connect=conn,
                                                                      prog_plot=prog_plot)
                                            pads_lines_list += [p for p in f_o.get_objects() if p]

                                        elif ap_type == 'O':
                                            f_o = self.clear_polygon2(elem['solid'],
                                                                      tooldia=tool_dia,
                                                                      steps_per_circle=self.app.defaults[
                                                                          "geometry_circle_steps"],
                                                                      overlap=over,
                                                                      contour=True,
                                                                      connect=conn,
                                                                      prog_plot=prog_plot)
                                            pads_lines_list += [p for p in f_o.get_objects() if p]

                                        elif ap_type == 'R':
                                            f_o = self.clear_polygon3(elem['solid'],
                                                                      tooldia=tool_dia,
                                                                      steps_per_circle=self.app.defaults[
                                                                          "geometry_circle_steps"],
                                                                      overlap=over,
                                                                      contour=True,
                                                                      connect=conn,
                                                                      prog_plot=prog_plot)

                                            pads_lines_list += [p for p in f_o.get_objects() if p]

                            # add the lines from pads to the storage
                            try:
                                for lin in pads_lines_list:
                                    if lin:
                                        cp.insert(lin)
                            except TypeError:
                                cp.insert(pads_lines_list)

                            copper_lines_list = []
                            # process the traces found in the selected polygon using the 'laser_lines'
                            # method, method which will follow the 'follow' line therefore use the longer
                            # path possible for the laser, therefore the acceleration will play
                            # a smaller factor
                            for aperture_size in traces_el_dict:
                                for elem in traces_el_dict[aperture_size]:
                                    line = elem['follow']
                                    if line:
                                        t_o = self.fill_with_lines(line, aperture_size,
                                                                   tooldia=tool_dia,
                                                                   steps_per_circle=self.app.defaults[
                                                                       "geometry_circle_steps"],
                                                                   overlap=over,
                                                                   contour=cont,
                                                                   connect=conn,
                                                                   prog_plot=prog_plot)

                                        copper_lines_list += [p for p in t_o.get_objects() if p]

                            # add the lines from copper features to storage but first try to make as few
                            # lines as possible
                            # by trying to fuse them
                            lines_union = linemerge(unary_union(copper_lines_list))
                            try:
                                for lin in lines_union:
                                    if lin:
                                        cp.insert(lin)
                            except TypeError:
                                cp.insert(lines_union)
                        elif paint_method == _("Combo"):
                            self.app.inform.emit(_("Painting polygons with method: lines."))
                            cp = self.clear_polygon3(poly_buf,
                                                     tooldia=tool_dia,
                                                     steps_per_circle=self.app.defaults[
                                                         "geometry_circle_steps"],
                                                     overlap=over,
                                                     contour=cont,
                                                     connect=conn,
                                                     prog_plot=prog_plot)

                            if cp and cp.objects:
                                pass
                            else:
                                self.app.inform.emit(_("Failed. Painting polygons with method: seed."))
                                cp = self.clear_polygon2(poly_buf,
                                                         tooldia=tool_dia,
                                                         steps_per_circle=self.app.defaults[
                                                             "geometry_circle_steps"],
                                                         overlap=over,
                                                         contour=cont,
                                                         connect=conn,
                                                         prog_plot=prog_plot)
                                if cp and cp.objects:
                                    pass
                                else:
                                    self.app.inform.emit(_("Failed. Painting polygons with method: standard."))
                                    cp = self.clear_polygon(poly_buf,
                                                            tooldia=tool_dia,
                                                            steps_per_circle=self.app.defaults[
                                                                "geometry_circle_steps"],
                                                            overlap=over,
                                                            contour=cont,
                                                            connect=conn,
                                                            prog_plot=prog_plot)
                        if cp and cp.objects:
                            total_geometry += list(cp.get_objects())
                    except FlatCAMApp.GracefulException:
                        return "fail"
                    except Exception as e:
                        log.debug("Could not Paint the polygons. %s" % str(e))
                        self.app.inform.emit('[ERROR] %s\n%s' %
                                             (_("Could not do Paint All. Try a different combination of parameters. "
                                                "Or a different Method of paint"), str(e)))
                        return

                    pol_nr += 1
                    disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 100]))
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

            # clean the progressive plotted shapes if it was used
            if self.app.defaults["tools_paint_plotting"] == 'progressive':
                self.temp_shapes.clear(update=True)

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

            self.app.inform.emit('[success] %s' % _("Paint Area Done."))

        # Initializes the new geometry object
        def gen_paintarea_rest_machining(geo_obj, app_obj):
            assert isinstance(geo_obj, FlatCAMGeometry), \
                "Initializer expected a FlatCAMGeometry, got %s" % type(geo_obj)

            log.debug("Paint Tool. Rest machining painting area task started.")
            if isinstance(obj, FlatCAMGerber):
                if app_obj.defaults["gerber_buffering"] == 'no':
                    app_obj.inform.emit('%s %s %s' %
                                        (_("Paint Tool."),
                                         _("Rest machining painting area task started."),
                                         _("Buffering geometry...")))
                else:
                    app_obj.inform.emit(_("Paint Tool. Rest machining painting area task started."))
            else:
                app_obj.inform.emit('%s %s' %
                                    (_("Paint Tool."), _("Rest machining painting area task started.")))

            tool_dia = None
            sorted_tools.sort(reverse=True)

            cleared_geo = []
            current_uid = int(1)
            geo_obj.solid_geometry = []

            # this is were heavy lifting is done and creating the geometry to be painted
            target_geo = obj.solid_geometry

            if isinstance(obj, FlatCAMGerber):
                if self.app.defaults["tools_paint_plotting"] == 'progressive':
                    if isinstance(target_geo, list):
                        target_geo = MultiPolygon(target_geo).buffer(0)
                    else:
                        target_geo = target_geo.buffer(0)

            geo_to_paint = target_geo.intersection(sel_obj)

            painted_area = recurse(geo_to_paint)

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

                # variables to display the percentage of work done
                geo_len = len(painted_area)
                old_disp_number = 0
                log.warning("Total number of polygons to be cleared. %s" % str(geo_len))

                pol_nr = 0
                for geo in painted_area:
                    try:
                        geo = Polygon(geo) if not isinstance(geo, Polygon) else geo
                        poly_buf = geo.buffer(-paint_margin)
                        cp = None

                        if paint_method == _("Standard"):
                            # Type(cp) == FlatCAMRTreeStorage | None
                            cp = self.clear_polygon(poly_buf, tooldia=tool_dia,
                                                    steps_per_circle=self.app.defaults["geometry_circle_steps"],
                                                    overlap=over, contour=cont, connect=conn,
                                                    prog_plot=prog_plot)

                        elif paint_method == _("Seed"):
                            # Type(cp) == FlatCAMRTreeStorage | None
                            cp = self.clear_polygon2(poly_buf, tooldia=tool_dia,
                                                     steps_per_circle=self.app.defaults["geometry_circle_steps"],
                                                     overlap=over, contour=cont, connect=conn,
                                                     prog_plot=prog_plot)

                        elif paint_method == _("Lines"):
                            # Type(cp) == FlatCAMRTreeStorage | None
                            cp = self.clear_polygon3(poly_buf, tooldia=tool_dia,
                                                     steps_per_circle=self.app.defaults["geometry_circle_steps"],
                                                     overlap=over, contour=cont, connect=conn,
                                                     prog_plot=prog_plot)
                        elif paint_method == _("Laser_lines"):
                            # line = None
                            # aperture_size = None

                            # the key is the aperture type and the val is a list of geo elements
                            flash_el_dict = {}
                            # the key is the aperture size, the val is a list of geo elements
                            copper_el_dict = {}

                            # find the flashes and the lines that are in the selected polygon and store
                            # them separately
                            for apid, apval in obj.apertures.items():
                                for geo_el in apval['geometry']:
                                    if apval["size"] == 0.0:
                                        if apval["size"] in copper_el_dict:
                                            copper_el_dict[apval["size"]].append(geo_el)
                                        else:
                                            copper_el_dict[apval["size"]] = [geo_el]

                                    if 'follow' in geo_el and geo_el['follow'].within(poly_buf):
                                        if isinstance(geo_el['follow'], Point):
                                            if apval["type"] == 'C':
                                                if 'C' in flash_el_dict:
                                                    flash_el_dict['C'].append(geo_el)
                                                else:
                                                    flash_el_dict['C'] = [geo_el]
                                            elif apval["type"] == 'O':
                                                if 'O' in flash_el_dict:
                                                    flash_el_dict['O'].append(geo_el)
                                                else:
                                                    flash_el_dict['O'] = [geo_el]
                                            elif apval["type"] == 'R':
                                                if 'R' in flash_el_dict:
                                                    flash_el_dict['R'].append(geo_el)
                                                else:
                                                    flash_el_dict['R'] = [geo_el]
                                        else:
                                            aperture_size = apval['size']

                                            if aperture_size in copper_el_dict:
                                                copper_el_dict[aperture_size].append(geo_el)
                                            else:
                                                copper_el_dict[aperture_size] = [geo_el]

                            cp = FlatCAMRTreeStorage()
                            pads_lines_list = []

                            # process the flashes found in the selected polygon with the 'lines' method
                            # for rectangular flashes and with _("Seed") for oblong and circular flashes
                            # and pads (flahes) need the contour therefore I override the GUI settings
                            # with always True
                            for ap_type in flash_el_dict:
                                for elem in flash_el_dict[ap_type]:
                                    if 'solid' in elem:
                                        if ap_type == 'C':
                                            f_o = self.clear_polygon2(elem['solid'],
                                                                      tooldia=tool_dia,
                                                                      steps_per_circle=self.app.defaults[
                                                                          "geometry_circle_steps"],
                                                                      overlap=over,
                                                                      contour=True,
                                                                      connect=conn,
                                                                      prog_plot=prog_plot)
                                            pads_lines_list += [p for p in f_o.get_objects() if p]

                                        elif ap_type == 'O':
                                            f_o = self.clear_polygon2(elem['solid'],
                                                                      tooldia=tool_dia,
                                                                      steps_per_circle=self.app.defaults[
                                                                          "geometry_circle_steps"],
                                                                      overlap=over,
                                                                      contour=True,
                                                                      connect=conn,
                                                                      prog_plot=prog_plot)
                                            pads_lines_list += [p for p in f_o.get_objects() if p]

                                        elif ap_type == 'R':
                                            f_o = self.clear_polygon3(elem['solid'],
                                                                      tooldia=tool_dia,
                                                                      steps_per_circle=self.app.defaults[
                                                                          "geometry_circle_steps"],
                                                                      overlap=over,
                                                                      contour=True,
                                                                      connect=conn,
                                                                      prog_plot=prog_plot)

                                            pads_lines_list += [p for p in f_o.get_objects() if p]

                            # add the lines from pads to the storage
                            try:
                                for lin in pads_lines_list:
                                    if lin:
                                        cp.insert(lin)
                            except TypeError:
                                cp.insert(pads_lines_list)

                            copper_lines_list = []
                            # process the traces found in the selected polygon using the 'laser_lines'
                            # method, method which will follow the 'follow' line therefore use the longer
                            # path possible for the laser, therefore the acceleration will play
                            # a smaller factor
                            for aperture_size in copper_el_dict:
                                for elem in copper_el_dict[aperture_size]:
                                    line = elem['follow']
                                    if line:
                                        t_o = self.fill_with_lines(line, aperture_size,
                                                                   tooldia=tool_dia,
                                                                   steps_per_circle=self.app.defaults[
                                                                       "geometry_circle_steps"],
                                                                   overlap=over,
                                                                   contour=cont,
                                                                   connect=conn,
                                                                   prog_plot=prog_plot)

                                        copper_lines_list += [p for p in t_o.get_objects() if p]

                            # add the lines from copper features to storage but first try to make as few
                            # lines as possible
                            # by trying to fuse them
                            lines_union = linemerge(unary_union(copper_lines_list))
                            try:
                                for lin in lines_union:
                                    if lin:
                                        cp.insert(lin)
                            except TypeError:
                                cp.insert(lines_union)
                        elif paint_method == _("Combo"):
                            self.app.inform.emit(_("Painting polygons with method: lines."))
                            cp = self.clear_polygon3(poly_buf,
                                                     tooldia=tool_dia,
                                                     steps_per_circle=self.app.defaults["geometry_circle_steps"],
                                                     overlap=over,
                                                     contour=cont,
                                                     connect=conn,
                                                     prog_plot=prog_plot)

                            if cp and cp.objects:
                                pass
                            else:
                                self.app.inform.emit(_("Failed. Painting polygons with method: seed."))
                                cp = self.clear_polygon2(poly_buf,
                                                         tooldia=tool_dia,
                                                         steps_per_circle=self.app.defaults[
                                                             "geometry_circle_steps"],
                                                         overlap=over,
                                                         contour=cont,
                                                         connect=conn,
                                                         prog_plot=prog_plot)
                                if cp and cp.objects:
                                    pass
                                else:
                                    self.app.inform.emit(_("Failed. Painting polygons with method: standard."))
                                    cp = self.clear_polygon(poly_buf,
                                                            tooldia=tool_dia,
                                                            steps_per_circle=self.app.defaults[
                                                                "geometry_circle_steps"],
                                                            overlap=over,
                                                            contour=cont,
                                                            connect=conn,
                                                            prog_plot=prog_plot)
                        if cp and cp.objects:
                            cleared_geo += list(cp.get_objects())
                    except FlatCAMApp.GracefulException:
                        return "fail"
                    except Exception as e:
                        log.debug("Could not Paint the polygons. %s" % str(e))
                        self.app.inform.emit('[ERROR] %s\n%s' %
                                             (_("Could not do Paint All. Try a different combination of parameters. "
                                                "Or a different Method of paint"), str(e)))
                        return

                    pol_nr += 1
                    disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 100]))
                    # log.debug("Polygons cleared: %d" % pol_nr)

                    if old_disp_number < disp_number <= 100:
                        app_obj.proc_container.update_view_text(' %d%%' % disp_number)
                        old_disp_number = disp_number
                        # log.debug("Polygons cleared: %d. Percentage done: %d%%" % (pol_nr, disp_number))

                # find the tooluid associated with the current tool_dia so we know where to add the tool solid_geometry
                for k, v in tools_storage.items():
                    if float('%.*f' % (self.decimals, v['tooldia'])) == float('%.*f' % (self.decimals, tool_dia)):
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

            # clean the progressive plotted shapes if it was used
            if self.app.defaults["tools_paint_plotting"] == 'progressive':
                self.temp_shapes.clear(update=True)

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
                    app_obj.new_object("geometry", name, gen_paintarea_rest_machining, plot=plot)
                else:
                    app_obj.new_object("geometry", name, gen_paintarea, plot=plot)
            except FlatCAMApp.GracefulException:
                proc.done()
                return
            except Exception:
                proc.done()
                traceback.print_stack()
                return
            proc.done()
            # focus on Selected Tab
            self.app.ui.notebook.setCurrentWidget(self.app.ui.selected_tab)

        self.app.inform.emit(_("Polygon Paint started ..."))

        # Promise object with the new name
        self.app.collection.promise(name)

        if run_threaded:
            # Background
            self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})
        else:
            job_thread(app_obj=self.app)

    def paint_poly_ref(self, obj, sel_obj,
                       tooldia=None,
                       overlap=None,
                       order=None,
                       margin=None,
                       method=None,
                       outname=None,
                       connect=None,
                       contour=None,
                       tools_storage=None,
                       plot=True,
                       run_threaded=True):
        """
        Paints all polygons in this object that are within the sel_obj object

        :param run_threaded:
        :param plot:
        :param obj: painted object
        :param sel_obj: paint only what is inside this object bounds
        :param tooldia: a tuple or single element made out of diameters of the tools to be used
        :param overlap: value by which the paths will overlap
        :param order: if the tools are ordered and how
        :param margin: a border around painting area
        :param outname: name of the resulting object
        :param connect: Connect lines to avoid tool lifts.
        :param contour: Paint around the edges.
        :param method: choice out of _("Seed"), 'normal', 'lines'
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
                             tools_storage=tools_storage,
                             plot=plot,
                             run_threaded=run_threaded)

    def ui_connect(self):
        self.tools_table.itemChanged.connect(self.on_tool_edit)

        # rows selected
        self.tools_table.clicked.connect(self.on_row_selection_change)
        self.tools_table.horizontalHeader().sectionClicked.connect(self.on_row_selection_change)

        for row in range(self.tools_table.rowCount()):
            try:
                self.tools_table.cellWidget(row, 2).currentIndexChanged.connect(self.on_tooltable_cellwidget_change)
            except AttributeError:
                pass

            try:
                self.tools_table.cellWidget(row, 4).currentIndexChanged.connect(self.on_tooltable_cellwidget_change)
            except AttributeError:
                pass

        self.tool_type_radio.activated_custom.connect(self.on_tool_type)

        # first disconnect
        for opt in self.form_fields:
            current_widget = self.form_fields[opt]
            if isinstance(current_widget, FCCheckBox):
                try:
                    current_widget.stateChanged.disconnect()
                except (TypeError, ValueError):
                    pass
            if isinstance(current_widget, RadioSet):
                try:
                    current_widget.activated_custom.disconnect()
                except (TypeError, ValueError):
                    pass
            elif isinstance(current_widget, FCDoubleSpinner):
                try:
                    current_widget.returnPressed.disconnect()
                except (TypeError, ValueError):
                    pass

        # then reconnect
        for opt in self.form_fields:
            current_widget = self.form_fields[opt]
            if isinstance(current_widget, FCCheckBox):
                current_widget.stateChanged.connect(self.form_to_storage)
            if isinstance(current_widget, RadioSet):
                current_widget.activated_custom.connect(self.form_to_storage)
            elif isinstance(current_widget, FCDoubleSpinner):
                current_widget.returnPressed.connect(self.form_to_storage)
            elif isinstance(current_widget, FCComboBox):
                current_widget.currentIndexChanged.connect(self.form_to_storage)

        self.rest_cb.stateChanged.connect(self.on_rest_machining_check)
        self.order_radio.activated_custom[str].connect(self.on_order_changed)

    def ui_disconnect(self):
        try:
            # if connected, disconnect the signal from the slot on item_changed as it creates issues
            self.tools_table.itemChanged.disconnect()
        except (TypeError, AttributeError):
            pass

        # rows selected
        try:
            self.tools_table.clicked.disconnect(self.on_row_selection_change)
        except (TypeError, AttributeError):
            pass

        try:
            self.tools_table.horizontalHeader().sectionClicked.disconnect(self.on_row_selection_change)
        except (TypeError, AttributeError):
            pass

        try:
            # if connected, disconnect the signal from the slot on item_changed as it creates issues
            self.tool_type_radio.activated_custom.disconnect()
        except (TypeError, AttributeError):
            pass

        for row in range(self.tools_table.rowCount()):
            for col in [2, 4]:
                try:
                    self.ui.geo_tools_table.cellWidget(row, col).currentIndexChanged.disconnect()
                except (TypeError, AttributeError):
                    pass

        for opt in self.form_fields:
            current_widget = self.form_fields[opt]
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
            elif isinstance(current_widget, FCDoubleSpinner):
                try:
                    current_widget.returnPressed.disconnect(self.form_to_storage)
                except (TypeError, ValueError):
                    pass
            elif isinstance(current_widget, FCComboBox):
                try:
                    current_widget.currentIndexChanged.connect(self.form_to_storage)
                except (TypeError, ValueError):
                    pass

    def reset_usage(self):
        self.obj_name = ""
        self.paint_obj = None
        self.bound_obj = None

        self.first_click = False
        self.cursor_pos = None
        self.mouse_is_dragging = False

        self.sel_rect = []

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
