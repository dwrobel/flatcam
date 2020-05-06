from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI
from flatcamGUI.preferences.PreferencesSectionUI import PreferencesSectionUI
from flatcamGUI.preferences.gerber.GerberEditorPrefGroupUI import GerberEditorPrefGroupUI
from flatcamGUI.preferences.gerber.GerberExpPrefGroupUI import GerberExpPrefGroupUI
from flatcamGUI.preferences.gerber.GerberAdvOptPrefGroupUI import GerberAdvOptPrefGroupUI
from flatcamGUI.preferences.gerber.GerberOptPrefGroupUI import GerberOptPrefGroupUI
from flatcamGUI.preferences.gerber.GerberGenPrefGroupUI import GerberGenPrefGroupUI


class GerberPreferencesUI(PreferencesSectionUI):

    def __init__(self, decimals, **kwargs):
        self.decimals = decimals
        self.gerber_gen_group = GerberGenPrefGroupUI(decimals=self.decimals)
        self.gerber_opt_group = GerberOptPrefGroupUI(decimals=self.decimals)
        self.gerber_exp_group = GerberExpPrefGroupUI(decimals=self.decimals)
        self.gerber_adv_opt_group = GerberAdvOptPrefGroupUI(decimals=self.decimals)
        self.gerber_editor_group = GerberEditorPrefGroupUI(decimals=self.decimals)
        super().__init__(**kwargs)

    def build_groups(self) -> [OptionsGroupUI]:
        return [
            self.gerber_gen_group,
            self.gerber_opt_group,  # FIXME vertical layout with opt and ext
            self.gerber_exp_group,
            self.gerber_adv_opt_group,
            self.gerber_editor_group
        ]

    def get_tab_id(self):
        return "gerber_tab"

    def get_tab_label(self):
        return _("GERBER")
