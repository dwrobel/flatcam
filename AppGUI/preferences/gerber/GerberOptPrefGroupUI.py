from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings

from AppGUI.GUIElements import FCDoubleSpinner, FCSpinner, RadioSet, FCCheckBox
from AppGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import AppTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

settings = QSettings("Open Source", "FlatCAM")
if settings.contains("machinist"):
    machinist_setting = settings.value('machinist', type=int)
else:
    machinist_setting = 0


class GerberOptPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "Gerber Options Preferences", parent=parent)
        super(GerberOptPrefGroupUI, self).__init__(self, parent=parent)

        self.decimals = decimals

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
        self.iso_tool_dia_entry = FCDoubleSpinner()
        self.iso_tool_dia_entry.set_precision(self.decimals)
        self.iso_tool_dia_entry.setSingleStep(0.1)
        self.iso_tool_dia_entry.set_range(-9999, 9999)

        grid0.addWidget(self.iso_tool_dia_entry, 0, 1)

        # Nr of passes
        passlabel = QtWidgets.QLabel('%s:' % _('# Passes'))
        passlabel.setToolTip(
            _("Width of the isolation gap in\n"
              "number (integer) of tool widths.")
        )
        self.iso_width_entry = FCSpinner()
        self.iso_width_entry.set_range(1, 999)

        grid0.addWidget(passlabel, 1, 0)
        grid0.addWidget(self.iso_width_entry, 1, 1)

        # Pass overlap
        overlabel = QtWidgets.QLabel('%s:' % _('Pass overlap'))
        overlabel.setToolTip(
            _("How much (percentage) of the tool width to overlap each tool pass.")
        )
        self.iso_overlap_entry = FCDoubleSpinner(suffix='%')
        self.iso_overlap_entry.set_precision(self.decimals)
        self.iso_overlap_entry.setWrapping(True)
        self.iso_overlap_entry.setRange(0.0000, 99.9999)
        self.iso_overlap_entry.setSingleStep(0.1)

        grid0.addWidget(overlabel, 2, 0)
        grid0.addWidget(self.iso_overlap_entry, 2, 1)

        # Isolation Scope
        self.iso_scope_label = QtWidgets.QLabel('%s:' % _('Scope'))
        self.iso_scope_label.setToolTip(
            _("Isolation scope. Choose what to isolate:\n"
              "- 'All' -> Isolate all the polygons in the object\n"
              "- 'Selection' -> Isolate a selection of polygons.")
        )
        self.iso_scope_radio = RadioSet([{'label': _('All'), 'value': 'all'},
                                         {'label': _('Selection'), 'value': 'single'}])

        grid0.addWidget(self.iso_scope_label, 3, 0)
        grid0.addWidget(self.iso_scope_radio, 3, 1, 1, 2)

        # Milling Type
        milling_type_label = QtWidgets.QLabel('%s:' % _('Milling Type'))
        milling_type_label.setToolTip(
            _("Milling type:\n"
              "- climb / best for precision milling and to reduce tool usage\n"
              "- conventional / useful when there is no backlash compensation")
        )
        grid0.addWidget(milling_type_label, 4, 0)
        self.milling_type_radio = RadioSet([{'label': _('Climb'), 'value': 'cl'},
                                            {'label': _('Conventional'), 'value': 'cv'}])
        grid0.addWidget(self.milling_type_radio, 4, 1)

        # Combine passes
        self.combine_passes_cb = FCCheckBox(label=_('Combine Passes'))
        self.combine_passes_cb.setToolTip(
            _("Combine all passes into one object")
        )
        grid0.addWidget(self.combine_passes_cb, 5, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 6, 0, 1, 2)

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
        self.noncopper_margin_entry = FCDoubleSpinner()
        self.noncopper_margin_entry.set_precision(self.decimals)
        self.noncopper_margin_entry.setSingleStep(0.1)
        self.noncopper_margin_entry.set_range(-9999, 9999)
        grid1.addWidget(self.noncopper_margin_entry, 0, 1)

        # Rounded corners
        self.noncopper_rounded_cb = FCCheckBox(label=_("Rounded Geo"))
        self.noncopper_rounded_cb.setToolTip(
            _("Resulting geometry will have rounded corners.")
        )
        grid1.addWidget(self.noncopper_rounded_cb, 1, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid1.addWidget(separator_line, 2, 0, 1, 2)

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
        self.bbmargin_entry = FCDoubleSpinner()
        self.bbmargin_entry.set_precision(self.decimals)
        self.bbmargin_entry.setSingleStep(0.1)
        self.bbmargin_entry.set_range(-9999, 9999)

        grid2.addWidget(bbmargin, 0, 0)
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
