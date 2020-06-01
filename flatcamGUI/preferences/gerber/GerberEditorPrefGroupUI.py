from flatcamGUI.preferences.OptionUI import *
from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI2

import gettext
import FlatCAMTranslation as fcTranslate
import builtins
fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GerberEditorPrefGroupUI(OptionsGroupUI2):

    def __init__(self, decimals=4, **kwargs):
        self.decimals = decimals
        super().__init__(**kwargs)
        self.setTitle(str(_("Gerber Editor")))

    def build_options(self) -> [OptionUI]:
        return [
            HeadingOptionUI(
                label_text="Parameters",
                label_tooltip="A list of Gerber Editor parameters."
            ),
            SpinnerOptionUI(
                option="gerber_editor_sel_limit",
                label_text="Selection limit",
                label_tooltip="Set the number of selected Gerber geometry\n"
                              "items above which the utility geometry\n"
                              "becomes just a selection rectangle.\n"
                              "Increases the performance when moving a\n"
                              "large number of geometric elements.",
                min_value=0, max_value=9999, step=1
            ),
            SpinnerOptionUI(
                option="gerber_editor_newcode",
                label_text="New Aperture code",
                label_tooltip="Code for the new aperture",
                min_value=10, max_value=99, step=1
            ),
            DoubleSpinnerOptionUI(
                option="gerber_editor_newsize",
                label_text="New Aperture size",
                label_tooltip="Size for the new aperture",
                min_value=0.0, max_value=100.0, step=0.1, decimals=self.decimals
            ),
            ComboboxOptionUI(
                option="gerber_editor_newtype",
                label_text="New Aperture type",
                label_tooltip="Type for the new aperture.\n"
                              "Can be 'C', 'R' or 'O'.",
                choices=['C', 'R', 'O']
            ),
            SpinnerOptionUI(
                option="gerber_editor_array_size",
                label_text="Nr of pads",
                label_tooltip="Specify how many pads to be in the array.",
                min_value=0, max_value=9999, step=1
            ),
            LineEntryOptionUI(
                option="gerber_editor_newdim",
                label_text="Aperture Dimensions",
                label_tooltip="Diameters of the tools, separated by comma.\n"
                              "The value of the diameter has to use the dot decimals separator.\n"
                              "Valid values: 0.3, 1.0"
            ),

            HeadingOptionUI(label_text="Linear Pad Array"),
            RadioSetOptionUI(
                option="gerber_editor_lin_axis",
                label_text="Linear Direction",
                label_tooltip="Direction on which the linear array is oriented:\n"
                              "- 'X' - horizontal axis \n"
                              "- 'Y' - vertical axis or \n"
                              "- 'Angle' - a custom angle for the array inclination",
                choices=[{'label': _('X'), 'value': 'X'},
                         {'label': _('Y'), 'value': 'Y'},
                         {'label': _('Angle'), 'value': 'A'}]
            ),
            DoubleSpinnerOptionUI(
                option="gerber_editor_lin_pitch",
                label_text="Pitch",
                label_tooltip="Pitch = Distance between elements of the array.",
                min_value=-9999.99, max_value=9999.99, step=0.1, decimals=self.decimals
            ),
            DoubleSpinnerOptionUI(
                option="gerber_editor_lin_angle",
                label_text="Angle",
                label_tooltip="Angle at which each element in circular array is placed.",  # FIXME: this seems wrong
                min_value=-360, max_value=360, step=5, decimals=self.decimals
            ),

            HeadingOptionUI(label_text="Circular Pad Array"),
            RadioSetOptionUI(
                option="gerber_editor_circ_dir",
                label_text="Circular Direction",
                label_tooltip="Direction for circular array.\n"
                              "Can be CW = clockwise or CCW = counter clockwise.",
                choices=[{'label': _('CW'), 'value': 'CW'},
                         {'label': _('CCW'), 'value': 'CCW'}]
            ),
            DoubleSpinnerOptionUI(
                option="gerber_editor_circ_angle",
                label_text="Circular Angle",
                label_tooltip="Angle at which each element in circular array is placed.",
                min_value=-360, max_value=360, step=5, decimals=self.decimals
            ),

            HeadingOptionUI(label_text="Buffer Tool"),
            DoubleSpinnerOptionUI(
                option="gerber_editor_buff_f",
                label_text="Buffer distance",
                label_tooltip="Distance at which to buffer the Gerber element.",
                min_value=-9999, max_value=9999, step=0.1, decimals=self.decimals
            ),

            HeadingOptionUI(label_text="Scale Tool"),
            DoubleSpinnerOptionUI(
                option="gerber_editor_scale_f",
                label_text="Scale factor",
                label_tooltip="Factor to scale the Gerber element.",
                min_value=0, max_value=9999, step=0.1, decimals=self.decimals
            ),

            HeadingOptionUI(label_text="Mark Area Tool"),
            DoubleSpinnerOptionUI(
                option="gerber_editor_ma_low",
                label_text="Threshold low",
                label_tooltip="Threshold value under which the apertures are not marked.",
                min_value=0, max_value=9999, step=0.1, decimals=self.decimals
            ),
            DoubleSpinnerOptionUI(
                option="gerber_editor_ma_high",
                label_text="Threshold high",
                label_tooltip="Threshold value over which the apertures are not marked.",
                min_value=0, max_value=9999, step=0.1, decimals=self.decimals
            )
        ]
