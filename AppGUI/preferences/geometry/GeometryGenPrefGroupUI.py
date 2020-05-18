from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QSettings

from AppGUI.GUIElements import FCCheckBox, FCSpinner, FCEntry
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


class GeometryGenPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "Geometry General Preferences", parent=parent)
        super(GeometryGenPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Geometry General")))
        self.decimals = decimals

        # ## Plot options
        self.plot_options_label = QtWidgets.QLabel("<b>%s:</b>" % _("Plot Options"))
        self.layout.addWidget(self.plot_options_label)

        # Plot CB
        self.plot_cb = FCCheckBox(label=_('Plot'))
        self.plot_cb.setToolTip(
            _("Plot (show) this object.")
        )
        self.layout.addWidget(self.plot_cb)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)

        # Number of circle steps for circular aperture linear approximation
        self.circle_steps_label = QtWidgets.QLabel('%s:' % _("Circle Steps"))
        self.circle_steps_label.setToolTip(
            _("The number of circle steps for <b>Geometry</b> \n"
              "circle and arc shapes linear approximation.")
        )
        self.circle_steps_entry = FCSpinner()
        self.circle_steps_entry.set_range(0, 999)

        grid0.addWidget(self.circle_steps_label, 1, 0)
        grid0.addWidget(self.circle_steps_entry, 1, 1)

        # Tools
        self.tools_label = QtWidgets.QLabel("<b>%s:</b>" % _("Tools"))
        grid0.addWidget(self.tools_label, 2, 0, 1, 2)

        # Tooldia
        tdlabel = QtWidgets.QLabel('<b><font color="green">%s:</font></b>' % _('Tools Dia'))
        tdlabel.setToolTip(
            _("Diameters of the tools, separated by comma.\n"
              "The value of the diameter has to use the dot decimals separator.\n"
              "Valid values: 0.3, 1.0")
        )
        self.cnctooldia_entry = FCEntry()

        grid0.addWidget(tdlabel, 3, 0)
        grid0.addWidget(self.cnctooldia_entry, 3, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 9, 0, 1, 2)

        # Geometry Object Color
        self.gerber_color_label = QtWidgets.QLabel('<b>%s</b>' % _('Geometry Object Color'))
        grid0.addWidget(self.gerber_color_label, 10, 0, 1, 2)

        # Plot Line Color
        self.line_color_label = QtWidgets.QLabel('%s:' % _('Outline'))
        self.line_color_label.setToolTip(
            _("Set the line color for plotted objects.")
        )
        self.line_color_entry = FCEntry()
        self.line_color_button = QtWidgets.QPushButton()
        self.line_color_button.setFixedSize(15, 15)

        self.form_box_child_2 = QtWidgets.QHBoxLayout()
        self.form_box_child_2.addWidget(self.line_color_entry)
        self.form_box_child_2.addWidget(self.line_color_button)
        self.form_box_child_2.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        grid0.addWidget(self.line_color_label, 11, 0)
        grid0.addLayout(self.form_box_child_2, 11, 1)

        self.layout.addStretch()

        # Setting plot colors signals
        self.line_color_entry.editingFinished.connect(self.on_line_color_entry)
        self.line_color_button.clicked.connect(self.on_line_color_button)

    def on_line_color_entry(self):
        self.app.defaults['geometry_plot_line'] = self.line_color_entry.get_value()[:7] + 'FF'
        self.line_color_button.setStyleSheet("background-color:%s" % str(self.app.defaults['geometry_plot_line'])[:7])

    def on_line_color_button(self):
        current_color = QtGui.QColor(self.app.defaults['geometry_plot_line'][:7])
        # print(current_color)

        c_dialog = QtWidgets.QColorDialog()
        plot_line_color = c_dialog.getColor(initial=current_color)

        if plot_line_color.isValid() is False:
            return

        self.line_color_button.setStyleSheet("background-color:%s" % str(plot_line_color.name()))

        new_val_line = str(plot_line_color.name()) + str(self.app.defaults['geometry_plot_line'][7:9])
        self.line_color_entry.set_value(new_val_line)
