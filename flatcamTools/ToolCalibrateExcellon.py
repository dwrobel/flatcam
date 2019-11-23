# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtCore

from FlatCAMTool import FlatCAMTool
from flatcamGUI.GUIElements import FCDoubleSpinner, EvalEntry, FCCheckBox, OptionalInputSection, FCTable

from shapely.geometry import Point
from shapely.geometry.base import *

import math
from datetime import datetime
import logging

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class ToolCalibrateExcellon(FlatCAMTool):

    toolName = _("Calibrate Excellon")

    def __init__(self, app):
        FlatCAMTool.__init__(self, app)

        self.app = app
        self.canvas = self.app.plotcanvas

        self.decimals = 4

        # ## Title
        title_label = QtWidgets.QLabel("%s" % self.toolName)
        title_label.setStyleSheet("""
                        QLabel
                        {
                            font-size: 16px;
                            font-weight: bold;
                        }
                        """)
        self.layout.addWidget(title_label)

        # ## Grid Layout
        i_grid_lay = QtWidgets.QGridLayout()
        self.layout.addLayout(i_grid_lay)
        i_grid_lay.setColumnStretch(0, 0)
        i_grid_lay.setColumnStretch(1, 1)
        i_grid_lay.setColumnStretch(2, 1)

        self.exc_object_combo = QtWidgets.QComboBox()
        self.exc_object_combo.setModel(self.app.collection)
        self.exc_object_combo.setRootModelIndex(self.app.collection.index(1, 0, QtCore.QModelIndex()))
        self.exc_object_combo.setCurrentIndex(1)

        self.excobj_label = QtWidgets.QLabel("<b>%s:</b>" % _("EXCELLON"))
        self.excobj_label.setToolTip(
            _("Excellon Object to be used as a source for reference points.")
        )

        i_grid_lay.addWidget(self.excobj_label, 0, 0)
        i_grid_lay.addWidget(self.exc_object_combo, 0, 1, 1, 2)
        i_grid_lay.addWidget(QtWidgets.QLabel(''), 1, 0)

        self.gcode_title_label = QtWidgets.QLabel('<b>%s</b>' % _('GCode Parameters'))
        self.gcode_title_label.setToolTip(
            _("Parameters used when creating the GCode in this tool.")
        )
        i_grid_lay.addWidget(self.gcode_title_label, 1, 0, 1, 3)

        # Travel Z entry
        travelz_lbl = QtWidgets.QLabel('%s:' % _("Travel Z"))
        travelz_lbl.setToolTip(
            _("Height (Z) for travelling between the points.")
        )

        self.travelz_entry = FCDoubleSpinner()
        self.travelz_entry.set_range(-9999.9999, 9999.9999)
        self.travelz_entry.set_precision(self.decimals)
        self.travelz_entry.setSingleStep(0.1)

        i_grid_lay.addWidget(travelz_lbl, 2, 0)
        i_grid_lay.addWidget(self.travelz_entry, 2, 1, 1, 2)

        # Verification Z entry
        verz_lbl = QtWidgets.QLabel('%s:' % _("Verification Z"))
        verz_lbl.setToolTip(
            _("Height (Z) for checking the point.")
        )

        self.verz_entry = FCDoubleSpinner()
        self.verz_entry.set_range(-9999.9999, 9999.9999)
        self.verz_entry.set_precision(self.decimals)
        self.verz_entry.setSingleStep(0.1)

        i_grid_lay.addWidget(verz_lbl, 3, 0)
        i_grid_lay.addWidget(self.verz_entry, 3, 1, 1, 2)

        # Zero the Z of the verification tool
        self.zeroz_cb = FCCheckBox('%s' % _("Zero Z tool"))
        self.zeroz_cb.setToolTip(
            _("Include a sequence to zero the height (Z)\n"
              "of the verification tool.")
        )

        i_grid_lay.addWidget(self.zeroz_cb, 4, 0, 1, 3)

        # Toochange Z entry
        toolchangez_lbl = QtWidgets.QLabel('%s:' % _("Toolchange Z"))
        toolchangez_lbl.setToolTip(
            _("Height (Z) for mounting the verification probe.")
        )

        self.toolchangez_entry = FCDoubleSpinner()
        self.toolchangez_entry.set_range(0.0000, 9999.9999)
        self.toolchangez_entry.set_precision(self.decimals)
        self.toolchangez_entry.setSingleStep(0.1)

        i_grid_lay.addWidget(toolchangez_lbl, 5, 0)
        i_grid_lay.addWidget(self.toolchangez_entry, 5, 1, 1, 2)

        self.z_ois = OptionalInputSection(self.zeroz_cb, [toolchangez_lbl, self.toolchangez_entry])

        i_grid_lay.addWidget(QtWidgets.QLabel(''), 6, 0, 1, 3)

        # ## Grid Layout
        grid_lay = QtWidgets.QGridLayout()
        self.layout.addLayout(grid_lay)
        grid_lay.setColumnStretch(0, 0)
        grid_lay.setColumnStretch(1, 1)
        grid_lay.setColumnStretch(2, 1)

        self.points_table_label = QtWidgets.QLabel('<b>%s</b>' % _('Calibration Points'))
        self.points_table_label.setToolTip(
            _("Contain the expected calibration points and the\n"
              "ones measured.")
        )
        grid_lay.addWidget(self.points_table_label, 1, 0, 1, 3)

        self.points_table = FCTable()
        self.points_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        # self.points_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        grid_lay.addWidget(self.points_table, 2, 0, 9, 3)

        self.points_table.setColumnCount(4)
        self.points_table.setHorizontalHeaderLabels(
            [
                '#',
                _("Name"),
                _("Target"),
                _("Found Delta")
            ]
        )
        self.points_table.setRowCount(8)
        row = 0

        # BOTTOM LEFT
        id_item_1 = QtWidgets.QTableWidgetItem('%d' % 1)
        flags = QtCore.Qt.ItemIsEnabled
        id_item_1.setFlags(flags)
        self.points_table.setItem(row, 0, id_item_1)  # Tool name/id

        self.bottom_left_coordx_lbl = QtWidgets.QLabel('%s' % _('Bot Left X'))
        self.points_table.setCellWidget(row, 1, self.bottom_left_coordx_lbl)
        self.bottom_left_coordx_tgt = EvalEntry()
        self.points_table.setCellWidget(row, 2, self.bottom_left_coordx_tgt)
        self.bottom_left_coordx_tgt.setReadOnly(True)
        self.bottom_left_coordx_found = EvalEntry()
        self.points_table.setCellWidget(row, 3, self.bottom_left_coordx_found)
        row += 1

        self.bottom_left_coordy_lbl = QtWidgets.QLabel('%s' % _('Bot Left Y'))
        self.points_table.setCellWidget(row, 1, self.bottom_left_coordy_lbl)
        self.bottom_left_coordy_tgt = EvalEntry()
        self.points_table.setCellWidget(row, 2, self.bottom_left_coordy_tgt)
        self.bottom_left_coordy_tgt.setReadOnly(True)
        self.bottom_left_coordy_found = EvalEntry()
        self.points_table.setCellWidget(row, 3, self.bottom_left_coordy_found)

        self.bottom_left_coordx_found.set_value(_("Origin"))
        self.bottom_left_coordy_found.set_value(_("Origin"))
        self.bottom_left_coordx_found.setDisabled(True)
        self.bottom_left_coordy_found.setDisabled(True)
        row += 1

        # BOTTOM RIGHT
        id_item_2 = QtWidgets.QTableWidgetItem('%d' % 2)
        flags = QtCore.Qt.ItemIsEnabled
        id_item_2.setFlags(flags)
        self.points_table.setItem(row, 0, id_item_2)  # Tool name/id

        self.bottom_right_coordx_lbl = QtWidgets.QLabel('%s' % _('Bot Right X'))
        self.points_table.setCellWidget(row, 1, self.bottom_right_coordx_lbl)
        self.bottom_right_coordx_tgt = EvalEntry()
        self.points_table.setCellWidget(row, 2, self.bottom_right_coordx_tgt)
        self.bottom_right_coordx_tgt.setReadOnly(True)
        self.bottom_right_coordx_found = EvalEntry()
        self.points_table.setCellWidget(row, 3, self.bottom_right_coordx_found)

        row += 1

        self.bottom_right_coordy_lbl = QtWidgets.QLabel('%s' % _('Bot Right Y'))
        self.points_table.setCellWidget(row, 1, self.bottom_right_coordy_lbl)
        self.bottom_right_coordy_tgt = EvalEntry()
        self.points_table.setCellWidget(row, 2, self.bottom_right_coordy_tgt)
        self.bottom_right_coordy_tgt.setReadOnly(True)
        self.bottom_right_coordy_found = EvalEntry()
        self.points_table.setCellWidget(row, 3, self.bottom_right_coordy_found)
        row += 1

        # TOP LEFT
        id_item_3 = QtWidgets.QTableWidgetItem('%d' % 3)
        flags = QtCore.Qt.ItemIsEnabled
        id_item_3.setFlags(flags)
        self.points_table.setItem(row, 0, id_item_3)  # Tool name/id

        self.top_left_coordx_lbl = QtWidgets.QLabel('%s' % _('Top Left X'))
        self.points_table.setCellWidget(row, 1, self.top_left_coordx_lbl)
        self.top_left_coordx_tgt = EvalEntry()
        self.points_table.setCellWidget(row, 2, self.top_left_coordx_tgt)
        self.top_left_coordx_tgt.setReadOnly(True)
        self.top_left_coordx_found = EvalEntry()
        self.points_table.setCellWidget(row, 3, self.top_left_coordx_found)
        row += 1

        self.top_left_coordy_lbl = QtWidgets.QLabel('%s' % _('Top Left Y'))
        self.points_table.setCellWidget(row, 1, self.top_left_coordy_lbl)
        self.top_left_coordy_tgt = EvalEntry()
        self.points_table.setCellWidget(row, 2, self.top_left_coordy_tgt)
        self.top_left_coordy_tgt.setReadOnly(True)
        self.top_left_coordy_found = EvalEntry()
        self.points_table.setCellWidget(row, 3, self.top_left_coordy_found)
        row += 1

        # TOP RIGHT
        id_item_4 = QtWidgets.QTableWidgetItem('%d' % 4)
        flags = QtCore.Qt.ItemIsEnabled
        id_item_4.setFlags(flags)
        self.points_table.setItem(row, 0, id_item_4)  # Tool name/id

        self.top_right_coordx_lbl = QtWidgets.QLabel('%s' % _('Top Right X'))
        self.points_table.setCellWidget(row, 1, self.top_right_coordx_lbl)
        self.top_right_coordx_tgt = EvalEntry()
        self.points_table.setCellWidget(row, 2, self.top_right_coordx_tgt)
        self.top_right_coordx_tgt.setReadOnly(True)
        self.top_right_coordx_found = EvalEntry()
        self.points_table.setCellWidget(row, 3, self.top_right_coordx_found)
        row += 1

        self.top_right_coordy_lbl = QtWidgets.QLabel('%s' % _('Top Right Y'))
        self.points_table.setCellWidget(row, 1, self.top_right_coordy_lbl)
        self.top_right_coordy_tgt = EvalEntry()
        self.points_table.setCellWidget(row, 2, self.top_right_coordy_tgt)
        self.top_right_coordy_tgt.setReadOnly(True)
        self.top_right_coordy_found = EvalEntry()
        self.points_table.setCellWidget(row, 3, self.top_right_coordy_found)

        vertical_header = self.points_table.verticalHeader()
        vertical_header.hide()
        self.points_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        horizontal_header = self.points_table.horizontalHeader()
        horizontal_header.setMinimumSectionSize(10)
        horizontal_header.setDefaultSectionSize(70)

        self.points_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        # for x in range(4):
        #     self.points_table.resizeColumnToContents(x)
        self.points_table.resizeColumnsToContents()
        self.points_table.resizeRowsToContents()

        horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(0, 20)
        horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        horizontal_header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        horizontal_header.setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)

        self.points_table.setMinimumHeight(self.points_table.getHeight() + 2)
        self.points_table.setMaximumHeight(self.points_table.getHeight() + 3)

        # # BOTTOM LEFT
        # self.bottom_left_lbl = QtWidgets.QLabel('<b>%s</b>' % _('Bottom Left'))
        # grid_lay.addWidget(self.bottom_left_lbl, 3, 0)
        # self.bottom_left_tgt_lbl = QtWidgets.QLabel('%s' % _('Target'))
        # grid_lay.addWidget(self.bottom_left_tgt_lbl, 3, 1)
        # self.bottom_left_found_lbl = QtWidgets.QLabel('%s' % _('Cal. Origin'))
        # grid_lay.addWidget(self.bottom_left_found_lbl, 3, 2)
        #
        # self.bottom_left_coordx_lbl = QtWidgets.QLabel('%s' % _('X'))
        # grid_lay.addWidget(self.bottom_left_coordx_lbl, 4, 0)
        # self.bottom_left_coordx_tgt = EvalEntry()
        # self.bottom_left_coordx_tgt.setReadOnly(True)
        # grid_lay.addWidget(self.bottom_left_coordx_tgt, 4, 1)
        # self.bottom_left_coordx_found = EvalEntry()
        # grid_lay.addWidget(self.bottom_left_coordx_found, 4, 2)
        #
        # self.bottom_left_coordy_lbl = QtWidgets.QLabel('%s' % _('Y'))
        # grid_lay.addWidget(self.bottom_left_coordy_lbl, 5, 0)
        # self.bottom_left_coordy_tgt = EvalEntry()
        # self.bottom_left_coordy_tgt.setReadOnly(True)
        # grid_lay.addWidget(self.bottom_left_coordy_tgt, 5, 1)
        # self.bottom_left_coordy_found = EvalEntry()
        # grid_lay.addWidget(self.bottom_left_coordy_found, 5, 2)
        #
        # self.bottom_left_coordx_found.set_value(_('Set Origin'))
        # self.bottom_left_coordy_found.set_value(_('Set Origin'))
        # self.bottom_left_coordx_found.setDisabled(True)
        # self.bottom_left_coordy_found.setDisabled(True)
        #
        # # BOTTOM RIGHT
        # self.bottom_right_lbl = QtWidgets.QLabel('<b>%s</b>' % _('Bottom Right'))
        # grid_lay.addWidget(self.bottom_right_lbl, 6, 0)
        # self.bottom_right_tgt_lbl = QtWidgets.QLabel('%s' % _('Target'))
        # grid_lay.addWidget(self.bottom_right_tgt_lbl, 6, 1)
        # self.bottom_right_found_lbl = QtWidgets.QLabel('%s' % _('Found Delta'))
        # grid_lay.addWidget(self.bottom_right_found_lbl, 6, 2)
        #
        # self.bottom_right_coordx_lbl = QtWidgets.QLabel('%s' % _('X'))
        # grid_lay.addWidget(self.bottom_right_coordx_lbl, 7, 0)
        # self.bottom_right_coordx_tgt = EvalEntry()
        # self.bottom_right_coordx_tgt.setReadOnly(True)
        # grid_lay.addWidget(self.bottom_right_coordx_tgt, 7, 1)
        # self.bottom_right_coordx_found = EvalEntry()
        # grid_lay.addWidget(self.bottom_right_coordx_found, 7, 2)
        #
        # self.bottom_right_coordy_lbl = QtWidgets.QLabel('%s' % _('Y'))
        # grid_lay.addWidget(self.bottom_right_coordy_lbl, 8, 0)
        # self.bottom_right_coordy_tgt = EvalEntry()
        # self.bottom_right_coordy_tgt.setReadOnly(True)
        # grid_lay.addWidget(self.bottom_right_coordy_tgt, 8, 1)
        # self.bottom_right_coordy_found = EvalEntry()
        # grid_lay.addWidget(self.bottom_right_coordy_found, 8, 2)
        #
        # # TOP LEFT
        # self.top_left_lbl = QtWidgets.QLabel('<b>%s</b>' % _('Top Left'))
        # grid_lay.addWidget(self.top_left_lbl, 9, 0)
        # self.top_left_tgt_lbl = QtWidgets.QLabel('%s' % _('Target'))
        # grid_lay.addWidget(self.top_left_tgt_lbl, 9, 1)
        # self.top_left_found_lbl = QtWidgets.QLabel('%s' % _('Found Delta'))
        # grid_lay.addWidget(self.top_left_found_lbl, 9, 2)
        #
        # self.top_left_coordx_lbl = QtWidgets.QLabel('%s' % _('X'))
        # grid_lay.addWidget(self.top_left_coordx_lbl, 10, 0)
        # self.top_left_coordx_tgt = EvalEntry()
        # self.top_left_coordx_tgt.setReadOnly(True)
        # grid_lay.addWidget(self.top_left_coordx_tgt, 10, 1)
        # self.top_left_coordx_found = EvalEntry()
        # grid_lay.addWidget(self.top_left_coordx_found, 10, 2)
        #
        # self.top_left_coordy_lbl = QtWidgets.QLabel('%s' % _('Y'))
        # grid_lay.addWidget(self.top_left_coordy_lbl, 11, 0)
        # self.top_left_coordy_tgt = EvalEntry()
        # self.top_left_coordy_tgt.setReadOnly(True)
        # grid_lay.addWidget(self.top_left_coordy_tgt, 11, 1)
        # self.top_left_coordy_found = EvalEntry()
        # grid_lay.addWidget(self.top_left_coordy_found, 11, 2)
        #
        # # TOP RIGHT
        # self.top_right_lbl = QtWidgets.QLabel('<b>%s</b>' % _('Top Right'))
        # grid_lay.addWidget(self.top_right_lbl, 12, 0)
        # self.top_right_tgt_lbl = QtWidgets.QLabel('%s' % _('Target'))
        # grid_lay.addWidget(self.top_right_tgt_lbl, 12, 1)
        # self.top_right_found_lbl = QtWidgets.QLabel('%s' % _('Found Delta'))
        # grid_lay.addWidget(self.top_right_found_lbl, 12, 2)
        #
        # self.top_right_coordx_lbl = QtWidgets.QLabel('%s' % _('X'))
        # grid_lay.addWidget(self.top_right_coordx_lbl, 13, 0)
        # self.top_right_coordx_tgt = EvalEntry()
        # self.top_right_coordx_tgt.setReadOnly(True)
        # grid_lay.addWidget(self.top_right_coordx_tgt, 13, 1)
        # self.top_right_coordx_found = EvalEntry()
        # grid_lay.addWidget(self.top_right_coordx_found, 13, 2)
        #
        # self.top_right_coordy_lbl = QtWidgets.QLabel('%s' % _('Y'))
        # grid_lay.addWidget(self.top_right_coordy_lbl, 14, 0)
        # self.top_right_coordy_tgt = EvalEntry()
        # self.top_right_coordy_tgt.setReadOnly(True)
        # grid_lay.addWidget(self.top_right_coordy_tgt, 14, 1)
        # self.top_right_coordy_found = EvalEntry()
        # grid_lay.addWidget(self.top_right_coordy_found, 14, 2)

        # STEP 1 #
        step_1 = QtWidgets.QLabel('<b>%s</b>' % _("STEP 1"))
        step_1.setToolTip(
            _("Pick four points by clicking inside the drill holes.\n"
              "Those four points should be in the four\n"
              "(as much as possible) corners of the Excellon object.")
        )
        grid_lay.addWidget(step_1, 15, 0, 1, 3)

        # ## Start Button
        self.start_button = QtWidgets.QPushButton(_("Acquire Calibration Points"))
        self.start_button.setToolTip(
            _("Pick four points by clicking inside the drill holes.\n"
              "Those four points should be in the four squares of\n"
              "the Excellon object.")
        )

        grid_lay.addWidget(self.start_button, 16, 0, 1, 3)

        # STEP 2 #
        step_2 = QtWidgets.QLabel('<b>%s</b>' % _("STEP 2"))
        step_2.setToolTip(
            _("Generate GCode file to locate and align the PCB by using\n"
              "the four points acquired above.")
        )
        grid_lay.addWidget(step_2, 17, 0, 1, 3)

        # ## GCode Button
        self.gcode_button = QtWidgets.QPushButton(_("Generate GCode"))
        self.gcode_button.setToolTip(
            _("Generate GCode file to locate and align the PCB by using\n"
              "the four points acquired above.")
        )

        grid_lay.addWidget(self.gcode_button, 18, 0, 1, 3)

        # STEP 3 #
        step_3 = QtWidgets.QLabel('<b>%s</b>' % _("STEP 3"))
        step_3.setToolTip(
            _("Calculate Scale and Skew factors based on the differences (delta)\n"
              "found when checking the PCB pattern. The differences must be filled\n"
              "in the fields Found (Delta).")
        )
        grid_lay.addWidget(step_3, 19, 0, 1, 3)

        # ## Factors Button
        self.generate_factors_button = QtWidgets.QPushButton(_("Calculate Factors"))
        self.generate_factors_button.setToolTip(
            _("Calculate Scale and Skew factors based on the differences (delta)\n"
              "found when checking the PCB pattern. The differences must be filled\n"
              "in the fields Found (Delta).")
        )
        grid_lay.addWidget(self.generate_factors_button, 20, 0, 1, 3)

        scale_lbl = QtWidgets.QLabel('<b>%s</b>' % _("Scale"))
        grid_lay.addWidget(scale_lbl, 21, 0, 1, 3)

        self.scalex_label = QtWidgets.QLabel(_("Factor X:"))
        self.scalex_label.setToolTip(
            _("Factor for Scale action over X axis.")
        )
        self.scalex_entry = FCDoubleSpinner()
        self.scalex_entry.set_range(0, 9999.9999)
        self.scalex_entry.set_precision(self.decimals)
        self.scalex_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.scalex_label, 22, 0)
        grid_lay.addWidget(self.scalex_entry, 22, 1, 1, 2)

        self.scaley_label = QtWidgets.QLabel(_("Factor Y:"))
        self.scaley_label.setToolTip(
            _("Factor for Scale action over Y axis.")
        )
        self.scaley_entry = FCDoubleSpinner()
        self.scaley_entry.set_range(0, 9999.9999)
        self.scaley_entry.set_precision(self.decimals)
        self.scaley_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.scaley_label, 23, 0)
        grid_lay.addWidget(self.scaley_entry, 23, 1, 1, 2)

        self.scale_button = QtWidgets.QPushButton(_("Scale"))
        self.scale_button.setToolTip(
            _("Apply Scale factors on the calibration points.")
        )
        grid_lay.addWidget(self.scale_button, 24, 0, 1, 3)

        skew_lbl = QtWidgets.QLabel('<b>%s</b>' % _("Skew"))
        grid_lay.addWidget(skew_lbl, 25, 0, 1, 3)

        self.skewx_label = QtWidgets.QLabel(_("Angle X:"))
        self.skewx_label.setToolTip(
            _("Angle for Skew action, in degrees.\n"
              "Float number between -360 and 359.")
        )
        self.skewx_entry = FCDoubleSpinner()
        self.skewx_entry.set_range(-360, 360)
        self.skewx_entry.set_precision(self.decimals)
        self.skewx_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.skewx_label, 26, 0)
        grid_lay.addWidget(self.skewx_entry, 26, 1, 1, 2)

        self.skewy_label = QtWidgets.QLabel(_("Angle Y:"))
        self.skewy_label.setToolTip(
            _("Angle for Skew action, in degrees.\n"
              "Float number between -360 and 359.")
        )
        self.skewy_entry = FCDoubleSpinner()
        self.skewy_entry.set_range(-360, 360)
        self.skewy_entry.set_precision(self.decimals)
        self.skewy_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.skewy_label, 27, 0)
        grid_lay.addWidget(self.skewy_entry, 27, 1, 1, 2)

        self.skew_button = QtWidgets.QPushButton(_("Skew"))
        self.skew_button.setToolTip(
            _("Apply Skew factors on the calibration points.")
        )
        grid_lay.addWidget(self.skew_button, 28, 0, 1, 3)

        # STEP 4 #
        step_4 = QtWidgets.QLabel('<b>%s</b>' % _("STEP 4"))
        step_4.setToolTip(
            _("Generate verification GCode file adjusted with\n"
              "the factors above.")
        )
        grid_lay.addWidget(step_4, 29, 0, 1, 3)

        # ## Adjusted GCode Button
        self.adj_gcode_button = QtWidgets.QPushButton(_("Generate Adjusted GCode"))
        self.adj_gcode_button.setToolTip(
            _("Generate verification GCode file adjusted with\n"
              "the factors above.")
        )
        grid_lay.addWidget(self.adj_gcode_button, 30, 0, 1, 3)

        # STEP 5 #
        step_5 = QtWidgets.QLabel('<b>%s</b>' % _("STEP 5"))
        step_5.setToolTip(
            _("Ajust the Excellon and Cutout Geometry objects\n"
              "with the factors determined, and verified, above.")
        )
        grid_lay.addWidget(step_5, 31, 0, 1, 3)

        self.adj_exc_object_combo = QtWidgets.QComboBox()
        self.adj_exc_object_combo.setModel(self.app.collection)
        self.adj_exc_object_combo.setRootModelIndex(self.app.collection.index(1, 0, QtCore.QModelIndex()))
        self.adj_exc_object_combo.setCurrentIndex(1)

        self.adj_excobj_label = QtWidgets.QLabel("<b>%s:</b>" % _("EXCELLON"))
        self.adj_excobj_label.setToolTip(
            _("Excellon Object to be adjusted.")
        )

        grid_lay.addWidget(self.adj_excobj_label, 32, 0)
        grid_lay.addWidget(self.adj_exc_object_combo, 32, 1, 1, 2)

        self.adj_geo_object_combo = QtWidgets.QComboBox()
        self.adj_geo_object_combo.setModel(self.app.collection)
        self.adj_geo_object_combo.setRootModelIndex(self.app.collection.index(2, 0, QtCore.QModelIndex()))
        self.adj_geo_object_combo.setCurrentIndex(1)

        self.adj_geoobj_label = QtWidgets.QLabel("<b>%s:</b>" % _("GEOMETRY"))
        self.adj_geoobj_label.setToolTip(
            _("Geometry Object to be adjusted.")
        )

        grid_lay.addWidget(self.adj_geoobj_label, 33, 0)
        grid_lay.addWidget(self.adj_geo_object_combo, 33, 1, 1, 2)

        # ## Adjust Objects Button
        self.adj_obj_button = QtWidgets.QPushButton(_("Adjust Objects"))
        self.adj_obj_button.setToolTip(
            _("Adjust (scale and/or skew) the objects\n"
              "with the factors determined above.")
        )
        grid_lay.addWidget(self.adj_obj_button, 34, 0, 1, 3)

        grid_lay.addWidget(QtWidgets.QLabel(''), 35, 0)
        self.layout.addStretch()

        self.mr = None
        self.units = ''

        # here store 4 points to be used for calibration
        self.click_points = list()

        # store the status of the grid
        self.grid_status_memory = None

        self.exc_obj = None

        # ## Signals
        self.start_button.clicked.connect(self.on_start_collect_points)
        self.gcode_button.clicked.connect(self.generate_verification_gcode)
        self.generate_factors_button.clicked.connect(self.calculate_factors)

    def run(self, toggle=True):
        self.app.report_usage("ToolCalibrateExcellon()")

        if toggle:
            # if the splitter is hidden, display it, else hide it but only if the current widget is the same
            if self.app.ui.splitter.sizes()[0] == 0:
                self.app.ui.splitter.setSizes([1, 1])
            else:
                try:
                    if self.app.ui.tool_scroll_area.widget().objectName() == self.toolName:
                        # if tab is populated with the tool but it does not have the focus, focus on it
                        if not self.app.ui.notebook.currentWidget() is self.app.ui.tool_tab:
                            # focus on Tool Tab
                            self.app.ui.notebook.setCurrentWidget(self.app.ui.tool_tab)
                        else:
                            self.app.ui.splitter.setSizes([0, 1])
                except AttributeError:
                    pass
        else:
            if self.app.ui.splitter.sizes()[0] == 0:
                self.app.ui.splitter.setSizes([1, 1])

        FlatCAMTool.run(self)

        self.set_tool_ui()

        self.app.ui.notebook.setTabText(2, _("Cal Exc Tool"))

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, shortcut='ALT+E', **kwargs)

    def set_tool_ui(self):
        self.units = self.app.defaults['units'].upper()

        # ## Initialize form
        # self.mm_entry.set_value('%.*f' % (self.decimals, 0))

    def on_start_collect_points(self):
        # disengage the grid snapping since it will be hard to find the drills on grid
        if self.app.ui.grid_snap_btn.isChecked():
            self.grid_status_memory = True
            self.app.ui.grid_snap_btn.trigger()
        else:
            self.grid_status_memory = False

        self.mr = self.canvas.graph_event_connect('mouse_release', self.on_mouse_click_release)

        if self.app.is_legacy is False:
            self.canvas.graph_event_disconnect('mouse_release', self.app.on_mouse_click_release_over_plot)
        else:
            self.canvas.graph_event_disconnect(self.app.mr)

        selection_index = self.exc_object_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.exc_object_combo.rootModelIndex())
        try:
            self.exc_obj = model_index.internalPointer().obj
        except Exception:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Excellon object loaded ..."))
            return

        self.app.inform.emit(_("Click inside the First drill point. Bottom Left..."))

    def on_mouse_click_release(self, event):
        if event.button == 1:
            if self.app.is_legacy is False:
                event_pos = event.pos
            else:
                event_pos = (event.xdata, event.ydata)

            pos_canvas = self.canvas.translate_coords(event_pos)
            click_pt = Point([pos_canvas[0], pos_canvas[1]])

            for tool, tool_dict in self.exc_obj.tools.items():
                for geo in tool_dict['solid_geometry']:
                    if click_pt.within(geo):
                        center_pt = geo.centroid
                        self.click_points.append(
                            (
                                float('%.*f' % (self.decimals, center_pt.x)),
                                float('%.*f' % (self.decimals, center_pt.y))
                            )
                        )
                        self.check_points()

    def check_points(self):
        if len(self.click_points) == 1:
            self.bottom_left_coordx_tgt.set_value(self.click_points[0][0])
            self.bottom_left_coordy_tgt.set_value(self.click_points[0][1])
            self.app.inform.emit(_("Click inside the Second drill point. Bottom Right..."))
        elif len(self.click_points) == 2:
            self.bottom_right_coordx_tgt.set_value(self.click_points[1][0])
            self.bottom_right_coordy_tgt.set_value(self.click_points[1][1])
            self.app.inform.emit(_("Click inside the Third drill point. Top Left..."))
        elif len(self.click_points) == 3:
            self.top_left_coordx_tgt.set_value(self.click_points[2][0])
            self.top_left_coordy_tgt.set_value(self.click_points[2][1])
            self.app.inform.emit(_("Click inside the Fourth drill point. Top Right..."))
        elif len(self.click_points) == 4:
            self.top_right_coordx_tgt.set_value(self.click_points[3][0])
            self.top_right_coordy_tgt.set_value(self.click_points[3][1])
            self.app.inform.emit('[success] %s' % _("Done. All four points have been acquired."))
            self.disconnect_cal_events()

            # restore the Grid snapping if it was active before
            if self.grid_status_memory is True:
                self.app.ui.grid_snap_btn.trigger()

    def gcode_header(self):
        log.debug("ToolCalibrateExcellon.gcode_header()")
        time_str = "{:%A, %d %B %Y at %H:%M}".format(datetime.now())

        gcode = '(G-CODE GENERATED BY FLATCAM v%s - www.flatcam.org - Version Date: %s)\n' % \
                (str(self.app.version), str(self.app.version_date)) + '\n'

        gcode += '(Name: ' + _('Verification GCode') + ')\n'

        gcode += '(Units: ' + self.units.upper() + ')\n' + "\n"
        gcode += '(Created on ' + time_str + ')\n' + '\n'
        gcode += 'G20\n' if self.units.upper() == 'IN' else 'G21\n'
        gcode += 'G90\n'
        gcode += 'G17\n'
        gcode += 'G94\n\n'
        return gcode

    def generate_verification_gcode(self):
        travel_z = '%.*f' % (self.decimals, self.travelz_entry.get_value())
        toolchange_z = '%.*f' % (self.decimals, self.toolchangez_entry.get_value())
        verification_z = '%.*f' % (self.decimals, self.verz_entry.get_value())

        if len(self.click_points) != 4:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled. Four points are needed for GCode generation."))
            return 'fail'

        gcode = self.gcode_header()
        if self.zeroz_cb.get_value():
            gcode += 'M5\n'
            gcode += f'G00 Z{toolchange_z}\n'
            gcode += 'M0\n'
            gcode += 'G01 Z0\n'
            gcode += 'M0\n'
            gcode += f'G00 Z{toolchange_z}\n'
            gcode += 'M0\n'

        gcode += f'G00 Z{travel_z}\n'
        gcode += f'G00 X{self.click_points[0][0]} Y{self.click_points[0][1]}\n'
        gcode += f'G01 Z{verification_z}\n'
        gcode += 'M0\n'

        gcode += f'G00 Z{travel_z}\n'
        gcode += f'G00 X{self.click_points[2][0]} Y{self.click_points[2][1]}\n'
        gcode += f'G01 Z{verification_z}\n'
        gcode += 'M0\n'

        gcode += f'G00 Z{travel_z}\n'
        gcode += f'G00 X{self.click_points[3][0]} Y{self.click_points[3][1]}\n'
        gcode += f'G01 Z{verification_z}\n'
        gcode += 'M0\n'

        gcode += f'G00 Z{travel_z}\n'
        gcode += f'G00 X{self.click_points[1][0]} Y{self.click_points[1][1]}\n'
        gcode += f'G01 Z{verification_z}\n'
        gcode += 'M0\n'

        gcode += f'G00 Z{travel_z}\n'
        gcode += f'G00 X0 Y0\n'
        gcode += f'G00 Z{toolchange_z}\n'

        gcode += 'M2'

        _filter_ = "G-Code Files (*.nc);;All Files (*.*)"

        try:
            dir_file_to_save = self.app.get_last_save_folder() + '/' + 'ver_gcode'
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(
                caption=_("Export Machine Code ..."),
                directory=dir_file_to_save,
                filter=_filter_
            )
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(caption=_("Export Machine Code ..."), filter=_filter_)

        filename = str(filename)

        if filename == '':
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Export Machine Code cancelled ..."))
            return

        with open(filename, 'w') as f:
            f.write(gcode)

    def calculate_factors(self):
        origin_x = self.click_points[0][0]
        origin_y = self.click_points[0][1]

        top_left_x = float('%.*f' % (self.decimals, self.click_points[2][0]))
        top_left_y = float('%.*f' % (self.decimals, self.click_points[2][1]))

        try:
            top_left_dx = float('%.*f' % (self.decimals, self.top_left_coordx_found.get_value()))
        except TypeError:
            top_left_dx = top_left_x

        try:
            top_left_dy = float('%.*f' % (self.decimals, self.top_left_coordy_found.get_value()))
        except TypeError:
            top_left_dy = top_left_y

        top_right_x = float('%.*f' % (self.decimals, self.click_points[3][0]))
        top_right_y = float('%.*f' % (self.decimals, self.click_points[3][1]))

        try:
            top_right_dx = float('%.*f' % (self.decimals, self.top_right_coordx_found.get_value()))
        except TypeError:
            top_right_dx = top_right_x

        try:
            top_right_dy = float('%.*f' % (self.decimals, self.top_right_coordy_found.get_value()))
        except TypeError:
            top_right_dy = top_right_y

        bot_right_x = float('%.*f' % (self.decimals, self.click_points[1][0]))
        bot_right_y = float('%.*f' % (self.decimals, self.click_points[1][1]))

        try:
            bot_right_dx = float('%.*f' % (self.decimals, self.bottom_right_coordx_found.get_value()))
        except TypeError:
            bot_right_dx = bot_right_x

        try:
            bot_right_dy = float('%.*f' % (self.decimals, self.bottom_right_coordy_found.get_value()))
        except TypeError:
            bot_right_dy = bot_right_y

        # ------------------------------------------------------------------------------- #
        # --------------------------- FACTORS CALCULUS ---------------------------------- #
        # ------------------------------------------------------------------------------- #
        if top_left_dy != float('%.*f' % (self.decimals, 0.0)):
            # we have scale on Y
            scale_y = (top_left_dy + top_left_y - origin_y) / (top_left_y - origin_y)
            self.scaley_entry.set_value(scale_y)

        if top_left_dx != float('%.*f' % (self.decimals, 0.0)):
            # we have skew on X
            dx = top_left_dx
            dy = top_left_y - origin_y
            skew_angle_x = math.degrees(math.atan(dx / dy))

            self.skewx_entrx.set_value(skew_angle_x)

        if bot_right_dx != float('%.*f' % (self.decimals, 0.0)):
            # we have scale on X
            scale_x = (bot_right_dx + bot_right_x - origin_x) / (bot_right_x - origin_x)
            self.scalex_entry.set_value(scale_x)

        if bot_right_dy != float('%.*f' % (self.decimals, 0.0)):
            # we have skew on Y
            dx = bot_right_x - origin_x
            dy = bot_right_dy + origin_y
            skew_angle_y = math.degrees(math.atan(dy / dx))

            self.skewy_entry.set_value(skew_angle_y)

    def disconnect_cal_events(self):
        self.app.mr = self.canvas.graph_event_connect('mouse_release', self.app.on_mouse_click_release_over_plot)

        if self.app.is_legacy is False:
            self.canvas.graph_event_disconnect('mouse_release', self.on_mouse_click_release)
        else:
            self.canvas.graph_event_disconnect(self.mr)

    def reset_fields(self):
        self.exc_object_combo.setRootModelIndex(self.app.collection.index(1, 0, QtCore.QModelIndex()))

# end of file
