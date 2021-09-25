from PyQt6 import QtWidgets, QtCore
from PyQt6.QtCore import QSettings

from appGUI.GUIElements import RadioSet, FCCheckBox, FCComboBox, FCSliderWithSpinner, FCColorEntry, FCLabel, \
    FCGridLayout, FCFrame
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GeneralGUIPrefGroupUI(OptionsGroupUI):
    def __init__(self, defaults, decimals=4, parent=None):
        super(GeneralGUIPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("GUI Preferences")))
        self.decimals = decimals
        self.defaults = defaults

        self.param_lbl = FCLabel('<span style="color:blue;"><b>%s</b></span>' % _("Parameters"))
        self.layout.addWidget(self.param_lbl)

        # #############################################################################################################
        # Grid0 Frame
        # #############################################################################################################
        par_frame = FCFrame()
        self.layout.addWidget(par_frame)

        grid0 = FCGridLayout(v_spacing=5, h_spacing=3)
        par_frame.setLayout(grid0)

        # Theme selection
        self.theme_label = FCLabel('%s:' % _('Theme'))
        self.theme_label.setToolTip(
            _("Select a theme for the application.\n"
              "It will theme the plot area.")
        )

        self.theme_radio = RadioSet([
            {"label": _("Light"), "value": "white"},
            {"label": _("Dark"), "value": "black"}
        ], compact=True)

        grid0.addWidget(self.theme_label, 0, 0)
        grid0.addWidget(self.theme_radio, 0, 1)

        # Enable Gray Icons
        self.gray_icons_cb = FCCheckBox('%s' % _('Use Gray Icons'))
        self.gray_icons_cb.setToolTip(
            _("Check this box to use a set of icons with\n"
              "a lighter (gray) color. To be used when a\n"
              "full dark theme is applied.")
        )
        grid0.addWidget(self.gray_icons_cb, 2, 0, 1, 3)

        # self.theme_button = FCButton(_("Apply Theme"))
        # self.theme_button.setToolTip(
        #     _("Select a theme for FlatCAM.\n"
        #       "It will theme the plot area.\n"
        #       "The application will restart after change.")
        # )
        # grid0.addWidget(self.theme_button, 2, 0, 1, 3)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        grid0.addWidget(separator_line, 4, 0, 1, 2)

        # Layout selection
        self.layout_label = FCLabel('%s:' % _('Layout'))
        self.layout_label.setToolTip(
            _("Select a layout for the application.\n"
              "It is applied immediately.")
        )
        self.layout_combo = FCComboBox()
        # don't translate the QCombo items as they are used in QSettings and identified by name
        self.layout_combo.addItem("standard")
        self.layout_combo.addItem("compact")
        self.layout_combo.addItem("minimal")

        grid0.addWidget(self.layout_label, 6, 0)
        grid0.addWidget(self.layout_combo, 6, 1)

        # Set the current index for layout_combo
        qsettings = QSettings("Open Source", "FlatCAM")
        if qsettings.contains("layout"):
            layout = qsettings.value('layout', type=str)
            idx = self.layout_combo.findText(layout.capitalize())
            self.layout_combo.setCurrentIndex(idx)

        # Style selection
        self.style_label = FCLabel('%s:' % _('Style'))
        self.style_label.setToolTip(
            _("Select a style for the application.\n"
              "It will be applied at the next app start.")
        )
        self.style_combo = FCComboBox()
        self.style_combo.addItems(QtWidgets.QStyleFactory.keys())
        # find current style
        current_style = QtWidgets.QApplication.style().objectName()
        index = self.style_combo.findText(current_style, QtCore.Qt.MatchFlag.MatchFixedString)
        self.style_combo.setCurrentIndex(index)
        self.style_combo.activated.connect(self.handle_style)

        grid0.addWidget(self.style_label, 8, 0)
        grid0.addWidget(self.style_combo, 8, 1)

        # Enable Hover box
        self.hover_cb = FCCheckBox('%s' % _('Hover Shape'))
        self.hover_cb.setToolTip(
            _("Enable display of a hover shape for the application objects.\n"
              "It is displayed whenever the mouse cursor is hovering\n"
              "over any kind of not-selected object.")
        )
        grid0.addWidget(self.hover_cb, 10, 0, 1, 3)

        # Enable Selection box
        self.selection_cb = FCCheckBox('%s' % _('Selection Shape'))
        self.selection_cb.setToolTip(
            _("Enable the display of a selection shape for the application objects.\n"
              "It is displayed whenever the mouse selects an object\n"
              "either by clicking or dragging mouse from left to right or\n"
              "right to left.")
        )
        grid0.addWidget(self.selection_cb, 12, 0, 1, 3)

        # #############################################################################################################
        # Grid1 Frame
        # #############################################################################################################
        self.color_lbl = FCLabel('<span style="color:red;"><b>%s</b></span>' % _("Colors"))
        self.layout.addWidget(self.color_lbl)

        color_frame = FCFrame()
        self.layout.addWidget(color_frame)

        grid1 = FCGridLayout(v_spacing=5, h_spacing=3)
        color_frame.setLayout(grid1)

        # Plot Selection (left - right) Color
        self.sel_lr_label = FCLabel('<b>%s</b>' % _('Left-Right Selection Color'))
        grid1.addWidget(self.sel_lr_label, 0, 0, 1, 2)

        self.sl_color_label = FCLabel('%s:' % _('Outline'))
        self.sl_color_label.setToolTip(
            _("Set the line color for the 'left to right' selection box.")
        )
        self.sl_color_entry = FCColorEntry()

        grid1.addWidget(self.sl_color_label, 2, 0)
        grid1.addWidget(self.sl_color_entry, 2, 1)

        self.sf_color_label = FCLabel('%s:' % _('Fill'))
        self.sf_color_label.setToolTip(
            _("Set the fill color for the selection box\n"
              "in case that the selection is done from left to right.\n"
              "First 6 digits are the color and the last 2\n"
              "digits are for alpha (transparency) level.")
        )
        self.sf_color_entry = FCColorEntry()

        grid1.addWidget(self.sf_color_label, 4, 0)
        grid1.addWidget(self.sf_color_entry, 4, 1)

        # Plot Selection (left - right) Fill Transparency Level
        self.left_right_alpha_label = FCLabel('%s:' % _('Alpha'))
        self.left_right_alpha_label.setToolTip(
            _("Set the fill transparency for the 'left to right' selection box.")
        )
        self.left_right_alpha_entry = FCSliderWithSpinner(0, 255, 1)

        grid1.addWidget(self.left_right_alpha_label, 6, 0)
        grid1.addWidget(self.left_right_alpha_entry, 6, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        grid1.addWidget(separator_line, 8, 0, 1, 2)

        # Plot Selection (left - right) Color
        self.sel_rl_label = FCLabel('<b>%s</b>' % _('Right-Left Selection Color'))
        grid1.addWidget(self.sel_rl_label, 10, 0, 1, 2)

        # Plot Selection (right - left) Line Color
        self.alt_sl_color_label = FCLabel('%s:' % _('Outline'))
        self.alt_sl_color_label.setToolTip(
            _("Set the line color for the 'right to left' selection box.")
        )
        self.alt_sl_color_entry = FCColorEntry()

        grid1.addWidget(self.alt_sl_color_label, 12, 0)
        grid1.addWidget(self.alt_sl_color_entry, 12, 1)

        # Plot Selection (right - left) Fill Color
        self.alt_sf_color_label = FCLabel('%s:' % _('Fill'))
        self.alt_sf_color_label.setToolTip(
            _("Set the fill color for the selection box\n"
              "in case that the selection is done from right to left.\n"
              "First 6 digits are the color and the last 2\n"
              "digits are for alpha (transparency) level.")
        )
        self.alt_sf_color_entry = FCColorEntry()

        grid1.addWidget(self.alt_sf_color_label, 14, 0)
        grid1.addWidget(self.alt_sf_color_entry, 14, 1)

        # Plot Selection (right - left) Fill Transparency Level
        self.right_left_alpha_label = FCLabel('%s:' % _('Alpha'))
        self.right_left_alpha_label.setToolTip(
            _("Set the fill transparency for selection 'right to left' box.")
        )
        self.right_left_alpha_entry = FCSliderWithSpinner(0, 255, 1)

        grid1.addWidget(self.right_left_alpha_label, 16, 0)
        grid1.addWidget(self.right_left_alpha_entry, 16, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        grid1.addWidget(separator_line, 18, 0, 1, 2)

        # ------------------------------------------------------------------
        # ----------------------- Editor Color -----------------------------
        # ------------------------------------------------------------------

        self.editor_color_label = FCLabel('<b>%s</b>' % _('Editor Color'))
        grid1.addWidget(self.editor_color_label, 20, 0, 1, 2)

        # Editor Draw Color
        self.draw_color_label = FCLabel('%s:' % _('Drawing'))
        self.alt_sf_color_label.setToolTip(
            _("Set the color for the shape.")
        )
        self.draw_color_entry = FCColorEntry()

        grid1.addWidget(self.draw_color_label, 22, 0)
        grid1.addWidget(self.draw_color_entry, 22, 1)

        # Editor Draw Selection Color
        self.sel_draw_color_label = FCLabel('%s:' % _('Selection'))
        self.sel_draw_color_label.setToolTip(
            _("Set the color of the shape when selected.")
        )
        self.sel_draw_color_entry = FCColorEntry()

        grid1.addWidget(self.sel_draw_color_label, 24, 0)
        grid1.addWidget(self.sel_draw_color_entry, 24, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        grid1.addWidget(separator_line, 26, 0, 1, 2)

        # ------------------------------------------------------------------
        # ----------------------- Project Settings -----------------------------
        # ------------------------------------------------------------------

        self.proj_settings_label = FCLabel('<b>%s</b>' % _('Project Items Color'))
        grid1.addWidget(self.proj_settings_label, 28, 0, 1, 2)

        # Project Tab items color
        self.proj_color_label = FCLabel('%s:' % _('Enabled'))
        self.proj_color_label.setToolTip(
            _("Set the color of the items in Project Tab Tree.")
        )
        self.proj_color_entry = FCColorEntry()

        grid1.addWidget(self.proj_color_label, 30, 0)
        grid1.addWidget(self.proj_color_entry, 30, 1)

        self.proj_color_dis_label = FCLabel('%s:' % _('Disabled'))
        self.proj_color_dis_label.setToolTip(
            _("Set the color of the items in Project Tab Tree,\n"
              "for the case when the items are disabled.")
        )
        self.proj_color_dis_entry = FCColorEntry()

        grid1.addWidget(self.proj_color_dis_label, 32, 0)
        grid1.addWidget(self.proj_color_dis_entry, 32, 1)

        FCGridLayout.set_common_column_size([grid0, grid1], 0)

        # Project autohide CB
        self.project_autohide_cb = FCCheckBox(label=_('Project AutoHide'))
        self.project_autohide_cb.setToolTip(
            _("Check this box if you want the project/selected/tool tab area to\n"
              "hide automatically when there are no objects loaded and\n"
              "to show whenever a new object is created.")
        )

        self.layout.addWidget(self.project_autohide_cb)

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
        qsettings.setValue('style', str(style))

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
