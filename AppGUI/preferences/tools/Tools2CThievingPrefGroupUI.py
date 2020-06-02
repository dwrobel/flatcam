from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings

from AppGUI.GUIElements import FCSpinner, FCDoubleSpinner, RadioSet
from AppGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import AppTranslation as fcTranslate
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
        self.cflabel = QtWidgets.QLabel('<b>%s</b>' % _('Parameters'))
        self.cflabel.setToolTip(
            _("A tool to generate a Copper Thieving that can be added\n"
              "to a selected Gerber file.")
        )
        grid_lay.addWidget(self.cflabel, 0, 0, 1, 2)

        # CIRCLE STEPS - to be used when buffering
        self.circle_steps_lbl = QtWidgets.QLabel('%s:' % _("Circle Steps"))
        self.circle_steps_lbl.setToolTip(
            _("Number of steps (lines) used to interpolate circles.")
        )

        self.circlesteps_entry = FCSpinner()
        self.circlesteps_entry.set_range(1, 9999)

        grid_lay.addWidget(self.circle_steps_lbl, 1, 0)
        grid_lay.addWidget(self.circlesteps_entry, 1, 1)

        # CLEARANCE #
        self.clearance_label = QtWidgets.QLabel('%s:' % _("Clearance"))
        self.clearance_label.setToolTip(
            _("This set the distance between the copper Thieving components\n"
              "(the polygon fill may be split in multiple polygons)\n"
              "and the copper traces in the Gerber file.")
        )
        self.clearance_entry = FCDoubleSpinner()
        self.clearance_entry.setMinimum(0.00001)
        self.clearance_entry.set_precision(self.decimals)
        self.clearance_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.clearance_label, 2, 0)
        grid_lay.addWidget(self.clearance_entry, 2, 1)

        # MARGIN #
        self.margin_label = QtWidgets.QLabel('%s:' % _("Margin"))
        self.margin_label.setToolTip(
            _("Bounding box margin.")
        )
        self.margin_entry = FCDoubleSpinner()
        self.margin_entry.setMinimum(0.0)
        self.margin_entry.set_precision(self.decimals)
        self.margin_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.margin_label, 3, 0)
        grid_lay.addWidget(self.margin_entry, 3, 1)

        # Reference #
        self.reference_radio = RadioSet([
            {'label': _('Itself'), 'value': 'itself'},
            {"label": _("Area Selection"), "value": "area"},
            {'label': _("Reference Object"), 'value': 'box'}
        ], orientation='vertical', stretch=False)
        self.reference_label = QtWidgets.QLabel(_("Reference:"))
        self.reference_label.setToolTip(
            _("- 'Itself' - the copper Thieving extent is based on the object extent.\n"
              "- 'Area Selection' - left mouse click to start selection of the area to be filled.\n"
              "- 'Reference Object' - will do copper thieving within the area specified by another object.")
        )
        grid_lay.addWidget(self.reference_label, 4, 0)
        grid_lay.addWidget(self.reference_radio, 4, 1)

        # Bounding Box Type #
        self.bbox_type_radio = RadioSet([
            {'label': _('Rectangular'), 'value': 'rect'},
            {"label": _("Minimal"), "value": "min"}
        ], stretch=False)
        self.bbox_type_label = QtWidgets.QLabel(_("Box Type:"))
        self.bbox_type_label.setToolTip(
            _("- 'Rectangular' - the bounding box will be of rectangular shape.\n"
              "- 'Minimal' - the bounding box will be the convex hull shape.")
        )
        grid_lay.addWidget(self.bbox_type_label, 5, 0)
        grid_lay.addWidget(self.bbox_type_radio, 5, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line, 6, 0, 1, 2)

        # Fill Type
        self.fill_type_radio = RadioSet([
            {'label': _('Solid'), 'value': 'solid'},
            {"label": _("Dots Grid"), "value": "dot"},
            {"label": _("Squares Grid"), "value": "square"},
            {"label": _("Lines Grid"), "value": "line"}
        ], orientation='vertical', stretch=False)
        self.fill_type_label = QtWidgets.QLabel(_("Fill Type:"))
        self.fill_type_label.setToolTip(
            _("- 'Solid' - copper thieving will be a solid polygon.\n"
              "- 'Dots Grid' - the empty area will be filled with a pattern of dots.\n"
              "- 'Squares Grid' - the empty area will be filled with a pattern of squares.\n"
              "- 'Lines Grid' - the empty area will be filled with a pattern of lines.")
        )
        grid_lay.addWidget(self.fill_type_label, 7, 0)
        grid_lay.addWidget(self.fill_type_radio, 7, 1)

        self.dots_label = QtWidgets.QLabel('<b>%s</b>:' % _("Dots Grid Parameters"))
        grid_lay.addWidget(self.dots_label, 8, 0, 1, 2)

        # Dot diameter #
        self.dotdia_label = QtWidgets.QLabel('%s:' % _("Dia"))
        self.dotdia_label.setToolTip(
            _("Dot diameter in Dots Grid.")
        )
        self.dot_dia_entry = FCDoubleSpinner()
        self.dot_dia_entry.set_range(0.0, 9999.9999)
        self.dot_dia_entry.set_precision(self.decimals)
        self.dot_dia_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.dotdia_label, 9, 0)
        grid_lay.addWidget(self.dot_dia_entry, 9, 1)

        # Dot spacing #
        self.dotspacing_label = QtWidgets.QLabel('%s:' % _("Spacing"))
        self.dotspacing_label.setToolTip(
            _("Distance between each two dots in Dots Grid.")
        )
        self.dot_spacing_entry = FCDoubleSpinner()
        self.dot_spacing_entry.set_range(0.0, 9999.9999)
        self.dot_spacing_entry.set_precision(self.decimals)
        self.dot_spacing_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.dotspacing_label, 10, 0)
        grid_lay.addWidget(self.dot_spacing_entry, 10, 1)

        self.squares_label = QtWidgets.QLabel('<b>%s</b>:' % _("Squares Grid Parameters"))
        grid_lay.addWidget(self.squares_label, 11, 0, 1, 2)

        # Square Size #
        self.square_size_label = QtWidgets.QLabel('%s:' % _("Size"))
        self.square_size_label.setToolTip(
            _("Square side size in Squares Grid.")
        )
        self.square_size_entry = FCDoubleSpinner()
        self.square_size_entry.set_range(0.0, 9999.9999)
        self.square_size_entry.set_precision(self.decimals)
        self.square_size_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.square_size_label, 12, 0)
        grid_lay.addWidget(self.square_size_entry, 12, 1)

        # Squares spacing #
        self.squares_spacing_label = QtWidgets.QLabel('%s:' % _("Spacing"))
        self.squares_spacing_label.setToolTip(
            _("Distance between each two squares in Squares Grid.")
        )
        self.squares_spacing_entry = FCDoubleSpinner()
        self.squares_spacing_entry.set_range(0.0, 9999.9999)
        self.squares_spacing_entry.set_precision(self.decimals)
        self.squares_spacing_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.squares_spacing_label, 13, 0)
        grid_lay.addWidget(self.squares_spacing_entry, 13, 1)

        self.lines_label = QtWidgets.QLabel('<b>%s</b>:' % _("Lines Grid Parameters"))
        grid_lay.addWidget(self.lines_label, 14, 0, 1, 2)

        # Square Size #
        self.line_size_label = QtWidgets.QLabel('%s:' % _("Size"))
        self.line_size_label.setToolTip(
            _("Line thickness size in Lines Grid.")
        )
        self.line_size_entry = FCDoubleSpinner()
        self.line_size_entry.set_range(0.0, 9999.9999)
        self.line_size_entry.set_precision(self.decimals)
        self.line_size_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.line_size_label, 15, 0)
        grid_lay.addWidget(self.line_size_entry, 15, 1)

        # Lines spacing #
        self.lines_spacing_label = QtWidgets.QLabel('%s:' % _("Spacing"))
        self.lines_spacing_label.setToolTip(
            _("Distance between each two lines in Lines Grid.")
        )
        self.lines_spacing_entry = FCDoubleSpinner()
        self.lines_spacing_entry.set_range(0.0, 9999.9999)
        self.lines_spacing_entry.set_precision(self.decimals)
        self.lines_spacing_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.lines_spacing_label, 16, 0)
        grid_lay.addWidget(self.lines_spacing_entry, 16, 1)

        self.robber_bar_label = QtWidgets.QLabel('<b>%s</b>' % _('Robber Bar Parameters'))
        self.robber_bar_label.setToolTip(
            _("Parameters used for the robber bar.\n"
              "Robber bar = copper border to help in pattern hole plating.")
        )
        grid_lay.addWidget(self.robber_bar_label, 17, 0, 1, 2)

        # ROBBER BAR MARGIN #
        self.rb_margin_label = QtWidgets.QLabel('%s:' % _("Margin"))
        self.rb_margin_label.setToolTip(
            _("Bounding box margin for robber bar.")
        )
        self.rb_margin_entry = FCDoubleSpinner()
        self.rb_margin_entry.set_range(-9999.9999, 9999.9999)
        self.rb_margin_entry.set_precision(self.decimals)
        self.rb_margin_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.rb_margin_label, 18, 0)
        grid_lay.addWidget(self.rb_margin_entry, 18, 1)

        # THICKNESS #
        self.rb_thickness_label = QtWidgets.QLabel('%s:' % _("Thickness"))
        self.rb_thickness_label.setToolTip(
            _("The robber bar thickness.")
        )
        self.rb_thickness_entry = FCDoubleSpinner()
        self.rb_thickness_entry.set_range(0.0000, 9999.9999)
        self.rb_thickness_entry.set_precision(self.decimals)
        self.rb_thickness_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.rb_thickness_label, 19, 0)
        grid_lay.addWidget(self.rb_thickness_entry, 19, 1)

        self.patern_mask_label = QtWidgets.QLabel('<b>%s</b>' % _('Pattern Plating Mask'))
        self.patern_mask_label.setToolTip(
            _("Generate a mask for pattern plating.")
        )
        grid_lay.addWidget(self.patern_mask_label, 20, 0, 1, 2)

        # Openings CLEARANCE #
        self.clearance_ppm_label = QtWidgets.QLabel('%s:' % _("Clearance"))
        self.clearance_ppm_label.setToolTip(
            _("The distance between the possible copper thieving elements\n"
              "and/or robber bar and the actual openings in the mask.")
        )
        self.clearance_ppm_entry = FCDoubleSpinner()
        self.clearance_ppm_entry.set_range(-9999.9999, 9999.9999)
        self.clearance_ppm_entry.set_precision(self.decimals)
        self.clearance_ppm_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.clearance_ppm_label, 21, 0)
        grid_lay.addWidget(self.clearance_ppm_entry, 21, 1)

        self.layout.addStretch()
