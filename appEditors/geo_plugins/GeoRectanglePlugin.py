
from PyQt6 import QtWidgets, QtGui
from appTool import AppToolEditor
from appGUI.GUIElements import VerticalScrollArea, FCLabel, FCButton, GLay, FCFrame, FCDoubleSpinner, RadioSetCross, \
    RadioSet, NumericalEvalEntry

from shapely.geometry import box, base

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class RectangleEditorTool(AppToolEditor):
    """
    Simple input for buffer distance.
    """

    def __init__(self, app, draw_app, plugin_name):
        AppToolEditor.__init__(self, app)

        self.draw_app = draw_app
        self.decimals = app.decimals
        self._mode = 'add'

        self.ui = RectangleEditorUI(layout=self.layout, rect_class=self)
        self.ui.pluginName = plugin_name

        self.connect_signals_at_init()
        self.set_tool_ui()

    def connect_signals_at_init(self):
        # Signals
        self.ui.add_button.clicked.connect(self.on_execute)

    def run(self):
        self.app.defaults.report_usage("Geo Editor RectangleTool()")
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
        self.ui.anchor_radio.set_value('c')
        self.ui.x_entry.set_value(self.draw_app.snap_x)
        self.ui.y_entry.set_value(self.draw_app.snap_y)
        self.ui.corner_radio.set_value('r')
        self.ui.radius_entry.set_value(1)
        self.ui.length_entry.set_value(0.0)
        self.ui.width_entry.set_value(0.0)

        self.ui.on_corner_changed(val=self.ui.corner_radio.get_value())

    def on_tab_close(self):
        self.draw_app.select_tool("select")
        self.app.ui.notebook.callback_on_close = lambda: None

    def on_execute(self):
        if self.mode == 'add':
            self.app.log.info("RectangleEditorTool.on_add() -> adding a Rectangle shape")
            self.on_add()
        else:
            self.app.log.info("RectangleEditorTool.on_add() -> modifying a Rectangle shape")
            self.draw_app.delete_selected()
            self.on_add()
            self.draw_app.app.inform.emit(_("Click on 1st corner ..."))

    def on_add(self):
        origin = self.ui.anchor_radio.get_value()
        origin_x = self.ui.x_entry.get_value()
        origin_y = self.ui.y_entry.get_value()
        corner_type = self.ui.corner_radio.get_value()
        corner_radius = self.ui.radius_entry.get_value()
        length = self.ui.length_entry.get_value()
        width = self.ui.width_entry.get_value()

        if length == 0.0 or width == 0.0:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Failed."))
            return

        if origin == 'tl':
            cx = origin_x + (length / 2)
            cy = origin_y - (width / 2)
        elif origin == 'tr':
            cx = origin_x - (length / 2)
            cy = origin_y - (width / 2)
        elif origin == 'bl':
            cx = origin_x + (length / 2)
            cy = origin_y + (width / 2)
        elif origin == 'br':
            cx = origin_x - (length / 2)
            cy = origin_y + (width / 2)
        else:   # 'c' - center
            cx = origin_x
            cy = origin_y

        if corner_radius == 0.0:
            corner_type = 's'
        if corner_type in ['r', 'b']:
            length -= 2 * corner_radius
            width -= 2 * corner_radius

        minx = cx - (length / 2)
        miny = cy - (width / 2)
        maxx = cx + (length / 2)
        maxy = cy + (width / 2)

        if corner_type == 'r':
            geo = box(minx, miny, maxx, maxy).buffer(
                corner_radius, join_style=base.JOIN_STYLE.round,
                resolution=self.draw_app.app.options["geometry_circle_steps"]).exterior
        elif corner_type == 'b':
            geo = box(minx, miny, maxx, maxy).buffer(
                corner_radius, join_style=base.JOIN_STYLE.bevel,
                resolution=self.draw_app.app.options["geometry_circle_steps"]).exterior
        else:   # 's' - square
            geo = box(minx, miny, maxx, maxy).exterior

        added_shapes = self.draw_app.add_shape(geo)
        for added_shape in added_shapes:
            added_shape.data['type'] = _("Rectangle")
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
    def length(self):
        return self.ui.length_entry.get_value()

    @length.setter
    def length(self, val):
        self.ui.length_entry.set_value(val)

    @property
    def width(self):
        return self.ui.width_entry.get_value()

    @width.setter
    def width(self, val):
        self.ui.width_entry.set_value(val)

    def hide_tool(self):
        self.ui.rect_frame.hide()
        self.app.ui.notebook.setCurrentWidget(self.app.ui.properties_tab)
        if self.draw_app.active_tool.name != 'select':
            self.draw_app.select_tool("select")


