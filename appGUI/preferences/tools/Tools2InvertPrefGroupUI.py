from PyQt6 import QtWidgets

from appGUI.GUIElements import FCDoubleSpinner, RadioSet, FCLabel, FCGridLayout, FCFrame
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class Tools2InvertPrefGroupUI(OptionsGroupUI):
    def __init__(self, defaults, decimals=4, parent=None):

        super(Tools2InvertPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Invert Gerber Plugin")))
        self.decimals = decimals
        self.defaults = defaults

        # #############################################################################################################
        # PARAMETERS Frame
        # #############################################################################################################
        self.sublabel = FCLabel('<span style="color:blue;"><b>%s</b></span>' % _("Parameters"))
        self.sublabel.setToolTip(
            _("A tool to invert Gerber geometry from positive to negative\n"
              "and in revers.")
        )
        self.layout.addWidget(self.sublabel)

        param_frame = FCFrame()
        self.layout.addWidget(param_frame)

        param_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        param_frame.setLayout(param_grid)

        # Margin
        self.margin_label = FCLabel('%s:' % _('Margin'))
        self.margin_label.setToolTip(
            _("Distance by which to avoid\n"
              "the edges of the Gerber object.")
        )
        self.margin_entry = FCDoubleSpinner()
        self.margin_entry.set_precision(self.decimals)
        self.margin_entry.set_range(0.0000, 10000.0000)
        self.margin_entry.setObjectName(_("Margin"))

        param_grid.addWidget(self.margin_label, 0, 0)
        param_grid.addWidget(self.margin_entry, 0, 1)

        # #############################################################################################################
        # Line Join Frame
        # #############################################################################################################
        self.join_label = FCLabel('<span style="color:tomato;"><b>%s</b></span>' % _("Lines Join Style"))
        self.join_label.setToolTip(
            _("The way that the lines in the object outline will be joined.\n"
              "Can be:\n"
              "- rounded -> an arc is added between two joining lines\n"
              "- square -> the lines meet in 90 degrees angle\n"
              "- bevel -> the lines are joined by a third line")
        )
        self.layout.addWidget(self.join_label)

        join_frame = FCFrame()
        self.layout.addWidget(join_frame)

        join_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        join_frame.setLayout(join_grid)

        line_join_lbl = FCLabel('%s:' % _("Value"))

        self.join_radio = RadioSet([
            {'label': _('Rounded'), 'value': 'r'},
            {'label': _('Square'), 'value': 's'},
            {'label': _('Bevel'), 'value': 'b'}
        ], orientation='vertical')

        join_grid.addWidget(line_join_lbl, 0, 0)
        join_grid.addWidget(self.join_radio, 0, 1)

        FCGridLayout.set_common_column_size([param_grid, join_grid], 0)

        self.layout.addStretch()
