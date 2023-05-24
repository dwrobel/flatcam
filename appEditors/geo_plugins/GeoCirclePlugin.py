
from PyQt6 import QtWidgets, QtGui
from appTool import AppToolEditor
from appGUI.GUIElements import VerticalScrollArea, FCLabel, FCButton, FCFrame, GLay, FCDoubleSpinner

from shapely import Point
from shapely.affinity import scale, rotate

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class CircleEditorTool(AppToolEditor):
    """
    Simple input for buffer distance.
    """

    def __init__(self, app, draw_app, plugin_name):
        AppToolEditor.__init__(self, app)

        self.draw_app = draw_app
        self.decimals = app.decimals
        self._mode = 'add'

        self.ui = CircleEditorUI(layout=self.layout, circle_class=self)
        self.ui.pluginName = plugin_name

        self.connect_signals_at_init()
        self.set_tool_ui()

    def connect_signals_at_init(self):
        # Signals
        self.ui.add_button.clicked.connect(self.on_execute)

    def run(self):
        self.app.defaults.report_usage("Geo Editor CircleTool()")
        super().run()

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
                self.app.ui.notebook.addTab(self.app.ui.plugin_tab, self.ui.pluginName)
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

        self.app.ui.notebook.setTabText(2, self.ui.pluginName)

    def set_tool_ui(self):
        # Init appGUI
        self.ui.x_entry.set_value(0)
        self.ui.y_entry.set_value(0)
        self.ui.radius_x_entry.set_value(0)
        self.ui.radius_y_entry.set_value(0)
        self.ui.angle_entry.set_value(0)
        self.ui.radius_link_btn.setChecked(True)
        self.ui.on_link_checked(True)

    def on_tab_close(self):
        self.draw_app.select_tool("select")
        self.app.ui.notebook.callback_on_close = lambda: None

    def on_execute(self):
        if self.mode == 'add':
            self.app.log.info("CircleEditorTool.on_add() -> adding a Circle shape")
            self.on_add()
        else:
            self.app.log.info("RectangleEditorTool.on_add() -> modifying a Circle shape")
            self.draw_app.delete_selected()
            self.on_add()
            self.draw_app.app.inform.emit(_("Click on Center point ..."))

    def on_add(self):
        origin_x = self.ui.x_entry.get_value()
        origin_y = self.ui.y_entry.get_value()
        radius_x = self.ui.radius_x_entry.get_value()
        radius_y = self.ui.radius_y_entry.get_value()
        angle = self.ui.angle_entry.get_value()
        is_circle = True if self.ui.radius_link_btn.isChecked() else False

        if radius_x == 0.0 or radius_y == 0.0:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Failed."))
            return

        if is_circle:
            geo = Point((origin_x, origin_y)).buffer(radius_x)
        else:   # 'ellipse'
            circle_geo = Point((origin_x, origin_y)).buffer(1)
            geo = scale(circle_geo, radius_x, radius_y)
            if angle != 0:
                geo = rotate(geo, -angle)

        added_shapes = self.draw_app.add_shape(geo.exterior)
        for added_shape in added_shapes:
            added_shape.data['type'] = _("Circle")
        self.draw_app.plot_all()

    def on_clear(self):
        self.set_tool_ui()

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, val):
        self._mode = val
        if self._mode == 'add':
            # remove selections when adding a new rectangle
            self.draw_app.selected = []
            self.ui.add_button.set_value(_("Add"))
            self.ui.add_button.setIcon(QtGui.QIcon(self.app.resource_location + '/plus16.png'))
        else:
            self.ui.add_button.set_value(_("Apply"))
            self.ui.add_button.setIcon(QtGui.QIcon(self.app.resource_location + '/apply32.png'))

    @property
    def radius_x(self):
        return self.ui.radius_x_entry.get_value()

    @radius_x.setter
    def radius_x(self, val):
        self.ui.radius_x_entry.set_value(val)

    @property
    def radius_y(self):
        return self.ui.radius_y_entry.get_value()

    @radius_y.setter
    def radius_y(self, val):
        self.ui.radius_y_entry.set_value(val)

    def hide_tool(self):
        self.ui.circle_frame.hide()
        self.app.ui.notebook.setCurrentWidget(self.app.ui.properties_tab)
        if self.draw_app.active_tool.name != 'select':
            self.draw_app.select_tool("select")


