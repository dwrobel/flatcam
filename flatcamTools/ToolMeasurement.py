############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
############################################################

from FlatCAMTool import FlatCAMTool
from FlatCAMObj import *
from flatcamGUI.VisPyVisuals import *

from math import sqrt

import gettext
import FlatCAMTranslation as fcTranslate

fcTranslate.apply_language('strings')
import builtins
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class Measurement(FlatCAMTool):

    toolName = _("Measurement")

    def __init__(self, app):
        FlatCAMTool.__init__(self, app)

        self.app = app

        self.units = self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().lower()

        ## Title
        title_label = QtWidgets.QLabel("<font size=4><b>%s</b></font><br>" % self.toolName)
        self.layout.addWidget(title_label)

        ## Form Layout
        form_layout = QtWidgets.QFormLayout()
        self.layout.addLayout(form_layout)


        self.units_label = QtWidgets.QLabel(_("Units:"))
        self.units_label.setToolTip(_("Those are the units in which the distance is measured."))
        self.units_value = QtWidgets.QLabel("%s" % str({'mm': "METRIC (mm)", 'in': "INCH (in)"}[self.units]))
        self.units_value.setDisabled(True)

        self.start_label = QtWidgets.QLabel("<b>%s</b> %s:" % (_('Start'), _('Coords')))
        self.start_label.setToolTip(_("This is measuring Start point coordinates."))

        self.stop_label = QtWidgets.QLabel("<b>%s</b> %s:" % (_('Stop'), _('Coords')))
        self.stop_label.setToolTip(_("This is the measuring Stop point coordinates."))

        self.distance_x_label = QtWidgets.QLabel("Dx:")
        self.distance_x_label.setToolTip(_("This is the distance measured over the X axis."))

        self.distance_y_label = QtWidgets.QLabel("Dy:")
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

        self.clicked_meas = 0

        self.point1 = None
        self.point2 = None

        # the default state is disabled for the Move command
        # self.setVisible(False)
        self.active = 0

        # VisPy visuals
        self.sel_shapes = ShapeCollection(parent=self.app.plotcanvas.vispy_canvas.view.scene, layers=1)

        self.measure_btn.clicked.connect(lambda: self.on_measure(activate=True))

    def run(self, toggle=False):
        self.app.report_usage("ToolMeasurement()")

        if self.app.tool_tab_locked is True:
            return

        self.app.ui.notebook.setTabText(2, _("Meas. Tool"))

        # if the splitter is hidden, display it, else hide it but only if the current widget is the same
        if self.app.ui.splitter.sizes()[0] == 0:
            self.app.ui.splitter.setSizes([1, 1])

        self.on_measure(activate=True)

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

    def activate(self):
        # we disconnect the mouse/key handlers from wherever the measurement tool was called
        self.app.plotcanvas.vis_disconnect('key_press')
        self.app.plotcanvas.vis_disconnect('mouse_double_click')
        self.app.plotcanvas.vis_disconnect('mouse_move')
        self.app.plotcanvas.vis_disconnect('mouse_press')
        self.app.plotcanvas.vis_disconnect('mouse_release')
        self.app.plotcanvas.vis_disconnect('key_release')

        # we can safely connect the app mouse events to the measurement tool
        self.app.plotcanvas.vis_connect('mouse_move', self.on_mouse_move_meas)
        self.app.plotcanvas.vis_connect('mouse_release', self.on_mouse_click)
        self.app.plotcanvas.vis_connect('key_release', self.on_key_release_meas)

        self.set_tool_ui()

    def deactivate(self):
        # disconnect the mouse/key events from functions of measurement tool
        self.app.plotcanvas.vis_disconnect('mouse_move')
        self.app.plotcanvas.vis_disconnect('mouse_press')
        self.app.plotcanvas.vis_disconnect('key_release')

        # reconnect the mouse/key events to the functions from where the tool was called
        self.app.plotcanvas.vis_connect('key_press', self.app.ui.keyPressEvent)
        self.app.plotcanvas.vis_connect('mouse_double_click', self.app.on_double_click_over_plot)

        if self.app.call_source == 'app':
            self.app.plotcanvas.vis_connect('mouse_move', self.app.on_mouse_move_over_plot)
            self.app.plotcanvas.vis_connect('mouse_press', self.app.on_mouse_click_over_plot)
            self.app.plotcanvas.vis_connect('mouse_release', self.app.on_mouse_click_release_over_plot)
        elif self.app.call_source == 'geo_editor':
            self.app.geo_editor.canvas.vis_connect('mouse_move', self.app.geo_editor.on_canvas_move)
            self.app.geo_editor.canvas.vis_connect('mouse_press', self.app.geo_editor.on_canvas_click)
            # self.app.geo_editor.canvas.vis_connect('key_press', self.app.geo_editor.on_canvas_key)
            self.app.geo_editor.canvas.vis_connect('mouse_release', self.app.geo_editor.on_canvas_click_release)
        elif self.app.call_source == 'exc_editor':
            self.app.exc_editor.canvas.vis_connect('mouse_move', self.app.exc_editor.on_canvas_move)
            self.app.exc_editor.canvas.vis_connect('mouse_press', self.app.exc_editor.on_canvas_click)
            # self.app.exc_editor.canvas.vis_connect('key_press', self.app.exc_editor.on_canvas_key)
            self.app.exc_editor.canvas.vis_connect('mouse_release', self.app.exc_editor.on_canvas_click_release)
        elif self.app.call_source == 'grb_editor':
            self.app.grb_editor.canvas.vis_connect('mouse_move', self.app.grb_editor.on_canvas_move)
            self.app.grb_editor.canvas.vis_connect('mouse_press', self.app.grb_editor.on_canvas_click)
            # self.app.grb_editor.canvas.vis_connect('key_press', self.app.grb_editor.on_canvas_key)
            self.app.grb_editor.canvas.vis_connect('mouse_release', self.app.grb_editor.on_canvas_click_release)

        self.app.ui.notebook.setTabText(2, _("Tools"))

    def on_measure(self, signal=None, activate=None):
        if activate is False or activate is None:
            # DISABLE the Measuring TOOL
            self.deactivate()

            self.app.call_source = 'measurement'
            self.app.command_active = None

            # delete the measuring line
            self.delete_shape()

            log.debug("Measurement Tool --> exit tool")
        elif activate is True:
            # ENABLE the Measuring TOOL
            self.clicked_meas = 0

            self.app.inform.emit(_("MEASURING: Click on the Start point ..."))
            self.units = self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().lower()

            self.activate()
            log.debug("Measurement Tool --> tool initialized")

    def on_key_release_meas(self, event):
        if event.key == 'escape':
            # abort the measurement action
            self.on_measure(activate=False)
            self.app.inform.emit(_("Measurement Tool exit..."))
            return

        if event.key == 'G':
            # toggle grid status
            self.app.ui.grid_snap_btn.trigger()
            return

    def on_mouse_click(self, event):
        # mouse click releases will be accepted only if the left button is clicked
        # this is necessary because right mouse click or middle mouse click
        # are used for panning on the canvas

        if event.button == 1:
            pos_canvas = self.app.plotcanvas.vispy_canvas.translate_coords(event.pos)

            if self.clicked_meas == 0:
                self.clicked_meas = 1

                # if GRID is active we need to get the snapped positions
                if self.app.grid_status() == True:
                    pos = self.app.geo_editor.snap(pos_canvas[0], pos_canvas[1])
                else:
                    pos = pos_canvas[0], pos_canvas[1]

                self.point1 = pos
                self.start_entry.set_value("(%.4f, %.4f)" % pos)
                self.app.inform.emit(_("MEASURING: Click on the Destination point ..."))

            else:
                try:
                    # delete the selection bounding box
                    self.delete_shape()

                    # if GRID is active we need to get the snapped positions
                    if self.app.grid_status() == True:
                        pos = self.app.geo_editor.snap(pos_canvas[0], pos_canvas[1])
                    else:
                        pos = pos_canvas[0], pos_canvas[1]

                    dx = pos[0] - self.point1[0]
                    dy = pos[1] - self.point1[1]
                    d = sqrt(dx**2 + dy**2)

                    self.stop_entry.set_value("(%.4f, %.4f)" % pos)

                    self.app.inform.emit(_("MEASURING: Result D(x) = {d_x} | D(y) = {d_y} | Distance = {d_z}").format(
                        d_x='%4f' % abs(dx), d_y='%4f' % abs(dy), d_z='%4f' % abs(d)))

                    self.distance_x_entry.set_value('%.4f' % abs(dx))
                    self.distance_y_entry.set_value('%.4f' % abs(dy))
                    self.total_distance_entry.set_value('%.4f' % abs(d))

                    self.on_measure(activate=False)

                    # delete the measuring line
                    self.delete_shape()
                except TypeError as e:
                    log.debug("Measurement.on_click_meas() --> %s" % str(e))

    def on_mouse_move_meas(self, event):
        pos_canvas = self.app.plotcanvas.vispy_canvas.translate_coords(event.pos)

        # if GRID is active we need to get the snapped positions
        if self.app.grid_status() == True:
            pos = self.app.geo_editor.snap(pos_canvas[0], pos_canvas[1])
            self.app.app_cursor.enabled = True
            # Update cursor
            self.app.app_cursor.set_data(np.asarray([(pos[0], pos[1])]), symbol='++', edge_color='black', size=20)
        else:
            pos = pos_canvas
            self.app.app_enabled = False

        self.point2 = (pos[0], pos[1])

        if self.clicked_meas == 1:
            self.update_meas_shape([self.point2, self.point1])

    def update_meas_shape(self, pos):
        self.delete_shape()
        self.draw_shape(pos)

    def delete_shape(self):
        self.sel_shapes.clear()
        self.sel_shapes.redraw()

    def draw_shape(self, coords):
        self.meas_line = LineString(coords)
        self.sel_shapes.add(self.meas_line, color='black', update=True, layer=0, tolerance=None)

    def set_meas_units(self, units):
        self.meas.units_label.setText("[" + self.app.options["units"].lower() + "]")

# end of file
