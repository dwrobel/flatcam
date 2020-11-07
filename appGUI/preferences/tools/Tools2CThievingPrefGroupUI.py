from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings

from appGUI.GUIElements import FCSpinner, FCDoubleSpinner, RadioSet, FCLabel
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


class Tools2CThievingPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):

        super(Tools2CThievingPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Copper Thieving Tool Options")))
        self.decimals = decimals

        # ## Grid Layout
        grid_lay = QtWidgets.QGridLayout()
        self.layout.addLayout(grid_lay)
        grid_lay.setColumnStretch(0, 0)
        grid_lay.setColumnStretch(1, 1)

        # ## Parameters
        self.cflabel = FCLabel('<b>%s</b>' % _('Parameters'))
        self.cflabel.setToolTip(
            _("A tool to generate a Copper Thieving that can be added\n"
              "to a selected Gerber file.")
        )
        grid_lay.addWidget(self.cflabel, 0, 0, 1, 2)

        # CIRCLE STEPS - to be used when buffering
        self.circle_steps_lbl = FCLabel('%s:' % _("Circle Steps"))
        self.circle_steps_lbl.setToolTip(
            _("Number of steps (lines) used to interpolate circles.")
        )

        self.circlesteps_entry = FCSpinner()
        self.circlesteps_entry.set_range(1, 9999)

        grid_lay.addWidget(self.circle_steps_lbl, 2, 0)
        grid_lay.addWidget(self.circlesteps_entry, 2, 1)

        # CLEARANCE #
        self.clearance_label = FCLabel('%s:' % _("Clearance"))
        self.clearance_label.setToolTip(
            _("This set the distance between the copper Thieving components\n"
              "(the polygon fill may be split in multiple polygons)\n"
              "and the copper traces in the Gerber file.")
        )
        self.clearance_entry = FCDoubleSpinner()
        self.clearance_entry.setMinimum(0.00001)
        self.clearance_entry.set_precision(self.decimals)
        self.clearance_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.clearance_label, 4, 0)
        grid_lay.addWidget(self.clearance_entry, 4, 1)

        # MARGIN #
        self.margin_label = FCLabel('%s:' % _("Margin"))
        self.margin_label.setToolTip(
            _("Bounding box margin.")
        )
        self.margin_entry = FCDoubleSpinner()
        self.margin_entry.setMinimum(0.0)
        self.margin_entry.set_precision(self.decimals)
        self.margin_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.margin_label, 6, 0)
        grid_lay.addWidget(self.margin_entry, 6, 1)

        # Area #
        self.area_label = FCLabel('%s:' % _("Area"))
        self.area_label.setToolTip(
            _("Thieving areas with area less then this value will not be added.")
        )
        self.area_entry = FCDoubleSpinner()
        self.area_entry.set_range(0.0, 10000.0000)
        self.area_entry.set_precision(self.decimals)
        self.area_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.area_label, 8, 0)
        grid_lay.addWidget(self.area_entry, 8, 1)
        
        # Reference #
        self.reference_radio = RadioSet([
            {'label': _('Itself'), 'value': 'itself'},
            {"label": _("Area Selection"), "value": "area"},
            {'label': _("Reference Object"), 'value': 'box'}
        ], orientation='vertical', stretch=False)
        self.reference_label = FCLabel(_("Reference:"))
        self.reference_label.setToolTip(
            _("- 'Itself' - the copper thieving extent is based on the object extent.\n"
              "- 'Area Selection' - left mouse click to start selection of the area to be filled.\n"
              "- 'Reference Object' - will do copper thieving within the area specified by another object.")
        )
        grid_lay.addWidget(self.reference_label, 10, 0)
        grid_lay.addWidget(self.reference_radio, 10, 1)

        # Bounding Box Type #
        self.bbox_type_radio = RadioSet([
            {'label': _('Rectangular'), 'value': 'rect'},
            {"label": _("Minimal"), "value": "min"}
        ], stretch=False)
        self.bbox_type_label = FCLabel('%s:' % _("Box Type"))
        self.bbox_type_label.setToolTip(
            _("- 'Rectangular' - the bounding box will be of rectangular shape.\n"
              "- 'Minimal' - the bounding box will be the convex hull shape.")
        )
        grid_lay.addWidget(self.bbox_type_label, 12, 0)
        grid_lay.addWidget(self.bbox_type_radio, 12, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line, 14, 0, 1, 2)

        # Fill Type
        self.fill_type_radio = RadioSet([
            {'label': _('Solid'), 'value': 'solid'},
            {"label": _("Dots Grid"), "value": "dot"},
            {"label": _("Squares Grid"), "value": "square"},
            {"label": _("Lines Grid"), "value": "line"}
        ], orientation='vertical', stretch=False)
        self.fill_type_label = FCLabel(_("Fill Type:"))
        self.fill_type_label.setToolTip(
            _("- 'Solid' - copper thieving will be a solid polygon.\n"
              "- 'Dots Grid' - the empty area will be filled with a pattern of dots.\n"
              "- 'Squares Grid' - the empty area will be filled with a pattern of squares.\n"
              "- 'Lines Grid' - the empty area will be filled with a pattern of lines.")
        )
        grid_lay.addWidget(self.fill_type_label, 16, 0)
        grid_lay.addWidget(self.fill_type_radio, 16, 1)

        self.dots_label = FCLabel('<b>%s</b>:' % _("Dots Grid Parameters"))
        grid_lay.addWidget(self.dots_label, 18, 0, 1, 2)

        # Dot diameter #
        self.dotdia_label = FCLabel('%s:' % _("Dia"))
        self.dotdia_label.setToolTip(
            _("Dot diameter in Dots Grid.")
        )
        self.dot_dia_entry = FCDoubleSpinner()
        self.dot_dia_entry.set_range(0.0, 10000.0000)
        self.dot_dia_entry.set_precision(self.decimals)
        self.dot_dia_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.dotdia_label, 20, 0)
        grid_lay.addWidget(self.dot_dia_entry, 20, 1)

        # Dot spacing #
        self.dotspacing_label = FCLabel('%s:' % _("Spacing"))
        self.dotspacing_label.setToolTip(
            _("Distance between each two dots in Dots Grid.")
        )
        self.dot_spacing_entry = FCDoubleSpinner()
        self.dot_spacing_entry.set_range(0.0, 10000.0000)
        self.dot_spacing_entry.set_precision(self.decimals)
        self.dot_spacing_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.dotspacing_label, 22, 0)
        grid_lay.addWidget(self.dot_spacing_entry, 22, 1)

        self.squares_label = FCLabel('<b>%s</b>:' % _("Squares Grid Parameters"))
        grid_lay.addWidget(self.squares_label, 24, 0, 1, 2)

        # Square Size #
        self.square_size_label = FCLabel('%s:' % _("Size"))
        self.square_size_label.setToolTip(
            _("Square side size in Squares Grid.")
        )
        self.square_size_entry = FCDoubleSpinner()
        self.square_size_entry.set_range(0.0, 10000.0000)
        self.square_size_entry.set_precision(self.decimals)
        self.square_size_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.square_size_label, 26, 0)
        grid_lay.addWidget(self.square_size_entry, 26, 1)

        # Squares spacing #
        self.squares_spacing_label = FCLabel('%s:' % _("Spacing"))
        self.squares_spacing_label.setToolTip(
            _("Distance between each two squares in Squares Grid.")
        )
        self.squares_spacing_entry = FCDoubleSpinner()
        self.squares_spacing_entry.set_range(0.0, 10000.0000)
        self.squares_spacing_entry.set_precision(self.decimals)
        self.squares_spacing_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.squares_spacing_label, 28, 0)
        grid_lay.addWidget(self.squares_spacing_entry, 28, 1)

        self.lines_label = FCLabel('<b>%s</b>:' % _("Lines Grid Parameters"))
        grid_lay.addWidget(self.lines_label, 30, 0, 1, 2)

        # Square Size #
        self.line_size_label = FCLabel('%s:' % _("Size"))
        self.line_size_label.setToolTip(
            _("Line thickness size in Lines Grid.")
        )
        self.line_size_entry = FCDoubleSpinner()
        self.line_size_entry.set_range(0.0, 10000.0000)
        self.line_size_entry.set_precision(self.decimals)
        self.line_size_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.line_size_label, 32, 0)
        grid_lay.addWidget(self.line_size_entry, 32, 1)

        # Lines spacing #
        self.lines_spacing_label = FCLabel('%s:' % _("Spacing"))
        self.lines_spacing_label.setToolTip(
            _("Distance between each two lines in Lines Grid.")
        )
        self.lines_spacing_entry = FCDoubleSpinner()
        self.lines_spacing_entry.set_range(0.0, 10000.0000)
        self.lines_spacing_entry.set_precision(self.decimals)
        self.lines_spacing_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.lines_spacing_label, 34, 0)
        grid_lay.addWidget(self.lines_spacing_entry, 34, 1)

        self.robber_bar_label = FCLabel('<b>%s</b>' % _('Robber Bar Parameters'))
        self.robber_bar_label.setToolTip(
            _("Parameters used for the robber bar.\n"
              "Robber bar = copper border to help in pattern hole plating.")
        )
        grid_lay.addWidget(self.robber_bar_label, 36, 0, 1, 2)

        # ROBBER BAR MARGIN #
        self.rb_margin_label = FCLabel('%s:' % _("Margin"))
        self.rb_margin_label.setToolTip(
            _("Bounding box margin for robber bar.")
        )
        self.rb_margin_entry = FCDoubleSpinner()
        self.rb_margin_entry.set_range(-10000.0000, 10000.0000)
        self.rb_margin_entry.set_precision(self.decimals)
        self.rb_margin_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.rb_margin_label, 38, 0)
        grid_lay.addWidget(self.rb_margin_entry, 38, 1)

        # THICKNESS #
        self.rb_thickness_label = FCLabel('%s:' % _("Thickness"))
        self.rb_thickness_label.setToolTip(
            _("The robber bar thickness.")
        )
        self.rb_thickness_entry = FCDoubleSpinner()
        self.rb_thickness_entry.set_range(0.0000, 10000.0000)
        self.rb_thickness_entry.set_precision(self.decimals)
        self.rb_thickness_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.rb_thickness_label, 40, 0)
        grid_lay.addWidget(self.rb_thickness_entry, 40, 1)

        self.patern_mask_label = FCLabel('<b>%s</b>' % _('Pattern Plating Mask'))
        self.patern_mask_label.setToolTip(
            _("Generate a mask for pattern plating.")
        )
        grid_lay.addWidget(self.patern_mask_label, 42, 0, 1, 2)

        # Openings CLEARANCE #
        self.clearance_ppm_label = FCLabel('%s:' % _("Clearance"))
        self.clearance_ppm_label.setToolTip(
            _("The distance between the possible copper thieving elements\n"
              "and/or robber bar and the actual openings in the mask.")
        )
        self.clearance_ppm_entry = FCDoubleSpinner()
        self.clearance_ppm_entry.set_range(-10000.0000, 10000.0000)
        self.clearance_ppm_entry.set_precision(self.decimals)
        self.clearance_ppm_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.clearance_ppm_label, 44, 0)
        grid_lay.addWidget(self.clearance_ppm_entry, 44, 1)

        # Include geometry
        self.ppm_choice_label = FCLabel('%s:' % _("Add"))
        self.ppm_choice_label.setToolTip(
            _("Choose which additional geometry to include, if available.")
        )
        self.ppm_choice_radio = RadioSet([
            {"label": _("Both"), "value": "b"},
            {'label': _('Thieving'), 'value': 't'},
            {"label": _("Robber bar"), "value": "r"},
            {"label": _("None"), "value": "n"}
        ], orientation='vertical', stretch=False)
        grid_lay.addWidget(self.ppm_choice_label, 46, 0)
        grid_lay.addWidget(self.ppm_choice_radio, 46, 1)

        self.layout.addStretch()
