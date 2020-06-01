from flatcamGUI.preferences.OptionUI import *
from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI2

import gettext
import FlatCAMTranslation as fcTranslate
import builtins
fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ExcellonExpPrefGroupUI(OptionsGroupUI2):

    def __init__(self, decimals=4, **kwargs):
        self.decimals = decimals
        super().__init__(**kwargs)
        self.setTitle(str(_("Excellon Export")))

        self.option_dict()["excellon_exp_format"].get_field().activated_custom.connect(self.optimization_selection)

    def build_options(self) -> [OptionUI]:
        return [
            HeadingOptionUI(
                label_text="Export Options",
                label_tooltip="The parameters set here are used in the file exported\n"
                              "when using the File -> Export -> Export Excellon menu entry."
            ),
            RadioSetOptionUI(
                option="excellon_exp_units",
                label_text="Units",
                label_tooltip="The units used in the Excellon file.",
                choices=[{'label': _('INCH'), 'value': 'INCH'},
                         {'label': _('MM'),   'value': 'METRIC'}]
            ),
            SpinnerOptionUI(
                option="excellon_exp_integer",
                label_text="Int",
                label_tooltip="This number signifies the number of digits in\nthe whole part of Excellon coordinates.",
                min_value=0, max_value=9, step=1
            ),
            SpinnerOptionUI(
                option="excellon_exp_decimals",
                label_text="Decimals",
                label_tooltip="This number signifies the number of digits in\nthe decimal part of Excellon coordinates.",
                min_value=0, max_value=9, step=1
            ),
            RadioSetOptionUI(
                option="excellon_exp_format",
                label_text="Format",
                label_tooltip="Select the kind of coordinates format used.\n"
                              "Coordinates can be saved with decimal point or without.\n"
                              "When there is no decimal point, it is required to specify\n"
                              "the number of digits for integer part and the number of decimals.\n"
                              "Also it will have to be specified if LZ = leading zeros are kept\n"
                              "or TZ = trailing zeros are kept.",
                choices=[{'label': _('Decimal'), 'value': 'dec'},
                         {'label': _('No-Decimal'), 'value': 'ndec'}]
            ),
            RadioSetOptionUI(
                option="excellon_exp_zeros",
                label_text="Zeros",
                label_tooltip="This sets the type of Excellon zeros.\n"
                              "If LZ then Leading Zeros are kept and\n"
                              "Trailing Zeros are removed.\n"
                              "If TZ is checked then Trailing Zeros are kept\n"
                              "and Leading Zeros are removed.",
                choices=[{'label': _('LZ'), 'value': 'LZ'},
                         {'label': _('TZ'), 'value': 'TZ'}]
            ),
            RadioSetOptionUI(
                option="excellon_exp_slot_type",
                label_text="Slot type",
                label_tooltip="This sets how the slots will be exported.\n"
                              "If ROUTED then the slots will be routed\n"
                              "using M15/M16 commands.\n"
                              "If DRILLED(G85) the slots will be exported\n"
                              "using the Drilled slot command (G85).",
                choices=[{'label': _('Routed'),       'value': 'routing'},
                         {'label': _('Drilled(G85)'), 'value': 'drilling'}]
            )
        ]

    def optimization_selection(self):
        disable_zeros = self.option_dict()["excellon_exp_format"].get_field().get_value() == "dec"
        self.option_dict()["excellon_exp_zeros"].label_widget.setDisabled(disable_zeros)
        self.option_dict()["excellon_exp_zeros"].get_field().setDisabled(disable_zeros)
