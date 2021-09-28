from PyQt6 import QtWidgets

from appGUI.GUIElements import FCCheckBox, RadioSet, FCDoubleSpinner, FCLabel, OptionalInputSection, FCGridLayout, \
    FCFrame
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GerberAdvOptPrefGroupUI(OptionsGroupUI):
    def __init__(self, defaults, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "Gerber Adv. Options Preferences", parent=parent)
        super(GerberAdvOptPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Gerber Adv. Options")))
        self.decimals = decimals
        self.defaults = defaults

        # #############################################################################################################
        # Advanced Gerber Frame
        # #############################################################################################################
        adv_frame = FCFrame()
        self.layout.addWidget(adv_frame)

        adv_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        adv_frame.setLayout(adv_grid)

        # Follow Attribute
        self.follow_cb = FCCheckBox(label=_('"Follow"'))
        self.follow_cb.setToolTip(
            _("Generate a 'Follow' geometry.\n"
              "This means that it will cut through\n"
              "the middle of the trace.")
        )
        adv_grid.addWidget(self.follow_cb, 0, 0, 1, 2)

        # Aperture Table Visibility CB
        self.aperture_table_visibility_cb = FCCheckBox(label=_('Table Show/Hide'))
        self.aperture_table_visibility_cb.setToolTip(
            _("Toggle the display of the Tools Table.")
        )
        adv_grid.addWidget(self.aperture_table_visibility_cb, 2, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        adv_grid.addWidget(separator_line, 4, 0, 1, 2)

        # Buffering Type
        buffering_label = FCLabel('%s:' % _('Buffering'))
        buffering_label.setToolTip(
            _("Buffering type:\n"
              "- None --> best performance, fast file loading but no so good display\n"
              "- Full --> slow file loading but good visuals. This is the default.\n"
              "<<WARNING>>: Don't change this unless you know what you are doing !!!")
        )
        self.buffering_radio = RadioSet([{'label': _('None'), 'value': 'no'},
                                         {'label': _('Full'), 'value': 'full'}])
        adv_grid.addWidget(buffering_label, 6, 0)
        adv_grid.addWidget(self.buffering_radio, 6, 1)

        # Delayed Buffering
        self.delayed_buffer_cb = FCCheckBox(label=_('Delayed Buffering'))
        self.delayed_buffer_cb.setToolTip(
            _("When checked it will do the buffering in background.")
        )
        adv_grid.addWidget(self.delayed_buffer_cb, 8, 0, 1, 2)

        # Simplification
        self.simplify_cb = FCCheckBox(label=_('Simplify'))
        self.simplify_cb.setToolTip(
            _("When checked all the Gerber polygons will be\n"
              "loaded with simplification having a set tolerance.\n"
              "<<WARNING>>: Don't change this unless you know what you are doing !!!")
                                    )
        adv_grid.addWidget(self.simplify_cb, 10, 0, 1, 2)

        # Simplification tolerance
        self.simplification_tol_label = FCLabel(_('Tolerance'))
        self.simplification_tol_label.setToolTip(_("Tolerance for polygon simplification."))

        self.simplification_tol_spinner = FCDoubleSpinner()
        self.simplification_tol_spinner.set_precision(self.decimals + 1)
        self.simplification_tol_spinner.setWrapping(True)
        self.simplification_tol_spinner.setRange(0.00000, 0.01000)
        self.simplification_tol_spinner.setSingleStep(0.0001)

        adv_grid.addWidget(self.simplification_tol_label, 12, 0)
        adv_grid.addWidget(self.simplification_tol_spinner, 12, 1)
        self.ois_simplif = OptionalInputSection(
            self.simplify_cb,
            [
                self.simplification_tol_label, self.simplification_tol_spinner
            ],
            logic=True)

        # self.layout.addStretch()

        # signals
        self.buffering_radio.activated_custom.connect(self.on_buffering_change)

    def on_buffering_change(self, val):
        if val == 'no':
            self.delayed_buffer_cb.setDisabled(False)
        else:
            self.delayed_buffer_cb.setDisabled(True)
