
from PyQt5 import QtWidgets, QtCore, QtGui

from appTool import AppTool
from appGUI.GUIElements import RadioSet, FCDoubleSpinner, FCButton, FCComboBox, NumericalEvalTupleEntry, FCLabel

from numpy import Inf

from shapely.geometry import Point
from shapely import affinity

import logging
import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class DblSidedTool(AppTool):

    def __init__(self, app):
        AppTool.__init__(self, app)
        self.decimals = self.app.decimals

        self.canvas = self.app.plotcanvas

        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = DsidedUI(layout=self.layout, app=self.app)
        self.toolName = self.ui.toolName

        self.mr = None

        # ## Signals
        self.ui.object_type_radio.activated_custom.connect(self.on_object_type)

        self.ui.add_point_button.clicked.connect(self.on_point_add)
        self.ui.add_drill_point_button.clicked.connect(self.on_drill_add)
        self.ui.delete_drill_point_button.clicked.connect(self.on_drill_delete_last)
        self.ui.box_type_radio.activated_custom.connect(self.on_combo_box_type)

        self.ui.axis_location.group_toggle_fn = self.on_toggle_pointbox

        self.ui.point_entry.textChanged.connect(lambda val: self.ui.align_ref_label_val.set_value(val))
        self.ui.pick_hole_button.clicked.connect(self.on_pick_hole)
        self.ui.mirror_button.clicked.connect(self.on_mirror)

        self.ui.xmin_btn.clicked.connect(self.on_xmin_clicked)
        self.ui.ymin_btn.clicked.connect(self.on_ymin_clicked)
        self.ui.xmax_btn.clicked.connect(self.on_xmax_clicked)
        self.ui.ymax_btn.clicked.connect(self.on_ymax_clicked)

        self.ui.center_btn.clicked.connect(
            lambda: self.ui.point_entry.set_value(self.ui.center_entry.get_value())
        )

        self.ui.create_alignment_hole_button.clicked.connect(self.on_create_alignment_holes)
        self.ui.calculate_bb_button.clicked.connect(self.on_bbox_coordinates)

        self.ui.reset_button.clicked.connect(self.set_tool_ui)

        self.drill_values = ""

        # will hold the Excellon object used for picking a hole as mirror reference
        self.exc_hole_obj = None

        # store the status of the grid
        self.grid_status_memory = None

        # set True if mouse events are locally connected
        self.local_connected = False

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Alt+D', **kwargs)

    def run(self, toggle=True):
        self.app.defaults.report_usage("Tool2Sided()")

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

        self.app.ui.notebook.setTabText(2, _("2-Sided Tool"))

    def set_tool_ui(self):
        self.reset_fields()

        self.ui.point_entry.set_value("")
        self.ui.alignment_holes.set_value("")

        self.ui.mirror_axis.set_value(self.app.defaults["tools_2sided_mirror_axis"])
        self.ui.axis_location.set_value(self.app.defaults["tools_2sided_axis_loc"])
        self.ui.drill_dia.set_value(self.app.defaults["tools_2sided_drilldia"])
        self.ui.align_axis_radio.set_value(self.app.defaults["tools_2sided_allign_axis"])

        self.ui.xmin_entry.set_value(0.0)
        self.ui.ymin_entry.set_value(0.0)
        self.ui.xmax_entry.set_value(0.0)
        self.ui.ymax_entry.set_value(0.0)
        self.ui.center_entry.set_value('')

        self.ui.align_ref_label_val.set_value('%.*f' % (self.decimals, 0.0))

        # run once to make sure that the obj_type attribute is updated in the FCComboBox
        self.ui.object_type_radio.set_value('grb')
        self.on_object_type('grb')
        self.ui.box_type_radio.set_value('grb')
        self.on_combo_box_type('grb')

        if self.local_connected is True:
            self.disconnect_events()

    def on_object_type(self, val):
        obj_type = {'grb': 0, 'exc': 1, 'geo': 2}[val]
        self.ui.object_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.ui.object_combo.setCurrentIndex(0)
        self.ui.object_combo.obj_type = {
            "grb": "Gerber", "exc": "Excellon", "geo": "Geometry"}[val]

    def on_combo_box_type(self, val):
        obj_type = {'grb': 0, 'exc': 1, 'geo': 2}[val]
        self.ui.box_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.ui.box_combo.setCurrentIndex(0)
        self.ui.box_combo.obj_type = {
            "grb": "Gerber", "exc": "Excellon", "geo": "Geometry"}[val]

    def on_create_alignment_holes(self):
        axis = self.ui.align_axis_radio.get_value()
        mode = self.ui.axis_location.get_value()

        if mode == "point":
            try:
                px, py = self.ui.point_entry.get_value()
            except TypeError:
                msg = '[WARNING_NOTCL] %s' % \
                      _("'Point' reference is selected and 'Point' coordinates are missing. Add them and retry.")
                self.app.inform.emit(msg)
                return
        else:
            selection_index = self.ui.box_combo.currentIndex()
            model_index = self.app.collection.index(selection_index, 0, self.ui.object_combo.rootModelIndex())
            try:
                bb_obj = model_index.internalPointer().obj
            except AttributeError:
                msg = '[WARNING_NOTCL] %s' % _("There is no Box reference object loaded. Load one and retry.")
                self.app.inform.emit(msg)
                return

            xmin, ymin, xmax, ymax = bb_obj.bounds()
            px = 0.5 * (xmin + xmax)
            py = 0.5 * (ymin + ymax)

        xscale, yscale = {"X": (1.0, -1.0), "Y": (-1.0, 1.0)}[axis]

        dia = self.ui.drill_dia.get_value()
        if dia == '':
            msg = '[WARNING_NOTCL] %s' % _("No value or wrong format in Drill Dia entry. Add it and retry.")
            self.app.inform.emit(msg)
            return

        tools = {1: {}}
        tools[1]["tooldia"] = dia
        tools[1]['drills'] = []
        tools[1]['solid_geometry'] = []

        # holes = self.alignment_holes.get_value()
        holes = eval('[{}]'.format(self.ui.alignment_holes.text()))
        if not holes:
            msg = '[WARNING_NOTCL] %s' % _("There are no Alignment Drill Coordinates to use. Add them and retry.")
            self.app.inform.emit(msg)
            return

        for hole in holes:
            point = Point(hole)
            point_mirror = affinity.scale(point, xscale, yscale, origin=(px, py))

            tools[1]['drills'] += [point, point_mirror]
            tools[1]['solid_geometry'] += [point, point_mirror]

        def obj_init(obj_inst, app_inst):
            obj_inst.tools = tools
            obj_inst.create_geometry()
            obj_inst.source_file = app_inst.f_handlers.export_excellon(obj_name=obj_inst.options['name'],
                                                                       local_use=obj_inst,
                                                                       filename=None,
                                                                       use_thread=False)

        ret_val = self.app.app_obj.new_object("excellon", _("Alignment Drills"), obj_init)
        self.drill_values = ''

        if not ret_val == 'fail':
            self.app.inform.emit('[success] %s' % _("Excellon object with alignment drills created..."))

    def on_pick_hole(self):

        # get the Excellon file whose geometry will contain the desired drill hole
        selection_index = self.ui.exc_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.ui.exc_combo.rootModelIndex())

        try:
            self.exc_hole_obj = model_index.internalPointer().obj
        except Exception:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Excellon object loaded ..."))
            return

        # disengage the grid snapping since it will be hard to find the drills or pads on grid
        if self.app.ui.grid_snap_btn.isChecked():
            self.grid_status_memory = True
            self.app.ui.grid_snap_btn.trigger()
        else:
            self.grid_status_memory = False

        self.local_connected = True

        self.app.inform.emit('%s.' % _("Click on canvas within the desired Excellon drill hole"))
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
                if self.exc_hole_obj.kind.lower() == 'excellon':
                    for tool, tool_dict in self.exc_hole_obj.tools.items():
                        for geo in tool_dict['solid_geometry']:
                            if click_pt.within(geo):
                                center_pt = geo.centroid
                                center_pt_coords = (
                                    self.app.dec_format(center_pt.x, self.decimals),
                                    self.app.dec_format(center_pt.y, self.decimals)
                                )
                                self.app.delete_selection_shape()

                                self.ui.axis_location.set_value('point')

                                # set the reference point for mirror
                                self.ui.point_entry.set_value(center_pt_coords)

                                self.app.inform.emit('[success] %s' % _("Mirror reference point set."))

        elif event.button == right_button and self.app.event_is_dragging is False:
            self.app.delete_selection_shape()
            self.disconnect_events()
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled by user request."))

    def disconnect_events(self):
        self.app.mr = self.canvas.graph_event_connect('mouse_release', self.app.on_mouse_click_release_over_plot)

        if self.app.is_legacy is False:
            self.canvas.graph_event_disconnect('mouse_release', self.on_mouse_click_release)
        else:
            self.canvas.graph_event_disconnect(self.mr)

        self.local_connected = False

    def on_mirror(self):
        selection_index = self.ui.object_combo.currentIndex()
        # fcobj = self.app.collection.object_list[selection_index]
        model_index = self.app.collection.index(selection_index, 0, self.ui.object_combo.rootModelIndex())
        try:
            fcobj = model_index.internalPointer().obj
        except Exception:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Gerber object loaded ..."))
            return

        if fcobj.kind not in ['gerber', 'geometry', 'excellon']:
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Only Gerber, Excellon and Geometry objects can be mirrored."))
            return

        axis = self.ui.mirror_axis.get_value()
        mode = self.ui.axis_location.get_value()

        if mode == "box":
            selection_index_box = self.ui.box_combo.currentIndex()
            model_index_box = self.app.collection.index(selection_index_box, 0, self.ui.box_combo.rootModelIndex())
            try:
                bb_obj = model_index_box.internalPointer().obj
            except Exception:
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Box object loaded ..."))
                return

            xmin, ymin, xmax, ymax = bb_obj.bounds()
            px = 0.5 * (xmin + xmax)
            py = 0.5 * (ymin + ymax)
        else:
            try:
                px, py = self.ui.point_entry.get_value()
            except TypeError:
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("There are no Point coordinates in the Point field. "
                                                              "Add coords and try again ..."))
                return

        fcobj.mirror(axis, [px, py])
        self.app.app_obj.object_changed.emit(fcobj)
        fcobj.plot()
        self.app.inform.emit('[success] %s: %s' % (_("Object was mirrored"), str(fcobj.options['name'])))

    def on_point_add(self):
        val = self.app.defaults["global_point_clipboard_format"] % \
              (self.decimals, self.app.pos[0], self.decimals, self.app.pos[1])
        self.ui.point_entry.set_value(val)

    def on_drill_add(self):
        self.drill_values += (self.app.defaults["global_point_clipboard_format"] %
                              (self.decimals, self.app.pos[0], self.decimals, self.app.pos[1])) + ','
        self.ui.alignment_holes.set_value(self.drill_values)

    def on_drill_delete_last(self):
        drill_values_without_last_tupple = self.drill_values.rpartition('(')[0]
        self.drill_values = drill_values_without_last_tupple
        self.ui.alignment_holes.set_value(self.drill_values)

    def on_toggle_pointbox(self):
        val = self.ui.axis_location.get_value()
        if val == "point":
            self.ui.point_entry.show()
            self.ui.add_point_button.show()
            self.ui.box_type_label.hide()
            self.ui.box_type_radio.hide()
            self.ui.box_combo.hide()

            self.ui.exc_hole_lbl.hide()
            self.ui.exc_combo.hide()
            self.ui.pick_hole_button.hide()

            self.ui.align_ref_label_val.set_value(self.ui.point_entry.get_value())
        elif val == 'box':
            self.ui.point_entry.hide()
            self.ui.add_point_button.hide()

            self.ui.box_type_label.show()
            self.ui.box_type_radio.show()
            self.ui.box_combo.show()

            self.ui.exc_hole_lbl.hide()
            self.ui.exc_combo.hide()
            self.ui.pick_hole_button.hide()

            self.ui.align_ref_label_val.set_value("Box centroid")
        elif val == 'hole':
            self.ui.point_entry.show()
            self.ui.add_point_button.hide()

            self.ui.box_type_label.hide()
            self.ui.box_type_radio.hide()
            self.ui.box_combo.hide()

            self.ui.exc_hole_lbl.show()
            self.ui.exc_combo.show()
            self.ui.pick_hole_button.show()

    def on_bbox_coordinates(self):

        xmin = Inf
        ymin = Inf
        xmax = -Inf
        ymax = -Inf

        obj_list = self.app.collection.get_selected()

        if not obj_list:
            self.app.inform.emit('[ERROR_NOTCL] %s %s' % (_("Failed."), _("No object is selected.")))
            return

        for obj in obj_list:
            try:
                gxmin, gymin, gxmax, gymax = obj.bounds()
                xmin = min([xmin, gxmin])
                ymin = min([ymin, gymin])
                xmax = max([xmax, gxmax])
                ymax = max([ymax, gymax])
            except Exception as e:
                log.warning("DEV WARNING: Tried to get bounds of empty geometry in DblSidedTool. %s" % str(e))

        self.ui.xmin_entry.set_value(xmin)
        self.ui.ymin_entry.set_value(ymin)
        self.ui.xmax_entry.set_value(xmax)
        self.ui.ymax_entry.set_value(ymax)
        cx = '%.*f' % (self.decimals, (((xmax - xmin) / 2.0) + xmin))
        cy = '%.*f' % (self.decimals, (((ymax - ymin) / 2.0) + ymin))
        val_txt = '(%s, %s)' % (cx, cy)

        self.ui.center_entry.set_value(val_txt)
        self.ui.axis_location.set_value('point')
        self.ui.point_entry.set_value(val_txt)
        self.app.delete_selection_shape()

    def on_xmin_clicked(self):
        xmin = self.ui.xmin_entry.get_value()
        self.ui.axis_location.set_value('point')

        try:
            px, py = self.ui.point_entry.get_value()
            val = self.app.defaults["global_point_clipboard_format"] % (self.decimals, xmin, self.decimals, py)
        except TypeError:
            val = self.app.defaults["global_point_clipboard_format"] % (self.decimals, xmin, self.decimals, 0.0)
        self.ui.point_entry.set_value(val)

    def on_ymin_clicked(self):
        ymin = self.ui.ymin_entry.get_value()
        self.ui.axis_location.set_value('point')

        try:
            px, py = self.ui.point_entry.get_value()
            val = self.app.defaults["global_point_clipboard_format"] % (self.decimals, px, self.decimals, ymin)
        except TypeError:
            val = self.app.defaults["global_point_clipboard_format"] % (self.decimals, 0.0, self.decimals, ymin)
        self.ui.point_entry.set_value(val)

    def on_xmax_clicked(self):
        xmax = self.ui.xmax_entry.get_value()
        self.ui.axis_location.set_value('point')

        try:
            px, py = self.ui.point_entry.get_value()
            val = self.app.defaults["global_point_clipboard_format"] % (self.decimals, xmax, self.decimals, py)
        except TypeError:
            val = self.app.defaults["global_point_clipboard_format"] % (self.decimals, xmax, self.decimals, 0.0)
        self.ui.point_entry.set_value(val)

    def on_ymax_clicked(self):
        ymax = self.ui.ymax_entry.get_value()
        self.ui.axis_location.set_value('point')

        try:
            px, py = self.ui.point_entry.get_value()
            val = self.app.defaults["global_point_clipboard_format"] % (self.decimals, px, self.decimals, ymax)
        except TypeError:
            val = self.app.defaults["global_point_clipboard_format"] % (self.decimals, 0.0, self.decimals, ymax)
        self.ui.point_entry.set_value(val)

    def reset_fields(self):
        self.ui.object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.ui.box_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))

        self.ui.object_combo.setCurrentIndex(0)
        self.ui.box_combo.setCurrentIndex(0)
        self.ui.box_type_radio.set_value('grb')

        self.drill_values = ""
        self.ui.align_ref_label_val.set_value('')


