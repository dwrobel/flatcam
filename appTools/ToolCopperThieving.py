# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 10/25/2019                                         #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtCore, QtGui

from camlib import grace
from appTool import AppTool
from appGUI.GUIElements import FCDoubleSpinner, RadioSet, FCEntry, FCComboBox, FCLabel

import shapely.geometry.base as base
from shapely.ops import unary_union
from shapely.geometry import Polygon, MultiPolygon, Point, LineString
from shapely.geometry import box as box
import shapely.affinity as affinity

import logging
from copy import deepcopy
import numpy as np
from collections import Iterable

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class ToolCopperThieving(AppTool):
    work_finished = QtCore.pyqtSignal()

    def __init__(self, app):
        AppTool.__init__(self, app)

        self.app = app
        self.canvas = self.app.plotcanvas

        self.decimals = self.app.decimals
        self.units = self.app.defaults['units']

        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = ThievingUI(layout=self.layout, app=self.app)
        self.toolName = self.ui.toolName

        # Objects involved in Copper thieving
        self.grb_object = None
        self.ref_obj = None
        self.sel_rect = []
        self.sm_object = None

        # store the flattened geometry here:
        self.flat_geometry = []

        # Events ID
        self.mr = None
        self.mm = None

        # Mouse cursor positions
        self.mouse_is_dragging = False
        self.cursor_pos = (0, 0)
        self.first_click = False

        self.handlers_connected = False

        # Tool properties
        self.clearance_val = None
        self.margin_val = None
        self.geo_steps_per_circle = 128

        # Thieving geometry storage
        self.thief_solid_geometry = []

        # Robber bar geometry storage
        self.robber_geo = None
        self.robber_line = None

        self.rb_thickness = None

        # SIGNALS
        self.ui.ref_combo_type.currentIndexChanged.connect(self.on_ref_combo_type_change)
        self.ui.reference_radio.group_toggle_fn = self.on_toggle_reference
        self.ui.fill_type_radio.activated_custom.connect(self.on_thieving_type)

        self.ui.fill_button.clicked.connect(self.on_add_copper_thieving_click)
        self.ui.rb_button.clicked.connect(self.on_add_robber_bar_click)
        self.ui.ppm_button.clicked.connect(self.on_add_ppm_click)
        self.ui.reset_button.clicked.connect(self.set_tool_ui)

        self.work_finished.connect(self.on_new_pattern_plating_object)

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolCopperThieving()")

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

        AppTool.run(self)

        self.set_tool_ui()

        self.app.ui.notebook.setTabText(2, _("Copper Thieving Tool"))

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Alt+J', **kwargs)

    def set_tool_ui(self):
        self.units = self.app.defaults['units']
        self.geo_steps_per_circle = int(self.app.defaults["tools_copper_thieving_circle_steps"])

        self.ui.clearance_entry.set_value(float(self.app.defaults["tools_copper_thieving_clearance"]))
        self.ui.margin_entry.set_value(float(self.app.defaults["tools_copper_thieving_margin"]))
        self.ui.reference_radio.set_value(self.app.defaults["tools_copper_thieving_reference"])
        self.ui.bbox_type_radio.set_value(self.app.defaults["tools_copper_thieving_box_type"])
        self.ui.fill_type_radio.set_value(self.app.defaults["tools_copper_thieving_fill_type"])

        self.ui.area_entry.set_value(self.app.defaults["tools_copper_thieving_area"])
        self.ui.dot_dia_entry.set_value(self.app.defaults["tools_copper_thieving_dots_dia"])
        self.ui.dot_spacing_entry.set_value(self.app.defaults["tools_copper_thieving_dots_spacing"])
        self.ui.square_size_entry.set_value(self.app.defaults["tools_copper_thieving_squares_size"])
        self.ui.squares_spacing_entry.set_value(self.app.defaults["tools_copper_thieving_squares_spacing"])
        self.ui.line_size_entry.set_value(self.app.defaults["tools_copper_thieving_lines_size"])
        self.ui.lines_spacing_entry.set_value(self.app.defaults["tools_copper_thieving_lines_spacing"])

        self.ui.rb_margin_entry.set_value(self.app.defaults["tools_copper_thieving_rb_margin"])
        self.ui.rb_thickness_entry.set_value(self.app.defaults["tools_copper_thieving_rb_thickness"])
        self.ui.clearance_ppm_entry.set_value(self.app.defaults["tools_copper_thieving_mask_clearance"])
        self.ui.ppm_choice_radio.set_value(self.app.defaults["tools_copper_thieving_geo_choice"])

        # INIT SECTION
        self.handlers_connected = False
        self.robber_geo = None
        self.robber_line = None
        self.thief_solid_geometry = []

    def on_ref_combo_type_change(self):
        obj_type = self.ui.ref_combo_type.currentIndex()
        self.ui.ref_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.ui.ref_combo.setCurrentIndex(0)
        self.ui.ref_combo.obj_type = {
            _("Gerber"): "Gerber", _("Excellon"): "Excellon", _("Geometry"): "Geometry"
        }[self.ui.ref_combo_type.get_value()]

    def on_toggle_reference(self):
        if self.ui.reference_radio.get_value() == "itself" or self.ui.reference_radio.get_value() == "area":
            self.ui.ref_combo.hide()
            self.ui.ref_combo_label.hide()
            self.ui.ref_combo_type.hide()
            self.ui.ref_combo_type_label.hide()
        else:
            self.ui.ref_combo.show()
            self.ui.ref_combo_label.show()
            self.ui.ref_combo_type.show()
            self.ui.ref_combo_type_label.show()

        if self.ui.reference_radio.get_value() == "itself":
            self.ui.bbox_type_label.show()
            self.ui.bbox_type_radio.show()
        else:
            if self.ui.fill_type_radio.get_value() == 'line':
                self.ui.reference_radio.set_value('itself')
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("Lines Grid works only for 'itself' reference ..."))
                return

            self.ui.bbox_type_label.hide()
            self.ui.bbox_type_radio.hide()

    def on_thieving_type(self, choice):
        if choice == 'solid':
            self.ui.dots_frame.hide()
            self.ui.squares_frame.hide()
            self.ui.lines_frame.hide()
            self.app.inform.emit(_("Solid fill selected."))
        elif choice == 'dot':
            self.ui.dots_frame.show()
            self.ui.squares_frame.hide()
            self.ui.lines_frame.hide()
            self.app.inform.emit(_("Dots grid fill selected."))
        elif choice == 'square':
            self.ui.dots_frame.hide()
            self.ui.squares_frame.show()
            self.ui.lines_frame.hide()
            self.app.inform.emit(_("Squares grid fill selected."))
        else:
            if self.ui.reference_radio.get_value() != 'itself':
                self.ui.reference_radio.set_value('itself')
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("Lines Grid works only for 'itself' reference ..."))

            self.ui.dots_frame.hide()
            self.ui.squares_frame.hide()
            self.ui.lines_frame.show()

    def on_add_robber_bar_click(self):
        rb_margin = self.ui.rb_margin_entry.get_value()
        self.rb_thickness = self.ui.rb_thickness_entry.get_value()

        # get the Gerber object on which the Robber bar will be inserted
        selection_index = self.ui.grb_object_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.ui.grb_object_combo.rootModelIndex())

        try:
            self.grb_object = model_index.internalPointer().obj
        except Exception as e:
            log.debug("ToolCopperThieving.on_add_robber_bar_click() --> %s" % str(e))
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Gerber object loaded ..."))
            return

        try:
            outline_pol = self.grb_object.solid_geometry.envelope
        except (TypeError, AttributeError):
            outline_pol = MultiPolygon(self.grb_object.solid_geometry).envelope

        rb_distance = rb_margin + (self.rb_thickness / 2.0)
        self.robber_line = outline_pol.buffer(rb_distance).exterior

        self.robber_geo = self.robber_line.buffer(self.rb_thickness / 2.0)

        self.app.proc_container.update_view_text(' %s' % _("Append geometry"))

        new_apertures = deepcopy(self.grb_object.apertures)
        aperture_found = None
        for ap_id, ap_val in self.grb_object.apertures.items():
            if ap_val['type'] == 'C' and ap_val['size'] == self.rb_thickness:
                aperture_found = ap_id
                break

        if aperture_found:
            geo_elem = {'solid': self.robber_geo, 'follow': self.robber_line}
            new_apertures[aperture_found]['geometry'].append(deepcopy(geo_elem))
        else:
            ap_keys = list(new_apertures.keys())
            if ap_keys:
                new_apid = str(int(max(ap_keys)) + 1)
            else:
                new_apid = '10'

            new_apertures[new_apid] = {
                'type': 'C',
                'size': deepcopy(self.rb_thickness),
                'geometry': []
            }

            geo_elem = {'solid': self.robber_geo, 'follow': self.robber_line}
            new_apertures[new_apid]['geometry'].append(deepcopy(geo_elem))

        geo_obj = deepcopy(self.grb_object.solid_geometry)
        if isinstance(geo_obj, MultiPolygon):
            s_list = []
            for pol in geo_obj.geoms:
                s_list.append(pol)
            s_list.append(deepcopy(self.robber_geo))
            geo_obj = MultiPolygon(s_list)
        elif isinstance(geo_obj, list):
            geo_obj.append(deepcopy(self.robber_geo))
        elif isinstance(geo_obj, Polygon):
            geo_obj = MultiPolygon([geo_obj, deepcopy(self.robber_geo)])

        outname = '%s_%s' % (str(self.grb_object.options['name']), 'robber')

        def initialize(grb_obj, app_obj):
            grb_obj.options = {}
            for opt in self.grb_object.options:
                if opt != 'name':
                    grb_obj.options[opt] = deepcopy(self.grb_object.options[opt])
            grb_obj.options['name'] = outname
            grb_obj.multitool = False
            grb_obj.multigeo = False
            grb_obj.follow = deepcopy(self.grb_object.follow)
            grb_obj.apertures = new_apertures
            grb_obj.solid_geometry = unary_union(geo_obj)
            grb_obj.follow_geometry = deepcopy(self.grb_object.follow_geometry) + [deepcopy(self.robber_line)]

            app_obj.proc_container.update_view_text(' %s' % _("Append source file"))
            # update the source file with the new geometry:
            grb_obj.source_file = app_obj.f_handlers.export_gerber(obj_name=outname, filename=None, local_use=grb_obj,
                                                                   use_thread=False)

        ret_val = self.app.app_obj.new_object('gerber', outname, initialize, plot=True)
        self.app.proc_container.update_view_text(' %s' % '')
        if ret_val == 'fail':
            self.app.call_source = "app"
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed."))
            return

        self.on_exit()
        self.app.inform.emit('[success] %s' % _("Copper Thieving Tool done."))

    def on_add_copper_thieving_click(self):
        self.app.call_source = "copper_thieving_tool"

        self.clearance_val = self.ui.clearance_entry.get_value()
        self.margin_val = self.ui.margin_entry.get_value()
        reference_method = self.ui.reference_radio.get_value()

        # get the Gerber object on which the Copper thieving will be inserted
        selection_index = self.ui.grb_object_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.ui.grb_object_combo.rootModelIndex())

        try:
            self.grb_object = model_index.internalPointer().obj
        except Exception as e:
            log.debug("ToolCopperThieving.on_add_copper_thieving_click() --> %s" % str(e))
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Gerber object loaded ..."))
            return

        if reference_method == 'itself':
            bound_obj_name = self.ui.grb_object_combo.currentText()

            # Get reference object.
            try:
                self.ref_obj = self.app.collection.get_by_name(bound_obj_name)
            except Exception as e:
                self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), str(e)))
                return "Could not retrieve object: %s" % self.obj_name

            self.copper_thieving(
                thieving_obj=self.grb_object,
                c_val=self.clearance_val,
                margin=self.margin_val
            )

        elif reference_method == 'area':
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Click the start point of the area."))
            self.connect_event_handlers()

        elif reference_method == 'box':
            bound_obj_name = self.ui.ref_combo.currentText()

            # Get reference object.
            try:
                self.ref_obj = self.app.collection.get_by_name(bound_obj_name)
            except Exception:
                self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), bound_obj_name))
                return

            self.copper_thieving(
                thieving_obj=self.grb_object,
                ref_obj=self.ref_obj,
                c_val=self.clearance_val,
                margin=self.margin_val
            )

        # To be called after clicking on the plot.

    def on_mouse_release(self, event):
        if self.app.is_legacy is False:
            event_pos = event.pos
            # event_is_dragging = event.is_dragging
            right_button = 2
        else:
            event_pos = (event.xdata, event.ydata)
            # event_is_dragging = self.app.plotcanvas.is_dragging
            right_button = 3

        event_pos = self.app.plotcanvas.translate_coords(event_pos)

        # do clear area only for left mouse clicks
        if event.button == 1:
            if self.first_click is False:
                self.first_click = True
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("Click the end point of the filling area."))

                self.cursor_pos = self.app.plotcanvas.translate_coords(event_pos)
                if self.app.grid_status() is True:
                    self.cursor_pos = self.app.geo_editor.snap(event_pos[0], event_pos[1])
            else:
                self.app.inform.emit(_("Zone added. Click to start adding next zone or right click to finish."))
                self.app.delete_selection_shape()

                if self.app.grid_status() is True:
                    curr_pos = self.app.geo_editor.snap(event_pos[0], event_pos[1])
                else:
                    curr_pos = (event_pos[0], event_pos[1])

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
            self.disconnect_event_handlers()

            if len(self.sel_rect) == 0:
                return

            self.sel_rect = unary_union(self.sel_rect)

            if not isinstance(self.sel_rect, Iterable):
                self.sel_rect = [self.sel_rect]

            self.copper_thieving(
                thieving_obj=self.grb_object,
                ref_obj=self.sel_rect,
                c_val=self.clearance_val,
                margin=self.margin_val
            )

    # called on mouse move
    def on_mouse_move(self, event):
        if self.app.is_legacy is False:
            event_pos = event.pos
            event_is_dragging = event.is_dragging
            # right_button = 2
        else:
            event_pos = (event.xdata, event.ydata)
            event_is_dragging = self.app.plotcanvas.is_dragging
            # right_button = 3

        curr_pos = self.app.plotcanvas.translate_coords(event_pos)

        # detect mouse dragging motion
        if event_is_dragging is True:
            self.mouse_is_dragging = True
        else:
            self.mouse_is_dragging = False

        # update the cursor position
        if self.app.grid_status() is True:
            # Update cursor
            curr_pos = self.app.geo_editor.snap(curr_pos[0], curr_pos[1])

            self.app.app_cursor.set_data(np.asarray([(curr_pos[0], curr_pos[1])]),
                                         symbol='++', edge_color=self.app.cursor_color_3D,
                                         edge_width=self.app.defaults["global_cursor_width"],
                                         size=self.app.defaults["global_cursor_size"])

        if self.cursor_pos is None:
            self.cursor_pos = (0, 0)

        self.app.dx = curr_pos[0] - float(self.cursor_pos[0])
        self.app.dy = curr_pos[1] - float(self.cursor_pos[1])

        # # update the positions on status bar
        self.app.ui.position_label.setText("&nbsp;<b>X</b>: %.4f&nbsp;&nbsp;   "
                                           "<b>Y</b>: %.4f&nbsp;" % (curr_pos[0], curr_pos[1]))
        self.app.ui.rel_position_label.setText("<b>Dx</b>: %.4f&nbsp;&nbsp;  <b>Dy</b>: "
                                               "%.4f&nbsp;&nbsp;&nbsp;&nbsp;" % (self.app.dx, self.app.dy))

        units = self.app.defaults["units"].lower()
        self.app.plotcanvas.text_hud.text = \
            'Dx:\t{:<.4f} [{:s}]\nDy:\t{:<.4f} [{:s}]\n\nX:  \t{:<.4f} [{:s}]\nY:  \t{:<.4f} [{:s}]'.format(
                self.app.dx, units, self.app.dy, units, curr_pos[0], units, curr_pos[1], units)

        # draw the utility geometry
        if self.first_click:
            self.app.delete_selection_shape()
            self.app.draw_moving_selection_shape(old_coords=(self.cursor_pos[0], self.cursor_pos[1]),
                                                 coords=(curr_pos[0], curr_pos[1]))

    def copper_thieving(self, thieving_obj, ref_obj=None, c_val=None, margin=None, run_threaded=True):
        """

        :param thieving_obj:
        :param ref_obj:
        :param c_val:
        :param margin:
        :param run_threaded:
        :return:
        """

        if run_threaded:
            self.app.proc_container.new('%s ...' % _("Thieving"))
        else:
            QtWidgets.QApplication.processEvents()

        self.app.proc_container.view.set_busy('%s ...' % _("Thieving"))

        # #####################################################################
        # ####### Read the parameters #########################################
        # #####################################################################

        log.debug("Copper Thieving Tool started. Reading parameters.")
        self.app.inform.emit(_("Copper Thieving Tool started. Reading parameters."))

        ref_selected = self.ui.reference_radio.get_value()
        if c_val is None:
            c_val = float(self.app.defaults["tools_copper_thieving_clearance"])
        if margin is None:
            margin = float(self.app.defaults["tools_copper_thieving_margin"])
        min_area = self.ui.area_entry.get_value()

        fill_type = self.ui.fill_type_radio.get_value()
        dot_dia = self.ui.dot_dia_entry.get_value()
        dot_spacing = self.ui.dot_spacing_entry.get_value()
        square_size = self.ui.square_size_entry.get_value()
        square_spacing = self.ui.squares_spacing_entry.get_value()
        line_size = self.ui.line_size_entry.get_value()
        line_spacing = self.ui.lines_spacing_entry.get_value()

        # make sure that the source object solid geometry is an Iterable
        if not isinstance(self.grb_object.solid_geometry, Iterable):
            self.grb_object.solid_geometry = [self.grb_object.solid_geometry]

        def job_thread_thieving(tool_obj):
            # #########################################################################################################
            # Prepare isolation polygon. This will create the clearance over the Gerber features
            # #########################################################################################################
            log.debug("Copper Thieving Tool. Preparing isolation polygons.")
            tool_obj.app.inform.emit(_("Copper Thieving Tool. Preparing isolation polygons."))

            # variables to display the percentage of work done
            try:
                geo_len = len(tool_obj.grb_object.solid_geometry)
            except TypeError:
                geo_len = 1

            old_disp_number = 0
            pol_nr = 0

            # #########################################################################################################
            # apply the clearance value to the geometry
            # #########################################################################################################
            clearance_geometry = []
            try:
                for pol in tool_obj.grb_object.solid_geometry:
                    if tool_obj.app.abort_flag:
                        # graceful abort requested by the user
                        raise grace

                    clearance_geometry.append(
                        pol.buffer(c_val, int(int(tool_obj.geo_steps_per_circle) / 4))
                    )

                    pol_nr += 1
                    disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 100]))

                    if old_disp_number < disp_number <= 100:
                        msg = ' %s ... %d%%' % (_("Thieving"), int(disp_number))
                        tool_obj.app.proc_container.update_view_text(msg)
                        old_disp_number = disp_number
            except TypeError:
                # taking care of the case when the self.solid_geometry is just a single Polygon, not a list or a
                # MultiPolygon (not an iterable)
                clearance_geometry.append(
                    tool_obj.grb_object.solid_geometry.buffer(c_val, int(int(tool_obj.geo_steps_per_circle) / 4))
                )

            tool_obj.app.proc_container.update_view_text(' %s ...' % _("Buffering"))
            clearance_geometry = unary_union(clearance_geometry)

            # #########################################################################################################
            # Prepare the area to fill with copper.
            # #########################################################################################################
            log.debug("Copper Thieving Tool. Preparing areas to fill with copper.")
            tool_obj.app.inform.emit(_("Copper Thieving Tool. Preparing areas to fill with copper."))

            try:
                if ref_obj is None or ref_obj == 'itself':
                    working_obj = thieving_obj
                else:
                    working_obj = ref_obj
            except Exception as e:
                log.debug("ToolCopperThieving.copper_thieving() --> %s" % str(e))
                return 'fail'

            tool_obj.app.proc_container.update_view_text(' %s' % _("Working..."))

            # #########################################################################################################
            # generate the bounding box geometry
            # #########################################################################################################
            if ref_selected == 'itself':
                geo_n = deepcopy(working_obj.solid_geometry)

                try:
                    if tool_obj.ui.bbox_type_radio.get_value() == 'min':
                        if isinstance(geo_n, MultiPolygon):
                            env_obj = geo_n.convex_hull
                        elif (isinstance(geo_n, MultiPolygon) and len(geo_n) == 1) or \
                                (isinstance(geo_n, list) and len(geo_n) == 1) and isinstance(geo_n[0], Polygon):
                            env_obj = unary_union(geo_n)
                        else:
                            env_obj = unary_union(geo_n)
                            env_obj = env_obj.convex_hull
                        bounding_box = env_obj.buffer(distance=margin, join_style=base.JOIN_STYLE.mitre)
                    else:
                        if isinstance(geo_n, Polygon):
                            bounding_box = geo_n.buffer(distance=margin, join_style=base.JOIN_STYLE.mitre)
                        elif isinstance(geo_n, list):
                            geo_n = MultiPolygon(geo_n)
                            x0, y0, x1, y1 = geo_n.bounds
                            geo = box(x0, y0, x1, y1)
                            bounding_box = geo.buffer(distance=margin, join_style=base.JOIN_STYLE.mitre)
                        elif isinstance(geo_n, MultiPolygon):
                            x0, y0, x1, y1 = geo_n.bounds
                            geo = box(x0, y0, x1, y1)
                            bounding_box = geo.buffer(distance=margin, join_style=base.JOIN_STYLE.mitre)
                        else:
                            tool_obj.app.inform.emit(
                                '[ERROR_NOTCL] %s: %s' % (_("Geometry not supported for"), type(geo_n))
                            )
                            return 'fail'

                except Exception as e:
                    log.debug("ToolCopperFIll.copper_thieving()  'itself'  --> %s" % str(e))
                    tool_obj.app.inform.emit('[ERROR_NOTCL] %s' % _("No object available."))
                    return 'fail'
            elif ref_selected == 'area':
                geo_buff_list = []
                try:
                    for poly in working_obj:
                        if tool_obj.app.abort_flag:
                            # graceful abort requested by the user
                            raise grace
                        geo_buff_list.append(poly.buffer(distance=margin, join_style=base.JOIN_STYLE.mitre))
                except TypeError:
                    geo_buff_list.append(working_obj.buffer(distance=margin, join_style=base.JOIN_STYLE.mitre))

                bounding_box = MultiPolygon(geo_buff_list)
            else:   # ref_selected == 'box'
                geo_n = working_obj.solid_geometry

                if working_obj.kind == 'geometry':
                    try:
                        __ = iter(geo_n)
                    except Exception as e:
                        log.debug("ToolCopperFIll.copper_thieving() 'box' --> %s" % str(e))
                        geo_n = [geo_n]

                    geo_buff_list = []
                    for poly in geo_n:
                        if tool_obj.app.abort_flag:
                            # graceful abort requested by the user
                            raise grace
                        geo_buff_list.append(poly.buffer(distance=margin, join_style=base.JOIN_STYLE.mitre))

                    bounding_box = unary_union(geo_buff_list)
                elif working_obj.kind == 'gerber':
                    geo_n = unary_union(geo_n).convex_hull
                    bounding_box = unary_union(thieving_obj.solid_geometry).convex_hull.intersection(geo_n)
                    bounding_box = bounding_box.buffer(distance=margin, join_style=base.JOIN_STYLE.mitre)
                else:
                    tool_obj.app.inform.emit('[ERROR_NOTCL] %s' % _("The reference object type is not supported."))
                    return 'fail'

            log.debug("Copper Thieving Tool. Finished creating areas to fill with copper.")

            tool_obj.app.inform.emit(_("Copper Thieving Tool. Appending new geometry and buffering."))

            # #########################################################################################################
            # Generate solid filling geometry. Effectively it's a NEGATIVE of the source object
            # #########################################################################################################
            tool_obj.thief_solid_geometry = bounding_box.difference(clearance_geometry)

            temp_geo = []
            try:
                for s_geo in tool_obj.thief_solid_geometry:
                    if s_geo.area >= min_area:
                        temp_geo.append(s_geo)
            except TypeError:
                if tool_obj.thief_solid_geometry.area >= min_area:
                    temp_geo.append(tool_obj.thief_solid_geometry)

            tool_obj.thief_solid_geometry = temp_geo

            # #########################################################################################################
            # apply the 'margin' to the bounding box geometry
            # #########################################################################################################
            try:
                bounding_box = thieving_obj.solid_geometry.envelope.buffer(
                    distance=margin,
                    join_style=base.JOIN_STYLE.mitre
                )
            except AttributeError:
                bounding_box = MultiPolygon(thieving_obj.solid_geometry).envelope.buffer(
                    distance=margin,
                    join_style=base.JOIN_STYLE.mitre
                )
            x0, y0, x1, y1 = bounding_box.bounds

            # #########################################################################################################
            # add Thieving geometry
            # #########################################################################################################
            tool_obj.app.proc_container.update_view_text(' %s' % _("Create geometry"))

            if fill_type == 'dot' or fill_type == 'square':
                # build the MultiPolygon of dots/squares that will fill the entire bounding box
                thieving_list = []

                if fill_type == 'dot':
                    radius = dot_dia / 2.0
                    new_x = x0 + radius
                    new_y = y0 + radius
                    while new_x <= x1 - radius:
                        while new_y <= y1 - radius:
                            dot_geo = Point((new_x, new_y)).buffer(radius, resolution=64)
                            thieving_list.append(dot_geo)
                            new_y += dot_dia + dot_spacing
                        new_x += dot_dia + dot_spacing
                        new_y = y0 + radius
                else:
                    h_size = square_size / 2.0
                    new_x = x0 + h_size
                    new_y = y0 + h_size
                    while new_x <= x1 - h_size:
                        while new_y <= y1 - h_size:
                            a, b, c, d = (Point((new_x, new_y)).buffer(h_size)).bounds
                            square_geo = box(a, b, c, d)
                            thieving_list.append(square_geo)
                            new_y += square_size + square_spacing
                        new_x += square_size + square_spacing
                        new_y = y0 + h_size

                thieving_box_geo = MultiPolygon(thieving_list)
                dx = bounding_box.centroid.x - thieving_box_geo.centroid.x
                dy = bounding_box.centroid.y - thieving_box_geo.centroid.y

                thieving_box_geo = affinity.translate(thieving_box_geo, xoff=dx, yoff=dy)

                try:
                    _it = iter(thieving_box_geo)
                except TypeError:
                    thieving_box_geo = [thieving_box_geo]

                thieving_geo = []
                for dot_geo in thieving_box_geo:
                    for geo_t in tool_obj.thief_solid_geometry:
                        if dot_geo.within(geo_t):
                            thieving_geo.append(dot_geo)

                tool_obj.thief_solid_geometry = thieving_geo

            if fill_type == 'line':
                half_thick_line = line_size / 2.0

                # create a thick polygon-line that surrounds the copper features
                outline_geometry = []
                try:
                    for pol in tool_obj.grb_object.solid_geometry:
                        if tool_obj.app.abort_flag:
                            # graceful abort requested by the user
                            raise grace

                        outline_geometry.append(
                            pol.buffer(c_val+half_thick_line, int(int(tool_obj.geo_steps_per_circle) / 4))
                        )

                        pol_nr += 1
                        disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 100]))

                        if old_disp_number < disp_number <= 100:
                            msg = ' %s ... %d%%' % (_("Buffering"), int(disp_number))
                            tool_obj.app.proc_container.update_view_text(msg)
                            old_disp_number = disp_number
                except TypeError:
                    # taking care of the case when the self.solid_geometry is just a single Polygon, not a list or a
                    # MultiPolygon (not an iterable)
                    outline_geometry.append(
                        tool_obj.grb_object.solid_geometry.buffer(
                            c_val+half_thick_line,
                            int(int(tool_obj.geo_steps_per_circle) / 4)
                        )
                    )

                tool_obj.app.proc_container.update_view_text(' %s' % _("Buffering"))
                outline_geometry = unary_union(outline_geometry)

                outline_line = []
                try:
                    for geo_o in outline_geometry:
                        outline_line.append(
                            geo_o.exterior.buffer(
                                half_thick_line, resolution=int(int(tool_obj.geo_steps_per_circle) / 4)
                            )
                        )
                except TypeError:
                    outline_line.append(
                        outline_geometry.exterior.buffer(
                            half_thick_line, resolution=int(int(tool_obj.geo_steps_per_circle) / 4)
                        )
                    )

                outline_geometry = unary_union(outline_line)

                # create a polygon-line that surrounds in the inside the bounding box polygon of the target Gerber
                box_outline_geo = box(x0, y0, x1, y1).buffer(-half_thick_line)
                box_outline_geo_exterior = box_outline_geo.exterior
                box_outline_geometry = box_outline_geo_exterior.buffer(
                    half_thick_line,
                    resolution=int(int(tool_obj.geo_steps_per_circle) / 4)
                )

                bx0, by0, bx1, by1 = box_outline_geo.bounds
                thieving_lines_geo = []
                new_x = bx0
                new_y = by0
                while new_x <= x1 - half_thick_line:
                    line_geo = LineString([(new_x, by0), (new_x, by1)]).buffer(
                        half_thick_line,
                        resolution=int(int(tool_obj.geo_steps_per_circle) / 4)
                    )
                    thieving_lines_geo.append(line_geo)
                    new_x += line_size + line_spacing

                while new_y <= y1 - half_thick_line:
                    line_geo = LineString([(bx0, new_y), (bx1, new_y)]).buffer(
                        half_thick_line,
                        resolution=int(int(tool_obj.geo_steps_per_circle) / 4)
                    )
                    thieving_lines_geo.append(line_geo)
                    new_y += line_size + line_spacing

                # merge everything together
                diff_lines_geo = []
                for line_poly in thieving_lines_geo:
                    rest_line = line_poly.difference(clearance_geometry)
                    diff_lines_geo.append(rest_line)
                tool_obj.flatten([outline_geometry, box_outline_geometry, diff_lines_geo])
                tool_obj.thief_solid_geometry = tool_obj.flat_geometry

            tool_obj.app.proc_container.update_view_text(' %s' % _("Append geometry"))
            # create a list of the source geometry
            geo_list = deepcopy(tool_obj.grb_object.solid_geometry)
            if isinstance(tool_obj.grb_object.solid_geometry, MultiPolygon):
                geo_list = list(geo_list.geoms)

            # create a new dictionary to hold the source object apertures allowing us to tamper with without altering
            # the original source object's apertures
            new_apertures = deepcopy(tool_obj.grb_object.apertures)
            if '0' not in new_apertures:
                new_apertures['0'] = {
                    'type': 'REG',
                    'size': 0.0,
                    'geometry': []
                }

            # add the thieving geometry in the '0' aperture of the new_apertures dict
            try:
                for poly in tool_obj.thief_solid_geometry:
                    # append to the new solid geometry
                    geo_list.append(poly)

                    # append into the '0' aperture
                    geo_elem = {'solid': poly, 'follow': poly.exterior}
                    new_apertures['0']['geometry'].append(deepcopy(geo_elem))
            except TypeError:
                # append to the new solid geometry
                geo_list.append(tool_obj.thief_solid_geometry)

                # append into the '0' aperture
                geo_elem = {'solid': tool_obj.new_solid_geometry, 'follow': tool_obj.new_solid_geometry.exterior}
                new_apertures['0']['geometry'].append(deepcopy(geo_elem))

            # prepare also the solid_geometry for the new object having the thieving geometry
            new_solid_geo = MultiPolygon(geo_list).buffer(0.0000001).buffer(-0.0000001)

            outname = '%s_%s' % (str(self.grb_object.options['name']), 'thief')

            def initialize(grb_obj, app_obj):
                grb_obj.options = {}
                for opt in self.grb_object.options:
                    if opt != 'name':
                        grb_obj.options[opt] = deepcopy(self.grb_object.options[opt])
                grb_obj.options['name'] = outname
                grb_obj.multitool = False
                grb_obj.multigeo = False
                grb_obj.follow = deepcopy(self.grb_object.follow)
                grb_obj.apertures = new_apertures
                grb_obj.solid_geometry = deepcopy(new_solid_geo)
                grb_obj.follow_geometry = deepcopy(self.grb_object.follow_geometry)

                app_obj.proc_container.update_view_text(' %s' % _("Append source file"))
                grb_obj.source_file = app_obj.f_handlers.export_gerber(obj_name=outname, filename=None,
                                                                       local_use=grb_obj,
                                                                       use_thread=False)

            ret_val = self.app.app_obj.new_object('gerber', outname, initialize, plot=True)
            tool_obj.app.proc_container.update_view_text(' %s' % '')
            if ret_val == 'fail':
                self.app.call_source = "app"
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed."))
                return

            tool_obj.on_exit()
            tool_obj.app.inform.emit('[success] %s' % _("Copper Thieving Tool done."))

        if run_threaded:
            self.app.worker_task.emit({'fcn': job_thread_thieving, 'params': [self]})
        else:
            job_thread_thieving(self)

    def on_add_ppm_click(self):
        run_threaded = True

        if run_threaded:
            self.app.proc_container.new('%s ...' % _("P-Plating Mask"))
        else:
            QtWidgets.QApplication.processEvents()

        self.app.proc_container.view.set_busy('%s ...' % _("P-Plating Mask"))

        if run_threaded:
            self.app.worker_task.emit({'fcn': self.on_new_pattern_plating_object, 'params': []})
        else:
            self.on_new_pattern_plating_object()

    def on_new_pattern_plating_object(self):
        ppm_clearance = self.ui.clearance_ppm_entry.get_value()
        geo_choice = self.ui.ppm_choice_radio.get_value()
        rb_thickness = self.rb_thickness

        # get the Gerber object on which the Copper thieving will be inserted
        selection_index = self.ui.sm_object_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.ui.sm_object_combo.rootModelIndex())

        try:
            self.sm_object = model_index.internalPointer().obj
        except Exception as e:
            log.debug("ToolCopperThieving.on_add_ppm_click() --> %s" % str(e))
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Gerber object loaded ..."))
            return

        self.app.proc_container.update_view_text(' %s' % _("Append PP-M geometry"))
        geo_list = deepcopy(self.sm_object.solid_geometry)
        if isinstance(geo_list, MultiPolygon):
            geo_list = list(geo_list.geoms)

        # create a copy of the source apertures so we can manipulate them without altering the source object
        new_apertures = deepcopy(self.sm_object.apertures)

        # if the clearance is negative apply it to the original soldermask geometry too
        if ppm_clearance < 0:
            temp_geo_list = []
            for geo in geo_list:
                temp_geo_list.append(geo.buffer(ppm_clearance))
            geo_list = temp_geo_list

            # squash former geometry in apertures
            for ap_id in new_apertures:
                for k in new_apertures[ap_id]:
                    if k == 'geometry':
                        new_apertures[ap_id]['geometry'] = []

            # then add a buffered geometry
            for ap_id in new_apertures:
                if 'geometry' in self.sm_object.apertures[ap_id]:
                    new_geo_list = []
                    for geo_el in self.sm_object.apertures[ap_id]['geometry']:
                        new_el = {
                            'solid': geo_el['solid'].buffer(ppm_clearance) if 'solid' in geo_el else [],
                            'follow': geo_el['follow'] if 'follow' in geo_el else [],
                            'clear': geo_el['clear'] if 'clear' in geo_el else []
                        }
                        new_geo_list.append(deepcopy(new_el))
                    new_apertures[ap_id]['geometry'] = deepcopy(new_geo_list)

        # calculate its own plated area (from the solder mask object)
        plated_area = 0.0
        for geo in geo_list:
            plated_area += geo.area

        thieving_solid_geo = deepcopy(self.thief_solid_geometry)
        robber_solid_geo = deepcopy(self.robber_geo)
        robber_line = deepcopy(self.robber_line)

        # store here the chosen follow geometry
        new_follow_geo = deepcopy(self.sm_object.follow_geometry)

        # if we have copper thieving geometry, add it
        if thieving_solid_geo and geo_choice in ['b', 't']:
            # add to the total the thieving geometry area, if chosen
            for geo in thieving_solid_geo:
                plated_area += geo.area

            if '0' not in new_apertures:
                new_apertures['0'] = {
                    'type': 'REG',
                    'size': 0.0,
                    'geometry': []
                }

            try:
                for poly in thieving_solid_geo:
                    poly_b = poly.buffer(ppm_clearance)

                    # append to the new solid geometry
                    geo_list.append(poly_b)

                    # append into the '0' aperture
                    geo_elem = {
                        'solid': poly_b,
                        'follow': poly_b.exterior
                    }
                    new_apertures['0']['geometry'].append(deepcopy(geo_elem))
            except TypeError:
                # append to the new solid geometry
                assert isinstance(thieving_solid_geo, Polygon)
                geo_list.append(thieving_solid_geo.buffer(ppm_clearance))

                # append into the '0' aperture
                geo_elem = {
                    'solid': thieving_solid_geo.buffer(ppm_clearance),
                    'follow': thieving_solid_geo.buffer(ppm_clearance).exterior
                }
                new_apertures['0']['geometry'].append(deepcopy(geo_elem))

        # if we have robber bar geometry, add it
        if robber_solid_geo and geo_choice in ['b', 'r']:
            # add to the total the robber bar geometry are, if chose
            plated_area += robber_solid_geo.area

            # add to the follow_geomery
            new_follow_geo.append(robber_line)

            aperture_found = None
            for ap_id, ap_val in new_apertures.items():
                if ap_val['type'] == 'C' and ap_val['size'] == self.rb_thickness + ppm_clearance:
                    aperture_found = ap_id
                    break

            if aperture_found:
                geo_elem = {'solid': robber_solid_geo, 'follow': robber_line}
                new_apertures[aperture_found]['geometry'].append(deepcopy(geo_elem))
            else:
                ap_keys = list(new_apertures.keys())
                max_apid = int(max(ap_keys))
                if ap_keys and max_apid != 0:
                    new_apid = str(max_apid + 1)
                else:
                    new_apid = '10'

                new_apertures[new_apid] = {
                    'type': 'C',
                    'size': rb_thickness + ppm_clearance,
                    'geometry': []
                }

                geo_elem = {
                    'solid': robber_solid_geo.buffer(ppm_clearance),
                    'follow': deepcopy(robber_line)
                }
                new_apertures[new_apid]['geometry'].append(deepcopy(geo_elem))

            geo_list.append(robber_solid_geo.buffer(ppm_clearance))

        # and then set the total plated area value to the GUI element
        self.ui.plated_area_entry.set_value(plated_area)

        new_solid_geometry = MultiPolygon(geo_list).buffer(0.0000001).buffer(-0.0000001)

        def obj_init(grb_obj, app_obj):
            grb_obj.options = {}
            for opt in self.sm_object.options:
                if opt != 'name':
                    grb_obj.options[opt] = deepcopy(self.sm_object.options[opt])
            grb_obj.options['name'] = outname
            grb_obj.multitool = False
            grb_obj.source_file = []
            grb_obj.multigeo = False
            grb_obj.follow = False
            grb_obj.follow_geometry = deepcopy(new_follow_geo)
            grb_obj.apertures = deepcopy(new_apertures)
            grb_obj.solid_geometry = deepcopy(new_solid_geometry)

            app_obj.proc_container.update_view_text(' %s' % _("Append source file"))
            # update the source file with the new geometry:
            grb_obj.source_file = app_obj.f_handlers.export_gerber(obj_name=outname, filename=None, local_use=grb_obj,
                                                                   use_thread=False)
            app_obj.proc_container.update_view_text(' %s' % '')

        # Object name
        obj_name, separatpr, obj_extension = self.sm_object.options['name'].rpartition('.')
        outname = '%s_%s.%s' % (obj_name, 'plating_mask', obj_extension)

        ret_val = self.app.app_obj.new_object('gerber', outname, obj_init, autoselected=False)
        if ret_val == 'fail':
            self.app.call_source = "app"
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed."))
            return

        # Register recent file
        self.app.file_opened.emit("gerber", outname)

        self.on_exit()
        self.app.inform.emit('[success] %s' % _("Generating Pattern Plating Mask done."))

    def replot(self, obj, run_thread=True):
        def worker_task():
            with self.app.proc_container.new('%s...' % _("Plotting")):
                obj.plot()
                self.app.app_obj.object_plotted.emit(obj)

        if run_thread:
            self.app.worker_task.emit({'fcn': worker_task, 'params': []})
        else:
            worker_task()

    def on_exit(self, obj=None):
        # plot the objects
        if obj:
            try:
                for ob in obj:
                    self.replot(obj=ob)
            except (AttributeError, TypeError):
                self.replot(obj=obj)
            except Exception:
                return

        # reset the variables
        self.sel_rect = []

        # Events ID
        self.mr = None
        self.mm = None

        # Mouse cursor positions
        self.mouse_is_dragging = False
        self.cursor_pos = (0, 0)
        self.first_click = False

        # if True it means we exited from tool in the middle of area adding therefore disconnect the events
        if self.handlers_connected is True:
            self.app.delete_selection_shape()

        self.disconnect_event_handlers()

        self.app.call_source = "app"
        self.app.inform.emit('[success] %s' % _("Copper Thieving Tool exit."))

    def connect_event_handlers(self):
        if self.handlers_connected is False:
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
            self.handlers_connected = True

    def disconnect_event_handlers(self):
        if self.handlers_connected is True:
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
            self.handlers_connected = False

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


