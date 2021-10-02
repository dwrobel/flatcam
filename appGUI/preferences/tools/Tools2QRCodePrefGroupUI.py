from PyQt6 import QtWidgets

from appGUI.GUIElements import FCSpinner, RadioSet, FCTextArea, FCLabel, FCColorEntry, FCGridLayout, FCFrame
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class Tools2QRCodePrefGroupUI(OptionsGroupUI):
    def __init__(self, defaults, decimals=4, parent=None):

        super(Tools2QRCodePrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("QRCode Plugin")))
        self.decimals = decimals
        self.defaults = defaults

        # #############################################################################################################
        # Parameters Frame
        # #############################################################################################################
        self.qrlabel = FCLabel('<span style="color:blue;"><b>%s</b></span>' % _("Parameters"))
        self.qrlabel.setToolTip(
            _("A tool to create a QRCode that can be inserted\n"
              "into a selected Gerber file, or it can be exported as a file.")
        )
        self.layout.addWidget(self.qrlabel)

        par_frame = FCFrame()
        self.layout.addWidget(par_frame)

        # ## Grid Layout
        param_grid = FCGridLayout(v_spacing=5, h_spacing=3)
        par_frame.setLayout(param_grid)

        # VERSION #
        self.version_label = FCLabel('%s:' % _("Version"))
        self.version_label.setToolTip(
            _("QRCode version can have values from 1 (21x21 boxes)\n"
              "to 40 (177x177 boxes).")
        )
        self.version_entry = FCSpinner()
        self.version_entry.set_range(1, 40)
        self.version_entry.setWrapping(True)

        param_grid.addWidget(self.version_label, 0, 0)
        param_grid.addWidget(self.version_entry, 0, 1)

        # ERROR CORRECTION #
        self.error_label = FCLabel('%s:' % _("Error correction"))
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
        param_grid.addWidget(self.error_label, 2, 0)
        param_grid.addWidget(self.error_radio, 2, 1)

        # BOX SIZE #
        self.bsize_label = FCLabel('%s:' % _("Box Size"))
        self.bsize_label.setToolTip(
            _("Box size control the overall size of the QRcode\n"
              "by adjusting the size of each box in the code.")
        )
        self.bsize_entry = FCSpinner()
        self.bsize_entry.set_range(1, 9999)
        self.bsize_entry.setWrapping(True)

        param_grid.addWidget(self.bsize_label, 4, 0)
        param_grid.addWidget(self.bsize_entry, 4, 1)

        # BORDER SIZE #
        self.border_size_label = FCLabel('%s:' % _("Border Size"))
        self.border_size_label.setToolTip(
            _("Size of the QRCode border. How many boxes thick is the border.\n"
              "Default value is 4. The width of the clearance around the QRCode.")
        )
        self.border_size_entry = FCSpinner()
        self.border_size_entry.set_range(1, 9999)
        self.border_size_entry.setWrapping(True)

        param_grid.addWidget(self.border_size_label, 6, 0)
        param_grid.addWidget(self.border_size_entry, 6, 1)

        # Text box
        self.text_label = FCLabel('%s:' % _("QRCode Data"))
        self.text_label.setToolTip(
            _("QRCode Data. Alphanumeric text to be encoded in the QRCode.")
        )
        self.text_data = FCTextArea()
        self.text_data.setPlaceholderText(
            _("Add here the text to be included in the QRCode...")
        )
        param_grid.addWidget(self.text_label, 8, 0)
        param_grid.addWidget(self.text_data, 10, 0, 1, 2)

        # POLARITY CHOICE #
        self.pol_label = FCLabel('%s:' % _("Polarity"))
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
        param_grid.addWidget(self.pol_label, 12, 0)
        param_grid.addWidget(self.pol_radio, 12, 1)

        # BOUNDING BOX TYPE #
        self.bb_label = FCLabel('%s:' % _("Bounding Box"))
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
        param_grid.addWidget(self.bb_label, 14, 0)
        param_grid.addWidget(self.bb_radio, 14, 1)

        # FILL COLOR #
        self.fill_color_label = FCLabel('%s:' % _('Fill Color'))
        self.fill_color_label.setToolTip(
            _("Set the QRCode fill color (squares color).")
        )
        self.fill_color_entry = FCColorEntry()

        param_grid.addWidget(self.fill_color_label, 16, 0)
        param_grid.addWidget(self.fill_color_entry, 16, 1)

        # BACK COLOR #
        self.back_color_label = FCLabel('%s:' % _('Back Color'))
        self.back_color_label.setToolTip(
            _("Set the QRCode background color.")
        )
        self.back_color_entry = FCColorEntry()

        param_grid.addWidget(self.back_color_label, 18, 0)
        param_grid.addWidget(self.back_color_entry, 18, 1)

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

        param_grid.addWidget(self.sel_limit_label, 20, 0)
        param_grid.addWidget(self.sel_limit_entry, 20, 1)
        # self.layout.addStretch()

        # QRCode Tool
        self.fill_color_entry.editingFinished.connect(self.on_qrcode_fill_color_entry)
        self.back_color_entry.editingFinished.connect(self.on_qrcode_back_color_entry)

    def on_qrcode_fill_color_entry(self):
        self.app.defaults['tools_qrcode_fill_color'] = self.fill_color_entry.get_value()

    def on_qrcode_back_color_entry(self):
        self.app.defaults['tools_qrcode_back_color'] = self.back_color_entry.get_value()
