# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtGui, QtCore
from appTool import AppTool
from appGUI.GUIElements import FCDoubleSpinner, FCCheckBox, RadioSet, FCComboBox, OptionalInputSection, FCButton

from shapely.geometry import box, MultiPolygon, Polygon, LineString, LinearRing, MultiLineString
from shapely.ops import cascaded_union, unary_union, linemerge
import shapely.affinity as affinity

from matplotlib.backend_bases import KeyEvent as mpl_key_event

from numpy import Inf
from copy import deepcopy
import math
import logging
import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')

settings = QtCore.QSettings("Open Source", "FlatCAM")
if settings.contains("machinist"):
    machinist_setting = settings.value('machinist', type=int)
else:
    machinist_setting = 0


class CutOut(AppTool):

    def __init__(self, app):
        AppTool.__init__(self, app)

        self.app = app
        self.canvas = app.plotcanvas
        self.decimals = self.app.decimals

        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = CutoutUI(layout=self.layout, app=self.app)
        self.toolName = self.ui.toolName

        self.cutting_gapsize = 0.0
        self.cutting_dia = 0.0

        # true if we want to repeat the gap without clicking again on the button
        self.repeat_gap = False

        self.flat_geometry = []

        # this is the Geometry object generated in this class to be used for adding manual gaps
        self.man_cutout_obj = None

        # if mouse is dragging set the object True
        self.mouse_is_dragging = False

        # if mouse events are bound to local methods
        self.mouse_events_connected = False

        # event handlers references
        self.kp = None
        self.mm = None
        self.mr = None

        # hold the mouse position here
        self.x_pos = None
        self.y_pos = None

        # store the default data for the resulting Geometry Object
        self.default_data = {}

        # store the current cursor type to be restored after manual geo
        self.old_cursor_type = self.app.defaults["global_cursor_type"]

        # store the current selection shape status to be restored after manual geo
        self.old_selection_state = self.app.defaults['global_selection_shape']

        # Signals
        self.ui.ff_cutout_object_btn.clicked.connect(self.on_freeform_cutout)
        self.ui.rect_cutout_object_btn.clicked.connect(self.on_rectangular_cutout)

        self.ui.type_obj_radio.activated_custom.connect(self.on_type_obj_changed)
        self.ui.man_geo_creation_btn.clicked.connect(self.on_manual_geo)
        self.ui.man_gaps_creation_btn.clicked.connect(self.on_manual_gap_click)
        self.ui.reset_button.clicked.connect(self.set_tool_ui)

    def on_type_obj_changed(self, val):
        obj_type = {'grb': 0, 'geo': 2}[val]
        self.ui.obj_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.ui.obj_combo.setCurrentIndex(0)
        self.ui.obj_combo.obj_type = {"grb": "Gerber", "geo": "Geometry"}[val]

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolCutOut()")

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

        self.app.ui.notebook.setTabText(2, _("Cutout Tool"))

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Alt+X', **kwargs)

    def set_tool_ui(self):
        self.reset_fields()

        self.ui.dia.set_value(float(self.app.defaults["tools_cutouttooldia"]))
        self.ui.obj_kind_combo.set_value(self.app.defaults["tools_cutoutkind"])
        self.ui.margin.set_value(float(self.app.defaults["tools_cutoutmargin"]))
        self.ui.cutz_entry.set_value(float(self.app.defaults["tools_cutout_z"]))
        self.ui.mpass_cb.set_value(float(self.app.defaults["tools_cutout_mdepth"]))
        self.ui.maxdepth_entry.set_value(float(self.app.defaults["tools_cutout_depthperpass"]))

        self.ui.gapsize.set_value(float(self.app.defaults["tools_cutoutgapsize"]))
        self.ui.gaps.set_value(self.app.defaults["tools_gaps_ff"])
        self.ui.convex_box.set_value(self.app.defaults['tools_cutout_convexshape'])
        self.ui.big_cursor_cb.set_value(self.app.defaults['tools_cutout_big_cursor'])

        # use the current selected object and make it visible in the Paint object combobox
        sel_list = self.app.collection.get_selected()
        if len(sel_list) == 1:
            active = self.app.collection.get_active()
            kind = active.kind
            if kind == 'gerber':
                self.ui.type_obj_radio.set_value('grb')
            else:
                self.ui.type_obj_radio.set_value('geo')

            # run those once so the obj_type attribute is updated for the FCComboboxes
            # so the last loaded object is displayed
            if kind == 'gerber':
                self.on_type_obj_changed(val='grb')
            else:
                self.on_type_obj_changed(val='geo')

            self.ui.obj_combo.set_value(active.options['name'])
        else:
            kind = 'gerber'
            self.ui.type_obj_radio.set_value('grb')

            # run those once so the obj_type attribute is updated for the FCComboboxes
            # so the last loaded object is displayed
            if kind == 'gerber':
                self.on_type_obj_changed(val='grb')
            else:
                self.on_type_obj_changed(val='geo')

        # self.type_obj_radio.set_value('grb')

        self.default_data.update({
            "plot":             True,
            "cutz":             float(self.app.defaults["geometry_cutz"]),
            "multidepth":       self.app.defaults["geometry_multidepth"],
            "depthperpass":     float(self.app.defaults["geometry_depthperpass"]),
            "vtipdia":          float(self.app.defaults["geometry_vtipdia"]),
            "vtipangle":        float(self.app.defaults["geometry_vtipangle"]),
            "travelz":          float(self.app.defaults["geometry_travelz"]),
            "feedrate":         float(self.app.defaults["geometry_feedrate"]),
            "feedrate_z":       float(self.app.defaults["geometry_feedrate_z"]),
            "feedrate_rapid":   float(self.app.defaults["geometry_feedrate_rapid"]),
            "spindlespeed":     self.app.defaults["geometry_spindlespeed"],
            "dwell":            self.app.defaults["geometry_dwell"],
            "dwelltime":        float(self.app.defaults["geometry_dwelltime"]),
            "spindledir":       self.app.defaults["geometry_spindledir"],
            "ppname_g":         self.app.defaults["geometry_ppname_g"],
            "extracut":         self.app.defaults["geometry_extracut"],
            "extracut_length":  float(self.app.defaults["geometry_extracut_length"]),
            "toolchange":       self.app.defaults["geometry_toolchange"],
            "toolchangexy":     self.app.defaults["geometry_toolchangexy"],
            "toolchangez":      float(self.app.defaults["geometry_toolchangez"]),
            "startz":           self.app.defaults["geometry_startz"],
            "endz":             float(self.app.defaults["geometry_endz"]),
            "area_exclusion":   self.app.defaults["geometry_area_exclusion"],
            "area_shape":       self.app.defaults["geometry_area_shape"],
            "area_strategy":    self.app.defaults["geometry_area_strategy"],
            "area_overz":       float(self.app.defaults["geometry_area_overz"]),
            "optimization_type":    self.app.defaults["geometry_optimization_type"],

            # NCC
            "tools_nccoperation":       self.app.defaults["tools_nccoperation"],
            "tools_nccmilling_type":    self.app.defaults["tools_nccmilling_type"],
            "tools_nccoverlap":         float(self.app.defaults["tools_nccoverlap"]),
            "tools_nccmargin":          float(self.app.defaults["tools_nccmargin"]),
            "tools_nccmethod":          self.app.defaults["tools_nccmethod"],
            "tools_nccconnect":         self.app.defaults["tools_nccconnect"],
            "tools_ncccontour":         self.app.defaults["tools_ncccontour"],
            "tools_ncc_offset_choice":  self.app.defaults["tools_ncc_offset_choice"],
            "tools_ncc_offset_value":   float(self.app.defaults["tools_ncc_offset_value"]),

            # Paint
            "tools_paintoverlap":       float(self.app.defaults["tools_paintoverlap"]),
            "tools_paintoffset":        float(self.app.defaults["tools_paintoffset"]),
            "tools_paintmethod":        self.app.defaults["tools_paintmethod"],
            "tools_pathconnect":        self.app.defaults["tools_pathconnect"],
            "tools_paintcontour":       self.app.defaults["tools_paintcontour"],

            # Isolation Tool
            "tools_iso_passes":         self.app.defaults["tools_iso_passes"],
            "tools_iso_overlap":        self.app.defaults["tools_iso_overlap"],
            "tools_iso_milling_type":   self.app.defaults["tools_iso_milling_type"],
            "tools_iso_follow":         self.app.defaults["tools_iso_follow"],
            "tools_iso_isotype":        self.app.defaults["tools_iso_isotype"],
        })

    def on_freeform_cutout(self):
        log.debug("Cutout.on_freeform_cutout() was launched ...")

        # def subtract_rectangle(obj_, x0, y0, x1, y1):
        #     pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        #     obj_.subtract_polygon(pts)
        name = self.ui.obj_combo.currentText()

        # Get source object.
        try:
            cutout_obj = self.app.collection.get_by_name(str(name))
        except Exception as e:
            log.debug("CutOut.on_freeform_cutout() --> %s" % str(e))
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), name))
            return "Could not retrieve object: %s" % name

        if cutout_obj is None:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("There is no object selected for Cutout.\nSelect one and try again."))
            return

        dia = float(self.ui.dia.get_value())
        if 0 in {dia}:
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("Tool Diameter is zero value. Change it to a positive real number."))
            return "Tool Diameter is zero value. Change it to a positive real number."

        try:
            kind = self.ui.obj_kind_combo.get_value()
        except ValueError:
            return

        margin = float(self.ui.margin.get_value())
        gapsize = float(self.ui.gapsize.get_value())

        try:
            gaps = self.ui.gaps.get_value()
        except TypeError:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Number of gaps value is missing. Add it and retry."))
            return

        if gaps not in ['None', 'LR', 'TB', '2LR', '2TB', '4', '8']:
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("Gaps value can be only one of: 'None', 'lr', 'tb', '2lr', '2tb', 4 or 8. "
                                   "Fill in a correct value and retry. "))
            return

        if cutout_obj.multigeo is True:
            self.app.inform.emit('[ERROR] %s' % _("Cutout operation cannot be done on a multi-geo Geometry.\n"
                                                  "Optionally, this Multi-geo Geometry can be converted to "
                                                  "Single-geo Geometry,\n"
                                                  "and after that perform Cutout."))
            return

        convex_box = self.ui.convex_box.get_value()

        gapsize = gapsize / 2 + (dia / 2)

        def geo_init(geo_obj, app_obj):
            solid_geo = []

            if cutout_obj.kind == 'gerber':
                if isinstance(cutout_obj.solid_geometry, list):
                    cutout_obj.solid_geometry = MultiPolygon(cutout_obj.solid_geometry)

                try:
                    if convex_box:
                        object_geo = cutout_obj.solid_geometry.convex_hull
                    else:
                        object_geo = cutout_obj.solid_geometry
                except Exception as err:
                    log.debug("CutOut.on_freeform_cutout().geo_init() --> %s" % str(err))
                    object_geo = cutout_obj.solid_geometry
            else:
                object_geo = cutout_obj.solid_geometry

            def cutout_handler(geom):
                # Get min and max data for each object as we just cut rectangles across X or Y
                xxmin, yymin, xxmax, yymax = CutOut.recursive_bounds(geom)

                px = 0.5 * (xxmin + xxmax) + margin
                py = 0.5 * (yymin + yymax) + margin
                lenx = (xxmax - xxmin) + (margin * 2)
                leny = (yymax - yymin) + (margin * 2)

                proc_geometry = []
                if gaps == 'None':
                    pass
                else:
                    if gaps == '8' or gaps == '2LR':
                        points = (
                            xxmin - gapsize,  # botleft_x
                            py - gapsize + leny / 4,  # botleft_y
                            xxmax + gapsize,  # topright_x
                            py + gapsize + leny / 4  # topright_y
                        )
                        geom = self.subtract_poly_from_geo(geom, points)
                        points = (
                            xxmin - gapsize,
                            py - gapsize - leny / 4,
                            xxmax + gapsize,
                            py + gapsize - leny / 4
                        )
                        geom = self.subtract_poly_from_geo(geom, points)

                    if gaps == '8' or gaps == '2TB':
                        points = (
                            px - gapsize + lenx / 4,
                            yymin - gapsize,
                            px + gapsize + lenx / 4,
                            yymax + gapsize
                        )
                        geom = self.subtract_poly_from_geo(geom, points)
                        points = (
                            px - gapsize - lenx / 4,
                            yymin - gapsize,
                            px + gapsize - lenx / 4,
                            yymax + gapsize
                        )
                        geom = self.subtract_poly_from_geo(geom, points)

                    if gaps == '4' or gaps == 'LR':
                        points = (
                            xxmin - gapsize,
                            py - gapsize,
                            xxmax + gapsize,
                            py + gapsize
                        )
                        geom = self.subtract_poly_from_geo(geom, points)

                    if gaps == '4' or gaps == 'TB':
                        points = (
                            px - gapsize,
                            yymin - gapsize,
                            px + gapsize,
                            yymax + gapsize
                        )
                        geom = self.subtract_poly_from_geo(geom, points)

                try:
                    for g in geom:
                        if g and not g.is_empty:
                            proc_geometry.append(g)
                except TypeError:
                    if geom and not geom.is_empty:
                        proc_geometry.append(geom)

                return proc_geometry

            if kind == 'single':
                object_geo = unary_union(object_geo)

                # for geo in object_geo:
                if cutout_obj.kind == 'gerber':
                    if isinstance(object_geo, MultiPolygon):
                        x0, y0, x1, y1 = object_geo.bounds
                        object_geo = box(x0, y0, x1, y1)
                    if margin >= 0:
                        geo_buf = object_geo.buffer(margin + abs(dia / 2))
                    else:
                        geo_buf = object_geo.buffer(margin - abs(dia / 2))

                    geo = geo_buf.exterior
                else:
                    geo = object_geo
                solid_geo = cutout_handler(geom=geo)
            else:
                try:
                    __ = iter(object_geo)
                except TypeError:
                    object_geo = [object_geo]

                for geom_struct in object_geo:
                    if cutout_obj.kind == 'gerber':
                        if margin >= 0:
                            geom_struct = (geom_struct.buffer(margin + abs(dia / 2))).exterior
                        else:
                            geom_struct_buff = geom_struct.buffer(-margin + abs(dia / 2))
                            geom_struct = geom_struct_buff.interiors

                    solid_geo += cutout_handler(geom=geom_struct)

            if not solid_geo:
                app_obj.inform.emit('[ERROR_NOTCL] %s' % _("Failed."))
                return "fail"

            solid_geo = linemerge(solid_geo)
            geo_obj.solid_geometry = deepcopy(solid_geo)

            xmin, ymin, xmax, ymax = CutOut.recursive_bounds(geo_obj.solid_geometry)
            geo_obj.options['xmin'] = xmin
            geo_obj.options['ymin'] = ymin
            geo_obj.options['xmax'] = xmax
            geo_obj.options['ymax'] = ymax
            geo_obj.options['cnctooldia'] = str(dia)
            geo_obj.options['cutz'] = self.ui.cutz_entry.get_value()
            geo_obj.options['multidepth'] = self.ui.mpass_cb.get_value()
            geo_obj.options['depthperpass'] = self.ui.maxdepth_entry.get_value()

            geo_obj.tools.update({
                1: {
                    'tooldia':          str(dia),
                    'offset':           'Path',
                    'offset_value':     0.0,
                    'type':             _('Rough'),
                    'tool_type':        'C1',
                    'data':             self.default_data,
                    'solid_geometry':   geo_obj.solid_geometry
                }
            })
            geo_obj.multigeo = True
            geo_obj.tools[1]['data']['name'] = outname
            geo_obj.tools[1]['data']['cutz'] = self.ui.cutz_entry.get_value()
            geo_obj.tools[1]['data']['multidepth'] = self.ui.mpass_cb.get_value()
            geo_obj.tools[1]['data']['depthperpass'] = self.ui.maxdepth_entry.get_value()

        outname = cutout_obj.options["name"] + "_cutout"
        ret = self.app.app_obj.new_object('geometry', outname, geo_init)

        if ret == 'fail':
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed."))
            return

        cutout_obj.plot()
        self.app.inform.emit('[success] %s' % _("Any form CutOut operation finished."))
        # self.app.ui.notebook.setCurrentWidget(self.app.ui.project_tab)
        self.app.should_we_save = True

    def on_rectangular_cutout(self):
        log.debug("Cutout.on_rectangular_cutout() was launched ...")

        # def subtract_rectangle(obj_, x0, y0, x1, y1):
        #     pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        #     obj_.subtract_polygon(pts)

        name = self.ui.obj_combo.currentText()

        # Get source object.
        try:
            cutout_obj = self.app.collection.get_by_name(str(name))
        except Exception as e:
            log.debug("CutOut.on_rectangular_cutout() --> %s" % str(e))
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), name))
            return "Could not retrieve object: %s" % name

        if cutout_obj is None:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Object not found"), str(name)))

        dia = float(self.ui.dia.get_value())
        if 0 in {dia}:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Tool Diameter is zero value. Change it to a positive real number."))
            return "Tool Diameter is zero value. Change it to a positive real number."

        try:
            kind = self.ui.obj_kind_combo.get_value()
        except ValueError:
            return

        margin = float(self.ui.margin.get_value())
        gapsize = float(self.ui.gapsize.get_value())

        try:
            gaps = self.ui.gaps.get_value()
        except TypeError:
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("Number of gaps value is missing. Add it and retry."))
            return

        if gaps not in ['None', 'LR', 'TB', '2LR', '2TB', '4', '8']:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Gaps value can be only one of: "
                                                          "'None', 'lr', 'tb', '2lr', '2tb', 4 or 8. "
                                                          "Fill in a correct value and retry. "))
            return

        if cutout_obj.multigeo is True:
            self.app.inform.emit('[ERROR] %s' % _("Cutout operation cannot be done on a multi-geo Geometry.\n"
                                                  "Optionally, this Multi-geo Geometry can be converted to "
                                                  "Single-geo Geometry,\n"
                                                  "and after that perform Cutout."))
            return

        # Get min and max data for each object as we just cut rectangles across X or Y

        gapsize = gapsize / 2 + (dia / 2)

        def geo_init(geo_obj, app_obj):
            solid_geo = []
            gaps_solid_geo = None

            object_geo = cutout_obj.solid_geometry

            def cutout_rect_handler(geom):
                proc_geometry = []

                px = 0.5 * (xmin + xmax) + margin
                py = 0.5 * (ymin + ymax) + margin
                lenx = (xmax - xmin) + (margin * 2)
                leny = (ymax - ymin) + (margin * 2)

                if gaps == 'None':
                    pass
                else:
                    if gaps == '8' or gaps == '2LR':
                        points = (
                            xmin - gapsize,  # botleft_x
                            py - gapsize + leny / 4,  # botleft_y
                            xmax + gapsize,  # topright_x
                            py + gapsize + leny / 4 # topright_y
                        )
                        geom = self.subtract_poly_from_geo(geom, points)
                        points = (
                            xmin - gapsize,
                            py - gapsize - leny / 4,
                            xmax + gapsize,
                            py + gapsize - leny / 4
                        )
                        geom = self.subtract_poly_from_geo(geom, points)

                    if gaps == '8' or gaps == '2TB':
                        points = (
                            px - gapsize + lenx / 4,
                            ymin - gapsize,
                            px + gapsize + lenx / 4,
                            ymax + gapsize
                        )
                        geom = self.subtract_poly_from_geo(geom, points)
                        points = (
                            px - gapsize - lenx / 4,
                            ymin - gapsize,
                            px + gapsize - lenx / 4,
                            ymax + gapsize
                        )
                        geom = self.subtract_poly_from_geo(geom, points)

                    if gaps == '4' or gaps == 'LR':
                        points = (
                            xmin - gapsize,
                            py - gapsize,
                            xmax + gapsize,
                            py + gapsize
                        )
                        geom = self.subtract_poly_from_geo(geom, points)

                    if gaps == '4' or gaps == 'TB':
                        points = (
                            px - gapsize,
                            ymin - gapsize,
                            px + gapsize,
                            ymax + gapsize
                        )
                        geom = self.subtract_poly_from_geo(geom, points)

                try:
                    for g in geom:
                        proc_geometry.append(g)
                except TypeError:
                    proc_geometry.append(geom)
                return proc_geometry

            if kind == 'single':
                # fuse the lines
                object_geo = unary_union(object_geo)

                xmin, ymin, xmax, ymax = object_geo.bounds
                geo = box(xmin, ymin, xmax, ymax)

                # if Gerber create a buffer at a distance
                # if Geometry then cut through the geometry
                if cutout_obj.kind == 'gerber':
                    if margin >= 0:
                        geo = geo.buffer(margin + abs(dia / 2))
                    else:
                        geo = geo.buffer(margin - abs(dia / 2))

                solid_geo = cutout_rect_handler(geom=geo)

                if self.ui.thin_cb.get_value():
                    gaps_solid_geo = self.invert_cutout(geo, solid_geo)

            else:
                if cutout_obj.kind == 'geometry':
                    try:
                        __ = iter(object_geo)
                    except TypeError:
                        object_geo = [object_geo]

                    for geom_struct in object_geo:
                        geom_struct = unary_union(geom_struct)
                        xmin, ymin, xmax, ymax = geom_struct.bounds
                        geom_struct = box(xmin, ymin, xmax, ymax)

                        solid_geo += cutout_rect_handler(geom=geom_struct)
                        if self.ui.thin_cb.get_value():
                            try:
                                gaps_solid_geo += self.invert_cutout(geom_struct, solid_geo)
                            except TypeError:
                                gaps_solid_geo.append(self.invert_cutout(geom_struct, solid_geo))
                elif cutout_obj.kind == 'gerber' and margin >= 0:
                    try:
                        __ = iter(object_geo)
                    except TypeError:
                        object_geo = [object_geo]

                    for geom_struct in object_geo:
                        geom_struct = unary_union(geom_struct)
                        xmin, ymin, xmax, ymax = geom_struct.bounds
                        geom_struct = box(xmin, ymin, xmax, ymax)

                        geom_struct = geom_struct.buffer(margin + abs(dia / 2))

                        solid_geo += cutout_rect_handler(geom=geom_struct)
                        if self.ui.thin_cb.get_value():
                            try:
                                gaps_solid_geo += self.invert_cutout(geom_struct, solid_geo)
                            except TypeError:
                                gaps_solid_geo.append(self.invert_cutout(geom_struct, solid_geo))
                elif cutout_obj.kind == 'gerber' and margin < 0:
                    app_obj.inform.emit(
                        '[WARNING_NOTCL] %s' % _("Rectangular cutout with negative margin is not possible."))
                    return "fail"

            geo_obj.options['cnctooldia'] = str(dia)
            geo_obj.options['cutz'] = self.ui.cutz_entry.get_value()
            geo_obj.options['multidepth'] = self.ui.mpass_cb.get_value()
            geo_obj.options['depthperpass'] = self.ui.maxdepth_entry.get_value()

            if not solid_geo:
                app_obj.inform.emit('[ERROR_NOTCL] %s' % _("Failed."))
                return "fail"

            solid_geo = linemerge(solid_geo)
            geo_obj.solid_geometry = deepcopy(solid_geo)

            geo_obj.tools.update({
                1: {
                    'tooldia':          str(dia),
                    'offset':           'Path',
                    'offset_value':     0.0,
                    'type':             _('Rough'),
                    'tool_type':        'C1',
                    'data':             deepcopy(self.default_data),
                    'solid_geometry':   geo_obj.solid_geometry
                }
            })
            geo_obj.multigeo = True
            geo_obj.tools[1]['data']['name'] = outname
            geo_obj.tools[1]['data']['cutz'] = self.ui.cutz_entry.get_value()
            geo_obj.tools[1]['data']['multidepth'] = self.ui.mpass_cb.get_value()
            geo_obj.tools[1]['data']['depthperpass'] = self.ui.maxdepth_entry.get_value()

            if gaps_solid_geo is not None:
                geo_obj.tools.update({
                    2: {
                        'tooldia': str(dia),
                        'offset': 'Path',
                        'offset_value': 0.0,
                        'type': _('Rough'),
                        'tool_type': 'C1',
                        'data': deepcopy(self.default_data),
                        'solid_geometry': gaps_solid_geo
                    }
                })
                geo_obj.tools[2]['data']['name'] = outname
                geo_obj.tools[2]['data']['cutz'] = self.ui.thin_depth_entry.get_value()
                geo_obj.tools[2]['data']['multidepth'] = self.ui.mpass_cb.get_value()
                geo_obj.tools[2]['data']['depthperpass'] = self.ui.maxdepth_entry.get_value()

        outname = cutout_obj.options["name"] + "_cutout"
        ret = self.app.app_obj.new_object('geometry', outname, geo_init)

        if ret != 'fail':
            # cutout_obj.plot()
            self.app.inform.emit('[success] %s' % _("Any form CutOut operation finished."))
        else:
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed."))
            return

        # self.app.ui.notebook.setCurrentWidget(self.app.ui.project_tab)
        self.app.should_we_save = True

    def on_manual_gap_click(self):
        name = self.ui.man_object_combo.currentText()

        # Get source object.
        try:
            self.man_cutout_obj = self.app.collection.get_by_name(str(name))
        except Exception as e:
            log.debug("CutOut.on_manual_cutout() --> %s" % str(e))
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve Geometry object"), name))
            return

        if self.man_cutout_obj is None:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' %
                                 (_("Geometry object for manual cutout not found"), self.man_cutout_obj))
            return

        self.app.inform.emit(_("Click on the selected geometry object perimeter to create a bridge gap ..."))
        self.app.geo_editor.tool_shape.enabled = True

        self.cutting_dia = float(self.ui.dia.get_value())
        if 0 in {self.cutting_dia}:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Tool Diameter is zero value. Change it to a positive real number."))
            return

        self.cutting_gapsize = float(self.ui.gapsize.get_value())

        name = self.ui.man_object_combo.currentText()
        # Get Geometry source object to be used as target for Manual adding Gaps
        try:
            self.man_cutout_obj = self.app.collection.get_by_name(str(name))
        except Exception as e:
            log.debug("CutOut.on_manual_cutout() --> %s" % str(e))
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve Geometry object"), name))
            return

        if self.app.is_legacy is False:
            self.app.plotcanvas.graph_event_disconnect('key_press', self.app.ui.keyPressEvent)
            self.app.plotcanvas.graph_event_disconnect('mouse_press', self.app.on_mouse_click_over_plot)
            self.app.plotcanvas.graph_event_disconnect('mouse_release', self.app.on_mouse_click_release_over_plot)
            self.app.plotcanvas.graph_event_disconnect('mouse_move', self.app.on_mouse_move_over_plot)
        else:
            self.app.plotcanvas.graph_event_disconnect(self.app.kp)
            self.app.plotcanvas.graph_event_disconnect(self.app.mp)
            self.app.plotcanvas.graph_event_disconnect(self.app.mr)
            self.app.plotcanvas.graph_event_disconnect(self.app.mm)

        self.kp = self.app.plotcanvas.graph_event_connect('key_press', self.on_key_press)
        self.mm = self.app.plotcanvas.graph_event_connect('mouse_move', self.on_mouse_move)
        self.mr = self.app.plotcanvas.graph_event_connect('mouse_release', self.on_mouse_click_release)

        self.mouse_events_connected = True

        if self.ui.big_cursor_cb.get_value():
            self.old_cursor_type = self.app.defaults["global_cursor_type"]
            self.app.on_cursor_type(val="big")
        self.app.defaults['global_selection_shape'] = False

    def on_manual_cutout(self, click_pos):

        if self.man_cutout_obj is None:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' %
                                 (_("Geometry object for manual cutout not found"), self.man_cutout_obj))
            return

        # use the snapped position as reference
        snapped_pos = self.app.geo_editor.snap(click_pos[0], click_pos[1])

        cut_poly = self.cutting_geo(pos=(snapped_pos[0], snapped_pos[1]))

        # first subtract geometry for the total solid_geometry
        new_solid_geometry = CutOut.subtract_polygon(self.man_cutout_obj.solid_geometry, cut_poly)
        new_solid_geometry = linemerge(new_solid_geometry)
        self.man_cutout_obj.solid_geometry = new_solid_geometry

        # then do it or each tool in the manual cutout Geometry object
        for tool in self.man_cutout_obj.tools:
            self.man_cutout_obj.tools[tool]['solid_geometry'] = new_solid_geometry

        self.man_cutout_obj.plot()
        self.app.inform.emit('[success] %s' % _("Added manual Bridge Gap."))

        self.app.should_we_save = True

    def on_manual_geo(self):
        name = self.ui.obj_combo.currentText()

        # Get source object.
        try:
            cutout_obj = self.app.collection.get_by_name(str(name))
        except Exception as e:
            log.debug("CutOut.on_manual_geo() --> %s" % str(e))
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve Gerber object"), name))
            return "Could not retrieve object: %s" % name

        if cutout_obj is None:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("There is no Gerber object selected for Cutout.\n"
                                   "Select one and try again."))
            return

        if cutout_obj.kind != 'gerber':
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("The selected object has to be of Gerber type.\n"
                                   "Select a Gerber file and try again."))
            return

        dia = float(self.ui.dia.get_value())
        if 0 in {dia}:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Tool Diameter is zero value. Change it to a positive real number."))
            return

        try:
            kind = self.ui.obj_kind_combo.get_value()
        except ValueError:
            return

        margin = float(self.ui.margin.get_value())
        convex_box = self.ui.convex_box.get_value()

        def geo_init(geo_obj, app_obj):
            geo_union = unary_union(cutout_obj.solid_geometry)

            if convex_box:
                geo = geo_union.convex_hull
                geo_obj.solid_geometry = geo.buffer(margin + abs(dia / 2))
            elif kind == 'single':
                if isinstance(geo_union, Polygon) or \
                        (isinstance(geo_union, list) and len(geo_union) == 1) or \
                        (isinstance(geo_union, MultiPolygon) and len(geo_union) == 1):
                    geo_obj.solid_geometry = geo_union.buffer(margin + abs(dia / 2)).exterior
                elif isinstance(geo_union, MultiPolygon):
                    x0, y0, x1, y1 = geo_union.bounds
                    geo = box(x0, y0, x1, y1)
                    geo_obj.solid_geometry = geo.buffer(margin + abs(dia / 2))
                else:
                    app_obj.inform.emit('[ERROR_NOTCL] %s: %s' % (
                        _("Geometry not supported for cutout"), type(geo_union)))
                    return 'fail'
            else:
                geo = geo_union
                geo = geo.buffer(margin + abs(dia / 2))
                if isinstance(geo, Polygon):
                    geo_obj.solid_geometry = geo.exterior
                elif isinstance(geo, MultiPolygon):
                    solid_geo = []
                    for poly in geo:
                        solid_geo.append(poly.exterior)
                    geo_obj.solid_geometry = deepcopy(solid_geo)

            geo_obj.options['cnctooldia'] = str(dia)
            geo_obj.options['cutz'] = self.ui.cutz_entry.get_value()
            geo_obj.options['multidepth'] = self.ui.mpass_cb.get_value()
            geo_obj.options['depthperpass'] = self.ui.maxdepth_entry.get_value()

            geo_obj.tools.update({
                1: {
                    'tooldia':          str(dia),
                    'offset':           'Path',
                    'offset_value':     0.0,
                    'type':             _('Rough'),
                    'tool_type':        'C1',
                    'data':             self.default_data,
                    'solid_geometry':   geo_obj.solid_geometry
                }
            })
            geo_obj.multigeo = True
            geo_obj.tools[1]['data']['name'] = outname
            geo_obj.tools[1]['data']['cutz'] = self.ui.cutz_entry.get_value()
            geo_obj.tools[1]['data']['multidepth'] = self.ui.mpass_cb.get_value()
            geo_obj.tools[1]['data']['depthperpass'] = self.ui.maxdepth_entry.get_value()

        outname = cutout_obj.options["name"] + "_cutout"
        self.app.app_obj.new_object('geometry', outname, geo_init)

    def cutting_geo(self, pos):
        self.cutting_dia = float(self.ui.dia.get_value())
        self.cutting_gapsize = float(self.ui.gapsize.get_value())

        offset = self.cutting_dia / 2 + self.cutting_gapsize / 2

        # cutting area definition
        orig_x = pos[0]
        orig_y = pos[1]
        xmin = orig_x - offset
        ymin = orig_y - offset
        xmax = orig_x + offset
        ymax = orig_y + offset

        cut_poly = box(xmin, ymin, xmax, ymax)
        return cut_poly

    # To be called after clicking on the plot.
    def on_mouse_click_release(self, event):

        if self.app.is_legacy is False:
            event_pos = event.pos
            # event_is_dragging = event.is_dragging
            right_button = 2
        else:
            event_pos = (event.xdata, event.ydata)
            # event_is_dragging = self.app.plotcanvas.is_dragging
            right_button = 3

        try:
            x = float(event_pos[0])
            y = float(event_pos[1])
        except TypeError:
            return
        event_pos = (x, y)

        # do paint single only for left mouse clicks
        if event.button == 1:
            self.app.inform.emit(_("Making manual bridge gap..."))

            pos = self.app.plotcanvas.translate_coords(event_pos)

            self.on_manual_cutout(click_pos=pos)

        # if RMB then we exit
        elif event.button == right_button and self.mouse_is_dragging is False:
            if self.app.is_legacy is False:
                self.app.plotcanvas.graph_event_disconnect('key_press', self.on_key_press)
                self.app.plotcanvas.graph_event_disconnect('mouse_move', self.on_mouse_move)
                self.app.plotcanvas.graph_event_disconnect('mouse_release', self.on_mouse_click_release)
            else:
                self.app.plotcanvas.graph_event_disconnect(self.kp)
                self.app.plotcanvas.graph_event_disconnect(self.mm)
                self.app.plotcanvas.graph_event_disconnect(self.mr)

            self.app.kp = self.app.plotcanvas.graph_event_connect('key_press', self.app.ui.keyPressEvent)
            self.app.mp = self.app.plotcanvas.graph_event_connect('mouse_press', self.app.on_mouse_click_over_plot)
            self.app.mr = self.app.plotcanvas.graph_event_connect('mouse_release',
                                                                  self.app.on_mouse_click_release_over_plot)
            self.app.mm = self.app.plotcanvas.graph_event_connect('mouse_move', self.app.on_mouse_move_over_plot)

            # Remove any previous utility shape
            self.app.geo_editor.tool_shape.clear(update=True)
            self.app.geo_editor.tool_shape.enabled = False

            # signal that the mouse events are disconnected from local methods
            self.mouse_events_connected = False

            if self.ui.big_cursor_cb.get_value():
                # restore cursor
                self.app.on_cursor_type(val=self.old_cursor_type)
            # restore selection
            self.app.defaults['global_selection_shape'] = self.old_selection_state

    def on_mouse_move(self, event):

        self.app.on_mouse_move_over_plot(event=event)

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
        event_pos = (x, y)

        pos = self.canvas.translate_coords(event_pos)
        event.xdata, event.ydata = pos[0], pos[1]

        if event_is_dragging is True:
            self.mouse_is_dragging = True
        else:
            self.mouse_is_dragging = False

        try:
            x = float(event.xdata)
            y = float(event.ydata)
        except TypeError:
            return

        if self.app.grid_status():
            snap_x, snap_y = self.app.geo_editor.snap(x, y)
        else:
            snap_x, snap_y = x, y

        self.x_pos, self.y_pos = snap_x, snap_y

        # #################################################
        # ### This section makes the cutting geo to #######
        # ### rotate if it intersects the target geo ######
        # #################################################
        cut_geo = self.cutting_geo(pos=(snap_x, snap_y))
        man_geo = self.man_cutout_obj.solid_geometry

        def get_angle(geo):
            line = cut_geo.intersection(geo)

            try:
                pt1_x = line.coords[0][0]
                pt1_y = line.coords[0][1]
                pt2_x = line.coords[1][0]
                pt2_y = line.coords[1][1]
                dx = pt1_x - pt2_x
                dy = pt1_y - pt2_y

                if dx == 0 or dy == 0:
                    angle = 0
                else:
                    radian = math.atan(dx / dy)
                    angle = radian * 180 / math.pi
            except Exception:
                angle = 0
            return angle

        try:
            rot_angle = 0
            for geo_el in man_geo:
                if isinstance(geo_el, Polygon):
                    work_geo = geo_el.exterior
                    if cut_geo.intersects(work_geo):
                        rot_angle = get_angle(geo=work_geo)
                    else:
                        rot_angle = 0
                else:
                    rot_angle = 0
                    if cut_geo.intersects(geo_el):
                        rot_angle = get_angle(geo=geo_el)
                if rot_angle != 0:
                    break
        except TypeError:
            if isinstance(man_geo, Polygon):
                work_geo = man_geo.exterior
                if cut_geo.intersects(work_geo):
                    rot_angle = get_angle(geo=work_geo)
                else:
                    rot_angle = 0
            else:
                rot_angle = 0
                if cut_geo.intersects(man_geo):
                    rot_angle = get_angle(geo=man_geo)

        # rotate only if there is an angle to rotate to
        if rot_angle != 0:
            cut_geo = affinity.rotate(cut_geo, -rot_angle)

        # Remove any previous utility shape
        self.app.geo_editor.tool_shape.clear(update=True)
        self.draw_utility_geometry(geo=cut_geo)

    def draw_utility_geometry(self, geo):
        self.app.geo_editor.tool_shape.add(
            shape=geo,
            color=(self.app.defaults["global_draw_color"] + '80'),
            update=False,
            layer=0,
            tolerance=None)
        self.app.geo_editor.tool_shape.redraw()

    def on_key_press(self, event):
        # events out of the self.app.collection view (it's about Project Tab) are of type int
        if type(event) is int:
            key = event
        # events from the GUI are of type QKeyEvent
        elif type(event) == QtGui.QKeyEvent:
            key = event.key()
        elif isinstance(event, mpl_key_event):  # MatPlotLib key events are trickier to interpret than the rest
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

        # Escape = Deselect All
        if key == QtCore.Qt.Key_Escape or key == 'Escape':
            if self.mouse_events_connected is True:
                self.mouse_events_connected = False
                if self.app.is_legacy is False:
                    self.app.plotcanvas.graph_event_disconnect('key_press', self.on_key_press)
                    self.app.plotcanvas.graph_event_disconnect('mouse_move', self.on_mouse_move)
                    self.app.plotcanvas.graph_event_disconnect('mouse_release', self.on_mouse_click_release)
                else:
                    self.app.plotcanvas.graph_event_disconnect(self.kp)
                    self.app.plotcanvas.graph_event_disconnect(self.mm)
                    self.app.plotcanvas.graph_event_disconnect(self.mr)

                self.app.kp = self.app.plotcanvas.graph_event_connect('key_press', self.app.ui.keyPressEvent)
                self.app.mp = self.app.plotcanvas.graph_event_connect('mouse_press', self.app.on_mouse_click_over_plot)
                self.app.mr = self.app.plotcanvas.graph_event_connect('mouse_release',
                                                                      self.app.on_mouse_click_release_over_plot)
                self.app.mm = self.app.plotcanvas.graph_event_connect('mouse_move', self.app.on_mouse_move_over_plot)

                if self.ui.big_cursor_cb.get_value():
                    # restore cursor
                    self.app.on_cursor_type(val=self.old_cursor_type)
                # restore selection
                self.app.defaults['global_selection_shape'] = self.old_selection_state

            # Remove any previous utility shape
            self.app.geo_editor.tool_shape.clear(update=True)
            self.app.geo_editor.tool_shape.enabled = False

        # Grid toggle
        if key == QtCore.Qt.Key_G or key == 'G':
            self.app.ui.grid_snap_btn.trigger()

        # Jump to coords
        if key == QtCore.Qt.Key_J or key == 'J':
            l_x, l_y = self.app.on_jump_to()
            self.app.geo_editor.tool_shape.clear(update=True)
            geo = self.cutting_geo(pos=(l_x, l_y))
            self.draw_utility_geometry(geo=geo)

    @staticmethod
    def subtract_poly_from_geo(solid_geo, pts):
        """
        Subtract polygon made from points from the given object.
        This only operates on the paths in the original geometry,
        i.e. it converts polygons into paths.

        :param solid_geo:   Geometry from which to subtract.
        :param pts:         a tuple of coordinates in format (x0, y0, x1, y1)
        :type pts:          tuple

        x0: x coord for lower left vertex of the polygon.
        y0: y coord for lower left vertex of the polygon.
        x1: x coord for upper right vertex of the polygon.
        y1: y coord for upper right vertex of the polygon.

        :return: none
        """

        x0 = pts[0]
        y0 = pts[1]
        x1 = pts[2]
        y1 = pts[3]

        points = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

        # pathonly should be always True, otherwise polygons are not subtracted
        flat_geometry = CutOut.flatten(geometry=solid_geo)

        log.debug("%d paths" % len(flat_geometry))

        polygon = Polygon(points)
        toolgeo = cascaded_union(polygon)
        diffs = []
        for target in flat_geometry:
            if type(target) == LineString or type(target) == LinearRing:
                diffs.append(target.difference(toolgeo))
            else:
                log.warning("Not implemented.")

        return unary_union(diffs)

    @staticmethod
    def invert_cutout(target_geo, subtractor_geo):
        """

        :param target_geo:
        :param subtractor_geo:
        :return:
        """
        flat_geometry = CutOut.flatten(geometry=target_geo)

        toolgeo = cascaded_union(subtractor_geo)
        diffs = []
        for target in flat_geometry:
            if type(target) == LineString or type(target) == LinearRing:
                diffs.append(target.difference(toolgeo))
            else:
                log.warning("Not implemented.")

        return unary_union(diffs)

    @staticmethod
    def intersect_poly_with_geo(solid_geo, pts, margin):
        """
        Intersections with a polygon made from points from the given object.
        This only operates on the paths in the original geometry,
        i.e. it converts polygons into paths.

        :param solid_geo:   Geometry from which to get intersections.
        :param pts:         a tuple of coordinates in format (x0, y0, x1, y1)
        :type pts:          tuple
        :param margin:      a distance (buffer) applied to each solid_geo

        x0: x coord for lower left vertex of the polygon.
        y0: y coord for lower left vertex of the polygon.
        x1: x coord for upper right vertex of the polygon.
        y1: y coord for upper right vertex of the polygon.

        :return: none
        """

        x0 = pts[0]
        y0 = pts[1]
        x1 = pts[2]
        y1 = pts[3]

        points = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

        # pathonly should be allways True, otherwise polygons are not subtracted
        flat_geometry = CutOut.flatten(geometry=solid_geo)

        log.debug("%d paths" % len(flat_geometry))

        polygon = Polygon(points)
        toolgeo = cascaded_union(polygon)

        intersects = []
        for target in flat_geometry:
            if type(target) == LineString or type(target) == LinearRing:
                intersects.append(target.intersection(toolgeo))
            else:
                log.warning("Not implemented.")

        return unary_union(intersects)

    @staticmethod
    def flatten(geometry):
        """
        Creates a list of non-iterable linear geometry objects.
        Polygons are expanded into its exterior and interiors.

        Results are placed in self.flat_geometry

        :param geometry: Shapely type or list or list of list of such.
        """
        flat_geo = []
        try:
            for geo in geometry:
                if geo and not geo.is_empty:
                    flat_geo += CutOut.flatten(geometry=geo)
        except TypeError:
            if isinstance(geometry, Polygon):
                flat_geo.append(geometry.exterior)
                CutOut.flatten(geometry=geometry.interiors)
            else:
                flat_geo.append(geometry)

        return flat_geo

    @staticmethod
    def recursive_bounds(geometry):
        """
        Return the bounds of the biggest bounding box in geometry, one that include all.

        :param geometry:    a iterable object that holds geometry
        :return:            Returns coordinates of rectangular bounds of geometry: (xmin, ymin, xmax, ymax).
        """

        # now it can get bounds for nested lists of objects

        def bounds_rec(obj):
            try:
                minx = Inf
                miny = Inf
                maxx = -Inf
                maxy = -Inf

                for k in obj:
                    minx_, miny_, maxx_, maxy_ = bounds_rec(k)
                    minx = min(minx, minx_)
                    miny = min(miny, miny_)
                    maxx = max(maxx, maxx_)
                    maxy = max(maxy, maxy_)
                return minx, miny, maxx, maxy
            except TypeError:
                # it's a Shapely object, return it's bounds
                if obj:
                    return obj.bounds

        return bounds_rec(geometry)

    @staticmethod
    def subtract_polygon(target_geo, subtractor):
        """
        Subtract subtractor polygon from the target_geo. This only operates on the paths in the target_geo,
        i.e. it converts polygons into paths.

        :param target_geo:      geometry from which to subtract
        :param subtractor:      a list of Points, a LinearRing or a Polygon that will be subtracted from target_geo
        :return:                a cascaded union of the resulting geometry
        """

        if target_geo is None:
            target_geo = []

        # flatten() takes care of possible empty geometry making sure that is filtered
        flat_geometry = CutOut.flatten(target_geo)
        log.debug("%d paths" % len(flat_geometry))

        toolgeo = unary_union(subtractor)

        diffs = []
        for target in flat_geometry:
            if isinstance(target, LineString) or isinstance(target, LinearRing) or isinstance(target, MultiLineString):
                diffs.append(target.difference(toolgeo))
            else:
                log.warning("Not implemented.")

        return unary_union(diffs)

    def reset_fields(self):
        self.ui.obj_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))


