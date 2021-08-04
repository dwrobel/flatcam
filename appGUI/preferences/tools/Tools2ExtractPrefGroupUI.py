from PyQt6 import QtWidgets

from appGUI.GUIElements import FCCheckBox, RadioSet, FCDoubleSpinner, FCLabel
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


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

        self.param_label = FCLabel('<b>%s:</b>' % _('Parameters'))
        self.param_label.setToolTip(
            _("Parameters used for this tool.")
        )
        grid_lay.addWidget(self.param_label, 0, 0, 1, 2)

        self.padt_label = FCLabel("%s:" % _("Processed Pads Type"))
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
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        grid_lay.addWidget(separator_line, 8, 0, 1, 2)

        # Method of extraction
        self.method_radio = RadioSet(
            [
                {'label': _("Fixed Diameter"), 'value': 'fixed'},
                {'label': _("Fixed Annular Ring"), 'value': 'ring'},
                {'label': _("Proportional"), 'value': 'prop'}
            ],
            orientation='vertical',
            stretch=False)
        self.method_label = FCLabel('<b>%s:</b>' % _("Method"))
        self.method_label.setToolTip(
            _("The method for processing pads. Can be:\n"
              "- Fixed Diameter -> all holes will have a set size\n"
              "- Fixed Annular Ring -> all holes will have a set annular ring\n"
              "- Proportional -> each hole size will be a fraction of the pad size"))

        grid_lay.addWidget(self.method_label, 9, 0)
        grid_lay.addWidget(self.method_radio, 9, 1)

        # grid_lay1.addWidget(FCLabel(''))

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        grid_lay.addWidget(separator_line, 10, 0, 1, 2)

        # Annular Ring
        self.fixed_label = FCLabel('<b>%s</b>' % _("Fixed Diameter"))
        grid_lay.addWidget(self.fixed_label, 11, 0, 1, 2)

        # Diameter value
        self.dia_entry = FCDoubleSpinner()
        self.dia_entry.set_precision(self.decimals)
        self.dia_entry.set_range(0.0000, 10000.0000)

        self.dia_label = FCLabel('%s:' % _("Value"))
        self.dia_label.setToolTip(
            _("Fixed hole diameter.")
        )

        grid_lay.addWidget(self.dia_label, 12, 0)
        grid_lay.addWidget(self.dia_entry, 12, 1)

        # Annular Ring value
        self.ring_label = FCLabel('<b>%s</b>' % _("Fixed Annular Ring"))
        self.ring_label.setToolTip(
            _("The size of annular ring.\n"
              "The copper sliver between the hole exterior\n"
              "and the margin of the copper pad.")
        )
        grid_lay.addWidget(self.ring_label, 13, 0, 1, 2)

        # Circular Annular Ring Value
        self.circular_ring_label = FCLabel('%s:' % _("Circular"))
        self.circular_ring_label.setToolTip(
            _("The size of annular ring for circular pads.")
        )

        self.circular_ring_entry = FCDoubleSpinner()
        self.circular_ring_entry.set_precision(self.decimals)
        self.circular_ring_entry.set_range(0.0000, 10000.0000)

        grid_lay.addWidget(self.circular_ring_label, 14, 0)
        grid_lay.addWidget(self.circular_ring_entry, 14, 1)

        # Oblong Annular Ring Value
        self.oblong_ring_label = FCLabel('%s:' % _("Oblong"))
        self.oblong_ring_label.setToolTip(
            _("The size of annular ring for oblong pads.")
        )

        self.oblong_ring_entry = FCDoubleSpinner()
        self.oblong_ring_entry.set_precision(self.decimals)
        self.oblong_ring_entry.set_range(0.0000, 10000.0000)

        grid_lay.addWidget(self.oblong_ring_label, 15, 0)
        grid_lay.addWidget(self.oblong_ring_entry, 15, 1)

        # Square Annular Ring Value
        self.square_ring_label = FCLabel('%s:' % _("Square"))
        self.square_ring_label.setToolTip(
            _("The size of annular ring for square pads.")
        )

        self.square_ring_entry = FCDoubleSpinner()
        self.square_ring_entry.set_precision(self.decimals)
        self.square_ring_entry.set_range(0.0000, 10000.0000)

        grid_lay.addWidget(self.square_ring_label, 16, 0)
        grid_lay.addWidget(self.square_ring_entry, 16, 1)

        # Rectangular Annular Ring Value
        self.rectangular_ring_label = FCLabel('%s:' % _("Rectangular"))
        self.rectangular_ring_label.setToolTip(
            _("The size of annular ring for rectangular pads.")
        )

        self.rectangular_ring_entry = FCDoubleSpinner()
        self.rectangular_ring_entry.set_precision(self.decimals)
        self.rectangular_ring_entry.set_range(0.0000, 10000.0000)

        grid_lay.addWidget(self.rectangular_ring_label, 17, 0)
        grid_lay.addWidget(self.rectangular_ring_entry, 17, 1)

        # Others Annular Ring Value
        self.other_ring_label = FCLabel('%s:' % _("Others"))
        self.other_ring_label.setToolTip(
            _("The size of annular ring for other pads.")
        )

        self.other_ring_entry = FCDoubleSpinner()
        self.other_ring_entry.set_precision(self.decimals)
        self.other_ring_entry.set_range(0.0000, 10000.0000)

        grid_lay.addWidget(self.other_ring_label, 18, 0)
        grid_lay.addWidget(self.other_ring_entry, 18, 1)

        self.prop_label = FCLabel('<b>%s</b>' % _("Proportional Diameter"))
        grid_lay.addWidget(self.prop_label, 19, 0, 1, 2)

        # Factor value
        self.factor_entry = FCDoubleSpinner(suffix='%')
        self.factor_entry.set_precision(self.decimals)
        self.factor_entry.set_range(0.0000, 100.0000)
        self.factor_entry.setSingleStep(0.1)

        self.factor_label = FCLabel('%s:' % _("Factor"))
        self.factor_label.setToolTip(
            _("Proportional Diameter.\n"
              "The hole diameter will be a fraction of the pad size.")
        )

        grid_lay.addWidget(self.factor_label, 20, 0)
        grid_lay.addWidget(self.factor_entry, 20, 1)

        # EXTRACT SOLDERMASK
        self.extract_sm_label = FCLabel('<b>%s</b>' % _("Extract Soldermask"))
        self.extract_sm_label.setToolTip(
            _("Extract soldermask from a given Gerber file."))
        grid_lay.addWidget(self.extract_sm_label, 22, 0, 1, 2)

        # CLEARANCE soldermask extraction
        self.clearance_label = FCLabel('%s:' % _("Clearance"))
        self.clearance_label.setToolTip(
            _("This set how much the soldermask extends\n"
              "beyond the margin of the pads.")
        )
        self.clearance_entry = FCDoubleSpinner()
        self.clearance_entry.set_range(0.0000, 10000.0000)
        self.clearance_entry.set_precision(self.decimals)
        self.clearance_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.clearance_label, 24, 0)
        grid_lay.addWidget(self.clearance_entry, 24, 1)

        # EXTRACT CUTOUT
        self.extract_cut_label = FCLabel('<b>%s</b>' % _("Extract Cutout"))
        self.extract_cut_label.setToolTip(
            _("Extract a cutout from a given Gerber file."))
        grid_lay.addWidget(self.extract_cut_label, 26, 0, 1, 2)

        # Margin Cutout
        self.margin_cut_label = FCLabel('%s:' % _("Margin"))
        self.margin_cut_label.setToolTip(
            _("Margin over bounds. A positive value here\n"
              "will make the cutout of the PCB further from\n"
              "the actual PCB border")
        )
        self.margin_cut_entry = FCDoubleSpinner()
        self.margin_cut_entry.set_range(-10000.0000, 10000.0000)
        self.margin_cut_entry.set_precision(self.decimals)
        self.margin_cut_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.margin_cut_label, 28, 0)
        grid_lay.addWidget(self.margin_cut_entry, 28, 1)

        # Thickness Cutout
        self.thick_cut_label = FCLabel('%s:' % _("Thickness"))
        self.thick_cut_label.setToolTip(
            _("The thickness of the line that makes the cutout geometry.")
        )
        self.thick_cut_entry = FCDoubleSpinner()
        self.thick_cut_entry.set_range(0.0000, 10000.0000)
        self.thick_cut_entry.set_precision(self.decimals)
        self.thick_cut_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.thick_cut_label, 30, 0)
        grid_lay.addWidget(self.thick_cut_entry, 30, 1)
        
        self.layout.addStretch()
