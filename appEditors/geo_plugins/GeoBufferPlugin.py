
from appTool import *

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class BufferSelectionTool(AppTool):
    """
    Simple input for buffer distance.
    """

    def __init__(self, app, draw_app):
        AppTool.__init__(self, app)

        self.draw_app = draw_app
        self.decimals = app.decimals

        self.ui = BufferEditorUI(layout=self.layout, buffer_class=self)

        self.connect_signals_at_init()
        self.set_tool_ui()

    def connect_signals_at_init(self):
        # Signals
        self.ui.buffer_button.clicked.connect(self.on_buffer)
        self.ui.buffer_int_button.clicked.connect(self.on_buffer_int)
        self.ui.buffer_ext_button.clicked.connect(self.on_buffer_ext)

    def run(self):
        self.app.defaults.report_usage("Geo Editor ToolBuffer()")
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

        self.app.ui.notebook.setTabText(2, _("Buffer"))

    def set_tool_ui(self):
        # Init appGUI
        self.ui.buffer_distance_entry.set_value(0.01)

    def on_tab_close(self):
        self.draw_app.select_tool("select")
        self.app.ui.notebook.callback_on_close = lambda: None

    def on_buffer(self):
        try:
            buffer_distance = float(self.ui.buffer_distance_entry.get_value())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                buffer_distance = float(self.ui.buffer_distance_entry.get_value().replace(',', '.'))
                self.ui.buffer_distance_entry.set_value(buffer_distance)
            except ValueError:
                self.app.inform.emit('[WARNING_NOTCL] %s' %
                                     _("Buffer distance value is missing or wrong format. Add it and retry."))
                return
        # the cb index start from 0 but the join styles for the buffer start from 1 therefore the adjustment
        # I populated the combobox such that the index coincide with the join styles value (which is really an INT)
        join_style = self.ui.buffer_corner_cb.currentIndex() + 1
        self.buffer(buffer_distance, join_style)

    def on_buffer_int(self):
        try:
            buffer_distance = float(self.ui.buffer_distance_entry.get_value())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                buffer_distance = float(self.ui.buffer_distance_entry.get_value().replace(',', '.'))
                self.ui.buffer_distance_entry.set_value(buffer_distance)
            except ValueError:
                self.app.inform.emit('[WARNING_NOTCL] %s' %
                                     _("Buffer distance value is missing or wrong format. Add it and retry."))
                return
        # the cb index start from 0 but the join styles for the buffer start from 1 therefore the adjustment
        # I populated the combobox such that the index coincide with the join styles value (which is really an INT)
        join_style = self.ui.buffer_corner_cb.currentIndex() + 1
        self.buffer_int(buffer_distance, join_style)

    def on_buffer_ext(self):
        try:
            buffer_distance = float(self.ui.buffer_distance_entry.get_value())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                buffer_distance = float(self.ui.buffer_distance_entry.get_value().replace(',', '.'))
                self.ui.buffer_distance_entry.set_value(buffer_distance)
            except ValueError:
                self.app.inform.emit('[WARNING_NOTCL] %s' %
                                     _("Buffer distance value is missing or wrong format. Add it and retry."))
                return
        # the cb index start from 0 but the join styles for the buffer start from 1 therefore the adjustment
        # I populated the combobox such that the index coincide with the join styles value (which is really an INT)
        join_style = self.ui.buffer_corner_cb.currentIndex() + 1
        self.buffer_ext(buffer_distance, join_style)

    def buffer(self, buf_distance, join_style):
        def work_task(geo_editor):
            with geo_editor.app.proc_container.new(_("Working...")):
                selected = geo_editor.get_selected()

                if buf_distance < 0:
                    msg = '[ERROR_NOTCL] %s' % _("Negative buffer value is not accepted. "
                                                 "Use Buffer interior to generate an 'inside' shape")
                    geo_editor.app.inform.emit(msg)

                    # deselect everything
                    geo_editor.selected = []
                    geo_editor.plot_all()
                    return 'fail'

                if len(selected) == 0:
                    geo_editor.app.inform.emit('[WARNING_NOTCL] %s' % _("Nothing selected."))
                    return 'fail'

                if not isinstance(buf_distance, float):
                    geo_editor.app.inform.emit('[WARNING_NOTCL] %s' % _("Invalid distance."))

                    # deselect everything
                    geo_editor.selected = []
                    geo_editor.plot_all()
                    return 'fail'

                results = []
                for t in selected:
                    if not t.geo.is_empty and t.geo.is_valid:
                        if t.geo.geom_type == 'Polygon':
                            results.append(t.geo.exterior.buffer(
                                buf_distance - 1e-10,
                                resolution=int(int(geo_editor.app.options["geometry_circle_steps"]) / 4),
                                join_style=join_style)
                            )
                        elif t.geo.geom_type == 'MultiLineString':
                            for line in t.geo:
                                if line.is_ring:
                                    b_geo = Polygon(line)
                                results.append(b_geo.buffer(
                                    buf_distance - 1e-10,
                                    resolution=int(int(geo_editor.app.options["geometry_circle_steps"]) / 4),
                                    join_style=join_style).exterior
                                               )
                                results.append(b_geo.buffer(
                                    -buf_distance + 1e-10,
                                    resolution=int(int(geo_editor.app.options["geometry_circle_steps"]) / 4),
                                    join_style=join_style).exterior
                                               )
                        elif t.geo.geom_type in ['LineString', 'LinearRing']:
                            if t.geo.is_ring:
                                b_geo = Polygon(t.geo)
                            results.append(b_geo.buffer(
                                buf_distance - 1e-10,
                                resolution=int(int(geo_editor.app.options["geometry_circle_steps"]) / 4),
                                join_style=join_style).exterior
                                           )
                            results.append(b_geo.buffer(
                                -buf_distance + 1e-10,
                                resolution=int(int(geo_editor.app.options["geometry_circle_steps"]) / 4),
                                join_style=join_style).exterior
                                           )

                if not results:
                    geo_editor.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed, the result is empty."))
                    # deselect everything
                    geo_editor.selected = []
                    geo_editor.plot_all()
                    return 'fail'

                for sha in results:
                    geo_editor.add_shape(sha)

                geo_editor.plot_all()
                geo_editor.build_ui_sig.emit()
                geo_editor.app.inform.emit('[success] %s' % _("Done."))

        self.app.worker_task.emit({'fcn': work_task, 'params': [self]})

    def buffer_int(self, buf_distance, join_style):
        def work_task(geo_editor):
            with geo_editor.app.proc_container.new(_("Working...")):
                selected = geo_editor.get_selected()

                if buf_distance < 0:
                    geo_editor.app.inform.emit('[ERROR_NOTCL] %s' % _("Negative buffer value is not accepted."))
                    # deselect everything
                    geo_editor.selected = []
                    geo_editor.plot_all()
                    return 'fail'

                if len(selected) == 0:
                    geo_editor.app.inform.emit('[WARNING_NOTCL] %s' % _("Nothing selected."))
                    return 'fail'

                if not isinstance(buf_distance, float):
                    geo_editor.app.inform.emit('[WARNING_NOTCL] %s' % _("Invalid distance."))
                    # deselect everything
                    geo_editor.selected = []
                    geo_editor.plot_all()
                    return 'fail'

                results = []
                for t in selected:
                    if not t.geo.is_empty and t.geo.is_valid:
                        if t.geo.geom_type == 'Polygon':
                            results.append(t.geo.exterior.buffer(
                                -buf_distance + 1e-10,
                                resolution=int(int(geo_editor.app.options["geometry_circle_steps"]) / 4),
                                join_style=join_style).exterior
                                           )
                        elif t.geo.geom_type == 'MultiLineString':
                            for line in t.geo:
                                if line.is_ring:
                                    b_geo = Polygon(line)
                                results.append(b_geo.buffer(
                                    -buf_distance + 1e-10,
                                    resolution=int(int(geo_editor.app.options["geometry_circle_steps"]) / 4),
                                    join_style=join_style).exterior
                                               )
                        elif t.geo.geom_type in ['LineString', 'LinearRing']:
                            if t.geo.is_ring:
                                b_geo = Polygon(t.geo)
                            results.append(b_geo.buffer(
                                -buf_distance + 1e-10,
                                resolution=int(int(geo_editor.app.options["geometry_circle_steps"]) / 4),
                                join_style=join_style).exterior
                                           )

                if not results:
                    geo_editor.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed, the result is empty."))
                    # deselect everything
                    geo_editor.selected = []
                    geo_editor.plot_all()
                    return 'fail'

                for sha in results:
                    geo_editor.add_shape(sha)

                geo_editor.plot_all()
                geo_editor.build_ui_sig.emit()
                geo_editor.app.inform.emit('[success] %s' % _("Done."))

        self.app.worker_task.emit({'fcn': work_task, 'params': [self]})

    def buffer_ext(self, buf_distance, join_style):
        def work_task(geo_editor):
            with geo_editor.app.proc_container.new(_("Working...")):
                selected = geo_editor.get_selected()

                if buf_distance < 0:
                    msg = '[ERROR_NOTCL] %s' % _("Negative buffer value is not accepted. "
                                                 "Use Buffer interior to generate an 'inside' shape")
                    geo_editor.app.inform.emit(msg)
                    # deselect everything
                    geo_editor.selected = []
                    geo_editor.plot_all()
                    return

                if len(selected) == 0:
                    geo_editor.app.inform.emit('[WARNING_NOTCL] %s' % _("Nothing selected."))
                    return

                if not isinstance(buf_distance, float):
                    geo_editor.app.inform.emit('[WARNING_NOTCL] %s' % _("Invalid distance."))
                    # deselect everything
                    geo_editor.selected = []
                    geo_editor.plot_all()
                    return

                results = []
                for t in selected:
                    if not t.geo.is_empty and t.geo.is_valid:
                        if t.geo.geom_type == 'Polygon':
                            results.append(t.geo.exterior.buffer(
                                buf_distance - 1e-10,
                                resolution=int(int(geo_editor.app.options["geometry_circle_steps"]) / 4),
                                join_style=join_style).exterior
                                           )
                        elif t.geo.geom_type == 'MultiLineString':
                            for line in t.geo:
                                if line.is_ring:
                                    b_geo = Polygon(line)
                                results.append(b_geo.buffer(
                                    buf_distance - 1e-10,
                                    resolution=int(int(geo_editor.app.options["geometry_circle_steps"]) / 4),
                                    join_style=join_style).exterior
                                               )
                        elif t.geo.geom_type in ['LineString', 'LinearRing']:
                            if t.geo.is_ring:
                                b_geo = Polygon(t.geo)
                            results.append(b_geo.buffer(
                                buf_distance - 1e-10,
                                resolution=int(int(geo_editor.app.options["geometry_circle_steps"]) / 4),
                                join_style=join_style).exterior
                                           )

                if not results:
                    geo_editor.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed, the result is empty."))
                    # deselect everything
                    geo_editor.selected = []
                    geo_editor.plot_all()
                    return 'fail'

                for sha in results:
                    geo_editor.add_shape(sha)

                geo_editor.plot_all()
                geo_editor.build_ui_sig.emit()
                geo_editor.app.inform.emit('[success] %s' % _("Done."))

        self.app.worker_task.emit({'fcn': work_task, 'params': [self]})

    def hide_tool(self):
        self.ui.buffer_tool_frame.hide()
        self.app.ui.notebook.setCurrentWidget(self.app.ui.properties_tab)


