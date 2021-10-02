from PyQt6 import QtWidgets

from appGUI.GUIElements import FCDoubleSpinner, RadioSet, FCLabel, FCGridLayout, FCComboBox2, FCFrame
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class Tools2FiducialsPrefGroupUI(OptionsGroupUI):
    def __init__(self, defaults, decimals=4, parent=None):

        super(Tools2FiducialsPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Fiducials Plugin")))
        self.decimals = decimals
        self.defaults = defaults

        # #############################################################################################################
        # Parameters Frame
        # #############################################################################################################
        self.param_label = FCLabel('<span style="color:blue;"><b>%s</b></span>' % _('Parameters'))
        self.param_label.setToolTip(
            _("Parameters used for this tool.")
        )
        self.layout.addWidget(self.param_label)

        par_frame = FCFrame()
        self.layout.addWidget(par_frame)

        param_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        par_frame.setLayout(param_grid)

        # DIAMETER #
        self.dia_label = FCLabel('%s:' % _("Size"))
        self.dia_label.setToolTip(
            _("This set the fiducial diameter if fiducial type is circular,\n"
              "otherwise is the size of the fiducial.\n"
              "The soldermask opening is double than that.")
        )
        self.dia_entry = FCDoubleSpinner()
        self.dia_entry.set_range(1.0000, 3.0000)
        self.dia_entry.set_precision(self.decimals)
        self.dia_entry.setWrapping(True)
        self.dia_entry.setSingleStep(0.1)

        param_grid.addWidget(self.dia_label, 2, 0)
        param_grid.addWidget(self.dia_entry, 2, 1)

        # MARGIN #
        self.margin_label = FCLabel('%s:' % _("Margin"))
        self.margin_label.setToolTip(
            _("Bounding box margin.")
        )
        self.margin_entry = FCDoubleSpinner()
        self.margin_entry.set_range(-10000.0000, 10000.0000)
        self.margin_entry.set_precision(self.decimals)
        self.margin_entry.setSingleStep(0.1)

        param_grid.addWidget(self.margin_label, 4, 0)
        param_grid.addWidget(self.margin_entry, 4, 1)

        # Position for second fiducial #
        self.pos_radio = RadioSet([
            {'label': _('Up'), 'value': 'up'},
            {"label": _("Down"), "value": "down"},
            {"label": _("None"), "value": "no"}
        ], compact=True)
        self.pos_label = FCLabel('%s:' % _("Second fiducial"))
        self.pos_label.setToolTip(
            _("The position for the second fiducial.\n"
              "- 'Up' - the order is: bottom-left, top-left, top-right.\n"
              "- 'Down' - the order is: bottom-left, bottom-right, top-right.\n"
              "- 'None' - there is no second fiducial. The order is: bottom-left, top-right.")
        )
        param_grid.addWidget(self.pos_label, 6, 0)
        param_grid.addWidget(self.pos_radio, 6, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        param_grid.addWidget(separator_line, 8, 0, 1, 2)

        # Fiducial type #
        self.fid_type_label = FCLabel('%s:' % _("Fiducial Type"))
        self.fid_type_label.setToolTip(
            _("The type of fiducial.\n"
              "- 'Circular' - this is the regular fiducial.\n"
              "- 'Cross' - cross lines fiducial.\n"
              "- 'Chess' - chess pattern fiducial.")
        )

        self.fid_type_combo = FCComboBox2()
        self.fid_type_combo.addItems([_('Circular'), _("Cross"), _("Chess")])

        param_grid.addWidget(self.fid_type_label, 10, 0)
        param_grid.addWidget(self.fid_type_combo, 10, 1)

        # Line Thickness #
        self.line_thickness_label = FCLabel('%s:' % _("Line thickness"))
        self.line_thickness_label.setToolTip(
            _("Bounding box margin.")
        )
        self.line_thickness_entry = FCDoubleSpinner()
        self.line_thickness_entry.set_range(0.00001, 10000.0000)
        self.line_thickness_entry.set_precision(self.decimals)
        self.line_thickness_entry.setSingleStep(0.1)

        param_grid.addWidget(self.line_thickness_label, 12, 0)
        param_grid.addWidget(self.line_thickness_entry, 12, 1)

        # #############################################################################################################
        # Selection Frame
        # #############################################################################################################
        self.sel_label = FCLabel('<span style="color:brown;"><b>%s</b></span>' % _("Selection"))
        self.layout.addWidget(self.sel_label)

        s_frame = FCFrame()
        self.layout.addWidget(s_frame)

        # Grid Layout
        grid_sel = FCGridLayout(v_spacing=5, h_spacing=3)
        s_frame.setLayout(grid_sel)

        # Mode #
        self.mode_radio = RadioSet([
            {'label': _('Auto'), 'value': 'auto'},
            {"label": _("Manual"), "value": "manual"}
        ], compact=True)
        self.mode_label = FCLabel('%s:' % _("Mode"))
        self.mode_label.setToolTip(
            _("- 'Auto' - automatic placement of fiducials in the corners of the bounding box.\n"
              "- 'Manual' - manual placement of fiducials.")
        )
        grid_sel.addWidget(self.mode_label, 0, 0)
        grid_sel.addWidget(self.mode_radio, 0, 1)

        FCGridLayout.set_common_column_size([param_grid, grid_sel], 0)

        self.layout.addStretch(1)
