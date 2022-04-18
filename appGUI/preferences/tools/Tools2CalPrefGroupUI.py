from PyQt6 import QtWidgets

from appGUI.GUIElements import RadioSet, FCDoubleSpinner, FCCheckBox, NumericalEvalTupleEntry, FCLabel, \
    GLay, FCFrame
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class Tools2CalPrefGroupUI(OptionsGroupUI):
    def __init__(self, app, parent=None):

        super(Tools2CalPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Calibration Plugin")))
        self.decimals = app.decimals
        self.options = app.options

        # #############################################################################################################
        # Parameters Frame
        # #############################################################################################################
        self.param_label = FCLabel('%s' % _("Parameters"), color='blue', bold=True)
        self.param_label.setToolTip(
            _("Parameters used for this tool.")
        )

        par_frame = FCFrame()
        self.layout.addWidget(par_frame)

        param_grid = GLay(v_spacing=5, h_spacing=3)
        par_frame.setLayout(param_grid)
        
        param_grid.addWidget(self.param_label, 0, 0, 1, 2)

        # Calibration source
        self.cal_source_lbl = FCLabel("%s:" % _("Source Type"))
        self.cal_source_lbl.setToolTip(_("The source of calibration points.\n"
                                         "It can be:\n"
                                         "- Object -> click a hole geo for Excellon or a pad for Gerber\n"
                                         "- Free -> click freely on canvas to acquire the calibration points"))
        self.cal_source_radio = RadioSet([{'label': _('Object'), 'value': 'object'},
                                          {'label': _('Free'), 'value': 'free'}],
                                         compact=True)

        param_grid.addWidget(self.cal_source_lbl, 2, 0)
        param_grid.addWidget(self.cal_source_radio, 2, 1, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        param_grid.addWidget(separator_line, 4, 0, 1, 2)

        # Travel Z entry
        travelz_lbl = FCLabel('%s:' % _("Travel Z"))
        travelz_lbl.setToolTip(
            _("Height (Z) for travelling between the points.")
        )

        self.travelz_entry = FCDoubleSpinner()
        self.travelz_entry.set_range(-10000.0000, 10000.0000)
        self.travelz_entry.set_precision(self.decimals)
        self.travelz_entry.setSingleStep(0.1)

        param_grid.addWidget(travelz_lbl, 6, 0)
        param_grid.addWidget(self.travelz_entry, 6, 1, 1, 2)

        # Verification Z entry
        verz_lbl = FCLabel('%s:' % _("Verification Z"))
        verz_lbl.setToolTip(
            _("Height (Z) for checking the point.")
        )

        self.verz_entry = FCDoubleSpinner()
        self.verz_entry.set_range(-10000.0000, 10000.0000)
        self.verz_entry.set_precision(self.decimals)
        self.verz_entry.setSingleStep(0.1)

        param_grid.addWidget(verz_lbl, 8, 0)
        param_grid.addWidget(self.verz_entry, 8, 1, 1, 2)

        # Zero the Z of the verification tool
        self.zeroz_cb = FCCheckBox('%s' % _("Zero Z tool"))
        self.zeroz_cb.setToolTip(
            _("Include a sequence to zero the height (Z)\n"
              "of the verification tool.")
        )

        param_grid.addWidget(self.zeroz_cb, 10, 0, 1, 3)

        # Second point choice
        second_point_lbl = FCLabel('%s:' % _("Second point"))
        second_point_lbl.setToolTip(
            _("Second point in the Gcode verification can be:\n"
              "- top-left -> the user will align the PCB vertically\n"
              "- bottom-right -> the user will align the PCB horizontally")
        )
        self.second_point_radio = RadioSet([{'label': _('Top Left'), 'value': 'tl'},
                                            {'label': _('Bottom Right'), 'value': 'br'}],
                                           orientation='vertical')

        param_grid.addWidget(second_point_lbl, 16, 0)
        param_grid.addWidget(self.second_point_radio, 16, 1, 1, 2)

        # #############################################################################################################
        # Tool change Frame
        # #############################################################################################################
        tc_lbl = FCLabel('%s' % _("Tool change"), color='brown', bold=True)
        self.layout.addWidget(tc_lbl)

        tc_frame = FCFrame()
        self.layout.addWidget(tc_frame)

        tc_grid = GLay(v_spacing=5, h_spacing=3)
        tc_frame.setLayout(tc_grid)

        # Toolchange X-Y entry
        toolchangexy_lbl = FCLabel('%s:' % "X-Y")
        toolchangexy_lbl.setToolTip(
            _("Toolchange X,Y position.\n"
              "If no value is entered then the current\n"
              "(x, y) point will be used,")
        )

        self.toolchange_xy_entry = NumericalEvalTupleEntry(border_color='#0069A9')

        tc_grid.addWidget(toolchangexy_lbl, 0, 0)
        tc_grid.addWidget(self.toolchange_xy_entry, 0, 1)

        # Toochange Z entry
        toolchangez_lbl = FCLabel('%s:' % "Z")
        toolchangez_lbl.setToolTip(
            _("Height (Z) for mounting the verification probe.")
        )

        self.toolchangez_entry = FCDoubleSpinner()
        self.toolchangez_entry.set_range(0.0000, 10000.0000)
        self.toolchangez_entry.set_precision(self.decimals)
        self.toolchangez_entry.setSingleStep(0.1)

        tc_grid.addWidget(toolchangez_lbl, 2, 0)
        tc_grid.addWidget(self.toolchangez_entry, 2, 1)

        GLay.set_common_column_size([param_grid, tc_grid], 0)

        self.layout.addStretch()
