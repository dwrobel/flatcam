from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QSettings, Qt

from appGUI.GUIElements import RadioSet, FCCheckBox, FCComboBox, FCSliderWithSpinner, FCColorEntry
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


class GeneralGUIPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):
        super(GeneralGUIPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("GUI Preferences")))
        self.decimals = decimals

        # Create a grid layout for the Application general settings
        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)

        # Theme selection
        self.theme_label = QtWidgets.QLabel('%s:' % _('Theme'))
        self.theme_label.setToolTip(
            _("Select a theme for the application.\n"
              "It will theme the plot area.")
        )

        self.theme_radio = RadioSet([
            {"label": _("Light"), "value": "white"},
            {"label": _("Dark"), "value": "black"}
        ], orientation='vertical')

        grid0.addWidget(self.theme_label, 0, 0)
        grid0.addWidget(self.theme_radio, 0, 1)

        # Enable Gray Icons
        self.gray_icons_cb = FCCheckBox('%s' % _('Use Gray Icons'))
        self.gray_icons_cb.setToolTip(
            _("Check this box to use a set of icons with\n"
              "a lighter (gray) color. To be used when a\n"
              "full dark theme is applied.")
        )
        grid0.addWidget(self.gray_icons_cb, 1, 0, 1, 3)

        # self.theme_button = FCButton(_("Apply Theme"))
        # self.theme_button.setToolTip(
        #     _("Select a theme for FlatCAM.\n"
        #       "It will theme the plot area.\n"
        #       "The application will restart after change.")
        # )
        # grid0.addWidget(self.theme_button, 2, 0, 1, 3)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 3, 0, 1, 2)

        # Layout selection
        self.layout_label = QtWidgets.QLabel('%s:' % _('Layout'))
        self.layout_label.setToolTip(
            _("Select a layout for the application.\n"
              "It is applied immediately.")
        )
        self.layout_combo = FCComboBox()
        # don't translate the QCombo items as they are used in QSettings and identified by name
        self.layout_combo.addItem("standard")
        self.layout_combo.addItem("compact")
        self.layout_combo.addItem("minimal")

        grid0.addWidget(self.layout_label, 4, 0)
        grid0.addWidget(self.layout_combo, 4, 1)

        # Set the current index for layout_combo
        qsettings = QSettings("Open Source", "FlatCAM")
        if qsettings.contains("layout"):
            layout = qsettings.value('layout', type=str)
            idx = self.layout_combo.findText(layout.capitalize())
            self.layout_combo.setCurrentIndex(idx)

        # Style selection
        self.style_label = QtWidgets.QLabel('%s:' % _('Style'))
        self.style_label.setToolTip(
            _("Select a style for the application.\n"
              "It will be applied at the next app start.")
        )
        self.style_combo = FCComboBox()
        self.style_combo.addItems(QtWidgets.QStyleFactory.keys())
        # find current style
        index = self.style_combo.findText(QtWidgets.qApp.style().objectName(), QtCore.Qt.MatchFixedString)
        self.style_combo.setCurrentIndex(index)
        self.style_combo.activated[str].connect(self.handle_style)

        grid0.addWidget(self.style_label, 5, 0)
        grid0.addWidget(self.style_combo, 5, 1)

        # Enable High DPI Support
        self.hdpi_cb = FCCheckBox('%s' % _('HDPI Support'))
        self.hdpi_cb.setToolTip(
            _("Enable High DPI support for the application.\n"
              "It will be applied at the next app start.")
        )

        qsettings = QSettings("Open Source", "FlatCAM")
        if qsettings.contains("hdpi"):
            self.hdpi_cb.set_value(qsettings.value('hdpi', type=int))
        else:
            self.hdpi_cb.set_value(False)
        self.hdpi_cb.stateChanged.connect(self.handle_hdpi)

        grid0.addWidget(self.hdpi_cb, 6, 0, 1, 3)

        # Enable Hover box
        self.hover_cb = FCCheckBox('%s' % _('Hover Shape'))
        self.hover_cb.setToolTip(
            _("Enable display of a hover shape for the application objects.\n"
              "It is displayed whenever the mouse cursor is hovering\n"
              "over any kind of not-selected object.")
        )
        grid0.addWidget(self.hover_cb, 8, 0, 1, 3)

        # Enable Selection box
        self.selection_cb = FCCheckBox('%s' % _('Selection Shape'))
        self.selection_cb.setToolTip(
            _("Enable the display of a selection shape for the application objects.\n"
              "It is displayed whenever the mouse selects an object\n"
              "either by clicking or dragging mouse from left to right or\n"
              "right to left.")
        )
        grid0.addWidget(self.selection_cb, 9, 0, 1, 3)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 14, 0, 1, 2)

        # Plot Selection (left - right) Color
        self.sel_lr_label = QtWidgets.QLabel('<b>%s</b>' % _('Left-Right Selection Color'))
        grid0.addWidget(self.sel_lr_label, 15, 0, 1, 2)

        self.sl_color_label = QtWidgets.QLabel('%s:' % _('Outline'))
        self.sl_color_label.setToolTip(
            _("Set the line color for the 'left to right' selection box.")
        )
        self.sl_color_entry = FCColorEntry()

        grid0.addWidget(self.sl_color_label, 16, 0)
        grid0.addWidget(self.sl_color_entry, 16, 1)

        self.sf_color_label = QtWidgets.QLabel('%s:' % _('Fill'))
        self.sf_color_label.setToolTip(
            _("Set the fill color for the selection box\n"
              "in case that the selection is done from left to right.\n"
              "First 6 digits are the color and the last 2\n"
              "digits are for alpha (transparency) level.")
        )
        self.sf_color_entry = FCColorEntry()

        grid0.addWidget(self.sf_color_label, 17, 0)
        grid0.addWidget(self.sf_color_entry, 17, 1)

        # Plot Selection (left - right) Fill Transparency Level
        self.left_right_alpha_label = QtWidgets.QLabel('%s:' % _('Alpha'))
        self.left_right_alpha_label.setToolTip(
            _("Set the fill transparency for the 'left to right' selection box.")
        )
        self.left_right_alpha_entry = FCSliderWithSpinner(0, 255, 1)

        grid0.addWidget(self.left_right_alpha_label, 18, 0)
        grid0.addWidget(self.left_right_alpha_entry, 18, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 19, 0, 1, 2)

        # Plot Selection (left - right) Color
        self.sel_rl_label = QtWidgets.QLabel('<b>%s</b>' % _('Right-Left Selection Color'))
        grid0.addWidget(self.sel_rl_label, 20, 0, 1, 2)

        # Plot Selection (right - left) Line Color
        self.alt_sl_color_label = QtWidgets.QLabel('%s:' % _('Outline'))
        self.alt_sl_color_label.setToolTip(
            _("Set the line color for the 'right to left' selection box.")
        )
        self.alt_sl_color_entry = FCColorEntry()

        grid0.addWidget(self.alt_sl_color_label, 21, 0)
        grid0.addWidget(self.alt_sl_color_entry, 21, 1)

        # Plot Selection (right - left) Fill Color
        self.alt_sf_color_label = QtWidgets.QLabel('%s:' % _('Fill'))
        self.alt_sf_color_label.setToolTip(
            _("Set the fill color for the selection box\n"
              "in case that the selection is done from right to left.\n"
              "First 6 digits are the color and the last 2\n"
              "digits are for alpha (transparency) level.")
        )
        self.alt_sf_color_entry = FCColorEntry()

        grid0.addWidget(self.alt_sf_color_label, 22, 0)
        grid0.addWidget(self.alt_sf_color_entry, 22, 1)

        # Plot Selection (right - left) Fill Transparency Level
        self.right_left_alpha_label = QtWidgets.QLabel('%s:' % _('Alpha'))
        self.right_left_alpha_label.setToolTip(
            _("Set the fill transparency for selection 'right to left' box.")
        )
        self.right_left_alpha_entry = FCSliderWithSpinner(0, 255, 1)

        grid0.addWidget(self.right_left_alpha_label, 23, 0)
        grid0.addWidget(self.right_left_alpha_entry, 23, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 24, 0, 1, 2)

        # ------------------------------------------------------------------
        # ----------------------- Editor Color -----------------------------
        # ------------------------------------------------------------------

        self.editor_color_label = QtWidgets.QLabel('<b>%s</b>' % _('Editor Color'))
        grid0.addWidget(self.editor_color_label, 25, 0, 1, 2)

        # Editor Draw Color
        self.draw_color_label = QtWidgets.QLabel('%s:' % _('Drawing'))
        self.alt_sf_color_label.setToolTip(
            _("Set the color for the shape.")
        )
        self.draw_color_entry = FCColorEntry()

        grid0.addWidget(self.draw_color_label, 26, 0)
        grid0.addWidget(self.draw_color_entry, 26, 1)

        # Editor Draw Selection Color
        self.sel_draw_color_label = QtWidgets.QLabel('%s:' % _('Selection'))
        self.sel_draw_color_label.setToolTip(
            _("Set the color of the shape when selected.")
        )
        self.sel_draw_color_entry = FCColorEntry()

        grid0.addWidget(self.sel_draw_color_label, 27, 0)
        grid0.addWidget(self.sel_draw_color_entry, 27, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 28, 0, 1, 2)

        # ------------------------------------------------------------------
        # ----------------------- Project Settings -----------------------------
        # ------------------------------------------------------------------

        self.proj_settings_label = QtWidgets.QLabel('<b>%s</b>' % _('Project Items Color'))
        grid0.addWidget(self.proj_settings_label, 29, 0, 1, 2)

        # Project Tab items color
        self.proj_color_label = QtWidgets.QLabel('%s:' % _('Enabled'))
        self.proj_color_label.setToolTip(
            _("Set the color of the items in Project Tab Tree.")
        )
        self.proj_color_entry = FCColorEntry()

        grid0.addWidget(self.proj_color_label, 30, 0)
        grid0.addWidget(self.proj_color_entry, 30, 1)

        self.proj_color_dis_label = QtWidgets.QLabel('%s:' % _('Disabled'))
        self.proj_color_dis_label.setToolTip(
            _("Set the color of the items in Project Tab Tree,\n"
              "for the case when the items are disabled.")
        )
        self.proj_color_dis_entry = FCColorEntry()

        grid0.addWidget(self.proj_color_dis_label, 31, 0)
        grid0.addWidget(self.proj_color_dis_entry, 31, 1)

        # Project autohide CB
        self.project_autohide_cb = FCCheckBox(label=_('Project AutoHide'))
        self.project_autohide_cb.setToolTip(
            _("Check this box if you want the project/selected/tool tab area to\n"
              "hide automatically when there are no objects loaded and\n"
              "to show whenever a new object is created.")
        )

        grid0.addWidget(self.project_autohide_cb, 32, 0, 1, 2)

        # Just to add empty rows
        grid0.addWidget(QtWidgets.QLabel(''), 33, 0, 1, 2)

        self.layout.addStretch()

        # #############################################################################
        # ############################# GUI COLORS SIGNALS ############################
        # #############################################################################

        # Setting selection (left - right) colors signals
        self.sf_color_entry.editingFinished.connect(self.on_sf_color_entry)
        self.sl_color_entry.editingFinished.connect(self.on_sl_color_entry)

        self.left_right_alpha_entry.valueChanged.connect(self.on_left_right_alpha_changed)  # alpha

        # Setting selection (right - left) colors signals
        self.alt_sf_color_entry.editingFinished.connect(self.on_alt_sf_color_entry)
        self.alt_sl_color_entry.editingFinished.connect(self.on_alt_sl_color_entry)

        self.right_left_alpha_entry.valueChanged.connect(self.on_right_left_alpha_changed)  # alpha

        # Setting Editor Draw colors signals
        self.draw_color_entry.editingFinished.connect(self.on_draw_color_entry)
        self.sel_draw_color_entry.editingFinished.connect(self.on_sel_draw_color_entry)

        self.proj_color_entry.editingFinished.connect(self.on_proj_color_entry)
        self.proj_color_dis_entry.editingFinished.connect(self.on_proj_color_dis_entry)

        self.layout_combo.activated.connect(self.app.on_layout)

    @staticmethod
    def handle_style(style):
        # set current style
        qsettings = QSettings("Open Source", "FlatCAM")
        qsettings.setValue('style', style)

        # This will write the setting to the platform specific storage.
        del qsettings

    @staticmethod
    def handle_hdpi(state):
        # set current HDPI
        qsettings = QSettings("Open Source", "FlatCAM")
        qsettings.setValue('hdpi', state)

        # This will write the setting to the platform specific storage.
        del qsettings

    # Setting selection colors (left - right) handlers
    def on_sf_color_entry(self):
        self.app.defaults['global_sel_fill'] = self.app.defaults['global_sel_fill'][7:9]

    def on_sl_color_entry(self):
        self.app.defaults['global_sel_line'] = self.sl_color_entry.get_value()[:7] + \
            self.app.defaults['global_sel_line'][7:9]

    def on_left_right_alpha_changed(self, spinner_value):
        """
        Change the alpha level for the color of the selection box when selection is done left to right.
        Called on valueChanged of a FCSliderWithSpinner.

        :param spinner_value:   passed value within [0, 255]
        :type spinner_value:    int
        :return:                None
        :rtype:
        """

        self.app.defaults['global_sel_fill'] = self.app.defaults['global_sel_fill'][:7] + \
            (hex(spinner_value)[2:] if int(hex(spinner_value)[2:], 16) > 0 else '00')
        self.app.defaults['global_sel_line'] = self.app.defaults['global_sel_line'][:7] + \
            (hex(spinner_value)[2:] if int(hex(spinner_value)[2:], 16) > 0 else '00')

    # Setting selection colors (right - left) handlers
    def on_alt_sf_color_entry(self):
        self.app.defaults['global_alt_sel_fill'] = self.alt_sf_color_entry.get_value()[:7] + \
                                                   self.app.defaults['global_alt_sel_fill'][7:9]

    def on_alt_sl_color_entry(self):
        self.app.defaults['global_alt_sel_line'] = self.alt_sl_color_entry.get_value()[:7] + \
                                                   self.app.defaults['global_alt_sel_line'][7:9]

    def on_right_left_alpha_changed(self, spinner_value):
        """
        Change the alpha level for the color of the selection box when selection is done right to left.
        Called on valueChanged of a FCSliderWithSpinner.

        :param spinner_value:   passed value within [0, 255]
        :type spinner_value:    int
        :return:                None
        :rtype:
        """

        self.app.defaults['global_alt_sel_fill'] = self.app.defaults['global_alt_sel_fill'][:7] + \
            (hex(spinner_value)[2:] if int(hex(spinner_value)[2:], 16) > 0 else '00')
        self.app.defaults['global_alt_sel_line'] = self.app.defaults['global_alt_sel_line'][:7] + \
            (hex(spinner_value)[2:] if int(hex(spinner_value)[2:], 16) > 0 else '00')

    # Setting Editor colors
    def on_draw_color_entry(self):
        self.app.defaults['global_draw_color'] = self.draw_color_entry.get_value()

    def on_sel_draw_color_entry(self):
        self.app.defaults['global_sel_draw_color'] = self.sel_draw_color_entry.get_value()

    def on_proj_color_entry(self):
        self.app.defaults['global_proj_item_color'] = self.proj_color_entry.get_value()

    def on_proj_color_dis_entry(self):
        self.app.defaults['global_proj_item_dis_color'] = self.proj_color_dis_entry.get_value()
