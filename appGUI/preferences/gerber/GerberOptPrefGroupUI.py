from PyQt6 import QtWidgets

from appGUI.GUIElements import FCDoubleSpinner, FCCheckBox, FCLabel, FCGridLayout, FCFrame
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GerberOptPrefGroupUI(OptionsGroupUI):
    def __init__(self, app, parent=None):
        # OptionsGroupUI.__init__(self, "Gerber Options Preferences", parent=parent)
        super(GerberOptPrefGroupUI, self).__init__(self, parent=parent)

        self.decimals = app.decimals
        self.options = app.options

        self.setTitle(str(_("Options")))

        # #############################################################################################################
        # Non-copper Regions Frame
        # #############################################################################################################
        self.clearcopper_label = FCLabel('<span style="color:blue;"><b>%s</b></span>' % _("Non-copper regions"))
        self.clearcopper_label.setToolTip(
            _("Create polygons covering the\n"
              "areas without copper on the PCB.\n"
              "Equivalent to the inverse of this\n"
              "object. Can be used to remove all\n"
              "copper from a specified region.")
        )
        self.layout.addWidget(self.clearcopper_label)

        ncc_frame = FCFrame()
        self.layout.addWidget(ncc_frame)

        # ## Grid Layout
        ncc_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        ncc_frame.setLayout(ncc_grid)

        # Margin
        bmlabel = FCLabel('%s:' % _('Boundary Margin'))
        bmlabel.setToolTip(
            _("Specify the edge of the PCB\n"
              "by drawing a box around all\n"
              "objects with this minimum\n"
              "distance.")
        )
        self.noncopper_margin_entry = FCDoubleSpinner()
        self.noncopper_margin_entry.set_precision(self.decimals)
        self.noncopper_margin_entry.setSingleStep(0.1)
        self.noncopper_margin_entry.set_range(-9999, 9999)

        ncc_grid.addWidget(bmlabel, 0, 0)
        ncc_grid.addWidget(self.noncopper_margin_entry, 0, 1)

        # Rounded corners
        self.noncopper_rounded_cb = FCCheckBox(label=_("Rounded Geo"))
        self.noncopper_rounded_cb.setToolTip(
            _("Resulting geometry will have rounded corners.")
        )
        ncc_grid.addWidget(self.noncopper_rounded_cb, 2, 0, 1, 2)

        # #############################################################################################################
        # Bounding Box Frame
        # #############################################################################################################
        self.boundingbox_label = FCLabel('<span style="color:brown;"><b>%s</b></span>' % _('Bounding Box'))
        self.layout.addWidget(self.boundingbox_label)

        bb_frame = FCFrame()
        self.layout.addWidget(bb_frame)

        bb_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        bb_frame.setLayout(bb_grid)

        bbmargin = FCLabel('%s:' % _('Boundary Margin'))
        bbmargin.setToolTip(
            _("Distance of the edges of the box\n"
              "to the nearest polygon.")
        )
        self.bbmargin_entry = FCDoubleSpinner()
        self.bbmargin_entry.set_precision(self.decimals)
        self.bbmargin_entry.setSingleStep(0.1)
        self.bbmargin_entry.set_range(-9999, 9999)

        bb_grid.addWidget(bbmargin, 0, 0)
        bb_grid.addWidget(self.bbmargin_entry, 0, 1)

        self.bbrounded_cb = FCCheckBox(label='%s' % _("Rounded Geo"))
        self.bbrounded_cb.setToolTip(
            _("If the bounding box is \n"
              "to have rounded corners\n"
              "their radius is equal to\n"
              "the margin.")
        )
        bb_grid.addWidget(self.bbrounded_cb, 2, 0, 1, 2)

        FCGridLayout.set_common_column_size([ncc_grid, bb_grid], 0)

        self.layout.addStretch()
