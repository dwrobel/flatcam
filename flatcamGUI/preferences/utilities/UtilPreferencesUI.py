from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI
from flatcamGUI.preferences.PreferencesSectionUI import PreferencesSectionUI
from flatcamGUI.preferences.utilities.AutoCompletePrefGroupUI import AutoCompletePrefGroupUI
from flatcamGUI.preferences.utilities.FAGrbPrefGroupUI import FAGrbPrefGroupUI
from flatcamGUI.preferences.utilities.FAGcoPrefGroupUI import FAGcoPrefGroupUI
from flatcamGUI.preferences.utilities.FAExcPrefGroupUI import FAExcPrefGroupUI


class UtilPreferencesUI(PreferencesSectionUI):

    def __init__(self, decimals, **kwargs):
        self.decimals = decimals
        self.fa_excellon_group = FAExcPrefGroupUI(decimals=self.decimals)
        self.fa_gcode_group = FAGcoPrefGroupUI(decimals=self.decimals)
        self.fa_gerber_group = FAGrbPrefGroupUI(decimals=self.decimals)
        self.kw_group = AutoCompletePrefGroupUI(decimals=self.decimals)
        super().__init__(**kwargs)

    def build_groups(self) -> [OptionsGroupUI]:
        return [
            self.fa_excellon_group, # fixme column with fa_excellon and fa_gcode
            self.fa_gcode_group,
            self.fa_gerber_group,
            self.kw_group,
        ]
