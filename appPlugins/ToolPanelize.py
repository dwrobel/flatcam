# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt6 import QtWidgets, QtCore, QtGui
from appTool import AppTool
from appGUI.GUIElements import VerticalScrollArea, FCLabel, FCButton, FCFrame, GLay, FCComboBox, FCCheckBox, \
    RadioSet, FCDoubleSpinner, FCSpinner, OptionalInputSection
from camlib import grace

import logging
from copy import deepcopy
import numpy as np

from shapely import LineString, MultiLineString, Polygon, MultiPolygon
from shapely.ops import unary_union, linemerge, snap
from shapely.affinity import translate

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class Panelize(AppTool):

    pluginName = _("Panelize PCB")

    def __init__(self, app):
        AppTool.__init__(self, app)
        self.decimals = app.decimals
        self.app = app

        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = PanelizeUI(layout=self.layout, app=self.app)
        self.pluginName = self.ui.pluginName
        self.connect_signals_at_init()

        # list to hold the temporary objects
        self.objs = []

        # final name for the panel object
        self.outname = ""

        # flag to signal the constrain was activated
        self.constrain_flag = False

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolPanelize()")

        if toggle:
            # if the splitter is hidden, display it
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

            try:
                if self.app.ui.plugin_scroll_area.widget().objectName() == self.pluginName and found_idx:
                    # if the Tool Tab is not focused, focus on it
                    if not self.app.ui.notebook.currentWidget() is self.app.ui.plugin_tab:
                        # focus on Tool Tab
                        self.app.ui.notebook.setCurrentWidget(self.app.ui.plugin_tab)
                    else:
                        # else remove the Tool Tab
                        self.app.ui.notebook.setCurrentWidget(self.app.ui.properties_tab)
                        self.app.ui.notebook.removeTab(2)

                        # if there are no objects loaded in the app then hide the Notebook widget
                        if not self.app.collection.get_list():
                            self.app.ui.splitter.setSizes([0, 1])
            except AttributeError:
                pass
        else:
            if self.app.ui.splitter.sizes()[0] == 0:
                self.app.ui.splitter.setSizes([1, 1])

        super().run()
        self.set_tool_ui()

        self.app.ui.notebook.setTabText(2, _("Panelization"))

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Alt+Z', **kwargs)

    def connect_signals_at_init(self):
        self.ui.level.toggled.connect(self.on_level_changed)
        self.ui.reference_radio.activated_custom.connect(self.on_reference_radio_changed)
        self.ui.panelize_object_button.clicked.connect(self.on_panelize)
        self.ui.type_obj_combo.currentIndexChanged.connect(self.on_type_obj_index_changed)
        self.ui.type_box_combo.currentIndexChanged.connect(self.on_type_box_index_changed)

        self.app.proj_selection_changed.connect(self.on_object_selection_changed)

        self.ui.reset_button.clicked.connect(self.set_tool_ui)

    def set_tool_ui(self):
        self.clear_ui(self.layout)
        self.ui = PanelizeUI(layout=self.layout, app=self.app)
        self.pluginName = self.ui.pluginName

        self.reset_fields()

        self.ui.reference_radio.set_value('bbox')
        self.on_reference_radio_changed(current_val=self.ui.reference_radio.get_value())

        # SELECT THE CURRENT OBJECT
        obj = self.app.collection.get_active()
        if obj:
            obj_name = obj.obj_options['name']
            if obj.kind == 'gerber':
                # run once to make sure that the obj_type attribute is updated in the FCComboBox
                self.ui.type_obj_combo.set_value(_("Gerber"))
            elif obj.kind == 'excellon':
                # run once to make sure that the obj_type attribute is updated in the FCComboBox
                self.ui.type_obj_combo.set_value(_("Excellon"))
            elif obj.kind == 'geometry':
                # run once to make sure that the obj_type attribute is updated in the FCComboBox
                self.ui.type_obj_combo.set_value(_("Geometry"))

            self.ui.object_combo.set_value(obj_name)

        sp_c = self.app.options["tools_panelize_spacing_columns"] if \
            self.app.options["tools_panelize_spacing_columns"] else 0.0
        self.ui.spacing_columns.set_value(float(sp_c))

        sp_r = self.app.options["tools_panelize_spacing_rows"] if \
            self.app.options["tools_panelize_spacing_rows"] else 0.0
        self.ui.spacing_rows.set_value(float(sp_r))

        rr = self.app.options["tools_panelize_rows"] if \
            self.app.options["tools_panelize_rows"] else 0.0
        self.ui.rows.set_value(int(rr))

        cc = self.app.options["tools_panelize_columns"] if \
            self.app.options["tools_panelize_columns"] else 0.0
        self.ui.columns.set_value(int(cc))

        optimized_path_cb = self.app.options["tools_panelize_optimization"] if \
            self.app.options["tools_panelize_optimization"] else True
        self.ui.optimization_cb.set_value(optimized_path_cb)

        c_cb = self.app.options["tools_panelize_constrain"] if \
            self.app.options["tools_panelize_constrain"] else False
        self.ui.constrain_cb.set_value(c_cb)

        x_w = self.app.options["tools_panelize_constrainx"] if \
            self.app.options["tools_panelize_constrainx"] else 0.0
        self.ui.x_width_entry.set_value(float(x_w))

        y_w = self.app.options["tools_panelize_constrainy"] if \
            self.app.options["tools_panelize_constrainy"] else 0.0
        self.ui.y_height_entry.set_value(float(y_w))

        panel_type = self.app.options["tools_panelize_panel_type"] if \
            self.app.options["tools_panelize_panel_type"] else 'gerber'
        self.ui.panel_type_radio.set_value(panel_type)

        self.ui.on_panel_type(val=panel_type)

        # run once the following so the obj_type attribute is updated in the FCComboBoxes
        # such that the last loaded object is populated in the combo boxes
        self.on_type_obj_index_changed()
        self.on_type_box_index_changed()

        self.connect_signals_at_init()

        # Show/Hide Advanced Options
        app_mode = self.app.options["global_app_level"]
        self.change_level(app_mode)

    def on_type_obj_index_changed(self):
        obj_type = self.ui.type_obj_combo.currentIndex()
        self.ui.object_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.ui.object_combo.setCurrentIndex(0)

        self.ui.object_combo.obj_type = {0: "Gerber", 1: "Excellon", 2: "Geometry"}[obj_type]

        # hide the panel type for Excellons, the panel can be only of type Geometry or Gerber
        if obj_type != 1:   # not Excellon
            self.ui.panel_type_label.setDisabled(False)
            self.ui.panel_type_radio.setDisabled(False)
            panel_type = self.ui.panel_type_radio.get_value()
            self.ui.on_panel_type(val=panel_type)
        else:
            self.ui.panel_type_label.setDisabled(True)
            self.ui.panel_type_radio.setDisabled(True)
            self.ui.optimization_cb.setDisabled(True)

        if obj_type in [0, 2]:
            # type_box_combo is missing the Excellon therefore it has only index 0 an 1
            self.ui.type_box_combo.setCurrentIndex(0) if obj_type == 0 else self.ui.type_box_combo.setCurrentIndex(1)
            self.ui.panel_type_radio.set_value(self.ui.object_combo.obj_type.lower())

    def on_type_box_index_changed(self):
        obj_type = self.ui.type_box_combo.currentIndex()
        obj_type = 2 if obj_type == 1 else obj_type
        self.ui.box_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.ui.box_combo.setCurrentIndex(0)

        self.ui.box_combo.obj_type = {0: "Gerber", 2: "Geometry"}[obj_type]

    def on_reference_radio_changed(self, current_val):
        if current_val == 'object':
            self.ui.type_box_combo.setDisabled(False)
            self.ui.type_box_combo_label.setDisabled(False)
            self.ui.box_combo.setDisabled(False)
        else:
            self.ui.type_box_combo.setDisabled(True)
            self.ui.type_box_combo_label.setDisabled(True)
            self.ui.box_combo.setDisabled(True)

    def on_object_selection_changed(self, current, previous):
        found_idx = None
        for tab_idx in range(self.app.ui.notebook.count()):
            if self.app.ui.notebook.tabText(tab_idx) == self.ui.pluginName:
                found_idx = True
                break

        if found_idx:
            try:
                name = current.indexes()[0].internalPointer().obj.obj_options['name']
                kind = current.indexes()[0].internalPointer().obj.kind

                if kind in ['gerber', 'excellon', 'geometry']:
                    obj_type = {
                        "gerber": _("Gerber"), "excellon": _("Excellon"), "geometry": _("Geometry")
                    }[kind]

                    self.ui.type_obj_combo.set_value(obj_type)
                    self.ui.type_box_combo.set_value(obj_type)

                self.ui.object_combo.set_value(name)
                self.ui.box_combo.set_value(name)
            except Exception:
                pass

    def change_level(self, level):
        """

        :param level:   application level: either 'b' or 'a'
        :type level:    str
        :return:
        """

        if level == 'a':
            self.ui.level.setChecked(True)
        else:
            self.ui.level.setChecked(False)
        self.on_level_changed(self.ui.level.isChecked())

    def on_level_changed(self, checked):
        if not checked:
            self.ui.level.setText('%s' % _('Beginner'))
            self.ui.level.setStyleSheet("""
                                        QToolButton
                                        {
                                            color: green;
                                        }
                                        """)

            # Parameters section
            self.ui.param_label.hide()
            self.ui.gp_frame.hide()
        else:
            self.ui.level.setText('%s' % _('Advanced'))
            self.ui.level.setStyleSheet("""
                                        QToolButton
                                        {
                                            color: red;
                                        }
                                        """)

            # Parameters section
            self.ui.param_label.show()
            self.ui.gp_frame.show()

    def on_panelize(self):
        name = self.ui.object_combo.currentText()

        # delete any selection box
        self.app.delete_selection_shape()

        # Get source object to be panelized.
        try:
            panel_source_obj = self.app.collection.get_by_name(str(name))
        except Exception as e:
            self.app.log.error("Panelize.on_panelize() --> %s" % str(e))
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), name))
            return

        if panel_source_obj is None:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' %
                                 (_("Object not found"), panel_source_obj))
            return

        boxname = self.ui.box_combo.currentText()

        try:
            box_obj = self.app.collection.get_by_name(boxname)
        except Exception as e:
            self.app.log.error("Panelize.on_panelize() --> %s" % str(e))
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), boxname))
            return

        if box_obj is None:
            self.app.inform.emit('[WARNING_NOTCL] %s: %s' % (_("No object Box. Using instead"), panel_source_obj))
            self.ui.reference_radio.set_value('bbox')

        if self.ui.reference_radio.get_value() == 'bbox':
            box_obj = panel_source_obj

        self.outname = name + '_panelized'

        spacing_columns = float(self.ui.spacing_columns.get_value())
        spacing_columns = spacing_columns if spacing_columns is not None else 0

        spacing_rows = float(self.ui.spacing_rows.get_value())
        spacing_rows = spacing_rows if spacing_rows is not None else 0

        rows = int(self.ui.rows.get_value())
        rows = rows if rows is not None else 1

        columns = int(self.ui.columns.get_value())
        columns = columns if columns is not None else 1

        constrain_dx = float(self.ui.x_width_entry.get_value())
        constrain_dy = float(self.ui.y_height_entry.get_value())

        panel_type = str(self.ui.panel_type_radio.get_value())

        if 0 in {columns, rows}:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Columns or Rows are zero value. Change them to a positive integer."))
            return

        xmin, ymin, xmax, ymax = box_obj.bounds()
        lenghtx = xmax - xmin + spacing_columns
        lenghty = ymax - ymin + spacing_rows

        # check if constrain within an area is desired
        if self.ui.constrain_cb.isChecked():
            panel_lengthx = ((xmax - xmin) * columns) + (spacing_columns * (columns - 1))
            panel_lengthy = ((ymax - ymin) * rows) + (spacing_rows * (rows - 1))

            # adjust the number of columns and/or rows so the panel will fit within the panel constraint area
            if (panel_lengthx > constrain_dx) or (panel_lengthy > constrain_dy):
                self.constrain_flag = True

                while panel_lengthx > constrain_dx:
                    columns -= 1
                    panel_lengthx = ((xmax - xmin) * columns) + (spacing_columns * (columns - 1))
                while panel_lengthy > constrain_dy:
                    rows -= 1
                    panel_lengthy = ((ymax - ymin) * rows) + (spacing_rows * (rows - 1))

        # ############################################################################################################
        # make a copy of the panelized Excellon or Geometry tools
        # ############################################################################################################
        if panel_source_obj.kind == 'excellon' or panel_source_obj.kind == 'geometry':
            copied_tools = {}
            for tt, tt_val in list(panel_source_obj.tools.items()):
                copied_tools[tt] = deepcopy(tt_val)

        # ############################################################################################################
        # make a copy of the panelized Gerber apertures
        # ############################################################################################################
        if panel_source_obj.kind == 'gerber':
            copied_apertures = {}
            for tt, tt_val in list(panel_source_obj.tools.items()):
                copied_apertures[tt] = deepcopy(tt_val)

        to_optimize = self.ui.optimization_cb.get_value()

        def panelize_worker():
            if panel_source_obj is not None:
                self.app.inform.emit(_("Generating panel ... "))

                def job_init_excellon(obj_fin, app_obj):
                    obj_fin.multitool = True

                    currenty = 0.0
                    # init the storage for drills and for slots
                    for tool in copied_tools:
                        copied_tools[tool]['drills'] = []
                        copied_tools[tool]['slots'] = []
                    obj_fin.tools = copied_tools
                    obj_fin.solid_geometry = []

                    for option in panel_source_obj.obj_options:
                        if option != 'name':
                            try:
                                obj_fin.obj_options[option] = panel_source_obj.obj_options[option]
                            except KeyError:
                                app_obj.log.warning("Failed to copy option. %s" % str(option))

                    # calculate the total number of drills and slots
                    geo_len_drills = 0
                    geo_len_slots = 0
                    for tool in copied_tools:
                        geo_len_drills += len(copied_tools[tool]['drills'])
                        geo_len_slots += len(copied_tools[tool]['slots'])

                    # panelization
                    element = 0
                    for row in range(rows):
                        currentx = 0.0
                        for col in range(columns):
                            element += 1
                            old_disp_number = 0

                            for tool in panel_source_obj.tools:
                                if 'drills' in panel_source_obj.tools[tool]:
                                    if panel_source_obj.tools[tool]['drills']:
                                        drill_nr = 0
                                        for drill in panel_source_obj.tools[tool]['drills']:
                                            # graceful abort requested by the user
                                            if self.app.abort_flag:
                                                raise grace

                                            # offset / panelization
                                            point_offseted = translate(drill, currentx, currenty)
                                            obj_fin.tools[tool]['drills'].append(point_offseted)

                                            # update progress
                                            drill_nr += 1
                                            disp_number = int(np.interp(drill_nr, [0, geo_len_drills], [0, 100]))
                                            if old_disp_number < disp_number <= 100:
                                                self.app.proc_container.update_view_text(' %s: %d D:%d%%' %
                                                                                         (_("Copy"),
                                                                                          int(element),
                                                                                          disp_number))
                                                old_disp_number = disp_number
                                else:
                                    panel_source_obj.tools[tool]['drills'] = []

                                if 'slots' in panel_source_obj.tools[tool]:
                                    if panel_source_obj.tools[tool]['slots']:
                                        slot_nr = 0
                                        for slot in panel_source_obj.tools[tool]['slots']:
                                            # graceful abort requested by the user
                                            if self.app.abort_flag:
                                                raise grace

                                            # offset / panelization
                                            start_offseted = translate(slot[0], currentx, currenty)
                                            stop_offseted = translate(slot[1], currentx, currenty)
                                            offseted_slot = (
                                                start_offseted,
                                                stop_offseted
                                            )
                                            obj_fin.tools[tool]['slots'].append(offseted_slot)

                                            # update progress
                                            slot_nr += 1
                                            disp_number = int(np.interp(slot_nr, [0, geo_len_slots], [0, 100]))
                                            if old_disp_number < disp_number <= 100:
                                                self.app.proc_container.update_view_text(' %s: %d S:%d%%' %
                                                                                         (_("Copy"),
                                                                                          int(element),
                                                                                          disp_number))
                                                old_disp_number = disp_number
                                else:
                                    panel_source_obj.tools[tool]['slots'] = []

                            currentx += lenghtx
                        currenty += lenghty

                    obj_fin.create_geometry()
                    obj_fin.zeros = panel_source_obj.zeros
                    obj_fin.units = panel_source_obj.units
                    app_obj.inform.emit('%s' % _("Generating panel ... Adding the source code."))
                    obj_fin.source_file = self.app.f_handlers.export_excellon(obj_name=self.outname,
                                                                              filename=None,
                                                                              local_use=obj_fin,
                                                                              use_thread=False)
                    app_obj.proc_container.update_view_text('')

                def job_init_geometry(new_obj, app_obj):
                    currentx = 0.0
                    currenty = 0.0

                    def translate_recursion(geom):
                        if type(geom) == list:
                            geoms = []
                            for local_geom in geom:
                                res_geo = translate_recursion(local_geom)
                                try:
                                    geoms += res_geo
                                except TypeError:
                                    geoms.append(res_geo)
                            return geoms
                        else:
                            return translate(geom, xoff=currentx, yoff=currenty)

                    new_obj.solid_geometry = []

                    # create the initial structure on which to create the panel
                    if panel_source_obj.kind == 'geometry':
                        new_obj.multigeo = panel_source_obj.multigeo
                        new_obj.tools = copied_tools
                        if panel_source_obj.multigeo is True:
                            for tool in panel_source_obj.tools:
                                new_obj.tools[tool]['solid_geometry'] = []
                        else:
                            new_obj.solid_geometry = panel_source_obj.solid_geometry
                    elif panel_source_obj.kind == 'gerber':
                        new_obj.tools = copied_apertures
                        for ap in new_obj.tools:
                            new_obj.tools[ap]['geometry'] = []

                    # find the number of polygons in the source solid_geometry
                    geo_len = 0
                    if panel_source_obj.kind == 'geometry':
                        if panel_source_obj.multigeo is True:
                            for tool in panel_source_obj.tools:
                                try:
                                    source_geo = panel_source_obj.tools[tool]['solid_geometry']
                                    work_geo = source_geo.geoms if \
                                        isinstance(source_geo, (MultiPolygon, MultiLineString)) else source_geo
                                    geo_len += len(work_geo)
                                except TypeError:
                                    geo_len += 1
                        else:
                            try:
                                source_geo = panel_source_obj.solid_geometry
                                work_geo = source_geo.geoms if \
                                    isinstance(source_geo, (MultiPolygon, MultiLineString)) else source_geo
                                geo_len = len(work_geo)
                            except TypeError:
                                geo_len = 1
                    elif panel_source_obj.kind == 'gerber':
                        for ap in panel_source_obj.tools:
                            if 'geometry' in panel_source_obj.tools[ap]:
                                try:
                                    source_geo = panel_source_obj.tools[ap]['geometry']
                                    work_geo = source_geo.geoms if isinstance(source_geo, MultiPolygon) else source_geo
                                    geo_len += len(work_geo)
                                except TypeError:
                                    geo_len += 1

                    element = 0
                    for row in range(rows):
                        currentx = 0.0

                        for col in range(columns):
                            element += 1
                            old_disp_number = 0

                            # Will panelize a Geometry Object
                            if panel_source_obj.kind == 'geometry':
                                if panel_source_obj.multigeo is True:
                                    for tool in panel_source_obj.tools:
                                        # graceful abort requested by the user
                                        if app_obj.abort_flag:
                                            raise grace

                                        # calculate the number of polygons
                                        try:
                                            source_geo = panel_source_obj.tools[tool]['solid_geometry']
                                            work_geo = source_geo.geoms if \
                                                isinstance(source_geo, (MultiPolygon, MultiLineString)) else source_geo
                                            geo_len = len(work_geo)
                                        except TypeError as err:
                                            self.app.log.error(
                                                "Panelize.on_panelize.panelize_worker() -> %s" % str(err))
                                            geo_len = 1

                                        # panelization
                                        pol_nr = 0

                                        trans_geo = translate_recursion(panel_source_obj.tools[tool]['solid_geometry'])
                                        try:
                                            work_geo = trans_geo.geoms if \
                                                isinstance(trans_geo, (MultiPolygon, MultiLineString)) else trans_geo
                                            for trans_it in work_geo:
                                                if not trans_it.is_empty:
                                                    new_obj.tools[tool]['solid_geometry'].append(trans_it)

                                                # update progress
                                                pol_nr += 1
                                                disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 100]))
                                                if old_disp_number < disp_number <= 100:
                                                    app_obj.proc_container.update_view_text(
                                                        ' %s: %d %d%%' % (_("Copy"), int(element), disp_number))
                                                    old_disp_number = disp_number
                                        except TypeError:
                                            if not trans_geo.is_empty:
                                                new_obj.tools[tool]['solid_geometry'].append(trans_geo)

                                            # update progress
                                            pol_nr += 1
                                            disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 100]))
                                            if old_disp_number < disp_number <= 100:
                                                app_obj.proc_container.update_view_text(
                                                    ' %s: %d %d%%' % (_("Copy"), int(element), disp_number))
                                                old_disp_number = disp_number

                                # #####################################################################################
                                # ##########   Panelize the solid_geometry - always done  #############################
                                # #####################################################################################
                                # graceful abort requested by the user
                                if app_obj.abort_flag:
                                    raise grace

                                # calculate the number of polygons
                                try:
                                    source_geo = panel_source_obj.solid_geometry
                                    work_geo = source_geo.geoms if \
                                        isinstance(source_geo, (MultiPolygon, MultiLineString)) else source_geo
                                    geo_len = len(work_geo)
                                except TypeError:
                                    geo_len = 1

                                # panelization
                                pol_nr = 0
                                try:
                                    sol_geo = panel_source_obj.solid_geometry
                                    work_geo = sol_geo.geoms if \
                                        isinstance(sol_geo, (MultiPolygon, MultiLineString)) else sol_geo
                                    for geo_el in work_geo:
                                        if app_obj.abort_flag:
                                            # graceful abort requested by the user
                                            raise grace

                                        trans_geo = translate_recursion(geo_el)
                                        new_obj.solid_geometry.append(trans_geo)

                                        # update progress
                                        pol_nr += 1
                                        disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 100]))
                                        if old_disp_number < disp_number <= 100:
                                            app_obj.proc_container.update_view_text(
                                                ' %s: %d %d%%' % (_("Copy"), int(element), disp_number))
                                            old_disp_number = disp_number

                                except TypeError:
                                    trans_geo = translate_recursion(panel_source_obj.solid_geometry)
                                    new_obj.solid_geometry.append(trans_geo)

                            # Will panelize a Gerber Object
                            if panel_source_obj.kind == 'gerber':
                                # graceful abort requested by the user
                                if self.app.abort_flag:
                                    raise grace

                                for apid in panel_source_obj.tools:
                                    # graceful abort requested by the user
                                    if app_obj.abort_flag:
                                        raise grace

                                    if 'geometry' in panel_source_obj.tools[apid]:
                                        # calculate the number of polygons
                                        try:
                                            geo_len = len(panel_source_obj.tools[apid]['geometry'])
                                        except TypeError:
                                            geo_len = 1

                                        # panelization -> tools
                                        pol_nr = 0
                                        for el in panel_source_obj.tools[apid]['geometry']:
                                            if app_obj.abort_flag:
                                                # graceful abort requested by the user
                                                raise grace

                                            new_el = {}
                                            if 'solid' in el:
                                                geo_aper = translate_recursion(el['solid'])
                                                new_el['solid'] = geo_aper
                                            if 'clear' in el:
                                                geo_aper = translate_recursion(el['clear'])
                                                new_el['clear'] = geo_aper
                                            if 'follow' in el:
                                                geo_aper = translate_recursion(el['follow'])
                                                new_el['follow'] = geo_aper
                                            new_obj.tools[apid]['geometry'].append(deepcopy(new_el))

                                            # update progress
                                            pol_nr += 1
                                            disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 100]))
                                            if old_disp_number < disp_number <= 100:
                                                app_obj.proc_container.update_view_text(
                                                    ' %s: %d %d%%' % (_("Copy"), int(element), disp_number))
                                                old_disp_number = disp_number

                                # #####################################################################################
                                # ##########   Panelize the solid_geometry - always done  #############################
                                # #####################################################################################
                                try:
                                    for geo_el in panel_source_obj.solid_geometry:
                                        # graceful abort requested by the user
                                        if app_obj.abort_flag:
                                            raise grace

                                        trans_geo = translate_recursion(geo_el)
                                        new_obj.solid_geometry.append(trans_geo)
                                except TypeError:
                                    trans_geo = translate_recursion(panel_source_obj.solid_geometry)
                                    new_obj.solid_geometry.append(trans_geo)

                            currentx += lenghtx
                        currenty += lenghty

                    # #################################################################################################
                    # ###########################   Path Optimization   ###############################################
                    # #################################################################################################
                    if panel_source_obj.kind == 'geometry' and panel_source_obj.multigeo is True:
                        # I'm going to do this only here as a fix for panelizing cutouts
                        # I'm going to separate linestrings out of the solid geometry from other
                        # possible type of elements and apply unary_union on them to fuse them

                        if to_optimize is True:
                            app_obj.inform.emit('%s' % _("Optimizing the overlapping paths."))

                        for tool in new_obj.tools:
                            lines = []
                            other_geo = []
                            for geo in new_obj.tools[tool]['solid_geometry']:
                                if isinstance(geo, LineString):
                                    lines.append(geo)
                                elif isinstance(geo, MultiLineString):
                                    for line in geo.geoms:
                                        lines.append(line)
                                else:
                                    other_geo.append(geo)

                            if to_optimize is True:
                                for idx, line in enumerate(lines):
                                    for idx_s in range(idx+1, len(lines)):
                                        line_mod = lines[idx_s]
                                        # dist = line.distance(line_mod)
                                        # if dist < 1e-8:
                                        #     print("Disjoint %d: %d -> %s" % (idx, idx_s, str(dist)))
                                        #     print("Distance %f" % dist)
                                        res = snap(line_mod, line, tolerance=1e-7)
                                        if res and not res.is_empty:
                                            lines[idx_s] = res

                            fused_lines = linemerge(lines)
                            fused_lines = [unary_union(fused_lines)] if not fused_lines.is_empty else []

                            new_obj.tools[tool]['solid_geometry'] = fused_lines + other_geo

                        if to_optimize is True:
                            app_obj.inform.emit('%s' % _("Optimization complete."))

                    if panel_source_obj.kind == 'gerber':
                        new_obj.multigeo = True

                        default_data = {}
                        for opt_key, opt_val in self.app.options.items():
                            if opt_key.find('geometry' + "_") == 0:
                                oname = opt_key[len('geometry') + 1:]
                                default_data[oname] = self.app.options[opt_key]
                            elif opt_key.find('tools_') == 0:
                                default_data[opt_key] = self.app.options[opt_key]

                        new_obj.tools = {}
                        new_tid = 10
                        for apid in new_obj.tools:
                            new_tid += 1
                            new_sgeo = [g['solid'] for g in new_obj.tools[apid]['geometry'] if 'solid' in g]
                            new_sgeo = unary_union(new_sgeo)
                            new_obj.tools[new_tid] = {
                                'tooldia': self.app.options["tools_mill_tooldia"],
                                'offset': 'Path',
                                'offset_value': 0.0,
                                'type': 'Rough',
                                'tool_type': 'C1',
                                'data': deepcopy(default_data),
                                'solid_geometry': deepcopy(new_sgeo)
                            }
                        new_tid += 1
                        new_obj.tools[new_tid] = {
                            'tooldia': self.app.options["tools_mill_tooldia"],
                            'offset': 'Path',
                            'offset_value': 0.0,
                            'type': 'Rough',
                            'tool_type': 'C1',
                            'data': deepcopy(default_data),
                            'solid_geometry': deepcopy(new_obj.solid_geometry)
                        }
                        del new_obj.tools   # TODO what the hack is this? First we create and then immediately delete?

                    app_obj.inform.emit('%s' % _("Generating panel ... Adding the source code."))
                    new_obj.source_file = self.app.f_handlers.export_dxf(obj_name=self.outname, filename=None,
                                                                         local_use=new_obj, use_thread=False)

                    # new_obj.solid_geometry = unary_union(obj_fin.solid_geometry)
                    # app_obj.log.debug("Finished creating a unary_union for the panel.")
                    app_obj.proc_container.update_view_text('')

                def job_init_gerber(new_obj, app_obj):
                    currentx = 0.0
                    currenty = 0.0

                    def translate_recursion(geom):
                        if type(geom) == list:
                            geoms = []
                            for local_geom in geom:
                                res_geo = translate_recursion(local_geom)
                                try:
                                    geoms += res_geo
                                except TypeError:
                                    geoms.append(res_geo)
                            return geoms
                        else:
                            return translate(geom, xoff=currentx, yoff=currenty)

                    new_obj.solid_geometry = []

                    # create the initial structure on which to create the panel
                    if panel_source_obj.kind == 'geometry':
                        new_obj.multigeo = panel_source_obj.multigeo
                        new_obj.tools = copied_tools
                        if panel_source_obj.multigeo is True:
                            for tool in panel_source_obj.tools:
                                new_obj.tools[tool]['solid_geometry'] = []
                        else:
                            new_obj.solid_geometry = panel_source_obj.solid_geometry
                    elif panel_source_obj.kind == 'gerber':
                        new_obj.tools = copied_apertures
                        for ap in new_obj.tools:
                            new_obj.tools[ap]['geometry'] = []

                    # find the number of polygons in the source solid_geometry
                    geo_len = 0
                    if panel_source_obj.kind == 'geometry':
                        if panel_source_obj.multigeo is True:
                            for tool in panel_source_obj.tools:
                                try:
                                    work_geo = panel_source_obj.tools[tool]['solid_geometry']
                                    geo_len += len(
                                        work_geo.geoms if isinstance(work_geo, (MultiPolygon, MultiLineString)) else
                                        work_geo
                                    )
                                except TypeError:
                                    geo_len += 1
                        else:
                            try:
                                work_geo = panel_source_obj.solid_geometry
                                geo_len = len(
                                    work_geo.geoms if isinstance(work_geo, (MultiPolygon, MultiLineString)) else
                                    work_geo
                                )
                            except TypeError:
                                geo_len = 1
                    elif panel_source_obj.kind == 'gerber':
                        for ap in panel_source_obj.tools:
                            if 'geometry' in panel_source_obj.tools[ap]:
                                try:
                                    geo_len += len(panel_source_obj.tools[ap]['geometry'])
                                except TypeError:
                                    geo_len += 1

                    element = 0
                    for row in range(rows):
                        currentx = 0.0

                        for col in range(columns):
                            element += 1
                            old_disp_number = 0

                            # Will panelize a Geometry Object
                            if panel_source_obj.kind == 'geometry':
                                if panel_source_obj.multigeo is True:
                                    for tool in panel_source_obj.tools:
                                        # graceful abort requested by the user
                                        if app_obj.abort_flag:
                                            raise grace

                                        # calculate the number of polygons
                                        try:
                                            work_geo = panel_source_obj.tools[tool]['solid_geometry']
                                            geo_len = len(
                                                work_geo.geoms if isinstance(work_geo, (MultiPolygon, MultiLineString))
                                                else work_geo
                                            )
                                        except TypeError:
                                            geo_len = 1

                                        # panelization
                                        pol_nr = 0
                                        work_geo = panel_source_obj.tools[tool]['solid_geometry']
                                        i_wg = work_geo.geoms if isinstance(work_geo, (MultiPolygon, MultiLineString)) \
                                            else work_geo
                                        for geo_el in i_wg:
                                            trans_geo = translate_recursion(geo_el)
                                            if not trans_geo.is_empty:
                                                new_obj.tools[tool]['solid_geometry'].append(trans_geo)

                                            # update progress
                                            pol_nr += 1
                                            disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 100]))
                                            if old_disp_number < disp_number <= 100:
                                                app_obj.proc_container.update_view_text(
                                                    ' %s: %d %d%%' % (_("Copy"), int(element), disp_number))
                                                old_disp_number = disp_number

                                # #####################################################################################
                                # ##########   Panelize the solid_geometry - always done  #############################
                                # #####################################################################################
                                # graceful abort requested by the user
                                if app_obj.abort_flag:
                                    raise grace

                                # calculate the number of polygons
                                try:
                                    work_geo = panel_source_obj.solid_geometry
                                    geo_len = len(
                                        work_geo.geoms if isinstance(work_geo, (MultiPolygon, MultiLineString))
                                        else work_geo
                                    )
                                except TypeError:
                                    geo_len = 1

                                # panelization
                                pol_nr = 0
                                try:
                                    work_geo = panel_source_obj.solid_geometry
                                    i_wg = work_geo.geoms if isinstance(work_geo, (MultiPolygon, MultiLineString)) \
                                        else work_geo
                                    for geo_el in i_wg:
                                        if app_obj.abort_flag:
                                            # graceful abort requested by the user
                                            raise grace

                                        trans_geo = translate_recursion(geo_el)
                                        new_obj.solid_geometry.append(trans_geo)

                                        # update progress
                                        pol_nr += 1
                                        disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 100]))
                                        if old_disp_number < disp_number <= 100:
                                            app_obj.proc_container.update_view_text(
                                                ' %s: %d %d%%' % (_("Copy"), int(element), disp_number))
                                            old_disp_number = disp_number

                                except TypeError:
                                    trans_geo = translate_recursion(panel_source_obj.solid_geometry)
                                    new_obj.solid_geometry.append(trans_geo)
                            # Will panelize a Gerber Object
                            else:
                                # graceful abort requested by the user
                                if self.app.abort_flag:
                                    raise grace

                                for apid in panel_source_obj.tools:
                                    # graceful abort requested by the user
                                    if app_obj.abort_flag:
                                        raise grace

                                    if 'geometry' in panel_source_obj.tools[apid]:
                                        # calculate the number of polygons
                                        try:
                                            geo_len = len(panel_source_obj.tools[apid]['geometry'])
                                        except TypeError:
                                            geo_len = 1

                                        # panelization -> apertures
                                        pol_nr = 0
                                        for el in panel_source_obj.tools[apid]['geometry']:
                                            if app_obj.abort_flag:
                                                # graceful abort requested by the user
                                                raise grace

                                            new_el = {}
                                            if 'solid' in el:
                                                geo_aper = translate_recursion(el['solid'])
                                                new_el['solid'] = geo_aper
                                            if 'clear' in el:
                                                geo_aper = translate_recursion(el['clear'])
                                                new_el['clear'] = geo_aper
                                            if 'follow' in el:
                                                geo_aper = translate_recursion(el['follow'])
                                                new_el['follow'] = geo_aper
                                            new_obj.tools[apid]['geometry'].append(deepcopy(new_el))

                                            # update progress
                                            pol_nr += 1
                                            disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 100]))
                                            if old_disp_number < disp_number <= 100:
                                                app_obj.proc_container.update_view_text(
                                                    ' %s: %d %d%%' % (_("Copy"), int(element), disp_number))
                                                old_disp_number = disp_number

                                # #####################################################################################
                                # ##########   Panelize the solid_geometry - always done  #############################
                                # #####################################################################################
                                try:
                                    for geo_el in panel_source_obj.solid_geometry:
                                        # graceful abort requested by the user
                                        if app_obj.abort_flag:
                                            raise grace

                                        trans_geo = translate_recursion(geo_el)
                                        new_obj.solid_geometry.append(trans_geo)
                                except TypeError:
                                    trans_geo = translate_recursion(panel_source_obj.solid_geometry)
                                    new_obj.solid_geometry.append(trans_geo)

                            currentx += lenghtx
                        currenty += lenghty

                    if panel_source_obj.kind == 'geometry':
                        new_obj.multitool = False
                        new_obj.multigeo = True
                        new_obj.source_file = ''
                        new_obj.follow = False
                        new_obj.follow_geometry = []

                        if panel_source_obj.multigeo is True:
                            new_solid_list = []
                            for tool in new_obj.tools:
                                if 'solid_geometry' in new_obj.tools[tool]:
                                    for geo in new_obj.tools[tool]['solid_geometry']:
                                        try:
                                            geo = linemerge(geo)
                                        except Exception:
                                            pass

                                        try:
                                            geo = Polygon(geo)
                                            new_el = {
                                                'solid': geo,
                                                'follow': geo.exterior
                                            }
                                        except Exception:
                                            new_el = {
                                                'solid': geo,
                                                'follow': geo
                                            }
                                        new_solid_list.append(deepcopy(new_el))

                            new_obj.tools = {
                                0: {
                                    'type': 'REG',
                                    'size': 0.0,
                                    'geometry': deepcopy(new_solid_list)
                                }
                            }
                            all_geo = [g['solid'] for g in new_solid_list if 'solid' in g]
                            all_geo = unary_union(all_geo)
                            new_obj.solid_geometry = deepcopy(all_geo)
                            del new_obj.tools
                        else:
                            new_obj.tools = {
                                0: {
                                    'type': 'REG',
                                    'size': 0.0,
                                    'geometry': deepcopy(new_obj.solid_geometry)
                                }
                            }
                            new_obj.solid_geometry = deepcopy(new_obj.solid_geometry)
                            del new_obj.tools

                    app_obj.inform.emit('%s' % _("Generating panel ... Adding the source code."))

                    new_obj.source_file = self.app.f_handlers.export_gerber(obj_name=self.outname, filename=None,
                                                                            local_use=new_obj, use_thread=False)

                    # new_obj.solid_geometry = unary_union(new_obj.solid_geometry)
                    # app_obj.log.debug("Finished creating a unary_union for the panel.")
                    app_obj.proc_container.update_view_text('')

                self.app.inform.emit('%s: %d' % (_("Generating panel... Spawning copies"), (int(rows * columns))))
                if panel_source_obj.kind == 'excellon':
                    self.app.app_obj.new_object(
                        "excellon", self.outname, job_init_excellon, plot=True, autoselected=False)
                else:
                    if panel_type == 'geometry':
                        self.app.app_obj.new_object(
                            'geometry', self.outname, job_init_geometry, plot=True, autoselected=False)
                    if panel_type == 'gerber':
                        self.app.app_obj.new_object(
                            'gerber', self.outname, job_init_gerber, plot=True, autoselected=False)

        if self.constrain_flag is False:
            self.app.inform.emit('[success] %s' % _("Done."))
        else:
            self.constrain_flag = False
            self.app.inform.emit(_("{text} Too big for the constrain area. "
                                   "Final panel has {col} columns and {row} rows").format(
                text='[WARNING] ', col=columns, row=rows))

        def job_thread(app_obj):
            with self.app.proc_container.new('%s...' % _("Working")):
                try:
                    panelize_worker()
                    app_obj.inform.emit('[success] %s' % _("Panel created successfully."))
                except Exception as ee:
                    self.app.log.error(str(ee))
                    return

        self.app.collection.promise(self.outname)
        self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})

    def reset_fields(self):
        self.ui.object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.ui.box_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))


