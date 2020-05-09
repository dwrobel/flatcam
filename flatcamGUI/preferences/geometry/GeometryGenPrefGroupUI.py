from flatcamGUI.preferences.OptionUI import *
from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI2

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GeometryGenPrefGroupUI(OptionsGroupUI2):

    def __init__(self, decimals=4, **kwargs):
        self.decimals = decimals
        super().__init__(**kwargs)
        self.setTitle(str(_("Geometry General")))

    def build_options(self) -> [OptionUI]:
        return [
            HeadingOptionUI(label_text="Plot Options"),
            CheckboxOptionUI(
                option="geometry_plot",
                label_text="Plot",
                label_tooltip="Plot (show) this object."
            ),
            SpinnerOptionUI(
                option="geometry_circle_steps",
                label_text="Circle Steps",
                label_tooltip="The number of circle steps for <b>Geometry</b> \n"
                              "circle and arc shapes linear approximation.",
                min_value=0, max_value=9999, step=1
            ),
            HeadingOptionUI(label_text="Tools"),
            LineEntryOptionUI(
                option="geometry_cnctooldia",
                label_text="Tools Dia",
                label_color="green",
                label_bold=True,
                label_tooltip="Diameters of the tools, separated by comma.\n"
                              "The value of the diameter has to use the dot decimals separator.\n"
                              "Valid values: 0.3, 1.0"
            ),
            SeparatorOptionUI(),

            HeadingOptionUI(label_text="Geometry Object Color"),
            ColorOptionUI(
                option="geometry_plot_line",
                label_text="Outline",

                label_tooltip="Set the line color for plotted objects.",
            ),
        ]
