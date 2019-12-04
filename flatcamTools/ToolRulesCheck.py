# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 09/27/2019                                         #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets

from FlatCAMTool import FlatCAMTool
from flatcamGUI.GUIElements import FCDoubleSpinner, FCCheckBox, OptionalInputSection
from copy import deepcopy

from FlatCAMPool import *
# from os import getpid
from shapely.ops import nearest_points
from shapely.geometry import MultiPolygon, Polygon

import logging
import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class RulesCheck(FlatCAMTool):

    toolName = _("Check Rules")

    tool_finished = QtCore.pyqtSignal(list)

    def __init__(self, app):
        super(RulesCheck, self).__init__(self)
        self.app = app
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

        # Form Layout
        self.grid_layout = QtWidgets.QGridLayout()
        self.layout.addLayout(self.grid_layout)

        self.grid_layout.setColumnStretch(0, 0)
        self.grid_layout.setColumnStretch(1, 3)
        self.grid_layout.setColumnStretch(2, 0)

        self.gerber_title_lbl = QtWidgets.QLabel('<b>%s</b>:' % _("Gerber Files"))
        self.gerber_title_lbl.setToolTip(
            _("Gerber objects for which to check rules.")
        )

        self.all_obj_cb = FCCheckBox()

        self.grid_layout.addWidget(self.gerber_title_lbl, 0, 0, 1, 2)
        self.grid_layout.addWidget(self.all_obj_cb, 0, 2)

        # Copper Top object
        self.copper_t_object = QtWidgets.QComboBox()
        self.copper_t_object.setModel(self.app.collection)
        self.copper_t_object.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.copper_t_object.setCurrentIndex(1)

        self.copper_t_object_lbl = QtWidgets.QLabel('%s:' % _("Top"))
        self.copper_t_object_lbl.setToolTip(
            _("The Top Gerber Copper object for which rules are checked.")
        )

        self.copper_t_cb = FCCheckBox()

        self.grid_layout.addWidget(self.copper_t_object_lbl, 1, 0)
        self.grid_layout.addWidget(self.copper_t_object, 1, 1)
        self.grid_layout.addWidget(self.copper_t_cb, 1, 2)

        # Copper Bottom object
        self.copper_b_object = QtWidgets.QComboBox()
        self.copper_b_object.setModel(self.app.collection)
        self.copper_b_object.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.copper_b_object.setCurrentIndex(1)

        self.copper_b_object_lbl = QtWidgets.QLabel('%s:' % _("Bottom"))
        self.copper_b_object_lbl.setToolTip(
            _("The Bottom Gerber Copper object for which rules are checked.")
        )

        self.copper_b_cb = FCCheckBox()

        self.grid_layout.addWidget(self.copper_b_object_lbl, 2, 0)
        self.grid_layout.addWidget(self.copper_b_object, 2, 1)
        self.grid_layout.addWidget(self.copper_b_cb, 2, 2)

        # SolderMask Top object
        self.sm_t_object = QtWidgets.QComboBox()
        self.sm_t_object.setModel(self.app.collection)
        self.sm_t_object.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.sm_t_object.setCurrentIndex(1)

        self.sm_t_object_lbl = QtWidgets.QLabel('%s:' % _("SM Top"))
        self.sm_t_object_lbl.setToolTip(
            _("The Top Gerber Solder Mask object for which rules are checked.")
        )

        self.sm_t_cb = FCCheckBox()

        self.grid_layout.addWidget(self.sm_t_object_lbl, 3, 0)
        self.grid_layout.addWidget(self.sm_t_object, 3, 1)
        self.grid_layout.addWidget(self.sm_t_cb, 3, 2)

        # SolderMask Bottom object
        self.sm_b_object = QtWidgets.QComboBox()
        self.sm_b_object.setModel(self.app.collection)
        self.sm_b_object.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.sm_b_object.setCurrentIndex(1)

        self.sm_b_object_lbl = QtWidgets.QLabel('%s:' % _("SM Bottom"))
        self.sm_b_object_lbl.setToolTip(
            _("The Bottom Gerber Solder Mask object for which rules are checked.")
        )

        self.sm_b_cb = FCCheckBox()

        self.grid_layout.addWidget(self.sm_b_object_lbl, 4, 0)
        self.grid_layout.addWidget(self.sm_b_object, 4, 1)
        self.grid_layout.addWidget(self.sm_b_cb, 4, 2)

        # SilkScreen Top object
        self.ss_t_object = QtWidgets.QComboBox()
        self.ss_t_object.setModel(self.app.collection)
        self.ss_t_object.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.ss_t_object.setCurrentIndex(1)

        self.ss_t_object_lbl = QtWidgets.QLabel('%s:' % _("Silk Top"))
        self.ss_t_object_lbl.setToolTip(
            _("The Top Gerber Silkscreen object for which rules are checked.")
        )

        self.ss_t_cb = FCCheckBox()

        self.grid_layout.addWidget(self.ss_t_object_lbl, 5, 0)
        self.grid_layout.addWidget(self.ss_t_object, 5, 1)
        self.grid_layout.addWidget(self.ss_t_cb, 5, 2)

        # SilkScreen Bottom object
        self.ss_b_object = QtWidgets.QComboBox()
        self.ss_b_object.setModel(self.app.collection)
        self.ss_b_object.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.ss_b_object.setCurrentIndex(1)

        self.ss_b_object_lbl = QtWidgets.QLabel('%s:' % _("Silk Bottom"))
        self.ss_b_object_lbl.setToolTip(
            _("The Bottom Gerber Silkscreen object for which rules are checked.")
        )

        self.ss_b_cb = FCCheckBox()

        self.grid_layout.addWidget(self.ss_b_object_lbl, 6, 0)
        self.grid_layout.addWidget(self.ss_b_object, 6, 1)
        self.grid_layout.addWidget(self.ss_b_cb, 6, 2)

        # Outline object
        self.outline_object = QtWidgets.QComboBox()
        self.outline_object.setModel(self.app.collection)
        self.outline_object.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.outline_object.setCurrentIndex(1)

        self.outline_object_lbl = QtWidgets.QLabel('%s:' % _("Outline"))
        self.outline_object_lbl.setToolTip(
            _("The Gerber Outline (Cutout) object for which rules are checked.")
        )

        self.out_cb = FCCheckBox()

        self.grid_layout.addWidget(self.outline_object_lbl, 7, 0)
        self.grid_layout.addWidget(self.outline_object, 7, 1)
        self.grid_layout.addWidget(self.out_cb, 7, 2)

        self.grid_layout.addWidget(QtWidgets.QLabel(""), 8, 0, 1, 3)

        self.excellon_title_lbl = QtWidgets.QLabel('<b>%s</b>:' % _("Excellon Objects"))
        self.excellon_title_lbl.setToolTip(
            _("Excellon objects for which to check rules.")
        )

        self.grid_layout.addWidget(self.excellon_title_lbl, 9, 0, 1, 3)

        # Excellon 1 object
        self.e1_object = QtWidgets.QComboBox()
        self.e1_object.setModel(self.app.collection)
        self.e1_object.setRootModelIndex(self.app.collection.index(1, 0, QtCore.QModelIndex()))
        self.e1_object.setCurrentIndex(1)

        self.e1_object_lbl = QtWidgets.QLabel('%s:' % _("Excellon 1"))
        self.e1_object_lbl.setToolTip(
            _("Excellon object for which to check rules.\n"
              "Holds the plated holes or a general Excellon file content.")
        )

        self.e1_cb = FCCheckBox()

        self.grid_layout.addWidget(self.e1_object_lbl, 10, 0)
        self.grid_layout.addWidget(self.e1_object, 10, 1)
        self.grid_layout.addWidget(self.e1_cb, 10, 2)

        # Excellon 2 object
        self.e2_object = QtWidgets.QComboBox()
        self.e2_object.setModel(self.app.collection)
        self.e2_object.setRootModelIndex(self.app.collection.index(1, 0, QtCore.QModelIndex()))
        self.e2_object.setCurrentIndex(1)

        self.e2_object_lbl = QtWidgets.QLabel('%s:' % _("Excellon 2"))
        self.e2_object_lbl.setToolTip(
            _("Excellon object for which to check rules.\n"
              "Holds the non-plated holes.")
        )

        self.e2_cb = FCCheckBox()

        self.grid_layout.addWidget(self.e2_object_lbl, 11, 0)
        self.grid_layout.addWidget(self.e2_object, 11, 1)
        self.grid_layout.addWidget(self.e2_cb, 11, 2)

        self.grid_layout.addWidget(QtWidgets.QLabel(""), 12, 0, 1, 3)

        # Control All
        self.all_cb = FCCheckBox('%s' % _("All Rules"))
        self.all_cb.setToolTip(
            _("This check/uncheck all the rules below.")
        )
        self.all_cb.setStyleSheet(
            """
            QCheckBox {font-weight: bold; color: green}
            """
        )
        self.layout.addWidget(self.all_cb)

        # Form Layout
        self.form_layout_1 = QtWidgets.QFormLayout()
        self.layout.addLayout(self.form_layout_1)

        self.form_layout_1.addRow(QtWidgets.QLabel(""))

        # Trace size
        self.trace_size_cb = FCCheckBox('%s:' % _("Trace Size"))
        self.trace_size_cb.setToolTip(
            _("This checks if the minimum size for traces is met.")
        )
        self.form_layout_1.addRow(self.trace_size_cb)

        # Trace size value
        self.trace_size_entry = FCDoubleSpinner()
        self.trace_size_entry.set_range(0.00001, 999.99999)
        self.trace_size_entry.set_precision(self.decimals)
        self.trace_size_entry.setSingleStep(0.1)

        self.trace_size_lbl = QtWidgets.QLabel('%s:' % _("Min value"))
        self.trace_size_lbl.setToolTip(
            _("Minimum acceptable trace size.")
        )
        self.form_layout_1.addRow(self.trace_size_lbl, self.trace_size_entry)

        self.ts = OptionalInputSection(self.trace_size_cb, [self.trace_size_lbl, self.trace_size_entry])

        # Copper2copper clearance
        self.clearance_copper2copper_cb = FCCheckBox('%s:' % _("Copper to Copper clearance"))
        self.clearance_copper2copper_cb.setToolTip(
            _("This checks if the minimum clearance between copper\n"
              "features is met.")
        )
        self.form_layout_1.addRow(self.clearance_copper2copper_cb)

        # Copper2copper clearance value
        self.clearance_copper2copper_entry = FCDoubleSpinner()
        self.clearance_copper2copper_entry.set_range(0.00001, 999.99999)
        self.clearance_copper2copper_entry.set_precision(self.decimals)
        self.clearance_copper2copper_entry.setSingleStep(0.1)

        self.clearance_copper2copper_lbl = QtWidgets.QLabel('%s:' % _("Min value"))
        self.clearance_copper2copper_lbl.setToolTip(
            _("Minimum acceptable clearance value.")
        )
        self.form_layout_1.addRow(self.clearance_copper2copper_lbl, self.clearance_copper2copper_entry)

        self.c2c = OptionalInputSection(
            self.clearance_copper2copper_cb, [self.clearance_copper2copper_lbl, self.clearance_copper2copper_entry])

        # Copper2outline clearance
        self.clearance_copper2ol_cb = FCCheckBox('%s:' % _("Copper to Outline clearance"))
        self.clearance_copper2ol_cb.setToolTip(
            _("This checks if the minimum clearance between copper\n"
              "features and the outline is met.")
        )
        self.form_layout_1.addRow(self.clearance_copper2ol_cb)

        # Copper2outline clearance value
        self.clearance_copper2ol_entry = FCDoubleSpinner()
        self.clearance_copper2ol_entry.set_range(0.00001, 999.99999)
        self.clearance_copper2ol_entry.set_precision(self.decimals)
        self.clearance_copper2ol_entry.setSingleStep(0.1)

        self.clearance_copper2ol_lbl = QtWidgets.QLabel('%s:' % _("Min value"))
        self.clearance_copper2ol_lbl.setToolTip(
            _("Minimum acceptable clearance value.")
        )
        self.form_layout_1.addRow(self.clearance_copper2ol_lbl, self.clearance_copper2ol_entry)

        self.c2ol = OptionalInputSection(
            self.clearance_copper2ol_cb, [self.clearance_copper2ol_lbl, self.clearance_copper2ol_entry])

        # Silkscreen2silkscreen clearance
        self.clearance_silk2silk_cb = FCCheckBox('%s:' % _("Silk to Silk Clearance"))
        self.clearance_silk2silk_cb.setToolTip(
            _("This checks if the minimum clearance between silkscreen\n"
              "features and silkscreen features is met.")
        )
        self.form_layout_1.addRow(self.clearance_silk2silk_cb)

        # Copper2silkscreen clearance value
        self.clearance_silk2silk_entry = FCDoubleSpinner()
        self.clearance_silk2silk_entry.set_range(0.00001, 999.99999)
        self.clearance_silk2silk_entry.set_precision(self.decimals)
        self.clearance_silk2silk_entry.setSingleStep(0.1)

        self.clearance_silk2silk_lbl = QtWidgets.QLabel('%s:' % _("Min value"))
        self.clearance_silk2silk_lbl.setToolTip(
            _("Minimum acceptable clearance value.")
        )
        self.form_layout_1.addRow(self.clearance_silk2silk_lbl, self.clearance_silk2silk_entry)

        self.s2s = OptionalInputSection(
            self.clearance_silk2silk_cb, [self.clearance_silk2silk_lbl, self.clearance_silk2silk_entry])

        # Silkscreen2soldermask clearance
        self.clearance_silk2sm_cb = FCCheckBox('%s:' % _("Silk to Solder Mask Clearance"))
        self.clearance_silk2sm_cb.setToolTip(
            _("This checks if the minimum clearance between silkscreen\n"
              "features and soldermask features is met.")
        )
        self.form_layout_1.addRow(self.clearance_silk2sm_cb)

        # Silkscreen2soldermask clearance value
        self.clearance_silk2sm_entry = FCDoubleSpinner()
        self.clearance_silk2sm_entry.set_range(0.00001, 999.99999)
        self.clearance_silk2sm_entry.set_precision(self.decimals)
        self.clearance_silk2sm_entry.setSingleStep(0.1)

        self.clearance_silk2sm_lbl = QtWidgets.QLabel('%s:' % _("Min value"))
        self.clearance_silk2sm_lbl.setToolTip(
            _("Minimum acceptable clearance value.")
        )
        self.form_layout_1.addRow(self.clearance_silk2sm_lbl, self.clearance_silk2sm_entry)

        self.s2sm = OptionalInputSection(
            self.clearance_silk2sm_cb, [self.clearance_silk2sm_lbl, self.clearance_silk2sm_entry])

        # Silk2outline clearance
        self.clearance_silk2ol_cb = FCCheckBox('%s:' % _("Silk to Outline Clearance"))
        self.clearance_silk2ol_cb.setToolTip(
            _("This checks if the minimum clearance between silk\n"
              "features and the outline is met.")
        )
        self.form_layout_1.addRow(self.clearance_silk2ol_cb)

        # Silk2outline clearance value
        self.clearance_silk2ol_entry = FCDoubleSpinner()
        self.clearance_silk2ol_entry.set_range(0.00001, 999.99999)
        self.clearance_silk2ol_entry.set_precision(self.decimals)
        self.clearance_silk2ol_entry.setSingleStep(0.1)

        self.clearance_silk2ol_lbl = QtWidgets.QLabel('%s:' % _("Min value"))
        self.clearance_silk2ol_lbl.setToolTip(
            _("Minimum acceptable clearance value.")
        )
        self.form_layout_1.addRow(self.clearance_silk2ol_lbl, self.clearance_silk2ol_entry)

        self.s2ol = OptionalInputSection(
            self.clearance_silk2ol_cb, [self.clearance_silk2ol_lbl, self.clearance_silk2ol_entry])

        # Soldermask2soldermask clearance
        self.clearance_sm2sm_cb = FCCheckBox('%s:' % _("Minimum Solder Mask Sliver"))
        self.clearance_sm2sm_cb.setToolTip(
            _("This checks if the minimum clearance between soldermask\n"
              "features and soldermask features is met.")
        )
        self.form_layout_1.addRow(self.clearance_sm2sm_cb)

        # Soldermask2soldermask clearance value
        self.clearance_sm2sm_entry = FCDoubleSpinner()
        self.clearance_sm2sm_entry.set_range(0.00001, 999.99999)
        self.clearance_sm2sm_entry.set_precision(self.decimals)
        self.clearance_sm2sm_entry.setSingleStep(0.1)

        self.clearance_sm2sm_lbl = QtWidgets.QLabel('%s:' % _("Min value"))
        self.clearance_sm2sm_lbl.setToolTip(
            _("Minimum acceptable clearance value.")
        )
        self.form_layout_1.addRow(self.clearance_sm2sm_lbl, self.clearance_sm2sm_entry)

        self.sm2sm = OptionalInputSection(
            self.clearance_sm2sm_cb, [self.clearance_sm2sm_lbl, self.clearance_sm2sm_entry])

        # Ring integrity check
        self.ring_integrity_cb = FCCheckBox('%s:' % _("Minimum Annular Ring"))
        self.ring_integrity_cb.setToolTip(
            _("This checks if the minimum copper ring left by drilling\n"
              "a hole into a pad is met.")
        )
        self.form_layout_1.addRow(self.ring_integrity_cb)

        # Ring integrity value
        self.ring_integrity_entry = FCDoubleSpinner()
        self.ring_integrity_entry.set_range(0.00001, 999.99999)
        self.ring_integrity_entry.set_precision(self.decimals)
        self.ring_integrity_entry.setSingleStep(0.1)

        self.ring_integrity_lbl = QtWidgets.QLabel('%s:' % _("Min value"))
        self.ring_integrity_lbl.setToolTip(
            _("Minimum acceptable ring value.")
        )
        self.form_layout_1.addRow(self.ring_integrity_lbl, self.ring_integrity_entry)

        self.anr = OptionalInputSection(
            self.ring_integrity_cb, [self.ring_integrity_lbl, self.ring_integrity_entry])

        self.form_layout_1.addRow(QtWidgets.QLabel(""))

        # Hole2Hole clearance
        self.clearance_d2d_cb = FCCheckBox('%s:' % _("Hole to Hole Clearance"))
        self.clearance_d2d_cb.setToolTip(
            _("This checks if the minimum clearance between a drill hole\n"
              "and another drill hole is met.")
        )
        self.form_layout_1.addRow(self.clearance_d2d_cb)

        # Hole2Hole clearance value
        self.clearance_d2d_entry = FCDoubleSpinner()
        self.clearance_d2d_entry.set_range(0.00001, 999.99999)
        self.clearance_d2d_entry.set_precision(self.decimals)
        self.clearance_d2d_entry.setSingleStep(0.1)

        self.clearance_d2d_lbl = QtWidgets.QLabel('%s:' % _("Min value"))
        self.clearance_d2d_lbl.setToolTip(
            _("Minimum acceptable clearance value.")
        )
        self.form_layout_1.addRow(self.clearance_d2d_lbl, self.clearance_d2d_entry)

        self.d2d = OptionalInputSection(
            self.clearance_d2d_cb, [self.clearance_d2d_lbl, self.clearance_d2d_entry])

        # Drill holes size check
        self.drill_size_cb = FCCheckBox('%s:' % _("Hole Size"))
        self.drill_size_cb.setToolTip(
            _("This checks if the drill holes\n"
              "sizes are above the threshold.")
        )
        self.form_layout_1.addRow(self.drill_size_cb)

        # Drile holes value
        self.drill_size_entry = FCDoubleSpinner()
        self.drill_size_entry.set_range(0.00001, 999.99999)
        self.drill_size_entry.set_precision(self.decimals)
        self.drill_size_entry.setSingleStep(0.1)

        self.drill_size_lbl = QtWidgets.QLabel('%s:' % _("Min value"))
        self.drill_size_lbl.setToolTip(
            _("Minimum acceptable drill size.")
        )
        self.form_layout_1.addRow(self.drill_size_lbl, self.drill_size_entry)

        self.ds = OptionalInputSection(
            self.drill_size_cb, [self.drill_size_lbl, self.drill_size_entry])

        # Buttons
        hlay_2 = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay_2)

        # hlay_2.addStretch()
        self.run_button = QtWidgets.QPushButton(_("Run Rules Check"))
        self.run_button.setToolTip(
            _("Panelize the specified object around the specified box.\n"
              "In other words it creates multiple copies of the source object,\n"
              "arranged in a 2D array of rows and columns.")
        )
        self.run_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)
        hlay_2.addWidget(self.run_button)

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

        # #######################################################
        # ################ SIGNALS ##############################
        # #######################################################
        self.copper_t_cb.stateChanged.connect(lambda st: self.copper_t_object.setDisabled(not st))
        self.copper_b_cb.stateChanged.connect(lambda st: self.copper_b_object.setDisabled(not st))

        self.sm_t_cb.stateChanged.connect(lambda st: self.sm_t_object.setDisabled(not st))
        self.sm_b_cb.stateChanged.connect(lambda st: self.sm_b_object.setDisabled(not st))

        self.ss_t_cb.stateChanged.connect(lambda st: self.ss_t_object.setDisabled(not st))
        self.ss_b_cb.stateChanged.connect(lambda st: self.ss_b_object.setDisabled(not st))

        self.out_cb.stateChanged.connect(lambda st: self.outline_object.setDisabled(not st))

        self.e1_cb.stateChanged.connect(lambda st: self.e1_object.setDisabled(not st))
        self.e2_cb.stateChanged.connect(lambda st: self.e2_object.setDisabled(not st))

        self.all_obj_cb.stateChanged.connect(self.on_all_objects_cb_changed)
        self.all_cb.stateChanged.connect(self.on_all_cb_changed)
        self.run_button.clicked.connect(self.execute)
        # self.app.collection.rowsInserted.connect(self.on_object_loaded)

        self.tool_finished.connect(self.on_tool_finished)
        self.reset_button.clicked.connect(self.set_tool_ui)

        # list to hold the temporary objects
        self.objs = []

        # final name for the panel object
        self.outname = ""

        # flag to signal the constrain was activated
        self.constrain_flag = False

        # Multiprocessing Process Pool
        self.pool = self.app.pool
        self.results = None

        self.decimals = 4

    # def on_object_loaded(self, index, row):
    #     print(index.internalPointer().child_items[row].obj.options['name'], index.data())

    def on_all_cb_changed(self, state):
        cb_items = [self.form_layout_1.itemAt(i).widget() for i in range(self.form_layout_1.count())
                    if isinstance(self.form_layout_1.itemAt(i).widget(), FCCheckBox)]

        for cb in cb_items:
            if state:
                cb.setChecked(True)
            else:
                cb.setChecked(False)

    def on_all_objects_cb_changed(self, state):
        cb_items = [self.grid_layout.itemAt(i).widget() for i in range(self.grid_layout.count())
                    if isinstance(self.grid_layout.itemAt(i).widget(), FCCheckBox)]

        for cb in cb_items:
            if state:
                cb.setChecked(True)
            else:
                cb.setChecked(False)

    def run(self, toggle=True):
        self.app.report_usage("ToolRulesCheck()")

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

        self.app.ui.notebook.setTabText(2, _("Rules Tool"))

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, shortcut='ALT+R', **kwargs)

    def set_tool_ui(self):

        # all object combobox default as disabled
        self.copper_t_object.setDisabled(True)
        self.copper_b_object.setDisabled(True)

        self.sm_t_object.setDisabled(True)
        self.sm_b_object.setDisabled(True)

        self.ss_t_object.setDisabled(True)
        self.ss_b_object.setDisabled(True)

        self.outline_object.setDisabled(True)

        self.e1_object.setDisabled(True)
        self.e2_object.setDisabled(True)

        self.trace_size_cb.set_value(self.app.defaults["tools_cr_trace_size"])
        self.trace_size_entry.set_value(float(self.app.defaults["tools_cr_trace_size_val"]))
        self.clearance_copper2copper_cb.set_value(self.app.defaults["tools_cr_c2c"])
        self.clearance_copper2copper_entry.set_value(float(self.app.defaults["tools_cr_c2c_val"]))
        self.clearance_copper2ol_cb.set_value(self.app.defaults["tools_cr_c2o"])
        self.clearance_copper2ol_entry.set_value(float(self.app.defaults["tools_cr_c2o_val"]))
        self.clearance_silk2silk_cb.set_value(self.app.defaults["tools_cr_s2s"])
        self.clearance_silk2silk_entry.set_value(float(self.app.defaults["tools_cr_s2s_val"]))
        self.clearance_silk2sm_cb.set_value(self.app.defaults["tools_cr_s2sm"])
        self.clearance_silk2sm_entry.set_value(float(self.app.defaults["tools_cr_s2sm_val"]))
        self.clearance_silk2ol_cb.set_value(self.app.defaults["tools_cr_s2o"])
        self.clearance_silk2ol_entry.set_value(float(self.app.defaults["tools_cr_s2o_val"]))
        self.clearance_sm2sm_cb.set_value(self.app.defaults["tools_cr_sm2sm"])
        self.clearance_sm2sm_entry.set_value(float(self.app.defaults["tools_cr_sm2sm_val"]))
        self.ring_integrity_cb.set_value(self.app.defaults["tools_cr_ri"])
        self.ring_integrity_entry.set_value(float(self.app.defaults["tools_cr_ri_val"]))
        self.clearance_d2d_cb.set_value(self.app.defaults["tools_cr_h2h"])
        self.clearance_d2d_entry.set_value(float(self.app.defaults["tools_cr_h2h_val"]))
        self.drill_size_cb.set_value(self.app.defaults["tools_cr_dh"])
        self.drill_size_entry.set_value(float(self.app.defaults["tools_cr_dh_val"]))

        self.reset_fields()

    @staticmethod
    def check_inside_gerber_clearance(gerber_obj, size, rule):
        log.debug("RulesCheck.check_inside_gerber_clearance()")

        rule_title = rule

        violations = list()
        obj_violations = dict()
        obj_violations.update({
            'name': '',
            'points': list()
        })

        if not gerber_obj:
            return 'Fail. Not enough Gerber objects to check Gerber 2 Gerber clearance'

        obj_violations['name'] = gerber_obj['name']

        solid_geo = list()
        clear_geo = list()
        for apid in gerber_obj['apertures']:
            if 'geometry' in gerber_obj['apertures'][apid]:
                geometry = gerber_obj['apertures'][apid]['geometry']
                for geo_el in geometry:
                    if 'solid' in geo_el and geo_el['solid'] is not None:
                        solid_geo.append(geo_el['solid'])
                    if 'clear' in geo_el and geo_el['clear'] is not None:
                        clear_geo.append(geo_el['clear'])

        if clear_geo:
            total_geo = list()
            for geo_c in clear_geo:
                for geo_s in solid_geo:
                    if geo_c.within(geo_s):
                        total_geo.append(geo_s.difference(geo_c))
        else:
            total_geo = MultiPolygon(solid_geo)
            total_geo = total_geo.buffer(0.000001)

        if isinstance(total_geo, Polygon):
            obj_violations['points'] = ['Failed. Only one polygon.']
            return rule_title, [obj_violations]
        else:
            iterations = len(total_geo)
            iterations = (iterations * (iterations - 1)) / 2
        log.debug("RulesCheck.check_gerber_clearance(). Iterations: %s" % str(iterations))

        min_dict = dict()
        idx = 1
        for geo in total_geo:
            for s_geo in total_geo[idx:]:
                # minimize the number of distances by not taking into considerations those that are too small
                dist = geo.distance(s_geo)
                if float(dist) < float(size):
                    loc_1, loc_2 = nearest_points(geo, s_geo)

                    dx = loc_1.x - loc_2.x
                    dy = loc_1.y - loc_2.y
                    loc = min(loc_1.x, loc_2.x) + (abs(dx) / 2), min(loc_1.y, loc_2.y) + (abs(dy) / 2)

                    if dist in min_dict:
                        min_dict[dist].append(loc)
                    else:
                        min_dict[dist] = [loc]
            idx += 1
        points_list = set()
        for dist in min_dict.keys():
            for location in min_dict[dist]:
                points_list.add(location)

        obj_violations['points'] = list(points_list)
        violations.append(deepcopy(obj_violations))

        return rule_title, violations

    @staticmethod
    def check_gerber_clearance(gerber_list, size, rule):
        log.debug("RulesCheck.check_gerber_clearance()")
        rule_title = rule

        violations = list()
        obj_violations = dict()
        obj_violations.update({
            'name': '',
            'points': list()
        })

        if len(gerber_list) == 2:
            gerber_1 = gerber_list[0]
            # added it so I won't have errors of using before declaring
            gerber_2 = dict()

            gerber_3 = gerber_list[1]
        elif len(gerber_list) == 3:
            gerber_1 = gerber_list[0]
            gerber_2 = gerber_list[1]
            gerber_3 = gerber_list[2]
        else:
            return 'Fail. Not enough Gerber objects to check Gerber 2 Gerber clearance'

        total_geo_grb_1 = list()
        for apid in gerber_1['apertures']:
            if 'geometry' in gerber_1['apertures'][apid]:
                geometry = gerber_1['apertures'][apid]['geometry']
                for geo_el in geometry:
                    if 'solid' in geo_el and geo_el['solid'] is not None:
                        total_geo_grb_1.append(geo_el['solid'])

        if len(gerber_list) == 3:
            # add the second Gerber geometry to the first one if it exists
            for apid in gerber_2['apertures']:
                if 'geometry' in gerber_2['apertures'][apid]:
                    geometry = gerber_2['apertures'][apid]['geometry']
                    for geo_el in geometry:
                        if 'solid' in geo_el and geo_el['solid'] is not None:
                            total_geo_grb_1.append(geo_el['solid'])

        total_geo_grb_3 = list()
        for apid in gerber_3['apertures']:
            if 'geometry' in gerber_3['apertures'][apid]:
                geometry = gerber_3['apertures'][apid]['geometry']
                for geo_el in geometry:
                    if 'solid' in geo_el and geo_el['solid'] is not None:
                        total_geo_grb_3.append(geo_el['solid'])

        total_geo_grb_1 = MultiPolygon(total_geo_grb_1)
        total_geo_grb_1 = total_geo_grb_1.buffer(0)

        total_geo_grb_3 = MultiPolygon(total_geo_grb_3)
        total_geo_grb_3 = total_geo_grb_3.buffer(0)

        if isinstance(total_geo_grb_1, Polygon):
            len_1 = 1
            total_geo_grb_1 = [total_geo_grb_1]
        else:
            len_1 = len(total_geo_grb_1)

        if isinstance(total_geo_grb_3, Polygon):
            len_3 = 1
            total_geo_grb_3 = [total_geo_grb_3]
        else:
            len_3 = len(total_geo_grb_3)

        iterations = len_1 * len_3
        log.debug("RulesCheck.check_gerber_clearance(). Iterations: %s" % str(iterations))

        min_dict = dict()
        for geo in total_geo_grb_1:
            for s_geo in total_geo_grb_3:
                # minimize the number of distances by not taking into considerations those that are too small
                dist = geo.distance(s_geo)
                if float(dist) < float(size):
                    loc_1, loc_2 = nearest_points(geo, s_geo)

                    dx = loc_1.x - loc_2.x
                    dy = loc_1.y - loc_2.y
                    loc = min(loc_1.x, loc_2.x) + (abs(dx) / 2), min(loc_1.y, loc_2.y) + (abs(dy) / 2)

                    if dist in min_dict:
                        min_dict[dist].append(loc)
                    else:
                        min_dict[dist] = [loc]

        points_list = set()
        for dist in min_dict.keys():
            for location in min_dict[dist]:
                points_list.add(location)

        name_list = list()
        if gerber_1:
            name_list.append(gerber_1['name'])
        if gerber_2:
            name_list.append(gerber_2['name'])
        if gerber_3:
            name_list.append(gerber_3['name'])

        obj_violations['name'] = name_list
        obj_violations['points'] = list(points_list)
        violations.append(deepcopy(obj_violations))

        return rule_title, violations

    @staticmethod
    def check_holes_size(elements, size):
        log.debug("RulesCheck.check_holes_size()")

        rule = _("Hole Size")

        violations = list()
        obj_violations = dict()
        obj_violations.update({
            'name': '',
            'dia': list()
        })

        for elem in elements:
            dia_list = []

            name = elem['name']
            for tool in elem['tools']:
                tool_dia = float('%.*f' % (4, float(elem['tools'][tool]['C'])))
                if tool_dia < float(size):
                    dia_list.append(tool_dia)
            obj_violations['name'] = name
            obj_violations['dia'] = dia_list
            violations.append(deepcopy(obj_violations))

        return rule, violations

    @staticmethod
    def check_holes_clearance(elements, size):
        log.debug("RulesCheck.check_holes_clearance()")
        rule = _("Hole to Hole Clearance")

        violations = list()
        obj_violations = dict()
        obj_violations.update({
            'name': '',
            'points': list()
        })

        total_geo = list()
        for elem in elements:
            for tool in elem['tools']:
                if 'solid_geometry' in elem['tools'][tool]:
                    geometry = elem['tools'][tool]['solid_geometry']
                    for geo in geometry:
                        total_geo.append(geo)

        min_dict = dict()
        idx = 1
        for geo in total_geo:
            for s_geo in total_geo[idx:]:

                # minimize the number of distances by not taking into considerations those that are too small
                dist = geo.distance(s_geo)
                loc_1, loc_2 = nearest_points(geo, s_geo)

                dx = loc_1.x - loc_2.x
                dy = loc_1.y - loc_2.y
                loc = min(loc_1.x, loc_2.x) + (abs(dx) / 2), min(loc_1.y, loc_2.y) + (abs(dy) / 2)

                if dist in min_dict:
                    min_dict[dist].append(loc)
                else:
                    min_dict[dist] = [loc]
            idx += 1

        points_list = set()
        for dist in min_dict.keys():
            if float(dist) < size:
                for location in min_dict[dist]:
                    points_list.add(location)

        name_list = list()
        for elem in elements:
            name_list.append(elem['name'])

        obj_violations['name'] = name_list
        obj_violations['points'] = list(points_list)
        violations.append(deepcopy(obj_violations))

        return rule, violations

    @staticmethod
    def check_traces_size(elements, size):
        log.debug("RulesCheck.check_traces_size()")

        rule = _("Trace Size")

        violations = list()
        obj_violations = dict()
        obj_violations.update({
            'name': '',
            'size': list(),
            'points': list()
        })

        for elem in elements:
            dia_list = []
            points_list = []
            name = elem['name']

            for apid in elem['apertures']:
                try:
                    tool_dia = float(elem['apertures'][apid]['size'])
                    if tool_dia < float(size) and tool_dia != 0.0:
                        dia_list.append(tool_dia)
                        for geo_el in elem['apertures'][apid]['geometry']:
                            if 'solid' in geo_el.keys():
                                geo = geo_el['solid']
                                pt = geo.representative_point()
                                points_list.append((pt.x, pt.y))
                except Exception as e:
                    # An exception  will be raised for the 'size' key in case of apertures of type AM (macro) which does
                    # not have the size key
                    pass

            obj_violations['name'] = name
            obj_violations['size'] = dia_list
            obj_violations['points'] = points_list
            violations.append(deepcopy(obj_violations))
        return rule, violations

    @staticmethod
    def check_gerber_annular_ring(obj_list, size, rule):
        rule_title = rule

        violations = list()
        obj_violations = dict()
        obj_violations.update({
            'name': '',
            'points': list()
        })

        # added it so I won't have errors of using before declaring
        gerber_obj = dict()
        gerber_extra_obj = dict()
        exc_obj = dict()
        exc_extra_obj = dict()

        if len(obj_list) == 2:
            gerber_obj = obj_list[0]
            exc_obj = obj_list[1]
            if 'apertures' in gerber_obj and 'tools' in exc_obj:
                pass
            else:
                return 'Fail. At least one Gerber and one Excellon object is required to check Minimum Annular Ring'
        elif len(obj_list) == 3:
            o1 = obj_list[0]
            o2 = obj_list[1]
            o3 = obj_list[2]
            if 'apertures' in o1 and 'apertures' in o2:
                gerber_obj = o1
                gerber_extra_obj = o2
                exc_obj = o3
            elif 'tools' in o2 and 'tools' in o3:
                gerber_obj = o1
                exc_obj = o2
                exc_extra_obj = o3
        elif len(obj_list) == 4:
            gerber_obj = obj_list[0]
            gerber_extra_obj = obj_list[1]
            exc_obj = obj_list[2]
            exc_extra_obj = obj_list[3]
        else:
            return 'Fail. Not enough objects to check Minimum Annular Ring'

        total_geo_grb = list()
        for apid in gerber_obj['apertures']:
            if 'geometry' in gerber_obj['apertures'][apid]:
                geometry = gerber_obj['apertures'][apid]['geometry']
                for geo_el in geometry:
                    if 'solid' in geo_el and geo_el['solid'] is not None:
                        total_geo_grb.append(geo_el['solid'])

        if len(obj_list) == 3 and gerber_extra_obj:
            # add the second Gerber geometry to the first one if it exists
            for apid in gerber_extra_obj['apertures']:
                if 'geometry' in gerber_extra_obj['apertures'][apid]:
                    geometry = gerber_extra_obj['apertures'][apid]['geometry']
                    for geo_el in geometry:
                        if 'solid' in geo_el and geo_el['solid'] is not None:
                            total_geo_grb.append(geo_el['solid'])

        total_geo_grb = MultiPolygon(total_geo_grb)
        total_geo_grb = total_geo_grb.buffer(0)

        total_geo_exc = list()
        for tool in exc_obj['tools']:
            if 'solid_geometry' in exc_obj['tools'][tool]:
                geometry = exc_obj['tools'][tool]['solid_geometry']
                for geo in geometry:
                    total_geo_exc.append(geo)

        if len(obj_list) == 3 and exc_extra_obj:
            # add the second Excellon geometry to the first one if it exists
            for tool in exc_extra_obj['tools']:
                if 'solid_geometry' in exc_extra_obj['tools'][tool]:
                    geometry = exc_extra_obj['tools'][tool]['solid_geometry']
                    for geo in geometry:
                        total_geo_exc.append(geo)

        if isinstance(total_geo_grb, Polygon):
            len_1 = 1
            total_geo_grb = [total_geo_grb]
        else:
            len_1 = len(total_geo_grb)

        if isinstance(total_geo_exc, Polygon):
            len_2 = 1
            total_geo_exc = [total_geo_exc]
        else:
            len_2 = len(total_geo_exc)

        iterations = len_1 * len_2
        log.debug("RulesCheck.check_gerber_annular_ring(). Iterations: %s" % str(iterations))

        min_dict = dict()
        dist = None
        for geo in total_geo_grb:
            for s_geo in total_geo_exc:
                try:
                    # minimize the number of distances by not taking into considerations those that are too small
                    dist = abs(geo.exterior.distance(s_geo))
                except Exception as e:
                    log.debug("RulesCheck.check_gerber_annular_ring() --> %s" % str(e))

                if dist > 0:
                    if float(dist) < float(size):
                        loc_1, loc_2 = nearest_points(geo.exterior, s_geo)

                        dx = loc_1.x - loc_2.x
                        dy = loc_1.y - loc_2.y
                        loc = min(loc_1.x, loc_2.x) + (abs(dx) / 2), min(loc_1.y, loc_2.y) + (abs(dy) / 2)

                        if dist in min_dict:
                            min_dict[dist].append(loc)
                        else:
                            min_dict[dist] = [loc]
                else:
                    if dist in min_dict:
                        min_dict[dist].append(s_geo.representative_point())
                    else:
                        min_dict[dist] = [s_geo.representative_point()]

        points_list = list()
        for dist in min_dict.keys():
            for location in min_dict[dist]:
                points_list.append(location)

        name_list = list()
        try:
            if gerber_obj:
                name_list.append(gerber_obj['name'])
        except KeyError:
            pass
        try:
            if gerber_extra_obj:
                name_list.append(gerber_extra_obj['name'])
        except KeyError:
            pass

        try:
            if exc_obj:
                name_list.append(exc_obj['name'])
        except KeyError:
            pass

        try:
            if exc_extra_obj:
                name_list.append(exc_extra_obj['name'])
        except KeyError:
            pass

        obj_violations['name'] = name_list
        obj_violations['points'] = points_list
        violations.append(deepcopy(obj_violations))
        return rule_title, violations

    def execute(self):
        self.results = list()

        log.debug("RuleCheck() executing")

        def worker_job(app_obj):
            self.app.proc_container.new(_("Working..."))

            # RULE: Check Trace Size
            if self.trace_size_cb.get_value():
                copper_list = list()
                copper_name_1 = self.copper_t_object.currentText()
                if copper_name_1 is not '' and self.copper_t_cb.get_value():
                    elem_dict = dict()
                    elem_dict['name'] = deepcopy(copper_name_1)
                    elem_dict['apertures'] = deepcopy(self.app.collection.get_by_name(copper_name_1).apertures)
                    copper_list.append(elem_dict)

                copper_name_2 = self.copper_b_object.currentText()
                if copper_name_2 is not '' and self.copper_b_cb.get_value():
                    elem_dict = dict()
                    elem_dict['name'] = deepcopy(copper_name_2)
                    elem_dict['apertures'] = deepcopy(self.app.collection.get_by_name(copper_name_2).apertures)
                    copper_list.append(elem_dict)

                trace_size = float(self.trace_size_entry.get_value())
                self.results.append(self.pool.apply_async(self.check_traces_size, args=(copper_list, trace_size)))

            # RULE: Check Copper to Copper Clearance
            if self.clearance_copper2copper_cb.get_value():

                try:
                    copper_copper_clearance = float(self.clearance_copper2copper_entry.get_value())
                except Exception as e:
                    log.debug("RulesCheck.execute.worker_job() --> %s" % str(e))
                    self.app.inform.emit('[ERROR_NOTCL] %s. %s' % (
                        _("Copper to Copper clearance"),
                        _("Value is not valid.")))
                    return

                if self.copper_t_cb.get_value():
                    copper_t_obj = self.copper_t_object.currentText()
                    copper_t_dict = dict()

                    if copper_t_obj is not '':
                        copper_t_dict['name'] = deepcopy(copper_t_obj)
                        copper_t_dict['apertures'] = deepcopy(self.app.collection.get_by_name(copper_t_obj).apertures)

                        self.results.append(self.pool.apply_async(self.check_inside_gerber_clearance,
                                                                  args=(copper_t_dict,
                                                                        copper_copper_clearance,
                                                                        _("TOP -> Copper to Copper clearance"))))
                if self.copper_b_cb.get_value():
                    copper_b_obj = self.copper_b_object.currentText()
                    copper_b_dict = dict()
                    if copper_b_obj is not '':
                        copper_b_dict['name'] = deepcopy(copper_b_obj)
                        copper_b_dict['apertures'] = deepcopy(self.app.collection.get_by_name(copper_b_obj).apertures)

                        self.results.append(self.pool.apply_async(self.check_inside_gerber_clearance,
                                                                  args=(copper_b_dict,
                                                                        copper_copper_clearance,
                                                                        _("BOTTOM -> Copper to Copper clearance"))))

                if self.copper_t_cb.get_value() is False and self.copper_b_cb.get_value() is False:
                    self.app.inform.emit('[ERROR_NOTCL] %s. %s' % (
                        _("Copper to Copper clearance"),
                        _("At least one Gerber object has to be selected for this rule but none is selected.")))
                    return

            # RULE: Check Copper to Outline Clearance
            if self.clearance_copper2ol_cb.get_value() and self.out_cb.get_value():
                top_dict = dict()
                bottom_dict = dict()
                outline_dict = dict()

                copper_top = self.copper_t_object.currentText()
                if copper_top is not '' and self.copper_t_cb.get_value():
                    top_dict['name'] = deepcopy(copper_top)
                    top_dict['apertures'] = deepcopy(self.app.collection.get_by_name(copper_top).apertures)

                copper_bottom = self.copper_b_object.currentText()
                if copper_bottom is not '' and self.copper_b_cb.get_value():
                    bottom_dict['name'] = deepcopy(copper_bottom)
                    bottom_dict['apertures'] = deepcopy(self.app.collection.get_by_name(copper_bottom).apertures)

                copper_outline = self.outline_object.currentText()
                if copper_outline is not '' and self.out_cb.get_value():
                    outline_dict['name'] = deepcopy(copper_outline)
                    outline_dict['apertures'] = deepcopy(self.app.collection.get_by_name(copper_outline).apertures)

                try:
                    copper_outline_clearance = float(self.clearance_copper2ol_entry.get_value())
                except Exception as e:
                    log.debug("RulesCheck.execute.worker_job() --> %s" % str(e))
                    self.app.inform.emit('[ERROR_NOTCL] %s. %s' % (
                        _("Copper to Outline clearance"),
                        _("Value is not valid.")))
                    return

                if not top_dict and not bottom_dict or not outline_dict:
                    self.app.inform.emit('[ERROR_NOTCL] %s. %s' % (
                        _("Copper to Outline clearance"),
                        _("One of the copper Gerber objects or the Outline Gerber object is not valid.")))
                    return
                objs = []
                if top_dict:
                    objs.append(top_dict)
                if bottom_dict:
                    objs.append(bottom_dict)

                if outline_dict:
                    objs.append(outline_dict)
                else:
                    self.app.inform.emit('[ERROR_NOTCL] %s. %s' % (
                        _("Copper to Outline clearance"),
                        _("Outline Gerber object presence is mandatory for this rule but it is not selected.")))
                    return

                self.results.append(self.pool.apply_async(self.check_gerber_clearance,
                                                          args=(objs,
                                                                copper_outline_clearance,
                                                                _("Copper to Outline clearance"))))

            # RULE: Check Silk to Silk Clearance
            if self.clearance_silk2silk_cb.get_value():
                silk_dict = dict()

                try:
                    silk_silk_clearance = float(self.clearance_silk2silk_entry.get_value())
                except Exception as e:
                    log.debug("RulesCheck.execute.worker_job() --> %s" % str(e))
                    self.app.inform.emit('[ERROR_NOTCL] %s. %s' % (
                        _("Silk to Silk clearance"),
                        _("Value is not valid.")))
                    return

                if self.ss_t_cb.get_value():
                    silk_obj = self.ss_t_object.currentText()
                    if silk_obj is not '':
                        silk_dict['name'] = deepcopy(silk_obj)
                        silk_dict['apertures'] = deepcopy(self.app.collection.get_by_name(silk_obj).apertures)

                        self.results.append(self.pool.apply_async(self.check_inside_gerber_clearance,
                                                                  args=(silk_dict,
                                                                        silk_silk_clearance,
                                                                        _("TOP -> Silk to Silk clearance"))))
                if self.ss_b_cb.get_value():
                    silk_obj = self.ss_b_object.currentText()
                    if silk_obj is not '':
                        silk_dict['name'] = deepcopy(silk_obj)
                        silk_dict['apertures'] = deepcopy(self.app.collection.get_by_name(silk_obj).apertures)

                        self.results.append(self.pool.apply_async(self.check_inside_gerber_clearance,
                                                                  args=(silk_dict,
                                                                        silk_silk_clearance,
                                                                        _("BOTTOM -> Silk to Silk clearance"))))

                if self.ss_t_cb.get_value() is False and self.ss_b_cb.get_value() is False:
                    self.app.inform.emit('[ERROR_NOTCL] %s. %s' % (
                        _("Silk to Silk clearance"),
                        _("At least one Gerber object has to be selected for this rule but none is selected.")))
                    return

            # RULE: Check Silk to Solder Mask Clearance
            if self.clearance_silk2sm_cb.get_value():
                silk_t_dict = dict()
                sm_t_dict = dict()
                silk_b_dict = dict()
                sm_b_dict = dict()

                top_ss = False
                bottom_ss = False
                top_sm = False
                bottom_sm = False

                silk_top = self.ss_t_object.currentText()
                if silk_top is not '' and self.ss_t_cb.get_value():
                    silk_t_dict['name'] = deepcopy(silk_top)
                    silk_t_dict['apertures'] = deepcopy(self.app.collection.get_by_name(silk_top).apertures)
                    top_ss = True

                silk_bottom = self.ss_b_object.currentText()
                if silk_bottom is not '' and self.ss_b_cb.get_value():
                    silk_b_dict['name'] = deepcopy(silk_bottom)
                    silk_b_dict['apertures'] = deepcopy(self.app.collection.get_by_name(silk_bottom).apertures)
                    bottom_ss = True

                sm_top = self.sm_t_object.currentText()
                if sm_top is not '' and self.sm_t_cb.get_value():
                    sm_t_dict['name'] = deepcopy(sm_top)
                    sm_t_dict['apertures'] = deepcopy(self.app.collection.get_by_name(sm_top).apertures)
                    top_sm = True

                sm_bottom = self.sm_b_object.currentText()
                if sm_bottom is not '' and self.sm_b_cb.get_value():
                    sm_b_dict['name'] = deepcopy(sm_bottom)
                    sm_b_dict['apertures'] = deepcopy(self.app.collection.get_by_name(sm_bottom).apertures)
                    bottom_sm = True

                try:
                    silk_sm_clearance = float(self.clearance_silk2sm_entry.get_value())
                except Exception as e:
                    log.debug("RulesCheck.execute.worker_job() --> %s" % str(e))
                    self.app.inform.emit('[ERROR_NOTCL] %s. %s' % (
                        _("Silk to Solder Mask Clearance"),
                        _("Value is not valid.")))
                    return

                if (not silk_t_dict and not silk_b_dict) or (not sm_t_dict and not sm_b_dict):
                    self.app.inform.emit('[ERROR_NOTCL] %s. %s' % (
                        _("Silk to Solder Mask Clearance"),
                        _("One or more of the Gerber objects is not valid.")))
                    return

                if top_ss is True and top_sm is True:
                    objs = [silk_t_dict, sm_t_dict]
                    self.results.append(self.pool.apply_async(self.check_gerber_clearance,
                                                              args=(objs,
                                                                    silk_sm_clearance,
                                                                    _("TOP -> Silk to Solder Mask Clearance"))))
                elif bottom_ss is True and bottom_sm is True:
                    objs = [silk_b_dict, sm_b_dict]
                    self.results.append(self.pool.apply_async(self.check_gerber_clearance,
                                                              args=(objs,
                                                                    silk_sm_clearance,
                                                                    _("BOTTOM -> Silk to Solder Mask Clearance"))))
                else:
                    self.app.inform.emit('[ERROR_NOTCL] %s. %s' % (
                        _("Silk to Solder Mask Clearance"),
                        _("Both Silk and Solder Mask Gerber objects has to be either both Top or both Bottom.")))
                    return

            # RULE: Check Silk to Outline Clearance
            if self.clearance_silk2ol_cb.get_value():
                top_dict = dict()
                bottom_dict = dict()
                outline_dict = dict()

                silk_top = self.ss_t_object.currentText()
                if silk_top is not '' and self.ss_t_cb.get_value():
                    top_dict['name'] = deepcopy(silk_top)
                    top_dict['apertures'] = deepcopy(self.app.collection.get_by_name(silk_top).apertures)

                silk_bottom = self.ss_b_object.currentText()
                if silk_bottom is not '' and self.ss_b_cb.get_value():
                    bottom_dict['name'] = deepcopy(silk_bottom)
                    bottom_dict['apertures'] = deepcopy(self.app.collection.get_by_name(silk_bottom).apertures)

                copper_outline = self.outline_object.currentText()
                if copper_outline is not '' and self.out_cb.get_value():
                    outline_dict['name'] = deepcopy(copper_outline)
                    outline_dict['apertures'] = deepcopy(self.app.collection.get_by_name(copper_outline).apertures)

                try:
                    copper_outline_clearance = float(self.clearance_copper2ol_entry.get_value())
                except Exception as e:
                    log.debug("RulesCheck.execute.worker_job() --> %s" % str(e))
                    self.app.inform.emit('[ERROR_NOTCL] %s. %s' % (
                        _("Silk to Outline Clearance"),
                        _("Value is not valid.")))
                    return

                if not top_dict and not bottom_dict or not outline_dict:
                    self.app.inform.emit('[ERROR_NOTCL] %s. %s' % (
                        _("Silk to Outline Clearance"),
                        _("One of the Silk Gerber objects or the Outline Gerber object is not valid.")))
                    return

                objs = []
                if top_dict:
                    objs.append(top_dict)
                if bottom_dict:
                    objs.append(bottom_dict)

                if outline_dict:
                    objs.append(outline_dict)
                else:
                    self.app.inform.emit('[ERROR_NOTCL] %s. %s' % (
                        _("Silk to Outline Clearance"),
                        _("Outline Gerber object presence is mandatory for this rule but it is not selected.")))
                    return

                self.results.append(self.pool.apply_async(self.check_gerber_clearance,
                                                          args=(objs,
                                                                copper_outline_clearance,
                                                                _("Silk to Outline Clearance"))))

            # RULE: Check Minimum Solder Mask Sliver
            if self.clearance_silk2silk_cb.get_value():
                sm_dict = dict()

                try:
                    sm_sm_clearance = float(self.clearance_sm2sm_entry.get_value())
                except Exception as e:
                    log.debug("RulesCheck.execute.worker_job() --> %s" % str(e))
                    self.app.inform.emit('[ERROR_NOTCL] %s. %s' % (
                        _("Minimum Solder Mask Sliver"),
                        _("Value is not valid.")))
                    return

                if self.sm_t_cb.get_value():
                    solder_obj = self.sm_t_object.currentText()
                    if solder_obj is not '':
                        sm_dict['name'] = deepcopy(solder_obj)
                        sm_dict['apertures'] = deepcopy(self.app.collection.get_by_name(solder_obj).apertures)

                        self.results.append(self.pool.apply_async(self.check_inside_gerber_clearance,
                                                                  args=(sm_dict,
                                                                        sm_sm_clearance,
                                                                        _("TOP -> Minimum Solder Mask Sliver"))))
                if self.sm_b_cb.get_value():
                    solder_obj = self.sm_b_object.currentText()
                    if solder_obj is not '':
                        sm_dict['name'] = deepcopy(solder_obj)
                        sm_dict['apertures'] = deepcopy(self.app.collection.get_by_name(solder_obj).apertures)

                        self.results.append(self.pool.apply_async(self.check_inside_gerber_clearance,
                                                                  args=(sm_dict,
                                                                        sm_sm_clearance,
                                                                        _("BOTTOM -> Minimum Solder Mask Sliver"))))

                if self.sm_t_cb.get_value() is False and self.sm_b_cb.get_value() is False:
                    self.app.inform.emit('[ERROR_NOTCL] %s. %s' % (
                        _("Minimum Solder Mask Sliver"),
                        _("At least one Gerber object has to be selected for this rule but none is selected.")))
                    return

            # RULE: Check Minimum Annular Ring
            if self.ring_integrity_cb.get_value():
                top_dict = dict()
                bottom_dict = dict()
                exc_1_dict = dict()
                exc_2_dict = dict()

                copper_top = self.copper_t_object.currentText()
                if copper_top is not '' and self.copper_t_cb.get_value():
                    top_dict['name'] = deepcopy(copper_top)
                    top_dict['apertures'] = deepcopy(self.app.collection.get_by_name(copper_top).apertures)

                copper_bottom = self.copper_b_object.currentText()
                if copper_bottom is not '' and self.copper_b_cb.get_value():
                    bottom_dict['name'] = deepcopy(copper_bottom)
                    bottom_dict['apertures'] = deepcopy(self.app.collection.get_by_name(copper_bottom).apertures)

                excellon_1 = self.e1_object.currentText()
                if excellon_1 is not '' and self.e1_cb.get_value():
                    exc_1_dict['name'] = deepcopy(excellon_1)
                    exc_1_dict['tools'] = deepcopy(
                        self.app.collection.get_by_name(excellon_1).tools)

                excellon_2 = self.e2_object.currentText()
                if excellon_2 is not '' and self.e2_cb.get_value():
                    exc_2_dict['name'] = deepcopy(excellon_2)
                    exc_2_dict['tools'] = deepcopy(
                        self.app.collection.get_by_name(excellon_2).tools)

                try:
                    ring_val = float(self.ring_integrity_entry.get_value())
                except Exception as e:
                    log.debug("RulesCheck.execute.worker_job() --> %s" % str(e))
                    self.app.inform.emit('[ERROR_NOTCL] %s. %s' % (
                        _("Minimum Annular Ring"),
                        _("Value is not valid.")))
                    return

                if (not top_dict and not bottom_dict) or (not exc_1_dict and not exc_2_dict):
                    self.app.inform.emit('[ERROR_NOTCL] %s. %s' % (
                        _("Minimum Annular Ring"),
                        _("One of the Copper Gerber objects or the Excellon objects is not valid.")))
                    return

                objs = []
                if top_dict:
                    objs.append(top_dict)
                elif bottom_dict:
                    objs.append(bottom_dict)

                if exc_1_dict:
                    objs.append(exc_1_dict)
                elif exc_2_dict:
                    objs.append(exc_2_dict)
                else:
                    self.app.inform.emit('[ERROR_NOTCL] %s. %s' % (
                        _("Minimum Annular Ring"),
                        _("Excellon object presence is mandatory for this rule but none is selected.")))
                    return

                self.results.append(self.pool.apply_async(self.check_gerber_annular_ring,
                                                          args=(objs,
                                                                ring_val,
                                                                _("Minimum Annular Ring"))))

            # RULE: Check Hole to Hole Clearance
            if self.clearance_d2d_cb.get_value():
                exc_list = list()
                exc_name_1 = self.e1_object.currentText()
                if exc_name_1 is not '' and self.e1_cb.get_value():
                    elem_dict = dict()
                    elem_dict['name'] = deepcopy(exc_name_1)
                    elem_dict['tools'] = deepcopy(self.app.collection.get_by_name(exc_name_1).tools)
                    exc_list.append(elem_dict)

                exc_name_2 = self.e2_object.currentText()
                if exc_name_2 is not '' and self.e2_cb.get_value():
                    elem_dict = dict()
                    elem_dict['name'] = deepcopy(exc_name_2)
                    elem_dict['tools'] = deepcopy(self.app.collection.get_by_name(exc_name_2).tools)
                    exc_list.append(elem_dict)

                hole_clearance = float(self.clearance_d2d_entry.get_value())
                self.results.append(self.pool.apply_async(self.check_holes_clearance, args=(exc_list, hole_clearance)))

            # RULE: Check Holes Size
            if self.drill_size_cb.get_value():
                exc_list = list()
                exc_name_1 = self.e1_object.currentText()
                if exc_name_1 is not '' and self.e1_cb.get_value():
                    elem_dict = dict()
                    elem_dict['name'] = deepcopy(exc_name_1)
                    elem_dict['tools'] = deepcopy(self.app.collection.get_by_name(exc_name_1).tools)
                    exc_list.append(elem_dict)

                exc_name_2 = self.e2_object.currentText()
                if exc_name_2 is not '' and self.e2_cb.get_value():
                    elem_dict = dict()
                    elem_dict['name'] = deepcopy(exc_name_2)
                    elem_dict['tools'] = deepcopy(self.app.collection.get_by_name(exc_name_2).tools)
                    exc_list.append(elem_dict)

                drill_size = float(self.drill_size_entry.get_value())
                self.results.append(self.pool.apply_async(self.check_holes_size, args=(exc_list, drill_size)))

            output = list()
            for p in self.results:
                output.append(p.get())

            self.tool_finished.emit(output)

            log.debug("RuleCheck() finished")

        self.app.worker_task.emit({'fcn': worker_job, 'params': [self.app]})

    def on_tool_finished(self, res):
        def init(new_obj, app_obj):
            txt = ''
            for el in res:
                txt += '<b>RULE NAME:</b>&nbsp;&nbsp;&nbsp;&nbsp;%s<BR>' % str(el[0]).upper()
                if isinstance(el[1][0]['name'], list):
                    for name in el[1][0]['name']:
                        txt += 'File name: %s<BR>' % str(name)
                else:
                    txt += 'File name: %s<BR>' % str(el[1][0]['name'])

                point_txt = ''
                try:
                    if el[1][0]['points']:
                        txt += '{title}: <span style="color:{color};background-color:{h_color}"' \
                               '>&nbsp;{status} </span>.<BR>'.format(title=_("STATUS"),
                                                                     h_color='red',
                                                                     color='white',
                                                                     status=_("FAILED"))
                        if 'Failed' in el[1][0]['points'][0]:
                            point_txt = el[1][0]['points'][0]
                        else:
                            for pt in el[1][0]['points']:
                                point_txt += '(%.*f, %.*f)' % (self.decimals, float(pt[0]), self.decimals, float(pt[1]))
                                point_txt += ', '
                        txt += 'Violations: %s<BR>' % str(point_txt)
                    else:
                        txt += '{title}: <span style="color:{color};background-color:{h_color}"' \
                               '>&nbsp;{status} </span>.<BR>'.format(title=_("STATUS"),
                                                                     h_color='green',
                                                                     color='white',
                                                                     status=_("PASSED"))
                        txt += '%s<BR>' % _("Violations: There are no violations for the current rule.")
                except KeyError:
                    pass

                try:
                    if el[1][0]['dia']:
                        txt += '{title}: <span style="color:{color};background-color:{h_color}"' \
                               '>&nbsp;{status} </span>.<BR>'.format(title=_("STATUS"),
                                                                     h_color='red',
                                                                     color='white',
                                                                     status=_("FAILED"))
                        if 'Failed' in el[1][0]['dia']:
                            point_txt = el[1][0]['dia']
                        else:
                            for pt in el[1][0]['dia']:
                                point_txt += '%.*f' % (self.decimals, float(pt))
                                point_txt += ', '
                        txt += 'Violations: %s<BR>' % str(point_txt)
                    else:
                        txt += '{title}: <span style="color:{color};background-color:{h_color}"' \
                               '>&nbsp;{status} </span>.<BR>'.format(title=_("STATUS"),
                                                                     h_color='green',
                                                                     color='white',
                                                                     status=_("PASSED"))
                        txt += '%s<BR>' % _("Violations: There are no violations for the current rule.")
                except KeyError:
                    pass

                txt += '<BR><BR>'
            new_obj.source_file = txt
            new_obj.read_only = True

        self.app.new_object('document', name='Rules Check results', initialize=init, plot=False)

    def reset_fields(self):
        # self.object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        # self.box_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        pass
