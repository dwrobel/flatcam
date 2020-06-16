
from PyQt5 import QtWidgets, QtCore

from appTool import AppTool
from appGUI.GUIElements import RadioSet, FCDoubleSpinner, EvalEntry, FCEntry, FCButton, FCComboBox

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

        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = DsidedUI(layout=self.layout, app=self.app)
        self.toolName = self.ui.toolName

        # ## Signals
        self.ui.mirror_gerber_button.clicked.connect(self.on_mirror_gerber)
        self.ui.mirror_exc_button.clicked.connect(self.on_mirror_exc)
        self.ui.mirror_geo_button.clicked.connect(self.on_mirror_geo)

        self.ui.add_point_button.clicked.connect(self.on_point_add)
        self.ui.add_drill_point_button.clicked.connect(self.on_drill_add)
        self.ui.delete_drill_point_button.clicked.connect(self.on_drill_delete_last)
        self.ui.box_type_radio.activated_custom.connect(self.on_combo_box_type)

        self.ui.axis_location.group_toggle_fn = self.on_toggle_pointbox

        self.ui.point_entry.textChanged.connect(lambda val: self.ui.align_ref_label_val.set_value(val))

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
        self.ui.box_type_radio.set_value('grb')
        self.on_combo_box_type('grb')

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
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("'Point' reference is selected and 'Point' coordinates "
                                                              "are missing. Add them and retry."))
                return
        else:
            selection_index = self.ui.box_combo.currentIndex()
            model_index = self.app.collection.index(selection_index, 0, self.ui.gerber_object_combo.rootModelIndex())
            try:
                bb_obj = model_index.internalPointer().obj
            except AttributeError:
                model_index = self.app.collection.index(selection_index, 0, self.ui.exc_object_combo.rootModelIndex())
                try:
                    bb_obj = model_index.internalPointer().obj
                except AttributeError:
                    model_index = self.app.collection.index(selection_index, 0,
                                                            self.ui.geo_object_combo.rootModelIndex())
                    try:
                        bb_obj = model_index.internalPointer().obj
                    except AttributeError:
                        self.app.inform.emit(
                            '[WARNING_NOTCL] %s' % _("There is no Box reference object loaded. Load one and retry."))
                        return

            xmin, ymin, xmax, ymax = bb_obj.bounds()
            px = 0.5 * (xmin + xmax)
            py = 0.5 * (ymin + ymax)

        xscale, yscale = {"X": (1.0, -1.0), "Y": (-1.0, 1.0)}[axis]

        dia = float(self.drill_dia.get_value())
        if dia == '':
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("No value or wrong format in Drill Dia entry. Add it and retry."))
            return

        tools = {}
        tools[1] = {}
        tools[1]["tooldia"] = dia
        tools[1]['solid_geometry'] = []

        # holes = self.alignment_holes.get_value()
        holes = eval('[{}]'.format(self.ui.alignment_holes.text()))
        if not holes:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There are no Alignment Drill Coordinates to use. "
                                                          "Add them and retry."))
            return

        for hole in holes:
            point = Point(hole)
            point_mirror = affinity.scale(point, xscale, yscale, origin=(px, py))

            tools[1]['drills'] = [point, point_mirror]
            tools[1]['solid_geometry'].append(point)
            tools[1]['solid_geometry'].append(point_mirror)

        def obj_init(obj_inst, app_inst):
            obj_inst.tools = tools
            obj_inst.create_geometry()
            obj_inst.source_file = app_inst.export_excellon(obj_name=obj_inst.options['name'], local_use=obj_inst,
                                                            filename=None, use_thread=False)

        self.app.app_obj.new_object("excellon", "Alignment Drills", obj_init)
        self.drill_values = ''
        self.app.inform.emit('[success] %s' % _("Excellon object with alignment drills created..."))

    def on_mirror_gerber(self):
        selection_index = self.ui.gerber_object_combo.currentIndex()
        # fcobj = self.app.collection.object_list[selection_index]
        model_index = self.app.collection.index(selection_index, 0, self.ui.gerber_object_combo.rootModelIndex())
        try:
            fcobj = model_index.internalPointer().obj
        except Exception:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Gerber object loaded ..."))
            return

        if fcobj.kind != 'gerber':
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Only Gerber, Excellon and Geometry objects can be mirrored."))
            return

        axis = self.ui.mirror_axis.get_value()
        mode = self.ui.axis_location.get_value()

        if mode == "point":
            try:
                px, py = self.ui.point_entry.get_value()
            except TypeError:
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("There are no Point coordinates in the Point field. "
                                                              "Add coords and try again ..."))
                return

        else:
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

        fcobj.mirror(axis, [px, py])
        self.app.app_obj.object_changed.emit(fcobj)
        fcobj.plot()
        self.app.inform.emit('[success] Gerber %s %s...' % (str(fcobj.options['name']), _("was mirrored")))

    def on_mirror_exc(self):
        selection_index = self.ui.exc_object_combo.currentIndex()
        # fcobj = self.app.collection.object_list[selection_index]
        model_index = self.app.collection.index(selection_index, 0, self.ui.exc_object_combo.rootModelIndex())
        try:
            fcobj = model_index.internalPointer().obj
        except Exception:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Excellon object loaded ..."))
            return

        if fcobj.kind != 'excellon':
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Only Gerber, Excellon and Geometry objects can be mirrored."))
            return

        axis = self.ui.mirror_axis.get_value()
        mode = self.ui.axis_location.get_value()

        if mode == "point":
            try:
                px, py = self.ui.point_entry.get_value()
            except Exception as e:
                log.debug("DblSidedTool.on_mirror_geo() --> %s" % str(e))
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("There are no Point coordinates in the Point field. "
                                                              "Add coords and try again ..."))
                return
        else:
            selection_index_box = self.ui.box_combo.currentIndex()
            model_index_box = self.app.collection.index(selection_index_box, 0, self.ui.box_combo.rootModelIndex())
            try:
                bb_obj = model_index_box.internalPointer().obj
            except Exception as e:
                log.debug("DblSidedTool.on_mirror_geo() --> %s" % str(e))
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Box object loaded ..."))
                return

            xmin, ymin, xmax, ymax = bb_obj.bounds()
            px = 0.5 * (xmin + xmax)
            py = 0.5 * (ymin + ymax)

        fcobj.mirror(axis, [px, py])
        self.app.app_obj.object_changed.emit(fcobj)
        fcobj.plot()
        self.app.inform.emit('[success] Excellon %s %s...' % (str(fcobj.options['name']), _("was mirrored")))

    def on_mirror_geo(self):
        selection_index = self.ui.geo_object_combo.currentIndex()
        # fcobj = self.app.collection.object_list[selection_index]
        model_index = self.app.collection.index(selection_index, 0, self.ui.geo_object_combo.rootModelIndex())
        try:
            fcobj = model_index.internalPointer().obj
        except Exception:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Geometry object loaded ..."))
            return

        if fcobj.kind != 'geometry':
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Only Gerber, Excellon and Geometry objects can be mirrored."))
            return

        axis = self.ui.mirror_axis.get_value()
        mode = self.ui.axis_location.get_value()

        if mode == "point":
            px, py = self.ui.point_entry.get_value()
        else:
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

        fcobj.mirror(axis, [px, py])
        self.app.app_obj.object_changed.emit(fcobj)
        fcobj.plot()
        self.app.inform.emit('[success] Geometry %s %s...' % (str(fcobj.options['name']), _("was mirrored")))

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
        if self.ui.axis_location.get_value() == "point":
            self.ui.point_entry.show()
            self.ui.add_point_button.show()
            self.ui.box_type_label.hide()
            self.ui.box_type_radio.hide()
            self.ui.box_combo.hide()

            self.ui.align_ref_label_val.set_value(self.ui.point_entry.get_value())
        else:
            self.ui.point_entry.hide()
            self.ui.add_point_button.hide()

            self.ui.box_type_label.show()
            self.ui.box_type_radio.show()
            self.ui.box_combo.show()

            self.ui.align_ref_label_val.set_value("Box centroid")

    def on_bbox_coordinates(self):

        xmin = Inf
        ymin = Inf
        xmax = -Inf
        ymax = -Inf

        obj_list = self.app.collection.get_selected()

        if not obj_list:
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed. No object(s) selected..."))
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
        self.ui.gerber_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.ui.exc_object_combo.setRootModelIndex(self.app.collection.index(1, 0, QtCore.QModelIndex()))
        self.ui.geo_object_combo.setRootModelIndex(self.app.collection.index(2, 0, QtCore.QModelIndex()))
        self.ui.box_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))

        self.ui.gerber_object_combo.setCurrentIndex(0)
        self.ui.exc_object_combo.setCurrentIndex(0)
        self.ui.geo_object_combo.setCurrentIndex(0)
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
        title_label = QtWidgets.QLabel("%s" % self.toolName)
        title_label.setStyleSheet("""
                                QLabel
                                {
                                    font-size: 16px;
                                    font-weight: bold;
                                }
                                """)
        self.layout.addWidget(title_label)

        self.layout.addWidget(QtWidgets.QLabel(""))

        # ## Grid Layout
        grid_lay = QtWidgets.QGridLayout()
        grid_lay.setColumnStretch(0, 1)
        grid_lay.setColumnStretch(1, 0)
        self.layout.addLayout(grid_lay)

        # Objects to be mirrored
        self.m_objects_label = QtWidgets.QLabel("<b>%s:</b>" % _("Mirror Operation"))
        self.m_objects_label.setToolTip('%s.' % _("Objects to be mirrored"))

        grid_lay.addWidget(self.m_objects_label, 0, 0, 1, 2)

        # ## Gerber Object to mirror
        self.gerber_object_combo = FCComboBox()
        self.gerber_object_combo.setModel(self.app.collection)
        self.gerber_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.gerber_object_combo.is_last = True
        self.gerber_object_combo.obj_type = "Gerber"

        self.botlay_label = QtWidgets.QLabel("%s:" % _("GERBER"))
        self.botlay_label.setToolTip('%s.' % _("Gerber to be mirrored"))

        self.mirror_gerber_button = QtWidgets.QPushButton(_("Mirror"))
        self.mirror_gerber_button.setToolTip(
            _("Mirrors (flips) the specified object around \n"
              "the specified axis. Does not create a new \n"
              "object, but modifies it.")
        )
        self.mirror_gerber_button.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        self.mirror_gerber_button.setMinimumWidth(60)

        grid_lay.addWidget(self.botlay_label, 1, 0)
        grid_lay.addWidget(self.gerber_object_combo, 2, 0)
        grid_lay.addWidget(self.mirror_gerber_button, 2, 1)

        # ## Excellon Object to mirror
        self.exc_object_combo = FCComboBox()
        self.exc_object_combo.setModel(self.app.collection)
        self.exc_object_combo.setRootModelIndex(self.app.collection.index(1, 0, QtCore.QModelIndex()))
        self.exc_object_combo.is_last = True
        self.exc_object_combo.obj_type = "Excellon"

        self.excobj_label = QtWidgets.QLabel("%s:" % _("EXCELLON"))
        self.excobj_label.setToolTip(_("Excellon Object to be mirrored."))

        self.mirror_exc_button = QtWidgets.QPushButton(_("Mirror"))
        self.mirror_exc_button.setToolTip(
            _("Mirrors (flips) the specified object around \n"
              "the specified axis. Does not create a new \n"
              "object, but modifies it.")
        )
        self.mirror_exc_button.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        self.mirror_exc_button.setMinimumWidth(60)

        grid_lay.addWidget(self.excobj_label, 3, 0)
        grid_lay.addWidget(self.exc_object_combo, 4, 0)
        grid_lay.addWidget(self.mirror_exc_button, 4, 1)

        # ## Geometry Object to mirror
        self.geo_object_combo = FCComboBox()
        self.geo_object_combo.setModel(self.app.collection)
        self.geo_object_combo.setRootModelIndex(self.app.collection.index(2, 0, QtCore.QModelIndex()))
        self.geo_object_combo.is_last = True
        self.geo_object_combo.obj_type = "Geometry"

        self.geoobj_label = QtWidgets.QLabel("%s:" % _("GEOMETRY"))
        self.geoobj_label.setToolTip(
            _("Geometry Obj to be mirrored.")
        )

        self.mirror_geo_button = QtWidgets.QPushButton(_("Mirror"))
        self.mirror_geo_button.setToolTip(
            _("Mirrors (flips) the specified object around \n"
              "the specified axis. Does not create a new \n"
              "object, but modifies it.")
        )
        self.mirror_geo_button.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        self.mirror_geo_button.setMinimumWidth(60)

        # grid_lay.addRow("Bottom Layer:", self.object_combo)
        grid_lay.addWidget(self.geoobj_label, 5, 0)
        grid_lay.addWidget(self.geo_object_combo, 6, 0)
        grid_lay.addWidget(self.mirror_geo_button, 6, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line, 7, 0, 1, 2)

        self.layout.addWidget(QtWidgets.QLabel(""))

        # ## Grid Layout
        grid_lay1 = QtWidgets.QGridLayout()
        grid_lay1.setColumnStretch(0, 0)
        grid_lay1.setColumnStretch(1, 1)
        self.layout.addLayout(grid_lay1)

        # Objects to be mirrored
        self.param_label = QtWidgets.QLabel("<b>%s:</b>" % _("Mirror Parameters"))
        self.param_label.setToolTip('%s.' % _("Parameters for the mirror operation"))

        grid_lay1.addWidget(self.param_label, 0, 0, 1, 2)

        # ## Axis
        self.mirax_label = QtWidgets.QLabel('%s:' % _("Mirror Axis"))
        self.mirax_label.setToolTip(_("Mirror vertically (X) or horizontally (Y)."))
        self.mirror_axis = RadioSet([{'label': 'X', 'value': 'X'},
                                     {'label': 'Y', 'value': 'Y'}])

        grid_lay1.addWidget(self.mirax_label, 2, 0)
        grid_lay1.addWidget(self.mirror_axis, 2, 1, 1, 2)

        # ## Axis Location
        self.axloc_label = QtWidgets.QLabel('%s:' % _("Reference"))
        self.axloc_label.setToolTip(
            _("The coordinates used as reference for the mirror operation.\n"
              "Can be:\n"
              "- Point -> a set of coordinates (x,y) around which the object is mirrored\n"
              "- Box -> a set of coordinates (x, y) obtained from the center of the\n"
              "bounding box of another object selected below")
        )
        self.axis_location = RadioSet([{'label': _('Point'), 'value': 'point'},
                                       {'label': _('Box'), 'value': 'box'}])

        grid_lay1.addWidget(self.axloc_label, 4, 0)
        grid_lay1.addWidget(self.axis_location, 4, 1, 1, 2)

        # ## Point/Box
        self.point_entry = EvalEntry()
        self.point_entry.setPlaceholderText(_("Point coordinates"))

        # Add a reference
        self.add_point_button = QtWidgets.QPushButton(_("Add"))
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

        grid_lay1.addWidget(self.point_entry, 7, 0, 1, 2)
        grid_lay1.addWidget(self.add_point_button, 7, 2)

        # ## Grid Layout
        grid_lay2 = QtWidgets.QGridLayout()
        grid_lay2.setColumnStretch(0, 0)
        grid_lay2.setColumnStretch(1, 1)
        self.layout.addLayout(grid_lay2)

        self.box_type_label = QtWidgets.QLabel('%s:' % _("Reference Object"))
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

        grid_lay2.addWidget(self.box_type_label, 0, 0, 1, 2)
        grid_lay2.addWidget(self.box_type_radio, 1, 0, 1, 2)

        # Object used as BOX reference
        self.box_combo = FCComboBox()
        self.box_combo.setModel(self.app.collection)
        self.box_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.box_combo.is_last = True

        self.box_combo.hide()

        grid_lay2.addWidget(self.box_combo, 3, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay2.addWidget(separator_line, 4, 0, 1, 2)

        grid_lay2.addWidget(QtWidgets.QLabel(""), 5, 0, 1, 2)

        # ## Title Bounds Values
        self.bv_label = QtWidgets.QLabel("<b>%s:</b>" % _('Bounds Values'))
        self.bv_label.setToolTip(
            _("Select on canvas the object(s)\n"
              "for which to calculate bounds values.")
        )
        grid_lay2.addWidget(self.bv_label, 6, 0, 1, 2)

        # Xmin value
        self.xmin_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.xmin_entry.set_precision(self.decimals)
        self.xmin_entry.set_range(-9999.9999, 9999.9999)

        self.xmin_btn = FCButton('%s:' % _("X min"))
        self.xmin_btn.setToolTip(
            _("Minimum location.")
        )
        self.xmin_entry.setReadOnly(True)

        grid_lay2.addWidget(self.xmin_btn, 7, 0)
        grid_lay2.addWidget(self.xmin_entry, 7, 1)

        # Ymin value
        self.ymin_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.ymin_entry.set_precision(self.decimals)
        self.ymin_entry.set_range(-9999.9999, 9999.9999)

        self.ymin_btn = FCButton('%s:' % _("Y min"))
        self.ymin_btn.setToolTip(
            _("Minimum location.")
        )
        self.ymin_entry.setReadOnly(True)

        grid_lay2.addWidget(self.ymin_btn, 8, 0)
        grid_lay2.addWidget(self.ymin_entry, 8, 1)

        # Xmax value
        self.xmax_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.xmax_entry.set_precision(self.decimals)
        self.xmax_entry.set_range(-9999.9999, 9999.9999)

        self.xmax_btn = FCButton('%s:' % _("X max"))
        self.xmax_btn.setToolTip(
            _("Maximum location.")
        )
        self.xmax_entry.setReadOnly(True)

        grid_lay2.addWidget(self.xmax_btn, 9, 0)
        grid_lay2.addWidget(self.xmax_entry, 9, 1)

        # Ymax value
        self.ymax_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.ymax_entry.set_precision(self.decimals)
        self.ymax_entry.set_range(-9999.9999, 9999.9999)

        self.ymax_btn = FCButton('%s:' % _("Y max"))
        self.ymax_btn.setToolTip(
            _("Maximum location.")
        )
        self.ymax_entry.setReadOnly(True)

        grid_lay2.addWidget(self.ymax_btn, 10, 0)
        grid_lay2.addWidget(self.ymax_entry, 10, 1)

        # Center point value
        self.center_entry = FCEntry()
        self.center_entry.setPlaceholderText(_("Center point coordinates"))

        self.center_btn = FCButton('%s:' % _("Centroid"))
        self.center_btn.setToolTip(
            _("The center point location for the rectangular\n"
              "bounding shape. Centroid. Format is (x, y).")
        )
        self.center_entry.setReadOnly(True)

        grid_lay2.addWidget(self.center_btn, 12, 0)
        grid_lay2.addWidget(self.center_entry, 12, 1)

        # Calculate Bounding box
        self.calculate_bb_button = QtWidgets.QPushButton(_("Calculate Bounds Values"))
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
        grid_lay2.addWidget(self.calculate_bb_button, 13, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay2.addWidget(separator_line, 14, 0, 1, 2)

        grid_lay2.addWidget(QtWidgets.QLabel(""), 15, 0, 1, 2)

        # ## Alignment holes
        self.alignment_label = QtWidgets.QLabel("<b>%s:</b>" % _('PCB Alignment'))
        self.alignment_label.setToolTip(
            _("Creates an Excellon Object containing the\n"
              "specified alignment holes and their mirror\n"
              "images.")
        )
        grid_lay2.addWidget(self.alignment_label, 25, 0, 1, 2)

        # ## Drill diameter for alignment holes
        self.dt_label = QtWidgets.QLabel("%s:" % _('Drill Diameter'))
        self.dt_label.setToolTip(
            _("Diameter of the drill for the alignment holes.")
        )

        self.drill_dia = FCDoubleSpinner(callback=self.confirmation_message)
        self.drill_dia.setToolTip(
            _("Diameter of the drill for the alignment holes.")
        )
        self.drill_dia.set_precision(self.decimals)
        self.drill_dia.set_range(0.0000, 9999.9999)

        grid_lay2.addWidget(self.dt_label, 26, 0)
        grid_lay2.addWidget(self.drill_dia, 26, 1)

        # ## Alignment Axis
        self.align_ax_label = QtWidgets.QLabel('%s:' % _("Align Axis"))
        self.align_ax_label.setToolTip(
            _("Mirror vertically (X) or horizontally (Y).")
        )
        self.align_axis_radio = RadioSet([{'label': 'X', 'value': 'X'},
                                          {'label': 'Y', 'value': 'Y'}])

        grid_lay2.addWidget(self.align_ax_label, 27, 0)
        grid_lay2.addWidget(self.align_axis_radio, 27, 1)

        # ## Alignment Reference Point
        self.align_ref_label = QtWidgets.QLabel('%s:' % _("Reference"))
        self.align_ref_label.setToolTip(
            _("The reference point used to create the second alignment drill\n"
              "from the first alignment drill, by doing mirror.\n"
              "It can be modified in the Mirror Parameters -> Reference section")
        )

        self.align_ref_label_val = EvalEntry()
        self.align_ref_label_val.setToolTip(
            _("The reference point used to create the second alignment drill\n"
              "from the first alignment drill, by doing mirror.\n"
              "It can be modified in the Mirror Parameters -> Reference section")
        )
        self.align_ref_label_val.setDisabled(True)

        grid_lay2.addWidget(self.align_ref_label, 28, 0)
        grid_lay2.addWidget(self.align_ref_label_val, 28, 1)

        grid_lay4 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid_lay4)

        # ## Alignment holes
        self.ah_label = QtWidgets.QLabel("%s:" % _('Alignment Drill Coordinates'))
        self.ah_label.setToolTip(
            _("Alignment holes (x1, y1), (x2, y2), ... "
              "on one side of the mirror axis. For each set of (x, y) coordinates\n"
              "entered here, a pair of drills will be created:\n\n"
              "- one drill at the coordinates from the field\n"
              "- one drill in mirror position over the axis selected above in the 'Align Axis'.")
        )

        self.alignment_holes = EvalEntry()
        self.alignment_holes.setPlaceholderText(_("Drill coordinates"))

        grid_lay4.addWidget(self.ah_label, 0, 0, 1, 2)
        grid_lay4.addWidget(self.alignment_holes, 1, 0, 1, 2)

        self.add_drill_point_button = FCButton(_("Add"))
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
        self.delete_drill_point_button.setToolTip(
            _("Delete the last coordinates tuple in the list.")
        )
        drill_hlay = QtWidgets.QHBoxLayout()

        drill_hlay.addWidget(self.add_drill_point_button)
        drill_hlay.addWidget(self.delete_drill_point_button)

        grid_lay4.addLayout(drill_hlay, 2, 0, 1, 2)

        # ## Buttons
        self.create_alignment_hole_button = QtWidgets.QPushButton(_("Create Excellon Object"))
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
