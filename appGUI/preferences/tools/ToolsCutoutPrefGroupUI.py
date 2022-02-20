from PyQt6 import QtWidgets

from appGUI.GUIElements import FCDoubleSpinner, FCCheckBox, RadioSet, FCComboBox, FCLabel, OptionalInputSection, \
    FCGridLayout, FCFrame, FCComboBox2
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ToolsCutoutPrefGroupUI(OptionsGroupUI):
    def __init__(self, app, parent=None):
        # OptionsGroupUI.__init__(self, "Cutout Plugin", parent=parent)
        super(ToolsCutoutPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Cutout Plugin")))
        self.decimals = app.decimals
        self.options = app.options

        # ## Board cutout
        self.board_cutout_label = FCLabel('<span style="color:blue;"><b>%s</b></span>' % _("Parameters"))
        self.board_cutout_label.setToolTip(
            _("Create toolpaths to cut around\n"
              "the PCB and separate it from\n"
              "the original board.")
        )
        self.layout.addWidget(self.board_cutout_label)

        # #############################################################################################################
        # Tool Params Frame
        # #############################################################################################################
        tool_par_frame = FCFrame()
        self.layout.addWidget(tool_par_frame)

        param_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        tool_par_frame.setLayout(param_grid)

        # Tool Diameter
        tdclabel = FCLabel('%s:' % _('Tool Dia'))
        tdclabel.setToolTip(
            _("Diameter of the tool used to cutout\n"
              "the PCB shape out of the surrounding material.")
        )

        self.cutout_tooldia_entry = FCDoubleSpinner()
        self.cutout_tooldia_entry.set_range(0.000001, 10000.0000)
        self.cutout_tooldia_entry.set_precision(self.decimals)
        self.cutout_tooldia_entry.setSingleStep(0.1)

        param_grid.addWidget(tdclabel, 0, 0)
        param_grid.addWidget(self.cutout_tooldia_entry, 0, 1)

        # Convex box shape
        self.convex_box = FCCheckBox('%s' % _("Convex Shape"))
        self.convex_box.setToolTip(
            _("Create a convex shape surrounding the entire PCB.\n"
              "Used only if the source object type is Gerber.")
        )
        param_grid.addWidget(self.convex_box, 2, 0, 1, 2)

        # Cut Z
        cutzlabel = FCLabel('%s:' % _('Cut Z'))
        cutzlabel.setToolTip(
            _(
                "Cutting depth (negative)\n"
                "below the copper surface."
            )
        )
        self.cutz_entry = FCDoubleSpinner()
        self.cutz_entry.set_precision(self.decimals)
        self.cutz_entry.setRange(-10000.0000, 10000.0000)

        self.cutz_entry.setSingleStep(0.1)

        param_grid.addWidget(cutzlabel, 4, 0)
        param_grid.addWidget(self.cutz_entry, 4, 1)

        # Multi-pass
        self.mpass_cb = FCCheckBox('%s:' % _("Multi-Depth"))
        self.mpass_cb.setToolTip(
            _(
                "Use multiple passes to limit\n"
                "the cut depth in each pass. Will\n"
                "cut multiple times until Cut Z is\n"
                "reached."
            )
        )

        self.maxdepth_entry = FCDoubleSpinner()
        self.maxdepth_entry.set_precision(self.decimals)
        self.maxdepth_entry.setRange(0, 10000.0000)
        self.maxdepth_entry.setSingleStep(0.1)

        self.maxdepth_entry.setToolTip(_("Depth of each pass (positive)."))

        param_grid.addWidget(self.mpass_cb, 6, 0)
        param_grid.addWidget(self.maxdepth_entry, 6, 1)

        self.ois_md = OptionalInputSection(self.mpass_cb, [self.maxdepth_entry])

        # Object kind
        kindlabel = FCLabel('%s:' % _('Kind'))
        kindlabel.setToolTip(
            _("Choice of what kind the object we want to cutout is.\n"
              "- Single: contain a single PCB Gerber outline object.\n"
              "- Panel: a panel PCB Gerber object, which is made\n"
              "out of many individual PCB outlines.")
        )

        self.obj_kind_combo = RadioSet([
            {"label": _("Single"), "value": "single"},
            {"label": _("Panel"), "value": "panel"},
        ])
        param_grid.addWidget(kindlabel, 8, 0)
        param_grid.addWidget(self.obj_kind_combo, 8, 1)

        marginlabel = FCLabel('%s:' % _('Margin'))
        marginlabel.setToolTip(
            _("Margin over bounds. A positive value here\n"
              "will make the cutout of the PCB further from\n"
              "the actual PCB border")
        )

        self.cutout_margin_entry = FCDoubleSpinner()
        self.cutout_margin_entry.set_range(-10000.0000, 10000.0000)
        self.cutout_margin_entry.set_precision(self.decimals)
        self.cutout_margin_entry.setSingleStep(0.1)

        param_grid.addWidget(marginlabel, 10, 0)
        param_grid.addWidget(self.cutout_margin_entry, 10, 1)

        self.gaps_label = FCLabel('<span style="color:green;"><b>%s</b></span>' % _("Gaps"))
        self.layout.addWidget(self.gaps_label)
        # #############################################################################################################
        # Gaps Frame
        # #############################################################################################################
        gaps_frame = FCFrame()
        self.layout.addWidget(gaps_frame)

        # Grid Layout
        gaps_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        gaps_frame.setLayout(gaps_grid)

        # Gap Size
        gaplabel = FCLabel('%s:' % _('Size'))
        gaplabel.setToolTip(
            _("The size of the bridge gaps in the cutout\n"
              "used to keep the board connected to\n"
              "the surrounding material (the one \n"
              "from which the PCB is cutout).")
        )

        self.cutout_gap_entry = FCDoubleSpinner()
        self.cutout_gap_entry.set_range(0.000001, 10000.0000)
        self.cutout_gap_entry.set_precision(self.decimals)
        self.cutout_gap_entry.setSingleStep(0.1)

        gaps_grid.addWidget(gaplabel, 0, 0)
        gaps_grid.addWidget(self.cutout_gap_entry, 0, 1)
        
        # Gap Type
        self.gaptype_label = FCLabel('%s:' % _("Type"))
        self.gaptype_label.setToolTip(
            _("The type of gap:\n"
              "- Bridge -> the cutout will be interrupted by bridges\n"
              "- Thin -> same as 'bridge' but it will be thinner by partially milling the gap\n"
              "- M-Bites -> 'Mouse Bites' - same as 'bridge' but covered with drill holes")
        )

        self.gaptype_combo = FCComboBox2()
        self.gaptype_combo.addItems([_('Bridge'), _('Thin'), _("Mouse Bytes")])

        gaps_grid.addWidget(self.gaptype_label, 2, 0)
        gaps_grid.addWidget(self.gaptype_combo, 2, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        gaps_grid.addWidget(separator_line, 4, 0, 1, 2)

        # Thin gaps Depth
        self.thin_depth_label = FCLabel('%s:' % _("Depth"))
        self.thin_depth_label.setToolTip(
            _("The depth until the milling is done\n"
              "in order to thin the gaps.")
        )
        self.thin_depth_entry = FCDoubleSpinner()
        self.thin_depth_entry.set_precision(self.decimals)
        self.thin_depth_entry.setRange(-10000.0000, 10000.0000)
        self.thin_depth_entry.setSingleStep(0.1)

        gaps_grid.addWidget(self.thin_depth_label, 6, 0)
        gaps_grid.addWidget(self.thin_depth_entry, 6, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        gaps_grid.addWidget(separator_line, 8, 0, 1, 2)

        # Mouse Bites Tool Diameter
        self.mb_dia_label = FCLabel('%s:' % _("Tool Diameter"))
        self.mb_dia_label.setToolTip(
            _("The drill hole diameter when doing mouse bites.")
        )
        self.mb_dia_entry = FCDoubleSpinner()
        self.mb_dia_entry.set_precision(self.decimals)
        self.mb_dia_entry.setRange(0, 100.0000)

        gaps_grid.addWidget(self.mb_dia_label, 10, 0)
        gaps_grid.addWidget(self.mb_dia_entry, 10, 1)

        # Mouse Bites Holes Spacing
        self.mb_spacing_label = FCLabel('%s:' % _("Spacing"))
        self.mb_spacing_label.setToolTip(
            _("The spacing between drill holes when doing mouse bites.")
        )
        self.mb_spacing_entry = FCDoubleSpinner()
        self.mb_spacing_entry.set_precision(self.decimals)
        self.mb_spacing_entry.setRange(0, 100.0000)

        gaps_grid.addWidget(self.mb_spacing_label, 12, 0)
        gaps_grid.addWidget(self.mb_spacing_entry, 12, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        gaps_grid.addWidget(separator_line, 14, 0, 1, 2)

        gaps_label = FCLabel('%s:' % _('Gaps'))
        gaps_label.setToolTip(
            _("Number of gaps used for the cutout.\n"
              "There can be maximum 8 bridges/gaps.\n"
              "The choices are:\n"
              "- None  - no gaps\n"
              "- lr    - left + right\n"
              "- tb    - top + bottom\n"
              "- 4     - left + right +top + bottom\n"
              "- 2lr   - 2*left + 2*right\n"
              "- 2tb  - 2*top + 2*bottom\n"
              "- 8     - 2*left + 2*right +2*top + 2*bottom")
        )

        self.gaps_combo = FCComboBox()
        gaps_grid.addWidget(gaps_label, 16, 0)
        gaps_grid.addWidget(self.gaps_combo, 16, 1)

        gaps_items = ['None', 'LR', 'TB', '4', '2LR', '2TB', '8']
        for it in gaps_items:
            self.gaps_combo.addItem(it)
            # self.gaps_combo.setStyleSheet('background-color: rgb(255,255,255)')

        self.big_cursor_cb = FCCheckBox('%s' % _("Big cursor"))
        self.big_cursor_cb.setToolTip(
            _("Use a big cursor when adding manual gaps."))
        gaps_grid.addWidget(self.big_cursor_cb, 18, 0, 1, 2)

        # Cut by Drilling Title
        self.title_drillcut_label = FCLabel('<span style="color:red;"><b>%s</b></span>' % _('Cut by Drilling'))
        self.title_drillcut_label.setToolTip(_("Create a series of drill holes following a geometry line."))
        self.layout.addWidget(self.title_drillcut_label)

        # #############################################################################################################
        # Cut by Drilling Frame
        # #############################################################################################################
        self.drill_cut_frame = FCFrame()
        self.layout.addWidget(self.drill_cut_frame)

        # Grid Layout
        drill_cut_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        self.drill_cut_frame.setLayout(drill_cut_grid)

        # Drill Tool Diameter
        self.drill_dia_entry = FCDoubleSpinner()
        self.drill_dia_entry.set_precision(self.decimals)
        self.drill_dia_entry.set_range(0.0000, 10000.0000)

        self.drill_dia_label = FCLabel('%s:' % _("Drill Dia"))
        self.drill_dia_label.setToolTip(
            _("Diameter of the tool used to cutout\n"
              "the PCB by drilling.")
        )
        drill_cut_grid.addWidget(self.drill_dia_label, 0, 0)
        drill_cut_grid.addWidget(self.drill_dia_entry, 0, 1)

        # Drill Tool Pitch
        self.drill_pitch_entry = FCDoubleSpinner()
        self.drill_pitch_entry.set_precision(self.decimals)
        self.drill_pitch_entry.set_range(0.0000, 10000.0000)

        self.drill_pitch_label = FCLabel('%s:' % _("Pitch"))
        self.drill_pitch_label.setToolTip(
            _("Distance between the center of\n"
              "two neighboring drill holes.")
        )
        drill_cut_grid.addWidget(self.drill_pitch_label, 2, 0)
        drill_cut_grid.addWidget(self.drill_pitch_entry, 2, 1)

        # Drill Tool Margin
        self.drill_margin_entry = FCDoubleSpinner()
        self.drill_margin_entry.set_precision(self.decimals)
        self.drill_margin_entry.set_range(0.0000, 10000.0000)

        self.drill_margin_label = FCLabel('%s:' % _("Margin"))
        self.drill_margin_label.setToolTip(
            _("Margin over bounds. A positive value here\n"
              "will make the cutout of the PCB further from\n"
              "the actual PCB border")
        )
        drill_cut_grid.addWidget(self.drill_margin_label, 4, 0)
        drill_cut_grid.addWidget(self.drill_margin_entry, 4, 1)

        FCGridLayout.set_common_column_size([param_grid, drill_cut_grid, gaps_grid], 0)


        # self.layout.addStretch()
