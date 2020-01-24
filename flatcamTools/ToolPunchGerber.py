# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 1/24/2020                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtGui, QtCore, QtWidgets

from FlatCAMTool import FlatCAMTool
from flatcamGUI.GUIElements import RadioSet, FCDoubleSpinner, FCCheckBox, \
    OptionalHideInputSection, OptionalInputSection, FCComboBox

from copy import deepcopy
import logging
from shapely.geometry import Polygon, MultiPolygon, Point

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
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class ToolPunchGerber(FlatCAMTool):

    toolName = _("Punch Gerber")

    def __init__(self, app):
        FlatCAMTool.__init__(self, app)

        self.decimals = self.app.decimals

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

        # Punch Drill holes
        self.layout.addWidget(QtWidgets.QLabel(""))

        # ## Grid Layout
        grid_lay = QtWidgets.QGridLayout()
        self.layout.addLayout(grid_lay)
        grid_lay.setColumnStretch(0, 1)
        grid_lay.setColumnStretch(1, 0)

        # ## Gerber Object
        self.gerber_object_combo = QtWidgets.QComboBox()
        self.gerber_object_combo.setModel(self.app.collection)
        self.gerber_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.gerber_object_combo.setCurrentIndex(1)

        self.grb_label = QtWidgets.QLabel("<b>%s:</b>" % _("GERBER"))
        self.grb_label.setToolTip('%s.' % _("Gerber into which to punch holes"))

        grid_lay.addWidget(self.grb_label, 0, 0, 1, 2)
        grid_lay.addWidget(self.gerber_object_combo, 1, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line, 2, 0, 1, 2)

        # Grid Layout
        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)

        self.method_label = QtWidgets.QLabel('%s:' % _("Method"))
        self.method_label.setToolTip(
            _("The punch hole source can be:\n"
              "- Excellon -> an Excellon holes center will serve as reference.\n"
              "- Fixed Diameter -> will try to use the pads center as reference.\n"
              "- Fixed Annular Ring -> will try to use the pads center as reference.\n"
              "- Proportional -> will try to use the pads center as reference.\n")
        )
        self.method_punch = RadioSet(
            [
                {'label': _('Excellon'), 'value': 'exc'},
                {'label': _("Fixed Diameter"), 'value': 'fixed'},
                {'label': _("Fixed Annular Ring"), 'value': 'ring'},
                {'label': _("Proportional"), 'value': 'prop'}
            ],
            orientation='vertical',
            stretch=False)
        grid0.addWidget(self.method_label, 0, 0)
        grid0.addWidget(self.method_punch, 0, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 1, 0, 1, 2)

        self.exc_label = QtWidgets.QLabel('<b>%s</b>' % _("Excellon"))
        self.exc_label.setToolTip(
            _("Remove the geometry of Excellon from the Gerber to create the holes in pads.")
        )

        self.exc_combo = QtWidgets.QComboBox()
        self.exc_combo.setModel(self.app.collection)
        self.exc_combo.setRootModelIndex(self.app.collection.index(1, 0, QtCore.QModelIndex()))
        self.exc_combo.setCurrentIndex(1)

        grid0.addWidget(self.exc_label, 2, 0, 1, 2)
        grid0.addWidget(self.exc_combo, 3, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 5, 0, 1, 2)

        # Fixed Dia
        self.fixed_label = QtWidgets.QLabel('<b>%s</b>' % _("Fixed Diameter"))
        grid0.addWidget(self.fixed_label, 6, 0, 1, 2)

        # Diameter value
        self.dia_entry = FCDoubleSpinner()
        self.dia_entry.set_precision(self.decimals)
        self.dia_entry.set_range(0.0000, 9999.9999)

        self.dia_label = QtWidgets.QLabel('%s:' % _("Value"))
        self.dia_label.setToolTip(
            _("Fixed hole diameter.")
        )

        grid0.addWidget(self.dia_label, 8, 0)
        grid0.addWidget(self.dia_entry, 8, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 9, 0, 1, 2)

        self.ring_frame = QtWidgets.QFrame()
        self.ring_frame.setContentsMargins(0, 0, 0, 0)
        grid0.addWidget(self.ring_frame, 10, 0, 1, 2)

        self.ring_box = QtWidgets.QVBoxLayout()
        self.ring_box.setContentsMargins(0, 0, 0, 0)
        self.ring_frame.setLayout(self.ring_box)

        # ## Grid Layout
        grid1 = QtWidgets.QGridLayout()
        grid1.setColumnStretch(0, 0)
        grid1.setColumnStretch(1, 1)
        self.ring_box.addLayout(grid1)

        # Annular Ring value
        self.ring_label = QtWidgets.QLabel('<b>%s</b>' % _("Fixed Annular Ring"))
        self.ring_label.setToolTip(
            _("The size of annular ring.\n"
              "The copper sliver between the drill hole exterior\n"
              "and the margin of the copper pad.")
        )
        grid1.addWidget(self.ring_label, 0, 0, 1, 2)

        # Circular Annular Ring Value
        self.circular_ring_label = QtWidgets.QLabel('%s:' % _("Circular"))
        self.circular_ring_label.setToolTip(
            _("The size of annular ring for circular pads.")
        )

        self.circular_ring_entry = FCDoubleSpinner()
        self.circular_ring_entry.set_precision(self.decimals)
        self.circular_ring_entry.set_range(0.0000, 9999.9999)

        grid1.addWidget(self.circular_ring_label, 1, 0)
        grid1.addWidget(self.circular_ring_entry, 1, 1)

        # Oblong Annular Ring Value
        self.oblong_ring_label = QtWidgets.QLabel('%s:' % _("Oblong"))
        self.oblong_ring_label.setToolTip(
            _("The size of annular ring for oblong pads.")
        )

        self.oblong_ring_entry = FCDoubleSpinner()
        self.oblong_ring_entry.set_precision(self.decimals)
        self.oblong_ring_entry.set_range(0.0000, 9999.9999)

        grid1.addWidget(self.oblong_ring_label, 2, 0)
        grid1.addWidget(self.oblong_ring_entry, 2, 1)

        # Square Annular Ring Value
        self.square_ring_label = QtWidgets.QLabel('%s:' % _("Square"))
        self.square_ring_label.setToolTip(
            _("The size of annular ring for square pads.")
        )

        self.square_ring_entry = FCDoubleSpinner()
        self.square_ring_entry.set_precision(self.decimals)
        self.square_ring_entry.set_range(0.0000, 9999.9999)

        grid1.addWidget(self.square_ring_label, 3, 0)
        grid1.addWidget(self.square_ring_entry, 3, 1)

        # Rectangular Annular Ring Value
        self.rectangular_ring_label = QtWidgets.QLabel('%s:' % _("Rectangular"))
        self.rectangular_ring_label.setToolTip(
            _("The size of annular ring for rectangular pads.")
        )

        self.rectangular_ring_entry = FCDoubleSpinner()
        self.rectangular_ring_entry.set_precision(self.decimals)
        self.rectangular_ring_entry.set_range(0.0000, 9999.9999)

        grid1.addWidget(self.rectangular_ring_label, 4, 0)
        grid1.addWidget(self.rectangular_ring_entry, 4, 1)

        # Others Annular Ring Value
        self.other_ring_label = QtWidgets.QLabel('%s:' % _("Others"))
        self.other_ring_label.setToolTip(
            _("The size of annular ring for other pads.")
        )

        self.other_ring_entry = FCDoubleSpinner()
        self.other_ring_entry.set_precision(self.decimals)
        self.other_ring_entry.set_range(0.0000, 9999.9999)

        grid1.addWidget(self.other_ring_label, 5, 0)
        grid1.addWidget(self.other_ring_entry, 5, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 11, 0, 1, 2)

        # Proportional value
        self.prop_label = QtWidgets.QLabel('<b>%s</b>' % _("Proportional Diameter"))
        grid0.addWidget(self.prop_label, 12, 0, 1, 2)

        # Diameter value
        self.factor_entry = FCDoubleSpinner(suffix='%')
        self.factor_entry.set_precision(self.decimals)
        self.factor_entry.set_range(0.0000, 100.0000)
        self.factor_entry.setSingleStep(0.1)

        self.factor_label = QtWidgets.QLabel('%s:' % _("Value"))
        self.factor_label.setToolTip(
            _("Proportional Diameter.\n"
              "The drill diameter will be a fraction of the pad size.")
        )

        grid0.addWidget(self.factor_label, 13, 0)
        grid0.addWidget(self.factor_entry, 13, 1)

        separator_line3 = QtWidgets.QFrame()
        separator_line3.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line3.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line3, 14, 0, 1, 2)

        # Buttons
        self.punch_object_button = QtWidgets.QPushButton(_("Punch Gerber"))
        self.punch_object_button.setToolTip(
            _("Create a Gerber object from the selected object, within\n"
              "the specified box.")
        )
        self.punch_object_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)
        self.layout.addWidget(self.punch_object_button)

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

        self.units = self.app.defaults['units']

        # ## Signals

        self.method_punch.activated_custom.connect(self.on_method)
        self.reset_button.clicked.connect(self.set_tool_ui)

    def run(self, toggle=True):
        self.app.report_usage("ToolPunchGerber()")

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

        self.app.ui.notebook.setTabText(2, _("Punch Tool"))

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, shortcut='ALT+H', **kwargs)

    def set_tool_ui(self):
        self.reset_fields()

        self.method_punch.set_value('exc')

    def on_method(self, val):
        self.exc_label.setEnabled(False)
        self.exc_combo.setEnabled(False)
        self.fixed_label.setEnabled(False)
        self.dia_label.setEnabled(False)
        self.dia_entry.setEnabled(False)
        self.ring_frame.setEnabled(False)
        self.prop_label.setEnabled(False)
        self.factor_label.setEnabled(False)
        self.factor_entry.setEnabled(False)

        if val == 'exc':
            self.exc_label.setEnabled(True)
            self.exc_combo.setEnabled(True)
        elif val == 'fixed':
            self.fixed_label.setEnabled(True)
            self.dia_label.setEnabled(True)
            self.dia_entry.setEnabled(True)
        elif val == 'ring':
            self.ring_frame.setEnabled(True)
        elif val == 'prop':
            self.prop_label.setEnabled(True)
            self.factor_label.setEnabled(True)
            self.factor_entry.setEnabled(True)

    def reset_fields(self):
        self.gerber_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.exc_combo.setRootModelIndex(self.app.collection.index(1, 0, QtCore.QModelIndex()))
