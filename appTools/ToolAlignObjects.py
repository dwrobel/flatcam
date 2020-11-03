# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 1/13/2020                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtCore, QtGui
from appTool import AppTool

from appGUI.GUIElements import FCComboBox, RadioSet, FCLabel, FCButton

import math

from shapely.geometry import Point
from shapely.affinity import translate

import gettext
import appTranslation as fcTranslate
import builtins
import logging

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class AlignObjects(AppTool):

    toolName = _("Align Objects")

    def __init__(self, app):
        AppTool.__init__(self, app)

        self.app = app
        self.decimals = app.decimals

        self.canvas = self.app.plotcanvas

        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = AlignUI(layout=self.layout, app=self.app)
        self.toolName = self.ui.toolName

        # Signals
        self.ui.align_object_button.clicked.connect(self.on_align)
        self.ui.type_obj_radio.activated_custom.connect(self.on_type_obj_changed)
        self.ui.type_aligner_obj_radio.activated_custom.connect(self.on_type_aligner_changed)
        self.ui.reset_button.clicked.connect(self.set_tool_ui)

        self.mr = None

        # if the mouse events are connected to a local method set this True
        self.local_connected = False

        # store the status of the grid
        self.grid_status_memory = None

        self.aligned_obj = None
        self.aligner_obj = None

        # this is one of the objects: self.aligned_obj or self.aligner_obj
        self.target_obj = None

        # here store the alignment points
        self.clicked_points = []

        self.align_type = None

        # old colors of objects involved in the alignment
        self.aligner_old_fill_color = None
        self.aligner_old_line_color = None
        self.aligned_old_fill_color = None
        self.aligned_old_line_color = None

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolAlignObjects()")

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

        self.app.ui.notebook.setTabText(2, _("Align Tool"))

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Alt+A', **kwargs)

    def set_tool_ui(self):
        self.reset_fields()

        self.clicked_points = []
        self.target_obj = None
        self.aligned_obj = None
        self.aligner_obj = None

        self.aligner_old_fill_color = None
        self.aligner_old_line_color = None
        self.aligned_old_fill_color = None
        self.aligned_old_line_color = None

        self.ui.a_type_radio.set_value(self.app.defaults["tools_align_objects_align_type"])
        self.ui.type_obj_radio.set_value('grb')
        self.ui.type_aligner_obj_radio.set_value('grb')

        if self.local_connected is True:
            self.disconnect_cal_events()

    def on_type_obj_changed(self, val):
        obj_type = {'grb': 0, 'exc': 1}[val]
        self.ui.object_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.ui.object_combo.setCurrentIndex(0)
        self.ui.object_combo.obj_type = {'grb': "Gerber", 'exc': "Excellon"}[val]

    def on_type_aligner_changed(self, val):
        obj_type = {'grb': 0, 'exc': 1}[val]
        self.ui.aligner_object_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.ui.aligner_object_combo.setCurrentIndex(0)
        self.ui.aligner_object_combo.obj_type = {'grb': "Gerber", 'exc': "Excellon"}[val]

    def on_align(self):
        self.app.delete_selection_shape()

        obj_sel_index = self.ui.object_combo.currentIndex()
        obj_model_index = self.app.collection.index(obj_sel_index, 0, self.ui.object_combo.rootModelIndex())
        try:
            self.aligned_obj = obj_model_index.internalPointer().obj
        except AttributeError:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no aligned FlatCAM object selected..."))
            return

        aligner_obj_sel_index = self.ui.aligner_object_combo.currentIndex()
        aligner_obj_model_index = self.app.collection.index(
            aligner_obj_sel_index, 0, self.ui.aligner_object_combo.rootModelIndex())

        try:
            self.aligner_obj = aligner_obj_model_index.internalPointer().obj
        except AttributeError:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no aligner FlatCAM object selected..."))
            return

        self.align_type = self.ui.a_type_radio.get_value()

        # disengage the grid snapping since it will be hard to find the drills or pads on grid
        if self.app.ui.grid_snap_btn.isChecked():
            self.grid_status_memory = True
            self.app.ui.grid_snap_btn.trigger()
        else:
            self.grid_status_memory = False

        self.local_connected = True

        self.aligner_old_fill_color = self.aligner_obj.fill_color
        self.aligner_old_line_color = self.aligner_obj.outline_color
        self.aligned_old_fill_color = self.aligned_obj.fill_color
        self.aligned_old_line_color = self.aligned_obj.outline_color

        self.target_obj = self.aligned_obj
        self.set_color()

        self.app.inform.emit('%s: %s' % (_("First Point"), _("Click on the START point.")))
        self.mr = self.canvas.graph_event_connect('mouse_release', self.on_mouse_click_release)

        if self.app.is_legacy is False:
            self.canvas.graph_event_disconnect('mouse_release', self.app.on_mouse_click_release_over_plot)
        else:
            self.canvas.graph_event_disconnect(self.app.mr)

    def on_mouse_click_release(self, event):
        if self.app.is_legacy is False:
            event_pos = event.pos
            right_button = 2
            self.app.event_is_dragging = self.app.event_is_dragging
        else:
            event_pos = (event.xdata, event.ydata)
            right_button = 3
            self.app.event_is_dragging = self.app.ui.popMenu.mouse_is_panning

        pos_canvas = self.canvas.translate_coords(event_pos)

        if event.button == 1:
            click_pt = Point([pos_canvas[0], pos_canvas[1]])

            if self.app.selection_type is not None:
                # delete previous selection shape
                self.app.delete_selection_shape()
                self.app.selection_type = None
            else:
                if self.target_obj.kind.lower() == 'excellon':
                    for tool, tool_dict in self.target_obj.tools.items():
                        for geo in tool_dict['solid_geometry']:
                            if click_pt.within(geo):
                                center_pt = geo.centroid
                                self.clicked_points.append(
                                    [
                                        float('%.*f' % (self.decimals, center_pt.x)),
                                        float('%.*f' % (self.decimals, center_pt.y))
                                    ]
                                )
                                self.check_points()
                elif self.target_obj.kind.lower() == 'gerber':
                    for apid, apid_val in self.target_obj.apertures.items():
                        for geo_el in apid_val['geometry']:
                            if 'solid' in geo_el:
                                if click_pt.within(geo_el['solid']):
                                    if isinstance(geo_el['follow'], Point):
                                        center_pt = geo_el['solid'].centroid
                                        self.clicked_points.append(
                                            [
                                                float('%.*f' % (self.decimals, center_pt.x)),
                                                float('%.*f' % (self.decimals, center_pt.y))
                                            ]
                                        )
                                        self.check_points()

        elif event.button == right_button and self.app.event_is_dragging is False:
            self.reset_color()
            self.clicked_points = []
            self.disconnect_cal_events()
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled by user request."))

    def check_points(self):
        if len(self.clicked_points) == 1:
            self.app.inform.emit('%s: %s. %s' % (
                _("First Point"), _("Click on the DESTINATION point ..."), _("Or right click to cancel.")))
            self.target_obj = self.aligner_obj
            self.reset_color()
            self.set_color()

        if len(self.clicked_points) == 2:
            if self.align_type == 'sp':
                self.align_translate()
                self.app.inform.emit('[success] %s' % _("Done."))
                self.app.plot_all()

                self.disconnect_cal_events()
                return
            else:
                self.app.inform.emit('%s: %s. %s' % (
                    _("Second Point"), _("Click on the START point."), _("Or right click to cancel.")))
                self.target_obj = self.aligned_obj
                self.reset_color()
                self.set_color()

        if len(self.clicked_points) == 3:
            self.app.inform.emit('%s: %s. %s' % (
                _("Second Point"), _("Click on the DESTINATION point ..."), _("Or right click to cancel.")))
            self.target_obj = self.aligner_obj
            self.reset_color()
            self.set_color()

        if len(self.clicked_points) == 4:
            self.align_translate()
            self.align_rotate()
            self.app.inform.emit('[success] %s' % _("Done."))

            self.disconnect_cal_events()
            self.app.plot_all()

    def align_translate(self):
        dx = self.clicked_points[1][0] - self.clicked_points[0][0]
        dy = self.clicked_points[1][1] - self.clicked_points[0][1]

        self.aligned_obj.offset((dx, dy))

        # Update the object bounding box options
        a, b, c, d = self.aligned_obj.bounds()
        self.aligned_obj.options['xmin'] = a
        self.aligned_obj.options['ymin'] = b
        self.aligned_obj.options['xmax'] = c
        self.aligned_obj.options['ymax'] = d

    def align_rotate(self):
        dx = self.clicked_points[1][0] - self.clicked_points[0][0]
        dy = self.clicked_points[1][1] - self.clicked_points[0][1]

        test_rotation_pt = translate(Point(self.clicked_points[2]), xoff=dx, yoff=dy)
        new_start = (test_rotation_pt.x, test_rotation_pt.y)
        new_dest = self.clicked_points[3]

        origin_pt = self.clicked_points[1]

        dxd = new_dest[0] - origin_pt[0]
        dyd = new_dest[1] - origin_pt[1]

        dxs = new_start[0] - origin_pt[0]
        dys = new_start[1] - origin_pt[1]

        rotation_not_needed = (abs(new_start[0] - new_dest[0]) <= (10 ** -self.decimals)) or \
                              (abs(new_start[1] - new_dest[1]) <= (10 ** -self.decimals))
        if rotation_not_needed is False:
            # calculate rotation angle
            angle_dest = math.degrees(math.atan(dyd / dxd))
            angle_start = math.degrees(math.atan(dys / dxs))
            angle = angle_dest - angle_start
            self.aligned_obj.rotate(angle=angle, point=origin_pt)

    def disconnect_cal_events(self):
        # restore the Grid snapping if it was active before
        if self.grid_status_memory is True:
            self.app.ui.grid_snap_btn.trigger()

        self.app.mr = self.canvas.graph_event_connect('mouse_release', self.app.on_mouse_click_release_over_plot)

        if self.app.is_legacy is False:
            self.canvas.graph_event_disconnect('mouse_release', self.on_mouse_click_release)
        else:
            self.canvas.graph_event_disconnect(self.mr)

        self.local_connected = False

        self.aligner_old_fill_color = None
        self.aligner_old_line_color = None
        self.aligned_old_fill_color = None
        self.aligned_old_line_color = None

    def set_color(self):
        new_color = "#15678abf"
        new_line_color = new_color
        self.target_obj.shapes.redraw(
            update_colors=(new_color, new_line_color)
        )

    def reset_color(self):
        self.aligned_obj.shapes.redraw(
            update_colors=(self.aligned_old_fill_color, self.aligned_old_line_color)
        )

        self.aligner_obj.shapes.redraw(
            update_colors=(self.aligner_old_fill_color, self.aligner_old_line_color)
        )

    def reset_fields(self):
        self.ui.object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.ui.aligner_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))


