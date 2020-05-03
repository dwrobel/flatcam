from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QSettings, Qt
from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI2

import gettext
import FlatCAMTranslation as fcTranslate
import builtins
fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

from flatcamGUI.preferences.OptionUI import OptionUI, CheckboxOptionUI, RadioSetOptionUI, \
    SeparatorOptionUI, HeadingOptionUI, ComboboxOptionUI, ColorOptionUI, FullWidthButtonOptionUI, \
    SliderWithSpinnerOptionUI


class GeneralGUIPrefGroupUI(OptionsGroupUI2):

    def __init__(self, decimals=4, **kwargs):
        self.decimals = decimals
        super().__init__(**kwargs)
        self.setTitle(str(_("GUI Preferences")))

        self.layout_field = self.option_dict()["layout"].get_field()
        self.layout_field.activated.connect(self.on_layout)

        self.theme_field = self.option_dict()["global_theme"].get_field()
        self.theme_apply_button = self.option_dict()["__button_apply_theme"].get_field()
        self.theme_apply_button.clicked.connect(self.on_theme_change)

        self.style_field = self.option_dict()["style"].get_field()
        current_style_index = self.style_field.findText(QtWidgets.qApp.style().objectName(), QtCore.Qt.MatchFixedString)
        self.style_field.setCurrentIndex(current_style_index)
        self.style_field.activated[str].connect(self.handle_style)

        self.hdpi_field = self.option_dict()["hdpi"].get_field()
        qsettings = QSettings("Open Source", "FlatCAM")
        if qsettings.contains("hdpi"):
            self.hdpi_field.set_value(qsettings.value('hdpi', type=int))
        else:
            self.hdpi_field.set_value(False)
        self.hdpi_field.stateChanged.connect(self.handle_hdpi)

        self.sel_line_field = self.option_dict()["global_sel_line"].get_field()
        self.sel_fill_field = self.option_dict()["global_sel_fill"].get_field()
        self.sel_alpha_field = self.option_dict()["_global_sel_alpha"].get_field()
        self.sel_alpha_field.spinner.valueChanged.connect(self.on_sel_alpha_change)

        self.alt_sel_line_field = self.option_dict()["global_alt_sel_line"].get_field()
        self.alt_sel_fill_field = self.option_dict()["global_alt_sel_fill"].get_field()
        self.alt_sel_alpha_field = self.option_dict()["_global_alt_sel_alpha"].get_field()
        self.alt_sel_alpha_field.spinner.valueChanged.connect(self.on_alt_sel_alpha_change)

    def build_options(self) -> [OptionUI]:
        return [
            RadioSetOptionUI(
                option="global_theme",
                label_text="Theme",
                label_tooltip="Select a theme for FlatCAM.\nIt will theme the plot area.",
                choices=[
                    {"label": _("Light"), "value": "white"},
                    {"label": _("Dark"), "value": "black"}
                ],
                orientation='vertical'
            ),
            CheckboxOptionUI(
                option="global_gray_icons",
                label_text="Use Gray Icons",
                label_tooltip="Check this box to use a set of icons with\na lighter (gray) color. To be used when a\nfull dark theme is applied."
            ),
            FullWidthButtonOptionUI(
                option="__button_apply_theme",
                label_text="Apply Theme",
                label_tooltip="Select a theme for FlatCAM.\n"
                              "It will theme the plot area.\n"
                              "The application will restart after change."
            ),
            SeparatorOptionUI(),

            ComboboxOptionUI(
                option="layout",
                label_text="Layout",
                label_tooltip="Select an layout for FlatCAM.\nIt is applied immediately.",
                choices=[
                    "standard",
                    "compact",
                    "minimal"
                ]
            ),
            ComboboxOptionUI(
                option="style",
                label_text="Style",
                label_tooltip="Select an style for FlatCAM.\nIt will be applied at the next app start.",
                choices=QtWidgets.QStyleFactory.keys()
            ),
            CheckboxOptionUI(
                option="hdpi",
                label_text='Activate HDPI Support',
                label_tooltip="Enable High DPI support for FlatCAM.\nIt will be applied at the next app start.",
            ),
            CheckboxOptionUI(
                option="global_hover",
                label_text='Display Hover Shape',
                label_tooltip="Enable display of a hover shape for FlatCAM objects.\nIt is displayed whenever the mouse cursor is hovering\nover any kind of not-selected object.",
            ),
            CheckboxOptionUI(
                option="global_selection_shape",
                label_text='Display Selection Shape',
                label_tooltip="Enable the display of a selection shape for FlatCAM objects.\n"
                  "It is displayed whenever the mouse selects an object\n"
                  "either by clicking or dragging mouse from left to right or\n"
                  "right to left."
            ),
            SeparatorOptionUI(),

            HeadingOptionUI(label_text="Left-Right Selection Color", label_tooltip=None),
            ColorOptionUI(
                option="global_sel_line",
                label_text="Outline",
                label_tooltip="Set the line color for the 'left to right' selection box."
            ),
            ColorOptionUI(
                option="global_sel_fill",
                label_text="Fill",
                label_tooltip="Set the fill color for the selection box\n"
                              "in case that the selection is done from left to right.\n"
                              "First 6 digits are the color and the last 2\n"
                              "digits are for alpha (transparency) level."
            ),
            SliderWithSpinnerOptionUI(
                option="_global_sel_alpha",
                label_text="Alpha",
                label_tooltip="Set the fill transparency for the 'left to right' selection box.",
                min_value=0, max_value=255, step=1
            ),
            SeparatorOptionUI(),

            HeadingOptionUI(label_text="Right-Left Selection Color", label_tooltip=None),
            ColorOptionUI(
                option="global_alt_sel_line",
                label_text="Outline",
                label_tooltip="Set the line color for the 'right to left' selection box."
            ),
            ColorOptionUI(
                option="global_alt_sel_fill",
                label_text="Fill",
                label_tooltip="Set the fill color for the selection box\n"
                              "in case that the selection is done from right to left.\n"
                              "First 6 digits are the color and the last 2\n"
                              "digits are for alpha (transparency) level."
            ),
            SliderWithSpinnerOptionUI(
                option="_global_alt_sel_alpha",
                label_text="Alpha",
                label_tooltip="Set the fill transparency for the 'right to left' selection box.",
                min_value=0, max_value=255, step=1
            ),
            SeparatorOptionUI(),

            HeadingOptionUI(label_text='Editor Color', label_tooltip=None),
            ColorOptionUI(
                option="global_draw_color",
                label_text="Drawing",
                label_tooltip="Set the color for the shape."
            ),
            ColorOptionUI(
                option="global_sel_draw_color",
                label_text="Selection",
                label_tooltip="Set the color of the shape when selected."
            ),
            SeparatorOptionUI(),

            HeadingOptionUI(label_text='Project Items Color', label_tooltip=None),
            ColorOptionUI(
                option="global_proj_item_color",
                label_text="Enabled",
                label_tooltip="Set the color of the items in Project Tab Tree."
            ),
            ColorOptionUI(
                option="global_proj_item_dis_color",
                label_text="Disabled",
                label_tooltip="Set the color of the items in Project Tab Tree,\n"
                              "for the case when the items are disabled."
            ),
            CheckboxOptionUI(
                option="global_project_autohide",
                label_text="Project AutoHide",
                label_tooltip="Check this box if you want the project/selected/tool tab area to\n"
                              "hide automatically when there are no objects loaded and\n"
                              "to show whenever a new object is created."
            ),
        ]

    def on_sel_alpha_change(self):
        alpha = self.sel_alpha_field.get_value()
        fill = self._modify_color_alpha(color=self.sel_fill_field.get_value(), alpha=alpha)
        self.sel_fill_field.set_value(fill)
        line = self._modify_color_alpha(color=self.sel_line_field.get_value(), alpha=alpha)
        self.sel_line_field.set_value(line)

    def on_alt_sel_alpha_change(self):
        alpha = self.alt_sel_alpha_field.get_value()
        fill = self._modify_color_alpha(color=self.alt_sel_fill_field.get_value(), alpha=alpha)
        self.alt_sel_fill_field.set_value(fill)
        line = self._modify_color_alpha(color=self.alt_sel_line_field.get_value(), alpha=alpha)
        self.alt_sel_line_field.set_value(line)



    def _modify_color_alpha(self, color: str, alpha: int):
        color_without_alpha = color[:7]
        if alpha > 255:
            return color_without_alpha + "FF"
        elif alpha < 0:
            return color_without_alpha + "00"
        else:
            hexalpha = hex(alpha)[2:]
            if len(hexalpha) == 1:
                hexalpha = "0" + hexalpha
            return color_without_alpha + hexalpha


    def on_theme_change(self):
        # FIXME: this should be moved out to a view model
        val = self.theme_field.get_value()
        qsettings = QSettings("Open Source", "FlatCAM")
        qsettings.setValue("theme", val)

        # This will write the setting to the platform specific storage.
        del qsettings

        self.app.on_app_restart()

    def on_layout(self, index=None, lay=None):
        # FIXME: this should be moved out somewhere else
        """
        Set the toolbars layout (location)

        :param index:
        :param lay:     Type of layout to be set on the toolbard
        :return:        None
        """

        self.app.defaults.report_usage("on_layout()")
        if lay:
            current_layout = lay
        else:
            current_layout = self.layout_field.get_value()

        lay_settings = QSettings("Open Source", "FlatCAM")
        lay_settings.setValue('layout', current_layout)

        # This will write the setting to the platform specific storage.
        del lay_settings

        # first remove the toolbars:
        try:
            self.app.ui.removeToolBar(self.app.ui.toolbarfile)
            self.app.ui.removeToolBar(self.app.ui.toolbargeo)
            self.app.ui.removeToolBar(self.app.ui.toolbarview)
            self.app.ui.removeToolBar(self.app.ui.toolbarshell)
            self.app.ui.removeToolBar(self.app.ui.toolbartools)
            self.app.ui.removeToolBar(self.app.ui.exc_edit_toolbar)
            self.app.ui.removeToolBar(self.app.ui.geo_edit_toolbar)
            self.app.ui.removeToolBar(self.app.ui.grb_edit_toolbar)
            self.app.ui.removeToolBar(self.app.ui.snap_toolbar)
            self.app.ui.removeToolBar(self.app.ui.toolbarshell)
        except Exception:
            pass

        if current_layout == 'compact':
            # ## TOOLBAR INSTALLATION # ##
            self.app.ui.toolbarfile = QtWidgets.QToolBar('File Toolbar')
            self.app.ui.toolbarfile.setObjectName('File_TB')
            self.app.ui.addToolBar(Qt.LeftToolBarArea, self.app.ui.toolbarfile)

            self.app.ui.toolbargeo = QtWidgets.QToolBar('Edit Toolbar')
            self.app.ui.toolbargeo.setObjectName('Edit_TB')
            self.app.ui.addToolBar(Qt.LeftToolBarArea, self.app.ui.toolbargeo)

            self.app.ui.toolbarshell = QtWidgets.QToolBar('Shell Toolbar')
            self.app.ui.toolbarshell.setObjectName('Shell_TB')
            self.app.ui.addToolBar(Qt.LeftToolBarArea, self.app.ui.toolbarshell)

            self.app.ui.toolbartools = QtWidgets.QToolBar('Tools Toolbar')
            self.app.ui.toolbartools.setObjectName('Tools_TB')
            self.app.ui.addToolBar(Qt.LeftToolBarArea, self.app.ui.toolbartools)

            self.app.ui.geo_edit_toolbar = QtWidgets.QToolBar('Geometry Editor Toolbar')
            # self.app.ui.geo_edit_toolbar.setVisible(False)
            self.app.ui.geo_edit_toolbar.setObjectName('GeoEditor_TB')
            self.app.ui.addToolBar(Qt.RightToolBarArea, self.app.ui.geo_edit_toolbar)

            self.app.ui.toolbarview = QtWidgets.QToolBar('View Toolbar')
            self.app.ui.toolbarview.setObjectName('View_TB')
            self.app.ui.addToolBar(Qt.RightToolBarArea, self.app.ui.toolbarview)

            self.app.ui.addToolBarBreak(area=Qt.RightToolBarArea)

            self.app.ui.grb_edit_toolbar = QtWidgets.QToolBar('Gerber Editor Toolbar')
            # self.app.ui.grb_edit_toolbar.setVisible(False)
            self.app.ui.grb_edit_toolbar.setObjectName('GrbEditor_TB')
            self.app.ui.addToolBar(Qt.RightToolBarArea, self.app.ui.grb_edit_toolbar)

            self.app.ui.exc_edit_toolbar = QtWidgets.QToolBar('Excellon Editor Toolbar')
            self.app.ui.exc_edit_toolbar.setObjectName('ExcEditor_TB')
            self.app.ui.addToolBar(Qt.RightToolBarArea, self.app.ui.exc_edit_toolbar)

            self.app.ui.snap_toolbar = QtWidgets.QToolBar('Grid Toolbar')
            self.app.ui.snap_toolbar.setObjectName('Snap_TB')
            self.app.ui.snap_toolbar.setMaximumHeight(30)
            self.app.ui.splitter_left.addWidget(self.app.ui.snap_toolbar)

            self.app.ui.corner_snap_btn.setVisible(True)
            self.app.ui.snap_magnet.setVisible(True)
        else:
            # ## TOOLBAR INSTALLATION # ##
            self.app.ui.toolbarfile = QtWidgets.QToolBar('File Toolbar')
            self.app.ui.toolbarfile.setObjectName('File_TB')
            self.app.ui.addToolBar(self.app.ui.toolbarfile)

            self.app.ui.toolbargeo = QtWidgets.QToolBar('Edit Toolbar')
            self.app.ui.toolbargeo.setObjectName('Edit_TB')
            self.app.ui.addToolBar(self.app.ui.toolbargeo)

            self.app.ui.toolbarview = QtWidgets.QToolBar('View Toolbar')
            self.app.ui.toolbarview.setObjectName('View_TB')
            self.app.ui.addToolBar(self.app.ui.toolbarview)

            self.app.ui.toolbarshell = QtWidgets.QToolBar('Shell Toolbar')
            self.app.ui.toolbarshell.setObjectName('Shell_TB')
            self.app.ui.addToolBar(self.app.ui.toolbarshell)

            self.app.ui.toolbartools = QtWidgets.QToolBar('Tools Toolbar')
            self.app.ui.toolbartools.setObjectName('Tools_TB')
            self.app.ui.addToolBar(self.app.ui.toolbartools)

            self.app.ui.exc_edit_toolbar = QtWidgets.QToolBar('Excellon Editor Toolbar')
            # self.app.ui.exc_edit_toolbar.setVisible(False)
            self.app.ui.exc_edit_toolbar.setObjectName('ExcEditor_TB')
            self.app.ui.addToolBar(self.app.ui.exc_edit_toolbar)

            self.app.ui.addToolBarBreak()

            self.app.ui.geo_edit_toolbar = QtWidgets.QToolBar('Geometry Editor Toolbar')
            # self.app.ui.geo_edit_toolbar.setVisible(False)
            self.app.ui.geo_edit_toolbar.setObjectName('GeoEditor_TB')
            self.app.ui.addToolBar(self.app.ui.geo_edit_toolbar)

            self.app.ui.grb_edit_toolbar = QtWidgets.QToolBar('Gerber Editor Toolbar')
            # self.app.ui.grb_edit_toolbar.setVisible(False)
            self.app.ui.grb_edit_toolbar.setObjectName('GrbEditor_TB')
            self.app.ui.addToolBar(self.app.ui.grb_edit_toolbar)

            self.app.ui.snap_toolbar = QtWidgets.QToolBar('Grid Toolbar')
            self.app.ui.snap_toolbar.setObjectName('Snap_TB')
            # self.app.ui.snap_toolbar.setMaximumHeight(30)
            self.app.ui.addToolBar(self.app.ui.snap_toolbar)

            self.app.ui.corner_snap_btn.setVisible(False)
            self.app.ui.snap_magnet.setVisible(False)

        if current_layout == 'minimal':
            self.app.ui.toolbarview.setVisible(False)
            self.app.ui.toolbarshell.setVisible(False)
            self.app.ui.snap_toolbar.setVisible(False)
            self.app.ui.geo_edit_toolbar.setVisible(False)
            self.app.ui.grb_edit_toolbar.setVisible(False)
            self.app.ui.exc_edit_toolbar.setVisible(False)
            self.app.ui.lock_toolbar(lock=True)

        # add all the actions to the toolbars
        self.app.ui.populate_toolbars()

        # reconnect all the signals to the toolbar actions
        self.app.connect_toolbar_signals()

        self.app.ui.grid_snap_btn.setChecked(True)
        self.app.ui.on_grid_snap_triggered(state=True)

        self.app.ui.grid_gap_x_entry.setText(str(self.app.defaults["global_gridx"]))
        self.app.ui.grid_gap_y_entry.setText(str(self.app.defaults["global_gridy"]))
        self.app.ui.snap_max_dist_entry.setText(str(self.app.defaults["global_snap_max"]))
        self.app.ui.grid_gap_link_cb.setChecked(True)

    @staticmethod
    def handle_style(style):
        # FIXME: this should be moved out to a view model
        # set current style
        qsettings = QSettings("Open Source", "FlatCAM")
        qsettings.setValue('style', style)

        # This will write the setting to the platform specific storage.
        del qsettings

    @staticmethod
    def handle_hdpi(state):
        # FIXME: this should be moved out to a view model
        # set current HDPI
        qsettings = QSettings("Open Source", "FlatCAM")
        qsettings.setValue('hdpi', state)

        # This will write the setting to the platform specific storage.
        del qsettings