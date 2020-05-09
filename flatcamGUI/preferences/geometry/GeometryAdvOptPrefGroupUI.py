from flatcamGUI.preferences.OptionUI import *
from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI2

import gettext
import FlatCAMTranslation as fcTranslate
import builtins
fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GeometryAdvOptPrefGroupUI(OptionsGroupUI2):

    def __init__(self, decimals=4, **kwargs):
        self.decimals = decimals
        super().__init__(**kwargs)
        self.setTitle(str(_("Geometry Adv. Options")))

    def build_options(self) -> [OptionUI]:
        return [
            HeadingOptionUI(
                label_text="Advanced Options",
                label_tooltip="A list of Geometry advanced parameters.\n"
                              "Those parameters are available only for\n"
                              "Advanced App. Level."
            ),
            LineEntryOptionUI(
                option="geometry_toolchangexy",
                label_text="Toolchange X-Y",
                label_tooltip="Toolchange X,Y position."
            ),
            FloatEntryOptionUI(
                option="geometry_startz",
                label_text="Start Z",
                label_tooltip="Height of the tool just after starting the work.\n"
                              "Delete the value if you don't need this feature."
            ),
            DoubleSpinnerOptionUI(
                option="geometry_feedrate_rapid",
                label_text="Feedrate Rapids",
                label_tooltip="Cutting speed in the XY plane\n"
                              "(in units per minute).\n"
                              "This is for the rapid move G00.\n"
                              "It is useful only for Marlin,\n"
                              "ignore for any other cases.",
                min_value=0, max_value=99999.9999, step=10, decimals=self.decimals
            ),
            CheckboxOptionUI(
                option="geometry_extracut",
                label_text="Re-cut",
                label_tooltip="In order to remove possible\n"
                              "copper leftovers where first cut\n"
                              "meet with last cut, we generate an\n"
                              "extended cut over the first cut section."
            ),
            DoubleSpinnerOptionUI(
                option="geometry_extracut_length",
                label_text="Re-cut length",
                label_tooltip="In order to remove possible\n"
                              "copper leftovers where first cut\n"
                              "meet with last cut, we generate an\n"
                              "extended cut over the first cut section.",
                min_value=0, max_value=99999, step=0.1, decimals=self.decimals
            ),
            DoubleSpinnerOptionUI(
                option="geometry_z_pdepth",
                label_text="Probe Z depth",
                label_tooltip="The maximum depth that the probe is allowed\n"
                              "to probe. Negative value, in current units.",
                min_value=-99999, max_value=0.0, step=0.1, decimals=self.decimals
            ),
            DoubleSpinnerOptionUI(
                option="geometry_feedrate_probe",
                label_text="Feedrate Probe",
                label_tooltip="The feedrate used while the probe is probing.",
                min_value=0, max_value=99999.9999, step=0.1, decimals=self.decimals
            ),
            RadioSetOptionUI(
                option="geometry_spindledir",
                label_text="Spindle direction",
                label_tooltip="This sets the direction that the spindle is rotating.\n"
                              "It can be either:\n"
                              "- CW = clockwise or\n"
                              "- CCW = counter clockwise",
                choices=[{'label': _('CW'), 'value': 'CW'},
                         {'label': _('CCW'), 'value': 'CCW'}]
            ),
            CheckboxOptionUI(
                option="geometry_f_plunge",
                label_text="Fast Plunge",
                label_tooltip="By checking this, the vertical move from\n"
                              "Z_Toolchange to Z_move is done with G0,\n"
                              "meaning the fastest speed available.\n"
                              "WARNING: the move is done at Toolchange X,Y coords."
            ),
            DoubleSpinnerOptionUI(
                option="geometry_segx",
                label_text="Segment X size",
                label_tooltip="The size of the trace segment on the X axis.\n"
                              "Useful for auto-leveling.\n"
                              "A value of 0 means no segmentation on the X axis.",
                min_value=0, max_value=99999, step=0.1, decimals=self.decimals
            ),
            DoubleSpinnerOptionUI(
                option="geometry_segy",
                label_text="Segment Y size",
                label_tooltip="The size of the trace segment on the Y axis.\n"
                              "Useful for auto-leveling.\n"
                              "A value of 0 means no segmentation on the Y axis.",
                min_value=0, max_value=99999, step=0.1, decimals=self.decimals
            ),

            HeadingOptionUI(
                label_text="Area Exclusion",
                label_tooltip="Area exclusion parameters.\n"
                              "Those parameters are available only for\n"
                              "Advanced App. Level."
            ),
            CheckboxOptionUI(
                option="geometry_area_exclusion",
                label_text="Exclusion areas",
                label_tooltip="Include exclusion areas.\n"
                              "In those areas the travel of the tools\n"
                              "is forbidden."
            ),
            RadioSetOptionUI(
                option="geometry_area_shape",
                label_text="Shape",
                label_tooltip="The kind of selection shape used for area selection.",
                choices=[{'label': _("Square"),  'value': 'square'},
                         {'label': _("Polygon"), 'value': 'polygon'}]
            ),
            RadioSetOptionUI(
                option="geometry_area_strategy",
                label_text="Strategy",
                label_tooltip="The strategy followed when encountering an exclusion area.\n"
                              "Can be:\n"
                              "- Over -> when encountering the area, the tool will go to a set height\n"
                              "- Around -> will avoid the exclusion area by going around the area",
                choices=[{'label': _('Over'), 'value': 'over'},
                         {'label': _('Around'), 'value': 'around'}]
            ),
            DoubleSpinnerOptionUI(
                option="geometry_area_overz",
                label_text="Over Z",
                label_tooltip="The height Z to which the tool will rise in order to avoid\n"
                              "an interdiction area.",
                min_value=0.0, max_value=9999.9999, step=0.5, decimals=self.decimals
            )
        ]
