from flatcamGUI.preferences.OptionUI import *
from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI2

import gettext
import FlatCAMTranslation as fcTranslate
import builtins
fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ExcellonAdvOptPrefGroupUI(OptionsGroupUI2):

    def __init__(self, decimals=4, **kwargs):
        self.decimals = decimals
        super().__init__(**kwargs)
        self.setTitle(str(_("Excellon Adv. Options")))

    def build_options(self) -> [OptionUI]:
        return [
            HeadingOptionUI(
                label_text="Advanced Options",
                label_tooltip="A list of Excellon advanced parameters.\n"
                              "Those parameters are available only for\n"
                              "Advanced App. Level."
            ),
            DoubleSpinnerOptionUI(
                option="excellon_offset",
                label_text="Offset Z",
                label_tooltip="Some drill bits (the larger ones) need to drill deeper\n"
                              "to create the desired exit hole diameter due of the tip shape.\n"
                              "The value here can compensate the Cut Z parameter.",
                min_value=-999.9999, max_value=999.9999, step=0.1, decimals=self.decimals
            ),
            LineEntryOptionUI(
                option="excellon_toolchangexy",
                label_text="Toolchange X,Y",
                label_tooltip="Toolchange X,Y position."
            ),
            FloatEntryOptionUI(
                option="excellon_startz",
                label_text="Start Z",
                label_tooltip="Height of the tool just after start.\n"
                           "Delete the value if you don't need this feature."
            ),
            DoubleSpinnerOptionUI(
                option="excellon_feedrate_rapid",
                label_text="Feedrate Rapids",
                label_tooltip="Tool speed while drilling\n"
                              "(in units per minute).\n"
                              "This is for the rapid move G00.\n"
                              "It is useful only for Marlin,\n"
                              "ignore for any other cases.",
                min_value=0.0001, max_value=99999.9999, step=50, decimals=self.decimals
            ),
            DoubleSpinnerOptionUI(
                option="excellon_z_pdepth",
                label_text="Probe Z depth",
                label_tooltip="The maximum depth that the probe is allowed\n"
                              "to probe. Negative value, in current units.",
                min_value=-99999.9999, max_value=0.0, step=0.1, decimals=self.decimals
            ),
            DoubleSpinnerOptionUI(
                option="excellon_feedrate_probe",
                label_text="Feedrate Probe",
                label_tooltip="The feedrate used while the probe is probing.",
                min_value=0.0001, max_value=99999.9999, step=0.1, decimals=self.decimals
            ),
            RadioSetOptionUI(
                option="excellon_spindledir",
                label_text="Spindle direction",
                label_tooltip="This sets the direction that the spindle is rotating.\n"
                              "It can be either:\n"
                              "- CW = clockwise or\n"
                              "- CCW = counter clockwise",
                choices=[{'label': _('CW'), 'value': 'CW'},
                         {'label': _('CCW'), 'value': 'CCW'}]
            ),
            CheckboxOptionUI(
                option="excellon_f_plunge",
                label_text="Fast Plunge",
                label_tooltip="By checking this, the vertical move from\n"
                              "Z_Toolchange to Z_move is done with G0,\n"
                              "meaning the fastest speed available.\n"
                              "WARNING: the move is done at Toolchange X,Y coords."
            ),
            CheckboxOptionUI(
                option="excellon_f_retract",
                label_text="Fast Retract",
                label_tooltip="Exit hole strategy.\n"
                              " - When uncheked, while exiting the drilled hole the drill bit\n"
                              "will travel slow, with set feedrate (G1), up to zero depth and then\n"
                              "travel as fast as possible (G0) to the Z Move (travel height).\n"
                              " - When checked the travel from Z cut (cut depth) to Z_move\n"
                              "(travel height) is done as fast as possible (G0) in one move."
            )
        ]