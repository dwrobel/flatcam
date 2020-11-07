from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings

from appGUI.GUIElements import RadioSet, FCDoubleSpinner, FCComboBox2, FCCheckBox, NumericalEvalTupleEntry
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


class ToolsPaintPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "Paint Area Tool Options", parent=parent)
        super(ToolsPaintPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Paint Tool Options")))
        self.decimals = decimals

        # ------------------------------
        # ## Paint area
        # ------------------------------
        self.paint_label = QtWidgets.QLabel('<b>%s:</b>' % _('Parameters'))
        self.paint_label.setToolTip(
            _("Creates tool paths to cover the\n"
              "whole area of a polygon.")
        )
        self.layout.addWidget(self.paint_label)

        grid0 = QtWidgets.QGridLayout()
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        self.layout.addLayout(grid0)

        # Tool dia
        ptdlabel = QtWidgets.QLabel('<b><font color="green">%s:</font></b>' % _('Tools Dia'))
        ptdlabel.setToolTip(
            _("Diameters of the tools, separated by comma.\n"
              "The value of the diameter has to use the dot decimals separator.\n"
              "Valid values: 0.3, 1.0")
        )
        grid0.addWidget(ptdlabel, 0, 0)

        self.painttooldia_entry = NumericalEvalTupleEntry(border_color='#0069A9')
        self.painttooldia_entry.setPlaceholderText(_("Comma separated values"))

        grid0.addWidget(self.painttooldia_entry, 0, 1)

        # Tool Type Radio Button
        self.tool_type_label = QtWidgets.QLabel('%s:' % _('Tool Type'))
        self.tool_type_label.setToolTip(
            _("Default tool type:\n"
              "- 'V-shape'\n"
              "- Circular")
        )

        self.tool_type_radio = RadioSet([{'label': _('V-shape'), 'value': 'V'},
                                         {'label': _('Circular'), 'value': 'C1'}])

        self.tool_type_radio.setObjectName(_("Tool Type"))

        grid0.addWidget(self.tool_type_label, 1, 0)
        grid0.addWidget(self.tool_type_radio, 1, 1)

        # Tip Dia
        self.tipdialabel = QtWidgets.QLabel('%s:' % _('V-Tip Dia'))
        self.tipdialabel.setToolTip(
            _("The tip diameter for V-Shape Tool"))
        self.tipdia_entry = FCDoubleSpinner()
        self.tipdia_entry.set_precision(self.decimals)
        self.tipdia_entry.set_range(0.0000, 10000.0000)
        self.tipdia_entry.setSingleStep(0.1)
        self.tipdia_entry.setObjectName(_("V-Tip Dia"))

        grid0.addWidget(self.tipdialabel, 2, 0)
        grid0.addWidget(self.tipdia_entry, 2, 1)

        # Tip Angle
        self.tipanglelabel = QtWidgets.QLabel('%s:' % _('V-Tip Angle'))
        self.tipanglelabel.setToolTip(
            _("The tip angle for V-Shape Tool.\n"
              "In degree."))
        self.tipangle_entry = FCDoubleSpinner()
        self.tipangle_entry.set_precision(self.decimals)
        self.tipangle_entry.set_range(1.0000, 180.0000)
        self.tipangle_entry.setSingleStep(5)
        self.tipangle_entry.setObjectName(_("V-Tip Angle"))

        grid0.addWidget(self.tipanglelabel, 3, 0)
        grid0.addWidget(self.tipangle_entry, 3, 1)

        # Cut Z entry
        cutzlabel = QtWidgets.QLabel('%s:' % _('Cut Z'))
        cutzlabel.setToolTip(
            _("Depth of cut into material. Negative value.\n"
              "In application units.")
        )
        self.cutz_entry = FCDoubleSpinner()
        self.cutz_entry.set_precision(self.decimals)
        self.cutz_entry.set_range(-910000.0000, 0.0000)
        self.cutz_entry.setObjectName(_("Cut Z"))

        self.cutz_entry.setToolTip(
            _("Depth of cut into material. Negative value.\n"
              "In application units.")
        )
        grid0.addWidget(cutzlabel, 4, 0)
        grid0.addWidget(self.cutz_entry, 4, 1)

        # ### Tool Diameter ####
        self.newdialabel = QtWidgets.QLabel('%s:' % _('New Dia'))
        self.newdialabel.setToolTip(
            _("Diameter for the new tool to add in the Tool Table.\n"
              "If the tool is V-shape type then this value is automatically\n"
              "calculated from the other parameters.")
        )
        self.newdia_entry = FCDoubleSpinner()
        self.newdia_entry.set_precision(self.decimals)
        self.newdia_entry.set_range(0.000, 10000.0000)
        self.newdia_entry.setObjectName(_("Tool Dia"))

        grid0.addWidget(self.newdialabel, 5, 0)
        grid0.addWidget(self.newdia_entry, 5, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 6, 0, 1, 2)

        self.paint_order_label = QtWidgets.QLabel('%s:' % _('Tool order'))
        self.paint_order_label.setToolTip(_("This set the way that the tools in the tools table are used.\n"
                                            "'No' --> means that the used order is the one in the tool table\n"
                                            "'Forward' --> means that the tools will be ordered from small to big\n"
                                            "'Reverse' --> means that the tools will ordered from big to small\n\n"
                                            "WARNING: using rest machining will automatically set the order\n"
                                            "in reverse and disable this control."))

        self.paint_order_radio = RadioSet([{'label': _('No'), 'value': 'no'},
                                           {'label': _('Forward'), 'value': 'fwd'},
                                           {'label': _('Reverse'), 'value': 'rev'}])

        grid0.addWidget(self.paint_order_label, 7, 0)
        grid0.addWidget(self.paint_order_radio, 7, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 8, 0, 1, 2)

        # Overlap
        ovlabel = QtWidgets.QLabel('%s:' % _('Overlap'))
        ovlabel.setToolTip(
            _("How much (percentage) of the tool width to overlap each tool pass.\n"
              "Adjust the value starting with lower values\n"
              "and increasing it if areas that should be processed are still \n"
              "not processed.\n"
              "Lower values = faster processing, faster execution on CNC.\n"
              "Higher values = slow processing and slow execution on CNC\n"
              "due of too many paths.")
        )
        self.paintoverlap_entry = FCDoubleSpinner(suffix='%')
        self.paintoverlap_entry.set_precision(self.decimals)
        self.paintoverlap_entry.setWrapping(True)
        self.paintoverlap_entry.setRange(0.0000, 99.9999)
        self.paintoverlap_entry.setSingleStep(0.1)

        grid0.addWidget(ovlabel, 9, 0)
        grid0.addWidget(self.paintoverlap_entry, 9, 1)

        # Margin
        marginlabel = QtWidgets.QLabel('%s:' % _('Margin'))
        marginlabel.setToolTip(
            _("Distance by which to avoid\n"
              "the edges of the polygon to\n"
              "be painted.")
        )
        self.paintmargin_entry = FCDoubleSpinner()
        self.paintmargin_entry.set_range(-10000.0000, 10000.0000)
        self.paintmargin_entry.set_precision(self.decimals)
        self.paintmargin_entry.setSingleStep(0.1)

        grid0.addWidget(marginlabel, 10, 0)
        grid0.addWidget(self.paintmargin_entry, 10, 1)

        # Method
        methodlabel = QtWidgets.QLabel('%s:' % _('Method'))
        methodlabel.setToolTip(
            _("Algorithm for painting:\n"
              "- Standard: Fixed step inwards.\n"
              "- Seed-based: Outwards from seed.\n"
              "- Line-based: Parallel lines.\n"
              "- Laser-lines: Active only for Gerber objects.\n"
              "Will create lines that follow the traces.\n"
              "- Combo: In case of failure a new method will be picked from the above\n"
              "in the order specified.")
        )

        # self.paintmethod_combo = RadioSet([
        #     {"label": _("Standard"), "value": "standard"},
        #     {"label": _("Seed-based"), "value": "seed"},
        #     {"label": _("Straight lines"), "value": "lines"}
        # ], orientation='vertical', stretch=False)
        self.paintmethod_combo = FCComboBox2()
        self.paintmethod_combo.addItems(
            [_("Standard"), _("Seed"), _("Lines"), _("Laser_lines"), _("Combo")]
        )

        grid0.addWidget(methodlabel, 11, 0)
        grid0.addWidget(self.paintmethod_combo, 11, 1)

        # Connect lines
        self.pathconnect_cb = FCCheckBox('%s' % _("Connect"))
        self.pathconnect_cb.setToolTip(
            _("Draw lines between resulting\n"
              "segments to minimize tool lifts.")
        )
        grid0.addWidget(self.pathconnect_cb, 12, 0)

        # Paint contour
        self.contour_cb = FCCheckBox('%s' % _("Contour"))
        self.contour_cb.setToolTip(
            _("Cut around the perimeter of the polygon\n"
              "to trim rough edges.")
        )
        grid0.addWidget(self.contour_cb, 12, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 13, 0, 1, 2)

        self.rest_cb = FCCheckBox('%s' % _("Rest"))
        self.rest_cb.setObjectName(_("Rest"))
        self.rest_cb.setToolTip(
            _("If checked, use 'rest machining'.\n"
              "Basically it will process copper outside PCB features,\n"
              "using the biggest tool and continue with the next tools,\n"
              "from bigger to smaller, to process the copper features that\n"
              "could not be processed by previous tool, until there is\n"
              "nothing left to process or there are no more tools.\n\n"
              "If not checked, use the standard algorithm.")
        )
        grid0.addWidget(self.rest_cb, 14, 0, 1, 2)

        # Polygon selection
        selectlabel = QtWidgets.QLabel('%s:' % _('Selection'))
        selectlabel.setToolTip(
            _("Selection of area to be processed.\n"
              "- 'Polygon Selection' - left mouse click to add/remove polygons to be processed.\n"
              "- 'Area Selection' - left mouse click to start selection of the area to be processed.\n"
              "Keeping a modifier key pressed (CTRL or SHIFT) will allow to add multiple areas.\n"
              "- 'All Polygons' - the process will start after click.\n"
              "- 'Reference Object' - will process the area specified by another object.")
        )

        # self.selectmethod_combo = RadioSet(
        #     [
        #         {"label": _("Polygon Selection"), "value": "single"},
        #         {"label": _("Area Selection"), "value": "area"},
        #         {"label": _("All Polygons"), "value": "all"},
        #         {"label": _("Reference Object"), "value": "ref"}
        #     ],
        #     orientation='vertical',
        #     stretch=None
        # )
        self.selectmethod_combo = FCComboBox2()
        self.selectmethod_combo.addItems(
            [_("All"), _("Polygon Selection"), _("Area Selection"), _("Reference Object")]
        )

        grid0.addWidget(selectlabel, 15, 0)
        grid0.addWidget(self.selectmethod_combo, 15, 1)

        self.area_shape_label = QtWidgets.QLabel('%s:' % _("Shape"))
        self.area_shape_label.setToolTip(
            _("The kind of selection shape used for area selection.")
        )

        self.area_shape_radio = RadioSet([{'label': _("Square"), 'value': 'square'},
                                          {'label': _("Polygon"), 'value': 'polygon'}])

        grid0.addWidget(self.area_shape_label, 18, 0)
        grid0.addWidget(self.area_shape_radio, 18, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 19, 0, 1, 2)

        # ## Plotting type
        self.paint_plotting_radio = RadioSet([{'label': _('Normal'), 'value': 'normal'},
                                              {"label": _("Progressive"), "value": "progressive"}])
        plotting_label = QtWidgets.QLabel('%s:' % _("Plotting"))
        plotting_label.setToolTip(
            _("- 'Normal' - normal plotting, done at the end of the job\n"
              "- 'Progressive' - each shape is plotted after it is generated")
        )
        grid0.addWidget(plotting_label, 20, 0)
        grid0.addWidget(self.paint_plotting_radio, 20, 1)

        self.layout.addStretch()
