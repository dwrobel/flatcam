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


class ExcellonOptPrefGroupUI(OptionsGroupUI2):

    def __init__(self, decimals=4, **kwargs):
        self.decimals = decimals
        super().__init__(**kwargs)
        self.setTitle(str(_("Excellon Options")))

        self.pp_excellon_name_cb = self.option_dict()["excellon_ppname_e"].get_field()

        self.multidepth_cb = self.option_dict()["excellon_multidepth"].get_field()
        self.depthperpass_entry = self.option_dict()["excellon_depthperpass"].get_field()
        self.ois_multidepth = OptionalInputSection(self.multidepth_cb, [self.depthperpass_entry])

        self.dwell_cb = self.option_dict()["excellon_dwell"].get_field()
        self.dwelltime_entry = self.option_dict()["excellon_dwelltime"].get_field()
        self.ois_dwell = OptionalInputSection(self.dwell_cb, [self.dwelltime_entry])

        # FIXME until this feature is implemented these are disabled
        self.option_dict()["excellon_gcode_type"].label_widget.hide()
        self.option_dict()["excellon_gcode_type"].get_field().hide()

    def build_options(self) -> [OptionUI]:
        return [
            HeadingOptionUI(
                label_text="Create CNC Job",
                label_tooltip="Parameters used to create a CNC Job object\n"
                              "for this drill object."
            ),
            RadioSetOptionUI(
                option="excellon_operation",
                label_text="Operation",
                label_bold=True,
                label_tooltip="Operation type:\n"
                              "- Drilling -> will drill the drills/slots associated with this tool\n"
                              "- Milling -> will mill the drills/slots",
                choices=[
                    {'label': _('Drilling'), 'value': 'drill'},
                    {'label': _("Milling"),  'value': 'mill'}
                ]
            ),
            RadioSetOptionUI(
                option="excellon_milling_type",
                label_text="Milling Type",
                label_tooltip="Milling type:\n"
                              "- Drills -> will mill the drills associated with this tool\n"
                              "- Slots -> will mill the slots associated with this tool\n"
                              "- Both -> will mill both drills and mills or whatever is available",
                choices=[
                    {'label': _('Drills'), 'value': 'drills'},
                    {'label': _("Slots"), 'value': 'slots'},
                    {'label': _("Both"), 'value': 'both'},
                ]
            ),
            DoubleSpinnerOptionUI(
                option="excellon_milling_dia",
                label_text="Milling Diameter",
                label_tooltip="The diameter of the tool who will do the milling",
                min_value=0.0, max_value=9999.9999, step=0.1, decimals=self.decimals
            ),
            DoubleSpinnerOptionUI(
                option="excellon_cutz",
                label_text="Cut Z",
                label_tooltip="Drill depth (negative) \nbelow the copper surface.",
                min_value=-9999.9999, max_value=(9999.9999 if machinist_setting else 0.0),
                step=0.1, decimals=self.decimals
            ),


            CheckboxOptionUI(
                option="excellon_multidepth",
                label_text="Multi-Depth",
                label_tooltip="Use multiple passes to limit\n"
                              "the cut depth in each pass. Will\n"
                              "cut multiple times until Cut Z is\n"
                              "reached."
            ),
            DoubleSpinnerOptionUI(
                option="excellon_depthperpass",
                label_text="Depth/Pass",
                label_tooltip="Depth of each pass (positive).",
                min_value=0, max_value=99999, step=0.1, decimals=self.decimals
            ),
            DoubleSpinnerOptionUI(
                option="excellon_travelz",
                label_text="Travel Z",
                label_tooltip="Tool height when travelling\nacross the XY plane.",
                min_value=(-9999.9999 if machinist_setting else 0.0001), max_value=9999.9999,
                step=0.1, decimals=self.decimals
            ),
            CheckboxOptionUI(
                option="excellon_toolchange",
                label_text="Tool change",
                label_tooltip="Include tool-change sequence\nin G-Code (Pause for tool change)."
            ),
            DoubleSpinnerOptionUI(
                option="excellon_toolchangez",
                label_text="Toolchange Z",
                label_tooltip="Z-axis position (height) for\ntool change.",
                min_value=(-9999.9999 if machinist_setting else 0.0), max_value=9999.9999,
                step=0.1, decimals=self.decimals
            ),
            DoubleSpinnerOptionUI(
                option="excellon_endz",
                label_text="End move Z",
                label_tooltip="Height of the tool after\nthe last move at the end of the job.",
                min_value=(-9999.9999 if machinist_setting else 0.0), max_value=9999.9999,
                step=0.1, decimals=self.decimals
            ),
            LineEntryOptionUI(
                option="excellon_endxy",
                label_text="End move X,Y",
                label_tooltip="End move X,Y position. In format (x,y).\n"
                              "If no value is entered then there is no move\n"
                              "on X,Y plane at the end of the job."
            ),
            DoubleSpinnerOptionUI(
                option="excellon_feedrate_z",
                label_text="Feedrate Z",
                label_tooltip="Tool speed while drilling\n"
                              "(in units per minute).\n"
                              "So called 'Plunge' feedrate.\n"
                              "This is for linear move G01.",
                min_value=0, max_value=99999.9999, step=0.1, decimals=self.decimals
            ),
            SpinnerOptionUI(
                option="excellon_spindlespeed",
                label_text="Spindle speed",
                label_tooltip="Speed of the spindle in RPM (optional).",
                min_value=0, max_value=1000000, step=100
            ),
            CheckboxOptionUI(
                option="excellon_dwell",
                label_text="Enable Dwell",
                label_tooltip="Pause to allow the spindle to reach its\nspeed before cutting."
            ),
            DoubleSpinnerOptionUI(
                option="excellon_dwelltime",
                label_text="Duration",
                label_tooltip="Number of time units for spindle to dwell.",
                min_value=0, max_value=999999, step=0.5, decimals=self.decimals
            ),
            ComboboxOptionUI(
                option="excellon_ppname_e",
                label_text="Preprocessor",
                label_tooltip="The preprocessor JSON file that dictates\nGcode output.", # FIXME tooltip incorrect?
                choices=[]  # Populated in App (FIXME)
            ),
            RadioSetOptionUI(
                option="excellon_gcode_type",
                label_text="Gcode",
                label_bold=True,
                label_tooltip="Choose what to use for GCode generation:\n"
                              "'Drills', 'Slots' or 'Both'.\n"
                              "When choosing 'Slots' or 'Both', slots will be\n"
                              "converted to drills.",
                choices=[
                    {'label': 'Drills', 'value': 'drills'},
                    {'label': 'Slots',  'value': 'slots'},
                    {'label': 'Both',   'value': 'both'}
                ]
            ),

            HeadingOptionUI(
                label_text="Mill Holes",
                label_tooltip="Create Geometry for milling holes."
            ),
            DoubleSpinnerOptionUI(
                option="excellon_tooldia",
                label_text="Drill Tool dia",
                label_tooltip="Diameter of the cutting tool",
                min_value=0.0, max_value=999.9999, step=0.1, decimals=self.decimals
            ),
            DoubleSpinnerOptionUI(
                option="excellon_slot_tooldia",
                label_text="Slot Tool dia",
                label_tooltip="Diameter of the cutting tool\nwhen milling slots.",
                min_value=0.0, max_value=999.9999, step=0.1, decimals=self.decimals
            )
        ]
