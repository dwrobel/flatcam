from flatcamGUI.preferences.OptionUI import *
from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI2

import gettext
import FlatCAMTranslation as fcTranslate
import builtins
fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GeometryEditorPrefGroupUI(OptionsGroupUI2):

    def __init__(self, decimals=4, **kwargs):
        self.decimals = decimals
        super().__init__(**kwargs)
        self.setTitle(str(_("Geometry Editor")))

    def build_options(self) -> [OptionUI]:
        return [
            HeadingOptionUI(label_text="Parameters"),
            SpinnerOptionUI(
                option="geometry_editor_sel_limit",
                label_text="Selection limit",
                label_tooltip="Set the number of selected geometry\n"
                              "items above which the utility geometry\n"
                              "becomes just a selection rectangle.\n"
                              "Increases the performance when moving a\n"
                              "large number of geometric elements.",
                min_value=0, max_value=9999, step=1
            ),
            RadioSetOptionUI(
                option="geometry_editor_milling_type",
                label_text="Milling Type",
                label_tooltip="Milling type:\n"
                              "- climb / best for precision milling and to reduce tool usage\n"
                              "- conventional / useful when there is no backlash compensation",
                choices=[{'label': _('Climb'), 'value': 'cl'},
                         {'label': _('Conventional'), 'value': 'cv'}]
            )
        ]