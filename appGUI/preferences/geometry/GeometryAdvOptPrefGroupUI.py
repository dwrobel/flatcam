
from PyQt6 import QtWidgets

from appGUI.GUIElements import FCDoubleSpinner, FCLabel, GLay, FCFrame
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GeometryAdvOptPrefGroupUI(OptionsGroupUI):
    def __init__(self, app, parent=None):
        # OptionsGroupUI.__init__(self, "Geometry Advanced Options Preferences", parent=parent)
        super(GeometryAdvOptPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Adv. Options")))
        self.decimals = app.decimals
        self.options = app.options

        # #############################################################################################################
        # Advanced Options Frame
        # #############################################################################################################
        self.geo_label = FCLabel('%s' % _("Advanced Options"), color='indigo', bold=True)
        self.geo_label.setToolTip(
            _("A list of advanced parameters.\n"
              "Those parameters are available only for\n"
              "Advanced App. Level.")
        )
        self.layout.addWidget(self.geo_label)

        adv_frame = FCFrame()
        self.layout.addWidget(adv_frame)

        adv_grid = GLay(v_spacing=5, h_spacing=3)
        adv_frame.setLayout(adv_grid)

        # Size of trace segment on X axis
        seg_x_label = FCLabel('%s:' % _("Segment X size"))
        seg_x_label.setToolTip(
            _("The size of the trace segment on the X axis.\n"
              "Useful for auto-leveling.\n"
              "A value of 0 means no segmentation on the X axis.")
        )
        self.seg_x_entry = FCDoubleSpinner()
        self.seg_x_entry.set_range(0, 99999)
        self.seg_x_entry.set_precision(self.decimals)
        self.seg_x_entry.setSingleStep(0.1)
        self.seg_x_entry.setWrapping(True)

        adv_grid.addWidget(seg_x_label, 0, 0)
        adv_grid.addWidget(self.seg_x_entry, 0, 1)

        # Size of trace segment on Y axis
        seg_y_label = FCLabel('%s:' % _("Segment Y size"))
        seg_y_label.setToolTip(
            _("The size of the trace segment on the Y axis.\n"
              "Useful for auto-leveling.\n"
              "A value of 0 means no segmentation on the Y axis.")
        )
        self.seg_y_entry = FCDoubleSpinner()
        self.seg_y_entry.set_range(0, 99999)
        self.seg_y_entry.set_precision(self.decimals)
        self.seg_y_entry.setSingleStep(0.1)
        self.seg_y_entry.setWrapping(True)

        adv_grid.addWidget(seg_y_label, 2, 0)
        adv_grid.addWidget(self.seg_y_entry, 2, 1)

        # self.layout.addStretch()
