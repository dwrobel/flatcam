# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 11/21/2019                                         #
# MIT Licence                                              #
# ##########################################################

from appTool import *
import shapely.geometry
from appCommon.Common import LoudDict

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class ToolFiducials(AppTool):

    def __init__(self, app):
        AppTool.__init__(self, app)

        self.app = app
        self.canvas = self.app.plotcanvas

        self.cursor_color_memory = None
        # store the current cursor type to be restored after manual geo
        self.old_cursor_type = self.app.options["global_cursor_type"]

        self.decimals = self.app.decimals
        self.units = ''

        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = FidoUI(layout=self.layout, app=self.app)
        self.pluginName = self.ui.pluginName

        # Objects involved in Copper thieving
        self.grb_object = None
        self.sm_object = None

        self.copper_obj_set = set()
        self.sm_obj_set = set()

        # store the flattened geometry here:
        self.flat_geometry = []

        # Events ID
        self.mr = None
        self.mm = None

        # Mouse cursor positions
        self.cursor_pos = (0, 0)
        self.first_click = False

        self.mode_method = False

        # Tool properties
        self.fid_dia = None
        self.sm_opening_dia = None

        self.margin_val = None
        self.sec_position = None

        self.grb_steps_per_circle = self.app.options["gerber_circle_steps"]

        self.click_points = []

        self.handlers_connected = False
        # storage for temporary shapes when adding manual markers
        self.temp_shapes = self.app.move_tool.sel_shapes

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolFiducials()")

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

        self.app.ui.notebook.setTabText(2, _("Fiducials"))

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Alt+F', **kwargs)

    def connect_signals_at_init(self):
        # #############################################################################
        # ############################ SIGNALS ########################################
        # #############################################################################
        self.ui.level.toggled.connect(self.on_level_changed)
        self.ui.add_cfid_button.clicked.connect(self.add_fiducials)
        self.ui.add_sm_opening_button.clicked.connect(self.add_soldermask_opening)

        self.ui.fid_type_combo.currentIndexChanged.connect(self.on_fiducial_type)
        self.ui.pos_radio.activated_custom.connect(self.on_second_point)
        self.ui.mode_radio.activated_custom.connect(self.on_method_change)

        self.ui.big_cursor_cb.stateChanged.connect(self.on_cursor_change)

        self.ui.reset_button.clicked.connect(self.set_tool_ui)

    def set_tool_ui(self):
        self.units = self.app.app_units

        self.clear_ui(self.layout)
        self.ui = FidoUI(layout=self.layout, app=self.app)
        self.pluginName = self.ui.pluginName
        self.connect_signals_at_init()

        self.ui.fid_size_entry.set_value(self.app.options["tools_fiducials_dia"])
        self.ui.margin_entry.set_value(float(self.app.options["tools_fiducials_margin"]))
        self.ui.mode_radio.set_value(self.app.options["tools_fiducials_mode"])
        self.ui.pos_radio.set_value(self.app.options["tools_fiducials_second_pos"])
        self.ui.fid_type_combo.set_value(self.app.options["tools_fiducials_type"])
        # needed so the visibility of some objects will be updated
        self.on_fiducial_type(val=self.ui.fid_type_combo.get_value())
        self.ui.line_thickness_entry.set_value(float(self.app.options["tools_fiducials_line_thickness"]))

        self.click_points = []
        self.ui.bottom_left_coords_entry.set_value('')
        self.ui.top_right_coords_entry.set_value('')
        self.ui.sec_points_coords_entry.set_value('')

        self.copper_obj_set = set()
        self.sm_obj_set = set()

        # Show/Hide Advanced Options
        app_mode = self.app.options["global_app_level"]
        self.change_level(app_mode)

        # SELECT THE CURRENT OBJECT
        obj = self.app.collection.get_active()
        if obj and obj.kind == 'gerber':
            obj_name = obj.obj_options['name']
            self.ui.grb_object_combo.set_value(obj_name)

        if obj is None:
            self.ui.grb_object_combo.setCurrentIndex(0)

        self.ui.big_cursor_cb.set_value(self.app.options["tools_fiducials_big_cursor"])

        # set cursor
        self.old_cursor_type = self.app.options["global_cursor_type"]

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

            self.ui.separator_line.hide()
            self.ui.fid_type_label.hide()
            self.ui.fid_type_combo.hide()
            self.ui.line_thickness_label.hide()
            self.ui.line_thickness_entry.hide()

        else:
            self.ui.level.setText('%s' % _('Advanced'))
            self.ui.level.setStyleSheet("""
                                        QToolButton
                                        {
                                            color: red;
                                        }
                                        """)

            self.ui.separator_line.show()
            self.ui.fid_type_label.show()
            self.ui.fid_type_combo.show()
            self.ui.line_thickness_label.show()
            self.ui.line_thickness_entry.show()

    def on_second_point(self, val):
        if val == 'no':
            self.ui.id_item_3.setFlags(QtCore.Qt.ItemFlag.NoItemFlags)
            self.ui.sec_point_coords_lbl.setFlags(QtCore.Qt.ItemFlag.NoItemFlags)
            self.ui.sec_points_coords_entry.setDisabled(True)
        else:
            self.ui.id_item_3.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
            self.ui.sec_point_coords_lbl.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
            self.ui.sec_points_coords_entry.setDisabled(False)

    def on_method_change(self, val):
        """
        Make sure that on method change we disconnect the event handlers and reset the points storage

        :param val:     value of the Radio button which trigger this method
        :return:        None
        """
        self.click_points = []

        if val == 'auto':
            try:
                self.disconnect_event_handlers()
            except TypeError:
                pass

            self.ui.big_cursor_cb.hide()
        else:
            self.ui.big_cursor_cb.show()

    def on_cursor_change(self, val):
        if val:
            self.app.options['tools_fiducials_big_cursor'] = True
        else:
            self.app.options['tools_fiducials_big_cursor'] = False

    def on_fiducial_type(self, val):
        if val == 2:    # 'cross'
            self.ui.line_thickness_label.setDisabled(False)
            self.ui.line_thickness_entry.setDisabled(False)
        else:
            self.ui.line_thickness_label.setDisabled(True)
            self.ui.line_thickness_entry.setDisabled(True)

    def add_fiducials(self):
        self.app.call_source = "fiducials_tool"
        self.app.ui.notebook.setDisabled(True)

        self.mode_method = self.ui.mode_radio.get_value()
        self.margin_val = self.ui.margin_entry.get_value()
        self.sec_position = self.ui.pos_radio.get_value()
        fid_type = self.ui.fid_type_combo.get_value()

        self.click_points = []

        # get the Gerber object on which the Fiducial will be inserted
        selection_index = self.ui.grb_object_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.ui.grb_object_combo.rootModelIndex())

        try:
            self.grb_object = model_index.internalPointer().obj
        except Exception as e:
            self.app.log.error("ToolFiducials.execute() --> %s" % str(e))
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Gerber object loaded ..."))
            self.app.ui.notebook.setDisabled(False)
            self.app.call_source = "app"
            return

        self.copper_obj_set.add(self.grb_object.obj_options['name'])

        if self.mode_method == 'auto':
            xmin, ymin, xmax, ymax = self.grb_object.bounds()
            bbox = box(xmin, ymin, xmax, ymax)
            buf_bbox = bbox.buffer(self.margin_val, self.grb_steps_per_circle, join_style=2)
            x0, y0, x1, y1 = buf_bbox.bounds

            self.click_points.append(
                (
                    float('%.*f' % (self.decimals, x0)),
                    float('%.*f' % (self.decimals, y0))
                )
            )
            self.ui.bottom_left_coords_entry.set_value('(%.*f, %.*f)' % (self.decimals, x0, self.decimals, y0))

            self.click_points.append(
                (
                    float('%.*f' % (self.decimals, x1)),
                    float('%.*f' % (self.decimals, y1))
                )
            )
            self.ui.top_right_coords_entry.set_value('(%.*f, %.*f)' % (self.decimals, x1, self.decimals, y1))

            if self.sec_position == 'up':
                self.click_points.append(
                    (
                        float('%.*f' % (self.decimals, x0)),
                        float('%.*f' % (self.decimals, y1))
                    )
                )
                self.ui.sec_points_coords_entry.set_value('(%.*f, %.*f)' % (self.decimals, x0, self.decimals, y1))
            elif self.sec_position == 'down':
                self.click_points.append(
                    (
                        float('%.*f' % (self.decimals, x1)),
                        float('%.*f' % (self.decimals, y0))
                    )
                )
                self.ui.sec_points_coords_entry.set_value('(%.*f, %.*f)' % (self.decimals, x1, self.decimals, y0))

            ret_val = self.add_fiducials_geo(self.click_points, g_obj=self.grb_object, fid_type=fid_type)
            self.app.call_source = "app"
            if ret_val == 'fail':
                self.app.call_source = "app"
                self.app.ui.notebook.setDisabled(False)
                self.disconnect_event_handlers()
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed."))
                return

            self.on_exit()
        else:
            self.app.inform.emit(_("Click to add first Fiducial. Bottom Left..."))
            self.ui.bottom_left_coords_entry.set_value('')
            self.ui.top_right_coords_entry.set_value('')
            self.ui.sec_points_coords_entry.set_value('')

            if self.ui.big_cursor_cb.get_value():
                self.app.on_cursor_type(val="big", control_cursor=True)
                self.cursor_color_memory = self.app.plotcanvas.cursor_color
                if self.app.use_3d_engine is True:
                    self.app.plotcanvas.cursor_color = '#000000FF'
                else:
                    self.app.plotcanvas.cursor_color = '#000000'
                self.app.app_cursor.enabled = True
            else:
                self.app.on_cursor_type(val="small", control_cursor=True)
                self.app.plotcanvas.cursor_color = self.cursor_color_memory

            self.connect_event_handlers()

        # To be called after clicking on the plot.

    def add_fiducials_geo(self, points_list, g_obj, fid_size=None, fid_type=None, line_size=None):
        """
        Add geometry to the solid_geometry of the copper Gerber object

        :param points_list:     list of coordinates for the fiducials
        :param g_obj:           the Gerber object where to add the geometry
        :param fid_size:        the overall size of the fiducial or fiducial opening depending on the g_obj type
        :param fid_type:        the type of fiducial: circular, cross, chess
        :param line_size:       the line thickenss when the fiducial type is cross
        :return:
        """
        fid_size = self.ui.fid_size_entry.get_value() if fid_size is None else fid_size
        fid_type = 0 if fid_type is None else fid_type  # default is 'circular' <=> 0
        line_thickness = self.ui.line_thickness_entry.get_value() if line_size is None else line_size

        radius = fid_size / 2.0

        new_apertures = deepcopy(g_obj.tools)

        if fid_type == 0:   # 'circular'
            geo_list = [Point(pt).buffer(radius, self.grb_steps_per_circle) for pt in points_list]

            aperture_found = None
            for ap_id, ap_val in g_obj.tools.items():
                if ap_val['type'] == 'C' and ap_val['size'] == fid_size:
                    aperture_found = ap_id
                    break

            if aperture_found:
                for geo in geo_list:
                    dict_el = {'follow': geo.centroid, 'solid': geo}
                    new_apertures[aperture_found]['geometry'].append(deepcopy(dict_el))
            else:
                ap_keys = list(g_obj.tools.keys())
                if ap_keys:
                    new_apid = int(max(ap_keys)) + 1
                else:
                    new_apid = 10

                new_apertures[new_apid] = {
                    'type': 'C',
                    'size': fid_size,
                    'geometry': []
                }

                for geo in geo_list:
                    dict_el = {'follow': geo.centroid, 'solid': geo}
                    new_apertures[new_apid]['geometry'].append(deepcopy(dict_el))

            s_list = []
            if g_obj.solid_geometry:
                try:
                    for poly in g_obj.solid_geometry:
                        s_list.append(poly)
                except TypeError:
                    s_list.append(g_obj.solid_geometry)

            s_list += geo_list
        elif fid_type == 1:  # 'cross'
            geo_list = []

            for pt in points_list:
                x = pt[0]
                y = pt[1]
                line_geo_hor = LineString([
                    (x - radius + (line_thickness / 2.0), y), (x + radius - (line_thickness / 2.0), y)
                ])
                line_geo_vert = LineString([
                    (x, y - radius + (line_thickness / 2.0)), (x, y + radius - (line_thickness / 2.0))
                ])
                geo_list.append([line_geo_hor, line_geo_vert])

            aperture_found = None
            for ap_id, ap_val in g_obj.tools.items():
                if ap_val['type'] == 'C' and ap_val['size'] == line_thickness:
                    aperture_found = ap_id
                    break

            geo_buff_list = []
            if aperture_found:
                for geo in geo_list:
                    geo_buff_h = geo[0].buffer(line_thickness / 2.0, self.grb_steps_per_circle)
                    geo_buff_v = geo[1].buffer(line_thickness / 2.0, self.grb_steps_per_circle)
                    geo_buff_list.append(geo_buff_h)
                    geo_buff_list.append(geo_buff_v)

                    dict_el = {'follow': geo_buff_h.centroid, 'solid': geo_buff_h}
                    new_apertures[aperture_found]['geometry'].append(deepcopy(dict_el))
                    dict_el = {'follow': geo_buff_v.centroid, 'solid': geo_buff_v}
                    new_apertures[aperture_found]['geometry'].append(deepcopy(dict_el))
            else:
                ap_keys = list(g_obj.tools.keys())
                if ap_keys:
                    new_apid = int(max(ap_keys)) + 1
                else:
                    new_apid = 10

                new_apertures[new_apid] = {
                    'type': 'C',
                    'size': line_thickness,
                    'geometry': []
                }

                for geo in geo_list:
                    geo_buff_h = geo[0].buffer(line_thickness / 2.0, self.grb_steps_per_circle)
                    geo_buff_v = geo[1].buffer(line_thickness / 2.0, self.grb_steps_per_circle)
                    geo_buff_list.append(geo_buff_h)
                    geo_buff_list.append(geo_buff_v)

                    dict_el = {'follow': geo_buff_h.centroid, 'solid': geo_buff_h}
                    new_apertures[new_apid]['geometry'].append(deepcopy(dict_el))
                    dict_el = {'follow': geo_buff_v.centroid, 'solid': geo_buff_v}
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
            for poly in geo_buff_list:
                s_list.append(poly)
        else:
            # value 3 meaning 'chess' pattern fiducial type
            geo_list = []

            def make_square_poly(center_pt, side_size):
                """

                :param center_pt:
                :param side_size:
                :return:            Polygon
                """
                half_s = side_size / 2
                x_center = center_pt[0]
                y_center = center_pt[1]

                pt1 = (x_center - half_s, y_center - half_s)
                pt2 = (x_center + half_s, y_center - half_s)
                pt3 = (x_center + half_s, y_center + half_s)
                pt4 = (x_center - half_s, y_center + half_s)

                return Polygon([pt1, pt2, pt3, pt4, pt1])

            for pt in points_list:
                x = pt[0]
                y = pt[1]
                first_square = make_square_poly(center_pt=(x-fid_size/4, y+fid_size/4), side_size=fid_size/2)
                second_square = make_square_poly(center_pt=(x+fid_size/4, y-fid_size/4), side_size=fid_size/2)
                geo_list += [first_square, second_square]

            aperture_found = None
            new_ap_size = math.sqrt(fid_size**2 + fid_size**2)
            for ap_id, ap_val in g_obj.tools.items():
                if ap_val['type'] == 'R' and \
                        round(ap_val['size'], ndigits=self.decimals) == round(new_ap_size, ndigits=self.decimals):
                    aperture_found = ap_id
                    break

            geo_buff_list = []
            if aperture_found:
                for geo in geo_list:
                    assert isinstance(geo, shapely.geometry.base.BaseGeometry)
                    geo_buff_list.append(geo)

                    dict_el = {'follow': geo.centroid, 'solid': geo}
                    new_apertures[aperture_found]['geometry'].append(deepcopy(dict_el))
            else:
                ap_keys = list(g_obj.tools.keys())
                if ap_keys:
                    new_apid = int(max(ap_keys)) + 1
                else:
                    new_apid = 10

                new_apertures[new_apid] = {
                    'type': 'R',
                    'size': new_ap_size,
                    'width': fid_size,
                    'height': fid_size,
                    'geometry': []
                }

                for geo in geo_list:
                    assert isinstance(geo, shapely.geometry.base.BaseGeometry)
                    geo_buff_list.append(geo)

                    dict_el = {'follow': geo.centroid, 'solid': geo}
                    new_apertures[new_apid]['geometry'].append(deepcopy(dict_el))

            s_list = []
            if g_obj.solid_geometry:
                try:
                    for poly in g_obj.solid_geometry:
                        s_list.append(poly)
                except TypeError:
                    s_list.append(g_obj.solid_geometry)

            for poly in geo_buff_list:
                s_list.append(poly)

        outname = '%s_%s' % (str(g_obj.obj_options['name']), 'fid')

        def initialize(grb_obj, app_obj):
            grb_obj.obj_options = LoudDict()
            for opt in g_obj.obj_options:
                if opt != 'name':
                    grb_obj.obj_options[opt] = deepcopy(g_obj.obj_options[opt])
            grb_obj.obj_options['name'] = outname
            grb_obj.multitool = False
            grb_obj.multigeo = False
            grb_obj.follow = deepcopy(g_obj.follow)
            grb_obj.tools = new_apertures
            grb_obj.solid_geometry = unary_union(s_list)
            grb_obj.follow_geometry = deepcopy(g_obj.follow_geometry) + geo_list

            grb_obj.source_file = app_obj.f_handlers.export_gerber(obj_name=outname, filename=None, local_use=grb_obj,
                                                                   use_thread=False)

        ret = self.app.app_obj.new_object('gerber', outname, initialize, plot=True)

        return ret

    def add_soldermask_opening(self):
        sm_opening_dia = self.ui.fid_size_entry.get_value() * 2.0

        # get the Gerber object on which the Fiducial will be inserted
        selection_index = self.ui.grb_object_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.ui.grb_object_combo.rootModelIndex())

        try:
            self.sm_object = model_index.internalPointer().obj
        except Exception as e:
            self.app.log.error("ToolFiducials.add_soldermask_opening() --> %s" % str(e))
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Gerber object loaded ..."))
            return

        self.sm_obj_set.add(self.sm_object.obj_options['name'])
        ret_val = self.add_fiducials_geo(
            self.click_points, g_obj=self.sm_object, fid_size=sm_opening_dia, fid_type='circular')
        self.app.call_source = "app"
        if ret_val == 'fail':
            self.app.call_source = "app"
            self.app.ui.notebook.setDisabled(False)
            self.disconnect_event_handlers()
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed."))
            return

        self.on_exit()

    def on_mouse_release(self, event):
        if self.app.use_3d_engine:
            event_pos = event.pos
            right_button = 2
            self.app.event_is_dragging = self.app.event_is_dragging
        else:
            event_pos = (event.xdata, event.ydata)
            right_button = 3
            self.app.event_is_dragging = self.app.ui.popMenu.mouse_is_panning

        if event.button == 1:
            pos_canvas = self.canvas.translate_coords(event_pos)
            if self.app.grid_status():
                pos = self.app.geo_editor.snap(pos_canvas[0], pos_canvas[1])
            else:
                pos = (pos_canvas[0], pos_canvas[1])
            click_pt = Point([pos[0], pos[1]])

            self.click_points.append(
                (
                    float('%.*f' % (self.decimals, click_pt.x)),
                    float('%.*f' % (self.decimals, click_pt.y))
                )
            )
            self.check_points()
            self.draw_utility_geometry(pos=pos)
        elif event.button == right_button and self.app.event_is_dragging is False:
            self.on_exit(cancelled=True)

    def check_points(self):
        fid_type = self.ui.fid_type_combo.get_value()

        if len(self.click_points) == 1:
            self.ui.bottom_left_coords_entry.set_value(self.click_points[0])
            self.app.inform.emit(_("Click to add the last fiducial. Top Right..."))

        if self.sec_position != 'no':
            if len(self.click_points) == 2:
                self.ui.top_right_coords_entry.set_value(self.click_points[1])
                self.app.inform.emit(_("Click to add the second fiducial. Top Left or Bottom Right..."))
            elif len(self.click_points) == 3:
                self.ui.sec_points_coords_entry.set_value(self.click_points[2])
                self.app.inform.emit('[success] %s' % _("Done."))

                ret_val = self.add_fiducials_geo(self.click_points, g_obj=self.grb_object, fid_type=fid_type)
                self.app.call_source = "app"

                if ret_val == 'fail':
                    self.app.call_source = "app"
                    self.app.ui.notebook.setDisabled(False)
                    self.disconnect_event_handlers()
                    self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed."))
                    return
                self.on_exit()
        else:
            if len(self.click_points) == 2:
                self.ui.top_right_coords_entry.set_value(self.click_points[1])
                self.app.inform.emit('[success] %s' % _("Done."))

                ret_val = self.add_fiducials_geo(self.click_points, g_obj=self.grb_object, fid_type=fid_type)
                self.app.call_source = "app"

                if ret_val == 'fail':
                    self.app.call_source = "app"
                    self.app.ui.notebook.setDisabled(False)
                    self.disconnect_event_handlers()
                    self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed."))
                    return
                self.on_exit()

    def on_mouse_move(self, event):
        pass

    def replot(self, obj, run_thread=True):
        def worker_task():
            with self.app.proc_container.new('%s ...' % _("Plotting")):
                obj.plot()
                self.app.app_obj.object_plotted.emit(obj)

        if run_thread:
            self.app.worker_task.emit({'fcn': worker_task, 'params': []})
        else:
            worker_task()

    def connect_event_handlers(self):
        if self.handlers_connected is False:
            if self.app.use_3d_engine:
                self.app.plotcanvas.graph_event_disconnect('mouse_press', self.app.on_mouse_click_over_plot)
                self.app.plotcanvas.graph_event_disconnect('mouse_release', self.app.on_mouse_click_release_over_plot)
            else:
                self.app.plotcanvas.graph_event_disconnect(self.app.mp)
                self.app.plotcanvas.graph_event_disconnect(self.app.mr)

            self.mr = self.app.plotcanvas.graph_event_connect('mouse_release', self.on_mouse_release)

            self.handlers_connected = True

    def disconnect_event_handlers(self):
        if self.handlers_connected is True:
            if self.app.use_3d_engine:
                self.app.plotcanvas.graph_event_disconnect('mouse_release', self.on_mouse_release)
            else:
                self.app.plotcanvas.graph_event_disconnect(self.mr)

            self.app.mp = self.app.plotcanvas.graph_event_connect('mouse_press',
                                                                  self.app.on_mouse_click_over_plot)

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

    def on_exit(self, cancelled=None):
        # restore cursor
        self.app.on_cursor_type(val=self.old_cursor_type, control_cursor=False)
        self.app.plotcanvas.cursor_color = self.cursor_color_memory

        self.clear_utility_geometry()

        # plot the object
        for ob_name in self.copper_obj_set:
            try:
                copper_obj = self.app.collection.get_by_name(name=ob_name)
                if len(self.copper_obj_set) > 1:
                    self.replot(obj=copper_obj, run_thread=False)
                else:
                    self.replot(obj=copper_obj)
            except (AttributeError, TypeError):
                continue

            # update the bounding box values
            try:
                a, b, c, d = copper_obj.bounds()
                copper_obj.obj_options['xmin'] = a
                copper_obj.obj_options['ymin'] = b
                copper_obj.obj_options['xmax'] = c
                copper_obj.obj_options['ymax'] = d
            except Exception as e:
                self.app.log.error("ToolFiducials.on_exit() copper_obj bounds error --> %s" % str(e))

        for ob_name in self.sm_obj_set:
            try:
                sm_obj = self.app.collection.get_by_name(name=ob_name)
                if len(self.sm_obj_set) > 1:
                    self.replot(obj=sm_obj, run_thread=False)
                else:
                    self.replot(obj=sm_obj)
            except (AttributeError, TypeError):
                continue

            # update the bounding box values
            try:
                a, b, c, d = sm_obj.bounds()
                sm_obj.obj_options['xmin'] = a
                sm_obj.obj_options['ymin'] = b
                sm_obj.obj_options['xmax'] = c
                sm_obj.obj_options['ymax'] = d
            except Exception as e:
                self.app.log.error("ToolFiducials.on_exit() sm_obj bounds error --> %s" % str(e))

        # Events ID
        self.mr = None
        # self.mm = None

        # Mouse cursor positions
        self.cursor_pos = (0, 0)
        self.first_click = False

        self.disconnect_event_handlers()

        self.app.call_source = "app"
        self.app.ui.notebook.setDisabled(False)

        if cancelled is True:
            self.app.delete_selection_shape()
            self.disconnect_event_handlers()
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled by user request."))
            return

        self.app.inform.emit('[success] %s' % _("Fiducials Tool exit."))

    def draw_utility_geometry(self, pos):
        fid_type = self.ui.fid_type_combo.get_value()
        line_thickness = self.ui.line_thickness_entry.get_value()
        fid_size = self.ui.fid_size_entry.get_value()
        radius = fid_size / 2.0

        geo_list = []
        pt = pos[0], pos[1]     # we ensure that this works in case the pt tuple is a return from Vispy (4 members)

        if fid_type == 0:  # 'circular'
            geo_list = [Point(pt).buffer(radius, self.grb_steps_per_circle)]
        elif fid_type == 1:      # 'cross'
            x = pt[0]
            y = pt[1]
            line_geo_hor = LineString([
                (x - radius + (line_thickness / 2.0), y), (x + radius - (line_thickness / 2.0), y)
            ])
            line_geo_vert = LineString([
                (x, y - radius + (line_thickness / 2.0)), (x, y + radius - (line_thickness / 2.0))
            ])
            geo_list = [line_geo_hor, line_geo_vert]
        else:       # 'chess' pattern
            def make_square_poly(center_pt, side_size):
                """

                :param center_pt:
                :param side_size:
                :return:            Polygon
                """
                half_s = side_size / 2
                x_center = center_pt[0]
                y_center = center_pt[1]

                pt1 = (x_center - half_s, y_center - half_s)
                pt2 = (x_center + half_s, y_center - half_s)
                pt3 = (x_center + half_s, y_center + half_s)
                pt4 = (x_center - half_s, y_center + half_s)

                return Polygon([pt1, pt2, pt3, pt4, pt1])

            x = pt[0]
            y = pt[1]
            first_square = make_square_poly(center_pt=(x - fid_size / 4, y + fid_size / 4), side_size=fid_size / 2)
            second_square = make_square_poly(center_pt=(x + fid_size / 4, y - fid_size / 4), side_size=fid_size / 2)
            geo_list += [first_square, second_square]

        outline = '#0000FFAF'
        for util_geo in geo_list:
            self.temp_shapes.add(util_geo, color=outline, update=True, layer=0, tolerance=None)

        if self.app.use_3d_engine:
            self.temp_shapes.redraw()

    def clear_utility_geometry(self):
        self.temp_shapes.clear(update=True)
        self.temp_shapes.redraw()

    def on_plugin_cleanup(self):
        self.on_exit()