class CircleEditorUI:
    pluginName = _("Circle")

    def __init__(self, layout, circle_class):
        self.circle_class = circle_class
        self.decimals = self.circle_class.app.decimals
        self.app = self.circle_class.app
        self.layout = layout

        # Title
        title_label = FCLabel("%s" % ('Editor ' + self.pluginName), size=16, bold=True)
        self.layout.addWidget(title_label)

        # this way I can hide/show the frame
        self.circle_frame = QtWidgets.QFrame()
        self.circle_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.circle_frame)
        self.circle_tool_box = QtWidgets.QVBoxLayout()
        self.circle_tool_box.setContentsMargins(0, 0, 0, 0)
        self.circle_frame.setLayout(self.circle_tool_box)

        # Grid Layout
        grid0 = GLay(v_spacing=5, h_spacing=3)
        self.circle_tool_box.addLayout(grid0)

        # Position
        self.pos_lbl = FCLabel('%s' % _("Position"), color='red', bold=True)
        grid0.addWidget(self.pos_lbl, 0, 0, 1, 3)

        # #############################################################################################################
        # Position Frame
        # #############################################################################################################
        pos_frame = FCFrame()
        grid0.addWidget(pos_frame, 2, 0, 1, 2)

        pos_grid = GLay(v_spacing=5, h_spacing=3)
        pos_frame.setLayout(pos_grid)

        # X Pos
        self.x_lbl = FCLabel('%s:' % _("X"))
        self.x_entry = FCDoubleSpinner()
        self.x_entry.set_precision(self.decimals)
        self.x_entry.set_range(-10000.0000, 10000.0000)
        pos_grid.addWidget(self.x_lbl, 0, 0)
        pos_grid.addWidget(self.x_entry, 0, 1, 1, 2)

        # Y Pos
        self.y_lbl = FCLabel('%s:' % _("Y"))
        self.y_entry = FCDoubleSpinner()
        self.y_entry.set_precision(self.decimals)
        self.y_entry.set_range(-10000.0000, 10000.0000)
        pos_grid.addWidget(self.y_lbl, 2, 0)
        pos_grid.addWidget(self.y_entry, 2, 1, 1, 2)

        # Radius
        self.radius_lbl = FCLabel('%s' % _("Radius"), bold=True, color='blue')
        grid0.addWidget(self.radius_lbl, 4, 0)

        # #############################################################################################################
        # Radius Frame
        # #############################################################################################################
        rad_frame = FCFrame()
        grid0.addWidget(rad_frame, 6, 0, 1, 2)

        rad_grid = GLay(v_spacing=5, h_spacing=3)
        rad_frame.setLayout(rad_grid)

        # Radius X
        self.radius_x_lbl = FCLabel('%s:' % "X")
        self.radius_x_entry = FCDoubleSpinner()
        self.radius_x_entry.set_precision(self.decimals)
        self.radius_x_entry.set_range(0.0000, 10000.0000)
        rad_grid.addWidget(self.radius_x_lbl, 0, 0)
        rad_grid.addWidget(self.radius_x_entry, 0, 1)

        # Radius Y
        self.radius_y_lbl = FCLabel('%s:' % "Y")
        self.radius_y_entry = FCDoubleSpinner()
        self.radius_y_entry.set_precision(self.decimals)
        self.radius_y_entry.set_range(0.0000, 10000.0000)
        rad_grid.addWidget(self.radius_y_lbl, 1, 0)
        rad_grid.addWidget(self.radius_y_entry, 1, 1)

        # Angle
        self.angle_lbl = FCLabel('%s:' % _("Angle"))
        self.angle_entry = FCDoubleSpinner()
        self.angle_entry.set_precision(self.decimals)
        self.angle_entry.set_range(-360.0000, 360.0000)
        rad_grid.addWidget(self.angle_lbl, 2, 0)
        rad_grid.addWidget(self.angle_entry, 2, 1)

        # Radius link
        self.radius_link_btn = QtWidgets.QToolButton()
        self.radius_link_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/link32.png'))
        self.radius_link_btn.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                           QtWidgets.QSizePolicy.Policy.Expanding)
        self.radius_link_btn.setCheckable(True)
        rad_grid.addWidget(self.radius_link_btn, 0, 2, 3, 1)

        # Buttons
        self.add_button = FCButton(_("Add"))
        self.add_button.setIcon(QtGui.QIcon(self.app.resource_location + '/plus16.png'))
        grid0.addWidget(self.add_button, 18, 0, 1, 3)

        GLay.set_common_column_size([grid0, pos_grid, rad_grid], 0)

        self.layout.addStretch(1)

        # Note
        self.note_lbl = FCLabel('%s' % _("Note"), bold=True)
        self.layout.addWidget(self.note_lbl)
        self.note_description_lbl = FCLabel('%s' % _("Shift + click to select a shape for modification."))
        self.layout.addWidget(self.note_description_lbl)

        # Signals
        self.radius_link_btn.clicked.connect(self.on_link_checked)

    def on_link_checked(self, checked):
        if checked:
            self.radius_x_lbl.set_value('%s:' % _("Value"))
            self.radius_y_lbl.setDisabled(True)
            self.radius_y_entry.setDisabled(True)
            self.radius_y_entry.set_value(self.radius_x_entry.get_value())
            self.angle_lbl.setDisabled(True)
            self.angle_entry.setDisabled(True)
        else:
            self.radius_x_lbl.set_value('%s:' % "X")
            self.radius_y_lbl.setDisabled(False)
            self.radius_y_entry.setDisabled(False)
            self.angle_lbl.setDisabled(False)
            self.angle_entry.setDisabled(False)
