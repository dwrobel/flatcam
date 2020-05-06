from PyQt5 import QtWidgets

from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI
from flatcamGUI.preferences.PreferencesSectionUI import PreferencesSectionUI
from flatcamGUI.preferences.cncjob.CNCJobAdvOptPrefGroupUI import CNCJobAdvOptPrefGroupUI
from flatcamGUI.preferences.cncjob.CNCJobOptPrefGroupUI import CNCJobOptPrefGroupUI
from flatcamGUI.preferences.cncjob.CNCJobGenPrefGroupUI import CNCJobGenPrefGroupUI


class CNCJobPreferencesUI(PreferencesSectionUI):

    def __init__(self, decimals, **kwargs):
        self.decimals = decimals
        self.cncjob_gen_group = CNCJobGenPrefGroupUI(decimals=self.decimals)
        self.cncjob_opt_group = CNCJobOptPrefGroupUI(decimals=self.decimals)
        self.cncjob_adv_opt_group = CNCJobAdvOptPrefGroupUI(decimals=self.decimals)
        super().__init__(**kwargs)

    def build_groups(self) -> [OptionsGroupUI]:
        return [
            self.cncjob_gen_group,
            self.cncjob_opt_group,
            self.cncjob_adv_opt_group
        ]

    def get_tab_id(self):
        # FIXME this doesn't seem right
        return "text_editor_tab"

    def get_tab_label(self):
        return _("CNC-JOB")