
from PyQt5 import QtWidgets, QtCore

from FlatCAMTool import FlatCAMTool
from flatcamGUI.GUIElements import RadioSet, FCDoubleSpinner, EvalEntry, FCEntry
from FlatCAMObj import FlatCAMGerber, FlatCAMExcellon, FlatCAMGeometry

from numpy import Inf

from shapely.geometry import Point
from shapely import affinity

import logging
import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class ToolExtractDrills(FlatCAMTool):

    toolName = _("Extract Drills")

    def __init__(self, app):
        FlatCAMTool.__init__(self, app)
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

        self.empty_lb = QtWidgets.QLabel("")
        self.layout.addWidget(self.empty_lb)

        # ## Grid Layout
        grid_lay = QtWidgets.QGridLayout()
        self.layout.addLayout(grid_lay)
        grid_lay.setColumnStretch(0, 1)
        grid_lay.setColumnStretch(1, 0)

        # ## Gerber Object
        self.gerber_object_combo = QtWidgets.QComboBox()
        self.gerber_object_combo.setModel(self.app.collection)
        self.gerber_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.gerber_object_combo.setCurrentIndex(1)

        self.grb_label = QtWidgets.QLabel("<b>%s:</b>" % _("GERBER"))
        self.grb_label.setToolTip('%s.' % _("Gerber from which to extract drill holes"))

        # grid_lay.addRow("Bottom Layer:", self.object_combo)
        grid_lay.addWidget(self.grb_label, 0, 0)
        grid_lay.addWidget(self.gerber_object_combo, 1, 0)

        # ## Grid Layout
        grid1 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid1)
        grid1.setColumnStretch(0, 0)
        grid1.setColumnStretch(1, 1)

        # ## Axis
        self.hole_size_radio = RadioSet([{'label': _("Fixed"), 'value': 'fixed'},
                                         {'label': _("Proportional"), 'value': 'prop'}])
        self.hole_size_label = QtWidgets.QLabel('%s:' % _("Hole Size"))
        self.hole_size_label.setToolTip(
            _("The type of hole size. Can be:\n"
              "- Fixed -> all holes will have a set size\n"
              "- Proprotional -> each hole will havea a variable size\n"
              "such as to preserve a set annular ring"))

        grid1.addWidget(self.hole_size_label, 3, 0)
        grid1.addWidget(self.hole_size_radio, 3, 1)

        # grid_lay1.addWidget(QtWidgets.QLabel(''))

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid1.addWidget(separator_line, 5, 0, 1, 2)

        # Diameter value
        self.dia_entry = FCDoubleSpinner()
        self.dia_entry.set_precision(self.decimals)
        self.dia_entry.set_range(0.0000, 9999.9999)

        self.dia_label = QtWidgets.QLabel('%s:' % _("Diameter"))
        self.dia_label.setToolTip(
            _("Fixed hole diameter.")
        )

        grid1.addWidget(self.dia_label, 7, 0)
        grid1.addWidget(self.dia_entry, 7, 1)

        # Annular Ring value
        self.ring_entry = FCDoubleSpinner()
        self.ring_entry.set_precision(self.decimals)
        self.ring_entry.set_range(0.0000, 9999.9999)

        self.ring_label = QtWidgets.QLabel('%s:' % _("Annular Ring"))
        self.ring_label.setToolTip(
            _("The size of annular ring.\n"
              "The copper sliver between the drill hole exterior\n"
              "and the margin of the copper pad.")
        )

        grid1.addWidget(self.ring_label, 8, 0)
        grid1.addWidget(self.ring_entry, 8, 1)

        # Calculate Bounding box
        self.e_drills_button = QtWidgets.QPushButton(_("Extract Drills"))
        self.e_drills_button.setToolTip(
            _("Extract drills from a given Gerber file.")
        )
        self.e_drills_button.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        self.layout.addWidget(self.e_drills_button)

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

        # ## Signals
        self.hole_size_radio.activated_custom.connect(self.on_hole_size_toggle)
        self.e_drills_button.clicked.connect(self.on_extract_drills_click)
        self.reset_button.clicked.connect(self.set_tool_ui)

        self.tools = list()
        self.drills = dict()

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, shortcut='ALT+E', **kwargs)

    def run(self, toggle=True):
        self.app.report_usage("Extract Drills()")

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

        self.app.ui.notebook.setTabText(2, _("Extract Drills Tool"))

    def set_tool_ui(self):
        self.reset_fields()

        self.hole_size_radio.set_value(self.app.defaults["tools_edrills_hole_type"])

        self.dia_entry.set_value(float(self.app.defaults["tools_edrills_hole_fixed_dia"]))
        self.ring_entry.set_value(float(self.app.defaults["tools_edrills_hole_ring"]))

    def on_extract_drills_click(self):
        selection_index = self.gerber_object_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.gerber_object_combo.rootModelIndex())

        try:
            fcobj = model_index.internalPointer().obj
        except Exception as e:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Gerber object loaded ..."))
            return

        # axis = self.mirror_axis.get_value()
        # mode = self.axis_location.get_value()
        #
        # if mode == "point":
        #     try:
        #         px, py = self.point_entry.get_value()
        #     except TypeError:
        #         self.app.inform.emit('[WARNING_NOTCL] %s' % _("'Point' coordinates missing. "
        #                                                       "Using Origin (0, 0) as mirroring reference."))
        #         px, py = (0, 0)
        #
        # else:
        #     selection_index_box = self.box_combo.currentIndex()
        #     model_index_box = self.app.collection.index(selection_index_box, 0, self.box_combo.rootModelIndex())
        #     try:
        #         bb_obj = model_index_box.internalPointer().obj
        #     except Exception as e:
        #         self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Box object loaded ..."))
        #         return
        #
        #     xmin, ymin, xmax, ymax = bb_obj.bounds()
        #     px = 0.5 * (xmin + xmax)
        #     py = 0.5 * (ymin + ymax)
        #
        # fcobj.mirror(axis, [px, py])
        # self.app.object_changed.emit(fcobj)
        # fcobj.plot()
        self.app.inform.emit('[success] Gerber %s %s...' % (str(fcobj.options['name']), _("was mirrored")))

    def on_hole_size_toggle(self, val):
        if val == "fixed":
            self.dia_entry.setDisabled(False)
            self.dia_label.setDisabled(False)

            self.ring_label.setDisabled(True)
            self.ring_entry.setDisabled(True)
        else:
            self.dia_entry.setDisabled(True)
            self.dia_label.setDisabled(True)

            self.ring_label.setDisabled(False)
            self.ring_entry.setDisabled(False)

    def reset_fields(self):
        self.gerber_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.gerber_object_combo.setCurrentIndex(0)
