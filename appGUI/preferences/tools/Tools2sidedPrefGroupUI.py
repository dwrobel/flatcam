from PyQt6 import QtWidgets

from appGUI.GUIElements import FCDoubleSpinner, RadioSet, FCLabel, FCGridLayout, FCFrame
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class Tools2sidedPrefGroupUI(OptionsGroupUI):
    def __init__(self, defaults, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "2sided Plugin", parent=parent)
        super(Tools2sidedPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("2-Sided Plugin")))
        self.decimals = decimals
        self.defaults = defaults

        # ## Board cuttout
        self.dblsided_label = FCLabel('<span style="color:indigo;"><b>%s</b></span>' % _("PCB Alignment"))
        self.dblsided_label.setToolTip(
            _("A tool to help in creating a double sided\n"
              "PCB using alignment holes.")
        )
        self.layout.addWidget(self.dblsided_label)

        # #############################################################################################################
        # Parameters Frame
        # #############################################################################################################
        par_frame = FCFrame()
        self.layout.addWidget(par_frame)

        param_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        par_frame.setLayout(param_grid)

        # ## Drill diameter for alignment holes
        self.drill_dia_entry = FCDoubleSpinner()
        self.drill_dia_entry.set_range(0.000001, 10000.0000)
        self.drill_dia_entry.set_precision(self.decimals)
        self.drill_dia_entry.setSingleStep(0.1)

        self.dd_label = FCLabel('%s:' % _("Drill Dia"))
        self.dd_label.setToolTip(
            _("Diameter of the drill for the "
              "alignment holes.")
        )
        param_grid.addWidget(self.dd_label, 0, 0)
        param_grid.addWidget(self.drill_dia_entry, 0, 1)

        # ## Alignment Axis
        self.align_ax_label = FCLabel('%s:' % _("Align Axis"))
        self.align_ax_label.setToolTip(
            _("Mirror vertically (X) or horizontally (Y).")
        )
        self.align_axis_radio = RadioSet([{'label': 'X', 'value': 'X'},
                                          {'label': 'Y', 'value': 'Y'}], compact=True)

        param_grid.addWidget(self.align_ax_label, 1, 0)
        param_grid.addWidget(self.align_axis_radio, 1, 1)

        # ## Axis
        self.mirror_axis_radio = RadioSet([{'label': 'X', 'value': 'X'},
                                           {'label': 'Y', 'value': 'Y'}], compact=True)
        self.mirax_label = FCLabel('%s:' % _("Mirror Axis"))
        self.mirax_label.setToolTip(
            _("Mirror vertically (X) or horizontally (Y).")
        )

        # separator_line = QtWidgets.QFrame()
        # separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        # separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        # param_grid.addWidget(separator_line, 2, 0, 1, 2)

        # #############################################################################################################
        # Mirror Frame
        # #############################################################################################################
        # ### Tools ## ##
        self.mirror_label = FCLabel('<span style="color:red;"><b>%s</b></span>' % _("Mirror Operation"))
        self.layout.addWidget(self.mirror_label)

        mirror_frame = FCFrame()
        self.layout.addWidget(mirror_frame)

        mirror_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        mirror_frame.setLayout(mirror_grid)

        mirror_grid.addWidget(self.mirax_label, 0, 0)
        mirror_grid.addWidget(self.mirror_axis_radio, 0, 1)

        # ## Axis Location
        self.axis_location_radio = RadioSet(
            [
                {'label': _('Point'), 'value': 'point'},
                {'label': _('Box'), 'value': 'box'},
                {'label': _('Snap'), 'value': 'hole'},
            ], compact=True
        )
        self.axloc_label = FCLabel('%s:' % _("Axis Ref"))
        self.axloc_label.setToolTip(
            _("The coordinates used as reference for the mirror operation.\n"
              "Can be:\n"
              "- Point -> a set of coordinates (x,y) around which the object is mirrored\n"
              "- Box -> a set of coordinates (x, y) obtained from the center of the\n"
              "bounding box of another object selected below\n"
              "- Snap -> a point defined by the center of a drill hole in a Excellon object")
        )

        mirror_grid.addWidget(self.axloc_label, 2, 0)
        mirror_grid.addWidget(self.axis_location_radio, 2, 1)

        FCGridLayout.set_common_column_size([param_grid, mirror_grid], 0)

        # self.layout.addStretch(1)
