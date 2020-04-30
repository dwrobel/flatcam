from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QSettings

from flatcamGUI.GUIElements import FCTextArea
from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI


class CNCJobOptPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "CNC Job Options Preferences", parent=None)
        super(CNCJobOptPrefGroupUI, self).__init__(self)

        self.setTitle(str(_("CNC Job Options")))
        self.decimals = decimals

        # ## Export G-Code
        self.export_gcode_label = QtWidgets.QLabel("<b>%s:</b>" % _("Export G-Code"))
        self.export_gcode_label.setToolTip(
            _("Export and save G-Code to\n"
              "make this object to a file.")
        )
        self.layout.addWidget(self.export_gcode_label)

        qsettings = QSettings("Open Source", "FlatCAM")
        if qsettings.contains("textbox_font_size"):
            tb_fsize = qsettings.value('textbox_font_size', type=int)
        else:
            tb_fsize = 10
        font = QtGui.QFont()
        font.setPointSize(tb_fsize)

        # Prepend to G-Code
        prependlabel = QtWidgets.QLabel('%s:' % _('Prepend to G-Code'))
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
        appendlabel = QtWidgets.QLabel('%s:' % _('Append to G-Code'))
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