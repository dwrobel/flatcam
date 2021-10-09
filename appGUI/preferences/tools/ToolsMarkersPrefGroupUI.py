from PyQt6 import QtWidgets

from appGUI.GUIElements import FCDoubleSpinner, FCLabel, RadioSet, FCGridLayout, FCFrame
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ToolsMarkersPrefGroupUI(OptionsGroupUI):
    def __init__(self, defaults, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "Calculators Plugin", parent=parent)
        super(ToolsMarkersPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Markers Options")))
        self.decimals = decimals
        self.defaults = defaults

        # #############################################################################################################
        # PARAMETERS Frame
        # #############################################################################################################
        self.param_label = FCLabel('<span style="color:blue;"><b>%s</b></span>' % _('Parameters'))
        self.param_label.setToolTip(
            _("Parameters used for this tool.")
        )
        self.layout.addWidget(self.param_label)

        param_frame = FCFrame()
        self.layout.addWidget(param_frame)

        param_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        param_frame.setLayout(param_grid)

        # Type of Marker
        self.type_label = FCLabel('%s:' % _("Type"))
        self.type_label.setToolTip(
            _("Shape of the marker.")
        )

        self.type_radio = RadioSet([
            {"label": _("Semi-Cross"), "value": "s"},
            {"label": _("Cross"), "value": "c"},
        ])

        param_grid.addWidget(self.type_label, 2, 0)
        param_grid.addWidget(self.type_radio, 2, 1)
        
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

        param_grid.addWidget(self.thick_label, 4, 0)
        param_grid.addWidget(self.thick_entry, 4, 1)

        # Margin X #
        self.marginx_label = FCLabel('%s X:' % _("Margin"))
        self.marginx_label.setToolTip(
            _("Bounding box margin.")
        )
        self.marginx_entry = FCDoubleSpinner()
        self.marginx_entry.set_range(-10000.0000, 10000.0000)
        self.marginx_entry.set_precision(self.decimals)
        self.marginx_entry.setSingleStep(0.1)

        param_grid.addWidget(self.marginx_label, 6, 0)
        param_grid.addWidget(self.marginx_entry, 6, 1)

        # Margin Y #
        self.marginy_label = FCLabel('%s Y:' % _("Margin"))
        self.marginy_label.setToolTip(
            _("Bounding box margin.")
        )
        self.marginy_entry = FCDoubleSpinner()
        self.marginy_entry.set_range(-10000.0000, 10000.0000)
        self.marginy_entry.set_precision(self.decimals)
        self.marginy_entry.setSingleStep(0.1)

        param_grid.addWidget(self.marginy_label, 8, 0)
        param_grid.addWidget(self.marginy_entry, 8, 1)

        # Length #
        self.l_label = FCLabel('%s:' % _("Length"))
        self.l_label.setToolTip(
            _("The length of the line that makes the corner marker.")
        )
        self.l_entry = FCDoubleSpinner()
        self.l_entry.set_range(-10000.0000, 10000.0000)
        self.l_entry.set_precision(self.decimals)
        self.l_entry.setSingleStep(10 ** -self.decimals)

        param_grid.addWidget(self.l_label, 10, 0)
        param_grid.addWidget(self.l_entry, 10, 1)

        # Drill Tool Diameter
        self.drill_dia_label = FCLabel('%s:' % _("Drill Dia"))
        self.drill_dia_label.setToolTip(
            '%s.' % _("Drill Diameter")
        )
        self.drill_dia_entry = FCDoubleSpinner()
        self.drill_dia_entry.set_range(0.0000, 100.0000)
        self.drill_dia_entry.set_precision(self.decimals)
        self.drill_dia_entry.setWrapping(True)

        param_grid.addWidget(self.drill_dia_label, 12, 0)
        param_grid.addWidget(self.drill_dia_entry, 12, 1)

        self.layout.addStretch()
