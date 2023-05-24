
from PyQt6 import QtWidgets

from appGUI.GUIElements import RadioSet, FCDoubleSpinner, FCComboBox2, FCCheckBox, FCSpinner, NumericalEvalTupleEntry, \
    FCLabel, GLay, FCFrame
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ToolsISOPrefGroupUI(OptionsGroupUI):
    def __init__(self, app, parent=None):
        super(ToolsISOPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Isolation Plugin")))
        self.decimals = app.decimals
        self.options = app.options

        # ## Clear non-copper regions
        self.iso_label = FCLabel(_("Parameters"), color='blue', bold=True)
        self.iso_label.setToolTip(
            _("Create a Geometry object with\n"
              "toolpaths to cut around polygons.")
        )
        self.layout.addWidget(self.iso_label)

        # #############################################################################################################
        # Parameters Frame
        # #############################################################################################################
        par_frame = FCFrame()
        self.layout.addWidget(par_frame)

        par_grid = GLay(v_spacing=5, h_spacing=3)
        par_frame.setLayout(par_grid)

        # Tool Dias
        isotdlabel = FCLabel('%s:' % _('Tools Dia'), color='green', bold=True)
        isotdlabel.setToolTip(
            _("Diameters of the tools, separated by comma.\n"
              "The value of the diameter has to use the dot decimals separator.\n"
              "Valid values: 0.3, 1.0")
        )
        self.tool_dia_entry = NumericalEvalTupleEntry(border_color='#0069A9')
        self.tool_dia_entry.setPlaceholderText(_("Comma separated values"))

        par_grid.addWidget(isotdlabel, 0, 0)
        par_grid.addWidget(self.tool_dia_entry, 0, 1, 1, 2)

        # Tool order
        self.iso_order_label = FCLabel('%s:' % _('Tool order'))
        self.iso_order_label.setToolTip(_("This set the way that the tools in the tools table are used.\n"
                                          "'Default' --> means that the used order is the one in the tool table\n"
                                          "'Forward' --> means that the tools will be ordered from small to big\n"
                                          "'Reverse' --> means that the tools will ordered from big to small\n\n"
                                          "WARNING: using rest machining will automatically set the order\n"
                                          "in reverse and disable this control."))

        self.iso_order_combo = FCComboBox2()
        self.iso_order_combo.addItems([_('Default'), _('Forward'), _('Reverse')])

        par_grid.addWidget(self.iso_order_label, 2, 0)
        par_grid.addWidget(self.iso_order_combo, 2, 1, 1, 2)

        # Tip Dia
        self.tipdialabel = FCLabel('%s:' % _('V-Tip Dia'))
        self.tipdialabel.setToolTip(
            _("The tip diameter for V-Shape Tool"))
        self.tipdia_entry = FCDoubleSpinner()
        self.tipdia_entry.set_precision(self.decimals)
        self.tipdia_entry.set_range(0, 1000)
        self.tipdia_entry.setSingleStep(0.1)

        par_grid.addWidget(self.tipdialabel, 4, 0)
        par_grid.addWidget(self.tipdia_entry, 4, 1, 1, 2)

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
        par_grid.addWidget(self.tipangle_entry, 6, 1, 1, 2)

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
        par_grid.addWidget(self.cutz_entry, 8, 1, 1, 2)

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
        par_grid.addWidget(self.newdia_entry, 10, 1, 1, 2)

        # separator_line = QtWidgets.QFrame()
        # separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        # separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        # par_grid.addWidget(separator_line, 10, 0, 1, 3)

        # #############################################################################################################
        # Tool Frame
        # #############################################################################################################
        # ### Tools ## ##
        self.tools_table_label = FCLabel(_("Tool Parameters"), color='green', bold=True)
        self.layout.addWidget(self.tools_table_label)

        tt_frame = FCFrame()
        self.layout.addWidget(tt_frame)

        tool_grid = GLay(v_spacing=5, h_spacing=3)
        tt_frame.setLayout(tool_grid)

        # Shape
        tool_shape_label = FCLabel('%s:' % _('Shape'))
        tool_shape_label.setToolTip(
            _("Tool Shape. \n"
              "Can be:\n"
              "C1 ... C4 = circular tool with x flutes\n"
              "B = ball tip milling tool\n"
              "V = v-shape milling tool\n"
              "L = laser")
        )

        self.tool_shape_combo = FCComboBox2(policy=False)
        self.tool_shape_combo.addItems(["C1", "C2", "C3", "C4", "B", "V", "L"])

        tool_grid.addWidget(tool_shape_label, 0, 0)
        tool_grid.addWidget(self.tool_shape_combo, 0, 1, 1, 2)

        # Passes
        passlabel = FCLabel('%s:' % _('Passes'))
        passlabel.setToolTip(
            _("Width of the isolation gap in\n"
              "number (integer) of tool widths.")
        )
        self.passes_entry = FCSpinner()
        self.passes_entry.set_range(1, 999)

        tool_grid.addWidget(passlabel, 2, 0)
        tool_grid.addWidget(self.passes_entry, 2, 1, 1, 2)

        # Pad Passes
        padpasslabel = FCLabel('%s:' % _('Pad Passes'))
        padpasslabel.setToolTip(
            _("Width of the extra isolation gap for pads only,\n"
              "in number (integer) of tool widths.")
        )
        self.pad_passes_entry = FCSpinner()
        self.pad_passes_entry.set_range(0, 999)

        tool_grid.addWidget(padpasslabel, 4, 0)
        tool_grid.addWidget(self.pad_passes_entry, 4, 1, 1, 2)

        # Overlap Entry
        overlabel = FCLabel('%s:' % _('Overlap'))
        overlabel.setToolTip(
            _("How much (percentage) of the tool width to overlap each tool pass.")
        )
        self.overlap_entry = FCDoubleSpinner(suffix='%')
        self.overlap_entry.set_precision(self.decimals)
        self.overlap_entry.setWrapping(True)
        self.overlap_entry.set_range(0.0000, 99.9999)
        self.overlap_entry.setSingleStep(0.1)

        tool_grid.addWidget(overlabel, 6, 0)
        tool_grid.addWidget(self.overlap_entry, 6, 1, 1, 2)

        # Milling Type Radio Button
        self.milling_type_label = FCLabel('%s:' % _('Milling Type'))
        self.milling_type_label.setToolTip(
            _("Milling type:\n"
              "- climb / best for precision milling and to reduce tool usage\n"
              "- conventional / useful when there is no backlash compensation")
        )

        self.milling_type_radio = RadioSet([{'label': _('Climb'), 'value': 'cl'},
                                            {'label': _('Conventional'), 'value': 'cv'}])
        self.milling_type_radio.setToolTip(
            _("Milling type:\n"
              "- climb / best for precision milling and to reduce tool usage\n"
              "- conventional / useful when there is no backlash compensation")
        )

        tool_grid.addWidget(self.milling_type_label, 8, 0)
        tool_grid.addWidget(self.milling_type_radio, 8, 1, 1, 2)

        # Isolation Type
        self.iso_type_label = FCLabel('%s:' % _('Isolation Type'))
        self.iso_type_label.setToolTip(
            _("Choose how the isolation will be executed:\n"
              "- 'Full' -> complete isolation of polygons\n"
              "- 'Ext' -> will isolate only on the outside\n"
              "- 'Int' -> will isolate only on the inside\n"
              "'Exterior' isolation is almost always possible\n"
              "(with the right tool) but 'Interior'\n"
              "isolation can be done only when there is an opening\n"
              "inside of the polygon (e.g polygon is a 'doughnut' shape).")
        )
        self.iso_type_radio = RadioSet([{'label': _('Full'), 'value': 'full'},
                                        {'label': _('Ext'), 'value': 'ext'},
                                        {'label': _('Int'), 'value': 'int'}])

        tool_grid.addWidget(self.iso_type_label, 10, 0)
        tool_grid.addWidget(self.iso_type_radio, 10, 1, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        tool_grid.addWidget(separator_line, 12, 0, 1, 3)

        # #############################################################################################################
        # General Parameters Frame
        # #############################################################################################################
        self.gen_param_label = FCLabel(_("Common Parameters"), color='indigo', bold=True)
        self.gen_param_label.setToolTip(
            _("Parameters that are common for all tools.")
        )
        self.layout.addWidget(self.gen_param_label)

        gp_frame = FCFrame()
        self.layout.addWidget(gp_frame)

        gen_grid = GLay(v_spacing=5, h_spacing=3)
        gp_frame.setLayout(gen_grid)

        # Rest machining CheckBox
        self.rest_cb = FCCheckBox('%s' % _("Rest"))
        self.rest_cb.setToolTip(
            _("If checked, use 'rest machining'.\n"
              "Basically it will process copper outside PCB features,\n"
              "using the biggest tool and continue with the next tools,\n"
              "from bigger to smaller, to process the copper features that\n"
              "could not be processed by previous tool, until there is\n"
              "nothing left to process or there are no more tools.\n\n"
              "If not checked, use the standard algorithm.")
        )

        gen_grid.addWidget(self.rest_cb, 0, 0)

        # Combine All Passes
        self.combine_passes_cb = FCCheckBox(label=_('Combine'))
        self.combine_passes_cb.setToolTip(
            _("Combine all passes into one object")
        )

        gen_grid.addWidget(self.combine_passes_cb, 0, 1)

        # Exception Areas
        self.except_cb = FCCheckBox(label=_('Except'))
        self.except_cb.setToolTip(_("When the isolation geometry is generated,\n"
                                    "by checking this, the area of the object below\n"
                                    "will be subtracted from the isolation geometry."))
        gen_grid.addWidget(self.except_cb, 0, 2)

        # Check Tool validity
        self.valid_cb = FCCheckBox(label=_('Check validity'))
        self.valid_cb.setToolTip(
            _("If checked then the tools diameters are verified\n"
              "if they will provide a complete isolation.")
        )

        gen_grid.addWidget(self.valid_cb, 2, 0, 1, 3)

        # Simplification Tolerance
        self.simplify_cb = FCCheckBox('%s' % _("Simplify"))
        self.simplify_cb.setToolTip(
            _("All points in the simplified object will be\n"
              "within the tolerance distance of the original geometry.")
        )
        self.sim_tol_entry = FCDoubleSpinner()
        self.sim_tol_entry.set_precision(self.decimals)
        self.sim_tol_entry.setSingleStep(10 ** -self.decimals)
        self.sim_tol_entry.set_range(0.0000, 10000.0000)

        gen_grid.addWidget(self.simplify_cb, 4, 0)
        gen_grid.addWidget(self.sim_tol_entry, 4, 1)

        # Isolation Scope
        self.select_label = FCLabel('%s:' % _("Selection"))
        self.select_label.setToolTip(
            _("Isolation scope. Choose what to isolate:\n"
              "- 'All' -> Isolate all the polygons in the object\n"
              "- 'Area Selection' -> Isolate polygons within a selection area.\n"
              "- 'Polygon Selection' -> Isolate a selection of polygons.\n"
              "- 'Reference Object' - will process the area specified by another object.")
        )
        self.select_combo = FCComboBox2()
        self.select_combo.addItems(
            [_("All"), _("Area Selection"), _("Polygon Selection"), _("Reference Object")]
        )

        gen_grid.addWidget(self.select_label, 6, 0)
        gen_grid.addWidget(self.select_combo, 6, 1, 1, 2)

        # Area Shape
        self.area_shape_label = FCLabel('%s:' % _("Shape"))
        self.area_shape_label.setToolTip(
            _("The kind of selection shape used for area selection.")
        )

        self.area_shape_radio = RadioSet([{'label': _("Square"), 'value': 'square'},
                                          {'label': _("Polygon"), 'value': 'polygon'}])

        gen_grid.addWidget(self.area_shape_label, 8, 0)
        gen_grid.addWidget(self.area_shape_radio, 8, 1, 1, 2)

        # Polygon interiors selection
        self.poly_int_cb = FCCheckBox(_("Interiors"))
        self.poly_int_cb.setToolTip(
            _("When checked the user can select interiors of a polygon.\n"
              "(holes in the polygon).")
        )

        # Force isolation even if the interiors are not isolated
        self.force_iso_cb = FCCheckBox(_("Forced Rest"))
        self.force_iso_cb.setToolTip(
            _("When checked the isolation will be done with the current tool even if\n"
              "interiors of a polygon (holes in the polygon) could not be isolated.\n"
              "Works when 'rest machining' is used.")
        )
        gen_grid.addWidget(self.poly_int_cb, 10, 0)
        gen_grid.addWidget(self.force_iso_cb, 10, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        gen_grid.addWidget(separator_line, 12, 0, 1, 3)

        # ## Plotting type
        self.plotting_radio = RadioSet([{'label': _('Normal'), 'value': 'normal'},
                                        {"label": _("Progressive"), "value": "progressive"}])
        plotting_label = FCLabel('%s:' % _("Plotting"))
        plotting_label.setToolTip(
            _("- 'Normal' - normal plotting, done at the end of the job\n"
              "- 'Progressive' - each shape is plotted after it is generated")
        )
        gen_grid.addWidget(plotting_label, 14, 0)
        gen_grid.addWidget(self.plotting_radio, 14, 1, 1, 2)

        GLay.set_common_column_size([par_grid, tool_grid, gen_grid], 0)

        self.layout.addStretch(1)
