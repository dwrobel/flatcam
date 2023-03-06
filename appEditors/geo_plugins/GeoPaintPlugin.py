
from PyQt6 import QtWidgets
from appTool import AppToolEditor
from appGUI.GUIElements import VerticalScrollArea, FCLabel, FCFrame, FCButton, GLay, FCDoubleSpinner, FCComboBox, \
    FCCheckBox
from camlib import Geometry

from shapely.geometry import Polygon
from shapely.ops import unary_union

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class PaintOptionsTool(AppToolEditor):
    """
    Inputs to specify how to paint the selected polygons.
    """

    def __init__(self, app, fcdraw):
        AppToolEditor.__init__(self, app)

        self.app = app
        self.fcdraw = fcdraw
        self.decimals = self.app.decimals

        self.ui = PaintEditorUI(layout=self.layout, paint_class=self)

        self.connect_signals_at_init()
        self.set_tool_ui()

    def run(self):
        self.app.defaults.report_usage("Geo Editor ToolPaint()")
        AppToolEditor.run(self)

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

        self.app.ui.notebook.setTabText(2, _("Paint Tool"))

    def connect_signals_at_init(self):
        # Signals
        self.ui.paint_button.clicked.connect(self.on_paint)

    def on_tab_close(self):
        self.fcdraw.select_tool("select")
        self.app.ui.notebook.callback_on_close = lambda: None

    def set_tool_ui(self):
        # Init appGUI
        if self.app.options["tools_paint_tooldia"]:
            self.ui.painttooldia_entry.set_value(self.app.options["tools_paint_tooldia"])
        else:
            self.ui.painttooldia_entry.set_value(0.0)

        if self.app.options["tools_paint_overlap"]:
            self.ui.paintoverlap_entry.set_value(self.app.options["tools_paint_overlap"])
        else:
            self.ui.paintoverlap_entry.set_value(0.0)

        if self.app.options["tools_paint_offset"]:
            self.ui.paintmargin_entry.set_value(self.app.options["tools_paint_offset"])
        else:
            self.ui.paintmargin_entry.set_value(0.0)

        if self.app.options["tools_paint_method"]:
            self.ui.paintmethod_combo.set_value(self.app.options["tools_paint_method"])
        else:
            self.ui.paintmethod_combo.set_value(_("Seed"))

        if self.app.options["tools_paint_connect"]:
            self.ui.pathconnect_cb.set_value(self.app.options["tools_paint_connect"])
        else:
            self.ui.pathconnect_cb.set_value(False)

        if self.app.options["tools_paint_contour"]:
            self.ui.paintcontour_cb.set_value(self.app.options["tools_paint_contour"])
        else:
            self.ui.paintcontour_cb.set_value(False)

    def on_paint(self):
        if not self.fcdraw.selected:
            self.app.inform.emit('[WARNING_NOTCL] %s %s' % (_("Cancelled."), _("No shape selected.")))
            return

        tooldia = self.ui.painttooldia_entry.get_value()
        overlap = self.ui.paintoverlap_entry.get_value() / 100.0
        margin = self.ui.paintmargin_entry.get_value()

        method = self.ui.paintmethod_combo.get_value()
        contour = self.ui.paintcontour_cb.get_value()
        connect = self.ui.pathconnect_cb.get_value()

        self.paint(tooldia, overlap, margin, connect=connect, contour=contour, method=method)
        self.fcdraw.select_tool("select")
        # self.app.ui.notebook.setTabText(2, _("Tools"))
        # self.app.ui.notebook.setCurrentWidget(self.app.ui.project_tab)
        #
        # self.app.ui.splitter.setSizes([0, 1])

    def paint(self, tooldia, overlap, margin, connect, contour, method):
        def work_task(geo_editor):
            with geo_editor.app.proc_container.new(_("Working...")):
                if overlap >= 100:
                    geo_editor.app.inform.emit('[ERROR_NOTCL] %s' %
                                               _("Could not do Paint. Overlap value has to be less than 100%%."))
                    return

                geo_editor.paint_tooldia = tooldia
                selected = geo_editor.get_selected()

                if len(selected) == 0:
                    geo_editor.app.inform.emit('[WARNING_NOTCL] %s' % _("Nothing selected."))
                    return

                for param in [tooldia, overlap, margin]:
                    if not isinstance(param, float):
                        param_name = [k for k, v in locals().items() if v is param][0]
                        geo_editor.app.inform.emit('[WARNING] %s: %s' % (_("Invalid value for"), str(param)))

                results = []

                def recurse(geometry, reset=True):
                    """
                    Creates a list of non-iterable linear geometry objects.
                    Results are placed in self.flat_geometry

                    :param geometry: Shapely type, list or list of lists of such.
                    :param reset: Clears the contents of self.flat_geometry.
                    """

                    if geometry is None:
                        return

                    if reset:
                        self.flat_geo = []

                    # If iterable, expand recursively.
                    try:
                        for geo_el in geometry:
                            if geo_el is not None and not geo_el.is_emoty:
                                recurse(geometry=geo_el, reset=False)

                    # Not iterable, do the actual indexing and add.
                    except TypeError:
                        self.flat_geo.append(geometry)

                    return self.flat_geo

                for geo in selected:

                    local_results = []
                    for geo_obj in recurse(geo.geo):
                        try:
                            if type(geo_obj) == Polygon:
                                poly_buf = geo_obj.buffer(-margin)
                            else:
                                poly_buf = Polygon(geo_obj).buffer(-margin)

                            if method == _("Seed"):
                                cp = Geometry.clear_polygon2(
                                    geo_editor, polygon_to_clear=poly_buf, tooldia=tooldia,
                                    steps_per_circle=geo_editor.app.options["geometry_circle_steps"],
                                    overlap=overlap, contour=contour, connect=connect)
                            elif method == _("Lines"):
                                cp = Geometry.clear_polygon3(
                                    geo_editor, polygon=poly_buf, tooldia=tooldia,
                                    steps_per_circle=geo_editor.app.options["geometry_circle_steps"],
                                    overlap=overlap, contour=contour, connect=connect)
                            else:
                                cp = Geometry.clear_polygon(
                                    geo_editor, polygon=poly_buf, tooldia=tooldia,
                                    steps_per_circle=geo_editor.app.options["geometry_circle_steps"],
                                    overlap=overlap, contour=contour, connect=connect)

                            if cp is not None:
                                local_results += list(cp.get_objects())
                        except Exception as e:
                            geo_editor.app.log.error("Could not Paint the polygons. %s" % str(e))
                            geo_editor.app.inform.emit(
                                '[ERROR] %s\n%s' % (_("Could not do Paint. Try a different combination of parameters. "
                                                      "Or a different method of Paint"), str(e))
                            )
                            return

                        # add the result to the results list
                        results.append(unary_union(local_results))

                # This is a dirty patch:
                for r in results:
                    geo_editor.add_shape(r)
                geo_editor.plot_all()
                geo_editor.build_ui_sig.emit()
                geo_editor.app.inform.emit('[success] %s' % _("Done."))

        self.app.worker_task.emit({'fcn': work_task, 'params': [self.fcdraw]})


