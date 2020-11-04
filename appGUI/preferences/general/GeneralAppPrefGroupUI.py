import sys

from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings

from appGUI.GUIElements import RadioSet, FCSpinner, FCCheckBox, FCComboBox, FCButton, OptionalInputSection, \
    FCDoubleSpinner
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

settings = QSettings("Open Source", "FlatCAM")
if settings.contains("machinist"):
    machinist_setting = settings.value('machinist', type=int)
else:
    machinist_setting = 0


class GeneralAppPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):
        super(GeneralAppPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(_("App Preferences"))
        self.decimals = decimals

        # Create a form layout for the Application general settings
        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)

        # Units for FlatCAM
        self.unitslabel = QtWidgets.QLabel('<span style="color:red;"><b>%s:</b></span>' % _('Units'))
        self.unitslabel.setToolTip(_("The default value for FlatCAM units.\n"
                                     "Whatever is selected here is set every time\n"
                                     "FlatCAM is started."))
        self.units_radio = RadioSet([{'label': _('MM'), 'value': 'MM'},
                                     {'label': _('IN'), 'value': 'IN'}])

        grid0.addWidget(self.unitslabel, 0, 0)
        grid0.addWidget(self.units_radio, 0, 1)

        # Precision Metric
        self.precision_metric_label = QtWidgets.QLabel('%s:' % _('Precision MM'))
        self.precision_metric_label.setToolTip(
            _("The number of decimals used throughout the application\n"
              "when the set units are in METRIC system.\n"
              "Any change here require an application restart.")
        )
        self.precision_metric_entry = FCSpinner()
        self.precision_metric_entry.set_range(2, 16)
        self.precision_metric_entry.setWrapping(True)

        grid0.addWidget(self.precision_metric_label, 1, 0)
        grid0.addWidget(self.precision_metric_entry, 1, 1)

        # Precision Inch
        self.precision_inch_label = QtWidgets.QLabel('%s:' % _('Precision Inch'))
        self.precision_inch_label.setToolTip(
            _("The number of decimals used throughout the application\n"
              "when the set units are in INCH system.\n"
              "Any change here require an application restart.")
        )
        self.precision_inch_entry = FCSpinner()
        self.precision_inch_entry.set_range(2, 16)
        self.precision_inch_entry.setWrapping(True)

        grid0.addWidget(self.precision_inch_label, 2, 0)
        grid0.addWidget(self.precision_inch_entry, 2, 1)

        # Graphic Engine for FlatCAM
        self.ge_label = QtWidgets.QLabel('<b>%s:</b>' % _('Graphic Engine'))
        self.ge_label.setToolTip(_("Choose what graphic engine to use in FlatCAM.\n"
                                   "Legacy(2D) -> reduced functionality, slow performance but enhanced compatibility.\n"
                                   "OpenGL(3D) -> full functionality, high performance\n"
                                   "Some graphic cards are too old and do not work in OpenGL(3D) mode, like:\n"
                                   "Intel HD3000 or older. In this case the plot area will be black therefore\n"
                                   "use the Legacy(2D) mode."))
        self.ge_radio = RadioSet([{'label': _('Legacy(2D)'), 'value': '2D'},
                                  {'label': _('OpenGL(3D)'), 'value': '3D'}],
                                 orientation='vertical')

        grid0.addWidget(self.ge_label, 3, 0)
        grid0.addWidget(self.ge_radio, 3, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 4, 0, 1, 2)

        # Application Level for FlatCAM
        self.app_level_label = QtWidgets.QLabel('<span style="color:red;"><b>%s:</b></span>' % _('APPLICATION LEVEL'))
        self.app_level_label.setToolTip(_("Choose the default level of usage for FlatCAM.\n"
                                          "BASIC level -> reduced functionality, best for beginner's.\n"
                                          "ADVANCED level -> full functionality.\n\n"
                                          "The choice here will influence the parameters in\n"
                                          "the Selected Tab for all kinds of FlatCAM objects."))
        self.app_level_radio = RadioSet([{'label': _('Basic'), 'value': 'b'},
                                         {'label': _('Advanced'), 'value': 'a'}])

        grid0.addWidget(self.app_level_label, 5, 0, 1, 2)
        grid0.addWidget(self.app_level_radio, 6, 0, 1, 2)

        # Portability for FlatCAM
        self.portability_cb = FCCheckBox('%s' % _('Portable app'))
        self.portability_cb.setToolTip(_("Choose if the application should run as portable.\n\n"
                                         "If Checked the application will run portable,\n"
                                         "which means that the preferences files will be saved\n"
                                         "in the application folder, in the lib\\config subfolder."))

        grid0.addWidget(self.portability_cb, 7, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 8, 0, 1, 2)

        # Languages for FlatCAM
        self.languagelabel = QtWidgets.QLabel('<b>%s</b>' % _('Languages'))
        self.languagelabel.setToolTip(_("Set the language used throughout FlatCAM."))
        self.language_cb = FCComboBox()

        grid0.addWidget(self.languagelabel, 9, 0, 1, 2)
        grid0.addWidget(self.language_cb, 10, 0, 1, 2)

        self.language_apply_btn = FCButton(_("Apply Language"))
        self.language_apply_btn.setToolTip(_("Set the language used throughout FlatCAM.\n"
                                             "The app will restart after click."))

        grid0.addWidget(self.language_apply_btn, 15, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 16, 0, 1, 2)

        # -----------------------------------------------------------
        # ----------- APPLICATION STARTUP SETTINGS ------------------
        # -----------------------------------------------------------

        self.startup_label = QtWidgets.QLabel('<b>%s</b>' % _('Startup Settings'))
        grid0.addWidget(self.startup_label, 17, 0, 1, 2)

        # Splash Screen
        self.splash_cb = FCCheckBox('%s' % _('Splash Screen'))
        self.splash_cb.setToolTip(
            _("Enable display of the splash screen at application startup.")
        )

        qsettings = QSettings("Open Source", "FlatCAM")
        if qsettings.value("splash_screen"):
            self.splash_cb.set_value(True)
        else:
            self.splash_cb.set_value(False)

        grid0.addWidget(self.splash_cb, 18, 0, 1, 2)

        # Sys Tray Icon
        self.systray_cb = FCCheckBox('%s' % _('Sys Tray Icon'))
        self.systray_cb.setToolTip(
            _("Enable display of FlatCAM icon in Sys Tray.")
        )
        grid0.addWidget(self.systray_cb, 19, 0, 1, 2)

        # Shell StartUp CB
        self.shell_startup_cb = FCCheckBox(label='%s' % _('Show Shell'))
        self.shell_startup_cb.setToolTip(
            _("Check this box if you want the shell to\n"
              "start automatically at startup.")
        )

        grid0.addWidget(self.shell_startup_cb, 20, 0, 1, 2)

        # Project at StartUp CB
        self.project_startup_cb = FCCheckBox(label='%s' % _('Show Project'))
        self.project_startup_cb.setToolTip(
            _("Check this box if you want the project/selected/tool tab area to\n"
              "to be shown automatically at startup.")
        )
        grid0.addWidget(self.project_startup_cb, 21, 0, 1, 2)

        # Version Check CB
        self.version_check_cb = FCCheckBox(label='%s' % _('Version Check'))
        self.version_check_cb.setToolTip(
            _("Check this box if you want to check\n"
              "for a new version automatically at startup.")
        )

        grid0.addWidget(self.version_check_cb, 22, 0, 1, 2)

        # Send Stats CB
        self.send_stats_cb = FCCheckBox(label='%s' % _('Send Statistics'))
        self.send_stats_cb.setToolTip(
            _("Check this box if you agree to send anonymous\n"
              "stats automatically at startup, to help improve FlatCAM.")
        )

        grid0.addWidget(self.send_stats_cb, 23, 0, 1, 2)

        self.ois_version_check = OptionalInputSection(self.version_check_cb, [self.send_stats_cb])

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 24, 0, 1, 2)

        # Worker Numbers
        self.worker_number_label = QtWidgets.QLabel('%s:' % _('Workers number'))
        self.worker_number_label.setToolTip(
            _("The number of Qthreads made available to the App.\n"
              "A bigger number may finish the jobs more quickly but\n"
              "depending on your computer speed, may make the App\n"
              "unresponsive. Can have a value between 2 and 16.\n"
              "Default value is 2.\n"
              "After change, it will be applied at next App start.")
        )
        self.worker_number_sb = FCSpinner()
        self.worker_number_sb.set_range(2, 16)

        grid0.addWidget(self.worker_number_label, 25, 0)
        grid0.addWidget(self.worker_number_sb, 25, 1)

        # Geometric tolerance
        tol_label = QtWidgets.QLabel('%s:' % _("Geo Tolerance"))
        tol_label.setToolTip(_(
            "This value can counter the effect of the Circle Steps\n"
            "parameter. Default value is 0.005.\n"
            "A lower value will increase the detail both in image\n"
            "and in Gcode for the circles, with a higher cost in\n"
            "performance. Higher value will provide more\n"
            "performance at the expense of level of detail."
        ))
        self.tol_entry = FCDoubleSpinner()
        self.tol_entry.setSingleStep(0.001)
        self.tol_entry.set_precision(6)

        grid0.addWidget(tol_label, 26, 0)
        grid0.addWidget(self.tol_entry, 26, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 27, 0, 1, 2)

        # Save Settings
        self.save_label = QtWidgets.QLabel('<b>%s</b>' % _("Save Settings"))
        grid0.addWidget(self.save_label, 28, 0, 1, 2)

        # Save compressed project CB
        self.save_type_cb = FCCheckBox(_('Save Compressed Project'))
        self.save_type_cb.setToolTip(
            _("Whether to save a compressed or uncompressed project.\n"
              "When checked it will save a compressed FlatCAM project.")
        )

        grid0.addWidget(self.save_type_cb, 29, 0, 1, 2)

        # Project LZMA Comppression Level
        self.compress_spinner = FCSpinner()
        self.compress_spinner.set_range(0, 9)
        self.compress_label = QtWidgets.QLabel('%s:' % _('Compression'))
        self.compress_label.setToolTip(
            _("The level of compression used when saving\n"
              "a FlatCAM project. Higher value means better compression\n"
              "but require more RAM usage and more processing time.")
        )

        grid0.addWidget(self.compress_label, 30, 0)
        grid0.addWidget(self.compress_spinner, 30, 1)

        self.proj_ois = OptionalInputSection(self.save_type_cb, [self.compress_label, self.compress_spinner], True)

        # Auto save CB
        self.autosave_cb = FCCheckBox(_('Enable Auto Save'))
        self.autosave_cb.setToolTip(
            _("Check to enable the autosave feature.\n"
              "When enabled, the application will try to save a project\n"
              "at the set interval.")
        )

        grid0.addWidget(self.autosave_cb, 31, 0, 1, 2)

        # Auto Save Timeout Interval
        self.autosave_entry = FCSpinner()
        self.autosave_entry.set_range(0, 9999999)
        self.autosave_label = QtWidgets.QLabel('%s:' % _('Interval'))
        self.autosave_label.setToolTip(
            _("Time interval for autosaving. In milliseconds.\n"
              "The application will try to save periodically but only\n"
              "if the project was saved manually at least once.\n"
              "While active, some operations may block this feature.")
        )

        grid0.addWidget(self.autosave_label, 32, 0)
        grid0.addWidget(self.autosave_entry, 32, 1)

        # self.as_ois = OptionalInputSection(self.autosave_cb, [self.autosave_label, self.autosave_entry], True)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 33, 0, 1, 2)

        self.pdf_param_label = QtWidgets.QLabel('<B>%s:</b>' % _("Text to PDF parameters"))
        self.pdf_param_label.setToolTip(
            _("Used when saving text in Code Editor or in FlatCAM Document objects.")
        )
        grid0.addWidget(self.pdf_param_label, 34, 0, 1, 2)

        # Top Margin value
        self.tmargin_entry = FCDoubleSpinner()
        self.tmargin_entry.set_precision(self.decimals)
        self.tmargin_entry.set_range(0.0000, 10000.0000)

        self.tmargin_label = QtWidgets.QLabel('%s:' % _("Top Margin"))
        self.tmargin_label.setToolTip(
            _("Distance between text body and the top of the PDF file.")
        )

        grid0.addWidget(self.tmargin_label, 35, 0)
        grid0.addWidget(self.tmargin_entry, 35, 1)

        # Bottom Margin value
        self.bmargin_entry = FCDoubleSpinner()
        self.bmargin_entry.set_precision(self.decimals)
        self.bmargin_entry.set_range(0.0000, 10000.0000)

        self.bmargin_label = QtWidgets.QLabel('%s:' % _("Bottom Margin"))
        self.bmargin_label.setToolTip(
            _("Distance between text body and the bottom of the PDF file.")
        )

        grid0.addWidget(self.bmargin_label, 36, 0)
        grid0.addWidget(self.bmargin_entry, 36, 1)

        # Left Margin value
        self.lmargin_entry = FCDoubleSpinner()
        self.lmargin_entry.set_precision(self.decimals)
        self.lmargin_entry.set_range(0.0000, 10000.0000)

        self.lmargin_label = QtWidgets.QLabel('%s:' % _("Left Margin"))
        self.lmargin_label.setToolTip(
            _("Distance between text body and the left of the PDF file.")
        )

        grid0.addWidget(self.lmargin_label, 37, 0)
        grid0.addWidget(self.lmargin_entry, 37, 1)

        # Right Margin value
        self.rmargin_entry = FCDoubleSpinner()
        self.rmargin_entry.set_precision(self.decimals)
        self.rmargin_entry.set_range(0.0000, 10000.0000)

        self.rmargin_label = QtWidgets.QLabel('%s:' % _("Right Margin"))
        self.rmargin_label.setToolTip(
            _("Distance between text body and the right of the PDF file.")
        )

        grid0.addWidget(self.rmargin_label, 38, 0)
        grid0.addWidget(self.rmargin_entry, 38, 1)

        self.layout.addStretch()

        if sys.platform != 'win32':
            self.portability_cb.hide()

        # splash screen button signal
        self.splash_cb.stateChanged.connect(self.on_splash_changed)

        # Monitor the checkbox from the Application Defaults Tab and show the TCL shell or not depending on it's value
        self.shell_startup_cb.clicked.connect(self.on_toggle_shell_from_settings)

        self.language_apply_btn.clicked.connect(lambda: fcTranslate.on_language_apply_click(app=self.app, restart=True))

    def on_toggle_shell_from_settings(self, state):
        """
        Toggle shell ui: if is visible close it, if it is closed then open it

        :return: None
        """

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
