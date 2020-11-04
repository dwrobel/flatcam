# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtCore, QtWidgets, QtGui

from appTool import AppTool
from appGUI.GUIElements import RadioSet, FCDoubleSpinner, FCCheckBox, \
    OptionalHideInputSection, FCComboBox, FCFileSaveDialog, FCButton, FCLabel, FCSpinner

from copy import deepcopy
import logging
from shapely.geometry import Polygon, MultiPolygon, Point
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
        self.units = self.app.defaults['units']

        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = FilmUI(layout=self.layout, app=self.app)
        self.toolName = self.ui.toolName

        # ## Signals
        self.ui.film_object_button.clicked.connect(self.on_film_creation)
        self.ui.tf_type_obj_combo.activated_custom.connect(self.on_type_obj_index_changed)
        self.ui.tf_type_box_combo.activated_custom.connect(self.on_type_box_index_changed)

        self.ui.film_type.activated_custom.connect(self.ui.on_film_type)
        self.ui.source_punch.activated_custom.connect(self.ui.on_punch_source)
        self.ui.file_type_radio.activated_custom.connect(self.ui.on_file_type)
        self.ui.reset_button.clicked.connect(self.set_tool_ui)

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

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolFilm()")

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

        self.app.ui.notebook.setTabText(2, _("Film Tool"))

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Alt+L', **kwargs)

    def set_tool_ui(self):
        self.reset_fields()

        f_type = self.app.defaults["tools_film_type"] if self.app.defaults["tools_film_type"] else 'neg'
        self.ui.film_type.set_value(str(f_type))
        self.ui.on_film_type(val=f_type)

        b_entry = self.app.defaults["tools_film_boundary"] if self.app.defaults["tools_film_boundary"] else 0.0
        self.ui.boundary_entry.set_value(float(b_entry))

        scale_stroke_width = self.app.defaults["tools_film_scale_stroke"] if \
            self.app.defaults["tools_film_scale_stroke"] else 0.0
        self.ui.film_scale_stroke_entry.set_value(int(scale_stroke_width))

        self.ui.punch_cb.set_value(False)
        self.ui.source_punch.set_value('exc')

        self.ui.film_scale_cb.set_value(self.app.defaults["tools_film_scale_cb"])
        self.ui.film_scalex_entry.set_value(float(self.app.defaults["tools_film_scale_x_entry"]))
        self.ui.film_scaley_entry.set_value(float(self.app.defaults["tools_film_scale_y_entry"]))
        self.ui.film_skew_cb.set_value(self.app.defaults["tools_film_skew_cb"])
        self.ui.film_skewx_entry.set_value(float(self.app.defaults["tools_film_skew_x_entry"]))
        self.ui.film_skewy_entry.set_value(float(self.app.defaults["tools_film_skew_y_entry"]))
        self.ui.film_skew_reference.set_value(self.app.defaults["tools_film_skew_ref_radio"])
        self.ui.film_mirror_cb.set_value(self.app.defaults["tools_film_mirror_cb"])
        self.ui.film_mirror_axis.set_value(self.app.defaults["tools_film_mirror_axis_radio"])
        self.ui.file_type_radio.set_value(self.app.defaults["tools_film_file_type_radio"])
        self.ui.orientation_radio.set_value(self.app.defaults["tools_film_orientation"])
        self.ui.pagesize_combo.set_value(self.app.defaults["tools_film_pagesize"])

        self.ui.png_dpi_spinner.set_value(self.app.defaults["tools_film_png_dpi"])

        self.ui.tf_type_obj_combo.set_value('grb')
        self.ui.tf_type_box_combo.set_value('grb')
        # run once to update the obj_type attribute in the FCCombobox so the last object is showed in cb
        self.on_type_obj_index_changed(val='grb')
        self.on_type_box_index_changed(val='grb')

    def on_film_creation(self):
        log.debug("ToolFilm.Film.on_film_creation() started ...")

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
        log.debug("ToolFilm.Film.generate_positive_normal_film() started ...")

        scale_factor_x = 1
        scale_factor_y = 1
        skew_factor_x = None
        skew_factor_y = None
        mirror = None
        skew_reference = 'center'

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

            skew_reference = self.ui.film_skew_reference.get_value()
        if self.ui.film_mirror_cb.get_value():
            if self.ui.film_mirror_axis.get_value() != 'none':
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

        if str(filename) == "":
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
            return
        else:
            pagesize = self.ui.pagesize_combo.get_value()
            orientation = self.ui.orientation_radio.get_value()
            color = self.app.defaults['tools_film_color']

            self.export_positive(name, boxname, filename,
                                 scale_stroke_factor=factor,
                                 scale_factor_x=scale_factor_x, scale_factor_y=scale_factor_y,
                                 skew_factor_x=skew_factor_x, skew_factor_y=skew_factor_y,
                                 skew_reference=skew_reference,
                                 mirror=mirror,
                                 pagesize_val=pagesize, orientation_val=orientation, color_val=color, opacity_val=1.0,
                                 ftype=ftype
                                 )

    def generate_positive_punched_film(self, name, boxname, source, factor, ftype='svg'):

        film_obj = self.app.collection.get_by_name(name)

        if source == 'exc':
            log.debug("ToolFilm.Film.generate_positive_punched_film() with Excellon source started ...")

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
            log.debug("ToolFilm.Film.generate_positive_punched_film() with Pad center source started ...")

            punch_size = float(self.ui.punch_size_spinner.get_value())

            punching_geo = []
            for apid in film_obj.apertures:
                if film_obj.apertures[apid]['type'] == 'C':
                    if punch_size >= float(film_obj.apertures[apid]['size']):
                        self.app.inform.emit('[ERROR_NOTCL] %s' %
                                             _("Failed. Punch hole size "
                                               "is bigger than some of the apertures in the Gerber object."))
                        return 'fail'
                    else:
                        for elem in film_obj.apertures[apid]['geometry']:
                            if 'follow' in elem:
                                if isinstance(elem['follow'], Point):
                                    punching_geo.append(elem['follow'].buffer(punch_size / 2))
                else:
                    if punch_size >= float(film_obj.apertures[apid]['width']) or \
                            punch_size >= float(film_obj.apertures[apid]['height']):
                        self.app.inform.emit('[ERROR_NOTCL] %s' %
                                             _("Failed. Punch hole size "
                                               "is bigger than some of the apertures in the Gerber object."))
                        return 'fail'
                    else:
                        for elem in film_obj.apertures[apid]['geometry']:
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
        log.debug("ToolFilm.Film.generate_negative_film() started ...")

        scale_factor_x = 1
        scale_factor_y = 1
        skew_factor_x = None
        skew_factor_y = None
        mirror = None
        skew_reference = 'center'

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

            skew_reference = self.ui.film_skew_reference.get_value()
        if self.ui.film_mirror_cb.get_value():
            if self.ui.film_mirror_axis.get_value() != 'none':
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
            self.export_negative(name, boxname, filename, border,
                                 scale_stroke_factor=factor,
                                 scale_factor_x=scale_factor_x, scale_factor_y=scale_factor_y,
                                 skew_factor_x=skew_factor_x, skew_factor_y=skew_factor_y,
                                 skew_reference=skew_reference,
                                 mirror=mirror, ftype=ftype
                                 )

    def export_negative(self, obj_name, box_name, filename, boundary,
                        scale_stroke_factor=0.00,
                        scale_factor_x=1, scale_factor_y=1,
                        skew_factor_x=None, skew_factor_y=None, skew_reference='center',
                        mirror=None,
                        use_thread=True, ftype='svg'):
        """
        Exports a Geometry Object to an SVG file in negative.

        :param obj_name: the name of the FlatCAM object to be saved as SVG
        :param box_name: the name of the FlatCAM object to be used as delimitation of the content to be saved
        :param filename: Path to the SVG file to save to.
        :param boundary: thickness of a black border to surround all the features
        :param scale_stroke_factor: factor by which to change/scale the thickness of the features
        :param scale_factor_x: factor to scale the svg geometry on the X axis
        :param scale_factor_y: factor to scale the svg geometry on the Y axis
        :param skew_factor_x: factor to skew the svg geometry on the X axis
        :param skew_factor_y: factor to skew the svg geometry on the Y axis
        :param skew_reference: reference to use for skew. Can be 'bottomleft', 'bottomright', 'topleft', 'topright' and
        those are the 4 points of the bounding box of the geometry to be skewed.
        :param mirror: can be 'x' or 'y' or 'both'. Axis on which to mirror the svg geometry
        :param use_thread: if to be run in a separate thread; boolean
        :param ftype: the type of file for saving the film: 'svg', 'png' or 'pdf'
        :return:
        """
        self.app.defaults.report_usage("export_negative()")

        if filename is None:
            filename = self.app.defaults["global_last_save_folder"]

        self.app.log.debug("export_svg() negative")

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

        def make_negative_film(scale_factor_x, scale_factor_y):
            log.debug("FilmTool.export_negative().make_negative_film()")

            scale_reference = 'center'

            self.screen_dpi = self.app.qapp.screens()[0].logicalDotsPerInch()

            new_png_dpi = self.ui.png_dpi_spinner.get_value()
            dpi_rate = new_png_dpi / self.screen_dpi
            # Determine bounding area for svg export
            bounds = box.bounds()
            tr_scale_reference = (bounds[0], bounds[1])

            if dpi_rate != 1 and ftype == 'png':
                scale_factor_x += dpi_rate
                scale_factor_y += dpi_rate
                scale_reference = (bounds[0], bounds[1])

            if box.kind.lower() == 'geometry':
                flat_geo = []
                if box.multigeo:
                    for tool in box.tools:
                        flat_geo += box.flatten(box.tools[tool]['solid_geometry'])
                    box_geo = unary_union(flat_geo)
                else:
                    box_geo = unary_union(box.flatten())
            else:
                box_geo = unary_union(box.flatten())

            skew_ref = 'center'
            if skew_reference != 'center':
                xmin, ymin, xmax, ymax = box_geo.bounds
                if skew_reference == 'topleft':
                    skew_ref = (xmin, ymax)
                elif skew_reference == 'bottomleft':
                    skew_ref = (xmin, ymin)
                elif skew_reference == 'topright':
                    skew_ref = (xmax, ymax)
                elif skew_reference == 'bottomright':
                    skew_ref = (xmax, ymin)

            transformed_box_geo = box_geo

            if scale_factor_x and not scale_factor_y:
                transformed_box_geo = affinity.scale(transformed_box_geo, scale_factor_x, 1.0,
                                                     origin=tr_scale_reference)
            elif not scale_factor_x and scale_factor_y:
                transformed_box_geo = affinity.scale(transformed_box_geo, 1.0, scale_factor_y,
                                                     origin=tr_scale_reference)
            elif scale_factor_x and scale_factor_y:
                transformed_box_geo = affinity.scale(transformed_box_geo, scale_factor_x, scale_factor_y,
                                                     origin=tr_scale_reference)

            if skew_factor_x and not skew_factor_y:
                transformed_box_geo = affinity.skew(transformed_box_geo, skew_factor_x, 0.0, origin=skew_ref)
            elif not skew_factor_x and skew_factor_y:
                transformed_box_geo = affinity.skew(transformed_box_geo, 0.0, skew_factor_y, origin=skew_ref)
            elif skew_factor_x and skew_factor_y:
                transformed_box_geo = affinity.skew(transformed_box_geo, skew_factor_x, skew_factor_y, origin=skew_ref)

            if mirror:
                if mirror == 'x':
                    transformed_box_geo = affinity.scale(transformed_box_geo, 1.0, -1.0)
                if mirror == 'y':
                    transformed_box_geo = affinity.scale(transformed_box_geo, -1.0, 1.0)
                if mirror == 'both':
                    transformed_box_geo = affinity.scale(transformed_box_geo, -1.0, -1.0)

            bounds = transformed_box_geo.bounds
            size = bounds[2] - bounds[0], bounds[3] - bounds[1]

            exported_svg = obj.export_svg(scale_stroke_factor=scale_stroke_factor,
                                          scale_factor_x=scale_factor_x, scale_factor_y=scale_factor_y,
                                          skew_factor_x=skew_factor_x, skew_factor_y=skew_factor_y,
                                          mirror=mirror,
                                          scale_reference=scale_reference, skew_reference=skew_reference
                                          )

            uom = obj.units.lower()

            # Convert everything to strings for use in the xml doc
            svgwidth = str(size[0] + (2 * boundary))
            svgheight = str(size[1] + (2 * boundary))
            minx = str(bounds[0] - boundary)
            miny = str(bounds[1] + boundary + size[1])
            miny_rect = str(bounds[1] - boundary)

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

            # Change the attributes of the exported SVG
            # We don't need stroke-width - wrong, we do when we have lines with certain width
            # We set opacity to maximum
            # We set the color to WHITE
            root = ET.fromstring(exported_svg)
            for child in root:
                child.set('fill', '#FFFFFF')
                child.set('opacity', '1.0')
                child.set('stroke', '#FFFFFF')

            # first_svg_elem = 'rect x="' + minx + '" ' + 'y="' + miny_rect + '" '
            # first_svg_elem += 'width="' + svgwidth + '" ' + 'height="' + svgheight + '" '
            # first_svg_elem += 'fill="#000000" opacity="1.0" stroke-width="0.0"'

            first_svg_elem_tag = 'rect'
            first_svg_elem_attribs = {
                'x': minx,
                'y': miny_rect,
                'width': svgwidth,
                'height': svgheight,
                'id': 'neg_rect',
                'style': 'fill:#000000;opacity:1.0;stroke-width:0.0'
            }

            root.insert(0, ET.Element(first_svg_elem_tag, first_svg_elem_attribs))
            exported_svg = ET.tostring(root)

            svg_elem = svg_header + str(exported_svg) + svg_footer

            # Parse the xml through a xml parser just to add line feeds
            # and to make it look more pretty for the output
            doc = parse_xml_string(svg_elem)
            doc_final = doc.toprettyxml()

            if ftype == 'svg':
                try:
                    with open(filename, 'w') as fp:
                        fp.write(doc_final)
                except PermissionError:
                    self.app.inform.emit('[WARNING] %s' %
                                         _("Permission denied, saving not possible.\n"
                                           "Most likely another app is holding the file open and not accessible."))
                    return 'fail'
            elif ftype == 'png':
                try:
                    doc_final = StringIO(doc_final)
                    drawing = svg2rlg(doc_final)
                    renderPM.drawToFile(drawing, filename, 'PNG')

                    # if new_png_dpi == default_dpi:
                    #     renderPM.drawToFile(drawing, filename, 'PNG')
                    # else:
                    #     renderPM.drawToFile(drawing, filename, 'PNG', dpi=new_png_dpi)
                except Exception as e:
                    log.debug("FilmTool.export_negative() --> PNG output --> %s" % str(e))
                    return 'fail'
            else:
                try:
                    if self.units == 'INCH':
                        unit = inch
                    else:
                        unit = mm

                    doc_final = StringIO(doc_final)
                    drawing = svg2rlg(doc_final)

                    p_size = self.ui.pagesize_combo.get_value()
                    if p_size == 'Bounds':
                        renderPDF.drawToFile(drawing, filename)
                    else:
                        if self.ui.orientation_radio.get_value() == 'p':
                            page_size = portrait(self.ui.pagesize[p_size])
                        else:
                            page_size = landscape(self.ui.pagesize[p_size])

                        my_canvas = canvas.Canvas(filename, pagesize=page_size)
                        my_canvas.translate(bounds[0] * unit, bounds[1] * unit)
                        renderPDF.draw(drawing, my_canvas, 0, 0)
                        my_canvas.save()
                except Exception as e:
                    log.debug("FilmTool.export_negative() --> PDF output --> %s" % str(e))
                    return 'fail'

            if self.app.defaults["global_open_style"] is False:
                self.app.file_opened.emit("SVG", filename)
            self.app.file_saved.emit("SVG", filename)
            self.app.inform.emit('[success] %s: %s' % (_("Film file exported to"), filename))

        if use_thread is True:
            def job_thread_film():
                with self.app.proc_container.new(_("Working...")):
                    try:
                        make_negative_film(scale_factor_x=scale_factor_x, scale_factor_y=scale_factor_y)
                    except Exception as e:
                        log.debug("export_negative() process -> %s" % str(e))
                        return

            self.app.worker_task.emit({'fcn': job_thread_film, 'params': []})
        else:
            make_negative_film(scale_factor_x=scale_factor_x, scale_factor_y=scale_factor_y)

    def export_positive(self, obj_name, box_name, filename,
                        scale_stroke_factor=0.00,
                        scale_factor_x=1, scale_factor_y=1,
                        skew_factor_x=None, skew_factor_y=None, skew_reference='center',
                        mirror=None,  orientation_val='p', pagesize_val='A4', color_val='black', opacity_val=1.0,
                        use_thread=True, ftype='svg'):

        """
        Exports a Geometry Object to an SVG file in positive black.

        :param obj_name:            the name of the FlatCAM object to be saved
        :param box_name:            the name of the FlatCAM object to be used as delimitation of the content to be saved
        :param filename:            Path to the file to save to.
        :param scale_stroke_factor: factor by which to change/scale the thickness of the features
        :param scale_factor_x:      factor to scale the geometry on the X axis
        :param scale_factor_y:      factor to scale the geometry on the Y axis
        :param skew_factor_x:       factor to skew the geometry on the X axis
        :param skew_factor_y:       factor to skew the geometry on the Y axis
        :param skew_reference:      reference to use for skew. Can be 'bottomleft', 'bottomright', 'topleft',
        'topright' and those are the 4 points of the bounding box of the geometry to be skewed.
        :param mirror:              can be 'x' or 'y' or 'both'. Axis on which to mirror the svg geometry
        :param orientation_val:
        :param pagesize_val:
        :param color_val:
        :param opacity_val:
        :param use_thread:          if to be run in a separate thread; boolean
        :param ftype:               the type of file for saving the film: 'svg', 'png' or 'pdf'

        :return:
        """
        self.app.defaults.report_usage("export_positive()")

        if filename is None:
            filename = self.app.defaults["global_last_save_folder"]

        self.app.log.debug("export_svg() black")

        try:
            obj = self.app.collection.get_by_name(str(obj_name))
        except Exception:
            return "Could not retrieve object: %s" % obj_name

        try:
            box = self.app.collection.get_by_name(str(box_name))
        except Exception:
            return "Could not retrieve object: %s" % box_name

        if box is None:
            self.inform.emit('[WARNING_NOTCL] %s: %s' % (_("No object Box. Using instead"), obj))
            box = obj

        scale_factor_x = scale_factor_x
        scale_factor_y = scale_factor_y

        p_size = pagesize_val
        orientation = orientation_val
        color = color_val
        transparency_level = opacity_val

        def make_positive_film(p_size, orientation, color, transparency_level, scale_factor_x, scale_factor_y):
            log.debug("FilmTool.export_positive().make_positive_film()")

            scale_reference = 'center'

            self.screen_dpi = self.app.qapp.screens()[0].logicalDotsPerInch()

            new_png_dpi = self.ui.png_dpi_spinner.get_value()
            dpi_rate = new_png_dpi / self.screen_dpi
            # Determine bounding area for svg export
            bounds = box.bounds()
            tr_scale_reference = (bounds[0], bounds[1])

            if dpi_rate != 1 and ftype == 'png':
                scale_factor_x += dpi_rate
                scale_factor_y += dpi_rate
                scale_reference = (bounds[0], bounds[1])

            if box.kind.lower() == 'geometry':
                flat_geo = []
                if box.multigeo:
                    for tool in box.tools:
                        flat_geo += box.flatten(box.tools[tool]['solid_geometry'])
                    box_geo = unary_union(flat_geo)
                else:
                    box_geo = unary_union(box.flatten())
            else:
                box_geo = unary_union(box.flatten())

            skew_ref = 'center'
            if skew_reference != 'center':
                xmin, ymin, xmax, ymax = box_geo.bounds
                if skew_reference == 'topleft':
                    skew_ref = (xmin, ymax)
                elif skew_reference == 'bottomleft':
                    skew_ref = (xmin, ymin)
                elif skew_reference == 'topright':
                    skew_ref = (xmax, ymax)
                elif skew_reference == 'bottomright':
                    skew_ref = (xmax, ymin)

            transformed_box_geo = box_geo

            if scale_factor_x and not scale_factor_y:
                transformed_box_geo = affinity.scale(transformed_box_geo, scale_factor_x, 1.0,
                                                     origin=tr_scale_reference)
            elif not scale_factor_x and scale_factor_y:
                transformed_box_geo = affinity.scale(transformed_box_geo, 1.0, scale_factor_y,
                                                     origin=tr_scale_reference)
            elif scale_factor_x and scale_factor_y:
                transformed_box_geo = affinity.scale(transformed_box_geo, scale_factor_x, scale_factor_y,
                                                     origin=tr_scale_reference)

            if skew_factor_x and not skew_factor_y:
                transformed_box_geo = affinity.skew(transformed_box_geo, skew_factor_x, 0.0, origin=skew_ref)
            elif not skew_factor_x and skew_factor_y:
                transformed_box_geo = affinity.skew(transformed_box_geo, 0.0, skew_factor_y, origin=skew_ref)
            elif skew_factor_x and skew_factor_y:
                transformed_box_geo = affinity.skew(transformed_box_geo, skew_factor_x, skew_factor_y, origin=skew_ref)

            if mirror:
                if mirror == 'x':
                    transformed_box_geo = affinity.scale(transformed_box_geo, 1.0, -1.0)
                if mirror == 'y':
                    transformed_box_geo = affinity.scale(transformed_box_geo, -1.0, 1.0)
                if mirror == 'both':
                    transformed_box_geo = affinity.scale(transformed_box_geo, -1.0, -1.0)

            bounds = transformed_box_geo.bounds
            size = bounds[2] - bounds[0], bounds[3] - bounds[1]

            exported_svg = obj.export_svg(scale_stroke_factor=scale_stroke_factor,
                                          scale_factor_x=scale_factor_x, scale_factor_y=scale_factor_y,
                                          skew_factor_x=skew_factor_x, skew_factor_y=skew_factor_y,
                                          mirror=mirror,
                                          scale_reference=scale_reference, skew_reference=skew_reference
                                          )

            # Change the attributes of the exported SVG
            # We don't need stroke-width
            # We set opacity to maximum
            # We set the colour to WHITE
            root = ET.fromstring(exported_svg)
            for child in root:
                child.set('fill', str(color))
                child.set('opacity', str(transparency_level))
                child.set('stroke', str(color))

            exported_svg = ET.tostring(root)

            # This contain the measure units
            uom = obj.units.lower()

            # Define a boundary around SVG of about 1.0mm (~39mils)
            if uom in "mm":
                boundary = 1.0
            else:
                boundary = 0.0393701

            # Convert everything to strings for use in the xml doc
            svgwidth = str(size[0] + (2 * boundary))
            svgheight = str(size[1] + (2 * boundary))
            minx = str(bounds[0] - boundary)
            miny = str(bounds[1] + boundary + size[1])

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
            doc_final = doc.toprettyxml()

            if ftype == 'svg':
                try:
                    with open(filename, 'w') as fp:
                        fp.write(doc_final)
                except PermissionError:
                    self.app.inform.emit('[WARNING] %s' %
                                         _("Permission denied, saving not possible.\n"
                                           "Most likely another app is holding the file open and not accessible."))
                    return 'fail'
            elif ftype == 'png':
                try:
                    doc_final = StringIO(doc_final)
                    drawing = svg2rlg(doc_final)
                    renderPM.drawToFile(drawing, filename, 'PNG')
                except Exception as e:
                    log.debug("FilmTool.export_positive() --> PNG output --> %s" % str(e))
                    return 'fail'
            else:
                try:
                    if self.units == 'IN':
                        unit = inch
                    else:
                        unit = mm

                    doc_final = StringIO(doc_final)
                    drawing = svg2rlg(doc_final)

                    if p_size == 'Bounds':
                        renderPDF.drawToFile(drawing, filename)
                    else:
                        if orientation == 'p':
                            page_size = portrait(self.ui.pagesize[p_size])
                        else:
                            page_size = landscape(self.ui.pagesize[p_size])

                        my_canvas = canvas.Canvas(filename, pagesize=page_size)
                        my_canvas.translate(bounds[0] * unit, bounds[1] * unit)
                        renderPDF.draw(drawing, my_canvas, 0, 0)
                        my_canvas.save()
                except Exception as e:
                    log.debug("FilmTool.export_positive() --> PDF output --> %s" % str(e))
                    return 'fail'

            if self.app.defaults["global_open_style"] is False:
                self.app.file_opened.emit("SVG", filename)
            self.app.file_saved.emit("SVG", filename)
            self.app.inform.emit('[success] %s: %s' % (_("Film file exported to"), filename))

        if use_thread is True:
            def job_thread_film():
                with self.app.proc_container.new(_("Working...")):
                    try:
                        make_positive_film(p_size=p_size, orientation=orientation, color=color,
                                           transparency_level=transparency_level,
                                           scale_factor_x=scale_factor_x, scale_factor_y=scale_factor_y)
                    except Exception as e:
                        log.debug("export_positive() process -> %s" % str(e))
                        return

            self.app.worker_task.emit({'fcn': job_thread_film, 'params': []})
        else:
            make_positive_film(p_size=p_size, orientation=orientation, color=color,
                               transparency_level=transparency_level,
                               scale_factor_x=scale_factor_x, scale_factor_y=scale_factor_y)

    def reset_fields(self):
        self.ui.tf_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.ui.tf_box_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))


