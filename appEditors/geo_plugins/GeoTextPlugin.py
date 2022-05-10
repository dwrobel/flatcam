
from appTool import *
from appParsers.ParseFont import *

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class TextInputTool(AppTool):
    """
    Simple input for buffer distance.
    """

    def __init__(self, app, draw_app):
        AppTool.__init__(self, app)

        self.app = app
        self.draw_app = draw_app
        self.text_path = []
        self.decimals = self.app.decimals

        self.f_parse = ParseFont(self.app)
        self.f_parse.get_fonts_by_types()
        self.font_name = None
        self.font_bold = False
        self.font_italic = False

        self.ui = TextEditorUI(layout=self.layout, text_class=self)

        self.connect_signals_at_init()
        self.set_tool_ui()

    def run(self):
        self.app.defaults.report_usage("Geo Editor TextInputTool()")
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

        self.app.ui.notebook.setTabText(2, _("Text Tool"))

    def connect_signals_at_init(self):
        # Signals
        self.ui.apply_button.clicked.connect(self.on_apply_button)
        self.ui.font_type_cb.currentFontChanged.connect(self.font_family)
        self.ui.font_size_cb.activated.connect(self.font_size)
        self.ui.font_bold_tb.clicked.connect(self.on_bold_button)
        self.ui.font_italic_tb.clicked.connect(self.on_italic_button)

    def set_tool_ui(self):
        # Font type
        if sys.platform == "win32":
            f_current = QtGui.QFont("Arial")
        elif sys.platform == "linux":
            f_current = QtGui.QFont("FreeMono")
        else:
            f_current = QtGui.QFont("Helvetica Neue")

        self.font_name = f_current.family()
        self.ui.font_type_cb.setCurrentFont(f_current)

        # Flag variables to show if font is bold, italic, both or none (regular)
        self.font_bold = False
        self.font_italic = False

        self.ui.text_input_entry.setCurrentFont(f_current)
        self.ui.text_input_entry.setFontPointSize(10)

        # # Create dictionaries with the filenames of the fonts
        # # Key: Fontname
        # # Value: Font File Name.ttf
        #
        # # regular fonts
        # self.ff_names_regular ={}
        # # bold fonts
        # self.ff_names_bold = {}
        # # italic fonts
        # self.ff_names_italic = {}
        # # bold and italic fonts
        # self.ff_names_bi = {}
        #
        # if sys.platform == 'win32':
        #     from winreg import ConnectRegistry, OpenKey, EnumValue, HKEY_LOCAL_MACHINE
        #     registry = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
        #     font_key = OpenKey(registry, "SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts")
        #     try:
        #         i = 0
        #         while 1:
        #             name_font, value, type = EnumValue(font_key, i)
        #             k = name_font.replace(" (TrueType)", '')
        #             if 'Bold' in k and 'Italic' in k:
        #                 k = k.replace(" Bold Italic", '')
        #                 self.ff_names_bi.update({k: value})
        #             elif 'Bold' in k:
        #                 k = k.replace(" Bold", '')
        #                 self.ff_names_bold.update({k: value})
        #             elif 'Italic' in k:
        #                 k = k.replace(" Italic", '')
        #                 self.ff_names_italic.update({k: value})
        #             else:
        #                 self.ff_names_regular.update({k: value})
        #             i += 1
        #     except WindowsError:
        #         pass

    def on_tab_close(self):
        self.draw_app.select_tool("select")
        self.app.ui.notebook.callback_on_close = lambda: None

    def on_apply_button(self):
        font_to_geo_type = ""

        if self.font_bold is True:
            font_to_geo_type = 'bold'
        elif self.font_italic is True:
            font_to_geo_type = 'italic'
        elif self.font_bold is True and self.font_italic is True:
            font_to_geo_type = 'bi'
        elif self.font_bold is False and self.font_italic is False:
            font_to_geo_type = 'regular'

        string_to_geo = self.ui.text_input_entry.get_value()
        font_to_geo_size = self.ui.font_size_cb.get_value()

        self.text_path = self.f_parse.font_to_geometry(char_string=string_to_geo, font_name=self.font_name,
                                                       font_size=font_to_geo_size,
                                                       font_type=font_to_geo_type,
                                                       units=self.app.app_units.upper())

    def font_family(self, font):
        self.ui.text_input_entry.selectAll()
        font.setPointSize(int(self.ui.font_size_cb.get_value()))
        self.ui.text_input_entry.setCurrentFont(font)
        self.font_name = self.ui.font_type_cb.currentFont().family()

    def font_size(self):
        self.ui.text_input_entry.selectAll()
        self.ui.text_input_entry.setFontPointSize(float(self.ui.font_size_cb.get_value()))

    def on_bold_button(self):
        if self.ui.font_bold_tb.isChecked():
            self.ui.text_input_entry.selectAll()
            self.ui.text_input_entry.setFontWeight(QtGui.QFont.Weight.Bold)
            self.font_bold = True
        else:
            self.ui.text_input_entry.selectAll()
            self.ui.text_input_entry.setFontWeight(QtGui.QFont.Weight.Normal)
            self.font_bold = False

    def on_italic_button(self):
        if self.ui.font_italic_tb.isChecked():
            self.ui.text_input_entry.selectAll()
            self.ui.text_input_entry.setFontItalic(True)
            self.font_italic = True
        else:
            self.ui.text_input_entry.selectAll()
            self.ui.text_input_entry.setFontItalic(False)
            self.font_italic = False

    def hide_tool(self):
        self.ui.text_tool_frame.hide()
        self.app.ui.notebook.setCurrentWidget(self.app.ui.properties_tab)
        # self.app.ui.splitter.setSizes([0, 1])
        # self.app.ui.notebook.setTabText(2, _("Tool"))
        self.app.ui.notebook.removeTab(2)


