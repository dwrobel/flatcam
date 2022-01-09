from PyQt6 import QtGui
from PyQt6.QtCore import QSettings

from appGUI.GUIElements import FCTextArea, FCLabel, FCFrame
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class CNCJobEditorPrefGroupUI(OptionsGroupUI):
    def __init__(self, defaults, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "CNC Job Options Preferences", parent=None)
        super(CNCJobEditorPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Editor")))
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

        qsettings = QSettings("Open Source", "FlatCAM")
        if qsettings.contains("textbox_font_size"):
            tb_fsize = qsettings.value('textbox_font_size', type=int)
        else:
            tb_fsize = 10
        font = QtGui.QFont()
        font.setPointSize(tb_fsize)

        # Prepend to G-Code
        prependlabel = FCLabel('%s:' % _('Prepend to G-Code'))
        prependlabel.setToolTip(
            _("Type here any G-Code commands you would\n"
              "like to add at the beginning of the G-Code file.")
        )
        self.layout.addWidget(prependlabel)

        self.prepend_text = FCTextArea()
        self.prepend_text.setPlaceholderText(
            _("Type here any G-Code commands you would "
              "like to add at the beginning of the G-Code file.")
        )
        self.layout.addWidget(self.prepend_text)
        self.prepend_text.setFont(font)

        # Append text to G-Code
        appendlabel = FCLabel('%s:' % _('Append to G-Code'))
        appendlabel.setToolTip(
            _("Type here any G-Code commands you would\n"
              "like to append to the generated file.\n"
              "I.e.: M2 (End of program)")
        )
        self.layout.addWidget(appendlabel)

        self.append_text = FCTextArea()
        self.append_text.setPlaceholderText(
            _("Type here any G-Code commands you would "
              "like to append to the generated file.\n"
              "I.e.: M2 (End of program)")
        )
        self.layout.addWidget(self.append_text)
        self.append_text.setFont(font)

        self.layout.addStretch()
