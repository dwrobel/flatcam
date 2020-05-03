from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI
from flatcamGUI.preferences.PreferencesSectionUI import PreferencesSectionUI
from flatcamGUI.preferences.general.GeneralAppPrefGroupUI import GeneralAppPrefGroupUI
from flatcamGUI.preferences.general.GeneralAppSettingsGroupUI import GeneralAppSettingsGroupUI
from flatcamGUI.preferences.general.GeneralGUIPrefGroupUI import GeneralGUIPrefGroupUI


class GeneralPreferencesUI(PreferencesSectionUI):

    def __init__(self, decimals, **kwargs):
        self.decimals = decimals
        self.general_gui_group = GeneralGUIPrefGroupUI(decimals=self.decimals)
        self.general_app_group = GeneralAppPrefGroupUI(decimals=self.decimals)
        self.general_app_settings_group = GeneralAppSettingsGroupUI(decimals=self.decimals)
        super().__init__(**kwargs)

    def build_groups(self) -> [OptionsGroupUI]:
        return [
            self.general_app_group,
            self.general_gui_group,
            self.general_app_settings_group
        ]