class RectangleEditorUI:
    pluginName = _("Rectangle")

    def __init__(self, layout, rect_class):
        self.rect_class = rect_class
        self.decimals = self.rect_class.app.decimals
        self.app = self.rect_class.app
        self.layout = layout

        # Title
        title_label = FCLabel("%s" % ('Editor ' + self.pluginName), size=16, bold=True)
        self.layout.addWidget(title_label)

        # this way I can hide/show the frame
        self.rect_frame = QtWidgets.QFrame()
        self.rect_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.rect_frame)
        self.rect_tool_box = QtWidgets.QVBoxLayout()
        self.rect_tool_box.setContentsMargins(0, 0, 0, 0)
        self.rect_frame.setLayout(self.rect_tool_box)

        # Grid Layout
        grid0 = GLay(v_spacing=5, h_spacing=3)
        self.rect_tool_box.addLayout(grid0)

        # Position
        self.pos_lbl = FCLabel('%s' % _("Position"), bold=True, color='red')
        grid0.addWidget(self.pos_lbl, 0, 0, 1, 2)
        # #############################################################################################################
        # Position Frame
        # #############################################################################################################
        pos_frame = FCFrame()
        grid0.addWidget(pos_frame, 2, 0, 1, 2)

        pos_grid = GLay(v_spacing=5, h_spacing=3)
        pos_frame.setLayout(pos_grid)

        # Anchor
        self.anchor_lbl = FCLabel('%s:' % _("Anchor"), bold=False)
        choices = [
            {"label": _("T Left"), "value": "tl"},
            {"label": _("T Right"), "value": "tr"},
            {"label": _("B Left"), "value": "bl"},
            {"label": _("B Right"), "value": "br"},
            {"label": _("Center"), "value": "c"}
        ]
        self.anchor_radio = RadioSetCross(choices, compact=True)
        pos_grid.addWidget(self.anchor_lbl, 0, 0)
        pos_grid.addWidget(self.anchor_radio, 0, 1)

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

        self.corner_lbl = FCLabel('%s' % _("Corner"), bold=True, color='green')
        grid0.addWidget(self.corner_lbl, 4, 0, 1, 2)
        # #############################################################################################################
        # Corner Frame
        # #############################################################################################################
        cor_frame = FCFrame()
        grid0.addWidget(cor_frame, 6, 0, 1, 2)

        cor_grid = GLay(v_spacing=5, h_spacing=3)
        cor_frame.setLayout(cor_grid)

        # Corner Type
        self.corner_lbl = FCLabel('%s:' % _("Type"))
        self.corner_lbl.setToolTip(
            _("There are 3 types of corners:\n"
              " - 'Round': the corners are rounded\n"
              " - 'Square': the corners meet in a sharp angle\n"
              " - 'Beveled': the corners are a line that directly connects the features meeting in the corner")
        )
        self.corner_radio = RadioSet([
            {'label': _('Round'), 'value': 'r'},
            {'label': _('Square'), 'value': 's'},
            {'label': _('Beveled'), 'value': 'b'},
        ], orientation='vertical', compact=True)
        cor_grid.addWidget(self.corner_lbl, 0, 0)
        cor_grid.addWidget(self.corner_radio, 0, 1)

        # Radius
        self.radius_lbl = FCLabel('%s:' % _("Radius"))
        self.radius_entry = FCDoubleSpinner()
        self.radius_entry.set_precision(self.decimals)
        self.radius_entry.set_range(0.0000, 10000.0000)
        cor_grid.addWidget(self.radius_lbl, 2, 0)
        cor_grid.addWidget(self.radius_entry, 2, 1)

        # Size
        self.size_lbl = FCLabel('%s' % _("Size"), bold=True, color='indigo')
        grid0.addWidget(self.size_lbl, 8, 0, 1, 2)
        # #############################################################################################################
        # Size Frame
        # #############################################################################################################
        size_frame = FCFrame()
        grid0.addWidget(size_frame, 10, 0, 1, 2)

        size_grid = GLay(v_spacing=5, h_spacing=3)
        size_frame.setLayout(size_grid)

        # Length
        self.length_lbl = FCLabel('%s:' % _("Length"))
        self.length_entry = NumericalEvalEntry()
        size_grid.addWidget(self.length_lbl, 0, 0)
        size_grid.addWidget(self.length_entry, 0, 1)

        # Width
        self.width_lbl = FCLabel('%s:' % _("Width"))
        self.width_entry = NumericalEvalEntry()
        size_grid.addWidget(self.width_lbl, 2, 0)
        size_grid.addWidget(self.width_entry, 2, 1)

        # Buttons
        self.add_button = FCButton(_("Add"))
        self.add_button.setIcon(QtGui.QIcon(self.app.resource_location + '/plus16.png'))
        grid0.addWidget(self.add_button, 18, 0, 1, 2)

        GLay.set_common_column_size([grid0, pos_grid, cor_grid, size_grid], 0)
        self.layout.addStretch(1)

        # Note
        self.note_lbl = FCLabel('%s' % _("Note"), bold=True)
        self.layout.addWidget(self.note_lbl)
        self.note_description_lbl = FCLabel('%s' % _("Shift + click to select a shape for modification."))
        self.layout.addWidget(self.note_description_lbl)

        # Signals
        self.corner_radio.activated_custom.connect(self.on_corner_changed)

    def on_corner_changed(self, val):
        if val in ['r', 'b']:
            self.radius_lbl.show()
            self.radius_entry.show()
        else:
            self.radius_lbl.hide()
            self.radius_entry.hide()
