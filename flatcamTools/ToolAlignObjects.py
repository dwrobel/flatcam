# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 1/13/2020                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtGui, QtCore
from FlatCAMTool import FlatCAMTool

from flatcamGUI.GUIElements import FCComboBox

from copy import deepcopy

import numpy as np

from shapely.geometry import Point

import gettext
import FlatCAMTranslation as fcTranslate
import builtins
import logging

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class AlignObjects(FlatCAMTool):

    toolName = _("Align Objects")

    def __init__(self, app):
        FlatCAMTool.__init__(self, app)

        self.app = app
        self.decimals = app.decimals

        self.canvas = self.app.plotcanvas

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
        grid0 = QtWidgets.QGridLayout()
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        self.layout.addLayout(grid0)

        self.aligned_label = QtWidgets.QLabel('<b>%s</b>' % _("Selection of the aligned object"))
        grid0.addWidget(self.aligned_label, 0, 0, 1, 2)

        # Type of object to be aligned
        self.type_obj_combo = QtWidgets.QComboBox()
        self.type_obj_combo.addItem("Gerber")
        self.type_obj_combo.addItem("Excellon")
        self.type_obj_combo.addItem("Geometry")

        self.type_obj_combo.setItemIcon(0, QtGui.QIcon(self.app.resource_location + "/flatcam_icon16.png"))
        self.type_obj_combo.setItemIcon(1, QtGui.QIcon(self.app.resource_location + "/drill16.png"))
        self.type_obj_combo.setItemIcon(2, QtGui.QIcon(self.app.resource_location + "/geometry16.png"))

        self.type_obj_combo_label = QtWidgets.QLabel('%s:' % _("Object Type"))
        self.type_obj_combo_label.setToolTip(
            _("Specify the type of object to be aligned.\n"
              "It can be of type: Gerber, Excellon or Geometry.\n"
              "The selection here decide the type of objects that will be\n"
              "in the Object combobox.")
        )
        grid0.addWidget(self.type_obj_combo_label, 2, 0)
        grid0.addWidget(self.type_obj_combo, 2, 1)

        # Object to be aligned
        self.object_combo = QtWidgets.QComboBox()
        self.object_combo.setModel(self.app.collection)
        self.object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.object_combo.setCurrentIndex(1)

        self.object_label = QtWidgets.QLabel('%s:' % _("Object"))
        self.object_label.setToolTip(
            _("Object to be aligned.")
        )

        grid0.addWidget(self.object_label, 3, 0)
        grid0.addWidget(self.object_combo, 3, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 4, 0, 1, 2)

        self.aligned_label = QtWidgets.QLabel('<b>%s</b>' % _("Selection of the aligner object"))
        self.aligned_label.setToolTip(
            _("Object to which the other objects will be aligned to (moved).")
        )
        grid0.addWidget(self.aligned_label, 6, 0, 1, 2)

        # Type of object to be aligned to = aligner
        self.type_aligner_obj_combo = QtWidgets.QComboBox()
        self.type_aligner_obj_combo.addItem("Gerber")
        self.type_aligner_obj_combo.addItem("Excellon")
        self.type_aligner_obj_combo.addItem("Geometry")

        self.type_aligner_obj_combo.setItemIcon(0, QtGui.QIcon(self.app.resource_location + "/flatcam_icon16.png"))
        self.type_aligner_obj_combo.setItemIcon(1, QtGui.QIcon(self.app.resource_location + "/drill16.png"))
        self.type_aligner_obj_combo.setItemIcon(2, QtGui.QIcon(self.app.resource_location + "/geometry16.png"))

        self.type_aligner_obj_combo_label = QtWidgets.QLabel('%s:' % _("Object Type"))
        self.type_aligner_obj_combo_label.setToolTip(
            _("Specify the type of object to be aligned to.\n"
              "It can be of type: Gerber, Excellon or Geometry.\n"
              "The selection here decide the type of objects that will be\n"
              "in the Object combobox.")
        )
        grid0.addWidget(self.type_aligner_obj_combo_label, 7, 0)
        grid0.addWidget(self.type_aligner_obj_combo, 7, 1)

        # Object to be aligned to = aligner
        self.aligner_object_combo = QtWidgets.QComboBox()
        self.aligner_object_combo.setModel(self.app.collection)
        self.aligner_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.aligner_object_combo.setCurrentIndex(1)

        self.aligner_object_label = QtWidgets.QLabel('%s:' % _("Object"))
        self.aligner_object_label.setToolTip(
            _("Object to be aligned to. Aligner.")
        )

        grid0.addWidget(self.aligner_object_label, 8, 0)
        grid0.addWidget(self.aligner_object_combo, 8, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 9, 0, 1, 2)

        # Buttons
        self.align_object_button = QtWidgets.QPushButton(_("Align Object"))
        self.align_object_button.setToolTip(
            _("Align the specified object to the aligner object.\n"
              "If only one point is used then it assumes translation.\n"
              "If tho points are used it assume translation and rotation.")
        )
        self.align_object_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)
        self.layout.addWidget(self.align_object_button)

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

        # Signals
        self.align_object_button.clicked.connect(self.on_align)
        self.type_obj_combo.currentIndexChanged.connect(self.on_type_obj_index_changed)
        self.type_aligner_obj_combo.currentIndexChanged.connect(self.on_type_aligner_index_changed)
        self.reset_button.clicked.connect(self.set_tool_ui)

        self.mr = None

        # if the mouse events are connected to a local method set this True
        self.local_connected = False

        # store the status of the grid
        self.grid_status_memory = None

        self.aligned_obj = None
        self.aligner_obj = None

        # here store the alignment points for the aligned object
        self.aligned_clicked_points = list()

        # here store the alignment points for the aligner object
        self.aligner_clicked_points = list()

        # counter for the clicks
        self.click_cnt = 0

    def run(self, toggle=True):
        self.app.report_usage("ToolAlignObjects()")

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

        self.app.ui.notebook.setTabText(2, _("Align Tool"))

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, shortcut='ALT+A', **kwargs)

    def set_tool_ui(self):
        self.reset_fields()

        self.click_cnt = 0

        if self.local_connected is True:
            self.disconnect_cal_events()

    def on_type_obj_index_changed(self):
        obj_type = self.type_obj_combo.currentIndex()
        self.object_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.object_combo.setCurrentIndex(0)

    def on_type_aligner_index_changed(self):
        obj_type = self.type_aligner_obj_combo.currentIndex()
        self.aligner_object_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.aligner_object_combo.setCurrentIndex(0)

    def on_align(self):

        obj_sel_index = self.object_combo.currentIndex()
        obj_model_index = self.app.collection.index(obj_sel_index, 0, self.object_combo.rootModelIndex())
        try:
            self.aligned_obj = obj_model_index.internalPointer().obj
        except AttributeError:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no aligned FlatCAM object selected..."))
            return

        aligner_obj_sel_index = self.object_combo.currentIndex()
        aligner_obj_model_index = self.app.collection.index(
            aligner_obj_sel_index, 0, self.object_combo.rootModelIndex())

        try:
            self.aligner_obj = aligner_obj_model_index.internalPointer().obj
        except AttributeError:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no aligner FlatCAM object selected..."))
            return

        # disengage the grid snapping since it will be hard to find the drills or pads on grid
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

        self.app.inform.emit(_("Get First alignment point on the aligned object."))

    def on_mouse_click_release(self, event):
        if self.app.is_legacy is False:
            event_pos = event.pos
            right_button = 2
            self.app.event_is_dragging = self.app.event_is_dragging
        else:
            event_pos = (event.xdata, event.ydata)
            right_button = 3
            self.app.event_is_dragging = self.app.ui.popMenu.mouse_is_panning

        pos_canvas = self.canvas.translate_coords(event_pos)

        if event.button == 1:
            click_pt = Point([pos_canvas[0], pos_canvas[1]])

            if self.app.selection_type is not None:
                # delete previous selection shape
                self.app.delete_selection_shape()
                self.app.selection_type = None
            else:
                if self.target_obj.kind.lower() == 'excellon':
                    for tool, tool_dict in self.target_obj.tools.items():
                        for geo in tool_dict['solid_geometry']:
                            if click_pt.within(geo):
                                center_pt = geo.centroid
                                self.click_points.append(
                                    [
                                        float('%.*f' % (self.decimals, center_pt.x)),
                                        float('%.*f' % (self.decimals, center_pt.y))
                                    ]
                                )
                                self.check_points()
                elif self.target_obj.kind.lower() == 'gerber':
                    for apid, apid_val in self.target_obj.apertures.items():
                        for geo_el in apid_val['geometry']:
                            if 'solid' in geo_el:
                                if click_pt.within(geo_el['solid']):
                                    if isinstance(geo_el['follow'], Point):
                                        center_pt = geo_el['solid'].centroid
                                        self.click_points.append(
                                            [
                                                float('%.*f' % (self.decimals, center_pt.x)),
                                                float('%.*f' % (self.decimals, center_pt.y))
                                            ]
                                        )
                                        self.check_points()

        elif event.button == right_button and self.app.event_is_dragging is False:
            if not len(self.click_points):
                self.reset_calibration_points()
                self.disconnect_cal_events()
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled by user request."))

    def check_points(self):
        if len(self.aligned_click_points) == 1:
            self.app.inform.emit(_("Get Second alignment point on aligned object. "
                                   "Or right click to get First alignment point on the aligner object."))

        if len(self.aligned_click_points) == 2:
            self.app.inform.emit(_("Get First alignment point on the aligner object."))

        if len(self.aligner_click_points) == 1:
            self.app.inform.emit(_("Get Second alignment point on the aligner object. Or right click to finish."))
            self.align_translate()
            self.align_rotate()
            self.disconnect_cal_events()

    def align_translate(self):
        pass

    def align_rotate(self):
        pass

    def execute(self):
        aligned_name = self.object_combo.currentText()

        # Get source object.
        try:
            aligned_obj = self.app.collection.get_by_name(str(aligned_name))
        except Exception as e:
            log.debug("AlignObjects.on_align() --> %s" % str(e))
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), aligned_name))
            return "Could not retrieve object: %s" % aligned_name

        if aligned_obj is None:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Object not found"), aligned_obj))
            return "Object not found: %s" % aligned_obj

        aligner_name = self.box_combo.currentText()

        try:
            aligner_obj = self.app.collection.get_by_name(aligner_name)
        except Exception as e:
            log.debug("AlignObjects.on_align() --> %s" % str(e))
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), aligner_name))
            return "Could not retrieve object: %s" % aligner_name

        if aligner_obj is None:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), aligner_name))

        def align_job():
            pass

        proc = self.app.proc_container.new(_("Working..."))

        def job_thread(app_obj):
            try:
                align_job()
                app_obj.inform.emit('[success] %s' % _("Panel created successfully."))
            except Exception as ee:
                proc.done()
                log.debug(str(ee))
                return
            proc.done()

        self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})

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
        self.click_cnt = 0

    def reset_fields(self):
        self.object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.aligner_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
