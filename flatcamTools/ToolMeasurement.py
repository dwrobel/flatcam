# ########################################################## ##
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ########################################################## ##

from FlatCAMTool import FlatCAMTool
from FlatCAMObj import *
from flatcamGUI.VisPyVisuals import *

from math import sqrt

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class Measurement(FlatCAMTool):

    toolName = _("Measurement")

    def __init__(self, app):
        FlatCAMTool.__init__(self, app)

        self.app = app
        self.canvas = self.app.plotcanvas
        self.units = self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().lower()

        # ## Title
        title_label = QtWidgets.QLabel("<font size=4><b>%s</b></font><br>" % self.toolName)
        self.layout.addWidget(title_label)

        # ## Form Layout
        form_layout = QtWidgets.QFormLayout()
        self.layout.addLayout(form_layout)

        self.units_label = QtWidgets.QLabel(_("Units:"))
        self.units_label.setToolTip(_("Those are the units in which the distance is measured."))
        self.units_value = QtWidgets.QLabel("%s" % str({'mm': _("METRIC (mm)"), 'in': _("INCH (in)")}[self.units]))
        self.units_value.setDisabled(True)

        self.start_label = QtWidgets.QLabel("<b>%s</b> %s:" % (_('Start'), _('Coords')))
        self.start_label.setToolTip(_("This is measuring Start point coordinates."))

        self.stop_label = QtWidgets.QLabel("<b>%s</b> %s:" % (_('Stop'), _('Coords')))
        self.stop_label.setToolTip(_("This is the measuring Stop point coordinates."))

        self.distance_x_label = QtWidgets.QLabel(_("Dx:"))
        self.distance_x_label.setToolTip(_("This is the distance measured over the X axis."))

        self.distance_y_label = QtWidgets.QLabel(_("Dy:"))
        self.distance_y_label.setToolTip(_("This is the distance measured over the Y axis."))

        self.total_distance_label = QtWidgets.QLabel("<b>%s:</b>" % _('DISTANCE'))
        self.total_distance_label.setToolTip(_("This is the point to point Euclidian distance."))

        self.start_entry = FCEntry()
        self.start_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.start_entry.setToolTip(_("This is measuring Start point coordinates."))

        self.stop_entry = FCEntry()
        self.stop_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.stop_entry.setToolTip(_("This is the measuring Stop point coordinates."))

        self.distance_x_entry = FCEntry()
        self.distance_x_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.distance_x_entry.setToolTip(_("This is the distance measured over the X axis."))

        self.distance_y_entry = FCEntry()
        self.distance_y_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.distance_y_entry.setToolTip(_("This is the distance measured over the Y axis."))

        self.total_distance_entry = FCEntry()
        self.total_distance_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.total_distance_entry.setToolTip(_("This is the point to point Euclidian distance."))

        self.measure_btn = QtWidgets.QPushButton(_("Measure"))
        # self.measure_btn.setFixedWidth(70)
        self.layout.addWidget(self.measure_btn)

        form_layout.addRow(self.units_label, self.units_value)
        form_layout.addRow(self.start_label, self.start_entry)
        form_layout.addRow(self.stop_label, self.stop_entry)
        form_layout.addRow(self.distance_x_label, self.distance_x_entry)
        form_layout.addRow(self.distance_y_label, self.distance_y_entry)
        form_layout.addRow(self.total_distance_label, self.total_distance_entry)

        # initial view of the layout
        self.start_entry.set_value('(0, 0)')
        self.stop_entry.set_value('(0, 0)')
        self.distance_x_entry.set_value('0')
        self.distance_y_entry.set_value('0')
        self.total_distance_entry.set_value('0')

        self.layout.addStretch()

        # store here the first click and second click of the measurement process
        self.points = []

        self.rel_point1 = None
        self.rel_point2 = None

        self.active = False
        self.clicked_meas = None
        self.meas_line = None

        self.original_call_source = 'app'

        # VisPy visuals
        self.sel_shapes = ShapeCollection(parent=self.app.plotcanvas.vispy_canvas.view.scene, layers=1)

        self.measure_btn.clicked.connect(self.activate_measure_tool)

    def run(self, toggle=False):
        self.app.report_usage("ToolMeasurement()")

        self.points[:] = []

        self.rel_point1 = None
        self.rel_point2 = None

        if self.app.tool_tab_locked is True:
            return

        self.app.ui.notebook.setTabText(2, _("Meas. Tool"))

        # if the splitter is hidden, display it
        if self.app.ui.splitter.sizes()[0] == 0:
            self.app.ui.splitter.setSizes([1, 1])
        if toggle:
            pass

        if self.active is False:
            self.activate_measure_tool()
        else:
            self.deactivate_measure_tool()

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, shortcut='CTRL+M', **kwargs)

    def set_tool_ui(self):
        # Remove anything else in the GUI
        self.app.ui.tool_scroll_area.takeWidget()

        # Put ourself in the GUI
        self.app.ui.tool_scroll_area.setWidget(self)

        # Switch notebook to tool page
        self.app.ui.notebook.setCurrentWidget(self.app.ui.tool_tab)
        self.units = self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().lower()

        self.app.command_active = "Measurement"

        # initial view of the layout
        self.start_entry.set_value('(0, 0)')
        self.stop_entry.set_value('(0, 0)')

        self.distance_x_entry.set_value('0')
        self.distance_y_entry.set_value('0')
        self.total_distance_entry.set_value('0')
        log.debug("Measurement Tool --> tool initialized")

    def activate_measure_tool(self):
        # ENABLE the Measuring TOOL
        self.active = True

        self.clicked_meas = 0
        self.original_call_source = copy(self.app.call_source)

        self.app.inform.emit(_("MEASURING: Click on the Start point ..."))
        self.units = self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().lower()

        # we can connect the app mouse events to the measurement tool
        # NEVER DISCONNECT THOSE before connecting some other handlers; it breaks something in VisPy
        self.canvas.vis_connect('mouse_move', self.on_mouse_move_meas)
        self.canvas.vis_connect('mouse_release', self.on_mouse_click_release)

        # we disconnect the mouse/key handlers from wherever the measurement tool was called
        if self.app.call_source == 'app':
            self.canvas.vis_disconnect('mouse_move', self.app.on_mouse_move_over_plot)
            self.canvas.vis_disconnect('mouse_press', self.app.on_mouse_click_over_plot)
            self.canvas.vis_disconnect('mouse_release', self.app.on_mouse_click_release_over_plot)
        elif self.app.call_source == 'geo_editor':
            self.canvas.vis_disconnect('mouse_move', self.app.geo_editor.on_canvas_move)
            self.canvas.vis_disconnect('mouse_press', self.app.geo_editor.on_canvas_click)
            self.canvas.vis_disconnect('mouse_release', self.app.geo_editor.on_geo_click_release)
        elif self.app.call_source == 'exc_editor':
            self.canvas.vis_disconnect('mouse_move', self.app.exc_editor.on_canvas_move)
            self.canvas.vis_disconnect('mouse_press', self.app.exc_editor.on_canvas_click)
            self.canvas.vis_disconnect('mouse_release', self.app.exc_editor.on_exc_click_release)
        elif self.app.call_source == 'grb_editor':
            self.canvas.vis_disconnect('mouse_move', self.app.grb_editor.on_canvas_move)
            self.canvas.vis_disconnect('mouse_press', self.app.grb_editor.on_canvas_click)
            self.canvas.vis_disconnect('mouse_release', self.app.grb_editor.on_grb_click_release)

        self.app.call_source = 'measurement'

        self.set_tool_ui()

    def deactivate_measure_tool(self):
        # DISABLE the Measuring TOOL
        self.active = False
        self.points = []

        self.app.call_source = copy(self.original_call_source)
        if self.original_call_source == 'app':
            self.canvas.vis_connect('mouse_move', self.app.on_mouse_move_over_plot)
            self.canvas.vis_connect('mouse_press', self.app.on_mouse_click_over_plot)
            self.canvas.vis_connect('mouse_release', self.app.on_mouse_click_release_over_plot)
        elif self.original_call_source == 'geo_editor':
            self.canvas.vis_connect('mouse_move', self.app.geo_editor.on_canvas_move)
            self.canvas.vis_connect('mouse_press', self.app.geo_editor.on_canvas_click)
            self.canvas.vis_connect('mouse_release', self.app.geo_editor.on_geo_click_release)
        elif self.original_call_source == 'exc_editor':
            self.canvas.vis_connect('mouse_move', self.app.exc_editor.on_canvas_move)
            self.canvas.vis_connect('mouse_press', self.app.exc_editor.on_canvas_click)
            self.canvas.vis_connect('mouse_release', self.app.exc_editor.on_exc_click_release)
        elif self.original_call_source == 'grb_editor':
            self.canvas.vis_connect('mouse_move', self.app.grb_editor.on_canvas_move)
            self.canvas.vis_connect('mouse_press', self.app.grb_editor.on_canvas_click)
            self.canvas.vis_connect('mouse_release', self.app.grb_editor.on_grb_click_release)

        # disconnect the mouse/key events from functions of measurement tool
        self.canvas.vis_disconnect('mouse_move', self.on_mouse_move_meas)
        self.canvas.vis_disconnect('mouse_release', self.on_mouse_click_release)

        # self.app.ui.notebook.setTabText(2, _("Tools"))
        # self.app.ui.notebook.setCurrentWidget(self.app.ui.project_tab)

        self.app.command_active = None

        # delete the measuring line
        self.delete_shape()

        log.debug("Measurement Tool --> exit tool")

    def on_mouse_click_release(self, event):
        # mouse click releases will be accepted only if the left button is clicked
        # this is necessary because right mouse click or middle mouse click
        # are used for panning on the canvas
        log.debug("Measuring Tool --> mouse click release")

        if event.button == 1:
            pos_canvas = self.canvas.vispy_canvas.translate_coords(event.pos)
            # if GRID is active we need to get the snapped positions
            if self.app.grid_status():
                pos = self.app.geo_editor.snap(pos_canvas[0], pos_canvas[1])
            else:
                pos = pos_canvas[0], pos_canvas[1]
            self.points.append(pos)

            # Reset here the relative coordinates so there is a new reference on the click position
            if self.rel_point1 is None:
                self.app.ui.rel_position_label.setText("<b>Dx</b>: %.4f&nbsp;&nbsp;  <b>Dy</b>: "
                                                       "%.4f&nbsp;&nbsp;&nbsp;&nbsp;" % (0.0, 0.0))
                self.rel_point1 = pos
            else:
                self.rel_point2 = copy(self.rel_point1)
                self.rel_point1 = pos

            if len(self.points) == 1:
                self.start_entry.set_value("(%.4f, %.4f)" % pos)
                self.app.inform.emit(_("MEASURING: Click on the Destination point ..."))

            if len(self.points) == 2:
                dx = self.points[1][0] - self.points[0][0]
                dy = self.points[1][1] - self.points[0][1]
                d = sqrt(dx ** 2 + dy ** 2)
                self.stop_entry.set_value("(%.4f, %.4f)" % pos)

                self.app.inform.emit(_("MEASURING: Result D(x) = {d_x} | D(y) = {d_y} | Distance = {d_z}").format(
                    d_x='%4f' % abs(dx), d_y='%4f' % abs(dy), d_z='%4f' % abs(d)))

                self.distance_x_entry.set_value('%.4f' % abs(dx))
                self.distance_y_entry.set_value('%.4f' % abs(dy))
                self.total_distance_entry.set_value('%.4f' % abs(d))
                self.app.ui.rel_position_label.setText("<b>Dx</b>: %.4f&nbsp;&nbsp;  <b>Dy</b>: "
                                                       "%.4f&nbsp;&nbsp;&nbsp;&nbsp;" % (pos[0], pos[1]))
                self.deactivate_measure_tool()

    def on_mouse_move_meas(self, event):
        try:  # May fail in case mouse not within axes
            pos_canvas = self.app.plotcanvas.vispy_canvas.translate_coords(event.pos)
            if self.app.grid_status():
                pos = self.app.geo_editor.snap(pos_canvas[0], pos_canvas[1])
                self.app.app_cursor.enabled = True
                # Update cursor
                self.app.app_cursor.set_data(np.asarray([(pos[0], pos[1])]),
                                             symbol='++', edge_color='black', size=20)
            else:
                pos = (pos_canvas[0], pos_canvas[1])
                self.app.app_cursor.enabled = False

            if self.rel_point1 is not None:
                dx = pos[0] - self.rel_point1[0]
                dy = pos[1] - self.rel_point1[1]
            else:
                dx = pos[0]
                dy = pos[1]

            self.app.ui.position_label.setText("&nbsp;&nbsp;&nbsp;&nbsp;<b>X</b>: %.4f&nbsp;&nbsp;   "
                                               "<b>Y</b>: %.4f" % (pos[0], pos[1]))
            self.app.ui.rel_position_label.setText("<b>Dx</b>: %.4f&nbsp;&nbsp;  <b>Dy</b>: "
                                                   "%.4f&nbsp;&nbsp;&nbsp;&nbsp;" % (dx, dy))
            # update utility geometry
            if len(self.points) == 1:
                self.utility_geometry(pos=pos)
        except Exception as e:
            self.app.ui.position_label.setText("")
            self.app.ui.rel_position_label.setText("")

    def utility_geometry(self, pos):
        # first delete old shape
        self.delete_shape()
        # second draw the new shape of the utility geometry
        self.meas_line = LineString([pos, self.points[0]])
        self.sel_shapes.add(self.meas_line, color='black', update=True, layer=0, tolerance=None)

    def delete_shape(self):
        self.sel_shapes.clear()
        self.sel_shapes.redraw()

    def set_meas_units(self, units):
        self.meas.units_label.setText("[" + self.app.options["units"].lower() + "]")

# end of file
