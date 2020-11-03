# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 1/24/2020                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtCore, QtWidgets, QtGui

from appTool import AppTool
from appGUI.GUIElements import RadioSet, FCDoubleSpinner, FCCheckBox, FCComboBox, FCTable

from copy import deepcopy
import logging
from shapely.geometry import MultiPolygon, Point
from shapely.ops import unary_union

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class ToolPunchGerber(AppTool):

    def __init__(self, app):
        AppTool.__init__(self, app)

        self.app = app
        self.decimals = self.app.decimals
        self.units = self.app.defaults['units']

        # store here the old object name
        self.old_name = ''

        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = PunchUI(layout=self.layout, app=self.app)
        self.toolName = self.ui.toolName

        # ## Signals
        self.ui.method_punch.activated_custom.connect(self.on_method)
        self.ui.reset_button.clicked.connect(self.set_tool_ui)
        self.ui.punch_object_button.clicked.connect(self.on_generate_object)

        self.ui.gerber_object_combo.currentIndexChanged.connect(self.build_tool_ui)

        self.ui.circular_cb.stateChanged.connect(
            lambda state:
                self.ui.circular_ring_entry.setDisabled(False) if state else
                self.ui.circular_ring_entry.setDisabled(True)
        )

        self.ui.oblong_cb.stateChanged.connect(
            lambda state:
            self.ui.oblong_ring_entry.setDisabled(False) if state else self.ui.oblong_ring_entry.setDisabled(True)
        )

        self.ui.square_cb.stateChanged.connect(
            lambda state:
            self.ui.square_ring_entry.setDisabled(False) if state else self.ui.square_ring_entry.setDisabled(True)
        )

        self.ui.rectangular_cb.stateChanged.connect(
            lambda state:
            self.ui.rectangular_ring_entry.setDisabled(False) if state else
            self.ui.rectangular_ring_entry.setDisabled(True)
        )

        self.ui.other_cb.stateChanged.connect(
            lambda state:
            self.ui.other_ring_entry.setDisabled(False) if state else self.ui.other_ring_entry.setDisabled(True)
        )

        self.ui.circular_cb.stateChanged.connect(self.build_tool_ui)
        self.ui.oblong_cb.stateChanged.connect(self.build_tool_ui)
        self.ui.square_cb.stateChanged.connect(self.build_tool_ui)
        self.ui.rectangular_cb.stateChanged.connect(self.build_tool_ui)
        self.ui.other_cb.stateChanged.connect(self.build_tool_ui)

        self.ui.gerber_object_combo.currentIndexChanged.connect(self.on_object_combo_changed)

    def on_object_combo_changed(self):
        # get the Gerber file who is the source of the punched Gerber
        selection_index = self.ui.gerber_object_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.ui.gerber_object_combo.rootModelIndex())

        try:
            grb_obj = model_index.internalPointer().obj
        except Exception:
            return

        if self.old_name != '':
            old_obj = self.app.collection.get_by_name(self.old_name)
            if old_obj:
                old_obj.clear_plot_apertures()
                old_obj.mark_shapes.enabled = False

        # enable mark shapes
        if grb_obj:
            grb_obj.mark_shapes.enabled = True

            # create storage for shapes
            for ap_code in grb_obj.apertures:
                grb_obj.mark_shapes_storage[ap_code] = []

            self.old_name = grb_obj.options['name']

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolPunchGerber()")

        if toggle:
            # if the splitter is hidden, display it, else hide it but only if the current widget is the same
            if self.app.ui.splitter.sizes()[0] == 0:
                self.app.ui.splitter.setSizes([1, 1])
            else:
                try:
                    if self.app.ui.tool_scroll_area.widget().objectName() == self.toolName:
                        # if tab is populated with the tool but it does not have the focus, focus on it
                        if not self.app.ui.notebook.currentWidget() is self.app.ui.tool_tab:
                            # focus on Tool Tab
                            self.app.ui.notebook.setCurrentWidget(self.app.ui.tool_tab)
                        else:
                            self.app.ui.splitter.setSizes([0, 1])
                except AttributeError:
                    pass
        else:
            if self.app.ui.splitter.sizes()[0] == 0:
                self.app.ui.splitter.setSizes([1, 1])

        AppTool.run(self)

        self.set_tool_ui()
        self.build_tool_ui()

        self.app.ui.notebook.setTabText(2, _("Punch Tool"))

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Alt+H', **kwargs)

    def set_tool_ui(self):
        self.reset_fields()

        self.ui_disconnect()
        self.ui_connect()
        self.ui.method_punch.set_value(self.app.defaults["tools_punch_hole_type"])
        self.ui.select_all_cb.set_value(False)

        self.ui.dia_entry.set_value(float(self.app.defaults["tools_punch_hole_fixed_dia"]))

        self.ui.circular_ring_entry.set_value(float(self.app.defaults["tools_punch_circular_ring"]))
        self.ui.oblong_ring_entry.set_value(float(self.app.defaults["tools_punch_oblong_ring"]))
        self.ui.square_ring_entry.set_value(float(self.app.defaults["tools_punch_square_ring"]))
        self.ui.rectangular_ring_entry.set_value(float(self.app.defaults["tools_punch_rectangular_ring"]))
        self.ui.other_ring_entry.set_value(float(self.app.defaults["tools_punch_others_ring"]))

        self.ui.circular_cb.set_value(self.app.defaults["tools_punch_circular"])
        self.ui.oblong_cb.set_value(self.app.defaults["tools_punch_oblong"])
        self.ui.square_cb.set_value(self.app.defaults["tools_punch_square"])
        self.ui.rectangular_cb.set_value(self.app.defaults["tools_punch_rectangular"])
        self.ui.other_cb.set_value(self.app.defaults["tools_punch_others"])

        self.ui.factor_entry.set_value(float(self.app.defaults["tools_punch_hole_prop_factor"]))

    def build_tool_ui(self):
        self.ui_disconnect()

        # reset table
        # self.ui.apertures_table.clear()   # this deletes the headers/tooltips too ... not nice!
        self.ui.apertures_table.setRowCount(0)

        # get the Gerber file who is the source of the punched Gerber
        selection_index = self.ui.gerber_object_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.ui.gerber_object_combo.rootModelIndex())
        obj = None

        try:
            obj = model_index.internalPointer().obj
            sort = [int(k) for k in obj.apertures.keys()]
            sorted_apertures = sorted(sort)
        except Exception:
            # no object loaded
            sorted_apertures = []

        # n = len(sorted_apertures)
        # calculate how many rows to add
        n = 0
        for ap_code in sorted_apertures:
            ap_code = str(ap_code)
            ap_type = obj.apertures[ap_code]['type']

            if ap_type == 'C' and self.ui.circular_cb.get_value() is True:
                n += 1
            if ap_type == 'R':
                if self.ui.square_cb.get_value() is True:
                    n += 1
                elif self.ui.rectangular_cb.get_value() is True:
                    n += 1
            if ap_type == 'O' and self.ui.oblong_cb.get_value() is True:
                n += 1
            if ap_type not in ['C', 'R', 'O'] and self.ui.other_cb.get_value() is True:
                n += 1

        self.ui.apertures_table.setRowCount(n)

        row = 0
        for ap_code in sorted_apertures:
            ap_code = str(ap_code)

            ap_type = obj.apertures[ap_code]['type']
            if ap_type == 'C':
                if self.ui.circular_cb.get_value() is False:
                    continue
            elif ap_type == 'R':
                if self.ui.square_cb.get_value() is True:
                    pass
                elif self.ui.rectangular_cb.get_value() is True:
                    pass
                else:
                    continue
            elif ap_type == 'O':
                if self.ui.oblong_cb.get_value() is False:
                    continue
            elif self.ui.other_cb.get_value() is True:
                pass
            else:
                continue

            # Aperture CODE
            ap_code_item = QtWidgets.QTableWidgetItem(ap_code)
            ap_code_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

            # Aperture TYPE
            ap_type_item = QtWidgets.QTableWidgetItem(str(ap_type))
            ap_type_item.setFlags(QtCore.Qt.ItemIsEnabled)

            # Aperture SIZE
            try:
                if obj.apertures[ap_code]['size'] is not None:
                    size_val = self.app.dec_format(float(obj.apertures[ap_code]['size']), self.decimals)
                    ap_size_item = QtWidgets.QTableWidgetItem(str(size_val))
                else:
                    ap_size_item = QtWidgets.QTableWidgetItem('')
            except KeyError:
                ap_size_item = QtWidgets.QTableWidgetItem('')
            ap_size_item.setFlags(QtCore.Qt.ItemIsEnabled)

            # Aperture MARK Item
            mark_item = FCCheckBox()
            mark_item.setLayoutDirection(QtCore.Qt.RightToLeft)
            # Empty PLOT ITEM
            empty_plot_item = QtWidgets.QTableWidgetItem('')
            empty_plot_item.setFlags(~QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            empty_plot_item.setFlags(QtCore.Qt.ItemIsEnabled)

            self.ui.apertures_table.setItem(row, 0, ap_code_item)  # Aperture Code
            self.ui.apertures_table.setItem(row, 1, ap_type_item)  # Aperture Type
            self.ui.apertures_table.setItem(row, 2, ap_size_item)  # Aperture Dimensions
            self.ui.apertures_table.setItem(row, 3, empty_plot_item)
            self.ui.apertures_table.setCellWidget(row, 3, mark_item)
            # increment row
            row += 1

        self.ui.apertures_table.selectColumn(0)
        self.ui.apertures_table.resizeColumnsToContents()
        self.ui.apertures_table.resizeRowsToContents()

        vertical_header = self.ui.apertures_table.verticalHeader()
        vertical_header.hide()
        # self.ui.apertures_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        horizontal_header = self.ui.apertures_table.horizontalHeader()
        horizontal_header.setMinimumSectionSize(10)
        horizontal_header.setDefaultSectionSize(70)
        horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        horizontal_header.setSectionResizeMode(3, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(3, 17)
        self.ui.apertures_table.setColumnWidth(3, 17)

        self.ui.apertures_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.ui.apertures_table.setSortingEnabled(False)
        # self.ui.apertures_table.setMinimumHeight(self.ui.apertures_table.getHeight())
        # self.ui.apertures_table.setMaximumHeight(self.ui.apertures_table.getHeight())

        self.ui_connect()

    def on_select_all(self, state):
        self.ui_disconnect()
        if state:
            self.ui.circular_cb.setChecked(True)
            self.ui.oblong_cb.setChecked(True)
            self.ui.square_cb.setChecked(True)
            self.ui.rectangular_cb.setChecked(True)
            self.ui.other_cb.setChecked(True)
        else:
            self.ui.circular_cb.setChecked(False)
            self.ui.oblong_cb.setChecked(False)
            self.ui.square_cb.setChecked(False)
            self.ui.rectangular_cb.setChecked(False)
            self.ui.other_cb.setChecked(False)

            # get the Gerber file who is the source of the punched Gerber
            selection_index = self.ui.gerber_object_combo.currentIndex()
            model_index = self.app.collection.index(selection_index, 0, self.ui.gerber_object_combo.rootModelIndex())

            try:
                grb_obj = model_index.internalPointer().obj
            except Exception:
                return

            grb_obj.clear_plot_apertures()

        self.ui_connect()

    def on_method(self, val):
        self.ui.exc_label.hide()
        self.ui.exc_combo.hide()
        self.ui.fixed_label.hide()
        self.ui.dia_label.hide()
        self.ui.dia_entry.hide()
        self.ui.ring_frame.hide()
        self.ui.prop_label.hide()
        self.ui.factor_label.hide()
        self.ui.factor_entry.hide()

        if val == 'exc':
            self.ui.exc_label.show()
            self.ui.exc_combo.show()
        elif val == 'fixed':
            self.ui.fixed_label.show()
            self.ui.dia_label.show()
            self.ui.dia_entry.show()
        elif val == 'ring':
            self.ui.ring_frame.show()
        elif val == 'prop':
            self.ui.prop_label.show()
            self.ui.factor_label.show()
            self.ui.factor_entry.show()

    def ui_connect(self):
        self.ui.select_all_cb.stateChanged.connect(self.on_select_all)

        # Mark Checkboxes
        for row in range(self.ui.apertures_table.rowCount()):
            try:
                self.ui.apertures_table.cellWidget(row, 3).clicked.disconnect()
            except (TypeError, AttributeError):
                pass
            self.ui.apertures_table.cellWidget(row, 3).clicked.connect(self.on_mark_cb_click_table)

    def ui_disconnect(self):
        try:
            self.ui.select_all_cb.stateChanged.disconnect()
        except (AttributeError, TypeError):
            pass

        # Mark Checkboxes
        for row in range(self.ui.apertures_table.rowCount()):
            try:
                self.ui.apertures_table.cellWidget(row, 3).clicked.disconnect()
            except (TypeError, AttributeError):
                pass

    def on_generate_object(self):

        # get the Gerber file who is the source of the punched Gerber
        selection_index = self.ui.gerber_object_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.ui.gerber_object_combo.rootModelIndex())

        try:
            grb_obj = model_index.internalPointer().obj
        except Exception:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Gerber object loaded ..."))
            return

        name = grb_obj.options['name'].rpartition('.')[0]
        outname = name + "_punched"

        punch_method = self.ui.method_punch.get_value()
        if punch_method == 'exc':
            self.on_excellon_method(grb_obj, outname)
        elif punch_method == 'fixed':
            self.on_fixed_method(grb_obj, outname)
        elif punch_method == 'ring':
            self.on_ring_method(grb_obj, outname)
        elif punch_method == 'prop':
            self.on_proportional_method(grb_obj, outname)

    def on_excellon_method(self, grb_obj, outname):
        # get the Excellon file whose geometry will create the punch holes
        selection_index = self.ui.exc_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.ui.exc_combo.rootModelIndex())

        try:
            exc_obj = model_index.internalPointer().obj
        except Exception:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Excellon object loaded ..."))
            return

        new_options = {}
        for opt in grb_obj.options:
            new_options[opt] = deepcopy(grb_obj.options[opt])

        # selected codes in thre apertures UI table
        sel_apid = []
        for it in self.ui.apertures_table.selectedItems():
            sel_apid.append(it.text())

        # this is the punching geometry
        exc_solid_geometry = MultiPolygon(exc_obj.solid_geometry)

        # this is the target geometry
        # if isinstance(grb_obj.solid_geometry, list):
        #     grb_solid_geometry = MultiPolygon(grb_obj.solid_geometry)
        # else:
        #     grb_solid_geometry = grb_obj.solid_geometry
        grb_solid_geometry = []
        target_geometry = []
        for apid in grb_obj.apertures:
            if 'geometry' in grb_obj.apertures[apid]:
                for el_geo in grb_obj.apertures[apid]['geometry']:
                    if 'solid' in el_geo:
                        if apid in sel_apid:
                            target_geometry.append(el_geo['solid'])
                        else:
                            grb_solid_geometry.append(el_geo['solid'])

        target_geometry = MultiPolygon(target_geometry).buffer(0)

        # create the punched Gerber solid_geometry
        punched_target_geometry = target_geometry.difference(exc_solid_geometry)

        # add together the punched geometry and the not affected geometry
        punched_solid_geometry = []
        try:
            for geo in punched_target_geometry.geoms:
                punched_solid_geometry.append(geo)
        except AttributeError:
            punched_solid_geometry.append(punched_target_geometry)
        for geo in grb_solid_geometry:
            punched_solid_geometry.append(geo)
        punched_solid_geometry = unary_union(punched_solid_geometry)

        # update the gerber apertures to include the clear geometry so it can be exported successfully
        new_apertures = deepcopy(grb_obj.apertures)
        new_apertures_items = new_apertures.items()

        # find maximum aperture id
        new_apid = max([int(x) for x, __ in new_apertures_items])

        # store here the clear geometry, the key is the drill size
        holes_apertures = {}

        for apid, val in new_apertures_items:
            if apid in sel_apid:
                for elem in val['geometry']:
                    # make it work only for Gerber Flashes who are Points in 'follow'
                    if 'solid' in elem and isinstance(elem['follow'], Point):
                        for tool in exc_obj.tools:
                            clear_apid_size = exc_obj.tools[tool]['tooldia']

                            if 'drills' in exc_obj.tools[tool]:
                                for drill_pt in exc_obj.tools[tool]['drills']:
                                    # since there may be drills that do not drill into a pad we test only for
                                    # drills in a pad
                                    if drill_pt.within(elem['solid']):
                                        geo_elem = {'clear': drill_pt}

                                        if clear_apid_size not in holes_apertures:
                                            holes_apertures[clear_apid_size] = {
                                                'type': 'C',
                                                'size': clear_apid_size,
                                                'geometry': []
                                            }

                                        holes_apertures[clear_apid_size]['geometry'].append(deepcopy(geo_elem))

        # add the clear geometry to new apertures; it's easier than to test if there are apertures with the same
        # size and add there the clear geometry
        for hole_size, ap_val in holes_apertures.items():
            new_apid += 1
            new_apertures[str(new_apid)] = deepcopy(ap_val)

        def init_func(new_obj, app_obj):
            new_obj.options.update(new_options)
            new_obj.options['name'] = outname
            new_obj.fill_color = deepcopy(grb_obj.fill_color)
            new_obj.outline_color = deepcopy(grb_obj.outline_color)

            new_obj.apertures = deepcopy(new_apertures)

            new_obj.solid_geometry = deepcopy(punched_solid_geometry)
            new_obj.source_file = app_obj.f_handlers.export_gerber(obj_name=outname, filename=None,
                                                                   local_use=new_obj, use_thread=False)

        self.app.app_obj.new_object('gerber', outname, init_func)

    def on_fixed_method(self, grb_obj, outname):
        punch_size = float(self.ui.dia_entry.get_value())
        if punch_size == 0.0:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("The value of the fixed diameter is 0.0. Aborting."))
            return 'fail'

        fail_msg = _("Failed. Punch hole size is bigger than"
                     " some of the apertures in the Gerber object.")

        new_options = {}
        for opt in grb_obj.options:
            new_options[opt] = deepcopy(grb_obj.options[opt])

        # selected codes in thre apertures UI table
        sel_apid = []
        for it in self.ui.apertures_table.selectedItems():
            sel_apid.append(it.text())

        punching_geo = []
        for apid in grb_obj.apertures:
            if apid in sel_apid:
                if grb_obj.apertures[apid]['type'] == 'C' and self.ui.circular_cb.get_value():
                    for elem in grb_obj.apertures[apid]['geometry']:
                        if 'follow' in elem:
                            if isinstance(elem['follow'], Point):
                                if punch_size >= float(grb_obj.apertures[apid]['size']):
                                    self.app.inform.emit('[ERROR_NOTCL] %s' % fail_msg)
                                    return 'fail'
                                punching_geo.append(elem['follow'].buffer(punch_size / 2))
                elif grb_obj.apertures[apid]['type'] == 'R':

                    if round(float(grb_obj.apertures[apid]['width']), self.decimals) == \
                            round(float(grb_obj.apertures[apid]['height']), self.decimals) and \
                            self.ui.square_cb.get_value():
                        for elem in grb_obj.apertures[apid]['geometry']:
                            if 'follow' in elem:
                                if isinstance(elem['follow'], Point):
                                    if punch_size >= float(grb_obj.apertures[apid]['width']) or \
                                            punch_size >= float(grb_obj.apertures[apid]['height']):
                                        self.app.inform.emit('[ERROR_NOTCL] %s' % fail_msg)
                                        return 'fail'
                                    punching_geo.append(elem['follow'].buffer(punch_size / 2))
                    elif round(float(grb_obj.apertures[apid]['width']), self.decimals) != \
                            round(float(grb_obj.apertures[apid]['height']), self.decimals) and \
                            self.ui.rectangular_cb.get_value():
                        for elem in grb_obj.apertures[apid]['geometry']:
                            if 'follow' in elem:
                                if isinstance(elem['follow'], Point):
                                    if punch_size >= float(grb_obj.apertures[apid]['width']) or \
                                            punch_size >= float(grb_obj.apertures[apid]['height']):
                                        self.app.inform.emit('[ERROR_NOTCL] %s' % fail_msg)
                                        return 'fail'
                                    punching_geo.append(elem['follow'].buffer(punch_size / 2))
                elif grb_obj.apertures[apid]['type'] == 'O' and self.ui.oblong_cb.get_value():
                    for elem in grb_obj.apertures[apid]['geometry']:
                        if 'follow' in elem:
                            if isinstance(elem['follow'], Point):
                                if punch_size >= float(grb_obj.apertures[apid]['size']):
                                    self.app.inform.emit('[ERROR_NOTCL] %s' % fail_msg)
                                    return 'fail'
                                punching_geo.append(elem['follow'].buffer(punch_size / 2))
                elif grb_obj.apertures[apid]['type'] not in ['C', 'R', 'O'] and self.ui.other_cb.get_value():
                    for elem in grb_obj.apertures[apid]['geometry']:
                        if 'follow' in elem:
                            if isinstance(elem['follow'], Point):
                                if punch_size >= float(grb_obj.apertures[apid]['size']):
                                    self.app.inform.emit('[ERROR_NOTCL] %s' % fail_msg)
                                    return 'fail'
                                punching_geo.append(elem['follow'].buffer(punch_size / 2))

        punching_geo = MultiPolygon(punching_geo)
        if isinstance(grb_obj.solid_geometry, list):
            temp_solid_geometry = MultiPolygon(grb_obj.solid_geometry)
        else:
            temp_solid_geometry = grb_obj.solid_geometry
        punched_solid_geometry = temp_solid_geometry.difference(punching_geo)

        if punched_solid_geometry == temp_solid_geometry:
            msg = '[WARNING_NOTCL] %s' % \
                  _("Failed. The new object geometry is the same as the one in the source object geometry...")
            self.app.inform.emit(msg)
            return 'fail'

        # update the gerber apertures to include the clear geometry so it can be exported successfully
        new_apertures = deepcopy(grb_obj.apertures)
        new_apertures_items = new_apertures.items()

        # find maximum aperture id
        new_apid = max([int(x) for x, __ in new_apertures_items])

        # store here the clear geometry, the key is the drill size
        holes_apertures = {}

        for apid, val in new_apertures_items:
            for elem in val['geometry']:
                # make it work only for Gerber Flashes who are Points in 'follow'
                if 'solid' in elem and isinstance(elem['follow'], Point):
                    for geo in punching_geo:
                        clear_apid_size = punch_size

                        # since there may be drills that do not drill into a pad we test only for drills in a pad
                        if geo.within(elem['solid']):
                            geo_elem = {'clear': geo.centroid}

                            if clear_apid_size not in holes_apertures:
                                holes_apertures[clear_apid_size] = {
                                    'type': 'C',
                                    'size': clear_apid_size,
                                    'geometry': []
                                }

                            holes_apertures[clear_apid_size]['geometry'].append(deepcopy(geo_elem))

        # add the clear geometry to new apertures; it's easier than to test if there are apertures with the same
        # size and add there the clear geometry
        for hole_size, ap_val in holes_apertures.items():
            new_apid += 1
            new_apertures[str(new_apid)] = deepcopy(ap_val)

        def init_func(new_obj, app_obj):
            new_obj.options.update(new_options)
            new_obj.options['name'] = outname
            new_obj.fill_color = deepcopy(grb_obj.fill_color)
            new_obj.outline_color = deepcopy(grb_obj.outline_color)

            new_obj.apertures = deepcopy(new_apertures)

            new_obj.solid_geometry = deepcopy(punched_solid_geometry)
            new_obj.source_file = app_obj.f_handlers.export_gerber(obj_name=outname, filename=None,
                                                                   local_use=new_obj, use_thread=False)

        self.app.app_obj.new_object('gerber', outname, init_func)

    def on_ring_method(self, grb_obj, outname):
        circ_r_val = self.ui.circular_ring_entry.get_value()
        oblong_r_val = self.ui.oblong_ring_entry.get_value()
        square_r_val = self.ui.square_ring_entry.get_value()
        rect_r_val = self.ui.rectangular_ring_entry.get_value()
        other_r_val = self.ui.other_ring_entry.get_value()
        dia = None

        new_options = {}
        for opt in grb_obj.options:
            new_options[opt] = deepcopy(grb_obj.options[opt])

        if isinstance(grb_obj.solid_geometry, list):
            temp_solid_geometry = MultiPolygon(grb_obj.solid_geometry)
        else:
            temp_solid_geometry = grb_obj.solid_geometry

        punched_solid_geometry = temp_solid_geometry

        new_apertures = deepcopy(grb_obj.apertures)
        new_apertures_items = new_apertures.items()

        # find maximum aperture id
        new_apid = max([int(x) for x, __ in new_apertures_items])

        # selected codes in the apertures UI table
        sel_apid = []
        for it in self.ui.apertures_table.selectedItems():
            sel_apid.append(it.text())

        # store here the clear geometry, the key is the new aperture size
        holes_apertures = {}

        for apid, apid_value in grb_obj.apertures.items():
            ap_type = apid_value['type']
            punching_geo = []

            if apid in sel_apid:
                if ap_type == 'C' and self.ui.circular_cb.get_value():
                    dia = float(apid_value['size']) - (2 * circ_r_val)
                    for elem in apid_value['geometry']:
                        if 'follow' in elem and isinstance(elem['follow'], Point):
                            punching_geo.append(elem['follow'].buffer(dia / 2))
                elif ap_type == 'O' and self.ui.oblong_cb.get_value():
                    width = float(apid_value['width'])
                    height = float(apid_value['height'])

                    if width > height:
                        dia = float(apid_value['height']) - (2 * oblong_r_val)
                    else:
                        dia = float(apid_value['width']) - (2 * oblong_r_val)

                    for elem in grb_obj.apertures[apid]['geometry']:
                        if 'follow' in elem:
                            if isinstance(elem['follow'], Point):
                                punching_geo.append(elem['follow'].buffer(dia / 2))
                elif ap_type == 'R':
                    width = float(apid_value['width'])
                    height = float(apid_value['height'])

                    # if the height == width (float numbers so the reason for the following)
                    if round(width, self.decimals) == round(height, self.decimals):
                        if self.ui.square_cb.get_value():
                            dia = float(apid_value['height']) - (2 * square_r_val)

                            for elem in grb_obj.apertures[apid]['geometry']:
                                if 'follow' in elem:
                                    if isinstance(elem['follow'], Point):
                                        punching_geo.append(elem['follow'].buffer(dia / 2))
                    elif self.ui.rectangular_cb.get_value():
                        if width > height:
                            dia = float(apid_value['height']) - (2 * rect_r_val)
                        else:
                            dia = float(apid_value['width']) - (2 * rect_r_val)

                        for elem in grb_obj.apertures[apid]['geometry']:
                            if 'follow' in elem:
                                if isinstance(elem['follow'], Point):
                                    punching_geo.append(elem['follow'].buffer(dia / 2))
                elif self.ui.other_cb.get_value():
                    try:
                        dia = float(apid_value['size']) - (2 * other_r_val)
                    except KeyError:
                        if ap_type == 'AM':
                            pol = apid_value['geometry'][0]['solid']
                            x0, y0, x1, y1 = pol.bounds
                            dx = x1 - x0
                            dy = y1 - y0
                            if dx <= dy:
                                dia = dx - (2 * other_r_val)
                            else:
                                dia = dy - (2 * other_r_val)

                    for elem in grb_obj.apertures[apid]['geometry']:
                        if 'follow' in elem:
                            if isinstance(elem['follow'], Point):
                                punching_geo.append(elem['follow'].buffer(dia / 2))

            # if dia is None then none of the above applied so we skip the following
            if dia is None:
                continue

            punching_geo = MultiPolygon(punching_geo)

            if punching_geo is None or punching_geo.is_empty:
                continue

            punched_solid_geometry = punched_solid_geometry.difference(punching_geo)

            # update the gerber apertures to include the clear geometry so it can be exported successfully
            for elem in apid_value['geometry']:
                # make it work only for Gerber Flashes who are Points in 'follow'
                if 'solid' in elem and isinstance(elem['follow'], Point):
                    clear_apid_size = dia
                    for geo in punching_geo:

                        # since there may be drills that do not drill into a pad we test only for geos in a pad
                        if geo.within(elem['solid']):
                            geo_elem = {'clear': geo.centroid}

                            if clear_apid_size not in holes_apertures:
                                holes_apertures[clear_apid_size] = {
                                    'type': 'C',
                                    'size': clear_apid_size,
                                    'geometry': []
                                }

                            holes_apertures[clear_apid_size]['geometry'].append(deepcopy(geo_elem))

        # add the clear geometry to new apertures; it's easier than to test if there are apertures with the same
        # size and add there the clear geometry
        for hole_size, ap_val in holes_apertures.items():
            new_apid += 1
            new_apertures[str(new_apid)] = deepcopy(ap_val)

        def init_func(new_obj, app_obj):
            new_obj.options.update(new_options)
            new_obj.options['name'] = outname
            new_obj.fill_color = deepcopy(grb_obj.fill_color)
            new_obj.outline_color = deepcopy(grb_obj.outline_color)

            new_obj.apertures = deepcopy(new_apertures)

            new_obj.solid_geometry = deepcopy(punched_solid_geometry)
            new_obj.source_file = app_obj.f_handlers.export_gerber(obj_name=outname, filename=None,
                                                                   local_use=new_obj, use_thread=False)

        self.app.app_obj.new_object('gerber', outname, init_func)

    def on_proportional_method(self, grb_obj, outname):
        prop_factor = self.ui.factor_entry.get_value() / 100.0
        dia = None
        new_options = {}
        for opt in grb_obj.options:
            new_options[opt] = deepcopy(grb_obj.options[opt])

        if isinstance(grb_obj.solid_geometry, list):
            temp_solid_geometry = MultiPolygon(grb_obj.solid_geometry)
        else:
            temp_solid_geometry = grb_obj.solid_geometry

        punched_solid_geometry = temp_solid_geometry

        new_apertures = deepcopy(grb_obj.apertures)
        new_apertures_items = new_apertures.items()

        # find maximum aperture id
        new_apid = max([int(x) for x, __ in new_apertures_items])

        # selected codes in the apertures UI table
        sel_apid = []
        for it in self.ui.apertures_table.selectedItems():
            sel_apid.append(it.text())

        # store here the clear geometry, the key is the new aperture size
        holes_apertures = {}

        for apid, apid_value in grb_obj.apertures.items():
            ap_type = apid_value['type']
            punching_geo = []

            if apid in sel_apid:
                if ap_type == 'C' and self.ui.circular_cb.get_value():
                    dia = float(apid_value['size']) * prop_factor
                    for elem in apid_value['geometry']:
                        if 'follow' in elem and isinstance(elem['follow'], Point):
                            punching_geo.append(elem['follow'].buffer(dia / 2))
                elif ap_type == 'O' and self.ui.oblong_cb.get_value():
                    width = float(apid_value['width'])
                    height = float(apid_value['height'])

                    if width > height:
                        dia = float(apid_value['height']) * prop_factor
                    else:
                        dia = float(apid_value['width']) * prop_factor

                    for elem in grb_obj.apertures[apid]['geometry']:
                        if 'follow' in elem:
                            if isinstance(elem['follow'], Point):
                                punching_geo.append(elem['follow'].buffer(dia / 2))
                elif ap_type == 'R':
                    width = float(apid_value['width'])
                    height = float(apid_value['height'])

                    # if the height == width (float numbers so the reason for the following)
                    if round(width, self.decimals) == round(height, self.decimals):
                        if self.ui.square_cb.get_value():
                            dia = float(apid_value['height']) * prop_factor

                            for elem in grb_obj.apertures[apid]['geometry']:
                                if 'follow' in elem:
                                    if isinstance(elem['follow'], Point):
                                        punching_geo.append(elem['follow'].buffer(dia / 2))
                    elif self.ui.rectangular_cb.get_value():
                        if width > height:
                            dia = float(apid_value['height']) * prop_factor
                        else:
                            dia = float(apid_value['width']) * prop_factor

                        for elem in grb_obj.apertures[apid]['geometry']:
                            if 'follow' in elem:
                                if isinstance(elem['follow'], Point):
                                    punching_geo.append(elem['follow'].buffer(dia / 2))
                elif self.ui.other_cb.get_value():
                    try:
                        dia = float(apid_value['size']) * prop_factor
                    except KeyError:
                        if ap_type == 'AM':
                            pol = apid_value['geometry'][0]['solid']
                            x0, y0, x1, y1 = pol.bounds
                            dx = x1 - x0
                            dy = y1 - y0
                            if dx <= dy:
                                dia = dx * prop_factor
                            else:
                                dia = dy * prop_factor

                    for elem in grb_obj.apertures[apid]['geometry']:
                        if 'follow' in elem:
                            if isinstance(elem['follow'], Point):
                                punching_geo.append(elem['follow'].buffer(dia / 2))

            # if dia is None then none of the above applied so we skip the following
            if dia is None:
                continue

            punching_geo = MultiPolygon(punching_geo)

            if punching_geo is None or punching_geo.is_empty:
                continue

            punched_solid_geometry = punched_solid_geometry.difference(punching_geo)

            # update the gerber apertures to include the clear geometry so it can be exported successfully
            for elem in apid_value['geometry']:
                # make it work only for Gerber Flashes who are Points in 'follow'
                if 'solid' in elem and isinstance(elem['follow'], Point):
                    clear_apid_size = dia
                    for geo in punching_geo:

                        # since there may be drills that do not drill into a pad we test only for geos in a pad
                        if geo.within(elem['solid']):
                            geo_elem = {'clear': geo.centroid}

                            if clear_apid_size not in holes_apertures:
                                holes_apertures[clear_apid_size] = {
                                    'type': 'C',
                                    'size': clear_apid_size,
                                    'geometry': []
                                }

                            holes_apertures[clear_apid_size]['geometry'].append(deepcopy(geo_elem))

        # add the clear geometry to new apertures; it's easier than to test if there are apertures with the same
        # size and add there the clear geometry
        for hole_size, ap_val in holes_apertures.items():
            new_apid += 1
            new_apertures[str(new_apid)] = deepcopy(ap_val)

        def init_func(new_obj, app_obj):
            new_obj.options.update(new_options)
            new_obj.options['name'] = outname
            new_obj.fill_color = deepcopy(grb_obj.fill_color)
            new_obj.outline_color = deepcopy(grb_obj.outline_color)

            new_obj.apertures = deepcopy(new_apertures)

            new_obj.solid_geometry = deepcopy(punched_solid_geometry)
            new_obj.source_file = app_obj.f_handlers.export_gerber(obj_name=outname, filename=None,
                                                                   local_use=new_obj, use_thread=False)

        self.app.app_obj.new_object('gerber', outname, init_func)

    def on_mark_cb_click_table(self):
        """
        Will mark aperture geometries on canvas or delete the markings depending on the checkbox state
        :return:
        """

        try:
            cw = self.sender()
            cw_index = self.ui.apertures_table.indexAt(cw.pos())
            cw_row = cw_index.row()
        except AttributeError:
            cw_row = 0
        except TypeError:
            return

        try:
            aperture = self.ui.apertures_table.item(cw_row, 0).text()
        except AttributeError:
            return

        # get the Gerber file who is the source of the punched Gerber
        selection_index = self.ui.gerber_object_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.ui.gerber_object_combo.rootModelIndex())

        try:
            grb_obj = model_index.internalPointer().obj
        except Exception:
            return

        if self.ui.apertures_table.cellWidget(cw_row, 3).isChecked():
            # self.plot_aperture(color='#2d4606bf', marked_aperture=aperture, visible=True)
            grb_obj.plot_aperture(color=self.app.defaults['global_sel_draw_color'] + 'AA',
                                  marked_aperture=aperture, visible=True, run_thread=True)
        else:
            grb_obj.clear_plot_apertures(aperture=aperture)

    def reset_fields(self):
        self.ui.gerber_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.ui.exc_combo.setRootModelIndex(self.app.collection.index(1, 0, QtCore.QModelIndex()))
        self.ui_disconnect()


