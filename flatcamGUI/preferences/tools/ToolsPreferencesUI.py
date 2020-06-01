from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI
from flatcamGUI.preferences.PreferencesSectionUI import PreferencesSectionUI
from flatcamGUI.preferences.tools.ToolsSubPrefGroupUI import ToolsSubPrefGroupUI
from flatcamGUI.preferences.tools.ToolsSolderpastePrefGroupUI import ToolsSolderpastePrefGroupUI
from flatcamGUI.preferences.tools.ToolsTransformPrefGroupUI import ToolsTransformPrefGroupUI
from flatcamGUI.preferences.tools.ToolsCalculatorsPrefGroupUI import ToolsCalculatorsPrefGroupUI
from flatcamGUI.preferences.tools.ToolsPanelizePrefGroupUI import ToolsPanelizePrefGroupUI
from flatcamGUI.preferences.tools.ToolsFilmPrefGroupUI import ToolsFilmPrefGroupUI
from flatcamGUI.preferences.tools.ToolsPaintPrefGroupUI import ToolsPaintPrefGroupUI
from flatcamGUI.preferences.tools.Tools2sidedPrefGroupUI import Tools2sidedPrefGroupUI
from flatcamGUI.preferences.tools.ToolsCutoutPrefGroupUI import ToolsCutoutPrefGroupUI
from flatcamGUI.preferences.tools.ToolsNCCPrefGroupUI import ToolsNCCPrefGroupUI


class ToolsPreferencesUI(PreferencesSectionUI):

    def __init__(self, decimals, **kwargs):
        self.decimals = decimals
        self.tools_ncc_group = ToolsNCCPrefGroupUI(decimals=self.decimals)
        self.tools_paint_group = ToolsPaintPrefGroupUI(decimals=self.decimals)
        self.tools_cutout_group = ToolsCutoutPrefGroupUI(decimals=self.decimals)
        self.tools_2sided_group = Tools2sidedPrefGroupUI(decimals=self.decimals)
        self.tools_film_group = ToolsFilmPrefGroupUI(decimals=self.decimals)
        self.tools_panelize_group = ToolsPanelizePrefGroupUI(decimals=self.decimals)
        self.tools_calculators_group = ToolsCalculatorsPrefGroupUI(decimals=self.decimals)
        self.tools_transform_group = ToolsTransformPrefGroupUI(decimals=self.decimals)
        self.tools_solderpaste_group = ToolsSolderpastePrefGroupUI(decimals=self.decimals)
        self.tools_sub_group = ToolsSubPrefGroupUI(decimals=self.decimals)
        super().__init__(**kwargs)

    def build_groups(self) -> [OptionsGroupUI]:
        return [
            # fixme column 1
            self.tools_ncc_group,
            self.tools_cutout_group,

            # fixme column 2
            self.tools_paint_group,
            self.tools_panelize_group,

            # fixme column 3
            self.tools_transform_group,
            self.tools_2sided_group,
            self.tools_sub_group,

            # fixme column 4
            self.tools_film_group,
            self.tools_calculators_group,

            # fixme column 5
            self.tools_solderpaste_group,
        ]

    def get_tab_id(self):
        return "tools_tab"

    def get_tab_label(self):
        return _("TOOLS")
