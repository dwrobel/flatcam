from PyQt6 import QtWidgets

from appGUI.GUIElements import FCSpinner, FCDoubleSpinner, RadioSet, FCLabel, FCCheckBox, FCGridLayout, FCFrame, \
    FCComboBox2
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class Tools2CThievingPrefGroupUI(OptionsGroupUI):
    def __init__(self, defaults, decimals=4, parent=None):

        super(Tools2CThievingPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Copper Thieving Plugin")))
        self.decimals = decimals
        self.defaults = defaults

        # #############################################################################################################
        # Parameters Frame
        # #############################################################################################################
        self.param_label = FCLabel('<span style="color:blue;"><b>%s</b></span>' % _('Parameters'))
        self.param_label.setToolTip(
            _("A tool to generate a Copper Thieving that can be added\n"
              "to a selected Gerber file.")
        )
        self.layout.addWidget(self.param_label)

        par_frame = FCFrame()
        self.layout.addWidget(par_frame)

        # ## Grid Layout
        grid_par = FCGridLayout(v_spacing=5, h_spacing=3)
        par_frame.setLayout(grid_par)

        # CIRCLE STEPS - to be used when buffering
        self.circle_steps_lbl = FCLabel('%s:' % _("Circle Steps"))
        self.circle_steps_lbl.setToolTip(
            _("Number of steps (lines) used to interpolate circles.")
        )

        self.circlesteps_entry = FCSpinner()
        self.circlesteps_entry.set_range(1, 10000)

        grid_par.addWidget(self.circle_steps_lbl, 2, 0)
        grid_par.addWidget(self.circlesteps_entry, 2, 1)

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

        grid_par.addWidget(self.clearance_label, 4, 0)
        grid_par.addWidget(self.clearance_entry, 4, 1)

        # MARGIN #
        self.margin_label = FCLabel('%s:' % _("Margin"))
        self.margin_label.setToolTip(
            _("Bounding box margin.")
        )
        self.margin_entry = FCDoubleSpinner()
        self.margin_entry.setMinimum(0.0)
        self.margin_entry.set_precision(self.decimals)
        self.margin_entry.setSingleStep(0.1)

        grid_par.addWidget(self.margin_label, 6, 0)
        grid_par.addWidget(self.margin_entry, 6, 1)

        # Area #
        self.area_label = FCLabel('%s:' % _("Area"))
        self.area_label.setToolTip(
            _("Thieving areas with area less then this value will not be added.")
        )
        self.area_entry = FCDoubleSpinner()
        self.area_entry.set_range(0.0, 10000.0000)
        self.area_entry.set_precision(self.decimals)
        self.area_entry.setSingleStep(0.1)

        grid_par.addWidget(self.area_label, 8, 0)
        grid_par.addWidget(self.area_entry, 8, 1)
        
        # Reference #
        # Reference #
        self.reference_label = FCLabel(_("Reference:"))
        self.reference_label.setToolTip(
            _("- 'Itself' - the copper thieving extent is based on the object extent.\n"
              "- 'Area Selection' - left mouse click to start selection of the area to be filled.\n"
              "- 'Reference Object' - will do copper thieving within the area specified by another object.")
        )
        self.reference_combo = FCComboBox2()
        self.reference_combo.addItems([_('Itself'), _("Area Selection"), _("Reference Object")])

        grid_par.addWidget(self.reference_label, 10, 0)
        grid_par.addWidget(self.reference_combo, 10, 1)

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
        grid_par.addWidget(self.bbox_type_label, 12, 0)
        grid_par.addWidget(self.bbox_type_radio, 12, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        grid_par.addWidget(separator_line, 14, 0, 1, 2)

        # Fill Type
        self.fill_type_label = FCLabel('%s:' % _("Fill"))
        self.fill_type_label.setToolTip(
            _("- 'Solid' - copper thieving will be a solid polygon.\n"
              "- 'Dots Grid' - the empty area will be filled with a pattern of dots.\n"
              "- 'Squares Grid' - the empty area will be filled with a pattern of squares.\n"
              "- 'Lines Grid' - the empty area will be filled with a pattern of lines.")
        )

        self.fill_type_combo = FCComboBox2()
        self.fill_type_combo.addItems([_('Solid'), _("Dots Grid"), _("Squares Grid"), _("Lines Grid")])

        grid_par.addWidget(self.fill_type_label, 16, 0)
        grid_par.addWidget(self.fill_type_combo, 16, 1)

        # #############################################################################################################
        # DOTS Grid Parameters Frame
        # #############################################################################################################
        self.dots_label = FCLabel('<b>%s</b>:' % _("Dots Grid Parameters"))
        self.layout.addWidget(self.dots_label)

        dots_frame = FCFrame()
        self.layout.addWidget(dots_frame)

        # ## Grid Layout
        grid_dots = FCGridLayout(v_spacing=5, h_spacing=3)
        dots_frame.setLayout(grid_dots)

        # Dot diameter #
        self.dotdia_label = FCLabel('%s:' % _("Dia"))
        self.dotdia_label.setToolTip(
            _("Dot diameter in Dots Grid.")
        )
        self.dot_dia_entry = FCDoubleSpinner()
        self.dot_dia_entry.set_range(0.0, 10000.0000)
        self.dot_dia_entry.set_precision(self.decimals)
        self.dot_dia_entry.setSingleStep(0.1)

        grid_dots.addWidget(self.dotdia_label, 0, 0)
        grid_dots.addWidget(self.dot_dia_entry, 0, 1)

        # Dot spacing #
        self.dotspacing_label = FCLabel('%s:' % _("Spacing"))
        self.dotspacing_label.setToolTip(
            _("Distance between each two dots in Dots Grid.")
        )
        self.dot_spacing_entry = FCDoubleSpinner()
        self.dot_spacing_entry.set_range(0.0, 10000.0000)
        self.dot_spacing_entry.set_precision(self.decimals)
        self.dot_spacing_entry.setSingleStep(0.1)

        grid_dots.addWidget(self.dotspacing_label, 2, 0)
        grid_dots.addWidget(self.dot_spacing_entry, 2, 1)

        # #############################################################################################################
        # Squares Grid Parameters Frame
        # #############################################################################################################
        self.squares_label = FCLabel('<b>%s</b>:' % _("Squares Grid Parameters"))
        self.layout.addWidget(self.squares_label)

        square_frame = FCFrame()
        self.layout.addWidget(square_frame)

        # ## Grid Layout
        grid_square = FCGridLayout(v_spacing=5, h_spacing=3)
        square_frame.setLayout(grid_square)

        # Square Size #
        self.square_size_label = FCLabel('%s:' % _("Size"))
        self.square_size_label.setToolTip(
            _("Square side size in Squares Grid.")
        )
        self.square_size_entry = FCDoubleSpinner()
        self.square_size_entry.set_range(0.0, 10000.0000)
        self.square_size_entry.set_precision(self.decimals)
        self.square_size_entry.setSingleStep(0.1)

        grid_square.addWidget(self.square_size_label, 0, 0)
        grid_square.addWidget(self.square_size_entry, 0, 1)

        # Squares spacing #
        self.squares_spacing_label = FCLabel('%s:' % _("Spacing"))
        self.squares_spacing_label.setToolTip(
            _("Distance between each two squares in Squares Grid.")
        )
        self.squares_spacing_entry = FCDoubleSpinner()
        self.squares_spacing_entry.set_range(0.0, 10000.0000)
        self.squares_spacing_entry.set_precision(self.decimals)
        self.squares_spacing_entry.setSingleStep(0.1)

        grid_square.addWidget(self.squares_spacing_label, 2, 0)
        grid_square.addWidget(self.squares_spacing_entry, 2, 1)

        # #############################################################################################################
        # Lines Grid Parameters Frame
        # #############################################################################################################
        self.lines_label = FCLabel('<b>%s</b>:' % _("Lines Grid Parameters"))
        self.layout.addWidget(self.lines_label)

        line_frame = FCFrame()
        self.layout.addWidget(line_frame)

        # ## Grid Layout
        grid_line = FCGridLayout(v_spacing=5, h_spacing=3)
        line_frame.setLayout(grid_line)

        # Line Size #
        self.line_size_label = FCLabel('%s:' % _("Size"))
        self.line_size_label.setToolTip(
            _("Line thickness size in Lines Grid.")
        )
        self.line_size_entry = FCDoubleSpinner()
        self.line_size_entry.set_range(0.0, 10000.0000)
        self.line_size_entry.set_precision(self.decimals)
        self.line_size_entry.setSingleStep(0.1)

        grid_line.addWidget(self.line_size_label, 0, 0)
        grid_line.addWidget(self.line_size_entry, 0, 1)

        # Lines spacing #
        self.lines_spacing_label = FCLabel('%s:' % _("Spacing"))
        self.lines_spacing_label.setToolTip(
            _("Distance between each two lines in Lines Grid.")
        )
        self.lines_spacing_entry = FCDoubleSpinner()
        self.lines_spacing_entry.set_range(0.0, 10000.0000)
        self.lines_spacing_entry.set_precision(self.decimals)
        self.lines_spacing_entry.setSingleStep(0.1)

        grid_line.addWidget(self.lines_spacing_label, 2, 0)
        grid_line.addWidget(self.lines_spacing_entry, 2, 1)

        # #############################################################################################################
        # Robber Bar Parameters Frame
        # #############################################################################################################
        self.robber_bar_label = FCLabel('<b>%s</b>' % _('Robber Bar Parameters'))
        self.robber_bar_label.setToolTip(
            _("Parameters used for the robber bar.\n"
              "Robber bar = copper border to help in pattern hole plating.")
        )
        self.layout.addWidget(self.robber_bar_label)

        rob_frame = FCFrame()
        self.layout.addWidget(rob_frame)

        # ## Grid Layout
        grid_robber = FCGridLayout(v_spacing=5, h_spacing=3)
        rob_frame.setLayout(grid_robber)

        # ROBBER BAR MARGIN #
        self.rb_margin_label = FCLabel('%s:' % _("Margin"))
        self.rb_margin_label.setToolTip(
            _("Bounding box margin for robber bar.")
        )
        self.rb_margin_entry = FCDoubleSpinner()
        self.rb_margin_entry.set_range(-10000.0000, 10000.0000)
        self.rb_margin_entry.set_precision(self.decimals)
        self.rb_margin_entry.setSingleStep(0.1)

        grid_robber.addWidget(self.rb_margin_label, 0, 0)
        grid_robber.addWidget(self.rb_margin_entry, 0, 1)

        # THICKNESS #
        self.rb_thickness_label = FCLabel('%s:' % _("Thickness"))
        self.rb_thickness_label.setToolTip(
            _("The robber bar thickness.")
        )
        self.rb_thickness_entry = FCDoubleSpinner()
        self.rb_thickness_entry.set_range(0.0000, 10000.0000)
        self.rb_thickness_entry.set_precision(self.decimals)
        self.rb_thickness_entry.setSingleStep(0.1)

        grid_robber.addWidget(self.rb_thickness_label, 2, 0)
        grid_robber.addWidget(self.rb_thickness_entry, 2, 1)

        # #############################################################################################################
        # RPattern Plating Mask Parameters Frame
        # #############################################################################################################
        self.patern_mask_label = FCLabel('<b>%s</b>' % _('Pattern Plating Mask'))
        self.patern_mask_label.setToolTip(
            _("Generate a mask for pattern plating.")
        )
        self.layout.addWidget(self.patern_mask_label)

        ppm_frame = FCFrame()
        self.layout.addWidget(ppm_frame)

        # ## Grid Layout
        grid_ppm = FCGridLayout(v_spacing=5, h_spacing=3)
        ppm_frame.setLayout(grid_ppm)

        # Use Only Pads
        self.only_pads_cb = FCCheckBox(_("Only Pads"))
        self.only_pads_cb.setToolTip(
            _("Select only pads in case the selected object is a copper Gerber.")
        )
        grid_ppm.addWidget(self.only_pads_cb, 0, 0, 1, 2)

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

        grid_ppm.addWidget(self.clearance_ppm_label, 2, 0)
        grid_ppm.addWidget(self.clearance_ppm_entry, 2, 1)

        # Include geometry
        self.ppm_choice_label = FCLabel('%s:' % _("Add"))
        self.ppm_choice_label.setToolTip(
            _("Choose which additional geometry to include, if available.")
        )
        self.ppm_choice_combo = FCComboBox2()
        self.ppm_choice_combo.addItems([_("Both"), _('Thieving'), _("Robber bar"), _("None")])
        grid_ppm.addWidget(self.ppm_choice_label, 4, 0)
        grid_ppm.addWidget(self.ppm_choice_combo, 4, 1)

        self.layout.addStretch()
