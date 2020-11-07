from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings

from appGUI.GUIElements import FCDoubleSpinner, RadioSet
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

settings = QSettings("Open Source", "FlatCAM")
if settings.contains("machinist"):
    machinist_setting = settings.value('machinist', type=int)
else:
    machinist_setting = 0


class Tools2FiducialsPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):

        super(Tools2FiducialsPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Fiducials Tool Options")))
        self.decimals = decimals

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

        # DIAMETER #
        self.dia_label = QtWidgets.QLabel('%s:' % _("Size"))
        self.dia_label.setToolTip(
            _("This set the fiducial diameter if fiducial type is circular,\n"
              "otherwise is the size of the fiducial.\n"
              "The soldermask opening is double than that.")
        )
        self.dia_entry = FCDoubleSpinner()
        self.dia_entry.set_range(1.0000, 3.0000)
        self.dia_entry.set_precision(self.decimals)
        self.dia_entry.setWrapping(True)
        self.dia_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.dia_label, 1, 0)
        grid_lay.addWidget(self.dia_entry, 1, 1)

        # MARGIN #
        self.margin_label = QtWidgets.QLabel('%s:' % _("Margin"))
        self.margin_label.setToolTip(
            _("Bounding box margin.")
        )
        self.margin_entry = FCDoubleSpinner()
        self.margin_entry.set_range(-10000.0000, 10000.0000)
        self.margin_entry.set_precision(self.decimals)
        self.margin_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.margin_label, 2, 0)
        grid_lay.addWidget(self.margin_entry, 2, 1)

        # Mode #
        self.mode_radio = RadioSet([
            {'label': _('Auto'), 'value': 'auto'},
            {"label": _("Manual"), "value": "manual"}
        ], stretch=False)
        self.mode_label = QtWidgets.QLabel('%s:' % _("Mode"))
        self.mode_label.setToolTip(
            _("- 'Auto' - automatic placement of fiducials in the corners of the bounding box.\n"
              "- 'Manual' - manual placement of fiducials.")
        )
        grid_lay.addWidget(self.mode_label, 3, 0)
        grid_lay.addWidget(self.mode_radio, 3, 1)

        # Position for second fiducial #
        self.pos_radio = RadioSet([
            {'label': _('Up'), 'value': 'up'},
            {"label": _("Down"), "value": "down"},
            {"label": _("None"), "value": "no"}
        ], stretch=False)
        self.pos_label = QtWidgets.QLabel('%s:' % _("Second fiducial"))
        self.pos_label.setToolTip(
            _("The position for the second fiducial.\n"
              "- 'Up' - the order is: bottom-left, top-left, top-right.\n"
              "- 'Down' - the order is: bottom-left, bottom-right, top-right.\n"
              "- 'None' - there is no second fiducial. The order is: bottom-left, top-right.")
        )
        grid_lay.addWidget(self.pos_label, 4, 0)
        grid_lay.addWidget(self.pos_radio, 4, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line, 5, 0, 1, 2)

        # Fiducial type #
        self.fid_type_radio = RadioSet([
            {'label': _('Circular'), 'value': 'circular'},
            {"label": _("Cross"), "value": "cross"},
            {"label": _("Chess"), "value": "chess"}
        ], stretch=False)

        self.fid_type_label = QtWidgets.QLabel('%s:' % _("Fiducial Type"))
        self.fid_type_label.setToolTip(
            _("The type of fiducial.\n"
              "- 'Circular' - this is the regular fiducial.\n"
              "- 'Cross' - cross lines fiducial.\n"
              "- 'Chess' - chess pattern fiducial.")
        )
        grid_lay.addWidget(self.fid_type_label, 6, 0)
        grid_lay.addWidget(self.fid_type_radio, 6, 1)

        # Line Thickness #
        self.line_thickness_label = QtWidgets.QLabel('%s:' % _("Line thickness"))
        self.line_thickness_label.setToolTip(
            _("Bounding box margin.")
        )
        self.line_thickness_entry = FCDoubleSpinner()
        self.line_thickness_entry.set_range(0.00001, 10000.0000)
        self.line_thickness_entry.set_precision(self.decimals)
        self.line_thickness_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.line_thickness_label, 7, 0)
        grid_lay.addWidget(self.line_thickness_entry, 7, 1)

        self.layout.addStretch()