class PaintEditorUI:
    pluginName = _("Paint")

    def __init__(self, layout, paint_class):
        self.paint_class = paint_class
        self.decimals = self.paint_class.app.decimals
        self.layout = layout

        # Title
        title_label = FCLabel("%s" % self.pluginName, size=16, bold=True)
        self.layout.addWidget(title_label)

        self.param_label = FCLabel('%s' % _("Parameters"), color='blue', bold=True)
        self.layout.addWidget(self.param_label)

        # #############################################################################################################
        # Tool Params Frame
        # #############################################################################################################
        tool_par_frame = FCFrame()
        self.layout.addWidget(tool_par_frame)

        # Grid Layout
        param_grid = GLay(v_spacing=5, h_spacing=3)
        tool_par_frame.setLayout(param_grid)

        # Tool dia
        ptdlabel = FCLabel('%s:' % _('Tool Dia'))
        ptdlabel.setToolTip(
            _("Diameter of the tool to be used in the operation.")
        )
        param_grid.addWidget(ptdlabel, 0, 0)

        self.painttooldia_entry = FCDoubleSpinner()
        self.painttooldia_entry.set_range(-10000.0000, 10000.0000)
        self.painttooldia_entry.set_precision(self.decimals)
        param_grid.addWidget(self.painttooldia_entry, 0, 1)

        # Overlap
        ovlabel = FCLabel('%s:' % _('Overlap'))
        ovlabel.setToolTip(
            _("How much (percentage) of the tool width to overlap each tool pass.\n"
              "Adjust the value starting with lower values\n"
              "and increasing it if areas that should be processed are still \n"
              "not processed.\n"
              "Lower values = faster processing, faster execution on CNC.\n"
              "Higher values = slow processing and slow execution on CNC\n"
              "due of too many paths.")
        )
        self.paintoverlap_entry = FCDoubleSpinner(suffix='%')
        self.paintoverlap_entry.set_range(0.0000, 99.9999)
        self.paintoverlap_entry.set_precision(self.decimals)
        self.paintoverlap_entry.setWrapping(True)
        self.paintoverlap_entry.setSingleStep(1)

        param_grid.addWidget(ovlabel, 1, 0)
        param_grid.addWidget(self.paintoverlap_entry, 1, 1)

        # Margin
        marginlabel = FCLabel('%s:' % _('Margin'))
        marginlabel.setToolTip(
            _("Distance by which to avoid\n"
              "the edges of the polygon to\n"
              "be painted.")
        )
        self.paintmargin_entry = FCDoubleSpinner()
        self.paintmargin_entry.set_range(-10000.0000, 10000.0000)
        self.paintmargin_entry.set_precision(self.decimals)

        param_grid.addWidget(marginlabel, 2, 0)
        param_grid.addWidget(self.paintmargin_entry, 2, 1)

        # Method
        methodlabel = FCLabel('%s:' % _('Method'))
        methodlabel.setToolTip(
            _("Algorithm to paint the polygons:\n"
              "- Standard: Fixed step inwards.\n"
              "- Seed-based: Outwards from seed.\n"
              "- Line-based: Parallel lines.")
        )
        # self.paintmethod_combo = RadioSet([
        #     {"label": _("Standard"), "value": "standard"},
        #     {"label": _("Seed-based"), "value": "seed"},
        #     {"label": _("Straight lines"), "value": "lines"}
        # ], orientation='vertical', compact=True)
        self.paintmethod_combo = FCComboBox()
        self.paintmethod_combo.addItems(
            [_("Standard"), _("Seed"), _("Lines")]
        )

        param_grid.addWidget(methodlabel, 3, 0)
        param_grid.addWidget(self.paintmethod_combo, 3, 1)

        # Connect lines
        pathconnectlabel = FCLabel('%s:' % _("Connect"))
        pathconnectlabel.setToolTip(
            _("Draw lines between resulting\n"
              "segments to minimize tool lifts.")
        )
        self.pathconnect_cb = FCCheckBox()

        param_grid.addWidget(pathconnectlabel, 4, 0)
        param_grid.addWidget(self.pathconnect_cb, 4, 1)

        contourlabel = FCLabel('%s:' % _("Contour"))
        contourlabel.setToolTip(
            _("Cut around the perimeter of the polygon\n"
              "to trim rough edges.")
        )
        self.paintcontour_cb = FCCheckBox()

        param_grid.addWidget(contourlabel, 5, 0)
        param_grid.addWidget(self.paintcontour_cb, 5, 1)

        # Buttons
        hlay = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay)
        self.paint_button = FCButton(_("Paint"))
        hlay.addWidget(self.paint_button)

        self.layout.addStretch(1)
