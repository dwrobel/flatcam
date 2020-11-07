from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings

from appGUI.GUIElements import RadioSet, FCDoubleSpinner, FCCheckBox, FCComboBox, FCColorEntry, FCLabel, FCSpinner
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


class ToolsFilmPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "Cutout Tool Options", parent=parent)
        super(ToolsFilmPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Film Tool Options")))
        self.decimals = decimals

        # ## Parameters
        self.film_label = FCLabel("<b>%s:</b>" % _("Parameters"))
        self.film_label.setToolTip(
            _("Create a PCB film from a Gerber or Geometry object.\n"
              "The file is saved in SVG format.")
        )
        self.layout.addWidget(self.film_label)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        self.film_type_radio = RadioSet([{'label': 'Pos', 'value': 'pos'},
                                         {'label': 'Neg', 'value': 'neg'}])
        ftypelbl = FCLabel('%s:' % _('Film Type'))
        ftypelbl.setToolTip(
            _("Generate a Positive black film or a Negative film.\n"
              "Positive means that it will print the features\n"
              "with black on a white canvas.\n"
              "Negative means that it will print the features\n"
              "with white on a black canvas.\n"
              "The Film format is SVG.")
        )
        grid0.addWidget(ftypelbl, 0, 0)
        grid0.addWidget(self.film_type_radio, 0, 1)

        # Film Color
        self.film_color_label = FCLabel('%s:' % _('Film Color'))
        self.film_color_label.setToolTip(
            _("Set the film color when positive film is selected.")
        )
        self.film_color_entry = FCColorEntry()

        grid0.addWidget(self.film_color_label, 1, 0)
        grid0.addWidget(self.film_color_entry, 1, 1)

        # Film Border
        self.film_boundary_entry = FCDoubleSpinner()
        self.film_boundary_entry.set_precision(self.decimals)
        self.film_boundary_entry.set_range(0, 10000.0000)
        self.film_boundary_entry.setSingleStep(0.1)

        self.film_boundary_label = FCLabel('%s:' % _("Border"))
        self.film_boundary_label.setToolTip(
            _("Specify a border around the object.\n"
              "Only for negative film.\n"
              "It helps if we use as a Box Object the same \n"
              "object as in Film Object. It will create a thick\n"
              "black bar around the actual print allowing for a\n"
              "better delimitation of the outline features which are of\n"
              "white color like the rest and which may confound with the\n"
              "surroundings if not for this border.")
        )
        grid0.addWidget(self.film_boundary_label, 2, 0)
        grid0.addWidget(self.film_boundary_entry, 2, 1)

        self.film_scale_stroke_entry = FCDoubleSpinner()
        self.film_scale_stroke_entry.set_precision(self.decimals)
        self.film_scale_stroke_entry.set_range(0, 10000.0000)
        self.film_scale_stroke_entry.setSingleStep(0.1)

        self.film_scale_stroke_label = FCLabel('%s:' % _("Scale Stroke"))
        self.film_scale_stroke_label.setToolTip(
            _("Scale the line stroke thickness of each feature in the SVG file.\n"
              "It means that the line that envelope each SVG feature will be thicker or thinner,\n"
              "therefore the fine features may be more affected by this parameter.")
        )
        grid0.addWidget(self.film_scale_stroke_label, 3, 0)
        grid0.addWidget(self.film_scale_stroke_entry, 3, 1)

        self.film_adj_label = FCLabel('<b>%s</b>' % _("Film Adjustments"))
        self.film_adj_label.setToolTip(
            _("Sometime the printers will distort the print shape, especially the Laser types.\n"
              "This section provide the tools to compensate for the print distortions.")
        )

        grid0.addWidget(self.film_adj_label, 4, 0, 1, 2)

        # Scale Geometry
        self.film_scale_cb = FCCheckBox('%s' % _("Scale Film geometry"))
        self.film_scale_cb.setToolTip(
            _("A value greater than 1 will stretch the film\n"
              "while a value less than 1 will jolt it.")
        )
        self.film_scale_cb.setStyleSheet(
            """
            QCheckBox {font-weight: bold; color: black}
            """
        )
        grid0.addWidget(self.film_scale_cb, 5, 0, 1, 2)

        self.film_scalex_label = FCLabel('%s:' % _("X factor"))
        self.film_scalex_entry = FCDoubleSpinner()
        self.film_scalex_entry.set_range(-999.9999, 999.9999)
        self.film_scalex_entry.set_precision(self.decimals)
        self.film_scalex_entry.setSingleStep(0.01)

        grid0.addWidget(self.film_scalex_label, 6, 0)
        grid0.addWidget(self.film_scalex_entry, 6, 1)

        self.film_scaley_label = FCLabel('%s:' % _("Y factor"))
        self.film_scaley_entry = FCDoubleSpinner()
        self.film_scaley_entry.set_range(-999.9999, 999.9999)
        self.film_scaley_entry.set_precision(self.decimals)
        self.film_scaley_entry.setSingleStep(0.01)

        grid0.addWidget(self.film_scaley_label, 7, 0)
        grid0.addWidget(self.film_scaley_entry, 7, 1)

        # Skew Geometry
        self.film_skew_cb = FCCheckBox('%s' % _("Skew Film geometry"))
        self.film_skew_cb.setToolTip(
            _("Positive values will skew to the right\n"
              "while negative values will skew to the left.")
        )
        self.film_skew_cb.setStyleSheet(
            """
            QCheckBox {font-weight: bold; color: black}
            """
        )
        grid0.addWidget(self.film_skew_cb, 8, 0, 1, 2)

        self.film_skewx_label = FCLabel('%s:' % _("X angle"))
        self.film_skewx_entry = FCDoubleSpinner()
        self.film_skewx_entry.set_range(-999.9999, 999.9999)
        self.film_skewx_entry.set_precision(self.decimals)
        self.film_skewx_entry.setSingleStep(0.01)

        grid0.addWidget(self.film_skewx_label, 9, 0)
        grid0.addWidget(self.film_skewx_entry, 9, 1)

        self.film_skewy_label = FCLabel('%s:' % _("Y angle"))
        self.film_skewy_entry = FCDoubleSpinner()
        self.film_skewy_entry.set_range(-999.9999, 999.9999)
        self.film_skewy_entry.set_precision(self.decimals)
        self.film_skewy_entry.setSingleStep(0.01)

        grid0.addWidget(self.film_skewy_label, 10, 0)
        grid0.addWidget(self.film_skewy_entry, 10, 1)

        self.film_skew_ref_label = FCLabel('%s:' % _("Reference"))
        self.film_skew_ref_label.setToolTip(
            _("The reference point to be used as origin for the skew.\n"
              "It can be one of the four points of the geometry bounding box.")
        )
        self.film_skew_reference = RadioSet([{'label': _('Bottom Left'), 'value': 'bottomleft'},
                                             {'label': _('Top Left'), 'value': 'topleft'},
                                             {'label': _('Bottom Right'), 'value': 'bottomright'},
                                             {'label': _('Top right'), 'value': 'topright'}],
                                            orientation='vertical',
                                            stretch=False)

        grid0.addWidget(self.film_skew_ref_label, 11, 0)
        grid0.addWidget(self.film_skew_reference, 11, 1)

        # Mirror Geometry
        self.film_mirror_cb = FCCheckBox('%s' % _("Mirror Film geometry"))
        self.film_mirror_cb.setToolTip(
            _("Mirror the film geometry on the selected axis or on both.")
        )
        self.film_mirror_cb.setStyleSheet(
            """
            QCheckBox {font-weight: bold; color: black}
            """
        )
        grid0.addWidget(self.film_mirror_cb, 12, 0, 1, 2)

        self.film_mirror_axis = RadioSet([{'label': _('None'), 'value': 'none'},
                                          {'label': _('X'), 'value': 'x'},
                                          {'label': _('Y'), 'value': 'y'},
                                          {'label': _('Both'), 'value': 'both'}],
                                         stretch=False)
        self.film_mirror_axis_label = FCLabel('%s:' % _("Mirror Axis"))

        grid0.addWidget(self.film_mirror_axis_label, 13, 0)
        grid0.addWidget(self.film_mirror_axis, 13, 1)

        separator_line3 = QtWidgets.QFrame()
        separator_line3.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line3.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line3, 14, 0, 1, 2)

        self.file_type_radio = RadioSet([{'label': _('SVG'), 'value': 'svg'},
                                         {'label': _('PNG'), 'value': 'png'},
                                         {'label': _('PDF'), 'value': 'pdf'}
                                         ], stretch=False)

        self.file_type_label = FCLabel('%s:' % _("Film Type"))
        self.file_type_label.setToolTip(
            _("The file type of the saved film. Can be:\n"
              "- 'SVG' -> open-source vectorial format\n"
              "- 'PNG' -> raster image\n"
              "- 'PDF' -> portable document format")
        )
        grid0.addWidget(self.file_type_label, 15, 0)
        grid0.addWidget(self.file_type_radio, 15, 1)

        # Page orientation
        self.orientation_label = FCLabel('%s:' % _("Page Orientation"))
        self.orientation_label.setToolTip(_("Can be:\n"
                                            "- Portrait\n"
                                            "- Landscape"))

        self.orientation_radio = RadioSet([{'label': _('Portrait'), 'value': 'p'},
                                           {'label': _('Landscape'), 'value': 'l'},
                                           ], stretch=False)

        grid0.addWidget(self.orientation_label, 16, 0)
        grid0.addWidget(self.orientation_radio, 16, 1)

        # Page Size
        self.pagesize_label = FCLabel('%s:' % _("Page Size"))
        self.pagesize_label.setToolTip(_("A selection of standard ISO 216 page sizes."))

        self.pagesize_combo = FCComboBox()

        self.pagesize = {}
        self.pagesize.update(
            {
                'Bounds': None,
                'A0': (841, 1189),
                'A1': (594, 841),
                'A2': (420, 594),
                'A3': (297, 420),
                'A4': (210, 297),
                'A5': (148, 210),
                'A6': (105, 148),
                'A7': (74, 105),
                'A8': (52, 74),
                'A9': (37, 52),
                'A10': (26, 37),

                'B0': (1000, 1414),
                'B1': (707, 1000),
                'B2': (500, 707),
                'B3': (353, 500),
                'B4': (250, 353),
                'B5': (176, 250),
                'B6': (125, 176),
                'B7': (88, 125),
                'B8': (62, 88),
                'B9': (44, 62),
                'B10': (31, 44),

                'C0': (917, 1297),
                'C1': (648, 917),
                'C2': (458, 648),
                'C3': (324, 458),
                'C4': (229, 324),
                'C5': (162, 229),
                'C6': (114, 162),
                'C7': (81, 114),
                'C8': (57, 81),
                'C9': (40, 57),
                'C10': (28, 40),

                # American paper sizes
                'LETTER': (8.5, 11),
                'LEGAL': (8.5, 14),
                'ELEVENSEVENTEEN': (11, 17),

                # From https://en.wikipedia.org/wiki/Paper_size
                'JUNIOR_LEGAL': (5, 8),
                'HALF_LETTER': (5.5, 8),
                'GOV_LETTER': (8, 10.5),
                'GOV_LEGAL': (8.5, 13),
                'LEDGER': (17, 11),
            }
        )

        page_size_list = list(self.pagesize.keys())
        self.pagesize_combo.addItems(page_size_list)

        grid0.addWidget(self.pagesize_label, 17, 0)
        grid0.addWidget(self.pagesize_combo, 17, 1)

        # PNG DPI
        self.png_dpi_label = FCLabel('%s:' % "PNG DPI")
        self.png_dpi_label.setToolTip(
            _("Default value is 96 DPI. Change this value to scale the PNG file.")
        )
        self.png_dpi_spinner = FCSpinner()
        self.png_dpi_spinner.set_range(0, 100000)

        grid0.addWidget(self.png_dpi_label, 19, 0)
        grid0.addWidget(self.png_dpi_spinner, 19, 1)

        self.layout.addStretch()

        # Film Tool
        self.film_color_entry.editingFinished.connect(self.on_film_color_entry)

    def on_film_color_entry(self):
        self.app.defaults['tools_film_color'] = self.film_color_entry.get_value()
