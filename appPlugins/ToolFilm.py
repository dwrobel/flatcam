# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################
import math

from PyQt6 import QtCore, QtWidgets, QtGui

from appTool import AppTool
from appGUI.GUIElements import RadioSet, FCDoubleSpinner, FCCheckBox, \
    OptionalHideInputSection, FCComboBox, FCFileSaveDialog, FCButton, FCLabel, FCSpinner, \
    VerticalScrollArea, FCGridLayout, FCFrame, FCComboBox2

from copy import deepcopy
import logging
from shapely.geometry import Polygon, MultiPolygon, Point, LineString, LinearRing
import shapely.affinity as affinity
from shapely.ops import unary_union

from reportlab.graphics import renderPDF
from reportlab.pdfgen import canvas
from reportlab.graphics import renderPM
from reportlab.lib.units import inch, mm
from reportlab.lib.pagesizes import landscape, portrait

from svglib.svglib import svg2rlg
from xml.dom.minidom import parseString as parse_xml_string
from lxml import etree as ET
from io import StringIO

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class Film(AppTool):

    def __init__(self, app):
        AppTool.__init__(self, app)

        self.decimals = self.app.decimals
        self.units = self.app.app_units

        # #############################################################################################################
        # ######################################## Tool GUI ###########################################################
        # #############################################################################################################
        self.ui = FilmUI(layout=self.layout, app=self.app)
        self.pluginName = self.ui.pluginName

        # #############################################################################################################
        # #####################################    Signals     ########################################################
        # #############################################################################################################
        self.connect_signals_at_init()
        # #############################################################################################################

        self.screen_dpi = 96

    def on_type_obj_index_changed(self, val):
        obj_type = 2 if val == 'geo' else 0
        self.ui.tf_object_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.ui.tf_object_combo.setCurrentIndex(0)
        self.ui.tf_object_combo.obj_type = {
            "grb": "gerber", "geo": "geometry"
        }[self.ui.tf_type_obj_combo.get_value()]

    def on_type_box_index_changed(self, val):
        obj_type = 2 if val == 'geo' else 0
        self.ui.tf_box_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.ui.tf_box_combo.setCurrentIndex(0)
        self.ui.tf_box_combo.obj_type = {
            "grb": "gerber", "geo": "geometry"
        }[self.ui.tf_type_obj_combo.get_value()]

    def on_object_selection_changed(self, current, previous):
        found_idx = None
        for tab_idx in range(self.app.ui.notebook.count()):
            if self.app.ui.notebook.tabText(tab_idx) == self.ui.pluginName:
                found_idx = True
                break

        if found_idx:
            try:
                name = current.indexes()[0].internalPointer().obj.obj_options['name']
                kind = current.indexes()[0].internalPointer().obj.kind

                if kind in ['gerber', 'geometry']:
                    obj_type = {'gerber': 'grb', 'geometry': 'geo'}[kind]
                    self.ui.tf_type_obj_combo.set_value(obj_type)
                    self.ui.tf_type_box_combo.set_value(obj_type)

                    self.ui.tf_object_combo.set_value(name)
                    self.ui.tf_box_combo.set_value(name)
            except Exception:
                pass

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolFilm()")

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

        self.app.ui.notebook.setTabText(2, _("Film"))

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Alt+L', **kwargs)

    def connect_signals_at_init(self):
        # #############################################################################
        # ############################ SIGNALS ########################################
        # #############################################################################
        self.ui.level.toggled.connect(self.on_level_changed)

        self.ui.film_object_button.clicked.connect(self.on_film_creation)
        self.ui.tf_type_obj_combo.activated_custom.connect(self.on_type_obj_index_changed)
        self.ui.tf_type_box_combo.activated_custom.connect(self.on_type_box_index_changed)

        self.ui.film_type.activated_custom.connect(self.ui.on_film_type)
        self.ui.source_punch.activated_custom.connect(self.ui.on_punch_source)
        self.ui.file_type_radio.activated_custom.connect(self.ui.on_file_type)

        self.app.proj_selection_changed.connect(self.on_object_selection_changed)

        self.ui.reset_button.clicked.connect(self.set_tool_ui)

    def set_tool_ui(self):

        self.clear_ui(self.layout)
        self.ui = FilmUI(layout=self.layout, app=self.app)
        self.pluginName = self.ui.pluginName
        self.connect_signals_at_init()

        self.reset_fields()

        f_type = self.app.options["tools_film_polarity"] if self.app.options["tools_film_polarity"] else 'neg'
        self.ui.film_type.set_value(str(f_type))
        self.ui.on_film_type(val=f_type)

        b_entry = self.app.options["tools_film_boundary"] if self.app.options["tools_film_boundary"] else 0.0
        self.ui.boundary_entry.set_value(float(b_entry))

        scale_stroke_width = self.app.options["tools_film_scale_stroke"] if \
            self.app.options["tools_film_scale_stroke"] else 0.0
        self.ui.film_scale_stroke_entry.set_value(float(scale_stroke_width))

        self.ui.punch_cb.set_value(False)
        self.ui.source_punch.set_value('exc')

        self.ui.film_scale_cb.set_value(self.app.options["tools_film_scale_cb"])
        self.ui.film_scalex_entry.set_value(float(self.app.options["tools_film_scale_x_entry"]))
        self.ui.film_scaley_entry.set_value(float(self.app.options["tools_film_scale_y_entry"]))
        self.ui.scale_ref_combo.set_value(self.app.options["tools_film_scale_ref"])

        self.ui.film_skew_cb.set_value(self.app.options["tools_film_skew_cb"])
        self.ui.film_skewx_entry.set_value(float(self.app.options["tools_film_skew_x_entry"]))
        self.ui.film_skewy_entry.set_value(float(self.app.options["tools_film_skew_y_entry"]))
        self.ui.skew_ref_combo.set_value(self.app.options["tools_film_skew_ref"])

        self.ui.film_mirror_cb.set_value(self.app.options["tools_film_mirror_cb"])
        self.ui.film_mirror_axis.set_value(self.app.options["tools_film_mirror_axis_radio"])
        self.ui.file_type_radio.set_value(self.app.options["tools_film_file_type_radio"])
        self.ui.orientation_radio.set_value(self.app.options["tools_film_orientation"])
        self.ui.pagesize_combo.set_value(self.app.options["tools_film_pagesize"])

        self.ui.png_dpi_spinner.set_value(self.app.options["tools_film_png_dpi"])

        self.ui.convex_box_cb.set_value(self.app.options["tools_film_shape"])
        self.ui.rounded_cb.set_value(self.app.options["tools_film_rounded"])

        obj = self.app.collection.get_active()
        if obj:
            obj_name = obj.obj_options['name']
            if obj.kind == 'gerber':
                # run once to make sure that the obj_type attribute is updated in the FCComboBox
                self.ui.tf_type_obj_combo.set_value('grb')
                self.ui.tf_type_box_combo.set_value('grb')
                # run once to update the obj_type attribute in the FCCombobox so the last object is showed in cb
                self.on_type_obj_index_changed(val='grb')
                self.on_type_box_index_changed(val='grb')

            elif obj.kind == 'geometry':
                # run once to make sure that the obj_type attribute is updated in the FCComboBox
                self.ui.tf_type_obj_combo.set_value('geo')
                self.ui.tf_type_box_combo.set_value('geo')
                # run once to update the obj_type attribute in the FCCombobox so the last object is showed in cb
                self.on_type_obj_index_changed(val='geo')
                self.on_type_box_index_changed(val='geo')

            self.ui.tf_object_combo.set_value(obj_name)
            self.ui.tf_box_combo.set_value(obj_name)
        else:
            # run once to make sure that the obj_type attribute is updated in the FCComboBox
            self.ui.tf_type_obj_combo.set_value('grb')
            self.ui.tf_type_box_combo.set_value('grb')
            # run once to update the obj_type attribute in the FCCombobox so the last object is showed in cb
            self.on_type_obj_index_changed(val='grb')
            self.on_type_box_index_changed(val='grb')

        # Show/Hide Advanced Options
        app_mode = self.app.options["global_app_level"]
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

            self.ui.film_adj_label.hide()
            self.ui.adj_frame.hide()

            self.ui.film_scale_cb.set_value(False)
            self.ui.film_skew_cb.set_value(False)
            self.ui.film_mirror_cb.set_value(False)
            self.ui.film_scale_stroke_entry.set_value(0.0)

        else:
            self.ui.level.setText('%s' % _('Advanced'))
            self.ui.level.setStyleSheet("""
                                        QToolButton
                                        {
                                            color: red;
                                        }
                                        """)

            self.ui.film_adj_label.show()
            self.ui.adj_frame.show()

            self.ui.film_scale_cb.set_value(self.app.options["tools_film_scale_cb"])
            self.ui.film_skew_cb.set_value(self.app.options["tools_film_skew_cb"])
            self.ui.film_mirror_cb.set_value(self.app.options["tools_film_mirror_cb"])

            scale_stroke_width = self.app.options["tools_film_scale_stroke"] if \
                self.app.options["tools_film_scale_stroke"] else 0.0
            self.ui.film_scale_stroke_entry.set_value(float(scale_stroke_width))

    def on_film_creation(self):
        self.app.log.debug("ToolFilm.Film.on_film_creation() started ...")

        try:
            name = self.ui.tf_object_combo.currentText()
        except Exception:
            self.app.inform.emit('[ERROR_NOTCL] %s %s' %
                                 (_("No object is selected."), _("Load an object for Film and retry.")))
            return

        try:
            boxname = self.ui.tf_box_combo.currentText()
        except Exception:
            self.app.inform.emit('[ERROR_NOTCL] %s %s' %
                                 (_("No object is selected."), _("Load an object for Box and retry.")))
            return

        if name == '' or boxname == '':
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("No object is selected."))
            return

        scale_stroke_width = float(self.ui.film_scale_stroke_entry.get_value())
        source = self.ui.source_punch.get_value()
        file_type = self.ui.file_type_radio.get_value()

        # #################################################################
        # ################ STARTING THE JOB ###############################
        # #################################################################

        self.app.inform.emit(_("Generating Film ..."))

        if self.ui.film_type.get_value() == "pos":

            if self.ui.punch_cb.get_value() is False:
                self.generate_positive_normal_film(name, boxname, factor=scale_stroke_width, ftype=file_type)
            else:
                self.generate_positive_punched_film(name, boxname, source, factor=scale_stroke_width, ftype=file_type)
        else:
            self.generate_negative_film(name, boxname, factor=scale_stroke_width, ftype=file_type)

    def generate_positive_normal_film(self, name, boxname, factor, ftype='svg'):
        self.app.log.debug("ToolFilm.Film.generate_positive_normal_film() started ...")

        scale_factor_x = 1
        scale_factor_y = 1
        skew_factor_x = None
        skew_factor_y = None
        mirror = None

        reference_list = ['center', 'bottomleft', 'topleft', 'bottomright', 'topright']

        scale_reference = reference_list[int(self.ui.scale_ref_combo.get_value())]
        skew_reference = reference_list[int(self.ui.skew_ref_combo.get_value())]

        if self.ui.film_scale_cb.get_value():
            if self.ui.film_scalex_entry.get_value() != 1.0:
                scale_factor_x = self.ui.film_scalex_entry.get_value()
            if self.ui.film_scaley_entry.get_value() != 1.0:
                scale_factor_y = self.ui.film_scaley_entry.get_value()

        if self.ui.film_skew_cb.get_value():
            if self.ui.film_skewx_entry.get_value() != 0.0:
                skew_factor_x = self.ui.film_skewx_entry.get_value()
            if self.ui.film_skewy_entry.get_value() != 0.0:
                skew_factor_y = self.ui.film_skewy_entry.get_value()

        if self.ui.film_mirror_cb.get_value():
            mirror = self.ui.film_mirror_axis.get_value()

        if ftype == 'svg':
            filter_ext = "SVG Files (*.SVG);;"\
                         "All Files (*.*)"
        elif ftype == 'png':
            filter_ext = "PNG Files (*.PNG);;" \
                         "All Files (*.*)"
        else:
            filter_ext = "PDF Files (*.PDF);;" \
                         "All Files (*.*)"

        try:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Export positive film"),
                directory=self.app.get_last_save_folder() + '/' + name + '_film',
                ext_filter=filter_ext)
        except TypeError:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Export positive film"),
                ext_filter=filter_ext)

        filename = str(filename)

        if str(filename) != "":
            self.export_positive_handler(name, boxname, filename,
                                         scale_stroke_factor=factor,
                                         scale_factor_x=scale_factor_x, scale_factor_y=scale_factor_y,
                                         scale_reference=scale_reference,
                                         skew_factor_x=skew_factor_x, skew_factor_y=skew_factor_y,
                                         skew_reference=skew_reference,
                                         mirror=mirror,
                                         opacity_val=1.0,
                                         ftype=ftype
                                         )
            return

        # if we reach here then the filename is null
        self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))

    def generate_positive_punched_film(self, name, boxname, source, factor, ftype='svg'):

        film_obj = self.app.collection.get_by_name(name)

        if source == 'exc':
            self.app.log.debug("ToolFilm.Film.generate_positive_punched_film() with Excellon source started ...")

            try:
                exc_name = self.ui.exc_combo.currentText()
            except Exception:
                self.app.inform.emit('[ERROR_NOTCL] %s' %
                                     _("No Excellon object selected. Load an object for punching reference and retry."))
                return

            exc_obj = self.app.collection.get_by_name(exc_name)
            exc_solid_geometry = MultiPolygon(exc_obj.solid_geometry)
            punched_solid_geometry = MultiPolygon(film_obj.solid_geometry).difference(exc_solid_geometry)

            def init_func(new_obj, app_obj):
                new_obj.solid_geometry = deepcopy(punched_solid_geometry)

            outname = name + "_punched"
            self.app.app_obj.new_object('gerber', outname, init_func)

            self.generate_positive_normal_film(outname, boxname, factor=factor, ftype=ftype)
        else:
            self.app.log.debug("ToolFilm.Film.generate_positive_punched_film() with Pad center source started ...")

            punch_size = float(self.ui.punch_size_spinner.get_value())

            punching_geo = []
            for apid in film_obj.tools:
                if film_obj.tools[apid]['type'] == 'C':
                    if punch_size >= float(film_obj.tools[apid]['size']):
                        self.app.inform.emit('[ERROR_NOTCL] %s' %
                                             _("Failed. Punch hole size "
                                               "is bigger than some of the apertures in the Gerber object."))
                        return 'fail'
                    else:
                        for elem in film_obj.tools[apid]['geometry']:
                            if 'follow' in elem:
                                if isinstance(elem['follow'], Point):
                                    punching_geo.append(elem['follow'].buffer(punch_size / 2))
                else:
                    if punch_size >= float(film_obj.tools[apid]['width']) or \
                            punch_size >= float(film_obj.tools[apid]['height']):
                        self.app.inform.emit('[ERROR_NOTCL] %s' %
                                             _("Failed. Punch hole size "
                                               "is bigger than some of the apertures in the Gerber object."))
                        return 'fail'
                    else:
                        for elem in film_obj.tools[apid]['geometry']:
                            if 'follow' in elem:
                                if isinstance(elem['follow'], Point):
                                    punching_geo.append(elem['follow'].buffer(punch_size / 2))

            punching_geo = MultiPolygon(punching_geo)
            if not isinstance(film_obj.solid_geometry, Polygon):
                temp_solid_geometry = MultiPolygon(film_obj.solid_geometry)
            else:
                temp_solid_geometry = film_obj.solid_geometry
            punched_solid_geometry = temp_solid_geometry.difference(punching_geo)

            if punched_solid_geometry == temp_solid_geometry:
                self.app.inform.emit('[WARNING_NOTCL] %s' %
                                     _("Failed. The new object geometry "
                                       "is the same as the one in the source object geometry..."))
                return 'fail'

            def init_func(new_obj, app_obj):
                new_obj.solid_geometry = deepcopy(punched_solid_geometry)

            outname = name + "_punched"
            self.app.app_obj.new_object('gerber', outname, init_func)

            self.generate_positive_normal_film(outname, boxname, factor=factor, ftype=ftype)

    def generate_negative_film(self, name, boxname, factor, ftype='svg'):
        self.app.log.debug("ToolFilm.Film.generate_negative_film() started ...")

        use_convex_hull = self.ui.convex_box_cb.get_value()
        rounded_box = self.ui.rounded_cb.get_value()

        scale_factor_x = 1
        scale_factor_y = 1
        skew_factor_x = None
        skew_factor_y = None
        mirror = None

        reference_list = ['center', 'bottomleft', 'topleft', 'bottomright', 'topright']

        scale_reference = reference_list[int(self.ui.scale_ref_combo.get_value())]
        skew_reference = reference_list[int(self.ui.skew_ref_combo.get_value())]

        if self.ui.film_scale_cb.get_value():
            if self.ui.film_scalex_entry.get_value() != 1.0:
                scale_factor_x = self.ui.film_scalex_entry.get_value()
            if self.ui.film_scaley_entry.get_value() != 1.0:
                scale_factor_y = self.ui.film_scaley_entry.get_value()

        if self.ui.film_skew_cb.get_value():
            if self.ui.film_skewx_entry.get_value() != 0.0:
                skew_factor_x = self.ui.film_skewx_entry.get_value()
            if self.ui.film_skewy_entry.get_value() != 0.0:
                skew_factor_y = self.ui.film_skewy_entry.get_value()

        if self.ui.film_mirror_cb.get_value():
            mirror = self.ui.film_mirror_axis.get_value()

        border = self.ui.boundary_entry.get_value()

        if border is None:
            border = 0

        if ftype == 'svg':
            filter_ext = "SVG Files (*.SVG);;"\
                         "All Files (*.*)"
        elif ftype == 'png':
            filter_ext = "PNG Files (*.PNG);;" \
                         "All Files (*.*)"
        else:
            filter_ext = "PDF Files (*.PDF);;" \
                         "All Files (*.*)"

        try:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Export negative film"),
                directory=self.app.get_last_save_folder() + '/' + name + '_film',
                ext_filter=filter_ext)
        except TypeError:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Export negative film"),
                ext_filter=filter_ext)

        filename = str(filename)

        if str(filename) == "":
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
            return
        else:
            self.export_negative_handler(name, boxname, filename, border,
                                         scale_stroke_factor=factor,
                                         scale_factor_x=scale_factor_x, scale_factor_y=scale_factor_y,
                                         scale_reference=scale_reference,
                                         skew_factor_x=skew_factor_x, skew_factor_y=skew_factor_y,
                                         skew_reference=skew_reference,
                                         mirror=mirror, ftype=ftype,
                                         use_convex_hull=use_convex_hull,
                                         rounded_box=rounded_box
                                         )

    def export_negative_handler(self, obj_name, box_name, filename, boundary,
                                scale_stroke_factor=0.00,
                                scale_factor_x=1, scale_factor_y=1, scale_reference='center',
                                skew_factor_x=None, skew_factor_y=None, skew_reference='center',
                                mirror=None, opacity_val=1.0,
                                use_thread=True, ftype='svg', use_convex_hull=False, rounded_box=False):
        """
        Exports a Geometry Object to an SVG file in negative.

        :param obj_name:            the name of the FlatCAM object to be saved as SVG
        :param box_name:            the name of the FlatCAM object to be used as delimitation
                                    of the content to be saved
        :param filename:            Path to the SVG file to save to.
        :param boundary:            thickness of a black border to surround all the features
        :param scale_stroke_factor: factor by which to change/scale the thickness of the features
        :param scale_factor_x:      factor to scale the svg geometry on the X axis
        :param scale_factor_y:      factor to scale the svg geometry on the Y axis
        :param scale_reference:     reference to use for transformation.
                                    Values: 'center', 'bottomleft', 'topleft', 'bottomright', 'topright'
        :param skew_factor_x:       factor to skew the svg geometry on the X axis
        :param skew_factor_y:       factor to skew the svg geometry on the Y axis
        :param skew_reference:      reference to use for transformation.
                                    Values: 'center', 'bottomleft', 'topleft', 'bottomright', 'topright'
        :param mirror:              can be 'x' or 'y' or 'both'. Axis on which to mirror the svg geometry
        :param opacity_val:
        :param use_thread:          if to be run in a separate thread; boolean
        :param ftype:               the type of file for saving the film: 'svg', 'png' or 'pdf'
        :param use_convex_hull:     Bool; if True it will make the negative box to minimize the black coverage
        :param rounded_box:         Bool; if True the negative bounded box will have rounded corners
                                    Works only in case the object used as box has multiple geometries
        :return:
        """
        self.app.defaults.report_usage("export_negative_handler()")

        if filename is None:
            filename = self.app.options["global_last_save_folder"]

        self.app.log.debug("Film.export_svg() negative")

        try:
            obj = self.app.collection.get_by_name(str(obj_name))
        except Exception:
            return "Could not retrieve object: %s" % obj_name

        try:
            box = self.app.collection.get_by_name(str(box_name))
        except Exception:
            return "Could not retrieve object: %s" % box_name

        if box is None:
            self.app.inform.emit('[WARNING_NOTCL] %s: %s' % (_("No object Box. Using instead"), obj))
            box = obj

        scale_factor_x = scale_factor_x
        scale_factor_y = scale_factor_y

        p_size = self.ui.pagesize_combo.get_value()
        orientation = self.ui.orientation_radio.get_value()
        color = obj.obj_options['tools_film_color']
        transparency_level = opacity_val

        def make_negative_film(color, transparency_level, scale_factor_x, scale_factor_y, use_convex_hull, rounded_box):
            self.app.log.debug("FilmTool.export_negative_handler().make_negative_film()")

            self.screen_dpi = self.app.qapp.screens()[0].logicalDotsPerInch()

            new_png_dpi = self.ui.png_dpi_spinner.get_value()
            dpi_rate = new_png_dpi / self.screen_dpi

            if dpi_rate != 1 and ftype == 'png':
                scale_factor_x += dpi_rate
                scale_factor_y += dpi_rate

            transformed_box_geo = self.transform_geometry(box, scale_factor_x=scale_factor_x,
                                                          scale_factor_y=scale_factor_y,
                                                          scale_reference=scale_reference,
                                                          skew_factor_x=skew_factor_x, skew_factor_y=skew_factor_y,
                                                          skew_reference=skew_reference,
                                                          mirror=mirror)

            transformed_obj_geo = self.transform_geometry(obj, scale_factor_x=scale_factor_x,
                                                          scale_factor_y=scale_factor_y,
                                                          scale_reference=scale_reference,
                                                          skew_factor_x=skew_factor_x, skew_factor_y=skew_factor_y,
                                                          skew_reference=skew_reference,
                                                          mirror=mirror)

            exported_svg = self.create_svg_geometry(transformed_obj_geo, scale_stroke_factor=scale_stroke_factor)

            svg_units = obj.units.lower()
            bounds = transformed_box_geo.bounds

            doc_final = self.create_negative_svg(svg_geo=exported_svg, box_bounds=bounds, r_box=rounded_box,
                                                 box_geo=transformed_box_geo, c_hull=use_convex_hull, margin=boundary,
                                                 color=color, opacity=transparency_level, svg_units=svg_units)

            obj_bounds = obj.bounds()
            ret = self.write_output_file(content2save=doc_final, filename=filename, file_type=ftype, p_size=p_size,
                                         orientation=orientation, source_bounds=obj_bounds, box_bounds=bounds)

            if ret == 'fail':
                return 'fail'

            if self.app.options["global_open_style"] is False:
                self.app.file_opened.emit("SVG", filename)
            self.app.file_saved.emit("SVG", filename)
            self.app.inform.emit('[success] %s: %s' % (_("Film file exported to"), filename))

        if use_thread is True:
            def job_thread_film():
                with self.app.proc_container.new(_("Working...")):
                    try:
                        make_negative_film(color=color, transparency_level=transparency_level,
                                           scale_factor_x=scale_factor_x, scale_factor_y=scale_factor_y,
                                           use_convex_hull=use_convex_hull, rounded_box=rounded_box)
                    except Exception as e:
                        self.app.log.error("export_negative_handler() process -> %s" % str(e))
                        return

            self.app.worker_task.emit({'fcn': job_thread_film, 'params': []})
        else:
            make_negative_film(scale_factor_x=scale_factor_x, scale_factor_y=scale_factor_y,
                               use_convex_hull=use_convex_hull, rounded_box=rounded_box)

    def create_negative_svg(self, svg_geo, box_bounds, r_box, box_geo, c_hull, margin,  color, opacity, svg_units):
        # Change the attributes of the exported SVG
        # We don't need stroke-width - wrong, we do when we have lines with certain width
        # We set opacity to maximum
        # We set the color to the inversed color
        root = ET.fromstring(svg_geo)
        for child in root:
            child.set('fill', self.get_complementary(color))
            child.set('opacity', str(opacity))
            child.set('stroke', self.get_complementary(color))

        uom = svg_units

        # Convert everything to strings for use in the xml doc
        size = box_bounds[2] - box_bounds[0], box_bounds[3] - box_bounds[1]

        svgwidth = str(size[0] + (2 * margin))
        svgheight = str(size[1] + (2 * margin))
        minx = str(box_bounds[0] - margin)
        miny = str(box_bounds[1] + margin + size[1])
        # miny_rect = str(bounds[1] - boundary)

        # Add a SVG Header and footer to the svg output from shapely
        # The transform flips the Y Axis so that everything renders
        # properly within svg apps such as inkscape
        svg_header = '<svg xmlns="http://www.w3.org/2000/svg" ' \
                     'version="1.1" xmlns:xlink="http://www.w3.org/1999/xlink" '
        svg_header += 'width="' + svgwidth + uom + '" '
        svg_header += 'height="' + svgheight + uom + '" '
        svg_header += 'viewBox="' + minx + ' -' + miny + ' ' + svgwidth + ' ' + svgheight + '" '
        svg_header += '>'
        svg_header += '<g transform="scale(1,-1)">'
        svg_footer = '</g> </svg>'

        # decide if to round the bounding box for the negative
        join_s = 1 if r_box else 2

        if isinstance(box_geo, (LineString, LinearRing)):
            b_geo = Polygon(box_geo).buffer(margin, join_style=join_s)
            coords_list = list(b_geo.exterior.coords)
        elif isinstance(box_geo, list) and len(box_geo) == 1 and isinstance(box_geo[0], (LineString, LinearRing)):
            b_geo = Polygon(box_geo[0]).buffer(margin, join_style=join_s)
            coords_list = list(b_geo.exterior.coords)
        elif isinstance(box_geo, Polygon):
            coords_list = list(box_geo.exterior.coords)
        elif isinstance(box_geo, list) and len(box_geo) == 1 and isinstance(box_geo[0], Polygon):
            coords_list = list(box_geo[0].exterior.coords)
        else:
            if c_hull:
                buff_box = box_geo.convex_hull.buffer(margin, join_style=join_s)
            else:
                buff_box = box_geo.envelope.buffer(margin, join_style=join_s)
            box_buff_outline = buff_box.exterior
            coords_list = list(box_buff_outline.coords)

        points_container = ''
        for coord_tuple in coords_list:
            points_container += '%s, %s ' % (str(coord_tuple[0]), str(coord_tuple[1]))

        first_svg_elem_tag = 'polygon'
        first_svg_elem_attribs = {
            'points': points_container,
            'id': 'neg_rect',
            'style': 'fill:%s;opacity:1.0;stroke-width:0.0' % str(color)
        }

        root.insert(0, ET.Element(first_svg_elem_tag, first_svg_elem_attribs))
        exported_svg = ET.tostring(root)

        svg_elem = svg_header + str(exported_svg) + svg_footer

        # Parse the xml through a xml parser just to add line feeds
        # and to make it look more pretty for the output
        doc = parse_xml_string(svg_elem)
        return doc.toprettyxml()

    @staticmethod
    def get_complementary(color_param):
        # strip the # from the beginning
        our_color = color_param[1:]

        # convert the string into hex
        our_color = int(our_color, 16)

        # invert the three bytes
        # as good as substracting each of RGB component by 255(FF)
        comp_color = 0xFFFFFF ^ our_color

        # convert the color back to hex by prefixing a #
        comp_color = "#%06X" % comp_color

        # return the result
        return comp_color

    def export_positive_handler(self, obj_name, box_name, filename,
                                scale_stroke_factor=0.00,
                                scale_factor_x=1, scale_factor_y=1, scale_reference='center',
                                skew_factor_x=None, skew_factor_y=None, skew_reference='center',
                                mirror=None, opacity_val=1.0,
                                use_thread=True, ftype='svg'):

        """
        Exports a Geometry Object to an SVG file in positive black.

        :param obj_name:            the name of the FlatCAM object to be saved
        :param box_name:            the name of the FlatCAM object to be used as delimitation of the content to be saved
        :param filename:            Path to the file to save to.
        :param scale_stroke_factor: factor by which to change/scale the thickness of the features
        :param scale_factor_x:      factor to scale the geometry on the X axis
        :param scale_factor_y:      factor to scale the geometry on the Y axis
        :param scale_reference:     reference to use for transformation.
                                    Values: 'center', 'bottomleft', 'topleft', 'bottomright', 'topright'
        :param skew_factor_x:       factor to skew the geometry on the X axis
        :param skew_factor_y:       factor to skew the geometry on the Y axis
        :param skew_reference:      reference to use for transformation.
                                    Values: 'center', 'bottomleft'
        :param mirror:              can be 'x' or 'y' or 'both'. Axis on which to mirror the svg geometry
        :param opacity_val:
        :param use_thread:          if to be run in a separate thread; boolean
        :param ftype:               the type of file for saving the film: 'svg', 'png' or 'pdf'

        :return:
        """
        self.app.defaults.report_usage("export_positive_handler()")

        if filename is None:
            filename = self.app.options["global_last_save_folder"]

        self.app.log.debug("Film.export_positive_handler() black")

        try:
            obj = self.app.collection.get_by_name(str(obj_name))
        except Exception:
            return "Could not retrieve object: %s" % obj_name

        try:
            box = self.app.collection.get_by_name(str(box_name))
        except Exception:
            return "Could not retrieve object: %s" % box_name

        if box is None:
            self.app.inform.emit('[WARNING_NOTCL] %s: %s' % (_("No object Box. Using instead"), obj))
            box = obj

        scale_factor_x = scale_factor_x
        scale_factor_y = scale_factor_y

        p_size = self.ui.pagesize_combo.get_value()
        orientation = self.ui.orientation_radio.get_value()
        color = obj.obj_options['tools_film_color']
        transparency_level = opacity_val

        def make_positive_film(color, transparency_level, scale_factor_x, scale_factor_y):
            self.app.log.debug("FilmTool.export_positive_handler().make_positive_film()")

            self.screen_dpi = self.app.qapp.screens()[0].logicalDotsPerInch()

            new_png_dpi = self.ui.png_dpi_spinner.get_value()
            dpi_rate = new_png_dpi / self.screen_dpi

            if dpi_rate != 1 and ftype == 'png':
                scale_factor_x += dpi_rate
                scale_factor_y += dpi_rate

            transformed_box_geo = self.transform_geometry(box, scale_factor_x=scale_factor_x,
                                                          scale_factor_y=scale_factor_y,
                                                          scale_reference=scale_reference,
                                                          skew_factor_x=skew_factor_x, skew_factor_y=skew_factor_y,
                                                          skew_reference=skew_reference,
                                                          mirror=mirror)

            transformed_obj_geo = self.transform_geometry(obj, scale_factor_x=scale_factor_x,
                                                          scale_factor_y=scale_factor_y,
                                                          scale_reference=scale_reference,
                                                          skew_factor_x=skew_factor_x, skew_factor_y=skew_factor_y,
                                                          skew_reference=skew_reference,
                                                          mirror=mirror)

            exported_svg = self.create_svg_geometry(transformed_obj_geo, scale_stroke_factor=scale_stroke_factor)

            bounds = transformed_box_geo.bounds
            svg_units = obj.units.lower()
            # Define a boundary around SVG
            margin = self.ui.boundary_entry.get_value()

            doc_final = self.create_positive_svg(svg_geo=exported_svg, box_bounds=bounds, margin=margin, color=color,
                                                 opacity=transparency_level, svg_units=svg_units)

            obj_bounds = obj.bounds()
            ret = self.write_output_file(content2save=doc_final, filename=filename, file_type=ftype, p_size=p_size,
                                         orientation=orientation, source_bounds=obj_bounds, box_bounds=bounds)

            if ret == 'fail':
                return 'fail'

            if self.app.options["global_open_style"] is False:
                self.app.file_opened.emit("SVG", filename)
            self.app.file_saved.emit("SVG", filename)
            self.app.inform.emit('[success] %s: %s' % (_("Film file exported to"), filename))

        if use_thread is True:
            def job_thread_film():
                with self.app.proc_container.new(_("Working...")):
                    try:
                        make_positive_film(color=color, transparency_level=transparency_level,
                                           scale_factor_x=scale_factor_x, scale_factor_y=scale_factor_y)
                    except Exception as e:
                        self.app.log.error("export_positive_handler() process -> %s" % str(e))
                        return

            self.app.worker_task.emit({'fcn': job_thread_film, 'params': []})
        else:
            make_positive_film(color=color, transparency_level=transparency_level,
                               scale_factor_x=scale_factor_x, scale_factor_y=scale_factor_y)

    @staticmethod
    def create_positive_svg(svg_geo, box_bounds, margin,  color, opacity, svg_units):
        # Change the attributes of the exported SVG
        # We don't need stroke-width
        # We set opacity to maximum
        # We set the colour to WHITE
        root = ET.fromstring(svg_geo)
        for child in root:
            child.set('fill', str(color))
            child.set('opacity', str(opacity))
            child.set('stroke', str(color))

        exported_svg = ET.tostring(root)

        # This contain the measure units
        uom = svg_units

        # Convert everything to strings for use in the xml doc
        size = box_bounds[2] - box_bounds[0], box_bounds[3] - box_bounds[1]

        svgwidth = str(size[0] + (2 * margin))
        svgheight = str(size[1] + (2 * margin))
        minx = str(box_bounds[0] - margin)
        miny = str(box_bounds[1] + margin + size[1])

        # Add a SVG Header and footer to the svg output from shapely
        # The transform flips the Y Axis so that everything renders
        # properly within svg apps such as inkscape
        svg_header = '<svg xmlns="http://www.w3.org/2000/svg" ' \
                     'version="1.1" xmlns:xlink="http://www.w3.org/1999/xlink" '
        svg_header += 'width="' + svgwidth + uom + '" '
        svg_header += 'height="' + svgheight + uom + '" '
        svg_header += 'viewBox="' + minx + ' -' + miny + ' ' + svgwidth + ' ' + svgheight + '" '
        svg_header += '>'
        svg_header += '<g transform="scale(1,-1)">'
        svg_footer = '</g> </svg>'

        svg_elem = str(svg_header) + str(exported_svg) + str(svg_footer)

        # Parse the xml through a xml parser just to add line feeds
        # and to make it look more pretty for the output
        doc = parse_xml_string(svg_elem)
        return doc.toprettyxml()

    def write_output_file(self, content2save, filename, file_type, p_size, orientation, source_bounds, box_bounds):
        p_msg = '[ERROR_NOTCL] %s' % _("Permission denied, saving not possible.\n"
                                       "Most likely another app is holding the file open and not accessible.")
        if file_type == 'svg':
            try:
                with open(filename, 'w') as fp:
                    fp.write(content2save)
            except PermissionError:
                self.app.inform.emit(p_msg)
                return 'fail'
        elif file_type == 'png':
            try:
                doc_final = StringIO(content2save)
                drawing = svg2rlg(doc_final)
                renderPM.drawToFile(drawing, filename, 'PNG')
            except PermissionError:
                self.app.inform.emit(p_msg)
                return 'fail'
            except Exception as e:
                self.app.log.error("FilmTool.write_output_file() --> PNG output --> %s" % str(e))
                return 'fail'
        else:  # PDF
            try:
                if self.units == 'IN':
                    unit = inch
                else:
                    unit = mm

                if p_size == 'Bounds':
                    page_size = None
                elif orientation == 'p':
                    page_size = portrait(self.ui.pagesize[p_size])
                else:
                    page_size = landscape(self.ui.pagesize[p_size])

                xmin, ymin, xmax, ymax = source_bounds
                if page_size:
                    page_xmax, page_ymax = (
                        page_size[0] / mm,
                        page_size[1] / mm
                    )
                else:
                    page_xmax, page_ymax = xmax, ymax

                if xmax < 0 or ymax < 0 or xmin > page_xmax or ymin > page_ymax:
                    err_msg = '[ERROR_NOTCL] %s %s' % \
                              (
                                  _("Failed."),
                                  _("The artwork has to be within the selected page size in order to be visible.\n"
                                    "For 'Bounds' page size, it needs to be in the first quadrant.")
                              )
                    self.app.inform.emit(err_msg)
                    return 'fail'

                doc_final = StringIO(content2save)
                drawing = svg2rlg(doc_final)

                if p_size == 'Bounds':
                    renderPDF.drawToFile(drawing, filename)
                else:
                    my_canvas = canvas.Canvas(filename, pagesize=page_size)
                    my_canvas.translate(box_bounds[0] * unit, box_bounds[1] * unit)
                    renderPDF.draw(drawing, my_canvas, 0, 0)
                    my_canvas.save()
            except PermissionError:
                self.app.inform.emit(p_msg)
                return 'fail'
            except Exception as e:
                self.app.log.error("FilmTool.write_output_file() --> PDF output --> %s" % str(e))
                return 'fail'

    @staticmethod
    def transform_geometry(obj, scale_factor_x=None, scale_factor_y=None,
                           skew_factor_x=None, skew_factor_y=None,
                           skew_reference='center', scale_reference='center', mirror=None):
        """
        Return a transformed geometry made from a Shapely geometry collection property of the `obj` object

        :return: Shapely geometry transformed
        """

        # Make sure we see a Shapely Geometry class and not a list
        if obj.kind.lower() == 'geometry':
            flat_geo = []
            if obj.multigeo:
                for tool in obj.tools:
                    flat_geo += obj.flatten(obj.tools[tool]['solid_geometry'])
                transformed_geo = unary_union(flat_geo)
            else:
                transformed_geo = unary_union(obj.flatten())
        else:
            transformed_geo = unary_union(obj.flatten())

        # SCALING
        if scale_factor_x or scale_factor_y:
            xmin, ymin, xmax, ymax = transformed_geo.bounds
            ref_scale_val = 'center'
            if scale_reference == 'topleft':
                ref_scale_val = (xmin, ymax)
            elif scale_reference == 'bottomleft':
                ref_scale_val = (xmin, ymin)
            elif scale_reference == 'topright':
                ref_scale_val = (xmax, ymax)
            elif scale_reference == 'bottomright':
                ref_scale_val = (xmax, ymin)

            if scale_factor_x and not scale_factor_y:
                val_x = scale_factor_x
                val_y = 0
            elif not scale_factor_x and scale_factor_y:
                val_x = 0
                val_y = scale_factor_y
            else:
                val_x = scale_factor_x
                val_y = scale_factor_y
            transformed_geo = affinity.scale(transformed_geo, val_x, val_y, origin=ref_scale_val)

        # SKEWING
        if skew_factor_x or skew_factor_y:
            xmin, ymin, xmax, ymax = transformed_geo.bounds
            if skew_reference == 'bottomleft':
                ref_skew_val = (xmin, ymin)
                if skew_factor_x and not skew_factor_y:
                    skew_angle_x = math.degrees(math.atan2(skew_factor_x, (ymax - ymin)))
                    skew_angle_y = 0.0
                elif not skew_factor_x and skew_factor_y:
                    skew_angle_x = 0.0
                    skew_angle_y = math.degrees(math.atan2(skew_factor_y, (xmax - xmin)))
                else:
                    skew_angle_x = math.degrees(math.atan2(skew_factor_x, (ymax - ymin)))
                    skew_angle_y = math.degrees(math.atan2(skew_factor_y, (xmax - xmin)))
            else:
                ref_skew_val = 'center'
                if skew_factor_x and not skew_factor_y:
                    skew_angle_x = math.degrees(math.atan2(skew_factor_x, ((ymax - ymin) * 0.5)))
                    skew_angle_y = 0.0
                elif not skew_factor_x and skew_factor_y:
                    skew_angle_x = 0.0
                    skew_angle_y = math.degrees(math.atan2(skew_factor_y, ((xmax - xmin) * 0.5)))
                else:
                    skew_angle_x = math.degrees(math.atan2(skew_factor_x, ((ymax - ymin) * 0.5)))
                    skew_angle_y = math.degrees(math.atan2(skew_factor_y, ((xmax - xmin) * 0.5)))

            transformed_geo = affinity.skew(transformed_geo, skew_angle_x, skew_angle_y, origin=ref_skew_val)

        if mirror:
            if mirror == 'x':
                transformed_geo = affinity.scale(transformed_geo, 1.0, -1.0, origin='center')
            if mirror == 'y':
                transformed_geo = affinity.scale(transformed_geo, -1.0, 1.0, origin='center')
            if mirror == 'both':
                transformed_geo = affinity.scale(transformed_geo, -1.0, -1.0, origin='center')

        return transformed_geo

    @staticmethod
    def create_svg_geometry(geom, scale_stroke_factor):
        """
        Return SVG geometry made from a Shapely geometry collection property of the `obj` object

        :param geom:                Shapely geometry collection
        :type geom:
        :param scale_stroke_factor: multiplication factor for the SVG stroke-width used within shapely's svg export
                                    If 0 or less which is invalid then default to 0.01
                                    This value appears to work for zooming, and getting the output svg line width
                                    to match that viewed on screen with FlatCam
                                    MS: I choose a factor of 0.01 so the scale is right for PCB UV film
        :type scale_stroke_factor:  float
        :return:                    SVG geometry
        :rtype:
        """

        if scale_stroke_factor <= 0:
            scale_stroke_factor = 0.01

        # Convert to a SVG
        svg_elem = geom.svg(scale_factor=scale_stroke_factor)
        return svg_elem

    def reset_fields(self):
        self.ui.tf_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.ui.tf_box_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))


