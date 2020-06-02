from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings

from flatcamGUI.GUIElements import FCDoubleSpinner, RadioSet
from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

settings = QSettings("Open Source", "FlatCAM")
if settings.contains("machinist"):
    machinist_setting = settings.value('machinist', type=int)
else:
    machinist_setting = 0


class Tools2sidedPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "2sided Tool Options", parent=parent)
        super(Tools2sidedPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("2Sided Tool Options")))
        self.decimals = decimals

        # ## Board cuttout
        self.dblsided_label = QtWidgets.QLabel("<b>%s:</b>" % _("Parameters"))
        self.dblsided_label.setToolTip(
            _("A tool to help in creating a double sided\n"
              "PCB using alignment holes.")
        )
        self.layout.addWidget(self.dblsided_label)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        # ## Drill diameter for alignment holes
        self.drill_dia_entry = FCDoubleSpinner()
        self.drill_dia_entry.set_range(0.000001, 9999.9999)
        self.drill_dia_entry.set_precision(self.decimals)
        self.drill_dia_entry.setSingleStep(0.1)

        self.dd_label = QtWidgets.QLabel('%s:' % _("Drill dia"))
        self.dd_label.setToolTip(
            _("Diameter of the drill for the "
              "alignment holes.")
        )
        grid0.addWidget(self.dd_label, 0, 0)
        grid0.addWidget(self.drill_dia_entry, 0, 1)

        # ## Alignment Axis
        self.align_ax_label = QtWidgets.QLabel('%s:' % _("Align Axis"))
        self.align_ax_label.setToolTip(
            _("Mirror vertically (X) or horizontally (Y).")
        )
        self.align_axis_radio = RadioSet([{'label': 'X', 'value': 'X'},
                                          {'label': 'Y', 'value': 'Y'}])

        grid0.addWidget(self.align_ax_label, 1, 0)
        grid0.addWidget(self.align_axis_radio, 1, 1)

        # ## Axis
        self.mirror_axis_radio = RadioSet([{'label': 'X', 'value': 'X'},
                                           {'label': 'Y', 'value': 'Y'}])
        self.mirax_label = QtWidgets.QLabel(_("Mirror Axis:"))
        self.mirax_label.setToolTip(
            _("Mirror vertically (X) or horizontally (Y).")
        )

        self.empty_lb1 = QtWidgets.QLabel("")
        grid0.addWidget(self.empty_lb1, 2, 0)
        grid0.addWidget(self.mirax_label, 3, 0)
        grid0.addWidget(self.mirror_axis_radio, 3, 1)

        # ## Axis Location
        self.axis_location_radio = RadioSet([{'label': _('Point'), 'value': 'point'},
                                             {'label': _('Box'), 'value': 'box'}])
        self.axloc_label = QtWidgets.QLabel('%s:' % _("Axis Ref"))
        self.axloc_label.setToolTip(
            _("The axis should pass through a <b>point</b> or cut\n "
              "a specified <b>box</b> (in a FlatCAM object) through \n"
              "the center.")
        )

        grid0.addWidget(self.axloc_label, 4, 0)
        grid0.addWidget(self.axis_location_radio, 4, 1)

        self.layout.addStretch()