class ThievingUI:

    toolName = _("Copper Thieving Tool")

    def __init__(self, layout, app):
        self.app = app
        self.decimals = self.app.decimals
        self.units = self.app.defaults['units']
        self.layout = layout

        # ## Title
        title_label = FCLabel("%s" % self.toolName)
        title_label.setStyleSheet("""
                                QLabel
                                {
                                    font-size: 16px;
                                    font-weight: bold;
                                }
                                """)
        self.layout.addWidget(title_label)
        self.layout.addWidget(FCLabel(""))

        # ## Grid Layout
        i_grid_lay = QtWidgets.QGridLayout()
        self.layout.addLayout(i_grid_lay)
        i_grid_lay.setColumnStretch(0, 0)
        i_grid_lay.setColumnStretch(1, 1)

        self.grb_object_combo = FCComboBox()
        self.grb_object_combo.setModel(self.app.collection)
        self.grb_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.grb_object_combo.is_last = True
        self.grb_object_combo.obj_type = 'Gerber'

        self.grbobj_label = FCLabel("<b>%s:</b>" % _("GERBER"))
        self.grbobj_label.setToolTip(
            _("Gerber Object to which will be added a copper thieving.")
        )

        i_grid_lay.addWidget(self.grbobj_label, 0, 0)
        i_grid_lay.addWidget(self.grb_object_combo, 1, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        i_grid_lay.addWidget(separator_line, 2, 0, 1, 2)

        # ## Grid Layout
        grid_lay = QtWidgets.QGridLayout()
        self.layout.addLayout(grid_lay)
        grid_lay.setColumnStretch(0, 0)
        grid_lay.setColumnStretch(1, 1)

        self.copper_fill_label = FCLabel('<b>%s</b>' % _('Parameters'))
        self.copper_fill_label.setToolTip(
            _("Parameters used for this tool.")
        )
        grid_lay.addWidget(self.copper_fill_label, 0, 0, 1, 2)

        # CLEARANCE #
        self.clearance_label = FCLabel('%s:' % _("Clearance"))
        self.clearance_label.setToolTip(
            _("This set the distance between the copper thieving components\n"
              "(the polygon fill may be split in multiple polygons)\n"
              "and the copper traces in the Gerber file.")
        )
        self.clearance_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.clearance_entry.set_range(0.00001, 10000.0000)
        self.clearance_entry.set_precision(self.decimals)
        self.clearance_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.clearance_label, 2, 0)
        grid_lay.addWidget(self.clearance_entry, 2, 1)

        # MARGIN #
        self.margin_label = FCLabel('%s:' % _("Margin"))
        self.margin_label.setToolTip(
            _("Bounding box margin.")
        )
        self.margin_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.margin_entry.set_range(0.0, 10000.0000)
        self.margin_entry.set_precision(self.decimals)
        self.margin_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.margin_label, 4, 0)
        grid_lay.addWidget(self.margin_entry, 4, 1)

        # Area #
        area_hlay = QtWidgets.QHBoxLayout()
        self.area_label = FCLabel('%s:' % _("Area"))
        self.area_label.setToolTip(
            _("Thieving areas with area less then this value will not be added.")
        )
        self.area_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.area_entry.set_range(0.0, 10000.0000)
        self.area_entry.set_precision(self.decimals)
        self.area_entry.setSingleStep(0.1)
        self.area_entry.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)

        if self.units.upper() == 'MM':
            units_area_label = FCLabel('%s<sup>2</sup>' % _("mm"))
        else:
            units_area_label = FCLabel('%s<sup>2</sup>' % _("in"))

        area_hlay.addWidget(self.area_entry)
        area_hlay.addWidget(units_area_label)

        grid_lay.addWidget(self.area_label, 6, 0)
        grid_lay.addLayout(area_hlay, 6, 1)

        # Reference #
        self.reference_radio = RadioSet([
            {'label': _('Itself'), 'value': 'itself'},
            {"label": _("Area Selection"), "value": "area"},
            {'label': _("Reference Object"), 'value': 'box'}
        ], orientation='vertical', stretch=False)
        self.reference_label = FCLabel(_("Reference:"))
        self.reference_label.setToolTip(
            _("- 'Itself' - the copper thieving extent is based on the object extent.\n"
              "- 'Area Selection' - left mouse click to start selection of the area to be filled.\n"
              "- 'Reference Object' - will do copper thieving within the area specified by another object.")
        )
        grid_lay.addWidget(self.reference_label, 8, 0)
        grid_lay.addWidget(self.reference_radio, 8, 1)

        self.ref_combo_type_label = FCLabel('%s:' % _("Ref. Type"))
        self.ref_combo_type_label.setToolTip(
            _("The type of FlatCAM object to be used as copper thieving reference.\n"
              "It can be Gerber, Excellon or Geometry.")
        )
        self.ref_combo_type = FCComboBox()
        self.ref_combo_type.addItems([_("Gerber"), _("Excellon"), _("Geometry")])

        grid_lay.addWidget(self.ref_combo_type_label, 10, 0)
        grid_lay.addWidget(self.ref_combo_type, 10, 1)

        self.ref_combo_label = FCLabel('%s:' % _("Ref. Object"))
        self.ref_combo_label.setToolTip(
            _("The FlatCAM object to be used as non copper clearing reference.")
        )
        self.ref_combo = FCComboBox()
        self.ref_combo.setModel(self.app.collection)
        self.ref_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.ref_combo.is_last = True
        self.ref_combo.obj_type = {
            _("Gerber"): "Gerber", _("Excellon"): "Excellon", _("Geometry"): "Geometry"
        }[self.ref_combo_type.get_value()]

        grid_lay.addWidget(self.ref_combo_label, 12, 0)
        grid_lay.addWidget(self.ref_combo, 12, 1)

        self.ref_combo.hide()
        self.ref_combo_label.hide()
        self.ref_combo_type.hide()
        self.ref_combo_type_label.hide()

        # Bounding Box Type #
        self.bbox_type_label = FCLabel('%s:' % _("Box Type"))
        self.bbox_type_label.setToolTip(
            _("- 'Rectangular' - the bounding box will be of rectangular shape.\n"
              "- 'Minimal' - the bounding box will be the convex hull shape.")
        )
        self.bbox_type_radio = RadioSet([
            {'label': _('Rectangular'), 'value': 'rect'},
            {"label": _("Minimal"), "value": "min"}
        ], stretch=False)

        grid_lay.addWidget(self.bbox_type_label, 14, 0)
        grid_lay.addWidget(self.bbox_type_radio, 14, 1)
        self.bbox_type_label.hide()
        self.bbox_type_radio.hide()

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line, 16, 0, 1, 2)

        # Fill Type
        self.fill_type_radio = RadioSet([
            {'label': _('Solid'), 'value': 'solid'},
            {"label": _("Dots Grid"), "value": "dot"},
            {"label": _("Squares Grid"), "value": "square"},
            {"label": _("Lines Grid"), "value": "line"}
        ], orientation='vertical', stretch=False)
        self.fill_type_label = FCLabel(_("Fill Type:"))
        self.fill_type_label.setToolTip(
            _("- 'Solid' - copper thieving will be a solid polygon.\n"
              "- 'Dots Grid' - the empty area will be filled with a pattern of dots.\n"
              "- 'Squares Grid' - the empty area will be filled with a pattern of squares.\n"
              "- 'Lines Grid' - the empty area will be filled with a pattern of lines.")
        )
        grid_lay.addWidget(self.fill_type_label, 18, 0)
        grid_lay.addWidget(self.fill_type_radio, 18, 1)

        # DOTS FRAME
        self.dots_frame = QtWidgets.QFrame()
        self.dots_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.dots_frame)
        dots_grid = QtWidgets.QGridLayout()
        dots_grid.setColumnStretch(0, 0)
        dots_grid.setColumnStretch(1, 1)
        dots_grid.setContentsMargins(0, 0, 0, 0)
        self.dots_frame.setLayout(dots_grid)
        self.dots_frame.hide()

        self.dots_label = FCLabel('<b>%s</b>:' % _("Dots Grid Parameters"))
        dots_grid.addWidget(self.dots_label, 0, 0, 1, 2)

        # Dot diameter #
        self.dotdia_label = FCLabel('%s:' % _("Dia"))
        self.dotdia_label.setToolTip(
            _("Dot diameter in Dots Grid.")
        )
        self.dot_dia_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.dot_dia_entry.set_range(0.0, 10000.0000)
        self.dot_dia_entry.set_precision(self.decimals)
        self.dot_dia_entry.setSingleStep(0.1)

        dots_grid.addWidget(self.dotdia_label, 1, 0)
        dots_grid.addWidget(self.dot_dia_entry, 1, 1)

        # Dot spacing #
        self.dotspacing_label = FCLabel('%s:' % _("Spacing"))
        self.dotspacing_label.setToolTip(
            _("Distance between each two dots in Dots Grid.")
        )
        self.dot_spacing_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.dot_spacing_entry.set_range(0.0, 10000.0000)
        self.dot_spacing_entry.set_precision(self.decimals)
        self.dot_spacing_entry.setSingleStep(0.1)

        dots_grid.addWidget(self.dotspacing_label, 2, 0)
        dots_grid.addWidget(self.dot_spacing_entry, 2, 1)

        # SQUARES FRAME
        self.squares_frame = QtWidgets.QFrame()
        self.squares_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.squares_frame)
        squares_grid = QtWidgets.QGridLayout()
        squares_grid.setColumnStretch(0, 0)
        squares_grid.setColumnStretch(1, 1)
        squares_grid.setContentsMargins(0, 0, 0, 0)
        self.squares_frame.setLayout(squares_grid)
        self.squares_frame.hide()

        self.squares_label = FCLabel('<b>%s</b>:' % _("Squares Grid Parameters"))
        squares_grid.addWidget(self.squares_label, 0, 0, 1, 2)

        # Square Size #
        self.square_size_label = FCLabel('%s:' % _("Size"))
        self.square_size_label.setToolTip(
            _("Square side size in Squares Grid.")
        )
        self.square_size_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.square_size_entry.set_range(0.0, 10000.0000)
        self.square_size_entry.set_precision(self.decimals)
        self.square_size_entry.setSingleStep(0.1)

        squares_grid.addWidget(self.square_size_label, 1, 0)
        squares_grid.addWidget(self.square_size_entry, 1, 1)

        # Squares spacing #
        self.squares_spacing_label = FCLabel('%s:' % _("Spacing"))
        self.squares_spacing_label.setToolTip(
            _("Distance between each two squares in Squares Grid.")
        )
        self.squares_spacing_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.squares_spacing_entry.set_range(0.0, 10000.0000)
        self.squares_spacing_entry.set_precision(self.decimals)
        self.squares_spacing_entry.setSingleStep(0.1)

        squares_grid.addWidget(self.squares_spacing_label, 2, 0)
        squares_grid.addWidget(self.squares_spacing_entry, 2, 1)

        # LINES FRAME
        self.lines_frame = QtWidgets.QFrame()
        self.lines_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.lines_frame)
        lines_grid = QtWidgets.QGridLayout()
        lines_grid.setColumnStretch(0, 0)
        lines_grid.setColumnStretch(1, 1)
        lines_grid.setContentsMargins(0, 0, 0, 0)
        self.lines_frame.setLayout(lines_grid)
        self.lines_frame.hide()

        self.lines_label = FCLabel('<b>%s</b>:' % _("Lines Grid Parameters"))
        lines_grid.addWidget(self.lines_label, 0, 0, 1, 2)

        # Square Size #
        self.line_size_label = FCLabel('%s:' % _("Size"))
        self.line_size_label.setToolTip(
            _("Line thickness size in Lines Grid.")
        )
        self.line_size_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.line_size_entry.set_range(0.0, 10000.0000)
        self.line_size_entry.set_precision(self.decimals)
        self.line_size_entry.setSingleStep(0.1)

        lines_grid.addWidget(self.line_size_label, 1, 0)
        lines_grid.addWidget(self.line_size_entry, 1, 1)

        # Lines spacing #
        self.lines_spacing_label = FCLabel('%s:' % _("Spacing"))
        self.lines_spacing_label.setToolTip(
            _("Distance between each two lines in Lines Grid.")
        )
        self.lines_spacing_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.lines_spacing_entry.set_range(0.0, 10000.0000)
        self.lines_spacing_entry.set_precision(self.decimals)
        self.lines_spacing_entry.setSingleStep(0.1)

        lines_grid.addWidget(self.lines_spacing_label, 2, 0)
        lines_grid.addWidget(self.lines_spacing_entry, 2, 1)

        # ## Insert Copper Thieving
        self.fill_button = QtWidgets.QPushButton(_("Insert Copper thieving"))
        self.fill_button.setIcon(QtGui.QIcon(self.app.resource_location + '/copperfill32.png'))
        self.fill_button.setToolTip(
            _("Will add a polygon (may be split in multiple parts)\n"
              "that will surround the actual Gerber traces at a certain distance.")
        )
        self.fill_button.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        self.layout.addWidget(self.fill_button)

        # ## Grid Layout
        grid_lay_1 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid_lay_1)
        grid_lay_1.setColumnStretch(0, 0)
        grid_lay_1.setColumnStretch(1, 1)
        grid_lay_1.setColumnStretch(2, 0)

        separator_line_1 = QtWidgets.QFrame()
        separator_line_1.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line_1.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay_1.addWidget(separator_line_1, 0, 0, 1, 3)

        grid_lay_1.addWidget(FCLabel(''))

        self.robber_bar_label = FCLabel('<b>%s</b>' % _('Robber Bar Parameters'))
        self.robber_bar_label.setToolTip(
            _("Parameters used for the robber bar.\n"
              "Robber bar = copper border to help in pattern hole plating.")
        )
        grid_lay_1.addWidget(self.robber_bar_label, 2, 0, 1, 3)

        # ROBBER BAR MARGIN #
        self.rb_margin_label = FCLabel('%s:' % _("Margin"))
        self.rb_margin_label.setToolTip(
            _("Bounding box margin for robber bar.")
        )
        self.rb_margin_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.rb_margin_entry.set_range(-10000.0000, 10000.0000)
        self.rb_margin_entry.set_precision(self.decimals)
        self.rb_margin_entry.setSingleStep(0.1)

        grid_lay_1.addWidget(self.rb_margin_label, 4, 0)
        grid_lay_1.addWidget(self.rb_margin_entry, 4, 1, 1, 2)

        # THICKNESS #
        self.rb_thickness_label = FCLabel('%s:' % _("Thickness"))
        self.rb_thickness_label.setToolTip(
            _("The robber bar thickness.")
        )
        self.rb_thickness_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.rb_thickness_entry.set_range(0.0000, 10000.0000)
        self.rb_thickness_entry.set_precision(self.decimals)
        self.rb_thickness_entry.setSingleStep(0.1)

        grid_lay_1.addWidget(self.rb_thickness_label, 6, 0)
        grid_lay_1.addWidget(self.rb_thickness_entry, 6, 1, 1, 2)

        # ## Insert Robber Bar
        self.rb_button = QtWidgets.QPushButton(_("Insert Robber Bar"))
        self.rb_button.setIcon(QtGui.QIcon(self.app.resource_location + '/robber32.png'))
        self.rb_button.setToolTip(
            _("Will add a polygon with a defined thickness\n"
              "that will surround the actual Gerber object\n"
              "at a certain distance.\n"
              "Required when doing holes pattern plating.")
        )
        self.rb_button.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        grid_lay_1.addWidget(self.rb_button, 8, 0, 1, 3)

        separator_line_2 = QtWidgets.QFrame()
        separator_line_2.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line_2.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay_1.addWidget(separator_line_2, 10, 0, 1, 3)

        self.patern_mask_label = FCLabel('<b>%s</b>' % _('Pattern Plating Mask'))
        self.patern_mask_label.setToolTip(
            _("Generate a mask for pattern plating.")
        )
        grid_lay_1.addWidget(self.patern_mask_label, 12, 0, 1, 3)

        self.sm_obj_label = FCLabel("%s:" % _("Select Soldermask object"))
        self.sm_obj_label.setToolTip(
            _("Gerber Object with the soldermask.\n"
              "It will be used as a base for\n"
              "the pattern plating mask.")
        )

        self.sm_object_combo = FCComboBox()
        self.sm_object_combo.setModel(self.app.collection)
        self.sm_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.sm_object_combo.is_last = True
        self.sm_object_combo.obj_type = 'Gerber'

        grid_lay_1.addWidget(self.sm_obj_label, 14, 0, 1, 3)
        grid_lay_1.addWidget(self.sm_object_combo, 16, 0, 1, 3)

        # Openings CLEARANCE #
        self.clearance_ppm_label = FCLabel('%s:' % _("Clearance"))
        self.clearance_ppm_label.setToolTip(
            _("The distance between the possible copper thieving elements\n"
              "and/or robber bar and the actual openings in the mask.")
        )
        self.clearance_ppm_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.clearance_ppm_entry.set_range(-10000.0000, 10000.0000)
        self.clearance_ppm_entry.set_precision(self.decimals)
        self.clearance_ppm_entry.setSingleStep(0.1)

        grid_lay_1.addWidget(self.clearance_ppm_label, 18, 0)
        grid_lay_1.addWidget(self.clearance_ppm_entry, 18, 1, 1, 2)

        # Plated area
        self.plated_area_label = FCLabel('%s:' % _("Plated area"))
        self.plated_area_label.setToolTip(
            _("The area to be plated by pattern plating.\n"
              "Basically is made from the openings in the plating mask.\n\n"
              "<<WARNING>> - the calculated area is actually a bit larger\n"
              "due of the fact that the soldermask openings are by design\n"
              "a bit larger than the copper pads, and this area is\n"
              "calculated from the soldermask openings.")
        )
        self.plated_area_entry = FCEntry()
        self.plated_area_entry.setDisabled(True)

        if self.units.upper() == 'MM':
            self.units_area_label = FCLabel('%s<sup>2</sup>' % _("mm"))
        else:
            self.units_area_label = FCLabel('%s<sup>2</sup>' % _("in"))

        grid_lay_1.addWidget(self.plated_area_label, 20, 0)
        grid_lay_1.addWidget(self.plated_area_entry, 20, 1)
        grid_lay_1.addWidget(self.units_area_label, 20, 2)

        # Include geometry
        self.ppm_choice_label = FCLabel('%s:' % _("Add"))
        self.ppm_choice_label.setToolTip(
            _("Choose which additional geometry to include, if available.")
        )
        self.ppm_choice_radio = RadioSet([
            {"label": _("Both"), "value": "b"},
            {'label': _('Thieving'), 'value': 't'},
            {"label": _("Robber bar"), "value": "r"},
            {"label": _("None"), "value": "n"}
        ], orientation='vertical', stretch=False)
        grid_lay_1.addWidget(self.ppm_choice_label, 22, 0)
        grid_lay_1.addWidget(self.ppm_choice_radio, 22, 1, 1, 2)

        # ## Pattern Plating Mask
        self.ppm_button = QtWidgets.QPushButton(_("Generate pattern plating mask"))
        self.ppm_button.setIcon(QtGui.QIcon(self.app.resource_location + '/pattern32.png'))
        self.ppm_button.setToolTip(
            _("Will add to the soldermask gerber geometry\n"
              "the geometries of the copper thieving and/or\n"
              "the robber bar if those were generated.")
        )
        self.ppm_button.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        grid_lay_1.addWidget(self.ppm_button, 24, 0, 1, 3)

        self.layout.addStretch()

        # ## Reset Tool
        self.reset_button = QtWidgets.QPushButton(_("Reset Tool"))
        self.reset_button.setIcon(QtGui.QIcon(self.app.resource_location + '/reset32.png'))
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

        # #################################### FINSIHED GUI ###########################
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
