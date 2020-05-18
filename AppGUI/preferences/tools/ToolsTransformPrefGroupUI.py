from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings

from AppGUI.GUIElements import FCDoubleSpinner, FCCheckBox, FCEntry
from AppGUI.preferences.OptionsGroupUI import OptionsGroupUI

import gettext
import AppTranslation as fcTranslate
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
              "on a FlatCAM object.")
        )
        self.layout.addWidget(self.transform_label)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)

        # ## Rotate Angle

        rotate_title_lbl = QtWidgets.QLabel('<b>%s</b>' % _("Rotate"))
        grid0.addWidget(rotate_title_lbl, 0, 0, 1, 2)

        self.rotate_entry = FCDoubleSpinner()
        self.rotate_entry.set_range(-360.0, 360.0)
        self.rotate_entry.set_precision(self.decimals)
        self.rotate_entry.setSingleStep(15)

        self.rotate_label = QtWidgets.QLabel('%s:' % _("Angle"))
        self.rotate_label.setToolTip(
            _("Angle for Rotation action, in degrees.\n"
              "Float number between -360 and 359.\n"
              "Positive numbers for CW motion.\n"
              "Negative numbers for CCW motion.")
        )
        grid0.addWidget(self.rotate_label, 1, 0)
        grid0.addWidget(self.rotate_entry, 1, 1)

        # ## Skew/Shear Angle on X axis
        skew_title_lbl = QtWidgets.QLabel('<b>%s</b>' % _("Skew"))
        grid0.addWidget(skew_title_lbl, 2, 0, 1, 2)

        self.skewx_entry = FCDoubleSpinner()
        self.skewx_entry.set_range(-360.0, 360.0)
        self.skewx_entry.set_precision(self.decimals)
        self.skewx_entry.setSingleStep(0.1)

        self.skewx_label = QtWidgets.QLabel('%s:' % _("X angle"))
        self.skewx_label.setToolTip(
            _("Angle for Skew action, in degrees.\n"
              "Float number between -360 and 359.")
        )
        grid0.addWidget(self.skewx_label, 3, 0)
        grid0.addWidget(self.skewx_entry, 3, 1)

        # ## Skew/Shear Angle on Y axis
        self.skewy_entry = FCDoubleSpinner()
        self.skewy_entry.set_range(-360.0, 360.0)
        self.skewy_entry.set_precision(self.decimals)
        self.skewy_entry.setSingleStep(0.1)

        self.skewy_label = QtWidgets.QLabel('%s:' % _("Y angle"))
        self.skewy_label.setToolTip(
            _("Angle for Skew action, in degrees.\n"
              "Float number between -360 and 359.")
        )
        grid0.addWidget(self.skewy_label, 4, 0)
        grid0.addWidget(self.skewy_entry, 4, 1)

        # ## Scale
        scale_title_lbl = QtWidgets.QLabel('<b>%s</b>' % _("Scale"))
        grid0.addWidget(scale_title_lbl, 5, 0, 1, 2)

        self.scalex_entry = FCDoubleSpinner()
        self.scalex_entry.set_range(0, 9999.9999)
        self.scalex_entry.set_precision(self.decimals)
        self.scalex_entry.setSingleStep(0.1)

        self.scalex_label = QtWidgets.QLabel('%s:' % _("X factor"))
        self.scalex_label.setToolTip(
            _("Factor for scaling on X axis.")
        )
        grid0.addWidget(self.scalex_label, 6, 0)
        grid0.addWidget(self.scalex_entry, 6, 1)

        # ## Scale factor on X axis
        self.scaley_entry = FCDoubleSpinner()
        self.scaley_entry.set_range(0, 9999.9999)
        self.scaley_entry.set_precision(self.decimals)
        self.scaley_entry.setSingleStep(0.1)

        self.scaley_label = QtWidgets.QLabel('%s:' % _("Y factor"))
        self.scaley_label.setToolTip(
            _("Factor for scaling on Y axis.")
        )
        grid0.addWidget(self.scaley_label, 7, 0)
        grid0.addWidget(self.scaley_entry, 7, 1)

        # ## Link Scale factors
        self.link_cb = FCCheckBox(_("Link"))
        self.link_cb.setToolTip(
            _("Scale the selected object(s)\n"
              "using the Scale_X factor for both axis.")
        )
        grid0.addWidget(self.link_cb, 8, 0)

        # ## Scale Reference
        self.reference_cb = FCCheckBox('%s' % _("Scale Reference"))
        self.reference_cb.setToolTip(
            _("Scale the selected object(s)\n"
              "using the origin reference when checked,\n"
              "and the center of the biggest bounding box\n"
              "of the selected objects when unchecked.")
        )
        grid0.addWidget(self.reference_cb, 8, 1)

        # ## Offset
        offset_title_lbl = QtWidgets.QLabel('<b>%s</b>' % _("Offset"))
        grid0.addWidget(offset_title_lbl, 9, 0, 1, 2)

        self.offx_entry = FCDoubleSpinner()
        self.offx_entry.set_range(-9999.9999, 9999.9999)
        self.offx_entry.set_precision(self.decimals)
        self.offx_entry.setSingleStep(0.1)

        self.offx_label = QtWidgets.QLabel('%s:' % _("X val"))
        self.offx_label.setToolTip(
           _("Distance to offset on X axis. In current units.")
        )
        grid0.addWidget(self.offx_label, 10, 0)
        grid0.addWidget(self.offx_entry, 10, 1)

        # ## Offset distance on Y axis
        self.offy_entry = FCDoubleSpinner()
        self.offy_entry.set_range(-9999.9999, 9999.9999)
        self.offy_entry.set_precision(self.decimals)
        self.offy_entry.setSingleStep(0.1)

        self.offy_label = QtWidgets.QLabel('%s:' % _("Y val"))
        self.offy_label.setToolTip(
            _("Distance to offset on Y axis. In current units.")
        )
        grid0.addWidget(self.offy_label, 11, 0)
        grid0.addWidget(self.offy_entry, 11, 1)

        # ## Mirror
        mirror_title_lbl = QtWidgets.QLabel('<b>%s</b>' % _("Mirror"))
        grid0.addWidget(mirror_title_lbl, 12, 0, 1, 2)

        # ## Mirror (Flip) Reference Point
        self.mirror_reference_cb = FCCheckBox('%s' % _("Mirror Reference"))
        self.mirror_reference_cb.setToolTip(
            _("Flip the selected object(s)\n"
              "around the point in Point Entry Field.\n"
              "\n"
              "The point coordinates can be captured by\n"
              "left click on canvas together with pressing\n"
              "SHIFT key. \n"
              "Then click Add button to insert coordinates.\n"
              "Or enter the coords in format (x, y) in the\n"
              "Point Entry field and click Flip on X(Y)"))
        grid0.addWidget(self.mirror_reference_cb, 13, 0, 1, 2)

        self.flip_ref_label = QtWidgets.QLabel('%s' % _("Mirror Reference point"))
        self.flip_ref_label.setToolTip(
            _("Coordinates in format (x, y) used as reference for mirroring.\n"
              "The 'x' in (x, y) will be used when using Flip on X and\n"
              "the 'y' in (x, y) will be used when using Flip on Y and")
        )
        self.flip_ref_entry = FCEntry()

        grid0.addWidget(self.flip_ref_label, 14, 0, 1, 2)
        grid0.addWidget(self.flip_ref_entry, 15, 0, 1, 2)

        # ## Buffer
        buffer_title_lbl = QtWidgets.QLabel('<b>%s</b>' % _("Buffer"))
        grid0.addWidget(buffer_title_lbl, 16, 0, 1, 2)

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
        self.buffer_entry.set_range(-9999.9999, 9999.9999)

        grid0.addWidget(self.buffer_label, 17, 0)
        grid0.addWidget(self.buffer_entry, 17, 1)

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

        grid0.addWidget(self.buffer_factor_label, 18, 0)
        grid0.addWidget(self.buffer_factor_entry, 18, 1)

        self.buffer_rounded_cb = FCCheckBox()
        self.buffer_rounded_cb.setText('%s' % _("Rounded"))
        self.buffer_rounded_cb.setToolTip(
            _("If checked then the buffer will surround the buffered shape,\n"
              "every corner will be rounded.\n"
              "If not checked then the buffer will follow the exact geometry\n"
              "of the buffered shape.")
        )

        grid0.addWidget(self.buffer_rounded_cb, 19, 0, 1, 2)

        self.layout.addStretch()
