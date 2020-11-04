# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtGui, QtCore
from appTool import AppTool
from appGUI.GUIElements import FCDoubleSpinner, FCCheckBox, FCButton, OptionalInputSection, FCComboBox, \
    NumericalEvalTupleEntry, FCLabel

import numpy as np

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ToolTransform(AppTool):

    def __init__(self, app):
        AppTool.__init__(self, app)
        self.decimals = self.app.decimals

        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = TransformUI(layout=self.layout, app=self.app)
        self.toolName = self.ui.toolName
        
        # ## Signals
        self.ui.ref_combo.currentIndexChanged.connect(self.ui.on_reference_changed)
        self.ui.type_obj_combo.currentIndexChanged.connect(self.on_type_obj_index_changed)
        self.ui.point_button.clicked.connect(self.on_add_coords)

        self.ui.rotate_button.clicked.connect(self.on_rotate)

        self.ui.skewx_button.clicked.connect(self.on_skewx)
        self.ui.skewy_button.clicked.connect(self.on_skewy)

        self.ui.scalex_button.clicked.connect(self.on_scalex)
        self.ui.scaley_button.clicked.connect(self.on_scaley)

        self.ui.offx_button.clicked.connect(self.on_offx)
        self.ui.offy_button.clicked.connect(self.on_offy)

        self.ui.flipx_button.clicked.connect(self.on_flipx)
        self.ui.flipy_button.clicked.connect(self.on_flipy)

        self.ui.buffer_button.clicked.connect(self.on_buffer_by_distance)
        self.ui.buffer_factor_button.clicked.connect(self.on_buffer_by_factor)

        self.ui.reset_button.clicked.connect(self.set_tool_ui)

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolTransform()")

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

        AppTool.run(self)
        self.set_tool_ui()

        self.app.ui.notebook.setTabText(2, _("Transform Tool"))

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Alt+T', **kwargs)

    def set_tool_ui(self):

        # ## Initialize form
        self.ui.ref_combo.set_value(self.app.defaults["tools_transform_reference"])
        self.ui.type_obj_combo.set_value(self.app.defaults["tools_transform_ref_object"])
        self.ui.point_entry.set_value(self.app.defaults["tools_transform_ref_point"])
        self.ui.rotate_entry.set_value(self.app.defaults["tools_transform_rotate"])

        self.ui.skewx_entry.set_value(self.app.defaults["tools_transform_skew_x"])
        self.ui.skewy_entry.set_value(self.app.defaults["tools_transform_skew_y"])
        self.ui.skew_link_cb.set_value(self.app.defaults["tools_transform_skew_link"])

        self.ui.scalex_entry.set_value(self.app.defaults["tools_transform_scale_x"])
        self.ui.scaley_entry.set_value(self.app.defaults["tools_transform_scale_y"])
        self.ui.scale_link_cb.set_value(self.app.defaults["tools_transform_scale_link"])

        self.ui.offx_entry.set_value(self.app.defaults["tools_transform_offset_x"])
        self.ui.offy_entry.set_value(self.app.defaults["tools_transform_offset_y"])

        self.ui.buffer_entry.set_value(self.app.defaults["tools_transform_buffer_dis"])
        self.ui.buffer_factor_entry.set_value(self.app.defaults["tools_transform_buffer_factor"])
        self.ui.buffer_rounded_cb.set_value(self.app.defaults["tools_transform_buffer_corner"])

        # initial state is hidden
        self.ui.point_label.hide()
        self.ui.point_entry.hide()
        self.ui.point_button.hide()

        self.ui.type_object_label.hide()
        self.ui.type_obj_combo.hide()
        self.ui.object_combo.hide()

    def on_type_obj_index_changed(self, index):
        self.ui.object_combo.setRootModelIndex(self.app.collection.index(index, 0, QtCore.QModelIndex()))
        self.ui.object_combo.setCurrentIndex(0)
        self.ui.object_combo.obj_type = {
            _("Gerber"): "Gerber", _("Excellon"): "Excellon", _("Geometry"): "Geometry"
        }[self.ui.type_obj_combo.get_value()]

    def on_calculate_reference(self):
        ref_val = self.ui.ref_combo.currentIndex()

        if ref_val == 0:    # "Origin" reference
            return 0, 0
        elif ref_val == 1:  # "Selection" reference
            sel_list = self.app.collection.get_selected()
            if sel_list:
                xmin, ymin, xmax, ymax = self.alt_bounds(obj_list=sel_list)
                px = (xmax + xmin) * 0.5
                py = (ymax + ymin) * 0.5
                return px, py
            else:
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("No object is selected."))
                return "fail"
        elif ref_val == 2:  # "Point" reference
            point_val = self.uipoint_entry.get_value()
            try:
                px, py = eval('{}'.format(point_val))
                return px, py
            except Exception:
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("Incorrect format for Point value. Needs format X,Y"))
                return "fail"
        else:               # "Object" reference
            obj_name = self.ui.object_combo.get_value()
            ref_obj = self.app.collection.get_by_name(obj_name)
            xmin, ymin, xmax, ymax = ref_obj.bounds()
            px = (xmax + xmin) * 0.5
            py = (ymax + ymin) * 0.5
            return px, py

    def on_add_coords(self):
        val = self.app.clipboard.text()
        self.ui.point_entry.set_value(val)

    def on_rotate(self):
        value = float(self.ui.rotate_entry.get_value())
        if value == 0:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Rotate transformation can not be done for a value of 0."))
            return
        point = self.on_calculate_reference()
        if point == 'fail':
            return
        self.app.worker_task.emit({'fcn': self.on_rotate_action, 'params': [value, point]})

    def on_flipx(self):
        axis = 'Y'
        point = self.on_calculate_reference()
        if point == 'fail':
            return
        self.app.worker_task.emit({'fcn': self.on_flip, 'params': [axis, point]})

    def on_flipy(self):
        axis = 'X'
        point = self.on_calculate_reference()
        if point == 'fail':
            return
        self.app.worker_task.emit({'fcn': self.on_flip, 'params': [axis, point]})

    def on_skewx(self):
        xvalue = float(self.ui.skewx_entry.get_value())

        if xvalue == 0:
            return

        if self.ui.skew_link_cb.get_value():
            yvalue = xvalue
        else:
            yvalue = 0

        axis = 'X'
        point = self.on_calculate_reference()
        if point == 'fail':
            return

        self.app.worker_task.emit({'fcn': self.on_skew, 'params': [axis, xvalue, yvalue, point]})

    def on_skewy(self):
        xvalue = 0
        yvalue = float(self.ui.skewy_entry.get_value())

        if yvalue == 0:
            return

        axis = 'Y'
        point = self.on_calculate_reference()
        if point == 'fail':
            return

        self.app.worker_task.emit({'fcn': self.on_skew, 'params': [axis, xvalue, yvalue, point]})

    def on_scalex(self):
        xvalue = float(self.ui.scalex_entry.get_value())

        if xvalue == 0 or xvalue == 1:
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("Scale transformation can not be done for a factor of 0 or 1."))
            return

        if self.ui.scale_link_cb.get_value():
            yvalue = xvalue
        else:
            yvalue = 1

        axis = 'X'
        point = self.on_calculate_reference()
        if point == 'fail':
            return

        self.app.worker_task.emit({'fcn': self.on_scale, 'params': [axis, xvalue, yvalue, point]})

    def on_scaley(self):
        xvalue = 1
        yvalue = float(self.ui.scaley_entry.get_value())

        if yvalue == 0 or yvalue == 1:
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("Scale transformation can not be done for a factor of 0 or 1."))
            return

        axis = 'Y'
        point = self.on_calculate_reference()
        if point == 'fail':
            return

        self.app.worker_task.emit({'fcn': self.on_scale, 'params': [axis, xvalue, yvalue, point]})

    def on_offx(self):
        value = float(self.ui.offx_entry.get_value())
        if value == 0:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Offset transformation can not be done for a value of 0."))
            return
        axis = 'X'

        self.app.worker_task.emit({'fcn': self.on_offset, 'params': [axis, value]})

    def on_offy(self):
        value = float(self.ui.offy_entry.get_value())
        if value == 0:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Offset transformation can not be done for a value of 0."))
            return
        axis = 'Y'

        self.app.worker_task.emit({'fcn': self.on_offset, 'params': [axis, value]})

    def on_buffer_by_distance(self):
        value = self.ui.buffer_entry.get_value()
        join = 1 if self.ui.buffer_rounded_cb.get_value() else 2

        self.app.worker_task.emit({'fcn': self.on_buffer_action, 'params': [value, join]})

    def on_buffer_by_factor(self):
        value = 1 + self.ui.buffer_factor_entry.get_value() / 100.0
        join = 1 if self.ui.buffer_rounded_cb.get_value() else 2

        # tell the buffer method to use the factor
        factor = True

        self.app.worker_task.emit({'fcn': self.on_buffer_action, 'params': [value, join, factor]})

    def on_rotate_action(self, num, point):
        obj_list = self.app.collection.get_selected()

        if not obj_list:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("No object is selected."))
            return
        else:
            with self.app.proc_container.new(_("Appying Rotate")):
                try:
                    px, py = point
                    for sel_obj in obj_list:
                        if sel_obj.kind == 'cncjob':
                            self.app.inform.emit(_("CNCJob objects can't be rotated."))
                        else:
                            sel_obj.rotate(-num, point=(px, py))
                            self.app.app_obj.object_changed.emit(sel_obj)

                        # add information to the object that it was changed and how much
                        sel_obj.options['rotate'] = num
                        sel_obj.plot()
                    self.app.inform.emit('[success] %s...' % _('Rotate done'))
                except Exception as e:
                    self.app.inform.emit('[ERROR_NOTCL] %s: %s.' % (_("Action was not executed"), str(e)))
                    return

    def on_flip(self, axis, point):
        obj_list = self.app.collection.get_selected()

        if not obj_list:
            self.app.inform.emit('[WARNING_NOTCL] %s!' % _("No object is selected."))
            return
        else:
            with self.app.proc_container.new(_("Applying Flip")):
                try:
                    px, py = point

                    # execute mirroring
                    for sel_obj in obj_list:
                        if sel_obj.kind == 'cncjob':
                            self.app.inform.emit(_("CNCJob objects can't be mirrored/flipped."))
                        else:
                            if axis == 'X':
                                sel_obj.mirror('X', (px, py))
                                # add information to the object that it was changed and how much
                                # the axis is reversed because of the reference
                                if 'mirror_y' in sel_obj.options:
                                    sel_obj.options['mirror_y'] = not sel_obj.options['mirror_y']
                                else:
                                    sel_obj.options['mirror_y'] = True
                                self.app.inform.emit('[success] %s...' % _('Flip on Y axis done'))
                            elif axis == 'Y':
                                sel_obj.mirror('Y', (px, py))
                                # add information to the object that it was changed and how much
                                # the axis is reversed because of the reference
                                if 'mirror_x' in sel_obj.options:
                                    sel_obj.options['mirror_x'] = not sel_obj.options['mirror_x']
                                else:
                                    sel_obj.options['mirror_x'] = True
                                self.app.inform.emit('[success] %s...' % _('Flip on X axis done'))
                            self.app.app_obj.object_changed.emit(sel_obj)
                        sel_obj.plot()
                except Exception as e:
                    self.app.inform.emit('[ERROR_NOTCL] %s: %s.' % (_("Action was not executed"), str(e)))
                    return

    def on_skew(self, axis, xvalue, yvalue, point):
        obj_list = self.app.collection.get_selected()

        if xvalue in [90, 180] or yvalue in [90, 180] or xvalue == yvalue == 0:
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("Skew transformation can not be done for 0, 90 and 180 degrees."))
            return

        if not obj_list:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("No object is selected."))
            return
        else:
            with self.app.proc_container.new(_("Applying Skew")):
                try:
                    px, py = point

                    for sel_obj in obj_list:
                        if sel_obj.kind == 'cncjob':
                            self.app.inform.emit(_("CNCJob objects can't be skewed."))
                        else:
                            sel_obj.skew(xvalue, yvalue, point=(px, py))
                            # add information to the object that it was changed and how much
                            sel_obj.options['skew_x'] = xvalue
                            sel_obj.options['skew_y'] = yvalue
                            self.app.app_obj.object_changed.emit(sel_obj)
                        sel_obj.plot()
                    self.app.inform.emit('[success] %s %s %s...' % (_('Skew on the'),  str(axis), _("axis done")))
                except Exception as e:
                    self.app.inform.emit('[ERROR_NOTCL] %s: %s.' % (_("Action was not executed"), str(e)))
                    return

    def on_scale(self, axis, xfactor, yfactor, point=None):
        obj_list = self.app.collection.get_selected()

        if not obj_list:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("No object is selected."))
            return
        else:
            with self.app.proc_container.new(_("Applying Scale")):
                try:
                    px, py = point

                    for sel_obj in obj_list:
                        if sel_obj.kind == 'cncjob':
                            self.app.inform.emit(_("CNCJob objects can't be scaled."))
                        else:
                            sel_obj.scale(xfactor, yfactor, point=(px, py))
                            # add information to the object that it was changed and how much
                            sel_obj.options['scale_x'] = xfactor
                            sel_obj.options['scale_y'] = yfactor
                            self.app.app_obj.object_changed.emit(sel_obj)
                        sel_obj.plot()

                    self.app.inform.emit('[success] %s %s %s...' % (_('Scale on the'), str(axis), _('axis done')))
                except Exception as e:
                    self.app.inform.emit('[ERROR_NOTCL] %s: %s.' % (_("Action was not executed"), str(e)))
                    return

    def on_offset(self, axis, num):
        obj_list = self.app.collection.get_selected()

        if not obj_list:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("No object is selected."))
            return
        else:
            with self.app.proc_container.new(_("Applying Offset")):
                try:
                    for sel_obj in obj_list:
                        if sel_obj.kind == 'cncjob':
                            self.app.inform.emit(_("CNCJob objects can't be offset."))
                        else:
                            if axis == 'X':
                                sel_obj.offset((num, 0))
                                # add information to the object that it was changed and how much
                                sel_obj.options['offset_x'] = num
                            elif axis == 'Y':
                                sel_obj.offset((0, num))
                                # add information to the object that it was changed and how much
                                sel_obj.options['offset_y'] = num
                            self.app.app_obj.object_changed.emit(sel_obj)
                        sel_obj.plot()

                    self.app.inform.emit('[success] %s %s %s...' % (_('Offset on the'), str(axis), _('axis done')))
                except Exception as e:
                    self.app.inform.emit('[ERROR_NOTCL] %s: %s.' % (_("Action was not executed"), str(e)))
                    return

    def on_buffer_action(self, value, join, factor=None):
        obj_list = self.app.collection.get_selected()

        if not obj_list:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("No object is selected."))
            return
        else:
            with self.app.proc_container.new(_("Applying Buffer")):
                try:
                    for sel_obj in obj_list:
                        if sel_obj.kind == 'cncjob':
                            self.app.inform.emit(_("CNCJob objects can't be buffered."))
                        elif sel_obj.kind.lower() == 'gerber':
                            sel_obj.buffer(value, join, factor)
                            sel_obj.source_file = self.app.f_handlers.export_gerber(obj_name=sel_obj.options['name'],
                                                                                    filename=None, local_use=sel_obj,
                                                                                    use_thread=False)
                        elif sel_obj.kind.lower() == 'excellon':
                            sel_obj.buffer(value, join, factor)
                            sel_obj.source_file = self.app.f_handlers.export_excellon(obj_name=sel_obj.options['name'],
                                                                                      filename=None, local_use=sel_obj,
                                                                                      use_thread=False)
                        elif sel_obj.kind.lower() == 'geometry':
                            sel_obj.buffer(value, join, factor)

                        self.app.app_obj.object_changed.emit(sel_obj)
                        sel_obj.plot()

                    self.app.inform.emit('[success] %s...' % _('Buffer done'))

                except Exception as e:
                    self.app.log.debug("ToolTransform.on_buffer_action() --> %s" % str(e))
                    self.app.inform.emit('[ERROR_NOTCL] %s: %s.' % (_("Action was not executed"), str(e)))
                    return

    @staticmethod
    def alt_bounds(obj_list):
        """
        Returns coordinates of rectangular bounds
        of an object with geometry: (xmin, ymin, xmax, ymax).
        """

        def bounds_rec(lst):
            minx = np.Inf
            miny = np.Inf
            maxx = -np.Inf
            maxy = -np.Inf

            try:
                for obj in lst:
                    if obj.kind != 'cncjob':
                        minx_, miny_, maxx_, maxy_ = bounds_rec(obj)
                        minx = min(minx, minx_)
                        miny = min(miny, miny_)
                        maxx = max(maxx, maxx_)
                        maxy = max(maxy, maxy_)
                return minx, miny, maxx, maxy
            except TypeError:
                # it's an object, return it's bounds
                return lst.bounds()

        return bounds_rec(obj_list)


