from PyQt5.QtCore import QSettings
from flatcamGUI.GUIElements import *
import platform
import webbrowser
import sys

from flatcamEditors.FlatCAMGeoEditor import FCShapeTool

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class OptionsGroupUI(QtWidgets.QGroupBox):
    def __init__(self, title, parent=None):
        # QtGui.QGroupBox.__init__(self, title, parent=parent)
        super(OptionsGroupUI, self).__init__()
        self.setStyleSheet("""
        QGroupBox
        {
            font-size: 16px;
            font-weight: bold;
        }
        """)

        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)


class GeneralPreferencesUI(QtWidgets.QWidget):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)

        self.general_app_group = GeneralAppPrefGroupUI()
        self.general_app_group.setMinimumWidth(290)

        self.general_gui_group = GeneralGUIPrefGroupUI()
        self.general_gui_group.setMinimumWidth(250)

        self.general_gui_set_group = GeneralGUISetGroupUI()
        self.general_gui_set_group.setMinimumWidth(250)

        self.layout.addWidget(self.general_app_group)
        self.layout.addWidget(self.general_gui_group)
        self.layout.addWidget(self.general_gui_set_group)

        self.layout.addStretch()


class GerberPreferencesUI(QtWidgets.QWidget):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)

        self.gerber_gen_group = GerberGenPrefGroupUI()
        self.gerber_gen_group.setMinimumWidth(250)
        self.gerber_opt_group = GerberOptPrefGroupUI()
        self.gerber_opt_group.setMinimumWidth(250)
        self.gerber_exp_group = GerberExpPrefGroupUI()
        self.gerber_exp_group.setMinimumWidth(230)
        self.gerber_adv_opt_group = GerberAdvOptPrefGroupUI()
        self.gerber_adv_opt_group.setMinimumWidth(200)
        self.gerber_editor_group = GerberEditorPrefGroupUI()
        self.gerber_editor_group.setMinimumWidth(200)

        self.vlay = QtWidgets.QVBoxLayout()
        self.vlay.addWidget(self.gerber_opt_group)
        self.vlay.addWidget(self.gerber_exp_group)

        self.layout.addWidget(self.gerber_gen_group)
        self.layout.addLayout(self.vlay)
        self.layout.addWidget(self.gerber_adv_opt_group)
        self.layout.addWidget(self.gerber_editor_group)

        self.layout.addStretch()


class ExcellonPreferencesUI(QtWidgets.QWidget):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)

        self.excellon_gen_group = ExcellonGenPrefGroupUI()
        self.excellon_gen_group.setMinimumWidth(220)
        self.excellon_opt_group = ExcellonOptPrefGroupUI()
        self.excellon_opt_group.setMinimumWidth(290)
        self.excellon_exp_group = ExcellonExpPrefGroupUI()
        self.excellon_exp_group.setMinimumWidth(250)
        self.excellon_adv_opt_group = ExcellonAdvOptPrefGroupUI()
        self.excellon_adv_opt_group.setMinimumWidth(250)
        self.excellon_editor_group = ExcellonEditorPrefGroupUI()
        self.excellon_editor_group.setMinimumWidth(260)

        self.vlay = QtWidgets.QVBoxLayout()
        self.vlay.addWidget(self.excellon_opt_group)
        self.vlay.addWidget(self.excellon_exp_group)

        self.layout.addWidget(self.excellon_gen_group)
        self.layout.addLayout(self.vlay)
        self.layout.addWidget(self.excellon_adv_opt_group)
        self.layout.addWidget(self.excellon_editor_group)

        self.layout.addStretch()


class GeometryPreferencesUI(QtWidgets.QWidget):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)

        self.geometry_gen_group = GeometryGenPrefGroupUI()
        self.geometry_gen_group.setMinimumWidth(220)
        self.geometry_opt_group = GeometryOptPrefGroupUI()
        self.geometry_opt_group.setMinimumWidth(300)
        self.geometry_adv_opt_group = GeometryAdvOptPrefGroupUI()
        self.geometry_adv_opt_group.setMinimumWidth(270)
        self.geometry_editor_group = GeometryEditorPrefGroupUI()
        self.geometry_editor_group.setMinimumWidth(250)

        self.layout.addWidget(self.geometry_gen_group)
        self.layout.addWidget(self.geometry_opt_group)
        self.layout.addWidget(self.geometry_adv_opt_group)
        self.layout.addWidget(self.geometry_editor_group)

        self.layout.addStretch()


class ToolsPreferencesUI(QtWidgets.QWidget):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)

        self.tools_ncc_group = ToolsNCCPrefGroupUI()
        self.tools_ncc_group.setMinimumWidth(220)
        self.tools_paint_group = ToolsPaintPrefGroupUI()
        self.tools_paint_group.setMinimumWidth(220)

        self.tools_cutout_group = ToolsCutoutPrefGroupUI()
        self.tools_cutout_group.setMinimumWidth(220)

        self.tools_2sided_group = Tools2sidedPrefGroupUI()
        self.tools_2sided_group.setMinimumWidth(220)

        self.tools_film_group = ToolsFilmPrefGroupUI()
        self.tools_film_group.setMinimumWidth(220)

        self.tools_panelize_group = ToolsPanelizePrefGroupUI()
        self.tools_panelize_group.setMinimumWidth(220)

        self.tools_calculators_group = ToolsCalculatorsPrefGroupUI()
        self.tools_calculators_group.setMinimumWidth(220)

        self.tools_transform_group = ToolsTransformPrefGroupUI()
        self.tools_transform_group.setMinimumWidth(200)

        self.tools_solderpaste_group = ToolsSolderpastePrefGroupUI()
        self.tools_solderpaste_group.setMinimumWidth(200)

        self.tools_sub_group = ToolsSubPrefGroupUI()
        self.tools_sub_group.setMinimumWidth(200)

        self.vlay = QtWidgets.QVBoxLayout()
        self.vlay.addWidget(self.tools_ncc_group)
        self.vlay.addWidget(self.tools_paint_group)

        self.vlay1 = QtWidgets.QVBoxLayout()
        self.vlay1.addWidget(self.tools_cutout_group)
        self.vlay1.addWidget(self.tools_transform_group)
        self.vlay1.addWidget(self.tools_2sided_group)

        self.vlay2 = QtWidgets.QVBoxLayout()
        self.vlay2.addWidget(self.tools_panelize_group)
        self.vlay2.addWidget(self.tools_calculators_group)

        self.vlay3 = QtWidgets.QVBoxLayout()
        self.vlay3.addWidget(self.tools_solderpaste_group)
        self.vlay3.addWidget(self.tools_sub_group)
        self.vlay3.addWidget(self.tools_film_group)

        self.layout.addLayout(self.vlay)
        self.layout.addLayout(self.vlay1)
        self.layout.addLayout(self.vlay2)
        self.layout.addLayout(self.vlay3)

        self.layout.addStretch()


class CNCJobPreferencesUI(QtWidgets.QWidget):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)

        self.cncjob_gen_group = CNCJobGenPrefGroupUI()
        self.cncjob_gen_group.setMinimumWidth(320)
        self.cncjob_opt_group = CNCJobOptPrefGroupUI()
        self.cncjob_opt_group.setMinimumWidth(260)
        self.cncjob_adv_opt_group = CNCJobAdvOptPrefGroupUI()
        self.cncjob_adv_opt_group.setMinimumWidth(260)

        self.layout.addWidget(self.cncjob_gen_group)
        self.layout.addWidget(self.cncjob_opt_group)
        self.layout.addWidget(self.cncjob_adv_opt_group)

        self.layout.addStretch()


class UtilPreferencesUI(QtWidgets.QWidget):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)

        self.vlay = QtWidgets.QVBoxLayout()
        self.fa_excellon_group = FAExcPrefGroupUI()
        self.fa_excellon_group.setMinimumWidth(260)

        self.fa_gcode_group = FAGcoPrefGroupUI()
        self.fa_gcode_group.setMinimumWidth(260)

        self.vlay.addWidget(self.fa_excellon_group)
        self.vlay.addWidget(self.fa_gcode_group)

        self.fa_gerber_group = FAGrbPrefGroupUI()
        self.fa_gerber_group.setMinimumWidth(260)

        self.kw_group = AutoCompletePrefGroupUI()
        self.kw_group.setMinimumWidth(260)

        self.layout.addLayout(self.vlay)
        self.layout.addWidget(self.fa_gerber_group)
        self.layout.addWidget(self.kw_group)

        self.layout.addStretch()


class GeneralGUIPrefGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        super(GeneralGUIPrefGroupUI, self).__init__(self)

        self.setTitle(str(_("GUI Preferences")))

        # Create a form layout for the Application general settings
        self.form_box = QtWidgets.QFormLayout()

        # Grid X Entry
        self.gridx_label = QtWidgets.QLabel('%s:' % _('Grid X value'))
        self.gridx_label.setToolTip(
           _("This is the Grid snap value on X axis.")
        )
        self.gridx_entry = FCEntry3()

        # Grid Y Entry
        self.gridy_label = QtWidgets.QLabel('%s:' % _('Grid Y value'))
        self.gridy_label.setToolTip(
            _("This is the Grid snap value on Y axis.")
        )
        self.gridy_entry = FCEntry3()

        # Snap Max Entry
        self.snap_max_label = QtWidgets.QLabel('%s:' % _('Snap Max'))
        self.snap_max_label.setToolTip(_("Max. magnet distance"))
        self.snap_max_dist_entry = FCEntry()

        # Workspace
        self.workspace_lbl = QtWidgets.QLabel('%s:' % _('Workspace'))
        self.workspace_lbl.setToolTip(
           _("Draw a delimiting rectangle on canvas.\n"
             "The purpose is to illustrate the limits for our work.")
        )
        self.workspace_type_lbl = QtWidgets.QLabel('%s:' % _('Wk. format'))
        self.workspace_type_lbl.setToolTip(
           _("Select the type of rectangle to be used on canvas,\n"
             "as valid workspace.")
        )
        self.workspace_cb = FCCheckBox()
        self.wk_cb = FCComboBox()
        self.wk_cb.addItem('A4P')
        self.wk_cb.addItem('A4L')
        self.wk_cb.addItem('A3P')
        self.wk_cb.addItem('A3L')

        self.wks = OptionalInputSection(self.workspace_cb, [self.workspace_type_lbl, self.wk_cb])

        # Plot Fill Color
        self.pf_color_label = QtWidgets.QLabel('%s:' % _('Plot Fill'))
        self.pf_color_label.setToolTip(
           _("Set the fill color for plotted objects.\n"
             "First 6 digits are the color and the last 2\n"
             "digits are for alpha (transparency) level.")
        )
        self.pf_color_entry = FCEntry()
        self.pf_color_button = QtWidgets.QPushButton()
        self.pf_color_button.setFixedSize(15, 15)

        self.form_box_child_1 = QtWidgets.QHBoxLayout()
        self.form_box_child_1.addWidget(self.pf_color_entry)
        self.form_box_child_1.addWidget(self.pf_color_button)
        self.form_box_child_1.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        # Plot Fill Transparency Level
        self.pf_alpha_label = QtWidgets.QLabel('%s:' % _('Alpha Level'))
        self.pf_alpha_label.setToolTip(
           _("Set the fill transparency for plotted objects.")
        )
        self.pf_color_alpha_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.pf_color_alpha_slider.setMinimum(0)
        self.pf_color_alpha_slider.setMaximum(255)
        self.pf_color_alpha_slider.setSingleStep(1)

        self.pf_color_alpha_spinner = FCSpinner()
        self.pf_color_alpha_spinner.setMinimumWidth(70)
        self.pf_color_alpha_spinner.setMinimum(0)
        self.pf_color_alpha_spinner.setMaximum(255)

        self.form_box_child_2 = QtWidgets.QHBoxLayout()
        self.form_box_child_2.addWidget(self.pf_color_alpha_slider)
        self.form_box_child_2.addWidget(self.pf_color_alpha_spinner)

        # Plot Line Color
        self.pl_color_label = QtWidgets.QLabel('%s:' % _('Plot Line'))
        self.pl_color_label.setToolTip(
           _("Set the line color for plotted objects.")
        )
        self.pl_color_entry = FCEntry()
        self.pl_color_button = QtWidgets.QPushButton()
        self.pl_color_button.setFixedSize(15, 15)

        self.form_box_child_3 = QtWidgets.QHBoxLayout()
        self.form_box_child_3.addWidget(self.pl_color_entry)
        self.form_box_child_3.addWidget(self.pl_color_button)
        self.form_box_child_3.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        # Plot Selection (left - right) Fill Color
        self.sf_color_label = QtWidgets.QLabel('%s:' % _('Sel. Fill'))
        self.sf_color_label.setToolTip(
            _("Set the fill color for the selection box\n"
              "in case that the selection is done from left to right.\n"
              "First 6 digits are the color and the last 2\n"
              "digits are for alpha (transparency) level.")
        )
        self.sf_color_entry = FCEntry()
        self.sf_color_button = QtWidgets.QPushButton()
        self.sf_color_button.setFixedSize(15, 15)

        self.form_box_child_4 = QtWidgets.QHBoxLayout()
        self.form_box_child_4.addWidget(self.sf_color_entry)
        self.form_box_child_4.addWidget(self.sf_color_button)
        self.form_box_child_4.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        # Plot Selection (left - right) Fill Transparency Level
        self.sf_alpha_label = QtWidgets.QLabel('%s:' % _('Alpha Level'))
        self.sf_alpha_label.setToolTip(
            _("Set the fill transparency for the 'left to right' selection box.")
        )
        self.sf_color_alpha_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.sf_color_alpha_slider.setMinimum(0)
        self.sf_color_alpha_slider.setMaximum(255)
        self.sf_color_alpha_slider.setSingleStep(1)

        self.sf_color_alpha_spinner = FCSpinner()
        self.sf_color_alpha_spinner.setMinimumWidth(70)
        self.sf_color_alpha_spinner.setMinimum(0)
        self.sf_color_alpha_spinner.setMaximum(255)

        self.form_box_child_5 = QtWidgets.QHBoxLayout()
        self.form_box_child_5.addWidget(self.sf_color_alpha_slider)
        self.form_box_child_5.addWidget(self.sf_color_alpha_spinner)

        # Plot Selection (left - right) Line Color
        self.sl_color_label = QtWidgets.QLabel('%s:' % _('Sel. Line'))
        self.sl_color_label.setToolTip(
            _("Set the line color for the 'left to right' selection box.")
        )
        self.sl_color_entry = FCEntry()
        self.sl_color_button = QtWidgets.QPushButton()
        self.sl_color_button.setFixedSize(15, 15)

        self.form_box_child_6 = QtWidgets.QHBoxLayout()
        self.form_box_child_6.addWidget(self.sl_color_entry)
        self.form_box_child_6.addWidget(self.sl_color_button)
        self.form_box_child_6.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        # Plot Selection (right - left) Fill Color
        self.alt_sf_color_label = QtWidgets.QLabel('%s:' % _('Sel2. Fill'))
        self.alt_sf_color_label.setToolTip(
            _("Set the fill color for the selection box\n"
              "in case that the selection is done from right to left.\n"
              "First 6 digits are the color and the last 2\n"
              "digits are for alpha (transparency) level.")
        )
        self.alt_sf_color_entry = FCEntry()
        self.alt_sf_color_button = QtWidgets.QPushButton()
        self.alt_sf_color_button.setFixedSize(15, 15)

        self.form_box_child_7 = QtWidgets.QHBoxLayout()
        self.form_box_child_7.addWidget(self.alt_sf_color_entry)
        self.form_box_child_7.addWidget(self.alt_sf_color_button)
        self.form_box_child_7.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        # Plot Selection (right - left) Fill Transparency Level
        self.alt_sf_alpha_label = QtWidgets.QLabel('%s:' % _('Alpha Level'))
        self.alt_sf_alpha_label.setToolTip(
            _("Set the fill transparency for selection 'right to left' box.")
        )
        self.alt_sf_color_alpha_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.alt_sf_color_alpha_slider.setMinimum(0)
        self.alt_sf_color_alpha_slider.setMaximum(255)
        self.alt_sf_color_alpha_slider.setSingleStep(1)

        self.alt_sf_color_alpha_spinner = FCSpinner()
        self.alt_sf_color_alpha_spinner.setMinimumWidth(70)
        self.alt_sf_color_alpha_spinner.setMinimum(0)
        self.alt_sf_color_alpha_spinner.setMaximum(255)

        self.form_box_child_8 = QtWidgets.QHBoxLayout()
        self.form_box_child_8.addWidget(self.alt_sf_color_alpha_slider)
        self.form_box_child_8.addWidget(self.alt_sf_color_alpha_spinner)

        # Plot Selection (right - left) Line Color
        self.alt_sl_color_label = QtWidgets.QLabel('%s:' % _('Sel2. Line'))
        self.alt_sl_color_label.setToolTip(
            _("Set the line color for the 'right to left' selection box.")
        )
        self.alt_sl_color_entry = FCEntry()
        self.alt_sl_color_button = QtWidgets.QPushButton()
        self.alt_sl_color_button.setFixedSize(15, 15)

        self.form_box_child_9 = QtWidgets.QHBoxLayout()
        self.form_box_child_9.addWidget(self.alt_sl_color_entry)
        self.form_box_child_9.addWidget(self.alt_sl_color_button)
        self.form_box_child_9.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        # Editor Draw Color
        self.draw_color_label = QtWidgets.QLabel('%s:' % _('Editor Draw'))
        self.alt_sf_color_label.setToolTip(
            _("Set the color for the shape.")
        )
        self.draw_color_entry = FCEntry()
        self.draw_color_button = QtWidgets.QPushButton()
        self.draw_color_button.setFixedSize(15, 15)

        self.form_box_child_10 = QtWidgets.QHBoxLayout()
        self.form_box_child_10.addWidget(self.draw_color_entry)
        self.form_box_child_10.addWidget(self.draw_color_button)
        self.form_box_child_10.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        # Editor Draw Selection Color
        self.sel_draw_color_label = QtWidgets.QLabel('%s:' % _('Editor Draw Sel.'))
        self.sel_draw_color_label.setToolTip(
            _("Set the color of the shape when selected.")
        )
        self.sel_draw_color_entry = FCEntry()
        self.sel_draw_color_button = QtWidgets.QPushButton()
        self.sel_draw_color_button.setFixedSize(15, 15)

        self.form_box_child_11 = QtWidgets.QHBoxLayout()
        self.form_box_child_11.addWidget(self.sel_draw_color_entry)
        self.form_box_child_11.addWidget(self.sel_draw_color_button)
        self.form_box_child_11.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        # Project Tab items color
        self.proj_color_label = QtWidgets.QLabel('%s:' % _('Project Items'))
        self.proj_color_label.setToolTip(
            _("Set the color of the items in Project Tab Tree.")
        )
        self.proj_color_entry = FCEntry()
        self.proj_color_button = QtWidgets.QPushButton()
        self.proj_color_button.setFixedSize(15, 15)

        self.form_box_child_12 = QtWidgets.QHBoxLayout()
        self.form_box_child_12.addWidget(self.proj_color_entry)
        self.form_box_child_12.addWidget(self.proj_color_button)
        self.form_box_child_12.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        self.proj_color_dis_label = QtWidgets.QLabel('%s:' % _('Proj. Dis. Items'))
        self.proj_color_dis_label.setToolTip(
            _("Set the color of the items in Project Tab Tree,\n"
              "for the case when the items are disabled.")
        )
        self.proj_color_dis_entry = FCEntry()
        self.proj_color_dis_button = QtWidgets.QPushButton()
        self.proj_color_dis_button.setFixedSize(15, 15)

        self.form_box_child_13 = QtWidgets.QHBoxLayout()
        self.form_box_child_13.addWidget(self.proj_color_dis_entry)
        self.form_box_child_13.addWidget(self.proj_color_dis_button)
        self.form_box_child_13.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        # Activity monitor icon
        self.activity_label = QtWidgets.QLabel('%s:' % _("Activity Icon"))
        self.activity_label.setToolTip(
            _("Select the GIF that show activity when FlatCAM is active.")
        )
        self.activity_combo = FCComboBox()
        self.activity_combo.addItems(['Ball black', 'Ball green', 'Arrow green', 'Eclipse green'])

        # Just to add empty rows
        self.spacelabel = QtWidgets.QLabel('')

        # Add (label - input field) pair to the QFormLayout
        self.form_box.addRow(self.spacelabel, self.spacelabel)

        self.form_box.addRow(self.gridx_label, self.gridx_entry)
        self.form_box.addRow(self.gridy_label, self.gridy_entry)
        self.form_box.addRow(self.snap_max_label, self.snap_max_dist_entry)

        self.form_box.addRow(self.workspace_lbl, self.workspace_cb)
        self.form_box.addRow(self.workspace_type_lbl, self.wk_cb)
        self.form_box.addRow(self.spacelabel, self.spacelabel)
        self.form_box.addRow(self.pf_color_label, self.form_box_child_1)
        self.form_box.addRow(self.pf_alpha_label, self.form_box_child_2)
        self.form_box.addRow(self.pl_color_label, self.form_box_child_3)
        self.form_box.addRow(self.sf_color_label, self.form_box_child_4)
        self.form_box.addRow(self.sf_alpha_label, self.form_box_child_5)
        self.form_box.addRow(self.sl_color_label, self.form_box_child_6)
        self.form_box.addRow(self.alt_sf_color_label, self.form_box_child_7)
        self.form_box.addRow(self.alt_sf_alpha_label, self.form_box_child_8)
        self.form_box.addRow(self.alt_sl_color_label, self.form_box_child_9)
        self.form_box.addRow(self.draw_color_label, self.form_box_child_10)
        self.form_box.addRow(self.sel_draw_color_label, self.form_box_child_11)
        self.form_box.addRow(QtWidgets.QLabel(""))
        self.form_box.addRow(self.proj_color_label, self.form_box_child_12)
        self.form_box.addRow(self.proj_color_dis_label, self.form_box_child_13)

        self.form_box.addRow(self.activity_label, self.activity_combo)

        self.form_box.addRow(self.spacelabel, self.spacelabel)

        # Add the QFormLayout that holds the Application general defaults
        # to the main layout of this TAB
        self.layout.addLayout(self.form_box)


class GeneralGUISetGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        super(GeneralGUISetGroupUI, self).__init__(self)

        self.setTitle(str(_("GUI Settings")))

        # Create a form layout for the Application general settings
        self.form_box = QtWidgets.QFormLayout()

        # Layout selection
        self.layout_label = QtWidgets.QLabel('%s:' % _('Layout'))
        self.layout_label.setToolTip(
            _("Select an layout for FlatCAM.\n"
              "It is applied immediately.")
        )
        self.layout_combo = FCComboBox()
        # don't translate the QCombo items as they are used in QSettings and identified by name
        self.layout_combo.addItem("standard")
        self.layout_combo.addItem("compact")

        # Set the current index for layout_combo
        settings = QSettings("Open Source", "FlatCAM")
        if settings.contains("layout"):
            layout = settings.value('layout', type=str)
            idx = self.layout_combo.findText(layout.capitalize())
            self.layout_combo.setCurrentIndex(idx)

        # Style selection
        self.style_label = QtWidgets.QLabel('%s:' % _('Style'))
        self.style_label.setToolTip(
            _("Select an style for FlatCAM.\n"
              "It will be applied at the next app start.")
        )
        self.style_combo = FCComboBox()
        self.style_combo.addItems(QtWidgets.QStyleFactory.keys())
        # find current style
        index = self.style_combo.findText(QtWidgets.qApp.style().objectName(), QtCore.Qt.MatchFixedString)
        self.style_combo.setCurrentIndex(index)
        self.style_combo.activated[str].connect(self.handle_style)

        # Enable High DPI Support
        self.hdpi_label = QtWidgets.QLabel('%s:' % _('HDPI Support'))
        self.hdpi_label.setToolTip(
            _("Enable High DPI support for FlatCAM.\n"
              "It will be applied at the next app start.")
        )
        self.hdpi_cb = FCCheckBox()

        settings = QSettings("Open Source", "FlatCAM")
        if settings.contains("hdpi"):
            self.hdpi_cb.set_value(settings.value('hdpi', type=int))
        else:
            self.hdpi_cb.set_value(False)
        self.hdpi_cb.stateChanged.connect(self.handle_hdpi)

        # Clear Settings
        self.clear_label = QtWidgets.QLabel('%s:' % _('Clear GUI Settings'))
        self.clear_label.setToolTip(
            _("Clear the GUI settings for FlatCAM,\n"
              "such as: layout, gui state, style, hdpi support etc.")
        )
        self.clear_btn = FCButton(_("Clear"))
        self.clear_btn.clicked.connect(self.handle_clear)

        # Enable Hover box
        self.hover_label = QtWidgets.QLabel('%s:' % _('Hover Shape'))
        self.hover_label.setToolTip(
            _("Enable display of a hover shape for FlatCAM objects.\n"
              "It is displayed whenever the mouse cursor is hovering\n"
              "over any kind of not-selected object.")
        )
        self.hover_cb = FCCheckBox()

        # Enable Selection box
        self.selection_label = QtWidgets.QLabel('%s:' % _('Sel. Shape'))
        self.selection_label.setToolTip(
            _("Enable the display of a selection shape for FlatCAM objects.\n"
              "It is displayed whenever the mouse selects an object\n"
              "either by clicking or dragging mouse from left to right or\n"
              "right to left.")
        )
        self.selection_cb = FCCheckBox()

        # Notebook Font Size
        self.notebook_font_size_label = QtWidgets.QLabel('%s:' % _('NB Font Size'))
        self.notebook_font_size_label.setToolTip(
            _("This sets the font size for the elements found in the Notebook.\n"
              "The notebook is the collapsible area in the left side of the GUI,\n"
              "and include the Project, Selected and Tool tabs.")
        )

        self.notebook_font_size_spinner = FCSpinner()
        self.notebook_font_size_spinner.setRange(8, 40)
        self.notebook_font_size_spinner.setWrapping(True)

        settings = QSettings("Open Source", "FlatCAM")
        if settings.contains("notebook_font_size"):
            self.notebook_font_size_spinner.set_value(settings.value('notebook_font_size', type=int))
        else:
            self.notebook_font_size_spinner.set_value(12)

        # Axis Font Size
        self.axis_font_size_label = QtWidgets.QLabel('%s:' % _('Axis Font Size'))
        self.axis_font_size_label.setToolTip(
            _("This sets the font size for canvas axis.")
        )

        self.axis_font_size_spinner = FCSpinner()
        self.axis_font_size_spinner.setRange(8, 40)
        self.axis_font_size_spinner.setWrapping(True)

        settings = QSettings("Open Source", "FlatCAM")
        if settings.contains("axis_font_size"):
            self.axis_font_size_spinner.set_value(settings.value('axis_font_size', type=int))
        else:
            self.axis_font_size_spinner.set_value(8)

        # TextBox Font Size
        self.textbox_font_size_label = QtWidgets.QLabel('%s:' % _('Textbox Font Size'))
        self.textbox_font_size_label.setToolTip(
            _("This sets the font size for the Textbox GUI\n"
              "elements that are used in FlatCAM.")
        )

        self.textbox_font_size_spinner = FCSpinner()
        self.textbox_font_size_spinner.setRange(8, 40)
        self.textbox_font_size_spinner.setWrapping(True)

        settings = QSettings("Open Source", "FlatCAM")
        if settings.contains("textbox_font_size"):
            self.textbox_font_size_spinner.set_value(settings.value('textbox_font_size', type=int))
        else:
            self.textbox_font_size_spinner.set_value(10)

        # Just to add empty rows
        self.spacelabel = QtWidgets.QLabel('')

        # Splash Screen
        self.splash_label = QtWidgets.QLabel('%s:' % _('Splash Screen'))
        self.splash_label.setToolTip(
            _("Enable display of the splash screen at application startup.")
        )
        self.splash_cb = FCCheckBox()
        settings = QSettings("Open Source", "FlatCAM")
        if settings.value("splash_screen"):
            self.splash_cb.set_value(True)
        else:
            self.splash_cb.set_value(False)

        # Sys Tray Icon
        self.systray_label = QtWidgets.QLabel('%s:' % _('Sys Tray Icon'))
        self.systray_label.setToolTip(
            _("Enable display of FlatCAM icon in Sys Tray.")
        )
        self.systray_cb = FCCheckBox()

        # Shell StartUp CB
        self.shell_startup_label = QtWidgets.QLabel('%s:' % _('Shell at StartUp'))
        self.shell_startup_label.setToolTip(
            _("Check this box if you want the shell to\n"
              "start automatically at startup.")
        )
        self.shell_startup_cb = FCCheckBox(label='')
        self.shell_startup_cb.setToolTip(
            _("Check this box if you want the shell to\n"
              "start automatically at startup.")
        )

        # Project at StartUp CB
        self.project_startup_label = QtWidgets.QLabel('%s:' % _('Project at StartUp'))
        self.project_startup_label.setToolTip(
            _("Check this box if you want the project/selected/tool tab area to\n"
              "to be shown automatically at startup.")
        )
        self.project_startup_cb = FCCheckBox(label='')
        self.project_startup_cb.setToolTip(
            _("Check this box if you want the project/selected/tool tab area to\n"
              "to be shown automatically at startup.")
        )

        # Project autohide CB
        self.project_autohide_label = QtWidgets.QLabel('%s:' % _('Project AutoHide'))
        self.project_autohide_label.setToolTip(
            _("Check this box if you want the project/selected/tool tab area to\n"
              "hide automatically when there are no objects loaded and\n"
              "to show whenever a new object is created.")
        )
        self.project_autohide_cb = FCCheckBox(label='')
        self.project_autohide_cb.setToolTip(
            _("Check this box if you want the project/selected/tool tab area to\n"
              "hide automatically when there are no objects loaded and\n"
              "to show whenever a new object is created.")
        )

        # Enable/Disable ToolTips globally
        self.toggle_tooltips_label = QtWidgets.QLabel('<b>%s:</b>' % _('Enable ToolTips'))
        self.toggle_tooltips_label.setToolTip(
            _("Check this box if you want to have toolTips displayed\n"
              "when hovering with mouse over items throughout the App.")
        )
        self.toggle_tooltips_cb = FCCheckBox(label='')
        self.toggle_tooltips_cb.setToolTip(
            _("Check this box if you want to have toolTips displayed\n"
              "when hovering with mouse over items throughout the App.")
        )

        # Mouse Cursor Shape
        self.cursor_lbl = QtWidgets.QLabel('%s:' % _('Mouse Cursor'))
        self.cursor_lbl.setToolTip(
           _("Choose a mouse cursor shape.\n"
             "- Small -> with a customizable size.\n"
             "- Big -> Infinite lines")
        )

        self.cursor_radio = RadioSet([
            {"label": _("Small"), "value": "small"},
            {"label": _("Big"), "value": "big"}
        ], orientation='horizontal', stretch=False)

        self.cursor_size_lbl = QtWidgets.QLabel('%s:' % _('Mouse Cursor Size'))
        self.cursor_size_lbl.setToolTip(
           _("Set the size of the mouse cursor, in pixels.")
        )

        self.cursor_size_entry = FCSpinner()
        self.cursor_size_entry.set_range(10, 70)
        self.cursor_size_entry.setWrapping(True)


        # Add (label - input field) pair to the QFormLayout
        self.form_box.addRow(self.spacelabel, self.spacelabel)

        self.form_box.addRow(self.layout_label, self.layout_combo)
        self.form_box.addRow(self.style_label, self.style_combo)
        self.form_box.addRow(self.hdpi_label, self.hdpi_cb)
        self.form_box.addRow(self.clear_label, self.clear_btn)
        self.form_box.addRow(self.hover_label, self.hover_cb)
        self.form_box.addRow(self.selection_label, self.selection_cb)
        self.form_box.addRow(QtWidgets.QLabel(''))
        self.form_box.addRow(self.notebook_font_size_label, self.notebook_font_size_spinner)
        self.form_box.addRow(self.axis_font_size_label, self.axis_font_size_spinner)
        self.form_box.addRow(self.textbox_font_size_label, self.textbox_font_size_spinner)
        self.form_box.addRow(QtWidgets.QLabel(''))
        self.form_box.addRow(self.splash_label, self.splash_cb)
        self.form_box.addRow(self.systray_label, self.systray_cb)
        self.form_box.addRow(self.shell_startup_label, self.shell_startup_cb)
        self.form_box.addRow(self.project_startup_label, self.project_startup_cb)
        self.form_box.addRow(self.project_autohide_label, self.project_autohide_cb)
        self.form_box.addRow(QtWidgets.QLabel(''))
        self.form_box.addRow(self.toggle_tooltips_label, self.toggle_tooltips_cb)
        self.form_box.addRow(self.cursor_lbl, self.cursor_radio)
        self.form_box.addRow(self.cursor_size_lbl, self.cursor_size_entry)

        # Add the QFormLayout that holds the Application general defaults
        # to the main layout of this TAB
        self.layout.addLayout(self.form_box)

        # Delete confirmation
        self.delete_conf_cb = FCCheckBox(_('Delete object confirmation'))
        self.delete_conf_cb.setToolTip(
            _("When checked the application will ask for user confirmation\n"
              "whenever the Delete object(s) event is triggered, either by\n"
              "menu shortcut or key shortcut.")
        )
        self.layout.addWidget(self.delete_conf_cb)

        self.layout.addStretch()

    def handle_style(self, style):
        # set current style
        settings = QSettings("Open Source", "FlatCAM")
        settings.setValue('style', style)

        # This will write the setting to the platform specific storage.
        del settings

    def handle_hdpi(self, state):
        # set current HDPI
        settings = QSettings("Open Source", "FlatCAM")
        settings.setValue('hdpi', state)

        # This will write the setting to the platform specific storage.
        del settings

    def handle_clear(self):
        msgbox = QtWidgets.QMessageBox()
        msgbox.setText(_("Are you sure you want to delete the GUI Settings? "
                         "\n")
                       )
        msgbox.setWindowTitle(_("Clear GUI Settings"))
        msgbox.setWindowIcon(QtGui.QIcon('share/trash32.png'))
        bt_yes = msgbox.addButton(_('Yes'), QtWidgets.QMessageBox.YesRole)
        bt_no = msgbox.addButton(_('No'), QtWidgets.QMessageBox.NoRole)

        msgbox.setDefaultButton(bt_no)
        msgbox.exec_()
        response = msgbox.clickedButton()

        if response == bt_yes:
            settings = QSettings("Open Source", "FlatCAM")
            for key in settings.allKeys():
                settings.remove(key)
            # This will write the setting to the platform specific storage.
            del settings


class GeneralAppPrefGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        super(GeneralAppPrefGroupUI, self).__init__(self)

        self.setTitle(str(_("App Preferences")))

        # Create a form layout for the Application general settings
        self.form_box = QtWidgets.QFormLayout()

        # Units for FlatCAM
        self.unitslabel = QtWidgets.QLabel('<span style="color:red;"><b>%s:</b></span>' % _('Units'))
        self.unitslabel.setToolTip(_("The default value for FlatCAM units.\n"
                                     "Whatever is selected here is set every time\n"
                                     "FLatCAM is started."))
        self.units_radio = RadioSet([{'label': _('IN'), 'value': 'IN'},
                                     {'label': _('MM'), 'value': 'MM'}])

        # Graphic Engine for FlatCAM
        self.ge_label = QtWidgets.QLabel('<b>%s:</b>' % _('Graphic Engine'))
        self.ge_label.setToolTip(_("Choose what graphic engine to use in FlatCAM.\n"
                                   "Legacy(2D) -> reduced functionality, slow performance but enhanced compatibility.\n"
                                   "OpenGL(3D) -> full functionality, high performance\n"
                                   "Some graphic cards are too old and do not work in OpenGL(3D) mode, like:\n"
                                   "Intel HD3000 or older. In this case the plot area will be black therefore\n"
                                   "use the Legacy(2D) mode."))
        self.ge_radio = RadioSet([{'label': _('Legacy(2D)'), 'value': '2D'},
                                  {'label': _('OpenGL(3D)'), 'value': '3D'}])

        # Application Level for FlatCAM
        self.app_level_label = QtWidgets.QLabel('<span style="color:red;"><b>%s:</b></span>' % _('APP. LEVEL'))
        self.app_level_label.setToolTip(_("Choose the default level of usage for FlatCAM.\n"
                                          "BASIC level -> reduced functionality, best for beginner's.\n"
                                          "ADVANCED level -> full functionality.\n\n"
                                          "The choice here will influence the parameters in\n"
                                          "the Selected Tab for all kinds of FlatCAM objects."))
        self.app_level_radio = RadioSet([{'label': _('Basic'), 'value': 'b'},
                                         {'label': _('Advanced'), 'value': 'a'}])

        # Application Level for FlatCAM
        self.portability_label = QtWidgets.QLabel('%s:' % _('Portable app'))
        self.portability_label.setToolTip(_("Choose if the application should run as portable.\n\n"
                                            "If Checked the application will run portable,\n"
                                            "which means that the preferences files will be saved\n"
                                            "in the application folder, in the lib\\config subfolder."))
        self.portability_cb = FCCheckBox()

        # Languages for FlatCAM
        self.languagelabel = QtWidgets.QLabel('<b>%s:</b>' % _('Languages'))
        self.languagelabel.setToolTip(_("Set the language used throughout FlatCAM."))
        self.language_cb = FCComboBox()
        self.languagespace = QtWidgets.QLabel('')
        self.language_apply_btn = FCButton(_("Apply Language"))
        self.language_apply_btn.setToolTip(_("Set the language used throughout FlatCAM.\n"
                                             "The app will restart after click."
                                             "Windows: When FlatCAM is installed in Program Files\n"
                                             "directory, it is possible that the app will not\n"
                                             "restart after the button is clicked due of Windows\n"
                                             "security features. In this case the language will be\n"
                                             "applied at the next app start."))

        # Version Check CB
        self.version_check_label = QtWidgets.QLabel('%s:' % _('Version Check'))
        self.version_check_label.setToolTip(
            _("Check this box if you want to check\n"
              "for a new version automatically at startup.")
        )
        self.version_check_cb = FCCheckBox(label='')
        self.version_check_cb.setToolTip(
            _("Check this box if you want to check\n"
              "for a new version automatically at startup.")
        )

        # Send Stats CB
        self.send_stats_label = QtWidgets.QLabel('%s:' % _('Send Stats'))
        self.send_stats_label.setToolTip(
            _("Check this box if you agree to send anonymous\n"
              "stats automatically at startup, to help improve FlatCAM.")
        )
        self.send_stats_cb = FCCheckBox(label='')
        self.send_stats_cb.setToolTip(
            _("Check this box if you agree to send anonymous\n"
              "stats automatically at startup, to help improve FlatCAM.")
        )

        self.ois_version_check = OptionalInputSection(self.version_check_cb, [self.send_stats_cb])

        # Select mouse pan button
        self.panbuttonlabel = QtWidgets.QLabel('<b>%s:</b>' % _('Pan Button'))
        self.panbuttonlabel.setToolTip(_("Select the mouse button to use for panning:\n"
                                         "- MMB --> Middle Mouse Button\n"
                                         "- RMB --> Right Mouse Button"))
        self.pan_button_radio = RadioSet([{'label': _('MMB'), 'value': '3'},
                                          {'label': _('RMB'), 'value': '2'}])

        # Multiple Selection Modifier Key
        self.mselectlabel = QtWidgets.QLabel('<b>%s:</b>' % _('Multiple Sel'))
        self.mselectlabel.setToolTip(_("Select the key used for multiple selection."))
        self.mselect_radio = RadioSet([{'label': _('CTRL'), 'value': 'Control'},
                                       {'label': _('SHIFT'), 'value': 'Shift'}])

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
        self.worker_number_sb.setToolTip(
            _("The number of Qthreads made available to the App.\n"
              "A bigger number may finish the jobs more quickly but\n"
              "depending on your computer speed, may make the App\n"
              "unresponsive. Can have a value between 2 and 16.\n"
              "Default value is 2.\n"
              "After change, it will be applied at next App start.")
        )
        self.worker_number_sb.set_range(2, 16)

        # Geometric tolerance
        tol_label = QtWidgets.QLabel('%s:' % _("Geo Tolerance"))
        tol_label.setToolTip(_(
            "This value can counter the effect of the Circle Steps\n"
            "parameter. Default value is 0.01.\n"
            "A lower value will increase the detail both in image\n"
            "and in Gcode for the circles, with a higher cost in\n"
            "performance. Higher value will provide more\n"
            "performance at the expense of level of detail."
        ))
        self.tol_entry = FCEntry()
        self.tol_entry.setToolTip(_(
            "This value can counter the effect of the Circle Steps\n"
            "parameter. Default value is 0.01.\n"
            "A lower value will increase the detail both in image\n"
            "and in Gcode for the circles, with a higher cost in\n"
            "performance. Higher value will provide more\n"
            "performance at the expense of level of detail."
        ))
        # Just to add empty rows
        self.spacelabel = QtWidgets.QLabel('')

        # Add (label - input field) pair to the QFormLayout
        self.form_box.addRow(self.unitslabel, self.units_radio)
        self.form_box.addRow(self.ge_label, self.ge_radio)
        self.form_box.addRow(QtWidgets.QLabel(''))
        self.form_box.addRow(self.app_level_label, self.app_level_radio)
        self.form_box.addRow(self.portability_label, self.portability_cb)
        self.form_box.addRow(QtWidgets.QLabel(''))

        self.form_box.addRow(self.languagelabel, self.language_cb)
        self.form_box.addRow(self.languagespace, self.language_apply_btn)

        self.form_box.addRow(self.spacelabel, self.spacelabel)
        self.form_box.addRow(self.version_check_label, self.version_check_cb)
        self.form_box.addRow(self.send_stats_label, self.send_stats_cb)

        self.form_box.addRow(self.panbuttonlabel, self.pan_button_radio)
        self.form_box.addRow(self.mselectlabel, self.mselect_radio)
        self.form_box.addRow(self.worker_number_label, self.worker_number_sb)
        self.form_box.addRow(tol_label, self.tol_entry)

        self.form_box.addRow(self.spacelabel, self.spacelabel)

        # Add the QFormLayout that holds the Application general defaults
        # to the main layout of this TAB
        self.layout.addLayout(self.form_box)

        # Open behavior
        self.open_style_cb = FCCheckBox('%s' % _('"Open" behavior'))
        self.open_style_cb.setToolTip(
            _("When checked the path for the last saved file is used when saving files,\n"
              "and the path for the last opened file is used when opening files.\n\n"
              "When unchecked the path for opening files is the one used last: either the\n"
              "path for saving files or the path for opening files.")
        )
        # self.advanced_cb.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.layout.addWidget(self.open_style_cb)

        # Save compressed project CB
        self.save_type_cb = FCCheckBox(_('Save Compressed Project'))
        self.save_type_cb.setToolTip(
            _("Whether to save a compressed or uncompressed project.\n"
              "When checked it will save a compressed FlatCAM project.")
        )
        # self.advanced_cb.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.layout.addWidget(self.save_type_cb)

        hlay1 = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay1)

        # Project LZMA Comppression Level
        self.compress_combo = FCComboBox()
        self.compress_label = QtWidgets.QLabel('%s:' % _('Compression Level'))
        self.compress_label.setToolTip(
            _("The level of compression used when saving\n"
              "a FlatCAM project. Higher value means better compression\n"
              "but require more RAM usage and more processing time.")
        )
        # self.advanced_cb.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.compress_combo.addItems([str(i) for i in range(10)])

        hlay1.addWidget(self.compress_label)
        hlay1.addWidget(self.compress_combo)

        self.proj_ois = OptionalInputSection(self.save_type_cb, [self.compress_label, self.compress_combo], True)

        self.form_box_2 = QtWidgets.QFormLayout()
        self.layout.addLayout(self.form_box_2)

        self.layout.addStretch()

        if sys.platform != 'win32':
            self.portability_label.hide()
            self.portability_cb.hide()


class GerberGenPrefGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        # OptionsGroupUI.__init__(self, "Gerber General Preferences", parent=parent)
        super(GerberGenPrefGroupUI, self).__init__(self)

        self.setTitle(str(_("Gerber General")))

        # ## Plot options
        self.plot_options_label = QtWidgets.QLabel("<b>%s:</b>" % _("Plot Options"))
        self.layout.addWidget(self.plot_options_label)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        # Solid CB
        self.solid_cb = FCCheckBox(label='%s' % _('Solid'))
        self.solid_cb.setToolTip(
            _("Solid color polygons.")
        )
        grid0.addWidget(self.solid_cb, 0, 0)

        # Multicolored CB
        self.multicolored_cb = FCCheckBox(label='%s' % _('M-Color'))
        self.multicolored_cb.setToolTip(
            _("Draw polygons in different colors.")
        )
        grid0.addWidget(self.multicolored_cb, 0, 1)

        # Plot CB
        self.plot_cb = FCCheckBox(label='%s' % _('Plot'))
        self.plot_options_label.setToolTip(
            _("Plot (show) this object.")
        )
        grid0.addWidget(self.plot_cb, 0, 2)

        # Number of circle steps for circular aperture linear approximation
        self.circle_steps_label = QtWidgets.QLabel('%s:' % _("Circle Steps"))
        self.circle_steps_label.setToolTip(
            _("The number of circle steps for Gerber \n"
              "circular aperture linear approximation.")
        )
        self.circle_steps_entry = IntEntry()
        grid0.addWidget(self.circle_steps_label, 1, 0)
        grid0.addWidget(self.circle_steps_entry, 1, 1, 1, 2)

        grid0.addWidget(QtWidgets.QLabel(''), 2, 0, 1, 3)

        # Default format for Gerber
        self.gerber_default_label = QtWidgets.QLabel('<b>%s:</b>' % _('Default Values'))
        self.gerber_default_label.setToolTip(
            _("Those values will be used as fallback values\n"
              "in case that they are not found in the Gerber file.")
        )

        grid0.addWidget(self.gerber_default_label, 3, 0, 1, 3)

        # Gerber Units
        self.gerber_units_label = QtWidgets.QLabel('%s:' % _('Units'))
        self.gerber_units_label.setToolTip(
            _("The units used in the Gerber file.")
        )

        self.gerber_units_radio = RadioSet([{'label': _('INCH'), 'value': 'IN'},
                                            {'label': _('MM'), 'value': 'MM'}])
        self.gerber_units_radio.setToolTip(
            _("The units used in the Gerber file.")
        )

        grid0.addWidget(self.gerber_units_label, 4, 0)
        grid0.addWidget(self.gerber_units_radio, 4, 1, 1, 2)

        # Gerber Zeros
        self.gerber_zeros_label = QtWidgets.QLabel('%s:' % _('Zeros'))
        self.gerber_zeros_label.setAlignment(QtCore.Qt.AlignLeft)
        self.gerber_zeros_label.setToolTip(
            _("This sets the type of Gerber zeros.\n"
              "If LZ then Leading Zeros are removed and\n"
              "Trailing Zeros are kept.\n"
              "If TZ is checked then Trailing Zeros are removed\n"
              "and Leading Zeros are kept.")
        )

        self.gerber_zeros_radio = RadioSet([{'label': _('LZ'), 'value': 'L'},
                                            {'label': _('TZ'), 'value': 'T'}])
        self.gerber_zeros_radio.setToolTip(
            _("This sets the type of Gerber zeros.\n"
              "If LZ then Leading Zeros are removed and\n"
              "Trailing Zeros are kept.\n"
              "If TZ is checked then Trailing Zeros are removed\n"
              "and Leading Zeros are kept.")
        )

        grid0.addWidget(self.gerber_zeros_label, 5, 0)
        grid0.addWidget(self.gerber_zeros_radio, 5, 1, 1, 2)

        self.layout.addStretch()


class GerberOptPrefGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        # OptionsGroupUI.__init__(self, "Gerber Options Preferences", parent=parent)
        super(GerberOptPrefGroupUI, self).__init__(self)

        self.setTitle(str(_("Gerber Options")))

        # ## Isolation Routing
        self.isolation_routing_label = QtWidgets.QLabel("<b>%s:</b>" % _("Isolation Routing"))
        self.isolation_routing_label.setToolTip(
            _("Create a Geometry object with\n"
              "toolpaths to cut outside polygons.")
        )
        self.layout.addWidget(self.isolation_routing_label)

        # Cutting Tool Diameter
        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        tdlabel = QtWidgets.QLabel('%s:' % _('Tool dia'))
        tdlabel.setToolTip(
            _("Diameter of the cutting tool.")
        )
        grid0.addWidget(tdlabel, 0, 0)
        self.iso_tool_dia_entry = LengthEntry()
        grid0.addWidget(self.iso_tool_dia_entry, 0, 1)

        # Nr of passes
        passlabel = QtWidgets.QLabel('%s:' % _('# Passes'))
        passlabel.setToolTip(
            _("Width of the isolation gap in\n"
              "number (integer) of tool widths.")
        )
        grid0.addWidget(passlabel, 1, 0)
        self.iso_width_entry = FCSpinner()
        self.iso_width_entry.setRange(1, 999)
        grid0.addWidget(self.iso_width_entry, 1, 1)

        # Pass overlap
        overlabel = QtWidgets.QLabel('%s:' % _('Pass overlap'))
        overlabel.setToolTip(
            _("How much (fraction) of the tool width to overlap each tool pass.\n"
              "Example:\n"
              "A value here of 0.25 means an overlap of 25%% from the tool diameter found above.")
        )
        grid0.addWidget(overlabel, 2, 0)
        self.iso_overlap_entry = FCDoubleSpinner()
        self.iso_overlap_entry.set_precision(3)
        self.iso_overlap_entry.setWrapping(True)
        self.iso_overlap_entry.setRange(0.000, 0.999)
        self.iso_overlap_entry.setSingleStep(0.1)
        grid0.addWidget(self.iso_overlap_entry, 2, 1)

        # Milling Type
        milling_type_label = QtWidgets.QLabel('%s:' % _('Milling Type'))
        milling_type_label.setToolTip(
            _("Milling type:\n"
              "- climb / best for precision milling and to reduce tool usage\n"
              "- conventional / useful when there is no backlash compensation")
        )
        grid0.addWidget(milling_type_label, 3, 0)
        self.milling_type_radio = RadioSet([{'label': _('Climb'), 'value': 'cl'},
                                            {'label': _('Conv.'), 'value': 'cv'}])
        grid0.addWidget(self.milling_type_radio, 3, 1)

        # Combine passes
        self.combine_passes_cb = FCCheckBox(label=_('Combine Passes'))
        self.combine_passes_cb.setToolTip(
            _("Combine all passes into one object")
        )
        grid0.addWidget(self.combine_passes_cb, 4, 0, 1, 2)

        # ## Clear non-copper regions
        self.clearcopper_label = QtWidgets.QLabel("<b>%s:</b>" % _("Non-copper regions"))
        self.clearcopper_label.setToolTip(
            _("Create polygons covering the\n"
              "areas without copper on the PCB.\n"
              "Equivalent to the inverse of this\n"
              "object. Can be used to remove all\n"
              "copper from a specified region.")
        )
        self.layout.addWidget(self.clearcopper_label)

        grid1 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid1)

        # Margin
        bmlabel = QtWidgets.QLabel('%s:' % _('Boundary Margin'))
        bmlabel.setToolTip(
            _("Specify the edge of the PCB\n"
              "by drawing a box around all\n"
              "objects with this minimum\n"
              "distance.")
        )
        grid1.addWidget(bmlabel, 0, 0)
        self.noncopper_margin_entry = LengthEntry()
        grid1.addWidget(self.noncopper_margin_entry, 0, 1)

        # Rounded corners
        self.noncopper_rounded_cb = FCCheckBox(label=_("Rounded Geo"))
        self.noncopper_rounded_cb.setToolTip(
            _("Resulting geometry will have rounded corners.")
        )
        grid1.addWidget(self.noncopper_rounded_cb, 1, 0, 1, 2)

        # ## Bounding box
        self.boundingbox_label = QtWidgets.QLabel('<b>%s:</b>' % _('Bounding Box'))
        self.layout.addWidget(self.boundingbox_label)

        grid2 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid2)

        bbmargin = QtWidgets.QLabel('%s:' % _('Boundary Margin'))
        bbmargin.setToolTip(
            _("Distance of the edges of the box\n"
              "to the nearest polygon.")
        )
        grid2.addWidget(bbmargin, 0, 0)
        self.bbmargin_entry = LengthEntry()
        grid2.addWidget(self.bbmargin_entry, 0, 1)

        self.bbrounded_cb = FCCheckBox(label='%s' % _("Rounded Geo"))
        self.bbrounded_cb.setToolTip(
            _("If the bounding box is \n"
              "to have rounded corners\n"
              "their radius is equal to\n"
              "the margin.")
        )
        grid2.addWidget(self.bbrounded_cb, 1, 0, 1, 2)
        self.layout.addStretch()


class GerberAdvOptPrefGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        # OptionsGroupUI.__init__(self, "Gerber Adv. Options Preferences", parent=parent)
        super(GerberAdvOptPrefGroupUI, self).__init__(self)

        self.setTitle(str(_("Gerber Adv. Options")))

        # ## Advanced Gerber Parameters
        self.adv_param_label = QtWidgets.QLabel('<b>%s:</b>' % _('Advanced Options'))
        self.adv_param_label.setToolTip(
            _("A list of Gerber advanced parameters.\n"
              "Those parameters are available only for\n"
              "Advanced App. Level.")
        )
        self.layout.addWidget(self.adv_param_label)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        # Follow Attribute
        self.follow_cb = FCCheckBox(label=_('"Follow"'))
        self.follow_cb.setToolTip(
            _("Generate a 'Follow' geometry.\n"
              "This means that it will cut through\n"
              "the middle of the trace.")
        )
        grid0.addWidget(self.follow_cb, 0, 0, 1, 2)

        # Aperture Table Visibility CB
        self.aperture_table_visibility_cb = FCCheckBox(label=_('Table Show/Hide'))
        self.aperture_table_visibility_cb.setToolTip(
            _("Toggle the display of the Gerber Apertures Table.\n"
              "Also, on hide, it will delete all mark shapes\n"
              "that are drawn on canvas.")

        )
        grid0.addWidget(self.aperture_table_visibility_cb, 1, 0, 1, 2)

        # Tool Type
        self.tool_type_label = QtWidgets.QLabel('<b>%s</b>' % _('Tool Type'))
        self.tool_type_label.setToolTip(
            _("Choose what tool to use for Gerber isolation:\n"
              "'Circular' or 'V-shape'.\n"
              "When the 'V-shape' is selected then the tool\n"
              "diameter will depend on the chosen cut depth.")
        )
        self.tool_type_radio = RadioSet([{'label': 'Circular', 'value': 'circular'},
                                         {'label': 'V-Shape', 'value': 'v'}])

        grid0.addWidget(self.tool_type_label, 2, 0)
        grid0.addWidget(self.tool_type_radio, 2, 1, 1, 2)

        # Tip Dia
        self.tipdialabel = QtWidgets.QLabel('%s:' % _('V-Tip Dia'))
        self.tipdialabel.setToolTip(
            _("The tip diameter for V-Shape Tool")
        )
        self.tipdia_spinner = FCDoubleSpinner()
        self.tipdia_spinner.set_range(-99.9999, 99.9999)
        self.tipdia_spinner.setSingleStep(0.1)
        self.tipdia_spinner.setWrapping(True)
        grid0.addWidget(self.tipdialabel, 3, 0)
        grid0.addWidget(self.tipdia_spinner, 3, 1, 1, 2)

        # Tip Angle
        self.tipanglelabel = QtWidgets.QLabel('%s:' % _('V-Tip Angle'))
        self.tipanglelabel.setToolTip(
            _("The tip angle for V-Shape Tool.\n"
              "In degree.")
        )
        self.tipangle_spinner = FCSpinner()
        self.tipangle_spinner.set_range(0, 180)
        self.tipangle_spinner.setSingleStep(5)
        self.tipangle_spinner.setWrapping(True)
        grid0.addWidget(self.tipanglelabel, 4, 0)
        grid0.addWidget(self.tipangle_spinner, 4, 1, 1, 2)

        # Cut Z
        self.cutzlabel = QtWidgets.QLabel('%s:' % _('Cut Z'))
        self.cutzlabel.setToolTip(
            _("Cutting depth (negative)\n"
              "below the copper surface.")
        )
        self.cutz_spinner = FCDoubleSpinner()
        self.cutz_spinner.set_range(-99.9999, -0.0001)
        self.cutz_spinner.setSingleStep(0.1)
        self.cutz_spinner.setWrapping(True)
        grid0.addWidget(self.cutzlabel, 5, 0)
        grid0.addWidget(self.cutz_spinner, 5, 1, 1, 2)

        # Buffering Type
        buffering_label = QtWidgets.QLabel('%s:' % _('Buffering'))
        buffering_label.setToolTip(
            _("Buffering type:\n"
              "- None --> best performance, fast file loading but no so good display\n"
              "- Full --> slow file loading but good visuals. This is the default.\n"
              "<<WARNING>>: Don't change this unless you know what you are doing !!!")
        )
        self.buffering_radio = RadioSet([{'label': _('None'), 'value': 'no'},
                                         {'label': _('Full'), 'value': 'full'}])
        grid0.addWidget(buffering_label, 6, 0)
        grid0.addWidget(self.buffering_radio, 6, 1)

        # Simplification
        self.simplify_cb = FCCheckBox(label=_('Simplify'))
        self.simplify_cb.setToolTip(
            _("When checked all the Gerber polygons will be\n"
              "loaded with simplification having a set tolerance.\n"
              "<<WARNING>>: Don't change this unless you know what you are doing !!!")
                                    )
        grid0.addWidget(self.simplify_cb, 7, 0, 1, 2)

        # Simplification tolerance
        self.simplification_tol_label = QtWidgets.QLabel(_('Tolerance'))
        self.simplification_tol_label.setToolTip(_("Tolerance for polygon simplification."))

        self.simplification_tol_spinner = FCDoubleSpinner()
        self.simplification_tol_spinner.set_precision(5)
        self.simplification_tol_spinner.setWrapping(True)
        self.simplification_tol_spinner.setRange(0.00000, 0.01000)
        self.simplification_tol_spinner.setSingleStep(0.0001)

        grid0.addWidget(self.simplification_tol_label, 8, 0)
        grid0.addWidget(self.simplification_tol_spinner, 8, 1)
        self.ois_simplif = OptionalInputSection(self.simplify_cb,
                                                [self.simplification_tol_label, self.simplification_tol_spinner],
                                                logic=True)

        self.layout.addStretch()


class GerberExpPrefGroupUI(OptionsGroupUI):

    def __init__(self, parent=None):
        super(GerberExpPrefGroupUI, self).__init__(self)

        self.setTitle(str(_("Gerber Export")))

        # Plot options
        self.export_options_label = QtWidgets.QLabel("<b>%s:</b>" % _("Export Options"))
        self.export_options_label.setToolTip(
            _("The parameters set here are used in the file exported\n"
              "when using the File -> Export -> Export Gerber menu entry.")
        )
        self.layout.addWidget(self.export_options_label)

        form = QtWidgets.QFormLayout()
        self.layout.addLayout(form)

        # Gerber Units
        self.gerber_units_label = QtWidgets.QLabel('<b>%s:</b>' % _('Units'))
        self.gerber_units_label.setToolTip(
            _("The units used in the Gerber file.")
        )

        self.gerber_units_radio = RadioSet([{'label': _('INCH'), 'value': 'IN'},
                                            {'label': _('MM'), 'value': 'MM'}])
        self.gerber_units_radio.setToolTip(
            _("The units used in the Gerber file.")
        )

        form.addRow(self.gerber_units_label, self.gerber_units_radio)

        # Gerber format
        self.digits_label = QtWidgets.QLabel("<b>%s:</b>" % _("Int/Decimals"))
        self.digits_label.setToolTip(
            _("The number of digits in the whole part of the number\n"
              "and in the fractional part of the number.")
        )

        hlay1 = QtWidgets.QHBoxLayout()

        self.format_whole_entry = IntEntry()
        self.format_whole_entry.setMaxLength(1)
        self.format_whole_entry.setAlignment(QtCore.Qt.AlignRight)
        self.format_whole_entry.setMinimumWidth(30)
        self.format_whole_entry.setToolTip(
            _("This numbers signify the number of digits in\n"
              "the whole part of Gerber coordinates.")
        )
        hlay1.addWidget(self.format_whole_entry, QtCore.Qt.AlignLeft)

        gerber_separator_label = QtWidgets.QLabel(':')
        gerber_separator_label.setFixedWidth(5)
        hlay1.addWidget(gerber_separator_label, QtCore.Qt.AlignLeft)

        self.format_dec_entry = IntEntry()
        self.format_dec_entry.setMaxLength(1)
        self.format_dec_entry.setAlignment(QtCore.Qt.AlignRight)
        self.format_dec_entry.setMinimumWidth(30)
        self.format_dec_entry.setToolTip(
            _("This numbers signify the number of digits in\n"
              "the decimal part of Gerber coordinates.")
        )
        hlay1.addWidget(self.format_dec_entry, QtCore.Qt.AlignLeft)
        hlay1.addStretch()

        form.addRow(self.digits_label, hlay1)

        # Gerber Zeros
        self.zeros_label = QtWidgets.QLabel('<b>%s:</b>' % _('Zeros'))
        self.zeros_label.setAlignment(QtCore.Qt.AlignLeft)
        self.zeros_label.setToolTip(
            _("This sets the type of Gerber zeros.\n"
              "If LZ then Leading Zeros are removed and\n"
              "Trailing Zeros are kept.\n"
              "If TZ is checked then Trailing Zeros are removed\n"
              "and Leading Zeros are kept.")
        )

        self.zeros_radio = RadioSet([{'label': _('LZ'), 'value': 'L'},
                                     {'label': _('TZ'), 'value': 'T'}])
        self.zeros_radio.setToolTip(
            _("This sets the type of Gerber zeros.\n"
              "If LZ then Leading Zeros are removed and\n"
              "Trailing Zeros are kept.\n"
              "If TZ is checked then Trailing Zeros are removed\n"
              "and Leading Zeros are kept.")
        )

        form.addRow(self.zeros_label, self.zeros_radio)

        self.layout.addStretch()


class GerberEditorPrefGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        # OptionsGroupUI.__init__(self, "Gerber Adv. Options Preferences", parent=parent)
        super(GerberEditorPrefGroupUI, self).__init__(self)

        self.setTitle(str(_("Gerber Editor")))

        # Advanced Gerber Parameters
        self.param_label = QtWidgets.QLabel("<b>%s:</b>" % _("Parameters"))
        self.param_label.setToolTip(
            _("A list of Gerber Editor parameters.")
        )
        self.layout.addWidget(self.param_label)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        # Selection Limit
        self.sel_limit_label = QtWidgets.QLabel('%s:' % _("Selection limit"))
        self.sel_limit_label.setToolTip(
            _("Set the number of selected Gerber geometry\n"
              "items above which the utility geometry\n"
              "becomes just a selection rectangle.\n"
              "Increases the performance when moving a\n"
              "large number of geometric elements.")
        )
        self.sel_limit_entry = IntEntry()

        grid0.addWidget(self.sel_limit_label, 0, 0)
        grid0.addWidget(self.sel_limit_entry, 0, 1)

        # New aperture code
        self.addcode_entry_lbl = QtWidgets.QLabel('%s:' % _('New Aperture code'))
        self.addcode_entry_lbl.setToolTip(
            _("Code for the new aperture")
        )

        self.addcode_entry = FCEntry()
        self.addcode_entry.setValidator(QtGui.QIntValidator(0, 99))

        grid0.addWidget(self.addcode_entry_lbl, 1, 0)
        grid0.addWidget(self.addcode_entry, 1, 1)

        # New aperture size
        self.addsize_entry_lbl = QtWidgets.QLabel('%s:' % _('New Aperture size'))
        self.addsize_entry_lbl.setToolTip(
            _("Size for the new aperture")
        )

        self.addsize_entry = FCEntry()
        self.addsize_entry.setValidator(QtGui.QDoubleValidator(0.0001, 99.9999, 4))

        grid0.addWidget(self.addsize_entry_lbl, 2, 0)
        grid0.addWidget(self.addsize_entry, 2, 1)

        # New aperture type
        self.addtype_combo_lbl = QtWidgets.QLabel('%s:' % _('New Aperture type'))
        self.addtype_combo_lbl.setToolTip(
            _("Type for the new aperture.\n"
              "Can be 'C', 'R' or 'O'.")
        )

        self.addtype_combo = FCComboBox()
        self.addtype_combo.addItems(['C', 'R', 'O'])

        grid0.addWidget(self.addtype_combo_lbl, 3, 0)
        grid0.addWidget(self.addtype_combo, 3, 1)

        # Number of pads in a pad array
        self.grb_array_size_label = QtWidgets.QLabel('%s:' % _('Nr of pads'))
        self.grb_array_size_label.setToolTip(
            _("Specify how many pads to be in the array.")
        )

        self.grb_array_size_entry = LengthEntry()

        grid0.addWidget(self.grb_array_size_label, 4, 0)
        grid0.addWidget(self.grb_array_size_entry, 4, 1)

        self.adddim_label = QtWidgets.QLabel('%s:' % _('Aperture Dimensions'))
        self.adddim_label.setToolTip(
            _("Diameters of the cutting tools, separated by ','")
        )
        grid0.addWidget(self.adddim_label, 5, 0)
        self.adddim_entry = FCEntry()
        grid0.addWidget(self.adddim_entry, 5, 1)

        self.grb_array_linear_label = QtWidgets.QLabel('<b>%s:</b>' % _('Linear Pad Array'))
        grid0.addWidget(self.grb_array_linear_label, 6, 0, 1, 2)

        # Linear Pad Array direction
        self.grb_axis_label = QtWidgets.QLabel('%s:' % _('Linear Dir.'))
        self.grb_axis_label.setToolTip(
            _("Direction on which the linear array is oriented:\n"
              "- 'X' - horizontal axis \n"
              "- 'Y' - vertical axis or \n"
              "- 'Angle' - a custom angle for the array inclination")
        )

        self.grb_axis_radio = RadioSet([{'label': _('X'), 'value': 'X'},
                                        {'label': _('Y'), 'value': 'Y'},
                                        {'label': _('Angle'), 'value': 'A'}])

        grid0.addWidget(self.grb_axis_label, 7, 0)
        grid0.addWidget(self.grb_axis_radio, 7, 1)

        # Linear Pad Array pitch distance
        self.grb_pitch_label = QtWidgets.QLabel('%s:' % _('Pitch'))
        self.grb_pitch_label.setToolTip(
            _("Pitch = Distance between elements of the array.")
        )
        # self.drill_pitch_label.setMinimumWidth(100)
        self.grb_pitch_entry = LengthEntry()

        grid0.addWidget(self.grb_pitch_label, 8, 0)
        grid0.addWidget(self.grb_pitch_entry, 8, 1)

        # Linear Pad Array custom angle
        self.grb_angle_label = QtWidgets.QLabel('%s:' % _('Angle'))
        self.grb_angle_label.setToolTip(
            _("Angle at which each element in circular array is placed.")
        )
        self.grb_angle_entry = LengthEntry()

        grid0.addWidget(self.grb_angle_label, 9, 0)
        grid0.addWidget(self.grb_angle_entry, 9, 1)

        self.grb_array_circ_label = QtWidgets.QLabel('<b>%s:</b>' % _('Circular Pad Array'))
        grid0.addWidget(self.grb_array_circ_label, 10, 0, 1, 2)

        # Circular Pad Array direction
        self.grb_circular_direction_label = QtWidgets.QLabel('%s:' % _('Circular Dir.'))
        self.grb_circular_direction_label.setToolTip(
            _("Direction for circular array.\n"
              "Can be CW = clockwise or CCW = counter clockwise.")
        )

        self.grb_circular_dir_radio = RadioSet([{'label': _('CW'), 'value': 'CW'},
                                                {'label': _('CCW'), 'value': 'CCW'}])

        grid0.addWidget(self.grb_circular_direction_label, 11, 0)
        grid0.addWidget(self.grb_circular_dir_radio, 11, 1)

        # Circular Pad Array Angle
        self.grb_circular_angle_label = QtWidgets.QLabel('%s:' % _('Circ. Angle'))
        self.grb_circular_angle_label.setToolTip(
            _("Angle at which each element in circular array is placed.")
        )
        self.grb_circular_angle_entry = LengthEntry()

        grid0.addWidget(self.grb_circular_angle_label, 12, 0)
        grid0.addWidget(self.grb_circular_angle_entry, 12, 1)

        self.grb_array_tools_b_label = QtWidgets.QLabel('<b>%s:</b>' % _('Buffer Tool'))
        grid0.addWidget(self.grb_array_tools_b_label, 13, 0, 1, 2)

        # Buffer Distance
        self.grb_buff_label = QtWidgets.QLabel('%s:' % _('Buffer distance'))
        self.grb_buff_label.setToolTip(
            _("Distance at which to buffer the Gerber element.")
        )
        self.grb_buff_entry = LengthEntry()

        grid0.addWidget(self.grb_buff_label, 14, 0)
        grid0.addWidget(self.grb_buff_entry, 14, 1)

        self.grb_array_tools_s_label = QtWidgets.QLabel('<b>%s:</b>' % _('Scale Tool'))
        grid0.addWidget(self.grb_array_tools_s_label, 15, 0, 1, 2)

        # Scale Factor
        self.grb_scale_label = QtWidgets.QLabel('%s:' % _('Scale factor'))
        self.grb_scale_label.setToolTip(
            _("Factor to scale the Gerber element.")
        )
        self.grb_scale_entry = LengthEntry()

        grid0.addWidget(self.grb_scale_label, 16, 0)
        grid0.addWidget(self.grb_scale_entry, 16, 1)

        self.grb_array_tools_ma_label = QtWidgets.QLabel('<b>%s:</b>' % _('Mark Area Tool'))
        grid0.addWidget(self.grb_array_tools_ma_label, 17, 0, 1, 2)

        # Mark area Tool low threshold
        self.grb_ma_low_label = QtWidgets.QLabel('%s:' % _('Threshold low'))
        self.grb_ma_low_label.setToolTip(
            _("Threshold value under which the apertures are not marked.")
        )
        self.grb_ma_low_entry = LengthEntry()

        grid0.addWidget(self.grb_ma_low_label, 18, 0)
        grid0.addWidget(self.grb_ma_low_entry, 18, 1)

        # Mark area Tool high threshold
        self.grb_ma_high_label = QtWidgets.QLabel('%s:' % _('Threshold high'))
        self.grb_ma_high_label.setToolTip(
            _("Threshold value over which the apertures are not marked.")
        )
        self.grb_ma_high_entry = LengthEntry()

        grid0.addWidget(self.grb_ma_high_label, 19, 0)
        grid0.addWidget(self.grb_ma_high_entry, 19, 1)

        self.layout.addStretch()