class FilmUI:

    pluginName = _("Film")

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
            _("Create a positive/negative film for UV exposure.")
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
        # Source Object Frame
        # #############################################################################################################
        self.obj_combo_label = FCLabel('<span style="color:darkorange;"><b>%s</b></span>' % _("Source Object"))
        self.obj_combo_label.setToolTip(
            _("Excellon object for drilling/milling operation.")
        )
        self.tools_box.addWidget(self.obj_combo_label)

        obj_frame = FCFrame()
        self.tools_box.addWidget(obj_frame)

        obj_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        obj_frame.setLayout(obj_grid)

        # Type of object for which to create the film
        self.tf_type_obj_combo = RadioSet([{'label': _('Gerber'), 'value': 'grb'},
                                           {'label': _('Geometry'), 'value': 'geo'}])

        self.tf_type_obj_combo_label = FCLabel('%s:' % _("Type"))
        self.tf_type_obj_combo_label.setToolTip(
            _("Specify the type of object for which to create the film.\n"
              "The object can be of type: Gerber or Geometry.\n"
              "The selection here decide the type of objects that will be\n"
              "in the Film Object combobox.")
        )
        obj_grid.addWidget(self.tf_type_obj_combo_label, 0, 0)
        obj_grid.addWidget(self.tf_type_obj_combo, 0, 1)

        # List of objects for which we can create the film
        self.tf_object_combo = FCComboBox()
        self.tf_object_combo.setModel(self.app.collection)
        self.tf_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.tf_object_combo.is_last = True

        obj_grid.addWidget(self.tf_object_combo, 2, 0, 1, 2)

        # Type of Box Object to be used as an envelope for film creation
        # Within this we can create negative
        self.tf_type_box_combo = RadioSet([{'label': _('Gerber'), 'value': 'grb'},
                                           {'label': _('Geometry'), 'value': 'geo'}])

        self.tf_type_box_combo_label = FCLabel('%s:' % _("Box Type"))
        self.tf_type_box_combo_label.setToolTip(
            _("Specify the type of object to be used as an container for\n"
              "film creation. It can be: Gerber or Geometry type."
              "The selection here decide the type of objects that will be\n"
              "in the Box Object combobox.")
        )
        obj_grid.addWidget(self.tf_type_box_combo_label, 4, 0)
        obj_grid.addWidget(self.tf_type_box_combo, 4, 1)

        # Box
        self.tf_box_combo = FCComboBox()
        self.tf_box_combo.setModel(self.app.collection)
        self.tf_box_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.tf_box_combo.is_last = True

        obj_grid.addWidget(self.tf_box_combo, 6, 0, 1, 2)

        # separator_line = QtWidgets.QFrame()
        # separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        # separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        # obj_grid.addWidget(separator_line, 8, 0, 1, 2)

        # #############################################################################################################
        # Adjustments Frame
        # #############################################################################################################
        self.film_adj_label = FCLabel('<span style="color:green;"><b>%s</b></span>' % _("Adjustments"))
        self.film_adj_label.setToolTip(
            _("Compensate print distortions.")
        )

        self.tools_box.addWidget(self.film_adj_label)

        self.adj_frame = FCFrame()
        self.tools_box.addWidget(self.adj_frame)

        adj_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        self.adj_frame.setLayout(adj_grid)

        # Scale Geometry
        self.film_scale_cb = FCCheckBox('%s' % _("Scale"))
        self.film_scale_cb.setToolTip(
            _("A value greater than 1 will compact the film\n"
              "while a value less than 1 will jolt it.")
        )
        self.film_scale_cb.setStyleSheet(
            """
            QCheckBox {font-weight: bold; color: black}
            """
        )
        adj_grid.addWidget(self.film_scale_cb, 2, 0, 1, 2)

        # Scale X
        self.film_scalex_label = FCLabel('%s:' % _("X factor"))
        self.film_scalex_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.film_scalex_entry.set_range(-999.9999, 999.9999)
        self.film_scalex_entry.set_precision(self.decimals)
        self.film_scalex_entry.setSingleStep(0.01)

        adj_grid.addWidget(self.film_scalex_label, 4, 0)
        adj_grid.addWidget(self.film_scalex_entry, 4, 1)

        # Scale Y
        self.film_scaley_label = FCLabel('%s:' % _("Y factor"))
        self.film_scaley_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.film_scaley_entry.set_range(-999.9999, 999.9999)
        self.film_scaley_entry.set_precision(self.decimals)
        self.film_scaley_entry.setSingleStep(0.01)

        adj_grid.addWidget(self.film_scaley_label, 6, 0)
        adj_grid.addWidget(self.film_scaley_entry, 6, 1)

        # Scale reference
        self.scale_ref_label = FCLabel('%s:' % _("Reference"))
        self.scale_ref_label.setToolTip(
            _("The reference point to be used as origin for the adjustment.")
        )

        self.scale_ref_combo = FCComboBox2()
        self.scale_ref_combo.addItems(
            [_('Center'), _('Bottom Left'), _('Top Left'), _('Bottom Right'), _('Top right')])

        adj_grid.addWidget(self.scale_ref_label, 8, 0)
        adj_grid.addWidget(self.scale_ref_combo, 8, 1)

        self.ois_scale = OptionalHideInputSection(self.film_scale_cb,
                                                  [
                                                      self.film_scalex_label,
                                                      self.film_scalex_entry,
                                                      self.film_scaley_label,
                                                      self.film_scaley_entry,
                                                      self.scale_ref_label,
                                                      self.scale_ref_combo
                                                  ])

        self.scale_separator_line = QtWidgets.QFrame()
        self.scale_separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.scale_separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        adj_grid.addWidget(self.scale_separator_line, 10, 0, 1, 2)

        # Skew Geometry
        self.film_skew_cb = FCCheckBox('%s' % _("Skew"))
        self.film_skew_cb.setToolTip(
            _("Positive values will skew to the right\n"
              "while negative values will skew to the left.")
        )
        self.film_skew_cb.setStyleSheet(
            """
            QCheckBox {font-weight: bold; color: black}
            """
        )
        adj_grid.addWidget(self.film_skew_cb, 12, 0, 1, 2)

        # Skew X
        self.film_skewx_label = FCLabel('%s:' % _("X val"))
        self.film_skewx_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.film_skewx_entry.set_range(-999.9999, 999.9999)
        self.film_skewx_entry.set_precision(self.decimals)
        self.film_skewx_entry.setSingleStep(0.01)

        adj_grid.addWidget(self.film_skewx_label, 14, 0)
        adj_grid.addWidget(self.film_skewx_entry, 14, 1)

        # Skew Y
        self.film_skewy_label = FCLabel('%s:' % _("Y val"))
        self.film_skewy_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.film_skewy_entry.set_range(-999.9999, 999.9999)
        self.film_skewy_entry.set_precision(self.decimals)
        self.film_skewy_entry.setSingleStep(0.01)

        adj_grid.addWidget(self.film_skewy_label, 16, 0)
        adj_grid.addWidget(self.film_skewy_entry, 16, 1)

        # Skew Reference
        self.skew_ref_label = FCLabel('%s:' % _("Reference"))
        self.skew_ref_label.setToolTip(
            _("The reference point to be used as origin for the adjustment.")
        )

        self.skew_ref_combo = FCComboBox2()
        self.skew_ref_combo.addItems(
            [_('Center'), _('Bottom Left')])

        adj_grid.addWidget(self.skew_ref_label, 18, 0)
        adj_grid.addWidget(self.skew_ref_combo, 18, 1)

        self.ois_skew = OptionalHideInputSection(self.film_skew_cb,
                                                 [
                                                     self.film_skewx_label,
                                                     self.film_skewx_entry,
                                                     self.film_skewy_label,
                                                     self.film_skewy_entry,
                                                     self.skew_ref_label,
                                                     self.skew_ref_combo
                                                 ])

        self.skew_separator_line1 = QtWidgets.QFrame()
        self.skew_separator_line1.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.skew_separator_line1.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        adj_grid.addWidget(self.skew_separator_line1, 20, 0, 1, 2)

        # Mirror Geometry
        self.film_mirror_cb = FCCheckBox('%s' % _("Mirror"))
        self.film_mirror_cb.setToolTip(
            _("Mirror the film geometry on the selected axis or on both.")
        )
        self.film_mirror_cb.setStyleSheet(
            """
            QCheckBox {font-weight: bold; color: black}
            """
        )
        adj_grid.addWidget(self.film_mirror_cb, 22, 0, 1, 2)

        self.film_mirror_axis = RadioSet([{'label': _('X'), 'value': 'x'},
                                          {'label': _('Y'), 'value': 'y'},
                                          {'label': _('Both'), 'value': 'both'}],
                                         compact=True)
        self.film_mirror_axis_label = FCLabel('%s:' % _("Axis"))
        self.film_mirror_axis_label.setToolTip(
            _("Mirror the film geometry on the selected axis or on both.")
        )

        adj_grid.addWidget(self.film_mirror_axis_label, 24, 0)
        adj_grid.addWidget(self.film_mirror_axis, 24, 1)

        self.ois_mirror = OptionalHideInputSection(self.film_mirror_cb,
                                                   [
                                                       self.film_mirror_axis_label,
                                                       self.film_mirror_axis
                                                   ])

        # #############################################################################################################
        # Parameters Frame
        # #############################################################################################################
        self.film_param_label = FCLabel('<span style="color:blue;"><b>%s</b></span>' % _("Parameters"))
        self.tools_box.addWidget(self.film_param_label)

        par_frame = FCFrame()
        self.tools_box.addWidget(par_frame)

        param_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        par_frame.setLayout(param_grid)

        # Convex Shape
        # Surrounding convex box shape
        self.convex_box_label = FCLabel('%s:' % _("Convex Shape"))
        self.convex_box_label.setToolTip(
            _("Create a convex shape surrounding the entire PCB.\n"
              "If not checked the shape is rectangular.")
        )
        self.convex_box_cb = FCCheckBox()

        param_grid.addWidget(self.convex_box_label, 0, 0)
        param_grid.addWidget(self.convex_box_cb, 0, 1)

        # Rounded corners
        self.rounded_label = FCLabel('%s:' % _("Rounded"))
        self.rounded_label.setToolTip(
            _("Resulting geometry will have rounded corners.")
        )

        self.rounded_cb = FCCheckBox()

        param_grid.addWidget(self.rounded_label, 2, 0)
        param_grid.addWidget(self.rounded_cb, 2, 1)

        # Scale Stroke size
        self.film_scale_stroke_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.film_scale_stroke_entry.set_range(-999.9999, 999.9999)
        self.film_scale_stroke_entry.setSingleStep(0.01)
        self.film_scale_stroke_entry.set_precision(self.decimals)

        self.film_scale_stroke_label = FCLabel('%s:' % _("Scale Stroke"))
        self.film_scale_stroke_label.setToolTip(
            _("Scale the line stroke thickness of each feature in the SVG file.\n"
              "It means that the line that envelope each SVG feature will be thicker or thinner,\n"
              "therefore the fine features may be more affected by this parameter.")
        )
        param_grid.addWidget(self.film_scale_stroke_label, 4, 0)
        param_grid.addWidget(self.film_scale_stroke_entry, 4, 1)

        # Polarity
        self.film_type = RadioSet([{'label': _('Positive'), 'value': 'pos'},
                                   {'label': _('Negative'), 'value': 'neg'}],
                                  compact=True)
        self.film_type_label = FCLabel('%s:' % _("Polarity"))
        self.film_type_label.setToolTip(
            _("Generate a Positive black film or a Negative film.")
        )
        param_grid.addWidget(self.film_type_label, 6, 0)
        param_grid.addWidget(self.film_type, 6, 1)

        # Border for negative film generation
        self.boundary_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.boundary_entry.set_range(-999.9999, 999.9999)
        self.boundary_entry.setSingleStep(0.01)
        self.boundary_entry.set_precision(self.decimals)

        self.boundary_label = FCLabel('%s:' % _("Border"))
        self.boundary_label.setToolTip(
            _("Specify a border around the object.\n"
              "Only for negative film.\n"
              "It helps if we use as a Box Object the same \n"
              "object as in Film Object. It will create a thick\n"
              "black bar around the actual print allowing for a\n"
              "better delimitation of the outline features which are of\n"
              "white color like the rest and which may confound with the\n"
              "surroundings if not for this border.")
        )
        param_grid.addWidget(self.boundary_label, 8, 0)
        param_grid.addWidget(self.boundary_entry, 8, 1)

        self.boundary_label.hide()
        self.boundary_entry.hide()

        # Punch Drill holes
        self.punch_cb = FCCheckBox(_("Punch drill holes"))
        self.punch_cb.setToolTip(_("When checked the generated film will have holes in pads when\n"
                                   "the generated film is positive. This is done to help drilling,\n"
                                   "when done manually."))
        param_grid.addWidget(self.punch_cb, 10, 0, 1, 2)

        # this way I can hide/show the frame
        self.punch_frame = QtWidgets.QFrame()
        self.punch_frame.setContentsMargins(0, 0, 0, 0)
        param_grid.addWidget(self.punch_frame, 12, 0, 1, 2)

        punch_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        punch_grid.setContentsMargins(0, 0, 0, 0)
        self.punch_frame.setLayout(punch_grid)

        self.ois_p = OptionalHideInputSection(self.punch_cb, [self.punch_frame])

        self.source_label = FCLabel('%s:' % _("Source"))
        self.source_label.setToolTip(
            _("The punch hole source can be:\n"
              "- Excellon -> an Excellon holes center will serve as reference.\n"
              "- Pad Center -> will try to use the pads center as reference.")
        )
        self.source_punch = RadioSet([{'label': _('Excellon'), 'value': 'exc'},
                                      {'label': _('Pad center'), 'value': 'pad'}],
                                     compact=True)
        punch_grid.addWidget(self.source_label, 0, 0)
        punch_grid.addWidget(self.source_punch, 0, 1)

        self.exc_combo = FCComboBox()
        self.exc_combo.setToolTip(
            _("Remove the geometry of Excellon from the Film to create the holes in pads.")
        )
        self.exc_combo.setModel(self.app.collection)
        self.exc_combo.setRootModelIndex(self.app.collection.index(1, 0, QtCore.QModelIndex()))
        self.exc_combo.is_last = True
        self.exc_combo.obj_type = "Excellon"

        punch_grid.addWidget(self.exc_combo, 2, 0, 1, 2)

        self.exc_combo.hide()

        self.punch_size_label = FCLabel('%s:' % _("Punch Size"))
        self.punch_size_label.setToolTip(_("The value here will control how big is the punch hole in the pads."))
        self.punch_size_spinner = FCDoubleSpinner(callback=self.confirmation_message)
        self.punch_size_spinner.set_range(0, 999.9999)
        self.punch_size_spinner.setSingleStep(0.1)
        self.punch_size_spinner.set_precision(self.decimals)

        punch_grid.addWidget(self.punch_size_label, 4, 0)
        punch_grid.addWidget(self.punch_size_spinner, 4, 1)

        self.punch_size_label.hide()
        self.punch_size_spinner.hide()

        # #############################################################################################################
        # Export Frame
        # #############################################################################################################
        self.export_label = FCLabel('<span style="color:red;"><b>%s</b></span>' % _('Export'))
        self.tools_box.addWidget(self.export_label)

        exp_frame = FCFrame()
        self.tools_box.addWidget(exp_frame)

        export_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        exp_frame.setLayout(export_grid)

        self.file_type_label = FCLabel('%s:' % _("Film Type"))
        self.file_type_label.setToolTip(
            _("The file type of the saved film. Can be:\n"
              "- 'SVG' -> open-source vectorial format\n"
              "- 'PNG' -> raster image\n"
              "- 'PDF' -> portable document format")
        )

        # File type
        self.file_type_radio = RadioSet([{'label': _('SVG'), 'value': 'svg'},
                                         {'label': _('PNG'), 'value': 'png'},
                                         {'label': _('PDF'), 'value': 'pdf'}
                                         ], compact=True)

        export_grid.addWidget(self.file_type_label, 0, 0)
        export_grid.addWidget(self.file_type_radio, 0, 1)

        # Page orientation
        self.orientation_label = FCLabel('%s:' % _("Page Orientation"))
        self.orientation_label.setToolTip(_("Can be:\n"
                                            "- Portrait\n"
                                            "- Landscape"))

        self.orientation_radio = RadioSet([{'label': _('Portrait'), 'value': 'p'},
                                           {'label': _('Landscape'), 'value': 'l'},
                                           ], compact=True)

        # #############################################################################################################
        # ################################  New Grid ##################################################################
        # #############################################################################################################
        export_grid.addWidget(self.orientation_label, 2, 0)
        export_grid.addWidget(self.orientation_radio, 2, 1)

        # Page Size
        self.pagesize_label = FCLabel('%s:' % _("Page Size"))
        self.pagesize_label.setToolTip(_("A selection of standard ISO 216 page sizes."))

        self.pagesize_combo = FCComboBox()

        self.pagesize = {
            'Bounds': None,
            'A0': (841 * mm, 1189 * mm),
            'A1': (594 * mm, 841 * mm),
            'A2': (420 * mm, 594 * mm),
            'A3': (297 * mm, 420 * mm),
            'A4': (210 * mm, 297 * mm),
            'A5': (148 * mm, 210 * mm),
            'A6': (105 * mm, 148 * mm),
            'A7': (74 * mm, 105 * mm),
            'A8': (52 * mm, 74 * mm),
            'A9': (37 * mm, 52 * mm),
            'A10': (26 * mm, 37 * mm),

            'B0': (1000 * mm, 1414 * mm),
            'B1': (707 * mm, 1000 * mm),
            'B2': (500 * mm, 707 * mm),
            'B3': (353 * mm, 500 * mm),
            'B4': (250 * mm, 353 * mm),
            'B5': (176 * mm, 250 * mm),
            'B6': (125 * mm, 176 * mm),
            'B7': (88 * mm, 125 * mm),
            'B8': (62 * mm, 88 * mm),
            'B9': (44 * mm, 62 * mm),
            'B10': (31 * mm, 44 * mm),

            'C0': (917 * mm, 1297 * mm),
            'C1': (648 * mm, 917 * mm),
            'C2': (458 * mm, 648 * mm),
            'C3': (324 * mm, 458 * mm),
            'C4': (229 * mm, 324 * mm),
            'C5': (162 * mm, 229 * mm),
            'C6': (114 * mm, 162 * mm),
            'C7': (81 * mm, 114 * mm),
            'C8': (57 * mm, 81 * mm),
            'C9': (40 * mm, 57 * mm),
            'C10': (28 * mm, 40 * mm),

            # American paper sizes
            'LETTER': (8.5 * inch, 11 * inch),
            'LEGAL': (8.5 * inch, 14 * inch),
            'ELEVENSEVENTEEN': (11 * inch, 17 * inch),

            # From https://en.wikipedia.org/wiki/Paper_size
            'JUNIOR_LEGAL': (5 * inch, 8 * inch),
            'HALF_LETTER': (5.5 * inch, 8 * inch),
            'GOV_LETTER': (8 * inch, 10.5 * inch),
            'GOV_LEGAL': (8.5 * inch, 13 * inch),
            'LEDGER': (17 * inch, 11 * inch),
        }

        page_size_list = list(self.pagesize.keys())
        self.pagesize_combo.addItems(page_size_list)

        export_grid.addWidget(self.pagesize_label, 4, 0)
        export_grid.addWidget(self.pagesize_combo, 4, 1)

        self.on_film_type(val='hide')

        # PNG DPI
        self.png_dpi_label = FCLabel('%s:' % "PNG DPI")
        self.png_dpi_label.setToolTip(
            _("Default value is 96 DPI. Change this value to scale the PNG file.")
        )
        self.png_dpi_spinner = FCSpinner(callback=self.confirmation_message_int)
        self.png_dpi_spinner.set_range(0, 100000)

        export_grid.addWidget(self.png_dpi_label, 6, 0)
        export_grid.addWidget(self.png_dpi_spinner, 6, 1)

        self.png_dpi_label.hide()
        self.png_dpi_spinner.hide()

        FCGridLayout.set_common_column_size([adj_grid, param_grid, obj_grid, export_grid, punch_grid], 0)

        # Buttons
        self.film_object_button = FCButton(_("Save Film"))
        self.film_object_button.setIcon(QtGui.QIcon(self.app.resource_location + '/save_as.png'))
        self.film_object_button.setToolTip(
            _("Create a Film for the selected object, within\n"
              "the specified box. Does not create a new \n "
              "FlatCAM object, but directly save it in the\n"
              "selected format.")
        )
        self.film_object_button.setStyleSheet("""
                               QPushButton
                               {
                                   font-weight: bold;
                               }
                               """)
        self.tools_box.addWidget(self.film_object_button)

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

    def on_film_type(self, val):
        type_of_film = val

        if type_of_film == 'neg':
            self.boundary_label.show()
            self.boundary_entry.show()
            self.punch_cb.set_value(False)  # required so the self.punch_frame it's hidden also by the signal emitted
            self.punch_cb.hide()
        else:
            self.boundary_label.hide()
            self.boundary_entry.hide()
            self.punch_cb.show()

    def on_file_type(self, val):
        if val == 'pdf':
            self.orientation_label.show()
            self.orientation_radio.show()
            self.pagesize_label.show()
            self.pagesize_combo.show()
            self.png_dpi_label.hide()
            self.png_dpi_spinner.hide()
        elif val == 'png':
            self.png_dpi_label.show()
            self.png_dpi_spinner.show()
            self.orientation_label.hide()
            self.orientation_radio.hide()
            self.pagesize_label.hide()
            self.pagesize_combo.hide()
        else:
            self.orientation_label.hide()
            self.orientation_radio.hide()
            self.pagesize_label.hide()
            self.pagesize_combo.hide()
            self.png_dpi_label.hide()
            self.png_dpi_spinner.hide()

    def on_punch_source(self, val):
        if val == 'pad' and self.punch_cb.get_value():
            self.punch_size_label.show()
            self.punch_size_spinner.show()
            self.exc_combo.hide()
        else:
            self.punch_size_label.hide()
            self.punch_size_spinner.hide()
            self.exc_combo.show()

        if val == 'pad' and self.tf_type_obj_combo.get_value() == 'geo':
            self.source_punch.set_value('exc')
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Using the Pad center does not work on Geometry objects. "
                                                          "Only a Gerber object has pads."))

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