class PanelizeUI:

    pluginName = _("Panelization")

    def __init__(self, layout, app):
        self.app = app
        self.decimals = self.app.decimals
        self.layout = layout

        self.tools_frame = QtWidgets.QFrame()
        self.tools_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.tools_frame)
        self.tools_box = QtWidgets.QVBoxLayout()
        self.tools_box.setContentsMargins(0, 0, 0, 0)
        self.tools_frame.setLayout(self.tools_box)

        self.title_box = QtWidgets.QHBoxLayout()
        self.tools_box.addLayout(self.title_box)

        # ## Title
        title_label = FCLabel("%s" % self.pluginName, size=16, bold=True)
        self.title_box.addWidget(title_label)

        # App Level label
        self.level = QtWidgets.QToolButton()
        self.level.setToolTip(
            _(
                "Beginner Mode - many parameters are hidden.\n"
                "Advanced Mode - full control.\n"
                "Permanent change is done in 'Preferences' menu."
            )
        )
        self.level.setCheckable(True)
        self.title_box.addWidget(self.level)

        # #############################################################################################################
        # Source Object Frame
        # #############################################################################################################
        self.object_label = FCLabel('%s' % _("Source Object"), color='darkorange', bold=True)
        self.object_label.setToolTip(
            _("Specify the type of object to be panelized\n"
              "It can be of type: Gerber, Excellon or Geometry.\n"
              "The selection here decide the type of objects that will be\n"
              "in the Object combobox.")
        )
        self.tools_box.addWidget(self.object_label)

        obj_frame = FCFrame()
        self.tools_box.addWidget(obj_frame)

        # Grid Layout
        grid0 = GLay(v_spacing=5, h_spacing=3)
        obj_frame.setLayout(grid0)

        # Type of object to be panelized
        self.type_object_label = FCLabel('%s:' % _("Target"))

        self.type_obj_combo = FCComboBox()
        self.type_obj_combo.addItems([_("Gerber"), _("Excellon"), _("Geometry")])
        self.type_obj_combo.setItemIcon(0, QtGui.QIcon(self.app.resource_location + "/flatcam_icon16.png"))
        self.type_obj_combo.setItemIcon(1, QtGui.QIcon(self.app.resource_location + "/drill16.png"))
        self.type_obj_combo.setItemIcon(2, QtGui.QIcon(self.app.resource_location + "/geometry16.png"))

        grid0.addWidget(self.type_object_label, 2, 0)
        grid0.addWidget(self.type_obj_combo, 2, 1)

        # Object to be panelized
        self.object_combo = FCComboBox()
        self.object_combo.setModel(self.app.collection)
        self.object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.object_combo.is_last = False

        self.object_combo.setToolTip(
            _("Object to be panelized. This means that it will\n"
              "be duplicated in an array of rows and columns.")
        )

        grid0.addWidget(self.object_combo, 4, 0, 1, 2)

        # #############################################################################################################
        # Reference Object Frame
        # #############################################################################################################
        # Type of box Panel object
        self.box_label = FCLabel('%s' % _("Reference"), color='green', bold=True)
        self.box_label.setToolTip(
            _("Choose the reference for panelization:\n"
              "- Object = the bounding box of a different object\n"
              "- Bounding Box = the bounding box of the object to be panelized\n"
              "\n"
              "The reference is useful when doing panelization for more than one\n"
              "object. The spacings (really offsets) will be applied in reference\n"
              "to this reference object therefore maintaining the panelized\n"
              "objects in sync.")
        )
        self.tools_box.addWidget(self.box_label)

        pr_frame = FCFrame()
        self.tools_box.addWidget(pr_frame)

        # Grid Layout
        grid1 = GLay(v_spacing=5, h_spacing=3)
        pr_frame.setLayout(grid1)

        self.reference_radio = RadioSet([{'label': _('Object'), 'value': 'object'},
                                         {'label': _('Bounding Box'), 'value': 'bbox'}])
        grid1.addWidget(self.reference_radio, 0, 0, 1, 2)

        # Type of Box Object to be used as an envelope for panelization
        self.type_box_combo = FCComboBox()
        self.type_box_combo.addItems([_("Gerber"), _("Geometry")])

        # we get rid of item1 ("Excellon") as it is not suitable for use as a "box" for panelizing
        # self.type_box_combo.view().setRowHidden(1, True)
        self.type_box_combo.setItemIcon(0, QtGui.QIcon(self.app.resource_location + "/flatcam_icon16.png"))
        self.type_box_combo.setItemIcon(1, QtGui.QIcon(self.app.resource_location + "/geometry16.png"))

        self.type_box_combo_label = FCLabel('%s:' % _("Box Type"))
        self.type_box_combo_label.setToolTip(
            _("Specify the type of object to be used as an container for\n"
              "panelization. It can be: Gerber or Geometry type.\n"
              "The selection here decide the type of objects that will be\n"
              "in the Box Object combobox.")
        )
        grid1.addWidget(self.type_box_combo_label, 2, 0)
        grid1.addWidget(self.type_box_combo, 2, 1)

        # Box
        self.box_combo = FCComboBox()
        self.box_combo.setModel(self.app.collection)
        self.box_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        # self.box_combo.is_last = True

        self.box_combo.setToolTip(
            _("The actual object that is used as container for the\n "
              "selected object that is to be panelized.")
        )
        grid1.addWidget(self.box_combo, 4, 0, 1, 2)

        # #############################################################################################################
        # Panel Data Frame
        # #############################################################################################################
        panel_data_label = FCLabel('%s' % _("Panel Data"), color='red', bold=True)
        panel_data_label.setToolTip(
            _("This informations will shape the resulting panel.\n"
              "The number of rows and columns will set how many\n"
              "duplicates of the original geometry will be generated.\n"
              "\n"
              "The spacings will set the distance between any two\n"
              "elements of the panel array.")
        )
        self.tools_box.addWidget(panel_data_label)

        pd_frame = FCFrame()
        self.tools_box.addWidget(pd_frame)

        grid2 = GLay(v_spacing=5, h_spacing=3)
        pd_frame.setLayout(grid2)

        # Spacing Columns
        self.spacing_columns = FCDoubleSpinner(callback=self.confirmation_message)
        self.spacing_columns.set_range(0, 9999)
        self.spacing_columns.set_precision(4)

        self.spacing_columns_label = FCLabel('%s:' % _("Spacing cols"))
        self.spacing_columns_label.setToolTip(
            _("Spacing between columns.\n"
              "In current units.")
        )
        grid2.addWidget(self.spacing_columns_label, 0, 0)
        grid2.addWidget(self.spacing_columns, 0, 1)

        # Spacing Rows
        self.spacing_rows = FCDoubleSpinner(callback=self.confirmation_message)
        self.spacing_rows.set_range(0, 9999)
        self.spacing_rows.set_precision(4)

        self.spacing_rows_label = FCLabel('%s:' % _("Spacing rows"))
        self.spacing_rows_label.setToolTip(
            _("Spacing between rows.\n"
              "In current units.")
        )
        grid2.addWidget(self.spacing_rows_label, 2, 0)
        grid2.addWidget(self.spacing_rows, 2, 1)

        # Columns
        self.columns = FCSpinner(callback=self.confirmation_message_int)
        self.columns.set_range(0, 10000)

        self.columns_label = FCLabel('%s:' % _("Columns"))
        self.columns_label.setToolTip(
            _("Number of columns")
        )
        grid2.addWidget(self.columns_label, 4, 0)
        grid2.addWidget(self.columns, 4, 1)

        # Rows
        self.rows = FCSpinner(callback=self.confirmation_message_int)
        self.rows.set_range(0, 10000)

        self.rows_label = FCLabel('%s:' % _("Rows"))
        self.rows_label.setToolTip(
            _("Number of rows")
        )
        grid2.addWidget(self.rows_label, 6, 0)
        grid2.addWidget(self.rows, 6, 1)

        # #############################################################################################################
        # COMMON PARAMETERS Frame
        # #############################################################################################################
        self.param_label = FCLabel('%s' % _("Parameters"), color='blue', bold=True)
        self.param_label.setToolTip(_("Parameters that are common for all tools."))
        self.tools_box.addWidget(self.param_label)

        self.gp_frame = FCFrame()
        self.tools_box.addWidget(self.gp_frame)

        grid3 = GLay(v_spacing=5, h_spacing=3)
        self.gp_frame.setLayout(grid3)

        # Type of resulting Panel object
        self.panel_type_radio = RadioSet([{'label': _('Gerber'), 'value': 'gerber'},
                                          {'label': _('Geo'), 'value': 'geometry'}])
        self.panel_type_label = FCLabel('%s:' % _("Panel Type"), bold=True)
        self.panel_type_label.setToolTip(
            _("Choose the type of object for the panel object:\n"
              "- Gerber\n"
              "- Geometry")
        )
        grid3.addWidget(self.panel_type_label, 0, 0)
        grid3.addWidget(self.panel_type_radio, 0, 1)

        # Path optimization
        self.optimization_cb = FCCheckBox('%s' % _("Path Optimization"))
        self.optimization_cb.setToolTip(
            _("Active only for Geometry panel type.\n"
              "When checked the application will find\n"
              "any two overlapping Line elements in the panel\n"
              "and will remove the overlapping parts, keeping only one of them.")
        )
        grid3.addWidget(self.optimization_cb, 2, 0, 1, 2)

        # Constrains
        self.constrain_cb = FCCheckBox('%s:' % _("Constrain panel within"))
        self.constrain_cb.setToolTip(
            _("Area define by DX and DY within to constrain the panel.\n"
              "DX and DY values are in current units.\n"
              "Regardless of how many columns and rows are desired,\n"
              "the final panel will have as many columns and rows as\n"
              "they fit completely within selected area.")
        )
        grid3.addWidget(self.constrain_cb, 4, 0, 1, 2)

        self.x_width_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.x_width_entry.set_precision(self.decimals)
        self.x_width_entry.set_range(0.0000, 10000.0000)

        self.x_width_lbl = FCLabel('%s:' % _("Width (DX)"))
        self.x_width_lbl.setToolTip(
            _("The width (DX) within which the panel must fit.\n"
              "In current units.")
        )
        grid3.addWidget(self.x_width_lbl, 6, 0)
        grid3.addWidget(self.x_width_entry, 6, 1)

        self.y_height_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.y_height_entry.set_range(0, 10000)
        self.y_height_entry.set_precision(self.decimals)

        self.y_height_lbl = FCLabel('%s:' % _("Height (DY)"))
        self.y_height_lbl.setToolTip(
            _("The height (DY)within which the panel must fit.\n"
              "In current units.")
        )
        grid3.addWidget(self.y_height_lbl, 8, 0)
        grid3.addWidget(self.y_height_entry, 8, 1)

        self.constrain_sel = OptionalInputSection(
            self.constrain_cb, [self.x_width_lbl, self.x_width_entry, self.y_height_lbl, self.y_height_entry])

        self.separator_line = QtWidgets.QFrame()
        self.separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        grid3.addWidget(self.separator_line, 10, 0, 1, 2)

        GLay.set_common_column_size([grid0, grid1, grid2, grid3], 0)

        # #############################################################################################################
        # Generate Panel Button
        # #############################################################################################################
        self.panelize_object_button = FCButton(_("Panelize Object"), bold=True)
        self.panelize_object_button.setIcon(QtGui.QIcon(self.app.resource_location + '/panelize16.png'))
        self.panelize_object_button.setToolTip(
            _("Panelize the specified object around the specified box.\n"
              "In other words it creates multiple copies of the source object,\n"
              "arranged in a 2D array of rows and columns.")
        )
        self.tools_box.addWidget(self.panelize_object_button)

        self.layout.addStretch(1)

        # ## Reset Tool
        self.reset_button = FCButton(_("Reset Tool"), bold=True)
        self.reset_button.setIcon(QtGui.QIcon(self.app.resource_location + '/reset32.png'))
        self.reset_button.setToolTip(
            _("Will reset the tool parameters.")
        )
        self.layout.addWidget(self.reset_button)

        # #################################### FINSIHED GUI ###########################
        # #############################################################################
        self.panel_type_radio.activated_custom.connect(self.on_panel_type)

    def on_panel_type(self, val):
        if val == 'geometry':
            self.optimization_cb.setDisabled(False)
        else:
            self.optimization_cb.setDisabled(True)

    def confirmation_message(self, accepted, minval, maxval):
        if accepted is False:
            self.app.inform[str, bool].emit('[WARNING_NOTCL] %s: [%.*f, %.*f]' % (_("Edited value is out of range"),
                                                                                  self.decimals,
                                                                                  minval,
                                                                                  self.decimals,
                                                                                  maxval), False)
        else:
            self.app.inform[str, bool].emit('[success] %s' % _("Edited value is within limits."), False)

    def confirmation_message_int(self, accepted, minval, maxval):
        if accepted is False:
            self.app.inform[str, bool].emit('[WARNING_NOTCL] %s: [%d, %d]' %
                                            (_("Edited value is out of range"), minval, maxval), False)
        else:
            self.app.inform[str, bool].emit('[success] %s' % _("Edited value is within limits."), False)
