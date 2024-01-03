
from PyQt6 import QtGui, QtWidgets, QtCore
from appTool import AppToolEditor
from appGUI.GUIElements import VerticalScrollArea, GLay, FCLabel, FCButton, FCFrame, FCTextEdit, FCEntry, \
    FCDoubleSpinner

# from camlib import  flatten_shapely_geometry
from copy import deepcopy

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class SimplificationTool(AppToolEditor):
    """
    Do a shape simplification for the selected geometry.
    """

    update_ui = QtCore.pyqtSignal(object, int)

    def __init__(self, app, draw_app):
        AppToolEditor.__init__(self, app)

        self.geo_editor = draw_app
        self.decimals = app.decimals
        self.app = self.geo_editor.app

        self.ui = SimplificationEditorUI(layout=self.layout, simp_class=self)
        self.plugin_name = self.ui.pluginName

        self.connect_signals_at_init()
        self.set_tool_ui()

    def connect_signals_at_init(self):
        # Signals
        self.ui.simplification_btn.clicked.connect(self.on_simplification_click)
        self.update_ui.connect(self.on_update_ui)

    def run(self):
        self.app.defaults.report_usage("Geo Editor SimplificationTool()")
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

        self.app.ui.notebook.setTabText(2,  self.plugin_name)

    def set_tool_ui(self):
        # Init appGUI
        self.ui.geo_tol_entry.set_value(0.01 if self.geo_editor.units == 'MM' else 0.0004)

        selected_shapes_geos = []
        selected_tree_items = self.geo_editor.ui.tw.selectedItems()
        for sel in selected_tree_items:
            for obj_shape in self.geo_editor.storage.get_objects():
                try:
                    if id(obj_shape) == int(sel.text(0)):
                        selected_shapes_geos.append(obj_shape.geo)
                except (ValueError, AttributeError):
                    pass
        if selected_shapes_geos:
            # those are displayed by triggering the signal self.update_ui
            self.calculate_coordinates_vertex(selected_shapes_geos)

    def on_tab_close(self):
        self.geo_editor.select_tool("select")
        self.app.ui.notebook.callback_on_close = lambda: None

    def on_simplification_click(self):
        self.app.log.debug("FCSimplification.on_simplification_click()")

        tol = self.ui.geo_tol_entry.get_value()

        def task_job(geo_editor):
            with self.app.proc_container.new('%s...' % _("Simplifying")):
                geo_editor.interdict_selection = True

                # Simplification
                selected_shapes = geo_editor.selected
                selected_shapes_geos = [
                    deepcopy(obj_shape.geo.simplify(tolerance=tol)) for obj_shape in selected_shapes
                ]

                not_selected_geos = [
                    obj_shape for obj_shape in geo_editor.storage.get_objects() if obj_shape not in selected_shapes
                ]

                if not selected_shapes or not selected_shapes_geos:
                    self.app.inform.emit('%s' % _("Failed."))
                    return

                # reset the old storage
                geo_editor.storage = geo_editor.make_storage()
                geo_editor.ui.tw.blockSignals(True)
                # add again the shapes (modified and non-modified
                for geo in not_selected_geos + selected_shapes_geos:
                    geo_editor.add_shape(geo, build_ui=False)
                geo_editor.ui.tw.blockSignals(False)

                # # -----------------------------------------------------
                # # Shape Deletion -> Shape Adding
                # # geo_editor.ui.tw.blockSignals(True)
                # geo_editor.delete_shape(selected_shapes)
                #
                # # while adding the shape also add it to selected
                # for geo in selected_shapes_geos:
                #     geo_editor.add_shape(geo, build_ui=False)
                # # geo_editor.ui.tw.blockSignals(False)
                # # -----------------------------------------------------

                self.calculate_coordinates_vertex(selected_shapes_geos)
                geo_editor.plot_all()

                geo_editor.interdict_selection = False
                geo_editor.build_ui_sig.emit()
                self.app.inform.emit('%s' % _("Done."))

        self.app.worker_task.emit({'fcn': task_job, 'params': [self.geo_editor]})

    def calculate_coordinates_vertex(self, selected_geos):
        vertex_nr = 0
        coordinates = ''

        if not isinstance(selected_geos, list):
            selected_geos = [selected_geos]
        for c_geo in selected_geos:
            if c_geo.geom_type == 'MultiLineString':
                for idx, line in enumerate(c_geo.geoms):
                    line_coords = list(line.coords)
                    vertex_nr += len(line_coords)
                    coordinates += 'Line %s\n' % str(idx)
                    coordinates += str(line_coords) + '\n'
            elif c_geo.geom_type == 'MultiPolygon':
                for idx, poly in enumerate(c_geo.geoms):
                    poly_coords = list(poly.exterior.coords) + [list(i.coords) for i in poly.interiors]
                    vertex_nr += len(poly_coords)

                    coordinates += 'Polygon %s\n' % str(idx)
                    coordinates += str(poly_coords) + '\n'
            elif c_geo.geom_type in ['LinearRing', 'LineString']:
                line_coords = list(c_geo.coords)
                coordinates += 'Line \n'
                coordinates += str(line_coords) + '\n'

                vertex_nr += len(line_coords)
            elif c_geo.geom_type == 'Polygon':
                line_coords = list(c_geo.exterior.coords)
                coordinates += 'Line \n'
                coordinates += str(line_coords) + '\n'

                vertex_nr += len(line_coords)
            else:
                coordinates += 'None\n'

        # if last_sel_geo:
        #     if last_sel_geo.geom_type == 'MultiLineString':
        #         coordinates = ''
        #         vertex_nr = 0
        #         for idx, line in enumerate(last_sel_geo.geoms):
        #             line_coords = list(line.coordinates)
        #             vertex_nr += len(line_coords)
        #             coordinates += 'Line %s\n' % str(idx)
        #             coordinates += str(line_coords) + '\n'
        #     elif last_sel_geo.geom_type == 'MultiPolygon':
        #         coordinates = ''
        #         vertex_nr = 0
        #         for idx, poly in enumerate(last_sel_geo.geoms):
        #             poly_coords = list(poly.exterior.coordinates) + [list(i.coordinates) for i in poly.interiors]
        #             vertex_nr += len(poly_coords)
        #
        #             coordinates += 'Polygon %s\n' % str(idx)
        #             coordinates += str(poly_coords) + '\n'
        #     elif last_sel_geo.geom_type in ['LinearRing', 'LineString']:
        #         coordinates = list(last_sel_geo.coordinates)
        #         vertex_nr = len(coordinates)
        #     elif last_sel_geo.geom_type == 'Polygon':
        #         coordinates = list(last_sel_geo.exterior.coordinates)
        #         vertex_nr = len(coordinates)
        #     else:
        #         coordinates = 'None'
        #         vertex_nr = 0

            self.update_ui.emit(coordinates, vertex_nr)

    def on_update_ui(self, coords, vertex_nr):
        self.ui.geo_coords_entry.set_value(str(coords))
        self.ui.geo_vertex_entry.set_value(vertex_nr)

    def hide_tool(self):
        self.ui.simp_frame.hide()
        self.app.ui.notebook.setCurrentWidget(self.app.ui.properties_tab)