class FidoUI:

    pluginName = _("Fiducials")

    def __init__(self, layout, app):
        self.app = app
        self.decimals = self.app.decimals
        self.layout = layout

        self.title_box = QtWidgets.QHBoxLayout()
        self.layout.addLayout(self.title_box)
        
        # ## Title
        title_label = FCLabel("%s" % self.pluginName)
        title_label.setStyleSheet("""
                                QLabel
                                {
                                    font-size: 16px;
                                    font-weight: bold;
                                }
                                """)
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
        self.level.setCheckable(True)
        self.title_box.addWidget(self.level)

        self.tools_frame = QtWidgets.QFrame()
        self.tools_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.tools_frame)
        self.tools_box = QtWidgets.QVBoxLayout()
        self.tools_box.setContentsMargins(0, 0, 0, 0)
        self.tools_frame.setLayout(self.tools_box)

        self.title_box = QtWidgets.QHBoxLayout()
        self.tools_box.addLayout(self.title_box)

        # #############################################################################################################
        # Gerber Source Object
        # #############################################################################################################
        self.obj_combo_label = FCLabel('%s' % _("Source Object"), color='darkorange', bold=True)
        self.obj_combo_label.setToolTip(
            _("Gerber object for adding fiducials and soldermask openings.")
        )

        self.grb_object_combo = FCComboBox()
        self.grb_object_combo.setModel(self.app.collection)
        self.grb_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.grb_object_combo.is_last = True
        self.grb_object_combo.obj_type = "Gerber"

        self.tools_box.addWidget(self.obj_combo_label)
        self.tools_box.addWidget(self.grb_object_combo)

        # #############################################################################################################
        # Coordinates Table Frame
        # #############################################################################################################
        self.points_label = FCLabel('%s' % _("Coordinates"), color='green', bold=True)
        self.points_label.setToolTip(
            _("A table with the fiducial points coordinates,\n"
              "in the format (x, y).")
        )
        self.tools_box.addWidget(self.points_label)

        self.points_table = FCTable()
        self.points_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tools_box.addWidget(self.points_table)

        self.points_table.setColumnCount(3)
        self.points_table.setHorizontalHeaderLabels(
            [
                '#',
                _("Name"),
                _("Coordinates"),
            ]
        )
        self.points_table.setRowCount(3)
        row = 0
        flags = QtCore.Qt.ItemFlag.ItemIsEnabled

        # BOTTOM LEFT
        id_item_1 = QtWidgets.QTableWidgetItem('%d' % 1)
        id_item_1.setFlags(flags)
        self.points_table.setItem(row, 0, id_item_1)  # Tool name/id

        self.bottom_left_coords_lbl = QtWidgets.QTableWidgetItem('%s' % _('Bottom Left'))
        self.bottom_left_coords_lbl.setFlags(flags)
        self.points_table.setItem(row, 1, self.bottom_left_coords_lbl)
        self.bottom_left_coords_entry = EvalEntry()
        self.points_table.setCellWidget(row, 2, self.bottom_left_coords_entry)
        row += 1

        # TOP RIGHT
        id_item_2 = QtWidgets.QTableWidgetItem('%d' % 2)
        id_item_2.setFlags(flags)
        self.points_table.setItem(row, 0, id_item_2)  # Tool name/id

        self.top_right_coords_lbl = QtWidgets.QTableWidgetItem('%s' % _('Top Right'))
        self.top_right_coords_lbl.setFlags(flags)
        self.points_table.setItem(row, 1, self.top_right_coords_lbl)
        self.top_right_coords_entry = EvalEntry()
        self.points_table.setCellWidget(row, 2, self.top_right_coords_entry)
        row += 1

        # Second Point
        self.id_item_3 = QtWidgets.QTableWidgetItem('%d' % 3)
        self.id_item_3.setFlags(flags)
        self.points_table.setItem(row, 0, self.id_item_3)  # Tool name/id

        self.sec_point_coords_lbl = QtWidgets.QTableWidgetItem('%s' % _('Second Point'))
        self.sec_point_coords_lbl.setFlags(flags)
        self.points_table.setItem(row, 1, self.sec_point_coords_lbl)
        self.sec_points_coords_entry = EvalEntry()
        self.points_table.setCellWidget(row, 2, self.sec_points_coords_entry)

        vertical_header = self.points_table.verticalHeader()
        vertical_header.hide()
        self.points_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        horizontal_header = self.points_table.horizontalHeader()
        horizontal_header.setMinimumSectionSize(10)
        horizontal_header.setDefaultSectionSize(70)

        self.points_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        # for x in range(4):
        #     self.points_table.resizeColumnToContents(x)
        self.points_table.resizeColumnsToContents()
        self.points_table.resizeRowsToContents()

        horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Fixed)
        horizontal_header.resizeSection(0, 20)
        horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Fixed)
        horizontal_header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Stretch)

        self.points_table.setMinimumHeight(self.points_table.getHeight() + 2)
        self.points_table.setMaximumHeight(self.points_table.getHeight() + 2)

        # remove the frame on the QLineEdit children of the table
        for row in range(self.points_table.rowCount()):
            wdg = self.points_table.cellWidget(row, 2)
            assert isinstance(wdg, QtWidgets.QLineEdit)
            wdg.setFrame(False)

        # separator_line = QtWidgets.QFrame()
        # separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        # separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        # self.layout.addWidget(separator_line)

        # #############################################################################################################
        # Parameters Frame
        # #############################################################################################################
        self.param_label = FCLabel('%s' % _("Parameters"), color='blue', bold=True)
        self.param_label.setToolTip(
            _("Parameters used for this tool.")
        )
        self.tools_box.addWidget(self.param_label)

        par_frame = FCFrame()
        self.tools_box.addWidget(par_frame)

        param_grid = GLay(v_spacing=5, h_spacing=3)
        par_frame.setLayout(param_grid)

        # DIAMETER #
        self.size_label = FCLabel('%s:' % _("Size"))
        self.size_label.setToolTip(
            _("This set the fiducial diameter if fiducial type is circular,\n"
              "otherwise is the size of the fiducial.\n"
              "The soldermask opening is double than that.")
        )
        self.fid_size_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.fid_size_entry.set_range(1.0000, 3.0000)
        self.fid_size_entry.set_precision(self.decimals)
        self.fid_size_entry.setWrapping(True)
        self.fid_size_entry.setSingleStep(0.1)

        param_grid.addWidget(self.size_label, 2, 0)
        param_grid.addWidget(self.fid_size_entry, 2, 1)

        # MARGIN #
        self.margin_label = FCLabel('%s:' % _("Margin"))
        self.margin_label.setToolTip(
            _("Bounding box margin.")
        )
        self.margin_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.margin_entry.set_range(-10000.0000, 10000.0000)
        self.margin_entry.set_precision(self.decimals)
        self.margin_entry.setSingleStep(0.1)

        param_grid.addWidget(self.margin_label, 4, 0)
        param_grid.addWidget(self.margin_entry, 4, 1)

        # Position for second fiducial #
        self.pos_radio = RadioSet([
            {'label': _('Up'), 'value': 'up'},
            {"label": _("Down"), "value": "down"},
            {"label": _("None"), "value": "no"}
        ], compact=True)
        self.pos_label = FCLabel('%s:' % _("Second fiducial"))
        self.pos_label.setToolTip(
            _("The position for the second fiducial.\n"
              "- 'Up' - the order is: bottom-left, top-left, top-right.\n"
              "- 'Down' - the order is: bottom-left, bottom-right, top-right.\n"
              "- 'None' - there is no second fiducial. The order is: bottom-left, top-right.")
        )
        param_grid.addWidget(self.pos_label, 6, 0)
        param_grid.addWidget(self.pos_radio, 6, 1)

        self.separator_line = QtWidgets.QFrame()
        self.separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        param_grid.addWidget(self.separator_line, 8, 0, 1, 2)

        # Fiducial type #
        self.fid_type_label = FCLabel('%s:' % _("Fiducial Type"))
        self.fid_type_label.setToolTip(
            _("The type of fiducial.\n"
              "- 'Circular' - this is the regular fiducial.\n"
              "- 'Cross' - cross lines fiducial.\n"
              "- 'Chess' - chess pattern fiducial.")
        )

        self.fid_type_combo = FCComboBox2()
        self.fid_type_combo.addItems([_('Circular'), _("Cross"), _("Chess")])

        param_grid.addWidget(self.fid_type_label, 10, 0)
        param_grid.addWidget(self.fid_type_combo, 10, 1)

        # Line Thickness #
        self.line_thickness_label = FCLabel('%s:' % _("Line thickness"))
        self.line_thickness_label.setToolTip(
            _("Thickness of the line that makes the fiducial.")
        )
        self.line_thickness_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.line_thickness_entry.set_range(0.00001, 10000.0000)
        self.line_thickness_entry.set_precision(self.decimals)
        self.line_thickness_entry.setSingleStep(0.1)

        param_grid.addWidget(self.line_thickness_label, 12, 0)
        param_grid.addWidget(self.line_thickness_entry, 12, 1)

        # separator_line_1 = QtWidgets.QFrame()
        # separator_line_1.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        # separator_line_1.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        # param_grid.addWidget(separator_line_1, 14, 0, 1, 2)

        # #############################################################################################################
        # Selection Frame
        # #############################################################################################################
        self.sel_label = FCLabel('%s' % _("Selection"), color='green', bold=True)
        self.tools_box.addWidget(self.sel_label)

        self.s_frame = FCFrame()
        self.tools_box.addWidget(self.s_frame)

        # Grid Layout
        grid_sel = GLay(v_spacing=5, h_spacing=3)
        self.s_frame.setLayout(grid_sel)

        # Mode #
        self.mode_radio = RadioSet([
            {'label': _('Auto'), 'value': 'auto'},
            {"label": _("Manual"), "value": "manual"}
        ], compact=True)
        self.mode_label = FCLabel(_("Mode:"))
        self.mode_label.setToolTip(
            _("- 'Auto' - automatic placement of fiducials in the corners of the bounding box.\n"
              "- 'Manual' - manual placement of fiducials.")
        )
        grid_sel.addWidget(self.mode_label, 0, 0)
        grid_sel.addWidget(self.mode_radio, 0, 1)

        # Big Cursor
        self.big_cursor_cb = FCCheckBox('%s' % _("Big cursor"))
        self.big_cursor_cb.setToolTip(
            _("Use a big cursor."))
        grid_sel.addWidget(self.big_cursor_cb, 2, 0, 1, 2)

        GLay.set_common_column_size([grid_sel, param_grid, param_grid], 0)

        # ## Insert Copper Fiducial
        self.add_cfid_button = FCButton(_("Add Fiducial"))
        self.add_cfid_button.setIcon(QtGui.QIcon(self.app.resource_location + '/fiducials_32.png'))
        self.add_cfid_button.setToolTip(
            _("Will add a polygon on the copper layer to serve as fiducial.")
        )
        self.add_cfid_button.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        self.tools_box.addWidget(self.add_cfid_button)

        # ## Insert Soldermask opening for Fiducial
        self.add_sm_opening_button = FCButton(_("Add Soldermask Opening"))
        self.add_sm_opening_button.setToolTip(
            _("Will add a polygon on the soldermask layer\n"
              "to serve as fiducial opening.\n"
              "The diameter is always double of the diameter\n"
              "for the copper fiducial.")
        )
        self.add_sm_opening_button.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        self.tools_box.addWidget(self.add_sm_opening_button)

        self.layout.addStretch(1)

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
