from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings

from appGUI.GUIElements import FCDoubleSpinner, FCSpinner, RadioSet, FCCheckBox
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


class ToolsPanelizePrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "Cutout Tool Options", parent=parent)
        super(ToolsPanelizePrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Panelize Tool Options")))
        self.decimals = decimals

        # ## Board cuttout
        self.panelize_label = QtWidgets.QLabel("<b>%s:</b>" % _("Parameters"))
        self.panelize_label.setToolTip(
            _("Create an object that contains an array of (x, y) elements,\n"
              "each element is a copy of the source object spaced\n"
              "at a X distance, Y distance of each other.")
        )
        self.layout.addWidget(self.panelize_label)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)

        # ## Spacing Columns
        self.pspacing_columns = FCDoubleSpinner()
        self.pspacing_columns.set_range(0.000001, 10000.0000)
        self.pspacing_columns.set_precision(self.decimals)
        self.pspacing_columns.setSingleStep(0.1)

        self.spacing_columns_label = QtWidgets.QLabel('%s:' % _("Spacing cols"))
        self.spacing_columns_label.setToolTip(
            _("Spacing between columns of the desired panel.\n"
              "In current units.")
        )
        grid0.addWidget(self.spacing_columns_label, 0, 0)
        grid0.addWidget(self.pspacing_columns, 0, 1)

        # ## Spacing Rows
        self.pspacing_rows = FCDoubleSpinner()
        self.pspacing_rows.set_range(0.000001, 10000.0000)
        self.pspacing_rows.set_precision(self.decimals)
        self.pspacing_rows.setSingleStep(0.1)

        self.spacing_rows_label = QtWidgets.QLabel('%s:' % _("Spacing rows"))
        self.spacing_rows_label.setToolTip(
            _("Spacing between rows of the desired panel.\n"
              "In current units.")
        )
        grid0.addWidget(self.spacing_rows_label, 1, 0)
        grid0.addWidget(self.pspacing_rows, 1, 1)

        # ## Columns
        self.pcolumns = FCSpinner()
        self.pcolumns.set_range(1, 1000)
        self.pcolumns.set_step(1)

        self.columns_label = QtWidgets.QLabel('%s:' % _("Columns"))
        self.columns_label.setToolTip(
            _("Number of columns of the desired panel")
        )
        grid0.addWidget(self.columns_label, 2, 0)
        grid0.addWidget(self.pcolumns, 2, 1)

        # ## Rows
        self.prows = FCSpinner()
        self.prows.set_range(1, 1000)
        self.prows.set_step(1)

        self.rows_label = QtWidgets.QLabel('%s:' % _("Rows"))
        self.rows_label.setToolTip(
            _("Number of rows of the desired panel")
        )
        grid0.addWidget(self.rows_label, 3, 0)
        grid0.addWidget(self.prows, 3, 1)

        # ## Type of resulting Panel object
        self.panel_type_radio = RadioSet([{'label': _('Gerber'), 'value': 'gerber'},
                                          {'label': _('Geo'), 'value': 'geometry'}])
        self.panel_type_label = QtWidgets.QLabel('%s:' % _("Panel Type"))
        self.panel_type_label.setToolTip(
           _("Choose the type of object for the panel object:\n"
             "- Gerber\n"
             "- Geometry")
        )

        grid0.addWidget(self.panel_type_label, 4, 0)
        grid0.addWidget(self.panel_type_radio, 4, 1)

        # Path optimization
        self.poptimization_cb = FCCheckBox('%s' % _("Path Optimization"))
        self.poptimization_cb.setToolTip(
            _("Active only for Geometry panel type.\n"
              "When checked the application will find\n"
              "any two overlapping Line elements in the panel\n"
              "and will remove the overlapping parts, keeping only one of them.")
        )
        grid0.addWidget(self.poptimization_cb, 5, 0, 1, 2)

        # ## Constrains
        self.pconstrain_cb = FCCheckBox('%s:' % _("Constrain within"))
        self.pconstrain_cb.setToolTip(
            _("Area define by DX and DY within to constrain the panel.\n"
              "DX and DY values are in current units.\n"
              "Regardless of how many columns and rows are desired,\n"
              "the final panel will have as many columns and rows as\n"
              "they fit completely within selected area.")
        )
        grid0.addWidget(self.pconstrain_cb, 10, 0, 1, 2)

        self.px_width_entry = FCDoubleSpinner()
        self.px_width_entry.set_range(0.000001, 10000.0000)
        self.px_width_entry.set_precision(self.decimals)
        self.px_width_entry.setSingleStep(0.1)

        self.x_width_lbl = QtWidgets.QLabel('%s:' % _("Width (DX)"))
        self.x_width_lbl.setToolTip(
            _("The width (DX) within which the panel must fit.\n"
              "In current units.")
        )
        grid0.addWidget(self.x_width_lbl, 12, 0)
        grid0.addWidget(self.px_width_entry, 12, 1)

        self.py_height_entry = FCDoubleSpinner()
        self.py_height_entry.set_range(0.000001, 10000.0000)
        self.py_height_entry.set_precision(self.decimals)
        self.py_height_entry.setSingleStep(0.1)

        self.y_height_lbl = QtWidgets.QLabel('%s:' % _("Height (DY)"))
        self.y_height_lbl.setToolTip(
            _("The height (DY)within which the panel must fit.\n"
              "In current units.")
        )
        grid0.addWidget(self.y_height_lbl, 17, 0)
        grid0.addWidget(self.py_height_entry, 17, 1)

        self.layout.addStretch()