class SimplificationEditorUI:
    pluginName = _("Simplification")

    def __init__(self, layout, simp_class):
        self.simp_class = simp_class
        self.app = self.simp_class.app
        self.decimals = self.app.decimals
        self.layout = layout

        # Title
        title_label = FCLabel("%s" % ('Editor ' + self.pluginName), size=16, bold=True)
        self.layout.addWidget(title_label)

        # this way I can hide/show the frame
        self.simp_frame = QtWidgets.QFrame()
        self.simp_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.simp_frame)
        self.simp_tools_box = QtWidgets.QVBoxLayout()
        self.simp_tools_box.setContentsMargins(0, 0, 0, 0)
        self.simp_frame.setLayout(self.simp_tools_box)

        # Grid Layout
        grid0 = GLay(v_spacing=5, h_spacing=3)
        self.simp_tools_box.addLayout(grid0)

        # Coordinates
        coords_lbl = FCLabel('%s' % _("Coordinates"), bold=True, color='red')
        coords_lbl.setToolTip(
            _("The coordinates of the selected geometry element.")
        )
        grid0.addWidget(coords_lbl, 0, 0, 1, 2)

        # #############################################################################################################
        # Coordinates Frame
        # #############################################################################################################
        coors_frame = FCFrame()
        grid0.addWidget(coors_frame, 2, 0, 1, 2)

        coords_grid = GLay(v_spacing=5, h_spacing=3)
        coors_frame.setLayout(coords_grid)

        self.geo_coords_entry = FCTextEdit()
        self.geo_coords_entry.setPlaceholderText(
            _("The coordinates of the selected geometry element.")
        )
        coords_grid.addWidget(self.geo_coords_entry, 0, 0, 1, 2)

        # Vertex Points Number
        vertex_lbl = FCLabel('%s:' % _("Vertex Points"), bold=False)
        vertex_lbl.setToolTip(
            _("The number of vertex points in the selected geometry element.")
        )
        self.geo_vertex_entry = FCEntry(decimals=self.decimals)
        self.geo_vertex_entry.setReadOnly(True)

        coords_grid.addWidget(vertex_lbl, 2, 0)
        coords_grid.addWidget(self.geo_vertex_entry, 2, 1)

        # Simplification Title
        par_lbl = FCLabel('%s' % _("Parameters"), bold=True, color='blue')
        grid0.addWidget(par_lbl, 4, 0, 1, 2)
        # #############################################################################################################
        # Parameters Frame
        # #############################################################################################################
        par_frame = FCFrame()
        grid0.addWidget(par_frame, 6, 0, 1, 2)

        par_grid = GLay(v_spacing=5, h_spacing=3)
        par_frame.setLayout(par_grid)

        # Simplification Tolerance
        simplification_tol_lbl = FCLabel('%s' % _("Tolerance"), bold=True)
        simplification_tol_lbl.setToolTip(
            _("All points in the simplified object will be\n"
              "within the tolerance distance of the original geometry.")
        )
        self.geo_tol_entry = FCDoubleSpinner()
        self.geo_tol_entry.set_precision(self.decimals)
        self.geo_tol_entry.setSingleStep(10 ** -self.decimals)
        self.geo_tol_entry.set_range(0.0000, 10000.0000)

        par_grid.addWidget(simplification_tol_lbl, 0, 0)
        par_grid.addWidget(self.geo_tol_entry, 0, 1)

        # Simplification button
        self.simplification_btn = FCButton(_("Simplify"), bold=True)
        self.simplification_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/simplify32.png'))
        self.simplification_btn.setToolTip(
            _("Simplify a geometry element by reducing its vertex points number.")
        )

        self.layout.addWidget(self.simplification_btn)

        GLay.set_common_column_size([grid0, coords_grid, par_grid], 0)
        self.layout.addStretch(1)
