from PyQt5.QtCore import QSettings

from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI
from flatcamGUI.preferences.PreferencesSectionUI import PreferencesSectionUI
from flatcamGUI.preferences.general.GeneralAppPrefGroupUI import GeneralAppPrefGroupUI
from flatcamGUI.preferences.general.GeneralAPPSetGroupUI import GeneralAPPSetGroupUI
from flatcamGUI.preferences.general.GeneralGUIPrefGroupUI import GeneralGUIPrefGroupUI, GeneralGUIPrefGroupUI2

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

settings = QSettings("Open Source", "FlatCAM")
if settings.contains("machinist"):
    machinist_setting = settings.value('machinist', type=int)
else:
    machinist_setting = 0


class GeneralPreferencesUI(PreferencesSectionUI):

    def __init__(self, decimals, **kwargs):
        self.decimals = decimals
        self.general_gui_group = GeneralGUIPrefGroupUI(decimals=self.decimals)
        self.general_gui_group2 = GeneralGUIPrefGroupUI2(decimals=self.decimals)
        self.general_app_group = GeneralAppPrefGroupUI(decimals=self.decimals)
        self.general_app_set_group = GeneralAPPSetGroupUI(decimals=self.decimals)
        super().__init__(**kwargs)

    def build_groups(self) -> [OptionsGroupUI]:
        return [
            self.general_app_group,
            self.general_gui_group,
            self.general_gui_group2,
            self.general_app_set_group
        ]

