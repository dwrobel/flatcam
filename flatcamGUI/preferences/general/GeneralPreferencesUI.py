from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI
from flatcamGUI.preferences.PreferencesSectionUI import PreferencesSectionUI
from flatcamGUI.preferences.general.GeneralAppPrefGroupUI import GeneralAppPrefGroupUI
from flatcamGUI.preferences.general.GeneralAPPSetGroupUI import GeneralAPPSetGroupUI
from flatcamGUI.preferences.general.GeneralGUIPrefGroupUI import GeneralGUIPrefGroupUI2


class GeneralPreferencesUI(PreferencesSectionUI):

    def __init__(self, decimals, **kwargs):
        self.decimals = decimals
        self.general_gui_group = GeneralGUIPrefGroupUI2(decimals=self.decimals)
        self.general_app_group = GeneralAppPrefGroupUI(decimals=self.decimals)
        self.general_app_set_group = GeneralAPPSetGroupUI(decimals=self.decimals)
        super().__init__(**kwargs)

    def build_groups(self) -> [OptionsGroupUI]:
        return [
            self.general_app_group,
            self.general_gui_group,
            self.general_app_set_group
        ]

