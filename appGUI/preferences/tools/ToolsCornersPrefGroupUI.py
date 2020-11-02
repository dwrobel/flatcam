from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings

from appGUI.GUIElements import FCDoubleSpinner, FCLabel, RadioSet
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


class ToolsCornersPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "Calculators Tool Options", parent=parent)
        super(ToolsCornersPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Corner Markers Options")))
        self.decimals = decimals

        grid0 = QtWidgets.QGridLayout()
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        self.layout.addLayout(grid0)

        self.param_label = FCLabel('<b>%s:</b>' % _('Parameters'))
        self.param_label.setToolTip(
            _("Parameters used for this tool.")
        )
        grid0.addWidget(self.param_label, 0, 0, 1, 2)

        # Type of Marker
        self.type_label = FCLabel('%s:' % _("Type"))
        self.type_label.setToolTip(
            _("Shape of the marker.")
        )

        self.type_radio = RadioSet([
            {"label": _("Semi-Cross"), "value": "s"},
            {"label": _("Cross"), "value": "c"},
        ])

        grid0.addWidget(self.type_label, 2, 0)
        grid0.addWidget(self.type_radio, 2, 1)
        
        # Thickness #
        self.thick_label = FCLabel('%s:' % _("Thickness"))
        self.thick_label.setToolTip(
            _("The thickness of the line that makes the corner marker.")
        )
        self.thick_entry = FCDoubleSpinner()
        self.thick_entry.set_range(0.0000, 9.9999)
        self.thick_entry.set_precision(self.decimals)
        self.thick_entry.setWrapping(True)
        self.thick_entry.setSingleStep(10 ** -self.decimals)

        grid0.addWidget(self.thick_label, 4, 0)
        grid0.addWidget(self.thick_entry, 4, 1)

        # Margin #
        self.margin_label = FCLabel('%s:' % _("Margin"))
        self.margin_label.setToolTip(
            _("Bounding box margin.")
        )
        self.margin_entry = FCDoubleSpinner()
        self.margin_entry.set_range(-10000.0000, 10000.0000)
        self.margin_entry.set_precision(self.decimals)
        self.margin_entry.setSingleStep(0.1)

        grid0.addWidget(self.margin_label, 6, 0)
        grid0.addWidget(self.margin_entry, 6, 1)

        # Length #
        self.l_label = FCLabel('%s:' % _("Length"))
        self.l_label.setToolTip(
            _("The length of the line that makes the corner marker.")
        )
        self.l_entry = FCDoubleSpinner()
        self.l_entry.set_range(-10000.0000, 10000.0000)
        self.l_entry.set_precision(self.decimals)
        self.l_entry.setSingleStep(10 ** -self.decimals)

        grid0.addWidget(self.l_label, 8, 0)
        grid0.addWidget(self.l_entry, 8, 1)

        # Drill Tool Diameter
        self.drill_dia_label = FCLabel('%s:' % _("Drill Dia"))
        self.drill_dia_label.setToolTip(
            '%s.' % _("Drill Diameter")
        )
        self.drill_dia_entry = FCDoubleSpinner()
        self.drill_dia_entry.set_range(0.0000, 100.0000)
        self.drill_dia_entry.set_precision(self.decimals)
        self.drill_dia_entry.setWrapping(True)

        grid0.addWidget(self.drill_dia_label, 10, 0)
        grid0.addWidget(self.drill_dia_entry, 10, 1)

        self.layout.addStretch()
