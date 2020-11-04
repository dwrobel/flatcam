from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QSettings

from appGUI.GUIElements import RadioSet, FCDoubleSpinner, FCCheckBox, FCEntry, FCSpinner, OptionalInputSection, \
    FCComboBox, NumericalEvalTupleEntry
from appGUI.preferences import machinist_setting
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


class ExcellonOptPrefGroupUI(OptionsGroupUI):

    def __init__(self, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "Excellon Options", parent=parent)
        super(ExcellonOptPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Excellon Options")))
        self.decimals = decimals

        # ## Create CNC Job
        self.cncjob_label = QtWidgets.QLabel('<b>%s</b>' % _('Create CNCJob'))
        self.cncjob_label.setToolTip(
            _("Parameters used to create a CNC Job object\n"
              "for this drill object.")
        )
        self.layout.addWidget(self.cncjob_label)

        grid2 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid2)
        grid2.setColumnStretch(0, 0)
        grid2.setColumnStretch(1, 1)

        # Operation Type
        self.operation_label = QtWidgets.QLabel('<b>%s:</b>' % _('Operation'))
        self.operation_label.setToolTip(
            _("Operation type:\n"
              "- Drilling -> will drill the drills/slots associated with this tool\n"
              "- Milling -> will mill the drills/slots")
        )
        self.operation_radio = RadioSet(
            [
                {'label': _('Drilling'), 'value': 'drill'},
                {'label': _("Milling"), 'value': 'mill'}
            ]
        )

        grid2.addWidget(self.operation_label, 0, 0)
        grid2.addWidget(self.operation_radio, 0, 1)

        self.mill_type_label = QtWidgets.QLabel('%s:' % _('Milling Type'))
        self.mill_type_label.setToolTip(
            _("Milling type:\n"
              "- Drills -> will mill the drills associated with this tool\n"
              "- Slots -> will mill the slots associated with this tool\n"
              "- Both -> will mill both drills and mills or whatever is available")
        )
        self.milling_type_radio = RadioSet(
            [
                {'label': _('Drills'), 'value': 'drills'},
                {'label': _("Slots"), 'value': 'slots'},
                {'label': _("Both"), 'value': 'both'},
            ]
        )

        grid2.addWidget(self.mill_type_label, 1, 0)
        grid2.addWidget(self.milling_type_radio, 1, 1)

        self.mill_dia_label = QtWidgets.QLabel('%s:' % _('Milling Diameter'))
        self.mill_dia_label.setToolTip(
            _("The diameter of the tool who will do the milling")
        )

        self.mill_dia_entry = FCDoubleSpinner()
        self.mill_dia_entry.set_precision(self.decimals)
        self.mill_dia_entry.set_range(0.0000, 10000.0000)

        grid2.addWidget(self.mill_dia_label, 2, 0)
        grid2.addWidget(self.mill_dia_entry, 2, 1)

        # ### Milling Holes ## ##
        self.mill_hole_label = QtWidgets.QLabel('<b>%s</b>' % _('Mill Holes'))
        self.mill_hole_label.setToolTip(
            _("Create Geometry for milling holes.")
        )
        grid2.addWidget(self.mill_hole_label, 16, 0, 1, 2)

        tdlabel = QtWidgets.QLabel('%s:' % _('Drill Tool dia'))
        tdlabel.setToolTip(
            _("Diameter of the cutting tool.")
        )
        self.tooldia_entry = FCDoubleSpinner()
        self.tooldia_entry.set_precision(self.decimals)
        self.tooldia_entry.set_range(0, 999.9999)

        grid2.addWidget(tdlabel, 18, 0)
        grid2.addWidget(self.tooldia_entry, 18, 1)

        stdlabel = QtWidgets.QLabel('%s:' % _('Slot Tool dia'))
        stdlabel.setToolTip(
            _("Diameter of the cutting tool\n"
              "when milling slots.")
        )
        self.slot_tooldia_entry = FCDoubleSpinner()
        self.slot_tooldia_entry.set_precision(self.decimals)
        self.slot_tooldia_entry.set_range(0, 999.9999)

        grid2.addWidget(stdlabel, 21, 0)
        grid2.addWidget(self.slot_tooldia_entry, 21, 1)

        self.layout.addStretch()