class CutoutUI:

    toolName = _("Cutout PCB")

    def __init__(self, layout, app):
        self.app = app
        self.decimals = self.app.decimals
        self.layout = layout

        # Title
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

        # Form Layout
        grid0 = QtWidgets.QGridLayout()
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        self.layout.addLayout(grid0)

        self.object_label = QtWidgets.QLabel('<b>%s:</b>' % _("Source Object"))
        self.object_label.setToolTip('%s.' % _("Object to be cutout"))

        grid0.addWidget(self.object_label, 0, 0, 1, 2)

        # Object kind
        self.kindlabel = QtWidgets.QLabel('%s:' % _('Kind'))
        self.kindlabel.setToolTip(
            _("Choice of what kind the object we want to cutout is.<BR>"
              "- <B>Single</B>: contain a single PCB Gerber outline object.<BR>"
              "- <B>Panel</B>: a panel PCB Gerber object, which is made\n"
              "out of many individual PCB outlines.")
        )
        self.obj_kind_combo = RadioSet([
            {"label": _("Single"), "value": "single"},
            {"label": _("Panel"), "value": "panel"},
        ])
        grid0.addWidget(self.kindlabel, 1, 0)
        grid0.addWidget(self.obj_kind_combo, 1, 1)

        # Type of object to be cutout
        self.type_obj_radio = RadioSet([
            {"label": _("Gerber"), "value": "grb"},
            {"label": _("Geometry"), "value": "geo"},
        ])

        self.type_obj_combo_label = QtWidgets.QLabel('%s:' % _("Type"))
        self.type_obj_combo_label.setToolTip(
            _("Specify the type of object to be cutout.\n"
              "It can be of type: Gerber or Geometry.\n"
              "What is selected here will dictate the kind\n"
              "of objects that will populate the 'Object' combobox.")
        )

        grid0.addWidget(self.type_obj_combo_label, 2, 0)
        grid0.addWidget(self.type_obj_radio, 2, 1)

        # Object to be cutout
        self.obj_combo = FCComboBox()
        self.obj_combo.setModel(self.app.collection)
        self.obj_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.obj_combo.is_last = True

        grid0.addWidget(self.obj_combo, 3, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 4, 0, 1, 2)

        grid0.addWidget(QtWidgets.QLabel(''), 5, 0, 1, 2)

        self.param_label = QtWidgets.QLabel('<b>%s:</b>' % _("Tool Parameters"))
        grid0.addWidget(self.param_label, 6, 0, 1, 2)

        # Tool Diameter
        self.dia = FCDoubleSpinner(callback=self.confirmation_message)
        self.dia.set_precision(self.decimals)
        self.dia.set_range(0.0000, 9999.9999)

        self.dia_label = QtWidgets.QLabel('%s:' % _("Tool Diameter"))
        self.dia_label.setToolTip(
            _("Diameter of the tool used to cutout\n"
              "the PCB shape out of the surrounding material.")
        )
        grid0.addWidget(self.dia_label, 8, 0)
        grid0.addWidget(self.dia, 8, 1)

        # Cut Z
        cutzlabel = QtWidgets.QLabel('%s:' % _('Cut Z'))
        cutzlabel.setToolTip(
            _(
                "Cutting depth (negative)\n"
                "below the copper surface."
            )
        )
        self.cutz_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.cutz_entry.set_precision(self.decimals)

        if machinist_setting == 0:
            self.cutz_entry.setRange(-9999.9999, -0.00001)
        else:
            self.cutz_entry.setRange(-9999.9999, 9999.9999)

        self.cutz_entry.setSingleStep(0.1)

        grid0.addWidget(cutzlabel, 9, 0)
        grid0.addWidget(self.cutz_entry, 9, 1)

        # Multi-pass
        self.mpass_cb = FCCheckBox('%s:' % _("Multi-Depth"))
        self.mpass_cb.setToolTip(
            _(
                "Use multiple passes to limit\n"
                "the cut depth in each pass. Will\n"
                "cut multiple times until Cut Z is\n"
                "reached."
            )
        )

        self.maxdepth_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.maxdepth_entry.set_precision(self.decimals)
        self.maxdepth_entry.setRange(0, 9999.9999)
        self.maxdepth_entry.setSingleStep(0.1)

        self.maxdepth_entry.setToolTip(
            _(
                "Depth of each pass (positive)."
            )
        )

        grid0.addWidget(self.mpass_cb, 10, 0)
        grid0.addWidget(self.maxdepth_entry, 10, 1)

        # Thin gaps
        self.thin_cb = FCCheckBox('%s:' % _("Thin gaps"))
        self.thin_cb.setToolTip(
            _("Active only when multi depth is active (negative value)\n"
              "If checked, it will mill de gaps until the specified depth."))

        self.thin_depth_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.thin_depth_entry.set_precision(self.decimals)
        if machinist_setting == 0:
            self.thin_depth_entry.setRange(-9999.9999, -0.00001)
        else:
            self.thin_depth_entry.setRange(-9999.9999, 9999.9999)
        self.thin_depth_entry.setSingleStep(0.1)

        self.thin_depth_entry.setToolTip(
            _("Active only when multi depth is active (negative value)\n"
              "If checked, it will mill de gaps until the specified depth."))

        grid0.addWidget(self.thin_cb, 12, 0)
        grid0.addWidget(self.thin_depth_entry, 12, 1)

        self.ois_mpass_geo = OptionalInputSection(self.mpass_cb,
                                                  [
                                                      self.maxdepth_entry,
                                                      self.thin_cb,
                                                      self.thin_depth_entry
                                                  ])

        # Margin
        self.margin = FCDoubleSpinner(callback=self.confirmation_message)
        self.margin.set_range(-9999.9999, 9999.9999)
        self.margin.setSingleStep(0.1)
        self.margin.set_precision(self.decimals)

        self.margin_label = QtWidgets.QLabel('%s:' % _("Margin"))
        self.margin_label.setToolTip(
            _("Margin over bounds. A positive value here\n"
              "will make the cutout of the PCB further from\n"
              "the actual PCB border")
        )
        grid0.addWidget(self.margin_label, 14, 0)
        grid0.addWidget(self.margin, 14, 1)

        # Gapsize
        self.gapsize = FCDoubleSpinner(callback=self.confirmation_message)
        self.gapsize.set_precision(self.decimals)

        self.gapsize_label = QtWidgets.QLabel('%s:' % _("Gap size"))
        self.gapsize_label.setToolTip(
            _("The size of the bridge gaps in the cutout\n"
              "used to keep the board connected to\n"
              "the surrounding material (the one \n"
              "from which the PCB is cutout).")
        )
        grid0.addWidget(self.gapsize_label, 16, 0)
        grid0.addWidget(self.gapsize, 16, 1)

        # How gaps wil be rendered:
        # lr    - left + right
        # tb    - top + bottom
        # 4     - left + right +top + bottom
        # 2lr   - 2*left + 2*right
        # 2tb   - 2*top + 2*bottom
        # 8     - 2*left + 2*right +2*top + 2*bottom

        # Surrounding convex box shape
        self.convex_box = FCCheckBox('%s' % _("Convex Shape"))
        # self.convex_box_label = QtWidgets.QLabel('%s' % _("Convex Sh."))
        self.convex_box.setToolTip(
            _("Create a convex shape surrounding the entire PCB.\n"
              "Used only if the source object type is Gerber.")
        )
        grid0.addWidget(self.convex_box, 18, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 20, 0, 1, 2)

        grid0.addWidget(QtWidgets.QLabel(''), 22, 0, 1, 2)

        # Title2
        title_param_label = QtWidgets.QLabel("<b>%s %s</b>:" % (_('Automatic'), _("Bridge Gaps")))
        title_param_label.setToolTip(
            _("This section handle creation of automatic bridge gaps.")
        )
        grid0.addWidget(title_param_label, 24, 0, 1, 2)

        # Gaps
        gaps_label = QtWidgets.QLabel('%s:' % _('Gaps'))
        gaps_label.setToolTip(
            _("Number of gaps used for the Automatic cutout.\n"
              "There can be maximum 8 bridges/gaps.\n"
              "The choices are:\n"
              "- None  - no gaps\n"
              "- lr    - left + right\n"
              "- tb    - top + bottom\n"
              "- 4     - left + right +top + bottom\n"
              "- 2lr   - 2*left + 2*right\n"
              "- 2tb  - 2*top + 2*bottom\n"
              "- 8     - 2*left + 2*right +2*top + 2*bottom")
        )
        # gaps_label.setMinimumWidth(60)

        self.gaps = FCComboBox()
        gaps_items = ['None', 'LR', 'TB', '4', '2LR', '2TB', '8']
        for it in gaps_items:
            self.gaps.addItem(it)
            # self.gaps.setStyleSheet('background-color: rgb(255,255,255)')
        grid0.addWidget(gaps_label, 26, 0)
        grid0.addWidget(self.gaps, 26, 1)

        # Buttons
        self.ff_cutout_object_btn = FCButton(_("Generate Geometry"))
        self.ff_cutout_object_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/irregular32.png'))
        self.ff_cutout_object_btn.setToolTip(
            _("Cutout the selected object.\n"
              "The cutout shape can be of any shape.\n"
              "Useful when the PCB has a non-rectangular shape.")
        )
        self.ff_cutout_object_btn.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        grid0.addWidget(self.ff_cutout_object_btn, 28, 0, 1, 2)

        self.rect_cutout_object_btn = FCButton(_("Generate Geometry"))
        self.rect_cutout_object_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/rectangle32.png'))
        self.rect_cutout_object_btn.setToolTip(
            _("Cutout the selected object.\n"
              "The resulting cutout shape is\n"
              "always a rectangle shape and it will be\n"
              "the bounding box of the Object.")
        )
        self.rect_cutout_object_btn.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        grid0.addWidget(self.rect_cutout_object_btn, 30, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 32, 0, 1, 2)

        grid0.addWidget(QtWidgets.QLabel(''), 34, 0, 1, 2)

        # MANUAL BRIDGE GAPS
        title_manual_label = QtWidgets.QLabel("<b>%s %s</b>:" % (_('Manual'), _("Bridge Gaps")))
        title_manual_label.setToolTip(
            _("This section handle creation of manual bridge gaps.\n"
              "This is done by mouse clicking on the perimeter of the\n"
              "Geometry object that is used as a cutout object. ")
        )
        grid0.addWidget(title_manual_label, 36, 0, 1, 2)

        # Big Cursor
        big_cursor_label = QtWidgets.QLabel('%s:' % _("Big cursor"))
        big_cursor_label.setToolTip(
            _("Use a big cursor when adding manual gaps."))
        self.big_cursor_cb = FCCheckBox()

        grid0.addWidget(big_cursor_label, 38, 0)
        grid0.addWidget(self.big_cursor_cb, 38, 1)

        # Generate a surrounding Geometry object
        self.man_geo_creation_btn = FCButton(_("Generate Manual Geometry"))
        self.man_geo_creation_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/rectangle32.png'))
        self.man_geo_creation_btn.setToolTip(
            _("If the object to be cutout is a Gerber\n"
              "first create a Geometry that surrounds it,\n"
              "to be used as the cutout, if one doesn't exist yet.\n"
              "Select the source Gerber file in the top object combobox.")
        )
        # self.man_geo_creation_btn.setStyleSheet("""
        #                         QPushButton
        #                         {
        #                             font-weight: bold;
        #                         }
        #                         """)
        grid0.addWidget(self.man_geo_creation_btn, 40, 0, 1, 2)

        # Manual Geo Object
        self.man_object_combo = FCComboBox()
        self.man_object_combo.setModel(self.app.collection)
        self.man_object_combo.setRootModelIndex(self.app.collection.index(2, 0, QtCore.QModelIndex()))
        self.man_object_combo.is_last = True
        self.man_object_combo.obj_type = "Geometry"

        self.man_object_label = QtWidgets.QLabel('%s:' % _("Manual cutout Geometry"))
        self.man_object_label.setToolTip(
            _("Geometry object used to create the manual cutout.")
        )
        # self.man_object_label.setMinimumWidth(60)

        grid0.addWidget(self.man_object_label, 42, 0, 1, 2)
        grid0.addWidget(self.man_object_combo, 44, 0, 1, 2)

        self.man_gaps_creation_btn = FCButton(_("Manual Add Bridge Gaps"))
        self.man_gaps_creation_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/gaps32.png'))
        self.man_gaps_creation_btn.setToolTip(
            _("Use the left mouse button (LMB) click\n"
              "to create a bridge gap to separate the PCB from\n"
              "the surrounding material.\n"
              "The LMB click has to be done on the perimeter of\n"
              "the Geometry object used as a cutout geometry.")
        )
        self.man_gaps_creation_btn.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        grid0.addWidget(self.man_gaps_creation_btn, 46, 0, 1, 2)

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

        # ############################ FINSIHED GUI ###################################
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
