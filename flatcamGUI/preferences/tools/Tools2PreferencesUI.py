from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI
from flatcamGUI.preferences.PreferencesSectionUI import PreferencesSectionUI
from flatcamGUI.preferences.tools.Tools2InvertPrefGroupUI import Tools2InvertPrefGroupUI
from flatcamGUI.preferences.tools.Tools2PunchGerberPrefGroupUI import Tools2PunchGerberPrefGroupUI
from flatcamGUI.preferences.tools.Tools2EDrillsPrefGroupUI import Tools2EDrillsPrefGroupUI
from flatcamGUI.preferences.tools.Tools2CalPrefGroupUI import Tools2CalPrefGroupUI
from flatcamGUI.preferences.tools.Tools2FiducialsPrefGroupUI import Tools2FiducialsPrefGroupUI
from flatcamGUI.preferences.tools.Tools2CThievingPrefGroupUI import Tools2CThievingPrefGroupUI
from flatcamGUI.preferences.tools.Tools2QRCodePrefGroupUI import Tools2QRCodePrefGroupUI
from flatcamGUI.preferences.tools.Tools2OptimalPrefGroupUI import Tools2OptimalPrefGroupUI
from flatcamGUI.preferences.tools.Tools2RulesCheckPrefGroupUI import Tools2RulesCheckPrefGroupUI


class Tools2PreferencesUI(PreferencesSectionUI):

    def __init__(self, decimals, **kwargs):
        self.decimals = decimals
        self.tools2_checkrules_group = Tools2RulesCheckPrefGroupUI(decimals=self.decimals)
        self.tools2_optimal_group = Tools2OptimalPrefGroupUI(decimals=self.decimals)
        self.tools2_qrcode_group = Tools2QRCodePrefGroupUI(decimals=self.decimals)
        self.tools2_cfill_group = Tools2CThievingPrefGroupUI(decimals=self.decimals)
        self.tools2_fiducials_group = Tools2FiducialsPrefGroupUI(decimals=self.decimals)
        self.tools2_cal_group = Tools2CalPrefGroupUI(decimals=self.decimals)
        self.tools2_edrills_group = Tools2EDrillsPrefGroupUI(decimals=self.decimals)
        self.tools2_punch_group = Tools2PunchGerberPrefGroupUI(decimals=self.decimals)
        self.tools2_invert_group = Tools2InvertPrefGroupUI(decimals=self.decimals)
        super().__init__(**kwargs)

    def build_groups(self) -> [OptionsGroupUI]:
        return [
            # fixme column 1
            self.tools2_checkrules_group,
            self.tools2_optimal_group,

            # fixme column 2
            self.tools2_qrcode_group,
            self.tools2_fiducials_group,

            # fixme column 3
            self.tools2_cfill_group,

            # fixme column 4
            self.tools2_cal_group,
            self.tools2_edrills_group,

            # fixme column 5
            self.tools2_punch_group,
            self.tools2_invert_group,
        ]