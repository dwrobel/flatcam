# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 11/21/2019                                         #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtCore

from FlatCAMTool import FlatCAMTool
from flatcamGUI.GUIElements import FCDoubleSpinner, RadioSet, EvalEntry, FCTable, FCComboBox

from shapely.geometry import Point, Polygon, MultiPolygon, LineString
from shapely.geometry import box as box

import math
import logging
from copy import deepcopy

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class ToolFiducials(FlatCAMTool):

    toolName = _("Fiducials Tool")

    def __init__(self, app):
        FlatCAMTool.__init__(self, app)

        self.app = app
        self.canvas = self.app.plotcanvas

        self.decimals = self.app.decimals
        self.units = ''

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
        self.layout.addWidget(QtWidgets.QLabel(''))

        self.points_label = QtWidgets.QLabel('<b>%s:</b>' % _('Fiducials Coordinates'))
        self.points_label.setToolTip(
            _("A table with the fiducial points coordinates,\n"
              "in the format (x, y).")
        )
        self.layout.addWidget(self.points_label)

        self.points_table = FCTable()
        self.points_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        self.layout.addWidget(self.points_table)
        self.layout.addWidget(QtWidgets.QLabel(''))

        self.points_table.setColumnCount(3)
        self.points_table.setHorizontalHeaderLabels(
            [
                '#',
                _("Name"),
                _("Coordinates"),
            ]
        )
        self.points_table.setRowCount(3)
        row = 0

        flags = QtCore.Qt.ItemIsEnabled

        # BOTTOM LEFT
        id_item_1 = QtWidgets.QTableWidgetItem('%d' % 1)
        id_item_1.setFlags(flags)
        self.points_table.setItem(row, 0, id_item_1)  # Tool name/id

        self.bottom_left_coords_lbl = QtWidgets.QTableWidgetItem('%s' % _('Bottom Left'))
        self.bottom_left_coords_lbl.setFlags(flags)
        self.points_table.setItem(row, 1, self.bottom_left_coords_lbl)
        self.bottom_left_coords_entry = EvalEntry()
        self.points_table.setCellWidget(row, 2, self.bottom_left_coords_entry)
        row += 1

        # TOP RIGHT
        id_item_2 = QtWidgets.QTableWidgetItem('%d' % 2)
        id_item_2.setFlags(flags)
        self.points_table.setItem(row, 0, id_item_2)  # Tool name/id

        self.top_right_coords_lbl = QtWidgets.QTableWidgetItem('%s' % _('Top Right'))
        self.top_right_coords_lbl.setFlags(flags)
        self.points_table.setItem(row, 1, self.top_right_coords_lbl)
        self.top_right_coords_entry = EvalEntry()
        self.points_table.setCellWidget(row, 2, self.top_right_coords_entry)
        row += 1

        # Second Point
        self.id_item_3 = QtWidgets.QTableWidgetItem('%d' % 3)
        self.id_item_3.setFlags(flags)
        self.points_table.setItem(row, 0, self.id_item_3)  # Tool name/id

        self.sec_point_coords_lbl = QtWidgets.QTableWidgetItem('%s' % _('Second Point'))
        self.sec_point_coords_lbl.setFlags(flags)
        self.points_table.setItem(row, 1, self.sec_point_coords_lbl)
        self.sec_points_coords_entry = EvalEntry()
        self.points_table.setCellWidget(row, 2, self.sec_points_coords_entry)

        vertical_header = self.points_table.verticalHeader()
        vertical_header.hide()
        self.points_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        horizontal_header = self.points_table.horizontalHeader()
        horizontal_header.setMinimumSectionSize(10)
        horizontal_header.setDefaultSectionSize(70)

        self.points_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        # for x in range(4):
        #     self.points_table.resizeColumnToContents(x)
        self.points_table.resizeColumnsToContents()
        self.points_table.resizeRowsToContents()

        horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(0, 20)
        horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        horizontal_header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)

        self.points_table.setMinimumHeight(self.points_table.getHeight() + 2)
        self.points_table.setMaximumHeight(self.points_table.getHeight() + 2)

        # remove the frame on the QLineEdit childrens of the table
        for row in range(self.points_table.rowCount()):
            self.points_table.cellWidget(row, 2).setFrame(False)

        # ## Grid Layout
        grid_lay = QtWidgets.QGridLayout()
        self.layout.addLayout(grid_lay)
        grid_lay.setColumnStretch(0, 0)
        grid_lay.setColumnStretch(1, 1)

        self.param_label = QtWidgets.QLabel('<b>%s:</b>' % _('Parameters'))
        self.param_label.setToolTip(
            _("Parameters used for this tool.")
        )
        grid_lay.addWidget(self.param_label, 0, 0, 1, 2)

        # DIAMETER #
        self.size_label = QtWidgets.QLabel('%s:' % _("Size"))
        self.size_label.setToolTip(
            _("This set the fiducial diameter if fiducial type is circular,\n"
              "otherwise is the size of the fiducial.\n"
              "The soldermask opening is double than that.")
        )
        self.fid_size_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.fid_size_entry.set_range(1.0000, 3.0000)
        self.fid_size_entry.set_precision(self.decimals)
        self.fid_size_entry.setWrapping(True)
        self.fid_size_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.size_label, 1, 0)
        grid_lay.addWidget(self.fid_size_entry, 1, 1)

        # MARGIN #
        self.margin_label = QtWidgets.QLabel('%s:' % _("Margin"))
        self.margin_label.setToolTip(
            _("Bounding box margin.")
        )
        self.margin_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.margin_entry.set_range(-9999.9999, 9999.9999)
        self.margin_entry.set_precision(self.decimals)
        self.margin_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.margin_label, 2, 0)
        grid_lay.addWidget(self.margin_entry, 2, 1)

        # Mode #
        self.mode_radio = RadioSet([
            {'label': _('Auto'), 'value': 'auto'},
            {"label": _("Manual"), "value": "manual"}
        ], stretch=False)
        self.mode_label = QtWidgets.QLabel(_("Mode:"))
        self.mode_label.setToolTip(
            _("- 'Auto' - automatic placement of fiducials in the corners of the bounding box.\n "
              "- 'Manual' - manual placement of fiducials.")
        )
        grid_lay.addWidget(self.mode_label, 3, 0)
        grid_lay.addWidget(self.mode_radio, 3, 1)

        # Position for second fiducial #
        self.pos_radio = RadioSet([
            {'label': _('Up'), 'value': 'up'},
            {"label": _("Down"), "value": "down"},
            {"label": _("None"), "value": "no"}
        ], stretch=False)
        self.pos_label = QtWidgets.QLabel('%s:' % _("Second fiducial"))
        self.pos_label.setToolTip(
            _("The position for the second fiducial.\n"
              "- 'Up' - the order is: bottom-left, top-left, top-right.\n"
              "- 'Down' - the order is: bottom-left, bottom-right, top-right.\n"
              "- 'None' - there is no second fiducial. The order is: bottom-left, top-right.")
        )
        grid_lay.addWidget(self.pos_label, 4, 0)
        grid_lay.addWidget(self.pos_radio, 4, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line, 5, 0, 1, 2)

        # Fiducial type #
        self.fid_type_radio = RadioSet([
            {'label': _('Circular'), 'value': 'circular'},
            {"label": _("Cross"), "value": "cross"},
            {"label": _("Chess"), "value": "chess"}
        ], stretch=False)
        self.fid_type_label = QtWidgets.QLabel('%s:' % _("Fiducial Type"))
        self.fid_type_label.setToolTip(
            _("The type of fiducial.\n"
              "- 'Circular' - this is the regular fiducial.\n"
              "- 'Cross' - cross lines fiducial.\n"
              "- 'Chess' - chess pattern fiducial.")
        )
        grid_lay.addWidget(self.fid_type_label, 6, 0)
        grid_lay.addWidget(self.fid_type_radio, 6, 1)

        # Line Thickness #
        self.line_thickness_label = QtWidgets.QLabel('%s:' % _("Line thickness"))
        self.line_thickness_label.setToolTip(
            _("Bounding box margin.")
        )
        self.line_thickness_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.line_thickness_entry.set_range(0.00001, 9999.9999)
        self.line_thickness_entry.set_precision(self.decimals)
        self.line_thickness_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.line_thickness_label, 7, 0)
        grid_lay.addWidget(self.line_thickness_entry, 7, 1)

        separator_line_1 = QtWidgets.QFrame()
        separator_line_1.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line_1.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line_1, 8, 0, 1, 2)

        # Copper Gerber object
        self.grb_object_combo = FCComboBox()
        self.grb_object_combo.setModel(self.app.collection)
        self.grb_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.grb_object_combo.is_last = True
        self.grb_object_combo.obj_type = "Gerber"

        self.grbobj_label = QtWidgets.QLabel("<b>%s:</b>" % _("Copper Gerber"))
        self.grbobj_label.setToolTip(
            _("Gerber Object to which will be added a copper thieving.")
        )

        grid_lay.addWidget(self.grbobj_label, 9, 0, 1, 2)
        grid_lay.addWidget(self.grb_object_combo, 10, 0, 1, 2)

        # ## Insert Copper Fiducial
        self.add_cfid_button = QtWidgets.QPushButton(_("Add Fiducial"))
        self.add_cfid_button.setToolTip(
            _("Will add a polygon on the copper layer to serve as fiducial.")
        )
        self.add_cfid_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)
        grid_lay.addWidget(self.add_cfid_button, 11, 0, 1, 2)

        separator_line_2 = QtWidgets.QFrame()
        separator_line_2.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line_2.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line_2, 12, 0, 1, 2)

        # Soldermask Gerber object #
        self.sm_object_label = QtWidgets.QLabel('<b>%s:</b>' % _("Soldermask Gerber"))
        self.sm_object_label.setToolTip(
            _("The Soldermask Gerber object.")
        )
        self.sm_object_combo = FCComboBox()
        self.sm_object_combo.setModel(self.app.collection)
        self.sm_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.sm_object_combo.is_last = True
        self.sm_object_combo.obj_type = "Gerber"

        grid_lay.addWidget(self.sm_object_label, 13, 0, 1, 2)
        grid_lay.addWidget(self.sm_object_combo, 14, 0, 1, 2)

        # ## Insert Soldermask opening for Fiducial
        self.add_sm_opening_button = QtWidgets.QPushButton(_("Add Soldermask Opening"))
        self.add_sm_opening_button.setToolTip(
            _("Will add a polygon on the soldermask layer\n"
              "to serve as fiducial opening.\n"
              "The diameter is always double of the diameter\n"
              "for the copper fiducial.")
        )
        self.add_sm_opening_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)
        grid_lay.addWidget(self.add_sm_opening_button, 15, 0, 1, 2)

        self.layout.addStretch()

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
        self.layout.addWidget(self.reset_button)

        # Objects involved in Copper thieving
        self.grb_object = None
        self.sm_object = None

        self.copper_obj_set = set()
        self.sm_obj_set = set()

        # store the flattened geometry here:
        self.flat_geometry = []

        # Events ID
        self.mr = None
        self.mm = None

        # Mouse cursor positions
        self.cursor_pos = (0, 0)
        self.first_click = False

        self.mode_method = False

        # Tool properties
        self.fid_dia = None
        self.sm_opening_dia = None

        self.margin_val = None
        self.sec_position = None
        self.geo_steps_per_circle = 128

        self.click_points = []

        # SIGNALS
        self.add_cfid_button.clicked.connect(self.add_fiducials)
        self.add_sm_opening_button.clicked.connect(self.add_soldermask_opening)

        self.fid_type_radio.activated_custom.connect(self.on_fiducial_type)
        self.pos_radio.activated_custom.connect(self.on_second_point)
        self.mode_radio.activated_custom.connect(self.on_method_change)
        self.reset_button.clicked.connect(self.set_tool_ui)

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolFiducials()")

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

        self.app.ui.notebook.setTabText(2, _("Fiducials Tool"))

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, shortcut='Alt+J', **kwargs)

    def set_tool_ui(self):
        self.units = self.app.defaults['units']
        self.fid_size_entry.set_value(self.app.defaults["tools_fiducials_dia"])
        self.margin_entry.set_value(float(self.app.defaults["tools_fiducials_margin"]))
        self.mode_radio.set_value(self.app.defaults["tools_fiducials_mode"])
        self.pos_radio.set_value(self.app.defaults["tools_fiducials_second_pos"])
        self.fid_type_radio.set_value(self.app.defaults["tools_fiducials_type"])
        self.line_thickness_entry.set_value(float(self.app.defaults["tools_fiducials_line_thickness"]))

        self.click_points = []
        self.bottom_left_coords_entry.set_value('')
        self.top_right_coords_entry.set_value('')
        self.sec_points_coords_entry.set_value('')

        self.copper_obj_set = set()
        self.sm_obj_set = set()

    def on_second_point(self, val):
        if val == 'no':
            self.id_item_3.setFlags(QtCore.Qt.NoItemFlags)
            self.sec_point_coords_lbl.setFlags(QtCore.Qt.NoItemFlags)
            self.sec_points_coords_entry.setDisabled(True)
        else:
            self.id_item_3.setFlags(QtCore.Qt.ItemIsEnabled)
            self.sec_point_coords_lbl.setFlags(QtCore.Qt.ItemIsEnabled)
            self.sec_points_coords_entry.setDisabled(False)

    def on_method_change(self, val):
        """
        Make sure that on method change we disconnect the event handlers and reset the points storage
        :param val: value of the Radio button which trigger this method
        :return: None
        """
        if val == 'auto':
            self.click_points = []

            try:
                self.disconnect_event_handlers()
            except TypeError:
                pass

    def on_fiducial_type(self, val):
        if val == 'cross':
            self.line_thickness_label.setDisabled(False)
            self.line_thickness_entry.setDisabled(False)
        else:
            self.line_thickness_label.setDisabled(True)
            self.line_thickness_entry.setDisabled(True)

    def add_fiducials(self):
        self.app.call_source = "fiducials_tool"
        self.mode_method = self.mode_radio.get_value()
        self.margin_val = self.margin_entry.get_value()
        self.sec_position = self.pos_radio.get_value()
        fid_type = self.fid_type_radio.get_value()

        self.click_points = []

        # get the Gerber object on which the Fiducial will be inserted
        selection_index = self.grb_object_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.grb_object_combo.rootModelIndex())

        try:
            self.grb_object = model_index.internalPointer().obj
        except Exception as e:
            log.debug("ToolFiducials.execute() --> %s" % str(e))
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Gerber object loaded ..."))
            return 'fail'

        self.copper_obj_set.add(self.grb_object.options['name'])

        if self.mode_method == 'auto':
            xmin, ymin, xmax, ymax = self.grb_object.bounds()
            bbox = box(xmin, ymin, xmax, ymax)
            buf_bbox = bbox.buffer(self.margin_val, join_style=2)
            x0, y0, x1, y1 = buf_bbox.bounds

            self.click_points.append(
                (
                    float('%.*f' % (self.decimals, x0)),
                    float('%.*f' % (self.decimals, y0))
                )
            )
            self.bottom_left_coords_entry.set_value('(%.*f, %.*f)' % (self.decimals, x0, self.decimals, y0))

            self.click_points.append(
                (
                    float('%.*f' % (self.decimals, x1)),
                    float('%.*f' % (self.decimals, y1))
                )
            )
            self.top_right_coords_entry.set_value('(%.*f, %.*f)' % (self.decimals, x1, self.decimals, y1))

            if self.sec_position == 'up':
                self.click_points.append(
                    (
                        float('%.*f' % (self.decimals, x0)),
                        float('%.*f' % (self.decimals, y1))
                    )
                )
                self.sec_points_coords_entry.set_value('(%.*f, %.*f)' % (self.decimals, x0, self.decimals, y1))
            elif self.sec_position == 'down':
                self.click_points.append(
                    (
                        float('%.*f' % (self.decimals, x1)),
                        float('%.*f' % (self.decimals, y0))
                    )
                )
                self.sec_points_coords_entry.set_value('(%.*f, %.*f)' % (self.decimals, x1, self.decimals, y0))

            self.add_fiducials_geo(self.click_points, g_obj=self.grb_object, fid_type=fid_type)
            self.grb_object.source_file = self.app.export_gerber(obj_name=self.grb_object.options['name'],
                                                                 filename=None,
                                                                 local_use=self.grb_object, use_thread=False)
            self.on_exit()
        else:
            self.app.inform.emit(_("Click to add first Fiducial. Bottom Left..."))
            self.bottom_left_coords_entry.set_value('')
            self.top_right_coords_entry.set_value('')
            self.sec_points_coords_entry.set_value('')

            self.connect_event_handlers()

        # To be called after clicking on the plot.

    def add_fiducials_geo(self, points_list, g_obj, fid_size=None, fid_type=None, line_size=None):
        """
        Add geometry to the solid_geometry of the copper Gerber object
        :param points_list: list of coordinates for the fiducials
        :param g_obj: the Gerber object where to add the geometry
        :param fid_size: the overall size of the fiducial or fiducial opening depending on the g_obj type
        :param fid_type: the type of fiducial: circular or cross
        :param line_size: the line thickenss when the fiducial type is cross
        :return:
        """
        fid_size = self.fid_size_entry.get_value() if fid_size is None else fid_size
        fid_type = 'circular' if fid_type is None else fid_type
        line_thickness = self.line_thickness_entry.get_value() if line_size is None else line_size

        radius = fid_size / 2.0

        if fid_type == 'circular':
            geo_list = [Point(pt).buffer(radius) for pt in points_list]

            aperture_found = None
            for ap_id, ap_val in g_obj.apertures.items():
                if ap_val['type'] == 'C' and ap_val['size'] == fid_size:
                    aperture_found = ap_id
                    break

            if aperture_found:
                for geo in geo_list:
                    dict_el = {}
                    dict_el['follow'] = geo.centroid
                    dict_el['solid'] = geo
                    g_obj.apertures[aperture_found]['geometry'].append(deepcopy(dict_el))
            else:
                ap_keys = list(g_obj.apertures.keys())
                if ap_keys:
                    new_apid = str(int(max(ap_keys)) + 1)
                else:
                    new_apid = '10'

                g_obj.apertures[new_apid] = {}
                g_obj.apertures[new_apid]['type'] = 'C'
                g_obj.apertures[new_apid]['size'] = fid_size
                g_obj.apertures[new_apid]['geometry'] = []

                for geo in geo_list:
                    dict_el = {}
                    dict_el['follow'] = geo.centroid
                    dict_el['solid'] = geo
                    g_obj.apertures[new_apid]['geometry'].append(deepcopy(dict_el))

            s_list = []
            if g_obj.solid_geometry:
                try:
                    for poly in g_obj.solid_geometry:
                        s_list.append(poly)
                except TypeError:
                    s_list.append(g_obj.solid_geometry)

            s_list += geo_list
            g_obj.solid_geometry = MultiPolygon(s_list)
        elif fid_type == 'cross':
            geo_list = []

            for pt in points_list:
                x = pt[0]
                y = pt[1]
                line_geo_hor = LineString([
                    (x - radius + (line_thickness / 2.0), y), (x + radius - (line_thickness / 2.0), y)
                ])
                line_geo_vert = LineString([
                    (x, y - radius + (line_thickness / 2.0)), (x, y + radius - (line_thickness / 2.0))
                ])
                geo_list.append([line_geo_hor, line_geo_vert])

            aperture_found = None
            for ap_id, ap_val in g_obj.apertures.items():
                if ap_val['type'] == 'C' and ap_val['size'] == line_thickness:
                    aperture_found = ap_id
                    break

            geo_buff_list = []
            if aperture_found:
                for geo in geo_list:
                    geo_buff_h = geo[0].buffer(line_thickness / 2.0)
                    geo_buff_v = geo[1].buffer(line_thickness / 2.0)
                    geo_buff_list.append(geo_buff_h)
                    geo_buff_list.append(geo_buff_v)

                    dict_el = {}
                    dict_el['follow'] = geo_buff_h.centroid
                    dict_el['solid'] = geo_buff_h
                    g_obj.apertures[aperture_found]['geometry'].append(deepcopy(dict_el))
                    dict_el['follow'] = geo_buff_v.centroid
                    dict_el['solid'] = geo_buff_v
                    g_obj.apertures[aperture_found]['geometry'].append(deepcopy(dict_el))
            else:
                ap_keys = list(g_obj.apertures.keys())
                if ap_keys:
                    new_apid = str(int(max(ap_keys)) + 1)
                else:
                    new_apid = '10'

                g_obj.apertures[new_apid] = {}
                g_obj.apertures[new_apid]['type'] = 'C'
                g_obj.apertures[new_apid]['size'] = line_thickness
                g_obj.apertures[new_apid]['geometry'] = []

                for geo in geo_list:
                    geo_buff_h = geo[0].buffer(line_thickness / 2.0)
                    geo_buff_v = geo[1].buffer(line_thickness / 2.0)
                    geo_buff_list.append(geo_buff_h)
                    geo_buff_list.append(geo_buff_v)

                    dict_el = {}
                    dict_el['follow'] = geo_buff_h.centroid
                    dict_el['solid'] = geo_buff_h
                    g_obj.apertures[new_apid]['geometry'].append(deepcopy(dict_el))
                    dict_el['follow'] = geo_buff_v.centroid
                    dict_el['solid'] = geo_buff_v
                    g_obj.apertures[new_apid]['geometry'].append(deepcopy(dict_el))

            s_list = []
            if g_obj.solid_geometry:
                try:
                    for poly in g_obj.solid_geometry:
                        s_list.append(poly)
                except TypeError:
                    s_list.append(g_obj.solid_geometry)

            geo_buff_list = MultiPolygon(geo_buff_list)
            geo_buff_list = geo_buff_list.buffer(0)
            for poly in geo_buff_list:
                s_list.append(poly)
            g_obj.solid_geometry = MultiPolygon(s_list)
        else:
            # chess pattern fiducial type
            geo_list = []

            def make_square_poly(center_pt, side_size):
                half_s = side_size / 2
                x_center = center_pt[0]
                y_center = center_pt[1]

                pt1 = (x_center - half_s, y_center - half_s)
                pt2 = (x_center + half_s, y_center - half_s)
                pt3 = (x_center + half_s, y_center + half_s)
                pt4 = (x_center - half_s, y_center + half_s)

                return Polygon([pt1, pt2, pt3, pt4, pt1])

            for pt in points_list:
                x = pt[0]
                y = pt[1]
                first_square = make_square_poly(center_pt=(x-fid_size/4, y+fid_size/4), side_size=fid_size/2)
                second_square = make_square_poly(center_pt=(x+fid_size/4, y-fid_size/4), side_size=fid_size/2)
                geo_list += [first_square, second_square]

            aperture_found = None
            new_ap_size = math.sqrt(fid_size**2 + fid_size**2)
            for ap_id, ap_val in g_obj.apertures.items():
                if ap_val['type'] == 'R' and \
                        round(ap_val['size'], ndigits=self.decimals) == round(new_ap_size, ndigits=self.decimals):
                    aperture_found = ap_id
                    break

            geo_buff_list = []
            if aperture_found:
                for geo in geo_list:
                    geo_buff_list.append(geo)

                    dict_el = {}
                    dict_el['follow'] = geo.centroid
                    dict_el['solid'] = geo
                    g_obj.apertures[aperture_found]['geometry'].append(deepcopy(dict_el))
            else:
                ap_keys = list(g_obj.apertures.keys())
                if ap_keys:
                    new_apid = str(int(max(ap_keys)) + 1)
                else:
                    new_apid = '10'

                g_obj.apertures[new_apid] = {}
                g_obj.apertures[new_apid]['type'] = 'R'
                g_obj.apertures[new_apid]['size'] = new_ap_size
                g_obj.apertures[new_apid]['width'] = fid_size
                g_obj.apertures[new_apid]['height'] = fid_size
                g_obj.apertures[new_apid]['geometry'] = []

                for geo in geo_list:
                    geo_buff_list.append(geo)

                    dict_el = {}
                    dict_el['follow'] = geo.centroid
                    dict_el['solid'] = geo
                    g_obj.apertures[new_apid]['geometry'].append(deepcopy(dict_el))

            s_list = []
            if g_obj.solid_geometry:
                try:
                    for poly in g_obj.solid_geometry:
                        s_list.append(poly)
                except TypeError:
                    s_list.append(g_obj.solid_geometry)

            for poly in geo_buff_list:
                s_list.append(poly)
            g_obj.solid_geometry = MultiPolygon(s_list)

    def add_soldermask_opening(self):
        sm_opening_dia = self.fid_size_entry.get_value() * 2.0

        # get the Gerber object on which the Fiducial will be inserted
        selection_index = self.sm_object_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.sm_object_combo.rootModelIndex())

        try:
            self.sm_object = model_index.internalPointer().obj
        except Exception as e:
            log.debug("ToolFiducials.add_soldermask_opening() --> %s" % str(e))
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Gerber object loaded ..."))
            return 'fail'

        self.sm_obj_set.add(self.sm_object.options['name'])
        self.add_fiducials_geo(self.click_points, g_obj=self.sm_object, fid_size=sm_opening_dia, fid_type='circular')

        self.sm_object.source_file = self.app.export_gerber(obj_name=self.sm_object.options['name'], filename=None,
                                                            local_use=self.sm_object, use_thread=False)
        self.on_exit()

    def on_mouse_release(self, event):
        if event.button == 1:
            if self.app.is_legacy is False:
                event_pos = event.pos
            else:
                event_pos = (event.xdata, event.ydata)

            pos_canvas = self.canvas.translate_coords(event_pos)
            if self.app.grid_status():
                pos = self.app.geo_editor.snap(pos_canvas[0], pos_canvas[1])
            else:
                pos = (pos_canvas[0], pos_canvas[1])
            click_pt = Point([pos[0], pos[1]])

            self.click_points.append(
                (
                    float('%.*f' % (self.decimals, click_pt.x)),
                    float('%.*f' % (self.decimals, click_pt.y))
                )
            )
            self.check_points()

    def check_points(self):
        fid_type = self.fid_type_radio.get_value()

        if len(self.click_points) == 1:
            self.bottom_left_coords_entry.set_value(self.click_points[0])
            self.app.inform.emit(_("Click to add the last fiducial. Top Right..."))

        if self.sec_position != 'no':
            if len(self.click_points) == 2:
                self.top_right_coords_entry.set_value(self.click_points[1])
                self.app.inform.emit(_("Click to add the second fiducial. Top Left or Bottom Right..."))
            elif len(self.click_points) == 3:
                self.sec_points_coords_entry.set_value(self.click_points[2])
                self.app.inform.emit('[success] %s' % _("Done. All fiducials have been added."))
                self.add_fiducials_geo(self.click_points, g_obj=self.grb_object, fid_type=fid_type)
                self.grb_object.source_file = self.app.export_gerber(obj_name=self.grb_object.options['name'],
                                                                     filename=None,
                                                                     local_use=self.grb_object, use_thread=False)
                self.on_exit()
        else:
            if len(self.click_points) == 2:
                self.top_right_coords_entry.set_value(self.click_points[1])
                self.app.inform.emit('[success] %s' % _("Done. All fiducials have been added."))
                self.add_fiducials_geo(self.click_points, g_obj=self.grb_object, fid_type=fid_type)
                self.grb_object.source_file = self.app.export_gerber(obj_name=self.grb_object.options['name'],
                                                                     filename=None,
                                                                     local_use=self.grb_object, use_thread=False)
                self.on_exit()

    def on_mouse_move(self, event):
        pass

    def replot(self, obj, run_thread=True):
        def worker_task():
            with self.app.proc_container.new('%s...' % _("Plotting")):
                obj.plot()

        if run_thread:
            self.app.worker_task.emit({'fcn': worker_task, 'params': []})
        else:
            worker_task()

    def on_exit(self):
        # plot the object
        for ob_name in self.copper_obj_set:
            try:
                copper_obj = self.app.collection.get_by_name(name=ob_name)
                if len(self.copper_obj_set) > 1:
                    self.replot(obj=copper_obj, run_thread=False)
                else:
                    self.replot(obj=copper_obj)
            except (AttributeError, TypeError):
                continue

            # update the bounding box values
            try:
                a, b, c, d = copper_obj.bounds()
                copper_obj.options['xmin'] = a
                copper_obj.options['ymin'] = b
                copper_obj.options['xmax'] = c
                copper_obj.options['ymax'] = d
            except Exception as e:
                log.debug("ToolFiducials.on_exit() copper_obj bounds error --> %s" % str(e))

        for ob_name in self.sm_obj_set:
            try:
                sm_obj = self.app.collection.get_by_name(name=ob_name)
                if len(self.sm_obj_set) > 1:
                    self.replot(obj=sm_obj, run_thread=False)
                else:
                    self.replot(obj=sm_obj)
            except (AttributeError, TypeError):
                continue

            # update the bounding box values
            try:
                a, b, c, d = sm_obj.bounds()
                sm_obj.options['xmin'] = a
                sm_obj.options['ymin'] = b
                sm_obj.options['xmax'] = c
                sm_obj.options['ymax'] = d
            except Exception as e:
                log.debug("ToolFiducials.on_exit() sm_obj bounds error --> %s" % str(e))

        # reset the variables
        self.grb_object = None
        self.sm_object = None

        # Events ID
        self.mr = None
        # self.mm = None

        # Mouse cursor positions
        self.cursor_pos = (0, 0)
        self.first_click = False

        self.disconnect_event_handlers()

        self.app.call_source = "app"
        self.app.inform.emit('[success] %s' % _("Fiducials Tool exit."))

    def connect_event_handlers(self):
        if self.app.is_legacy is False:
            self.app.plotcanvas.graph_event_disconnect('mouse_press', self.app.on_mouse_click_over_plot)
            # self.app.plotcanvas.graph_event_disconnect('mouse_move', self.app.on_mouse_move_over_plot)
            self.app.plotcanvas.graph_event_disconnect('mouse_release', self.app.on_mouse_click_release_over_plot)
        else:
            self.app.plotcanvas.graph_event_disconnect(self.app.mp)
            # self.app.plotcanvas.graph_event_disconnect(self.app.mm)
            self.app.plotcanvas.graph_event_disconnect(self.app.mr)

        self.mr = self.app.plotcanvas.graph_event_connect('mouse_release', self.on_mouse_release)
        # self.mm = self.app.plotcanvas.graph_event_connect('mouse_move', self.on_mouse_move)

    def disconnect_event_handlers(self):
        if self.app.is_legacy is False:
            self.app.plotcanvas.graph_event_disconnect('mouse_release', self.on_mouse_release)
            # self.app.plotcanvas.graph_event_disconnect('mouse_move', self.on_mouse_move)
        else:
            self.app.plotcanvas.graph_event_disconnect(self.mr)
            # self.app.plotcanvas.graph_event_disconnect(self.mm)

        self.app.mp = self.app.plotcanvas.graph_event_connect('mouse_press',
                                                              self.app.on_mouse_click_over_plot)
        # self.app.mm = self.app.plotcanvas.graph_event_connect('mouse_move',
        #                                                       self.app.on_mouse_move_over_plot)
        self.app.mr = self.app.plotcanvas.graph_event_connect('mouse_release',
                                                              self.app.on_mouse_click_release_over_plot)

    def flatten(self, geometry):
        """
        Creates a list of non-iterable linear geometry objects.
        :param geometry: Shapely type or list or list of list of such.

        Results are placed in self.flat_geometry
        """

        # ## If iterable, expand recursively.
        try:
            for geo in geometry:
                if geo is not None:
                    self.flatten(geometry=geo)

        # ## Not iterable, do the actual indexing and add.
        except TypeError:
            self.flat_geometry.append(geometry)

        return self.flat_geometry