class FilmUI:

    toolName = _("Film PCB")

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

        # Form Layout
        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)

        # Type of object for which to create the film
        self.tf_type_obj_combo = RadioSet([{'label': _('Gerber'), 'value': 'grb'},
                                           {'label': _('Geometry'), 'value': 'geo'}])

        self.tf_type_obj_combo_label = FCLabel('<b>%s</b>:' % _("Object"))
        self.tf_type_obj_combo_label.setToolTip(
            _("Specify the type of object for which to create the film.\n"
              "The object can be of type: Gerber or Geometry.\n"
              "The selection here decide the type of objects that will be\n"
              "in the Film Object combobox.")
        )
        grid0.addWidget(self.tf_type_obj_combo_label, 0, 0)
        grid0.addWidget(self.tf_type_obj_combo, 0, 1)

        # List of objects for which we can create the film
        self.tf_object_combo = FCComboBox()
        self.tf_object_combo.setModel(self.app.collection)
        self.tf_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.tf_object_combo.is_last = True

        grid0.addWidget(self.tf_object_combo, 1, 0, 1, 2)

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
        grid0.addWidget(self.tf_type_box_combo_label, 2, 0)
        grid0.addWidget(self.tf_type_box_combo, 2, 1)

        # Box
        self.tf_box_combo = FCComboBox()
        self.tf_box_combo.setModel(self.app.collection)
        self.tf_box_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.tf_box_combo.is_last = True

        grid0.addWidget(self.tf_box_combo, 3, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 4, 0, 1, 2)

        self.film_adj_label = FCLabel('<b>%s</b>' % _("Film Adjustments"))
        self.film_adj_label.setToolTip(
            _("Sometime the printers will distort the print shape, especially the Laser types.\n"
              "This section provide the tools to compensate for the print distortions.")
        )

        grid0.addWidget(self.film_adj_label, 5, 0, 1, 2)

        # Scale Geometry
        self.film_scale_cb = FCCheckBox('%s' % _("Scale Film geometry"))
        self.film_scale_cb.setToolTip(
            _("A value greater than 1 will stretch the film\n"
              "while a value less than 1 will jolt it.")
        )
        self.film_scale_cb.setStyleSheet(
            """
            QCheckBox {font-weight: bold; color: black}
            """
        )
        grid0.addWidget(self.film_scale_cb, 6, 0, 1, 2)

        self.film_scalex_label = FCLabel('%s:' % _("X factor"))
        self.film_scalex_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.film_scalex_entry.set_range(-999.9999, 999.9999)
        self.film_scalex_entry.set_precision(self.decimals)
        self.film_scalex_entry.setSingleStep(0.01)

        grid0.addWidget(self.film_scalex_label, 7, 0)
        grid0.addWidget(self.film_scalex_entry, 7, 1)

        self.film_scaley_label = FCLabel('%s:' % _("Y factor"))
        self.film_scaley_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.film_scaley_entry.set_range(-999.9999, 999.9999)
        self.film_scaley_entry.set_precision(self.decimals)
        self.film_scaley_entry.setSingleStep(0.01)

        grid0.addWidget(self.film_scaley_label, 8, 0)
        grid0.addWidget(self.film_scaley_entry, 8, 1)

        self.ois_scale = OptionalHideInputSection(self.film_scale_cb,
                                                  [
                                                      self.film_scalex_label,
                                                      self.film_scalex_entry,
                                                      self.film_scaley_label,
                                                      self.film_scaley_entry
                                                  ])

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 9, 0, 1, 2)

        # Skew Geometry
        self.film_skew_cb = FCCheckBox('%s' % _("Skew Film geometry"))
        self.film_skew_cb.setToolTip(
            _("Positive values will skew to the right\n"
              "while negative values will skew to the left.")
        )
        self.film_skew_cb.setStyleSheet(
            """
            QCheckBox {font-weight: bold; color: black}
            """
        )
        grid0.addWidget(self.film_skew_cb, 10, 0, 1, 2)

        self.film_skewx_label = FCLabel('%s:' % _("X angle"))
        self.film_skewx_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.film_skewx_entry.set_range(-999.9999, 999.9999)
        self.film_skewx_entry.set_precision(self.decimals)
        self.film_skewx_entry.setSingleStep(0.01)

        grid0.addWidget(self.film_skewx_label, 11, 0)
        grid0.addWidget(self.film_skewx_entry, 11, 1)

        self.film_skewy_label = FCLabel('%s:' % _("Y angle"))
        self.film_skewy_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.film_skewy_entry.set_range(-999.9999, 999.9999)
        self.film_skewy_entry.set_precision(self.decimals)
        self.film_skewy_entry.setSingleStep(0.01)

        grid0.addWidget(self.film_skewy_label, 12, 0)
        grid0.addWidget(self.film_skewy_entry, 12, 1)

        self.film_skew_ref_label = FCLabel('%s:' % _("Reference"))
        self.film_skew_ref_label.setToolTip(
            _("The reference point to be used as origin for the skew.\n"
              "It can be one of the four points of the geometry bounding box.")
        )
        self.film_skew_reference = RadioSet([{'label': _('Bottom Left'), 'value': 'bottomleft'},
                                             {'label': _('Top Left'), 'value': 'topleft'},
                                             {'label': _('Bottom Right'), 'value': 'bottomright'},
                                             {'label': _('Top right'), 'value': 'topright'}],
                                            orientation='vertical',
                                            stretch=False)

        grid0.addWidget(self.film_skew_ref_label, 13, 0)
        grid0.addWidget(self.film_skew_reference, 13, 1)

        self.ois_skew = OptionalHideInputSection(self.film_skew_cb,
                                                 [
                                                     self.film_skewx_label,
                                                     self.film_skewx_entry,
                                                     self.film_skewy_label,
                                                     self.film_skewy_entry,
                                                     self.film_skew_ref_label,
                                                     self.film_skew_reference
                                                 ])

        separator_line1 = QtWidgets.QFrame()
        separator_line1.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line1.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line1, 14, 0, 1, 2)

        # Mirror Geometry
        self.film_mirror_cb = FCCheckBox('%s' % _("Mirror Film geometry"))
        self.film_mirror_cb.setToolTip(
            _("Mirror the film geometry on the selected axis or on both.")
        )
        self.film_mirror_cb.setStyleSheet(
            """
            QCheckBox {font-weight: bold; color: black}
            """
        )
        grid0.addWidget(self.film_mirror_cb, 15, 0, 1, 2)

        self.film_mirror_axis = RadioSet([{'label': _('None'), 'value': 'none'},
                                          {'label': _('X'), 'value': 'x'},
                                          {'label': _('Y'), 'value': 'y'},
                                          {'label': _('Both'), 'value': 'both'}],
                                         stretch=False)
        self.film_mirror_axis_label = FCLabel('%s:' % _("Mirror Axis"))

        grid0.addWidget(self.film_mirror_axis_label, 16, 0)
        grid0.addWidget(self.film_mirror_axis, 16, 1)

        self.ois_mirror = OptionalHideInputSection(self.film_mirror_cb,
                                                   [
                                                       self.film_mirror_axis_label,
                                                       self.film_mirror_axis
                                                   ])

        separator_line2 = QtWidgets.QFrame()
        separator_line2.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line2.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line2, 17, 0, 1, 2)

        self.film_param_label = FCLabel('<b>%s</b>' % _("Film Parameters"))

        grid0.addWidget(self.film_param_label, 18, 0, 1, 2)

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
        grid0.addWidget(self.film_scale_stroke_label, 19, 0)
        grid0.addWidget(self.film_scale_stroke_entry, 19, 1)

        # Film Type
        self.film_type = RadioSet([{'label': _('Positive'), 'value': 'pos'},
                                   {'label': _('Negative'), 'value': 'neg'}],
                                  stretch=False)
        self.film_type_label = FCLabel('%s:' % _("Film Type"))
        self.film_type_label.setToolTip(
            _("Generate a Positive black film or a Negative film.\n"
              "Positive means that it will print the features\n"
              "with black on a white canvas.\n"
              "Negative means that it will print the features\n"
              "with white on a black canvas.\n"
              "The Film format is SVG.")
        )
        grid0.addWidget(self.film_type_label, 21, 0)
        grid0.addWidget(self.film_type, 21, 1)

        # Boundary for negative film generation
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
        grid0.addWidget(self.boundary_label, 22, 0)
        grid0.addWidget(self.boundary_entry, 22, 1)

        self.boundary_label.hide()
        self.boundary_entry.hide()

        # Punch Drill holes
        self.punch_cb = FCCheckBox(_("Punch drill holes"))
        self.punch_cb.setToolTip(_("When checked the generated film will have holes in pads when\n"
                                   "the generated film is positive. This is done to help drilling,\n"
                                   "when done manually."))
        grid0.addWidget(self.punch_cb, 23, 0, 1, 2)

        # this way I can hide/show the frame
        self.punch_frame = QtWidgets.QFrame()
        self.punch_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.punch_frame)
        punch_grid = QtWidgets.QGridLayout()
        punch_grid.setContentsMargins(0, 0, 0, 0)
        self.punch_frame.setLayout(punch_grid)

        punch_grid.setColumnStretch(0, 0)
        punch_grid.setColumnStretch(1, 1)

        self.ois_p = OptionalHideInputSection(self.punch_cb, [self.punch_frame])

        self.source_label = FCLabel('%s:' % _("Source"))
        self.source_label.setToolTip(
            _("The punch hole source can be:\n"
              "- Excellon -> an Excellon holes center will serve as reference.\n"
              "- Pad Center -> will try to use the pads center as reference.")
        )
        self.source_punch = RadioSet([{'label': _('Excellon'), 'value': 'exc'},
                                      {'label': _('Pad center'), 'value': 'pad'}],
                                     stretch=False)
        punch_grid.addWidget(self.source_label, 0, 0)
        punch_grid.addWidget(self.source_punch, 0, 1)

        self.exc_label = FCLabel('%s:' % _("Excellon Obj"))
        self.exc_label.setToolTip(
            _("Remove the geometry of Excellon from the Film to create the holes in pads.")
        )
        self.exc_combo = FCComboBox()
        self.exc_combo.setModel(self.app.collection)
        self.exc_combo.setRootModelIndex(self.app.collection.index(1, 0, QtCore.QModelIndex()))
        self.exc_combo.is_last = True
        self.exc_combo.obj_type = "Excellon"

        punch_grid.addWidget(self.exc_label, 1, 0)
        punch_grid.addWidget(self.exc_combo, 1, 1)

        self.exc_label.hide()
        self.exc_combo.hide()

        self.punch_size_label = FCLabel('%s:' % _("Punch Size"))
        self.punch_size_label.setToolTip(_("The value here will control how big is the punch hole in the pads."))
        self.punch_size_spinner = FCDoubleSpinner(callback=self.confirmation_message)
        self.punch_size_spinner.set_range(0, 999.9999)
        self.punch_size_spinner.setSingleStep(0.1)
        self.punch_size_spinner.set_precision(self.decimals)

        punch_grid.addWidget(self.punch_size_label, 2, 0)
        punch_grid.addWidget(self.punch_size_spinner, 2, 1)

        self.punch_size_label.hide()
        self.punch_size_spinner.hide()

        grid1 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid1)
        grid1.setColumnStretch(0, 0)
        grid1.setColumnStretch(1, 1)

        separator_line3 = QtWidgets.QFrame()
        separator_line3.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line3.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid1.addWidget(separator_line3, 0, 0, 1, 2)

        # File type
        self.file_type_radio = RadioSet([{'label': _('SVG'), 'value': 'svg'},
                                         {'label': _('PNG'), 'value': 'png'},
                                         {'label': _('PDF'), 'value': 'pdf'}
                                         ], stretch=False)

        self.file_type_label = FCLabel('%s:' % _("Film Type"))
        self.file_type_label.setToolTip(
            _("The file type of the saved film. Can be:\n"
              "- 'SVG' -> open-source vectorial format\n"
              "- 'PNG' -> raster image\n"
              "- 'PDF' -> portable document format")
        )
        grid1.addWidget(self.file_type_label, 1, 0)
        grid1.addWidget(self.file_type_radio, 1, 1)

        # Page orientation
        self.orientation_label = FCLabel('%s:' % _("Page Orientation"))
        self.orientation_label.setToolTip(_("Can be:\n"
                                            "- Portrait\n"
                                            "- Landscape"))

        self.orientation_radio = RadioSet([{'label': _('Portrait'), 'value': 'p'},
                                           {'label': _('Landscape'), 'value': 'l'},
                                           ], stretch=False)

        grid1.addWidget(self.orientation_label, 2, 0)
        grid1.addWidget(self.orientation_radio, 2, 1)

        # Page Size
        self.pagesize_label = FCLabel('%s:' % _("Page Size"))
        self.pagesize_label.setToolTip(_("A selection of standard ISO 216 page sizes."))

        self.pagesize_combo = FCComboBox()

        self.pagesize = {}
        self.pagesize.update(
            {
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
        )

        page_size_list = list(self.pagesize.keys())
        self.pagesize_combo.addItems(page_size_list)

        grid1.addWidget(self.pagesize_label, 3, 0)
        grid1.addWidget(self.pagesize_combo, 3, 1)

        self.on_film_type(val='hide')

        # PNG DPI
        self.png_dpi_label = FCLabel('%s:' % "PNG DPI")
        self.png_dpi_label.setToolTip(
            _("Default value is 96 DPI. Change this value to scale the PNG file.")
        )
        self.png_dpi_spinner = FCSpinner(callback=self.confirmation_message_int)
        self.png_dpi_spinner.set_range(0, 100000)

        grid1.addWidget(self.png_dpi_label, 4, 0)
        grid1.addWidget(self.png_dpi_spinner, 4, 1)

        self.png_dpi_label.hide()
        self.png_dpi_spinner.hide()

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
        grid1.addWidget(self.film_object_button, 6, 0, 1, 2)

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
            self.exc_label.hide()
            self.exc_combo.hide()
        else:
            self.punch_size_label.hide()
            self.punch_size_spinner.hide()
            self.exc_label.show()
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
