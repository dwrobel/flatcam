from PyQt5.QtCore import Qt

from flatcamGUI.preferences.OptionUI import *
from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI2
import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class CNCJobAdvOptPrefGroupUI(OptionsGroupUI2):

    def __init__(self, decimals=4, **kwargs):
        self.decimals = decimals
        super().__init__(**kwargs)
        self.setTitle(str(_("CNC Job Adv. Options")))

        self.toolchange_text = self.option_dict()["cncjob_toolchange_macro"].get_field()

        # Populate the Combo Box
        self.tc_variable_combo = self.option_dict()["__toolchange_variable"].get_field()
        variables = [_('Parameters'), 'tool', 'tooldia', 't_drills', 'x_toolchange', 'y_toolchange', 'z_toolchange',
                     'z_cut', 'z_move', 'z_depthpercut', 'spindlespeed', 'dwelltime']
        self.tc_variable_combo.addItems(variables)
        self.tc_variable_combo.insertSeparator(1)

        self.tc_variable_combo.setItemData(0, _("FlatCAM CNC parameters"), Qt.ToolTipRole)
        fnt = QtGui.QFont()
        fnt.setBold(True)
        self.tc_variable_combo.setItemData(0, fnt, Qt.FontRole)

        self.tc_variable_combo.setItemData(2, 'tool = %s' % _("tool number"), Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(3, 'tooldia = %s' % _("tool diameter"), Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(4, 't_drills = %s' % _("for Excellon, total number of drills"),
                                           Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(5, 'x_toolchange = %s' % _("X coord for Toolchange"), Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(6, 'y_toolchange = %s' % _("Y coord for Toolchange"),
                                           Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(7, 'z_toolchange = %s' % _("Z coord for Toolchange"), Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(8, 'z_cut = %s' % _("Z depth for the cut"), Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(9, 'z_move = %s' % _("Z height for travel"), Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(10, 'z_depthpercut = %s' % _("the step value for multidepth cut"),
                                           Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(11, 'spindlesspeed = %s' % _("the value for the spindle speed"),
                                           Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(12,
                                           _("dwelltime = time to dwell to allow the spindle to reach it's set RPM"),
                                           Qt.ToolTipRole)

        self.tc_variable_combo.currentIndexChanged[str].connect(self.on_cnc_custom_parameters)

    def build_options(self) -> [OptionUI]:
        return [
            HeadingOptionUI(
                label_text="Export CNC Code",
                label_tooltip="Export and save G-Code to\n"
                              "make this object to a file."
            ),
            CheckboxOptionUI(
                option="cncjob_toolchange_macro_enable",
                label_text="Use Toolchange Macro",
                label_tooltip="Check this box if you want to use\n"
                              "a Custom Toolchange GCode (macro)."
            ),
            TextAreaOptionUI(
                option="cncjob_toolchange_macro",
                label_text="Toolchange G-Code",
                label_tooltip="Type here any G-Code commands you would "
                              "like to be executed when Toolchange event is encountered.\n"
                              "This will constitute a Custom Toolchange GCode, "
                              "or a Toolchange Macro.\n"
                              "The FlatCAM variables are surrounded by '%' symbol.\n"
                              "WARNING: it can be used only with a preprocessor file "
                              "that has 'toolchange_custom' in it's name."
            ),
            ComboboxOptionUI(
                option="__toolchange_variable",
                label_text="Insert variable",
                label_tooltip="A list of the FlatCAM variables that can be used\n"
                              "in the Toolchange event.\n"
                              "They have to be surrounded by the '%' symbol",
                choices=[]  # see init.
            ),

            SpinnerOptionUI(
                option="cncjob_annotation_fontsize",
                label_text="Annotation Size",
                label_tooltip="The font size of the annotation text. In pixels.",
                min_value=1, max_value=9999, step=1
            ),
            ColorOptionUI(
                option="cncjob_annotation_fontcolor",
                label_text="Annotation Color",
                label_tooltip="Set the font color for the annotation texts."
            )
        ]

    def on_cnc_custom_parameters(self, signal_text):
        if signal_text == _("Parameters"):
            return
        else:
            self.toolchange_text.insertPlainText('%%%s%%' % signal_text)
            self.tc_variable_combo.set_value(_("Parameters"))

