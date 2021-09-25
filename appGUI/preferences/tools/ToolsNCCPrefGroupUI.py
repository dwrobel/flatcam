from PyQt6 import QtWidgets

from appGUI.GUIElements import RadioSet, FCDoubleSpinner, FCCheckBox, NumericalEvalTupleEntry, FCComboBox2, FCLabel, \
    FCGridLayout, FCFrame
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ToolsNCCPrefGroupUI(OptionsGroupUI):
    def __init__(self, defaults, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "NCC Plugin", parent=parent)
        super(ToolsNCCPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("NCC Plugin")))
        self.decimals = decimals
        self.defaults = defaults

        # ## Clear non-copper regions
        self.clearcopper_label = FCLabel('<span style="color:blue;"><b>%s</b></span>' % _("Parameters"))
        self.clearcopper_label.setToolTip(
            _("Create a Geometry object with\n"
              "toolpaths to cut all non-copper regions.")
        )
        self.layout.addWidget(self.clearcopper_label)

        # #############################################################################################################
        # Parameters Frame
        # #############################################################################################################
        par_frame = FCFrame()
        self.layout.addWidget(par_frame)

        par_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        par_frame.setLayout(par_grid)

        # Tools Diameters
        ncctdlabel = FCLabel('<b><font color="green">%s:</font></b>' % _('Tools Dia'))
        ncctdlabel.setToolTip(
            _("Diameters of the tools, separated by comma.\n"
              "The value of the diameter has to use the dot decimals separator.\n"
              "Valid values: 0.3, 1.0")
        )
        self.ncc_tool_dia_entry = NumericalEvalTupleEntry(border_color='#0069A9')
        self.ncc_tool_dia_entry.setPlaceholderText(_("Comma separated values"))

        par_grid.addWidget(ncctdlabel, 0, 0)
        par_grid.addWidget(self.ncc_tool_dia_entry, 0, 1)

        # Tool order
        self.ncc_order_label = FCLabel('%s:' % _('Tool order'))
        self.ncc_order_label.setToolTip(_("This set the way that the tools in the tools table are used.\n"
                                          "'No' --> means that the used order is the one in the tool table\n"
                                          "'Forward' --> means that the tools will be ordered from small to big\n"
                                          "'Reverse' --> means that the tools will ordered from big to small\n\n"
                                          "WARNING: using rest machining will automatically set the order\n"
                                          "in reverse and disable this control."))

        self.ncc_order_combo = FCComboBox2()
        self.ncc_order_combo.addItems([_('Default'), _('Forward'), _('Reverse')])

        par_grid.addWidget(self.ncc_order_label, 2, 0)
        par_grid.addWidget(self.ncc_order_combo, 2, 1)

        # Tip Dia
        self.tipdialabel = FCLabel('%s:' % _('V-Tip Dia'))
        self.tipdialabel.setToolTip(
            _("The tip diameter for V-Shape Tool"))
        self.tipdia_entry = FCDoubleSpinner()
        self.tipdia_entry.set_precision(self.decimals)
        self.tipdia_entry.set_range(0, 1000)
        self.tipdia_entry.setSingleStep(0.1)

        par_grid.addWidget(self.tipdialabel, 4, 0)
        par_grid.addWidget(self.tipdia_entry, 4, 1)

        # Tip Angle
        self.tipanglelabel = FCLabel('%s:' % _('V-Tip Angle'))
        self.tipanglelabel.setToolTip(
            _("The tip angle for V-Shape Tool.\n"
              "In degree."))
        self.tipangle_entry = FCDoubleSpinner()
        self.tipangle_entry.set_precision(self.decimals)
        self.tipangle_entry.set_range(1, 180)
        self.tipangle_entry.setSingleStep(5)
        self.tipangle_entry.setWrapping(True)

        par_grid.addWidget(self.tipanglelabel, 6, 0)
        par_grid.addWidget(self.tipangle_entry, 6, 1)

        # Cut Z entry
        cutzlabel = FCLabel('%s:' % _('Cut Z'))
        cutzlabel.setToolTip(
           _("Depth of cut into material. Negative value.\n"
             "In application units.")
        )
        self.cutz_entry = FCDoubleSpinner()
        self.cutz_entry.set_precision(self.decimals)
        self.cutz_entry.set_range(-10000.0000, 0.0000)
        self.cutz_entry.setSingleStep(0.1)

        self.cutz_entry.setToolTip(
           _("Depth of cut into material. Negative value.\n"
             "In application units.")
        )

        par_grid.addWidget(cutzlabel, 8, 0)
        par_grid.addWidget(self.cutz_entry, 8, 1)

        # New Diameter
        self.newdialabel = FCLabel('%s:' % _('New Dia'))
        self.newdialabel.setToolTip(
            _("Diameter for the new tool to add in the Tool Table.\n"
              "If the tool is V-shape type then this value is automatically\n"
              "calculated from the other parameters.")
        )
        self.newdia_entry = FCDoubleSpinner()
        self.newdia_entry.set_precision(self.decimals)
        self.newdia_entry.set_range(0.0001, 10000.0000)
        self.newdia_entry.setSingleStep(0.1)

        par_grid.addWidget(self.newdialabel, 10, 0)
        par_grid.addWidget(self.newdia_entry, 10, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        par_grid.addWidget(separator_line, 12, 0, 1, 2)

        # Milling Type Radio Button
        self.milling_type_label = FCLabel('%s:' % _('Milling Type'))
        self.milling_type_label.setToolTip(
            _("Milling type:\n"
              "- climb / best for precision milling and to reduce tool usage\n"
              "- conventional / useful when there is no backlash compensation")
        )

        self.milling_type_radio = RadioSet([{'label': _('Climb'), 'value': 'cl'},
                                            {'label': _('Conventional'), 'value': 'cv'}], compact=True)
        self.milling_type_radio.setToolTip(
            _("Milling type:\n"
              "- climb / best for precision milling and to reduce tool usage\n"
              "- conventional / useful when there is no backlash compensation")
        )

        par_grid.addWidget(self.milling_type_label, 14, 0)
        par_grid.addWidget(self.milling_type_radio, 14, 1)

        # #############################################################################################################
        # Tool Frame
        # #############################################################################################################
        # ### Tools ## ##
        self.tools_table_label = FCLabel('<span style="color:green;"><b>%s</b></span>' % _("Tool Parameters"))
        self.layout.addWidget(self.tools_table_label)

        tt_frame = FCFrame()
        self.layout.addWidget(tt_frame)

        tool_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        tt_frame.setLayout(tool_grid)

        # Overlap Entry
        nccoverlabel = FCLabel('%s:' % _('Overlap'))
        nccoverlabel.setToolTip(
           _("How much (percentage) of the tool width to overlap each tool pass.\n"
             "Adjust the value starting with lower values\n"
             "and increasing it if areas that should be processed are still \n"
             "not processed.\n"
             "Lower values = faster processing, faster execution on CNC.\n"
             "Higher values = slow processing and slow execution on CNC\n"
             "due of too many paths.")
        )
        self.ncc_overlap_entry = FCDoubleSpinner(suffix='%')
        self.ncc_overlap_entry.set_precision(self.decimals)
        self.ncc_overlap_entry.setWrapping(True)
        self.ncc_overlap_entry.setRange(0.0000, 99.9999)
        self.ncc_overlap_entry.setSingleStep(0.1)

        tool_grid.addWidget(nccoverlabel, 0, 0)
        tool_grid.addWidget(self.ncc_overlap_entry, 0, 1)

        # Margin entry
        nccmarginlabel = FCLabel('%s:' % _('Margin'))
        nccmarginlabel.setToolTip(
            _("Bounding box margin.")
        )
        self.ncc_margin_entry = FCDoubleSpinner()
        self.ncc_margin_entry.set_precision(self.decimals)
        self.ncc_margin_entry.set_range(-10000, 10000)
        self.ncc_margin_entry.setSingleStep(0.1)

        tool_grid.addWidget(nccmarginlabel, 2, 0)
        tool_grid.addWidget(self.ncc_margin_entry, 2, 1)

        # Method
        methodlabel = FCLabel('%s:' % _('Method'))
        methodlabel.setToolTip(
            _("Algorithm for copper clearing:\n"
              "- Standard: Fixed step inwards.\n"
              "- Seed-based: Outwards from seed.\n"
              "- Line-based: Parallel lines.")
        )

        # self.ncc_method_radio = RadioSet([
        #     {"label": _("Standard"), "value": "standard"},
        #     {"label": _("Seed-based"), "value": "seed"},
        #     {"label": _("Straight lines"), "value": "lines"}
        # ], orientation='vertical', compact=True)
        self.ncc_method_combo = FCComboBox2()
        self.ncc_method_combo.addItems(
            [_("Standard"), _("Seed"), _("Lines"), _("Combo")]
        )

        tool_grid.addWidget(methodlabel, 4, 0)
        tool_grid.addWidget(self.ncc_method_combo, 4, 1)

        # Connect lines
        self.ncc_connect_cb = FCCheckBox('%s' % _("Connect"))
        self.ncc_connect_cb.setToolTip(
            _("Draw lines between resulting\n"
              "segments to minimize tool lifts.")
        )

        tool_grid.addWidget(self.ncc_connect_cb, 6, 0)

        # Contour Checkbox
        self.ncc_contour_cb = FCCheckBox('%s' % _("Contour"))
        self.ncc_contour_cb.setToolTip(
           _("Cut around the perimeter of the polygon\n"
             "to trim rough edges.")
        )

        tool_grid.addWidget(self.ncc_contour_cb, 6, 1)

        # ## NCC Offset choice
        self.ncc_choice_offset_cb = FCCheckBox('%s' % _("Offset"))
        self.ncc_choice_offset_cb.setToolTip(
            _("If used, it will add an offset to the copper features.\n"
              "The copper clearing will finish to a distance\n"
              "from the copper features.")
        )

        tool_grid.addWidget(self.ncc_choice_offset_cb, 8, 0, 1, 2)

        # ## NCC Offset value
        self.ncc_offset_label = FCLabel('%s:' % _("Offset value"))
        self.ncc_offset_label.setToolTip(
            _("If used, it will add an offset to the copper features.\n"
              "The copper clearing will finish to a distance\n"
              "from the copper features.")
        )
        self.ncc_offset_spinner = FCDoubleSpinner()
        self.ncc_offset_spinner.set_range(0.00, 10000.0000)
        self.ncc_offset_spinner.set_precision(self.decimals)
        self.ncc_offset_spinner.setWrapping(True)
        self.ncc_offset_spinner.setSingleStep(0.1)

        tool_grid.addWidget(self.ncc_offset_label, 10, 0)
        tool_grid.addWidget(self.ncc_offset_spinner, 10, 1)

        # separator_line = QtWidgets.QFrame()
        # separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        # separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        # par_grid.addWidget(separator_line, 16, 0, 1, 2)

        # #############################################################################################################
        # General Parameters Frame
        # #############################################################################################################
        self.gen_param_label = FCLabel('<span style="color:indigo;"><b>%s</b></span>' % _("Common Parameters"))
        self.gen_param_label.setToolTip(
            _("Parameters that are common for all tools.")
        )
        self.layout.addWidget(self.gen_param_label)

        gp_frame = FCFrame()
        self.layout.addWidget(gp_frame)

        gen_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        gp_frame.setLayout(gen_grid)

        # Rest machining CheckBox
        self.ncc_rest_cb = FCCheckBox('%s' % _("Rest"))
        self.ncc_rest_cb.setToolTip(
            _("If checked, use 'rest machining'.\n"
              "Basically it will process copper outside PCB features,\n"
              "using the biggest tool and continue with the next tools,\n"
              "from bigger to smaller, to process the copper features that\n"
              "could not be processed by previous tool, until there is\n"
              "nothing left to process or there are no more tools.\n\n"
              "If not checked, use the standard algorithm.")
        )

        gen_grid.addWidget(self.ncc_rest_cb, 0, 0, 1, 2)

        # ## Reference
        # self.reference_radio = RadioSet([{'label': _('Itself'), 'value': 'itself'},
        #                                  {"label": _("Area Selection"), "value": "area"},
        #                                  {'label': _('Reference Object'), 'value': 'box'}],
        #                                 orientation='vertical',
        #                                 compact=None)
        self.select_combo = FCComboBox2()
        self.select_combo.addItems(
            [_("Itself"), _("Area Selection"), _("Reference Object")]
        )
        select_label = FCLabel('%s:' % _("Selection"))
        select_label.setToolTip(
            _("Selection of area to be processed.\n"
              "- 'Itself' - the processing extent is based on the object that is processed.\n "
              "- 'Area Selection' - left mouse click to start selection of the area to be processed.\n"
              "- 'Reference Object' - will process the area specified by another object.")
        )

        gen_grid.addWidget(select_label, 2, 0)
        gen_grid.addWidget(self.select_combo, 2, 1)

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
        self.plotting_radio = RadioSet([{'label': _('Normal'), 'value': 'normal'},
                                        {"label": _("Progressive"), "value": "progressive"}], compact=True)
        plotting_label = FCLabel('%s:' % _("Plotting"))
        plotting_label.setToolTip(
            _("- 'Normal' - normal plotting, done at the end of the job\n"
              "- 'Progressive' - each shape is plotted after it is generated")
        )
        gen_grid.addWidget(plotting_label, 8, 0)
        gen_grid.addWidget(self.plotting_radio, 8, 1)

        # Check Tool validity
        self.valid_cb = FCCheckBox(label=_('Check validity'))
        self.valid_cb.setToolTip(
            _("If checked then the tools diameters are verified\n"
              "if they will provide a complete isolation.")
        )
        self.valid_cb.setObjectName("n_check")

        gen_grid.addWidget(self.valid_cb, 10, 0, 1, 2)

        FCGridLayout.set_common_column_size([par_grid, tool_grid, gen_grid], 0)

        # self.layout.addStretch()
