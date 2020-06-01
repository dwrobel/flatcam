from flatcamGUI.preferences.OptionUI import *
from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI2

import gettext
import FlatCAMTranslation as fcTranslate
import builtins
fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ExcellonEditorPrefGroupUI(OptionsGroupUI2):

    def __init__(self, decimals=4, **kwargs):
        self.decimals = decimals
        super().__init__(**kwargs)
        self.setTitle(str(_("Excellon Editor")))

    def build_options(self) -> [OptionUI]:
        return [
            HeadingOptionUI(
                label_text="Parameters",
                label_tooltip="A list of Excellon Editor parameters."
            ),
            SpinnerOptionUI(
                option="excellon_editor_sel_limit",
                label_text="Selection limit",
                label_tooltip="Set the number of selected Excellon geometry\n"
                              "items above which the utility geometry\n"
                              "becomes just a selection rectangle.\n"
                              "Increases the performance when moving a\n"
                              "large number of geometric elements.",
                min_value=0, max_value=99999, step=1
            ),
            DoubleSpinnerOptionUI(
                option="excellon_editor_newdia",
                label_text="New Dia",
                label_tooltip="Diameter for the new tool",
                min_value=0.000001, max_value=99.9999, step=0.1, decimals=self.decimals
            ),
            SpinnerOptionUI(
                option="excellon_editor_array_size",
                label_text="Nr of drills",
                label_tooltip="Specify how many drills to be in the array.",
                min_value=0, max_value=9999, step=1
            ),

            HeadingOptionUI(label_text="Linear Drill Array"),
            RadioSetOptionUI(
                option="excellon_editor_lin_dir",
                label_text="Linear Direction",
                label_tooltip="Direction on which the linear array is oriented:\n"
                              "- 'X' - horizontal axis \n"
                              "- 'Y' - vertical axis or \n"
                              "- 'Angle' - a custom angle for the array inclination",
                choices=[
                    {'label': _('X'),     'value': 'X'},
                    {'label': _('Y'),     'value': 'Y'},
                    {'label': _('Angle'), 'value': 'A'}
                ]
            ),
            DoubleSpinnerOptionUI(
                option="excellon_editor_lin_pitch",
                label_text="Pitch",
                label_tooltip="Pitch = Distance between elements of the array.",
                min_value=0, max_value=99999.9999, step=0.1, decimals=self.decimals
            ),
            DoubleSpinnerOptionUI(
                option="excellon_editor_lin_angle",
                label_text="Angle",
                label_tooltip="Angle at which each element in circular array is placed.",  # FIXME tooltip seems wrong ?
                min_value=-360, max_value=360, step=5, decimals=self.decimals
            ),

            HeadingOptionUI(label_text="Circular Drill Array"),
            RadioSetOptionUI(
                option="excellon_editor_circ_dir",
                label_text="Circular Direction",
                label_tooltip="Direction for circular array.\n"
                              "Can be CW = clockwise or CCW = counter clockwise.",
                choices=[
                    {'label': _('CW'), 'value': 'CW'},
                    {'label': _('CCW'), 'value': 'CCW'}
                ]
            ),
            DoubleSpinnerOptionUI(
                option="excellon_editor_circ_angle",
                label_text="Angle",
                label_tooltip="Angle at which each element in circular array is placed.",
                min_value=-360, max_value=360, step=5, decimals=self.decimals
            ),

            HeadingOptionUI(label_text="Slots"),
            DoubleSpinnerOptionUI(
                option="excellon_editor_slot_length",
                label_text="Length",
                label_tooltip="Length = The length of the slot.",
                min_value=0, max_value=99999, step=1, decimals=self.decimals
            ),
            RadioSetOptionUI(
                option="excellon_editor_slot_direction",
                label_text="Direction",
                label_tooltip="Direction on which the slot is oriented:\n"
                              "- 'X' - horizontal axis \n"
                              "- 'Y' - vertical axis or \n"
                              "- 'Angle' - a custom angle for the slot inclination",
                choices=[
                    {'label': _('X'),     'value': 'X'},
                    {'label': _('Y'),     'value': 'Y'},
                    {'label': _('Angle'), 'value': 'A'}
                ]
            ),
            DoubleSpinnerOptionUI(
                option="excellon_editor_slot_angle",
                label_text="Angle",
                label_tooltip="Angle at which the slot is placed.\n"
                              "The precision is of max 2 decimals.\n"
                              "Min value is: -359.99 degrees.\n"
                              "Max value is:  360.00 degrees.",
                min_value=-359.99, max_value=360.00, step=5, decimals=self.decimals
            ),

            HeadingOptionUI(label_text="Linear Slot Array"),
            SpinnerOptionUI(
                option="excellon_editor_slot_array_size",
                label_text="Nr of slots",
                label_tooltip="Specify how many slots to be in the array.",
                min_value=0, max_value=999999, step=1
            ),
            RadioSetOptionUI(
                option="excellon_editor_slot_lin_dir",
                label_text="Linear Direction",
                label_tooltip="Direction on which the linear array is oriented:\n"
                              "- 'X' - horizontal axis \n"
                              "- 'Y' - vertical axis or \n"
                              "- 'Angle' - a custom angle for the array inclination",
                choices=[
                    {'label': _('X'),     'value': 'X'},
                    {'label': _('Y'),     'value': 'Y'},
                    {'label': _('Angle'), 'value': 'A'}
                ]
            ),
            DoubleSpinnerOptionUI(
                option="excellon_editor_slot_lin_pitch",
                label_text="Pitch",
                label_tooltip="Pitch = Distance between elements of the array.",
                min_value=0, max_value=999999, step=1, decimals=self.decimals
            ),
            DoubleSpinnerOptionUI(
                option="excellon_editor_slot_lin_angle",
                label_text="Angle",
                label_tooltip="Angle at which each element in circular array is placed.", # FIXME
                min_value=-360, max_value=360, step=5, decimals=self.decimals
            ),

            HeadingOptionUI(label_text="Circular Slot Array"),
            RadioSetOptionUI(
                option="excellon_editor_slot_circ_dir",
                label_text="Circular Direction",
                label_tooltip="Direction for circular array.\n"
                              "Can be CW = clockwise or CCW = counter clockwise.",
                choices=[{'label': _('CW'), 'value': 'CW'},
                         {'label': _('CCW'), 'value': 'CCW'}]
            ),
            DoubleSpinnerOptionUI(
                option="excellon_editor_slot_circ_angle",
                label_text="Circular Angle",
                label_tooltip="Angle at which each element in circular array is placed.",
                min_value=-360, max_value=360, step=5, decimals=self.decimals
            )

        ]

