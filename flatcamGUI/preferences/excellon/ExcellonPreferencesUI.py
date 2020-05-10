from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI
from flatcamGUI.preferences.PreferencesSectionUI import PreferencesSectionUI
from flatcamGUI.preferences.excellon.ExcellonEditorPrefGroupUI import ExcellonEditorPrefGroupUI
from flatcamGUI.preferences.excellon.ExcellonExpPrefGroupUI import ExcellonExpPrefGroupUI
from flatcamGUI.preferences.excellon.ExcellonAdvOptPrefGroupUI import ExcellonAdvOptPrefGroupUI
from flatcamGUI.preferences.excellon.ExcellonOptPrefGroupUI import ExcellonOptPrefGroupUI
from flatcamGUI.preferences.excellon.ExcellonGenPrefGroupUI import ExcellonGenPrefGroupUI

import gettext
import FlatCAMTranslation as fcTranslate
import builtins
fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ExcellonPreferencesUI(PreferencesSectionUI):

    def __init__(self, decimals, **kwargs):
        self.decimals = decimals
        # FIXME: remove the need for external access to excellon_opt_group
        self.excellon_opt_group = ExcellonOptPrefGroupUI(decimals=self.decimals)
        self.excellon_editor_group = ExcellonEditorPrefGroupUI(decimals=self.decimals)
        super().__init__(**kwargs)
        self.init_sync_export()

    def build_groups(self) -> [OptionsGroupUI]:
        return [
            ExcellonGenPrefGroupUI(decimals=self.decimals),
            self.excellon_opt_group,
            ExcellonExpPrefGroupUI(decimals=self.decimals),
            ExcellonAdvOptPrefGroupUI(decimals=self.decimals),
            self.excellon_editor_group
        ]

    def get_tab_id(self):
        return "excellon_tab"

    def get_tab_label(self):
        return _("EXCELLON")

    def init_sync_export(self):
        self.option_dict()["excellon_update"].get_field().stateChanged.connect(self.sync_export)
        self.option_dict()["excellon_format_upper_in"].get_field().returnPressed.connect(self.sync_export)
        self.option_dict()["excellon_format_lower_in"].get_field().returnPressed.connect(self.sync_export)
        self.option_dict()["excellon_format_upper_mm"].get_field().returnPressed.connect(self.sync_export)
        self.option_dict()["excellon_format_lower_mm"].get_field().returnPressed.connect(self.sync_export)
        self.option_dict()["excellon_zeros"].get_field().activated_custom.connect(self.sync_export)
        self.option_dict()["excellon_units"].get_field().activated_custom.connect(self.sync_export)

    def sync_export(self):
        if not self.option_dict()["excellon_update"].get_field().get_value():
            # User has disabled sync.
            return

        zeros = self.option_dict()["excellon_zeros"].get_field().get_value() + 'Z'
        self.option_dict()["excellon_exp_zeros"].get_field().set_value(zeros)

        units = self.option_dict()["excellon_units"].get_field().get_value()
        self.option_dict()["excellon_exp_units"].get_field().set_value(units)

        if units.upper() == 'METRIC':
            whole = self.option_dict()["excellon_format_upper_mm"].get_field().get_value()
            dec = self.option_dict()["excellon_format_lower_mm"].get_field().get_value()
        else:
            whole = self.option_dict()["excellon_format_upper_in"].get_field().get_value()
            dec = self.option_dict()["excellon_format_lower_in"].get_field().get_value()
        self.option_dict()["excellon_exp_integer"].get_field().set_value(whole)
        self.option_dict()["excellon_exp_decimals"].get_field().set_value(dec)


