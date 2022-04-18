from PyQt6 import QtWidgets, QtGui

from appGUI.GUIElements import FCDoubleSpinner, FCCheckBox, NumericalEvalTupleEntry, FCComboBox, FCLabel, \
    GLay, FCFrame
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ToolsTransformPrefGroupUI(OptionsGroupUI):
    def __init__(self, app, parent=None):

        super(ToolsTransformPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Transform Plugin")))
        self.decimals = app.decimals
        self.options = app.options

        # #############################################################################################################
        # PARAMETERS Frame
        # #############################################################################################################
        self.transform_label = FCLabel('%s' % _("Parameters"), color='blue', bold=True)
        self.transform_label.setToolTip(
            _("Various transformations that can be applied\n"
              "on a application object.")
        )
        self.layout.addWidget(self.transform_label)

        param_frame = FCFrame()
        self.layout.addWidget(param_frame)

        param_grid = GLay(v_spacing=5, h_spacing=3)
        param_frame.setLayout(param_grid)

        # Reference Type
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

        param_grid.addWidget(ref_label, 0, 0)
        param_grid.addWidget(self.ref_combo, 0, 1)

        self.point_label = FCLabel('%s:' % _("Point"))
        self.point_label.setToolTip(
            _("A point of reference in format X,Y.")
        )
        self.point_entry = NumericalEvalTupleEntry()

        param_grid.addWidget(self.point_label, 2, 0)
        param_grid.addWidget(self.point_entry, 2, 1)

        # Type of object to be used as reference
        self.type_object_label = FCLabel('%s:' % _("Object"))
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

        param_grid.addWidget(self.type_object_label, 4, 0)
        param_grid.addWidget(self.type_obj_combo, 4, 1)

        # #############################################################################################################
        # Rotate Frame
        # #############################################################################################################
        rotate_title_lbl = FCLabel('%s' % _("Rotate"), color='tomato', bold=True)
        self.layout.addWidget(rotate_title_lbl)

        rot_frame = FCFrame()
        self.layout.addWidget(rot_frame)

        rot_grid = GLay(v_spacing=5, h_spacing=3)
        rot_frame.setLayout(rot_grid)

        self.rotate_entry = FCDoubleSpinner()
        self.rotate_entry.set_range(-360.0, 360.0)
        self.rotate_entry.set_precision(self.decimals)
        self.rotate_entry.setSingleStep(15)

        self.rotate_label = FCLabel('%s:' % _("Angle"))
        self.rotate_label.setToolTip(
            _("Angle, in degrees.\n"
              "Float number between -360 and 359.\n"
              "Positive numbers for CW motion.\n"
              "Negative numbers for CCW motion.")
        )
        rot_grid.addWidget(self.rotate_label, 0, 0)
        rot_grid.addWidget(self.rotate_entry, 0, 1)

        # #############################################################################################################
        # Skew Frame
        # #############################################################################################################
        s_t_lay = QtWidgets.QHBoxLayout()
        self.layout.addLayout(s_t_lay)

        skew_title_lbl = FCLabel('%s' % _("Skew"), color='teal', bold=True)
        s_t_lay.addWidget(skew_title_lbl)

        s_t_lay.addStretch()

        # ## Link Skew factors
        self.skew_link_cb = FCCheckBox()
        self.skew_link_cb.setText(_("Link"))
        self.skew_link_cb.setToolTip(
            _("Link the Y entry to X entry and copy its content.")
        )

        s_t_lay.addWidget(self.skew_link_cb)

        skew_frame = FCFrame()
        self.layout.addWidget(skew_frame)

        skew_grid = GLay(v_spacing=5, h_spacing=3)
        skew_frame.setLayout(skew_grid)

        self.skewx_entry = FCDoubleSpinner()
        self.skewx_entry.set_range(-360.0, 360.0)
        self.skewx_entry.set_precision(self.decimals)
        self.skewx_entry.setSingleStep(0.1)

        self.skewx_label = FCLabel('%s:' % _("X angle"))
        self.skewx_label.setToolTip(
            _("Angle, in degrees.\n"
              "Float number between -360 and 359.")
        )
        skew_grid.addWidget(self.skewx_label, 2, 0)
        skew_grid.addWidget(self.skewx_entry, 2, 1)

        # ## Skew/Shear Angle on Y axis
        self.skewy_entry = FCDoubleSpinner()
        self.skewy_entry.set_range(-360.0, 360.0)
        self.skewy_entry.set_precision(self.decimals)
        self.skewy_entry.setSingleStep(0.1)

        self.skewy_label = FCLabel('%s:' % _("Y angle"))
        self.skewy_label.setToolTip(
            _("Angle, in degrees.\n"
              "Float number between -360 and 359.")
        )
        skew_grid.addWidget(self.skewy_label, 4, 0)
        skew_grid.addWidget(self.skewy_entry, 4, 1)

        # #############################################################################################################
        # Scale Frame
        # #############################################################################################################
        sc_t_lay = QtWidgets.QHBoxLayout()
        self.layout.addLayout(sc_t_lay)

        scale_title_lbl = FCLabel('%s' % _("Scale"), color='magenta', bold=True)
        sc_t_lay.addWidget(scale_title_lbl)

        sc_t_lay.addStretch()

        # ## Link Scale factors
        self.scale_link_cb = FCCheckBox(_("Link"))
        self.scale_link_cb.setToolTip(
            _("Link the Y entry to X entry and copy its content.")
        )
        sc_t_lay.addWidget(self.scale_link_cb)

        scale_frame = FCFrame()
        self.layout.addWidget(scale_frame)

        scale_grid = GLay(v_spacing=5, h_spacing=3)
        scale_frame.setLayout(scale_grid)

        self.scalex_entry = FCDoubleSpinner()
        self.scalex_entry.set_range(0, 10000.0000)
        self.scalex_entry.set_precision(self.decimals)
        self.scalex_entry.setSingleStep(0.1)

        self.scalex_label = FCLabel('%s:' % _("X factor"))
        self.scalex_label.setToolTip(
            _("Factor for scaling on X axis.")
        )
        scale_grid.addWidget(self.scalex_label, 2, 0)
        scale_grid.addWidget(self.scalex_entry, 2, 1)

        # ## Scale factor on X axis
        self.scaley_entry = FCDoubleSpinner()
        self.scaley_entry.set_range(0, 10000.0000)
        self.scaley_entry.set_precision(self.decimals)
        self.scaley_entry.setSingleStep(0.1)

        self.scaley_label = FCLabel('%s:' % _("Y factor"))
        self.scaley_label.setToolTip(
            _("Factor for scaling on Y axis.")
        )
        scale_grid.addWidget(self.scaley_label, 4, 0)
        scale_grid.addWidget(self.scaley_entry, 4, 1)

        # #############################################################################################################
        # Offset Frame
        # #############################################################################################################
        offset_title_lbl = FCLabel('%s' % _("Offset"), color='green', bold=True)
        self.layout.addWidget(offset_title_lbl)

        off_frame = FCFrame()
        self.layout.addWidget(off_frame)

        off_grid = GLay(v_spacing=5, h_spacing=3)
        off_frame.setLayout(off_grid)

        self.offx_entry = FCDoubleSpinner()
        self.offx_entry.set_range(-10000.0000, 10000.0000)
        self.offx_entry.set_precision(self.decimals)
        self.offx_entry.setSingleStep(0.1)

        self.offx_label = FCLabel('%s:' % _("X val"))
        self.offx_label.setToolTip(
           _("Distance to offset on X axis. In current units.")
        )
        off_grid.addWidget(self.offx_label, 0, 0)
        off_grid.addWidget(self.offx_entry, 0, 1)

        # ## Offset distance on Y axis
        self.offy_entry = FCDoubleSpinner()
        self.offy_entry.set_range(-10000.0000, 10000.0000)
        self.offy_entry.set_precision(self.decimals)
        self.offy_entry.setSingleStep(0.1)

        self.offy_label = FCLabel('%s:' % _("Y val"))
        self.offy_label.setToolTip(
            _("Distance to offset on Y axis. In current units.")
        )
        off_grid.addWidget(self.offy_label, 2, 0)
        off_grid.addWidget(self.offy_entry, 2, 1)

        # #############################################################################################################
        # Buffer Frame
        # #############################################################################################################
        b_t_lay = QtWidgets.QHBoxLayout()
        self.layout.addLayout(b_t_lay)

        buffer_title_lbl = FCLabel('%s' % _("Buffer"), color='indigo', bold=True)
        b_t_lay.addWidget(buffer_title_lbl)

        b_t_lay.addStretch()

        self.buffer_rounded_cb = FCCheckBox()
        self.buffer_rounded_cb.setText('%s' % _("Rounded"))
        self.buffer_rounded_cb.setToolTip(
            _("If checked then the buffer will surround the buffered shape,\n"
              "every corner will be rounded.\n"
              "If not checked then the buffer will follow the exact geometry\n"
              "of the buffered shape.")
        )

        b_t_lay.addWidget(self.buffer_rounded_cb)

        buff_frame = FCFrame()
        self.layout.addWidget(buff_frame)

        buff_grid = GLay(v_spacing=5, h_spacing=3)
        buff_frame.setLayout(buff_grid)

        self.buffer_label = FCLabel('%s:' % _("Distance"))
        self.buffer_label.setToolTip(
            _("A positive value will create the effect of dilation,\n"
              "while a negative value will create the effect of erosion.\n"
              "Each geometry element of the object will be increased\n"
              "or decreased with the 'distance'.")
        )

        self.buffer_entry = FCDoubleSpinner()
        self.buffer_entry.set_precision(self.decimals)
        self.buffer_entry.setSingleStep(0.1)
        self.buffer_entry.setWrapping(True)
        self.buffer_entry.set_range(-10000.0000, 10000.0000)

        buff_grid.addWidget(self.buffer_label, 2, 0)
        buff_grid.addWidget(self.buffer_entry, 2, 1)

        self.buffer_factor_label = FCLabel('%s:' % _("Value"))
        self.buffer_factor_label.setToolTip(
            _("A positive value will create the effect of dilation,\n"
              "while a negative value will create the effect of erosion.\n"
              "Each geometry element of the object will be increased\n"
              "or decreased to fit the 'Value'. Value is a percentage\n"
              "of the initial dimension.")
        )

        self.buffer_factor_entry = FCDoubleSpinner(suffix='%')
        self.buffer_factor_entry.set_range(-100.0000, 1000.0000)
        self.buffer_factor_entry.set_precision(self.decimals)
        self.buffer_factor_entry.setWrapping(True)
        self.buffer_factor_entry.setSingleStep(1)

        buff_grid.addWidget(self.buffer_factor_label, 4, 0)
        buff_grid.addWidget(self.buffer_factor_entry, 4, 1)

        GLay.set_common_column_size(
            [param_grid, rot_grid, skew_grid, scale_grid, off_grid, buff_grid], 0)

        self.layout.addStretch()
