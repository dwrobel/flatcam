from PyQt6 import QtWidgets

from appGUI.GUIElements import FCCheckBox, FCSpinner, FCEntry, FCColorEntry, RadioSet, FCLabel, FCGridLayout
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

import platform

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GeometryGenPrefGroupUI(OptionsGroupUI):
    def __init__(self, defaults, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "Geometry General Preferences", parent=parent)
        super(GeometryGenPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("Geometry General")))
        self.decimals = decimals
        self.defaults = defaults

        # ## Plot options
        self.plot_options_label = FCLabel("<b>%s:</b>" % _("Plot Options"))
        self.layout.addWidget(self.plot_options_label)

        plot_hlay = QtWidgets.QHBoxLayout()
        self.layout.addLayout(plot_hlay)

        # Plot CB
        self.plot_cb = FCCheckBox(label=_('Plot'))
        self.plot_cb.setToolTip(
            _("Plot (show) this object.")
        )
        plot_hlay.addWidget(self.plot_cb)

        # Multicolored CB
        self.multicolored_cb = FCCheckBox(label=_('M-Color'))
        self.multicolored_cb.setToolTip(
            _("Draw polygons in different colors.")
        )
        plot_hlay.addWidget(self.multicolored_cb)

        grid0 = FCGridLayout(v_spacing=5, h_spacing=3)
        self.layout.addLayout(grid0)

        # Number of circle steps for circular aperture linear approximation
        self.circle_steps_label = FCLabel('%s:' % _("Circle Steps"))
        self.circle_steps_label.setToolTip(
            _("The number of circle steps for <b>Geometry</b> \n"
              "circle and arc shapes linear approximation.")
        )
        self.circle_steps_entry = FCSpinner()
        self.circle_steps_entry.set_range(0, 999)

        grid0.addWidget(self.circle_steps_label, 1, 0)
        grid0.addWidget(self.circle_steps_entry, 1, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        grid0.addWidget(separator_line, 9, 0, 1, 2)

        self.opt_label = FCLabel("<b>%s:</b>" % _("Path Optimization"))
        grid0.addWidget(self.opt_label, 10, 0, 1, 2)

        self.opt_algorithm_label = FCLabel(_('Algorithm:'))
        self.opt_algorithm_label.setToolTip(
            _("This sets the path optimization algorithm.\n"
              "- Rtre -> Rtree algorithm\n"
              "- MetaHeuristic -> Google OR-Tools algorithm with\n"
              "MetaHeuristic Guided Local Path is used. Default search time is 3sec.\n"
              "- Basic -> Using Google OR-Tools Basic algorithm\n"
              "- TSA -> Using Travelling Salesman algorithm\n"
              "\n"
              "Some options are disabled when the application works in 32bit mode.")
        )

        self.opt_algorithm_radio = RadioSet(
            [
                {'label': _('Rtree'), 'value': 'R'},
                {'label': _('MetaHeuristic'), 'value': 'M'},
                {'label': _('Basic'), 'value': 'B'},
                {'label': _('TSA'), 'value': 'T'}
            ], orientation='vertical', compact=True)

        grid0.addWidget(self.opt_algorithm_label, 12, 0)
        grid0.addWidget(self.opt_algorithm_radio, 12, 1)

        self.optimization_time_label = FCLabel('%s:' % _('Duration'))
        self.optimization_time_label.setToolTip(
            _("When OR-Tools Metaheuristic (MH) is enabled there is a\n"
              "maximum threshold for how much time is spent doing the\n"
              "path optimization. This max duration is set here.\n"
              "In seconds.")

        )

        self.optimization_time_entry = FCSpinner()
        self.optimization_time_entry.set_range(0, 999)

        grid0.addWidget(self.optimization_time_label, 14, 0)
        grid0.addWidget(self.optimization_time_entry, 14, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        grid0.addWidget(separator_line, 16, 0, 1, 2)

        # Fuse Tools
        self.join_geo_label = FCLabel('<b>%s</b>:' % _('Join Option'))
        grid0.addWidget(self.join_geo_label, 18, 0, 1, 2)

        self.fuse_tools_cb = FCCheckBox(_("Fuse Tools"))
        self.fuse_tools_cb.setToolTip(
            _("When checked, the tools will be merged\n"
              "but only if they share some of their attributes.")
        )
        grid0.addWidget(self.fuse_tools_cb, 20, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        grid0.addWidget(separator_line, 22, 0, 1, 2)

        # Geometry Object Color
        self.gerber_color_label = FCLabel('<b>%s</b>:' % _('Object Color'))
        grid0.addWidget(self.gerber_color_label, 24, 0, 1, 2)

        # Plot Line Color
        self.line_color_label = FCLabel('%s:' % _('Outline'))
        self.line_color_label.setToolTip(
            _("Set the line color for plotted objects.")
        )
        self.line_color_entry = FCColorEntry()

        grid0.addWidget(self.line_color_label, 26, 0)
        grid0.addWidget(self.line_color_entry, 26, 1)

        self.layout.addStretch()

        current_platform = platform.architecture()[0]
        if current_platform == '64bit':
            self.opt_algorithm_radio.setOptionsDisabled([_('MetaHeuristic'), _('Basic')], False)
            self.optimization_time_label.setDisabled(False)
            self.optimization_time_entry.setDisabled(False)
        else:
            self.opt_algorithm_radio.setOptionsDisabled([_('MetaHeuristic'), _('Basic')], True)
            self.optimization_time_label.setDisabled(True)
            self.optimization_time_entry.setDisabled(True)

        self.opt_algorithm_radio.activated_custom.connect(self.optimization_selection)

        # Setting plot colors signals
        self.line_color_entry.editingFinished.connect(self.on_line_color_entry)

    def on_line_color_entry(self):
        self.app.defaults['geometry_plot_line'] = self.line_color_entry.get_value()[:7] + 'FF'

    def optimization_selection(self, val):
        if platform.architecture()[0] != '64bit':
            # set Geometry path optimizations algorithm to Rtree if the app is run on a 32bit platform
            # modes 'M' or 'B' are not allowed when the app is running in 32bit platform
            if val in ['M', 'B']:
                self.opt_algorithm_radio.blockSignals(True)
                self.opt_algorithm_radio.set_value('R')
                self.opt_algorithm_radio.blockSignals(False)

        if val == 'M':
            self.optimization_time_label.setDisabled(False)
            self.optimization_time_entry.setDisabled(False)
        else:
            self.optimization_time_label.setDisabled(True)
            self.optimization_time_entry.setDisabled(True)
