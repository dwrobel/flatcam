from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings

from appGUI.GUIElements import FCCheckBox, RadioSet, FCDoubleSpinner
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


class Tools2EDrillsPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):

        super(Tools2EDrillsPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Extract Drills Options")))
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

        self.padt_label = QtWidgets.QLabel("<b>%s:</b>" % _("Processed Pads Type"))
        self.padt_label.setToolTip(
            _("The type of pads shape to be processed.\n"
              "If the PCB has many SMD pads with rectangular pads,\n"
              "disable the Rectangular aperture.")
        )

        grid_lay.addWidget(self.padt_label, 2, 0, 1, 2)

        # Circular Aperture Selection
        self.circular_cb = FCCheckBox('%s' % _("Circular"))
        self.circular_cb.setToolTip(
            _("Process Circular Pads.")
        )

        grid_lay.addWidget(self.circular_cb, 3, 0, 1, 2)

        # Oblong Aperture Selection
        self.oblong_cb = FCCheckBox('%s' % _("Oblong"))
        self.oblong_cb.setToolTip(
            _("Process Oblong Pads.")
        )

        grid_lay.addWidget(self.oblong_cb, 4, 0, 1, 2)

        # Square Aperture Selection
        self.square_cb = FCCheckBox('%s' % _("Square"))
        self.square_cb.setToolTip(
            _("Process Square Pads.")
        )

        grid_lay.addWidget(self.square_cb, 5, 0, 1, 2)

        # Rectangular Aperture Selection
        self.rectangular_cb = FCCheckBox('%s' % _("Rectangular"))
        self.rectangular_cb.setToolTip(
            _("Process Rectangular Pads.")
        )

        grid_lay.addWidget(self.rectangular_cb, 6, 0, 1, 2)

        # Others type of Apertures Selection
        self.other_cb = FCCheckBox('%s' % _("Others"))
        self.other_cb.setToolTip(
            _("Process pads not in the categories above.")
        )

        grid_lay.addWidget(self.other_cb, 7, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line, 8, 0, 1, 2)

        # ## Axis
        self.hole_size_radio = RadioSet(
            [
                {'label': _("Fixed Diameter"), 'value': 'fixed'},
                {'label': _("Fixed Annular Ring"), 'value': 'ring'},
                {'label': _("Proportional"), 'value': 'prop'}
            ],
            orientation='vertical',
            stretch=False)
        self.hole_size_label = QtWidgets.QLabel('<b>%s:</b>' % _("Method"))
        self.hole_size_label.setToolTip(
            _("The method for processing pads. Can be:\n"
              "- Fixed Diameter -> all holes will have a set size\n"
              "- Fixed Annular Ring -> all holes will have a set annular ring\n"
              "- Proportional -> each hole size will be a fraction of the pad size"))

        grid_lay.addWidget(self.hole_size_label, 9, 0)
        grid_lay.addWidget(self.hole_size_radio, 9, 1)

        # grid_lay1.addWidget(QtWidgets.QLabel(''))

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line, 10, 0, 1, 2)

        # Annular Ring
        self.fixed_label = QtWidgets.QLabel('<b>%s</b>' % _("Fixed Diameter"))
        grid_lay.addWidget(self.fixed_label, 11, 0, 1, 2)

        # Diameter value
        self.dia_entry = FCDoubleSpinner()
        self.dia_entry.set_precision(self.decimals)
        self.dia_entry.set_range(0.0000, 10000.0000)

        self.dia_label = QtWidgets.QLabel('%s:' % _("Value"))
        self.dia_label.setToolTip(
            _("Fixed hole diameter.")
        )

        grid_lay.addWidget(self.dia_label, 12, 0)
        grid_lay.addWidget(self.dia_entry, 12, 1)

        # Annular Ring value
        self.ring_label = QtWidgets.QLabel('<b>%s</b>' % _("Fixed Annular Ring"))
        self.ring_label.setToolTip(
            _("The size of annular ring.\n"
              "The copper sliver between the hole exterior\n"
              "and the margin of the copper pad.")
        )
        grid_lay.addWidget(self.ring_label, 13, 0, 1, 2)

        # Circular Annular Ring Value
        self.circular_ring_label = QtWidgets.QLabel('%s:' % _("Circular"))
        self.circular_ring_label.setToolTip(
            _("The size of annular ring for circular pads.")
        )

        self.circular_ring_entry = FCDoubleSpinner()
        self.circular_ring_entry.set_precision(self.decimals)
        self.circular_ring_entry.set_range(0.0000, 10000.0000)

        grid_lay.addWidget(self.circular_ring_label, 14, 0)
        grid_lay.addWidget(self.circular_ring_entry, 14, 1)

        # Oblong Annular Ring Value
        self.oblong_ring_label = QtWidgets.QLabel('%s:' % _("Oblong"))
        self.oblong_ring_label.setToolTip(
            _("The size of annular ring for oblong pads.")
        )

        self.oblong_ring_entry = FCDoubleSpinner()
        self.oblong_ring_entry.set_precision(self.decimals)
        self.oblong_ring_entry.set_range(0.0000, 10000.0000)

        grid_lay.addWidget(self.oblong_ring_label, 15, 0)
        grid_lay.addWidget(self.oblong_ring_entry, 15, 1)

        # Square Annular Ring Value
        self.square_ring_label = QtWidgets.QLabel('%s:' % _("Square"))
        self.square_ring_label.setToolTip(
            _("The size of annular ring for square pads.")
        )

        self.square_ring_entry = FCDoubleSpinner()
        self.square_ring_entry.set_precision(self.decimals)
        self.square_ring_entry.set_range(0.0000, 10000.0000)

        grid_lay.addWidget(self.square_ring_label, 16, 0)
        grid_lay.addWidget(self.square_ring_entry, 16, 1)

        # Rectangular Annular Ring Value
        self.rectangular_ring_label = QtWidgets.QLabel('%s:' % _("Rectangular"))
        self.rectangular_ring_label.setToolTip(
            _("The size of annular ring for rectangular pads.")
        )

        self.rectangular_ring_entry = FCDoubleSpinner()
        self.rectangular_ring_entry.set_precision(self.decimals)
        self.rectangular_ring_entry.set_range(0.0000, 10000.0000)

        grid_lay.addWidget(self.rectangular_ring_label, 17, 0)
        grid_lay.addWidget(self.rectangular_ring_entry, 17, 1)

        # Others Annular Ring Value
        self.other_ring_label = QtWidgets.QLabel('%s:' % _("Others"))
        self.other_ring_label.setToolTip(
            _("The size of annular ring for other pads.")
        )

        self.other_ring_entry = FCDoubleSpinner()
        self.other_ring_entry.set_precision(self.decimals)
        self.other_ring_entry.set_range(0.0000, 10000.0000)

        grid_lay.addWidget(self.other_ring_label, 18, 0)
        grid_lay.addWidget(self.other_ring_entry, 18, 1)

        self.prop_label = QtWidgets.QLabel('<b>%s</b>' % _("Proportional Diameter"))
        grid_lay.addWidget(self.prop_label, 19, 0, 1, 2)

        # Factor value
        self.factor_entry = FCDoubleSpinner(suffix='%')
        self.factor_entry.set_precision(self.decimals)
        self.factor_entry.set_range(0.0000, 100.0000)
        self.factor_entry.setSingleStep(0.1)

        self.factor_label = QtWidgets.QLabel('%s:' % _("Factor"))
        self.factor_label.setToolTip(
            _("Proportional Diameter.\n"
              "The hole diameter will be a fraction of the pad size.")
        )

        grid_lay.addWidget(self.factor_label, 20, 0)
        grid_lay.addWidget(self.factor_entry, 20, 1)

        self.layout.addStretch()
