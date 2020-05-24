# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
# ##########################################################

# ##########################################################
# File modified by: Marius Stanciu                         #
# ##########################################################


from shapely.geometry import Point, Polygon, MultiPolygon, MultiLineString, LineString, LinearRing
from shapely.ops import cascaded_union

from AppParsers.ParseGerber import Gerber
from AppObjects.FlatCAMObj import *

import math
import numpy as np
from copy import deepcopy

import gettext
import AppTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class GerberObject(FlatCAMObj, Gerber):
    """
    Represents Gerber code.
    """
    optionChanged = QtCore.pyqtSignal(str)
    replotApertures = QtCore.pyqtSignal()

    ui_type = GerberObjectUI

    @staticmethod
    def merge(grb_list, grb_final):
        """
        Merges the geometry of objects in geo_list into
        the geometry of geo_final.

        :param grb_list: List of GerberObject Objects to join.
        :param grb_final: Destination GeometryObject object.
        :return: None
        """

        if grb_final.solid_geometry is None:
            grb_final.solid_geometry = []
            grb_final.follow_geometry = []

        if not grb_final.apertures:
            grb_final.apertures = {}

        if type(grb_final.solid_geometry) is not list:
            grb_final.solid_geometry = [grb_final.solid_geometry]
            grb_final.follow_geometry = [grb_final.follow_geometry]

        for grb in grb_list:

            # Expand lists
            if type(grb) is list:
                GerberObject.merge(grb_list=grb, grb_final=grb_final)
            else:   # If not list, just append
                for option in grb.options:
                    if option != 'name':
                        try:
                            grb_final.options[option] = grb.options[option]
                        except KeyError:
                            log.warning("Failed to copy option.", option)

                try:
                    for geos in grb.solid_geometry:
                        grb_final.solid_geometry.append(geos)
                        grb_final.follow_geometry.append(geos)
                except TypeError:
                    grb_final.solid_geometry.append(grb.solid_geometry)
                    grb_final.follow_geometry.append(grb.solid_geometry)

                for ap in grb.apertures:
                    if ap not in grb_final.apertures:
                        grb_final.apertures[ap] = grb.apertures[ap]
                    else:
                        # create a list of integers out of the grb.apertures keys and find the max of that value
                        # then, the aperture duplicate is assigned an id value incremented with 1,
                        # and finally made string because the apertures dict keys are strings
                        max_ap = str(max([int(k) for k in grb_final.apertures.keys()]) + 1)
                        grb_final.apertures[max_ap] = {}
                        grb_final.apertures[max_ap]['geometry'] = []

                        for k, v in grb.apertures[ap].items():
                            grb_final.apertures[max_ap][k] = deepcopy(v)

        grb_final.solid_geometry = MultiPolygon(grb_final.solid_geometry)
        grb_final.follow_geometry = MultiPolygon(grb_final.follow_geometry)

    def __init__(self, name):
        self.decimals = self.app.decimals

        self.circle_steps = int(self.app.defaults["gerber_circle_steps"])

        Gerber.__init__(self, steps_per_circle=self.circle_steps)
        FlatCAMObj.__init__(self, name)

        self.kind = "gerber"

        # The 'name' is already in self.options from FlatCAMObj
        # Automatically updates the UI
        self.options.update({
            "plot": True,
            "multicolored": False,
            "solid": False,
            "tool_type": 'circular',
            "vtipdia": 0.1,
            "vtipangle": 30,
            "vcutz": -0.05,
            "isotooldia": 0.016,
            "isopasses": 1,
            "isooverlap": 15,
            "milling_type": "cl",
            "combine_passes": True,
            "noncoppermargin": 0.0,
            "noncopperrounded": False,
            "bboxmargin": 0.0,
            "bboxrounded": False,
            "aperture_display": False,
            "follow": False,
            "iso_scope": 'all',
            "iso_type": 'full'
        })

        # type of isolation: 0 = exteriors, 1 = interiors, 2 = complete isolation (both interiors and exteriors)
        self.iso_type = 2

        self.multigeo = False

        self.follow = False

        self.apertures_row = 0

        # store the source file here
        self.source_file = ""

        # list of rows with apertures plotted
        self.marked_rows = []

        # Mouse events
        self.mr = None
        self.mm = None
        self.mp = None

        # dict to store the polygons selected for isolation; key is the shape added to be plotted and value is the poly
        self.poly_dict = {}

        # store the status of grid snapping
        self.grid_status_memory = None

        self.units_found = self.app.defaults['units']

        self.fill_color = self.app.defaults['gerber_plot_fill']
        self.outline_color = self.app.defaults['gerber_plot_line']
        self.alpha_level = 'bf'

        # keep track if the UI is built so we don't have to build it every time
        self.ui_build = False

        # build only once the aperture storage (takes time)
        self.build_aperture_storage = False

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from predecessors.
        self.ser_attrs += ['options', 'kind', 'fill_color', 'outline_color', 'alpha_level']

    def set_ui(self, ui):
        """
        Maps options with GUI inputs.
        Connects GUI events to methods.

        :param ui: GUI object.
        :type ui: GerberObjectUI
        :return: None
        """
        FlatCAMObj.set_ui(self, ui)
        log.debug("GerberObject.set_ui()")

        self.units = self.app.defaults['units'].upper()

        self.replotApertures.connect(self.on_mark_cb_click_table)

        self.form_fields.update({
            "plot": self.ui.plot_cb,
            "multicolored": self.ui.multicolored_cb,
            "solid": self.ui.solid_cb,
            "tool_type": self.ui.tool_type_radio,
            "vtipdia": self.ui.tipdia_spinner,
            "vtipangle": self.ui.tipangle_spinner,
            "vcutz": self.ui.cutz_spinner,
            "isotooldia": self.ui.iso_tool_dia_entry,
            "isopasses": self.ui.iso_width_entry,
            "isooverlap": self.ui.iso_overlap_entry,
            "milling_type": self.ui.milling_type_radio,
            "combine_passes": self.ui.combine_passes_cb,
            "noncoppermargin": self.ui.noncopper_margin_entry,
            "noncopperrounded": self.ui.noncopper_rounded_cb,
            "bboxmargin": self.ui.bbmargin_entry,
            "bboxrounded": self.ui.bbrounded_cb,
            "aperture_display": self.ui.aperture_table_visibility_cb,
            "follow": self.ui.follow_cb,
            "iso_scope": self.ui.iso_scope_radio,
            "iso_type": self.ui.iso_type_radio
        })

        # Fill form fields only on object create
        self.to_form()

        assert isinstance(self.ui, GerberObjectUI)
        self.ui.plot_cb.stateChanged.connect(self.on_plot_cb_click)
        self.ui.solid_cb.stateChanged.connect(self.on_solid_cb_click)
        self.ui.multicolored_cb.stateChanged.connect(self.on_multicolored_cb_click)
        self.ui.generate_iso_button.clicked.connect(self.on_iso_button_click)
        self.ui.generate_ncc_button.clicked.connect(self.app.ncclear_tool.run)
        self.ui.generate_cutout_button.clicked.connect(self.app.cutout_tool.run)
        self.ui.generate_bb_button.clicked.connect(self.on_generatebb_button_click)
        self.ui.generate_noncopper_button.clicked.connect(self.on_generatenoncopper_button_click)
        self.ui.aperture_table_visibility_cb.stateChanged.connect(self.on_aperture_table_visibility_change)
        self.ui.follow_cb.stateChanged.connect(self.on_follow_cb_click)

        # set the model for the Area Exception comboboxes
        self.ui.obj_combo.setModel(self.app.collection)
        self.ui.obj_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.ui.obj_combo.is_last = True
        self.ui.obj_combo.obj_type = {
            _("Gerber"): "Gerber", _("Geometry"): "Geometry"
        }[self.ui.type_obj_combo.get_value()]
        self.on_type_obj_index_changed()

        self.ui.type_obj_combo.currentIndexChanged.connect(self.on_type_obj_index_changed)

        self.ui.tool_type_radio.activated_custom.connect(self.on_tool_type_change)
        # establish visibility for the GUI elements found in the slot function
        self.ui.tool_type_radio.activated_custom.emit(self.options['tool_type'])

        # Show/Hide Advanced Options
        if self.app.defaults["global_app_level"] == 'b':
            self.ui.level.setText('<span style="color:green;"><b>%s</b></span>' % _('Basic'))
            self.options['tool_type'] = 'circular'

            self.ui.tool_type_label.hide()
            self.ui.tool_type_radio.hide()

            # override the Preferences Value; in Basic mode the Tool Type is always Circular ('C1')
            self.ui.tool_type_radio.set_value('circular')

            self.ui.tipdialabel.hide()
            self.ui.tipdia_spinner.hide()
            self.ui.tipanglelabel.hide()
            self.ui.tipangle_spinner.hide()
            self.ui.cutzlabel.hide()
            self.ui.cutz_spinner.hide()

            self.ui.apertures_table_label.hide()
            self.ui.aperture_table_visibility_cb.hide()
            self.ui.milling_type_label.hide()
            self.ui.milling_type_radio.hide()
            self.ui.iso_type_label.hide()
            self.ui.iso_type_radio.hide()

            self.ui.follow_cb.hide()
            self.ui.except_cb.setChecked(False)
            self.ui.except_cb.hide()
        else:
            self.ui.level.setText('<span style="color:red;"><b>%s</b></span>' % _('Advanced'))
            self.ui.tipdia_spinner.valueChanged.connect(self.on_calculate_tooldia)
            self.ui.tipangle_spinner.valueChanged.connect(self.on_calculate_tooldia)
            self.ui.cutz_spinner.valueChanged.connect(self.on_calculate_tooldia)

        if self.app.defaults["gerber_buffering"] == 'no':
            self.ui.create_buffer_button.show()
            try:
                self.ui.create_buffer_button.clicked.disconnect(self.on_generate_buffer)
            except TypeError:
                pass
            self.ui.create_buffer_button.clicked.connect(self.on_generate_buffer)
        else:
            self.ui.create_buffer_button.hide()

        # set initial state of the aperture table and associated widgets
        self.on_aperture_table_visibility_change()

        self.build_ui()
        self.units_found = self.app.defaults['units']

    def on_calculate_tooldia(self):
        try:
            tdia = float(self.ui.tipdia_spinner.get_value())
        except Exception:
            return
        try:
            dang = float(self.ui.tipangle_spinner.get_value())
        except Exception:
            return
        try:
            cutz = float(self.ui.cutz_spinner.get_value())
        except Exception:
            return

        cutz *= -1
        if cutz < 0:
            cutz *= -1

        half_tip_angle = dang / 2

        tool_diameter = tdia + (2 * cutz * math.tan(math.radians(half_tip_angle)))
        self.ui.iso_tool_dia_entry.set_value(tool_diameter)

    def on_type_obj_index_changed(self):
        val = self.ui.type_obj_combo.get_value()
        obj_type = {"Gerber": 0, "Geometry": 2}[val]
        self.ui.obj_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.ui.obj_combo.setCurrentIndex(0)
        self.ui.obj_combo.obj_type = {_("Gerber"): "Gerber", _("Geometry"): "Geometry"}[val]

    def on_tool_type_change(self, state):
        if state == 'circular':
            self.ui.tipdialabel.hide()
            self.ui.tipdia_spinner.hide()
            self.ui.tipanglelabel.hide()
            self.ui.tipangle_spinner.hide()
            self.ui.cutzlabel.hide()
            self.ui.cutz_spinner.hide()
            self.ui.iso_tool_dia_entry.setDisabled(False)
            # update the value in the self.iso_tool_dia_entry once this is selected
            self.ui.iso_tool_dia_entry.set_value(self.options['isotooldia'])
        else:
            self.ui.tipdialabel.show()
            self.ui.tipdia_spinner.show()
            self.ui.tipanglelabel.show()
            self.ui.tipangle_spinner.show()
            self.ui.cutzlabel.show()
            self.ui.cutz_spinner.show()
            self.ui.iso_tool_dia_entry.setDisabled(True)
            # update the value in the self.iso_tool_dia_entry once this is selected
            self.on_calculate_tooldia()

    def build_ui(self):
        FlatCAMObj.build_ui(self)

        if self.ui.aperture_table_visibility_cb.get_value() and self.ui_build is False:
            self.ui_build = True

            try:
                # if connected, disconnect the signal from the slot on item_changed as it creates issues
                self.ui.apertures_table.itemChanged.disconnect()
            except (TypeError, AttributeError):
                pass

            self.apertures_row = 0
            aper_no = self.apertures_row + 1
            sort = []
            for k, v in list(self.apertures.items()):
                sort.append(int(k))
            sorted_apertures = sorted(sort)

            n = len(sorted_apertures)
            self.ui.apertures_table.setRowCount(n)

            for ap_code in sorted_apertures:
                ap_code = str(ap_code)

                ap_id_item = QtWidgets.QTableWidgetItem('%d' % int(self.apertures_row + 1))
                ap_id_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                self.ui.apertures_table.setItem(self.apertures_row, 0, ap_id_item)  # Tool name/id

                ap_code_item = QtWidgets.QTableWidgetItem(ap_code)
                ap_code_item.setFlags(QtCore.Qt.ItemIsEnabled)

                ap_type_item = QtWidgets.QTableWidgetItem(str(self.apertures[ap_code]['type']))
                ap_type_item.setFlags(QtCore.Qt.ItemIsEnabled)

                if str(self.apertures[ap_code]['type']) == 'R' or str(self.apertures[ap_code]['type']) == 'O':
                    ap_dim_item = QtWidgets.QTableWidgetItem(
                        '%.*f, %.*f' % (self.decimals, self.apertures[ap_code]['width'],
                                        self.decimals, self.apertures[ap_code]['height']
                                        )
                    )
                    ap_dim_item.setFlags(QtCore.Qt.ItemIsEnabled)
                elif str(self.apertures[ap_code]['type']) == 'P':
                    ap_dim_item = QtWidgets.QTableWidgetItem(
                        '%.*f, %.*f' % (self.decimals, self.apertures[ap_code]['diam'],
                                        self.decimals, self.apertures[ap_code]['nVertices'])
                    )
                    ap_dim_item.setFlags(QtCore.Qt.ItemIsEnabled)
                else:
                    ap_dim_item = QtWidgets.QTableWidgetItem('')
                    ap_dim_item.setFlags(QtCore.Qt.ItemIsEnabled)

                try:
                    if self.apertures[ap_code]['size'] is not None:
                        ap_size_item = QtWidgets.QTableWidgetItem(
                            '%.*f' % (self.decimals, float(self.apertures[ap_code]['size'])))
                    else:
                        ap_size_item = QtWidgets.QTableWidgetItem('')
                except KeyError:
                    ap_size_item = QtWidgets.QTableWidgetItem('')
                ap_size_item.setFlags(QtCore.Qt.ItemIsEnabled)

                mark_item = FCCheckBox()
                mark_item.setLayoutDirection(QtCore.Qt.RightToLeft)
                # if self.ui.aperture_table_visibility_cb.isChecked():
                #     mark_item.setChecked(True)

                self.ui.apertures_table.setItem(self.apertures_row, 1, ap_code_item)  # Aperture Code
                self.ui.apertures_table.setItem(self.apertures_row, 2, ap_type_item)  # Aperture Type
                self.ui.apertures_table.setItem(self.apertures_row, 3, ap_size_item)   # Aperture Dimensions
                self.ui.apertures_table.setItem(self.apertures_row, 4, ap_dim_item)   # Aperture Dimensions

                empty_plot_item = QtWidgets.QTableWidgetItem('')
                empty_plot_item.setFlags(~QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                self.ui.apertures_table.setItem(self.apertures_row, 5, empty_plot_item)
                self.ui.apertures_table.setCellWidget(self.apertures_row, 5, mark_item)

                self.apertures_row += 1

            self.ui.apertures_table.selectColumn(0)
            self.ui.apertures_table.resizeColumnsToContents()
            self.ui.apertures_table.resizeRowsToContents()

            vertical_header = self.ui.apertures_table.verticalHeader()
            # vertical_header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
            vertical_header.hide()
            self.ui.apertures_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

            horizontal_header = self.ui.apertures_table.horizontalHeader()
            horizontal_header.setMinimumSectionSize(10)
            horizontal_header.setDefaultSectionSize(70)
            horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
            horizontal_header.resizeSection(0, 27)
            horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
            horizontal_header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
            horizontal_header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
            horizontal_header.setSectionResizeMode(4,  QtWidgets.QHeaderView.Stretch)
            horizontal_header.setSectionResizeMode(5, QtWidgets.QHeaderView.Fixed)
            horizontal_header.resizeSection(5, 17)
            self.ui.apertures_table.setColumnWidth(5, 17)

            self.ui.apertures_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            self.ui.apertures_table.setSortingEnabled(False)
            self.ui.apertures_table.setMinimumHeight(self.ui.apertures_table.getHeight())
            self.ui.apertures_table.setMaximumHeight(self.ui.apertures_table.getHeight())

            # update the 'mark' checkboxes state according with what is stored in the self.marked_rows list
            if self.marked_rows:
                for row in range(self.ui.apertures_table.rowCount()):
                    try:
                        self.ui.apertures_table.cellWidget(row, 5).set_value(self.marked_rows[row])
                    except IndexError:
                        pass

            self.ui_connect()

    def ui_connect(self):
        for row in range(self.ui.apertures_table.rowCount()):
            try:
                self.ui.apertures_table.cellWidget(row, 5).clicked.disconnect(self.on_mark_cb_click_table)
            except (TypeError, AttributeError):
                pass
            self.ui.apertures_table.cellWidget(row, 5).clicked.connect(self.on_mark_cb_click_table)

        try:
            self.ui.mark_all_cb.clicked.disconnect(self.on_mark_all_click)
        except (TypeError, AttributeError):
            pass
        self.ui.mark_all_cb.clicked.connect(self.on_mark_all_click)

    def ui_disconnect(self):
        for row in range(self.ui.apertures_table.rowCount()):
            try:
                self.ui.apertures_table.cellWidget(row, 5).clicked.disconnect()
            except (TypeError, AttributeError):
                pass

        try:
            self.ui.mark_all_cb.clicked.disconnect(self.on_mark_all_click)
        except (TypeError, AttributeError):
            pass

    def on_generate_buffer(self):
        self.app.inform.emit('[WARNING_NOTCL] %s...' % _("Buffering solid geometry"))

        def buffer_task():
            with self.app.proc_container.new('%s...' % _("Buffering")):
                if isinstance(self.solid_geometry, list):
                    self.solid_geometry = MultiPolygon(self.solid_geometry)

                self.solid_geometry = self.solid_geometry.buffer(0.0000001)
                self.solid_geometry = self.solid_geometry.buffer(-0.0000001)
                self.app.inform.emit('[success] %s.' % _("Done"))
                self.plot_single_object.emit()

        self.app.worker_task.emit({'fcn': buffer_task, 'params': []})

    def on_generatenoncopper_button_click(self, *args):
        self.app.defaults.report_usage("gerber_on_generatenoncopper_button")

        self.read_form()
        name = self.options["name"] + "_noncopper"

        def geo_init(geo_obj, app_obj):
            assert geo_obj.kind == 'geometry', "Expected a Geometry object got %s" % type(geo_obj)

            if isinstance(self.solid_geometry, list):
                try:
                    self.solid_geometry = MultiPolygon(self.solid_geometry)
                except Exception:
                    self.solid_geometry = cascaded_union(self.solid_geometry)

            bounding_box = self.solid_geometry.envelope.buffer(float(self.options["noncoppermargin"]))
            if not self.options["noncopperrounded"]:
                bounding_box = bounding_box.envelope
            non_copper = bounding_box.difference(self.solid_geometry)

            if non_copper is None or non_copper.is_empty:
                self.app.inform.emit("[ERROR_NOTCL] %s" % _("Operation could not be done."))
                return "fail"
            geo_obj.solid_geometry = non_copper

        self.app.app_obj.new_object("geometry", name, geo_init)

    def on_generatebb_button_click(self, *args):
        self.app.defaults.report_usage("gerber_on_generatebb_button")
        self.read_form()
        name = self.options["name"] + "_bbox"

        def geo_init(geo_obj, app_obj):
            assert geo_obj.kind == 'geometry', "Expected a Geometry object got %s" % type(geo_obj)

            if isinstance(self.solid_geometry, list):
                try:
                    self.solid_geometry = MultiPolygon(self.solid_geometry)
                except Exception:
                    self.solid_geometry = cascaded_union(self.solid_geometry)

            # Bounding box with rounded corners
            bounding_box = self.solid_geometry.envelope.buffer(float(self.options["bboxmargin"]))
            if not self.options["bboxrounded"]:  # Remove rounded corners
                bounding_box = bounding_box.envelope

            if bounding_box is None or bounding_box.is_empty:
                self.app.inform.emit("[ERROR_NOTCL] %s" % _("Operation could not be done."))
                return "fail"
            geo_obj.solid_geometry = bounding_box

        self.app.app_obj.new_object("geometry", name, geo_init)

    def on_iso_button_click(self, *args):

        obj = self.app.collection.get_active()

        self.iso_type = 2
        if self.ui.iso_type_radio.get_value() == 'ext':
            self.iso_type = 0
        if self.ui.iso_type_radio.get_value() == 'int':
            self.iso_type = 1

        def worker_task(iso_obj, app_obj):
            with self.app.proc_container.new(_("Isolating...")):
                if self.ui.follow_cb.get_value() is True:
                    iso_obj.follow_geo()
                    # in the end toggle the visibility of the origin object so we can see the generated Geometry
                    iso_obj.ui.plot_cb.toggle()
                else:
                    app_obj.defaults.report_usage("gerber_on_iso_button")
                    self.read_form()

                    iso_scope = 'all' if self.ui.iso_scope_radio.get_value() == 'all' else 'single'
                    self.isolate_handler(iso_type=self.iso_type, iso_scope=iso_scope)

        self.app.worker_task.emit({'fcn': worker_task, 'params': [obj, self.app]})

    def follow_geo(self, outname=None):
        """
        Creates a geometry object "following" the gerber paths.

        :return: None
        """

        # default_name = self.options["name"] + "_follow"
        # follow_name = outname or default_name

        if outname is None:
            follow_name = self.options["name"] + "_follow"
        else:
            follow_name = outname

        def follow_init(follow_obj, app):
            # Propagate options
            follow_obj.options["cnctooldia"] = str(self.options["isotooldia"])
            follow_obj.solid_geometry = self.follow_geometry

        # TODO: Do something if this is None. Offer changing name?
        try:
            self.app.app_obj.new_object("geometry", follow_name, follow_init)
        except Exception as e:
            return "Operation failed: %s" % str(e)

    def isolate_handler(self, iso_type, iso_scope):

        if iso_scope == 'all':
            self.isolate(iso_type=iso_type)
        else:
            # disengage the grid snapping since it may be hard to click on polygons with grid snapping on
            if self.app.ui.grid_snap_btn.isChecked():
                self.grid_status_memory = True
                self.app.ui.grid_snap_btn.trigger()
            else:
                self.grid_status_memory = False

            self.mr = self.app.plotcanvas.graph_event_connect('mouse_release', self.on_mouse_click_release)

            if self.app.is_legacy is False:
                self.app.plotcanvas.graph_event_disconnect('mouse_release', self.app.on_mouse_click_release_over_plot)
            else:
                self.app.plotcanvas.graph_event_disconnect(self.app.mr)

            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Click on a polygon to isolate it."))

    def on_mouse_click_release(self, event):
        if self.app.is_legacy is False:
            event_pos = event.pos
            right_button = 2
            self.app.event_is_dragging = self.app.event_is_dragging
        else:
            event_pos = (event.xdata, event.ydata)
            right_button = 3
            self.app.event_is_dragging = self.app.ui.popMenu.mouse_is_panning

        try:
            x = float(event_pos[0])
            y = float(event_pos[1])
        except TypeError:
            return

        event_pos = (x, y)
        curr_pos = self.app.plotcanvas.translate_coords(event_pos)
        if self.app.grid_status():
            curr_pos = self.app.geo_editor.snap(curr_pos[0], curr_pos[1])
        else:
            curr_pos = (curr_pos[0], curr_pos[1])

        if event.button == 1:
            clicked_poly = self.find_polygon(point=(curr_pos[0], curr_pos[1]))

            if self.app.selection_type is not None:
                self.selection_area_handler(self.app.pos, curr_pos, self.app.selection_type)
                self.app.selection_type = None
            elif clicked_poly:
                if clicked_poly not in self.poly_dict.values():
                    shape_id = self.app.tool_shapes.add(tolerance=self.drawing_tolerance, layer=0, shape=clicked_poly,
                                                        color=self.app.defaults['global_sel_draw_color'] + 'AF',
                                                        face_color=self.app.defaults['global_sel_draw_color'] + 'AF',
                                                        visible=True)
                    self.poly_dict[shape_id] = clicked_poly
                    self.app.inform.emit(
                        '%s: %d. %s' % (_("Added polygon"), int(len(self.poly_dict)),
                                        _("Click to add next polygon or right click to start isolation."))
                    )
                else:
                    try:
                        for k, v in list(self.poly_dict.items()):
                            if v == clicked_poly:
                                self.app.tool_shapes.remove(k)
                                self.poly_dict.pop(k)
                                break
                    except TypeError:
                        return
                    self.app.inform.emit(
                        '%s. %s' % (_("Removed polygon"),
                                    _("Click to add/remove next polygon or right click to start isolation."))
                    )

                self.app.tool_shapes.redraw()
            else:
                self.app.inform.emit(_("No polygon detected under click position."))
        elif event.button == right_button and self.app.event_is_dragging is False:
            # restore the Grid snapping if it was active before
            if self.grid_status_memory is True:
                self.app.ui.grid_snap_btn.trigger()

            if self.app.is_legacy is False:
                self.app.plotcanvas.graph_event_disconnect('mouse_release', self.on_mouse_click_release)
            else:
                self.app.plotcanvas.graph_event_disconnect(self.mr)

            self.app.mr = self.app.plotcanvas.graph_event_connect('mouse_release',
                                                                  self.app.on_mouse_click_release_over_plot)

            self.app.tool_shapes.clear(update=True)

            if self.poly_dict:
                poly_list = deepcopy(list(self.poly_dict.values()))
                self.isolate(iso_type=self.iso_type, geometry=poly_list)
                self.poly_dict.clear()
            else:
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("List of single polygons is empty. Aborting."))

    def selection_area_handler(self, start_pos, end_pos, sel_type):
        """
        :param start_pos: mouse position when the selection LMB click was done
        :param end_pos: mouse position when the left mouse button is released
        :param sel_type: if True it's a left to right selection (enclosure), if False it's a 'touch' selection
        :return:
        """
        poly_selection = Polygon([start_pos, (end_pos[0], start_pos[1]), end_pos, (start_pos[0], end_pos[1])])

        # delete previous selection shape
        self.app.delete_selection_shape()

        added_poly_count = 0
        try:
            for geo in self.solid_geometry:
                if geo not in self.poly_dict.values():
                    if sel_type is True:
                        if geo.within(poly_selection):
                            shape_id = self.app.tool_shapes.add(tolerance=self.drawing_tolerance, layer=0,
                                                                shape=geo,
                                                                color=self.app.defaults['global_sel_draw_color'] + 'AF',
                                                                face_color=self.app.defaults[
                                                                               'global_sel_draw_color'] + 'AF',
                                                                visible=True)
                            self.poly_dict[shape_id] = geo
                            added_poly_count += 1
                    else:
                        if poly_selection.intersects(geo):
                            shape_id = self.app.tool_shapes.add(tolerance=self.drawing_tolerance, layer=0,
                                                                shape=geo,
                                                                color=self.app.defaults['global_sel_draw_color'] + 'AF',
                                                                face_color=self.app.defaults[
                                                                               'global_sel_draw_color'] + 'AF',
                                                                visible=True)
                            self.poly_dict[shape_id] = geo
                            added_poly_count += 1
        except TypeError:
            if self.solid_geometry not in self.poly_dict.values():
                if sel_type is True:
                    if self.solid_geometry.within(poly_selection):
                        shape_id = self.app.tool_shapes.add(tolerance=self.drawing_tolerance, layer=0,
                                                            shape=self.solid_geometry,
                                                            color=self.app.defaults['global_sel_draw_color'] + 'AF',
                                                            face_color=self.app.defaults[
                                                                           'global_sel_draw_color'] + 'AF',
                                                            visible=True)
                        self.poly_dict[shape_id] = self.solid_geometry
                        added_poly_count += 1
                else:
                    if poly_selection.intersects(self.solid_geometry):
                        shape_id = self.app.tool_shapes.add(tolerance=self.drawing_tolerance, layer=0,
                                                            shape=self.solid_geometry,
                                                            color=self.app.defaults['global_sel_draw_color'] + 'AF',
                                                            face_color=self.app.defaults[
                                                                           'global_sel_draw_color'] + 'AF',
                                                            visible=True)
                        self.poly_dict[shape_id] = self.solid_geometry
                        added_poly_count += 1

        if added_poly_count > 0:
            self.app.tool_shapes.redraw()
            self.app.inform.emit(
                '%s: %d. %s' % (_("Added polygon"),
                                int(added_poly_count),
                                _("Click to add next polygon or right click to start isolation."))
            )
        else:
            self.app.inform.emit(_("No polygon in selection."))

    def isolate(self, iso_type=None, geometry=None, dia=None, passes=None, overlap=None, outname=None, combine=None,
                milling_type=None, follow=None, plot=True):
        """
        Creates an isolation routing geometry object in the project.

        :param iso_type: type of isolation to be done: 0 = exteriors, 1 = interiors and 2 = both
        :param geometry: specific geometry to isolate
        :param dia: Tool diameter
        :param passes: Number of tool widths to cut
        :param overlap: Overlap between passes in fraction of tool diameter
        :param outname: Base name of the output object
        :param combine: Boolean: if to combine passes in one resulting object in case of multiple passes
        :param milling_type: type of milling: conventional or climbing
        :param follow: Boolean: if to generate a 'follow' geometry
        :param plot: Boolean: if to plot the resulting geometry object
        :return: None
        """

        if geometry is None:
            work_geo = self.follow_geometry if follow is True else self.solid_geometry
        else:
            work_geo = geometry

        if dia is None:
            dia = float(self.options["isotooldia"])

        if passes is None:
            passes = int(self.options["isopasses"])

        if overlap is None:
            overlap = float(self.options["isooverlap"])

        overlap /= 100.0

        combine = self.options["combine_passes"] if combine is None else bool(combine)

        if milling_type is None:
            milling_type = self.options["milling_type"]

        if iso_type is None:
            iso_t = 2
        else:
            iso_t = iso_type

        base_name = self.options["name"]

        if combine:
            if outname is None:
                if self.iso_type == 0:
                    iso_name = base_name + "_ext_iso"
                elif self.iso_type == 1:
                    iso_name = base_name + "_int_iso"
                else:
                    iso_name = base_name + "_iso"
            else:
                iso_name = outname

            def iso_init(geo_obj, app_obj):
                # Propagate options
                geo_obj.options["cnctooldia"] = str(self.options["isotooldia"])
                geo_obj.tool_type = self.ui.tool_type_radio.get_value().upper()

                geo_obj.solid_geometry = []

                # transfer the Cut Z and Vtip and VAngle values in case that we use the V-Shape tool in Gerber UI
                if self.ui.tool_type_radio.get_value() == 'v':
                    new_cutz = self.ui.cutz_spinner.get_value()
                    new_vtipdia = self.ui.tipdia_spinner.get_value()
                    new_vtipangle = self.ui.tipangle_spinner.get_value()
                    tool_type = 'V'
                else:
                    new_cutz = self.app.defaults['geometry_cutz']
                    new_vtipdia = self.app.defaults['geometry_vtipdia']
                    new_vtipangle = self.app.defaults['geometry_vtipangle']
                    tool_type = 'C1'

                # store here the default data for Geometry Data
                default_data = {}
                default_data.update({
                    "name": iso_name,
                    "plot": self.app.defaults['geometry_plot'],
                    "cutz": new_cutz,
                    "vtipdia": new_vtipdia,
                    "vtipangle": new_vtipangle,
                    "travelz": self.app.defaults['geometry_travelz'],
                    "feedrate": self.app.defaults['geometry_feedrate'],
                    "feedrate_z": self.app.defaults['geometry_feedrate_z'],
                    "feedrate_rapid": self.app.defaults['geometry_feedrate_rapid'],
                    "dwell": self.app.defaults['geometry_dwell'],
                    "dwelltime": self.app.defaults['geometry_dwelltime'],
                    "multidepth": self.app.defaults['geometry_multidepth'],
                    "ppname_g": self.app.defaults['geometry_ppname_g'],
                    "depthperpass": self.app.defaults['geometry_depthperpass'],
                    "extracut": self.app.defaults['geometry_extracut'],
                    "extracut_length": self.app.defaults['geometry_extracut_length'],
                    "toolchange": self.app.defaults['geometry_toolchange'],
                    "toolchangez": self.app.defaults['geometry_toolchangez'],
                    "endz": self.app.defaults['geometry_endz'],
                    "spindlespeed": self.app.defaults['geometry_spindlespeed'],
                    "toolchangexy": self.app.defaults['geometry_toolchangexy'],
                    "startz": self.app.defaults['geometry_startz']
                })

                geo_obj.tools = {}
                geo_obj.tools['1'] = {}
                geo_obj.tools.update({
                    '1': {
                        'tooldia': float(self.options["isotooldia"]),
                        'offset': 'Path',
                        'offset_value': 0.0,
                        'type': _('Rough'),
                        'tool_type': tool_type,
                        'data': default_data,
                        'solid_geometry': geo_obj.solid_geometry
                    }
                })

                for nr_pass in range(passes):
                    iso_offset = dia * ((2 * nr_pass + 1) / 2.0000001) - (nr_pass * overlap * dia)

                    # if milling type is climb then the move is counter-clockwise around features
                    mill_dir = 1 if milling_type == 'cl' else 0
                    geom = self.generate_envelope(iso_offset, mill_dir, geometry=work_geo, env_iso_type=iso_t,
                                                  follow=follow, nr_passes=nr_pass)

                    if geom == 'fail':
                        app_obj.inform.emit('[ERROR_NOTCL] %s' % _("Isolation geometry could not be generated."))
                        return 'fail'
                    geo_obj.solid_geometry.append(geom)

                    # update the geometry in the tools
                    geo_obj.tools['1']['solid_geometry'] = geo_obj.solid_geometry

                # detect if solid_geometry is empty and this require list flattening which is "heavy"
                # or just looking in the lists (they are one level depth) and if any is not empty
                # proceed with object creation, if there are empty and the number of them is the length
                # of the list then we have an empty solid_geometry which should raise a Custom Exception
                empty_cnt = 0
                if not isinstance(geo_obj.solid_geometry, list) and \
                        not isinstance(geo_obj.solid_geometry, MultiPolygon):
                    geo_obj.solid_geometry = [geo_obj.solid_geometry]

                for g in geo_obj.solid_geometry:
                    if g:
                        break
                    else:
                        empty_cnt += 1

                if empty_cnt == len(geo_obj.solid_geometry):
                    raise ValidationError("Empty Geometry", None)
                else:
                    app_obj.inform.emit('[success] %s" %s' % (_("Isolation geometry created"), geo_obj.options["name"]))

                # even if combine is checked, one pass is still single-geo
                geo_obj.multigeo = True if passes > 1 else False

                # ############################################################
                # ########## AREA SUBTRACTION ################################
                # ############################################################
                if self.ui.except_cb.get_value():
                    self.app.proc_container.update_view_text(' %s' % _("Subtracting Geo"))
                    geo_obj.solid_geometry = self.area_subtraction(geo_obj.solid_geometry)

            # TODO: Do something if this is None. Offer changing name?
            self.app.app_obj.new_object("geometry", iso_name, iso_init, plot=plot)
        else:
            for i in range(passes):
                offset = dia * ((2 * i + 1) / 2.0000001) - (i * overlap * dia)
                if passes > 1:
                    if outname is None:
                        if self.iso_type == 0:
                            iso_name = base_name + "_ext_iso" + str(i + 1)
                        elif self.iso_type == 1:
                            iso_name = base_name + "_int_iso" + str(i + 1)
                        else:
                            iso_name = base_name + "_iso" + str(i + 1)
                    else:
                        iso_name = outname
                else:
                    if outname is None:
                        if self.iso_type == 0:
                            iso_name = base_name + "_ext_iso"
                        elif self.iso_type == 1:
                            iso_name = base_name + "_int_iso"
                        else:
                            iso_name = base_name + "_iso"
                    else:
                        iso_name = outname

                def iso_init(geo_obj, fc_obj):
                    # Propagate options
                    geo_obj.options["cnctooldia"] = str(self.options["isotooldia"])
                    if self.ui.tool_type_radio.get_value() == 'v':
                        geo_obj.tool_type = 'V'
                    else:
                        geo_obj.tool_type = 'C1'

                    # if milling type is climb then the move is counter-clockwise around features
                    mill_dir = 1 if milling_type == 'cl' else 0
                    geom = self.generate_envelope(offset, mill_dir, geometry=work_geo, env_iso_type=iso_t,
                                                  follow=follow,
                                                  nr_passes=i)

                    if geom == 'fail':
                        fc_obj.inform.emit('[ERROR_NOTCL] %s' % _("Isolation geometry could not be generated."))
                        return 'fail'

                    geo_obj.solid_geometry = geom

                    # transfer the Cut Z and Vtip and VAngle values in case that we use the V-Shape tool in Gerber UI
                    # even if the resulting geometry is not multigeo we add the tools dict which will hold the data
                    # required to be transfered to the Geometry object
                    if self.ui.tool_type_radio.get_value() == 'v':
                        new_cutz = self.ui.cutz_spinner.get_value()
                        new_vtipdia = self.ui.tipdia_spinner.get_value()
                        new_vtipangle = self.ui.tipangle_spinner.get_value()
                        tool_type = 'V'
                    else:
                        new_cutz = self.app.defaults['geometry_cutz']
                        new_vtipdia = self.app.defaults['geometry_vtipdia']
                        new_vtipangle = self.app.defaults['geometry_vtipangle']
                        tool_type = 'C1'

                    # store here the default data for Geometry Data
                    default_data = {}
                    default_data.update({
                        "name": iso_name,
                        "plot": self.app.defaults['geometry_plot'],
                        "cutz": new_cutz,
                        "vtipdia": new_vtipdia,
                        "vtipangle": new_vtipangle,
                        "travelz": self.app.defaults['geometry_travelz'],
                        "feedrate": self.app.defaults['geometry_feedrate'],
                        "feedrate_z": self.app.defaults['geometry_feedrate_z'],
                        "feedrate_rapid": self.app.defaults['geometry_feedrate_rapid'],
                        "dwell": self.app.defaults['geometry_dwell'],
                        "dwelltime": self.app.defaults['geometry_dwelltime'],
                        "multidepth": self.app.defaults['geometry_multidepth'],
                        "ppname_g": self.app.defaults['geometry_ppname_g'],
                        "depthperpass": self.app.defaults['geometry_depthperpass'],
                        "extracut": self.app.defaults['geometry_extracut'],
                        "extracut_length": self.app.defaults['geometry_extracut_length'],
                        "toolchange": self.app.defaults['geometry_toolchange'],
                        "toolchangez": self.app.defaults['geometry_toolchangez'],
                        "endz": self.app.defaults['geometry_endz'],
                        "spindlespeed": self.app.defaults['geometry_spindlespeed'],
                        "toolchangexy": self.app.defaults['geometry_toolchangexy'],
                        "startz": self.app.defaults['geometry_startz']
                    })

                    geo_obj.tools = {}
                    geo_obj.tools['1'] = {}
                    geo_obj.tools.update({
                        '1': {
                            'tooldia': float(self.options["isotooldia"]),
                            'offset': 'Path',
                            'offset_value': 0.0,
                            'type': _('Rough'),
                            'tool_type': tool_type,
                            'data': default_data,
                            'solid_geometry': geo_obj.solid_geometry
                        }
                    })

                    # detect if solid_geometry is empty and this require list flattening which is "heavy"
                    # or just looking in the lists (they are one level depth) and if any is not empty
                    # proceed with object creation, if there are empty and the number of them is the length
                    # of the list then we have an empty solid_geometry which should raise a Custom Exception
                    empty_cnt = 0
                    if not isinstance(geo_obj.solid_geometry, list):
                        geo_obj.solid_geometry = [geo_obj.solid_geometry]

                    for g in geo_obj.solid_geometry:
                        if g:
                            break
                        else:
                            empty_cnt += 1

                    if empty_cnt == len(geo_obj.solid_geometry):
                        raise ValidationError("Empty Geometry", None)
                    else:
                        fc_obj.inform.emit('[success] %s: %s' %
                                            (_("Isolation geometry created"), geo_obj.options["name"]))
                    geo_obj.multigeo = False

                    # ############################################################
                    # ########## AREA SUBTRACTION ################################
                    # ############################################################
                    if self.ui.except_cb.get_value():
                        self.app.proc_container.update_view_text(' %s' % _("Subtracting Geo"))
                        geo_obj.solid_geometry = self.area_subtraction(geo_obj.solid_geometry)

                # TODO: Do something if this is None. Offer changing name?
                self.app.app_obj.new_object("geometry", iso_name, iso_init, plot=plot)

    def generate_envelope(self, offset, invert, geometry=None, env_iso_type=2, follow=None, nr_passes=0):
        # isolation_geometry produces an envelope that is going on the left of the geometry
        # (the copper features). To leave the least amount of burrs on the features
        # the tool needs to travel on the right side of the features (this is called conventional milling)
        # the first pass is the one cutting all of the features, so it needs to be reversed
        # the other passes overlap preceding ones and cut the left over copper. It is better for them
        # to cut on the right side of the left over copper i.e on the left side of the features.

        if follow:
            geom = self.isolation_geometry(offset, geometry=geometry, follow=follow)
        else:
            try:
                geom = self.isolation_geometry(offset, geometry=geometry, iso_type=env_iso_type, passes=nr_passes)
            except Exception as e:
                log.debug('GerberObject.isolate().generate_envelope() --> %s' % str(e))
                return 'fail'

        if invert:
            try:
                pl = []
                for p in geom:
                    if p is not None:
                        if isinstance(p, Polygon):
                            pl.append(Polygon(p.exterior.coords[::-1], p.interiors))
                        elif isinstance(p, LinearRing):
                            pl.append(Polygon(p.coords[::-1]))
                geom = MultiPolygon(pl)
            except TypeError:
                if isinstance(geom, Polygon) and geom is not None:
                    geom = Polygon(geom.exterior.coords[::-1], geom.interiors)
                elif isinstance(geom, LinearRing) and geom is not None:
                    geom = Polygon(geom.coords[::-1])
                else:
                    log.debug("GerberObject.isolate().generate_envelope() Error --> Unexpected Geometry %s" %
                              type(geom))
            except Exception as e:
                log.debug("GerberObject.isolate().generate_envelope() Error --> %s" % str(e))
                return 'fail'
        return geom

    def area_subtraction(self, geo, subtractor_geo=None):
        """
        Subtracts the subtractor_geo (if present else self.solid_geometry) from the geo

        :param geo: target geometry from which to subtract
        :param subtractor_geo: geometry that acts as subtractor
        :return:
        """
        new_geometry = []
        target_geo = geo

        if subtractor_geo:
            sub_union = cascaded_union(subtractor_geo)
        else:
            name = self.ui.obj_combo.currentText()
            subtractor_obj = self.app.collection.get_by_name(name)
            sub_union = cascaded_union(subtractor_obj.solid_geometry)

        try:
            for geo_elem in target_geo:
                if isinstance(geo_elem, Polygon):
                    for ring in self.poly2rings(geo_elem):
                        new_geo = ring.difference(sub_union)
                        if new_geo and not new_geo.is_empty:
                            new_geometry.append(new_geo)
                elif isinstance(geo_elem, MultiPolygon):
                    for poly in geo_elem:
                        for ring in self.poly2rings(poly):
                            new_geo = ring.difference(sub_union)
                            if new_geo and not new_geo.is_empty:
                                new_geometry.append(new_geo)
                elif isinstance(geo_elem, LineString):
                    new_geo = geo_elem.difference(sub_union)
                    if new_geo:
                        if not new_geo.is_empty:
                            new_geometry.append(new_geo)
                elif isinstance(geo_elem, MultiLineString):
                    for line_elem in geo_elem:
                        new_geo = line_elem.difference(sub_union)
                        if new_geo and not new_geo.is_empty:
                            new_geometry.append(new_geo)
        except TypeError:
            if isinstance(target_geo, Polygon):
                for ring in self.poly2rings(target_geo):
                    new_geo = ring.difference(sub_union)
                    if new_geo:
                        if not new_geo.is_empty:
                            new_geometry.append(new_geo)
            elif isinstance(target_geo, LineString):
                new_geo = target_geo.difference(sub_union)
                if new_geo and not new_geo.is_empty:
                    new_geometry.append(new_geo)
            elif isinstance(target_geo, MultiLineString):
                for line_elem in target_geo:
                    new_geo = line_elem.difference(sub_union)
                    if new_geo and not new_geo.is_empty:
                        new_geometry.append(new_geo)
        return new_geometry

    def on_plot_cb_click(self, *args):
        if self.muted_ui:
            return
        self.read_form_item('plot')
        self.plot()

    def on_solid_cb_click(self, *args):
        if self.muted_ui:
            return
        self.read_form_item('solid')
        self.plot()

    def on_multicolored_cb_click(self, *args):
        if self.muted_ui:
            return
        self.read_form_item('multicolored')
        self.plot()

    def on_follow_cb_click(self):
        if self.muted_ui:
            return
        self.plot()

    def on_aperture_table_visibility_change(self):
        if self.ui.aperture_table_visibility_cb.isChecked():
            # add the shapes storage for marking apertures
            if self.build_aperture_storage is False:
                self.build_aperture_storage = True

                if self.app.is_legacy is False:
                    for ap_code in self.apertures:
                        self.mark_shapes[ap_code] = self.app.plotcanvas.new_shape_collection(layers=1)
                else:
                    for ap_code in self.apertures:
                        self.mark_shapes[ap_code] = ShapeCollectionLegacy(obj=self, app=self.app,
                                                                          name=self.options['name'] + str(ap_code))

            self.ui.apertures_table.setVisible(True)
            for ap in self.mark_shapes:
                self.mark_shapes[ap].enabled = True

            self.ui.mark_all_cb.setVisible(True)
            self.ui.mark_all_cb.setChecked(False)
            self.build_ui()
        else:
            self.ui.apertures_table.setVisible(False)

            self.ui.mark_all_cb.setVisible(False)

            # on hide disable all mark plots
            try:
                for row in range(self.ui.apertures_table.rowCount()):
                    self.ui.apertures_table.cellWidget(row, 5).set_value(False)
                self.clear_plot_apertures()

                # for ap in list(self.mark_shapes.keys()):
                #     # self.mark_shapes[ap].enabled = False
                #     del self.mark_shapes[ap]
            except Exception as e:
                log.debug(" GerberObject.on_aperture_visibility_changed() --> %s" % str(e))

    def convert_units(self, units):
        """
        Converts the units of the object by scaling dimensions in all geometry
        and options.

        :param units: Units to which to convert the object: "IN" or "MM".
        :type units: str
        :return: None
        :rtype: None
        """

        # units conversion to get a conversion should be done only once even if we found multiple
        # units declaration inside a Gerber file (it can happen to find also the obsolete declaration)
        if self.conversion_done is True:
            log.debug("Gerber units conversion cancelled. Already done.")
            return

        log.debug("FlatCAMObj.GerberObject.convert_units()")

        factor = Gerber.convert_units(self, units)

        # self.options['isotooldia'] = float(self.options['isotooldia']) * factor
        # self.options['bboxmargin'] = float(self.options['bboxmargin']) * factor

    def plot(self, kind=None, **kwargs):
        """

        :param kind:    Not used, for compatibility with the plot method for other objects
        :param kwargs:  Color and face_color, visible
        :return:
        """
        log.debug(str(inspect.stack()[1][3]) + " --> GerberObject.plot()")

        # Does all the required setup and returns False
        # if the 'ptint' option is set to False.
        if not FlatCAMObj.plot(self):
            return

        if 'color' in kwargs:
            color = kwargs['color']
        else:
            color = self.outline_color

        if 'face_color' in kwargs:
            face_color = kwargs['face_color']
        else:
            face_color = self.fill_color

        if 'visible' not in kwargs:
            visible = self.options['plot']
        else:
            visible = kwargs['visible']

        # if the Follow Geometry checkbox is checked then plot only the follow geometry
        if self.ui.follow_cb.get_value():
            geometry = self.follow_geometry
        else:
            geometry = self.solid_geometry

        # Make sure geometry is iterable.
        try:
            __ = iter(geometry)
        except TypeError:
            geometry = [geometry]

        if self.app.is_legacy is False:
            def random_color():
                r_color = np.random.rand(4)
                r_color[3] = 1
                return r_color
        else:
            def random_color():
                while True:
                    r_color = np.random.rand(4)
                    r_color[3] = 1

                    new_color = '#'
                    for idx in range(len(r_color)):
                        new_color += '%x' % int(r_color[idx] * 255)
                    # do it until a valid color is generated
                    # a valid color has the # symbol, another 6 chars for the color and the last 2 chars for alpha
                    # for a total of 9 chars
                    if len(new_color) == 9:
                        break
                return new_color

        try:
            if self.options["solid"]:
                for g in geometry:
                    if type(g) == Polygon or type(g) == LineString:
                        self.add_shape(shape=g, color=color,
                                       face_color=random_color() if self.options['multicolored']
                                       else face_color, visible=visible)
                    elif type(g) == Point:
                        pass
                    else:
                        try:
                            for el in g:
                                self.add_shape(shape=el, color=color,
                                               face_color=random_color() if self.options['multicolored']
                                               else face_color, visible=visible)
                        except TypeError:
                            self.add_shape(shape=g, color=color,
                                           face_color=random_color() if self.options['multicolored']
                                           else face_color, visible=visible)
            else:
                for g in geometry:
                    if type(g) == Polygon or type(g) == LineString:
                        self.add_shape(shape=g, color=random_color() if self.options['multicolored'] else 'black',
                                       visible=visible)
                    elif type(g) == Point:
                        pass
                    else:
                        for el in g:
                            self.add_shape(shape=el, color=random_color() if self.options['multicolored'] else 'black',
                                           visible=visible)
            self.shapes.redraw(
                # update_colors=(self.fill_color, self.outline_color),
                # indexes=self.app.plotcanvas.shape_collection.data.keys()
            )
        except (ObjectDeleted, AttributeError):
            self.shapes.clear(update=True)
        except Exception as e:
            log.debug("GerberObject.plot() --> %s" % str(e))

    # experimental plot() when the solid_geometry is stored in the self.apertures
    def plot_aperture(self, run_thread=True, **kwargs):
        """

        :param run_thread: if True run the aperture plot as a thread in a worker
        :param kwargs: color and face_color
        :return:
        """

        log.debug(str(inspect.stack()[1][3]) + " --> GerberObject.plot_aperture()")

        # Does all the required setup and returns False
        # if the 'ptint' option is set to False.
        # if not FlatCAMObj.plot(self):
        #     return

        # for marking apertures, line color and fill color are the same
        if 'color' in kwargs:
            color = kwargs['color']
        else:
            color = self.app.defaults['gerber_plot_fill']

        if 'marked_aperture' not in kwargs:
            return
        else:
            aperture_to_plot_mark = kwargs['marked_aperture']
            if aperture_to_plot_mark is None:
                return

        if 'visible' not in kwargs:
            visibility = True
        else:
            visibility = kwargs['visible']

        with self.app.proc_container.new(_("Plotting Apertures")):

            def job_thread(app_obj):
                try:
                    if aperture_to_plot_mark in self.apertures:
                        for elem in self.apertures[aperture_to_plot_mark]['geometry']:
                            if 'solid' in elem:
                                geo = elem['solid']
                                if type(geo) == Polygon or type(geo) == LineString:
                                    self.add_mark_shape(apid=aperture_to_plot_mark, shape=geo, color=color,
                                                        face_color=color, visible=visibility)
                                else:
                                    for el in geo:
                                        self.add_mark_shape(apid=aperture_to_plot_mark, shape=el, color=color,
                                                            face_color=color, visible=visibility)

                    self.mark_shapes[aperture_to_plot_mark].redraw()

                except (ObjectDeleted, AttributeError):
                    self.clear_plot_apertures()
                except Exception as e:
                    log.debug("GerberObject.plot_aperture() --> %s" % str(e))

            if run_thread:
                self.app.worker_task.emit({'fcn': job_thread, 'params': [self]})
            else:
                job_thread(self)

    def clear_plot_apertures(self, aperture='all'):
        """

        :param aperture: string; aperture for which to clear the mark shapes
        :return:
        """

        if self.mark_shapes:
            if aperture == 'all':
                for apid in list(self.apertures.keys()):
                    try:
                        if self.app.is_legacy is True:
                            self.mark_shapes[apid].clear(update=False)
                        else:
                            self.mark_shapes[apid].clear(update=True)
                    except Exception as e:
                        log.debug("GerberObject.clear_plot_apertures() 'all' --> %s" % str(e))
            else:
                try:
                    if self.app.is_legacy is True:
                        self.mark_shapes[aperture].clear(update=False)
                    else:
                        self.mark_shapes[aperture].clear(update=True)
                except Exception as e:
                    log.debug("GerberObject.clear_plot_apertures() 'aperture' --> %s" % str(e))

    def clear_mark_all(self):
        self.ui.mark_all_cb.set_value(False)
        self.marked_rows[:] = []

    def on_mark_cb_click_table(self):
        """
        Will mark aperture geometries on canvas or delete the markings depending on the checkbox state
        :return:
        """

        self.ui_disconnect()
        try:
            cw = self.sender()
            cw_index = self.ui.apertures_table.indexAt(cw.pos())
            cw_row = cw_index.row()
        except AttributeError:
            cw_row = 0
        except TypeError:
            return

        self.marked_rows[:] = []

        try:
            aperture = self.ui.apertures_table.item(cw_row, 1).text()
        except AttributeError:
            return

        if self.ui.apertures_table.cellWidget(cw_row, 5).isChecked():
            self.marked_rows.append(True)
            # self.plot_aperture(color='#2d4606bf', marked_aperture=aperture, visible=True)
            self.plot_aperture(color=self.app.defaults['global_sel_draw_color'] + 'AF',
                               marked_aperture=aperture, visible=True, run_thread=True)
            # self.mark_shapes[aperture].redraw()
        else:
            self.marked_rows.append(False)
            self.clear_plot_apertures(aperture=aperture)

        # make sure that the Mark All is disabled if one of the row mark's are disabled and
        # if all the row mark's are enabled also enable the Mark All checkbox
        cb_cnt = 0
        total_row = self.ui.apertures_table.rowCount()
        for row in range(total_row):
            if self.ui.apertures_table.cellWidget(row, 5).isChecked():
                cb_cnt += 1
            else:
                cb_cnt -= 1
        if cb_cnt < total_row:
            self.ui.mark_all_cb.setChecked(False)
        else:
            self.ui.mark_all_cb.setChecked(True)
        self.ui_connect()

    def on_mark_all_click(self):
        self.ui_disconnect()
        mark_all = self.ui.mark_all_cb.isChecked()
        for row in range(self.ui.apertures_table.rowCount()):
            # update the mark_rows list
            if mark_all:
                self.marked_rows.append(True)
            else:
                self.marked_rows[:] = []

            mark_cb = self.ui.apertures_table.cellWidget(row, 5)
            mark_cb.setChecked(mark_all)

        if mark_all:
            for aperture in self.apertures:
                # self.plot_aperture(color='#2d4606bf', marked_aperture=aperture, visible=True)
                self.plot_aperture(color=self.app.defaults['global_sel_draw_color'] + 'AF',
                                   marked_aperture=aperture, visible=True)
            # HACK: enable/disable the grid for a better look
            self.app.ui.grid_snap_btn.trigger()
            self.app.ui.grid_snap_btn.trigger()
        else:
            self.clear_plot_apertures()
            self.marked_rows[:] = []

        self.ui_connect()

    def export_gerber(self, whole, fract, g_zeros='L', factor=1):
        """
        Creates a Gerber file content to be exported to a file.

        :param whole: how many digits in the whole part of coordinates
        :param fract: how many decimals in coordinates
        :param g_zeros: type of the zero suppression used: LZ or TZ; string
        :param factor: factor to be applied onto the Gerber coordinates
        :return: Gerber_code
        """
        log.debug("GerberObject.export_gerber() --> Generating the Gerber code from the selected Gerber file")

        def tz_format(x, y, fac):
            x_c = x * fac
            y_c = y * fac

            x_form = "{:.{dec}f}".format(x_c, dec=fract)
            y_form = "{:.{dec}f}".format(y_c, dec=fract)

            # extract whole part and decimal part
            x_form = x_form.partition('.')
            y_form = y_form.partition('.')

            # left padd the 'whole' part with zeros
            x_whole = x_form[0].rjust(whole, '0')
            y_whole = y_form[0].rjust(whole, '0')

            # restore the coordinate padded in the left with 0 and added the decimal part
            # without the decinal dot
            x_form = x_whole + x_form[2]
            y_form = y_whole + y_form[2]
            return x_form, y_form

        def lz_format(x, y, fac):
            x_c = x * fac
            y_c = y * fac

            x_form = "{:.{dec}f}".format(x_c, dec=fract).replace('.', '')
            y_form = "{:.{dec}f}".format(y_c, dec=fract).replace('.', '')

            # pad with rear zeros
            x_form.ljust(length, '0')
            y_form.ljust(length, '0')

            return x_form, y_form

        # Gerber code is stored here
        gerber_code = ''

        # apertures processing
        try:
            length = whole + fract
            if '0' in self.apertures:
                if 'geometry' in self.apertures['0']:
                    for geo_elem in self.apertures['0']['geometry']:
                        if 'solid' in geo_elem:
                            geo = geo_elem['solid']
                            if not geo.is_empty:
                                gerber_code += 'G36*\n'
                                geo_coords = list(geo.exterior.coords)
                                # first command is a move with pen-up D02 at the beginning of the geo
                                if g_zeros == 'T':
                                    x_formatted, y_formatted = tz_format(geo_coords[0][0], geo_coords[0][1], factor)
                                    gerber_code += "X{xform}Y{yform}D02*\n".format(xform=x_formatted,
                                                                                   yform=y_formatted)
                                else:
                                    x_formatted, y_formatted = lz_format(geo_coords[0][0], geo_coords[0][1], factor)
                                    gerber_code += "X{xform}Y{yform}D02*\n".format(xform=x_formatted,
                                                                                   yform=y_formatted)
                                for coord in geo_coords[1:]:
                                    if g_zeros == 'T':
                                        x_formatted, y_formatted = tz_format(coord[0], coord[1], factor)
                                        gerber_code += "X{xform}Y{yform}D01*\n".format(xform=x_formatted,
                                                                                       yform=y_formatted)
                                    else:
                                        x_formatted, y_formatted = lz_format(coord[0], coord[1], factor)
                                        gerber_code += "X{xform}Y{yform}D01*\n".format(xform=x_formatted,
                                                                                       yform=y_formatted)
                                gerber_code += 'D02*\n'
                                gerber_code += 'G37*\n'

                                clear_list = list(geo.interiors)
                                if clear_list:
                                    gerber_code += '%LPC*%\n'
                                    for clear_geo in clear_list:
                                        gerber_code += 'G36*\n'
                                        geo_coords = list(clear_geo.coords)

                                        # first command is a move with pen-up D02 at the beginning of the geo
                                        if g_zeros == 'T':
                                            x_formatted, y_formatted = tz_format(
                                                geo_coords[0][0], geo_coords[0][1], factor)
                                            gerber_code += "X{xform}Y{yform}D02*\n".format(xform=x_formatted,
                                                                                           yform=y_formatted)
                                        else:
                                            x_formatted, y_formatted = lz_format(
                                                geo_coords[0][0], geo_coords[0][1], factor)
                                            gerber_code += "X{xform}Y{yform}D02*\n".format(xform=x_formatted,
                                                                                           yform=y_formatted)

                                        prev_coord = geo_coords[0]
                                        for coord in geo_coords[1:]:
                                            if coord != prev_coord:
                                                if g_zeros == 'T':
                                                    x_formatted, y_formatted = tz_format(coord[0], coord[1], factor)
                                                    gerber_code += "X{xform}Y{yform}D01*\n".format(xform=x_formatted,
                                                                                                   yform=y_formatted)
                                                else:
                                                    x_formatted, y_formatted = lz_format(coord[0], coord[1], factor)
                                                    gerber_code += "X{xform}Y{yform}D01*\n".format(xform=x_formatted,
                                                                                                   yform=y_formatted)
                                            prev_coord = coord

                                        gerber_code += 'D02*\n'
                                        gerber_code += 'G37*\n'
                                    gerber_code += '%LPD*%\n'
                        if 'clear' in geo_elem:
                            geo = geo_elem['clear']
                            if not geo.is_empty:
                                gerber_code += '%LPC*%\n'
                                gerber_code += 'G36*\n'
                                geo_coords = list(geo.exterior.coords)
                                # first command is a move with pen-up D02 at the beginning of the geo
                                if g_zeros == 'T':
                                    x_formatted, y_formatted = tz_format(geo_coords[0][0], geo_coords[0][1], factor)
                                    gerber_code += "X{xform}Y{yform}D02*\n".format(xform=x_formatted,
                                                                                   yform=y_formatted)
                                else:
                                    x_formatted, y_formatted = lz_format(geo_coords[0][0], geo_coords[0][1], factor)
                                    gerber_code += "X{xform}Y{yform}D02*\n".format(xform=x_formatted,
                                                                                   yform=y_formatted)

                                prev_coord = geo_coords[0]
                                for coord in geo_coords[1:]:
                                    if coord != prev_coord:
                                        if g_zeros == 'T':
                                            x_formatted, y_formatted = tz_format(coord[0], coord[1], factor)
                                            gerber_code += "X{xform}Y{yform}D01*\n".format(xform=x_formatted,
                                                                                           yform=y_formatted)
                                        else:
                                            x_formatted, y_formatted = lz_format(coord[0], coord[1], factor)
                                            gerber_code += "X{xform}Y{yform}D01*\n".format(xform=x_formatted,
                                                                                           yform=y_formatted)
                                    prev_coord = coord

                                gerber_code += 'D02*\n'
                                gerber_code += 'G37*\n'
                                gerber_code += '%LPD*%\n'
        except Exception as e:
            log.debug("FlatCAMObj.GerberObject.export_gerber() '0' aperture --> %s" % str(e))

        for apid in self.apertures:
            if apid == '0':
                continue
            else:
                gerber_code += 'D%s*\n' % str(apid)
                if 'geometry' in self.apertures[apid]:
                    for geo_elem in self.apertures[apid]['geometry']:
                        try:
                            if 'follow' in geo_elem:
                                geo = geo_elem['follow']
                                if not geo.is_empty:
                                    if isinstance(geo, Point):
                                        if g_zeros == 'T':
                                            x_formatted, y_formatted = tz_format(geo.x, geo.y, factor)
                                            gerber_code += "X{xform}Y{yform}D03*\n".format(xform=x_formatted,
                                                                                           yform=y_formatted)
                                        else:
                                            x_formatted, y_formatted = lz_format(geo.x, geo.y, factor)
                                            gerber_code += "X{xform}Y{yform}D03*\n".format(xform=x_formatted,
                                                                                           yform=y_formatted)
                                    else:
                                        geo_coords = list(geo.coords)
                                        # first command is a move with pen-up D02 at the beginning of the geo
                                        if g_zeros == 'T':
                                            x_formatted, y_formatted = tz_format(
                                                geo_coords[0][0], geo_coords[0][1], factor)
                                            gerber_code += "X{xform}Y{yform}D02*\n".format(xform=x_formatted,
                                                                                           yform=y_formatted)
                                        else:
                                            x_formatted, y_formatted = lz_format(
                                                geo_coords[0][0], geo_coords[0][1], factor)
                                            gerber_code += "X{xform}Y{yform}D02*\n".format(xform=x_formatted,
                                                                                           yform=y_formatted)

                                        prev_coord = geo_coords[0]
                                        for coord in geo_coords[1:]:
                                            if coord != prev_coord:
                                                if g_zeros == 'T':
                                                    x_formatted, y_formatted = tz_format(coord[0], coord[1], factor)
                                                    gerber_code += "X{xform}Y{yform}D01*\n".format(xform=x_formatted,
                                                                                                   yform=y_formatted)
                                                else:
                                                    x_formatted, y_formatted = lz_format(coord[0], coord[1], factor)
                                                    gerber_code += "X{xform}Y{yform}D01*\n".format(xform=x_formatted,
                                                                                                   yform=y_formatted)
                                            prev_coord = coord

                                        # gerber_code += "D02*\n"
                        except Exception as e:
                            log.debug("FlatCAMObj.GerberObject.export_gerber() 'follow' --> %s" % str(e))

                        try:
                            if 'clear' in geo_elem:
                                gerber_code += '%LPC*%\n'

                                geo = geo_elem['clear']
                                if not geo.is_empty:
                                    if isinstance(geo, Point):
                                        if g_zeros == 'T':
                                            x_formatted, y_formatted = tz_format(geo.x, geo.y, factor)
                                            gerber_code += "X{xform}Y{yform}D03*\n".format(xform=x_formatted,
                                                                                           yform=y_formatted)
                                        else:
                                            x_formatted, y_formatted = lz_format(geo.x, geo.y, factor)
                                            gerber_code += "X{xform}Y{yform}D03*\n".format(xform=x_formatted,
                                                                                           yform=y_formatted)
                                    elif isinstance(geo, Polygon):
                                        geo_coords = list(geo.exterior.coords)
                                        # first command is a move with pen-up D02 at the beginning of the geo
                                        if g_zeros == 'T':
                                            x_formatted, y_formatted = tz_format(
                                                geo_coords[0][0], geo_coords[0][1], factor)
                                            gerber_code += "X{xform}Y{yform}D02*\n".format(xform=x_formatted,
                                                                                           yform=y_formatted)
                                        else:
                                            x_formatted, y_formatted = lz_format(
                                                geo_coords[0][0], geo_coords[0][1], factor)
                                            gerber_code += "X{xform}Y{yform}D02*\n".format(xform=x_formatted,
                                                                                           yform=y_formatted)

                                        prev_coord = geo_coords[0]
                                        for coord in geo_coords[1:]:
                                            if coord != prev_coord:
                                                if g_zeros == 'T':
                                                    x_formatted, y_formatted = tz_format(coord[0], coord[1], factor)
                                                    gerber_code += "X{xform}Y{yform}D01*\n".format(xform=x_formatted,
                                                                                                   yform=y_formatted)
                                                else:
                                                    x_formatted, y_formatted = lz_format(coord[0], coord[1], factor)
                                                    gerber_code += "X{xform}Y{yform}D01*\n".format(xform=x_formatted,
                                                                                                   yform=y_formatted)

                                            prev_coord = coord

                                        for geo_int in geo.interiors:
                                            geo_coords = list(geo_int.coords)
                                            # first command is a move with pen-up D02 at the beginning of the geo
                                            if g_zeros == 'T':
                                                x_formatted, y_formatted = tz_format(
                                                    geo_coords[0][0], geo_coords[0][1], factor)
                                                gerber_code += "X{xform}Y{yform}D02*\n".format(xform=x_formatted,
                                                                                               yform=y_formatted)
                                            else:
                                                x_formatted, y_formatted = lz_format(
                                                    geo_coords[0][0], geo_coords[0][1], factor)
                                                gerber_code += "X{xform}Y{yform}D02*\n".format(xform=x_formatted,
                                                                                               yform=y_formatted)

                                            prev_coord = geo_coords[0]
                                            for coord in geo_coords[1:]:
                                                if coord != prev_coord:
                                                    if g_zeros == 'T':
                                                        x_formatted, y_formatted = tz_format(coord[0], coord[1], factor)
                                                        gerber_code += "X{xform}Y{yform}D01*\n".format(
                                                            xform=x_formatted,
                                                            yform=y_formatted)
                                                    else:
                                                        x_formatted, y_formatted = lz_format(coord[0], coord[1], factor)
                                                        gerber_code += "X{xform}Y{yform}D01*\n".format(
                                                            xform=x_formatted,
                                                            yform=y_formatted)

                                                prev_coord = coord
                                    else:
                                        geo_coords = list(geo.coords)
                                        # first command is a move with pen-up D02 at the beginning of the geo
                                        if g_zeros == 'T':
                                            x_formatted, y_formatted = tz_format(
                                                geo_coords[0][0], geo_coords[0][1], factor)
                                            gerber_code += "X{xform}Y{yform}D02*\n".format(xform=x_formatted,
                                                                                           yform=y_formatted)
                                        else:
                                            x_formatted, y_formatted = lz_format(
                                                geo_coords[0][0], geo_coords[0][1], factor)
                                            gerber_code += "X{xform}Y{yform}D02*\n".format(xform=x_formatted,
                                                                                           yform=y_formatted)

                                        prev_coord = geo_coords[0]
                                        for coord in geo_coords[1:]:
                                            if coord != prev_coord:
                                                if g_zeros == 'T':
                                                    x_formatted, y_formatted = tz_format(coord[0], coord[1], factor)
                                                    gerber_code += "X{xform}Y{yform}D01*\n".format(xform=x_formatted,
                                                                                                   yform=y_formatted)
                                                else:
                                                    x_formatted, y_formatted = lz_format(coord[0], coord[1], factor)
                                                    gerber_code += "X{xform}Y{yform}D01*\n".format(xform=x_formatted,
                                                                                                   yform=y_formatted)

                                            prev_coord = coord
                                        # gerber_code += "D02*\n"
                                    gerber_code += '%LPD*%\n'
                        except Exception as e:
                            log.debug("FlatCAMObj.GerberObject.export_gerber() 'clear' --> %s" % str(e))

        if not self.apertures:
            log.debug("FlatCAMObj.GerberObject.export_gerber() --> Gerber Object is empty: no apertures.")
            return 'fail'

        return gerber_code

    def mirror(self, axis, point):
        Gerber.mirror(self, axis=axis, point=point)
        self.replotApertures.emit()

    def offset(self, vect):
        Gerber.offset(self, vect=vect)
        self.replotApertures.emit()

    def rotate(self, angle, point):
        Gerber.rotate(self, angle=angle, point=point)
        self.replotApertures.emit()

    def scale(self, xfactor, yfactor=None, point=None):
        Gerber.scale(self, xfactor=xfactor, yfactor=yfactor, point=point)
        self.replotApertures.emit()

    def skew(self, angle_x, angle_y, point):
        Gerber.skew(self, angle_x=angle_x, angle_y=angle_y, point=point)
        self.replotApertures.emit()

    def buffer(self, distance, join, factor=None):
        Gerber.buffer(self, distance=distance, join=join, factor=factor)
        self.replotApertures.emit()

    def serialize(self):
        return {
            "options": self.options,
            "kind": self.kind
        }
