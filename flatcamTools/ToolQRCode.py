# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 10/24/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtCore

from FlatCAMTool import FlatCAMTool
from flatcamGUI.GUIElements import RadioSet, FCTextArea, FCSpinner, FCDoubleSpinner
from flatcamParsers.ParseSVG import *

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
from lxml import etree as ET

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class QRCode(FlatCAMTool):

    toolName = _("QRCode Tool")

    def __init__(self, app):
        FlatCAMTool.__init__(self, app)

        self.app = app
        self.canvas = self.app.plotcanvas

        self.decimals = 4
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

        # ## Grid Layout
        i_grid_lay = QtWidgets.QGridLayout()
        self.layout.addLayout(i_grid_lay)
        i_grid_lay.setColumnStretch(0, 0)
        i_grid_lay.setColumnStretch(1, 1)

        self.grb_object_combo = QtWidgets.QComboBox()
        self.grb_object_combo.setModel(self.app.collection)
        self.grb_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.grb_object_combo.setCurrentIndex(1)

        self.grbobj_label = QtWidgets.QLabel("<b>%s:</b>" % _("GERBER"))
        self.grbobj_label.setToolTip(
            _("Gerber Object to which the QRCode will be added.")
        )

        i_grid_lay.addWidget(self.grbobj_label, 0, 0)
        i_grid_lay.addWidget(self.grb_object_combo, 0, 1, 1, 2)
        i_grid_lay.addWidget(QtWidgets.QLabel(''), 1, 0)

        # ## Grid Layout
        grid_lay = QtWidgets.QGridLayout()
        self.layout.addLayout(grid_lay)
        grid_lay.setColumnStretch(0, 0)
        grid_lay.setColumnStretch(1, 1)

        self.qrcode_label = QtWidgets.QLabel('<b>%s</b>' % _('QRCode Parameters'))
        self.qrcode_label.setToolTip(
            _("Contain the expected calibration points and the\n"
              "ones measured.")
        )
        grid_lay.addWidget(self.qrcode_label, 0, 0, 1, 2)

        # VERSION #
        self.version_label = QtWidgets.QLabel('%s:' % _("Version"))
        self.version_label.setToolTip(
            _("QRCode version can have values from 1 (21x21 boxes)\n"
              "to 40 (177x177 boxes).")
        )
        self.version_entry = FCSpinner()
        self.version_entry.set_range(1, 40)
        self.version_entry.setWrapping(True)

        grid_lay.addWidget(self.version_label, 1, 0)
        grid_lay.addWidget(self.version_entry, 1, 1)

        # ERROR CORRECTION #
        self.error_label = QtWidgets.QLabel('%s:' % _("Error correction"))
        self.error_label.setToolTip(
            _("Parameter that controls the error correction used for the QR Code.\n"
              "L = maximum 7% errors can be corrected\n"
              "M = maximum 15% errors can be corrected\n"
              "Q = maximum 25% errors can be corrected\n"
              "H = maximum 30% errors can be corrected.")
        )
        self.error_radio = RadioSet([{'label': 'L', 'value': 'L'},
                                     {'label': 'M', 'value': 'M'},
                                     {'label': 'Q', 'value': 'Q'},
                                     {'label': 'H', 'value': 'H'}])
        self.error_radio.setToolTip(
            _("Parameter that controls the error correction used for the QR Code.\n"
              "L = maximum 7% errors can be corrected\n"
              "M = maximum 15% errors can be corrected\n"
              "Q = maximum 25% errors can be corrected\n"
              "H = maximum 30% errors can be corrected.")
        )
        grid_lay.addWidget(self.error_label, 2, 0)
        grid_lay.addWidget(self.error_radio, 2, 1)

        # BOX SIZE #
        self.bsize_label = QtWidgets.QLabel('%s:' % _("Box Size"))
        self.bsize_label.setToolTip(
            _("Box size control the overall size of the QRcode\n"
              "by adjusting the size of each box in the code.")
        )
        self.bsize_entry = FCSpinner()
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
        self.border_size_entry = FCSpinner()
        self.border_size_entry.set_range(1, 9999)
        self.border_size_entry.setWrapping(True)
        self.border_size_entry.set_value(4)

        grid_lay.addWidget(self.border_size_label, 4, 0)
        grid_lay.addWidget(self.border_size_entry, 4, 1)

        # Text box
        self.text_label = QtWidgets.QLabel('%s:' % _("QRCode Data"))
        self.text_label.setToolTip(
            _("QRCode Data. Alphanumeric text to be encoded in the QRCode.")
        )
        self.text_data = FCTextArea()
        self.text_data.setPlaceholderText(
            _("Add here the text to be included in the QRData...")
        )
        grid_lay.addWidget(self.text_label, 5, 0)
        grid_lay.addWidget(self.text_data, 6, 0, 1, 2)

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
              "If added on a Silkscreen Gerber you may add\n"
              "it as positive. If you add it to a Copper\n"
              "Gerber then perhaps you can add it as positive.")
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

        # ## Create QRCode
        self.qrcode_button = QtWidgets.QPushButton(_("Create QRCode"))
        self.qrcode_button.setToolTip(
            _("Create the QRCode object.")
        )
        grid_lay.addWidget(self.qrcode_button, 9, 0, 1, 2)
        grid_lay.addWidget(QtWidgets.QLabel(''), 10, 0)

        self.layout.addStretch()

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

    def run(self, toggle=True):
        self.app.report_usage("QRCode()")

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

        FlatCAMTool.run(self)

        self.set_tool_ui()

        self.app.ui.notebook.setTabText(2, _("QRCode Tool"))

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, shortcut='ALT+Q', **kwargs)

    def set_tool_ui(self):
        self.units = self.app.ui.general_defaults_form.general_app_group.units_radio.get_value()
        self.version_entry.set_value(1)
        self.error_radio.set_value('M')
        self.bsize_entry.set_value(3)
        self.border_size_entry.set_value(4)
        self.pol_radio.set_value('pos')
        self.bb_radio.set_value('r')

        # Signals #
        self.qrcode_button.clicked.connect(self.execute)

    def execute(self):
        text_data = self.text_data.get_value()
        if text_data == '':
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Cancelled. There is no QRCode Data in the text box."))
            return 'fail'

        # get the Gerber object on which the QRCode will be inserted
        selection_index = self.grb_object_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.grb_object_combo.rootModelIndex())

        try:
            self.grb_object = model_index.internalPointer().obj
        except Exception as e:
            log.debug("QRCode.execute() --> %s" % str(e))
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Gerber object loaded ..."))
            return 'fail'

        # we can safely activate the mouse events
        self.mm = self.app.plotcanvas.graph_event_connect('mouse_move', self.on_mouse_move)
        self.mr = self.app.plotcanvas.graph_event_connect('mouse_release', self.on_mouse_release)
        self.kr = self.app.plotcanvas.graph_event_connect('key_release', self.on_key_release)

        self.proc = self.app.proc_container.new('%s...' % _("Generating QRCode geometry"))

        def job_thread_qr(app_obj):
            error_code = {
                'L': qrcode.constants.ERROR_CORRECT_L,
                'M': qrcode.constants.ERROR_CORRECT_M,
                'Q': qrcode.constants.ERROR_CORRECT_Q,
                'H': qrcode.constants.ERROR_CORRECT_H
            }[self.error_radio.get_value()]

            qr = qrcode.QRCode(
                version=self.version_entry.get_value(),
                error_correction=error_code,
                box_size=self.bsize_entry.get_value(),
                border=self.border_size_entry.get_value(),
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
            except Exception as e:
                log.debug("QRCode.make() bounds error --> %s" % str(e))

            app_obj.call_source = 'qrcode_tool'
            app_obj.inform.emit(_("Click on the Destination point ..."))

        self.app.worker_task.emit({'fcn': job_thread_qr, 'params': [self.app]})

    def make(self, pos):
        self.on_exit()

        # add the svg geometry to the selected Gerber object solid_geometry and in obj.apertures, apid = 0
        if not isinstance(self.grb_object.solid_geometry, Iterable):
            self.grb_object.solid_geometry = list(self.grb_object.solid_geometry)

        # I use the utility geometry (self.qrcode_utility_geometry) because it is already buffered
        geo_list = self.grb_object.solid_geometry
        if isinstance(self.grb_object.solid_geometry, MultiPolygon):
            geo_list = list(self.grb_object.solid_geometry.geoms)

        # this is the bounding box of the QRCode geometry
        a, b, c, d = self.qrcode_utility_geometry.bounds
        buff_val = self.border_size_entry.get_value() * (self.bsize_entry.get_value() / 10)

        if self.bb_radio.get_value() == 'r':
            mask_geo = box(a, b, c, d).buffer(buff_val)
        else:
            mask_geo = box(a, b, c, d).buffer(buff_val, join_style=2)

        # update the solid geometry with the cutout (if it is the case)
        new_solid_geometry = list()
        offset_mask_geo = translate(mask_geo, xoff=pos[0], yoff=pos[1])
        for poly in geo_list:
            if poly.contains(offset_mask_geo):
                new_solid_geometry.append(poly.difference(offset_mask_geo))
            else:
                if poly not in new_solid_geometry:
                    new_solid_geometry.append(poly)

        geo_list = deepcopy(list(new_solid_geometry))

        # Polarity
        if self.pol_radio.get_value() == 'pos':
            working_geo = self.qrcode_utility_geometry
        else:
            working_geo = mask_geo.difference(self.qrcode_utility_geometry)

        try:
            for geo in working_geo:
                geo_list.append(translate(geo, xoff=pos[0], yoff=pos[1]))
        except TypeError:
            geo_list.append(translate(working_geo, xoff=pos[0], yoff=pos[1]))

        self.grb_object.solid_geometry = deepcopy(geo_list)

        box_size = float(self.bsize_entry.get_value()) / 10.0

        sort_apid = list()
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
            self.grb_object.apertures[new_apid] = dict()
            self.grb_object.apertures[new_apid]['geometry'] = list()
            self.grb_object.apertures[new_apid]['type'] = 'R'
            # TODO: HACK
            # I've artificially added 1% to the height and width because otherwise after loading the
            # exported file, it will not be correctly reconstructed (it will be made from multiple shapes instead of
            # one shape which show that the buffering didn't worked well). It may be the MM to INCH conversion.
            self.grb_object.apertures[new_apid]['height'] = deepcopy(box_size * 1.01)
            self.grb_object.apertures[new_apid]['width'] = deepcopy(box_size * 1.01)
            self.grb_object.apertures[new_apid]['size'] = deepcopy(math.sqrt(box_size ** 2 + box_size ** 2))

        if '0' not in self.grb_object.apertures:
            self.grb_object.apertures['0'] = dict()
            self.grb_object.apertures['0']['geometry'] = list()
            self.grb_object.apertures['0']['type'] = 'REG'
            self.grb_object.apertures['0']['size'] = 0.0

        # in case that the QRCode geometry is dropped onto a copper region (found in the '0' aperture)
        # make sure that I place a cutout there
        zero_elem = dict()
        zero_elem['clear'] = offset_mask_geo
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
                geo_elem = dict()
                geo_elem['solid'] = translate(geo, xoff=pos[0], yoff=pos[1])
                geo_elem['follow'] = translate(geo.centroid, xoff=pos[0], yoff=pos[1])
                self.grb_object.apertures[new_apid]['geometry'].append(deepcopy(geo_elem))
        except TypeError:
            geo_elem = dict()
            geo_elem['solid'] = self.qrcode_geometry
            self.grb_object.apertures[new_apid]['geometry'].append(deepcopy(geo_elem))

        # update the source file with the new geometry:
        self.grb_object.source_file = self.app.export_gerber(obj_name=self.grb_object.options['name'], filename=None,
                                                             local_use=self.grb_object, use_thread=False)

        self.replot()

    def draw_utility_geo(self, pos):

        # face = '#0000FF' + str(hex(int(0.2 * 255)))[2:]
        outline = '#0000FFAF'

        offset_geo = list()

        # I use the len of self.qrcode_geometry instead of the utility one because the complexity of the polygons is
        # better seen in this
        if len(self.qrcode_geometry) <= 330:
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
        if self.app.grid_status() == True:
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
            if self.app.grid_status() == True:
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
        geos = getsvggeo(svg_root, object_type)

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

    def replot(self):
        obj = self.grb_object

        def worker_task():
            with self.app.proc_container.new('%s...' % _("Plotting")):
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
