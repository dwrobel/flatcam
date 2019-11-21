# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 10/25/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtCore

from FlatCAMTool import FlatCAMTool
from flatcamGUI.GUIElements import FCDoubleSpinner, RadioSet, EvalEntry, FCTable

import shapely.geometry.base as base
from shapely.ops import unary_union
from shapely.geometry import Point
from shapely.geometry import box as box


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

        self.decimals = 4
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
        self.dia_label = QtWidgets.QLabel('%s:' % _("Diameter"))
        self.dia_label.setToolTip(
            _("This set the fiducial diameter.\n"
              "The soldermask opening is double than that.")
        )
        self.dia_entry = FCDoubleSpinner()
        self.dia_entry.set_range(1.0000, 3.0000)
        self.dia_entry.set_precision(self.decimals)
        self.dia_entry.setWrapping(True)
        self.dia_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.dia_label, 1, 0)
        grid_lay.addWidget(self.dia_entry, 1, 1)

        # MARGIN #
        self.margin_label = QtWidgets.QLabel('%s:' % _("Margin"))
        self.margin_label.setToolTip(
            _("Bounding box margin.")
        )
        self.margin_entry = FCDoubleSpinner()
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
              "- 'Up' - the order is: bottom-left, top-left, top-right.\n "
              "- 'Down' - the order is: bottom-left, bottom-right, top-right.\n"
              "- 'None' - there is no second fiducial. The order is: bottom-left, top-right.")
        )
        grid_lay.addWidget(self.pos_label, 4, 0)
        grid_lay.addWidget(self.pos_radio, 4, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line, 5, 0, 1, 2)

        # Copper Gerber object
        self.grb_object_combo = QtWidgets.QComboBox()
        self.grb_object_combo.setModel(self.app.collection)
        self.grb_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.grb_object_combo.setCurrentIndex(1)

        self.grbobj_label = QtWidgets.QLabel("<b>%s:</b>" % _("Copper Gerber"))
        self.grbobj_label.setToolTip(
            _("Gerber Object to which will be added a copper thieving.")
        )

        grid_lay.addWidget(self.grbobj_label, 6, 0, 1, 2)
        grid_lay.addWidget(self.grb_object_combo, 7, 0, 1, 2)

        # ## Insert Copper Fiducial
        self.add_cfid_button = QtWidgets.QPushButton(_("Add Fiducial"))
        self.add_cfid_button.setToolTip(
            _("Will add a polygon on the copper layer to serve as fiducial.")
        )
        grid_lay.addWidget(self.add_cfid_button, 8, 0, 1, 2)

        separator_line_1 = QtWidgets.QFrame()
        separator_line_1.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line_1.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line_1, 9, 0, 1, 2)

        # Soldermask Gerber object #
        self.sm_object_label = QtWidgets.QLabel('<b>%s:</b>' % _("Soldermask Gerber"))
        self.sm_object_label.setToolTip(
            _("The Soldermask Gerber object.")
        )
        self.sm_object_combo = QtWidgets.QComboBox()
        self.sm_object_combo.setModel(self.app.collection)
        self.sm_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.sm_object_combo.setCurrentIndex(1)

        grid_lay.addWidget(self.sm_object_label, 10, 0, 1, 2)
        grid_lay.addWidget(self.sm_object_combo, 11, 0, 1, 2)

        # ## Insert Soldermask opening for Fiducial
        self.add_sm_opening_button = QtWidgets.QPushButton(_("Add Soldermask Opening"))
        self.add_sm_opening_button.setToolTip(
            _("Will add a polygon on the soldermask layer\n"
              "to serve as fiducial opening.\n"
              "The diameter is always double of the diameter\n"
              "for the copper fiducial.")
        )
        grid_lay.addWidget(self.add_sm_opening_button, 12, 0, 1, 2)

        self.layout.addStretch()

        # Objects involved in Copper thieving
        self.grb_object = None
        self.sm_object = None

        self.copper_obj_set = set()
        self.sm_obj_set = set()

        # store the flattened geometry here:
        self.flat_geometry = list()

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

        self.click_points = list()

        # SIGNALS
        self.add_cfid_button.clicked.connect(self.add_fiducials)
        self.add_sm_opening_button.clicked.connect(self.add_soldermask_opening)

        # self.reference_radio.group_toggle_fn = self.on_toggle_reference
        self.pos_radio.activated_custom.connect(self.on_second_point)
        self.mode_radio.activated_custom.connect(self.on_method_change)

    def run(self, toggle=True):
        self.app.report_usage("ToolFiducials()")

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
        FlatCAMTool.install(self, icon, separator, shortcut='ALT+J', **kwargs)

    def set_tool_ui(self):
        self.units = self.app.ui.general_defaults_form.general_app_group.units_radio.get_value()
        # self.mode_radio.set_value(float(self.app.defaults["tools_fiducials_mode"]))
        # self.margin_entry.set_value(float(self.app.defaults["tools_fiducials_margin"]))
        # self.dia_entry.set_value(self.app.defaults["tools_fiducials_dia"])
        self.click_points = list()
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
            self.click_points = list()

            try:
                self.disconnect_event_handlers()
            except TypeError:
                pass

    def add_fiducials(self):
        self.app.call_source = "fiducials_tool"
        self.mode_method = self.mode_radio.get_value()
        self.margin_val = self.margin_entry.get_value()
        self.sec_position = self.pos_radio.get_value()

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

            self.add_fiducials_geo(self.click_points)
            self.on_exit()
        else:
            self.app.inform.emit(_("Click to add first Fiducial. Bottom Left..."))
            self.bottom_left_coords_entry.set_value('')
            self.top_right_coords_entry.set_value('')
            self.sec_points_coords_entry.set_value('')

            if self.app.is_legacy is False:
                self.app.plotcanvas.graph_event_disconnect('mouse_press', self.app.on_mouse_click_over_plot)
                # self.app.plotcanvas.graph_event_disconnect('mouse_move', self.app.on_mouse_move_over_plot)
                self.app.plotcanvas.graph_event_disconnect('mouse_release', self.app.on_mouse_click_release_over_plot)
            else:
                self.app.plotcanvas.graph_event_disconnect(self.app.mp)
                self.app.plotcanvas.graph_event_disconnect(self.app.mm)
                self.app.plotcanvas.graph_event_disconnect(self.app.mr)

            self.mr = self.app.plotcanvas.graph_event_connect('mouse_release', self.on_mouse_release)
            # self.mm = self.app.plotcanvas.graph_event_connect('mouse_move', self.on_mouse_move)

        # To be called after clicking on the plot.

    def add_fiducials_geo(self, points_list):
        """
        Add geometry to the solid_geometry of the copper Gerber object
        :param points_list: list of coordinates for the fiducials
        :return:
        """
        self.fid_dia = self.dia_entry.get_value()
        radius = self.fid_dia / 2.0

        geo_list = [Point(pt).buffer(radius) for pt in points_list]

        aperture_found = None
        for ap_id, ap_val in self.grb_object.apertures.items():
            if ap_val['type'] == 'C' and ap_val['size'] == self.fid_dia:
                aperture_found = ap_id
                break

        if aperture_found:
            for geo in geo_list:
                dict_el = dict()
                dict_el['follow'] = geo.centroid
                dict_el['solid'] = geo
                self.grb_object.apertures[aperture_found]['geometry'].append(deepcopy(dict_el))
        else:
            new_apid = int(max(list(self.grb_object.apertures.keys()))) + 1
            self.grb_object.apertures[new_apid] = dict()
            self.grb_object.apertures[new_apid]['type'] = 'C'
            self.grb_object.apertures[new_apid]['size'] = self.fid_dia
            self.grb_object.apertures[new_apid]['geometry'] = list()

            for geo in geo_list:
                dict_el = dict()
                dict_el['follow'] = geo.centroid
                dict_el['solid'] = geo
                self.grb_object.apertures[new_apid]['geometry'].append(deepcopy(dict_el))

            if self.grb_object.solid_geometry:
                self.grb_object.solid_geometry = [self.grb_object.solid_geometry, geo_list]

    def add_soldermask_opening(self):

        self.sm_opening_dia = self.dia_entry.get_value() * 2.0

        # get the Gerber object on which the Fiducial will be inserted
        selection_index = self.grb_object_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.grb_object_combo.rootModelIndex())

        try:
            self.sm_object = model_index.internalPointer().obj
        except Exception as e:
            log.debug("ToolFiducials.add_soldermask_opening() --> %s" % str(e))
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Gerber object loaded ..."))
            return 'fail'

        self.sm_obj_set.add(self.sm_object.options['name'])

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
                self.add_fiducials_geo(self.click_points)
                self.on_exit()
        else:
            if len(self.click_points) == 2:
                self.sec_points_coords_entry.set_value(self.click_points[2])
                self.app.inform.emit('[success] %s' % _("Done. All fiducials have been added."))
                self.add_fiducials_geo(self.click_points)
                self.on_exit()

    def on_mouse_move(self, event):
        pass

    def replot(self, obj):
        def worker_task():
            with self.app.proc_container.new('%s...' % _("Plotting")):
                obj.plot()

        self.app.worker_task.emit({'fcn': worker_task, 'params': []})

    def on_exit(self):
        # plot the object
        for ob_name in self.copper_obj_set:
            try:
                copper_obj = self.app.collection.get_by_name(name=ob_name)
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

        # if True it means we exited from tool in the middle of fiducials adding
        if len(self.click_points) not in [0, 3]:
            self.click_points = list()

        if self.mode_method == 'manual' and len(self.click_points) not in [0, 3]:
            self.disconnect_event_handlers()

        self.app.call_source = "app"
        self.app.inform.emit('[success] %s' % _("Fiducials Tool exit."))

    def disconnect_event_handlers(self):
        if self.app.is_legacy is False:
            self.app.plotcanvas.graph_event_disconnect('mouse_release', self.on_mouse_release)
            self.app.plotcanvas.graph_event_disconnect('mouse_move', self.on_mouse_move)
        else:
            self.app.plotcanvas.graph_event_disconnect(self.mr)
            self.app.plotcanvas.graph_event_disconnect(self.mm)

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
