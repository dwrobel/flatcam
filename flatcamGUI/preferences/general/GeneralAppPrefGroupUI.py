import sys
from PyQt5.QtCore import QSettings
from flatcamGUI.GUIElements import OptionalInputSection
from flatcamGUI.preferences.OptionUI import *
from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI2

import gettext
import FlatCAMTranslation as fcTranslate
import builtins
fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GeneralAppPrefGroupUI(OptionsGroupUI2):
    def __init__(self, decimals=4, **kwargs):
        self.decimals = decimals
        super().__init__(**kwargs)
        self.setTitle(str(_("App Preferences")))

        if sys.platform != 'win32':
            self.option_dict()["global_portable"].get_field().hide()
        self.option_dict()["splash_screen"].get_field().stateChanged.connect(self.on_splash_changed)
        self.option_dict()["global_shell_at_startup"].get_field().clicked.connect(self.on_toggle_shell_from_settings)
        self.option_dict()["__apply_language_button"].get_field().clicked.connect(lambda: fcTranslate.on_language_apply_click(app=self.app, restart=True))

        qsettings = QSettings("Open Source", "FlatCAM")
        if qsettings.value("splash_screen"):
            self.option_dict()["splash_screen"].get_field().set_value(True)
        else:
            self.option_dict()["splash_screen"].get_field().set_value(False)

        self.version_check_field = self.option_dict()["global_version_check"].get_field()
        self.send_stats_field = self.option_dict()["global_send_stats"].get_field()
        self.ois_version_check = OptionalInputSection(self.version_check_field, [self.send_stats_field])

        self.save_compressed_field = self.option_dict()["global_save_compressed"].get_field()
        self.compression_label = self.option_dict()["global_compression_level"].label_widget
        self.compression_field = self.option_dict()["global_compression_level"].get_field()
        self.proj_ois = OptionalInputSection(self.save_compressed_field, [self.compression_label, self.compression_field], True)
        # self.as_ois = OptionalInputSection(self.autosave_cb, [self.autosave_label, self.autosave_entry], True)

    def build_options(self) -> [OptionUI]:
        return [
            RadioSetOptionUI(
                option="units",
                label_text="Units",
                label_tooltip="The default value for FlatCAM units.\n"
                              "Whatever is selected here is set every time\n"
                              "FlatCAM is started.",
                label_bold=True,
                label_color="red",
                choices=[{'label': _('MM'), 'value': 'MM'},
                         {'label': _('IN'), 'value': 'IN'}]
            ),
            SpinnerOptionUI(
                option="decimals_metric",
                label_text="Precision MM",
                label_tooltip="The number of decimals used throughout the application\n"
                              "when the set units are in METRIC system.\n"
                              "Any change here require an application restart.",
                min_value=2, max_value=16, step=1
            ),
            SpinnerOptionUI(
                option="decimals_metric",
                label_text="Precision INCH",
                label_tooltip="The number of decimals used throughout the application\n"
                              "when the set units are in INCH system.\n"
                              "Any change here require an application restart.",
                min_value=2, max_value=16, step=1
            ),
            RadioSetOptionUI(
                option="global_graphic_engine",
                label_text='Graphic Engine',
                label_tooltip="Choose what graphic engine to use in FlatCAM.\n"
                              "Legacy(2D) -> reduced functionality, slow performance but enhanced compatibility.\n"
                              "OpenGL(3D) -> full functionality, high performance\n"
                              "Some graphic cards are too old and do not work in OpenGL(3D) mode, like:\n"
                              "Intel HD3000 or older. In this case the plot area will be black therefore\n"
                              "use the Legacy(2D) mode.",
                label_bold=True,
                choices=[{'label': _('Legacy(2D)'), 'value': '2D'},
                         {'label': _('OpenGL(3D)'), 'value': '3D'}],
                orientation="vertical"
            ),
            SeparatorOptionUI(),

            RadioSetOptionUI(
                option="global_app_level",
                label_text="APP. LEVEL",
                label_tooltip="Choose the default level of usage for FlatCAM.\n"
                              "BASIC level -> reduced functionality, best for beginner's.\n"
                              "ADVANCED level -> full functionality.\n\n"
                              "The choice here will influence the parameters in\n"
                              "the Selected Tab for all kinds of FlatCAM objects.",
                label_bold=True,
                label_color="red",
                choices=[{'label': _('Basic'),    'value': 'b'},
                         {'label': _('Advanced'), 'value': 'a'}]
            ),
            CheckboxOptionUI(
                option="global_portable",
                label_text="Portable app",
                label_tooltip="Choose if the application should run as portable.\n\n"
                              "If Checked the application will run portable,\n"
                              "which means that the preferences files will be saved\n"
                              "in the application folder, in the lib\\config subfolder."
            ),
            SeparatorOptionUI(),

            HeadingOptionUI(label_text="Languages", label_tooltip="Set the language used throughout FlatCAM."),
            ComboboxOptionUI(
                option="global_language",
                label_text="Language",
                label_tooltip="Set the language used throughout FlatCAM.",
                choices=[]  # FIXME: choices should be added here instead of in App
            ),
            FullWidthButtonOptionUI(
                option="__apply_language_button",
                label_text="Apply Language",
                label_tooltip="Set the language used throughout FlatCAM.\n"
                              "The app will restart after click."
            ),
            SeparatorOptionUI(),

            HeadingOptionUI("Startup Settings", label_tooltip=None),
            CheckboxOptionUI(
                option="splash_screen",
                label_text="Splash Screen",
                label_tooltip="Enable display of the splash screen at application startup."
            ),
            CheckboxOptionUI(
                option="global_systray_icon",
                label_text="Sys Tray Icon",
                label_tooltip="Enable display of FlatCAM icon in Sys Tray."
            ),
            CheckboxOptionUI(
                option="global_shell_at_startup",
                label_text="Show Shell",
                label_tooltip="Check this box if you want the shell to\n"
                              "start automatically at startup."
            ),
            CheckboxOptionUI(
                option="global_project_at_startup",
                label_text="Show Project",
                label_tooltip="Check this box if you want the project/selected/tool tab area to\n"
                              "to be shown automatically at startup."
            ),
            CheckboxOptionUI(
                option="global_version_check",
                label_text="Version Check",
                label_tooltip="Check this box if you want to check\n"
                              "for a new version automatically at startup."
            ),
            CheckboxOptionUI(
                option="global_send_stats",
                label_text="Send Statistics",
                label_tooltip="Check this box if you agree to send anonymous\n"
                              "stats automatically at startup, to help improve FlatCAM."
            ),
            SeparatorOptionUI(),

            SpinnerOptionUI(
                option="global_worker_number",
                label_text="Workers number",
                label_tooltip="The number of Qthreads made available to the App.\n"
                              "A bigger number may finish the jobs more quickly but\n"
                              "depending on your computer speed, may make the App\n"
                              "unresponsive. Can have a value between 2 and 16.\n"
                              "Default value is 2.\n"
                              "After change, it will be applied at next App start.",
                min_value=2, max_value=16, step=1
            ),
            DoubleSpinnerOptionUI(
                option="global_tolerance",
                label_text="Geo Tolerance",
                label_tooltip="This value can counter the effect of the Circle Steps\n"
                              "parameter. Default value is 0.005.\n"
                              "A lower value will increase the detail both in image\n"
                              "and in Gcode for the circles, with a higher cost in\n"
                              "performance. Higher value will provide more\n"
                              "performance at the expense of level of detail.",
                min_value=0.0, max_value=100.0, step=0.001, decimals=6
            ),
            SeparatorOptionUI(),

            HeadingOptionUI(label_text="Save Settings"),
            CheckboxOptionUI(
                option="global_save_compressed",
                label_text="Save Compressed Project",
                label_tooltip="Whether to save a compressed or uncompressed project.\n"
                              "When checked it will save a compressed FlatCAM project."
            ),
            SpinnerOptionUI(
                option="global_compression_level",
                label_text="Compression",
                label_tooltip="The level of compression used when saving\n"
                              "a FlatCAM project. Higher value means better compression\n"
                              "but require more RAM usage and more processing time.",
                min_value=0, max_value=9, step=1
            ),
            CheckboxOptionUI(
                option="global_autosave",
                label_text="Enable Auto Save",
                label_tooltip="Check to enable the autosave feature.\n"
                              "When enabled, the application will try to save a project\n"
                              "at the set interval."
            ),
            SpinnerOptionUI(
                option="global_autosave_timeout",
                label_text="Interval",
                label_tooltip="Time interval for autosaving. In milliseconds.\n"
                              "The application will try to save periodically but only\n"
                              "if the project was saved manually at least once.\n"
                              "While active, some operations may block this feature.",
                min_value=500, max_value=9999999, step=60000
            ),
            SeparatorOptionUI(),

            HeadingOptionUI(
                label_text="Text to PDF parameters",
                label_tooltip="Used when saving text in Code Editor or in FlatCAM Document objects."
            ),
            DoubleSpinnerOptionUI(
                option="global_tpdf_tmargin",
                label_text="Top Margin",
                label_tooltip="Distance between text body and the top of the PDF file.",
                min_value=0.0, max_value=9999.9999, step=1, decimals=2
            ),
            DoubleSpinnerOptionUI(
                option="global_tpdf_bmargin",
                label_text="Bottom Margin",
                label_tooltip="Distance between text body and the bottom of the PDF file.",
                min_value=0.0, max_value=9999.9999, step=1, decimals=2
            ),
            DoubleSpinnerOptionUI(
                option="global_tpdf_lmargin",
                label_text="Left Margin",
                label_tooltip="Distance between text body and the left of the PDF file.",
                min_value=0.0, max_value=9999.9999, step=1, decimals=2
            ),
            DoubleSpinnerOptionUI(
                option="global_tpdf_rmargin",
                label_text="Right Margin",
                label_tooltip="Distance between text body and the right of the PDF file.",
                min_value=0.0, max_value=9999.9999, step=1, decimals=2
            )
        ]

    def on_toggle_shell_from_settings(self, state):
        """
        Toggle shell: if is visible close it, if it is closed then open it
        :return: None
        """

        self.app.defaults.report_usage("on_toggle_shell_from_settings()")

        if state is True:
            if not self.app.ui.shell_dock.isVisible():
                self.app.ui.shell_dock.show()
        else:
            if self.app.ui.shell_dock.isVisible():
                self.app.ui.shell_dock.hide()

    @staticmethod
    def on_splash_changed(state):
        qsettings = QSettings("Open Source", "FlatCAM")
        qsettings.setValue('splash_screen', 1) if state else qsettings.setValue('splash_screen', 0)

        # This will write the setting to the platform specific storage.
        del qsettings