from flatcamGUI.preferences.OptionUI import *
from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI2

import gettext
import FlatCAMTranslation as fcTranslate
import builtins
fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class CNCJobGenPrefGroupUI(OptionsGroupUI2):

    def __init__(self, decimals=4, **kwargs):
        self.decimals = decimals
        super().__init__(**kwargs)
        self.setTitle(str(_("CNC Job General")))

        # hidden for the time being, until implemented
        self.option_dict()["cncjob_coords_type"].label_widget.hide()
        self.option_dict()["cncjob_coords_type"].get_field().hide()

    def build_options(self) -> [OptionUI]:
        return [
            HeadingOptionUI(label_text="Plot Options"),
            CheckboxOptionUI(
                option="cncjob_plot",
                label_text="Plot Object",
                label_tooltip="Plot (show) this object."
            ),
            RadioSetOptionUI(
                option="cncjob_plot_kind",
                label_text="Plot kind",
                label_tooltip="This selects the kind of geometries on the canvas to plot.\n"
                              "Those can be either of type 'Travel' which means the moves\n"
                              "above the work piece or it can be of type 'Cut',\n"
                              "which means the moves that cut into the material.",
                choices=[
                    {"label": _("All"),    "value": "all"},
                    {"label": _("Travel"), "value": "travel"},
                    {"label": _("Cut"),    "value": "cut"}
                ],
                orientation="vertical"
            ),
            CheckboxOptionUI(
                option="cncjob_annotation",
                label_text="Display Annotation",
                label_tooltip="This selects if to display text annotation on the plot.\n"
                              "When checked it will display numbers in order for each end\n"
                              "of a travel line."
            ),
            SpinnerOptionUI(
                option="cncjob_steps_per_circle",
                label_text="Circle Steps",
                label_tooltip="The number of circle steps for <b>GCode</b> \n"
                              "circle and arc shapes linear approximation.",
                min_value=3, max_value=99999, step=1
            ),
            DoubleSpinnerOptionUI(
                option="cncjob_tooldia",
                label_text="Travel dia",
                label_tooltip="The width of the travel lines to be\n"
                              "rendered in the plot.",
                min_value=0, max_value=99999, step=0.1, decimals=self.decimals
            ),

            HeadingOptionUI(label_text="G-code Decimals"),
            SpinnerOptionUI(
                option="cncjob_coords_decimals",
                label_text="Coordinates",
                label_tooltip="The number of decimals to be used for \n"
                              "the X, Y, Z coordinates in CNC code (GCODE, etc.)",
                min_value=0, max_value=9, step=1
            ),
            SpinnerOptionUI(
                option="cncjob_fr_decimals",
                label_text="Feedrate",
                label_tooltip="The number of decimals to be used for \n"
                              "the Feedrate parameter in CNC code (GCODE, etc.)",
                min_value=0, max_value=9, step=1
            ),
            RadioSetOptionUI(
                option="cncjob_coords_type",
                label_text="Coordinates type",
                label_tooltip="The type of coordinates to be used in Gcode.\n"
                              "Can be:\n"
                              "- Absolute G90 -> the reference is the origin x=0, y=0\n"
                              "- Incremental G91 -> the reference is the previous position",
                choices=[
                    {"label": _("Absolute G90"),    "value": "G90"},
                    {"label": _("Incremental G91"), "value": "G91"}
                ],
                orientation="vertical"
            ),
            CheckboxOptionUI(
                option="cncjob_line_ending",
                label_text="Force Windows style line-ending",
                label_tooltip="When checked will force a Windows style line-ending\n"
                              "(\\r\\n) on non-Windows OS's."
            ),
            SeparatorOptionUI(),

            HeadingOptionUI(label_text="Travel Line Color"),
            ColorOptionUI(
                option="cncjob_travel_line",
                label_text="Outline",
                label_tooltip="Set the line color for plotted objects.",
            ),
            ColorOptionUI(
                option="cncjob_travel_fill",
                label_text="Fill",
                label_tooltip="Set the fill color for plotted objects.\n"
                              "First 6 digits are the color and the last 2\n"
                              "digits are for alpha (transparency) level."
            ),
            ColorAlphaSliderOptionUI(
                applies_to=["cncjob_travel_line", "cncjob_travel_fill"],
                group=self,
                label_text="Alpha",
                label_tooltip="Set the transparency for plotted objects."
            ),

            HeadingOptionUI(label_text="CNCJob Object  Color"),
            ColorOptionUI(
                option="cncjob_plot_line",
                label_text="Outline",
                label_tooltip="Set the line color for plotted objects.",
            ),
            ColorOptionUI(
                option="cncjob_plot_fill",
                label_text="Fill",
                label_tooltip="Set the fill color for plotted objects.\n"
                              "First 6 digits are the color and the last 2\n"
                              "digits are for alpha (transparency) level."
            ),
            ColorAlphaSliderOptionUI(
                applies_to=["cncjob_plot_line", "cncjob_plot_fill"],
                group=self,
                label_text="Alpha",
                label_tooltip="Set the transparency for plotted objects."
            )
        ]