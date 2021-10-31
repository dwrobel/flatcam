
from PyQt6 import QtWidgets, QtCore, QtGui

from appTool import AppTool
from appGUI.GUIElements import RadioSet, FCDoubleSpinner, FCButton, FCComboBox, NumericalEvalTupleEntry, FCLabel, \
    VerticalScrollArea, FCGridLayout, FCComboBox2, FCFrame

from numpy import Inf
from copy import deepcopy

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
        self.pluginName = self.ui.pluginName
        self.connect_signals_at_init()

        self.mr = None

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
            # if the splitter is hidden, display it
            if self.app.ui.splitter.sizes()[0] == 0:
                self.app.ui.splitter.setSizes([1, 1])

            # if the Tool Tab is hidden display it, else hide it but only if the objectName is the same
            found_idx = None
            for idx in range(self.app.ui.notebook.count()):
                if self.app.ui.notebook.widget(idx).objectName() == "plugin_tab":
                    found_idx = idx
                    break
            # show the Tab
            if not found_idx:
                try:
                    self.app.ui.notebook.addTab(self.app.ui.plugin_tab, _("Plugin"))
                except RuntimeError:
                    self.app.ui.plugin_tab = QtWidgets.QWidget()
                    self.app.ui.plugin_tab.setObjectName("plugin_tab")
                    self.app.ui.plugin_tab_layout = QtWidgets.QVBoxLayout(self.app.ui.plugin_tab)
                    self.app.ui.plugin_tab_layout.setContentsMargins(2, 2, 2, 2)

                    self.app.ui.plugin_scroll_area = VerticalScrollArea()
                    self.app.ui.plugin_tab_layout.addWidget(self.app.ui.plugin_scroll_area)
                    self.app.ui.notebook.addTab(self.app.ui.plugin_tab, _("Plugin"))
                # focus on Tool Tab
                self.app.ui.notebook.setCurrentWidget(self.app.ui.plugin_tab)

            try:
                if self.app.ui.plugin_scroll_area.widget().objectName() == self.pluginName and found_idx:
                    # if the Tool Tab is not focused, focus on it
                    if not self.app.ui.notebook.currentWidget() is self.app.ui.plugin_tab:
                        # focus on Tool Tab
                        self.app.ui.notebook.setCurrentWidget(self.app.ui.plugin_tab)
                    else:
                        # else remove the Tool Tab
                        self.app.ui.notebook.setCurrentWidget(self.app.ui.properties_tab)
                        self.app.ui.notebook.removeTab(2)

                        # if there are no objects loaded in the app then hide the Notebook widget
                        if not self.app.collection.get_list():
                            self.app.ui.splitter.setSizes([0, 1])
            except AttributeError:
                pass
        else:
            if self.app.ui.splitter.sizes()[0] == 0:
                self.app.ui.splitter.setSizes([1, 1])

        AppTool.run(self)
        self.set_tool_ui()

        self.app.ui.notebook.setTabText(2, _("2-Sided"))

    def connect_signals_at_init(self):
        # #############################################################################
        # ############################ SIGNALS ########################################
        # #############################################################################
        self.ui.level.toggled.connect(self.on_level_changed)

        self.ui.object_type_combo.currentIndexChanged.connect(self.on_object_type)

        self.ui.add_point_button.clicked.connect(self.on_point_add)
        self.ui.delete_drill_point_button.clicked.connect(self.on_drill_delete_last)
        self.ui.box_type_radio.activated_custom.connect(self.on_combo_box_type)

        self.ui.axis_location.activated_custom.connect(self.on_toggle_pointbox)

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

        self.ui.create_excellon_button.clicked.connect(self.on_create_alignment_holes)
        self.ui.calculate_bb_button.clicked.connect(self.on_bbox_coordinates)

        self.app.proj_selection_changed.connect(self.on_object_selection_changed)

        self.ui.reset_button.clicked.connect(self.set_tool_ui)

    def set_tool_ui(self):
        self.clear_ui(self.layout)
        self.ui = DsidedUI(layout=self.layout, app=self.app)
        self.pluginName = self.ui.pluginName
        self.connect_signals_at_init()

        self.reset_fields()

        self.ui.point_entry.set_value("")
        self.ui.alignment_holes.set_value("")

        self.ui.mirror_axis.set_value(self.app.defaults["tools_2sided_mirror_axis"])
        self.ui.axis_location.set_value(self.app.defaults["tools_2sided_axis_loc"])
        self.on_toggle_pointbox(self.ui.axis_location.get_value())

        self.ui.drill_dia.set_value(self.app.defaults["tools_2sided_drilldia"])
        self.ui.align_type_radio.set_value(self.app.defaults["tools_2sided_align_type"])
        self.ui.on_align_type_changed(val=self.ui.align_type_radio.get_value())

        self.ui.xmin_entry.set_value(0.0)
        self.ui.ymin_entry.set_value(0.0)
        self.ui.xmax_entry.set_value(0.0)
        self.ui.ymax_entry.set_value(0.0)
        self.ui.center_entry.set_value('')

        self.ui.align_ref_label_val.set_value('%.*f' % (self.decimals, 0.0))

        # SELECT THE CURRENT OBJECT
        obj = self.app.collection.get_active()
        if obj:
            obj_name = obj.options['name']
            if obj.kind == 'gerber':
                # run once to make sure that the obj_type attribute is updated in the FCComboBox
                self.ui.object_type_combo.set_value(0)
                self.on_object_type(0)  # Gerber
                self.ui.box_type_radio.set_value('grb')
                self.on_combo_box_type('grb')
            elif obj.kind == 'excellon':
                # run once to make sure that the obj_type attribute is updated in the FCComboBox
                self.ui.object_type_combo.set_value(1)
                self.on_object_type(1)  # Excellon
                self.ui.box_type_radio.set_value('exc')
                self.on_combo_box_type('exc')
            elif obj.kind == 'geometry':
                # run once to make sure that the obj_type attribute is updated in the FCComboBox
                self.ui.object_type_combo.set_value(2)
                self.on_object_type(2)  # Geometry
                self.ui.box_type_radio.set_value('geo')
                self.on_combo_box_type('geo')

            self.ui.object_combo.set_value(obj_name)
        else:
            self.ui.object_type_combo.set_value(0)
            self.on_object_type(0)  # Gerber

        if self.local_connected is True:
            self.disconnect_events()

        # Show/Hide Advanced Options
        app_mode = self.app.defaults["global_app_level"]
        self.change_level(app_mode)

    def change_level(self, level):
        """

        :param level:   application level: either 'b' or 'a'
        :type level:    str
        :return:
        """

        if level == 'a':
            self.ui.level.setChecked(True)
        else:
            self.ui.level.setChecked(False)
        self.on_level_changed(self.ui.level.isChecked())

    def on_level_changed(self, checked):
        if not checked:
            self.ui.level.setText('%s' % _('Beginner'))
            self.ui.level.setStyleSheet("""
                                        QToolButton
                                        {
                                            color: green;
                                        }
                                        """)

            self.ui.bv_label.hide()
            self.ui.bounds_frame.hide()
            self.ui.center_entry.hide()
            self.ui.center_btn.hide()
            self.ui.calculate_bb_button.hide()
        else:
            self.ui.level.setText('%s' % _('Advanced'))
            self.ui.level.setStyleSheet("""
                                        QToolButton
                                        {
                                            color: red;
                                        }
                                        """)

            self.ui.bv_label.show()
            self.ui.bounds_frame.show()
            self.ui.center_entry.show()
            self.ui.center_btn.show()
            self.ui.calculate_bb_button.show()

    def on_object_type(self, val):
        """
        Will select the actual type of objects: Gerber, Excellon, Geometry

        :param val:     Index in the combobox where 0 = Gerber, 1 = Excellon and 2 = Geometry
        :type val:      int
        :return:        None
        :rtype:         None
        """
        self.ui.object_combo.setRootModelIndex(self.app.collection.index(val, 0, QtCore.QModelIndex()))
        self.ui.object_combo.setCurrentIndex(0)
        self.ui.object_combo.obj_type = {
            0: "Gerber", 1: "Excellon", 2: "Geometry"}[val]

    def on_combo_box_type(self, val):
        obj_type = {'grb': 0, 'exc': 1, 'geo': 2}[val]
        self.ui.box_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.ui.box_combo.setCurrentIndex(0)
        self.ui.box_combo.obj_type = {
            "grb": "Gerber", "exc": "Excellon", "geo": "Geometry"}[val]

    def on_object_selection_changed(self, current, previous):
        found_idx = None
        for tab_idx in range(self.app.ui.notebook.count()):
            if self.app.ui.notebook.tabText(tab_idx) == self.ui.pluginName:
                found_idx = True
                break

        if found_idx:
            try:
                name = current.indexes()[0].internalPointer().obj.options['name']
                kind = current.indexes()[0].internalPointer().obj.kind

                if kind in ['gerber', 'excellon', 'geometry']:
                    index = {'gerber': 0, 'excellon': 1, 'geometry': 2}[kind]
                    self.ui.object_type_combo.set_value(index)

                    obj_type = {'gerber': 'grb', 'excellon': 'exc', 'geometry': 'geo'}[kind]
                    self.ui.box_type_radio.set_value(obj_type)

                    self.ui.object_combo.set_value(name)
            except Exception as err:
                self.app.log.error("DblSidedTool.on_object_selection_changed() --> %s" % str(err))

    def on_create_alignment_holes(self):
        align_type = self.ui.align_type_radio.get_value()
        mode = self.ui.axis_location.get_value()

        if align_type in ["X", "Y"]:
            if mode == "point":
                try:
                    px, py = self.ui.point_entry.get_value()
                except TypeError:
                    msg = '[WARNING_NOTCL] %s' % \
                          _("'Point' reference is selected and 'Point' coordinates are missing.")
                    self.app.inform.emit(msg)
                    return
            elif mode == 'box':
                selection_index = self.ui.box_combo.currentIndex()
                model_index = self.app.collection.index(selection_index, 0, self.ui.object_combo.rootModelIndex())
                try:
                    bb_obj = model_index.internalPointer().obj
                except AttributeError:
                    msg = '[WARNING_NOTCL] %s' % _("Box reference object is missing.")
                    self.app.inform.emit(msg)
                    return

                xmin, ymin, xmax, ymax = bb_obj.bounds()
                px = 0.5 * (xmin + xmax)
                py = 0.5 * (ymin + ymax)
            else:
                msg = '[ERROR_NOTCL] %s' % _("Not supported.")
                self.app.inform.emit(msg)
                return

        dia = self.ui.drill_dia.get_value()
        if dia == '':
            msg = '[WARNING_NOTCL] %s' % _("Drill diameter is missing.")
            self.app.inform.emit(msg)
            return

        # holes = self.alignment_holes.get_value()
        holes = eval('[{}]'.format(self.ui.alignment_holes.text()))
        if not holes:
            msg = '[WARNING_NOTCL] %s' % _("Alignment drill coordinates are missing.")
            self.app.inform.emit(msg)
            return

        tools = {
            1: {
                "tooldia":          dia,
                "drills":           [],
                "solid_geometry":   []
            }
        }

        if align_type in ["X", "Y"]:
            xscale, yscale = {"X": (1.0, -1.0), "Y": (-1.0, 1.0)}[align_type]

            for hole in holes:
                point = Point(hole)
                point_mirror = affinity.scale(point, xscale, yscale, origin=(px, py))

                tools[1]['drills'] += [point, point_mirror]
                tools[1]['solid_geometry'] += [point, point_mirror]
        elif align_type == "manual":
            for hole in holes:
                point = Point(hole)
                tools[1]['drills'].append(point)
                tools[1]['solid_geometry'].append(point.buffer(dia/2))

        def obj_init(obj_inst, app_inst):
            obj_inst.tools = deepcopy(tools)
            obj_inst.create_geometry()
            obj_inst.source_file = app_inst.f_handlers.export_excellon(obj_name=obj_inst.options['name'],
                                                                       local_use=obj_inst,
                                                                       filename=None,
                                                                       use_thread=False)

        ret_val = self.app.app_obj.new_object("excellon", _("Alignment Drills"), obj_init, autoselected=False)
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

        # disable the Notebook while in this feature
        self.app.ui.notebook.setDisabled(True)
        self.app.call_source = "2_sided_tool"

        self.app.inform.emit('%s.' % _("Click on canvas within the desired Excellon drill hole"))
        self.mr = self.canvas.graph_event_connect('mouse_release', self.on_mouse_click_release)

        if self.app.use_3d_engine:
            self.canvas.graph_event_disconnect('mouse_release', self.app.on_mouse_click_release_over_plot)
        else:
            self.canvas.graph_event_disconnect(self.app.mr)

    def on_mouse_click_release(self, event):
        if self.app.use_3d_engine:
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

                                self.on_exit()
                                self.app.inform.emit('[success] %s' % _("Mirror reference point set."))
                                break

        elif event.button == right_button and self.app.event_is_dragging is False:
            self.on_exit(cancelled=True)

    def on_plugin_mouse_click_release(self, pos):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        # if modifiers == QtCore.Qt.KeyboardModifier.ShiftModifier:
        #     clip_val = self.app.clipboard.text()
        #     self.ui.point_entry.set_value(clip_val)
        clip_val = self.app.clipboard.text()

        if modifiers == QtCore.Qt.KeyboardModifier.ControlModifier | QtCore.Qt.KeyboardModifier.ShiftModifier:
            alignment_holes = self.ui.alignment_holes.get_value()
            try:
                eval_clip_val = eval(clip_val)
            except Exception as err:
                self.app.log.debug("DblSidedTool.on_plugin_mouse_click_release() --> %s" % str(err))
                return

            if alignment_holes == '' or alignment_holes is None:
                if isinstance(eval_clip_val, list):
                    altered_clip_val = str(eval_clip_val[-1])
                    self.app.clipboard.setText(altered_clip_val)
                else:
                    altered_clip_val = clip_val
            else:
                if isinstance(eval_clip_val, list):
                    # remove duplicates
                    clean_eval_clip = set(eval_clip_val)
                    # convert to string
                    clip_val = str(list(clean_eval_clip))
                altered_clip_val = clip_val.replace("[", '').replace("]", '')

            self.ui.alignment_holes.set_value(altered_clip_val)
            self.drill_values = altered_clip_val
        elif modifiers == QtCore.Qt.KeyboardModifier.ShiftModifier:
            self.ui.alignment_holes.set_value(clip_val)
            self.drill_values = clip_val

    def on_exit(self, cancelled=None):
        self.app.call_source = "app"
        self.app.ui.notebook.setDisabled(False)
        self.disconnect_events()

        if cancelled is True:
            self.app.delete_selection_shape()
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled by user request."))

    def disconnect_events(self):
        self.app.mr = self.canvas.graph_event_connect('mouse_release', self.app.on_mouse_click_release_over_plot)

        if self.app.use_3d_engine:
            self.canvas.graph_event_disconnect('mouse_release', self.on_mouse_click_release)
        else:
            self.canvas.graph_event_disconnect(self.mr)

        self.local_connected = False

    def on_mirror(self):
        selection_index = self.ui.object_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.ui.object_combo.rootModelIndex())
        try:
            fcobj = model_index.internalPointer().obj
        except Exception:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("No object is selected."))
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

    def on_drill_delete_last(self):
        drill_values_without_last_tupple = self.drill_values.rpartition('(')[0]
        self.drill_values = drill_values_without_last_tupple
        self.ui.alignment_holes.set_value(self.drill_values)

        # adjust the clipboard content too
        try:
            old_clipb = eval(self.app.clipboard.text())
        except Exception:
            # self.log.error("App.on_mouse_and_key_modifiers() --> %s" % str(err))
            old_clipb = None

        if isinstance(old_clipb, list):
            red_clip = old_clipb[:-1]
            clip_text = str(red_clip[0]) if len(red_clip) == 1 else str(red_clip)
        else:
            clip_text = ''
        self.app.clipboard.setText(clip_text)

    def on_toggle_pointbox(self, val):
        if val == "point":
            self.ui.pr_frame.show()
            self.ui.br_frame.hide()
            self.ui.sr_frame.hide()
            self.ui.align_ref_label_val.set_value(self.ui.point_entry.get_value())
        elif val == 'box':
            self.ui.pr_frame.hide()
            self.ui.br_frame.show()
            self.ui.sr_frame.hide()
            self.ui.align_ref_label_val.set_value("Box centroid")
        elif val == 'hole':
            self.ui.pr_frame.hide()
            self.ui.br_frame.hide()
            self.ui.sr_frame.show()

    def on_bbox_coordinates(self):
        xmin = Inf
        ymin = Inf
        xmax = -Inf
        ymax = -Inf

        obj_list = self.app.collection.get_selected()
        if not obj_list:
            selection_index = self.ui.object_combo.currentIndex()
            model_index = self.app.collection.index(selection_index, 0, self.ui.object_combo.rootModelIndex())
            try:
                fcobj = model_index.internalPointer().obj
            except Exception:
                self.app.inform.emit('[ERROR_NOTCL] %s %s' % (_("Failed."), _("No object is selected.")))
                return
            xmin, ymin, xmax, ymax = fcobj.bounds()
        else:
            for obj in obj_list:
                try:
                    gxmin, gymin, gxmax, gymax = obj.bounds()
                    xmin = min([xmin, gxmin])
                    ymin = min([ymin, gymin])
                    xmax = max([xmax, gxmax])
                    ymax = max([ymax, gymax])
                except Exception as e:
                    self.app.log.error("Tried to get bounds of empty geometry in DblSidedTool. %s" % str(e))
                    self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed."))
                    return

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

    pluginName = _("2-Sided")

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
        title_label = FCLabel("%s" % self.pluginName)
        title_label.setStyleSheet("""
                                        QLabel
                                        {
                                            font-size: 16px;
                                            font-weight: bold;
                                        }
                                        """)
        title_label.setToolTip(
            _("Create a Geometry object with\n"
              "toolpaths to cover the space outside the copper pattern.")
        )

        self.title_box.addWidget(title_label)

        # App Level label
        self.level = QtWidgets.QToolButton()
        self.level.setToolTip(
            _(
                "Beginner Mode - many parameters are hidden.\n"
                "Advanced Mode - full control.\n"
                "Permanent change is done in 'Preferences' menu."
            )
        )
        # self.level.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.level.setCheckable(True)
        self.title_box.addWidget(self.level)

        # #############################################################################################################
        # Source Object
        # #############################################################################################################
        self.m_objects_label = FCLabel('<span style="color:darkorange;"><b>%s</b></span>' % _("Source Object"))
        self.m_objects_label.setToolTip('%s.' % _("Objects to be mirrored"))
        self.tools_box.addWidget(self.m_objects_label)

        source_frame = FCFrame()
        self.tools_box.addWidget(source_frame)

        # ## Grid Layout
        obj_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        source_frame.setLayout(obj_grid)

        # Type of object to be cutout
        self.type_obj_combo_label = FCLabel('%s:' % _("Target"))
        self.type_obj_combo_label.setToolTip(
            _("Select the type of application object to be processed in this tool.")
        )

        self.object_type_combo = FCComboBox2()
        self.object_type_combo.addItems([_("Gerber"), _("Excellon"), _("Geometry")])
        obj_grid.addWidget(self.type_obj_combo_label, 0, 0)
        obj_grid.addWidget(self.object_type_combo, 0, 1)

        # ## Gerber Object to mirror
        self.object_combo = FCComboBox()
        self.object_combo.setModel(self.app.collection)
        self.object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.object_combo.is_last = True

        obj_grid.addWidget(self.object_combo, 2, 0, 1, 2)

        # #############################################################################################################
        # ##########    BOUNDS OPERATION    ###########################################################################
        # #############################################################################################################
        self.bv_label = FCLabel('<span style="color:purple;"><b>%s</b></span>' % _('Bounds Values'))
        self.bv_label.setToolTip(
            _("Select on canvas the object(s)\n"
              "for which to calculate bounds values.")
        )
        self.tools_box.addWidget(self.bv_label)

        self.bounds_frame = FCFrame()
        self.tools_box.addWidget(self.bounds_frame)

        grid_bounds = FCGridLayout(v_spacing=5, h_spacing=3)
        self.bounds_frame.setLayout(grid_bounds)

        # Xmin value
        self.xmin_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.xmin_entry.set_precision(self.decimals)
        self.xmin_entry.set_range(-10000.0000, 10000.0000)

        self.xmin_btn = FCButton('%s:' % _("X min"))
        self.xmin_btn.setToolTip(
            _("Minimum location.")
        )
        self.xmin_entry.setReadOnly(True)

        grid_bounds.addWidget(self.xmin_btn, 0, 0)
        grid_bounds.addWidget(self.xmin_entry, 0, 1)

        # Ymin value
        self.ymin_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.ymin_entry.set_precision(self.decimals)
        self.ymin_entry.set_range(-10000.0000, 10000.0000)

        self.ymin_btn = FCButton('%s:' % _("Y min"))
        self.ymin_btn.setToolTip(
            _("Minimum location.")
        )
        self.ymin_entry.setReadOnly(True)

        grid_bounds.addWidget(self.ymin_btn, 2, 0)
        grid_bounds.addWidget(self.ymin_entry, 2, 1)

        # Xmax value
        self.xmax_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.xmax_entry.set_precision(self.decimals)
        self.xmax_entry.set_range(-10000.0000, 10000.0000)

        self.xmax_btn = FCButton('%s:' % _("X max"))
        self.xmax_btn.setToolTip(
            _("Maximum location.")
        )
        self.xmax_entry.setReadOnly(True)

        grid_bounds.addWidget(self.xmax_btn, 4, 0)
        grid_bounds.addWidget(self.xmax_entry, 4, 1)

        # Ymax value
        self.ymax_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.ymax_entry.set_precision(self.decimals)
        self.ymax_entry.set_range(-10000.0000, 10000.0000)

        self.ymax_btn = FCButton('%s:' % _("Y max"))
        self.ymax_btn.setToolTip(
            _("Maximum location.")
        )
        self.ymax_entry.setReadOnly(True)

        grid_bounds.addWidget(self.ymax_btn, 6, 0)
        grid_bounds.addWidget(self.ymax_entry, 6, 1)

        # Center point value
        self.center_entry = NumericalEvalTupleEntry(border_color='#0069A9')
        self.center_entry.setPlaceholderText(_("Center point coordinates"))

        self.center_btn = FCButton('%s:' % _("Centroid"))
        self.center_btn.setToolTip(
            _("The center point location for the rectangular\n"
              "bounding shape. Centroid. Format is (x, y).")
        )
        self.center_entry.setReadOnly(True)

        grid_bounds.addWidget(self.center_btn, 8, 0)
        grid_bounds.addWidget(self.center_entry, 8, 1)

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
        self.tools_box.addWidget(self.calculate_bb_button)

        # #############################################################################################################
        # ##########    MIRROR OPERATION    ###########################################################################
        # #############################################################################################################
        self.param_label = FCLabel('<span style="color:blue;"><b>%s</b></span>' % _("Mirror Operation"))
        self.param_label.setToolTip('%s.' % _("Parameters for the mirror operation"))
        self.tools_box.addWidget(self.param_label)

        mirror_frame = FCFrame()
        self.tools_box.addWidget(mirror_frame)

        grid_mirror = FCGridLayout(v_spacing=5, h_spacing=3)
        mirror_frame.setLayout(grid_mirror)

        # ## Axis
        self.mirax_label = FCLabel('%s:' % _("Axis"))
        self.mirax_label.setToolTip(_("Mirror vertically (X) or horizontally (Y)."))
        self.mirror_axis = RadioSet(
            [
                {'label': 'X', 'value': 'X'},
                {'label': 'Y', 'value': 'Y'}
            ],
            compact=True
        )

        grid_mirror.addWidget(self.mirax_label, 2, 0)
        grid_mirror.addWidget(self.mirror_axis, 2, 1, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        grid_mirror.addWidget(separator_line, 3, 0, 1, 3)

        # ## Reference
        self.axloc_label = FCLabel('<b>%s</b>:' % _("Reference"))
        self.axloc_label.setToolTip(
            _("The coordinates used as reference for the mirror operation.\n"
              "Can be:\n"
              "- Point -> a set of coordinates (x,y) around which the object is mirrored\n"
              "- Box -> a set of coordinates (x, y) obtained from the center of the\n"
              "bounding box of another object selected below\n"
              "- Snap -> a point defined by the center of a drill hole in a Excellon object")
        )
        self.axis_location = RadioSet(
            [
                {'label': _('Point'), 'value': 'point'},
                {'label': _('Box'), 'value': 'box'},
                {'label': _('Snap'), 'value': 'hole'},
            ],
            compact=True
        )

        grid_mirror.addWidget(self.axloc_label, 4, 0)
        grid_mirror.addWidget(self.axis_location, 4, 1, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        grid_mirror.addWidget(separator_line, 7, 0, 1, 3)

        # #############################################################################################################
        # ## Point Reference
        # #############################################################################################################
        self.pr_frame = QtWidgets.QFrame()
        self.pr_frame.setContentsMargins(0, 0, 0, 0)
        grid_mirror.addWidget(self.pr_frame, 9, 0, 1, 3)

        self.point_entry = NumericalEvalTupleEntry(border_color='#0069A9')
        self.point_entry.setPlaceholderText(_("Point coordinates"))

        pr_hlay = QtWidgets.QHBoxLayout()
        pr_hlay.setContentsMargins(0, 0, 0, 0)
        self.pr_frame.setLayout(pr_hlay)

        # Add a reference
        self.add_point_button = QtWidgets.QToolButton()
        self.add_point_button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.add_point_button.setIcon(QtGui.QIcon(self.app.resource_location + '/plus16.png'))
        self.add_point_button.setText(_("Add"))
        self.add_point_button.setToolTip(
            _("Add the coordinates in format <b>(x, y)</b> through which the mirroring axis\n "
              "selected in 'MIRROR AXIS' pass.\n"
              "The (x, y) coordinates are captured by pressing SHIFT key\n"
              "and left mouse button click on canvas or you can enter the coordinates manually.")
        )

        pr_hlay.addWidget(self.point_entry, stretch=1)
        pr_hlay.addWidget(self.add_point_button)

        # #############################################################################################################
        # Box Reference
        # #############################################################################################################
        self.br_frame = QtWidgets.QFrame()
        self.br_frame.setContentsMargins(0, 0, 0, 0)
        grid_mirror.addWidget(self.br_frame, 11, 0, 1, 3)

        grid_box_ref = FCGridLayout(v_spacing=5, h_spacing=3)
        grid_box_ref.setContentsMargins(0, 0, 0, 0)
        self.br_frame.setLayout(grid_box_ref)

        # Type of object used as BOX reference
        self.box_type_radio = RadioSet([{'label': _('Gerber'), 'value': 'grb'},
                                        {'label': _('Excellon'), 'value': 'exc'},
                                        {'label': _('Geometry'), 'value': 'geo'}])
        self.box_type_radio.setToolTip(
            _("It can be of type: Gerber or Excellon or Geometry.\n"
              "The coordinates of the center of the bounding box are used\n"
              "as reference for mirror operation.")
        )
        grid_box_ref.addWidget(self.box_type_radio, 0, 0, 1, 2)

        # Object used as BOX reference
        self.box_combo = FCComboBox()
        self.box_combo.setModel(self.app.collection)
        self.box_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.box_combo.is_last = True

        grid_box_ref.addWidget(self.box_combo, 2, 0, 1, 2)

        # #############################################################################################################
        # Snap Hole Reference
        # #############################################################################################################
        self.sr_frame = QtWidgets.QFrame()
        self.sr_frame.setContentsMargins(0, 0, 0, 0)
        grid_mirror.addWidget(self.sr_frame, 13, 0, 1, 3)

        grid_snap_ref = FCGridLayout(v_spacing=5, h_spacing=3)
        grid_snap_ref.setContentsMargins(0, 0, 0, 0)
        self.sr_frame.setLayout(grid_snap_ref)

        self.exc_hole_lbl = FCLabel('<b>%s</b>:' % _("Excellon"))
        self.exc_hole_lbl.setToolTip(
            _("Object that holds holes that can be picked as reference for mirroring.")
        )

        # Excellon Object that holds the holes
        self.exc_combo = FCComboBox()
        self.exc_combo.setModel(self.app.collection)
        self.exc_combo.setRootModelIndex(self.app.collection.index(1, 0, QtCore.QModelIndex()))
        self.exc_combo.is_last = True

        grid_snap_ref.addWidget(self.exc_hole_lbl, 0, 0, 1, 2)
        grid_snap_ref.addWidget(self.exc_combo, 2, 0, 1, 2)

        self.pick_hole_button = FCButton(_("Pick hole"))
        self.pick_hole_button.setToolTip(
            _("Click inside a drill hole that belong to the selected Excellon object,\n"
              "and the hole center coordinates will be copied to the Point field.")
        )

        grid_snap_ref.addWidget(self.pick_hole_button, 4, 0, 1, 2)

        # #############################################################################################################
        # Mirror Button
        # #############################################################################################################
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
        self.tools_box.addWidget(self.mirror_button)

        # #############################################################################################################
        # ##########    ALIGNMENT OPERATION    ########################################################################
        # #############################################################################################################
        # ## Alignment holes
        self.alignment_label = FCLabel('<span style="color:brown;"><b>%s</b></span>' % _('PCB Alignment'))
        self.alignment_label.setToolTip(
            _("Creates an Excellon Object containing the\n"
              "specified alignment holes and their mirror\n"
              "images.")
        )
        self.tools_box.addWidget(self.alignment_label)

        align_frame = FCFrame()
        self.tools_box.addWidget(align_frame)

        grid4 = FCGridLayout(v_spacing=5, h_spacing=3)
        align_frame.setLayout(grid4)

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

        # ## Alignment Type
        self.align_type_label = FCLabel('%s:' % _("Type"))
        self.align_type_label.setToolTip(
            _("The content of the Excellon file.\n"
              "X - Pairs of drill holes mirrored vertically from reference point\n"
              "Y - Pairs of drill holes mirrored horizontally from reference point\n"
              "Manual - no mirroring; drill holes in place")
        )
        self.align_type_radio = RadioSet(
            [
                {'label': 'X',          'value': 'X'},
                {'label': 'Y',          'value': 'Y'},
                {'label': _("Manual"),  'value': 'manual'}
            ],
            compact=True
        )

        grid4.addWidget(self.align_type_label, 4, 0)
        grid4.addWidget(self.align_type_radio, 4, 1)

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

        # ## Alignment holes
        self.ah_label = FCLabel("%s:" % _('Drill Coordinates'))
        self.ah_label.setToolTip(
            _("Alignment holes (x1, y1), (x2, y2), ... \n"
              "If the type is X or Y then for each pair of coordinates\n"
              "two drill points will be added: one with the given coordinates,\n"
              "and the other will be mirrored as set in the 'Mirror' section.\n"
              "If the type is 'Manual' then no mirror point is generated.\n"
              "\n"
              "Shift + mouse click will add one set of coordinates.\n"
              "Ctrl + Shift + mouse click will accumulate sets of coordinates. ")
        )

        grid4.addWidget(self.ah_label, 8, 0, 1, 2)

        self.alignment_holes = NumericalEvalTupleEntry(border_color='#0069A9')
        self.alignment_holes.setPlaceholderText(_("Drill coordinates"))

        self.delete_drill_point_button = QtWidgets.QToolButton()
        self.delete_drill_point_button.setIcon(QtGui.QIcon(self.app.resource_location + '/trash32.png'))
        self.delete_drill_point_button.setToolTip(
            _("Delete the last coordinates tuple in the list.")
        )

        hlay = QtWidgets.QHBoxLayout()
        hlay.addWidget(self.alignment_holes)
        hlay.addWidget(self.delete_drill_point_button)
        grid4.addLayout(hlay, 9, 0, 1, 2)

        FCGridLayout.set_common_column_size([obj_grid, grid_bounds, grid_mirror, grid_box_ref, grid4], 0)

        # ## Buttons
        self.create_excellon_button = FCButton(_("Create Excellon Object"))
        self.create_excellon_button.setIcon(QtGui.QIcon(self.app.resource_location + '/drill32.png'))
        self.create_excellon_button.setToolTip(
            _("Creates an Excellon Object containing the\n"
              "specified alignment holes and their mirror\n"
              "images.")
        )
        self.create_excellon_button.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        self.tools_box.addWidget(self.create_excellon_button)

        self.tools_box.addStretch(1)

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
        
        
        self.align_type_radio.activated_custom.connect(self.on_align_type_changed)
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
    
    def on_align_type_changed(self, val):
        if val in ["X", "Y"]:
            self.align_ref_label.show()
            self.align_ref_label_val.show()
        else:
            self.align_ref_label.hide()
            self.align_ref_label_val.hide()
