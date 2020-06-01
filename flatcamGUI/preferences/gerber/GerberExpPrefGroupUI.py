from flatcamGUI.preferences.OptionUI import *
from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI2

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GerberExpPrefGroupUI(OptionsGroupUI2):

    def __init__(self, decimals=4, **kwargs):
        self.decimals = decimals
        super().__init__(**kwargs)
        self.setTitle(str(_("Gerber Export")))

    def build_options(self) -> [OptionUI]:
        return [
            HeadingOptionUI(
                label_text="Export Options",
                label_tooltip="The parameters set here are used in the file exported\n"
                              "when using the File -> Export -> Export Gerber menu entry."
            ),
            RadioSetOptionUI(
                option="gerber_exp_units",
                label_text="Units",
                label_tooltip="The units used in the Gerber file.",
                choices=[{'label': _('INCH'), 'value': 'IN'},
                         {'label': _('MM'),   'value': 'MM'}]
            ),
            SpinnerOptionUI(
                option="gerber_exp_integer",
                label_text="Int",
                label_tooltip="The number of digits in the whole part of Gerber coordinates",
                min_value=0, max_value=9, step=1
            ),
            SpinnerOptionUI(
                option="gerber_exp_decimals",
                label_text="Decimals",
                label_tooltip="The number of digits in the decimal part of Gerber coordinates",
                min_value=0, max_value=9, step=1
            ),
            RadioSetOptionUI(
                option="gerber_exp_zeros",
                label_text="Zeros",
                label_tooltip="This sets the type of Gerber zeros.\n"
                              "If LZ then Leading Zeros are removed and\n"
                              "Trailing Zeros are kept.\n"
                              "If TZ is checked then Trailing Zeros are removed\n"
                              "and Leading Zeros are kept.",
                choices=[{'label': _('LZ'), 'value': 'L'},
                         {'label': _('TZ'), 'value': 'T'}]
            )
        ]