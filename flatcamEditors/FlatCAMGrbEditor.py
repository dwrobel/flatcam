from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import Qt, QSettings

from shapely.geometry import LineString, LinearRing, MultiLineString
from shapely.ops import cascaded_union
import shapely.affinity as affinity

from numpy import arctan2, Inf, array, sqrt, sign, dot
from rtree import index as rtindex
import threading, time
import copy

from camlib import *
from flatcamGUI.GUIElements import FCEntry, FCComboBox, FCTable, FCDoubleSpinner, LengthEntry, RadioSet, \
    SpinBoxDelegate, EvalEntry
from flatcamEditors.FlatCAMGeoEditor import FCShapeTool, DrawTool, DrawToolShape, DrawToolUtilityShape, FlatCAMGeoEditor
from FlatCAMObj import FlatCAMGerber
from FlatCAMTool import FlatCAMTool

import gettext
import FlatCAMTranslation as fcTranslate

fcTranslate.apply_language('strings')
import builtins
if '_' not in builtins.__dict__:
    _ = gettext.gettext


# class ScaleGrbTool(FlatCAMTool):
#     """
#     Simple input for buffer distance.
#     """
#
#     toolName = _("Scale")
#
#     def __init__(self, app, draw_app):
#         FlatCAMTool.__init__(self, app)
#
#         self.draw_app = draw_app
#
#         # Title
#         title_label = QtWidgets.QLabel("{name} {tooln} ".format(name=_("Editor"), tooln=self.toolName))
#         title_label.setStyleSheet("""
#                         QLabel
#                         {
#                             font-size: 16px;
#                             font-weight: bold;
#                         }
#                         """)
#         self.layout.addWidget(title_label)
#
#         # this way I can hide/show the frame
#         self.scale_tool_frame = QtWidgets.QFrame()
#         self.scale_tool_frame.setContentsMargins(0, 0, 0, 0)
#         self.layout.addWidget(self.scale_tool_frame)
#         self.scale_tools_box = QtWidgets.QVBoxLayout()
#         self.scale_tools_box.setContentsMargins(0, 0, 0, 0)
#         self.scale_tool_frame.setLayout(self.scale_tools_box)
#
#         # Form Layout
#         form_layout = QtWidgets.QFormLayout()
#         self.scale_tools_box.addLayout(form_layout)
#
#         # Buffer distance
#         self.scale_factor_entry = FCEntry()
#         form_layout.addRow(_("Scale Factor:"), self.scale_factor_entry)
#
#         # Buttons
#         hlay1 = QtWidgets.QHBoxLayout()
#         self.scale_tools_box.addLayout(hlay1)
#
#         self.scale_button = QtWidgets.QPushButton(_("Scale"))
#         hlay1.addWidget(self.scale_button)
#
#         self.layout.addStretch()
#
#         # Signals
#         self.scale_button.clicked.connect(self.on_scale)
#
#         # Init GUI
#         self.scale_factor_entry.set_value(1)
#
#     def run(self):
#         self.app.report_usage("Gerber Editor ToolScale()")
#         FlatCAMTool.run(self)
#
#         # if the splitter us hidden, display it
#         if self.app.ui.splitter.sizes()[0] == 0:
#             self.app.ui.splitter.setSizes([1, 1])
#
#         self.app.ui.notebook.setTabText(2, _("Scale Tool"))
#
#     def on_scale(self):
#         if not self.draw_app.selected:
#             self.app.inform.emit(_("[WARNING_NOTCL] Scale cancelled. No aperture selected."))
#             return
#
#         try:
#             buffer_distance = float(self.buff_tool.buffer_distance_entry.get_value())
#         except ValueError:
#             # try to convert comma to decimal point. if it's still not working error message and return
#             try:
#                 buffer_distance = float(self.buff_tool.buffer_distance_entry.get_value().replace(',', '.'))
#                 self.buff_tool.buffer_distance_entry.set_value(buffer_distance)
#             except ValueError:
#                 self.app.inform.emit(_("[WARNING_NOTCL] Buffer distance value is missing or wrong format. "
#                                        "Add it and retry."))
#                 return
#         # the cb index start from 0 but the join styles for the buffer start from 1 therefore the adjustment
#         # I populated the combobox such that the index coincide with the join styles value (whcih is really an INT)
#         join_style = self.buff_tool.buffer_corner_cb.currentIndex() + 1
#         self.draw_app.buffer(buffer_distance, join_style)
#         self.app.ui.notebook.setTabText(2, _("Tools"))
#         self.draw_app.app.ui.splitter.setSizes([0, 1])
#
#         self.deactivate()
#         self.app.inform.emit(_("[success] Done. Scale Tool completed."))


class FCScale(FCShapeTool):
    def __init__(self, draw_app):
        FCShapeTool.__init__(self, draw_app)
        self.name = 'scale'

        # self.shape_buffer = self.draw_app.shape_buffer
        self.draw_app = draw_app
        self.app = draw_app.app

        self.start_msg = _("Scale the selected Gerber apertures ...")
        self.origin = (0, 0)

        if self.draw_app.app.ui.splitter.sizes()[0] == 0:
            self.draw_app.app.ui.splitter.setSizes([1, 1])
        self.activate()

    def activate(self):
        self.draw_app.hide_tool('all')
        self.draw_app.scale_tool_frame.show()

        try:
            self.draw_app.scale_button.clicked.disconnect()
        except TypeError:
            pass
        self.draw_app.scale_button.clicked.connect(self.on_scale_click)

    def deactivate(self):
        self.draw_app.scale_button.clicked.disconnect()
        self.complete = True
        self.draw_app.select_tool("select")
        self.draw_app.hide_tool(self.name)

    def on_scale_click(self):
        self.draw_app.on_scale()
        self.deactivate()


class FCBuffer(FCShapeTool):
    def __init__(self, draw_app):
        FCShapeTool.__init__(self, draw_app)
        self.name = 'buffer'

        # self.shape_buffer = self.draw_app.shape_buffer
        self.draw_app = draw_app
        self.app = draw_app.app

        self.start_msg = _("Buffer the selected apertures ...")
        self.origin = (0, 0)

        if self.draw_app.app.ui.splitter.sizes()[0] == 0:
            self.draw_app.app.ui.splitter.setSizes([1, 1])
        self.activate()

    def activate(self):
        self.draw_app.hide_tool('all')
        self.draw_app.buffer_tool_frame.show()

        try:
            self.draw_app.buffer_button.clicked.disconnect()
        except TypeError:
            pass
        self.draw_app.buffer_button.clicked.connect(self.on_buffer_click)

    def deactivate(self):
        self.draw_app.buffer_button.clicked.disconnect()
        self.complete = True
        self.draw_app.select_tool("select")
        self.draw_app.hide_tool(self.name)

    def on_buffer_click(self):
        self.draw_app.on_buffer()
        self.deactivate()


class FCApertureMove(FCShapeTool):
    def __init__(self, draw_app):
        DrawTool.__init__(self, draw_app)
        self.name = 'aperture_move'

        # self.shape_buffer = self.draw_app.shape_buffer
        self.origin = None
        self.destination = None
        self.selected_apertures = []

        if self.draw_app.launched_from_shortcuts is True:
            self.draw_app.launched_from_shortcuts = False
            self.draw_app.app.inform.emit(_("Click on target location ..."))
        else:
            self.draw_app.app.inform.emit(_("Click on reference location ..."))
        self.current_storage = None
        self.geometry = []

        for index in self.draw_app.apertures_table.selectedIndexes():
            row = index.row()
            # on column 1 in tool tables we hold the diameters, and we retrieve them as strings
            # therefore below we convert to float
            aperture_on_row = self.draw_app.apertures_table.item(row, 1).text()
            self.selected_apertures.append(aperture_on_row)

        # Switch notebook to Selected page
        self.draw_app.app.ui.notebook.setCurrentWidget(self.draw_app.app.ui.selected_tab)

    def set_origin(self, origin):
        self.origin = origin

    def click(self, point):
        if len(self.draw_app.get_selected()) == 0:
            return "Nothing to move."

        if self.origin is None:
            self.set_origin(point)
            self.draw_app.app.inform.emit(_("Click on target location ..."))
            return
        else:
            self.destination = point
            self.make()

            # MS: always return to the Select Tool
            self.draw_app.select_tool("select")
            return

    def make(self):
        # Create new geometry
        dx = self.destination[0] - self.origin[0]
        dy = self.destination[1] - self.origin[1]
        sel_shapes_to_be_deleted = []

        for sel_dia in self.selected_apertures:
            self.current_storage = self.draw_app.storage_dict[sel_dia]['solid_geometry']
            for select_shape in self.draw_app.get_selected():
                if select_shape in self.current_storage:

                    self.geometry.append(DrawToolShape(affinity.translate(select_shape.geo, xoff=dx, yoff=dy)))
                    self.current_storage.remove(select_shape)
                    sel_shapes_to_be_deleted.append(select_shape)
                    self.draw_app.on_grb_shape_complete(self.current_storage)
                    self.geometry = []

            for shp in sel_shapes_to_be_deleted:
                self.draw_app.selected.remove(shp)
            sel_shapes_to_be_deleted = []

        self.draw_app.build_ui()
        self.draw_app.app.inform.emit(_("[success] Done. Apertures Move completed."))

    def utility_geometry(self, data=None):
        """
        Temporary geometry on screen while using this tool.

        :param data:
        :return:
        """
        geo_list = []

        if self.origin is None:
            return None

        if len(self.draw_app.get_selected()) == 0:
            return None

        dx = data[0] - self.origin[0]
        dy = data[1] - self.origin[1]
        for geom in self.draw_app.get_selected():
            geo_list.append(affinity.translate(geom.geo, xoff=dx, yoff=dy))
        return DrawToolUtilityShape(geo_list)


