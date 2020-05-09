from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI
from flatcamGUI.preferences.PreferencesSectionUI import PreferencesSectionUI
from flatcamGUI.preferences.gerber.GerberEditorPrefGroupUI import GerberEditorPrefGroupUI
from flatcamGUI.preferences.gerber.GerberExpPrefGroupUI import GerberExpPrefGroupUI
from flatcamGUI.preferences.gerber.GerberAdvOptPrefGroupUI import GerberAdvOptPrefGroupUI
from flatcamGUI.preferences.gerber.GerberOptPrefGroupUI import GerberOptPrefGroupUI
from flatcamGUI.preferences.gerber.GerberGenPrefGroupUI import GerberGenPrefGroupUI

import gettext
import FlatCAMTranslation as fcTranslate
import builtins
fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GerberPreferencesUI(PreferencesSectionUI):

    def __init__(self, decimals, **kwargs):
        self.decimals = decimals
        super().__init__(**kwargs)

    def build_groups(self) -> [OptionsGroupUI]:
        return [
            GerberGenPrefGroupUI(decimals=self.decimals),

            GerberOptPrefGroupUI(decimals=self.decimals),  # FIXME vertical layout with opt and exp
            GerberExpPrefGroupUI(decimals=self.decimals),

            GerberAdvOptPrefGroupUI(decimals=self.decimals),
            GerberEditorPrefGroupUI(decimals=self.decimals)
        ]

    def get_tab_id(self):
        return "gerber_tab"

    def get_tab_label(self):
        return _("GERBER")
