
from appTool import *

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ExcSlotArrayEditorTool(AppTool):
    """
    Create an array of drill holes
    """

    def __init__(self, app, draw_app, plugin_name):
        AppTool.__init__(self, app)

        self.draw_app = draw_app
        self.decimals = app.decimals
        self.plugin_name = plugin_name

        self.ui = ExcSlotArrayEditorUI(layout=self.layout, sarray_class=self, plugin_name=plugin_name)

        self.connect_signals_at_init()
        self.set_tool_ui()

    def connect_signals_at_init(self):
        # Signals
        pass

    def disconnect_signals(self):
        # Signals
        pass

    def run(self):
        self.app.defaults.report_usage("Exc Editor ArrayTool()")
        AppTool.run(self)

        # if the splitter us hidden, display it
        if self.app.ui.splitter.sizes()[0] == 0:
            self.app.ui.splitter.setSizes([1, 1])

        # if the Tool Tab is hidden display it, else hide it but only if the objectName is the same
        found_idx = None
        for idx in range(self.app.ui.notebook.count()):
            if self.app.ui.notebook.widget(idx).objectName() == "plugin_tab":
                found_idx = idx
                break
        # show the Tab
        if not found_idx:
            try:
                self.app.ui.notebook.addTab(self.app.ui.plugin_tab, _("Plugin"))
            except RuntimeError:
                self.app.ui.plugin_tab = QtWidgets.QWidget()
                self.app.ui.plugin_tab.setObjectName("plugin_tab")
                self.app.ui.plugin_tab_layout = QtWidgets.QVBoxLayout(self.app.ui.plugin_tab)
                self.app.ui.plugin_tab_layout.setContentsMargins(2, 2, 2, 2)

                self.app.ui.plugin_scroll_area = VerticalScrollArea()
                self.app.ui.plugin_tab_layout.addWidget(self.app.ui.plugin_scroll_area)
                self.app.ui.notebook.addTab(self.app.ui.plugin_tab, _("Plugin"))

            # focus on Tool Tab
            self.app.ui.notebook.setCurrentWidget(self.app.ui.plugin_tab)

        # self.app.ui.notebook.callback_on_close = self.on_tab_close

        self.app.ui.notebook.setTabText(2, self.plugin_name)

    def set_tool_ui(self):
        # Init appGUI
        pass

    def on_tab_close(self):
        self.disconnect_signals()
        self.hide_tool()
        # self.app.ui.notebook.callback_on_close = lambda: None

    def on_clear(self):
        self.set_tool_ui()

    def hide_tool(self):
        self.ui.sarray_frame.hide()
        self.app.ui.notebook.setCurrentWidget(self.app.ui.properties_tab)
        if self.draw_app.active_tool.name != 'select':
            self.draw_app.select_tool("select")


