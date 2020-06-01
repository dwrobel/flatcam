from flatcamGUI.preferences.OptionUI import *
from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI2

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GerberOptPrefGroupUI(OptionsGroupUI2):

    def __init__(self, decimals=4, **kwargs):
        self.decimals = decimals
        super().__init__(**kwargs)
        self.setTitle(str(_("Gerber Options")))

    def build_options(self) -> [OptionUI]:
        return [
            HeadingOptionUI(
                label_text="Isolation Routing",
                label_tooltip="Create a Geometry object with\n"
                              "toolpaths to cut outside polygons."
            ),
            DoubleSpinnerOptionUI(
                option="gerber_isotooldia",
                label_text="Tool dia",
                label_tooltip="Diameter of the cutting tool.",
                min_value=0.0, max_value=9999.9, step=0.1, decimals=self.decimals
            ),
            SpinnerOptionUI(
                option="gerber_isopasses",
                label_text="# Passes",
                label_tooltip="Width of the isolation gap in\n"
                              "number (integer) of tool widths.",
                min_value=1, max_value=999, step=1
            ),
            DoubleSpinnerOptionUI(
                option="gerber_isooverlap",
                label_text="Pass overlap",
                label_tooltip="How much (percentage) of the tool width to overlap each tool pass.",
                min_value=0.0, max_value=99.9999, step=0.1, decimals=self.decimals, suffix="%"
            ),
            RadioSetOptionUI(
                option="gerber_iso_scope",
                label_text="Scope",
                label_tooltip="Isolation scope. Choose what to isolate:\n"
                              "- 'All' -> Isolate all the polygons in the object\n"
                              "- 'Selection' -> Isolate a selection of polygons.",
                choices=[{'label': _('All'),       'value': 'all'},
                         {'label': _('Selection'), 'value': 'single'}]
            ),
            RadioSetOptionUI(
                option="gerber_milling_type",
                label_text="Milling Type",
                label_tooltip="Milling type:\n"
                              "- climb / best for precision milling and to reduce tool usage\n"
                              "- conventional / useful when there is no backlash compensation",
                choices=[{'label': _('Climb'),        'value': 'cl'},
                         {'label': _('Conventional'), 'value': 'cv'}]
            ),
            CheckboxOptionUI(
                option="gerber_combine_passes",
                label_text="Combine Passes",
                label_tooltip="Combine all passes into one object"
            ),
            SeparatorOptionUI(),

            HeadingOptionUI(
                label_text="Non-copper regions",
                label_tooltip="Create polygons covering the\n"
                              "areas without copper on the PCB.\n"
                              "Equivalent to the inverse of this\n"
                              "object. Can be used to remove all\n"
                              "copper from a specified region."
            ),
            DoubleSpinnerOptionUI(
                option="gerber_noncoppermargin",
                label_text="Boundary Margin",
                label_tooltip="Specify the edge of the PCB\n"
                              "by drawing a box around all\n"
                              "objects with this minimum\n"
                              "distance.",
                min_value=-9999, max_value=9999, step=0.1, decimals=self.decimals
            ),
            CheckboxOptionUI(
                option="gerber_noncopperrounded",
                label_text="Rounded Geo",
                label_tooltip="Resulting geometry will have rounded corners."
            ),
            SeparatorOptionUI(),

            HeadingOptionUI(label_text="Bounding Box"),
            DoubleSpinnerOptionUI(
                option="gerber_bboxmargin",
                label_text="Boundary Margin",
                label_tooltip="Distance of the edges of the box\n"
                              "to the nearest polygon.",
                min_value=-9999, max_value=9999, step=0.1, decimals=self.decimals
            ),
            CheckboxOptionUI(
                option="gerber_bboxrounded",
                label_text="Rounded Geo",
                label_tooltip="If the bounding box is \n"
                              "to have rounded corners\n"
                              "their radius is equal to\n"
                              "the margin."
            ),
        ]