# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 5/17/2020                                         #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtCore, QtGui

from appTool import AppTool
from appGUI.GUIElements import FCDoubleSpinner, FCCheckBox, FCComboBox, FCButton, RadioSet, FCLabel

from shapely.geometry import MultiPolygon, LineString, Point
from shapely.ops import unary_union

from copy import deepcopy
import logging

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class ToolCorners(AppTool):

    def __init__(self, app):
        AppTool.__init__(self, app)

        self.app = app
        self.canvas = self.app.plotcanvas

        self.decimals = self.app.decimals
        self.units = ''

        # here we store the locations of the selected corners
        self.points = {}

        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = CornersUI(layout=self.layout, app=self.app)
        self.toolName = self.ui.toolName

        # Objects involved in Copper thieving
        self.grb_object = None

        # store the flattened geometry here:
        self.flat_geometry = []

        # Tool properties
        self.fid_dia = None

        self.grb_steps_per_circle = self.app.defaults["gerber_circle_steps"]

        # SIGNALS
        self.ui.add_marker_button.clicked.connect(self.add_markers)
        self.ui.toggle_all_cb.toggled.connect(self.on_toggle_all)
        self.ui.drill_button.clicked.connect(self.on_create_drill_object)

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolCorners()")

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

        self.app.ui.notebook.setTabText(2, _("Corners Tool"))

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Alt+M', **kwargs)

    def set_tool_ui(self):
        self.units = self.app.defaults['units']
        self.ui.thick_entry.set_value(self.app.defaults["tools_corners_thickness"])
        self.ui.l_entry.set_value(float(self.app.defaults["tools_corners_length"]))
        self.ui.margin_entry.set_value(float(self.app.defaults["tools_corners_margin"]))
        self.ui.toggle_all_cb.set_value(False)
        self.ui.type_radio.set_value(self.app.defaults["tools_corners_type"])
        self.ui.drill_dia_entry.set_value(self.app.defaults["tools_corners_drill_dia"])

    def on_toggle_all(self, val):
        self.ui.bl_cb.set_value(val)
        self.ui.br_cb.set_value(val)
        self.ui.tl_cb.set_value(val)
        self.ui.tr_cb.set_value(val)

    def add_markers(self):
        self.app.call_source = "corners_tool"
        tl_state = self.ui.tl_cb.get_value()
        tr_state = self.ui.tr_cb.get_value()
        bl_state = self.ui.bl_cb.get_value()
        br_state = self.ui.br_cb.get_value()

        # get the Gerber object on which the corner marker will be inserted
        selection_index = self.ui.object_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.ui.object_combo.rootModelIndex())

        try:
            self.grb_object = model_index.internalPointer().obj
        except Exception as e:
            log.debug("ToolCorners.add_markers() --> %s" % str(e))
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Gerber object loaded ..."))
            self.app.call_source = "app"
            return

        xmin, ymin, xmax, ymax = self.grb_object.bounds()
        self.points = {}
        if tl_state:
            self.points['tl'] = (xmin, ymax)
        if tr_state:
            self.points['tr'] = (xmax, ymax)
        if bl_state:
            self.points['bl'] = (xmin, ymin)
        if br_state:
            self.points['br'] = (xmax, ymin)

        ret_val = self.add_corners_geo(self.points, g_obj=self.grb_object)
        self.app.call_source = "app"
        if ret_val == 'fail':
            self.app.call_source = "app"
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed."))
            return

        self.on_exit(ret_val)

    def add_corners_geo(self, points_storage, g_obj):
        """
        Add geometry to the solid_geometry of the copper Gerber object

        :param points_storage:  a dictionary holding the points where to add corners
        :param g_obj:           the Gerber object where to add the geometry
        :return:                None
        """

        marker_type = self.ui.type_radio.get_value()
        line_thickness = self.ui.thick_entry.get_value()
        margin = self.ui.margin_entry.get_value()
        line_length = self.ui.l_entry.get_value() / 2.0

        geo_list = []

        if not points_storage:
            self.app.inform.emit("[ERROR_NOTCL] %s." % _("Please select at least a location"))
            return 'fail'

        for key in points_storage:
            if key == 'tl':
                pt = points_storage[key]
                x = pt[0] - margin - line_thickness / 2.0
                y = pt[1] + margin + line_thickness / 2.0
                if marker_type == 's':
                    line_geo_hor = LineString([
                        (x, y), (x + line_length, y)
                    ])
                    line_geo_vert = LineString([
                        (x, y), (x, y - line_length)
                    ])
                else:
                    line_geo_hor = LineString([
                        (x - line_length, y), (x + line_length, y)
                    ])
                    line_geo_vert = LineString([
                        (x, y + line_length), (x, y - line_length)
                    ])
                geo_list.append(line_geo_hor)
                geo_list.append(line_geo_vert)
            if key == 'tr':
                pt = points_storage[key]
                x = pt[0] + margin + line_thickness / 2.0
                y = pt[1] + margin + line_thickness / 2.0
                if marker_type == 's':
                    line_geo_hor = LineString([
                        (x, y), (x - line_length, y)
                    ])
                    line_geo_vert = LineString([
                        (x, y), (x, y - line_length)
                    ])
                else:
                    line_geo_hor = LineString([
                        (x + line_length, y), (x - line_length, y)
                    ])
                    line_geo_vert = LineString([
                        (x, y + line_length), (x, y - line_length)
                    ])
                geo_list.append(line_geo_hor)
                geo_list.append(line_geo_vert)
            if key == 'bl':
                pt = points_storage[key]
                x = pt[0] - margin - line_thickness / 2.0
                y = pt[1] - margin - line_thickness / 2.0
                if marker_type == 's':
                    line_geo_hor = LineString([
                        (x, y), (x + line_length, y)
                    ])
                    line_geo_vert = LineString([
                        (x, y), (x, y + line_length)
                    ])
                else:
                    line_geo_hor = LineString([
                        (x - line_length, y), (x + line_length, y)
                    ])
                    line_geo_vert = LineString([
                        (x, y - line_length), (x, y + line_length)
                    ])
                geo_list.append(line_geo_hor)
                geo_list.append(line_geo_vert)
            if key == 'br':
                pt = points_storage[key]
                x = pt[0] + margin + line_thickness / 2.0
                y = pt[1] - margin - line_thickness / 2.0
                if marker_type == 's':
                    line_geo_hor = LineString([
                        (x, y), (x - line_length, y)
                    ])
                    line_geo_vert = LineString([
                        (x, y), (x, y + line_length)
                    ])
                else:
                    line_geo_hor = LineString([
                        (x + line_length, y), (x - line_length, y)
                    ])
                    line_geo_vert = LineString([
                        (x, y - line_length), (x, y + line_length)
                    ])
                geo_list.append(line_geo_hor)
                geo_list.append(line_geo_vert)

        new_apertures = deepcopy(g_obj.apertures)

        aperture_found = None
        for ap_id, ap_val in new_apertures.items():
            if ap_val['type'] == 'C' and ap_val['size'] == line_thickness:
                aperture_found = ap_id
                break

        geo_buff_list = []
        if aperture_found:
            for geo in geo_list:
                geo_buff = geo.buffer(line_thickness / 2.0, resolution=self.grb_steps_per_circle, join_style=2)
                geo_buff_list.append(geo_buff)

                dict_el = {'follow': geo, 'solid': geo_buff}
                new_apertures[aperture_found]['geometry'].append(deepcopy(dict_el))
        else:
            ap_keys = list(new_apertures.keys())
            if ap_keys:
                new_apid = str(int(max(ap_keys)) + 1)
            else:
                new_apid = '10'

            new_apertures[new_apid] = {}
            new_apertures[new_apid]['type'] = 'C'
            new_apertures[new_apid]['size'] = line_thickness
            new_apertures[new_apid]['geometry'] = []

            for geo in geo_list:
                geo_buff = geo.buffer(line_thickness / 2.0, resolution=self.grb_steps_per_circle, join_style=3)
                geo_buff_list.append(geo_buff)

                dict_el = {'follow': geo, 'solid': geo_buff}
                new_apertures[new_apid]['geometry'].append(deepcopy(dict_el))

        s_list = []
        if g_obj.solid_geometry:
            try:
                for poly in g_obj.solid_geometry:
                    s_list.append(poly)
            except TypeError:
                s_list.append(g_obj.solid_geometry)

        geo_buff_list = MultiPolygon(geo_buff_list)
        geo_buff_list = geo_buff_list.buffer(0)
        try:
            for poly in geo_buff_list:
                s_list.append(poly)
        except TypeError:
            s_list.append(geo_buff_list)

        outname = '%s_%s' % (str(self.grb_object.options['name']), 'corners')

        def initialize(grb_obj, app_obj):
            grb_obj.options = {}
            for opt in g_obj.options:
                if opt != 'name':
                    grb_obj.options[opt] = deepcopy(g_obj.options[opt])
            grb_obj.options['name'] = outname
            grb_obj.multitool = False
            grb_obj.multigeo = False
            grb_obj.follow = deepcopy(g_obj.follow)
            grb_obj.apertures = new_apertures
            grb_obj.solid_geometry = unary_union(s_list)
            grb_obj.follow_geometry = deepcopy(g_obj.follow_geometry) + geo_list

            grb_obj.source_file = app_obj.f_handlers.export_gerber(obj_name=outname, filename=None, local_use=grb_obj,
                                                                   use_thread=False)

        ret = self.app.app_obj.new_object('gerber', outname, initialize, plot=True)

        return ret

    def on_create_drill_object(self):
        self.app.call_source = "corners_tool"

        tooldia = self.ui.drill_dia_entry.get_value()

        if tooldia == 0:
            self.app.inform.emit('[WARNING_NOTCL] %s %s' % (_("Cancelled."), _("The tool diameter is zero.")))
            return

        line_thickness = self.ui.thick_entry.get_value()
        margin = self.ui.margin_entry.get_value()
        tl_state = self.ui.tl_cb.get_value()
        tr_state = self.ui.tr_cb.get_value()
        bl_state = self.ui.bl_cb.get_value()
        br_state = self.ui.br_cb.get_value()

        # get the Gerber object on which the corner marker will be inserted
        selection_index = self.ui.object_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.ui.object_combo.rootModelIndex())

        try:
            self.grb_object = model_index.internalPointer().obj
        except Exception as e:
            log.debug("ToolCorners.add_markers() --> %s" % str(e))
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Gerber object loaded ..."))
            self.app.call_source = "app"
            return

        if tl_state is False and tr_state is False and bl_state is False and br_state is False:
            self.app.inform.emit("[ERROR_NOTCL] %s." % _("Please select at least a location"))
            self.app.call_source = "app"
            return

        xmin, ymin, xmax, ymax = self.grb_object.bounds()

        # list of (x,y) tuples. Store here the drill coordinates
        drill_list = []

        if tl_state:
            x = xmin - margin - line_thickness / 2.0
            y = ymax + margin + line_thickness / 2.0
            drill_list.append(
                Point((x, y))
            )

        if tr_state:
            x = xmax + margin + line_thickness / 2.0
            y = ymax + margin + line_thickness / 2.0
            drill_list.append(
                Point((x, y))
            )

        if bl_state:
            x = xmin - margin - line_thickness / 2.0
            y = ymin - margin - line_thickness / 2.0
            drill_list.append(
                Point((x, y))
            )

        if br_state:
            x = xmax + margin + line_thickness / 2.0
            y = ymin - margin - line_thickness / 2.0
            drill_list.append(
                Point((x, y))
            )

        tools = {1: {}}
        tools[1]["tooldia"] = tooldia
        tools[1]['drills'] = drill_list
        tools[1]['solid_geometry'] = []

        def obj_init(obj_inst, app_inst):
            obj_inst.options.update({
                'name': outname
            })
            obj_inst.tools = deepcopy(tools)
            obj_inst.create_geometry()
            obj_inst.source_file = app_inst.f_handlers.export_excellon(obj_name=obj_inst.options['name'],
                                                                       local_use=obj_inst,
                                                                       filename=None,
                                                                       use_thread=False)

        outname = '%s_%s' % (str(self.grb_object.options['name']), 'corner_drills')
        ret_val = self.app.app_obj.new_object("excellon", outname, obj_init)

        self.app.call_source = "app"
        if ret_val == 'fail':
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed."))
        else:
            self.app.inform.emit('[success] %s' % _("Excellon object with corner drills created."))

    def replot(self, obj, run_thread=True):
        def worker_task():
            with self.app.proc_container.new('%s ...' % _("Plotting")):
                obj.plot()
                self.app.app_obj.object_plotted.emit(obj)

        if run_thread:
            self.app.worker_task.emit({'fcn': worker_task, 'params': []})
        else:
            worker_task()

    def on_exit(self, corner_gerber_obj=None):
        # plot the object
        if corner_gerber_obj:
            try:
                for ob in corner_gerber_obj:
                    self.replot(obj=ob)
            except (AttributeError, TypeError):
                self.replot(obj=corner_gerber_obj)
            except Exception:
                return

        # update the bounding box values
        try:
            a, b, c, d = self.grb_object.bounds()
            self.grb_object.options['xmin'] = a
            self.grb_object.options['ymin'] = b
            self.grb_object.options['xmax'] = c
            self.grb_object.options['ymax'] = d
        except Exception as e:
            log.debug("ToolCorners.on_exit() copper_obj bounds error --> %s" % str(e))

        self.app.call_source = "app"
        self.app.inform.emit('[success] %s' % _("A Gerber object with corner markers was created."))