class ExcellonGenPrefGroupUI(OptionsGroupUI):

    def __init__(self, parent=None):
        # OptionsGroupUI.__init__(self, "Excellon Options", parent=parent)
        super(ExcellonGenPrefGroupUI, self).__init__(self)

        self.setTitle(str(_("Excellon General")))

        # Plot options
        self.plot_options_label = QtWidgets.QLabel("<b>%s:</b>" % _("Plot Options"))
        self.layout.addWidget(self.plot_options_label)

        grid1 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid1)

        self.plot_cb = FCCheckBox(label=_('Plot'))
        self.plot_cb.setToolTip(
            "Plot (show) this object."
        )
        grid1.addWidget(self.plot_cb, 0, 0)

        self.solid_cb = FCCheckBox(label=_('Solid'))
        self.solid_cb.setToolTip(
            "Plot as solid circles."
        )
        grid1.addWidget(self.solid_cb, 0, 1)

        # Excellon format
        self.excellon_format_label = QtWidgets.QLabel("<b>%s:</b>" % _("Excellon Format"))
        self.excellon_format_label.setToolTip(
            _("The NC drill files, usually named Excellon files\n"
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
              "KiCAD 3:5 INCH TZ")
        )
        self.layout.addWidget(self.excellon_format_label)

        hlay1 = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay1)
        self.excellon_format_in_label = QtWidgets.QLabel('%s:' % _("INCH"))
        self.excellon_format_in_label.setAlignment(QtCore.Qt.AlignLeft)
        self.excellon_format_in_label.setToolTip(
            _("Default values for INCH are 2:4"))
        hlay1.addWidget(self.excellon_format_in_label, QtCore.Qt.AlignLeft)

        self.excellon_format_upper_in_entry = IntEntry()
        self.excellon_format_upper_in_entry.setMaxLength(1)
        self.excellon_format_upper_in_entry.setAlignment(QtCore.Qt.AlignRight)
        self.excellon_format_upper_in_entry.setMinimumWidth(30)
        self.excellon_format_upper_in_entry.setToolTip(
           _("This numbers signify the number of digits in\n"
             "the whole part of Excellon coordinates.")
        )
        hlay1.addWidget(self.excellon_format_upper_in_entry, QtCore.Qt.AlignLeft)

        excellon_separator_in_label = QtWidgets.QLabel(':')
        excellon_separator_in_label.setFixedWidth(5)
        hlay1.addWidget(excellon_separator_in_label, QtCore.Qt.AlignLeft)

        self.excellon_format_lower_in_entry = IntEntry()
        self.excellon_format_lower_in_entry.setMaxLength(1)
        self.excellon_format_lower_in_entry.setAlignment(QtCore.Qt.AlignRight)
        self.excellon_format_lower_in_entry.setMinimumWidth(30)
        self.excellon_format_lower_in_entry.setToolTip(
            _("This numbers signify the number of digits in\n"
              "the decimal part of Excellon coordinates.")
        )
        hlay1.addWidget(self.excellon_format_lower_in_entry, QtCore.Qt.AlignLeft)
        hlay1.addStretch()

        hlay2 = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay2)
        self.excellon_format_mm_label = QtWidgets.QLabel('%s:' % _("METRIC"))
        self.excellon_format_mm_label.setAlignment(QtCore.Qt.AlignLeft)
        self.excellon_format_mm_label.setToolTip(
            _("Default values for METRIC are 3:3"))
        hlay2.addWidget(self.excellon_format_mm_label, QtCore.Qt.AlignLeft)

        self.excellon_format_upper_mm_entry = IntEntry()
        self.excellon_format_upper_mm_entry.setMaxLength(1)
        self.excellon_format_upper_mm_entry.setAlignment(QtCore.Qt.AlignRight)
        self.excellon_format_upper_mm_entry.setMinimumWidth(30)
        self.excellon_format_upper_mm_entry.setToolTip(
            _("This numbers signify the number of digits in\n"
              "the whole part of Excellon coordinates.")
        )
        hlay2.addWidget(self.excellon_format_upper_mm_entry, QtCore.Qt.AlignLeft)

        excellon_separator_mm_label = QtWidgets.QLabel(':')
        excellon_separator_mm_label.setFixedWidth(5)
        hlay2.addWidget(excellon_separator_mm_label, QtCore.Qt.AlignLeft)

        self.excellon_format_lower_mm_entry = IntEntry()
        self.excellon_format_lower_mm_entry.setMaxLength(1)
        self.excellon_format_lower_mm_entry.setAlignment(QtCore.Qt.AlignRight)
        self.excellon_format_lower_mm_entry.setMinimumWidth(30)
        self.excellon_format_lower_mm_entry.setToolTip(
            _("This numbers signify the number of digits in\n"
              "the decimal part of Excellon coordinates.")
        )
        hlay2.addWidget(self.excellon_format_lower_mm_entry, QtCore.Qt.AlignLeft)
        hlay2.addStretch()

        grid2 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid2)

        self.excellon_zeros_label = QtWidgets.QLabel('%s:' % _('Default <b>Zeros</b>'))
        self.excellon_zeros_label.setAlignment(QtCore.Qt.AlignLeft)
        self.excellon_zeros_label.setToolTip(
            _("This sets the type of Excellon zeros.\n"
              "If LZ then Leading Zeros are kept and\n"
              "Trailing Zeros are removed.\n"
              "If TZ is checked then Trailing Zeros are kept\n"
              "and Leading Zeros are removed.")
        )
        grid2.addWidget(self.excellon_zeros_label, 0, 0)

        self.excellon_zeros_radio = RadioSet([{'label': _('LZ'), 'value': 'L'},
                                              {'label': _('TZ'), 'value': 'T'}])
        self.excellon_zeros_radio.setToolTip(
            _("This sets the default type of Excellon zeros.\n"
              "If it is not detected in the parsed file the value here\n"
              "will be used."
              "If LZ then Leading Zeros are kept and\n"
              "Trailing Zeros are removed.\n"
              "If TZ is checked then Trailing Zeros are kept\n"
              "and Leading Zeros are removed.")
        )
        grid2.addWidget(self.excellon_zeros_radio, 0, 1)

        self.excellon_units_label = QtWidgets.QLabel('%s:' % _('Default <b>Units</b>'))
        self.excellon_units_label.setAlignment(QtCore.Qt.AlignLeft)
        self.excellon_units_label.setToolTip(
            _("This sets the default units of Excellon files.\n"
              "If it is not detected in the parsed file the value here\n"
              "will be used."
              "Some Excellon files don't have an header\n"
              "therefore this parameter will be used.")
        )
        grid2.addWidget(self.excellon_units_label, 1, 0)

        self.excellon_units_radio = RadioSet([{'label': _('INCH'), 'value': 'INCH'},
                                              {'label': _('MM'), 'value': 'METRIC'}])
        self.excellon_units_radio.setToolTip(
            _("This sets the units of Excellon files.\n"
              "Some Excellon files don't have an header\n"
              "therefore this parameter will be used.")
        )
        grid2.addWidget(self.excellon_units_radio, 1, 1)

        self.update_excellon_cb = FCCheckBox(label=_('Update Export settings'))
        self.update_excellon_cb.setToolTip(
            "If checked, the Excellon Export settings will be updated with the ones above."
        )
        grid2.addWidget(self.update_excellon_cb, 2, 0, 1, 2)

        grid2.addWidget(QtWidgets.QLabel(""), 3, 0)

        self.excellon_general_label = QtWidgets.QLabel("<b>%s:</b>" % _("Excellon Optimization"))
        grid2.addWidget(self.excellon_general_label, 4, 0, 1, 2)

        self.excellon_optimization_label = QtWidgets.QLabel(_('Algorithm:'))
        self.excellon_optimization_label.setToolTip(
            _("This sets the optimization type for the Excellon drill path.\n"
              "If <<MetaHeuristic>> is checked then Google OR-Tools algorithm with\n"
              "MetaHeuristic Guided Local Path is used. Default search time is 3sec.\n"
              "If <<Basic>> is checked then Google OR-Tools Basic algorithm is used.\n"
              "If <<TSA>> is checked then Travelling Salesman algorithm is used for\n"
              "drill path optimization.\n"
              "\n"
              "If this control is disabled, then FlatCAM works in 32bit mode and it uses\n"
              "Travelling Salesman algorithm for path optimization.")
        )
        grid2.addWidget(self.excellon_optimization_label, 5, 0)

        self.excellon_optimization_radio = RadioSet([{'label': _('MetaHeuristic'), 'value': 'M'},
                                                     {'label': _('Basic'), 'value': 'B'},
                                                     {'label': _('TSA'), 'value': 'T'}],
                                                    orientation='vertical', stretch=False)
        self.excellon_optimization_radio.setToolTip(
            _("This sets the optimization type for the Excellon drill path.\n"
              "If <<MetaHeuristic>> is checked then Google OR-Tools algorithm with\n"
              "MetaHeuristic Guided Local Path is used. Default search time is 3sec.\n"
              "If <<Basic>> is checked then Google OR-Tools Basic algorithm is used.\n"
              "If <<TSA>> is checked then Travelling Salesman algorithm is used for\n"
              "drill path optimization.\n"
              "\n"
              "If this control is disabled, then FlatCAM works in 32bit mode and it uses\n"
              "Travelling Salesman algorithm for path optimization.")
        )
        grid2.addWidget(self.excellon_optimization_radio, 5, 1)

        self.optimization_time_label = QtWidgets.QLabel('%s:' % _('Optimization Time'))
        self.optimization_time_label.setAlignment(QtCore.Qt.AlignLeft)
        self.optimization_time_label.setToolTip(
            _("When OR-Tools Metaheuristic (MH) is enabled there is a\n"
              "maximum threshold for how much time is spent doing the\n"
              "path optimization. This max duration is set here.\n"
              "In seconds.")

        )
        grid2.addWidget(self.optimization_time_label, 6, 0)

        self.optimization_time_entry = IntEntry()
        self.optimization_time_entry.setValidator(QtGui.QIntValidator(0, 999))
        grid2.addWidget(self.optimization_time_entry, 6, 1)

        current_platform = platform.architecture()[0]
        if current_platform == '64bit':
            self.excellon_optimization_label.setDisabled(False)
            self.excellon_optimization_radio.setDisabled(False)
            self.optimization_time_label.setDisabled(False)
            self.optimization_time_entry.setDisabled(False)
            self.excellon_optimization_radio.activated_custom.connect(self.optimization_selection)

        else:
            self.excellon_optimization_label.setDisabled(True)
            self.excellon_optimization_radio.setDisabled(True)
            self.optimization_time_label.setDisabled(True)
            self.optimization_time_entry.setDisabled(True)

        self.layout.addStretch()

    def optimization_selection(self):
        if self.excellon_optimization_radio.get_value() == 'M':
            self.optimization_time_label.setDisabled(False)
            self.optimization_time_entry.setDisabled(False)
        else:
            self.optimization_time_label.setDisabled(True)
            self.optimization_time_entry.setDisabled(True)


class ExcellonOptPrefGroupUI(OptionsGroupUI):

    def __init__(self, parent=None):
        # OptionsGroupUI.__init__(self, "Excellon Options", parent=parent)
        super(ExcellonOptPrefGroupUI, self).__init__(self)

        self.setTitle(str(_("Excellon Options")))

        # ## Create CNC Job
        self.cncjob_label = QtWidgets.QLabel('<b>%s</b>' % _('Create CNC Job'))
        self.cncjob_label.setToolTip(
            _("Parameters used to create a CNC Job object\n"
              "for this drill object.")
        )
        self.layout.addWidget(self.cncjob_label)

        grid2 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid2)

        # Cut Z
        cutzlabel = QtWidgets.QLabel('%s:' % _('Cut Z'))
        cutzlabel.setToolTip(
            _("Drill depth (negative)\n"
              "below the copper surface.")
        )
        grid2.addWidget(cutzlabel, 0, 0)
        self.cutz_entry = LengthEntry()
        grid2.addWidget(self.cutz_entry, 0, 1)

        # Travel Z
        travelzlabel = QtWidgets.QLabel('%s:' % _('Travel Z'))
        travelzlabel.setToolTip(
            _("Tool height when travelling\n"
              "across the XY plane.")
        )
        grid2.addWidget(travelzlabel, 1, 0)
        self.travelz_entry = LengthEntry()
        grid2.addWidget(self.travelz_entry, 1, 1)

        # Tool change:
        toolchlabel = QtWidgets.QLabel('%s:' % _("Tool change"))
        toolchlabel.setToolTip(
            _("Include tool-change sequence\n"
              "in G-Code (Pause for tool change).")
        )
        self.toolchange_cb = FCCheckBox()
        grid2.addWidget(toolchlabel, 2, 0)
        grid2.addWidget(self.toolchange_cb, 2, 1)

        toolchangezlabel = QtWidgets.QLabel('%s:' % _('Toolchange Z'))
        toolchangezlabel.setToolTip(
            _("Z-axis position (height) for\n"
              "tool change.")
        )
        grid2.addWidget(toolchangezlabel, 3, 0)
        self.toolchangez_entry = LengthEntry()
        grid2.addWidget(self.toolchangez_entry, 3, 1)

        # End Move Z
        endzlabel = QtWidgets.QLabel('%s:' % _('End move Z'))
        endzlabel.setToolTip(
            _("Height of the tool after\n"
              "the last move at the end of the job.")
        )
        grid2.addWidget(endzlabel, 4, 0)
        self.eendz_entry = LengthEntry()
        grid2.addWidget(self.eendz_entry, 4, 1)

        # Feedrate Z
        frlabel = QtWidgets.QLabel('%s:' % _('Feedrate Z'))
        frlabel.setToolTip(
            _("Tool speed while drilling\n"
              "(in units per minute).\n"
              "So called 'Plunge' feedrate.\n"
              "This is for linear move G01.")
        )
        grid2.addWidget(frlabel, 5, 0)
        self.feedrate_entry = LengthEntry()
        grid2.addWidget(self.feedrate_entry, 5, 1)

        # Spindle speed
        spdlabel = QtWidgets.QLabel('%s:' % _('Spindle Speed'))
        spdlabel.setToolTip(
            _("Speed of the spindle\n"
              "in RPM (optional)")
        )
        grid2.addWidget(spdlabel, 6, 0)
        self.spindlespeed_entry = IntEntry(allow_empty=True)
        grid2.addWidget(self.spindlespeed_entry, 6, 1)

        # Dwell
        dwelllabel = QtWidgets.QLabel('%s:' % _('Dwell'))
        dwelllabel.setToolTip(
            _("Pause to allow the spindle to reach its\n"
              "speed before cutting.")
        )
        dwelltime = QtWidgets.QLabel('%s:' % _('Duration'))
        dwelltime.setToolTip(
            _("Number of time units for spindle to dwell.")
        )
        self.dwell_cb = FCCheckBox()
        self.dwelltime_entry = FCEntry()

        grid2.addWidget(dwelllabel, 7, 0)
        grid2.addWidget(self.dwell_cb, 7, 1)
        grid2.addWidget(dwelltime, 8, 0)
        grid2.addWidget(self.dwelltime_entry, 8, 1)

        self.ois_dwell_exc = OptionalInputSection(self.dwell_cb, [self.dwelltime_entry])

        # postprocessor selection
        pp_excellon_label = QtWidgets.QLabel('%s:' % _("Postprocessor"))
        pp_excellon_label.setToolTip(
            _("The postprocessor JSON file that dictates\n"
              "Gcode output.")
        )
        grid2.addWidget(pp_excellon_label, 9, 0)
        self.pp_excellon_name_cb = FCComboBox()
        self.pp_excellon_name_cb.setFocusPolicy(Qt.StrongFocus)
        grid2.addWidget(self.pp_excellon_name_cb, 9, 1)

        # ### Choose what to use for Gcode creation: Drills, Slots or Both
        excellon_gcode_type_label = QtWidgets.QLabel('<b>%s</b>' % _('Gcode'))
        excellon_gcode_type_label.setToolTip(
            _("Choose what to use for GCode generation:\n"
              "'Drills', 'Slots' or 'Both'.\n"
              "When choosing 'Slots' or 'Both', slots will be\n"
              "converted to drills.")
        )
        self.excellon_gcode_type_radio = RadioSet([{'label': 'Drills', 'value': 'drills'},
                                                   {'label': 'Slots', 'value': 'slots'},
                                                   {'label': 'Both', 'value': 'both'}])
        grid2.addWidget(excellon_gcode_type_label, 10, 0)
        grid2.addWidget(self.excellon_gcode_type_radio, 10, 1)

        # until I decide to implement this feature those remain disabled
        excellon_gcode_type_label.hide()
        self.excellon_gcode_type_radio.setVisible(False)

        # ### Milling Holes ## ##
        self.mill_hole_label = QtWidgets.QLabel('<b>%s</b>' % _('Mill Holes'))
        self.mill_hole_label.setToolTip(
            _("Create Geometry for milling holes.")
        )
        grid2.addWidget(self.mill_hole_label, 11, 0, 1, 2)

        tdlabel = QtWidgets.QLabel('%s:' % _('Drill Tool dia'))
        tdlabel.setToolTip(
            _("Diameter of the cutting tool.")
        )
        grid2.addWidget(tdlabel, 12, 0)
        self.tooldia_entry = LengthEntry()
        grid2.addWidget(self.tooldia_entry, 12, 1)
        stdlabel = QtWidgets.QLabel('%s:' % _('Slot Tool dia'))
        stdlabel.setToolTip(
            _("Diameter of the cutting tool\n"
              "when milling slots.")
        )
        grid2.addWidget(stdlabel, 13, 0)
        self.slot_tooldia_entry = LengthEntry()
        grid2.addWidget(self.slot_tooldia_entry, 13, 1)

        grid4 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid4)

        # Adding the Excellon Format Defaults Button
        self.excellon_defaults_button = QtWidgets.QPushButton()
        self.excellon_defaults_button.setText(str(_("Defaults")))
        self.excellon_defaults_button.setMinimumWidth(80)
        grid4.addWidget(self.excellon_defaults_button, 0, 0, QtCore.Qt.AlignRight)

        self.layout.addStretch()


class ExcellonAdvOptPrefGroupUI(OptionsGroupUI):

    def __init__(self, parent=None):
        # OptionsGroupUI.__init__(self, "Excellon Advanced Options", parent=parent)
        super(ExcellonAdvOptPrefGroupUI, self).__init__(self)

        self.setTitle(str(_("Excellon Adv. Options")))

        # #######################
        # ## ADVANCED OPTIONS ###
        # #######################

        self.exc_label = QtWidgets.QLabel('<b>%s:</b>' % _('Advanced Options'))
        self.exc_label.setToolTip(
            _("A list of Excellon advanced parameters.\n"
              "Those parameters are available only for\n"
              "Advanced App. Level.")
        )
        self.layout.addWidget(self.exc_label)

        grid1 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid1)

        offsetlabel = QtWidgets.QLabel('%s:' % _('Offset Z'))
        offsetlabel.setToolTip(
            _("Some drill bits (the larger ones) need to drill deeper\n"
              "to create the desired exit hole diameter due of the tip shape.\n"
              "The value here can compensate the Cut Z parameter."))
        grid1.addWidget(offsetlabel, 0, 0)
        self.offset_entry = LengthEntry()
        grid1.addWidget(self.offset_entry, 0, 1)

        toolchange_xy_label = QtWidgets.QLabel('%s:' % _('Toolchange X,Y'))
        toolchange_xy_label.setToolTip(
            _("Toolchange X,Y position.")
        )
        grid1.addWidget(toolchange_xy_label, 1, 0)
        self.toolchangexy_entry = FCEntry()
        grid1.addWidget(self.toolchangexy_entry, 1, 1)

        startzlabel = QtWidgets.QLabel('%s:' % _('Start move Z'))
        startzlabel.setToolTip(
            _("Height of the tool just after start.\n"
              "Delete the value if you don't need this feature.")
        )
        grid1.addWidget(startzlabel, 2, 0)
        self.estartz_entry = FloatEntry()
        grid1.addWidget(self.estartz_entry, 2, 1)

        # Feedrate Rapids
        fr_rapid_label = QtWidgets.QLabel('%s:' % _('Feedrate Rapids'))
        fr_rapid_label.setToolTip(
            _("Tool speed while drilling\n"
              "(in units per minute).\n"
              "This is for the rapid move G00.\n"
              "It is useful only for Marlin,\n"
              "ignore for any other cases.")
        )
        grid1.addWidget(fr_rapid_label, 3, 0)
        self.feedrate_rapid_entry = LengthEntry()
        grid1.addWidget(self.feedrate_rapid_entry, 3, 1)

        # Probe depth
        self.pdepth_label = QtWidgets.QLabel('%s:' % _("Probe Z depth"))
        self.pdepth_label.setToolTip(
            _("The maximum depth that the probe is allowed\n"
              "to probe. Negative value, in current units.")
        )
        grid1.addWidget(self.pdepth_label, 4, 0)
        self.pdepth_entry = FCEntry()
        grid1.addWidget(self.pdepth_entry, 4, 1)

        # Probe feedrate
        self.feedrate_probe_label = QtWidgets.QLabel('%s:' % _("Feedrate Probe"))
        self.feedrate_probe_label.setToolTip(
           _("The feedrate used while the probe is probing.")
        )
        grid1.addWidget(self.feedrate_probe_label, 5, 0)
        self.feedrate_probe_entry = FCEntry()
        grid1.addWidget(self.feedrate_probe_entry, 5, 1)

        # Spindle direction
        spindle_dir_label = QtWidgets.QLabel('%s:' % _('Spindle dir.'))
        spindle_dir_label.setToolTip(
            _("This sets the direction that the spindle is rotating.\n"
              "It can be either:\n"
              "- CW = clockwise or\n"
              "- CCW = counter clockwise")
        )

        self.spindledir_radio = RadioSet([{'label': _('CW'), 'value': 'CW'},
                                          {'label': _('CCW'), 'value': 'CCW'}])
        grid1.addWidget(spindle_dir_label, 6, 0)
        grid1.addWidget(self.spindledir_radio, 6, 1)

        fplungelabel = QtWidgets.QLabel('%s:' % _('Fast Plunge'))
        fplungelabel.setToolTip(
            _("By checking this, the vertical move from\n"
              "Z_Toolchange to Z_move is done with G0,\n"
              "meaning the fastest speed available.\n"
              "WARNING: the move is done at Toolchange X,Y coords.")
        )
        self.fplunge_cb = FCCheckBox()
        grid1.addWidget(fplungelabel, 7, 0)
        grid1.addWidget(self.fplunge_cb, 7, 1)

        fretractlabel = QtWidgets.QLabel('%s:' % _('Fast Retract'))
        fretractlabel.setToolTip(
            _("Exit hole strategy.\n"
              " - When uncheked, while exiting the drilled hole the drill bit\n"
              "will travel slow, with set feedrate (G1), up to zero depth and then\n"
              "travel as fast as possible (G0) to the Z Move (travel height).\n"
              " - When checked the travel from Z cut (cut depth) to Z_move\n"
              "(travel height) is done as fast as possible (G0) in one move.")
        )
        self.fretract_cb = FCCheckBox()
        grid1.addWidget(fretractlabel, 8, 0)
        grid1.addWidget(self.fretract_cb, 8, 1)

        self.layout.addStretch()


class ExcellonExpPrefGroupUI(OptionsGroupUI):

    def __init__(self, parent=None):
        super(ExcellonExpPrefGroupUI, self).__init__(self)

        self.setTitle(str(_("Excellon Export")))

        # Plot options
        self.export_options_label = QtWidgets.QLabel("<b>%s:</b>" % _("Export Options"))
        self.export_options_label.setToolTip(
            _("The parameters set here are used in the file exported\n"
              "when using the File -> Export -> Export Excellon menu entry.")
        )
        self.layout.addWidget(self.export_options_label)

        form = QtWidgets.QFormLayout()
        self.layout.addLayout(form)

        # Excellon Units
        self.excellon_units_label = QtWidgets.QLabel('<b>%s:</b>' % _('Units'))
        self.excellon_units_label.setToolTip(
            _("The units used in the Excellon file.")
        )

        self.excellon_units_radio = RadioSet([{'label': _('INCH'), 'value': 'INCH'},
                                              {'label': _('MM'), 'value': 'METRIC'}])
        self.excellon_units_radio.setToolTip(
            _("The units used in the Excellon file.")
        )

        form.addRow(self.excellon_units_label, self.excellon_units_radio)

        # Excellon non-decimal format
        self.digits_label = QtWidgets.QLabel("<b>%s:</b>" % _("Int/Decimals"))
        self.digits_label.setToolTip(
            _("The NC drill files, usually named Excellon files\n"
              "are files that can be found in different formats.\n"
              "Here we set the format used when the provided\n"
              "coordinates are not using period.")
        )

        hlay1 = QtWidgets.QHBoxLayout()

        self.format_whole_entry = IntEntry()
        self.format_whole_entry.setMaxLength(1)
        self.format_whole_entry.setAlignment(QtCore.Qt.AlignRight)
        self.format_whole_entry.setMinimumWidth(30)
        self.format_whole_entry.setToolTip(
            _("This numbers signify the number of digits in\n"
              "the whole part of Excellon coordinates.")
        )
        hlay1.addWidget(self.format_whole_entry, QtCore.Qt.AlignLeft)

        excellon_separator_label = QtWidgets.QLabel(':')
        excellon_separator_label.setFixedWidth(5)
        hlay1.addWidget(excellon_separator_label, QtCore.Qt.AlignLeft)

        self.format_dec_entry = IntEntry()
        self.format_dec_entry.setMaxLength(1)
        self.format_dec_entry.setAlignment(QtCore.Qt.AlignRight)
        self.format_dec_entry.setMinimumWidth(30)
        self.format_dec_entry.setToolTip(
            _("This numbers signify the number of digits in\n"
              "the decimal part of Excellon coordinates.")
        )
        hlay1.addWidget(self.format_dec_entry, QtCore.Qt.AlignLeft)
        hlay1.addStretch()

        form.addRow(self.digits_label, hlay1)

        # Select the Excellon Format
        self.format_label = QtWidgets.QLabel("<b>%s:</b>" % _("Format"))
        self.format_label.setToolTip(
            _("Select the kind of coordinates format used.\n"
              "Coordinates can be saved with decimal point or without.\n"
              "When there is no decimal point, it is required to specify\n"
              "the number of digits for integer part and the number of decimals.\n"
              "Also it will have to be specified if LZ = leading zeros are kept\n"
              "or TZ = trailing zeros are kept.")
        )
        self.format_radio = RadioSet([{'label': _('Decimal'), 'value': 'dec'},
                                      {'label': _('No-Decimal'), 'value': 'ndec'}])
        self.format_radio.setToolTip(
            _("Select the kind of coordinates format used.\n"
              "Coordinates can be saved with decimal point or without.\n"
              "When there is no decimal point, it is required to specify\n"
              "the number of digits for integer part and the number of decimals.\n"
              "Also it will have to be specified if LZ = leading zeros are kept\n"
              "or TZ = trailing zeros are kept.")
        )

        form.addRow(self.format_label, self.format_radio)

        # Excellon Zeros
        self.zeros_label = QtWidgets.QLabel('<b>%s:</b>' % _('Zeros'))
        self.zeros_label.setAlignment(QtCore.Qt.AlignLeft)
        self.zeros_label.setToolTip(
            _("This sets the type of Excellon zeros.\n"
              "If LZ then Leading Zeros are kept and\n"
              "Trailing Zeros are removed.\n"
              "If TZ is checked then Trailing Zeros are kept\n"
              "and Leading Zeros are removed.")
        )

        self.zeros_radio = RadioSet([{'label': _('LZ'), 'value': 'LZ'},
                                     {'label': _('TZ'), 'value': 'TZ'}])
        self.zeros_radio.setToolTip(
            _("This sets the default type of Excellon zeros.\n"
              "If LZ then Leading Zeros are kept and\n"
              "Trailing Zeros are removed.\n"
              "If TZ is checked then Trailing Zeros are kept\n"
              "and Leading Zeros are removed.")
        )

        form.addRow(self.zeros_label, self.zeros_radio)

        # Slot type
        self.slot_type_label = QtWidgets.QLabel('<b>%s:</b>' % _('Slot type'))
        self.slot_type_label.setAlignment(QtCore.Qt.AlignLeft)
        self.slot_type_label.setToolTip(
            _("This sets how the slots will be exported.\n"
              "If ROUTED then the slots will be routed\n"
              "using M15/M16 commands.\n"
              "If DRILLED(G85) the slots will be exported\n"
              "using the Drilled slot command (G85).")
        )

        self.slot_type_radio = RadioSet([{'label': _('Routed'), 'value': 'routing'},
                                         {'label': _('Drilled(G85)'), 'value': 'drilling'}])
        self.slot_type_radio.setToolTip(
            _("This sets how the slots will be exported.\n"
              "If ROUTED then the slots will be routed\n"
              "using M15/M16 commands.\n"
              "If DRILLED(G85) the slots will be exported\n"
              "using the Drilled slot command (G85).")
        )

        form.addRow(self.slot_type_label, self.slot_type_radio)

        self.layout.addStretch()
        self.format_radio.activated_custom.connect(self.optimization_selection)

    def optimization_selection(self):
        if self.format_radio.get_value() == 'dec':
            self.zeros_label.setDisabled(True)
            self.zeros_radio.setDisabled(True)
        else:
            self.zeros_label.setDisabled(False)
            self.zeros_radio.setDisabled(False)


class ExcellonEditorPrefGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        super(ExcellonEditorPrefGroupUI, self).__init__(self)

        self.setTitle(str(_("Excellon Editor")))

        # Excellon Editor Parameters
        self.param_label = QtWidgets.QLabel("<b>%s:</b>" % _("Parameters"))
        self.param_label.setToolTip(
            _("A list of Excellon Editor parameters.")
        )
        self.layout.addWidget(self.param_label)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        # Selection Limit
        self.sel_limit_label = QtWidgets.QLabel('%s:' % _("Selection limit"))
        self.sel_limit_label.setToolTip(
            _("Set the number of selected Excellon geometry\n"
              "items above which the utility geometry\n"
              "becomes just a selection rectangle.\n"
              "Increases the performance when moving a\n"
              "large number of geometric elements.")
        )
        self.sel_limit_entry = IntEntry()

        grid0.addWidget(self.sel_limit_label, 0, 0)
        grid0.addWidget(self.sel_limit_entry, 0, 1)

        # New tool diameter
        self.addtool_entry_lbl = QtWidgets.QLabel('%s:' % _('New Tool Dia'))
        self.addtool_entry_lbl.setToolTip(
            _("Diameter for the new tool")
        )

        self.addtool_entry = FCEntry()
        self.addtool_entry.setValidator(QtGui.QDoubleValidator(0.0001, 99.9999, 4))

        grid0.addWidget(self.addtool_entry_lbl, 1, 0)
        grid0.addWidget(self.addtool_entry, 1, 1)

        # Number of drill holes in a drill array
        self.drill_array_size_label = QtWidgets.QLabel('%s:' % _('Nr of drills'))
        self.drill_array_size_label.setToolTip(
            _("Specify how many drills to be in the array.")
        )
        # self.drill_array_size_label.setMinimumWidth(100)

        self.drill_array_size_entry = LengthEntry()

        grid0.addWidget(self.drill_array_size_label, 2, 0)
        grid0.addWidget(self.drill_array_size_entry, 2, 1)

        self.drill_array_linear_label = QtWidgets.QLabel('<b>%s:</b>' % _('Linear Drill Array'))
        grid0.addWidget(self.drill_array_linear_label, 3, 0, 1, 2)

        # Linear Drill Array direction
        self.drill_axis_label = QtWidgets.QLabel('%s:' % _('Linear Dir.'))
        self.drill_axis_label.setToolTip(
            _("Direction on which the linear array is oriented:\n"
              "- 'X' - horizontal axis \n"
              "- 'Y' - vertical axis or \n"
              "- 'Angle' - a custom angle for the array inclination")
        )
        # self.drill_axis_label.setMinimumWidth(100)
        self.drill_axis_radio = RadioSet([{'label': _('X'), 'value': 'X'},
                                          {'label': _('Y'), 'value': 'Y'},
                                          {'label': _('Angle'), 'value': 'A'}])

        grid0.addWidget(self.drill_axis_label, 4, 0)
        grid0.addWidget(self.drill_axis_radio, 4, 1)

        # Linear Drill Array pitch distance
        self.drill_pitch_label = QtWidgets.QLabel('%s:' % _('Pitch'))
        self.drill_pitch_label.setToolTip(
            _("Pitch = Distance between elements of the array.")
        )
        # self.drill_pitch_label.setMinimumWidth(100)
        self.drill_pitch_entry = LengthEntry()

        grid0.addWidget(self.drill_pitch_label, 5, 0)
        grid0.addWidget(self.drill_pitch_entry, 5, 1)

        # Linear Drill Array custom angle
        self.drill_angle_label = QtWidgets.QLabel('%s:' % _('Angle'))
        self.drill_angle_label.setToolTip(
            _("Angle at which each element in circular array is placed.")
        )
        self.drill_angle_entry = LengthEntry()

        grid0.addWidget(self.drill_angle_label, 6, 0)
        grid0.addWidget(self.drill_angle_entry, 6, 1)

        self.drill_array_circ_label = QtWidgets.QLabel('<b>%s:</b>' % _('Circular Drill Array'))
        grid0.addWidget(self.drill_array_circ_label, 7, 0, 1, 2)

        # Circular Drill Array direction
        self.drill_circular_direction_label = QtWidgets.QLabel('%s:' % _('Circular Dir.'))
        self.drill_circular_direction_label.setToolTip(
            _("Direction for circular array.\n"
              "Can be CW = clockwise or CCW = counter clockwise.")
        )

        self.drill_circular_dir_radio = RadioSet([{'label': _('CW'), 'value': 'CW'},
                                                  {'label': _('CCW'), 'value': 'CCW'}])

        grid0.addWidget(self.drill_circular_direction_label, 8, 0)
        grid0.addWidget(self.drill_circular_dir_radio, 8, 1)

        # Circular Drill Array Angle
        self.drill_circular_angle_label = QtWidgets.QLabel('%s:' % _('Circ. Angle'))
        self.drill_circular_angle_label.setToolTip(
            _("Angle at which each element in circular array is placed.")
        )
        self.drill_circular_angle_entry = LengthEntry()

        grid0.addWidget(self.drill_circular_angle_label, 9, 0)
        grid0.addWidget(self.drill_circular_angle_entry, 9, 1)

        # ##### SLOTS #####
        # #################
        self.drill_array_circ_label = QtWidgets.QLabel('<b>%s:</b>' % _('Slots'))
        grid0.addWidget(self.drill_array_circ_label, 10, 0, 1, 2)

        # Slot length
        self.slot_length_label = QtWidgets.QLabel('%s:' % _('Length'))
        self.slot_length_label.setToolTip(
            _("Length = The length of the slot.")
        )
        self.slot_length_label.setMinimumWidth(100)

        self.slot_length_entry = LengthEntry()
        grid0.addWidget(self.slot_length_label, 11, 0)
        grid0.addWidget(self.slot_length_entry, 11, 1)

        # Slot direction
        self.slot_axis_label = QtWidgets.QLabel('%s:' % _('Direction'))
        self.slot_axis_label.setToolTip(
            _("Direction on which the slot is oriented:\n"
              "- 'X' - horizontal axis \n"
              "- 'Y' - vertical axis or \n"
              "- 'Angle' - a custom angle for the slot inclination")
        )
        self.slot_axis_label.setMinimumWidth(100)

        self.slot_axis_radio = RadioSet([{'label': _('X'), 'value': 'X'},
                                         {'label': _('Y'), 'value': 'Y'},
                                         {'label': _('Angle'), 'value': 'A'}])
        grid0.addWidget(self.slot_axis_label, 12, 0)
        grid0.addWidget(self.slot_axis_radio, 12, 1)

        # Slot custom angle
        self.slot_angle_label = QtWidgets.QLabel('%s:' % _('Angle'))
        self.slot_angle_label.setToolTip(
            _("Angle at which the slot is placed.\n"
              "The precision is of max 2 decimals.\n"
              "Min value is: -359.99 degrees.\n"
              "Max value is:  360.00 degrees.")
        )
        self.slot_angle_label.setMinimumWidth(100)

        self.slot_angle_spinner = FCDoubleSpinner()
        self.slot_angle_spinner.set_precision(2)
        self.slot_angle_spinner.setWrapping(True)
        self.slot_angle_spinner.setRange(-359.99, 360.00)
        self.slot_angle_spinner.setSingleStep(1.0)
        grid0.addWidget(self.slot_angle_label, 13, 0)
        grid0.addWidget(self.slot_angle_spinner, 13, 1)

        # #### SLOTS ARRAY #######
        # ########################

        self.slot_array_linear_label = QtWidgets.QLabel('<b>%s:</b>' % _('Linear Slot Array'))
        grid0.addWidget(self.slot_array_linear_label, 14, 0, 1, 2)

        # Number of slot holes in a drill array
        self.slot_array_size_label = QtWidgets.QLabel('%s:' % _('Nr of slots'))
        self.drill_array_size_label.setToolTip(
            _("Specify how many slots to be in the array.")
        )
        # self.slot_array_size_label.setMinimumWidth(100)

        self.slot_array_size_entry = LengthEntry()

        grid0.addWidget(self.slot_array_size_label, 15, 0)
        grid0.addWidget(self.slot_array_size_entry, 15, 1)

        # Linear Slot Array direction
        self.slot_array_axis_label = QtWidgets.QLabel('%s:' % _('Linear Dir.'))
        self.slot_array_axis_label.setToolTip(
            _("Direction on which the linear array is oriented:\n"
              "- 'X' - horizontal axis \n"
              "- 'Y' - vertical axis or \n"
              "- 'Angle' - a custom angle for the array inclination")
        )
        # self.slot_axis_label.setMinimumWidth(100)
        self.slot_array_axis_radio = RadioSet([{'label': _('X'), 'value': 'X'},
                                               {'label': _('Y'), 'value': 'Y'},
                                               {'label': _('Angle'), 'value': 'A'}])

        grid0.addWidget(self.slot_array_axis_label, 16, 0)
        grid0.addWidget(self.slot_array_axis_radio, 16, 1)

        # Linear Slot Array pitch distance
        self.slot_array_pitch_label = QtWidgets.QLabel('%s:' % _('Pitch'))
        self.slot_array_pitch_label.setToolTip(
            _("Pitch = Distance between elements of the array.")
        )
        # self.drill_pitch_label.setMinimumWidth(100)
        self.slot_array_pitch_entry = LengthEntry()

        grid0.addWidget(self.slot_array_pitch_label, 17, 0)
        grid0.addWidget(self.slot_array_pitch_entry, 17, 1)

        # Linear Slot Array custom angle
        self.slot_array_angle_label = QtWidgets.QLabel('%s:' % _('Angle'))
        self.slot_array_angle_label.setToolTip(
            _("Angle at which each element in circular array is placed.")
        )
        self.slot_array_angle_entry = LengthEntry()

        grid0.addWidget(self.slot_array_angle_label, 18, 0)
        grid0.addWidget(self.slot_array_angle_entry, 18, 1)

        self.slot_array_circ_label = QtWidgets.QLabel('<b>%s:</b>' % _('Circular Slot Array'))
        grid0.addWidget(self.slot_array_circ_label, 19, 0, 1, 2)

        # Circular Slot Array direction
        self.slot_array_circular_direction_label = QtWidgets.QLabel('%s:' % _('Circular Dir.'))
        self.slot_array_circular_direction_label.setToolTip(
            _("Direction for circular array.\n"
              "Can be CW = clockwise or CCW = counter clockwise.")
        )

        self.slot_array_circular_dir_radio = RadioSet([{'label': _('CW'), 'value': 'CW'},
                                                       {'label': _('CCW'), 'value': 'CCW'}])

        grid0.addWidget(self.slot_array_circular_direction_label, 20, 0)
        grid0.addWidget(self.slot_array_circular_dir_radio, 20, 1)

        # Circular Slot Array Angle
        self.slot_array_circular_angle_label = QtWidgets.QLabel('%s:' % _('Circ. Angle'))
        self.slot_array_circular_angle_label.setToolTip(
            _("Angle at which each element in circular array is placed.")
        )
        self.slot_array_circular_angle_entry = LengthEntry()

        grid0.addWidget(self.slot_array_circular_angle_label, 21, 0)
        grid0.addWidget(self.slot_array_circular_angle_entry, 21, 1)

        self.layout.addStretch()


class GeometryGenPrefGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        # OptionsGroupUI.__init__(self, "Geometry General Preferences", parent=parent)
        super(GeometryGenPrefGroupUI, self).__init__(self)

        self.setTitle(str(_("Geometry General")))

        # ## Plot options
        self.plot_options_label = QtWidgets.QLabel("<b>%s:</b>" % _("Plot Options"))
        self.layout.addWidget(self.plot_options_label)

        # Plot CB
        self.plot_cb = FCCheckBox(label=_('Plot'))
        self.plot_cb.setToolTip(
            _("Plot (show) this object.")
        )
        self.layout.addWidget(self.plot_cb)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        # Number of circle steps for circular aperture linear approximation
        self.circle_steps_label = QtWidgets.QLabel('%s:' % _("Circle Steps"))
        self.circle_steps_label.setToolTip(
            _("The number of circle steps for <b>Geometry</b> \n"
              "circle and arc shapes linear approximation.")
        )
        grid0.addWidget(self.circle_steps_label, 1, 0)
        self.circle_steps_entry = IntEntry()
        grid0.addWidget(self.circle_steps_entry, 1, 1)

        # Tools
        self.tools_label = QtWidgets.QLabel("<b>%s:</b>" % _("Tools"))
        grid0.addWidget(self.tools_label, 2, 0, 1, 2)

        # Tooldia
        tdlabel = QtWidgets.QLabel('%s:' % _('Tool dia'))
        tdlabel.setToolTip(
            _("Diameters of the cutting tools, separated by ','")
        )
        grid0.addWidget(tdlabel, 3, 0)
        self.cnctooldia_entry = FCEntry()
        grid0.addWidget(self.cnctooldia_entry, 3, 1)

        self.layout.addStretch()


class GeometryOptPrefGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        # OptionsGroupUI.__init__(self, "Geometry Options Preferences", parent=parent)
        super(GeometryOptPrefGroupUI, self).__init__(self)

        self.setTitle(str(_("Geometry Options")))

        # ------------------------------
        # ## Create CNC Job
        # ------------------------------
        self.cncjob_label = QtWidgets.QLabel('<b>%s:</b>' % _('Create CNC Job'))
        self.cncjob_label.setToolTip(
            _("Create a CNC Job object\n"
              "tracing the contours of this\n"
              "Geometry object.")
        )
        self.layout.addWidget(self.cncjob_label)

        grid1 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid1)

        # Cut Z
        cutzlabel = QtWidgets.QLabel('%s:' % _('Cut Z'))
        cutzlabel.setToolTip(
            _("Cutting depth (negative)\n"
              "below the copper surface.")
        )
        grid1.addWidget(cutzlabel, 0, 0)
        self.cutz_entry = LengthEntry()
        grid1.addWidget(self.cutz_entry, 0, 1)

        # Multidepth CheckBox
        self.multidepth_cb = FCCheckBox(label=_('Multi-Depth'))
        self.multidepth_cb.setToolTip(
            _(
                "Use multiple passes to limit\n"
                "the cut depth in each pass. Will\n"
                "cut multiple times until Cut Z is\n"
                "reached."
            )
        )
        grid1.addWidget(self.multidepth_cb, 1, 0)

        # Depth/pass
        dplabel = QtWidgets.QLabel('%s:' % _('Depth/Pass'))
        dplabel.setToolTip(
            _("The depth to cut on each pass,\n"
              "when multidepth is enabled.\n"
              "It has positive value although\n"
              "it is a fraction from the depth\n"
              "which has negative value.")
        )

        grid1.addWidget(dplabel, 2, 0)
        self.depthperpass_entry = LengthEntry()
        grid1.addWidget(self.depthperpass_entry, 2, 1)

        self.ois_multidepth = OptionalInputSection(self.multidepth_cb, [self.depthperpass_entry])

        # Travel Z
        travelzlabel = QtWidgets.QLabel('%s:' % _('Travel Z'))
        travelzlabel.setToolTip(
            _("Height of the tool when\n"
              "moving without cutting.")
        )
        grid1.addWidget(travelzlabel, 3, 0)
        self.travelz_entry = LengthEntry()
        grid1.addWidget(self.travelz_entry, 3, 1)

        # Tool change:
        toolchlabel = QtWidgets.QLabel('%s:' % _("Tool change"))
        toolchlabel.setToolTip(
            _(
                "Include tool-change sequence\n"
                "in the Machine Code (Pause for tool change)."
            )
        )
        self.toolchange_cb = FCCheckBox()
        grid1.addWidget(toolchlabel, 4, 0)
        grid1.addWidget(self.toolchange_cb, 4, 1)

        # Toolchange Z
        toolchangezlabel = QtWidgets.QLabel('%s:' % _('Toolchange Z'))
        toolchangezlabel.setToolTip(
            _(
                "Z-axis position (height) for\n"
                "tool change."
            )
        )
        grid1.addWidget(toolchangezlabel, 5, 0)
        self.toolchangez_entry = LengthEntry()
        grid1.addWidget(self.toolchangez_entry, 5, 1)

        # End move Z
        endzlabel = QtWidgets.QLabel('%s:' % _('End move Z'))
        endzlabel.setToolTip(
            _("Height of the tool after\n"
              "the last move at the end of the job.")
        )
        grid1.addWidget(endzlabel, 6, 0)
        self.gendz_entry = LengthEntry()
        grid1.addWidget(self.gendz_entry, 6, 1)

        # Feedrate X-Y
        frlabel = QtWidgets.QLabel('%s:' % _('Feed Rate X-Y'))
        frlabel.setToolTip(
            _("Cutting speed in the XY\n"
              "plane in units per minute")
        )
        grid1.addWidget(frlabel, 7, 0)
        self.cncfeedrate_entry = LengthEntry()
        grid1.addWidget(self.cncfeedrate_entry, 7, 1)

        # Feedrate Z (Plunge)
        frz_label = QtWidgets.QLabel('%s:' % _('Feed Rate Z'))
        frz_label.setToolTip(
            _("Cutting speed in the XY\n"
              "plane in units per minute.\n"
              "It is called also Plunge.")
        )
        grid1.addWidget(frz_label, 8, 0)
        self.cncplunge_entry = LengthEntry()
        grid1.addWidget(self.cncplunge_entry, 8, 1)

        # Spindle Speed
        spdlabel = QtWidgets.QLabel('%s:' % _('Spindle speed'))
        spdlabel.setToolTip(
            _(
                "Speed of the spindle in RPM (optional).\n"
                "If LASER postprocessor is used,\n"
                "this value is the power of laser."
            )
        )
        grid1.addWidget(spdlabel, 9, 0)
        self.cncspindlespeed_entry = IntEntry(allow_empty=True)
        grid1.addWidget(self.cncspindlespeed_entry, 9, 1)

        # Dwell
        self.dwell_cb = FCCheckBox(label='%s:' % _('Dwell'))
        self.dwell_cb.setToolTip(
            _("Pause to allow the spindle to reach its\n"
              "speed before cutting.")
        )
        dwelltime = QtWidgets.QLabel('%s:' % _('Duration'))
        dwelltime.setToolTip(
            _("Number of time units for spindle to dwell.")
        )
        self.dwelltime_entry = FCEntry()
        grid1.addWidget(self.dwell_cb, 10, 0)
        grid1.addWidget(dwelltime, 11, 0)
        grid1.addWidget(self.dwelltime_entry, 11, 1)

        self.ois_dwell = OptionalInputSection(self.dwell_cb, [self.dwelltime_entry])

        # postprocessor selection
        pp_label = QtWidgets.QLabel('%s:' % _("Postprocessor"))
        pp_label.setToolTip(
            _("The Postprocessor file that dictates\n"
              "the Machine Code (like GCode, RML, HPGL) output.")
        )
        grid1.addWidget(pp_label, 12, 0)
        self.pp_geometry_name_cb = FCComboBox()
        self.pp_geometry_name_cb.setFocusPolicy(Qt.StrongFocus)
        grid1.addWidget(self.pp_geometry_name_cb, 12, 1)

        self.layout.addStretch()


class GeometryAdvOptPrefGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        # OptionsGroupUI.__init__(self, "Geometry Advanced Options Preferences", parent=parent)
        super(GeometryAdvOptPrefGroupUI, self).__init__(self)

        self.setTitle(str(_("Geometry Adv. Options")))

        # ------------------------------
        # ## Advanced Options
        # ------------------------------
        self.geo_label = QtWidgets.QLabel('<b>%s:</b>' % _('Advanced Options'))
        self.geo_label.setToolTip(
            _("A list of Geometry advanced parameters.\n"
              "Those parameters are available only for\n"
              "Advanced App. Level.")
        )
        self.layout.addWidget(self.geo_label)

        grid1 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid1)

        # Toolchange X,Y
        toolchange_xy_label = QtWidgets.QLabel('%s:' % _('Toolchange X-Y'))
        toolchange_xy_label.setToolTip(
            _("Toolchange X,Y position.")
        )
        grid1.addWidget(toolchange_xy_label, 1, 0)
        self.toolchangexy_entry = FCEntry()
        grid1.addWidget(self.toolchangexy_entry, 1, 1)

        # Start move Z
        startzlabel = QtWidgets.QLabel('%s:' % _('Start move Z'))
        startzlabel.setToolTip(
            _("Height of the tool just after starting the work.\n"
              "Delete the value if you don't need this feature.")
        )
        grid1.addWidget(startzlabel, 2, 0)
        self.gstartz_entry = FloatEntry()
        grid1.addWidget(self.gstartz_entry, 2, 1)

        # Feedrate rapids
        fr_rapid_label = QtWidgets.QLabel('%s:' % _('Feed Rate Rapids'))
        fr_rapid_label.setToolTip(
            _("Cutting speed in the XY plane\n"
              "(in units per minute).\n"
              "This is for the rapid move G00.\n"
              "It is useful only for Marlin,\n"
              "ignore for any other cases.")
        )
        grid1.addWidget(fr_rapid_label, 4, 0)
        self.cncfeedrate_rapid_entry = LengthEntry()
        grid1.addWidget(self.cncfeedrate_rapid_entry, 4, 1)

        # End move extra cut
        self.extracut_cb = FCCheckBox(label='%s' % _('Re-cut 1st pt.'))
        self.extracut_cb.setToolTip(
            _("In order to remove possible\n"
              "copper leftovers where first cut\n"
              "meet with last cut, we generate an\n"
              "extended cut over the first cut section.")
        )
        grid1.addWidget(self.extracut_cb, 5, 0)

        # Probe depth
        self.pdepth_label = QtWidgets.QLabel('%s:' % _("Probe Z depth"))
        self.pdepth_label.setToolTip(
            _("The maximum depth that the probe is allowed\n"
              "to probe. Negative value, in current units.")
        )
        grid1.addWidget(self.pdepth_label, 6, 0)
        self.pdepth_entry = FCEntry()
        grid1.addWidget(self.pdepth_entry, 6, 1)

        # Probe feedrate
        self.feedrate_probe_label = QtWidgets.QLabel('%s:' % _("Feedrate Probe"))
        self.feedrate_probe_label.setToolTip(
            _("The feedrate used while the probe is probing.")
        )
        grid1.addWidget(self.feedrate_probe_label, 7, 0)
        self.feedrate_probe_entry = FCEntry()
        grid1.addWidget(self.feedrate_probe_entry, 7, 1)

        # Spindle direction
        spindle_dir_label = QtWidgets.QLabel('%s:' % _('Spindle dir.'))
        spindle_dir_label.setToolTip(
            _("This sets the direction that the spindle is rotating.\n"
              "It can be either:\n"
              "- CW = clockwise or\n"
              "- CCW = counter clockwise")
        )

        self.spindledir_radio = RadioSet([{'label': _('CW'), 'value': 'CW'},
                                          {'label': _('CCW'), 'value': 'CCW'}])
        grid1.addWidget(spindle_dir_label, 8, 0)
        grid1.addWidget(self.spindledir_radio, 8, 1)

        # Fast Move from Z Toolchange
        fplungelabel = QtWidgets.QLabel('%s:' % _('Fast Plunge'))
        fplungelabel.setToolTip(
            _("By checking this, the vertical move from\n"
              "Z_Toolchange to Z_move is done with G0,\n"
              "meaning the fastest speed available.\n"
              "WARNING: the move is done at Toolchange X,Y coords.")
        )
        self.fplunge_cb = FCCheckBox()
        grid1.addWidget(fplungelabel, 9, 0)
        grid1.addWidget(self.fplunge_cb, 9, 1)

        # Size of trace segment on X axis
        segx_label = QtWidgets.QLabel('%s:' % _("Seg. X size"))
        segx_label.setToolTip(
            _("The size of the trace segment on the X axis.\n"
              "Useful for auto-leveling.\n"
              "A value of 0 means no segmentation on the X axis.")
        )
        grid1.addWidget(segx_label, 10, 0)
        self.segx_entry = FCEntry()
        grid1.addWidget(self.segx_entry, 10, 1)

        # Size of trace segment on Y axis
        segy_label = QtWidgets.QLabel('%s:' % _("Seg. Y size"))
        segy_label.setToolTip(
            _("The size of the trace segment on the Y axis.\n"
              "Useful for auto-leveling.\n"
              "A value of 0 means no segmentation on the Y axis.")
        )
        grid1.addWidget(segy_label, 11, 0)
        self.segy_entry = FCEntry()
        grid1.addWidget(self.segy_entry, 11, 1)

        self.layout.addStretch()


class GeometryEditorPrefGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        # OptionsGroupUI.__init__(self, "Gerber Adv. Options Preferences", parent=parent)
        super(GeometryEditorPrefGroupUI, self).__init__(self)

        self.setTitle(str(_("Geometry Editor")))

        # Advanced Geometry Parameters
        self.param_label = QtWidgets.QLabel("<b>%s:</b>" % _("Parameters"))
        self.param_label.setToolTip(
            _("A list of Geometry Editor parameters.")
        )
        self.layout.addWidget(self.param_label)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        # Selection Limit
        self.sel_limit_label = QtWidgets.QLabel('%s:' % _("Selection limit"))
        self.sel_limit_label.setToolTip(
            _("Set the number of selected geometry\n"
              "items above which the utility geometry\n"
              "becomes just a selection rectangle.\n"
              "Increases the performance when moving a\n"
              "large number of geometric elements.")
        )
        self.sel_limit_entry = IntEntry()

        grid0.addWidget(self.sel_limit_label, 0, 0)
        grid0.addWidget(self.sel_limit_entry, 0, 1)

        # Milling Type
        milling_type_label = QtWidgets.QLabel('%s:' % _('Milling Type'))
        milling_type_label.setToolTip(
            _("Milling type:\n"
              "- climb / best for precision milling and to reduce tool usage\n"
              "- conventional / useful when there is no backlash compensation")
        )
        self.milling_type_radio = RadioSet([{'label': _('Climb'), 'value': 'cl'},
                                            {'label': _('Conv.'), 'value': 'cv'}])
        grid0.addWidget(milling_type_label, 1, 0)
        grid0.addWidget(self.milling_type_radio, 1, 1)

        self.layout.addStretch()


class CNCJobGenPrefGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        # OptionsGroupUI.__init__(self, "CNC Job General Preferences", parent=None)
        super(CNCJobGenPrefGroupUI, self).__init__(self)

        self.setTitle(str(_("CNC Job General")))

        # ## Plot options
        self.plot_options_label = QtWidgets.QLabel("<b>%s:</b>" % _("Plot Options"))
        self.layout.addWidget(self.plot_options_label)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)
        # grid0.setColumnStretch(1, 1)
        # grid0.setColumnStretch(2, 1)

        # Plot CB
        # self.plot_cb = QtWidgets.QCheckBox('Plot')
        self.plot_cb = FCCheckBox(_('Plot Object'))
        self.plot_cb.setToolTip(_("Plot (show) this object."))
        grid0.addWidget(self.plot_cb, 0, 0)

        # Plot Kind
        self.cncplot_method_label = QtWidgets.QLabel('%s:' % _("Plot kind"))
        self.cncplot_method_label.setToolTip(
            _("This selects the kind of geometries on the canvas to plot.\n"
              "Those can be either of type 'Travel' which means the moves\n"
              "above the work piece or it can be of type 'Cut',\n"
              "which means the moves that cut into the material.")
        )

        self.cncplot_method_radio = RadioSet([
            {"label": _("All"), "value": "all"},
            {"label": _("Travel"), "value": "travel"},
            {"label": _("Cut"), "value": "cut"}
        ], stretch=False)

        grid0.addWidget(self.cncplot_method_label, 1, 0)
        grid0.addWidget(self.cncplot_method_radio, 1, 1)
        grid0.addWidget(QtWidgets.QLabel(''), 1, 2)

        # Display Annotation
        self.annotation_label = QtWidgets.QLabel('%s:' % _("Display Annotation"))
        self.annotation_label.setToolTip(
            _("This selects if to display text annotation on the plot.\n"
              "When checked it will display numbers in order for each end\n"
              "of a travel line."
              )
        )
        self.annotation_cb = FCCheckBox()

        grid0.addWidget(self.annotation_label, 2, 0)
        grid0.addWidget(self.annotation_cb, 2, 1)
        grid0.addWidget(QtWidgets.QLabel(''), 2, 2)

        # ###################################################################
        # Number of circle steps for circular aperture linear approximation #
        # ###################################################################
        self.steps_per_circle_label = QtWidgets.QLabel('%s:' % _("Circle Steps"))
        self.steps_per_circle_label.setToolTip(
            _("The number of circle steps for <b>GCode</b> \n"
              "circle and arc shapes linear approximation.")
        )
        grid0.addWidget(self.steps_per_circle_label, 3, 0)
        self.steps_per_circle_entry = IntEntry()
        grid0.addWidget(self.steps_per_circle_entry, 3, 1)

        # Tool dia for plot
        tdlabel = QtWidgets.QLabel('%s:' % _('Travel dia'))
        tdlabel.setToolTip(
            _("The width of the travel lines to be\n"
              "rendered in the plot.")
        )
        self.tooldia_entry = LengthEntry()
        grid0.addWidget(tdlabel, 4, 0)
        grid0.addWidget(self.tooldia_entry, 4, 1)

        # add a space
        grid0.addWidget(QtWidgets.QLabel(''), 5, 0)

        # Number of decimals to use in GCODE coordinates
        cdeclabel = QtWidgets.QLabel('%s:' % _('Coordinates decimals'))
        cdeclabel.setToolTip(
            _("The number of decimals to be used for \n"
              "the X, Y, Z coordinates in CNC code (GCODE, etc.)")
        )
        self.coords_dec_entry = IntEntry()
        grid0.addWidget(cdeclabel, 6, 0)
        grid0.addWidget(self.coords_dec_entry, 6, 1)

        # Number of decimals to use in GCODE feedrate
        frdeclabel = QtWidgets.QLabel('%s:' % _('Feedrate decimals'))
        frdeclabel.setToolTip(
            _("The number of decimals to be used for \n"
              "the Feedrate parameter in CNC code (GCODE, etc.)")
        )
        self.fr_dec_entry = IntEntry()
        grid0.addWidget(frdeclabel, 7, 0)
        grid0.addWidget(self.fr_dec_entry, 7, 1)

        # The type of coordinates used in the Gcode: Absolute or Incremental
        coords_type_label = QtWidgets.QLabel('%s:' % _('Coordinates type'))
        coords_type_label.setToolTip(
            _("The type of coordinates to be used in Gcode.\n"
              "Can be:\n"
              "- Absolute G90 -> the reference is the origin x=0, y=0\n"
              "- Incremental G91 -> the reference is the previous position")
        )
        self.coords_type_radio = RadioSet([
            {"label": _("Absolute G90"), "value": "G90"},
            {"label": _("Incremental G91"), "value": "G91"}
        ], orientation='vertical', stretch=False)
        grid0.addWidget(coords_type_label, 8, 0)
        grid0.addWidget(self.coords_type_radio, 8, 1)

        # hidden for the time being, until implemented
        coords_type_label.hide()
        self.coords_type_radio.hide()

        self.layout.addStretch()


class CNCJobOptPrefGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        # OptionsGroupUI.__init__(self, "CNC Job Options Preferences", parent=None)
        super(CNCJobOptPrefGroupUI, self).__init__(self)

        self.setTitle(str(_("CNC Job Options")))

        # ## Export G-Code
        self.export_gcode_label = QtWidgets.QLabel("<b>%s:</b>" % _("Export G-Code"))
        self.export_gcode_label.setToolTip(
            _("Export and save G-Code to\n"
              "make this object to a file.")
        )
        self.layout.addWidget(self.export_gcode_label)

        settings = QSettings("Open Source", "FlatCAM")
        if settings.contains("textbox_font_size"):
            tb_fsize = settings.value('textbox_font_size', type=int)
        else:
            tb_fsize = 10
        font = QtGui.QFont()
        font.setPointSize(tb_fsize)

        # Prepend to G-Code
        prependlabel = QtWidgets.QLabel('%s:' % _('Prepend to G-Code'))
        prependlabel.setToolTip(
            _("Type here any G-Code commands you would\n"
              "like to add at the beginning of the G-Code file.")
        )
        self.layout.addWidget(prependlabel)

        self.prepend_text = FCTextArea()
        self.layout.addWidget(self.prepend_text)
        self.prepend_text.setFont(font)

        # Append text to G-Code
        appendlabel = QtWidgets.QLabel('%s:' % _('Append to G-Code'))
        appendlabel.setToolTip(
            _("Type here any G-Code commands you would\n"
              "like to append to the generated file.\n"
              "I.e.: M2 (End of program)")
        )
        self.layout.addWidget(appendlabel)

        self.append_text = FCTextArea()
        self.layout.addWidget(self.append_text)
        self.append_text.setFont(font)

        self.layout.addStretch()


class CNCJobAdvOptPrefGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        # OptionsGroupUI.__init__(self, "CNC Job Advanced Options Preferences", parent=None)
        super(CNCJobAdvOptPrefGroupUI, self).__init__(self)

        self.setTitle(str(_("CNC Job Adv. Options")))

        # ## Export G-Code
        self.export_gcode_label = QtWidgets.QLabel("<b>%s:</b>" % _("Export CNC Code"))
        self.export_gcode_label.setToolTip(
            _("Export and save G-Code to\n"
              "make this object to a file.")
        )
        self.layout.addWidget(self.export_gcode_label)

        # Prepend to G-Code
        toolchangelabel = QtWidgets.QLabel('%s:' % _('Toolchange G-Code'))
        toolchangelabel.setToolTip(
            _(
                "Type here any G-Code commands you would\n"
                "like to be executed when Toolchange event is encountered.\n"
                "This will constitute a Custom Toolchange GCode,\n"
                "or a Toolchange Macro.\n"
                "The FlatCAM variables are surrounded by '%' symbol.\n\n"
                "WARNING: it can be used only with a postprocessor file\n"
                "that has 'toolchange_custom' in it's name and this is built\n"
                "having as template the 'Toolchange Custom' posprocessor file."
            )
        )
        self.layout.addWidget(toolchangelabel)

        settings = QSettings("Open Source", "FlatCAM")
        if settings.contains("textbox_font_size"):
            tb_fsize = settings.value('textbox_font_size', type=int)
        else:
            tb_fsize = 10
        font = QtGui.QFont()
        font.setPointSize(tb_fsize)

        self.toolchange_text = FCTextArea()
        self.layout.addWidget(self.toolchange_text)
        self.toolchange_text.setFont(font)

        hlay = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay)

        # Toolchange Replacement GCode
        self.toolchange_cb = FCCheckBox(label='%s' % _('Use Toolchange Macro'))
        self.toolchange_cb.setToolTip(
            _("Check this box if you want to use\n"
              "a Custom Toolchange GCode (macro).")
        )
        hlay.addWidget(self.toolchange_cb)
        hlay.addStretch()

        hlay1 = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay1)

        # Variable list
        self.tc_variable_combo = FCComboBox()
        self.tc_variable_combo.setToolTip(
            _("A list of the FlatCAM variables that can be used\n"
              "in the Toolchange event.\n"
              "They have to be surrounded by the '%' symbol")
        )
        hlay1.addWidget(self.tc_variable_combo)

        # Populate the Combo Box
        variables = [_('Parameters'), 'tool', 'tooldia', 't_drills', 'x_toolchange', 'y_toolchange', 'z_toolchange',
                     'z_cut', 'z_move', 'z_depthpercut', 'spindlespeed', 'dwelltime']
        self.tc_variable_combo.addItems(variables)
        self.tc_variable_combo.setItemData(0, _("FlatCAM CNC parameters"), Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(1, 'tool = %s' % _("tool number"), Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(2, 'tooldia = %s' % _("tool diameter"), Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(3, 't_drills = %s' % _("for Excellon, total number of drills"),
                                           Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(4, 'x_toolchange = %s' % _("X coord for Toolchange"), Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(5, 'y_toolchange = %s' % _("y_toolchange = Y coord for Toolchange"),
                                           Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(6, 'z_toolchange = %s' % _("Z coord for Toolchange"), Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(7, 'z_cut = %s' % _("Z depth for the cut"), Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(8, 'z_move = %s' % _("Z height for travel"), Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(9, 'z_depthpercut = %s' % _("the step value for multidepth cut"),
                                           Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(10, 'spindlesspeed = %s' % _("the value for the spindle speed"),
                                           Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(11,
                                           _("dwelltime = time to dwell to allow the spindle to reach it's set RPM"),
                                           Qt.ToolTipRole)

        hlay1.addStretch()

        # Insert Variable into the Toolchange G-Code Text Box
        # self.tc_insert_buton = FCButton("Insert")
        # self.tc_insert_buton.setToolTip(
        #     "Insert the variable in the GCode Box\n"
        #     "surrounded by the '%' symbol."
        # )
        # hlay1.addWidget(self.tc_insert_buton)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        grid0.addWidget(QtWidgets.QLabel(''), 1, 0, 1, 2)

        # Annotation Font Size
        self.annotation_fontsize_label = QtWidgets.QLabel('%s:' % _("Annotation Size"))
        self.annotation_fontsize_label.setToolTip(
            _("The font size of the annotation text. In pixels.")
        )
        grid0.addWidget(self.annotation_fontsize_label, 2, 0)
        self.annotation_fontsize_sp = FCSpinner()
        grid0.addWidget(self.annotation_fontsize_sp, 2, 1)
        grid0.addWidget(QtWidgets.QLabel(''), 2, 2)

        # Annotation Font Color
        self.annotation_color_label = QtWidgets.QLabel('%s:' % _('Annotation Color'))
        self.annotation_color_label.setToolTip(
            _("Set the font color for the annotation texts.")
        )
        self.annotation_fontcolor_entry = FCEntry()
        self.annotation_fontcolor_button = QtWidgets.QPushButton()
        self.annotation_fontcolor_button.setFixedSize(15, 15)

        self.form_box_child = QtWidgets.QHBoxLayout()
        self.form_box_child.setContentsMargins(0, 0, 0, 0)
        self.form_box_child.addWidget(self.annotation_fontcolor_entry)
        self.form_box_child.addWidget(self.annotation_fontcolor_button, alignment=Qt.AlignRight)
        self.form_box_child.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        color_widget = QtWidgets.QWidget()
        color_widget.setLayout(self.form_box_child)
        grid0.addWidget(self.annotation_color_label, 3, 0)
        grid0.addWidget(color_widget, 3, 1)
        grid0.addWidget(QtWidgets.QLabel(''), 3, 2)

        self.layout.addStretch()


class ToolsNCCPrefGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        # OptionsGroupUI.__init__(self, "NCC Tool Options", parent=parent)
        super(ToolsNCCPrefGroupUI, self).__init__(self)

        self.setTitle(str(_("NCC Tool Options")))

        # ## Clear non-copper regions
        self.clearcopper_label = QtWidgets.QLabel("<b>%s:</b>" % _("Parameters"))
        self.clearcopper_label.setToolTip(
            _("Create a Geometry object with\n"
              "toolpaths to cut all non-copper regions.")
        )
        self.layout.addWidget(self.clearcopper_label)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        ncctdlabel = QtWidgets.QLabel('%s:' % _('Tools dia'))
        ncctdlabel.setToolTip(
            _("Diameters of the cutting tools, separated by ','")
        )
        grid0.addWidget(ncctdlabel, 0, 0)
        self.ncc_tool_dia_entry = FCEntry()
        grid0.addWidget(self.ncc_tool_dia_entry, 0, 1)

        # Tool Type Radio Button
        self.tool_type_label = QtWidgets.QLabel('%s:' % _('Tool Type'))
        self.tool_type_label.setToolTip(
            _("Default tool type:\n"
              "- 'V-shape'\n"
              "- Circular")
        )

        self.tool_type_radio = RadioSet([{'label': _('V-shape'), 'value': 'V'},
                                         {'label': _('Circular'), 'value': 'C1'}])
        self.tool_type_radio.setToolTip(
            _("Default tool type:\n"
              "- 'V-shape'\n"
              "- Circular")
        )

        grid0.addWidget(self.tool_type_label, 1, 0)
        grid0.addWidget(self.tool_type_radio, 1, 1)

        # Tip Dia
        self.tipdialabel = QtWidgets.QLabel('%s:' % _('V-Tip Dia'))
        self.tipdialabel.setToolTip(
            _("The tip diameter for V-Shape Tool"))
        self.tipdia_entry = LengthEntry()

        grid0.addWidget(self.tipdialabel, 2, 0)
        grid0.addWidget(self.tipdia_entry, 2, 1)

        # Tip Angle
        self.tipanglelabel = QtWidgets.QLabel('%s:' % _('V-Tip Angle'))
        self.tipanglelabel.setToolTip(
            _("The tip angle for V-Shape Tool.\n"
              "In degree."))
        self.tipangle_entry = LengthEntry()

        grid0.addWidget(self.tipanglelabel, 3, 0)
        grid0.addWidget(self.tipangle_entry, 3, 1)

        # Milling Type Radio Button
        self.milling_type_label = QtWidgets.QLabel('%s:' % _('Milling Type'))
        self.milling_type_label.setToolTip(
            _("Milling type when the selected tool is of type: 'iso_op':\n"
              "- climb / best for precision milling and to reduce tool usage\n"
              "- conventional / useful when there is no backlash compensation")
        )

        self.milling_type_radio = RadioSet([{'label': _('Climb'), 'value': 'cl'},
                                            {'label': _('Conv.'), 'value': 'cv'}])
        self.milling_type_radio.setToolTip(
            _("Milling type when the selected tool is of type: 'iso_op':\n"
              "- climb / best for precision milling and to reduce tool usage\n"
              "- conventional / useful when there is no backlash compensation")
        )

        grid0.addWidget(self.milling_type_label, 4, 0)
        grid0.addWidget(self.milling_type_radio, 4, 1)

        # Tool order Radio Button
        self.ncc_order_label = QtWidgets.QLabel('%s:' % _('Tool order'))
        self.ncc_order_label.setToolTip(_("This set the way that the tools in the tools table are used.\n"
                                          "'No' --> means that the used order is the one in the tool table\n"
                                          "'Forward' --> means that the tools will be ordered from small to big\n"
                                          "'Reverse' --> menas that the tools will ordered from big to small\n\n"
                                          "WARNING: using rest machining will automatically set the order\n"
                                          "in reverse and disable this control."))

        self.ncc_order_radio = RadioSet([{'label': _('No'), 'value': 'no'},
                                         {'label': _('Forward'), 'value': 'fwd'},
                                         {'label': _('Reverse'), 'value': 'rev'}])
        self.ncc_order_radio.setToolTip(_("This set the way that the tools in the tools table are used.\n"
                                          "'No' --> means that the used order is the one in the tool table\n"
                                          "'Forward' --> means that the tools will be ordered from small to big\n"
                                          "'Reverse' --> menas that the tools will ordered from big to small\n\n"
                                          "WARNING: using rest machining will automatically set the order\n"
                                          "in reverse and disable this control."))
        grid0.addWidget(self.ncc_order_label, 5, 0)
        grid0.addWidget(self.ncc_order_radio, 5, 1)

        # Cut Z entry
        cutzlabel = QtWidgets.QLabel('%s:' % _('Cut Z'))
        cutzlabel.setToolTip(
           _("Depth of cut into material. Negative value.\n"
             "In FlatCAM units.")
        )
        self.cutz_entry = FloatEntry()
        self.cutz_entry.setToolTip(
           _("Depth of cut into material. Negative value.\n"
             "In FlatCAM units.")
        )

        grid0.addWidget(cutzlabel, 6, 0)
        grid0.addWidget(self.cutz_entry, 6, 1)

        # Overlap Entry
        nccoverlabel = QtWidgets.QLabel('%s:' % _('Overlap Rate'))
        nccoverlabel.setToolTip(
           _("How much (fraction) of the tool width to overlap each tool pass.\n"
             "Example:\n"
             "A value here of 0.25 means 25%% from the tool diameter found above.\n\n"
             "Adjust the value starting with lower values\n"
             "and increasing it if areas that should be cleared are still \n"
             "not cleared.\n"
             "Lower values = faster processing, faster execution on PCB.\n"
             "Higher values = slow processing and slow execution on CNC\n"
             "due of too many paths.")
        )
        self.ncc_overlap_entry = FCDoubleSpinner()
        self.ncc_overlap_entry.set_precision(3)
        self.ncc_overlap_entry.setWrapping(True)
        self.ncc_overlap_entry.setRange(0.000, 0.999)
        self.ncc_overlap_entry.setSingleStep(0.1)
        grid0.addWidget(nccoverlabel, 7, 0)
        grid0.addWidget(self.ncc_overlap_entry, 7, 1)

        # Margin entry
        nccmarginlabel = QtWidgets.QLabel('%s:' % _('Margin'))
        nccmarginlabel.setToolTip(
            _("Bounding box margin.")
        )
        grid0.addWidget(nccmarginlabel, 8, 0)
        self.ncc_margin_entry = FloatEntry()
        grid0.addWidget(self.ncc_margin_entry, 8, 1)

        # Method
        methodlabel = QtWidgets.QLabel('%s:' % _('Method'))
        methodlabel.setToolTip(
            _("Algorithm for non-copper clearing:<BR>"
              "<B>Standard</B>: Fixed step inwards.<BR>"
              "<B>Seed-based</B>: Outwards from seed.<BR>"
              "<B>Line-based</B>: Parallel lines.")
        )
        grid0.addWidget(methodlabel, 9, 0)
        self.ncc_method_radio = RadioSet([
            {"label": _("Standard"), "value": "standard"},
            {"label": _("Seed-based"), "value": "seed"},
            {"label": _("Straight lines"), "value": "lines"}
        ], orientation='vertical', stretch=False)
        grid0.addWidget(self.ncc_method_radio, 9, 1)

        # Connect lines
        pathconnectlabel = QtWidgets.QLabel('%s:' % _("Connect"))
        pathconnectlabel.setToolTip(
            _("Draw lines between resulting\n"
              "segments to minimize tool lifts.")
        )
        grid0.addWidget(pathconnectlabel, 10, 0)
        self.ncc_connect_cb = FCCheckBox()
        grid0.addWidget(self.ncc_connect_cb, 10, 1)

        # Contour Checkbox
        contourlabel = QtWidgets.QLabel('%s:' % _("Contour"))
        contourlabel.setToolTip(
           _("Cut around the perimeter of the polygon\n"
             "to trim rough edges.")
        )
        grid0.addWidget(contourlabel, 11, 0)
        self.ncc_contour_cb = FCCheckBox()
        grid0.addWidget(self.ncc_contour_cb, 11, 1)

        # Rest machining CheckBox
        restlabel = QtWidgets.QLabel('%s:' % _("Rest M."))
        restlabel.setToolTip(
            _("If checked, use 'rest machining'.\n"
              "Basically it will clear copper outside PCB features,\n"
              "using the biggest tool and continue with the next tools,\n"
              "from bigger to smaller, to clear areas of copper that\n"
              "could not be cleared by previous tool, until there is\n"
              "no more copper to clear or there are no more tools.\n"
              "If not checked, use the standard algorithm.")
        )
        grid0.addWidget(restlabel, 12, 0)
        self.ncc_rest_cb = FCCheckBox()
        grid0.addWidget(self.ncc_rest_cb, 12, 1)

        # ## NCC Offset choice
        self.ncc_offset_choice_label = QtWidgets.QLabel('%s:' % _("Offset"))
        self.ncc_offset_choice_label.setToolTip(
            _("If used, it will add an offset to the copper features.\n"
              "The copper clearing will finish to a distance\n"
              "from the copper features.\n"
              "The value can be between 0 and 10 FlatCAM units.")
        )
        grid0.addWidget(self.ncc_offset_choice_label, 13, 0)
        self.ncc_choice_offset_cb = FCCheckBox()
        grid0.addWidget(self.ncc_choice_offset_cb, 13, 1)

        # ## NCC Offset value
        self.ncc_offset_label = QtWidgets.QLabel('%s:' % _("Offset value"))
        self.ncc_offset_label.setToolTip(
            _("If used, it will add an offset to the copper features.\n"
              "The copper clearing will finish to a distance\n"
              "from the copper features.\n"
              "The value can be between 0 and 10 FlatCAM units.")
        )
        grid0.addWidget(self.ncc_offset_label, 14, 0)
        self.ncc_offset_spinner = FCDoubleSpinner()
        self.ncc_offset_spinner.set_range(0.00, 10.00)
        self.ncc_offset_spinner.set_precision(4)
        self.ncc_offset_spinner.setWrapping(True)
        self.ncc_offset_spinner.setSingleStep(0.1)

        grid0.addWidget(self.ncc_offset_spinner, 14, 1)

        # ## Reference
        self.reference_radio = RadioSet([{'label': _('Itself'), 'value': 'itself'},
                                         {"label": _("Area"), "value": "area"},
                                         {'label': _('Ref'), 'value': 'box'}])
        reference_label = QtWidgets.QLabel('%s:' % _("Reference"))
        reference_label.setToolTip(
            _("- 'Itself' -  the non copper clearing extent\n"
              "is based on the object that is copper cleared.\n "
              "- 'Area Selection' - left mouse click to start selection of the area to be painted.\n"
              "Keeping a modifier key pressed (CTRL or SHIFT) will allow to add multiple areas.\n"
              "- 'Reference Object' -  will do non copper clearing within the area\n"
              "specified by another object.")
        )
        grid0.addWidget(reference_label, 15, 0)
        grid0.addWidget(self.reference_radio, 15, 1)

        # ## Plotting type
        self.ncc_plotting_radio = RadioSet([{'label': _('Normal'), 'value': 'normal'},
                                            {"label": _("Progressive"), "value": "progressive"}])
        plotting_label = QtWidgets.QLabel('%s:' % _("NCC Plotting"))
        plotting_label.setToolTip(
            _("- 'Normal' -  normal plotting, done at the end of the NCC job\n"
              "- 'Progressive' - after each shape is generated it will be plotted.")
        )
        grid0.addWidget(plotting_label, 16, 0)
        grid0.addWidget(self.ncc_plotting_radio, 16, 1)

        self.layout.addStretch()


class ToolsCutoutPrefGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        # OptionsGroupUI.__init__(self, "Cutout Tool Options", parent=parent)
        super(ToolsCutoutPrefGroupUI, self).__init__(self)

        self.setTitle(str(_("Cutout Tool Options")))

        # ## Board cuttout
        self.board_cutout_label = QtWidgets.QLabel("<b>%s:</b>" % _("Parameters"))
        self.board_cutout_label.setToolTip(
            _("Create toolpaths to cut around\n"
              "the PCB and separate it from\n"
              "the original board.")
        )
        self.layout.addWidget(self.board_cutout_label)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        tdclabel = QtWidgets.QLabel('%s:' % _('Tool dia'))
        tdclabel.setToolTip(
            _("Diameter of the tool used to cutout\n"
              "the PCB shape out of the surrounding material.")
        )
        grid0.addWidget(tdclabel, 0, 0)
        self.cutout_tooldia_entry = LengthEntry()
        grid0.addWidget(self.cutout_tooldia_entry, 0, 1)

        # Object kind
        kindlabel = QtWidgets.QLabel('%s:' % _('Obj kind'))
        kindlabel.setToolTip(
            _("Choice of what kind the object we want to cutout is.<BR>"
              "- <B>Single</B>: contain a single PCB Gerber outline object.<BR>"
              "- <B>Panel</B>: a panel PCB Gerber object, which is made\n"
              "out of many individual PCB outlines.")
        )
        grid0.addWidget(kindlabel, 1, 0)
        self.obj_kind_combo = RadioSet([
            {"label": _("Single"), "value": "single"},
            {"label": _("Panel"), "value": "panel"},
        ])
        grid0.addWidget(self.obj_kind_combo, 1, 1)

        marginlabel = QtWidgets.QLabel('%s:' % _('Margin'))
        marginlabel.setToolTip(
            _("Margin over bounds. A positive value here\n"
              "will make the cutout of the PCB further from\n"
              "the actual PCB border")
        )
        grid0.addWidget(marginlabel, 2, 0)
        self.cutout_margin_entry = LengthEntry()
        grid0.addWidget(self.cutout_margin_entry, 2, 1)

        gaplabel = QtWidgets.QLabel('%s:' % _('Gap size'))
        gaplabel.setToolTip(
            _("The size of the bridge gaps in the cutout\n"
              "used to keep the board connected to\n"
              "the surrounding material (the one \n"
              "from which the PCB is cutout).")
        )
        grid0.addWidget(gaplabel, 3, 0)
        self.cutout_gap_entry = LengthEntry()
        grid0.addWidget(self.cutout_gap_entry, 3, 1)

        gaps_label = QtWidgets.QLabel('%s:' % _('Gaps'))
        gaps_label.setToolTip(
            _("Number of gaps used for the cutout.\n"
              "There can be maximum 8 bridges/gaps.\n"
              "The choices are:\n"
              "- None  - no gaps\n"
              "- lr    - left + right\n"
              "- tb    - top + bottom\n"
              "- 4     - left + right +top + bottom\n"
              "- 2lr   - 2*left + 2*right\n"
              "- 2tb  - 2*top + 2*bottom\n"
              "- 8     - 2*left + 2*right +2*top + 2*bottom")
        )
        grid0.addWidget(gaps_label, 4, 0)
        self.gaps_combo = FCComboBox()
        grid0.addWidget(self.gaps_combo, 4, 1)

        gaps_items = ['None', 'LR', 'TB', '4', '2LR', '2TB', '8']
        for it in gaps_items:
            self.gaps_combo.addItem(it)
            self.gaps_combo.setStyleSheet('background-color: rgb(255,255,255)')

        # Surrounding convex box shape
        self.convex_box = FCCheckBox()
        self.convex_box_label = QtWidgets.QLabel('%s:' % _("Convex Sh."))
        self.convex_box_label.setToolTip(
            _("Create a convex shape surrounding the entire PCB.\n"
              "Used only if the source object type is Gerber.")
        )
        grid0.addWidget(self.convex_box_label, 5, 0)
        grid0.addWidget(self.convex_box, 5, 1)

        self.layout.addStretch()


class Tools2sidedPrefGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        # OptionsGroupUI.__init__(self, "2sided Tool Options", parent=parent)
        super(Tools2sidedPrefGroupUI, self).__init__(self)

        self.setTitle(str(_("2Sided Tool Options")))

        # ## Board cuttout
        self.dblsided_label = QtWidgets.QLabel("<b>%s:</b>" % _("Parameters"))
        self.dblsided_label.setToolTip(
            _("A tool to help in creating a double sided\n"
              "PCB using alignment holes.")
        )
        self.layout.addWidget(self.dblsided_label)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        # ## Drill diameter for alignment holes
        self.drill_dia_entry = LengthEntry()
        self.dd_label = QtWidgets.QLabel('%s:' % _("Drill dia"))
        self.dd_label.setToolTip(
            _("Diameter of the drill for the "
              "alignment holes.")
        )
        grid0.addWidget(self.dd_label, 0, 0)
        grid0.addWidget(self.drill_dia_entry, 0, 1)

        # ## Axis
        self.mirror_axis_radio = RadioSet([{'label': 'X', 'value': 'X'},
                                           {'label': 'Y', 'value': 'Y'}])
        self.mirax_label = QtWidgets.QLabel(_("Mirror Axis:"))
        self.mirax_label.setToolTip(
            _("Mirror vertically (X) or horizontally (Y).")
        )
        # grid_lay.addRow("Mirror Axis:", self.mirror_axis)
        self.empty_lb1 = QtWidgets.QLabel("")
        grid0.addWidget(self.empty_lb1, 1, 0)
        grid0.addWidget(self.mirax_label, 2, 0)
        grid0.addWidget(self.mirror_axis_radio, 2, 1)

        # ## Axis Location
        self.axis_location_radio = RadioSet([{'label': _('Point'), 'value': 'point'},
                                             {'label': _('Box'), 'value': 'box'}])
        self.axloc_label = QtWidgets.QLabel('%s:' % _("Axis Ref"))
        self.axloc_label.setToolTip(
            _("The axis should pass through a <b>point</b> or cut\n "
              "a specified <b>box</b> (in a FlatCAM object) through \n"
              "the center.")
        )
        # grid_lay.addRow("Axis Location:", self.axis_location)
        grid0.addWidget(self.axloc_label, 3, 0)
        grid0.addWidget(self.axis_location_radio, 3, 1)

        self.layout.addStretch()


class ToolsPaintPrefGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        # OptionsGroupUI.__init__(self, "Paint Area Tool Options", parent=parent)
        super(ToolsPaintPrefGroupUI, self).__init__(self)

        self.setTitle(str(_("Paint Tool Options")))

        # ------------------------------
        # ## Paint area
        # ------------------------------
        self.paint_label = QtWidgets.QLabel(_('<b>Parameters:</b>'))
        self.paint_label.setToolTip(
            _("Creates tool paths to cover the\n"
              "whole area of a polygon (remove\n"
              "all copper). You will be asked\n"
              "to click on the desired polygon.")
        )
        self.layout.addWidget(self.paint_label)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        # Tool dia
        ptdlabel = QtWidgets.QLabel('%s:' % _('Tool dia'))
        ptdlabel.setToolTip(
            _("Diameter of the tool to\n"
              "be used in the operation.")
        )
        grid0.addWidget(ptdlabel, 0, 0)

        self.painttooldia_entry = LengthEntry()
        grid0.addWidget(self.painttooldia_entry, 0, 1)

        self.paint_order_label = QtWidgets.QLabel('<b>%s:</b>' % _('Tool order'))
        self.paint_order_label.setToolTip(_("This set the way that the tools in the tools table are used.\n"
                                            "'No' --> means that the used order is the one in the tool table\n"
                                            "'Forward' --> means that the tools will be ordered from small to big\n"
                                            "'Reverse' --> menas that the tools will ordered from big to small\n\n"
                                            "WARNING: using rest machining will automatically set the order\n"
                                            "in reverse and disable this control."))

        self.paint_order_radio = RadioSet([{'label': _('No'), 'value': 'no'},
                                           {'label': _('Forward'), 'value': 'fwd'},
                                           {'label': _('Reverse'), 'value': 'rev'}])
        self.paint_order_radio.setToolTip(_("This set the way that the tools in the tools table are used.\n"
                                            "'No' --> means that the used order is the one in the tool table\n"
                                            "'Forward' --> means that the tools will be ordered from small to big\n"
                                            "'Reverse' --> menas that the tools will ordered from big to small\n\n"
                                            "WARNING: using rest machining will automatically set the order\n"
                                            "in reverse and disable this control."))
        grid0.addWidget(self.paint_order_label, 1, 0)
        grid0.addWidget(self.paint_order_radio, 1, 1)

        # Overlap
        ovlabel = QtWidgets.QLabel('%s:' % _('Overlap Rate'))
        ovlabel.setToolTip(
            _("How much (fraction) of the tool width to overlap each tool pass.\n"
              "Example:\n"
              "A value here of 0.25 means 25%% from the tool diameter found above.\n\n"
              "Adjust the value starting with lower values\n"
              "and increasing it if areas that should be painted are still \n"
              "not painted.\n"
              "Lower values = faster processing, faster execution on PCB.\n"
              "Higher values = slow processing and slow execution on CNC\n"
              "due of too many paths.")
        )
        self.paintoverlap_entry = FCDoubleSpinner()
        self.paintoverlap_entry.set_precision(3)
        self.paintoverlap_entry.setWrapping(True)
        self.paintoverlap_entry.setRange(0.000, 0.999)
        self.paintoverlap_entry.setSingleStep(0.1)
        grid0.addWidget(ovlabel, 2, 0)
        grid0.addWidget(self.paintoverlap_entry, 2, 1)

        # Margin
        marginlabel = QtWidgets.QLabel('%s:' % _('Margin'))
        marginlabel.setToolTip(
            _("Distance by which to avoid\n"
              "the edges of the polygon to\n"
              "be painted.")
        )
        grid0.addWidget(marginlabel, 3, 0)
        self.paintmargin_entry = LengthEntry()
        grid0.addWidget(self.paintmargin_entry, 3, 1)

        # Method
        methodlabel = QtWidgets.QLabel('%s:' % _('Method'))
        methodlabel.setToolTip(
            _("Algorithm for non-copper clearing:<BR>"
              "<B>Standard</B>: Fixed step inwards.<BR>"
              "<B>Seed-based</B>: Outwards from seed.<BR>"
              "<B>Line-based</B>: Parallel lines.")
        )
        grid0.addWidget(methodlabel, 4, 0)
        self.paintmethod_combo = RadioSet([
            {"label": _("Standard"), "value": "standard"},
            {"label": _("Seed-based"), "value": "seed"},
            {"label": _("Straight lines"), "value": "lines"}
        ], orientation='vertical', stretch=False)
        grid0.addWidget(self.paintmethod_combo, 4, 1)

        # Connect lines
        pathconnectlabel = QtWidgets.QLabel('%s:' % _("Connect"))
        pathconnectlabel.setToolTip(
            _("Draw lines between resulting\n"
              "segments to minimize tool lifts.")
        )
        grid0.addWidget(pathconnectlabel, 5, 0)
        self.pathconnect_cb = FCCheckBox()
        grid0.addWidget(self.pathconnect_cb, 5, 1)

        # Paint contour
        contourlabel = QtWidgets.QLabel('%s:' % _("Contour"))
        contourlabel.setToolTip(
            _("Cut around the perimeter of the polygon\n"
              "to trim rough edges.")
        )
        grid0.addWidget(contourlabel, 6, 0)
        self.contour_cb = FCCheckBox()
        grid0.addWidget(self.contour_cb, 6, 1)

        # Polygon selection
        selectlabel = QtWidgets.QLabel('%s:' % _('Selection'))
        selectlabel.setToolTip(
            _("How to select Polygons to be painted.\n\n"
              "- 'Area Selection' - left mouse click to start selection of the area to be painted.\n"
              "Keeping a modifier key pressed (CTRL or SHIFT) will allow to add multiple areas.\n"
              "- 'All Polygons' - the Paint will start after click.\n"
              "- 'Reference Object' -  will do non copper clearing within the area\n"
              "specified by another object.")
        )
        self.selectmethod_combo = RadioSet([
            {"label": _("Single"), "value": "single"},
            {"label": _("Area"), "value": "area"},
            {"label": _("All"), "value": "all"},
            {"label": _("Ref."), "value": "ref"}
        ])
        grid0.addWidget(selectlabel, 7, 0)
        grid0.addWidget(self.selectmethod_combo, 7, 1)

        # ## Plotting type
        self.paint_plotting_radio = RadioSet([{'label': _('Normal'), 'value': 'normal'},
                                              {"label": _("Progressive"), "value": "progressive"}])
        plotting_label = QtWidgets.QLabel('%s:' % _("Paint Plotting"))
        plotting_label.setToolTip(
            _("- 'Normal' -  normal plotting, done at the end of the Paint job\n"
              "- 'Progressive' - after each shape is generated it will be plotted.")
        )
        grid0.addWidget(plotting_label, 8, 0)
        grid0.addWidget(self.paint_plotting_radio, 8, 1)

        self.layout.addStretch()


class ToolsFilmPrefGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        # OptionsGroupUI.__init__(self, "Cutout Tool Options", parent=parent)
        super(ToolsFilmPrefGroupUI, self).__init__(self)

        self.setTitle(str(_("Film Tool Options")))

        # ## Board cuttout
        self.film_label = QtWidgets.QLabel("<b>%s:</b>" % _("Parameters"))
        self.film_label.setToolTip(
            _("Create a PCB film from a Gerber or Geometry\n"
              "FlatCAM object.\n"
              "The file is saved in SVG format.")
        )
        self.layout.addWidget(self.film_label)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        self.film_type_radio = RadioSet([{'label': 'Pos', 'value': 'pos'},
                                         {'label': 'Neg', 'value': 'neg'}])
        ftypelbl = QtWidgets.QLabel('%s:' % _('Film Type'))
        ftypelbl.setToolTip(
            _("Generate a Positive black film or a Negative film.\n"
              "Positive means that it will print the features\n"
              "with black on a white canvas.\n"
              "Negative means that it will print the features\n"
              "with white on a black canvas.\n"
              "The Film format is SVG.")
        )
        grid0.addWidget(ftypelbl, 0, 0)
        grid0.addWidget(self.film_type_radio, 0, 1)

        # Film Color
        self.film_color_label = QtWidgets.QLabel('%s:' % _('Film Color'))
        self.film_color_label.setToolTip(
            _("Set the film color when positive film is selected.")
        )
        self.film_color_entry = FCEntry()
        self.film_color_button = QtWidgets.QPushButton()
        self.film_color_button.setFixedSize(15, 15)

        self.form_box_child = QtWidgets.QHBoxLayout()
        self.form_box_child.setContentsMargins(0, 0, 0, 0)
        self.form_box_child.addWidget(self.film_color_entry)
        self.form_box_child.addWidget(self.film_color_button, alignment=Qt.AlignRight)
        self.form_box_child.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        film_color_widget = QtWidgets.QWidget()
        film_color_widget.setLayout(self.form_box_child)
        grid0.addWidget(self.film_color_label, 1, 0)
        grid0.addWidget(film_color_widget, 1, 1)

        self.film_boundary_entry = FCEntry()
        self.film_boundary_label = QtWidgets.QLabel('%s:' % _("Border"))
        self.film_boundary_label.setToolTip(
            _("Specify a border around the object.\n"
              "Only for negative film.\n"
              "It helps if we use as a Box Object the same \n"
              "object as in Film Object. It will create a thick\n"
              "black bar around the actual print allowing for a\n"
              "better delimitation of the outline features which are of\n"
              "white color like the rest and which may confound with the\n"
              "surroundings if not for this border.")
        )
        grid0.addWidget(self.film_boundary_label, 2, 0)
        grid0.addWidget(self.film_boundary_entry, 2, 1)

        self.film_scale_entry = FCEntry()
        self.film_scale_label = QtWidgets.QLabel('%s:' % _("Scale Stroke"))
        self.film_scale_label.setToolTip(
            _("Scale the line stroke thickness of each feature in the SVG file.\n"
              "It means that the line that envelope each SVG feature will be thicker or thinner,\n"
              "therefore the fine features may be more affected by this parameter.")
        )
        grid0.addWidget(self.film_scale_label, 3, 0)
        grid0.addWidget(self.film_scale_entry, 3, 1)

        self.layout.addStretch()


class ToolsPanelizePrefGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        # OptionsGroupUI.__init__(self, "Cutout Tool Options", parent=parent)
        super(ToolsPanelizePrefGroupUI, self).__init__(self)

        self.setTitle(str(_("Panelize Tool Options")))

        # ## Board cuttout
        self.panelize_label = QtWidgets.QLabel("<b>%s:</b>" % _("Parameters"))
        self.panelize_label.setToolTip(
            _("Create an object that contains an array of (x, y) elements,\n"
              "each element is a copy of the source object spaced\n"
              "at a X distance, Y distance of each other.")
        )
        self.layout.addWidget(self.panelize_label)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        # ## Spacing Columns
        self.pspacing_columns = FCEntry()
        self.spacing_columns_label = QtWidgets.QLabel('%s:' % _("Spacing cols"))
        self.spacing_columns_label.setToolTip(
            _("Spacing between columns of the desired panel.\n"
              "In current units.")
        )
        grid0.addWidget(self.spacing_columns_label, 0, 0)
        grid0.addWidget(self.pspacing_columns, 0, 1)

        # ## Spacing Rows
        self.pspacing_rows = FCEntry()
        self.spacing_rows_label = QtWidgets.QLabel('%s:' % _("Spacing rows"))
        self.spacing_rows_label.setToolTip(
            _("Spacing between rows of the desired panel.\n"
              "In current units.")
        )
        grid0.addWidget(self.spacing_rows_label, 1, 0)
        grid0.addWidget(self.pspacing_rows, 1, 1)

        # ## Columns
        self.pcolumns = FCEntry()
        self.columns_label = QtWidgets.QLabel('%s:' % _("Columns"))
        self.columns_label.setToolTip(
            _("Number of columns of the desired panel")
        )
        grid0.addWidget(self.columns_label, 2, 0)
        grid0.addWidget(self.pcolumns, 2, 1)

        # ## Rows
        self.prows = FCEntry()
        self.rows_label = QtWidgets.QLabel('%s:' % _("Rows"))
        self.rows_label.setToolTip(
            _("Number of rows of the desired panel")
        )
        grid0.addWidget(self.rows_label, 3, 0)
        grid0.addWidget(self.prows, 3, 1)

        # ## Type of resulting Panel object
        self.panel_type_radio = RadioSet([{'label': _('Gerber'), 'value': 'gerber'},
                                          {'label': _('Geo'), 'value': 'geometry'}])
        self.panel_type_label = QtWidgets.QLabel('%s:' % _("Panel Type"))
        self.panel_type_label.setToolTip(
           _("Choose the type of object for the panel object:\n"
             "- Gerber\n"
             "- Geometry")
        )

        grid0.addWidget(self.panel_type_label, 4, 0)
        grid0.addWidget(self.panel_type_radio, 4, 1)

        # ## Constrains
        self.pconstrain_cb = FCCheckBox('%s:' % _("Constrain within"))
        self.pconstrain_cb.setToolTip(
            _("Area define by DX and DY within to constrain the panel.\n"
              "DX and DY values are in current units.\n"
              "Regardless of how many columns and rows are desired,\n"
              "the final panel will have as many columns and rows as\n"
              "they fit completely within selected area.")
        )
        grid0.addWidget(self.pconstrain_cb, 5, 0)

        self.px_width_entry = FCEntry()
        self.x_width_lbl = QtWidgets.QLabel('%s:' % _("Width (DX)"))
        self.x_width_lbl.setToolTip(
            _("The width (DX) within which the panel must fit.\n"
              "In current units.")
        )
        grid0.addWidget(self.x_width_lbl, 6, 0)
        grid0.addWidget(self.px_width_entry, 6, 1)

        self.py_height_entry = FCEntry()
        self.y_height_lbl = QtWidgets.QLabel('%s:' % _("Height (DY)"))
        self.y_height_lbl.setToolTip(
            _("The height (DY)within which the panel must fit.\n"
              "In current units.")
        )
        grid0.addWidget(self.y_height_lbl, 7, 0)
        grid0.addWidget(self.py_height_entry, 7, 1)

        self.layout.addStretch()


class ToolsCalculatorsPrefGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        # OptionsGroupUI.__init__(self, "Calculators Tool Options", parent=parent)
        super(ToolsCalculatorsPrefGroupUI, self).__init__(self)

        self.setTitle(str(_("Calculators Tool Options")))

        # ## V-shape Calculator Tool
        self.vshape_tool_label = QtWidgets.QLabel("<b>%s:</b>" % _("V-Shape Tool Calculator"))
        self.vshape_tool_label.setToolTip(
            _("Calculate the tool diameter for a given V-shape tool,\n"
              "having the tip diameter, tip angle and\n"
              "depth-of-cut as parameters.")
        )
        self.layout.addWidget(self.vshape_tool_label)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        # ## Tip Diameter
        self.tip_dia_entry = FCEntry()
        self.tip_dia_label = QtWidgets.QLabel('%s:' % _("Tip Diameter"))
        self.tip_dia_label.setToolTip(
            _("This is the tool tip diameter.\n"
              "It is specified by manufacturer.")
        )
        grid0.addWidget(self.tip_dia_label, 0, 0)
        grid0.addWidget(self.tip_dia_entry, 0, 1)

        # ## Tip angle
        self.tip_angle_entry = FCEntry()
        self.tip_angle_label = QtWidgets.QLabel('%s:' % _("Tip Angle"))
        self.tip_angle_label.setToolTip(
            _("This is the angle on the tip of the tool.\n"
              "It is specified by manufacturer.")
        )
        grid0.addWidget(self.tip_angle_label, 1, 0)
        grid0.addWidget(self.tip_angle_entry, 1, 1)

        # ## Depth-of-cut Cut Z
        self.cut_z_entry = FCEntry()
        self.cut_z_label = QtWidgets.QLabel('%s:' % _("Cut Z"))
        self.cut_z_label.setToolTip(
            _("This is depth to cut into material.\n"
              "In the CNCJob object it is the CutZ parameter.")
        )
        grid0.addWidget(self.cut_z_label, 2, 0)
        grid0.addWidget(self.cut_z_entry, 2, 1)

        # ## Electroplating Calculator Tool
        self.plate_title_label = QtWidgets.QLabel("<b>%s:</b>" % _("ElectroPlating Calculator"))
        self.plate_title_label.setToolTip(
            _("This calculator is useful for those who plate the via/pad/drill holes,\n"
              "using a method like grahite ink or calcium hypophosphite ink or palladium chloride.")
        )
        self.layout.addWidget(self.plate_title_label)

        grid1 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid1)

        # ## PCB Length
        self.pcblength_entry = FCEntry()
        self.pcblengthlabel = QtWidgets.QLabel('%s:' % _("Board Length"))

        self.pcblengthlabel.setToolTip(_('This is the board length. In centimeters.'))
        grid1.addWidget(self.pcblengthlabel, 0, 0)
        grid1.addWidget(self.pcblength_entry, 0, 1)

        # ## PCB Width
        self.pcbwidth_entry = FCEntry()
        self.pcbwidthlabel = QtWidgets.QLabel('%s:' % _("Board Width"))

        self.pcbwidthlabel.setToolTip(_('This is the board width.In centimeters.'))
        grid1.addWidget(self.pcbwidthlabel, 1, 0)
        grid1.addWidget(self.pcbwidth_entry, 1, 1)

        # ## Current Density
        self.cdensity_label = QtWidgets.QLabel('%s:' % _("Current Density"))
        self.cdensity_entry = FCEntry()

        self.cdensity_label.setToolTip(_("Current density to pass through the board. \n"
                                         "In Amps per Square Feet ASF."))
        grid1.addWidget(self.cdensity_label, 2, 0)
        grid1.addWidget(self.cdensity_entry, 2, 1)

        # ## PCB Copper Growth
        self.growth_label = QtWidgets.QLabel('%s:' % _("Copper Growth"))
        self.growth_entry = FCEntry()

        self.growth_label.setToolTip(_("How thick the copper growth is intended to be.\n"
                                       "In microns."))
        grid1.addWidget(self.growth_label, 3, 0)
        grid1.addWidget(self.growth_entry, 3, 1)

        self.layout.addStretch()


class ToolsTransformPrefGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):

        super(ToolsTransformPrefGroupUI, self).__init__(self)

        self.setTitle(str(_("Transform Tool Options")))

        # ## Transformations
        self.transform_label = QtWidgets.QLabel("<b>%s:</b>" % _("Parameters"))
        self.transform_label.setToolTip(
            _("Various transformations that can be applied\n"
              "on a FlatCAM object.")
        )
        self.layout.addWidget(self.transform_label)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        # ## Rotate Angle
        self.rotate_entry = FCEntry()
        self.rotate_label = QtWidgets.QLabel('%s:' % _("Rotate Angle"))
        self.rotate_label.setToolTip(
            _("Angle for Rotation action, in degrees.\n"
              "Float number between -360 and 359.\n"
              "Positive numbers for CW motion.\n"
              "Negative numbers for CCW motion.")
        )
        grid0.addWidget(self.rotate_label, 0, 0)
        grid0.addWidget(self.rotate_entry, 0, 1)

        # ## Skew/Shear Angle on X axis
        self.skewx_entry = FCEntry()
        self.skewx_label = QtWidgets.QLabel('%s:' % _("Skew_X angle"))
        self.skewx_label.setToolTip(
            _("Angle for Skew action, in degrees.\n"
              "Float number between -360 and 359.")
        )
        grid0.addWidget(self.skewx_label, 1, 0)
        grid0.addWidget(self.skewx_entry, 1, 1)

        # ## Skew/Shear Angle on Y axis
        self.skewy_entry = FCEntry()
        self.skewy_label = QtWidgets.QLabel('%s:' % _("Skew_Y angle"))
        self.skewy_label.setToolTip(
            _("Angle for Skew action, in degrees.\n"
              "Float number between -360 and 359.")
        )
        grid0.addWidget(self.skewy_label, 2, 0)
        grid0.addWidget(self.skewy_entry, 2, 1)

        # ## Scale factor on X axis
        self.scalex_entry = FCEntry()
        self.scalex_label = QtWidgets.QLabel('%s:' % _("Scale_X factor"))
        self.scalex_label.setToolTip(
            _("Factor for scaling on X axis.")
        )
        grid0.addWidget(self.scalex_label, 3, 0)
        grid0.addWidget(self.scalex_entry, 3, 1)

        # ## Scale factor on X axis
        self.scaley_entry = FCEntry()
        self.scaley_label = QtWidgets.QLabel('%s:' % _("Scale_Y factor"))
        self.scaley_label.setToolTip(
            _("Factor for scaling on Y axis.")
        )
        grid0.addWidget(self.scaley_label, 4, 0)
        grid0.addWidget(self.scaley_entry, 4, 1)

        # ## Link Scale factors
        self.link_cb = FCCheckBox(_("Link"))
        self.link_cb.setToolTip(
            _("Scale the selected object(s)\n"
              "using the Scale_X factor for both axis.")
        )
        grid0.addWidget(self.link_cb, 5, 0)

        # ## Scale Reference
        self.reference_cb = FCCheckBox('%s' % _("Scale Reference"))
        self.reference_cb.setToolTip(
            _("Scale the selected object(s)\n"
              "using the origin reference when checked,\n"
              "and the center of the biggest bounding box\n"
              "of the selected objects when unchecked.")
        )
        grid0.addWidget(self.reference_cb, 5, 1)

        # ## Offset distance on X axis
        self.offx_entry = FCEntry()
        self.offx_label = QtWidgets.QLabel('%s:' % _("Offset_X val"))
        self.offx_label.setToolTip(
           _("Distance to offset on X axis. In current units.")
        )
        grid0.addWidget(self.offx_label, 6, 0)
        grid0.addWidget(self.offx_entry, 6, 1)

        # ## Offset distance on Y axis
        self.offy_entry = FCEntry()
        self.offy_label = QtWidgets.QLabel('%s:' % _("Offset_Y val"))
        self.offy_label.setToolTip(
            _("Distance to offset on Y axis. In current units.")
        )
        grid0.addWidget(self.offy_label, 7, 0)
        grid0.addWidget(self.offy_entry, 7, 1)

        # ## Mirror (Flip) Reference Point
        self.mirror_reference_cb = FCCheckBox('%s' % _("Mirror Reference"))
        self.mirror_reference_cb.setToolTip(
            _("Flip the selected object(s)\n"
              "around the point in Point Entry Field.\n"
              "\n"
              "The point coordinates can be captured by\n"
              "left click on canvas together with pressing\n"
              "SHIFT key. \n"
              "Then click Add button to insert coordinates.\n"
              "Or enter the coords in format (x, y) in the\n"
              "Point Entry field and click Flip on X(Y)"))
        grid0.addWidget(self.mirror_reference_cb, 8, 1)

        self.flip_ref_label = QtWidgets.QLabel('%s:' % _(" Mirror Ref. Point"))
        self.flip_ref_label.setToolTip(
            _("Coordinates in format (x, y) used as reference for mirroring.\n"
              "The 'x' in (x, y) will be used when using Flip on X and\n"
              "the 'y' in (x, y) will be used when using Flip on Y and")
        )
        self.flip_ref_entry = EvalEntry2("(0, 0)")

        grid0.addWidget(self.flip_ref_label, 9, 0)
        grid0.addWidget(self.flip_ref_entry, 9, 1)

        self.layout.addStretch()


class ToolsSolderpastePrefGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):

        super(ToolsSolderpastePrefGroupUI, self).__init__(self)

        self.setTitle(str(_("SolderPaste Tool Options")))

        # ## Solder Paste Dispensing
        self.solderpastelabel = QtWidgets.QLabel("<b>%s:</b>" % _("Parameters"))
        self.solderpastelabel.setToolTip(
            _("A tool to create GCode for dispensing\n"
              "solder paste onto a PCB.")
        )
        self.layout.addWidget(self.solderpastelabel)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        # Nozzle Tool Diameters
        nozzletdlabel = QtWidgets.QLabel('%s:' % _('Tools dia'))
        nozzletdlabel.setToolTip(
            _("Diameters of nozzle tools, separated by ','")
        )
        self.nozzle_tool_dia_entry = FCEntry()
        grid0.addWidget(nozzletdlabel, 0, 0)
        grid0.addWidget(self.nozzle_tool_dia_entry, 0, 1)

        # New Nozzle Tool Dia
        self.addtool_entry_lbl = QtWidgets.QLabel('<b>%s:</b>' % _('New Nozzle Dia'))
        self.addtool_entry_lbl.setToolTip(
            _("Diameter for the new Nozzle tool to add in the Tool Table")
        )
        self.addtool_entry = FCEntry()
        grid0.addWidget(self.addtool_entry_lbl, 1, 0)
        grid0.addWidget(self.addtool_entry, 1, 1)

        # Z dispense start
        self.z_start_entry = FCEntry()
        self.z_start_label = QtWidgets.QLabel('%s:' % _("Z Dispense Start"))
        self.z_start_label.setToolTip(
            _("The height (Z) when solder paste dispensing starts.")
        )
        grid0.addWidget(self.z_start_label, 2, 0)
        grid0.addWidget(self.z_start_entry, 2, 1)

        # Z dispense
        self.z_dispense_entry = FCEntry()
        self.z_dispense_label = QtWidgets.QLabel('%s:' % _("Z Dispense"))
        self.z_dispense_label.setToolTip(
            _("The height (Z) when doing solder paste dispensing.")
        )
        grid0.addWidget(self.z_dispense_label, 3, 0)
        grid0.addWidget(self.z_dispense_entry, 3, 1)

        # Z dispense stop
        self.z_stop_entry = FCEntry()
        self.z_stop_label = QtWidgets.QLabel('%s:' % _("Z Dispense Stop"))
        self.z_stop_label.setToolTip(
            _("The height (Z) when solder paste dispensing stops.")
        )
        grid0.addWidget(self.z_stop_label, 4, 0)
        grid0.addWidget(self.z_stop_entry, 4, 1)

        # Z travel
        self.z_travel_entry = FCEntry()
        self.z_travel_label = QtWidgets.QLabel('%s:' % _("Z Travel"))
        self.z_travel_label.setToolTip(
            _("The height (Z) for travel between pads\n"
              "(without dispensing solder paste).")
        )
        grid0.addWidget(self.z_travel_label, 5, 0)
        grid0.addWidget(self.z_travel_entry, 5, 1)

        # Z toolchange location
        self.z_toolchange_entry = FCEntry()
        self.z_toolchange_label = QtWidgets.QLabel('%s:' % _("Z Toolchange"))
        self.z_toolchange_label.setToolTip(
            _("The height (Z) for tool (nozzle) change.")
        )
        grid0.addWidget(self.z_toolchange_label, 6, 0)
        grid0.addWidget(self.z_toolchange_entry, 6, 1)

        # X,Y Toolchange location
        self.xy_toolchange_entry = FCEntry()
        self.xy_toolchange_label = QtWidgets.QLabel('%s:' % _("Toolchange X-Y"))
        self.xy_toolchange_label.setToolTip(
            _("The X,Y location for tool (nozzle) change.\n"
              "The format is (x, y) where x and y are real numbers.")
        )
        grid0.addWidget(self.xy_toolchange_label, 7, 0)
        grid0.addWidget(self.xy_toolchange_entry, 7, 1)

        # Feedrate X-Y
        self.frxy_entry = FCEntry()
        self.frxy_label = QtWidgets.QLabel('%s:' % _("Feedrate X-Y"))
        self.frxy_label.setToolTip(
            _("Feedrate (speed) while moving on the X-Y plane.")
        )
        grid0.addWidget(self.frxy_label, 8, 0)
        grid0.addWidget(self.frxy_entry, 8, 1)

        # Feedrate Z
        self.frz_entry = FCEntry()
        self.frz_label = QtWidgets.QLabel('%s:' % _("Feedrate Z"))
        self.frz_label.setToolTip(
            _("Feedrate (speed) while moving vertically\n"
              "(on Z plane).")
        )
        grid0.addWidget(self.frz_label, 9, 0)
        grid0.addWidget(self.frz_entry, 9, 1)

        # Feedrate Z Dispense
        self.frz_dispense_entry = FCEntry()
        self.frz_dispense_label = QtWidgets.QLabel('%s:' % _("Feedrate Z Dispense"))
        self.frz_dispense_label.setToolTip(
            _("Feedrate (speed) while moving up vertically\n"
              "to Dispense position (on Z plane).")
        )
        grid0.addWidget(self.frz_dispense_label, 10, 0)
        grid0.addWidget(self.frz_dispense_entry, 10, 1)

        # Spindle Speed Forward
        self.speedfwd_entry = FCEntry()
        self.speedfwd_label = QtWidgets.QLabel('%s:' % _("Spindle Speed FWD"))
        self.speedfwd_label.setToolTip(
            _("The dispenser speed while pushing solder paste\n"
              "through the dispenser nozzle.")
        )
        grid0.addWidget(self.speedfwd_label, 11, 0)
        grid0.addWidget(self.speedfwd_entry, 11, 1)

        # Dwell Forward
        self.dwellfwd_entry = FCEntry()
        self.dwellfwd_label = QtWidgets.QLabel('%s:' % _("Dwell FWD"))
        self.dwellfwd_label.setToolTip(
            _("Pause after solder dispensing.")
        )
        grid0.addWidget(self.dwellfwd_label, 12, 0)
        grid0.addWidget(self.dwellfwd_entry, 12, 1)

        # Spindle Speed Reverse
        self.speedrev_entry = FCEntry()
        self.speedrev_label = QtWidgets.QLabel('%s:' % _("Spindle Speed REV"))
        self.speedrev_label.setToolTip(
            _("The dispenser speed while retracting solder paste\n"
              "through the dispenser nozzle.")
        )
        grid0.addWidget(self.speedrev_label, 13, 0)
        grid0.addWidget(self.speedrev_entry, 13, 1)

        # Dwell Reverse
        self.dwellrev_entry = FCEntry()
        self.dwellrev_label = QtWidgets.QLabel('%s:' % _("Dwell REV"))
        self.dwellrev_label.setToolTip(
            _("Pause after solder paste dispenser retracted,\n"
              "to allow pressure equilibrium.")
        )
        grid0.addWidget(self.dwellrev_label, 14, 0)
        grid0.addWidget(self.dwellrev_entry, 14, 1)

        # Postprocessors
        pp_label = QtWidgets.QLabel('%s:' % _('PostProcessor'))
        pp_label.setToolTip(
            _("Files that control the GCode generation.")
        )

        self.pp_combo = FCComboBox()
        grid0.addWidget(pp_label, 15, 0)
        grid0.addWidget(self.pp_combo, 15, 1)

        self.layout.addStretch()


class ToolsSubPrefGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):

        super(ToolsSubPrefGroupUI, self).__init__(self)

        self.setTitle(str(_("Substractor Tool Options")))

        # ## Solder Paste Dispensing
        self.sublabel = QtWidgets.QLabel("<b>%s:</b>" % _("Parameters"))
        self.sublabel.setToolTip(
            _("A tool to substract one Gerber or Geometry object\n"
              "from another of the same type.")
        )
        self.layout.addWidget(self.sublabel)

        self.close_paths_cb = FCCheckBox(_("Close paths"))
        self.close_paths_cb.setToolTip(_("Checking this will close the paths cut by the Geometry substractor object."))
        self.layout.addWidget(self.close_paths_cb)

        self.layout.addStretch()


class FAExcPrefGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        # OptionsGroupUI.__init__(self, "Excellon File associations Preferences", parent=None)
        super().__init__(self)

        self.setTitle(str(_("Excellon File associations")))

        self.layout.setContentsMargins(2, 2, 2, 2)

        self.vertical_lay = QtWidgets.QVBoxLayout()
        scroll_widget = QtWidgets.QWidget()

        scroll = VerticalScrollArea()
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)

        self.restore_btn = FCButton(_("Restore"))
        self.restore_btn.setToolTip(_("Restore the extension list to the default state."))
        self.del_all_btn = FCButton(_("Delete All"))
        self.del_all_btn.setToolTip(_("Delete all extensions from the list."))

        hlay0 = QtWidgets.QHBoxLayout()
        hlay0.addWidget(self.restore_btn)
        hlay0.addWidget(self.del_all_btn)
        self.vertical_lay.addLayout(hlay0)

        # # ## Excellon associations
        list_label = QtWidgets.QLabel("<b>%s:</b>" % _("Extensions list"))
        list_label.setToolTip(
            _("List of file extensions to be\n"
              "associated with FlatCAM.")
        )
        self.vertical_lay.addWidget(list_label)

        settings = QSettings("Open Source", "FlatCAM")
        if settings.contains("textbox_font_size"):
            tb_fsize = settings.value('textbox_font_size', type=int)
        else:
            tb_fsize = 10

        self.exc_list_text = FCTextArea()
        self.exc_list_text.setReadOnly(True)
        # self.exc_list_text.sizeHint(custom_sizehint=150)
        font = QtGui.QFont()
        font.setPointSize(tb_fsize)
        self.exc_list_text.setFont(font)

        self.vertical_lay.addWidget(self.exc_list_text)

        self.ext_label = QtWidgets.QLabel('%s:' % _("Extension"))
        self.ext_label.setToolTip(_("A file extension to be added or deleted to the list."))
        self.ext_entry = FCEntry()

        hlay1 = QtWidgets.QHBoxLayout()
        self.vertical_lay.addLayout(hlay1)
        hlay1.addWidget(self.ext_label)
        hlay1.addWidget(self.ext_entry)

        self.add_btn = FCButton(_("Add Extension"))
        self.add_btn.setToolTip(_("Add a file extension to the list"))
        self.del_btn = FCButton(_("Delete Extension"))
        self.del_btn.setToolTip(_("Delete a file extension from the list"))

        hlay2 = QtWidgets.QHBoxLayout()
        self.vertical_lay.addLayout(hlay2)
        hlay2.addWidget(self.add_btn)
        hlay2.addWidget(self.del_btn)

        self.exc_list_btn = FCButton(_("Apply Association"))
        self.exc_list_btn.setToolTip(_("Apply the file associations between\n"
                                       "FlatCAM and the files with above extensions.\n"
                                       "They will be active after next logon.\n"
                                       "This work only in Windows."))
        self.vertical_lay.addWidget(self.exc_list_btn)

        scroll_widget.setLayout(self.vertical_lay)
        self.layout.addWidget(scroll)

        # self.vertical_lay.addStretch()


class FAGcoPrefGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        # OptionsGroupUI.__init__(self, "Gcode File associations Preferences", parent=None)
        super(FAGcoPrefGroupUI, self).__init__(self)

        self.setTitle(str(_("GCode File associations")))

        self.restore_btn = FCButton(_("Restore"))
        self.restore_btn.setToolTip(_("Restore the extension list to the default state."))
        self.del_all_btn = FCButton(_("Delete All"))
        self.del_all_btn.setToolTip(_("Delete all extensions from the list."))

        hlay0 = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay0)
        hlay0.addWidget(self.restore_btn)
        hlay0.addWidget(self.del_all_btn)

        # ## G-Code associations
        self.gco_list_label = QtWidgets.QLabel("<b>%s:</b>" % _("Extensions list"))
        self.gco_list_label.setToolTip(
            _("List of file extensions to be\n"
              "associated with FlatCAM.")
        )
        self.layout.addWidget(self.gco_list_label)

        settings = QSettings("Open Source", "FlatCAM")
        if settings.contains("textbox_font_size"):
            tb_fsize = settings.value('textbox_font_size', type=int)
        else:
            tb_fsize = 10

        self.gco_list_text = FCTextArea()
        self.gco_list_text.setReadOnly(True)
        # self.gco_list_text.sizeHint(custom_sizehint=150)
        font = QtGui.QFont()
        font.setPointSize(tb_fsize)
        self.gco_list_text.setFont(font)

        self.layout.addWidget(self.gco_list_text)

        self.ext_label = QtWidgets.QLabel('%s:' % _("Extension"))
        self.ext_label.setToolTip(_("A file extension to be added or deleted to the list."))
        self.ext_entry = FCEntry()

        hlay1 = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay1)
        hlay1.addWidget(self.ext_label)
        hlay1.addWidget(self.ext_entry)

        self.add_btn = FCButton(_("Add Extension"))
        self.add_btn.setToolTip(_("Add a file extension to the list"))
        self.del_btn = FCButton(_("Delete Extension"))
        self.del_btn.setToolTip(_("Delete a file extension from the list"))

        hlay2 = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay2)
        hlay2.addWidget(self.add_btn)
        hlay2.addWidget(self.del_btn)

        self.gco_list_btn = FCButton(_("Apply Association"))
        self.gco_list_btn.setToolTip(_("Apply the file associations between\n"
                                       "FlatCAM and the files with above extensions.\n"
                                       "They will be active after next logon.\n"
                                       "This work only in Windows."))
        self.layout.addWidget(self.gco_list_btn)

        # self.layout.addStretch()


class FAGrbPrefGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        # OptionsGroupUI.__init__(self, "Gerber File associations Preferences", parent=None)
        super(FAGrbPrefGroupUI, self).__init__(self)

        self.setTitle(str(_("Gerber File associations")))

        self.restore_btn = FCButton(_("Restore"))
        self.restore_btn.setToolTip(_("Restore the extension list to the default state."))
        self.del_all_btn = FCButton(_("Delete All"))
        self.del_all_btn.setToolTip(_("Delete all extensions from the list."))

        hlay0 = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay0)
        hlay0.addWidget(self.restore_btn)
        hlay0.addWidget(self.del_all_btn)

        # ## Gerber associations
        self.grb_list_label = QtWidgets.QLabel("<b>%s:</b>" % _("Extensions list"))
        self.grb_list_label.setToolTip(
            _("List of file extensions to be\n"
              "associated with FlatCAM.")
        )
        self.layout.addWidget(self.grb_list_label)

        settings = QSettings("Open Source", "FlatCAM")
        if settings.contains("textbox_font_size"):
            tb_fsize = settings.value('textbox_font_size', type=int)
        else:
            tb_fsize = 10

        self.grb_list_text = FCTextArea()
        self.grb_list_text.setReadOnly(True)
        # self.grb_list_text.sizeHint(custom_sizehint=150)
        self.layout.addWidget(self.grb_list_text)
        font = QtGui.QFont()
        font.setPointSize(tb_fsize)
        self.grb_list_text.setFont(font)

        self.ext_label = QtWidgets.QLabel('%s:' % _("Extension"))
        self.ext_label.setToolTip(_("A file extension to be added or deleted to the list."))
        self.ext_entry = FCEntry()

        hlay1 = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay1)
        hlay1.addWidget(self.ext_label)
        hlay1.addWidget(self.ext_entry)

        self.add_btn = FCButton(_("Add Extension"))
        self.add_btn.setToolTip(_("Add a file extension to the list"))
        self.del_btn = FCButton(_("Delete Extension"))
        self.del_btn.setToolTip(_("Delete a file extension from the list"))

        hlay2 = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay2)
        hlay2.addWidget(self.add_btn)
        hlay2.addWidget(self.del_btn)

        self.grb_list_btn = FCButton(_("Apply Association"))
        self.grb_list_btn.setToolTip(_("Apply the file associations between\n"
                                       "FlatCAM and the files with above extensions.\n"
                                       "They will be active after next logon.\n"
                                       "This work only in Windows."))

        self.layout.addWidget(self.grb_list_btn)

        # self.layout.addStretch()


class AutoCompletePrefGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        # OptionsGroupUI.__init__(self, "Gerber File associations Preferences", parent=None)
        super().__init__(self, parent=parent)

        self.setTitle(str(_("Autocompleter Keywords")))

        self.restore_btn = FCButton(_("Restore"))
        self.restore_btn.setToolTip(_("Restore the autocompleter keywords list to the default state."))
        self.del_all_btn = FCButton(_("Delete All"))
        self.del_all_btn.setToolTip(_("Delete all autocompleter keywords from the list."))

        hlay0 = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay0)
        hlay0.addWidget(self.restore_btn)
        hlay0.addWidget(self.del_all_btn)

        # ## Gerber associations
        self.grb_list_label = QtWidgets.QLabel("<b>%s:</b>" % _("Keywords list"))
        self.grb_list_label.setToolTip(
            _("List of keywords used by\n"
              "the autocompleter in FlatCAM.\n"
              "The autocompleter is installed\n"
              "in the Code Editor and for the Tcl Shell.")
        )
        self.layout.addWidget(self.grb_list_label)

        settings = QSettings("Open Source", "FlatCAM")
        if settings.contains("textbox_font_size"):
            tb_fsize = settings.value('textbox_font_size', type=int)
        else:
            tb_fsize = 10

        self.kw_list_text = FCTextArea()
        self.kw_list_text.setReadOnly(True)
        # self.grb_list_text.sizeHint(custom_sizehint=150)
        self.layout.addWidget(self.kw_list_text)
        font = QtGui.QFont()
        font.setPointSize(tb_fsize)
        self.kw_list_text.setFont(font)

        self.kw_label = QtWidgets.QLabel('%s:' % _("Extension"))
        self.kw_label.setToolTip(_("A keyword to be added or deleted to the list."))
        self.kw_entry = FCEntry()

        hlay1 = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay1)
        hlay1.addWidget(self.kw_label)
        hlay1.addWidget(self.kw_entry)

        self.add_btn = FCButton(_("Add keyword"))
        self.add_btn.setToolTip(_("Add a keyword to the list"))
        self.del_btn = FCButton(_("Delete keyword"))
        self.del_btn.setToolTip(_("Delete a keyword from the list"))

        hlay2 = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay2)
        hlay2.addWidget(self.add_btn)
        hlay2.addWidget(self.del_btn)

        # self.layout.addStretch()