class AlignUI:

    toolName = _("Align Objects")

    def __init__(self, layout, app):
        self.app = app
        self.decimals = self.app.decimals
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

        self.layout.addWidget(QtWidgets.QLabel(""))

        # Form Layout
        grid0 = QtWidgets.QGridLayout()
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        self.layout.addLayout(grid0)

        self.aligned_label = FCLabel('<b>%s:</b>' % _("MOVING object"))
        grid0.addWidget(self.aligned_label, 0, 0, 1, 2)

        self.aligned_label.setToolTip(
            _("Specify the type of object to be aligned.\n"
              "It can be of type: Gerber or Excellon.\n"
              "The selection here decide the type of objects that will be\n"
              "in the Object combobox.")
        )

        # Type of object to be aligned
        self.type_obj_radio = RadioSet([
            {"label": _("Gerber"), "value": "grb"},
            {"label": _("Excellon"), "value": "exc"},
        ])

        grid0.addWidget(self.type_obj_radio, 3, 0, 1, 2)

        # Object to be aligned
        self.object_combo = FCComboBox()
        self.object_combo.setModel(self.app.collection)
        self.object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.object_combo.is_last = True

        self.object_combo.setToolTip(
            _("Object to be aligned.")
        )

        grid0.addWidget(self.object_combo, 4, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 5, 0, 1, 2)

        grid0.addWidget(FCLabel(''), 6, 0, 1, 2)

        self.aligned_label = FCLabel('<b>%s:</b>' % _("DESTINATION object"))
        self.aligned_label.setToolTip(
            _("Specify the type of object to be aligned to.\n"
              "It can be of type: Gerber or Excellon.\n"
              "The selection here decide the type of objects that will be\n"
              "in the Object combobox.")
        )
        grid0.addWidget(self.aligned_label, 7, 0, 1, 2)

        # Type of object to be aligned to = aligner
        self.type_aligner_obj_radio = RadioSet([
            {"label": _("Gerber"), "value": "grb"},
            {"label": _("Excellon"), "value": "exc"},
        ])

        grid0.addWidget(self.type_aligner_obj_radio, 8, 0, 1, 2)

        # Object to be aligned to = aligner
        self.aligner_object_combo = FCComboBox()
        self.aligner_object_combo.setModel(self.app.collection)
        self.aligner_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.aligner_object_combo.is_last = True

        self.aligner_object_combo.setToolTip(
            _("Object to be aligned to. Aligner.")
        )

        grid0.addWidget(self.aligner_object_combo, 9, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 10, 0, 1, 2)

        grid0.addWidget(QtWidgets.QLabel(''), 11, 0, 1, 2)

        # Alignment Type
        self.a_type_lbl = FCLabel('<b>%s:</b>' % _("Alignment Type"))
        self.a_type_lbl.setToolTip(
            _("The type of alignment can be:\n"
              "- Single Point -> it require a single point of sync, the action will be a translation\n"
              "- Dual Point -> it require two points of sync, the action will be translation followed by rotation")
        )
        self.a_type_radio = RadioSet(
            [
                {'label': _('Single Point'), 'value': 'sp'},
                {'label': _('Dual Point'), 'value': 'dp'}
            ])

        grid0.addWidget(self.a_type_lbl, 12, 0, 1, 2)
        grid0.addWidget(self.a_type_radio, 13, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 14, 0, 1, 2)

        # Buttons
        self.align_object_button = FCButton(_("Align Object"))
        self.align_object_button.setIcon(QtGui.QIcon(self.app.resource_location + '/align16.png'))
        self.align_object_button.setToolTip(
            _("Align the specified object to the aligner object.\n"
              "If only one point is used then it assumes translation.\n"
              "If tho points are used it assume translation and rotation.")
        )
        self.align_object_button.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        self.layout.addWidget(self.align_object_button)

        self.layout.addStretch()

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
