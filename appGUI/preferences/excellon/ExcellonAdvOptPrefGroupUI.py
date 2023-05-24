
from PyQt6 import QtWidgets

from appGUI.GUIElements import FCCheckBox, FCLabel, GLay, FCFrame
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ExcellonAdvOptPrefGroupUI(OptionsGroupUI):

    def __init__(self, app, parent=None):
        # OptionsGroupUI.__init__(self, "Excellon Advanced Options", parent=parent)
        super(ExcellonAdvOptPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Adv. Options")))
        self.decimals = app.decimals
        self.options = app.options

        # #############################################################################################################
        # PARAMETERS Frame
        # #############################################################################################################
        self.exc_label = FCLabel('%s' % _("Advanced Options"), color='indigo', bold=True)
        self.exc_label.setToolTip(
            _("A list of advanced parameters.\n"
              "Those parameters are available only for\n"
              "Advanced App. Level.")
        )
        self.layout.addWidget(self.exc_label)

        param_frame = FCFrame()
        self.layout.addWidget(param_frame)

        param_grid = GLay(v_spacing=5, h_spacing=3)
        param_frame.setLayout(param_grid)

        # Table Visibility CB
        self.table_visibility_cb = FCCheckBox(label=_('Table Show/Hide'))
        self.table_visibility_cb.setToolTip(
            _("Toggle the display of the Tools Table.")
        )
        param_grid.addWidget(self.table_visibility_cb, 0, 0, 1, 2)

        # Auto Load Tools from DB
        self.autoload_db_cb = FCCheckBox('%s' % _("Auto load from DB"))
        self.autoload_db_cb.setToolTip(
            _("Automatic replacement of the tools from related application tools\n"
              "with tools from DB that have a close diameter value.")
        )
        param_grid.addWidget(self.autoload_db_cb, 2, 0, 1, 2)

        # self.layout.addStretch()
