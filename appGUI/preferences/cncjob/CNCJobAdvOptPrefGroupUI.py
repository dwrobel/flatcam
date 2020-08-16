from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QSettings, Qt

from appGUI.GUIElements import FCComboBox, FCSpinner, FCColorEntry, FCLabel, FCDoubleSpinner, RadioSet
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI
import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

settings = QSettings("Open Source", "FlatCAM")
if settings.contains("machinist"):
    machinist_setting = settings.value('machinist', type=int)
else:
    machinist_setting = 0


class CNCJobAdvOptPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "CNC Job Advanced Options Preferences", parent=None)
        super(CNCJobAdvOptPrefGroupUI, self).__init__(self, parent=parent)
        self.decimals = decimals

        self.setTitle(str(_("CNC Job Adv. Options")))

        grid0 = QtWidgets.QGridLayout()
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        self.layout.addLayout(grid0)

        # ## Export G-Code
        self.export_gcode_label = QtWidgets.QLabel("<b>%s:</b>" % _("Parameters"))
        self.export_gcode_label.setToolTip(
            _("Export and save G-Code to\n"
              "make this object to a file.")
        )
        grid0.addWidget(self.export_gcode_label, 0, 0, 1, 2)

        # Annotation Font Size
        self.annotation_fontsize_label = QtWidgets.QLabel('%s:' % _("Annotation Size"))
        self.annotation_fontsize_label.setToolTip(
            _("The font size of the annotation text. In pixels.")
        )
        self.annotation_fontsize_sp = FCSpinner()
        self.annotation_fontsize_sp.set_range(0, 9999)

        grid0.addWidget(self.annotation_fontsize_label, 2, 0)
        grid0.addWidget(self.annotation_fontsize_sp, 2, 1)

        # Annotation Font Color
        self.annotation_color_label = QtWidgets.QLabel('%s:' % _('Annotation Color'))
        self.annotation_color_label.setToolTip(
            _("Set the font color for the annotation texts.")
        )
        self.annotation_fontcolor_entry = FCColorEntry()

        grid0.addWidget(self.annotation_color_label, 4, 0)
        grid0.addWidget(self.annotation_fontcolor_entry, 4, 1)

        # ## Autolevelling
        self.autolevelling_gcode_label = QtWidgets.QLabel("<b>%s</b>" % _("Autolevelling"))
        self.autolevelling_gcode_label.setToolTip(
            _("Parameters for the autolevelling.")
        )
        grid0.addWidget(self.autolevelling_gcode_label, 6, 0, 1, 2)

        # Probe points mode
        al_mode_lbl = FCLabel('%s:' % _("Mode"))
        al_mode_lbl.setToolTip(_("Choose a mode for height map generation.\n"
                                 "- Manual: will pick a selection of probe points by clicking on canvas\n"
                                 "- Grid: will automatically generate a grid of probe points"))

        self.al_mode_radio = RadioSet(
            [
                {'label': _('Manual'), 'value': 'manual'},
                {'label': _('Grid'), 'value': 'grid'}
            ])
        grid0.addWidget(al_mode_lbl, 8, 0)
        grid0.addWidget(self.al_mode_radio, 8, 1)

        # ## Columns
        self.al_columns_entry = FCSpinner()

        self.al_columns_label = QtWidgets.QLabel('%s:' % _("Columns"))
        self.al_columns_label.setToolTip(
            _("The number of grid columns.")
        )
        grid0.addWidget(self.al_columns_label, 10, 0)
        grid0.addWidget(self.al_columns_entry, 10, 1)

        # ## Rows
        self.al_rows_entry = FCSpinner()

        self.al_rows_label = QtWidgets.QLabel('%s:' % _("Rows"))
        self.al_rows_label.setToolTip(
            _("The number of gird rows.")
        )
        grid0.addWidget(self.al_rows_label, 12, 0)
        grid0.addWidget(self.al_rows_entry, 12, 1)

        # Travel Z Probe
        self.ptravelz_label = QtWidgets.QLabel('%s:' % _("Probe Z travel"))
        self.ptravelz_label.setToolTip(
            _("The safe Z for probe travelling between probe points.")
        )
        self.ptravelz_entry = FCDoubleSpinner()
        self.ptravelz_entry.set_precision(self.decimals)
        self.ptravelz_entry.set_range(0.0000, 9999.9999)

        grid0.addWidget(self.ptravelz_label, 14, 0)
        grid0.addWidget(self.ptravelz_entry, 14, 1)

        # Probe depth
        self.pdepth_label = QtWidgets.QLabel('%s:' % _("Probe Z depth"))
        self.pdepth_label.setToolTip(
            _("The maximum depth that the probe is allowed\n"
              "to probe. Negative value, in current units.")
        )
        self.pdepth_entry = FCDoubleSpinner()
        self.pdepth_entry.set_precision(self.decimals)
        self.pdepth_entry.set_range(-99999.9999, 0.0000)

        grid0.addWidget(self.pdepth_label, 16, 0)
        grid0.addWidget(self.pdepth_entry, 16, 1)

        # Probe feedrate
        self.feedrate_probe_label = QtWidgets.QLabel('%s:' % _("Probe Feedrate"))
        self.feedrate_probe_label.setToolTip(
            _("The feedrate used while the probe is probing.")
        )
        self.feedrate_probe_entry = FCDoubleSpinner()
        self.feedrate_probe_entry.set_precision(self.decimals)
        self.feedrate_probe_entry.set_range(0, 99999.9999)

        grid0.addWidget(self.feedrate_probe_label, 18, 0)
        grid0.addWidget(self.feedrate_probe_entry, 18, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 20, 0, 1, 2)

        self.al_controller_label = FCLabel('%s:' % _("Controller"))
        self.al_controller_label.setToolTip(
            _("The kind of controller for which to generate\n"
              "height map gcode.")
        )

        self.al_controller_combo = FCComboBox()
        self.al_controller_combo.addItems(["MACH3", "MACH4", "LinuxCNC", "GRBL"])
        grid0.addWidget(self.al_controller_label, 22, 0)
        grid0.addWidget(self.al_controller_combo, 22, 1)

        self.layout.addStretch()

        self.annotation_fontcolor_entry.editingFinished.connect(self.on_annotation_fontcolor_entry)

    def on_annotation_fontcolor_entry(self):
        self.app.defaults['cncjob_annotation_fontcolor'] = self.annotation_fontcolor_entry.get_value()
