# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File by:  Marius Adrian Stanciu (c)                      #
# Date:     11/12/2020                                     #
# License:  MIT Licence                                    #
# ##########################################################

from PyQt5 import QtWidgets, QtCore, QtGui

from appTool import AppTool
from appGUI.GUIElements import RadioSet, FCButton, FCComboBox, FCLabel
from appParsers.ParseGerber import Gerber

from copy import deepcopy

import numpy as np

from shapely.ops import unary_union
from shapely.geometry import Polygon

from matplotlib.backend_bases import KeyEvent as mpl_key_event

import logging
import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class ToolFollow(AppTool, Gerber):

    optimal_found_sig = QtCore.pyqtSignal(float)

    def __init__(self, app):
        self.app = app
        self.decimals = self.app.decimals

        AppTool.__init__(self, app)
        Gerber.__init__(self, steps_per_circle=self.app.defaults["gerber_circle_steps"])

        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = FollowUI(layout=self.layout, app=self.app)
        self.toolName = self.ui.toolName

        # disconnect flags
        self.area_sel_disconnect_flag = False

        self.first_click = False
        self.cursor_pos = None
        self.mouse_is_dragging = False

        self.mm = None
        self.mp = None
        self.mr = None
        self.kp = None

        self.sel_rect = []

        # store here the points for the "Polygon" area selection shape
        self.points = []
        # set this as True when in middle of drawing a "Polygon" area selection shape
        # it is made False by first click to signify that the shape is complete
        self.poly_drawn = False

        # Signals
        self.ui.selectmethod_radio.activated_custom.connect(self.ui.on_selection)
        self.ui.generate_geometry_button.clicked.connect(self.on_generate_geometry_click)

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='', **kwargs)

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolFollow()")
        log.debug("ToolFOllow().run() was launched ...")

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

        self.app.ui.notebook.setTabText(2, _("Follow Tool"))

    def set_tool_ui(self):
        self.units = self.app.defaults['units'].upper()
        self.ui.selectmethod_radio.set_value('all')     # _("All")
        self.ui.area_shape_radio.set_value('square')

        self.sel_rect[:] = []
        self.points = []
        self.poly_drawn = False
        self.area_sel_disconnect_flag = False

    def on_generate_geometry_click(self):
        obj_name = self.ui.object_combo.currentText()

        # Get source object.
        try:
            obj = self.app.collection.get_by_name(obj_name)
        except Exception as e:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), str(obj_name)))
            return "Could not retrieve object: %s with error: %s" % (obj_name, str(e))

        if obj is None:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Object not found"), str(obj_name)))
            return

        formatted_name = obj_name.rpartition('.')[0]
        if formatted_name == '':
            formatted_name = obj_name
        outname = '%s_follow' % formatted_name

        select_method = self.ui.selectmethod_radio.get_value()
        if select_method == 'all':  # _("All")
            self.follow_all(obj, outname)
        else:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Click the start point of the area."))

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
            self.kp = self.app.plotcanvas.graph_event_connect('key_press', self.on_key_press)

            # disconnect flags
            self.area_sel_disconnect_flag = True

    def follow_all(self, obj, outname):
        def job_thread(tool_obj):
            tool_obj.follow_geo(obj, outname)

        self.app.worker_task.emit({'fcn': job_thread, 'params': [self]})

    def follow_area(self):
        obj_name = self.ui.object_combo.currentText()

        # Get source object.
        try:
            obj = self.app.collection.get_by_name(obj_name)
        except Exception as e:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), str(obj_name)))
            return "Could not retrieve object: %s with error: %s" % (obj_name, str(e))

        if obj is None:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Object not found"), str(self.obj_name)))
            return

        formatted_name = obj_name.rpartition('.')[0]
        if formatted_name == '':
            formatted_name = obj_name
        outname = '%s_follow' % formatted_name

        def job_thread(tool_obj):
            tool_obj.follow_geo_area(obj, outname)

        self.app.worker_task.emit({'fcn': job_thread, 'params': [self]})

    def follow_geo(self, followed_obj, outname):
        """
        Creates a geometry object "following" the gerber paths.

        :param followed_obj:    Gerber object for which to generate the follow geometry
        :type followed_obj:     AppObjects.FlatCAMGerber.GerberObject
        :param outname:         Nme of the resulting Geometry object
        :type outname:          str
        :return: None
        """

        def follow_init(new_obj, app_obj):
            if type(app_obj.defaults["geometry_cnctooldia"]) == float:
                tools_list = [app_obj.defaults["geometry_cnctooldia"]]
            else:
                try:
                    temp_tools = app_obj.defaults["geometry_cnctooldia"].split(",")
                    tools_list = [
                        float(eval(dia)) for dia in temp_tools if dia != ''
                    ]
                except Exception as e:
                    log.error("ToolFollow.follow_geo -> At least one tool diameter needed. -> %s" % str(e))
                    return 'fail'

            # store here the default data for Geometry Data
            new_data = {}

            for opt_key, opt_val in app_obj.options.items():
                if opt_key.find('geometry' + "_") == 0:
                    oname = opt_key[len('geometry') + 1:]
                    new_data[oname] = app_obj.options[opt_key]
                if opt_key.find('tools_mill' + "_") == 0:
                    oname = opt_key[len('tools_mill') + 1:]
                    new_data[oname] = app_obj.options[opt_key]

            # Propagate options
            new_obj.options["cnctooldia"] = app_obj.defaults["geometry_cnctooldia"]
            new_obj.solid_geometry = deepcopy(followed_obj.follow_geometry)
            new_obj.tools = {
                1: {
                    'tooldia': app_obj.dec_format(float(tools_list[0]), self.decimals),
                    'offset': 'Path',
                    'offset_value': 0.0,
                    'type': 'Rough',
                    'tool_type': 'C1',
                    'data': deepcopy(new_data),
                    'solid_geometry': new_obj.solid_geometry
                }
            }

        ret = self.app.app_obj.new_object("geometry", outname, follow_init)
        if ret == 'fail':
            self.app.inform.emit("[ERROR_NOTCL] %s" % _("Failed to create Follow Geometry."))
        else:
            self.app.inform.emit("[success] %s" % _("Done."))

    def follow_geo_area(self, followed_obj, outname):
        """
        Creates a geometry object "following" the gerber paths.

        :param followed_obj:    Gerber object for which to generate the follow geometry
        :type followed_obj:     AppObjects.FlatCAMGerber.GerberObject
        :param outname:         Nme of the resulting Geometry object
        :type outname:          str
        :return: None
        """

        def follow_init(new_obj, app_obj):
            if type(app_obj.defaults["geometry_cnctooldia"]) == float:
                tools_list = [app_obj.defaults["geometry_cnctooldia"]]
            else:
                try:
                    temp_tools = app_obj.defaults["geometry_cnctooldia"].split(",")
                    tools_list = [
                        float(eval(dia)) for dia in temp_tools if dia != ''
                    ]
                except Exception as e:
                    log.error("ToolFollow.follow_geo -> At least one tool diameter needed. -> %s" % str(e))
                    return 'fail'

            # store here the default data for Geometry Data
            new_data = {}

            for opt_key, opt_val in app_obj.options.items():
                if opt_key.find('geometry' + "_") == 0:
                    oname = opt_key[len('geometry') + 1:]
                    new_data[oname] = app_obj.options[opt_key]
                if opt_key.find('tools_mill' + "_") == 0:
                    oname = opt_key[len('tools_mill') + 1:]
                    new_data[oname] = app_obj.options[opt_key]

            # Propagate options
            new_obj.options["cnctooldia"] = app_obj.defaults["geometry_cnctooldia"]

            target_geo = unary_union(followed_obj.follow_geometry)
            area_follow = target_geo.intersection(deepcopy(unary_union(self.sel_rect)))
            self.sel_rect[:] = []
            self.points = []

            new_obj.solid_geometry = deepcopy(area_follow)
            new_obj.tools = {
                1: {
                    'tooldia': app_obj.dec_format(float(tools_list[0]), self.decimals),
                    'offset': 'Path',
                    'offset_value': 0.0,
                    'type': 'Rough',
                    'tool_type': 'C1',
                    'data': deepcopy(new_data),
                    'solid_geometry': new_obj.solid_geometry
                }
            }

        ret = self.app.app_obj.new_object("geometry", outname, follow_init)
        if ret == 'fail':
            self.app.inform.emit("[ERROR_NOTCL] %s" % _("Failed to create Follow Geometry."))
        else:
            self.app.inform.emit("[success] %s" % _("Done."))

    # To be called after clicking on the plot.
    def on_mouse_release(self, event):
        if self.app.is_legacy is False:
            event_pos = event.pos
            # event_is_dragging = event.is_dragging
            right_button = 2
        else:
            event_pos = (event.xdata, event.ydata)
            right_button = 3

        try:
            x = float(event_pos[0])
            y = float(event_pos[1])
        except TypeError:
            return

        event_pos = (x, y)

        shape_type = self.ui.area_shape_radio.get_value()

        curr_pos = self.app.plotcanvas.translate_coords(event_pos)
        if self.app.grid_status():
            curr_pos = self.app.geo_editor.snap(curr_pos[0], curr_pos[1])

        x1, y1 = curr_pos[0], curr_pos[1]

        # do paint single only for left mouse clicks
        if event.button == 1:
            if shape_type == "square":
                if not self.first_click:
                    self.first_click = True
                    self.app.inform.emit('[WARNING_NOTCL] %s' % _("Click the end point of the area."))

                    self.cursor_pos = self.app.plotcanvas.translate_coords(event_pos)
                    if self.app.grid_status():
                        self.cursor_pos = self.app.geo_editor.snap(self.cursor_pos[0], self.cursor_pos[1])
                else:
                    self.app.inform.emit(_("Zone added. Click to start adding next zone or right click to finish."))
                    self.app.delete_selection_shape()

                    x0, y0 = self.cursor_pos[0], self.cursor_pos[1]
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
            else:
                self.points.append((x1, y1))

                if len(self.points) > 1:
                    self.poly_drawn = True
                    self.app.inform.emit(_("Click on next Point or click right mouse button to complete ..."))

                return ""
        elif event.button == right_button and self.mouse_is_dragging is False:

            shape_type = self.ui.area_shape_radio.get_value()

            if shape_type == "square":
                self.first_click = False
            else:
                # if we finish to add a polygon
                if self.poly_drawn is True:
                    try:
                        # try to add the point where we last clicked if it is not already in the self.points
                        last_pt = (x1, y1)
                        if last_pt != self.points[-1]:
                            self.points.append(last_pt)
                    except IndexError:
                        pass

                    # we need to add a Polygon and a Polygon can be made only from at least 3 points
                    if len(self.points) > 2:
                        self.delete_moving_selection_shape()
                        pol = Polygon(self.points)
                        # do not add invalid polygons even if they are drawn by utility geometry
                        if pol.is_valid:
                            self.sel_rect.append(pol)
                            self.draw_selection_shape_polygon(points=self.points)
                            self.app.inform.emit(
                                _("Zone added. Click to start adding next zone or right click to finish."))

                    self.points = []
                    self.poly_drawn = False
                    return

            self.delete_tool_selection_shape()

            if self.app.is_legacy is False:
                self.app.plotcanvas.graph_event_disconnect('mouse_release', self.on_mouse_release)
                self.app.plotcanvas.graph_event_disconnect('mouse_move', self.on_mouse_move)
                self.app.plotcanvas.graph_event_disconnect('key_press', self.on_key_press)
            else:
                self.app.plotcanvas.graph_event_disconnect(self.mr)
                self.app.plotcanvas.graph_event_disconnect(self.mm)
                self.app.plotcanvas.graph_event_disconnect(self.kp)

            self.app.mp = self.app.plotcanvas.graph_event_connect('mouse_press',
                                                                  self.app.on_mouse_click_over_plot)
            self.app.mm = self.app.plotcanvas.graph_event_connect('mouse_move',
                                                                  self.app.on_mouse_move_over_plot)
            self.app.mr = self.app.plotcanvas.graph_event_connect('mouse_release',
                                                                  self.app.on_mouse_click_release_over_plot)

            # disconnect flags
            self.area_sel_disconnect_flag = False

            if len(self.sel_rect) == 0:
                return

            self.follow_area()

    # called on mouse move
    def on_mouse_move(self, event):
        shape_type = self.ui.area_shape_radio.get_value()

        if self.app.is_legacy is False:
            event_pos = event.pos
            event_is_dragging = event.is_dragging
            # right_button = 2
        else:
            event_pos = (event.xdata, event.ydata)
            event_is_dragging = self.app.plotcanvas.is_dragging
            # right_button = 3

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
        if shape_type == "square":
            if self.first_click:
                self.app.delete_selection_shape()
                self.app.draw_moving_selection_shape(old_coords=(self.cursor_pos[0], self.cursor_pos[1]),
                                                     coords=(curr_pos[0], curr_pos[1]))
        else:
            self.delete_moving_selection_shape()
            self.draw_moving_selection_shape_poly(points=self.points, data=(curr_pos[0], curr_pos[1]))

    def on_key_press(self, event):
        # modifiers = QtWidgets.QApplication.keyboardModifiers()
        # matplotlib_key_flag = False

        # events out of the self.app.collection view (it's about Project Tab) are of type int
        if type(event) is int:
            key = event
        # events from the GUI are of type QKeyEvent
        elif type(event) == QtGui.QKeyEvent:
            key = event.key()
        elif isinstance(event, mpl_key_event):  # MatPlotLib key events are trickier to interpret than the rest
            # matplotlib_key_flag = True

            key = event.key
            key = QtGui.QKeySequence(key)

            # check for modifiers
            key_string = key.toString().lower()
            if '+' in key_string:
                mod, __, key_text = key_string.rpartition('+')
                if mod.lower() == 'ctrl':
                    # modifiers = QtCore.Qt.ControlModifier
                    pass
                elif mod.lower() == 'alt':
                    # modifiers = QtCore.Qt.AltModifier
                    pass
                elif mod.lower() == 'shift':
                    # modifiers = QtCore.Qt.ShiftModifier
                    pass
                else:
                    # modifiers = QtCore.Qt.NoModifier
                    pass
                key = QtGui.QKeySequence(key_text)

        # events from Vispy are of type KeyEvent
        else:
            key = event.key

        if key == QtCore.Qt.Key_Escape or key == 'Escape':
            if self.area_sel_disconnect_flag is True:
                try:
                    if self.app.is_legacy is False:
                        self.app.plotcanvas.graph_event_disconnect('mouse_release', self.on_mouse_release)
                        self.app.plotcanvas.graph_event_disconnect('mouse_move', self.on_mouse_move)
                        self.app.plotcanvas.graph_event_disconnect('key_press', self.on_key_press)
                    else:
                        self.app.plotcanvas.graph_event_disconnect(self.mr)
                        self.app.plotcanvas.graph_event_disconnect(self.mm)
                        self.app.plotcanvas.graph_event_disconnect(self.kp)
                except Exception as e:
                    log.debug("ToolFollow.on_key_press() _1 --> %s" % str(e))

                self.app.mp = self.app.plotcanvas.graph_event_connect('mouse_press',
                                                                      self.app.on_mouse_click_over_plot)
                self.app.mm = self.app.plotcanvas.graph_event_connect('mouse_move',
                                                                      self.app.on_mouse_move_over_plot)
                self.app.mr = self.app.plotcanvas.graph_event_connect('mouse_release',
                                                                      self.app.on_mouse_click_release_over_plot)
            self.points = []
            self.poly_drawn = False
            self.sel_rect[:] = []

            self.delete_moving_selection_shape()
            self.delete_tool_selection_shape()


