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
        self.excellon_gen_group = ExcellonGenPrefGroupUI(decimals=self.decimals)

        # FIXME: remove the need for external access to excellon_opt_group
        self.excellon_opt_group = ExcellonOptPrefGroupUI(decimals=self.decimals)

        self.excellon_exp_group = ExcellonExpPrefGroupUI(decimals=self.decimals)
        self.excellon_adv_opt_group = ExcellonAdvOptPrefGroupUI(decimals=self.decimals)
        self.excellon_editor_group = ExcellonEditorPrefGroupUI(decimals=self.decimals)
        super().__init__(**kwargs)

        self.excellon_gen_group.excellon_format_upper_in_entry.returnPressed.connect(self.sync_export)
        self.excellon_gen_group.excellon_format_lower_in_entry.returnPressed.connect(self.sync_export)
        self.excellon_gen_group.excellon_format_upper_mm_entry.returnPressed.connect(self.sync_export)
        self.excellon_gen_group.excellon_format_lower_mm_entry.returnPressed.connect(self.sync_export)
        self.excellon_gen_group.excellon_zeros_radio.activated_custom.connect(self.sync_export)
        self.excellon_gen_group.excellon_units_radio.activated_custom.connect(self.sync_export)


    def build_groups(self) -> [OptionsGroupUI]:
        return [
            self.excellon_gen_group,
            self.excellon_opt_group,
            self.excellon_exp_group,
            self.excellon_adv_opt_group,
            self.excellon_editor_group
        ]

    def get_tab_id(self):
        return "excellon_tab"

    def get_tab_label(self):
        return _("EXCELLON")

    def sync_export(self):
        if not self.excellon_gen_group.update_excellon_cb.get_value():
            # User has disabled sync.
            return

        self.excellon_exp_group.zeros_radio.set_value(self.excellon_gen_group.excellon_zeros_radio.get_value() + 'Z')
        self.excellon_exp_group.excellon_units_radio.set_value(self.excellon_gen_group.excellon_units_radio.get_value())
        if self.excellon_gen_group.excellon_units_radio.get_value().upper() == 'METRIC':
            self.excellon_exp_group.format_whole_entry.set_value(self.excellon_gen_group.excellon_format_upper_mm_entry.get_value())
            self.excellon_exp_group.format_dec_entry.set_value(self.excellon_gen_group.excellon_format_lower_mm_entry.get_value())
        else:
            self.excellon_exp_group.format_whole_entry.set_value(self.excellon_gen_group.excellon_format_upper_in_entry.get_value())
            self.excellon_exp_group.format_dec_entry.set_value(self.excellon_gen_group.excellon_format_lower_in_entry.get_value())