class PunchUI:

    toolName = _("Punch Gerber")

    def __init__(self, layout, app):
        self.app = app
        self.decimals = self.app.decimals
        self.layout = layout

        # ## Title
        title_label = QtWidgets.QLabel("%s" % self.toolName)
        title_label.setStyleSheet("""
                                QLabel
                                {
                                    font-size: 16px;
                                    font-weight: bold;
                                }
                                """)
        self.layout.addWidget(title_label)

        # Punch Drill holes
        self.layout.addWidget(QtWidgets.QLabel(""))

        # ## Grid Layout
        grid_lay = QtWidgets.QGridLayout()
        self.layout.addLayout(grid_lay)
        grid_lay.setColumnStretch(0, 1)
        grid_lay.setColumnStretch(1, 0)

        # ## Gerber Object
        self.gerber_object_combo = FCComboBox()
        self.gerber_object_combo.setModel(self.app.collection)
        self.gerber_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.gerber_object_combo.is_last = True
        self.gerber_object_combo.obj_type = "Gerber"

        self.grb_label = QtWidgets.QLabel("<b>%s:</b>" % _("GERBER"))
        self.grb_label.setToolTip('%s.' % _("Gerber into which to punch holes"))

        grid_lay.addWidget(self.grb_label, 0, 0, 1, 2)
        grid_lay.addWidget(self.gerber_object_combo, 1, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line, 2, 0, 1, 2)

        self.padt_label = QtWidgets.QLabel("<b>%s</b>" % _("Processed Pads Type"))
        self.padt_label.setToolTip(
            _("The type of pads shape to be processed.\n"
              "If the PCB has many SMD pads with rectangular pads,\n"
              "disable the Rectangular aperture.")
        )

        grid_lay.addWidget(self.padt_label, 3, 0, 1, 2)

        pad_all_grid = QtWidgets.QGridLayout()
        pad_all_grid.setColumnStretch(0, 0)
        pad_all_grid.setColumnStretch(1, 1)
        grid_lay.addLayout(pad_all_grid, 5, 0, 1, 2)

        pad_grid = QtWidgets.QGridLayout()
        pad_grid.setColumnStretch(0, 0)
        pad_all_grid.addLayout(pad_grid, 0, 0)

        # Select all
        self.select_all_cb = FCCheckBox('%s' % _("All"))
        pad_grid.addWidget(self.select_all_cb, 0, 0)

        # Circular Aperture Selection
        self.circular_cb = FCCheckBox('%s' % _("Circular"))
        self.circular_cb.setToolTip(
            _("Process Circular Pads.")
        )

        pad_grid.addWidget(self.circular_cb, 1, 0)

        # Oblong Aperture Selection
        self.oblong_cb = FCCheckBox('%s' % _("Oblong"))
        self.oblong_cb.setToolTip(
            _("Process Oblong Pads.")
        )

        pad_grid.addWidget(self.oblong_cb, 2, 0)

        # Square Aperture Selection
        self.square_cb = FCCheckBox('%s' % _("Square"))
        self.square_cb.setToolTip(
            _("Process Square Pads.")
        )

        pad_grid.addWidget(self.square_cb, 3, 0)

        # Rectangular Aperture Selection
        self.rectangular_cb = FCCheckBox('%s' % _("Rectangular"))
        self.rectangular_cb.setToolTip(
            _("Process Rectangular Pads.")
        )

        pad_grid.addWidget(self.rectangular_cb, 4, 0)

        # Others type of Apertures Selection
        self.other_cb = FCCheckBox('%s' % _("Others"))
        self.other_cb.setToolTip(
            _("Process pads not in the categories above.")
        )

        pad_grid.addWidget(self.other_cb, 5, 0)

        # Aperture Table
        self.apertures_table = FCTable()
        pad_all_grid.addWidget(self.apertures_table, 0, 1)

        self.apertures_table.setColumnCount(4)
        self.apertures_table.setHorizontalHeaderLabels([_('Code'), _('Type'), _('Size'), 'M'])
        self.apertures_table.setSortingEnabled(False)
        self.apertures_table.setRowCount(0)
        self.apertures_table.resizeColumnsToContents()
        self.apertures_table.resizeRowsToContents()

        self.apertures_table.horizontalHeaderItem(0).setToolTip(
            _("Aperture Code"))
        self.apertures_table.horizontalHeaderItem(1).setToolTip(
            _("Type of aperture: circular, rectangle, macros etc"))
        self.apertures_table.horizontalHeaderItem(2).setToolTip(
            _("Aperture Size:"))
        self.apertures_table.horizontalHeaderItem(3).setToolTip(
            _("Mark the aperture instances on canvas."))

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)
        self.apertures_table.setSizePolicy(sizePolicy)
        self.apertures_table.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line, 10, 0, 1, 2)

        # Grid Layout
        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)

        self.method_label = QtWidgets.QLabel('<b>%s:</b>' % _("Method"))
        self.method_label.setToolTip(
            _("The punch hole source can be:\n"
              "- Excellon Object-> the Excellon object drills center will serve as reference.\n"
              "- Fixed Diameter -> will try to use the pads center as reference adding fixed diameter holes.\n"
              "- Fixed Annular Ring -> will try to keep a set annular ring.\n"
              "- Proportional -> will make a Gerber punch hole having the diameter a percentage of the pad diameter.")
        )
        self.method_punch = RadioSet(
            [
                {'label': _('Excellon'), 'value': 'exc'},
                {'label': _("Fixed Diameter"), 'value': 'fixed'},
                {'label': _("Proportional"), 'value': 'prop'},
                {'label': _("Fixed Annular Ring"), 'value': 'ring'}
            ],
            orientation='vertical',
            stretch=False)
        grid0.addWidget(self.method_label, 0, 0, 1, 2)
        grid0.addWidget(self.method_punch, 1, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 2, 0, 1, 2)

        self.exc_label = QtWidgets.QLabel('<b>%s</b>' % _("Excellon"))
        self.exc_label.setToolTip(
            _("Remove the geometry of Excellon from the Gerber to create the holes in pads.")
        )

        self.exc_combo = FCComboBox()
        self.exc_combo.setModel(self.app.collection)
        self.exc_combo.setRootModelIndex(self.app.collection.index(1, 0, QtCore.QModelIndex()))
        self.exc_combo.is_last = True
        self.exc_combo.obj_type = "Excellon"

        grid0.addWidget(self.exc_label, 3, 0, 1, 2)
        grid0.addWidget(self.exc_combo, 4, 0, 1, 2)

        # Fixed Dia
        self.fixed_label = QtWidgets.QLabel('<b>%s</b>' % _("Fixed Diameter"))
        grid0.addWidget(self.fixed_label, 6, 0, 1, 2)

        # Diameter value
        self.dia_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.dia_entry.set_precision(self.decimals)
        self.dia_entry.set_range(0.0000, 10000.0000)

        self.dia_label = QtWidgets.QLabel('%s:' % _("Value"))
        self.dia_label.setToolTip(
            _("Fixed hole diameter.")
        )

        grid0.addWidget(self.dia_label, 8, 0)
        grid0.addWidget(self.dia_entry, 8, 1)

        # #############################################################################################################
        # RING FRAME
        # #############################################################################################################
        self.ring_frame = QtWidgets.QFrame()
        self.ring_frame.setContentsMargins(0, 0, 0, 0)
        grid0.addWidget(self.ring_frame, 10, 0, 1, 2)

        self.ring_box = QtWidgets.QVBoxLayout()
        self.ring_box.setContentsMargins(0, 0, 0, 0)
        self.ring_frame.setLayout(self.ring_box)

        # Annular Ring value
        self.ring_label = QtWidgets.QLabel('<b>%s</b>' % _("Fixed Annular Ring"))
        self.ring_label.setToolTip(
            _("The size of annular ring.\n"
              "The copper sliver between the hole exterior\n"
              "and the margin of the copper pad.")
        )
        self.ring_box.addWidget(self.ring_label)

        # ## Grid Layout
        self.grid1 = QtWidgets.QGridLayout()
        self.grid1.setColumnStretch(0, 0)
        self.grid1.setColumnStretch(1, 1)
        self.ring_box.addLayout(self.grid1)

        # Circular Annular Ring Value
        self.circular_ring_label = QtWidgets.QLabel('%s:' % _("Circular"))
        self.circular_ring_label.setToolTip(
            _("The size of annular ring for circular pads.")
        )

        self.circular_ring_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.circular_ring_entry.set_precision(self.decimals)
        self.circular_ring_entry.set_range(0.0000, 10000.0000)

        self.grid1.addWidget(self.circular_ring_label, 3, 0)
        self.grid1.addWidget(self.circular_ring_entry, 3, 1)

        # Oblong Annular Ring Value
        self.oblong_ring_label = QtWidgets.QLabel('%s:' % _("Oblong"))
        self.oblong_ring_label.setToolTip(
            _("The size of annular ring for oblong pads.")
        )

        self.oblong_ring_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.oblong_ring_entry.set_precision(self.decimals)
        self.oblong_ring_entry.set_range(0.0000, 10000.0000)

        self.grid1.addWidget(self.oblong_ring_label, 4, 0)
        self.grid1.addWidget(self.oblong_ring_entry, 4, 1)

        # Square Annular Ring Value
        self.square_ring_label = QtWidgets.QLabel('%s:' % _("Square"))
        self.square_ring_label.setToolTip(
            _("The size of annular ring for square pads.")
        )

        self.square_ring_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.square_ring_entry.set_precision(self.decimals)
        self.square_ring_entry.set_range(0.0000, 10000.0000)

        self.grid1.addWidget(self.square_ring_label, 5, 0)
        self.grid1.addWidget(self.square_ring_entry, 5, 1)

        # Rectangular Annular Ring Value
        self.rectangular_ring_label = QtWidgets.QLabel('%s:' % _("Rectangular"))
        self.rectangular_ring_label.setToolTip(
            _("The size of annular ring for rectangular pads.")
        )

        self.rectangular_ring_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.rectangular_ring_entry.set_precision(self.decimals)
        self.rectangular_ring_entry.set_range(0.0000, 10000.0000)

        self.grid1.addWidget(self.rectangular_ring_label, 6, 0)
        self.grid1.addWidget(self.rectangular_ring_entry, 6, 1)

        # Others Annular Ring Value
        self.other_ring_label = QtWidgets.QLabel('%s:' % _("Others"))
        self.other_ring_label.setToolTip(
            _("The size of annular ring for other pads.")
        )

        self.other_ring_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.other_ring_entry.set_precision(self.decimals)
        self.other_ring_entry.set_range(0.0000, 10000.0000)

        self.grid1.addWidget(self.other_ring_label, 7, 0)
        self.grid1.addWidget(self.other_ring_entry, 7, 1)
        # #############################################################################################################

        # Proportional value
        self.prop_label = QtWidgets.QLabel('<b>%s</b>' % _("Proportional Diameter"))
        grid0.addWidget(self.prop_label, 12, 0, 1, 2)

        # Diameter value
        self.factor_entry = FCDoubleSpinner(callback=self.confirmation_message, suffix='%')
        self.factor_entry.set_precision(self.decimals)
        self.factor_entry.set_range(0.0000, 100.0000)
        self.factor_entry.setSingleStep(0.1)

        self.factor_label = QtWidgets.QLabel('%s:' % _("Value"))
        self.factor_label.setToolTip(
            _("Proportional Diameter.\n"
              "The hole diameter will be a fraction of the pad size.")
        )

        grid0.addWidget(self.factor_label, 13, 0)
        grid0.addWidget(self.factor_entry, 13, 1)

        separator_line3 = QtWidgets.QFrame()
        separator_line3.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line3.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line3, 14, 0, 1, 2)

        # Buttons
        self.punch_object_button = QtWidgets.QPushButton(_("Punch Gerber"))
        self.punch_object_button.setIcon(QtGui.QIcon(self.app.resource_location + '/punch32.png'))
        self.punch_object_button.setToolTip(
            _("Create a Gerber object from the selected object, within\n"
              "the specified box.")
        )
        self.punch_object_button.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        self.layout.addWidget(self.punch_object_button)

        self.layout.addStretch()

        # ## Reset Tool
        self.reset_button = QtWidgets.QPushButton(_("Reset Tool"))
        self.reset_button.setIcon(QtGui.QIcon(self.app.resource_location + '/reset32.png'))
        self.reset_button.setToolTip(
            _("Will reset the tool parameters.")
        )
        self.reset_button.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        self.layout.addWidget(self.reset_button)

        self.circular_ring_entry.setEnabled(False)
        self.oblong_ring_entry.setEnabled(False)
        self.square_ring_entry.setEnabled(False)
        self.rectangular_ring_entry.setEnabled(False)
        self.other_ring_entry.setEnabled(False)

        self.dia_entry.hide()
        self.dia_label.hide()
        self.factor_label.hide()
        self.factor_entry.hide()

        # #################################### FINSIHED GUI ###########################
        # #############################################################################

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
