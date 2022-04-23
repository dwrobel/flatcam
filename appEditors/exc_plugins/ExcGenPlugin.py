
from appTool import *

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ExcGenEditorTool(AppTool):
    """
    Simple input for buffer distance.
    """

    def __init__(self, app, draw_app, plugin_name):
        AppTool.__init__(self, app)

        self.draw_app = draw_app
        self.decimals = app.decimals
        self.plugin_name = plugin_name

        self.ui = ExcGenEditorUI(layout=self.layout, path_class=self, plugin_name=plugin_name)

        self.connect_signals_at_init()
        self.set_tool_ui()

    def connect_signals_at_init(self):
        # Signals
        self.ui.clear_btn.clicked.connect(self.on_clear)

    def disconnect_signals(self):
        # Signals
        try:
            self.ui.clear_btn.clicked.disconnect()
        except (TypeError, AttributeError):
            pass

    def run(self):
        self.app.defaults.report_usage("Geo Editor ToolPath()")
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
        self.length = 0.0

    def on_tab_close(self):
        self.disconnect_signals()
        self.hide_tool()
        # self.app.ui.notebook.callback_on_close = lambda: None

    def on_clear(self):
        self.set_tool_ui()

    @property
    def length(self):
        return self.ui.project_line_entry.get_value()

    @length.setter
    def length(self, val):
        self.ui.project_line_entry.set_value(val)

    def hide_tool(self):
        self.ui.path_tool_frame.hide()
        self.app.ui.notebook.setCurrentWidget(self.app.ui.properties_tab)
        if self.draw_app.active_tool.name != 'select':
            self.draw_app.select_tool("select")


class ExcGenEditorUI:

    def __init__(self, layout, path_class, plugin_name):
        self.pluginName = plugin_name
        self.path_class = path_class
        self.decimals = self.path_class.app.decimals
        self.layout = layout

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
        self.path_tool_frame = QtWidgets.QFrame()
        self.path_tool_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.path_tool_frame)
        self.path_tool_box = QtWidgets.QVBoxLayout()
        self.path_tool_box.setContentsMargins(0, 0, 0, 0)
        self.path_tool_frame.setLayout(self.path_tool_box)

        # Grid Layout
        grid_path = GLay(v_spacing=5, h_spacing=3)
        self.path_tool_box.addLayout(grid_path)

        # Project distance
        self.project_line_lbl = FCLabel('%s:' % _("Length"))
        self.project_line_lbl.setToolTip(
            _("Length of the current segment/move.")
        )
        self.project_line_entry = NumericalEvalEntry(border_color='#0069A9')
        grid_path.addWidget(self.project_line_lbl, 0, 0)
        grid_path.addWidget(self.project_line_entry, 0, 1)

        # self.buffer_corner_lbl = FCLabel('%s:' % _("Buffer corner"))
        # self.buffer_corner_lbl.setToolTip(
        #     _("There are 3 types of corners:\n"
        #       " - 'Round': the corner is rounded for exterior buffer.\n"
        #       " - 'Square': the corner is met in a sharp angle for exterior buffer.\n"
        #       " - 'Beveled': the corner is a line that directly connects the features meeting in the corner")
        # )
        # self.buffer_corner_cb = FCComboBox()
        # self.buffer_corner_cb.addItem(_("Round"))
        # self.buffer_corner_cb.addItem(_("Square"))
        # self.buffer_corner_cb.addItem(_("Beveled"))
        # grid_path.addWidget(self.buffer_corner_lbl, 2, 0)
        # grid_path.addWidget(self.buffer_corner_cb, 2, 1)

        self.clear_btn = FCButton(_("Clear"))
        grid_path.addWidget(self.clear_btn, 4, 0, 1, 2)

        self.layout.addStretch(1)
