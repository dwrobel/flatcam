# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtCore, QtGui

from FlatCAMTool import FlatCAMTool
from flatcamGUI.GUIElements import FCDoubleSpinner, EvalEntry, FCCheckBox, OptionalInputSection
from flatcamGUI.GUIElements import FCTable, FCComboBox, RadioSet
from flatcamEditors.FlatCAMTextEditor import TextEditor

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


class ToolCalibration(FlatCAMTool):

    toolName = _("Calibration Tool")

    def __init__(self, app):
        FlatCAMTool.__init__(self, app)

        self.app = app
        self.canvas = self.app.plotcanvas

        self.decimals = self.app.decimals

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

        self.layout.addWidget(QtWidgets.QLabel(''))

        # ## Grid Layout
        grid_lay = QtWidgets.QGridLayout()
        self.layout.addLayout(grid_lay)
        grid_lay.setColumnStretch(0, 0)
        grid_lay.setColumnStretch(1, 1)
        grid_lay.setColumnStretch(2, 0)

        step_1 = QtWidgets.QLabel('<b>%s</b>' % _("STEP 1: Acquire Calibration Points"))
        step_1.setToolTip(
            _("Pick four points by clicking inside the drill holes.\n"
              "Those four points should be in the four\n"
              "(as much as possible) corners of the Excellon object.")
        )
        grid_lay.addWidget(step_1, 0, 0, 1, 3)

        self.cal_source_lbl = QtWidgets.QLabel("<b>%s:</b>" % _("Source Type"))
        self.cal_source_lbl.setToolTip(_("The source of calibration points.\n"
                                         "It can be:\n"
                                         "- Object -> click a hole geo for Excellon or a pad for Gerber\n"
                                         "- Free -> click freely on canvas to acquire the calibration points"))
        self.cal_source_radio = RadioSet([{'label': _('Object'), 'value': 'object'},
                                          {'label': _('Free'), 'value': 'free'}],
                                         stretch=False)

        grid_lay.addWidget(self.cal_source_lbl, 1, 0)
        grid_lay.addWidget(self.cal_source_radio, 1, 1, 1, 2)

        self.obj_type_label = QtWidgets.QLabel("%s:" % _("Object Type"))

        self.obj_type_combo = FCComboBox()
        self.obj_type_combo.addItem(_("Gerber"))
        self.obj_type_combo.addItem(_("Excellon"))
        self.obj_type_combo.setCurrentIndex(1)

        grid_lay.addWidget(self.obj_type_label, 2, 0)
        grid_lay.addWidget(self.obj_type_combo, 2, 1, 1, 2)

        self.object_combo = FCComboBox()
        self.object_combo.setModel(self.app.collection)
        self.object_combo.setRootModelIndex(self.app.collection.index(1, 0, QtCore.QModelIndex()))
        self.object_combo.setCurrentIndex(1)

        self.object_label = QtWidgets.QLabel("%s:" % _("Source object selection"))
        self.object_label.setToolTip(
            _("FlatCAM Object to be used as a source for reference points.")
        )

        grid_lay.addWidget(self.object_label, 3, 0, 1, 3)
        grid_lay.addWidget(self.object_combo, 4, 0, 1, 3)

        self.points_table_label = QtWidgets.QLabel('<b>%s</b>' % _('Calibration Points'))
        self.points_table_label.setToolTip(
            _("Contain the expected calibration points and the\n"
              "ones measured.")
        )
        grid_lay.addWidget(self.points_table_label, 5, 0, 1, 3)

        self.points_table = FCTable()
        self.points_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        # self.points_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        grid_lay.addWidget(self.points_table, 6, 0, 1, 3)

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

        # ## Get Points Button
        self.start_button = QtWidgets.QPushButton(_("Get Points"))
        self.start_button.setToolTip(
            _("Pick four points by clicking on canvas if the source choice\n"
              "is 'free' or inside the object geometry if the source is 'object'.\n"
              "Those four points should be in the four squares of\n"
              "the object.")
        )
        self.start_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)
        grid_lay.addWidget(self.start_button, 7, 0, 1, 3)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line, 8, 0, 1, 3)

        grid_lay.addWidget(QtWidgets.QLabel(''), 9, 0)

        # STEP 2 #
        step_2 = QtWidgets.QLabel('<b>%s</b>' % _("STEP 2: Verification GCode"))
        step_2.setToolTip(
            _("Generate GCode file to locate and align the PCB by using\n"
              "the four points acquired above.")
        )
        grid_lay.addWidget(step_2, 10, 0, 1, 3)

        self.gcode_title_label = QtWidgets.QLabel('<b>%s</b>' % _('GCode Parameters'))
        self.gcode_title_label.setToolTip(
            _("Parameters used when creating the GCode in this tool.")
        )
        grid_lay.addWidget(self.gcode_title_label, 11, 0, 1, 3)

        # Travel Z entry
        travelz_lbl = QtWidgets.QLabel('%s:' % _("Travel Z"))
        travelz_lbl.setToolTip(
            _("Height (Z) for travelling between the points.")
        )

        self.travelz_entry = FCDoubleSpinner()
        self.travelz_entry.set_range(-9999.9999, 9999.9999)
        self.travelz_entry.set_precision(self.decimals)
        self.travelz_entry.setSingleStep(0.1)

        grid_lay.addWidget(travelz_lbl, 12, 0)
        grid_lay.addWidget(self.travelz_entry, 12, 1, 1, 2)

        # Verification Z entry
        verz_lbl = QtWidgets.QLabel('%s:' % _("Verification Z"))
        verz_lbl.setToolTip(
            _("Height (Z) for checking the point.")
        )

        self.verz_entry = FCDoubleSpinner()
        self.verz_entry.set_range(-9999.9999, 9999.9999)
        self.verz_entry.set_precision(self.decimals)
        self.verz_entry.setSingleStep(0.1)

        grid_lay.addWidget(verz_lbl, 13, 0)
        grid_lay.addWidget(self.verz_entry, 13, 1, 1, 2)

        # Zero the Z of the verification tool
        self.zeroz_cb = FCCheckBox('%s' % _("Zero Z tool"))
        self.zeroz_cb.setToolTip(
            _("Include a sequence to zero the height (Z)\n"
              "of the verification tool.")
        )

        grid_lay.addWidget(self.zeroz_cb, 14, 0, 1, 3)

        # Toochange Z entry
        toolchangez_lbl = QtWidgets.QLabel('%s:' % _("Toolchange Z"))
        toolchangez_lbl.setToolTip(
            _("Height (Z) for mounting the verification probe.")
        )

        self.toolchangez_entry = FCDoubleSpinner()
        self.toolchangez_entry.set_range(0.0000, 9999.9999)
        self.toolchangez_entry.set_precision(self.decimals)
        self.toolchangez_entry.setSingleStep(0.1)

        grid_lay.addWidget(toolchangez_lbl, 15, 0)
        grid_lay.addWidget(self.toolchangez_entry, 15, 1, 1, 2)

        self.z_ois = OptionalInputSection(self.zeroz_cb, [toolchangez_lbl, self.toolchangez_entry])

        # ## GCode Button
        self.gcode_button = QtWidgets.QPushButton(_("Generate GCode"))
        self.gcode_button.setToolTip(
            _("Generate GCode file to locate and align the PCB by using\n"
              "the four points acquired above.")
        )
        self.gcode_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)
        grid_lay.addWidget(self.gcode_button, 16, 0, 1, 3)

        separator_line1 = QtWidgets.QFrame()
        separator_line1.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line1.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line1, 17, 0, 1, 3)

        grid_lay.addWidget(QtWidgets.QLabel(''), 18, 0, 1, 3)

        # STEP 3 #
        step_3 = QtWidgets.QLabel('<b>%s</b>' % _("STEP 3: Adjustments"))
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
        self.generate_factors_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)
        grid_lay.addWidget(self.generate_factors_button, 20, 0, 1, 3)

        self.scalex_label = QtWidgets.QLabel(_("Scale Factor X:"))
        self.scalex_label.setToolTip(
            _("Factor for Scale action over X axis.")
        )
        self.scalex_entry = FCDoubleSpinner()
        self.scalex_entry.set_range(0, 9999.9999)
        self.scalex_entry.set_precision(self.decimals)
        self.scalex_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.scalex_label, 21, 0)
        grid_lay.addWidget(self.scalex_entry, 21, 1, 1, 2)

        self.scaley_label = QtWidgets.QLabel(_("Scale Factor Y:"))
        self.scaley_label.setToolTip(
            _("Factor for Scale action over Y axis.")
        )
        self.scaley_entry = FCDoubleSpinner()
        self.scaley_entry.set_range(0, 9999.9999)
        self.scaley_entry.set_precision(self.decimals)
        self.scaley_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.scaley_label, 22, 0)
        grid_lay.addWidget(self.scaley_entry, 22, 1, 1, 2)

        self.scale_button = QtWidgets.QPushButton(_("Apply Scale Factors"))
        self.scale_button.setToolTip(
            _("Apply Scale factors on the calibration points.")
        )
        self.scale_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)
        grid_lay.addWidget(self.scale_button, 23, 0, 1, 3)

        self.skewx_label = QtWidgets.QLabel(_("Skew Angle X:"))
        self.skewx_label.setToolTip(
            _("Angle for Skew action, in degrees.\n"
              "Float number between -360 and 359.")
        )
        self.skewx_entry = FCDoubleSpinner()
        self.skewx_entry.set_range(-360, 360)
        self.skewx_entry.set_precision(self.decimals)
        self.skewx_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.skewx_label, 24, 0)
        grid_lay.addWidget(self.skewx_entry, 24, 1, 1, 2)

        self.skewy_label = QtWidgets.QLabel(_("Skew Angle Y:"))
        self.skewy_label.setToolTip(
            _("Angle for Skew action, in degrees.\n"
              "Float number between -360 and 359.")
        )
        self.skewy_entry = FCDoubleSpinner()
        self.skewy_entry.set_range(-360, 360)
        self.skewy_entry.set_precision(self.decimals)
        self.skewy_entry.setSingleStep(0.1)

        grid_lay.addWidget(self.skewy_label, 25, 0)
        grid_lay.addWidget(self.skewy_entry, 25, 1, 1, 2)

        self.skew_button = QtWidgets.QPushButton(_("Apply Skew Factors"))
        self.skew_button.setToolTip(
            _("Apply Skew factors on the calibration points.")
        )
        self.skew_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)
        grid_lay.addWidget(self.skew_button, 26, 0, 1, 3)

        # final_factors_lbl = QtWidgets.QLabel('<b>%s</b>' % _("Final Factors"))
        # final_factors_lbl.setToolTip(
        #     _("Generate verification GCode file adjusted with\n"
        #       "the factors above.")
        # )
        # grid_lay.addWidget(final_factors_lbl, 27, 0, 1, 3)
        #
        # self.fin_scalex_label = QtWidgets.QLabel(_("Scale Factor X:"))
        # self.fin_scalex_label.setToolTip(
        #     _("Final factor for Scale action over X axis.")
        # )
        # self.fin_scalex_entry = FCDoubleSpinner()
        # self.fin_scalex_entry.set_range(0, 9999.9999)
        # self.fin_scalex_entry.set_precision(self.decimals)
        # self.fin_scalex_entry.setSingleStep(0.1)
        #
        # grid_lay.addWidget(self.fin_scalex_label, 28, 0)
        # grid_lay.addWidget(self.fin_scalex_entry, 28, 1, 1, 2)
        #
        # self.fin_scaley_label = QtWidgets.QLabel(_("Scale Factor Y:"))
        # self.fin_scaley_label.setToolTip(
        #     _("Final factor for Scale action over Y axis.")
        # )
        # self.fin_scaley_entry = FCDoubleSpinner()
        # self.fin_scaley_entry.set_range(0, 9999.9999)
        # self.fin_scaley_entry.set_precision(self.decimals)
        # self.fin_scaley_entry.setSingleStep(0.1)
        #
        # grid_lay.addWidget(self.fin_scaley_label, 29, 0)
        # grid_lay.addWidget(self.fin_scaley_entry, 29, 1, 1, 2)
        #
        # self.fin_skewx_label = QtWidgets.QLabel(_("Skew Angle X:"))
        # self.fin_skewx_label.setToolTip(
        #     _("Final value for angle for Skew action, in degrees.\n"
        #       "Float number between -360 and 359.")
        # )
        # self.fin_skewx_entry = FCDoubleSpinner()
        # self.fin_skewx_entry.set_range(-360, 360)
        # self.fin_skewx_entry.set_precision(self.decimals)
        # self.fin_skewx_entry.setSingleStep(0.1)
        #
        # grid_lay.addWidget(self.fin_skewx_label, 30, 0)
        # grid_lay.addWidget(self.fin_skewx_entry, 30, 1, 1, 2)
        #
        # self.fin_skewy_label = QtWidgets.QLabel(_("Skew Angle Y:"))
        # self.fin_skewy_label.setToolTip(
        #     _("Final value for angle for Skew action, in degrees.\n"
        #       "Float number between -360 and 359.")
        # )
        # self.fin_skewy_entry = FCDoubleSpinner()
        # self.fin_skewy_entry.set_range(-360, 360)
        # self.fin_skewy_entry.set_precision(self.decimals)
        # self.fin_skewy_entry.setSingleStep(0.1)
        #
        # grid_lay.addWidget(self.fin_skewy_label, 31, 0)
        # grid_lay.addWidget(self.fin_skewy_entry, 31, 1, 1, 2)

        separator_line1 = QtWidgets.QFrame()
        separator_line1.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line1.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line1, 32, 0, 1, 3)

        grid_lay.addWidget(QtWidgets.QLabel(''), 32, 0, 1, 3)

        # STEP 4 #
        step_4 = QtWidgets.QLabel('<b>%s</b>' % _("STEP 4: Adjusted GCode"))
        step_4.setToolTip(
            _("Generate verification GCode file adjusted with\n"
              "the factors above.")
        )
        grid_lay.addWidget(step_4, 34, 0, 1, 3)

        # ## Adjusted GCode Button
        self.adj_gcode_button = QtWidgets.QPushButton(_("Generate Adjusted GCode"))
        self.adj_gcode_button.setToolTip(
            _("Generate verification GCode file adjusted with\n"
              "the factors above.")
        )
        self.adj_gcode_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)
        grid_lay.addWidget(self.adj_gcode_button, 35, 0, 1, 3)

        separator_line1 = QtWidgets.QFrame()
        separator_line1.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line1.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line1, 36, 0, 1, 3)

        grid_lay.addWidget(QtWidgets.QLabel(''), 37, 0, 1, 3)

        # STEP 5 #
        step_5 = QtWidgets.QLabel('<b>%s</b>' % _("STEP 5: Calibrate FlatCAM Objects"))
        step_5.setToolTip(
            _("Adjust the Excellon and Cutout Geometry objects\n"
              "with the factors determined, and verified, above.")
        )
        grid_lay.addWidget(step_5, 38, 0, 1, 3)

        self.adj_exc_object_combo = QtWidgets.QComboBox()
        self.adj_exc_object_combo.setModel(self.app.collection)
        self.adj_exc_object_combo.setRootModelIndex(self.app.collection.index(1, 0, QtCore.QModelIndex()))
        self.adj_exc_object_combo.setCurrentIndex(1)

        self.adj_excobj_label = QtWidgets.QLabel("%s:" % _("EXCELLON"))
        self.adj_excobj_label.setToolTip(
            _("Excellon Object to be adjusted.")
        )

        grid_lay.addWidget(self.adj_excobj_label, 39, 0, 1, 3)
        grid_lay.addWidget(self.adj_exc_object_combo, 40, 0, 1, 3)

        self.adj_geo_object_combo = QtWidgets.QComboBox()
        self.adj_geo_object_combo.setModel(self.app.collection)
        self.adj_geo_object_combo.setRootModelIndex(self.app.collection.index(2, 0, QtCore.QModelIndex()))
        self.adj_geo_object_combo.setCurrentIndex(1)

        self.adj_geoobj_label = QtWidgets.QLabel("%s:" % _("GEOMETRY"))
        self.adj_geoobj_label.setToolTip(
            _("Geometry Object to be adjusted.")
        )

        grid_lay.addWidget(self.adj_geoobj_label, 41, 0, 1, 3)
        grid_lay.addWidget(self.adj_geo_object_combo, 42, 0, 1, 3)

        # ## Adjust Objects Button
        self.adj_obj_button = QtWidgets.QPushButton(_("Calibrate"))
        self.adj_obj_button.setToolTip(
            _("Adjust (scale and/or skew) the objects\n"
              "with the factors determined above.")
        )
        self.adj_obj_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)
        grid_lay.addWidget(self.adj_obj_button, 43, 0, 1, 3)

        separator_line2 = QtWidgets.QFrame()
        separator_line2.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line2.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line2, 44, 0, 1, 3)

        grid_lay.addWidget(QtWidgets.QLabel(''), 45, 0, 1, 3)

        self.layout.addStretch()

        # ## Reset Tool
        self.reset_button = QtWidgets.QPushButton(_("Reset Tool"))
        self.reset_button.setToolTip(
            _("Will reset the tool parameters.")
        )
        self.reset_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)
        self.layout.addWidget(self.reset_button)

        self.mr = None
        self.units = ''

        # here store 4 points to be used for calibration
        self.click_points = list()

        # store the status of the grid
        self.grid_status_memory = None

        self.target_obj = None

        # if the mouse events are connected to a local method set this True
        self.local_connected = False

        # ## Signals
        self.start_button.clicked.connect(self.on_start_collect_points)
        self.gcode_button.clicked.connect(self.generate_verification_gcode)
        self.generate_factors_button.clicked.connect(self.calculate_factors)
        self.reset_button.clicked.connect(self.set_tool_ui)

        self.cal_source_radio.activated_custom.connect(self.on_cal_source_radio)

        self.obj_type_combo.currentIndexChanged.connect(self.on_obj_type_combo)

    def run(self, toggle=True):
        self.app.report_usage("ToolCalibration()")

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

        self.app.ui.notebook.setTabText(2, _("Calibrate Tool"))

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, shortcut='ALT+E', **kwargs)

    def set_tool_ui(self):
        self.units = self.app.defaults['units'].upper()

        if self.local_connected is True:
            self.disconnect_cal_events()

        self.reset_calibration_points()

        self.cal_source_radio.set_value(self.app.defaults['tools_cal_calsource'])
        self.travelz_entry.set_value(self.app.defaults['tools_cal_travelz'])
        self.verz_entry.set_value(self.app.defaults['tools_cal_verz'])
        self.zeroz_cb.set_value(self.app.defaults['tools_cal_zeroz'])
        self.toolchangez_entry.set_value(self.app.defaults['tools_cal_toolchangez'])

        self.scalex_entry.set_value(1.0)
        self.scaley_entry.set_value(1.0)
        self.skewx_entry.set_value(0.0)
        self.skewy_entry.set_value(0.0)

        self.app.inform.emit('%s...' % _("Tool initialized"))

    def on_obj_type_combo(self):
        obj_type = self.obj_type_combo.currentIndex()
        self.object_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.object_combo.setCurrentIndex(0)

    def on_cal_source_radio(self, val):
        if val == 'object':
            self.obj_type_label.setDisabled(False)
            self.obj_type_combo.setDisabled(False)
            self.object_label.setDisabled(False)
            self.object_combo.setDisabled(False)
        else:
            self.obj_type_label.setDisabled(True)
            self.obj_type_combo.setDisabled(True)
            self.object_label.setDisabled(True)
            self.object_combo.setDisabled(True)

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

        self.local_connected = True

        if self.cal_source_radio.get_value() == 'object':
            selection_index = self.object_combo.currentIndex()
            model_index = self.app.collection.index(selection_index, 0, self.object_combo.rootModelIndex())
            try:
                self.target_obj = model_index.internalPointer().obj
            except Exception:
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no target object loaded ..."))
                return

        self.reset_calibration_points()

        self.app.inform.emit(_("Get First calibration point. Bottom Left..."))

    def on_mouse_click_release(self, event):
        if event.button == 1:
            if self.app.is_legacy is False:
                event_pos = event.pos
            else:
                event_pos = (event.xdata, event.ydata)

            pos_canvas = self.canvas.translate_coords(event_pos)
            click_pt = Point([pos_canvas[0], pos_canvas[1]])

            if self.cal_source_radio.get_value() == 'object':
                if self.target_obj.kind.lower() == 'excellon':
                    for tool, tool_dict in self.target_obj.tools.items():
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
                else:
                    for apid, apid_val in self.target_obj.apertures.items():
                        for geo_el in apid_val['geometry']:
                            if 'solid' in geo_el:
                                if click_pt.within(geo_el['solid']):
                                    if isinstance(geo_el['follow'], Point):
                                        center_pt = geo_el['solid'].centroid
                                        self.click_points.append(
                                            (
                                                float('%.*f' % (self.decimals, center_pt.x)),
                                                float('%.*f' % (self.decimals, center_pt.y))
                                            )
                                        )
                                        self.check_points()
            else:
                self.click_points.append(
                    (
                        float('%.*f' % (self.decimals, click_pt.x)),
                        float('%.*f' % (self.decimals, click_pt.y))
                    )
                )
                self.check_points()

    def check_points(self):
        if len(self.click_points) == 1:
            self.bottom_left_coordx_tgt.set_value(self.click_points[0][0])
            self.bottom_left_coordy_tgt.set_value(self.click_points[0][1])
            self.app.inform.emit(_("Get Second calibration point. Bottom Right..."))
        elif len(self.click_points) == 2:
            self.bottom_right_coordx_tgt.set_value(self.click_points[1][0])
            self.bottom_right_coordy_tgt.set_value(self.click_points[1][1])
            self.app.inform.emit(_("Get Third calibration point. Top Left..."))
        elif len(self.click_points) == 3:
            self.top_left_coordx_tgt.set_value(self.click_points[2][0])
            self.top_left_coordy_tgt.set_value(self.click_points[2][1])
            self.app.inform.emit(_("Get Forth calibration point. Top Right..."))
        elif len(self.click_points) == 4:
            self.top_right_coordx_tgt.set_value(self.click_points[3][0])
            self.top_right_coordy_tgt.set_value(self.click_points[3][1])
            self.app.inform.emit('[success] %s' % _("Done. All four points have been acquired."))
            self.disconnect_cal_events()

    def reset_calibration_points(self):
        self.click_points = list()

        self.bottom_left_coordx_tgt.set_value('')
        self.bottom_left_coordy_tgt.set_value('')

        self.bottom_right_coordx_tgt.set_value('')
        self.bottom_right_coordy_tgt.set_value('')

        self.top_left_coordx_tgt.set_value('')
        self.top_left_coordy_tgt.set_value('')

        self.top_right_coordx_tgt.set_value('')
        self.top_right_coordy_tgt.set_value('')

    def gcode_header(self):
        log.debug("ToolCalibration.gcode_header()")
        time_str = "{:%A, %d %B %Y at %H:%M}".format(datetime.now())

        gcode = '(G-CODE GENERATED BY FLATCAM v%s - www.flatcam.org - Version Date: %s)\n' % \
                (str(self.app.version), str(self.app.version_date)) + '\n'

        gcode += '(Name: ' + _('Verification GCode for FlatCAM Calibrate Tool') + ')\n'

        gcode += '(Units: ' + self.units.upper() + ')\n' + "\n"
        gcode += '(Created on ' + time_str + ')\n' + '\n'
        gcode += 'G20\n' if self.units.upper() == 'IN' else 'G21\n'
        gcode += 'G90\n'
        gcode += 'G17\n'
        gcode += 'G94\n\n'
        return gcode

    def close_tab(self):
        for idx in range(self.app.ui.plot_tab_area.count()):
            if self.app.ui.plot_tab_area.tabText(idx) == _("Gcode Viewer"):
                wdg = self.app.ui.plot_tab_area.widget(idx)
                wdg.deleteLater()
                self.app.ui.plot_tab_area.removeTab(idx)

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

        self.gcode_editor_tab = TextEditor(app=self.app, plain_text=True)

        # add the tab if it was closed
        self.app.ui.plot_tab_area.addTab(self.gcode_editor_tab, '%s' % _("Gcode Viewer"))
        self.gcode_editor_tab.setObjectName('gcode_viewer_tab')

        # delete the absolute and relative position and messages in the infobar
        self.app.ui.position_label.setText("")
        self.app.ui.rel_position_label.setText("")

        # first clear previous text in text editor (if any)
        self.gcode_editor_tab.code_editor.clear()
        self.gcode_editor_tab.code_editor.setReadOnly(False)

        self.gcode_editor_tab.code_editor.completer_enable = False
        self.gcode_editor_tab.buttonRun.hide()

        # Switch plot_area to CNCJob tab
        self.app.ui.plot_tab_area.setCurrentWidget(self.gcode_editor_tab)

        self.gcode_editor_tab.t_frame.hide()
        # then append the text from GCode to the text editor
        try:
            self.gcode_editor_tab.code_editor.setPlainText(gcode)
        except Exception as e:
            self.app.inform.emit('[ERROR] %s %s' % ('ERROR -->', str(e)))
            return

        self.gcode_editor_tab.code_editor.moveCursor(QtGui.QTextCursor.Start)

        self.gcode_editor_tab.t_frame.show()
        self.app.proc_container.view.set_idle()

        self.app.inform.emit('[success] %s...' % _('Loaded Machine Code into Code Editor'))

        _filter_ = "G-Code Files (*.nc);;All Files (*.*)"
        self.gcode_editor_tab.buttonSave.clicked.disconnect()
        self.gcode_editor_tab.buttonSave.clicked.connect(
            lambda: self.gcode_editor_tab.handleSaveGCode(name='fc_ver_gcode', filt=_filter_, callback=self.close_tab))
        #
        # try:
        #     dir_file_to_save = self.app.get_last_save_folder() + '/' + 'ver_gcode'
        #     filename, _f = QtWidgets.QFileDialog.getSaveFileName(
        #         caption=_("Export Machine Code ..."),
        #         directory=dir_file_to_save,
        #         filter=_filter_
        #     )
        # except TypeError:
        #     filename, _f = QtWidgets.QFileDialog.getSaveFileName(caption=_("Export Machine Code ..."), filter=_filter_)
        #
        # filename = str(filename)
        #
        # if filename == '':
        #     self.app.inform.emit('[WARNING_NOTCL] %s' % _("Export Machine Code cancelled ..."))
        #     return
        #
        # with open(filename, 'w') as f:
        #     f.write(gcode)

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

        # top_right_x = float('%.*f' % (self.decimals, self.click_points[3][0]))
        # top_right_y = float('%.*f' % (self.decimals, self.click_points[3][1]))

        # try:
        #     top_right_dx = float('%.*f' % (self.decimals, self.top_right_coordx_found.get_value()))
        # except TypeError:
        #     top_right_dx = top_right_x
        #
        # try:
        #     top_right_dy = float('%.*f' % (self.decimals, self.top_right_coordy_found.get_value()))
        # except TypeError:
        #     top_right_dy = top_right_y

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

            self.skewx_entry.set_value(skew_angle_x)

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
        # restore the Grid snapping if it was active before
        if self.grid_status_memory is True:
            self.app.ui.grid_snap_btn.trigger()

        self.app.mr = self.canvas.graph_event_connect('mouse_release', self.app.on_mouse_click_release_over_plot)

        if self.app.is_legacy is False:
            self.canvas.graph_event_disconnect('mouse_release', self.on_mouse_click_release)
        else:
            self.canvas.graph_event_disconnect(self.mr)

        self.local_connected = False

    def reset_fields(self):
        self.object_combo.setRootModelIndex(self.app.collection.index(1, 0, QtCore.QModelIndex()))
        self.adj_exc_object_combo.setRootModelIndex(self.app.collection.index(1, 0, QtCore.QModelIndex()))
        self.adj_geo_object_combo.setRootModelIndex(self.app.collection.index(2, 0, QtCore.QModelIndex()))

# end of file
