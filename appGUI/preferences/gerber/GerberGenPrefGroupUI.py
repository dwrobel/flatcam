
from PyQt6 import QtCore, QtGui, QtWidgets

from appGUI.GUIElements import FCCheckBox, FCSpinner, RadioSet, FCButton, FCSliderWithSpinner, FCLabel, \
    GLay, FCFrame, FCTable, FCColorEntry, OptionalInputSection
from appGUI.preferences.OptionsGroupUI import OptionsGroupUI

from copy import deepcopy

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GerberGenPrefGroupUI(OptionsGroupUI):
    def __init__(self, app, parent=None):
        # OptionsGroupUI.__init__(self, "Gerber General Preferences", parent=parent)
        super(GerberGenPrefGroupUI, self).__init__(self, parent=parent)

        self.setTitle(str(_("General")))
        self.decimals = app.decimals
        self.options = app.options

        # ## Plot options
        self.plot_options_label = FCLabel('%s' % _("Plot Options"), color='blue', bold=True)
        self.layout.addWidget(self.plot_options_label)

        # #############################################################################################################
        # Plot Frame
        # #############################################################################################################

        plot_frame = FCFrame()
        self.layout.addWidget(plot_frame)

        # ## Grid Layout
        plot_grid = GLay(v_spacing=5, h_spacing=3)
        plot_frame.setLayout(plot_grid)

        # Plot CB
        self.plot_cb = FCCheckBox(label='%s' % _('Plot'))
        self.plot_options_label.setToolTip(
            _("Plot (show) this object.")
        )
        plot_grid.addWidget(self.plot_cb, 0, 0)

        # Solid CB
        self.solid_cb = FCCheckBox(label='%s' % _('Solid'))
        self.solid_cb.setToolTip(
            _("Solid color polygons.")
        )
        plot_grid.addWidget(self.solid_cb, 0, 1)

        # Multicolored CB
        self.multicolored_cb = FCCheckBox(label='%s' % _('M-Color'))
        self.multicolored_cb.setToolTip(
            _("Draw polygons in different colors.")
        )
        plot_grid.addWidget(self.multicolored_cb, 0, 2)

        # Number of circle steps for circular aperture linear approximation
        self.circle_steps_label = FCLabel('%s:' % _("Circle Steps"))
        self.circle_steps_label.setToolTip(
            _("The number of circle steps for \n"
              "linear approximation of circles.")
        )
        self.circle_steps_entry = FCSpinner()
        self.circle_steps_entry.set_range(0, 9999)

        plot_grid.addWidget(self.circle_steps_label, 2, 0)
        plot_grid.addWidget(self.circle_steps_entry, 2, 1, 1, 2)

        # #############################################################################################################
        # Default Values Frame
        # #############################################################################################################

        # Default format for Gerber
        self.gerber_default_label = FCLabel('%s' % _("Default Values"), color='green', bold=True)
        self.gerber_default_label.setToolTip(
            _("Those values will be used as fallback values\n"
              "in case that they are not found in the Gerber file.")
        )

        self.layout.addWidget(self.gerber_default_label)

        def_frame = FCFrame()
        self.layout.addWidget(def_frame)

        # ## Grid Layout
        def_grid = GLay(v_spacing=5, h_spacing=3)
        def_frame.setLayout(def_grid)

        # Gerber Units
        self.gerber_units_label = FCLabel('%s:' % _('Units'))
        self.gerber_units_label.setToolTip(
            _("The units used in the Gerber file.")
        )

        self.gerber_units_radio = RadioSet([{'label': _('Inch'), 'value': 'IN'},
                                            {'label': _('mm'), 'value': 'MM'}], compact=True)
        self.gerber_units_radio.setToolTip(
            _("The units used in the Gerber file.")
        )

        def_grid.addWidget(self.gerber_units_label, 0, 0)
        def_grid.addWidget(self.gerber_units_radio, 0, 1, 1, 2)

        # Gerber Zeros
        self.gerber_zeros_label = FCLabel('%s:' % _('Zeros'))
        self.gerber_zeros_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.gerber_zeros_label.setToolTip(
            _("This sets the type of Gerber zeros.\n"
              "If LZ then Leading Zeros are removed and\n"
              "Trailing Zeros are kept.\n"
              "If TZ is checked then Trailing Zeros are removed\n"
              "and Leading Zeros are kept.")
        )

        self.gerber_zeros_radio = RadioSet([{'label': _('LZ'), 'value': 'L'},
                                            {'label': _('TZ'), 'value': 'T'}], compact=True)
        self.gerber_zeros_radio.setToolTip(
            _("This sets the type of Gerber zeros.\n"
              "If LZ then Leading Zeros are removed and\n"
              "Trailing Zeros are kept.\n"
              "If TZ is checked then Trailing Zeros are removed\n"
              "and Leading Zeros are kept.")
        )

        def_grid.addWidget(self.gerber_zeros_label, 2, 0)
        def_grid.addWidget(self.gerber_zeros_radio, 2, 1, 1, 2)

        # #############################################################################################################
        # Parameters Frame
        # #############################################################################################################
        self.param_label = FCLabel('%s' % _("Parameters"), color='indigo', bold=True)
        self.layout.addWidget(self.param_label)

        par_frame = FCFrame()
        self.layout.addWidget(par_frame)

        # ## Grid Layout
        param_grid = GLay(v_spacing=5, h_spacing=3)
        par_frame.setLayout(param_grid)

        # Apertures Cleaning
        self.gerber_clean_cb = FCCheckBox(label='%s' % _('Clean Apertures'))
        self.gerber_clean_cb.setToolTip(
            _("Will remove apertures that do not have geometry\n"
              "thus lowering the number of apertures in the Gerber object.")
        )
        param_grid.addWidget(self.gerber_clean_cb, 0, 0, 1, 3)

        # Apply Extra Buffering
        self.gerber_extra_buffering = FCCheckBox(label='%s' % _('Polarity change buffer'))
        self.gerber_extra_buffering.setToolTip(
            _("Will apply extra buffering for the\n"
              "solid geometry when we have polarity changes.\n"
              "May help loading Gerber files that otherwise\n"
              "do not load correctly.")
        )
        param_grid.addWidget(self.gerber_extra_buffering, 2, 0, 1, 3)

        # Plot on Select
        self.gerber_plot_on_select_cb = FCCheckBox(label='%s' % _('Plot on Select'))
        self.gerber_plot_on_select_cb.setToolTip(
            _("When active, selecting an object in the Project tab will replot it above the others.")
        )
        param_grid.addWidget(self.gerber_plot_on_select_cb, 4, 0, 1, 3)

        # #############################################################################################################
        # Layers Frame
        # #############################################################################################################
        # Layers label
        self.layers_label = FCLabel('%s' % _("Layers"), color='magenta', bold=True)
        self.layout.addWidget(self.layers_label)

        layers_frame = FCFrame()
        self.layout.addWidget(layers_frame)

        # ## Grid Layout
        layers_grid = GLay(v_spacing=5, h_spacing=3)
        layers_frame.setLayout(layers_grid)

        # Store colors
        self.store_colors_cb = FCCheckBox(label='%s' % _('Store colors'))
        self.store_colors_cb.setToolTip(
            _("It will store the set colors for Gerber objects.\n"
              "Those will be used each time the application is started.")
        )
        layers_grid.addWidget(self.store_colors_cb, 0, 0, 1, 3)

        # Layers color manager
        self.layers_button = FCButton()
        self.layers_button.setText('%s' % _('Color manager'))
        self.layers_button.setIcon(QtGui.QIcon(self.app.resource_location + '/set_colors64.png'))
        self.layers_button.setToolTip(
            _("Manage colors associated with Gerber objects.")
        )

        # Clear stored colors
        self.clear_colors_button = QtWidgets.QToolButton()
        # self.clear_colors_button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        # self.clear_colors_button.setText('%s' % _('Clear Colors'))
        self.clear_colors_button.setIcon(QtGui.QIcon(self.app.resource_location + '/trash32.png'))
        self.clear_colors_button.setToolTip(
            _("Reset the colors associated with Gerber objects.")
        )

        layers_grid.addWidget(self.layers_button, 2, 0, 1, 2)
        layers_grid.addWidget(self.clear_colors_button, 2, 3)

        # separator_line = QtWidgets.QFrame()
        # separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        # separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        # plot_grid.addWidget(separator_line, 13, 0, 1, 3)

        # #############################################################################################################
        # Object Frame
        # #############################################################################################################
        # Gerber Object Color
        self.gerber_color_label = FCLabel('%s' % _("Object Color"), color='darkorange', bold=True)
        self.layout.addWidget(self.gerber_color_label)

        obj_frame = FCFrame()
        self.layout.addWidget(obj_frame)

        # ## Grid Layout
        obj_grid = GLay(v_spacing=5, h_spacing=3)
        obj_frame.setLayout(obj_grid)

        # Enable Outline plotting
        self.enable_line_cb = FCCheckBox(label='%s' % _('Outline'))
        self.enable_line_cb.setToolTip(
            _("If checked, the polygon outline will be plotted on canvas.\n"
              "Plotting the outline require more processing power but looks nicer.")
        )
        obj_grid.addWidget(self.enable_line_cb, 0, 0, 1, 2)

        # Plot Line Color
        self.line_color_label = FCLabel('%s:' % _('Outline'))
        self.line_color_label.setToolTip(
            _("Set the line color for plotted objects.")
        )
        self.line_color_entry = FCColorEntry(icon=QtGui.QIcon(self.app.resource_location + '/set_colors64.png'))

        obj_grid.addWidget(self.line_color_label, 2, 0)
        obj_grid.addWidget(self.line_color_entry, 2, 1, 1, 2)

        self.outline_ois = OptionalInputSection(self.enable_line_cb, [self.line_color_label, self.line_color_entry])

        # Plot Fill Color
        self.fill_color_label = FCLabel('%s:' % _('Fill'))
        self.fill_color_label.setToolTip(
            _("Set the fill color for plotted objects.\n"
              "First 6 digits are the color and the last 2\n"
              "digits are for alpha (transparency) level.")
        )
        self.fill_color_entry = FCColorEntry(icon=QtGui.QIcon(self.app.resource_location + '/set_colors64.png'))

        obj_grid.addWidget(self.fill_color_label, 4, 0)
        obj_grid.addWidget(self.fill_color_entry, 4, 1, 1, 2)

        # Plot Fill Transparency Level
        self.gerber_alpha_label = FCLabel('%s:' % _('Alpha'))
        self.gerber_alpha_label.setToolTip(
            _("Set the fill transparency for plotted objects.")
        )
        self.gerber_alpha_entry = FCSliderWithSpinner(0, 255, 1)

        obj_grid.addWidget(self.gerber_alpha_label, 6, 0)
        obj_grid.addWidget(self.gerber_alpha_entry, 6, 1, 1, 2)

        GLay.set_common_column_size([plot_grid, param_grid, def_grid, obj_grid], 0)

        self.layout.addStretch()

        # Setting plot colors signals
        self.line_color_entry.editingFinished.connect(self.on_line_color_changed)
        self.fill_color_entry.editingFinished.connect(self.on_fill_color_changed)

        self.gerber_alpha_entry.valueChanged.connect(self.on_gerber_alpha_changed)  # alpha

        self.layers_button.clicked.connect(self.on_layers_manager)
        self.clear_colors_button.clicked.connect(self.on_colors_clear_clicked)

    # Setting plot colors handlers
    def on_fill_color_changed(self):
        """
        Will set the default fill color for the Gerber Object
        :return:
        :rtype:
        """
        self.app.options['gerber_plot_fill'] = self.fill_color_entry.get_value()[:7] + \
                                                self.app.options['gerber_plot_fill'][7:9]

    def on_gerber_alpha_changed(self, spinner_value):
        """
        Will set the default alpha (transparency) for the Gerber Object
        :param spinner_value:   alpha level
        :type spinner_value:    int
        :return:
        :rtype:
        """
        self.app.options['gerber_plot_fill'] = \
            self.app.options['gerber_plot_fill'][:7] + \
            (hex(spinner_value)[2:] if int(hex(spinner_value)[2:], 16) > 0 else '00')
        self.app.options['gerber_plot_line'] = \
            self.app.options['gerber_plot_line'][:7] + \
            (hex(spinner_value)[2:] if int(hex(spinner_value)[2:], 16) > 0 else '00')

    def on_line_color_changed(self):
        """
        Will set the default outline color for the Gerber Object
        :return:
        :rtype:
        """
        self.app.options['gerber_plot_line'] = (self.line_color_entry.get_value()[:7] +
                                                 self.app.options['gerber_plot_line'][7:9])

    def on_colors_clear_clicked(self):
        """
        Clear the list that stores the colors for the Gerber Objects
        :return:
        :rtype:
        """
        self.app.options["gerber_color_list"].clear()
        self.app.inform.emit('[WARNING_NOTCL] %s' % _("Stored colors for Gerber objects are deleted."))

    def on_layers_manager(self):
        color_box = ColorsManager(app=self.app, parent=self)

        if color_box.ok is True:
            color_box.update_color_list()
            self.options["gerber_color_list"] = color_box.color_list


