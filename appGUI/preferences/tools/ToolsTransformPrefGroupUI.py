from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QSettings

from appGUI.GUIElements import FCDoubleSpinner, FCCheckBox, NumericalEvalTupleEntry, FCComboBox
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


class ToolsTransformPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):

        super(ToolsTransformPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Transform Tool Options")))
        self.decimals = decimals

        # ## Transformations
        self.transform_label = QtWidgets.QLabel("<b>%s:</b>" % _("Parameters"))
        self.transform_label.setToolTip(
            _("Various transformations that can be applied\n"
              "on a application object.")
        )
        self.layout.addWidget(self.transform_label)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)

        # Reference Type
        ref_label = QtWidgets.QLabel('%s:' % _("Reference"))
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
        grid0.addWidget(self.ref_combo, 0, 1)

        self.point_label = QtWidgets.QLabel('%s:' % _("Point"))
        self.point_label.setToolTip(
            _("A point of reference in format X,Y.")
        )
        self.point_entry = NumericalEvalTupleEntry()

        grid0.addWidget(self.point_label, 1, 0)
        grid0.addWidget(self.point_entry, 1, 1)

        # Type of object to be used as reference
        self.type_object_label = QtWidgets.QLabel('%s:' % _("Object"))
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
        grid0.addWidget(self.type_obj_combo, 3, 1)

        # ## Rotate Angle
        rotate_title_lbl = QtWidgets.QLabel('<b>%s</b>' % _("Rotate"))
        grid0.addWidget(rotate_title_lbl, 4, 0, 1, 2)

        self.rotate_entry = FCDoubleSpinner()
        self.rotate_entry.set_range(-360.0, 360.0)
        self.rotate_entry.set_precision(self.decimals)
        self.rotate_entry.setSingleStep(15)

        self.rotate_label = QtWidgets.QLabel('%s:' % _("Angle"))
        self.rotate_label.setToolTip(
            _("Angle, in degrees.\n"
              "Float number between -360 and 359.\n"
              "Positive numbers for CW motion.\n"
              "Negative numbers for CCW motion.")
        )
        grid0.addWidget(self.rotate_label, 6, 0)
        grid0.addWidget(self.rotate_entry, 6, 1)

        # ## Skew/Shear Angle on X axis
        skew_title_lbl = QtWidgets.QLabel('<b>%s</b>' % _("Skew"))
        grid0.addWidget(skew_title_lbl, 8, 0)

        # ## Link Skew factors
        self.skew_link_cb = FCCheckBox()
        self.skew_link_cb.setText(_("Link"))
        self.skew_link_cb.setToolTip(
            _("Link the Y entry to X entry and copy its content.")
        )

        grid0.addWidget(self.skew_link_cb, 8, 1)

        self.skewx_entry = FCDoubleSpinner()
        self.skewx_entry.set_range(-360.0, 360.0)
        self.skewx_entry.set_precision(self.decimals)
        self.skewx_entry.setSingleStep(0.1)

        self.skewx_label = QtWidgets.QLabel('%s:' % _("X angle"))
        self.skewx_label.setToolTip(
            _("Angle, in degrees.\n"
              "Float number between -360 and 359.")
        )
        grid0.addWidget(self.skewx_label, 9, 0)
        grid0.addWidget(self.skewx_entry, 9, 1)

        # ## Skew/Shear Angle on Y axis
        self.skewy_entry = FCDoubleSpinner()
        self.skewy_entry.set_range(-360.0, 360.0)
        self.skewy_entry.set_precision(self.decimals)
        self.skewy_entry.setSingleStep(0.1)

        self.skewy_label = QtWidgets.QLabel('%s:' % _("Y angle"))
        self.skewy_label.setToolTip(
            _("Angle, in degrees.\n"
              "Float number between -360 and 359.")
        )
        grid0.addWidget(self.skewy_label, 10, 0)
        grid0.addWidget(self.skewy_entry, 10, 1)

        # ## Scale
        scale_title_lbl = QtWidgets.QLabel('<b>%s</b>' % _("Scale"))
        grid0.addWidget(scale_title_lbl, 12, 0)

        # ## Link Scale factors
        self.scale_link_cb = FCCheckBox(_("Link"))
        self.scale_link_cb.setToolTip(
            _("Link the Y entry to X entry and copy its content.")
        )
        grid0.addWidget(self.scale_link_cb, 12, 1)

        self.scalex_entry = FCDoubleSpinner()
        self.scalex_entry.set_range(0, 10000.0000)
        self.scalex_entry.set_precision(self.decimals)
        self.scalex_entry.setSingleStep(0.1)

        self.scalex_label = QtWidgets.QLabel('%s:' % _("X factor"))
        self.scalex_label.setToolTip(
            _("Factor for scaling on X axis.")
        )
        grid0.addWidget(self.scalex_label, 14, 0)
        grid0.addWidget(self.scalex_entry, 14, 1)

        # ## Scale factor on X axis
        self.scaley_entry = FCDoubleSpinner()
        self.scaley_entry.set_range(0, 10000.0000)
        self.scaley_entry.set_precision(self.decimals)
        self.scaley_entry.setSingleStep(0.1)

        self.scaley_label = QtWidgets.QLabel('%s:' % _("Y factor"))
        self.scaley_label.setToolTip(
            _("Factor for scaling on Y axis.")
        )
        grid0.addWidget(self.scaley_label, 16, 0)
        grid0.addWidget(self.scaley_entry, 16, 1)

        # ## Offset
        offset_title_lbl = QtWidgets.QLabel('<b>%s</b>' % _("Offset"))
        grid0.addWidget(offset_title_lbl, 20, 0, 1, 2)

        self.offx_entry = FCDoubleSpinner()
        self.offx_entry.set_range(-10000.0000, 10000.0000)
        self.offx_entry.set_precision(self.decimals)
        self.offx_entry.setSingleStep(0.1)

        self.offx_label = QtWidgets.QLabel('%s:' % _("X val"))
        self.offx_label.setToolTip(
           _("Distance to offset on X axis. In current units.")
        )
        grid0.addWidget(self.offx_label, 22, 0)
        grid0.addWidget(self.offx_entry, 22, 1)

        # ## Offset distance on Y axis
        self.offy_entry = FCDoubleSpinner()
        self.offy_entry.set_range(-10000.0000, 10000.0000)
        self.offy_entry.set_precision(self.decimals)
        self.offy_entry.setSingleStep(0.1)

        self.offy_label = QtWidgets.QLabel('%s:' % _("Y val"))
        self.offy_label.setToolTip(
            _("Distance to offset on Y axis. In current units.")
        )
        grid0.addWidget(self.offy_label, 24, 0)
        grid0.addWidget(self.offy_entry, 24, 1)

        # ## Buffer
        buffer_title_lbl = QtWidgets.QLabel('<b>%s</b>' % _("Buffer"))
        grid0.addWidget(buffer_title_lbl, 26, 0)

        self.buffer_rounded_cb = FCCheckBox()
        self.buffer_rounded_cb.setText('%s' % _("Rounded"))
        self.buffer_rounded_cb.setToolTip(
            _("If checked then the buffer will surround the buffered shape,\n"
              "every corner will be rounded.\n"
              "If not checked then the buffer will follow the exact geometry\n"
              "of the buffered shape.")
        )

        grid0.addWidget(self.buffer_rounded_cb, 26, 1)

        self.buffer_label = QtWidgets.QLabel('%s:' % _("Distance"))
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

        grid0.addWidget(self.buffer_label, 28, 0)
        grid0.addWidget(self.buffer_entry, 28, 1)

        self.buffer_factor_label = QtWidgets.QLabel('%s:' % _("Value"))
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

        grid0.addWidget(self.buffer_factor_label, 30, 0)
        grid0.addWidget(self.buffer_factor_entry, 30, 1)

        self.layout.addStretch()