class DsidedUI:

    toolName = _("2-Sided PCB")

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
        self.layout.addWidget(FCLabel(""))

        # ## Grid Layout
        grid_lay = QtWidgets.QGridLayout()
        grid_lay.setColumnStretch(0, 1)
        grid_lay.setColumnStretch(1, 0)
        self.layout.addLayout(grid_lay)

        # Objects to be mirrored
        self.m_objects_label = FCLabel("<b>%s:</b>" % _("Source Object"))
        self.m_objects_label.setToolTip('%s.' % _("Objects to be mirrored"))

        grid_lay.addWidget(self.m_objects_label, 0, 0, 1, 2)

        # Type of object to be cutout
        self.type_obj_combo_label = FCLabel('%s:' % _("Type"))
        self.type_obj_combo_label.setToolTip(
            _("Select the type of application object to be processed in this tool.")
        )

        self.object_type_radio = RadioSet([
            {"label": _("Gerber"), "value": "grb"},
            {"label": _("Geometry"), "value": "geo"},
            {"label": _("Excellon"), "value": "exc"}
        ])

        grid_lay.addWidget(self.type_obj_combo_label, 2, 0)
        grid_lay.addWidget(self.object_type_radio, 2, 1)

        # ## Gerber Object to mirror
        self.object_combo = FCComboBox()
        self.object_combo.setModel(self.app.collection)
        self.object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.object_combo.is_last = True

        grid_lay.addWidget(self.object_combo, 4, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line, 7, 0, 1, 2)

        # #############################################################################################################
        # ##########    BOUNDS OPERATION    ###########################################################################
        # #############################################################################################################
        grid0 = QtWidgets.QGridLayout()
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        self.layout.addLayout(grid0)

        # ## Title Bounds Values
        self.bv_label = FCLabel("<b>%s:</b>" % _('Bounds Values'))
        self.bv_label.setToolTip(
            _("Select on canvas the object(s)\n"
              "for which to calculate bounds values.")
        )
        grid0.addWidget(self.bv_label, 6, 0, 1, 2)

        # Xmin value
        self.xmin_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.xmin_entry.set_precision(self.decimals)
        self.xmin_entry.set_range(-10000.0000, 10000.0000)

        self.xmin_btn = FCButton('%s:' % _("X min"))
        self.xmin_btn.setToolTip(
            _("Minimum location.")
        )
        self.xmin_entry.setReadOnly(True)

        grid0.addWidget(self.xmin_btn, 7, 0)
        grid0.addWidget(self.xmin_entry, 7, 1)

        # Ymin value
        self.ymin_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.ymin_entry.set_precision(self.decimals)
        self.ymin_entry.set_range(-10000.0000, 10000.0000)

        self.ymin_btn = FCButton('%s:' % _("Y min"))
        self.ymin_btn.setToolTip(
            _("Minimum location.")
        )
        self.ymin_entry.setReadOnly(True)

        grid0.addWidget(self.ymin_btn, 8, 0)
        grid0.addWidget(self.ymin_entry, 8, 1)

        # Xmax value
        self.xmax_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.xmax_entry.set_precision(self.decimals)
        self.xmax_entry.set_range(-10000.0000, 10000.0000)

        self.xmax_btn = FCButton('%s:' % _("X max"))
        self.xmax_btn.setToolTip(
            _("Maximum location.")
        )
        self.xmax_entry.setReadOnly(True)

        grid0.addWidget(self.xmax_btn, 9, 0)
        grid0.addWidget(self.xmax_entry, 9, 1)

        # Ymax value
        self.ymax_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.ymax_entry.set_precision(self.decimals)
        self.ymax_entry.set_range(-10000.0000, 10000.0000)

        self.ymax_btn = FCButton('%s:' % _("Y max"))
        self.ymax_btn.setToolTip(
            _("Maximum location.")
        )
        self.ymax_entry.setReadOnly(True)

        grid0.addWidget(self.ymax_btn, 10, 0)
        grid0.addWidget(self.ymax_entry, 10, 1)

        # Center point value
        self.center_entry = NumericalEvalTupleEntry(border_color='#0069A9')
        self.center_entry.setPlaceholderText(_("Center point coordinates"))

        self.center_btn = FCButton('%s:' % _("Centroid"))
        self.center_btn.setToolTip(
            _("The center point location for the rectangular\n"
              "bounding shape. Centroid. Format is (x, y).")
        )
        self.center_entry.setReadOnly(True)

        grid0.addWidget(self.center_btn, 12, 0)
        grid0.addWidget(self.center_entry, 12, 1)

        # Calculate Bounding box
        self.calculate_bb_button = FCButton(_("Calculate Bounds Values"))
        self.calculate_bb_button.setToolTip(
            _("Calculate the enveloping rectangular shape coordinates,\n"
              "for the selection of objects.\n"
              "The envelope shape is parallel with the X, Y axis.")
        )
        self.calculate_bb_button.setStyleSheet("""
                                               QPushButton
                                               {
                                                   font-weight: bold;
                                               }
                                               """)
        grid0.addWidget(self.calculate_bb_button, 13, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 14, 0, 1, 2)

        # #############################################################################################################
        # ##########    MIRROR OPERATION    ###########################################################################
        # #############################################################################################################
        grid1 = QtWidgets.QGridLayout()
        grid1.setColumnStretch(0, 0)
        grid1.setColumnStretch(1, 1)
        self.layout.addLayout(grid1)

        self.param_label = FCLabel("<b>%s:</b>" % _("Mirror Operation"))
        self.param_label.setToolTip('%s.' % _("Parameters for the mirror operation"))

        grid1.addWidget(self.param_label, 0, 0, 1, 2)

        # ## Axis
        self.mirax_label = FCLabel('%s:' % _("Axis"))
        self.mirax_label.setToolTip(_("Mirror vertically (X) or horizontally (Y)."))
        self.mirror_axis = RadioSet(
            [
                {'label': 'X', 'value': 'X'},
                {'label': 'Y', 'value': 'Y'}
            ],
            orientation='vertical',
            stretch=False
        )

        grid1.addWidget(self.mirax_label, 2, 0)
        grid1.addWidget(self.mirror_axis, 2, 1, 1, 2)

        # ## Axis Location
        self.axloc_label = FCLabel('%s:' % _("Reference"))
        self.axloc_label.setToolTip(
            _("The coordinates used as reference for the mirror operation.\n"
              "Can be:\n"
              "- Point -> a set of coordinates (x,y) around which the object is mirrored\n"
              "- Box -> a set of coordinates (x, y) obtained from the center of the\n"
              "bounding box of another object selected below\n"
              "- Hole Snap -> a point defined by the center of a drill hole in a Excellon object")
        )
        self.axis_location = RadioSet(
            [
                {'label': _('Point'), 'value': 'point'},
                {'label': _('Box'), 'value': 'box'},
                {'label': _('Hole Snap'), 'value': 'hole'},
            ]
        )

        grid1.addWidget(self.axloc_label, 4, 0)
        grid1.addWidget(self.axis_location, 4, 1, 1, 2)

        # ## Point/Box
        self.point_entry = NumericalEvalTupleEntry(border_color='#0069A9')
        self.point_entry.setPlaceholderText(_("Point coordinates"))

        # Add a reference
        self.add_point_button = FCButton(_("Add"))
        self.add_point_button.setIcon(QtGui.QIcon(self.app.resource_location + '/plus16.png'))
        self.add_point_button.setToolTip(
            _("Add the coordinates in format <b>(x, y)</b> through which the mirroring axis\n "
              "selected in 'MIRROR AXIS' pass.\n"
              "The (x, y) coordinates are captured by pressing SHIFT key\n"
              "and left mouse button click on canvas or you can enter the coordinates manually.")
        )
        self.add_point_button.setStyleSheet("""
                                        QPushButton
                                        {
                                            font-weight: bold;
                                        }
                                        """)
        self.add_point_button.setMinimumWidth(60)

        grid1.addWidget(self.point_entry, 7, 0, 1, 2)
        grid1.addWidget(self.add_point_button, 7, 2)

        self.exc_hole_lbl = FCLabel('%s:' % _("Excellon"))
        self.exc_hole_lbl.setToolTip(
            _("Object that holds holes that can be picked as reference for mirroring.")
        )

        # Excellon Object that holds the holes
        self.exc_combo = FCComboBox()
        self.exc_combo.setModel(self.app.collection)
        self.exc_combo.setRootModelIndex(self.app.collection.index(1, 0, QtCore.QModelIndex()))
        self.exc_combo.is_last = True

        self.exc_hole_lbl.hide()
        self.exc_combo.hide()

        grid1.addWidget(self.exc_hole_lbl, 10, 0)
        grid1.addWidget(self.exc_combo, 10, 1, 1, 2)

        self.pick_hole_button = FCButton(_("Pick hole"))
        self.pick_hole_button.setToolTip(
            _("Click inside a drill hole that belong to the selected Excellon object,\n"
              "and the hole center coordinates will be copied to the Point field.")
        )

        self.pick_hole_button.hide()

        grid1.addWidget(self.pick_hole_button, 12, 0, 1, 3)

        # ## Grid Layout
        grid_lay3 = QtWidgets.QGridLayout()
        grid_lay3.setColumnStretch(0, 0)
        grid_lay3.setColumnStretch(1, 1)
        grid1.addLayout(grid_lay3, 14, 0, 1, 3)

        self.box_type_label = FCLabel('%s:' % _("Reference Object"))
        self.box_type_label.setToolTip(
            _("It can be of type: Gerber or Excellon or Geometry.\n"
              "The coordinates of the center of the bounding box are used\n"
              "as reference for mirror operation.")
        )

        # Type of object used as BOX reference
        self.box_type_radio = RadioSet([{'label': _('Gerber'), 'value': 'grb'},
                                        {'label': _('Excellon'), 'value': 'exc'},
                                        {'label': _('Geometry'), 'value': 'geo'}])

        self.box_type_label.hide()
        self.box_type_radio.hide()

        grid_lay3.addWidget(self.box_type_label, 0, 0, 1, 2)
        grid_lay3.addWidget(self.box_type_radio, 1, 0, 1, 2)

        # Object used as BOX reference
        self.box_combo = FCComboBox()
        self.box_combo.setModel(self.app.collection)
        self.box_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.box_combo.is_last = True

        self.box_combo.hide()

        grid_lay3.addWidget(self.box_combo, 3, 0, 1, 2)

        self.mirror_button = FCButton(_("Mirror"))
        self.mirror_button.setIcon(QtGui.QIcon(self.app.resource_location + '/doubleside16.png'))
        self.mirror_button.setToolTip(
            _("Mirrors (flips) the specified object around \n"
              "the specified axis. Does not create a new \n"
              "object, but modifies it.")
        )
        self.mirror_button.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        grid1.addWidget(self.mirror_button, 16, 0, 1, 3)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid1.addWidget(separator_line, 18, 0, 1, 3)

        # #############################################################################################################
        # ##########    ALIGNMENT OPERATION    ########################################################################
        # #############################################################################################################
        grid4 = QtWidgets.QGridLayout()
        grid4.setColumnStretch(0, 0)
        grid4.setColumnStretch(1, 1)
        self.layout.addLayout(grid4)

        # ## Alignment holes
        self.alignment_label = FCLabel("<b>%s:</b>" % _('PCB Alignment'))
        self.alignment_label.setToolTip(
            _("Creates an Excellon Object containing the\n"
              "specified alignment holes and their mirror\n"
              "images.")
        )
        grid4.addWidget(self.alignment_label, 0, 0, 1, 2)

        # ## Drill diameter for alignment holes
        self.dt_label = FCLabel("%s:" % _('Drill Dia'))
        self.dt_label.setToolTip(
            _("Diameter of the drill for the alignment holes.")
        )

        self.drill_dia = FCDoubleSpinner(callback=self.confirmation_message)
        self.drill_dia.setToolTip(
            _("Diameter of the drill for the alignment holes.")
        )
        self.drill_dia.set_precision(self.decimals)
        self.drill_dia.set_range(0.0000, 10000.0000)

        grid4.addWidget(self.dt_label, 2, 0)
        grid4.addWidget(self.drill_dia, 2, 1)

        # ## Alignment Axis
        self.align_ax_label = FCLabel('%s:' % _("Axis"))
        self.align_ax_label.setToolTip(
            _("Mirror vertically (X) or horizontally (Y).")
        )
        self.align_axis_radio = RadioSet(
            [
                {'label': 'X', 'value': 'X'},
                {'label': 'Y', 'value': 'Y'}
            ],
            orientation='vertical',
            stretch=False
        )

        grid4.addWidget(self.align_ax_label, 4, 0)
        grid4.addWidget(self.align_axis_radio, 4, 1)

        # ## Alignment Reference Point
        self.align_ref_label = FCLabel('%s:' % _("Reference"))
        self.align_ref_label.setToolTip(
            _("The reference point used to create the second alignment drill\n"
              "from the first alignment drill, by doing mirror.\n"
              "It can be modified in the Mirror Parameters -> Reference section")
        )

        self.align_ref_label_val = NumericalEvalTupleEntry(border_color='#0069A9')
        self.align_ref_label_val.setToolTip(
            _("The reference point used to create the second alignment drill\n"
              "from the first alignment drill, by doing mirror.\n"
              "It can be modified in the Mirror Parameters -> Reference section")
        )
        self.align_ref_label_val.setDisabled(True)

        grid4.addWidget(self.align_ref_label, 6, 0)
        grid4.addWidget(self.align_ref_label_val, 6, 1)

        grid5 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid5)

        # ## Alignment holes
        self.ah_label = FCLabel("%s:" % _('Alignment Drill Coordinates'))
        self.ah_label.setToolTip(
            _("Alignment holes (x1, y1), (x2, y2), ... "
              "on one side of the mirror axis. For each set of (x, y) coordinates\n"
              "entered here, a pair of drills will be created:\n\n"
              "- one drill at the coordinates from the field\n"
              "- one drill in mirror position over the axis selected above in the 'Align Axis'.")
        )

        self.alignment_holes = NumericalEvalTupleEntry(border_color='#0069A9')
        self.alignment_holes.setPlaceholderText(_("Drill coordinates"))

        grid5.addWidget(self.ah_label, 0, 0, 1, 2)
        grid5.addWidget(self.alignment_holes, 1, 0, 1, 2)

        self.add_drill_point_button = FCButton(_("Add"))
        self.add_drill_point_button.setIcon(QtGui.QIcon(self.app.resource_location + '/plus16.png'))
        self.add_drill_point_button.setToolTip(
            _("Add alignment drill holes coordinates in the format: (x1, y1), (x2, y2), ... \n"
              "on one side of the alignment axis.\n\n"
              "The coordinates set can be obtained:\n"
              "- press SHIFT key and left mouse clicking on canvas. Then click Add.\n"
              "- press SHIFT key and left mouse clicking on canvas. Then Ctrl+V in the field.\n"
              "- press SHIFT key and left mouse clicking on canvas. Then RMB click in the field and click Paste.\n"
              "- by entering the coords manually in the format: (x1, y1), (x2, y2), ...")
        )
        # self.add_drill_point_button.setStyleSheet("""
        #                 QPushButton
        #                 {
        #                     font-weight: bold;
        #                 }
        #                 """)

        self.delete_drill_point_button = FCButton(_("Delete Last"))
        self.delete_drill_point_button.setIcon(QtGui.QIcon(self.app.resource_location + '/trash32.png'))
        self.delete_drill_point_button.setToolTip(
            _("Delete the last coordinates tuple in the list.")
        )
        drill_hlay = QtWidgets.QHBoxLayout()

        drill_hlay.addWidget(self.add_drill_point_button)
        drill_hlay.addWidget(self.delete_drill_point_button)

        grid5.addLayout(drill_hlay, 2, 0, 1, 2)

        # ## Buttons
        self.create_alignment_hole_button = FCButton(_("Create Excellon Object"))
        self.create_alignment_hole_button.setIcon(QtGui.QIcon(self.app.resource_location + '/drill32.png'))
        self.create_alignment_hole_button.setToolTip(
            _("Creates an Excellon Object containing the\n"
              "specified alignment holes and their mirror\n"
              "images.")
        )
        self.create_alignment_hole_button.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        self.layout.addWidget(self.create_alignment_hole_button)

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
