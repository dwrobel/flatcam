from PyQt6 import QtCore, QtGui
from PyQt6.QtCore import QSettings

from appGUI.GUIElements import FCDoubleSpinner, FCCheckBox, FCComboBox, RadioSet, OptionalInputSection, FCSpinner, \
    FCColorEntry, FCLabel, GLay, FCFrame
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GeneralAPPSetGroupUI(OptionsGroupUI):
    def __init__(self, app, parent=None):
        super(GeneralAPPSetGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("App Settings")))
        self.decimals = app.decimals
        self.options = app.options

        theme_settings = QtCore.QSettings("Open Source", "FlatCAM")
        if theme_settings.contains("theme"):
            theme = theme_settings.value('theme', type=str)
        else:
            theme = 'light'

        if theme == 'light':
            self.resource_loc = 'assets/resources'
        else:
            self.resource_loc = 'assets/resources'

        # #############################################################################################################
        # Grid Settings Frame
        # #############################################################################################################
        # GRID Settings
        self.grid_label = FCLabel('%s' % _("Grid Settings"), color='magenta', bold=True)
        self.layout.addWidget(self.grid_label)

        grids_frame = FCFrame()
        self.layout.addWidget(grids_frame)

        # Create a grid layout for the Application general settings
        grids_grid = GLay(v_spacing=5, h_spacing=3)
        grids_frame.setLayout(grids_grid)

        # Grid X Entry
        self.gridx_label = FCLabel('%s:' % _('X value'))
        self.gridx_label.setToolTip(
           _("This is the Grid snap value on X axis.")
        )
        self.gridx_entry = FCDoubleSpinner()
        self.gridx_entry.set_precision(self.decimals)
        self.gridx_entry.setSingleStep(0.1)

        grids_grid.addWidget(self.gridx_label, 2, 0)
        grids_grid.addWidget(self.gridx_entry, 2, 1)

        # Grid Y Entry
        self.gridy_label = FCLabel('%s:' % _('Y value'))
        self.gridy_label.setToolTip(
            _("This is the Grid snap value on Y axis.")
        )
        self.gridy_entry = FCDoubleSpinner()
        self.gridy_entry.set_precision(self.decimals)
        self.gridy_entry.setSingleStep(0.1)

        grids_grid.addWidget(self.gridy_label, 4, 0)
        grids_grid.addWidget(self.gridy_entry, 4, 1)

        # Snap Max Entry
        self.snap_max_label = FCLabel('%s:' % _('Snap Max'))
        self.snap_max_label.setToolTip(_("Max. magnet distance"))
        self.snap_max_dist_entry = FCDoubleSpinner()
        self.snap_max_dist_entry.set_precision(self.decimals)
        self.snap_max_dist_entry.setSingleStep(0.1)

        grids_grid.addWidget(self.snap_max_label, 6, 0)
        grids_grid.addWidget(self.snap_max_dist_entry, 6, 1)

        # separator_line = QtWidgets.QFrame()
        # separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        # separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        # grids_grid.addWidget(separator_line, 8, 0, 1, 2)

        # #############################################################################################################
        # Workspace Frame
        # #############################################################################################################
        # Workspace
        self.workspace_label = FCLabel('%s' % _("Workspace Settings"), color='brown', bold=True)
        self.layout.addWidget(self.workspace_label)

        wk_frame = FCFrame()
        self.layout.addWidget(wk_frame)

        wk_grid = GLay(v_spacing=5, h_spacing=3)
        wk_frame.setLayout(wk_grid)

        self.workspace_cb = FCCheckBox('%s' % _('Active'))
        self.workspace_cb.setToolTip(
           _("Draw a delimiting rectangle on canvas.\n"
             "The purpose is to illustrate the limits for our work.")
        )

        wk_grid.addWidget(self.workspace_cb, 0, 0, 1, 2)

        self.workspace_type_lbl = FCLabel('%s:' % _('Size'))
        self.workspace_type_lbl.setToolTip(
           _("Select the type of rectangle to be used on canvas,\n"
             "as valid workspace.")
        )
        self.wk_cb = FCComboBox()

        wk_grid.addWidget(self.workspace_type_lbl, 2, 0)
        wk_grid.addWidget(self.wk_cb, 2, 1)

        self.pagesize = {}
        self.pagesize.update(
            {
                'A0': (841, 1189),
                'A1': (594, 841),
                'A2': (420, 594),
                'A3': (297, 420),
                'A4': (210, 297),
                'A5': (148, 210),
                'A6': (105, 148),
                'A7': (74, 105),
                'A8': (52, 74),
                'A9': (37, 52),
                'A10': (26, 37),

                'B0': (1000, 1414),
                'B1': (707, 1000),
                'B2': (500, 707),
                'B3': (353, 500),
                'B4': (250, 353),
                'B5': (176, 250),
                'B6': (125, 176),
                'B7': (88, 125),
                'B8': (62, 88),
                'B9': (44, 62),
                'B10': (31, 44),

                'C0': (917, 1297),
                'C1': (648, 917),
                'C2': (458, 648),
                'C3': (324, 458),
                'C4': (229, 324),
                'C5': (162, 229),
                'C6': (114, 162),
                'C7': (81, 114),
                'C8': (57, 81),
                'C9': (40, 57),
                'C10': (28, 40),

                # American paper sizes
                'LETTER': (8.5, 11),
                'LEGAL': (8.5, 14),
                'ELEVENSEVENTEEN': (11, 17),

                # From https://en.wikipedia.org/wiki/Paper_size
                'JUNIOR_LEGAL': (5, 8),
                'HALF_LETTER': (5.5, 8),
                'GOV_LETTER': (8, 10.5),
                'GOV_LEGAL': (8.5, 13),
                'LEDGER': (17, 11),
            }
        )

        page_size_list = list(self.pagesize.keys())

        self.wk_cb.addItems(page_size_list)

        # Page orientation
        self.wk_orientation_label = FCLabel('%s:' % _("Orientation"))
        self.wk_orientation_label.setToolTip(_("Can be:\n"
                                               "- Portrait\n"
                                               "- Landscape"))

        self.wk_orientation_radio = RadioSet([{'label': _('Portrait'), 'value': 'p'},
                                              {'label': _('Landscape'), 'value': 'l'},
                                              ], compact=True)

        wk_grid.addWidget(self.wk_orientation_label, 4, 0)
        wk_grid.addWidget(self.wk_orientation_radio, 4, 1)

        # #############################################################################################################
        # Font Frame
        # #############################################################################################################
        # Font Size
        self.font_size_label = FCLabel('%s' % _("Font Size"), color='green', bold=True)
        self.layout.addWidget(self.font_size_label)

        fnt_frame = FCFrame()
        self.layout.addWidget(fnt_frame)

        fnt_grid = GLay(v_spacing=5, h_spacing=3)
        fnt_frame.setLayout(fnt_grid)

        # Notebook Font Size
        self.notebook_font_size_label = FCLabel('%s:' % _('Notebook'))
        self.notebook_font_size_label.setToolTip(
            _("This sets the font size for the elements found in the Notebook.\n"
              "The notebook is the collapsible area in the left side of the GUI,\n"
              "and include the Project, Selected and Tool tabs.")
        )

        self.notebook_font_size_spinner = FCSpinner()
        self.notebook_font_size_spinner.set_range(8, 40)
        self.notebook_font_size_spinner.setWrapping(True)

        qsettings = QSettings("Open Source", "FlatCAM")
        if qsettings.contains("notebook_font_size"):
            self.notebook_font_size_spinner.set_value(qsettings.value('notebook_font_size', type=int))
        else:
            self.notebook_font_size_spinner.set_value(12)

        fnt_grid.addWidget(self.notebook_font_size_label, 0, 0)
        fnt_grid.addWidget(self.notebook_font_size_spinner, 0, 1)

        # Axis Font Size
        self.axis_font_size_label = FCLabel('%s:' % _('Axis'))
        self.axis_font_size_label.setToolTip(
            _("This sets the font size for canvas axis.")
        )

        self.axis_font_size_spinner = FCSpinner()
        self.axis_font_size_spinner.set_range(0, 40)
        self.axis_font_size_spinner.setWrapping(True)

        qsettings = QSettings("Open Source", "FlatCAM")
        if qsettings.contains("axis_font_size"):
            self.axis_font_size_spinner.set_value(qsettings.value('axis_font_size', type=int))
        else:
            self.axis_font_size_spinner.set_value(8)

        fnt_grid.addWidget(self.axis_font_size_label, 2, 0)
        fnt_grid.addWidget(self.axis_font_size_spinner, 2, 1)

        # TextBox Font Size
        self.textbox_font_size_label = FCLabel('%s:' % _('Textbox'))
        self.textbox_font_size_label.setToolTip(
            _("This sets the font size for the Textbox GUI\n"
              "elements that are used in the application.")
        )

        self.textbox_font_size_spinner = FCSpinner()
        self.textbox_font_size_spinner.set_range(8, 40)
        self.textbox_font_size_spinner.setWrapping(True)

        qsettings = QSettings("Open Source", "FlatCAM")
        if qsettings.contains("textbox_font_size"):
            self.textbox_font_size_spinner.set_value(qsettings.value('textbox_font_size', type=int))
        else:
            self.textbox_font_size_spinner.set_value(10)

        fnt_grid.addWidget(self.textbox_font_size_label, 4, 0)
        fnt_grid.addWidget(self.textbox_font_size_spinner, 4, 1)

        # HUD Font Size
        self.hud_font_size_label = FCLabel('%s:' % _('HUD'))
        self.hud_font_size_label.setToolTip(
            _("This sets the font size for the Heads Up Display.")
        )

        self.hud_font_size_spinner = FCSpinner()
        self.hud_font_size_spinner.set_range(8, 40)
        self.hud_font_size_spinner.setWrapping(True)

        qsettings = QSettings("Open Source", "FlatCAM")
        if qsettings.contains("hud_font_size"):
            self.hud_font_size_spinner.set_value(qsettings.value('hud_font_size', type=int))
        else:
            self.hud_font_size_spinner.set_value(8)

        fnt_grid.addWidget(self.hud_font_size_label, 6, 0)
        fnt_grid.addWidget(self.hud_font_size_spinner, 6, 1)

        # #############################################################################################################
        # Axis Frame
        # #############################################################################################################
        # Axis Size
        self.axis_label = FCLabel('%s' % _("Axis"), color='brown', bold=True)
        self.layout.addWidget(self.axis_label)

        ax_frame = FCFrame()
        self.layout.addWidget(ax_frame)

        ax_grid = GLay(v_spacing=5, h_spacing=3)
        ax_frame.setLayout(ax_grid)

        # Axis Color
        self.axis_color_label = FCLabel('%s:' % _('Axis Color'))
        self.axis_color_label.setToolTip(
            _("Set the color of the screen axis.")
        )
        self.axis_color_entry = FCColorEntry(icon=QtGui.QIcon(self.app.resource_location + '/set_colors64.png'))

        ax_grid.addWidget(self.axis_color_label, 0, 0)
        ax_grid.addWidget(self.axis_color_entry, 0, 1)

        # #############################################################################################################
        # Mouse Frame
        # #############################################################################################################
        self.mouse_lbl = FCLabel('%s' % _("Mouse Settings"), color='darkorange', bold=True)
        self.layout.addWidget(self.mouse_lbl)

        m_frame = FCFrame()
        self.layout.addWidget(m_frame)

        m_grid = GLay(v_spacing=5, h_spacing=3)
        m_frame.setLayout(m_grid)

        # Mouse Cursor Shape
        self.cursor_lbl = FCLabel('%s:' % _('Cursor Shape'))
        self.cursor_lbl.setToolTip(
           _("Choose a mouse cursor shape.\n"
             "- Small -> with a customizable size.\n"
             "- Big -> Infinite lines")
        )

        self.cursor_radio = RadioSet([
            {"label": _("Small"), "value": "small"},
            {"label": _("Big"), "value": "big"}
        ], orientation='horizontal', compact=True)

        m_grid.addWidget(self.cursor_lbl, 0, 0)
        m_grid.addWidget(self.cursor_radio, 0, 1)

        # Mouse Cursor Size
        self.cursor_size_lbl = FCLabel('%s:' % _('Cursor Size'))
        self.cursor_size_lbl.setToolTip(
           _("Set the size of the mouse cursor, in pixels.")
        )

        self.cursor_size_entry = FCSpinner()
        self.cursor_size_entry.set_range(10, 70)
        self.cursor_size_entry.setWrapping(True)

        m_grid.addWidget(self.cursor_size_lbl, 2, 0)
        m_grid.addWidget(self.cursor_size_entry, 2, 1)

        # Cursor Width
        self.cursor_width_lbl = FCLabel('%s:' % _('Cursor Width'))
        self.cursor_width_lbl.setToolTip(
           _("Set the line width of the mouse cursor, in pixels.")
        )

        self.cursor_width_entry = FCSpinner()
        self.cursor_width_entry.set_range(1, 10)
        self.cursor_width_entry.setWrapping(True)

        m_grid.addWidget(self.cursor_width_lbl, 4, 0)
        m_grid.addWidget(self.cursor_width_entry, 4, 1)

        # Cursor Color Enable
        self.mouse_cursor_color_cb = FCCheckBox(label='%s' % _('Cursor Color'))
        self.mouse_cursor_color_cb.setToolTip(
            _("Check this box to color mouse cursor.")
        )
        m_grid.addWidget(self.mouse_cursor_color_cb, 6, 0, 1, 2)

        # Cursor Color
        self.mouse_color_label = FCLabel('%s:' % _('Cursor Color'))
        self.mouse_color_label.setToolTip(
            _("Set the color of the mouse cursor.")
        )
        self.mouse_cursor_entry = FCColorEntry(icon=QtGui.QIcon(self.app.resource_location + '/set_colors64.png'))

        m_grid.addWidget(self.mouse_color_label, 8, 0)
        m_grid.addWidget(self.mouse_cursor_entry, 8, 1)

        self.mois = OptionalInputSection(
            self.mouse_cursor_color_cb,
            [
                self.mouse_color_label,
                self.mouse_cursor_entry
            ]
        )

        # Select mouse pan button
        self.panbuttonlabel = FCLabel('%s:' % _('Pan Button'))
        self.panbuttonlabel.setToolTip(
            _("Select the mouse button to use for panning:\n"
              "- MMB --> Middle Mouse Button\n"
              "- RMB --> Right Mouse Button")
        )
        self.pan_button_radio = RadioSet([{'label': _('MMB'), 'value': '3'},
                                          {'label': _('RMB'), 'value': '2'}], compact=True)

        m_grid.addWidget(self.panbuttonlabel, 10, 0)
        m_grid.addWidget(self.pan_button_radio, 10, 1)

        # Multiple Selection Modifier Key
        self.mselectlabel = FCLabel('%s:' % _('Multi-Selection'))
        self.mselectlabel.setToolTip(
            _("Select the key used for multiple selection.")
        )
        self.mselect_radio = RadioSet([{'label': _('CTRL'), 'value': 'Control'},
                                       {'label': _('SHIFT'), 'value': 'Shift'}], compact=True)

        m_grid.addWidget(self.mselectlabel, 50, 0)
        m_grid.addWidget(self.mselect_radio, 50, 1)

        # #############################################################################################################
        # Parameters Frame
        # #############################################################################################################
        self.par_label = FCLabel('%s' % _("Parameters"), color='blue', bold=True)
        self.layout.addWidget(self.par_label)

        par_frame = FCFrame()
        self.layout.addWidget(par_frame)

        par_grid = GLay(v_spacing=5, h_spacing=3)
        par_frame.setLayout(par_grid)

        # Delete confirmation
        self.delete_conf_cb = FCCheckBox(_('Delete object confirmation'))
        self.delete_conf_cb.setToolTip(
            _("When checked the application will ask for user confirmation\n"
              "whenever the Delete object(s) event is triggered, either by\n"
              "menu shortcut or key shortcut.")
        )
        par_grid.addWidget(self.delete_conf_cb, 0, 0, 1, 2)

        self.allow_edit_cb = FCCheckBox(_("Allow Edit"))
        self.allow_edit_cb.setToolTip(
            _("When checked, the user can edit the object names in the Project Tab\n"
              "by clicking on the object name. Active after restart.")
        )
        par_grid.addWidget(self.allow_edit_cb, 2, 0, 1, 2)

        # Open behavior
        self.open_style_cb = FCCheckBox('%s' % _('"Open" behavior'))
        self.open_style_cb.setToolTip(
            _("When checked the path for the last saved file is used when saving files,\n"
              "and the path for the last opened file is used when opening files.\n\n"
              "When unchecked the path for opening files is the one used last: either the\n"
              "path for saving files or the path for opening files.")
        )

        par_grid.addWidget(self.open_style_cb, 4, 0, 1, 2)

        # Enable/Disable ToolTips globally
        self.toggle_tooltips_cb = FCCheckBox(label=_('Enable ToolTips'))
        self.toggle_tooltips_cb.setToolTip(
            _("Check this box if you want to have toolTips displayed\n"
              "when hovering with mouse over items throughout the App.")
        )

        par_grid.addWidget(self.toggle_tooltips_cb, 6, 0, 1, 2)

        # Bookmarks Limit in the Help Menu
        self.bm_limit_spinner = FCSpinner()
        self.bm_limit_spinner.set_range(0, 9999)
        self.bm_limit_label = FCLabel('%s:' % _('Bookmarks limit'))
        self.bm_limit_label.setToolTip(
            _("The maximum number of bookmarks that may be installed in the menu.\n"
              "The number of bookmarks in the bookmark manager may be greater\n"
              "but the menu will hold only so much.")
        )

        par_grid.addWidget(self.bm_limit_label, 8, 0)
        par_grid.addWidget(self.bm_limit_spinner, 8, 1)

        # Activity monitor icon
        self.activity_label = FCLabel('%s:' % _("Activity Icon"))
        self.activity_label.setToolTip(
            _("Select the GIF that show activity when FlatCAM is active.")
        )
        self.activity_combo = FCComboBox()
        self.activity_combo.addItems(['Ball black', 'Ball green', 'Arrow green', 'Eclipse green'])

        par_grid.addWidget(self.activity_label, 10, 0)
        par_grid.addWidget(self.activity_combo, 10, 1)

        GLay.set_common_column_size(
            [grids_grid, m_grid, par_grid, wk_grid, fnt_grid, ax_grid], 0
        )

        self.layout.addStretch()

        self.mouse_cursor_color_cb.stateChanged.connect(self.on_mouse_cursor_color_enable)
        self.mouse_cursor_entry.editingFinished.connect(self.on_mouse_cursor_entry)

        self.axis_color_entry.editingFinished.connect(self.on_axis_color_entry)

    def on_mouse_cursor_color_enable(self, val):
        if val:
            self.app.cursor_color_3D = self.app.options["global_cursor_color"]
        else:
            theme_settings = QtCore.QSettings("Open Source", "FlatCAM")
            if theme_settings.contains("theme"):
                theme = theme_settings.value('theme', type=str)
            else:
                theme = 'light'

            if theme_settings.contains("dark_canvas"):
                dark_canvas = theme_settings.value('dark_canvas', type=bool)
            else:
                dark_canvas = True

            if theme == 'light' and not dark_canvas:
                self.app.cursor_color_3D = 'black'
            else:
                self.app.cursor_color_3D = 'gray'

    def on_mouse_cursor_entry(self):
        self.app.options['global_cursor_color'] = self.mouse_cursor_entry.get_value()
        self.app.cursor_color_3D = self.app.options["global_cursor_color"]

    def on_axis_color_entry(self):
        self.app.options['global_axis_color'] = self.axis_color_entry.get_value()
        self.app.plotcanvas.apply_axis_color()
