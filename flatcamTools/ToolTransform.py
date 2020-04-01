# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets
from FlatCAMTool import FlatCAMTool
from flatcamGUI.GUIElements import FCDoubleSpinner, FCCheckBox, FCButton, OptionalInputSection, EvalEntry2
from FlatCAMObj import FlatCAMCNCjob

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ToolTransform(FlatCAMTool):

    toolName = _("Object Transform")
    rotateName = _("Rotate")
    skewName = _("Skew/Shear")
    scaleName = _("Scale")
    flipName = _("Mirror (Flip)")
    offsetName = _("Offset")
    bufferName = _("Buffer")

    def __init__(self, app):
        FlatCAMTool.__init__(self, app)
        self.decimals = self.app.decimals

        self.transform_lay = QtWidgets.QVBoxLayout()
        self.layout.addLayout(self.transform_lay)
        # ## Title
        title_label = QtWidgets.QLabel("%s" % self.toolName)
        title_label.setStyleSheet("""
                        QLabel
                        {
                            font-size: 16px;
                            font-weight: bold;
                        }
                        """)
        self.transform_lay.addWidget(title_label)
        self.transform_lay.addWidget(QtWidgets.QLabel(''))

        # ## Layout
        grid0 = QtWidgets.QGridLayout()
        self.transform_lay.addLayout(grid0)
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        grid0.setColumnStretch(2, 0)

        grid0.addWidget(QtWidgets.QLabel(''))

        # ## Rotate Title
        rotate_title_label = QtWidgets.QLabel("<font size=3><b>%s</b></font>" % self.rotateName)
        grid0.addWidget(rotate_title_label, 0, 0, 1, 3)

        self.rotate_label = QtWidgets.QLabel('%s:' % _("Angle"))
        self.rotate_label.setToolTip(
            _("Angle for Rotation action, in degrees.\n"
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

        self.rotate_button = FCButton()
        self.rotate_button.setToolTip(
            _("Rotate the selected object(s).\n"
              "The point of reference is the middle of\n"
              "the bounding box for all selected objects.")
        )
        self.rotate_button.setMinimumWidth(90)

        grid0.addWidget(self.rotate_label, 1, 0)
        grid0.addWidget(self.rotate_entry, 1, 1)
        grid0.addWidget(self.rotate_button, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 2, 0, 1, 3)

        # ## Skew Title
        skew_title_label = QtWidgets.QLabel("<font size=3><b>%s</b></font>" % self.skewName)
        grid0.addWidget(skew_title_label, 3, 0, 1, 3)

        self.skewx_label = QtWidgets.QLabel('%s:' % _("X angle"))
        self.skewx_label.setToolTip(
            _("Angle for Skew action, in degrees.\n"
              "Float number between -360 and 360.")
        )
        self.skewx_entry = FCDoubleSpinner(callback=self.confirmation_message)
        # self.skewx_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.skewx_entry.set_precision(self.decimals)
        self.skewx_entry.set_range(-360, 360)

        self.skewx_button = FCButton()
        self.skewx_button.setToolTip(
            _("Skew/shear the selected object(s).\n"
              "The point of reference is the middle of\n"
              "the bounding box for all selected objects."))
        self.skewx_button.setMinimumWidth(90)

        grid0.addWidget(self.skewx_label, 4, 0)
        grid0.addWidget(self.skewx_entry, 4, 1)
        grid0.addWidget(self.skewx_button, 4, 2)

        self.skewy_label = QtWidgets.QLabel('%s:' % _("Y angle"))
        self.skewy_label.setToolTip(
            _("Angle for Skew action, in degrees.\n"
              "Float number between -360 and 360.")
        )
        self.skewy_entry = FCDoubleSpinner(callback=self.confirmation_message)
        # self.skewy_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.skewy_entry.set_precision(self.decimals)
        self.skewy_entry.set_range(-360, 360)

        self.skewy_button = FCButton()
        self.skewy_button.setToolTip(
            _("Skew/shear the selected object(s).\n"
              "The point of reference is the middle of\n"
              "the bounding box for all selected objects."))
        self.skewy_button.setMinimumWidth(90)

        grid0.addWidget(self.skewy_label, 5, 0)
        grid0.addWidget(self.skewy_entry, 5, 1)
        grid0.addWidget(self.skewy_button, 5, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 6, 0, 1, 3)

        # ## Scale Title
        scale_title_label = QtWidgets.QLabel("<font size=3><b>%s</b></font>" % self.scaleName)
        grid0.addWidget(scale_title_label, 7, 0, 1, 3)

        self.scalex_label = QtWidgets.QLabel('%s:' % _("X factor"))
        self.scalex_label.setToolTip(
            _("Factor for scaling on X axis.")
        )
        self.scalex_entry = FCDoubleSpinner(callback=self.confirmation_message)
        # self.scalex_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.scalex_entry.set_precision(self.decimals)
        self.scalex_entry.setMinimum(-1e6)

        self.scalex_button = FCButton()
        self.scalex_button.setToolTip(
            _("Scale the selected object(s).\n"
              "The point of reference depends on \n"
              "the Scale reference checkbox state."))
        self.scalex_button.setMinimumWidth(90)

        grid0.addWidget(self.scalex_label, 8, 0)
        grid0.addWidget(self.scalex_entry, 8, 1)
        grid0.addWidget(self.scalex_button, 8, 2)

        self.scaley_label = QtWidgets.QLabel('%s:' % _("Y factor"))
        self.scaley_label.setToolTip(
            _("Factor for scaling on Y axis.")
        )
        self.scaley_entry = FCDoubleSpinner(callback=self.confirmation_message)
        # self.scaley_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.scaley_entry.set_precision(self.decimals)
        self.scaley_entry.setMinimum(-1e6)

        self.scaley_button = FCButton()
        self.scaley_button.setToolTip(
            _("Scale the selected object(s).\n"
              "The point of reference depends on \n"
              "the Scale reference checkbox state."))
        self.scaley_button.setMinimumWidth(90)

        grid0.addWidget(self.scaley_label, 9, 0)
        grid0.addWidget(self.scaley_entry, 9, 1)
        grid0.addWidget(self.scaley_button, 9, 2)

        self.scale_link_cb = FCCheckBox()
        self.scale_link_cb.setText(_("Link"))
        self.scale_link_cb.setToolTip(
            _("Scale the selected object(s)\n"
              "using the Scale_X factor for both axis.")
        )

        self.scale_zero_ref_cb = FCCheckBox()
        self.scale_zero_ref_cb.setText('%s' % _("Scale Reference"))
        self.scale_zero_ref_cb.setToolTip(
            _("Scale the selected object(s)\n"
              "using the origin reference when checked,\n"
              "and the center of the biggest bounding box\n"
              "of the selected objects when unchecked."))

        self.ois_scale = OptionalInputSection(self.scale_link_cb, [self.scaley_entry, self.scaley_button], logic=False)

        grid0.addWidget(self.scale_link_cb, 10, 0)
        grid0.addWidget(self.scale_zero_ref_cb, 10, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 11, 0, 1, 3)

        # ## Offset Title
        offset_title_label = QtWidgets.QLabel("<font size=3><b>%s</b></font>" % self.offsetName)
        grid0.addWidget(offset_title_label, 12, 0, 1, 3)

        self.offx_label = QtWidgets.QLabel('%s:' % _("X val"))
        self.offx_label.setToolTip(
            _("Distance to offset on X axis. In current units.")
        )
        self.offx_entry = FCDoubleSpinner(callback=self.confirmation_message)
        # self.offx_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.offx_entry.set_precision(self.decimals)
        self.offx_entry.setMinimum(-1e6)

        self.offx_button = FCButton()
        self.offx_button.setToolTip(
            _("Offset the selected object(s).\n"
              "The point of reference is the middle of\n"
              "the bounding box for all selected objects.\n"))
        self.offx_button.setMinimumWidth(90)

        grid0.addWidget(self.offx_label, 13, 0)
        grid0.addWidget(self.offx_entry, 13, 1)
        grid0.addWidget(self.offx_button, 13, 2)

        self.offy_label = QtWidgets.QLabel('%s:' % _("Y val"))
        self.offy_label.setToolTip(
            _("Distance to offset on Y axis. In current units.")
        )
        self.offy_entry = FCDoubleSpinner(callback=self.confirmation_message)
        # self.offy_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.offy_entry.set_precision(self.decimals)
        self.offy_entry.setMinimum(-1e6)

        self.offy_button = FCButton()
        self.offy_button.setToolTip(
            _("Offset the selected object(s).\n"
              "The point of reference is the middle of\n"
              "the bounding box for all selected objects.\n"))
        self.offy_button.setMinimumWidth(90)

        grid0.addWidget(self.offy_label, 14, 0)
        grid0.addWidget(self.offy_entry, 14, 1)
        grid0.addWidget(self.offy_button, 14, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 15, 0, 1, 3)

        # ## Flip Title
        flip_title_label = QtWidgets.QLabel("<font size=3><b>%s</b></font>" % self.flipName)
        grid0.addWidget(flip_title_label, 16, 0, 1, 3)

        self.flipx_button = FCButton()
        self.flipx_button.setToolTip(
            _("Flip the selected object(s) over the X axis.")
        )

        self.flipy_button = FCButton()
        self.flipy_button.setToolTip(
            _("Flip the selected object(s) over the X axis.")
        )

        hlay0 = QtWidgets.QHBoxLayout()
        grid0.addLayout(hlay0, 17, 0, 1, 3)

        hlay0.addWidget(self.flipx_button)
        hlay0.addWidget(self.flipy_button)

        self.flip_ref_cb = FCCheckBox()
        self.flip_ref_cb.setText('%s' % _("Mirror Reference"))
        self.flip_ref_cb.setToolTip(
            _("Flip the selected object(s)\n"
              "around the point in Point Entry Field.\n"
              "\n"
              "The point coordinates can be captured by\n"
              "left click on canvas together with pressing\n"
              "SHIFT key. \n"
              "Then click Add button to insert coordinates.\n"
              "Or enter the coords in format (x, y) in the\n"
              "Point Entry field and click Flip on X(Y)"))

        grid0.addWidget(self.flip_ref_cb, 18, 0, 1, 3)

        self.flip_ref_label = QtWidgets.QLabel('%s:' % _("Ref. Point"))
        self.flip_ref_label.setToolTip(
            _("Coordinates in format (x, y) used as reference for mirroring.\n"
              "The 'x' in (x, y) will be used when using Flip on X and\n"
              "the 'y' in (x, y) will be used when using Flip on Y.")
        )
        self.flip_ref_entry = EvalEntry2("(0, 0)")
        # self.flip_ref_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        # self.flip_ref_entry.setFixedWidth(70)

        self.flip_ref_button = FCButton()
        self.flip_ref_button.setToolTip(
            _("The point coordinates can be captured by\n"
              "left click on canvas together with pressing\n"
              "SHIFT key. Then click Add button to insert."))

        self.ois_flip = OptionalInputSection(self.flip_ref_cb, [self.flip_ref_entry, self.flip_ref_button], logic=True)

        hlay1 = QtWidgets.QHBoxLayout()
        grid0.addLayout(hlay1, 19, 0, 1, 3)

        hlay1.addWidget(self.flip_ref_label)
        hlay1.addWidget(self.flip_ref_entry)

        grid0.addWidget(self.flip_ref_button, 20, 0, 1, 3)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 21, 0, 1, 3)

        # ## Buffer Title
        buffer_title_label = QtWidgets.QLabel("<font size=3><b>%s</b></font>" % self.bufferName)
        grid0.addWidget(buffer_title_label, 22, 0, 1, 3)

        self.buffer_label = QtWidgets.QLabel('%s:' % _("Distance"))
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
        self.buffer_entry.set_range(-9999.9999, 9999.9999)

        self.buffer_button = FCButton()
        self.buffer_button.setToolTip(
            _("Create the buffer effect on each geometry,\n"
              "element from the selected object, using the distance.")
        )
        self.buffer_button.setMinimumWidth(90)

        grid0.addWidget(self.buffer_label, 23, 0)
        grid0.addWidget(self.buffer_entry, 23, 1)
        grid0.addWidget(self.buffer_button, 23, 2)

        self.buffer_factor_label = QtWidgets.QLabel('%s:' % _("Value"))
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

        self.buffer_factor_button = FCButton()
        self.buffer_factor_button.setToolTip(
            _("Create the buffer effect on each geometry,\n"
              "element from the selected object, using the factor.")
        )
        self.buffer_factor_button.setMinimumWidth(90)

        grid0.addWidget(self.buffer_factor_label, 24, 0)
        grid0.addWidget(self.buffer_factor_entry, 24, 1)
        grid0.addWidget(self.buffer_factor_button, 24, 2)

        self.buffer_rounded_cb = FCCheckBox('%s' % _("Rounded"))
        self.buffer_rounded_cb.setToolTip(
            _("If checked then the buffer will surround the buffered shape,\n"
              "every corner will be rounded.\n"
              "If not checked then the buffer will follow the exact geometry\n"
              "of the buffered shape.")
        )

        grid0.addWidget(self.buffer_rounded_cb, 25, 0, 1, 3)

        grid0.addWidget(QtWidgets.QLabel(''), 26, 0, 1, 3)

        self.transform_lay.addStretch()

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
        self.transform_lay.addWidget(self.reset_button)

        # ## Signals
        self.rotate_button.clicked.connect(self.on_rotate)
        self.skewx_button.clicked.connect(self.on_skewx)
        self.skewy_button.clicked.connect(self.on_skewy)
        self.scalex_button.clicked.connect(self.on_scalex)
        self.scaley_button.clicked.connect(self.on_scaley)
        self.offx_button.clicked.connect(self.on_offx)
        self.offy_button.clicked.connect(self.on_offy)
        self.flipx_button.clicked.connect(self.on_flipx)
        self.flipy_button.clicked.connect(self.on_flipy)
        self.flip_ref_button.clicked.connect(self.on_flip_add_coords)
        self.buffer_button.clicked.connect(self.on_buffer_by_distance)
        self.buffer_factor_button.clicked.connect(self.on_buffer_by_factor)

        self.reset_button.clicked.connect(self.set_tool_ui)

        # self.rotate_entry.returnPressed.connect(self.on_rotate)
        # self.skewx_entry.returnPressed.connect(self.on_skewx)
        # self.skewy_entry.returnPressed.connect(self.on_skewy)
        # self.scalex_entry.returnPressed.connect(self.on_scalex)
        # self.scaley_entry.returnPressed.connect(self.on_scaley)
        # self.offx_entry.returnPressed.connect(self.on_offx)
        # self.offy_entry.returnPressed.connect(self.on_offy)
        # self.buffer_entry.returnPressed.connect(self.on_buffer_by_distance)

    def run(self, toggle=True):
        self.app.report_usage("ToolTransform()")

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

        self.app.ui.notebook.setTabText(2, _("Transform Tool"))

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, shortcut='ALT+T', **kwargs)

    def set_tool_ui(self):
        self.rotate_button.set_value(_("Rotate"))
        self.skewx_button.set_value(_("Skew X"))
        self.skewy_button.set_value(_("Skew Y"))
        self.scalex_button.set_value(_("Scale X"))
        self.scaley_button.set_value(_("Scale Y"))
        self.scale_link_cb.set_value(True)
        self.scale_zero_ref_cb.set_value(True)
        self.offx_button.set_value(_("Offset X"))
        self.offy_button.set_value(_("Offset Y"))
        self.flipx_button.set_value(_("Flip on X"))
        self.flipy_button.set_value(_("Flip on Y"))
        self.flip_ref_cb.set_value(True)
        self.flip_ref_button.set_value(_("Add"))
        self.buffer_button.set_value(_("Buffer D"))
        self.buffer_factor_button.set_value(_("Buffer F"))

        # ## Initialize form
        if self.app.defaults["tools_transform_rotate"]:
            self.rotate_entry.set_value(self.app.defaults["tools_transform_rotate"])
        else:
            self.rotate_entry.set_value(0.0)

        if self.app.defaults["tools_transform_skew_x"]:
            self.skewx_entry.set_value(self.app.defaults["tools_transform_skew_x"])
        else:
            self.skewx_entry.set_value(0.0)

        if self.app.defaults["tools_transform_skew_y"]:
            self.skewy_entry.set_value(self.app.defaults["tools_transform_skew_y"])
        else:
            self.skewy_entry.set_value(0.0)

        if self.app.defaults["tools_transform_scale_x"]:
            self.scalex_entry.set_value(self.app.defaults["tools_transform_scale_x"])
        else:
            self.scalex_entry.set_value(1.0)

        if self.app.defaults["tools_transform_scale_y"]:
            self.scaley_entry.set_value(self.app.defaults["tools_transform_scale_y"])
        else:
            self.scaley_entry.set_value(1.0)

        if self.app.defaults["tools_transform_scale_link"]:
            self.scale_link_cb.set_value(self.app.defaults["tools_transform_scale_link"])
        else:
            self.scale_link_cb.set_value(True)

        if self.app.defaults["tools_transform_scale_reference"]:
            self.scale_zero_ref_cb.set_value(self.app.defaults["tools_transform_scale_reference"])
        else:
            self.scale_zero_ref_cb.set_value(True)

        if self.app.defaults["tools_transform_offset_x"]:
            self.offx_entry.set_value(self.app.defaults["tools_transform_offset_x"])
        else:
            self.offx_entry.set_value(0.0)

        if self.app.defaults["tools_transform_offset_y"]:
            self.offy_entry.set_value(self.app.defaults["tools_transform_offset_y"])
        else:
            self.offy_entry.set_value(0.0)

        if self.app.defaults["tools_transform_mirror_reference"]:
            self.flip_ref_cb.set_value(self.app.defaults["tools_transform_mirror_reference"])
        else:
            self.flip_ref_cb.set_value(False)

        if self.app.defaults["tools_transform_mirror_point"]:
            self.flip_ref_entry.set_value(self.app.defaults["tools_transform_mirror_point"])
        else:
            self.flip_ref_entry.set_value((0, 0))

        if self.app.defaults["tools_transform_buffer_dis"]:
            self.buffer_entry.set_value(self.app.defaults["tools_transform_buffer_dis"])
        else:
            self.buffer_entry.set_value(0.0)

        if self.app.defaults["tools_transform_buffer_factor"]:
            self.buffer_factor_entry.set_value(self.app.defaults["tools_transform_buffer_factor"])
        else:
            self.buffer_factor_entry.set_value(100.0)

        if self.app.defaults["tools_transform_buffer_corner"]:
            self.buffer_rounded_cb.set_value(self.app.defaults["tools_transform_buffer_corner"])
        else:
            self.buffer_rounded_cb.set_value(True)

    def on_rotate(self):
        value = float(self.rotate_entry.get_value())
        if value == 0:
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("Rotate transformation can not be done for a value of 0."))
        self.app.worker_task.emit({'fcn': self.on_rotate_action, 'params': [value]})
        return

    def on_flipx(self):
        axis = 'Y'

        self.app.worker_task.emit({'fcn': self.on_flip, 'params': [axis]})
        return

    def on_flipy(self):
        axis = 'X'

        self.app.worker_task.emit({'fcn': self.on_flip, 'params': [axis]})
        return

    def on_flip_add_coords(self):
        val = self.app.clipboard.text()
        self.flip_ref_entry.set_value(val)

    def on_skewx(self):
        value = float(self.skewx_entry.get_value())
        axis = 'X'

        self.app.worker_task.emit({'fcn': self.on_skew, 'params': [axis, value]})
        return

    def on_skewy(self):
        value = float(self.skewy_entry.get_value())
        axis = 'Y'

        self.app.worker_task.emit({'fcn': self.on_skew, 'params': [axis, value]})
        return

    def on_scalex(self):
        xvalue = float(self.scalex_entry.get_value())

        if xvalue == 0 or xvalue == 1:
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("Scale transformation can not be done for a factor of 0 or 1."))
            return

        if self.scale_link_cb.get_value():
            yvalue = xvalue
        else:
            yvalue = 1

        axis = 'X'
        point = (0, 0)
        if self.scale_zero_ref_cb.get_value():
            self.app.worker_task.emit({'fcn': self.on_scale, 'params': [axis, xvalue, yvalue, point]})
        else:
            self.app.worker_task.emit({'fcn': self.on_scale, 'params': [axis, xvalue, yvalue]})

        return

    def on_scaley(self):
        xvalue = 1
        yvalue = float(self.scaley_entry.get_value())

        if yvalue == 0 or yvalue == 1:
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("Scale transformation can not be done for a factor of 0 or 1."))
            return

        axis = 'Y'
        point = (0, 0)
        if self.scale_zero_ref_cb.get_value():
            self.app.worker_task.emit({'fcn': self.on_scale, 'params': [axis, xvalue, yvalue, point]})
        else:
            self.app.worker_task.emit({'fcn': self.on_scale, 'params': [axis, xvalue, yvalue]})

        return

    def on_offx(self):
        value = float(self.offx_entry.get_value())
        if value == 0:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Offset transformation can not be done for a value of 0."))
            return
        axis = 'X'

        self.app.worker_task.emit({'fcn': self.on_offset, 'params': [axis, value]})
        return

    def on_offy(self):
        value = float(self.offy_entry.get_value())
        if value == 0:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Offset transformation can not be done for a value of 0."))
            return
        axis = 'Y'

        self.app.worker_task.emit({'fcn': self.on_offset, 'params': [axis, value]})
        return

    def on_buffer_by_distance(self):
        value = self.buffer_entry.get_value()
        join = 1 if self.buffer_rounded_cb.get_value() else 2

        self.app.worker_task.emit({'fcn': self.on_buffer_action, 'params': [value, join]})
        return

    def on_buffer_by_factor(self):
        value = self.buffer_factor_entry.get_value() / 100.0
        join = 1 if self.buffer_rounded_cb.get_value() else 2

        # tell the buffer method to use the factor
        factor = True

        self.app.worker_task.emit({'fcn': self.on_buffer_action, 'params': [value, join, factor]})
        return

    def on_rotate_action(self, num):
        obj_list = self.app.collection.get_selected()
        xminlist = []
        yminlist = []
        xmaxlist = []
        ymaxlist = []

        if not obj_list:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("No object selected. Please Select an object to rotate!"))
            return
        else:
            with self.app.proc_container.new(_("Appying Rotate")):
                try:
                    # first get a bounding box to fit all
                    for obj in obj_list:
                        if isinstance(obj, FlatCAMCNCjob):
                            pass
                        else:
                            xmin, ymin, xmax, ymax = obj.bounds()
                            xminlist.append(xmin)
                            yminlist.append(ymin)
                            xmaxlist.append(xmax)
                            ymaxlist.append(ymax)

                    # get the minimum x,y and maximum x,y for all objects selected
                    xminimal = min(xminlist)
                    yminimal = min(yminlist)
                    xmaximal = max(xmaxlist)
                    ymaximal = max(ymaxlist)

                    px = 0.5 * (xminimal + xmaximal)
                    py = 0.5 * (yminimal + ymaximal)
                    for sel_obj in obj_list:
                        if isinstance(sel_obj, FlatCAMCNCjob):
                            self.app.inform.emit(_("CNCJob objects can't be rotated."))
                        else:
                            sel_obj.rotate(-num, point=(px, py))
                            self.app.object_changed.emit(sel_obj)

                        # add information to the object that it was changed and how much
                        sel_obj.options['rotate'] = num
                        sel_obj.plot()
                    self.app.inform.emit('[success] %s...' % _('Rotate done'))
                except Exception as e:
                    self.app.inform.emit('[ERROR_NOTCL] %s %s, %s.' %
                                         (_("Due of"), str(e), _("action was not executed.")))
                    return

    def on_flip(self, axis):
        obj_list = self.app.collection.get_selected()
        xminlist = []
        yminlist = []
        xmaxlist = []
        ymaxlist = []

        if not obj_list:
            self.app.inform.emit('[WARNING_NOTCL] %s!' %
                                 _("No object selected. Please Select an object to flip"))
            return
        else:
            with self.app.proc_container.new(_("Applying Flip")):
                try:
                    # get mirroring coords from the point entry
                    if self.flip_ref_cb.isChecked():
                        px, py = eval('{}'.format(self.flip_ref_entry.text()))
                    # get mirroing coords from the center of an all-enclosing bounding box
                    else:
                        # first get a bounding box to fit all
                        for obj in obj_list:
                            if isinstance(obj, FlatCAMCNCjob):
                                pass
                            else:
                                xmin, ymin, xmax, ymax = obj.bounds()
                                xminlist.append(xmin)
                                yminlist.append(ymin)
                                xmaxlist.append(xmax)
                                ymaxlist.append(ymax)

                        # get the minimum x,y and maximum x,y for all objects selected
                        xminimal = min(xminlist)
                        yminimal = min(yminlist)
                        xmaximal = max(xmaxlist)
                        ymaximal = max(ymaxlist)

                        px = 0.5 * (xminimal + xmaximal)
                        py = 0.5 * (yminimal + ymaximal)

                    # execute mirroring
                    for sel_obj in obj_list:
                        if isinstance(sel_obj, FlatCAMCNCjob):
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
                                self.app.inform.emit('[success] %s...' %
                                                     _('Flip on the Y axis done'))
                            elif axis == 'Y':
                                sel_obj.mirror('Y', (px, py))
                                # add information to the object that it was changed and how much
                                # the axis is reversed because of the reference
                                if 'mirror_x' in sel_obj.options:
                                    sel_obj.options['mirror_x'] = not sel_obj.options['mirror_x']
                                else:
                                    sel_obj.options['mirror_x'] = True
                                self.app.inform.emit('[success] %s...' % _('Flip on the X axis done'))
                            self.app.object_changed.emit(sel_obj)
                        sel_obj.plot()
                except Exception as e:
                    self.app.inform.emit('[ERROR_NOTCL] %s %s, %s.' %
                                         (_("Due of"), str(e), _("action was not executed.")))
                    return

    def on_skew(self, axis, num):
        obj_list = self.app.collection.get_selected()
        xminlist = []
        yminlist = []

        if num == 0 or num == 90 or num == 180:
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("Skew transformation can not be done for 0, 90 and 180 degrees."))
            return

        if not obj_list:
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("No object selected. Please Select an object to shear/skew!"))
            return
        else:
            with self.app.proc_container.new(_("Applying Skew")):
                try:
                    # first get a bounding box to fit all
                    for obj in obj_list:
                        if isinstance(obj, FlatCAMCNCjob):
                            pass
                        else:
                            xmin, ymin, xmax, ymax = obj.bounds()
                            xminlist.append(xmin)
                            yminlist.append(ymin)

                    # get the minimum x,y and maximum x,y for all objects selected
                    xminimal = min(xminlist)
                    yminimal = min(yminlist)

                    for sel_obj in obj_list:
                        if isinstance(sel_obj, FlatCAMCNCjob):
                            self.app.inform.emit(_("CNCJob objects can't be skewed."))
                        else:
                            if axis == 'X':
                                sel_obj.skew(num, 0, point=(xminimal, yminimal))
                                # add information to the object that it was changed and how much
                                sel_obj.options['skew_x'] = num
                            elif axis == 'Y':
                                sel_obj.skew(0, num, point=(xminimal, yminimal))
                                # add information to the object that it was changed and how much
                                sel_obj.options['skew_y'] = num
                            self.app.object_changed.emit(sel_obj)
                        sel_obj.plot()
                    self.app.inform.emit('[success] %s %s %s...' % (_('Skew on the'),  str(axis), _("axis done")))
                except Exception as e:
                    self.app.inform.emit('[ERROR_NOTCL] %s %s, %s.' %
                                         (_("Due of"), str(e), _("action was not executed.")))
                    return

    def on_scale(self, axis, xfactor, yfactor, point=None):
        obj_list = self.app.collection.get_selected()
        xminlist = []
        yminlist = []
        xmaxlist = []
        ymaxlist = []

        if not obj_list:
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("No object selected. Please Select an object to scale!"))
            return
        else:
            with self.app.proc_container.new(_("Applying Scale")):
                try:
                    # first get a bounding box to fit all
                    for obj in obj_list:
                        if isinstance(obj, FlatCAMCNCjob):
                            pass
                        else:
                            xmin, ymin, xmax, ymax = obj.bounds()
                            xminlist.append(xmin)
                            yminlist.append(ymin)
                            xmaxlist.append(xmax)
                            ymaxlist.append(ymax)

                    # get the minimum x,y and maximum x,y for all objects selected
                    xminimal = min(xminlist)
                    yminimal = min(yminlist)
                    xmaximal = max(xmaxlist)
                    ymaximal = max(ymaxlist)

                    if point is None:
                        px = 0.5 * (xminimal + xmaximal)
                        py = 0.5 * (yminimal + ymaximal)
                    else:
                        px = 0
                        py = 0

                    for sel_obj in obj_list:
                        if isinstance(sel_obj, FlatCAMCNCjob):
                            self.app.inform.emit(_("CNCJob objects can't be scaled."))
                        else:
                            sel_obj.scale(xfactor, yfactor, point=(px, py))
                            # add information to the object that it was changed and how much
                            sel_obj.options['scale_x'] = xfactor
                            sel_obj.options['scale_y'] = yfactor
                            self.app.object_changed.emit(sel_obj)
                        sel_obj.plot()

                    self.app.inform.emit('[success] %s %s %s...' %
                                         (_('Scale on the'), str(axis), _('axis done')))
                except Exception as e:
                    self.app.inform.emit('[ERROR_NOTCL] %s %s, %s.' %
                                         (_("Due of"), str(e), _("action was not executed.")))
                    return

    def on_offset(self, axis, num):
        obj_list = self.app.collection.get_selected()

        if not obj_list:
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("No object selected. Please Select an object to offset!"))
            return
        else:
            with self.app.proc_container.new(_("Applying Offset")):
                try:
                    for sel_obj in obj_list:
                        if isinstance(sel_obj, FlatCAMCNCjob):
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
                            self.app.object_changed.emit(sel_obj)
                        sel_obj.plot()

                    self.app.inform.emit('[success] %s %s %s...' %
                                         (_('Offset on the'), str(axis), _('axis done')))
                except Exception as e:
                    self.app.inform.emit('[ERROR_NOTCL] %s %s, %s.' %
                                         (_("Due of"), str(e),  _("action was not executed.")))
                    return

    def on_buffer_action(self, value, join, factor=None):
        obj_list = self.app.collection.get_selected()

        if not obj_list:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("No object selected. Please Select an object to buffer!"))
            return
        else:
            with self.app.proc_container.new(_("Applying Buffer")):
                try:
                    for sel_obj in obj_list:
                        if isinstance(sel_obj, FlatCAMCNCjob):
                            self.app.inform.emit(_("CNCJob objects can't be buffered."))
                        elif sel_obj.kind.lower() == 'gerber':
                            sel_obj.buffer(value, join, factor)
                            sel_obj.source_file = self.app.export_gerber(obj_name=sel_obj.options['name'],
                                                                         filename=None, local_use=sel_obj,
                                                                         use_thread=False)
                        elif sel_obj.kind.lower() == 'excellon':
                            sel_obj.buffer(value, join, factor)
                            sel_obj.source_file = self.app.export_excellon(obj_name=sel_obj.options['name'],
                                                                           filename=None, local_use=sel_obj,
                                                                           use_thread=False)
                        elif sel_obj.kind.lower() == 'geometry':
                            sel_obj.buffer(value, join, factor)

                        self.app.object_changed.emit(sel_obj)
                        sel_obj.plot()

                    self.app.inform.emit('[success] %s...' % _('Buffer done'))

                except Exception as e:
                    self.app.log.debug("ToolTransform.on_buffer_action() --> %s" % str(e))
                    self.app.inform.emit('[ERROR_NOTCL] %s %s, %s.' %
                                         (_("Due of"), str(e),  _("action was not executed.")))
                    return

# end of file
