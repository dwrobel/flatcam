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

from shapely.geometry import Point
from shapely.geometry.base import *
from shapely.ops import unary_union
from shapely.affinity import translate

from io import StringIO, BytesIO
from collections import Iterable
import logging
import qrcode
import qrcode.image.svg
from lxml import etree as ET
from copy import copy, deepcopy

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
              "Default value is 4.")
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
            _("Parameter that controls the error correction used for the QR Code.\n"
              "L = maximum 7% errors can be corrected\n"
              "M = maximum 15% errors can be corrected\n"
              "Q = maximum 25% errors can be corrected\n"
              "H = maximum 30% errors can be corrected.")
        )
        self.pol_radio = RadioSet([{'label': _('Negative'), 'value': 'neg'},
                                   {'label': _('Positive'), 'value': 'pos'}])
        self.error_radio.setToolTip(
            _("Choose the type of QRCode to be created.\n"
              "If added on a Silkscreen Gerber you may add\n"
              "it as positive. If you add it to a Copper\n"
              "Gerber then perhaps you can add it as positive.")
        )
        grid_lay.addWidget(self.pol_label, 7, 0)
        grid_lay.addWidget(self.pol_radio, 7, 1)

        # BOUNDARY THICKNESS #
        self.boundary_label = QtWidgets.QLabel('%s:' % _("Boundary Thickness"))
        self.boundary_label.setToolTip(
            _("The width of the clearance around the QRCode.")
        )
        self.boundary_entry = FCDoubleSpinner()
        self.boundary_entry.set_range(0.0, 9999.9999)
        self.boundary_entry.set_precision(self.decimals)
        self.boundary_entry.setWrapping(True)

        grid_lay.addWidget(self.boundary_label, 8, 0)
        grid_lay.addWidget(self.boundary_entry, 8, 1)

        # ## Create QRCode
        self.qrcode_button = QtWidgets.QPushButton(_("Create QRCode"))
        self.qrcode_button.setToolTip(
            _("Create the QRCode object.")
        )
        grid_lay.addWidget(self.qrcode_button, 9, 0, 1, 2)
        grid_lay.addWidget(QtWidgets.QLabel(''), 10, 0)

        self.layout.addStretch()

        self.clicked_move = 0

        self.point1 = None
        self.point2 = None

        self.mm = None
        self.mr = None
        self.kr = None

        self.shapes = self.app.move_tool.sel_shapes
        self.qrcode_geometry = list()

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

        # Signals #
        self.qrcode_button.clicked.connect(self.execute)

    def execute(self):

        text_data = self.text_data.get_value()
        if text_data == '':
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Cancelled. There is no QRCode Data in the text box."))
            return 'fail'

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
        svg_geometry = unary_union(svg_geometry).buffer(0.0000001).buffer(-0.0000001)

        self.qrcode_geometry = svg_geometry

        # def obj_init(geo_obj, app_obj):
        #     geo_obj.solid_geometry = svg_geometry
        #
        # with self.app.proc_container.new(_("Generating QRCode...")):
        #     # Object creation
        #     self.app.new_object('gerber', 'QRCode', obj_init, plot=True)

        # if we have an object selected then we can safely activate the mouse events
        self.mm = self.app.plotcanvas.graph_event_connect('mouse_move', self.on_mouse_move)
        self.mr = self.app.plotcanvas.graph_event_connect('mouse_release', self.on_mouse_release)
        self.kr = self.app.plotcanvas.graph_event_connect('key_release', self.on_key_release)

    def make(self, pos):
        if self.app.is_legacy is False:
            self.app.plotcanvas.graph_event_disconnect('mouse_move', self.on_mouse_move)
            self.app.plotcanvas.graph_event_disconnect('mouse_release', self.on_mouse_release)
            self.app.plotcanvas.graph_event_disconnect('key_release', self.on_key_release)
        else:
            self.app.plotcanvas.graph_event_disconnect(self.mm)
            self.app.plotcanvas.graph_event_disconnect(self.mr)
            self.app.plotcanvas.graph_event_disconnect(self.kr)

        self.clicked_move = 0

        # delete the utility geometry
        self.delete_utility_geo()

        # add the svg geometry to the selected Gerber object solid_geometry and in obj.apertures, apid = 0

    def draw_utility_geo(self, pos):

        face = '#0000FF' + str(hex(int(0.2 * 255)))[2:]
        outline = '#0000FFAF'

        offset_geo = list()

        try:
            for poly in self.qrcode_geometry:
                offset_geo.append(translate(poly.exterior, xoff=pos[0], yoff=pos[1]))
                for geo_int in poly.interiors:
                    offset_geo.append(translate(geo_int, xoff=pos[0], yoff=pos[1]))
        except TypeError:
            offset_geo.append(translate(self.qrcode_geometry.exterior, xoff=pos[0], yoff=pos[1]))
            for geo_int in self.qrcode_geometry.interiors:
                offset_geo.append(translate(geo_int, xoff=pos[0], yoff=pos[1]))

        for shape in offset_geo:
            self.shapes.add(shape, color=outline, face_color=face, update=True, layer=0, tolerance=None)

        if self.app.is_legacy is True:
            self.shapes.redraw()

    def delete_utility_geo(self):
        self.shapes.clear()
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

        if self.point1 is None:
            dx = pos[0]
            dy = pos[1]
        else:
            dx = pos[0] - self.point1[0]
            dy = pos[1] - self.point1[1]

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
            if self.clicked_move == 0:

                # if GRID is active we need to get the snapped positions
                if self.app.grid_status() == True:
                    pos = self.app.geo_editor.snap(pos_canvas[0], pos_canvas[1])
                else:
                    pos = pos_canvas

                if self.point1 is None:
                    self.point1 = pos
                else:
                    self.point2 = copy(self.point1)
                    self.point1 = pos
                self.app.inform.emit(_("Click on the Destination point ..."))

            if self.clicked_move == 1:
                self.delete_utility_geo()

                # if GRID is active we need to get the snapped positions
                if self.app.grid_status() == True:
                    pos = self.app.geo_editor.snap(pos_canvas[0], pos_canvas[1])
                else:
                    pos = pos_canvas

                dx = pos[0] - self.point1[0]
                dy = pos[1] - self.point1[1]

                self.make(pos=(dx, dy))
                self.clicked_move = 0
                return


            self.clicked_move = 1

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

    def flatten_list(self, list):
        for item in list:
            if isinstance(item, Iterable) and not isinstance(item, (str, bytes)):
                yield from self.flatten_list(item)
            else:
                yield item

    def replot(self):
        obj = self.grb_object_combo

        def worker_task():
            with self.app.proc_container.new('%s...' % _("Plotting")):
                obj.plot()

        self.app.worker_task.emit({'fcn': worker_task, 'params': []})
