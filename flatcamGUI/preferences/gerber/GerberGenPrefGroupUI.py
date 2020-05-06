from PyQt5 import QtCore, QtGui
from flatcamGUI.preferences.OptionUI import *
from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI2

import gettext
import FlatCAMTranslation as fcTranslate
import builtins
fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GerberGenPrefGroupUI(OptionsGroupUI2):
    def __init__(self, decimals=4, **kwargs):
        self.decimals = decimals
        super().__init__(**kwargs)
        self.setTitle(str(_("Gerber General")))

        self.plot_line_field = self.option_dict()["gerber_plot_line"].get_field()
        self.plot_fill_field = self.option_dict()["gerber_plot_fill"].get_field()
        self.plot_alpha_field = self.option_dict()["_gerber_plot_alpha"].get_field()
        self.plot_alpha_field.spinner.valueChanged.connect(self.on_plot_alpha_change)

    def build_options(self) -> [OptionUI]:
        return [
            HeadingOptionUI(label_text="Plot Options"),
            CheckboxOptionUI(
                option="gerber_solid",
                label_text="Solid",
                label_tooltip="Solid color polygons."
            ),
            CheckboxOptionUI(
                option="gerber_multicolored",
                label_text="M-Color",
                label_tooltip="Draw polygons in different colors."
            ),
            CheckboxOptionUI(
                option="gerber_plot",
                label_text="Plot",
                label_tooltip="Plot (show) this object."
            ),
            SpinnerOptionUI(
                option="gerber_circle_steps",
                label_text="Circle Steps",
                label_tooltip="The number of circle steps for Gerber \n"
                              "circular aperture linear approximation.",
                min_value=0, max_value=9999, step=1
            ),
            SeparatorOptionUI(),

            HeadingOptionUI(
                label_text="Default Values",
                label_tooltip="Those values will be used as fallback values\n"
                              "in case that they are not found in the Gerber file."
            ),
            RadioSetOptionUI(
                option="gerber_def_units",
                label_text="Units",
                label_tooltip="The units used in the Gerber file.",
                choices=[{'label': _('INCH'), 'value': 'IN'},
                         {'label': _('MM'),   'value': 'MM'}]
            ),
            RadioSetOptionUI(
                option="gerber_def_zeros",
                label_text="Zeros",
                label_tooltip="This sets the type of Gerber zeros.\n"
                              "If LZ then Leading Zeros are removed and\n"
                              "Trailing Zeros are kept.\n"
                              "If TZ is checked then Trailing Zeros are removed\n"
                              "and Leading Zeros are kept.",
                choices=[{'label': _('LZ'), 'value': 'L'},
                         {'label': _('TZ'), 'value': 'T'}]
            ),
            SeparatorOptionUI(),

            CheckboxOptionUI(
                option="gerber_clean_apertures",
                label_text="Clean Apertures",
                label_tooltip="Will remove apertures that do not have geometry\n"
                              "thus lowering the number of apertures in the Gerber object."
            ),
            CheckboxOptionUI(
                option="gerber_extra_buffering",
                label_text="Polarity change buffer",
                label_tooltip="Will apply extra buffering for the\n"
                              "solid geometry when we have polarity changes.\n"
                              "May help loading Gerber files that otherwise\n"
                              "do not load correctly."
            ),
            SeparatorOptionUI(),

            HeadingOptionUI(label_text="Gerber Object Color"),
            ColorOptionUI(
                option="gerber_plot_line",
                label_text="Outline",
                label_tooltip="Set the line color for plotted objects.",
            ),
            ColorOptionUI(
                option="gerber_plot_fill",
                label_text="Fill",
                label_tooltip="Set the fill color for plotted objects.\n"
                              "First 6 digits are the color and the last 2\n"
                              "digits are for alpha (transparency) level."
            ),
            SliderWithSpinnerOptionUI(
                option="_gerber_plot_alpha",
                label_text="Alpha",
                label_tooltip="Set the transparency for plotted objects.",
                min_value=0, max_value=255, step=1
            )
        ]

    def on_plot_alpha_change(self):
        alpha = self.plot_alpha_field.get_value()
        fill = self._modify_color_alpha(color=self.plot_fill_field.get_value(), alpha=alpha)
        self.plot_fill_field.set_value(fill)
        line = self._modify_color_alpha(color=self.plot_line_field.get_value(), alpha=alpha)
        self.plot_line_field.set_value(line)

    def _modify_color_alpha(self, color: str, alpha: int):
        color_without_alpha = color[:7]
        if alpha > 255:
            return color_without_alpha + "FF"
        elif alpha < 0:
            return color_without_alpha + "00"
        else:
            hexalpha = hex(alpha)[2:]
            if len(hexalpha) == 1:
                hexalpha = "0" + hexalpha
            return color_without_alpha + hexalpha


    # def on_pf_color_alpha_spinner(self):
    #     self.pf_color_alpha_slider.setValue(spinner_value)
    #     self.app.defaults['gerber_plot_fill'] = \
    #         self.app.defaults['gerber_plot_fill'][:7] + \
    #         (hex(spinner_value)[2:] if int(hex(spinner_value)[2:], 16) > 0 else '00')
    #     self.app.defaults['gerber_plot_line'] = \
    #         self.app.defaults['gerber_plot_line'][:7] + \
    #         (hex(spinner_value)[2:] if int(hex(spinner_value)[2:], 16) > 0 else '00')