class FollowUI:

    toolName = _("Follow Tool")

    def __init__(self, layout, app):
        self.app = app
        self.decimals = self.app.decimals
        self.layout = layout

        self.tools_frame = QtWidgets.QFrame()
        self.tools_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.tools_frame)
        self.tools_box = QtWidgets.QVBoxLayout()
        self.tools_box.setContentsMargins(0, 0, 0, 0)
        self.tools_frame.setLayout(self.tools_box)

        self.title_box = QtWidgets.QHBoxLayout()
        self.tools_box.addLayout(self.title_box)

        # ## Title
        title_label = FCLabel("%s" % self.toolName)
        title_label.setStyleSheet("""
                                QLabel
                                {
                                    font-size: 16px;
                                    font-weight: bold;
                                }
                                """)
        title_label.setToolTip(
            _("Create a Geometry object with\n"
              "toolpaths to cut around polygons.")
        )

        self.title_box.addWidget(title_label)

        self.obj_combo_label = FCLabel('<b>%s</b>:' % _("GERBER"))
        self.obj_combo_label.setToolTip(
            _("Source object for following geometry.")
        )

        self.tools_box.addWidget(self.obj_combo_label)

        # #############################################################################################################
        # ################################ The object to be followed ##################################################
        # #############################################################################################################
        self.object_combo = FCComboBox()
        self.object_combo.setModel(self.app.collection)
        self.object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        # self.object_combo.setCurrentIndex(1)
        self.object_combo.is_last = True

        self.tools_box.addWidget(self.object_combo)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.tools_box.addWidget(separator_line)

        grid0 = QtWidgets.QGridLayout()
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        self.tools_box.addLayout(grid0)

        # Parameter Title
        self.param_title = FCLabel("<b>%s:</b>" % _("Parameters"))
        grid0.addWidget(self.param_title, 0, 0, 1, 2)

        # Polygon selection
        selectlabel = FCLabel('%s:' % _('Selection'))
        selectlabel.setToolTip(
            _("Selection of area to be processed.\n"
              "- 'All Polygons' - the process will start after click.\n"
              "- 'Area Selection' - left mouse click to start selection of the area to be processed.")
        )

        self.selectmethod_radio = RadioSet([{'label': _("All"), 'value': 'all'},
                                            {'label': _("Area Selection"), 'value': 'area'}])

        grid0.addWidget(selectlabel, 2, 0)
        grid0.addWidget(self.selectmethod_radio, 2, 1)

        # Area Selection shape
        self.area_shape_label = FCLabel('%s:' % _("Shape"))
        self.area_shape_label.setToolTip(
            _("The kind of selection shape used for area selection.")
        )

        self.area_shape_radio = RadioSet([{'label': _("Square"), 'value': 'square'},
                                          {'label': _("Polygon"), 'value': 'polygon'}])

        grid0.addWidget(self.area_shape_label, 4, 0)
        grid0.addWidget(self.area_shape_radio, 4, 1)

        self.area_shape_label.hide()
        self.area_shape_radio.hide()

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 6, 0, 1, 2)

        self.generate_geometry_button = FCButton("%s" % _("Generate Geometry"))
        self.generate_geometry_button.setIcon(QtGui.QIcon(self.app.resource_location + '/geometry32.png'))
        self.generate_geometry_button.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        self.generate_geometry_button.setToolTip(_("Generate a 'Follow' geometry.\n"
                                                   "This means that it will cut through\n"
                                                   "the middle of the trace."))
        self.tools_box.addWidget(self.generate_geometry_button)

        self.tools_box.addStretch()

        # ## Reset Tool
        self.reset_button = FCButton(_("Reset Tool"))
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
        self.tools_box.addWidget(self.reset_button)
        # ############################ FINISHED GUI ###################################
        # #############################################################################

    def on_selection(self, val):
        if val == 'area':  # _("Area Selection")
            self.area_shape_label.show()
            self.area_shape_radio.show()
        else:   # All
            self.area_shape_label.hide()
            self.area_shape_radio.hide()

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
