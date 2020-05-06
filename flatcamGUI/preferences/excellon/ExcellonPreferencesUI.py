from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI
from flatcamGUI.preferences.PreferencesSectionUI import PreferencesSectionUI
from flatcamGUI.preferences.excellon.ExcellonEditorPrefGroupUI import ExcellonEditorPrefGroupUI
from flatcamGUI.preferences.excellon.ExcellonExpPrefGroupUI import ExcellonExpPrefGroupUI
from flatcamGUI.preferences.excellon.ExcellonAdvOptPrefGroupUI import ExcellonAdvOptPrefGroupUI
from flatcamGUI.preferences.excellon.ExcellonOptPrefGroupUI import ExcellonOptPrefGroupUI
from flatcamGUI.preferences.excellon.ExcellonGenPrefGroupUI import ExcellonGenPrefGroupUI


class ExcellonPreferencesUI(PreferencesSectionUI):

    def __init__(self, decimals, **kwargs):
        self.decimals = decimals
        self.excellon_gen_group = ExcellonGenPrefGroupUI(decimals=self.decimals)
        self.excellon_opt_group = ExcellonOptPrefGroupUI(decimals=self.decimals)
        self.excellon_exp_group = ExcellonExpPrefGroupUI(decimals=self.decimals)
        self.excellon_adv_opt_group = ExcellonAdvOptPrefGroupUI(decimals=self.decimals)
        self.excellon_editor_group = ExcellonEditorPrefGroupUI(decimals=self.decimals)
        super().__init__(**kwargs)

    def build_groups(self) -> [OptionsGroupUI]:
        return [
            self.excellon_gen_group,
            self.excellon_opt_group,
            self.excellon_exp_group,
            self.excellon_adv_opt_group,
            self.excellon_editor_group
        ]

    def get_tab_id(self):
        return "excellon_tab"

    def get_tab_label(self):
        return _("EXCELLON")