class TextEditorUI:
    pluginName = _("Text")

    def __init__(self, layout, text_class):
        self.text_class = text_class
        self.decimals = self.text_class.app.decimals
        self.layout = layout
        self.app = self.text_class.app

        # this way I can hide/show the frame
        self.text_tool_frame = QtWidgets.QFrame()
        self.text_tool_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.text_tool_frame)
        self.text_tools_box = QtWidgets.QVBoxLayout()
        self.text_tools_box.setContentsMargins(0, 0, 0, 0)
        self.text_tool_frame.setLayout(self.text_tools_box)

        # Title
        title_label = FCLabel("%s" % self.pluginName, size=16, bold=True)
        self.text_tools_box.addWidget(title_label)

        # Grid Layout
        self.grid_text = GLay(v_spacing=5, h_spacing=3)
        self.text_tools_box.addLayout(self.grid_text)

        self.font_type_cb = QtWidgets.QFontComboBox()
        self.grid_text.addWidget(FCLabel('%s:' % _("Font")), 0, 0)
        self.grid_text.addWidget(self.font_type_cb, 0, 1)

        # Font size
        hlay = QtWidgets.QHBoxLayout()

        self.font_size_cb = FCComboBox(policy=False)
        self.font_size_cb.setEditable(True)
        self.font_size_cb.setMinimumContentsLength(3)
        self.font_size_cb.setMaximumWidth(70)

        font_sizes = ['6', '7', '8', '9', '10', '11', '12', '13', '14',
                      '15', '16', '18', '20', '22', '24', '26', '28',
                      '32', '36', '40', '44', '48', '54', '60', '66',
                      '72', '80', '88', '96']

        self.font_size_cb.addItems(font_sizes)
        self.font_size_cb.setCurrentIndex(4)

        hlay.addWidget(self.font_size_cb)
        hlay.addStretch()

        self.font_bold_tb = QtWidgets.QToolButton()
        self.font_bold_tb.setCheckable(True)
        self.font_bold_tb.setIcon(QtGui.QIcon(self.app.resource_location + '/bold32.png'))
        hlay.addWidget(self.font_bold_tb)

        self.font_italic_tb = QtWidgets.QToolButton()
        self.font_italic_tb.setCheckable(True)
        self.font_italic_tb.setIcon(QtGui.QIcon(self.app.resource_location + '/italic32.png'))
        hlay.addWidget(self.font_italic_tb)

        self.grid_text.addWidget(FCLabel('%s:' % _("Size")), 2, 0)
        self.grid_text.addLayout(hlay, 2, 1)

        # Text input
        self.grid_text.addWidget(FCLabel('%s:' % _("Text")), 4, 0, 1, 2)

        self.text_input_entry = FCTextAreaRich()
        self.text_input_entry.setTabStopDistance(12)
        self.text_input_entry.setMinimumHeight(200)
        # self.text_input_entry.setMaximumHeight(150)

        self.grid_text.addWidget(self.text_input_entry, 6, 0, 1, 2)

        # Buttons
        self.apply_button = FCButton(_("Apply"))
        self.grid_text.addWidget(self.apply_button, 8, 0, 1, 2)

        # self.layout.addStretch()
