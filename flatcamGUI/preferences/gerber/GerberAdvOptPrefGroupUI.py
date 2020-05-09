from PyQt5 import QtWidgets

from flatcamGUI.GUIElements import FCCheckBox, RadioSet, FCDoubleSpinner, FCSpinner, OptionalInputSection
from flatcamGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GerberAdvOptPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):
        super(GerberAdvOptPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Gerber Adv. Options")))
        self.decimals = decimals

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

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 2, 0, 1, 2)

        # Tool Type
        self.tool_type_label = QtWidgets.QLabel('<b>%s</b>' % _('Tool Type'))
        self.tool_type_label.setToolTip(
            _("Choose which tool to use for Gerber isolation:\n"
              "'Circular' or 'V-shape'.\n"
              "When the 'V-shape' is selected then the tool\n"
              "diameter will depend on the chosen cut depth.")
        )
        self.tool_type_radio = RadioSet([{'label': 'Circular', 'value': 'circular'},
                                         {'label': 'V-Shape', 'value': 'v'}])

        grid0.addWidget(self.tool_type_label, 3, 0)
        grid0.addWidget(self.tool_type_radio, 3, 1, 1, 2)

        # Tip Dia
        self.tipdialabel = QtWidgets.QLabel('%s:' % _('V-Tip Dia'))
        self.tipdialabel.setToolTip(
            _("The tip diameter for V-Shape Tool")
        )
        self.tipdia_spinner = FCDoubleSpinner()
        self.tipdia_spinner.set_precision(self.decimals)
        self.tipdia_spinner.set_range(-99.9999, 99.9999)
        self.tipdia_spinner.setSingleStep(0.1)
        self.tipdia_spinner.setWrapping(True)
        grid0.addWidget(self.tipdialabel, 4, 0)
        grid0.addWidget(self.tipdia_spinner, 4, 1, 1, 2)

        # Tip Angle
        self.tipanglelabel = QtWidgets.QLabel('%s:' % _('V-Tip Angle'))
        self.tipanglelabel.setToolTip(
            _("The tip angle for V-Shape Tool.\n"
              "In degree.")
        )
        self.tipangle_spinner = FCSpinner()
        self.tipangle_spinner.set_range(1, 180)
        self.tipangle_spinner.set_step(5)
        self.tipangle_spinner.setWrapping(True)
        grid0.addWidget(self.tipanglelabel, 5, 0)
        grid0.addWidget(self.tipangle_spinner, 5, 1, 1, 2)

        # Cut Z
        self.cutzlabel = QtWidgets.QLabel('%s:' % _('Cut Z'))
        self.cutzlabel.setToolTip(
            _("Cutting depth (negative)\n"
              "below the copper surface.")
        )
        self.cutz_spinner = FCDoubleSpinner()
        self.cutz_spinner.set_precision(self.decimals)
        self.cutz_spinner.set_range(-99.9999, 0.0000)
        self.cutz_spinner.setSingleStep(0.1)
        self.cutz_spinner.setWrapping(True)

        grid0.addWidget(self.cutzlabel, 6, 0)
        grid0.addWidget(self.cutz_spinner, 6, 1, 1, 2)

        # Isolation Type
        self.iso_type_label = QtWidgets.QLabel('%s:' % _('Isolation Type'))
        self.iso_type_label.setToolTip(
            _("Choose how the isolation will be executed:\n"
              "- 'Full' -> complete isolation of polygons\n"
              "- 'Ext' -> will isolate only on the outside\n"
              "- 'Int' -> will isolate only on the inside\n"
              "'Exterior' isolation is almost always possible\n"
              "(with the right tool) but 'Interior'\n"
              "isolation can be done only when there is an opening\n"
              "inside of the polygon (e.g polygon is a 'doughnut' shape).")
        )
        self.iso_type_radio = RadioSet([{'label': _('Full'), 'value': 'full'},
                                        {'label': _('Exterior'), 'value': 'ext'},
                                        {'label': _('Interior'), 'value': 'int'}])

        grid0.addWidget(self.iso_type_label, 7, 0,)
        grid0.addWidget(self.iso_type_radio, 7, 1, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 8, 0, 1, 2)

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
        grid0.addWidget(buffering_label, 9, 0)
        grid0.addWidget(self.buffering_radio, 9, 1)

        # Simplification
        self.simplify_cb = FCCheckBox(label=_('Simplify'))
        self.simplify_cb.setToolTip(
            _("When checked all the Gerber polygons will be\n"
              "loaded with simplification having a set tolerance.\n"
              "<<WARNING>>: Don't change this unless you know what you are doing !!!")
                                    )
        grid0.addWidget(self.simplify_cb, 10, 0, 1, 2)

        # Simplification tolerance
        self.simplification_tol_label = QtWidgets.QLabel(_('Tolerance'))
        self.simplification_tol_label.setToolTip(_("Tolerance for polygon simplification."))

        self.simplification_tol_spinner = FCDoubleSpinner()
        self.simplification_tol_spinner.set_precision(self.decimals + 1)
        self.simplification_tol_spinner.setWrapping(True)
        self.simplification_tol_spinner.setRange(0.00000, 0.01000)
        self.simplification_tol_spinner.setSingleStep(0.0001)

        grid0.addWidget(self.simplification_tol_label, 11, 0)
        grid0.addWidget(self.simplification_tol_spinner, 11, 1)
        self.ois_simplif = OptionalInputSection(
            self.simplify_cb,
            [
                self.simplification_tol_label, self.simplification_tol_spinner
            ],
            logic=True)

        self.layout.addStretch()