class BufferEditorUI:
    pluginName = _("Buffer")

    def __init__(self, layout, buffer_class):
        self.buffer_class = buffer_class
        self.decimals = self.buffer_class.app.decimals
        self.layout = layout

        # Title
        title_label = FCLabel("%s" % ('Editor ' + self.pluginName), size=16, bold=True)
        self.layout.addWidget(title_label)

        # this way I can hide/show the frame
        self.buffer_tool_frame = QtWidgets.QFrame()
        self.buffer_tool_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.buffer_tool_frame)
        self.buffer_tools_box = QtWidgets.QVBoxLayout()
        self.buffer_tools_box.setContentsMargins(0, 0, 0, 0)
        self.buffer_tool_frame.setLayout(self.buffer_tools_box)

        # Grid Layout
        grid_buffer = GLay(v_spacing=5, h_spacing=3)
        self.buffer_tools_box.addLayout(grid_buffer)

        # Buffer distance
        self.buffer_distance_entry = FCDoubleSpinner()
        self.buffer_distance_entry.set_precision(self.decimals)
        self.buffer_distance_entry.set_range(0.0000, 10000.0000)
        grid_buffer.addWidget(FCLabel('%s:' % _("Buffer distance")), 0, 0)
        grid_buffer.addWidget(self.buffer_distance_entry, 0, 1)

        self.buffer_corner_lbl = FCLabel('%s:' % _("Buffer corner"))
        self.buffer_corner_lbl.setToolTip(
            _("There are 3 types of corners:\n"
              " - 'Round': the corner is rounded for exterior buffer.\n"
              " - 'Square': the corner is met in a sharp angle for exterior buffer.\n"
              " - 'Beveled': the corner is a line that directly connects the features meeting in the corner")
        )
        self.buffer_corner_cb = FCComboBox()
        self.buffer_corner_cb.addItem(_("Round"))
        self.buffer_corner_cb.addItem(_("Square"))
        self.buffer_corner_cb.addItem(_("Beveled"))
        grid_buffer.addWidget(self.buffer_corner_lbl, 2, 0)
        grid_buffer.addWidget(self.buffer_corner_cb, 2, 1)

        # Buttons
        hlay = QtWidgets.QHBoxLayout()
        grid_buffer.addLayout(hlay, 4, 0, 1, 2)

        self.buffer_int_button = FCButton(_("Buffer Interior"))
        hlay.addWidget(self.buffer_int_button)
        self.buffer_ext_button = FCButton(_("Buffer Exterior"))
        hlay.addWidget(self.buffer_ext_button)

        hlay1 = QtWidgets.QHBoxLayout()
        grid_buffer.addLayout(hlay1, 6, 0, 1, 2)

        self.buffer_button = FCButton(_("Full Buffer"))
        hlay1.addWidget(self.buffer_button)

        self.layout.addStretch(1)
