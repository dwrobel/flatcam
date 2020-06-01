from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI
from flatcamGUI.preferences.PreferencesSectionUI import PreferencesSectionUI
from flatcamGUI.preferences.cncjob.CNCJobAdvOptPrefGroupUI import CNCJobAdvOptPrefGroupUI
from flatcamGUI.preferences.cncjob.CNCJobOptPrefGroupUI import CNCJobOptPrefGroupUI
from flatcamGUI.preferences.cncjob.CNCJobGenPrefGroupUI import CNCJobGenPrefGroupUI

import gettext
import FlatCAMTranslation as fcTranslate
import builtins
fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class CNCJobPreferencesUI(PreferencesSectionUI):

    def __init__(self, decimals, **kwargs):
        self.decimals = decimals
        super().__init__(**kwargs)

    def build_groups(self) -> [OptionsGroupUI]:
        return [
            CNCJobGenPrefGroupUI(decimals=self.decimals),
            CNCJobOptPrefGroupUI(decimals=self.decimals),
            CNCJobAdvOptPrefGroupUI(decimals=self.decimals)
        ]

    def get_tab_id(self):
        # FIXME this doesn't seem right
        return "text_editor_tab"

    def get_tab_label(self):
        return _("CNC-JOB")