from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings

from AppGUI.GUIElements import FCDoubleSpinner, FCCheckBox, RadioSet, FCComboBox
from AppGUI.preferences import machinist_setting
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


class ToolsCutoutPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "Cutout Tool Options", parent=parent)
        super(ToolsCutoutPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Cutout Tool Options")))
        self.decimals = decimals

        # ## Board cutout
        self.board_cutout_label = QtWidgets.QLabel("<b>%s:</b>" % _("Parameters"))
        self.board_cutout_label.setToolTip(
            _("Create toolpaths to cut around\n"
              "the PCB and separate it from\n"
              "the original board.")
        )
        self.layout.addWidget(self.board_cutout_label)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        tdclabel = QtWidgets.QLabel('%s:' % _('Tool Diameter'))
        tdclabel.setToolTip(
            _("Diameter of the tool used to cutout\n"
              "the PCB shape out of the surrounding material.")
        )

        self.cutout_tooldia_entry = FCDoubleSpinner()
        self.cutout_tooldia_entry.set_range(0.000001, 9999.9999)
        self.cutout_tooldia_entry.set_precision(self.decimals)
        self.cutout_tooldia_entry.setSingleStep(0.1)

        grid0.addWidget(tdclabel, 0, 0)
        grid0.addWidget(self.cutout_tooldia_entry, 0, 1)

        # Cut Z
        cutzlabel = QtWidgets.QLabel('%s:' % _('Cut Z'))
        cutzlabel.setToolTip(
            _(
                "Cutting depth (negative)\n"
                "below the copper surface."
            )
        )
        self.cutz_entry = FCDoubleSpinner()
        self.cutz_entry.set_precision(self.decimals)

        if machinist_setting == 0:
            self.cutz_entry.setRange(-9999.9999, 0.0000)
        else:
            self.cutz_entry.setRange(-9999.9999, 9999.9999)

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
        self.maxdepth_entry.setRange(0, 9999.9999)
        self.maxdepth_entry.setSingleStep(0.1)

        self.maxdepth_entry.setToolTip(_("Depth of each pass (positive)."))

        grid0.addWidget(self.mpass_cb, 2, 0)
        grid0.addWidget(self.maxdepth_entry, 2, 1)

        # Object kind
        kindlabel = QtWidgets.QLabel('%s:' % _('Object kind'))
        kindlabel.setToolTip(
            _("Choice of what kind the object we want to cutout is.<BR>"
              "- <B>Single</B>: contain a single PCB Gerber outline object.<BR>"
              "- <B>Panel</B>: a panel PCB Gerber object, which is made\n"
              "out of many individual PCB outlines.")
        )

        self.obj_kind_combo = RadioSet([
            {"label": _("Single"), "value": "single"},
            {"label": _("Panel"), "value": "panel"},
        ])
        grid0.addWidget(kindlabel, 3, 0)
        grid0.addWidget(self.obj_kind_combo, 3, 1)

        marginlabel = QtWidgets.QLabel('%s:' % _('Margin'))
        marginlabel.setToolTip(
            _("Margin over bounds. A positive value here\n"
              "will make the cutout of the PCB further from\n"
              "the actual PCB border")
        )

        self.cutout_margin_entry = FCDoubleSpinner()
        self.cutout_margin_entry.set_range(-9999.9999, 9999.9999)
        self.cutout_margin_entry.set_precision(self.decimals)
        self.cutout_margin_entry.setSingleStep(0.1)

        grid0.addWidget(marginlabel, 4, 0)
        grid0.addWidget(self.cutout_margin_entry, 4, 1)

        gaplabel = QtWidgets.QLabel('%s:' % _('Gap size'))
        gaplabel.setToolTip(
            _("The size of the bridge gaps in the cutout\n"
              "used to keep the board connected to\n"
              "the surrounding material (the one \n"
              "from which the PCB is cutout).")
        )

        self.cutout_gap_entry = FCDoubleSpinner()
        self.cutout_gap_entry.set_range(0.000001, 9999.9999)
        self.cutout_gap_entry.set_precision(self.decimals)
        self.cutout_gap_entry.setSingleStep(0.1)

        grid0.addWidget(gaplabel, 5, 0)
        grid0.addWidget(self.cutout_gap_entry, 5, 1)

        gaps_label = QtWidgets.QLabel('%s:' % _('Gaps'))
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
        grid0.addWidget(gaps_label, 6, 0)
        grid0.addWidget(self.gaps_combo, 6, 1)

        gaps_items = ['None', 'LR', 'TB', '4', '2LR', '2TB', '8']
        for it in gaps_items:
            self.gaps_combo.addItem(it)
            self.gaps_combo.setStyleSheet('background-color: rgb(255,255,255)')

        # Surrounding convex box shape
        self.convex_box = FCCheckBox('%s' % _("Convex Shape"))
        self.convex_box.setToolTip(
            _("Create a convex shape surrounding the entire PCB.\n"
              "Used only if the source object type is Gerber.")
        )
        grid0.addWidget(self.convex_box, 7, 0, 1, 2)

        self.layout.addStretch()
