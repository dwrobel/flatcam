
from PyQt6 import QtWidgets, QtGui
from PyQt6.QtCore import QSettings

from appGUI.GUIElements import FCButton, FCTextArea, FCEntry, FCLabel
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class AutoCompletePrefGroupUI(OptionsGroupUI):
    def __init__(self, app, parent=None):
        # OptionsGroupUI.__init__(self, "Gerber File associations Preferences", parent=None)
        super().__init__(self, parent=parent)

        self.setTitle(str(_("Autocompleter Keywords")))
        self.decimals = app.decimals
        self.options = app.options

        self.restore_btn = FCButton(_("Restore"))
        self.restore_btn.setToolTip(_("Restore the autocompleter keywords list to the default state."))
        self.del_all_btn = FCButton(_("Delete All"))
        self.del_all_btn.setToolTip(_("Delete all autocompleter keywords from the list."))

        hlay0 = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay0)
        hlay0.addWidget(self.restore_btn)
        hlay0.addWidget(self.del_all_btn)

        # ## Gerber associations
        self.grb_list_label = FCLabel('%s:' % _("Keywords list"), bold=True)
        self.grb_list_label.setToolTip(
            _("List of keywords used by\n"
              "the autocompleter in FlatCAM.\n"
              "The autocompleter is installed\n"
              "in the Code Editor and for the Tcl Shell.")
        )
        self.layout.addWidget(self.grb_list_label)

        qsettings = QSettings("Open Source", "FlatCAM")
        if qsettings.contains("textbox_font_size"):
            tb_fsize = qsettings.value('textbox_font_size', type=int)
        else:
            tb_fsize = 10

        self.kw_list_text = FCTextArea()
        self.kw_list_text.setReadOnly(True)
        # self.grb_list_text.sizeHint(custom_sizehint=150)
        self.layout.addWidget(self.kw_list_text)
        font = QtGui.QFont()
        font.setPointSize(tb_fsize)
        self.kw_list_text.setFont(font)

        self.kw_label = FCLabel('%s:' % _("Extension"))
        self.kw_label.setToolTip(_("A keyword to be added or deleted to the list."))
        self.kw_entry = FCEntry()

        hlay1 = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay1)
        hlay1.addWidget(self.kw_label)
        hlay1.addWidget(self.kw_entry)

        self.add_btn = FCButton(_("Add keyword"))
        self.add_btn.setToolTip(_("Add a keyword to the list"))
        self.del_btn = FCButton(_("Delete keyword"))
        self.del_btn.setToolTip(_("Delete a keyword from the list"))

        hlay2 = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay2)
        hlay2.addWidget(self.add_btn)
        hlay2.addWidget(self.del_btn)

        # self.layout.addStretch()
