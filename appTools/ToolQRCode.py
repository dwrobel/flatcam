# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 10/24/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt

from appTool import AppTool
from appGUI.GUIElements import RadioSet, FCTextArea, FCSpinner, FCEntry, FCCheckBox, FCComboBox, FCFileSaveDialog
from appParsers.ParseSVG import *

from shapely.geometry.base import *
from shapely.ops import unary_union
from shapely.affinity import translate
from shapely.geometry import box

from io import StringIO, BytesIO
from collections import Iterable
import logging
from copy import deepcopy

import qrcode
import qrcode.image.svg
import qrcode.image.pil
from lxml import etree as ET

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class QRCode(AppTool):

    def __init__(self, app):
        AppTool.__init__(self, app)

        self.app = app
        self.canvas = self.app.plotcanvas

        self.decimals = self.app.decimals
        self.units = ''

        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = QRcodeUI(layout=self.layout, app=self.app)
        self.toolName = self.ui.toolName

        self.grb_object = None
        self.box_poly = None
        self.proc = None

        self.origin = (0, 0)

        self.mm = None
        self.mr = None
        self.kr = None

        self.shapes = self.app.move_tool.sel_shapes
        self.qrcode_geometry = MultiPolygon()
        self.qrcode_utility_geometry = MultiPolygon()

        self.old_back_color = ''

        # Signals #
        self.ui.qrcode_button.clicked.connect(self.execute)
        self.ui.export_cb.stateChanged.connect(self.on_export_frame)
        self.ui.export_png_button.clicked.connect(self.export_png_file)
        self.ui.export_svg_button.clicked.connect(self.export_svg_file)

        self.ui.fill_color_entry.editingFinished.connect(self.on_qrcode_fill_color_entry)
        self.ui.fill_color_button.clicked.connect(self.on_qrcode_fill_color_button)
        self.ui.back_color_entry.editingFinished.connect(self.on_qrcode_back_color_entry)
        self.ui.back_color_button.clicked.connect(self.on_qrcode_back_color_button)

        self.ui.transparent_cb.stateChanged.connect(self.on_transparent_back_color)
        self.ui.reset_button.clicked.connect(self.set_tool_ui)

    def run(self, toggle=True):
        self.app.defaults.report_usage("QRCode()")

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

        self.app.ui.notebook.setTabText(2, _("QRCode Tool"))

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Alt+Q', **kwargs)

    def set_tool_ui(self):
        self.units = self.app.defaults['units']
        self.ui.border_size_entry.set_value(4)

        self.ui.version_entry.set_value(int(self.app.defaults["tools_qrcode_version"]))
        self.ui.error_radio.set_value(self.app.defaults["tools_qrcode_error"])
        self.ui.bsize_entry.set_value(int(self.app.defaults["tools_qrcode_box_size"]))
        self.ui.border_size_entry.set_value(int(self.app.defaults["tools_qrcode_border_size"]))
        self.ui.pol_radio.set_value(self.app.defaults["tools_qrcode_polarity"])
        self.ui.bb_radio.set_value(self.app.defaults["tools_qrcode_rounded"])

        self.ui.text_data.set_value(self.app.defaults["tools_qrcode_qrdata"])

        self.ui.fill_color_entry.set_value(self.app.defaults['tools_qrcode_fill_color'])
        self.ui.fill_color_button.setStyleSheet("background-color:%s" %
                                                str(self.app.defaults['tools_qrcode_fill_color'])[:7])

        self.ui.back_color_entry.set_value(self.app.defaults['tools_qrcode_back_color'])
        self.ui.back_color_button.setStyleSheet("background-color:%s" %
                                                str(self.app.defaults['tools_qrcode_back_color'])[:7])

    def on_export_frame(self, state):
        self.ui.export_frame.setVisible(state)
        self.ui.qrcode_button.setVisible(not state)

    def execute(self):
        text_data = self.ui.text_data.get_value()
        if text_data == '':
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Cancelled. There is no QRCode Data in the text box."))
            return

        # get the Gerber object on which the QRCode will be inserted
        selection_index = self.ui.grb_object_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.ui.grb_object_combo.rootModelIndex())

        try:
            self.grb_object = model_index.internalPointer().obj
        except Exception as e:
            log.debug("QRCode.execute() --> %s" % str(e))
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Gerber object loaded ..."))
            return

        # we can safely activate the mouse events
        self.mm = self.app.plotcanvas.graph_event_connect('mouse_move', self.on_mouse_move)
        self.mr = self.app.plotcanvas.graph_event_connect('mouse_release', self.on_mouse_release)
        self.kr = self.app.plotcanvas.graph_event_connect('key_release', self.on_key_release)

        def job_thread_qr(app_obj):
            with self.app.proc_container.new('%s' % _("Working ...")) as self.proc:

                error_code = {
                    'L': qrcode.constants.ERROR_CORRECT_L,
                    'M': qrcode.constants.ERROR_CORRECT_M,
                    'Q': qrcode.constants.ERROR_CORRECT_Q,
                    'H': qrcode.constants.ERROR_CORRECT_H
                }[self.ui.error_radio.get_value()]

                qr = qrcode.QRCode(
                    version=self.ui.version_entry.get_value(),
                    error_correction=error_code,
                    box_size=self.ui.bsize_entry.get_value(),
                    border=self.ui.border_size_entry.get_value(),
                    image_factory=qrcode.image.svg.SvgFragmentImage
                )
                qr.add_data(text_data)
                qr.make()

                svg_file = BytesIO()
                img = qr.make_image()
                img.save(svg_file)

                svg_text = StringIO(svg_file.getvalue().decode('UTF-8'))
                svg_geometry = self.convert_svg_to_geo(svg_text, units=self.units)
                self.qrcode_geometry = deepcopy(svg_geometry)

                svg_geometry = unary_union(svg_geometry).buffer(0.0000001).buffer(-0.0000001)
                self.qrcode_utility_geometry = svg_geometry

                # make a bounding box of the QRCode geometry to help drawing the utility geometry in case it is too
                # complicated
                try:
                    a, b, c, d = self.qrcode_utility_geometry.bounds
                    self.box_poly = box(minx=a, miny=b, maxx=c, maxy=d)
                except Exception as ee:
                    log.debug("QRCode.make() bounds error --> %s" % str(ee))

                app_obj.call_source = 'qrcode_tool'
                app_obj.inform.emit(_("Click on the DESTINATION point ..."))

        self.app.worker_task.emit({'fcn': job_thread_qr, 'params': [self.app]})

    def make(self, pos):
        self.on_exit()

        # make sure that the source object solid geometry is an Iterable
        if not isinstance(self.grb_object.solid_geometry, Iterable):
            self.grb_object.solid_geometry = [self.grb_object.solid_geometry]

        # I use the utility geometry (self.qrcode_utility_geometry) because it is already buffered
        geo_list = self.grb_object.solid_geometry
        if isinstance(self.grb_object.solid_geometry, MultiPolygon):
            geo_list = list(self.grb_object.solid_geometry.geoms)

        # this is the bounding box of the QRCode geometry
        a, b, c, d = self.qrcode_utility_geometry.bounds
        buff_val = self.ui.border_size_entry.get_value() * (self.ui.bsize_entry.get_value() / 10)

        if self.ui.bb_radio.get_value() == 'r':
            mask_geo = box(a, b, c, d).buffer(buff_val)
        else:
            mask_geo = box(a, b, c, d).buffer(buff_val, join_style=2)

        # update the solid geometry with the cutout (if it is the case)
        new_solid_geometry = []
        offset_mask_geo = translate(mask_geo, xoff=pos[0], yoff=pos[1])
        for poly in geo_list:
            if poly.contains(offset_mask_geo):
                new_solid_geometry.append(poly.difference(offset_mask_geo))
            else:
                if poly not in new_solid_geometry:
                    new_solid_geometry.append(poly)

        geo_list = deepcopy(list(new_solid_geometry))

        # Polarity
        if self.ui.pol_radio.get_value() == 'pos':
            working_geo = self.qrcode_utility_geometry
        else:
            working_geo = mask_geo.difference(self.qrcode_utility_geometry)

        try:
            for geo in working_geo:
                geo_list.append(translate(geo, xoff=pos[0], yoff=pos[1]))
        except TypeError:
            geo_list.append(translate(working_geo, xoff=pos[0], yoff=pos[1]))

        self.grb_object.solid_geometry = deepcopy(geo_list)

        box_size = float(self.ui.bsize_entry.get_value()) / 10.0

        sort_apid = []
        new_apid = '10'
        if self.grb_object.apertures:
            for k, v in list(self.grb_object.apertures.items()):
                sort_apid.append(int(k))
            sorted_apertures = sorted(sort_apid)
            max_apid = max(sorted_apertures)
            if max_apid >= 10:
                new_apid = str(max_apid + 1)
            else:
                new_apid = '10'

        # don't know if the condition is required since I already made sure above that the new_apid is a new one
        if new_apid not in self.grb_object.apertures:
            self.grb_object.apertures[new_apid] = {
                'type': 'R',
                'geometry': []
            }

            # TODO: HACK
            # I've artificially added 1% to the height and width because otherwise after loading the
            # exported file, it will not be correctly reconstructed (it will be made from multiple shapes instead of
            # one shape which show that the buffering didn't worked well). It may be the MM to INCH conversion.
            self.grb_object.apertures[new_apid]['height'] = deepcopy(box_size * 1.01)
            self.grb_object.apertures[new_apid]['width'] = deepcopy(box_size * 1.01)
            self.grb_object.apertures[new_apid]['size'] = deepcopy(math.sqrt(box_size ** 2 + box_size ** 2))

        if '0' not in self.grb_object.apertures:
            self.grb_object.apertures['0'] = {
                'type': 'REG',
                'size': 0.0,
                'geometry': []
            }

        # in case that the QRCode geometry is dropped onto a copper region (found in the '0' aperture)
        # make sure that I place a cutout there
        zero_elem = {'clear': offset_mask_geo}
        self.grb_object.apertures['0']['geometry'].append(deepcopy(zero_elem))

        try:
            a, b, c, d = self.grb_object.bounds()
            self.grb_object.options['xmin'] = a
            self.grb_object.options['ymin'] = b
            self.grb_object.options['xmax'] = c
            self.grb_object.options['ymax'] = d
        except Exception as e:
            log.debug("QRCode.make() bounds error --> %s" % str(e))

        try:
            for geo in self.qrcode_geometry:
                geo_elem = {
                    'solid': translate(geo, xoff=pos[0], yoff=pos[1]),
                    'follow': translate(geo.centroid, xoff=pos[0], yoff=pos[1])
                }
                self.grb_object.apertures[new_apid]['geometry'].append(deepcopy(geo_elem))
        except TypeError:
            geo_elem = {'solid': self.qrcode_geometry}
            self.grb_object.apertures[new_apid]['geometry'].append(deepcopy(geo_elem))

        # update the source file with the new geometry:
        self.grb_object.source_file = self.app.f_handlers.export_gerber(obj_name=self.grb_object.options['name'],
                                                                        filename=None,
                                                                        local_use=self.grb_object, use_thread=False)

        self.replot(obj=self.grb_object)
        self.app.inform.emit('[success] %s' % _("QRCode Tool done."))

    def draw_utility_geo(self, pos):

        # face = '#0000FF' + str(hex(int(0.2 * 255)))[2:]
        outline = '#0000FFAF'

        offset_geo = []

        # I use the len of self.qrcode_geometry instead of the utility one because the complexity of the polygons is
        # better seen in this (bit what if the sel.qrcode_geometry is just one geo element? len will fail ...
        if len(self.qrcode_geometry) <= self.app.defaults["tools_qrcode_sel_limit"]:
            try:
                for poly in self.qrcode_utility_geometry:
                    offset_geo.append(translate(poly.exterior, xoff=pos[0], yoff=pos[1]))
                    for geo_int in poly.interiors:
                        offset_geo.append(translate(geo_int, xoff=pos[0], yoff=pos[1]))
            except TypeError:
                offset_geo.append(translate(self.qrcode_utility_geometry.exterior, xoff=pos[0], yoff=pos[1]))
                for geo_int in self.qrcode_utility_geometry.interiors:
                    offset_geo.append(translate(geo_int, xoff=pos[0], yoff=pos[1]))
        else:
            offset_geo = [translate(self.box_poly, xoff=pos[0], yoff=pos[1])]

        for shape in offset_geo:
            self.shapes.add(shape, color=outline, update=True, layer=0, tolerance=None)

        if self.app.is_legacy is True:
            self.shapes.redraw()

    def delete_utility_geo(self):
        self.shapes.clear(update=True)
        self.shapes.redraw()

    def on_mouse_move(self, event):
        if self.app.is_legacy is False:
            event_pos = event.pos
        else:
            event_pos = (event.xdata, event.ydata)

        try:
            x = float(event_pos[0])
            y = float(event_pos[1])
        except TypeError:
            return

        pos_canvas = self.app.plotcanvas.translate_coords((x, y))

        # if GRID is active we need to get the snapped positions
        if self.app.grid_status():
            pos = self.app.geo_editor.snap(pos_canvas[0], pos_canvas[1])
        else:
            pos = pos_canvas

        dx = pos[0] - self.origin[0]
        dy = pos[1] - self.origin[1]

        # delete the utility geometry
        self.delete_utility_geo()
        self.draw_utility_geo((dx, dy))

    def on_mouse_release(self, event):
        # mouse click will be accepted only if the left button is clicked
        # this is necessary because right mouse click and middle mouse click
        # are used for panning on the canvas

        if self.app.is_legacy is False:
            event_pos = event.pos
        else:
            event_pos = (event.xdata, event.ydata)

        if event.button == 1:
            pos_canvas = self.app.plotcanvas.translate_coords(event_pos)
            self.delete_utility_geo()

            # if GRID is active we need to get the snapped positions
            if self.app.grid_status():
                pos = self.app.geo_editor.snap(pos_canvas[0], pos_canvas[1])
            else:
                pos = pos_canvas

            dx = pos[0] - self.origin[0]
            dy = pos[1] - self.origin[1]

            self.make(pos=(dx, dy))

    def on_key_release(self, event):
        pass

    def convert_svg_to_geo(self, filename, object_type=None, flip=True, units='MM'):
        """
        Convert shapes from an SVG file into a geometry list.

        :param filename: A String Stream file.
        :param object_type: parameter passed further along. What kind the object will receive the SVG geometry
        :param flip: Flip the vertically.
        :type flip: bool
        :param units: FlatCAM units
        :return: None
        """

        # Parse into list of shapely objects
        svg_tree = ET.parse(filename)
        svg_root = svg_tree.getroot()

        # Change origin to bottom left
        # h = float(svg_root.get('height'))
        # w = float(svg_root.get('width'))
        h = svgparselength(svg_root.get('height'))[0]  # TODO: No units support yet
        units = self.app.defaults['units'] if units is None else units
        res = self.app.defaults['geometry_circle_steps']
        factor = svgparse_viewbox(svg_root)
        geos = getsvggeo(svg_root, object_type, units=units, res=res, factor=factor)

        if flip:
            geos = [translate(scale(g, 1.0, -1.0, origin=(0, 0)), yoff=h) for g in geos]

        # flatten the svg geometry for the case when the QRCode SVG is added into a Gerber object
        solid_geometry = list(self.flatten_list(geos))

        geos_text = getsvgtext(svg_root, object_type, units=units)
        if geos_text is not None:
            geos_text_f = []
            if flip:
                # Change origin to bottom left
                for i in geos_text:
                    _, minimy, _, maximy = i.bounds
                    h2 = (maximy - minimy) * 0.5
                    geos_text_f.append(translate(scale(i, 1.0, -1.0, origin=(0, 0)), yoff=(h + h2)))
            if geos_text_f:
                solid_geometry += geos_text_f
        return solid_geometry

    def flatten_list(self, geo_list):
        for item in geo_list:
            if isinstance(item, Iterable) and not isinstance(item, (str, bytes)):
                yield from self.flatten_list(item)
            else:
                yield item

    def replot(self, obj):
        def worker_task():
            with self.app.proc_container.new('%s ...' % _("Plotting")):
                obj.plot()

        self.app.worker_task.emit({'fcn': worker_task, 'params': []})

    def on_exit(self):
        if self.app.is_legacy is False:
            self.app.plotcanvas.graph_event_disconnect('mouse_move', self.on_mouse_move)
            self.app.plotcanvas.graph_event_disconnect('mouse_release', self.on_mouse_release)
            self.app.plotcanvas.graph_event_disconnect('key_release', self.on_key_release)
        else:
            self.app.plotcanvas.graph_event_disconnect(self.mm)
            self.app.plotcanvas.graph_event_disconnect(self.mr)
            self.app.plotcanvas.graph_event_disconnect(self.kr)

        # delete the utility geometry
        self.delete_utility_geo()
        self.app.call_source = 'app'

    def export_png_file(self):
        text_data = self.ui.text_data.get_value()
        if text_data == '':
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Cancelled. There is no QRCode Data in the text box."))
            return 'fail'

        def job_thread_qr_png(app_obj, fname):
            error_code = {
                'L': qrcode.constants.ERROR_CORRECT_L,
                'M': qrcode.constants.ERROR_CORRECT_M,
                'Q': qrcode.constants.ERROR_CORRECT_Q,
                'H': qrcode.constants.ERROR_CORRECT_H
            }[self.ui.error_radio.get_value()]

            qr = qrcode.QRCode(
                version=self.ui.version_entry.get_value(),
                error_correction=error_code,
                box_size=self.ui.bsize_entry.get_value(),
                border=self.ui.border_size_entry.get_value(),
                image_factory=qrcode.image.pil.PilImage
            )
            qr.add_data(text_data)
            qr.make(fit=True)

            img = qr.make_image(fill_color=self.ui.fill_color_entry.get_value(),
                                back_color=self.ui.back_color_entry.get_value())
            img.save(fname)

            app_obj.call_source = 'qrcode_tool'

        name = 'qr_code'

        _filter = "PNG File (*.png);;All Files (*.*)"
        try:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Export PNG"),
                directory=self.app.get_last_save_folder() + '/' + str(name) + '_png',
                ext_filter=_filter)
        except TypeError:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Export PNG"),
                ext_filter=_filter)

        filename = str(filename)

        if filename == "":
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
            return
        else:
            self.app.worker_task.emit({'fcn': job_thread_qr_png, 'params': [self.app, filename]})

    def export_svg_file(self):
        text_data = self.ui.text_data.get_value()
        if text_data == '':
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Cancelled. There is no QRCode Data in the text box."))
            return 'fail'

        def job_thread_qr_svg(app_obj, fname):
            error_code = {
                'L': qrcode.constants.ERROR_CORRECT_L,
                'M': qrcode.constants.ERROR_CORRECT_M,
                'Q': qrcode.constants.ERROR_CORRECT_Q,
                'H': qrcode.constants.ERROR_CORRECT_H
            }[self.ui.error_radio.get_value()]

            qr = qrcode.QRCode(
                version=self.ui.version_entry.get_value(),
                error_correction=error_code,
                box_size=self.ui.bsize_entry.get_value(),
                border=self.ui.border_size_entry.get_value(),
                image_factory=qrcode.image.svg.SvgPathImage
            )
            qr.add_data(text_data)
            img = qr.make_image(fill_color=self.ui.fill_color_entry.get_value(),
                                back_color=self.ui.back_color_entry.get_value())
            img.save(fname)

            app_obj.call_source = 'qrcode_tool'

        name = 'qr_code'

        _filter = "SVG File (*.svg);;All Files (*.*)"
        try:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Export SVG"),
                directory=self.app.get_last_save_folder() + '/' + str(name) + '_svg',
                ext_filter=_filter)
        except TypeError:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Export SVG"),
                ext_filter=_filter)

        filename = str(filename)

        if filename == "":
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
            return
        else:
            self.app.worker_task.emit({'fcn': job_thread_qr_svg, 'params': [self.app, filename]})

    def on_qrcode_fill_color_entry(self):
        color = self.ui.fill_color_entry.get_value()
        self.ui.fill_color_button.setStyleSheet("background-color:%s" % str(color))

    def on_qrcode_fill_color_button(self):
        current_color = QtGui.QColor(self.ui.fill_color_entry.get_value())

        c_dialog = QtWidgets.QColorDialog()
        fill_color = c_dialog.getColor(initial=current_color)

        if fill_color.isValid() is False:
            return

        self.ui.fill_color_button.setStyleSheet("background-color:%s" % str(fill_color.name()))

        new_val_sel = str(fill_color.name())
        self.ui.fill_color_entry.set_value(new_val_sel)

    def on_qrcode_back_color_entry(self):
        color = self.ui.back_color_entry.get_value()
        self.ui.back_color_button.setStyleSheet("background-color:%s" % str(color))

    def on_qrcode_back_color_button(self):
        current_color = QtGui.QColor(self.ui.back_color_entry.get_value())

        c_dialog = QtWidgets.QColorDialog()
        back_color = c_dialog.getColor(initial=current_color)

        if back_color.isValid() is False:
            return

        self.ui.back_color_button.setStyleSheet("background-color:%s" % str(back_color.name()))

        new_val_sel = str(back_color.name())
        self.ui.back_color_entry.set_value(new_val_sel)

    def on_transparent_back_color(self, state):
        if state:
            self.ui.back_color_entry.setDisabled(True)
            self.ui.back_color_button.setDisabled(True)
            self.old_back_color = self.ui.back_color_entry.get_value()
            self.ui.back_color_entry.set_value('transparent')
        else:
            self.ui.back_color_entry.setDisabled(False)
            self.ui.back_color_button.setDisabled(False)
            self.ui.back_color_entry.set_value(self.old_back_color)


