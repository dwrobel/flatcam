from PyQt5.QtCore import QSettings

from flatcamGUI.GUIElements import OptionalInputSection
from flatcamGUI.preferences import machinist_setting
from flatcamGUI.preferences.OptionUI import *
from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI2

import gettext
import FlatCAMTranslation as fcTranslate
import builtins
fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

settings = QSettings("Open Source", "FlatCAM")
if settings.contains("machinist"):
    machinist_setting = settings.value('machinist', type=int)
else:
    machinist_setting = 0


class GeometryOptPrefGroupUI(OptionsGroupUI2):

    def __init__(self, decimals=4, **kwargs):
        self.decimals = decimals
        super().__init__(**kwargs)
        self.setTitle(str(_("Geometry Options")))
        self.pp_geometry_name_cb = self.option_dict()["geometry_ppname_g"].get_field()

        self.multidepth_cb = self.option_dict()["geometry_multidepth"].get_field()
        self.depthperpass_entry = self.option_dict()["geometry_depthperpass"].get_field()
        self.ois_multidepth = OptionalInputSection(self.multidepth_cb, [self.depthperpass_entry])

        self.dwell_cb = self.option_dict()["geometry_dwell"].get_field()
        self.dwelltime_entry = self.option_dict()["geometry_dwelltime"].get_field()
        self.ois_dwell = OptionalInputSection(self.dwell_cb, [self.dwelltime_entry])

    def build_options(self) -> [OptionUI]:
        return [
            HeadingOptionUI(
                label_text="Create CNC Job",
                label_tooltip="Create a CNC Job object\n"
                              "tracing the contours of this\n"
                              "Geometry object."
            ),
            DoubleSpinnerOptionUI(
                option="geometry_cutz",
                label_text="Cut Z",
                label_tooltip="Cutting depth (negative)\n"
                              "below the copper surface.",
                min_value=-9999.9999, max_value=(9999.999 if machinist_setting else 0.0),
                decimals=self.decimals, step=0.1
            ),
            CheckboxOptionUI(
                option="geometry_multidepth",
                label_text="Multi-Depth",
                label_tooltip="Use multiple passes to limit\n"
                              "the cut depth in each pass. Will\n"
                              "cut multiple times until Cut Z is\n"
                              "reached."
            ),
            DoubleSpinnerOptionUI(
                option="geometry_depthperpass",
                label_text="Depth/Pass",
                label_tooltip="The depth to cut on each pass,\n"
                              "when multidepth is enabled.\n"
                              "It has positive value although\n"
                              "it is a fraction from the depth\n"
                              "which has negative value.",
                min_value=0, max_value=99999, step=0.1, decimals=self.decimals

            ),
            DoubleSpinnerOptionUI(
                option="geometry_travelz",
                label_text="Travel Z",
                label_tooltip="Height of the tool when\n"
                              "moving without cutting.",
                min_value=(-9999.9999 if machinist_setting else 0.0001), max_value=9999.9999,
                step=0.1, decimals=self.decimals
            ),
            CheckboxOptionUI(
                option="geometry_toolchange",
                label_text="Tool change",
                label_tooltip="Include tool-change sequence\n"
                              "in the Machine Code (Pause for tool change)."
            ),
            DoubleSpinnerOptionUI(
                option="geometry_toolchangez",
                label_text="Toolchange Z",
                label_tooltip="Z-axis position (height) for\n"
                              "tool change.",
                min_value=(-9999.9999 if machinist_setting else 0.0), max_value=9999.9999,
                step=0.1, decimals=self.decimals
            ),
            DoubleSpinnerOptionUI(
                option="geometry_endz",
                label_text="End move Z",
                label_tooltip="Height of the tool after\n"
                              "the last move at the end of the job.",
                min_value=(-9999.9999 if machinist_setting else 0.0), max_value=9999.9999,
                step=0.1, decimals=self.decimals
            ),
            LineEntryOptionUI(
                option="geometry_endxy",
                label_text="End move X,Y",
                label_tooltip="End move X,Y position. In format (x,y).\n"
                              "If no value is entered then there is no move\n"
                              "on X,Y plane at the end of the job."
            ),
            DoubleSpinnerOptionUI(
                option="geometry_feedrate",
                label_text="Feedrate X-Y",
                label_tooltip="Cutting speed in the XY\n"
                              "plane in units per minute",
                min_value=0, max_value=99999.9999, step=0.1, decimals=self.decimals
            ),
            DoubleSpinnerOptionUI(
                option="geometry_feedrate_z",
                label_text="Feedrate Z",
                label_tooltip="Cutting speed in the XY\n"
                              "plane in units per minute.\n"
                              "It is called also Plunge.",
                min_value=0, max_value=99999.9999, step=0.1, decimals=self.decimals
            ),
            SpinnerOptionUI(
                option="geometry_spindlespeed",
                label_text="Spindle speed",
                label_tooltip="Speed of the spindle in RPM (optional).\n"
                              "If LASER preprocessor is used,\n"
                              "this value is the power of laser.",
                min_value=0, max_value=1000000, step=100
            ),
            CheckboxOptionUI(
                option="geometry_dwell",
                label_text="Enable Dwell",
                label_tooltip="Pause to allow the spindle to reach its\n"
                              "speed before cutting."
            ),
            DoubleSpinnerOptionUI(
                option="geometry_dwelltime",
                label_text="Duration",
                label_tooltip="Number of time units for spindle to dwell.",
                min_value=0, max_value=999999, step=0.5, decimals=self.decimals
            ),
            ComboboxOptionUI(
                option="geometry_ppname_g",
                label_text="Preprocessor",
                label_tooltip="The Preprocessor file that dictates\n"
                           "the Machine Code (like GCode, RML, HPGL) output.",
                choices=[]  # Populated in App (FIXME)
            )
        ]

