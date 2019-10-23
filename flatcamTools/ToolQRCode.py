# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtCore

from FlatCAMTool import FlatCAMTool
from flatcamGUI.GUIElements import RadioSet, FCTextArea, FCSpinner
from camlib import *

from shapely.geometry import Point
from shapely.geometry.base import *

import math
import io
from datetime import datetime
import logging
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

        grid_lay.addWidget(self.text_label, 5, 0)
        grid_lay.addWidget(self.text_data, 6, 0, 1, 2)

        # ## Create QRCode
        self.qrcode_button = QtWidgets.QPushButton(_("Create QRCode"))
        self.qrcode_button.setToolTip(
            _("Create the QRCode object.")
        )
        grid_lay.addWidget(self.qrcode_button, 7, 0, 1, 2)

        grid_lay.addWidget(QtWidgets.QLabel(''), 8, 0)

        self.layout.addStretch()

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

        # Signals #
        self.qrcode_button.clicked.connect(self.execute)

    def execute(self):

        text_data = self.text_data.get_value()
        if text_data == '':
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Cancelled. There is no QRCode Data in the text box."))
            return 'fail'

        svg_file = io.BytesIO()
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

        img = qr.make_image()
        img.save(svg_file)

        svg_text = StringIO(svg_file.getvalue().decode('UTF-8'))

        def obj_init(geo_obj, app_obj):
            geo_obj.import_svg(svg_text, units=self.units)
            geo_obj.solid_geometry = unary_union(geo_obj.solid_geometry).buffer(0.0000001)
            geo_obj.solid_geometry = geo_obj.solid_geometry.buffer(-0.0000001)

        with self.app.proc_container.new(_("Generating QRCode...")):
            # Object creation
            self.app.new_object('gerber', 'QRCode', obj_init, plot=True)

    def make(self):
        pass

    def utility_geo(self):
        pass

    def on_mouse_move(self, event):
        pass

    def on_mouse_release(self, event):
        pass
