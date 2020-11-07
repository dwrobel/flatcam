from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings

from appGUI.GUIElements import FCDoubleSpinner, FCLabel
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


class ToolsCalculatorsPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "Calculators Tool Options", parent=parent)
        super(ToolsCalculatorsPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Calculators Tool Options")))
        self.decimals = decimals

        # ## V-shape Calculator Tool
        self.vshape_tool_label = FCLabel("<b>%s:</b>" % _("V-Shape Tool Calculator"))
        self.vshape_tool_label.setToolTip(
            _("Calculate the tool diameter for a given V-shape tool,\n"
              "having the tip diameter, tip angle and\n"
              "depth-of-cut as parameters.")
        )
        self.layout.addWidget(self.vshape_tool_label)

        grid0 = QtWidgets.QGridLayout()
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        self.layout.addLayout(grid0)

        # ## Tip Diameter
        self.tip_dia_entry = FCDoubleSpinner()
        self.tip_dia_entry.set_range(0.000001, 10000.0000)
        self.tip_dia_entry.set_precision(self.decimals)
        self.tip_dia_entry.setSingleStep(0.1)

        self.tip_dia_label = FCLabel('%s:' % _("Tip Diameter"))
        self.tip_dia_label.setToolTip(
            _("This is the tool tip diameter.\n"
              "It is specified by manufacturer.")
        )
        grid0.addWidget(self.tip_dia_label, 0, 0)
        grid0.addWidget(self.tip_dia_entry, 0, 1)

        # ## Tip angle
        self.tip_angle_entry = FCDoubleSpinner()
        self.tip_angle_entry.set_range(0.0, 180.0)
        self.tip_angle_entry.set_precision(self.decimals)
        self.tip_angle_entry.setSingleStep(5)

        self.tip_angle_label = FCLabel('%s:' % _("Tip Angle"))
        self.tip_angle_label.setToolTip(
            _("This is the angle on the tip of the tool.\n"
              "It is specified by manufacturer.")
        )
        grid0.addWidget(self.tip_angle_label, 2, 0)
        grid0.addWidget(self.tip_angle_entry, 2, 1)

        # ## Depth-of-cut Cut Z
        self.cut_z_entry = FCDoubleSpinner()
        self.cut_z_entry.set_range(-10000.0000, 0.0000)
        self.cut_z_entry.set_precision(self.decimals)
        self.cut_z_entry.setSingleStep(0.01)

        self.cut_z_label = FCLabel('%s:' % _("Cut Z"))
        self.cut_z_label.setToolTip(
            _("This is depth to cut into material.\n"
              "In the CNCJob object it is the CutZ parameter.")
        )
        grid0.addWidget(self.cut_z_label, 4, 0)
        grid0.addWidget(self.cut_z_entry, 4, 1)

        # ## Electroplating Calculator Tool
        self.plate_title_label = FCLabel("<b>%s:</b>" % _("ElectroPlating Calculator"))
        self.plate_title_label.setToolTip(
            _("This calculator is useful for those who plate the via/pad/drill holes,\n"
              "using a method like graphite ink or calcium hypophosphite ink or palladium chloride.")
        )
        grid0.addWidget(self.plate_title_label, 3, 0, 1, 2)

        # ## PCB Length
        self.pcblength_entry = FCDoubleSpinner()
        self.pcblength_entry.set_range(0.000001, 10000.0000)
        self.pcblength_entry.set_precision(self.decimals)
        self.pcblength_entry.setSingleStep(0.1)

        self.pcblengthlabel = FCLabel('%s:' % _("Board Length"))

        self.pcblengthlabel.setToolTip(_('This is the board length. In centimeters.'))
        grid0.addWidget(self.pcblengthlabel, 6, 0)
        grid0.addWidget(self.pcblength_entry, 6, 1)

        # ## PCB Width
        self.pcbwidth_entry = FCDoubleSpinner()
        self.pcbwidth_entry.set_range(0.000001, 10000.0000)
        self.pcbwidth_entry.set_precision(self.decimals)
        self.pcbwidth_entry.setSingleStep(0.1)

        self.pcbwidthlabel = FCLabel('%s:' % _("Board Width"))

        self.pcbwidthlabel.setToolTip(_('This is the board width.In centimeters.'))
        grid0.addWidget(self.pcbwidthlabel, 8, 0)
        grid0.addWidget(self.pcbwidth_entry, 8, 1)
        
        # AREA
        self.area_label = FCLabel('%s:' % _("Area"))
        self.area_label.setToolTip(_('This is the board area.'))
        self.area_entry = FCDoubleSpinner()
        self.area_entry.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)
        self.area_entry.set_precision(self.decimals)
        self.area_entry.set_range(0.0, 10000.0000)
        
        grid0.addWidget(self.area_label, 10, 0)
        grid0.addWidget(self.area_entry, 10, 1)
        
        # ## Current Density
        self.cdensity_label = FCLabel('%s:' % _("Current Density"))
        self.cdensity_entry = FCDoubleSpinner()
        self.cdensity_entry.set_range(0.000001, 10000.0000)
        self.cdensity_entry.set_precision(self.decimals)
        self.cdensity_entry.setSingleStep(0.1)

        self.cdensity_label.setToolTip(_("Current density to pass through the board. \n"
                                         "In Amps per Square Feet ASF."))
        grid0.addWidget(self.cdensity_label, 12, 0)
        grid0.addWidget(self.cdensity_entry, 12, 1)

        # ## PCB Copper Growth
        self.growth_label = FCLabel('%s:' % _("Copper Growth"))
        self.growth_entry = FCDoubleSpinner()
        self.growth_entry.set_range(0.000001, 10000.0000)
        self.growth_entry.set_precision(self.decimals)
        self.growth_entry.setSingleStep(0.01)

        self.growth_label.setToolTip(_("How thick the copper growth is intended to be.\n"
                                       "In microns."))
        grid0.addWidget(self.growth_label, 14, 0)
        grid0.addWidget(self.growth_entry, 14, 1)

        self.layout.addStretch()