class TransformUI:
    
    toolName = _("Object Transform")
    rotateName = _("Rotate")
    skewName = _("Skew/Shear")
    scaleName = _("Scale")
    flipName = _("Mirror (Flip)")
    offsetName = _("Offset")
    bufferName = _("Buffer")

    def __init__(self, layout, app):
        self.app = app
        self.decimals = self.app.decimals
        self.layout = layout

        # ## Title
        title_label = FCLabel("%s" % self.toolName)
        title_label.setStyleSheet("""
                                QLabel
                                {
                                    font-size: 16px;
                                    font-weight: bold;
                                }
                                """)
        self.layout.addWidget(title_label)
        self.layout.addWidget(FCLabel(""))

        # ## Layout
        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        grid0.setColumnStretch(2, 0)

        grid0.addWidget(FCLabel(''))

        # Reference
        ref_label = FCLabel('%s:' % _("Reference"))
        ref_label.setToolTip(
            _("The reference point for Rotate, Skew, Scale, Mirror.\n"
              "Can be:\n"
              "- Origin -> it is the 0, 0 point\n"
              "- Selection -> the center of the bounding box of the selected objects\n"
              "- Point -> a custom point defined by X,Y coordinates\n"
              "- Object -> the center of the bounding box of a specific object")
        )
        self.ref_combo = FCComboBox()
        self.ref_items = [_("Origin"), _("Selection"), _("Point"), _("Object")]
        self.ref_combo.addItems(self.ref_items)

        grid0.addWidget(ref_label, 0, 0)
        grid0.addWidget(self.ref_combo, 0, 1, 1, 2)

        self.point_label = FCLabel('%s:' % _("Value"))
        self.point_label.setToolTip(
            _("A point of reference in format X,Y.")
        )
        self.point_entry = NumericalEvalTupleEntry()

        grid0.addWidget(self.point_label, 1, 0)
        grid0.addWidget(self.point_entry, 1, 1, 1, 2)

        self.point_button = FCButton(_("Add"))
        self.point_button.setToolTip(
            _("Add point coordinates from clipboard.")
        )
        grid0.addWidget(self.point_button, 2, 0, 1, 3)

        # Type of object to be used as reference
        self.type_object_label = FCLabel('%s:' % _("Type"))
        self.type_object_label.setToolTip(
            _("The type of object used as reference.")
        )

        self.type_obj_combo = FCComboBox()
        self.type_obj_combo.addItem(_("Gerber"))
        self.type_obj_combo.addItem(_("Excellon"))
        self.type_obj_combo.addItem(_("Geometry"))

        self.type_obj_combo.setItemIcon(0, QtGui.QIcon(self.app.resource_location + "/flatcam_icon16.png"))
        self.type_obj_combo.setItemIcon(1, QtGui.QIcon(self.app.resource_location + "/drill16.png"))
        self.type_obj_combo.setItemIcon(2, QtGui.QIcon(self.app.resource_location + "/geometry16.png"))

        grid0.addWidget(self.type_object_label, 3, 0)
        grid0.addWidget(self.type_obj_combo, 3, 1, 1, 2)

        # Object to be used as reference
        self.object_combo = FCComboBox()
        self.object_combo.setModel(self.app.collection)
        self.object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.object_combo.is_last = True

        self.object_combo.setToolTip(
            _("The object used as reference.\n"
              "The used point is the center of it's bounding box.")
        )
        grid0.addWidget(self.object_combo, 4, 0, 1, 3)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 5, 0, 1, 3)

        # ## Rotate Title
        rotate_title_label = FCLabel("<font size=3><b>%s</b></font>" % self.rotateName)
        grid0.addWidget(rotate_title_label, 6, 0, 1, 3)

        self.rotate_label = FCLabel('%s:' % _("Angle"))
        self.rotate_label.setToolTip(
            _("Angle, in degrees.\n"
              "Float number between -360 and 359.\n"
              "Positive numbers for CW motion.\n"
              "Negative numbers for CCW motion.")
        )

        self.rotate_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.rotate_entry.set_precision(self.decimals)
        self.rotate_entry.setSingleStep(45)
        self.rotate_entry.setWrapping(True)
        self.rotate_entry.set_range(-360, 360)

        # self.rotate_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.rotate_button = FCButton(_("Rotate"))
        self.rotate_button.setToolTip(
            _("Rotate the selected object(s).\n"
              "The point of reference is the middle of\n"
              "the bounding box for all selected objects.")
        )
        self.rotate_button.setMinimumWidth(90)

        grid0.addWidget(self.rotate_label, 7, 0)
        grid0.addWidget(self.rotate_entry, 7, 1)
        grid0.addWidget(self.rotate_button, 7, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 8, 0, 1, 3)

        # ## Skew Title
        skew_title_label = FCLabel("<font size=3><b>%s</b></font>" % self.skewName)
        grid0.addWidget(skew_title_label, 9, 0, 1, 2)

        self.skew_link_cb = FCCheckBox()
        self.skew_link_cb.setText(_("Link"))
        self.skew_link_cb.setToolTip(
            _("Link the Y entry to X entry and copy its content.")
        )

        grid0.addWidget(self.skew_link_cb, 9, 2)

        self.skewx_label = FCLabel('%s:' % _("X angle"))
        self.skewx_label.setToolTip(
            _("Angle for Skew action, in degrees.\n"
              "Float number between -360 and 360.")
        )
        self.skewx_entry = FCDoubleSpinner(callback=self.confirmation_message)
        # self.skewx_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.skewx_entry.set_precision(self.decimals)
        self.skewx_entry.set_range(-360, 360)

        self.skewx_button = FCButton(_("Skew X"))
        self.skewx_button.setToolTip(
            _("Skew/shear the selected object(s).\n"
              "The point of reference is the middle of\n"
              "the bounding box for all selected objects."))
        self.skewx_button.setMinimumWidth(90)

        grid0.addWidget(self.skewx_label, 10, 0)
        grid0.addWidget(self.skewx_entry, 10, 1)
        grid0.addWidget(self.skewx_button, 10, 2)

        self.skewy_label = FCLabel('%s:' % _("Y angle"))
        self.skewy_label.setToolTip(
            _("Angle for Skew action, in degrees.\n"
              "Float number between -360 and 360.")
        )
        self.skewy_entry = FCDoubleSpinner(callback=self.confirmation_message)
        # self.skewy_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.skewy_entry.set_precision(self.decimals)
        self.skewy_entry.set_range(-360, 360)

        self.skewy_button = FCButton(_("Skew Y"))
        self.skewy_button.setToolTip(
            _("Skew/shear the selected object(s).\n"
              "The point of reference is the middle of\n"
              "the bounding box for all selected objects."))
        self.skewy_button.setMinimumWidth(90)

        grid0.addWidget(self.skewy_label, 12, 0)
        grid0.addWidget(self.skewy_entry, 12, 1)
        grid0.addWidget(self.skewy_button, 12, 2)

        self.ois_sk = OptionalInputSection(self.skew_link_cb, [self.skewy_label, self.skewy_entry, self.skewy_button],
                                           logic=False)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 14, 0, 1, 3)

        # ## Scale Title
        scale_title_label = FCLabel("<font size=3><b>%s</b></font>" % self.scaleName)
        grid0.addWidget(scale_title_label, 15, 0, 1, 2)

        self.scale_link_cb = FCCheckBox()
        self.scale_link_cb.setText(_("Link"))
        self.scale_link_cb.setToolTip(
            _("Link the Y entry to X entry and copy its content.")
        )

        grid0.addWidget(self.scale_link_cb, 15, 2)

        self.scalex_label = FCLabel('%s:' % _("X factor"))
        self.scalex_label.setToolTip(
            _("Factor for scaling on X axis.")
        )
        self.scalex_entry = FCDoubleSpinner(callback=self.confirmation_message)
        # self.scalex_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.scalex_entry.set_precision(self.decimals)
        self.scalex_entry.setMinimum(-1e6)

        self.scalex_button = FCButton(_("Scale X"))
        self.scalex_button.setToolTip(
            _("Scale the selected object(s).\n"
              "The point of reference depends on \n"
              "the Scale reference checkbox state."))
        self.scalex_button.setMinimumWidth(90)

        grid0.addWidget(self.scalex_label, 17, 0)
        grid0.addWidget(self.scalex_entry, 17, 1)
        grid0.addWidget(self.scalex_button, 17, 2)

        self.scaley_label = FCLabel('%s:' % _("Y factor"))
        self.scaley_label.setToolTip(
            _("Factor for scaling on Y axis.")
        )
        self.scaley_entry = FCDoubleSpinner(callback=self.confirmation_message)
        # self.scaley_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.scaley_entry.set_precision(self.decimals)
        self.scaley_entry.setMinimum(-1e6)

        self.scaley_button = FCButton(_("Scale Y"))
        self.scaley_button.setToolTip(
            _("Scale the selected object(s).\n"
              "The point of reference depends on \n"
              "the Scale reference checkbox state."))
        self.scaley_button.setMinimumWidth(90)

        grid0.addWidget(self.scaley_label, 19, 0)
        grid0.addWidget(self.scaley_entry, 19, 1)
        grid0.addWidget(self.scaley_button, 19, 2)

        self.ois_s = OptionalInputSection(self.scale_link_cb,
                                          [
                                              self.scaley_label,
                                              self.scaley_entry,
                                              self.scaley_button
                                          ], logic=False)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 21, 0, 1, 3)

        # ## Flip Title
        flip_title_label = FCLabel("<font size=3><b>%s</b></font>" % self.flipName)
        grid0.addWidget(flip_title_label, 23, 0, 1, 3)

        self.flipx_button = FCButton(_("Flip on X"))
        self.flipx_button.setToolTip(
            _("Flip the selected object(s) over the X axis.")
        )

        self.flipy_button = FCButton(_("Flip on Y"))
        self.flipy_button.setToolTip(
            _("Flip the selected object(s) over the X axis.")
        )

        hlay0 = QtWidgets.QHBoxLayout()
        grid0.addLayout(hlay0, 25, 0, 1, 3)

        hlay0.addWidget(self.flipx_button)
        hlay0.addWidget(self.flipy_button)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 27, 0, 1, 3)

        # ## Offset Title
        offset_title_label = FCLabel("<font size=3><b>%s</b></font>" % self.offsetName)
        grid0.addWidget(offset_title_label, 29, 0, 1, 3)

        self.offx_label = FCLabel('%s:' % _("X val"))
        self.offx_label.setToolTip(
            _("Distance to offset on X axis. In current units.")
        )
        self.offx_entry = FCDoubleSpinner(callback=self.confirmation_message)
        # self.offx_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.offx_entry.set_precision(self.decimals)
        self.offx_entry.setMinimum(-1e6)

        self.offx_button = FCButton(_("Offset X"))
        self.offx_button.setToolTip(
            _("Offset the selected object(s).\n"
              "The point of reference is the middle of\n"
              "the bounding box for all selected objects.\n"))
        self.offx_button.setMinimumWidth(90)

        grid0.addWidget(self.offx_label, 31, 0)
        grid0.addWidget(self.offx_entry, 31, 1)
        grid0.addWidget(self.offx_button, 31, 2)

        self.offy_label = FCLabel('%s:' % _("Y val"))
        self.offy_label.setToolTip(
            _("Distance to offset on Y axis. In current units.")
        )
        self.offy_entry = FCDoubleSpinner(callback=self.confirmation_message)
        # self.offy_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.offy_entry.set_precision(self.decimals)
        self.offy_entry.setMinimum(-1e6)

        self.offy_button = FCButton(_("Offset Y"))
        self.offy_button.setToolTip(
            _("Offset the selected object(s).\n"
              "The point of reference is the middle of\n"
              "the bounding box for all selected objects.\n"))
        self.offy_button.setMinimumWidth(90)

        grid0.addWidget(self.offy_label, 32, 0)
        grid0.addWidget(self.offy_entry, 32, 1)
        grid0.addWidget(self.offy_button, 32, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 34, 0, 1, 3)

        # ## Buffer Title
        buffer_title_label = FCLabel("<font size=3><b>%s</b></font>" % self.bufferName)
        grid0.addWidget(buffer_title_label, 35, 0, 1, 2)

        self.buffer_rounded_cb = FCCheckBox('%s' % _("Rounded"))
        self.buffer_rounded_cb.setToolTip(
            _("If checked then the buffer will surround the buffered shape,\n"
              "every corner will be rounded.\n"
              "If not checked then the buffer will follow the exact geometry\n"
              "of the buffered shape.")
        )

        grid0.addWidget(self.buffer_rounded_cb, 35, 2)

        self.buffer_label = FCLabel('%s:' % _("Distance"))
        self.buffer_label.setToolTip(
            _("A positive value will create the effect of dilation,\n"
              "while a negative value will create the effect of erosion.\n"
              "Each geometry element of the object will be increased\n"
              "or decreased with the 'distance'.")
        )

        self.buffer_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.buffer_entry.set_precision(self.decimals)
        self.buffer_entry.setSingleStep(0.1)
        self.buffer_entry.setWrapping(True)
        self.buffer_entry.set_range(-10000.0000, 10000.0000)

        self.buffer_button = FCButton(_("Buffer D"))
        self.buffer_button.setToolTip(
            _("Create the buffer effect on each geometry,\n"
              "element from the selected object, using the distance.")
        )
        self.buffer_button.setMinimumWidth(90)

        grid0.addWidget(self.buffer_label, 37, 0)
        grid0.addWidget(self.buffer_entry, 37, 1)
        grid0.addWidget(self.buffer_button, 37, 2)

        self.buffer_factor_label = FCLabel('%s:' % _("Value"))
        self.buffer_factor_label.setToolTip(
            _("A positive value will create the effect of dilation,\n"
              "while a negative value will create the effect of erosion.\n"
              "Each geometry element of the object will be increased\n"
              "or decreased to fit the 'Value'. Value is a percentage\n"
              "of the initial dimension.")
        )

        self.buffer_factor_entry = FCDoubleSpinner(callback=self.confirmation_message, suffix='%')
        self.buffer_factor_entry.set_range(-100.0000, 1000.0000)
        self.buffer_factor_entry.set_precision(self.decimals)
        self.buffer_factor_entry.setWrapping(True)
        self.buffer_factor_entry.setSingleStep(1)

        self.buffer_factor_button = FCButton(_("Buffer F"))
        self.buffer_factor_button.setToolTip(
            _("Create the buffer effect on each geometry,\n"
              "element from the selected object, using the factor.")
        )
        self.buffer_factor_button.setMinimumWidth(90)

        grid0.addWidget(self.buffer_factor_label, 38, 0)
        grid0.addWidget(self.buffer_factor_entry, 38, 1)
        grid0.addWidget(self.buffer_factor_button, 38, 2)

        grid0.addWidget(FCLabel(''), 42, 0, 1, 3)

        self.layout.addStretch()

        # ## Reset Tool
        self.reset_button = FCButton(_("Reset Tool"))
        self.reset_button.setIcon(QtGui.QIcon(self.app.resource_location + '/reset32.png'))
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

        # #################################### FINSIHED GUI ###########################
        # #############################################################################
    
    def on_reference_changed(self, index):
        if index == 0 or index == 1:  # "Origin" or "Selection" reference
            self.point_label.hide()
            self.point_entry.hide()
            self.point_button.hide()

            self.type_object_label.hide()
            self.type_obj_combo.hide()
            self.object_combo.hide()
        elif index == 2:    # "Point" reference
            self.point_label.show()
            self.point_entry.show()
            self.point_button.show()

            self.type_object_label.hide()
            self.type_obj_combo.hide()
            self.object_combo.hide()
        else:   # "Object" reference
            self.point_label.hide()
            self.point_entry.hide()
            self.point_button.hide()

            self.type_object_label.show()
            self.type_obj_combo.show()
            self.object_combo.show()
            
    def confirmation_message(self, accepted, minval, maxval):
        if accepted is False:
            self.app.inform[str, bool].emit('[WARNING_NOTCL] %s: [%.*f, %.*f]' % (_("Edited value is out of range"),
                                                                                  self.decimals,
                                                                                  minval,
                                                                                  self.decimals,
                                                                                  maxval), False)
        else:
            self.app.inform[str, bool].emit('[success] %s' % _("Edited value is within limits."), False)

    def confirmation_message_int(self, accepted, minval, maxval):
        if accepted is False:
            self.app.inform[str, bool].emit('[WARNING_NOTCL] %s: [%d, %d]' %
                                            (_("Edited value is out of range"), minval, maxval), False)
        else:
            self.app.inform[str, bool].emit('[success] %s' % _("Edited value is within limits."), False)
