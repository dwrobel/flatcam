from PyQt6 import QtWidgets

from appGUI.GUIElements import FCSpinner, RadioSet, FCLabel, FCGridLayout, FCFrame
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GeometryEditorPrefGroupUI(OptionsGroupUI):
    def __init__(self, defaults, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "Gerber Adv. Options Preferences", parent=parent)
        super(GeometryEditorPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Geometry Editor")))
        self.decimals = decimals
        self.defaults = defaults

        # #############################################################################################################
        # PARAMETERS Frame
        # #############################################################################################################
        self.param_label = FCLabel('<span style="color:blue;"><b>%s</b></span>' % _("Parameters"))
        self.param_label.setToolTip(
            _("A list of Editor parameters.")
        )
        self.layout.addWidget(self.param_label)

        editor_frame = FCFrame()
        self.layout.addWidget(editor_frame)

        editor_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        editor_frame.setLayout(editor_grid)

        # Selection Limit
        self.sel_limit_label = FCLabel('%s:' % _("Selection limit"))
        self.sel_limit_label.setToolTip(
            _("Set the number of selected geometry\n"
              "items above which the utility geometry\n"
              "becomes just a selection rectangle.\n"
              "Increases the performance when moving a\n"
              "large number of geometric elements.")
        )
        self.sel_limit_entry = FCSpinner()
        self.sel_limit_entry.set_range(0, 9999)

        editor_grid.addWidget(self.sel_limit_label, 0, 0)
        editor_grid.addWidget(self.sel_limit_entry, 0, 1)

        # Milling Type
        milling_type_label = FCLabel('%s:' % _('Milling Type'))
        milling_type_label.setToolTip(
            _("Milling type:\n"
              "- climb / best for precision milling and to reduce tool usage\n"
              "- conventional / useful when there is no backlash compensation")
        )
        self.milling_type_radio = RadioSet([{'label': _('Climb'), 'value': 'cl'},
                                            {'label': _('Conventional'), 'value': 'cv'}], compact=True)
        editor_grid.addWidget(milling_type_label, 2, 0)
        editor_grid.addWidget(self.milling_type_radio, 2, 1)

        self.layout.addStretch()