class QRcodeUI:

    toolName = _("QRCode Tool")

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
        self.layout.addWidget(QtWidgets.QLabel(''))

        # ## Grid Layout
        i_grid_lay = QtWidgets.QGridLayout()
        self.layout.addLayout(i_grid_lay)
        i_grid_lay.setColumnStretch(0, 0)
        i_grid_lay.setColumnStretch(1, 1)

        self.grb_object_combo = FCComboBox()
        self.grb_object_combo.setModel(self.app.collection)
        self.grb_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.grb_object_combo.is_last = True
        self.grb_object_combo.obj_type = "Gerber"

        self.grbobj_label = QtWidgets.QLabel("<b>%s:</b>" % _("GERBER"))
        self.grbobj_label.setToolTip(
            _("Gerber Object to which the QRCode will be added.")
        )

        i_grid_lay.addWidget(self.grbobj_label, 0, 0)
        i_grid_lay.addWidget(self.grb_object_combo, 1, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        i_grid_lay.addWidget(separator_line, 2, 0, 1, 2)

        # Text box
        self.text_label = QtWidgets.QLabel('<b>%s</b>:' % _("QRCode Data"))
        self.text_label.setToolTip(
            _("QRCode Data. Alphanumeric text to be encoded in the QRCode.")
        )
        self.text_data = FCTextArea()
        self.text_data.setPlaceholderText(
            _("Add here the text to be included in the QRCode...")
        )
        i_grid_lay.addWidget(self.text_label, 5, 0)
        i_grid_lay.addWidget(self.text_data, 6, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        i_grid_lay.addWidget(separator_line, 7, 0, 1, 2)

        # ## Grid Layout
        grid_lay = QtWidgets.QGridLayout()
        self.layout.addLayout(grid_lay)
        grid_lay.setColumnStretch(0, 0)
        grid_lay.setColumnStretch(1, 1)

        self.qrcode_label = QtWidgets.QLabel('<b>%s</b>' % _('Parameters'))
        self.qrcode_label.setToolTip(
            _("The parameters used to shape the QRCode.")
        )
        grid_lay.addWidget(self.qrcode_label, 0, 0, 1, 2)

        # VERSION #
        self.version_label = QtWidgets.QLabel('%s:' % _("Version"))
        self.version_label.setToolTip(
            _("QRCode version can have values from 1 (21x21 boxes)\n"
              "to 40 (177x177 boxes).")
        )
        self.version_entry = FCSpinner(callback=self.confirmation_message_int)
        self.version_entry.set_range(1, 40)
        self.version_entry.setWrapping(True)

        grid_lay.addWidget(self.version_label, 1, 0)
        grid_lay.addWidget(self.version_entry, 1, 1)

        # ERROR CORRECTION #
        self.error_label = QtWidgets.QLabel('%s:' % _("Error correction"))
        self.error_label.setToolTip(
            _("Parameter that controls the error correction used for the QR Code.\n"
              "L = maximum 7%% errors can be corrected\n"
              "M = maximum 15%% errors can be corrected\n"
              "Q = maximum 25%% errors can be corrected\n"
              "H = maximum 30%% errors can be corrected.")
        )
        self.error_radio = RadioSet([{'label': 'L', 'value': 'L'},
                                     {'label': 'M', 'value': 'M'},
                                     {'label': 'Q', 'value': 'Q'},
                                     {'label': 'H', 'value': 'H'}])
        self.error_radio.setToolTip(
            _("Parameter that controls the error correction used for the QR Code.\n"
              "L = maximum 7%% errors can be corrected\n"
              "M = maximum 15%% errors can be corrected\n"
              "Q = maximum 25%% errors can be corrected\n"
              "H = maximum 30%% errors can be corrected.")
        )
        grid_lay.addWidget(self.error_label, 2, 0)
        grid_lay.addWidget(self.error_radio, 2, 1)

        # BOX SIZE #
        self.bsize_label = QtWidgets.QLabel('%s:' % _("Box Size"))
        self.bsize_label.setToolTip(
            _("Box size control the overall size of the QRcode\n"
              "by adjusting the size of each box in the code.")
        )
        self.bsize_entry = FCSpinner(callback=self.confirmation_message_int)
        self.bsize_entry.set_range(1, 9999)
        self.bsize_entry.setWrapping(True)

        grid_lay.addWidget(self.bsize_label, 3, 0)
        grid_lay.addWidget(self.bsize_entry, 3, 1)

        # BORDER SIZE #
        self.border_size_label = QtWidgets.QLabel('%s:' % _("Border Size"))
        self.border_size_label.setToolTip(
            _("Size of the QRCode border. How many boxes thick is the border.\n"
              "Default value is 4. The width of the clearance around the QRCode.")
        )
        self.border_size_entry = FCSpinner(callback=self.confirmation_message_int)
        self.border_size_entry.set_range(1, 9999)
        self.border_size_entry.setWrapping(True)

        grid_lay.addWidget(self.border_size_label, 4, 0)
        grid_lay.addWidget(self.border_size_entry, 4, 1)

        # POLARITY CHOICE #
        self.pol_label = QtWidgets.QLabel('%s:' % _("Polarity"))
        self.pol_label.setToolTip(
            _("Choose the polarity of the QRCode.\n"
              "It can be drawn in a negative way (squares are clear)\n"
              "or in a positive way (squares are opaque).")
        )
        self.pol_radio = RadioSet([{'label': _('Negative'), 'value': 'neg'},
                                   {'label': _('Positive'), 'value': 'pos'}])
        self.pol_radio.setToolTip(
            _("Choose the type of QRCode to be created.\n"
              "If added on a Silkscreen Gerber file the QRCode may\n"
              "be added as positive. If it is added to a Copper Gerber\n"
              "file then perhaps the QRCode can be added as negative.")
        )
        grid_lay.addWidget(self.pol_label, 7, 0)
        grid_lay.addWidget(self.pol_radio, 7, 1)

        # BOUNDING BOX TYPE #
        self.bb_label = QtWidgets.QLabel('%s:' % _("Bounding Box"))
        self.bb_label.setToolTip(
            _("The bounding box, meaning the empty space that surrounds\n"
              "the QRCode geometry, can have a rounded or a square shape.")
        )
        self.bb_radio = RadioSet([{'label': _('Rounded'), 'value': 'r'},
                                  {'label': _('Square'), 'value': 's'}])
        self.bb_radio.setToolTip(
            _("The bounding box, meaning the empty space that surrounds\n"
              "the QRCode geometry, can have a rounded or a square shape.")
        )
        grid_lay.addWidget(self.bb_label, 8, 0)
        grid_lay.addWidget(self.bb_radio, 8, 1)

        # Export QRCode
        self.export_cb = FCCheckBox(_("Export QRCode"))
        self.export_cb.setToolTip(
            _("Show a set of controls allowing to export the QRCode\n"
              "to a SVG file or an PNG file.")
        )
        grid_lay.addWidget(self.export_cb, 9, 0, 1, 2)

        # this way I can hide/show the frame
        self.export_frame = QtWidgets.QFrame()
        self.export_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.export_frame)
        self.export_lay = QtWidgets.QGridLayout()
        self.export_lay.setContentsMargins(0, 0, 0, 0)
        self.export_frame.setLayout(self.export_lay)
        self.export_lay.setColumnStretch(0, 0)
        self.export_lay.setColumnStretch(1, 1)

        # default is hidden
        self.export_frame.hide()

        # FILL COLOR #
        self.fill_color_label = QtWidgets.QLabel('%s:' % _('Fill Color'))
        self.fill_color_label.setToolTip(
            _("Set the QRCode fill color (squares color).")
        )
        self.fill_color_entry = FCEntry()
        self.fill_color_button = QtWidgets.QPushButton()
        self.fill_color_button.setFixedSize(15, 15)

        fill_lay_child = QtWidgets.QHBoxLayout()
        fill_lay_child.setContentsMargins(0, 0, 0, 0)
        fill_lay_child.addWidget(self.fill_color_entry)
        fill_lay_child.addWidget(self.fill_color_button, alignment=Qt.AlignRight)
        fill_lay_child.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        fill_color_widget = QtWidgets.QWidget()
        fill_color_widget.setLayout(fill_lay_child)

        self.export_lay.addWidget(self.fill_color_label, 0, 0)
        self.export_lay.addWidget(fill_color_widget, 0, 1)

        self.transparent_cb = FCCheckBox(_("Transparent back color"))
        self.export_lay.addWidget(self.transparent_cb, 1, 0, 1, 2)

        # BACK COLOR #
        self.back_color_label = QtWidgets.QLabel('%s:' % _('Back Color'))
        self.back_color_label.setToolTip(
            _("Set the QRCode background color.")
        )
        self.back_color_entry = FCEntry()
        self.back_color_button = QtWidgets.QPushButton()
        self.back_color_button.setFixedSize(15, 15)

        back_lay_child = QtWidgets.QHBoxLayout()
        back_lay_child.setContentsMargins(0, 0, 0, 0)
        back_lay_child.addWidget(self.back_color_entry)
        back_lay_child.addWidget(self.back_color_button, alignment=Qt.AlignRight)
        back_lay_child.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        back_color_widget = QtWidgets.QWidget()
        back_color_widget.setLayout(back_lay_child)

        self.export_lay.addWidget(self.back_color_label, 2, 0)
        self.export_lay.addWidget(back_color_widget, 2, 1)

        # ## Export QRCode as SVG image
        self.export_svg_button = QtWidgets.QPushButton(_("Export QRCode SVG"))
        self.export_svg_button.setToolTip(
            _("Export a SVG file with the QRCode content.")
        )
        self.export_svg_button.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        self.export_lay.addWidget(self.export_svg_button, 3, 0, 1, 2)

        # ## Export QRCode as PNG image
        self.export_png_button = QtWidgets.QPushButton(_("Export QRCode PNG"))
        self.export_png_button.setToolTip(
            _("Export a PNG image file with the QRCode content.")
        )
        self.export_png_button.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        self.export_lay.addWidget(self.export_png_button, 4, 0, 1, 2)

        # ## Insert QRCode
        self.qrcode_button = QtWidgets.QPushButton(_("Insert QRCode"))
        self.qrcode_button.setIcon(QtGui.QIcon(self.app.resource_location + '/qrcode32.png'))
        self.qrcode_button.setToolTip(
            _("Create the QRCode object.")
        )
        self.qrcode_button.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        self.layout.addWidget(self.qrcode_button)

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
