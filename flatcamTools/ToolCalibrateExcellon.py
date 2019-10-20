# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtCore
from FlatCAMTool import FlatCAMTool
from flatcamGUI.GUIElements import FCDoubleSpinner, EvalEntry
import math
from shapely.geometry import Point
from shapely.geometry.base import *

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


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
        grid_lay = QtWidgets.QGridLayout()
        self.layout.addLayout(grid_lay)
        grid_lay.setColumnStretch(0, 0)
        grid_lay.setColumnStretch(1, 1)
        grid_lay.setColumnStretch(2, 1)

        self.exc_object_combo = QtWidgets.QComboBox()
        self.exc_object_combo.setModel(self.app.collection)
        self.exc_object_combo.setRootModelIndex(self.app.collection.index(1, 0, QtCore.QModelIndex()))
        self.exc_object_combo.setCurrentIndex(1)

        self.excobj_label = QtWidgets.QLabel("<b>%s:</b>" % _("EXCELLON"))
        self.excobj_label.setToolTip(
            _("Excellon Object to be mirrored.")
        )

        grid_lay.addWidget(self.excobj_label, 0, 0)
        grid_lay.addWidget(self.exc_object_combo, 0, 1, 1, 2)
        grid_lay.addWidget(QtWidgets.QLabel(''), 1, 0)

        self.points_table_label = QtWidgets.QLabel('<b>%s</b>' % _('Calibration Points'))
        self.points_table_label.setToolTip(
            _("Contain the expected calibration points and the\n"
              "ones measured.")
        )
        grid_lay.addWidget(self.points_table_label, 2, 0, 1, 2)

        # BOTTOM LEFT
        self.bottom_left_lbl = QtWidgets.QLabel('<b>%s</b>' % _('Bottom Left'))
        grid_lay.addWidget(self.bottom_left_lbl, 3, 0)
        self.bottom_left_tgt_lbl = QtWidgets.QLabel('%s' % _('Target'))
        grid_lay.addWidget(self.bottom_left_tgt_lbl, 3, 1)
        self.bottom_left_found_lbl = QtWidgets.QLabel('%s' % _('Found'))
        grid_lay.addWidget(self.bottom_left_found_lbl, 3, 2)

        self.bottom_left_coordx_lbl = QtWidgets.QLabel('%s' % _('X'))
        grid_lay.addWidget(self.bottom_left_coordx_lbl, 4, 0)
        self.bottom_left_coordx_tgt = EvalEntry()
        self.bottom_left_coordx_tgt.setDisabled(True)
        grid_lay.addWidget(self.bottom_left_coordx_tgt, 4, 1)
        self.bottom_left_coordx_found = EvalEntry()
        grid_lay.addWidget(self.bottom_left_coordx_found, 4, 2)

        self.bottom_left_coordy_lbl = QtWidgets.QLabel('%s' % _('Y'))
        grid_lay.addWidget(self.bottom_left_coordy_lbl, 5, 0)
        self.bottom_left_coordy_tgt = EvalEntry()
        self.bottom_left_coordy_tgt.setDisabled(True)
        grid_lay.addWidget(self.bottom_left_coordy_tgt, 5, 1)
        self.bottom_left_coordy_found = EvalEntry()
        grid_lay.addWidget(self.bottom_left_coordy_found, 5, 2)

        grid_lay.addWidget(QtWidgets.QLabel(''), 6, 0)
        self.bottom_left_coordx_found.set_value(_('Set Origin'))
        self.bottom_left_coordy_found.set_value(_('Set Origin'))
        self.bottom_left_coordx_found.setDisabled(True)
        self.bottom_left_coordy_found.setDisabled(True)

        # BOTTOM RIGHT
        self.bottom_right_lbl = QtWidgets.QLabel('<b>%s</b>' % _('Bottom Right'))
        grid_lay.addWidget(self.bottom_right_lbl, 7, 0)
        self.bottom_right_tgt_lbl = QtWidgets.QLabel('%s' % _('Target'))
        grid_lay.addWidget(self.bottom_right_tgt_lbl, 7, 1)
        self.bottom_right_found_lbl = QtWidgets.QLabel('%s' % _('Found'))
        grid_lay.addWidget(self.bottom_right_found_lbl, 7, 2)

        self.bottom_right_coordx_lbl = QtWidgets.QLabel('%s' % _('X'))
        grid_lay.addWidget(self.bottom_right_coordx_lbl, 8, 0)
        self.bottom_right_coordx_tgt = EvalEntry()
        self.bottom_right_coordx_tgt.setDisabled(True)
        grid_lay.addWidget(self.bottom_right_coordx_tgt, 8, 1)
        self.bottom_right_coordx_found = EvalEntry()
        grid_lay.addWidget(self.bottom_right_coordx_found, 8, 2)

        self.bottom_right_coordy_lbl = QtWidgets.QLabel('%s' % _('Y'))
        grid_lay.addWidget(self.bottom_right_coordy_lbl, 9, 0)
        self.bottom_right_coordy_tgt = EvalEntry()
        self.bottom_right_coordy_tgt.setDisabled(True)
        grid_lay.addWidget(self.bottom_right_coordy_tgt, 9, 1)
        self.bottom_right_coordy_found = EvalEntry()
        grid_lay.addWidget(self.bottom_right_coordy_found, 9, 2)

        grid_lay.addWidget(QtWidgets.QLabel(''), 10, 0)

        # TOP LEFT
        self.top_left_lbl = QtWidgets.QLabel('<b>%s</b>' % _('Top Left'))
        grid_lay.addWidget(self.top_left_lbl, 11, 0)
        self.top_left_tgt_lbl = QtWidgets.QLabel('%s' % _('Target'))
        grid_lay.addWidget(self.top_left_tgt_lbl, 11, 1)
        self.top_left_found_lbl = QtWidgets.QLabel('%s' % _('Found'))
        grid_lay.addWidget(self.top_left_found_lbl, 11, 2)

        self.top_left_coordx_lbl = QtWidgets.QLabel('%s' % _('X'))
        grid_lay.addWidget(self.top_left_coordx_lbl, 12, 0)
        self.top_left_coordx_tgt = EvalEntry()
        self.top_left_coordx_tgt.setDisabled(True)
        grid_lay.addWidget(self.top_left_coordx_tgt, 12, 1)
        self.top_left_coordx_found = EvalEntry()
        grid_lay.addWidget(self.top_left_coordx_found, 12, 2)

        self.top_left_coordy_lbl = QtWidgets.QLabel('%s' % _('Y'))
        grid_lay.addWidget(self.top_left_coordy_lbl, 13, 0)
        self.top_left_coordy_tgt = EvalEntry()
        self.top_left_coordy_tgt.setDisabled(True)
        grid_lay.addWidget(self.top_left_coordy_tgt, 13, 1)
        self.top_left_coordy_found = EvalEntry()
        grid_lay.addWidget(self.top_left_coordy_found, 13, 2)

        grid_lay.addWidget(QtWidgets.QLabel(''), 14, 0)

        # TOP RIGHT
        self.top_right_lbl = QtWidgets.QLabel('<b>%s</b>' % _('Top Right'))
        grid_lay.addWidget(self.top_right_lbl, 15, 0)
        self.top_right_tgt_lbl = QtWidgets.QLabel('%s' % _('Target'))
        grid_lay.addWidget(self.top_right_tgt_lbl, 15, 1)
        self.top_right_found_lbl = QtWidgets.QLabel('%s' % _('Found'))
        grid_lay.addWidget(self.top_right_found_lbl, 15, 2)

        self.top_right_coordx_lbl = QtWidgets.QLabel('%s' % _('X'))
        grid_lay.addWidget(self.top_right_coordx_lbl, 16, 0)
        self.top_right_coordx_tgt = EvalEntry()
        self.top_right_coordx_tgt.setDisabled(True)
        grid_lay.addWidget(self.top_right_coordx_tgt, 16, 1)
        self.top_right_coordx_found = EvalEntry()
        grid_lay.addWidget(self.top_right_coordx_found, 16, 2)

        self.top_right_coordy_lbl = QtWidgets.QLabel('%s' % _('Y'))
        grid_lay.addWidget(self.top_right_coordy_lbl, 17, 0)
        self.top_right_coordy_tgt = EvalEntry()
        self.top_right_coordy_tgt.setDisabled(True)
        grid_lay.addWidget(self.top_right_coordy_tgt, 17, 1)
        self.top_right_coordy_found = EvalEntry()
        grid_lay.addWidget(self.top_right_coordy_found, 17, 2)

        grid_lay.addWidget(QtWidgets.QLabel(''), 18, 0)

        # ## Buttons
        self.start_button = QtWidgets.QPushButton(_("Start"))
        self.start_button.setToolTip(
            _("Start to collect four drill center coordinates,\n  "
              "to be used as references. ")
        )

        self.layout.addWidget(self.start_button)

        self.layout.addStretch()

        self.mr = None
        self.units = ''

        # here store 4 points to be used for calibration
        self.click_points = list()

        self.exc_obj = None

        # ## Signals
        self.start_button.clicked.connect(self.on_start_collect_points)

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
        self.units = self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().upper()

        # ## Initialize form
        # self.mm_entry.set_value('%.*f' % (self.decimals, 0))

    def on_start_collect_points(self):
        self.mr = self.canvas.graph_event_connect('mouse_release', self.on_mouse_click_release)

        if self.app.is_legacy is False:
            self.canvas.graph_event_disconnect('mouse_release', self.app.on_mouse_click_release_over_plot)
        else:
            self.canvas.graph_event_disconnect(self.app.mr)

        selection_index = self.exc_object_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.exc_object_combo.rootModelIndex())
        try:
            self.exc_obj = model_index.internalPointer().obj
        except Exception as e:
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

    def disconnect_cal_events(self):
        self.app.mr = self.canvas.graph_event_connect('mouse_release', self.app.on_mouse_click_release_over_plot)

        if self.app.is_legacy is False:
            self.canvas.graph_event_disconnect('mouse_release', self.on_mouse_click_release)
        else:
            self.canvas.graph_event_disconnect(self.mr)

    def reset_fields(self):
        self.exc_object_combo.setRootModelIndex(self.app.collection.index(1, 0, QtCore.QModelIndex()))

# end of file
