import platform
from flatcamGUI.preferences.OptionUI import *
from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI2

import gettext
import FlatCAMTranslation as fcTranslate
import builtins
fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ExcellonGenPrefGroupUI(OptionsGroupUI2):

    def __init__(self, decimals=4, **kwargs):
        self.decimals = decimals
        super().__init__(**kwargs)
        self.setTitle(str(_("Excellon General")))

        # disable the Excellon path optimizations made with Google OR-Tools if the app is run on a 32bit platform
        if platform.architecture()[0] != '64bit':
            self.option_dict()["excellon_optimization_type"].get_field().set_value('T')
            self.option_dict()["excellon_optimization_type"].get_field().setDisabled(True)
            self.option_dict()["excellon_optimization_type"].label_widget.setDisabled(True)

        # Enable/disable the duration box according to type selected
        self.option_dict()["excellon_optimization_type"].get_field().activated_custom.connect(self.optimization_selection)
        self.optimization_selection()

        # Load the defaults values into the Excellon Format and Excellon Zeros fields
        self.option_dict()["__excellon_restore_defaults"].get_field().clicked.connect(self.on_defaults_button)


    def build_options(self) -> [OptionUI]:
        return [
            HeadingOptionUI(label_text="Plot Options"),
            CheckboxOptionUI(
                option="excellon_plot",
                label_text="Plot",
                label_tooltip="Plot (show) this object."
            ),
            CheckboxOptionUI(
                option="excellon_solid",
                label_text="Solid",
                label_tooltip="Plot as solid circles."
            ),
            SeparatorOptionUI(),

            HeadingOptionUI(
                label_text="Excellon Format",
                label_tooltip="The NC drill files, usually named Excellon files\n"
                              "are files that can be found in different formats.\n"
                              "Here we set the format used when the provided\n"
                              "coordinates are not using period.\n"
                              "\n"
                              "Possible presets:\n"
                              "\n"
                              "PROTEUS 3:3 MM LZ\n"
                              "DipTrace 5:2 MM TZ\n"
                              "DipTrace 4:3 MM LZ\n"
                              "\n"
                              "EAGLE 3:3 MM TZ\n"
                              "EAGLE 4:3 MM TZ\n"
                              "EAGLE 2:5 INCH TZ\n"
                              "EAGLE 3:5 INCH TZ\n"
                              "\n"
                              "ALTIUM 2:4 INCH LZ\n"
                              "Sprint Layout 2:4 INCH LZ"
                              "\n"
                              "KiCAD 3:5 INCH TZ"
            ),
            SpinnerOptionUI(
                option="excellon_format_upper_in",
                label_text="INCH int",
                label_tooltip="This number signifies the number of digits in\nthe whole part of Excellon coordinates.",
                min_value=0, max_value=9, step=1
            ),
            SpinnerOptionUI(
                option="excellon_format_lower_in",
                label_text="INCH decimals",
                label_tooltip="This number signifies the number of digits in\nthe decimal part of Excellon coordinates.",
                min_value=0, max_value=9, step=1
            ),
            SpinnerOptionUI(
                option="excellon_format_upper_mm",
                label_text="METRIC int",
                label_tooltip="This number signifies the number of digits in\nthe whole part of Excellon coordinates.",
                min_value=0, max_value=9, step=1
            ),
            SpinnerOptionUI(
                option="excellon_format_lower_mm",
                label_text="METRIC decimals",
                label_tooltip="This number signifies the number of digits in\nthe decimal part of Excellon coordinates.",
                min_value=0, max_value=9, step=1
            ),
            RadioSetOptionUI(
                option="excellon_zeros",
                label_text="Zeros",
                label_tooltip="This sets the type of Excellon zeros.\n"
                              "If LZ then Leading Zeros are kept and\n"
                              "Trailing Zeros are removed.\n"
                              "If TZ is checked then Trailing Zeros are kept\n"
                              "and Leading Zeros are removed.\n\n"
                              "This is used when there is no information\n"
                              "stored in the Excellon file.",
                choices=[
                    {'label': _('LZ'), 'value': 'L'},
                    {'label': _('TZ'), 'value': 'T'}
                ]
            ),
            RadioSetOptionUI(
                option="excellon_units",
                label_text="Units",
                label_tooltip="This sets the default units of Excellon files.\n"
                              "If it is not detected in the parsed file the value here\n"
                              "will be used."
                              "Some Excellon files don't have an header\n"
                              "therefore this parameter will be used.",
                choices=[
                    {'label': _('INCH'), 'value': 'INCH'},
                    {'label': _('MM'), 'value': 'METRIC'}
                ]
            ),
            CheckboxOptionUI(
                option="excellon_update",
                label_text="Update Export settings",
                label_tooltip="If checked, the Excellon Export settings will be updated with the ones above."
            ),
            FullWidthButtonOptionUI(
                option="__excellon_restore_defaults",
                label_text="Restore Defaults",
                label_tooltip=None
            ),
            SeparatorOptionUI(),

            HeadingOptionUI(label_text="Excellon Optimization"),
            RadioSetOptionUI(
                option="excellon_optimization_type",
                label_text="Algorithm",
                label_tooltip="This sets the optimization type for the Excellon drill path.\n"
                              "If <<MetaHeuristic>> is checked then Google OR-Tools algorithm with\n"
                              "MetaHeuristic Guided Local Path is used. Default search time is 3sec.\n"
                              "If <<Basic>> is checked then Google OR-Tools Basic algorithm is used.\n"
                              "If <<TSA>> is checked then Travelling Salesman algorithm is used for\n"
                              "drill path optimization.\n"
                              "\n"
                              "If this control is disabled, then FlatCAM works in 32bit mode and it uses\n"
                              "Travelling Salesman algorithm for path optimization.",
                choices=[
                    {'label': _('MetaHeuristic'), 'value': 'M'},
                    {'label': _('Basic'),         'value': 'B'},
                    {'label': _('TSA'),           'value': 'T'}
                ],
                orientation="vertical"
            ),
            SpinnerOptionUI(
                option="excellon_search_time",
                label_text="Duration",
                label_tooltip="When OR-Tools Metaheuristic (MH) is enabled there is a\n"
                              "maximum threshold for how much time is spent doing the\n"
                              "path optimization. This max duration is set here.\n"
                              "In seconds.",
                min_value=1, max_value=999, step=1
            ),
            SeparatorOptionUI(),

            HeadingOptionUI(label_text="Excellon Object Color"),
            ColorOptionUI(
                option="excellon_plot_line",
                label_text="Outline",
                label_tooltip="Set the line color for plotted objects.",
            ),
            ColorOptionUI(
                option="excellon_plot_fill",
                label_text="Fill",
                label_tooltip="Set the fill color for plotted objects.\n"
                              "First 6 digits are the color and the last 2\n"
                              "digits are for alpha (transparency) level."
            ),
            ColorAlphaSliderOptionUI(
                applies_to=["excellon_plot_line", "excellon_plot_fill"],
                group=self,
                label_text="Alpha",
                label_tooltip="Set the transparency for plotted objects."
            )
        ]

    def optimization_selection(self):
        disable_time = (self.option_dict()["excellon_optimization_type"].get_field().get_value() != 'M')
        self.option_dict()["excellon_search_time"].label_widget.setDisabled(disable_time)
        self.option_dict()["excellon_search_time"].get_field().setDisabled(disable_time)

    def on_defaults_button(self):
        self.option_dict()["excellon_format_lower_in"].get_field().set_value('4')
        self.option_dict()["excellon_format_upper_in"].get_field().set_value('2')
        self.option_dict()["excellon_format_lower_mm"].get_field().set_value('3')
        self.option_dict()["excellon_format_upper_mm"].get_field().set_value('3')
        self.option_dict()["excellon_zeros"].get_field().set_value('L')
        self.option_dict()["excellon_units"].get_field().set_value('INCH')
