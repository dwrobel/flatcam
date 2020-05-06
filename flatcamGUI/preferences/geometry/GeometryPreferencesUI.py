from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI
from flatcamGUI.preferences.PreferencesSectionUI import PreferencesSectionUI
from flatcamGUI.preferences.geometry.GeometryEditorPrefGroupUI import GeometryEditorPrefGroupUI
from flatcamGUI.preferences.geometry.GeometryAdvOptPrefGroupUI import GeometryAdvOptPrefGroupUI
from flatcamGUI.preferences.geometry.GeometryOptPrefGroupUI import GeometryOptPrefGroupUI
from flatcamGUI.preferences.geometry.GeometryGenPrefGroupUI import GeometryGenPrefGroupUI


class GeometryPreferencesUI(PreferencesSectionUI):

    def __init__(self, decimals, **kwargs):
        self.decimals = decimals
        self.geometry_gen_group = GeometryGenPrefGroupUI(decimals=self.decimals)
        self.geometry_opt_group = GeometryOptPrefGroupUI(decimals=self.decimals)
        self.geometry_adv_opt_group = GeometryAdvOptPrefGroupUI(decimals=self.decimals)
        self.geometry_editor_group = GeometryEditorPrefGroupUI(decimals=self.decimals)
        super().__init__(**kwargs)

    def build_groups(self) -> [OptionsGroupUI]:
        return [
            self.geometry_gen_group,
            self.geometry_opt_group,
            self.geometry_adv_opt_group,
            self.geometry_editor_group
        ]

    def get_tab_id(self):
        return "geometry_tab"

    def get_tab_label(self):
        return _("GEOMETRY")