class ExcSlotArrayEditorUI:

    def __init__(self, layout, sarray_class, plugin_name):
        self.pluginName = plugin_name
        self.ed_class = sarray_class
        self.decimals = self.ed_class.app.decimals
        self.layout = layout
        self.app = self.ed_class.app

        # Title
        title_label = FCLabel("%s" % ('Editor ' + self.pluginName))
        title_label.setStyleSheet("""
                                QLabel
                                {
                                    font-size: 16px;
                                    font-weight: bold;
                                }
                                """)
        self.layout.addWidget(title_label)

        # this way I can hide/show the frame
        self.sarray_frame = QtWidgets.QFrame()
        self.sarray_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.sarray_frame)

        self.editor_vbox = QtWidgets.QVBoxLayout()
        self.editor_vbox.setContentsMargins(0, 0, 0, 0)
        self.sarray_frame.setLayout(self.editor_vbox)

        # Position
        self.tool_lbl = FCLabel('%s' % _("Tool Diameter"), bold=True, color='blue')
        self.editor_vbox.addWidget(self.tool_lbl)
        # #############################################################################################################
        # Diameter Frame
        # #############################################################################################################
        dia_frame = FCFrame()
        self.editor_vbox.addWidget(dia_frame)

        dia_grid = GLay(v_spacing=5, h_spacing=3, c_stretch=[0, 1, 0])
        dia_frame.setLayout(dia_grid)

        # Dia Value
        self.dia_lbl = FCLabel('%s:' % _("Value"))
        self.dia_entry = NumericalEvalEntry(border_color='#0069A9')
        self.dia_entry.setDisabled(True)
        self.dia_unit = FCLabel('%s' % 'mm')

        dia_grid.addWidget(self.dia_lbl, 0, 0)
        dia_grid.addWidget(self.dia_entry, 0, 1)
        dia_grid.addWidget(self.dia_unit, 0, 2)

        # Position
        self.pos_lbl = FCLabel('%s' % _("Position"), bold=True, color='red')
        self.editor_vbox.addWidget(self.pos_lbl)
        # #############################################################################################################
        # Position Frame
        # #############################################################################################################
        pos_frame = FCFrame()
        self.editor_vbox.addWidget(pos_frame)

        pos_grid = GLay(v_spacing=5, h_spacing=3)
        pos_frame.setLayout(pos_grid)

        # X Pos
        self.x_lbl = FCLabel('%s:' % _("X"))
        self.x_entry = FCDoubleSpinner()
        self.x_entry.set_precision(self.decimals)
        self.x_entry.set_range(-10000.0000, 10000.0000)
        pos_grid.addWidget(self.x_lbl, 2, 0)
        pos_grid.addWidget(self.x_entry, 2, 1)

        # Y Pos
        self.y_lbl = FCLabel('%s:' % _("Y"))
        self.y_entry = FCDoubleSpinner()
        self.y_entry.set_precision(self.decimals)
        self.y_entry.set_range(-10000.0000, 10000.0000)
        pos_grid.addWidget(self.y_lbl, 4, 0)
        pos_grid.addWidget(self.y_entry, 4, 1)

        # Slot Parameters
        self.slot_label = FCLabel('%s' % _("Slot"), bold=True, color='green')
        self.slot_label.setToolTip(
            _("Parameters for adding a slot (hole with oval shape)\n"
              "either single or as an part of an array.")
        )
        self.editor_vbox.addWidget(self.slot_label)
        # #############################################################################################################
        # ################################### Parameter Frame #########################################################
        # #############################################################################################################
        self.slot_frame = FCFrame()
        self.editor_vbox.addWidget(self.slot_frame)

        slot_grid = GLay(v_spacing=5, h_spacing=3)
        self.slot_frame.setLayout(slot_grid)

        # Slot length
        self.slot_length_label = FCLabel('%s:' % _('Length'))
        self.slot_length_label.setToolTip(
            _("Length. The length of the slot.")
        )

        self.slot_length_entry = FCDoubleSpinner(policy=False)
        self.slot_length_entry.set_precision(self.decimals)
        self.slot_length_entry.setSingleStep(0.1)
        self.slot_length_entry.setRange(0.0000, 10000.0000)

        slot_grid.addWidget(self.slot_length_label, 2, 0)
        slot_grid.addWidget(self.slot_length_entry, 2, 1)

        # Slot direction
        self.slot_axis_label = FCLabel('%s:' % _('Direction'))
        self.slot_axis_label.setToolTip(
            _("Direction on which the slot is oriented:\n"
              "- 'X' - horizontal axis \n"
              "- 'Y' - vertical axis or \n"
              "- 'Angle' - a custom angle for the slot inclination")
        )

        self.slot_direction_radio = RadioSet([{'label': _('X'), 'value': 'X'},
                                              {'label': _('Y'), 'value': 'Y'},
                                              {'label': _('Angle'), 'value': 'A'}])

        slot_grid.addWidget(self.slot_axis_label, 4, 0)
        slot_grid.addWidget(self.slot_direction_radio, 4, 1)

        # Slot custom angle
        self.slot_angle_label = FCLabel('%s:' % _('Angle'))
        self.slot_angle_label.setToolTip(
            _("Angle at which the slot is placed.\n"
              "The precision is of max 2 decimals.\n"
              "Min value is: -360.00 degrees.\n"
              "Max value is: 360.00 degrees.")
        )

        self.slot_angle_entry = FCDoubleSpinner(policy=False)
        self.slot_angle_entry.set_precision(self.decimals)
        self.slot_angle_entry.setWrapping(True)
        self.slot_angle_entry.setRange(-360.00, 360.00)
        self.slot_angle_entry.setSingleStep(1.0)

        slot_grid.addWidget(self.slot_angle_label, 6, 0)
        slot_grid.addWidget(self.slot_angle_entry, 6, 1)

        # Slot Array Title
        self.slot_array_label = FCLabel('%s' % _("Parameters"), bold=True, color='purple')
        self.slot_array_label.setToolTip(
            _("Array parameters.")
        )

        self.editor_vbox.addWidget(self.slot_array_label)
        # #############################################################################################################
        # ##################################### ADDING SLOT ARRAY  ####################################################
        # #############################################################################################################
        self.array_frame = FCFrame()
        self.editor_vbox.addWidget(self.array_frame)

        self.array_grid = GLay(v_spacing=5, h_spacing=3)
        self.array_frame.setLayout(self.array_grid)

        # Array Type
        array_type_lbl = FCLabel('%s:' % _("Type"))
        array_type_lbl.setToolTip(
            _("Select the type of slot array to create.\n"
              "It can be Linear X(Y) or Circular")
        )

        self.array_type_radio = RadioSet([
            {'label': _('Linear'), 'value': 'linear'},
            {'label': _('Circular'), 'value': 'circular'}])

        self.array_grid.addWidget(array_type_lbl, 2, 0)
        self.array_grid.addWidget(self.array_type_radio, 2, 1)

        # Array Size
        self.array_size_label = FCLabel('%s:' % _('Size'))
        self.array_size_label.setToolTip(_("Specify how many slots to be in the array."))

        self.array_size_entry = FCSpinner(policy=False)
        self.array_size_entry.set_range(0, 10000)

        self.array_grid.addWidget(self.array_size_label, 4, 0)
        self.array_grid.addWidget(self.array_size_entry, 4, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.array_grid.addWidget(separator_line, 6, 0, 1, 2)

        # #############################################################################################################
        # ##################################### Linear SLOT ARRAY  ####################################################
        # #############################################################################################################
        self.array_linear_frame = QtWidgets.QFrame()
        self.array_linear_frame.setContentsMargins(0, 0, 0, 0)
        self.array_grid.addWidget(self.array_linear_frame, 8, 0, 1, 2)

        self.array_lin_grid = GLay(v_spacing=5, h_spacing=3)
        self.array_lin_grid.setContentsMargins(0, 0, 0, 0)
        self.array_linear_frame.setLayout(self.array_lin_grid)

        # Linear Slot Array direction
        self.slot_array_axis_label = FCLabel('%s:' % _('Direction'))
        self.slot_array_axis_label.setToolTip(
            _("Direction on which the linear array is oriented:\n"
              "- 'X' - horizontal axis \n"
              "- 'Y' - vertical axis or \n"
              "- 'Angle' - a custom angle for the array inclination")
        )

        self.array_axis_radio = RadioSet([
            {'label': _('X'), 'value': 'X'},
            {'label': _('Y'), 'value': 'Y'},
            {'label': _('Angle'), 'value': 'A'}])

        self.array_lin_grid.addWidget(self.slot_array_axis_label, 0, 0)
        self.array_lin_grid.addWidget(self.array_axis_radio, 0, 1)

        # Linear Slot Array pitch distance
        self.slot_array_pitch_label = FCLabel('%s:' % _('Pitch'))
        self.slot_array_pitch_label.setToolTip(
            _("Pitch = Distance between elements of the array.")
        )

        self.array_pitch_entry = FCDoubleSpinner(policy=False)
        self.array_pitch_entry.set_precision(self.decimals)
        self.array_pitch_entry.setSingleStep(0.1)
        self.array_pitch_entry.setRange(0.0000, 10000.0000)

        self.array_lin_grid.addWidget(self.slot_array_pitch_label, 2, 0)
        self.array_lin_grid.addWidget(self.array_pitch_entry, 2, 1)

        # Linear Slot Array angle
        self.slot_array_linear_angle_label = FCLabel('%s:' % _('Angle'))
        self.slot_array_linear_angle_label.setToolTip(
            _("Angle at which the linear array is placed.\n"
              "The precision is of max 2 decimals.\n"
              "Min value is: -360.00 degrees.\n"
              "Max value is: 360.00 degrees.")
        )

        self.array_linear_angle_entry = FCDoubleSpinner(policy=False)
        self.array_linear_angle_entry.set_precision(self.decimals)
        self.array_linear_angle_entry.setSingleStep(1.0)
        self.array_linear_angle_entry.setRange(-360.00, 360.00)

        self.array_lin_grid.addWidget(self.slot_array_linear_angle_label, 4, 0)
        self.array_lin_grid.addWidget(self.array_linear_angle_entry, 4, 1)

        # #############################################################################################################
        # ##################################### Circular SLOT ARRAY  ##################################################
        # #############################################################################################################
        self.array_circular_frame = QtWidgets.QFrame()
        self.array_circular_frame.setContentsMargins(0, 0, 0, 0)
        self.array_grid.addWidget(self.array_circular_frame, 10, 0, 1, 2)

        self.array_circ_grid = GLay(v_spacing=5, h_spacing=3)
        self.array_circ_grid.setContentsMargins(0, 0, 0, 0)
        self.array_circular_frame.setLayout(self.array_circ_grid)

        # Slot Circular Array Direction
        self.slot_array_direction_label = FCLabel('%s:' % _('Direction'))
        self.slot_array_direction_label.setToolTip(_("Direction for circular array.\n"
                                                     "Can be CW = clockwise or CCW = counter clockwise."))

        self.array_direction_radio = RadioSet([
            {'label': _('CW'), 'value': 'CW'},
            {'label': _('CCW'), 'value': 'CCW'}])

        self.array_circ_grid.addWidget(self.slot_array_direction_label, 0, 0)
        self.array_circ_grid.addWidget(self.array_direction_radio, 0, 1)

        # Slot Circular Array Angle
        self.slot_array_angle_label = FCLabel('%s:' % _('Angle'))
        self.slot_array_angle_label.setToolTip(_("Angle at which each element in circular array is placed."))

        self.array_angle_entry = FCDoubleSpinner(policy=False)
        self.array_angle_entry.set_precision(self.decimals)
        self.array_angle_entry.setSingleStep(1)
        self.array_angle_entry.setRange(-360.00, 360.00)

        self.array_circ_grid.addWidget(self.slot_array_angle_label, 2, 0)
        self.array_circ_grid.addWidget(self.array_angle_entry, 2, 1)

        # Radius
        self.radius_lbl = FCLabel('%s:' % _('Radius'))
        self.radius_lbl.setToolTip(_("Array radius."))

        self.radius_entry = FCDoubleSpinner(policy=False)
        self.radius_entry.set_precision(self.decimals)
        self.radius_entry.setSingleStep(1.0)
        self.radius_entry.setRange(-10000.0000, 10000.000)

        self.array_circ_grid.addWidget(self.radius_lbl, 4, 0)
        self.array_circ_grid.addWidget(self.radius_entry, 4, 1)

        # #############################################################################################################
        # Buttons
        # #############################################################################################################
        self.add_btn = FCButton(_("Add"))
        self.add_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/plus16.png'))
        self.layout.addWidget(self.add_btn)

        GLay.set_common_column_size([
            dia_grid, pos_grid, slot_grid, self.array_grid, self.array_lin_grid, self.array_circ_grid], 0)

        self.layout.addStretch(1)

        # Signals
        self.slot_direction_radio.activated_custom.connect(self.on_slot_angle_radio)

        self.array_type_radio.activated_custom.connect(self.on_array_type_radio)
        self.array_axis_radio.activated_custom.connect(self.on_linear_angle_radio)

    def confirmation_message(self, accepted, minval, maxval):
        if accepted is False:
            self.app.inform[str, bool].emit('[WARNING_NOTCL] %s: [%.*f, %.*f]' % (_("Edited value is out of range"),
                                                                                  self.decimals,
                                                                                  minval,
                                                                                  self.decimals,
                                                                                  maxval), False)

    def confirmation_message_int(self, accepted, minval, maxval):
        if accepted is False:
            self.app.inform[str, bool].emit('[WARNING_NOTCL] %s: [%d, %d]' %
                                            (_("Edited value is out of range"), minval, maxval), False)

    def on_array_type_radio(self, val):
        if val == 'linear':
            self.array_circular_frame.hide()
            self.array_linear_frame.show()
            self.app.inform.emit(_("Click to place ..."))
        else:  # 'circular'
            self.array_circular_frame.show()
            self.array_linear_frame.hide()
            self.app.inform.emit(_("Click on the circular array Center position"))

        self.array_size_entry.setDisabled(False)

    def on_linear_angle_radio(self, val):
        if val == 'A':
            self.array_linear_angle_entry.show()
            self.slot_array_linear_angle_label.show()
        else:
            self.array_linear_angle_entry.hide()
            self.slot_array_linear_angle_label.hide()

    def on_slot_array_type_radio(self, val):
        if val == 'linear':
            self.array_circular_frame.hide()
            self.array_linear_frame.show()
            self.app.inform.emit(_("Click to place ..."))
        else:
            self.array_circular_frame.show()
            self.array_linear_frame.hide()
            self.app.inform.emit(_("Click on the circular array Center position"))

    def on_slot_array_linear_angle_radio(self):
        val = self.array_axis_radio.get_value()
        if val == 'A':
            self.array_linear_angle_entry.show()
            self.slot_array_linear_angle_label.show()
        else:
            self.array_linear_angle_entry.hide()
            self.slot_array_linear_angle_label.hide()

    def on_slot_angle_radio(self):
        val = self.slot_direction_radio.get_value()
        if val == 'A':
            self.slot_angle_entry.setEnabled(True)
            self.slot_angle_label.setEnabled(True)
        else:
            self.slot_angle_entry.setEnabled(False)
            self.slot_angle_label.setEnabled(False)
