
from PyQt5 import QtCore
from PyQt5.QtCore import QSettings
from appGUI.GUIElements import OptionalInputSection
from appGUI.preferences import settings
from appGUI.preferences.OptionUI import *
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI2

import gettext
import appTranslation as fcTranslate
import builtins
fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GeneralAppSettingsGroupUI(OptionsGroupUI2):
    def __init__(self, decimals=4, **kwargs):
        self.decimals = decimals
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
        super().__init__(**kwargs)

        self.setTitle(str(_("App Settings")))

        qsettings = QSettings("Open Source", "FlatCAM")

        self.notebook_font_size_field = self.option_dict()["notebook_font_size"].get_field()
        if qsettings.contains("notebook_font_size"):
            self.notebook_font_size_field.set_value(qsettings.value('notebook_font_size', type=int))
        else:
            self.notebook_font_size_field.set_value(12)

        self.axis_font_size_field = self.option_dict()["axis_font_size"].get_field()
        if qsettings.contains("axis_font_size"):
            self.axis_font_size_field.set_value(qsettings.value('axis_font_size', type=int))
        else:
            self.axis_font_size_field.set_value(8)

        self.textbox_font_size_field = self.option_dict()["textbox_font_size"].get_field()
        if qsettings.contains("textbox_font_size"):
            self.textbox_font_size_field.set_value(settings.value('textbox_font_size', type=int))
        else:
            self.textbox_font_size_field.set_value(10)

        self.workspace_enabled_field = self.option_dict()["global_workspace"].get_field()
        self.workspace_type_field = self.option_dict()["global_workspaceT"].get_field()
        self.workspace_type_label = self.option_dict()["global_workspaceT"].label_widget
        self.workspace_orientation_field = self.option_dict()["global_workspace_orientation"].get_field()
        self.workspace_orientation_label = self.option_dict()["global_workspace_orientation"].label_widget
        self.wks = OptionalInputSection(
            self.workspace_enabled_field,
            [
                self.workspace_type_label,
                self.workspace_type_field,
                self.workspace_orientation_label,
                self.workspace_orientation_field
            ]
        )

        self.mouse_cursor_color_enabled_field = self.option_dict()["global_cursor_color_enabled"].get_field()
        self.mouse_cursor_color_field = self.option_dict()["global_cursor_color"].get_field()
        self.mouse_cursor_color_label = self.option_dict()["global_cursor_color"].label_widget
        self.mois = OptionalInputSection(
            self.mouse_cursor_color_enabled_field,
            [
                self.mouse_cursor_color_label,
                self.mouse_cursor_color_field
            ]
        )
        self.mouse_cursor_color_enabled_field.stateChanged.connect(self.on_mouse_cursor_color_enable)
        self.mouse_cursor_color_field.entry.editingFinished.connect(self.on_mouse_cursor_entry)

    def build_options(self) -> [OptionUI]:
        return [
            HeadingOptionUI(label_text="Grid Settings", label_tooltip=None),
            DoubleSpinnerOptionUI(
                option="global_gridx",
                label_text="X value",
                label_tooltip="This is the Grid snap value on X axis.",
                step=0.1,
                decimals=self.decimals
            ),
            DoubleSpinnerOptionUI(
                option="global_gridy",
                label_text='Y value',
                label_tooltip="This is the Grid snap value on Y axis.",
                step=0.1,
                decimals=self.decimals
            ),
            DoubleSpinnerOptionUI(
                option="global_snap_max",
                label_text="Snap Max",
                label_tooltip="Max. magnet distance",
                step=0.1,
                decimals=self.decimals
            ),
            SeparatorOptionUI(),

            HeadingOptionUI(label_text="Workspace Settings", label_tooltip=None),
            CheckboxOptionUI(
                option="global_workspace",
                label_text="Active",
                label_tooltip="Draw a delimiting rectangle on canvas.\n"
                              "The purpose is to illustrate the limits for our work."
            ),
            ComboboxOptionUI(
                option="global_workspaceT",
                label_text="Size",
                label_tooltip="Select the type of rectangle to be used on canvas,\nas valid workspace.",
                choices=list(self.pagesize.keys())
            ),
            RadioSetOptionUI(
                option="global_workspace_orientation",
                label_text="Orientation",
                label_tooltip="Can be:\n- Portrait\n- Landscape",
                choices=[
                    {'label': _('Portrait'), 'value': 'p'},
                    {'label': _('Landscape'), 'value': 'l'},
                ]
            ),
            # FIXME enabling OptionalInputSection ??
            SeparatorOptionUI(),

            HeadingOptionUI(label_text="Font Size", label_tooltip=None),
            SpinnerOptionUI(
                option="notebook_font_size",
                label_text="Notebook",
                label_tooltip="This sets the font size for the elements found in the Notebook.\n"
                              "The notebook is the collapsible area in the left side of the GUI,\n"
                              "and include the Project, Selected and Tool tabs.",
                min_value=8, max_value=40, step=1
            ),
            SpinnerOptionUI(
                option="axis_font_size",
                label_text="Axis",
                label_tooltip="This sets the font size for canvas axis.",
                min_value=8, max_value=40, step=1
            ),
            SpinnerOptionUI(
                option="textbox_font_size",
                label_text="Textbox",
                label_tooltip="This sets the font size for the Textbox GUI\n"
                              "elements that are used in the application.",
                min_value=8, max_value=40, step=1
            ),
            SeparatorOptionUI(),

            HeadingOptionUI(label_text="Mouse Settings", label_tooltip=None),
            RadioSetOptionUI(
                option="global_cursor_type",
                label_text="Cursor Shape",
                label_tooltip="Choose a mouse cursor shape.\n"
                              "- Small -> with a customizable size.\n"
                              "- Big -> Infinite lines",
                choices=[
                    {"label": _("Small"), "value": "small"},
                    {"label": _("Big"), "value": "big"}
                ]
            ),
            SpinnerOptionUI(
                option="global_cursor_size",
                label_text="Cursor Size",
                label_tooltip="Set the size of the mouse cursor, in pixels.",
                min_value=10, max_value=70, step=1
            ),
            SpinnerOptionUI(
                option="global_cursor_width",
                label_text="Cursor Width",
                label_tooltip="Set the line width of the mouse cursor, in pixels.",
                min_value=1, max_value=10, step=1
            ),
            CheckboxOptionUI(
                option="global_cursor_color_enabled",
                label_text="Cursor Color",
                label_tooltip="Check this box to color mouse cursor."
            ),
            ColorOptionUI(
                option="global_cursor_color",
                label_text="Cursor Color",
                label_tooltip="Set the color of the mouse cursor."
            ),
            # FIXME enabling of cursor color
            RadioSetOptionUI(
                option="global_pan_button",
                label_text="Pan Button",
                label_tooltip="Select the mouse button to use for panning:\n"
                              "- MMB --> Middle Mouse Button\n"
                              "- RMB --> Right Mouse Button",
                choices=[{'label': _('MMB'), 'value': '3'},
                         {'label': _('RMB'), 'value': '2'}]
            ),
            RadioSetOptionUI(
                option="global_mselect_key",
                label_text="Multiple Selection",
                label_tooltip="Select the key used for multiple selection.",
                choices=[{'label': _('CTRL'),  'value': 'Control'},
                         {'label': _('SHIFT'), 'value': 'Shift'}]
            ),
            SeparatorOptionUI(),

            CheckboxOptionUI(
                option="global_delete_confirmation",
                label_text="Delete object confirmation",
                label_tooltip="When checked the application will ask for user confirmation\n"
                              "whenever the Delete object(s) event is triggered, either by\n"
                              "menu shortcut or key shortcut."
            ),
            CheckboxOptionUI(
                option="global_open_style",
                label_text='"Open" behavior',
                label_tooltip="When checked the path for the last saved file is used when saving files,\n"
                              "and the path for the last opened file is used when opening files.\n\n"
                              "When unchecked the path for opening files is the one used last: either the\n"
                              "path for saving files or the path for opening files."
            ),
            CheckboxOptionUI(
                option="global_toggle_tooltips",
                label_text="Enable ToolTips",
                label_tooltip="Check this box if you want to have toolTips displayed\n"
                              "when hovering with mouse over items throughout the App."
            ),
            CheckboxOptionUI(
                option="global_machinist_setting",
                label_text="Allow Machinist Unsafe Settings",
                label_tooltip="If checked, some of the application settings will be allowed\n"
                              "to have values that are usually unsafe to use.\n"
                              "Like Z travel negative values or Z Cut positive values.\n"
                              "It will applied at the next application start.\n"
                              "<<WARNING>>: Don't change this unless you know what you are doing !!!"
            ),
            SpinnerOptionUI(
                option="global_bookmarks_limit",
                label_text="Bookmarks limit",
                label_tooltip="The maximum number of bookmarks that may be installed in the menu.\n"
                              "The number of bookmarks in the bookmark manager may be greater\n"
                              "but the menu will hold only so much.",
                min_value=0, max_value=9999, step=1
            ),
            ComboboxOptionUI(
                option="global_activity_icon",
                label_text="Activity Icon",
                label_tooltip="Select the GIF that show activity when FlatCAM is active.",
                choices=['Ball black', 'Ball green', 'Arrow green', 'Eclipse green']
            )

        ]

    def on_mouse_cursor_color_enable(self, val):
        if val:
            self.app.cursor_color_3D = self.app.defaults["global_cursor_color"]
        else:
            theme_settings = QtCore.QSettings("Open Source", "FlatCAM")
            if theme_settings.contains("theme"):
                theme = theme_settings.value('theme', type=str)
            else:
                theme = 'white'

            if theme == 'white':
                self.app.cursor_color_3D = 'black'
            else:
                self.app.cursor_color_3D = 'gray'

    def on_mouse_cursor_entry(self):
        self.app.defaults['global_cursor_color'] = self.mouse_cursor_color_field.get_value()
        self.app.cursor_color_3D = self.app.defaults["global_cursor_color"]
