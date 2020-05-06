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
            ColorAlphaSliderOptionUI(
                applies_to=["gerber_plot_line", "gerber_plot_fill"],
                group=self,
                label_text="Alpha",
                label_tooltip="Set the transparency for plotted objects."
            )
        ]

