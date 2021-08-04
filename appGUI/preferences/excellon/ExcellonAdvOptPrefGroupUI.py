from PyQt6 import QtWidgets

from appGUI.GUIElements import FCCheckBox, FCLabel
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI
import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ExcellonAdvOptPrefGroupUI(OptionsGroupUI):

    def __init__(self, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "Excellon Advanced Options", parent=parent)
        super(ExcellonAdvOptPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Excellon Adv. Options")))
        self.decimals = decimals

        # #######################
        # ## ADVANCED OPTIONS ###
        # #######################

        self.exc_label = FCLabel('<b>%s:</b>' % _('Advanced Options'))
        self.exc_label.setToolTip(
            _("A list of advanced parameters.\n"
              "Those parameters are available only for\n"
              "Advanced App. Level.")
        )
        self.layout.addWidget(self.exc_label)

        grid0 = QtWidgets.QGridLayout()
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        self.layout.addLayout(grid0)

        # Table Visibility CB
        self.table_visibility_cb = FCCheckBox(label=_('Table Show/Hide'))
        self.table_visibility_cb.setToolTip(
            _("Toggle the display of the Tools Table.")
        )
        grid0.addWidget(self.table_visibility_cb, 0, 0, 1, 2)

        # Auto Load Tools from DB
        self.autoload_db_cb = FCCheckBox('%s' % _("Auto load from DB"))
        self.autoload_db_cb.setToolTip(
            _("Automatic replacement of the tools from related application tools\n"
              "with tools from DB that have a close diameter value.")
        )
        grid0.addWidget(self.autoload_db_cb, 1, 0, 1, 2)

        self.layout.addStretch()
