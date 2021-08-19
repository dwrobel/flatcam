from PyQt6 import QtWidgets

from appGUI.GUIElements import RadioSet, FCDoubleSpinner, FCComboBox2, FCCheckBox, FCSpinner, NumericalEvalTupleEntry, \
    FCLabel, FCGridLayout
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ToolsISOPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):
        super(ToolsISOPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Isolation Plugin")))
        self.decimals = decimals

        # ## Clear non-copper regions
        self.iso_label = FCLabel("<b>%s:</b>" % _("Parameters"))
        self.iso_label.setToolTip(
            _("Create a Geometry object with\n"
              "toolpaths to cut around polygons.")
        )
        self.layout.addWidget(self.iso_label)

        grid0 = FCGridLayout(v_spacing=5, h_spacing=3)
        self.layout.addLayout(grid0)

        # Tool Dias
        isotdlabel = FCLabel('<b><font color="green">%s:</font></b>' % _('Tools Dia'))
        isotdlabel.setToolTip(
            _("Diameters of the tools, separated by comma.\n"
              "The value of the diameter has to use the dot decimals separator.\n"
              "Valid values: 0.3, 1.0")
        )
        self.tool_dia_entry = NumericalEvalTupleEntry(border_color='#0069A9')
        self.tool_dia_entry.setPlaceholderText(_("Comma separated values"))

        grid0.addWidget(isotdlabel, 0, 0)
        grid0.addWidget(self.tool_dia_entry, 0, 1, 1, 2)

        # Tool order Radio Button
        self.order_label = FCLabel('%s:' % _('Tool order'))
        self.order_label.setToolTip(_("This set the way that the tools in the tools table are used.\n"
                                      "'No' --> means that the used order is the one in the tool table\n"
                                      "'Forward' --> means that the tools will be ordered from small to big\n"
                                      "'Reverse' --> means that the tools will ordered from big to small\n\n"
                                      "WARNING: using rest machining will automatically set the order\n"
                                      "in reverse and disable this control."))

        self.order_radio = RadioSet([{'label': _('No'), 'value': 'no'},
                                     {'label': _('Forward'), 'value': 'fwd'},
                                     {'label': _('Reverse'), 'value': 'rev'}])

        grid0.addWidget(self.order_label, 2, 0)
        grid0.addWidget(self.order_radio, 2, 1, 1, 2)

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

        grid0.addWidget(cutzlabel, 10, 0)
        grid0.addWidget(self.cutz_entry, 10, 1, 1, 2)

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

        grid0.addWidget(self.newdialabel, 12, 0)
        grid0.addWidget(self.newdia_entry, 12, 1, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        grid0.addWidget(separator_line, 14, 0, 1, 3)

        # Tool Type
        tool_shape_label = FCLabel('%s:' % _('Shape'))
        tool_shape_label.setToolTip(
            _("Tool Shape. \n"
              "Can be:\n"
              "C1 ... C4 = circular tool with x flutes\n"
              "B = ball tip milling tool\n"
              "V = v-shape milling tool")
        )

        self.tool_shape_combo = FCComboBox2(policy=False)
        self.tool_shape_combo.setObjectName('i_tool_shape')
        self.tool_shape_combo.addItems(["C1", "C2", "C3", "C4", "B", "V"])

        grid0.addWidget(tool_shape_label, 16, 0)
        grid0.addWidget(self.tool_shape_combo, 16, 1, 1, 2)

        # Passes
        passlabel = FCLabel('%s:' % _('Passes'))
        passlabel.setToolTip(
            _("Width of the isolation gap in\n"
              "number (integer) of tool widths.")
        )
        self.passes_entry = FCSpinner()
        self.passes_entry.set_range(1, 999)
        self.passes_entry.setObjectName("i_passes")

        grid0.addWidget(passlabel, 18, 0)
        grid0.addWidget(self.passes_entry, 18, 1, 1, 2)

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
        self.overlap_entry.setObjectName("i_overlap")

        grid0.addWidget(overlabel, 20, 0)
        grid0.addWidget(self.overlap_entry, 20, 1, 1, 2)

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

        grid0.addWidget(self.milling_type_label, 22, 0)
        grid0.addWidget(self.milling_type_radio, 22, 1, 1, 2)

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
        self.iso_type_radio.setObjectName("i_type")

        grid0.addWidget(self.iso_type_label, 24, 0)
        grid0.addWidget(self.iso_type_radio, 24, 1, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        grid0.addWidget(separator_line, 26, 0, 1, 3)

        # Rest machining CheckBox
        self.rest_cb = FCCheckBox('%s' % _("Rest"))
        self.rest_cb.setObjectName("i_rest_machining")
        self.rest_cb.setToolTip(
            _("If checked, use 'rest machining'.\n"
              "Basically it will process copper outside PCB features,\n"
              "using the biggest tool and continue with the next tools,\n"
              "from bigger to smaller, to process the copper features that\n"
              "could not be processed by previous tool, until there is\n"
              "nothing left to process or there are no more tools.\n\n"
              "If not checked, use the standard algorithm.")
        )

        grid0.addWidget(self.rest_cb, 28, 0)

        # Combine All Passes
        self.combine_passes_cb = FCCheckBox(label=_('Combine'))
        self.combine_passes_cb.setToolTip(
            _("Combine all passes into one object")
        )
        self.combine_passes_cb.setObjectName("i_combine")

        grid0.addWidget(self.combine_passes_cb, 28, 1)

        # Exception Areas
        self.except_cb = FCCheckBox(label=_('Except'))
        self.except_cb.setToolTip(_("When the isolation geometry is generated,\n"
                                    "by checking this, the area of the object below\n"
                                    "will be subtracted from the isolation geometry."))
        self.except_cb.setObjectName("i_except")
        grid0.addWidget(self.except_cb, 28, 2)

        # Check Tool validity
        self.valid_cb = FCCheckBox(label=_('Check validity'))
        self.valid_cb.setToolTip(
            _("If checked then the tools diameters are verified\n"
              "if they will provide a complete isolation.")
        )
        self.valid_cb.setObjectName("i_check")

        grid0.addWidget(self.valid_cb, 30, 0, 1, 3)

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
        self.select_combo.setObjectName("i_selection")

        grid0.addWidget(self.select_label, 32, 0)
        grid0.addWidget(self.select_combo, 32, 1, 1, 2)

        # Area Shape
        self.area_shape_label = FCLabel('%s:' % _("Shape"))
        self.area_shape_label.setToolTip(
            _("The kind of selection shape used for area selection.")
        )

        self.area_shape_radio = RadioSet([{'label': _("Square"), 'value': 'square'},
                                          {'label': _("Polygon"), 'value': 'polygon'}])

        grid0.addWidget(self.area_shape_label, 34, 0)
        grid0.addWidget(self.area_shape_radio, 34, 1, 1, 2)

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
        grid0.addWidget(self.poly_int_cb, 36, 0)
        grid0.addWidget(self.force_iso_cb, 36, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        grid0.addWidget(separator_line, 38, 0, 1, 3)

        # ## Plotting type
        self.plotting_radio = RadioSet([{'label': _('Normal'), 'value': 'normal'},
                                        {"label": _("Progressive"), "value": "progressive"}])
        plotting_label = FCLabel('%s:' % _("Plotting"))
        plotting_label.setToolTip(
            _("- 'Normal' - normal plotting, done at the end of the job\n"
              "- 'Progressive' - each shape is plotted after it is generated")
        )
        grid0.addWidget(plotting_label, 40, 0)
        grid0.addWidget(self.plotting_radio, 40, 1, 1, 2)

        self.layout.addStretch()