class FCApertureCopy(FCApertureMove):
    def __init__(self, draw_app):
        FCApertureMove.__init__(self, draw_app)
        self.name = 'aperture_copy'

    def make(self):
        # Create new geometry
        dx = self.destination[0] - self.origin[0]
        dy = self.destination[1] - self.origin[1]
        sel_shapes_to_be_deleted = []

        for sel_dia in self.selected_apertures:
            self.current_storage = self.draw_app.storage_dict[sel_dia]['solid_geometry']
            for select_shape in self.draw_app.get_selected():
                if select_shape in self.current_storage:
                    self.geometry.append(DrawToolShape(affinity.translate(select_shape.geo, xoff=dx, yoff=dy)))

                    sel_shapes_to_be_deleted.append(select_shape)
                    self.draw_app.on_grb_shape_complete(self.current_storage)
                    self.geometry = []

            for shp in sel_shapes_to_be_deleted:
                self.draw_app.selected.remove(shp)
            sel_shapes_to_be_deleted = []

        self.draw_app.build_ui()
        self.draw_app.app.inform.emit(_("[success] Done. Apertures copied."))


class FCApertureSelect(DrawTool):
    def __init__(self, grb_editor_app):
        DrawTool.__init__(self, grb_editor_app)
        self.name = 'select'

        self.grb_editor_app = grb_editor_app
        self.storage = self.grb_editor_app.storage_dict
        # self.selected = self.grb_editor_app.selected

        # here we store all shapes that were selected
        self.sel_storage = []

        self.grb_editor_app.apertures_table.clearSelection()
        self.grb_editor_app.hide_tool('all')
        self.grb_editor_app.hide_tool('select')

    def click(self, point):
        key_modifier = QtWidgets.QApplication.keyboardModifiers()
        if self.grb_editor_app.app.defaults["global_mselect_key"] == 'Control':
            if key_modifier == Qt.ControlModifier:
                pass
            else:
                self.grb_editor_app.selected = []
        else:
            if key_modifier == Qt.ShiftModifier:
                pass
            else:
                self.grb_editor_app.selected = []

    def click_release(self, point):
        self.grb_editor_app.apertures_table.clearSelection()
        sel_aperture = set()
        for storage in self.grb_editor_app.storage_dict:
            for shape in self.grb_editor_app.storage_dict[storage]['solid_geometry']:
                if Point(point).within(shape.geo):
                    if self.draw_app.key == self.draw_app.app.defaults["global_mselect_key"]:
                        if shape in self.draw_app.selected:
                            self.draw_app.selected.remove(shape)
                        else:
                            # add the object to the selected shapes
                            self.draw_app.selected.append(shape)
                            sel_aperture.add(storage)
                    else:
                        self.draw_app.selected.append(shape)
                        sel_aperture.add(storage)

        try:
            self.draw_app.apertures_table.cellPressed.disconnect()
        except:
            pass

        self.grb_editor_app.apertures_table.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        for aper in sel_aperture:
            for row in range(self.grb_editor_app.apertures_table.rowCount()):
                if str(aper) == self.grb_editor_app.apertures_table.item(row, 1).text():
                    self.grb_editor_app.apertures_table.selectRow(row)
                    self.draw_app.last_aperture_selected = aper
        self.grb_editor_app.apertures_table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        self.draw_app.apertures_table.cellPressed.connect(self.draw_app.on_row_selected)

        return ""


