from flatcamGUI.preferences.OptionUI import *
from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI2

import gettext
import FlatCAMTranslation as fcTranslate
import builtins
fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class CNCJobOptPrefGroupUI(OptionsGroupUI2):

    def __init__(self, decimals=4, **kwargs):
        self.decimals = decimals
        super().__init__(**kwargs)
        self.setTitle(str(_("CNC Job Options")))

    def build_options(self) -> [OptionUI]:
        return [
            HeadingOptionUI(
                label_text="Export G-Code",
                label_tooltip="Export and save G-Code to\n"
                              "make this object to a file."
            ),
            TextAreaOptionUI(
                option="cncjob_prepend",
                label_text="Prepend to G-Code",
                label_tooltip="Type here any G-Code commands you would\n"
                              "like to add at the beginning of the G-Code file."
            ),
            TextAreaOptionUI(
                option="cncjob_append",
                label_text="Append to G-Code",
                label_tooltip="Type here any G-Code commands you would\n"
                              "like to append to the generated file.\n"
                              "I.e.: M2 (End of program)"
            )
        ]