class CornersUI:

    toolName = _("Corner Markers Tool")

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

        # Gerber object #
        self.object_label = FCLabel('<b>%s:</b>' % _("GERBER"))
        self.object_label.setToolTip(
            _("The Gerber object to which will be added corner markers.")
        )
        self.object_combo = FCComboBox()
        self.object_combo.setModel(self.app.collection)
        self.object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.object_combo.is_last = True
        self.object_combo.obj_type = "Gerber"

        self.layout.addWidget(self.object_label)
        self.layout.addWidget(self.object_combo)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.layout.addWidget(separator_line)

        self.points_label = FCLabel('<b>%s:</b>' % _('Locations'))
        self.points_label.setToolTip(
            _("Locations where to place corner markers.")
        )
        self.layout.addWidget(self.points_label)

        # ## Grid Layout
        grid_loc = QtWidgets.QGridLayout()
        self.layout.addLayout(grid_loc)

        # TOP LEFT
        self.tl_cb = FCCheckBox(_("Top Left"))
        grid_loc.addWidget(self.tl_cb, 0, 0)

        # TOP RIGHT
        self.tr_cb = FCCheckBox(_("Top Right"))
        grid_loc.addWidget(self.tr_cb, 0, 1)

        # BOTTOM LEFT
        self.bl_cb = FCCheckBox(_("Bottom Left"))
        grid_loc.addWidget(self.bl_cb, 1, 0)

        # BOTTOM RIGHT
        self.br_cb = FCCheckBox(_("Bottom Right"))
        grid_loc.addWidget(self.br_cb, 1, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.layout.addWidget(separator_line)

        # Toggle ALL
        self.toggle_all_cb = FCCheckBox(_("Toggle ALL"))
        self.layout.addWidget(self.toggle_all_cb)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.layout.addWidget(separator_line)

        # ## Grid Layout
        grid_lay = QtWidgets.QGridLayout()
        self.layout.addLayout(grid_lay)
        grid_lay.setColumnStretch(0, 0)
        grid_lay.setColumnStretch(1, 1)

        self.param_label = FCLabel('<b>%s:</b>' % _('Parameters'))
        self.param_label.setToolTip(
            _("Parameters used for this tool.")
        )
        grid_lay.addWidget(self.param_label, 0, 0, 1, 2)

        # Type of Marker
        self.type_label = FCLabel('%s:' % _("Type"))
        self.type_label.setToolTip(
            _("Shape of the marker.")
        )

        self.type_radio = RadioSet([
            {"label": _("Semi-Cross"), "value": "s"},
            {"label": _("Cross"), "value": "c"},
        ])

        grid_lay.addWidget(self.type_label, 2, 0)
        grid_lay.addWidget(self.type_radio, 2, 1)

        # Thickness #
        self.thick_label = FCLabel('%s:' % _("Thickness"))
        self.thick_label.setToolTip(
            _("The thickness of the line that makes the corner marker.")
        )
        self.thick_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.thick_entry.set_range(0.0000, 10.0000)
        self.thick_entry.set_precision(self.decimals)
        self.thick_entry.setWrapping(True)
        self.thick_entry.setSingleStep(10 ** -self.decimals)

        grid_lay.addWidget(self.thick_label, 4, 0)
        grid_lay.addWidget(self.thick_entry, 4, 1)

        # Length #
        self.l_label = FCLabel('%s:' % _("Length"))
        self.l_label.setToolTip(
            _("The length of the line that makes the corner marker.")
        )
        self.l_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.l_entry.set_range(-10000.0000, 10000.0000)
        self.l_entry.set_precision(self.decimals)
        self.l_entry.setSingleStep(10 ** -self.decimals)

        grid_lay.addWidget(self.l_label, 6, 0)
        grid_lay.addWidget(self.l_entry, 6, 1)

        # Margin #
        self.margin_label = FCLabel('%s:' % _("Margin"))
        self.margin_label.setToolTip(
            _("Bounding box margin.")
        )
        self.margin_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.margin_entry.set_range(-10000.0000, 10000.0000)
        self.margin_entry.set_precision(self.decimals)
        self.margin_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.margin_label, 8, 0)
        grid_lay.addWidget(self.margin_entry, 8, 1)

        # separator_line_2 = QtWidgets.QFrame()
        # separator_line_2.setFrameShape(QtWidgets.QFrame.HLine)
        # separator_line_2.setFrameShadow(QtWidgets.QFrame.Sunken)
        # grid_lay.addWidget(separator_line_2, 10, 0, 1, 2)

        # ## Insert Corner Marker
        self.add_marker_button = FCButton(_("Add Marker"))
        self.add_marker_button.setIcon(QtGui.QIcon(self.app.resource_location + '/corners_32.png'))
        self.add_marker_button.setToolTip(
            _("Will add corner markers to the selected Gerber file.")
        )
        self.add_marker_button.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        grid_lay.addWidget(self.add_marker_button, 12, 0, 1, 2)

        separator_line_2 = QtWidgets.QFrame()
        separator_line_2.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line_2.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line_2, 14, 0, 1, 2)

        # Drill is corners
        self.drills_label = FCLabel('<b>%s:</b>' % _('Drills in Corners'))
        grid_lay.addWidget(self.drills_label, 16, 0, 1, 2)

        # Drill Tooldia #
        self.drill_dia_label = FCLabel('%s:' % _("Drill Dia"))
        self.drill_dia_label.setToolTip(
            '%s.' % _("Drill Diameter")
        )
        self.drill_dia_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.drill_dia_entry.set_range(0.0000, 100.0000)
        self.drill_dia_entry.set_precision(self.decimals)
        self.drill_dia_entry.setWrapping(True)

        grid_lay.addWidget(self.drill_dia_label, 18, 0)
        grid_lay.addWidget(self.drill_dia_entry, 18, 1)

        # ## Create an Excellon object
        self.drill_button = FCButton(_("Create Excellon Object"))
        self.drill_button.setIcon(QtGui.QIcon(self.app.resource_location + '/drill32.png'))
        self.drill_button.setToolTip(
            _("Will add drill holes in the center of the markers.")
        )
        self.drill_button.setStyleSheet("""
                                        QPushButton
                                        {
                                            font-weight: bold;
                                        }
                                        """)
        grid_lay.addWidget(self.drill_button, 20, 0, 1, 2)

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