class ColorsManager(QtWidgets.QDialog):
    def __init__(self, app, parent):
        """
        A Dialog to show the color's manager
        :param parent:
        :type parent:
        """
        super(ColorsManager, self).__init__(parent=parent)
        self.app = app

        self.ok = False
        self.color_list = []
        self.original_color_list = deepcopy(self.app.options["gerber_color_list"])

        self.setWindowIcon(QtGui.QIcon(self.app.resource_location + '/set_colors64.png'))
        self.setWindowTitle('%s' % _('Color manager'))

        self.layout = QtWidgets.QVBoxLayout(self)

        # #############################################################################################################
        # ################################ Layers Frame ###############################################################
        # #############################################################################################################
        layers_frame = FCFrame()
        layers_frame.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.Expanding)
        self.layout.addWidget(layers_frame)

        layers_grid = GLay(v_spacing=5, h_spacing=3)
        layers_frame.setLayout(layers_grid)

        # Layers Colors Table
        self.colors_table = FCTable()
        layers_grid.addWidget(self.colors_table, 0, 0, 1, 2)
        # self.colors_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.colors_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)

        self.colors_table.setColumnCount(3)
        self.colors_table.setColumnWidth(0, 20)
        self.colors_table.setHorizontalHeaderLabels(['#', _('Name'), _("Color")])

        self.colors_table.horizontalHeaderItem(0).setToolTip(_("ID"))
        self.colors_table.horizontalHeaderItem(1).setToolTip(_("Name"))
        self.colors_table.horizontalHeaderItem(2).setToolTip('%s.' % _("Color"))

        self.layout.addStretch(1)

        lay_hlay = QtWidgets.QHBoxLayout()

        # Add layer
        self.add_button = FCButton()
        self.add_button.setText('%s' % _("Add"))
        self.add_button.setIcon(QtGui.QIcon(self.app.resource_location + '/plus16.png'))
        self.add_button.setToolTip(
            _("Add a new layer.")
        )

        # Delete layer
        self.delete_button = FCButton()
        self.delete_button.setText('%s' % _("Delete"))
        self.delete_button.setIcon(QtGui.QIcon(self.app.resource_location + '/trash32.png'))
        self.delete_button.setToolTip(
            _("Delete the last layers.")
        )
        lay_hlay.addWidget(self.add_button)
        lay_hlay.addWidget(self.delete_button)

        layers_grid.addLayout(lay_hlay, 2, 0, 1, 2)

        # #############################################################################################################
        # ######################################## Button Grid ########################################################
        # #############################################################################################################
        button_grid = GLay(h_spacing=5, v_spacing=5)
        self.layout.addLayout(button_grid)

        self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok |
                                                     QtWidgets.QDialogButtonBox.StandardButton.Cancel,
                                                     orientation=QtCore.Qt.Orientation.Horizontal, parent=self)
        button_grid.addWidget(self.button_box, 8, 0, 1, 2)

        self.button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).setText(_("Ok"))
        self.button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel).setText(_("Cancel"))

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.add_button.clicked.connect(self.on_layer_add)
        self.delete_button.clicked.connect(self.on_layer_delete)

        self.build_ui()

        self.ok = True if self.exec() == QtWidgets.QDialog.DialogCode.Accepted else False

    def build_ui(self):
        n = len(self.original_color_list)
        self.colors_table.setRowCount(n)

        color_id = 0
        for color in range(n):
            color_id += 1

            # ------------------------  ID ----------------------------------------------------------------------------
            id_ = QtWidgets.QTableWidgetItem('%d' % int(color_id))
            flags = QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled
            id_.setFlags(flags)
            row_no = color_id - 1
            self.colors_table.setItem(row_no, 0, id_)  # Tool name/id

            # ------------------------ Name ----------------------------------------------------------------------------
            if self.original_color_list[color][2] == '':
                name = '%s_%d' % (_("Layer"), int(color_id))
            else:
                name = self.original_color_list[color][2]

            name_item = QtWidgets.QTableWidgetItem(name)
            name_item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
            self.colors_table.setItem(row_no, 1, name_item)  # Name

            # ------------------------ Color Widget --------------------------------------------------------------------
            color_item = FCColorEntry(icon=QtGui.QIcon(self.app.resource_location + '/set_colors64.png'))
            color_item.set_value(self.original_color_list[color][1])
            self.colors_table.setCellWidget(row_no, 2, color_item)

        # make the name column editable
        for row in range(color_id):
            flags = QtCore.Qt.ItemFlag.ItemIsEditable | QtCore.Qt.ItemFlag.ItemIsSelectable | \
                    QtCore.Qt.ItemFlag.ItemIsEnabled
            self.colors_table.item(row, 1).setFlags(flags)

        self.colors_table.resizeColumnsToContents()
        self.colors_table.resizeRowsToContents()

        vertical_header = self.colors_table.verticalHeader()
        vertical_header.hide()
        self.colors_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        horizontal_header = self.colors_table.horizontalHeader()
        horizontal_header.setMinimumSectionSize(10)
        horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Fixed)
        horizontal_header.resizeSection(0, 20)
        horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)

        self.colors_table.setMinimumHeight(self.colors_table.getHeight())
        self.colors_table.setMaximumHeight(self.colors_table.getHeight())

        self.colors_table.setMinimumWidth(self.colors_table.getWidth())

    def update_color_list(self):
        n = len(self.original_color_list)
        for row in range(n):
            fill_color = self.colors_table.cellWidget(row, 2).get_value()
            line_color = fill_color[:-2]
            layer_name = self.colors_table.item(row, 1).text()
            self.color_list.append(
                (
                    line_color,
                    fill_color,
                    layer_name
                )
            )

    def on_layer_add(self):
        list_len = len(self.original_color_list)
        if list_len is None:
            layer_nr = 0
        else:
            layer_nr = list_len
        self.original_color_list.append(
            (
                self.app.options['gerber_plot_line'],
                self.app.options['gerber_plot_fill'],
                '%s_%d' % (_("Layer"), layer_nr)
            )
        )
        self.build_ui()

    def on_layer_delete(self):
        sel_rows = set()
        for it in self.colors_table.selectedItems():
            sel_rows.add(it.row())

        table_len = self.colors_table.rowCount()

        if (table_len - 1) in sel_rows:
            self.colors_table.removeRow(table_len - 1)
            self.original_color_list.pop()
            self.build_ui()
            self.on_layer_delete()
