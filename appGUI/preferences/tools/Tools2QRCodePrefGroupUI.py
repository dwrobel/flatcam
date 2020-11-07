from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt, QSettings

from appGUI.GUIElements import FCSpinner, RadioSet, FCTextArea, FCEntry, FCColorEntry
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

settings = QSettings("Open Source", "FlatCAM")
if settings.contains("machinist"):
    machinist_setting = settings.value('machinist', type=int)
else:
    machinist_setting = 0


class Tools2QRCodePrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):

        super(Tools2QRCodePrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("QRCode Tool Options")))
        self.decimals = decimals

        # ## Parameters
        self.qrlabel = QtWidgets.QLabel("<b>%s:</b>" % _("Parameters"))
        self.qrlabel.setToolTip(
            _("A tool to create a QRCode that can be inserted\n"
              "into a selected Gerber file, or it can be exported as a file.")
        )
        self.layout.addWidget(self.qrlabel)

        # ## Grid Layout
        grid_lay = QtWidgets.QGridLayout()
        self.layout.addLayout(grid_lay)
        grid_lay.setColumnStretch(0, 0)
        grid_lay.setColumnStretch(1, 1)

        # VERSION #
        self.version_label = QtWidgets.QLabel('%s:' % _("Version"))
        self.version_label.setToolTip(
            _("QRCode version can have values from 1 (21x21 boxes)\n"
              "to 40 (177x177 boxes).")
        )
        self.version_entry = FCSpinner()
        self.version_entry.set_range(1, 40)
        self.version_entry.setWrapping(True)

        grid_lay.addWidget(self.version_label, 1, 0)
        grid_lay.addWidget(self.version_entry, 1, 1)

        # ERROR CORRECTION #
        self.error_label = QtWidgets.QLabel('%s:' % _("Error correction"))
        self.error_label.setToolTip(
            _("Parameter that controls the error correction used for the QR Code.\n"
              "L = maximum 7%% errors can be corrected\n"
              "M = maximum 15%% errors can be corrected\n"
              "Q = maximum 25%% errors can be corrected\n"
              "H = maximum 30%% errors can be corrected.")
        )
        self.error_radio = RadioSet([{'label': 'L', 'value': 'L'},
                                     {'label': 'M', 'value': 'M'},
                                     {'label': 'Q', 'value': 'Q'},
                                     {'label': 'H', 'value': 'H'}])
        self.error_radio.setToolTip(
            _("Parameter that controls the error correction used for the QR Code.\n"
              "L = maximum 7%% errors can be corrected\n"
              "M = maximum 15%% errors can be corrected\n"
              "Q = maximum 25%% errors can be corrected\n"
              "H = maximum 30%% errors can be corrected.")
        )
        grid_lay.addWidget(self.error_label, 2, 0)
        grid_lay.addWidget(self.error_radio, 2, 1)

        # BOX SIZE #
        self.bsize_label = QtWidgets.QLabel('%s:' % _("Box Size"))
        self.bsize_label.setToolTip(
            _("Box size control the overall size of the QRcode\n"
              "by adjusting the size of each box in the code.")
        )
        self.bsize_entry = FCSpinner()
        self.bsize_entry.set_range(1, 9999)
        self.bsize_entry.setWrapping(True)

        grid_lay.addWidget(self.bsize_label, 3, 0)
        grid_lay.addWidget(self.bsize_entry, 3, 1)

        # BORDER SIZE #
        self.border_size_label = QtWidgets.QLabel('%s:' % _("Border Size"))
        self.border_size_label.setToolTip(
            _("Size of the QRCode border. How many boxes thick is the border.\n"
              "Default value is 4. The width of the clearance around the QRCode.")
        )
        self.border_size_entry = FCSpinner()
        self.border_size_entry.set_range(1, 9999)
        self.border_size_entry.setWrapping(True)

        grid_lay.addWidget(self.border_size_label, 4, 0)
        grid_lay.addWidget(self.border_size_entry, 4, 1)

        # Text box
        self.text_label = QtWidgets.QLabel('%s:' % _("QRCode Data"))
        self.text_label.setToolTip(
            _("QRCode Data. Alphanumeric text to be encoded in the QRCode.")
        )
        self.text_data = FCTextArea()
        self.text_data.setPlaceholderText(
            _("Add here the text to be included in the QRCode...")
        )
        grid_lay.addWidget(self.text_label, 5, 0)
        grid_lay.addWidget(self.text_data, 6, 0, 1, 2)

        # POLARITY CHOICE #
        self.pol_label = QtWidgets.QLabel('%s:' % _("Polarity"))
        self.pol_label.setToolTip(
            _("Choose the polarity of the QRCode.\n"
              "It can be drawn in a negative way (squares are clear)\n"
              "or in a positive way (squares are opaque).")
        )
        self.pol_radio = RadioSet([{'label': _('Negative'), 'value': 'neg'},
                                   {'label': _('Positive'), 'value': 'pos'}])
        self.pol_radio.setToolTip(
            _("Choose the type of QRCode to be created.\n"
              "If added on a Silkscreen Gerber file the QRCode may\n"
              "be added as positive. If it is added to a Copper Gerber\n"
              "file then perhaps the QRCode can be added as negative.")
        )
        grid_lay.addWidget(self.pol_label, 7, 0)
        grid_lay.addWidget(self.pol_radio, 7, 1)

        # BOUNDING BOX TYPE #
        self.bb_label = QtWidgets.QLabel('%s:' % _("Bounding Box"))
        self.bb_label.setToolTip(
            _("The bounding box, meaning the empty space that surrounds\n"
              "the QRCode geometry, can have a rounded or a square shape.")
        )
        self.bb_radio = RadioSet([{'label': _('Rounded'), 'value': 'r'},
                                  {'label': _('Square'), 'value': 's'}])
        self.bb_radio.setToolTip(
            _("The bounding box, meaning the empty space that surrounds\n"
              "the QRCode geometry, can have a rounded or a square shape.")
        )
        grid_lay.addWidget(self.bb_label, 8, 0)
        grid_lay.addWidget(self.bb_radio, 8, 1)

        # FILL COLOR #
        self.fill_color_label = QtWidgets.QLabel('%s:' % _('Fill Color'))
        self.fill_color_label.setToolTip(
            _("Set the QRCode fill color (squares color).")
        )
        self.fill_color_entry = FCColorEntry()

        grid_lay.addWidget(self.fill_color_label, 9, 0)
        grid_lay.addWidget(self.fill_color_entry, 9, 1)

        # BACK COLOR #
        self.back_color_label = QtWidgets.QLabel('%s:' % _('Back Color'))
        self.back_color_label.setToolTip(
            _("Set the QRCode background color.")
        )
        self.back_color_entry = FCColorEntry()

        grid_lay.addWidget(self.back_color_label, 10, 0)
        grid_lay.addWidget(self.back_color_entry, 10, 1)

        # Selection Limit
        self.sel_limit_label = QtWidgets.QLabel('%s:' % _("Selection limit"))
        self.sel_limit_label.setToolTip(
            _("Set the number of selected geometry\n"
              "items above which the utility geometry\n"
              "becomes just a selection rectangle.\n"
              "Increases the performance when moving a\n"
              "large number of geometric elements.")
        )
        self.sel_limit_entry = FCSpinner()
        self.sel_limit_entry.set_range(0, 9999)

        grid_lay.addWidget(self.sel_limit_label, 11, 0)
        grid_lay.addWidget(self.sel_limit_entry, 11, 1)
        # self.layout.addStretch()

        # QRCode Tool
        self.fill_color_entry.editingFinished.connect(self.on_qrcode_fill_color_entry)
        self.back_color_entry.editingFinished.connect(self.on_qrcode_back_color_entry)

    def on_qrcode_fill_color_entry(self):
        self.app.defaults['tools_qrcode_fill_color'] = self.fill_color_entry.get_value()

    def on_qrcode_back_color_entry(self):
        self.app.defaults['tools_qrcode_back_color'] = self.back_color_entry.get_value()
