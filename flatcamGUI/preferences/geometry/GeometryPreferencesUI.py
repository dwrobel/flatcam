from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI
from flatcamGUI.preferences.PreferencesSectionUI import PreferencesSectionUI
from flatcamGUI.preferences.geometry.GeometryEditorPrefGroupUI import GeometryEditorPrefGroupUI
from flatcamGUI.preferences.geometry.GeometryAdvOptPrefGroupUI import GeometryAdvOptPrefGroupUI
from flatcamGUI.preferences.geometry.GeometryOptPrefGroupUI import GeometryOptPrefGroupUI
from flatcamGUI.preferences.geometry.GeometryGenPrefGroupUI import GeometryGenPrefGroupUI

import gettext
import FlatCAMTranslation as fcTranslate
import builtins
fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GeometryPreferencesUI(PreferencesSectionUI):

    def __init__(self, decimals, **kwargs):
        self.decimals = decimals
        # FIXME: remove the need for external access to geometry_opt_group
        self.geometry_opt_group = GeometryOptPrefGroupUI(decimals=self.decimals)
        super().__init__(**kwargs)

    def build_groups(self) -> [OptionsGroupUI]:
        return [
            GeometryGenPrefGroupUI(decimals=self.decimals),
            self.geometry_opt_group,
            GeometryAdvOptPrefGroupUI(decimals=self.decimals),
            GeometryEditorPrefGroupUI(decimals=self.decimals)
        ]

    def get_tab_id(self):
        return "geometry_tab"

    def get_tab_label(self):
        return _("GEOMETRY")

