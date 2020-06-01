from flatcamGUI.GUIElements import OptionalInputSection
from flatcamGUI.preferences.OptionUI import *
from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI2

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GerberAdvOptPrefGroupUI(OptionsGroupUI2):

    def __init__(self, decimals=4, **kwargs):
        self.decimals = decimals
        super().__init__(**kwargs)
        self.setTitle(str(_("Gerber Adv. Options")))

        self.simplify_cb = self.option_dict()["gerber_simplification"].get_field()
        self.simplification_tol_label = self.option_dict()["gerber_simp_tolerance"].label_widget
        self.simplification_tol_spinner = self.option_dict()["gerber_simp_tolerance"].get_field()
        self.ois_simplif = OptionalInputSection(self.simplify_cb, [self.simplification_tol_label, self.simplification_tol_spinner], logic=True)

    def build_options(self) -> [OptionUI]:
        return [
            HeadingOptionUI(
                label_text="Advanced Options",
                label_tooltip="A list of Gerber advanced parameters.\n"
                              "Those parameters are available only for\n"
                              "Advanced App. Level."
            ),
            CheckboxOptionUI(
                option="gerber_follow",
                label_text='"Follow"',
                label_tooltip="Generate a 'Follow' geometry.\n"
                              "This means that it will cut through\n"
                              "the middle of the trace."
            ),
            CheckboxOptionUI(
                option="gerber_aperture_display",
                label_text="Table Show/Hide",
                label_tooltip="Toggle the display of the Gerber Apertures Table.\n"
                              "Also, on hide, it will delete all mark shapes\n"
                              "that are drawn on canvas."
            ),
            SeparatorOptionUI(),

            RadioSetOptionUI(
                option="gerber_tool_type",
                label_text="Tool Type",
                label_bold=True,
                label_tooltip="Choose which tool to use for Gerber isolation:\n"
                              "'Circular' or 'V-shape'.\n"
                              "When the 'V-shape' is selected then the tool\n"
                              "diameter will depend on the chosen cut depth.",
                choices=[{'label': 'Circular', 'value': 'circular'},
                         {'label': 'V-Shape', 'value': 'v'}]
            ),
            DoubleSpinnerOptionUI(
                option="gerber_vtipdia",
                label_text="V-Tip Dia",
                label_tooltip="The tip diameter for V-Shape Tool",
                min_value=-99.9999, max_value=99.9999, step=0.1, decimals=self.decimals
            ),
            SpinnerOptionUI(
                option="gerber_vtipangle",
                label_text="V-Tip Angle",
                label_tooltip="The tip angle for V-Shape Tool.\n"
                              "In degrees.",
                min_value=1, max_value=180, step=5
            ),
            DoubleSpinnerOptionUI(
                option="gerber_vcutz",
                label_text="Cut Z",
                label_tooltip="Cutting depth (negative)\n"
                              "below the copper surface.",
                min_value=-99.9999, max_value=0.0000, step=0.1, decimals=self.decimals
            ),

            RadioSetOptionUI(
                option="gerber_iso_type",
                label_text="Isolation Type",
                label_tooltip="Choose how the isolation will be executed:\n"
                              "- 'Full' -> complete isolation of polygons\n"
                              "- 'Ext' -> will isolate only on the outside\n"
                              "- 'Int' -> will isolate only on the inside\n"
                              "'Exterior' isolation is almost always possible\n"
                              "(with the right tool) but 'Interior'\n"
                              "isolation can be done only when there is an opening\n"
                              "inside of the polygon (e.g polygon is a 'doughnut' shape).",
                choices=[{'label': _('Full'), 'value': 'full'},
                         {'label': _('Exterior'), 'value': 'ext'},
                         {'label': _('Interior'), 'value': 'int'}]
            ),
            SeparatorOptionUI(),

            RadioSetOptionUI(
                option="gerber_buffering",
                label_text="Buffering",
                label_tooltip="Buffering type:\n"
                              "- None --> best performance, fast file loading but no so good display\n"
                              "- Full --> slow file loading but good visuals. This is the default.\n"
                              "<<WARNING>>: Don't change this unless you know what you are doing !!!",
                choices=[{'label': _('None'), 'value': 'no'},
                         {'label': _('Full'), 'value': 'full'}]
            ),
            CheckboxOptionUI(
                option="gerber_simplification",
                label_text="Simplify",
                label_tooltip="When checked all the Gerber polygons will be\n"
                              "loaded with simplification having a set tolerance.\n"
                              "<<WARNING>>: Don't change this unless you know what you are doing !!!"
            ),
            DoubleSpinnerOptionUI(
                option="gerber_simp_tolerance",
                label_text="Tolerance",
                label_tooltip="Tolerance for polygon simplification.",
                min_value=0.0, max_value=0.01, step=0.0001, decimals=self.decimals+1
            )
        ]