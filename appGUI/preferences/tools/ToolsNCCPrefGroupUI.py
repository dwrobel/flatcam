from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings

from appGUI.GUIElements import RadioSet, FCDoubleSpinner, FCCheckBox, NumericalEvalTupleEntry, FCComboBox2
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


class ToolsNCCPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "NCC Tool Options", parent=parent)
        super(ToolsNCCPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("NCC Tool Options")))
        self.decimals = decimals

        # ## Clear non-copper regions
        self.clearcopper_label = QtWidgets.QLabel("<b>%s:</b>" % _("Parameters"))
        self.clearcopper_label.setToolTip(
            _("Create a Geometry object with\n"
              "toolpaths to cut all non-copper regions.")
        )
        self.layout.addWidget(self.clearcopper_label)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        ncctdlabel = QtWidgets.QLabel('<b><font color="green">%s:</font></b>' % _('Tools Dia'))
        ncctdlabel.setToolTip(
            _("Diameters of the tools, separated by comma.\n"
              "The value of the diameter has to use the dot decimals separator.\n"
              "Valid values: 0.3, 1.0")
        )
        grid0.addWidget(ncctdlabel, 0, 0)
        self.ncc_tool_dia_entry = NumericalEvalTupleEntry(border_color='#0069A9')
        self.ncc_tool_dia_entry.setPlaceholderText(_("Comma separated values"))
        grid0.addWidget(self.ncc_tool_dia_entry, 0, 1)

        # Tool Type Radio Button
        self.tool_type_label = QtWidgets.QLabel('%s:' % _('Tool Type'))
        self.tool_type_label.setToolTip(
            _("Default tool type:\n"
              "- 'V-shape'\n"
              "- Circular")
        )

        self.tool_type_radio = RadioSet([{'label': _('V-shape'), 'value': 'V'},
                                         {'label': _('Circular'), 'value': 'C1'}])
        self.tool_type_radio.setToolTip(
            _("Default tool type:\n"
              "- 'V-shape'\n"
              "- Circular")
        )

        grid0.addWidget(self.tool_type_label, 1, 0)
        grid0.addWidget(self.tool_type_radio, 1, 1)

        # Tip Dia
        self.tipdialabel = QtWidgets.QLabel('%s:' % _('V-Tip Dia'))
        self.tipdialabel.setToolTip(
            _("The tip diameter for V-Shape Tool"))
        self.tipdia_entry = FCDoubleSpinner()
        self.tipdia_entry.set_precision(self.decimals)
        self.tipdia_entry.set_range(0, 1000)
        self.tipdia_entry.setSingleStep(0.1)

        grid0.addWidget(self.tipdialabel, 2, 0)
        grid0.addWidget(self.tipdia_entry, 2, 1)

        # Tip Angle
        self.tipanglelabel = QtWidgets.QLabel('%s:' % _('V-Tip Angle'))
        self.tipanglelabel.setToolTip(
            _("The tip angle for V-Shape Tool.\n"
              "In degree."))
        self.tipangle_entry = FCDoubleSpinner()
        self.tipangle_entry.set_precision(self.decimals)
        self.tipangle_entry.set_range(1, 180)
        self.tipangle_entry.setSingleStep(5)
        self.tipangle_entry.setWrapping(True)

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
        self.cutz_entry.set_range(-10000.0000, 0.0000)
        self.cutz_entry.setSingleStep(0.1)

        self.cutz_entry.setToolTip(
           _("Depth of cut into material. Negative value.\n"
             "In application units.")
        )

        grid0.addWidget(cutzlabel, 4, 0)
        grid0.addWidget(self.cutz_entry, 4, 1)

        # New Diameter
        self.newdialabel = QtWidgets.QLabel('%s:' % _('New Dia'))
        self.newdialabel.setToolTip(
            _("Diameter for the new tool to add in the Tool Table.\n"
              "If the tool is V-shape type then this value is automatically\n"
              "calculated from the other parameters.")
        )
        self.newdia_entry = FCDoubleSpinner()
        self.newdia_entry.set_precision(self.decimals)
        self.newdia_entry.set_range(0.0001, 10000.0000)
        self.newdia_entry.setSingleStep(0.1)

        grid0.addWidget(self.newdialabel, 5, 0)
        grid0.addWidget(self.newdia_entry, 5, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 6, 0, 1, 2)

        # Milling Type Radio Button
        self.milling_type_label = QtWidgets.QLabel('%s:' % _('Milling Type'))
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

        grid0.addWidget(self.milling_type_label, 7, 0)
        grid0.addWidget(self.milling_type_radio, 7, 1)

        # Tool order Radio Button
        self.ncc_order_label = QtWidgets.QLabel('%s:' % _('Tool order'))
        self.ncc_order_label.setToolTip(_("This set the way that the tools in the tools table are used.\n"
                                          "'No' --> means that the used order is the one in the tool table\n"
                                          "'Forward' --> means that the tools will be ordered from small to big\n"
                                          "'Reverse' --> means that the tools will ordered from big to small\n\n"
                                          "WARNING: using rest machining will automatically set the order\n"
                                          "in reverse and disable this control."))

        self.ncc_order_radio = RadioSet([{'label': _('No'), 'value': 'no'},
                                         {'label': _('Forward'), 'value': 'fwd'},
                                         {'label': _('Reverse'), 'value': 'rev'}])
        self.ncc_order_radio.setToolTip(_("This set the way that the tools in the tools table are used.\n"
                                          "'No' --> means that the used order is the one in the tool table\n"
                                          "'Forward' --> means that the tools will be ordered from small to big\n"
                                          "'Reverse' --> means that the tools will ordered from big to small\n\n"
                                          "WARNING: using rest machining will automatically set the order\n"
                                          "in reverse and disable this control."))
        grid0.addWidget(self.ncc_order_label, 8, 0)
        grid0.addWidget(self.ncc_order_radio, 8, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 9, 0, 1, 2)

        # Overlap Entry
        nccoverlabel = QtWidgets.QLabel('%s:' % _('Overlap'))
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

        grid0.addWidget(nccoverlabel, 10, 0)
        grid0.addWidget(self.ncc_overlap_entry, 10, 1)

        # Margin entry
        nccmarginlabel = QtWidgets.QLabel('%s:' % _('Margin'))
        nccmarginlabel.setToolTip(
            _("Bounding box margin.")
        )
        self.ncc_margin_entry = FCDoubleSpinner()
        self.ncc_margin_entry.set_precision(self.decimals)
        self.ncc_margin_entry.set_range(-10000, 10000)
        self.ncc_margin_entry.setSingleStep(0.1)

        grid0.addWidget(nccmarginlabel, 11, 0)
        grid0.addWidget(self.ncc_margin_entry, 11, 1)

        # Method
        methodlabel = QtWidgets.QLabel('%s:' % _('Method'))
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
        # ], orientation='vertical', stretch=False)
        self.ncc_method_combo = FCComboBox2()
        self.ncc_method_combo.addItems(
            [_("Standard"), _("Seed"), _("Lines"), _("Combo")]
        )

        grid0.addWidget(methodlabel, 12, 0)
        grid0.addWidget(self.ncc_method_combo, 12, 1)

        # Connect lines
        self.ncc_connect_cb = FCCheckBox('%s' % _("Connect"))
        self.ncc_connect_cb.setToolTip(
            _("Draw lines between resulting\n"
              "segments to minimize tool lifts.")
        )

        grid0.addWidget(self.ncc_connect_cb, 13, 0)

        # Contour Checkbox
        self.ncc_contour_cb = FCCheckBox('%s' % _("Contour"))
        self.ncc_contour_cb.setToolTip(
           _("Cut around the perimeter of the polygon\n"
             "to trim rough edges.")
        )

        grid0.addWidget(self.ncc_contour_cb, 13, 1)

        # ## NCC Offset choice
        self.ncc_choice_offset_cb = FCCheckBox('%s' % _("Offset"))
        self.ncc_choice_offset_cb.setToolTip(
            _("If used, it will add an offset to the copper features.\n"
              "The copper clearing will finish to a distance\n"
              "from the copper features.")
        )

        grid0.addWidget(self.ncc_choice_offset_cb, 14, 0, 1, 2)

        # ## NCC Offset value
        self.ncc_offset_label = QtWidgets.QLabel('%s:' % _("Offset value"))
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

        grid0.addWidget(self.ncc_offset_label, 15, 0)
        grid0.addWidget(self.ncc_offset_spinner, 15, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 16, 0, 1, 2)

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

        grid0.addWidget(self.ncc_rest_cb, 17, 0, 1, 2)

        # ## Reference
        # self.reference_radio = RadioSet([{'label': _('Itself'), 'value': 'itself'},
        #                                  {"label": _("Area Selection"), "value": "area"},
        #                                  {'label': _('Reference Object'), 'value': 'box'}],
        #                                 orientation='vertical',
        #                                 stretch=None)
        self.select_combo = FCComboBox2()
        self.select_combo.addItems(
            [_("Itself"), _("Area Selection"), _("Reference Object")]
        )
        select_label = QtWidgets.QLabel('%s:' % _("Selection"))
        select_label.setToolTip(
            _("Selection of area to be processed.\n"
              "- 'Itself' - the processing extent is based on the object that is processed.\n "
              "- 'Area Selection' - left mouse click to start selection of the area to be processed.\n"
              "- 'Reference Object' - will process the area specified by another object.")
        )

        grid0.addWidget(select_label, 18, 0)
        grid0.addWidget(self.select_combo, 18, 1)

        self.area_shape_label = QtWidgets.QLabel('%s:' % _("Shape"))
        self.area_shape_label.setToolTip(
            _("The kind of selection shape used for area selection.")
        )

        self.area_shape_radio = RadioSet([{'label': _("Square"), 'value': 'square'},
                                          {'label': _("Polygon"), 'value': 'polygon'}])

        grid0.addWidget(self.area_shape_label, 19, 0)
        grid0.addWidget(self.area_shape_radio, 19, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 20, 0, 1, 2)

        # ## Plotting type
        self.plotting_radio = RadioSet([{'label': _('Normal'), 'value': 'normal'},
                                        {"label": _("Progressive"), "value": "progressive"}])
        plotting_label = QtWidgets.QLabel('%s:' % _("Plotting"))
        plotting_label.setToolTip(
            _("- 'Normal' - normal plotting, done at the end of the job\n"
              "- 'Progressive' - each shape is plotted after it is generated")
        )
        grid0.addWidget(plotting_label, 21, 0)
        grid0.addWidget(self.plotting_radio, 21, 1)

        # Check Tool validity
        self.valid_cb = FCCheckBox(label=_('Check validity'))
        self.valid_cb.setToolTip(
            _("If checked then the tools diameters are verified\n"
              "if they will provide a complete isolation.")
        )
        self.valid_cb.setObjectName("n_check")

        grid0.addWidget(self.valid_cb, 23, 0, 1, 2)

        self.layout.addStretch()
