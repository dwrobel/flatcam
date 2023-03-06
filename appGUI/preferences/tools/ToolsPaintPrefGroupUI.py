
from PyQt6 import QtWidgets

from appGUI.GUIElements import RadioSet, FCDoubleSpinner, FCComboBox2, FCCheckBox, NumericalEvalTupleEntry, FCLabel, \
    GLay, FCFrame
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ToolsPaintPrefGroupUI(OptionsGroupUI):
    def __init__(self, app, parent=None):
        # OptionsGroupUI.__init__(self, "Paint Area Plugin", parent=parent)
        super(ToolsPaintPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Paint Plugin")))
        self.decimals = app.decimals
        self.options = app.options

        # ------------------------------
        # ## Paint area
        # ------------------------------
        self.paint_label = FCLabel('%s' % _("Parameters"), color='blue', bold=True)
        self.paint_label.setToolTip(
            _("Creates tool paths to cover the\n"
              "whole area of a polygon.")
        )
        self.layout.addWidget(self.paint_label)

        # #############################################################################################################
        # Parameters Frame
        # #############################################################################################################
        par_frame = FCFrame()
        self.layout.addWidget(par_frame)

        param_grid = GLay(v_spacing=5, h_spacing=3)
        par_frame.setLayout(param_grid)

        # Tool dia
        ptdlabel = FCLabel('%s:' % _('Tools Dia'), color='green', bold=True)
        ptdlabel.setToolTip(
            _("Diameters of the tools, separated by comma.\n"
              "The value of the diameter has to use the dot decimals separator.\n"
              "Valid values: 0.3, 1.0")
        )
        param_grid.addWidget(ptdlabel, 0, 0)

        self.painttooldia_entry = NumericalEvalTupleEntry(border_color='#0069A9')
        self.painttooldia_entry.setPlaceholderText(_("Comma separated values"))

        param_grid.addWidget(self.painttooldia_entry, 0, 1)

        self.paint_order_label = FCLabel('%s:' % _('Tool order'))
        self.paint_order_label.setToolTip(_("This set the way that the tools in the tools table are used.\n"
                                            "'Default' --> means that the used order is the one in the tool table\n"
                                            "'Forward' --> means that the tools will be ordered from small to big\n"
                                            "'Reverse' --> means that the tools will ordered from big to small\n\n"
                                            "WARNING: using rest machining will automatically set the order\n"
                                            "in reverse and disable this control."))

        self.paint_order_combo = FCComboBox2()
        self.paint_order_combo.addItems([_('Default'), _('Forward'), _('Reverse')])

        param_grid.addWidget(self.paint_order_label, 2, 0)
        param_grid.addWidget(self.paint_order_combo, 2, 1)

        # Tip Dia
        self.tipdialabel = FCLabel('%s:' % _('V-Tip Dia'))
        self.tipdialabel.setToolTip(
            _("The tip diameter for V-Shape Tool"))
        self.tipdia_entry = FCDoubleSpinner()
        self.tipdia_entry.set_precision(self.decimals)
        self.tipdia_entry.set_range(0.0000, 10000.0000)
        self.tipdia_entry.setSingleStep(0.1)
        self.tipdia_entry.setObjectName(_("V-Tip Dia"))

        param_grid.addWidget(self.tipdialabel, 4, 0)
        param_grid.addWidget(self.tipdia_entry, 4, 1)

        # Tip Angle
        self.tipanglelabel = FCLabel('%s:' % _('V-Tip Angle'))
        self.tipanglelabel.setToolTip(
            _("The tip angle for V-Shape Tool.\n"
              "In degree."))
        self.tipangle_entry = FCDoubleSpinner()
        self.tipangle_entry.set_precision(self.decimals)
        self.tipangle_entry.set_range(1.0000, 180.0000)
        self.tipangle_entry.setSingleStep(5)
        self.tipangle_entry.setObjectName(_("V-Tip Angle"))

        param_grid.addWidget(self.tipanglelabel, 6, 0)
        param_grid.addWidget(self.tipangle_entry, 6, 1)

        # Cut Z entry
        cutzlabel = FCLabel('%s:' % _('Cut Z'))
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
        param_grid.addWidget(cutzlabel, 8, 0)
        param_grid.addWidget(self.cutz_entry, 8, 1)

        # ### Tool Diameter ####
        self.newdialabel = FCLabel('%s:' % _('New Dia'))
        self.newdialabel.setToolTip(
            _("Diameter for the new tool to add in the Tool Table.\n"
              "If the tool is V-shape type then this value is automatically\n"
              "calculated from the other parameters.")
        )
        self.newdia_entry = FCDoubleSpinner()
        self.newdia_entry.set_precision(self.decimals)
        self.newdia_entry.set_range(-10000.000, 10000.0000)
        self.newdia_entry.setObjectName(_("Tool Dia"))

        param_grid.addWidget(self.newdialabel, 10, 0)
        param_grid.addWidget(self.newdia_entry, 10, 1)

        # separator_line = QtWidgets.QFrame()
        # separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        # separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        # param_grid.addWidget(separator_line, 6, 0, 1, 2)

        # #############################################################################################################
        # Tool Frame
        # #############################################################################################################
        # ### Tools ## ##
        self.tools_table_label = FCLabel('%s' % _("Tool Parameters"), color='green', bold=True)
        self.layout.addWidget(self.tools_table_label)

        tt_frame = FCFrame()
        self.layout.addWidget(tt_frame)

        tool_grid = GLay(v_spacing=5, h_spacing=3)
        tt_frame.setLayout(tool_grid)

        # Overlap
        ovlabel = FCLabel('%s:' % _('Overlap'))
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

        tool_grid.addWidget(ovlabel, 0, 0)
        tool_grid.addWidget(self.paintoverlap_entry, 0, 1)

        # Margin
        marginlabel = FCLabel('%s:' % _('Margin'))
        marginlabel.setToolTip(
            _("Distance by which to avoid\n"
              "the edges of the polygon to\n"
              "be painted.")
        )
        self.paintmargin_entry = FCDoubleSpinner()
        self.paintmargin_entry.set_range(-10000.0000, 10000.0000)
        self.paintmargin_entry.set_precision(self.decimals)
        self.paintmargin_entry.setSingleStep(0.1)

        tool_grid.addWidget(marginlabel, 2, 0)
        tool_grid.addWidget(self.paintmargin_entry, 2, 1)

        # Method
        methodlabel = FCLabel('%s:' % _('Method'))
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
        # ], orientation='vertical', compact=True)
        self.paintmethod_combo = FCComboBox2()
        self.paintmethod_combo.addItems(
            [_("Standard"), _("Seed"), _("Lines"), _("Laser_lines"), _("Combo")]
        )

        tool_grid.addWidget(methodlabel, 4, 0)
        tool_grid.addWidget(self.paintmethod_combo, 4, 1)

        # Connect lines
        self.pathconnect_cb = FCCheckBox('%s' % _("Connect"))
        self.pathconnect_cb.setToolTip(
            _("Draw lines between resulting\n"
              "segments to minimize tool lifts.")
        )

        # Paint contour
        self.contour_cb = FCCheckBox('%s' % _("Contour"))
        self.contour_cb.setToolTip(
            _("Cut around the perimeter of the polygon\n"
              "to trim rough edges.")
        )

        tool_grid.addWidget(self.pathconnect_cb, 6, 0)
        tool_grid.addWidget(self.contour_cb, 6, 1)

        # #############################################################################################################
        # General Parameters Frame
        # #############################################################################################################
        self.gen_param_label = FCLabel('%s' % _("Common Parameters"), color='indigo', bold=True)
        self.gen_param_label.setToolTip(
            _("Parameters that are common for all tools.")
        )
        self.layout.addWidget(self.gen_param_label)

        gp_frame = FCFrame()
        self.layout.addWidget(gp_frame)

        gen_grid = GLay(v_spacing=5, h_spacing=3)
        gp_frame.setLayout(gen_grid)

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
        gen_grid.addWidget(self.rest_cb, 0, 0, 1, 2)

        # Polygon selection
        selectlabel = FCLabel('%s:' % _('Selection'))
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
        #     compact=None
        # )
        self.selectmethod_combo = FCComboBox2()
        self.selectmethod_combo.addItems(
            [_("All"), _("Polygon Selection"), _("Area Selection"), _("Reference Object")]
        )

        gen_grid.addWidget(selectlabel, 2, 0)
        gen_grid.addWidget(self.selectmethod_combo, 2, 1)

        self.area_shape_label = FCLabel('%s:' % _("Shape"))
        self.area_shape_label.setToolTip(
            _("The kind of selection shape used for area selection.")
        )

        self.area_shape_radio = RadioSet([{'label': _("Square"), 'value': 'square'},
                                          {'label': _("Polygon"), 'value': 'polygon'}], compact=True)

        gen_grid.addWidget(self.area_shape_label, 4, 0)
        gen_grid.addWidget(self.area_shape_radio, 4, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        gen_grid.addWidget(separator_line, 6, 0, 1, 2)

        # ## Plotting type
        self.paint_plotting_radio = RadioSet([{'label': _('Normal'), 'value': 'normal'},
                                              {"label": _("Progressive"), "value": "progressive"}],
                                             compact=True)
        plotting_label = FCLabel('%s:' % _("Plotting"))
        plotting_label.setToolTip(
            _("- 'Normal' - normal plotting, done at the end of the job\n"
              "- 'Progressive' - each shape is plotted after it is generated")
        )
        gen_grid.addWidget(plotting_label, 8, 0)
        gen_grid.addWidget(self.paint_plotting_radio, 8, 1)

        GLay.set_common_column_size([tool_grid, param_grid, gen_grid], 0)

        self.layout.addStretch(1)
