from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings

from appGUI.GUIElements import FCDoubleSpinner, FCCheckBox, RadioSet, FCComboBox, FCLabel
from appGUI.preferences import machinist_setting
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


class ToolsCutoutPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "Cutout Tool Options", parent=parent)
        super(ToolsCutoutPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Cutout Tool Options")))
        self.decimals = decimals

        # ## Board cutout
        self.board_cutout_label = FCLabel("<b>%s:</b>" % _("Parameters"))
        self.board_cutout_label.setToolTip(
            _("Create toolpaths to cut around\n"
              "the PCB and separate it from\n"
              "the original board.")
        )
        self.layout.addWidget(self.board_cutout_label)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        tdclabel = FCLabel('%s:' % _('Tool Diameter'))
        tdclabel.setToolTip(
            _("Diameter of the tool used to cutout\n"
              "the PCB shape out of the surrounding material.")
        )

        self.cutout_tooldia_entry = FCDoubleSpinner()
        self.cutout_tooldia_entry.set_range(0.000001, 10000.0000)
        self.cutout_tooldia_entry.set_precision(self.decimals)
        self.cutout_tooldia_entry.setSingleStep(0.1)

        grid0.addWidget(tdclabel, 0, 0)
        grid0.addWidget(self.cutout_tooldia_entry, 0, 1)

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

        if machinist_setting == 0:
            self.cutz_entry.setRange(-10000.0000, 0.0000)
        else:
            self.cutz_entry.setRange(-10000.0000, 10000.0000)

        self.cutz_entry.setSingleStep(0.1)

        grid0.addWidget(cutzlabel, 1, 0)
        grid0.addWidget(self.cutz_entry, 1, 1)

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

        grid0.addWidget(self.mpass_cb, 2, 0)
        grid0.addWidget(self.maxdepth_entry, 2, 1)

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
        grid0.addWidget(kindlabel, 3, 0)
        grid0.addWidget(self.obj_kind_combo, 3, 1)

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

        grid0.addWidget(marginlabel, 4, 0)
        grid0.addWidget(self.cutout_margin_entry, 4, 1)
        
        # Gap Size
        gaplabel = FCLabel('%s:' % _('Gap size'))
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

        grid0.addWidget(gaplabel, 5, 0)
        grid0.addWidget(self.cutout_gap_entry, 5, 1)
        
        # Gap Type
        self.gaptype_label = FCLabel('%s:' % _("Gap type"))
        self.gaptype_label.setToolTip(
            _("The type of gap:\n"
              "- Bridge -> the cutout will be interrupted by bridges\n"
              "- Thin -> same as 'bridge' but it will be thinner by partially milling the gap\n"
              "- M-Bites -> 'Mouse Bites' - same as 'bridge' but covered with drill holes")
        )

        self.gaptype_radio = RadioSet(
            [
                {'label': _('Bridge'),      'value': 'b'},
                {'label': _('Thin'),        'value': 'bt'},
                {'label': "M-Bites",        'value': 'mb'}
            ],
            stretch=True
        )

        grid0.addWidget(self.gaptype_label, 7, 0)
        grid0.addWidget(self.gaptype_radio, 7, 1)

        # Thin gaps Depth
        self.thin_depth_label = FCLabel('%s:' % _("Depth"))
        self.thin_depth_label.setToolTip(
            _("The depth until the milling is done\n"
              "in order to thin the gaps.")
        )
        self.thin_depth_entry = FCDoubleSpinner()
        self.thin_depth_entry.set_precision(self.decimals)
        if machinist_setting == 0:
            self.thin_depth_entry.setRange(-10000.0000, -0.00001)
        else:
            self.thin_depth_entry.setRange(-10000.0000, 10000.0000)
        self.thin_depth_entry.setSingleStep(0.1)

        grid0.addWidget(self.thin_depth_label, 9, 0)
        grid0.addWidget(self.thin_depth_entry, 9, 1)

        # Mouse Bites Tool Diameter
        self.mb_dia_label = FCLabel('%s:' % _("Tool Diameter"))
        self.mb_dia_label.setToolTip(
            _("The drill hole diameter when doing mouse bites.")
        )
        self.mb_dia_entry = FCDoubleSpinner()
        self.mb_dia_entry.set_precision(self.decimals)
        self.mb_dia_entry.setRange(0, 100.0000)

        grid0.addWidget(self.mb_dia_label, 11, 0)
        grid0.addWidget(self.mb_dia_entry, 11, 1)

        # Mouse Bites Holes Spacing
        self.mb_spacing_label = FCLabel('%s:' % _("Spacing"))
        self.mb_spacing_label.setToolTip(
            _("The spacing between drill holes when doing mouse bites.")
        )
        self.mb_spacing_entry = FCDoubleSpinner()
        self.mb_spacing_entry.set_precision(self.decimals)
        self.mb_spacing_entry.setRange(0, 100.0000)

        grid0.addWidget(self.mb_spacing_label, 13, 0)
        grid0.addWidget(self.mb_spacing_entry, 13, 1)
        
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
        grid0.addWidget(gaps_label, 15, 0)
        grid0.addWidget(self.gaps_combo, 15, 1)

        gaps_items = ['None', 'LR', 'TB', '4', '2LR', '2TB', '8']
        for it in gaps_items:
            self.gaps_combo.addItem(it)
            # self.gaps_combo.setStyleSheet('background-color: rgb(255,255,255)')

        # Surrounding convex box shape
        self.convex_box = FCCheckBox('%s' % _("Convex Shape"))
        self.convex_box.setToolTip(
            _("Create a convex shape surrounding the entire PCB.\n"
              "Used only if the source object type is Gerber.")
        )
        grid0.addWidget(self.convex_box, 17, 0, 1, 2)

        self.big_cursor_cb = FCCheckBox('%s' % _("Big cursor"))
        self.big_cursor_cb.setToolTip(
            _("Use a big cursor when adding manual gaps."))
        grid0.addWidget(self.big_cursor_cb, 19, 0, 1, 2)

        self.layout.addStretch()
