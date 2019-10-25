# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 10/25/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtCore

import FlatCAMApp
from FlatCAMTool import FlatCAMTool
from flatcamGUI.GUIElements import FCDoubleSpinner, RadioSet
from FlatCAMObj import FlatCAMGerber, FlatCAMGeometry, FlatCAMExcellon

import shapely.geometry.base as base
from shapely.ops import cascaded_union, unary_union
from shapely.geometry import Polygon, MultiPolygon
from shapely.geometry import box as box

import logging
from copy import deepcopy
import numpy as np
from collections import Iterable

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class ToolCopperFill(FlatCAMTool):

    toolName = _("Copper Fill Tool")

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

        # ## Grid Layout
        i_grid_lay = QtWidgets.QGridLayout()
        self.layout.addLayout(i_grid_lay)
        i_grid_lay.setColumnStretch(0, 0)
        i_grid_lay.setColumnStretch(1, 1)

        self.grb_object_combo = QtWidgets.QComboBox()
        self.grb_object_combo.setModel(self.app.collection)
        self.grb_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.grb_object_combo.setCurrentIndex(1)

        self.grbobj_label = QtWidgets.QLabel("<b>%s:</b>" % _("GERBER"))
        self.grbobj_label.setToolTip(
            _("Gerber Object to which will be added a copper fill.")
        )

        i_grid_lay.addWidget(self.grbobj_label, 0, 0)
        i_grid_lay.addWidget(self.grb_object_combo, 0, 1, 1, 2)
        i_grid_lay.addWidget(QtWidgets.QLabel(''), 1, 0)

        # ## Grid Layout
        grid_lay = QtWidgets.QGridLayout()
        self.layout.addLayout(grid_lay)
        grid_lay.setColumnStretch(0, 0)
        grid_lay.setColumnStretch(1, 1)

        self.copper_fill_label = QtWidgets.QLabel('<b>%s</b>' % _('Parameters'))
        self.copper_fill_label.setToolTip(
            _("Parameters used for this tool.")
        )
        grid_lay.addWidget(self.copper_fill_label, 0, 0, 1, 2)

        # CLEARANCE #
        self.clearance_label = QtWidgets.QLabel('%s:' % _("Clearance"))
        self.clearance_label.setToolTip(
            _("This set the distance between the copper fill components\n"
              "(the polygon fill may be split in multiple polygons)\n"
              "and the copper traces in the Gerber file.")
        )
        self.clearance_entry = FCDoubleSpinner()
        self.clearance_entry.setMinimum(0.00001)
        self.clearance_entry.set_precision(self.decimals)
        self.clearance_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.clearance_label, 1, 0)
        grid_lay.addWidget(self.clearance_entry, 1, 1)

        # MARGIN #
        self.margin_label = QtWidgets.QLabel('%s:' % _("Margin"))
        self.margin_label.setToolTip(
            _("Bounding box margin.")
        )
        self.margin_entry = FCDoubleSpinner()
        self.margin_entry.setMinimum(0.0)
        self.margin_entry.set_precision(self.decimals)
        self.margin_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.margin_label, 2, 0)
        grid_lay.addWidget(self.margin_entry, 2, 1)

        # Reference #
        self.reference_radio = RadioSet([
            {'label': _('Itself'), 'value': 'itself'},
            {"label": _("Area Selection"), "value": "area"},
            {'label':  _("Reference Object"), 'value': 'box'}
        ], orientation='vertical', stretch=False)
        self.reference_label = QtWidgets.QLabel(_("Reference:"))
        self.reference_label.setToolTip(
            _("- 'Itself' - the copper fill extent is based on the object that is copper cleared.\n "
              "- 'Area Selection' - left mouse click to start selection of the area to be filled.\n"
              "- 'Reference Object' - will do copper filling within the area specified by another object.")
        )
        grid_lay.addWidget(self.reference_label, 3, 0)
        grid_lay.addWidget(self.reference_radio, 3, 1)

        self.box_combo_type_label = QtWidgets.QLabel('%s:' % _("Ref. Type"))
        self.box_combo_type_label.setToolTip(
            _("The type of FlatCAM object to be used as copper filling reference.\n"
              "It can be Gerber, Excellon or Geometry.")
        )
        self.box_combo_type = QtWidgets.QComboBox()
        self.box_combo_type.addItem(_("Reference Gerber"))
        self.box_combo_type.addItem(_("Reference Excellon"))
        self.box_combo_type.addItem(_("Reference Geometry"))

        grid_lay.addWidget(self.box_combo_type_label, 4, 0)
        grid_lay.addWidget(self.box_combo_type, 4, 1)

        self.box_combo_label = QtWidgets.QLabel('%s:' % _("Ref. Object"))
        self.box_combo_label.setToolTip(
            _("The FlatCAM object to be used as non copper clearing reference.")
        )
        self.box_combo = QtWidgets.QComboBox()
        self.box_combo.setModel(self.app.collection)
        self.box_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.box_combo.setCurrentIndex(1)

        grid_lay.addWidget(self.box_combo_label, 5, 0)
        grid_lay.addWidget(self.box_combo, 5, 1)

        self.box_combo.hide()
        self.box_combo_label.hide()
        self.box_combo_type.hide()
        self.box_combo_type_label.hide()

        # Bounding Box Type #
        self.bbox_type_radio = RadioSet([
            {'label': _('Rectangular'), 'value': 'rect'},
            {"label": _("Minimal"), "value": "min"}
        ], stretch=False)
        self.bbox_type_label = QtWidgets.QLabel(_("Box Type:"))
        self.bbox_type_label.setToolTip(
            _("- 'Rectangular' - the bounding box will be of rectangular shape.\n "
              "- 'Minimal' - the bounding box will be the convex hull shape.")
        )
        grid_lay.addWidget(self.bbox_type_label, 6, 0)
        grid_lay.addWidget(self.bbox_type_radio, 6, 1)
        self.bbox_type_label.hide()
        self.bbox_type_radio.hide()

        # ## Insert Copper Fill
        self.fill_button = QtWidgets.QPushButton(_("Insert Copper Fill"))
        self.fill_button.setToolTip(
            _("Will add a polygon (may be split in multiple parts)\n"
              "that will surround the actual Gerber traces at a certain distance.")
        )
        self.layout.addWidget(self.fill_button)

        self.layout.addStretch()

        # Objects involved in Copper filling
        self.grb_object = None
        self.ref_obj = None
        self.sel_rect = list()

        # Events ID
        self.mr = None
        self.mm = None

        # Mouse cursor positions
        self.mouse_is_dragging = False
        self.cursor_pos = (0, 0)
        self.first_click = False

        self.area_method = False

        # Tool properties
        self.clearance_val = None
        self.margin_val = None
        self.geo_steps_per_circle = 128

        # SIGNALS
        self.fill_button.clicked.connect(self.execute)
        self.box_combo_type.currentIndexChanged.connect(self.on_combo_box_type)
        self.reference_radio.group_toggle_fn = self.on_toggle_reference

    def run(self, toggle=True):
        self.app.report_usage("ToolCopperFill()")

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

        self.app.ui.notebook.setTabText(2, _("Copper Fill Tool"))

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, shortcut='ALT+F', **kwargs)

    def set_tool_ui(self):
        self.units = self.app.ui.general_defaults_form.general_app_group.units_radio.get_value()
        # self.clearance_entry.set_value(float(self.app.defaults["tools_copperfill_clearance"]))
        # self.margin_entry.set_value(float(self.app.defaults["tools_copperfill_margin"]))
        # self.reference_radio.set_value(self.app.defaults["tools_copperfill_reference"])
        # self.geo_steps_per_circle = int(self.app.defaults["tools_copperfill_circle_steps"])
        # self.bbox_type_radio.set_value(self.app.defaults["tools_copperfill_box_type"])

        self.clearance_entry.set_value(0.5)
        self.margin_entry.set_value(1.0)
        self.reference_radio.set_value('itself')
        self.bbox_type_radio.set_value('rect')

        self.area_method = False

    def on_combo_box_type(self):
        obj_type = self.box_combo_type.currentIndex()
        self.box_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.box_combo.setCurrentIndex(0)

    def on_toggle_reference(self):
        if self.reference_radio.get_value() == "itself" or self.reference_radio.get_value() == "area":
            self.box_combo.hide()
            self.box_combo_label.hide()
            self.box_combo_type.hide()
            self.box_combo_type_label.hide()
        else:
            self.box_combo.show()
            self.box_combo_label.show()
            self.box_combo_type.show()
            self.box_combo_type_label.show()

        if self.reference_radio.get_value() == "itself":
            self.bbox_type_label.show()
            self.bbox_type_radio.show()
        else:
            self.bbox_type_label.hide()
            self.bbox_type_radio.hide()

    def execute(self):
        self.app.call_source = "copperfill_tool"

        self.clearance_val = self.clearance_entry.get_value()
        self.margin_val = self.margin_entry.get_value()
        reference_method = self.reference_radio.get_value()

        # get the Gerber object on which the Copper fill will be inserted
        selection_index = self.grb_object_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.grb_object_combo.rootModelIndex())

        try:
            self.grb_object = model_index.internalPointer().obj
        except Exception as e:
            log.debug("ToolCopperFill.execute() --> %s" % str(e))
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Gerber object loaded ..."))
            return 'fail'

        if reference_method == 'itself':
            bound_obj_name = self.grb_object_combo.currentText()

            # Get reference object.
            try:
                self.ref_obj = self.app.collection.get_by_name(bound_obj_name)
            except Exception as e:
                self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), str(e)))
                return "Could not retrieve object: %s" % self.obj_name

            self.on_copper_fill(
                fill_obj=self.grb_object,
                c_val=self.clearance_val,
                margin=self.margin_val
            )

        elif reference_method == 'area':
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Click the start point of the area."))

            self.area_method = True

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

        elif reference_method == 'box':
            bound_obj_name = self.box_combo.currentText()

            # Get reference object.
            try:
                self.ref_obj = self.app.collection.get_by_name(bound_obj_name)
            except Exception as e:
                self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), bound_obj_name))
                return "Could not retrieve object: %s. Error: %s" % (bound_obj_name, str(e))

            self.on_copper_fill(
                fill_obj=self.grb_object,
                ref_obj=self.ref_obj,
                c_val=self.clearance_val,
                margin=self.margin_val
            )

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

        event_pos = self.app.plotcanvas.translate_coords(event_pos)

        # do clear area only for left mouse clicks
        if event.button == 1:
            if self.first_click is False:
                self.first_click = True
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("Click the end point of the filling area."))

                self.cursor_pos = self.app.plotcanvas.translate_coords(event_pos)
                if self.app.grid_status() == True:
                    self.cursor_pos = self.app.geo_editor.snap(event_pos[0], event_pos[1])
            else:
                self.app.inform.emit(_("Zone added. Click to start adding next zone or right click to finish."))

                if self.app.grid_status() == True:
                    curr_pos = self.app.geo_editor.snap(event_pos[0], event_pos[1])
                else:
                    curr_pos = (event_pos[0], event_pos[1])

                x0, y0 = self.cursor_pos[0], self.cursor_pos[1]
                x1, y1 = curr_pos[0], curr_pos[1]
                pt1 = (x0, y0)
                pt2 = (x1, y0)
                pt3 = (x1, y1)
                pt4 = (x0, y1)

                self.sel_rect.append(Polygon([pt1, pt2, pt3, pt4]))
                self.first_click = False
                return

        elif event.button == right_button and self.mouse_is_dragging == False:
            self.app.delete_selection_shape()
            self.area_method = False
            self.first_click = False

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

            if not isinstance(self.sel_rect, Iterable):
                self.sel_rect = [self.sel_rect]

            self.on_copper_fill(
                fill_obj=self.grb_object,
                ref_obj=self.sel_rect,
                c_val=self.clearance_val,
                margin=self.margin_val
            )

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

        curr_pos = self.app.plotcanvas.translate_coords(event_pos)

        # detect mouse dragging motion
        if event_is_dragging is True:
            self.mouse_is_dragging = True
        else:
            self.mouse_is_dragging = False

        # update the cursor position
        if self.app.grid_status() == True:
            # Update cursor
            curr_pos = self.app.geo_editor.snap(curr_pos[0], curr_pos[1])

            self.app.app_cursor.set_data(np.asarray([(curr_pos[0], curr_pos[1])]),
                                         symbol='++', edge_color=self.app.cursor_color_3D,
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

    def on_copper_fill(self, fill_obj, ref_obj=None, c_val=None, margin=None, run_threaded=True):
        """

        :param fill_obj:
        :param ref_obj:
        :param c_val:
        :param margin:
        :param run_threaded:
        :return:
        """

        if run_threaded:
            proc = self.app.proc_container.new('%s ...' % _("Copper filling"))
        else:
            self.app.proc_container.view.set_busy('%s ...' % _("Copper filling"))
            QtWidgets.QApplication.processEvents()

        # #####################################################################
        # ####### Read the parameters #########################################
        # #####################################################################

        log.debug("Copper Filling Tool started. Reading parameters.")
        self.app.inform.emit(_("Copper Filling Tool started. Reading parameters."))

        ref_selected = self.reference_radio.get_value()
        if c_val is None:
            c_val = float(self.app.defaults["tools_copperfill_clearance"])
        if margin is None:
            margin = float(self.app.defaults["tools_copperfill_margin"])

        # make sure that the source object solid geometry is an Iterable
        if not isinstance(self.grb_object.solid_geometry, Iterable):
            self.grb_object.solid_geometry = [self.grb_object.solid_geometry]

        # #########################################################################################
        # Prepare isolation polygon. This will create the clearance over the Gerber features ######
        # #########################################################################################
        log.debug("Copper Filling Tool. Preparing isolation polygons.")
        self.app.inform.emit(_("Copper Filling Tool. Preparing isolation polygons."))

        # variables to display the percentage of work done
        geo_len = 0
        try:
            for pol in self.grb_object.solid_geometry:
                geo_len += 1
        except TypeError:
            geo_len = 1

        old_disp_number = 0
        pol_nr = 0

        clearance_geometry = []
        try:
            for pol in self.grb_object.solid_geometry:
                if self.app.abort_flag:
                    # graceful abort requested by the user
                    raise FlatCAMApp.GracefulException

                clearance_geometry.append(
                    pol.buffer(c_val, int(int(self.geo_steps_per_circle) / 4))
                )

                pol_nr += 1
                disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 100]))

                if old_disp_number < disp_number <= 100:
                    self.app.proc_container.update_view_text(' %s ... %d%%' %
                                                             (_("Buffering"), int(disp_number)))
                    old_disp_number = disp_number
        except TypeError:
            # taking care of the case when the self.solid_geometry is just a single Polygon, not a list or a
            # MultiPolygon (not an iterable)
            clearance_geometry.append(
                self.grb_object.solid_geometry.buffer(c_val, int(int(self.geo_steps_per_circle) / 4))
            )

        self.app.proc_container.update_view_text(' %s' % _("Buffering"))
        clearance_geometry = unary_union(clearance_geometry)

        # #########################################################################################
        # Prepare the area to fill with copper. ###################################################
        # #########################################################################################
        log.debug("Copper Filling Tool. Preparing areas to fill with copper.")
        self.app.inform.emit(_("Copper Filling Tool. Preparing areas to fill with copper."))

        try:
            if ref_obj is None or ref_obj == 'itself':
                working_obj = fill_obj
            else:
                working_obj = ref_obj
        except Exception as e:
            log.debug("ToolCopperFIll.on_copper_fill() --> %s" % str(e))
            return 'fail'

        bounding_box = None
        if ref_selected == 'itself':
            geo_n = working_obj.solid_geometry

            try:
                if self.bbox_type_radio.get_value() == 'min':
                    if isinstance(geo_n, MultiPolygon):
                        env_obj = geo_n.convex_hull
                    elif (isinstance(geo_n, MultiPolygon) and len(geo_n) == 1) or \
                            (isinstance(geo_n, list) and len(geo_n) == 1) and isinstance(geo_n[0], Polygon):
                        env_obj = cascaded_union(geo_n)
                    else:
                        env_obj = cascaded_union(geo_n)
                        env_obj = env_obj.convex_hull
                else:
                    if isinstance(geo_n, Polygon) or \
                            (isinstance(geo_n, list) and len(geo_n) == 1) or \
                            (isinstance(geo_n, MultiPolygon) and len(geo_n) == 1):
                        env_obj = geo_n.buffer(0, join_style=base.JOIN_STYLE.mitre).exterior
                    elif isinstance(geo_n, MultiPolygon):
                        x0, y0, x1, y1 = geo_n.bounds
                        geo = box(x0, y0, x1, y1)
                        env_obj = geo.buffer(0, join_style=base.JOIN_STYLE.mitre)
                    else:
                        self.app.inform.emit(
                            '[ERROR_NOTCL] %s: %s' % (_("Geometry not supported for bounding box"), type(geo_n))
                        )
                        return 'fail'

                bounding_box = env_obj.buffer(distance=margin, join_style=base.JOIN_STYLE.mitre)
            except Exception as e:
                log.debug("ToolCopperFIll.on_copper_fill()  'itself'  --> %s" % str(e))
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("No object available."))
                return 'fail'

        elif ref_selected == 'area':
            geo_n = cascaded_union(working_obj)
            try:
                __ = iter(geo_n)
            except Exception as e:
                log.debug("ToolCopperFIll.on_copper_fill() 'area' --> %s" % str(e))
                geo_n = [geo_n]

            geo_buff_list = []
            for poly in geo_n:
                if self.app.abort_flag:
                    # graceful abort requested by the user
                    raise FlatCAMApp.GracefulException
                geo_buff_list.append(poly.buffer(distance=margin, join_style=base.JOIN_STYLE.mitre))

            bounding_box = cascaded_union(geo_buff_list)

        elif ref_selected == 'box':
            geo_n = working_obj.solid_geometry

            if isinstance(working_obj, FlatCAMGeometry):
                try:
                    __ = iter(geo_n)
                except Exception as e:
                    log.debug("ToolCopperFIll.on_copper_fill() 'box' --> %s" % str(e))
                    geo_n = [geo_n]

                geo_buff_list = []
                for poly in geo_n:
                    if self.app.abort_flag:
                        # graceful abort requested by the user
                        raise FlatCAMApp.GracefulException
                    geo_buff_list.append(poly.buffer(distance=margin, join_style=base.JOIN_STYLE.mitre))

                bounding_box = cascaded_union(geo_buff_list)
            elif isinstance(working_obj, FlatCAMGerber):
                geo_n = cascaded_union(geo_n).convex_hull
                bounding_box = cascaded_union(self.ncc_obj.solid_geometry).convex_hull.intersection(geo_n)
                bounding_box = bounding_box.buffer(distance=margin, join_style=base.JOIN_STYLE.mitre)
            else:
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("The reference object type is not supported."))
                return 'fail'

        log.debug("Copper Filling Tool. Finished creating areas to fill with copper.")

        self.app.inform.emit(_("Copper Filling Tool. Appending new geometry and buffering."))
        new_solid_geometry = bounding_box.difference(clearance_geometry)

        geo_list = self.grb_object.solid_geometry
        if isinstance(self.grb_object.solid_geometry, MultiPolygon):
            geo_list = list(self.grb_object.solid_geometry.geoms)

        if '0' not in self.grb_object.apertures:
            self.grb_object.apertures['0'] = dict()
            self.grb_object.apertures['0']['geometry'] = list()
            self.grb_object.apertures['0']['type'] = 'REG'
            self.grb_object.apertures['0']['size'] = 0.0

        try:
            for poly in new_solid_geometry:
                # append to the new solid geometry
                geo_list.append(poly)

                # append into the '0' aperture
                geo_elem = dict()
                geo_elem['solid'] = poly
                geo_elem['follow'] = poly.exterior
                self.grb_object.apertures['0']['geometry'].append(deepcopy(geo_elem))
        except TypeError:
            # append to the new solid geometry
            geo_list.append(new_solid_geometry)

            # append into the '0' aperture
            geo_elem = dict()
            geo_elem['solid'] = new_solid_geometry
            geo_elem['follow'] = new_solid_geometry.exterior
            self.grb_object.apertures['0']['geometry'].append(deepcopy(geo_elem))

        self.grb_object.solid_geometry = MultiPolygon(geo_list).buffer(0.0000001).buffer(-0.0000001)

        # update the source file with the new geometry:
        self.grb_object.source_file = self.app.export_gerber(obj_name=self.grb_object.options['name'], filename=None,
                                                             local_use=self.grb_object, use_thread=False)

        self.on_exit()
        self.app.inform.emit('[success] %s' % _("Copper Fill Tool done."))

    def replot(self, obj):
        def worker_task():
            with self.app.proc_container.new('%s...' % _("Plotting")):
                obj.plot()

        self.app.worker_task.emit({'fcn': worker_task, 'params': []})

    def on_exit(self):
        # plot the object
        self.replot(obj=self.grb_object)

        # update the bounding box values
        try:
            a, b, c, d = self.grb_object.bounds()
            self.grb_object.options['xmin'] = a
            self.grb_object.options['ymin'] = b
            self.grb_object.options['xmax'] = c
            self.grb_object.options['ymax'] = d
        except Exception as e:
            log.debug("ToolCopperFill.on_exit() bounds error --> %s" % str(e))

        # reset the variables
        self.grb_object = None
        self.ref_obj = None
        self.sel_rect = list()

        # Events ID
        self.mr = None
        self.mm = None

        # Mouse cursor positions
        self.mouse_is_dragging = False
        self.cursor_pos = (0, 0)
        self.first_click = False

        # if True it means we exited from tool in the middle of area adding therefore disconnect the events
        if self.area_method is True:
            self.app.delete_selection_shape()
            self.area_method = False

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

        self.app.call_source = "app"
        self.app.inform.emit('[success] %s' % _("Copper Fill Tool exit."))
