# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 5/17/2020                                         #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtCore

from AppTool import AppTool
from AppGUI.GUIElements import FCDoubleSpinner, FCCheckBox, FCComboBox, FCButton

from shapely.geometry import MultiPolygon, LineString

from copy import deepcopy
import logging

import gettext
import AppTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class ToolCorners(AppTool):

    toolName = _("Corner Markers Tool")

    def __init__(self, app):
        AppTool.__init__(self, app)

        self.app = app
        self.canvas = self.app.plotcanvas

        self.decimals = self.app.decimals
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

        # Gerber object #
        self.object_label = QtWidgets.QLabel('<b>%s:</b>' % _("GERBER"))
        self.object_label.setToolTip(
            _("The Gerber object that to which will be added corner markers.")
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

        self.points_label = QtWidgets.QLabel('<b>%s:</b>' % _('Locations'))
        self.points_label.setToolTip(
            _("Locations where to place corner markers.")
        )
        self.layout.addWidget(self.points_label)

        # BOTTOM LEFT
        self.bl_cb = FCCheckBox(_("Bottom Left"))
        self.layout.addWidget(self.bl_cb)

        # BOTTOM RIGHT
        self.br_cb = FCCheckBox(_("Bottom Right"))
        self.layout.addWidget(self.br_cb)

        # TOP LEFT
        self.tl_cb = FCCheckBox(_("Top Left"))
        self.layout.addWidget(self.tl_cb)

        # TOP RIGHT
        self.tr_cb = FCCheckBox(_("Top Right"))
        self.layout.addWidget(self.tr_cb)

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

        self.param_label = QtWidgets.QLabel('<b>%s:</b>' % _('Parameters'))
        self.param_label.setToolTip(
            _("Parameters used for this tool.")
        )
        grid_lay.addWidget(self.param_label, 0, 0, 1, 2)

        # Thickness #
        self.thick_label = QtWidgets.QLabel('%s:' % _("Thickness"))
        self.thick_label.setToolTip(
            _("The thickness of the line that makes the corner marker.")
        )
        self.thick_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.thick_entry.set_range(0.0000, 9.9999)
        self.thick_entry.set_precision(self.decimals)
        self.thick_entry.setWrapping(True)
        self.thick_entry.setSingleStep(10 ** -self.decimals)

        grid_lay.addWidget(self.thick_label, 1, 0)
        grid_lay.addWidget(self.thick_entry, 1, 1)

        # Length #
        self.l_label = QtWidgets.QLabel('%s:' % _("Length"))
        self.l_label.setToolTip(
            _("The length of the line that makes the corner marker.")
        )
        self.l_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.l_entry.set_range(-9999.9999, 9999.9999)
        self.l_entry.set_precision(self.decimals)
        self.l_entry.setSingleStep(10 ** -self.decimals)

        grid_lay.addWidget(self.l_label, 2, 0)
        grid_lay.addWidget(self.l_entry, 2, 1)

        # Margin #
        self.margin_label = QtWidgets.QLabel('%s:' % _("Margin"))
        self.margin_label.setToolTip(
            _("Bounding box margin.")
        )
        self.margin_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.margin_entry.set_range(-9999.9999, 9999.9999)
        self.margin_entry.set_precision(self.decimals)
        self.margin_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.margin_label, 3, 0)
        grid_lay.addWidget(self.margin_entry, 3, 1)

        separator_line_2 = QtWidgets.QFrame()
        separator_line_2.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line_2.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line_2, 4, 0, 1, 2)

        # ## Insert Corner Marker
        self.add_marker_button = FCButton(_("Add Marker"))
        self.add_marker_button.setToolTip(
            _("Will add corner markers to the selected Gerber file.")
        )
        self.add_marker_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)
        grid_lay.addWidget(self.add_marker_button, 11, 0, 1, 2)

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

        # Objects involved in Copper thieving
        self.grb_object = None

        # store the flattened geometry here:
        self.flat_geometry = []

        # Tool properties
        self.fid_dia = None

        self.grb_steps_per_circle = self.app.defaults["gerber_circle_steps"]

        # SIGNALS
        self.add_marker_button.clicked.connect(self.add_markers)
        self.toggle_all_cb.toggled.connect(self.on_toggle_all)

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
        self.thick_entry.set_value(self.app.defaults["tools_corners_thickness"])
        self.l_entry.set_value(float(self.app.defaults["tools_corners_length"]))
        self.margin_entry.set_value(float(self.app.defaults["tools_corners_margin"]))
        self.toggle_all_cb.set_value(False)

    def on_toggle_all(self, val):
        self.bl_cb.set_value(val)
        self.br_cb.set_value(val)
        self.tl_cb.set_value(val)
        self.tr_cb.set_value(val)

    def add_markers(self):
        self.app.call_source = "corners_tool"
        tl_state = self.tl_cb.get_value()
        tr_state = self.tr_cb.get_value()
        bl_state = self.bl_cb.get_value()
        br_state = self.br_cb.get_value()

        # get the Gerber object on which the corner marker will be inserted
        selection_index = self.object_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.object_combo.rootModelIndex())

        try:
            self.grb_object = model_index.internalPointer().obj
        except Exception as e:
            log.debug("ToolCorners.add_markers() --> %s" % str(e))
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Gerber object loaded ..."))
            return

        xmin, ymin, xmax, ymax = self.grb_object.bounds()
        points = {}
        if tl_state:
            points['tl'] = (xmin, ymax)
        if tr_state:
            points['tr'] = (xmax, ymax)
        if bl_state:
            points['bl'] = (xmin, ymin)
        if br_state:
            points['br'] = (xmax, ymin)

        self.add_corners_geo(points, g_obj=self.grb_object)

        self.grb_object.source_file = self.app.export_gerber(obj_name=self.grb_object.options['name'],
                                                             filename=None,
                                                             local_use=self.grb_object, use_thread=False)
        self.on_exit()

    def add_corners_geo(self, points_storage, g_obj):
        """
        Add geometry to the solid_geometry of the copper Gerber object

        :param points_storage:  a dictionary holding the points where to add corners
        :param g_obj:           the Gerber object where to add the geometry
        :return:                None
        """

        line_thickness = self.thick_entry.get_value()
        line_length = self.l_entry.get_value()
        margin = self.margin_entry.get_value()

        geo_list = []

        if not points_storage:
            self.app.inform.emit("[ERROR_NOTCL] %s." % _("Please select at least a location"))
            return

        for key in points_storage:
            if key == 'tl':
                pt = points_storage[key]
                x = pt[0] - margin - line_thickness / 2.0
                y = pt[1] + margin + line_thickness / 2.0
                line_geo_hor = LineString([
                    (x, y), (x + line_length, y)
                ])
                line_geo_vert = LineString([
                    (x, y), (x, y - line_length)
                ])
                geo_list.append(line_geo_hor)
                geo_list.append(line_geo_vert)
            if key == 'tr':
                pt = points_storage[key]
                x = pt[0] + margin + line_thickness / 2.0
                y = pt[1] + margin + line_thickness / 2.0
                line_geo_hor = LineString([
                    (x, y), (x - line_length, y)
                ])
                line_geo_vert = LineString([
                    (x, y), (x, y - line_length)
                ])
                geo_list.append(line_geo_hor)
                geo_list.append(line_geo_vert)
            if key == 'bl':
                pt = points_storage[key]
                x = pt[0] - margin - line_thickness / 2.0
                y = pt[1] - margin - line_thickness / 2.0
                line_geo_hor = LineString([
                    (x, y), (x + line_length, y)
                ])
                line_geo_vert = LineString([
                    (x, y), (x, y + line_length)
                ])
                geo_list.append(line_geo_hor)
                geo_list.append(line_geo_vert)
            if key == 'br':
                pt = points_storage[key]
                x = pt[0] + margin + line_thickness / 2.0
                y = pt[1] - margin - line_thickness / 2.0
                line_geo_hor = LineString([
                    (x, y), (x - line_length, y)
                ])
                line_geo_vert = LineString([
                    (x, y), (x, y + line_length)
                ])
                geo_list.append(line_geo_hor)
                geo_list.append(line_geo_vert)

        aperture_found = None
        for ap_id, ap_val in g_obj.apertures.items():
            if ap_val['type'] == 'C' and ap_val['size'] == line_thickness:
                aperture_found = ap_id
                break

        geo_buff_list = []
        if aperture_found:
            for geo in geo_list:
                geo_buff = geo.buffer(line_thickness / 2.0, resolution=self.grb_steps_per_circle, join_style=2)
                geo_buff_list.append(geo_buff)

                dict_el = {}
                dict_el['follow'] = geo
                dict_el['solid'] = geo_buff
                g_obj.apertures[aperture_found]['geometry'].append(deepcopy(dict_el))
        else:
            ap_keys = list(g_obj.apertures.keys())
            if ap_keys:
                new_apid = str(int(max(ap_keys)) + 1)
            else:
                new_apid = '10'

            g_obj.apertures[new_apid] = {}
            g_obj.apertures[new_apid]['type'] = 'C'
            g_obj.apertures[new_apid]['size'] = line_thickness
            g_obj.apertures[new_apid]['geometry'] = []

            for geo in geo_list:
                geo_buff = geo.buffer(line_thickness / 2.0, resolution=self.grb_steps_per_circle, join_style=3)
                geo_buff_list.append(geo_buff)

                dict_el = {}
                dict_el['follow'] = geo
                dict_el['solid'] = geo_buff
                g_obj.apertures[new_apid]['geometry'].append(deepcopy(dict_el))

        s_list = []
        if g_obj.solid_geometry:
            try:
                for poly in g_obj.solid_geometry:
                    s_list.append(poly)
            except TypeError:
                s_list.append(g_obj.solid_geometry)

        geo_buff_list = MultiPolygon(geo_buff_list)
        geo_buff_list = geo_buff_list.buffer(0)
        for poly in geo_buff_list:
            s_list.append(poly)
        g_obj.solid_geometry = MultiPolygon(s_list)

    def replot(self, obj, run_thread=True):
        def worker_task():
            with self.app.proc_container.new('%s...' % _("Plotting")):
                obj.plot()

        if run_thread:
            self.app.worker_task.emit({'fcn': worker_task, 'params': []})
        else:
            worker_task()

    def on_exit(self):
        # plot the object
        try:
            self.replot(obj=self.grb_object)
        except (AttributeError, TypeError):
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

        # reset the variables
        self.grb_object = None

        self.app.call_source = "app"
        self.app.inform.emit('[success] %s' % _("Corners Tool exit."))