class FlatCAMGrbEditor(QtCore.QObject):

    draw_shape_idx = -1

    def __init__(self, app):
        assert isinstance(app, FlatCAMApp.App), \
            "Expected the app to be a FlatCAMApp.App, got %s" % type(app)

        super(FlatCAMGrbEditor, self).__init__()

        self.app = app
        self.canvas = self.app.plotcanvas

        ## Current application units in Upper Case
        self.units = self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().upper()

        self.grb_edit_widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        self.grb_edit_widget.setLayout(layout)

        ## Page Title box (spacing between children)
        self.title_box = QtWidgets.QHBoxLayout()
        layout.addLayout(self.title_box)

        ## Page Title icon
        pixmap = QtGui.QPixmap('share/flatcam_icon32.png')
        self.icon = QtWidgets.QLabel()
        self.icon.setPixmap(pixmap)
        self.title_box.addWidget(self.icon, stretch=0)

        ## Title label
        self.title_label = QtWidgets.QLabel("<font size=5><b>%s</b></font>" % _('Gerber Editor'))
        self.title_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.title_box.addWidget(self.title_label, stretch=1)

        ## Object name
        self.name_box = QtWidgets.QHBoxLayout()
        layout.addLayout(self.name_box)
        name_label = QtWidgets.QLabel(_("Name:"))
        self.name_box.addWidget(name_label)
        self.name_entry = FCEntry()
        self.name_box.addWidget(self.name_entry)

        ## Box for custom widgets
        # This gets populated in offspring implementations.
        self.custom_box = QtWidgets.QVBoxLayout()
        layout.addLayout(self.custom_box)


        #### Gerber Apertures ####
        self.apertures_table_label = QtWidgets.QLabel(_('<b>Apertures:</b>'))
        self.apertures_table_label.setToolTip(
            _("Apertures Table for the Gerber Object.")
        )
        self.custom_box.addWidget(self.apertures_table_label)

        self.apertures_table = FCTable()
        # delegate = SpinBoxDelegate(units=self.units)
        # self.apertures_table.setItemDelegateForColumn(1, delegate)

        self.custom_box.addWidget(self.apertures_table)

        self.apertures_table.setColumnCount(5)
        self.apertures_table.setHorizontalHeaderLabels(['#', _('Code'), _('Type'), _('Size'), _('Dim')])
        self.apertures_table.setSortingEnabled(False)

        self.apertures_table.horizontalHeaderItem(0).setToolTip(
            _("Index"))
        self.apertures_table.horizontalHeaderItem(1).setToolTip(
            _("Aperture Code"))
        self.apertures_table.horizontalHeaderItem(2).setToolTip(
            _("Type of aperture: circular, rectangle, macros etc"))
        self.apertures_table.horizontalHeaderItem(4).setToolTip(
            _("Aperture Size:"))
        self.apertures_table.horizontalHeaderItem(4).setToolTip(
            _("Aperture Dimensions:\n"
              " - (width, height) for R, O type.\n"
              " - (dia, nVertices) for P type"))

        self.empty_label = QtWidgets.QLabel('')
        self.custom_box.addWidget(self.empty_label)

        # add a frame and inside add a vertical box layout. Inside this vbox layout I add all the Apertures widgets
        # this way I can hide/show the frame
        self.apertures_frame = QtWidgets.QFrame()
        self.apertures_frame.setContentsMargins(0, 0, 0, 0)
        self.custom_box.addWidget(self.apertures_frame)
        self.apertures_box = QtWidgets.QVBoxLayout()
        self.apertures_box.setContentsMargins(0, 0, 0, 0)
        self.apertures_frame.setLayout(self.apertures_box)

        #### Add/Delete an new Aperture ####

        grid1 = QtWidgets.QGridLayout()
        self.apertures_box.addLayout(grid1)

        apcode_lbl = QtWidgets.QLabel(_('Aperture Code:'))
        apcode_lbl.setToolTip(
        _("Code for the new aperture")
        )
        grid1.addWidget(apcode_lbl, 1, 0)

        self.apcode_entry = FCEntry()
        self.apcode_entry.setValidator(QtGui.QIntValidator(0, 999))
        grid1.addWidget(self.apcode_entry, 1, 1)

        apsize_lbl = QtWidgets.QLabel(_('Aperture Size:'))
        apsize_lbl.setToolTip(
        _("Size for the new aperture")
        )
        grid1.addWidget(apsize_lbl, 2, 0)

        self.apsize_entry = FCEntry()
        self.apsize_entry.setValidator(QtGui.QDoubleValidator(0.0001, 99.9999, 4))
        grid1.addWidget(self.apsize_entry, 2, 1)

        aptype_lbl = QtWidgets.QLabel(_('Aperture Type:'))
        aptype_lbl.setToolTip(
        _("Select the type of new aperture. Can be:\n"
          "C = circular\n"
          "R = rectangular")
        )
        grid1.addWidget(aptype_lbl, 3, 0)

        self.aptype_cb = FCComboBox()
        self.aptype_cb.addItems(['C', 'R'])
        grid1.addWidget(self.aptype_cb, 3, 1)

        self.apdim_lbl = QtWidgets.QLabel(_('Aperture Dim:'))
        self.apdim_lbl.setToolTip(
        _("Dimensions for the new aperture.\n"
          "Active only for rectangular apertures (type R).\n"
          "The format is (width, height)")
        )
        grid1.addWidget(self.apdim_lbl, 4, 0)

        self.apdim_entry = EvalEntry()
        grid1.addWidget(self.apdim_entry, 4, 1)

        apadd_lbl = QtWidgets.QLabel('<b>%s</b>' % _('Add Aperture:'))
        apadd_lbl.setToolTip(
            _("Add an aperture to the aperture list")
        )
        grid1.addWidget(apadd_lbl, 5, 0)

        self.addaperture_btn = QtWidgets.QPushButton(_('Go'))
        self.addaperture_btn.setToolTip(
           _( "Add a new aperture to the aperture list")
        )
        grid1.addWidget(self.addaperture_btn, 5, 1)

        apdelete_lbl = QtWidgets.QLabel('<b>%s</b>' % _('Del Aperture:'))
        apdelete_lbl.setToolTip(
            _( "Delete a aperture in the aperture list")
        )
        grid1.addWidget(apdelete_lbl, 6, 0)

        self.delaperture_btn = QtWidgets.QPushButton(_('Go'))
        self.delaperture_btn.setToolTip(
           _( "Delete a aperture in the aperture list")
        )
        grid1.addWidget(self.delaperture_btn, 6, 1)

        ### BUFFER TOOL ###

        self.buffer_tool_frame = QtWidgets.QFrame()
        self.buffer_tool_frame.setContentsMargins(0, 0, 0, 0)
        self.custom_box.addWidget(self.buffer_tool_frame)
        self.buffer_tools_box = QtWidgets.QVBoxLayout()
        self.buffer_tools_box.setContentsMargins(0, 0, 0, 0)
        self.buffer_tool_frame.setLayout(self.buffer_tools_box)
        self.buffer_tool_frame.hide()

        # Title
        buf_title_lbl = QtWidgets.QLabel('<b>%s</b>' % _('Buffer Aperture:'))
        buf_title_lbl.setToolTip(
            _("Buffer a aperture in the aperture list")
        )
        self.buffer_tools_box.addWidget(buf_title_lbl)

        # Form Layout
        buf_form_layout = QtWidgets.QFormLayout()
        self.buffer_tools_box.addLayout(buf_form_layout)

        # Buffer distance
        self.buffer_distance_entry = FCEntry()
        buf_form_layout.addRow(_("Buffer distance:"), self.buffer_distance_entry)
        self.buffer_corner_lbl = QtWidgets.QLabel(_("Buffer corner:"))
        self.buffer_corner_lbl.setToolTip(
            _("There are 3 types of corners:\n"
              " - 'Round': the corner is rounded.\n"
              " - 'Square:' the corner is met in a sharp angle.\n"
              " - 'Beveled:' the corner is a line that directly connects the features meeting in the corner")
        )
        self.buffer_corner_cb = FCComboBox()
        self.buffer_corner_cb.addItem(_("Round"))
        self.buffer_corner_cb.addItem(_("Square"))
        self.buffer_corner_cb.addItem(_("Beveled"))
        buf_form_layout.addRow(self.buffer_corner_lbl, self.buffer_corner_cb)

        # Buttons
        hlay_buf = QtWidgets.QHBoxLayout()
        self.buffer_tools_box.addLayout(hlay_buf)

        self.buffer_button = QtWidgets.QPushButton(_("Buffer"))
        hlay_buf.addWidget(self.buffer_button)

        ### SCALE TOOL ###

        self.scale_tool_frame = QtWidgets.QFrame()
        self.scale_tool_frame.setContentsMargins(0, 0, 0, 0)
        self.custom_box.addWidget(self.scale_tool_frame)
        self.scale_tools_box = QtWidgets.QVBoxLayout()
        self.scale_tools_box.setContentsMargins(0, 0, 0, 0)
        self.scale_tool_frame.setLayout(self.scale_tools_box)
        self.scale_tool_frame.hide()

        # Title
        scale_title_lbl = QtWidgets.QLabel('<b>%s</b>' % _('Scale Aperture:'))
        scale_title_lbl.setToolTip(
            _("Scale a aperture in the aperture list")
        )
        self.scale_tools_box.addWidget(scale_title_lbl)

        # Form Layout
        scale_form_layout = QtWidgets.QFormLayout()
        self.scale_tools_box.addLayout(scale_form_layout)

        self.scale_factor_lbl = QtWidgets.QLabel(_("Scale factor:"))
        self.scale_factor_lbl.setToolTip(
            _("The factor by which to scale the selected aperture.\n"
              "Values can be between 0.0000 and 999.9999")
        )
        self.scale_factor_entry = FCEntry()
        self.scale_factor_entry.setValidator(QtGui.QDoubleValidator(0.0000, 999.9999, 4))
        scale_form_layout.addRow(self.scale_factor_lbl, self.scale_factor_entry)

        # Buttons
        hlay_scale = QtWidgets.QHBoxLayout()
        self.scale_tools_box.addLayout(hlay_scale)

        self.scale_button = QtWidgets.QPushButton(_("Scale"))
        hlay_scale.addWidget(self.scale_button)


        self.custom_box.addStretch()

        ## Toolbar events and properties
        self.tools_gerber = {
            "select": {"button": self.app.ui.grb_select_btn,
                       "constructor": FCApertureSelect},
            "aperture_buffer": {"button": self.app.ui.aperture_buffer_btn,
                                "constructor": FCBuffer},
            "aperture_scale": {"button": self.app.ui.aperture_scale_btn,
                                "constructor": FCScale},
            "aperture_copy": {"button": self.app.ui.aperture_copy_btn,
                     "constructor": FCApertureCopy},
            "aperture_move": {"button": self.app.ui.aperture_move_btn,
                     "constructor": FCApertureMove},
        }

        ### Data
        self.active_tool = None

        self.storage_dict = {}
        self.current_storage = []

        self.sorted_apid =[]

        self.new_apertures = {}
        self.new_aperture_macros = {}

        # store here the plot promises, if empty the delayed plot will be activated
        self.grb_plot_promises = []

        # dictionary to store the tool_row and diameters in Tool_table
        # it will be updated everytime self.build_ui() is called
        self.olddia_newdia = {}

        self.tool2tooldia = {}

        # this will store the value for the last selected tool, for use after clicking on canvas when the selection
        # is cleared but as a side effect also the selected tool is cleared
        self.last_aperture_selected = None
        self.utility = []

        # this will flag if the Editor "tools" are launched from key shortcuts (True) or from menu toolbar (False)
        self.launched_from_shortcuts = False

        # this var will store the state of the toolbar before starting the editor
        self.toolbar_old_state = False

        # Signals
        self.buffer_button.clicked.connect(self.on_buffer)
        self.scale_button.clicked.connect(self.on_scale)

        self.app.ui.delete_drill_btn.triggered.connect(self.on_delete_btn)
        self.name_entry.returnPressed.connect(self.on_name_activate)

        self.aptype_cb.currentIndexChanged[str].connect(self.on_aptype_changed)

        self.addaperture_btn.clicked.connect(self.on_aperture_add)
        self.delaperture_btn.clicked.connect(self.on_aperture_delete)
        self.apertures_table.cellPressed.connect(self.on_row_selected)

        self.app.ui.grb_copy_menuitem.triggered.connect(self.on_copy_button)
        self.app.ui.grb_delete_menuitem.triggered.connect(self.on_delete_btn)

        self.app.ui.grb_move_menuitem.triggered.connect(self.on_move_button)


        # Init GUI
        self.apdim_lbl.hide()
        self.apdim_entry.hide()
        self.gerber_obj = None
        self.gerber_obj_options = {}

        self.buffer_distance_entry.set_value(0.01)
        self.scale_factor_entry.set_value(1.0)

        # VisPy Visuals
        self.shapes = self.app.plotcanvas.new_shape_collection(layers=1)
        self.tool_shape = self.app.plotcanvas.new_shape_collection(layers=1)
        self.app.pool_recreated.connect(self.pool_recreated)

        # Remove from scene
        self.shapes.enabled = False
        self.tool_shape.enabled = False

        ## List of selected shapes.
        self.selected = []

        self.move_timer = QtCore.QTimer()
        self.move_timer.setSingleShot(True)

        self.key = None  # Currently pressed key
        self.modifiers = None
        self.x = None  # Current mouse cursor pos
        self.y = None
        # Current snapped mouse pos
        self.snap_x = None
        self.snap_y = None
        self.pos = None

        def make_callback(thetool):
            def f():
                self.on_tool_select(thetool)
            return f

        for tool in self.tools_gerber:
            self.tools_gerber[tool]["button"].triggered.connect(make_callback(tool))  # Events
            self.tools_gerber[tool]["button"].setCheckable(True)  # Checkable

        self.options = {
            "global_gridx": 0.1,
            "global_gridy": 0.1,
            "snap_max": 0.05,
            "grid_snap": True,
            "corner_snap": False,
            "grid_gap_link": True
        }
        self.app.options_read_form()

        for option in self.options:
            if option in self.app.options:
                self.options[option] = self.app.options[option]

        # flag to show if the object was modified
        self.is_modified = False

        self.edited_obj_name = ""

        self.tool_row = 0

        # store the status of the editor so the Delete at object level will not work until the edit is finished
        self.editor_active = False

        def entry2option(option, entry):
            self.options[option] = float(entry.text())

        # store the status of the editor so the Delete at object level will not work until the edit is finished
        self.editor_active = False

    def pool_recreated(self, pool):
        self.shapes.pool = pool
        self.tool_shape.pool = pool

    def set_ui(self):
        # updated units
        self.units = self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().upper()

        self.olddia_newdia.clear()
        self.tool2tooldia.clear()

        # update the olddia_newdia dict to make sure we have an updated state of the tool_table
        for key in self.storage_dict:
            self.olddia_newdia[key] = key

        sort_temp = []
        for aperture in self.olddia_newdia:
            sort_temp.append(int(aperture))
        self.sorted_apid = sorted(sort_temp)

        # populate self.intial_table_rows dict with the tool number as keys and tool diameters as values
        for i in range(len(self.sorted_apid)):
            tt_aperture = self.sorted_apid[i]
            self.tool2tooldia[i + 1] = tt_aperture

    def build_ui(self):

        try:
            # if connected, disconnect the signal from the slot on item_changed as it creates issues
            self.apertures_table.itemChanged.disconnect()
        except:
            pass

        try:
            self.apertures_table.cellPressed.disconnect()
        except:
            pass

        # updated units
        self.units = self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().upper()

        # make a new name for the new Excellon object (the one with edited content)
        self.edited_obj_name = self.gerber_obj.options['name']
        self.name_entry.set_value(self.edited_obj_name)

        if self.units == "IN":
            self.apsize_entry.set_value(0.039)
        else:
            self.apsize_entry.set_value(1.00)

        self.apertures_row = 0
        aper_no = self.apertures_row + 1

        sort = []
        for k, v in list(self.storage_dict.items()):
            sort.append(int(k))

        sorted_apertures = sorted(sort)

        sort = []
        for k, v in list(self.gerber_obj.aperture_macros.items()):
            sort.append(k)
        sorted_macros = sorted(sort)

        n = len(sorted_apertures) + len(sorted_macros)
        self.apertures_table.setRowCount(n)

        for ap_code in sorted_apertures:
            ap_code = str(ap_code)

            ap_id_item = QtWidgets.QTableWidgetItem('%d' % int(self.apertures_row + 1))
            ap_id_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.apertures_table.setItem(self.apertures_row, 0, ap_id_item)  # Tool name/id

            ap_code_item = QtWidgets.QTableWidgetItem(ap_code)
            ap_code_item.setFlags(QtCore.Qt.ItemIsEnabled)

            ap_type_item = QtWidgets.QTableWidgetItem(str(self.storage_dict[ap_code]['type']))
            ap_type_item.setFlags(QtCore.Qt.ItemIsEnabled)

            if str(self.storage_dict[ap_code]['type']) == 'R' or str(self.storage_dict[ap_code]['type']) == 'O':
                ap_dim_item = QtWidgets.QTableWidgetItem(
                    '%.4f, %.4f' % (self.storage_dict[ap_code]['width'] * self.gerber_obj.file_units_factor,
                                    self.storage_dict[ap_code]['height'] * self.gerber_obj.file_units_factor
                                    )
                )
                ap_dim_item.setFlags(QtCore.Qt.ItemIsEnabled)
            elif str(self.storage_dict[ap_code]['type']) == 'P':
                ap_dim_item = QtWidgets.QTableWidgetItem(
                    '%.4f, %.4f' % (self.storage_dict[ap_code]['diam'] * self.gerber_obj.file_units_factor,
                                    self.storage_dict[ap_code]['nVertices'] * self.gerber_obj.file_units_factor)
                )
                ap_dim_item.setFlags(QtCore.Qt.ItemIsEnabled)
            else:
                ap_dim_item = QtWidgets.QTableWidgetItem('')
                ap_dim_item.setFlags(QtCore.Qt.ItemIsEnabled)

            try:
                if self.storage_dict[ap_code]['size'] is not None:
                    ap_size_item = QtWidgets.QTableWidgetItem('%.4f' %
                                                              float(self.storage_dict[ap_code]['size'] *
                                                                    self.gerber_obj.file_units_factor))
                else:
                    ap_size_item = QtWidgets.QTableWidgetItem('')
            except KeyError:
                ap_size_item = QtWidgets.QTableWidgetItem('')
            ap_size_item.setFlags(QtCore.Qt.ItemIsEnabled)

            self.apertures_table.setItem(self.apertures_row, 1, ap_code_item)  # Aperture Code
            self.apertures_table.setItem(self.apertures_row, 2, ap_type_item)  # Aperture Type
            self.apertures_table.setItem(self.apertures_row, 3, ap_size_item)  # Aperture Dimensions
            self.apertures_table.setItem(self.apertures_row, 4, ap_dim_item)  # Aperture Dimensions

            self.apertures_row += 1

        for ap_code in sorted_macros:
            ap_code = str(ap_code)

            ap_id_item = QtWidgets.QTableWidgetItem('%d' % int(self.apertures_row + 1))
            ap_id_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.apertures_table.setItem(self.apertures_row, 0, ap_id_item)  # Tool name/id

            ap_code_item = QtWidgets.QTableWidgetItem(ap_code)

            ap_type_item = QtWidgets.QTableWidgetItem('AM')
            ap_type_item.setFlags(QtCore.Qt.ItemIsEnabled)

            self.apertures_table.setItem(self.apertures_row, 1, ap_code_item)  # Aperture Code
            self.apertures_table.setItem(self.apertures_row, 2, ap_type_item)  # Aperture Type

            self.apertures_row += 1

        self.apertures_table.selectColumn(0)
        self.apertures_table.resizeColumnsToContents()
        self.apertures_table.resizeRowsToContents()

        vertical_header = self.apertures_table.verticalHeader()
        # vertical_header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        vertical_header.hide()
        self.apertures_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        horizontal_header = self.apertures_table.horizontalHeader()
        horizontal_header.setMinimumSectionSize(10)
        horizontal_header.setDefaultSectionSize(70)
        horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(0, 20)
        horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(4, QtWidgets.QHeaderView.Stretch)

        self.apertures_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.apertures_table.setSortingEnabled(False)
        self.apertures_table.setMinimumHeight(self.apertures_table.getHeight())
        self.apertures_table.setMaximumHeight(self.apertures_table.getHeight())

        # make sure no rows are selected so the user have to click the correct row, meaning selecting the correct tool
        self.apertures_table.clearSelection()

        # Remove anything else in the GUI Selected Tab
        self.app.ui.selected_scroll_area.takeWidget()
        # Put ourself in the GUI Selected Tab
        self.app.ui.selected_scroll_area.setWidget(self.grb_edit_widget)
        # Switch notebook to Selected page
        self.app.ui.notebook.setCurrentWidget(self.app.ui.selected_tab)

        # we reactivate the signals after the after the tool adding as we don't need to see the tool been populated
        self.apertures_table.itemChanged.connect(self.on_tool_edit)
        self.apertures_table.cellPressed.connect(self.on_row_selected)

    def on_aperture_add(self, apid=None):
        self.is_modified = True
        if apid:
            ap_id = apid
        else:
            try:
                ap_id = str(self.apcode_entry.get_value())
            except ValueError:
                self.app.inform.emit(_("[WARNING_NOTCL] Aperture code value is missing or wrong format. "
                                       "Add it and retry."))
                return

        if ap_id not in self.olddia_newdia:
            self.storage_dict[ap_id] = {}

            type_val = self.aptype_cb.currentText()
            self.storage_dict[ap_id]['type'] = type_val
            try:
                size_val = float(self.apsize_entry.get_value())
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    size_val = float(self.apsize_entry.get_value().replace(',', '.'))
                    self.apsize_entry.set_value(size_val)
                except ValueError:
                    self.app.inform.emit(_("[WARNING_NOTCL] Aperture size value is missing or wrong format. "
                                           "Add it and retry."))
                    return
            self.storage_dict[ap_id]['size'] = size_val

            if type_val == 'R':
                try:
                    dims = self.apdim_entry.get_value()
                    self.storage_dict[ap_id]['width'] = dims[0]
                    self.storage_dict[ap_id]['height'] = dims[1]
                except Exception as e:
                    log.error("FlatCAMGrbEditor.on_aperture_add() --> the R aperture dims has to be in a "
                              "tuple format (x,y)\nError: %s" % str(e))
                    self.app.inform.emit(_("[WARNING_NOTCL] Aperture dimensions value is missing or wrong format. "
                                           "Add it in format (width, height) and retry."))
                    return

            self.storage_dict[ap_id]['solid_geometry'] = []
            self.storage_dict[ap_id]['follow_geometry'] = []

            # self.olddia_newdia dict keeps the evidence on current tools diameters as keys and gets updated on values
            # each time a tool diameter is edited or added
            self.olddia_newdia[ap_id] = ap_id
        else:
            self.app.inform.emit(_("[WARNING_NOTCL] Aperture already in the aperture table."))
            return

        # since we add a new tool, we update also the initial state of the tool_table through it's dictionary
        # we add a new entry in the tool2tooldia dict
        self.tool2tooldia[len(self.olddia_newdia)] = ap_id

        self.app.inform.emit(_("[success] Added new aperture with dia: {apid}").format(apid=str(ap_id)))

        self.build_ui()

        # make a quick sort through the tool2tooldia dict so we find which row to select
        row_to_be_selected = None
        for key in sorted(self.tool2tooldia):
            if self.tool2tooldia[key] == ap_id:
                row_to_be_selected = int(key) - 1
                break

        self.apertures_table.selectRow(row_to_be_selected)

    def on_aperture_delete(self, apid=None):
        self.is_modified = True
        deleted_tool_dia_list = []
        deleted_tool_offset_list = []

        try:
            if apid is None or apid is False:
                # deleted_tool_dia = float(self.apertures_table.item(self.apertures_table.currentRow(), 1).text())
                for index in self.apertures_table.selectionModel().selectedRows():
                    row = index.row()
                    deleted_tool_dia_list.append(self.apertures_table.item(row, 1).text())
            else:
                if isinstance(apid, list):
                    for dd in apid:
                        deleted_tool_dia_list.append(dd)
                else:
                    deleted_tool_dia_list.append(apid)
        except:
            self.app.inform.emit(_("[WARNING_NOTCL] Select a tool in Tool Table"))
            return

        for deleted_tool_dia in deleted_tool_dia_list:
            # delete the storage used for that tool
            self.storage_dict.pop(deleted_tool_dia, None)

            # I've added this flag_del variable because dictionary don't like
            # having keys deleted while iterating through them
            flag_del = []
            for deleted_tool in self.tool2tooldia:
                if self.tool2tooldia[deleted_tool] == deleted_tool_dia:
                    flag_del.append(deleted_tool)

            if flag_del:
                for tool_to_be_deleted in flag_del:
                    # delete the tool
                    self.tool2tooldia.pop(tool_to_be_deleted, None)
                flag_del = []

            self.olddia_newdia.pop(deleted_tool_dia, None)

            self.app.inform.emit(_("[success] Deleted aperture with code: {del_dia}").format(del_dia=str(deleted_tool_dia)))

        self.plot_all()
        self.build_ui()

    def on_tool_edit(self, item_changed):

        # if connected, disconnect the signal from the slot on item_changed as it creates issues
        self.apertures_table.itemChanged.disconnect()
        # self.apertures_table.cellPressed.disconnect()

        self.is_modified = True
        geometry = []
        current_table_dia_edited = None

        if self.apertures_table.currentItem() is not None:
            try:
                current_table_dia_edited = float(self.apertures_table.currentItem().text())
            except ValueError as e:
                log.debug("FlatCAMExcEditor.on_tool_edit() --> %s" % str(e))
                self.apertures_table.setCurrentItem(None)
                return

        row_of_item_changed = self.apertures_table.currentRow()

        # rows start with 0, tools start with 1 so we adjust the value by 1
        key_in_tool2tooldia = row_of_item_changed + 1

        dia_changed = self.tool2tooldia[key_in_tool2tooldia]

        # tool diameter is not used so we create a new tool with the desired diameter
        if current_table_dia_edited not in self.olddia_newdia.values():
            # update the dict that holds as keys our initial diameters and as values the edited diameters
            self.olddia_newdia[dia_changed] = current_table_dia_edited
            # update the dict that holds tool_no as key and tool_dia as value
            self.tool2tooldia[key_in_tool2tooldia] = current_table_dia_edited

            # update the tool offset
            modified_offset = self.gerber_obj.tool_offset.pop(dia_changed)
            self.gerber_obj.tool_offset[current_table_dia_edited] = modified_offset

            self.plot_all()
        else:
            # tool diameter is already in use so we move the drills from the prior tool to the new tool
            factor = current_table_dia_edited / dia_changed
            for shape in self.storage_dict[dia_changed].get_objects():
                geometry.append(DrawToolShape(
                    MultiLineString([affinity.scale(subgeo, xfact=factor, yfact=factor) for subgeo in shape.geo])))

                self.points_edit[current_table_dia_edited].append((0, 0))
            self.add_gerber_shape(geometry, self.storage_dict[current_table_dia_edited])

            self.on_aperture_delete(apid=dia_changed)

            # delete the tool offset
            self.gerber_obj.tool_offset.pop(dia_changed, None)

        # we reactivate the signals after the after the tool editing
        self.apertures_table.itemChanged.connect(self.on_tool_edit)
        # self.apertures_table.cellPressed.connect(self.on_row_selected)

    def on_name_activate(self):
        self.edited_obj_name = self.name_entry.get_value()

    def on_aptype_changed(self, current_text):
        if current_text == 'R':
            self.apdim_lbl.show()
            self.apdim_entry.show()
        else:
            self.apdim_lbl.hide()
            self.apdim_entry.hide()

    def activate(self):
        self.connect_canvas_event_handlers()

        # init working objects
        self.storage_dict = {}
        self.current_storage = []
        self.sorted_apid = []
        self.new_apertures = {}
        self.new_aperture_macros = {}
        self.grb_plot_promises = []
        self.olddia_newdia = {}
        self.tool2tooldia = {}

        self.shapes.enabled = True
        self.tool_shape.enabled = True

        self.app.ui.snap_max_dist_entry.setEnabled(True)
        self.app.ui.corner_snap_btn.setEnabled(True)
        self.app.ui.snap_magnet.setVisible(True)
        self.app.ui.corner_snap_btn.setVisible(True)

        self.app.ui.grb_editor_menu.setDisabled(False)
        self.app.ui.grb_editor_menu.menuAction().setVisible(True)

        self.app.ui.update_obj_btn.setEnabled(True)
        self.app.ui.grb_editor_cmenu.setEnabled(True)

        self.app.ui.grb_edit_toolbar.setDisabled(False)
        self.app.ui.grb_edit_toolbar.setVisible(True)
        # self.app.ui.snap_toolbar.setDisabled(False)

        # start with GRID toolbar activated
        if self.app.ui.grid_snap_btn.isChecked() is False:
            self.app.ui.grid_snap_btn.trigger()

        # Tell the App that the editor is active
        self.editor_active = True

    def deactivate(self):
        self.disconnect_canvas_event_handlers()
        self.clear()
        self.app.ui.grb_edit_toolbar.setDisabled(True)

        settings = QSettings("Open Source", "FlatCAM")
        if settings.contains("layout"):
            layout = settings.value('layout', type=str)
            if layout == 'standard':
                # self.app.ui.exc_edit_toolbar.setVisible(False)

                self.app.ui.snap_max_dist_entry.setEnabled(False)
                self.app.ui.corner_snap_btn.setEnabled(False)
                self.app.ui.snap_magnet.setVisible(False)
                self.app.ui.corner_snap_btn.setVisible(False)
            elif layout == 'compact':
                # self.app.ui.exc_edit_toolbar.setVisible(True)

                self.app.ui.snap_max_dist_entry.setEnabled(False)
                self.app.ui.corner_snap_btn.setEnabled(False)
                self.app.ui.snap_magnet.setVisible(True)
                self.app.ui.corner_snap_btn.setVisible(True)
        else:
            # self.app.ui.exc_edit_toolbar.setVisible(False)

            self.app.ui.snap_max_dist_entry.setEnabled(False)
            self.app.ui.corner_snap_btn.setEnabled(False)
            self.app.ui.snap_magnet.setVisible(False)
            self.app.ui.corner_snap_btn.setVisible(False)

        # set the Editor Toolbar visibility to what was before entering in the Editor
        self.app.ui.grb_edit_toolbar.setVisible(False) if self.toolbar_old_state is False \
            else self.app.ui.grb_edit_toolbar.setVisible(True)

        # Disable visuals
        self.shapes.enabled = False
        self.tool_shape.enabled = False
        # self.app.app_cursor.enabled = False

        # Tell the app that the editor is no longer active
        self.editor_active = False

        self.app.ui.grb_editor_menu.setDisabled(True)
        self.app.ui.grb_editor_menu.menuAction().setVisible(False)

        self.app.ui.update_obj_btn.setEnabled(False)

        self.app.ui.g_editor_cmenu.setEnabled(False)
        self.app.ui.grb_editor_cmenu.setEnabled(False)
        self.app.ui.e_editor_cmenu.setEnabled(False)

        # Show original geometry
        if self.gerber_obj:
            self.gerber_obj.visible = True

    def connect_canvas_event_handlers(self):
        ## Canvas events

        # make sure that the shortcuts key and mouse events will no longer be linked to the methods from FlatCAMApp
        # but those from FlatCAMGeoEditor

        self.app.plotcanvas.vis_disconnect('mouse_press', self.app.on_mouse_click_over_plot)
        self.app.plotcanvas.vis_disconnect('mouse_move', self.app.on_mouse_move_over_plot)
        self.app.plotcanvas.vis_disconnect('mouse_release', self.app.on_mouse_click_release_over_plot)
        self.app.plotcanvas.vis_disconnect('mouse_double_click', self.app.on_double_click_over_plot)
        self.app.collection.view.clicked.disconnect()

        self.canvas.vis_connect('mouse_press', self.on_canvas_click)
        self.canvas.vis_connect('mouse_move', self.on_canvas_move)
        self.canvas.vis_connect('mouse_release', self.on_canvas_click_release)

    def disconnect_canvas_event_handlers(self):
        self.canvas.vis_disconnect('mouse_press', self.on_canvas_click)
        self.canvas.vis_disconnect('mouse_move', self.on_canvas_move)
        self.canvas.vis_disconnect('mouse_release', self.on_canvas_click_release)

        # we restore the key and mouse control to FlatCAMApp method
        self.app.plotcanvas.vis_connect('mouse_press', self.app.on_mouse_click_over_plot)
        self.app.plotcanvas.vis_connect('mouse_move', self.app.on_mouse_move_over_plot)
        self.app.plotcanvas.vis_connect('mouse_release', self.app.on_mouse_click_release_over_plot)
        self.app.plotcanvas.vis_connect('mouse_double_click', self.app.on_double_click_over_plot)
        self.app.collection.view.clicked.connect(self.app.collection.on_mouse_down)

    def clear(self):
        self.active_tool = None
        # self.shape_buffer = []
        self.selected = []

        self.shapes.clear(update=True)
        self.tool_shape.clear(update=True)

    def edit_fcgerber(self, orig_grb_obj):
        """
        Imports the geometry found in self.apertures from the given FlatCAM Gerber object
        into the editor.

        :param fcgeometry: FlatCAMExcellon
        :return: None
        """

        self.deactivate()
        self.activate()

        # create a reference to the source object
        self.gerber_obj = orig_grb_obj

        self.gerber_obj_options = orig_grb_obj.options

        # Hide original geometry
        orig_grb_obj.visible = False

        # Set selection tolerance
        # DrawToolShape.tolerance = fc_excellon.drawing_tolerance * 10

        self.select_tool("select")

        # we activate this after the initial build as we don't need to see the tool been populated
        self.apertures_table.itemChanged.connect(self.on_tool_edit)

        # build the geometry for each tool-diameter, each drill will be represented by a '+' symbol
        # and then add it to the storage elements (each storage elements is a member of a list

        def job_thread(self, apid):
            with self.app.proc_container.new(_("Adding aperture: %s geo ...") % str(apid)):
                solid_storage_elem = []
                follow_storage_elem = []

                self.storage_dict[apid] = {}
                for k, v in self.gerber_obj.apertures[apid].items():
                    if k == 'solid_geometry':
                        for geo in v:
                            if geo is not None:
                                self.add_gerber_shape(DrawToolShape(geo), solid_storage_elem)
                        self.storage_dict[apid][k] = solid_storage_elem
                    elif k == 'follow_geometry':
                        for geo in v:
                            if geo is not None:
                                self.add_gerber_shape(DrawToolShape(geo), follow_storage_elem)
                        self.storage_dict[apid][k] = follow_storage_elem
                    else:
                        self.storage_dict[apid][k] = v

                # Check promises and clear if exists
                while True:
                    try:
                        self.grb_plot_promises.remove(apid)
                        time.sleep(0.5)
                    except ValueError:
                        break

        for apid in self.gerber_obj.apertures:
            self.grb_plot_promises.append(apid)
            self.app.worker_task.emit({'fcn': job_thread, 'params': [self, apid]})

        self.start_delayed_plot(check_period=1000)

    def update_fcgerber(self, grb_obj):
        """
        Create a new Gerber object that contain the edited content of the source Gerber object

        :param grb_obj: FlatCAMGerber
        :return: None
        """

        new_grb_name = self.edited_obj_name

        # if the 'delayed plot' malfunctioned stop the QTimer
        try:
            self.plot_thread.stop()
        except:
            pass

        if "_edit" in self.edited_obj_name:
            try:
                id = int(self.edited_obj_name[-1]) + 1
                new_grb_name= self.edited_obj_name[:-1] + str(id)
            except ValueError:
                new_grb_name += "_1"
        else:
            new_grb_name = self.edited_obj_name + "_edit"

        self.app.worker_task.emit({'fcn': self.new_edited_gerber,
                                   'params': [new_grb_name]})

        # reset the tool table
        self.apertures_table.clear()

        self.apertures_table.setHorizontalHeaderLabels(['#', _('Code'), _('Type'), _('Size'), _('Dim')])
        self.last_aperture_selected = None

        # restore GUI to the Selected TAB
        # Remove anything else in the GUI
        self.app.ui.selected_scroll_area.takeWidget()
        # Switch notebook to Selected page
        self.app.ui.notebook.setCurrentWidget(self.app.ui.selected_tab)

    def update_options(self, obj):
        try:
            if not obj.options:
                obj.options = {}
                obj.options['xmin'] = 0
                obj.options['ymin'] = 0
                obj.options['xmax'] = 0
                obj.options['ymax'] = 0
                return True
            else:
                return False
        except AttributeError:
            obj.options = {}
            return True

    def new_edited_gerber(self, outname):
        """
        Creates a new Gerber object for the edited Gerber. Thread-safe.

        :param outname: Name of the resulting object. None causes the name to be that of the file.
        :type outname: str
        :return: None
        """

        self.app.log.debug("Update the Gerber object with edited content. Source is: %s" %
                           self.gerber_obj.options['name'].upper())

        out_name = outname
        local_storage_dict = deepcopy(self.storage_dict)

        # How the object should be initialized
        def obj_init(grb_obj, app_obj):

            poly_buffer = []
            follow_buffer = []

            for storage_apid, storage_val in local_storage_dict.items():
                grb_obj.apertures[storage_apid] = {}

                for k, v in storage_val.items():
                    if k == 'solid_geometry':
                        grb_obj.apertures[storage_apid][k] = []
                        for geo in v:
                            new_geo = deepcopy(geo.geo)
                            grb_obj.apertures[storage_apid][k].append(new_geo)
                            poly_buffer.append(new_geo)

                    elif k == 'follow_geometry':
                        grb_obj.apertures[storage_apid][k] = []
                        for geo in v:
                            new_geo = deepcopy(geo.geo)
                            grb_obj.apertures[storage_apid][k].append(new_geo)
                            follow_buffer.append(new_geo)
                    else:
                        grb_obj.apertures[storage_apid][k] = deepcopy(v)

            grb_obj.aperture_macros = deepcopy(self.gerber_obj.aperture_macros)

            new_poly = MultiPolygon(poly_buffer)
            new_poly = new_poly.buffer(0.00000001)
            new_poly = new_poly.buffer(-0.00000001)
            grb_obj.solid_geometry = new_poly

            grb_obj.follow_geometry = deepcopy(follow_buffer)

            for k, v in self.gerber_obj_options.items():
                if k == 'name':
                    grb_obj.options[k] = out_name
                else:
                    grb_obj.options[k] = deepcopy(v)

            grb_obj.source_file = []
            grb_obj.multigeo = False
            grb_obj.follow = False

            try:
                grb_obj.create_geometry()
            except KeyError:
                self.app.inform.emit(
                   _( "[ERROR_NOTCL] There are no Aperture definitions in the file. Aborting Gerber creation.")
                )
            except:
                msg = _("[ERROR] An internal error has ocurred. See shell.\n")
                msg += traceback.format_exc()
                app_obj.inform.emit(msg)
                raise
                # raise

        with self.app.proc_container.new(_("Creating Gerber.")):
            try:
                self.app.new_object("gerber", outname, obj_init)
            except Exception as e:
                log.error("Error on object creation: %s" % str(e))
                self.app.progress.emit(100)
                return

            self.app.inform.emit(_("[success] Gerber editing finished."))
            # self.progress.emit(100)

    def on_tool_select(self, tool):
        """
        Behavior of the toolbar. Tool initialization.

        :rtype : None
        """
        current_tool = tool

        self.app.log.debug("on_tool_select('%s')" % tool)

        if self.last_aperture_selected is None and current_tool is not 'select':
            # self.draw_app.select_tool('select')
            self.complete = True
            current_tool = 'select'
            self.app.inform.emit(_("[WARNING_NOTCL] Cancelled. No aperture is selected"))

        # This is to make the group behave as radio group
        if current_tool in self.tools_gerber:
            if self.tools_gerber[current_tool]["button"].isChecked():
                self.app.log.debug("%s is checked." % current_tool)
                for t in self.tools_gerber:
                    if t != current_tool:
                        self.tools_gerber[t]["button"].setChecked(False)

                # this is where the Editor toolbar classes (button's) are instantiated
                self.active_tool = self.tools_gerber[current_tool]["constructor"](self)
                # self.app.inform.emit(self.active_tool.start_msg)
            else:
                self.app.log.debug("%s is NOT checked." % current_tool)
                for t in self.tools_gerber:
                    self.tools_gerber[t]["button"].setChecked(False)
                self.active_tool = None

    def on_row_selected(self, row, col):
        if col == 0:
            key_modifier = QtWidgets.QApplication.keyboardModifiers()
            if self.app.defaults["global_mselect_key"] == 'Control':
                modifier_to_use = Qt.ControlModifier
            else:
                modifier_to_use = Qt.ShiftModifier

            if key_modifier == modifier_to_use:
                pass
            else:
                self.selected = []

            try:
                selected_apid = str(self.tool2tooldia[row + 1])
                self.last_aperture_selected = row + 1

                for obj in self.storage_dict[selected_apid]['solid_geometry']:
                    self.selected.append(obj)
            except Exception as e:
                self.app.log.debug(str(e))

            self.plot_all()

    def toolbar_tool_toggle(self, key):
        self.options[key] = self.sender().isChecked()
        return self.options[key]

    def on_grb_shape_complete(self, storage):
        self.app.log.debug("on_shape_complete()")

        # Add shape
        self.add_gerber_shape(self.active_tool.geometry, storage)

        # Remove any utility shapes
        self.delete_utility_geometry()
        self.tool_shape.clear(update=True)

        # Replot and reset tool.
        self.plot_all()

    def add_gerber_shape(self, shape, storage):
        """
        Adds a shape to the shape storage.

        :param shape: Shape to be added.
        :type shape: DrawToolShape
        :return: None
        """
        # List of DrawToolShape?
        if isinstance(shape, list):
            for subshape in shape:
                self.add_gerber_shape(subshape, storage)
            return

        assert isinstance(shape, DrawToolShape), \
            "Expected a DrawToolShape, got %s" % str(type(shape))

        assert shape.geo is not None, \
            "Shape object has empty geometry (None)"

        assert (isinstance(shape.geo, list) and len(shape.geo) > 0) or \
               not isinstance(shape.geo, list), \
            "Shape objects has empty geometry ([])"

        if isinstance(shape, DrawToolUtilityShape):
            self.utility.append(shape)
        else:
            storage.append(shape)  # TODO: Check performance

    def on_canvas_click(self, event):
        """
        event.x and .y have canvas coordinates
        event.xdaya and .ydata have plot coordinates

        :param event: Event object dispatched by Matplotlib
        :return: None
        """

        if event.button is 1:
            self.app.ui.rel_position_label.setText("<b>Dx</b>: %.4f&nbsp;&nbsp;  <b>Dy</b>: "
                                                   "%.4f&nbsp;&nbsp;&nbsp;&nbsp;" % (0, 0))
            self.pos = self.canvas.vispy_canvas.translate_coords(event.pos)

            ### Snap coordinates
            x, y = self.app.geo_editor.snap(self.pos[0], self.pos[1])

            self.pos = (x, y)

            # Selection with left mouse button
            if self.active_tool is not None and event.button is 1:
                # Dispatch event to active_tool
                # msg = self.active_tool.click(self.app.geo_editor.snap(event.xdata, event.ydata))
                msg = self.active_tool.click(self.app.geo_editor.snap(self.pos[0], self.pos[1]))

                # If it is a shape generating tool
                if isinstance(self.active_tool, FCShapeTool) and self.active_tool.complete:
                    if self.current_storage is not None:
                        self.on_grb_shape_complete(self.current_storage)
                        self.build_ui()
                    # MS: always return to the Select Tool if modifier key is not pressed
                    # else return to the current tool
                    key_modifier = QtWidgets.QApplication.keyboardModifiers()
                    if self.app.defaults["global_mselect_key"] == 'Control':
                        modifier_to_use = Qt.ControlModifier
                    else:
                        modifier_to_use = Qt.ShiftModifier
                    # if modifier key is pressed then we add to the selected list the current shape but if it's already
                    # in the selected list, we removed it. Therefore first click selects, second deselects.
                    if key_modifier == modifier_to_use:
                        self.select_tool(self.active_tool.name)
                    else:
                        self.select_tool("select")
                        return

                if isinstance(self.active_tool, FCApertureSelect):
                    # self.app.log.debug("Replotting after click.")
                    self.plot_all()
            else:
                self.app.log.debug("No active tool to respond to click!")

    def on_canvas_click_release(self, event):
        pos_canvas = self.canvas.vispy_canvas.translate_coords(event.pos)

        self.modifiers = QtWidgets.QApplication.keyboardModifiers()

        if self.app.grid_status():
            pos = self.app.geo_editor.snap(pos_canvas[0], pos_canvas[1])
        else:
            pos = (pos_canvas[0], pos_canvas[1])

        # if the released mouse button was RMB then test if it was a panning motion or not, if not it was a context
        # canvas menu
        try:
            if event.button == 2:  # right click
                if self.app.panning_action is True:
                    self.app.panning_action = False
                else:
                    self.app.cursor = QtGui.QCursor()
                    self.app.ui.popMenu.popup(self.app.cursor.pos())
        except Exception as e:
            log.warning("Error: %s" % str(e))
            raise

        # if the released mouse button was LMB then test if we had a right-to-left selection or a left-to-right
        # selection and then select a type of selection ("enclosing" or "touching")
        try:
            if event.button == 1:  # left click
                if self.app.selection_type is not None:
                    self.draw_selection_area_handler(self.pos, pos, self.app.selection_type)
                    self.app.selection_type = None

                elif isinstance(self.active_tool, FCApertureSelect):
                    # Dispatch event to active_tool
                    # msg = self.active_tool.click(self.app.geo_editor.snap(event.xdata, event.ydata))
                    # msg = self.active_tool.click_release((self.pos[0], self.pos[1]))
                    # self.app.inform.emit(msg)
                    self.active_tool.click_release((self.pos[0], self.pos[1]))

                    # if there are selected objects then plot them
                    if self.selected:
                        self.plot_all()
        except Exception as e:
            log.warning("Error: %s" % str(e))
            raise

    def draw_selection_area_handler(self, start_pos, end_pos, sel_type):
        """
        :param start_pos: mouse position when the selection LMB click was done
        :param end_pos: mouse position when the left mouse button is released
        :param sel_type: if True it's a left to right selection (enclosure), if False it's a 'touch' selection
        :type Bool
        :return:
        """
        poly_selection = Polygon([start_pos, (end_pos[0], start_pos[1]), end_pos, (start_pos[0], end_pos[1])])

        sel_aperture = set()
        self.apertures_table.clearSelection()

        self.app.delete_selection_shape()
        for storage in self.storage_dict:
            for obj in self.storage_dict[storage]['solid_geometry']:
                if (sel_type is True and poly_selection.contains(obj.geo)) or \
                        (sel_type is False and poly_selection.intersects(obj.geo)):
                    if self.key == self.app.defaults["global_mselect_key"]:
                        if obj in self.selected:
                            self.selected.remove(obj)
                        else:
                            # add the object to the selected shapes
                            self.selected.append(obj)
                            sel_aperture.add(storage)
                    else:
                        self.selected.append(obj)
                        sel_aperture.add(storage)

        try:
            self.apertures_table.cellPressed.disconnect()
        except:
            pass

        self.apertures_table.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        for aper in sel_aperture:
            for row in range(self.apertures_table.rowCount()):
                if str(aper) == self.apertures_table.item(row, 1).text():
                    self.apertures_table.selectRow(row)
                    self.last_aperture_selected = aper
        self.apertures_table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        self.apertures_table.cellPressed.connect(self.on_row_selected)
        self.plot_all()

    def on_canvas_move(self, event):
        """
        Called on 'mouse_move' event

        event.pos have canvas screen coordinates

        :param event: Event object dispatched by VisPy SceneCavas
        :return: None
        """

        pos = self.canvas.vispy_canvas.translate_coords(event.pos)
        event.xdata, event.ydata = pos[0], pos[1]

        self.x = event.xdata
        self.y = event.ydata

        # Prevent updates on pan
        # if len(event.buttons) > 0:
        #     return

        # if the RMB is clicked and mouse is moving over plot then 'panning_action' is True
        if event.button == 2:
            self.app.panning_action = True
            return
        else:
            self.app.panning_action = False

        try:
            x = float(event.xdata)
            y = float(event.ydata)
        except TypeError:
            return

        if self.active_tool is None:
            return

        ### Snap coordinates
        x, y = self.app.geo_editor.app.geo_editor.snap(x, y)

        self.snap_x = x
        self.snap_y = y

        # update the position label in the infobar since the APP mouse event handlers are disconnected
        self.app.ui.position_label.setText("&nbsp;&nbsp;&nbsp;&nbsp;<b>X</b>: %.4f&nbsp;&nbsp;   "
                                       "<b>Y</b>: %.4f" % (x, y))

        if self.pos is None:
            self.pos = (0, 0)
        dx = x - self.pos[0]
        dy = y - self.pos[1]

        # update the reference position label in the infobar since the APP mouse event handlers are disconnected
        self.app.ui.rel_position_label.setText("<b>Dx</b>: %.4f&nbsp;&nbsp;  <b>Dy</b>: "
                                           "%.4f&nbsp;&nbsp;&nbsp;&nbsp;" % (dx, dy))

        ### Utility geometry (animated)
        geo = self.active_tool.utility_geometry(data=(x, y))

        if isinstance(geo, DrawToolShape) and geo.geo is not None:

            # Remove any previous utility shape
            self.tool_shape.clear(update=True)
            self.draw_utility_geometry(geo=geo)

        ### Selection area on canvas section ###
        dx = pos[0] - self.pos[0]
        if event.is_dragging == 1 and event.button == 1:
            self.app.delete_selection_shape()
            if dx < 0:
                self.app.draw_moving_selection_shape((self.pos[0], self.pos[1]), (x,y),
                     color=self.app.defaults["global_alt_sel_line"],
                     face_color=self.app.defaults['global_alt_sel_fill'])
                self.app.selection_type = False
            else:
                self.app.draw_moving_selection_shape((self.pos[0], self.pos[1]), (x,y))
                self.app.selection_type = True
        else:
            self.app.selection_type = None

        # Update cursor
        self.app.app_cursor.set_data(np.asarray([(x, y)]), symbol='++', edge_color='black', size=20)

    def on_canvas_key_release(self, event):
        self.key = None

    def draw_utility_geometry(self, geo):
        if type(geo.geo) == list:
            for el in geo.geo:
                # Add the new utility shape
                self.tool_shape.add(
                    shape=el, color=(self.app.defaults["global_draw_color"] + '80'),
                    update=False, layer=0, tolerance=None)
        else:
            # Add the new utility shape
            self.tool_shape.add(
                shape=geo.geo, color=(self.app.defaults["global_draw_color"] + '80'),
                update=False, layer=0, tolerance=None)

        self.tool_shape.redraw()

    def plot_all(self):
        """
        Plots all shapes in the editor.

        :return: None
        :rtype: None
        """
        with self.app.proc_container.new("Plotting"):
            # self.app.log.debug("plot_all()")
            self.shapes.clear(update=True)

            for storage in self.storage_dict:
                for shape in self.storage_dict[storage]['solid_geometry']:
                    if shape.geo is None:
                        continue

                    if shape in self.selected:
                        self.plot_shape(geometry=shape.geo, color=self.app.defaults['global_sel_draw_color'],
                                        linewidth=2)
                        continue
                    self.plot_shape(geometry=shape.geo, color=self.app.defaults['global_draw_color'])

            for shape in self.utility:
                self.plot_shape(geometry=shape.geo, linewidth=1)
                continue

            self.shapes.redraw()

    def plot_shape(self, geometry=None, color='black', linewidth=1):
        """
        Plots a geometric object or list of objects without rendering. Plotted objects
        are returned as a list. This allows for efficient/animated rendering.

        :param geometry: Geometry to be plotted (Any Shapely.geom kind or list of such)
        :param color: Shape color
        :param linewidth: Width of lines in # of pixels.
        :return: List of plotted elements.
        """
        # plot_elements = []

        if geometry is None:
            geometry = self.active_tool.geometry

        try:
            self.shapes.add(shape=geometry.geo, color=color, face_color=color, layer=0)
        except AttributeError:
            if type(geometry) == Point:
                return
            self.shapes.add(shape=geometry, color=color, face_color=color+'AF', layer=0)

    def start_delayed_plot(self, check_period):
        # self.plot_thread = threading.Thread(target=lambda: self.check_plot_finished(check_period))
        # self.plot_thread.start()
        log.debug("FlatCAMGrbEditor --> Delayed Plot started.")
        self.plot_thread = QtCore.QTimer()
        self.plot_thread.setInterval(check_period)
        self.plot_thread.timeout.connect(self.check_plot_finished)
        self.plot_thread.start()

    def check_plot_finished(self):
        # print(self.grb_plot_promises)
        try:
            if not self.grb_plot_promises:
                self.plot_thread.stop()

                self.set_ui()
                # now that we hava data, create the GUI interface and add it to the Tool Tab
                self.build_ui()

                self.plot_all()
                log.debug("FlatCAMGrbEditor --> delayed_plot finished")
        except Exception:
            traceback.print_exc()

    def on_shape_complete(self):
        self.app.log.debug("on_shape_complete()")

        # Add shape
        self.add_shape(self.active_tool.geometry)

        # Remove any utility shapes
        self.delete_utility_geometry()
        self.tool_shape.clear(update=True)

        # Replot and reset tool.
        self.plot_all()
        # self.active_tool = type(self.active_tool)(self)

    def get_selected(self):
        """
        Returns list of shapes that are selected in the editor.

        :return: List of shapes.
        """
        # return [shape for shape in self.shape_buffer if shape["selected"]]
        return self.selected

    def delete_selected(self):
        temp_ref = [s for s in self.selected]
        for shape_sel in temp_ref:
            self.delete_shape(shape_sel)

        self.selected = []
        self.build_ui()
        self.app.inform.emit(_("[success] Done. Apertures deleted."))

    def delete_shape(self, shape):
        self.is_modified = True

        if shape in self.utility:
            self.utility.remove(shape)
            return

        for storage in self.storage_dict:
            # try:
            #     self.storage_dict[storage].remove(shape)
            # except:
            #     pass
            if shape in self.storage_dict[storage]['solid_geometry']:
                self.storage_dict[storage]['solid_geometry'].remove(shape)

        if shape in self.selected:
            self.selected.remove(shape)  # TODO: Check performance

    def delete_utility_geometry(self):
        # for_deletion = [shape for shape in self.shape_buffer if shape.utility]
        # for_deletion = [shape for shape in self.storage.get_objects() if shape.utility]
        for_deletion = [shape for shape in self.utility]
        for shape in for_deletion:
            self.delete_shape(shape)

        self.tool_shape.clear(update=True)
        self.tool_shape.redraw()

    def on_delete_btn(self):
        self.delete_selected()
        self.plot_all()

    def select_tool(self, toolname):
        """
        Selects a drawing tool. Impacts the object and GUI.

        :param toolname: Name of the tool.
        :return: None
        """
        self.tools_gerber[toolname]["button"].setChecked(True)
        self.on_tool_select(toolname)

    def set_selected(self, shape):

        # Remove and add to the end.
        if shape in self.selected:
            self.selected.remove(shape)

        self.selected.append(shape)

    def set_unselected(self, shape):
        if shape in self.selected:
            self.selected.remove(shape)

    def on_copy_button(self):
        self.select_tool('copy')
        return

    def on_move_button(self):
        self.select_tool('move')
        return

    def on_buffer(self):
        buff_value = 0.01
        log.debug("FlatCAMGrbEditor.on_buffer()")

        try:
            buff_value = float(self.buffer_distance_entry.get_value())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                buff_value = float(self.buffer_distance_entry.get_value().replace(',', '.'))
                self.buffer_distance_entry.set_value(buff_value)
            except ValueError:
                self.app.inform.emit(_("[WARNING_NOTCL] Buffer distance value is missing or wrong format. "
                                     "Add it and retry."))
                return
        # the cb index start from 0 but the join styles for the buffer start from 1 therefore the adjustment
        # I populated the combobox such that the index coincide with the join styles value (whcih is really an INT)
        join_style = self.buffer_corner_cb.currentIndex() + 1

        def buffer_recursion(geom, selection):
            if type(geom) == list or type(geom) is MultiPolygon:
                geoms = list()
                for local_geom in geom:
                    geoms.append(buffer_recursion(local_geom, selection=selection))
                return geoms
            else:
                if geom in selection:
                    return DrawToolShape(geom.geo.buffer(buff_value, join_style=join_style))
                else:
                    return geom

        if not self.apertures_table.selectedItems():
            self.app.inform.emit(_(
                "[WARNING_NOTCL] No aperture to buffer. Select at least one aperture and try again."
            ))
            return

        for x in self.apertures_table.selectedItems():
            try:
                apid = self.apertures_table.item(x.row(), 1).text()

                temp_storage = deepcopy(buffer_recursion(self.storage_dict[apid]['solid_geometry'], self.selected))
                self.storage_dict[apid]['solid_geometry'] = []
                self.storage_dict[apid]['solid_geometry'] = temp_storage

            except Exception as e:
                log.debug("FlatCAMGrbEditor.buffer() --> %s" % str(e))
        self.plot_all()
        self.app.inform.emit(_("[success] Done. Buffer Tool completed."))

    def on_scale(self):
        scale_factor = 1.0
        log.debug("FlatCAMGrbEditor.on_scale()")

        try:
            scale_factor = float(self.scale_factor_entry.get_value())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                scale_factor = float(self.scale_factor_entry.get_value().replace(',', '.'))
                self.scale_factor_entry.set_value(scale_factor)
            except ValueError:
                self.app.inform.emit(_("[WARNING_NOTCL] Scale factor value is missing or wrong format. "
                                     "Add it and retry."))
                return

        def scale_recursion(geom, selection):
            if type(geom) == list or type(geom) is MultiPolygon:
                geoms = list()
                for local_geom in geom:
                    geoms.append(scale_recursion(local_geom, selection=selection))
                return geoms
            else:
                if geom in selection:
                    return DrawToolShape(affinity.scale(geom.geo, scale_factor, scale_factor, origin='center'))
                else:
                    return geom

        if not self.apertures_table.selectedItems():
            self.app.inform.emit(_(
                "[WARNING_NOTCL] No aperture to scale. Select at least one aperture and try again."
            ))
            return

        for x in self.apertures_table.selectedItems():
            try:
                apid = self.apertures_table.item(x.row(), 1).text()

                temp_storage = deepcopy(scale_recursion(self.storage_dict[apid]['solid_geometry'], self.selected))
                self.storage_dict[apid]['solid_geometry'] = []
                self.storage_dict[apid]['solid_geometry'] = temp_storage

            except Exception as e:
                log.debug("FlatCAMGrbEditor.on_scale() --> %s" % str(e))

        self.plot_all()
        self.app.inform.emit(_("[success] Done. Scale Tool completed."))

    def hide_tool(self, tool_name):
        # self.app.ui.notebook.setTabText(2, _("Tools"))

        if tool_name == 'all':
            self.apertures_frame.hide()
        if tool_name == 'select':
            self.apertures_frame.show()
        if tool_name == 'buffer' or tool_name == 'all':
            self.buffer_tool_frame.hide()
        if tool_name == 'scale' or tool_name == 'all':
            self.scale_tool_frame.hide()

        self.app.ui.notebook.setCurrentWidget(self.app.ui.selected_tab)